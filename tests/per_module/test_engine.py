from _common import chk, summary
import numpy as np, calibrate as C
rng = np.random.default_rng(7)
# tune_scalar generic root finding
base = rng.standard_normal(2000); e = rng.standard_normal(2000)
a = C.tune_scalar(lambda a: np.corrcoef(base, a*base + e)[0,1], 0.7, x0=1.0)
chk("tune_scalar root finding", abs(np.corrcoef(base, a*base + e)[0,1] - 0.7) < 0.02)
# build_latents exact in-sample corr
z1 = C.zscale(rng.standard_normal(2000)); z2 = C.zscale(-0.3*z1 + np.sqrt(1-0.09)*rng.standard_normal(2000))
L = C.build_latents(np.column_stack([z1,z2]), [[-0.5, 0.4]])
chk("build_latents exact corr", abs(np.corrcoef(L[:,0], z1)[0,1] + 0.5) < 0.02)
# nearest_pd
R = np.array([[1, 0.99, 0.99], [0.99, 1, 0.99], [0.99, 0.99, 1]])
chk("nearest_pd preserves PD input", np.allclose(C.nearest_pd(R), R, atol=1e-4))
summary()
