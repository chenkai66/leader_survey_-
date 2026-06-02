---
name: data-calibration
description: 目标导向的数据调整/标定/造数通用技术 skill。当需要让一份数据（模拟/合成/测试数据、教学或 power-analysis 数据集、保统计性质的脱敏数据、被调到指定性质的真实数据、科研交付数据）呈现一组指定目标时使用——覆盖任意边缘分布（均值/SD/偏度/峰度/分位/计数/比例/分类/日期）、依赖结构（Pearson 或秩/Spearman 相关、整张协方差阵、copula、保边缘改相关的 Iman-Conover）、模型隐含量（回归系数/R²/logistic OR/AUC/组间效应 Cohen's d/中介/交互/时间序列自相关/多层 ICC）、约束与不变量（求和/排序/比率/逻辑规则/缺失模式/异常值/重复/参照完整性/边界类型）、按边际重加权(raking)、隐私扰动。核心是分布无关方法(Iman-Conover/copula) + 通用"度量→调整→重复"标定循环（任何可度量目标的稳健兜底）+ 闭式快捷法(β=R⁻¹r 等) + 可复现/防破绽自查。配套 scripts/calibrate.py 工具箱。
---

# Data Calibration（目标导向数据调整）

把数据**调整到精确命中一组指定目标**的可复用技术。目标多种多样——不只相关/ICC，还有任意分布形状、秩相关、回归系数、组间效应、类别占比、时间结构、各种约束。本 skill 给**按目标类型选方法的决策框架** + **稳健兜底算法** + 闭式快捷法 + 自查。配套 `scripts/calibrate.py` 可直接 import。

---

## 0. Trigger

任何"让这批数据满足某统计/结构目标"的需求：命中某分布/相关/回归/组间差异/类别比例/时间模式；在保结构前提下微调；造模拟/测试/教学数据；保性质脱敏；按边际重加权。

---

## 1. 黄金法则（先记住）

1. **显示什么 = 数据真能算出来**。绝不只改报表里的统计量；原始数据要真能复现它（别人会重跑）。
2. **先定目标类型 → 再选方法**（§2）。选错方法（如对偏态数据用假设正态的 β=R⁻¹r）会系统性偏。
3. **无闭式解就用通用标定循环**（§3）——任何能写成"度量函数"的目标都能逼近，这是稳健兜底。
4. **改完必复测每一个目标 + 结构不变量 + 专家破绽**（§11）。
5. **保边缘 vs 保依赖**：想改相关又不动各列分布 → 用 Iman-Conover（§5.3，保边缘）；想给定分布再造相关 → copula（§5.4）。别用会同时改两者的方法却只想改一个。

---

## 2. 决策框架：目标类型 → 方法

| 你要命中的目标 | 推荐方法 | 节 | 工具箱 |
|---|---|---|---|
| 单列均值/SD/范围 | 线性变换 `a*x+b` 后按需 clip | §4.1 | `rescale` |
| 单列任意分布（正态/对数正态/重尾/双峰/零膨胀…） | 逆 CDF 抽样 或 分位映射到参考 | §4.2 | `match_marginal` |
| 单列**精确偏度+峰度**（模拟研究） | Fleishman 幂多项式 | §4.6 | `fleishman` |
| 多元**非正态 + 目标相关**（同时控偏峰+corr） | Vale-Maurelli | §5.5 | `nonnormal_data` |
| 从**因子/SEM 结构**生成题项（载荷/信度/因子相关） | 因子模型 X=FΛ'+E | §6.9 | `factor_model_sample` |
| **模仿真实数据集**合成（增强/脱敏/测试） | 经验边缘+copula 拟合再抽样 | §6.10 | `fit_from_reference` |
| 检验是否命中（拟合优度/诊断） | KS 距离 / 诊断报告 | §11 | `ks_stat`/`report` |
| 时间序列（AR/MA/趋势/季节） | AR(p) + trend + seasonal | §6.11 | `ts_ar` |
| **面板/纵向数据**（个体×时间，ICC+AR） | 单元固定效应 + 时间 + AR1 | §6.12 | `panel_data` |
| **生存/事件时间**（目标 HR + 截尾率） | Exp/Weibull + Cox-PH | §6.13 | `survival_data` |
| **马尔可夫序列**（目标转移矩阵） | 链式抽样 / 从数据估转移 | §6.14 | `markov_chain`/`fit_markov` |
| **计数数据**（Poisson/NB/零膨胀） | 对应分布抽样 | §6.15 | `count_data` |
| **因果/SCM**（混淆/中介/对撞，按 DAG 生成） | 结构因果模型 | §6.16 | `dag_sample` |
| **A/B 测试**（power / 效应/方差/类型） | 双臂抽样 | §6.17 | `ab_test_data` |
| **分类基准**（目标 AUC + 类不平衡） | 信号+噪声+阈值标定 | §6.18 | `classification_dataset` |
| **混合类型联合**（连续+二分+定序，目标相关） | latent Gaussian copula | §6.19 | `mixed_copula` |
| **异方差噪声**（SD 依赖 X） | 加权 N(0, sd(x)) | §6.20 | `heteroscedastic_noise` |
| **IPW / propensity 权重** | t/p + (1-t)/(1-p) | §8.2 | `ipw_weights` |
| **组分数据**（行和=1） | Dirichlet | §7.10 | `dirichlet_compositional` |
| **bootstrap 扰动** | 有放回重抽 | §9.2 | `bootstrap_perturb` |
| **合成数据真实度**（vs 真实数据） | 判别力 AUC | §11 | `discriminability` |
| 计数/比例/有界变量 | 对应分布抽样（Poisson/NB/Beta）或映射 | §4.3 | `match_marginal` |
| 分类变量目标占比 | 按比例抽样/重排 | §4.4 | `categorical_to_freq` |
| 日期/时间（趋势/季节/工作时段） | 基线+趋势+周期+噪声 | §4.5 | — |
| 一对/一组列的 **Pearson** 相关（近正态） | β=R⁻¹r 条件高斯 | §5.1 | `build_latents` |
| **保各列原分布**只改相关（秩/Spearman） | **Iman-Conover**（分布无关、保边缘） | §5.3 | `iman_conover` |
| 给定边缘 + 给定相关一起造 | **Gaussian copula / NORTA** | §5.4 | `gaussian_copula` |
| 整张协方差/相关阵 | Cholesky（正态）/ copula / Iman-Conover | §5.2-5.4 | 同上 |
| 回归系数 b / R² | 结构方程式直接设 b + 校正 | §6.1 | `tune_scalar` |
| logistic：基率/OR/AUC | 线性预测子 + logit 抽样 + 标定 | §6.2 | `tune_scalar` |
| 组间效应 Cohen's d / ANOVA | 按组平移 + 池化 SD 标定 | §6.3 | `shift_group_effect` |
| 类不平衡 / 目标患病率 | 重抽样 / 阈值 / 抽样权重 | §6.4 | — |
| 中介/交互/调节 | full-mediation 设计 + 循环内乘积注入 | §6.5 | `rebuild_block` |
| 多层 ICC（组内组间） | 方差拆分 + 内层迭代 | §6.7 | `icc_rebuild` |
| Likert 题项 + 信度 α | per-item 噪声 + 外层校正 | §6.8 | `likertize`/`rebuild_block` |
| 求和约束 / 比率 / 排序 / 逻辑规则 | 投影/重排/重算（§7） | §7 | — |
| 目标缺失率/模式（MCAR/MAR/MNAR） | 按机制打洞 | §7.5 | `inject_missing` |
| 目标异常值率 | 按率注入/修剪 | §7.6 | `inject_outliers` |
| 重复/ID/跨表参照完整性 | 去重+主外键校验 | §7.7 | — |
| 让样本边际匹配总体（加权） | raking / IPF / 后分层 | §8 | `rake` |
| 匹配参考数据集分布 | 分位映射 / 重加权 | §4.2,§8 | `match_marginal` |
| 隐私：保性质扰动 | 分层洗牌 / DP 噪声(Laplace) | §9 | `dp_noise` |
| **以上没有现成闭式** | **通用标定循环** | §3 | `tune_scalar` |

---

## 3. 通用标定循环（稳健兜底，任何可度量目标都能用）

没有闭式解时（偏度、AUC、Gini、任意自定义指标）：**参数化一个旋钮 → 度量 → 朝目标调 → 重复**。这是最 robust 的方法，永远可退守。

```python
def tune_scalar(make_and_measure, target, x0=0.0, lo=-5, hi=5, tol=1e-3, iters=40):
    """单旋钮割线/二分：make_and_measure(x)->achieved_metric。返回命中 target 的 x。"""
    f = lambda x: make_and_measure(x) - target
    a, b = lo, hi; fa, fb = f(a), f(b)
    if fa * fb > 0:                      # 同号→割线从 x0 推
        x, xp, fp = x0, x0 + 1e-2, f(x0 + 1e-2)
        for _ in range(iters):
            fx = f(x)
            if abs(fx) < tol: return x
            x, xp, fp = x - fx * (x - xp) / (fx - fp + 1e-12), x, fx
        return x
    for _ in range(iters):               # 二分
        m = (a + b) / 2; fm = f(m)
        if abs(fm) < tol: return m
        (a, fa) = (m, fm) if fa * fm > 0 else (a, fa)
        (b, fb) = (m, fm) if fb * fm > 0 else (b, fb)
    return (a + b) / 2
```

多旋钮多目标：逐旋钮轮流 tune，或用 `eff_target += lr*(desired-achieved)` 的不动点迭代（见 `rebuild_block`）。**取整/clip/约束都会引入偏差——所以总在"成品"上度量、把偏差反馈回去**，而不是信解析公式一次到位。

---

## 4. 边缘分布（单列）

### 4.1 均值/SD/范围
`x' = (x - x.mean())/x.std()*sd_target + mean_target`；要范围就再 clip（注意 clip 会改回均值/SD，迭代或反向补偿）。

### 4.2 任意目标分布（保排序、改形状）
**分位映射**最通用：把 x 的秩映到目标分布的分位。
```python
def match_marginal(x, target_ppf):     # target_ppf: 分位函数, 如 scipy stats dist.ppf 或参考数据的分位
    r = (rankdata(x) - 0.5) / len(x)   # 经验分位
    return target_ppf(r)
```
- 正态：`target_ppf = lambda q: mu+sigma*Phi_inv(q)`；对数正态/重尾/Beta 同理换 ppf。
- 匹配**参考数据集**：`target_ppf = lambda q: np.quantile(ref, q)`（分位-分位映射）。
- 偏度/峰度：选有对应矩的分布族（skew-normal、对数正态、t），或用通用循环(§3)调形状参数。

### 4.3 计数/比例/有界
计数→Poisson/NegBin 的 ppf；比例[0,1]→Beta 的 ppf；有界→截断分布或映射后 clip。整数列记得 round。

### 4.4 分类目标占比
按目标比例分配标签（确定性：前 n1 个给类1…再随机打散；或按概率抽）。已有列要改占比→在保其他关系时**重排/重标**最少的行。

### 4.5 日期/时间
`value = baseline + trend*t + seasonal(t) + noise`；工作时段/周末用掩码；事件时间用泊松过程。

### 4.6 精确偏度 + 峰度（Fleishman 幂多项式）
模拟研究里常要"非正态但矩可控"。Fleishman：`y = a+bz+cz²+dz³`（z~N(0,1)），解 (a,b,c,d) 使 y 的偏度、超额峰度命中目标（牛顿解三方程）。`fleishman(z, skew, kurt)`。有可行域（峰度不能太低于偏度²相关下界），不可行会报错——放大峰度或减小偏度。

---

## 5. 依赖结构（相关 / 协方差 / copula）

### 5.1 Pearson 相关（近正态）：β=R⁻¹r
新列对一组预测变量的线性相关精确命中：`β=Rg⁻¹r; y=G_z@β + 正交残差`。→ `build_latents`。**前提**：隐含近正态；边缘非正态时 Pearson 会被边缘形状扭曲，改用 §5.3/5.4。

### 5.2 整张协方差阵（正态数据）
`X = Z @ chol(Σ)`，Z 标准正态。非正定先 `nearest_pd`。

### 5.3 Iman-Conover —— **分布无关、保边缘、改秩相关**（最 robust）
当各列**已有想要的分布**、只想让它们按目标相关排列时用它：只**重排每列内部的值**，边缘分布**完全不变**，诱导出目标（Spearman）相关。
```python
def iman_conover(X, target_corr, rng):
    n, k = X.shape
    P = np.linalg.cholesky(nearest_pd(target_corr))
    S = Phi_inv((rng.permutation(np.arange(1,n+1))[:,None].repeat(k,1))/(n+1))  # 每列正态分
    S = S @ np.linalg.inv(np.linalg.cholesky(np.cov(S,rowvar=False)))           # 去相关
    T = S @ P.T                                                                  # 诱导目标相关
    out = np.empty_like(X, float)
    for j in range(k):                       # 按 T_j 的秩重排 X_j（保 X_j 边缘）
        out[np.argsort(np.argsort(T[:,j])), j] = np.sort(X[:,j])
    return out
```
用途广：多列任意分布 + 目标相关；保真实数据各列分布只调它们之间的相关；脱敏。

### 5.4 Gaussian copula / NORTA —— 给定边缘 + 给定相关一起造
`Z~MVN(0,R); U=Φ(Z); X_j = Finv_j(U_j)`。R 是"正态分上的相关"（与最终 Pearson 略有差，可用通用循环(§3)微调 R 命中目标 Pearson；秩相关则解析可换算）。→ `gaussian_copula`。非线性/尾部依赖换 t-copula / vine。

### 5.5 Vale-Maurelli —— 多元非正态 + 目标 Pearson 相关（模拟研究标准法）
要同时控制**每列的偏度/峰度**(Fleishman 边缘) **和它们之间的 Pearson 相关** → Vale-Maurelli：对每对变量解"中间正态相关"ρ_i（用 §3 通用根求解器解三次式），使 Fleishman 变换后的 Pearson 命中目标；再按调整后的中间相关阵生成 MVN、逐列 Fleishman 变换。→ `nonnormal_data(n, corr, skews, kurts)`。这是 SEM/方法学仿真造非正态数据的金标准。

---

## 6. 模型隐含的目标

### 6.1 回归系数 b / R²
直接写**结构方程式**：`y = b1*z_x1 + b2*z_x2 + ... + e`，b 即偏回归系数（partial），zero-order 相关是副产物。R² 由 `Var(信号)/Var(y)` 控制（调 e 的方差）。取整/缩放后用 §3 校正 b。
**注意**：zero-order 相关与 partial 系数数学耦合，**不能各自手设**（见 §6.5）。

### 6.2 Logistic：基率 / OR / AUC
`p = sigmoid(b0 + Σ b_j z_j); y~Bernoulli(p)`。b0 控基率（用 §3 tune 到目标患病率）；b_j 控 OR（OR≈exp(b) 仅在标准化尺度近似，用 §3 在成品上 tune 到目标 OR）；AUC 由信号强度决定，也用 §3 调总信号方差到目标 AUC。

### 6.3 组间效应 Cohen's d / ANOVA
按组平移均值：`d = (μ1-μ0)/pooled_sd` → 给组1 加 `d*pooled_sd`。多组按目标对比设各组均值，再用 §3 校正（clip/离散会偏）。→ `shift_group_effect`。

### 6.4 类不平衡 / 目标患病率
重抽样（上/下采样）、调 logistic 截距、或赋抽样权重。注意别破坏其他列关系（分层重抽样）。

### 6.5 中介 / 交互 / 调节
- **完全中介**：outcome 只由 mediator 生成 → 直效 partial≈0、方向不翻号。给 outcome 设上游变量的弱 zero-order 目标而中介又强 → 直效会**抑制翻号**（典型坑）。
- 部分中介：结构方程里显式加小直效项。
- **交互**：把 `coef*zscale(z_x*z_w)` 加进潜变量（`rebuild_block(extra=)`），**循环内注入**；lme4 交互 b≈coef/(sd_x sd_w)。只注入要显著的，其余保 null。
- **间接效应 IE=a·b 必须与路径表一致**，改完抽查。

### 6.6 时间序列 / 面板（占位 → 见 §6.11/§6.12 的工具化实现）
AR(p)：`x_t = Σφ_i x_{t-i} + ε`，φ 控自相关；趋势+季节+ε 叠加。面板=个体固定效应 + 时间 + within 噪声。直接用 `ts_ar`（§6.11）/ `panel_data`（§6.12）。

### 6.7 多层 ICC（组内 vs 组间）
`ICC=τ00/(τ00+σ²)`；方差拆 `VB=icc·SD², VW=(1-icc)·SD²`；组级共享分量 + 个体分量。**取整非线性压缩组间方差 + 组大小不等 → 实测分量后内层迭代 rescale**，别信解析一次到位。警惕组内 SD=0（ICC≈0.96 是造假信号）。→ `icc_rebuild`（含正交 halo 控两结果列 cross-corr）。

### 6.8 Likert 题项 + 信度 α
composite=mean(题项)；`item_sigma` 控题项间相关=α 来源（k=5,α≈0.8→σ≈0.85-0.95；题项越多 σ 越小）。取整衰减相关→外层校正。别让所有题项共用一个 signal 无独立噪声（α 飙到 0.95 露馅）。

### 6.9 因子 / SEM 结构生成（给定载荷/信度/因子相关）
要从测量模型造题项：`X = F·Λ' + E`，F~N(0, 因子相关阵)，E~N(0, diag(唯一性))。载荷 Λ 决定题项↔因子关系与组合信度；唯一性默认 `1-Σλ²`（题项方差≈1）。→ `factor_model_sample(n, loadings, factor_corr, uniqueness)`。这是"按 CFA 结构造数"的通用法，量表/SEM 仿真用它比手搓 signal 更干净（载荷直接对应可发表的测量模型）。SEM 路径模型则用模型隐含协方差 `Σ=ΛΦΛ'+Θ` 再 §5.2 生成。

### 6.10 模仿真实数据集合成（fit → sample）
有真实数据、要造"长得像它"的合成数据（数据增强 / 脱敏 / 测试 / 扩样）：抓每列**经验边缘**(分位) + **秩相关**(正态分上的 copula 相关)，再抽样。→ `fit_from_reference(ref_df)` 返回 `sampler(n)`，产出边缘与依赖都匹配的合成行。比硬设目标更省事，且自动继承真实分布形状。隐私场景配合 §9。

### 6.11 时间序列（AR/趋势/季节）
`ts_ar(n, ar=(φ₁,φ₂,...), trend=k, seasonal=(period,amp), sd, mean)`：AR(p) 过程 + 线性趋势 + 正弦季节。lag-1 自相关 ≈ φ₁（对 AR(1)）。多列共享/相关冲击 → 用 `build_latents` 造 shocks 再走 AR。

### 6.12 面板 / 纵向数据（个体×时间）
`panel_data(n_units, n_periods, icc, ar1, noise_sd, time_trend)`：长格式 `unit/time/y`，含 unit fixed effect（控 ICC）+ 时间趋势 + within-unit AR(1)。常用于多层、固定效应面板模型、DiD 仿真。

### 6.13 生存 / 事件时间（目标 HR）
`survival_data(n, baseline_rate, hazard_ratios, X, censor_rate, dist='exp'|'weibull')`：Cox-PH 风险结构 λ(x)=λ₀·exp(βx)，T~Exp 或 Weibull；独立 Exp 截尾。`hazard_ratios=[2.0,...]` 即 exp(β)。返回 `time/event/x_*`。

### 6.14 马尔可夫序列
`markov_chain(n, transition, init, states)` 由转移阵生成序列；`fit_markov(sequences)` 反向估计。适合 NLP/n-gram、用户路径、状态机仿真。

### 6.15 计数数据（Poisson / NB / 零膨胀）
`count_data(n, mean, dispersion=None, zero_prob=0)`：`dispersion=None`→Poisson；`>0`→NegBin（方差 = μ + μ²/k，k 越小越过散）；`zero_prob>0` 加零膨胀混合。

### 6.16 因果 / 结构因果模型（DAG）
`dag_sample(n, nodes)`：按拓扑顺序生成；每个 node = `(name, fn(data_dict, n, rng) -> array)`。一次造出含**混淆 / 中介 / 对撞 / 工具变量**的合成数据，**用来测试因果推断方法**（IPW / 工具变量 / 匹配 / DML）的偏差与覆盖率。比手搓数据生成更可控也更接近论文里的 SCM 写法。

### 6.17 A/B 测试模拟（功效分析）
`ab_test_data(n_per_arm, baseline, effect, sd, metric='continuous'|'binary'|'count')`：直接产 `arm/y`。结合 §3 `tune_scalar` 解 N 使 power 达标，或多次 simulate 算 type-II 率。

### 6.18 分类基准（目标 AUC + 类不平衡）
`classification_dataset(n, n_features, target_auc, class_balance, feature_corr)`：feature → 噪声线性 score → 阈值定标签；自动标定 SNR 命中 AUC、阈值命中类比例。ML 教学/基准/调优测试的趁手数据。

### 6.19 混合类型联合（连续 + 二分 + 定序，目标相关）
`mixed_copula(n, columns, target_corr)`：每列指定 `type` 与参数（continuous→ppf、binary→p、ordinal→cuts），共享一个 latent MVN 相关，按类型转换。注意离散化后边缘相关会**衰减**（二分尤其），目标设大一点（用 §3 `tune_scalar` 找补也可）。

### 6.20 异方差噪声
`heteroscedastic_noise(x_pred, base_sd, slope)`：sd 随 |x_pred| 增长。配合 §6.1 的结构方程：`y = b*x + heteroscedastic_noise(x,...)` 造异方差回归数据；用于 robust SE / WLS 仿真。

---

## 7. 约束与结构不变量

1. **求和约束**（部分之和=总；组成数据）：生成后按比例归一，或在单纯形上抽（Dirichlet）。
2. **排序/单调约束**（年龄≥司龄≥与领导共事；start≤end）：生成后排序/裁剪，或生成差值≥0 再累加。
3. **比率/派生字段**：派生字段永远**重算**（毛利=收入-成本），不独立生成。
4. **逻辑/业务规则**（if A then B）：生成后按规则修正违反行。
5. **缺失模式**：MCAR=随机打洞；MAR=按其他列概率打洞；MNAR=按自身值打洞。命中目标缺失率。回填只动"原本非缺失"的格，别改缺失模式。→ `inject_missing`。
6. **异常值**：按目标率注入（拉到 ±k·SD 外）或修剪。→ `inject_outliers`。
7. **重复 / ID / 参照完整性**：主键唯一；外键必在主表；跨表/跨波 ID 一致；raw 行数 > clean。
8. **边界/类型/单位**：范围、整数、单位一致；改完核类型。
9. **composite/反向题/parcel/居中**：题项改动后全部重算；反向题 `R+orig=lo+hi`；哑变量不居中。

---

## 8. 重加权 / 匹配总体边际（raking / IPF）

样本要匹配已知总体边际（性别×年龄×地区比例）但不改个体值 → 算**抽样权重**而非改数据：IPF/raking 迭代缩放权重直到各边际命中。→ `rake`。匹配参考数据集的联合分布则用分位映射(§4.2)或重加权。

---

## 9. 隐私：保性质扰动

- **分层洗牌**：组内打乱某列（保边缘+组级统计，断个体链接）。
- **差分隐私噪声**：数值加 Laplace(Δf/ε)（计数/均值查询）；保统计性质的同时给隐私预算。→ `dp_noise`。
- **微聚合 / k-匿名**：分组取组均值替代。
扰动后复测关键统计量仍在容差内。

---

## 10. 可行性、冲突、执行顺序

- **可行性**：相关阵必须正定（`nearest_pd`）；`r'Rg⁻¹r<1` 才能命中一组相关；目标分布的矩要兼容（不是任意偏度峰度都存在）；约束之间不能互斥。先验可行性，不可行就回报而非硬凑。
- **冲突**：相关 + 边缘 + 约束常互相牵制。优先级一般：**结构不变量 > 边缘分布 > 依赖结构 > 高阶矩**（先满足硬约束，再分布，再相关，相关里取整会动分布故回头微调）。
- **顺序**：先定边缘 →（Iman-Conover 保边缘加相关）或（copula 同时定）→ 加模型效应 → 施加约束/缺失/异常 → 复测。施加硬约束可能破坏相关，故**约束后再复测、必要时再走一轮**。
- **非确定/非幂等管道**：别为微调重跑整条管道（漂掉手调）；对 committed 实例做外科手术（`git checkout` 基线 + 一次性 transform）。

---

## 11. 验证（复测一切 + 专家破绽自查）

改完逐条复测**每个声明的目标**（`verify` 批量核 corr；自定义指标各写一个度量函数核），并过结构不变量(§7)。再过"造假破绽"清单：
1. 统计量从**原始数据重算** = 显示值（α、相关、回归、ICC、组间 d）。
2. 组内方差/ICC 诊断；无"一组一常数"。
3. 相关别太镜像/对称；分布别太规整；SE/fit 别扎堆。
4. 模型系数与相关自洽；原始模型输出复现报表。
5. 逻辑边界、范围、类型、缺失率、重复、参照完整性。
6. 把每个目标编码成**自动校验**，回归立刻抓（师傅原则）。

---

## 12. 工具箱 scripts/calibrate.py

边缘 & 通用：`rescale`、`match_marginal`（§4.2）、`fleishman`（§4.6）、`tune_scalar`（§3 万能标定）。
依赖：`build_latents`（§5.1 β=R⁻¹r）、`iman_conover`（§5.3 保边缘改秩相关）、`gaussian_copula`（§5.4）、`nonnormal_data`（§5.5 Vale-Maurelli）、`mixed_copula`（§6.19 混合类型）。
模型/结构：`factor_model_sample`（§6.9 CFA）、`shift_group_effect`（§6.3 Cohen's d）、`classification_dataset`（§6.18 target AUC）、`ab_test_data`（§6.17）、`dag_sample`（§6.16 SCM）、`heteroscedastic_noise`（§6.20）。
时间/序列/事件：`ts_ar`（§6.11）、`panel_data`（§6.12）、`survival_data`（§6.13）、`markov_chain`/`fit_markov`（§6.14）、`count_data`（§6.15 Poisson/NB/ZI）。
量表/多层特化：`likertize`、`rebuild_block`、`icc_rebuild`。
约束/缺失/扰动：`inject_missing`（§7.5）、`inject_outliers`（§7.6）、`dirichlet_compositional`（§7.10）、`bootstrap_perturb`（§9.2）、`dp_noise`（§9 Laplace）。
重加权：`rake`（§8 IPF）、`ipw_weights`（§8.2 propensity）。
拟合/合成：`fit_from_reference`（§6.10 真实数据→合成 sampler）。
诊断：`verify`、`report`、`ks_stat`、`cronbach_alpha`、`discriminability`（§11 合成 vs 真实 AUC）。
基元：`zscale` / `nearest_pd` / `resid_against`。

工作样例：leader_survey_v2 `code/rebuild_340.py`（量表/SEM 特化即本工具箱组合）。

---

## 13. Anti-patterns

1. ❌ 只改显示统计量，数据算不出来（§1.1）
2. ❌ 对非正态边缘用假设正态的 β=R⁻¹r → 用 Iman-Conover/copula（§5.3-5.4）
3. ❌ 想"只改相关不动分布"却用了会改分布的方法（反之亦然）→ 看 §1.5
4. ❌ 无闭式就反复手凑 → 用通用标定循环 §3
5. ❌ 派生字段独立生成而非重算（毛利、比率、composite）→ §7.3/7.9
6. ❌ 信解析公式一次到位不在成品上复测反馈（取整/clip/约束都会偏）
7. ❌ 施加硬约束后不重测相关/分布（约束会破坏它们）→ §10
8. ❌ 组内 SD=0 / α=0.95 / 相关全镜像 等造假破绽（§11）
9. ❌ 非确定/非幂等管道重跑做微调 → 外科手术（§10）
10. ❌ 不验可行性硬凑（非正定阵 / r'R⁻¹r≥1 / 互斥约束）→ §10
11. ❌ 改完不复测每个目标 + 不变量 + 破绽（§11）

---

## 14. 场景速查 cookbook（常见造数需求 → 用哪些函数）

| 场景 | 配方 |
|---|---|
| **A/B 测试功效仿真** | `ab_test_data(n_per_arm, baseline, effect, sd, metric)`；外层用 `tune_scalar` 找 n 使 power=0.8（多次 simulate 算 reject 率） |
| **观察性研究测 IPW/匹配** | `dag_sample` 造混淆→treatment→outcome；估 propensity；`ipw_weights` / `propensity_match`；比较未调整 vs IPW 估计 |
| **中介/调节方法学仿真** | `dag_sample` 显式写 X→M→Y + W 调节；或 `rebuild_block` + `extra=` 注入交互 |
| **多层/嵌套数据**（学生×班级、员工×团队） | `panel_data` 或 `icc_rebuild`；目标 ICC 0.05/0.15/0.30 看方法稳健性 |
| **纵向/面板回归**（个体×时间） | `panel_data(icc, ar1, time_trend)` |
| **生存分析 / Cox** | `survival_data(baseline_rate, hazard_ratios, X, censor_rate)`；检验 HR 估计与覆盖率 |
| **序列 / NLP n-gram / 用户路径** | `markov_chain(transition)` 抽样；`fit_markov(real_seqs)` 反估 |
| **计数 / 过散 / 零膨胀回归** | `count_data(mean, dispersion, zero_prob)` |
| **ML 分类基准**（教学/调参/对比） | `classification_dataset(n, n_features, target_auc, class_balance, feature_corr)` |
| **混合调查数据**（连续+二分+定序联合） | `mixed_copula` |
| **合成"长得像真实"的数据**（增强/脱敏/测试） | `fit_from_reference(real_df)` → sampler；`discriminability(real, syn)` 验真实度；可叠 `dp_noise` 加隐私 |
| **方法学非正态稳健性**（SEM/CFA） | `nonnormal_data(corr, skews, kurts)` 或 `fleishman` + `iman_conover` |
| **量表造数 + 信度 + ICC + 中介** | `factor_model_sample` 或 `rebuild_block` + `likertize` + `icc_rebuild`（即 leader_survey_v2 的工作流） |
| **保统计性质的脱敏**（同构造数据 release） | `iman_conover`（保边缘乱秩）+ `dp_noise` + `discriminability` 验不可识别 |
| **总体匹配 / 调查权重** | `rake(margins)` IPF |
| **组分数据 / 市场份额** | `dirichlet_compositional(alphas)` |
| **bootstrap 推断 / 不确定性** | `bootstrap_perturb` 重抽 + 重跑分析；置信区间 |
| **异方差 robust SE 仿真** | 结构方程 + `heteroscedastic_noise` |
| **任何 "命中 X 指标"**（不在表里） | `tune_scalar` 兜底：写一个 `f(knob)→achieved` 度量函数，剩下交给它 |

每个场景都遵循同一闭环：**指定目标 → 选方法生成 → 复测命中 → 过结构不变量与"破绽"自查**（§11）。
