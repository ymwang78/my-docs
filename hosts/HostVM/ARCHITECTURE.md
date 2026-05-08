# HostVM 架构设计文档

> 基于 `hosts/HostVM` 与 `libsrc/libzce` 库中 `zce_process` / `zce_service` / `zvm` 相关源码整理。

---

## 目录

1. [总体架构概述](#总体架构概述)
2. [进程模式与启动流程](#进程模式与启动流程)
3. [核心组件](#核心组件)
4. [进程间通信协议](#进程间通信协议)
5. [消息协议](#消息协议)
6. [子进程管理与生命周期](#子进程管理与生命周期)
7. [外部进程注册机制](#外部进程注册机制)
8. [配置结构](#配置结构)
9. [元数据持久化](#元数据持久化)
10. [Storm 消息总线](#storm-消息总线)
11. [RPC 框架](#rpc-框架)
12. [CLI 工具 hostctrl](#cli-工具-hostctrl)
13. [支持的 VM 类型](#支持的-vm-类型)

---

## 总体架构概述

HostVM 是一个**多进程虚拟机宿主管理器**，具备以下核心能力：

- 以 **Daemon 模式**运行，统一管理和监控多个子进程（SubVM）
- 以 **Worker 模式**作为子进程运行，加载具体的 VM 运行时（Lua / Python / MPC / Ident 等）
- 通过 **命名管道（Named Pipe）** 在父子进程之间建立 IPC 通道
- 提供 **ZDP RPC** 接口，支持远程查询/启停子进程
- 将子进程元数据持久化至 **SQLite 数据库**，重启后自动恢复
- 通过 **Storm 消息总线** 广播日志和状态变更事件

```
+-----------------------------------------------------------+
|                    HostVM Daemon 进程                      |
|                                                           |
|  HostVMService (zce::Service)                             |
|  +-- Reactor (libuv 事件循环)                              |
|  +-- Scheduler (线程池, 默认 2 线程)                        |
|  +-- VirtualMachineStub (RPC 框架)                         |
|  |   +-- 监听 TCP vmport:22500                             |
|  +-- SubProcessHost (子进程管理器)                          |
|  |   +-- subprocess_map_[name] -> Process                  |
|  |   +-- SQLite DB (subvm.db)                              |
|  |   +-- StormClient -> StormVM:22501                      |
|  +-- Timer (1s 周期：配置热更新/版本检查/状态打印)            |
|                                                           |
|  子进程 #1 (Worker): hostvm work --vmguid G1 --vmtype lua |
|  子进程 #2 (Worker): hostvm work --vmguid G2 --vmtype py  |
+-----------------------------------------------------------+
         | Named Pipe (GUID)       | Named Pipe
         v                         v
+------------------+   +----------------------+
|  Worker: lua VM  |   |  Worker: Python VM   |
|  zce::Service    |   |  zce::Service        |
|  SubProcess 反连  |   |  SubProcess 反连     |
+------------------+   +----------------------+

外部工具:
hostctrl ps / list / start / stop / restart
    | TCP RPC 22500
    +---> SubProcessHost.listVM / startVM / stopVM ...
```

---

## 进程模式与启动流程

HostVM 可执行文件支持以下运行模式（通过子命令区分）：

| 子命令     | 说明                                   |
|----------|--------------------------------------|
| `daemon` | 守护进程模式，管理子进程                 |
| `console`| 前台模式（等同 daemon，但不脱离终端）      |
| `work`   | 子进程工作模式（由 daemon 自动启动）       |
| `service`| Windows 系统服务模式                    |

### Daemon 启动序列

```
main()/wmain()
  +-- HostVMService::main(argc, argv)
        +-- CLI 解析 -> mode = "daemon"
              +-- Service::runReactor()
                    +-- Reactor::start()
                          +-- onReactorStart()
                                +-- HostVMService::onDaemonStart()
                                      1. zce::chdirToModulePath()
                                      2. zlog_init("hostvm")
                                      3. HostVMConfig::load("hostvm.xml")
                                      4. Scheduler::active(2)        -- 启动线程池
                                      5. VirtualMachineStub::initStub()
                                      6. Service::onDaemonStart()    -- 基类
                                         +-- 创建 SubProcessHost
                                         +-- SubProcessHost::start()
                                         |     +-- 创建 StormClient:22501
                                         |     +-- 打开/创建 SQLite subvm.db
                                         |     +-- 从 DB 恢复历史子进程记录
                                         |     +-- 补充 auto_create 新增条目
                                         |     +-- invoke() 启动所有子进程
                                         +-- VirtualMachineStub::listen(22500)
                                      7. 从 XML <subvms> 添加自动创建条目
                                      8. boot("updated", ...) -- 版本检查VM
```

### Worker 启动序列

子进程由 `SubProcessHost` 通过 `uv_spawn` 启动，命令行格式：

```
hostvm work --vmguid <guid> --vmtype lua --vmname <name> --vmpath <path>
```

```
main()
  +-- HostVMService::main()
        +-- mode = "work"
              +-- HostVMService::onWorkerStart()
                    1. 添加 Python/Lua 环境 PATH
                    2. zlog_init(vmname, prefix="Sub-")
                    3. HostVMConfig::load("hostvm.xml")
                    4. BlockPool::add_pool()          -- 内存池初始化
                    5. Scheduler::active(threadnum)
                    6. VirtualMachineStub::initStub()
                    7. 根据 vmtype 分发初始化：
                       "lua"       -> zua_init() + zcoin_init()
                       "py"        -> zpy_init()
                       "TaijiMPC"  -> zmpc_init()
                       "ident"     -> zident_init()
                    8. Service::onWorkerStart() 基类
                       +-- connectToFatherProcess()  -- 连回父进程 named pipe
```

---

## 核心组件

### HostVMService

**位置**：`hosts/HostVM/hostvm/hostvm_service.{h,cpp}`

HostVM 应用的顶层服务类，继承自 `zce::Service`。

**关键回调**：

| 方法                | 触发时机        | 主要职责                             |
|-------------------|---------------|-------------------------------------|
| `onDaemonStart()` | Daemon 模式启动 | 加载配置、初始化基础设施、启动子进程       |
| `onWorkerStart()` | Worker 模式启动 | 初始化内存池、分发 VM 类型初始化函数      |
| `onWorkerStop()`  | Worker 停止   | `_exit(0)` 强制退出（防止析构挂起）      |
| `onTimer()`       | 每秒一次        | 配置热更新、定期版本检查、日志轮转、状态打印 |

---

### zce::Service

**位置**：`include/zce/zce_service.h`，`libsrc/libzce/core/zce_service.cpp`

所有 ZCE 服务的基类，继承自 `zce::Reactor`（libuv 事件循环）。

**核心职责**：

- 使用 CLI11 解析命令行参数，分发到对应模式
- 管理操作系统信号（SIGHUP / SIGINT / SIGTERM）
- 管理 1 秒周期定时器
- Daemon 模式下：持有 `SubProcessHost`、`StormVM` 实例
- Worker 模式下：通过 `connectToFatherProcess()` 连回父进程管道

**重要成员**：

```cpp
AppOptions options_;                         // 解析后的命令行参数
SmartPtr<SubProcessHost> process_host_;      // 子进程宿主（仅 Daemon）
SmartPtr<zdp::StormVM> storm_host_;          // Storm 消息服务端
SmartPtr<zdp::StormClient> storm_client_;    // Storm 消息客户端
SubProcessHost::HostContext host_context_;   // SubProcessHost 配置
SmartPtr<SubProcess> sub_process_;           // 连回父进程通道（仅 Worker）
```

`AppOptions` 继承自 `zdp_base::zvm_t`，额外字段：

```
mode        - 运行模式：daemon / work / service
pidfile     - PID 文件路径
logsuffix   - 日志文件名后缀
configpath  - 配置文件路径
```

---

### zce::SubProcessHost

**位置**：`include/zce/zce_process.h`，`libsrc/libzce/core/zce_process.cpp`

子进程管理器，继承自 `zce::zvm::Machine`（可被 RPC 调用的虚拟机）。

**核心数据**：

```cpp
map<string, SmartPtr<Process>> subprocess_map_;    // 活跃子进程表
map<string, SmartPtr<Process>> delaycheck_map_;    // 延迟重启队列
map<string, zvm_t>  auto_create_process_map_;      // 配置预设的自动创建条目
map<string, int>    vmtype_maxnum_map_;             // 每种 vmtype 最大实例数限制
SmartPtr<zdb::Database> database_ptr_;             // SQLite 持久化
SmartPtr<zdp::StormClient> storm_client_;          // 广播状态/日志
```

**HostContext 配置**：

| 字段             | 默认值         | 说明                     |
|----------------|--------------|--------------------------|
| `metadb_path`  | `"subvm.db"` | SQLite 数据库路径           |
| `table_name`   | `"subvm0"`   | 子进程元数据表名             |
| `debug_mode`   | `false`      | 子进程是否继承 stdout/stderr |
| `vmname`       | `"VMHost"`   | 本机 RPC 名称              |
| `vmport`       | 22500        | RPC 监听端口               |
| `stormport`    | 22501        | Storm 消息端口             |
| `host_dir`     | `"."`        | VM 文件存储根目录            |

**暴露的 RPC 方法**：

| 方法        | 参数              | 说明                        |
|-----------|-----------------|----------------------------|
| `listVM`  | 无              | 列出所有子进程信息               |
| `newVM`   | vmtype, vmname  | 创建并启动新的 VM 实例           |
| `uploadVM`| zvm_t, content  | 上传文件并创建 VM 实例           |
| `startVM` | name            | 启动已注册但未运行的 VM          |
| `stopVM`  | name            | 停止 VM（保留注册记录）          |
| `restartVM`| name           | 停止后重新启动 VM              |
| `deleteVM`| name            | 停止并注销 VM（从 DB 删除）      |

---

### zce::Process

**位置**：`include/zce/zce_process.h`，`libsrc/libzce/core/zce_process.cpp`

代表一个被管理的子进程，继承自 `zce::zdp::zdp_stream`（ZDP 协议流）。

**ProcessInfo（进程元数据）** 继承自 `zdp_base::zvm_t`：

```cpp
struct ProcessInfo : public zdp_base::zvm_t {
    string exepath;       // 可执行文件路径
    unsigned delayed;     // 退出后延迟重启秒数
    unsigned pid;         // OS PID
    zce_timestamp starttime;
    zce_timestamp endtime;
    RefBlock dblock;      // 启动时携带的数据块（如脚本内容）
    string extra;         // 扩展字段（JSON）
    int exitcode;         // 退出码
    unsigned autoadd;     // 0=手动, 1=自动创建, 2=外部注册, 3=外部自动重启
};
```

**zvm_t 基础字段**：

```cpp
string vmname;    // 实例名（全局唯一键）
string vmtype;    // VM 类型：lua/py/TaijiMPC/ident
string vmpath;    // 脚本路径
string vmguid;    // GUID（命名管道名称）
string vmaddr;    // 子进程 RPC 地址
uint16 vmport;    // 子进程 RPC 端口
uint16 vmstatus;  // 状态标志（RUNNING=0x01 等）
vector<nspair_t> args;   // 额外命令行参数
vector<nspair_t> env;    // 额外环境变量
```

**子进程启动流程**：

```
SubProcessHost::invoke(process_ptr)
  +-- Process::startProcess()
        +-- 若 PID 存活 -> attachProcess() -- 仅建立 Pipe 连接
        +-- 否则 Impl::startProcess()
              +-- _doListenPipe()
              |     +-- PipeAcceptor 监听 /tmp/<guid>（Linux）
              |     +-- 或 \\.\pipe\<guid>（Windows）
              +-- uv_spawn(exepath, ["work", "--vmguid", guid, ...])
                    +-- 子进程启动 -> 连接 Pipe -> Process::on_open()
```

**进程退出回调链**：

```
libuv uv_exit_cb
  +-- Impl::onExit(exit_code)
        +-- 清除 PID，记录 endtime，清除 RUNNING 标志
        +-- uv_close -> Impl::onClose()
              +-- exit_cb_()  // 默认: invoke(vmname) 触发重启
```

---

### zce::zvm 虚拟机存根

**位置**：`include/zce/zvm.h`，`libsrc/libzce/zvm/`

#### VirtualMachineStub（全局单例 VirtualMachineStubSigt）

| 方法                    | 说明                               |
|-----------------------|----------------------------------|
| `initStub(sched, reactor, dir)` | 初始化 RPC 框架                  |
| `listen(host, port)`  | 作为 RPC 服务端监听 TCP 端口         |
| `listenSchema(uri)`   | 统一 URI 方式（tcp:// 或 pipe://）   |
| `boot(...)`           | 连接远程 VM，返回 VM 指针对象         |
| `rpc_call_dblock(...)`| 发起 RPC 调用（raw dblock）         |
| `rpc_call_builtin(..)`| 发起 RPC（内置类型，自动序列化）       |
| `rpc_call_msg(...)`   | 发起 RPC（ZDP 消息结构体）           |
| `destroy(vmptr)`      | 断开并销毁 VM 连接                  |

#### Machine（抽象基类）

所有可被 RPC 调用的虚拟机继承 `Machine`，需实现：

```cpp
virtual int start() = 0;
virtual void stop() = 0;
virtual int call_dblock(objid, method, dblock, timeout, response_cb) = 0;
```

`SubProcessHost` 继承 `Machine`，通过 `call_dblock` 分发所有管理命令。

---

### zce::Reactor

**位置**：`include/zce/zce_reactor.h`，`libsrc/libzce/core/zce_reactor.cpp`

基于 **libuv** 的事件循环，是整个框架的核心驱动：

- `start(in_place)` - 启动事件循环（当前线程或独立线程）
- `startLoop()` - 进入主循环（阻塞）
- `stop()` - 停止事件循环
- `scheduleTimer(queue, ms, repeat, cb)` - 注册定时器
- `delegateTask(task)` - 向线程池提交异步任务
- `dns_resolve(domain, ptr)` - 异步 DNS 解析（带 TTL 缓存）

`Service` 继承自 `Reactor`，因此 HostVM 进程本身就是事件循环的拥有者。

---

## 进程间通信协议

父子进程之间通过**命名管道**通信，名称规则：

| 平台    | 管道名格式               |
|-------|------------------------|
| Linux | `/tmp/<vmguid>`        |
| Windows | `\\.\pipe\<vmguid>` |

数据帧采用 **ZDP 协议**（ZCE Data Protocol），帧头 `zdp_head` 包含消息 ID、序列号、压缩标志、数据长度。

**连接建立方式**：

- 父进程侧：`PipeAcceptor` 监听 → 接受连接 → 创建 `Pipe` → 链接到 `Process`（zdp_stream）
- 子进程侧：`SubProcess::connectProcess()` → `PipeConnector` → 连接父进程管道

---

## 消息协议

```cpp
enum PRECESS_MSGID {
    // 广播消息 (MBRD = Multicast BRoadcast)
    PROCESS_MBRD_LOGTEXT   = 0x0000,  // 子进程日志广播
    PROCESS_MBRD_UPDATEVM  = 0x0001,  // VM 状态变更广播

    // 子进程->父进程 (S2M = Subprocess to Master)
    PROCESS_S2MQUEFYVM_REQ  = 0x0040, // 子进程启动后查询自身配置
    PROCESS_S2MQUEFYVM_RES  = 0x0041,
    PROCESS_S2MUPDATEVM_REQ = 0x0042, // 子进程更新自身状态(port/status/stormtopic)
    PROCESS_S2MUPDATEVM_RES = 0x0043,
    PROCESS_S2MHBEAT_REQ    = 0x0044, // 心跳
    PROCESS_S2MHBEAT_RES    = 0x0045,
    PROCESS_S2MREGISTER_REQ = 0x0046, // 外部进程注册
    PROCESS_S2MREGISTER_RES = 0x0047,
    PROCESS_S2MUNREGISTER_REQ = 0x0048, // 外部进程注销
    PROCESS_S2MUNREGISTER_RES = 0x0049,

    // 父进程->子进程 (M2S = Master to Subprocess)
    PROCESS_M2SQUIT_REQ  = 0x0080,    // 通知子进程退出
    PROCESS_M2SQUIT_RES  = 0x0081,
    PROCESS_M2SHBEAT_REQ = 0x0082,    // 父进程发起心跳
    PROCESS_M2SHBEAT_RES = 0x0083,
};
```

**典型消息交互流程**：

```
子进程启动
  +-- 连接命名管道 -> Process::on_open() 触发
  +-- 发送 S2MQUEFYVM_REQ -> 父进程返回 zvm_t 信息（含 vmpath/dblock 等）
  +-- 子进程初始化完成后发送 S2MUPDATEVM_REQ
        +-- 通知父进程实际 RPC 端口/状态/stormtopic
        +-- 父进程更新 DB + Storm 广播 MBRD_UPDATEVM

父进程正常停止:
  +-- 发送 M2SQUIT_REQ -> 子进程 graceful 退出
  +-- 等待 200ms -> 若仍存活则 kill(SIGTERM)
```

---

## 子进程管理与生命周期

```
invoke(process_ptr)
  +-- 检查 endtime + delayed -> 若未到延迟时间 -> 加入 delaycheck_map_
  +-- 否则 Process::startProcess()

Process 退出 (uv_exit_cb)
  +-- Impl::onExit()
        +-- 清除 PID, 记录 endtime, 清除 RUNNING 标志
        +-- exit_cb_() -> invoke(vmname) 触发重启逻辑

invoke() 重启逻辑:
  +-- 若 elapsed >= delayed * 1s -> 立即 startProcess()
  +-- 否则 -> 加入 delaycheck_map_

checkDelayedStart()（每秒 Timer 调用）:
  +-- 遍历 delaycheck_map_
  +-- 若 now - endtime >= delayed * 1s -> startProcess() + 移出队列
```

**autoadd 字段含义**：

| 值 | 含义                       |
|---|--------------------------|
| 0 | 手动创建（不自动重启）         |
| 1 | 配置文件自动创建（退出后自动重启）|
| 2 | 外部进程注册（监控但不重启）    |
| 3 | 外部进程注册（退出后自动重启）  |

---

## 外部进程注册机制

任意外部进程可连接 HostVM 的命名管道，将自身注册为受监控的实例：

```
外部进程
  +-- 创建 SubProcess 对象
  +-- connectProcess(pipe_id, ...)    -- 连接到 HostVM 管道
  +-- 发送 S2MREGISTER_REQ(zvm_t, pid, auto_restart)
        +-- HostVM 验证 PID 有效性（通过 isProcessExists()）
        +-- 注册到 subprocess_map_（autoadd = 2 或 3）
        +-- 持久化到 SQLite

checkExternalProcesses()（每秒 Timer 调用）:
  +-- 每 5s 检查一次外部进程 PID 是否存活
  +-- 若退出且 autoadd=3 -> onExternalProcessExit()
        +-- 加入 delaycheck_map_（默认延迟 5s 后重启）

注销时:
  +-- 发送 S2MUNREGISTER_REQ(vmname)
  +-- HostVM 从 subprocess_map_ + DB 中删除记录
```

---

## 配置结构

主配置文件 `hostvm.xml`，XML 反序列化到 `hostvm::hostvm_server`：

```
hostvm_info:
  threadnum    - 工作线程数（0 = CPU 核心数）
  loglevel     - 日志级别
  keepdays     - 日志保留天数（默认 3）
  metadb_path  - SQLite 路径（默认 subvm.db）
  projects_dir - VM 文件根目录
  vmname       - 本实例 RPC 名称（默认 zmis）
  vmaddr       - 监听地址（默认 0.0.0.0）
  vmtopic      - Storm 主题名
  vmport       - RPC 监听端口（默认 22500）
  stormport    - Storm 消息端口（默认 22501）

subvms[]:         -- 预定义的自动启动子 VM 列表
  vmtype         - VM 类型
  vmname         - 实例名
  vmpath         - 脚本路径
  vmaddr         - 连接地址
  vmport         - 端口
```

**配置热更新**：`onTimer()` 每秒检测 `hostvm.xml` 修改时间，若有变化则重新加载并动态调整 `loglevel` 和 `keepdays`，无需重启进程。

---

## 元数据持久化

SQLite 表（默认表名 `subvm0`）：

```sql
CREATE TABLE IF NOT EXISTS subvm0 (
    vmname    TEXT PRIMARY KEY,
    vmtype    TEXT,
    vmpath    TEXT,
    vmaddr    TEXT,
    vmport    INTEGER,
    workdir   TEXT,
    exepath   TEXT,
    args      TEXT,         -- JSON 数组
    env       TEXT,         -- JSON 对象
    vmguid    TEXT,
    stormaddr TEXT,
    stormport INTEGER,
    stormtopic TEXT,
    delayed   INTEGER,
    pid       INTEGER,
    starttime BIGINTEGER,
    endtime   BIGINTEGER,
    extra     TEXT,
    autoadd   INTEGER DEFAULT 0
);
```

**数据库操作时机**：

| 操作               | 触发时机                       |
|------------------|------------------------------|
| INSERT OR REPLACE | 子进程启动/状态更新/连接建立时      |
| DELETE           | `deleteVM` 或外部进程注销时       |
| SELECT ALL       | Daemon 启动时，从 DB 恢复历史记录  |

数据库连接参数：`PRAGMA synchronous=NORMAL; PRAGMA journal_mode=WAL`（兼顾性能与安全）

---

## Storm 消息总线

Storm 是 ZCE 的发布/订阅消息系统，HostVM 使用端口 22501。

**HostVM 发布的消息**：

```
StormClient (host_topic = "ZCE.Process.Host.<guid>")
  +-- 接管 Logger::setCallback()
  |     +-- 将 WARN 及以上级别日志发布 (PROCESS_MBRD_LOGTEXT)
  +-- 子进程状态变更时发布 (PROCESS_MBRD_UPDATEVM)

各子进程的 StormTopic = "ZCE.Subprocess.<vmname>.<vmguid>"
```

---

## RPC 框架

HostVM 在 `vmport:22500` 上提供 ZDP RPC 服务（TCP），任何实现了 ZVM 协议的客户端均可调用：

```
客户端（hostctrl / 远程服务）
    | TCP/ZDP RPC
    v
VirtualMachineStub（监听 22500）
    |
    v
SubProcessHost::call_dblock(objid, method, dblock, timeout, response_cb)
    |
    +-- "listVM"     -> listVM(response)
    +-- "newVM"      -> newVM(vmtype, vmname, response)
    +-- "uploadVM"   -> uploadVM(zvm_t, content, force, response)
    +-- "startVM"    -> startVM(name, response)
    +-- "stopVM"     -> stopVM(name, response)
    +-- "restartVM"  -> restartVM(name, response)
    +-- "deleteVM"   -> deleteVM(name, response)
```

RPC 调用的三种序列化方式：

| 方法                  | 数据格式           | 适用场景          |
|---------------------|------------------|-----------------|
| `rpc_call_dblock`   | 原始 RefBlock      | 通用/自定义序列化   |
| `rpc_call_builtin<T>`| 内置类型（int/string等）| 简单参数      |
| `rpc_call_msg<T>`   | ZDP 消息结构体      | 复杂结构化数据     |

---

## CLI 工具 hostctrl

**位置**：`hosts/HostVM/hostctrl/main.cpp`

独立可执行工具，通过 TCP RPC 与 HostVM Daemon 通信。

### 命令列表

```
hostctrl ps                          列出所有实例（等同 list）
hostctrl list [--app TYPE]           按 vmtype 筛选列表
hostctrl inspect --instance NAME     查看单个实例详情
hostctrl start   --instance NAME     启动实例
hostctrl stop    --instance NAME     停止实例
hostctrl restart --instance NAME     重启实例
```

### 全局选项

```
--human               人类可读输出（默认输出 JSON）
--verbose             详细诊断输出到 stderr
--host HOST[:PORT]    HostVM 地址（默认 127.0.0.1:22500）
--port PORT           RPC 端口
--timeout SEC         超时秒数（默认 15）
HOSTVM=HOST[:PORT]    环境变量（--host 优先级更高）
```

### 实现原理

```
hostctrl
  +-- zce_init() + Reactor::start()
  +-- VirtualMachineStub::boot("zmis", host, port)  -- 连接 HostVM
  +-- rpc_call_dblock(vmptr, 0, "listVM"/..., dblock, timeout, cb)
  +-- Reactor::startLoop()   -- 等待 RPC 响应
  +-- 打印结果 -> stop()
```

**JSON 输出格式**（list 命令）：

```json
{
  "errcode": 0,
  "errdesc": "",
  "data": {
    "host": { "host_topic": "ZCE.Process.Host.xxx", "storm_port": 22501 },
    "instances": [
      { "vmname": "lua1", "vmtype": "lua", "vmpath": "...",
        "vmguid": "...", "vmstatus": 1, "vmport": 22502 }
    ]
  }
}
```

---

## 支持的 VM 类型

| vmtype      | 初始化函数                       | 说明                       |
|------------|--------------------------------|--------------------------|
| `lua`      | `zua_init()` + `zcoin_init()`  | Lua 脚本引擎 + coin 扩展    |
| `py`       | `zpy_init()`                   | Python 脚本引擎（需 Python3）|
| `TaijiMPC` | `zmpc_init()`                  | 太极 MPC 计算模块            |
| `ident`    | `zident_init()`                | 身份验证/识别模块             |

每种 VM 类型通过静态注册机制向 `VirtualMachineStub` 注册工厂函数（`_zXXX_register` 模式），初始化函数的作用是防止链接器优化掉未被显式引用的静态对象。

---

## 组件依赖关系

```
HostVMService
  | inherits
  v
zce::Service
  | inherits           holds
  v              +------------------------+
zce::Reactor <---| SmartPtr<SubProcessHost>|
  |              | SmartPtr<StormVM>       |
  | uses         | SmartPtr<StormClient>   |
  v              +------------------------+
libuv (uv_loop_t)
                       |
                SubProcessHost
                (inherits Machine)
                       | manages
                +------v------+
                | map<name,   |
                | SmartPtr    |
                | <Process>>  |
                +------+------+
                       |
                    Process
                (inherits zdp_stream)
                       | wraps
                uv_process_t (uv_spawn)
                       |
              Named Pipe (GUID-based)
                       |
                 Worker 进程
               (SubProcess 反向连接)

VirtualMachineStub (Singleton)
  +-- RpcServant (监听 TCP:22500)
  |     +-- 分发到 SubProcessHost::call_dblock
  +-- vm_map[name] -> 远程 VM 连接对象
```

---

*文档基于源码 (`zce_process.cpp` / `zce_service.cpp` / `zvm.h`) 生成，最后更新：2026-05-08*