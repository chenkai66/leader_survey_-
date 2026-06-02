# diagnostics-privacy.md — 诊断 + 隐私 + 重加权 + 缺失/异常注入

生成数据后必跑的"破绽自查" + 重加权到总体 + 隐私扰动 + 缺失模式 / 异常 / 异方差注入。

---

## 1. 黄金校验流程（生成后必跑）

```
1. verify(df, [(a, b, target), ...])     # 批量核相关
2. report(df, cols)                       # 全列均值/SD/偏度/峰度/缺失/范围 + Pearson/Spearman 矩阵
3. 关键指标用专用函数复测（KS / GoF / Mardia / ICC / α / ...）
4. 多维一致性：见 multitable.md 的 check_*
5. 真实度（vs 真实数据）：discriminability
```

---

## 2. verify —— 通用相关核验

```python
verify(df, checks=[("x","y", 0.5), ...], tol=0.02)
# 输出 PASS/FAIL；返回 all-pass bool
```

---

## 3. report —— 一键全列诊断

```python
report(df, cols=None)
# 每列 mean/sd/skew/kurt/min/max/missing%
# Pearson + Spearman 相关矩阵
```
眼检"破绽"用——SE 别扎堆、相关别太镜像、α 别全 0.9+、组内 SD>0 等。

---

## 4. 分布拟合优度

| 检验 | 函数 | 用途 |
|---|---|---|
| Kolmogorov-Smirnov | `ks_stat(x, target_ppf)` | 一列对目标分布拟合度（小=好） |
| Anderson-Darling | `anderson_darling_normal(x)` | 对正态拟合（A²>0.752 α=.05 拒绝） |
| Pearson chi-square | `chi_square_gof(observed, expected)` | 离散/分桶频数拟合 |

---

## 5. 分布相似 / 漂移检测

| 指标 | 函数 | 解读 |
|---|---|---|
| PSI（Population Stability Index）| `psi(ref, cur, bins=10)` | <0.1 稳定 / 0.1-0.25 中度 / >0.25 严重漂移 |
| Jensen-Shannon divergence | `js_divergence(p, q, bins=30)` | 对称、有界、距离感（0=完全相同） |
| Discriminability（合成 vs 真实）| `discriminability(real_df, syn_df)` | logistic 分类 AUC：≈0.5 = 不可识别（合成真实度好） |

---

## 6. 多元正态性 / 异常检测

```python
b1, b2, z_kurt = mardia_normality(X)
# Mardia 多元偏度+峰度；z_kurt 接近 0 = 正态

dists, flags = mahalanobis_outliers(X, threshold=None)
# 马氏距离 + 异常标记；阈值默认 sqrt(chi²_0.975, p) 启发式
```

---

## 7. 信度 α（量表）

```python
alpha = cronbach_alpha(item_matrix)
# 必须题项重算 = 显示值（黄金法则）；别只写报表
```

---

## 8. 重加权到总体边际

```python
w = rake(df, margins={"sex":{0:0.7,1:0.3}, "age":{...}}, iters=50)
# IPF 迭代缩放，命中各列目标边际
```

---

## 9. IPW（propensity weight）

```python
w = ipw_weights(treatment, propensity)
# 见 causal.md，因果场景常用
```

---

## 10. 缺失模式注入（`inject_missing`）

```python
x_na = inject_missing(x, rate=0.1, mechanism="MCAR"|"MAR"|"MNAR", by=None)
# MCAR: 随机；MAR: 概率正比 rank(by)；MNAR: 概率正比 rank(自身值)
```
注意：回填仅动"原本非缺失"的格，否则破坏缺失模式。

---

## 11. 异常值注入（`inject_outliers`）

```python
x_out = inject_outliers(x, rate=0.02, k=4)
# 把 rate 比例的点拉到 mean ± k·SD（随机方向）
```

---

## 12. 异方差噪声（`heteroscedastic_noise`）

```python
e = heteroscedastic_noise(x_pred, base_sd=1.0, slope=0.5)
# sd = base_sd + slope·|x_pred|；配合 y = b·x + e 造 WLS 仿真
```

---

## 13. 差分隐私（`dp_noise`）

```python
y_dp = dp_noise(x, sensitivity, epsilon)
# Laplace(sensitivity/epsilon) 噪声，ε-DP
# x 是已聚合的统计量（计数/均值）
```
进阶（k-anonymity / l-diversity）：分层洗牌或微聚合替代（doc only）。

---

## 14. Bootstrap 扰动（`bootstrap_perturb`）

```python
df_boot = bootstrap_perturb(df, n=None, rng=None)
# 有放回重抽，保联合分布；用于 bootstrap CI / 鲁棒性
```

---

## 15. 组间效应（`shift_group_effect`）

```python
y_new = shift_group_effect(x, group, target_d=0.5, ref_group=None)
# 平移组均值使 Cohen's d 精确命中
```

---

## 16. 函数清单

诊断：`verify` / `report` / `ks_stat` / `anderson_darling_normal` / `chi_square_gof` / `psi` / `js_divergence` / `discriminability` / `mardia_normality` / `mahalanobis_outliers` / `cronbach_alpha`。

重加权：`rake` / `ipw_weights`（causal.md）。

注入：`inject_missing` / `inject_outliers` / `heteroscedastic_noise` / `dp_noise`。

其他：`bootstrap_perturb` / `shift_group_effect`。

---

## 17. 专家"破绽" tells 自查清单

改完逐条过：
1. 重算 α / ICC / 相关 / 路径系数 = 显示值（黄金法则）
2. 组内 SD > 0；不存在"一组一常数"
3. 相关别太镜像/对称；分布别太规整；SE 别扎堆
4. 路径与相关数学自洽
5. 边界/范围/类型/缺失率/重复
6. 多维一致性（外键 / 聚合 / 时序 / 行内恒等式）
7. 把每条目标编码进自动校验（师傅原则）
