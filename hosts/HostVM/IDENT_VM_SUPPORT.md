# Ident VM 支持说明

## 修改内容

已成功为 HostVM 添加了 "ident" VM 类型的支持，对应 libident 库。

### 修改文件

1. **hostvm/hostvm_service.cpp**
   - 添加了 `extern "C" int zident_init();` 声明
   - 在 `onWorkerStart()` 函数中添加了对 "ident" vmtype 的处理分支，调用 `zident_init()`

2. **../libsrc/libident/src/zident_vm.h**
   - 添加了 `zident_init()` 函数的 extern "C" 声明

3. **../libsrc/libident/src/zident_vm.cpp**
   - 在 `_zident_register` 静态对象下方添加了 `zident_init()` 函数实现
   - 该函数引用静态注册对象以防止链接器优化

### 代码变更

#### 1. zident_vm.cpp

在静态注册对象下方添加了初始化函数：

```cpp
static zce::zvm::VirtualMachineRegister _zident_register(
    "ident",
    [](const zdp_base::zvm_t& vm, const zce::SmartPtr<zce::zvm::VirtualMachineStub>& stub_ptr,
       zce::RefBlock& /*args*/) -> zce::SmartPtr<zce::zvm::Machine> {
        return zce::SmartPtr<zce::zvm::Machine>(new ZidentMachine(vm.vmname, stub_ptr));
    });

}  // namespace zident

extern "C" int zident_init() {
    // Reference the static register object to ensure it's not optimized away
    // by the linker. The actual registration happens at static initialization.
    (void)&zident::_zident_register;
    ZCE_DEBUG((ZLOG_INFOR, "zident_init: ident VM type registered"));
    return 0;
}

namespace zident {
```

#### 2. zident_vm.h

添加了函数声明：

```cpp
#ifdef __cplusplus
extern "C" {
#endif

/// Initialize ident VM and ensure static registration is not optimized away.
int zident_init();

#ifdef __cplusplus
}
#endif
```

#### 3. hostvm_service.cpp

添加了 extern 声明：

```cpp
extern "C" int zident_init();
```

在 VM 类型判断部分添加了调用：

```cpp
} else if (options_.vmtype == "ident") {
    ret = zident_init();
    if (ret < 0) {
        ZCE_DEBUG((ZLOG_ERROR, "zident_init failed ret=%d", ret));
        return false;
    }
```

### 使用方式

在配置文件（hostvm.xml）中设置 vmtype 为 "ident" 即可启用 ident VM：

```xml
<vmtype>ident</vmtype>
```

### 技术细节

1. **防止链接器优化**: 
   - 静态注册对象 `_zident_register` 可能会被链接器优化掉（如果没有显式引用）
   - `zident_init()` 函数通过引用该静态对象 `(void)&zident::_zident_register;` 确保其不被优化
   - 该函数必须放在 register 对象定义的下方，否则可能无效

2. **自动注册机制**: libident 通过 `zce::zvm::VirtualMachineRegister` 实现了 VM 的自动注册，在静态初始化阶段完成

3. **VM 实现**: ZidentMachine 类提供了完整的 VM 实现，包括：
   - 单线程 IdentReactor 用于串行化 Python 识别调用
   - 任务超时管理（5秒看门狗定时器）
   - RPC 方法支持：mlfOnlineIdent、mlfEstdelayon、mlfTestDesign

4. **依赖库**: libident.lib 已在 hostvm_inc.h 中正确链接

### 注意事项

- `zident_init()` 函数必须在 hostvm 启动时被调用，以确保静态注册不被优化
- 该函数的实现必须放在 `_zident_register` 定义之后
- 使用 `extern "C"` 确保 C++ name mangling 的兼容性

