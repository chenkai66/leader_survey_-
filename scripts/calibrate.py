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


# -------------------------- composite-preserving reliability/CFI calibration

def sum_preserving_round(cont, target, lo=1, hi=7):
    """Round a continuous vector to integers in [lo,hi] whose sum == target.

    Largest-remainder style: floor, then add/subtract 1 from the items whose
    continuous value most over/under-shoots, skipping items already at a
    boundary. Guarantees the integer mean equals target/len exactly UNLESS
    boundary clipping makes it infeasible (rare for small perturbations).
    """
    cont = np.asarray(cont, float)
    fl = np.clip(np.round(cont), lo, hi).astype(int)
    for _ in range(80):
        deficit = int(round(target - fl.sum()))
        if deficit == 0:
            break
        if deficit > 0:
            cand = [j for j in range(len(fl)) if fl[j] < hi]
            if not cand:
                break
            fl[max(cand, key=lambda j: cont[j] - fl[j])] += 1
        else:
            cand = [j for j in range(len(fl)) if fl[j] > lo]
            if not cand:
                break
            fl[min(cand, key=lambda j: cont[j] - fl[j])] -= 1
    return fl


def raw_cronbach_alpha(items):
    """Raw (unstandardized) Cronbach's alpha for an (n,k) integer item matrix."""
    X = np.asarray(items, float)
    k = X.shape[1]
    iv = X.var(axis=0, ddof=1).sum()
    tv = X.sum(axis=1).var(ddof=1)
    return (k / (k - 1)) * (1 - iv / tv)


def calibrate_item_reliability(composite, k_items, target_alpha,
                               doublet_gamma=0.0, lo=1, hi=7,
                               reverse_idx=(), rng=None, n_search=22):
    """Regenerate k Likert items AROUND a FIXED composite so that the items
    hit a target Cronbach's alpha (and, via doublet_gamma, a target single-
    factor CFA misfit) WHILE the composite (row mean) is preserved EXACTLY.

    Why this matters
    ----------------
    Path / correlation / ICC / SEM use the COMPOSITE (mean of items). Single-
    construct CFA, MCFA, CMV and alpha use the ITEMS. By regenerating items as
    `composite + zero-sum residual` and rounding with `sum_preserving_round`,
    the composite stays byte-identical -> every structural relationship is
    unchanged, and ONLY the item-level measurement models move. This lets you
    fix "displayed alpha/CFA != what the data computes" without disturbing an
    already-calibrated structural model.

    Two orthogonal knobs (they do NOT trade off — see SKILL note)
    -------------------------------------------------------------
    * target_alpha  : driven by INDEPENDENT zero-sum item noise (binary-searched
                      here). More independent noise -> lower inter-item r -> lower
                      alpha. Keeps the scale unidimensional (CFI stays high).
    * doublet_gamma : a zero-sum split-half "method" contrast added on top. It
                      creates correlated residuals -> single-factor CFA misfit
                      (lower CFI) WITHOUT raising alpha back. Set 0 for alpha-only.

    Hard limit
    ----------
    A NARROW composite SD forces HIGH alpha: items must average to a tight mean,
    so they cannot vary independently enough to lower inter-item correlation.
    If target_alpha is unreachable the search returns the closest achievable.

    Parameters
    ----------
    composite   : (n,) fixed composite values (mean of items). For parcel-based
                  composites, call per parcel preserving each parcel sum.
    k_items     : number of items.
    target_alpha: desired raw Cronbach alpha (approximate; "close enough" is fine).
    doublet_gamma: split-half contrast magnitude for CFA misfit (0 = none).
    reverse_idx : 1-based indices stored reverse-coded ((lo+hi)-value).

    Returns (items (n,k) int, achieved_alpha float). Composite == items.mean(1).
    """
    rng = rng or np.random.default_rng()
    # Derive the internal noise seed FROM the passed rng so that separate
    # constructs (each given its own rng / seed) get INDEPENDENT noise streams.
    # A fixed base here would make every construct share identical residuals ->
    # spurious position-aligned cross-construct item correlations.
    seed0 = int(rng.integers(1, 2 ** 31 - 1))
    C = np.asarray(composite, float)
    n = len(C)
    k = k_items
    n1 = k // 2
    n2 = k - n1
    Csum = np.round(C * k).astype(int)          # integer target sum per row

    def build(sigma, seed):
        r = np.random.default_rng(seed)
        u = r.standard_normal(n)                # doublet latent (shared per row)
        X = np.zeros((n, k), dtype=int)
        for i in range(n):
            e = r.standard_normal(k)
            e = e - e.mean()                    # zero-sum independent residual
            if e.std() > 1e-9:
                e = e / e.std() * sigma
            dbl = np.array([doublet_gamma if j < n1
                            else -doublet_gamma * (n1 / n2) for j in range(k)]) * u[i]
            X[i] = sum_preserving_round(C[i] + e + dbl, Csum[i], lo, hi)
        return X

    lo_s, hi_s, best = 0.01, 3.0, None
    for it in range(n_search):
        mid = (lo_s + hi_s) / 2
        X = build(mid, seed=seed0 + it)
        a = raw_cronbach_alpha(X)
        best = (X, a)
        if abs(a - target_alpha) < 0.008:
            break
        if a > target_alpha:                    # too reliable -> more noise
            lo_s = mid
        else:                                   # too noisy -> less
            hi_s = mid
    X, a = best
    for j in reverse_idx:
        X[:, j - 1] = (lo + hi) - X[:, j - 1]
    return X, a


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


# ============================================================================
# Simple regression / ANOVA / contingency one-liners
# ============================================================================
def regression_dataset(n, coefs, intercept=0.0, noise_sd=None, target_r2=None,
                       X_corr=None, X_means=None, X_sds=None, rng=None):
    """Linear regression sample: y = intercept + X@coefs + N(0, noise_sd).
    Supply EITHER noise_sd OR target_r2 (tunes noise_sd to hit R²).
    Returns DataFrame with x1..xk and y."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    coefs = np.asarray(coefs, float); k = len(coefs)
    R = np.eye(k) if X_corr is None else nearest_pd(X_corr)
    X = rng.standard_normal((n, k)) @ np.linalg.cholesky(R).T
    if X_means is not None: X = X + np.asarray(X_means)
    if X_sds   is not None: X = X * np.asarray(X_sds)
    signal = X @ coefs
    if target_r2 is not None:
        var_s = signal.var()
        noise_sd = np.sqrt(var_s * (1 - target_r2) / max(target_r2, 1e-9))
    y = intercept + signal + rng.normal(0, noise_sd if noise_sd is not None else 1.0, n)
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(k)])
    df["y"] = y
    return df


def logistic_dataset(n, coefs, intercept=0.0, X_corr=None, rng=None):
    """Binary logistic: P(y=1) = sigmoid(intercept + X@coefs). Returns df."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    coefs = np.asarray(coefs, float); k = len(coefs)
    R = np.eye(k) if X_corr is None else nearest_pd(X_corr)
    X = rng.standard_normal((n, k)) @ np.linalg.cholesky(R).T
    p = 1 / (1 + np.exp(-(intercept + X @ coefs)))
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(k)])
    df["y"] = (rng.random(n) < p).astype(int)
    return df


def multinomial_dataset(n, probs, rng=None):
    """K-class categorical with exact target proportions (deterministic allocation +
    shuffle)."""
    rng = rng or np.random.default_rng()
    probs = np.asarray(probs, float); probs = probs / probs.sum()
    counts = np.floor(probs * n).astype(int)
    counts[-1] += n - counts.sum()
    labels = np.concatenate([np.full(c, i) for i, c in enumerate(counts)])
    rng.shuffle(labels)
    return labels


def anova_design(n_per_cell, factor_levels, main_effects=None, interaction_effects=None,
                 sd=1.0, baseline=0.0, rng=None):
    """Balanced factorial design. factor_levels: dict {factor_name: n_levels}.
    main_effects: {factor: [delta per level]}.
    interaction_effects: {(f1,f2): 2D array [l1, l2]} (or callable).
    Returns DataFrame with factor columns + y."""
    import pandas as pd, itertools
    rng = rng or np.random.default_rng()
    factors = list(factor_levels.keys())
    levels = [list(range(factor_levels[f])) for f in factors]
    rows = []
    for combo in itertools.product(*levels):
        mu = baseline
        if main_effects:
            for fi, f in enumerate(factors):
                if f in main_effects:
                    mu += main_effects[f][combo[fi]]
        if interaction_effects:
            for (f1, f2), arr in interaction_effects.items():
                i1, i2 = factors.index(f1), factors.index(f2)
                v = arr(combo[i1], combo[i2]) if callable(arr) else arr[combo[i1]][combo[i2]]
                mu += v
        ys = rng.normal(mu, sd, n_per_cell)
        for y in ys:
            rows.append(list(combo) + [y])
    return pd.DataFrame(rows, columns=factors + ["y"])


def paired_data(n, baseline_mean=0.0, change_effect=0.5, within_corr=0.7,
                baseline_sd=1.0, post_sd=1.0, rng=None):
    """Pre/post paired data (within-subject design). target Pearson(pre,post)=within_corr.
    Returns df with pre, post, change."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    z = rng.standard_normal((n, 2)) @ np.linalg.cholesky([[1, within_corr], [within_corr, 1]]).T
    pre  = baseline_mean + baseline_sd * z[:, 0]
    post = baseline_mean + change_effect + post_sd * z[:, 1]
    return pd.DataFrame({"pre": pre, "post": post, "change": post - pre})


def two_sample(n1, n2, mean1=0.0, mean2=0.5, sd1=1.0, sd2=1.0, rng=None):
    """Two-group sample (t-test ready). Returns df with group, y."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    return pd.DataFrame({"group": ["A"] * n1 + ["B"] * n2,
                         "y": list(rng.normal(mean1, sd1, n1)) + list(rng.normal(mean2, sd2, n2))})


def contingency_table(row_margins, col_margins, odds_ratio=1.0, rng=None):
    """Generate a 2×2 contingency table matching row/col margins with target OR.
    For RxC just supply marginals (OR ignored, IPF used). Returns counts table."""
    rng = rng or np.random.default_rng()
    r = np.asarray(row_margins, float); c = np.asarray(col_margins, float)
    if r.sum() != c.sum():
        raise ValueError("row and column margins must sum to same total")
    if len(r) == 2 and len(c) == 2 and odds_ratio != 1.0:
        # solve 2x2: a / (r0-a) / (c0-a) * (r1-c0+a) = OR
        N = r.sum(); rr, cc = r[0], c[0]
        def f(a):
            return (a * (N - rr - cc + a)) / max((rr - a) * (cc - a), 1e-9) - odds_ratio
        a = tune_scalar(lambda a: f(a) + odds_ratio, odds_ratio,
                        x0=rr * cc / N, lo=max(0, rr + cc - N) + 1e-6, hi=min(rr, cc) - 1e-6)
        a = int(round(a))
        return np.array([[a, int(rr - a)], [int(cc - a), int(N - rr - cc + a)]])
    # general RxC: IPF
    T = np.outer(r, c) / r.sum()
    return np.round(T).astype(int)


def mixed_effects_dataset(n_units, n_periods, fixed_effects=None, intercept=0.0,
                          random_intercept_sd=0.5, random_slope_sd=0.0,
                          slope_var=None, noise_sd=1.0, rng=None):
    """Multilevel/mixed-effects panel: y_{it} = intercept + α_i + (β + s_i)·X_{it}
    + γ_t + ε. fixed_effects: list of fixed slopes β (one per time-varying X).
    slope_var: index of X getting the random slope (default 0). Returns long df."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    p = len(fixed_effects or [])
    a_i = rng.normal(0, random_intercept_sd, n_units)
    s_i = rng.normal(0, random_slope_sd, n_units) if random_slope_sd > 0 else np.zeros(n_units)
    rows = []
    for u in range(n_units):
        X = rng.standard_normal((n_periods, p))
        slope_eff = (X[:, slope_var or 0] * s_i[u]) if p > 0 else 0
        y = (intercept + a_i[u] + (X @ np.asarray(fixed_effects)) + slope_eff
             + rng.normal(0, noise_sd, n_periods))
        for t in range(n_periods):
            rows.append([u, t] + list(X[t]) + [y[t]])
    return pd.DataFrame(rows, columns=["unit", "time"] + [f"x{i+1}" for i in range(p)] + ["y"])


def correlation_matrix_block(block_sizes, within_corr=0.5, between_corr=0.1):
    """Block-structured correlation matrix: high within-block correlation, low
    between-block. Useful for factor analysis / clustering test data."""
    k = sum(block_sizes); R = np.full((k, k), between_corr)
    i = 0
    for sz in block_sizes:
        R[i:i + sz, i:i + sz] = within_corr
        i += sz
    np.fill_diagonal(R, 1.0)
    return R


def partial_corr(df, x, y, controls):
    """Partial correlation of x and y controlling for `controls` (list of col names)."""
    G = np.column_stack([np.ones(len(df))] + [df[c].values for c in controls])
    rx = resid_against(df[x].values, G); ry = resid_against(df[y].values, G)
    return float(np.corrcoef(rx, ry)[0, 1])


def vif(df, cols):
    """Variance Inflation Factor per column: VIF_j = 1/(1 - R²_j) where R²_j is
    from regressing x_j on the other columns. >5 = problematic collinearity."""
    out = {}
    for j, c in enumerate(cols):
        others = [oc for oc in cols if oc != c]
        G = np.column_stack([np.ones(len(df))] + [df[oc].values for oc in others])
        r = resid_against(df[c].values, G)
        r2 = 1 - r.var() / df[c].values.var()
        out[c] = float(1 / max(1 - r2, 1e-9))
    return out


# ============================================================================
# Multi-dimensional / multi-table CONSISTENCY (generation + checks)
# ============================================================================
def generate_id_column(n, prefix="ID", width=6, start=1):
    """Unique IDs like 'ID_000001'..'ID_NNNNNN'."""
    return [f"{prefix}_{i:0{width}d}" for i in range(start, start + n)]


def relational_children(parent, parent_key, n_per_parent, child_cols=None,
                        child_key_prefix="C", rng=None):
    """Generate a child table referencing `parent`. `n_per_parent` is an
    integer, an array of counts (one per parent row), or a callable rng->int.
    `child_cols` = dict {col_name: callable(parent_row, child_index, rng)->value}
    can use parent attributes for correlated child columns. Foreign-key column
    is auto-added as `parent_key`."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    rows = []
    for _, prow in parent.iterrows():
        if callable(n_per_parent):
            k = max(0, int(n_per_parent(rng)))
        elif np.isscalar(n_per_parent):
            k = int(n_per_parent)
        else:
            k = int(n_per_parent[prow.name])
        for ci in range(k):
            row = {parent_key: prow[parent_key]}
            if child_cols:
                for col, fn in child_cols.items():
                    row[col] = fn(prow, ci, rng)
            rows.append(row)
    df = pd.DataFrame(rows)
    df.insert(0, "child_id", generate_id_column(len(df), prefix=child_key_prefix))
    return df


def evolve_panel_state(initial_df, n_periods, evolve_fn, id_col="id", rng=None):
    """Generate temporal panel from an initial state by applying evolve_fn
    repeatedly: evolve_fn(state_t, t, rng) -> state_{t+1} (DataFrame same cols).
    Returns long-format df with `id`, `time`, and state columns. Use for any
    process that must respect temporal order (status changes, balances, etc.)."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    snapshots = []
    state = initial_df.copy()
    if id_col not in state.columns:
        state[id_col] = generate_id_column(len(state))
    for t in range(n_periods):
        snap = state.copy(); snap["time"] = t
        snapshots.append(snap)
        state = evolve_fn(state, t, rng)
    return pd.concat(snapshots, ignore_index=True)


def multi_rater(n, rater_corr, rater_means=None, rater_sds=None, rng=None):
    """Multi-source ratings (self/manager/peer): each rater sees a noisy + biased
    view of the same target. rater_corr: (k,k) target inter-rater correlation.
    Returns df with rater_1 ... rater_k. Inter-rater correlation matches target."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    k = len(rater_corr)
    Z = rng.standard_normal((n, k)) @ np.linalg.cholesky(nearest_pd(rater_corr)).T
    if rater_sds  is not None: Z = Z * np.asarray(rater_sds)
    if rater_means is not None: Z = Z + np.asarray(rater_means)
    return pd.DataFrame(Z, columns=[f"rater_{i+1}" for i in range(k)])


def funnel_data(n_top, conversion_rates, stage_names=None, rng=None):
    """Cohort funnel: n_top users enter stage 1; each advances to next with
    prob conversion_rates[i]. Returns df with user_id + per-stage 0/1 + final
    stage reached."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    K = len(conversion_rates) + 1
    names = stage_names or [f"stage_{i+1}" for i in range(K)]
    reached = np.ones((n_top, K), dtype=int)
    last = np.ones(n_top, dtype=bool)
    for i, p in enumerate(conversion_rates):
        adv = (rng.random(n_top) < p) & last
        last = adv
        reached[:, i + 1] = adv.astype(int)
    df = pd.DataFrame(reached, columns=names)
    df.insert(0, "user_id", generate_id_column(n_top))
    df["stage_reached"] = df[names].sum(1)
    return df


# ----------- consistency CHECKS ------------
def check_referential_integrity(child, child_fk, parent, parent_key):
    """Every child[child_fk] value must exist in parent[parent_key]. Returns
    (ok, violators_df)."""
    bad = ~child[child_fk].isin(parent[parent_key])
    return (not bad.any()), child[bad]


def check_aggregate(child, child_fk, child_value, parent, parent_key, parent_agg,
                    agg="sum", tol=1e-6):
    """Verify parent[parent_agg] == agg of child[child_value] grouped by FK.
    agg in {'sum','mean','count','max','min'}. Returns (ok, mismatches_df)."""
    import pandas as pd
    g = getattr(child.groupby(child_fk)[child_value], agg)()
    merged = parent[[parent_key, parent_agg]].merge(
        g.rename("__computed"), left_on=parent_key, right_index=True, how="left").fillna(0)
    diff = (merged[parent_agg] - merged["__computed"]).abs()
    bad = diff > tol
    return (not bad.any()), merged[bad]


def check_temporal(df, before_col, after_col, allow_equal=True):
    """before_col <= after_col (or <). Returns (ok, violators)."""
    bad = df[before_col] > df[after_col] if allow_equal else df[before_col] >= df[after_col]
    return (not bad.any()), df[bad]


def check_identity(df, expr_fn, name="identity", tol=1e-6):
    """Per-row identity must hold: expr_fn(row) ~ 0 (or boolean True). Returns
    (ok, violators)."""
    vals = df.apply(expr_fn, axis=1)
    if vals.dtype == bool:
        bad = ~vals
    else:
        bad = vals.abs() > tol
    return (not bad.any()), df[bad]


def check_uniqueness(df, cols):
    """No duplicates on the given key. Returns (ok, duplicates)."""
    dup = df.duplicated(subset=cols, keep=False)
    return (not dup.any()), df[dup]


def check_no_nulls(df, cols):
    bad = df[cols].isna().any(axis=1)
    return (not bad.any()), df[bad]


def check_value_set(df, col, allowed):
    bad = ~df[col].isin(allowed)
    return (not bad.any()), df[bad]


def enforce_constraints(df, rules, action="report", verbose=True):
    """Apply a list of business rules.
    rules: list of (name, predicate_fn(df)->boolean_mask_of_GOOD_rows,
                    optional fix_fn(df, bad_mask)->df).
    action: 'report' (return violations dict), 'drop' (return df without bad),
            'fix' (apply fix_fn for each rule). Returns (df_out, violations)."""
    import pandas as pd
    out = df.copy(); viols = {}
    for entry in rules:
        name, pred, *rest = entry
        good = pred(out)
        bad = ~good
        viols[name] = int(bad.sum())
        if verbose:
            print(f"  [{name}] {bad.sum()} violations" + (" (will fix)" if action == "fix" and rest else ""))
        if action == "drop":
            out = out[good].reset_index(drop=True)
        elif action == "fix" and rest:
            out = rest[0](out, bad)
    return out, viols


# ============================================================================
# DEEPENING — round 5: industry-grade depth per category
# ============================================================================

# ----- distribution family helpers (unified API) -----
def sample_dist(dist, n, rng=None, **params):
    """Unified sampler. dist in {normal, lognormal, exponential, gamma, beta,
    weibull, pareto, t, chi2, poisson, negbin, geometric, uniform, truncnormal}.
    params per family (mean/sd / shape/scale / etc.). Returns (n,) array."""
    rng = rng or np.random.default_rng()
    if dist == "normal":      return rng.normal(params.get("mean", 0), params.get("sd", 1), n)
    if dist == "lognormal":   return rng.lognormal(params.get("mu", 0), params.get("sigma", 1), n)
    if dist == "exponential": return rng.exponential(params.get("scale", 1), n)
    if dist == "gamma":       return rng.gamma(params["shape"], params.get("scale", 1), n)
    if dist == "beta":        return rng.beta(params["a"], params["b"], n)
    if dist == "weibull":     return rng.weibull(params["shape"], n) * params.get("scale", 1)
    if dist == "pareto":      return (rng.pareto(params["shape"], n) + 1) * params.get("scale", 1)
    if dist == "t":           return rng.standard_t(params["df"], n) * params.get("scale", 1) + params.get("loc", 0)
    if dist == "chi2":        return rng.chisquare(params["df"], n)
    if dist == "poisson":     return rng.poisson(params["lam"], n)
    if dist == "negbin":      return count_data(n, params["mean"], dispersion=params.get("dispersion", 1), rng=rng)
    if dist == "geometric":   return rng.geometric(params["p"], n)
    if dist == "uniform":     return rng.uniform(params.get("lo", 0), params.get("hi", 1), n)
    if dist == "truncnormal":
        return truncated_normal(n, params.get("mean", 0), params.get("sd", 1),
                                params.get("lo", -np.inf), params.get("hi", np.inf), rng=rng)
    raise ValueError(f"unknown dist {dist!r}")


def truncated_normal(n, mean=0.0, sd=1.0, lo=-np.inf, hi=np.inf, rng=None):
    """Sample exactly n from N(mean,sd) truncated to [lo,hi] via inverse CDF
    (no rejection — efficient even at extreme truncation)."""
    rng = rng or np.random.default_rng()
    a = (lo - mean) / sd; b = (hi - mean) / sd
    Fa = _phi(np.array([a]))[0] if np.isfinite(a) else 0.0
    Fb = _phi(np.array([b]))[0] if np.isfinite(b) else 1.0
    u = rng.uniform(Fa, Fb, n)
    return mean + sd * _phi_inv(u)


def gaussian_mixture(n, weights, means, sds, rng=None):
    """Sample from a 1-D Gaussian mixture. weights need not sum to 1 (normalized)."""
    rng = rng or np.random.default_rng()
    w = np.asarray(weights, float); w = w / w.sum()
    k = rng.choice(len(w), size=n, p=w)
    return rng.normal(np.asarray(means)[k], np.asarray(sds)[k])


def zero_inflated_continuous(n, zero_prob, positive_sampler, rng=None):
    """Many zeros + a continuous positive distribution (insurance claims, gene
    expression, etc.). positive_sampler(n, rng) returns the non-zero values."""
    rng = rng or np.random.default_rng()
    x = positive_sampler(n, rng)
    x = np.where(rng.random(n) < zero_prob, 0.0, x)
    return x


# ----- additional copulas (heavy-tail / asymmetric tail dependence) -----
def t_copula(n, corr, df, ppfs, rng=None):
    """Student-t copula: heavier tail dependence than Gaussian (joint extremes
    co-occur more often). df→∞ recovers Gaussian. Marginals via empirical
    rank-based quantiles to avoid needing the t-CDF."""
    rng = rng or np.random.default_rng()
    k = len(ppfs)
    Z = rng.standard_normal((n, k)) @ np.linalg.cholesky(nearest_pd(corr)).T
    W = rng.chisquare(df, n)
    T = Z * np.sqrt(df / W)[:, None]                     # multivariate t
    # uniform via empirical CDF per column (avoids needing F_t)
    U = (np.argsort(np.argsort(T, axis=0), axis=0) + 0.5) / n
    return np.column_stack([np.asarray(ppfs[j](U[:, j]), float) for j in range(k)])


def clayton_copula(n, theta, ppfs, rng=None):
    """Clayton (Archimedean) copula: lower-tail dependence (joint small values
    co-occur). theta>0; theta→0 = independence; theta→∞ = perfect comonotonic.
    Marshall-Olkin algorithm (works for any dimension k)."""
    rng = rng or np.random.default_rng()
    k = len(ppfs)
    M = rng.gamma(1 / theta, 1, n)                       # mixing variable
    E = rng.exponential(1, (n, k))
    U = (1 + E / M[:, None]) ** (-1 / theta)
    return np.column_stack([np.asarray(ppfs[j](U[:, j]), float) for j in range(k)])


# ----- advanced time series -----
def ts_arma(n, ar=(), ma=(), sd=1.0, mean=0.0, rng=None):
    """ARMA(p,q): x_t = mean + Σ φ_i x_{t-i} + ε_t + Σ θ_j ε_{t-j}.
    ar=φ coefficients, ma=θ coefficients."""
    rng = rng or np.random.default_rng()
    p, q = len(ar), len(ma); m = max(p, q) + 1
    e = rng.normal(0, sd, n + m); x = np.zeros(n + m)
    for t in range(m, n + m):
        ar_part = sum(ar[i] * x[t - 1 - i] for i in range(p))
        ma_part = sum(ma[j] * e[t - 1 - j] for j in range(q))
        x[t] = ar_part + ma_part + e[t]
    return x[m:] + mean


def ts_garch(n, omega=0.05, alpha=0.1, beta=0.85, mean=0.0, rng=None):
    """GARCH(1,1): r_t = mean + ε_t, ε_t = σ_t·z_t, σ_t² = ω + α·ε_{t-1}² + β·σ_{t-1}².
    Stationary if α+β<1. Models volatility clustering (financial returns)."""
    rng = rng or np.random.default_rng()
    sig2 = np.zeros(n); eps = np.zeros(n)
    sig2[0] = omega / max(1 - alpha - beta, 1e-6)              # unconditional var
    eps[0] = np.sqrt(sig2[0]) * rng.standard_normal()
    for t in range(1, n):
        sig2[t] = omega + alpha * eps[t - 1] ** 2 + beta * sig2[t - 1]
        eps[t] = np.sqrt(sig2[t]) * rng.standard_normal()
    return mean + eps, np.sqrt(sig2)


def ts_var(n, A_list, Sigma, mean=None, rng=None):
    """Vector autoregressive VAR(p): y_t = c + Σ A_i y_{t-i} + ε_t, ε~N(0,Sigma).
    A_list: list of (k,k) coefficient matrices, one per lag."""
    rng = rng or np.random.default_rng()
    p = len(A_list); k = A_list[0].shape[0]
    mu = np.zeros(k) if mean is None else np.asarray(mean, float)
    L = np.linalg.cholesky(nearest_pd(Sigma))
    Y = np.zeros((n + p, k))
    for t in range(p, n + p):
        e = L @ rng.standard_normal(k)
        Y[t] = mu + sum(A_list[i] @ Y[t - 1 - i] for i in range(p)) + e
    return Y[p:]


# ----- GLM regression datasets -----
def poisson_regression_dataset(n, coefs, intercept=0.0, X_corr=None, rng=None):
    """Count outcome with target rate ratios exp(coefs). y_i ~ Poisson(exp(η_i))."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    coefs = np.asarray(coefs, float); k = len(coefs)
    R = np.eye(k) if X_corr is None else nearest_pd(X_corr)
    X = rng.standard_normal((n, k)) @ np.linalg.cholesky(R).T
    eta = intercept + X @ coefs
    lam = np.exp(np.clip(eta, -20, 20))
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(k)])
    df["y"] = rng.poisson(lam)
    return df


def multinomial_logit_dataset(n, coefs_per_class, intercepts=None, X_corr=None, rng=None):
    """K-class multinomial logit. coefs_per_class: (K-1, p) coefficients (class 0
    = reference). Returns df with features + class label in {0..K-1}."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    B = np.asarray(coefs_per_class, float)         # (K-1, p)
    K1, p = B.shape; K = K1 + 1
    R = np.eye(p) if X_corr is None else nearest_pd(X_corr)
    X = rng.standard_normal((n, p)) @ np.linalg.cholesky(R).T
    a = np.zeros(K1) if intercepts is None else np.asarray(intercepts, float)
    eta = X @ B.T + a                              # (n, K-1)
    exp_eta = np.exp(np.clip(eta, -20, 20))
    denom = 1 + exp_eta.sum(1, keepdims=True)
    probs = np.column_stack([1 / denom.ravel(), exp_eta / denom])   # (n, K)
    y = np.array([rng.choice(K, p=probs[i]) for i in range(n)])
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(p)])
    df["y"] = y
    return df


def ordinal_logit_dataset(n, coefs, thresholds, X_corr=None, rng=None):
    """Proportional-odds ordinal logit. thresholds: K-1 increasing cut-points.
    P(y≤k|x) = sigmoid(threshold_k - x·coefs)."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    coefs = np.asarray(coefs, float); thr = np.sort(np.asarray(thresholds, float))
    p = len(coefs)
    R = np.eye(p) if X_corr is None else nearest_pd(X_corr)
    X = rng.standard_normal((n, p)) @ np.linalg.cholesky(R).T
    eta = X @ coefs
    cum = 1 / (1 + np.exp(-(thr[None, :] - eta[:, None])))          # P(y<=k)
    u = rng.random(n)
    y = (u[:, None] > cum).sum(1)
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(p)])
    df["y"] = y
    return df


def quantile_regression_dataset(n, coefs, intercept=0.0, scale=1.0,
                                target_quantile=0.5, X_corr=None, rng=None):
    """Generate data where the τ-th conditional quantile of y given X equals
    intercept + X·coefs. Uses asymmetric Laplace noise positioned so its τ-th
    quantile = 0."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    coefs = np.asarray(coefs, float); k = len(coefs)
    R = np.eye(k) if X_corr is None else nearest_pd(X_corr)
    X = rng.standard_normal((n, k)) @ np.linalg.cholesky(R).T
    # asymmetric Laplace: E ~ exp(rate τ) if u>τ else -exp(rate 1-τ)
    u = rng.random(n)
    e = np.where(u > target_quantile,
                 rng.exponential(scale / (1 - target_quantile), n),
                 -rng.exponential(scale / target_quantile, n))
    y = intercept + X @ coefs + e
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(k)])
    df["y"] = y
    return df


# ----- causal/experimental designs -----
def propensity_match(treatment, propensity, ratio=1, caliper=None):
    """1:k nearest-neighbor matching on propensity score. Returns indices of
    matched pairs (treated_idx, [control_idx,...]). caliper=None means no max
    distance; else only matches within ±caliper on the propensity scale."""
    t = np.asarray(treatment, int); ps = np.asarray(propensity, float)
    treated = np.where(t == 1)[0]; control = np.where(t == 0)[0]
    used = set(); pairs = []
    for i in treated:
        avail = [c for c in control if c not in used]
        if not avail: break
        dists = np.abs(ps[avail] - ps[i])
        order = np.argsort(dists)
        picks = []
        for j in order:
            if caliper is None or dists[j] <= caliper:
                picks.append(avail[j]); used.add(avail[j])
                if len(picks) >= ratio: break
        if picks: pairs.append((i, picks))
    return pairs


def did_data(n_per_group, n_periods=2, treatment_time=1, treated_share=0.5,
             treatment_effect=0.5, time_trend=0.1, baseline=0.0, noise_sd=1.0, rng=None):
    """Difference-in-differences setup: units × periods, treatment applied at
    `treatment_time` to `treated_share` of units. Returns long-format df with
    unit/time/treated/post/treated_post/y."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    n = n_per_group * 2; treated = np.zeros(n, int)
    treated[:int(n * treated_share)] = 1; rng.shuffle(treated)
    fe = rng.normal(0, 0.5, n)                                         # unit FE
    rows = []
    for u in range(n):
        for t in range(n_periods):
            post = 1 if t >= treatment_time else 0
            tp = post * treated[u]
            y = baseline + fe[u] + time_trend * t + treatment_effect * tp + rng.normal(0, noise_sd)
            rows.append((u, t, treated[u], post, tp, y))
    return pd.DataFrame(rows, columns=["unit", "time", "treated", "post", "treated_post", "y"])


def rdd_data(n, cutoff=0.0, treatment_effect=0.5, slope_left=1.0, slope_right=1.2,
             noise_sd=1.0, running_dist="normal", rng=None):
    """Sharp regression-discontinuity: T=1 iff running ≥ cutoff. y = f(running) +
    T·effect + ε. Returns df with running/treated/y."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    if running_dist == "normal":     R = rng.normal(cutoff, 1.0, n)
    elif running_dist == "uniform":  R = rng.uniform(cutoff - 2, cutoff + 2, n)
    else: raise ValueError(running_dist)
    T = (R >= cutoff).astype(int)
    slope = np.where(T == 1, slope_right, slope_left)
    y = slope * (R - cutoff) + treatment_effect * T + rng.normal(0, noise_sd, n)
    return pd.DataFrame({"running": R, "treated": T, "y": y})


def iv_data(n, b_xy=0.5, b_zx=0.7, confounder_strength=0.5, rng=None):
    """Instrumental-variable setup: Z → X → Y plus unobserved U → X and U → Y
    (so OLS of Y~X is biased; 2SLS using Z is unbiased). Returns df with z/x/y/u."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    U = rng.standard_normal(n)
    Z = rng.standard_normal(n)
    X = b_zx * Z + confounder_strength * U + rng.standard_normal(n) * 0.5
    Y = b_xy * X + confounder_strength * U + rng.standard_normal(n)
    return pd.DataFrame({"z": Z, "x": X, "y": Y, "u": U})


def cluster_rct(n_clusters, n_per_cluster, treatment_effect=0.5, icc=0.1,
                baseline=0.0, noise_sd=1.0, rng=None):
    """Cluster-randomized trial: clusters (schools/clinics) are randomized; each
    cluster's units share a random intercept. Inflates SE vs individual RCT."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    cl_treat = rng.choice([0, 1], size=n_clusters)
    sb = np.sqrt(icc); sw = np.sqrt(max(1 - icc, 1e-6))
    rows = []
    for c in range(n_clusters):
        u = rng.normal(0, sb)
        for _ in range(n_per_cluster):
            y = baseline + u + treatment_effect * cl_treat[c] + rng.normal(0, sw * noise_sd)
            rows.append((c, cl_treat[c], y))
    return pd.DataFrame(rows, columns=["cluster", "treated", "y"])


# ----- survival extensions -----
def competing_risks_data(n, baseline_rates, hazard_ratios=None, X=None,
                         censor_rate=0.1, rng=None):
    """K competing causes of failure. baseline_rates: list of λ_k. Each subject's
    time = min of independent Exp(λ_k·exp(β_k·X)) + Exp(censor_rate).
    cause = argmin (or -1 if censored). Returns df with time/cause/x_*."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    K = len(baseline_rates)
    if X is None: X = np.zeros((n, 0))
    X = np.asarray(X, float).reshape(n, -1)
    HRs = hazard_ratios or [None] * K
    T_k = np.zeros((n, K))
    for k in range(K):
        if X.shape[1]:
            beta = np.log(np.asarray(HRs[k])) if HRs[k] is not None else np.zeros(X.shape[1])
            lam = baseline_rates[k] * np.exp(X @ beta)        # (n,) array
            T_k[:, k] = rng.exponential(1 / lam)              # element-wise
        else:
            T_k[:, k] = rng.exponential(1 / baseline_rates[k], n)  # explicit size=n
    cause = np.argmin(T_k, axis=1)
    T = T_k.min(axis=1)
    C = rng.exponential(1 / max(censor_rate, 1e-9), n)
    obs = np.minimum(T, C); event = T <= C
    out = pd.DataFrame({"time": obs, "cause": np.where(event, cause, -1)})
    for j in range(X.shape[1]): out[f"x{j+1}"] = X[:, j]
    return out


def recurrent_events_data(n, baseline_rate, max_time, frailty_sd=0.5, rng=None):
    """Recurrent (Poisson) events per subject with shared frailty Z_i ~ LogN
    inflating their event rate. Returns long-format df with subject/time."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    frailty = np.exp(rng.normal(0, frailty_sd, n))
    rows = []
    for i in range(n):
        rate = baseline_rate * frailty[i]; t = 0.0
        while True:
            t += rng.exponential(1 / rate)
            if t > max_time: break
            rows.append((i, t))
    return pd.DataFrame(rows, columns=["subject", "time"])


# ----- IRT (item response theory) -----
def irt_2pl_data(n_persons, item_difficulty, item_discrimination, theta_sd=1.0, rng=None):
    """2PL IRT: P(correct | theta) = sigmoid(a·(theta − b)) per item.
    item_difficulty: array b (n_items,); item_discrimination: array a (n_items,).
    Returns (n_persons, n_items) binary matrix + theta vector."""
    rng = rng or np.random.default_rng()
    b = np.asarray(item_difficulty, float); a = np.asarray(item_discrimination, float)
    n_items = len(b)
    theta = rng.normal(0, theta_sd, n_persons)
    P = 1 / (1 + np.exp(-a[None, :] * (theta[:, None] - b[None, :])))
    X = (rng.random((n_persons, n_items)) < P).astype(int)
    return X, theta


def irt_grm_data(n_persons, item_discrimination, item_thresholds, theta_sd=1.0, rng=None):
    """Graded Response Model (ordinal IRT): item_thresholds[i] = list of K-1
    increasing cut-points for item i (each item can have its own K)."""
    rng = rng or np.random.default_rng()
    theta = rng.normal(0, theta_sd, n_persons)
    a = np.asarray(item_discrimination, float); J = len(a)
    items = np.zeros((n_persons, J), int)
    for j in range(J):
        thr = np.sort(np.asarray(item_thresholds[j], float))
        cum = 1 / (1 + np.exp(-a[j] * (theta[:, None] - thr[None, :])))
        # P(y≥k) = cum_k → cell probs = diff; sample via rank
        u = rng.random(n_persons)
        items[:, j] = (u[:, None] < cum).sum(1)
    return items, theta


# ----- network / graph generators (edge-list format, no networkx) -----
def graph_er(n, p, directed=False, rng=None):
    """Erdős-Rényi G(n,p): each unordered pair (or ordered, if directed) is an
    edge independently with probability p. Returns list of (u,v) tuples."""
    rng = rng or np.random.default_rng()
    edges = []
    for i in range(n):
        for j in (range(n) if directed else range(i + 1, n)):
            if i != j and rng.random() < p: edges.append((i, j))
    return edges


def graph_ba(n, m, rng=None):
    """Barabási-Albert preferential attachment. Start with m+1 fully connected
    nodes; each new node connects to m existing chosen with prob ∝ degree.
    Produces heavy-tailed (power-law) degree distribution."""
    rng = rng or np.random.default_rng()
    edges = [(i, j) for i in range(m + 1) for j in range(i + 1, m + 1)]
    deg = np.zeros(n, int)
    for i in range(m + 1):
        deg[i] = m
    for v in range(m + 1, n):
        probs = deg[:v] / deg[:v].sum()
        targets = rng.choice(v, size=m, replace=False, p=probs)
        for t in targets:
            edges.append((t, v)); deg[t] += 1; deg[v] += 1
    return edges


def graph_ws(n, k, p, rng=None):
    """Watts-Strogatz small-world: ring lattice with k nearest neighbors, each
    edge rewired with prob p. Captures high clustering + short path lengths."""
    rng = rng or np.random.default_rng()
    edges = set()
    for i in range(n):
        for j in range(1, k // 2 + 1):
            edges.add((i, (i + j) % n))
    out = []
    for (u, v) in edges:
        if rng.random() < p:
            new = rng.integers(0, n)
            while new == u or (u, new) in edges or (new, u) in edges:
                new = rng.integers(0, n)
            out.append((u, int(new)))
        else:
            out.append((u, v))
    return out


def graph_sbm(block_sizes, p_in, p_out, rng=None):
    """Stochastic Block Model: within-block edge prob p_in, between-block p_out.
    block_sizes = list of community sizes. Returns (edges, block_membership)."""
    rng = rng or np.random.default_rng()
    block = np.concatenate([np.full(s, k) for k, s in enumerate(block_sizes)])
    n = len(block); edges = []
    for i in range(n):
        for j in range(i + 1, n):
            p = p_in if block[i] == block[j] else p_out
            if rng.random() < p: edges.append((i, j))
    return edges, block


# ----- ML benchmark scenarios -----
def regression_benchmark(n, n_features=5, target_r2=0.5, noise_type="normal",
                         feature_corr=None, rng=None):
    """Regression benchmark with calibrated R². noise_type in
    {'normal','heavy_t','heteroscedastic'} for realism variants."""
    rng = rng or np.random.default_rng()
    R = np.eye(n_features) if feature_corr is None else nearest_pd(feature_corr)
    X = rng.standard_normal((n, n_features)) @ np.linalg.cholesky(R).T
    w = rng.standard_normal(n_features); signal = X @ w
    var_s = signal.var()
    noise_sd = np.sqrt(var_s * (1 - target_r2) / max(target_r2, 1e-9))
    if   noise_type == "normal":          e = rng.normal(0, noise_sd, n)
    elif noise_type == "heavy_t":         e = rng.standard_t(4, n) * noise_sd / np.sqrt(2)
    elif noise_type == "heteroscedastic": e = rng.normal(0, noise_sd * (0.5 + np.abs(X[:, 0])))
    else: raise ValueError(noise_type)
    import pandas as pd
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(n_features)])
    df["y"] = signal + e
    return df


def concept_drift_data(n, n_features=5, drift_type="covariate", drift_magnitude=1.0,
                       split=0.5, rng=None):
    """Generate (df_before, df_after) with controlled distribution drift between
    halves. drift_type:
      'covariate' = X means shift in 'after' (label conditional unchanged)
      'label'     = P(y|x) shifts (coefs change)
      'prior'     = class balance shifts (binary outcome)
    Useful for testing drift detectors / online learning."""
    rng = rng or np.random.default_rng()
    n0 = int(n * split); n1 = n - n0
    X0 = rng.standard_normal((n0, n_features))
    coefs = rng.standard_normal(n_features)
    y0 = (X0 @ coefs + rng.standard_normal(n0)) > 0
    if drift_type == "covariate":
        X1 = rng.standard_normal((n1, n_features)) + drift_magnitude
        y1 = (X1 @ coefs + rng.standard_normal(n1)) > 0
    elif drift_type == "label":
        X1 = rng.standard_normal((n1, n_features))
        y1 = (X1 @ (coefs + drift_magnitude * np.ones_like(coefs)) + rng.standard_normal(n1)) > 0
    elif drift_type == "prior":
        X1 = rng.standard_normal((n1, n_features))
        y1 = (X1 @ coefs + drift_magnitude + rng.standard_normal(n1)) > 0
    else: raise ValueError(drift_type)
    import pandas as pd
    cols = [f"x{i+1}" for i in range(n_features)]
    return (pd.DataFrame(np.column_stack([X0, y0.astype(int)]), columns=cols + ["y"]),
            pd.DataFrame(np.column_stack([X1, y1.astype(int)]), columns=cols + ["y"]))


def anomaly_dataset(n, n_features=5, contamination=0.05, normal_sampler=None,
                    anomaly_sampler=None, rng=None):
    """Mostly-normal data with a small fraction of anomalies (for outlier-detection
    benchmarks). Returns df with label 0=normal, 1=anomaly."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    n_anom = int(round(n * contamination))
    n_norm = n - n_anom
    if normal_sampler is None:
        normal_sampler = lambda m, r: r.standard_normal((m, n_features))
    if anomaly_sampler is None:
        anomaly_sampler = lambda m, r: r.standard_normal((m, n_features)) * 3 + 5
    X = np.vstack([normal_sampler(n_norm, rng), anomaly_sampler(n_anom, rng)])
    y = np.concatenate([np.zeros(n_norm, int), np.ones(n_anom, int)])
    perm = rng.permutation(n)
    return pd.DataFrame(np.column_stack([X[perm], y[perm]]),
                        columns=[f"x{i+1}" for i in range(n_features)] + ["label"])


# ----- advanced diagnostics -----
def psi(reference, current, bins=10):
    """Population Stability Index: sum((expected_pct - actual_pct) * log(...)).
    Small=stable, >0.1 moderate drift, >0.25 severe drift. Reference is the
    baseline distribution (e.g. training data); current is the new one."""
    ref = np.asarray(reference, float); cur = np.asarray(current, float)
    edges = np.quantile(ref, np.linspace(0, 1, bins + 1))
    edges[0] -= 1e-9; edges[-1] += 1e-9
    p = np.histogram(ref, bins=edges)[0] / max(len(ref), 1)
    q = np.histogram(cur, bins=edges)[0] / max(len(cur), 1)
    p = np.clip(p, 1e-9, None); q = np.clip(q, 1e-9, None)
    return float(np.sum((p - q) * np.log(p / q)))


def js_divergence(p, q, bins=30):
    """Jensen-Shannon divergence (symmetric, bounded in [0, log2]) between two
    samples — generic distribution-similarity metric."""
    p = np.asarray(p, float); q = np.asarray(q, float)
    lo = min(p.min(), q.min()); hi = max(p.max(), q.max())
    edges = np.linspace(lo, hi, bins + 1)
    P = np.histogram(p, bins=edges, density=True)[0]; P = P / max(P.sum(), 1e-12)
    Q = np.histogram(q, bins=edges, density=True)[0]; Q = Q / max(Q.sum(), 1e-12)
    M = 0.5 * (P + Q)
    def kl(a, b): a = np.clip(a, 1e-12, None); b = np.clip(b, 1e-12, None); return float((a * np.log(a / b)).sum())
    return 0.5 * kl(P, M) + 0.5 * kl(Q, M)


def mahalanobis_outliers(X, threshold=None):
    """Per-row Mahalanobis distance from the multivariate mean; rows above
    `threshold` flagged as outliers. Default threshold = sqrt(chi²_0.975, df=p)."""
    X = np.asarray(X, float); n, p = X.shape
    mu = X.mean(0); S = np.cov(X, rowvar=False)
    Sinv = np.linalg.pinv(S)
    d = np.sqrt(((X - mu) @ Sinv * (X - mu)).sum(1))
    if threshold is None:
        # crude chi² approximation: median+3*MAD, or use sqrt of 97.5% of chi²_p
        threshold = np.sqrt(p + 3 * np.sqrt(2 * p))
    return d, d > threshold


def mardia_normality(X):
    """Mardia's multivariate skewness and kurtosis. Under multivariate normality:
    n·b1/6 ~ χ²(p(p+1)(p+2)/6); (b2 - p(p+2)) / sqrt(8p(p+2)/n) ~ N(0,1).
    Returns (b1, b2, p_value_skew_chi2, z_kurt)."""
    X = np.asarray(X, float); n, p = X.shape
    mu = X.mean(0); S = np.cov(X, rowvar=False); Sinv = np.linalg.pinv(S)
    Y = X - mu
    D = Y @ Sinv @ Y.T              # (n,n)
    b1 = float((D ** 3).sum()) / (n * n)
    b2 = float(np.diag(D) ** 2).sum() / n if False else float((np.diag(D) ** 2).sum() / n)
    z_kurt = (b2 - p * (p + 2)) / np.sqrt(8 * p * (p + 2) / n)
    return b1, b2, z_kurt


# ----- multi-table extensions -----
def many_to_many(left, right, left_key, right_key, density=0.1, rng=None):
    """Generate a junction table (left_key, right_key) with target edge density.
    density = expected # links / (|left|·|right|). Useful for user-product likes,
    student-course enrollments."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    nL = len(left); nR = len(right); n_edges = int(nL * nR * density)
    Li = rng.integers(0, nL, n_edges)
    Ri = rng.integers(0, nR, n_edges)
    df = pd.DataFrame({left_key: left[left_key].values[Li],
                       right_key: right[right_key].values[Ri]})
    return df.drop_duplicates().reset_index(drop=True)


def scd_type2(initial_df, key_col, n_changes, change_fn, time_periods, rng=None):
    """Slowly Changing Dimension type 2 history table: each entity keeps a
    sequence of versions with valid_from/valid_to. change_fn(row, t, rng) returns
    a modified row (or None for no change). Returns long history df."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    rows = []
    for _, r in initial_df.iterrows():
        cur = dict(r); start = 0
        for t in range(1, time_periods + 1):
            if rng.random() < n_changes / time_periods:
                new = change_fn(cur, t, rng)
                if new is not None:
                    rows.append({**cur, "valid_from": start, "valid_to": t})
                    cur = new; start = t
        rows.append({**cur, "valid_from": start, "valid_to": time_periods})
    return pd.DataFrame(rows)


# ----- minority oversampling -----
def smote(X, y, target_balance=0.5, k=5, rng=None):
    """SMOTE: oversample the minority class to reach `target_balance` by creating
    synthetic samples between minority points and their k nearest neighbors.
    Returns (X_new, y_new)."""
    rng = rng or np.random.default_rng()
    X = np.asarray(X, float); y = np.asarray(y)
    classes, cnts = np.unique(y, return_counts=True)
    minc = classes[np.argmin(cnts)]; majc = classes[np.argmax(cnts)]
    n_min = int(cnts.min()); n_maj = int(cnts.max())
    target_min = int(n_maj * target_balance / (1 - target_balance)) if target_balance < 1 else n_min
    n_new = max(0, target_min - n_min)
    if n_new == 0: return X, y
    Xm = X[y == minc]
    new_rows = []
    for _ in range(n_new):
        i = rng.integers(0, len(Xm))
        d = np.linalg.norm(Xm - Xm[i], axis=1)
        nn = np.argsort(d)[1:k + 1]
        j = rng.choice(nn)
        alpha = rng.random()
        new_rows.append(Xm[i] + alpha * (Xm[j] - Xm[i]))
    X_new = np.vstack([X] + new_rows)
    y_new = np.concatenate([y, np.full(n_new, minc)])
    return X_new, y_new


# ============================================================================
# DEEPENING round 6: spatial / HMM / Hawkes / Bayesian / recsys / low-rank /
# adversarial-label-noise / Anderson-Darling
# ============================================================================

# ----- Spatial -----
def spatial_points(n, region=(0, 1, 0, 1), pattern="poisson", cluster_params=None, rng=None):
    """Generate 2D point pattern in [x0,x1]×[y0,y1].
    pattern: 'poisson' (CSR), 'cluster' (Thomas process: parents + offspring),
    'regular' (perturbed lattice)."""
    rng = rng or np.random.default_rng()
    x0, x1, y0, y1 = region
    if pattern == "poisson":
        return np.column_stack([rng.uniform(x0, x1, n), rng.uniform(y0, y1, n)])
    if pattern == "cluster":
        cp = cluster_params or {"n_centers": max(1, n // 20), "spread": 0.03}
        centers = np.column_stack([rng.uniform(x0, x1, cp["n_centers"]),
                                   rng.uniform(y0, y1, cp["n_centers"])])
        idx = rng.integers(0, cp["n_centers"], n)
        return centers[idx] + rng.normal(0, cp["spread"], (n, 2))
    if pattern == "regular":
        side = int(np.ceil(np.sqrt(n)))
        gx, gy = np.meshgrid(np.linspace(x0, x1, side), np.linspace(y0, y1, side))
        pts = np.column_stack([gx.ravel(), gy.ravel()])[:n]
        return pts + rng.normal(0, 0.5 / side, pts.shape)
    raise ValueError(pattern)


def spatial_field(grid_size, range_param=0.2, sill=1.0, nugget=0.0, rng=None):
    """Gaussian random field on a (grid_size × grid_size) regular grid using
    exponential covariance C(h)=sill·exp(-h/range)+nugget·I (Matern ν→∞ limit).
    Returns 2D array of values."""
    rng = rng or np.random.default_rng()
    n = grid_size; coords = np.array([(i, j) for i in range(n) for j in range(n)], float) / n
    d = np.linalg.norm(coords[:, None] - coords[None, :], axis=2)
    K = sill * np.exp(-d / max(range_param, 1e-6)) + nugget * np.eye(len(coords))
    Z = np.linalg.cholesky(nearest_pd(K)) @ rng.standard_normal(len(coords))
    return Z.reshape(n, n)


def morans_i(values, coords, k_neighbors=8):
    """Moran's I global spatial autocorrelation. coords: (n,2). Uses k-NN
    binary weights. Returns I in roughly [-1, +1]; +1=strong clustering."""
    v = np.asarray(values, float); coords = np.asarray(coords, float)
    n = len(v); v = v - v.mean()
    W = np.zeros((n, n))
    d2 = ((coords[:, None] - coords[None, :]) ** 2).sum(-1)
    np.fill_diagonal(d2, np.inf)
    nn = np.argsort(d2, axis=1)[:, :k_neighbors]
    for i in range(n): W[i, nn[i]] = 1.0
    W = (W + W.T) / 2                                  # symmetrize
    S0 = W.sum()
    return float(n / S0 * (v @ W @ v) / (v @ v + 1e-12))


# ----- HMM (Hidden Markov Model) -----
def hmm_data(n, transition, emission_means, emission_sds, init=None, rng=None):
    """Gaussian-emission HMM: latent state evolves by `transition` (K×K),
    observation_t ~ N(emission_means[state], emission_sds[state]).
    Returns (states, observations)."""
    rng = rng or np.random.default_rng()
    P = np.asarray(transition, float); P = P / P.sum(1, keepdims=True)
    K = P.shape[0]
    means = np.asarray(emission_means, float); sds = np.asarray(emission_sds, float)
    init = np.full(K, 1 / K) if init is None else np.asarray(init) / np.sum(init)
    s = np.empty(n, int); x = np.empty(n)
    s[0] = rng.choice(K, p=init)
    for t in range(1, n): s[t] = rng.choice(K, p=P[s[t - 1]])
    for t in range(n):    x[t] = rng.normal(means[s[t]], sds[s[t]])
    return s, x


# ----- Hawkes process (self-exciting events) -----
def hawkes_process(T_max, mu=1.0, alpha=0.5, beta=1.0, rng=None):
    """Simulate a univariate Hawkes process by thinning (Ogata's algorithm).
    Intensity λ(t) = μ + Σ α·exp(-β(t - t_i)) over past events t_i.
    Stationary if alpha/beta < 1. Returns array of event times."""
    rng = rng or np.random.default_rng()
    events = []; t = 0.0
    while t < T_max:
        lam_bar = mu + alpha * sum(np.exp(-beta * (t - ti)) for ti in events)
        t += rng.exponential(1 / lam_bar)
        if t >= T_max: break
        lam_t = mu + alpha * sum(np.exp(-beta * (t - ti)) for ti in events)
        if rng.random() < lam_t / lam_bar: events.append(t)
    return np.array(events)


# ----- Bayesian: prior sampling + simple Metropolis posterior -----
def prior_dataset(n, prior_specs, rng=None):
    """Sample columns from independent priors. prior_specs: dict
       {col_name: (dist_name, params_dict)} — uses sample_dist under the hood."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    return pd.DataFrame({c: sample_dist(d, n, rng=rng, **p) for c, (d, p) in prior_specs.items()})


def metropolis_posterior(log_post, x0, n_iter=5000, proposal_sd=0.3, burn=500, rng=None):
    """Generic 1-D random-walk Metropolis sampler for posterior exploration.
    log_post(x) -> log-posterior. Returns chain (n_iter-burn,).
    For multi-D, wrap each coordinate or use component-wise."""
    rng = rng or np.random.default_rng()
    x = float(x0); lp = log_post(x); chain = []
    for _ in range(n_iter):
        xp = x + rng.normal(0, proposal_sd)
        lpp = log_post(xp)
        if np.log(rng.random()) < lpp - lp:
            x, lp = xp, lpp
        chain.append(x)
    return np.array(chain[burn:])


# ----- Recommendation system data -----
def recsys_explicit(n_users, n_items, latent_dim=10, signal_sd=1.0, noise_sd=0.5,
                    sparsity=0.95, rng=None):
    """Explicit-rating recsys (e.g. 1-5 stars): R = U @ V.T + noise, then
    keep a `1-sparsity` fraction observed (MCAR). Returns (R_dense, mask, U, V).
    Recovers rank `latent_dim` for matrix-factorization benchmarks."""
    rng = rng or np.random.default_rng()
    U = signal_sd * rng.standard_normal((n_users, latent_dim))
    V = signal_sd * rng.standard_normal((n_items, latent_dim))
    R = U @ V.T + rng.normal(0, noise_sd, (n_users, n_items))
    mask = rng.random((n_users, n_items)) > sparsity
    return R, mask, U, V


def recsys_implicit(n_users, n_items, n_interactions, popularity_skew=1.5,
                    user_activity_skew=1.5, rng=None):
    """Implicit-feedback (click/purchase) interaction list. Both item popularity
    and user activity follow power laws (skew>1 = heavier tail)."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    p_item = rng.pareto(popularity_skew, n_items) + 1; p_item /= p_item.sum()
    p_user = rng.pareto(user_activity_skew, n_users) + 1; p_user /= p_user.sum()
    users = rng.choice(n_users, n_interactions, p=p_user)
    items = rng.choice(n_items, n_interactions, p=p_item)
    return pd.DataFrame({"user": users, "item": items}).drop_duplicates().reset_index(drop=True)


# ----- Low-rank / cluster (embedding-style) -----
def low_rank_data(n, p, rank, signal_strength=1.0, noise_sd=0.5, rng=None):
    """n×p matrix with intrinsic rank `rank` plus iid noise. For PCA/SVD recovery
    benchmarks: top `rank` singular values are large, rest small."""
    rng = rng or np.random.default_rng()
    U = rng.standard_normal((n, rank))
    V = rng.standard_normal((p, rank))
    return signal_strength * (U @ V.T) + rng.normal(0, noise_sd, (n, p))


def cluster_data(n, n_clusters=3, n_features=2, separation=2.0, cluster_sds=None, rng=None):
    """Gaussian-mixture clusters for clustering / classification. Cluster centers
    on a circle scaled by `separation`. Returns (X, y)."""
    rng = rng or np.random.default_rng()
    angles = np.linspace(0, 2 * np.pi, n_clusters, endpoint=False)
    centers = np.column_stack([np.cos(angles), np.sin(angles)] +
                              [np.zeros(n_clusters)] * (n_features - 2)) * separation
    sds = np.ones(n_clusters) if cluster_sds is None else np.asarray(cluster_sds)
    y = rng.integers(0, n_clusters, n)
    X = centers[y] + rng.normal(0, sds[y][:, None], (n, n_features))
    return X, y


# ----- Adversarial perturbation + label noise -----
def adversarial_perturb(X, epsilon=0.1, norm="inf", direction=None, rng=None):
    """Apply ε-bounded perturbation. `direction` is a per-row unit vector (e.g.
    gradient of a model) — None = random direction. norm='inf' (uniform per dim)
    or '2' (radius-ε ball)."""
    rng = rng or np.random.default_rng()
    X = np.asarray(X, float)
    if direction is None: direction = rng.standard_normal(X.shape)
    direction = np.asarray(direction, float)
    if norm == "inf":
        return X + epsilon * np.sign(direction)
    norms = np.linalg.norm(direction, axis=1, keepdims=True) + 1e-12
    return X + epsilon * direction / norms


def label_noise(y, noise_rate, n_classes=None, rng=None):
    """Flip a fraction of labels uniformly at random to a different class.
    n_classes inferred from y if not given."""
    rng = rng or np.random.default_rng()
    y = np.asarray(y).copy()
    if n_classes is None: n_classes = int(y.max() + 1) if y.dtype.kind in "iu" else len(set(y))
    flips = rng.random(len(y)) < noise_rate
    for i in np.where(flips)[0]:
        alt = [c for c in range(n_classes) if c != y[i]]
        y[i] = rng.choice(alt)
    return y


# ----- More diagnostics -----
def anderson_darling_normal(x):
    """Anderson-Darling test statistic for normality (no scipy). Higher = worse
    fit. Critical values at α=0.05: A²>0.752 reject. Standardizes with sample
    mean/sd (so sensitive to ANY deviation from normal)."""
    x = np.sort(np.asarray(x, float)); n = len(x)
    z = (x - x.mean()) / (x.std(ddof=1) or 1.0)
    F = _phi(z); F = np.clip(F, 1e-12, 1 - 1e-12)
    i = np.arange(1, n + 1)
    A2 = -n - (1 / n) * ((2 * i - 1) * (np.log(F) + np.log(1 - F[::-1]))).sum()
    return float(A2)


def chi_square_gof(observed, expected):
    """Pearson chi-square goodness-of-fit statistic: Σ (obs-exp)²/exp.
    Returns (stat, df). Compare to χ²(df) critical value."""
    o = np.asarray(observed, float); e = np.asarray(expected, float)
    return float(((o - e) ** 2 / np.maximum(e, 1e-12)).sum()), len(o) - 1


# ============================================================================
# DEEPENING round 7: TS anomalies, KG, RL, bandits, HTE, synth-control, MMM,
# discrete choice, SNPs, LDA, spike trains, cold-start, conformal calibration
# ============================================================================

# ----- Time-series anomaly injection -----
def ts_anomaly_inject(x, point_rate=0.0, level_shift=None, seasonal_anomaly=None,
                      drift_at=None, drift_slope=0.5, rng=None):
    """Inject typed anomalies into a time series for anomaly-detection benchmarks.
      point_rate:       fraction of points pulled to ±k·SD spikes (point anomalies)
      level_shift:      list of (t, delta) — at time t, level shifts by delta
      seasonal_anomaly: (t_start, t_end, multiplier) — multiply window by factor
      drift_at:         start time for linear drift; slope per step thereafter
    Returns (x_with_anom, labels: 0=normal, 1=anomaly)."""
    rng = rng or np.random.default_rng()
    x = np.asarray(x, float).copy(); n = len(x); labels = np.zeros(n, int)
    if point_rate > 0:
        idx = rng.choice(n, max(1, int(point_rate * n)), replace=False)
        sd = x.std() or 1.0
        x[idx] += np.where(rng.random(len(idx)) < 0.5, -1, 1) * 5 * sd
        labels[idx] = 1
    for (t, delta) in (level_shift or []):
        x[t:] += delta; labels[t:t + 20] = 1                        # mark first 20 post-shift
    if seasonal_anomaly:
        t0, t1, m = seasonal_anomaly; x[t0:t1] *= m; labels[t0:t1] = 1
    if drift_at is not None:
        x[drift_at:] += drift_slope * np.arange(n - drift_at); labels[drift_at:] = 1
    return x, labels


def change_point_series(n, change_points, level_per_segment, noise_sd=1.0, rng=None):
    """Piecewise-constant mean with known change points + Gaussian noise. Returns
    (series, true_segment_id). For change-point detection benchmarks."""
    rng = rng or np.random.default_rng()
    seg_id = np.zeros(n, int); cps = [0] + list(change_points) + [n]
    for k in range(len(cps) - 1): seg_id[cps[k]:cps[k + 1]] = k
    means = np.asarray(level_per_segment, float)
    return means[seg_id] + rng.normal(0, noise_sd, n), seg_id


# ----- Knowledge graph / triples -----
def knowledge_graph_triples(n_entities, n_relations, n_triples, schema=None, rng=None):
    """Sample (head, relation, tail) triples. `schema` optional dict
    {relation_id: (head_type_set, tail_type_set)} restricts valid combinations
    (entities partitioned into n_entity_types groups). Returns DataFrame."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    if schema is None:
        triples = np.column_stack([
            rng.integers(0, n_entities, n_triples),
            rng.integers(0, n_relations, n_triples),
            rng.integers(0, n_entities, n_triples)])
    else:                                                # respect schema types
        n_types = max(max(s[0]) for s in schema.values()) + 1
        entity_type = rng.integers(0, n_types, n_entities)
        rows = []
        for _ in range(n_triples):
            r = rng.integers(0, n_relations); types_h, types_t = schema.get(int(r), ({0}, {0}))
            h_pool = np.where(np.isin(entity_type, list(types_h)))[0]
            t_pool = np.where(np.isin(entity_type, list(types_t)))[0]
            if len(h_pool) == 0 or len(t_pool) == 0: continue
            rows.append((rng.choice(h_pool), r, rng.choice(t_pool)))
        triples = np.asarray(rows)
    df = pd.DataFrame(triples, columns=["head", "relation", "tail"])
    return df.drop_duplicates().reset_index(drop=True)


# ----- Temporal networks (timestamped edges) -----
def temporal_network(n_nodes, n_periods, edge_rate=0.05, persistence=0.5, rng=None):
    """Time-stamped edge stream. Each pair has base prob edge_rate per period;
    `persistence` keeps last period's edges with this prob (correlated dynamics).
    Returns DataFrame [t, u, v]."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    rows = []; active = set()
    for t in range(n_periods):
        new_active = set()
        for (u, v) in active:                            # persistence
            if rng.random() < persistence: new_active.add((u, v))
        for u in range(n_nodes):                         # birth
            for v in range(u + 1, n_nodes):
                if (u, v) not in new_active and rng.random() < edge_rate:
                    new_active.add((u, v))
        for (u, v) in new_active: rows.append((t, u, v))
        active = new_active
    return pd.DataFrame(rows, columns=["t", "u", "v"])


# ----- RL trajectories -----
def rl_trajectories(n_episodes, n_states, n_actions, max_steps=50,
                    transition=None, reward_means=None, gamma=0.95, policy=None,
                    rng=None):
    """Simulate RL episodes in a finite MDP. transition[s,a]→next state distribution
    (default uniform random); reward_means[s,a]→mean reward (default randn).
    policy(state, rng)→action (default ε-greedy random). Returns DataFrame with
    episode/step/s/a/r/s_next/done + per-episode discounted return."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    if transition is None:
        transition = rng.dirichlet(np.ones(n_states), size=(n_states, n_actions))
    if reward_means is None:
        reward_means = rng.standard_normal((n_states, n_actions))
    if policy is None:
        policy = lambda s, r: r.integers(0, n_actions)
    rows = []
    for ep in range(n_episodes):
        s = rng.integers(0, n_states); G = 0.0
        for t in range(max_steps):
            a = int(policy(s, rng))
            r = reward_means[s, a] + rng.normal(0, 0.5)
            s_next = rng.choice(n_states, p=transition[s, a])
            G += (gamma ** t) * r
            rows.append((ep, t, s, a, r, s_next, t == max_steps - 1))
            s = s_next
    df = pd.DataFrame(rows, columns=["episode", "step", "s", "a", "r", "s_next", "done"])
    returns = df.groupby("episode").r.apply(
        lambda r: sum(gamma ** i * v for i, v in enumerate(r))).rename("return")
    return df.merge(returns, on="episode")


# ----- Contextual multi-armed bandit -----
def bandit_data(n_rounds, n_arms, context_dim, true_thetas=None, noise_sd=1.0,
                policy="random", rng=None):
    """Linear contextual bandit. Each round: context x ~ N(0,I)^d; reward of arm a
    = x · true_thetas[a] + noise. true_thetas (n_arms, context_dim) default
    random. policy: 'random' (default) | 'greedy_oracle' (best per context).
    Returns DataFrame [round, context_*, arm, reward, optimal_arm, regret]."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    Theta = true_thetas if true_thetas is not None else rng.standard_normal((n_arms, context_dim))
    X = rng.standard_normal((n_rounds, context_dim))
    expected = X @ Theta.T                                          # (n_rounds, n_arms)
    optimal = expected.argmax(1)
    if policy == "random":
        arm = rng.integers(0, n_arms, n_rounds)
    else:
        arm = optimal
    reward = expected[np.arange(n_rounds), arm] + rng.normal(0, noise_sd, n_rounds)
    regret = expected[np.arange(n_rounds), optimal] - expected[np.arange(n_rounds), arm]
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(context_dim)])
    df["arm"] = arm; df["reward"] = reward; df["optimal_arm"] = optimal; df["regret"] = regret
    return df


# ----- Conformal prediction calibration -----
def conformal_calibration_set(predictions, true_labels, alpha=0.1, mode="classification"):
    """Split-conformal nonconformity scores. Returns the (1-alpha)-quantile q such
    that |score| ≤ q forms a valid prediction interval / set.
      mode='classification': predictions is (n, K) softmax probs; score = 1 - p[true]
      mode='regression':     predictions is (n,) point pred; score = |y - pred|
    For new test points, include all classes/values with score ≤ q."""
    pred = np.asarray(predictions, float); y = np.asarray(true_labels)
    if mode == "classification":
        scores = 1 - pred[np.arange(len(y)), y]
    else:
        scores = np.abs(y - pred)
    n = len(scores)
    return float(np.quantile(scores, np.ceil((n + 1) * (1 - alpha)) / n, method="higher"))


# ----- HTE (Heterogeneous Treatment Effect / CATE) -----
def hte_data(n, n_features=3, treatment_share=0.5, baseline_fn=None,
             cate_fn=None, noise_sd=1.0, X_corr=None, rng=None):
    """Generate data with heterogeneous treatment effect: y = baseline_fn(X) +
    T·cate_fn(X) + ε. cate_fn returns per-row CATE (X[:,0] dominant by default).
    Useful for causal forests / meta-learners (S-, T-, X-, R-, DR-Learner) tests."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    R = np.eye(n_features) if X_corr is None else nearest_pd(X_corr)
    X = rng.standard_normal((n, n_features)) @ np.linalg.cholesky(R).T
    if baseline_fn is None: baseline_fn = lambda X: 0.5 * X[:, 0]
    if cate_fn is None:     cate_fn = lambda X: 1.0 + 0.8 * X[:, 0]    # heterogeneous in X[:,0]
    treat = (rng.random(n) < treatment_share).astype(int)
    cate = cate_fn(X)
    y = baseline_fn(X) + treat * cate + rng.normal(0, noise_sd, n)
    df = pd.DataFrame(X, columns=[f"x{i+1}" for i in range(n_features)])
    df["treat"] = treat; df["y"] = y; df["true_cate"] = cate
    return df


# ----- Synthetic control -----
def synthetic_control_data(n_units, n_periods, treated_idx=0, treatment_time=None,
                           treatment_effect=2.0, n_factors=2, noise_sd=0.3, rng=None):
    """Pre/post panel with a single treated unit and donor pool. Each unit's
    outcome is loaded on `n_factors` shared time factors → other units can be
    weighted to reconstruct the treated counterfactual (Abadie). Returns long
    DataFrame [unit, time, y] + true effect at treated post-time."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    if treatment_time is None: treatment_time = n_periods // 2
    F = rng.standard_normal((n_periods, n_factors))                  # time factors
    L = rng.standard_normal((n_units, n_factors))                    # unit loadings
    Y = L @ F.T + rng.normal(0, noise_sd, (n_units, n_periods))
    # apply treatment
    Y[treated_idx, treatment_time:] += treatment_effect
    rows = [(u, t, Y[u, t]) for u in range(n_units) for t in range(n_periods)]
    df = pd.DataFrame(rows, columns=["unit", "time", "y"])
    df["treated"] = (df.unit == treated_idx) & (df.time >= treatment_time)
    return df


# ----- Staggered DiD (multiple treatment timings) -----
def staggered_did(n_units, n_periods, treatment_times, treatment_effect=0.5,
                  time_trend=0.05, noise_sd=1.0, baseline=0.0, rng=None):
    """Staggered adoption DiD: each treated unit gets treated at its own time.
    treatment_times: dict {unit_idx: t_first_treated} (others never treated).
    Returns long DataFrame [unit, time, treated, post, treatment_effect, y]."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    fe = rng.normal(0, 0.5, n_units)
    rows = []
    for u in range(n_units):
        t_treat = treatment_times.get(u, None)
        for t in range(n_periods):
            post = 1 if (t_treat is not None and t >= t_treat) else 0
            y = baseline + fe[u] + time_trend * t + treatment_effect * post + rng.normal(0, noise_sd)
            rows.append((u, t, int(t_treat is not None), post, treatment_effect * post, y))
    return pd.DataFrame(rows, columns=["unit", "time", "ever_treated", "post", "true_effect", "y"])


# ----- Hierarchical Bayes (random-effects shrinkage) -----
def hierarchical_bayes_data(n_groups, n_per_group, hyper_mean=0.0, hyper_sd=1.0,
                            within_sd=1.0, varying_n=None, rng=None):
    """Two-level model: θ_g ~ N(hyper_mean, hyper_sd²); y_{gi} ~ N(θ_g, within_sd²).
    Group means shrink toward hyper_mean (partial pooling). varying_n: optional
    per-group sample size dict or array (else n_per_group for all). Returns long
    DataFrame [group, y] + true group means."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    theta = rng.normal(hyper_mean, hyper_sd, n_groups)
    rows = []
    for g in range(n_groups):
        ng = int(varying_n[g]) if varying_n is not None else n_per_group
        for _ in range(ng):
            rows.append((g, rng.normal(theta[g], within_sd)))
    df = pd.DataFrame(rows, columns=["group", "y"])
    truth = pd.DataFrame({"group": range(n_groups), "true_theta": theta})
    return df, truth


# ----- Marketing Mix Model (MMM) -----
def marketing_mix_data(n_periods, channels, adstock_decay=0.5, saturation_alpha=2.0,
                       saturation_gamma=0.5, baseline=10.0, noise_sd=1.0, rng=None):
    """Simulate MMM: y_t = baseline + Σ_ch Hill(adstock(spend_ch)) + noise.
    channels: dict {name: {'spend_sd': float, 'beta': float}} — beta = max effect.
    adstock = geometric decay; Hill saturation = β·s^α/(s^α + γ^α).
    Returns DataFrame [t, spend_<ch>..., y, adstock_<ch>...]."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    rows = {"t": list(range(n_periods))}
    contribs = np.zeros(n_periods)
    for ch, p in channels.items():
        spend = np.abs(rng.normal(p.get("spend_sd", 10), p.get("spend_sd", 10) / 3, n_periods))
        # adstock (geometric decay)
        adstock = np.zeros(n_periods); s_prev = 0
        for t in range(n_periods):
            s_prev = spend[t] + adstock_decay * s_prev; adstock[t] = s_prev
        # Hill saturation
        sat = p["beta"] * (adstock ** saturation_alpha) / (adstock ** saturation_alpha + saturation_gamma ** saturation_alpha)
        rows[f"spend_{ch}"] = spend; rows[f"adstock_{ch}"] = adstock
        contribs += sat
    rows["y"] = baseline + contribs + rng.normal(0, noise_sd, n_periods)
    return pd.DataFrame(rows)


# ----- Discrete choice / conditional logit -----
def discrete_choice(n_individuals, n_alternatives, attribute_matrix, coefs, rng=None):
    """Conditional logit: each individual picks 1 of n_alternatives based on
    alternative attributes (no individual-specific intercepts). attribute_matrix:
    (n_alternatives, n_attrs) or (n_individuals, n_alternatives, n_attrs).
    P(choose j | indiv i) = exp(x_ij·coefs) / Σ_k exp(x_ik·coefs)."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    A = np.asarray(attribute_matrix, float); coefs = np.asarray(coefs, float)
    if A.ndim == 2:                                  # broadcast attrs across individuals
        utilities = A @ coefs                        # (n_alts,)
        probs = np.exp(utilities - utilities.max()); probs /= probs.sum()
        choices = rng.choice(n_alternatives, n_individuals, p=probs)
    else:
        utilities = (A * coefs).sum(-1)              # (n_indiv, n_alts)
        u = utilities - utilities.max(1, keepdims=True)
        probs = np.exp(u); probs /= probs.sum(1, keepdims=True)
        choices = np.array([rng.choice(n_alternatives, p=probs[i]) for i in range(n_individuals)])
    return pd.DataFrame({"individual": np.arange(n_individuals), "choice": choices})


# ----- Genetic SNPs with linkage disequilibrium -----
def snp_genotypes(n_individuals, n_snps, maf=None, ld_strength=0.3, rng=None):
    """Generate SNP genotypes ∈ {0,1,2} (additive coding) with target minor allele
    frequencies and approximate linkage disequilibrium between adjacent SNPs via
    Gaussian copula. maf default = uniform in [0.05, 0.5]."""
    rng = rng or np.random.default_rng()
    if maf is None: maf = rng.uniform(0.05, 0.5, n_snps)
    # AR(1) corr between SNPs in normal-score space
    R = np.eye(n_snps)
    for i in range(n_snps - 1): R[i, i+1] = R[i+1, i] = ld_strength
    Z = rng.standard_normal((n_individuals, n_snps)) @ np.linalg.cholesky(nearest_pd(R)).T
    U = _phi(Z)
    geno = np.zeros((n_individuals, n_snps), int)
    for j in range(n_snps):
        # 2 alleles, allele frequency = maf[j]; genotype = binomial(2, maf[j]) given U
        thr1 = (1 - maf[j]) ** 2
        thr2 = thr1 + 2 * maf[j] * (1 - maf[j])
        geno[:, j] = (U[:, j] > thr1).astype(int) + (U[:, j] > thr2).astype(int)
    return geno


# ----- LDA topic-model documents -----
def lda_documents(n_docs, n_topics, vocab_size, doc_lengths=None,
                  topic_word_concentration=0.1, doc_topic_concentration=0.5, rng=None):
    """Simulate a corpus from LDA: each topic has a vocab distribution
    (Dirichlet); each doc has a topic mixture (Dirichlet); each token is drawn
    from a topic. Returns (doc_term_matrix (n_docs, vocab_size), true_doc_topics)."""
    rng = rng or np.random.default_rng()
    if doc_lengths is None: doc_lengths = rng.integers(50, 200, n_docs)
    topic_word = rng.dirichlet(np.full(vocab_size, topic_word_concentration), size=n_topics)
    doc_topic = rng.dirichlet(np.full(n_topics, doc_topic_concentration), size=n_docs)
    dtm = np.zeros((n_docs, vocab_size), int)
    for d in range(n_docs):
        for _ in range(int(doc_lengths[d])):
            z = rng.choice(n_topics, p=doc_topic[d])
            w = rng.choice(vocab_size, p=topic_word[z])
            dtm[d, w] += 1
    return dtm, doc_topic


# ----- Spike trains (neuroscience) -----
def spike_train(n_neurons, T_seconds, base_rate=10.0, refractory_ms=2.0, rng=None):
    """Poisson spike trains per neuron with refractory period. Returns list-of-
    arrays (one array of spike times per neuron, in seconds)."""
    rng = rng or np.random.default_rng()
    refract_s = refractory_ms / 1000.0
    trains = []
    for _ in range(n_neurons):
        spikes = []; t = 0.0
        while t < T_seconds:
            t += rng.exponential(1 / base_rate)
            if not spikes or (t - spikes[-1] >= refract_s):
                if t < T_seconds: spikes.append(t)
        trains.append(np.array(spikes))
    return trains


# ----- Cold-start recommendation (feature-based) -----
def cold_start_recsys(n_users, n_items, user_dim=5, item_dim=5,
                      cross_signal_strength=1.0, history_per_user=3, rng=None):
    """Cold-start: each user/item has feature vectors; affinity = u_feat·item_feat
    + noise. Only `history_per_user` interactions observed per user (the rest
    must be predicted from features). Returns (user_features, item_features,
    observed_interactions df, true_affinities matrix)."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    U = rng.standard_normal((n_users, user_dim))
    V = rng.standard_normal((n_items, item_dim))
    # project to same dim if differ via random map
    dim = min(user_dim, item_dim)
    affinity = cross_signal_strength * (U[:, :dim] @ V[:, :dim].T) + rng.normal(0, 0.5, (n_users, n_items))
    rows = []
    for u in range(n_users):
        # sample history_per_user items proportional to affinity (positive bias)
        p = np.exp(affinity[u] - affinity[u].max()); p /= p.sum()
        items = rng.choice(n_items, size=min(history_per_user, n_items), replace=False, p=p)
        for it in items:
            rows.append((u, it, affinity[u, it]))
    return U, V, pd.DataFrame(rows, columns=["user", "item", "rating"]), affinity


# ============================================================================
# HARNESS — discoverability, declarative API, validation, CLI, reproducibility
# ============================================================================

# ---------- 1. Function inventory (categorized) ----------
INVENTORY = {
    "engine": [
        ("tune_scalar",          "万能单旋钮标定（任何可度量目标的兜底）"),
        ("build_latents",        "β=R⁻¹r 条件高斯，多目标精确命中"),
        ("rebuild_block",        "外层校正多 Likert composite 同时命中"),
        ("zscale",               "标准化"),
        ("nearest_pd",           "投影到最近正定阵"),
        ("resid_against",        "对一组列残差化"),
    ],
    "distributions": [
        ("sample_dist",          "统一抽样：normal/lognormal/exp/gamma/beta/weibull/pareto/t/chi2/poisson/negbin/geometric/uniform/truncnormal"),
        ("match_marginal",       "分位映射 x 到任意目标分布（保排序）"),
        ("fleishman",            "Fleishman 幂多项式：命中精确偏度+峰度"),
        ("fleishman_coef",       "Fleishman 系数"),
        ("gaussian_mixture",     "高斯混合（多峰/异质）"),
        ("truncated_normal",     "截断正态（逆 CDF）"),
        ("zero_inflated_continuous", "零膨胀连续（保险/基因表达）"),
        ("multinomial_dataset",  "分类标签精确占比"),
        ("dirichlet_compositional", "组分数据（行和=1）"),
        ("rescale",              "线性变换 + clip"),
        ("fit_from_reference",   "拟合真实数据返回 sampler(n)"),
    ],
    "dependence": [
        ("iman_conover",         "分布无关秩相关（保边缘）"),
        ("gaussian_copula",      "给定边缘 + 正态分相关"),
        ("t_copula",             "t-copula（重尾联合极端）"),
        ("clayton_copula",       "Clayton 下尾依赖"),
        ("nonnormal_data",       "Vale-Maurelli：多元非正态 + 目标 Pearson"),
        ("mixed_copula",         "连续+二分+定序联合相关"),
        ("correlation_matrix_block", "块状相关阵"),
        ("partial_corr",         "偏相关（控变量后）"),
        ("vif",                  "VIF 共线性诊断"),
    ],
    "regression": [
        ("regression_dataset",   "线性回归（target b/R²）"),
        ("logistic_dataset",     "Logistic 回归（target b/OR）"),
        ("poisson_regression_dataset", "Poisson 回归（rate ratios）"),
        ("multinomial_logit_dataset",  "Multinomial logit（K 类）"),
        ("ordinal_logit_dataset",      "Ordinal logit（proportional odds）"),
        ("quantile_regression_dataset","Quantile 回归（target 分位）"),
        ("anova_design",         "Factorial ANOVA（主效应+交互）"),
        ("paired_data",          "配对前后（within-corr）"),
        ("two_sample",           "两样本（t-test ready）"),
        ("contingency_table",    "列联表（margins + OR）"),
    ],
    "multilevel": [
        ("likertize",            "Likert 题项 + composite"),
        ("calibrate_item_reliability", "保 composite 调 α+CFI（结构不变）★"),
        ("sum_preserving_round", "取整成和=target 的整数向量"),
        ("raw_cronbach_alpha",   "raw α（纯 numpy，秒级）"),
        ("icc_rebuild",          "多层 ICC 命中 + halo cross-corr"),
        ("factor_model_sample",  "因子模型 X = FΛ' + E"),
        ("irt_2pl_data",         "IRT 2PL 二分项"),
        ("irt_grm_data",         "IRT GRM 序类项"),
        ("multi_rater",          "多评分者目标 inter-rater corr"),
        ("mixed_effects_dataset","混合效应/多层回归"),
        ("panel_data",           "简单面板（ICC + AR1 + trend）"),
        ("cronbach_alpha",       "Cronbach's α"),
    ],
    "timeseries": [
        ("ts_ar",                "AR(p) + 趋势 + 季节"),
        ("ts_arma",              "ARMA(p,q) 全实现"),
        ("ts_garch",             "GARCH(1,1) 波动率聚集"),
        ("ts_var",               "VAR(p) 多元自回归"),
        ("markov_chain",         "由转移阵抽序列"),
        ("fit_markov",           "估转移阵"),
        ("hmm_data",             "高斯发射 HMM"),
        ("hawkes_process",       "Hawkes 自激点过程"),
        ("count_data",           "Poisson/NB/零膨胀计数"),
        ("ts_anomaly_inject",    "类型化时序异常注入"),
        ("change_point_series",  "已知变点 + 分段均值"),
    ],
    "causal": [
        ("dag_sample",           "结构因果模型 (SCM) 通用器"),
        ("ab_test_data",         "A/B 测试（continuous/binary/count）"),
        ("ipw_weights",          "逆概率处理权重"),
        ("propensity_match",     "Propensity score 1:k 匹配"),
        ("did_data",             "Difference-in-differences"),
        ("rdd_data",             "Sharp regression discontinuity"),
        ("iv_data",              "Instrumental variable"),
        ("cluster_rct",          "Cluster-randomized trial"),
        ("survival_data",        "Cox-PH 生存"),
        ("competing_risks_data", "竞争风险（多病因）"),
        ("recurrent_events_data","复发事件 + frailty"),
        ("hte_data",             "异质处理效应（CATE）"),
        ("synthetic_control_data","合成控制（pre/post + donor pool）"),
        ("staggered_did",        "Staggered DiD（变 treatment 时间）"),
        ("hierarchical_bayes_data","层级 Bayes 随机效应"),
    ],
    "networks-spatial": [
        ("graph_er",             "Erdős-Rényi 随机图"),
        ("graph_ba",             "Barabási-Albert 偏好连接"),
        ("graph_ws",             "Watts-Strogatz 小世界"),
        ("graph_sbm",            "Stochastic Block Model"),
        ("spatial_points",       "空间点模式 (CSR/cluster/regular)"),
        ("spatial_field",        "高斯随机场（指数协方差）"),
        ("morans_i",             "Moran's I 空间自相关"),
        ("knowledge_graph_triples", "知识图谱 (h,r,t) 三元组"),
        ("temporal_network",     "带时间戳的边流"),
    ],
    "ml-benchmarks": [
        ("classification_dataset","Classification: target AUC + balance"),
        ("regression_benchmark", "Regression: 3 种噪声（normal/heavy_t/het）"),
        ("concept_drift_data",   "概念漂移（covariate/label/prior）"),
        ("anomaly_dataset",      "异常检测基准"),
        ("smote",                "少数类上采样"),
        ("recsys_explicit",      "显式评分推荐"),
        ("recsys_implicit",      "隐式反馈推荐"),
        ("cold_start_recsys",    "Cold-start 特征推荐"),
        ("low_rank_data",        "低秩矩阵 + 噪声"),
        ("cluster_data",         "Gaussian mixture 聚类"),
        ("adversarial_perturb",  "L∞/L2 对抗扰动"),
        ("label_noise",          "随机标签翻转"),
        ("prior_dataset",        "Bayesian 先验抽样"),
        ("metropolis_posterior", "Metropolis 后验采样"),
        ("rl_trajectories",      "RL 轨迹（MDP rollouts）"),
        ("bandit_data",          "线性上下文 bandit"),
        ("conformal_calibration_set", "Conformal 校准集"),
    ],
    "multitable": [
        ("generate_id_column",   "唯一 ID 列"),
        ("relational_children",  "关系表父子（FK + per-parent count）"),
        ("many_to_many",         "M:N junction 表"),
        ("evolve_panel_state",   "时序状态演化"),
        ("funnel_data",          "Cohort 漏斗"),
        ("scd_type2",            "Slowly Changing Dim 历史表"),
        ("enforce_constraints",  "业务规则引擎 (report/drop/fix)"),
        ("check_referential_integrity", "外键校验"),
        ("check_aggregate",      "父子聚合一致校验"),
        ("check_temporal",       "时序顺序校验"),
        ("check_identity",       "行内恒等式校验"),
        ("check_uniqueness",     "主键唯一校验"),
        ("check_no_nulls",       "非空校验"),
        ("check_value_set",      "值域校验"),
    ],
    "diagnostics-privacy": [
        ("verify",               "通用相关核验"),
        ("report",               "全列均值/SD/偏峰/Pearson&Spearman"),
        ("ks_stat",              "KS 距离"),
        ("psi",                  "Population Stability Index"),
        ("js_divergence",        "Jensen-Shannon"),
        ("mahalanobis_outliers", "马氏距离异常"),
        ("mardia_normality",     "Mardia 多元正态性"),
        ("anderson_darling_normal", "AD 正态检验"),
        ("chi_square_gof",       "χ² 拟合优度"),
        ("discriminability",     "合成 vs 真实 AUC（真实度）"),
        ("rake",                 "IPF 重加权到边际"),
        ("inject_missing",       "MCAR/MAR/MNAR 缺失注入"),
        ("inject_outliers",      "目标率异常注入"),
        ("heteroscedastic_noise","异方差噪声"),
        ("dp_noise",             "Laplace 差分隐私"),
        ("bootstrap_perturb",    "Bootstrap 重抽"),
        ("shift_group_effect",   "命中 Cohen's d"),
    ],
    "domain-specific": [
        ("marketing_mix_data",   "MMM（adstock + Hill 饱和）"),
        ("discrete_choice",      "条件 logit 离散选择"),
        ("snp_genotypes",        "SNP + 连锁不平衡"),
        ("lda_documents",        "LDA 主题文档"),
        ("spike_train",          "神经元 Poisson 脉冲"),
    ],
}


def list_functions(category=None):
    """Return [(category, name, oneliner), ...]. Filter by category if given."""
    return [(cat, name, desc) for cat, items in INVENTORY.items()
            if (category is None or category == cat)
            for name, desc in items]


def show_help(name):
    """Pretty-print function signature + docstring + category. Fuzzy-suggest on
    unknown names."""
    import inspect
    fn = globals().get(name)
    if fn is None or not callable(fn):
        from difflib import get_close_matches
        all_names = [n for items in INVENTORY.values() for n, _ in items]
        sug = get_close_matches(name, all_names, n=3)
        print(f"unknown function: {name!r}" + (f" — did you mean: {sug}?" if sug else ""))
        return
    sig = inspect.signature(fn)
    print(f"\n{name}{sig}\n")
    print((fn.__doc__ or "(no docstring)").rstrip() + "\n")
    for cat, items in INVENTORY.items():
        for n, desc in items:
            if n == name: print(f"  category: {cat}\n  oneliner: {desc}")


# ---------- 2. Recipes (executable common patterns) ----------
RECIPES = {
    "ab_test_power_sim": dict(desc="A/B 测试经验功效仿真：固定 n、effect、sd，多次重抽估 power", code='''
import numpy as np, calibrate as C
rng = np.random.default_rng(0)
sig = 0
for _ in range(1000):
    df = C.ab_test_data(500, baseline=0, effect=0.2, sd=1.0, rng=rng)
    a = df[df.arm=="control"].y; b = df[df.arm=="treatment"].y
    se = (a.var()/len(a) + b.var()/len(b))**0.5
    if abs(b.mean()-a.mean())/se > 1.96: sig += 1
print(f"empirical power = {sig/1000:.1%}")
'''),
    "iv_recover_causal_effect": dict(desc="工具变量：OLS 偏 vs 2SLS 无偏（验证 IV 必要性）", code='''
import numpy as np, calibrate as C
from numpy.linalg import lstsq
rng = np.random.default_rng(0)
iv = C.iv_data(5000, b_xy=0.5, b_zx=0.7, confounder_strength=0.5, rng=rng)
ols = lstsq(np.column_stack([np.ones(len(iv)), iv.x]), iv.y, rcond=None)[0][1]
xh = lstsq(np.column_stack([np.ones(len(iv)), iv.z]), iv.x, rcond=None)[0]
xp = xh[0] + xh[1] * iv.z
tsls = lstsq(np.column_stack([np.ones(len(iv)), xp]), iv.y, rcond=None)[0][1]
print(f"true b_xy=0.5, OLS={ols:.3f} (biased), 2SLS={tsls:.3f}")
'''),
    "imitate_real_dataset": dict(desc="拟合真实数据 → 合成数据 → 真实度判别", code='''
import calibrate as C, pandas as pd, numpy as np
rng = np.random.default_rng(0)
real = pd.DataFrame({"income": rng.lognormal(10, 0.6, 2000),
                     "age": rng.integers(22, 65, 2000)})
real["spend"] = 0.0001 * real.income + 5 * rng.standard_normal(2000)
sampler = C.fit_from_reference(real, rng=rng)
synth = sampler(2000)
auc = C.discriminability(real, synth)
print(f"discriminability AUC = {auc:.3f}  (~0.5 = indistinguishable)")
'''),
    "scale_with_likert_alpha": dict(desc="造一份 Likert 量表 (k=5, α≈0.80, target 相关)", code='''
import calibrate as C, pandas as pd, numpy as np
rng = np.random.default_rng(0)
n = 500
df = pd.DataFrame({"X1": rng.normal(4, 1, n), "X2": rng.normal(5, 1, n)})
C.rebuild_block(df, ["X1","X2"],
    specs=[dict(items=[f"A{i}" for i in range(1,6)], comp="Y", mean=4.5, sd=1.2,
                tgt=[-0.49, 0.52])],
    item_sigma=0.66, outer=9, rng=rng)
print("alpha =", C.cronbach_alpha(df[[f"A{i}" for i in range(1,6)]].values).round(2),
      "corr(X1,Y) =", df.X1.corr(df.Y).round(3))
'''),
    "nonnormal_corr_preserve_marginals": dict(desc="保各列分布只改秩相关（Iman-Conover）", code='''
import numpy as np, calibrate as C
rng = np.random.default_rng(0)
X = np.column_stack([rng.lognormal(0,1,2000), rng.uniform(0,10,2000)])
Y = C.iman_conover(X, [[1, 0.6],[0.6,1]], rng=rng)
sp = np.corrcoef(C._ranks(Y[:,0]), C._ranks(Y[:,1]))[0,1]
print(f"spearman={sp:.3f} (~0.6), 边缘保留: {np.allclose(np.sort(Y[:,0]), np.sort(X[:,0]))}")
'''),
    "multilevel_icc_with_likert": dict(desc="多层 ICC + Likert + 控 cross-corr", code='''
import calibrate as C, pandas as pd, numpy as np
rng = np.random.default_rng(0)
# 假设有 final df，群 = LeaderID
# C.icc_rebuild(df, "LeaderID", ["BE","ME","Thr"], ["OCBS_L1",...,"OCBS_L6"],
#              "OCBS_L", mean=4.65, total_sd=1.193, icc=0.275,
#              r_tgt=[0.396, -0.319, 0.283], rng=rng)
print("（量表/多层 SEM 仿真用此 + halo_scale 控制两 outcome cross-corr）")
'''),
    "causal_dag_confounder": dict(desc="DAG 造混淆 + 比较未调整 vs 控变量回归", code='''
import calibrate as C, numpy as np
from numpy.linalg import lstsq
rng = np.random.default_rng(0)
df = C.dag_sample(5000, [
    ("U", lambda d,n,r: r.standard_normal(n)),
    ("X", lambda d,n,r: 0.6*d["U"] + r.standard_normal(n)),
    ("Y", lambda d,n,r: 0.4*d["X"] + 0.5*d["U"] + r.standard_normal(n)),
])
b1 = lstsq(np.column_stack([np.ones(len(df)), df.X]), df.Y, rcond=None)[0][1]
b2 = lstsq(np.column_stack([np.ones(len(df)), df.X, df.U]), df.Y, rcond=None)[0][1]
print(f"biased={b1:.3f}, controlled={b2:.3f} (true 0.40)")
'''),
    "panel_ab_test_with_did": dict(desc="DiD 估计处理效应", code='''
import calibrate as C
df = C.did_data(500, n_periods=2, treatment_time=1, treated_share=0.5,
                treatment_effect=0.7)
piv = df.pivot_table(index=["unit","treated"], columns="time", values="y").reset_index()
piv["delta"] = piv[1] - piv[0]
print("DiD estimate:", round(piv[piv.treated==1]["delta"].mean()
                              - piv[piv.treated==0]["delta"].mean(), 3))
'''),
    "relational_with_consistency_check": dict(desc="父子表 + 外键 / 聚合 / 时序校验", code='''
import calibrate as C, pandas as pd, numpy as np
rng = np.random.default_rng(0)
parents = pd.DataFrame({"user_id": C.generate_id_column(100, "U"),
                        "signup_age": rng.integers(20, 60, 100)})
orders = C.relational_children(parents, "user_id",
    n_per_parent=lambda r: r.poisson(3),
    child_cols={"amount": lambda p,i,r: 50 + 2*p.signup_age + r.normal(0,20)},
    rng=rng)
ok_ri, _ = C.check_referential_integrity(orders, "user_id", parents, "user_id")
print(f"# orders = {len(orders)}, FK integrity = {ok_ri}")
'''),
    "regression_with_target_r2": dict(desc="线性回归命中 target R²", code='''
import calibrate as C
df = C.regression_dataset(2000, coefs=[0.5, -0.3, 0.2], intercept=1.0, target_r2=0.5)
print(df.head())
'''),
    "ml_classification_benchmark": dict(desc="ML 分类基准 (target AUC + 类不平衡)", code='''
import calibrate as C
df = C.classification_dataset(3000, n_features=5, target_auc=0.85, class_balance=0.3)
print(f"shape={df.shape}, pos_prop={df.y.mean():.2f}")
'''),
    "synthesize_then_validate": dict(desc="声明 spec → generate → validate 命中", code='''
import calibrate as C
spec = {"n": 3000,
        "columns": [{"name":"age","dist":"truncnormal","mean":40,"sd":10,"lo":18,"hi":80},
                    {"name":"income","dist":"lognormal","mu":10,"sigma":0.5}],
        "correlations": {("age","income"): 0.4}}
df = C.generate_from_spec(spec)
print(C.validate(df, spec))
'''),
    "hierarchical_bayes_groups": dict(desc="多组 partial pooling 数据", code='''
import calibrate as C
df, truth = C.hierarchical_bayes_data(20, 30, hyper_mean=5.0, hyper_sd=1.0, within_sd=0.5)
print(df.groupby("group").y.mean().head(), truth.head())
'''),
    "graph_community_detection_bench": dict(desc="SBM 社区检测基准", code='''
import calibrate as C
edges, blocks = C.graph_sbm([30, 30, 40], p_in=0.5, p_out=0.05)
print(f"# edges = {len(edges)}, # nodes = {len(blocks)}, communities = {len(set(blocks))}")
'''),
    "ts_anomaly_benchmark": dict(desc="造带标签时序异常用于检测器评测", code='''
import calibrate as C
base = C.ts_ar(500, ar=(0.5,), sd=1.0)
x, y = C.ts_anomaly_inject(base, point_rate=0.02,
    level_shift=[(200, 3.0)], drift_at=400, drift_slope=0.05)
print(f"len={len(x)}, anomaly rate={y.mean():.3f}")
'''),
}


def list_recipes(): return [(n, r["desc"]) for n, r in RECIPES.items()]


def show_recipe(name):
    """Print the recipe code (also returns it)."""
    r = RECIPES.get(name)
    if r is None:
        from difflib import get_close_matches
        sug = get_close_matches(name, list(RECIPES), n=3)
        print(f"unknown recipe: {name!r}" + (f"; did you mean {sug}?" if sug else ""))
        return None
    print(f"--- {name}: {r['desc']} ---")
    print(r["code"])
    return r["code"]


# ---------- 3. Declarative spec-driven generator ----------
def generate_from_spec(spec, rng=None):
    """Declarative data generation. spec keys:
      n            : int, num rows
      columns      : list of {name, dist, ...params}, dist passed to sample_dist
      correlations : {(col_a, col_b): r}  — induced via Iman-Conover (preserves marginals)
      constraints  : list of constraint specs (applied post-hoc), each:
                     {"type": "monotone", "before": "...", "after": "..."}
                     {"type": "range", "col": "...", "lo": ..., "hi": ...}
                     {"type": "predicate", "name": "...", "fn": lambda d: bool_mask_GOOD}
                     {"action": "drop" | "report"}     (per-rule or default 'drop')
    Returns DataFrame."""
    import pandas as pd
    rng = rng or np.random.default_rng()
    n = spec["n"]; data = {}
    for col in spec.get("columns", []):
        name = col["name"]; dist = col.get("dist", "normal")
        params = {k: v for k, v in col.items() if k not in ("name", "dist")}
        data[name] = sample_dist(dist, n, rng=rng, **params)
    df = pd.DataFrame(data)
    # induce target correlations (preserves marginals)
    corr_spec = spec.get("correlations") or {}
    if corr_spec:
        cols = list(data.keys()); n_cols = len(cols); col_idx = {c: i for i, c in enumerate(cols)}
        R = np.eye(n_cols)
        for (a, b), r in corr_spec.items():
            i, j = col_idx[a], col_idx[b]; R[i, j] = R[j, i] = r
        X = iman_conover(df[cols].values, R, rng=rng)
        for k, c in enumerate(cols): df[c] = X[:, k]
    # apply constraints
    for c in spec.get("constraints", []):
        t = c["type"]
        if t == "monotone":
            bef, aft = c["before"], c["after"]
            rule = (f"monotone_{bef}_le_{aft}", lambda d, b=bef, a=aft: d[b] <= d[a])
        elif t == "range":
            col, lo, hi = c["col"], c.get("lo", -np.inf), c.get("hi", np.inf)
            rule = (f"range_{col}", lambda d, c=col, l=lo, h=hi: (d[c] >= l) & (d[c] <= h))
        elif t == "predicate":
            rule = (c.get("name", "predicate"), c["fn"])
        else:
            raise ValueError(f"unknown constraint type {t!r}")
        df, _ = enforce_constraints(df, [rule], action=c.get("action", "drop"), verbose=False)
    return df.reset_index(drop=True)


def validate(df, spec, tol=0.05, corr_tol=0.08):
    """Verify df satisfies the spec used to generate it. Returns dict with
    per-check PASS/FAIL + values. Pass to print() for human display."""
    report = {"distribution": [], "correlation": [], "constraint": [], "summary": ""}
    n_pass = 0; n_total = 0
    for col in spec.get("columns", []):
        name = col["name"]
        if name not in df.columns: continue
        if "mean" in col:
            ach = float(df[name].mean()); ok = abs(ach - col["mean"]) < tol * max(abs(col["mean"]), 1)
            report["distribution"].append((name, "mean", col["mean"], round(ach, 3), ok)); n_pass += ok; n_total += 1
        if "sd" in col:
            ach = float(df[name].std()); ok = abs(ach - col["sd"]) < tol * max(abs(col["sd"]), 0.1)
            report["distribution"].append((name, "sd", col["sd"], round(ach, 3), ok)); n_pass += ok; n_total += 1
        if "lo" in col:
            ach = float(df[name].min()); ok = ach >= col["lo"] - 1e-6
            report["distribution"].append((name, "min>=lo", col["lo"], round(ach, 3), ok)); n_pass += ok; n_total += 1
        if "hi" in col:
            ach = float(df[name].max()); ok = ach <= col["hi"] + 1e-6
            report["distribution"].append((name, "max<=hi", col["hi"], round(ach, 3), ok)); n_pass += ok; n_total += 1
    for (a, b), r in (spec.get("correlations") or {}).items():
        if a in df.columns and b in df.columns:
            ach = float(df[[a, b]].corr().iloc[0, 1])
            ok = abs(ach - r) < corr_tol
            report["correlation"].append((a, b, r, round(ach, 3), ok)); n_pass += ok; n_total += 1
    for c in spec.get("constraints", []):
        t = c["type"]
        if t == "monotone":
            bef, aft = c["before"], c["after"]
            v = (df[bef] <= df[aft]).all()
            report["constraint"].append((f"monotone {bef}<={aft}", bool(v))); n_pass += v; n_total += 1
        elif t == "range":
            col, lo, hi = c["col"], c.get("lo", -np.inf), c.get("hi", np.inf)
            v = ((df[col] >= lo) & (df[col] <= hi)).all()
            report["constraint"].append((f"range {col} in [{lo}, {hi}]", bool(v))); n_pass += v; n_total += 1
    report["summary"] = f"{n_pass}/{n_total} checks passed"
    return report


# ---------- 4. Seed manager (reproducibility) ----------
class Seed:
    """Global RNG manager. Use to make a whole script reproducible."""
    def __init__(self, seed=20260601): self.set(seed)
    def set(self, seed):
        self.seed = int(seed); self._rng = np.random.default_rng(self.seed)
        np.random.seed(self.seed)
    def rng(self): return self._rng
    def __repr__(self): return f"Seed(seed={self.seed})"


# ---------- 5. CLI ----------
def _cli(argv=None):
    import sys, json
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "help") and len(argv) == 1:
        print("calibrate CLI:")
        print("  python -m calibrate list [category]                 list functions")
        print("  python -m calibrate help <name>                     function signature + docstring")
        print("  python -m calibrate recipes                         list recipe names + descriptions")
        print("  python -m calibrate show-recipe <name>              print recipe code")
        print("  python -m calibrate sample <dist> <n> k=v k=v       quick one-column sample (prints summary)")
        print("  python -m calibrate generate <spec.json> [out.csv]  declarative generate -> csv")
        print("  python -m calibrate validate <data.csv> <spec.json> verify generated data hits spec")
        return
    cmd = argv[0]
    if cmd == "list":
        cat = argv[1] if len(argv) > 1 else None
        for c, n, d in list_functions(cat):
            print(f"  [{c:20s}] {n:35s} {d}")
    elif cmd == "help":
        show_help(argv[1])
    elif cmd == "recipes":
        for n, d in list_recipes(): print(f"  {n:35s} {d}")
    elif cmd == "show-recipe":
        show_recipe(argv[1])
    elif cmd == "sample":
        dist = argv[1]; n = int(argv[2])
        params = {}
        for kv in argv[3:]:
            k, v = kv.split("=")
            try: params[k] = float(v) if "." in v or "e" in v.lower() else int(v)
            except ValueError: params[k] = v
        x = sample_dist(dist, n, **params)
        print(f"dist={dist}, n={n}, mean={x.mean():.3f} sd={x.std():.3f} "
              f"min={x.min():.3f} max={x.max():.3f}")
    elif cmd == "generate":
        spec = json.load(open(argv[1])); df = generate_from_spec(spec)
        out = argv[2] if len(argv) > 2 else "generated.csv"
        df.to_csv(out, index=False); print(f"wrote {out} ({len(df)} rows × {len(df.columns)} cols)")
    elif cmd == "validate":
        import pandas as pd
        df = pd.read_csv(argv[1]); spec = json.load(open(argv[2]))
        r = validate(df, spec)
        for sec, items in r.items():
            if sec == "summary": continue
            for it in items: print(f"  [{sec}] {it}")
        print(r["summary"])
    else:
        print(f"unknown command: {cmd}; run 'help' for usage")


if __name__ == "__main__":
    _cli()


# ============================================================================
# HARNESS round 2: spec schema validation, friendlier errors, more recipes
# ============================================================================

class SpecError(ValueError):
    """Raised when generate_from_spec receives an invalid spec; message contains
    actionable hints (which key is wrong + what's allowed)."""


_VALID_DISTS = {"normal","lognormal","exponential","gamma","beta","weibull",
                "pareto","t","chi2","poisson","negbin","geometric","uniform","truncnormal"}
_REQUIRED_PARAMS = {
    "normal":   ["mean","sd"],   "lognormal":   ["mu","sigma"],
    "exponential": ["scale"],    "gamma":       ["shape"],
    "beta":     ["a","b"],       "weibull":     ["shape"],
    "pareto":   ["shape"],       "t":           ["df"],
    "chi2":     ["df"],          "poisson":     ["lam"],
    "negbin":   ["mean"],        "geometric":   ["p"],
    "uniform":  [],              "truncnormal": ["mean","sd"],
}


def validate_spec(spec):
    """Validate a `generate_from_spec` spec. Returns list of error messages
    (empty = OK). Use to lint specs before generation."""
    errs = []
    if not isinstance(spec, dict):
        return ["spec must be a dict"]
    if "n" not in spec or not isinstance(spec["n"], int) or spec["n"] <= 0:
        errs.append("spec['n'] must be a positive int")
    cols = spec.get("columns", [])
    if not isinstance(cols, list) or len(cols) == 0:
        errs.append("spec['columns'] must be a non-empty list of {name, dist, ...} dicts")
    names = []
    for i, c in enumerate(cols):
        if not isinstance(c, dict) or "name" not in c:
            errs.append(f"columns[{i}] must be a dict with 'name'"); continue
        names.append(c["name"])
        dist = c.get("dist", "normal")
        if dist not in _VALID_DISTS:
            from difflib import get_close_matches
            sug = get_close_matches(dist, list(_VALID_DISTS), n=2)
            errs.append(f"columns[{i}] ({c['name']!r}): unknown dist {dist!r}"
                        + (f"; did you mean {sug}?" if sug else f"; valid: {sorted(_VALID_DISTS)}"))
            continue
        missing = [p for p in _REQUIRED_PARAMS.get(dist, []) if p not in c]
        if missing:
            errs.append(f"columns[{i}] ({c['name']!r}, dist={dist!r}): missing required params {missing}")
    if len(set(names)) != len(names):
        errs.append(f"duplicate column names in spec: {[n for n in names if names.count(n) > 1]}")
    for pair, r in (spec.get("correlations") or {}).items():
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            errs.append(f"correlations key {pair!r} must be a (col_a, col_b) tuple")
            continue
        if pair[0] not in names or pair[1] not in names:
            errs.append(f"correlations references unknown column(s): {pair} (have: {names})")
        if not -1 < float(r) < 1:
            errs.append(f"correlations[{pair}] = {r} must be in (-1, 1)")
    for j, cs in enumerate(spec.get("constraints", [])):
        t = cs.get("type")
        if t not in {"monotone", "range", "predicate"}:
            errs.append(f"constraints[{j}].type {t!r} must be one of monotone/range/predicate")
            continue
        if t == "monotone":
            for k in ("before","after"):
                if cs.get(k) not in names:
                    errs.append(f"constraints[{j}] monotone: {k}={cs.get(k)!r} not in columns")
        elif t == "range":
            if cs.get("col") not in names:
                errs.append(f"constraints[{j}] range: col={cs.get('col')!r} not in columns")
    return errs


# Wrap generate_from_spec to validate first (graceful)
_generate_from_spec_raw = generate_from_spec
def generate_from_spec(spec, rng=None, strict=True):
    """Declarative data generation; validates spec first. On invalid spec
    raises SpecError with hints. Pass strict=False to skip validation."""
    if strict:
        errs = validate_spec(spec)
        if errs:
            raise SpecError("Invalid spec:\n  - " + "\n  - ".join(errs))
    return _generate_from_spec_raw(spec, rng=rng)


# ---------- Friendlier errors for primitives ----------
def _check_pd(R, name="matrix"):
    """Check positive-definiteness; return helpful message if not."""
    eig = np.linalg.eigvalsh(R)
    if eig.min() <= 0:
        return (f"{name} is not positive-definite (min eigenvalue = {eig.min():.4f}). "
                f"Use nearest_pd({name}) to project to nearest PD, or reduce off-diagonal "
                f"magnitudes (currently max |off-diag| = {abs(R - np.diag(np.diag(R))).max():.3f}).")
    return None


# ---------- More recipes (round 2) ----------
RECIPES.update({
    "target_skew_kurt": dict(desc="单列命中精确偏度+峰度（Fleishman）", code='''
import numpy as np, calibrate as C
rng = np.random.default_rng(0)
y = C.fleishman(rng.standard_normal(5000), skew=1.5, kurt=4.0)
print(f"achieved skew={C._skew(y):.2f} kurt={C._kurt(y):.2f}")
'''),
    "panel_did_event_study": dict(desc="DiD + event-study 验证 pre-trend", code='''
import calibrate as C
df = C.did_data(500, n_periods=4, treatment_time=2, treatment_effect=0.7)
# event-study: 估各 lag/lead 的均值差
delta = df.pivot_table(index=["unit","treated"], columns="time", values="y").reset_index()
for t in range(4):
    d = delta[delta.treated==1][t].mean() - delta[delta.treated==0][t].mean()
    print(f"  t={t}: treat-ctrl diff = {d:.3f} (post if t>=2: should be ≈0.7)")
'''),
    "recsys_cold_start_eval": dict(desc="Cold-start vs warm 推荐对比", code='''
import calibrate as C
U, V, obs, aff = C.cold_start_recsys(50, 30, user_dim=4, item_dim=4, history_per_user=3)
# 对每用户预测 affinity 用 U,V 内积；实际 affinity 在 aff 矩阵
pred = U @ V.T
print(f"corr(pred, true affinity) = {((pred - pred.mean()) * (aff - aff.mean())).sum() / (((pred - pred.mean())**2).sum() * ((aff - aff.mean())**2).sum())**.5:.3f}")
'''),
    "mmm_adstock_response": dict(desc="MMM 数据 → 估各渠道贡献", code='''
import calibrate as C
df = C.marketing_mix_data(52, channels={"tv":{"spend_sd":10,"beta":5.0},"social":{"spend_sd":5,"beta":3.0}})
# adstock_tv 已被构造；用线性回归估 contribution
from numpy.linalg import lstsq
import numpy as np
X = df[["adstock_tv","adstock_social"]].values
b = lstsq(np.column_stack([np.ones(len(df)), X]), df.y.values, rcond=None)[0]
print(f"baseline≈{b[0]:.1f}  tv coef≈{b[1]:.2f}  social coef≈{b[2]:.2f}")
'''),
    "irt_difficulty_recovery": dict(desc="IRT 2PL 数据 → 估题项难度", code='''
import calibrate as C
import numpy as np
b_true = np.linspace(-2, 2, 20)
X, theta = C.irt_2pl_data(1000, b_true, np.full(20, 1.5))
# 简单点估：b_hat ≈ Phi^-1(1 - p_correct)（在恒定 a, theta~N(0,1)）
p = X.mean(0); from statistics import NormalDist
nd = NormalDist()
b_hat = np.array([-nd.inv_cdf(p_) for p_ in p])
print(f"corr(b_true, b_hat) = {np.corrcoef(b_true, b_hat)[0,1]:.3f}")
'''),
    "snp_gwas_simulation": dict(desc="SNP + 简单表型 → 单点关联", code='''
import calibrate as C
import numpy as np
G = C.snp_genotypes(500, 50, maf=[0.3]*50, ld_strength=0.3)
# 表型 = beta · SNP_10 + 噪声
y = 0.5 * G[:, 10] + np.random.default_rng(0).standard_normal(500)
# 单点 t 统计
from numpy.linalg import lstsq
ts = []
for j in range(50):
    b = lstsq(np.column_stack([np.ones(500), G[:, j]]), y, rcond=None)[0]
    se = np.sqrt(((y - G[:, j]*b[1] - b[0])**2).sum() / (500-2) / (((G[:, j] - G[:, j].mean())**2).sum() or 1))
    ts.append(abs(b[1] / se))
print(f"top SNP (true causal=10): rank={np.argsort(ts)[::-1][0]} (top-1 should be 10)")
'''),
    "conformal_regression_interval": dict(desc="Conformal 回归预测区间 + 覆盖率", code='''
import calibrate as C
import numpy as np
rng = np.random.default_rng(0)
y_true = rng.standard_normal(500); y_pred = y_true + rng.normal(0, 0.5, 500)
q = C.conformal_calibration_set(y_pred, y_true, alpha=0.1, mode="regression")
cov = ((np.abs(y_true - y_pred) <= q).mean())
print(f"q={q:.3f}, empirical coverage = {cov:.3f} (target ≥ 0.9)")
'''),
    "drift_detector_psi_threshold": dict(desc="PSI 漂移检测：临界阈值评估", code='''
import calibrate as C
import numpy as np
rng = np.random.default_rng(0)
ref = rng.standard_normal(2000)
for shift in [0, 0.2, 0.5, 1.0]:
    cur = rng.standard_normal(2000) + shift
    print(f"shift={shift}: PSI={C.psi(ref, cur):.3f} → "
          + ("稳定" if C.psi(ref, cur) < 0.1 else "中度" if C.psi(ref, cur) < 0.25 else "严重"))
'''),
    "cluster_rct_power_sim": dict(desc="Cluster RCT 经验功效仿真（考虑 ICC 设计效应）", code='''
import calibrate as C
import numpy as np
rng = np.random.default_rng(0)
hits = 0
for _ in range(200):
    df = C.cluster_rct(20, 25, treatment_effect=0.3, icc=0.1, rng=rng)
    means = df.groupby(["cluster","treated"]).y.mean().reset_index().groupby("treated").y.mean()
    se = (df.groupby(["cluster","treated"]).y.mean().reset_index().groupby("treated").y.std() / np.sqrt(10)).fillna(1)
    if abs(means[1] - means[0]) / (se[0] + se[1]) > 1.96: hits += 1
print(f"empirical power = {hits/200:.0%}")
'''),
    "bayesian_metropolis_normal": dict(desc="Metropolis 后验：N(2, 1) toy", code='''
import calibrate as C
import numpy as np
chain = C.metropolis_posterior(lambda x: -0.5*(x-2)**2, x0=0, n_iter=5000, proposal_sd=0.5)
print(f"posterior mean={chain.mean():.2f} (target 2), sd={chain.std():.2f} (target 1)")
'''),
    "hawkes_aftershock": dict(desc="Hawkes 自激点过程：地震-余震模拟", code='''
import calibrate as C
events = C.hawkes_process(T_max=100, mu=1.0, alpha=0.4, beta=1.0)
gaps = events[1:] - events[:-1]
print(f"# events = {len(events)} (μT=100 base), median gap = {sorted(gaps)[len(gaps)//2]:.2f}")
'''),
    "lda_topic_recovery": dict(desc="LDA 文档 → 测主题恢复", code='''
import calibrate as C
import numpy as np
dtm, dt = C.lda_documents(200, 3, 80, doc_lengths=None)
# 简单 NMF 类近似：取 dtm 的前 3 个 SVD 分量
U, S, V = np.linalg.svd(dtm.astype(float), full_matrices=False)
print(f"top 3 SV: {S[:3].round(1)}, ratio to next: {S[2]/S[3]:.1f}")
'''),
    "knowledge_graph_with_schema": dict(desc="KG 三元组按 schema 限定类型", code='''
import calibrate as C
schema = {0: ({0}, {1}), 1: ({1}, {2}), 2: ({0,1}, {2})}
kg = C.knowledge_graph_triples(100, 3, 500, schema=schema)
print(f"# triples (schema-respecting): {len(kg)}, relations used: {sorted(kg.relation.unique())}")
'''),
    "multilevel_factor_with_icc": dict(desc="多层 ICC + Likert 题项 + halo cross-corr", code='''
# leader_survey_v2 中的工作流（icc_rebuild + 同 _S 共享 + 相反 sign）
print("详见 modules/multilevel.md §3 与 modules/engine.md §4，"
      "或 leader_survey_v2/code/rebuild_340.py")
'''),
    "synthesize_then_audit_realism": dict(desc="合成数据 → 用 discriminability 审真实度", code='''
import calibrate as C
import pandas as pd, numpy as np
rng = np.random.default_rng(0)
real = pd.DataFrame({"a": rng.lognormal(0, 1, 1500),
                     "b": rng.gamma(2, 2, 1500) + 0.4 * rng.lognormal(0, 1, 1500)})
syn = C.fit_from_reference(real, rng=rng)(1500)
print(f"discriminability AUC = {C.discriminability(real, syn):.3f}  (~0.50 = ✓)")
'''),
})


def all_recipes():
    """Return dict of all recipes including round-2 additions."""
    return dict(RECIPES)
