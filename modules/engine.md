# engine.md — 核心标定算法

数据调整的"机芯"。其他模块的方法都建立在这几个原语上。当没有现成函数命中你的目标时，回到这里组装。

---

## 1. 通用标定循环（万能兜底，`tune_scalar`）

**任何能写成"度量函数"的目标都能用此逼近**（偏度、AUC、Gini、OR、患病率、ICC、自相关、任意自定义指标）。这是最 robust 的方法，永远可退守。

```python
def tune_scalar(make_and_measure, target, x0=0.0, lo=-5.0, hi=5.0, tol=1e-3, iters=60):
    """单旋钮割线/二分：make_and_measure(x)->achieved_metric。返回命中 target 的 x。
    端点同号→割线推（带步长 clip 防溢出）；端点异号→二分。"""
```

**多旋钮多目标**：逐旋钮轮流 tune，或用不动点迭代：`eff_target += lr*(desired - achieved)`，参考 `rebuild_block` 的实现。

**取整/clip/约束都会引入偏差** → 总在"成品"上度量，把偏差反馈回去，不要信解析公式一次到位。

---

## 2. β=R⁻¹r 条件高斯（`build_latents`）—— 多目标精确命中

让一组潜变量对一组给定预测变量的样本内相关**精确**命中目标向量 + 彼此之间的目标交叉相关。

原理：β = R_g⁻¹ r 推导回归权重，signal = G_z @ β + 正交残差（残差化→白化→上色到 resid_cov）。

```python
def build_latents(givens_z, targets, pair_corr=None, rng=None):
    """givens_z:(n,k) 标准化预测；targets: list of length-k 相关向量；
    pair_corr:(m,m) 新变量间相关。返回 (n,m) 潜变量，每列 var=1，
    样本内对 givens 的相关 = targets 精确，新变量间相关 = pair_corr 精确。
    可行性：r'Rg^-1 r < 1（resid variance > 0），否则报错。"""
```

**前提**：隐含近正态。边缘非正态时 Pearson 会被边缘形状扭曲 → 改用 `iman_conover`（保边缘）或 `gaussian_copula`（指定边缘）。详见 `dependence.md`。

---

## 3. 外层校正循环（`rebuild_block`）—— Likert 取整衰减补偿

Likert/离散化会衰减相关（atten ~0.9）。在"成品"上量实测相关，差值反馈到 eff_target，重建——通常 9 次落进 ±0.02。

```python
def rebuild_block(df, given_cols, specs, pair_corr=None, item_sigma=0.66,
                  outer=9, lr=0.85, lo=1, hi=7, rng=None):
    """specs 每项 = {items: [...], comp: ..., mean, sd, tgt, optional extra}。
    extra 是循环内注入的乘积项（交互效应），不会稀释主相关。"""
```

**关键点**：交互/干扰项必须**循环内**注入（事后加再 Likert 会稀释主相关）。

---

## 4. ICC 内层迭代（`icc_rebuild`）—— 多层组间-组内方差精确命中

取整对组间方差是**非线性压缩**，加上组大小不等 → "标准化到 SD=1" ≠ "ANOVA 组间分量=1"。必须实测方差分量后内层迭代 rescale（`cb, cw` 反复校正），别信解析一次到位。详见 `multilevel.md`。

---

## 5. Full-mediation 设计（防抑制翻号）

**关键认知**：zero-order 相关与 partial（回归）系数**数学耦合，不能各自手设**。强中介下：
- 若给 outcome 设弱的 X zero-order 目标 → 控制中介后的 partial direct 会**翻号**（典型坑：理论上 Aut→Thriving 该负，partial 却 +0.20***）。
- 解法：outcome **只**由 mediator 生成 → 直效 partial≈0、方向不翻；X→outcome 的 zero-order 自然 = 完全中介值。
- 要小直效（部分中介）→ 用结构方程式直接设：`y = b1·z_m1 + b_dir·z_x + noise`，b_dir 即 partial。
- **间接效应 IE = a·b 必须和路径表一致**；改完抽查 `IE ≈ a×b`。

详见 `causal.md` 中介专节 + `multilevel.md` Likert/factor 应用。

---

## 6. 通用工作流（任何场景）

```
1. 把目标写成"度量函数" f(data)→metric
2. 选生成机制（structural eq / latent + Likert / copula / Iman-Conover ...）
3. 用闭式法初始化（β=R⁻¹r 等）；不可行就 tune_scalar 兜底
4. Likert/取整/约束后用外层循环修正实测偏差
5. 多层/混合 → 内层 rescale 修正方差分量
6. 复测每个目标 + 结构不变量；不过则回到 3
```

---

## 7. 可行性 / 冲突 / 顺序

- **可行性**：相关阵正定（`nearest_pd` 项目正定截断）；`r'Rg⁻¹r<1` 才能命中一组相关；约束之间不能互斥。先验可行性，不可行就回报而不硬凑。
- **冲突**：相关 + 边缘 + 约束常互相牵制。优先级一般：**结构不变量 > 边缘分布 > 依赖结构 > 高阶矩**（先满足硬约束，再分布，再相关；相关里取整会动分布故回头微调）。
- **顺序**：先定边缘 →（Iman-Conover 保边缘加相关 或 copula 同时定）→ 加模型效应 → 施加约束/缺失/异常 → 复测。施加硬约束可能破坏相关，故约束后再复测。
- **非确定/非幂等管道**：别为微调重跑整条管道（漂掉手调）；对 committed 实例做外科手术（`git checkout` 基线 + 一次性 transform）。
