Assignment 01

**Name: 肖文赜**

**SUSTech ID: 12631523**

## Flowchart

**[10 points]** Write a function `Print_values` with arguments `a`, `b`, and `c` to reflect the following flowchart. Here the purple parallelogram operator is to print values in the given order. Report your output with some random `a`, `b`, and `c` values.

<img src="https://zhu-group.github.io/ese5023/figs/flowchart_a1.png" width="400">

**解题思路：**题目中有提到purple parallelogram operator is to print values in the given order。比较后发现，经过一系列的判断，会将数字从大到小进行输出。例如a>b为False，b＞c为False，则可推出c＞b＞a，按顺序输出c，b，a。同时注意到题目给的流程图中，判断a＞b为False后再判断b＞c为True后，没有往下接流程图，结合题目意思，考虑补充流程图。如下图所示：

![79147109597](PS1.assets/1791471095976.png)

**程序：**PS1_1.py

```python
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 22:52:53 2026
@author: 55471
"""
def Print_values(a,b,c):
    if(a>b):
        if(b>c):
            print(a,b,c)    
        else:
            if(a>c):
                print(a,c,b)
            else:
                print(c,a,b)
    else:
        if(b>c):
            if(a>c):
                print(b,a,c)
            else:
                print(b,c,a)
            
        else:
            print(c,b,a)
    return 

##主函数
import random
a=random.random()
b=random.random()
c=random.random()
print('random number a is:' + str(a))
print('random number b is:' + str(b))
print('random number c is:' + str(c))
Print_values(a,b,c)
```

**输入样例与输出结果报告：**

**Test#1**

| Input#1                                                      | Output#1                                                     |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| random number a is:0.1376348026894113<br />random number b is:0.9387575523534156<br />random number c is:0.6942940658437009 | 0.9387575523534156 <br />0.6942940658437009 <br />0.1376348026894113 |

**Test#2**

| Input#2                                                      | Output#2                                                     |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| random number a is:0.47702960150601437<br />random number b is:0.3393952645687328<br />random number c is:0.35997666397802863 | 0.47702960150601437 <br />0.35997666397802863 <br />0.3393952645687328 |

**Test#3**

| Input#3                                                      | Output#3                                                     |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| random number a is:0.3022115485341458<br />random number b is:0.237463675493091<br />random number c is:0.7472706790794602 | 0.7472706790794602<br />0.3022115485341458 <br />0.237463675493091 |

程序能够实现要求，对输入数字按指定顺序输出

## Matrix multiplication

**2.1 [5 points]** Make two matrices `M1` (`5` rows and `10` columns ) and `M2` (`10` rows and `5` columns ); both are filled with random integers from `0` and `50`.

**2.2 [10 points]** Write a function `Matrix_multip` to do matrix multiplication, *i.e.*, `M1 * M2`. Here you are **ONLY** allowed to use `for` loop, `*` operator, and `+` operator.



解题思路：







## Dynamic programming

**5.1 [30 points]** Write a function `Find_expression`, which should be able to print every possible solution that makes the expression evaluate to a random integer from `1` to `100`. For example, `Find_expression(50)` should print lines include:
$$
1−2+34+5+6+7+8−9=50
$$
and
$$
1+2+34−56+78−9=50
$$
**5.2 [5 points]** Count the total number of suitable solutions for any integer *i* from `1` to `100`, assign the count to a list called `Total_solutions`. Plot the list `Total_solutions`, so which number(s) yields the maximum and minimum of `Total_solutions`?

**解题思路：**对于5.1。实际上就是需要往1 2 3 4 5 6 7 8 9里面放加号和减号，一共有8个空位可以填东西，每个空位要么放加号，要么放减号，要么什么都不放。所以初步的思路是写一个8层for循环，每层循环枚举三种情况，枚举出总共3^8种情况，在最后一层循环内汇总结果，进行字符串的拼接，计算，判断结果是否等于目标值，再输出结果。但是代码比较不好看。

在这基础上可以简化一下，把这个看做一个递推的过程，从上到下总共进行8层的选择，每层选择做一件事（放加号，放减号，什么都不放），例如第一层可以产生1+，1-，1□的结果，每层又都可以产生一个分支进入第二层选择，例如1+可以产生1+2+，1+2-和1+2□，而1-可以产生1-2+，1-2-和1-2□，1□可以产生12+，12-，12□的结果，以此进行递推。直到第9层时计算一下结果并输出，返回一个表示有答案的1，可以考虑使用深度优先搜索**（本题使用的解法）**，递推枚举所有可能，递归返回计数结果。

据此也很自然可以想到另一种思路，上面提到了这是一个递推的过程，后一次产生的结果可以看做总是建立在前一次的结果之上。所以如果保存下了前一次所有的结果，那么就能产生后一次的结果。据此也可以考虑使用一个2层for循环，第一层for循环枚举8个层数，第二层for循环枚举保存的结果列表，每次循环，把结果列表中的所有字符串都取出来，进行上面所说的三个操作，随后再保存回新的结果列表，如此最后结束时也可枚举出所有的情况并计算出答案。

**程序：**PS1_5.py

**#Partial 5.1**

```python
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
Total_solutions = [0]
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
            print(fs + num_list[deep] + '=' + str(tar))
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
```

**#Partial 5.2**

```python
for i in range(1,101):
    Total_solutions.append(find_expression(i))


print(Total_solutions)

import matplotlib.pyplot as plt

# Get some data
x = range(1,101)
y = Total_solutions[1:101]

# Plot a line
plt.plot(x,y)

# Add x and y labels
plt.xlabel("Number")
plt.ylabel("Total_solutions")


# Show plot
plt.show
```

**输出结果报告：**

**#5.1**

12+3+4-56+78+9=50
12-3+45+6+7-8-9=50
12-3-4-5+67-8-9=50
1+2+34-56+78-9=50
1+2+34-5-6+7+8+9=50
1+2+3+4-56+7+89=50
1+2+3-4+56-7+8-9=50
1+2-34+5-6-7+89=50
1+2-3+4+56+7-8-9=50
1-23+4+5-6+78-9=50
1-23-4-5-6+78+9=50
1-2+34+5+6+7+8-9=50
1-2+34-5-67+89=50
1-2+3-45+6+78+9=50
1-2-34-5-6+7+89=50
1-2-3+4+56-7-8+9=50
1-2-3-4-5-6+78-9=50

17

以结果等于50为例，总共有17种情况，Find_expression函数能够给出具体的计算过程，以及总数统计结果。

**#5.2**

Total_Solution = [0, 26, 11, 18, 8, 21, 12, 17, 8, 22, 12, 21, 11, 16, 15, 20, 8, 17, 11, 20, 15, 16, 11, 23, 18, 13, 14, 21, 15, 19, 17, 14, 19, 19, 7, 14, 19, 19, 17, 18, 16, 17, 18, 10, 15, 26, 18, 15, 16, 12, 17, 19, 9, 17, 21, 16, 13, 14, 16, 17, 17, 11, 13, 22, 14, 13, 15, 15, 15, 17, 7, 14, 17, 15, 12, 13, 14, 14, 14, 10, 9, 19, 12, 13, 13, 12, 11, 12, 6, 12, 14, 16, 13, 11, 11, 10, 11, 7, 9, 17, 11]

其中$i=0$的情况并没有纳入考虑，所以Total_solution对应值为0。其他取值$i$从1到100都能获得对应的解

<img src="PS1.assets/1791476111298.png" width="400">

结合图片可以分析结果，当$i=1$或者$i=45$时，解的数量最多，有26种







片