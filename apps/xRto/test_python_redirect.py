#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Python输出重定向功能的脚本
"""

import sys
import time

def test_print_output():
    """测试print输出重定向"""
    print("=== 测试Python输出重定向 ===")
    print("这是一条普通的print输出")
    print("支持中文输出：你好，世界！")
    print("支持数字输出：", 123, 456.789)
    print("支持多参数输出：", "参数1", "参数2", 42)
    
def test_stderr_output():
    """测试stderr输出重定向"""
    print("=== 测试stderr输出重定向 ===")
    sys.stderr.write("这是stderr输出\n")
    sys.stderr.write("stderr中文输出：错误信息\n")
    
def test_exception_output():
    """测试异常输出重定向"""
    print("=== 测试异常输出重定向 ===")
    try:
        1 / 0
    except ZeroDivisionError as e:
        print(f"捕获到异常: {e}")
        
def test_loop_output():
    """测试循环输出"""
    print("=== 测试循环输出 ===")
    for i in range(5):
        print(f"循环输出 {i+1}/5")
        time.sleep(0.1)  # 短暂延迟以观察实时输出
        
def test_formatted_output():
    """测试格式化输出"""
    print("=== 测试格式化输出 ===")
    name = "xRto"
    version = "2.0"
    print(f"软件名称: {name}")
    print(f"版本号: {version}")
    print("格式化数字: {:.2f}".format(3.14159))

if __name__ == "__main__":
    print("开始测试Python输出重定向功能...")
    
    test_print_output()
    test_stderr_output()
    test_exception_output()
    test_loop_output()
    test_formatted_output()
    
    print("测试完成！")
