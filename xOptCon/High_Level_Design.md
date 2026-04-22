# xApc 概要设计文档

## 1. 文档说明

### 1.1 文档目的
本文档描述 xApc 平台的高层设计，包括系统功能、模块划分、接口定义和关键设计决策。

### 1.2 适用范围
- 系统架构师
- 开发人员
- 测试人员
- 项目管理人员

### 1.3 文档版本
- 版本：1.0
- 日期：2024年
- 基于代码版本：当前主分支

## 2. 系统概述

### 2.1 系统定位
xApc 是一个工业过程优化和控制平台，主要面向模型预测控制（MPC）应用，支持：
- 多项目类型管理（插件化架构）
- 远程服务器连接和项目管理
- 实时数据监控和控制
- 模型辨识和仿真
- 控制器配置和调优

### 2.2 核心功能

#### 2.2.1 解决方案管理
- 创建、打开、保存解决方案（.xsln 文件）
- 管理多个项目宿主（ProjectHost）
- 框架设置（主题、语言等）

#### 2.2.2 项目宿主管理
- 添加、删除项目宿主
- 连接到远程服务器
- 刷新和同步项目实例列表

#### 2.2.3 项目管理
- 创建新项目
- 加载现有项目
- 项目配置和验证
- 项目操作（测试、仿真、控制）

#### 2.2.4 TaijiMPC 功能
- 信号配置（MV、CV、DV、TV、EV）
- 模型辨识
- 仿真运行
- 控制器运行
- 脚本管理

## 3. 模块设计

### 3.1 框架模块（Framework）

#### 3.1.1 MainWindow 模块
**职责**：主窗口管理，UI 协调

**主要功能**：
- 菜单栏和工具栏管理
- 项目树显示和管理
- 标签页管理（多项目切换）
- 状态栏和进度显示
- 日志窗口管理

**关键接口**：
```cpp
class MainWindow {
    // Solution 管理
    bool createNewSolution();
    bool openSolution(const QString& fileName);
    bool saveSolution();
    
    // 项目访问
    Solution* getCurrentSolution() const;
    IProject* getCurrentProject() const;
    
    // UI 更新
    void updateStatusBar(const QString& message);
    void updateProjectTree();
};
```

#### 3.1.2 Solution 模块
**职责**：解决方案管理，持久化

**主要功能**：
- Solution 文件读写（JSON 格式）
- ProjectHost 管理
- 框架设置管理
- 路径转换（相对/绝对）

**关键接口**：
```cpp
class Solution {
    // 文件操作
    bool loadFromFile(const QString& filePath);
    bool saveToFile(const QString& filePath);
    
    // ProjectHost 管理
    void addProjectHost(ProjectHost* host);
    void removeProjectHost(const QString& hostKey);
    ProjectHost* getProjectHost(const QString& hostKey);
    
    // 设置管理
    void setTheme(const QString& theme);
    void setLanguage(const QString& language);
};
```

#### 3.1.3 ProjectHost 模块
**职责**：项目宿主管理，远程连接

**主要功能**：
- 服务端点配置
- 远程服务器连接
- 项目实例列表同步
- 本地项目对象管理

**关键接口**：
```cpp
class ProjectHost {
    // 连接管理
    void refreshInstances();
    bool isConnected() const;
    
    // 项目管理
    void newProject(const std::string& name, const std::string& type);
    void loadProject(const std::string& name, zce::RefBlock data);
    void deleteProject(IProject* project);
    
    // 项目访问
    IProject* getProject(int index);
    int getProjectCount() const;
};
```

#### 3.1.4 ProjectFactory 模块
**职责**：项目类型注册和创建

**主要功能**：
- 项目类型注册
- 项目实例创建
- 类型检测和查询

**关键接口**：
```cpp
class ProjectFactory {
    // 类型注册
    bool registerProjectType(const ProjectTypeInfo& info, ProjectCreator creator);
    
    // 项目创建
    IProjectPtr loadProject(ProjectHost* host, const QString& typeId);
    IProjectPtr loadProjectFromFile(ProjectHost* host, const QString& filePath);
    
    // 类型查询
    QList<ProjectTypeInfo> getRegisteredTypes() const;
};
```

### 3.2 应用模块（Application）

#### 3.2.1 TaijiMPCProject 模块
**职责**：TaijiMPC 插件实现

**主要功能**：
- 实现 IProject 接口
- 包装 PIDProject
- 创建 TaijiMPC UI
- 视图同步管理

**关键接口**：
```cpp
class TaijiMPCProject : public IProject {
    // IProject 实现
    QWidget* createMainWidget(QWidget* parent) override;
    bool connectProject() override;
    bool verifyConfiguration() override;
    
    // TaijiMPC 特定
    PIDProject* getPIDProject() const;
    BaseView* getCurrentView() const;
};
```

#### 3.2.2 PIDProject 模块
**职责**：MPC 项目核心逻辑

**主要功能**：
- 项目数据管理（配置、运行时）
- 信号管理（MV、CV、DV、TV、EV）
- 远程连接（ZMpcRuntime）
- 配置验证
- 数据导入导出

**关键接口**：
```cpp
class PIDProject {
    // 项目生命周期
    bool connectProject();
    bool saveToFile(const QString& fileName);
    
    // 配置访问
    const zmpc::ProjectConfig& getProjectConfig() const;
    zmpc::ProjectConfig& getProjectConfig();
    
    // 信号访问
    int getMVCount() const;
    zmpc::MVRuntime* getMVSignal(int index);
    
    // 操作
    bool startTesting(bool clear_old_data);
    bool startControlling(bool is_simulating);
    VerificationResult verifyConfiguration();
};
```

#### 3.2.3 视图模块（Views）

**职责**：用户界面展示

**视图分类**：
1. **配置视图**（Configure）
   - `ConfigureGeneralView`：通用配置
   - `ConfigureMVView`：MV 配置
   - `ConfigureDVView`：DV 配置
   - `ConfigureCVView`：CV 配置
   - `ConfigureTVView`：TV 配置
   - `ConfigureEVView`：EV 配置
   - `ConfigureExpectationView`：期望值配置

2. **辨识视图**（IDTest）
   - `IDTestMVView`：MV 辨识
   - `IDTestCVView`：CV 辨识
   - `IDTestDVView`：DV 辨识
   - `IDTestTVView`：TV 辨识
   - `IDTestSignalView`：信号辨识
   - `IDTestCovarianceView`：协方差辨识

3. **仿真视图**（Simulation）
   - `SimulationMVView`：MV 仿真
   - `SimulationDVView`：DV 仿真
   - `SimulationCVView`：CV 仿真
   - `SimulationModelView`：模型仿真
   - `SimulationGainView`：增益仿真
   - `SimulationTuningView`：调优仿真

4. **控制器视图**（Controller）
   - `ControllerMVView`：MV 控制
   - `ControllerDVView`：DV 控制
   - `ControllerCVView`：CV 控制
   - `ControllerGainView`：增益控制
   - `ControllerModelView`：模型控制
   - `ControllerTuningView`：调优控制

5. **脚本视图**（Scripts）
   - `ScriptView`：脚本编辑（Init、Before、After）

**基类设计**：
```cpp
class BaseView : public QWidget {
    // 视图更新
    virtual void updateView() = 0;
    virtual void setupUI() = 0;
    
    // 项目访问
    PIDProject* getProject() const;
};
```

#### 3.2.4 组件模块（Widgets）

**职责**：可复用 UI 组件

**主要组件**：
- `ChartWidget_QWT`：QWT 图表组件
- `DataTableWidget`：数据表格
- `ModelChart`：模型图表
- `SPCurveEditWidget`：设定值曲线编辑
- 各种对话框组件

## 4. 数据模型

### 4.1 Solution 数据模型

```
Solution
├── name: QString
├── version: QString
├── filePath: QString
├── settings: FrameworkSettings
│   ├── theme: QString
│   ├── language: QString
│   ├── autosave: bool
│   └── recentProjectsCount: int
└── projectHosts: QList<ProjectHost*>
    └── ProjectHost
        ├── name: QString
        ├── hostKey: QString
        ├── serviceHost: QString
        ├── servicePort: int
        └── stormPort: int
```

### 4.2 Project 数据模型

```
IProject (接口)
└── TaijiMPCProject
    └── PIDProject
        ├── projectInstance: zdp_base::zvm_t
        ├── projectFullData: zmpc::ProjectFull
        │   ├── baseConfig: zmpc::ProjectConfig
        │   │   ├── samplingTime: unsigned
        │   │   ├── mvConfigs: vector<MVConfig>
        │   │   ├── cvConfigs: vector<CVConfig>
        │   │   ├── dvConfigs: vector<DVConfig>
        │   │   └── ...
        │   └── runtime: zmpc::ProjectRuntime
        │       ├── mvRuntime: vector<MVRuntime>
        │       ├── cvRuntime: vector<CVRuntime>
        │       └── ...
        └── frontSetting: zmpc::ProjectFrontSetting
```

### 4.3 信号数据模型

```
信号类型层次：
├── MV (Manipulated Variable) - 操作变量
├── CV (Controlled Variable) - 控制变量
├── DV (Disturbance Variable) - 干扰变量
├── TV (Test Variable) - 测试变量
└── EV (Expectation Variable) - 期望变量

每个信号包含：
├── Config (配置)
│   ├── tagName: string
│   ├── description: string
│   ├── hiLimit/loLimit: double
│   └── ...
└── Runtime (运行时)
    ├── xvRead: double
    ├── xvWrite: double
    ├── quality: int
    └── ...
```

## 5. 接口设计

### 5.1 IProject 接口

**设计原则**：
- 最小化接口，最大化实现自由度
- 明确的职责划分
- 支持插件化扩展

**核心方法**：
```cpp
// 元数据
QString getProjectTypeName() const;
QIcon getProjectTypeIcon() const;
QString getProjectFileExtension() const;

// 生命周期
bool loadFromFile(const QString& filePath);
bool saveToFile(const QString& filePath);
bool connectProject();

// UI 创建（插件核心）
QWidget* createMainWidget(QWidget* parent);
QWidget* createPropertiesWidget(QWidget* parent);

// 操作
bool startOperation();
bool stopOperation();
bool verifyConfiguration();
```

### 5.2 视图接口

**BaseView 基类**：
```cpp
class BaseView : public QWidget {
    // 必须实现
    virtual void updateView() = 0;
    virtual void setupUI() = 0;
    
    // 可选实现
    virtual void onProjectActivated() {}
    virtual void onProjectDeactivated() {}
};
```

### 5.3 数据访问接口

**PIDProject 数据访问**：
```cpp
// 配置访问
const zmpc::ProjectConfig& getProjectConfig() const;
zmpc::ProjectConfig& getProjectConfig();

// 运行时访问
const std::vector<zmpc::MVRuntime>& getMVRuntimeSignals() const;
zmpc::MVRuntime* getMVSignal(int index);

// 信号计数
int getMVCount() const;
int getCVCount() const;
```

## 6. 关键设计决策

### 6.1 插件化架构

**决策**：采用接口 + 工厂模式的插件架构

**理由**：
- 支持多种项目类型扩展
- 框架与应用解耦
- 符合开闭原则

**实现**：
- `IProject` 接口定义契约
- `ProjectFactory` 管理注册和创建
- 各项目类型独立实现

### 6.2 Solution-ProjectHost-Project 三层结构

**决策**：采用三层管理结构

**理由**：
- Solution：用户工作空间，持久化
- ProjectHost：远程服务器连接，可配置
- Project：具体项目实例，动态加载

**优势**：
- 清晰的职责划分
- 支持多服务器管理
- 灵活的持久化策略

### 6.3 远程连接架构

**决策**：使用 ZDP 协议 + Storm 广播

**理由**：
- ZDP：RPC 调用，可靠
- Storm：实时数据推送，高效

**实现**：
- `ProjectHostServiceProxy`：ZDP RPC 代理
- Storm 订阅：按项目实例订阅 topic

### 6.4 UI 架构

**决策**：标签页 + 视图模式

**理由**：
- 标签页：多项目切换
- 视图：功能模块化

**实现**：
- MainWindow 管理标签页
- TaijiMPCProject 创建标签页 UI
- 各视图继承 BaseView

### 6.5 数据同步机制

**决策**：信号-槽机制 + 异步回调

**理由**：
- Qt 信号-槽：类型安全，解耦
- 异步回调：不阻塞 UI

**实现**：
- PIDProject 发出数据变更信号
- 视图订阅信号并更新
- 远程数据通过回调更新

## 7. 非功能性需求

### 7.1 性能要求
- UI 响应时间 < 100ms
- 数据刷新频率：可配置（默认 1Hz）
- 大项目加载时间 < 5s

### 7.2 可扩展性
- 支持添加新项目类型（无需修改框架）
- 支持添加新视图（在应用层）
- 支持自定义数据源

### 7.3 可维护性
- 代码模块化，职责清晰
- 接口文档完善
- 单元测试覆盖核心功能

### 7.4 可移植性
- 跨平台支持（Windows、Linux）
- Qt6 抽象平台差异
- CMake 统一构建

## 8. 依赖关系

### 8.1 外部依赖
- **Qt6**：GUI 框架
- **QWT**：图表库
- **libzce**：ZCE 基础库（通信、虚拟机）
- **libQTExt**：Qt 扩展库

### 8.2 内部依赖
```
MainWindow
  ├── Solution
  │   └── ProjectHost
  │       └── IProject (via ProjectFactory)
  │           └── TaijiMPCProject
  │               └── PIDProject
  └── ProjectFactory
```

## 9. 扩展点

### 9.1 新项目类型
1. 实现 `IProject` 接口
2. 注册到 `ProjectFactory`
3. 实现专属 UI 和逻辑

### 9.2 新视图
1. 继承 `BaseView`
2. 在 `TaijiMPCProject` 中创建
3. 添加到标签页

### 9.3 新数据源
1. 实现数据源接口
2. 集成到 `PIDProject`
3. 更新配置界面

## 10. 已知限制

### 10.1 当前限制
- 仅支持 TaijiMPC 项目类型（其他类型待实现）
- 远程连接需要 ZDP/Storm 服务器
- 项目文件格式固定（.tmpc）

### 10.2 未来改进
- 动态插件加载（DLL）
- 更多项目类型支持
- 云端同步功能

## 11. 测试策略

### 11.1 单元测试
- 框架组件测试
- 项目类型测试
- 数据模型测试

### 11.2 集成测试
- 端到端流程测试
- 远程连接测试
- 多项目场景测试

### 11.3 UI 测试
- 视图功能测试
- 用户交互测试
- 性能测试

## 12. 文档和规范

### 12.1 代码规范
- C++17 标准
- Qt 编码规范
- 4 空格缩进
- 类名 PascalCase，方法名 camelCase

### 12.2 文档要求
- 类和方法注释
- 架构设计文档
- 用户使用文档
