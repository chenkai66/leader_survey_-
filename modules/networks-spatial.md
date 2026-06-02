# networks-spatial.md — 图 / 网络 / 空间

随机图模型（ER/BA/WS/SBM）+ 2D 空间点模式 / 高斯随机场 / Moran's I 自相关。
返回 edge-list（list of tuples），不依赖 networkx。

---

## 1. Erdős-Rényi G(n,p)（`graph_er`）

```python
edges = graph_er(n, p, directed=False, rng=None)
# 每对节点独立有概率 p 连边
# 期望边数 = n(n-1)/2 · p（无向）
```

---

## 2. Barabási-Albert 偏好连接（`graph_ba`）—— 幂律度分布

```python
edges = graph_ba(n, m, rng=None)
# 从 m+1 全连接核开始；每加一个新节点连 m 条边，目标按现有度概率
# 度分布近似幂律 P(k) ∝ k^{-3}
```

---

## 3. Watts-Strogatz 小世界（`graph_ws`）

```python
edges = graph_ws(n, k, p, rng=None)
# 起始环 + 每节点连 k 个最近邻；每条边以 p 概率重接到随机节点
# 兼具高聚类系数 + 短路径长度
```

---

## 4. Stochastic Block Model（`graph_sbm`）—— 社区检测基准

```python
edges, blocks = graph_sbm(block_sizes=[20,20,30], p_in=0.5, p_out=0.05, rng=None)
# 同块连边概率 p_in；跨块 p_out
# 返回 (edges, block_membership 向量)
```

---

## 5. 度分布 / 聚类系数（用 numpy）

```python
deg = np.zeros(n, int)
for u, v in edges: deg[u] += 1; deg[v] += 1
print('avg degree:', deg.mean())
print('max degree:', deg.max())
# 三角形 / 聚类系数: 邻接矩阵 trace((A@A)@A) / count_potential_triangles
```

---

## 6. 空间点模式（`spatial_points`）

```python
spatial_points(n, region=(x0,x1,y0,y1), pattern="poisson"|"cluster"|"regular",
               cluster_params=None, rng=None)
# poisson  = 完全空间随机（CSR）
# cluster  = Thomas 过程（parents + offspring with spread）
# regular  = 扰动正方格点
```

---

## 7. 高斯随机场（`spatial_field`）—— 地统计

```python
field = spatial_field(grid_size, range_param=0.2, sill=1.0, nugget=0.0, rng=None)
# 指数协方差 C(h) = sill·exp(-h/range) + nugget·I
# 返回 (grid_size, grid_size) 数组
# range_param 越大，相邻格点越像
```

---

## 8. Moran's I 全局空间自相关（`morans_i`）

```python
mi = morans_i(values, coords, k_neighbors=8)
# values: (n,) 节点值；coords: (n, 2) 坐标
# 用 k-NN 二元权重；I ∈ [-1, +1]；+1 = 强空间聚集
```

诊断生成的空间场是否真有自相关：随机噪声的 Moran I ~ 0；强场 ~ 0.5-0.8。

---

## 9. 网络属性诊断思路

- **度分布**：histogram(deg) — 长尾 = preferential attachment 特征
- **平均路径长度**：`scipy.sparse.csgraph.shortest_path` 或自己 BFS
- **聚类系数**：每节点局部 C_i = 邻居间存在边数 / C(k_i, 2)
- **社区检测准确率**（对 SBM）：标签 vs 真 blocks 的 ARI/NMI

---

## 10. 函数清单

`graph_er` / `graph_ba` / `graph_ws` / `graph_sbm` / `spatial_points` / `spatial_field` / `morans_i`。

如需更复杂图（configuration model 给定度序列 / spatial network）：用基础原语自己组装。
