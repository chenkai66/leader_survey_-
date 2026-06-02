"""Self-tests: assert achieved ≈ target for every method. Run: python tests/test_calibrate.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import numpy as np, pandas as pd
import calibrate as C

rng = np.random.default_rng(7)
n = 4000
PASS = []


def chk(name, cond, detail=""):
    PASS.append(bool(cond))
    print(f"  [{'PASS' if cond else '**FAIL**'}] {name} {detail}")


# build_latents: exact in-sample corr to predictors + pair corr
z1 = C.zscale(rng.standard_normal(n))
z2 = C.zscale(-0.34 * z1 + np.sqrt(1 - 0.34**2) * C.zscale(rng.standard_normal(n)))
L = C.build_latents(np.column_stack([z1, z2]), [[-0.5, 0.5], [0.4, -0.4]],
                    pair_corr=[[1, -0.3], [-0.3, 1]], rng=rng)
chk("build_latents corr(L0,z1)≈-0.5", abs(np.corrcoef(L[:, 0], z1)[0, 1] + 0.5) < 0.02)
chk("build_latents pair≈-0.3", abs(np.corrcoef(L[:, 0], L[:, 1])[0, 1] + 0.3) < 0.02)

# rebuild_block: Likert composites hit targets (within sampling noise)
df = pd.DataFrame({"X1": 4 + 0.9 * z1, "X2": 5 + 1.0 * z2})
C.rebuild_block(df, ["X1", "X2"],
                specs=[dict(items=[f"A{i}" for i in range(1, 6)], comp="Y1", mean=4.5, sd=1.2, tgt=[-0.49, 0.52]),
                       dict(items=[f"B{i}" for i in range(1, 6)], comp="Y2", mean=3.1, sd=1.2, tgt=[0.54, -0.46])],
                pair_corr=[[1, -0.43], [-0.43, 1]], item_sigma=0.66, outer=12, rng=rng)
chk("rebuild_block composite==mean(items)", bool((df.Y1 == df[[f"A{i}" for i in range(1, 6)]].mean(1)).all()))
chk("rebuild_block corr(X1,Y1)≈-0.49", abs(df.X1.corr(df.Y1) + 0.49) < 0.04)
chk("rebuild_block items in 1..7 int", bool(df[[f"A{i}" for i in range(1, 6)]].values.min() >= 1 and
                                            df[[f"A{i}" for i in range(1, 6)]].values.max() <= 7))

# iman_conover: distribution-free, preserves marginals, hits Spearman
xa = rng.lognormal(0, 1, n); xb = rng.uniform(0, 10, n)
Y = C.iman_conover(np.column_stack([xa, xb]), [[1, 0.6], [0.6, 1]], rng=rng)
sp = np.corrcoef(C._ranks(Y[:, 0]), C._ranks(Y[:, 1]))[0, 1]
chk("iman_conover spearman≈0.6", abs(sp - 0.6) < 0.05)
chk("iman_conover marginal preserved", np.allclose(np.sort(Y[:, 0]), np.sort(xa)))

# gaussian_copula
Z = C.gaussian_copula(n, [[1, 0.5], [0.5, 1]], [lambda q: C._phi_inv(q), lambda q: -np.log(1 - q)], rng=rng)
chk("gaussian_copula corr in (0.4,0.55)", 0.40 < np.corrcoef(Z[:, 0], Z[:, 1])[0, 1] < 0.55)

# fleishman: skew + kurtosis
y = C.fleishman(rng.standard_normal(n), 1.0, 2.0)
chk("fleishman skew≈1.0", abs(C._skew(y) - 1.0) < 0.15)
chk("fleishman kurt≈2.0", abs(C._kurt(y) - 2.0) < 0.6)

# nonnormal_data (Vale-Maurelli)
V = C.nonnormal_data(n, [[1, 0.5], [0.5, 1]], skews=[1.0, -0.5], kurts=[2.0, 1.0], rng=rng)
chk("VM corr≈0.5", abs(np.corrcoef(V[:, 0], V[:, 1])[0, 1] - 0.5) < 0.05)
chk("VM marginal skew≈1.0", abs(C._skew(V[:, 0]) - 1.0) < 0.2)

# factor_model_sample
Xf = C.factor_model_sample(n, [[.7, 0], [.75, 0], [.8, 0], [0, .7], [0, .75], [0, .8]],
                           factor_corr=[[1, .4], [.4, 1]], rng=rng)
chk("factor alpha f1 in (.7,.85)", 0.70 < C.cronbach_alpha(Xf[:, :3]) < 0.85)

# tune_scalar: generic fallback
base = rng.standard_normal(n); e = rng.standard_normal(n)
a = C.tune_scalar(lambda a: np.corrcoef(base, a * base + e)[0, 1], 0.7, x0=1.0)
chk("tune_scalar hits 0.7", abs(np.corrcoef(base, a * base + e)[0, 1] - 0.7) < 0.01)

# shift_group_effect: Cohen's d
g = rng.integers(0, 2, n); v = rng.standard_normal(n) * 2 + 5
v2 = C.shift_group_effect(v, g, 0.5)
pooled = np.sqrt(np.mean([v2[g == k].var(ddof=1) for k in (0, 1)]))
chk("shift_group_effect d≈0.5", abs((v2[g == 1].mean() - v2[g == 0].mean()) / pooled - 0.5) < 0.02)

# inject_missing / inject_outliers
chk("inject_missing rate≈0.1", abs(np.mean(np.isnan(C.inject_missing(v.copy(), 0.1, "MCAR", rng=rng))) - 0.1) < 0.03)
o = C.inject_outliers(v.copy(), 0.02, k=5, rng=rng)
chk("inject_outliers creates extremes", (np.abs((o - o.mean()) / o.std()) > 4).any())

# rake
dfr = pd.DataFrame({"sex": rng.integers(0, 2, n)})
w = C.rake(dfr, {"sex": {0: 0.7, 1: 0.3}})
chk("rake weighted prop≈0.7", abs(w[dfr.sex == 0].sum() / w.sum() - 0.7) < 0.01)

# fit_from_reference
ref = pd.DataFrame({"a": rng.lognormal(0, 1, 3000)})
ref["b"] = rng.gamma(2, 2, 3000) + 0.3 * ref["a"]
syn = C.fit_from_reference(ref, rng=rng)(3000)
chk("fit_from_reference keeps spearman sign",
    np.sign(syn.corr(method="spearman").iloc[0, 1]) == np.sign(ref.corr(method="spearman").iloc[0, 1]))

print(f"  ({sum(PASS)}/{len(PASS)} so far)\n")

# ---------- new (round-3) functions ----------
import pandas as _pd

# ts_ar lag-1 autocorr
xs = C.ts_ar(3000, ar=(0.7,), sd=1.0, rng=rng)
chk("ts_ar lag-1 acf ≈ 0.7", abs(np.corrcoef(xs[:-1], xs[1:])[0,1] - 0.7) < 0.05)

# panel ICC
df_p = C.panel_data(200, 20, icc=0.3, ar1=0.4, rng=rng)
bv = df_p.groupby("unit").y.mean().var(); wv = df_p.groupby("unit").y.var().mean()
chk("panel_data ICC ≈ 0.3", abs(bv/(bv+wv) - 0.30) < 0.07)

# survival HR=2 → treated half the median time
X_s = rng.standard_normal((5000, 1))
ss = C.survival_data(5000, baseline_rate=0.1, hazard_ratios=[2.0], X=X_s,
                     censor_rate=0.05, rng=rng)
chk("survival has events", 0.5 < ss.event.mean() < 0.9)

# markov fit recovers transition
P_t = np.array([[0.7,0.2,0.1],[0.1,0.8,0.1],[0.2,0.2,0.6]])
seq = C.markov_chain(20000, P_t, states=["A","B","C"], rng=rng)
Ph, _ = C.fit_markov(seq, states=["A","B","C"])
chk("markov P estimate within 0.02", np.max(np.abs(Ph - P_t)) < 0.02)

# count NB overdispersed
v_nb = C.count_data(5000, 3.0, dispersion=1.0, rng=rng)
chk("NB variance > mean", v_nb.var() > 2 * v_nb.mean())

# DAG confounder unbiased after adjustment
dfd = C.dag_sample(8000, [
    ("U", lambda d,n,r: r.standard_normal(n)),
    ("X", lambda d,n,r: 0.6*d["U"] + r.standard_normal(n)),
    ("Y", lambda d,n,r: 0.4*d["X"] + 0.5*d["U"] + r.standard_normal(n)),
])
b_adj = np.linalg.lstsq(np.column_stack([np.ones(len(dfd)),dfd.X,dfd.U]), dfd.Y, rcond=None)[0][1]
chk("DAG adjusted b ≈ 0.4", abs(b_adj - 0.4) < 0.03)

# A/B test continuous effect
ab = C.ab_test_data(2000, baseline=10, effect=1.0, sd=3, rng=rng)
d = ab.groupby("arm").y.mean(); chk("A/B effect ≈ 1.0", abs(d["treatment"]-d["control"]-1.0) < 0.2)

# classification_dataset hits AUC + balance
cd = C.classification_dataset(3000, n_features=4, target_auc=0.8, class_balance=0.3, rng=rng)
from numpy.linalg import lstsq
W = lstsq(np.column_stack([np.ones(len(cd))]+[cd[f"x{i+1}"].values.reshape(-1,1) for i in range(4)]), cd.y.values, rcond=None)[0]
pred = cd[[f"x{i+1}" for i in range(4)]].values @ W[1:] + W[0]
o = np.argsort(pred); ys = cd.y.values[o]; npos = ys.sum(); nneg = len(ys)-npos
auc = (np.arange(1,len(ys)+1)[ys==1].sum() - npos*(npos+1)/2) / (npos*nneg)
chk("classification AUC ≈ 0.8", abs(auc - 0.8) < 0.04)
chk("classification balance ≈ 0.3", abs(cd.y.mean() - 0.3) < 0.02)

# mixed_copula: ordinal column has all 4 cats
mc = C.mixed_copula(3000, [
    dict(name="age",  type="continuous", ppf=lambda q: 30 + 10*C._phi_inv(q)),
    dict(name="male", type="binary",     p=0.5),
    dict(name="edu",  type="ordinal",    cuts=[0.3, 0.6, 0.85])],
    target_corr=[[1,0.3,0.4],[0.3,1,0.2],[0.4,0.2,1]], rng=rng)
chk("mixed_copula has 4 ordinal cats", set(mc.edu.unique()) == {0,1,2,3})

# discriminability: same → ~0.5, shifted → high
real = _pd.DataFrame({"a": rng.standard_normal(1000)+1, "b": rng.standard_normal(1000)})
syn_same = _pd.DataFrame({"a": rng.standard_normal(1000)+1, "b": rng.standard_normal(1000)})
syn_diff = _pd.DataFrame({"a": rng.standard_normal(1000)+3, "b": rng.standard_normal(1000)})
chk("discriminability same ≈ 0.5", abs(C.discriminability(real, syn_same) - 0.5) < 0.10)
chk("discriminability shifted >> 0.5", C.discriminability(real, syn_diff) > 0.7)

# dirichlet rows sum to 1
chk("dirichlet rows sum 1", np.allclose(C.dirichlet_compositional(50, [2,3,5], rng=rng).sum(1), 1))

# ipw weights
chk("ipw_weights basic", np.allclose(C.ipw_weights([1,0],[0.4,0.6]), [1/0.4, 1/0.4]))

# bootstrap shape
chk("bootstrap_perturb shape", C.bootstrap_perturb(real, n=500, rng=rng).shape == (500, 2))

print(f"\n{sum(PASS)}/{len(PASS)} passed (extended)")
sys.exit(0 if all(PASS) else 1)
