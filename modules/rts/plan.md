# RTS 模块实现计划 (plan.md)

> 依据 `docs/design_rts.md` 对当前实现 (commit `05f4223 init rts library`) 的核对结果与执行计划。

## 一、现状评估

当前代码已搭好 **MVC 骨架**，可运行性较好的部分：

| 层 | 已实现 | 文件 |
|----|--------|------|
| 对外接口 | `xRtsInterface` 全部 8 个方法已实现并导出 | `RtsInterfaceImpl.*`、`DllMain.cpp` |
| Model | 节点/连线/变量/数据源容器、增删查、JSON 导入导出、观察者通知 | `Model/RtsModel.*`、`RtsNodeModel.*`、`RtsConnectionModel.*`、`RtsObserver.h` |
| Controller | 拖拽建节点、连线、删除、属性对话框、变量面板联动 | `Controller/RtsController.*`、`DialogRtsNode.*` |
| Engine | 独立 QThread 顺序执行、按 outport 跟随连线、Lua VM 集成、日志回传 | `Controller/RtsEngine.*`、`RtsLuaVM.*` |
| View | 画布/场景/节点/端口/连线/工具箱/变量面板/日志 | `View/*` |

**架构优点**：Engine 直接驱动 Model，符合"model 可脱离 view 运行"；日志通过信号 + 回调双路输出；线程停止/reset 已有处理。

## 二、差距分析（设计 vs 实现）

当前实现本质是一个**通用流程图引擎**，与设计要求的**领域专用 RTS 模块**存在结构性偏差。

### 2.1 节点类型不匹配（最高优先级）

设计要求 9 种内置模块，实现只有 7 种且语义不符：

| 设计模块 | 实现现状 | 差距 |
|----------|----------|------|
| 开始模块（启动模式调度） | `Start`（仅空 outport，无调度） | ❌ 缺启动模式、下次启动时间显示 |
| 结束模块（多 inport） | `End`（单 inport） | ⚠️ 缺多 inport |
| Input 模块（位号→变量） | `TagMapping`（读分支，**空操作仅打印日志**） | ❌ 未接数据源，无多读选择 |
| Output 模块（变量→位号） | `TagMapping`（写分支，**空操作**） | ❌ 同上 |
| 自定义脚本模块（Lua 编辑/校验/测试） | 无（`VarDecl`/`Condition` 是片段化替代） | ❌ 缺独立脚本模块与编辑器 |
| 外部程序调用模块（同步/异步） | **完全缺失** | ❌ |
| 宏模块（初始化宏 + 运行宏 + 参数表） | `MacroCall`（单宏名、无 init/run 区分、无参数表） | ❌ |
| 计算任务选择模块 | **完全缺失** | ❌ |
| 求解模块（参数绑定变量 / 结果解析回写） | `Solve`（仅透传 sInfo，不绑定变量/不解析结果） | ⚠️ 缺变量绑定与结果回写 |
| —（设计中无） | `Condition`、`VarDecl` | ➕ 多余类型，可保留为脚本能力或移除 |

### 2.2 决策变量架构缺失（设计核心，最高优先级）

设计 §2：**每个模块内置一个整数"决策变量"，按其值（相等匹配）决定激活哪个 outport**。

当前实现用硬编码的 `success(port 0)/fail(port 1)` 取代，`executeNode` 返回固定端口索引，端口未携带"匹配值"。这是与设计**根本性的偏差**，需重构：
- `RtsNodeModel::Port` 增加 `match_value`（决策值）。
- `executeNode` 改为：执行 → 计算决策整数 → 找 `match_value == 决策值` 的 outport → 跟随连线。
- 各模块按设计定义决策值规则（Start 恒 0；Input/Output/Macro/Solve/计算任务 = 成功 0 / 失败 -1；脚本由脚本决定；外部程序 = 退出码或映射）。

### 2.3 流程图全局功能不完整（高优先级）

设计 §1：
- ✅ 全局变量表：`RtsModel::variables_` + `RtsVariablePanel` 已具雏形（但仅 name/init 文本）。
- ❌ **变量↔位号关联**：变量结构无位号绑定字段。
- ❌ **数据源位号定义**：`RtsDataSource{name,type,connection}` 无位号清单；CSV/OPC 均未实现实际读写。
- ❌ **数据源 UI**：无数据源管理面板（仅节点属性对话框里填字符串）。

### 2.4 启动模式 / 调度缺失（高优先级）

设计 §3 开始模块四种模式：单次运行 / 结束后间隔 X 分 / 首次后每 X 分 / 整点每 X 小时。当前 Engine `run()` 仅线性跑一遍即结束（`grep` 确认无 QTimer/schedule/interval）。需引入调度循环 + 下次启动时间计算与回显。

### 2.5 未使用的平台回调（中优先级）

`xRtsCallbackInterface` 中以下方法**从未被调用**：
- `getFlowSheetInfo` / `getFlowSheetComputeTask` / `setCurrentComputeTask`（→ 计算任务选择模块依赖）
- `getMacroInfo`（→ 宏模块下拉选择依赖）
- `saveRts`（→ 应在导出/编辑后落盘持久化）

宏/求解模块当前 `callMacro`/`solve` 的 `flowSheetName` 写死为 `"FlowSheet"`，应来自 `getFlowSheetInfo`。

### 2.6 工程化缺失（中优先级）

- ❌ **无 GTest 测试**（CLAUDE.md 强制要求 `tests/` + `test_*.cpp`）。
- ⚠️ **仅 Windows 构建**（`RtsLibrary.vcxproj`），无 CMakeLists.txt；Linux `build.sh` 未覆盖本模块。
- ⚠️ 头文件包含路径不一致（`../Controller/xRtsInterface.h` vs `../../Controller/...`，实际在 `include/xOpt/`），靠 vcxproj include dir 兜底，CMake 化时需统一。
- ⚠️ **线程安全**：`callMacro`/`solve` 在 Engine 子线程调用平台回调，需确认平台侧线程约定（必要时排队到主线程）。

## 三、执行计划（分阶段）

### 阶段 0：地基重构（决策变量 + 端口模型）
1. `RtsNodeModel::Port` 增加 `match_value`，并支持动态增删 inport/outport（设计要求多数模块可增删端口）。
2. Engine 改为"决策值 → 端口匹配"模型；保留 `End` 终止、最大步数保护、stop 检查。
3. 序列化（`toJson/fromJson`）同步携带端口与 `match_value`。
4. 为重构后的引擎写首批 GTest（纯 Model + Engine，可脱离 view）。

### 阶段 1：节点类型对齐设计
5. 重命名/拆分节点枚举为设计 9 类：`Start/End/Input/Output/Script/ExternalProc/Macro/ComputeTaskSelect/Solve`；评估 `Condition/VarDecl` 去留（建议并入 `Script`）。
6. `End` 支持多 inport；`Input/Output/Macro/Solve/ComputeTaskSelect` 固定 2 outport（成功/失败）+ 可增删 inport。
7. 逐个实现 `executeXxx`：
   - **Start**：决策值恒 0；承载启动模式配置（见阶段 3）。
   - **Input/Output**：对接数据源做实际位号读写，全成功=0 否则 -1（依赖阶段 2）。
   - **Script**：执行 Lua，决策值由脚本设置（默认 0）；提供编辑/validate/测试执行。
   - **ExternalProc**：`QProcess` 同步阻塞（决策值=退出码 或 0/-1 映射）与异步发射（成功 0/-1）。
   - **Macro**：初始化宏（仅首次）+ 运行宏；参数表名值对（支持从 JSON 导入）；注入 `__rts_env__`、解析 `__rts_result__.errcode`。
   - **ComputeTaskSelect**：经 `getFlowSheetComputeTask` 选择、`setCurrentComputeTask` 切换。
   - **Solve**：求解参数名值对绑定变量 → 读变量填参 → `solve` → 解析结果 JSON 回写到结果变量。
8. 同步更新 `RtsStyle`（颜色/标签）、`RtsNodeToolBox`（工具箱条目）、`DialogRtsNode`（各模块专属配置页）。

### 阶段 2：全局变量与数据源
9. 扩展数据源模型：CSV/OPC 连接 + **位号清单**；实现 CSV 读写，OPC 预留抽象接口（优先 libzce 既有能力，见 LIBZCE.md）。
10. 变量模型增加**位号绑定**字段；变量面板支持绑定编辑。
11. 新增**数据源管理面板**（增删数据源、维护位号、变量关联）。
12. Input/Output 模块支持"全部/部分"位号读写选择。

### 阶段 3：启动模式与调度
13. 实现 Start 四种启动模式配置 + Engine 调度循环（结束后/周期/整点）。
14. 画布上直观显示当前模式与**下次启动时间**（节点绘制 + 定时刷新）。
15. 调度使用 `zce::Timer` 或 `QTimer`（避免 sleep 轮询，参考 CLAUDE.md/libzce 约定）。

### 阶段 4：平台回调闭环与持久化
16. 接入 `getFlowSheetInfo`/`getMacroInfo`/`getFlowSheetComputeTask` 驱动各模块的下拉选择，去除写死的 `"FlowSheet"`。
17. 在导出/重要编辑后调用 `saveRts` 持久化。
18. 明确并落实 Engine→平台回调的线程模型。

### 阶段 5：工程化与测试
19. 新增 `tests/`，按 CLAUDE.md 规范（`test_*.cpp`、`#ifndef USE_GTEST_MAIN`、`TEST_F`）覆盖 Model、Engine、各模块执行、序列化往返。
20. 添加 CMakeLists.txt 并接入 `build.sh`，统一 include 路径（`include/xOpt/xRtsInterface.h`），实现 Linux 可构建。
21. 全量代码确认 UTF-8 + BOM、命名规范（类 PascalCase / 函数 camelCase / 变量 snake_case / 成员尾下划线）。

## 四、优先级建议

- **P0（阻塞）**：阶段 0（决策变量重构）、阶段 1（节点类型对齐）—— 否则后续都建立在错误模型上。
- **P1（核心功能）**：阶段 2（数据源/位号）、阶段 3（启动调度）。
- **P2（完善）**：阶段 4（回调闭环/持久化）、阶段 5（测试/CMake/Linux）。

> 备注：阶段 0/1 改动较大，建议在分支上推进，每阶段配套 GTest 后再合并。
