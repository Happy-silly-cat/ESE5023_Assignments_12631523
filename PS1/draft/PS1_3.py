# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 10:19:40 2026

@author: 55471
"""
def Pascal_triangle(k):
    ##初始化列表
    upper = []
    #第i层
    for i in range(1,k+1):
        #第i层有i个数字
        #初始化每层答案
        ans = []
        for j in range(1,i+1):
            #到达第k层需要输出
            if (j == 1): 
                ans.append(1)
            elif (j == i):
                ans.append(1)
                upper = ans.copy()
            else:
                ans.append(upper[j-1]+upper[j-2])
    return ans
    
k = round(float(input("Please enter the level:"))) 
Pascal_triangle(k)

