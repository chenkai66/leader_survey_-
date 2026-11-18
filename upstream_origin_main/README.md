# Leadership Survey — Study 3 (Final Deliverables)

Simulated 3-wave longitudinal leadership-survey dataset and accompanying
analysis artefacts for the autocratic / empowering leadership → envy →
work-outcomes study.

## Theoretical model

```
   Autocratic / Empowering Leadership  (T1, follower-rated)
                │
                ▼            ▼
           Narcissism    Power Distance        (level-1 mediators)
                │            │
                ▼            ▼
       Benign Envy / Malicious Envy  (T2, follower-rated)
                │
                ▼
   Thriving (T1 + T3)  +  OCB-S / CWB-S  (T3)
```

* `Power Distance` acts as a moderator on selected leadership → envy paths.
* `Narcissism` is a mediator only — not a moderator.
* Outcomes at T3 are leader-rated in the main analysis; a robustness
  supplement (Model 3) uses follower-rated OCB-S / CWB-S.

## What is in this branch

```
.
├── README.md                          this file
├── code/
│   ├── analysis_code.R                multilevel path models, ICC,
│   │                                  Monte-Carlo CI for indirect &
│   │                                  conditional indirect effects
│   └── mcfa_mplus_syntax.inp          Mplus syntax for nested
│                                      multilevel CFA (5/4/3/2-factor)
├── data/
│   ├── T1_raw.xlsx / T1_cleaned.xlsx
│   ├── T2_raw.xlsx / T2_cleaned.xlsx
│   ├── T3_leader_raw.xlsx   / T3_leader_cleaned.xlsx
│   ├── T3_follower_raw.xlsx / T3_follower_cleaned.xlsx
│   ├── final_merged_analysis_data.xlsx     final analytic sample (361 dyads × 79 leaders)
│   ├── study3_mcfa.dat                     flat ASCII Mplus input
│   └── _attrition_summary.json             attrition counts wave-by-wave
└── results/
    ├── Model1.xlsx                    main analysis (with controls)
    ├── Model2.xlsx                    no-controls robustness
    ├── Model3.xlsx                    follower-rated outcome supplement
    ├── measurement appendix.xlsx     MCFA + cluster-adjusted CFA
    ├── ICC空模型.xlsx                 null-model ICC results
    ├── 主模型结果填答表.xlsx          main results template (filled)
    ├── study3附录结果填答.xlsx        appendix template (filled)
    └── 样本量变化表.xlsx              sample attrition table
```

## Final sample

| Wave | Leaders | Followers | Notes |
|------|---------|-----------|-------|
| T1   | 90      | 436       | Baseline leadership + thriving |
| T2   | 85      | 401       | Envy (≈2 weeks after T1) |
| T3 (leader) | 79 | —      | Leader-rated OCB-S / CWB-S |
| T3 (follower) | 79 | 361   | Follower self-thriving + OCB-S / CWB-S |
| **Final analytic** | **79** | **361** | **per-leader ≥ 3, avg 4.57** |

Wave-by-wave attrition counts are in `data/_attrition_summary.json`
and the audit-grade `样本量变化表.xlsx`.

## Reproducing the published analyses

The deliverables in `results/` were produced by:

1. `code/analysis_code.R` — fits the multilevel path model
   (`lavaan::sem` with cluster argument), computes ICC, runs the
   Monte-Carlo confidence intervals for indirect and conditional
   indirect effects, exports tables.
2. `code/mcfa_mplus_syntax.inp` — Mplus syntax for the nested MCFA
   reported in `measurement appendix.xlsx` (Table 1A).

Both scripts read directly from the `data/` directory; no preprocessing
is required.

```R
# from project root
setwd("path/to/this/folder")
source("code/analysis_code.R")
```

## File-naming conventions

* `_raw.xlsx` files contain every submitted response, including those
  later excluded by attention-check / duplicate / response-time filters.
* `_cleaned.xlsx` files contain the post-screening rows used in the
  reported analyses. The exclusion log is summarised in
  `_attrition_summary.json`.
* `final_merged_analysis_data.xlsx` is the joined wide-format file with
  one row per follower (T1+T2+T3 measures plus controls), filtered to
  leaders with ≥3 follower responses.
* `study3_mcfa.dat` is the flat-ASCII version of the cleaned data, in
  the column order required by `mcfa_mplus_syntax.inp`.

## Notes on the data

* All Likert responses are integer-valued on a 1-7 scale.
* Reverse-coded items: `R_THR5` (paired with `THR5`) and `R_THR10`
  (paired with `THR10`); composites use the recoded versions.
* `Thriving` composite is the mean of 10 items (5 learning + 5
  vitality); 4 item-parcels (`THRP1`-`THRP4`) follow the YUYU spec
  layout for the measurement appendix CFAs.
* Leader-level identifiers (`LeaderID`) match across waves and are
  retained in the cluster column (`CLID`, 1-to-1 with `LeaderID`,
  range [1, 79]).
