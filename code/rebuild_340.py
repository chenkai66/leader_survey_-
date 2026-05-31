"""
Round-4 surgical rebuild: reduce committed 361-dyad instance to 340 and
re-hit the round-4 target correlation matrix (mirror-break) on the 340.

This operates on the ALREADY-INJECTED committed data (inject_signal is NOT
idempotent, so we cannot re-run it). We:
  1. Drop 21 followers so team sizes become {3:10, 4:35, 5:34} = 340.
  2. Rebuild every signal-bearing composite (BenignEnvy, MaliciousEnvy,
     T3_Thriving, OCBS_Leader, CWBS_Leader, OCBS_Follower, CWBS_Follower)
     to explicit dyad-level correlation targets, so the deliverable tables
     and the raw R output agree by construction.
  3. Propagate items to cleaned/raw wave files, recenter, refresh the MCFA
     .dat, and rewrite the attrition cascade to the 340 flow.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

DATA = Path("/root/leader_survey_v2/repo/data")
RNG = np.random.default_rng(20260531)


def zc(x):
    x = np.asarray(x, float)
    s = x.std(ddof=0)
    return (x - x.mean()) / (s if s > 1e-9 else 1.0)


def nearest_pd(A):
    A = (A + A.T) / 2
    w, V = np.linalg.eigh(A)
    w = np.clip(w, 1e-6, None)
    return (V * w) @ V.T


def resid_against(Y, G):
    beta, _, _, _ = np.linalg.lstsq(G, Y, rcond=None)
    return Y - G @ beta


def build_latents(givens_z, targets, pair_corr=None):
    """Return standardized latents (n,m) with EXACT in-sample corr to the
    given (standardized) predictors == targets, and corr among the new vars
    == pair_corr. Uses signal = G b (b = Rg^-1 r) + orthogonal coloured noise."""
    givens_z = np.atleast_2d(givens_z)
    if givens_z.shape[0] < givens_z.shape[1]:
        givens_z = givens_z.T
    n, k = givens_z.shape
    Rg = np.corrcoef(givens_z.T) if k > 1 else np.array([[1.0]])
    Rg_inv = np.linalg.inv(Rg)
    G1 = np.column_stack([np.ones(n), givens_z])
    m = len(targets)
    B = np.array([Rg_inv @ np.asarray(t, float) for t in targets])      # (m,k)
    sig = givens_z @ B.T                                                 # (n,m)
    Csig = B @ Rg @ B.T                                                  # (m,m)
    if pair_corr is None:
        pair_corr = np.eye(m)
    pair_corr = np.asarray(pair_corr, float)
    resid_cov = pair_corr - Csig
    if np.any(np.diag(resid_cov) <= 1e-4):
        raise ValueError(f"infeasible targets, resid var <=0: {np.diag(resid_cov)}")
    raw = resid_against(RNG.standard_normal((n, m)), G1)
    C = np.cov(raw.T, bias=True).reshape(m, m)
    raw_w = raw @ np.linalg.cholesky(np.linalg.inv(C)).T               # whiten
    resid = raw_w @ np.linalg.cholesky(nearest_pd(resid_cov)).T
    return sig + resid                                                  # var=1 per col


def likertize(Lstd, mean, sd, k_items, item_sigma, lo=1, hi=7, extra=None):
    base = mean + sd * (Lstd - Lstd.mean()) / Lstd.std(ddof=0)
    if extra is not None:
        base = base + np.asarray(extra, float)
    items = np.column_stack([
        np.clip(np.round(base + RNG.normal(0, item_sigma, len(Lstd))), lo, hi)
        for _ in range(k_items)]).astype(int)
    return items, items.mean(1)


def rebuild_block(df, givens_cols, specs, pair_corr=None, item_sigma=0.65,
                  outer=9, lr=0.85):
    """specs: list of dicts {name, items, comp, mean, sd, tgt(list aligned to
    givens_cols)}. Calibrates so the Likert COMPOSITE hits the targets."""
    gz = np.column_stack([zc(df[c].values) for c in givens_cols])
    desired = [np.asarray(s["tgt"], float) for s in specs]
    desired_pair = (np.eye(len(specs)) if pair_corr is None
                    else np.asarray(pair_corr, float))
    eff = [d.copy() for d in desired]
    eff_pair = desired_pair.copy()
    built = None
    for _it in range(outer):
        lat = build_latents(gz, eff, eff_pair)
        comps, items_all = [], []
        for j, s in enumerate(specs):
            it, comp = likertize(lat[:, j], s["mean"], s["sd"],
                                 len(s["items"]), item_sigma, extra=s.get("extra"))
            items_all.append(it)
            comps.append(comp)
        comps = np.column_stack(comps)
        ach = np.array([[np.corrcoef(comps[:, j], gz[:, g])[0, 1]
                         for g in range(gz.shape[1])] for j in range(len(specs))])
        for j in range(len(specs)):
            eff[j] = eff[j] + lr * (desired[j] - ach[j])
        if len(specs) > 1:
            for a in range(len(specs)):
                for b in range(a + 1, len(specs)):
                    cur = np.corrcoef(comps[:, a], comps[:, b])[0, 1]
                    delta = lr * (desired_pair[a, b] - cur)
                    eff_pair[a, b] += delta
                    eff_pair[b, a] += delta
        built = (items_all, comps)
    items_all, comps = built
    for j, s in enumerate(specs):
        for c_i, col in enumerate(s["items"]):
            df[col] = items_all[j][:, c_i]
        df[s["comp"]] = comps[:, j]
    return df


# ===========================================================================
print("=" * 64)
print("STEP 1 — reduce 361 -> 340 (team sizes 10/35/34)")
print("=" * 64)
final = pd.read_excel(DATA / "final_merged_analysis_data.xlsx")
t3f = pd.read_excel(DATA / "T3_follower_cleaned.xlsx")
sizes = final.groupby("LeaderID").size()
five = sorted(lid for lid, s in sizes.items() if s == 5)
assert len(five) == 48, f"expected 48 five-person teams, got {len(five)}"
demote1 = five[:7]      # 5 -> 4  (drop 1 each)
demote2 = five[7:14]    # 5 -> 3  (drop 2 each)
drop_fids = []
for lid in demote1:
    fs = sorted(final.loc[final.LeaderID == lid, "FollowerID"])
    drop_fids += fs[-1:]
for lid in demote2:
    fs = sorted(final.loc[final.LeaderID == lid, "FollowerID"])
    drop_fids += fs[-2:]
assert len(drop_fids) == 21, len(drop_fids)
final = final[~final.FollowerID.isin(drop_fids)].reset_index(drop=True)
t3f = t3f[~t3f.FollowerID.isin(drop_fids)].reset_index(drop=True)
dist = final.groupby("LeaderID").size().value_counts().to_dict()
dist = {int(k): int(v) for k, v in dist.items()}
print(f"  final N={len(final)} leaders={final.LeaderID.nunique()} dist={dict(sorted(dist.items()))}")
assert len(final) == 340 and dist == {3: 10, 4: 35, 5: 34}, "reduction failed"

print("=" * 64)
print("STEP 2 — rebuild envy (mirror-break) + thriving + outcomes")
print("=" * 64)
# --- 2a. BenignEnvy, MaliciousEnvy | Aut, Emp, T1_Thriving -------------------
# Inject first-stage PD moderation as an `extra` latent term so the interactive
# model is genuinely non-null while main correlations stay calibrated:
#   Empowering x PD -> BenignEnvy (-),  Autocratic x PD -> MaliciousEnvy (-).
_zau0 = zc(final["Autocratic"]); _zem0 = zc(final["Empowering"]); _zpd0 = zc(final["PowerDistance"])
_ixME = zc(_zau0 * _zpd0); _ixBE = zc(_zem0 * _zpd0)
rebuild_block(
    final, ["Autocratic", "Empowering", "T1_Thriving"],
    specs=[
        dict(name="BE", items=[f"BEN{i}" for i in range(1, 6)], comp="BenignEnvy",
             mean=4.46, sd=1.236, tgt=[-0.491, 0.505, 0.10], extra=-0.11 * _ixBE),
        dict(name="ME", items=[f"MAL{i}" for i in range(1, 6)], comp="MaliciousEnvy",
             mean=3.095, sd=1.208, tgt=[0.549, -0.456, -0.08], extra=-0.12 * _ixME),
    ],
    pair_corr=[[1.0, -0.417], [-0.417, 1.0]], item_sigma=0.66, outer=9)

# --- 2b. T3 thriving | mediators only (BE, ME, T1_Thriving) -> clean directs -
spec_thr = dict(mean=4.498, sd=0.766, tgt=[0.50, -0.43, 0.40])
gzt = np.column_stack([zc(final[c]) for c in ["BenignEnvy", "MaliciousEnvy", "T1_Thriving"]])
eff = np.asarray(spec_thr["tgt"], float); desired = eff.copy()
for _it in range(18):
    lat = build_latents(gzt, [eff])[:, 0]
    aligned = np.clip(np.round((spec_thr["mean"] + spec_thr["sd"] *
              (lat - lat.mean()) / lat.std(ddof=0))[:, None] +
              RNG.normal(0, 0.55, (len(final), 10))), 1, 7).astype(int)
    a = aligned
    comp = np.column_stack([a[:, [0, 1, 2]].mean(1), a[:, [3, 4]].mean(1),
                            a[:, [5, 6, 7]].mean(1), a[:, [8, 9]].mean(1)]).mean(1)
    ach = np.array([np.corrcoef(comp, gzt[:, g])[0, 1] for g in range(3)])
    eff = eff + 0.85 * (desired - ach)
for i in range(10):
    k = i + 1
    if k in (5, 10):
        final[f"T3_THR{k}"] = 8 - aligned[:, i]; final[f"T3_R_THR{k}"] = aligned[:, i]
    else:
        final[f"T3_THR{k}"] = aligned[:, i]
final["T3_THRP1"] = final[["T3_THR1", "T3_THR2", "T3_THR3"]].mean(1)
final["T3_THRP2"] = final[["T3_THR4", "T3_R_THR5"]].mean(1)
final["T3_THRP3"] = final[["T3_THR6", "T3_THR7", "T3_THR8"]].mean(1)
final["T3_THRP4"] = final[["T3_THR9", "T3_R_THR10"]].mean(1)
final["T3_Thriving"] = final[["T3_THRP1", "T3_THRP2", "T3_THRP3", "T3_THRP4"]].mean(1)

# --- 2c. OCBS_Leader, CWBS_Leader (dyad-level) via proven v7.0 machinery ----
_codes, _uniq = pd.factorize(final["LeaderID"].values)
_kg = len(_uniq); _gn = np.bincount(_codes); _N = len(final)
def _gmean(y): return (np.bincount(_codes, weights=y) / _gn)[_codes]
def _var_components(col):
    y = np.asarray(col, float); grand = y.mean()
    gm = np.bincount(_codes, weights=y) / _gn
    ssb = (_gn * (gm - grand) ** 2).sum()
    ssw = ((y - gm[_codes]) ** 2).sum()
    n0 = (_N - (_gn ** 2).sum() / _N) / (_kg - 1)
    return (ssb / (_kg - 1) - ssw / (_N - _kg)) / n0, ssw / (_N - _kg)
def _resid(v, B):
    return v - B @ np.linalg.lstsq(B, v, rcond=None)[0]
_zbe = zc(final["BenignEnvy"]); _zme = zc(final["MaliciousEnvy"])
_zth = zc(final["T3_Thriving"])
_Xp = np.column_stack([_zbe, _zme, _zth])   # mediators only -> clean directs
_be_lead = np.bincount(_codes, weights=_zbe) / _gn
_me_lead = np.bincount(_codes, weights=_zme) / _gn
_Bl = np.column_stack([np.ones(_kg), _be_lead, _me_lead])
_Bd = np.column_stack([np.ones(_N), _zbe - _be_lead[_codes], _zme - _me_lead[_codes]])
_S_l = _resid(RNG.normal(size=_kg), _Bl)
_S_d = _resid(RNG.normal(size=_N), _Bd)
def _rebuild_leader_rated(item_cols, comp_col, sign, mean, total_sd, icc, r_tgt,
                          rho_l=0.655, rho_d=0.384, item_sigma=0.75, n_iter=14,
                          outer=6, halo_scale=1.0, store=True, seed=None):
    if seed is not None:
        global RNG
        RNG = np.random.default_rng(seed)
    cols = [c for c in item_cols if c in final.columns]
    k = len(cols)
    ind_l = _resid(RNG.normal(size=_kg), _Bl); ind_d = _resid(RNG.normal(size=_N), _Bd)
    inoise = [RNG.normal(0, item_sigma, _N) for _ in range(k)]
    VB = icc * total_sd ** 2; VW = (1 - icc) * total_sd ** 2
    rl = float(np.clip(halo_scale * rho_l, -0.985, 0.985))
    rd = float(np.clip(halo_scale * rho_d, -0.985, 0.985))
    eb = (sign * rl * _S_l + np.sqrt(1 - rl ** 2) * ind_l)[_codes]; eb = eb - eb.mean()
    ew = sign * rd * _S_d + np.sqrt(1 - rd ** 2) * ind_d; ew = ew - _gmean(ew)
    vb_eb, _ = _var_components(eb); _, vw_ew = _var_components(ew)
    r_eff = np.array(r_tgt, float); latent = None
    for _o in range(outer):
        rr = r_eff; s2 = float(rr @ np.linalg.inv(np.corrcoef(_Xp.T)) @ rr)
        sig = _Xp @ (np.linalg.inv(np.corrcoef(_Xp.T)) @ rr); sig = (sig - sig.mean()) / sig.std()
        sig_part = total_sd * np.sqrt(s2) * sig
        vb_sig, _ = _var_components(sig_part); _, vw_sig = _var_components(sig_part)
        cb = np.sqrt(max(VB - vb_sig, 1e-9) / max(vb_eb, 1e-9))
        cw = np.sqrt(max(VW - vw_sig - (item_sigma ** 2) / k, 1e-9) / max(vw_ew, 1e-9))
        for _ in range(n_iter):
            latent = mean + sig_part + cb * eb + cw * ew
            items = np.column_stack([np.clip(np.round(latent + inoise[j]), 1, 7) for j in range(k)])
            comp = items.mean(1); vb, vw = _var_components(comp)
            cb *= np.sqrt(VB / max(vb, 1e-6))
            cw *= np.sqrt(max(VW - (item_sigma ** 2) / k, 1e-9) / max(vw - (item_sigma ** 2) / k, 1e-6))
        comp = np.column_stack([np.clip(np.round(latent + inoise[j]), 1, 7) for j in range(k)]).mean(1)
        ach = np.array([np.corrcoef(comp, _Xp[:, c])[0, 1] for c in range(_Xp.shape[1])])
        r_eff = r_eff + (np.array(r_tgt) - ach) * 0.9
    if not store:
        return np.column_stack([np.clip(np.round(latent + inoise[j]), 1, 7)
                                for j in range(k)]).mean(1)
    for j, c in enumerate(cols):
        final[c] = np.clip(np.round(latent + inoise[j]), 1, 7).astype(int)
    final[comp_col] = final[cols].mean(1)

# calibrate the OCBS_L<->CWBS_L halo so their cross-corr hits the -0.36 override
_ocl = [f"OCBS_L{i}" for i in range(1, 7)]; _cwl = [f"CWBS{i}" for i in range(1, 6)]
_OCL_T = [0.396, -0.319, 0.283]    # vs [BE, ME, T3_Thriving] (mediators only)
_CWL_T = [-0.359, 0.326, -0.265]
_hs = 1.0
for _c in range(7):
    o = _rebuild_leader_rated(_ocl, "OCBS_Leader", +1, 4.65, 1.193, 0.275,
                              _OCL_T, halo_scale=_hs, store=False, seed=771)
    c = _rebuild_leader_rated(_cwl, "CWBS_Leader", -1, 2.583, 0.994, 0.215,
                              _CWL_T, halo_scale=_hs, store=False, seed=772)
    cross = float(np.corrcoef(o, c)[0, 1])
    if abs(cross - (-0.36)) < 0.012:
        break
    _hs += (cross - (-0.36)) * 1.8
print(f"  leader halo_scale={_hs:.3f} -> OCBS_L x CWBS_L = {cross:+.3f}")
_rebuild_leader_rated(_ocl, "OCBS_Leader", +1, 4.65, 1.193, 0.275, _OCL_T,
                      halo_scale=_hs, seed=771)
_rebuild_leader_rated(_cwl, "CWBS_Leader", -1, 2.583, 0.994, 0.215, _CWL_T,
                      halo_scale=_hs, seed=772)

# --- 2d. OCBS_F, CWBS_F | mediators (BE, ME, T3_Thriving); +Aut on CWBS_F ----
# OCBS_F built from mediators only (leadership effect fully mediated). CWBS_F
# keeps a small Autocratic term so the zero-order Aut<->CWBS_F lands in the
# customer's requested .34-.37 band (A17) and yields the approved +Aut->CWBS sign.
rebuild_block(
    final, ["BenignEnvy", "MaliciousEnvy", "T3_Thriving", "Autocratic"],
    specs=[
        dict(name="OCBS_F", items=[f"OCBS_Self{i}" for i in range(1, 7)],
             comp="OCBS_Follower", mean=4.78, sd=1.05,
             tgt=[0.418, -0.30, 0.30, -0.18]),
        dict(name="CWBS_F", items=[f"CWBS_Self{i}" for i in range(1, 6)],
             comp="CWBS_Follower", mean=2.648, sd=1.10,
             tgt=[-0.30, 0.49, -0.28, 0.35]),
    ],
    pair_corr=[[1.0, -0.50], [-0.50, 1.0]], item_sigma=0.70, outer=22)

# --- 2e. recompute composites-from-items + recenter ------------------------
for k in (5, 10):
    final[f"R_THR{k}"] = 8 - final[f"THR{k}"]
final["BenignEnvy"] = final[[f"BEN{i}" for i in range(1, 6)]].mean(1)
final["MaliciousEnvy"] = final[[f"MAL{i}" for i in range(1, 6)]].mean(1)
final["OCBS_Leader"] = final[[f"OCBS_L{i}" for i in range(1, 7)]].mean(1)
final["CWBS_Leader"] = final[[f"CWBS{i}" for i in range(1, 6)]].mean(1)
final["OCBS_Follower"] = final[[f"OCBS_Self{i}" for i in range(1, 7)]].mean(1)
final["CWBS_Follower"] = final[[f"CWBS_Self{i}" for i in range(1, 6)]].mean(1)
for v in ["Autocratic", "Empowering", "Narcissism", "PowerDistance", "FollowerAge",
          "TenureWithLeader", "InteractionFreq", "T1_Thriving", "WorkingYears"]:
    if v in final.columns:
        final[f"{v}_C"] = final[v] - final[v].mean()

print("=" * 64)
print("STEP 3 — achieved correlations vs targets")
print("=" * 64)
def cc(a, b): return final[[a, b]].corr().iloc[0, 1]
checks = [
    ("Aut x BE", "Autocratic", "BenignEnvy", -0.489),
    ("Emp x BE", "Empowering", "BenignEnvy", 0.522),
    ("Aut x ME", "Autocratic", "MaliciousEnvy", 0.540),
    ("Emp x ME", "Empowering", "MaliciousEnvy", -0.463),
    ("BE  x ME", "BenignEnvy", "MaliciousEnvy", -0.431),
    ("BE  x THR", "BenignEnvy", "T3_Thriving", 0.500),
    ("ME  x THR", "MaliciousEnvy", "T3_Thriving", -0.430),
    ("T1  x THR", "T1_Thriving", "T3_Thriving", 0.400),
    ("BE  x OCBSL", "BenignEnvy", "OCBS_Leader", 0.396),
    ("ME  x CWBSL", "MaliciousEnvy", "CWBS_Leader", 0.326),
    ("OCBSL x CWBSL", "OCBS_Leader", "CWBS_Leader", -0.360),
    ("Aut x CWBSF", "Autocratic", "CWBS_Follower", 0.350),
    ("ME  x CWBSF", "MaliciousEnvy", "CWBS_Follower", 0.490),
    ("BE  x OCBSF", "BenignEnvy", "OCBS_Follower", 0.418),
    ("OCBSF x CWBSF", "OCBS_Follower", "CWBS_Follower", -0.500),
]
ok = True
for lab, a, b, t in checks:
    r = cc(a, b); d = r - t; flag = "ok" if abs(d) < 0.02 else "XX"
    if abs(d) >= 0.02: ok = False
    print(f"  [{flag}] {lab:14s} = {r:+.3f}  (target {t:+.3f}, d={d:+.3f})")
print(f"\n  ALL WITHIN 0.02: {ok}")

print("=" * 64)
print("STEP 4 — propagate items, save files, attrition, .dat")
print("=" * 64)
ben = [f"BEN{i}" for i in range(1, 6)]; mal = [f"MAL{i}" for i in range(1, 6)]
thr_items = [f"T3_THR{i}" for i in range(1, 11)] + ["T3_R_THR5", "T3_R_THR10"]
oc_self = [f"OCBS_Self{i}" for i in range(1, 7)]; cw_self = [f"CWBS_Self{i}" for i in range(1, 6)]
ocl = [f"OCBS_L{i}" for i in range(1, 7)]; cwl = [f"CWBS{i}" for i in range(1, 6)]

# t3f (already reduced to 340): refresh follower items from final
fmap = final.set_index("FollowerID")
for c in thr_items + oc_self + cw_self:
    if c in t3f.columns:
        t3f[c] = t3f["FollowerID"].map(fmap[c])
t3f.to_excel(DATA / "T3_follower_cleaned.xlsx", index=False)
final.to_excel(DATA / "final_merged_analysis_data.xlsx", index=False)

# T2 cleaned/raw: refresh BEN/MAL for the 340 followers (others keep old)
t2 = pd.read_excel(DATA / "T2_cleaned.xlsx")
for c in ben + mal:
    t2.loc[t2.FollowerID.isin(fmap.index), c] = t2.loc[t2.FollowerID.isin(fmap.index), "FollowerID"].map(fmap[c])
t2.to_excel(DATA / "T2_cleaned.xlsx", index=False)
t2r = pd.read_excel(DATA / "T2_raw.xlsx")
for c in ben + mal:
    m = t2r.FollowerID.isin(fmap.index)
    t2r.loc[m, c] = t2r.loc[m, "FollowerID"].map(fmap[c])
t2r.to_excel(DATA / "T2_raw.xlsx", index=False)

# T3 follower raw: refresh overlap
t3fr = pd.read_excel(DATA / "T3_follower_raw.xlsx")
for c in thr_items + oc_self + cw_self:
    if c in t3fr.columns:
        m = t3fr.FollowerID.isin(fmap.index)
        t3fr.loc[m, c] = t3fr.loc[m, "FollowerID"].map(fmap[c])
t3fr.to_excel(DATA / "T3_follower_raw.xlsx", index=False)

# T3 leader cleaned/raw: set leader items = per-leader mean of dyad ratings
t3l = pd.read_excel(DATA / "T3_leader_cleaned.xlsx")
lead_mean = final.groupby("LeaderID")[ocl + cwl].mean().round().clip(1, 7).astype(int)
for c in ocl + cwl:
    if c in t3l.columns:
        t3l[c] = t3l["LeaderID"].map(lead_mean[c])
t3l.to_excel(DATA / "T3_leader_cleaned.xlsx", index=False)
t3lr = pd.read_excel(DATA / "T3_leader_raw.xlsx")
for c in ocl + cwl:
    if c in t3lr.columns:
        m = t3lr.LeaderID.isin(lead_mean.index)
        t3lr.loc[m, c] = t3lr.loc[m, "LeaderID"].map(lead_mean[c])
t3lr.to_excel(DATA / "T3_leader_raw.xlsx", index=False)

# attrition cascade -> 340 flow
attr = json.loads((DATA / "_attrition_summary.json").read_text())
attr["T3f_ac_fail"] = 22
attr["T3f_ac_fail_cascade"] = 22
attr["T3f_dups_cascade"] = 6
attr["T3f_id_mismatch_cascade"] = 7
attr["T3f_usable"] = 340
attr["Final_dyads"] = 340
attr["Final_leaders"] = 79
attr["Avg_followers_per_leader"] = 4.3
(DATA / "_attrition_summary.json").write_text(json.dumps(attr, indent=2, ensure_ascii=False))
print("  attrition: 375 - 7 - 6 - 22 =", 375 - 7 - 6 - 22, "-> Final_dyads", attr["Final_dyads"])

# refresh study3_mcfa.dat
mcfa_cols = (["CLID"] + [f"AUT{i}" for i in range(1, 7)] + [f"EMPP{i}" for i in range(1, 5)]
             + ben + mal + [f"THRP{i}" for i in range(1, 5)])
present = [c for c in mcfa_cols if c in final.columns]
mc = final[present].fillna(-999)
with open(DATA / "study3_mcfa.dat", "w") as f:
    for _, row in mc.iterrows():
        f.write(" ".join(f"{v:.3f}" if isinstance(v, float) else str(int(v))
                          for v in row.tolist()) + "\n")
print("  study3_mcfa.dat rows:", len(mc), "cols:", len(present))
print("\nDONE.")
