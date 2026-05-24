#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 runComputeTask 功能的脚本，包含日志文件功能演示
"""

import time
import os

def test_run_compute_task():
    """测试运行计算任务"""
    print("=== 测试 runComputeTask 功能 ===")
    
    # 测试参数
    task_name = "test_task"
    script_file = "example_compute_task.py"
    
    print(f"任务名称: {task_name}")
    print(f"脚本文件: {script_file}")
    
    # 检查脚本文件是否存在
    if not os.path.exists(script_file):
        print(f"错误: 脚本文件 {script_file} 不存在")
        return
    
    # 运行计算任务
    print("\n启动计算任务...")
    process_id = FlowSheet.runComputeTask(task_name, script_file)
    
    if process_id == -1:
        print("错误: 启动计算任务失败")
        return
    
    print(f"成功启动计算任务，进程ID: {process_id}")
    
    # 获取日志文件路径
    log_file = FlowSheet.getProcessLogFile(process_id, task_name)
    if log_file:
        print(f"日志文件路径: {log_file}")
    else:
        print("警告: 无法获取日志文件路径")
    
    # 监控进程状态
    print("\n监控进程状态...")
    max_wait_time = 30  # 最大等待30秒
    check_interval = 2  # 每2秒检查一次
    elapsed_time = 0
    
    while elapsed_time < max_wait_time:
        is_running = FlowSheet.isProcessRunning(process_id)
        print(f"时间: {elapsed_time}s - 进程 {process_id} 状态: {'运行中' if is_running else '已结束'}")
        
        if not is_running:
            print("进程已结束")
            break
            
        time.sleep(check_interval)
        elapsed_time += check_interval
    
    if elapsed_time >= max_wait_time:
        print(f"警告: 进程运行时间超过 {max_wait_time} 秒")
    
    # 进程结束后，尝试读取日志文件
    if log_file and os.path.exists(log_file):
        print(f"\n=== 日志文件内容 ({log_file}) ===")
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    print(content)
                else:
                    print("日志文件为空")
        except Exception as e:
            print(f"读取日志文件失败: {e}")
        print("=== 日志文件内容结束 ===")
    else:
        print("日志文件不存在或路径无效")
    
    print("\n=== 测试完成 ===")

def test_multiple_processes():
    """测试多个进程同时运行"""
    print("\n=== 测试多个进程同时运行 ===")
    
    script_file = "example_compute_task.py"
    if not os.path.exists(script_file):
        print(f"错误: 脚本文件 {script_file} 不存在")
        return
    
    # 启动多个进程
    processes = []
    for i in range(3):
        task_name = f"multi_task_{i+1}"
        print(f"启动任务: {task_name}")
        
        process_id = FlowSheet.runComputeTask(task_name, script_file)
        if process_id != -1:
            # 获取日志文件路径
            log_file = FlowSheet.getProcessLogFile(process_id, task_name)
            processes.append((process_id, task_name, log_file))
            print(f"  进程ID: {process_id}")
            if log_file:
                print(f"  日志文件: {log_file}")
        else:
            print(f"  启动失败")
    
    if not processes:
        print("没有成功启动的进程")
        return
    
    # 监控所有进程
    print(f"\n监控 {len(processes)} 个进程...")
    max_wait_time = 20
    check_interval = 3
    elapsed_time = 0
    
    while elapsed_time < max_wait_time and processes:
        print(f"\n--- 时间: {elapsed_time}s ---")
        
        # 检查每个进程的状态
        running_processes = []
        for process_id, task_name, log_file in processes:
            is_running = FlowSheet.isProcessRunning(process_id)
            status = "运行中" if is_running else "已结束"
            print(f"  {task_name} (PID: {process_id}): {status}")
            
            if is_running:
                running_processes.append((process_id, task_name, log_file))
        
        processes = running_processes
        
        if not processes:
            print("所有进程已结束")
            break
            
        time.sleep(check_interval)
        elapsed_time += check_interval
    
    if processes:
        print(f"\n警告: 仍有 {len(processes)} 个进程在运行")
        for process_id, task_name, log_file in processes:
            print(f"  {task_name} (PID: {process_id})")
    
    print("\n=== 多进程测试完成 ===")

def test_log_file_functionality():
    """专门测试日志文件功能"""
    print("\n=== 测试日志文件功能 ===")
    
    script_file = "example_compute_task.py"
    if not os.path.exists(script_file):
        print(f"错误: 脚本文件 {script_file} 不存在")
        return
    
    task_name = "log_test_task"
    print(f"启动任务: {task_name}")
    
    # 启动进程
    process_id = FlowSheet.runComputeTask(task_name, script_file)
    if process_id == -1:
        print("启动任务失败")
        return
    
    print(f"进程ID: {process_id}")
    
    # 立即尝试获取日志文件路径
    log_file = FlowSheet.getProcessLogFile(process_id, task_name)
    if log_file:
        print(f"日志文件路径: {log_file}")
        
        # 等待一段时间让进程产生输出
        print("等待进程产生输出...")
        time.sleep(5)
        
        # 尝试实时读取日志文件
        if os.path.exists(log_file):
            print(f"\n=== 实时日志内容 ===")
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        print(content)
                    else:
                        print("日志文件暂时为空")
            except Exception as e:
                print(f"读取日志文件失败: {e}")
        else:
            print("日志文件尚未创建")
    else:
        print("无法获取日志文件路径")
    
    # 等待进程结束
    print("\n等待进程结束...")
    max_wait = 15
    for i in range(max_wait):
        if not FlowSheet.isProcessRunning(process_id):
            print("进程已结束")
            break
        time.sleep(1)
    else:
        print("进程仍在运行")
    
    # 最终读取完整日志
    if log_file and os.path.exists(log_file):
        print(f"\n=== 最终日志内容 ===")
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    print(content)
                else:
                    print("日志文件为空")
        except Exception as e:
            print(f"读取日志文件失败: {e}")
    
    print("\n=== 日志文件功能测试完成 ===")

if __name__ == "__main__":
    # 确保 FlowSheet 对象可用
    if 'FlowSheet' not in globals():
        print("错误: FlowSheet 对象不可用")
        print("请在 xRto 环境中运行此脚本")
    else:
        test_run_compute_task()
        test_multiple_processes()
        test_log_file_functionality()
