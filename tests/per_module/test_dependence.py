from _common import chk, summary
import numpy as np, calibrate as C
rng = np.random.default_rng(7)
xa = rng.lognormal(0,1,3000); xb = rng.uniform(0,10,3000)
Y = C.iman_conover(np.column_stack([xa, xb]), [[1, 0.6],[0.6, 1]], rng=rng)
sp = np.corrcoef(C._ranks(Y[:,0]), C._ranks(Y[:,1]))[0,1]
chk("iman_conover spearman ≈ 0.6", abs(sp - 0.6) < 0.05)
chk("iman_conover preserves marginal", np.allclose(np.sort(Y[:,0]), np.sort(xa)))
Z = C.gaussian_copula(3000, [[1, 0.5],[0.5, 1]], [lambda q: C._phi_inv(q)]*2, rng=rng)
chk("gaussian_copula corr in band", 0.4 < np.corrcoef(Z[:,0], Z[:,1])[0,1] < 0.6)
V = C.nonnormal_data(3000, [[1, 0.5],[0.5, 1]], skews=[1.0, -0.5], kurts=[2.0, 1.0], rng=rng)
chk("VM corr ≈ 0.5", abs(np.corrcoef(V[:,0], V[:,1])[0,1] - 0.5) < 0.06)
tc = C.t_copula(3000, [[1, 0.5],[0.5, 1]], df=4, ppfs=[lambda q: C._phi_inv(q)]*2, rng=rng)
gc = C.gaussian_copula(3000, [[1, 0.5],[0.5, 1]], [lambda q: C._phi_inv(q)]*2, rng=rng)
chk("t-copula heavier tail than gaussian",
    np.mean((tc[:,0] > np.quantile(tc[:,0], 0.95)) & (tc[:,1] > np.quantile(tc[:,1], 0.95))) >
    np.mean((gc[:,0] > np.quantile(gc[:,0], 0.95)) & (gc[:,1] > np.quantile(gc[:,1], 0.95))))
summary()
