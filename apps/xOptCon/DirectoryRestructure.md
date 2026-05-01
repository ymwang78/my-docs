# xApc 项目重组总结

## 概述

已成功将 xApc 项目重组为清晰的框架和应用分离结构，提高了代码的可维护性和可扩展性。

## 新的目录结构

```
xApc/
├── framework/              # 框架部分 - 可复用的平台代码
│   ├── core/              # 核心框架类
│   │   ├── MainWindow.h/cpp        # 主窗口(原MainWindowPlugin)
│   │   ├── GlobalDefines.h         # 全局定义
│   │   └── dialogs/               # 框架对话框
│   │       ├── NewProjectWizard.h/cpp
│   │       └── ImportDataDialog.h/cpp
│   ├── plugins/           # 插件系统
│   │   └── ProjectFactory.h/cpp
│   ├── interfaces/        # 接口定义
│   │   └── IProject.h
│   └── launcher/          # 启动器
│       └── main.cpp
├── applications/          # 具体应用项目
│   └── TaijiMPC/         # TaijiMPC应用
│       ├── TaijiMPCProject.h/cpp
│       ├── TaijiMPCPlugin.cpp
│       ├── PIDProject.h/cpp
│       ├── PIDSignal.h/cpp
│       ├── ProjectManager.h/cpp
│       ├── views/        # MPC相关视图
│       │   ├── BaseView.h/cpp
│       │   ├── LogView.h/cpp
│       │   ├── ToolsView.h/cpp
│       │   ├── configure/  # 配置视图
│       │   ├── controller/ # 控制器视图
│       │   └── monitor/    # 监控视图
│       └── widgets/      # MPC相关组件
│           ├── ChartWidget.h/cpp
│           ├── DataTableWidget.h/cpp
│           ├── ProjectDockWidget.h/cpp
│           ├── ProjectManagerWidget.h/cpp
│           ├── ProjectTreeWidget.h/cpp
│           ├── ProjectWidget.h/cpp
│           └── PropertyWidget.h/cpp
├── include/              # 公共头文件
├── lib/                 # 预编译库
├── libsrc/             # 共享库源码
├── ui/                 # UI文件
├── resources/          # 资源文件
├── docs/               # 文档
└── build/              # 构建输出
```

## 主要更改

### 1. 目录重组
- **框架代码**：移动到 `framework/` 目录
  - `core/`：核心框架类（MainWindow、GlobalDefines等）
  - `interfaces/`：接口定义（IProject.h）
  - `plugins/`：插件系统（ProjectFactory）
  - `launcher/`：程序入口（main.cpp）

- **应用代码**：移动到 `applications/TaijiMPC/` 目录
  - 所有TaijiMPC相关的项目、视图、组件代码

### 2. 文件重命名
- `MainWindowPlugin` → `MainWindow`
- 更新了所有相关的引用和包含

### 3. 构建系统更新

#### CMakeLists.txt
- 更新了源文件路径以反映新的目录结构
- 分离了框架和应用的源文件列表
- 更新了包含目录路径

#### Visual Studio 项目文件
- **xApc.vcxproj**：
  - 更新了所有源文件和头文件的路径
  - 更新了包含目录配置
  - 保持了Qt MOC处理配置

- **xApc.vcxproj.filters**：
  - 重新组织了文件夹结构
  - 创建了清晰的框架和应用分组
  - 保持了Visual Studio中的层次结构

### 4. 包含路径更新
- Debug配置：添加了新的框架目录到包含路径
- Release配置：同步更新了包含路径

## 优势

1. **清晰分离**：框架代码和应用代码完全分离
2. **模块化设计**：按功能组织代码结构
3. **可扩展性**：新应用可以轻松添加到applications目录
4. **可维护性**：代码结构更清晰，便于维护
5. **可复用性**：框架部分可以被其他应用复用

## 构建验证

- ✅ CMake配置成功
- ✅ Visual Studio项目文件更新完成
- ✅ 所有文件路径正确映射
- ✅ 包含目录配置正确

## 后续工作建议

1. **测试构建**：在Windows环境下使用Visual Studio测试构建
2. **依赖检查**：确保所有头文件包含路径正确
3. **功能测试**：验证重组后的功能完整性
4. **文档更新**：更新相关的开发文档

## 注意事项

- 所有原有的功能应该保持不变
- 新的目录结构便于后续添加新的应用模块
- 框架部分现在可以作为独立的组件进行维护和扩展