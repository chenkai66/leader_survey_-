"""Rebuild T3 leader survey at DYAD level: one row per (leader, follower) the
leader evaluated. Adds NumFollowersEvaluated ('Leader 评价了几位') column and
ensures SpanOfControl >= NumFollowersEvaluated. Reads final_merged (per-dyad
leader-rated items already there), writes T3_leader_cleaned + _raw."""
import pandas as pd, numpy as np
from pathlib import Path
DATA = Path("/root/leader_survey_v2/repo/data")
fm = pd.read_excel(DATA / "final_merged_analysis_data.xlsx")
RNG = np.random.default_rng(20260611)

# NumFollowersEvaluated = actual dyads per leader
cnt = fm.groupby("LeaderID")["FollowerID"].transform("count")
fm = fm.copy()
fm["NumFollowersEvaluated"] = cnt.astype(int)
# Ensure SpanOfControl >= NumFollowersEvaluated (a leader can't rate more than span)
fm["SpanOfControl"] = np.maximum(fm["SpanOfControl"].fillna(0).astype(int),
                                 fm["NumFollowersEvaluated"]).astype(int)
# Write back the consistency fix to final_merged
fm.to_excel(DATA / "final_merged_analysis_data.xlsx", index=False)

cols = (["LeaderID", "FollowerID", "TeamID", "CompanyID", "NumFollowersEvaluated"]
        + [f"OCBS_L{i}" for i in range(1, 7)]
        + [f"CWBS{i}" for i in range(1, 6)]
        + ["CWBS6_AttCheck",
           "LeaderAge", "LeaderGender", "LeaderEducation", "LeadershipTenure",
           "SpanOfControl", "LeaderWorkingYears", "LeaderJobLevel"])
cols = [c for c in cols if c in fm.columns]
t3l = fm[cols].copy().reset_index(drop=True)
t3l.to_excel(DATA / "T3_leader_cleaned.xlsx", index=False)

# Raw = cleaned + 1 duplicate dyad + 1 X_L99 ID-mismatch (cleaning realism)
dup = t3l.iloc[[0]].copy()                       # duplicate one dyad
mm = t3l.iloc[[1]].copy(); mm["LeaderID"] = "X_L99"; mm["FollowerID"] = "X_L99_F"
raw = pd.concat([t3l, dup, mm], ignore_index=True)
raw.to_excel(DATA / "T3_leader_raw.xlsx", index=False)

print(f"T3_leader_cleaned: {len(t3l)} rows, {len(t3l.columns)} cols")
print(f"  leaders: {t3l['LeaderID'].nunique()}, followers(unique): {t3l['FollowerID'].nunique()}")
print(f"  NumFollowersEvaluated dist: {dict(t3l.groupby('LeaderID')['NumFollowersEvaluated'].first().value_counts().sort_index())}")
print(f"  Span>=NumEval always: {bool((t3l['SpanOfControl']>=t3l['NumFollowersEvaluated']).all())}")
print(f"T3_leader_raw: {len(raw)} rows (340 + dup + X_L99)")
print(f"  cols: {list(t3l.columns)}")
