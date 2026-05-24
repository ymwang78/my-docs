# runComputeTask 函数更新说明

## 更新日期
2025年10月14日

## 更新概述
为`runComputeTask`函数添加了两个新参数：`timeOutSeconds`（超时控制）和`scriptArg`（脚本参数传递）。

## 修改的文件

### 1. Controller/FlowSheetController.h
**修改内容：**
- 更新函数签名，添加`timeOutSeconds`和`scriptArg`参数
- 所有新参数都有默认值，保持向后兼容

**修改前：**
```cpp
qint64 runComputeTask(const std::string& computeTaskName, const std::string& scriptFile);
```

**修改后：**
```cpp
qint64 runComputeTask(const std::string& computeTaskName, 
                     const std::string& scriptFile = "",
                     int timeOutSeconds = 0,
                     const std::string& scriptArg = "");
```

### 2. Controller/FlowSheetController.cpp
**修改内容：**
- 实现新参数的处理逻辑
- 在命令行参数中添加`--timeOut`和`--scriptArg`选项

**新增代码：**
```cpp
if (timeOutSeconds > 0)
    arguments << "--timeOut" << QString::number(timeOutSeconds);

if (!scriptArg.empty())
    arguments << "--scriptArg" << QString::fromStdString(scriptArg);
```

### 3. PyBinding/PyBinding.cpp
**修改内容：**
- 更新Python绑定，添加新参数
- 添加详细的函数文档字符串

**修改前：**
```cpp
.def("runComputeTask", &FlowSheetController::runComputeTask,
     py::arg("computeTaskName"), py::arg("scriptFile"),
     "Run a compute task...")
```

**修改后：**
```cpp
.def("runComputeTask", &FlowSheetController::runComputeTask,
     py::arg("computeTaskName"), 
     py::arg("scriptFile") = "", 
     py::arg("timeOutSeconds") = 0, 
     py::arg("scriptArg") = "",
     "Run a compute task in a new xRto process with the current project file.\n"
     "Args:\n"
     "    computeTaskName: Name of the compute task to run\n"
     "    scriptFile: Optional script file to execute (Python or Lua)\n"
     "    timeOutSeconds: Optional timeout in seconds (0 = no timeout)\n"
     "    scriptArg: Optional string argument passed to script via XRTO_SCRIPT_ARG env var\n"
     "Returns:\n"
     "    Process ID or -1 if failed.")
```

## 新功能说明

### 1. timeOutSeconds 参数
- **类型：** `int`
- **默认值：** `0`（无超时）
- **功能：** 设置子进程的运行超时时间（秒）
- **行为：** 
  - 当值 > 0 时，子进程将在指定秒数后自动退出（退出码-2）
  - 当值 = 0 时，不设置超时限制
- **用途：** 防止任务运行时间过长，适用于有时间限制的场景

### 2. scriptArg 参数
- **类型：** `std::string` (C++) / `str` (Python)
- **默认值：** 空字符串
- **功能：** 向子脚本传递参数
- **传递方式：** 通过环境变量`XRTO_SCRIPT_ARG`
- **建议格式：** `"key1=value1,key2=value2,..."`
- **用途：** 动态配置脚本行为，无需修改脚本文件

## 使用示例

### C++ 调用示例
```cpp
// 基本用法
qint64 pid = controller->runComputeTask("myTask");

// 使用超时
qint64 pid = controller->runComputeTask("myTask", "script.py", 600);

// 传递参数
qint64 pid = controller->runComputeTask("myTask", "script.py", 0, "param=value");

// 完整用法
qint64 pid = controller->runComputeTask(
    "myTask", 
    "script.py", 
    1800,  // 30分钟超时
    "iterations=100,tolerance=0.001"
);
```

### Python 调用示例
```python
# 基本用法
pid = controller.runComputeTask("myTask")

# 使用脚本和超时
pid = controller.runComputeTask(
    "myTask",
    scriptFile="script.py",
    timeOutSeconds=600
)

# 传递参数
pid = controller.runComputeTask(
    "myTask",
    scriptFile="script.py",
    scriptArg="iterations=100,tolerance=0.001"
)

# 完整用法
pid = controller.runComputeTask(
    "myTask",
    scriptFile="script.py",
    timeOutSeconds=1800,
    scriptArg="mode=production,output=result.csv"
)
```

### 脚本中接收参数
**Python:**
```python
import os
script_arg = os.environ.get('XRTO_SCRIPT_ARG', '')
# 解析参数
params = dict(item.split('=') for item in script_arg.split(',') if '=' in item)
```

**Lua:**
```lua
local script_arg = os.getenv('XRTO_SCRIPT_ARG') or ''
-- 解析参数
local params = {}
for item in string.gmatch(script_arg, "[^,]+") do
    local key, value = string.match(item, "([^=]+)=(.+)")
    if key and value then params[key] = value end
end
```

## 向后兼容性
✅ **完全向后兼容**

所有新参数都有默认值，现有代码无需修改即可继续工作：

```cpp
// 旧代码仍然有效
qint64 pid = controller->runComputeTask("myTask", "script.py");
```

```python
# 旧代码仍然有效
pid = controller.runComputeTask("myTask", scriptFile="script.py")
```

## 相关文档
- [计算模式参数说明.md](./计算模式参数说明.md) - 命令行和API完整文档
- [example_runComputeTask.py](./example_runComputeTask.py) - Python API使用示例
- [example_script.py](./example_script.py) - 子脚本参数接收示例（Python）
- [example_script.lua](./example_script.lua) - 子脚本参数接收示例（Lua）

## 测试建议

### 测试用例1：基本功能
```python
pid = controller.runComputeTask("test_task")
assert pid > 0
assert controller.isProcessRunning(pid)
```

### 测试用例2：超时功能
```python
# 启动一个会运行很长时间的任务，设置10秒超时
pid = controller.runComputeTask("long_task", "long_script.py", timeOutSeconds=10)
time.sleep(15)  # 等待超过超时时间
assert not controller.isProcessRunning(pid)  # 应该已经退出
```

### 测试用例3：参数传递
```python
# 启动任务并传递参数
pid = controller.runComputeTask(
    "param_task",
    scriptFile="test_param_script.py",
    scriptArg="test_key=test_value"
)
# 在test_param_script.py中验证参数接收
```

## 注意事项

1. **超时精度：** 超时时间以秒为单位，精度为秒级
2. **参数长度：** scriptArg参数建议不超过1024字符
3. **特殊字符：** scriptArg中如果包含特殊字符（如逗号、等号），需要在脚本中正确解析
4. **环境变量：** 脚本参数通过环境变量传递，在某些情况下可能受到系统限制
5. **进程清理：** 超时退出的进程退出码为-2，正常退出为0，错误退出为-1

## 未来扩展建议

1. 支持传递复杂对象（JSON格式）
2. 支持回调函数，在超时前警告
3. 支持自定义超时行为（重试、发送信号等）
4. 支持多个环境变量传递不同类型的参数


