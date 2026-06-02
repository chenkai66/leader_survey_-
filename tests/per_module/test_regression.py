from _common import chk, summary
import numpy as np, calibrate as C
from numpy.linalg import lstsq
rng = np.random.default_rng(7)
df = C.regression_dataset(3000, coefs=[0.5,-0.3,0.2], intercept=1.0, target_r2=0.5, rng=rng)
b = lstsq(np.column_stack([np.ones(3000), df[["x1","x2","x3"]].values]), df.y, rcond=None)[0]
chk("regression recovers b1", abs(b[1]-0.5) < 0.05)
df = C.logistic_dataset(3000, coefs=[0.8,-0.5], intercept=-0.3, rng=rng)
chk("logistic outputs binary", set(df.y.unique()) == {0, 1})
df = C.poisson_regression_dataset(3000, coefs=[0.4, -0.2], intercept=1.0, rng=rng)
chk("poisson outputs non-neg int", (df.y >= 0).all())
df = C.multinomial_logit_dataset(2000, coefs_per_class=[[1,-0.5],[0.5,1]], rng=rng)
chk("multinomial 3 classes", set(df.y.unique()) == {0,1,2})
df = C.ordinal_logit_dataset(2000, coefs=[0.8, -0.4], thresholds=[-1, 0, 1], rng=rng)
chk("ordinal 4 categories", set(df.y.unique()) == {0,1,2,3})
df = C.anova_design(200, {"A":2,"B":2}, main_effects={"A":[0,1],"B":[0,0.5]},
                   interaction_effects={("A","B"): [[0,0],[0,0.7]]}, sd=1.0, rng=rng)
m = df.groupby(["A","B"]).y.mean().unstack()
chk("anova interaction near 0.7", abs((m.loc[1,1]-m.loc[1,0]) - (m.loc[0,1]-m.loc[0,0]) - 0.7) < 0.3)
df = C.paired_data(1500, change_effect=2.0, within_corr=0.7, rng=rng)
chk("paired pre-post corr ≈ 0.7", abs(df.pre.corr(df.post) - 0.7) < 0.04)
df = C.two_sample(500, 500, mean1=0, mean2=0.5, sd1=1, sd2=1.2, rng=rng)
chk("two_sample diff ≈ 0.5", abs(df[df.group=='B'].y.mean() - df[df.group=='A'].y.mean() - 0.5) < 0.25)
ct = C.contingency_table([100, 100], [100, 100], odds_ratio=2.0, rng=rng)
chk("contingency 2x2 OR ≈ 2", 1.5 < (ct[0,0]*ct[1,1])/max(ct[0,1]*ct[1,0], 1) < 3.0)
summary()
