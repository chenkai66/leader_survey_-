# regression.md — 回归 / GLM 家族 + ANOVA + 配对 + 列联表

最常见的"我要一份回归数据"等需求 → 一行式 API。

---

## 1. 线性回归（`regression_dataset`）

```python
regression_dataset(n, coefs, intercept=0, noise_sd=None, target_r2=None,
                   X_corr=None, X_means=None, X_sds=None)
# y = intercept + X@coefs + N(0, noise_sd)
# 给 target_r2 自动定 noise_sd 命中 R²
```

---

## 2. Logistic 回归（`logistic_dataset`）

```python
logistic_dataset(n, coefs, intercept=0, X_corr=None)
# y ~ Bernoulli(sigmoid(intercept + X@coefs))
# coefs 直接是 log-OR
```

---

## 3. Poisson 回归（`poisson_regression_dataset`）

```python
poisson_regression_dataset(n, coefs, intercept=0, X_corr=None)
# y_i ~ Poisson(exp(intercept + X_i@coefs))
# coefs = log(rate ratio)
```

过散就用 `count_data(n, mean, dispersion=k)` 自己组装（见 `timeseries.md`）。

---

## 4. Multinomial Logit（`multinomial_logit_dataset`）

```python
multinomial_logit_dataset(n, coefs_per_class, intercepts=None, X_corr=None)
# coefs_per_class: (K-1, p) 矩阵，class 0 = reference。
# y ∈ {0..K-1}。
```

---

## 5. Ordinal Logit / Proportional Odds（`ordinal_logit_dataset`）

```python
ordinal_logit_dataset(n, coefs, thresholds, X_corr=None)
# K-1 个阈值定 K 个序类。
# P(y≤k|x) = sigmoid(threshold_k - x·coefs)
```

---

## 6. Quantile 回归（`quantile_regression_dataset`）

```python
quantile_regression_dataset(n, coefs, intercept=0, scale=1.0,
                            target_quantile=0.5, X_corr=None)
# 不对称 Laplace 噪声使条件 target_quantile-分位 = intercept + X·coefs。
```

---

## 7. ANOVA / Factorial 设计（`anova_design`）

```python
anova_design(n_per_cell, factor_levels={"A":2,"B":2},
             main_effects={"A":[0,1], "B":[0,0.5]},
             interaction_effects={("A","B"): [[0,0],[0,0.7]]},
             sd=1.0, baseline=0.0)
# 平衡 factorial（2×2 / 2×3 / 3×3 …）；返回 df with factor cols + y。
```
交互效应可 callable `lambda i, j: ...` 或 2D 数组。

---

## 8. 配对 / 前后测（`paired_data`）

```python
paired_data(n, baseline_mean=0, change_effect=0.5, within_corr=0.7,
            baseline_sd=1, post_sd=1)
# 双变量 MVN，target pre-post Pearson = within_corr 精确。
# 返回 pre / post / change。
```

---

## 9. 两样本（`two_sample`）

```python
two_sample(n1, n2, mean1, mean2, sd1, sd2)
# 返回 group / y，t-test ready。
```

---

## 10. 列联表 / Chi-square（`contingency_table`）

```python
contingency_table(row_margins, col_margins, odds_ratio=1.0)
# 2×2：解一元方程命中目标 OR。
# RxC：IPF 命中边际（OR=1 忽略）。
```

---

## 11. R² 与 partial / direct effect 设计

- `regression_dataset` 直接控**partial / 回归系数**（结构方程式）；zero-order 相关是副产物。
- 要 zero-order corr 命中 → 用 `build_latents`（`dependence.md`）。
- **二者数学耦合，不能各自手设**——见 `engine.md` §5 full-mediation。

---

## 12. 函数清单

`regression_dataset` / `logistic_dataset` / `poisson_regression_dataset` / `multinomial_logit_dataset` / `ordinal_logit_dataset` / `quantile_regression_dataset` / `anova_design` / `paired_data` / `two_sample` / `contingency_table` / `multinomial_dataset` / `mixed_effects_dataset`（multilevel.md）。
