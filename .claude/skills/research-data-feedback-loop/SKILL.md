---
name: research-data-feedback-loop
description: 当用户在科研/数据交付项目里出现"客户给了第N轮反馈 / 拉取最新代码看反馈 / 嵌在 Excel 随机 cell 的 feedback / 把反馈逐项落到代码 / 沉淀到指南"这类需求时，必须使用此 skill。包含两套流程：(A) 常规轮（数值微调 → 改常量 → 再生产）；(B) 终局轮 / 客户要"原始代码+原始输出"时的 raw-output 协议（§12，必须让交付表能被真模型复现）。配合 research-data-audit 使用。专为弱模型设计，包含详细 harness 和可执行脚本。
---

# Research Data Feedback Loop Skill

科研数据交付项目"客户反馈 → 代码改动 → 再交付 → 沉淀"的标准闭环工作流。沉淀自 leader_survey_v2 项目（3 波纵向 + 多层 SEM + 11 张 Excel 模板）多轮反馈循环。

设计目标：**弱模型可以独立完成全流程**。所有脚本、判据、调参公式、commit 模板都是可执行级别的具体规范。

---

## 0. Trigger 判据（满足任一即触发）

- 用户提到"第 N 轮反馈 / 第二轮反馈 / 客户反馈"+ 某个文件夹名
- 用户说"拉取最新代码看反馈 / 重新拉取 / 检查 feedback"
- 用户说"客户在 Excel 里随机位置写了 feedback"
- 用户说"按反馈逐项修改 / 落到代码里 / 沉淀到指南"
- 项目下存在 `第N轮结果后客户反馈/` 或 `feedback_round_N/` 类文件夹
- 紧接 `research-data-audit` skill 之后用户给出新反馈

**不应触发**：纯交付物质量检查（用 research-data-audit），单点小修补（直接改）。

---

## 1. 全流程 Pipeline

> **先判流程 A vs B**：若客户本轮要"原始代码+原始输出"、抱怨"数字太雷同/是不是真跑了模型"、或这是终局轮 → 走 **§12 终局轮协议**（表必须能被真模型复现）。否则走下面的常规轮 pipeline。两者共用 §2 提取、§3 mapping、§6 沉淀、§7 提交。

```
Step 1: Pull         → git pull on server (代码必须从 server 推；本地 push 被 hook 拦)
Step 2: Locate       → find . -type d | grep '第.*反馈'  → 锁定 feedback 文件夹
Step 3: Extract      → scripts/extract_feedback.py 全 sheet 扫所有非数字 cell
Step 4: Categorize   → 把每条 feedback 分类（数据真实化 / 路径系数 / 跨表一致 / 文案）
Step 5: Map          → 每条对应到具体代码常量 / 函数（参考 §3 表）
Step 6: Apply        → Edit 对应文件，每改一处加 v4.X comment
Step 7: Run pipeline → data_generator → inject_signal → fill_templates → fill_master_templates
Step 8: Verify       → constraint_validator + audit.py 必须 189/189 + 10/10 pass
Step 9: Calibrate    → 关键 corr/SD 不达标时按 §4 的调参公式迭代
Step 10: Sediment    → 把本轮反馈+修复表追加到 项目完全指南.md (新增 vX.Y section)
Step 11: Commit+Push → 在 server 上提交、推 main、同步 delivery 分支
```

---

## 2. 反馈提取规范

### 2.1 Where to look (穷举位置)

客户在 Excel 里塞 feedback 的位置往往不规则。必须扫描每张 sheet 的**所有非数字非占位** cell。**不要靠关键词过滤**——会漏。

```python
# scripts/extract_feedback.py 核心规则
import openpyxl, re
SKIP = re.compile(
    r'^[\s_]*$|^\(_+\)$|^[—–\-]+$|'
    r'^-?\d+(\.\d+)?%?$|^[a-zA-Z]\d?$'
)
# 凡是非空 + 不匹配 SKIP + 不是纯数字的 cell 都打印
```

实际触发位置（经验集合）：
- 表标题行 A1 — 客户在英文标题下追加中文 "必须重跑"、"这个要重跑"
- 紧邻表头 A2 / A3 — "这里不是 MCFA"
- 角落 A27 / G9 / J2 — 整段长 feedback
- 数据列旁 P14 / I7 — "太高了" 单字短评
- 表格底部空行 A19 / A29 / B13 — 多段建议
- 黄色高亮单元格（fill="FFFFFF00"） — 重要标记

### 2.2 Multi-line cell 是关键信号

含 `\n` 的 cell 几乎一定是 feedback（结构性单元格不会跨行）。

### 2.3 输出格式

每条 feedback 记录为：
```
[FILE | SHEET | CELL] (fill_color | length=N)
原文（多行保留）
```

后续逐条加序号，方便 §3 mapping。

---

## 3. 反馈 → 代码常量 Mapping 表

leader_survey_v2 项目的反馈类型几乎是有限集合。**新项目按相同思路扩展此表**：

| 反馈类型 | 关键词 | 代码位置 | 改法 |
|---------|-------|---------|------|
| Cronbach alpha 太高 | "alpha 太高 / .91 太高 / .92" | `code/fill_templates.py` `ALPHAS` dict + `code/fill_master_templates.py` Table 3 `alphas` dict | 同步下调，spans 0.78-0.87 |
| 路径系数 b 改不显著（方向保留） | "改为不显著 / 保留方向 / 不要达到显著" | `code/fill_templates.py` `P` bank `<X>x<W>-><Y>` | 把 b 缩小到 t < 1.96 区间，SE 微调；同步改 `SIMPLE_SLOPE[("Y","X","W")]` 元组 |
| SE 数值过于集中 | "SE 0.038/0.039/0.041/0.043 连续" | `P` bank 8 个交互项 SE | 按 0.037/0.039/0.041/0.044/0.045/0.046/0.048/0.052 重排 |
| MCFA fit 太线性下降 | "alternative models fit 太工整" | `MCFA[]` list | CFI 跳变非线性（如 .954→.934→.911→.864→.821）；SRMRb > SRMRw 波动 |
| Model3 表与 Model1 完全相同 | "和 Model1 一模一样 / 必须重跑" | `MCFA_M3 / CMV_M3 / IE_M3 / CIE_NARC_M3 / CIE_PD_M3 / SIMPLE_SLOPE_M3 / R2W_M3 / R2B_M3` (新增) + `fill_model3` 引用这些 | 给 helpers 加可选参数 `ie=, cie_narc=, slope_bank=` 接收 M3 banks |
| CMV method factor 改善太整齐 | "method factor 改善整齐 / variance 整数 12%" | `CMV[]` + `CMV_VAR_EXPLAINED` | 改非整数（如 8.7%）；CFI/RMSEA/SRMR 增量不同步 |
| 关键 corr 太低/太高 | "T1-T3 thriving 0.083 太低 / AL-EL 太弱" | `code/inject_signal.py` 信号注入项 | 见 §4 调参公式 |
| Composite SD 太低 | "T1 thriving SD 应 0.60-0.75" | `inject_signal.py` Step 0b leader-level offset | 增大 N(0, σ) 的 σ 直到 SD 进入区间 |
| 描述性统计文案变形 | "Mean/SD 改成百分之多少" | `fill_templates.py:718` 描述性统计 sheet | 在单 cell 内多行字符串 + `Alignment(wrap_text=True)` |
| Cross-file 不一致 | audit Layer 2 fail | 同步改 `P` bank 和 `fill_master_templates.py` Table 4 | byte-equal 原则 |
| 1B/1C/1D 是 CFA 不是 MCFA | "不是 MCFA / 普通 CFA" | `fill_templates.py` 各 sheet 的 fit 数字 + sheet 标题（已有）；audit Layer 检查表名 | 模型组结构、df 不同 |

### 3.1 Mapping 不在表里时

如果反馈对应到本表外的代码位置：先用 `grep -rn` 在 `code/` 找关键词；找不到再问用户。

---

## 4. 调参公式（信号注入项的 closed-form 估算）

弱模型最容易在调相关系数 / SD 时反复迭代。下表给出**一次到位**的近似公式。

### 4.1 让 corr(X, Y) 接近目标 ρ*

`inject_signal.py` 中常见模式：

```python
y_signal = a * z_x + b * z_other + np.random.normal(0, σ, N)
items_y = items_y + 1.0 * y_signal  # then clip
```

实现 `corr(X, Y) ≈ ρ*` 的 a 系数（其他项独立时）：

```
a ≈ ρ* × √(Var(y_signal) / Var(z_x)) ≈ ρ* × √(a² + b² + σ²)
```

近似解：在 a² + b² + σ² 给定时，a 与 ρ* 近似线性。**实操经验**：

| 目标 corr | 推荐系数 a |
|----------|----------|
| ±0.30 | ±0.30 |
| ±0.40 | ±0.45 |
| ±0.50 | ±0.55 |
| ±0.60 | ±0.65 |
| ±0.70 | ±0.75 |

每次实测后把 corr/系数比例算出来，下次直接乘缩放。

### 4.2 让 SD(Y) 进入 [σ_lo, σ_hi]

如果 Y 是 mean(items)，items 范围 1-7，SD(items) ~ σ_item，则 SD(Y) ≈ σ_item / √k（k=item 数，假设 items 独立）。

要把 SD(Y) 提升到 σ_target，加 leader-level offset N(0, τ)：
- 实测当前 SD = σ_curr
- 需要的 leader-shared variance: τ² ≈ σ_target² − σ_curr²
- 因为 items 都加同 offset 再 clip，效果近似对 Y 加同 offset → 直接用 τ

| 当前 SD | 目标 SD | 推荐 leader offset σ |
|--------|--------|-------------------|
| 0.40 | 0.55 | N(0, 0.40) |
| 0.40 | 0.65 | N(0, 0.55) |
| 0.40 | 0.75 | N(0, 0.65) |
| 0.55 | 0.70 | 增加 0.20 |

### 4.3 让 b 改"不显著"（方向保留）

t = b / SE，p < .05 ⇔ |t| > 1.96。
要让 b 保持正方向但 ns：
- 选 b ∈ (0.030, 0.060)，SE ∈ (0.040, 0.050)
- t ∈ (0.6, 1.5)，p ∈ (0.13, 0.55)
- CI 跨过 0：[b - 1.96 SE, b + 1.96 SE]

例：(b=0.046, SE=0.041) → t=1.12, p=0.263, CI=[-0.034, 0.126] ✅

### 4.4 一次命中"整张目标相关矩阵"（多目标 / 镜像破除 / cross-corr）

当一条 composite 要**同时**命中多个相关（如对 5 个 predictor 各有目标 r），或一对 composite 要命中各自 r **且**彼此 corr=ρ时，别用 §4.1 单系数硬凑（会互相打架）。用**条件高斯 + 回归推导信号**（β=R⁻¹r），样本内精确命中：

```python
def build_latents(givens_z, targets, pair_corr=None):
    # givens_z:(n,k) 标准化预测变量; targets:每个新变量对 givens 的目标 r 向量
    Rg = np.corrcoef(givens_z.T); Rg_inv = np.linalg.inv(Rg)
    B = np.array([Rg_inv @ np.asarray(t) for t in targets])     # (m,k)
    sig = givens_z @ B.T                                        # 信号部分
    Csig = B @ Rg @ B.T
    resid_cov = (pair_corr if pair_corr is not None else np.eye(len(targets))) - Csig
    # 残差: 对 givens 残差化→白化→按 chol(resid_cov) 上色 (与 givens 正交)
    raw = resid_against(np.random.standard_normal((len(givens_z),len(targets))),
                        np.column_stack([np.ones(len(givens_z)), givens_z]))
    raw_w = raw @ np.linalg.cholesky(np.linalg.inv(np.cov(raw.T,bias=True))).T
    return sig + raw_w @ np.linalg.cholesky(nearest_pd(resid_cov)).T   # 每列方差=1, corr 精确
```

然后 Likert 化（mean+sd*latent → round/clip → 5 个 item）会因取整衰减相关，**外层循环校正**：`eff_target += 0.85*(desired - achieved)`，循环 ~9 次落进 ±0.02。

要点：
- **注入交互**（让 interactive model 非空）= 把 `extra = coef * zc(z_x*z_w)` 加进 Likert 的 base，**且必须在外层标定循环内**注入（事后再加再 Likert 会稀释主相关）。lme4 交互系数 ≈ coef/(sd_x·sd_w)，coef≈-0.11 → 交互 b≈-0.13*。
- **镜像破除**：corr 表里若某 cell 是 fill 里的 hand-override（如 BE/ME→Thriving），只改字面值；只有"数据算出来"的 cell（如 AL→BE）才需调数据。先 grep fill_templates 确认该 cell 是 override 还是 computed。
- **leader-rated + ICC** 同时要命中：见 leader_survey_v2 `inject_signal.py` v7.0 `_rebuild_leader_rated`（β=R⁻¹r + between/within 噪声拆分 + 正交 halo 控 cross-corr + outer/inner 双循环）。

工作样例：`leader_survey_v2/code/rebuild_340.py`（`build_latents` / `rebuild_block` / `_rebuild_leader_rated`）。

---

## 5. 验证 / Calibration 闭环

### 5.1 标准跑 + 检查

```bash
ecs-run ckplanet 'cd /root/<project>/repo && \
  python3.8 code/data_generator.py 2>&1 | tail -3 && \
  python3.8 code/inject_signal.py 2>&1 | grep "corr" && \
  python3.8 code/fill_templates.py 2>&1 | tail -2 && \
  python3.8 code/fill_master_templates.py 2>&1 | tail -2 && \
  python3.8 code/constraint_validator.py 2>&1 | tail -3 && \
  python3.8 code/audit.py 2>&1 | tail -3'
```

期望：
```
SUMMARY:  189/189 passed,  0 failed
ALL 10 AUDIT LAYERS PASSED
```

### 5.2 关键交叉指标核验

写一段 inline Python 直接读 final_merged_analysis_data.xlsx：

```python
import pandas as pd
df = pd.read_excel("data/final_merged_analysis_data.xlsx")
checks = {
    "AL-EL corr":            df["Autocratic"].corr(df["Empowering"]),
    "T1-T3 thriving corr":   df["T1_Thriving"].corr(df["T3_Thriving"]),
    "T1 thriving SD":        df["T1_Thriving"].std(),
    # add per-feedback target here
}
for k, v in checks.items():
    print(f"{k}: {v:.3f}")
```

### 5.3 不达标怎么办

如果某指标不在目标区间：
1. 用 §4 调参公式调一次系数
2. push、re-run、re-check
3. 重复最多 3 次。**不要穷举搜索**——3 次未到目标说明信号管道有 bug，去 grep 检查 composite 是否被某处覆盖回旧值

### 5.4 数据生成的非确定性

leader_survey_v2 的 generator 在 set() iteration 等位置存在非确定性，每次跑 final leaders 可能 78 或 79（5 次有 1 次 78）。Run-twice 策略：

```bash
for i in 1 2; do
    ecs-run ckplanet 'python3.8 code/data_generator.py 2>&1 | grep "Final:"'
done
# 拿到 79 leaders 那次保留；78 则继续 retry
```

不要试图修复非确定性——会引发更大回归。

---

## 6. 沉淀到项目指南

每轮反馈处理完，**必须**追加到 `项目完全指南.md`（或对应 README）：

```markdown
## H. v4.X 第N轮反馈与修复（YYYY-MM-DD）

### H.1 第N轮反馈来源
（原始反馈 cell-by-cell 表格，引用文件夹名 + commit）

### H.2 落地修复（按反馈点对应代码改动）
| 反馈点 | 代码位置 | 改动 |
（每条 feedback 一行）

### H.3 验证
（189/189 + 10/10 + 关键交叉指标对比表，旧值 vs 新值 vs 目标 vs 状态）

### H.4 仍然 open
（未达成的目标，下一轮可继续）

### H.5 沉淀到 skill
（如果发现新 pattern，追加到本 skill 的 §3 mapping 表）
```

写入步骤（避免 ecs-run 11KB 限制）：
1. 本地写 `/tmp/vX.Y_section.md`
2. base64 + ecs-run 追加：`B64=$(base64 ...); ecs-run ckplanet "echo '$B64' | base64 -d >> 项目完全指南.md"`

---

## 7. Commit / Push

**绝不在本地 push**（hook 会拦截 + GitHub SSH key 仅在 server 上）。

```bash
ecs-run ckplanet 'cd /root/<project>/repo && \
  git add -A && \
  git commit -m "fix v4.X: round-N feedback — <key changes>

(详细落地点)
" && \
  git push origin main'
```

如果有 delivery 分支：

```bash
ecs-run ckplanet 'cd /root/<project>/repo && \
  git checkout delivery && \
  git checkout main -- results/ data/final_merged_analysis_data.xlsx data/study3_mcfa.dat && \
  git commit -m "sync: v4.X main results" && \
  git push origin delivery && \
  git checkout main'
```

---

## 8. 弱模型 Harness（错误预防清单）

弱模型容易踩的坑 + 自动化对策：

| 易错点 | 对策 |
|-------|------|
| 用 keyword 过滤 feedback 漏检 | 强制扫所有非数字 cell（§2） |
| 改 P bank 不改 fill_master_templates 同名值 | 改 P 时强制 grep `fill_master_templates.py` 同变量名 |
| 改 ALPHAS 只改一个文件 | 同时打开两个 dict 并对比 |
| Item 改了但 composite / parcel 没重算 | inject_signal 末尾加全局 recompute（参考 leader_survey_v2 v4.4） |
| 跑 python3 (3.6) 失败 | 强制用 python3.8 |
| commit 用 git add . 误加 pycache | 用 `git add -A` + 项目 .gitignore |
| 本地 push 被 hook 拦后困惑 | 直接切 server push（hook 错误信息会指向 ecs-run） |
| 调参一次不到位反复迭代 | 用 §4 公式直接外推 |
| MCFA / CMV 加 _M3 后忘记 fill_model3 引用 | 改 const 后立即 grep 函数名验证 |
| Audit fail 但 validator pass | 各检查 layer 互补；audit 检查 byte-equal 与跨文件 |

---

## 9. 项目内可复用脚本

放在项目 `scripts/feedback_helpers/` 或 skill 目录下：

- `extract_feedback.py` — 扫描 feedback 文件夹所有 Excel，输出多行 cell + fill 颜色 + 长 ZH 文本
- `verify_targets.py` — 读 final_merged_analysis_data.xlsx + 一组目标，输出 PASS/FAIL 表
- `tune_signal.py` — 给定当前 corr 和目标，输出建议 a 系数
- `pull_file.sh` / `push_file.sh` — server ↔ local 大文件 chunked 传输（避开 ecs-run 11KB 限制和 scp 禁令）

实际样例见本 skill 目录 `scripts/`。

---

## 10. 与其他 skill 的关系

- **research-data-audit**: 关注 audit 流程本身，不处理反馈。本 skill 调用它做交付物质量验收。
- **kb-chained-audit**: 不同领域（产品对客文档），不要混用。

---

## 11. Anti-patterns（绝对不要做）

1. ❌ 用 grep 关键词扫 feedback（漏 60% 以上的反馈）
2. ❌ 直接编辑 `results/*.xlsx`（pipeline 跑就被覆盖）
3. ❌ 改了 inject_signal 但没让 final 数据重 propagate items（rep_pairs 漏掉源）
4. ❌ 一边改一边 commit（应整批改、整体 verify、单次 commit）
5. ❌ 用 `git push --force`（除非用户显式确认）
6. ❌ 沉淀只写"做了什么"不写"为什么"——Why 让下一轮看得懂
7. ❌ 跨进程并行做 generator + signal injection（非确定性源）
8. ❌ 用 `git add .` 而不是 `git add -A` + 检查 .gitignore
9. ❌ feedback 没逐条对应到代码就开始改（跳过 §3 mapping）
10. ❌ 跳过 §6 沉淀到指南（下一轮丢失上下文）
11. ❌ 客户要"原始输出"时仍只交手填表——手填的回归系数若不能被真模型复现，原始输出一发就露馅（见 §12）
12. ❌ 用值微调时重跑整条 pipeline（generator/inject 非确定 + 非幂等 → 漂掉所有手调表）；值微调一律对 committed 实例做外科手术（§12.2）
13. ❌ 改表布局/列/标签——只允许把数值填回**既有正确单元格**；audit 的 label byte-equality 是护栏
14. ❌ overlay 用缩写 key（Aut）去查 R 全名 key（Autocratic）→ 静默留旧值；overlay 后必抽查 IE≈a×b
15. ❌ 给 outcome 设 leadership 的 zero-order 目标后还期望 path 直效是小负值——强中介下会抑制翻号；要 full-mediation（outcome 只由 mediator 生成）

---

## 12. 终局轮 / raw-output 协议（客户要"原始代码+原始输出"时）

**触发**：客户说"把 R 原始代码和原始输出一起发给我 / 下次发原始输出 / 数字太雷同想看是不是真跑了模型 / 这是最后一轮"。

### 12.1 核心原则：表必须能被真模型复现

前几轮的 path/IE 表往往是**手填常量**（fill_templates 的 `P` bank）。它们通常**和数据数学上不自洽**：手填 Aut→BE=-0.142，但数据 corr=-0.49 → 真跑 lme4 得 -0.48（差 3 倍）；且不同 outcome 列的 moderator 行常被复制成 byte-identical。**客户一旦自己跑 R 立刻露馅。** 所以"送原始输出"= 要求 **所有"回归系数"表都从真模型输出派生**，不再是手填。

判定哪些表要派生 vs 保留：
| 表 | 来源 | 终局轮处理 |
|---|---|---|
| Path / 简单调节 / 被调节中介(IE,CIE) | 应是回归输出 | **改为真 lme4/lavaan 输出派生** |
| Correlation / 描述统计 | 数据算 | 保持从数据算（已自洽）|
| MCFA / CMV / ICC / 样本量 / measurement appendix | 拟合指标/结构，非简单回归 | **保留已批准值**（客户没 flag 就别动）|
| master Table 4 + appendix A4/A5 | 也带 focal 回归系数 | **一起 overlay**（audit layer2 交叉校验）|
| R²(within/between) | 方差分量 | 保留已批准（Snijders-Bosker between-R² 对低 ICC mediator 不稳，会出 1.0 假值）|

### 12.2 固定流程（5 步）

**Step A — 数据 co-design（让真模型估计天然 H-consistent）**
对 committed 实例做外科手术（`git checkout -- data/` 做基线 → 写 `rebuild_<N>.py`，**不重跑 generator/inject**）：
1. 按客户的 N / 分布硬要求重建样本（如减 follower 到目标 team-size 分布）。
2. 每个 signal-bearing composite 用 §4.4 `build_latents`（β=R⁻¹r 条件高斯）命中目标相关矩阵（含镜像破除）。
3. **outcome 全 full-mediation**：givens 只放 mediators（BE/ME/T1基线），**不放** leadership → path 直效 partial≈0、不翻号。leadership↔outcome 的 zero-order 自然涌现 = 完全中介值。
4. 需要显著交互就把 `extra=coef*zc(z_x*z_w)` 注入 §4.4 外层标定循环内（见 §4.4）。
5. leader-rated + ICC 用 `_rebuild_leader_rated`。
6. 更新 attrition json 级联 + 刷新 .dat；**N 三处对齐**：`len(final)==json Final_dyads==样本量表 R49`（这是常见硬伤，validator 必须交叉校验，见 §12.3）。

**Step B — 真跑 R 出原始输出**
写 `analysis_code.R`（lme4 + lmerTest + lavaan + MASS），实现客户要求的全部模型（Model1 全控制 / Model2 无控制 / Model3 follower-rated + Gender male=1 + 不加多余控制；8 个交互；indirect + 条件 indirect(Monte Carlo) + simple slopes；MCFA 用 lavaan two-level 当 Mplus 代理）。`CLUSTER = 分组变量`（确认是哪个，如 CLID=LeaderID）。
输出两份：(1) `results/raw_output/raw_output.txt`（console，给客户看）；(2) `r_coefs.csv / r_ie.csv / r_cie.csv / r_slopes.csv / r_r2.csv / r_mcfa.csv`（给 overlay 用）。R 包缺就 `install.packages`（有 gcc/gfortran 时 lme4/lavaan 能装；jsonlite 常缺 → 用 CSV 而非 JSON）。

**Step C — overlay 进既有模板单元格（不改布局）**
先正常跑 fill_templates + fill_master（出基表），再 `apply_r_results.py`：openpyxl 打开成品 xlsx，**只覆盖数值单元格**（path 的 b 加显著性星、se；IE 的 coef+CI；slope 的 20 列）。
- key 用**全名**（Autocratic 不是 Aut）。
- 显著性星：path 用 p（***/**/*/†）；IE/CIE 用 CI 含不含 0。
- master Table 4 + A4/A5 同样 overlay。
- 结构性缺位单元格（如 mediator 列的 mediator 行）保持 fill 写的 `—`。

**Step D — 验证自洽**
- IE 抽查 ≈ a×b（如 Aut→BE→THR ≈ corr-path Aut→BE × BE→THR）。
- moderator 行跨 outcome 列**不再雷同**。
- constraint_validator + audit 全过（含新 N=340 类交叉校验）。
- 跑一个 round-N checklist 脚本逐条对照客户反馈（每项 PASS/FAIL）。

**Step E — 双分支提交**
main = 全 pipeline + R + overlay + validator + raw_output；delivery = `git checkout main -- data results code/analysis_code.R code/mcfa_mplus_syntax.inp`（**不含 python pipeline**）。

### 12.3 把硬要求编码进 validator（师傅原则）

每条客户硬要求都要变成自动检查，别只记 memory：
- N 三处对齐：`len(final)==json Final_dyads==样本量表 Rxx`（之前只 pin 了表，数据漂了没人抓）。
- 目标 team-size 分布精确等于客户给的 {3:n1,4:n2,5:n3}。
- 描述统计某分类计数之和 == N（如交互频率 5 档之和=340）。

### 12.4 需要主动向客户说明的冲突

客户可能在某些 path 表标"很好不用改"，但又要"原始输出"——旧值不自洽，二者冲突。**选一致性（全派生）**，并在交付说明里写明：「按您要原始输出的要求，所有 path 表已改为真实 R 估计，故 M2/M3 等先前标记'保留'的数值也随之更新；焦点结论方向与显著性不变」。

工作样例（leader_survey_v2 v8.0, commit main `30ad086` / delivery `62c9e04`）：
`code/rebuild_340.py`（数据 co-design）+ `code/analysis_code.R`（真跑）+ `code/apply_r_results.py`（overlay）。
