#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPCP / GES DISC 数据下载脚本（带 NASA Earthdata Login 认证）

============================================================
为什么原脚本报 401
============================================================
data.gesdisc.earthdata.nasa.gov 整个站点都要求 Earthdata Login。
未认证的请求会被 302 跳到:

    https://urs.earthdata.nasa.gov/oauth/authorize?...&app_type=401

这个 URL 末尾的 app_type=401 是 URS 的一个约定：它用 HTTP 401 +
WWW-Authenticate 头来"要求"客户端做 HTTP Basic 认证。原脚本从来不带
任何凭据，所以 requests 跟到这一跳就拿到 401，raise_for_status() 直接抛
"401 Client Error: Unauthorized"——这就是你看到的错误。它甚至没走到真正
的文件地址。

============================================================
两步修好
============================================================
第 1 步（一次性）：准备 Earthdata 账号 + 授权 GES DISC 应用

  a. 到 https://urs.earthdata.nasa.gov/users/new 注册（已有就登录）。
  b. 登录后进 https://urs.earthdata.nasa.gov/profile -> Applications ->
     "Approve More Applications" -> 找到并批准
         NASA GESDISC DATA ARCHIVE
     以及（保险起见） NASA GESDISC DATA ARCHIVE (Legacy) / EOSDIS。
     这一步非常关键：账号密码对了但没批准这个应用，GES DISC 依然返回 401。

第 2 步：把这台机器上的凭据写好，然后跑 --check

  方式 A（不用写明文密码到脚本里，推荐）：
      python download_files_GPCPDAY_3.3_authed.py --write-netrc
      # 按提示输入用户名/密码，会在 C:\\Users\\<你>\\_netrc 生成文件

  方式 B（自己手写 C:\\Users\\<你>\\_netrc，注意 Windows 下文件名没有点）：
      machine urs.earthdata.nasa.gov
            login 你的用户名
            password 你的密码

  写完先自检：
      python download_files_GPCPDAY_3.3_authed.py --check

  自检通过再正式下载：
      python download_files_GPCPDAY_3.3_authed.py --start 2000-01-01 --end 2000-12-31

============================================================
其它已修复的坑
============================================================
* 断点续传 + 先写 .part 再原子改名，中断后重跑不会留下半个 .nc4。
* 校验文件头（HDF5 / NetCDF3 魔数），把"登录页 HTML 被存成 .nc4"这种
  假成功识别出来并删除重下。
* 429/5xx/连接中断自动指数退避重试，尊重 Retry-After。
* 默认 4 并发（GES DISC 对单账号并发有上限，5~8 以上容易吃 429）。
* 401 时把服务端返回的英文提示翻成人话，直接告诉你缺哪一步。
* 支持环境变量代理（你机器上 HTTP_PROXY=127.0.0.1:7890 会被自动使用），
  也支持 --no-proxy / --insecure。

仅依赖 requests；tqdm 可选。
"""

import argparse
import getpass
import os
import re
import sys
import time
import netrc as netrc_mod
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

try:
    import requests
    from requests.auth import HTTPBasicAuth
except ImportError:
    sys.exit("缺少 requests：请先运行  pip install requests  （可选：pip install tqdm）")

try:
    from tqdm import tqdm
except ImportError:  # tqdm 可选
    tqdm = None


def _setup_stdio():
    """让输出立刻可见（IDE/管道里也刷出来），并避免 GBK 控制台因 emoji 崩掉。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True, errors="replace")
        except Exception:
            pass


_setup_stdio()


CMR_BASE_URL = "https://cmr.earthdata.nasa.gov"
URS_HOST = "urs.earthdata.nasa.gov"
URAL_PROFILE = "https://urs.earthdata.nasa.gov/profile"
DEFAULT_NETRC = os.environ.get("NETRC") or os.path.join(os.path.expanduser("~"), "_netrc")

SHORT_NAME = "GPCPDAY"
VERSION = "3.3"
PROBE_URL = (
    "https://data.gesdisc.earthdata.nasa.gov/data/GPCP/GPCPDAY.3.3/"
    "2000/GPCPDAY_L3_20001126_V3.3.nc4"
)

# 这是 GES DISC 未认证时被跳转到的那个 OAuth 地址。
# app_type=401 表示"用 HTTP 401 + Basic 挑战来要求输入账号密码"：
#   302 = 账号密码 OK（会带 code 跳回 GES DISC）
#   401 = 账号密码错（Access denied）
#   200 = 返回了网页，通常是要你批准应用 / 同意协议
URS_PROBE = (
    f"https://{URS_HOST}/oauth/authorize?client_id=e2WVk8Pw6weeLUKZYOxvTQ"
    "&response_type=code&redirect_uri=https://data.gesdisc.earthdata.nasa.gov/login"
    "&app_type=401"
)

HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
NETCDF3_MAGIC = b"CDF"


# --------------------------------------------------------------------------
# 认证
# --------------------------------------------------------------------------
class AuthError(Exception):
    pass


class EarthdataSession(requests.Session):
    """只在 urs.earthdata.nasa.gov 上带 Basic 凭据的 Session。

    requests 默认会在跨主机重定向时丢掉 Authorization 头，这里在
    rebuild_auth 里对 URS 主机重新挂上——这正是 Earthdata 官方给的做法。
    """

    def __init__(self, username, password, verify=True, trust_proxy=True):
        super().__init__()
        self._urs_auth = HTTPBasicAuth(username, password) if username else None
        self.verify = verify
        self.trust_env = trust_proxy
        self.headers.update({"User-Agent": "gpcp-downloader/2.0 (python-requests)"})
        # 连接层重试：代理抖动（10053/连接被重置）时自动重来
        try:
            from urllib3.util.retry import Retry
            retry = Retry(total=4, connect=4, read=2, backoff_factor=1.0,
                          status_forcelist=(429, 500, 502, 503, 504),
                          allowed_methods=frozenset(["GET", "HEAD"]),
                          respect_retry_after_header=True)
            adapter = requests.adapters.HTTPAdapter(max_retries=retry, pool_maxsize=16)
            self.mount("https://", adapter)
            self.mount("http://", adapter)
        except Exception:
            pass

    def rebuild_auth(self, prepared_request, response):
        super().rebuild_auth(prepared_request, response)
        if self._urs_auth is None:
            return
        host = (urlparse(prepared_request.url).hostname or "").lower()
        if host == URS_HOST:
            prepared_request.prepare_auth(self._urs_auth)


def _read_netrc(path):
    if not path or not os.path.exists(path):
        return None
    try:
        auth = netrc_mod.netrc(path).authenticators(URS_HOST)
    except netrc_mod.NetrcParseError as exc:
        print(f"⚠️  {path} 解析失败：{exc}（检查缩进/引号，密码含空格要用双引号）")
        return None
    except Exception as exc:  # 权限等
        print(f"⚠️  读取 {path} 失败：{exc}")
        return None
    if not auth:
        return None
    login, _account, password = auth
    return (login, password) if login and password else None


def resolve_credentials(args):
    """返回 (username, password, 来源说明)"""
    if args.user and args.password:
        return args.user, args.password, "--user/--password 命令行参数"

    env_u = os.environ.get("EARTHDATA_USERNAME")
    env_p = os.environ.get("EARTHDATA_PASSWORD")
    if env_u and env_p:
        return env_u, env_p, "EARTHDATA_USERNAME / EARTHDATA_PASSWORD 环境变量"

    for path in filter(None, [args.netrc, DEFAULT_NETRC]):
        creds = _read_netrc(path)
        if creds:
            return creds[0], creds[1], path

    if args.write_netrc:
        return None, None, "需要交互输入"

    return None, None, None


def _netrc_token(value):
    """netrc 里含空格或 # 的字段必须加双引号，否则解析失败（bad follower token）。"""
    if value and not re.search(r'[\s#"\']', value):
        return value
    return '"%s"' % value


def write_netrc(path=DEFAULT_NETRC, user=None, password=None):
    print("生成/更新 Earthdata 凭据文件：", path)
    print("（密码来自 https://urs.earthdata.nasa.gov ，不会显示在屏幕上）")

    interactive = bool(getattr(sys.stdin, "isatty", lambda: False)())

    if not user:
        if not interactive:
            print("\n⚠️  当前不是交互终端（stdin 不是键盘），脚本读不到输入，会“看起来没反应”。")
            print("   改用这两种写法之一：")
            print("     A) python 本脚本 --write-netrc --user 用户名 --password 密码")
            print("     B) 直接用 PowerShell 写文件（见下方），完全不依赖 Python")
            return 2
        try:
            user = input("Earthdata 用户名: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            return 2
    if not user:
        print("用户名不能为空。")
        return 2

    if not password:
        if not interactive:
            print("⚠️  需要密码但没有交互终端。请加 --password 参数，或用 PowerShell 方式写。")
            return 2
        try:
            password = getpass.getpass("Earthdata 密码: ")
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            return 2
    if not password:
        print("密码不能为空。")
        return 2

    if '"' in password:
        print('⚠️  密码里含英文双引号 "，netrc 格式无法安全表示，')
        print("   请改用环境变量：set EARTHDATA_PASSWORD=... 或直接用 --password 参数。")
    block = "machine %s\n  login %s\n  password %s\n" % (
        URS_HOST, _netrc_token(user), _netrc_token(password))
    existing = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            existing = fh.read()
        if re.search(rf"machine\s+{re.escape(URS_HOST)}\b", existing):
            # 替换已有块
            existing = re.sub(
                rf"machine\s+{re.escape(URS_HOST)}\b.*?(?=\n*machine\s|\Z)",
                block,
                existing,
                flags=re.S,
            )
            block = existing
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(block)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    print(f"✅ 已写入 {path}")
    print(f"   login = {user}")
    print("   注意：Windows 上文件名是 _netrc（不是 .netrc），放在用户主目录。")
    print("   下一步：python 本脚本 --check")
    return 0


# --------------------------------------------------------------------------
# 诊断
# --------------------------------------------------------------------------
def _hint_for_401(text):
    low = (text or "").lower()
    hints = []
    if "access denied" in low:
        hints.append(
            "URS 拒绝了这组用户名/密码（不是权限问题，是凭据本身不对）。"
            "检查 _netrc 里的 login / password 是否与 https://urs.earthdata.nasa.gov 一致；"
            "密码里若有 # 空格等字符，需要用双引号包起来。"
        )
    if "authorize" in low or "approve" in low or "eula" in low:
        hints.append(
            "服务端说这个账号还没授权该应用 —— 打开 "
            f"{URAL_PROFILE} -> Applications -> Approve More Applications，"
            "批准 “NASA GESDISC DATA ARCHIVE”。"
        )
    if not hints:
        hints.append(
            "确认 (1) _netrc 存在且机器名是 urs.earthdata.nasa.gov；"
            "(2) 已批准 “NASA GESDISC DATA ARCHIVE” 应用；"
            "(3) 在浏览器里能手动下载该文件。"
        )
    return "\n   ".join(hints)


def _sniff_html(body):
    """从错误/授权网页里捞关键信息"""
    low = body.lower()
    if "approve" in low or "authorize" in low:
        return ("页面在要你批准应用 —— 用浏览器登录 "
                f"{URAL_PROFILE} 的 Applications，批准 “NASA GESDISC DATA ARCHIVE”。")
    if "eula" in low or "terms of use" in low:
        return "页面是 GES DISC 使用协议 —— 用浏览器打开该数据集页面点一次同意即可。"
    snippet = " ".join(body.split())[:300]
    return f"页面内容：{snippet}"


def check(session, verify):
    print("=" * 72)
    print("Earthdata 认证自检")
    print("=" * 72)

    proxies = requests.utils.getproxies()
    if proxies:
        print("代理：", proxies, "（requests 会自动走它；有疑虑可加 --no-proxy 对比）")

    # ---- 1/3 账号密码 ----
    print("\n[1/3] 账号密码（直接拿 URS 的 OAuth Basic 挑战来验）...")
    try:
        r = session.get(URS_PROBE, allow_redirects=False, timeout=60, verify=verify)
    except requests.RequestException as exc:
        print(f"    ❌ 连不上 URS：{exc}")
        print("       SSL/代理问题可试 --no-proxy 或 --insecure。")
        return False

    if r.status_code in (301, 302, 303, 307, 308):
        print("    ✅ 302 —— 用户名/密码被接受")
    elif r.status_code == 401:
        print("    ❌ 401 “HTTP Basic: Access denied.” —— 用户名或密码不对")
        print("   " + _hint_for_401(r.text))
        return False
    elif r.status_code == 200:
        print("    ⚠️  200 —— 密码可能没问题，但卡在“批准应用”这一步")
        print("   " + _sniff_html(r.text[:4000]))
        return False
    else:
        print(f"    ❌ 未预期状态 {r.status_code}: {r.text[:200]}")
        return False

    # ---- 2/3 数据文件 ----
    print("\n[2/3] 从 GES DISC 取一个真实 GPCP 文件的前 8 字节 ...")
    try:
        r = session.get(PROBE_URL, headers={"Range": "bytes=0-7"},
                        stream=True, timeout=90, verify=verify)
    except requests.RequestException as exc:
        print(f"    ❌ 连接 GES DISC 失败：{exc}")
        return False

    print(f"    status={r.status_code}  final_url={r.url.split('?')[0]}")
    if r.status_code in (200, 206):
        head = next(r.iter_content(8), b"")
        ok = head.startswith(HDF5_MAGIC) or head.startswith(NETCDF3_MAGIC)
        if ok:
            r.close()
            print(f"    ✅ 前 8 字节 {head!r} 是 NetCDF/HDF5 —— 可以开始下载了")
        else:
            body = head + (r.content[:4000] if not r.headers.get("Content-Range") else b"")
            r.close()
            print(f"    ⚠️  拿到的不是数据文件（前 8 字节 {head!r}）")
            print("   " + _sniff_html(body.decode("utf-8", "replace")))
        return ok

    body = r.text[:4000] if r.status_code < 500 else ""
    r.close()
    if r.status_code == 401:
        print("    ❌ 401 Unauthorized")
        print("   " + _hint_for_401(body))
    elif r.status_code == 403:
        print("    ❌ 403：" + _sniff_html(body))
    elif r.status_code == 404:
        print("    ⚠️ 404：认证大概已通过，只是探针文件没了（数据集结构变了）")
        return True
    else:
        print(f"    ❌ 未预期状态 {r.status_code}: {' '.join(body.split())[:300]}")
    return False


# --------------------------------------------------------------------------
# CMR 查询
# --------------------------------------------------------------------------
def query_cmr_granules(session, short_name, version, page_size=2000,
                       search_after=None, **extra_params):
    url = f"{CMR_BASE_URL}/search/granules.umm_json"
    params = {"short_name": short_name, "version": version,
              "page_size": page_size, **extra_params}
    headers = {"Accept": "application/json"}
    if search_after:
        headers["CMR-Search-After"] = search_after
    r = session.get(url, params=params, headers=headers, timeout=120)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print("CMR 查询失败：", r.text[:500])
        raise
    return r, r.json().get("items", [])


def count_granules(session, short_name, version, **params):
    url = f"{CMR_BASE_URL}/search/granules.umm_json"
    p = {"short_name": short_name, "version": version, "page_size": 1, **params}
    r = session.get(url, params=p, timeout=120)
    r.raise_for_status()
    return r.json().get("hits", 0)


def collect_urls(session, short_name, version, total, page_size=2000, **params):
    urls, seen, no_url = [], set(), 0
    search_after = None
    bar = tqdm(total=total, desc="收集下载链接", unit="granule") if tqdm else None
    try:
        while True:
            resp, items = query_cmr_granules(session, short_name, version,
                                             page_size, search_after, **params)
            for item in items:
                if bar:
                    bar.update(1)
                found = [u.get("URL") for u in
                         item.get("umm", {}).get("RelatedUrls", [])
                         if u.get("Type") == "GET DATA" and u.get("URL")]
                if not found:
                    no_url += 1
                for u in found:
                    if u not in seen:
                        seen.add(u)
                        urls.append(u)
            search_after = resp.headers.get("CMR-Search-After")
            if not search_after:
                break
    finally:
        if bar:
            bar.close()
    print(f"共找到 {len(urls)} 个文件" + (f"（{no_url} 个 granule 无下载链接）" if no_url else ""))
    return urls


# --------------------------------------------------------------------------
# 下载
# --------------------------------------------------------------------------
def _looks_like_data(path, min_bytes=8):
    try:
        with open(path, "rb") as fh:
            head = fh.read(8)
    except OSError:
        return False
    return head.startswith(HDF5_MAGIC) or head.startswith(NETCDF3_MAGIC)


def _looks_like_login_page(r):
    ctype = (r.headers.get("Content-Type") or "").lower()
    return "html" in ctype or "text/" in ctype


def download_file(session, url, out_dir, overwrite=False, max_retries=5,
                  verify=True, verify_body=True):
    """返回 (status, filename, message) status ∈ success/skipped/failed"""
    name = os.path.basename(urlparse(url).path) or "download.bin"
    final = os.path.join(out_dir, name)
    part = final + ".part"

    if os.path.exists(final) and not overwrite:
        if not verify_body or _looks_like_data(final):
            return "skipped", name, "已存在"
        os.remove(final)  # 之前存的假文件，删掉重下
    if os.path.exists(final) and overwrite:
        os.remove(final)

    last_err = ""
    for attempt in range(1, max_retries + 1):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with session.get(url, headers=headers, stream=True, timeout=(30, 300),
                             verify=verify, allow_redirects=True) as r:
                if r.status_code == 401:
                    raise AuthError(
                        "401 —— 认证没通过（缺凭据，或账号未批准 "
                        "“NASA GESDISC DATA ARCHIVE” 应用）"
                    )
                if r.status_code == 416 and have:  # 已经下完
                    os.replace(part, final)
                    return "success", name, "续传完成"
                if r.status_code in (429, 500, 502, 503, 504):
                    wait = int(r.headers.get("Retry-After", 0) or 0) or min(60, 2 ** attempt)
                    last_err = f"HTTP {r.status_code}，{wait}s 后重试"
                    time.sleep(wait)
                    continue
                r.raise_for_status()

                if verify_body and _looks_like_login_page(r) and "nc" in name:
                    raise AuthError("服务端返回的是网页（登录/EULA 页），不是数据文件")

                remaining = int(r.headers.get("Content-Length") or 0)
                total = have + remaining if remaining else 0
                mode = "ab" if (have and r.status_code == 206) else "wb"
                got = 0
                with open(part, mode) as fh:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        if not chunk:
                            continue
                        fh.write(chunk)
                        got += len(chunk)
                if total and os.path.getsize(part) != total:
                    raise IOError(f"大小不符：应为 {total}，实得 {os.path.getsize(part)}")

            if verify_body and not _looks_like_data(part):
                os.remove(part)
                raise IOError("下载内容不是 NetCDF/HDF5，可能是错误页")
            os.replace(part, final)
            return "success", name, f"{os.path.getsize(final)/1e6:.1f} MB"
        except AuthError:
            if os.path.exists(part):
                os.remove(part)
            raise
        except Exception as exc:
            last_err = str(exc)
            if attempt < max_retries:
                time.sleep(min(30, 2 ** attempt))
    return "failed", name, last_err


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        description="下载 GPCP / GES DISC 数据（带 Earthdata 认证）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  python download_files_GPCPDAY_3.3_authed.py --write-netrc
  python download_files_GPCPDAY_3.3_authed.py --check
  python download_files_GPCPDAY_3.3_authed.py --start 2000-01-01 --end 2000-12-31
  python download_files_GPCPDAY_3.3_authed.py --dataset GPCPMON --version 3.3 --start 1983-01-01 --end 1983-12-31
""")
    p.add_argument("--dataset", default=SHORT_NAME, help=f"CMR short_name，默认 {SHORT_NAME}")
    p.add_argument("--version", default=VERSION, help=f"数据集版本，默认 {VERSION}")
    p.add_argument("--start", default="2000-01-01", help="起始日期 YYYY-MM-DD，默认 2000-01-01")
    p.add_argument("--end", default="2000-12-31", help="结束日期 YYYY-MM-DD，默认 2000-12-31")
    p.add_argument("--bbox", default="", help='裁剪，格式 "minLon,minLat,maxLon,maxLat"')
    p.add_argument("--out", default="", help="下载目录，默认 ./<short_name>_<version>")
    p.add_argument("--workers", type=int, default=4, help="并发数，默认 4（GES DISC 建议 ≤4）")
    p.add_argument("--limit", type=int, default=0, help="只下载前 N 个（试跑用）")
    p.add_argument("--overwrite", action="store_true", help="覆盖已存在文件")
    p.add_argument("--no-verify-body", action="store_true", help="不校验文件头（不建议）")
    p.add_argument("--netrc", default="", help=f"凭据文件路径，默认 {DEFAULT_NETRC}")
    p.add_argument("--user", default="", help="Earthdata 用户名（不推荐，会留在历史记录）")
    p.add_argument("--password", default="", help="Earthdata 密码（不推荐）")
    p.add_argument("--write-netrc", action="store_true", help="交互式写入 _netrc 后退出")
    p.add_argument("--check", action="store_true", help="只做认证自检")
    p.add_argument("--list-only", action="store_true", help="只列出 URL 不下载")
    p.add_argument("--insecure", action="store_true", help="跳过 TLS 校验（仅代理做 MITM 时用）")
    p.add_argument("--no-proxy", action="store_true", help="忽略 HTTP(S)_PROXY 环境变量")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.write_netrc:
        return write_netrc(args.netrc or DEFAULT_NETRC, args.user or None,
                           args.password or None)

    print(f"解释器：{sys.executable}（Python {sys.version.split()[0]}）")

    user, password, source = resolve_credentials(args)
    if not (user and password):
        if args.list_only:
            # 列清单只查 CMR，不需要登录
            print("（未配置凭据：只查 CMR 清单，不下载）")
            user, password, source = "", "", "无（--list-only）"
        else:
            print("❌ 没找到 Earthdata 凭据。")
            print(f"   预期文件：{DEFAULT_NETRC}")
            print("   一键生成：python %s --write-netrc" % os.path.basename(__file__))
            print(f"   并确认已在 {URAL_PROFILE} 批准 “NASA GESDISC DATA ARCHIVE” 应用。")
            return 2

    if user:
        masked = user[:2] + "*" * max(0, len(user) - 2)
        print(f"凭据来源：{source}（用户 {masked}）")

    verify = not args.insecure
    if not verify:
        print("⚠️  已关闭 TLS 校验")

    session = EarthdataSession(user, password, verify=verify,
                               trust_proxy=not args.no_proxy)

    if args.check:
        return 0 if check(session, verify) else 1

    params = {}
    if args.start and args.end:
        params["temporal"] = f"{args.start}T00:00:00Z,{args.end}T23:59:59Z"
    if args.bbox:
        params["bounding_box"] = args.bbox

    out_dir = args.out or f"./{args.dataset}_{args.version}"
    os.makedirs(out_dir, exist_ok=True)

    total = count_granules(session, args.dataset, args.version, **params)
    print(f"命中 granule：{total:,}  -> {out_dir}")

    urls = collect_urls(session, args.dataset, args.version, total, **params)
    if args.list_only:
        for u in urls:
            print(u)
        return 0
    if not urls:
        print("没有可下载的文件。")
        return 1
    if args.limit:
        urls = urls[:args.limit]

    ok = skip = fail = 0
    failures = []
    auth_failed = False
    bar = tqdm(total=len(urls), desc="下载", unit="file") if tqdm else None
    try:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {
                pool.submit(download_file, session, u, out_dir, args.overwrite,
                            5, verify, not args.no_verify_body): u
                for u in urls
            }
            for fut in as_completed(futures):
                try:
                    status, name, msg = fut.result()
                except AuthError as exc:
                    fail += 1
                    if not auth_failed:
                        auth_failed = True
                        print(f"\n❌ 认证失败，已停止其余下载：{exc}")
                        print("   先跑 --check 定位；凭据写好后重跑本命令即可（会自动续传）。")
                        for f in futures:
                            f.cancel()
                    if bar:
                        bar.update(1)
                    continue
                except Exception as exc:  # 兜底，别让一个文件炸掉整批
                    fail += 1
                    failures.append((os.path.basename(futures[fut]), repr(exc)))
                    if bar:
                        bar.update(1)
                    continue
                if status == "success":
                    ok += 1
                elif status == "skipped":
                    skip += 1
                else:
                    fail += 1
                    failures.append((name, msg))
                    print(f"\n❌ {name}: {msg}")
                if bar:
                    bar.update(1)
                    bar.set_description(f"✅{ok} ⏭{skip} ❌{fail}")
    except KeyboardInterrupt:
        print("\n已中断（已下载部分保留，重跑会续传）。")
    finally:
        if bar:
            bar.close()

    print(f"\n完成：成功 {ok}，跳过 {skip}，失败 {fail}")
    if auth_failed:
        print("⚠️  本次是认证问题，不是网络问题：先 python "
              f"{os.path.basename(__file__)} --check")
    if failures:
        print("失败列表：")
        for name, msg in failures[:20]:
            print(f"  - {name}: {msg}")
        if len(failures) > 20:
            print(f"  ... 另外 {len(failures) - 20} 个")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
