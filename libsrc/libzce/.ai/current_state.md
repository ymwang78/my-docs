# libzce 当前状态报告

> 本文档记录截至 **2026-04-30** 时点 `libzce` 仓库的当前状态：分支/提交、模块完成度、构建/测试覆盖、依赖、运行平台、主要风险与近期演进方向。
> 仓库根：`D:/Github/cxxproj/libsrc/libzce`，分支：`master`（与 `origin/master` 一致）。

---

## 1. 仓库快照

| 项目 | 值 |
| ---- | -- |
| 当前分支 | `master`（同步 `origin/master`，工作树干净，仅有未跟踪 `docks` 软链） |
| 最近提交（HEAD） | `cb66d0b 2026-04-28 优化数据传输协议的压缩处理与日志记录` |
| 一周内提交 | 4 笔（zds float matrix、zua stack、win32 编译兼容、压缩处理优化） |
| 三个月内提交 | 60+ 笔，涉及 ZVM/ZDB/Reactor/Logger/平台兼容 |
| 主要语言 | C++17（含少量 C：sqlite3、secp256k1、rsaref；少量内嵌 Lua/Python C 代码） |
| 编码约定 | UTF-8 with BOM（`.cursor/rules/cpp-utf8-bom.mdc` 强制）|
| License | 仓库根 `LICENSE.txt`（待补 SPDX 标识） |

---

## 2. 模块完成度

| 模块 | 状态 | 说明 |
| ---- | ---- | ---- |
| `core/`（Reactor/Service/Allocator/IStream/Process/...） | **稳定（生产已用）** | API 较稳定；仍有少量平台兼容补丁（macOS、Win32）持续合入 |
| `log/`（zlog/Logger） | **稳定** | 日志切分 / 远程日志 / C++ 流式，覆盖度高 |
| `text/`（HTTP/URI/TextStream） | **可用** | HTTP 服务端/客户端 + WebSocket 已经投产；`on_prepare_nextres` 仍是空 todo |
| `xml/`（zxml） | **轻量可用** | 仅做配置解析与简单序列化 |
| `mat/`（数值矩阵） | **演进中** | 4 月新增 `add mat` / `cmake add mat` / 浮点矩阵 zds 支持 |
| `exp/`（whp/rtp/nano） | **实验** | 部分模块未包含在 CI；rtp 已被实际使用 |
| `zdp/`（ZDP+ZDS+BSON+Storm） | **稳定** | RFC 写在 `zdp/README.md`；通过 zGen 生成代码 |
| `zwt/`（链上工具） | **稳定** | tron 地址、椭圆曲线签名、keccak |
| `zvm/`（VM 框架） | **核心稳定** | `Machine` / `RpcStream` / `Proxy` / `VirtualMachineStub` 均已就位 |
| `zvm/zua/`（Lua VM） | **稳定** | Lua 5.4，可选 5.5；4 月修复了 zua_stream 栈管理 |
| `zvm/zpy/`（Python VM） | **演进中** | pybind11 接管原手写绑定（3 月迁移），4 月修复 GIL/子解释器问题 |
| `zvm/zcc/`（C VM 示例） | **示例级** | `FileSystemMachine` 示范，最小化 |
| `zvm/zjs/`（JS VM） | **未启用** | 文件存在但 CMake 注释，依赖 quickjs-ng 未引入 |
| `zdb/zdb_rdb*` | **稳定** | 通用接口 + 模板 ORM；@todo 注释多处需要审计 |
| `zdb/sqlite/` | **稳定** | 内嵌 sqlite3.c，无外部依赖 |
| `zdb/zdb_rdb_pgsql/zdb_ecpg` | **稳定** | 4 月修复 Win32 链接 (`pragma comment`) |
| `zdb/zdb_redis` | **稳定** | hiredis 客户端 |
| `zdb/zdb_rdb_mysql.cpp` | **不参与构建** | `ZCE_ZDB_MYSQL=0`，CMake 不生成 |
| `rsa/`（RSAREF/MD2/MD5/DES） | **legacy** | 仅供历史业务使用，应迁移到 OpenSSL |
| `gtest/` | **基本覆盖** | 16 个测试文件（见下表），需要 BUILD_TESTS=ON |
| `core/zce_service` | **稳定，但依赖 CLI11** | 找不到 CLI11 时整个 service 文件被剔除 |

---

## 3. 测试覆盖

`gtest/` 目录的 16 个 cpp（启用 `BUILD_TESTS=ON` 时构建为可执行 `libzce_testExe`）：

| 测试文件 | 覆盖范围 |
| -------- | -------- |
| `libzce_test.cpp` | gtest 主入口 |
| `test_zce_allocator.cpp` | Chunk / Dynamic 分配器 |
| `test_zce_any.cpp` | `zce::Any` 容器 |
| `test_zce_api.cpp` | `zce_api`（编解码、压缩、时间） |
| `test_zce_array.cpp` | 自研 Array 容器 |
| `test_zce_convertor.cpp` | 转换器（Any/Json） |
| `test_zce_hash.cpp` | hash/sha 系列 |
| `test_zce_mat.cpp` | 矩阵 zds 序列化 |
| `test_zce_reactor.cpp` | Reactor 启停、跨线程 delegate、定时器 |
| `test_zce_task_future.cpp` | `Scheduler::performFuture`、`TaskResult` |
| `test_zce_uri.cpp` | URI 解析 |
| `test_zce_zdp.cpp` | ZDP 报文 / ZDS 序列化 |
| `test_zvm.cpp` | VM Stub / Machine 注册 |
| `test_zvm_listen_schema.cpp` | listenSchema(`tcp://` / `pipe://`) |
| `test_zvm_subinterpreter.cpp` | Python 子解释器隔离 |
| `zdb_rdb_demo.cpp` | 关系型数据库样例（非自动化用） |

> 没有 CI 配置文件（`.github/workflows`）入仓，测试目前依赖开发者本地运行。

---

## 4. 构建状态

### 4.1 平台支持

| 平台 | 构建状态 | 说明 |
| ---- | -------- | ---- |
| Windows x64（vcpkg `x64-windows-static-md`） | ✅ 持续维护 | 依赖：boost / libuv / nlohmann_json / uriparser / minizip / bzip2 / expat / postgresql / hiredis / pybind11 |
| Linux（Ubuntu/Debian apt + pkg-config） | ✅ 持续维护 | 依赖通过 `pkg-config`：libuv / liburiparser / libpq+libecpg；其余 apt：libbz2-dev / lua5.4 / python3.13 |
| macOS（Apple Silicon Homebrew） | ✅ 4 月修复 | `cdc9835 Fix libzce macOS build compatibility`；硬编码 `/opt/homebrew/...` 路径，注意 Python/Lua 版本 |
| Android（`core/android`） | ⚠️ 仅有源 | CMake 未导出 Android target，需要业务层自行集成 |

### 4.2 关键 CMake 选项

```cmake
option(BUILD_SHARED_LIBS "..." OFF)     # 静态库（推荐）
option(BUILD_TESTS       "..." OFF)
option(ENABLE_ZVM        "..." ON)      # 关闭后所有 VM 子模块禁用
option(ENABLE_ZDB_SQLITE "..." ON)
option(ENABLE_ZDB_PGSQL  "..." ON)
option(ENABLE_ZDB_REDIS  "..." ON)
option(ENABLE_ZDB_COMMON "..." OFF)     # 任一 ENABLE_ZDB_* 开启时自动 ON
```

### 4.3 已知构建注意事项

1. CLI11 未安装时 `core/zce_service.cpp` 被剔除，但库仍可生成；调用 `zce::Service` 会链接报错。
2. `BUILD_SHARED_LIBS=ON` 未在 CI 验证，导出表不全（多内嵌 C 源码且无 visibility 注解）。
3. 平台头路径硬编码（`/usr/include/python3.13`、`/usr/include/lua5.4`、`/opt/homebrew/...`）；升级 OS 时需要手动修改。
4. PostgreSQL/ecpg、Boost CMP0167（Boost 1.70+ CONFIG 模式）较新，老 CMake 需升级。

---

## 5. 依赖矩阵（运行时/构建时）

| 依赖 | 用途 | 是否必需 |
| ---- | ---- | -------- |
| Boost | header-only（algorithm/optional/string_view fallback） | 必需 |
| libuv | Reactor/IO 核心 | 必需 |
| uriparser | URI 解析 | 必需 |
| nlohmann_json | JSON / MCP / 协议互转 | 必需 |
| bzip2 | ZDP/HTTP 压缩 | 必需 |
| expat | XML 解析（zxml） | 必需 |
| OpenSSL | `ZCE_SUPPORT_SSL` / 哈希 / 随机 / SocksTLS | 推荐 |
| minizip | zwt / 压缩文件 | 必需（Win32），可选（Linux） |
| libpq + libecpg | PostgreSQL 关系型 + 嵌入式 SQL | 启用 PG 时必需 |
| hiredis | Redis 客户端 | 启用 Redis 时必需 |
| Lua 5.4（推荐 5.5） | ZuaMachine | 启用 ZVM 时必需 |
| Python ≥ 3.12 | ZpyMachine（Linux 默认 3.13，Windows 默认 3.12） | 启用 ZVM 时必需 |
| pybind11 | Python 绑定 | 启用 ZVM 时必需 |
| CLI11 | `zce::Service` 命令行解析 | 强烈推荐 |
| sqlite3 | 内嵌（zdb/sqlite/sqlite3.c） | 自带 |
| secp256k1 | 内嵌（zwt/secp256k1） | 自带 |
| GoogleTest | 单元测试 | 仅 `BUILD_TESTS=ON` 需要 |

---

## 6. API/ABI 稳定性

- 头文件位于 `include/zce/`，命名空间 `zce::` / `zce::zdp::` / `zce::zvm::` / `zce::zdb::`。
- **API 稳定**（不会随便改名）：`Object/SmartPtr`、`Reactor`、`Service`、`Tcp/Udp/Pipe/Tty`、`zlog/Logger`、`Allocator/RefBlock/BlockPool`、`zce_init/fini/_pyenv`。
- **API 还在演进**（近 6 个月有改动）：
  - `zvm::VirtualMachineStub::listenSchema`（3 月新增）
  - `Reactor::scheduleTimer(taskqueue, …)`（3 月新增）
  - ZpyMachine 内部从 PyZObject 迁移到纯 pybind11（3-4 月）
  - HTTP 流压缩 / chunked 编码近期持续微调（最近一周改动集中在此）。
- ABI 暂不保证（静态库为主），二进制升级需重新编译所有依赖方。

---

## 7. 运行时表现摘要

> 这部分基于源码静态分析与提交历史回溯，未跑性能基准。

| 维度 | 当前估算 |
| ---- | -------- |
| Reactor 单实例吞吐 | 单线程 libuv loop，已有"100k tasks"上限保护；建议每实例不超过 5w QPS。 |
| Worker 线程模型 | `Scheduler::active(N)`，N 默认无；典型 1+CPU 核数 |
| 内存模型 | 引用计数对象 + Allocator 池；`OBJECT_MONITOR` 默认开启，会有少量计数开销 |
| 日志 | 同步写文件；`zlog_setremote` 开启 UDP/TCP 异步上报 |
| ZVM 调度 | 每个 `Machine` 使用 `TaskQueue` 串行执行，避免脚本 GIL 冲突 |
| 子进程 IPC | 命名管道 + ZDP；每秒 timer 心跳 |
| 数据库连接 | Redis 使用 TLS 线程局部缓存；SQLite/PG 由业务管理 |

---

## 8. 风险点（紧急关注）

> 2026-04-30 修复批次已合入；此处列出当前仍未解决的高优先级风险。

剩余高优先级：

1. `ZpyMachine` 在 Python 3.13/OpenSSL 3 组合下的回归测试不充分（**P0 Risk**，需要实际运行验证）。
2. 各 VM（Lua/Python/CC）重复的 dispatch 代码尚未抽象统一（**P1 Tech-Debt**）。
3. `BUILD_SHARED_LIBS=ON` 与 `Service` 依赖 CLI11 等构建分支缺乏 CI 验证（**P1 Build**）。
4. `OBJECT_MONITOR` 在 release 默认开启带来轻量开销（**P2 Risk**）。

已修复（见 `known_issues.md` 中 `[Fixed 2026-04-30]` 标签）：

- `TaskDelegator::_delegateFuture` "unknow buggy"；新增 `delegateFuture` 返回 `std::future`，并修复 `delegate(bwait=true)` 提交失败时永久卡死的 bug。
- `zdb_rdb.h::select_byprop(std::vector<T>&, ...)` 向量版只取首行的 bug。
- `Reactor::stop` 在 reactor 自身线程调用时自杀式 join 导致死锁；同时 `Reactor::delegate_delay` 在未 start 场景下的 null 解引用。
- `Acceptor::block_dict_` 新增 `purgeExpiredBlocks()` + 机会性清理，避免长期运行内存膨胀。
- DNS 缓存 TTL 可配置 / 可清空（`Reactor::setDnsCacheTTL` / `clearDnsCache`）。
- `HttpStream::on_prepare_nextres` 真实实现（keep-alive 下第二个响应复用同一连接）。
- `RpcStream` 版本协商过低时主动 `close()`；未知 msgmid 对偶数 REQ 尽力回 `MSG_RPCCALL_RES{ ZCE_ERROR_INVALID }`，对端不再只能等超时。

---

## 9. 文档清单

| 文档 | 位置 | 用途 |
| ---- | ---- | ---- |
| `CLAUDE.md` (项目) | `libsrc/libzce/CLAUDE.md` | AI Agent 工程规范 |
| `CLAUDE.md` (仓库根) | `cxxproj/CLAUDE.md` | 仓库级总览（含 libzce、ctl、frontend 等） |
| `LIBZCE.md` | `cxxproj/LIBZCE.md` | libzce 库使用指南 |
| `README.md` | `libsrc/libzce/README.md` | 设计原则与模块概览 |
| `zdp/README.md` | `libsrc/libzce/zdp/README.md` | ZDS RFC-001 |
| `ZuaAPI.md` / `ZuaAPI_en.md` | `libsrc/libzce/zvm/zua/` | Lua 侧 API |
| `docs/ai/architecture.md` | 本目录 | 整体架构（本次新增） |
| `docs/ai/api.md` | 本目录 | 关键 API 索引（本次新增） |
| `docs/ai/known_issues.md` | 本目录 | 已知问题与技术债（本次新增） |
| `docs/ai/current_state.md` | 本目录 | 本文件 |

---

## 10. 近 30 天关键动作摘要

| 日期（2026） | 主题 | 备注 |
| ---- | ---- | ---- |
| 04-30 | P0/P1 批量修复（见 `known_issues.md`） | 工作树改动，未提交 |
| 04-28 | ZDP 压缩处理 + 日志兼容性优化 | HEAD |
| 04-26 | ZDS 浮点矩阵支持 | `mat/` 与 `zdp/zds_*` 联动 |
| 04-24 | Zua 流处理 Lua 栈管理 | `zvm/zua/zua_stream.cpp` |
| 04-24 | Win32 ECPG/PG 链接修复 | `pragma comment(lib, …)` |
| 04-24 | `.gitignore` 整理 | 加入 `bin/`、`obj/`、`docs/` 等 |
| 04-19 | 日志级别调整 | `log/zce_log.cpp` |
| 04-18 | testpy 添加 / pybind11 bug 修复 | `gtest/test_zvm_subinterpreter.cpp` |
| 04-15 | Pipe + crash 修复 | `zce_handler.cpp` |
| 04-12 | macOS mac_addr 修复 | `core/linux/zce_api_unix.cpp` |
| 04-11 | python path、py init、env 修复 | `core/zce_api.cpp` |
| 04-06 | log fix | |
| 04-02 | tests fix / compile fix | |
| 03-31 | 弃用 PyZObject，统一到 pybind11 | `b52729d` 起一系列 |
| 03-28 | `Reactor::scheduleTimer` 增加 TaskQueue 参数 | |
| 03-23 | comp（综合提交） | |
| 03-17 | mat / Lua 5.5 | `40a4460` 升级 lfs，`426ffa8` lua_5.5 |
| 03-16 | `zvm: listenSchema` URI API | `83cd939` |
| 03-09 | 增加 `scheduleTimer` | |
| 03-07 | Reactor inplace 模式 | |
| 03-01 | AI Agent 项目设置优化 + 修复测试 | |

---

## 11. 短期建议路线（结合 known_issues）

1. **修复 P0**：`select_byprop` 向 vector 的版本、`_delegateFuture`、ZpyMachine 在 Python 3.13 下的回归。
2. **CI 入仓**：增加 `.github/workflows`（Windows MSVC + Ubuntu LTS + macOS arm64），跑 `BUILD_TESTS=ON`。
3. **CMake 现代化**：用 `find_package(Python3 / Lua / hiredis)` 替换硬编码包含路径，把 OS 升级风险降下来。
4. **抽象 VM dispatch**：让 ZuaMachine/ZpyMachine 共享一份 `dispatchMethod` 模板，新语言（zjs/zcc）实现成本下降。
5. **HTTP 客户端 keep-alive**：补完 `on_prepare_nextres`，并做大文件 chunked 上行的回归。
6. **内存监控**：把 `OBJECT_MONITOR` 改成 release 默认 OFF，提供独立 `enable_object_monitor()` 运行时开关。
7. **legacy rsa 隔离**：把 `rsa/` 模块拆成可选 `ENABLE_RSA_LEGACY`，默认 OFF，避免新业务误用。
8. **文档同步**：让 `README.md` / `CLAUDE.md` / `LIBZCE.md` / `docs/ai/*.md` 互相 cross-link，并约定统一更新规则。

---

## 12. 联系/责任

- 主线开发者：参见 `git log --format='%an'` 输出，主要贡献者为内部团队。
- AI 工具协作：本仓库已配置 `.cursor/rules/` 指导 AI 写 C++（UTF-8+BOM、命名规范、类型 trait 等）。
- AI 文档（本目录）：在每次较大的架构调整后请同步更新 `architecture.md` 与 `current_state.md`，并在 `known_issues.md` 中追加/勾掉条目。

---

> 如果在阅读本文档时发现与代码不符，请优先以最新代码为准，然后回头修订本文件。
