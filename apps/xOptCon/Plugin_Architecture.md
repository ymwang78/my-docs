# xApc 插件化架构设计文档

## 概述

xApc 已经成功重构为插件化平台架构，支持多种 APC/RTO 项目类型的无缝集成。本文档详细介绍了新的架构设计、实现方式和使用方法。

## 架构优势

### 原架构问题
- **紧耦合**：MainWindow 直接依赖 TaijiMPC 特定视图
- **硬编码**：所有视图类型硬编码在 MainWindow.h 中
- **单一项目类型**：只支持 PIDProject
- **扩展困难**：添加新项目类型需要大量修改核心代码

### 新架构优势
- **高度可扩展**：添加新项目类型无需修改框架代码
- **关注点分离**：项目类型开发完全独立
- **代码整洁**：消除大量 if-else 判断
- **面向对象**：符合开闭原则（对扩展开放，对修改关闭）

## 核心组件

### 1. IProject 接口 (`src/project/IProject.h`)

所有项目类型必须实现的抽象接口，定义了项目的统一契约：

```cpp
class IProject {
public:
    // 元数据
    virtual QString getProjectTypeName() const = 0;
    virtual QIcon getProjectTypeIcon() const = 0;
    virtual QString getProjectTypeDescription() const = 0;
    virtual QString getProjectFileExtension() const = 0;

    // 项目生命周期
    virtual bool createNew(const QString& directory, const QString& name) = 0;
    virtual bool loadFromFile(const QString& filePath) = 0;
    virtual bool saveToFile(const QString& filePath = QString()) = 0;
    
    // UI 创建（插件架构核心）
    virtual QWidget* createMainWidget(QWidget* parent = nullptr) = 0;
    virtual QWidget* createPropertiesWidget(QWidget* parent = nullptr) = 0;
    
    // 项目操作
    virtual bool startOperation() = 0;
    virtual bool stopOperation() = 0;
    virtual bool verifyConfiguration(QStringList* errors, QStringList* warnings) = 0;
    
    // 数据导入导出
    virtual QStringList getSupportedImportFormats() const = 0;
    virtual QStringList getSupportedExportFormats() const = 0;
    virtual bool importData(const QString& filePath, const QString& format) = 0;
    virtual bool exportData(const QString& filePath, const QString& format) = 0;
    
    // 序列化支持
    virtual QJsonObject toJson() const = 0;
    virtual bool fromJson(const QJsonObject& json) = 0;
};
```

### 2. ProjectFactory 工厂类 (`src/project/ProjectFactory.h`)

负责项目类型的注册和创建：

```cpp
class ProjectFactory {
public:
    static ProjectFactory& instance();
    
    // 项目类型注册
    bool registerProjectType(const ProjectTypeInfo& typeInfo, ProjectCreator creator);
    
    // 项目创建
    IProjectPtr createProject(const QString& typeId) const;
    IProjectPtr createProjectFromFile(const QString& filePath) const;
    
    // 类型信息查询
    QList<ProjectTypeInfo> getRegisteredTypes() const;
    QString getFileFilter(const QString& typeId = QString()) const;
};
```

### 3. TaijiMPCProject 插件实现 (`src/project/TaijiMPCProject.h`)

TaijiMPC 的插件化实现，包装现有的 PIDProject：

```cpp
class TaijiMPCProject : public QObject, public IProject {
public:
    // 实现 IProject 接口
    QString getProjectTypeName() const override { return "Taiji MPC"; }
    QWidget* createMainWidget(QWidget* parent = nullptr) override;
    
    // TaijiMPC 特定功能
    PIDProject* getPIDProject() const { return m_pidProject.get(); }
    
private:
    std::unique_ptr<PIDProject> m_pidProject;  // 包装现有实现
    QWidget* m_mainWidget;                     // 缓存的主界面
};
```

### 4. MainWindowPlugin 插件化主窗口 (`src/MainWindowPlugin.h`)

新的主窗口完全通过 IProject 接口工作：

```cpp
class MainWindowPlugin : public QMainWindow {
public:
    // 项目管理
    bool createNewProject();
    bool openProject(const QString& fileName = QString());
    bool saveProject();
    bool closeProject();
    
    // 当前项目访问
    IProject* getCurrentProject() const;
    
private:
    QList<IProjectPtr> m_projects;        // 支持多项目
    int m_currentProjectIndex;
    QTreeWidget* m_projectTree;           // 项目树
    QTabWidget* m_mainTabs;               // 主标签页
};
```

## 项目文件格式

新的项目文件采用 JSON 格式，包含项目类型标识：

```json
{
  "projectType": "TaijiMPC",
  "projectFormatVersion": "1.0",
  "projectName": "MyProject",
  "creationTime": "2024-08-04T15:30:00",
  "lastModified": "2024-08-04T15:35:00",
  "data": {
    "samplingTime": 30,
    "samplingTimeUnit": "seconds",
    "isRealPlant": true,
    "watchdogEnabled": true,
    "mvCount": 5,
    "cvCount": 3,
    "dvCount": 2
  }
}
```

## 添加新项目类型

### 步骤 1：创建项目类

```cpp
// src/project/MyNewProject.h
class MyNewProject : public QObject, public IProject {
    Q_OBJECT
public:
    // 实现所有 IProject 接口方法
    QString getProjectTypeName() const override { return "My New Optimizer"; }
    QIcon getProjectTypeIcon() const override { return QIcon(":/icons/my_optimizer.png"); }
    QString getProjectTypeDescription() const override { 
        return "Linear Programming Optimizer for resource allocation"; 
    }
    QString getProjectFileExtension() const override { return "lpopt"; }
    
    QWidget* createMainWidget(QWidget* parent = nullptr) override {
        // 创建您的专属UI界面
        return new MyOptimizerMainWidget(parent);
    }
    
    // ... 实现其他方法
};
```

### 步骤 2：注册插件

```cpp
// src/project/MyNewProjectPlugin.cpp
void registerMyNewProjectPlugin() {
    ProjectFactory::ProjectTypeInfo typeInfo(
        "My New Optimizer",       // 显示名称
        "MyNewOptimizer",         // 类型ID
        "Linear Programming...",  // 描述
        "lpopt",                  // 文件扩展名
        QIcon(":/icons/my_optimizer.png")
    );
    
    ProjectFactory::instance().registerProjectType(
        typeInfo,
        []() -> IProjectPtr {
            return std::make_unique<MyNewProject>();
        }
    );
}

// 自动注册
static class MyNewProjectRegistrar {
public:
    MyNewProjectRegistrar() { registerMyNewProjectPlugin(); }
} g_myNewProjectRegistrar;
```

### 步骤 3：链接插件

在 `main.cpp` 中包含插件：

```cpp
#include "project/TaijiMPCPlugin.cpp"
#include "project/MyNewProjectPlugin.cpp"  // 添加新插件
```

## 用户界面

### 新建项目向导
- 显示所有已注册的项目类型
- 提供项目类型描述
- 配置项目名称和路径
- 自动验证和创建目录

### 项目树
- 显示当前打开的所有项目
- 支持多项目同时工作
- 右键菜单提供项目操作

### 主工作区
- 每个项目类型提供自定义的主界面
- 标签页方式管理多个项目
- 项目间独立操作，互不影响

### 菜单功能
- 文件菜单：新建、打开、保存、关闭项目
- 工具菜单：配置验证、数据导入导出
- 插件管理器（规划中）

## 技术特性

### 多项目支持
- 同时打开多个不同类型的项目
- 项目间独立操作和状态管理
- 统一的项目管理界面

### 类型安全
- 通过 IProject 接口保证类型安全
- 工厂模式确保正确的对象创建
- 智能指针管理内存安全

### 配置持久化
- 支持 JSON 序列化/反序列化
- 项目配置自动保存和恢复
- 扩展性强的数据格式

### 错误处理
- 完善的配置验证机制
- 友好的错误信息提示
- 优雅的错误恢复策略

## 兼容性

### 向后兼容
- TaijiMPC 功能完全保留
- 现有项目文件可以升级
- 用户界面保持熟悉

### 前向兼容
- 插件接口版本化管理
- 渐进式功能添加
- 平滑的升级路径

## 性能优化

### 延迟加载
- 视图组件按需创建
- 项目数据延迟加载
- UI 响应性能优化

### 内存管理
- 智能指针自动管理
- 缓存机制减少重复创建
- 及时释放未使用资源

## 开发指南

### 项目类型开发
1. 继承 IProject 接口
2. 实现所有纯虚函数
3. 创建专属的 UI 组件
4. 实现数据序列化
5. 注册插件到工厂

### 调试技巧
- 使用 qDebug() 输出调试信息
- 检查插件注册日志
- 验证 JSON 数据格式
- 测试项目生命周期

### 最佳实践
- 遵循接口契约
- 保持UI响应性
- 处理异常情况
- 提供用户反馈
- 文档化接口变更

## 未来扩展

### 动态插件系统
- 运行时加载插件 DLL
- 插件热更新支持
- 插件依赖管理

### 插件市场
- 第三方插件分发
- 版本兼容性检查
- 数字签名验证

### 云端集成
- 项目云端同步
- 协作功能支持
- 远程计算资源

## 总结

通过插件化架构重构，xApc 成功转型为可扩展的 APC/RTO 平台。新架构不仅保持了 TaijiMPC 的完整功能，还为未来添加更多项目类型奠定了坚实基础。

这个架构遵循了软件工程的最佳实践，实现了高内聚、低耦合的设计目标，为 xApc 的长期发展提供了强大的技术支撑。