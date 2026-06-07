"""Export study3_mcfa.dat with item-level EMP + THR (no parcels)."""
from pathlib import Path
import numpy as np, pandas as pd

REPO = Path("/root/leader_survey_v2/repo")
df = pd.read_excel(REPO / "data" / "final_merged_analysis_data.xlsx")

# MCFA variables (item-level, no parcels):
# AUT1-6 (autocratic, T1)
# EMP1-12 (empowering, T1, skip EMP9_AttCheck)
# BEN1-5 (benign envy, T2)
# MAL1-5 (malicious envy, T2)
# THR1-10 with R_THR5, R_THR10 (thriving T1; use reverse-coded versions)
#   -> for items 5 and 10 use R_THR5 and R_THR10

cols = ["CLID"]
cols += [f"AUT{i}" for i in range(1, 7)]             # 6 items
cols += [f"EMP{i}" for i in range(1, 13)]             # 12 items (skip AttCheck)
cols += [f"BEN{i}" for i in range(1, 6)]              # 5 items
cols += [f"MAL{i}" for i in range(1, 6)]              # 5 items
# THR: use forward-coded for 1-4,6-9; reverse-coded R_THR5, R_THR10
thr_cols = []
for i in range(1, 11):
    if i == 5:
        thr_cols.append("R_THR5")
    elif i == 10:
        thr_cols.append("R_THR10")
    else:
        thr_cols.append(f"THR{i}")
cols += thr_cols

# Build CLID
codes, _ = pd.factorize(df["LeaderID"])
df["CLID"] = codes + 1

# Verify all columns exist
missing = [c for c in cols if c not in df.columns]
if missing:
    raise SystemExit(f"Missing columns: {missing}")

out = df[cols].copy()
for c in out.columns:
    out[c] = pd.to_numeric(out[c], errors="coerce")
out = out.fillna(-999)

outpath = REPO / "data" / "study3_mcfa.dat"
with open(outpath, "w") as f:
    for _, row in out.iterrows():
        parts = []
        for c in cols:
            v = row[c]
            parts.append(f"{int(v):d}" if c == "CLID" else f"{v:.4f}")
        f.write(" ".join(parts) + "\n")

print(f"Wrote {outpath}: {len(out)} rows, {len(cols)} cols")
print(f"Variables: {' '.join(cols)}")
print(f"  AUT: 6, EMP: 12, BEN: 5, MAL: 5, THR: 10 = 38 items + CLID = 39 total")
