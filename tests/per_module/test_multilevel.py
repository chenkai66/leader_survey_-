from _common import chk, summary
import numpy as np, pandas as pd, calibrate as C
rng = np.random.default_rng(7)
z = C.zscale(rng.standard_normal(2000))
df = pd.DataFrame({"X": 4 + z})
C.rebuild_block(df, ["X"], specs=[dict(items=[f"A{i}" for i in range(1,6)], comp="Y",
                                        mean=4.5, sd=1.2, tgt=[0.5])],
                item_sigma=0.66, outer=9, rng=rng)
chk("rebuild_block composite == mean(items)", bool((df.Y == df[[f"A{i}" for i in range(1,6)]].mean(1)).all()))
chk("rebuild_block items in 1..7 int", df[[f"A{i}" for i in range(1,6)]].values.min() >= 1 and df[[f"A{i}" for i in range(1,6)]].values.max() <= 7)
chk("cronbach_alpha plausible", 0.5 < C.cronbach_alpha(df[[f"A{i}" for i in range(1,6)]].values) < 1.0)
Xf = C.factor_model_sample(3000, [[.7,0],[.75,0],[.8,0],[0,.7],[0,.75],[0,.8]],
                            factor_corr=[[1,.4],[.4,1]], rng=rng)
chk("factor_model alpha", 0.7 < C.cronbach_alpha(Xf[:,:3]) < 0.85)
X_irt, theta = C.irt_2pl_data(1000, np.linspace(-2,2,20), np.full(20,1.5), rng=rng)
chk("IRT 2PL theta-totalscore corr > 0.85", np.corrcoef(theta, X_irt.sum(1))[0,1] > 0.85)
df_p = C.panel_data(200, 20, icc=0.3, ar1=0.4, rng=rng)
bv = df_p.groupby("unit").y.mean().var(); wv = df_p.groupby("unit").y.var().mean()
chk("panel ICC ≈ 0.3", abs(bv/(bv+wv) - 0.3) < 0.07)
mr = C.multi_rater(2000, rater_corr=[[1,0.6],[0.6,1]], rng=rng)
chk("multi_rater inter-rater corr ≈ 0.6", abs(mr.corr().iloc[0,1] - 0.6) < 0.05)

# composite-preserving reliability calibration (regenerate items at target alpha,
# keep composite byte-identical so structural relationships are untouched)
comp = np.clip(np.round(rng.normal(4.5, 1.0, 500)), 1, 7)
it_a, ach = C.calibrate_item_reliability(comp, 6, target_alpha=0.78, rng=rng)
chk("calibrate_item_reliability alpha ≈ 0.78", abs(ach - 0.78) < 0.03)
chk("calibrate_item_reliability composite preserved", abs(it_a.mean(1) - comp).max() < 1e-9)
chk("calibrate_item_reliability items 1..7 int",
    it_a.min() >= 1 and it_a.max() <= 7 and it_a.dtype.kind == "i")
chk("sum_preserving_round hits target sum", C.sum_preserving_round([4.3,5.1,3.8], 13).sum() == 13)
summary()
