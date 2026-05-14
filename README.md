# Study 3 — 交付物

3-wave longitudinal leadership survey data, 79 leaders × 438 followers，
two-level random-intercept multilevel path model on follower scale scores。

## 文件结构

```
.
├── data/                                问卷原始数据 + 清洗后数据
│   ├── T1_raw.xlsx       T1_cleaned.xlsx
│   ├── T2_raw.xlsx       T2_cleaned.xlsx
│   ├── T3_leader_raw.xlsx     T3_leader_cleaned.xlsx
│   ├── T3_follower_raw.xlsx   T3_follower_cleaned.xlsx
│   ├── final_merged_analysis_data.xlsx   最终可分析数据 (438 行 × 79 leaders)
│   └── study3_mcfa.dat                   Mplus 输入文件（数值 CLID 在第 1 列）
│
├── results/                             填答结果表
│   ├── Model1.xlsx                      主模型（含 controls）
│   ├── Model2.xlsx                      no-controls 稳健性
│   ├── Model3.xlsx                      follower-rated outcome 稳健性
│   ├── measurement appendix.xlsx        MCFA + 单量表 cluster-adjusted CFA
│   ├── ICC空模型.xlsx                   null-model ICC
│   └── YUYU样本量变化.xlsx              样本量流失表
│
└── code/                                run model 的代码
    ├── analysis_code.R                  R: multilevel path models, ICC,
    │                                       descriptives, Monte-Carlo CI (20 000 reps)
    └── mcfa_mplus_syntax.inp            Mplus: 5/4/3/2-factor MCFA 语法
```

## 数据清洗规则

- **T1**：~10 个非核心变量缺失值；~10 个重复 ID（清洗时删除）
- **T2**：零缺失；~5 个重复 ID（答案完全相同，清洗时删重）；3 个 ID 错误无法匹配（标记并排除）
- **T3 领导端**：~3 个非核心变量缺失值；1 个重复 ID；1 个 ID 错误无法匹配
- **T3 下属端**：基于 T1 ∩ T2 名单回访
- **final_merged_analysis_data.xlsx**：T1/T2/T3 三波都成功匹配、注意力检查通过、且每个 leader 至少 3 名 follower

## 注意力检查项位置（已嵌入并标 `*_AttCheck`）

| 文件 | 列名 | 说明 |
|---|---|---|
| T1_cleaned.xlsx | `EMP9_AttCheck` | empowering leadership 第 9 题 |
| T2_cleaned.xlsx | `MAL6_AttCheck` | malicious envy 第 6 题 |
| T3_follower_cleaned.xlsx | `OCBS7_AttCheck` | OCBS 第 7 题 |
| T3_leader_cleaned.xlsx | `CWBS6_AttCheck` | 对第一个下属评价中 CWBS 第 6 题 |

注意力检查题不进入任何复合分数 / 题包 / CFA / MCFA。

## 题包定义（Empowering & Thriving）

按理论维度组合（不随机分 parcel）：

```
EMPP1 = mean(EMP1, EMP2, EMP3)              参与决策
EMPP2 = mean(EMP4, EMP5, EMP6)              表达信心
EMPP3 = mean(EMP7, EMP8, EMP9)              工作意义
EMPP4 = mean(EMP10, EMP11, EMP12)           自主性

THRP1 = mean(THR1, THR3, R_THR5)            学习 (前 3，含反向)
THRP2 = mean(THR2, THR4)                    学习 (后 2)
THRP3 = mean(THR6, THR8, R_THR10)           活力 (前 3，含反向)
THRP4 = mean(THR7, THR9)                    活力 (后 2)
```

`R_THR5` / `R_THR10` 已经先反向再放进 parcel。

## 中心化规则（grand-mean centering，`_C` 后缀）

**做中心化**（用于所有 multilevel hypothesis-testing models）：
`Autocratic`, `Empowering`, `Narcissism`, `PowerDistance`, `FollowerAge`,
`TenureWithLeader`, `InteractionFreq`, `T1_Thriving`（仅 T3 thriving 模型），
`WorkingYears`（仅 Model 3）。

**不做中心化**：所有 dummy variables；CFA / MCFA / reliability / ICC / rwg /
descriptives / correlations 全部用未中心化变量。

## 模型说明

- **主模型 (Model 1)**：multilevel path，level-1 outcomes 直接用下属层面分数，不再聚合。Controls：follower age、gender(dummy)、tenure with leader、interaction frequency；T3 thriving 额外控制 T1 thriving。
- **Model 2**：与 Model 1 同结构但完全去除 controls。
- **Model 3**：把 leader-rated OCBS/CWBS 替换为 follower-rated；其余 controls 与 Model 1 一致，并加入 follower working years。

`Narcissism` 是 mediator，**不作为调节变量**。Power Distance 在 Model 1 / Model 3 中作为调节变量进入 leadership × moderator 交互项。

## 测量验证（measurement appendix.xlsx）

- `MCFA Comparison` sheet：5-factor (hypothesised) vs 4 / 3 / 2-factor 替代模型。`TYPE = TWOLEVEL; ESTIMATOR = MLR; CLUSTER IS CLID`，详见 `code/mcfa_mplus_syntax.inp`。
- `Single-Construct CFA` sheet：单量表普通 CFA，**已做 cluster adjustment**（`TYPE = COMPLEX; CLUSTER IS CLID`）。

## CLID 说明

`CLID` 是为 Mplus 准备的数值型 cluster ID，与 `LeaderID` 一对一，范围 1–79。`study3_mcfa.dat` 第 1 列即 CLID。

## Indirect / conditional indirect effects

按 `analysis_code.R` 中的设定，使用 **Monte Carlo simulation, 20 000 replications** 生成 95% CI，不只依赖 normal-theory tests。
