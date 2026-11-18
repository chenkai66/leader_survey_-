"""Propagate regenerated items from final_merged_analysis_data.xlsx to all wave
files (T1/T2/T3-follower by FollowerID; T3-leader rebuilt WIDE from dyad data in
final_merged), recompute parcels, refresh Mplus .dat. Run AFTER copying the
regenerated final_merged into data/."""
import pandas as pd, numpy as np
from pathlib import Path
DATA = Path("/root/leader_survey_v2/repo/data")
d = pd.read_excel(DATA / "final_merged_analysis_data.xlsx", engine="openpyxl")

# --- recompute parcels in final_merged (EMPP stale after EMP regen) ---
for p in range(4):
    d[f"EMPP{p+1}"] = d[[f"EMP{3*p+1}", f"EMP{3*p+2}", f"EMP{3*p+3}"]].mean(1)
d["THRP1"]=d[["THR1","THR2","THR3"]].mean(1); d["THRP2"]=d[["THR4","R_THR5"]].mean(1)
d["THRP3"]=d[["THR6","THR7","THR8"]].mean(1); d["THRP4"]=d[["THR9","R_THR10"]].mean(1)
d["T3_THRP1"]=d[["T3_THR1","T3_THR2","T3_THR3"]].mean(1); d["T3_THRP2"]=d[["T3_THR4","T3_R_THR5"]].mean(1)
d["T3_THRP3"]=d[["T3_THR6","T3_THR7","T3_THR8"]].mean(1); d["T3_THRP4"]=d[["T3_THR9","T3_R_THR10"]].mean(1)
d.to_excel(DATA / "final_merged_analysis_data.xlsx", index=False)

REGEN = ([f"AUT{i}" for i in range(1,7)]+[f"EMP{i}" for i in range(1,13)]+[f"NARC{i}" for i in range(1,7)]
        +[f"PD{i}" for i in range(1,6)]+[f"BEN{i}" for i in range(1,6)]+[f"MAL{i}" for i in range(1,6)]
        +[f"THR{i}" for i in range(1,11)]+["R_THR5","R_THR10"]+[f"T3_THR{i}" for i in range(1,11)]+["T3_R_THR5","T3_R_THR10"]
        +[f"OCBS_Self{i}" for i in range(1,7)]+[f"CWBS_Self{i}" for i in range(1,6)]
        +[f"EMPP{i}" for i in range(1,5)]+[f"THRP{i}" for i in range(1,5)]+[f"T3_THRP{i}" for i in range(1,5)])
fmap = d.set_index("FollowerID")

def recompute_parcels(w, m):
    grp = {"EMPP1":[1,2,3],"EMPP2":[4,5,6],"EMPP3":[7,8,9],"EMPP4":[10,11,12]}
    for pc,idx in grp.items():
        if pc in w.columns and all(f"EMP{i}" in w.columns for i in idx):
            w.loc[m,pc]=w.loc[m,[f"EMP{i}" for i in idx]].mean(1)
    thr={"THRP1":["THR1","THR2","THR3"],"THRP2":["THR4","R_THR5"],"THRP3":["THR6","THR7","THR8"],"THRP4":["THR9","R_THR10"]}
    for pc,its in thr.items():
        if pc in w.columns and all(c in w.columns for c in its):
            w.loc[m,pc]=w.loc[m,its].mean(1)
    # recompute construct composites where present (else stale vs new items)
    comp={"Autocratic":[f"AUT{i}" for i in range(1,7)],"Empowering":[f"EMP{i}" for i in range(1,13)],
          "Narcissism":[f"NARC{i}" for i in range(1,7)],"PowerDistance":[f"PD{i}" for i in range(1,6)]}
    for c,its in comp.items():
        if c in w.columns and all(x in w.columns for x in its):
            w.loc[m,c]=w.loc[m,its].mean(1)
    if "T1_Thriving" in w.columns and all(f"THRP{i}" in w.columns for i in range(1,5)):
        w.loc[m,"T1_Thriving"]=w.loc[m,[f"THRP{i}" for i in range(1,5)]].mean(1)

def propagate(fname):
    w = pd.read_excel(DATA / fname, engine="openpyxl")
    if "FollowerID" not in w.columns: return
    cols=[c for c in w.columns if c in REGEN and c in fmap.columns]
    m=w.FollowerID.isin(fmap.index)
    for c in cols:
        w.loc[m,c]=w.loc[m,"FollowerID"].map(fmap[c])
    recompute_parcels(w,m)
    w.to_excel(DATA / fname, index=False)
    print(f"  {fname}: propagated {len(cols)} item-cols to {int(m.sum())}/{len(w)} rows")

for f in ["T1_cleaned.xlsx","T1_raw.xlsx","T2_cleaned.xlsx","T2_raw.xlsx",
          "T3_follower_cleaned.xlsx","T3_follower_raw.xlsx"]:
    propagate(f)

# --- T3 leader WIDE rebuilt from final_merged dyad ratings ---
MAXF=5
def build_wide(dyad):
    rows=[]
    for lid,g in dyad.groupby("LeaderID",sort=True):
        g=g.sort_values("FollowerID").reset_index(drop=True); n=len(g)
        r={"CompanyID":g.loc[0,"CompanyID"],"TeamID":g.loc[0,"TeamID"],"LeaderID":lid,"评价下属人数":n}
        for k in range(1,MAXF+1):
            if k<=n:
                row=g.loc[k-1]; r[f"FollowerID_{k}"]=row["FollowerID"]
                for i in range(1,7): r[f"OCBS_{k}_{i}"]=row[f"OCBS_L{i}"]
                for i in range(1,6): r[f"CWBS_{k}_{i}"]=row[f"CWBS{i}"]
                r[f"CWBS_{k}_6_AttCheck"]=row["CWBS6_AttCheck"]
            else:
                r[f"FollowerID_{k}"]=np.nan
                for i in range(1,7): r[f"OCBS_{k}_{i}"]=np.nan
                for i in range(1,6): r[f"CWBS_{k}_{i}"]=np.nan
                r[f"CWBS_{k}_6_AttCheck"]=np.nan
        for c in ["LeaderAge","LeaderGender","LeaderEducation","LeadershipTenure",
                  "SpanOfControl","LeaderWorkingYears","LeaderJobLevel"]:
            r[c]=g.loc[0,c]
        rows.append(r)
    return pd.DataFrame(rows)
wide=build_wide(d)
wide.to_excel(DATA/"T3_leader_cleaned.xlsx",index=False)
dup=wide.iloc[[0]].copy(); mm=wide.iloc[[1]].copy(); mm["LeaderID"]="X_L99"
pd.concat([wide,dup,mm],ignore_index=True).to_excel(DATA/"T3_leader_raw.xlsx",index=False)
print(f"  T3_leader WIDE: {len(wide)} leaders, dist={dict(wide['评价下属人数'].value_counts().sort_index())}")

# --- refresh Mplus .dat ---
ben=[f"BEN{i}" for i in range(1,6)]; mal=[f"MAL{i}" for i in range(1,6)]
mcfa_cols=["CLID"]+[f"AUT{i}" for i in range(1,7)]+[f"EMPP{i}" for i in range(1,5)]+ben+mal+[f"THRP{i}" for i in range(1,5)]
if "CLID" not in d.columns:
    d["CLID"]=pd.factorize(d["LeaderID"])[0]+1
present=[c for c in mcfa_cols if c in d.columns]
mc=d[present].fillna(-999)
with open(DATA/"study3_mcfa.dat","w") as f:
    for _,row in mc.iterrows():
        f.write(" ".join(f"{v:.3f}" if isinstance(v,float) else str(int(v)) for v in row.tolist())+"\n")
print(f"  study3_mcfa.dat: {len(mc)} rows x {len(present)} cols")
print("propagation DONE")
