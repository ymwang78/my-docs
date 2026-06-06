# 订阅时间（sample_timespan_msec）设计与使用说明

本文档描述 `libidh` 中**订阅时间**参数 `sample_timespan_msec` 的完整语义、两种工作模式、缓存窗口节流机制，以及对应的接口使用方式。

---

## 1. 背景与问题

`libidh` 的组（group / batch）读取默认采用 **OPC 订阅模式**：

- OPC 服务器（UA 或 DA）按订阅周期（publishing / update rate）周期性地把变化的数据推送给客户端；
- 客户端把推送到的值缓存在每个位号（tag）上；
- `idh_group_readvalues()` 返回的是**缓存值**，即「上一个订阅周期推送的数据」。

**问题**：如果在订阅周期中间去读，会读到上一个周期的旧数据。在某些对实时性要求高的场景（例如读后立即依据该值控制、或周期远大于业务节拍），这个延迟是不可接受的。

**解决思路**：允许把**订阅时间设置为 0** 表示「不订阅」，此时每次组读改为**同步读**（直接向 OPC 服务器请求当前值），保证拿到实时数据；同时用一个**缓存窗口**对高频快读做节流，避免短时间内大量请求打到 OPC 服务器。

---

## 2. 参数定义

订阅时间通过创建数据源时的 `sample_timespan_msec` 参数指定：

```c
LIBIDH_API idh_source_t idh_source_create(
    idh_handle_t handle,
    IDH_RTSOURCE source_type,
    const char*  source_schema,
    int          sample_timespan_msec,   // 订阅时间（毫秒）
    unsigned int source_flag);
```

| 取值 | 含义 | 模式 |
|------|------|------|
| `> 0` | 订阅周期（毫秒） | **订阅模式**（subscribe） |
| `== 0` | 不订阅 | **同步读模式**（sync read） |

---

## 3. 两种工作模式

### 3.1 订阅模式（`sample_timespan_msec > 0`）

保持原有行为，**本次改动不影响**：

- **UA**：`doInit()` 调用 `createSubscription()`，`requestedPublishingInterval = sample_timespan_msec`；为每个位号建立 MonitoredItem，`samplingInterval = sample_timespan_msec`。数据变化由 `_dataChangeCallback` 推送并写入 `tag->tag_idh` 缓存。
- **DA**：以 `sample_timespan_msec` 作为组的 update rate，通过 `IOPCDataCallback` 回调接收变化推送。
- 定时器 `handleSampleTimer()` 每 100ms 触发一次，按 `sample_timespan_msec` 边界做：清理无引用位号、UA 的 `run_iterate`/重连、DA 的坏点重订阅。
- `idh_group_readvalues()` → `readSubscribedRealValues()` 返回**缓存值**。

### 3.2 同步读模式（`sample_timespan_msec == 0`）

- **不建立订阅**：
  - UA：`doInit()` 跳过 `createSubscription()`，`is_support_subscribe_ = false`。
  - DA：强制 `is_support_subscribe_ = false`，跳过 `IOPCDataCallback` 的 `Advise`。
- **不做后台周期轮询**：`handleSampleTimer()` 仍运行（用于连接维护、清理无引用位号），但不再周期性地批量读取所有位号。
- **读时同步读 + 缓存窗口节流**（见第 4 节）：组读时直接向 OPC 同步读取「过期」的位号，并把结果写入缓存。

> 位号缓存（`tag->tag_idh`）在两种模式下都保留，组读时引用同一个共享位号对象。

---

## 4. 缓存窗口节流（sync cache window）

同步读模式下，为避免高频快读对 OPC 服务器造成压力，引入**缓存有效窗口**：

- 每个位号记录**本地最后刷新时间** `local_update_time`（微秒，`zce_timestamp_now()`，初值 0 表示从未刷新）。
- 每次同步读成功写入 `tag_idh` 后，更新 `local_update_time = 现在`。
- 组读时对每个位号判断：

  ```
  if (local_update_time != 0 && now - local_update_time <= window)
      使用缓存值；            // 命中窗口，不读 OPC
  else
      加入本次同步读列表；     // 过期，需要刷新
  ```

- 仅对**过期**位号发起一次合并的同步读；新鲜位号直接用缓存。

### 4.1 窗口大小

- **默认 100ms**，可运行时设置。
- `window == 0` 表示每次组读都必读 OPC（不节流）。

### 4.2 时间戳说明

- `local_update_time` 是**本地刷新时刻**，与 `tag_idh` 内携带的「服务器采样时间戳」**不同**：前者用于本地节流，后者表示数据在服务器侧的时间。两者分开存储，互不影响。

---

## 5. 接口使用

### 5.1 创建同步读数据源

```c
// 订阅时间设为 0 -> 同步读模式
idh_source_t src = idh_source_create(
    h, IDH_RTSOURCE_UA, "opc.tcp://127.0.0.1:4840/",
    /*sample_timespan_msec=*/0,
    IDH_RTSOURCE_FLAG_NONE);
```

### 5.2 设置缓存窗口

```c
// 运行时调整同步读缓存窗口（毫秒），默认 100ms；0 = 每次必读
LIBIDH_API int idh_source_set_sync_cache_msec(idh_source_t source_id, int msec);

// 查询当前窗口（毫秒）；返回 >=0 为窗口值，负值为错误码
LIBIDH_API int idh_source_get_sync_cache_msec(idh_source_t source_id);
```

示例：

```c
idh_source_set_sync_cache_msec(src, 50);   // 窗口 50ms
idh_source_set_sync_cache_msec(src, 0);    // 关闭节流，每次都读
int w = idh_source_get_sync_cache_msec(src);
```

> **写后一致性**：组写（`idh_group_writevalues`）成功后会把相关位号的 `local_update_time` 置 0，使下次组读强制重新同步读，避免窗口内返回写入前的旧值。

### 5.3 组读（与订阅模式一致）

读取接口不变；模式差异对调用方透明：

```c
idh_group_t g = idh_group_create(src, "g1");
long long handles[N];
idh_group_subscribe(g, handles, tags, N);   // 注册位号（同步读模式下仅登记，不建订阅）
idh_real_t values[N];
idh_group_readvalues(g, values, handles, N);// 同步读模式：窗口内命中缓存，否则同步读
```

### 5.4 Python 绑定

```python
src = idh.source_create(h, IDH_RTSOURCE.IDH_RTSOURCE_UA,
                        "opc.tcp://127.0.0.1:4840/",
                        sample_timespan_msec=0,            # 同步读模式
                        source_flag=IDH_RTSOURCE_FLAG.IDH_RTSOURCE_FLAG_NONE.value)
idh.source_set_sync_cache_msec(src, 100)                   # 设置窗口
```

---

## 6. 行为对照表

| 场景 | `sample > 0`（订阅） | `sample == 0`（同步读） |
|------|----------------------|--------------------------|
| 数据来源 | 订阅回调推送 | 组读时同步读 |
| 组读返回 | 缓存值（可能是上周期） | 实时值（过期则刷新） |
| 后台轮询 | 周期维护/重订阅 | 不做周期批量读 |
| 快读（窗口内多次） | 返回同一缓存 | 首次读 OPC，其余命中缓存 |
| OPC 压力 | 每订阅周期一次推送 | 最多每窗口一次/位号 |
| 窗口可调 | 不适用 | `idh_source_set_sync_cache_msec`，默认 100ms |
| 实时性 | 取决于订阅周期 | 高（窗口内）/ 实时（窗口外） |

---

## 7. 实现要点（开发参考）

| 位置 | 改动 |
|------|------|
| `IdhRtDataTag`（`IdhRtData.h`） | 新增 `zce_timestamp local_update_time`（本地刷新时间） |
| `IdhRtDataSourceBase`（`IdhRtData.h`） | 新增 `int sync_cache_span_msec_ = 100` + `setSyncCacheSpanMsec/syncCacheSpanMsec` |
| `idhCacheIsFresh`（`IdhRtData.h`） | 窗口判定的唯一来源(UA/DA共用), `inline bool idhCacheIsFresh(local_update_time, now, window_msec)`，便于单元测试 |
| `IdhRtDataSourceUA::doInit` | `sample==0` 跳过 `createSubscription()` |
| `IdhRtDataSourceUA::doReadTagSetValue` | 读后更新 `local_update_time` |
| `IdhRtDataSourceUA::doReadSubscribedRealValues` | 非订阅时按窗口合并同步读 |
| `IdhRtDataSourceUA::handleSampleTimer` | 有效周期清理；`sample==0` 不后台轮询 |
| `IdhRtDataSourceDA::ctor` / `initOPCDAInterfaces` | `sample==0` 禁用回调订阅 |
| `IdhRtDataSourceDA::doReadTagSetValue/doReadTagVecValue` | 读后更新 `local_update_time` |
| `IdhRtDataSourceDA::doReadSubscribedRealValues` | 非订阅时按窗口合并同步读 |
| `IdhRtDataSourceDA::handleSampleTimer` | 有效周期；`sample==0` 不后台轮询 |
| `libidh.cpp` / `include/idh/libidh.h` | 新增 `idh_source_set_sync_cache_msec` |
| `pyidh.py` | 新增 `source_set_sync_cache_msec` 封装 |

---

## 8. 测试

窗口策略已抽成 `idhCacheIsFresh`，在 `gtest/test_libidh_unit.cpp` 中做确定性单元测试（`SyncCacheWindow.*`，无需 OPC 服务器）：

- 从未刷新（`local_update_time==0`）→ 过期；
- 窗口内（含边界 `<=` 窗口）→ 命中缓存；窗口外 → 过期；
- 窗口 `<=0` → 永不节流（每次必读）；
- `IdhRtDataTag::local_update_time` 默认 0；
- `idh_source_set_sync_cache_msec` 对无效句柄返回错误码；对同步读源设置/清零/负值（按 0）均成功（需可用源，否则 `GTEST_SKIP`）。

> 该测试由 CMake `BUILD_TESTS=ON` 编入 `test_libidh_unit` 目标。

## 9. 兼容性

- 触发开关复用既有 `sample_timespan_msec` 参数，**不新增创建参数**；旧代码均传 `> 0`，行为不变。
- 订阅模式逻辑完全不受影响。
- 新增的 `idh_source_set_sync_cache_msec` 为可选接口，不调用时使用默认窗口 100ms。
