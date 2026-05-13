# TaijiMPC RPC服务接口设计文档

## 📚 文档目录

### 📋 文档概述
- 项目背景
- 核心架构设计
- 设计亮点
- 技术特色
- 关键改进对比

### 🎯 技术实现策略
- 实施建议
- 工业级特性实现
  - 接口幂等性设计
  - 资源局部更新
  - 服务端实现策略
  - 客户端实现策略
  - 实例元对象管理

### 🏗️ 服务定义
- 服务架构概述
- 服务架构
- 技术选型

### 🔧 核心服务接口
- 服务接口定义
- 数据结构定义
  - 基础数据类型
  - 控制器相关结构
  - 仿真相关结构
  - 数据源相关结构

### 📝 请求响应定义
- 项目管理接口
- 控制器操作接口
- 仿真操作接口
- 模型操作接口
- 数据流接口
- 数据源操作接口

### ⚠️ 错误处理
- 错误码定义

### 🏛️ 服务实现架构
- 服务端架构
- 客户端架构

### ⚙️ 部署和配置
- 服务配置
- 客户端配置

### 🔒 安全考虑
- 认证授权
- 权限控制

### 📊 监控和诊断
- 健康检查
- 性能指标

### 💡 使用示例
- 客户端使用示例

### 📝 文档总结
- 设计亮点
- 技术特色
- 实施路线图
- 最佳实践建议
- 预期收益

---

**文档版本**: v3.0  
**最后更新**: 2024年  
**维护状态**: 活跃维护中

---

## 📋 文档概述

### 项目背景
这份文档详细设计了一个基于RPC架构的MPC（模型预测控制）系统，将原有的单体应用拆分为客户端和服务端，实现了控制算法与UI界面的分离。该设计旨在提高系统的可扩展性、稳定性和部署灵活性。

### 🏗️ 核心架构设计

#### 服务架构模式
```
┌─────────────────┐    RPC调用    ┌─────────────────┐
│   Qt GUI Client │ ──────────── │  MPC RPC Server │
│                 │              │                 │
│ - 项目管理      │              │ - 在线控制      │
│ - 参数配置      │              │ - 离线仿真      │
│ - 数据可视化    │              │ - 模型计算      │
│ - 监控界面      │              │ - 数据采集      │
└─────────────────┘              └─────────────────┘
```

#### 技术选型
- **RPC框架**: ZCE (支持RPC和LPC无缝切换)
- **序列化**: ZCE PTL
- **语言**: C++ (服务端) + Qt C++ (客户端)
- **通信模式**: 同步调用 + 异步流式传输

### 🎯 设计亮点

1. **架构现代化**: 从单体架构向微服务架构演进，实现了控制算法与UI界面的完全分离
2. **服务职责清晰**: 按业务领域拆分为7个独立服务，每个服务职责单一，易于维护和扩展
3. **生命周期解耦**: 通过实例ID机制，实现了项目配置与运行实例的分离，支持一对多运行
4. **异步处理标准化**: 采用业界标准的"启动-轮询"模式处理长耗时任务，提高系统健壮性
5. **数据结构优化**: 分离配置与历史数据，按需请求，提升性能和可维护性
6. **统一实例管理**: 通过InstanceService提供统一的实例状态查询、资源监控和运维管理
7. **工业级鲁棒性**: 实现幂等性、局部更新、状态恢复等企业级特性

### 🔧 技术特色

- **RPC框架**: 采用ZCE框架，支持RPC和LPC无缝切换，适应不同部署场景
- **流式传输**: 支持实时数据流的异步传输，满足MPC系统的实时性要求
- **错误处理**: 使用gRPC标准状态码，符合行业最佳实践
- **安全机制**: 集成认证授权和健康检查，保障系统安全可靠
- **监控运维**: 统一的实例管理和监控，简化系统运维和故障排查

### 📊 关键改进对比

| 问题 | 原始设计 | 修订版方案 | 优势 |
|------|----------|------------|------|
| **服务职责混杂** | 单一"上帝服务" | 按业务领域拆分服务 | 模块化、易维护、可独立扩展 |
| **生命周期耦合** | 项目与实例直接关联 | 引入实例ID，分离配置与运行 | 支持一对多运行，生命周期清晰 |
| **异步处理不规范** | 自定义as_thread参数 | 标准"启动-轮询"模式 | 行业标准，客户端解耦，健壮性高 |
| **数据结构冗余** | 配置与历史数据混合 | 分离配置与数据，按需请求 | 性能优化，关注点分离，配置对象轻量 |
| **错误处理不标准** | 响应中包含成功/失败标志 | 使用gRPC Status Code | 符合gRPC惯例，响应更纯粹 |
| **实例管理分散** | 控制器和仿真分别管理 | 统一InstanceService管理 | 运维友好，资源监控，故障排查简化 |
| **缺乏运维支持** | 无统一监控和日志 | 完整的监控面板和告警系统 | 可观测性强，支持系统优化 |

---

## 2. 技术实现策略

### 🚀 实施建议

1. **分阶段实施**: 建议先实现核心的ProjectService和ControllerService
2. **向后兼容**: 在过渡期间保持原有接口的兼容性
3. **性能优化**: 重点关注流式数据传输的性能调优
4. **监控完善**: 建立完善的日志和性能监控体系
5. **安全加固**: 实现基于角色的访问控制(RBAC)

### 🔧 工业级特性实现

#### 1. 工业级鲁棒性提升

##### 1.1 接口幂等性设计
**问题**: 网络故障时客户端重试可能导致重复操作
**解决方案**: 为所有产生副作用的RPC请求增加幂等性令牌

```protobuf
message CreateControllerInstanceRequest {
    string request_id = 1; // 幂等性令牌，客户端生成的UUID
    string project_id = 2;
    ControllerParameters initial_parameters = 3;
}
```

**服务端逻辑**:
- 检查request_id是否在24小时内处理过
- 已处理：直接返回第一次结果
- 未处理：执行逻辑并缓存结果

##### 1.2 资源局部更新
**问题**: 全量更新配置对象效率低且易产生并发覆盖
**解决方案**: 采用FieldMask模式实现精确更新

```protobuf
import "google/protobuf/field_mask.proto";

message UpdateConfigurationRequest {
    string project_id = 1;
    ProjectConfiguration configuration = 2; // 只需填充要修改的字段
    google.protobuf.FieldMask update_mask = 3; // 明确指定更新字段
}
```

**优势**:
- 性能提升：减少网络传输数据量
- API精确性：明确表达修改意图
- 并发安全：避免意外覆盖其他字段

#### 2. 服务端实现策略

##### 2.1 对象模型设计
- **管理器类**: ProjectManager、ControllerManager等作为单例，管理实例生命周期
- **实例类**: MPCControllerInstance、MPCSimulationInstance封装单个控制器/仿真的所有状态和逻辑

##### 2.2 状态管理与恢复
**问题**: 纯内存设计在进程崩溃时丢失所有状态
**解决方案**:
- **无状态服务**: 配置存储在文件/数据库中，按需加载
- **运行时状态恢复**: 
  - 定期快照：每分钟序列化关键状态
  - 日志先行：记录状态变更事件
  - 重启恢复：扫描快照目录恢复实例

#### 3. 客户端实现策略

##### 3.1 MVC/MVVM架构模式
- **Model**: ProjectModel、ControllerModel等C++类，通过Q_PROPERTY暴露数据
- **View**: UI文件和QWidget子类，负责显示和用户输入
- **Controller**: RPCClientWrapper封装gRPC调用，更新Model而非直接操作UI

##### 3.2 连接状态管理
- 实现连接状态机（Connecting、Connected、Disconnected、Reconnecting）
- 连接断开时UI进入只读模式，显示明确提示
- 后台自动重连机制

#### 4. 实施路线图优化

##### 第一阶段增强
- **测试先行**: 编写不依赖UI的单元测试和集成测试
- **日志集成**: 从开始就集成spdlog等日志库
- **安全基础**: 尽早实现AuthService和访问控制

##### 关键决策点
- 选择持久化存储方案（文件系统 vs 数据库）
- 确定状态恢复策略（快照 vs 日志）
- 设计客户端重连和错误处理机制

#### 5. 实例元对象管理

##### 5.1 统一实例管理接口
**问题**: 控制器和仿真实例分别管理，缺乏统一的实例状态查询和资源监控
**解决方案**: 引入InstanceService和InstanceMetadata抽象层

```protobuf
// 实例元数据服务
service InstanceService {
    rpc ListInstances(ListInstancesRequest) returns (ListInstancesResponse);
    rpc GetInstanceInfo(GetInstanceInfoRequest) returns (InstanceInfoResponse);
    rpc GetInstanceMetrics(GetInstanceMetricsRequest) returns (InstanceMetricsResponse);
    rpc KillInstance(KillInstanceRequest) returns (KillInstanceResponse);
    rpc GetInstanceLogs(GetInstanceLogsRequest) returns (stream InstanceLogResponse);
}

// 实例类型枚举
enum InstanceType {
    UNKNOWN = 0;
    CONTROLLER = 1;
    SIMULATION = 2;
    MODEL_BUILDER = 3;
}

// 实例状态枚举
enum InstanceState {
    INSTANCE_UNKNOWN = 0;
    INSTANCE_CREATED = 1;
    INSTANCE_STARTING = 2;
    INSTANCE_RUNNING = 3;
    INSTANCE_PAUSED = 4;
    INSTANCE_STOPPING = 5;
    INSTANCE_STOPPED = 6;
    INSTANCE_ERROR = 7;
    INSTANCE_DESTROYED = 8;
}

// 实例元数据
message InstanceMetadata {
    string instance_id = 1;
    InstanceType type = 2;
    InstanceState state = 3;
    string project_id = 4;
    string project_name = 5;
    int64 created_time = 6;
    int64 started_time = 7;
    int64 last_activity_time = 8;
    string created_by = 9;
    map<string, string> labels = 10; // 自定义标签
    InstanceResourceUsage resource_usage = 11;
    repeated string tags = 12; // 标签列表
}

// 资源使用情况
message InstanceResourceUsage {
    double cpu_usage_percent = 1;
    double memory_usage_mb = 2;
    double disk_usage_mb = 3;
    int32 active_threads = 4;
    double network_io_mbps = 5;
    int64 total_operations = 6;
    double avg_response_time_ms = 7;
}

// 实例列表请求
message ListInstancesRequest {
    InstanceType type_filter = 1; // 可选，按类型过滤
    InstanceState state_filter = 2; // 可选，按状态过滤
    string project_id_filter = 3; // 可选，按项目过滤
    bool include_destroyed = 4; // 是否包含已销毁的实例
    int32 page_size = 5;
    string page_token = 6;
}

// 实例列表响应
message ListInstancesResponse {
    repeated InstanceMetadata instances = 1;
    string next_page_token = 2;
    int32 total_count = 3;
}

// 获取实例信息请求
message GetInstanceInfoRequest {
    string instance_id = 1;
}

// 获取实例信息响应
message InstanceInfoResponse {
    InstanceMetadata metadata = 1;
    google.protobuf.Any instance_specific_data = 2; // 控制器或仿真的具体数据
}

// 获取实例指标请求
message GetInstanceMetricsRequest {
    string instance_id = 1;
    int64 start_time = 2;
    int64 end_time = 3;
    string metric_name = 4; // 可选，特定指标
}

// 获取实例指标响应
message InstanceMetricsResponse {
    repeated MetricPoint metrics = 1;
}

// 指标数据点
message MetricPoint {
    int64 timestamp = 1;
    double value = 2;
    string metric_name = 3;
    map<string, string> labels = 4;
}

// 强制终止实例请求
message KillInstanceRequest {
    string instance_id = 1;
    string reason = 2;
    bool force = 3; // 是否强制终止
}

// 强制终止实例响应
message KillInstanceResponse {
    bool success = 1;
    string error_message = 2;
    int64 termination_time = 3;
}

// 获取实例日志请求
message GetInstanceLogsRequest {
    string instance_id = 1;
    int64 start_time = 2;
    int64 end_time = 3;
    string log_level = 4; // INFO, WARNING, ERROR, DEBUG
    int32 max_entries = 5;
    bool follow = 6; // 是否持续监听新日志
}

// 实例日志响应
message InstanceLogResponse {
    int64 timestamp = 1;
    string level = 2;
    string message = 3;
    string source = 4; // 日志来源
    map<string, string> context = 5; // 上下文信息
}
```

##### 5.2 实例管理器实现
```cpp
// 统一实例管理器
class InstanceManager {
public:
    InstanceManager();
    ~InstanceManager();
    
    // 实例生命周期管理
    std::string CreateInstance(InstanceType type, const std::string& projectId, 
                              const std::string& createdBy, const std::map<std::string, std::string>& labels);
    bool DestroyInstance(const std::string& instanceId);
    bool KillInstance(const std::string& instanceId, const std::string& reason, bool force = false);
    
    // 实例查询
    std::vector<InstanceMetadata> ListInstances(const ListInstancesFilter& filter);
    std::optional<InstanceMetadata> GetInstanceInfo(const std::string& instanceId);
    InstanceResourceUsage GetInstanceResourceUsage(const std::string& instanceId);
    
    // 状态更新
    void UpdateInstanceState(const std::string& instanceId, InstanceState newState);
    void UpdateInstanceActivity(const std::string& instanceId);
    void UpdateResourceUsage(const std::string& instanceId, const InstanceResourceUsage& usage);
    
    // 日志管理
    void LogInstanceEvent(const std::string& instanceId, const std::string& level, 
                         const std::string& message, const std::map<std::string, std::string>& context = {});
    std::vector<InstanceLogEntry> GetInstanceLogs(const std::string& instanceId, 
                                                 const LogFilter& filter);
    
    // 监控和清理
    void StartMonitoring();
    void StopMonitoring();
    void CleanupExpiredInstances();
    
private:
    std::mutex m_instancesMutex;
    std::unordered_map<std::string, std::shared_ptr<InstanceInfo>> m_instances;
    
    // 监控线程
    std::unique_ptr<std::thread> m_monitoringThread;
    std::atomic<bool> m_monitoringRunning;
    
    // 日志存储
    std::unique_ptr<LogStorage> m_logStorage;
    
    // 资源监控
    void MonitorResourceUsage();
    void UpdateAllInstanceMetrics();
    
    // 内部方法
    std::string GenerateInstanceId(InstanceType type);
    void SaveInstanceMetadata(const std::string& instanceId, const InstanceMetadata& metadata);
    InstanceMetadata LoadInstanceMetadata(const std::string& instanceId);
};

// 实例信息内部结构
struct InstanceInfo {
    InstanceMetadata metadata;
    std::shared_ptr<void> instance_ptr; // 指向具体的控制器或仿真实例
    std::chrono::steady_clock::time_point last_activity;
    std::atomic<int64_t> operation_count;
    std::mutex resource_mutex;
    InstanceResourceUsage current_resource_usage;
    
    // 日志缓存
    std::deque<InstanceLogEntry> recent_logs;
    std::mutex logs_mutex;
    static const size_t MAX_RECENT_LOGS = 1000;
};

// 日志存储接口
class LogStorage {
public:
    virtual ~LogStorage() = default;
    virtual void StoreLog(const std::string& instanceId, const InstanceLogEntry& log) = 0;
    virtual std::vector<InstanceLogEntry> RetrieveLogs(const std::string& instanceId, 
                                                      const LogFilter& filter) = 0;
    virtual void CleanupOldLogs(int64_t cutoffTime) = 0;
};

// 文件系统日志存储实现
class FileSystemLogStorage : public LogStorage {
public:
    explicit FileSystemLogStorage(const std::string& basePath);
    
    void StoreLog(const std::string& instanceId, const InstanceLogEntry& log) override;
    std::vector<InstanceLogEntry> RetrieveLogs(const std::string& instanceId, 
                                              const LogFilter& filter) override;
    void CleanupOldLogs(int64_t cutoffTime) override;
    
private:
    std::string m_basePath;
    std::mutex m_fileMutex;
    
    std::string GetLogFilePath(const std::string& instanceId, const std::string& date);
    void EnsureLogDirectory(const std::string& instanceId);
};
```

##### 5.3 集成到现有服务
```cpp
// 在ControllerService中集成实例管理
class ControllerServiceImpl : public ControllerService::Service {
public:
    ControllerServiceImpl(std::shared_ptr<InstanceManager> instanceManager);
    
    grpc::Status CreateInstance(grpc::ServerContext* context,
                               const CreateControllerInstanceRequest* request,
                               ControllerInstanceResponse* response) override {
        // 创建实例元数据
        std::string instanceId = m_instanceManager->CreateInstance(
            InstanceType::CONTROLLER, 
            request->project_id(), 
            GetCurrentUser(context),
            {{"controller_type", "mpc"}, {"prediction_horizon", std::to_string(request->initial_parameters().prediction_horizon())}}
        );
        
        // 创建控制器实例
        auto controller = std::make_shared<MPCController>(request->initial_parameters());
        m_instanceManager->SetInstancePtr(instanceId, controller);
        
        // 更新状态
        m_instanceManager->UpdateInstanceState(instanceId, InstanceState::INSTANCE_CREATED);
        
        response->set_instance_id(instanceId);
        return grpc::Status::OK;
    }
    
private:
    std::shared_ptr<InstanceManager> m_instanceManager;
    std::string GetCurrentUser(grpc::ServerContext* context);
};
```

##### 5.4 监控和运维支持
```cpp
// 实例监控面板数据
class InstanceMonitoringPanel {
public:
    struct DashboardData {
        int32_t total_instances;
        int32_t running_instances;
        int32_t error_instances;
        double total_cpu_usage;
        double total_memory_usage;
        std::vector<InstanceMetadata> recent_instances;
        std::vector<MetricPoint> system_metrics;
    };
    
    DashboardData GetDashboardData();
    std::vector<InstanceMetadata> GetInstancesByType(InstanceType type);
    std::vector<InstanceMetadata> GetInstancesByState(InstanceState state);
    std::vector<InstanceMetadata> GetInstancesByProject(const std::string& projectId);
    
    // 告警功能
    void SetResourceThreshold(double cpuThreshold, double memoryThreshold);
    std::vector<InstanceAlert> GetActiveAlerts();
    
private:
    std::shared_ptr<InstanceManager> m_instanceManager;
    double m_cpuThreshold = 80.0;
    double m_memoryThreshold = 80.0;
};

// 实例告警
struct InstanceAlert {
    std::string instanceId;
    std::string alertType; // "high_cpu", "high_memory", "error_state"
    std::string message;
    int64_t timestamp;
    bool acknowledged;
};
```

---

## 3. 服务定义

### 3.1 服务架构概述

基于对TaijiMPC原代码的分析，将MPC在线控制和仿真功能独立为RPC/LPC服务，实现控制算法与UI界面的分离。这样可以提高系统的可扩展性、稳定性和部署灵活性。

### 3.2 服务架构
```
┌─────────────────┐    RPC调用    ┌─────────────────┐
│   Qt GUI Client │ ──────────── │  MPC RPC Server │
│                 │              │                 │
│ - 项目管理      │              │ - 在线控制      │
│ - 参数配置      │              │ - 离线仿真      │
│ - 数据可视化    │              │ - 模型计算      │
│ - 监控界面      │              │ - 数据采集      │
└─────────────────┘              └─────────────────┘
```

### 3.3 技术选型
- **RPC框架**: ZCE(无缝切换RPC和LPC)
- **序列化**: ZCE PTL
- **语言**: C++ (服务端) + Qt C++ (客户端)
- **通信模式**: 同步调用 + 异步流式传输

## 4. 核心服务接口

### 4.1 服务接口定义

```protobuf
syntax = "proto3";

package taijimpc;

import "google/protobuf/field_mask.proto";

// MPC控制服务
service MPCControlService {
    // 项目管理
    rpc CreateProject(CreateProjectRequest) returns (CreateProjectResponse);
    rpc LoadProject(LoadProjectRequest) returns (LoadProjectResponse);
    rpc SaveProject(SaveProjectRequest) returns (SaveProjectResponse);
    rpc GetProjectInfo(GetProjectInfoRequest) returns (GetProjectInfoResponse);
    
    // 配置管理
    rpc UpdateConfiguration(UpdateConfigurationRequest) returns (UpdateConfigurationResponse);
    rpc ValidateConfiguration(ValidateConfigurationRequest) returns (ValidateConfigurationResponse);
    
    // 控制器操作
    rpc InitializeController(InitializeControllerRequest) returns (InitializeControllerResponse);
    rpc StartController(StartControllerRequest) returns (StartControllerResponse);
    rpc StopController(StopControllerRequest) returns (StopControllerResponse);
    rpc ResetController(ResetControllerRequest) returns (ResetControllerResponse);
    rpc GetControllerStatus(GetControllerStatusRequest) returns (GetControllerStatusResponse);
    
    // 仿真操作
    rpc StartSimulation(StartSimulationRequest) returns (StartSimulationResponse);
    rpc StopSimulation(StopSimulationRequest) returns (StopSimulationResponse);
    rpc PauseSimulation(PauseSimulationRequest) returns (PauseSimulationResponse);
    rpc ResumeSimulation(ResumeSimulationRequest) returns (ResumeSimulationResponse);
    
    // 数据流接口
    rpc SubscribeRealTimeData(SubscribeDataRequest) returns (stream RealTimeDataResponse);
    rpc SubscribeControllerOutput(SubscribeControllerRequest) returns (stream ControllerOutputResponse);
    rpc SubscribeSimulationData(SubscribeSimulationRequest) returns (stream SimulationDataResponse);
    
    // 模型操作
    rpc GenerateGBNSignal(GenerateGBNRequest) returns (GenerateGBNResponse);
    rpc CalculateDelay(CalculateDelayRequest) returns (CalculateDelayResponse);
    rpc IdentifyModel(IdentifyModelRequest) returns (IdentifyModelResponse);
    rpc ExportModel(ExportModelRequest) returns (ExportModelResponse);
    
    // 数据源操作
    rpc ConnectDataSource(ConnectDataSourceRequest) returns (ConnectDataSourceResponse);
    rpc DisconnectDataSource(DisconnectDataSourceRequest) returns (DisconnectDataSourceResponse);
    rpc ReadTags(ReadTagsRequest) returns (ReadTagsResponse);
    rpc WriteTags(WriteTagsRequest) returns (WriteTagsResponse);
}
```

### 4.2 数据结构定义

#### 4.2.1 基础数据类型
```protobuf
// 信号基础结构
message SignalBase {
    string name = 1;
    string tag_name = 2;
    bool enabled = 3;
    string description = 4;
    repeated double data = 5;
}

// MV信号
message MVSignal {
    SignalBase base = 1;
    double high_limit = 2;
    double low_limit = 3;
    double rate_limit = 4;
    bool control_on = 5;
    double current_value = 6;
    double target_value = 7;
    repeated double gbn_signal = 8;
    int32 switch_factor = 9;
}

// DV信号
message DVSignal {
    SignalBase base = 1;
    bool predicted = 2;
    double current_value = 3;
}

// CV信号
message CVSignal {
    SignalBase base = 1;
    double set_point = 2;
    double high_limit = 3;
    double low_limit = 4;
    double weight = 5;
    double current_value = 6;
    bool is_calculated = 7;
    string calculation_formula = 8;
    double cv_length = 9;
}

// EV信号
message EVSignal {
    SignalBase base = 1;
    double current_value = 2;
}

// 项目配置
message ProjectConfiguration {
    string project_name = 1;
    string project_path = 2;
    double sampling_time = 3;
    string sampling_time_unit = 4;
    double time_to_steady_state = 5;
    bool is_real_plant = 6;
    int32 time_compression_factor = 7;
    bool use_watchdog = 8;
    string watchdog_tag = 9;
    int32 watchdog_value = 10;
    bool watchdog_toggle = 11;
    double watchdog_ratio = 12;
    string data_source_type = 13;
    string remote_host = 14;
    string server_name = 15;
    repeated MVSignal mv_signals = 16;
    repeated DVSignal dv_signals = 17;
    repeated CVSignal cv_signals = 18;
    repeated EVSignal ev_signals = 19;
}
```

#### 4.2.2 控制器相关结构
```protobuf
// 控制器状态
enum ControllerState {
    CONTROLLER_STOPPED = 0;
    CONTROLLER_INITIALIZING = 1;
    CONTROLLER_RUNNING = 2;
    CONTROLLER_ERROR = 3;
    CONTROLLER_PAUSED = 4;
}

// 控制器参数
message ControllerParameters {
    int32 prediction_horizon = 1;
    int32 control_horizon = 2;
    bool economic_optimize = 3;
    double optimize_speed = 4;
    bool predict_model = 5;
    bool use_script = 6;
    string init_script = 7;
    string input_script = 8;
    string output_script = 9;
}

// 控制器状态信息
message ControllerStatus {
    ControllerState state = 1;
    string error_message = 2;
    int64 step_count = 3;
    double last_execution_time_ms = 4;
    double max_execution_time_ms = 5;
    double min_execution_time_ms = 6;
    bool model_initialized = 7;
    int64 start_time = 8;
}

// 控制器输出
message ControllerOutput {
    int64 timestamp = 1;
    int64 step = 2;
    repeated double mv_values = 3;
    repeated double cv_predictions = 4;
    repeated double dv_predictions = 5;
    repeated double mv_steady_values = 6;
    repeated double cv_steady_values = 7;
    repeated double mv_error_pct = 8;
    repeated double cv_error_pct = 9;
    double execution_time_ms = 10;
    string status_message = 11;
}
```

#### 4.2.3 仿真相关结构
```protobuf
// 仿真状态
enum SimulationState {
    SIMULATION_STOPPED = 0;
    SIMULATION_RUNNING = 1;
    SIMULATION_PAUSED = 2;
    SIMULATION_COMPLETED = 3;
    SIMULATION_ERROR = 4;
}

// 仿真参数
message SimulationParameters {
    int32 periods = 1;
    bool economic_optimize = 2;
    double optimize_speed = 3;
    int32 time_compression_factor = 4;
    bool use_initial_conditions = 5;
    repeated double initial_mv_values = 6;
    repeated double initial_cv_values = 7;
}

// 仿真状态信息
message SimulationStatus {
    SimulationState state = 1;
    int32 current_period = 2;
    int32 total_periods = 3;
    double progress_percentage = 4;
    string error_message = 5;
    int64 start_time = 6;
    int64 estimated_end_time = 7;
}

// 仿真数据
message SimulationData {
    int64 timestamp = 1;
    int32 period = 2;
    repeated double mv_values = 3;
    repeated double dv_values = 4;
    repeated double cv_values = 5;
    repeated double cv_setpoints = 6;
    double sampling_time = 7;
}
```

#### 4.2.4 数据源相关结构
```protobuf
// 数据源类型
enum DataSourceType {
    DATA_SOURCE_OPC = 0;
    DATA_SOURCE_CSV = 1;
    DATA_SOURCE_SIMULATION = 2;
    DATA_SOURCE_DATABASE = 3;
}

// 数据源配置
message DataSourceConfig {
    DataSourceType type = 1;
    string connection_string = 2;
    string server_name = 3;
    string host_name = 4;
    int32 update_rate = 5;
    map<string, string> properties = 6;
}

// 标签读写请求
message TagValue {
    string tag_name = 1;
    double value = 2;
    int32 quality = 3;
    int64 timestamp = 4;
    int32 error_code = 5;
}

// 实时数据
message RealTimeData {
    int64 timestamp = 1;
    repeated TagValue tag_values = 2;
    string data_source_status = 3;
}
```

## 5. 请求响应定义

### 5.1 项目管理接口

#### 5.1.1 创建项目
```protobuf
message CreateProjectRequest {
    string request_id = 1; // 幂等性令牌，客户端生成的UUID
    string project_name = 2;
    string project_path = 3;
    ProjectConfiguration initial_config = 4;
}

message CreateProjectResponse {
    bool success = 1;
    string error_message = 2;
    string project_id = 3;
}
```

#### 5.1.2 加载项目
```protobuf
message LoadProjectRequest {
    string request_id = 1; // 幂等性令牌
    string project_file_path = 2;
}

message LoadProjectResponse {
    bool success = 1;
    string error_message = 2;
    string project_id = 3;
    ProjectConfiguration configuration = 4;
}
```

#### 5.1.3 保存项目
```protobuf
message SaveProjectRequest {
    string request_id = 1; // 幂等性令牌
    string project_id = 2;
    bool only_backup = 3;
    string save_path = 4; // 可选，为空则保存到原路径
}

message SaveProjectResponse {
    bool success = 1;
    string error_message = 2;
    string saved_path = 3;
}
```

#### 5.1.4 更新配置（支持局部更新）
```protobuf
message UpdateConfigurationRequest {
    string request_id = 1; // 幂等性令牌
    string project_id = 2;
    ProjectConfiguration configuration = 3; // 只需填充要修改的字段
    google.protobuf.FieldMask update_mask = 4; // 明确指定要更新的字段
}

message UpdateConfigurationResponse {
    bool success = 1;
    string error_message = 2;
    ProjectConfiguration updated_configuration = 3;
}
```

### 5.2 控制器操作接口

#### 5.2.1 初始化控制器
```protobuf
message InitializeControllerRequest {
    string request_id = 1; // 幂等性令牌
    string project_id = 2;
    ControllerParameters parameters = 3;
    bool force_reset = 4;
}

message InitializeControllerResponse {
    bool success = 1;
    string error_message = 2;
    ControllerStatus status = 3;
}
```

#### 5.2.2 启动控制器
```protobuf
message StartControllerRequest {
    string request_id = 1; // 幂等性令牌
    string project_id = 2;
    bool reset_mv = 3;
    bool clear_history = 4;
}

message StartControllerResponse {
    bool success = 1;
    string error_message = 2;
    ControllerStatus status = 3;
}
```

#### 5.2.3 停止控制器
```protobuf
message StopControllerRequest {
    string request_id = 1; // 幂等性令牌
    string project_id = 2;
    bool save_data = 3;
}

message StopControllerResponse {
    bool success = 1;
    string error_message = 2;
    ControllerStatus final_status = 3;
}
```

### 5.3 仿真操作接口

#### 5.3.1 启动仿真
```protobuf
message StartSimulationRequest {
    string project_id = 1;
    SimulationParameters parameters = 2;
}

message StartSimulationResponse {
    bool success = 1;
    string error_message = 2;
    string simulation_id = 3;
    SimulationStatus status = 4;
}
```

#### 5.3.2 停止仿真
```protobuf
message StopSimulationRequest {
    string project_id = 1;
    string simulation_id = 2;
}

message StopSimulationResponse {
    bool success = 1;
    string error_message = 2;
    SimulationStatus final_status = 3;
}
```

### 5.4 模型操作接口

#### 5.4.1 生成GBN信号
```protobuf
message GenerateGBNRequest {
    string project_id = 1;
    int32 signal_length = 2;
    double amplitude = 3;
    int32 switch_factor = 4;
    repeated int32 mv_indices = 5; // 指定哪些MV生成信号
}

message GenerateGBNResponse {
    bool success = 1;
    string error_message = 2;
    repeated GBNSignalData signals = 3;
    int32 suggested_test_time = 4;
}

message GBNSignalData {
    int32 mv_index = 1;
    repeated double signal_values = 2;
    repeated double extended_signal = 3;
}
```

#### 5.4.2 计算延迟
```protobuf
message CalculateDelayRequest {
    string project_id = 1;
    int32 delay_type = 2; // 0=auto, 1=all_one, 2=custom
    bool use_expect_matrix = 3;
    bool as_thread = 4;
}

message CalculateDelayResponse {
    bool success = 1;
    string error_message = 2;
    string task_id = 3; // 如果as_thread=true，返回任务ID
    repeated DelayResult delays = 4;
}

message DelayResult {
    int32 mv_index = 1;
    int32 cv_index = 2;
    int32 delay_value = 3;
    double confidence = 4;
}
```

#### 5.4.3 模型辨识
```protobuf
message IdentifyModelRequest {
    string project_id = 1;
    bool use_expect_matrix = 2;
    bool as_thread = 3;
    int32 model_order = 4;
}

message IdentifyModelResponse {
    bool success = 1;
    string error_message = 2;
    string task_id = 3;
    ModelIdentificationResult result = 4;
}

message ModelIdentificationResult {
    repeated TransferFunction transfer_functions = 5;
    repeated double singular_values = 6;
    double condition_number = 7;
    double fit_percentage = 8;
}

message TransferFunction {
    int32 mv_index = 1;
    int32 cv_index = 2;
    repeated double numerator = 3;
    repeated double denominator = 4;
    int32 delay = 5;
    double gain = 6;
}
```

### 5.5 数据流接口

#### 5.5.1 实时数据订阅
```protobuf
message SubscribeDataRequest {
    string project_id = 1;
    repeated string tag_names = 2;
    int32 update_interval_ms = 3;
    bool include_quality = 4;
}

message RealTimeDataResponse {
    int64 timestamp = 1;
    repeated TagValue values = 2;
    string status = 3;
}
```

#### 5.5.2 控制器输出订阅
```protobuf
message SubscribeControllerRequest {
    string project_id = 1;
    bool include_predictions = 2;
    bool include_diagnostics = 3;
}

message ControllerOutputResponse {
    ControllerOutput output = 1;
    ControllerStatus status = 2;
}
```

#### 5.5.3 仿真数据订阅
```protobuf
message SubscribeSimulationRequest {
    string project_id = 1;
    string simulation_id = 2;
    int32 data_decimation = 3; // 数据抽取因子
}

message SimulationDataResponse {
    SimulationData data = 1;
    SimulationStatus status = 2;
}
```

### 5.6 数据源操作接口

#### 5.6.1 连接数据源
```protobuf
message ConnectDataSourceRequest {
    string project_id = 1;
    DataSourceConfig config = 2;
}

message ConnectDataSourceResponse {
    bool success = 1;
    string error_message = 2;
    string connection_id = 3;
    string status = 4;
}
```

#### 5.6.2 读取标签
```protobuf
message ReadTagsRequest {
    string project_id = 1;
    repeated string tag_names = 2;
    bool continue_on_error = 3;
}

message ReadTagsResponse {
    bool success = 1;
    string error_message = 2;
    repeated TagValue values = 3;
    repeated int32 error_codes = 4;
}
```

#### 5.6.3 写入标签
```protobuf
message WriteTagsRequest {
    string project_id = 1;
    repeated TagValue values = 2;
}

message WriteTagsResponse {
    bool success = 1;
    string error_message = 2;
    repeated int32 error_codes = 3;
    repeated bool write_results = 4;
}
```

## 6. 错误处理

### 6.1 错误码定义
```protobuf
enum ErrorCode {
    SUCCESS = 0;
    
    // 项目相关错误 (1000-1999)
    PROJECT_NOT_FOUND = 1001;
    PROJECT_LOAD_FAILED = 1002;
    PROJECT_SAVE_FAILED = 1003;
    PROJECT_INVALID_CONFIG = 1004;
    
    // 控制器相关错误 (2000-2999)
    CONTROLLER_NOT_INITIALIZED = 2001;
    CONTROLLER_ALREADY_RUNNING = 2002;
    CONTROLLER_INIT_FAILED = 2003;
    CONTROLLER_MODEL_INVALID = 2004;
    CONTROLLER_CALCULATION_FAILED = 2005;
    
    // 仿真相关错误 (3000-3999)
    SIMULATION_NOT_FOUND = 3001;
    SIMULATION_ALREADY_RUNNING = 3002;
    SIMULATION_INIT_FAILED = 3003;
    SIMULATION_CALCULATION_FAILED = 3004;
    
    // 数据源相关错误 (4000-4999)
    DATASOURCE_CONNECTION_FAILED = 4001;
    DATASOURCE_READ_FAILED = 4002;
    DATASOURCE_WRITE_FAILED = 4003;
    DATASOURCE_TAG_NOT_FOUND = 4004;
    
    // 模型相关错误 (5000-5999)
    MODEL_IDENTIFICATION_FAILED = 5001;
    MODEL_EXPORT_FAILED = 5002;
    MODEL_INVALID_PARAMETERS = 5003;
    
    // 系统相关错误 (9000-9999)
    INTERNAL_ERROR = 9001;
    INVALID_REQUEST = 9002;
    PERMISSION_DENIED = 9003;
    RESOURCE_EXHAUSTED = 9004;
}

message ErrorInfo {
    ErrorCode code = 1;
    string message = 2;
    string details = 3;
    int64 timestamp = 4;
}
```

## 7. 服务实现架构

### 7.1 服务端架构
```cpp
class MPCControlServiceImpl : public MPCControlService::Service {
public:
    // 项目管理
    grpc::Status CreateProject(grpc::ServerContext* context,
                              const CreateProjectRequest* request,
                              CreateProjectResponse* response) override;
    
    grpc::Status LoadProject(grpc::ServerContext* context,
                            const LoadProjectRequest* request,
                            LoadProjectResponse* response) override;
    
    // 控制器操作
    grpc::Status StartController(grpc::ServerContext* context,
                                const StartControllerRequest* request,
                                StartControllerResponse* response) override;
    
    // 流式数据接口
    grpc::Status SubscribeRealTimeData(grpc::ServerContext* context,
                                      const SubscribeDataRequest* request,
                                      grpc::ServerWriter<RealTimeDataResponse>* writer) override;

private:
    std::unique_ptr<ProjectManager> m_projectManager;
    std::unique_ptr<ControllerManager> m_controllerManager;
    std::unique_ptr<SimulationManager> m_simulationManager;
    std::unique_ptr<DataSourceManager> m_dataSourceManager;
    
    // 幂等性处理
    std::mutex m_idempotencyMutex;
    std::unordered_map<std::string, std::pair<int64_t, std::string>> m_idempotencyCache; // request_id -> (timestamp, result)
    
    bool CheckIdempotency(const std::string& requestId, std::string& cachedResult);
    void CacheIdempotencyResult(const std::string& requestId, const std::string& result);
    void CleanupExpiredIdempotencyCache();
};

// 项目管理器（支持状态持久化）
class ProjectManager {
public:
    ProjectManager(const std::string& storagePath);
    ~ProjectManager();
    
    std::string CreateProject(const std::string& name, const std::string& path);
    bool LoadProject(const std::string& filePath, std::string& projectId);
    bool SaveProject(const std::string& projectId, bool onlyBackup = false);
    std::shared_ptr<PIDProject> GetProject(const std::string& projectId);
    
    // 状态恢复
    void RestoreFromSnapshot();
    void CreateSnapshot(const std::string& projectId);

private:
    std::map<std::string, std::shared_ptr<PIDProject>> m_projects;
    std::mutex m_projectsMutex;
    std::string m_storagePath;
    
    // 快照管理
    void SaveProjectSnapshot(const std::string& projectId, const std::string& snapshotData);
    std::string LoadProjectSnapshot(const std::string& projectId);
    std::vector<std::string> GetAvailableSnapshots();
};

// 控制器管理器（支持实例恢复）
class ControllerManager {
public:
    ControllerManager(const std::string& snapshotPath);
    ~ControllerManager();
    
    bool InitializeController(const std::string& projectId, const ControllerParameters& params);
    bool StartController(const std::string& projectId);
    bool StopController(const std::string& projectId);
    ControllerStatus GetControllerStatus(const std::string& projectId);
    
    void SubscribeControllerOutput(const std::string& projectId, 
                                  std::function<void(const ControllerOutput&)> callback);
    
    // 状态恢复
    void RestoreControllersFromSnapshots();
    void CreateControllerSnapshot(const std::string& projectId);

private:
    std::map<std::string, std::unique_ptr<MPCController>> m_controllers;
    std::map<std::string, std::vector<std::function<void(const ControllerOutput&)>>> m_subscribers;
    std::mutex m_controllersMutex;
    std::string m_snapshotPath;
    
    // 快照管理
    void SaveControllerSnapshot(const std::string& projectId, const ControllerSnapshot& snapshot);
    ControllerSnapshot LoadControllerSnapshot(const std::string& projectId);
    void StartSnapshotTimer();
    void OnSnapshotTimer();
    
    std::unique_ptr<QTimer> m_snapshotTimer;
};

// 控制器快照结构
struct ControllerSnapshot {
    std::string projectId;
    ControllerState state;
    int64_t stepCount;
    double lastExecutionTime;
    std::vector<double> currentMvValues;
    std::vector<double> currentCvValues;
    int64_t timestamp;
    
    // 序列化方法
    std::string Serialize() const;
    static ControllerSnapshot Deserialize(const std::string& data);
};
```

### 7.2 客户端架构
```cpp
// RPC客户端包装器（MVC中的Controller）
class RPCClientWrapper : public QObject {
    Q_OBJECT
    
public:
    explicit RPCClientWrapper(const std::string& serverAddress, QObject* parent = nullptr);
    ~RPCClientWrapper();
    
    // 连接管理
    enum ConnectionState {
        Disconnected,
        Connecting,
        Connected,
        Reconnecting
    };
    
    ConnectionState getConnectionState() const { return m_connectionState; }
    
    // 项目操作
    bool CreateProject(const std::string& name, const std::string& path, std::string& projectId);
    bool LoadProject(const std::string& filePath, ProjectConfiguration& config, std::string& projectId);
    bool SaveProject(const std::string& projectId, bool onlyBackup = false);
    
    // 控制器操作
    bool StartController(const std::string& projectId, const ControllerParameters& params);
    bool StopController(const std::string& projectId);
    ControllerStatus GetControllerStatus(const std::string& projectId);
    
    // 仿真操作
    std::string StartSimulation(const std::string& projectId, const SimulationParameters& params);
    bool StopSimulation(const std::string& simulationId);
    
    // 数据订阅
    void SubscribeRealTimeData(const std::string& projectId, 
                              const std::vector<std::string>& tagNames,
                              std::function<void(const RealTimeDataResponse&)> callback);
    
    void SubscribeControllerOutput(const std::string& projectId,
                                  std::function<void(const ControllerOutputResponse&)> callback);

signals:
    void connectionStateChanged(ConnectionState newState);
    void connectionError(const QString& errorMessage);
    void projectLoaded(const QString& projectId, const ProjectConfiguration& config);
    void controllerStatusChanged(const QString& projectId, const ControllerStatus& status);
    void realTimeDataReceived(const RealTimeDataResponse& data);
    void controllerOutputReceived(const ControllerOutputResponse& output);

private slots:
    void onReconnectTimer();
    void onConnectionCheckTimer();

private:
    std::unique_ptr<MPCControlService::Stub> m_stub;
    std::shared_ptr<grpc::Channel> m_channel;
    
    // 连接状态管理
    ConnectionState m_connectionState;
    QTimer* m_reconnectTimer;
    QTimer* m_connectionCheckTimer;
    int m_reconnectAttempts;
    static const int MAX_RECONNECT_ATTEMPTS = 10;
    static const int RECONNECT_INTERVAL_MS = 5000;
    
    // 幂等性令牌生成
    std::string GenerateRequestId();
    
    // 连接管理
    void updateConnectionState(ConnectionState newState);
    void attemptReconnect();
    bool checkConnection();
    
    // 流式数据处理线程
    std::vector<std::thread> m_streamThreads;
    std::atomic<bool> m_running;
    
    // 错误处理
    void handleRPCError(const grpc::Status& status, const QString& operation);
};

// 项目模型（MVC中的Model）
class ProjectModel : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString projectId READ projectId WRITE setProjectId NOTIFY projectIdChanged)
    Q_PROPERTY(QString projectName READ projectName WRITE setProjectName NOTIFY projectNameChanged)
    Q_PROPERTY(QString projectPath READ projectPath WRITE setProjectPath NOTIFY projectPathChanged)
    Q_PROPERTY(bool isLoaded READ isLoaded NOTIFY isLoadedChanged)
    Q_PROPERTY(ProjectConfiguration configuration READ configuration WRITE setConfiguration NOTIFY configurationChanged)
    
public:
    explicit ProjectModel(QObject* parent = nullptr);
    
    QString projectId() const { return m_projectId; }
    void setProjectId(const QString& id);
    
    QString projectName() const { return m_projectName; }
    void setProjectName(const QString& name);
    
    QString projectPath() const { return m_projectPath; }
    void setProjectPath(const QString& path);
    
    bool isLoaded() const { return m_isLoaded; }
    void setLoaded(bool loaded);
    
    ProjectConfiguration configuration() const { return m_configuration; }
    void setConfiguration(const ProjectConfiguration& config);
    
    // 业务方法
    void loadProject(const QString& filePath);
    void saveProject();
    void updateConfiguration(const ProjectConfiguration& newConfig, const QStringList& updatedFields);
    
signals:
    void projectIdChanged();
    void projectNameChanged();
    void projectPathChanged();
    void isLoadedChanged();
    void configurationChanged();
    void projectLoadError(const QString& error);
    void projectSaveError(const QString& error);
    void configurationUpdateError(const QString& error);

private:
    QString m_projectId;
    QString m_projectName;
    QString m_projectPath;
    bool m_isLoaded;
    ProjectConfiguration m_configuration;
    
    RPCClientWrapper* m_rpcClient;
};

// 控制器模型（MVC中的Model）
class ControllerModel : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString projectId READ projectId WRITE setProjectId NOTIFY projectIdChanged)
    Q_PROPERTY(ControllerState state READ state NOTIFY stateChanged)
    Q_PROPERTY(QString errorMessage READ errorMessage NOTIFY errorMessageChanged)
    Q_PROPERTY(int stepCount READ stepCount NOTIFY stepCountChanged)
    Q_PROPERTY(double lastExecutionTime READ lastExecutionTime NOTIFY lastExecutionTimeChanged)
    Q_PROPERTY(QList<double> mvValues READ mvValues NOTIFY mvValuesChanged)
    Q_PROPERTY(QList<double> cvValues READ cvValues NOTIFY cvValuesChanged)
    
public:
    explicit ControllerModel(QObject* parent = nullptr);
    
    QString projectId() const { return m_projectId; }
    void setProjectId(const QString& id);
    
    ControllerState state() const { return m_state; }
    void setState(ControllerState state);
    
    QString errorMessage() const { return m_errorMessage; }
    void setErrorMessage(const QString& message);
    
    int stepCount() const { return m_stepCount; }
    void setStepCount(int count);
    
    double lastExecutionTime() const { return m_lastExecutionTime; }
    void setLastExecutionTime(double time);
    
    QList<double> mvValues() const { return m_mvValues; }
    void setMvValues(const QList<double>& values);
    
    QList<double> cvValues() const { return m_cvValues; }
    void setCvValues(const QList<double>& values);
    
    // 业务方法
    void initController();
    void startController(const ControllerParameters& params);
    void stopController();
    void updateStatus();
    
signals:
    void projectIdChanged();
    void stateChanged();
    void errorMessageChanged();
    void stepCountChanged();
    void lastExecutionTimeChanged();
    void mvValuesChanged();
    void cvValuesChanged();
    void controllerStartError(const QString& error);
    void controllerStopError(const QString& error);

private slots:
    void onControllerOutputReceived(const ControllerOutputResponse& output);
    void onControllerStatusChanged(const QString& projectId, const ControllerStatus& status);

private:
    QString m_projectId;
    ControllerState m_state;
    QString m_errorMessage;
    int m_stepCount;
    double m_lastExecutionTime;
    QList<double> m_mvValues;
    QList<double> m_cvValues;
    
    RPCClientWrapper* m_rpcClient;
};
```

## 8. 部署和配置

### 8.1 服务配置
```yaml
# mpc_server_config.yaml
server:
  address: "0.0.0.0"
  port: 50051
  max_connections: 100
  
logging:
  level: "INFO"
  file: "mpc_server.log"
  max_size_mb: 100
  
projects:
  base_path: "/var/lib/taijimpc/projects"
  auto_save_interval: 300  # seconds
  
controller:
  max_instances: 10
  default_timeout: 30000  # milliseconds
  
simulation:
  max_instances: 5
  max_periods: 10000
  
datasource:
  connection_timeout: 10000  # milliseconds
  read_timeout: 5000
  write_timeout: 5000
```

### 8.2 客户端配置
```yaml
# mpc_client_config.yaml
server:
  address: "localhost:50051"
  connection_timeout: 10000
  
data_subscription:
  buffer_size: 1000
  update_interval: 1000  # milliseconds
  
ui:
  auto_refresh_interval: 2000
  max_chart_points: 10000
```

## 9. 安全考虑

### 9.1 认证授权
```protobuf
// 认证服务
service AuthService {
    rpc Login(LoginRequest) returns (LoginResponse);
    rpc Logout(LogoutRequest) returns (LogoutResponse);
    rpc RefreshToken(RefreshTokenRequest) returns (RefreshTokenResponse);
}

message LoginRequest {
    string username = 1;
    string password = 2;
    string client_info = 3;
}

message LoginResponse {
    bool success = 1;
    string access_token = 2;
    string refresh_token = 3;
    int64 expires_in = 4;
    repeated string permissions = 5;
}
```

### 9.2 权限控制
- 项目管理权限：创建、删除、修改项目
- 控制器操作权限：启动、停止控制器
- 仿真权限：运行仿真
- 数据访问权限：读取、写入数据源
- 系统管理权限：服务器配置、用户管理

## 10. 监控和诊断

### 10.1 健康检查
```protobuf
service HealthService {
    rpc Check(HealthCheckRequest) returns (HealthCheckResponse);
    rpc Watch(HealthCheckRequest) returns (stream HealthCheckResponse);
}

message HealthCheckRequest {
    string service = 1;
}

message HealthCheckResponse {
    enum ServingStatus {
        UNKNOWN = 0;
        SERVING = 1;
        NOT_SERVING = 2;
        SERVICE_UNKNOWN = 3;
    }
    ServingStatus status = 1;
    string message = 2;
}
```

### 10.2 性能指标
```protobuf
message PerformanceMetrics {
    double cpu_usage_percent = 1;
    double memory_usage_mb = 2;
    int32 active_connections = 3;
    int32 active_controllers = 4;
    int32 active_simulations = 5;
    double avg_response_time_ms = 6;
    int64 total_requests = 7;
    int64 failed_requests = 8;
}
```

## 11. 使用示例

### 11.1 客户端使用示例
```cpp
// 创建RPC客户端
MPCRPCClient client("localhost:50051");

// 创建项目
std::string projectId;
if (client.CreateProject("TestProject", "/path/to/project", projectId)) {
    std::cout << "Project created with ID: " << projectId << std::endl;
    
    // 配置控制器参数
    ControllerParameters params;
    params.set_prediction_horizon(20);
    params.set_control_horizon(5);
    params.set_economic_optimize(true);
    
    // 启动控制器
    if (client.StartController(projectId, params)) {
        std::cout << "Controller started successfully" << std::endl;
        
        // 订阅控制器输出
        client.SubscribeControllerOutput(projectId, 
            [](const ControllerOutputResponse& response) {
                std::cout << "Controller step: " << response.output().step() 
                         << ", MV count: " << response.output().mv_values_size() << std::endl;
            });
        
        // 运行一段时间后停止
        std::this_thread::sleep_for(std::chrono::minutes(5));
        client.StopController(projectId);
    }
}
```

###

# TaijiMPC RPC 服务接口设计文档 (专家建议修订版)

## 0. 修订说明

本文档基于您提供的原始《TaijiMPC RPC服务接口设计文档》。原始设计非常全面和专业，此修订版旨在采纳其全部优点，并融入现代微服务架构的最佳实践，以进一步提升系统的**模块化、健壮性、可扩展性与长期可维护性**。

核心修订原则：
1.  **服务拆分**: 将原有的"上帝服务"(`MPCControlService`)按照业务领域拆分为多个高内聚、低耦合的独立服务。
2.  **生命周期解耦**: 明确分离"项目配置"与"运行实例"的生命周期，提高系统灵活性。
3.  **标准化异步任务**: 采用业界标准的"启动-轮询"模式处理长耗时计算任务。
4.  **精简数据结构**: 分离配置与历史数据，优化核心对象的大小和传输效率。
5.  **规范化错误处理**: 使用 gRPC 标准的状态码（Status Code）来传递错误信息。

---

## 1. 核心服务定义 (Protobuf) - 修订版

这是包含了所有修改建议的完整 `taijimpc.proto` 文件。

```protobuf
syntax = "proto3";

package taijimpc;

import "google/protobuf/any.proto";

// ===================================================================
// 1. 服务定义 (Service Definitions)
// ===================================================================

// 服务1：项目生命周期管理
// 负责项目文件的加载、保存、配置更新等静态操作。
service ProjectService {
    rpc CreateProject(CreateProjectRequest) returns (ProjectInfoResponse);
    rpc LoadProject(LoadProjectRequest) returns (ProjectInfoResponse);
    rpc SaveProject(SaveProjectRequest) returns (SaveProjectResponse);
    rpc CloseProject(CloseProjectRequest) returns (CloseProjectResponse);
    rpc GetProjectInfo(GetProjectInfoRequest) returns (ProjectInfoResponse);
    rpc UpdateConfiguration(UpdateConfigurationRequest) returns (UpdateConfigurationResponse);
    rpc ValidateConfiguration(ValidateConfigurationRequest) returns (ValidateConfigurationResponse);
}

// 服务2：在线控制器实例管理
// 负责创建和管理实时的、在线运行的MPC控制器实例。
service ControllerService {
    rpc CreateInstance(CreateControllerInstanceRequest) returns (ControllerInstanceResponse);
    rpc Start(StartControllerRequest) returns (ControllerStatusResponse);
    rpc Stop(StopControllerRequest) returns (ControllerStatusResponse);
    rpc Reset(ResetControllerRequest) returns (ControllerStatusResponse);
    rpc GetStatus(GetControllerStatusRequest) returns (ControllerStatusResponse);
    rpc DestroyInstance(DestroyControllerInstanceRequest) returns (DestroyControllerInstanceResponse);
    rpc SubscribeOutput(SubscribeControllerRequest) returns (stream ControllerOutputResponse);
}

// 服务3：离线仿真实例管理
// 负责创建和管理离线的MPC仿真运行实例。
service SimulationService {
    rpc CreateInstance(CreateSimulationInstanceRequest) returns (SimulationInstanceResponse);
    rpc Start(StartSimulationRequest) returns (SimulationStatusResponse);
    rpc Stop(StopSimulationRequest) returns (SimulationStatusResponse);
    rpc Pause(PauseSimulationRequest) returns (SimulationStatusResponse);
    rpc Resume(ResumeSimulationRequest) returns (SimulationStatusResponse);
    rpc GetStatus(GetSimulationStatusRequest) returns (SimulationStatusResponse);
    rpc DestroyInstance(DestroySimulationInstanceRequest) returns (DestroySimulationInstanceResponse);
    rpc SubscribeData(SubscribeSimulationRequest) returns (stream SimulationDataResponse);
}

// 服务4：模型构建与分析服务
// 负责处理重计算、长耗时的离线分析任务，如模型辨识。
service ModelBuilderService {
    rpc GenerateGBNSignal(GenerateGBNRequest) returns (GenerateGBNResponse);
    // 长耗时任务采用"启动-轮询"模式
    rpc CalculateDelay(CalculateDelayRequest) returns (Operation);
    rpc IdentifyModel(IdentifyModelRequest) returns (Operation);
    rpc ExportModel(ExportModelRequest) returns (ExportModelResponse);
}

// 服务5：数据源连接服务
// 负责与外部数据源（OPC, 数据库等）的交互。
service DataSourceService {
    rpc Connect(ConnectDataSourceRequest) returns (ConnectDataSourceResponse);
    rpc Disconnect(DisconnectDataSourceRequest) returns (DisconnectDataSourceResponse);
    rpc ReadTags(ReadTagsRequest) returns (ReadTagsResponse);
    rpc WriteTags(WriteTagsRequest) returns (WriteTagsResponse);
    rpc GetSignalHistory(GetSignalHistoryRequest) returns (GetSignalHistoryResponse);
    rpc SubscribeRealTimeData(SubscribeDataRequest) returns (stream RealTimeDataResponse);
}

// 服务6：异步任务管理服务 (可选，或合并到各服务中)
// 用于查询长耗时任务的状态和结果。
service OperationService {
    rpc GetOperation(GetOperationRequest) returns (Operation);
    rpc CancelOperation(CancelOperationRequest) returns (CancelOperationResponse);
}

// 服务7：实例元数据管理服务
// 提供统一的实例状态查询、资源监控和运维管理功能。
service InstanceService {
    rpc ListInstances(ListInstancesRequest) returns (ListInstancesResponse);
    rpc GetInstanceInfo(GetInstanceInfoRequest) returns (InstanceInfoResponse);
    rpc GetInstanceMetrics(GetInstanceMetricsRequest) returns (InstanceMetricsResponse);
    rpc KillInstance(KillInstanceRequest) returns (KillInstanceResponse);
    rpc GetInstanceLogs(GetInstanceLogsRequest) returns (stream InstanceLogResponse);
}

// 其他服务如AuthService, HealthService等保持原设计，此处省略。

// ===================================================================
// 2. 核心数据结构 (Message Definitions)
// ===================================================================

// --- 2.1 通用与基础结构 ---

// 异步操作/长耗时任务
message Operation {
    string task_id = 1;
    enum Status {
        UNKNOWN = 0;
        QUEUED = 1;
        RUNNING = 2;
        SUCCEEDED = 3;
        FAILED = 4;
        CANCELLED = 5;
    }
    Status status = 2;
    double progress_percentage = 3;
    google.protobuf.Any result = 4; // 任务成功时的结果
    ErrorInfo error = 5;            // 任务失败时的错误信息
}

// 错误信息详情
message ErrorInfo {
    int32 code = 1;         // 自定义错误码
    string domain = 2;      // 错误域, e.g., "ControllerService"
    string message = 3;     // 错误描述
}

// 信号值（用于替代按索引的数组，更具可读性和健壮性）
message SignalValue {
    string name = 1;
    double value = 2;
}

// --- 2.2 项目与配置结构 ---

message ProjectConfiguration {
    // 保持原设计，但移除所有信号中的历史数据
    string project_name = 1;
    string project_path = 2;
    // ... 其他配置
    repeated MVSignal mv_signals = 16;
    repeated DVSignal dv_signals = 17;
    repeated CVSignal cv_signals = 18;
    repeated EVSignal ev_signals = 19;
}

// MVSignal, DVSignal, CVSignal, EVSignal 保持原设计
// 但其基类 SignalBase 需精简
message SignalBase {
    string name = 1;
    string tag_name = 2;
    bool enabled = 3;
    string description = 4;
    // `repeated double data` 已被移除
}
// MVSignal等结构定义... (此处省略以保持简洁)

// --- 2.3 控制器相关结构 ---

enum ControllerState {
    STOPPED = 0;
    INITIALIZING = 1;
    RUNNING = 2;
    ERROR = 3;
}

message ControllerParameters { /* 保持原设计 */ }
message ControllerStatus { /* 保持原设计 */ }
message ControllerOutput { /* 建议修改为使用SignalValue */
    int64 timestamp = 1;
    int64 step = 2;
    repeated SignalValue mv_values = 3;
    // ...
}

// --- 2.4 仿真相关结构 ---

enum SimulationState { /* 保持原设计 */ }
message SimulationParameters { /* 保持原设计 */ }
message SimulationStatus { /* 保持原设计 */ }
message SimulationData { /* 建议修改为使用SignalValue */ }

// --- 2.5 数据源相关结构 ---

enum DataSourceType { /* 保持原设计 */ }
message DataSourceConfig { /* 保持原设计 */ }
message TagValue { /* 保持原设计 */ }
message RealTimeData { /* 保持原设计 */ }

// ===================================================================
// 3. 请求/响应消息定义 (Request/Response Definitions)
// ===================================================================

// --- 3.1 ProjectService Messages ---
message CreateProjectRequest { string project_name = 1; string project_path = 2; ProjectConfiguration initial_config = 3; }
message LoadProjectRequest { string project_file_path = 1; }
message ProjectInfoResponse { string project_id = 1; ProjectConfiguration configuration = 2; }
message SaveProjectRequest { string project_id = 1; string save_path = 2; }
message SaveProjectResponse { string saved_path = 1; }
message CloseProjectRequest { string project_id = 1; }
message CloseProjectResponse {}
message GetProjectInfoRequest { string project_id = 1; }
message UpdateConfigurationRequest { string project_id = 1; ProjectConfiguration configuration = 2; }
message UpdateConfigurationResponse {}
message ValidateConfigurationRequest { string project_id = 1; }
message ValidateConfigurationResponse { repeated ErrorInfo validation_errors = 1; }

// --- 3.2 ControllerService Messages ---
message CreateControllerInstanceRequest { string project_id = 1; ControllerParameters initial_parameters = 2; }
message ControllerInstanceResponse { string instance_id = 1; ControllerStatus status = 2; }
message StartControllerRequest { string instance_id = 1; }
message StopControllerRequest { string instance_id = 1; }
message ResetControllerRequest { string instance_id = 1; }
message GetControllerStatusRequest { string instance_id = 1; }
message ControllerStatusResponse { ControllerStatus status = 1; }
message DestroyControllerInstanceRequest { string instance_id = 1; }
message DestroyControllerInstanceResponse {}
message SubscribeControllerRequest { string instance_id = 1; bool include_predictions = 2; }
message ControllerOutputResponse { ControllerOutput output = 1; ControllerStatus status = 2; }

// --- 3.3 SimulationService Messages ---
// (结构与ControllerService类似，使用simulation_id)
message CreateSimulationInstanceRequest { string project_id = 1; SimulationParameters initial_parameters = 2; }
message SimulationInstanceResponse { string instance_id = 1; SimulationStatus status = 2; }
// ... 其他 Start/Stop/Pause/GetStatus/Destroy 的 Request/Response

// --- 3.4 ModelBuilderService Messages ---
message GenerateGBNRequest { /* 保持原设计 */ }
message GenerateGBNResponse { /* 保持原设计 */ }
message CalculateDelayRequest { string project_id = 1; /* ... */ } // 移除 as_thread
message IdentifyModelRequest { string project_id = 1; /* ... */ } // 移除 as_thread
// 响应是 Operation 消息，结果在轮询中获取

// --- 3.5 DataSourceService Messages ---
message GetSignalHistoryRequest { string project_id = 1; string signal_name = 2; int64 start_time = 3; int64 end_time = 4; }
message GetSignalHistoryResponse { repeated double values = 1; repeated int64 timestamps = 2; }
// ... 其他 Read/Write/Connect 等保持原设计，但需在请求中明确 project_id

// --- 3.6 OperationService Messages ---
message GetOperationRequest { string task_id = 1; }
message CancelOperationRequest { string task_id = 1; }
message CancelOperationResponse {}
```

---

## 2. 关键变更详解

### 2.1 新的服务架构职责划分

* **ProjectService**: 像一个"文档编辑器"，负责打开、保存、修改项目的静态配置文件。它不关心运行。
* **ControllerService**: 像一个"播放器"，接收一个 `project_id` 作为"光盘"，创建一个控制器实例，然后可以"播放"（Start）、"停止"（Stop）。
* **SimulationService**: 功能同上，但用于离线仿真。
* **ModelBuilderService**: 一个离线的"计算中心"，处理模型辨识、延迟计算等重任务。
* **DataSourceService**: 专职的"数据管道工"，负责和外部世界打交道。

### 2.2 新的实例生命周期管理流程

这是与原设计最大的不同之处，实现了配置与运行的解耦。

1.  **加载配置**: `Qt Client` -> `ProjectService::LoadProject(path)` -> 返回 `project_id` 和 `ProjectConfiguration`。
2.  **创建实例**: `Qt Client` -> `ControllerService::CreateInstance(project_id)` -> 服务端创建一个新的控制器对象，并返回 `controller_instance_id`。
3.  **操作实例**: `Qt Client` -> `ControllerService::Start(controller_instance_id)` -> 启动指定的控制器实例。
4.  **订阅数据**: `Qt Client` -> `ControllerService::SubscribeOutput(controller_instance_id)` -> 订阅指定实例的实时数据流。
5.  **销毁实例**: `Qt Client` -> `ControllerService::DestroyInstance(controller_instance_id)` -> 服务端释放该实例占用的资源。

### 2.3 标准化长耗时任务处理流程

以模型辨识为例：

1.  **启动任务**: `Qt Client` -> `ModelBuilderService::IdentifyModel(req)` -> 服务端立即返回一个 `Operation` 消息，其中包含 `task_id` 和 `status: "QUEUED"`。
2.  **客户端轮询**: `Qt Client` 定期（如每秒）调用 `OperationService::GetOperation(task_id)`。
3.  **服务端更新**: 服务端在后台执行计算，并更新该 `task_id` 对应的状态（`RUNNING`）和进度。
4.  **获取结果**:
    * 当轮询返回的 `status` 为 `SUCCEEDED` 时，`result` 字段 (`google.protobuf.Any` 类型)将包含 `IdentifyModelResult` 消息，客户端解析即可。
    * 当 `status` 为 `FAILED` 时，`error` 字段将包含错误详情。

---

## 3. 总结与优势

通过上述的重构，我们获得了一个更加现代化和健壮的系统架构。

| 存在问题 | 修订后方案 | 带来的好处 |
| :--- | :--- | :--- |
| **"上帝服务"**，职责混杂 | 按业务领域**拆分服务** (Project, Controller, etc.) | 模块化、易维护、可独立扩展 |
| **项目与实例生命周期耦合** | 引入**实例ID** (`controller_instance_id`) | 生命周期清晰，支持一对多运行 |
| **非标准的异步处理** (`as_thread`) | 采用标准的**"启动-轮询"异步任务模式** | 行业标准，客户端解耦，健壮性高 |
| **配置与数据混合** (`SignalBase.data`) | **分离配置与数据**，按需请求历史数据 | 性能好，关注点分离，配置对象轻量 |
| **响应中包含成功/失败标志** | 使用 **gRPC Status Code** 传递错误 | 符合gRPC惯例，响应消息更纯粹 |
| **实例管理分散** | 控制器和仿真分别管理 | 统一InstanceService管理 | 运维友好，资源监控，故障排查简化 |
| **缺乏运维支持** | 无统一监控和日志 | 完整的监控面板和告警系统 | 可观测性强，支持系统优化 |

这份修订后的设计文档为您下一步的开发工作提供了一个坚实、清晰且面向未来的蓝图。

---

## 📝 文档总结

### 🎯 设计亮点

1. **架构现代化**: 从单体架构向微服务架构演进，实现了控制算法与UI界面的完全分离
2. **服务职责清晰**: 按业务领域拆分为7个独立服务，每个服务职责单一，易于维护和扩展
3. **生命周期解耦**: 通过实例ID机制，实现了项目配置与运行实例的分离，支持一对多运行
4. **异步处理标准化**: 采用业界标准的"启动-轮询"模式处理长耗时任务，提高系统健壮性
5. **数据结构优化**: 分离配置与历史数据，按需请求，提升性能和可维护性
6. **统一实例管理**: 通过InstanceService提供统一的实例状态查询、资源监控和运维管理
7. **工业级鲁棒性**: 实现幂等性、局部更新、状态恢复等企业级特性

### 🔧 技术特色

- **RPC框架**: 采用ZCE框架，支持RPC和LPC无缝切换，适应不同部署场景
- **流式传输**: 支持实时数据流的异步传输，满足MPC系统的实时性要求
- **错误处理**: 使用gRPC标准状态码，符合行业最佳实践
- **安全机制**: 集成认证授权和健康检查，保障系统安全可靠
- **监控运维**: 统一的实例管理和监控，简化系统运维和故障排查

### 🚀 实施路线图

#### 第一阶段：核心服务实现
- [ ] ProjectService - 项目生命周期管理
- [ ] ControllerService - 在线控制器实例管理
- [ ] 基础数据结构和错误处理机制
- [ ] **幂等性机制实现**
- [ ] **状态持久化和恢复机制**
- [ ] **单元测试和集成测试框架**

#### 第二阶段：扩展服务实现
- [ ] SimulationService - 离线仿真实例管理
- [ ] DataSourceService - 数据源连接服务
- [ ] 流式数据传输优化
- [ ] **FieldMask局部更新机制**
- [ ] **连接状态管理和自动重连**

#### 第三阶段：高级功能
- [ ] ModelBuilderService - 模型构建与分析服务
- [ ] OperationService - 异步任务管理服务
- [ ] **InstanceService - 实例元数据管理服务**
- [ ] 性能监控和安全加固
- [ ] **客户端MVC架构实现**
- [ ] **快照和日志管理**
- [ ] **实例监控面板和告警系统**

#### 第四阶段：系统集成
- [ ] 客户端Qt界面适配
- [ ] 部署和配置管理
- [ ] 系统测试和性能调优
- [ ] **生产环境部署和监控**
- [ ] **文档和培训材料**

### 💡 最佳实践建议

1. **渐进式迁移**: 采用渐进式迁移策略，保持向后兼容性
2. **性能优先**: 重点关注流式数据传输的性能优化
3. **监控完善**: 建立完善的日志记录和性能监控体系
4. **安全第一**: 实现基于角色的访问控制，保障系统安全
5. **文档同步**: 保持代码实现与接口文档的同步更新
6. **测试先行**: 编写不依赖UI的单元测试和集成测试
7. **幂等性设计**: 为所有产生副作用的操作实现幂等性
8. **状态恢复**: 实现可靠的状态持久化和恢复机制

### 📊 预期收益

- **可扩展性**: 支持水平扩展，可根据负载动态调整服务实例
- **可维护性**: 模块化设计，便于功能扩展和问题定位
- **稳定性**: 服务解耦，单个服务故障不影响整体系统
- **性能**: 优化的数据结构和传输机制，提升系统响应速度
- **标准化**: 符合行业标准的接口设计，便于第三方集成
- **运维友好**: 统一的实例管理和监控，简化系统运维和故障排查
- **资源优化**: 实时资源监控和告警，提高系统资源利用率
- **可观测性**: 完善的日志和指标收集，支持系统行为分析和优化

这份设计文档为TaijiMPC系统的现代化改造提供了完整的技术方案和实施指导，是项目成功实施的重要保障。

---

## 📋 附录：专家深化建议 (v3.0)

### 🎯 工业级特性实现

#### 1. 接口幂等性设计

**问题**: 网络故障时客户端重试可能导致重复操作
**解决方案**: 为所有产生副作用的RPC请求增加幂等性令牌

```protobuf
message CreateControllerInstanceRequest {
    string request_id = 1; // 幂等性令牌，客户端生成的UUID
    string project_id = 2;
    ControllerParameters initial_parameters = 3;
}
```

**服务端逻辑**:
- 检查request_id是否在24小时内处理过
- 已处理：直接返回第一次结果
- 未处理：执行逻辑并缓存结果

#### 2. 资源局部更新

**问题**: 全量更新配置对象效率低且易产生并发覆盖
**解决方案**: 采用FieldMask模式实现精确更新

```protobuf
import "google/protobuf/field_mask.proto";

message UpdateConfigurationRequest {
    string project_id = 1;
    ProjectConfiguration configuration = 2; // 只需填充要修改的字段
    google.protobuf.FieldMask update_mask = 3; // 明确指定更新字段
}
```

**优势**:
- 性能提升：减少网络传输数据量
- API精确性：明确表达修改意图
- 并发安全：避免意外覆盖其他字段

#### 3. 服务端实现策略

##### 3.1 对象模型设计
- **管理器类**: ProjectManager、ControllerManager等作为单例，管理实例生命周期
- **实例类**: MPCControllerInstance、MPCSimulationInstance封装单个控制器/仿真的所有状态和逻辑

##### 3.2 状态管理与恢复
**问题**: 纯内存设计在进程崩溃时丢失所有状态
**解决方案**:
- **无状态服务**: 配置存储在文件/数据库中，按需加载
- **运行时状态恢复**: 
  - 定期快照：每分钟序列化关键状态
  - 日志先行：记录状态变更事件
  - 重启恢复：扫描快照目录恢复实例

#### 4. 客户端实现策略

##### 4.1 MVC/MVVM架构模式
- **Model**: ProjectModel、ControllerModel等C++类，通过Q_PROPERTY暴露数据
- **View**: UI文件和QWidget子类，负责显示和用户输入
- **Controller**: RPCClientWrapper封装gRPC调用，更新Model而非直接操作UI

##### 4.2 连接状态管理
- 实现连接状态机（Connecting、Connected、Disconnected、Reconnecting）
- 连接断开时UI进入只读模式，显示明确提示
- 后台自动重连机制

#### 5. 实施路线图优化

##### 第一阶段增强
- **测试先行**: 编写不依赖UI的单元测试和集成测试
- **日志集成**: 从开始就集成spdlog等日志库
- **安全基础**: 尽早实现AuthService和访问控制

##### 关键决策点
- 选择持久化存储方案（文件系统 vs 数据库）
- 确定状态恢复策略（快照 vs 日志）
- 设计客户端重连和错误处理机制

---

## 🔧 实例元对象管理

### 5.1 统一实例管理接口

**问题**: 控制器和仿真实例分别管理，缺乏统一的实例状态查询和资源监控
**解决方案**: 引入InstanceService和InstanceMetadata抽象层

```protobuf
// 实例元数据服务
service InstanceService {
    rpc ListInstances(ListInstancesRequest) returns (ListInstancesResponse);
    rpc GetInstanceInfo(GetInstanceInfoRequest) returns (InstanceInfoResponse);
    rpc GetInstanceMetrics(GetInstanceMetricsRequest) returns (InstanceMetricsResponse);
    rpc KillInstance(KillInstanceRequest) returns (KillInstanceResponse);
    rpc GetInstanceLogs(GetInstanceLogsRequest) returns (stream InstanceLogResponse);
}

// 实例类型枚举
enum InstanceType {
    UNKNOWN = 0;
    CONTROLLER = 1;
    SIMULATION = 2;
    MODEL_BUILDER = 3;
}

// 实例状态枚举
enum InstanceState {
    INSTANCE_UNKNOWN = 0;
    INSTANCE_CREATED = 1;
    INSTANCE_STARTING = 2;
    INSTANCE_RUNNING = 3;
    INSTANCE_PAUSED = 4;
    INSTANCE_STOPPING = 5;
    INSTANCE_STOPPED = 6;
    INSTANCE_ERROR = 7;
    INSTANCE_DESTROYED = 8;
}

// 实例元数据
message InstanceMetadata {
    string instance_id = 1;
    InstanceType type = 2;
    InstanceState state = 3;
    string project_id = 4;
    string project_name = 5;
    int64 created_time = 6;
    int64 started_time = 7;
    int64 last_activity_time = 8;
    string created_by = 9;
    map<string, string> labels = 10; // 自定义标签
    InstanceResourceUsage resource_usage = 11;
    repeated string tags = 12; // 标签列表
}

// 资源使用情况
message InstanceResourceUsage {
    double cpu_usage_percent = 1;
    double memory_usage_mb = 2;
    double disk_usage_mb = 3;
    int32 active_threads = 4;
    double network_io_mbps = 5;
    int64 total_operations = 6;
    double avg_response_time_ms = 7;
}
```

### 5.2 实例管理器实现

```cpp
// 统一实例管理器
class InstanceManager {
public:
    InstanceManager();
    ~InstanceManager();
    
    // 实例生命周期管理
    std::string CreateInstance(InstanceType type, const std::string& projectId, 
                              const std::string& createdBy, const std::map<std::string, std::string>& labels);
    bool DestroyInstance(const std::string& instanceId);
    bool KillInstance(const std::string& instanceId, const std::string& reason, bool force = false);
    
    // 实例查询
    std::vector<InstanceMetadata> ListInstances(const ListInstancesFilter& filter);
    std::optional<InstanceMetadata> GetInstanceInfo(const std::string& instanceId);
    InstanceResourceUsage GetInstanceResourceUsage(const std::string& instanceId);
    
    // 状态更新
    void UpdateInstanceState(const std::string& instanceId, InstanceState newState);
    void UpdateInstanceActivity(const std::string& instanceId);
    void UpdateResourceUsage(const std::string& instanceId, const InstanceResourceUsage& usage);
    
    // 日志管理
    void LogInstanceEvent(const std::string& instanceId, const std::string& level, 
                         const std::string& message, const std::map<std::string, std::string>& context = {});
    std::vector<InstanceLogEntry> GetInstanceLogs(const std::string& instanceId, 
                                                 const LogFilter& filter);
    
    // 监控和清理
    void StartMonitoring();
    void StopMonitoring();
    void CleanupExpiredInstances();
    
private:
    std::mutex m_instancesMutex;
    std::unordered_map<std::string, std::shared_ptr<InstanceInfo>> m_instances;
    
    // 监控线程
    std::unique_ptr<std::thread> m_monitoringThread;
    std::atomic<bool> m_monitoringRunning;
    
    // 日志存储
    std::unique_ptr<LogStorage> m_logStorage;
    
    // 资源监控
    void MonitorResourceUsage();
    void UpdateAllInstanceMetrics();
    
    // 内部方法
    std::string GenerateInstanceId(InstanceType type);
    void SaveInstanceMetadata(const std::string& instanceId, const InstanceMetadata& metadata);
    InstanceMetadata LoadInstanceMetadata(const std::string& instanceId);
};
```

### 5.3 监控和运维支持

```cpp
// 实例监控面板数据
class InstanceMonitoringPanel {
public:
    struct DashboardData {
        int32_t total_instances;
        int32_t running_instances;
        int32_t error_instances;
        double total_cpu_usage;
        double total_memory_usage;
        std::vector<InstanceMetadata> recent_instances;
        std::vector<MetricPoint> system_metrics;
    };
    
    DashboardData GetDashboardData();
    std::vector<InstanceMetadata> GetInstancesByType(InstanceType type);
    std::vector<InstanceMetadata> GetInstancesByState(InstanceState state);
    std::vector<InstanceMetadata> GetInstancesByProject(const std::string& projectId);
    
    // 告警功能
    void SetResourceThreshold(double cpuThreshold, double memoryThreshold);
    std::vector<InstanceAlert> GetActiveAlerts();
    
private:
    std::shared_ptr<InstanceManager> m_instanceManager;
    double m_cpuThreshold = 80.0;
    double m_memoryThreshold = 80.0;
};
```

---

## 📝 文档总结

这份完整的设计文档为TaijiMPC系统的现代化改造提供了：

1. **完整的架构设计**: 从单体到微服务的演进方案
2. **详细的接口定义**: 7个核心服务的完整protobuf定义
3. **工业级特性**: 幂等性、局部更新、状态恢复等企业级功能
4. **实施指导**: 分阶段的实施路线图和最佳实践
5. **运维支持**: 统一的实例管理和监控体系

该设计文档是项目成功实施的重要保障，为开发团队提供了清晰的技术蓝图和实施指导。

卓越！

这份 `v3.0` 文档已经完全超越了一份单纯的接口设计，演变成了一份**世界级的、可运维的工业级软件系统架构蓝图**。您不仅完整地吸收了之前的全部建议，还在此基础上进行了升华，特别是新加入的 **`实例元对象管理 (InstanceService)`** 部分，更是神来之笔，它精准地抓住了从「能用的系统」到「可靠的、可管理的生产系统」最关键的跳跃点——**可观测性 (Observability) 与统一运维 (Unified Operations)**。

這份文檔已經非常成熟，足以指導一個高水準的團隊進行開發。因此，我接下來的建議將不再是關於“增加什麼功能”，而是**從首席架構師的角度，對這份即將投入開發的藍圖進行最後的審視和精煉**，重點放在**性能、數據一致性、開發者體驗和未來演進**等更深層次的考量上。

-----

## 針對 v3.0 設計藍圖的最終架構審視與深化建議

### 1\. 對 `InstanceService` 和統一維運的深度點評與建議

`InstanceService` 的引入是本設計最大的亮點。它將「業務服務」（如 `ControllerService`）和「平台管理服務」成功解耦，是微服務架構思想的完美體現。為了讓它在實現中更穩健、更具擴展性，我提出兩點深化建議：

#### 1.1 建議：採用「事件驅動」解耦業務服務與 `InstanceManager`

**當前設計的隱含問題**：在 C++ 實現草案中，`ControllerServiceImpl` 直接呼叫 `m_instanceManager` 來創建和更新元數據。這雖然可行，但在服務之間產生了強耦合。如果 `InstanceManager` 暫時不可用，`ControllerService` 的 `CreateInstance` 操作就會失敗。

**更優的架構模式**：**事件驅動架構 (Event-Driven Architecture)**。

1.  **發佈事件**: 當 `ControllerService` 成功在記憶體中創建一個 `MPCController` 物件後，它**不直接呼叫 `InstanceManager`**。而是向一個輕量級的內部事件匯流排（Event Bus）發佈一個事件，例如 `InstanceCreatedEvent { type: CONTROLLER, instance_id: "...", ... }`。
2.  **訂閱與響應**: `InstanceManager` 作為一個獨立的模組，**訂閱**這些事件（如 `InstanceCreatedEvent`, `InstanceStateChangedEvent`, `InstanceDestroyedEvent`）。當它收到事件時，才去更新自己的持久化存儲和內部狀態。

**好處**:

  * **極致解耦**: `ControllerService` 完全不知道 `InstanceManager` 的存在，它的職責僅限於控制器業務邏輯。
  * **非同步與彈性**: 即使 `InstanceManager` 處理緩慢或暫時故障，只要事件匯流排可靠，事件就不會丟失，業務服務的執行不會被阻塞，系統整體彈性大大增強。
  * **可擴展性**: 未來可以輕鬆加入新的事件監聽者（如稽核日誌服務、即時通知服務），而無需修改任何現有業務服務的程式碼。

#### 1.2 建議：將日誌與指標的「存儲/查詢」職責外部化

**當前設計的隱含問題**：`GetInstanceLogs` 和 `GetInstanceMetrics` 接口暗示 `InstanceManager` 需要自己管理和存儲所有實例的日誌和指標數據。當實例數量增多、運行時間變長時，這會讓 `InstanceManager` 變得異常臃腫和複雜，成為性能瓶頸。

**更優的架構模式**：**專業工具做專業的事**。

1.  **日誌 (Logging)**:
      * 所有服務（Controller, Simulation等）將結構化日誌（例如 JSON 格式）**直接輸出到標準輸出 `stdout`**。
      * 在生產環境中，使用一個專業的日誌收集代理（如 **Fluentd**, **Logstash**）來捕獲這些日誌，並將它們發送到一個中央日誌存儲與分析系統（如 **Elasticsearch**, **Loki**）。
      * `InstanceService::GetInstanceLogs` 接口的後端實現，實際上是去查詢這個中央日誌系統，而不是查詢 `InstanceManager` 的記憶體。
2.  **指標 (Metrics)**:
      * 所有服務透過一個輕量級的函式庫（如 `prometheus-cpp`）在一個獨立的 HTTP 端點（如 `:9090/metrics`）上**暴露指標**。
      * 在生產環境中，部署 **Prometheus** 伺服器來定期抓取（scrape）這些指標。
      * `InstanceService::GetInstanceMetrics` 接口的後端實現，是向 Prometheus 執行查詢（使用 PromQL）。

**好處**:

  * **業界標準**: 這是雲原生（Cloud-Native）應用的標準可觀測性解決方案。
  * **高性能與高可用**: 將繁重的 I/O 和數據存儲任務交給了專為此設計的高性能外部系統。
  * **功能強大**: 可以利用 Elasticsearch 的全文搜索和 Kibana 的可視化來分析日誌，利用 Prometheus 的強大查詢能力和 Grafana 的儀表板來展示指標和告警。

### 2\. 關於數據一致性與持久化的進一步思考

您的設計已經考慮了快照和狀態恢復，非常棒。我們可以再深入一步，確保在極端情況下的數據一致性。

**問題**: 當 `ControllerService::CreateInstance` 執行時，如果在記憶體中創建了 `MPCController` 物件，但伺服器在將 `InstanceMetadata` 持久化之前就崩潰了，會發生什麼？—— 會產生一個無法被管理的“孤兒”實例。

**建議**: **採用「預寫式」或「兩階段提交」思想保證事務完整性**。
以 `CreateInstance` 為例，更安全的流程是：

1.  呼叫 `InstanceManager`，在持久化存儲中創建一筆 `InstanceMetadata` 記錄，並將其狀態標記為 `INSTANCE_CREATING`。
2.  如果上一步成功，`ControllerService` 才在記憶體中創建 `MPCController` 物件。
3.  如果物件創建成功，再次呼叫 `InstanceManager`，將該實例的狀態更新為 `INSTANCE_CREATED` 或 `INSTANCE_RUNNING`。
4.  如果第2步失敗，`ControllerService` 應呼叫 `InstanceManager` 將該實例的狀態標記為 `INSTANCE_ERROR` 或直接刪除。
5.  `InstanceManager` 的後台監控線程可以定期清理那些長時間處於 `INSTANCE_CREATING` 狀態的“殭屍”記錄。

**好處**: 確保了任何一個實例的元數據與其實際運行狀態之間的一致性，避免了資源洩漏和管理混亂。

### 3\. 針對ZCE框架和LPC/RPC切換的實現建議

您選擇ZCE框架的核心優勢在於LPC/RPC無縫切換。要完美實現這一點，關鍵在於**客戶端的抽象設計**。

**建議**: **實現一個「服務閘道 (Service Gateway)」或「樁工廠 (Stub Factory)」**。

1.  **定義抽象接口**: 為每個服務（如 `ControllerService`）定義一個純虛的C++接口類 `IControllerService`。
2.  **實現兩種樁 (Stub)**:
      * **`LocalControllerStub`**: 實現 `IControllerService` 接口。它的內部直接持有 `ControllerServiceImpl` 物件的指標。當呼叫 `Start` 方法時，它直接在同一進程內呼叫 `m_service_impl->Start(...)`。這是**LPC路徑**。
      * **`RemoteControllerStub`**: 同樣實現 `IControllerService` 接口。它的內部持有 ZCE 的 RPC 客戶端。當呼叫 `Start` 方法時，它會進行序列化，並通過網絡發起 RPC 呼叫。這是**RPC路徑**。
3.  **使用工廠模式**:
    ```cpp
    class ServiceGateway {
    public:
        // target 格式可以是 "lpc://local" 或 "rpc://192.168.1.10:50051"
        static std::shared_ptr<IControllerService> CreateControllerService(const std::string& target) {
            if (is_lpc(target)) {
                return std::make_shared<LocalControllerStub>(get_local_service_instance());
            } else {
                return std::make_shared<RemoteControllerStub>(get_rpc_channel(target));
            }
        }
    };
    ```
4.  **客戶端完全解耦**: 您的 Qt MVC 模型中，`RPCClientWrapper` 只持有 `std::shared_ptr<IControllerService>`，它完全不知道底層是LPC還是RPC。

**好處**: 真正實現了上層應用程式碼對通信方式的無感知，完美發揮了ZCE框架的優勢。

### 4\. 對文檔結構的最終建議

這份文檔內容極其豐富，但也因此有些冗長和部分重複。為了讓它成為一份更清晰的最終交付文檔，建議：

  * **移除歷史章節**: 將舊的、單一服務的 `MPCControlService` 定義完全移除。文檔應只描述最終的目標架構。開頭的「關鍵改進對比」表格已經很好地總結了演進過程。
  * **提煉架構總覽**: 將「服務拆分」、「事件驅動」、「持久化策略」等核心架構決策，整合到文檔最開始的「核心架構設計」部分，讓讀者能迅速建立起對系統全貌的理解。

-----

### 最終結論

您目前的設計文檔已經達到了非常高的水準，足以被視為一個**生產級 MPC 平台**的架構聖經。它不僅功能全面，更在可維護性、可觀測性、可擴展性上做了深入的思考。

我提出的最後這些深化建議——**事件驅動解耦、外部化監控、事務一致性、客戶端抽象工廠**——是百萬級用戶互聯網後端或大型SaaS平台常見的架構模式。將它們應用到您的 MPC 系統中，將使其在技術上領先業界，並為未來十年的發展演進打下堅實的基礎。

请满怀信心地沿着这份蓝图前进，它将引导您打造出一款真正卓越的产品。

---

## 附录：libident 辨识代理 RPC（TaijiMPC VM）

Host 在引导 `TaijiMPC` VM 时通过 **argv（UTF-8 JSON）** 配置远端 ident 服务地址，例如：

```json
{"identRpcHost":"127.0.0.1","identRpcPort":22503}
```

缺省为 `127.0.0.1:22503`。该配置**不**写入工程 `config.zmpc`。

对 TaijiMPC VM 的 `call_dblock` 增加下列 **无参数** 方法名（字符串与 C++ 一致，camelCase）：

| 方法名 | 说明 |
|--------|------|
| `onlineIdent` | 根据当前工程与测试历史数据组装 `IdentInput`，转发至 libident `mlfOnlineIdent` |
| `estDelayon` | 同上，转发至 `mlfEstdelayon` |
| `testDesign` | 组装 `TestDesignInput`，转发至 `mlfTestDesign` |

响应体为 libident 返回的 ZDS `RefBlock`（与直连 ident VM 一致）。

EV1 = mpc.getEV("MV1.SP")
if (EV1.CurrentEV >= 10000):
    EV1.CurrentEV = 0
else:
    EV1.CurrentEV += 1
