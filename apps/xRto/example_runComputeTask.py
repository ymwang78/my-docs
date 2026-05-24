#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例脚本：演示如何在Python中使用runComputeTask函数的新参数

这个脚本展示了如何通过Python API启动计算任务，
包括设置超时和传递参数给子脚本。
"""

import time
import os


def example_basic_task(controller):
    """示例1：运行基本计算任务（不带脚本）"""
    print("=" * 60)
    print("示例1：运行基本计算任务")
    print("=" * 60)
    
    # 只运行计算任务，不执行脚本
    task_name = "optimization_task"
    process_id = controller.runComputeTask(task_name)
    
    if process_id > 0:
        print(f"计算任务已启动，进程ID: {process_id}")
        return process_id
    else:
        print("启动计算任务失败！")
        return -1


def example_task_with_script(controller):
    """示例2：运行计算任务并执行脚本"""
    print("\n" + "=" * 60)
    print("示例2：运行计算任务并执行脚本")
    print("=" * 60)
    
    task_name = "optimization_task"
    script_file = "process_script.py"  # 脚本文件路径
    
    process_id = controller.runComputeTask(
        task_name,
        scriptFile=script_file
    )
    
    if process_id > 0:
        print(f"计算任务已启动，进程ID: {process_id}")
        print(f"将执行脚本: {script_file}")
        return process_id
    else:
        print("启动计算任务失败！")
        return -1


def example_task_with_timeout(controller):
    """示例3：运行计算任务并设置超时"""
    print("\n" + "=" * 60)
    print("示例3：运行计算任务并设置超时")
    print("=" * 60)
    
    task_name = "optimization_task"
    script_file = "long_running_script.py"
    timeout = 300  # 5分钟超时
    
    process_id = controller.runComputeTask(
        task_name,
        scriptFile=script_file,
        timeOutSeconds=timeout
    )
    
    if process_id > 0:
        print(f"计算任务已启动，进程ID: {process_id}")
        print(f"超时设置: {timeout}秒")
        return process_id
    else:
        print("启动计算任务失败！")
        return -1


def example_task_with_arguments(controller):
    """示例4：运行计算任务并传递参数给脚本"""
    print("\n" + "=" * 60)
    print("示例4：运行计算任务并传递参数给脚本")
    print("=" * 60)
    
    task_name = "optimization_task"
    script_file = "parameterized_script.py"
    
    # 构建参数字符串
    script_args = "iterations=100,tolerance=0.001,output=result.csv,mode=production"
    
    process_id = controller.runComputeTask(
        task_name,
        scriptFile=script_file,
        scriptArg=script_args
    )
    
    if process_id > 0:
        print(f"计算任务已启动，进程ID: {process_id}")
        print(f"传递的参数: {script_args}")
        return process_id
    else:
        print("启动计算任务失败！")
        return -1


def example_full_featured(controller):
    """示例5：使用所有参数"""
    print("\n" + "=" * 60)
    print("示例5：使用所有参数的完整示例")
    print("=" * 60)
    
    task_name = "complex_optimization"
    script_file = "advanced_optimization.py"
    timeout = 1800  # 30分钟超时
    script_args = "maxIterations=500,convergenceTol=1e-6,outputDir=results,verbose=true"
    
    process_id = controller.runComputeTask(
        task_name,
        scriptFile=script_file,
        timeOutSeconds=timeout,
        scriptArg=script_args
    )
    
    if process_id > 0:
        print(f"计算任务已启动，进程ID: {process_id}")
        print(f"脚本文件: {script_file}")
        print(f"超时设置: {timeout}秒 ({timeout/60:.1f}分钟)")
        print(f"脚本参数: {script_args}")
        return process_id
    else:
        print("启动计算任务失败！")
        return -1


def monitor_process(controller, process_id, task_name):
    """监控进程运行状态"""
    print("\n" + "-" * 60)
    print(f"监控进程 {process_id}")
    print("-" * 60)
    
    # 获取日志文件路径
    log_file = controller.getProcessLogFile(process_id, task_name)
    if log_file:
        print(f"日志文件: {log_file}")
    
    # 检查进程是否仍在运行
    check_count = 0
    max_checks = 10  # 最多检查10次
    
    while check_count < max_checks:
        is_running = controller.isProcessRunning(process_id)
        
        if is_running:
            print(f"进程 {process_id} 仍在运行... ({check_count + 1}/{max_checks})")
            time.sleep(2)  # 等待2秒
            check_count += 1
        else:
            print(f"进程 {process_id} 已完成")
            break
    
    if check_count >= max_checks:
        print(f"监控结束（已检查{max_checks}次，进程可能仍在运行）")
    
    # 如果有日志文件，尝试读取最后几行
    if log_file and os.path.exists(log_file):
        print("\n日志文件最后几行:")
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_lines = lines[-10:] if len(lines) > 10 else lines
                for line in last_lines:
                    print("  " + line.rstrip())
        except Exception as e:
            print(f"  无法读取日志文件: {e}")


def batch_run_tasks(controller):
    """示例6：批量运行多个任务"""
    print("\n" + "=" * 60)
    print("示例6：批量运行多个任务")
    print("=" * 60)
    
    tasks = [
        {
            "name": "task1",
            "script": "script1.py",
            "timeout": 300,
            "args": "param1=value1"
        },
        {
            "name": "task2",
            "script": "script2.py",
            "timeout": 600,
            "args": "param2=value2,param3=value3"
        },
        {
            "name": "task3",
            "script": "script3.py",
            "timeout": 900,
            "args": "mode=fast,iterations=50"
        }
    ]
    
    process_ids = []
    
    for task in tasks:
        print(f"\n启动任务: {task['name']}")
        process_id = controller.runComputeTask(
            task["name"],
            scriptFile=task["script"],
            timeOutSeconds=task["timeout"],
            scriptArg=task["args"]
        )
        
        if process_id > 0:
            print(f"  进程ID: {process_id}")
            print(f"  超时: {task['timeout']}秒")
            print(f"  参数: {task['args']}")
            process_ids.append(process_id)
        else:
            print(f"  启动失败！")
    
    print(f"\n已启动 {len(process_ids)} 个任务")
    return process_ids


def main():
    """
    主函数
    
    注意：这个脚本需要在xRto的Python环境中运行，
    并且需要有一个有效的FlowSheetController实例。
    """
    print("runComputeTask 函数使用示例")
    print("=" * 60)
    
    # 在实际使用中，controller应该是从xRto环境中获取的
    # 这里只是展示API的使用方法
    
    # 假设我们已经有了controller实例
    # controller = ... (从xRto环境获取)
    
    print("\n请参考以上示例函数，了解如何使用runComputeTask的各种参数：")
    print("1. example_basic_task() - 基本用法")
    print("2. example_task_with_script() - 执行脚本")
    print("3. example_task_with_timeout() - 设置超时")
    print("4. example_task_with_arguments() - 传递参数")
    print("5. example_full_featured() - 完整功能")
    print("6. batch_run_tasks() - 批量运行")
    print("7. monitor_process() - 监控进程")
    
    print("\n在xRto的Python脚本中使用示例：")
    print("-" * 60)
    print("""
# 获取控制器实例
controller = getFlowSheetController()

# 运行任务
process_id = controller.runComputeTask(
    "my_task",
    scriptFile="my_script.py",
    timeOutSeconds=600,
    scriptArg="param1=value1,param2=value2"
)

# 检查进程状态
if process_id > 0:
    print(f"任务已启动，进程ID: {process_id}")
    
    # 监控进程
    while controller.isProcessRunning(process_id):
        print("任务运行中...")
        time.sleep(5)
    
    print("任务完成！")
""")


if __name__ == '__main__':
    main()


