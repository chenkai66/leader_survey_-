"""Non-normal data with controlled dependence — three approaches.
Run: python examples/example_nonnormal.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import numpy as np, calibrate as C
rng = np.random.default_rng(0)
n = 5000

print("== 1. Iman-Conover: correlate columns that ALREADY have the right marginals ==")
income = rng.lognormal(10, 0.6, n)          # right-skewed
age = rng.integers(22, 65, n).astype(float)  # discrete uniform
X = C.iman_conover(np.column_stack([income, age]), [[1, 0.45], [0.45, 1]], rng=rng)
print(f"  spearman(income,age) = {np.corrcoef(C._ranks(X[:,0]),C._ranks(X[:,1]))[0,1]:.3f} (target 0.45)")
print(f"  income marginal unchanged: {np.allclose(np.sort(X[:,0]), np.sort(income))}")

print("== 2. Vale-Maurelli: build skewed/kurtotic columns WITH a target Pearson corr ==")
V = C.nonnormal_data(n, [[1, 0.6, -0.3], [0.6, 1, 0.2], [-0.3, 0.2, 1]],
                     skews=[1.2, -0.8, 0.0], kurts=[3.0, 1.5, 0.5],
                     means=[50, 100, 0], sds=[10, 15, 1], rng=rng)
print("  Pearson:\n", np.round(np.corrcoef(V.T), 2))
print(f"  col0 skew={C._skew(V[:,0]):.2f} kurt={C._kurt(V[:,0]):.2f} mean={V[:,0].mean():.1f}")

print("== 3. Gaussian copula: pick each marginal + a dependence ==")
Z = C.gaussian_copula(n, [[1, 0.5], [0.5, 1]],
                      ppfs=[lambda q: 50 + 10 * C._phi_inv(q),     # Normal(50,10)
                            lambda q: -2 * np.log(1 - q)], rng=rng)  # Exponential(mean 2)
print(f"  corr={np.corrcoef(Z[:,0],Z[:,1])[0,1]:.3f}  col2 is exponential (skew={C._skew(Z[:,1]):.2f})")
