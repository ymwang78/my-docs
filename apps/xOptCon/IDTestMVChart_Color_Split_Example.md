# IDTestMVChart 颜色分割功能使用说明

## 功能概述

IDTestMVChart现在支持根据指定位置将趋势线分成两段，使用不同的颜色显示：
- **分割点之前**：使用蓝色显示
- **分割点之后**：使用黄色显示

## 实现原理

### 1. 数据结构
```cpp
class IDTestMVChart {
private:
    int m_colorSplitPoint;    // 颜色分割点位置
    // ...
};
```

### 2. 曲线设置
图表创建两条曲线：
- **曲线0**："MV Value Before" - 蓝色，显示分割点之前的数据
- **曲线1**："MV Value After" - 黄色，显示分割点之后的数据

### 3. 数据分割逻辑
```cpp
// 确保分割点在有效范围内
int actualSplitPoint = qBound(startPoint, m_colorSplitPoint, endPoint);

// 分割数据到两条曲线
for (int i = startPoint; i < endPoint && i < xvReadData.size(); ++i) {
    if (i < actualSplitPoint) {
        // 分割点之前的数据 - 蓝色曲线
        xDataBefore.append(i);
        yDataBefore.append(xvReadData[i]);
    } else if (i == actualSplitPoint) {
        // 分割点位置：蓝线和黄线都包含这个点，实现连接
        xDataBefore.append(i);
        yDataBefore.append(xvReadData[i]);
        xDataAfter.append(i);
        yDataAfter.append(xvReadData[i]);
    } else {
        // 分割点之后的数据 - 黄色曲线
        xDataAfter.append(i);
        yDataAfter.append(xvReadData[i]);
    }
}

// 确保两条曲线都覆盖完整的显示范围
// 处理边界情况，避免空白区域
if (xDataBefore.isEmpty() && !xDataAfter.isEmpty()) {
    // 分割点在显示范围开始位置或之前，所有数据用蓝色显示
    for (int i = startPoint; i < endPoint && i < xvReadData.size(); ++i) {
        xDataBefore.append(i);
        yDataBefore.append(xvReadData[i]);
    }
    xDataAfter.clear();
    yDataAfter.clear();
}
else if (xDataAfter.isEmpty() && !xDataBefore.isEmpty()) {
    // 分割点在显示范围结束位置或之后，所有数据用黄色显示
    for (int i = startPoint; i < endPoint && i < xvReadData.size(); ++i) {
        xDataAfter.append(i);
        yDataAfter.append(xvReadData[i]);
    }
    xDataBefore.clear();
    yDataBefore.clear();
}
else if (xDataBefore.isEmpty() && xDataAfter.isEmpty() && endPoint > startPoint) {
    // 显示范围内没有数据，但范围有效，用蓝色显示所有可用数据
    for (int i = startPoint; i < endPoint && i < xvReadData.size(); ++i) {
        xDataBefore.append(i);
        yDataBefore.append(xvReadData[i]);
    }
}
```

## 使用方法

### 1. 设置分割点
```cpp
// 在IDTestMVView中设置分割点
IDTestMVChart* chart = dynamic_cast<IDTestMVChart*>(m_charts[0]);
if (chart) {
    // 设置分割点为第100个数据点
    chart->setColorSplitPoint(100);
}
```

### 2. 获取当前分割点
```cpp
int currentSplitPoint = chart->getColorSplitPoint();
```

### 3. 控制图例显示
```cpp
// 隐藏图例
chart->enableLegend(false);
// 或者
chart->showLegend(false);
// 或者
chart->enableLegend(false);

// 显示图例
chart->enableLegend(true);
// 或者
chart->showLegend(true);
// 或者
chart->enableLegend(true);
```

### 4. 动态更新分割点
```cpp
// 根据测试状态动态设置分割点
void IDTestMVView::updateColorSplitPoint() {
    if (!m_project) return;
    
    // 例如：根据测试开始时间设置分割点
    int testStartPoint = m_project->getTestStartPoint();
    
    for (auto* chart : m_charts) {
        IDTestMVChart* mvChart = dynamic_cast<IDTestMVChart*>(chart);
        if (mvChart) {
            mvChart->setColorSplitPoint(testStartPoint);
        }
    }
}
```

### 5. 批量控制图例显示
```cpp
// 隐藏所有图表的图例
void IDTestMVView::hideAllLegends() {
    for (auto* chart : m_charts) {
        IDTestMVChart* mvChart = dynamic_cast<IDTestMVChart*>(chart);
        if (mvChart) {
            mvChart->enableLegend(false);
        }
    }
}

// 显示所有图表的图例
void IDTestMVView::showAllLegends() {
    for (auto* chart : m_charts) {
        IDTestMVChart* mvChart = dynamic_cast<IDTestMVChart*>(chart);
        if (mvChart) {
            mvChart->enableLegend(true);
        }
    }
}
```

### 6. 控制线宽
```cpp
// 设置单个曲线的线宽
chart->setCurveWidth(0, 1);  // 设置蓝色曲线线宽为1像素
chart->setCurveWidth(1, 1);  // 设置黄色曲线线宽为1像素

// 设置所有曲线的线宽
chart->setAllCurvesWidth(1);  // 设置所有曲线线宽为1像素

// 批量设置所有图表的线宽
idTestMVView->setAllChartsCurveWidth(1);  // 设置所有图表线宽为1像素
```

### 7. X轴范围限制
图表自动确保X轴范围满足以下条件：
- **最小范围**：X轴范围最小不小于10个数据点
- **整数端点**：左右端点自动取整为整数
- **自动扩展**：如果用户缩放导致范围小于10，会自动扩展到10个点
- **居中扩展**：扩展时以当前中心点为基准，向两边各扩展5个点

```cpp
// 示例：用户缩放导致范围过小时，会自动调整
// 原始范围：[5.2, 12.8] -> 范围7.6 < 10，自动扩展
// 调整后范围：[5, 15] -> 范围10，端点为整数
```

### 8. 空白区域修复
修复了用户选择特定范围时出现的空白区域问题：

**问题场景**：
- 现有100个数据点
- 用户选择范围30-40
- 分割点设置为35
- 原来会出现右边空白区域

**修复逻辑**：
```cpp
// 自动处理边界情况
if (xDataBefore.isEmpty() && !xDataAfter.isEmpty()) {
    // 分割点在显示范围开始位置或之前，所有数据用蓝色显示
    // 例如：分割点=25，范围=30-40，所有数据用蓝色显示
}
else if (xDataAfter.isEmpty() && !xDataBefore.isEmpty()) {
    // 分割点在显示范围结束位置或之后，所有数据用黄色显示
    // 例如：分割点=45，范围=30-40，所有数据用黄色显示
}
else if (xDataBefore.isEmpty() && xDataAfter.isEmpty() && endPoint > startPoint) {
    // 显示范围内没有数据，但范围有效，用蓝色显示所有可用数据
    // 例如：范围=30-40，但只有35-40有数据，35-40用蓝色显示
}
```

**修复效果**：
- 确保显示范围内的所有数据都能正确显示
- 避免出现空白区域
- 保持颜色分割的视觉效果

### 9. 参数同步机制
所有图表参数现在通过`IDTestBaseViewSync`统一管理，确保多图表一致性：

**同步参数**：
```cpp
struct IDTestBaseViewSync {
    // 原有参数
    bool m_userZoomed = true;
    QRectF m_userZoomRect;
    bool m_forceAxisUpdate;
    
    // 新增同步参数
    double m_durationHours = 4.0;        // 显示时长（小时）
    int m_samplingTimeMs = 1000;         // 采样时间（毫秒）
    int m_pageNumber = 0;                // 当前页码
    int m_maxDisplayPoints = 0;          // 最大显示点数
    int m_currentStartPoint = 0;         // 当前起始点
    int m_colorSplitPoint = 0;           // 颜色分割点位置
};
```

**使用方法**：
```cpp
// 通过IDTestMVView设置参数（自动同步到所有图表）
idTestMVView->setDurationHours(2.0);      // 设置显示时长为2小时
idTestMVView->setSamplingTimeMs(500);     // 设置采样时间为500ms
idTestMVView->setPageNumber(1);           // 设置页码为1
idTestMVView->setColorSplitPoint(50);     // 设置分割点为50

// 获取当前参数
double hours = idTestMVView->getDurationHours();
int ms = idTestMVView->getSamplingTimeMs();
int page = idTestMVView->getPageNumber();
int splitPoint = idTestMVView->getColorSplitPoint();
```

**优势**：
- **一致性**：所有图表共享相同的参数设置
- **简化管理**：通过一个接口管理所有图表参数
- **自动同步**：参数修改后所有图表自动更新
- **扩展性**：易于添加新的同步参数

## 使用场景

### 1. 测试前后对比
```cpp
// 设置测试开始点作为分割点
void IDTestMVView::onTestStarted() {
    int testStartPoint = getCurrentDataPoint();
    
    for (auto* chart : m_charts) {
        IDTestMVChart* mvChart = dynamic_cast<IDTestMVChart*>(chart);
        if (mvChart) {
            mvChart->setColorSplitPoint(testStartPoint);
        }
    }
}
```

### 2. 参数调整前后对比
```cpp
// 设置参数调整点作为分割点
void IDTestMVView::onParameterChanged() {
    int changePoint = getCurrentDataPoint();
    
    for (auto* chart : m_charts) {
        IDTestMVChart* mvChart = dynamic_cast<IDTestMVChart*>(chart);
        if (mvChart) {
            mvChart->setColorSplitPoint(changePoint);
        }
    }
}
```

### 3. 多阶段测试
```cpp
// 根据不同的测试阶段设置不同的分割点
void IDTestMVView::setTestPhase(int phase) {
    int splitPoint = 0;
    
    switch (phase) {
        case 1: // 第一阶段
            splitPoint = 0;
            break;
        case 2: // 第二阶段
            splitPoint = 500; // 第500个点开始第二阶段
            break;
        case 3: // 第三阶段
            splitPoint = 1000; // 第1000个点开始第三阶段
            break;
    }
    
    for (auto* chart : m_charts) {
        IDTestMVChart* mvChart = dynamic_cast<IDTestMVChart*>(chart);
        if (mvChart) {
            mvChart->setColorSplitPoint(splitPoint);
        }
    }
}
```

## 视觉效果

### 默认状态
- 所有数据点都显示为蓝色（分割点设为0）

### 设置分割点后
- 分割点之前的数据点：蓝色
- 分割点位置：蓝色和黄色都包含（实现连接）
- 分割点之后的数据点：黄色

### 示例
```
数据点: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
分割点: 5
颜色:   [蓝,蓝,蓝,蓝,蓝,蓝黄,黄,黄,黄,黄]
```
注：分割点5同时显示为蓝色和黄色，实现连接效果

## 注意事项

1. **分割点范围**：分割点会自动限制在有效的数据范围内
2. **空数据处理**：如果某段没有数据，对应的曲线会被清空
3. **性能影响**：数据分割对性能影响很小，因为只是简单的数组操作
4. **缩放兼容**：颜色分割功能与用户缩放功能完全兼容
5. **多图表同步**：所有图表共享相同的同步参数，确保一致性
6. **图例控制**：默认情况下图例是隐藏的，可以通过API控制显示/隐藏
7. **线宽设置**：默认线宽为1像素，可以通过API动态调整
8. **X轴范围限制**：X轴范围最小不小于10，左右端点自动取整为整数
9. **空白区域修复**：自动处理边界情况，确保显示范围内所有数据都能正确显示
10. **参数同步**：所有图表参数（时长、采样时间、页码、分割点等）都通过`IDTestBaseViewSync`统一管理

## 扩展功能

### 1. 自定义颜色
可以进一步扩展支持自定义颜色：
```cpp
void setColorSplitPoint(int splitPoint, QColor beforeColor, QColor afterColor);
```

### 2. 多分割点
可以支持多个分割点，创建多段不同颜色的曲线：
```cpp
void setMultipleSplitPoints(const QVector<int>& splitPoints, const QVector<QColor>& colors);
```

### 3. 渐变效果
可以在分割点附近创建渐变效果，而不是硬分割：
```cpp
void setGradientSplitPoint(int splitPoint, int gradientWidth);
```

## 测试建议

1. **边界测试**：测试分割点为0、最大值、负数等边界情况
2. **数据更新测试**：测试数据更新时颜色分割是否正常工作
3. **缩放测试**：测试用户缩放时颜色分割是否保持正确
4. **性能测试**：测试大量数据时的性能表现
5. **多图表测试**：测试多个图表同时使用不同分割点的情况
