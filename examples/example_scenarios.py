"""Common real-world scenarios — A/B test, causal inference, time/panel, survival,
sequences, classification benchmark, mimic real data, mixed-type survey.
Run: python examples/example_scenarios.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import numpy as np, pandas as pd, calibrate as C
rng = np.random.default_rng(42)

print("== A/B test power (continuous, MDE=0.2, sd=1) ==")
hits = 0
for _ in range(200):
    ab = C.ab_test_data(500, baseline=0, effect=0.2, sd=1.0, rng=rng)
    a = ab[ab.arm == "control"].y; b = ab[ab.arm == "treatment"].y
    se = np.sqrt(a.var()/len(a) + b.var()/len(b))
    if abs(b.mean() - a.mean()) / se > 1.96: hits += 1
print(f"  empirical power at n=500/arm = {hits/200:.2%}")

print("== Causal inference: confounded observational study, then adjust ==")
df = C.dag_sample(5000, [
    ("U",     lambda d, n, r: r.standard_normal(n)),                                       # confounder
    ("treat", lambda d, n, r: (1 / (1 + np.exp(-0.8 * d["U"])) > r.random(n)).astype(int)),# propensity
    ("Y",     lambda d, n, r: 0.5 * d["treat"] + 0.6 * d["U"] + r.standard_normal(n)),
])
t = df["treat"].values; y = df["Y"].values; u = df["U"].values
naive = y[t == 1].mean() - y[t == 0].mean()
prop = 1 / (1 + np.exp(-0.8 * u))
w = C.ipw_weights(t, prop)
ipw = ((y * t * w).sum() / (t * w).sum()
       - (y * (1 - t) * w).sum() / ((1 - t) * w).sum())
print(f"  true ATE=0.50  naive={naive:.3f} (biased by U)  IPW={ipw:.3f}")

print("== Panel data: 100 firms × 12 quarters, ICC=0.25, AR1=0.5 ==")
pd_ = C.panel_data(100, 12, icc=0.25, ar1=0.5, time_trend=0.05, rng=rng)
print(f"  rows={len(pd_)} unique firms={pd_.unit.nunique()} y mean over time monotone? "
      f"{(pd_.groupby('time').y.mean().diff().dropna() > 0).sum()}/11 up-steps")

print("== Survival: HR=2 for treated, 30% censoring ==")
trt = (rng.random(3000) < 0.5).astype(float).reshape(-1, 1)
s = C.survival_data(3000, baseline_rate=0.1, hazard_ratios=[2.0], X=trt,
                    censor_rate=0.05, rng=rng)
mt0 = np.median(s[(s.event == 1) & (s.x1 == 0)].time)
mt1 = np.median(s[(s.event == 1) & (s.x1 == 1)].time)
print(f"  median event time: control={mt0:.2f}  treated={mt1:.2f}  ratio~{mt0/mt1:.2f} (HR=2 → ~2)")

print("== Markov sequences: simulate user clickstream then re-estimate ==")
P = np.array([[0.6, 0.3, 0.1], [0.2, 0.5, 0.3], [0.4, 0.2, 0.4]])
seq = C.markov_chain(15000, P, states=["home", "browse", "buy"], rng=rng)
Phat, _ = C.fit_markov(seq, states=["home", "browse", "buy"])
print(f"  max |P_hat - P| = {np.max(np.abs(Phat - P)):.3f}")

print("== Classification benchmark: 4 features, target AUC=0.85, 20% positives ==")
cd = C.classification_dataset(5000, n_features=4, target_auc=0.85, class_balance=0.2, rng=rng)
from numpy.linalg import lstsq
W = lstsq(np.column_stack([np.ones(len(cd))] + [cd[f"x{i+1}"].values.reshape(-1, 1) for i in range(4)]), cd.y.values, rcond=None)[0]
p = cd[[f"x{i+1}" for i in range(4)]].values @ W[1:] + W[0]
o = np.argsort(p); ys = cd.y.values[o]; np_ = ys.sum(); nn = len(ys) - np_
auc = (np.arange(1, len(ys) + 1)[ys == 1].sum() - np_ * (np_ + 1) / 2) / (np_ * nn)
print(f"  pos prop={cd.y.mean():.2f}  achievable AUC={auc:.3f}")

print("== Mimic real dataset + measure realism ==")
ref = pd.DataFrame({"income": rng.lognormal(10, 0.6, 2000), "age": rng.integers(22, 65, 2000)})
ref["spend"] = 0.0001 * ref.income + 5 * rng.standard_normal(2000)
syn = C.fit_from_reference(ref, rng=rng)(2000)
auc_real_vs_syn = C.discriminability(ref, syn)
print(f"  fit-from-ref → discriminability AUC = {auc_real_vs_syn:.3f} (close to .50 = realistic)")

print("== Mixed survey: continuous + binary + ordinal, target correlations ==")
mc = C.mixed_copula(2000, [
    dict(name="income",   type="continuous", ppf=lambda q: 30000 * np.exp(C._phi_inv(q))),
    dict(name="employed", type="binary",     p=0.75),
    dict(name="edu_lvl",  type="ordinal",    cuts=[0.25, 0.55, 0.85])],
    target_corr=[[1, 0.4, 0.5], [0.4, 1, 0.3], [0.5, 0.3, 1]], rng=rng)
print(f"  income mean={mc.income.mean():.0f}  employed prop={mc.employed.mean():.2f}  "
      f"edu distribution={dict(mc.edu_lvl.value_counts().sort_index())}")
print(f"  spearman(income, edu_lvl) = {np.corrcoef(C._ranks(mc.income), C._ranks(mc.edu_lvl))[0,1]:.3f} (target .50)")
