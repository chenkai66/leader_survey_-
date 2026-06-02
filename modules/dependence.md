# dependence.md — 依赖结构（相关 / 协方差 / copula）

让多列按指定相关结构联动。**最重要的判断**：保边缘 vs 改边缘？

| 你的诉求 | 用 |
|---|---|
| 各列**已有**想要的分布、只调它们之间的相关 | **Iman-Conover**（§3，分布无关、保边缘） |
| **指定**边缘 + **指定**相关一起造 | **Gaussian / t / Clayton copula**（§4-5） |
| 多元正态（边缘正态 + Pearson 相关） | β=R⁻¹r `build_latents`（§2）|
| 多元**非正态** + 目标 Pearson | **Vale-Maurelli** `nonnormal_data`（§6）|
| 连续 + 二分 + 定序混合 + 目标相关 | latent Gaussian copula `mixed_copula`（§7）|

---

## 1. 选方法的关键考虑

- **β=R⁻¹r 假设近正态**。边缘偏态时 Pearson 会被边缘形状扭曲 → 用 Iman-Conover 或 copula。
- **Iman-Conover** 控制**秩相关**（Spearman），Pearson 因边缘非正态会偏离（这是正确行为，不是 bug）。
- **Gaussian copula** 的"相关"是**正态分上的相关**；与最终 Pearson 略有差异——若要精确 Pearson 命中，外层用 `tune_scalar` 微调中间相关。
- 整张相关阵必须**正定**——`nearest_pd(R)` 截断负特征值。

---

## 2. β=R⁻¹r 条件高斯（`build_latents`）—— 多目标精确

```python
build_latents(givens_z, targets, pair_corr=None, rng=None)
# givens_z:(n,k) 标准化；targets: list of k-vec；pair_corr:(m,m)。
# 返回 (n,m) 标准化潜变量，对 givens 的样本内 corr = targets 精确，
# 新变量间 corr = pair_corr 精确。需 r'Rg^-1 r < 1。
```

详见 `engine.md` §2。

---

## 3. Iman-Conover（分布无关、保边缘）—— 最 robust

```python
iman_conover(X, target_corr, rng=None)
# X:(n,k) 已有各自分布；只重排每列内部值，
# 边缘完全不变，诱导出目标 Spearman 相关。
```
机制：(1) 用 cholesky 因子生成正态分目标矩阵 T；(2) 按 T 的秩重排 X 每列。**保边缘的代价**：Pearson 与边缘形状有关，秩相关精确。

用途：保真实数据各列分布只调它们之间的相关；脱敏。

---

## 4. Gaussian copula / NORTA（指定边缘 + 指定相关）

```python
gaussian_copula(n, corr, ppfs, rng=None)
# Z~MVN(0, corr); U=Φ(Z); X_j = ppfs[j](U_j)。
# ppfs 是每列的逆 CDF（lambda q: ...）。
```
要精确 Pearson 命中：用 `tune_scalar` 调中间相关。秩相关解析可换算。

---

## 5. t-copula（重尾联合极端）

```python
t_copula(n, corr, df, ppfs, rng=None)
# 多元 t → empirical CDF → 边缘 ppf。
# df 小 (3-5) = 重尾依赖，联合极端值同时出现的概率高于 Gaussian。
```
金融压力测试、风险模型常用。

---

## 6. Vale-Maurelli（多元非正态 + 目标 Pearson）—— SEM 仿真标准法

每列 Fleishman（控偏度峰度）+ 调整中间正态相关（解三次式）使 transformed Pearson 命中目标：

```python
nonnormal_data(n, corr, skews, kurts, means=None, sds=None)
```
方法学/SEM 仿真造非正态数据的金标准。

---

## 7. Clayton copula（下尾依赖）—— Archimedean

```python
clayton_copula(n, theta, ppfs, rng=None)
# Marshall-Olkin 算法，theta>0；下尾依赖（联合小值同时出现）。
# theta→0 = 独立；theta→∞ = 完全共单调。
```
风险评估（联合极端低）、共发疾病分析。

---

## 8. 混合类型联合（`mixed_copula`）

连续 + 二分 + 定序 联合相关（latent Gaussian copula）：

```python
mixed_copula(n, columns, target_corr, rng=None)
# columns 每项 = {name, type:'continuous|binary|ordinal', ppf|p|cuts}
```
**注意**：离散化后秩相关会**衰减**（二分尤其）；目标设大一点，或用 `tune_scalar` 找补。

---

## 9. 整张协方差阵（正态数据）

```python
X = Z @ chol(Σ).T          # Z 标准正态
# Σ 非正定先 nearest_pd
```

块状/层次：`correlation_matrix_block([3,3,4], within_corr=0.6, between_corr=0.1)`。

---

## 10. 偏相关 + 共线性诊断

```python
partial_corr(df, x, y, controls)   # x 和 y 在控制 controls 后的相关
vif(df, cols)                       # 每列 VIF = 1/(1-R²_j)；>5 = 问题
```

---

## 11. 函数清单

`build_latents` / `iman_conover` / `gaussian_copula` / `t_copula` / `clayton_copula` / `nonnormal_data` / `mixed_copula` / `correlation_matrix_block` / `partial_corr` / `vif` / `nearest_pd` / `zscale` / `resid_against`。
