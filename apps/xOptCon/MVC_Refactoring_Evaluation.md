# TaijiMPC MVC 重构方案评估

## 方案概述

**重构目标：**
1. `TaijiMPCProject` → Controller（实现 IProject 接口）
2. `PIDProject` → `TaijiMPCModel`（直接使用，不需要接口类）
3. 新增 `TaijiMPCView`（管理 m_mainWidget 和所有子视图）

## 方案合理性分析

### ✅ 优点

1. **职责分离清晰**
   - Controller：实现 IProject 接口，协调 Model 和 View
   - Model：数据管理和业务逻辑
   - View：UI 展示和管理

2. **符合 MVC 模式**
   - 三层架构清晰
   - 依赖方向正确（Controller 依赖 Model 和 View）

3. **简化设计**
   - 不需要接口类，直接使用 TaijiMPCModel
   - 减少抽象层次

### ⚠️ 需要明确的问题

#### 1. 视图同步逻辑的位置

**当前代码：** `setupViewSynchronization()` 在 TaijiMPCProject 中，连接 Model 信号到多个视图

**问题：** 这个逻辑应该放在哪里？

**选项 A：放在 Controller（推荐）**
```cpp
// TaijiMPCProject (Controller)
void setupViewSynchronization() {
    connect(m_model.get(), &TaijiMPCModel::mvDataChanged, this, [this]() {
        m_view->markViewsDirty(...);
        m_view->updateCurrentView();
    });
}
```

**选项 B：放在 View**
```cpp
// TaijiMPCView
void setupViewSynchronization(TaijiMPCModel* model) {
    connect(model, &TaijiMPCModel::mvDataChanged, this, [this]() {
        markViewsDirty(...);
        updateCurrentView();
    });
}
```

**建议：** 放在 **Controller**，因为：
- 这是协调逻辑，属于 Controller 职责
- Controller 知道需要更新哪些视图
- View 不应该直接监听 Model 信号（违反 MVC 依赖方向）

#### 2. getCurrentView() 的位置

**当前代码：** `getCurrentView()` 在 TaijiMPCProject 中，被 BaseView 调用

**问题：** 这个方法应该放在哪里？

**选项 A：放在 View（推荐）**
```cpp
// TaijiMPCView
BaseView* getCurrentView() const {
    // 访问 m_mainWidget 的内部结构
}
```

**选项 B：放在 Controller**
```cpp
// TaijiMPCProject
BaseView* getCurrentView() const {
    return m_view->getCurrentView();
}
```

**建议：** 放在 **View**，因为：
- 这是 View 的内部状态查询
- View 知道自己的结构
- Controller 可以通过 View 的接口访问

#### 3. updateCurrentView() 的位置

**当前代码：** `updateCurrentView()` 在 TaijiMPCProject 中，在多个地方被调用

**问题：** 这个方法应该放在哪里？

**选项 A：放在 View，由 Controller 触发（推荐）**
```cpp
// TaijiMPCView
void updateCurrentView(bool forced = false) {
    // 更新当前视图的逻辑
}

// TaijiMPCProject (Controller)
void onModelChanged() {
    m_view->updateCurrentView();
}
```

**选项 B：放在 Controller**
```cpp
// TaijiMPCProject
void updateCurrentView(bool forced = false) {
    BaseView* current = m_view->getCurrentView();
    if (current) {
        current->updateView(forced);
    }
}
```

**建议：** 放在 **View**，但由 **Controller 触发**，因为：
- 更新逻辑属于 View 职责
- Controller 负责协调和触发

#### 4. 视图创建时机和方式

**当前代码：** 视图在 `createMainWidget()` 中按需创建

**问题：** 视图应该在哪里创建？

**选项 A：Controller 创建 View，View 创建子视图（推荐）**
```cpp
// TaijiMPCProject (Controller)
QWidget* createMainWidget(QWidget* parent) {
    if (!m_view) {
        m_view = std::make_unique<TaijiMPCView>(m_model.get(), parent);
    }
    return m_view->getMainWidget();
}

// TaijiMPCView
TaijiMPCView(TaijiMPCModel* model, QWidget* parent) {
    m_model = model;
    createAllViews();
}
```

**选项 B：Controller 创建所有视图**
```cpp
// TaijiMPCProject
QWidget* createMainWidget(QWidget* parent) {
    m_view = std::make_unique<TaijiMPCView>(parent);
    m_view->setModel(m_model.get());
    m_view->createAllViews();
    return m_view->getMainWidget();
}
```

**建议：** **选项 A**，因为：
- View 负责管理自己的子视图
- Controller 只需要创建 View 并传入 Model

#### 5. Model 信号连接

**当前代码：** Model 的信号连接到 TaijiMPCProject 的槽

**问题：** 信号应该连接到哪里？

**选项 A：连接到 Controller（推荐）**
```cpp
// TaijiMPCProject (Controller)
void setupConnections() {
    connect(m_model.get(), &TaijiMPCModel::projectChanged, 
            this, &TaijiMPCProject::onModelChanged);
    connect(m_model.get(), &TaijiMPCModel::statusChanged,
            this, &TaijiMPCProject::onModelStatusChanged);
}

void onModelChanged(unsigned sigs) {
    // Controller 处理，然后通知 View
    m_view->updateCurrentView();
    emit projectConfigChanged();
}
```

**选项 B：直接连接到 View**
```cpp
// TaijiMPCView
void setupConnections(TaijiMPCModel* model) {
    connect(model, &TaijiMPCModel::projectChanged,
            this, &TaijiMPCView::onModelChanged);
}
```

**建议：** **选项 A**，因为：
- Controller 负责协调 Model 和 View
- Controller 可以处理业务逻辑，然后通知 View
- 符合 MVC 的依赖方向

#### 6. BaseView 对 Controller 的依赖

**当前代码：** `BaseView::onProjectChanged()` 中调用了 `mpc_project->getCurrentView()`

**问题：** BaseView 是否需要知道 Controller？

**选项 A：BaseView 只依赖 Model（推荐）**
```cpp
// BaseView
void onProjectChanged(unsigned signal) {
    // 只处理自己的更新，不访问 Controller
    updateView();
}
```

**选项 B：BaseView 可以访问 Controller**
```cpp
// BaseView
void setController(TaijiMPCProject* controller);
TaijiMPCProject* getController() const;
```

**建议：** **选项 A**，因为：
- View 应该只依赖 Model
- 如果需要协调多个视图，应该通过 Controller
- 保持 View 的独立性

## 推荐的架构设计

### 类职责划分

#### TaijiMPCProject (Controller)
- 实现 IProject 接口
- 拥有 Model 和 View
- 协调 Model 和 View 的交互
- 处理业务逻辑（验证、操作等）
- 连接 Model 信号，通知 View 更新

#### TaijiMPCModel (Model)
- 数据管理
- 业务逻辑（连接、操作等）
- 发出数据变更信号

#### TaijiMPCView (View)
- 管理 m_mainWidget 和所有子视图
- 创建和管理子视图
- 提供视图访问接口（getCurrentView 等）
- 处理视图更新逻辑（updateCurrentView）
- 管理视图同步器

### 依赖关系

```
TaijiMPCProject (Controller)
    ├── 拥有 TaijiMPCModel (Model)
    ├── 拥有 TaijiMPCView (View)
    ├── 连接 Model 信号 → Controller 槽
    └── 调用 View 方法更新 UI

TaijiMPCView (View)
    ├── 接收 TaijiMPCModel* (只读访问)
    ├── 创建和管理子视图
    └── 子视图通过 setProject() 接收 Model

BaseView 及子视图
    ├── 只依赖 TaijiMPCModel*
    └── 不依赖 Controller
```

### 关键方法分配

| 方法 | 位置 | 理由 |
|------|------|------|
| `setupViewSynchronization()` | Controller | 协调逻辑 |
| `getCurrentView()` | View | View 内部状态 |
| `updateCurrentView()` | View | View 更新逻辑 |
| `create*Views()` | View | View 管理子视图 |
| `setupConnections()` | Controller | 连接 Model 信号 |
| `onModelChanged()` | Controller | 处理 Model 变化 |

## 需要修改的地方

### 1. BaseView 的 getCurrentView() 调用

**当前：**
```cpp
// BaseView.cpp
auto* current_view = mpc_project ? mpc_project->getCurrentView() : nullptr;
```

**修改为：**
```cpp
// 方案 A：移除这个调用，BaseView 不需要知道当前视图
// 方案 B：通过信号/槽机制，由 Controller 通知
```

**建议：** 分析这个调用的用途，如果不需要，可以移除。

### 2. 视图同步逻辑

**当前：** `setupViewSynchronization()` 在 Controller 中，但访问了所有视图成员

**修改为：**
```cpp
// TaijiMPCProject (Controller)
void setupViewSynchronization() {
    connect(m_model.get(), &TaijiMPCModel::mvDataChanged, this, [this]() {
        m_view->markViewsDirty(ViewType::MV);
        m_view->updateCurrentView();
    });
}

// TaijiMPCView
void markViewsDirty(ViewType type) {
    // 根据类型标记相关视图为 dirty
}
```

### 3. createMainWidget() 的实现

**当前：** 在 TaijiMPCProject 中创建视图

**修改为：**
```cpp
// TaijiMPCProject
QWidget* createMainWidget(QWidget* parent) {
    if (!m_view) {
        m_view = std::make_unique<TaijiMPCView>(m_model.get(), parent);
    }
    return m_view->getMainWidget();
}
```

## 总结

### ✅ 方案总体合理

你的重构方案总体上是合理的，符合 MVC 模式。主要需要明确的是：

1. **职责边界**：明确 Controller、Model、View 各自的职责
2. **依赖方向**：确保依赖方向正确（Controller → Model/View，View → Model）
3. **信号连接**：Model 信号连接到 Controller，Controller 通知 View

### 📝 建议的改进

1. **视图同步逻辑**：放在 Controller，但通过 View 的接口操作
2. **getCurrentView()**：放在 View，Controller 可以通过 View 访问
3. **updateCurrentView()**：放在 View，由 Controller 触发
4. **BaseView 依赖**：移除对 Controller 的直接依赖

### 🎯 实施建议

1. 先创建 TaijiMPCView，迁移视图管理代码
2. 明确信号连接方式（Model → Controller → View）
3. 逐步重构，保持功能正常
4. 测试每个阶段，确保没有破坏现有功能
