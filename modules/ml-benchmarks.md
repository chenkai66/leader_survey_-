# ml-benchmarks.md — ML 基准数据 + Bayesian

分类 target AUC + 回归基准 + 概念漂移 + 异常检测 + SMOTE 不平衡 + 推荐系统 + 低秩/聚类 + 对抗扰动 + 标签噪声 + Bayesian 先验/Metropolis 后验。

---

## 1. 分类基准（`classification_dataset`）—— target AUC + 类不平衡

```python
classification_dataset(n, n_features=5, target_auc=0.8, class_balance=0.5,
                       feature_corr=None, rng=None)
# 特征 → noisy linear score → 阈值定标签
# 自动标定 SNR 命中 AUC、阈值命中类比例
```
实测可精确到 AUC ±0.003，balance ±0.005。ML 教学/基准/调优测试趁手。

---

## 2. 回归基准（`regression_benchmark`）—— 3 种噪声形态

```python
regression_benchmark(n, n_features=5, target_r2=0.5,
                     noise_type="normal"|"heavy_t"|"heteroscedastic",
                     feature_corr=None)
# normal: 同方差正态噪声
# heavy_t: 自由度 4 的 t 噪声（重尾，测 robust 估计）
# heteroscedastic: sd ∝ |x_1|（异方差，测 WLS / robust SE）
```

---

## 3. 概念漂移（`concept_drift_data`）—— 在线学习 / 漂移检测

```python
before, after = concept_drift_data(n, n_features=5,
                                   drift_type="covariate"|"label"|"prior",
                                   drift_magnitude=1.0, split=0.5)
# covariate: X 分布漂移（P(X) 变，P(y|x) 不变）
# label:     P(y|x) 漂移（系数变）
# prior:     类比例漂移（intercept 变）
```
配合 `psi` / `js_divergence`（`diagnostics-privacy.md`）测漂移检测器。

---

## 4. 异常检测（`anomaly_dataset`）

```python
anomaly_dataset(n, n_features=5, contamination=0.05,
                normal_sampler=None, anomaly_sampler=None)
# 95% 正常 + 5% 异常（默认从不同高斯）
# 返回 df with label ∈ {0=normal, 1=anomaly}
```

---

## 5. SMOTE 上采样（`smote`）—— 类不平衡

```python
X_new, y_new = smote(X, y, target_balance=0.5, k=5, rng=None)
# 在少数类点的 k 近邻间线性插值合成新样本
# 把少数类比例拉到 target_balance
```

---

## 6. 推荐系统：显式评分（`recsys_explicit`）

```python
R, mask, U, V = recsys_explicit(n_users, n_items, latent_dim=10,
                                signal_sd=1.0, noise_sd=0.5, sparsity=0.95)
# R = U @ V.T + noise；mask 决定哪些被观察
# 矩阵分解 / MF 基准数据
```

---

## 7. 推荐系统：隐式反馈（`recsys_implicit`）

```python
df = recsys_implicit(n_users, n_items, n_interactions,
                     popularity_skew=1.5, user_activity_skew=1.5)
# 用户活跃度 + item 流行度都按幂律（Pareto），生成 user-item 交互
```

---

## 8. 低秩矩阵（`low_rank_data`）—— PCA/SVD 基准

```python
M = low_rank_data(n, p, rank, signal_strength=1.0, noise_sd=0.5)
# n×p 矩阵 = (U @ V.T) + iid noise；top-rank 奇异值大，余小
# 用于 PCA 维度选择 / 低秩恢复算法基准
```

---

## 9. 聚类数据（`cluster_data`）—— 聚类算法基准

```python
X, y = cluster_data(n, n_clusters=3, n_features=2, separation=2.0,
                    cluster_sds=None)
# 中心在半径 separation 的圆上 + 每簇 Gaussian
# K-means / GMM / DBSCAN 基准
```

---

## 10. 对抗扰动（`adversarial_perturb`）—— Robust ML

```python
X_perturbed = adversarial_perturb(X, epsilon=0.1, norm="inf"|"2",
                                  direction=None, rng=None)
# ε-bounded 扰动；direction None = 随机方向（否则传梯度方向）
# 测模型对 L∞ / L2 扰动的鲁棒性
```

---

## 11. 标签噪声（`label_noise`）

```python
y_noisy = label_noise(y, noise_rate, n_classes=None, rng=None)
# 一致随机翻转到不同类；测 label-noise robust 学习算法
```

---

## 12. Bayesian：先验抽样（`prior_dataset`）

```python
prior_dataset(n, prior_specs, rng=None)
# prior_specs: dict {col: (dist_name, params)}, 内部调 sample_dist
# 例：{"mu":("normal",{"mean":0,"sd":1}), "sigma":("gamma",{"shape":2,"scale":1})}
```

---

## 13. Bayesian：Metropolis 后验（`metropolis_posterior`）

```python
chain = metropolis_posterior(log_post, x0, n_iter=5000, proposal_sd=0.3, burn=500)
# 1-D 随机游走 Metropolis；log_post(x) → 对数后验
# 多维：包装每坐标轮换或用分量 Metropolis-within-Gibbs
```

---

## 14. 函数清单

`classification_dataset` / `regression_benchmark` / `concept_drift_data` / `anomaly_dataset` / `smote` / `recsys_explicit` / `recsys_implicit` / `low_rank_data` / `cluster_data` / `adversarial_perturb` / `label_noise` / `prior_dataset` / `metropolis_posterior`。
