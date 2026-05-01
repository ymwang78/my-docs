# libzce 已知问题与技术债

> 本文档记录代码中明显可见的"待办、风险、设计不一致、潜在 Bug"等条目。
> 来源：源码注释（`@todo` / `unknow buggy` / `assert` 等）+ 构建脚本里被排除的目标 + 对当前实现的横向 review。
> 标注规则：
> - **[Bug]**：可能在生产环境直接造成错误的实现缺陷。
> - **[Risk]**：当前能跑，但语义不严谨或存在并发/资源风险。
> - **[Tech-Debt]**：代码层面的整洁度/重复/过时实现。
> - **[Build]**：构建配置、依赖、平台相关问题。
> - **[Doc/UX]**：API 易用性、文档缺失、不一致命名等。

---

## 1. 调度 / 任务相关

### 1.1 [Bug][Fixed 2026-04-30] `TaskDelegator::_delegateFuture` 标记为 “unknow buggy”
- 位置：`include/zce/zce_task.h`。
- 原现象：作者注明该路径存在未知 bug，`delegate(true, ...)` 回退到基于全局信号量的实现；死代码 `#if 0` 分支里还调用了根本不存在的 `delegateFuture`。
- 修复：
  - 新增 `TaskDelegator::delegateFuture(...)` 作为主入口，返回 `std::future<TaskResult<...>>`（与 `Scheduler::performFuture` 对称）。内部增加 `fulfilled_` 防御 flag 防止二次 set_value。
  - `_delegateFuture(...)` 保留为 alias，转调 `delegateFuture`。
  - 删除 "unknow buggy" 注释，补充调用约束（禁止在目标线程内 wait 自己）。
  - 修复 `delegate(bwait=true, ...)` 真正的 bug：`delegateTask` 返回非 0 时直接返回而不再 `sem_->acquire()` 永久卡死。

### 1.2 [Risk] `delegate(true, ...)` 在 Windows 下显式断言"非死锁"
- 位置：`zce_task.h:147-152`：
  ```cpp
#ifdef _WIN32
    if (sem_) {  // ensure sem is 0
        bool isget = sem_->try_acquire();
        ZCE_ASSERT_TEXT(!isget, "deadlock detected!");
        if (isget) sem_->release();
    }
#endif
  ```
- 现象：表达"线程的全局信号量必须为 0"，否则提示死锁。这是一种**借助全局信号量串行化** `delegate(true)` 的实现，意味着同一条线程上同时只能有一个嵌套的同步 `delegate`，套娃即报警。Linux/macOS 没有此检查，行为不一致。
- 风险：业务里嵌套同步等待会触发 `ZCE_ASSERT`（fatal log），但不会真正阻止运行。建议：跨平台对称处理，并考虑把 sem 改成"per-call 创建"，或者引入一个限定调用层级的助手。

### 1.3 [Risk] `Reactor::delegate_delay` 必须在 Reactor 线程内被调用
- 位置：`libsrc/libzce/core/zce_reactor.cpp:200`：`ZCE_ASSERT_TEXT((zce_thread_id() == thread_->getThreadId()), "delegate task not in thread");`
- 现象：注释写了"uv_timer_init 必须在 loop_ 所在的线程内"，但实现里假设外层调用者已经在 reactor 线程；如果不是，再用 `delegate(false, …, [=]{ pimpl_->delegate_delay(…) })` 二次绕回。
- 风险：调用栈较深时容易漏。建议把 assert 替换成"自动 delegate"的统一行为（参考 `dns_resolve` 的写法）。

### 1.4 [Risk] 任务队列长度限 100k 直接断流
- 位置：`zce_reactor.cpp` 中 `delegateTask`：当 `delegate_deque_.size() > 100000` 时返回 -1，并打 `ZLOG_FATAL`。
- 现象：上限是硬编码常量，没有背压回流和上层感知机制。
- 建议：暴露阈值为构造参数（或运行时可调），并增加丢弃统计上报。

### 1.5 [Risk][Fixed 2026-04-30] `Reactor::stop` 会触发 `joinThread`，但如果在 reactor 线程里调用就会卡死
- 位置：`core/zce_reactor.cpp::Reactor::stop`。
- 原现象：`stop()` 调用 `joinThread()`；从 reactor 线程内调用等于线程自己 join 自己，会死锁。
- 修复：在 `Reactor::stop` 中检测调用线程，如果等于 reactor 自身线程，仅触发 `uv_stop + uv_async_send`（loop 将在当前回调返回后退出），不再尝试 join。`ReactorThread::onThreadTerminate()` 仍会在 loop 返回后被触发，`onReactorStop()` 逻辑不受影响。外部线程调用 `stop()` 的行为保持不变（仍然会 join）。
- 同时顺手修了 `Reactor::delegate_delay`：当 `pimpl_->thread_` 尚未 start 时不再 crash，改为 `ZLOG_ERROR` 并返回 -1。

---

## 2. 网络 / 协议层

### 2.1 [Tech-Debt][Fixed 2026-04-30] `HttpStream::on_prepare_nextres` 仍是空 `@todo`
- 位置：`include/zce/http_stream.h` + `libsrc/libzce/text/http_stream.cpp`。
- 原现象：`zce_http_client::on_prepare_nextres` 是 `{};//@todo`，keep-alive 下第二个响应复用了第一个 response header 的残留状态。
- 修复：在 `zce_http_client` 中提供实际实现——重置 `response_` 到默认 `ZCE_HTTP_RESPONSE()`、清空 `cont_dblock_`。`dblock_` 由调用方 reset（原逻辑不变）。对于 WebSocket 依然是 no-op（由 `WebSocketStream::on_prepare_nextreq` 覆盖）。

### 2.2 [Risk] `HttpStream` 无 chunked 上行支持的明确路径
- 位置：`text/http_stream.cpp` （40k+ 行的整体实现，本次未深读全部分支）。
- 风险：`chunked_ack_/gzip_ack_/body_length_ack_` 字段有定义，但 `write_continue` 并未跨 chunked 边界做窗口限制，需要做大文件上传场景验证。

### 2.3 [Risk][Partially Fixed 2026-04-30] DNS 缓存 60s 全局生效，无法按域名禁用
- 位置：`zce_reactor.cpp`。
- 原现象：TTL 硬编码 60 秒。
- 修复：
  - 新增 `Reactor::setDnsCacheTTL(unsigned seconds)`（`0` 表示禁用缓存）与 `Reactor::getDnsCacheTTL()`。默认值仍然是 60s，行为向后兼容。
  - 新增 `Reactor::clearDnsCache()`，可在 SIGHUP/网络切换后调用强制刷新；跨线程调用会自动 delegate 到 reactor 线程再执行。
- 未覆盖项：仍未做按域名粒度的 TTL 配置，如业务需要可基于 `clearDnsCache()` 手动实现。

### 2.4 [Tech-Debt][Fixed 2026-04-30] `Acceptor::block_dict_` 是手写 `std::map`，无定期清理
- 位置：`include/zce/zce_handler.h` + `libsrc/libzce/core/zce_handler.cpp`。
- 原现象：阻塞名单只在"该 ip 再来一次"时懒清理；攻击者换 IP 后旧记录永不释放。
- 修复：
  - 新增 `Acceptor::purgeExpiredBlocks()` 公共方法，便于业务在 `onTimer` 中定期调用（返回被清掉的条目数）。
  - 新增 `Acceptor::blockedCount()` 方便观测。
  - `block_remote(...)` 内做机会性清理：当 `block_dict_.size() > 1024` 时顺带全量扫描过期条目。
- 说明：`block_count_` 是 `AtomicLong`，仅暴露 `++/--`，批量减是通过 `for` 循环 `--`。不是性能热点。

### 2.5 [Tech-Debt] `SocksStream` 状态机较简略
- 位置：`zce_handler.h:499-525`。
- 现象：仅支持 `Begin/Auth/Connect`，没有 UDP relay、IPv6 ATYP、错误码上报；未在生产被验证。
- 建议：补充错误码、抓包测试。

### 2.6 [Risk][Fixed 2026-04-30] `RpcStream::on_packet` 对未知 msgmid 仅打 `ZLOG_ERROR`
- 位置：`zvm/zvm_base.cpp`。
- 原现象：未实现"返回标准错误响应"，对端会一直阻塞直到超时。
- 修复：利用 ZDP 约定"偶数 msgmid == REQ，奇数 == RES"，对未知的 REQ 尽力回一个 `MSG_RPCCALL_RES{ ie_result = ZCE_ERROR_INVALID }`（使用请求自己的 `msgseq`），让对端不必等到自己超时。对未知 RES/通知仅记录 error 日志。

### 2.7 [Risk][Fixed 2026-04-30] `RpcStream` 旧版本协商逻辑写死 `1.0`
- 位置：`zvm/zvm_base.cpp::client_Proc_MSG_NONE_REQ`。
- 原现象：解析 `ie_ns "ver=1.0"`，否则打 ERROR 并把整个连接挂起（不发响应、不主动关闭）。
- 修复：版本过低时记录原始 `raw_ver` 字符串 + 解析出的 `ver` 数值，并 **主动 `close()`**，这样对端能立即观察到断链而不是等自己超时。日志仍旧走 `ZLOG_ERROR`，便于排障。

---

## 3. 虚拟机 / VM 子系统

### 3.1 [Risk] `ZpyMachine::gil_lock_` 是静态 `zce::Mutex`
- 位置：`zvm/zpy/zvm_py.h:47`。
- 现象：使用一个全局互斥锁守护 GIL/子解释器切换，配合 `tss_threadstate_` 进行 thread-state swap。
- 风险：在 Python 3.12+ 子解释器（“per-interpreter GIL”）下需小心被废弃；当前 `_PyThreadState_UncheckedGet`/`PyThreadState_GetUnchecked` 的条件判定是对版本 0x030d0000 切换，但仍依赖 pybind11 的 `subinterpreter_scoped_activate`，需要对未来 Python 版本做版本回归测试。

### 3.2 [Risk] `ZpyMachine` 析构期间静态 `unique_ptr<scoped_interpreter>` 与 `SmartPtr<ZpyMachine>` 的析构顺序
- 位置：`zvm/zpy/zvm_py.cpp` 顶部静态变量。
- 风险：进程退出时 C++ 静态对象析构序与 Python finalize、libuv loop 关闭交叉，曾出现过崩溃风险。建议在 `zce_fini_pyenv()` 内显式释放，并在 `Service::onWorkerStop` 之后调用。

### 3.3 [Tech-Debt] `ZuaMachine` 与 `ZpyMachine` 的 RPC 路径未抽象到 `Machine` 基类
- 位置：`zua_vm.cpp` / `zvm_py.cpp`。
- 现象：每种语言都自行 unpack 参数、压栈、调脚本、再 pack 返回；代码重复且容易在新语言（zjs/zcc）出现兼容偏差。
- 建议：在 `zvm_base` 中放一个 `dispatchMethod(...)` 模板，各 VM 只实现 `invokeRaw(...)`。

### 3.4 [Risk] `Proxy::start()` 在已经 CONNECTED 时不会触发 `open_cb_`
- 位置：`zvm/zvm_base.cpp:340-377`。
- 现象：`is_reuse_conn` 走的是 `_do_call()`，而 `state_` 已经是 CONNECTED 时不会触发 `call_cb`，业务想"重复 boot 同一连接"获取 open 时机会拿不到。
- 建议：确认是否需要复发 `open_cb_`；至少在文档里说明。

### 3.5 [Risk] `_zpy_registe / _zua_registe` 等静态 `VirtualMachineRegister` 依赖静态初始化顺序
- 位置：各语言 `zvm_*.cpp`。
- 现象：依赖每个翻译单元的 `zvm_creator::instance()` 在自己之前完成；目前 `zvm_creator` 是 `Singleton`，构造时按线程安全 lazy 初始化，OK。但如果链接器丢了未引用的 cpp（典型：把 libzce 链入 exe，又没保留 zpy/zua 的符号），就不会注册成功。
- 建议：在 CMake 静态库链接时显式 `-Wl,--whole-archive`，或暴露 `zce_register_all_vm()` 显式调用以防 dead-strip。

---

## 4. 数据库层

### 4.1 [Tech-Debt] `zdb_rdb.h` 大量 `// @todo check` 模板
- 位置：`include/zce/zdb_rdb.h` 共 18 处 `@todo check`/`@todo check isprc`。
- 现象：模板里 `select_byprop / insert / update / remove / execute` 都遗留了未实现/未确认的分支：是否处理 `isprc`（存储过程）参数、是否要 `skip_row` 等。
- 风险：使用 `select_byprop(connptr, vec, sql, prop)` 时只取首行就 `return` 的逻辑（`select_byprop` 的 vector 版本第 426 行 `return 1`）实际上**只插入一行就跳出循环**，与函数语义不符——疑似 Bug。
- 建议：审计每个 @todo，把"只取一行"逻辑改成 `continue`/`break` 显式控制。

### 4.2 [Bug][Fixed 2026-04-30] `select_byprop(vec)` 实际只返回首行（疑似复制粘贴遗留）
- 位置：`include/zce/zdb_rdb.h::DatabaseObject<TKEY,T>::select_byprop(std::vector<T>&,...)`。
- 原现象：while 循环里 `return 1` 直接退出，等同于"只取首行"。
- 修复：去掉循环体内的 `return 1`，让它正常迭代所有行后返回 `(int)vec.size()`。对标 `select_byprop_base(std::vector<Q>&,...)`、`select_all_vec`、`select_bykey(std::vector<T>&,...)` 的正确写法。
- 其余 `//@todo check` 仅是审计提醒，不影响行为，暂保留。

### 4.3 [Risk] `Connection::execute*` 的 catch-all 直接 `connptr->close()`
- 位置：多处 `catch (...) { connptr->close(); }`（`zdb_rdb.h` & 子类）。
- 风险：在多用户共享连接（连接池）的场景下，一次异常会把整池 close 掉。当前 `RedisDatabase` 用 `Tss tss_conn_` 做线程局部连接，但 SQLite/PG 的 `Database::getConnection` 实现需要确认是否每次都返回独立 conn。
- 建议：把异常包装成 `int err`，由调用方决定是否 close。

### 4.4 [Tech-Debt] `RedisConnection` 头：注释 “don't know why gcc call this”
- 位置：`include/zce/zdb_redis.h:33` 用 Windows 宏隔离了一个空拷贝构造。
- 现象：作者也不确定这条规则的必要性。
- 建议：实测后删除或改为 `= delete`。

### 4.5 [Build] MySQL 后端被构建禁用
- 位置：`include/zce/zce_inc.h:2-4`：`#define ZCE_ZDB_MYSQL 0`。CMakeLists 里没有任何 `-DZCE_ZDB_MYSQL=1` 入口。
- 现象：`zdb/zdb_rdb_mysql.*` 永远不参与编译；otlv4.h 是为 MySQL 准备的，目前无入口。
- 建议：明确把 MySQL 标为 deprecated（README 提一下）或补足 CMake 选项。

### 4.6 [Risk] `Database::DatabaseImpl` 无运行时注册接口
- 位置：`zdb_rdb.h:259-264` 留了 `pfn_DatabaseImpl_create`，但没看到统一注册中心。
- 风险：增加新数据库需要改 `Database` 构造函数 + 重编译。
- 建议：参考 `VirtualMachineRegister` 的模式，做插件式后端注册。

---

## 5. 协议 / 序列化

### 5.1 [Doc] ZDS 只有 v1，v2（tag-based）尚未发布
- 位置：`libsrc/libzce/zdp/README.md` 顶部声明 “version 1 stable, will be superseded by future tag-based version”。
- 现象：README/RFC 与实现已固定 v1，没有迁移计划。
- 建议：制定演进路线图（保留 prefix=ZDS_PAYLOAD_TAGSTRUCT 的占位说明）。

### 5.2 [Risk] zGen 生成的 `zdp_base_proto.h/zdp_base_pack.h` 直接放在头文件公开仓库
- 位置：`include/zce/zdp_base_*.h`、`zdp/zdp_base.ptl`。
- 风险：开发者可能直接修改生成文件而忘了 `.ptl`。
- 建议：在生成文件顶端的标识保留 `// don't modify manually`，并在 CI 中校验生成内容与 `.ptl` 一致。

### 5.3 [Tech-Debt] `zds_persist.h:129` 一个 `@todo`
- 现象：未完成的持久化路径，可能在新业务里被踩到。
- 建议：列入 backlog 并补 unit test。

---

## 6. 应用框架 (`zce::Service`)

### 6.1 [Risk] `Service` 与 `Reactor` 单例耦合
- 位置：`Service::Service` 直接 `zce::ReactorSigt::setInstance(this)` 并 `assert(instance_ == 0)`。
- 风险：进程内只能存在一个 `Service`，并强制把它作为 `ReactorSigt::instance()`；与多 reactor 共存场景不兼容。
- 建议：把 `Service` 的 instance 抽离出 `ReactorSigt`，并允许业务自创建辅助 Reactor。

### 6.2 [Bug] `Service::main` 在 `console` 子命令下把 `mode` 设为 `"daemon"`
- 位置：`core/zce_service.cpp:196-202`。
- 现象：`console` 流程沿用 daemon 路径，但 `isDaemonProcess()` 又是按 `mode == "daemon"` 判定，结果"console"模式被识别为 daemon，前台 stdin 流由 `__DEBUG` 标记触发。容易让 `isDaemonProcess()`/`isWorkProcess()` 的语义混淆。
- 建议：增加 `isConsoleProcess()` 显式判断，或 mode 命名为 `daemon-console`。

### 6.3 [Risk] `runWorkerProcess` 把所有异常吞掉
- 位置：`zce_service.cpp:144-165`。
- 现象：`catch (...)` 只是打日志，然后 `return EXIT_FAILURE`。在生产环境里堆栈丢失，难以定位。
- 建议：使用 `boost::stacktrace` / `backtrace_symbols` 在 catch 时打印调用栈。

### 6.4 [Doc] Windows 服务 `_cbWindowsServiceCtrlHandler` 接收的命令字未列出
- 位置：`zce_service.cpp` `_cbWindowsServiceMain/_cbWindowsServiceCtrlHandler`。
- 风险：用户不知道支持哪些 SCM 命令（STOP/SHUTDOWN/PRESHUTDOWN/PARAMCHANGE…）。
- 建议：补充表格到 `LIBZCE.md`。

### 6.5 [Risk] `Service::onTimer` 内 daemon/worker 行为相互扭结
- 位置：`zce_service.cpp:357-380`。
- 现象：每秒一次 timer 一并做"Win32 SCM heartbeat / 启动延时检查 / 子进程重连"。如果用户重写 `onTimer` 没有先调用基类，行为会丢失。
- 建议：把"基础维护"剥到 `_baseTimer()` 私有函数，文档强调子类需要 `Service::onTimer()` 显式调用。

---

## 7. 日志 / 可观测

### 7.1 [Risk] 日志 cleanup 仅匹配 `*-MM-dd.NNN.log` 格式
- 位置：`log/zce_log.cpp:60-85` 的 `_parse_date_from_filename`。
- 现象：只识别 `name-MM-dd.NNN.log`；自定义 prefix/带年的命名（如 `app-2025-04-30.log`）不会被清理。
- 建议：放宽正则或允许业务注入清理规则。

### 7.2 [Tech-Debt] 日志全局 `console_verbose_level_` 是 `static` 文件级变量
- 位置：`log/zce_log.cpp:32`。
- 现象：跨翻译单元控制不便；只能通过环境变量 `ZCE_LOG_CONSOLE_LEVEL` 设置一次。
- 建议：暴露 `zlog_setconsolelevel` 之类接口。

### 7.3 [Risk] `zlog_setremote` 没有失败回路
- 位置：`include/zce/zce_log.h:73`。
- 现象：UDP/TCP 连接失败时静默丢弃日志。建议加入失败统计。

---

## 8. 内存 / 对象监控

### 8.1 [Risk] `BlockPool` 的 `add_pool` 非线程安全
- 位置：`include/zce/zce_mbpool.h` 头部注释明确说明：“add_pool 非线程安全，必须在初始化时全部 add 完成”。
- 风险：业务在运行时动态扩展池会出问题；目前没有运行时 assert。
- 建议：在第一次 `acquire` 后冻结池配置，并 fatal log 任何 `add_pool` 调用。

### 8.2 [Risk] `Object::__decref` 在 `release_delegator_` 失效后会内存泄漏
- 位置：`include/zce/zce_object.h:65-73`。
- 现象：如果 `delegator` 已经 stop（`Reactor::stop` 后再有 SmartPtr 析构），`delegateRelease` 返回 `-1` 时对象不会被 delete。
- 建议：在 `Reactor::stop` 后清空 `release_delegator_` 并切换为 `delete this`。

### 8.3 [Tech-Debt] `OBJECT_MONITOR` 总是开启
- 位置：CMakeLists 把 `OBJECT_MONITOR` 加到平台编译宏。
- 现象：即便 release 也会带计数开销。
- 建议：默认 release 关，仅 debug/profile 开。

---

## 9. 测试与构建

### 9.1 [Build] CMake 在某些平台需要手工添加 lua/python 路径
- 位置：`CMakeLists.txt:48-62`，硬编码了 `/usr/local/include/python3.13`、`/usr/include/lua5.4` 等。
- 风险：升级 Python 3.14、Lua 5.5 或在 Apple Silicon Homebrew 路径变更时会编译失败。
- 建议：改用 `find_package(Python3 COMPONENTS Development.Embed)`、`find_package(Lua REQUIRED)`。

### 9.2 [Build] `core/zce_service.cpp` 依赖 CLI11 头，找不到时整个 service 被剔除
- 位置：CMakeLists 71-76：找不到 CLI11 时 `list(REMOVE_ITEM core .../zce_service.cpp)` 并打 warning，但 libzce 仍会编出来。
- 风险：业务调用 `zce::Service` 链接期才发现符号缺失。
- 建议：要么把 CLI11 标为必需，要么在头里加 `#error` 友好提示。

### 9.3 [Build] `zvm/zjs/` 全部被注释掉
- 位置：CMakeLists 119 / 159 等。
- 现象：JS VM 框架在仓库存在，但默认不参与构建，也没有 CI 验证。需要明确生命周期：是否长期维护，还是删除。

### 9.4 [Build] `BUILD_SHARED_LIBS=ON` 未验证
- 位置：CMakeLists 21。
- 现象：libzce 大量内嵌静态资源（sqlite3, secp256k1, zua vendor），共享库构建未做导出表（只在头里点缀 `ZCE_API`）。
- 建议：暂时禁用 `BUILD_SHARED_LIBS=ON` 或者补足 export map。

### 9.5 [Build] 大量第三方告警关闭：`-Wno-deprecated-declarations`、`-Wno-gnu-zero-variadic-macro-arguments`
- 位置：CMakeLists 391-393。
- 风险：屏蔽了一些 OpenSSL 3 的真实迁移点（HMAC、EVP_*）；ZCE_DEBUG/ZLOG 宏依赖 GNU 扩展，未来 clang 升级可能失效。
- 建议：清理 `RAND_pseudo_bytes` 等已弃用 API；切换 `ZLOG` 宏为 `__VA_OPT__(,)__VA_ARGS__` 写法。

### 9.6 [Build] OpenSSL 3 静态生效环境下 `OpenSSL_add_all_algorithms` 已废弃
- 位置：`core/zce_api.cpp:148-150`。
- 现象：在 OpenSSL ≥ 1.1.0 这是 no-op，1.1+ 之后无需调用；3.x 下虽可调但会触发 warning。
- 建议：用 `OPENSSL_init_crypto(...)` 替代，或者完全移除。

### 9.7 [Build] PostgreSQL/Redis 头路径在 CMake 中拼成长清单
- 位置：CMakeLists 41-62 / 240-252。
- 风险：维护成本高；多个 Homebrew 版本叠加时（`libpq` + `postgresql@18`）顺序敏感。
- 建议：拆分到 `cmake/Findxxx.cmake` 文件。

### 9.8 [Test] gtests 部分功能依赖外部资源（Python、Lua）
- 位置：`gtest/test_zvm*.cpp`、`test_zce_api.cpp`。
- 风险：CI 没跑通时被注释掉，长期会与实现漂移。
- 建议：在 README 加“开启 ZVM 测试需要 ZCE_TEST_PYTHON_HOME”说明，并把 Lua/Python 测试拆成单独 target，未配齐就跳过。

---

## 10. 杂项 / 文档

### 10.1 [Doc] README.md 与 CLAUDE.md 不一致
- 现象：仓库 `libsrc/libzce/CLAUDE.md` 描述模块为 `core / log / zdb / zvm / text / xml / zdp / zwt`，README.md 又额外列出 `mat / rsa / exp`。
- 建议：定期同步两份文档，或互相 cross-link。

### 10.2 [Doc] `LIBZCE.md` 在仓库根，但 `libsrc/libzce` 内部没有 cross-link
- 建议：在 `libzce/README.md` 顶部加引用，便于搜索。

### 10.3 [Doc] 注释多语言混杂（中文 + 英文 + 缩写）
- 现象：`zvm_base.h` 头注释中文，函数英文，错误日志混合。
- 建议：所有公共头注释、Doxygen 注释统一为英文（参照 `cpp-programming-guidelines`），中文注释放在 README/AI 文档里。

### 10.4 [Doc] `ZuaAPI.md` 与 `ZuaAPI_en.md` 内容偏长，未拆分
- 建议：拆分为 modules / examples / api-reference 三个文件。

### 10.5 [Tech-Debt] 大量 `// override from IStream` 注释，但部分 override 没有 `override` 关键字
- 现象：`Process::on_open / on_packet / on_close` 写了 override，但 `RpcStream::client_Proc_MSG_NONE_REQ` 等私有函数没有标识；老代码混用。
- 建议：开启编译选项 `-Wsuggest-override`（GCC/Clang）后逐文件清理。

### 10.6 [Tech-Debt] `zce::Object` 的 `obj_idx_` 是 `const zce_int64`
- 风险：`std::vector<Object>` / 拷贝构造能编译，但 oid 不会真正变更（拷贝构造里仍调 `next_oid()`，但 `operator=` 不变更 oid）。容易造成调试时 oid 误判。
- 建议：删除拷贝构造或显式禁止 `=`，并在文档里说明。

---

## 11. 安全相关

### 11.1 [Risk] 大量 `assert` 在 release 构建依然展开为 `ZLOG_FATAL`
- 现象：`ZCE_ASSERT` 在 release 也会执行表达式并写日志，不会 abort，但会大量制造 fatal log 噪音。
- 建议：根据等级区分 `ZCE_ASSERT_DEBUG`（仅 debug 生效）与 `ZCE_VERIFY`（fatal+abort）。

### 11.2 [Risk] `RsaRef`(`rsa/`) 是上世纪 90 年代的代码（RSAREF）
- 位置：`rsa/r_*.c`、`rsa.c`、`md5c.c`、`desc.c`。
- 风险：MD2/MD5/DES/RSA-1024 在现代场景已经不安全。
- 建议：标注模块"legacy only"，新业务请使用 `OpenSSL` / `secp256k1` / `zce_ssl.h`；考虑物理隔离到 `rsa-legacy/`。

### 11.3 [Risk] HTTP 解析对超长头无明确上限
- 位置：`text/http_stream.cpp` 的 `unpack`。
- 风险：客户端可能发超大 header 导致内存膨胀。
- 建议：增加 `MAX_HEADER_BYTES` 阈值（默认 16k 或可配）并在超出时关闭连接。

### 11.4 [Risk] `Acceptor` 没有连接速率限制
- 现象：恶意端可在短时间打开大量 TCP，导致 `Tcp` 实例暴涨。
- 建议：与 `block_dict_` 联动，新增 `accept-rate / max-concurrent` 限制。

### 11.5 [Risk] `Service` 的 stdin 命令仅判断 `x` / `o` 等单字符
- 位置：`zce_service.cpp:382-388`。
- 风险：调试用通道，不设鉴权；上线时如果 stdin 没关掉，本地可控；但配合 daemon 模式不应该开。
- 建议：仅在 `console` 模式启用 stdin。

---

## 12. 后续建议（汇总）

> 2026-04-30 修复状态见条目中 `[Fixed ...]` 标签。此处保留 backlog 便于排期。

| 优先级 | 任务 | 涉及位置 | 状态 |
| ------ | ---- | -------- | ---- |
| P0 | 修复 `select_byprop` vector 版本只取首行的逻辑 (4.2) | `include/zce/zdb_rdb.h` | ✅ 2026-04-30 |
| P0 | 解决 `_delegateFuture` 的 “unknow buggy” 提示 (1.1) | `include/zce/zce_task.h` | ✅ 2026-04-30 |
| P0 | 在 OpenSSL 3 + Python 3.13 上回归 ZpyMachine (3.1, 9.6) | `zvm/zpy/`, `core/zce_api.cpp` | TODO（需要运行环境） |
| P1 | 抽取通用 `dispatchMethod` 减少 VM 重复代码 (3.3) | `zvm/zvm_base.cpp` | TODO |
| P1 | 完成 `HttpStream::on_prepare_nextres` (2.1) | `text/http_stream.cpp` | ✅ 2026-04-30 |
| P1 | 让 `Reactor::stop` 在自身线程内安全调用 (1.5) | `core/zce_reactor.cpp` | ✅ 2026-04-30 |
| P1 | `Acceptor::block_dict_` 定期清理 (2.4) | `core/zce_handler.cpp` | ✅ 2026-04-30 |
| P1 | DNS 缓存 TTL 可配置 / 可清空 (2.3) | `core/zce_reactor.cpp` | ✅ 2026-04-30 |
| P1 | RpcStream 版本协商过低/未知 msgmid 友好断链 (2.6, 2.7) | `zvm/zvm_base.cpp` | ✅ 2026-04-30 |
| P2 | 用 `find_package(Python3/Lua)` 替代硬编码包含路径 (9.1) | `CMakeLists.txt` | TODO |
| P2 | 清理 `OBJECT_MONITOR`、统一 ASSERT 等级 (8.3, 11.1) | 全局 | TODO |
| P2 | `zce_log` 支持自定义清理规则、可观测 (7.x) | `log/zce_log.cpp` | TODO |
| P3 | 整理 README/CLAUDE/LIBZCE 文档一致性 (10.x) | `libsrc/libzce/README.md` 等 | TODO |

---

> 本文档基于一次静态 review 整理，未实际跑回归。对每条记录建议在仓库提一个 issue/任务并附上复现/修复 patch。
