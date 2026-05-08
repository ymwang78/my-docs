# SoftSensor 完整软件架构设计与技术方案选型

## 1. 文档目的

本文基于以下输入形成：

- [design_softsensor.md](</D:/GitHub/cxx 工程/xOptCon/docs/design_softsensor.md>) 中的功能架构草案
- 当前 `xOptCon` 代码中的实际扩展点与约束
- 当前 `TaijiMPC` 的项目插件实现方式

本文目标不是再写一份概念说明，而是输出一份可以直接指导开发排期、模块拆分、接口设计和技术选型的落地方案。

本文覆盖三部分：

- `xOptCon` 中的 `SoftSensorOfflineProject` 建模工程
- `xOptCon` 中的 `SoftSensorOnlineProject` 组态/在线工程
- HostVM 侧在线运行时

说明：

- 当前仓库主要承载 `xOptCon` 前端代码
- HostVM 运行时实现大概率位于同体系的服务端工程中，不一定与本仓库同目录
- 因此本文会同时给出“本仓库内应如何改”和“服务端应如何配套实现”两部分设计

## 2. 当前架构现状与约束

### 2.1 当前可复用的基础能力

当前仓库已经具备以下可复用骨架：

- 插件型项目抽象：`framework/interfaces/IProject.h`
- 项目类型注册工厂：`framework/plugins/ProjectFactory.h`
- 解决方案与宿主管理：`framework/core/Solution.h`、`framework/core/ProjectHost.h`
- 主窗口与标签页承载：`framework/core/MainWindow.h`
- 新建项目向导：`framework/core/dialogs/NewProjectWizard.*`
- 应用级项目插件样板：`applications/TaijiMPC/TaijiMPCProject.*`
- 应用级 Model/View 分层样板：`TaijiMPCModel` + `TaijiMPCView`
- 远程通信机制：`ZDP RPC + Storm 广播`
- 工业曲线与表格界面基础：`Qt6 Widgets + QWT`

结论：SoftSensor 最合理的落地方式不是塞进 `TaijiMPC`，而是拆成两个新的 project 类型并列挂接到 `xOptCon` 中：

- `SoftSensorOfflineProject`
- `SoftSensorOnlineProject`

它们与 `TaijiMPCProject` 处于同一层级。

### 2.2 当前必须正视的架构硬编码

虽然框架层已经有 `IProject` 和 `ProjectFactory`，但目前仍然存在多处 `TaijiMPC` 专用耦合，主要集中在：

- `framework/core/MainWindow.cpp`
- `framework/core/ProjectHost.cpp`
- `framework/core/InstanceService.cpp`
- `framework/core/view/SolutionTreeModel.*`
- `framework/core/view/SolutionTreeRoles.h`
- `framework/core/view/treeitems/TaijiMPCInstanceTreeItem.*`

这些文件里存在的典型问题：

- 通过 `dynamic_cast<TaijiMPCProject*>` 和 `TaijiMPCModel*` 执行实例打开和连接
- TreeView 角色定义里直接暴露 `TaijiMPCModelRole`
- Storm 广播路由直接写死到 `TaijiMPCProject -> TaijiMPCModel -> ZMpcRuntime`
- `ProjectHost::getOrLoadProjectForInstance` 中按 `TaijiMPC` 特例初始化远程实例

结论：SoftSensor 真正开工前，必须先做一轮“框架去 TaijiMPC 硬编码”的基建改造，否则后续 SoftSensor 插件会被迫复制一套分支逻辑，长期不可维护。

## 3. 目标产品形态

建议最终产品拆成 5 个逻辑子系统：

1. `SoftSensorOfflineProject`
作为 `xOptCon` 中的本地建模工程类型，负责数据导入、清洗、时滞/时常搜索、变量筛选、模型训练、评估、导出模型包。

2. `SoftSensorOnlineProject`
作为 `xOptCon` 中的组态/在线工程类型，负责模型导入、通讯配置、位号映射、校正策略、脚本、在线监控与维护。

3. `Python Training Worker`
作为 `SoftSensorOfflineProject` 的本地算法 sidecar，执行重计算任务。

4. `SoftSensor HostVM Runtime`
部署在服务端，执行实时采样、预处理、推断、校正、报警、日志、历史缓存，并通过 RPC/Storm 与前端通信。

5. `softsensor-core`
共享核心库，统一数据模型、模型包格式、预处理逻辑、推断接口、校正算法和序列化协议。

整体关系如下：

```text
+----------------------------------------------------------------------------------+
| xOptCon                                                                          |
|                                                                                  |
|  +-----------------------------+        导出 .ssmdl        +-------------------+ |
|  | SoftSensorOfflineProject    | ------------------------> | SoftSensorOnline  | |
|  | 本地建模工程                |                           | Project           | |
|  +--------------+--------------+                           | 组态/在线工程     | |
|                 |                                          +---------+---------+ |
|                 | QProcess / 文件交换                                |           |
+-----------------|----------------------------------------------------|-----------+
                  v                                                    v
        +---------------------------+                        +----------------------+
        | Python Training Worker    |                        | SoftSensor HostVM    |
        | 训练/搜索/导出 .ssmdl     |                        | Runtime              |
        +-------------+-------------+                        | 实时采样/推断/校正  |
                      ^                                      +----------+-----------+
                      |                                                 ^
                      +---------------- softsensor-core -----------------+
```

## 4. 总体设计原则

### 4.1 架构原则

- 前后端分层明确：离线建模重计算，在线推断重稳定，不混在一套执行环境里。
- UI 与算法解耦：Qt 前端只负责流程编排和结果展示，不承担复杂模型训练。
- 模型包标准化：离线与在线之间只通过标准模型包 `.ssmdl` 交互。
- 在线侧最小依赖：HostVM 运行时不依赖 Python，避免 7x24 运行中的环境不稳定。
- 先打通 MVP，再逐步补算法：先交付 LPLS + 手工动态参数 + 在线推断闭环，再迭代 GA/SVM/ANN/JITL/NPLS。

### 4.2 实施原则

- 第一阶段尽量复用 `TaijiMPC` 的项目组织方式
- 第二阶段再抽出共享软测量基础库
- 任何需要在 `MainWindow / ProjectHost / SolutionTreeModel` 中新增的能力，优先抽象成通用接口，不做 SoftSensor 特例分支

## 5. 目标模块分层

### 5.1 平台层

路径建议：

```text
framework/
  core/
  interfaces/
  plugins/
```

职责：

- Solution / ProjectHost / MainWindow / TreeModel / Plugin Factory
- 不感知具体是 `TaijiMPC` 还是 `SoftSensor`
- 仅通过统一接口与项目类型交互

### 5.2 应用插件层

路径建议：

```text
applications/
  TaijiMPC/
  SoftSensorOffline/
  SoftSensorOnline/
```

职责：

- 每个应用实现自己的 `Project / Model / View`
- 各自管理本领域的配置、运行时和专用 UI

### 5.3 共享软测量核心层

建议新增：

```text
libraries/
  softsensor-core/
```

如果短期不想改动工程结构过大，第一版也可以先放在：

```text
applications/shared/softsensor-core/
```

但中期必须抽离出来，供以下三端共享：

- `SoftSensorOfflineProject`
- `SoftSensorOnlineProject`
- `SoftSensor HostVM Runtime`

### 5.4 算法训练层

建议作为 `SoftSensorOfflineProject` 调用的 Python sidecar：

```text
tools/
  softsensor_worker/
```

职责：

- 数据清洗与统计分析
- GA 搜索
- 变量筛选
- 模型训练与评估
- 导出标准模型包

### 5.5 在线运行时层

建议放在 HostVM 工程中，模块名统一为 `zssm` 或 `SoftSensor`：

```text
hostvm/
  softsensor/
```

职责：

- OPC 采样
- 样本缓存
- 预处理
- 推断
- 校正
- 报警/日志
- 对前端提供 RPC/Storm 接口

## 6. 必须先完成的框架改造

这部分是 SoftSensor 开发的 Phase 0。

### 6.1 先支持“本地工程类型 + 远程工程类型”共存

这是这次需求变化后的前置条件。

当前 `xOptCon` 基本假设项目都挂在 `ProjectHost` 下，且大多是远程实例。若 `SoftSensorOfflineProject`
要作为与 `TaijiMPCProject`、`SoftSensorOnlineProject` 并列的 project 类型，则框架必须支持两类工程：

- 本地工程类型：例如 `SoftSensorOfflineProject`
- 远程工程类型：例如 `TaijiMPCProject`、`SoftSensorOnlineProject`

建议采用“本地宿主”方案，尽量少动现有主框架：

- 在 `Solution` 下引入内置 `LocalProjectHost`，例如显示为 `Local Workspace`
- `SoftSensorOfflineProject` 创建在该本地宿主下，不依赖 RPC/Storm
- `TaijiMPCProject` 和 `SoftSensorOnlineProject` 继续创建在远程 `ProjectHost` 下

建议给 `ProjectFactory::ProjectTypeInfo` 增加部署模式字段：

```cpp
enum class ProjectDeployMode {
    LocalOnly,
    RemoteOnly
};
```

```cpp
struct ProjectTypeInfo {
    ...
    ProjectDeployMode deployMode;
};
```

这样 `NewProjectWizard`、树节点、打开工程流程都能根据类型决定落到本地还是远程宿主。

### 6.2 新增通用远程项目接口

建议新增：

`framework/interfaces/IRemoteProject.h`

建议接口：

```cpp
class IRemoteProject : public IProject {
public:
    virtual ~IRemoteProject() = default;

    virtual bool initRemoteInstance(const zdp_base::zvm_t& instance,
                                    const QString& serviceHost,
                                    int stormPort) = 0;

    virtual bool isRemoteConnected() const = 0;
    virtual QString getInstanceStatusText() const = 0;
    virtual QIcon getInstanceStatusIcon() const = 0;

    virtual bool connectRemoteInstance() = 0;
    virtual bool uploadProjectConfig() = 0;

    virtual bool handleStormMessage(zce_int64 topic,
                                    const zce_byte* data,
                                    zce_uint32 len) = 0;
};
```

说明：

- `IProject` 继续保留通用 UI/项目生命周期接口
- `IRemoteProject` 解决当前远程实例初始化、连接、广播路由被写死到 `TaijiMPC` 的问题

### 6.3 泛化 Tree Model 和角色定义

建议修改：

- `framework/core/view/SolutionTreeRoles.h`
- `framework/core/view/SolutionTreeModel.*`

建议替换：

- `TaijiMPCModelRole` -> `ProjectPointerRole`
- 新增 `ProjectTypeRole`
- 新增 `ProjectStatusTextRole`
- 新增 `ProjectStatusIconRole`

不再把树节点绑定到具体 `TaijiMPCModel*`。

### 6.4 泛化实例树节点

建议删除“每个项目类型一个树节点类”的做法，改为统一 `GenericInstanceTreeItem`：

- 远程实例未加载时，使用 `ProjectFactory::ProjectTypeInfo` 中提供的格式化器
- 远程实例已加载时，优先调用 `IRemoteProject::getInstanceStatusText/Icon`

建议扩展 `ProjectTypeInfo`：

```cpp
std::function<QString(const zdp_base::zvm_t&)> instanceStatusTextProvider;
std::function<QIcon(const zdp_base::zvm_t&)> instanceStatusIconProvider;
```

### 6.5 泛化 MainWindow 的项目打开逻辑

当前 `MainWindow::onInstanceOpen()` 直接围绕 `TaijiMPCProject` 和 `TaijiMPCModel` 展开。

建议改成：

1. 通过 `ProjectHost::getOrLoadProjectForInstance()` 得到 `IProject*`
2. 若该对象实现 `IRemoteProject`，则调用 `connectRemoteInstance()`
3. 连接成功后统一走 `switchToProject()`
4. `switchToProject()` 只依赖 `IProject::createMainWidget()`

### 6.6 泛化 Storm 广播路由

当前 `InstanceService.cpp` 里按 `TaijiMPCProject -> TaijiMPCModel -> ZMpcRuntime` 路由。

建议改成：

1. `ProjectHost` 遍历所有已加载项目
2. 识别实现了 `IRemoteProject` 的对象
3. 调用 `handleStormMessage(...)`

这样 SoftSensor 和 TaijiMPC 都能通过自己的 Runtime 处理广播。

## 7. SoftSensor 目标应用结构

建议新增目录：

```text
applications/
  SoftSensorOffline/
    SoftSensorOfflinePlugin.cpp
    SoftSensorOfflineProject.h
    SoftSensorOfflineProject.cpp
    SoftSensorOfflineModel.h
    SoftSensorOfflineModel.cpp
    SoftSensorOfflineView.h
    SoftSensorOfflineView.cpp
    workflow/
      DataImportPage.*
      DataCleaningPage.*
      DynamicPreselectionPage.*
      VariableSelectionPage.*
      DynamicFineselectionPage.*
      ObjectModelingPage.*
      EvaluationExportPage.*
  SoftSensorOnline/
    SoftSensorOnlinePlugin.cpp
    SoftSensorOnlineProject.h
    SoftSensorOnlineProject.cpp
    SoftSensorOnlineModel.h
    SoftSensorOnlineModel.cpp
    SoftSensorOnlineView.h
    SoftSensorOnlineView.cpp
    zssm/
      ZSoftSensorRuntime.h
      ZSoftSensorRuntime.cpp
      zssm_proto.h
      zssm_pack.h
    views/
      configure/
        ConfigureGeneralView.*
        ConfigureDataSourceView.*
        ConfigureTagMappingView.*
        ConfigureCorrectionView.*
        ConfigureScriptView.*
        ConfigureAlarmView.*
      online/
        RuntimeOverviewView.*
        TrendView.*
        CalibrationView.*
        QualityView.*
        EventLogView.*
      model/
        ModelSummaryView.*
        ModelVariableView.*
    widgets/
      PredictionTrendWidget.*
      QualityBadgeWidget.*
      CalibrationTableWidget.*
libraries/
  softsensor-core/
```

## 8. 软测量项目对象设计

### 8.1 项目类型定义

建议明确拆成两个 project 类型：

#### `SoftSensorOfflineProject`

- `typeId = "SoftSensorOffline"`
- `typeName = "Soft Sensor Modeling"`
- `deployMode = LocalOnly`
- `fileExtension = "ssmproj"`

说明：

- 这是本地工程类型
- 挂在 `LocalProjectHost` 下
- 持有数据集、清洗参数、搜索参数、训练结果和导出产物引用

#### `SoftSensorOnlineProject`

- `typeId = "SoftSensorOnline"`
- `typeName = "Soft Sensor Online"`
- `deployMode = RemoteOnly`
- `vmtype = "SoftSensor"`
- `fileExtension = "sscfg"`
- 远程配置文件名：`_config.zssm`

### 8.2 关键类职责

#### `SoftSensorOfflineProject`

职责：

- 实现本地建模工程的 `IProject`
- 管理七步建模流程
- 维护数据集、实验、参数和中间结果缓存
- 调用 `Python Training Worker`
- 导出 `.ssmdl`

#### `SoftSensorOnlineProject`

职责：

- 实现 `IRemoteProject`
- 对接 `ProjectFactory`
- 创建主界面与属性页
- 承接 `MainWindow` 和 `ProjectHost` 的通用项目操作

#### `SoftSensorOnlineModel`

职责：

- 持有 `SoftSensorOnlineProjectFull`
- 管理 RPC 调用
- 管理前端缓存数据
- 响应 Storm 广播
- 发出视图刷新信号

建议定义：

```cpp
struct SoftSensorOnlineProjectFull {
    SoftSensorOnlineProjectConfig config;
    SoftSensorOnlineProjectRuntime runtime;
    SoftSensorModelPackageMeta modelMeta;
};
```

#### `SoftSensorOnlineView`

职责：

- 组织配置页、在线页、趋势页、校正页
- 统一标签页导航
- 脏数据刷新与当前视图局部更新

#### `SoftSensorOfflineView`

职责：

- 组织建模七步流程页
- 展示数据质量、特征筛选和训练评估结果
- 管理后台训练任务状态
- 导出标准模型包

### 8.3 建议 UI 视图结构

对于 `SoftSensorOnlineProject`，建议采用与 `TaijiMPC` 一致的“主标签页 + 子页面”方式，降低主框架接入成本。

建议主标签页如下：

1. `General`
基础信息、采样周期、运行模式、心跳/看门狗

2. `DataSource`
OPC-Device / OPC-Cache 选择、服务器枚举、连接检测、采样质量设置

3. `Model`
导入 `.ssmdl`、查看模型版本、训练指标、输入变量清单、动态参数摘要

4. `Tag Mapping`
模型输入/输出/化验变量与现场位号映射

5. `Correction`
化验闭环校正规则、等待期、死区、滤波、校正因子

6. `Scripts`
初始化脚本、输入脚本、输出脚本

7. `Runtime`
当前输入值、预测值、修正值、质量码、模型状态

8. `Trend`
实时趋势、多曲线、多时间尺度

9. `Calibration`
化验录入、等待队列、回溯比对、校正记录

10. `Events`
报警、日志、状态变更记录

## 9. 核心数据模型设计

### 9.1 配置对象

建议定义：

```cpp
struct SoftSensorOnlineProjectConfig {
    BasicConfig basic;
    DataSourceConfig dataSource;
    ModelBindingConfig modelBinding;
    std::vector<TagMapping> inputMappings;
    TagMapping outputMapping;
    std::optional<TagMapping> labMapping;
    CorrectionPolicy correctionPolicy;
    ScriptPolicy scriptPolicy;
    AlarmPolicy alarmPolicy;
    FrontSettings frontSettings;
};
```

### 9.2 运行时对象

建议定义：

```cpp
struct SoftSensorOnlineProjectRuntime {
    ProjectState state;
    std::vector<SignalRuntime> inputs;
    SignalRuntime output;
    std::optional<SignalRuntime> labValue;
    PredictionSnapshot latestPrediction;
    CalibrationState calibrationState;
    QualitySummary qualitySummary;
    std::vector<AlarmEvent> activeAlarms;
    LicenseInfo licenseInfo;
};
```

### 9.3 模型包对象

建议统一为单文件模型包 `.ssmdl`，内部使用 SQLite 作为容器格式。

原因：

- 单文件，便于交付和版本管理
- Python 侧直接可写
- C++ 侧直接可读
- 无需额外引入 zip 打包依赖
- 可同时保存结构化元数据和二进制模型

建议表结构：

- `package_meta`
- `algorithm_meta`
- `feature_schema`
- `dynamic_features`
- `preprocess_pipeline`
- `metrics`
- `artifacts`
- `training_summary`

其中 `artifacts` 表中可保存：

- ONNX 模型二进制
- LPLS/NPLS 系数矩阵
- JITL 样本库
- 归一化参数

### 9.4 模型包元数据建议

```json
{
  "packageVersion": "1.0",
  "modelId": "sulfur_softsensor_v20260422_001",
  "algorithm": "LPLS",
  "targetTag": "SULFUR_PRED",
  "samplingPeriodMs": 60000,
  "featureCount": 18,
  "supportsCalibration": true,
  "trainingMetrics": {
    "r2": 0.91,
    "rmse": 0.24,
    "mae": 0.18
  }
}
```

## 10. SoftSensorOfflineProject 架构

### 10.1 总体定位

离线建模部分不再作为独立外部工具描述，而是作为 `xOptCon` 中的本地 project 类型 `SoftSensorOfflineProject` 落地。

它与以下工程并列：

- `TaijiMPCProject`
- `SoftSensorOnlineProject`

原因：

- 满足“离线建模也是 project 类型”的统一产品形态
- 可以复用 `xOptCon` 的 Solution、标签页、属性页、最近工程等基础能力
- 训练链路仍然可以通过 Python sidecar 与在线侧保持执行环境分离

说明：

- `SoftSensorOfflineProject` 是本地工程，不依赖 HostVM
- 它负责生成 `.ssmdl`
- `SoftSensorOnlineProject` 负责消费 `.ssmdl`

### 10.2 工具内部模块

建议拆分为：

- `ProjectManager`
- `DatasetManager`
- `CleaningPipelineService`
- `DynamicFeatureSearchService`
- `FeatureSelectionService`
- `TrainingOrchestrator`
- `EvaluationService`
- `ModelPackageExporter`

### 10.3 UI 流程

直接按需求文档中的 7 步组织：

1. Data Import
2. Data Cleaning
3. Dynamic Pre-selection
4. Variable Selection
5. Dynamic Fine-selection
6. Object Modeling
7. Evaluation & Export

每一步都要支持：

- 参数保存
- 结果预览
- 回退重算
- 产出缓存

### 10.4 训练引擎选型

建议使用本地 Python sidecar，而不是纯 C++ 重写所有算法。

建议技术栈：

- Python 3.12
- `pandas`
- `numpy`
- `scipy`
- `scikit-learn`
- `deap` 或 `pymoo`
- `skl2onnx`
- `onnxruntime` 用于导出验证

原因：

- 数据清洗、搜索、训练算法成熟度高
- 开发速度远高于纯 C++
- 后续补 SVM / ANN / JITL / NPLS 更快

### 10.5 前后端协作方式

不建议上 gRPC，不建议常驻本地端口服务。

建议采用：

- `SoftSensorOfflineProject` 通过 `Qt QProcess` 启动本地 `softsensor_worker`
- 命令参数传任务类型
- 输入输出使用 JSON 文件 + CSV/Parquet 临时目录

优点：

- Windows 部署最简单
- 崩溃隔离
- 不引入额外网络端口
- 易于重试和记录任务日志

### 10.6 算法落地策略

建议分 3 个层次交付：

#### MVP

- LPLS
- 手工 delay / time constant
- 边界检查 / 呆滞检查 / 跳变检查
- 滑动平均
- 相关性分析

#### V2

- GA 动态参数搜索
- GA 变量筛选
- SVM
- ANN

#### V3

- JITL
- NPLS
- 自动重训练建议
- 模型对比实验

## 11. 在线 Runtime 架构

### 11.1 HostVM 侧模块

建议拆分为：

- `SoftSensorVmFacade`
- `DataAcquisitionService`
- `SamplingScheduler`
- `SlidingWindowBuffer`
- `PreprocessPipeline`
- `InferenceService`
- `CalibrationService`
- `ScriptEngineService`
- `AlarmService`
- `HistoryCacheService`
- `StormPublisher`

### 11.2 在线推断主循环

每个采样周期执行：

1. 采集输入位号值
2. 检查质量码与时间戳
3. 写入滑动窗口
4. 执行预处理
5. 执行输入脚本
6. 生成动态特征
7. 进行模型推断
8. 执行输出脚本
9. 执行化验闭环校正
10. 写输出位号
11. 记录日志/趋势缓存
12. 通过 Storm 发布运行态

### 11.3 运行时线程模型

建议线程拆分如下：

- 主控制线程：调度周期和状态机
- 采样线程：OPC 拉取
- 推断线程：模型推断
- 校正线程：化验等待与回溯
- 脚本线程：脚本执行沙箱
- 广播线程：Storm 推送

原则：

- 采样与推断分离
- 推断不能阻塞下一周期采样
- 脚本异常不能拖垮主循环

### 11.4 Runtime 状态机

建议状态：

- `Created`
- `Loaded`
- `Configured`
- `Running`
- `Degraded`
- `CalibrationWaiting`
- `CalibrationApplied`
- `Alarm`
- `Stopped`
- `Faulted`

## 12. 化验闭环校正设计

### 12.1 数据结构

建议定义：

- `LabSampleRecord`
- `PendingCalibrationJob`
- `CalibrationResult`
- `CalibrationHistoryRecord`

### 12.2 处理流程

1. 操作员录入化验值和采样时间
2. 系统进入 `CalibrationWaiting`
3. 到等待时间后，从历史预测序列中回溯对应时间点预测值
4. 计算偏差 `lab - predicted`
5. 若偏差落在死区内，则只记录，不校正
6. 若超出死区，按 `alpha` 平滑更新偏置
7. 记录校正结果和状态变迁

### 12.3 建议校正模型

建议先采用简单稳健方案：

```text
bias_new = (1 - alpha) * bias_old + alpha * (lab_value - predicted_value)
corrected_output = raw_output + filtered_bias
```

这样最容易解释，也最适合第一版工业落地。

## 13. 脚本引擎设计

### 13.1 选型建议

主路线建议：

- `Lua 5.4 + sol2`

不建议主路线直接采用 VBScript，原因：

- 仅适合 Windows
- 依赖 COM / ActiveScript
- 调试和沙箱能力弱
- 后续迁移成本高

### 13.2 兼容策略

如果业务上必须兼容历史 VBScript 脚本，可采用：

- V1：只支持 Lua
- V2：增加一个 Windows-only 的 VBScript 兼容执行器

不要在第一版同时支持两套语法。

### 13.3 脚本挂点

保留需求文档中的三类挂点：

- `InitScript`
- `InputScript`
- `OutputScript`

建议脚本上下文暴露对象：

- `project`
- `inputs`
- `output`
- `lab`
- `quality`
- `logger`
- `env`

### 13.4 安全约束

- 禁止文件系统写入
- 禁止网络访问
- 限制最大执行时长
- 限制最大内存占用
- 脚本异常仅影响当前周期，不允许拖死主服务

## 14. 通讯与数据源设计

### 14.1 前后端通讯

继续复用当前体系：

- 控制面：`ZDP RPC`
- 数据面：`Storm 广播`

原因：

- 与 `xOptCon` 当前架构一致
- 前端接入成本最低
- 宿主管理与实例生命周期可复用

### 14.2 现场数据接入

建议抽象：

```cpp
class IDataSourceAdapter {
public:
    virtual bool connect() = 0;
    virtual bool disconnect() = 0;
    virtual std::vector<SignalSample> batchRead(...) = 0;
    virtual bool batchWrite(...) = 0;
};
```

第一版支持两类实现：

- `OpcDeviceAdapter`
- `OpcCacheAdapter`

### 14.3 OPC 选型建议

结合当前 `TaijiMPC` 的配置界面和现有 RPC 方式，建议：

- 前端仍保留 OPC Server 枚举、配置和 Verify 入口
- 真正的 OPC 连接与读写全部放在 HostVM 侧

原因：

- 前端不承担现场通讯压力
- 在线逻辑和采样时间戳统一在服务端
- 可减少 DCOM/网络环境差异带来的前端不一致

## 15. 模型推断内核设计

### 15.1 统一推断接口

建议定义：

```cpp
class ISoftSensorInferenceModel {
public:
    virtual ~ISoftSensorInferenceModel() = default;
    virtual bool load(const SoftSensorModelPackage& pkg) = 0;
    virtual PredictionResult predict(const FeatureVector& features) = 0;
};
```

### 15.2 各算法实现建议

#### LPLS

- C++ 原生实现
- 数值库：`Eigen3`
- 存储：系数矩阵、均值方差、变量列表

#### NPLS

- V1 可以先实现为“非线性特征映射 + PLS”
- 算法训练放 Python
- 在线侧仍落到 C++ 可执行参数化形式

#### ANN

- 训练：Python / scikit-learn 或 PyTorch
- 导出：ONNX
- 在线：`ONNX Runtime C++`

#### SVM

- 训练：Python / scikit-learn
- 导出：ONNX
- 在线：`ONNX Runtime C++`

#### JITL

- 训练阶段只保存样本库、局部回归参数和归一化参数
- 在线侧 C++ 原生实现局部样本搜索与回归
- 可选使用 KD-Tree 或 BallTree

### 15.3 为什么在线侧不能依赖 Python

- 工业现场 7x24 不适合依赖 Python 解释器环境
- 服务升级、包冲突、部署审计都更难
- 故障定位成本高

因此建议原则：

- 训练可以用 Python
- 运行时推断必须落回 C++ 或 ONNX Runtime

## 16. 关键 RPC 与广播接口

### 16.1 RPC 建议

建议 SoftSensor Runtime 提供以下 RPC：

- `getProjectFull`
- `setProjectConfig`
- `uploadModelPackage`
- `startOnline`
- `stopOnline`
- `enumOpcServerList`
- `verifyTags`
- `setScript`
- `executeScript`
- `submitLabSample`
- `queryCalibrationHistory`
- `ackAlarm`
- `exportHistory`

### 16.2 Storm 广播建议

建议广播事件：

- `ProjectRuntimeUpdated`
- `PredictionTrendPoint`
- `CalibrationStateChanged`
- `AlarmRaised`
- `AlarmCleared`
- `LogText`

## 17. 技术选型总表

| 领域 | 选型 | 原因 | 备注 |
|---|---|---|---|
| 前端 UI | Qt6 Widgets | 与当前工程一致，接入成本最低 | 继续使用 |
| 曲线与趋势 | QWT | 当前工程已使用 | 继续使用 |
| 主体语言 | C++17 | 与当前仓库一致 | 继续使用 |
| 插件接入 | `IProject + ProjectFactory` | 已有成熟骨架 | 需去硬编码 |
| 远程通信 | ZDP RPC + Storm | 与当前架构一致 | 继续使用 |
| 数值计算 | Eigen3 | 轻量、适合矩阵运算 | 新增依赖 |
| 离线训练 | Python 3.12 sidecar | 算法成熟、开发快 | 新增工具链 |
| Python 算法库 | pandas/numpy/scipy/scikit-learn/deap | 满足清洗、搜索、训练 | 建议 requirements 锁版本 |
| ANN/SVM 在线推断 | ONNX Runtime C++ | 稳定、可脱离 Python | 新增依赖 |
| 脚本引擎 | Lua 5.4 + sol2 | 易嵌入、可控、跨平台 | 主路线 |
| 模型包 | SQLite 单文件 `.ssmdl` | 单文件、可读写、易版本化 | 强烈推荐 |
| 历史缓存 | SQLite + 内存环形缓冲 | 易追溯、性能可控 | HostVM 侧 |
| 日志 | 复用现有日志 + 结构化事件表 | 方便界面展示和导出 | 统一事件模型 |

## 18. 开发阶段拆分

### Phase 0：框架基建改造

目标：

- 支持本地工程类型与远程工程类型共存
- 引入 `IRemoteProject`
- 去掉 `MainWindow / ProjectHost / SolutionTreeModel / InstanceService` 对 `TaijiMPC` 的硬编码依赖

交付物：

- `SoftSensorOfflineProject` 和 `SoftSensorOnlineProject` 都可以被 ProjectFactory 注册
- TreeView 可以同时显示本地工程节点和远程实例节点
- MainWindow 可以用统一机制打开本地工程与远程项目

### Phase 1：双 SoftSensor Project 骨架

目标：

- 建立 `SoftSensorOfflineProject / SoftSensorOfflineModel / SoftSensorOfflineView`
- 建立 `SoftSensorOnlineProject / SoftSensorOnlineModel / SoftSensorOnlineView`
- 打通本地工程创建、远程工程创建、基础页签显示

交付物：

- 能在 `xOptCon` 中新建两类 SoftSensor 项目
- Offline 七步流程页和 Online 基础页签可以正常显示

### Phase 2：SoftSensorOfflineProject MVP

目标：

- Data Import
- Data Cleaning
- 手工动态参数
- LPLS 训练与评估
- 导出 `.ssmdl`

交付物：

- 可以在 `SoftSensorOfflineProject` 中完成从数据到模型包的 MVP 闭环

### Phase 3：SoftSensorOnlineProject 组态接入

目标：

- 支持导入 `.ssmdl`
- 支持位号映射
- 支持 OPC Verify
- 支持基础策略配置

交付物：

- 模型摘要页
- 变量映射页
- 校正策略页
- 脚本页占位

### Phase 4：HostVM MVP 在线运行

目标：

- 打通 OPC 采样
- 完成 LPLS 推断
- 完成趋势和运行监控

交付物：

- 可以用真实或仿真点位做在线预测
- 前端可实时显示输入/输出/质量/趋势

### Phase 5：校正与脚本

目标：

- 化验录入
- 等待队列
- 偏置平滑校正
- 脚本执行

交付物：

- Calibration 页面可用
- Init/Input/Output 脚本可验证和部署

### Phase 6：高级算法

目标：

- GA 搜索
- SVM / ANN
- JITL
- NPLS

## 19. 建议的首版交付边界

如果目标是尽快上线一版可用系统，建议首版范围严格控制在：

- 新项目类型 `SoftSensorOfflineProject`
- 新项目类型 `SoftSensorOnlineProject`
- 单输出软测量
- OPC-Device / OPC-Cache
- LPLS
- 手工 delay / time constant
- 位号映射
- 趋势监控
- 化验闭环校正
- Lua 脚本

首版不要同时做：

- 多模型编排
- 自动重训练
- NPLS
- JITL
- 双脚本语法支持
- 大规模历史分析报表

## 20. 主要风险与应对

### 风险 1：框架仍残留 TaijiMPC 特化

影响：

- SoftSensor 接入过程中出现越来越多的 if/else 分支

应对：

- 强制先做 Phase 0
- 新增能力优先改接口，不加临时特例

### 风险 2：算法训练与在线推断结果不一致

影响：

- 线下指标好，线上效果差

应对：

- 用统一 `.ssmdl` 包描述预处理
- 在线侧必须复用同一套归一化、动态特征和校正参数
- 增加“离线包回放验证”测试

### 风险 3：脚本引擎失控

影响：

- 在线线程卡死

应对：

- 单独脚本线程
- 超时强制终止
- 禁止外部 IO

### 风险 4：现场 OPC 质量差导致预测抖动

影响：

- 预测不稳定，误报警

应对：

- 引入质量码判断
- 缺失值策略
- 数据清洗和低通滤波
- 在 Runtime 页面明确展示质量状态

## 21. 建议的最小测试集

必须覆盖以下测试：

- 项目类型注册与新建
- 本地工程创建与打开
- 远程实例加载与连接
- `.ssmdl` 导入解析
- 预处理一致性测试
- LPLS 在线推断正确性
- 化验校正流程
- 脚本超时与异常保护
- Storm 广播刷新
- OPC Verify 批量校验
- 趋势缓存与历史导出

## 22. 最终结论

基于当前仓库的真实结构，SoftSensor 的正确建设路径是：

1. 先把 `xOptCon` 的插件框架从“名义通用、实际偏 TaijiMPC”改成真正可并列多项目类型
2. 再新增 `SoftSensorOfflineProject` 和 `SoftSensorOnlineProject` 作为与 `TaijiMPCProject` 并列的两种工程类型
3. 通过本地工程类型和远程工程类型的共存，容纳“离线建模”和“在线组态”两种不同生命周期
4. 用统一 `.ssmdl` 模型包打通离线与在线
5. 训练侧使用 Python 提升算法交付速度，在线侧使用 C++/ONNX Runtime 保证工业稳定性

如果按这个路线推进，SoftSensor 不只是“加几个页面”，而是能在现有 `xOptCon + HostVM` 架构上稳定落地、可持续演进的一条产品线。
