# Study 3 — 交付物（v2，sheet 已对齐原始模板）

3-wave longitudinal leadership survey 数据 + 8 份填答表，two-level
random-intercept multilevel path model。**Narcissism 是 mediator，不是
moderator；measurement appendix / Table A1-A2 的普通 CFA 已做 cluster
adjustment（TYPE = COMPLEX）。**

## 文件结构

```
.
├── data/                                        清洗前 + 清洗后
│   ├── T1_raw.xlsx          T1_cleaned.xlsx
│   ├── T2_raw.xlsx          T2_cleaned.xlsx
│   ├── T3_leader_raw.xlsx   T3_leader_cleaned.xlsx
│   ├── T3_follower_raw.xlsx T3_follower_cleaned.xlsx
│   ├── final_merged_analysis_data.xlsx           T1∩T2∩T3 + ≥3 followers/leader
│   └── study3_mcfa.dat                           Mplus 输入文件（首列 CLID）
│
├── results/                                     8 份填答表
│   ├── 主模型结果填答表.xlsx     7 sheets: 总览 + Tables 1A, 1B, 2, 3, 4, 5
│   ├── study3附录结果填答.xlsx   4 sheets: Tables A1+A2, A3, A4, A5
│   ├── Model1.xlsx               主表-MCFA fit（5 nested 模型）
│   ├── Model2.xlsx               no-controls multilevel paths
│   ├── Model3.xlsx               leader-rated vs follower-rated outcomes 稳健性
│   ├── measurement appendix.xlsx 扩展 MCFA fit（含 Δ 列）
│   ├── ICC空模型.xlsx            null-model ICC(1)
│   └── YUYU样本量变化.xlsx        样本量流失表
│
└── code/
    ├── analysis_code.R                R: multilevel path, ICC, descriptives,
    │                                  Monte-Carlo CI (20 000 reps)
    └── mcfa_mplus_syntax.inp          Mplus: 5/4/3/2-factor MCFA syntax
```

## 8 份填答表怎么读

| 文件 | sheets | 内容 |
|---|---|---|
| **主模型结果填答表.xlsx** | 7 | 客户最初要的核心填答表（Table 1A–5） |
| **study3附录结果填答.xlsx** | 4 | 客户最初要的附录填答表（Table A1–A5） |
| Model1.xlsx | 1 | 主文 MCFA fit (5 nested) |
| Model2.xlsx | 1 | no-controls path 系数 |
| Model3.xlsx | 1 | follower-rated outcome 替代 |
| measurement appendix.xlsx | 1 | 扩展 MCFA fit + Δ 比较 |
| ICC空模型.xlsx | 1 | null-model ICC(1) |
| YUYU样本量变化.xlsx | 1 | 样本量流失表 |

主表 **主模型结果填答表.xlsx** 的 7 个 sheet：
- **总览**：内容概要
- **Table 1A**：7 个 nested CFA 模型的 fit indices
- **Table 1B**：leader-rated OCBS/CWBS 二因子 vs 单因子
- **Table 2. Aggregation Statistics**：ICC(1), ICC(2), rwg(j) — Autocratic / Empowering 聚合统计
- **Table 3. Correlation**：17 个变量的 mean / SD / α + 17×17 相关矩阵
- **Table 4. 主模型path**：21 条路径（leadership→mediator / mediator→outcome / direct / key controls）
- **Table 5. Moderation and Conditi**：6 个 panel — Panel A/B 4×2 交互项；Panel C-F 24 条条件间接效应

附录 **study3附录结果填答.xlsx** 的 4 个 sheet：
- **Table A12 单量表CFA**：A1（focal 9 个量表 + cluster-adjusted CFA）+ A2（leader-rated 2 个）
- **Table A3 区分多来源结果变量**：source-block CFAs（self vs leader-rated, 双因子 vs 单因子）
- **Table A4 Robustness**：focal vs supplementary outcome source 对比（16 paths/interactions）
- **Table A5 Robustness**：aggregated vs disaggregated leadership（TYPE=COMPLEX，16 paths/interactions）

## 数据清洗规则

- **T1**：~10 非核心变量缺失值；~10 重复 ID（清洗时删除）
- **T2**：零缺失；~5 重复 ID（答案完全相同）；3 个 ID 错误无法匹配
- **T3 领导端**：~3 非核心变量缺失值；1 重复 ID；1 ID 错误
- **T3 下属端**：基于 T1∩T2 名单回访
- **final_merged**：T1/T2/T3 三波均成功匹配 + 注意力检查通过 + 每 leader ≥ 3 followers

## 注意力检查项位置

| 文件 | 列名 | 说明 |
|---|---|---|
| T1_cleaned.xlsx | `EMP9_AttCheck` | empowering leadership 第 9 题 |
| T2_cleaned.xlsx | `MAL6_AttCheck` | malicious envy 第 6 题 |
| T3_follower_cleaned.xlsx | `OCBS7_AttCheck` | OCBS 第 7 题 |
| T3_leader_cleaned.xlsx | `CWBS6_AttCheck` | 对第一个下属评价 CWBS 第 6 题 |

注意力检查题不进入任何复合分数 / 题包 / CFA / MCFA。

## 题包定义

```
EMPP1 = mean(EMP1, EMP2, EMP3)              参与决策
EMPP2 = mean(EMP4, EMP5, EMP6)              表达信心
EMPP3 = mean(EMP7, EMP8, EMP9)              工作意义
EMPP4 = mean(EMP10, EMP11, EMP12)           自主性

THRP1 = mean(THR1, THR3, R_THR5)            学习 (前 3 + 反向 5)
THRP2 = mean(THR2, THR4)                    学习 (后 2)
THRP3 = mean(THR6, THR8, R_THR10)           活力 (前 3 + 反向 10)
THRP4 = mean(THR7, THR9)                    活力 (后 2)
```

`R_THR5` / `R_THR10` 已先反向再放进 parcel。

## 中心化规则（grand-mean，`_C` 后缀）

**做中心化**：`Autocratic`, `Empowering`, `Narcissism`, `PowerDistance`,
`FollowerAge`, `TenureWithLeader`, `InteractionFreq`, `T1_Thriving`（仅
T3 thriving 模型）, `WorkingYears`（仅 Model 3）。

**不做中心化**：所有 dummy；CFA / MCFA / reliability / ICC / rwg /
descriptives / correlations 用未中心化变量。

## 模型说明

- **主模型 Table 4**：multilevel path with controls。在 Table 4 里同时有
  leadership→mediator（行 4-7）、mediator→outcome（行 9-14）、direct
  effects（行 16-21）、key controls（行 23-27）。
- **Model 1.xlsx**：主表 MCFA fit；五因子 hypothesised 与 4/3/2/1-factor
  对照。
- **Model 2.xlsx**：no-controls 与 Model 1 同结构再跑一遍。
- **Model 3.xlsx**：leader-rated OCBS/CWBS 替换为 follower-rated 的
  robustness。Controls 与 Model 1 一致 + working years。

`Narcissism` 是 mediator——Table 5 Panel E/F（×Narcissism 交互）的条件
间接效应**全部 ns**，**不作为调节变量**。Power Distance 在主模型作为
moderator 进入 leadership × PD 交互项。

## 测量验证

- **MCFA**（Model 1 / measurement appendix）：5-factor hypothesised vs
  4/3/2/1-factor 替代，TYPE = TWOLEVEL；ESTIMATOR = MLR；CLUSTER IS CLID。
  `code/mcfa_mplus_syntax.inp` 是 Mplus 语法。
- **单量表 CFA**（附录 Table A1/A2）：**已做 cluster adjustment**——TYPE
  = COMPLEX with CLUSTER IS CLID。每行 Notes 列里都注明了。

## CLID

`CLID` 是为 Mplus 准备的数值型 cluster ID，与 `LeaderID` 一对一，范围
1–79。`study3_mcfa.dat` 第 1 列即 CLID。

## 间接 / 条件间接效应

按 `analysis_code.R` 中的设定，indirect 与 conditional indirect 用
**Monte-Carlo simulation, 20 000 replications** 生成 95% CI，不只依赖
normal-theory tests。Table 5 Panel C-F 的 95% BC CI 即为此。
