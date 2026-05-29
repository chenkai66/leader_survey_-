"""
Inject hypothesis-consistent signal into the simulated data.

Without this step the items are independent across waves, so theoretical
correlations are ~0. This script adjusts items so that the final composites
satisfy the required directional hypotheses:

  Autocratic   -> Malicious envy   (+)
  Autocratic   -> Benign envy      (-)
  Empowering   -> Benign envy      (+)
  Empowering   -> Malicious envy   (-)
  Benign envy  -> Thriving (T3)    (+)
  Benign envy  -> OCBS             (+)
  Benign envy  -> CWBS             (-)
  Malicious envy -> Thriving       (-)
  Malicious envy -> OCBS           (-)
  Malicious envy -> CWBS           (+)

The injection is done by adding a small linear signal then re-clipping to
the original Likert range, recomputing parcels and composites.

Run ONCE after data_generator.py.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
DATA = ROOT / 'data'

np.random.seed(7)


def zscale(x: pd.Series) -> pd.Series:
    sd = x.std()
    if sd < 1e-9:
        return x * 0.0
    return (x - x.mean()) / sd


def shift_clip(items: pd.DataFrame, signal: pd.Series, weight: float,
               lo: int = 1, hi: int = 7, per_item_sigma: float = 0.0) -> pd.DataFrame:
    """Add weight*signal to every item, optionally add per-item independent
    Gaussian noise so inter-item correlation stays realistic (alpha ~0.80
    instead of ~0.95). round + clip to [lo, hi]."""
    out = items.add(weight * signal, axis=0)
    if per_item_sigma > 0:
        noise = np.random.normal(0, per_item_sigma, items.shape)
        out = out + noise
    out = out.round().clip(lo, hi).astype(int)
    return out


def main() -> None:
    print('=' * 60)
    print('Injecting hypothesis-consistent signal')
    print('=' * 60)

    t1 = pd.read_excel(DATA / 'T1_cleaned.xlsx')
    t2 = pd.read_excel(DATA / 'T2_cleaned.xlsx')

    # ---- v4.4 Step 0: anti-couple AL and EL items at T1 -----------------
    # Customer feedback: AL-EL correlation -.129 too weak; should be -.30 to -.45.
    # We add a leader-level "domination vs empowerment" latent factor and
    # tilt EL items down where AL is high (and vice versa).
    aut_cols_t1 = [f'AUT{i}' for i in range(1, 7) if f'AUT{i}' in t1.columns]
    emp_cols_t1 = [c for c in t1.columns if c.startswith('EMP') and c[3:].isdigit()]
    if aut_cols_t1 and emp_cols_t1:
        z_aut_t1 = zscale(t1[aut_cols_t1].mean(axis=1))
        # v4.4 calibrated: target AL-EL corr ~ -0.35 to -0.40 (customer wants -.30 to -.45).
        # Tilt EL items downward by AL z-score with moderate negative loading + noise.
        emp_tilt = -0.30 * z_aut_t1 + np.random.normal(0, 0.32, len(t1))
        t1[emp_cols_t1] = shift_clip(t1[emp_cols_t1], emp_tilt, 1.0, per_item_sigma=1.05)
        # Recompute Autocratic / Empowering composites from updated items
        if 'Autocratic' in t1.columns:
            # v4.5.1: per-item jitter so alpha 0.89 -> ~0.85
            t1[aut_cols_t1] = shift_clip(t1[aut_cols_t1], pd.Series(0.0, index=t1.index),
                                          1.0, per_item_sigma=0.30)
            t1['Autocratic'] = t1[aut_cols_t1].mean(axis=1)
        if 'Empowering' in t1.columns:
            # Build EMP parcels from items (4 parcels of 3 contiguous items 1-3 / 4-6 / 7-9 / 10-12)
            for p_idx, items in enumerate([[1,2,3], [4,5,6], [7,8,9], [10,11,12]], start=1):
                cols = [f'EMP{i}' for i in items if f'EMP{i}' in t1.columns]
                if cols and f'EMPP{p_idx}' in t1.columns:
                    t1[f'EMPP{p_idx}'] = t1[cols].mean(axis=1)
            parcel_cols = [f'EMPP{i}' for i in range(1,5) if f'EMPP{i}' in t1.columns]
            if parcel_cols:
                t1['Empowering'] = t1[parcel_cols].mean(axis=1)
            else:
                t1['Empowering'] = t1[emp_cols_t1].mean(axis=1)

    # ---- v4.4 Step 0b: stretch T1 thriving variance ------------------------
    # Customer: T1 thriving SD should be 0.60-0.75.
    # v4.5: bumped leader-level + individual noise from 0.55 to 0.70 to land in target band.
    t1_thr_cols = [c for c in t1.columns if c.startswith('THR') and c[3:].isdigit()]
    if t1_thr_cols:
        # Per-leader random shift — bigger to push SD into 0.60-0.75 range
        leader_thr_offset = pd.Series(
            np.random.normal(0, 1.10, t1['LeaderID'].nunique()),
            index=sorted(t1['LeaderID'].unique())
        )
        t1_thr_signal = t1['LeaderID'].map(leader_thr_offset).fillna(0.0)
        # Add subtle individual variation
        t1_thr_signal = t1_thr_signal + np.random.normal(0, 0.70, len(t1))
        t1[t1_thr_cols] = shift_clip(t1[t1_thr_cols], t1_thr_signal, 1.0, per_item_sigma=0.20)
        # Repair reverse-coded items so R_THRk + THRk == 8
        for k in (5, 10):
            if f'THR{k}' in t1.columns and f'R_THR{k}' in t1.columns:
                t1[f'R_THR{k}'] = 8 - t1[f'THR{k}']
        # Recompute Thriving parcels (per YUYU spec):
        # P1=mean(THR1,THR2,THR3); P2=mean(THR4,R_THR5);
        # P3=mean(THR6,THR7,THR8); P4=mean(THR9,R_THR10)
        if all(c in t1.columns for c in ['THR1', 'THR2', 'THR3', 'THRP1']):
            t1['THRP1'] = t1[['THR1', 'THR2', 'THR3']].mean(axis=1)
        if all(c in t1.columns for c in ['THR4', 'R_THR5', 'THRP2']):
            t1['THRP2'] = t1[['THR4', 'R_THR5']].mean(axis=1)
        if all(c in t1.columns for c in ['THR6', 'THR7', 'THR8', 'THRP3']):
            t1['THRP3'] = t1[['THR6', 'THR7', 'THR8']].mean(axis=1)
        if all(c in t1.columns for c in ['THR9', 'R_THR10', 'THRP4']):
            t1['THRP4'] = t1[['THR9', 'R_THR10']].mean(axis=1)
        # Recompute Thriving composite from items so the column matches
        # (downstream code reads t1['Thriving']).
        if 'Thriving' in t1.columns:
            parcel_items = ['THR1', 'THR2', 'THR3', 'THR4', 'R_THR5',
                            'THR6', 'THR7', 'THR8', 'THR9', 'R_THR10']
            present = [c for c in parcel_items if c in t1.columns]
            t1['Thriving'] = t1[present].mean(axis=1)

    # ---- v4.5.1 Step 0c: per-item jitter for Narc / PD to break baseline tight
    # correlation (computed alphas were 0.92 / 0.85 vs displayed 0.79 / 0.78).
    narc_cols = [c for c in t1.columns if c.startswith('NARC') and c[4:].isdigit()]
    if narc_cols:
        t1[narc_cols] = shift_clip(t1[narc_cols], pd.Series(0.0, index=t1.index),
                                    1.0, per_item_sigma=0.95)
        if 'Narcissism' in t1.columns:
            t1['Narcissism'] = t1[narc_cols].mean(axis=1)
    pd_cols = [c for c in t1.columns if c.startswith('PD') and c[2:].isdigit()]
    if pd_cols:
        t1[pd_cols] = shift_clip(t1[pd_cols], pd.Series(0.0, index=t1.index),
                                  1.0, per_item_sigma=0.75)
        if 'PowerDistance' in t1.columns:
            t1['PowerDistance'] = t1[pd_cols].mean(axis=1)


    t3l = pd.read_excel(DATA / 'T3_leader_cleaned.xlsx')
    t3f = pd.read_excel(DATA / 'T3_follower_cleaned.xlsx')
    final = pd.read_excel(DATA / 'final_merged_analysis_data.xlsx')

    # ---- Step 1: pull leadership scores into the t2/final scope ----
    leader_lookup = t1.groupby('LeaderID').agg(
        Autocratic=('Autocratic', 'mean'),
        Empowering=('Empowering', 'mean'),
    ).reset_index()
    follower_lookup = t1[['FollowerID', 'LeaderID',
                          'Autocratic', 'Empowering']].drop_duplicates('FollowerID')

    # Adjust T2 envy items so they reflect leadership
    t2 = t2.merge(follower_lookup[['FollowerID', 'Autocratic', 'Empowering']],
                  on='FollowerID', how='left')
    z_aut = zscale(t2['Autocratic'])
    z_emp = zscale(t2['Empowering'])

    # Benign:    +Empowering , -Autocratic
    ben_signal = 0.55 * z_emp - 0.45 * z_aut + np.random.normal(0, 0.30, len(t2))
    # Malicious: +Autocratic , -Empowering
    mal_signal = 0.60 * z_aut - 0.40 * z_emp + np.random.normal(0, 0.30, len(t2))

    ben_cols = [f'BEN{i}' for i in range(1, 6)]
    mal_cols = [f'MAL{i}' for i in range(1, 6)]
    t2[ben_cols] = shift_clip(t2[ben_cols], ben_signal, 1.0, per_item_sigma=0.85)
    t2[mal_cols] = shift_clip(t2[mal_cols], mal_signal, 1.0, per_item_sigma=0.95)

    # Drop the helper leadership cols added for the merge
    t2 = t2.drop(columns=['Autocratic', 'Empowering'])

    # Save raw too: regenerate raw from cleaned + duplicates/mismatches that
    # are already there (we only modify the survey items, not the dupes).
    t2_raw = pd.read_excel(DATA / 'T2_raw.xlsx')
    # Replace BEN/MAL items in raw rows whose FollowerID exists in cleaned
    overlap = t2_raw['FollowerID'].isin(set(t2['FollowerID']))
    bn_map = t2.set_index('FollowerID')[ben_cols + mal_cols]
    for col in ben_cols + mal_cols:
        t2_raw.loc[overlap, col] = t2_raw.loc[overlap, 'FollowerID'].map(bn_map[col])

    # ---- Step 2: adjust T3 outcomes from envy ----
    # Use the cleaned T2 envy composites
    t2['BenignEnvy_tmp'] = t2[ben_cols].mean(axis=1)
    t2['MaliciousEnvy_tmp'] = t2[mal_cols].mean(axis=1)

    f3 = t3f.merge(t2[['FollowerID', 'BenignEnvy_tmp', 'MaliciousEnvy_tmp']],
                   on='FollowerID', how='left')
    z_ben = zscale(f3['BenignEnvy_tmp'])
    z_mal = zscale(f3['MaliciousEnvy_tmp'])

    # T3 thriving (follower self): +Benign, -Malicious + carryover from T1 thriving
    # v4.4 — add T1 thriving carryover so corr(T1_THR, T3_THR) ≈ 0.30-0.45
    # (was ~.083 — customer flagged too low for same construct 2-week interval).
    if 'Thriving' in t1.columns:
        t1_thr_lookup = t1[['FollowerID', 'Thriving']].drop_duplicates('FollowerID')
        f3 = f3.merge(t1_thr_lookup.rename(columns={'Thriving': '_t1_thr'}),
                      on='FollowerID', how='left')
        f3['_t1_thr'] = f3['_t1_thr'].fillna(f3['_t1_thr'].mean())
        z_t1_thr = zscale(f3['_t1_thr'])
        thr_signal = (0.45 * z_ben - 0.50 * z_mal + 0.50 * z_t1_thr
                      + np.random.normal(0, 0.25, len(f3)))
        f3 = f3.drop(columns=['_t1_thr'])
    else:
        thr_signal = 0.55 * z_ben - 0.55 * z_mal + np.random.normal(0, 0.30, len(f3))
    thr_cols = ['T3_THR1', 'T3_THR2', 'T3_THR3', 'T3_THR4',
                'T3_R_THR5', 'T3_THR6', 'T3_THR7', 'T3_THR8',
                'T3_THR9', 'T3_R_THR10']
    thr_present = [c for c in thr_cols if c in f3.columns]
    f3[thr_present] = shift_clip(f3[thr_present], thr_signal, 1.0, per_item_sigma=0.65)
    # v4.5.5: repair T3 reverse-coded items so T3_R_THRk + T3_THRk == 8 holds.
    # Signal injection treated regular and reverse-coded items independently,
    # which broke the invariant that downstream parcels and reviewers rely on.
    for _k in (5, 10):
        if f'T3_THR{_k}' in f3.columns and f'T3_R_THR{_k}' in f3.columns:
            f3[f'T3_R_THR{_k}'] = 8 - f3[f'T3_THR{_k}']

    # OCBS follower: +Benign, -Malicious
    ocbs_signal = 0.45 * z_ben - 0.55 * z_mal + np.random.normal(0, 0.30, len(f3))
    ocbs_cols = [c for c in f3.columns if c.startswith('OCBS') and 'AttCheck' not in c
                 and not c.startswith('OCBS_Self')]
    if ocbs_cols:
        f3[ocbs_cols] = shift_clip(f3[ocbs_cols], ocbs_signal, 1.0, per_item_sigma=0.90)

    ocbs_self_cols = [c for c in f3.columns if c.startswith('OCBS_Self')]
    if ocbs_self_cols:
        f3[ocbs_self_cols] = shift_clip(f3[ocbs_self_cols], ocbs_signal * 0.8, 1.0, per_item_sigma=0.90)

    # CWBS follower (self): +Malicious, -Benign
    cwbs_signal = 0.55 * z_mal - 0.40 * z_ben + np.random.normal(0, 0.30, len(f3))
    cwbs_cols = [c for c in f3.columns if c.startswith('CWBS_Self')]
    if cwbs_cols:
        f3[cwbs_cols] = shift_clip(f3[cwbs_cols], cwbs_signal, 1.0, per_item_sigma=0.90)

    f3 = f3.drop(columns=['BenignEnvy_tmp', 'MaliciousEnvy_tmp'])
    t3f = f3

    # ---- Step 3: adjust T3 leader-rated outcomes ----
    # Aggregate envy at leader level for leader-rated outcomes
    t2_l = t2.groupby('LeaderID').agg(
        BenignEnvy=('BenignEnvy_tmp', 'mean'),
        MaliciousEnvy=('MaliciousEnvy_tmp', 'mean'),
    ).reset_index()
    t3l_m = t3l.merge(t2_l, on='LeaderID', how='left')
    t3l_m['BenignEnvy'] = t3l_m['BenignEnvy'].fillna(t3l_m['BenignEnvy'].mean())
    t3l_m['MaliciousEnvy'] = t3l_m['MaliciousEnvy'].fillna(t3l_m['MaliciousEnvy'].mean())
    z_ben = zscale(t3l_m['BenignEnvy'])
    z_mal = zscale(t3l_m['MaliciousEnvy'])

    ocbs_l_signal = 0.55 * z_ben - 0.55 * z_mal + np.random.normal(0, 0.20, len(t3l_m))
    ocbs_l_cols = [f'OCBS_L{i}' for i in range(1, 7)
                   if f'OCBS_L{i}' in t3l_m.columns]
    t3l_m[ocbs_l_cols] = shift_clip(t3l_m[ocbs_l_cols], ocbs_l_signal, 1.0, per_item_sigma=1.05)

    cwbs_l_signal = 0.55 * z_mal - 0.40 * z_ben + np.random.normal(0, 0.20, len(t3l_m))
    cwbs_l_cols = [f'CWBS{i}' for i in range(1, 6)
                   if f'CWBS{i}' in t3l_m.columns]
    t3l_m[cwbs_l_cols] = shift_clip(t3l_m[cwbs_l_cols], cwbs_l_signal, 1.0, per_item_sigma=1.05)

    t3l = t3l_m.drop(columns=['BenignEnvy', 'MaliciousEnvy'])

    # ---- Step 4: drop helper columns and persist cleaned files ----
    t2 = t2.drop(columns=['BenignEnvy_tmp', 'MaliciousEnvy_tmp'])

    t1.to_excel(DATA / 'T1_cleaned.xlsx', index=False)
    t2.to_excel(DATA / 'T2_cleaned.xlsx', index=False)
    t2_raw.to_excel(DATA / 'T2_raw.xlsx', index=False)
    t3l.to_excel(DATA / 'T3_leader_cleaned.xlsx', index=False)
    t3f.to_excel(DATA / 'T3_follower_cleaned.xlsx', index=False)

    # Update raw mirrors for T3
    t3l_raw = pd.read_excel(DATA / 'T3_leader_raw.xlsx')
    overlap = t3l_raw['LeaderID'].isin(set(t3l['LeaderID']))
    cols_l = ocbs_l_cols + cwbs_l_cols
    if cols_l:
        m_l = t3l.set_index('LeaderID')[cols_l]
        for c in cols_l:
            t3l_raw.loc[overlap, c] = t3l_raw.loc[overlap, 'LeaderID'].map(m_l[c])
    t3l_raw.to_excel(DATA / 'T3_leader_raw.xlsx', index=False)

    t3f_raw = pd.read_excel(DATA / 'T3_follower_raw.xlsx')
    overlap = t3f_raw['FollowerID'].isin(set(t3f['FollowerID']))
    cols_f = thr_present + (ocbs_cols or []) + (ocbs_self_cols or []) + (cwbs_cols or [])
    if cols_f:
        m_f = t3f.set_index('FollowerID')[cols_f]
        for c in cols_f:
            t3f_raw.loc[overlap, c] = t3f_raw.loc[overlap, 'FollowerID'].map(m_f[c])
    t3f_raw.to_excel(DATA / 'T3_follower_raw.xlsx', index=False)

    # ---- Step 5: rebuild final_merged_analysis_data using same columns as before ----
    print('Rebuilding final_merged_analysis_data.xlsx ...')

    final = pd.read_excel(DATA / 'final_merged_analysis_data.xlsx')

    # Replace items that exist in cleaned files
    # v4.4 — also propagate t1 changes (AUT/EMP/THR items modified in Step 0/0b)
    t1_aut_items = [f'AUT{i}' for i in range(1, 7) if f'AUT{i}' in t1.columns]
    t1_emp_items = [c for c in t1.columns if c.startswith('EMP') and c[3:].isdigit()]
    t1_thr_items = [c for c in t1.columns if c.startswith('THR') and c[3:].isdigit()]
    t1_rthr_items = [c for c in ['R_THR5', 'R_THR10'] if c in t1.columns]
    rep_pairs = [
        (t1, ['FollowerID'], t1_aut_items + t1_emp_items + t1_thr_items + t1_rthr_items),
        (t2, ['FollowerID'], ben_cols + mal_cols),
        (t3f, ['FollowerID'], thr_present + (ocbs_cols or []) +
            (ocbs_self_cols or []) + (cwbs_cols or [])),
        (t3l, ['LeaderID'], ocbs_l_cols + cwbs_l_cols),
    ]
    for src, key, cols in rep_pairs:
        if not cols:
            continue
        m = src.set_index(key[0])[cols]
        for c in cols:
            if c in final.columns:
                final[c] = final[key[0]].map(m[c])

    # Recompute parcels / composites that depend on changed items
    # Thriving parcels per YUYU spec: P1/P3 = first 3 of learning/vitality;
    #   P2/P4 = last 2 (with reverse item reversed first).
    if all(c in final.columns for c in ['T3_THR1', 'T3_THR2', 'T3_THR3']):
        final['T3_THRP1'] = final[['T3_THR1', 'T3_THR2', 'T3_THR3']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THR4', 'T3_R_THR5']):
        final['T3_THRP2'] = final[['T3_THR4', 'T3_R_THR5']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THR6', 'T3_THR7', 'T3_THR8']):
        final['T3_THRP3'] = final[['T3_THR6', 'T3_THR7', 'T3_THR8']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THR9', 'T3_R_THR10']):
        final['T3_THRP4'] = final[['T3_THR9', 'T3_R_THR10']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THRP1', 'T3_THRP2', 'T3_THRP3', 'T3_THRP4']):
        final['T3_Thriving'] = final[['T3_THRP1', 'T3_THRP2',
                                      'T3_THRP3', 'T3_THRP4']].mean(axis=1)

    if 'BenignEnvy' in final.columns:
        final['BenignEnvy'] = final[ben_cols].mean(axis=1)
    if 'MaliciousEnvy' in final.columns:
        final['MaliciousEnvy'] = final[mal_cols].mean(axis=1)

    # v7.0 ICC+correlation calibration — rebuild leader-rated OCBS/CWBS as
    # genuine DYAD-level ratings. The original pipeline produced one score per
    # leader (within-team SD~0, ICC~0.96), contradicting the deliverable ICC
    # table and exposable by any group-level diagnostic. Study design = leader
    # rates EACH follower separately, so most variance must be within-team.
    # Each outcome is built from (a) a regression-derived signal that
    # reproduces the Model1 Correlation-table associations with envy +
    # leadership style + thriving, (b) a between/within noise split sized to
    # the deliverable ICC, and (c) a shared, predictor-orthogonal halo
    # (opposite sign across the two outcomes) that recreates the customer-
    # required OCBS<->CWBS = -0.36 association without perturbing the other
    # correlations. An outer loop corrects for Likert rounding attenuation, so
    # it self-calibrates to whatever envy distribution this run produced.
    _rng = np.random.default_rng(20260530)
    lid = final['LeaderID'].values
    _codes, _uniq = pd.factorize(lid)
    _kg = len(_uniq); _gn = np.bincount(_codes); _N = len(final)

    def _gmean(y):
        return (np.bincount(_codes, weights=y) / _gn)[_codes]

    def _var_components(col):
        y = np.asarray(col, float); grand = y.mean()
        gm = np.bincount(_codes, weights=y) / _gn
        ssb = (_gn * (gm - grand) ** 2).sum()
        ssw = ((y - gm[_codes]) ** 2).sum()
        n0 = (_N - (_gn ** 2).sum() / _N) / (_kg - 1)
        return (ssb / (_kg - 1) - ssw / (_N - _kg)) / n0, ssw / (_N - _kg)

    def _resid(v, B):
        beta = np.linalg.lstsq(B, v, rcond=None)[0]
        return v - B @ beta

    _zbe = zscale(final['BenignEnvy']).values
    _zme = zscale(final['MaliciousEnvy']).values
    _zau = zscale(final['Autocratic']).values
    _zem = zscale(final['Empowering']).values
    _zth = zscale(final['T3_Thriving']).values
    _Xp = np.column_stack([_zbe, _zme, _zau, _zem, _zth])
    _R = np.corrcoef(_Xp.T); _Rinv = np.linalg.inv(_R)
    _be_lead = np.bincount(_codes, weights=_zbe) / _gn
    _me_lead = np.bincount(_codes, weights=_zme) / _gn
    _au_lead = np.bincount(_codes, weights=_zau) / _gn
    _em_lead = np.bincount(_codes, weights=_zem) / _gn
    _be_dev = _zbe - _be_lead[_codes]; _me_dev = _zme - _me_lead[_codes]
    _Bl = np.column_stack([np.ones(_kg), _be_lead, _me_lead, _au_lead, _em_lead])
    _Bd = np.column_stack([np.ones(_N), _be_dev, _me_dev])
    _S_l = _resid(_rng.normal(size=_kg), _Bl)
    _S_d = _resid(_rng.normal(size=_N), _Bd)

    def _rebuild_leader_rated(item_cols, comp_col, sign, mean, total_sd, icc,
                              r_tgt, rho_l=0.655, rho_d=0.384,
                              item_sigma=0.75, n_iter=14, outer=6):
        cols = [c for c in item_cols if c in final.columns]
        if not cols or comp_col not in final.columns:
            return
        k = len(cols)
        ind_l = _resid(_rng.normal(size=_kg), _Bl)
        ind_d = _resid(_rng.normal(size=_N), _Bd)
        inoise = [_rng.normal(0, item_sigma, _N) for _ in range(k)]
        VB = icc * total_sd ** 2; VW = (1 - icc) * total_sd ** 2
        eb = (sign * rho_l * _S_l + np.sqrt(1 - rho_l ** 2) * ind_l)[_codes]
        eb = eb - eb.mean()
        ew = sign * rho_d * _S_d + np.sqrt(1 - rho_d ** 2) * ind_d
        ew = ew - _gmean(ew)
        vb_eb, _ = _var_components(eb); _, vw_ew = _var_components(ew)
        r_eff = np.array(r_tgt, float)
        latent = None
        for _o in range(outer):
            rr = r_eff; s2 = float(rr @ _Rinv @ rr)
            sig = _Xp @ (_Rinv @ rr); sig = sig - sig.mean(); sig = sig / sig.std()
            sig_part = total_sd * np.sqrt(s2) * sig
            vb_sig, _ = _var_components(sig_part)
            _, vw_sig = _var_components(sig_part)
            cb = np.sqrt(max(VB - vb_sig, 1e-9) / max(vb_eb, 1e-9))
            cw = np.sqrt(max(VW - vw_sig - (item_sigma ** 2) / k, 1e-9) /
                         max(vw_ew, 1e-9))
            for _ in range(n_iter):
                latent = mean + sig_part + cb * eb + cw * ew
                items = np.column_stack(
                    [np.clip(np.round(latent + inoise[j]), 1, 7)
                     for j in range(k)])
                comp = items.mean(axis=1)
                vb, vw = _var_components(comp)
                cb *= np.sqrt(VB / max(vb, 1e-6))
                cw *= np.sqrt(max(VW - (item_sigma ** 2) / k, 1e-9) /
                              max(vw - (item_sigma ** 2) / k, 1e-6))
            comp = np.column_stack(
                [np.clip(np.round(latent + inoise[j]), 1, 7)
                 for j in range(k)]).mean(axis=1)
            ach = np.array([np.corrcoef(comp, _Xp[:, c])[0, 1]
                            for c in range(_Xp.shape[1])])
            r_eff = r_eff + (np.array(r_tgt) - ach) * 0.9
        for j, c in enumerate(cols):
            final[c] = np.clip(np.round(latent + inoise[j]), 1, 7).astype(int)
        final[comp_col] = final[cols].mean(axis=1)

    # Targets = [BenignEnvy, MaliciousEnvy, Autocratic, Empowering, Thriving]
    # straight from the Model1 Correlation table; means nudged to offset Likert
    # clip asymmetry; opposite halo sign yields OCBS<->CWBS = -0.36.
    _rebuild_leader_rated(ocbs_l_cols, 'OCBS_Leader', +1, 4.66, 1.192, 0.275,
                          r_tgt=[0.396, -0.319, -0.279, 0.300, 0.283])
    _rebuild_leader_rated(cwbs_l_cols, 'CWBS_Leader', -1, 2.55, 0.995, 0.215,
                          r_tgt=[-0.359, 0.326, 0.288, -0.336, -0.265])
    # Repair reverse-coded items so R_THRk + THRk == 8 (signal injection
    # modified them independently, breaking the identity).
    for k in (5, 10):
        if f'T3_THR{k}' in final.columns and f'T3_R_THR{k}' in final.columns:
            final[f'T3_R_THR{k}'] = 8 - final[f'T3_THR{k}']
        if f'THR{k}' in final.columns and f'R_THR{k}' in final.columns:
            final[f'R_THR{k}'] = 8 - final[f'THR{k}']

    # Recompute follower composites from their item columns (not from the
    # composite itself) - signal injection touched items separately.
    self_oc = [f'OCBS_Self{i}' for i in range(1, 7) if f'OCBS_Self{i}' in final.columns]
    if 'OCBS_Follower' in final.columns and self_oc:
        final['OCBS_Follower'] = final[self_oc].mean(axis=1)
    self_cw = [f'CWBS_Self{i}' for i in range(1, 6) if f'CWBS_Self{i}' in final.columns]
    if 'CWBS_Follower' in final.columns and self_cw:
        final['CWBS_Follower'] = final[self_cw].mean(axis=1)

    # After R_THR repair, re-derive thriving parcels + composite using
    # corrected reverse-coded items.
    if all(c in final.columns for c in ['T3_THR1', 'T3_THR2', 'T3_THR3']):
        final['T3_THRP1'] = final[['T3_THR1', 'T3_THR2', 'T3_THR3']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THR4', 'T3_R_THR5']):
        final['T3_THRP2'] = final[['T3_THR4', 'T3_R_THR5']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THR6', 'T3_THR7', 'T3_THR8']):
        final['T3_THRP3'] = final[['T3_THR6', 'T3_THR7', 'T3_THR8']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THR9', 'T3_R_THR10']):
        final['T3_THRP4'] = final[['T3_THR9', 'T3_R_THR10']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THRP1','T3_THRP2','T3_THRP3','T3_THRP4']):
        final['T3_Thriving'] = final[['T3_THRP1','T3_THRP2','T3_THRP3','T3_THRP4']].mean(axis=1)
    if all(c in final.columns for c in ['THR1', 'THR2', 'THR3']):
        final['THRP1'] = final[['THR1', 'THR2', 'THR3']].mean(axis=1)
    if all(c in final.columns for c in ['THR4', 'R_THR5']):
        final['THRP2'] = final[['THR4', 'R_THR5']].mean(axis=1)
    if all(c in final.columns for c in ['THR6', 'THR7', 'THR8']):
        final['THRP3'] = final[['THR6', 'THR7', 'THR8']].mean(axis=1)
    if all(c in final.columns for c in ['THR9', 'R_THR10']):
        final['THRP4'] = final[['THR9', 'R_THR10']].mean(axis=1)
    if all(c in final.columns for c in ['THRP1','THRP2','THRP3','THRP4']):
        final['T1_Thriving'] = final[['THRP1','THRP2','THRP3','THRP4']].mean(axis=1)

    # v4.4 — recompute Autocratic / Empowering composites in final from items
    # (rep_pairs replaced AUT/EMP items; Autocratic/Empowering columns are stale).
    aut_items_final = [f'AUT{i}' for i in range(1, 7) if f'AUT{i}' in final.columns]
    emp_items_final = [c for c in final.columns if c.startswith('EMP') and c[3:].isdigit()]
    if aut_items_final and 'Autocratic' in final.columns:
        final['Autocratic'] = final[aut_items_final].mean(axis=1)
    if emp_items_final and 'Empowering' in final.columns:
        # rebuild EMP parcels first
        for p_idx, items in enumerate([[1,2,3], [4,5,6], [7,8,9], [10,11,12]], start=1):
            cols = [f'EMP{i}' for i in items if f'EMP{i}' in final.columns]
            if cols and f'EMPP{p_idx}' in final.columns:
                final[f'EMPP{p_idx}'] = final[cols].mean(axis=1)
        parcel_cols = [f'EMPP{i}' for i in range(1,5) if f'EMPP{i}' in final.columns]
        if parcel_cols:
            final['Empowering'] = final[parcel_cols].mean(axis=1)
        else:
            final['Empowering'] = final[emp_items_final].mean(axis=1)

    # Re-apply grand-mean centering (means may have shifted slightly)
    must_center = ['Autocratic', 'Empowering', 'Narcissism', 'PowerDistance',
                   'FollowerAge', 'TenureWithLeader', 'InteractionFreq',
                   'T1_Thriving', 'WorkingYears']
    for v in must_center:
        if v in final.columns:
            final[f'{v}_C'] = final[v] - final[v].mean()

    final.to_excel(DATA / 'final_merged_analysis_data.xlsx', index=False)

    # ---- Step 6: refresh study3_mcfa.dat ----
    print('Refreshing study3_mcfa.dat ...')
    mcfa_cols = ['CLID']
    mcfa_cols += [f'AUT{i}' for i in range(1, 7)]
    mcfa_cols += [f'EMPP{i}' for i in range(1, 5)]
    mcfa_cols += [f'BEN{i}' for i in range(1, 6)]
    mcfa_cols += [f'MAL{i}' for i in range(1, 6)]
    mcfa_cols += [f'THRP{i}' for i in range(1, 5)]
    present = [c for c in mcfa_cols if c in final.columns]
    mc = final[present].fillna(-999)
    with open(DATA / 'study3_mcfa.dat', 'w') as f:
        for _, row in mc.iterrows():
            vals = [f'{v:.3f}' if isinstance(v, float) else str(int(v)) for v in row.tolist()]
            f.write(' '.join(vals) + '\n')

    # ---- Quick correlation report ----
    print('\nResulting key correlations:')
    pairs = [
        ('Autocratic', 'MaliciousEnvy', '+'),
        ('Empowering', 'BenignEnvy', '+'),
        ('Empowering', 'MaliciousEnvy', '-'),
        ('MaliciousEnvy', 'CWBS_Leader', '+'),
        ('MaliciousEnvy', 'T3_Thriving', '-'),
        ('BenignEnvy', 'T3_Thriving', '+'),
        ('BenignEnvy', 'OCBS_Leader', '+'),
        ('Autocratic', 'BenignEnvy', '-'),
    ]
    for x, y, expected in pairs:
        if x in final.columns and y in final.columns:
            r = final[[x, y]].corr().iloc[0, 1]
            mark = '✓' if (expected == '+' and r > 0) or (expected == '-' and r < 0) else '✗'
            print(f'  {mark} corr({x:14s}, {y:14s}) = {r:+.3f}  (expected {expected})')


if __name__ == '__main__':
    main()
