"""Hit model-implied targets: regression coef, group effect, factor structure,
and the universal fallback. Run: python examples/example_model_targets.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import numpy as np, pandas as pd, calibrate as C
rng = np.random.default_rng(1)
n = 4000

print("== Regression: set partial coefficients directly (structural equation) ==")
x1, x2 = rng.standard_normal(n), rng.standard_normal(n)
y = 0.4 * x1 - 0.25 * x2 + rng.standard_normal(n) * 0.8     # b1=0.4, b2=-0.25
b = np.linalg.lstsq(np.column_stack([np.ones(n), x1, x2]), y, rcond=None)[0]
print(f"  recovered b1={b[1]:.3f} (set 0.40), b2={b[2]:.3f} (set -0.25)")

print("== Group effect size: hit Cohen's d ==")
g = rng.integers(0, 3, n); v = rng.standard_normal(n) * 2 + 5
v = C.shift_group_effect(v, g, target_d=0.6, ref_group=0)
pooled = np.sqrt(np.mean([v[g == k].var(ddof=1) for k in range(3)]))
print(f"  d(group1 vs 0) = {(v[g==1].mean()-v[g==0].mean())/pooled:.3f} (target 0.6)")

print("== Factor / CFA structure -> items with target loadings & reliability ==")
Lam = [[.72, 0], [.68, 0], [.80, 0], [0, .75], [0, .70], [0, .82]]
items = C.factor_model_sample(n, Lam, factor_corr=[[1, .35], [.35, 1]], rng=rng)
print(f"  alpha factor1={C.cronbach_alpha(items[:,:3]):.2f}  factor2={C.cronbach_alpha(items[:,3:]):.2f}")
print(f"  factor-score corr={np.corrcoef(items[:,:3].mean(1), items[:,3:].mean(1))[0,1]:.3f} (target .35)")

print("== Universal fallback: hit ANY measurable target (here logistic prevalence) ==")
z = rng.standard_normal(n)
b0 = C.tune_scalar(lambda b0: (1 / (1 + np.exp(-(b0 + 0.8 * z)))).mean(), target=0.20, x0=0.0)
p = 1 / (1 + np.exp(-(b0 + 0.8 * z))); yb = (rng.random(n) < p).astype(int)
print(f"  intercept={b0:.3f} -> outcome prevalence={yb.mean():.3f} (target 0.20)")
