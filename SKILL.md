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
| **时间序列 / 序列**：AR / ARMA / GARCH 波动率 / VAR 多元 / Markov / HMM / Hawkes 自激 / **TS 异常注入** / **变点检测** | `modules/timeseries.md` | `ts_ar`, `ts_arma`, `ts_garch`, `ts_var`, `markov_chain`, `fit_markov`, `hmm_data`, `hawkes_process`, `count_data`, `ts_anomaly_inject`, `change_point_series` |
| **因果 / 实验**：DAG/SCM / AB / IPW / propensity / DiD / RDD / IV / cluster RCT / 生存 / 竞争风险 / 复发 / **HTE-CATE** / **合成控制** / **staggered DiD** / **层级 Bayes** | `modules/causal.md` | `dag_sample`, `ab_test_data`, `ipw_weights`, `propensity_match`, `did_data`, `rdd_data`, `iv_data`, `cluster_rct`, `survival_data`, `competing_risks_data`, `recurrent_events_data`, `hte_data`, `synthetic_control_data`, `staggered_did`, `hierarchical_bayes_data` |
| **网络 / 空间**：ER/BA/WS/SBM 图 + 空间点/高斯场/Moran I + **知识图谱三元组** + **时序网络** | `modules/networks-spatial.md` | `graph_er`, `graph_ba`, `graph_ws`, `graph_sbm`, `spatial_points`, `spatial_field`, `morans_i`, `knowledge_graph_triples`, `temporal_network` |
| **ML 基准**：classification target AUC / 回归基准 / 概念漂移 / 异常 / SMOTE / 推荐系统 / 低秩 / 聚类 / 对抗 / 标签噪声 / Bayesian / **cold-start** / **RL 轨迹** / **上下文 bandit** / **conformal** | `modules/ml-benchmarks.md` | `classification_dataset`, `regression_benchmark`, `concept_drift_data`, `anomaly_dataset`, `smote`, `recsys_explicit`, `recsys_implicit`, `low_rank_data`, `cluster_data`, `adversarial_perturb`, `label_noise`, `prior_dataset`, `metropolis_posterior`, `cold_start_recsys`, `rl_trajectories`, `bandit_data`, `conformal_calibration_set` |
| **行业特定**：MMM 营销组合 / 离散选择条件 logit / 遗传 SNP+LD / LDA 主题文档 / 神经元 spike trains | `modules/domain-specific.md` | `marketing_mix_data`, `discrete_choice`, `snp_genotypes`, `lda_documents`, `spike_train` |
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
  domain-specific.md     行业特定：MMM 营销组合 / 离散选择 / 遗传 SNP+LD / LDA / 神经元 spike
scripts/calibrate.py     130+ 函数，仅 numpy + Python stdlib（无 scipy）
tests/test_calibrate.py     monolithic 129+ 断言（向后兼容）
tests/per_module/           按模块拆分的 13 个聚焦测试 + run_all.py（112+ 断言）
examples/                3 个端到端场景脚本（nonnormal / model_targets / scenarios）
```

**阅读策略**：常驻只读本 SKILL.md（路由）；某个模块需要时再 `Read modules/xxx.md`；代码直接 `from calibrate import ...`。

---

## 6. Harness（discoverability + 声明式 + 复测 + CLI + recipes）

不想读模块只想直接用：以下入口让你从命令行或交互式 REPL 即时上手。

```python
import calibrate as C

# A. 函数清单（按类）
C.list_functions()                    # [(category, name, oneliner), ...] 共 133
C.list_functions("regression")        # 仅某类

# B. 内省（签名 + docstring + fuzzy 建议）
C.show_help("fleishman")              # 完整签名 + 文档 + 所属类
C.show_help("rebuild_blocks")         # 拼错 → 'did you mean: ["rebuild_block"]?'

# C. 配方库（15 个常见模式的可执行代码）
C.list_recipes()                      # name + 描述
C.show_recipe("ab_test_power_sim")    # 打印可直接 copy-run 的脚本

# D. 声明式 spec → df（一行式造数）
spec = {"n": 2000,
        "columns": [{"name":"age","dist":"truncnormal","mean":40,"sd":10,"lo":18,"hi":80},
                    {"name":"income","dist":"lognormal","mu":10,"sigma":0.5}],
        "correlations": {("age","income"): 0.4},
        "constraints":  [{"type":"range","col":"age","lo":18,"hi":80}]}
df = C.generate_from_spec(spec)

# E. 先验 spec（生成前 lint，避免无效 spec 浪费时间）
errs = C.validate_spec(spec)         # [] = OK；非空 = 错误清单（含 'did you mean'）
df = C.generate_from_spec(spec)      # 自动调 validate_spec；不合法抛 SpecError

# F. 复测命中（验数据 vs spec）
print(C.validate(df, spec))          # 每条 PASS/FAIL + N/T 摘要

# F. 全局可复现种子
S = C.Seed(42); rng = S.rng()         # 整脚本共用
```

**CLI**（不用写 Python）：
```bash
python -m calibrate help                          # 用法
python -m calibrate list [category]               # 列函数
python -m calibrate help <function>               # 文档
python -m calibrate recipes                       # 配方
python -m calibrate show-recipe <name>            # 打印某配方
python -m calibrate sample <dist> <n> k=v ...     # 快速单列抽样 + 摘要
python -m calibrate generate spec.json out.csv    # 声明式造数 → CSV
python -m calibrate validate data.csv spec.json   # 校验
```

**入门路径**：
1. 跑 `examples/quickstart.py`（5 个最常见模式串起来）
2. 用 `generate_from_spec` 声明式造一份基础数据；`validate` 看命中
3. 复杂场景：按 §2 路由读相应模块；用 `show_help(name)` 查具体函数
4. 没有现成函数：用 `tune_scalar`（万能兜底）或翻 `modules/engine.md`
