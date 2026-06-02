# multilevel.md — 多层 / 心理测量

ICC 多层数据、Likert 题项 + 信度、因子模型、IRT、多评分者、混合效应面板。

---

## 1. Likert 题项 + 信度 α（`likertize`）

composite = mean(题项)；`item_sigma` 控题项间相关 = α 来源。

```python
likertize(Lstd, mean, sd, k_items, item_sigma, lo=1, hi=7,
          extra=None, reverse_idx=())
# Lstd: 标准化潜变量
# extra: 额外加项（如交互注入）
# reverse_idx: 1-based 反向题索引；存储 raw 反向、composite 用对齐值
```

**经验表**（hit α≈0.80 的 item_sigma）：

| 题项数 k | item_sigma |
|---|---|
| 5 | 0.85–0.95 |  6 | 0.90–1.05 |  10(parcel) | 0.30–0.55 |  12 | ~1.05 |

**取整衰减相关** → 用 `rebuild_block` 外层校正（详见 `engine.md` §3）。

---

## 2. 多 composite 外层校正（`rebuild_block`）

```python
rebuild_block(df, given_cols, specs, pair_corr=None, item_sigma=0.66,
              outer=9, lr=0.85, lo=1, hi=7)
# specs 每项 = dict(items, comp, mean, sd, tgt, optional extra, reverse_idx)
# 外层循环修正 Likert 取整对相关的衰减
```
交互/干扰项**必须循环内**注入（事后加再 Likert 会稀释主相关）。

---

## 3. 多层 ICC（`icc_rebuild`）—— 组内 vs 组间

`ICC = τ00 / (τ00 + σ²)`。方差拆 `VB = icc·SD²`, `VW = (1-icc)·SD²`。

```python
icc_rebuild(df, group_col, given_cols, item_cols, comp_col, mean, total_sd,
            icc, r_tgt, sign=1, shared=None, halo_scale=1.0,
            rho_l=0.655, rho_d=0.384, item_sigma=0.75, n_iter=14, outer=6)
```

关键点：
- **取整对组间方差是非线性压缩** + 组大小不等 → 实测方差分量后**内层迭代 rescale**，不能信解析公式一次到位。
- **组内 SD=0** 是最明显的造假信号（leader-rated outcome 如果一个组一个常数 → ICC≈0.96，露馅）。
- `shared` + `halo_scale`：构造两个结果列的 cross-corr（如 OCBS↔CWBS = -0.36）——同一个共享因子用相反 sign 给两次调用。

---

## 4. 因子模型 / CFA 结构（`factor_model_sample`）

`X = F·Λ' + E`，F~N(0, factor_corr)，E~N(0, diag(uniqueness))。

```python
factor_model_sample(n, loadings, factor_corr=None, uniqueness=None)
# loadings: (n_items, n_factors) 矩阵 Λ
# uniqueness 默认 1 - Σλ²（题项方差≈1）
# 返回 (n, n_items) 数据；组合信度 ≈ (Σλ)²/(Σλ)²+Σu)
```
比手搓 signal 更干净；载荷直接对应可发表测量模型。SEM 路径模型则用 `Σ = ΛΦΛ' + Θ` + `chol(Σ)`。

---

## 5. IRT 2PL（`irt_2pl_data`）—— 二分项

```python
irt_2pl_data(n_persons, item_difficulty, item_discrimination, theta_sd=1.0)
# P(correct | θ) = sigmoid(a·(θ − b))
# 返回 (X: 0/1 矩阵, θ 向量)
```

---

## 6. IRT GRM（`irt_grm_data`）—— 序类项

```python
irt_grm_data(n_persons, item_discrimination, item_thresholds, theta_sd=1.0)
# item_thresholds[i]: K-1 个递增阈值。每项可有不同 K。
# 返回 (items 矩阵, θ 向量)
```

---

## 7. 多评分者（`multi_rater`）—— self / manager / peer

```python
multi_rater(n, rater_corr, rater_means=None, rater_sds=None)
# 同一目标被 k 个来源打分。inter-rater corr 精确命中 rater_corr。
```
共享 latent + 评分者特异噪声驱动 inter-rater correlation。

---

## 8. 混合效应面板（`mixed_effects_dataset`）

```python
mixed_effects_dataset(n_units, n_periods, fixed_effects=[β...],
                      intercept=0, random_intercept_sd=0.5,
                      random_slope_sd=0.0, slope_var=0, noise_sd=1.0)
# y_{it} = intercept + α_i + (β + s_i)·X_{it} + ε
# random_slope_sd > 0 → 给第 slope_var 个 X 加随机斜率
```

---

## 9. 简单面板（`panel_data`）

```python
panel_data(n_units, n_periods, icc=0.3, ar1=0.5, noise_sd=1.0, time_trend=0.0)
# 长格式：unit/time/y，含单元固定效应 + AR(1) + 时间趋势。
# ICC 控组间方差占比。
```

---

## 10. 中介 / 交互（详细见 engine.md §5 + causal.md）

- 中介：full-mediation 设计避免抑制翻号
- 交互：`rebuild_block(extra=coef * zscale(z_x*z_w))` 循环内注入

---

## 11. 函数清单

`likertize` / `rebuild_block` / `icc_rebuild` / `factor_model_sample` / `irt_2pl_data` / `irt_grm_data` / `multi_rater` / `mixed_effects_dataset` / `panel_data` / `correlation_matrix_block` / `cronbach_alpha`（诊断，详见 `diagnostics-privacy.md`）。
