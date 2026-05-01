# libfgw 总体设计

**版本**：0.1.0  
**日期**：2026-04-22  
**作者**：ymwang78

---

## 1. 概述

### 1.1 目标

libfgw（Fixed-egress Gateway Library）的目标是：

- 提供**稳定、快速、固定出口**的数据传输通道
- 支持多链路聚合（UTP + TCP），通过多路并发传输提升带宽利用率和容错能力
- 对上层透明地提供类 SOCKS5 语义的代理能力
- 在网络抖动、丢包、链路切换等恶劣环境下保持低延迟和高可靠性

### 1.2 典型场景

| 场景 | 说明 |
|------|------|
| 出口固定的隧道代理 | 客户端通过 libfgw 经由固定出口 IP 访问目标服务 |
| 多路聚合加速 | 同时使用多条 UTP/TCP 链路提升吞吐量 |
| 网络环境恶劣的可靠传输 | 在高丢包率网络中利用 UTP 拥塞控制 + 重传机制保证可靠性 |

### 1.3 依赖

| 库 | 用途 |
|----|------|
| [libutp](https://github.com/bittorrent/libutp) | 基于 UDP 的可靠传输协议（μTP） |
| zce | 内部基础库，提供 `IStream`、`TcpStream`、事件循环等 |

---

## 2. 总体设计

### 2.1 分层设计

libfgw 采用三层架构：

```
┌──────────────────┐                    ┌──────────────────────────┐
│   InportService  │                    │     OutportService       │
│  （接受客户TCP） │                    │  （SOCKS5 层，数据通道上） │
└────────┬─────────┘                    └────────────┬─────────────┘
         │                                           │
┌────────▼───────────────────────────────────────────▼─────────────┐
│                    DataStream（数据通道层）                        │
│         分片 / 多发 / 重传 / 排序 / 校验 / 聚合                    │
├──────────────────┬────────────────────────────────────────────────┤
│  FgwUtpChannel   │   FgwTcpChannel   │   …（扩展）                │
│  （链路通道层）  │   （链路通道层）  │                             │
└──────────────────┴────────────────────────────────────────────────┘
```

> **关键约定**：SOCKS5 协议的握手与目标连接建立完全在 **OutportService** 侧完成，工作在 DataStream 字节流之上。InportService 侧只做原始 TCP 接入，将客户端数据**透传**进 DataStream，不感知 SOCKS5 语义。

#### 2.1.1 链路通道（Link Channel）

对应一个**端点对端点**的物理/协议传输通道。通道应尽可能保持长连接并被复用。

| 类型 | 实现 | 特点 |
|------|------|------|
| **FgwUtpChannel** | 基于 libutp 的 utp_socket | UDP 承载，内置拥塞控制，弱网表现好 |
| **FgwTcpChannel** | 基于 zce::TcpStream | 低延迟，NAT 穿透能力弱，带宽稳定 |

链路通道的职责：
- 建立/维护/重连底层连接
- 提供字节流读写接口（`zce::IStream`）
- 上报链路质量指标（RTT、丢包率、带宽估算）

#### 2.1.2 数据通道（Data Stream）

`DataStream` 关联**一组**链路通道，为上层提供单一的可靠字节流接口。

核心能力：

| 能力 | 说明 |
|------|------|
| **分片（Segmentation）** | 将数据切分为固定大小的 Segment，加 SegmentID |
| **多发（Multipath Send）** | 同一 Segment 可同时经由多条链路发送 |
| **去重（Deduplication）** | 接收端按 SegmentID 去重，保证幂等 |
| **排序（Reordering）** | 接收端缓冲乱序 Segment，按序交付上层 |
| **重传（Retransmission）** | 超时未确认的 Segment 在备用链路重传 |
| **校验（Checksum）** | 每个 Segment 携带 CRC32 校验 |

### 2.2 软件架构

#### 2.2.1 核心类

```
zce::IStream (interface)
    ├── FgwUtpChannel      -- 封装 libutp utp_socket
    ├── FgwTcpChannel      -- 封装 zce::TcpStream
    └── DataStream         -- 多链路聚合流
            ├── 关联 N 个 FgwUtpChannel
            └── 关联 M 个 FgwTcpChannel

FgwSession                 -- 代表一次客户端会话（InportService 侧）
    └── 持有一个 DataStream，将客户 TCP 数据透传入 DataStream

InportService              -- 监听入口，接受客户端 TCP 连接，透传数据
OutportService             -- 出口端：在 DataStream 字节流之上实现 SOCKS5 服务端，
                             解析目标地址后发起真实出口连接
ChannelManager             -- 管理链路通道池，负责连接/重连/心跳
```

#### 2.2.2 类关系图

```
InportService
    │  accepts TCP connection
    ▼
FgwSession ──────── DataStream ─────┬── FgwUtpChannel ──► OutportService
                                    ├── FgwUtpChannel
                                    └── FgwTcpChannel ──► OutportService
```

#### 2.2.3 线程模型

- 单线程事件驱动（基于 zce 事件循环）
- libutp 回调在同一事件循环线程中处理
- IO 密集任务（加解密、校验）可选择性地 offload 到线程池

---

## 3. 数据流设计

### 3.1 整体拓扑

```
Client App
    │  TCP（任意协议，客户端发起 SOCKS5 请求）
    ▼
InportService（监听 TCP 端口，透传数据）
    │
    ▼
FgwSession + DataStream（多路聚合，不解析 SOCKS5）
    │          │
    │   UTP链路（若干条）
    │   TCP链路（若干条）
    │          │
    ▼          ▼
OutportService（出口节点）
    │  在 DataStream 字节流之上解析 SOCKS5 协议
    │  根据目标地址发起真实 TCP/UDP 连接
    ▼
Target Server
```

### 3.2 建连流程

```
Client              InportService        ChannelManager      OutportService
  │─── TCP connect ────►│                     │                    │
  │                     │── 创建 FgwSession ──►│                    │
  │                     │                     │── 复用/新建链路 ───►│
  │                     │◄────────────────────│── 链路就绪 ────────│
  │─── SOCKS5 握手 ─────►│                     │                    │
  │   （原始字节透传）    │─── 写入 DataStream ──────────────────────►│
  │                     │                     │         │ 在 DataStream 上
  │                     │                     │         │ 解析 SOCKS5 握手
  │                     │                     │         ▼
  │                     │                     │  连接 Target Server
  │◄── SOCKS5 REPLY ◄───────────────────────────────────│
  │═══ 数据转发（透传）══════════════════════════════════► │
```

### 3.3 数据发送流程

```
DataStream::write(buf, len)
    │
    ├── 切分为 Segment（默认 1200 字节，含 SegmentID、SeqNum、CRC32）
    │
    ├── 选路策略（LinkSelector）
    │       ├── 最优单路：选 RTT 最低的链路
    │       ├── 全量多发：同一 Segment 写入所有活跃链路
    │       └── 加权多发：按链路质量权重分发
    │
    └── 各 FgwUtpChannel / FgwTcpChannel 发送
```

### 3.4 数据接收流程

```
FgwUtpChannel / FgwTcpChannel 收到数据
    │
    ├── 解包 Segment，校验 CRC32
    │
    ├── 去重（SegmentID 已存在则丢弃）
    │
    ├── 放入接收缓冲区（按 SeqNum 排序）
    │
    └── 连续段交付 DataStream::on_data_ready() → 上层回调
```

---

## 4. 报文格式

### 4.1 Segment 头部（固定 16 字节）

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
├───────────────────────────────────────────────────────────────┤
│  Magic(8)  │  Flags(8)  │         PayloadLen(16)              │
├───────────────────────────────────────────────────────────────┤
│                     SessionID (32)                            │
├───────────────────────────────────────────────────────────────┤
│                      SeqNum (32)                              │
├───────────────────────────────────────────────────────────────┤
│                      CRC32 (32)                               │
└───────────────────────────────────────────────────────────────┘
```

| 字段 | 长度 | 说明 |
|------|------|------|
| Magic | 1B | 固定值 `0xFG`（0xF6），用于帧同步 |
| Flags | 1B | `SYN=0x01, FIN=0x02, DATA=0x04, ACK=0x08, HEARTBEAT=0x10` |
| PayloadLen | 2B | Payload 字节数，最大 65519 |
| SessionID | 4B | 会话标识，用于多路复用 |
| SeqNum | 4B | 单调递增序列号，用于排序和去重 |
| CRC32 | 4B | 头部 + Payload 的 CRC32 校验 |

---

## 5. 关键算法

### 5.1 选路策略（LinkSelector）

默认采用**加权最短路径**策略：

$$
w_i = \frac{1}{\text{RTT}_i \times (1 + \text{loss\_rate}_i)}
$$

发送时按权重 $w_i$ 分配 Segment，权重越高分配越多。

当链路质量指标超过阈值（RTT > 500ms 或丢包率 > 30%）时，该链路进入**降级状态**，仅用于冗余备份发送。

### 5.2 接收去重与排序

- 维护一个大小为 `W`（默认 1024）的接收窗口
- 使用滑动窗口 + Bitmap 标记已接收的 SeqNum
- SeqNum 落在窗口之外（过旧）的 Segment 直接丢弃
- 窗口头部连续已收 Segment 批量交付，窗口向前滑动

### 5.3 心跳与链路探活

- 每条链路每隔 `heartbeat_interval`（默认 5s）发送一个 `HEARTBEAT` Segment
- 超过 `link_timeout`（默认 15s）无响应则标记链路为不可用
- 不可用链路进入**重连队列**，按指数退避（1s, 2s, 4s, … 上限 60s）重连

---

## 6. 接口设计

### 6.1 DataStream

```cpp
class DataStream : public zce::IStream {
public:
    // 添加/移除链路通道
    int  add_channel(std::shared_ptr<IFgwChannel> ch);
    int  remove_channel(uint32_t channel_id);

    // 选路策略（可替换）
    void set_link_selector(std::unique_ptr<ILinkSelector> selector);

    // zce::IStream 接口
    ssize_t read(void* buf, size_t len) override;
    ssize_t write(const void* buf, size_t len) override;
    int     close() override;

    // 异步回调
    using DataReadyCallback = std::function<void(const uint8_t*, size_t)>;
    void set_on_data_ready(DataReadyCallback cb);
};
```

### 6.2 FgwUtpChannel / FgwTcpChannel

```cpp
class IFgwChannel : public zce::IStream {
public:
    virtual uint32_t    channel_id()   const = 0;
    virtual LinkQuality quality()      const = 0;  // RTT, loss_rate, bandwidth
    virtual bool        is_connected() const = 0;
    virtual int         connect(const zce::SockAddrIn& remote) = 0;
    virtual ~IFgwChannel() = default;
};

class FgwUtpChannel : public IFgwChannel { /* libutp 实现 */ };
class FgwTcpChannel : public IFgwChannel { /* zce::TcpStream 实现 */ };
```

### 6.3 InportService

```cpp
class InportService {
public:
    // 启动监听，port 为本地 SOCKS5 监听端口
    int  start(uint16_t port);
    void stop();

    // 会话创建回调（用于注入 DataStream 工厂）
    using SessionFactory = std::function<std::shared_ptr<FgwSession>()>;
    void set_session_factory(SessionFactory f);
};
```

### 6.4 OutportService

```cpp
class OutportService {
public:
    // 启动出口监听（供 DataStream/链路通道连接）
    int  start(uint16_t port);
    void stop();

    // 出口绑定地址（固定出口 IP）
    void set_egress_addr(const zce::SockAddrIn& addr);

    // OutportService 在收到 DataStream 字节流后，在其上运行 SOCKS5 服务端：
    //   1. 完成 SOCKS5 握手（方法协商 + CONNECT/BIND/UDP_ASSOC 请求解析）
    //   2. 根据请求中的目标地址，以固定出口 IP 向 Target Server 发起连接
    //   3. 连接成功后双向转发 DataStream ↔ Target Server
    //   4. 连接失败时写回 SOCKS5 错误应答，关闭会话
};
```

---

## 7. 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `inport.listen_port` | uint16 | 1080 | 本地 SOCKS5 监听端口 |
| `outport.addr` | string | — | 出口节点地址（IP:Port） |
| `channel.utp_count` | int | 2 | 预建 UTP 链路数量 |
| `channel.tcp_count` | int | 1 | 预建 TCP 链路数量 |
| `channel.heartbeat_interval` | int(s) | 5 | 心跳间隔（秒） |
| `channel.link_timeout` | int(s) | 15 | 链路超时（秒） |
| `channel.reconnect_max` | int(s) | 60 | 重连最大退避时间（秒） |
| `stream.segment_size` | int | 1200 | 分片大小（字节） |
| `stream.recv_window` | int | 1024 | 接收窗口大小（Segment 数） |
| `stream.multipath_mode` | string | `weighted` | 选路策略：`best`/`all`/`weighted` |

---

## 8. 错误处理

| 错误场景 | 处理策略 |
|----------|---------|
| 链路断开 | 标记不可用，触发重连，DataStream 切换到其余链路继续传输 |
| CRC 校验失败 | 丢弃该 Segment，依赖重传恢复 |
| 接收窗口满 | 向发送端发送流控（WINDOW_FULL），暂停发送 |
| 所有链路不可用 | 向上层回调错误，等待至少一条链路恢复后继续 |
| SOCKS5 目标不可达 | OutportService 写回 SOCKS5 错误应答（0x04/0x05），关闭出口会话 |

---

## 9. 后续工作（Roadmap）

- [ ] 实现 `FgwUtpChannel`（libutp 集成）
- [ ] 实现 `FgwTcpChannel`
- [ ] 实现 `DataStream`（分片/多发/去重/排序）
- [ ] 实现 `InportService`（原始 TCP 接入 + 数据透传）
- [ ] 实现 `OutportService`（DataStream 之上的 SOCKS5 服务端 + 出口转发）
- [ ] 实现 `ChannelManager`（连接池/心跳/重连）
- [ ] 单元测试与集成测试
- [ ] 性能基准测试（吞吐量、延迟、丢包恢复）
- [ ] 支持加密（ChaCha20-Poly1305）
- [ ] 支持多出口负载均衡
