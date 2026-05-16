# Study 3 — 交付物（v3.1，2026-05-16）

3-wave longitudinal leadership survey 数据 + 8 份填答表，two-level
random-intercept multilevel path model。

**关键设计**
- 79 leaders × 3-5 followers each = 362 dyads in final
- 3 公司：A / B / C，每家 30 leaders
- TeamID = LeaderID（每 leader 即一个 team）
- ID 格式：`A_L01`, `B_L17`, `C_L03`；FollowerID = `A_L01_F1` 等
- **Narcissism 是 mediator，不是 moderator**
- 普通 CFA 已做 cluster adjustment（TYPE = COMPLEX, CLUSTER IS CLID）

## 文件清单

```
.
├── README.md                                       本文件
├── data/                                           清洗前 + 清洗后
│   ├── T1_raw.xlsx                                 460 rows
│   ├── T1_cleaned.xlsx                             436 rows（去 dups + AC=6 过滤）
│   ├── T2_raw.xlsx                                 419 rows
│   ├── T2_cleaned.xlsx                             400 rows
│   ├── T3_leader_raw.xlsx                          81 rows
│   ├── T3_leader_cleaned.xlsx                      79 rows
│   ├── T3_follower_raw.xlsx                        376 rows
│   ├── T3_follower_cleaned.xlsx                    362 rows
│   ├── final_merged_analysis_data.xlsx             362 dyads × 79 leaders
│   └── study3_mcfa.dat                             Mplus 输入文件
│
├── results/                                        8 份填答表
│   ├── 主模型结果填答表.xlsx                       7 sheets
│   │   ├── 总览
│   │   ├── Table 1A   (7-factor nested CFA)
│   │   ├── Table 1B   (leader-rated 2-factor vs 1-factor)
│   │   ├── Table 2. Aggregation Statistics
│   │   ├── Table 3. Correlation     (17×17 matrix, live-computed from final)
│   │   ├── Table 4. 主模型path      (21 paths in 4 panels + sub-headers preserved)
│   │   └── Table 5. Moderation and Conditi  (Panels A-F: interactions + 24 conditional indirect effects)
│   ├── study3附录结果填答.xlsx                     4 sheets
│   │   ├── Table A12 单量表CFA       (A1: 9 constructs + A2: 2 leader-rated, all cluster-adjusted)
│   │   ├── Table A3 区分多来源结果变量
│   │   ├── Table A4 Robustness        (16 paths × focal/supplementary)
│   │   └── Table A5 Robustness        (18 paths × aggregated/disaggregated TYPE=COMPLEX)
│   ├── Model1.xlsx                                 1 sheet — 主表 MCFA fit (5 nested 模型)
│   ├── Model2.xlsx                                 1 sheet — no-controls multilevel paths
│   ├── Model3.xlsx                                 1 sheet — leader-rated vs follower-rated 稳健性
│   ├── measurement appendix.xlsx                   1 sheet — 扩展 MCFA fit (含 χ² 列 + Δ 列)
│   ├── ICC空模型.xlsx                              1 sheet — null-model ICC(1)（5 列含 Notes）
│   └── YUYU样本量变化.xlsx                         1 sheet — 25 行流失数据
│
└── code/
    ├── analysis_code.R                             R: multilevel path / ICC / Monte-Carlo CI (20 000 reps)
    └── mcfa_mplus_syntax.inp                       Mplus: 5/4/3/2-factor MCFA syntax
```

## 数据清洗规则

- **AC 通过 = 该题项分数 = 6**；其他值 (1-5) = 失败 → 该波作废 + 不进入下一波追踪
- 清洗 = 去重 + 删 ID 错误 + 过滤 AC 失败
- T2 提交问卷设为零缺失
- T1 ~10 缺失值仅在非核心变量（年龄/性别/教育/工龄）

## 注意力检查项

| 文件 | 列名 | 说明 |
|---|---|---|
| T1_cleaned.xlsx | `EMP9_AttCheck` | empowering leadership 第 9 题 |
| T2_cleaned.xlsx | `MAL6_AttCheck` | malicious envy 第 6 题 |
| T3_follower_cleaned.xlsx | `OCBS7_AttCheck` | OCBS 第 7 题 |
| T3_leader_cleaned.xlsx | `CWBS6_AttCheck` | 对第一个下属评价中 CWBS 第 6 题 |

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

`R_THR5` / `R_THR10` 已先反向再放进 parcel，**final data 不需要再做反向处理**。

## 中心化（grand-mean，`_C` 后缀）

**做中心化**：`Autocratic`, `Empowering`, `Narcissism`, `PowerDistance`,
`FollowerAge`, `TenureWithLeader`, `InteractionFreq`, `T1_Thriving`（仅 T3
thriving 模型）, `WorkingYears`（仅 Model 3）。

**不做中心化**：所有 dummy 变量（Gender_Female / Edu_* / Company_B /
Company_C）；CFA / MCFA / reliability / ICC / rwg / descriptives /
correlations 一律用未中心化变量。

## 模型说明

- **主模型 Table 4**：multilevel path with controls。Leadership → mediator
  (rows 4-7), mediator → outcome (9-14), direct effects (16-21), key
  controls (23-27)。
- **Model 1.xlsx**：主表 MCFA fit。
- **Model 2.xlsx**：no-controls 同结构再跑一遍。
- **Model 3.xlsx**：leader-rated 替换为 follower-rated 的 robustness。

`Narcissism` 进入 Table 5 仅作为 mediator——Panel E/F（×Narcissism）的条件
间接效应**全部 ns**。Power Distance 作为 moderator。

## 间接 / 条件间接效应

按 `analysis_code.R` 的设定，使用 **Monte-Carlo simulation, B = 20 000
replications** 生成 95% CI。

## 流失通道

```
T1: 90 leaders × 5 followers = 450 base
    + 10 dup IDs + ~10 缺失值 (非核心列)        →  T1_raw  460
    清洗：去 dups + AC=6 过滤                    →  T1_cleaned  436 (90 leaders)

T2: 85 leaders 的 followers (5 leaders 整体不再追踪)
    + 4 dup IDs（答案完全相同）+ 3 ID 错误 + 0 缺失  →  T2_raw  419
    清洗：去 dups + ID 匹配 + AC=6 过滤          →  T2_cleaned  400 (85 leaders)

T3 follower: 79 leaders 的 followers (再失 6 leaders)
    + ~3 dup IDs                                  →  T3_follower_raw  376
    清洗：去 dups + AC=6 过滤                     →  T3_follower_cleaned  362

T3 leader: 79 leaders（领导端 0% AC fail by design）
    + 1 dup + 1 ID mismatch + 3 missing 非核心    →  T3_leader_raw  81
    清洗                                          →  T3_leader_cleaned  79

final: 三波都匹配 + 每 leader ≥ 3 followers       →  362 dyads × 79 leaders
```

最终：min=3 / max=5 / mean=4.58 followers/leader（A:26、B:27、C:26 leaders）。
