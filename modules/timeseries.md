# timeseries.md — 时间序列与序列

AR/ARMA/GARCH/VAR、Markov、Hidden Markov、Hawkes 自激点过程、计数。

---

## 1. AR(p) 简单（`ts_ar`）

```python
ts_ar(n, ar=(0.7,), trend=0.0, seasonal=None, sd=1.0, mean=0.0)
# x_t = Σ φ_i x_{t-i} + ε_t + 趋势 + sin 季节
# seasonal=(period, amplitude)
```
AR(1) 的 lag-1 acf ≈ φ₁。

---

## 2. ARMA(p,q)（`ts_arma`）

```python
ts_arma(n, ar=(), ma=(), sd=1.0, mean=0.0)
# x_t = Σ φ_i x_{t-i} + ε_t + Σ θ_j ε_{t-j}
# MA 分量给短期冲击额外持续性
```

---

## 3. GARCH(1,1)（`ts_garch`）—— 波动率聚集

```python
returns, sigma = ts_garch(n, omega=0.05, alpha=0.1, beta=0.85, mean=0.0)
# σ_t² = ω + α·ε_{t-1}² + β·σ_{t-1}²
# ε_t = σ_t · z_t
# 平稳条件 α+β < 1。金融收益建模标准模型。
```
诊断：`|ε_t²` lag-1 acf > 0 = 波动率聚集。

---

## 4. VAR(p) 多元（`ts_var`）

```python
ts_var(n, A_list=[A_1, A_2, ...], Sigma, mean=None)
# y_t = c + Σ A_i y_{t-i} + ε_t,  ε~N(0, Sigma)
# A_list 是各 lag 的 (k,k) 系数矩阵
```

---

## 5. Markov 链（`markov_chain` / `fit_markov`）

```python
markov_chain(n, transition, init=None, states=None, rng=None)
# 由 (k,k) 转移阵抽样长 n 序列

fit_markov(sequences, states=None)
# 反向估计转移阵，返回 (P_hat, states)
```
用途：NLP n-gram、用户路径、状态机仿真。

---

## 6. Hidden Markov（`hmm_data`）

```python
states, observations = hmm_data(n, transition, emission_means, emission_sds, init=None)
# 高斯发射 HMM：latent state 演化 + 观察 ~ N(means[state], sds[state])
# 返回 (states, observations) 两个数组
```
用于训练 HMM 推断、Viterbi 解码基准。

---

## 7. Hawkes 自激点过程（`hawkes_process`）—— 事件聚集

```python
events = hawkes_process(T_max, mu=1.0, alpha=0.5, beta=1.0, rng=None)
# 强度 λ(t) = μ + Σ α·exp(-β(t - t_i))
# 平稳 α/β < 1。Ogata 稀释算法。
```
用途：地震余震、社交媒体级联、金融订单流。

---

## 8. 计数数据（`count_data`）

```python
count_data(n, mean, dispersion=None, zero_prob=0.0)
# dispersion=None → Poisson
# dispersion>0   → NegBin (variance = mean + mean²/k, smaller k = more overdispersed)
# zero_prob>0    → 加零膨胀混合
```

---

## 9. 多个相关时间序列

用 `build_latents` 造每期共享冲击，再走 AR：
```python
shocks = build_latents(rng.standard_normal((n, k)), targets=...)
# 然后每列分别走 AR(1) 或 VAR
```

---

## 10. 函数清单

`ts_ar` / `ts_arma` / `ts_garch` / `ts_var` / `markov_chain` / `fit_markov` / `hmm_data` / `hawkes_process` / `count_data`。

Long-format 面板见 `multilevel.md`（`panel_data`、`mixed_effects_dataset`）；状态演化见 `multitable.md`（`evolve_panel_state`）。
