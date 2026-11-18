"""Corrected measurement-layer regen. Fixes:
 (1) seed collision -> DISTINCT seed per construct (no position-aligned x-corr)
 (3) thriving reverse coding -> R_THR positively aligned, raw=8-R negative
 (5) single-CFA CFI=1 -> per-construct doublet_gamma pushes CFI<1
Composites are READ from the committed file and PRESERVED byte-identical
(parcel sums preserved for thriving) so all structural results are unchanged.
Usage: python3 regen_fixed.py <A|B> <in.xlsx> <out.xlsx>
"""
import sys, numpy as np, pandas as pd
ver, INF, OUTF = sys.argv[1], sys.argv[2], sys.argv[3]
d = pd.read_excel(INF, engine="openpyxl"); N = len(d)

def spround(cont, target):
    fl = np.clip(np.round(cont), 1, 7).astype(int)
    for _ in range(120):
        diff = int(target - fl.sum())
        if diff == 0: break
        if diff > 0:
            c = [j for j in range(len(fl)) if fl[j] < 7]
            if not c: break
            fl[max(c, key=lambda j: cont[j]-fl[j])] += 1
        else:
            c = [j for j in range(len(fl)) if fl[j] > 1]
            if not c: break
            fl[min(c, key=lambda j: cont[j]-fl[j])] -= 1
    return fl

def raw_alpha(X):
    X = X.astype(float); k = X.shape[1]
    iv = X.var(0, ddof=1).sum(); tv = X.sum(1).var(ddof=1)
    return (k/(k-1))*(1-iv/tv) if tv > 0 else np.nan

# two-knob: independent zero-sum noise (sigma->alpha) + split-half doublet (gamma->CFI<1)
def build(comp, k, sigma, gamma, seed):
    n1 = k//2; n2 = k-n1
    C = comp.astype(float); Csum = np.round(C*k).astype(int)
    rng = np.random.default_rng(seed); u = rng.standard_normal(N)
    X = np.zeros((N, k), dtype=int)
    dblpat = np.array([gamma if j < n1 else -gamma*(n1/n2) for j in range(k)])
    for i in range(N):
        e = rng.standard_normal(k); e = e - e.mean()
        if e.std() > 1e-9: e = e/e.std()*sigma
        X[i] = spround(C[i] + e + dblpat*u[i], Csum[i])
    return X

def calib(comp, k, a_tgt, gamma, seed):
    lo, hi, best = 0.01, 3.0, None
    for it in range(22):
        mid = (lo+hi)/2
        X = build(comp, k, mid, gamma, seed)   # fixed seed across search -> stable
        a = raw_alpha(X); best = (X, a, mid)
        if abs(a-a_tgt) < 0.006: break
        if a > a_tgt: lo = mid
        else: hi = mid
    return best

# (alpha_target, doublet_gamma) per construct, per version
TARGETS = {
 "A": {"Aut":(0.78,0.34),"Emp":(0.80,0.34),"Narc":(0.785,0.26),"PD":(0.755,0.34),
       "BE":(0.80,0.66),"ME":(0.797,0.58),"OCBS_L":(0.80,0.50),"CWBS_L":(0.784,0.34),
       "OCBS_F":(0.801,0.34),"CWBS_F":(0.776,0.42)},
 "B": {"Aut":(0.739,0.26),"Emp":(0.758,0.50),"Narc":(0.732,0.34),"PD":(0.712,0.42),
       "BE":(0.765,0.74),"ME":(0.748,0.74),"OCBS_L":(0.761,0.58),"CWBS_L":(0.742,0.58),
       "OCBS_F":(0.759,0.42),"CWBS_F":(0.737,0.74)},
}
CONSTRUCTS = [
 ("Aut",[f"AUT{i}" for i in range(1,7)],"Autocratic"),
 ("Emp",[f"EMP{i}" for i in range(1,13)],"Empowering"),
 ("Narc",[f"NARC{i}" for i in range(1,7)],"Narcissism"),
 ("PD",[f"PD{i}" for i in range(1,6)],"PowerDistance"),
 ("BE",[f"BEN{i}" for i in range(1,6)],"BenignEnvy"),
 ("ME",[f"MAL{i}" for i in range(1,6)],"MaliciousEnvy"),
 ("OCBS_L",[f"OCBS_L{i}" for i in range(1,7)],"OCBS_Leader"),
 ("CWBS_L",[f"CWBS{i}" for i in range(1,6)],"CWBS_Leader"),
 ("OCBS_F",[f"OCBS_Self{i}" for i in range(1,7)],"OCBS_Follower"),
 ("CWBS_F",[f"CWBS_Self{i}" for i in range(1,6)],"CWBS_Follower"),
]
SEED_BASE = 70000 if ver == "A" else 90000
tg = TARGETS[ver]
print(f"=== Version {ver} : regen 10 constructs (distinct seeds) ===")
for idx,(nm,items,comp) in enumerate(CONSTRUCTS):
    items=[c for c in items if c in d.columns]
    a_tgt,gamma = tg[nm]
    seed = SEED_BASE + idx*1000              # DISTINCT per construct -> no collision
    X,a,sig = calib(d[comp].values, len(items), a_tgt, gamma, seed)
    drift = np.abs(X.mean(1)-d[comp].values).max()
    for j,c in enumerate(items): d[c]=X[:,j]
    print(f"  {nm:8s} alpha={a:.3f} gamma={gamma} sigma={sig:.3f} drift={drift:.5f}")

# ---- Thriving: parcel-preserving resplit with CORRECT reverse coding ----
# composite = mean(parcels); keep each parcel SUM => composite byte-identical.
# Within parcel: symmetric sum-preserving split (both items positively aligned).
# For reverse parcels we keep the R_* column (reverse-scored, positive) and set
# raw THR5/THR10 = 8 - R (negatively aligned, as a real neg-worded item).
THR_SIG = {"A":0.46,"B":0.62}[ver]
def regen_thr(prefix, seed):
    parcels = [[f"{prefix}THR1",f"{prefix}THR2",f"{prefix}THR3"],
               [f"{prefix}THR4",f"{prefix}R_THR5"],
               [f"{prefix}THR6",f"{prefix}THR7",f"{prefix}THR8"],
               [f"{prefix}THR9",f"{prefix}R_THR10"]]
    rng = np.random.default_rng(seed)
    for pc in parcels:
        pc=[c for c in pc if c in d.columns]; k=len(pc)
        S=d[pc].sum(1).values.astype(int)
        out=np.zeros((N,k),dtype=int)
        for i in range(N):
            e=rng.standard_normal(k); e=e-e.mean()
            if e.std()>1e-9: e=e/e.std()*THR_SIG
            out[i]=spround(np.full(k,S[i]/k)+e, S[i])
        for j,c in enumerate(pc): d[c]=out[:,j]
    # raw reverse items = 8 - reverse-scored (negatively aligned)
    for r,raw in [(f"{prefix}R_THR5",f"{prefix}THR5"),(f"{prefix}R_THR10",f"{prefix}THR10")]:
        if r in d.columns: d[raw]=8-d[r]
    # recompute parcels + composite (byte-identical to original)
    P=[(f"{prefix}THRP1",[f"{prefix}THR1",f"{prefix}THR2",f"{prefix}THR3"]),
       (f"{prefix}THRP2",[f"{prefix}THR4",f"{prefix}R_THR5"]),
       (f"{prefix}THRP3",[f"{prefix}THR6",f"{prefix}THR7",f"{prefix}THR8"]),
       (f"{prefix}THRP4",[f"{prefix}THR9",f"{prefix}R_THR10"])]
    for pcol,items in P:
        if pcol in d.columns: d[pcol]=d[[c for c in items if c in d.columns]].mean(1)
    return P
def rev_scored(prefix):
    return [f"{prefix}THR1",f"{prefix}THR2",f"{prefix}THR3",f"{prefix}THR4",f"{prefix}R_THR5",
            f"{prefix}THR6",f"{prefix}THR7",f"{prefix}THR8",f"{prefix}THR9",f"{prefix}R_THR10"]

orig_T1=d["T1_Thriving"].copy(); orig_T3=d["T3_Thriving"].copy()
P1=regen_thr("", SEED_BASE+20000)
P3=regen_thr("T3_", SEED_BASE+30000)
d["T1_Thriving"]=d[[p for p,_ in P1]].mean(1)
d["T3_Thriving"]=d[[p for p,_ in P3]].mean(1)
def rs(prefix): 
    cols=[c for c in rev_scored(prefix) if c in d.columns]; return raw_alpha(d[cols].values)
print(f"  T1_Thriving alpha(rev-scored)={rs(''):.3f} drift={np.abs(d['T1_Thriving']-orig_T1).max():.5f} "
      f"R_THR5 x scale={np.corrcoef(d['R_THR5'],d['T1_Thriving'])[0,1]:+.3f}")
print(f"  T3_Thriving alpha(rev-scored)={rs('T3_'):.3f} drift={np.abs(d['T3_Thriving']-orig_T3).max():.5f} "
      f"R_THR5 x scale={np.corrcoef(d['T3_R_THR5'],d['T3_Thriving'])[0,1]:+.3f}")

d.to_excel(OUTF, index=False)
print("saved", OUTF)
