# RTS设计

- RTS设计为一个独立的模块，平台通过xRtsInterface调用RTS模块的功能，RTS模块通过xRtsCallbackInterface回调平台的功能。
- 一个平台有多个RTS模块实例, 但同时最多只有一个RTS实例可以运行

## xRtsInterface

- createRtsWidget: 创建RTS Widget，返回一个RTS Widget的句柄。
- destroyRtsWidget: 销毁RTS Widget，释放资源。
- setRtsCallback: 设置RTS回调接口，平台需要实现xRtsCallbackInterface接口，并将其传递给RTS模块。
- exportProject: 导出RTS项目，返回导出结果, 用于平台持久化存储。
- importProject: 导入RTS项目，返回导入结果，用于恢复持久化存储的数据到RTS模块。
- startRts: 启动RTS模块，开始运行RTS实例。
- stopRts: 停止RTS模块，停止运行RTS实例。
- isRtsRunning: 检查RTS模块是否正在运行，返回布尔值。
- resetRts: 重置RTS模块，恢复到初始状态。

## xRtsCallbackInterface

- getFlowSheetInfo: 获取流程图列表(可能有多个流程图)。
- getFlowSheetComputeTask: 获取流程图的计算任务列表。
- setCurrentComputeTask: 设置当前计算任务。
- getMacroInfo: 获取宏信息列表(可能有多个宏)。
- callMacro: 调用宏，执行宏的功能, 注意这里需要携带一个env dict, 用于传递宏执行的环境变量, `__rts_env__` 传入, `__rts_result__` 返回；其中 `__rts_result__` 需直接设置为完整 JSON 对象，例如 `{ "errcode": 0, "errdesc": "ok", "data": {} }`
- solve: 计算RTS实例的结果，返回计算结果。
- appendLog: 追加日志信息，平台可以将日志信息展示给用户。


## rts 内部实现

- rts 按MVC模式设计，model可以脱离view直接运行，view作为观察器和配置器功能存在

- rts 是一个执行流程图，由执行模块(包含输入输出端口)和模块连接线组成

- rts 每个实例对应一个LUA VM, 可以定义自己的变量列表，并通过lua脚本读写这些变量

- rts 还可以对应到不同的实时数据源，例如csv文件或者OPC数据源等，并绑定到不同的变量

- rts 的每个执行模块根据不同的执行结果，导入到不同的输出流，来决定下一个计算模块的位置

- rts 的执行模块可以视情况配置多个输入/输出端口
