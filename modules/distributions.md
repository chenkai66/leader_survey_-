# distributions.md — 边缘分布

让单列呈现任意目标分布：均值/SD/范围/偏度/峰度/命名分布/混合/截断/零膨胀/分位映射；以及"从真实数据拟合再合成"。

---

## 1. 简单 mean / SD / 范围（`rescale`）

```python
rescale(x, mean=None, sd=None, lo=None, hi=None)
# x' = (x-x.mean())/x.std()*sd + mean，再 clip 到 [lo, hi]。
# clip 会改回均值/SD，迭代或反向补偿。
```

---

## 2. 命名分布的统一抽样（`sample_dist`）

```python
sample_dist(dist, n, rng=None, **params)
# dist ∈ {normal, lognormal, exponential, gamma, beta, weibull, pareto, t,
#         chi2, poisson, negbin, geometric, uniform, truncnormal}
# params 因 dist 而异（mean/sd / shape/scale / a,b / df / lam …）
```

---

## 3. 任意目标分布 / 分位映射（`match_marginal`）—— 最通用

把 x 的秩映到目标分布的分位（保排序、改形状）：

```python
def match_marginal(x, target_ppf):
    r = (rankdata(x) - 0.5) / len(x)
    return target_ppf(r)
```
- 正态：`lambda q: mu + sigma * _phi_inv(q)`
- 对数正态/重尾/Beta/Gamma：换对应 ppf
- **匹配参考数据集**：`lambda q: np.quantile(ref, q)`（分位-分位映射）
- 偏度/峰度精确：用 `fleishman`（§5）

---

## 4. 计数 / 比例 / 有界

- 计数：`sample_dist('poisson', n, lam=...)` 或 `count_data`（Poisson/NB/零膨胀，见 `timeseries.md`）
- 比例[0,1]：`sample_dist('beta', n, a=..., b=...)`
- 有界整数：`np.round(np.clip(...))` 或 truncnormal

---

## 5. 精确偏度 + 峰度（`fleishman`）—— Fleishman 幂多项式

模拟研究里常要"非正态但矩可控"。Fleishman：`y = a + bz + cz² + dz³`（z~N(0,1)），牛顿解三方程使偏度、超额峰度命中目标。

```python
fleishman(z, skew, kurt)  # 返回 transformed array
fleishman_coef(skew, kurt)  # 返回 (a, b, c, d)
```
有可行域（峰度不能太低于偏度² 相关下界）；不可行报错——放大峰度或减小偏度。

---

## 6. 混合分布（多峰 / 异质）

```python
gaussian_mixture(n, weights, means, sds, rng=None)
# weights 自动归一；适合双峰、零膨胀替代、混合人群
```

---

## 7. 截断 + 零膨胀连续

```python
truncated_normal(n, mean, sd, lo, hi)
# 逆 CDF 抽样，极端截断也高效（不靠 rejection）

zero_inflated_continuous(n, zero_prob, positive_sampler)
# 保险理赔 / 基因表达：多个 0 + 正态/对数正态的正值
# positive_sampler(n, rng) 自定义正部分
```

---

## 8. 分类目标占比（`multinomial_dataset`）

```python
multinomial_dataset(n, probs)
# 精确分配（前 n1 个给类 0…再随机打散），目标占比一定命中
# 6/3/1 ratio + n=1000 → 精确 600/300/100
```

---

## 9. 组分数据（Dirichlet）

```python
dirichlet_compositional(n, alphas)
# (n, k) 行和 = 1。市场份额、配比、土壤组成
```

---

## 10. 模仿真实数据集（`fit_from_reference`）

抓真实数据每列**经验边缘**(分位) + **秩相关**(copula on normal scores)，返回 `sampler(n)` 产合成数据：

```python
sampler = fit_from_reference(real_df)
synth = sampler(5000)        # 边缘与依赖都匹配
```
用途：数据增强、教学、脱敏（叠 `dp_noise` 加隐私）、扩样。配合 `discriminability`（见 `diagnostics-privacy.md`）核真实度。

---

## 11. 日期 / 时间

`value = baseline + trend*t + seasonal(t) + noise`；工作时段/周末用掩码；事件时间用泊松过程（或 Hawkes，见 `timeseries.md`）。

---

## 12. 函数清单

`sample_dist` / `match_marginal` / `fleishman` / `fleishman_coef` / `gaussian_mixture` / `truncated_normal` / `zero_inflated_continuous` / `multinomial_dataset` / `dirichlet_compositional` / `fit_from_reference` / `rescale`。

诊断 `KS / Anderson-Darling`：见 `diagnostics-privacy.md`。
