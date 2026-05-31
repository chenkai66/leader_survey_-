# data-calibration

A small, dependency-light toolkit + methodology for **adjusting a dataset to hit
specified statistical targets** while keeping it internally consistent and
reproducible. Domain-agnostic: works for simulation studies, synthetic/test data,
teaching & power-analysis datasets, statistics-preserving anonymization, fitting &
re-sampling real data, and research-data delivery.

- `calibrate.py` — the toolkit (numpy + Python stdlib only; **no scipy**).
- `SKILL.md` — the methodology: how to pick a method per target type, the robust
  fallback, feasibility/conflict/ordering, and a "fabrication tells" self-check.
- `examples/` — runnable scenario scripts.
- `tests/` — assertions that achieved ≈ target for every method.

## Why

Two recurring failures this toolkit prevents:
1. **"Displayed ≠ computed."** Hand-writing a statistic into a report that the raw
   data cannot reproduce. Anyone who re-runs the analysis catches it. Here every
   target is induced in the data and re-measured.
2. **Wrong method for the marginal.** Inducing Pearson correlation with a
   normal-based trick on skewed data distorts the marginals. Use distribution-free
   (Iman-Conover) or copula / Vale-Maurelli instead.

## Install

```bash
pip install numpy pandas        # pandas only for the DataFrame helpers
cp calibrate.py your_project/   # or add this dir to PYTHONPATH
```

## Quickstart

```python
import numpy as np, pandas as pd, calibrate as C
rng = np.random.default_rng(0)

# 1) Distribution-free: make existing columns correlate, marginals untouched
X = np.column_stack([rng.lognormal(0,1,2000), rng.uniform(0,10,2000)])
X = C.iman_conover(X, [[1,0.6],[0.6,1]], rng=rng)        # Spearman ≈ 0.6, marginals exact

# 2) Multivariate non-normal with target Pearson + skew/kurtosis (Vale-Maurelli)
Z = C.nonnormal_data(2000, [[1,0.5],[0.5,1]], skews=[1.0,-0.5], kurts=[2.0,1.0], rng=rng)

# 3) Hit ANY measurable target with the universal calibrator
a = C.tune_scalar(lambda a: np.corrcoef(z0, a*z0+e)[0,1], target=0.7, x0=1.0)

# 4) Survey / factor structure
items = C.factor_model_sample(2000, loadings=[[.7,0],[.75,0],[.8,0],[0,.7],[0,.75],[0,.8]],
                              factor_corr=[[1,.4],[.4,1]], rng=rng)

# 5) Mimic a real dataset (augment / de-identify / test)
sampler = C.fit_from_reference(real_df); synthetic = sampler(5000)
```

## Method index (target → function)

| Target | Function |
|---|---|
| mean / sd / range | `rescale` |
| any marginal distribution / match a reference | `match_marginal` |
| exact skewness + kurtosis | `fleishman` |
| Pearson corr to predictors (near-normal) | `build_latents` |
| correlation, **marginals preserved** (rank/Spearman) | `iman_conover` |
| given marginals + given correlation | `gaussian_copula` |
| multivariate non-normal + target Pearson | `nonnormal_data` (Vale-Maurelli) |
| factor / CFA structure → items | `factor_model_sample` |
| regression b / R² / logistic OR / AUC / prevalence | `tune_scalar` (+ structural eqs) |
| group effect size Cohen's d | `shift_group_effect` |
| mediation / interaction / multilevel ICC / Likert α | `rebuild_block`, `icc_rebuild`, `likertize` |
| target missingness (MCAR/MAR/MNAR) | `inject_missing` |
| target outlier rate | `inject_outliers` |
| reweight to population margins (raking/IPF) | `rake` |
| ε-differential-privacy noise | `dp_noise` |
| mimic a real dataset | `fit_from_reference` |
| diagnostics / goodness-of-fit | `report`, `ks_stat`, `verify` |
| **anything with no closed form** | `tune_scalar` (measure → adjust → repeat) |

See `SKILL.md` for the full methodology, feasibility/ordering rules, and the
self-check for detectable fabrication.

## Tests

```bash
python tests/test_calibrate.py     # asserts achieved ≈ target for every method
```

## License / provenance

Generalized from a multi-round research-data delivery project. Use freely.
