#!/usr/bin/env lua
--[[
示例脚本：演示如何在计算模式下使用scriptArg参数（Lua版本）

使用方法：
xRto.exe --computeTask myTask --projectFile project.xrto \
         --scriptFile example_script.lua \
         --scriptArg "iterations=100,tolerance=0.001,output=result.csv"
--]]

-- 解析scriptArg参数字符串
function parse_script_args(arg_string)
    local params = {}
    if not arg_string or arg_string == "" then
        return params
    end
    
    -- 支持逗号分隔的key=value格式
    for item in string.gmatch(arg_string, "[^,]+") do
        item = item:match("^%s*(.-)%s*$")  -- 去除首尾空格
        
        local key, value = string.match(item, "([^=]+)=(.+)")
        if key and value then
            key = key:match("^%s*(.-)%s*$")
            value = value:match("^%s*(.-)%s*$")
            params[key] = value
        else
            -- 如果没有等号，使用索引作为key
            local idx = 0
            for _ in pairs(params) do idx = idx + 1 end
            params["arg_" .. idx] = item
        end
    end
    
    return params
end

function main()
    print(string.rep("=", 60))
    print("计算模式脚本示例 (Lua)")
    print(string.rep("=", 60))
    
    -- 获取传入的脚本参数
    local script_arg = os.getenv('XRTO_SCRIPT_ARG') or ''
    print(string.format("\n接收到的原始参数: '%s'", script_arg))
    
    -- 解析参数
    local params = parse_script_args(script_arg)
    print("\n解析后的参数:")
    for key, value in pairs(params) do
        print(string.format("  %s = %s", key, value))
    end
    
    -- 使用参数（带默认值）
    local iterations = tonumber(params.iterations) or 10
    local tolerance = tonumber(params.tolerance) or 0.01
    local output_file = params.output or 'default_output.csv'
    local mode = params.mode or 'normal'
    
    print("\n使用的配置:")
    print(string.format("  迭代次数: %d", iterations))
    print(string.format("  容差: %.6f", tolerance))
    print(string.format("  输出文件: %s", output_file))
    print(string.format("  运行模式: %s", mode))
    
    -- 这里可以添加实际的计算逻辑
    print(string.format("\n开始执行计算..."))
    print(string.format("模拟进行 %d 次迭代...", iterations))
    
    -- 模拟计算过程
    local show_count = math.min(5, iterations)
    for i = 1, show_count do
        print(string.format("  迭代 %d/%d", i, iterations))
    end
    
    if iterations > 5 then
        print(string.format("  ... (省略 %d 次迭代)", iterations - 5))
    end
    
    print("\n计算完成!")
    print(string.format("结果已保存到: %s", output_file))
    print(string.rep("=", 60))
    
    return 0
end

-- 执行主函数
local status, err = pcall(main)
if not status then
    print(string.format("\n错误: %s", err))
    os.exit(1)
end


