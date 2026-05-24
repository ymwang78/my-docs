# xRto 多语言国际化指南

本项目支持多语言界面，目前支持简体中文和英文。

## 文件结构

```
xRto/

├──resources/
│   └── translations/           # 翻译文件目录
│        ├── xRto_zh_CN.ts      # 中文翻译源文件
│        ├── xRto_en_US.ts      # 英文翻译源文件
│        ├── xRto_zh_CN.qm      # 中文编译后的翻译文件
│        ├── xRto_en_US.qm      # 英文编译后的翻译文件
│        └── translations.qrc   # 翻译资源文件
├── View/
│   ├── LanguageManager.h   # 语言管理器头文件
│   └── LanguageManager.cpp # 语言管理器实现
└── update_translations.sh  # 翻译文件更新脚本
```

## 如何使用

### 1. 语言切换
- 启动应用程序后，点击菜单栏的"语言"菜单
- 选择"简体中文"或"English"进行切换
- 语言设置会自动保存，下次启动时会使用上次选择的语言

### 2. 添加新的可翻译文本
在代码中使用`tr()`函数包装需要翻译的字符串：

```cpp
// 在C++代码中
setWindowTitle(tr("Window Title"));
button->setText(tr("Button Text"));

// 在类外使用QObject::tr()
QMessageBox::information(this, QObject::tr("Title"), QObject::tr("Message"));
```

### 3. 更新翻译文件
添加新的tr()字符串后，需要更新翻译文件：

```bash
# 在项目根目录执行
./update_translations.sh
```

这个脚本会：
- 从源代码中提取所有tr()包装的字符串
- 更新.ts翻译源文件
- 编译生成.qm运行时翻译文件

### 4. 编辑翻译内容
1. 打开`translations/xRto_zh_CN.ts`文件
2. 找到需要翻译的`<source>`标签
3. 在对应的`<translation>`标签中填入翻译内容
4. 重新运行`./update_translations.sh`生成.qm文件

## 开发指南

### 1. 代码规范
- 所有用户可见的文本都必须用tr()包装
- 不要在Model层使用tr()，Model层应该保持与UI无关
- 在View和Controller层适当使用tr()

### 2. 动态文本更新
对于动态创建的UI元素，需要在`MainWindow::retranslateUi()`方法中添加更新代码：

```cpp
void MainWindow::retranslateUi()
{
    setWindowTitle(tr("RTO - Real Time Optimizer"));
    // 添加其他需要动态更新的UI元素
}
```

### 3. 上下文管理
Qt的翻译系统使用类名作为上下文，同一个英文字符串在不同上下文中可以有不同的翻译。

### 4. 构建配置
CMakeLists.txt已经配置了Qt Linguist支持：
- 添加了LinguistTools依赖
- 配置了lupdate和lrelease工具
- 设置了翻译资源文件

## 支持的语言

| 语言 | 代码 | 文件名 | 显示名 |
|------|------|---------|---------|
| 简体中文 | zh_CN | xRto_zh_CN.ts | 简体中文 |
| 英文 | en_US | xRto_en_US.ts | English |

## 添加新语言

1. 在`translations/`目录下创建新的.ts文件，如`xRto_fr_FR.ts`
2. 更新`translations.qrc`文件，添加新的.qm文件引用
3. 修改`CMakeLists.txt`中的TS_FILES列表
4. 更新`LanguageManager`类，添加新语言支持
5. 运行翻译更新脚本生成新的翻译文件

## 注意事项

1. **Model层限制**：Model目录中的代码不依赖Qt，因此不能使用tr()函数
2. **资源文件**：翻译文件通过Qt资源系统嵌入到程序中
3. **自动保存**：语言选择会自动保存到QSettings中
4. **实时切换**：支持运行时动态切换语言，无需重启程序

## 常见问题

**Q: 新添加的tr()文本没有显示翻译？**
A: 需要运行`./update_translations.sh`更新翻译文件，并确保.qm文件已重新生成。

**Q: 如何为特定文本提供不同语言的翻译？**  
A: 编辑对应的.ts文件，在`<translation>`标签中填入相应语言的翻译。

**Q: Model层需要输出用户消息怎么办？**
A: Model层应该通过信号或回调将消息传递给View层，由View层负责显示本地化的消息。