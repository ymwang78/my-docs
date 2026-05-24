#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例脚本：演示如何在计算模式下使用scriptArg参数

使用方法：
xRto.exe --computeTask myTask --projectFile project.xrto \
         --scriptFile example_script.py \
         --scriptArg "iterations=100,tolerance=0.001,output=result.csv"
"""

import os
import sys

def parse_script_args(arg_string):
    """解析scriptArg参数字符串"""
    params = {}
    if not arg_string:
        return params
    
    # 支持逗号分隔的key=value格式
    for item in arg_string.split(','):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            params[key.strip()] = value.strip()
        else:
            # 如果没有等号，使用索引作为key
            params[f'arg_{len(params)}'] = item
    
    return params

def main():
    print("=" * 60)
    print("计算模式脚本示例")
    print("=" * 60)
    
    # 获取传入的脚本参数
    script_arg = os.environ.get('XRTO_SCRIPT_ARG', '')
    print(f"\n接收到的原始参数: '{script_arg}'")
    
    # 解析参数
    params = parse_script_args(script_arg)
    print(f"\n解析后的参数:")
    for key, value in params.items():
        print(f"  {key} = {value}")
    
    # 使用参数（带默认值）
    iterations = int(params.get('iterations', '10'))
    tolerance = float(params.get('tolerance', '0.01'))
    output_file = params.get('output', 'default_output.csv')
    mode = params.get('mode', 'normal')
    
    print(f"\n使用的配置:")
    print(f"  迭代次数: {iterations}")
    print(f"  容差: {tolerance}")
    print(f"  输出文件: {output_file}")
    print(f"  运行模式: {mode}")
    
    # 这里可以添加实际的计算逻辑
    print(f"\n开始执行计算...")
    print(f"模拟进行 {iterations} 次迭代...")
    
    # 模拟计算过程
    for i in range(min(5, iterations)):  # 只打印前5次
        print(f"  迭代 {i+1}/{iterations}")
    
    if iterations > 5:
        print(f"  ... (省略 {iterations-5} 次迭代)")
    
    print(f"\n计算完成!")
    print(f"结果已保存到: {output_file}")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


