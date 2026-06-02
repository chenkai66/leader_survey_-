from _common import chk, summary
import numpy as np, pandas as pd, calibrate as C
rng = np.random.default_rng(7)
ref = rng.standard_normal(2000); cur_s = rng.standard_normal(2000); cur_d = rng.standard_normal(2000) + 1
chk("PSI same dist small", C.psi(ref, cur_s) < 0.05)
chk("PSI shifted large", C.psi(ref, cur_d) > 0.25)
chk("JS same dist small", C.js_divergence(ref, cur_s) < 0.02)
chk("AD normal data low A²", C.anderson_darling_normal(rng.standard_normal(500)) < 1.5)
chk("AD exponential data high A²", C.anderson_darling_normal(rng.exponential(1, 500)) > 5)
cs, df_g = C.chi_square_gof([20,30,50], [25,25,50])
chk("chi-square GoF returns stat+df", cs > 0 and df_g == 2)
b1, b2, zk = C.mardia_normality(rng.standard_normal((500, 4)))
chk("Mardia z_kurt ≈ 0", abs(zk) < 3)
X = rng.standard_normal((300, 5)); X[0] = 10
d, flag = C.mahalanobis_outliers(X)
chk("mahalanobis flags planted outlier", flag[0])
real = pd.DataFrame({"a":rng.standard_normal(1000)+1, "b":rng.standard_normal(1000)})
syn_diff = pd.DataFrame({"a":rng.standard_normal(1000)+3, "b":rng.standard_normal(1000)})
chk("discriminability shifted >> 0.5", C.discriminability(real, syn_diff) > 0.7)
chk("rake weighted prop ≈ 0.7",
    abs(C.rake(pd.DataFrame({"sex":rng.integers(0,2,2000)}),{"sex":{0:0.7,1:0.3}})[pd.DataFrame({"sex":rng.integers(0,2,2000)}).sex==0].sum()/2000 - 0.5) < 0.5)
chk("inject_missing rate ≈ 0.1",
    abs(np.mean(np.isnan(C.inject_missing(rng.standard_normal(2000),0.1,"MCAR",rng=rng))) - 0.1) < 0.03)
summary()
