"""
Constraint Validator for Leadership Survey Data
Checks ALL requirements from the project specification.
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent

PASS = "PASS"
FAIL = "FAIL"


def check(name, condition, detail=""):
    """Print pass/fail for a check."""
    status = PASS if condition else FAIL
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)
    return condition


def validate_all():
    """Run all constraint checks."""
    print("=" * 60)
    print("CONSTRAINT VALIDATOR")
    print("=" * 60)

    results = []

    # Load all files
    print("\nLoading data files...")
    try:
        t1_raw = pd.read_excel(DATA_DIR / 'T1_raw.xlsx')
        t1_clean = pd.read_excel(DATA_DIR / 'T1_cleaned.xlsx')
        t2_raw = pd.read_excel(DATA_DIR / 'T2_raw.xlsx')
        t2_clean = pd.read_excel(DATA_DIR / 'T2_cleaned.xlsx')
        t3_leader_raw = pd.read_excel(DATA_DIR / 'T3_leader_raw.xlsx')
        t3_leader_clean = pd.read_excel(DATA_DIR / 'T3_leader_cleaned.xlsx')
        t3_follower_raw = pd.read_excel(DATA_DIR / 'T3_follower_raw.xlsx')
        t3_follower_clean = pd.read_excel(DATA_DIR / 'T3_follower_cleaned.xlsx')
        final = pd.read_excel(DATA_DIR / 'final_merged_analysis_data.xlsx')
    except FileNotFoundError as e:
        print(f"  ERROR: {e}")
        print("  Run data_generator.py first!")
        return False

    print("  All files loaded successfully.\n")

    # --- SECTION 1: Sample Sizes ---
    print("-" * 40)
    print("SECTION 1: Sample Sizes")
    print("-" * 40)

    results.append(check("T1 cleaned rows == 449",
                         len(t1_clean) == 449,
                         f"got {len(t1_clean)}"))

    results.append(check("T1 leaders == 90",
                         t1_clean['LeaderID'].nunique() == 90,
                         f"got {t1_clean['LeaderID'].nunique()}"))

    results.append(check("T2 cleaned rows == 444",
                         len(t2_clean) == 444,
                         f"got {len(t2_clean)}"))

    results.append(check("T2 leaders == 85",
                         t2_clean['LeaderID'].nunique() == 85,
                         f"got {t2_clean['LeaderID'].nunique()}"))

    results.append(check("T3 leader cleaned rows == 79",
                         len(t3_leader_clean) == 79,
                         f"got {len(t3_leader_clean)}"))

    results.append(check("T3 follower cleaned rows == 438",
                         len(t3_follower_clean) == 438,
                         f"got {len(t3_follower_clean)}"))

    results.append(check("T3 follower leaders == 79",
                         t3_follower_clean['LeaderID'].nunique() == 79,
                         f"got {t3_follower_clean['LeaderID'].nunique()}"))

    results.append(check("Final merged rows == 438",
                         len(final) == 438,
                         f"got {len(final)}"))

    results.append(check("Final merged leaders == 79",
                         final['LeaderID'].nunique() == 79,
                         f"got {final['LeaderID'].nunique()}"))

    # --- SECTION 2: Raw > Cleaned ---
    print("\n" + "-" * 40)
    print("SECTION 2: Raw has MORE rows than Cleaned")
    print("-" * 40)

    results.append(check("T1 raw > T1 cleaned",
                         len(t1_raw) > len(t1_clean),
                         f"{len(t1_raw)} > {len(t1_clean)}"))

    results.append(check("T2 raw > T2 cleaned",
                         len(t2_raw) > len(t2_clean),
                         f"{len(t2_raw)} > {len(t2_clean)}"))

    results.append(check("T3 leader raw > T3 leader cleaned",
                         len(t3_leader_raw) > len(t3_leader_clean),
                         f"{len(t3_leader_raw)} > {len(t3_leader_clean)}"))

    results.append(check("T3 follower raw > T3 follower cleaned",
                         len(t3_follower_raw) > len(t3_follower_clean),
                         f"{len(t3_follower_raw)} > {len(t3_follower_clean)}"))

    # --- SECTION 3: Min 3 subordinates per leader ---
    print("\n" + "-" * 40)
    print("SECTION 3: Minimum 3 subordinates per leader")
    print("-" * 40)

    for name, df in [("T3 follower cleaned", t3_follower_clean), ("Final merged", final)]:
        min_subs = df.groupby('LeaderID').size().min()
        results.append(check(f"{name}: min subs >= 3",
                             min_subs >= 3,
                             f"min={min_subs}"))

    # --- SECTION 4: Attention Check Items ---
    print("\n" + "-" * 40)
    print("SECTION 4: Attention Check Items Present")
    print("-" * 40)

    results.append(check("T1 has EMP9_AttCheck",
                         'EMP9_AttCheck' in t1_clean.columns))

    results.append(check("T2 has MAL6_AttCheck",
                         'MAL6_AttCheck' in t2_clean.columns))

    results.append(check("T3 follower has OCBS7_AttCheck",
                         'OCBS7_AttCheck' in t3_follower_clean.columns))

    results.append(check("T3 leader has CWBS6_AttCheck",
                         'CWBS6_AttCheck' in t3_leader_clean.columns))

    # --- SECTION 5: CLID ---
    print("\n" + "-" * 40)
    print("SECTION 5: CLID (Numeric Cluster ID)")
    print("-" * 40)

    results.append(check("CLID exists in final",
                         'CLID' in final.columns))

    if 'CLID' in final.columns:
        results.append(check("CLID is numeric",
                             pd.api.types.is_numeric_dtype(final['CLID'])))

        results.append(check("CLID range: 1 to 79",
                             final['CLID'].min() == 1 and final['CLID'].max() == 79,
                             f"range [{final['CLID'].min()}, {final['CLID'].max()}]"))

        # 1:1 mapping
        mapping = final[['LeaderID', 'CLID']].drop_duplicates()
        results.append(check("CLID 1:1 with LeaderID",
                             len(mapping) == final['LeaderID'].nunique(),
                             f"unique mappings={len(mapping)}, unique leaders={final['LeaderID'].nunique()}"))

    # --- SECTION 6: LeaderEducation ---
    print("\n" + "-" * 40)
    print("SECTION 6: LeaderEducation")
    print("-" * 40)

    le_col = None
    for col_name in ['LeaderEducation']:
        if col_name in final.columns:
            le_col = col_name
            break

    if le_col:
        le_min = final[le_col].min()
        le_max = final[le_col].max()
        results.append(check("LeaderEducation range [2, 5]",
                             le_min >= 2 and le_max <= 5,
                             f"range [{le_min}, {le_max}]"))
        le_nan = final[le_col].isna().sum()
        results.append(check("LeaderEducation no NaN",
                             le_nan == 0,
                             f"found {le_nan} NaN values"))
    else:
        # Check in T1 cleaned
        if 'LeaderEducation' in t1_clean.columns:
            le_min = t1_clean['LeaderEducation'].min()
            le_max = t1_clean['LeaderEducation'].max()
            results.append(check("LeaderEducation range [2, 5] (in T1)",
                                 le_min >= 2 and le_max <= 5,
                                 f"range [{le_min}, {le_max}]"))
        else:
            results.append(check("LeaderEducation exists", False, "not found"))

    # --- SECTION 7: Centering ---
    print("\n" + "-" * 40)
    print("SECTION 7: Grand-Mean Centering")
    print("-" * 40)

    centered_vars = [col for col in final.columns if col.endswith('_C')]
    results.append(check("Centered variables exist (_C suffix)",
                         len(centered_vars) > 0,
                         f"found {len(centered_vars)}: {centered_vars[:5]}..."))

    # Mean of centered vars should be ~0
    for cv in centered_vars:
        mean_val = final[cv].mean()
        results.append(check(f"  {cv} mean ~ 0",
                             abs(mean_val) < 0.001,
                             f"mean={mean_val:.6f}"))

    # Dummy variables should NOT be centered
    dummy_cols = [col for col in final.columns if 'Gender_' in col or 'Edu_' in col]
    if dummy_cols:
        centered_dummies = [col for col in dummy_cols if col.endswith('_C')]
        results.append(check("Dummy variables NOT centered",
                             len(centered_dummies) == 0,
                             f"centered dummies: {centered_dummies}" if centered_dummies else "correct"))

    # --- SECTION 8: Duplicate IDs in Raw ---
    print("\n" + "-" * 40)
    print("SECTION 8: Duplicate IDs in Raw Data")
    print("-" * 40)

    # T1 raw duplicates
    if 'FollowerID' in t1_raw.columns:
        t1_dupes = t1_raw['FollowerID'].duplicated().sum()
        results.append(check("T1 raw has duplicate IDs (<=10)",
                             0 < t1_dupes <= 10,
                             f"found {t1_dupes} duplicates"))

    # T2 raw duplicates
    if 'FollowerID' in t2_raw.columns:
        t2_dupes = t2_raw['FollowerID'].duplicated().sum()
        results.append(check("T2 raw has duplicate IDs (<=5)",
                             0 < t2_dupes <= 5,
                             f"found {t2_dupes} duplicates"))

    # T3 leader raw duplicates
    if 'LeaderID' in t3_leader_raw.columns:
        t3l_dupes = t3_leader_raw['LeaderID'].duplicated().sum()
        results.append(check("T3 leader raw has duplicate IDs (<=1)",
                             0 < t3l_dupes <= 1,
                             f"found {t3l_dupes} duplicates"))

    # --- SECTION 9: ID Mismatches in Raw ---
    print("\n" + "-" * 40)
    print("SECTION 9: ID Mismatches in Raw Data")
    print("-" * 40)

    # T2 should have 3 mismatched IDs
    if 'FollowerID' in t2_raw.columns:
        t1_fids = set(t1_clean['FollowerID'].unique())
        t2_raw_fids = set(t2_raw['FollowerID'].unique())
        mismatches_t2 = t2_raw_fids - t1_fids
        results.append(check("T2 raw has 3 ID mismatches",
                             len(mismatches_t2) >= 3,
                             f"found {len(mismatches_t2)} mismatched IDs"))

    # T3 leader should have 1 mismatch
    if 'LeaderID' in t3_leader_raw.columns:
        t2_lids = set(t2_clean['LeaderID'].unique())
        t3l_raw_lids = set(t3_leader_raw['LeaderID'].unique())
        mismatches_t3l = t3l_raw_lids - t2_lids
        results.append(check("T3 leader raw has 1 ID mismatch",
                             len(mismatches_t3l) >= 1,
                             f"found {len(mismatches_t3l)} mismatched IDs"))

    # --- SECTION 10: Missing Data ---
    print("\n" + "-" * 40)
    print("SECTION 10: Missing Data Simulation")
    print("-" * 40)

    # T1 raw: ~10 missing in non-core
    t1_missing = t1_raw.isnull().sum().sum()
    results.append(check("T1 raw has ~10 missing values",
                         5 <= t1_missing <= 15,
                         f"found {t1_missing} total missing"))

    # T2 raw: ZERO missing values (requirement: "T2 设置为零缺失值")
    t2_total_missing = t2_raw.isnull().sum().sum()
    results.append(check("T2 raw: ZERO missing values",
                         t2_total_missing == 0,
                         f"found {t2_total_missing} total missing"))

    # T3 leader raw: ~3 missing in non-core
    t3l_missing = t3_leader_raw.isnull().sum().sum()
    results.append(check("T3 leader raw: ~3 missing in non-core",
                         1 <= t3l_missing <= 5,
                         f"found {t3l_missing} total missing"))

    # --- SECTION 11: Required Columns ---
    print("\n" + "-" * 40)
    print("SECTION 11: Required Columns Exist")
    print("-" * 40)

    # T1 must have AUT, EMP, THR, NARC, PD items
    t1_required = ['AUT1', 'AUT6', 'EMP1', 'EMP12', 'THR1', 'R_THR5', 'R_THR10',
                   'NARC1', 'PD1', 'LeaderID', 'FollowerID']
    for col in t1_required:
        results.append(check(f"T1 has {col}", col in t1_clean.columns))

    # T2 must have BEN, MAL items
    t2_required = ['BEN1', 'BEN5', 'MAL1', 'MAL5', 'LeaderID', 'FollowerID']
    for col in t2_required:
        results.append(check(f"T2 has {col}", col in t2_clean.columns))

    # Final must have parcels, scale scores, CLID
    final_required = ['EMPP1', 'EMPP4', 'THRP1', 'THRP4', 'CLID',
                      'Autocratic', 'Empowering', 'BenignEnvy', 'MaliciousEnvy',
                      'LeaderID', 'FollowerID']
    for col in final_required:
        results.append(check(f"Final has {col}", col in final.columns))

    # --- SECTION 12: Parcel Computation ---
    print("\n" + "-" * 40)
    print("SECTION 12: Parcel Computation Correctness")
    print("-" * 40)

    # Spot-check EMPP1 = mean(EMP1, EMP2, EMP3)
    if all(c in t1_clean.columns for c in ['EMP1', 'EMP2', 'EMP3', 'EMPP1']):
        expected_empp1 = t1_clean[['EMP1', 'EMP2', 'EMP3']].mean(axis=1)
        diff = (t1_clean['EMPP1'] - expected_empp1).abs().max()
        results.append(check("EMPP1 = mean(EMP1, EMP2, EMP3)",
                             diff < 0.001,
                             f"max diff = {diff:.6f}"))

    # Spot-check THRP1 = mean(THR1, THR3, R_THR5)
    if all(c in t1_clean.columns for c in ['THR1', 'THR3', 'R_THR5', 'THRP1']):
        expected_thrp1 = t1_clean[['THR1', 'THR3', 'R_THR5']].mean(axis=1)
        diff = (t1_clean['THRP1'] - expected_thrp1).abs().max()
        results.append(check("THRP1 = mean(THR1, THR3, R_THR5)",
                             diff < 0.001,
                             f"max diff = {diff:.6f}"))

    # Spot-check EMPP4 = mean(EMP10, EMP11, EMP12)
    if all(c in t1_clean.columns for c in ['EMP10', 'EMP11', 'EMP12', 'EMPP4']):
        expected_empp4 = t1_clean[['EMP10', 'EMP11', 'EMP12']].mean(axis=1)
        diff = (t1_clean['EMPP4'] - expected_empp4).abs().max()
        results.append(check("EMPP4 = mean(EMP10, EMP11, EMP12)",
                             diff < 0.001,
                             f"max diff = {diff:.6f}"))

    # --- SUMMARY ---
    print("\n" + "=" * 60)
    n_pass = sum(results)
    n_total = len(results)
    n_fail = n_total - n_pass
    print(f"SUMMARY: {n_pass}/{n_total} checks PASSED, {n_fail} FAILED")
    if n_fail == 0:
        print("ALL CONSTRAINTS SATISFIED!")
    else:
        print(f"WARNING: {n_fail} constraints not met. Fix and re-run.")
    print("=" * 60)

    return n_fail == 0


if __name__ == '__main__':
    success = validate_all()
    exit(0 if success else 1)
