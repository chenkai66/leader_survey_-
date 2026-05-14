"""
Data Generator for Leadership Survey Study (Study 3)
Generates simulated 3-wave longitudinal survey data with proper
leader-subordinate nesting, attention checks, and realistic properties.
"""

import numpy as np
import pandas as pd
from pathlib import Path

# Reproducibility
np.random.seed(42)

OUTPUT_DIR = Path(__file__).parent.parent / "data"


def generate_likert_items(n_rows, n_items, mean=3.5, sd=0.8, scale_min=1,
                          scale_max=5, icc=0.15, leader_ids=None,
                          correlation=0.5):
    """
    Generate correlated Likert-scale items with leader-level clustering (ICC).

    Parameters
    ----------
    n_rows : int
        Number of individual-level rows
    n_items : int
        Number of items to generate
    mean : float
        Target mean for items
    sd : float
        Target SD for items
    scale_min, scale_max : int
        Likert scale bounds
    icc : float
        Intra-class correlation (proportion of variance at leader level)
    leader_ids : array-like
        Leader IDs for each row (for clustering)
    correlation : float
        Average inter-item correlation within construct
    """
    unique_leaders = np.unique(leader_ids)
    n_leaders = len(unique_leaders)

    # Between-group variance component
    between_var = icc * sd**2
    within_var = (1 - icc) * sd**2

    # Generate leader-level means
    leader_means = np.random.normal(mean, np.sqrt(between_var), n_leaders)
    leader_mean_map = dict(zip(unique_leaders, leader_means))

    # Generate correlated items within each person
    # Use a factor model: X_i = lambda * F + epsilon
    lam = np.sqrt(correlation)
    eps_sd = np.sqrt(1 - correlation)

    data = np.zeros((n_rows, n_items))
    for i in range(n_rows):
        lid = leader_ids[i]
        group_mean = leader_mean_map[lid]
        # Common factor for this person
        factor = np.random.normal(0, 1)
        for j in range(n_items):
            raw = group_mean + lam * factor * np.sqrt(within_var) + \
                  eps_sd * np.random.normal(0, np.sqrt(within_var))
            data[i, j] = raw

    # Round and clip to Likert scale
    data = np.round(data).astype(int)
    data = np.clip(data, scale_min, scale_max)

    return data


def generate_demographics(n_rows, leader_ids):
    """Generate demographic variables for followers."""
    unique_leaders = np.unique(leader_ids)

    # Follower age: 22-55
    age = np.random.normal(30, 5, n_rows).round().astype(int)
    age = np.clip(age, 22, 55)

    # Gender: 1=male, 2=female
    gender = np.random.choice([1, 2], n_rows, p=[0.55, 0.45])

    # Education: 1=high school, 2=associate, 3=bachelor, 4=master, 5=doctoral
    education = np.random.choice([1, 2, 3, 4, 5], n_rows, p=[0.05, 0.15, 0.50, 0.25, 0.05])

    # Working years
    working_years = (age - 22 + np.random.normal(0, 2, n_rows)).round().astype(int)
    working_years = np.clip(working_years, 0, 35)

    # Tenure with current leader (years): 0.5-10
    tenure_leader = np.random.exponential(2.5, n_rows).round(1)
    tenure_leader = np.clip(tenure_leader, 0.5, 10)

    # Interaction frequency: 1-5 scale
    interaction_freq = np.random.choice([1, 2, 3, 4, 5], n_rows, p=[0.05, 0.15, 0.35, 0.30, 0.15])

    # Leader education: range 2-5 (one per leader)
    leader_edu_map = {}
    for lid in unique_leaders:
        leader_edu_map[lid] = np.random.choice([2, 3, 4, 5], p=[0.10, 0.35, 0.40, 0.15])
    leader_education = np.array([leader_edu_map[lid] for lid in leader_ids])

    return {
        'FollowerAge': age,
        'FollowerGender': gender,
        'FollowerEducation': education,
        'WorkingYears': working_years,
        'TenureWithLeader': tenure_leader,
        'InteractionFreq': interaction_freq,
        'LeaderEducation': leader_education,
    }


def create_leader_subordinate_structure(n_leaders, min_subs=3, max_subs=7):
    """Create leader-subordinate nesting with >=3 subs per leader."""
    leader_ids = []
    follower_ids = []
    follower_count = 0

    for i in range(1, n_leaders + 1):
        n_subs = np.random.randint(min_subs, max_subs + 1)
        for j in range(n_subs):
            follower_count += 1
            leader_ids.append(f"L{i:03d}")
            follower_ids.append(f"F{follower_count:04d}")

    return np.array(leader_ids), np.array(follower_ids)


def simulate_attrition(leader_ids, follower_ids, n_leaders_to_drop):
    """Simulate wave-to-wave attrition by dropping entire leader groups."""
    unique_leaders = np.unique(leader_ids)
    leaders_to_drop = np.random.choice(unique_leaders, n_leaders_to_drop, replace=False)
    mask = ~np.isin(leader_ids, leaders_to_drop)
    return leader_ids[mask], follower_ids[mask], mask


def generate_t1_data(leader_ids, follower_ids):
    """Generate T1 wave data (90 leaders)."""
    n = len(leader_ids)
    print(f"  Generating T1 data: {n} followers, {len(np.unique(leader_ids))} leaders")

    # Core constructs
    aut_items = generate_likert_items(n, 6, mean=3.2, sd=0.9, leader_ids=leader_ids, icc=0.18, correlation=0.55)
    emp_items = generate_likert_items(n, 12, mean=3.6, sd=0.8, leader_ids=leader_ids, icc=0.20, correlation=0.50)

    # Thriving (10 items, items 5 and 10 are reverse-coded)
    thr_items = generate_likert_items(n, 10, mean=3.7, sd=0.7, leader_ids=leader_ids, icc=0.12, correlation=0.45)
    # Reverse code items 5 and 10 (0-indexed: 4 and 9)
    thr_items[:, 4] = 6 - thr_items[:, 4]  # R_THR5
    thr_items[:, 9] = 6 - thr_items[:, 9]  # R_THR10

    # Narcissism (6 items, 1-5 scale)
    narc_items = generate_likert_items(n, 6, mean=2.8, sd=0.9, leader_ids=leader_ids, icc=0.10, correlation=0.50)

    # Power Distance (6 items, 1-5 scale)
    pd_items = generate_likert_items(n, 6, mean=3.0, sd=0.8, leader_ids=leader_ids, icc=0.12, correlation=0.45)

    # Demographics
    demo = generate_demographics(n, leader_ids)

    # Attention check: EMP9 (empowering leadership item 9)
    # Item 9 is index 8 in emp_items - we'll add a separate attention check column
    attention_check_emp9 = np.random.choice([1, 2, 3, 4, 5], n, p=[0.02, 0.03, 0.90, 0.03, 0.02])

    # Build dataframe
    df = pd.DataFrame({
        'LeaderID': leader_ids,
        'FollowerID': follower_ids,
    })

    # AUT items
    for i in range(6):
        df[f'AUT{i+1}'] = aut_items[:, i]

    # EMP items
    for i in range(12):
        df[f'EMP{i+1}'] = emp_items[:, i]

    # Attention check EMP9 (replaces the actual EMP9 in the attention check analysis)
    df['EMP9_AttCheck'] = attention_check_emp9

    # THR items (with reverse coding labels)
    for i in range(10):
        if i == 4:
            df['R_THR5'] = thr_items[:, i]
        elif i == 9:
            df['R_THR10'] = thr_items[:, i]
        else:
            df[f'THR{i+1}'] = thr_items[:, i]

    # Narcissism
    for i in range(6):
        df[f'NARC{i+1}'] = narc_items[:, i]

    # Power Distance
    for i in range(6):
        df[f'PD{i+1}'] = pd_items[:, i]

    # Demographics
    for key, val in demo.items():
        df[key] = val

    return df


def generate_t2_data(leader_ids, follower_ids):
    """Generate T2 wave data (85 leaders) - Envy measures."""
    n = len(leader_ids)
    print(f"  Generating T2 data: {n} followers, {len(np.unique(leader_ids))} leaders")

    # Benign envy (5 items)
    ben_items = generate_likert_items(n, 5, mean=3.0, sd=0.9, leader_ids=leader_ids, icc=0.15, correlation=0.55)

    # Malicious envy (5 items)
    mal_items = generate_likert_items(n, 5, mean=2.2, sd=0.8, leader_ids=leader_ids, icc=0.13, correlation=0.55)

    # Attention check: MAL6 (malicious envy item 6 - extra item)
    attention_check_mal6 = np.random.choice([1, 2, 3, 4, 5], n, p=[0.02, 0.03, 0.90, 0.03, 0.02])

    # Demographics (subset needed for T2)
    demo = generate_demographics(n, leader_ids)

    df = pd.DataFrame({
        'LeaderID': leader_ids,
        'FollowerID': follower_ids,
    })

    # BEN items
    for i in range(5):
        df[f'BEN{i+1}'] = ben_items[:, i]

    # MAL items
    for i in range(5):
        df[f'MAL{i+1}'] = mal_items[:, i]

    # Attention check
    df['MAL6_AttCheck'] = attention_check_mal6

    # Add some demographics
    df['FollowerAge'] = demo['FollowerAge']
    df['FollowerGender'] = demo['FollowerGender']

    return df


def generate_t3_follower_data(leader_ids, follower_ids):
    """Generate T3 follower-rated data (79 leaders)."""
    n = len(leader_ids)
    print(f"  Generating T3 follower data: {n} followers, {len(np.unique(leader_ids))} leaders")

    # Thriving T3 (10 items, same structure as T1)
    thr_items = generate_likert_items(n, 10, mean=3.6, sd=0.7, leader_ids=leader_ids, icc=0.12, correlation=0.45)
    thr_items[:, 4] = 6 - thr_items[:, 4]
    thr_items[:, 9] = 6 - thr_items[:, 9]

    # OCBS (follower-rated, 8 items including attention check at item 7)
    ocbs_items = generate_likert_items(n, 8, mean=3.5, sd=0.7, leader_ids=leader_ids, icc=0.10, correlation=0.50)

    # Attention check: OCBS7
    attention_check_ocbs7 = np.random.choice([1, 2, 3, 4, 5], n, p=[0.02, 0.03, 0.90, 0.03, 0.02])

    # Follower-rated CWBS (for Model 3 robustness)
    cwbs_follower_items = generate_likert_items(n, 7, mean=1.8, sd=0.6, leader_ids=leader_ids, icc=0.10, correlation=0.50)

    df = pd.DataFrame({
        'LeaderID': leader_ids,
        'FollowerID': follower_ids,
    })

    # THR items T3
    for i in range(10):
        if i == 4:
            df['T3_R_THR5'] = thr_items[:, i]
        elif i == 9:
            df['T3_R_THR10'] = thr_items[:, i]
        else:
            df[f'T3_THR{i+1}'] = thr_items[:, i]

    # OCBS items
    for i in range(8):
        if i == 6:  # item 7 is attention check position
            df['OCBS7_AttCheck'] = attention_check_ocbs7
            df[f'OCBS{i+1}'] = ocbs_items[:, i]
        else:
            df[f'OCBS{i+1}'] = ocbs_items[:, i]

    # Follower-rated CWBS
    for i in range(7):
        df[f'CWBS_F{i+1}'] = cwbs_follower_items[:, i]

    # Follower-rated OCBS (for Model 3 - self-rated)
    ocbs_self_items = generate_likert_items(n, 8, mean=3.4, sd=0.7, leader_ids=leader_ids, icc=0.08, correlation=0.45)
    for i in range(8):
        df[f'OCBS_Self{i+1}'] = ocbs_self_items[:, i]

    return df


def generate_t3_leader_data(leader_ids):
    """Generate T3 leader-rated data (79 leaders rate their subordinates)."""
    n_leaders = len(leader_ids)
    print(f"  Generating T3 leader data: {n_leaders} leaders")

    # For leader-rated data, each leader rates all their subordinates
    # CWBS (leader rates subordinates, 7 items)
    # OCBS (leader rates subordinates, 8 items)
    # We generate one row per leader with their ratings

    # CWBS items (leader-rated)
    cwbs_items = np.random.normal(2.0, 0.7, (n_leaders, 7))
    cwbs_items = np.round(cwbs_items).astype(int)
    cwbs_items = np.clip(cwbs_items, 1, 5)

    # OCBS items (leader-rated)
    ocbs_items = np.random.normal(3.5, 0.7, (n_leaders, 8))
    ocbs_items = np.round(ocbs_items).astype(int)
    ocbs_items = np.clip(ocbs_items, 1, 5)

    # Attention check: CWBS6
    attention_check_cwbs6 = np.random.choice([1, 2, 3, 4, 5], n_leaders, p=[0.02, 0.03, 0.90, 0.03, 0.02])

    # Leader demographics
    leader_age = np.random.normal(40, 6, n_leaders).round().astype(int)
    leader_age = np.clip(leader_age, 28, 60)
    leader_gender = np.random.choice([1, 2], n_leaders, p=[0.60, 0.40])

    df = pd.DataFrame({
        'LeaderID': leader_ids,
    })

    for i in range(7):
        df[f'CWBS{i+1}'] = cwbs_items[:, i]

    for i in range(8):
        df[f'OCBS_L{i+1}'] = ocbs_items[:, i]

    df['CWBS6_AttCheck'] = attention_check_cwbs6
    df['LeaderAge'] = leader_age
    df['LeaderGender'] = leader_gender

    return df


def add_raw_defects_t1(df_clean):
    """Add simulated defects to T1 raw data."""
    df = df_clean.copy()
    n = len(df)

    # Add ~10 missing values in non-core demographics
    non_core_cols = ['FollowerAge', 'FollowerGender', 'FollowerEducation', 'WorkingYears']
    missing_indices = np.random.choice(n, 10, replace=False)
    for idx in missing_indices:
        col = np.random.choice(non_core_cols)
        df.loc[df.index[idx], col] = np.nan

    # Add <=10 duplicate IDs (copy some rows with same FollowerID)
    n_dupes = np.random.randint(5, 11)
    dupe_indices = np.random.choice(n, n_dupes, replace=False)
    dupes = df.iloc[dupe_indices].copy()
    # Slightly alter some responses for duplicates (realistic: person submitted twice)
    for col in ['AUT1', 'AUT2', 'EMP1', 'EMP2']:
        noise = np.random.choice([-1, 0, 0, 0, 1], len(dupes))
        dupes[col] = np.clip(dupes[col] + noise, 1, 5)

    df = pd.concat([df, dupes], ignore_index=True)
    # Shuffle
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    return df


def add_raw_defects_t2(df_clean):
    """Add simulated defects to T2 raw data."""
    df = df_clean.copy()
    n = len(df)

    # Add <=5 duplicate IDs with IDENTICAL responses
    n_dupes = np.random.randint(3, 6)
    dupe_indices = np.random.choice(n, n_dupes, replace=False)
    dupes = df.iloc[dupe_indices].copy()  # Identical copies
    df = pd.concat([df, dupes], ignore_index=True)

    # Add 3 ID mismatches (fake IDs that don't exist in T1)
    mismatch_rows = df.iloc[np.random.choice(len(df), 3, replace=False)].copy()
    mismatch_rows['FollowerID'] = [f'F_MISMATCH_{i}' for i in range(3)]
    mismatch_rows['LeaderID'] = [f'L_MISMATCH_{i}' for i in range(3)]
    df = pd.concat([df, mismatch_rows], ignore_index=True)

    # T2 requirement: ZERO missing values (do not add any)
    # Ensure no NaN crept in from concatenation or type coercion
    for col in df.columns:
        if df[col].isnull().any():
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].median())
            else:
                df[col] = df[col].fillna(df[col].mode().iloc[0])

    # Shuffle
    df = df.sample(frac=1, random_state=43).reset_index(drop=True)

    return df


def add_raw_defects_t3_leader(df_clean):
    """Add simulated defects to T3 leader raw data."""
    df = df_clean.copy()
    n = len(df)

    # Add ~3 missing in non-core
    non_core_cols = ['LeaderAge', 'LeaderGender']
    for _ in range(3):
        idx = np.random.randint(0, n)
        col = np.random.choice(non_core_cols)
        df.loc[df.index[idx], col] = np.nan

    # Add <=1 duplicate ID
    dupe_idx = np.random.randint(0, n)
    dupe = df.iloc[[dupe_idx]].copy()
    df = pd.concat([df, dupe], ignore_index=True)

    # Add 1 ID mismatch
    mismatch_row = df.iloc[[np.random.randint(0, len(df))]].copy()
    mismatch_row['LeaderID'] = 'L_MISMATCH_X'
    df = pd.concat([df, mismatch_row], ignore_index=True)

    # Shuffle
    df = df.sample(frac=1, random_state=44).reset_index(drop=True)

    return df


def add_raw_defects_t3_follower(df_clean):
    """Add simulated defects to T3 follower raw data."""
    df = df_clean.copy()
    n = len(df)

    # Add a few extra rows (duplicate IDs)
    n_dupes = np.random.randint(3, 6)
    dupe_indices = np.random.choice(n, n_dupes, replace=False)
    dupes = df.iloc[dupe_indices].copy()
    df = pd.concat([df, dupes], ignore_index=True)

    # Shuffle
    df = df.sample(frac=1, random_state=45).reset_index(drop=True)

    return df


def compute_parcels(df, prefix=''):
    """Compute theoretical parcels from item-level data."""
    p = prefix

    # Empowering Leadership Parcels
    if f'{p}EMP1' in df.columns:
        df[f'{p}EMPP1'] = df[[f'{p}EMP1', f'{p}EMP2', f'{p}EMP3']].mean(axis=1)
        df[f'{p}EMPP2'] = df[[f'{p}EMP4', f'{p}EMP5', f'{p}EMP6']].mean(axis=1)
        df[f'{p}EMPP3'] = df[[f'{p}EMP7', f'{p}EMP8', f'{p}EMP9']].mean(axis=1)
        df[f'{p}EMPP4'] = df[[f'{p}EMP10', f'{p}EMP11', f'{p}EMP12']].mean(axis=1)

    # Thriving Parcels - check for T3 prefix variants
    thr_prefix = f'{p}T3_' if f'{p}T3_THR1' in df.columns else p
    r_thr5_col = f'{thr_prefix}R_THR5' if f'{thr_prefix}R_THR5' in df.columns else f'{p}R_THR5'
    r_thr10_col = f'{thr_prefix}R_THR10' if f'{thr_prefix}R_THR10' in df.columns else f'{p}R_THR10'

    if f'{thr_prefix}THR1' in df.columns and r_thr5_col in df.columns:
        df[f'{p}THRP1'] = df[[f'{thr_prefix}THR1', f'{thr_prefix}THR3', r_thr5_col]].mean(axis=1)
        df[f'{p}THRP2'] = df[[f'{thr_prefix}THR2', f'{thr_prefix}THR4']].mean(axis=1)
        df[f'{p}THRP3'] = df[[f'{thr_prefix}THR6', f'{thr_prefix}THR8', r_thr10_col]].mean(axis=1)
        df[f'{p}THRP4'] = df[[f'{thr_prefix}THR7', f'{thr_prefix}THR9']].mean(axis=1)

    return df


def compute_scale_scores(df, prefix=''):
    """Compute composite scale scores (means) for each construct."""
    p = prefix

    # Autocratic leadership mean
    aut_cols = [f'{p}AUT{i}' for i in range(1, 7) if f'{p}AUT{i}' in df.columns]
    if aut_cols:
        df[f'{p}Autocratic'] = df[aut_cols].mean(axis=1)

    # Empowering leadership mean (from parcels or items)
    emp_parcel_cols = [f'{p}EMPP{i}' for i in range(1, 5) if f'{p}EMPP{i}' in df.columns]
    if emp_parcel_cols:
        df[f'{p}Empowering'] = df[emp_parcel_cols].mean(axis=1)

    # Benign envy
    ben_cols = [f'{p}BEN{i}' for i in range(1, 6) if f'{p}BEN{i}' in df.columns]
    if ben_cols:
        df[f'{p}BenignEnvy'] = df[ben_cols].mean(axis=1)

    # Malicious envy
    mal_cols = [f'{p}MAL{i}' for i in range(1, 6) if f'{p}MAL{i}' in df.columns]
    if mal_cols:
        df[f'{p}MaliciousEnvy'] = df[mal_cols].mean(axis=1)

    # Thriving
    thr_parcel_cols = [f'{p}THRP{i}' for i in range(1, 5) if f'{p}THRP{i}' in df.columns]
    if thr_parcel_cols:
        df[f'{p}Thriving'] = df[thr_parcel_cols].mean(axis=1)

    # Narcissism
    narc_cols = [f'{p}NARC{i}' for i in range(1, 7) if f'{p}NARC{i}' in df.columns]
    if narc_cols:
        df[f'{p}Narcissism'] = df[narc_cols].mean(axis=1)

    # Power Distance
    pd_cols = [f'{p}PD{i}' for i in range(1, 7) if f'{p}PD{i}' in df.columns]
    if pd_cols:
        df[f'{p}PowerDistance'] = df[pd_cols].mean(axis=1)

    return df


def apply_grand_mean_centering(df):
    """Apply grand-mean centering to appropriate variables. Add _C suffix."""
    vars_to_center = [
        'Autocratic', 'Empowering', 'Narcissism', 'PowerDistance',
        'FollowerAge', 'TenureWithLeader', 'InteractionFreq', 'T1_Thriving', 'WorkingYears'
    ]

    for var in vars_to_center:
        if var in df.columns:
            grand_mean = df[var].mean()
            df[f'{var}_C'] = df[var] - grand_mean

    return df


def create_dummy_variables(df):
    """Create dummy variables for categorical predictors."""
    # Gender dummy (reference: male=1)
    if 'FollowerGender' in df.columns:
        df['Gender_Female'] = (df['FollowerGender'] == 2).astype(int)

    # Education dummies (reference: bachelor=3)
    if 'FollowerEducation' in df.columns:
        df['Edu_HighSchool'] = (df['FollowerEducation'] == 1).astype(int)
        df['Edu_Associate'] = (df['FollowerEducation'] == 2).astype(int)
        df['Edu_Master'] = (df['FollowerEducation'] == 4).astype(int)
        df['Edu_Doctoral'] = (df['FollowerEducation'] == 5).astype(int)

    return df


def create_clid(df):
    """Create numeric CLID from LeaderID for Mplus."""
    unique_leaders = sorted(df['LeaderID'].unique())
    leader_to_clid = {lid: i + 1 for i, lid in enumerate(unique_leaders)}
    df['CLID'] = df['LeaderID'].map(leader_to_clid)
    return df


def generate_all_data():
    """Main function: generate all wave data and produce output files."""
    print("=" * 60)
    print("LEADERSHIP SURVEY DATA GENERATOR")
    print("=" * 60)

    # --- COORDINATED ATTRITION DESIGN ---
    # Work backwards: T3 defines the 438 final followers, T2 and T1 are supersets.
    # This ensures all T3 followers exist in T2 and T1 (no fake IDs needed).
    print("\n[Step 1] Designing coordinated attrition structure...")

    np.random.seed(42)
    n_leaders_t1 = 90
    target_t1 = 449
    target_t2 = 444
    target_t3 = 438
    n_leaders_t2 = 85
    n_leaders_t3 = 79

    all_leader_ids = [f"L{i+1:03d}" for i in range(n_leaders_t1)]

    # Decide which leaders drop at each wave
    np.random.seed(50)
    t2_drop_leaders = list(np.random.choice(all_leader_ids, 5, replace=False))
    t2_keep_leaders = sorted([l for l in all_leader_ids if l not in t2_drop_leaders])

    np.random.seed(200)
    t3_drop_leaders = list(np.random.choice(t2_keep_leaders, 6, replace=False))
    t3_keep_leaders = sorted([l for l in t2_keep_leaders if l not in t3_drop_leaders])

    assert len(t2_keep_leaders) == 85
    assert len(t3_keep_leaders) == 79

    # T3 allocation: 438 followers across 79 leaders (5 or 6 each)
    np.random.seed(300)
    base_t3 = target_t3 // n_leaders_t3  # 5
    extra_t3 = target_t3 - n_leaders_t3 * base_t3  # 43
    t3_alloc = np.full(n_leaders_t3, base_t3)
    extra_idx = np.random.choice(n_leaders_t3, extra_t3, replace=False)
    for idx in extra_idx:
        t3_alloc[idx] += 1
    t3_leader_alloc = dict(zip(t3_keep_leaders, t3_alloc))

    # T2 allocation: T3-keep leaders get same as T3, T3-drop leaders get remainder
    # T2 total = 444, T3-keep contribute 438, T3-drop leaders get 444-438=6 across 6 leaders
    t2_t3drop_total = target_t2 - target_t3  # 6
    t2_leader_alloc = {}
    for lid in t3_keep_leaders:
        t2_leader_alloc[lid] = t3_leader_alloc[lid]
    for i, lid in enumerate(sorted(t3_drop_leaders)):
        t2_leader_alloc[lid] = 1  # each gets 1

    assert sum(t2_leader_alloc.values()) == target_t2

    # T1 allocation: T2-keep leaders get same as T2, T2-drop leaders get remainder
    # T1 total = 449, T2-keep contribute 444, T2-drop leaders get 449-444=5 across 5 leaders
    t1_leader_alloc = {}
    for lid in t2_keep_leaders:
        t1_leader_alloc[lid] = t2_leader_alloc[lid]
    for i, lid in enumerate(sorted(t2_drop_leaders)):
        t1_leader_alloc[lid] = 1  # each gets 1

    assert sum(t1_leader_alloc.values()) == target_t1

    print(f"  Attrition plan: T1={target_t1}, T2={target_t2}, T3={target_t3}")
    print(f"  Leaders: T1={n_leaders_t1}, T2={n_leaders_t2}, T3={n_leaders_t3}")
    print(f"  T3-keep leaders: {n_leaders_t3} × [5,6] = {target_t3}")
    print(f"  T3-drop in T2: {len(t3_drop_leaders)} × 1 = {t2_t3drop_total}")
    print(f"  T2-drop in T1: {len(t2_drop_leaders)} × 1 = {target_t1 - target_t2}")

    # --- STEP 2: Generate T1 cleaned data ---
    print("\n[Step 2] Generating T1 data...")

    # Build T1 follower IDs (deterministic, all followers get unique IDs)
    t1_leaders_list = []
    t1_followers_list = []
    fid_counter = 1
    for lid in all_leader_ids:
        n_subs = t1_leader_alloc[lid]
        for _ in range(n_subs):
            t1_leaders_list.append(lid)
            t1_followers_list.append(f"F{fid_counter:04d}")
            fid_counter += 1

    t1_leaders_all = np.array(t1_leaders_list)
    t1_followers_all = np.array(t1_followers_list)

    assert len(t1_leaders_all) == target_t1
    assert len(np.unique(t1_leaders_all)) == n_leaders_t1
    print(f"  T1 structure: {len(t1_leaders_all)} followers under {n_leaders_t1} leaders")

    t1_df = generate_t1_data(t1_leaders_all, t1_followers_all)
    t1_df = compute_parcels(t1_df)
    t1_df = compute_scale_scores(t1_df)

    print(f"  T1 cleaned: {len(t1_df)} rows, {t1_df['LeaderID'].nunique()} leaders")

    # --- STEP 3: Build T2 as subset of T1 followers ---
    print("\n[Step 3] Building T2 data (subset of T1 followers)...")

    t2_leaders_list = []
    t2_followers_list = []
    for lid in sorted(t2_keep_leaders):
        t1_fids_for_leader = t1_followers_all[t1_leaders_all == lid]
        n_needed = t2_leader_alloc[lid]
        fids_to_use = t1_fids_for_leader[:n_needed]
        for fid in fids_to_use:
            t2_leaders_list.append(lid)
            t2_followers_list.append(fid)

    t2_leaders = np.array(t2_leaders_list)
    t2_followers = np.array(t2_followers_list)

    assert len(t2_leaders) == target_t2, f"T2 should have {target_t2} rows, got {len(t2_leaders)}"
    assert len(np.unique(t2_leaders)) == n_leaders_t2

    t2_df = generate_t2_data(t2_leaders, t2_followers)
    print(f"  T2 cleaned: {len(t2_df)} rows, {t2_df['LeaderID'].nunique()} leaders")

    # --- STEP 4: Build T3 as subset of T2 followers ---
    print("\n[Step 4] Building T3 data (subset of T2 followers)...")

    t3_leaders_list = []
    t3_followers_list = []
    for lid in sorted(t3_keep_leaders):
        t2_fids_for_leader = t2_followers[t2_leaders == lid]
        n_needed = t3_leader_alloc[lid]
        fids_to_use = t2_fids_for_leader[:n_needed]
        for fid in fids_to_use:
            t3_leaders_list.append(lid)
            t3_followers_list.append(fid)

    t3_leaders = np.array(t3_leaders_list)
    t3_followers = np.array(t3_followers_list)

    assert len(t3_leaders) == 438, f"T3 should have 438 rows, got {len(t3_leaders)}"
    assert len(np.unique(t3_leaders)) == 79, f"T3 should have 79 leaders, got {len(np.unique(t3_leaders))}"

    # T3 follower data
    t3_follower_df = generate_t3_follower_data(t3_leaders, t3_followers)
    print(f"  T3 follower cleaned: {len(t3_follower_df)} rows, {t3_follower_df['LeaderID'].nunique()} leaders")

    # T3 leader data (one row per leader)
    t3_unique_leaders = np.unique(t3_leaders)
    t3_leader_df = generate_t3_leader_data(t3_unique_leaders)
    print(f"  T3 leader cleaned: {len(t3_leader_df)} rows")

    # --- STEP 5: Create raw data with defects ---
    print("\n[Step 5] Adding defects to create raw data...")
    t1_raw = add_raw_defects_t1(t1_df)
    t2_raw = add_raw_defects_t2(t2_df)
    t3_leader_raw = add_raw_defects_t3_leader(t3_leader_df)
    t3_follower_raw = add_raw_defects_t3_follower(t3_follower_df)

    print(f"  T1 raw: {len(t1_raw)} rows (cleaned: {len(t1_df)})")
    print(f"  T2 raw: {len(t2_raw)} rows (cleaned: {len(t2_df)})")
    print(f"  T3 leader raw: {len(t3_leader_raw)} rows (cleaned: {len(t3_leader_df)})")
    print(f"  T3 follower raw: {len(t3_follower_raw)} rows (cleaned: {len(t3_follower_df)})")

    # --- STEP 6: Create final merged analysis dataset ---
    print("\n[Step 6] Creating final merged analysis dataset...")

    # Merge T1, T2, T3 follower data on FollowerID
    # T1 contributes: leadership, thriving T1, narcissism, power distance, demographics
    t1_for_merge = t1_df.copy()
    # Rename T1 thriving to T1_Thriving
    if 'Thriving' in t1_for_merge.columns:
        t1_for_merge.rename(columns={'Thriving': 'T1_Thriving'}, inplace=True)

    # T2 contributes: envy measures
    t2_for_merge = t2_df[['FollowerID', 'LeaderID'] +
                         [c for c in t2_df.columns if c.startswith('BEN') or c.startswith('MAL')]].copy()
    # Remove attention check from merge
    if 'MAL6_AttCheck' in t2_for_merge.columns:
        t2_for_merge.drop(columns=['MAL6_AttCheck'], inplace=True)

    # T3 follower contributes: T3 thriving, OCBS, CWBS
    t3f_for_merge = t3_follower_df.copy()
    if 'OCBS7_AttCheck' in t3f_for_merge.columns:
        t3f_for_merge.drop(columns=['OCBS7_AttCheck'], inplace=True)

    # Merge on FollowerID (all T3 followers exist in T1 and T2 by construction)
    final_df = t3f_for_merge.merge(
        t1_for_merge.drop(columns=['LeaderID'], errors='ignore'),
        on='FollowerID', how='inner'
    )
    final_df = final_df.merge(
        t2_for_merge.drop(columns=['LeaderID'], errors='ignore'),
        on='FollowerID', how='inner'
    )

    # Merge leader-rated data
    t3l_for_merge = t3_leader_df.copy()
    if 'CWBS6_AttCheck' in t3l_for_merge.columns:
        t3l_for_merge.drop(columns=['CWBS6_AttCheck'], inplace=True)
    final_df = final_df.merge(t3l_for_merge, on='LeaderID', how='left')

    # Compute T3 thriving parcels
    # T3 thriving items have T3_ prefix
    if 'T3_THR1' in final_df.columns:
        final_df['T3_THRP1'] = final_df[['T3_THR1', 'T3_THR3', 'T3_R_THR5']].mean(axis=1)
        final_df['T3_THRP2'] = final_df[['T3_THR2', 'T3_THR4']].mean(axis=1)
        final_df['T3_THRP3'] = final_df[['T3_THR6', 'T3_THR8', 'T3_R_THR10']].mean(axis=1)
        final_df['T3_THRP4'] = final_df[['T3_THR7', 'T3_THR9']].mean(axis=1)
        final_df['T3_Thriving'] = final_df[['T3_THRP1', 'T3_THRP2', 'T3_THRP3', 'T3_THRP4']].mean(axis=1)

    # Compute OCBS and CWBS scale scores
    ocbs_l_cols = [f'OCBS_L{i}' for i in range(1, 9) if f'OCBS_L{i}' in final_df.columns]
    if ocbs_l_cols:
        final_df['OCBS_Leader'] = final_df[ocbs_l_cols].mean(axis=1)

    cwbs_cols = [f'CWBS{i}' for i in range(1, 8) if f'CWBS{i}' in final_df.columns]
    if cwbs_cols:
        final_df['CWBS_Leader'] = final_df[cwbs_cols].mean(axis=1)

    # Follower-rated versions for Model 3
    ocbs_self_cols = [f'OCBS_Self{i}' for i in range(1, 9) if f'OCBS_Self{i}' in final_df.columns]
    if ocbs_self_cols:
        final_df['OCBS_Follower'] = final_df[ocbs_self_cols].mean(axis=1)

    cwbs_f_cols = [f'CWBS_F{i}' for i in range(1, 8) if f'CWBS_F{i}' in final_df.columns]
    if cwbs_f_cols:
        final_df['CWBS_Follower'] = final_df[cwbs_f_cols].mean(axis=1)

    # Compute BenignEnvy and MaliciousEnvy composites (from T2 items)
    ben_cols = [f'BEN{i}' for i in range(1, 6) if f'BEN{i}' in final_df.columns]
    if ben_cols:
        final_df['BenignEnvy'] = final_df[ben_cols].mean(axis=1)

    mal_cols = [f'MAL{i}' for i in range(1, 6) if f'MAL{i}' in final_df.columns]
    if mal_cols:
        final_df['MaliciousEnvy'] = final_df[mal_cols].mean(axis=1)

    # Ensure LeaderEducation is complete (leader-level attribute, fill from leader map)
    np.random.seed(99)
    unique_final_leaders = sorted(final_df['LeaderID'].unique())
    leader_edu_map = {}
    for lid in unique_final_leaders:
        existing = final_df.loc[final_df['LeaderID'] == lid, 'LeaderEducation'].dropna()
        if len(existing) > 0:
            leader_edu_map[lid] = int(existing.iloc[0])
        else:
            leader_edu_map[lid] = int(np.random.choice([2, 3, 4, 5], p=[0.10, 0.35, 0.40, 0.15]))
    final_df['LeaderEducation'] = final_df['LeaderID'].map(leader_edu_map)

    # Create CLID
    final_df = create_clid(final_df)

    # Create dummy variables
    final_df = create_dummy_variables(final_df)

    # Apply grand-mean centering
    final_df = apply_grand_mean_centering(final_df)

    # Verify CLID range
    assert final_df['CLID'].min() == 1
    assert final_df['CLID'].max() == 79

    print(f"  Final merged: {len(final_df)} rows, {final_df['LeaderID'].nunique()} leaders")
    print(f"  CLID range: {final_df['CLID'].min()} - {final_df['CLID'].max()}")

    # --- STEP 7: Save all files ---
    print("\n[Step 7] Saving output files...")

    t1_raw.to_excel(OUTPUT_DIR / 'T1_raw.xlsx', index=False)
    print(f"  Saved T1_raw.xlsx ({len(t1_raw)} rows)")

    t1_df.to_excel(OUTPUT_DIR / 'T1_cleaned.xlsx', index=False)
    print(f"  Saved T1_cleaned.xlsx ({len(t1_df)} rows)")

    t2_raw.to_excel(OUTPUT_DIR / 'T2_raw.xlsx', index=False)
    print(f"  Saved T2_raw.xlsx ({len(t2_raw)} rows)")

    t2_df.to_excel(OUTPUT_DIR / 'T2_cleaned.xlsx', index=False)
    print(f"  Saved T2_cleaned.xlsx ({len(t2_df)} rows)")

    t3_leader_raw.to_excel(OUTPUT_DIR / 'T3_leader_raw.xlsx', index=False)
    print(f"  Saved T3_leader_raw.xlsx ({len(t3_leader_raw)} rows)")

    t3_leader_df.to_excel(OUTPUT_DIR / 'T3_leader_cleaned.xlsx', index=False)
    print(f"  Saved T3_leader_cleaned.xlsx ({len(t3_leader_df)} rows)")

    t3_follower_raw.to_excel(OUTPUT_DIR / 'T3_follower_raw.xlsx', index=False)
    print(f"  Saved T3_follower_raw.xlsx ({len(t3_follower_raw)} rows)")

    t3_follower_df.to_excel(OUTPUT_DIR / 'T3_follower_cleaned.xlsx', index=False)
    print(f"  Saved T3_follower_cleaned.xlsx ({len(t3_follower_df)} rows)")

    final_df.to_excel(OUTPUT_DIR / 'final_merged_analysis_data.xlsx', index=False)
    print(f"  Saved final_merged_analysis_data.xlsx ({len(final_df)} rows)")

    # Generate Mplus data file (study3_mcfa.dat)
    mcfa_vars = ['CLID'] + [f'AUT{i}' for i in range(1, 7)] + \
                [f'EMPP{i}' for i in range(1, 5)] + \
                [f'BEN{i}' for i in range(1, 6)] + \
                [f'MAL{i}' for i in range(1, 6)] + \
                [f'THRP{i}' for i in range(1, 5)]
    mcfa_df = final_df[mcfa_vars].copy()
    mcfa_df = mcfa_df.fillna(-999)
    mcfa_df.to_csv(OUTPUT_DIR / 'study3_mcfa.dat', sep='\t', header=False, index=False)
    print(f"  Saved study3_mcfa.dat ({len(mcfa_df)} rows, {len(mcfa_vars)} vars)")

    print("\n" + "=" * 60)
    print("DATA GENERATION COMPLETE")
    print("=" * 60)

    return {
        't1_raw': t1_raw, 't1_cleaned': t1_df,
        't2_raw': t2_raw, 't2_cleaned': t2_df,
        't3_leader_raw': t3_leader_raw, 't3_leader_cleaned': t3_leader_df,
        't3_follower_raw': t3_follower_raw, 't3_follower_cleaned': t3_follower_df,
        'final_merged': final_df,
    }


if __name__ == '__main__':
    generate_all_data()
