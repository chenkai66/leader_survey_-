"""
data-calibration toolkit — adjust a dataset to hit specified statistical
targets (correlations, cross-correlations, reliability, ICC, interactions)
while keeping composites/items consistent.

Domain-agnostic generalization of leader_survey_v2/code/rebuild_340.py.
All functions take plain arrays / DataFrames + column names; no project
constants baked in. See SKILL.md for the methodology behind each function.

Typical use:
    from calibrate import rebuild_block, verify
    rebuild_block(df, ["X1","X2"], specs=[...], pair_corr=[[1,r],[r,1]],
                  item_sigma=0.66, outer=9)
    verify(df, [("X1","Y1", -0.49), ...])
"""
from __future__ import annotations
import numpy as np

# ---------------------------------------------------------------- primitives
def zscale(x):
    x = np.asarray(x, float)
    s = x.std(ddof=0)
    return (x - x.mean()) / (s if s > 1e-12 else 1.0)


def nearest_pd(A):
    """Project a symmetric matrix to the nearest positive-definite one."""
    A = (np.asarray(A, float) + np.asarray(A, float).T) / 2
    w, V = np.linalg.eigh(A)
    return (V * np.clip(w, 1e-6, None)) @ V.T


def resid_against(Y, G):
    """Residual of Y after regressing on columns of G (G should include a 1s col)."""
    beta, *_ = np.linalg.lstsq(G, Y, rcond=None)
    return Y - G @ beta


# ----------------------------------------------- exact in-sample correlations
def build_latents(givens_z, targets, pair_corr=None, rng=None):
    """Return standardized latents (n, m) whose SAMPLE correlation to each
    given predictor equals `targets[i]` and whose mutual correlation equals
    `pair_corr` — both exactly (β = Rg⁻¹ r conditional-Gaussian construction).

    givens_z : (n,k) standardized predictors (already z-scored).
    targets  : list of length-k target-correlation vectors (one per new var).
    pair_corr: (m,m) target correlation among the new vars (default identity).
    Raises ValueError if a target is infeasible (residual variance <= 0).
    """
    rng = rng or np.random.default_rng()
    givens_z = np.atleast_2d(np.asarray(givens_z, float))
    if givens_z.shape[0] < givens_z.shape[1]:
        givens_z = givens_z.T
    n, k = givens_z.shape
    Rg = np.corrcoef(givens_z.T) if k > 1 else np.array([[1.0]])
    Rg_inv = np.linalg.inv(Rg)
    G1 = np.column_stack([np.ones(n), givens_z])
    m = len(targets)
    B = np.array([Rg_inv @ np.asarray(t, float) for t in targets])      # (m,k)
    sig = givens_z @ B.T                                                # (n,m)
    Csig = B @ Rg @ B.T
    pc = np.eye(m) if pair_corr is None else np.asarray(pair_corr, float)
    resid_cov = pc - Csig
    if np.any(np.diag(resid_cov) <= 1e-4):
        raise ValueError(f"infeasible targets; residual var<=0: {np.diag(resid_cov)} "
                         f"(reduce target magnitudes; r'Rg^-1 r must be < 1)")
    raw = resid_against(rng.standard_normal((n, m)), G1)
    raw_w = raw @ np.linalg.cholesky(np.linalg.inv(np.cov(raw.T, bias=True).reshape(m, m))).T
    resid = raw_w @ np.linalg.cholesky(nearest_pd(resid_cov)).T
    return sig + resid                                                  # var=1 per col


# ---------------------------------------------------------- Likert / items
def likertize(Lstd, mean, sd, k_items, item_sigma, lo=1, hi=7,
              extra=None, reverse_idx=(), rng=None):
    """Latent -> k integer Likert items + composite(mean of items).

    extra      : optional additive raw-unit term per row (e.g. interaction
                 injection coef*zscale(z_x*z_w)); applied to the base.
    reverse_idx: 1-based item indices stored reverse-coded as (lo+hi)-aligned;
                 returns BOTH raw (reverse) and the aligned value via the
                 composite. For simple scales leave empty.
    Returns (items (n,k) int, composite (n,) float).
    """
    rng = rng or np.random.default_rng()
    Lstd = np.asarray(Lstd, float)
    base = mean + sd * (Lstd - Lstd.mean()) / (Lstd.std(ddof=0) or 1.0)
    if extra is not None:
        base = base + np.asarray(extra, float)
    aligned = np.column_stack([
        np.clip(np.round(base + rng.normal(0, item_sigma, len(Lstd))), lo, hi)
        for _ in range(k_items)]).astype(int)
    items = aligned.copy()
    for j in reverse_idx:                       # store raw reverse; composite uses aligned
        items[:, j - 1] = (lo + hi) - aligned[:, j - 1]
    composite = aligned.mean(1)                 # composite from aligned values
    return items, composite


# ---------------------------------- outer-calibrated multi-composite rebuild
def rebuild_block(df, given_cols, specs, pair_corr=None, item_sigma=0.66,
                  outer=9, lr=0.85, lo=1, hi=7, rng=None):
    """Calibrate a set of composites so each Likert COMPOSITE hits its target
    correlations (corrects Likert rounding attenuation via an outer loop).

    given_cols : predictor column names in df (used standardized).
    specs      : list of dicts with keys:
                 items (col names), comp (name), mean, sd, tgt (len==given_cols),
                 optional extra (raw-unit additive array, e.g. interaction).
    pair_corr  : target corr among the comps (default identity).
    Mutates df in place (writes items + comp). Returns achieved corr matrix
    (m x len(given_cols)).
    """
    rng = rng or np.random.default_rng(20260531)
    gz = np.column_stack([zscale(df[c].values) for c in given_cols])
    desired = [np.asarray(s["tgt"], float) for s in specs]
    dpair = np.eye(len(specs)) if pair_corr is None else np.asarray(pair_corr, float)
    eff = [d.copy() for d in desired]
    eff_pair = dpair.copy()
    built = None
    for _ in range(outer):
        lat = build_latents(gz, eff, eff_pair, rng=rng)
        comps, items_all = [], []
        for j, s in enumerate(specs):
            it, comp = likertize(lat[:, j], s["mean"], s["sd"], len(s["items"]),
                                 item_sigma, lo, hi, extra=s.get("extra"),
                                 reverse_idx=s.get("reverse_idx", ()), rng=rng)
            items_all.append(it); comps.append(comp)
        comps = np.column_stack(comps)
        ach = np.array([[np.corrcoef(comps[:, j], gz[:, g])[0, 1]
                         for g in range(gz.shape[1])] for j in range(len(specs))])
        for j in range(len(specs)):
            eff[j] = eff[j] + lr * (desired[j] - ach[j])
        for a in range(len(specs)):
            for b in range(a + 1, len(specs)):
                cur = np.corrcoef(comps[:, a], comps[:, b])[0, 1]
                d = lr * (dpair[a, b] - cur)
                eff_pair[a, b] += d; eff_pair[b, a] += d
        built = (items_all, comps)
    items_all, comps = built
    for j, s in enumerate(specs):
        for ci, col in enumerate(s["items"]):
            df[col] = items_all[j][:, ci]
        df[s["comp"]] = comps[:, j]
    return ach


# ------------------------------------------------- multilevel ICC rebuild
def _var_components(y, codes, gn, kg, N):
    y = np.asarray(y, float); grand = y.mean()
    gm = np.bincount(codes, weights=y) / gn
    ssb = (gn * (gm - grand) ** 2).sum()
    ssw = ((y - gm[codes]) ** 2).sum()
    n0 = (N - (gn ** 2).sum() / N) / (kg - 1)
    return (ssb / (kg - 1) - ssw / (N - kg)) / n0, ssw / (N - kg)


def icc_rebuild(df, group_col, given_cols, item_cols, comp_col, mean, total_sd,
                icc, r_tgt, sign=1, shared=None, halo_scale=1.0,
                rho_l=0.655, rho_d=0.384, item_sigma=0.75, n_iter=14, outer=6,
                lo=1, hi=7, rng=None, write=True):
    """Build a group-nested (multilevel) composite that hits target correlations
    `r_tgt` against `given_cols` AND a target group-level ICC, with genuine
    within-group variance. Optional `shared` orthogonal halo factor (pass the
    SAME array with opposite `sign` to two calls to induce a cross-corr between
    the two composites — calibrate `halo_scale` to hit it).

    Returns the composite. If write=False, does not modify df (use for
    calibrating halo_scale).
    """
    rng = rng or np.random.default_rng(771)
    codes, uniq = np.asarray(df[group_col].factorize()[0]), df[group_col].nunique()
    kg = uniq; gn = np.bincount(codes); N = len(df)
    gmean = lambda y: (np.bincount(codes, weights=y) / gn)[codes]
    Xp = np.column_stack([zscale(df[c].values) for c in given_cols])
    lead = [np.bincount(codes, weights=Xp[:, j]) / gn for j in range(Xp.shape[1])]
    Bl = np.column_stack([np.ones(kg)] + lead)
    Bd = np.column_stack([np.ones(N)] + [Xp[:, j] - lead[j][codes] for j in range(Xp.shape[1])])
    S_l = shared if shared is not None else resid_against(rng.normal(size=kg), Bl)
    S_d = resid_against(rng.normal(size=N), Bd)
    ind_l = resid_against(rng.normal(size=kg), Bl)
    ind_d = resid_against(rng.normal(size=N), Bd)
    inoise = [rng.normal(0, item_sigma, N) for _ in item_cols]
    VB, VW = icc * total_sd ** 2, (1 - icc) * total_sd ** 2
    rl = float(np.clip(halo_scale * rho_l, -0.985, 0.985))
    rd = float(np.clip(halo_scale * rho_d, -0.985, 0.985))
    eb = (sign * rl * S_l + np.sqrt(1 - rl ** 2) * ind_l)[codes]; eb -= eb.mean()
    ew = sign * rd * S_d + np.sqrt(1 - rd ** 2) * ind_d; ew -= gmean(ew)
    vb_eb, _ = _var_components(eb, codes, gn, kg, N)
    _, vw_ew = _var_components(ew, codes, gn, kg, N)
    Rinv = np.linalg.inv(np.corrcoef(Xp.T))
    r_eff = np.asarray(r_tgt, float); latent = None
    for _ in range(outer):
        s2 = float(r_eff @ Rinv @ r_eff)
        sig = Xp @ (Rinv @ r_eff); sig = (sig - sig.mean()) / sig.std()
        sig_part = total_sd * np.sqrt(s2) * sig
        vb_sig, _ = _var_components(sig_part, codes, gn, kg, N)
        _, vw_sig = _var_components(sig_part, codes, gn, kg, N)
        cb = np.sqrt(max(VB - vb_sig, 1e-9) / max(vb_eb, 1e-9))
        cw = np.sqrt(max(VW - vw_sig - item_sigma ** 2 / len(item_cols), 1e-9) / max(vw_ew, 1e-9))
        for _ in range(n_iter):
            latent = mean + sig_part + cb * eb + cw * ew
            comp = np.column_stack([np.clip(np.round(latent + inoise[j]), lo, hi)
                                    for j in range(len(item_cols))]).mean(1)
            vb, vw = _var_components(comp, codes, gn, kg, N)
            cb *= np.sqrt(VB / max(vb, 1e-6))
            cw *= np.sqrt(max(VW - item_sigma ** 2 / len(item_cols), 1e-9) /
                          max(vw - item_sigma ** 2 / len(item_cols), 1e-6))
        comp = np.column_stack([np.clip(np.round(latent + inoise[j]), lo, hi)
                                for j in range(len(item_cols))]).mean(1)
        ach = np.array([np.corrcoef(comp, Xp[:, c])[0, 1] for c in range(Xp.shape[1])])
        r_eff = r_eff + (np.asarray(r_tgt) - ach) * 0.9
    items = np.column_stack([np.clip(np.round(latent + inoise[j]), lo, hi)
                             for j in range(len(item_cols))]).astype(int)
    if write:
        for j, c in enumerate(item_cols):
            df[c] = items[:, j]
        df[comp_col] = items.mean(1)
    return items.mean(1)


# --------------------------------------------------------------- verify
def verify(df, checks, tol=0.02):
    """checks: list of (colA, colB, target_corr). Prints PASS/FAIL and returns
    True if all within tol."""
    allok = True
    for a, b, t in checks:
        r = df[[a, b]].corr().iloc[0, 1]
        good = abs(r - t) < tol
        allok &= good
        print(f"  [{'PASS' if good else '**FAIL**'}] corr({a},{b})={r:+.3f} "
              f"target={t:+.3f} d={r - t:+.3f}")
    print(f"ALL WITHIN {tol}: {allok}")
    return allok


def cronbach_alpha(item_matrix):
    """Quick Cronbach's alpha from an (n,k) item matrix — use to confirm
    displayed alpha == computed alpha (golden rule)."""
    X = np.asarray(item_matrix, float); k = X.shape[1]
    var_items = X.var(0, ddof=1).sum()
    var_total = X.sum(1).var(ddof=1)
    return k / (k - 1) * (1 - var_items / var_total)


# ============================================================================
# General-purpose calibration (distribution-free; not survey-specific)
# numpy + stdlib only (no scipy). Normal CDF/inv-CDF via statistics.NormalDist.
# ============================================================================
from statistics import NormalDist as _ND
_nd = _ND()
def _phi(z):     return np.array([_nd.cdf(float(v))     for v in np.ravel(z)]).reshape(np.shape(z))
def _phi_inv(p): return np.array([_nd.inv_cdf(float(v)) for v in np.ravel(p)]).reshape(np.shape(p))
def _ranks(x):   # average ranks 1..n
    order = np.argsort(np.argsort(np.asarray(x, float)))
    return order + 1.0


def rescale(x, mean=None, sd=None, lo=None, hi=None):
    """Linear-rescale x to target mean/sd (each optional), then optional clip."""
    x = np.asarray(x, float)
    if sd is not None:
        s = x.std(ddof=0) or 1.0
        x = (x - x.mean()) / s * sd
    if mean is not None:
        x = x - x.mean() + mean
    if lo is not None or hi is not None:
        x = np.clip(x, -np.inf if lo is None else lo, np.inf if hi is None else hi)
    return x


def tune_scalar(make_and_measure, target, x0=0.0, lo=-5.0, hi=5.0, tol=1e-3, iters=60):
    """Hit ANY measurable target by tuning one knob. make_and_measure(x)->metric.
    Secant if endpoints same-signed, else bisection. The robust fallback when no
    closed form exists (skewness, AUC, OR, prevalence, Gini, ...)."""
    f = lambda x: make_and_measure(x) - target
    fa, fb = f(lo), f(hi)
    if fa * fb <= 0:
        a, b = lo, hi
        for _ in range(iters):
            m = 0.5 * (a + b); fm = f(m)
            if abs(fm) < tol: return m
            if fa * fm > 0: a, fa = m, fm
            else:           b = m
        return 0.5 * (a + b)
    x, xp, fp = x0, x0 + 1e-2, f(x0 + 1e-2)
    for _ in range(iters):
        fx = f(x)
        if abs(fx) < tol: return x
        denom = fx - fp
        if abs(denom) < 1e-12:                # secant degenerate -> small step
            x, xp, fp = x + 0.1, x, fx; continue
        step = fx * (x - xp) / denom
        step = float(np.clip(step, -abs(hi - lo), abs(hi - lo)))   # clip
        x, xp, fp = float(np.clip(x - step, lo, hi)), x, fx
    return x


def match_marginal(x, target_ppf):
    """Reshape x to an arbitrary target marginal by quantile (rank) mapping —
    preserves the rank order of x. target_ppf: callable(q in (0,1)) -> values
    (e.g. lambda q: mu+sd*_phi_inv(q); or lambda q: np.quantile(reference, q))."""
    x = np.asarray(x, float)
    q = (_ranks(x) - 0.5) / len(x)
    return np.asarray(target_ppf(q), float)


def iman_conover(X, target_corr, rng=None):
    """Distribution-free: reorder values WITHIN each column so the columns attain
    the target (rank) correlation, leaving every marginal EXACTLY unchanged.
    X: (n,k) array. Use when columns already have the distributions you want."""
    rng = rng or np.random.default_rng()
    X = np.asarray(X, float); n, k = X.shape
    P = np.linalg.cholesky(nearest_pd(target_corr))
    S = np.column_stack([_phi_inv((rng.permutation(n) + 1) / (n + 1)) for _ in range(k)])
    S = S @ np.linalg.inv(np.linalg.cholesky(np.cov(S, rowvar=False)))   # decorrelate
    T = S @ P.T                                                          # induce target
    out = np.empty_like(X)
    for j in range(k):
        # place X's r-th smallest value where T column has rank r → matches T's
        # rank pattern (induces target corr) while keeping X_j's marginal exactly
        out[:, j] = np.sort(X[:, j])[np.argsort(np.argsort(T[:, j]))]
    return out


def gaussian_copula(n, corr, ppfs, rng=None):
    """Sample n rows with given target correlation `corr` (on the normal scores)
    and given marginals via inverse-CDFs `ppfs` (list of callables q->values).
    NORTA. If you need a specific Pearson on the *marginals*, wrap the relevant
    corr entry in tune_scalar to hit it."""
    rng = rng or np.random.default_rng()
    k = len(ppfs)
    Z = rng.standard_normal((n, k)) @ np.linalg.cholesky(nearest_pd(corr)).T
    U = _phi(Z)
    return np.column_stack([np.asarray(ppfs[j](U[:, j]), float) for j in range(k)])


def shift_group_effect(x, group, target_d, ref_group=None):
    """Shift group means so the (two-group) Cohen's d hits target_d, preserving
    pooled SD and overall spread shape. group: array of labels. For >2 groups,
    pass ref_group and call per comparison group."""
    x = np.asarray(x, float).copy(); group = np.asarray(group)
    labs = np.unique(group)
    g0 = ref_group if ref_group is not None else labs[0]
    pooled = np.sqrt(np.mean([x[group == g].var(ddof=1) for g in labs]))
    for g in labs:
        if g == g0: continue
        cur_d = (x[group == g].mean() - x[group == g0].mean()) / (pooled or 1.0)
        x[group == g] += (target_d - cur_d) * pooled
    return x


def inject_missing(x, rate, mechanism="MCAR", by=None, rng=None):
    """Set `rate` fraction of x to NaN. MCAR=random; MAR=prob∝rank(by);
    MNAR=prob∝rank(x)."""
    rng = rng or np.random.default_rng()
    x = np.asarray(x, float).copy(); n = len(x)
    if mechanism == "MCAR":
        p = np.full(n, rate)
    else:
        drv = np.asarray(by if (mechanism == "MAR" and by is not None) else x, float)
        w = (_ranks(drv)) / n
        p = w / w.mean() * rate
    mask = rng.random(n) < np.clip(p, 0, 1)
    x[mask] = np.nan
    return x


def inject_outliers(x, rate, k=4.0, rng=None):
    """Push `rate` fraction of points to mean ± k*SD (random side)."""
    rng = rng or np.random.default_rng()
    x = np.asarray(x, float).copy(); n = len(x)
    m, s = np.nanmean(x), np.nanstd(x)
    idx = rng.choice(n, max(1, int(round(rate * n))), replace=False)
    x[idx] = m + np.where(rng.random(len(idx)) < 0.5, -1, 1) * k * s
    return x


def rake(df, margins, weight0=None, iters=50, tol=1e-6):
    """Iterative proportional fitting (raking): return per-row weights so the
    weighted marginals of each column match targets. margins: {col: {value:
    target_proportion}}. Changes weights, not the data (use for survey weighting
    / matching a population)."""
    n = len(df); w = np.ones(n) if weight0 is None else np.asarray(weight0, float).copy()
    for _ in range(iters):
        w0 = w.copy()
        for col, tgt in margins.items():
            vals = df[col].values
            for v, p in tgt.items():
                m = (vals == v)
                cur = w[m].sum() / w.sum()
                if cur > 0:
                    w[m] *= p / cur
        if np.max(np.abs(w - w0)) < tol:
            break
    return w * n / w.sum()


def dp_noise(x, sensitivity, epsilon, rng=None):
    """Add Laplace(sensitivity/epsilon) noise for ε-differential privacy."""
    rng = rng or np.random.default_rng()
    return np.asarray(x, float) + rng.laplace(0.0, sensitivity / epsilon, size=np.shape(x))


# ============================================================================
# Non-normal moment matching & model-implied generation (simulation-grade)
# ============================================================================
def _skew(x):
    x = np.asarray(x, float); m = x.mean(); s = x.std()
    return np.mean(((x - m) / (s or 1)) ** 3)
def _kurt(x):  # excess kurtosis
    x = np.asarray(x, float); m = x.mean(); s = x.std()
    return np.mean(((x - m) / (s or 1)) ** 4) - 3.0


def fleishman_coef(skew, kurt, iters=200, tol=1e-10):
    """Fleishman power-method coefficients (a,b,c,d) for y=a+bz+cz²+dz³, z~N(0,1),
    so y has mean 0, var 1, target skewness & excess kurtosis. Newton solve.
    Raises if (skew,kurt) is outside Fleishman's feasible region."""
    g1, g2 = float(skew), float(kurt)
    def F(v):
        b, c, d = v
        return np.array([
            b*b + 6*b*d + 2*c*c + 15*d*d - 1,
            2*c*(b*b + 24*b*d + 105*d*d + 2) - g1,
            24*(b*d + c*c*(1 + b*b + 28*b*d) + d*d*(12 + 48*b*d + 141*c*c + 225*d*d)) - g2,
        ])
    v = np.array([1.0, g1 / 6.0, 0.01])
    for _ in range(iters):
        f = F(v)
        if np.max(np.abs(f)) < tol:
            break
        J = np.zeros((3, 3)); h = 1e-6
        for j in range(3):
            vp = v.copy(); vp[j] += h
            J[:, j] = (F(vp) - f) / h
        try:
            v = v - np.linalg.solve(J, f)
        except np.linalg.LinAlgError:
            break
    if np.max(np.abs(F(v))) > 1e-4:
        raise ValueError(f"infeasible (skew={g1}, kurt={g2}) for Fleishman; "
                         f"need kurt > skew^2*? (try larger kurtosis)")
    b, c, d = v
    return (-c, b, c, d)


def fleishman(z, skew, kurt):
    """Transform standard-normal z into a variable with target skew/kurtosis."""
    a, b, c, d = fleishman_coef(skew, kurt)
    return a + b * z + c * z ** 2 + d * z ** 3


def nonnormal_data(n, corr, skews, kurts, means=None, sds=None, rng=None):
    """Vale-Maurelli: multivariate data with target Pearson `corr` AND per-column
    target skewness/kurtosis (Fleishman marginals). Solves the intermediate
    normal correlation per pair so the post-transform Pearson hits `corr`."""
    rng = rng or np.random.default_rng()
    k = len(skews)
    coef = [fleishman_coef(skews[j], kurts[j]) for j in range(k)]
    Ri = np.eye(k)
    for i in range(k):
        for j in range(i + 1, k):
            _, b1, c1, d1 = coef[i]; _, b2, c2, d2 = coef[j]
            # target = ρi*(b1b2+3b1d2+3d1b2+9d1d2) + ρi²*(2c1c2) + ρi³*(6d1d2)
            A = b1*b2 + 3*b1*d2 + 3*d1*b2 + 9*d1*d2
            B = 2*c1*c2; Cc = 6*d1*d2; t = corr[i][j]
            rho = tune_scalar(lambda r: A*r + B*r*r + Cc*r**3, t, x0=t, lo=-0.999, hi=0.999)
            Ri[i, j] = Ri[j, i] = np.clip(rho, -0.999, 0.999)
    Z = rng.standard_normal((n, k)) @ np.linalg.cholesky(nearest_pd(Ri)).T
    X = np.column_stack([coef[j][0] + coef[j][1]*Z[:, j] + coef[j][2]*Z[:, j]**2
                         + coef[j][3]*Z[:, j]**3 for j in range(k)])
    if sds is not None:   X = X * np.asarray(sds)
    if means is not None: X = X + np.asarray(means)
    return X


def factor_model_sample(n, loadings, factor_corr=None, uniqueness=None, rng=None):
    """Generate item data from a (confirmatory) factor model:
        X = F @ Λ' + E,   F ~ N(0, factor_corr),  E ~ N(0, diag(uniqueness)).
    loadings: (n_items, n_factors) Λ. uniqueness default = 1 - rowsum(λ²) (so item
    var≈1). Returns (n, n_items). Generalizes 'build items with target loadings/
    reliability' — composite reliability follows from the loadings."""
    rng = rng or np.random.default_rng()
    Lam = np.asarray(loadings, float); p, m = Lam.shape
    Rf = np.eye(m) if factor_corr is None else nearest_pd(factor_corr)
    F = rng.standard_normal((n, m)) @ np.linalg.cholesky(Rf).T
    if uniqueness is None:
        uniqueness = np.clip(1 - (Lam ** 2).sum(1), 1e-3, None)
    E = rng.standard_normal((n, p)) * np.sqrt(np.asarray(uniqueness))
    return F @ Lam.T + E


def fit_from_reference(ref_df, cols=None, rng=None):
    """Model a real dataset then synthesize: capture each column's empirical
    marginal + the rank-correlation, return a sampler(n)->DataFrame producing
    synthetic rows with matching marginals & dependence (Gaussian-copula on
    empirical quantiles). For privacy/augmentation/testing."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    cols = list(cols or ref_df.columns)
    ref = ref_df[cols].dropna()
    # normal-score correlation
    Zr = np.column_stack([_phi_inv((_ranks(ref[c].values) - 0.5) / len(ref)) for c in cols])
    R = np.corrcoef(Zr.T)
    refvals = {c: np.sort(ref[c].values) for c in cols}

    def sampler(n):
        Z = rng.standard_normal((n, len(cols))) @ np.linalg.cholesky(nearest_pd(R)).T
        U = _phi(Z)
        out = {}
        for j, c in enumerate(cols):
            q = np.clip(U[:, j], 1e-6, 1 - 1e-6)
            out[c] = np.quantile(refvals[c], q)
        return pd.DataFrame(out)
    return sampler


def report(df, cols=None):
    """Quick diagnostics: per-column mean/sd/skew/kurt/min/max/missing + Pearson
    & Spearman correlation matrices. Use to eyeball realism / spot 'tells'."""
    cols = list(cols or df.select_dtypes("number").columns)
    print("col                  mean      sd    skew    kurt     min     max   miss%")
    for c in cols:
        x = df[c].values.astype(float); v = x[~np.isnan(x)]
        print(f"{c:18s} {v.mean():8.3f} {v.std():7.3f} {_skew(v):7.3f} {_kurt(v):7.3f} "
              f"{v.min():7.2f} {v.max():7.2f} {100*np.isnan(x).mean():6.1f}")
    P = df[cols].corr().values
    S = df[cols].corr(method="spearman").values
    print("Pearson corr:\n", np.round(P, 2))
    print("Spearman corr:\n", np.round(S, 2))


def ks_stat(x, target_ppf, grid=200):
    """Kolmogorov-Smirnov distance between sample x and a target distribution
    (given its ppf). Small = good fit. No scipy needed."""
    x = np.sort(np.asarray(x, float))
    q = (np.arange(1, len(x) + 1)) / len(x)
    tq = target_ppf(np.linspace(1e-4, 1 - 1e-4, grid))
    # empirical CDF of x at tq vs uniform
    ecdf = np.searchsorted(x, tq, side="right") / len(x)
    return float(np.max(np.abs(ecdf - np.linspace(1e-4, 1 - 1e-4, grid))))


# ============================================================================
# Time / sequences / events / causal / experimental / mixed-type
# ============================================================================
def ts_ar(n, ar=(0.7,), trend=0.0, seasonal=None, sd=1.0, mean=0.0, rng=None):
    """AR(p) time series: x_t = Σφ_i x_{t-i} + ε_t, plus optional linear trend
    (per step) and seasonal=(period,amplitude). Returns (n,) array."""
    rng = rng or np.random.default_rng()
    p = len(ar); x = np.zeros(n + p)
    e = rng.normal(0, sd, n + p)
    for t in range(p, n + p):
        x[t] = sum(ar[i] * x[t - 1 - i] for i in range(p)) + e[t]
    out = x[p:] + mean + trend * np.arange(n)
    if seasonal:
        per, amp = seasonal
        out = out + amp * np.sin(2 * np.pi * np.arange(n) / per)
    return out


def panel_data(n_units, n_periods, icc=0.3, ar1=0.5, noise_sd=1.0,
               time_trend=0.0, rng=None):
    """Generate long-format panel: (n_units * n_periods) rows with `unit`,
    `time`, `y`. y = unit_FE + time_trend*t + AR(1) within-unit shock.
    Between-unit ICC ≈ `icc`."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    fe_sd = np.sqrt(icc); ws_sd = np.sqrt(max(1 - icc, 1e-6))
    rows = []
    for u in range(n_units):
        a = rng.normal(0, fe_sd); eps = rng.normal(0, ws_sd, n_periods); y_prev = 0
        for t in range(n_periods):
            y = a + time_trend * t + ar1 * y_prev + noise_sd * eps[t]
            rows.append((u, t, y)); y_prev = y - a - time_trend * t
    return pd.DataFrame(rows, columns=["unit", "time", "y"])


def survival_data(n, baseline_rate=0.1, hazard_ratios=None, X=None,
                  censor_rate=0.2, dist="exp", weibull_shape=1.5, rng=None):
    """Generate (time, event, X) with target hazard ratios. λ(x)=λ0·exp(βx);
    T~Exp(λ) or Weibull. Independent Exp censoring at rate `censor_rate`.
    Returns DataFrame. hazard_ratios per column of X give exp(β)."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    if X is None: X = np.zeros((n, 0))
    X = np.asarray(X, float).reshape(n, -1)
    beta = np.log(np.asarray(hazard_ratios, float)) if hazard_ratios is not None else np.zeros(X.shape[1])
    lam = baseline_rate * np.exp(X @ beta)
    if dist == "exp":
        T = rng.exponential(1 / lam)
    else:
        U = rng.random(n); T = (-np.log(1 - U) / lam) ** (1 / weibull_shape)
    C = rng.exponential(1 / max(censor_rate, 1e-9), n)
    obs = np.minimum(T, C); event = (T <= C).astype(int)
    out = pd.DataFrame({"time": obs, "event": event})
    for j in range(X.shape[1]):
        out[f"x{j+1}"] = X[:, j]
    return out


def markov_chain(n, transition, init=None, states=None, rng=None):
    """Sample a length-n sequence from a Markov chain with transition matrix P
    (k,k) and optional initial distribution `init`. `states` labels the states."""
    rng = rng or np.random.default_rng()
    P = np.asarray(transition, float); k = P.shape[0]
    P = P / P.sum(1, keepdims=True)
    states = list(range(k)) if states is None else list(states)
    init = np.full(k, 1 / k) if init is None else np.asarray(init) / np.sum(init)
    seq = np.empty(n, dtype=object)
    s = rng.choice(k, p=init)
    for t in range(n):
        seq[t] = states[s]; s = rng.choice(k, p=P[s])
    return seq


def fit_markov(sequences, states=None):
    """Estimate transition matrix from one or more sequences (lists/arrays)."""
    seqs = [list(s) for s in (sequences if isinstance(sequences[0], (list, np.ndarray)) else [sequences])]
    sset = sorted(set(x for s in seqs for x in s)) if states is None else list(states)
    idx = {s: i for i, s in enumerate(sset)}; k = len(sset)
    C = np.zeros((k, k))
    for s in seqs:
        for a, b in zip(s[:-1], s[1:]): C[idx[a], idx[b]] += 1
    R = C.sum(1, keepdims=True); R[R == 0] = 1
    return C / R, sset


def count_data(n, mean, dispersion=None, zero_prob=0.0, rng=None):
    """Counts with target mean. dispersion=None→Poisson; dispersion>0→NegBin
    (variance = mean + mean²/dispersion, smaller k = more over-dispersion);
    zero_prob>0 adds a zero-inflation mixture."""
    rng = rng or np.random.default_rng()
    if dispersion is None:
        x = rng.poisson(mean, n)
    else:
        # NegBin via gamma-mixture: λ ~ Gamma(dispersion, mean/dispersion)
        lam = rng.gamma(dispersion, mean / dispersion, n)
        x = rng.poisson(lam)
    if zero_prob > 0:
        x = np.where(rng.random(n) < zero_prob, 0, x)
    return x


def dag_sample(n, nodes, rng=None):
    """Structural Causal Model. `nodes`: ordered list of (name, fn) where fn
    takes a dict of already-generated arrays and returns the new column. The
    order encodes the DAG (each fn only references earlier names).

    Example:
        dag_sample(5000, [
          ("U", lambda d, n, r: r.standard_normal(n)),
          ("X", lambda d, n, r: 0.6*d["U"] + r.standard_normal(n)),
          ("Y", lambda d, n, r: 0.4*d["X"] + 0.5*d["U"] + r.standard_normal(n)),
        ])  # X→Y with confounder U; regressing Y~X without adjusting for U is biased.
    """
    import pandas as pd
    rng = rng or np.random.default_rng()
    data = {}
    for name, fn in nodes:
        data[name] = np.asarray(fn(data, n, rng), float)
    return pd.DataFrame(data)


def ab_test_data(n_per_arm, baseline=0.0, effect=0.2, sd=1.0, metric="continuous",
                 arm_names=("control", "treatment"), rng=None):
    """Simulate an A/B test. metric='continuous' (Normal) | 'binary' (Bernoulli
    with effect=lift in prob) | 'count' (Poisson with effect=lift in mean)."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    rows = []
    for i, arm in enumerate(arm_names):
        mu = baseline + (effect if i > 0 else 0)
        if metric == "continuous":
            y = rng.normal(mu, sd, n_per_arm)
        elif metric == "binary":
            y = (rng.random(n_per_arm) < np.clip(mu, 0, 1)).astype(int)
        else:
            y = rng.poisson(max(mu, 1e-6), n_per_arm)
        for v in y: rows.append((arm, v))
    return pd.DataFrame(rows, columns=["arm", "y"])


def classification_dataset(n, n_features=5, target_auc=0.8, class_balance=0.5,
                           feature_corr=None, rng=None):
    """Generate features + binary label with target AUC and class balance. The
    label is built from a noisy linear score of the features; AUC is measured
    using the noiseless feature signal (the achievable AUC any classifier sees).
    Tunes signal-to-noise to hit `target_auc`; threshold pins `class_balance`."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    R = feature_corr if feature_corr is not None else np.eye(n_features)
    X = rng.standard_normal((n, n_features)) @ np.linalg.cholesky(nearest_pd(R)).T
    w = rng.standard_normal(n_features); w = w / np.linalg.norm(w)
    sig = X @ w
    noise = rng.standard_normal(n)                           # fix noise

    def auc_for_a(a):
        score_for_y = a * sig + noise
        thr = np.quantile(score_for_y, 1 - class_balance)
        y = (score_for_y > thr).astype(int)
        o = np.argsort(sig); ys = y[o]
        npos = int(ys.sum()); nneg = len(ys) - npos
        if npos == 0 or nneg == 0: return 0.5
        return (np.arange(1, len(ys) + 1)[ys == 1].sum()
                - npos * (npos + 1) / 2) / (npos * nneg)

    a = tune_scalar(auc_for_a, target_auc, x0=2.0, lo=0.01, hi=30, tol=2e-3)
    score_for_y = a * sig + noise
    thr = np.quantile(score_for_y, 1 - class_balance)
    y = (score_for_y > thr).astype(int)
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(n_features)])
    df["y"] = y
    return df


def mixed_copula(n, columns, target_corr, rng=None):
    """Joint generation for MIXED continuous + binary + ordinal columns with a
    target latent (rank) correlation matrix. `columns`: list of dicts:
        {name, type: 'continuous'|'binary'|'ordinal', ppf|p|cuts}
      continuous → ppf(q)→values; binary → p (positive prob);
      ordinal → cuts: sorted thresholds in (0,1) giving the cumulative cell probs."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    k = len(columns)
    Z = rng.standard_normal((n, k)) @ np.linalg.cholesky(nearest_pd(target_corr)).T
    out = {}
    for j, c in enumerate(columns):
        u = _phi(Z[:, j])
        if c["type"] == "continuous":
            out[c["name"]] = np.asarray(c["ppf"](u), float)
        elif c["type"] == "binary":
            out[c["name"]] = (u >= (1 - c["p"])).astype(int)
        else:                                              # ordinal: thresholds in (0,1)
            cuts = list(c["cuts"])
            cat = np.zeros(n, dtype=int)
            for ci, thr in enumerate(cuts, start=1):
                cat[u > thr] = ci
            out[c["name"]] = cat
    return pd.DataFrame(out)


def bootstrap_perturb(df, n=None, rng=None):
    """Resample df rows with replacement (preserves joint distribution).
    Useful for robustness checks / generating bootstrap replicates."""
    rng = rng or np.random.default_rng()
    n = n or len(df)
    return df.iloc[rng.integers(0, len(df), n)].reset_index(drop=True)


def discriminability(real_df, synth_df, cols=None, n_iter=400, lr=0.05):
    """Train a tiny logistic regression to distinguish real from synthetic on
    `cols`. Returns AUC on a held-out 25% split. AUC ~0.5 = indistinguishable
    (good synthesis); >>0.6 = the synthesizer is leaking."""
    rng = np.random.default_rng(0)
    cols = list(cols or set(real_df.select_dtypes("number").columns) &
                       set(synth_df.select_dtypes("number").columns))
    R = real_df[cols].dropna().values; S = synth_df[cols].dropna().values
    X = np.vstack([R, S]); y = np.concatenate([np.ones(len(R)), np.zeros(len(S))])
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    X = np.column_stack([np.ones(len(X)), X])
    perm = rng.permutation(len(X)); sp = int(0.75 * len(X))
    Xtr, ytr = X[perm[:sp]], y[perm[:sp]]; Xte, yte = X[perm[sp:]], y[perm[sp:]]
    w = np.zeros(X.shape[1])
    for _ in range(n_iter):
        p = 1 / (1 + np.exp(-Xtr @ w))
        w -= lr * Xtr.T @ (p - ytr) / len(Xtr)
    s = Xte @ w
    ord_ = np.argsort(s); ys = yte[ord_]
    n_pos = ys.sum(); n_neg = len(ys) - n_pos
    if n_pos == 0 or n_neg == 0: return 0.5
    return (np.arange(1, len(ys) + 1)[ys == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def heteroscedastic_noise(x_pred, base_sd=1.0, slope=0.5, rng=None):
    """Noise with sd = base_sd + slope*|x_pred|. Returns array same shape."""
    rng = rng or np.random.default_rng()
    sd = base_sd + slope * np.abs(np.asarray(x_pred, float))
    return rng.normal(0, sd)


def ipw_weights(treatment, propensity):
    """Inverse probability of treatment weights: 1/p for treated, 1/(1-p) for control.
    Clip tiny propensities to avoid extreme weights."""
    t = np.asarray(treatment, float); p = np.clip(np.asarray(propensity, float), 0.02, 0.98)
    return t / p + (1 - t) / (1 - p)


def dirichlet_compositional(n, alphas, rng=None):
    """Compositional data (rows sum to 1) from Dirichlet(alphas). Returns (n,k)."""
    rng = rng or np.random.default_rng()
    return rng.dirichlet(np.asarray(alphas, float), size=n)
