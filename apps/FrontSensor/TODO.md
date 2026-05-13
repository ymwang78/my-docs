TODO: 建模部分从VB迁移工程到QT
1. 这是一个基于VB开发的工业控制软测量建模、组态和运行软件
2. VB工程代码位于Legacy/VBProject下
3. 现在需要把VB代码转换为基于QT的部分，只实现建模部分，实现为一个单独的exe
4. QT项目要求使用MVC架构, 把原有VB的数据模型部分抽提为QT的Model
6. 要求尽可能重用现有基础架构，libsrc/libQTEXT(QT的表格，趋势图), libsrc/libzce(Reactor，Scheduler， Process、ProcessHost，Python、Lua)，libsrc/libidh(OPC)
7. 如果libQTEXT无法实现对应的表格、绘图功能，如果是一个通用的功能，代码修改到libQTExt里，也就是尽可能同时扩展基础架构
