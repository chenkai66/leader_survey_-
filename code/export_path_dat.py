"""
Export final_merged_analysis_data.xlsx to study3_path.dat for Mplus structural
path model (code/path_mplus_syntax.inp).

Variable order (matches NAMES in path_mplus_syntax.inp):
  CLID FAGE GMALE TEN INTF AUT EMP NARC PD T1THR
  BE ME T3THR OCBSL CWBSL OCBSF CWBSF

Output format: space-delimited, missing = -999, no header (Mplus convention).
File written to data/study3_path.dat
"""
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

df = pd.read_excel(DATA / "final_merged_analysis_data.xlsx")
print(f"loaded N={len(df)}, columns={len(df.columns)}")

# Mplus needs numeric CLID. Factorize LeaderID -> integer 1..k
codes, uniq = pd.factorize(df["LeaderID"])
df["_CLID"] = codes + 1   # Mplus prefers 1-indexed

# Gender_Male: 1 = male, 0 = female. If column missing, derive from Gender_Female.
if "Male" in df.columns:
    df["_GMALE"] = df["Male"].astype(int)
elif "Gender_Female" in df.columns:
    df["_GMALE"] = (1 - df["Gender_Female"]).astype(int)
else:
    raise SystemExit("no Male / Gender_Female column")

OUT_COLS = [
    ("CLID",   "_CLID"),
    ("FAGE",   "FollowerAge"),
    ("GMALE",  "_GMALE"),
    ("TEN",    "TenureWithLeader"),
    ("INTF",   "InteractionFreq"),
    ("AUT",    "Autocratic"),
    ("EMP",    "Empowering"),
    ("NARC",   "Narcissism"),
    ("PD",     "PowerDistance"),
    ("T1THR",  "T1_Thriving"),
    ("BE",     "BenignEnvy"),
    ("ME",     "MaliciousEnvy"),
    ("T3THR",  "T3_Thriving"),
    ("OCBSL",  "OCBS_Leader"),
    ("CWBSL",  "CWBS_Leader"),
    ("OCBSF",  "OCBS_Follower"),
    ("CWBSF",  "CWBS_Follower"),
]

missing = [src for _, src in OUT_COLS if src not in df.columns]
if missing:
    raise SystemExit(f"missing columns in data: {missing}")

out = df[[src for _, src in OUT_COLS]].copy()
out.columns = [name for name, _ in OUT_COLS]

# Coerce all to numeric, replace NaN with -999 (Mplus convention)
for c in out.columns:
    out[c] = pd.to_numeric(out[c], errors="coerce")
out = out.fillna(-999)

# Format: integers stay integer; floats stay floats; CLID and GMALE as int
out_path = DATA / "study3_path.dat"
fmt_cols = []
for name, _ in OUT_COLS:
    if name in ("CLID", "GMALE"):
        fmt_cols.append("%d")
    else:
        fmt_cols.append("%.4f")

with open(out_path, "w") as f:
    for _, row in out.iterrows():
        parts = []
        for (name, _), fmt in zip(OUT_COLS, fmt_cols):
            v = row[name]
            if fmt == "%d":
                parts.append(f"{int(v):d}")
            else:
                parts.append(fmt % v)
        f.write(" ".join(parts) + "\n")

print(f"wrote {out_path}  ({len(out)} rows, {len(out.columns)} cols)")
print(f"\nVariable order (use this in Mplus NAMES statement):")
print("  " + " ".join(name for name, _ in OUT_COLS))
print(f"\nFile preview (first 3 rows):")
import subprocess
subprocess.run(["head", "-3", str(out_path)])
