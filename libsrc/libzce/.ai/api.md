# libzce 关键 API 索引

> 仅整理对外可用、最常被复用的 API。完整声明请以 `include/zce/*.h` 为准。
> 所有头文件包含路径都是 `#include "zce/xxx.h"`（包含根：`cxxproj/include/`）。

---

## 1. 进程初始化与基础设施 (`zce_api.h`)

| API | 说明 |
| --- | --- |
| `int zce_init()` / `void zce_fini()` | 进程级初始化与收尾，幂等（`AtomicLong _init_count`）。Win32 会做 `CoInitialize/WSAStartup`，启用 SSL 时会 `OpenSSL_add_all_algorithms`。 |
| `int zce_init_pyenv(const char* python_home)` / `void zce_fini_pyenv()` | 在嵌入 Python 前设置 Python Home（即 prefix 目录，需含 `lib/pythonX.Y`）。 |
| `zce_uint64 zce_tick()` / `zce_uint64 zce_nowms()` | 单调时钟与系统时间（毫秒）。 |
| `zce_timestamp zce_timestamp_now()` / `zce_to_timestamp(time_t)` / `zce_to_timet(zce_timestamp)` | ZCE 自定义时间戳互转。 |
| `int zce_localtime_str(char* buf, int size, bool msec)` / `std::string zce_localtime_str(bool msec)` | 本地时间字符串。 |
| `unsigned zce_thread_id()` | 跨平台线程 id。 |
| `void zce_msleep(int msec)` / `bool zce_interrupted()` | 跨平台睡眠/中断检查。 |
| `void zce_enable_coredump(bool)` | 开启 coredump（Windows/Linux 都支持）。 |
| `unsigned zce_getmem()` / `unsigned zce_getcpu()` | 当前进程 RSS / CPU 占用。 |
| `int zce_compress / zce_decompress(ERV_ZCE_COMPRESS, ...)` | 压缩/解压（AUTO/NONE/BZIP2）。 |
| `int zce_inet_pton/ntop/aton/ntoa/parse_host_port` | IP 解析/格式化。 |
| `int zce_create_pipe(SOCKET fds[2])` | 跨平台 pipe socketpair。 |
| `int zce_base64/58/32_encode/decode`、`zce_to_hex/from_hex` | 编解码。 |
| `std::string zce_md5sum(const char*)`, `zce_hash_md5/sha256(...)` | 哈希。 |
| `std::string zce_string_format(unsigned len, const char* fmt, ...)` | 安全 sprintf。 |
| `std::string zce_trim(const std::string&, ...)` | 去空白。 |
| `class zce_profile` | RAII 性能采样：超过 `limit` 会打 ZTRACE。 |
| `int zce_list_ip(std::vector<std::string>&)`, `zce_get_mac/hardrive/cpuinfo/hostname/imei/harddrv` | 主机信息收集。 |

---

## 2. 日志 (`zce_log.h`)

```cpp
zlog_handle zlog_init(zlog_handle share, zlog_param* p);
void zlog_fini();
void zlog_setlevel(unsigned level);    // ZLOG_TRACE..ZLOG_NONEL
unsigned zlog_getlevel();
void zlog_setremote(const char* ip, unsigned short port);
void zlog_cleanup(int keep_days);
```

宏：
- C 风格：`ZLOG(lv, fmt, ...)`、`ZLOG_SYSCALL(lv, s)`、`ZCE_DEBUG((ZLOG_xxx, fmt, ...))`。
- C++ 流式：`ZTRACE/ZDEBUG/ZINFOR/ZWARNI/ZERROR/ZFATAL(arg, arg, ...)` 自动用 `|` 分隔。
- 断言：`ZCE_ASSERT(X)`、`ZCE_ASSERT_TEXT(X, msg)`、`ZCE_ASSERT_RETURN(X, ret)`。
- `zce::Logger::setCallback(...)` 让上层接管输出（如转发到 ZVM）。
- `zce_loglevel __ll(level, __FILE__)` + `ZCE_CURRENT_LOGLEVEL(x)` 让单文件覆写日志级别。

---

## 3. 对象与智能指针 (`zce_object.h`)

```cpp
namespace zce {
class Object {
public:
    inline zce_int64 __get_oid() const noexcept;
    inline void __addref() const noexcept;
    inline void __decref() const noexcept;
    long __get_ref_count() const noexcept;
    std::shared_ptr<Object> shared_ptr() noexcept;
    template<typename T> std::shared_ptr<T> shared_from_this() noexcept;

    void __set_allocator(Allocator*) noexcept;
    void __set_release_delegator(TaskDelegator*);
};

template<typename T, typename LOCK = MutexNull>
class SmartPtr {
public:
    explicit SmartPtr(T* = 0);
    SmartPtr(const SmartPtr&); SmartPtr(SmartPtr&&) noexcept;
    SmartPtr& operator=(...);
    T* operator->() const; T& operator*() const; operator T*() const;
    T* get() const;
    template<class Y, class P> static SmartPtr __dynamic_cast(const SmartPtr<Y,P>&);
    template<class Y> static SmartPtr __dynamic_cast(Y* p);
};
}
```

辅助：`zce::ObjectPtr`（=`SmartPtr<Object>`）、`ObjectWrapper<T>`（把任意 POD 包成 Object）、`SmartPtrDecRef`（RAII 减引用）。

---

## 4. 数据块与内存池

`zce_dblock.h`：
- `class DataBlock`（`zce::Object`）：物理 buffer，可附带 `ObjectCounter` 与 `Allocator`。
- `class RefBlock`：值语义的 `DataBlock` 视图，支持 `prespace / length / space / capacity / preserv / rd_ptr / wr_ptr / merge / crunch / resize / copy`。
- `RefBlock(size_t size, zce_byte* buf, int wr_pos, int rd_pos = 0)`：把外部缓冲挂入零拷贝。
- 工具：`int zce::fromFile(RefBlock& mb, const char* path, unsigned extra)`。
- `template<typename T, unsigned S> class TempBlock`：栈/堆混合的小缓冲。

`zce_mbpool.h`：
- `zce::BlockPool`：进程级 `Singleton<BlockPool>`（=`BlockPoolSigt`）。`add_pool(size, count)` 注册定长池，`add_pool_v2(atomic_size, count)` 注册变长池；`acquire_dblock(len, obj)` 分配带统计的 `RefBlock`。
- `template<typename T> class ObjectPool`：定长 `T` 的对象池。
- 宏 `ZCE_MBACQUIRE(refblock_var, len)` 是首选分配方式。

`zce_allocator.h`：
- `Allocator::createChunk(size, n_chunks, lock)`、`createDynamic(size, n_chunks, lock)`。
- 接口：`alloc / zfree / realloc / getCapacity / getStat / getTotalSize / getAllocatorType`。

---

## 5. 同步原语 (`zce_sync.h`)

```cpp
zce::Mutex / MutexNull / MutexReadWrite / Semaphore
zce::Guard<L>            // RAII
zce::GuardRead<MRW>      // RAII 读锁
zce::GuardWrite<MRW>     // RAII 写锁
zce::Lock<T> / LockRead<T> / LockWrite<T>   // 把对象+锁打包，支持 tempUnlock/tempLockWrite
zce::ExecPermit          // 单写者执行许可证 (atomic<int> 0/1)
```

`zce_atomic.h`：
- `zce::AtomicLong { ++/--/value() }`，平台分发到 `InterlockedIncrement/__sync/OSAtomic`。
- `AtomicLongGuard guard(atomic)`：构造 ++、析构 --，配合"并发计数"。

`zce_tss.h`：
- `Tss::getGlobal()` 拿当前线程 `global_t`：`oid_/last_errcode_/log_cache_/current_delegator_/sem_vec_`。
- `Tss::zce_global_semaphore`：从池子借一个 `Semaphore`，析构归还（`zce::Task` 同步等待用）。
- `Tss::zce_env_task_delegator`：在当前线程切换 `current_delegator_`，析构恢复。

---

## 6. 调度

### 6.1 `Reactor` (`zce_reactor.h`)

```cpp
class Reactor : public TaskDelegator {
public:
    Reactor(const char* name = nullptr);
    int start(bool in_place = false);     // 创建独立线程或 in-place
    int startLoop();                      // in_place=true 时用户自驱动
    void stop();                          // uv_stop + join
    bool isStart() const;
    const std::string& name() const;
    unsigned long thread_id() const;
    void* loop_t() const;                 // 真实 uv_loop_t*

    int delegateTask(const TaskPtr&) override;
    int delegate_delay(const TaskPtr&, int ms);
    int delegateRelease(zce::Object*) override;
    void delegate_work();                 // 通常由 async_t 触发，无需手调

    int dns_resolve(const std::string& domain, const SmartPtr<DnsResolve>&);
    SmartPtr<Timer> scheduleTimer(SmartPtr<TaskQueue> q, int ms, bool repeat,
                                  std::function<void(Timer*)> cb);

    void* alloc(unsigned size); void zfree(void*);

    virtual int onReactorStart();       // 子类钩子（Service 用）
    virtual void onReactorStop();
};
typedef SmartPtr<Reactor> ReactorPtr;
typedef Singleton<Reactor, MutexNull> ReactorSigt;
```

### 6.2 `Scheduler` / `TaskQueue` / `Task` (`zce_task.h`, `zce_task_queue.h`)

```cpp
class Task : public Object {
public:
    Task(const char* name);
    virtual void call() = 0;
    const char* name() const;
};

class TaskDelegator : public Object {
public:
    virtual int delegateTask(const TaskPtr&) = 0;
    virtual int delegateRelease(Object*) = 0;
    template<typename F> int delegate(bool wait, const char* name, F&& f);
    template<typename F, typename... Args> auto _delegateFuture(...);
};

class Scheduler : public Object {
public:
    int active(int worker_count);
    void stop();
    int perform(const TaskPtr&, int idx = -1);   // idx 精准绑线程
    template<typename F> int performFunc(F&&, int idx = -1);
    template<typename F, typename... Args> auto performFuture(F&& f, Args&&... args)
        -> std::future<TaskResult<decltype(f(args...))>>;
    int printCurrentTasks();
    bool isActive() const;
    int getWorkerCount() const;
};
typedef Singleton<Scheduler> SchedulerSigt;

class TaskQueue : public Task, public TaskDelegator {
public:
    TaskQueue(const SchedulerPtr&, unsigned cont_proc = 10, const char* name = 0);
    int try_queue_length();
    void pause(); int resume();
    void attach(const TaskQueuePtr&);
};
```

`TaskResult<T>`：
```cpp
struct TaskResultBase { Status status; std::string error_message; bool is_ok() const; };
template<typename T> struct TaskResult : TaskResultBase { std::optional<T> value; };
template<> struct TaskResult<void> : TaskResultBase {};
```

### 6.3 `Thread` (`zce_thread.h`)

```cpp
class Thread : public Object {
public:
    enum THREAD_PRIORITY { PRIORITY_HIGHEST..PRIORITY_LOWEST };
    Thread(const char* name = nullptr);
    int startThread(bool in_place = false);
    void joinThread();
    int setThreadPriority(THREAD_PRIORITY);
    unsigned long getThreadId() const;
    const char* getName() const;

    virtual void onThreadStart() = 0;
    virtual void onThreadTerminate() = 0;
};
```

### 6.4 `Timer` (`zce_timer.h`)

```cpp
class Timer : public Object {
public:
    Timer(const SmartPtr<Reactor>&, const SmartPtr<TaskQueue>& sync_queue,
          unsigned msecond, bool repeat = true);
    int start(const SmartPtr<TimerDoozer>& doozer);
    int start(const std::function<void()>& cb, bool noaccumulate = false);
    void cancel();
    int getMilliSecondSpan() const;
};
class TimerDoozer : public Object {
public:
    TimerDoozer(bool noaccum = false);
    virtual bool will_trigger();
    virtual void handle_timeout() = 0;
};
```

---

## 7. IO / 协议栈 (`zce_handler.h`)

> 所有 stream 都基于 `IStream`，通过 `prev/next/link()` 串联。

```cpp
class IStream : public Object {
public:
    enum ERV_ISTREAM_WRITEOPT { /* 优先级与控制位 */ };
    void link(const SmartPtr<IStream>& next);
    virtual void on_open(bool passive, const zce_sockaddr_t& remote);
    virtual void on_read(RefBlock&, const Any&);
    virtual void on_close();
    virtual int  write(RefBlock&, ERV_ISTREAM_WRITEOPT = ERV_ISTREAM_DEFAULT);
    virtual void close();
};

class Socket : public IStream { /* 公共字段：remote_addr_/local_addr_/reactor_ */ };
class Tcp    : public Socket  { int connect(const char* ip, uint16); /* 自动 reactor 投递 */ };
class Udp    : public Socket  { int listen(...); int connect(...); int write(RefBlock&, const zce_sockaddr_t*, ...); };
class Pipe   : public Socket  { int open(int fd); int get_local_addr(char*, size_t*) const; };
class Tty    : public Socket  { int open(int fd); };
class Signal : public Object  { Signal(reactor, signum, std::function<void(int)>); int start(); void close(); };

class Connector : public Object {
    Connector(const SmartPtr<Tcp>&, const std::string& ip, uint16 port, uint16 timeout_sec = 0);
    int start_connect();
    virtual void on_connect(int status);
};
class Acceptor : public Object {
    Acceptor(const SmartPtr<Reactor>&, std::function<Tcp*()> make_handler);
    int listen(const char* ip, uint16, std::function<void(uint16)> on_listen = nullptr);
    void close();
    void block_remote(const zce_sockaddr_t&, unsigned end_t, const std::string& reason);
    void unblock_remote(const zce_sockaddr_t&);
};
class PipeConnector : public Object { PipeConnector(const SmartPtr<Pipe>&, std::string name); int start_connect(); };
class PipeAcceptor  : public Object { PipeAcceptor(const SmartPtr<Reactor>&, MakeHandlerFunc, bool ipc=false); int listen(const char* name); void close(); };

class DnsResolve : public Object {
    DnsResolve(const SmartPtr<Reactor>&, const char* domain);
    int start_resolve();
    virtual void on_resolved(int errcode, const zce_sockaddr_t&) = 0;
};

class SyncStream : public IStream {
    SyncStream(const SmartPtr<TaskQueue>&, const SmartPtr<Reactor>&);
    virtual int do_match_queue(SmartPtr<TaskQueue>&, const RefBlock&, const Any&);
};

class SocksStream : public IStream { SocksStream(realip, realport, user, pass); };
```

地址工具：`bool operator<(const zce_sockaddr_t&, const zce_sockaddr_t&)`、`bool operator<(const zce_addr_t&, const zce_addr_t&)`。

---

## 8. HTTP / WebSocket (`http_stream.h`)

```cpp
struct ZCE_HTTP_REQUEST  : ZCE_HTTP_HEADER { /* method/url/version + parse/pack */ };
struct ZCE_HTTP_RESPONSE : ZCE_HTTP_HEADER { /* result_code/result_string */ };

class HttpStream : public IStream {
    virtual void on_http_request(const SmartPtr<ZCE_HTTP_REQUEST>&, const RefBlock&);
    virtual void on_http_continue(RefBlock&) {};
    int write_ack(unsigned code, const zce_byte*, size_t, std::map<std::string, std::string>&);
    int write_continue(const zce_byte*, size_t);
};
class zce_http_client : public IStream {
    int request(const std::string& url, METHOD_E, zce_byte* buf, size_t,
                const std::map<std::string, std::string>& params = {});
    virtual void on_http_response(const ZCE_HTTP_RESPONSE&, const RefBlock&) = 0;
};
class WebSocketStream  : public HttpStream { WebSocketStream(int opcode = OPCODE_BIN); };
class zce_websocket_client : public IStream {
    zce_websocket_client(const std::string& host, const std::string& path = "/", int opcode = OPCODE_BIN);
};

std::string http_urlencode(const std::string&);
std::string http_urldecode(const std::string&);
int http_gzip(zce_byte*, size_t*, const zce_byte*, size_t, int level);
```

---

## 9. ZDP 协议层

### 9.1 `zdp_stream.h`

```cpp
namespace zce::zdp {

class zdp_stream : public IStream {
public:
    zdp_stream(const SmartPtr<Reactor>&, unsigned preserv = 0);
    virtual void on_packet(const zdp_head&, const RefBlock& body, const RefBlock& full, const Any& ctx);
    virtual void on_timeout(zdp_resctx*);

    int do_request(RefBlock& body, int mstimeout = 0, const Any& ctx = Any((zce_int64)0));
    int request(int msgmid, RefBlock body, int mstimeout = 0, const Any& ctx = Any((zce_int64)0));
    template<typename MSG> int request(const MSG&, int mstimeout = 0, const Any& ctx = ..., ERV_ZCE_COMPRESS = ZCE_COMPRESS_NONE);
    template<typename MSG> int response(const MSG&, unsigned seq, zce_byte rev = 0, ERV_ZCE_COMPRESS = ZCE_COMPRESS_NONE);
    template<typename T, typename... A> int requestArgs(int msgmid, int mstimeout, const Any& ctx,
                                                        ERV_ZCE_COMPRESS, int preserv, const T&, A&&...);
    template<typename T, typename... A> int responseArgs(int msgmid, unsigned seq, zce_byte rev,
                                                         ERV_ZCE_COMPRESS, const T&, A&&...);
};

int zdp_serialize_dblock(RefBlock&, uint16 msgmid, uint32 seq, ERV_ZCE_COMPRESS,
                         uint32 bodylen, int preserv, int rev = 0);
template<typename T> int zdp_serialize_struct(RefBlock&, const T& msg, zce_byte rev, int preserv = 0);
template<typename T> int zdp_serialize(RefBlock&, uint32 seq, const T& msg, zce_byte rev,
                                       ERV_ZCE_COMPRESS = ZCE_COMPRESS_NONE, int preserv = 0);
}
```

### 9.2 `zdp_base_proto.h` 内置消息（zGen 生成）

```
err_t / zdp_addr_t / zdp_container_t / nspair_t / nipair_t / nllpair_t /
logtext_t / zobject_proxy_t / zvm_t / zvm_host_t

MSG_NONE_REQ          E_MSG_NONE_REQ        // 版本协商
MSG_DISCONN_REQ       E_MSG_DISCONN_REQ     // 主动断开
MSG_CONTAINER_REQ/RES E_MSG_CONTAINER_*     // 通用容器，子命令 + payload
MSG_RPCCALL_REQ/RES   E_MSG_RPCCALL_*       // RPC 调用
```

### 9.3 ZDS (`zds_schema.h`)

> 主要由 zGen 生成代码使用，业务也可以直接调用。

```cpp
namespace zce::zdp {
template<typename T> int zds_pack(zce_byte* buf, int size, const T&, zds_context_t*, bool);
template<typename T> int zds_unpack(T&, const zce_byte* buf, int size, zds_context_t*, bool);
template<typename T> int zds_pack_builtin(...); int zds_unpack_builtin(...);
template<typename T> int zds_pack_array(...);   int zds_unpack_array(...);
template<typename T, typename... A> int zds_pack_multi(...); int zds_unpack_multi(...);
template<typename T> constexpr bool is_builtin_type();
template<typename T> constexpr bool is_vector();
}
```

### 9.4 BSON (`zce_bson.h`)

提供 `zce::zdp::Bson*` 系列，支持与 ZDS 之间互转，便于和 MongoDB 等存储桥接（细节直接看头文件）。

---

## 10. RPC / 虚拟机宿主 (`zvm.h`, `zdp_storm.h`)

### 10.1 `VirtualMachineStub`

```cpp
namespace zce::zvm {
class VirtualMachineStub : public Object {
public:
    int initStub(const SchedulerPtr&, const ReactorPtr&, const std::string& host_dir);
    int listen(const char* host, uint16);
    int listenPipe(const char* pipe_name);
    int listenSchema(const char* schema);   // tcp:// 或 pipe://
    void stopAllServants();

    SmartPtr<Object> boot(const zdp_base::zvm_t&, RefBlock args);
    SmartPtr<Object> boot(const std::string& svc_name, const std::string& host, uint16 port,
                          bool ssl, int default_timeout,
                          std::function<void()> open_cb, std::function<void()> close_cb);
    SmartPtr<Object> get_vm(const std::string& svc_name) const;
    void destroy(const SmartPtr<Object>& vm);

    int rpc_call_dblock(const SmartPtr<Object>& vm, zce_int64 objid,
                        const std::string& method, RefBlock&& dblock,
                        int mstimeout, const response_cb& response);
    template<typename T> int rpc_call_builtin/_msg/...(...);

    const ReactorPtr& getReactorPtr() const noexcept;
    const SchedulerPtr& getSchedulerPtr() const noexcept;
    const std::string& hostDir() const noexcept;
    std::string vmHomeDir(const zdp_base::zvm_t&) const noexcept;
};
typedef Singleton<VirtualMachineStub> VirtualMachineStubSigt;
}
```

### 10.2 `Machine`（VM 基类）

```cpp
class Machine : public TaskQueue {
public:
    Machine(const std::string& vm_name, const SmartPtr<VirtualMachineStub>&);
    const std::string& vm_name() const noexcept;
    const std::string& full_name() const noexcept;
    const SmartPtr<VirtualMachineStub>& stub_ptr() const noexcept;
    SmartPtr<Machine> get_vm(const std::string&) const;
    const SmartPtr<Reactor> reactor_ptr() const noexcept;

    SmartPtr<RpcServant> rpc_serve(const char* host, uint16 port, bool ssl,
                                   const char* cert, const char* key,
                                   const char* method_prefix = "");

    virtual int  start() = 0;
    virtual void stop()  = 0;
    virtual int  call_dblock(zce_int64 objid, const std::string& method, RefBlock& dblock,
                             int mstimeout, const VirtualMachineStub::response_cb&) = 0;
    virtual int  call_dblock_from_remote(zce_int64, const std::string&, RefBlock&,
                                         const SmartPtr<RpcStream>&,
                                         const VirtualMachineStub::response_cb&);

    template<typename... Args>
    int sendResponse(const VirtualMachineStub::response_cb&, Args&&... args) const;
};
```

### 10.3 客户端代理 / 异步调用

```cpp
class VirtualMachineProxy : public Object {
protected:
    virtual int doCallTwoWay(const char* func, const RefBlock& input, int mstimeout,
                             std::function<void(int, const RefBlock&)> cb) = 0;
public:
    template<typename... Results, typename... Args, typename F>
    int callTwoWayAsync(const char* func, int mstimeout, F&& cb, Args&&... args);

    template<typename... RESULTs>
    struct RpcResult { int errcode; std::string errdesc; std::tuple<RESULTs...> data; ... };
};
```

### 10.4 注册新 VM 类型

```cpp
class VirtualMachineRegister {
public:
    using lpfn_zvm_creator =
        std::function<SmartPtr<Machine>(const zdp_base::zvm_t&,
                                        const SmartPtr<VirtualMachineStub>&,
                                        RefBlock&)>;
    VirtualMachineRegister(const std::string& vmtype, lpfn_zvm_creator);
};
// 静态对象方式：
static VirtualMachineRegister _myvm("myvm", [](...) { return new MyMachine(...); });
```

### 10.5 `zdp_storm.h`（发布订阅总线）

```cpp
namespace zce::zdp {

class Storm : public Object {            // 服务端 / shard
public:
    Storm(const ReactorPtr&, const SchedulerPtr&, uint16 shard_id, const Any& ctx,
          publish_callback child_cb, set_callback set_cb);
    int listen(const char* ip, uint16 port);
    int stop();
};

class StormClient : public Object {       // 订阅端
public:
    StormClient(const ReactorPtr&, const std::string& ident, const std::string& token,
                const Any& ctx, publish_callback father_cb, set_callback set_cb,
                std::function<void()> on_open, std::function<void()> on_close);
    int connect(const char* ip, uint16 port);
    int subscribe(const std::string& topic);
    int unsubscribe(zce_int64 topic_id);
    zce_int64 getTopicId(const std::string& topic) const;
    int publish(zce_int64 topic, const zce_byte* data, size_t len, zce_int32 trace);
    template<typename T, typename TTOPIC>
    int publish(TTOPIC topic, const T& msg, const zdp_storm_peer& = {}, int seq = 0, zce_int64 trace = 0);
    template<typename... Args> int publishMessage(zce_int64 topic, Args&&... args);
    int set(zce_int64 topic, const std::string& name, ...);
};

class StormStreamAdapter : public IStream { /* 把任意 IStream 桥接到 storm topic */ };
class StormVM            : public zvm::Machine { /* 对 VM 体系暴露的 storm 实体 */ };
}
```

### 10.6 子进程框架 (`zce_process.h`)

```cpp
class Process : public zdp::zdp_stream {
    struct ProcessInfo : zdp_base::zvm_t { /* exepath, pid, starttime, dblock, autoadd, ... */ };
    Process(SubProcessHost*, ProcessInfo, bool debug = false, ExitCallback = nullptr);
    int startProcess(); int kill(int sig = 0); int upsert();
    int pid() const; bool isRunning() const;
    void setContextPtr(...); ProcessInfo& processInfo();
    static bool isProcessExists(unsigned long pid, const std::string& name);
};

class SubProcessHost : public zvm::Machine {
    struct HostContext { metadb_path, table_name, debug_mode, *_cb, vmname, vmaddr, vmport,
                         stormport, host_dir, host_topic; };
    SubProcessHost(stub, reactor, HostContext);
    int addAutoCreateProcess(const zdp_base::zvm_t&);
    SmartPtr<Process> createSubProcess(zdp_base::zvm_t, bool debug, RefBlock content);
    int invoke(const SmartPtr<Process>&);
    int stopSubProcess(const std::string& name);
    int querySubProcess(const std::string&, SmartPtr<Process>&);
    const std::map<std::string, SmartPtr<Process>>& queryAllSubProcess() const;
    void checkDelayedStart();
    int start() override; void stop() override;
};

class SubProcess : public Object {     // 子进程侧代理
    SubProcess(const SmartPtr<Reactor>&);
    int connectProcess(const std::string& pipe_id, SmartPtr<IStream>);
    int connectProcess(const std::string& pipe_id, ConnectCallback, DisconnectCallback, DataCallback);
    void close();
    SmartPtr<IStream> getStreamPtr();
};
```

---

## 11. 应用框架 `zce::Service` (`zce_service.h`)

```cpp
struct AppOptions : zdp_base::zvm_t {
    std::string mode;        // daemon / work / service / console
    std::string pidfile;
    std::string logsuffix;
    std::string configpath;
    std::string help_target;
#ifdef _WIN32
    std::string service_action;     // install/remove/start/stop/restart/status
    std::string service_name;       // 名字
    std::string service_exec_path;
    std::string service_display;
#endif
};

class Service : public Reactor {
public:
    Service(const char* name);
    static Service* instance();

    int main(int& argc, const char* argv[]);     // 解析子命令并启动相应模式
    int runWorkerProcess();
    bool isDaemonProcess() const;
    bool isWorkProcess() const;
    AppOptions& options();
    void updateVMStatus(const zdp_base::zvm_t&);
    virtual bool shutdownDaemonAndWorker();      // 把 daemon/worker 都停掉

protected:
    // —— 必须重写之一/全部 ——
    virtual int  onReactorStart() override;     // 1s 心跳 + 信号 + (daemon|worker)分流
    virtual void onReactorStop() override;
    virtual void onTimer();
    virtual void onStdinCommand(std::string line);

    virtual bool onDaemonStart();                // 已默认注册 vmhost/storm vm，返回 true
    virtual void onDaemonStop();
    virtual bool onWorkerStart();
    virtual bool onWorkerStop() = 0;             // 用户必须实现
    virtual void onSignal(int);
};
```

---

## 12. 数据库 (`zdb_rdb.h`, `zdb_redis.h`)

### 12.1 关系型抽象

```cpp
namespace zce::zdb {
class Database : public Object {
public:
    enum ERV_DATABASE { UNKNOW, SQLITE, MYSQL, PGSQL, LIMIT };
    Database(ERV_DATABASE, const zce_astring& connection_str);
    SmartPtr<Connection> getConnection();
    ERV_DATABASE database_type() const;
};

class Connection : public Object {
public:
    virtual bool connetion_ok() = 0;
    virtual void close() = 0;
    virtual void begin() = 0; virtual void commit() = 0; virtual void rollback() = 0;
    virtual int  create_stmt(SmartPtr<Statement>&, const char* sql, bool multi) = 0;
    virtual int  backup(const char*, const char*) { return -1; }

    int execute(SmartPtr<Statement>&, const char* sql, const std::vector<std::string>& vecargs);
    int execute_multi(SmartPtr<Statement>&, const char* sql);
    template<typename OUT> int execute_multi(const char* sql, OUT&);
    template<typename IN, typename OUT> int execute(const char* sql, OUT&, const IN&);
    template<typename IN, typename OUT> int execute(const char* sql, std::vector<OUT>&, const IN&);
};

class Statement : public Object {
    Statement& operator<<(int|short|double|zce_int64|std::string|timespec|...);
    Statement& operator>>(int|short|double|zce_int64|std::string|timespec|...);
    int operator<<(const _endl_t&);                // = go()
    int operator>>(const _endl_t&);                // = end_row(): >0 还有行, =0 完, <0 错
    int  init(); int reset(); int go(); int end_row();
    int  lasterr_code() const; int lasterr_column() const;
    field_type_e get_next_filed_type();
    int  get_column(); int get_rows_effected(); const char* get_column_name(int);
};

template<typename TKEY, typename T>
struct DatabaseObject {
    static int select_all(...); static int select_all_vec(...); static int select_all_ptr(...);
    static int select_byprop(...); static int select_byprop_base(...);
    static int select_bykey(...); static int insert(...); static int replace(...);
    static int update(...); static int remove(...); static int execute(...);
};

template<typename record, bool transaction = true>
class zdb_table : public Object {
    zdb_table(const std::string& name);
    int create/drop/query/execute/insert/update/remove(...);
    int query(Connection_ptr&, record&, record::zdb_query_e, bool transaction = true);
};
}
```

### 12.2 Redis (`zdb_redis.h`)

```cpp
class RedisDatabase : public Object {
    RedisDatabase(bool ssl, const std::string& ip, uint16 port, const char* passwd);
    SmartPtr<RedisConnection> getConnection();
};
class RedisConnection : public Object {
    bool connetion_ok() const; void close();

    bool key_exists(const std::string&);
    int  set/get/del/inc/expire/...                    // KV
    int  hget/hset/hdel/hgetall/hinc                   // Hash
    int  zset/zinc/zdel/zrange                         // ZSet
    int  llen/lpush/rpush/lpop                         // List
};
struct ZdbRedis { /* RAII redisReply* 包装 */ };
int zdb_redis_toval(...);
```

---

## 13. 文件 / 字符串 / 加解密

`zce_filesystem.h`：
```cpp
handle_t zce_open(const char*, int mode, uint16 perms, LPSECURITY_ATTRIBUTES);
ssize_t  zce_read/write/writev(...);
int      zce_close(handle_t);
zce_int64 zce_llseek(handle_t, zce_int64, int);
int      zce_ftruncate(handle_t, zce_int64);
namespace zce {
    int statFile(const char*, struct stat*);
    std::string getModulePath(); std::string matchModulePath(const char*);
    void chdirToModulePath();
    std::string getAbsolutePath(const char*);
    int addToPath(const char*);
    bool makeDir(const char*);
    bool isFilePathExists(const char*);
    const char* getFileName(const char*);
    zce_int64 getFileSize(const char*);
    bool writeFile(const char*, const void*, size_t);
    class File : Object { /* open/read/write/writev/lseek_block/lseek/ftruncate/size/close */ };
}
```

`zce_string.h`：`zce::replace`、`zce::hash`、`zce::to_string<T>`、`split`、`start_with`、`zce::string_view`（C++17 之前回退到 boost）。

`zce_random.h`、`zce_guid.h`、`zce_rsa.h`、`zce_ssl.h`：随机数、UUID/Guid15、RSA、OpenSSL 包装。

`zce_convertor.h`：基础类型 / 容器 / Any 的相互转换辅助（`std::optional`, `zce::Any`, base64/hex 等）。

`zce_filter.h`：通用滤波器接口（zce_filter）。

`zce_ctrlc_handler.h`：Ctrl-C / signal 与异常处理。

`zce_translator.h`：i18n 字典查询（实现为空，仅头）。

---

## 14. Lua / Python / C VM 子模块

> 这些 API 主要在 `libsrc/libzce/zvm/<lang>/` 下，对外通常只通过 `Machine` 注册的方式使用，下面列出主要类与脚本侧入口。

### 14.1 Lua (`zvm/zua/`)

- `class ZuaMachine : public zvm::Machine` 实现 Lua VM。`start()` 创建 lua_State、加载 startup 脚本。
- `class ZuaThread`：Lua 协程（lua_State+top）。
- `class ZuaStackBalanceChecker`：调试用栈平衡断言。
- `class CoTaskCallee / CoTaskCaller`（`zua_cotask_*.h`）：协程 RPC 协议。
- `zua_register openlibs`：在静态对象阶段注册自定义 `lua_openlibs`。
- 详见 `ZuaAPI.md`、`ZuaAPI_en.md` 中导出的 Lua 全局 API。

### 14.2 Python (`zvm/zpy/`)

- `class ZpyMachine : public zvm::Machine`：使用 pybind11 子解释器实现多 VM 隔离。
- `static int initPythonEmbedded(const char* relative_path)`、`static void finiPythonEmbedded()` 控制全局解释器。
- `static SmartPtr<ZpyMachine> from_interpreter()`、`main_interpreter()`。
- `bool zpy_try_extract_object_ptr(PyObject*, SmartPtr<Object>&, PyObjectBindingKind*)`：从 Python 对象提取 zce::Object。
- `zce_pybind11.h` 提供：`type_caster<zce::Any>`（dict/list/scalar 互转）、`toNumpyArray/toNumpyArrayCopy/fromNumpyArray`。
- `zce.pyi` 提供 Python 侧 stub。

### 14.3 C VM (`zvm/zcc/`)

- `class FileSystemMachine`（`zcc_vms.h`/`.cpp`）：示例性 C 风格 VM，可作为最小化 Machine 模板。

### 14.4 JS（默认未编入）

- `zvm/zjs/` 提供基于 quickjs-ng 的实现框架（`zvm_js.cpp` 等），目前 CMakeLists 注释掉。

---

## 15. MCP 服务 (`zce_mcp.h`)

```cpp
class McpStream : public HttpStream {
    int sendJsonRpc(const json&);
    int sendJsonRpcResult(const json& id, const json& result);
    int sendJsonRpcError(const json& id, int code, const std::string& msg, const json& data = nullptr);
    bool isInitialized() const; void markInitialized();
    const std::string& negotiatedProtocolVersion() const;
};

class McpHost : public Object {
    enum class Protocol { HTTP, HTTPS, WEBSOCKET, WEBSOCKETS };
    int bind(const SmartPtr<Reactor>&, const std::string& addr, int port);
    int handleJsonRpc(const SmartPtr<McpStream>&, const json&);
protected:
    virtual json serverInfo() const;
    virtual json serverCapabilities() const;
    virtual int onInitialize(...);
    virtual int onToolsList(...) = 0;     // 必须实现
    virtual int onToolsCall(...) = 0;
    virtual int onResourcesList(...) = 0;
    virtual int onResourcesRead(...) = 0;
};
```

---

## 16. 其他实用头

| 头文件 | 主要内容 |
| ------ | -------- |
| `zce_array.h` / `zce_list.h` / `zce_hash.h` / `zce_safemap.h` | 自研侵入式容器，兼顾分配器 / 线程安全 / 排序需求 |
| `zce_ring.h` | 环形缓冲 |
| `zce_bytes.h` / `zce_bits.h` | 位操作 / 字节序工具 |
| `zce_matrix.h` / `zce_matrix_extra.h` / `zce_mat`（cpp） | 数值矩阵 |
| `zce_object_counter.h` | 对象监控（按类型计数，配合宏 `ZCE_OBJECT_*`） |
| `zce_sysperf.h` | 系统级性能采样 |
| `zce_service.h` | 上层应用框架（见第 11 节） |
| `ptp_*.h` | PTP（点对点）协议、节点、传输层 |
| `rtmp_stream.h` / `rtp_stream.h` / `rtp.h` / `whp_stream.h` | 流媒体 |
| `webs.h` / `wsse.h` | WebService 与签名 |
| `usys_transceiver_udp.h` | 业务层 UDP 收发 |
| `zwt.h` / `zwt_tron.cpp` / `secp256k1` | 链上工具与椭圆曲线签名 |
| `zxml_parser.h` / `zxml_node_*.h` / `zxml_convertor.h` | XML 解析 / 序列化 / 转换 |

---

## 17. 单例总结

| 单例 | 作用 |
| ---- | ---- |
| `zce::ReactorSigt` (= `Singleton<Reactor, MutexNull>`) | 进程默认 Reactor。`Service` 派生时自动 `setInstance(this)` |
| `zce::SchedulerSigt` | 默认 Scheduler，需要 `active(N)` 才生效 |
| `zce::BlockPoolSigt` | 内存池。需要先 `add_pool` / `add_pool_v2` |
| `zce::zvm::VirtualMachineStubSigt` | VM 注册中心，需先 `initStub(...)` |
| `zvm_creator` (内部 `Singleton`) | vmtype → 工厂注册表，由 `VirtualMachineRegister` 维护 |
| `zce::Service::instance()` | 当前应用 Service（assert 单例） |

---

## 18. 例：最小服务骨架

```cpp
#include "zce/zce_api.h"
#include "zce/zce_service.h"
#include "zce/zce_log.h"

class MyService : public zce::Service {
public:
    MyService() : Service("MyApp") {}

protected:
    bool onWorkerStart() override {
        // 启动 RPC 监听
        auto& stub = *zce::zvm::VirtualMachineStubSigt::instance();
        stub.initStub(zce::SchedulerPtr(zce::SchedulerSigt::instance()),
                      zce::ReactorPtr(this), "./host");
        zce::SchedulerSigt::instance()->active(4);
        stub.listen("0.0.0.0", 12345);
        ZINFOR("worker started");
        return true;
    }
    bool onWorkerStop() override { ZINFOR("worker stopping"); return true; }
};

int main(int argc, const char* argv[]) {
    zce_init();
    int ret = -1;
    {
        MyService svc;
        ret = svc.main(argc, argv);
    }
    zce_fini();
    return ret;
}
```

更多用法请参考 `cxxproj/CLAUDE.md` 中的 “libzce Library Usage” 与 `LIBZCE.md`。
