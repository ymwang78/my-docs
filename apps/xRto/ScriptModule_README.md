# XRto 脚本模块系统使用说明

## 概述

XRto 脚本模块系统允许用户将Python脚本作为可重用的模块来管理和执行。每个脚本可以注册为一个模块，提供特定的功能函数，并且可以在其他脚本中调用。

## 主要功能

### 1. 脚本执行
- 支持Python脚本的直接执行
- 通过PyBinding与C++后端交互
- 访问流程表模型、单元模型等

### 2. 模块管理
- 将脚本注册为可重用模块
- 模块的注册、注销和重新加载
- 模块函数的调用

### 3. 流程表操作
- 获取所有单元和连接
- 设置单元变量
- 分析流程表结构

## 使用方法

### 基本脚本执行

1. 在ScriptView中编写Python代码
2. 点击"执行"按钮或使用快捷键
3. 脚本通过PyBinding执行，可以访问以下对象：
   - `FlowSheet`: 流程表控制器
   - 各个单元模型（通过单元名称访问）

### 模块注册和使用

#### 注册模块
```python
# 在ScriptView中右键选择"注册为模块"
# 或者通过代码：
script_controller.registerScriptModule("my_module.py", script_content)
```

#### 调用模块函数
```python
# 通过ScriptController调用模块函数
script_controller.executeModuleFunction("my_module", "function_name", [arg1, arg2])
```

### 示例脚本结构

```python
# 模块初始化
def init_module():
    print("模块初始化")

# 业务函数
def my_function(param1, param2):
    # 访问流程表
    units = FlowSheet.getAllUnits()
    # 处理逻辑
    return result

# 主函数（可选）
def main():
    # 模块主要逻辑
    pass

# 自动初始化
init_module()

# 如果直接执行
if __name__ == "__main__":
    main()
```

## API 参考

### FlowSheetController (FlowSheet)
- `getAllUnits()`: 获取所有单元
- `getAllConnections()`: 获取所有连接
- `addUnit(...)`: 添加单元
- `addConnection(...)`: 添加连接

### UnitModel
- `name()`: 获取单元名称
- `id()`: 获取单元ID
- `getUnitModelTypeName()`: 获取单元类型
- `getInPorts()`: 获取输入端口
- `getOutPorts()`: 获取输出端口
- 变量访问：`unit.T.initx = value`

### Variable (xOptParsedVariable)
- `initx`: 初始值
- `current`: 当前值
- `lower`: 下限
- `upper`: 上限
- `unit`: 单位
- `name`: 变量名

## 示例模块

### 1. 基本单元操作
```python
def get_unit_by_name(unit_name):
    units = FlowSheet.getAllUnits()
    for unit in units:
        if unit.name() == unit_name:
            return unit
    return None

def set_temperature(unit_name, temperature):
    unit = get_unit_by_name(unit_name)
    if unit and hasattr(unit, 'T'):
        unit.T.initx = temperature
        return True
    return False
```

### 2. 批量操作
```python
def batch_set_variables(settings):
    """
    settings = {
        'unit_name': {'var_name': value, ...},
        ...
    }
    """
    results = {}
    for unit_name, variables in settings.items():
        unit = get_unit_by_name(unit_name)
        if unit:
            unit_results = {}
            for var_name, value in variables.items():
                if hasattr(unit, var_name):
                    getattr(unit, var_name).initx = value
                    unit_results[var_name] = True
                else:
                    unit_results[var_name] = False
            results[unit_name] = unit_results
    return results
```

### 3. 数据分析
```python
def analyze_flowsheet():
    units = FlowSheet.getAllUnits()
    connections = FlowSheet.getAllConnections()
    
    analysis = {
        'unit_count': len(units),
        'connection_count': len(connections),
        'unit_types': {}
    }
    
    for unit in units:
        unit_type = unit.getUnitModelTypeName()
        analysis['unit_types'][unit_type] = analysis['unit_types'].get(unit_type, 0) + 1
    
    return analysis
```

## 最佳实践

### 1. 模块设计
- 每个模块应该有明确的功能职责
- 提供清晰的函数接口
- 包含适当的错误处理

### 2. 错误处理
```python
def safe_operation():
    try:
        # 操作代码
        result = some_operation()
        return result
    except Exception as e:
        print(f"操作失败: {e}")
        return None
```

### 3. 日志记录
```python
def log_operation(operation_name, result):
    if result:
        print(f"[成功] {operation_name}")
    else:
        print(f"[失败] {operation_name}")
```

### 4. 模块文档
- 为每个函数提供文档字符串
- 说明参数类型和返回值
- 提供使用示例

## 注意事项

1. **线程安全**: 脚本执行在主线程中，避免长时间阻塞操作
2. **内存管理**: 大量数据处理时注意内存使用
3. **异常处理**: 始终包含适当的异常处理代码
4. **模块依赖**: 避免模块间的循环依赖

## 故障排除

### 常见问题

1. **模块注册失败**
   - 检查脚本语法是否正确
   - 确认模块名称有效
   - 查看错误日志

2. **函数调用失败**
   - 确认函数名称正确
   - 检查参数类型和数量
   - 验证模块是否已注册

3. **变量访问错误**
   - 确认单元存在
   - 检查变量名称
   - 验证变量类型

### 调试技巧

1. 使用`print()`输出调试信息
2. 检查ScriptController的日志输出
3. 验证PyBinding的连接状态
4. 测试简单的操作后再进行复杂操作

## 扩展开发

如需扩展脚本系统功能，可以：

1. 在PyBinding中添加新的C++类绑定
2. 扩展ScriptController的功能
3. 添加新的模块管理功能
4. 实现脚本间的通信机制

---

更多信息请参考源代码中的注释和示例。
