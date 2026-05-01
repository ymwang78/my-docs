### IDTestMVView的Chart功能实现

#### 横坐标

* MV/TV/CV/DV的每个Chart的横坐标都是一致的，也就是说同时放大/缩小/平移

* 横坐标数值: 是点在数组里的下标

* 横坐标显示范围, 根据m_frontSetting.idTestFront.durationHour以及 m_projectConfig->sampleConfig.samplingTime 来计算当前需要显示的点数宽度, 再结合m_frontSetting.idTestFront.pageNumber确定显示的数组范围。

* m_frontSetting.idTestFront.durationHour 是根据界面右侧的界面配置选择设置，界面上是有4Hour/12Hours/2Day(48Hours)/All(0 Hours).

#### 纵坐标

* 纵坐标是每个位号对应采样点的数值

* 纵坐标数值: 根据对应位号的xvRead的值，例如MV的就是 m_projectData.testingData.mvTestingData.xvRead, TV的就是m_projectData.testingData.tvTestingData.xvRead, 以此类推。

* 纵坐标显示范围, 根据上下限值，中心是上下限平均值，在上下限相减的基础上上下限上下方各留10%的裕量绘图空间。也就是显示范围在上下限差额的120%范围。上下限的值以MV为例在: m_projectRuntime.mpcRuntime.mvRuntime.baseRuntime.hiLimit/loLimmit.

* 上下限高度处分别绘制一根红色横虚线，提示范围