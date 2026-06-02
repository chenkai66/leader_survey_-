"""Quickstart — 5 most common use cases in one runnable script.
Run: python examples/quickstart.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import numpy as np, pandas as pd
import calibrate as C

print("=" * 60)
print("data-calibration QUICKSTART (5 common patterns)")
print("=" * 60)

# ----- 1. Discover what's available -----
print("\n[1] Discover: 11 categories, %d functions" % len(C.list_functions()))
print("    e.g.  calibrate.list_functions('regression') / help / recipes")

# ----- 2. Declarative generation from spec (easiest entry point) -----
print("\n[2] generate_from_spec — declarative, validates marginals + corr + constraints")
spec = {"n": 2000,
        "columns": [{"name": "age",    "dist": "truncnormal", "mean": 40, "sd": 10, "lo": 18, "hi": 80},
                    {"name": "income", "dist": "lognormal",   "mu": 10,   "sigma": 0.5},
                    {"name": "spend",  "dist": "normal",      "mean": 50, "sd": 15}],
        "correlations": {("age", "income"): 0.4, ("income", "spend"): 0.6},
        "constraints":  [{"type": "range", "col": "age", "lo": 18, "hi": 80}]}
df = C.generate_from_spec(spec, rng=np.random.default_rng(0))
report = C.validate(df, spec)
print(f"    generated {len(df)} rows; {report['summary']}")
for line in report["correlation"]: print(f"      corr {line[0]}-{line[1]}: target {line[2]}, achieved {line[3]} ({'✓' if line[4] else '✗'})")

# ----- 3. Standard regression dataset with target R² -----
print("\n[3] regression_dataset — linear regression with target R²")
df_r = C.regression_dataset(2000, coefs=[0.5, -0.3, 0.2], intercept=1.0, target_r2=0.5,
                            rng=np.random.default_rng(1))
from numpy.linalg import lstsq
b = lstsq(np.column_stack([np.ones(2000), df_r[["x1","x2","x3"]].values]), df_r.y.values, rcond=None)[0]
print(f"    target b=[0.5, -0.3, 0.2], recovered b={np.round(b[1:], 3).tolist()}; intercept={b[0]:.2f}")

# ----- 4. Causal inference with confounding (DAG / SCM) -----
print("\n[4] dag_sample — SCM with hidden confounder; IV / matching / DiD tests")
dfc = C.dag_sample(5000, [
    ("U",     lambda d, n, r: r.standard_normal(n)),                                          # unobserved confounder
    ("treat", lambda d, n, r: (1 / (1 + np.exp(-0.8 * d["U"])) > r.random(n)).astype(int)),
    ("Y",     lambda d, n, r: 0.5 * d["treat"] + 0.6 * d["U"] + r.standard_normal(n))])
t, y, u = dfc["treat"].values, dfc["Y"].values, dfc["U"].values
naive = y[t == 1].mean() - y[t == 0].mean()
prop  = 1 / (1 + np.exp(-0.8 * u))
w     = C.ipw_weights(t, prop)
ipw = ((y * t * w).sum() / (t * w).sum() - (y * (1 - t) * w).sum() / ((1 - t) * w).sum())
print(f"    true ATE=0.50; naive (biased)={naive:.3f}; IPW={ipw:.3f}")

# ----- 5. Synthetic data mimicking a real dataset -----
print("\n[5] fit_from_reference + discriminability — synthesize 'looks like real' data")
real = pd.DataFrame({"a": np.random.default_rng(2).lognormal(0, 1, 2000),
                     "b": np.random.default_rng(3).gamma(2, 2, 2000)})
real["c"] = 0.4 * real.a + np.random.default_rng(4).standard_normal(2000)
sampler = C.fit_from_reference(real, rng=np.random.default_rng(5))
synth = sampler(2000)
auc = C.discriminability(real, synth)
print(f"    discriminability AUC = {auc:.3f}  (~0.50 = indistinguishable)")

print("\n" + "=" * 60)
print("Next steps:")
print("  - SKILL.md   →  routing to 11 modules/*.md by goal type")
print("  - python -m calibrate help <function>   →  any function's docs")
print("  - python -m calibrate recipes           →  15 ready-to-run patterns")
print("  - python -m calibrate generate spec.json out.csv  →  CLI generation")
print("=" * 60)
