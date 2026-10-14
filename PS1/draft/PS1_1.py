# -*- coding: utf-8 -*-
"""
Created on Thu Oct  8 22:52:53 2026
@author: 55471
"""
def Print_values(a,b,c):
    if(a>b):
        if(b>c):
            print(a,b,c,sep=",")    
        else:
            if(a>c):
                print(a,c,b,sep=",")
            else:
                print(c,a,b,sep=",")
    else:
        if(b>c):
            if(a>c):
                print(b,a,c,sep=",")
            else:
                print(b,c,a,sep=",")
            
        else:
            print(c,b,a,sep=",")
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

# PS1_1 示例测试
print('Test#1')
print('输入结果为：3, 2, 1')
print('输出结果为：', end='')
Print_values(3, 2, 1)
print()

print('Test#2')
print('输入结果为：9, 2, 6')
print('输出结果为：', end='')
Print_values(9, 2, 6)
print()

print('Test#3')
print('输入结果为：4, 2, 7')
print('输出结果为：', end='')
Print_values(4, 2, 7)
print()

print('Test#4')
print('输入结果为：2, 6, 10')
print('输出结果为：', end='')
Print_values(2, 6, 10)
print()

print('Test#5')
print('输入结果为：2, 8, 5')
print('输出结果为：', end='')
Print_values(2, 8, 5)
print()
print()
