# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 09:39:42 2026

@author: 55471
"""
## Matrix multiplication
##列表嵌套
##定义初始列表
import random
M1=[]
M2=[]
def Matrix_multip(M1,M2):
    ##保存结果
    ans_M=[]
    ##M1的第i行
    for i in range(5):
        ##M2的第j列
        sub_ans_M = []
        for j in range(5):
            ##总共有10个元素要进行计算
            ##temp_ans存储单次计算结果
            temp_ans = 0
            ##第k个元素
            for k in range(10):
                temp_ans = temp_ans + M1[i][k]*M2[k][j]
            sub_ans_M.append(temp_ans)
        ans_M.append(sub_ans_M)
    return ans_M


for i in range(5):
    M1_sub=[]
    for j in range(10):
        M1_sub.append(round(random.random()*50))
    M1.append(M1_sub)

for i in range(10):
    M2_sub=[]
    for j in range(5):
        M2_sub.append(round(random.random()*50))
    M2.append(M2_sub)

print(M1)
print(M2)

Matrix_multip(M1,M2)


