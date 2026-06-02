from _common import chk, summary
import numpy as np, pandas as pd, calibrate as C
from numpy.linalg import lstsq
rng = np.random.default_rng(7)
df = C.dag_sample(8000, [
    ("U", lambda d,n,r: r.standard_normal(n)),
    ("X", lambda d,n,r: 0.6*d["U"] + r.standard_normal(n)),
    ("Y", lambda d,n,r: 0.4*d["X"] + 0.5*d["U"] + r.standard_normal(n))])
b_adj = lstsq(np.column_stack([np.ones(len(df)), df.X, df.U]), df.Y, rcond=None)[0][1]
chk("DAG adjusted b ≈ 0.4", abs(b_adj - 0.4) < 0.03)
ab = C.ab_test_data(2000, baseline=10, effect=1.0, sd=3, rng=rng)
chk("A/B effect ≈ 1", abs(ab.groupby("arm").y.mean().diff().iloc[1] - 1.0) < 0.2)
iv = C.iv_data(5000, b_xy=0.5, b_zx=0.7, confounder_strength=0.5, rng=rng)
xh = lstsq(np.column_stack([np.ones(len(iv)), iv.z]), iv.x, rcond=None)[0]
tsls = lstsq(np.column_stack([np.ones(len(iv)), xh[0]+xh[1]*iv.z]), iv.y, rcond=None)[0][1]
chk("IV 2SLS unbiased", abs(tsls - 0.5) < 0.05)
ss = C.survival_data(3000, baseline_rate=0.1, hazard_ratios=[2.0], X=rng.standard_normal((3000,1)),
                      censor_rate=0.05, rng=rng)
chk("survival has events", 0.5 < ss.event.mean() < 0.95)
cr = C.competing_risks_data(3000, baseline_rates=[0.1,0.05,0.03], censor_rate=0.05, rng=rng)
chk("competing risks all causes", set(cr.cause.unique()) >= {-1,0,1,2})
df_h = C.hte_data(3000, n_features=3, rng=rng)
naive = df_h[df_h.treat==1].y.mean() - df_h[df_h.treat==0].y.mean()
chk("HTE naive ≈ true CATE", abs(naive - df_h.true_cate.mean()) < 0.15)
sc = C.synthetic_control_data(20, 30, treated_idx=0, treatment_time=15, treatment_effect=2.5, rng=rng)
tr = sc[sc.unit==0]
chk("synth control diff ≈ 2.5", abs((tr[tr.time>=15].y.mean() - tr[tr.time<15].y.mean()) - 2.5) < 1.2)
chk("cluster RCT diff ≈ 0.4", abs(C.cluster_rct(50, 30, treatment_effect=0.4, icc=0.15, rng=rng).groupby("treated").y.mean().diff().iloc[1] - 0.4) < 0.2)
df_hb, _ = C.hierarchical_bayes_data(20, 30, hyper_mean=5.0, hyper_sd=1.0, within_sd=0.5, rng=rng)
chk("hier_bayes group var > 0", df_hb.groupby("group").y.mean().var() > 0.3)
summary()
