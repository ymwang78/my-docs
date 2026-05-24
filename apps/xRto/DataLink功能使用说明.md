# xRto DataLink功能使用说明

## 功能概述

DataLink功能用于建立模型变量与现场工业位号之间的连接关系，实现实时数据的读取和写入。该功能类似于Case Manager中Variables的管理方式，但专门针对工业现场的位号连接。

## 主要特性

1. **工业位号管理**：从CSV文件加载现场位号信息
2. **DataLink连接**：建立模型变量与工业位号的映射关系
3. **连接类型**：支持读取、写入和双向连接
4. **状态管理**：可激活/禁用特定的连接

## 数据结构

### 工业位号 (XRIndustrialTag)
- `tag_name`: 位号名称
- `description`: 位号描述
- `lower_bound`: 下界值
- `upper_bound`: 上界值
- `precision`: 精度
- `unit`: 单位
- `data_type`: 数据类型
- `data_source_name`: 所属数据源

### DataLink连接 (XRDataLink)
- `model_variable_name`: 模型变量完整路径
- `unit_name`: 单元名称
- `variable_name`: 变量名称
- `industrial_tag_name`: 工业位号名称
- `data_source_name`: 数据源名称
- `link_type`: 连接类型 (0:读取, 1:写入, 2:双向)
- `is_active`: 是否激活 (0:禁用, 1:激活)

## 使用步骤

### 1. 准备CSV文件
创建包含工业位号信息的CSV文件，需要包含以下列：
- TagName: 位号名称（必需）
- Description: 描述（可选）
- LowerBound: 下界（可选）
- UpperBound: 上界（可选）
- Precision: 精度（可选）
- Unit: 单位（可选）
- DataType: 数据类型（可选）

示例CSV内容：
```csv
TagName,Description,LowerBound,UpperBound,Precision,Unit,DataType
FIC101,Feed Flow Control,0,1000,0.1,kg/h,double
TIC102,Temperature Control,0,500,0.1,°C,double
PIC103,Pressure Control,0,10,0.01,bar,double
```

### 2. 配置数据源
在主界面其他模块中配置CSV类型的外部数据源：
- 名称：数据源名称
- 类型：CSV
- 位置：CSV文件的完整路径

### 3. 加载工业位号
1. 点击工具栏的"Data Link"按钮打开DataLink对话框
2. 在左侧"工业位号管理"区域选择数据源
3. 点击"加载位号"按钮从CSV文件加载位号信息
4. 系统会显示加载进度，完成后显示所有位号

### 4. 创建DataLink连接
1. 在左侧位号列表中选择要连接的工业位号
2. 点击右侧"创建连接"按钮
3. 输入模型变量路径（如：Unit1.variables.temperature）
4. 选择连接类型（读取/写入/双向）
5. 确认创建连接

### 5. 管理连接
- **删除连接**：选择连接后点击"删除连接"
- **切换状态**：选择连接后点击"切换状态"激活/禁用连接

## CSV文件格式要求

系统支持自动检测CSV文件的列映射，支持以下字段名称：

### 位号名称（必需）
- TagName, tag_name, 位号名称, 标签名称

### 可选字段
- **描述**: Description, desc, 描述, 说明
- **下界**: LowerBound, lower, min, 下限, 下界
- **上界**: UpperBound, upper, max, 上限, 上界
- **精度**: Precision, precision, 精度, 小数位
- **单位**: Unit, unit, 单位
- **数据类型**: DataType, type, 类型

## 注意事项

1. **文件格式**：确保CSV文件采用UTF-8编码，逗号分隔
2. **必需字段**：至少包含一个位号名称字段
3. **数据源配置**：确保数据源的路径正确且文件可访问
4. **模型变量路径**：输入正确的模型变量完整路径
5. **连接唯一性**：同一个模型变量只能连接一个工业位号

## 错误处理

- **文件不存在**：检查数据源路径配置
- **格式错误**：确保CSV文件格式正确
- **缺少必需字段**：确保包含位号名称列
- **加载失败**：检查文件权限和内容格式

## 技术实现

### 核心类
- `IndustrialTagLoader`: CSV文件加载器
- `PageDatalink`: DataLink主界面
- `IndustrialTagModel`: 工业位号表格模型
- `DataLinkModel`: DataLink连接表格模型

### 数据存储
数据保存在FlowSheetModel中：
- `industrial_tags`: 工业位号列表
- `data_links`: DataLink连接列表
- `ext_data_sources`: 外部数据源列表

数据会随项目文件一起保存和加载。