"""Rebuild T3 leader survey in 问卷星 WIDE format: ONE LEADER PER ROW.
Each leader rates up to 5 followers; per-follower blocks (FollowerID_k +
OCBS_k 6 items + CWBS_k 5 items + AttCheck). Mirrors the WJX questionnaire."""
import pandas as pd, numpy as np
from pathlib import Path
DATA = Path("/root/leader_survey_v2/repo/data")
# read dyad-level source (has per-follower leader ratings)
dy = pd.read_excel(DATA / "T3_leader_cleaned.xlsx")
MAXF = 5

def build_wide(dyad):
    rows = []
    for lid, g in dyad.groupby("LeaderID", sort=True):
        g = g.sort_values("FollowerID").reset_index(drop=True)
        n = len(g)
        r = {
            "CompanyID": g.loc[0, "CompanyID"],
            "TeamID": g.loc[0, "TeamID"],
            "LeaderID": lid,
            "评价下属人数": n,                     # NumFollowersEvaluated
        }
        for k in range(1, MAXF + 1):
            if k <= n:
                row = g.loc[k - 1]
                r[f"FollowerID_{k}"] = row["FollowerID"]
                for i in range(1, 7):
                    r[f"OCBS_{k}_{i}"] = row[f"OCBS_L{i}"]
                for i in range(1, 6):
                    r[f"CWBS_{k}_{i}"] = row[f"CWBS{i}"]
                r[f"CWBS_{k}_6_AttCheck"] = row["CWBS6_AttCheck"]
            else:
                r[f"FollowerID_{k}"] = np.nan
                for i in range(1, 7):
                    r[f"OCBS_{k}_{i}"] = np.nan
                for i in range(1, 6):
                    r[f"CWBS_{k}_{i}"] = np.nan
                r[f"CWBS_{k}_6_AttCheck"] = np.nan
        for c in ["LeaderAge", "LeaderGender", "LeaderEducation", "LeadershipTenure",
                  "SpanOfControl", "LeaderWorkingYears", "LeaderJobLevel"]:
            r[c] = g.loc[0, c]
        rows.append(r)
    return pd.DataFrame(rows)

wide = build_wide(dy)
wide.to_excel(DATA / "T3_leader_cleaned.xlsx", index=False)

# raw = cleaned + 1 duplicate leader + 1 X_L99 ID-mismatch leader
dup = wide.iloc[[0]].copy()
mm = wide.iloc[[1]].copy(); mm["LeaderID"] = "X_L99"
raw = pd.concat([wide, dup, mm], ignore_index=True)
raw.to_excel(DATA / "T3_leader_raw.xlsx", index=False)

print(f"WIDE T3_leader_cleaned: {len(wide)} rows (one per leader), {len(wide.columns)} cols")
print(f"  评价下属人数 dist: {dict(wide['评价下属人数'].value_counts().sort_index())}")
print(f"  columns: {list(wide.columns)[:12]} ...")
print(f"  ...tail: {list(wide.columns)[-9:]}")
print(f"WIDE T3_leader_raw: {len(raw)} rows (79 + dup + X_L99)")
# show one leader-with-3 and one with-5 to verify blanks
ex3 = wide[wide['评价下属人数']==3].iloc[0]
print(f"\n  example leader (3 followers): FollowerID_4={ex3['FollowerID_4']} (should be NaN), OCBS_4_1={ex3['OCBS_4_1']}")
ex5 = wide[wide['评价下属人数']==5].iloc[0]
print(f"  example leader (5 followers): FollowerID_5={ex5['FollowerID_5']} (should have value), OCBS_5_1={ex5['OCBS_5_1']}")
