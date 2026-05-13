# FrontSensor VB6 → Qt6 迁移计划 / Migration Plan

> 跟踪文档 / Living document. 每完成一个 Phase 在 *Status* 栏勾选并在 commit 中引用。

## Background / 背景

`apps/FrontSensor/Legacy/VBProject/` 是一个基于 Visual Basic 6 的工业过程 **软测量** (soft-sensor) 建模、组态与运行软件，约 130 个文件、~12,000 行 VB 代码。它支持以下 6 步建模流水线：

`导入数据 → 数据清洗 → 动态初选 → 变量选择 → 动态精选 → 对象建模`

并实现 LPLS / NPLS / JITL / SVR / ANN / NLS 六类预测模型，配以 GA 驱动的超参数搜索。

按 `docs/TODO.md`，**只迁移建模部分**到 Qt6 C++ 单独可执行文件。组态 / 在线运行部分**不**在本次迁移范围。

## High-level decisions / 关键决策

| 决策 | 取舍 |
|---|---|
| 算法实现 | 同时实现 **C++ 原生** 与 **Python 嵌入** 两套，便于数值对��� |
| 工程文件格式 | 新格式 `*.fsproj`（`libzce` ZDS / BSON）；老 `*.mod` v10 **单向导入**（计划 Phase 6） |
| 命名规范 | C++ 标识符**全英文**（PascalCase 类 / camelCase 方法 / snake_case_ 成员），UI 文案**保持中文**（`tr()`） |
| 架构 | MVC：`Model/` 数据 + 信号；`View/` Qt 视图；`Controller/` 业务逻辑 |
| 复用 | `libQTExt`（xTableView/xQwtChart/xLogView）、`libzce`（ZDS、Logger、Thread、Task）、Qt6 + Qwt + qtadvanceddocking |

## Phases / 各阶段

| # | 主题 | 范围 | 状态 |
|---|---|---|---|
| 1 | **Skeleton + Data Model + Main Window** | `CMakeLists`、`Model/`（11 类型 + ZDS schema）、`Controller/`（保存/打开/最近）、`View/`（启动窗、主窗口 6 步按钮 + 菜单 + 工具栏 + 6 个 stub 对话框）、`main.cpp`、文档 | ✅ Phase 1 完成 (2026-05-08) |
| 2 | Step 1 (导入数据) + Step 2 (数据清洗) | CSV 导入；`xTableView` 表格视图（清洗前/后）、`xQwtChart` 趋势曲线、相关性分析；移植 `Correlation_Module.bas`、公共统计 (`公共_Module.bas` 子集) | 待开始 |
| 3 | Step 3 (动态初选) + Step 4 (变量选择) | 移植 `Cholseky_Module.bas`、`Linear_PLS_Module.bas`、`GA_Module.bas`；初选/变选搜索约束 UI 和结果展示 | 待开始 |
| 4 | Step 5 (动态精选) + Step 6 (对象建模) | 6 类模型核心算法（LPLS/NPLS/JITL/SVR/ANN/NLS）；模型训练后台任务（`zce::Task`）；模型校验 | 待开始 |
| 5 | 结果可视化 | 化验点预测表格/曲线、全部点预测、单因素分析、模型校验报告 | 待开始 |
| 6 | 老工程 `*.mod` 导入 | 完整实现 v10 二进制读取（单向）；版本兼容矩阵 | 待开始 |
| 7 | 模型导出 + 单因素分析 | 导出独立可加载模型文件（运行时格式）；单因素曲线 | 待开始 |
| 8 | 自定义计算脚本 | 用 `libzce` 的 Lua/Python 嵌入替换 VB6 `MSScript` | 待开始 |

## Phase 1 完成清单

```
apps/FrontSensor/
├── CMakeLists.txt              ✅ 跨平台 CMake，链接 Qt6 + libQTExt + libzce
├── FrontSensor.qrc             ✅ 图标资源 (11 个 SVG)
├── FrontSensor.rc              ✅ Win32 版本信息
├── main.cpp                    ✅ 入口、QApplication、splash → MainWindow
├── generate_ptl.{bat,sh}       ✅ 调用 zgen 生成序列化代码
├── translations/*.ts           ✅ Qt 翻译占位
├── resources/*.svg             ✅ 步骤图标
├── Model/                      ✅
│   ├── ProjectData.ptl                   ZDS schema
│   ├── ProjectDataProto.h (gen)          POD 结构
│   ├── ProjectData_pack.{h,cpp} (gen)    ZDS pack/unpack
│   ├── ProjectModel.{h,cpp}              QObject 根模型，发信号
│   ├── DataFile / DataVariable           数据源
│   ├── AuxVariable / LabVariable         50+ 字段的辅助/化验建模变量
│   ├── Constraint                        组合约束 + CandidateSeed
│   ├── StepParams                        6 步全局参数 + LM 求解器参数
│   ├── SoftSensor / SoftSensorVars       cls软测量族
│   ├── FixedQueue                        FIFO（运行时使用）
│   ├── DataMatrix                        TimeSeries / Frame
│   └── ModelInclude.h                    汇总头
├── Controller/                 ✅
│   ├── ProjectController       新建/打开/保存/另存为/最近文件/未保存提示
│   ├── ProjectSerializer       *.fsproj 读写（魔数 + ZDS payload）
│   └── LegacyMODImporter       Phase 6 的 stub
└── View/                       ✅
    ├── MainWindow              工具栏 + 菜单 + 6 步按钮 + 6 结果按钮
    ├── SplashDialog            建模/组态/在线（仅建模可点）
    ├── AboutDialog
    └── StepDialogs/StepStubDialog (1 stub 服务 6 步)
```

## Verification (Phase 1) — 全部通过 ✅

| 验证项 | 结果 |
|---|---|
| CMake 配置通过 (Qt 6.10.3 + Ninja + MSVC) | ✅ |
| `FrontSensor.sln` (VS18 / v145) MSBuild Debug x64 构建成功，输出 `bin/x64/Debug/FrontSensor.exe` | ✅ |
| zgen 生成确定性 — 第二次运行无 diff | ✅ |
| `FrontSensor.exe --help` / `--version` 正确解析并退出 0 | ✅ |
| `FrontSensor.exe --smoke-test` 头无 GUI 自检：构造 ProjectModel → 保存 .fsproj → 读回 → 18 项字段全部一致 | ✅ |
| 启动模式选择窗口（splash）出现，建模/组态/在线 三个按钮，仅"建模"可点 | ✅ |
| `--no-splash` 直接进入 MainWindow，进程保持活动 ≥3s 无崩溃 | ✅ |
| Splash 模式启动后保持活动 ≥3s 无崩溃 | ✅ |

后续手工冒烟（用户交互层面，自动化不便覆盖）：

* 6 个 Step 按钮 → 弹出 stub → 点"标记为已执行" → 关闭后右侧 result 按钮亮起
* 文件 → 保存为 → 选 `test.fsproj` → 重启打开 → step state 与 modified 标志正确恢复
* 关闭未保存工程 → 弹出 "是否保存修改？" 三选一

## 后续约定

* 每个 Phase 落地时在本表 Status 栏更新；同时在 `docs/DATA_MODEL.md` 增补涉及的字段。
* 任何对 `Model/ProjectData.ptl` 的字段增删需同步更新 `ProjectSerializer.cpp` 中的 `modelToProto` / `protoToModel`，并在 README 中提示老用户重新保存。
* 算法实现采用 `algo/cpp/<name>.cpp` 与 `algo/py/<name>.py` 双源对照；测试用 `tests/algo_*.cpp` 比较两边数值结果（GTest）。
