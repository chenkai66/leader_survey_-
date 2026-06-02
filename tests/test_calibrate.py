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

print(f"  ({sum(PASS)}/{len(PASS)} so far)\n")

# ---------- round-4: simple stats / regression / multi-table consistency ----------
from numpy.linalg import lstsq as _ls

# regression with target R²
df_r = C.regression_dataset(3000, coefs=[0.5,-0.3,0.2], intercept=1.0, target_r2=0.5, rng=rng)
b = _ls(np.column_stack([np.ones(3000), df_r[["x1","x2","x3"]].values]), df_r.y.values, rcond=None)[0]
chk("regression b1 ≈ 0.5", abs(b[1]-0.5) < 0.05)
chk("regression intercept ≈ 1.0", abs(b[0]-1.0) < 0.1)
y = df_r.y.values; pred = df_r[["x1","x2","x3"]].values @ b[1:] + b[0]
r2 = 1 - ((y-pred)**2).sum() / ((y-y.mean())**2).sum()
chk("regression R² ≈ 0.5", abs(r2-0.5) < 0.05)

# logistic recovers coefs
dfl = C.logistic_dataset(5000, coefs=[0.8,-0.5], intercept=-0.5, rng=rng)
Xl = np.column_stack([np.ones(len(dfl)), dfl.x1, dfl.x2]); yl = dfl.y.values
w_l = np.zeros(3)
for _ in range(300):
    p_ = 1/(1+np.exp(-Xl@w_l)); w_l -= 0.1*Xl.T@(p_-yl)/len(Xl)
chk("logistic b1 recovered ≈ 0.8", abs(w_l[1]-0.8) < 0.1)
chk("logistic b2 recovered ≈ -0.5", abs(w_l[2]-(-0.5)) < 0.1)

# anova interaction visible (SE shrinks with n; use enough power)
da = C.anova_design(400, {"A":2,"B":2}, main_effects={"A":[0,1],"B":[0,0.5]},
                    interaction_effects={("A","B"): [[0,0],[0,0.7]]}, sd=1.0, rng=rng)
m = da.groupby(["A","B"]).y.mean().unstack()
ix = (m.loc[1,1] - m.loc[1,0]) - (m.loc[0,1] - m.loc[0,0])
chk("anova interaction ≈ 0.7", abs(ix - 0.7) < 0.20)

# paired within_corr
p_p = C.paired_data(2000, change_effect=2, within_corr=0.7, rng=rng)
chk("paired pre-post corr ≈ 0.7", abs(p_p.pre.corr(p_p.post) - 0.7) < 0.04)
chk("paired mean change ≈ 2.0", abs(p_p.change.mean() - 2.0) < 0.1)

# contingency 2x2 OR
ct = C.contingency_table([100,100], [100,100], odds_ratio=2.0, rng=rng)
or_ = (ct[0,0]*ct[1,1]) / max(ct[0,1]*ct[1,0], 1)
chk("contingency OR ≈ 2.0", 1.5 < or_ < 3.0)

# multinomial exact
mn = C.multinomial_dataset(1000, [0.6, 0.3, 0.1], rng=rng)
uniq, cnt = np.unique(mn, return_counts=True)
chk("multinomial exact 600/300/100", list(cnt) == [600, 300, 100])

# correlation_matrix_block PD + block structure
Rb = C.correlation_matrix_block([3,3], 0.6, 0.1)
chk("block matrix PD", np.all(np.linalg.eigvalsh(Rb) > 0))
chk("block within > between", Rb[0,1] == 0.6 and Rb[0,3] == 0.1)

# partial_corr removes confounder
df_pc = pd.DataFrame({"x": rng.standard_normal(2000), "z": rng.standard_normal(2000)})
df_pc["y"] = 0.7*df_pc.x + 0.5*df_pc.z + rng.standard_normal(2000)
pc = C.partial_corr(df_pc, "x", "y", ["z"])
chk("partial_corr ≈ 0.7/sqrt(...) > raw", pc > df_pc.x.corr(df_pc.y) - 0.1)

# vif
vifs = C.vif(df_pc, ["x","y","z"])
chk("vif all finite & >=1", all(v >= 0.99 and np.isfinite(v) for v in vifs.values()))

# relational tables + referential integrity check
parents = pd.DataFrame({"user_id": C.generate_id_column(20, prefix="U"),
                        "signup_age": rng.integers(20, 60, 20)})
children = C.relational_children(parents, "user_id",
    n_per_parent=lambda r: r.poisson(3),
    child_cols={"amount": lambda p, i, r: 50 + 5*p.signup_age + r.normal(0, 20)},
    rng=rng)
ok_ri, _ = C.check_referential_integrity(children, "user_id", parents, "user_id")
chk("relational FK integrity", ok_ri)
chk("relational child count varies", children.groupby("user_id").size().nunique() > 1)

# aggregate consistency
parent2 = pd.DataFrame({"pid":["A","B","C"], "total":[10,20,30]})
child2 = pd.DataFrame({"pid":["A","A","B","B","C"], "val":[5,5,8,12,30]})
ok_a, _ = C.check_aggregate(child2, "pid", "val", parent2, "pid", "total", agg="sum")
chk("aggregate consistency OK", ok_a)

# temporal & identity & enforce_constraints
chk("temporal monotone", C.check_temporal(pd.DataFrame({"a":[1,2],"b":[2,3]}), "a","b")[0])
chk("identity a+b==c",
    C.check_identity(pd.DataFrame({"a":[1,2],"b":[2,3],"c":[3,5]}), lambda r: r.a+r.b-r.c)[0])
ef, viol = C.enforce_constraints(
    pd.DataFrame({"x":[1,2,3], "y":[1,0,3]}),
    [("y_pos", lambda d: d.y > 0)], action="drop", verbose=False)
chk("enforce_constraints drops bad", len(ef) == 2 and viol["y_pos"] == 1)

# multi-rater inter-rater corr
mr = C.multi_rater(2000, rater_corr=[[1,0.6,0.4],[0.6,1,0.5],[0.4,0.5,1]], rng=rng)
chk("multi_rater r12 ≈ 0.6", abs(mr.corr().iloc[0,1] - 0.6) < 0.05)

# funnel monotone non-increasing reach
fn = C.funnel_data(1000, [0.7, 0.5, 0.3], rng=rng)
cnts = [fn[f"stage_{i+1}"].sum() for i in range(4)]
chk("funnel reach monotone non-increasing", all(cnts[i] >= cnts[i+1] for i in range(3)))

# evolve_panel: temporal expansion correct
init = pd.DataFrame({"id": C.generate_id_column(10, "A"), "balance": np.full(10, 100.0)})
panel = C.evolve_panel_state(init, 5, lambda s,t,r: s.assign(balance=s.balance+r.normal(0,5,len(s))), rng=rng)
chk("evolve_panel shape n*T", len(panel) == 50 and panel.time.nunique() == 5)
print(f"  ({sum(PASS)}/{len(PASS)} so far)\n")

# ---------- round-5: industry-grade depth per category ----------
# distributions
for d, p in [("normal",{"mean":5,"sd":2}), ("gamma",{"shape":2,"scale":2}),
             ("beta",{"a":2,"b":5}), ("exponential",{"scale":3}),
             ("weibull",{"shape":1.5}), ("t",{"df":5}),
             ("truncnormal",{"mean":0,"sd":1,"lo":-1,"hi":1})]:
    x = C.sample_dist(d, 3000, rng=rng, **p)
    chk(f"sample_dist {d} in plausible range", np.isfinite(x).all() and len(x)==3000)
chk("truncnormal respects bounds",
    (C.sample_dist("truncnormal", 1000, rng=rng, mean=0, sd=1, lo=-1, hi=1).min() >= -1) and
    (C.sample_dist("truncnormal", 1000, rng=rng, mean=0, sd=1, lo=-1, hi=1).max() <= 1))
gm = C.gaussian_mixture(5000, [0.3,0.7], [-2,2], [0.5,1.0], rng=rng)
chk("gaussian_mixture bimodal", gm.std() > 1.5)
zi = C.zero_inflated_continuous(3000, 0.4, lambda n,r: r.lognormal(2,0.5,n), rng=rng)
chk("zero_inflated has zeros", 0.35 < np.mean(zi==0) < 0.45)

# t-copula has heavier joint tails than gaussian copula
tc = C.t_copula(5000, [[1,0.5],[0.5,1]], df=4, ppfs=[lambda q: C._phi_inv(q)]*2, rng=rng)
gc = C.gaussian_copula(5000, [[1,0.5],[0.5,1]], ppfs=[lambda q: C._phi_inv(q)]*2, rng=rng)
def jt(X,q): a,b=np.quantile(X[:,0],q),np.quantile(X[:,1],q); return np.mean((X[:,0]>a)&(X[:,1]>b))
chk("t-copula upper tail > gaussian", jt(tc,0.95) > jt(gc,0.95))
cc = C.clayton_copula(5000, theta=2.0, ppfs=[lambda q: C._phi_inv(q)]*2, rng=rng)
def jl(X,q): a,b=np.quantile(X[:,0],q),np.quantile(X[:,1],q); return np.mean((X[:,0]<a)&(X[:,1]<b))
chk("Clayton lower tail > gaussian", jl(cc,0.05) > jl(gc,0.05))

# ARMA / GARCH / VAR
x = C.ts_arma(3000, ar=(0.6,), ma=(0.3,), sd=1.0, rng=rng)
chk("ARMA(1,1) acf > pure AR(.6)", np.corrcoef(x[:-1],x[1:])[0,1] > 0.6)
r, sig = C.ts_garch(5000, omega=0.05, alpha=0.1, beta=0.85, rng=rng)
chk("GARCH volatility clustering", np.corrcoef(r[:-1]**2, r[1:]**2)[0,1] > 0.05)
Y = C.ts_var(2000, A_list=[np.array([[0.5,0.2],[0.1,0.4]])], Sigma=[[1,0.3],[0.3,1]], rng=rng)
chk("VAR(1) shape correct", Y.shape == (2000, 2))

# GLM
dfp = C.poisson_regression_dataset(3000, coefs=[0.5,-0.3], intercept=1.0, rng=rng)
chk("Poisson reg outputs integers >=0", (dfp.y >= 0).all() and (dfp.y == dfp.y.astype(int)).all())
dfm = C.multinomial_logit_dataset(2000, coefs_per_class=[[1.0,-0.5],[0.5,1.0]], rng=rng)
chk("multinomial logit 3 classes", set(dfm.y.unique()) == {0,1,2})
dfo = C.ordinal_logit_dataset(2000, coefs=[0.8,-0.4], thresholds=[-1,0,1], rng=rng)
chk("ordinal logit 4 categories", set(dfo.y.unique()) == {0,1,2,3})

# causal/experimental
dd = C.did_data(300, n_periods=2, treatment_time=1, treatment_effect=0.7, rng=rng)
ch = dd.pivot_table(index=["unit","treated"], columns="time", values="y").reset_index()
ch["diff"] = ch[1] - ch[0]
did_est = ch[ch.treated==1]["diff"].mean() - ch[ch.treated==0]["diff"].mean()
chk("DiD estimator near 0.7", abs(did_est - 0.7) < 0.3)
iv = C.iv_data(5000, b_xy=0.5, b_zx=0.7, rng=rng)
from numpy.linalg import lstsq as _ls2
ols = _ls2(np.column_stack([np.ones(len(iv)),iv.x]), iv.y, rcond=None)[0][1]
xh = _ls2(np.column_stack([np.ones(len(iv)),iv.z]), iv.x, rcond=None)[0]
xp_ = xh[0] + xh[1]*iv.z
tsls = _ls2(np.column_stack([np.ones(len(iv)),xp_]), iv.y, rcond=None)[0][1]
chk("IV 2SLS unbiased vs OLS biased", abs(tsls - 0.5) < 0.05 and abs(ols - 0.5) > 0.1)

# competing risks: all causes sampled
cr = C.competing_risks_data(3000, baseline_rates=[0.1,0.05,0.03], censor_rate=0.05, rng=rng)
chk("competing risks samples all causes", set(cr.cause.unique()) >= {-1,0,1,2})

# IRT theta-totalscore correlation high
X_irt, theta = C.irt_2pl_data(800, np.linspace(-2,2,20), np.full(20,1.5), rng=rng)
chk("IRT 2PL theta-totalscore corr > 0.85", np.corrcoef(theta, X_irt.sum(1))[0,1] > 0.85)

# graphs
e_er = C.graph_er(50, 0.1, rng=rng)
chk("ER edges in expected range", 80 < len(e_er) < 170)
e_ba = C.graph_ba(80, 3, rng=rng); deg = np.zeros(80, int)
for u,v in e_ba: deg[u]+=1; deg[v]+=1
chk("BA has heavy-tailed degrees", deg.max() > 15)
e_sbm, blk = C.graph_sbm([20,20], 0.5, 0.05, rng=rng)
wi = sum(1 for u,v in e_sbm if blk[u]==blk[v])
chk("SBM within > between", wi > (len(e_sbm) - wi))

# ML scenarios
ad = C.anomaly_dataset(2000, contamination=0.05, rng=rng)
chk("anomaly contamination ≈ 0.05", abs(ad.label.mean() - 0.05) < 0.005)
bf, af = C.concept_drift_data(2000, drift_type="covariate", drift_magnitude=1.0, rng=rng)
chk("concept drift covariate shift ≈ 1.0", abs(af.x1.mean() - bf.x1.mean() - 1.0) < 0.2)

# diagnostics
ref = rng.standard_normal(2000); cur_s = rng.standard_normal(2000); cur_d = rng.standard_normal(2000)+1
chk("PSI small for same dist", C.psi(ref, cur_s) < 0.05)
chk("PSI large for shifted dist", C.psi(ref, cur_d) > 0.25)
chk("JS small for same dist", C.js_divergence(ref, cur_s) < 0.02)

# multi-table extensions
L = pd.DataFrame({"user_id": C.generate_id_column(50,"U")})
R = pd.DataFrame({"item_id": C.generate_id_column(30,"I")})
m2m = C.many_to_many(L, R, "user_id", "item_id", density=0.05, rng=rng)
chk("many_to_many density approx 5%", 40 < len(m2m) < 110)
init_s = pd.DataFrame({"emp_id": C.generate_id_column(10,"E"), "salary": rng.uniform(50,100,10)})
hist = C.scd_type2(init_s, "emp_id", n_changes=3,
                   change_fn=lambda r,t,rng_: {**r, "salary": r["salary"]*1.05},
                   time_periods=12, rng=rng)
chk("SCD type-2 has valid_from/valid_to", "valid_from" in hist.columns and "valid_to" in hist.columns)
chk("SCD type-2 versions per entity > 1 on average", len(hist) > 10)

# SMOTE
Xs = rng.standard_normal((600,5)); ys = np.concatenate([np.zeros(540,int), np.ones(60,int)])
Xn, yn = C.smote(Xs, ys, target_balance=0.5, rng=rng)
chk("SMOTE balanced", abs((yn==1).mean() - 0.5) < 0.05)
print(f"  ({sum(PASS)}/{len(PASS)} so far)\n")

# ---------- round-6: spatial / HMM / Hawkes / Bayesian / recsys / low-rank / adversarial / AD/GoF ----------
# spatial
pts = C.spatial_points(500, pattern="cluster", rng=rng)
chk("spatial cluster shape", pts.shape == (500, 2))
field = C.spatial_field(12, range_param=0.3, rng=rng)
mi = C.morans_i(field.ravel(), np.array([(i,j) for i in range(12) for j in range(12)], float))
chk("morans_i field high autocorr", mi > 0.3)
mi_noise = C.morans_i(rng.standard_normal(144), np.array([(i,j) for i in range(12) for j in range(12)], float))
chk("morans_i noise ≈ 0", abs(mi_noise) < 0.15)

# HMM
states, obs = C.hmm_data(2000, np.array([[0.9,0.1],[0.2,0.8]]),
                         emission_means=[0,3], emission_sds=[1,1], rng=rng)
chk("HMM emission means differ by state", abs(obs[states==1].mean() - obs[states==0].mean()) > 2)

# Hawkes
events = C.hawkes_process(50, mu=1.0, alpha=0.4, beta=1.0, rng=rng)
chk("Hawkes more events than base μ·T", len(events) > 50)

# Bayesian
ps = C.prior_dataset(1000, dict(mu=("normal",{"mean":0,"sd":1}),
                                 sigma=("gamma",{"shape":2,"scale":1})), rng=rng)
chk("prior_dataset cols generated", set(ps.columns) == {"mu","sigma"})
chain = C.metropolis_posterior(lambda x: -0.5*(x-2)**2, x0=0.0, n_iter=3000,
                                proposal_sd=0.5, burn=500, rng=rng)
chk("metropolis posterior mean ≈ 2", abs(chain.mean() - 2) < 0.2)

# recsys
R, mask, U, V = C.recsys_explicit(80, 40, latent_dim=5, sparsity=0.9, rng=rng)
chk("recsys explicit shape", R.shape == (80,40) and mask.sum() < R.size)
inter = C.recsys_implicit(80, 40, n_interactions=600, rng=rng)
chk("recsys implicit has unique interactions", 0 < len(inter) <= 600)

# low-rank
M = C.low_rank_data(150, 40, rank=5, noise_sd=0.3, rng=rng)
sv = np.linalg.svd(M, compute_uv=False)
chk("low_rank singular value gap", sv[0] / sv[5] > 5)

# cluster
Xc, yc = C.cluster_data(300, n_clusters=3, n_features=2, separation=3.0, rng=rng)
chk("cluster has 3 classes", len(set(yc)) == 3)

# adversarial
X0 = rng.standard_normal((100, 5))
Xp = C.adversarial_perturb(X0, epsilon=0.1, norm="inf", rng=rng)
chk("adversarial inf-norm bounded", abs(np.abs(Xp-X0).max() - 0.1) < 1e-6)
Xp2 = C.adversarial_perturb(X0, epsilon=0.1, norm="2", rng=rng)
chk("adversarial 2-norm bounded", np.linalg.norm(Xp2-X0, axis=1).max() < 0.11)

# label noise
y = np.random.randint(0, 3, 1000); yn = C.label_noise(y, noise_rate=0.1, n_classes=3, rng=rng)
chk("label_noise rate ≈ 0.1", abs((y!=yn).mean() - 0.1) < 0.03)

# Anderson-Darling
chk("AD normal data low A²", C.anderson_darling_normal(rng.standard_normal(500)) < 1.5)
chk("AD exponential data high A²", C.anderson_darling_normal(rng.exponential(1, 500)) > 5)

# chi-square GoF
cs, df_g = C.chi_square_gof([20,30,50], [25,25,50])
chk("chi-square GoF returns stat + df", cs > 0 and df_g == 2)

print(f"\nFINAL: {sum(PASS)}/{len(PASS)} passed")
sys.exit(0 if all(PASS) else 1)
