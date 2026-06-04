# xTdb 前后端架构职责说明

## 1. 文档目标

在以下既定前提下，定义 xTdb GUI 产品的前后端职责边界与分层方案：

- 后端基于 HostVM + libtdb
- 前端基于 xApc framework + application 框架
- 产品目标是构建一个可交付、可诊断、可扩展的 GUI 产品

核心判断：

> 这条路线总体可行，而且比 GUI 直接耦合内核/SDK 更适合产品化交付。

但前提是：后端不能只是 libtdb 透传层，前端不能退化成调试台壳子。

---

## 2. 架构可行性结论

### 2.1 总体可行

该方案满足前面产品规划中最关键的几个要求：

- 支持“连接 -> 浏览 -> 执行 -> 查看结果 -> 排错/复用”的最小闭环
- 有明确前后端边界，利于错误收敛、状态管理、日志与诊断
- 前端可以复用 xApc 框架，降低 GUI 基建成本
- 后端可以基于 HostVM + libtdb 承载复杂能力和运行时细节

### 2.2 方案成立的三个前提

#### 前提 1，后端必须是应用服务层
后端需要提供产品语义接口，例如：

- testConnection
- listResources
- getResourceDetail
- runQuery
- runAction
- listHistory
- getDiagnostics

不应简单原样暴露 libtdb 内部 API。

#### 前提 2，前端必须按用户任务组织
前端页面与流程应围绕：

- 首页
- 连接管理
- 资源浏览
- 操作台
- 结果页
- 历史
- 设置与诊断

不应按底层模块结构直接分栏。

#### 前提 3，首版仍需坚持最小闭环
即使有完整前后端架构，也不能把首版扩成平台化大工程。首版仍应控制在：

- 1 个查询动作
- 1 到 2 个执行动作
- 统一结果页
- 基础历史与诊断能力

---

## 3. 总体分层

建议分为 4 层：

### L1. GUI 展示层（xApc framework + application）
职责：
- 页面承载
- 导航与布局
- 表单输入
- 状态展示
- 结果渲染
- 用户提示

### L2. 前端应用层
职责：
- 页面状态编排
- 请求参数组装
- 结果模型适配
- 前端错误展示映射
- 页面级流程控制

### L3. 后端应用服务层（HostVM 产品后端）
职责：
- 封装 libtdb 能力
- 管理连接
- 管理资源查询
- 管理动作执行与生命周期
- 管理历史记录
- 统一错误与结果模型
- 输出日志与诊断信息

### L4. 内核能力层（HostVM runtime + libtdb）
职责：
- 底层能力执行
- 任务调度
- 资源访问
- 底层错误产生
- 运行时状态维护

---

## 4. 前端职责边界

## 4.1 前端负责

### F1. 用户工作流组织
首版至少包括：
- 首页
- 连接管理页
- 资源浏览页
- 操作台页
- 结果页
- 历史页
- 设置与诊断页

### F2. 参数输入与交互反馈
- 表单组件
- 默认值呈现
- 必填/格式校验提示
- 空状态与失败状态
- 写动作风险提示与确认

### F3. 结果展示
- 表格视图
- 原始视图
- 错误详情
- 执行状态
- 复制与导出入口

### F4. 页面级状态管理
- 当前连接上下文
- 当前资源上下文
- 当前动作上下文
- 当前执行状态
- 当前结果上下文

## 4.2 前端不应负责

前端不应承担以下职责：

- 直接理解 libtdb 内部细节
- 手工拼装复杂调用链
- 自己做错误层级归类
- 自己维护任务生命周期
- 自己定义历史记录结构
- 自己判断版本兼容性

这些职责应尽量在后端应用服务层收敛。

---

## 5. 后端职责边界

## 5.1 后端负责

### B1. 能力产品化封装
将底层能力转换成稳定的产品接口，而不是裸暴露底层实现。

### B2. 错误统一
统一将异常归类为：
- 输入错误
- 连接错误
- 权限错误
- 资源错误
- SDK/libtdb 错误
- 内核/运行时错误
- 未知错误

### B3. 结果统一
所有动作统一返回 ResultEnvelope，供前端结果页统一渲染。

### B4. 执行生命周期管理
管理：
- 提交
- 运行中
- 完成
- 失败
- 取消（如支持）

### B5. 历史与诊断
- 保存执行记录
- 生成 taskId / traceId
- 聚合日志与错误上下文
- 输出可复制诊断信息

### B6. 连接与安全
- 连接配置管理
- 凭证安全处理
- 连接测试
- 版本兼容检查
- 权限相关错误反馈

## 5.2 后端不应退化成什么

后端不应退化为：

- libtdb 透传层
- 无统一模型的散接口集合
- 只能被当前 GUI 使用的临时脚本层

如果退化成上述形态，新增动作和维护成本会快速上升。

---

## 6. 建议的后端服务域

### 6.1 ConnectionService
职责：
- createConnection
- updateConnection
- deleteConnection
- listConnections
- testConnection
- activateConnection
- getCurrentConnection

### 6.2 ResourceService
职责：
- listResources
- searchResources
- getResourceDetail
- refreshResource

### 6.3 ActionService
职责：
- runQuery
- runAction
- getTaskStatus
- getTaskResult
- cancelTask（如支持）
- listAvailableActions

### 6.4 HistoryService
职责：
- saveHistoryRecord
- listHistory
- getHistoryRecord
- rerunHistoryRecord

### 6.5 DiagnosticService
职责：
- getDiagnosticSnapshot
- getVersionInfo
- getLogEntryPoint / exportLogs
- aggregateRecentErrors

### 6.6 RuntimeService
职责：
- 获取 HostVM runtime 状态
- 获取 libtdb 版本与兼容矩阵
- 运行时健康检查

---

## 7. 推荐的数据流

以“查询动作”为例：

1. 用户在前端操作台填写参数
2. 前端应用层组装 RunQueryRequest / ActionRequest
3. 调用后端 ActionService.runQuery
4. 后端做参数校验与上下文补全
5. 后端通过 HostVM 调用 libtdb
6. 后端统一封装为 ResultEnvelope
7. 后端写入 HistoryRecord，并生成 taskId / traceId
8. 前端使用统一结果模型渲染结果页

该数据流的价值：

- 前端始终围绕稳定模型开发
- libtdb 复杂性不外溢到页面层
- 历史、结果、诊断天然可关联

---

## 8. 对照前面产品要求，需要补的工作

## 8.1 为满足“连接管理”要求，需要做
- 连接模型定义
- 连接持久化策略
- 测试连接接口
- 凭证安全策略
- 版本兼容检查

## 8.2 为满足“资源浏览”要求，需要做
- 资源列表接口
- 资源详情接口
- 分页/懒加载策略
- 资源能力标识（capabilities）

## 8.3 为满足“核心动作”要求，需要做
- 首版动作清单选型
- 动作参数 schema
- 统一动作提交接口
- 统一执行状态与错误回执

## 8.4 为满足“结果展示”要求，需要做
- ResultEnvelope 统一模型
- 大结果集展示策略
- 原始视图与表格视图的双轨返回支持
- 复制/导出能力

## 8.5 为满足“历史记录”要求，需要做
- HistoryRecord 模型
- 参数快照结构
- 再执行流程
- 历史保留与清理策略

## 8.6 为满足“设置与诊断”要求，需要做
- 版本信息汇总
- DiagnosticSnapshot 模型
- 日志入口/导出
- traceId / taskId 串联机制

---

## 9. 首版最先应启动的工作包

### WP1. 前后端契约与分层定稿
输出：
- 职责边界
- 调用方式
- 核心服务域
- 统一模型原则

### WP2. 统一错误与结果模型
输出：
- ErrorInfo
- ResultEnvelope
- taskId / traceId 约定

### WP3. 前端工作台骨架
输出：
- 首页
- 连接页
- 资源页
- 操作台页
- 结果页骨架

### WP4. 后端基础服务雏形
输出：
- ConnectionService
- ResourceService
- ActionService 基础版
- DiagnosticService 基础版

### WP5. 首版动作映射与选型
输出：
- 查询动作定义
- 执行动作候选列表
- 首版动作评分与优先级

---

## 10. 当前需要继续关注的关键点

当前仍未最终拍板，但会影响后续实施的关键点：

1. 首版 GUI 目标平台范围
2. 前后端调用机制（RPC / IPC / HTTP / 桥接）
3. 首版 1 到 2 个执行动作的具体选择

其中最关键的是第 3 点，因为它直接影响首版 demo 价值和操作台结构。

---

## 11. 结论

这套“后端 HostVM + libtdb，前端 xApc framework + application”的方案总体可行，且是正确方向。

但要真正满足前面定义的产品要求，必须补齐以下关键能力：

- 前后端职责清晰
- 后端应用服务层产品化
- 统一错误与结果模型
- 首版动作收敛
- 历史与诊断能力前置建设
- 交付链路（安装包、版本、日志、文档）同步纳入

一句话总结：

> 这条路线不是“能不能做”的问题，而是“必须把后端做成产品后端，把前端做成用户工作台”，这样才能支撑 xTdb 从内核/SDK 走向真正可交付的 GUI 产品。
