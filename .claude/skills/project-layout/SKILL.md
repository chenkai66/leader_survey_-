---
name: project-layout
description: 多项目标准化文件夹与分支组织。当开新项目（科研数据交付、合成数据生成、ML/数据-分析项目、咨询交付物等任何"有数据 + 有代码 + 有结果 + 有客户/评审反馈轮"的项目）时使用。给出统一的目录结构、分支策略（main 完整轨 + delivery 客户向轨 + wip/audit/archive 等细分）、命名约定、清单文件 (_manifest.json)、决策日志，以及一个 `scripts/scaffold.py` 自动建项目骨架。从 leader_survey_v2 + data-calibration + research-data-feedback-loop 的实践沉淀，避免每个新项目重新决定目录怎么放、分支怎么开、什么文件该放哪。配套：CLAUDE.md / README.md / .gitignore / run_pipeline.sh / decision_log.md 模板。
---

# project-layout — 多项目标准化组织

每个新项目都按这套结构起家。**核心思想**：内部完整状态在 `main`，客户/评审只看 `delivery`；声明式 spec 驱动生成；feedback 一轮一文件夹；决策记入 `decision_log.md`。

---

## 0. Trigger

任何"开新项目"或"重组现有项目"：科研数据交付、合成数据生成、ML/数据分析项目、咨询交付物、需要反复迭代客户反馈的项目。

---

## 1. 标准目录结构

```
<project>/
├── README.md                    项目概述、入口、交付物说明
├── CLAUDE.md                    AI 助手上下文（workspace → server → tool 映射、约定）
├── .gitignore
├── .claude/skills/              本项目专用的 vendor skill（可选；通用 skill 留全局）
│
├── data/
│   ├── raw/                     原始未处理数据
│   ├── interim/                 清洗中间态
│   ├── cleaned/                 分析就绪数据
│   ├── final/                   规范的分析数据集（最终用于结果的版本）
│   └── _manifest.json           元数据：N、列、来源、生成时间、checksum
│
├── specs/                       声明式规格（驱动生成 + 校验）
│   ├── data_spec.json           数据生成 spec（喂给 calibrate.generate_from_spec）
│   ├── targets.json             目标值（相关阵、ICC、效应量等）
│   ├── constraints.json         业务规则（用于 enforce_constraints / check_*）
│   └── schema.json              列定义（dtype/range/允许值）
│
├── code/
│   ├── pipeline/                数据生成/转换/清洗（按序号命名顺序）
│   │   ├── 01_generate.py
│   │   ├── 02_clean.py
│   │   ├── 03_inject_signal.py
│   │   └── 04_propagate.py
│   ├── analysis/                统计分析（R / Python / Mplus）
│   │   ├── analysis.R
│   │   └── mcfa.inp
│   ├── fillers/                 模板填充（Excel 交付物）
│   ├── validators/              约束 + audit
│   │   ├── constraint_check.py
│   │   └── audit.py
│   └── lib/                     共享 util
│
├── results/                     最终交付物
│   ├── tables/                  填好的表
│   ├── figures/
│   ├── raw_output/              原始 R/Mplus/模型输出
│   └── _manifest.json           交付物清单 + 生成方式 + checksum
│
├── feedback/                    客户反馈（每轮一文件夹，时间倒序）
│   ├── round_1/
│   │   ├── annotations.md       从原文件提取的所有反馈条
│   │   ├── changes.md           本轮做了什么 / 没做什么 + 理由
│   │   └── original/            客户给的原文件副本
│   ├── round_2/
│   └── ...
│
├── docs/
│   ├── methodology.md           方法论：怎么造的、为什么
│   ├── decision_log.md          决策日志（关键决策 + 当时的取舍）
│   └── changelog.md             版本变化（vX.Y → 改了什么）
│
├── scripts/                     运维入口
│   ├── run_pipeline.sh          一键跑全 pipeline
│   ├── run_analysis.sh          只跑分析
│   ├── validate.sh              跑校验
│   ├── deploy.sh                推服务器/部署
│   └── sync.sh                  与远端同步
│
└── tests/                       项目级测试
    ├── test_data_integrity.py   数据完整性（行数、列、缺失）
    ├── test_constraints.py      约束（外键、聚合、时序、值域）
    └── test_analyses.py         分析结果合理性
```

---

## 2. 分支策略

| 分支 | 内容 | 谁看 |
|---|---|---|
| `main` | **完整源**：全部 pipeline + 代码 + data + results + feedback + tests + docs | 内部团队 |
| `delivery` | **客户向轨**：仅 data + analysis 代码 + results + raw_output + README，**不含**内部 pipeline / 反馈历史 / 决策日志 | 客户 / 评审 |
| `wip/<feature>` | 进行中的功能/重构（合并到 main 后删） | 内部 |
| `audit/round-<N>` | 第 N 轮反馈结束后的快照（可选；用于 reviewer 比较） | 内部 / 评审 |
| `archive/v<X.Y>` | 阶段性 tag（重大版本结束后冻结） | 历史 |
| `experiment/<name>` | 临时实验（成功 → 合 main；失败 → 留底或删） | 内部 |

**生命周期**：
- 开新项目 → `main` (init) → `delivery` (orphan branch, 第一次交付时建)
- 大改动 → `wip/<feature>` → 合 `main` → 同步选定文件到 `delivery`
- 客户反馈 → 在 `main` 处理 → 完成后同步 `delivery` 并打 `audit/round-N`
- 阶段交付 → tag `archive/v<X.Y>`

**delivery 同步规则**（在 main 处理完一轮反馈后）：
```bash
git checkout delivery
git checkout main -- data results code/analysis docs/README.md  # 只同步客户要的
git commit -m "sync: round-N delivery"
git push origin delivery
git checkout main
```

---

## 3. 关键文件规范

### 3.1 `data/_manifest.json`
```json
{
  "N": 340,
  "leaders": 79,
  "generated_at": "2026-06-01T12:34:56",
  "generator": "code/pipeline/03_inject_signal.py v7.0",
  "files": {
    "final_merged_analysis_data.xlsx": {"rows": 340, "cols": 138, "sha256": "..."}
  },
  "targets_hit": {"correlations": "spec/targets.json", "icc": 0.275}
}
```

### 3.2 `specs/data_spec.json`（声明式生成 spec）
配合 `data-calibration` skill 的 `generate_from_spec`：
```json
{
  "n": 340,
  "columns": [
    {"name": "age", "dist": "truncnormal", "mean": 40, "sd": 10, "lo": 18, "hi": 80},
    {"name": "income", "dist": "lognormal", "mu": 10, "sigma": 0.5}
  ],
  "correlations": {"['age','income']": 0.4},
  "constraints": [
    {"type": "range", "col": "age", "lo": 18, "hi": 80}
  ]
}
```

### 3.3 `feedback/round_N/changes.md`
每轮必写（**为什么这样改 + 怎么验证**）：
```markdown
# Round 3 changes (2026-05-30)

## Done
- [client.xlsx | Model1 | A18] mirror-break: AL→BE −0.521→−0.489
  - Why: 客户觉得 AL-EL/BE-ME 太镜像对称
  - How verified: data corr now = -0.487 (target -0.489)
- ...

## Deferred / not done
- [client.xlsx | Path | A29] 数字太相似 → 留到下一轮和"raw output"一起改
  - Why: 改 path 表会破坏 4 轮已通过的 path 数值；要先送原始输出让客户判断

## Open
- (none)
```

### 3.4 `docs/decision_log.md`
关键决策 + 当时取舍（避免下次回头不知道为什么这么决定）：
```markdown
## 2026-05-31: Path 表全部改为从 R 真跑派生（不再 hand-coded）
**Context**: 客户要原始代码+原始输出，hand-coded path 数字（-0.142）和数据真跑（-0.48）3 倍偏。
**Options**:
  A. 保留 hand-coded path + 送 raw output（客户会看出 3 倍偏差）
  B. 调数据使真跑 = hand-coded（强中介下不可能）
  C. ⭐ 接受真跑值改交付表
**Decision**: C，理由：客户主导诉求是一致性；改 path 比改方法或欺骗都好
**Risk**: 4 轮已通过的 path 数会变；M2/M3 path"很好不用改"的注释也违反
**Mitigation**: 在交付说明明示"已切换为真模型派生，保留焦点结论"
```

---

## 4. 命名约定

- **目录**：snake_case 单数（`code/`、`data/`、`feedback/`）
- **Python 文件**：snake_case（`run_pipeline.py`、`constraint_check.py`）
- **R/Mplus 文件**：snake_case，`.R` / `.inp`
- **Pipeline 脚本**：数字前缀表顺序（`01_generate.py`、`02_clean.py`）
- **Specs / configs**：`<purpose>_spec.json` 或 `<thing>_targets.json`
- **Validators**：`check_<aspect>.py` 或 `validate_<thing>.py`
- **Feedback 文件夹**：`round_<N>/`（N 单调递增；保留原文件副本进 `original/`）
- **Tags**：`v<major>.<minor>.<patch>`，配合 `archive/v<X.Y>` 分支
- **测试**：`test_<module>.py`，与被测代码同结构

---

## 5. CLAUDE.md（每项目根目录的 AI 助手入口）

模板见 `templates/CLAUDE.md.template`。最少含：
- 项目简介 + 当前阶段
- 服务器 / 部署目标（如 leader_survey 用 `ecs-run ckplanet`）
- 主要文件位置（哪里是 pipeline、哪里是 specs、哪里是 feedback）
- 关键约定（"feedback 进 feedback/round_N/"、"决策记 docs/decision_log.md"）
- 当前的 main 与 delivery 分支状态

---

## 6. 用 scaffold.py 一键起新项目

```bash
python ~/.claude/skills/project-layout/scripts/scaffold.py <project_path> [--name NAME]
```
会创建上面的完整目录结构 + 默认模板文件（.gitignore / README / CLAUDE.md / run_pipeline.sh / .gitkeep）+ git init + 提示下一步。

```bash
# 例：
python ~/.claude/skills/project-layout/scripts/scaffold.py ~/Desktop/Project/my_new_study
cd ~/Desktop/Project/my_new_study
# 编辑 README.md / CLAUDE.md / specs/data_spec.json
# 把数据放进 data/raw/
# 写 code/pipeline/01_*.py
git add -A && git commit -m "init"
```

---

## 7. 配合其他 skill

| 场景 | 用什么 |
|---|---|
| 数据生成/标定 | `data-calibration`（`generate_from_spec` + `validate`） |
| 客户反馈迭代 | `research-data-feedback-loop`（专门）或 `deliverable-feedback-loop`（通用） |
| 服务器同步 | 项目自带 `scripts/sync.sh`（首次按本 skill 模板生成） |

---

## 8. Anti-patterns

1. ❌ 数据和代码混在一个目录（→ 拆 `data/` 和 `code/`）
2. ❌ feedback 直接覆盖原文件（→ 留 `feedback/round_N/original/` 副本）
3. ❌ 决策只存于"对话记忆"（→ 写 `docs/decision_log.md`）
4. ❌ delivery 分支带内部生成 pipeline（客户看到"造数代码"会问"为什么这么巧"）
5. ❌ 不写 `_manifest.json`（下次回看不知道 results/ 里的表是怎么来的）
6. ❌ 一个项目里多种命名风格混用
7. ❌ `main` 直推到客户（→ 始终走 `delivery` 同步）
8. ❌ 改一轮反馈直接覆盖上一轮的代码而不记 changes.md
