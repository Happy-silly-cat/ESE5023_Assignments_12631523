# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 10:44:54 2026

@author: 55471
"""
def Least_moves(x):
    cnt=[0,0]
    for i in range(2,x+1):
        if i%2 ==0:
            cnt.append(min(cnt[i-1]+1,cnt[i//2]+1))
        else:
            cnt.append(cnt[i-1]+1)
    return cnt[x]
    
x=int(input('Please enter your RMB:'))
Least_moves(x)

"""
def Least_moves(x):
    cnt=0
    while(x>1):
        if(x%2==0):
            x=x//2
            cnt=cnt+1
        else:
            x=x-1
            cnt=cnt+1
    return cnt
"""