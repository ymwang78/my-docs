# DATA_MODEL — VB6 ↔ C++ 字段映射对照表

本文档记录 Qt 移植中 **数据模型字段** 的中英对照，方便排查算法移植时的字段语义。命名遵循：

* C++ 类型用 PascalCase（`AuxVariable`），字段 snake_case（`min_value_s1`）。
* 时间长度统一存储为 `double` (秒)，时刻存为 `QDateTime`/`int64` Unix 时间戳。

> 本文同步随 Phase 推进更新；Phase 1 已覆盖所有 VB `typ*` 与 `cls*` 类型。

---

## ProjectModel (was 全局变量_建模.bas globals)

| 旧 (VB) | 新 (C++) | 说明 |
|---|---|---|
| `工程名称` | `name_` | QString |
| `工程描述` | `description_` | QString |
| `工程文件名` | `file_path_` | QString，绝对路径 |
| `工程已修改` | `is_modified_` | bool |
| `程序步骤` | `current_step_` (`PipelineStep`) | enum 0..6 |
| `版本号` | `format_version_` | int32, current = 1 |
| `sample_period` | `sample_period_seconds_` | int32 (秒) |
| `nauxfile`, `辅助数据文件()` | `aux_files_` | std::vector<DataFile> |
| `nlabfile`, `化验数据文件()` | `lab_files_` | std::vector<DataFile> |
| `辅助数据变量()` | `aux_data_vars_` | std::vector<DataVariable> |
| `化验数据变量()` | `lab_data_vars_` | 同上 |
| `辅助建模变量()` | `aux_vars_` | std::vector<AuxVariable> |
| `化验建模变量` | `lab_var_` | LabVariable (单个) |
| `data_aux_raw / data_lab_raw / bad_*_raw` | `aux_raw_frame_` / `lab_raw_frame_` | Frame (rows×cols + bad) |
| `data_aux / data_lab / bad_*` | `aux_clean_frame_` / `lab_clean_frame_` | 同上 |
| `tmd_*` | `tmd_frame_` | 时滞对齐后的建模数据 |
| `fmd_*` | `fmd_frame_` | 变量选择后的建模数据 |
| `fmd_pred()` | `fmd_pred_` | Frame |
| `fpd_*` | `fpd_pred_` | Frame |

---

## DataFile (typ数据文件)

| VB | C++ |
|---|---|
| `文件名` | `file_name` |
| `文件路径` | `file_path` |
| `变量数` | `variable_count` |
| `纪录数` | `record_count` |
| `采样周期` | `sample_period_seconds` |
| `起始时间` | `start_time` (QDateTime) |
| `结束时间` | `end_time` (QDateTime) |

---

## DataVariable (typ数据变量)

| VB | C++ |
|---|---|
| `名称` | `name` |
| `来源` | `source_file` |
| `选用` | `selected` (bool) |

---

## AuxVariable (typ辅助变量)

完整 50+ 字段参见 `Model/AuxVariable.h`。摘要：

| 阶段 | VB | C++ |
|---|---|---|
| 通用 | `名称 / 单位 / 描述` | `name / unit / description` |
| 上下限 | `上下限来源` | `bound_source` (`BoundSource` enum) |
| **S1** | `最小值S1 / 最大值S1 / 平均值S1 / 最小变化量S1 / 最大变化量S1 / 绘制上下限S1` | `min_value_s1 / max_value_s1 / mean_value_s1 / min_change_s1 / max_change_s1 / plot_upper_s1 / plot_lower_s1` |
| **S2** | `坏值个数 / 边界检查 / 有效上下限 / 呆滞{检查,窗长,容限} / 跳变{检查,窗长,容限}` | `bad_count / boundary_check / valid_{upper,lower} / stale_{check,window_s,tolerance} / step_{check,window_s,tolerance}` |
| **S2 stats** | `*S2` | `_s2` 后缀 |
| **S3** | `滞常搜索策略S3 / 预测贡献度S3 / *滞常S3 / 滞常精度S3` | `lag_tau_strategy_s3` (`SearchStrategy::GA / Preset`)、`prediction_contribution_s3` 等 |
| **S4** | `变选搜索策略S4 / 预测贡献度S4 / 变量选中率S4 / 估计变选S4 / 修正变选S4` | `var_select_strategy_s4` (`GA / ForceOn / ForceOff`)、`selection_rate_s4`、`estimated_select_s4` (0/1)、`corrected_select_s4` (0/1) |
| **S5 lag** | `时滞搜索策略S5 / *时滞S5` | `lag_strategy_s5 / *_lag_s5` |
| **S5 tau** | `时常搜索策略S5 / *时常S5` | `tau_strategy_s5 / *_tau_s5` |
| **S6** | `变量选择S6 / 变量时滞S6 / 变量时常S6` | `variable_select_s6 (0/1) / variable_lag_s6 / variable_tau_s6` |

---

## LabVariable (typ化验变量)

类似 AuxVariable，但增加：

| VB | C++ |
|---|---|
| `训练/测试/整体数据数` | `train_count / test_count / total_count` |
| `训练R2指标 / 训练均方根误差 / 训练平均绝对误差 / 训练最大绝对误差` | `train_r2 / train_rmse / train_mae / train_max_ae` |
| `测试*` / `整体*` | `test_*` / `total_*` |
| `绘制上下限S6` | `plot_upper_s6 / plot_lower_s6` |

---

## Constraint (typ组合约束)

| VB | C++ |
|---|---|
| `约束参数` (0:时滞 1:时常 2:时滞+时常) | `param` (`ConstraintParam::Lag/Tau/LagAndTau`) |
| `左变量下标 / 右变量下标` | `left_idx / right_idx` (注意：VB 1-based → C++ 0-based) |
| `约束符号` (0:≤ 1:= 2:≥) | `relation` (`ConstraintRelation`) |
| `偏置符号` (0:- 1:+) | `bias_sign` (`ConstraintBiasSign`) |
| `偏置时间` | `bias_seconds` (秒) |
| `约束变量集` | `variable_set` (QString) |
| `最大/最小选中数` | `max_select_count / min_select_count` |

---

## StepParams (typ导入/清洗/初选/变选/精选/建模全局参数)

每个步骤定义一个 struct：`ImportParams / CleaningParams / PrelimSelectParams / VarSelectParams / FineSelectParams / ModelBuildParams` + 共用 `PlsCommon / GaCommon`。所有步骤都包含 `executed_state` (`StepStatus::NotExecuted / Executed / Skipped`)。

| VB 类型 | C++ 类型 | 主字段映射 |
|---|---|---|
| `typ导入全局参数` | `ImportParams` | `执行状态 → executed_state` |
| `typ清洗全局参数` | `CleaningParams` | `数据平均策略 → average_strategy`, `数据平均窗长 → average_window_s`, `测试集选择策略 → test_set_strategy (Random/Block)`, `测试集数据比例 → test_set_ratio`, `测试集随机种子 → test_set_seed`, `相关性窗长/分辨率 → correlation_window_s/resolution` |
| `typ初选全局参数` | `PrelimSelectParams` | `PLS{最大隐变量数,交叉验证段数,最佳隐变量数,交叉验证误差,模型精度指标} → pls.{pls_max_latents,...}` ; `GA{执行次数,种群因子,最大代数,收敛容限,持续次数,选择压力,交叉概率,变异概率,惩罚权重,随机种子} → ga.{...}`; `动态类型 → dynamic_type (LagModel/TauModel)`, `搜索分辨率 → search_resolution` |
| `typ变选全局参数` | `VarSelectParams` | + `变量选择算法 → algorithm (SinglePass/MultiRound)`, `模型复杂度权重 → complexity_weight`, `级联筛选阈值 → cascade_threshold` |
| `typ精选全局参数` | `FineSelectParams` | + `时滞分辨率 → lag_resolution`, `时常分辨率 → tau_resolution` |
| `typ建模全局参数` | `ModelBuildParams` | `建模方法 → method (ModelMethod)`, 各模型族超参（LPLS/NPLS/JITL/SVR/ANN）按前缀分组 |
| `typ搜索参数` | `LMSearchParams` | `maxiter / FTolerance / XTolerance / LmStartValue → max_iter / f_tolerance / x_tolerance / lm_start_value` |

---

## SoftSensor 族 (cls软测量 / cls输入变量 / cls输出变量 / cls化验变量)

| VB | C++ |
|---|---|
| `cls软测量` | `SoftSensor`（持有 `inputs_` 数组、`output_`、`lab_`） |
| `cls输入变量` (`TimeDelay/TimeTau/LimitChk/ValidHi/ValidLo/Value`) | `SoftSensorInput` (`time_delay_s/time_tau_s/limit_check/valid_upper/valid_lower/measured_value`) |
| `cls输出变量` (+ `PredBias`) | `SoftSensorOutput` (+ `pred_bias / predicted_value`) |
| `cls化验变量` (`LabData/LabTime/CorrFlag/CorrCoef/CorrDead/PredAvgTime/BiasFiltTime`) | `SoftSensorLab` (`lab_value/lab_time_unix/correction_flag/correction_coef/correction_dead/pred_avg_window_s/bias_filter_time_s`) |
| `FixedQueue.cls` (`InitializeQueue/Enqueue/HeadDequeue/ResizeQueue`) | `template<class T> FixedQueue` (`initialize/enqueue/dequeueHead/resize`) |

---

## Search results (初/变/精选候选种子)

| VB | C++ |
|---|---|
| `*候选种子()` | `std::vector<CandidateSeed>` |
| 各阶段独立的种子内容（doubles 或 0/1 标志） | `payload` 字段（`QByteArray`，按阶段约定布局） |

---

## 序列化层

C++ Model 类型（`AuxVariable` 等）持有 `QString / QDateTime / std::vector<...>` ——便于 UI 使用。
持久化时由 `ProjectSerializer` 转换为 `FrontSensorProto::FS*` POD 类型，再调用 `zce::zdp::zds_pack/zds_unpack`：

```text
                modelToProto                zds_pack
ProjectModel  ─────────────►  FSProject ──────────────► bytes (磁盘)

                protoToModel                zds_unpack
ProjectModel  ◄─────────────  FSProject ◄────────────── bytes (磁盘)
```

Schema 在 `Model/ProjectData.ptl`。**字段增改必须同步更新 schema 与 `ProjectSerializer.cpp` 的两个映射函数**。
