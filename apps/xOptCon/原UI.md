# TaiJiMPC UI界面说明书

## 1. 概述

TaiJiMPC是一个基于Windows的模型预测控制(MPC)软件，采用MFC框架开发。本文档详细描述了TaiJiMPC的UI界面结构、各个界面元素及其关系，为Qt移植开发提供指导。

## 2. 主窗口结构

### 2.1 主框架窗口 (MainFrame)
- **类名**: `CMainFrame`
- **基类**: `CFrameWindowImpl<CMainFrame>`
- **功能**: 应用程序的主窗口框架

#### 2.1.1 窗口布局
```
主窗口
├── 菜单栏 (Menu Bar)
├── 工具栏 (Toolbar)
├── 分割窗口 (Splitter Windows)
│   ├── 左侧面板 (可选)
│   └── 右侧主工作区
│       ├── 上部：视图区域
│       └── 下部：工具面板
└── 状态栏 (Status Bar)
```

#### 2.1.2 分割器结构
- **垂直分割器**: `m_vetSplit` (可选的项目树面板)
- **水平分割器**: `m_horSplit` (主工作区和工具面板)

### 2.2 菜单系统

#### 2.2.1 主菜单 (IDR_MAINFRAME)
```
文件 (File)
├── 新建 (New) - Ctrl+N
├── 打开 (Open) - Ctrl+O
├── 保存 (Save) - Ctrl+S
├── 另存为 (Save As)
├── 导入辨识数据 (Import Data for Ident)
├── 导出MPC项目 (Export MPC Project)
├── 最近项目 (Recent Project)
├── 加载CSV数据文件 (Load CSV Data File)
├── 保存CSV数据文件 (Save CSV Data File)
├── 打印 (Print) - Ctrl+P
└── 退出 (Exit)

视图 (View)
├── 工具栏 (Toolbar)
├── 状态栏 (Status Bar)
├── LPV窗口 (LPV)
└── 日志 (Log)

工具 (Tools)
├── 验证OPC连接 (Verify OPC Connection)
├── 跟踪平均 (Tracking Average)
├── 在控制中使用脚本 (Use Script in Control)
├── 编辑脚本 (Edit Script)
├── 转置MV,CV (Transpose MV,CV)
├── 显示轴为时间 (Show Axes As Time)
├── 绘制稳态 (Plot Steady State)
├── 内部状态 (Inner Status)
├── 保存数据到CSV文件 (Save Data to CSV Files)
├── 锁定TaiJiMPC (Lock TaiJiMPC)
├── 解锁TaiJiMPC (UnLock TaiJiMPC)
└── 保存日志到文件 (Save Log to File)

导出模型 (Export Model)
├── 低阶+延迟 (LowOrder+Delay)
├── DMC格式 (DMC Format)
└── Septic

帮助 (Help)
└── 关于TaiJiMPC (About TaiJiMPC)
```

#### 2.2.2 工具栏 (Toolbar)
- **ID**: `IDR_MAINFRAME`
- **按钮**: 新建、打开、保存、日志、打印、关于

### 2.3 状态栏
- **状态栏ID**: 包含4个面板
  - `STATUSBAR_ID_X`: X坐标
  - `STATUSBAR_ID_Y`: Y坐标  
  - `STATUSBAR_NAME`: 名称
  - `STATUSBAR_STATUS`: 测试/控制状态

## 3. 主要视图窗口

### 3.1 配置视图 (Configuration Views)

#### 3.1.1 通用配置 (General Configuration)
- **类名**: `CConfigureGeneralView`
- **对话框ID**: `IDD_FORMVIEW_CONFIG_GENERAL`
- **功能**: 项目基本配置
- **主要控件**:
  - 数据源配置 (Datasource)
  - 时间设置 (Times)
  - 看门狗设置 (Watch Dog)
  - 选项设置 (Options)
  - HostVM服务 (HostVM Service)
  - 许可证信息 (License)
  - 通用设置 (General)

#### 3.1.2 MV配置 (MV Configuration)
- **类名**: `CConfigureMVView`
- **对话框ID**: `IDD_FORMVIEW_CONFIG_XV`
- **功能**: 操纵变量配置
- **主要控件**:
  - MV列表网格
  - 添加/删除/移动按钮
  - MV和测试标签配置

#### 3.1.3 DV配置 (DV Configuration)
- **类名**: `CConfigureDVView`
- **功能**: 干扰变量配置

#### 3.1.4 CV配置 (CV Configuration)
- **类名**: `CConfigureCVView`
- **功能**: 控制变量配置

#### 3.1.5 TV配置 (TV Configuration)
- **类名**: `CConfigureTVView`
- **功能**: 测试信号配置

#### 3.1.6 期望值配置 (Expectation Configuration)
- **类名**: `CConfigureExpectationView`
- **对话框ID**: `IDD_FORMVIEW_CONFIG_EXPECTATION`
- **功能**: 期望值矩阵配置

#### 3.1.7 多模型配置 (Multi-Model Configuration)
- **类名**: `CConfigureMultiModelView`
- **对话框ID**: `IDD_FORMVIEW_CONFIG_MULTIMODEL`
- **功能**: 多模型配置

### 3.2 监控视图 (Monitor Views)

#### 3.2.1 MV监控 (MV Monitor)
- **类名**: `CMonitorMVView`
- **对话框ID**: `IDD_FORMVIEW_MONITOR_XV`
- **功能**: 操纵变量监控
- **主要控件**:
  - 曲线显示画布
  - 控制按钮 (ON/OFF, 全部开启/关闭, 开始/停止测试)
  - 配置选项卡
  - 数据网格

#### 3.2.2 DV监控 (DV Monitor)
- **类名**: `CMonitorDVView`
- **功能**: 干扰变量监控

#### 3.2.3 CV监控 (CV Monitor)
- **类名**: `CMonitorCVView`
- **功能**: 控制变量监控

#### 3.2.4 TV监控 (TV Monitor)
- **类名**: `CMonitorTVView`
- **功能**: 测试信号监控

#### 3.2.5 测试信号监控 (Test Signal Monitor)
- **类名**: `CMonitorTestSignalView`
- **对话框ID**: `IDD_FORMVIEW_MONITOR_TESTSIGNAL`
- **功能**: 测试信号监控

#### 3.2.6 协方差监控 (Covariance Monitor)
- **类名**: `CMonitorCovarianceView`
- **对话框ID**: `IDD_FORMVIEW_MONITOR_COVARIANCE`
- **功能**: 协方差矩阵监控

### 3.3 模型辨识视图 (Model Identification Views)

#### 3.3.1 MV模型辨识 (MV Model ID)
- **类名**: `CModelIDMVView`
- **对话框ID**: `IDD_FORMVIEW_MODELID_XV`
- **功能**: MV模型辨识

#### 3.3.2 CV模型辨识 (CV Model ID)
- **类名**: `CModelIDCVView`
- **功能**: CV模型辨识

#### 3.3.3 模型响应 (Model Response)
- **类名**: `CModelIDModelResponseView`
- **功能**: 模型响应显示

#### 3.3.4 延迟配置 (Delay Configuration)
- **类名**: `CModelIDDelayView`
- **对话框ID**: `IDD_FORMVIEW_CONFIG_DELAY`
- **功能**: 延迟时间配置

#### 3.3.5 增益配置 (Gain Configuration)
- **类名**: `CModelIDGainView`
- **对话框ID**: `IDD_FORMVIEW_MODELID_GAIN`
- **功能**: 增益配置

### 3.4 控制器视图 (Controller Views)

#### 3.4.1 MV控制器 (MV Controller)
- **类名**: `CControllerMVView`
- **对话框ID**: `IDD_FORMVIEW_CONTROLLERVIEW_XV`
- **功能**: MV控制器配置

#### 3.4.2 DV控制器 (DV Controller)
- **类名**: `CControllerDVView`
- **功能**: DV控制器配置

#### 3.4.3 CV控制器 (CV Controller)
- **类名**: `CControllerCVView`
- **功能**: CV控制器配置

#### 3.4.4 EV控制器 (EV Controller)
- **类名**: `CControllerEVView`
- **功能**: EV控制器配置

#### 3.4.5 控制器模型 (Controller Model)
- **类名**: `CControllerMultiModelView`
- **功能**: 控制器模型配置

#### 3.4.6 控制器增益 (Controller Gain)
- **类名**: `CControllerGainView`
- **对话框ID**: `IDD_CONTROLLER_GAIN`
- **功能**: 控制器增益配置

#### 3.4.7 控制器增益因子 (Controller Gain Factor)
- **类名**: `CControllerGainFactorView`
- **对话框ID**: `IDD_CONTROLLER_GAINFACTOR`
- **功能**: 控制器增益因子配置

#### 3.4.8 控制器调优 (Controller Tuning)
- **类名**: `CControllerTuningView`
- **对话框ID**: `IDD_CONTROLLER_TUNING`
- **功能**: 控制器参数调优

### 3.5 控制器仿真视图 (Controller Simulation Views)

#### 3.5.1 仿真MV控制器 (Simulation MV Controller)
- **类名**: `CControllerSimMVView`
- **功能**: 仿真MV控制器

#### 3.5.2 仿真DV控制器 (Simulation DV Controller)
- **类名**: `CControllerSimDVView`
- **功能**: 仿真DV控制器

#### 3.5.3 仿真CV控制器 (Simulation CV Controller)
- **类名**: `CControllerSimCVView`
- **功能**: 仿真CV控制器

#### 3.5.4 仿真EV控制器 (Simulation EV Controller)
- **类名**: `CControllerSimEVView`
- **功能**: 仿真EV控制器

#### 3.5.5 仿真控制器增益 (Simulation Controller Gain)
- **类名**: `CControllerSimGainView`
- **对话框ID**: `IDD_SIMCONTROLLER_GAIN`
- **功能**: 仿真控制器增益

#### 3.5.6 仿真控制器调优 (Simulation Controller Tuning)
- **类名**: `CControllerSimTuningView`
- **对话框ID**: `IDD_SIMCONTROLLER_TUNING`
- **功能**: 仿真控制器调优

## 4. 对话框窗口

### 4.1 数据导入对话框

#### 4.1.1 CSV文件加载对话框
- **对话框ID**: `IDD_DIALOG_LOADCSVFILE`
- **功能**: MV/DV/CV选择
- **主要控件**:
  - 所有标签列表
  - MV/DV/CV/DT标签列表
  - 添加/删除按钮
  - 确定/取消按钮

#### 4.1.2 辨识数据导入对话框
- **对话框ID**: `IDD_DIALOG_IMPORTIDENTDATA`
- **功能**: 导入测试数据
- **主要控件**:
  - 数据文件选择
  - 清除旧数据选项
  - 文件路径输入框

### 4.2 模型配置对话框

#### 4.2.1 添加模型对话框
- **对话框ID**: `IDD_DIALOG_ADD_MODEL`
- **功能**: 添加/重置控制器模型
- **主要控件**:
  - 模型阶数选择 (1阶/2阶/3阶)
  - 积分选项
  - 传递函数参数输入
  - 延迟时间设置

#### 4.2.2 修改模型对话框
- **对话框ID**: `IDD_DIALOG_MODIFY_MODEL`
- **功能**: 修改控制器模型
- **主要控件**:
  - 模型预览画布
  - 起始样本设置
  - 过渡样本设置
  - 新增益设置

#### 4.2.3 多重增益对话框
- **对话框ID**: `IDD_DIALOG_MUTIPLE_GAIN`
- **功能**: 修改控制器模型增益
- **主要控件**:
  - 模型预览画布
  - 放大倍数设置
  - 旧增益显示

#### 4.2.4 过滤模型对话框
- **对话框ID**: `IDD_DIALOG_FILTER_MODEL`
- **功能**: 零初始系数设置
- **主要控件**:
  - 模型预览画布
  - 起始/结束样本设置
  - 新值设置

### 4.3 控制器配置对话框

#### 4.3.1 控制器调优对话框
- **对话框ID**: `IDD_CONTROLLER_TUNING`
- **功能**: 控制器参数调优
- **主要控件**:
  - 自动调优按钮
  - MV调优列表
  - CV调优列表
  - 在仿真中使用参数按钮

#### 4.3.2 仿真控制器调优对话框
- **对话框ID**: `IDD_SIMCONTROLLER_TUNING`
- **功能**: 仿真控制器参数调优
- **主要控件**:
  - 自动调优按钮
  - MV调优列表
  - CV调优列表
  - 在控制器中使用参数按钮

#### 4.3.3 控制器调优助手对话框
- **对话框ID**: `IDD_CONTROLLER_TUNINGHELPER`
- **功能**: 控制器调优助手
- **主要控件**:
  - 在控制器中使用结果按钮
  - 在仿真中使用结果按钮
  - MV/CV调优列表
  - MV权重滑块

### 4.4 特殊功能对话框

#### 4.4.1 计算函数对话框
- **对话框ID**: `IDD_DIALOG_CALCULATEDFUN`
- **功能**: CV计算函数编辑
- **主要控件**:
  - 函数编辑框
  - 语法检查按钮
  - 示例说明

#### 4.4.2 脚本参数对话框
- **对话框ID**: `IDD_DIALOG_SCRIPTPARAMETER`
- **功能**: 自定义变量配置
- **主要控件**:
  - 参数名称/类型/读写设置
  - 标签名称/值设置
  - 导航按钮

#### 4.4.3 仿真周期对话框
- **对话框ID**: `IDD_DIALOG_SIMULATIONPERIOD`
- **功能**: 仿真采样时间设置

#### 4.4.4 选择模型对话框
- **对话框ID**: `IDD_DIALOG_SELECTMODEL`
- **功能**: 多模型选择

#### 4.4.5 期望值更改对话框
- **对话框ID**: `IDD_DIALOG_CHANGEEXPECT`
- **功能**: 更改期望值

#### 4.4.6 分割阶跃响应对话框
- **对话框ID**: `IDD_DIALOG_DIVIDESTPRESP`
- **功能**: 分割模型

#### 4.4.7 锁定对话框
- **对话框ID**: `IDD_LOCKBOX`
- **功能**: 应用程序锁定
- **主要控件**:
  - 密码输入框
  - 解锁按钮

#### 4.4.8 关于对话框
- **对话框ID**: `IDD_ABOUTBOX`
- **功能**: 程序信息显示

### 4.5 高级功能对话框

#### 4.5.1 设定点曲线对话框
- **对话框ID**: `IDD_DIALOG_SPCURVE`
- **功能**: 设定点曲线设置
- **主要控件**:
  - 类型选择 (无/斜率/分段)
  - 斜率配置
  - 分段定义
  - X轴标签设置

#### 4.5.2 DV预测对话框
- **对话框ID**: `IDD_DIALOG_DVPRED`
- **功能**: DV预测模块配置
- **主要控件**:
  - DV预测标签选择
  - DV预测长度设置

#### 4.5.3 克隆工作点对话框
- **对话框ID**: `IDD_DIALOG_CLONEWOKRPOINT`
- **功能**: 克隆模型到新工作点
- **主要控件**:
  - 当前工作点显示
  - 新工作点输入

## 5. 工具面板

### 5.1 工具视图 (Tools View)
- **类名**: `CMyToolsView`
- **功能**: 工具面板显示

### 5.2 日志视图 (Log View)
- **类名**: `CMyLogView`
- **对话框ID**: `IDD_DIALOG_LOG`
- **功能**: 日志信息显示
- **主要控件**:
  - 日志列表视图
  - 事件/时间列

## 6. 属性页

### 6.1 自定义变量属性页
- **对话框ID**: `IDD_PROPPAGE_CUSTOMVARIABLE`
- **功能**: 自定义变量配置

### 6.2 输出脚本属性页
- **对话框ID**: `IDD_PROPPAGE_OUTPUTSCRIPT`
- **功能**: 输出脚本编辑

### 6.3 初始化脚本属性页
- **对话框ID**: `IDD_PROPPAGE_INITSCRIPT`
- **功能**: 初始化脚本编辑

### 6.4 输入脚本属性页
- **对话框ID**: `IDD_PROPPAGE_INPUTSCRIPT`
- **功能**: 输入脚本编辑

### 6.5 新项目向导属性页
- **对话框ID**: `IDD_PROPPAGE_WIZARD_NEWPROJECT`
- **功能**: 新项目创建向导

## 7. 界面元素关系图

```
主窗口 (CMainFrame)
├── 菜单栏
│   ├── 文件菜单 → 项目操作
│   ├── 视图菜单 → 界面显示控制
│   ├── 工具菜单 → 功能操作
│   └── 帮助菜单 → 程序信息
├── 工具栏 → 快捷操作
├── 分割窗口
│   ├── 左侧面板 (可选) → 项目树
│   └── 右侧主工作区
│       ├── 配置视图组 → 项目配置
│       │   ├── 通用配置 → 基本设置
│       │   ├── MV配置 → 操纵变量
│       │   ├── DV配置 → 干扰变量
│       │   ├── CV配置 → 控制变量
│       │   ├── TV配置 → 测试信号
│       │   └── 期望值配置 → 期望矩阵
│       ├── 监控视图组 → 实时监控
│       │   ├── MV监控 → 操纵变量监控
│       │   ├── DV监控 → 干扰变量监控
│       │   ├── CV监控 → 控制变量监控
│       │   ├── TV监控 → 测试信号监控
│       │   └── 协方差监控 → 统计信息
│       ├── 模型辨识视图组 → 模型建立
│       │   ├── MV模型辨识 → 操纵变量模型
│       │   ├── CV模型辨识 → 控制变量模型
│       │   ├── 模型响应 → 模型验证
│       │   ├── 延迟配置 → 时间延迟
│       │   └── 增益配置 → 模型增益
│       ├── 控制器视图组 → 控制器设计
│       │   ├── MV控制器 → 操纵变量控制
│       │   ├── DV控制器 → 干扰变量控制
│       │   ├── CV控制器 → 控制变量控制
│       │   ├── EV控制器 → 期望变量控制
│       │   ├── 控制器模型 → 模型配置
│       │   ├── 控制器增益 → 增益配置
│       │   └── 控制器调优 → 参数调优
│       └── 控制器仿真视图组 → 仿真验证
│           ├── 仿真MV控制器 → 仿真操纵变量控制
│           ├── 仿真DV控制器 → 仿真干扰变量控制
│           ├── 仿真CV控制器 → 仿真控制变量控制
│           ├── 仿真EV控制器 → 仿真期望变量控制
│           ├── 仿真控制器增益 → 仿真增益配置
│           └── 仿真控制器调优 → 仿真参数调优
│       └── 工具面板
│           ├── 工具视图 → 工具面板
│           └── 日志视图 → 日志信息
└── 状态栏 → 状态信息
```

## 8. 数据流关系

### 8.1 配置数据流
```
配置视图 → 项目配置对象 → 数据源连接 → 实时数据
```

### 8.2 监控数据流
```
实时数据 → 数据源 → 监控视图 → 曲线显示/数据网格
```

### 8.3 模型辨识数据流
```
测试数据 → 模型辨识算法 → 模型参数 → 模型响应视图
```

### 8.4 控制器数据流
```
模型参数 → 控制器配置 → 控制器算法 → 控制输出
```

## 9. Qt移植建议

### 9.1 窗口结构移植
1. **主窗口**: 使用`QMainWindow`替代`CMainFrame`
2. **分割器**: 使用`QSplitter`替代`CSplitterWindow`
3. **标签页**: 使用`QTabWidget`替代`CTabCtrl`
4. **工具栏**: 使用`QToolBar`替代`CToolBar`
5. **状态栏**: 使用`QStatusBar`替代`CStatusBar`

### 9.2 视图移植
1. **配置视图**: 使用`QWidget`+`QFormLayout`/`QGridLayout`
2. **监控视图**: 使用`QWidget`+`QChart`(Qt Charts)
3. **数据网格**: 使用`QTableView`+`QStandardItemModel`
4. **曲线显示**: 使用`QChartView`+`QLineSeries`

### 9.3 对话框移植
1. **模态对话框**: 使用`QDialog`
2. **非模态对话框**: 使用`QWidget`+`Qt::Window`
3. **属性页**: 使用`QTabWidget`或`QStackedWidget`

### 9.4 数据模型移植
1. **项目数据**: 使用`QObject`派生类
2. **配置数据**: 使用`QSettings`或自定义配置类
3. **实时数据**: 使用信号槽机制
4. **模型数据**: 使用`QAbstractItemModel`派生类

### 9.5 通信机制移植
1. **OPC通信**: 使用Qt的COM支持或第三方OPC库
2. **数据源连接**: 使用Qt的网络和串口支持
3. **事件处理**: 使用Qt的信号槽机制
4. **定时器**: 使用`QTimer`

### 9.6 界面风格移植
1. **主题**: 使用Qt的样式表(QSS)
2. **图标**: 使用Qt的图标系统
3. **字体**: 使用Qt的字体系统
4. **布局**: 使用Qt的布局管理器

## 10. 总结

TaiJiMPC的UI界面结构清晰，功能模块化程度高，主要分为配置、监控、模型辨识、控制器设计和仿真验证五大功能模块。每个模块都有相应的视图窗口和配置对话框，通过主窗口的统一管理实现功能的协调工作。

Qt移植时需要保持原有的功能模块划分，充分利用Qt的现代化UI组件和信号槽机制，实现更好的用户体验和跨平台支持。 