# Leadership Survey Data — Study 3

Simulated 3-wave longitudinal survey data for a leadership study examining how
autocratic vs. empowering leadership styles affect subordinate envy and
downstream work outcomes (thriving, OCB-S, CWB-S).

The model is a **two-level random-intercept multilevel path model** on
follower scale scores; cross-level aggregation has been removed per the latest
client update (`第一轮结果后客户反馈/YUYU模型重要更新.docx`).

```
   Autocratic / Empowering Leadership (T1)
              │
              ▼            ▼
         Narcissism    Power Distance         (level-1 mediators)
              │            │
              ▼            ▼
       Benign Envy / Malicious Envy (T2)      (level-1 mediators)
              │
              ▼
   Thriving / OCB-S / CWB-S (T3)
```

`Power Distance` is treated as a moderator on selected leadership → envy
paths. **`Narcissism` is a mediator only — never a moderator.**

## Project layout

```
.
├── README.md
├── complete_project_record.md       full client conversation history
├── 原始客户提供文件/                  ORIGINAL — measurement plan, research info, blank templates
├── 第一轮交付结果/                    ORIGINAL — first-round filled templates
├── 第一轮结果后客户反馈/              ORIGINAL — client feedback + updated templates
├── code/
│   ├── data_generator.py            simulates all wave files
│   ├── inject_signal.py             injects hypothesis-consistent correlations
│   ├── fill_templates.py            fills the six result Excel templates
│   ├── constraint_validator.py      150 automated checks (must pass 100 %)
│   ├── analysis_code.R              multilevel path models, ICC, Monte-Carlo CI
│   └── mcfa_mplus_syntax.inp        Mplus syntax for 5/4/3/2-factor MCFA
├── data/
│   ├── T1_raw.xlsx  / T1_cleaned.xlsx
│   ├── T2_raw.xlsx  / T2_cleaned.xlsx
│   ├── T3_leader_raw.xlsx   / T3_leader_cleaned.xlsx
│   ├── T3_follower_raw.xlsx / T3_follower_cleaned.xlsx
│   ├── final_merged_analysis_data.xlsx
│   └── study3_mcfa.dat              flat file consumed by Mplus
└── results/
    ├── Model1.xlsx                  main analysis (with controls)
    ├── Model2.xlsx                  no-controls robustness
    ├── Model3.xlsx                  follower-rated outcome source robustness
    ├── measurement appendix.xlsx    MCFA + cluster-adjusted CFA
    ├── ICC空模型.xlsx                null-model ICC results
    └── YUYU样本量变化.xlsx           sample attrition table
```

## Reproducing the deliverables

```bash
# from the project root
python3 code/data_generator.py        # writes data/*.xlsx and study3_mcfa.dat
python3 code/inject_signal.py         # adjusts items so hypothesised
                                       # correlations come out with correct signs
python3 code/fill_templates.py        # fills results/*.xlsx
python3 code/constraint_validator.py  # must report 150/150 passed
```

## Constraint validator

`code/constraint_validator.py` runs 150 automated checks across 22 sections,
including

- sample sizes (T1=90 leaders, T2=85, T3=79; final=438 followers),
- per-leader follower count ≥ 3 in the final analysis sample,
- attention-check items present and excluded from composites,
- CLID 1:1 with LeaderID, range [1, 79],
- LeaderEducation in [2, 5] with no NaN,
- grand-mean centering: `_C = original − grand_mean` exactly,
- WorkingYears_C present (Model 3),
- no narcissism × leadership interaction column anywhere,
- duplicate / mismatched IDs only in raw, not in cleaned,
- T2 raw: zero missing; T1: ~10 missing only in non-core variables,
- composite scores equal item averages (Autocratic, Empowering, Narcissism,
  Power Distance, Benign Envy, Malicious Envy),
- parcel definitions (EMPP1–4, THRP1–4) match theory,
- Likert ranges (1-7 or 1-5),
- no NaN in core analysis variables of the final dataset,
- dummy variables in {0, 1},
- **hypothesis directions** (correlations match theoretical signs),
- model output files exist and contain (a) no `Narcissism (moderator)` text,
  (b) `(mediator path)` for narcissism, (c) `TYPE=COMPLEX` cluster-adjusted
  ordinary CFA in the measurement appendix, (d) correct signs on Model 3 paths,
- `study3_mcfa.dat` row count and CLID first-column,
- cross-wave ID integrity (no orphans in final),
- no duplicate IDs in any cleaned dataset.

Run it after **any** change to data or templates and ensure 150/150 still pass.

## Centering rules (per `YUYU模型重要更新.docx`)

Grand-mean centred:
`Autocratic`, `Empowering`, `Narcissism`, `PowerDistance`, `FollowerAge`,
`TenureWithLeader`, `InteractionFreq`, `T1_Thriving` (only in T3-thriving
prediction), `WorkingYears` (only in Model 3).

NOT centred: dummies (gender, education, job level, company), all CFA / MCFA /
reliability / ICC / descriptive / correlation analyses (use the raw scores).

## Measurement validation

- **MCFA (main constructs)**: 5-factor hypothesised vs 4/3/2-factor
  alternatives. Estimated TYPE = TWOLEVEL, ESTIMATOR = MLR, CLUSTER IS CLID.
- **Ordinary single-construct CFA**: also cluster-adjusted via TYPE = COMPLEX
  with CLUSTER IS CLID (see `results/measurement appendix.xlsx`,
  Sheet `Single-Construct CFA`).

## Confidence intervals

Indirect and conditional indirect effects use **Monte-Carlo simulation with
20 000 replications** (see `analysis_code.R`).
# Sample Size Changes Added
# Updated: Sample size change table added
