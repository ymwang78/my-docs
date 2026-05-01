# libzce 架构说明

> 本文档面向 AI Agent 与开发者，整理 `libzce`（Zhidu Communication Engine, 又名 ZCE）静态库的整体架构、模块职责、关键对象关系、初始化与运行流程。
> 适用版本：源码快照 ~2026-04，仓库根 `D:/Github/cxxproj/libsrc/libzce`。

---

## 1. 总体定位

`libzce` 是一个 C++17 的通用通信/服务运行时基座，提供：

- 跨平台基础设施（线程、进程、文件、同步、原子、时间、加解密、字符串等）。
- 基于 **libuv** 的异步事件循环 `Reactor`，配合工作线程池 `Scheduler` 形成 **Reactor + Worker** 模型。
- 自研引用计数对象/智能指针体系（`zce::Object` + `zce::SmartPtr`），统一对象生命周期与跨线程释放策略。
- 协议/序列化层（**ZDP** 报文头 + **ZDS** 二进制序列化 + BSON/Storm/PTP/HTTP/WebSocket 等）。
- 数据库抽象层（**zdb**：SQLite / PostgreSQL / Redis）。
- 多语言虚拟机宿主（**zvm**：Lua / Python / C-VM, 预留 JS）。
- 应用层框架 `zce::Service`（Daemon / Worker / Windows Service / 控制台 / 子进程）+ 进程间消息总线 `Storm`。
- 顶层日志/告警/对象监控等可观察性设施。

> 它的目标是 **服务进程基座**：上层只关心业务逻辑，把网络、并发、IPC、数据访问、脚本扩展全部交给 libzce。

---

## 2. 顶层模块布局

源码目录结构（仅列与构建相关的模块）：

```
libsrc/libzce/
├── core/         # 基础设施 + 事件循环 + 任务/线程/进程/服务/SSL/文件
│   ├── win32/      # Win32 平台特化
│   └── android/    # Android 平台特化
├── log/          # 日志框架
├── mat/          # 矩阵/数值计算 (zce_mat)
├── rsa/          # RSA/MD2/MD5/DES 等遗留加密 (含 linux/win32 子目录)
├── exp/          # 实验性流：whp_stream(WebRTC), rtp_stream, nano_stream
├── text/         # HTTP / URI / TextStream
├── xml/          # 轻量 XML 解析与转换 (zxml_*)
├── zdp/          # ZDP 协议 + ZDS 序列化 + BSON + Storm + 协议生成
├── zdb/          # 数据库抽象（sqlite/pgsql/redis），含三方 sqlite3 源码
├── zvm/          # 虚拟机框架 (zvm_base/zvm_pimpl/zvm_rpc) + 各语言子集
│   ├── zua/        # Lua VM
│   ├── zpy/        # Python VM (pybind11 + subinterpreter)
│   ├── zcc/        # C VM
│   └── zjs/        # 预留 JS（quickjs-ng，默认未编入）
├── zwt/          # 链上/钱包工具：tron, secp256k1, keccak
├── gtest/        # GoogleTest 单元测试
└── CMakeLists.txt # 顶层构建脚本（含 ENABLE_ZVM/ENABLE_ZDB_* 开关）
```

对外头文件统一存放于 **`include/zce/`**（仓库 `cxxproj/include/zce/`），包含路径 `#include "zce/zce_xxx.h"`。

---

## 3. 关键分层

```
┌────────────────────────────────────────────────────────────────┐
│ 应用 / CTL / 业务进程        (各 *ctl, 业务 daemon, gtests)     │
├────────────────────────────────────────────────────────────────┤
│ 应用框架层  zce::Service  +  zce::SubProcessHost / SubProcess  │
│             基于 CLI11 解析 daemon/console/work/service 子命令 │
├────────────────────────────────────────────────────────────────┤
│ VM/RPC 层   zvm::VirtualMachineStub  →  zvm::Machine  →  Proxy │
│             zdp::Storm + StormVM + StormClient (发布订阅总线)  │
├────────────────────────────────────────────────────────────────┤
│ 协议/序列化 ZDP 头 + ZDS payload + BSON/JSON/HTTP/WebSocket    │
│             zdp_stream / RpcStream / HttpStream / RTP / WHP    │
├────────────────────────────────────────────────────────────────┤
│ 网络/IO    Tcp / Udp / Pipe / Tty / Acceptor / Connector       │
│             SSL / Socks / DnsResolve  (基于 libuv)             │
├────────────────────────────────────────────────────────────────┤
│ 调度核心    Reactor (单线程 uv_loop)  +  Scheduler (Worker池)  │
│             TaskQueue / Task / Timer / TaskDelegator           │
├────────────────────────────────────────────────────────────────┤
│ 内存/对象   Object + SmartPtr + Allocator(Chunk/V2)            │
│             RefBlock + DataBlock + BlockPool + Tss             │
├────────────────────────────────────────────────────────────────┤
│ 平台原语   Mutex/RW/Sema/Atomic/Thread/Filesystem/Time/log     │
│             zce_api（zce_init/zce_fini/编解码/inet/压缩…）     │
└────────────────────────────────────────────────────────────────┘
```

各层只依赖更下层；上层模块通过头文件接口或 `pimpl` 隐藏实现。

---

## 4. 核心抽象

### 4.1 对象生命周期：`zce::Object` + `zce::SmartPtr`

- 所有运行时对象统一从 `zce::Object`（`include/zce/zce_object.h`）派生。
- 计数为 `mutable AtomicLong ref_count_`，`__addref/__decref` 控制引用，析构时分三路：
  1. 若设置了 `release_delegator_`：投递到指定线程释放（解决跨线程析构不安全的问题）。
  2. 若设置了 `zce_alloc_`：调 `__free_me()` 走自定义 Allocator。
  3. 否则 `delete this`。
- `zce::SmartPtr<T, LOCK = MutexNull>` 是侵入式智能指针，模板锁可选；提供 `__dynamic_cast` 用于跨多态指针转换。
- 每个对象拥有全局唯一 `oid_`（来自 `Tss::getGlobal()->next_oid()`）便于日志/对象监控（`zce::ObjectCounter`）。
- 还提供 `shared_ptr()` 适配标准 `std::shared_ptr`。

### 4.2 数据块：`DataBlock` / `RefBlock`

- `DataBlock` 是引用计数的物理缓冲区，可来自分配器或外部。
- `RefBlock` 是 `DataBlock` 的视图（`prespace + length + space`，三段语义见 `zce_dblock.h` 头注释）。
- 网络 IO、协议 pack/unpack、IPC 都以 `RefBlock` 为统一字节单位，从 `BlockPool`（`zce_mbpool.h`）池化分配；宏 `ZCE_MBACQUIRE` 提供按需取块。

### 4.3 分配器：`zce::Allocator`

- 提供两种实现：
  - `Allocator::createChunk(size, n, lock)`：固定大小 chunk 池，适合高频小对象。
  - `Allocator::createDynamic(size, n, lock)`：动态长度（在 atomic_size 单元上分配，元数据约占 1/atomic_size）。
- 允许把 `Object*` 绑定到 Allocator，析构时由 Allocator 回收，避免 `new/delete` 抖动。

### 4.4 线程局部状态：`zce::Tss`

- `Tss::global_t` 持有全局 `oid_` 计数、错误码缓存、当前 `TaskDelegator`、`Semaphore` 池等。
- `zce_global_semaphore` / `zce_env_task_delegator` 是 RAII 包装，用于阻塞同步与跨线程委托上下文切换。

### 4.5 同步原语 `zce_sync.h`

- `MutexNull / Mutex / MutexReadWrite / Semaphore` 全部 pimpl，跨平台 0 模板。
- `Guard / GuardRead / GuardWrite / Lock / LockRead / LockWrite` 提供 RAII 包装，并支持 `tempUnlock / tempLockWrite` 倒排锁段。
- `ExecPermit` 提供单写者执行许可证，常用于"任意时刻只允许一个回调进入"的语义。

---

## 5. 调度核心

```
                ┌─────────────────────┐
                │   zce::Scheduler    │  Worker线程池（默认 1+N）
                │  (work-stealing,    │  每个 Worker 自己 spec_queue + 全局 task_queue
                │   uv_cond/uv_mutex) │
                └─────────┬───────────┘
                          │ delegate / performFunc / performFuture
                          ▼
                ┌─────────────────────┐
                │  zce::TaskQueue     │  顺序队列（FIFO），可多个挂在 Scheduler 上
                │  (TaskDelegator)    │
                └─────────┬───────────┘
                          │ Task::call()
                          ▼
                ┌─────────────────────┐
                │  zce::Reactor       │  libuv 单线程 loop，跨线程靠 uv_async_t
                │  (TaskDelegator)    │
                └─────────────────────┘
```

### 5.1 `Reactor`

- 拥有独立 `uv_loop_t` 和 `uv_async_t`，IO 事件、定时器、DNS 都跑在同一个线程。
- `start(in_place)`：创建 `ReactorThread`，根据 `in_place` 决定是否立即 `uv_run`。
- `delegateTask` 跨线程投递任务：写入 `delegate_deque_` 后通过 `uv_async_send` 唤醒 loop，再在 loop 线程批量 `delegate_work` 执行（最多并发 2 次唤醒以减抖）。
- `delegate_delay` 用 `uv_timer_t` 调度延时任务（必须在 loop 线程内调用，跨线程会自动 delegate 一次）。
- `dns_resolve` 自带 60s 缓存，避免风暴。
- 析构由 `SmartPtr` 管理，`Reactor` 受 `Singleton<Reactor, MutexNull>`（`ReactorSigt`）单例支持，但 `Service` 派生类可直接 `setInstance` 覆盖。

### 5.2 `Scheduler`

- 每个 `Worker` 都有：本地 `spec_queue_`（精准投递）、`uv_cond_t/uv_mutex_t`（睡眠唤醒）、`idle_value_` 标记。
- 对外接口：`active(N)`、`stop()`、`perform(task)`、`perform(task, idx)` 精准绑定线程、`performFunc(F)`、`performFuture(F, args...)`（封装 `std::promise`，结果使用 `TaskResult<T>` 统一表达 `Success / TaskException / SubmitFailed`）。

### 5.3 `TaskQueue` / `Task` / `TaskDelegator`

- `Task` 是基础单位（`call()` 必须重写）。
- `TaskQueue` 同时是 `Task` 又是 `TaskDelegator`：把多个任务串行化、绑定到一个 `Scheduler`、提供 `pause/resume/attach`。
- `TaskDelegator::delegate(bwait, name, F)`：
  - `bwait=false`：投递回调 `Fr_task` 到执行器（不等待）。
  - `bwait=true`：取一个 `Tss` 全局信号量，提交任务后 `acquire()` 同步等待（避免重复 new sem）。
- `Reactor` / `TaskQueue` / `Scheduler` 都实现了 `TaskDelegator`，因此业务代码使用同一个 `delegate(...)` 接口，无需感知具体执行器。

### 5.4 `Timer`

- `Timer(reactor, taskqueue, ms, repeat)` + `start(cb)`：在 reactor 线程调起；如指定 `taskqueue` 则把回调进一步派发到该队列（避免重型任务阻塞 IO）。
- `TimerDoozer` 提供合并触发（防止累积放大）。

---

## 6. 网络/IO 层

> 全部围绕 `zce::IStream` 抽象（`zce_handler.h`），上下游通过 `prev/next` 形成"双向链表式协议栈"。

```
应用层(IStream) -- prev/next --> 协议层(IStream)
                   ZdpStream/HttpStream/RpcStream
        ↑
       link
        ↓
传输层 Socket  →  Tcp / Udp / Pipe / Tty
                   |  attach 到 Reactor 上的 uv_handle
                   v
                Reactor (libuv loop)
```

- **`Socket`**：缓冲区/读引用计数/远端地址等公共字段，子类实现 `do_write` 与 `handle()` 返回 uv 句柄。
- **`Tcp` / `Udp` / `Pipe` / `Tty`**：均是 `Socket` 的具体实现；`Pipe` 同时支持 IPC 与 TTY 风格。
- **`Acceptor`**：监听 TCP，回调 `make_handler()` 为新连接创建 `Tcp`；带阻塞名单 `block_dict_`（防 DDoS / 重连风暴）。
- **`Connector`**：发起 TCP 连接，超时 + DNS 解析 + 地址族识别。
- **`PipeAcceptor` / `PipeConnector`**：命名管道版本，Windows 走 `\\.\pipe\<name>`，Linux 走 `/tmp/<name>`。
- **`Signal`**：跨平台信号挂载（基于 uv_signal）。
- **`SyncStream`**：把异步流读写绑定到指定 `TaskQueue`，使上层回调在固定线程触发。
- **`SocksStream`**：Socks5 客户端协议封装。
- **SSL**：`zce_ssl`（基于 OpenSSL），通过 `link` 插入到 Tcp 上层；编译宏 `ZCE_SUPPORT_SSL` 控制。
- **DNS**：`Reactor::dns_resolve` + `DnsResolve` 接口，60s 内做合并/缓存。

### 6.1 应用协议

- **HTTP/WebSocket**：`HttpStream` / `zce_http_client` / `WebSocketStream` / `zce_websocket_client`，支持 chunked / gzip / 标准 + uWSGI CGI。
- **RTP / WHP / Nano**：放在 `exp/` 下的实验流。
- **ZDP**：`zdp::zdp_stream`（`include/zce/zdp_stream.h`）实现"消息=固定头 + 序列化 body"，支持 `request/response`、超时 `zdp_resctx`、可压缩（auto/bzip2/none）、流式合包/拆包。
- **MCP**：`zce::McpHost` / `McpStream` 实现 JSON-RPC over HTTP 的 MCP 服务端骨架（基于 `nlohmann::json`）。

---

## 7. 协议与序列化

### 7.1 ZDS（ZCE Data Serialization）

- 二进制自描述格式（详见 `libsrc/libzce/zdp/README.md` 的 ZDS-RFC-001）。
- 每个字段一个 1 字节 prefix：`E(1) | Subtype(3) | Payload(4)`，其后跟变长整型 / 浮点 / 字符串 / 结构体 / dict / vector / matrix。
- C++ API：`zce::zdp::zds_pack` / `zds_unpack` / `zds_pack_multi` / `zds_unpack_multi` / `zds_pack_builtin` / `is_builtin_type`。
- 由代码生成器 **zGen** 从 `.ptl` 文件生成 `*_proto.h`（POD 结构体）+ `*_pack.h/cpp`（序列化）。仓库内的 `zdp/zdp_base.ptl` `zdp/zdp_comm.ptl` `zdp/zdp_storm.ptl` 都是源文件。

### 7.2 ZDP（ZCE Data Protocol）

- 通用消息分层：`zdp_head`（含 `msgmid/msgseq` 等）+ payload。
- 内置消息族 `MSG_NONE_REQ` / `MSG_DISCONN_REQ` / `MSG_CONTAINER_REQ/RES` / `MSG_RPCCALL_REQ/RES`（见 `zdp_base_proto.h`）。
- `zdp_serialize/zdp_serialize_struct` 负责"头 + body + 可选压缩 + 可选预留头空间"。
- `zdp_resctx` 维护请求-响应映射 + 超时定时器。

### 7.3 BSON

- `zce_bson.h` / `zce_bson.cpp`：与 ZDS 互通的 BSON 实现（依赖 libbson / mongoc 头）。

---

## 8. RPC 与虚拟机宿主（ZVM）

```
                ┌──────────────────────────┐
                │ VirtualMachineStub       │  对外门面，进程级单例 (Sigt)
                │  + initStub(scheduler,   │
                │     reactor, host_dir)   │
                │  + listen / listenSchema │
                │  + boot(zvm_t, args)     │
                └────────────┬─────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │ VirtualMachineStubPimpl  │
                │  vm_map_       guarded by│
                │  rpc_serve_map_ MutexRW  │
                └────────────┬─────────────┘
                             │ creator(vmtype) registered by
                             │ VirtualMachineRegister
                             ▼
                ┌──────────────────────────┐
                │ zvm::Machine (TaskQueue) │  抽象基类
                │  start/stop/call_dblock  │
                │  + sendResponse<T...>    │
                ├──────────────────────────┤
                │ ZuaMachine   (Lua)       │
                │ ZpyMachine   (Python)    │
                │ Proxy        (远端 VM)   │
                │ StormVM      (storm RPC) │
                │ SubProcessHost (子进程)  │
                │ FileSystemMachine (CCVM) │
                └──────────────────────────┘
```

- **注册式**：`VirtualMachineRegister _xxx_registe("py", creator)` 在 cpp 静态初始化阶段把"vmtype → 工厂"塞进全局 `zvm_creator` 单例；`Service::onDaemonStart` 注册 `vmhost / stormhost`，`zvm_py.cpp` 注册 `py`，`zvm_zua.cpp` 注册 `lua` 等。
- **`Machine`** 继承自 `TaskQueue`：所有进入虚拟机的调用都自动序列化到该 VM 的任务队列，避免脚本运行时多线程问题（Python 子解释器 GIL、Lua state 单线程等）。
- **远程调用**：`RpcStream` 是 `zdp_stream` 的 RPC 子类，做版本协商（`MSG_NONE_REQ` 携带 `ver=1.0`）、`MSG_RPCCALL_REQ/RES` 派发；`Proxy` 负责发起方的连接管理（含 pipe/tcp、SSL、断线重排、timeout）。
- **`RpcServantRemote` / `RpcServantPipe`**：服务端 listen 实现，监听端口/管道并把每个连接接到 `RpcStream`。
- **多 VM 复用同一连接**：`RpcStream::reuse_remote_map_` 允许一条已有连接上 boot 多个虚拟机代理（`boot_reuse_vm`）。
- **Python**：`ZpyMachine` 使用 pybind11 的 `subinterpreter` 隔离不同 VM；`gil_lock_` 与 `tss_threadstate_` 处理 GIL；`initPythonEmbedded` / `finiPythonEmbedded` 控制全局解释器；`zce_init_pyenv(home)` 在 C 侧设置 Python Home。
- **Lua**：`ZuaMachine` 内含一个 `lua_State`、`zua_allocator_`、`vmvar_keyexpire_ptr_` 等，通过 `zce::zvm::CoTaskCallee/Caller` 协程支持远程调用回到脚本。
- **Storm**：发布-订阅总线（详见 `zdp_storm.h`），`Storm`（服务端 / shard）+ `StormClient`（订阅端）+ `StormStreamAdapter`（把任意 IStream 桥接到 storm topic）+ `StormVM`（在 ZVM 体系下表现为一个 Machine）。

### 子进程模型（Process / SubProcessHost / SubProcess）

```
父进程 (daemon mode)                    子进程 (work --vmguid=GUID)
   │                                       │
   │ uv_spawn(exe, --vmguid=GUID)          │
   ├──────────────────────────────────────►│
   │                                       │ Service::connectToFatherProcess
   │                                       │   PipeConnector("\\.\pipe\GUID")
   │ PipeAcceptor(/tmp/GUID)               │   → ZdpStream
   │   └─→ SubProcessHost   ◄──────────────┤
   │       维护 zdb 表 subvm0              │
   │       PROCESS_S2M*, PROCESS_M2S*      │
```

- 父进程内 `SubProcessHost` 既是 VM（继承 `Machine`），又是子进程仓库（`map<name, SmartPtr<Process>>`）。
- 元数据落在 SQLite 数据库（`HostContext.metadb_path`，默认 `subvm.db`，表 `subvm0`），允许 daemon 重启后恢复。
- 通过 PROCESS_* 一组消息号交换：注册、心跳、查询/更新 vm 信息、退出请求等。
- `SubProcess` 是子进程侧的代理对象，`connectProcess()` 用 `PipeConnector` 接到父进程并把 `IStream` 串上。

---

## 9. 数据库（zdb）

```
zce::zdb::Database (ERV_DATABASE: SQLITE/MYSQL/PGSQL)
   └── DatabaseImpl (pfn_DatabaseImpl_create 注册)
         └── Connection (begin/commit/rollback/create_stmt/execute/...)
               └── Statement (operator<< / operator>> / endl / end_row)
```

- `zdb_rdb.h` 是统一抽象，模板 `DatabaseObject<TKEY, T>` 给数据访问类提供 `select_all / select_bykey / insert / replace / update / remove / execute` 等模板，行为通过用户类静态方法（`select_all_sql`, `insert_sql`, `extract`, `putinsertvars`…）描述 schema。
- `zdb_table<record, transaction>` 进一步封装 CRUD + create/drop。
- Redis：`zdb_redis.h` / `RedisDatabase` + `RedisConnection`（基于 hiredis），覆盖 KV/Hash/ZSet/List/expire 等常用操作；`ZdbRedis` 是 `redisReply*` 的 RAII 包装。
- ECPG/PostgreSQL：`zdb_ecpg.cpp` + `zdb_rdb_pgsql.cpp`，编译时通过 `ENABLE_ZDB_PGSQL` 控制（默认开）。
- SQLite：直接编入 `zdb/sqlite/sqlite3.c`，零外部链接。
- MySQL：`zdb_rdb_mysql.cpp` 保留但 `ZCE_ZDB_MYSQL` 默认 `0`，构建未启用。

---

## 10. 应用框架（zce::Service）

`Service` 同时是 `Reactor` 子类、`Singleton<Reactor, MutexNull>` 当前实例（`zce::ReactorSigt::setInstance(this)`）和应用入口。它把命令行处理、daemon 化、Win32 服务、控制台前台、子进程 worker 五种运行模式统一在一个类里。

### 10.1 命令行（CLI11 子命令）

```
<exe> daemon [<svcname>] [--logsuffix --configpath]
<exe> console            [--logsuffix --configpath]
<exe> work [--vmguid <guid>] [--vmtype --vmname --vmpath --pidfile ...]
<exe> service install|remove|start|stop|restart|status <name>   # 仅 Windows
<exe> help [target]
```

- daemon 模式：Linux 走 `runPosixDaemon` (`fork+setsid+stdio /dev/null`)，Windows 走 `StartServiceCtrlDispatcherA` + `_cbWindowsServiceMain`，再回调 `onDaemonStart()`。
- console 模式：跟 daemon 共享 `onDaemonStart()`，但保留 stdin（`zce::Tty(0)`）、加挂 SIGHUP/SIGINT/SIGTERM。
- work 模式：进入 `runWorkerProcess()`，Reactor 启动 -> `onReactorStart` -> `onWorkerStart`（用户实现）。如果是子进程（带 `--vmguid`），定时器里会 `connectToFatherProcess()` 拉起命名管道。
- service install：父进程帮忙 `daemon ...` 注册成 Windows 服务。
- `__DEBUG` 是 service_name 的特殊值，等价于"前台 daemon"，用于 IDE 调试。

### 10.2 重要成员

| 成员                | 说明                                                         |
| ------------------- | ------------------------------------------------------------ |
| `process_host_`     | `SubProcessHost`，daemon 模式下管理子进程                    |
| `storm_host_`       | `zdp::StormVM`，可选的进程内消息总线                         |
| `storm_client_`     | `zdp::StormClient`，子进程或单点连父进程的 storm             |
| `sub_process_`      | work 模式下连接父进程的 `SubProcess`                         |
| `sub_vm_`           | work 模式下从父进程接管的 vm 业务对象                        |
| `pipe_/tty_/signal_*` | 通信与信号通道                                              |
| `timer_`            | 1s 心跳：daemon 走 `checkDelayedStart()`，work 走重连父进程 |

### 10.3 三种角色

```
┌───────────────────────┐    pipe IPC    ┌──────────────────────┐
│       Daemon Process  │ <────────────► │   Worker Process(es) │
│  (Service::onDaemonStart)              │ (Service::onWorkerStart)│
│  - VirtualMachineStub                  │  - 直接业务，或       │
│  - SubProcessHost (启动/监控子进程)    │  - 作为子 VM 运行     │
│  - StormVM (可选)                      │                       │
└───────────────────────┘                └──────────────────────┘
```

---

## 11. 关键初始化流程

下面给出最常见的"daemon + 子进程 worker"启动序列，便于排查链路问题。

### 11.1 进程启动总览

```
main()
 ├── zce_init()                      // 在 zce_api.cpp，原子计数 _init_count
 │     ├── (Win32) CoInitialize + WSAStartup + zce_win32_init
 │     ├── (Linux) clock_gettime 检测 CLOCK_MONOTONIC_COARSE
 │     ├── (Apple) mach_timebase_info
 │     └── OpenSSL_add_all_algorithms      (ZCE_SUPPORT_SSL=1)
 │
 ├── zlog_init(...)                   // 日志/事件
 │
 ├── MyService svc("MyApp");          // svc->Reactor::Reactor("MyApp"): uv_loop_init, async_init
 │     └── zce::ReactorSigt::setInstance(this)   // 进程内默认 Reactor 单例
 │
 ├── svc.main(argc, argv);            // 解析子命令并分流
 │     ├── daemon → runPosixDaemon / startWindowsService
 │     ├── console → 等同 daemon 但前台
 │     ├── work → runWorkerProcess
 │     └── service * → 注册/卸载/查询 Windows 服务
 │
 └── zce_fini();
```

### 11.2 Daemon 主线（`onDaemonStart`）

```
Service::onReactorStart()                       // 注册 1s timer + signal/tty
  └── isDaemonProcess() ? onDaemonStart() : onWorkerStart()

Service::onDaemonStart()
  ├── VirtualMachineRegister("vmhost")          // 静态注册子进程 host VM
  ├── VirtualMachineRegister("stormhost")       // 静态注册 storm host VM
  ├── VirtualMachineStubSigt::instance()->boot(zvm_t{type=vmhost,...})
  │     └── 由 vmhost creator new SubProcessHost(stub, this, host_context_)
  │     └── start() → SubProcessHost::start
  │           ├── 打开 SQLite metadb + 表 subvm0
  │           ├── 加载历史进程信息 → addAutoCreateProcess
  │           └── PipeAcceptor.listen(host_context_.host_topic) 让子进程回连
  ├── (可选) boot stormhost:
  │     └── new StormVM(...).start() → 启 storm shard
  └── (可选) VirtualMachineStubSigt::listen(addr, port)
        └── new RpcServantRemote(...).start()  → 提供跨主机/跨进程 RPC

VirtualMachineStub::initStub(scheduler, reactor, host_dir)   // 通常更早调用
  └── new VirtualMachineStubPimpl(scheduler, reactor, host_dir) → 创建 GUID + makeDir
```

### 11.3 子进程主线（`onWorkerStart`）

```
Service::onReactorStart()
  └── isWorkProcess() ? onWorkerStart() : onDaemonStart()

work 模式下:
  - 若 --vmguid/--vmname 为空：作为前台 worker，挂 stdin + SIGHUP/INT/TERM
  - 否则：prctl(PR_SET_PDEATHSIG, SIGKILL) (Linux)，等定时器拉起 connectToFatherProcess()

Service::onTimer()  (1s)
  └── if work && !sub_process_:
        connectToFatherProcess(false)
          └── new zce::SubProcess(reactor)
                .connectProcess("\\.\pipe\<GUID>", connect_cb, disconnect_cb, data_cb)
          └── 收到 startVM 指令后:
                Service::startVMFromFather(zvm, content)
                  └── VirtualMachineStubSigt::instance()->boot(zvm, content)
                        → 由对应 vmtype 的 creator 实例化 ZuaMachine/ZpyMachine 等
```

### 11.4 RPC 调用流（Proxy → 远端 Machine）

```
client 业务代码
  └── VirtualMachineStub::boot(svc_name, host, port, ssl, ...)
        → 返回 SmartPtr<Object> = SmartPtr<Proxy>
  └── stub->rpc_call_dblock(proxy, objid, "method", dblock, timeout, response_cb)
        ├── 若不在 proxy 所在 reactor 线程，先 delegate 过去
        └── proxy->call_dblock → _do_dblock(item)
              ├── state==CONNECTED:    入队 + _do_call → client_ptr_->request(MSG_RPCCALL_REQ, …)
              ├── state==CONNNONE:     start() → Connector / PipeConnector 异步连
              └── state==CONNECTING:   入队等待 on_open

server 端 (RpcStream::on_packet)
  └── case MSG_RPCCALL_REQ:
        stub_->pimpl_ptr()->call_dblock_by_vmname(svcname, objid, method, payload, this, [response]…)
              └── vm->delegate(false, …, [=]{ vm->call_dblock_from_remote(...) })
                    └── ZuaMachine/ZpyMachine 在自己的 TaskQueue 里同步执行脚本调用，回调 response
```

### 11.5 Storm 发布订阅简流

```
StormClient(reactor, ident, token, ctx, child_cb, set_cb, on_open, on_close)
  → connect(fatherip, fatherport)        # Tcp + zdp_stream
  → subscribe("topic")                    # 服务端返回 topic_id（zce_int64）
  → publish(topic_id, data, len, trace)
       Storm::Pimpl 收到后通过分片队列分发到所有匹配子节点
  ← child_cb(ctx, n_topics, topics, from, data, len)
```

---

## 12. 跨平台与构建

- **CMake**：顶层 `libzce/CMakeLists.txt` 输出静态库 `zce`（=`libzce.a` / `zce.lib`）。
- **编译选项**：
  - `BUILD_SHARED_LIBS`（默认 OFF）；`BUILD_TESTS`（默认 OFF，开启时构建 `gtest/libzce_testExe`）。
  - `ENABLE_ZVM`（默认 ON）→ 同步把 `ZCE_SUPPORT_PYVM/LUAVM/CCVM` 宏置 1，否则置 0。
  - `ENABLE_ZDB_SQLITE / PGSQL / REDIS`（默认 ON）；至少一个开启时 `ENABLE_ZDB_COMMON` 自动开启。
  - 平台宏：`__WINDOWS__ / __LINUX__ / OBJECT_MONITOR / NDEBUG / HAVE_MEMMOVE / LUA_USE_LINUX`。
- **依赖**（核心）：
  - `Boost`、`libuv`、`uriparser`、`nlohmann_json`、`bzip2`、`expat`；
  - 数据库：`libpq` + `libecpg`（pgsql）、`hiredis`（redis）；
  - 脚本：Lua 5.4、Python 3.13（Linux 默认头）/3.12（Windows）、pybind11；
  - 安全：OpenSSL（可选 `ZCE_SUPPORT_SSL`）；
  - Windows 经 vcpkg（`x64-windows-static-md`），Linux 经 pkg-config + apt；
  - 三方源码内嵌：`zdb/sqlite/sqlite3.c`、`zwt/secp256k1/`、`zvm/zua/vendor`。
- **平台目录**：
  - Windows 平台特化在 `core/win32/`、`rsa/win32/`，Android 在 `core/android/`，Linux 在 `core/linux/`、`rsa/linux/`。
  - 编码必须 UTF-8 BOM（仓库根 `.cursor/rules/cpp-utf8-bom.mdc`）。
- **测试**：`gtest/`（GoogleTest），覆盖 allocator、any、api、array、convertor、hash、mat、reactor、task future、uri、zdp、zvm subinterpreter / listen schema 等；详细命令见仓库 `CLAUDE.md`。

---

## 13. 错误码与日志

- 错误码：`ERV_ZCE_ERROR`（`zce_inc.h`）按 0x81xxxxxx / 0x82xxxxxx 分段：
  - `ZCE_ERROR_*`：通用 ZCE 错误；
  - `ZDB_ERROR_*`：数据库；
  - `ZVM_ERROR_*`：虚拟机；
  - `ZAP_ERROR_*`：应用层（COIN/ZMPC）。
- `ZCE_ERROR_OK = 0`；`ZDB_SUCCE_COMMON / ZDB_SUCCE_MULTIRESPONSE` 是成功类回执。
- 日志：
  - C 接口 `zlog_logv` + 宏 `ZLOG(level, fmt, ...)`、`ZLOG_SYSCALL`。
  - C++ 接口 `ZTRACE/ZDEBUG/ZINFOR/ZWARNI/ZERROR/ZFATAL`，使用 `zce::Logger` 流式拼装 `key|value|`。
  - 编译时有 `ZCE_DEBUG/ZCE_ERROR` 宏，运行时有 `ZLOG_TRACE … ZLOG_FATAL` 等级（`zlog_setlevel/getlevel`）。
  - 日志文件按日切分（`zlog_cleanup(keep_days)`），可远程 `zlog_setremote(ip, port)`。

---

## 14. 关键约定（贡献者必读）

1. **任何新对象** 都应继承 `zce::Object` 并由 `SmartPtr` 管理，避免裸 `delete`。
2. **跨线程释放/调用** 一律走 `delegate(...)`；如果在 `Reactor` 线程内 `delegate` 自身则直接同步执行。
3. **`Reactor` 线程禁忌**：不要在 IO 回调里做阻塞调用、长 CPU 任务、长 SQL；这类工作放 `Scheduler` Worker 或者 `TaskQueue::delegate(true, ...)` 同步等待。
4. **协议字段** 必须用 `.ptl` + zGen 生成，不要手写 `*_proto.h / *_pack.cpp`。
5. **新 VM 类型** 用 `VirtualMachineRegister("type", creator)` 注册，creator 内构造 `Machine` 子类即可；不要直接修改 `VirtualMachineStubPimpl`。
6. **数据库表/列** 命名遵循 `cxxproj/CLAUDE.md` 的复数 + snake_case 约定（参见仓库根 CLAUDE）。
7. **新源文件** 必须 UTF-8 with BOM，命名空间 `zce::`，类 PascalCase、函数 camelCase、变量 snake_case、成员 snake_case_。
8. **静态全局对象** 的析构顺序敏感：`Singleton::release()` 或 `setCallback(nullptr)` 应在 `zce_fini` 之前显式释放。

---

## 15. 速览：常见入口

| 入口                                   | 说明                                              |
| -------------------------------------- | ------------------------------------------------- |
| `zce_init() / zce_fini()`              | 进程级初始化/收尾（COM/WSA/openssl/clock 等）     |
| `zce_init_pyenv(home)`                 | 注入 Python Home（Linux 默认 `/opt/venv`）        |
| `zce::Service` 派生 + `main(argc,argv)` | 启动 daemon/console/work/service                 |
| `zce::ReactorSigt::instance()`         | 获取主 Reactor（Service 派生时 = 自己）           |
| `zce::SchedulerSigt::instance()`       | 获取全局 Scheduler                                |
| `zce::zvm::VirtualMachineStubSigt::instance()` | 获取 VM 注册中心，调用 `boot/listen/get_vm` |
| `zce::BlockPoolSigt::instance()`       | 内存块池（`ZCE_MBACQUIRE`）                       |
| `zce::Tss::getGlobal()`                | 当前线程局部状态                                  |

---

参考原始资料：
- 仓库 `libsrc/libzce/README.md`、`CLAUDE.md`
- `libsrc/libzce/zdp/README.md`（ZDS RFC）
- 头文件：`include/zce/zce_api.h, zce_object.h, zce_reactor.h, zce_handler.h, zce_task.h, zce_service.h, zce_process.h, zvm.h, zdp_stream.h, zdp_storm.h, zdb_rdb.h …`
