#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例计算任务脚本 - 用于测试日志重定向功能
这个脚本会产生stdout和stderr输出，用于验证日志重定向是否正常工作
"""

import time
import sys
import os

def main():
    """主函数 - 产生各种输出用于测试日志功能"""
    print("=== 计算任务开始 ===")
    print(f"脚本路径: {__file__}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python版本: {sys.version}")
    print(f"进程ID: {os.getpid()}")
    
    # 输出到stdout
    print("\n开始执行计算任务...")
    sys.stdout.flush()  # 强制刷新输出缓冲区
    
    # 模拟计算过程，产生多种输出
    for i in range(5):
        print(f"步骤 {i+1}/5: 正在处理数据...")
        sys.stdout.flush()
        
        # 模拟一些计算
        time.sleep(1)
        
        # 计算结果
        result = (i + 1) * 10 + i * 5
        print(f"  计算结果: {result}")
        
        # 偶尔输出到stderr进行测试
        if i == 2:
            print(f"警告: 这是一个测试警告信息 (步骤 {i+1})", file=sys.stderr)
            sys.stderr.flush()
    
    # 输出一些统计信息
    print("\n=== 任务统计 ===")
    print("处理的步骤数: 5")
    print("总耗时: 约5秒")
    print("状态: 成功完成")
    
    # 测试错误输出
    print("测试错误输出: 这不是真正的错误", file=sys.stderr)
    sys.stderr.flush()
    
    print("\n计算任务完成!")
    print("=== 任务结束 ===")
    sys.stdout.flush()

def test_flowsheet_access():
    """测试是否能访问FlowSheet对象"""
    print("\n=== 测试FlowSheet访问 ===")
    
    if 'FlowSheet' in globals():
        print("✓ FlowSheet对象可用")
        try:
            # 尝试获取一些基本信息
            units = FlowSheet.getAllUnits()
            print(f"当前工程包含 {len(units)} 个单元")
            
            connections = FlowSheet.getAllConnections()
            print(f"当前工程包含 {len(connections)} 个连接")
            
        except Exception as e:
            print(f"访问FlowSheet时发生错误: {e}", file=sys.stderr)
    else:
        print("✗ FlowSheet对象不可用")
        print("这可能是因为脚本在独立的xRto进程中运行", file=sys.stderr)

def simulate_long_running_task():
    """模拟长时间运行的任务"""
    print("\n=== 模拟长时间任务 ===")
    
    total_steps = 10
    for step in range(total_steps):
        progress = (step + 1) / total_steps * 100
        print(f"进度: {progress:.1f}% ({step + 1}/{total_steps})")
        
        # 模拟工作
        time.sleep(0.5)
        
        # 每隔几步输出详细信息
        if (step + 1) % 3 == 0:
            print(f"  详细信息: 已完成第 {step + 1} 个子任务")
            sys.stdout.flush()
    
    print("长时间任务完成!")

if __name__ == "__main__":
    try:
        main()
        test_flowsheet_access()
        simulate_long_running_task()
        
        print("\n所有测试完成，脚本正常退出")
        
    except Exception as e:
        print(f"脚本执行过程中发生错误: {e}", file=sys.stderr)
        sys.stderr.flush()
        sys.exit(1)
