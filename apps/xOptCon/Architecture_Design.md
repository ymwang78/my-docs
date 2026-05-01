# xApc 架构设计文档

## 1. 概述

### 1.1 项目定位
xApc 是一个基于 Qt6 的模型预测控制（MPC）应用平台，采用插件化架构设计，支持多种 APC/RTO 项目类型的集成。该平台从原有的 TaiJiMPC 系统进行 Qt 移植，并重构为可扩展的插件化架构。

### 1.2 设计目标
- **可扩展性**：支持多种项目类型（TaijiMPC、线性规划优化器等）的插件式集成
- **模块化**：框架代码与应用代码清晰分离
- **可维护性**：代码结构清晰，便于维护和扩展
- **可复用性**：框架部分可被其他应用复用

### 1.3 技术栈
- **GUI框架**：Qt 6.x
- **编程语言**：C++17
- **构建系统**：CMake + Visual Studio
- **图表库**：QWT（Qt Widgets for Technical Applications）
- **通信协议**：ZDP（ZCE Data Protocol）、Storm 广播

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        MainWindow                            │
│  (主窗口，管理 Solution、ProjectHost、Project 的 UI)          │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├──────────────────────────────────────────────┐
               │                                              │
┌──────────────▼──────────────┐              ┌───────────────▼──────────────┐
│        Solution             │              │      ProjectFactory           │
│  (解决方案管理，持久化)       │              │  (项目类型注册和创建工厂)      │
│  - 管理多个 ProjectHost      │              │  - 注册项目类型               │
│  - 框架设置                  │              │  - 创建项目实例               │
│  - 持久化到 .xsln 文件       │              │  - 类型检测                   │
└──────────────┬──────────────┘              └───────────────────────────────┘
               │
               │ 1:N
               │
┌──────────────▼──────────────┐
│      ProjectHost            │
│  (项目宿主，连接远程服务器)   │
│  - 服务端点配置              │
│  - 连接管理                  │
│  - 实例列表同步              │
│  - 管理本地 Project 实例     │
└──────────────┬──────────────┘
               │
               │ 1:N
               │
┌──────────────▼──────────────┐
│      IProject               │
│  (项目接口，插件架构核心)     │
│  - 项目生命周期              │
│  - UI 创建                   │
│  - 操作管理                  │
└──────────────┬──────────────┘
               │
               │ implements
               │
┌──────────────▼──────────────┐
│   TaijiMPCProject           │
│  (TaijiMPC 插件实现)         │
│  - 包装 PIDProject          │
│  - 创建 TaijiMPC UI         │
└──────────────┬──────────────┘
               │
               │ uses
               │
┌──────────────▼──────────────┐
│      PIDProject             │
│  (MPC 项目核心逻辑)          │
│  - 信号管理 (MV/CV/DV/TV)   │
│  - 配置管理                  │
│  - 运行时数据                │
│  - 远程连接 (ZMpcRuntime)    │
└──────────────────────────────┘
```

### 2.2 分层架构

#### 2.2.1 框架层 (Framework Layer)
位于 `framework/` 目录，提供平台核心功能：

- **core/**：核心框架类
  - `MainWindow`：主窗口，管理整个应用界面
  - `Solution`：解决方案管理，持久化到 `.xsln` 文件
  - `ProjectHost`：项目宿主，管理远程连接和项目实例
  - `InstanceService`：实例服务，处理远程实例操作
  - `GlobalDefines.h`：全局定义和常量

- **interfaces/**：接口定义
  - `IProject.h`：项目接口，所有项目类型必须实现

- **plugins/**：插件系统
  - `ProjectFactory`：项目工厂，注册和创建项目类型

- **launcher/**：启动器
  - `main.cpp`：应用程序入口

- **dialogs/**：框架对话框
  - `NewProjectWizard`：新建项目向导
  - `NewConnectionDialog`：新建连接对话框
  - `ImportDataDialog`：数据导入对话框
  - `SolutionSettingsDialog`：解决方案设置对话框

#### 2.2.2 应用层 (Application Layer)
位于 `applications/` 目录，实现具体的项目类型：

- **TaijiMPC/**：TaijiMPC 应用实现
  - `TaijiMPCProject`：实现 `IProject` 接口
  - `PIDProject`：MPC 项目核心逻辑
  - `views/`：视图层（配置、监控、控制器等）
  - `widgets/`：自定义控件
  - `zmpc/`：MPC 运行时和协议

#### 2.2.3 共享库层 (Shared Libraries)
- **libQTExt**：Qt 扩展库（表格、树形视图等）
- **libQWT**：图表绘制库
- **libzce**：ZCE 基础库（通信、虚拟机等）

## 3. 核心组件设计

### 3.1 Solution（解决方案）

#### 3.1.1 职责
- 管理多个 ProjectHost
- 保存框架设置（主题、语言等）
- 持久化到 `.xsln` 文件
- 提供项目宿主的管理接口

#### 3.1.2 数据模型
```cpp
Solution {
    QString name;                    // 解决方案名称
    QString version;                 // 版本号
    QString filePath;                // 文件路径
    QList<ProjectHost*> projectHosts; // 项目宿主列表
    FrameworkSettings settings;      // 框架设置
}
```

#### 3.1.3 文件格式
Solution 文件采用 JSON 格式：
```json
{
  "name": "My Solution",
  "version": "1.0",
  "created": "2024-01-01T00:00:00",
  "modified": "2024-01-01T00:00:00",
  "settings": {
    "theme": "light",
    "language": "zh-CN",
    "autosave": true
  },
  "projectHosts": [
    {
      "name": "Production Server",
      "hostKey": "unique-id",
      "serviceHost": "localhost",
      "servicePort": 8080
    }
  ]
}
```

### 3.2 ProjectHost（项目宿主）

#### 3.2.1 职责
- 代表一个远程服务器连接
- 管理该服务器上的项目实例列表
- 处理与远程服务器的通信（通过 `ProjectHostServiceProxy`）
- 同步远程实例到本地 Project 对象

#### 3.2.2 数据模型
```cpp
ProjectHost {
    QString name;                    // 宿主名称
    QString hostKey;                 // 唯一标识
    QString serviceHost;             // 服务器地址
    int servicePort;                  // 服务端口
    int stormPort;                    // 广播端口
    bool connected;                  // 连接状态
    std::vector<IProjectPtr> projects; // 本地项目列表
    ProjectHostServiceProxy* proxy;   // 服务代理
}
```

#### 3.2.3 生命周期
1. **创建**：在 Solution 中添加 ProjectHost
2. **连接**：连接到远程服务器
3. **刷新**：从服务器获取实例列表
4. **同步**：将远程实例同步为本地 Project 对象
5. **断开**：断开连接，清理资源

### 3.3 IProject（项目接口）

#### 3.3.1 职责
- 定义所有项目类型的统一契约
- 提供项目生命周期管理
- 提供 UI 创建接口（插件架构核心）
- 提供操作和验证接口

#### 3.3.2 核心接口
```cpp
class IProject {
    // 元数据
    virtual QString getProjectTypeName() const = 0;
    virtual QIcon getProjectTypeIcon() const = 0;
    
    // 项目生命周期
    virtual bool loadFromFile(const QString& filePath) = 0;
    virtual bool saveToFile(const QString& filePath) = 0;
    virtual bool connectProject() = 0;
    
    // UI 创建（插件架构核心）
    virtual QWidget* createMainWidget(QWidget* parent) = 0;
    virtual QWidget* createPropertiesWidget(QWidget* parent) = 0;
    
    // 操作管理
    virtual bool startOperation() = 0;
    virtual bool stopOperation() = 0;
    virtual bool verifyConfiguration() = 0;
};
```

### 3.4 ProjectFactory（项目工厂）

#### 3.4.1 职责
- 注册项目类型
- 创建项目实例
- 从文件检测项目类型
- 提供类型信息查询

#### 3.4.2 注册机制
```cpp
// 在插件初始化时注册
ProjectFactory::instance().registerProjectType(
    ProjectTypeInfo("Taiji MPC", "TaijiMPC", "...", "tmpc"),
    [](ProjectHost* host) -> IProjectPtr {
        return std::make_unique<TaijiMPCProject>(host);
    }
);
```

### 3.5 TaijiMPCProject（TaijiMPC 插件）

#### 3.5.1 职责
- 实现 `IProject` 接口
- 包装 `PIDProject` 功能
- 创建 TaijiMPC 专属 UI（标签页界面）
- 管理视图同步

#### 3.5.2 UI 结构
TaijiMPC 使用标签页界面：
- **配置视图**：General、MV、DV、CV、TV、EV、Expectation
- **辨识视图**：MV、CV、DV、TV、Signal、Covariance
- **仿真视图**：MV、DV、CV、Model、Gain、Tuning
- **控制器视图**：MV、DV、CV、Gain、Model、Tuning
- **脚本视图**：Init、Before、After

### 3.6 PIDProject（MPC 项目核心）

#### 3.6.1 职责
- 管理 MPC 项目数据（配置、运行时数据）
- 管理信号（MV、CV、DV、TV、EV）
- 处理远程连接（通过 `ZMpcRuntime`）
- 提供配置验证、数据导入导出等功能

#### 3.6.2 数据模型
```cpp
PIDProject {
    zmpc::ProjectFull projectFullData;  // 完整项目数据
    zmpc::ProjectFrontSetting frontSetting; // 前端设置
    ZMpcRuntime* mpcRuntime;              // 远程运行时
    zdp_base::zvm_t projectInstance;      // 项目实例信息
}
```

## 4. 数据流和交互

### 4.1 项目创建流程

```
用户操作: 新建项目
    ↓
MainWindow::onSolutionNew()
    ↓
Solution::create()
    ↓
MainWindow::onProjectHostNewProject()
    ↓
ProjectHost::newProject()
    ↓
ProjectHostServiceProxy::callFunction("newVM")
    ↓
服务器创建实例
    ↓
ProjectHost::refreshInstances()
    ↓
ProjectHost::syncProjectsFromInstances()
    ↓
ProjectFactory::loadProject() → TaijiMPCProject
    ↓
MainWindow::switchToProject()
    ↓
显示项目 UI
```

### 4.2 项目加载流程

```
用户操作: 打开项目
    ↓
MainWindow::onInstanceOpen()
    ↓
ProjectHost::loadProject()
    ↓
ProjectHostServiceProxy::callFunction("uploadVM")
    ↓
服务器加载项目配置
    ↓
ProjectHost::refreshInstances()
    ↓
ProjectHost::syncProjectsFromInstances()
    ↓
TaijiMPCProject::connectProject()
    ↓
PIDProject::connectProject()
    ↓
ZMpcRuntime::connect()
    ↓
下载配置数据
    ↓
显示项目 UI
```

### 4.3 数据同步流程

```
远程数据更新 (Storm 广播)
    ↓
ProjectHost::onStormMessage()
    ↓
PIDProject::invokeSetProjectRuntime()
    ↓
更新本地运行时数据
    ↓
发出信号: projectChanged()
    ↓
视图更新: BaseView::updateView()
```

## 5. 插件架构

### 5.1 插件注册机制

1. **静态注册**：在编译时通过宏注册
   ```cpp
   REGISTER_PROJECT_TYPE("TaijiMPC", "Taiji MPC", "...", "tmpc", icon, TaijiMPCProject)
   ```

2. **动态注册**（未来）：运行时加载 DLL 插件

### 5.2 添加新项目类型

1. 创建项目类，实现 `IProject` 接口
2. 在插件文件中注册到 `ProjectFactory`
3. 在 `main.cpp` 中包含插件文件
4. 实现项目专属 UI 和逻辑

## 6. 持久化设计

### 6.1 Solution 文件 (.xsln)
- 格式：JSON
- 内容：Solution 元数据、ProjectHost 列表、框架设置
- 位置：用户指定

### 6.2 项目文件
- TaijiMPC：`.tmpc` 文件（通过 `PIDProject::saveToFile`）
- 其他类型：各自定义格式

## 7. 通信架构

### 7.1 服务连接
- **协议**：ZDP (ZCE Data Protocol)
- **代理**：`ProjectHostServiceProxy`
- **功能**：RPC 调用（newVM、uploadVM、deleteVM 等）

### 7.2 数据广播
- **协议**：Storm 广播
- **功能**：实时数据推送（运行时数据、状态更新等）
- **订阅**：按项目实例订阅 topic

## 8. 线程模型

### 8.1 主线程
- UI 操作和更新
- Qt 事件循环

### 8.2 工作线程
- 远程 RPC 调用（通过 `callFunctionCallbackInQt` 在 Qt 线程中回调）
- 数据同步处理

## 9. 错误处理

### 9.1 连接错误
- 显示错误消息
- 更新连接状态
- 提供重试机制

### 9.2 数据验证
- 配置验证（`verifyConfiguration`）
- 文件格式验证
- 运行时检查

## 10. 扩展点

### 10.1 新项目类型
- 实现 `IProject` 接口
- 注册到 `ProjectFactory`
- 创建专属 UI

### 10.2 新视图类型
- 继承 `BaseView`
- 在 `TaijiMPCProject` 中创建和注册

### 10.3 新数据源
- 实现数据源接口
- 集成到 `PIDProject`

## 11. 性能考虑

### 11.1 延迟加载
- 视图按需创建
- 项目数据延迟加载

### 11.2 缓存机制
- UI 组件缓存（`QPointer` 保护）
- 配置数据缓存

### 11.3 异步操作
- 远程调用异步化
- 数据同步异步化

## 12. 安全性

### 12.1 数据保护
- 配置验证
- 文件权限检查

### 12.2 连接安全
- 连接状态验证
- 超时处理

## 13. 测试策略

### 13.1 单元测试
- 框架组件测试
- 项目类型测试

### 13.2 集成测试
- 端到端流程测试
- 远程连接测试

### 13.3 UI 测试
- 视图功能测试
- 用户交互测试
