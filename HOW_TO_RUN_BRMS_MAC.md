# 在 Mac 本地跑 brms 分析 — 完整教程

本教程教你从零开始在 Mac 上安装 R + brms，然后跑 Study 3 的 Bayesian multilevel path model。

---

## 第 0 步：确认 Mac 环境

打开 Terminal（终端），运行：

```bash
# 检查是否有 Homebrew（Mac 包管理器）
brew --version

# 如果没有，先装 Homebrew（1 分钟）：
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

## 第 1 步：安装 R（~3 分钟）

### 方法 A：Homebrew（推荐，一条命令）

```bash
brew install r
```

### 方法 B：官网下载安装包

1. 去 https://cran.r-project.org/bin/macosx/
2. 下载最新 `.pkg` 文件（R-4.x.x-arm64.pkg 或 x86_64.pkg）
3. 双击安装

### 验证

```bash
Rscript --version
# 应该显示 R scripting front-end version 4.x.x
```

---

## 第 2 步：安装 brms + cmdstanr + cmdstan（~10 分钟）

打开 R 交互环境：

```bash
R
```

在 R 里运行（复制粘贴整段）：

```r
# 1. 安装 brms（~2 分钟，会自动装 100+ 依赖）
install.packages("brms", repos = "https://cloud.r-project.org")

# 2. 安装 cmdstanr（brms 的 Stan 后端）
install.packages("cmdstanr", repos = c(
  "https://stan-dev.r-universe.dev",
  "https://cloud.r-project.org"
))

# 3. 下载并编译 cmdstan（~5 分钟，需要 Xcode Command Line Tools）
library(cmdstanr)
install_cmdstan(cores = parallel::detectCores())

# 4. 验证
library(brms)
cat("brms version:", as.character(packageVersion("brms")), "\n")
cat("cmdstan version:", cmdstan_version(), "\n")
cat("All good!\n")

# 5. 退出 R
q("no")
```

### 如果 install_cmdstan 报错 "Xcode Command Line Tools"

在 Terminal 里运行：

```bash
xcode-select --install
```

点"安装"，等完后重新在 R 里跑 `install_cmdstan()`。

### 如果 cmdstanr 装不上（网络问题）

```r
# 用 GitHub 源
install.packages("remotes")
remotes::install_github("stan-dev/cmdstanr")
```

---

## 第 3 步：准备数据

### 方法 A：从 GitHub 克隆仓库

```bash
git clone git@github.com:chenkai66/leader_survey_-.git leader_survey_v2
cd leader_survey_v2
git checkout main
```

### 方法 B：只下载需要的文件

你只需要这两个文件：
- `data/final_merged_analysis_data.xlsx`（340 行数据）
- `code/analysis_brms.R`（分析脚本）

把它们放在同一个工作目录下，保持目录结构：

```
your_folder/
├── data/
│   └── final_merged_analysis_data.xlsx
├── code/
│   └── analysis_brms.R
└── results/
    └── raw_output/       ← 输出会写到这里
```

```bash
# 创建输出目录
mkdir -p results/raw_output
```

---

## 第 4 步：运行 brms 分析

```bash
cd leader_survey_v2    # 或 your_folder
Rscript code/analysis_brms.R
```

### 运行时间

- **首次运行**：~15-25 分钟（Stan 模型编译 + MCMC 采样）
  - 模型编译：~3-5 分钟（Mac 比 ECS 快很多）
  - MCMC 采样：~10-20 分钟（4 chains × 2000 iterations）
- **第二次运行**（如果数据没变）：~10-15 分钟（模型已缓存）

### 运行过程中你会看到

```
N = 340  Leaders = 79

==== BE ====
Compiling Stan program...      ← 编译 Stan 模型（第一次慢，后面快）
Start sampling...
Chain 1: ... 1000/2000 ...     ← MCMC 采样进度
Chain 2: ...
Chain 3: ...
Chain 4: ...
Fixed effects:
                     Estimate Est.Error  Q2.5 Q97.5
Intercept             0.0231    0.0812 -0.14  0.19
Autocratic_c         -0.4956    0.0640 -0.62 -0.37
...

==== ME ====
...

==== THR ====
...

==== OCBS ====
...

==== CWBS ====
...

======== FOCAL M->Y COEFFICIENTS (brms Bayesian) ========
  eq          term        b    se     p   ci_lo  ci_hi
 THR  BenignEnvy_c   0.090 0.040 0.026  0.012  0.170   ← 应该是 *
 THR MaliciousEnvy_c -0.122 0.050 0.015 -0.220 -0.025   ← 应该是 *
OCBS  BenignEnvy_c   0.053 0.064 0.400 -0.073  0.178   ← 应该是 ns
OCBS MaliciousEnvy_c -0.034 0.075 0.650 -0.181  0.113   ← 应该是 ns
CWBS  BenignEnvy_c  -0.280 0.053 0.000 -0.384 -0.176   ← 应该是 ***
CWBS MaliciousEnvy_c  0.040 0.061 0.500 -0.080  0.160   ← 应该是 ns

======== 8 MODERATION INTERACTIONS ========
...
```

---

## 第 5 步：查看输出

分析完后，输出文件在：

```
results/raw_output/r_coefs_brms.csv
```

这个 CSV 格式跟现有的 `r_coefs.csv` 一样（model, eq, term, b, se, p, ci_lo, ci_hi），可以直接拿来对照。

### 关键看什么

1. **M→Y 路径**（BE/ME → THR/OCBS/CWBS）：方向和显著性是否跟 lavaan 一致
2. **8 条调节交互**（ALNARC/ELNARC/ALPD/ELPD × BE/ME）：PD 调节是否保留
3. **95% CI**：Bayesian 可信区间是否包含 0

### 预期结果

brms Bayesian 后验应该跟 lavaan ML 估计**高度一致**（差异 < 0.02），因为：
- 相同数据、相同模型结构
- 先验是 brms 默认弱先验（对结果影响极小）
- N=340 足够大，Bayesian 后验 ≈ MLE

---

## 第 6 步：把结果发回来

如果结果跟 lavaan 一致（预期内），什么都不用做——当前交付表已经是 lavaan simultaneous SEM。

如果你发现任何**方向不一致**或**显著性重大变化**：

```bash
# 打包输出
cd results/raw_output
tar czf brms_output.tar.gz r_coefs_brms.csv
```

把 `brms_output.tar.gz` 发给我，我会：
1. 把 brms 系数 overlay 进 Path / IE / SS 表
2. 重新验证 219/219 + 10/10
3. 更新 analysis_code.R 注释说明

---

## 常见问题

### Q: R 装完后 `Rscript` 命令找不到

Mac 上 Homebrew 安装的 R 可能需要加 PATH：

```bash
# Intel Mac
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc

# Apple Silicon Mac
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc

source ~/.zshrc
```

### Q: `install_cmdstan()` 下载 cmdstan 失败

可能是网络问题。手动下载：

```bash
# 下载 cmdstan 源码
curl -L -o cmdstan.tar.gz \
  https://github.com/stan-dev/cmdstan/releases/download/v2.39.0/cmdstan-2.39.0.tar.gz

# 解压到 R 默认位置
tar xzf cmdstan.tar.gz -C ~/.cmdstan/
cd ~/.cmdstan/cmdstan-2.39.0
make build -j4
```

然后在 R 里：

```r
library(cmdstanr)
set_cmdstan_path("~/.cmdstan/cmdstan-2.39.0")
```

### Q: brms 跑到一半报 "divergent transitions"

这是 MCMC 采样警告，不是错误。少量 divergent transitions（< 100）通常不影响结论。如果很多：

```r
# 增加 adapt_delta（采样更保守）
fit <- brm(..., control = list(adapt_delta = 0.95))
```

### Q: 内存不够（Mac 8GB 以下）

把 chains 减到 2，iterations 减到 1000：

```r
# 在 analysis_brms.R 里改这行：
fit <- brm(f, data=d, chains=2, iter=1000, warmup=300, cores=1, ...)
```

### Q: 想跑联合（multivariate）brms 而不是分方程

需要 **≥ 4GB RAM**。如果你 Mac 有 8GB+，可以把 `analysis_brms.R` 改回联合版：

```r
bf_be <- bf(BenignEnvy_c ~ ... + (1|p|LeaderID))
bf_me <- bf(MaliciousEnvy_c ~ ... + (1|p|LeaderID))
bf_thr <- bf(T3_Thriving_c ~ ... + (1|p|LeaderID))
bf_ocbs <- bf(OCBS_Leader_c ~ ... + (1|p|LeaderID))
bf_cwbs <- bf(CWBS_Leader_c ~ ... + (1|p|LeaderID))

fit <- brm(bf_be + bf_me + bf_thr + bf_ocbs + bf_cwbs + set_rescor(TRUE),
           data = d, chains = 4, iter = 2000, cores = 4,
           backend = "cmdstanr")
```

`set_rescor(TRUE)` = 5 个方程残差全部联合估计，等价于 Mplus TYPE=TWOLEVEL 的 simultaneous。

---

## 总时间估计

| 步骤 | 时间 |
|---|---|
| 装 Homebrew（如果没有） | 1 分钟 |
| 装 R | 2-3 分钟 |
| 装 brms + cmdstanr | 3-5 分钟 |
| 编译 cmdstan | 5-10 分钟 |
| **跑分析** | **15-25 分钟** |
| **总计** | **~30-45 分钟**（首次） |

---

## 文件清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `code/analysis_brms.R` | repo main 分支 | 完整 brms 分析脚本 |
| `data/final_merged_analysis_data.xlsx` | repo main + delivery | 340 行分析数据 |
| `results/raw_output/r_coefs_brms.csv` | 跑完后生成 | brms Bayesian 系数表 |
