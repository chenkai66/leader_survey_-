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

## 2b. composite 保留的信度/CFI 标定（`calibrate_item_reliability`）★

**场景**：结构模型（path/相关/ICC/SEM）已标定好，但**显示的 α / 单因子 CFA / MCFA / CMV 跟数据真算的对不上**（典型：题项太"干净"→ 真算 α=0.97、CFA CFI=1.000，太完美像造假）。要把这些 item 级测量指标改成目标值，**又绝不能动结构关系**。

**核心技巧**：item = `固定composite + 零和残差`，再用 `sum_preserving_round` 取整 → **composite 逐行精确不变（drift=0）** → path/相关/ICC/demote 全部 byte-identical，只有 item 级测量模型变。

```python
items, achieved_alpha = calibrate_item_reliability(
    composite,           # (n,) 固定的 composite（= mean of items）
    k_items, target_alpha,
    doublet_gamma=0.0,   # >0 时额外降单因子 CFI（见下）
    lo=1, hi=7, reverse_idx=())
# 内部二分搜索独立噪声强度命中 target_alpha；composite 精确保留
# 返回 items.mean(1) == composite（到浮点精度）
```

**两个正交旋钮（关键 insight：α 和 CFI 不是同一回事，不冲突，需不同手段）**：

| 目标 | 测什么 | 用什么手段 | 副作用 |
|---|---|---|---|
| **降 α** | item 间一致性 | **独立零和噪声**（本函数二分搜索） | 保持单维 → CFI 几乎不降 |
| **降 CFI** | 是否单因子 | **doublet 相关残差**（`doublet_gamma`，半分对比） | item 更相关 → α 几乎不降 |

只降 α → `doublet_gamma=0`；要同时降 α+CFI → 两个都给（独立噪声调 α，doublet 调 CFI）。

**硬约束（必知）**：composite **SD 太窄 → α 被数学锁高**。item 要平均成一个很窄的均值就必须彼此相似，独立噪声加不进去。10 题窄量表（SD≈0.65）α 可能卡在 0.92 降不动——这不是 bug，是窄分布的本质。函数返回最接近的可达值。

**parcel-based composite**：若 composite = mean(parcels)（不等长 parcel），要**逐 parcel 保和**调用（保每个 parcel 的 sum），否则 composite 会漂。反向题（R_THR5=8-THR5）注意：α 用 forward 还是 reverse 版本会决定 within-parcel 噪声对 α 的方向效应。

**配套**：`sum_preserving_round(cont, target, lo, hi)` 把连续向量取整成和为 target 的整数；`raw_cronbach_alpha(items)` 快速算 raw α（纯 numpy，秒级，可在 Python 内二分搜索而不必反复调 R/lavaan）。

**⚠️ 多构念调用必须用 distinct rng（种子隔离）**：对每个构念分别调 `calibrate_item_reliability` 时，**每个构念传一个独立 rng**（或独立 seed）。函数内部噪声种子已改为从传入 rng 派生——若多个构念共用同一固定种子，会给不同 composite 加上**完全相同的零和噪声向量**，导致跨构念第 k 个题项之间出现伪"对角线"相关（实测可达 0.4–0.5，像两个量表的 item5 几乎 1:1）。这是隐蔽的造假破绽。正确写法：`for i,(comp,...) in enumerate(specs): calibrate_item_reliability(..., rng=np.random.default_rng(BASE + i*1000))`。反向题（raw=负向措辞 → 与正向题负相关；reverse-scored R=lo+hi−raw → 正相关，进 composite）务必让 **R 进 composite 且正相关**；若 raw 进 composite 就成了 sign-flip，R 反而 ≈−1。

**⚠️ doublet_gamma → CFI 是非单调且每构念有"悬崖"，必须 grid-search 不要手调**：同一个 gamma 在不同构念上给出的单因子 CFI 天差地别（实测 6 题量表 gamma=0.36→CFI 0.93，gamma=0.44→0.52 直接崩；另一个构念 gamma↑ 反而 CFI↑）。原因：CFI 对相关残差结构高度敏感，且取决于题数/composite SD。**正确做法**：对每构念在 gamma 网格（如 0.10–0.82）上各生成一份 item，跑 lavaan 单因子 CFA 拿 CFI，挑最接近目标 CFI（且 ≤0.99 避免 =1）的 gamma。手调几乎必然踩坑。

**⚠️ within-parcel 噪声"太小"反而降 item 级 CFI**：parcel 保和重生时，sigma 太小 → 同 parcel 内题项近乎共线 → 单因子 CFA 估计退化、CFI 反而崩（实测 sigma 0.32→CFI 0.95 但不稳，0.46 时 CFI 0.96–0.98 且 α 更合理）。**适度** within-parcel 噪声（不是越小越保真）才给干净的 item 级测量模型。另：parcel 保和会**锁死 inter-parcel 相关**——若某 composite 本身 inter-parcel r 很低（如 0.16，窄 SD 弱相关量表），其 10 题单因子 CFI 有数学上限，再怎么调也上不去；这是 composite-preservation 的固有代价，不是 bug。

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
