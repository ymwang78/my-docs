# RPC_CALL 多参数支持实现

## 功能概述

修改了RPC_CALL宏以支持多个参数的解包和调用，现在可以处理：
- 单参数RPC调用：`RPC_CALL(functionName, argType)`
- 双参数RPC调用：`RPC_CALL(functionName, arg1Type, arg2Type)`
- 三参数RPC调用：`RPC_CALL(functionName, arg1Type, arg2Type, arg3Type)`

## 实现机制

### 1. 宏定义架构

```cpp
// 单参数RPC调用宏
#define RPC_CALL_1(FUNC, REQ)                                                           \
    if (method == #FUNC) {                                                               \
        REQ arg;                                                                         \
        int unpack_ret =                                                                 \
            ::zce::zdp::zds_unpack(arg, dblock.rd_ptr(), (int)dblock.length(), 0, true); \
        if (unpack_ret < 0) {                                                            \
            ZCE_ERROR((ZLOG_ERROR, "unpack %s failed, ret=0x%x\n", #REQ, unpack_ret));   \
            response(unpack_ret, zce::RefBlock());                                       \
            return unpack_ret;                                                           \
        }                                                                                \
        return FUNC(arg, response);                                                      \
    }

// 双参数RPC调用宏
#define RPC_CALL_2(FUNC, ARG1_TYPE, ARG2_TYPE)                                         \
    if (method == #FUNC) {                                                               \
        ARG1_TYPE arg1;                                                                  \
        ARG2_TYPE arg2;                                                                  \
        int unpack_ret =                                                                 \
            ::zce::zdp::zds_unpack(arg1, dblock.rd_ptr(), (int)dblock.length(), 0, true); \
        if (unpack_ret < 0) {                                                            \
            ZCE_ERROR((ZLOG_ERROR, "unpack first arg failed, ret=0x%x\n", unpack_ret)); \
            response(unpack_ret, zce::RefBlock());                                       \
            return unpack_ret;                                                           \
        }                                                                                \
        dblock.rd_ptr(unpack_ret);                                                       \
        unpack_ret =                                                                     \
            ::zce::zdp::zds_unpack(arg2, dblock.rd_ptr(), (int)dblock.length(), 0, true); \
        if (unpack_ret < 0) {                                                            \
            ZCE_ERROR((ZLOG_ERROR, "unpack second arg failed, ret=0x%x\n", unpack_ret)); \
            response(unpack_ret, zce::RefBlock());                                       \
            return unpack_ret;                                                           \
        }                                                                                \
        return FUNC(arg1, arg2, response);                                               \
    }

// 三参数RPC调用宏
#define RPC_CALL_3(FUNC, ARG1_TYPE, ARG2_TYPE, ARG3_TYPE)                              \
    if (method == #FUNC) {                                                               \
        ARG1_TYPE arg1;                                                                  \
        ARG2_TYPE arg2;                                                                  \
        ARG3_TYPE arg3;                                                                  \
        int unpack_ret =                                                                 \
            ::zce::zdp::zds_unpack(arg1, dblock.rd_ptr(), (int)dblock.length(), 0, true); \
        if (unpack_ret < 0) {                                                            \
            ZCE_ERROR((ZLOG_ERROR, "unpack first arg failed, ret=0x%x\n", unpack_ret)); \
            response(unpack_ret, zce::RefBlock());                                       \
            return unpack_ret;                                                           \
        }                                                                                \
        dblock.rd_ptr(unpack_ret);                                                       \
        unpack_ret =                                                                     \
            ::zce::zdp::zds_unpack(arg2, dblock.rd_ptr(), (int)dblock.length(), 0, true); \
        if (unpack_ret < 0) {                                                            \
            ZCE_ERROR((ZLOG_ERROR, "unpack second arg failed, ret=0x%x\n", unpack_ret)); \
            response(unpack_ret, zce::RefBlock());                                       \
            return unpack_ret;                                                           \
        }                                                                                \
        dblock.rd_ptr(unpack_ret);                                                       \
        unpack_ret =                                                                     \
            ::zce::zdp::zds_unpack(arg3, dblock.rd_ptr(), (int)dblock.length(), 0, true); \
        if (unpack_ret < 0) {                                                            \
            ZCE_ERROR((ZLOG_ERROR, "unpack third arg failed, ret=0x%x\n", unpack_ret));  \
            response(unpack_ret, zce::RefBlock());                                       \
            return unpack_ret;                                                           \
        }                                                                                \
        return FUNC(arg1, arg2, arg3, response);                                         \
    }

// 通用RPC调用宏 - 根据参数数量自动选择
#define RPC_CALL(FUNC, ...) RPC_CALL_IMPL(FUNC, __VA_ARGS__)

// 辅助宏，用于根据参数数量选择正确的宏
#define RPC_CALL_IMPL(FUNC, ARG1, ...) RPC_CALL_IMPL_2(FUNC, ARG1, __VA_ARGS__)
#define RPC_CALL_IMPL_2(FUNC, ARG1, ARG2, ...) RPC_CALL_IMPL_3(FUNC, ARG1, ARG2, __VA_ARGS__)
#define RPC_CALL_IMPL_3(FUNC, ARG1, ARG2, ARG3, ...) RPC_CALL_IMPL_4(FUNC, ARG1, ARG2, ARG3, __VA_ARGS__)

// 根据参数数量选择对应的宏
#define RPC_CALL_IMPL_4(FUNC, ARG1, ARG2, ARG3, ARG4, ...) RPC_CALL_3(FUNC, ARG1, ARG2, ARG3)
#define RPC_CALL_IMPL_3(FUNC, ARG1, ARG2, ARG3, ...) RPC_CALL_2(FUNC, ARG1, ARG2)
#define RPC_CALL_IMPL_2(FUNC, ARG1, ARG2, ...) RPC_CALL_1(FUNC, ARG1)
```

### 2. 参数解包机制

每个宏都会：
1. 从数据块中按顺序解包参数
2. 更新数据块读取指针位置
3. 检查解包错误并返回适当的错误码
4. 调用对应的函数并传递response回调

### 3. 函数签名要求

所有RPC函数都必须接受response回调作为最后一个参数：

```cpp
// 单参数函数
int functionName(ArgType arg, const zce::zvm::VirtualMachineStub::response_cb& response);

// 双参数函数
int functionName(Arg1Type arg1, Arg2Type arg2, const zce::zvm::VirtualMachineStub::response_cb& response);

// 三参数函数
int functionName(Arg1Type arg1, Arg2Type arg2, Arg3Type arg3, const zce::zvm::VirtualMachineStub::response_cb& response);
```

## 使用示例

### 在call_dblock函数中的使用

```cpp
int ZmpcMachine::call_dblock(zce_int64 objid, const std::string& method, zce::RefBlock& dblock,
                             const zvm::VirtualMachineStub::response_cb& response) {
    ZTRACE("ZmpcMachine::call_dblock", objid, method, dblock.length());
    
    // 单参数RPC调用
    RPC_CALL(loadProjectConfig, zmpc::ProjectConfig);
    RPC_CALL(startTesting, zmpc::StartTestingRequest);
    RPC_CALL(stopTesting, zmpc::StopTestingRequest);
    RPC_CALL(setMVEngLowLimit, double);
    RPC_CALL(setMVHighLimit, double);
    RPC_CALL(setAmplitude, double);
    RPC_CALL(setMVLowLimit, double);
    RPC_CALL(setMVSWitchFactor, double);
    
    // 双参数RPC调用
    RPC_CALL(setMVEngHighLimit, int, double);
    
    return -1;
}
```

### 函数实现示例

```cpp
int ZmpcMachine::setMVEngHighLimit(int index, double value, 
                                   const zce::zvm::VirtualMachineStub::response_cb& response) {
    ZTRACE("ZmpcMachine::setMVEngHighLimit", index, value);
    
    LockRead config(config_, config_lock_);
    if (index < 0 || index >= static_cast<int>(config_.mvConfig.size())) {
        ZCE_ERROR((ZLOG_ERROR, "Invalid MV index: %d", index));
        response(ZMPC_ERRCODE_INVALIDPARAM, zce::RefBlock());
        return ZMPC_ERRCODE_INVALIDPARAM;
    }
    
    {
        auto write_lock = config.tempLockWrite();
        config_.mvConfig[index].commonConf.fixedEngHighLimit = value;
    }
    
    // 同步到运行时
    {
        Lock runtime(runtime_, runtime_lock_);
        runtime_.mpcRuntime.mvRuntime[index].baseRuntime.hiLimit = value;
    }
    
    zce::RefBlock response_data;
    response(0, std::move(response_data));
    return 0;
}
```

## 支持的参数类型

### 基本类型
- `int` - 整数类型
- `double` - 双精度浮点数
- `float` - 单精度浮点数
- `bool` - 布尔类型
- `std::string` - 字符串类型

### 复杂类型
- `zmpc::ProjectConfig` - 项目配置结构
- `zmpc::StartTestingRequest` - 开始测试请求
- `zmpc::StopTestingRequest` - 停止测试请求
- 其他自定义结构体类型

## 错误处理

### 解包错误
- 当参数解包失败时，会记录错误日志
- 返回解包错误码给客户端
- 不会继续处理后续参数

### 函数执行错误
- 函数内部可以返回自定义错误码
- 通过response回调返回错误信息
- 支持详细的错误描述

## 扩展性

### 添加更多参数支持
如果需要支持更多参数，可以按照相同的模式添加：

```cpp
// 四参数RPC调用宏
#define RPC_CALL_4(FUNC, ARG1_TYPE, ARG2_TYPE, ARG3_TYPE, ARG4_TYPE) \
    // 实现四参数解包逻辑

// 更新选择宏
#define RPC_CALL_IMPL_5(FUNC, ARG1, ARG2, ARG3, ARG4, ARG5, ...) RPC_CALL_4(FUNC, ARG1, ARG2, ARG3, ARG4)
```

### 自定义解包逻辑
对于特殊类型，可以添加自定义解包逻辑：

```cpp
// 特殊类型的解包宏
#define RPC_CALL_CUSTOM(FUNC, UNPACK_FUNC) \
    if (method == #FUNC) { \
        // 使用自定义解包函数 \
        return UNPACK_FUNC(dblock, response); \
    }
```

## 注意事项

1. **参数顺序**：参数必须按照函数签名中的顺序进行解包
2. **内存管理**：解包后的参数会自动管理内存
3. **错误处理**：每个解包步骤都有独立的错误检查
4. **线程安全**：函数实现需要考虑线程安全问题
5. **性能考虑**：大量参数会影响解包性能，建议合理设计参数结构

## 测试建议

1. **单元测试**：为每个RPC函数编写单元测试
2. **参数验证**：测试各种参数组合和边界条件
3. **错误测试**：测试解包失败和函数执行失败的情况
4. **并发测试**：测试多线程环境下的调用
5. **性能测试**：测试大量参数时的性能表现


