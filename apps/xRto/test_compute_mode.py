#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试计算模式的Python脚本
"""

print("开始执行测试脚本...")
print("这是一个测试计算任务的脚本")

# 模拟一些计算操作
import time
import math

print("执行计算操作...")
result = 0
for i in range(10):
    result += math.sin(i) * math.cos(i)
    time.sleep(0.1)  # 模拟计算时间
    print(f"计算进度: {(i+1)*10}%")

print(f"计算完成，结果: {result}")
print("脚本执行结束")
