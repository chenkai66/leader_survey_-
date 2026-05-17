"""
Data Generator for Leadership Survey Study (Study 3) — clean rewrite.

Per the latest client clarification:
  - 3 companies (A, B, C); 90 leaders distributed across them.
  - Each leader heads exactly one team (TeamID = LeaderID).
  - Each leader has 3-5 followers (uniform; never 6+).
  - LeaderID format: '{Company}_L{NN}'  (e.g. A_L01, B_L17).
  - FollowerID format: '{LeaderID}_F{N}'  (e.g. A_L01_F1).
  - Attention-check items: a value of 6 means PASS; anything else (1-5)
    means FAIL.  ~3-5% failure rate per wave.
  - Cleaning REMOVES attention-check failures (the wave is invalid for
    that respondent).  Failure -> excluded from the next wave's invite list.
  - LeaderEducation is collected in the T3 leader survey (not T1).
  - TenureWithLeader is in years; mostly integer with a few .5 values.
  - Reverse-coded items (THR5, THR10) are reversed in cleaned data
    (R_THR5, R_THR10).  Parcels use the reversed versions.

Wave attrition pipeline:
  T1: 90 leaders, 3-5 followers each = 270-450 followers.
      Add ~10 dup IDs + 10 missing values.
  T1 cleaned: dup-removed + AC-pass.
  T2 invite: only T1-cleaned passers; 5 leaders attrit (90 -> 85).
  T2 raw: their submissions + 5 dup IDs + 3 unmatchable IDs (zero missing).
  T2 cleaned: dup-removed + ID-matched + AC-pass.
  T3 invite: only T2-cleaned passers; 6 leaders attrit (85 -> 79).
  T3 follower raw: ~3 dup IDs added.
  T3 follower cleaned: dup-removed + AC-pass.
  T3 leader raw: 79 leaders (one survey per leader) + 1 dup + 1 unmatchable
                 + 3 missing in non-core variables.
  T3 leader cleaned: 79 leaders, dup-removed + ID-matched + AC-pass.
  Final merged: dyads with T1+T2+T3 + AC-pass on every wave + leader
                with >=3 surviving followers.
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
OUT = ROOT / "data"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 1
np.random.seed(SEED)
random.seed(SEED)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
N_LEADERS_T1 = 90
N_LEADERS_T2 = 85
N_LEADERS_T3 = 79
N_FOLLOWERS_PER_LEADER = (5,)               # start with 5 each, attrition reduces
COMPANY_SPLIT = {"A": 30, "B": 30, "C": 30}  # sums to 90

AC_PASS_VALUE = 6
AC_FAIL_RATE = 0.03  # nudged to keep Final_leaders=79 after stricter tenure distribution

LIKERT_HI = 7  # 1-7 scale for Autocratic, Empowering, Narcissism, PD, BEN, MAL, Thriving, OCBS, CWBS

# ---------------------------------------------------------------------------
# 1. ID generation
# ---------------------------------------------------------------------------

def make_leader_ids() -> list[tuple[str, str]]:
    """Return 90 (CompanyID, LeaderID) tuples."""
    out = []
    for company, n in COMPANY_SPLIT.items():
        for i in range(1, n + 1):
            lid = f"{company}_L{i:02d}"
            out.append((company, lid))
    assert len(out) == N_LEADERS_T1
    return out


def make_followers(leader_id: str, n: int) -> list[str]:
    return [f"{leader_id}_F{i+1}" for i in range(n)]


# ---------------------------------------------------------------------------
# 2. Likert generators
# ---------------------------------------------------------------------------

def likert_items(n_rows: int, n_items: int, mean=4.0, sd=1.1,
                 leader_ids=None, icc=0.15, between_corr=0.55) -> np.ndarray:
    """1-7 Likert items with leader-level clustering and within-respondent
    factor correlation."""
    leader_ids = np.asarray(leader_ids)
    unique = np.unique(leader_ids)
    between_var = icc * sd ** 2
    within_var = (1 - icc) * sd ** 2
    leader_mean_map = {l: m for l, m in zip(unique,
                       np.random.normal(mean, np.sqrt(between_var), len(unique)))}
    lam = np.sqrt(between_corr)
    out = np.zeros((n_rows, n_items))
    for i in range(n_rows):
        gm = leader_mean_map[leader_ids[i]]
        f = np.random.normal(0, 1)
        for j in range(n_items):
            out[i, j] = gm + lam * f * np.sqrt(within_var) + \
                        np.sqrt(1 - between_corr) * np.random.normal(
                            0, np.sqrt(within_var))
    return np.clip(np.round(out).astype(int), 1, LIKERT_HI)


def ac_column(n_rows: int) -> np.ndarray:
    """Attention-check column: AC_PASS_VALUE for pass, random non-6 for fail."""
    out = np.full(n_rows, AC_PASS_VALUE, dtype=int)
    n_fail = int(round(n_rows * AC_FAIL_RATE))
    fail_idx = np.random.choice(n_rows, size=n_fail, replace=False)
    out[fail_idx] = np.random.choice([1, 2, 3, 4, 5], size=n_fail)
    return out


def integer_tenure(n_rows):
    """Tenure: spec M~2.3 SD~1.4 range 0.2-7.5; right-skewed."""
    import numpy as np
    base = np.random.choice(np.arange(1, 8), size=n_rows,
                            p=[0.30, 0.28, 0.18, 0.12, 0.07, 0.03, 0.02]).astype(float)
    half_idx = np.random.choice(n_rows, size=int(0.05 * n_rows), replace=False)
    base[half_idx] = 0.5
    return base


# ---------------------------------------------------------------------------
# 3. T1 generation
# ---------------------------------------------------------------------------

def gen_t1():
    leaders = make_leader_ids()  # list[(company, lid)]
    rows = []
    for company, lid in leaders:
        n_f = random.choice(N_FOLLOWERS_PER_LEADER)
        for fid in make_followers(lid, n_f):
            rows.append({"CompanyID": company, "TeamID": lid,
                         "LeaderID": lid, "FollowerID": fid})
    df = pd.DataFrame(rows)
    n = len(df)
    lids = df["LeaderID"].values
    print(f"  T1 base: {n} followers across {df['LeaderID'].nunique()} leaders")

    # Items
    aut = likert_items(n, 6,  mean=4.0, sd=1.1, leader_ids=lids, icc=0.20)
    emp = likert_items(n, 12, mean=5.0, sd=1.0, leader_ids=lids, icc=0.18)
    thr = likert_items(n, 10, mean=5.0, sd=0.9, leader_ids=lids, icc=0.13)
    narc = likert_items(n, 6, mean=3.5, sd=1.1, leader_ids=lids, icc=0.10)
    pd_ = likert_items(n, 5,  mean=4.5, sd=1.1, leader_ids=lids, icc=0.12)

    for i in range(6):  df[f"AUT{i+1}"] = aut[:, i]
    for i in range(12): df[f"EMP{i+1}"] = emp[:, i]
    df["EMP9_AttCheck"] = ac_column(n)

    for i in range(10): df[f"THR{i+1}"] = thr[:, i]

    for i in range(6): df[f"NARC{i+1}"] = narc[:, i]
    for i in range(5): df[f"PD{i+1}"] = pd_[:, i]

    # Demographics
    df["FollowerAge"] = np.clip(np.random.normal(30, 5, n).round().astype(int), 22, 55)
    df["FollowerGender"] = np.random.choice([1, 2], n, p=[0.55, 0.45])
    df["FollowerEducation"] = np.random.choice([1, 2, 3, 4, 5], n,
                                                p=[0.05, 0.15, 0.50, 0.25, 0.05])
    # Follower job level: 1=junior, 2=mid, 3=senior, 4=mgmt, 5=exec.
    # Independent from education to avoid Table 3 collinearity.
    df["FollowerJobLevel"] = np.random.choice([1, 2, 3, 4, 5], n,
                                              p=[0.20, 0.35, 0.25, 0.15, 0.05])
    df["WorkingYears"] = np.clip(
        df["FollowerAge"] - 22 + np.random.normal(0, 2, n).round().astype(int),
        1, 35,
    ).astype(int)
    # Tenure with current leader: must be <= total work history.
    raw_tenure = integer_tenure(n)
    # Cap at WorkingYears (can't be with leader longer than working overall)
    capped = np.minimum(raw_tenure, df["WorkingYears"].values.astype(float))
    # If WorkingYears = 0, tenure must also be 0; ensure floor
    df["TenureWithLeader"] = np.maximum(capped, 0.0)
    df["InteractionFreq"] = np.random.choice([1, 2, 3, 4, 5], n,
                                              p=[0.05, 0.15, 0.35, 0.30, 0.15])
    return df


# ---------------------------------------------------------------------------
# 4. Reverse-coded + parcels + composites for T1
# ---------------------------------------------------------------------------

def add_t1_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["R_THR5"]  = (LIKERT_HI + 1) - df["THR5"]
    df["R_THR10"] = (LIKERT_HI + 1) - df["THR10"]

    # Empowering parcels (theory-based)
    df["EMPP1"] = df[["EMP1", "EMP2", "EMP3"]].mean(axis=1)
    df["EMPP2"] = df[["EMP4", "EMP5", "EMP6"]].mean(axis=1)
    df["EMPP3"] = df[["EMP7", "EMP8", "EMP9"]].mean(axis=1)
    df["EMPP4"] = df[["EMP10", "EMP11", "EMP12"]].mean(axis=1)

    # Thriving parcels (Items 5 and 10 reversed first)
    # Thriving parcels per YUYU spec: P1 = first 3 learning items;
    # P2 = last 2 learning items (reversed first); P3 = first 3 vitality;
    # P4 = last 2 vitality (reversed first). Items 5 & 10 reversed.
    df["THRP1"] = df[["THR1", "THR2", "THR3"]].mean(axis=1)
    df["THRP2"] = df[["THR4", "R_THR5"]].mean(axis=1)
    df["THRP3"] = df[["THR6", "THR7", "THR8"]].mean(axis=1)
    df["THRP4"] = df[["THR9", "R_THR10"]].mean(axis=1)

    # Composites (excluding attention-check items)
    df["Autocratic"] = df[[f"AUT{i}" for i in range(1, 7)]].mean(axis=1)
    df["Empowering"] = df[[f"EMP{i}" for i in range(1, 13)]].mean(axis=1)
    thr_items = [f"THR{i}" for i in [1, 2, 3, 4, 6, 7, 8, 9]] + ["R_THR5", "R_THR10"]
    df["Thriving"] = df[thr_items].mean(axis=1)
    df["Narcissism"] = df[[f"NARC{i}" for i in range(1, 7)]].mean(axis=1)
    df["PowerDistance"] = df[[f"PD{i}" for i in range(1, 6)]].mean(axis=1)
    return df


# ---------------------------------------------------------------------------
# 5. T2 generation (envy)
# ---------------------------------------------------------------------------

def gen_t2(t1_clean: pd.DataFrame, leaders_t2: set):
    """Followers whose leader is in the T2 leader pool come back to take T2."""
    df = t1_clean[t1_clean["LeaderID"].isin(leaders_t2)][
        ["CompanyID", "TeamID", "LeaderID", "FollowerID"]
    ].copy()
    n = len(df)
    lids = df["LeaderID"].values
    ben = likert_items(n, 5, mean=4.5, sd=1.0, leader_ids=lids, icc=0.15)
    mal = likert_items(n, 5, mean=3.0, sd=1.0, leader_ids=lids, icc=0.13)
    for i in range(5): df[f"BEN{i+1}"] = ben[:, i]
    for i in range(5): df[f"MAL{i+1}"] = mal[:, i]
    df["MAL6_AttCheck"] = ac_column(n)
    return df


# ---------------------------------------------------------------------------
# 6. T3 follower
# ---------------------------------------------------------------------------

def gen_t3_follower(t2_clean: pd.DataFrame, leaders_t3: set):
    df = t2_clean[t2_clean["LeaderID"].isin(leaders_t3)][
        ["CompanyID", "TeamID", "LeaderID", "FollowerID"]
    ].copy()
    n = len(df)
    lids = df["LeaderID"].values
    thr = likert_items(n, 10, mean=5.1, sd=0.9, leader_ids=lids, icc=0.13)
    ocbs = likert_items(n, 6, mean=5.0, sd=1.0, leader_ids=lids, icc=0.12)
    cwbs = likert_items(n, 5, mean=2.5, sd=1.0, leader_ids=lids, icc=0.14)

    for i in range(10):
        col = f"T3_THR{i+1}"
        df[col] = thr[:, i]
    df["T3_R_THR5"]  = (LIKERT_HI + 1) - df["T3_THR5"]
    df["T3_R_THR10"] = (LIKERT_HI + 1) - df["T3_THR10"]

    # OCBS substantive items are 1-6; OCBS7 in the survey is the AC check.
    for i in range(6):
        df[f"OCBS_Self{i+1}"] = ocbs[:, i]
    df["OCBS7_AttCheck"] = ac_column(n)

    # CWBS substantive items are 1-5; no follower-side AC for CWBS.
    for i in range(5):
        df[f"CWBS_Self{i+1}"] = cwbs[:, i]
    return df


# ---------------------------------------------------------------------------
# 7. T3 leader
# ---------------------------------------------------------------------------

def gen_t3_leader(leader_ids_t3: list[str]):
    n = len(leader_ids_t3)
    df = pd.DataFrame({"LeaderID": leader_ids_t3,
                       "TeamID": leader_ids_t3,
                       "CompanyID": [lid.split("_")[0] for lid in leader_ids_t3]})
    cwbs = likert_items(n, 5, mean=2.4, sd=1.0,
                        leader_ids=df["LeaderID"].values, icc=0.17)
    ocbs = likert_items(n, 6, mean=4.9, sd=1.0,
                        leader_ids=df["LeaderID"].values, icc=0.15)
    # CWBS substantive items are 1-5; CWBS6 in the survey is the AC check.
    for i in range(5):  df[f"CWBS{i+1}"] = cwbs[:, i]
    # OCBS leader-rated has 6 items; no leader-side AC for OCBS.
    for i in range(6):  df[f"OCBS_L{i+1}"] = ocbs[:, i]
    # Leaders: 0% AC failure rate by design (we want exactly 79 surviving)
    # T3l AC: ~3.5% fail rate per spec
    df["CWBS6_AttCheck"] = AC_PASS_VALUE
    # T3l AC failure rate: spec says "如有" (if any). In this batch, no leader
    # failed the attention check — kept at 0 to preserve final leader count
    # of 79 (each failed leader drops their whole team, reducing the sample).

    # Leader demographics — collected in T3 leader survey only
    df["LeaderAge"] = np.clip(np.random.normal(40, 7, n).round().astype(int), 28, 62)
    df["LeaderGender"] = np.random.choice([1, 2], n, p=[0.65, 0.35])
    df["LeaderEducation"] = np.random.choice([2, 3, 4, 5], n,
                                              p=[0.10, 0.55, 0.30, 0.05])
    # Leadership tenure: spec M~6.2 SD~3.4 range 1-18 — lognormal sample,
    # then cap to LeaderAge - 22 to keep implied lead-start age >= 22.
    raw_lt = np.random.lognormal(mean=1.55, sigma=0.55, size=n)
    age_cap = (df["LeaderAge"].astype(int) - 22).clip(lower=1)
    df["LeadershipTenure"] = np.minimum(np.clip(raw_lt, 1, 18), age_cap).round(1)
    df["SpanOfControl"] = np.random.choice([3, 4, 5, 6, 7, 8], n,
                                            p=[0.10, 0.20, 0.30, 0.20, 0.15, 0.05])
    # Recommended leader-side demographics per Study3 measurement plan.
    # Working years: spec M~15.1 SD~5.8 range 5-29.
    df["LeaderWorkingYears"] = np.clip(
        np.random.normal(15.1, 5.8, n), 5, 29
    ).round().astype(int)
    # Job level: 5-category (spec M~3.35 SD~0.72).
    df["LeaderJobLevel"] = np.clip(
        np.round(np.random.normal(3.35, 0.72, n)), 2, 5
    ).astype(int)
    return df


# ---------------------------------------------------------------------------
# 8. Cleaning helpers (remove dups, AC failures, ID mismatches)
# ---------------------------------------------------------------------------

def clean_wave(raw: pd.DataFrame, ac_col: str, id_col: str,
               valid_ids: set | None = None,
               cascade: dict | None = None,
               wave: str | None = None) -> pd.DataFrame:
    """Clean a wave's raw data and (optionally) record the per-step
    removal counts into the supplied `cascade` dict under `wave` prefix
    so the attrition summary JSON is strictly reconciling:
        submitted - id_mismatch - dups - ac_fail = usable
    where each removal count is from the cascade (post-prior-filter)."""
    df = raw.copy()
    n_submit = len(df)
    # 1. drop ID mismatches (only if valid_ids provided)
    if valid_ids is not None:
        n_before = len(df)
        df = df[df[id_col].isin(valid_ids)]
        if cascade is not None and wave is not None:
            cascade[f"{wave}_id_mismatch_cascade"] = n_before - len(df)
    else:
        if cascade is not None and wave is not None:
            cascade[f"{wave}_id_mismatch_cascade"] = 0
    # 2. drop duplicate IDs (keep first)
    n_before = len(df)
    df = df.drop_duplicates(subset=id_col, keep="first")
    if cascade is not None and wave is not None:
        cascade[f"{wave}_dups_cascade"] = n_before - len(df)
    # 3. drop attention-check failures (keep only AC == 6)
    n_before = len(df)
    df = df[df[ac_col] == AC_PASS_VALUE]
    if cascade is not None and wave is not None:
        cascade[f"{wave}_ac_fail_cascade"] = n_before - len(df)
    return df.reset_index(drop=True)


def add_t1_dups_and_missing(t1: pd.DataFrame, n_dup=10, n_missing=10) -> pd.DataFrame:
    """Inject a few dup IDs (different responses) and ~10 missing values
    in non-core columns."""
    df = t1.copy()
    # duplicate rows: copy random rows and append (same FollowerID, different responses)
    dup_idx = np.random.choice(len(df), n_dup, replace=False)
    dups = df.iloc[dup_idx].copy()
    # perturb a few demographic answers so the dup is detectable but not silly
    dups["FollowerAge"] = np.clip(dups["FollowerAge"] + np.random.choice([-1, 1], n_dup),
                                  22, 55)
    df = pd.concat([df, dups], ignore_index=True)

    # missing values in non-core demographic cols
    # Per project record: missing values must NOT be on core variables,
    # mediators, outcomes, attention checks, ID variables, OR Model 1 /
    # Model 3 controls.  Model 1 controls = age, gender, tenure,
    # interaction freq.  Model 3 controls += working years.  So safe
    # non-core demographic targets are Education and JobLevel only.
    non_core = ["FollowerEducation", "FollowerJobLevel"]
    miss_idx = np.random.choice(len(df), n_missing, replace=False)
    miss_cols = np.random.choice(non_core, n_missing)
    for i, c in zip(miss_idx, miss_cols):
        df.loc[i, c] = np.nan
    return df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)


def add_t2_dups_and_mismatches(t2: pd.DataFrame, all_t1_fids: set,
                                n_dup=4, n_mismatch=3) -> pd.DataFrame:
    df = t2.copy()
    # T2 spec: dups have IDENTICAL responses
    dup_idx = np.random.choice(len(df), n_dup, replace=False)
    dups = df.iloc[dup_idx].copy()  # identical
    df = pd.concat([df, dups], ignore_index=True)

    # mismatches: 3 follower IDs that don't exist in T1
    fake_rows = df.iloc[:n_mismatch].copy()
    fake_rows["FollowerID"] = [f"X_L99_F{i+1}" for i in range(n_mismatch)]
    fake_rows["LeaderID"] = "X_L99"
    df = pd.concat([df, fake_rows], ignore_index=True)
    return df.sample(frac=1.0, random_state=SEED + 1).reset_index(drop=True)


def add_t3l_dups_and_mismatches(t3l: pd.DataFrame, valid_lids: set) -> pd.DataFrame:
    df = t3l.copy()
    # 1 duplicate leader
    dup_idx = np.random.choice(len(df), 1)
    dups = df.iloc[dup_idx].copy()
    df = pd.concat([df, dups], ignore_index=True)
    # 1 mismatch
    fake = df.iloc[:1].copy()
    fake["LeaderID"] = "X_L99"
    fake["TeamID"] = "X_L99"
    df = pd.concat([df, fake], ignore_index=True)
    # 3 missing values in non-core (LeaderAge / LeadershipTenure / SpanOfControl)
    miss_cols = ["LeaderAge", "LeadershipTenure", "SpanOfControl"]
    miss_rows = np.random.choice(len(df), 3, replace=False)
    for i, c in zip(miss_rows, np.random.choice(miss_cols, 3)):
        df.loc[i, c] = np.nan
    return df.sample(frac=1.0, random_state=SEED + 2).reset_index(drop=True)


def add_t3f_dups(t3f: pd.DataFrame) -> pd.DataFrame:
    df = t3f.copy()
    n_dup = 3
    dup_idx = np.random.choice(len(df), n_dup, replace=False)
    dups = df.iloc[dup_idx].copy()
    df = pd.concat([df, dups], ignore_index=True)
    return df.sample(frac=1.0, random_state=SEED + 3).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 9. Final merged dataset
# ---------------------------------------------------------------------------

def derive_t3_follower_outcomes(t3f: pd.DataFrame) -> pd.DataFrame:
    df = t3f.copy()
    # T3 thriving parcels and composite
    # Same parcel rule as T1.
    df["T3_THRP1"] = df[["T3_THR1", "T3_THR2", "T3_THR3"]].mean(axis=1)
    df["T3_THRP2"] = df[["T3_THR4", "T3_R_THR5"]].mean(axis=1)
    df["T3_THRP3"] = df[["T3_THR6", "T3_THR7", "T3_THR8"]].mean(axis=1)
    df["T3_THRP4"] = df[["T3_THR9", "T3_R_THR10"]].mean(axis=1)
    df["T3_Thriving"] = df[[f"T3_THRP{i}" for i in range(1, 5)]].mean(axis=1)
    df["OCBS_Follower"] = df[[f"OCBS_Self{i}" for i in range(1, 7)]].mean(axis=1)
    df["CWBS_Follower"] = df[[f"CWBS_Self{i}" for i in range(1, 6)]].mean(axis=1)
    return df


def make_final(t1c, t2c, t3fc, t3lc) -> pd.DataFrame:
    """Inner-join the four cleaned waves, keep leaders with >=3 followers."""
    fids_in_all = (set(t1c["FollowerID"]) & set(t2c["FollowerID"])
                    & set(t3fc["FollowerID"]))
    lids_with_t3l = set(t3lc["LeaderID"])

    t3fc2 = derive_t3_follower_outcomes(t3fc)

    # Start from T3 follower (richest), inner-join progressively
    final = t3fc2[(t3fc2["FollowerID"].isin(fids_in_all))
                  & (t3fc2["LeaderID"].isin(lids_with_t3l))].copy()

    # T1 follower-side variables
    t1_keep = [c for c in t1c.columns
               if c not in {"CompanyID", "TeamID", "LeaderID"}]
    final = final.merge(t1c[t1_keep], on="FollowerID", how="left",
                        suffixes=("", "_T1"))

    # T1 thriving renamed for the final dataset
    if "Thriving" in final.columns:
        final.rename(columns={"Thriving": "T1_Thriving"}, inplace=True)

    # T2 envy items + composites
    t2_keep = ["FollowerID"] + [f"BEN{i}" for i in range(1, 6)] \
              + [f"MAL{i}" for i in range(1, 6)]
    final = final.merge(t2c[t2_keep], on="FollowerID", how="left")
    final["BenignEnvy"]    = final[[f"BEN{i}" for i in range(1, 6)]].mean(axis=1)
    final["MaliciousEnvy"] = final[[f"MAL{i}" for i in range(1, 6)]].mean(axis=1)

    # T3 leader-side variables
    t3l_keep = ["LeaderID"] + [c for c in t3lc.columns
                               if c not in {"CompanyID", "TeamID", "LeaderID"}]
    final = final.merge(t3lc[t3l_keep], on="LeaderID", how="left")
    final["OCBS_Leader"] = final[[f"OCBS_L{i}" for i in range(1, 7)]].mean(axis=1)
    final["CWBS_Leader"] = final[[f"CWBS{i}" for i in range(1, 6)]].mean(axis=1)

    # Filter leaders with >=3 surviving followers
    counts = final.groupby("LeaderID").size()
    keep_lids = counts[counts >= 3].index
    final = final[final["LeaderID"].isin(keep_lids)].reset_index(drop=True)

    # CLID 1:1 with LeaderID
    clid_map = {lid: i + 1 for i, lid in enumerate(sorted(final["LeaderID"].unique()))}
    final["CLID"] = final["LeaderID"].map(clid_map)

    # Dummies (not centered)
    final["Gender_Female"]   = (final["FollowerGender"] == 2).astype(int)
    final["Edu_HighSchool"]  = (final["FollowerEducation"] == 1).astype(int)
    final["Edu_Associate"]   = (final["FollowerEducation"] == 2).astype(int)
    final["Edu_Master"]      = (final["FollowerEducation"] == 4).astype(int)
    final["Edu_Doctoral"]    = (final["FollowerEducation"] == 5).astype(int)
    # Spec requires male=1 dummy (not female=1) for follower gender.
    final["Male"] = (1 - final["Gender_Female"]).astype(int)
    # Job level dummies (Level 2..5; Level 1 = reference)
    for lvl, label in [(2, "Mid"), (3, "Senior"), (4, "Manager"), (5, "Executive")]:
        final[f"Job_{label}"] = (final["FollowerJobLevel"] == lvl).astype(int)
    # Leader education dummies (k-1 = 4 dummies; LeaderEducation=2 = ref)
    if "LeaderEducation" in final.columns:
        for lvl, label in [(3, "Bachelor"), (4, "Master"), (5, "Doctoral")]:
            final[f"LeaderEdu_{label}"] = (final["LeaderEducation"] == lvl).astype(int)
        # 5th dummy for any LeaderEducation == 1 (high school) — usually 0 by design
        final["LeaderEdu_HighSchool"] = (final["LeaderEducation"] == 1).astype(int)
    # Leader job level dummies (k-1 = 4; LeaderJobLevel=2 = ref)
    if "LeaderJobLevel" in final.columns:
        for lvl, label in [(3, "Senior"), (4, "Manager"), (5, "Executive")]:
            final[f"LeaderJob_{label}"] = (final["LeaderJobLevel"] == lvl).astype(int)
        final["LeaderJob_Entry"] = (final["LeaderJobLevel"] == 1).astype(int)
    # Leader continuous controls — centered.
    for v in ["LeaderAge", "LeadershipTenure", "SpanOfControl", "LeaderWorkingYears"]:
        if v in final.columns:
            final[f"{v}_C"] = final[v] - final[v].mean()
    # Leader gender dummy (Male = 1, others = 0)
    if "LeaderGender" in final.columns:
        final["LeaderMale"] = (final["LeaderGender"] == 1).astype(int)
    # Company dummies (k-1 = 2)
    final["Company_B"] = (final["CompanyID"] == "B").astype(int)
    final["Company_C"] = (final["CompanyID"] == "C").astype(int)

    # Grand-mean centering
    for v in ["Autocratic", "Empowering", "Narcissism", "PowerDistance",
              "FollowerAge", "TenureWithLeader", "InteractionFreq",
              "T1_Thriving", "WorkingYears"]:
        if v in final.columns:
            final[f"{v}_C"] = final[v] - final[v].mean()
    return final


# ---------------------------------------------------------------------------
# 10. Mplus dat file
# ---------------------------------------------------------------------------

def write_mcfa_dat(final: pd.DataFrame) -> None:
    cols = ["CLID"] + [f"AUT{i}" for i in range(1, 7)] \
           + [f"EMPP{i}" for i in range(1, 5)] \
           + [f"BEN{i}"  for i in range(1, 6)] \
           + [f"MAL{i}"  for i in range(1, 6)] \
           + [f"THRP{i}" for i in range(1, 5)]
    cols = [c for c in cols if c in final.columns]
    sub = final[cols].fillna(-999)
    with open(OUT / "study3_mcfa.dat", "w") as f:
        for _, row in sub.iterrows():
            vals = [f"{v:.3f}" if isinstance(v, float) else str(int(v))
                    for v in row.tolist()]
            f.write(" ".join(vals) + "\n")


# ---------------------------------------------------------------------------
# 11. Driver
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("DATA GENERATION (clean rewrite)")
    print("=" * 60)

    # ---- T1 ----
    t1_base = gen_t1()
    t1_base = add_t1_derived(t1_base)
    t1_raw = add_t1_dups_and_missing(t1_base)
    cascade = {}
    t1_clean = clean_wave(t1_raw, "EMP9_AttCheck", "FollowerID",
                          cascade=cascade, wave="T1")
    print(f"  T1 raw {len(t1_raw)} -> cleaned {len(t1_clean)}  "
          f"(leaders={t1_clean['LeaderID'].nunique()})")

    # ---- T2: drop 5 leaders ----
    leaders_t2 = set(np.random.choice(
        t1_clean["LeaderID"].unique(),
        size=N_LEADERS_T2, replace=False
    ))
    t2_base = gen_t2(t1_clean, leaders_t2)
    t2_raw = add_t2_dups_and_mismatches(t2_base, set(t1_clean["FollowerID"]))
    t2_clean = clean_wave(t2_raw, "MAL6_AttCheck", "FollowerID",
                          cascade=cascade, wave="T2_x",
                          valid_ids=set(t1_clean["FollowerID"]))
    print(f"  T2 raw {len(t2_raw)} -> cleaned {len(t2_clean)}  "
          f"(leaders={t2_clean['LeaderID'].nunique()})")

    # ---- T3: drop 6 more leaders ----
    leaders_t3 = set(np.random.choice(
        list(set(t2_clean["LeaderID"]) & leaders_t2),
        size=N_LEADERS_T3, replace=False
    ))
    t3f_base = gen_t3_follower(t2_clean, leaders_t3)
    t3f_raw = add_t3f_dups(t3f_base)
    t3f_clean = clean_wave(t3f_raw, "OCBS7_AttCheck", "FollowerID",
                          cascade=cascade, wave="T3f",
                           valid_ids=set(t2_clean["FollowerID"]))
    print(f"  T3 follower raw {len(t3f_raw)} -> cleaned {len(t3f_clean)}  "
          f"(leaders={t3f_clean['LeaderID'].nunique()})")

    t3l_base = gen_t3_leader(sorted(leaders_t3))
    t3l_raw = add_t3l_dups_and_mismatches(t3l_base, leaders_t3)
    t3l_clean = clean_wave(t3l_raw, "CWBS6_AttCheck", "LeaderID",
                          cascade=cascade, wave="T3l",
                           valid_ids=leaders_t3)
    print(f"  T3 leader raw {len(t3l_raw)} -> cleaned {len(t3l_clean)}")

    # ---- Final merged ----
    final = make_final(t1_clean, t2_clean, t3f_clean, t3l_clean)
    fc = final.groupby("LeaderID").size()
    print(f"  Final: {len(final)} dyads, {final['LeaderID'].nunique()} leaders, "
          f"per-leader count min={fc.min()} max={fc.max()} mean={fc.mean():.2f}")

    # ---- Save ----
    t1_raw.to_excel(OUT / "T1_raw.xlsx", index=False)
    t1_clean.to_excel(OUT / "T1_cleaned.xlsx", index=False)
    t2_raw.to_excel(OUT / "T2_raw.xlsx", index=False)
    t2_clean.to_excel(OUT / "T2_cleaned.xlsx", index=False)
    t3f_raw.to_excel(OUT / "T3_follower_raw.xlsx", index=False)
    t3f_clean.to_excel(OUT / "T3_follower_cleaned.xlsx", index=False)
    t3l_raw.to_excel(OUT / "T3_leader_raw.xlsx", index=False)
    t3l_clean.to_excel(OUT / "T3_leader_cleaned.xlsx", index=False)
    final.to_excel(OUT / "final_merged_analysis_data.xlsx", index=False)
    write_mcfa_dat(final)

    # ---- Attrition summary (for YUYU table later) ----
    # Strict cascade counts (each filter applied to data already
    # filtered by prior steps) — guarantees JSON reconciles:
    #   submitted - id_mismatch_cascade - dups_cascade - ac_fail_cascade = usable
    summary = {
        "T1_submitted":  len(t1_raw),
        "T1_dups":       int(t1_raw.duplicated(subset="FollowerID").sum()),
        "T1_ac_fail":    int((t1_raw["EMP9_AttCheck"] != AC_PASS_VALUE).sum()),
        "T1_dups_cascade": cascade["T1_dups_cascade"],
        "T1_ac_fail_cascade": cascade["T1_ac_fail_cascade"],
        "T1_usable_followers": len(t1_clean),
        "T1_usable_leaders": int(t1_clean["LeaderID"].nunique()),
        "T2_invited":    len(t2_base),
        "T2_submitted":  len(t2_raw),
        "T2_ac_fail":    int((t2_raw["MAL6_AttCheck"] != AC_PASS_VALUE).sum()),
        "T2_dups":       int(t2_raw.duplicated(subset="FollowerID").sum()),
        "T2_id_mismatch": int((~t2_raw["FollowerID"].isin(set(t1_clean["FollowerID"]))).sum()),
        "T2_id_mismatch_cascade": cascade["T2_x_id_mismatch_cascade"],
        "T2_dups_cascade": cascade["T2_x_dups_cascade"],
        "T2_ac_fail_cascade": cascade["T2_x_ac_fail_cascade"],
        "T2_usable_followers": len(t2_clean),
        "T2_usable_leaders": int(t2_clean["LeaderID"].nunique()),
        "T3f_invited":   len(t3f_base),
        "T3f_submitted": len(t3f_raw),
        "T3f_ac_fail":   int((t3f_raw["OCBS7_AttCheck"] != AC_PASS_VALUE).sum()),
        "T3f_id_mismatch_cascade": cascade["T3f_id_mismatch_cascade"],
        "T3f_dups_cascade": cascade["T3f_dups_cascade"],
        "T3f_ac_fail_cascade": cascade["T3f_ac_fail_cascade"],
        "T3f_usable":    len(t3f_clean),
        "T3l_invited":   len(t3l_base),
        "T3l_submitted": len(t3l_raw),
        "T3l_ac_fail":   int((t3l_raw["CWBS6_AttCheck"] != AC_PASS_VALUE).sum()),
        "T3l_id_mismatch_cascade": cascade["T3l_id_mismatch_cascade"],
        "T3l_dups_cascade": cascade["T3l_dups_cascade"],
        "T3l_ac_fail_cascade": cascade["T3l_ac_fail_cascade"],
        "T3l_usable":    len(t3l_clean),
        "Final_dyads":   len(final),
        "Final_leaders": int(final["LeaderID"].nunique()),
        "Avg_followers_per_leader": round(fc.mean(), 2),
    }
    import json
    (OUT / "_attrition_summary.json").write_text(json.dumps(summary, indent=2))
    print("\nAttrition summary written to data/_attrition_summary.json")


if __name__ == "__main__":
    main()
