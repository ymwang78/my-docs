# LogCollectorVM 设计文档

## 1. 背景和目标

HostVM 需要在守护进程中提供一个基于 UDP 的日志收集能力。这个能力属于 HostVM 的基础设施，不应该实现成挂在 `HostVMService` 外侧的独立组件，而应该实现为一种 HostVM VM。

目标：

- `LogCollectorVM` 作为 HostVM 内建 VM 运行在 daemon 进程里。
- VM 自带 `Reactor` 负责 UDP 数据收集。
- UDP 接收线程只做轻量解析和入队，不做阻塞落盘。
- VM 启动专门的 `Scheduler` 和按文件前缀分片的多个 `TaskQueue` 执行落盘。
- 文件名前缀由“来源 IP + 应用名”统一生成。
- 不同 `appname`（更准确地说，不同 `source_prefix`）写到不同日志文件；线程池用于分散这些不同文件的写入。
- UDP 协议头尽量小，固定头只占 2 字节。

v1 暂不做：

- ACK、重传、可靠传输。
- 鉴权、加密、跨公网安全传输。
- 产品业务语义解析。
- 修改模块公开 API。

## 2. HostVM 框架定位

`LogCollectorVM` 按 HostVM VM 模型实现。注意 `zce::zvm::Machine` 本身即继承自 `zce::TaskQueue`（见 `include/zce/zvm.h`）；`zce::Reactor` 是事件循环，UDP socket 是绑定到 reactor 的 `zce::Udp`，**不能通过继承 `Reactor` 来“拥有 socket”**。

```text
HostVM daemon (master 进程)
  -> VirtualMachineStubSigt::initStub(scheduler, reactor, host_dir)
  -> zlogcollector_init()        // 触发静态注册，防链接器优化
  -> boot vmtype="logcollector", vmname="logcollector"
       -> LogCollectorMachine : zce::zvm::Machine (= zce::TaskQueue)
            -> LogUdpReceiver : zce::Udp
                 -> 绑定到 reactor（共享 stub reactor 或独立 zce::Reactor 实例）
                 -> on_read_data() 解析后投递落盘 dispatcher
            -> LogDiskDispatcher
                 -> 跑在专用 zce::Scheduler 上
                 -> hash(source_prefix) 路由到 LogDiskShardQueue[N]
            -> LogDiskShardQueue[N] : zce::TaskQueue
                 -> 文件落盘（仅在这些分片队列发生文件 IO）
```

关键点：

- 使用 `VirtualMachineRegister("logcollector", ...)` 注册 VM 工厂。
- `LogCollectorMachine` 必须实现 `Machine` 的纯虚接口：`start()`、`stop()`、`call_dblock()`（v1 无 RPC，`call_dblock` 返回未实现错误码）。
- `LogCollectorMachine::start()` 创建并 `listen()` UDP 接收器，启动专用落盘 scheduler 和多个落盘分片队列。
- `LogCollectorMachine::stop()` 先关闭 UDP 接收，再 flush 全部落盘分片队列，最后 stop 专用 scheduler。
- `HostVMService` 新增成员保存 boot 返回的 VM 对象，daemon 退出时经 `VirtualMachineStub::destroy()` 显式销毁（destroy 内部触发 `Machine::stop()`）。

## 3. UDP 协议 v1

固定头 2 字节：

```cpp
// byte 0: flag
// bit 7..6: version   0..3，v1 使用 1
// bit 5..3: level     对应 zce 的 8 个 ZLOG_LEVEL
// bit 2..1: compress  0 none, 1 zlib, 2 bz2, 3 reserved
// bit 0:    type      0 log content, 1 interactive command

// byte 1: ext
// bit 7..4: app_len   应用名长度，0..15 字节
// bit 3..0: reserved  发送端置 0
```

包结构：

```text
+--------+------+----------------+------------------+
| flag   | ext  | app[app_len]   | content[...]     |
| 1 byte |1 byte| 0..15 bytes    | remaining bytes  |
+--------+------+----------------+------------------+
```

解析规则：

- `version` 必须是 `1`。
- `level` 是 3 bit 日志级别，对应 zce 的 8 个 `ZLOG_LEVEL`。
- `type=0` 表示普通日志内容。
- `type=1` 保留给交互 Command，v1 暂不处理。
- `compress=0` 表示 `content` 是原始 UTF-8/字节内容。
- `compress=1/2` 预留给 zlib/bz2，只压缩 `content`，不压缩 header 和 app。
- `app_len` 是应用名字节数，不带 `\0`。
- `app_len=0` 允许接收，但归一化为 `unknown`。
- `content` 是 app 后面的全部剩余字节。
- `ext` 的 bit3..0 reserved：接收端必须忽略，**不得**因 reserved 非 0 而丢包（前向兼容）。
- 推荐 UDP 包大小不超过 1400 字节；接收端默认硬上限 2048 字节。

> 说明：CLAUDE.md 要求网络结构体走 ZDL `.ptl` + zgen。本协议头**故意不使用 ZDS**——ZDS 帧/字段开销会破坏“固定头仅 2 字节”的目标，因此采用手写 mask/shift 位域。配置结构（见 §6）仍走 `.ptl`。

建议 level 映射：

```text
0 -> ZLOG_TRACE
1 -> ZLOG_DEBUG
2 -> ZLOG_INFOR
3 -> ZLOG_WARNI
4 -> ZLOG_ERROR
5 -> ZLOG_FATAL
6 -> ZLOG_BIZDT
7 -> ZLOG_NONEL
```

推荐用 mask/shift，不使用 C++ bitfield：

```cpp
constexpr uint8_t kVersionMask = 0xC0;
constexpr uint8_t kLevelMask = 0x38;
constexpr uint8_t kCompressMask = 0x06;
constexpr uint8_t kTypeMask = 0x01;
constexpr uint8_t kAppLenMask = 0xF0;

inline uint8_t getVersion(uint8_t flag) { return (flag >> 6) & 0x03; }
inline uint8_t getLevel(uint8_t flag) { return (flag >> 3) & 0x07; }
inline uint8_t getCompress(uint8_t flag) { return (flag >> 1) & 0x03; }
inline uint8_t getType(uint8_t flag) { return flag & 0x01; }
inline uint8_t getAppLen(uint8_t ext) { return (ext >> 4) & 0x0F; }

inline uint8_t makeFlag(uint8_t version, uint8_t level, uint8_t compress, uint8_t type) {
    return static_cast<uint8_t>(((version & 0x03) << 6) |
                                ((level & 0x07) << 3) |
                                ((compress & 0x03) << 1) |
                                (type & 0x01));
}

inline uint8_t makeExt(uint8_t app_len) {
    return static_cast<uint8_t>((app_len & 0x0F) << 4);
}
```

## 4. 文件名前缀

日志文件的来源标识由来源 IP 和应用名组成：

```text
source_prefix = remote_ip_if_not_localhost + app_name
```

规则：

- 来源是 localhost 时，IP 为空。
- localhost 判定保持简单确定：源 IP 属于 `127.0.0.0/8` 或等于 `::1` 即视为 localhost。**不**枚举本机全部网卡地址（昂贵且有竞态）。
- 来源不是 localhost 时，前缀加 `<ip>-`。
- app 名只保留 `[A-Za-z0-9_.-]`，其他字符替换为 `_`。
- 文件名加固（app 来自不可信网络输入）：清洗后若结果为空、为 `.`、为 `..`、或以 `.` / `-` 开头，归一化为 `unknown`，防止路径注入。
- 空 app 或清洗后为空时使用 `unknown`。

示例：

```text
tjmpc-2026-05-17.001.log
192.168.1.10-tjmpc-2026-05-17.001.log
10.0.0.8-hostvm-2026-05-17.002.log
```

滚动策略：

- 文件名包含完整日期：`yyyy-MM-dd`。
- 每个 `source_prefix + date` 独立编号，从 `.001` 开始。
- 超过配置的最大文件大小后递增序号。
- `keepdays` 控制历史收集日志清理。

## 5. 主要类设计

### 5.1 LogCollectorMachine

继承 `zce::zvm::Machine`（即 `zce::TaskQueue`），由 HostVM VM map 持有。

职责：

- 读取 `logcollector_info` 配置。
- 创建 / 绑定 / 关闭 `LogUdpReceiver`。
- 启停专用落盘 `Scheduler`。
- 持有 `LogDiskDispatcher` 和 `LogDiskShardQueue[N]`。
- 汇总统计信息，供 `printServiceStatus()` 输出。
- 后续可扩展 RPC 方法，例如 `GetLogCollectorStatus`。

必须实现的 `Machine` 纯虚接口：

- `int start() override;`
- `void stop() override;`
- `int call_dblock(zce_int64, const std::string&, zce::RefBlock&, int, const VirtualMachineStub::response_cb&) override;`（v1 无 RPC，直接回未实现错误码）

建议成员：

```cpp
zce::SmartPtr<zce::Reactor>   udp_reactor_;   // 共享 stub reactor 或独立实例
zce::SmartPtr<LogUdpReceiver> receiver_;      // zce::Udp 派生
zce::SmartPtr<zce::Scheduler> disk_scheduler_;
std::vector<zce::SmartPtr<LogDiskShardQueue>> disk_queues_;   // 必须声明在 dispatcher 之前
LogDiskDispatcher             disk_dispatcher_;               // 析构早于 disk_queues_，构造时引用已就绪队列
LogCollectorConfig            config_;
LogCollectorStats             stats_;
```

### 5.2 UDP 接收（reactor 绑定关系）

zce 模型：`zce::Udp : public Socket`，构造时**传入**一个 `zce::Reactor`（见 `include/zce/zce_handler.h`）。**不**通过继承 `zce::Reactor` 来拥有 socket，因此**不存在 `LogCollectorReactor` 这个类**。接收逻辑放在 `LogUdpReceiver`（见 §5.3），由某个 reactor 驱动：

- reactor 选择：优先复用 `Machine::reactor_ptr()` / stub 的共享 reactor；若需隔离收集流量，可 `new zce::Reactor` 一个独立实例并 `start()`。
- 在配置的 `bind_addr:bind_port` 上 `listen()`。
- 接收 datagram，解析 2 字节协议头、app、content。
- 归一化来源 IP 和 app 名。
- 丢弃非法 version/type/compress/长度。
- 把合法 `LogRecord` 投递到 `LogDiskDispatcher`。
- 接收路径不做文件 IO。

### 5.3 LogUdpReceiver

建议继承 `zce::Udp`，覆盖 `on_read_data`：

```cpp
class LogUdpReceiver : public zce::Udp {
  public:
    void on_read_data(zce_byte* buf, zce_uint32 len, const zce_sockaddr_t* addr) override;
};
```

`on_read_data` 只做轻量解析后调用 `LogCollectorMachine::handlePacket(...)`（解析 + 归一化 + 投递落盘 dispatcher），实际文件 IO 在 `LogDiskShardQueue` 异步完成。`LogUdpReceiver` 构造需传入所选 reactor。`handlePacket` 运行在 UDP reactor 线程，除原子统计和线程安全的 dispatcher 入队外，不直接修改需要 VM `TaskQueue` 串行保护的状态。

### 5.4 LogDiskDispatcher 和 LogDiskShardQueue

落盘层分为两部分：

- `LogDiskDispatcher`：轻量路由器，不做文件 IO；按 `source_prefix` 计算分片，把 `LogRecord` 投递到对应 `LogDiskShardQueue`。
- `LogDiskShardQueue`：继承 `zce::TaskQueue`，运行在专用 `zce::Scheduler` 上，真正执行文件 IO。

职责：

- 批量写入日志。
- 按 `source_prefix` 缓存打开的文件句柄（**shard-local**，见下）；不同 `source_prefix` 一定对应不同文件名。
- 按日期和大小滚动文件。
- 定时 flush / 关闭空闲句柄 / 清理过期文件。
- 清理超过 `keepdays` 的文件。

状态归属（关键）：

- 句柄缓存（`map<source_prefix, FILE*>`）、当前文件大小、滚动序号计数等全部为 **shard-local 成员**，每个 `LogDiskShardQueue` 各持一份，**无共享、无锁**。
- 这是分片并行成立的前提：同一 `source_prefix` 恒定路由同一 shard，天然无需跨线程同步；若改成跨分片共享一张句柄表则必须加锁，会抵消分片收益并在滚动/关闭时引入数据竞争——明确禁止。
- 文件名只由 `source_prefix`（+日期+序号）决定，与 shard 索引无关；因此 `disk_threads` 变更或重启不会改变某个 source 的目标文件，只改变由哪个线程写它。

并发与顺序：

- **同一个 `source_prefix` 固定路由到同一个 `LogDiskShardQueue`**，因此同一个 app/source 对应的文件写入顺序由该 `TaskQueue` 的串行化保证。
- **不同 `source_prefix` 对应不同文件**，可被 hash 到不同 `LogDiskShardQueue`，由 `disk_scheduler_` 的线程池并行落盘；这正是 `disk_threads` 的作用。
- `disk_threads` 同时决定 scheduler 工作线程数和分片队列数，取值至少为 1。建议 v1 默认 2 或 4；单机日志量低时可配置为 1。
- 一个分片队列内部仍然串行执行。若多个热点 app hash 到同一分片，会共享该分片的顺序队列；后续可在保持“单 `source_prefix` 单 writer”的前提下增加一致性 hash 或动态迁移。
- 定时 flush / 清理用 `zce::Reactor::scheduleTimer(task_queue, msec, repeat, fn)` 或 `zce::Timer`，**禁止 sleep 循环**（遵循 CLAUDE.md / LIBZCE 约定）。

路由伪代码（`TaskQueue` 无 `submit`，用真实 API `delegate`）：

```cpp
size_t shard = stableHash(record.source_prefix) % disk_queues_.size();
// record 移动进闭包，避免接收线程持有；非阻塞 fire-and-forget
disk_queues_[shard]->delegate(false, "logdisk",
    [q = disk_queues_[shard].get(), rec = std::move(record)]() mutable {
        q->writeRecord(std::move(rec));
    });
```

构造/销毁顺序：`start()` 中**先填充 `disk_queues_`，再装配 `disk_dispatcher_`**（使其引用已就绪的队列）；析构时 dispatcher 必须早于 `disk_queues_` 释放——成员声明顺序已保证（queues 在前、dispatcher 在后 → dispatcher 先析构）。

## 6. 配置设计

建议在 `hostvm_config.ptl` 中增加：

```ptl
struct logcollector_info
{
    [_default_val, 0] byte enable;
    [_default_val, "127.0.0.1"] astring bind_addr;
    [_default_val, 22502] uint16 bind_port;
    [_default_val, "log/collect"] astring log_path;
    [_default_val, 2048] uint16 max_datagram;
    [_default_val, 8] uint16 batch_size;
    [_default_val, 2] uint16 disk_threads;
    [_default_val, 4] uint16 max_file_mb;
    [_default_val, 7] byte keepdays;
};
```

并挂到 `hostvm_server`：

```ptl
struct hostvm_server
{
    struct hostvm_info info_;
    struct logcollector_info logcollector_;
    struct subvm_info subvms_[];
};
```

示例 XML：

```xml
<hostvm_server>
    <hostvm_info threadnum="4" loglevel="0" metadb_path="." projects_dir="."
                 vmname="zmis" vmaddr="" />
    <logcollector_info enable="1" bind_addr="127.0.0.1" bind_port="22502"
                       log_path="log/collect" keepdays="7" />
    <subvm_info vmtype="py" vmname="zpy" vmpath="start.py" vmaddr="" />
</hostvm_server>
```

默认绑定 `127.0.0.1`。如果要收集局域网日志，需要显式配置 LAN 地址或 `0.0.0.0`。

兼容性与代码生成约束：

- `enable` 默认 `0`：基础设施新端口必须**显式开启**，不能升级即开监听（安全姿态）。示例 XML 中 `enable="1"` 仅为演示。
- 在 `hostvm_server` 的 `info_` 与 `subvms_[]` 之间插入 `logcollector_`，XML 为具名解析；旧 `hostvm.xml`（无 `<logcollector_info>`）必须能靠默认值正常解析——上线前需实测回归。
- 修改 `hostvm_config.ptl` 后**必须用 zgen 重新生成** `hostvm_config_proto.h` 与 `hostvm_config_pack.{h,cpp}`，不能手改生成文件。

## 7. 生命周期

进程模型注意：现有 VM（`zpy`/`zident`/`zmpc` 等）在 `onWorkerStart()` 里、跑在 `process_host_` 拉起的**独立 worker 进程**。`LogCollectorVM` 作为基础设施、单实例常驻，**有意**放在 daemon（master）进程的 `onDaemonStart()` 里，与现有 subvm 模式不同，这是刻意取舍。daemon 主 scheduler 当前为 `active(2)`（见 `hostvm_service.cpp`），故落盘必须使用 §5.4 的专用 scheduler。

### HostVMService 改动

- 新增成员：`zce::SmartPtr<zce::Object> log_collector_vm_;`
- override `void onDaemonStop();`（`zce::Service` 已声明该虚函数）。

### daemon 启动（`onDaemonStart()` 内，`initStub` 之后、subvm 自动创建循环之前）

1. 加载 `hostvm.xml`、启动主 scheduler、`initStub(...)`（沿用现有流程）。
2. 调用 `zlogcollector_init()` 确保 VM 类型注册。该函数必须复刻 ident 的**防链接器优化**写法（在静态 register 对象之后引用它，如 `(void)&logcollector::_register;`），否则静态注册会被链接器优化掉——ident 曾踩此坑。
3. 若 `logcollector_.enable != 0`，boot：

```cpp
zdp_base::zvm_t vm{};
vm.vmtype = "logcollector";
vm.vmname = "logcollector";
log_collector_vm_ = zce::zvm::VirtualMachineStubSigt::instance()->boot(vm, {});
```

4. 继续现有 daemon 启动流程。

### daemon 停止（`onDaemonStop()` 内）

1. `zce::zvm::VirtualMachineStubSigt::instance()->destroy(log_collector_vm_);`（`destroy()` 是真实 API，内部触发 `Machine::stop()`）。
2. `LogCollectorMachine::stop()`：先关闭 UDP 接收 socket（停止新包进入）；若 §5.2 选用了**独立 reactor 实例**，还需 `udp_reactor_->stop()` 停其线程（共享 stub reactor 则不动它）。
3. flush 全部落盘分片队列：停止入队 → 排空各 shard 剩余 record → fsync + 关闭文件句柄。须为**有界等待**（设上限超时 / 最大排空轮次），防止停止流程挂起。
4. `disk_scheduler_->stop()`（必须在 flush 完成之后，否则 flush 任务无线程执行）。
5. 继续 `zce::Service::onDaemonStop()` 原有清理。

### 配置热更新

v1 建议：

- `enable`、`bind_addr`、`bind_port` 变更要求重启。
- `keepdays`、`max_file_mb`、清理策略可以热更新。
- 后续版本可支持配置变化时重启 `LogCollectorVM`。

## 8. 错误处理和背压

接收端校验：

- 长度小于 2 字节：丢弃（`dropped_short`）。
- `version` 不支持：丢弃（`dropped_version`）。
- `type` 非法值：丢弃（`dropped_type`）。`type=1`（交互 Command）是合法但 v1 不处理，单独计入 `skipped_command`，不混入 `dropped_type`。
- `compress` 不支持：丢弃（`dropped_compress`）。
- UDP 截断语义：`recvfrom` 超出接收缓冲会被内核**静默截断**，收端无法获知原始长度。接收缓冲 / `suggest_size` 至少设为 `max_datagram`；超过 `max_datagram` 的包按截断处理并计入 `dropped_*`，而非假设可判长丢弃。
- `ext` reserved 位非 0：忽略，**不丢包**（前向兼容，见 §3）。
- app 名非法：按 §4 清洗后继续处理；清洗为空 / 非法形态则用 `unknown`。

背压策略（入队准入控制，非队内重排）：

- `TaskQueue` 内部是 `std::deque`，**不支持优先级重排**。背压只能在**入队前**做准入：当目标 `LogDiskShardQueue::try_queue_length()` 或 dispatcher 汇总队列长度超阈值时，丢弃**新到包**中 level ≤ 当前截断级别的包，已入队元素不动。
- `try_queue_length()` 在拿不到锁时返回 `-1`（见 `zce_task_queue.h`）。`-1` 必须视为“长度未知、本次不丢”，**不得**参与阈值比较，也不得计入 dispatcher 的汇总求和（负值会污染估算）。
- 截断级别按队列拥塞程度抬升，丢弃优先级：`TRACE -> DEBUG -> INFOR -> WARNI -> ERROR -> FATAL -> BIZDT`。
- `LogDiskDispatcher` 维护全局队列长度估算和分级丢弃计数；每个 `LogDiskShardQueue` 维护自身队列长度、写入量、活跃文件数。
- `ZLOG_NONEL` 通常不应由发送端发送；如果收到，计入统计并按最低优先级（最先丢）处理或直接丢弃。
- 不要对每个丢弃包都写本地日志，避免形成递归日志风暴。

统计字段：

```text
received_packets
received_bytes
parsed_packets
dropped_short
dropped_version
dropped_type
dropped_compress
skipped_command
dropped_queue_full
dropped_trace
dropped_debug
dropped_infor
dropped_warni
dropped_error
dropped_fatal
dropped_bizdt
dropped_nonel
written_packets
written_bytes
active_files
```

`HostVMService::printServiceStatus()` 应输出这些统计。

## 9. 发送端设计

需要一个小的 UDP 发送 helper：

```cpp
int sendUdpLog(const char* host, uint16_t port,
               const char* app, const char* content, size_t content_len);
```

发送端规则：

- app 名清洗后截断到 15 字节（注意按字节截断可能切断多字节 UTF-8 序列；清洗会把残字节替换为 `_`，可接受）。
- 设置 `version=1`、`level` 按本地日志级别映射、`compress=0`、`type=0`、ext reserved 位置 0。
- 总 datagram 建议不超过 1400 字节。
- helper 必须**线程安全且非阻塞**：`zce::Logger::setCallback` 是全局静态、回调在任意日志线程触发；用一次性 UDP `sendto`，失败即弃，不影响业务流程。
- **递归防护**：转发路径自身的失败 / 诊断**绝不能**再走会被转发的日志宏，否则形成日志风暴（与 §8 收端递归防护对应）。

后续 worker 进程可通过 `zce::Logger::setCallback()`（签名 `void(unsigned level, const char* msg, size_t len)`，见 `include/zce/zce_log.h`）接入这个 helper，让现有 `ZCE_DEBUG`、`ZCE_ERROR` 调用无需改动即可转发。

## 10. 开发计划

> 全程规范约束（CLAUDE.md）：
> - 新增 `.h/.cpp` 必须 **UTF-8 with BOM** 编码。
> - 命名：类 PascalCase、函数 camelCase、变量 snake_case、成员变量尾下划线。
> - 测试必须 GTest：文件名 `test_*.cpp`、放 `tests/` 目录、`main` 用 `#ifndef USE_GTEST_MAIN` 包裹、CMake 用 `add_test` 注册并链接 `GTest::gtest`。
> - 优先复用 libzce（Reactor / Udp / TaskQueue / Scheduler / Timer / 日志），不自造。

### 阶段 1：协议和解析器

- 新增 `logcollector_protocol.h/.cpp`。
- 实现 flag/ext 打包和解析。
- 实现 `parseLogPacket`。
- 覆盖测试：合法包、短包、错误 version、level 映射、错误 type、错误 app 长度、空 app。

### 阶段 2：VM 骨架

- 新增 `logcollector_vm.h/.cpp`。
- 实现 `LogCollectorMachine : zce::zvm::Machine`。
- 注册 `VirtualMachineRegister("logcollector", ...)`。
- 增加 `zlogcollector_init()`。
- 在 HostVM daemon 中接入 boot 和 shutdown。

### 阶段 3：UDP 接收

- 新增 `logcollector_receiver.h/.cpp`。
- 实现 `LogUdpReceiver : zce::Udp`，构造传入所选 reactor（共享 stub reactor 或独立实例），不派生 `zce::Reactor`。
- 根据配置 `listen(bind_addr, bind_port)`。
- 把 `zce_sockaddr_t` 转为规范 source IP（§4 localhost 规则）。
- 将解析后的 `LogRecord` 投递给 `LogDiskDispatcher`。

### 阶段 4：落盘队列

- 新增 `logcollector_disk.h/.cpp`。
- 实现专用 `zce::Scheduler`、`LogDiskDispatcher` 和 `LogDiskShardQueue[N]`。
- 实现文件命名、打开文件缓存、按日期/大小滚动、flush、历史清理。
- 确保所有文件 IO 只发生在落盘 scheduler，不发生在 UDP reactor。

### 阶段 5：配置和状态

- 扩展 `hostvm_config.ptl`。
- 使用现有 HostVM 生成流程更新 `hostvm_config_proto/pack`。
- 更新示例 `hostvm.xml` 模板。
- 在 `printServiceStatus()` 输出 LogCollector 统计。

### 阶段 6：发送端 helper

- 新增发送端 helper，用于测试和 worker 接入。
- 可选：通过 `zce::Logger::setCallback()` 转发 worker 本地日志。
- 保持发送失败非致命。

### 阶段 7：验证

- 协议解析单元测试（GTest，`tests/test_logcollector_protocol.cpp`，覆盖：合法包 / 短包 / 错误 version / level 映射 / 错误 type / `type=1` 跳过 / 错误 app 长度 / 空 app / reserved 位非 0 不丢）。
- localhost UDP smoke test：发一条日志，检查目标文件按 §4 命名规则生成。
- 文件名加固测试：app 为 `..` / `.` / 前导 `-` / 含 `/` 时归一化为 `unknown`，无越权写出。
- 小 `max_file_mb` 配置下的滚动测试。
- 队列阈值很小时的背压 / 分级丢弃测试（验证入队准入而非队内重排）。
- 旧 `hostvm.xml`（无 `<logcollector_info>`）默认值解析回归。
- 跑 HostVM 对应平台构建。
