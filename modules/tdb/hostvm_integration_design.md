# xTdb × HostVM ZVM 集成 — 设计与开发计划

> 范围：**后端**。让 xTdb 既能独立运行，又能作为 HostVM 的受管 `subvm` 运行，
> 通过一层 ZVM 门面（`XTdbMachine`）接入统一的 **进程守护 / 控制面 RPC / 日志与事件归集**。
> 嵌入采用 **链接式 subvm（与 `zmpc` 同款）**：VM 注册静态链接进 HostVM，
> worker 进程为“重生的 `hostvm.bin work`”。独立形态 `xtdbd` 与嵌入用的 `xtdb_vm_lib` **分开编译**。
>
> 前端 `TdbProject`（xOptCon 插件）属于后续工作，本文仅在 §8 给出对接契约，不展开。

| 项 | 值 |
|---|---|
| 文档状态 | Draft **v2**（v1 关于宿主进程模型的若干假设已被源码核实推翻，见 §2.4 / 变更说明） |
| 日期 | 2026-06-04 |
| 宿主模型决策 | **A：链接式 subvm（zmpc 同款）** |
| 关联模块 | `modules/tdb`、`hosts/HostVM`、`libsrc/libzce/{zvm,core}` |
| 参考实现 | `modules/fgw`（`ZfgwMachine`/`zfgw_init`）、`modules/mpc`（`zmpc_init`）、`hosts/HostVM/hostvm/logcollector_vm.cpp` |

> **v1→v2 变更说明（已用源码核实）**：v1 误以为嵌入是“独立 `xtdbvm` 子进程，`subvm_info.vmpath` 指向它，HostVM 零改动”。
> 实测：`exepath` 恒为 `getModulePath()`（HostVM 自身二进制，`zce_process.cpp:700/1428`），`--vmpath` 仅为提示参数；
> worker = 重生的 `hostvm.bin work`，**VM 工厂必须静态链接进 HostVM**（现状即如此：`CMakeLists:200` 链 `zmpc`、
> `hostvm_service.cpp:172` 调 `zmpc_init`）。故 v1 的独立 `xtdbvm` exe / `main_vm.cpp` 作废，改为本版 §5/§6。

---

## 1. 背景与目标

### 1.1 现状（已具备）

- xTdb 已有 core + api（`libxtdb`），并提供两套对外协议：
  - **REST 管理面**：`rest_server.{h,cpp}`（`/api/v1/db|stats|containers|data|maintenance`）。
  - **xds 二进制数据面**：`server/xds.ptl`（高频写 / 范围查询，自带帧头 + CRC + ZDS payload）。
- 已有共享静态库 **`xtdb_server_lib`**（`rest_server.cpp` + `data_server.cpp` + `xds_pack.cpp`）与独立守护进程 **`xtdbd`**（`server/src/main.cpp`）。见 `server/CMakeLists.txt`。
- `main.cpp` **已实现 zmis 自注册**：`--instance-name / --zmis-host / --zmis-port / --advertise-addr`，
  通过 `zmisRegister()` 用 `VirtualMachineStub` 连 zmis 并 announce（`server/src/main.cpp:155,183`）。

> 即：xTdb 目前是 zmis 的 **客户端（announce-only）**——能让 mesh 知道“我在 `advertise-addr`”，
> 但 **未托管可被调用的 VM**，HostVM 也 **不拉起/守护** 它。

### 1.2 目标（本期）

1. 让 xTdb 作为 HostVM 的 **受管 subvm** 运行：HostVM 负责拉起、守护、重启。
2. 在 xTdb 内 **实现 `XTdbMachine : zce::zvm::Machine` 门面**，提供 **控制面 RPC**（状态/端点发现/统计/容器元数据/生命周期/维护/token）。
3. **日志归集**：tdb 的 ZLOG 汇入 HostVM `logcollector`；**关键事件/错误** 经 **Storm** 广播给前端。
4. **保留完全独立运行**：`xtdbd` 不变、零 HostVM 耦合；嵌入所需的 VM 门面单列为 `xtdb_vm_lib`，与 `xtdbd` **分开编译**。

### 1.3 非目标（本期不做）

- ❌ 前端 `TdbProject` 插件实现（另文）。
- ❌ 修改 xds 线协议、存储引擎格式。
- ❌ 把 **数据面** 改走 HostVM/ZVM 中转 —— **数据面永远 xds 直连**。
- ❌ 改动 libzce 公共框架（`zce_process` 等）以支持“独立 exe 形态”—— 那是 §5 模型 C，本期不采。

> 关于隔离：采用模型 A 后，**VM 代码被链接进 HostVM 二进制**，但 **worker 仍是独立 OS 进程**
> （重生的 `hostvm.bin work`）。因此 tdb 崩溃 **不会** 拖垮 HostVM daemon——进程级隔离仍在；
> 代价是 HostVM 二进制体积变大（携带 `libxtdb`），见 §5、§12。

---

## 2. 关键现状与契约（已核实，带文件引用）

### 2.1 HostVM = 单体宿主（链接所有模块 VM）+ ZVM mesh + 进程守护

- HostVM **链接各模块 VM 静态库** 并在 `onDaemonStart` 调它们的 `*_init()` 注册 VM 类型：
  `zua_init/zpy_init/zident_init/zcoin_init/zmpc_init/zlogcollector_init`（`hostvm_service.cpp:7-11,155-178`），
  构建侧 `target_link_libraries(hostvm.bin PRIVATE ... zmpc ...)`（`hosts/HostVM/CMakeLists.txt:200`）。
- 子进程型 subvm：`process_host_->addAutoCreateProcess(zvm_info)`（`hostvm_service.cpp:81-89`）。
- 进程内型 infra VM：`VirtualMachineStubSigt::instance()->boot(vm, args)`（如 `logcollector`）。
- subvm 配置（`hostvm_config.ptl`）：`struct subvm_info { vmtype; vmname; vmpath; vmaddr; uint16 vmport; }`。

### 2.2 VM 契约：`zce::zvm::Machine`

`include/zce/zvm.h` + `libsrc/libzce/zvm/zvm_base.h`，参考 `LogCollectorMachine`/`ZfgwMachine`：

```cpp
class Machine : public zce::TaskQueue {          // VM 自带串行任务队列
  Machine(const std::string& vm_name, const SmartPtr<VirtualMachineStub>& stub_ptr);
  virtual int  start() = 0;                       // 资源拉起；reactor_ptr() 取共享 reactor
  virtual void stop()  = 0;                        // 优雅关停
  virtual int  call_dblock(zce_int64 objid, const std::string& method,
                           RefBlock& dblock, int mstimeout,
                           const VirtualMachineStub::response_cb& response) = 0;  // 控制面 RPC 分发
  // 便捷返回：sendResponse(response, r1, r2, ...);
};
```

注册（静态，**链接进 HostVM 后由对应 `*_init()` 触发**）：

```cpp
static zce::zvm::VirtualMachineRegister _xtdb_register(
    "xtdb",
    [](const zdp_base::zvm_t& vm, const SmartPtr<VirtualMachineStub>& stub, RefBlock& content)
        -> SmartPtr<Machine> { return new XTdbMachine(vm.vmname, stub, content); });  // content=配置 payload
extern "C" int xtdb_vm_init();   // 触碰注册符号，防链接器 GC（logcollector/ident 曾踩坑）
```

### 2.3 参考范式 `fgw`/`mpc`

模块自身编为 **static lib**，内含 `XxxMachine : zce::zvm::Machine`（类型化 handler + 宏分发），
注册于 `VirtualMachineRegister("type", ...)` + `xxx_init()`，由 HostVM 链接并在启动时调用。**tdb 照此落地。**

### 2.4 ⭐ 子进程启动契约（本次核实重点，三段）

1. **argv（固定）** — HostVM `uv_spawn` 推送（`zce_process.cpp:286-300`），子进程经 `zce::Service` 的 `work` 子命令解析（`zce_service.cpp:204-218`）：
   ```
   <hostvm.bin> work --vmguid <guid> --vmtype <type> --vmname <name> --vmpath <path>
                     [可选 --vmport/--pidfile/--logsuffix/--configpath 及透传 args]
   ```
   `exepath` **恒为 `getModulePath()`**（`zce_process.cpp:700/1428/683/281`）⇒ 被 spawn 的就是 **HostVM 自己**；`--vmpath` 仅作提示。
2. **env** — `ProcessInfo.env`（metadb 内以 JSON 存，`_serializeEnv`）作为真实环境变量传入；一般 subvm 为空。
3. **真正的参数/配置经 vmguid 命名管道“回查”**（line 285 注释“更多VM参数...需要子进程向父进程查询”的实现）：
   - 子进程凭 `--vmguid` 连父进程命名管道 → 发 `PROCESS_S2MQUEFYVM_REQ`（"QUEFYVM"）；
   - 父进程回 `PROCESS_S2MQUEFYVM_RES`，带 **完整 `zvm_t`（vmaddr/vmport/stormaddr/stormtopic…）+ 配置 `dblock`**（`zce_service.cpp:1049-1070`、`zce_process.cpp:1606-1608`）；
   - 子进程 `startVMFromFather(zvm_info, content)` → `listen(vmaddr,vmport)` → `boot(options_, content)` 实例化已注册的 VM（`zce_service.cpp:1094-1116`）。
   - 配置 `content` = `ProcessInfo.dblock`（`createSubProcess` 塞入，或 `uploadVM` 落 VM home dir 文件）。
4. **控制口自动上报已内建**：`vmport==0` → 子进程取临时端口 → 经 `PROCESS_S2MUPDATEVM_REQ` 回报父进程（`zce_service.cpp:1098-1113`）。
   ⇒ **控制口的端点发现框架已替我们做了**；REST/xds 口仍需我们经 `getEndpoints` 自报（§8）。

> 结论：tdb **不需要** 自写 `main`/`initStub`/管道握手——这些由 HostVM 的 `zce::Service` work 模式完成。
> tdb 只需 **提供链接进 HostVM 的 VM 注册（`xtdb_vm_init` + `XTdbMachine`）**，并从 `boot` 传入的 `content` 解析自身配置。

---

## 3. 总体架构

### 3.1 “一个 Ops 门面 + 三个传输适配器”

> 核心原则：**业务逻辑只在 `xtdb_server_lib` 实现一次**；REST / xds / ZVM-RPC 都是 **薄适配器**。

```
                         ┌─────────────────────────────────────────────┐
                         │              libxtdb (engine + api)          │
                         └─────────────────────────────────────────────┘
                                              ▲
                         ┌─────────────────────────────────────────────┐
                         │  xtdb_server_lib  (唯一业务实现 / Ops 门面)   │
                         │  open/close · stats · containers · write     │
                         │  query · flush · retention/reclaim/seal      │
                         │  token store                                 │
                         └───────┬───────────────┬───────────────┬──────┘
            REST adapter ────────┘      xds adapter ┘   ZVM-RPC adapter ┘
            (现有, /api/v1)        (现有, 数据面)        (新增 = XTdbMachine, in xtdb_vm_lib)
```

### 3.2 两种部署形态

```
 ┌──────────────────────────── Standalone（保持不变）───────────────────────────┐
 │  xtdbd  =  xtdb_server_lib + REST + xds  (+ 可选 zmis announce)                │
 │  不链接 xtdb_vm_lib；无监管；独立部署/CI/测试                                   │
 └───────────────────────────────────────────────────────────────────────────────┘

 ┌──────────────────────────── Embedded（链接式 subvm，模型 A）────────────────────┐
 │   hostvm.bin (daemon, vmname="zmis")  ── 链接 xtdb_vm_lib，onDaemonStart 调 xtdb_vm_init()
 │     ├─ process_host: uv_spawn(自身, "work") + 守护 ──►  hostvm.bin(work) 子进程   │
 │     │                                                   = 重生进程，内含 XTdbMachine│
 │     ├─ vmguid 管道: QUEFYVM 下发 zvm_t + 配置 dblock ──►  start(): openDb+REST+xds │
 │     ├─ zvm mesh (vmport) ◄── 控制面 RPC ──────────────►  XTdbMachine ("xtdb")     │
 │     ├─ Storm (22501)     ◄── 事件/错误 ───────────────┘                           │
 │     └─ logcollector(UDP) ◄── 批量日志(ZLOG) ──────────┘                           │
 │                                                                                  │
 │   前端 xOptCon ──连 HostVM──► 枚举 subvm("xtdb*") ──getEndpoints/issueToken──┐    │
 │                                                                             ▼     │
 │   前端 xds client ───────── 数据面直连 xds(addr:port, token) ─────────► 该 worker │
 └──────────────────────────────────────────────────────────────────────────────────┘
```

- **控制/发现/生命周期** → ZVM-RPC（经 mesh，按 `vmname` 路由）。
- **高频数据（write/query）** → xds **直连**（前端先经 RPC 拿 endpoints + token）。
- **批量日志** → logcollector（UDP→落盘）；**低频事件/错误** → Storm（前端 `InstanceStormClient` 订阅）。

---

## 4. 编译目标拆分（“分开编译”）

### 4.1 目标矩阵

| 目标 | 类型 | 组成 | 依赖 | 说明 |
|---|---|---|---|---|
| `xtdb` (`libxtdb`) | static | 引擎 + api | — | 已存在 |
| `xtdb_server_lib` | static | rest_server + data_server + xds_pack + **Ops 门面** | xtdb, zce | 已存在；**抽出 Ops 门面**（§4.3） |
| **`xtdb_vm_lib`** | static | **新增** `xtdb_vm.cpp` + `xtdb_vm_rpc.cpp` + `xtdb_vm_pack.cpp` + 注册 + `xtdb_vm_init` | xtdb_server_lib, zce(zvm) | **本期新增**；控制面全部在此；**被 HostVM 链接** |
| `xtdbd` | exe | `main.cpp` | xtdb_server_lib | 已存在；**不链接 `xtdb_vm_lib`** |
| `hostvm.bin` | exe | HostVM | 各模块 VM lib **+ 新增 `xtdb_vm_lib`** | **改动**：加链接 + `xtdb_vm_init()`（照 `zmpc`） |

> ⚠️ 模型 A 下 **没有独立 `xtdbvm` 可执行文件**；嵌入态 VM 代码随 `hostvm.bin` 一起编译/部署，
> 运行时以“重生的 `hostvm.bin work`”子进程承载。

### 4.2 硬约束（保证“分开编译、互不强依赖”）

1. `xtdbd` **绝不** 链接 `xtdb_vm_lib` —— standalone 二进制内 **不含** HostVM 控制面代码。
2. `xtdb_server_lib` **不依赖** `xtdb_vm_lib`/HostVM —— 保持可独立 gtest。
3. `xtdb_vm_lib` 可独立构建（`cmake --build . --target xtdb_vm_lib`），不触发 `xtdbd`。
4. Windows 侧新增 `libxtdb_vm.vcxproj`；HostVM 工程增加对其引用 + `xtdb_vm_init` 调用。
5. 可选宏 `XTDB_WITH_HOSTVM`：仅 `xtdb_vm_lib` 定义，`#ifdef` 包裹 zvm/Storm include，便于裁剪。

> 说明：zce/zvm 本就是 standalone 既有依赖（`xtdbd` 已用 zce reactor/http，且 `zmisRegister` 已用 `VirtualMachineStub`）。
> “分开编译”的目的是隔离 **`XTdbMachine` + VM 注册 + 控制面 handler**，使 standalone 无 HostVM 业务耦合、可独立回归。

### 4.3 `xtdb_server_lib` 的小重构（P0，不改行为）

把 REST handler 内联的业务调用，**收敛为稳定 Ops 门面**（被 REST 与 ZVM-RPC 共用）：

```cpp
// server/include/xtdb_ops.h  (新增；从 rest_server 抽取，零行为变化)
namespace xtdb::server {
class XtdbOps {                          // 持有 xtdb_handle_t；线程访问见 §6.3
  int  openDb(const OpenReq&, OpenRes&);
  int  closeDb();              int dbInfo(DbInfo&);
  int  stats(StatsKind, StatsOut&);                  // write/read/maintenance/all
  int  listContainers(ContainerList&);  int getContainer(uint64_t id, ContainerInfo&);
  int  retention(); int reclaim(); int seal();
  std::string issueToken(const std::string& role);   // token store
};
}
```

REST adapter 与 `XTdbMachine` 均调用 **同一** `XtdbOps`，杜绝逻辑分叉。

---

## 5. 宿主进程模型：A 链接式 subvm（决策已定）

| 维度 | 取值 |
|---|---|
| 机制 | `xtdb_vm_lib` 链接进 `hostvm.bin`；`onDaemonStart` 调 `xtdb_vm_init()` 注册 `"xtdb"` VM 类型；`hostvm.xml` 配 `subvm` |
| worker | `process_host` `uv_spawn(getModulePath(), "work", --vmguid …)` ⇒ **重生的 `hostvm.bin work`** 子进程 |
| 参数/配置 | 经 **vmguid 管道 QUEFYVM 回查**（§2.4），配置在 `content` dblock |
| 守护 | HostVM 原生 spawn + exit_cb 重拉 |
| 隔离 | worker 为独立 OS 进程，tdb 崩溃不拖垮 HostVM daemon；但 `hostvm.bin` 体积含 `libxtdb`（代价，§12） |

**为何不选 B/C**：B（attach/外部注册）守护语义需额外验证、偏离 zmpc 既有范式；C（改 `zce_process` 支持 `exepath`）动公共框架、影响面大。A 与 `zmpc` 完全一致、改动最小、即刻可用。

**与现有 zmis 自注册的关系**：`xtdbd` 的 `--zmis-host` announce 仍保留用于 standalone 被发现；嵌入态则由 HostVM 直接托管，不依赖该 announce 路径。

---

## 6. ZVM 门面：`XTdbMachine`（tdb 侧唯一需新写的运行时代码）

### 6.1 类骨架（镜像 `ZfgwMachine`）

```cpp
// modules/tdb/server/include/xtdb_vm.h
#pragma once
#include <zce/zvm.h>
#include "xtdb_ops.h"
#include "server_config.h"
namespace xtdb::server {
using response_cb = zce::zvm::VirtualMachineStub::response_cb;

class XTdbMachine : public zce::zvm::Machine {
  ZCE_OBJECT_DECLARE;
 public:
  // content = QUEFYVM 下发的配置 payload（ServerConfig 的序列化），在此解析
  XTdbMachine(const std::string& vm_name,
              const zce::SmartPtr<zce::zvm::VirtualMachineStub>& stub_ptr,
              const zce::RefBlock& content);
  ~XTdbMachine() override;

  int  start() override;            // 解析 cfg_ → openDb → 拉起 REST+xds → 经 getEndpoints 备好端点
  void stop()  override;            // 反序优雅关停
  int  call_dblock(zce_int64, const std::string& method, zce::RefBlock&, int,
                   const response_cb&) override;

 private:
  int rpcGetStatus(XEmpty,const response_cb&);     int rpcGetEndpoints(XEmpty,const response_cb&);
  int rpcGetStats(XStatsReq,const response_cb&);    int rpcListContainers(XEmpty,const response_cb&);
  int rpcGetContainer(XContainerReq,const response_cb&);
  int rpcOpenDb(XOpenReq,const response_cb&);       int rpcCloseDb(XEmpty,const response_cb&);
  int rpcRetention(XEmpty,const response_cb&);       int rpcReclaim(XEmpty,const response_cb&);
  int rpcSeal(XEmpty,const response_cb&);            int rpcIssueToken(XTokenReq,const response_cb&);

  ServerConfig                cfg_;
  std::unique_ptr<XtdbOps>    ops_;
  zce::SmartPtr<RestServer>   rest_;
  zce::SmartPtr<DataServer>   data_;
  Endpoints                   endpoints_;     // rest/xds host:port + advertise + instance_name
  bool                        running_ = false;
};
}  // namespace xtdb::server
```

### 6.2 `call_dblock` 分发（与 fgw 一致的宏式分发）

```cpp
int XTdbMachine::call_dblock(zce_int64, const std::string& method, zce::RefBlock& in,
                             int, const response_cb& resp) {
  XTDB_RPC_DISPATCH("getStatus",      rpcGetStatus,      XEmpty);
  XTDB_RPC_DISPATCH("getEndpoints",   rpcGetEndpoints,   XEmpty);
  XTDB_RPC_DISPATCH("getStats",       rpcGetStats,       XStatsReq);
  XTDB_RPC_DISPATCH("listContainers", rpcListContainers, XEmpty);
  XTDB_RPC_DISPATCH("getContainer",   rpcGetContainer,   XContainerReq);
  XTDB_RPC_DISPATCH("openDb",         rpcOpenDb,         XOpenReq);
  XTDB_RPC_DISPATCH("closeDb",        rpcCloseDb,        XEmpty);
  XTDB_RPC_DISPATCH("retention",      rpcRetention,      XEmpty);
  XTDB_RPC_DISPATCH("reclaim",        rpcReclaim,        XEmpty);
  XTDB_RPC_DISPATCH("seal",           rpcSeal,           XEmpty);
  XTDB_RPC_DISPATCH("issueToken",     rpcIssueToken,     XTokenReq);
  if (resp) resp(ZVM_ERROR_INVALIDMETHOD, zce::RefBlock());
  return ZVM_ERROR_INVALIDMETHOD;
}
```

### 6.3 线程模型（关键）

- `Machine` 自带 **TaskQueue**（控制面 RPC 在此串行）；REST/xds 跑在 server_lib 的 reactor 线程（`handle_` 仅 Reactor 线程访问，见 `rest_server.h`）。
- 控制面 handler **禁止** 在 TaskQueue 线程直接碰 `handle_`：统一“**投递到 Reactor 线程** + 回调/future”。控制面均低频，正确性优先。

### 6.4 宿主侧接入（照 `zmpc`，无需自写 main）

tdb **不写** `main`/`initStub`/管道握手。仅需：

```cpp
// xtdb_vm_register.cpp（编入 xtdb_vm_lib）
ZCE_OBJECT_INSTANCE(XTdbMachine);
static zce::zvm::VirtualMachineRegister _xtdb_register("xtdb",
    [](const zdp_base::zvm_t& vm, const SmartPtr<VirtualMachineStub>& stub, zce::RefBlock& content)
       -> SmartPtr<Machine> { return new XTdbMachine(vm.vmname, stub, content); });
extern "C" int xtdb_vm_init() { (void)&_xtdb_register; return 0; }   // 防链接器 GC
```

HostVM 侧改动（与 `zmpc_init` 完全对称）：

```cpp
// hostvm_service.cpp
extern "C" int xtdb_vm_init();          // 声明
...                                     // onDaemonStart 内：
ret = xtdb_vm_init();                   // 触发注册
```
```cmake
# hosts/HostVM/CMakeLists.txt
target_link_libraries(hostvm.bin PRIVATE zmpc xtdb_vm_lib)   # 增加 xtdb_vm_lib
```

---

## 7. 控制面 RPC 协议

### 7.1 新增 `server/xtdb_vm.ptl`（zGen 生成 `_proto.h`/`_pack.{h,cpp}`，遵循 ZDL_PROTOCOL.md）

定义 `XEmpty / XStatusRes / XEndpoints / XStatsReq / XStatsRes / XContainerReq / XContainerInfo /
XOpenReq / XTokenReq / XTokenRes`（字段 snake_case，结构 PascalCase）。

### 7.2 方法表（均委托 `XtdbOps`，与 REST 一一对应避免分叉）

| RPC method | 角色 | 委托 | 对应 REST |
|---|---|---|---|
| `ping` | any | 存活探测 | `GET /health` |
| `getStatus` | readonly | `ops.dbInfo`+uptime | `GET /api/v1/status` |
| `getEndpoints` | readonly | `endpoints_` | （新增） |
| `getStats` | readonly | `ops.stats(kind)` | `GET /api/v1/stats[/*]` |
| `listContainers` | readonly | `ops.listContainers` | `GET /api/v1/containers` |
| `getContainer` | readonly | `ops.getContainer` | `GET /api/v1/containers/:id` |
| `openDb` | admin | `ops.openDb` | `POST /api/v1/db/open` |
| `closeDb` | admin | `ops.closeDb` | `POST /api/v1/db/close` |
| `retention` | admin | `ops.retention` | `POST /api/v1/maintenance/retention` |
| `reclaim` | admin | `ops.reclaim` | `POST /api/v1/maintenance/reclaim` |
| `seal` | admin | `ops.seal` | `POST /api/v1/maintenance/seal` |
| `issueToken` | admin | `ops.issueToken(role)` | （新增） |

数据面 `write/query/flush` **不进 RPC 表** —— 前端拿 `getEndpoints`+`issueToken` 后 **直连 xds**。
错误码复用 `xtdb_api` 的 `ERV_*` 与 mesh 的 `ZVM_ERROR_*`；统一 `sendResponse(resp, errcode, payload)` 返回。

---

## 8. 端点发现与鉴权（前端对接契约）

### 8.1 发现时序

```
前端 ──TCP──► HostVM            # ProjectHost = Solution.ServiceEndpoint{host,port,storm_port}
前端 ──RPC──► 枚举 subvm (vmname 形如 "xtdb*")
前端 ──RPC[getEndpoints]──► XTdbMachine  ◄── { xds_host, xds_port, rest_host, rest_port, instance_name }
前端 ──RPC[issueToken(role)]──► XTdbMachine ◄── { token, expire_at }
前端 ──xds 直连(xds_host:xds_port)──► AUTH(E_MSG_AUTH_REQ, token) → write/query
```

- **控制口** 由框架自动上报（§2.4 第 4 点）；**REST/xds 口** 由 `getEndpoints` 自报（含 `--advertise-addr` 语义）。

### 8.2 鉴权统一

- xds 首帧 `E_MSG_AUTH_REQ` 需 token（`xds.ptl`）；REST 用 Bearer+role（`rest_server.h` `checkAuth/hasRole`）。
- **单一来源**：`issueToken` 委托 `XtdbOps` 颁发 **scoped+短期 TTL** token，前端同时用于 xds 与 REST。
- 信任边界：`issueToken` 仅对 mesh 内（HostVM 已鉴权会话）可达；token 设 TTL。

---

## 9. 日志与事件

| 通道 | 内容 | 机制 | 落点/消费者 |
|---|---|---|---|
| **logcollector** | 批量 ZLOG 行 | UDP datagram（`logcollector_info.bind_port`） | HostVM logcollector → 落盘 + `keepdays` 轮转 |
| **Storm** | 低频事件/错误：db open/close、retention 完成、磁盘水位、引擎异常 | Storm publish（mesh `stormport`） | 前端 `InstanceStormClient` 实时订阅 |

- 嵌入态 worker 的 ZLOG sink 指向 HostVM logcollector 的 UDP 口；standalone 仍写本地文件（不变）。
- 约定：**Storm 只走事件**；高频数据点 **不** 经 Storm（前端 live tail = xds 轮询 query）。

---

## 10. 配置与部署

### 10.1 HostVM 侧改动（小，照 `zmpc`）

1. 构建：`hostvm.bin` 链接 `xtdb_vm_lib`（`CMakeLists` + `libxtdb_vm.vcxproj` 引用）。
2. 代码：`onDaemonStart` 增 `xtdb_vm_init();`（`hostvm_service.cpp`，与 `zmpc_init` 并列）。
3. 配置：`hostvm.xml` 增 `subvm`：
   ```xml
   <subvm vmtype="xtdb" vmname="xtdb01" vmpath="(提示,可填 tdb 标识)" vmaddr="127.0.0.1" vmport="0"/>
   ```
   - `vmport="0"` → 控制口由框架自动分配并上报（§2.4）。
   - tdb 私有配置（data-dir/ports/retention/tokens）经 **VM 配置 payload**（`content` dblock / `uploadVM`）或 **VM home dir 配置文件**（`stub->vmHomeDir(vm)`）下发；`XTdbMachine` 构造时从 `content` 解析为 `ServerConfig`。
   - **端口模型**：`vmport`=控制口（框架管）；`rest_port`/`data_port(xds)` 由 tdb 自绑并经 `getEndpoints` 上报。

### 10.2 standalone 不变

```
xtdbd --data-dir /data/xtdb --port 8080 --data-port 9090 [--zmis-host ip:22500 --advertise-addr ...]
```

---

## 11. 开发计划（分阶段）

> 估时为相对粗估（理想人日）。

### P0 — 重构 Ops 门面（不改行为）  ~1.5d
抽 `XtdbOps`，REST handler 改调门面。
**验收**：`xtdbd` 行为不变、`test_rest_api` 全绿、`xtdbd` 仍不链新库。

### P1 — `XTdbMachine` + 注册 + 链入 HostVM  ~3d
- 新增 `xtdb_vm.{h,cpp}`、`xtdb_vm_register.cpp`（`VirtualMachineRegister("xtdb")`+`xtdb_vm_init`）。
- 新增 `xtdb_vm_lib` 目标（CMake + `libxtdb_vm.vcxproj`），落实 §4.2 硬约束。
- HostVM：链接 `xtdb_vm_lib` + `onDaemonStart` 调 `xtdb_vm_init()`；`hostvm.xml` 配 subvm。
- `XTdbMachine` 从 `content` 解析 `ServerConfig`；`start()` openDb+REST+xds；实现 `ping`/`getStatus`。
- **验收**：HostVM 启动后自动拉起 `xtdb01`（重生 `hostvm.bin work`）；`hostctrl` 可 `list` 到；
  `ping`/`getStatus` 通；kill worker 后 HostVM **自动重拉**（守护验证）。

### P2 — 端点发现 + token  ~2d
`getEndpoints`/`issueToken`；端点自报；token TTL。
**验收**：独立 xds client 仅凭“mesh 发现的 addr + 颁发的 token”跑通 `write`+`query`。

### P3 — 控制面其余 RPC + 一致性测试  ~2.5d
`getStats/listContainers/getContainer/openDb/closeDb/retention/reclaim/seal` + **REST↔RPC 一致性测试**。
**验收**：方法表全过；线程归属（§6.3）无竞争（审查/tsan）。

### P4 — 日志/事件  ~1.5d
ZLOG→logcollector（嵌入态）；Storm 事件发布 + 订阅 smoke。
**验收**：logcollector 落盘见 tdb 日志；订阅端收到 db open/retention 事件。

### P5 — 双模 CI + 文档 + 故障注入  ~1.5d
CI：独立构建 `xtdbd` 与 `xtdb_vm_lib`；符号校验“`xtdbd` 不含 vm 符号”。故障注入：worker 崩溃→HostVM 重拉。
**验收**：双目标绿；守护/隔离达标；更新 README/部署文档。

### 里程碑
| 里程碑 | 含 | 退出标准 |
|---|---|---|
| M1 可守护 | P0+P1 | HostVM 拉起+重拉+ping 通 |
| M2 可使用 | P2+P3 | 前端可发现+鉴权+数据/控制全通 |
| M3 可交付 | P4+P5 | 日志/事件归集 + 双模 CI + 文档 |

---

## 12. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| `libxtdb` 链入 HostVM → 二进制变重/单体化 | 中 | 接受（zmpc 同此）；如后续在意，再走模型 C（独立 exe，改 `zce_process` 支持 `exepath`） |
| worker=重生 hostvm.bin，tdb 故障域 | 中 | 进程级隔离仍在（独立 OS 进程），daemon 不受影响；崩溃由 exit_cb 重拉 |
| 单 `vmport` 不含 REST/xds 口 | 中 | 控制口框架自报；REST/xds 经 `getEndpoints` 自报（支持端口 0） |
| token 分发信任边界 | 中 | `issueToken` 限 mesh 内 + scoped + 短 TTL |
| 控制面线程归属（TaskQueue vs Reactor） | 中 | handler 一律投递到 Reactor 访问 `handle_`（§6.3） |
| standalone 回归被破坏 | 中 | CI 双目标 + “`xtdbd` 不链 `xtdb_vm_lib`”硬约束 + 符号校验 |
| 静态注册被链接器 GC | 中 | 显式 `xtdb_vm_init()`（logcollector/ident 已有前车之鉴） |
| REST/RPC 逻辑漂移 | 中 | **单一 `XtdbOps` 实现** + REST↔RPC 一致性测试 |
| 配置 `content` 下发格式未定 | 低 | P1 定义 `ServerConfig` 的 ptl 序列化；空 `content` 时回退 VM home dir 配置文件 |

---

## 13. 附录

### 13.1 文件 / 目标清单

**新增**
- `modules/tdb/server/include/xtdb_ops.h`，`server/src/xtdb_ops.cpp`
- `modules/tdb/server/include/xtdb_vm.h`，`server/src/xtdb_vm.cpp`，`server/src/xtdb_vm_rpc.cpp`，`server/src/xtdb_vm_register.cpp`
- `modules/tdb/server/xtdb_vm.ptl`（+ 生成 `xtdb_vm_proto.h`/`xtdb_vm_pack.{h,cpp}`）
- CMake 目标 `xtdb_vm_lib`；Windows `libxtdb_vm.vcxproj`

**修改**
- `modules/tdb/server/src/rest_server.cpp`（改调 `XtdbOps`，零行为变化）
- `modules/tdb/server/CMakeLists.txt`（新增 `xtdb_vm_lib` + 硬约束）
- `hosts/HostVM/hostvm/hostvm_service.cpp`（声明 + 调 `xtdb_vm_init()`）
- `hosts/HostVM/CMakeLists.txt`（链接 `xtdb_vm_lib`）+ HostVM `.vcxproj`
- `hostvm.xml`（增 `subvm`）

### 13.2 关键源引用（已核实）

- 单体宿主链接 + init：`hosts/HostVM/CMakeLists.txt:200`、`hosts/HostVM/hostvm/hostvm_service.cpp:7-11,155-178`
- subvm 守护：`hostvm_service.cpp:81`
- **子进程 argv**：`libsrc/libzce/core/zce_process.cpp:286-300`（`exepath=getModulePath` `:700/1428/683/281`）
- **work 子命令解析**：`libsrc/libzce/core/zce_service.cpp:204-218`
- **QUEFYVM 管道回查**：`zce_service.cpp:1049-1070,1094-1116`、`zce_process.cpp:1606-1608`
- **控制口自动上报**：`zce_service.cpp:1098-1113`
- attach/外部注册（模型 B 备选）：`zce_process.cpp:244,1191`
- VM 基类/Stub：`include/zce/zvm.h`、`libsrc/libzce/zvm/zvm_base.h`
- VM 参考实现：`hosts/HostVM/hostvm/logcollector_vm.cpp`、`modules/fgw/src/zfgw_vm.h`、`modules/fgw/src/zfgw.cpp:101`
- tdb 现有 server / zmis 自注册：`modules/tdb/server/{CMakeLists.txt,src/main.cpp:155,183,include/rest_server.h,xds.ptl}`

### 13.3 术语
| 术语 | 释义 |
|---|---|
| zmis | HostVM mesh 服务名（`hostvm_config.ptl` 默认 `vmname="zmis"`） |
| ZVM / Machine | zce 虚拟机框架 / VM 基类（自带 TaskQueue） |
| subvm | HostVM 拉起并守护的子进程型 VM；模型 A 下 worker=重生 `hostvm.bin work` |
| QUEFYVM | 子进程经 vmguid 管道向父进程回查 `zvm_t`+配置的握手消息 |
| Storm | zce 广播/发布订阅（前端 `InstanceStormClient` 消费） |
| xds | xTdb 二进制数据面协议（`server/xds.ptl`） |
