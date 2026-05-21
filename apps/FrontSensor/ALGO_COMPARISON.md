# 算法对比：VB 原版 vs Qt 移植版

本文档记录 FrontSensor VB6 → Qt6 迁移中，核心算法实现与 VB 原版的差别，供后续调优和 Bug 溯源参考。

---

## 一、LPLS（线性 PLS）

### 对应关系

| VB 函数 | Qt 函数 | 说明 |
|---|---|---|
| `LPLS_Init` | — | Qt 不需要显式初始化，`LplsModel` 在 `lplsTrain` 内填充 |
| `Train_Epoch` (NIPALS 1步) | `nipalsOneStep` (迭代至收敛) | 见下方差别 1 |
| `LPLS_TrainCrva` | `lplsTrainBest` | CV 选最优潜变量数 |
| — (手动指定 LV) | `lplsTrain` | 指定固定潜变量数训练 |
| `LPLS_Prediction` | `lplsPredict` | 预测 |
| — | `lplsCvQ2` | 独立 Q² 计算（VB 内嵌在 TrainCrva） |
| — | `computeR2` | 独立 R² 辅助函数 |

### 差别

#### 1. NIPALS 内层迭代：1 步 vs 收敛

**VB** (`Train_Epoch`) 每次调用只做 **1 步** NIPALS 更新（外层循环由调用方控制），且对 PLS1（单输出）直接取 `u = y`，内层 t←u、p←X'u、q←Y't、u←Y*q 各做一次即退出。

**Qt** (`nipalsOneStep`) 迭代直到 `t` 向量收敛（默认 200 次迭代，容限 1e-10），单次调用即完成一个潜变量的完整 NIPALS。

**影响**：对 PLS1（单化验值），`u = y_centered / ||y_centered||` 后 t-u 的循环一步即收敛，两者数值上等价。多输出场景（PLS2，本项目不用）才有实质区别。

#### 2. 标准化：种群标准差 vs 样本标准差

**VB**（`Split_Data`）：除以 `√(Σ(x-μ)²/n)`（总体标准差，分母 n）

**Qt**（`standardize`）：除以 `√(Σ(x-μ)²/(n-1))`（样本标准差，分母 n-1）

**影响**：n 足够大时差异可忽略（< 1%）。建模样本通常 ≥ 50 个，无实质影响。

#### 3. CV 标准化范围

**VB**：每折用**全体训练集**的均值/标准差来标准化测试折（全局一次）。

**Qt** (`lplsCvQ2`)：每折独立计算该折训练子集的均值/标准差再标准化测试折（折内归一化）。

**影响**：会导致 Q² 数值略有差异，但 `lplsTrainBest` 用于选最优 LV 数的排序关系不受影响。

#### 4. Q²/R² 命名约定（VB 反转）

**VB** 的命名：
- `tpls.Rsquare(lv)` 实际存的是 **CV 指标**（= 1 - CV_SSE / TSS），即 Q²
- `tpls.Qsquare(lv)` 实际存的是**训练集 R²**

**Qt** 命名符合惯例：`r2_train` = 训练 R²，`q2_cv` = CV Q²。

在 Step 3 中，VB `LVRule=0` 选 `BestRLatent`（按 Rsquare 最大），对应 Qt 的 `lplsTrainBest → r2_train`，两者含义一致（都按 CV 指标选最优 LV）。

#### 5. p 向量归一化约定

VB：`p` 不归一化，`t` 归一化（`t = t / ||t||`），残差计算用 `X -= t * p'`。

Qt：同样约定，数值上等价。

---

## 二、GA（遗传算法）

### 对应关系

| VB 函数 | Qt 函数 |
|---|---|
| `InitPop` | `makeRandom` |
| `Transcode` | `decodeChrom` / `decodeGene` |
| `Dectobin` / `Bintodec` | `encodeGene` / `decodeGene` |
| `EvalFit` | `evaluateChrom` + 外部 fitness lambda |
| `Selection_线性排名_单约束` | `linearRankSelect` |
| `Crossover` | `crossover` |
| `Mutation` | `mutate` |
| `Elitist_单约束` | inline 精英更新（`gaRun:235-241`） |
| `CheckPop_Range` | 无对应 |
| `CalcAvgFit` | inline 均值计算（`gaRun:244-246`） |
| `GA` | `gaRun` |

### 差别

#### 1. 染色体表示

| 方面 | VB | Qt |
|---|---|---|
| 存储 | `typChrom.code As String`（'0'/'1' 字符串） | `Chrom.bits: vector<uint8_t>`（每字节 0 或 1） |
| 操作 | VB 字符串拼接（慢） | 直接字节访问（快） |
| 语义 | 相同 | 相同 |

#### 2. 种群规模公式（重要）

**VB**（调用侧）：
```
opt.PopSize = CLng(factor × n_GA变量数)
```
按**变量个数**缩放。

**Qt**（`GeneticAlgo.cpp:183`）：
```cpp
pop_size = factor × total_bits   // total_bits = Σ bits[i]
```
按**总比特数**缩放。

**影响**：10 个变量、每变量 8 位、factor=5 时：VB 种群=50，Qt 种群=400。Qt 种群通常大得多，计算量也大得多。VB 语义更直觉（每变量有 factor 个候选）；Qt 偏信息论。

#### 3. 选择：merged pool（最显著的算法差别）

**VB**（`GA_Module.bas:778-794`）：

- `iter=2`：仅从 `curpop` 选
- `iter≥3`：合并 `curpop + prvpop` → `tmppop`（2×PopSize），从中选

```vb
For j = 1 To PopSize
    tmppop(j)           = curpop(j)
    tmppop(PopSize + j) = prvpop(j)
Next j
Call Selection_线性排名_单约束(tmppop, curpop, SelPres)
```

**Qt**：永远只从当前 `pop` 选，无合并历史代的逻辑。

**影响**：VB 的 merged-pool 是"稳态"压力机制——历史代优秀个体不会因一次运气不好的选择而消失，等效于维护了 2×PopSize 的候选池。Qt 每代完全替换，保留仅靠精英策略。

#### 4. 收敛判据

**VB**（`:811`）：
```vb
Abs(avgfit(iter) - avgfit(iter-1)) <= tolerance * avgfit(iter)
```
**相对容限**：变化量 ≤ `tol × 当前均值`

**Qt**（`:247`）：
```cpp
std::abs(avg - prev_avg) < params.convergence_tol
```
**绝对容限**：变化量 < `tol`

**影响**：R²≈0.8 时，VB 实际阈值约 `0.01×0.8=0.008`；Qt 固定 `0.01`。两者在 R²≈1 时接近，R²≪1 时差异较大。

#### 5. `CheckPop_Range`：基因硬裁剪（VB 独有）

VB 在初始化后（`:765`）和每次进化后（`:802`）调用 `CheckPop_Range`：若解码值超过独立的 `limit[j]`，将那段比特串替换为 `limit[j]` 的编码。

Qt 无对应机制。解码时 `clamp(lo, hi)` 确保不超界，`hi` 已是唯一上界，效果等价（Step 3 中 limit=hi，该调用为空操作）。

#### 6. FastEval 适应度缓存（VB 独有）

**VB**（`:450-456`）：从第 2 代起（`FastEval=1`），对当代每条染色体先在 `prvpop` 中全表搜索相同编码，若找到则直接复用适应度，跳过 LPLS 计算：

```vb
If FastEval = 1 Then
    For j = 1 To npop
        If StrComp(curpop(i).code, prvpop(j).code) = 0 Then
            k = j: Exit For
        End If
    Next j
End If
```

**Qt**：每条染色体无论是否变化都重新计算。选择后相当一部分个体与上代相同，VB 此处有显著加速。

#### 7. 终止条件 off-by-one

**VB**（`:811-812`）：`sustain > Patience`（需要 Patience+**1** 个连续平坦代才终止）

**Qt**（`:248`）：`stagnation >= patience`（Patience 个连续平坦代即终止）

#### 8. RNG 播种

**VB**（`:759`）：`Call rndinit(opt.RandSeed)` — 所有 `ExecCount` 轮运行前播种**一次**，各轮顺序消耗同一 RNG 状态，完全可复现。

**Qt**（`:197-199`）：每轮重新播种（`rng.seed(rng() ^ (run * 1013))`），各轮有额外的随机性差异。

#### 9. 通用性设计

**VB** 的 `GA()` 通过 `Task` 参数（1=动态初选、2=变量选择、3=动态精选）在内部 `EvalFit` 中切换逻辑，算法与业务深度耦合。

**Qt** 的 `gaRun` 通过 `GaFitnessFn` 回调完全解耦，业务逻辑在调用侧 lambda 中，GA 本体不知道任务类型。

### 实际影响排序

| 差别 | 对结果的影响 |
|---|---|
| 种群规模公式 | **高**——Qt 种群可能大 8–10×，收敛更稳但慢很多 |
| merged pool 选择 | **中**——VB 保留历史代优秀个体，多样性更高 |
| FastEval 缓存 | **无（结果），高（速度）**——Qt 不缓存是纯粹的性能劣化 |
| 收敛判据 | **低-中**——R²≈0.8 时阈值差异约 20% |
| RNG 播种 | **低**——多轮结果仍稳定 |
| CheckPop_Range | **无**（Step 3 中 limit=hi，无实际效果） |
