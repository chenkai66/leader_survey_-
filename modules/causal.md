# causal.md — 因果推断与实验设计 + 生存

DAG/SCM、A/B 测试、IPW、propensity matching、DiD、RDD、IV、cluster RCT；生存：Cox-PH、竞争风险、复发事件。

---

## 1. DAG / 结构因果模型（`dag_sample`）—— 通用因果数据生成器

按拓扑顺序生成；每个 node = `(name, fn(data_dict, n, rng) -> array)`。**一次造出含混淆 / 中介 / 对撞 / 工具变量**的数据，用来评测因果推断方法的偏差与覆盖率。

```python
df = dag_sample(n, [
    ("U", lambda d,n,r: r.standard_normal(n)),                  # 未观察混淆
    ("X", lambda d,n,r: 0.6*d["U"] + r.standard_normal(n)),
    ("Y", lambda d,n,r: 0.4*d["X"] + 0.5*d["U"] + r.standard_normal(n)),
])
# 未调整 OLS(Y~X) 偏；控 U 后 b=0.40。
```

---

## 2. A/B 测试模拟（`ab_test_data`）

```python
ab_test_data(n_per_arm, baseline=0.0, effect=0.2, sd=1.0,
             metric="continuous"|"binary"|"count",
             arm_names=("control","treatment"))
# 返回 df with arm, y
```
Power 仿真：用 `tune_scalar` 找 n 使 reject 率 = 0.8。

---

## 3. IPW 权重（`ipw_weights`）

```python
w = ipw_weights(treatment, propensity)
# w = t/p + (1-t)/(1-p), 含自动 clip [0.02, 0.98]
```
用法：估计 ATE = `(y·t·w).sum()/(t·w).sum() − (y·(1-t)·w).sum()/((1-t)·w).sum()`。

---

## 4. Propensity Score Matching（`propensity_match`）

```python
pairs = propensity_match(treatment, propensity, ratio=1, caliper=None)
# 1:k 最近邻匹配，返回 [(treated_idx, [control_idx...]), ...]
# caliper 限制最大距离（在 propensity 标量空间）
```

---

## 5. Difference-in-differences（`did_data`）

```python
did_data(n_per_group, n_periods=2, treatment_time=1, treated_share=0.5,
         treatment_effect=0.5, time_trend=0.1, baseline=0.0, noise_sd=1.0)
# 长格式：unit/time/treated/post/treated_post/y
# DiD 估计 = E[Δy|treated] - E[Δy|control] = treatment_effect (target)
```

---

## 6. Regression Discontinuity（`rdd_data`）—— Sharp RD

```python
rdd_data(n, cutoff=0.0, treatment_effect=0.5, slope_left=1.0, slope_right=1.2,
         noise_sd=1.0, running_dist="normal"|"uniform")
# T = (running >= cutoff)
# 返回 running/treated/y
```
局部线性估计：在 cutoff 附近窗口内比较两侧均值差 ≈ treatment_effect。

---

## 7. Instrumental Variable（`iv_data`）

```python
iv_data(n, b_xy=0.5, b_zx=0.7, confounder_strength=0.5)
# Z → X → Y，U → X 且 U → Y（OLS 偏；2SLS 用 Z 无偏）
# 返回 df with z/x/y/u
```
2SLS 验证：`Y ~ X_hat`（X_hat 来自 Z 回归 X）。

---

## 8. Cluster RCT（`cluster_rct`）

```python
cluster_rct(n_clusters, n_per_cluster, treatment_effect=0.5, icc=0.1,
            baseline=0.0, noise_sd=1.0)
# 集群级随机化；每集群共享随机截距。SE 比个体 RCT 膨胀（design effect）
```

---

## 9. 中介 / 调节（与 `engine.md` §5 互补）

- 完全中介数据：outcome 只由 mediator 生成 → partial direct≈0 不翻号
- 部分中介：结构方程式直接设小直效项
- 交互注入：`rebuild_block(extra=coef·zscale(z_x·z_w))`
- IE = a·b 必须自洽，改完抽查

---

## 10. 生存 / Cox-PH（`survival_data`）

```python
survival_data(n, baseline_rate=0.1, hazard_ratios=[exp(β)], X=X,
              censor_rate=0.2, dist="exp"|"weibull", weibull_shape=1.5)
# λ(x) = λ_0 · exp(β·x); T~Exp 或 Weibull; 独立 Exp 截尾
# 返回 df with time/event/x_*
```

---

## 11. 竞争风险（`competing_risks_data`）—— 多病因

```python
competing_risks_data(n, baseline_rates=[λ_1, λ_2, λ_3], hazard_ratios=None,
                     X=None, censor_rate=0.1)
# 每个 cause k 有独立 Exp(λ_k·exp(β_k·X))；时间 = min；cause = argmin（censored = -1）
```

---

## 12. 复发事件（`recurrent_events_data`）

```python
recurrent_events_data(n, baseline_rate, max_time, frailty_sd=0.5)
# Poisson 事件 + 共享 LogN frailty 膨胀个体率
# 返回长格式 subject/time
```

---

## 13. 函数清单

`dag_sample` / `ab_test_data` / `ipw_weights` / `propensity_match` / `did_data` / `rdd_data` / `iv_data` / `cluster_rct` / `survival_data` / `competing_risks_data` / `recurrent_events_data`。

时间序列见 `timeseries.md`；多评分者/多层见 `multilevel.md`。
