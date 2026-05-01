# TaijiMPCProject 与 PIDProject 关系重构方案

## 1. 当前架构分析

### 1.1 现状

```
┌─────────────────────────────────────┐
│      TaijiMPCProject                │
│  (IProject 接口实现)                │
│  - 拥有 PIDProject                  │
│  - 创建和管理所有 Views             │
│  - 转发 PIDProject 的方法           │
└──────────┬──────────────────────────┘
           │
           │ owns
           │
┌──────────▼──────────────────────────┐
│      PIDProject                     │
│  (业务逻辑 + 数据)                  │
│  - 项目配置                         │
│  - 运行时数据                       │
│  - 信号管理                         │
│  - 远程连接                         │
└──────────┬──────────────────────────┘
           │
           │ direct access
           │
┌──────────▼──────────────────────────┐
│      Views (20+ 个视图)              │
│  - 直接调用 PIDProject 方法          │
│  - 直接访问 PIDProject 数据          │
│  - 直接修改 PIDProject 状态          │
└─────────────────────────────────────┘
```

### 1.2 存在的问题

1. **职责不清**
   - `TaijiMPCProject` 既是插件适配器，又是视图管理器，职责混杂
   - `PIDProject` 既是 Model，又包含业务逻辑，还处理 UI 信号

2. **违反 MVC 原则**
   - Views 直接访问 Model（PIDProject），缺少 Controller 层
   - 没有数据验证和转换层
   - 业务逻辑分散在 Views 中

3. **耦合度高**
   - Views 直接依赖 PIDProject 的具体实现
   - 难以替换数据源或测试
   - 修改 PIDProject 会影响所有 Views

4. **可测试性差**
   - Views 和 Model 紧耦合，难以单独测试
   - 业务逻辑无法独立测试

## 2. 重构目标

### 2.1 采用 MVC 架构

```
┌─────────────────────────────────────┐
│      TaijiMPCProject                │
│  (IProject 接口 + Controller)       │
│  - 实现 IProject 接口               │
│  - 作为 Controller 协调 View 和 Model│
│  - 处理用户交互和业务流程            │
└──────────┬──────────────────────────┘
           │
           │ uses
           │
┌──────────▼──────────────────────────┐
│      PIDProjectModel                 │
│  (Model - 纯数据层)                  │
│  - 项目数据管理                      │
│  - 数据访问接口                      │
│  - 数据变更通知                      │
└──────────┬──────────────────────────┘
           │
           │ observes
           │
┌──────────▼──────────────────────────┐
│      Views                          │
│  (View - 纯展示层)                  │
│  - 只通过 Controller 访问 Model     │
│  - 只负责 UI 展示                   │
│  - 用户交互转发给 Controller        │
└─────────────────────────────────────┘
```

### 2.2 设计原则

1. **单一职责原则**
   - Model：只负责数据管理
   - View：只负责 UI 展示
   - Controller：只负责协调和业务逻辑

2. **依赖倒置原则**
   - Views 依赖 Controller 接口，不直接依赖 Model
   - Controller 依赖 Model 接口

3. **开闭原则**
   - 可以替换不同的 Model 实现
   - 可以替换不同的 View 实现

## 3. 重构方案

### 3.1 方案一：轻量级 MVC（推荐）

保持 `PIDProject` 作为 Model，但通过 `TaijiMPCProject` 作为 Controller 层。

#### 3.1.1 架构设计

```cpp
// Model 层（保持 PIDProject，但封装为接口）
class IPIDProjectModel {
public:
    // 只读数据访问
    virtual const zmpc::ProjectConfig& getConfig() const = 0;
    virtual int getMVCount() const = 0;
    virtual zmpc::MVRuntime* getMVSignal(int index) = 0;
    
    // 数据变更通知
    signals:
    void dataChanged();
    void configChanged();
};

// Controller 层（TaijiMPCProject 增强）
class TaijiMPCProject : public QObject, public IProject {
    // 作为 Controller，协调 View 和 Model
    // 处理用户操作，验证数据，更新 Model
    // Views 通过 Controller 访问 Model
};

// View 层（Views 重构）
class BaseView : public QWidget {
    // 不再直接访问 PIDProject
    // 通过 Controller 访问数据
    TaijiMPCProject* getController() const;
    // 用户操作通过 Controller 处理
};
```

#### 3.1.2 实现步骤

**步骤 1：创建 Model 接口**

```cpp
// applications/TaijiMPC/IPIDProjectModel.h
#pragma once

#include "zmpc_proto.h"
#include <QObject>

/**
 * @brief PIDProject Model 接口
 * 
 * 定义数据访问接口，Views 通过此接口访问数据
 * 不包含业务逻辑，只负责数据管理
 */
class IPIDProjectModel : public QObject {
    Q_OBJECT
    
public:
    virtual ~IPIDProjectModel() = default;
    
    // === 配置访问（只读） ===
    virtual const zmpc::ProjectConfig& getConfig() const = 0;
    virtual QString getProjectName() const = 0;
    virtual double getSamplingTime() const = 0;
    
    // === 信号访问 ===
    virtual int getMVCount() const = 0;
    virtual int getCVCount() const = 0;
    virtual int getDVCount() const = 0;
    
    virtual zmpc::MVRuntime* getMVSignal(int index) = 0;
    virtual zmpc::CVRuntime* getCVSignal(int index) = 0;
    virtual zmpc::DVRuntime* getDVSignal(int index) = 0;
    
    // === 状态查询 ===
    virtual bool isTesting() const = 0;
    virtual bool isControlling() const = 0;
    virtual bool isSimulating() const = 0;
    virtual bool isConnected() const = 0;
    
signals:
    // 数据变更通知
    void configChanged();
    void dataChanged();
    void statusChanged(const QString& status);
    void mvDataChanged();
    void cvDataChanged();
    void dvDataChanged();
};
```

**步骤 2：PIDProject 实现 Model 接口**

```cpp
// applications/TaijiMPC/PIDProject.h
class PIDProject : public IPIDProjectModel {
    // 实现 IPIDProjectModel 接口
    // 保持现有功能，但通过接口暴露
};
```

**步骤 3：TaijiMPCProject 作为 Controller**

```cpp
// applications/TaijiMPC/TaijiMPCProject.h
class TaijiMPCProject : public QObject, public IProject {
    Q_OBJECT
    
public:
    // === IProject 接口实现 ===
    // ... 保持不变
    
    // === Controller 方法 ===
    /**
     * @brief 获取 Model（供 Views 使用）
     */
    IPIDProjectModel* getModel() const { return m_pidProject.get(); }
    
    /**
     * @brief 处理用户操作（Controller 职责）
     */
    bool startTesting();
    bool stopTesting();
    bool startControlling(bool isSimulating);
    bool stopControlling(bool isSimulating);
    
    /**
     * @brief 数据验证（Controller 职责）
     */
    bool validateAndUpdateConfig(const zmpc::ProjectConfig& config);
    
    /**
     * @brief 信号操作（Controller 职责）
     */
    bool addMVSignal(const zmpc::MVConfig& config);
    bool removeMVSignal(int index);
    bool updateMVSignal(int index, const zmpc::MVConfig& config);
    
private:
    std::unique_ptr<PIDProject> m_pidProject;  // Model
    // Views 通过 getModel() 访问，不直接访问 m_pidProject
};
```

**步骤 4：Views 重构**

```cpp
// applications/TaijiMPC/views/BaseView.h
class BaseView : public QWidget {
    Q_OBJECT
    
public:
    // 不再直接访问 PIDProject
    // 通过 Controller 访问 Model
    void setController(TaijiMPCProject* controller);
    TaijiMPCProject* getController() const { return m_controller; }
    
    // 通过 Model 接口访问数据
    IPIDProjectModel* getModel() const {
        return m_controller ? m_controller->getModel() : nullptr;
    }
    
protected:
    // 用户操作通过 Controller 处理
    void onUserAction() {
        if (m_controller) {
            m_controller->handleUserAction(...);
        }
    }
    
private:
    TaijiMPCProject* m_controller;
};
```

#### 3.1.3 优势

1. **职责清晰**
   - Model：数据管理
   - Controller：业务逻辑和协调
   - View：UI 展示

2. **解耦**
   - Views 不直接依赖 PIDProject
   - 可以替换 Model 实现

3. **可测试性**
   - 可以 Mock Model 进行测试
   - Controller 逻辑可以独立测试

4. **渐进式重构**
   - 不需要一次性重构所有代码
   - 可以逐步迁移

#### 3.1.4 迁移策略

1. **阶段 1**：创建接口，保持向后兼容
   - 创建 `IPIDProjectModel` 接口
   - `PIDProject` 实现接口
   - Views 仍可直接访问 PIDProject（向后兼容）

2. **阶段 2**：重构部分 Views
   - 选择几个简单的 View 先重构
   - 通过 Controller 访问 Model
   - 验证架构正确性

3. **阶段 3**：全面迁移
   - 所有 Views 通过 Controller 访问
   - 移除直接访问 PIDProject 的代码

### 3.2 方案二：完整 MVC（可选）

如果希望更彻底的分离，可以创建独立的 Model 类。

#### 3.2.1 架构设计

```cpp
// Model 层（独立的数据模型）
class PIDProjectModel : public IPIDProjectModel {
    // 纯数据管理，不包含业务逻辑
    // 从 PIDProject 中提取数据部分
};

// Controller 层
class TaijiMPCProjectController {
    // 业务逻辑
    // 操作 Model
    // 协调 Views
};

// View 层
class BaseView {
    // 只负责 UI
};
```

#### 3.2.2 缺点

- 需要大量重构
- 可能破坏现有功能
- 工作量较大

## 4. 推荐方案

### 4.1 选择方案一（轻量级 MVC）

**理由**：
1. 渐进式重构，风险低
2. 保持向后兼容
3. 职责清晰，满足 MVC 原则
4. 工作量适中

### 4.2 实施计划

#### 阶段 1：接口定义（1 周）
1. 创建 `IPIDProjectModel` 接口
2. `PIDProject` 实现接口
3. 添加适配器方法（保持兼容）

#### 阶段 2：Controller 增强（1 周）
1. `TaijiMPCProject` 添加 Controller 方法
2. 实现数据验证和转换
3. 实现用户操作处理

#### 阶段 3：Views 重构（2-3 周）
1. 重构 `BaseView`，通过 Controller 访问
2. 逐个重构 Views（按优先级）
3. 移除直接访问 PIDProject 的代码

#### 阶段 4：测试和优化（1 周）
1. 全面测试
2. 性能优化
3. 文档更新

## 5. 代码示例

### 5.1 接口定义

```cpp
// IPIDProjectModel.h
class IPIDProjectModel : public QObject {
    Q_OBJECT
public:
    // 只读数据访问
    virtual const zmpc::ProjectConfig& getConfig() const = 0;
    virtual int getMVCount() const = 0;
    virtual zmpc::MVRuntime* getMVSignal(int index) = 0;
    
signals:
    void dataChanged();
    void configChanged();
};
```

### 5.2 Controller 实现

```cpp
// TaijiMPCProject.h
class TaijiMPCProject : public QObject, public IProject {
public:
    // Controller 方法
    IPIDProjectModel* getModel() const;
    
    // 处理用户操作
    bool startTesting();
    bool addMVSignal(const zmpc::MVConfig& config);
    
private:
    std::unique_ptr<PIDProject> m_pidProject;  // Model
};
```

### 5.3 View 使用

```cpp
// ConfigureMVView.cpp
void ConfigureMVView::updateView() {
    auto* model = getModel();
    if (!model) return;
    
    // 通过 Model 接口访问数据
    int mvCount = model->getMVCount();
    for (int i = 0; i < mvCount; ++i) {
        auto* mv = model->getMVSignal(i);
        // 更新 UI
    }
}

void ConfigureMVView::onAddButtonClicked() {
    // 用户操作通过 Controller 处理
    if (auto* controller = getController()) {
        zmpc::MVConfig config;
        // ... 填充 config
        controller->addMVSignal(config);
    }
}
```

## 6. 风险评估

### 6.1 风险
- **中等风险**：需要重构大量代码
- **兼容性风险**：可能影响现有功能

### 6.2 缓解措施
1. 渐进式重构，保持向后兼容
2. 充分测试每个阶段
3. 保留回滚方案

## 7. 总结

采用轻量级 MVC 架构可以：
1. ✅ 明确职责分离（Model-View-Controller）
2. ✅ 降低耦合度（Views 不直接依赖 PIDProject）
3. ✅ 提高可测试性（可以 Mock Model）
4. ✅ 保持向后兼容（渐进式重构）

建议采用**方案一（轻量级 MVC）**，逐步实施。
