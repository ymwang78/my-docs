# i18n 国际化开发指南

> 适用范围:`applications/TaijiMPC/` 及其它使用 `views/TranslationUtils.h` 的 Qt 视图代码。
> 最近一次更新:2026-05-28(PR #15 把三套并存模式收敛到 Pattern B)。

本项目的国际化(English / 简体中文 切换)统一使用 **Pattern B —— 标记 + 遍历重译**:每个可翻译字面量在控件构造时通过宏标记到 `QObject` 属性上;切语言时 `QEvent::LanguageChange` 触发 `retranslateUi()`,遍历整棵 widget 树把标记的属性按当前 translator 重新刷一遍。

---

## 0. 三套历史模式之争(背景知识)

在 PR #15 合并前,代码里同时存在三种 i18n 写法:

| 模式 | 形态 | 适用 | 现状 |
|------|------|------|------|
| **A** 静态表 + `QT_TRANSLATE_NOOP` | 表格列定义里写 `{QT_TRANSLATE_NOOP("Ctx","X"), ...}`,`headerData()` 里 `QCoreApplication::translate("Ctx", x.name.toUtf8().constData())` | 表格列 | **已退役**(context 串重复 3 次、QString→utf8 来回转换) |
| **B** `markText`/`markTab` + 属性遍历 | `TR_LABEL(this, "OPC Host:")` 一次性记录 | 普通 widget(label/button/check/radio/group/tab/combo/tooltip) | **首选,本指南主推** |
| **C** 手写 `retranslateUi` 列每个 setText | `retranslateUi() { m_label->setText(tr("X")); ... }` | 动态字符串 / 表格 `headerData()` 内的 `tr()` | **保留用于无法被 B 处理的特殊情况** |

**核心原则**:
- **静态文本** → 用 B
- **`tr("...").arg(...)` 这类动态字符串** → 用 C(在 `retranslateUi` 里手写)
- **`QAbstractItemModel::headerData()` 表头** → 用 C 的小变种:`headerData()` 里直接调 `tr()`,在 `retranslateUi()` 里 emit `headerDataChanged()` 触发 QHeaderView 重新查询

---

## 1. 引入头文件

```cpp
#include "applications/TaijiMPC/views/TranslationUtils.h"
```

该头文件定义了一个 namespace `TaijiMPCUi`(包含 `markText` / `markTab` / `retranslateMarkedChildren` 等函数)和一组**全局宏**(TR_LABEL 等,故意不放在 namespace 里以便直接使用)。

使用条件:**必须在含 `Q_OBJECT` 的类的成员函数里调用宏**(宏内部用 `tr(lit)`,需要类的 `tr()` 静态方法)。

---

## 2. 控件构造时:用 TR_* 宏

每个宏遵循同样契约:**字面量在源文件里只出现一次**,既被 `tr()` 用于初次渲染,也被记录为 widget 属性供后续 retranslate。

### 2.1 单值文本

```cpp
QLabel*       lbl   = TR_LABEL(this,  "OPC Host:");
QPushButton*  btn   = TR_BUTTON(this, "Refresh");
QCheckBox*    chk   = TR_CHECK(this,  "Enable DCS Tag");
QRadioButton* radio = TR_RADIO(this,  "4 Hours");
QAction*      act   = TR_ACTION(this, "Open...");
```

### 2.2 GroupBox 标题

```cpp
QGroupBox* g = TR_GROUP(this, "Datasource");
```

### 2.3 后期设置(widget 已构造)

如果 widget 是别人创建好你拿到的,或需要先做配置再赋文本:

```cpp
m_btn = new QPushButton(QStringLiteral("◀"), this);  // 图标本身不翻译
m_btn->setMaximumWidth(40);
TR_SET_TOOLTIP(m_btn, "Navigate backward in time");

// 类似还有 TR_SET_TEXT、TR_SET_TITLE
TR_SET_TEXT(m_existingButton, "Apply");
TR_SET_TITLE(m_existingGroupBox, "Options");
```

### 2.4 ComboBox 项

```cpp
m_combo->addItem(tr("seconds"));
m_combo->addItem(tr("minutes"));
TaijiMPCUi::markComboItems(m_combo, {"seconds", "minutes"});
```

参数顺序、个数必须和 `addItem` 调用一一对应。

### 2.5 QTabWidget 标签

`addTab()` 返回新增 tab 的 index,需要把 index 一并记录到 widget 属性。直接用宏:

```cpp
TR_ADD_TAB(myTabs, page,  "Configure");                    // 无图标
TR_ADD_TAB_ICON(myTabs, page, icon, "ID Test");            // 带图标
```

---

## 3. 切语言时:`retranslateUi()` 怎么写

### 3.1 标准模式(派生自 `BaseView`)

`BaseView::changeEvent` 已经监听 `QEvent::LanguageChange` 并调用虚函数 `retranslateUi()`,子类只要 override 即可:

```cpp
// MyView.h
class MyView : public BaseView {
    Q_OBJECT
  protected:
    void retranslateUi() override;
    // ...
};

// MyView.cpp
void MyView::retranslateUi() {
    ::TaijiMPCUi::retranslateMarkedChildren(this, "MyView");
}
```

`retranslateMarkedChildren` 会:
1. 在 `this` 上调用 `retranslateObject`(处理 root 自身的标记)
2. 用 `findChildren<QObject*>()` 递归找所有子孙
3. 对每个子孙调 `retranslateObject`,匹配到 `kTextSourceProperty` / `kTitleSourceProperty` / `kToolTipSourceProperty` / `kComboSourcesProperty` / `kTabSourcesProperty` 任一就重译

### 3.2 直接是 `QWidget`(没继承 BaseView)

需要自己 hook `changeEvent`:

```cpp
class MyWidget : public QWidget {
    Q_OBJECT
  protected:
    void changeEvent(QEvent* event) override {
        if (event && event->type() == QEvent::LanguageChange) {
            retranslateUi();
        }
        QWidget::changeEvent(event);
    }
  private:
    void retranslateUi();
};
```

### 3.3 ⚠️ QTabWidget 标签的特殊处理

**`findChildren` 在某些情况下不能可靠地刷新 tab 标签**(QTabWidget 的 tab page 在 `addTab()` 后会被 reparent 到内部 QStackedWidget,加上 `QPointer` 的隐式转换等因素)。对于持有大量 tab 的视图,**显式遍历 + 调 `retranslateObject` 是最稳的写法**:

```cpp
void TaijiMPCView::retranslateUi() {
    if (!m_mainWidget) return;

    // 一级 tab(m_mainWidget 自己)
    ::TaijiMPCUi::retranslateObject(m_mainWidget.data(), "TaijiMPCView");

    // 二级 tab(m_mainWidget 的每个 page 都是 QTabWidget)
    for (int i = 0; i < m_mainWidget->count(); ++i) {
        if (auto* sub = qobject_cast<QTabWidget*>(m_mainWidget->widget(i))) {
            ::TaijiMPCUi::retranslateObject(sub, "TaijiMPCView");
        }
    }
}
```

`ToolsView::retranslateUi()` 也用了同样模式。对于普通 widget,继续用 `retranslateMarkedChildren` 即可。

### 3.4 动态字符串(arg 拼接)

Pattern B 只能往返"固定字面量"。如果文本是 `tr("%1 Script").arg(name)` 这类带变量拼接,**必须手写**:

```cpp
void ScriptView::retranslateUi() {
    // 静态标签/按钮先走 B
    ::TaijiMPCUi::retranslateMarkedChildren(this, "ScriptView");
    // 再手动重建动态标题
    if (m_titleLabel) {
        m_titleLabel->setText(tr("%1 Script").arg(getScriptTypeDisplayName()));
    }
}
```

---

## 4. `QAbstractItemModel` 表头(Pattern C-for-tables)

表格头是用 `headerData()` 提供的,**不能** mark 到属性上。约定:

### 4.1 静态列定义(`ChartLayoutBaseView::TableColumn`)

```cpp
// MyTableModel.cpp 文件顶部
#define TR_COL_NOOP(s) QT_TRANSLATE_NOOP("MyTableModel", s)
#define TR_COL(s)      QCoreApplication::translate("MyTableModel", (s))

static const QVector<TableColumn> s_cols = {
    {TR_COL_NOOP("Tag Name"),  TR_COL_NOOP("CV signal tag name"), 150, false, false},
    {TR_COL_NOOP("High Limit"), TR_COL_NOOP("SetPoint high limit"), 100, true,  true },
    // ...
};
```

`TableColumn::name/description` 类型是 `const char*`(不是 `QString`),避免每次重绘做 utf8 转换。

### 4.2 `headerData()`

```cpp
QVariant MyTableModel::headerData(int section, Qt::Orientation o, int role) const {
    if (o == Qt::Horizontal && section >= 0 && section < s_cols.size()) {
        if (role == Qt::DisplayRole) return TR_COL(s_cols[section].name);
        if (role == Qt::ToolTipRole) return TR_COL(s_cols[section].description);
    }
    return QVariant();
}
```

### 4.3 切语言时刷新表头

派生自 `ChartLayoutBaseView` 的视图**自动**通过基类的 `retranslateUi()` 触发 `headerDataChanged` 信号,无需手写。其它情况下:

```cpp
void MyView::retranslateUi() {
    if (m_tableModel) {
        emit m_tableModel->headerDataChanged(
            Qt::Horizontal, 0, m_tableModel->columnCount() - 1);
    }
}
```

不要 emit `layoutChanged()`,它会触发整张表重新布局/排序,代价大且没必要。

### 4.4 完全在 `headerData()` 里用 `tr()`(无静态表)

对于列名直接写死在 switch 里、不抽 TableColumn 的简单表(如 `ControllerTuningView::MVTuningTableModel`):

```cpp
QVariant headerData(int section, Qt::Orientation o, int role) const override {
    if (o == Qt::Horizontal && role == Qt::DisplayRole) {
        switch (section) {
            case ColTagName: return tr("Tag Name");
            case ColIRV:     return tr("IRV");
            // ...
        }
    }
    return QVariant();
}
```

注意 `tr()` 用的是这个 model 类的 `Q_OBJECT` 上下文。

---

## 5. 翻译文件流程(.ts → .qm)

### 5.1 字面量被 lupdate 扫描的条件

`lupdate` 会扫到这些地方的字面量(必须是字面常量,**不能是变量**):
- `tr("X")`(包括宏展开后的 tr)
- `QT_TR_NOOP("X")`、`QT_TRANSLATE_NOOP("Ctx", "X")`
- `QCoreApplication::translate("Ctx", "X")` 当 "X" 是字面量

**反例**(扫不到):
```cpp
const char* msg = "Hello";
tr(msg);                            // ❌ 变量
tr(QString("X").toUtf8());          // ❌ 表达式
```

我们的宏(`TR_LABEL`、`TR_COL_NOOP` 等)展开后都包含字面量形式的 `tr()` 或 `QT_TRANSLATE_NOOP`,所以 lupdate 都能正常扫到。

### 5.2 更新 .ts

每次新增/修改可翻译字符串后,在 Windows 上跑:

```
lupdate xOptCon.pro -no-obsolete
```

- `-no-obsolete` 会删除不再出现在源码中的旧条目(避免 .ts 越积越多)
- 已有的中文翻译条目按 `(context, source)` 配对,源码改了行号但字面量不变时不会丢翻译

### 5.3 编译 .qm

```
lrelease xOptCon.pro
```

生成 `translations/xOptCon_zh_CN.qm`。这是运行时实际加载的二进制翻译表。

### 5.4 资源打包

`xOptCon_zh_CN.qm` 通过 Qt 资源系统打入二进制(参考 `framework/core/LanguageManager.cpp` 里的 `translator_->load(":/translations/xOptCon_zh_CN.qm")`)。**确保 .qrc 包含最新 .qm**,否则切到中文会显示英文 fallback。

---

## 6. Context 命名约定

**Context 就是 `tr()` 调用所在类的类名**(由 `Q_OBJECT` 自动生成):

- 在 `TaijiMPCView::createTabbedMainWidget()` 里写 `TR_ADD_TAB(...)`,字面量进入 `TaijiMPCView` context
- 在 `ConfigureGeneralView::setupUI()` 里写 `TR_LABEL(...)`,字面量进入 `ConfigureGeneralView` context
- 文件局部宏(如 `TR_COL_NOOP("ControllerCVTableModel", s)`)显式指定 context — **此时 context 必须与 model 类名一致**,否则 lupdate 扫到的 context 和运行时查找的 context 对不上

`retranslateMarkedChildren(this, "MyView")` 的第二个参数必须和 `tr()` 实际使用的 context 一致。一个常见出错点:**派生类调用基类 retranslateMarkedChildren 时混淆 context**,务必传入派生类自己的名字。

---

## 7. 加新视图的 Checklist

新写一个继承 `BaseView` 的视图,按下面的清单走:

- [ ] `.cpp` 顶部加 `#include "../TranslationUtils.h"`(路径按相对深度)
- [ ] `setupUI()` 里所有静态 label/button/check/radio/groupbox/action 用 `TR_LABEL` / `TR_BUTTON` / `TR_CHECK` / `TR_RADIO` / `TR_GROUP` / `TR_ACTION` 构造
- [ ] tab 用 `TR_ADD_TAB` 或 `TR_ADD_TAB_ICON`
- [ ] tooltip 用 `TR_SET_TOOLTIP`(widget 已经造好之后)
- [ ] combo 项:`addItem(tr("X"))` + 配套 `markComboItems(combo, {"X", ...})`
- [ ] 表格 model:用 `TR_COL_NOOP`/`TR_COL` 文件局部宏定义(`headerData()` 走 Pattern C-for-tables)
- [ ] **override `retranslateUi()`**,函数体一般就一行:
  ```cpp
  void MyView::retranslateUi() {
      ::TaijiMPCUi::retranslateMarkedChildren(this, "MyView");
  }
  ```
- [ ] 如果有 QTabWidget,在 `retranslateUi()` 末尾追加显式 `retranslateObject(tabWidget, "MyView")`(参考 `TaijiMPCView`)
- [ ] 如果有 `tr("%1 ...").arg(x)` 这种动态字符串,在 `retranslateUi()` 里手动 setText
- [ ] **新文件落盘必须是 UTF-8 with BOM**(CLAUDE.md 硬性规范)

---

## 8. 常见陷阱

### 8.1 字面量必须是 `const char*`

宏内部通过 `tr(lit)` 调用,而 `tr()` 的第一个参数是 `const char*`:

```cpp
const QString name = "Click";
TR_BUTTON(this, name);           // ❌ name 是 QString,编译失败
TR_BUTTON(this, "Click");        // ✓
```

如果非要用变量(运行时拼接),退化到 Pattern C:`new QPushButton(tr("..."), this)` + 在 `retranslateUi()` 里手写 setText。

### 8.2 不要在 `markText` 后又手动 `setText` 一个不同的字面量

```cpp
auto* b = TR_BUTTON(this, "OK");   // 标记为 "OK"
b->setText(tr("Confirm"));         // ❌ 现在显示 "Confirm",但属性还是 "OK"
                                    //    切语言后会变回 "OK" 的翻译
```

如果确实要换字面量,用 `TR_SET_TEXT(b, "Confirm")`。

### 8.3 BOM 别被工具吃掉

CLAUDE.md 要求所有 `.h/.hpp/.c/.cpp` 都是 UTF-8 with BOM。编辑器(VS、Qt Creator)默认能保留;但有些自动化工具(prettier 类、某些 git filter)会 strip。建议加 pre-commit hook:

```bash
#!/bin/bash
# .git/hooks/pre-commit
for f in $(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(h|hpp|c|cpp)$'); do
    if [ "$(head -c 3 "$f" | od -An -tx1 | tr -d ' \n')" != "efbbbf" ]; then
        echo "ERROR: $f missing UTF-8 BOM (see CLAUDE.md)"; exit 1
    fi
done
```

### 8.4 `QPointer<QTabWidget>` 隐式转换

`TR_ADD_TAB(m_mainWidget, ...)` 中 `m_mainWidget` 即使是 `QPointer<QTabWidget>` 也能直接传(`QPointer<T>::operator T*()`),但在 `retranslateUi()` 里显式调 `retranslateObject(m_mainWidget.data(), ...)` 更稳:

```cpp
::TaijiMPCUi::retranslateObject(m_mainWidget.data(), "TaijiMPCView");
//                                            ^^^^^^^ 拿原始指针
```

### 8.5 不要 emit `layoutChanged()` 当只是想刷表头

```cpp
emit model->layoutChanged();   // ❌ 触发整表 re-layout,view state 可能丢
emit model->headerDataChanged(Qt::Horizontal, 0, model->columnCount() - 1);  // ✓
```

### 8.6 ComboBox 在 retranslate 时 currentIndex 别被信号打飞

`retranslateObject` 处理 combo 时已经用 `QSignalBlocker` + 保存/恢复 `currentIndex`。如果你手写 setItemText,记得自己挡信号:

```cpp
{
    const QSignalBlocker blocker(combo);
    const int idx = combo->currentIndex();
    for (int i = 0; i < n; ++i) combo->setItemText(i, tr(literal[i]));
    combo->setCurrentIndex(idx);
}
```

---

## 9. 测试与验证

### 9.1 Smoke test

`tests/test_i18n_switch.cpp` 提供一个 standalone 测试:

- 构造一个 `FixtureWidget`,用全部 `TR_*` 宏(label/button/check/radio/group/tab/combo/tooltip)+ `QPointer<QTabWidget>` 形态
- 安装一个 `FakeTranslator`,对任意源串返回 `"[ZH]" + source`
- 触发 `QEvent::LanguageChange`,断言所有控件文本都变成 `"[ZH]X"`
- 卸载 translator,断言全部还原

构建运行:
```bash
cd tests
cmake -B build -S . -f CMakeTestLists.txt
cmake --build build --target test_i18n_switch
./build/test_i18n_switch
```

### 9.2 手动验证

实际操作:
1. 启动应用(默认按 settings 里上次的语言加载)
2. 顶部菜单 → Tools → Solution Settings → Language 切换
3. 主 tab、二级 tab、表头、tooltip、所有 label/button 都应该立刻变成目标语言
4. 切回去,再切回来,反复多次都应该工作

最容易漏的地方:**动态字符串**(`tr("%1 Script").arg(x)`)— 必须手写 retranslateUi 里的拼接,Pattern B 帮不上忙。

---

## 10. 相关文件速查

| 文件 | 作用 |
|------|------|
| `applications/TaijiMPC/views/TranslationUtils.h` | 全部 Pattern B 机制(marker 函数 + TR_* 宏 + retranslate 函数) |
| `framework/core/LanguageManager.{h,cpp}` | 单例,封装 QTranslator 加载/卸载;`languageChanged` 信号 |
| `applications/TaijiMPC/views/BaseView.{h,cpp}` | 基类的 `changeEvent` + 虚函数 `retranslateUi()` |
| `applications/TaijiMPC/views/ChartLayoutBaseView.{h,cpp}` | 图表+表格视图基类,包含 `TableColumn` 结构 |
| `translations/xOptCon_zh_CN.ts` | 文本翻译源文件(lupdate 输出) |
| `translations/xOptCon_zh_CN.qm` | 编译后的二进制翻译(lrelease 输出,运行时加载) |
| `tests/test_i18n_switch.cpp` | 切语言 smoke test |
| `tests/CMakeTestLists.txt` | 包含 `test_i18n_switch` target 定义 |

---

## 修订记录

- **2026-05-28**:初版,基于 PR #15 把三套模式收敛到 Pattern B 后的状态编写。
