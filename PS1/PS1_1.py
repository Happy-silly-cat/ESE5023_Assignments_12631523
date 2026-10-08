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
