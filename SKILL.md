---
name: data-calibration
description: 目标导向的数据调整/标定/造数通用技术 skill。当需要让一份数据（模拟/合成/测试/教学/power-analysis/保性质脱敏/科研交付数据）呈现一组指定目标时使用。覆盖：任意边缘分布（含 Fleishman 偏度峰度、混合、截断、零膨胀、10+ 命名分布）、依赖结构（Pearson/秩相关、协方差阵、Gaussian/t/Clayton copula、Iman-Conover 分布无关、Vale-Maurelli 多元非正态）、回归 GLM 家族（线性/logistic/Poisson/multinomial/ordinal/quantile + ANOVA + 配对 + 列联表）、多层与心理测量（多层 ICC + Likert+α + 因子模型 + IRT 2PL/GRM + 多评分者）、时间序列与序列（AR/ARMA/GARCH/VAR + Markov + HMM + Hawkes 自激）、生存（含竞争风险/复发事件）、因果实验（DAG/SCM + AB + IPW + propensity match + DiD + RDD + IV + cluster RCT）、网络与空间（ER/BA/WS/SBM + 空间点/高斯随机场/Moran's I）、ML 基准（target AUC + 回归基准 + 概念漂移 + 异常检测 + SMOTE + 推荐系统 + 低秩 + 聚类 + 对抗扰动 + 标签噪声 + Bayesian 先验/Metropolis 后验）、多表多维一致性（关系表 + SCD type-2 + M:N + 业务规则引擎 + 7 类一致性校验）、约束/缺失/隐私（MCAR/MAR/MNAR + outliers + Dirichlet + DP + rake/IPW）、诊断（KS/PSI/JS/Mahalanobis/Mardia/Anderson-Darling/chi-square GoF/discriminability/report/cronbach）。100+ 函数、108+ 自测全过。**渐进式披露架构**：本文件是轻量路由（按目标定位需读的模块），具体方法在 modules/*.md 按需 Read，代码 scripts/calibrate.py。
---

# Data Calibration（数据标定 / 造数）—— 路由 SKILL.md

把数据**调整到精确命中一组统计/结构目标**的可复用技术。本文件是**路由**，按你的目标指引你读哪个 `modules/*.md`。**避免一次把全部内容塞进上下文**——只读用到的模块。

---

## 0. Trigger

任何"让这批数据满足某统计/结构目标"的需求：命中某分布/相关/回归/组间差异/类别比例/时间模式/网络结构/空间自相关；保结构微调；造模拟/测试/教学/基准数据；保性质脱敏；按边际重加权；多表保持一致。

---

## 1. 黄金法则（5 条，全场景通用）

1. **显示什么 = 数据真能算出来**。绝不只改报表数字；原始数据要能复现（别人会重跑）。
2. **先定目标类型 → 再选方法**（§2 路由）。选错方法会系统性偏（如对偏态数据用假设正态的 β=R⁻¹r）。
3. **无闭式解就用通用标定循环**（`tune_scalar` + 外层校正）。详见 `modules/engine.md`。
4. **改完必复测每个目标 + 结构不变量 + 专家"破绽"清单**。详见 `modules/diagnostics-privacy.md`。
5. **保边缘 vs 保依赖**：想改相关又不动各列分布 → Iman-Conover（保边缘）；想给定分布再造相关 → copula。

---

## 2. 路由：你的目标 → 读哪个模块

| 目标类型 | 读 | 典型函数 |
|---|---|---|
| **核心算法**：通用标定循环 / β=R⁻¹r / 外-内层校正 / full-mediation 设计 | `modules/engine.md` | `tune_scalar`, `build_latents`, `rebuild_block` |
| **边缘分布**：mean/SD/偏度/峰度/10+ 命名分布/混合/截断/零膨胀/分位映射/模仿真实数据 | `modules/distributions.md` | `sample_dist`, `match_marginal`, `fleishman`, `gaussian_mixture`, `truncated_normal`, `zero_inflated_continuous`, `rescale`, `multinomial_dataset`, `dirichlet_compositional`, `fit_from_reference` |
| **依赖结构**：相关 / 协方差 / copula（Gaussian/t/Clayton）/ Iman-Conover / Vale-Maurelli / 混合类型联合 | `modules/dependence.md` | `build_latents`, `iman_conover`, `gaussian_copula`, `t_copula`, `clayton_copula`, `nonnormal_data`, `mixed_copula`, `correlation_matrix_block`, `partial_corr`, `vif` |
| **回归 / GLM**：线性 / logistic / Poisson / multinomial / ordinal / quantile + ANOVA / 配对 / 两样本 / 列联表 | `modules/regression.md` | `regression_dataset`, `logistic_dataset`, `poisson_regression_dataset`, `multinomial_logit_dataset`, `ordinal_logit_dataset`, `quantile_regression_dataset`, `anova_design`, `paired_data`, `two_sample`, `contingency_table` |
| **多层 / 心理测量**：ICC 多层 / Likert+α / 因子模型 / IRT 2PL/GRM / 多评分者 / 中介-调节 | `modules/multilevel.md` | `icc_rebuild`, `likertize`, `rebuild_block`, `factor_model_sample`, `irt_2pl_data`, `irt_grm_data`, `multi_rater`, `mixed_effects_dataset`, `panel_data` |
| **时间序列 / 序列**：AR / ARMA / GARCH 波动率 / VAR 多元 / Markov / HMM / Hawkes 自激点过程 | `modules/timeseries.md` | `ts_ar`, `ts_arma`, `ts_garch`, `ts_var`, `markov_chain`, `fit_markov`, `hmm_data`, `hawkes_process`, `count_data` |
| **因果 / 实验**：DAG/SCM / AB / IPW / propensity / DiD / RDD / IV / cluster RCT / 生存 / 竞争风险 / 复发 | `modules/causal.md` | `dag_sample`, `ab_test_data`, `ipw_weights`, `propensity_match`, `did_data`, `rdd_data`, `iv_data`, `cluster_rct`, `survival_data`, `competing_risks_data`, `recurrent_events_data` |
| **网络 / 空间**：ER / BA / WS / SBM 图 + 空间点模式 / 高斯随机场 / Moran's I | `modules/networks-spatial.md` | `graph_er`, `graph_ba`, `graph_ws`, `graph_sbm`, `spatial_points`, `spatial_field`, `morans_i` |
| **ML 基准**：classification target AUC + 回归基准 + 概念漂移 + 异常 + SMOTE + 推荐系统 + 低秩 + 聚类 + 对抗 + 标签噪声 + Bayesian | `modules/ml-benchmarks.md` | `classification_dataset`, `regression_benchmark`, `concept_drift_data`, `anomaly_dataset`, `smote`, `recsys_explicit`, `recsys_implicit`, `low_rank_data`, `cluster_data`, `adversarial_perturb`, `label_noise`, `prior_dataset`, `metropolis_posterior` |
| **多表 / 多维一致性**：关系表 / SCD / M:N / 父子聚合 / 时序顺序 / 业务规则 / 7 类校验 | `modules/multitable.md` | `relational_children`, `many_to_many`, `scd_type2`, `evolve_panel_state`, `funnel_data`, `enforce_constraints`, `check_referential_integrity`, `check_aggregate`, `check_temporal`, `check_identity`, `check_uniqueness`, `check_no_nulls`, `check_value_set` |
| **诊断 / 隐私 / 重加权 / 缺失/异常**：KS / PSI / JS / Mahalanobis / Mardia / AD / chi-square GoF / discriminability / DP / rake / IPW / 缺失模式注入 / outliers | `modules/diagnostics-privacy.md` | `verify`, `report`, `ks_stat`, `psi`, `js_divergence`, `mahalanobis_outliers`, `mardia_normality`, `anderson_darling_normal`, `chi_square_gof`, `discriminability`, `cronbach_alpha`, `dp_noise`, `rake`, `inject_missing`, `inject_outliers`, `shift_group_effect`, `bootstrap_perturb`, `heteroscedastic_noise` |
| **以上没现成闭式** | `modules/engine.md` §"通用标定循环" | `tune_scalar` 兜底 |

---

## 3. 通用 4 步工作流

```
1. 选目标类型 → 找模块（§2）
2. 调函数生成数据（按模块文档的 API）
3. 复测目标（diagnostics-privacy.md 工具：verify / report / 各类 GoF / discriminability）
4. 不满足 → tune_scalar 兜底（engine.md）或换更合适的方法
```

---

## 4. 总体不变量（造任何数据都要保）

- composite/汇总/派生字段 = 由源**重算**而非独立生成（profit=rev-cost、composite=mean(items)…）
- 反向题 R+orig=lo+hi；parcel=规定项均值；居中 _C = var − mean；哑变量不居中
- 多波/多表同一 ID 的稳定属性（DOB、gender）跨记录不能变
- 求和约束（部分之和=总）、排序约束（age≥tenure）、值域/类型/单位、缺失模式
- 时序顺序（created ≤ updated）、外键引用都解析、父子聚合一致
- N 三处对齐：`len(data) == json/manifest 元数据 == 报表中声明的 N`

详细校验：`modules/multitable.md` §"校验器汇总"。

---

## 5. 仓库结构

```
SKILL.md                  本文件（路由 + 黄金法则 + 工作流 + 不变量）
README.md                 quickstart + 方法索引
modules/                  按目标分类的深度文档（按需 Read，不要全读）
  engine.md              核心标定算法（tune_scalar / β=R⁻¹r / 外-内层校正 / full-mediation）
  distributions.md       边缘分布 / Fleishman / 混合 / 截断 / 零膨胀 / fit-from-reference
  dependence.md          相关 / 协方差 / copula / Iman-Conover / Vale-Maurelli
  regression.md          GLM 家族 + ANOVA + 配对 + 列联表
  multilevel.md          ICC / Likert+α / 因子 / IRT / 多评分者 / 面板
  timeseries.md          AR/ARMA/GARCH/VAR + Markov + HMM + Hawkes
  causal.md              SCM/AB/IPW/PSM/DiD/RDD/IV/cluster RCT + 生存
  networks-spatial.md    图（ER/BA/WS/SBM）+ 空间（点/场/Moran）
  ml-benchmarks.md       classification/regression/drift/anomaly/SMOTE/recsys/低秩/聚类/对抗/标签噪声/Bayesian
  multitable.md          关系表 / SCD / M:N / 时序演化 / 业务规则 / 7 校验器
  diagnostics-privacy.md 诊断 / 隐私 / 重加权 / 缺失/异常注入 / 异方差
scripts/calibrate.py     100+ 函数，仅 numpy + Python stdlib（无 scipy）
tests/test_calibrate.py  108+ 断言（每方法实测达标）
examples/                3 个端到端场景脚本（nonnormal / model_targets / scenarios）
```

**阅读策略**：常驻只读本 SKILL.md（路由）；某个模块需要时再 `Read modules/xxx.md`；代码直接 `from calibrate import ...`。
