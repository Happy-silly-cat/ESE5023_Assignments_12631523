# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 23:37:27 2026

@author: 55471
"""
##考虑深度优先搜索
##穷尽位置即可，总共有8个位置可以插入符号
##每个位置有3种选择，什么都不做，插入加号，插入减号
##1 2 3 4 5 6 7 8 9
##初始化数字列表以及存储答案的列表
num_list = ['0','1','2','3','4','5','6','7','8','9']
ans = [0]
##计算函数
def cal(symb,res,temp):
    if(symb == 0):
        res = res + float(temp)
    else:
        res = res - float(temp)
    return res

##tar表示答案，deep为深度，symb=0,1表示加法和减法，res表示当前答案,temp表示临时截断的答案,fs用于输出完整字符串
def find_expression(tar,deep = 1,symb = 0,res = 0,temp = '',fs = ''):
    ##深度等于9最终结算
    if(deep == 9):
        res = cal(symb,res,temp+num_list[deep])
        if(res == tar):
            #print(fs + num_list[deep] + '=' + str(tar))
            return 1
        return 0
    ##接下来，什么都不做，那就接着把数字补全
    count1 = find_expression(tar,deep+1,symb = symb,res = res,temp = temp + num_list[deep] ,fs=fs + num_list[deep])
    ##接下来加，数字截断，进行一次cal结算
    count2 = find_expression(tar,deep+1,symb = 0,res = cal(symb,res,temp + num_list[deep]),temp = '',fs = fs + num_list[deep] + "+")
    ##接下来减，数字截断，进行一次cal结算
    count3 = find_expression(tar,deep+1,symb = 1,res = cal(symb,res,temp + num_list[deep]),temp = '',fs = fs + num_list[deep] + "-")
    return count1 + count2 + count3

find_expression(50)