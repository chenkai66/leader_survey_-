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

print(f"\n{sum(PASS)}/{len(PASS)} passed")
sys.exit(0 if all(PASS) else 1)
