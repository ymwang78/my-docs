# SimulationModelView Implementation

## Overview
本文档描述了xApc项目中SimulationModelView的实现，该视图用于显示控制模型的仿真响应曲线。

## 架构设计

### 1. ModelChart类
基于ChartWidget_QWT实现的专用模型图表组件。

#### 主要功能：
- **三种显示模式**：
  - `StepResponse`: 阶跃响应显示
  - `FrequencyResponse`: 频域响应显示  
  - `BothResponses`: 同时显示两种响应

- **模型数据接口**：
  - `setControlModel(PIDProject*, int cvIndex, int inputIndex, bool isDV)`: 设置控制模型引用
  - `setModelIndices(int cvIndex, int inputIndex, bool isDV)`: 设置模型对应的行列号
  - `updateModelData()`: 更新模型数据显示

#### 数据获取机制：
```cpp
// 从project的nmpcControlModel获取模型数据
// cvIndex: CV序号（行号）
// inputIndex: MV/DV序号（列号）  
// isDV: 标识是DV还是MV信号
```

### 2. SimulationModelView类
主视图类，实现了左右布局的模型仿真界面。

#### 布局结构：
```
[左侧面板]                    [右侧面板]
┌─────────────┐             ┌─────────────────────────────────┐
│ Work Points │             │ [模型曲线区域]        [控制面板] │
│ ┌─────────┐ │             │ ┌─────────────────┐  ┌─────────┐│
│ │WorkPoint│ │             │ │  CV1 vs MV1     │  │显示模式 ││
│ │   1     │ │             │ │  CV1 vs MV2     │  │ ○ 阶跃  ││
│ │WorkPoint│ │    <====>   │ │  CV1 vs DV1     │  │ ○ 频域  ││
│ │   2     │ │             │ │  CV2 vs MV1     │  │ ○ 同时  ││
│ │WorkPoint│ │             │ │  CV2 vs MV2     │  │─────────││
│ │   3     │ │             │ │  CV2 vs DV1     │  │ 图例说明││
│ └─────────┘ │             │ └─────────────────┘  └─────────┘│
└─────────────┘             └─────────────────────────────────┘
```

#### 关键特性：
1. **智能隐藏**: 当只有一个WorkPoint时，左侧ListView自动隐藏
2. **动态网格**: 根据CV、MV、DV数量动态创建图表网格 (CV * (MV + DV))
3. **实时同步**: 显示模式变化时所有图表同步更新
4. **可滚动**: 图表区域支持滚动显示大量模型曲线

## 接口设计

### ModelChart核心接口

```cpp
class ModelChart : public ChartWidget_QWT
{
public:
    enum DisplayMode {
        StepResponse = 0,
        FrequencyResponse,  
        BothResponses
    };
    
    // 设置模型数据源
    void setControlModel(PIDProject* project, int cvIndex, int inputIndex, bool isDV);
    
    // 设置显示模式
    void setDisplayMode(DisplayMode mode);
    
    // 更新模型数据
    void updateModelData();
    
    // 设置图表标题
    void setModelTitle(const QString& cvName, const QString& inputName);
};
```

### SimulationModelView核心接口

```cpp
class SimulationModelView : public BaseView
{
public:
    enum DisplayMode {
        StepResponse = 0,
        FrequencyResponse,
        BothResponses
    };
    
    // 设置显示模式
    void setDisplayMode(DisplayMode mode);
    
    // 更新视图（重写BaseView）
    void updateView(bool forced = false) override;
    
private slots:
    void onWorkPointSelectionChanged();
    void onDisplayModeChanged();
};
```

## 数据流

1. **初始化阶段**：
   ```
   SimulationModelView::setupUI()
   └── setupLeftPanel() - 创建WorkPoint列表
   └── setupRightPanel()
       └── setupModelCurvesArea() - 创建图表区域
       └── setupLegendArea() - 创建控制面板
   ```

2. **数据更新流程**：
   ```
   updateView() 
   └── updateWorkPointList() - 更新工作点列表
   └── updateModelCurves()
       └── clearCharts() - 清空现有图表
       └── createModelChart() - 为每个CV*(MV+DV)创建ModelChart
           └── ModelChart::setControlModel() - 设置模型数据源
           └── ModelChart::setDisplayMode() - 设置显示模式  
           └── ModelChart::updateModelData() - 更新图表数据
   ```

3. **用户交互流程**：
   ```
   用户选择WorkPoint → onWorkPointSelectionChanged() → updateModelCurves()
   用户切换显示模式 → onDisplayModeChanged() → updateChartData()
   ```

## 扩展点

### 1. 实际数据集成
```cpp
// 在ModelChart::getModelResponseData()中实现：
void ModelChart::getModelResponseData(QVector<double>& stepX, QVector<double>& stepY,
                                     QVector<double>& freqX, QVector<double>& freqY)
{
    if (!m_controlProject) return;
    
    // 获取nmpcControlModel
    auto* nmpcModel = m_controlProject->getNmpcControlModel();
    if (!nmpcModel) return;
    
    // 获取当前工作点的ControlModel  
    auto* controlModel = nmpcModel->getControlModel(currentWorkPointIndex);
    if (!controlModel) return;
    
    if (m_isDV) {
        // 获取DV模型数据
        auto dvModel = controlModel->getDVModel(m_cvIndex, m_inputIndex);
        stepX = dvModel->getStepTimeVector();
        stepY = dvModel->getStepResponseVector();
        freqX = dvModel->getFrequencyVector(); 
        freqY = dvModel->getMagnitudeVector();
    } else {
        // 获取MV模型数据
        auto mvModel = controlModel->getMVModel(m_cvIndex, m_inputIndex);
        stepX = mvModel->getStepTimeVector();
        stepY = mvModel->getStepResponseVector();
        freqX = mvModel->getFrequencyVector();
        freqY = mvModel->getMagnitudeVector();
    }
}
```

### 2. 高级显示功能
- 双Y轴显示（幅度和相位）
- 子图分割显示
- 图表联动缩放
- 导出功能集成

### 3. 性能优化
- 数据缓存机制
- 渐进式绘制
- 视窗剔除优化

## 测试验证

创建了测试程序 `test_model_chart.cpp` 用于验证：
- ModelChart的基本功能
- 显示模式切换
- 数据更新机制

## 总结

该实现完全符合需求：
1. ✅ 基于BaseView的继承结构
2. ✅ 左右布局（WorkPoint列表 + 模型曲线显示）
3. ✅ 基于ChartWidget_QWT的ModelChart
4. ✅ 三种显示方式支持
5. ✅ 动态图表网格 (CV * (MV + DV))
6. ✅ 完整的接口设计和扩展能力

代码结构清晰、易于维护和扩展，为后续与实际项目数据的集成提供了良好的基础。