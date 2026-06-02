# domain-specific.md — 行业特定数据

营销组合（MMM）、离散选择（条件 logit）、遗传学 SNPs（含 LD）、NLP/LDA 主题文档、神经元 spike trains。这些不是通用方法，但每个在自己领域是标准。

---

## 1. Marketing Mix Model（`marketing_mix_data`）—— 营销组合建模

广告渠道有**adstock**（延滞效应）和 **Hill 饱和**（边际递减）。MMM 仿真数据用于贝叶斯回归（PyMC-Marketing、Robyn）测试。

```python
df = marketing_mix_data(
    n_periods=52,                                # 一年周度数据
    channels={"tv":     {"spend_sd":10, "beta":5.0},
              "social": {"spend_sd":5,  "beta":3.0},
              "search": {"spend_sd":8,  "beta":4.0}},
    adstock_decay=0.5,             # 几何衰减系数 ∈ [0,1)
    saturation_alpha=2.0,          # Hill 形状参数
    saturation_gamma=0.5,          # Hill 半饱和点
    baseline=10.0,
    noise_sd=1.0)
# 返回列：t, spend_<ch>, adstock_<ch>, y
```

- `adstock_t = spend_t + decay · adstock_{t-1}`
- `contribution = β · s^α / (s^α + γ^α)`（Hill）
- 真实 β 是渠道**最大贡献**，回归恢复 β/α/γ。

---

## 2. 条件 Logit / 离散选择（`discrete_choice`）—— 交通模式、购买选择

每个个体在 K 个备选项中选一个，效用 = 属性·系数：

```python
A = np.array([[1.0, 0.5],    # 备选项 0 的两个属性
              [2.0, 1.0],    # 备选项 1
              [0.5, 2.0]])   # 备选项 2
df = discrete_choice(n_individuals=2000, n_alternatives=3,
                     attribute_matrix=A, coefs=[0.8, -0.3])
# 返回 individual / choice
# A 可以是 (n_alts, n_attrs) 共享，或 (n_indiv, n_alts, n_attrs) 个性化
```
P(choose j | i) = exp(x_ij · β) / Σ_k exp(x_ik · β)（IIA 假设）。

---

## 3. 遗传 SNPs + 连锁不平衡（`snp_genotypes`）—— GWAS / 群体遗传

```python
G = snp_genotypes(n_individuals=500, n_snps=20,
                  maf=[0.3]*20,          # 次等位基因频率
                  ld_strength=0.4)       # 相邻 SNP 相关
# G ∈ {0, 1, 2} 加性编码，shape=(n_indiv, n_snps)
```
机制：通过 AR(1) Gaussian copula 在正态分上诱导相邻 SNP 相关，再按 MAF 阈值映射到基因型。adjacent SNP corr ≈ ld_strength。用于 GWAS / 多基因风险评分（PRS）方法基准。

---

## 4. LDA 主题文档（`lda_documents`）—— NLP / 主题模型

```python
dtm, doc_topic = lda_documents(
    n_docs=200, n_topics=5, vocab_size=500,
    doc_lengths=None,                          # 默认 randint(50,200)
    topic_word_concentration=0.1,              # 主题-词 Dirichlet α（小=稀疏）
    doc_topic_concentration=0.5)               # 文档-主题 Dirichlet α
# dtm: (n_docs, vocab_size) 文档-词频矩阵
# doc_topic: (n_docs, n_topics) 真实主题分布
```
用途：测 LDA / NMF / Top2Vec / 主题一致性指标。

---

## 5. 神经元 spike trains（`spike_train`）—— 神经科学 / 神经信号处理

```python
trains = spike_train(n_neurons=10, T_seconds=60.0,
                     base_rate=20.0,            # Hz
                     refractory_ms=2.0)         # 不应期
# 返回 list of arrays（每个神经元的 spike 时刻数组，秒）
```
Poisson 过程 + 不应期（接受-拒绝）。基础 firing rate / 跨神经元同步性 / spike-triggered average 等分析的基准数据。

---

## 6. 函数清单

`marketing_mix_data` / `discrete_choice` / `snp_genotypes` / `lda_documents` / `spike_train`。

---

## 7. 与其他模块的桥接

- 多通道间相关 / 媒介-基线相关 → `dependence.md`（`build_latents`）
- SNP-表型关联回归 → `regression.md`（`linear_dataset` / `logistic_dataset`）
- 主题模型评测 → `diagnostics-privacy.md`（perplexity 需自己算，KL/JS 可用）
- 神经元 cross-correlation / synchrony → 用 numpy 自己算
- 这些场景常配 `engine.md` 的 `tune_scalar` 调单旋钮命中目标
