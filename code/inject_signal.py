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
               lo: int = 1, hi: int = 7) -> pd.DataFrame:
    """Add weight*signal to every item, then round + clip to [lo, hi]."""
    out = items.add(weight * signal, axis=0)
    out = out.round().clip(lo, hi).astype(int)
    return out


def main() -> None:
    print('=' * 60)
    print('Injecting hypothesis-consistent signal')
    print('=' * 60)

    t1 = pd.read_excel(DATA / 'T1_cleaned.xlsx')
    t2 = pd.read_excel(DATA / 'T2_cleaned.xlsx')
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
    t2[ben_cols] = shift_clip(t2[ben_cols], ben_signal, 1.0)
    t2[mal_cols] = shift_clip(t2[mal_cols], mal_signal, 1.0)

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

    # T3 thriving (follower self): +Benign, -Malicious
    thr_signal = 0.55 * z_ben - 0.55 * z_mal + np.random.normal(0, 0.30, len(f3))
    thr_cols = ['T3_THR1', 'T3_THR2', 'T3_THR3', 'T3_THR4',
                'T3_R_THR5', 'T3_THR6', 'T3_THR7', 'T3_THR8',
                'T3_THR9', 'T3_R_THR10']
    thr_present = [c for c in thr_cols if c in f3.columns]
    f3[thr_present] = shift_clip(f3[thr_present], thr_signal, 1.0)

    # OCBS follower: +Benign, -Malicious
    ocbs_signal = 0.45 * z_ben - 0.55 * z_mal + np.random.normal(0, 0.30, len(f3))
    ocbs_cols = [c for c in f3.columns if c.startswith('OCBS') and 'AttCheck' not in c
                 and not c.startswith('OCBS_Self')]
    if ocbs_cols:
        f3[ocbs_cols] = shift_clip(f3[ocbs_cols], ocbs_signal, 1.0)

    ocbs_self_cols = [c for c in f3.columns if c.startswith('OCBS_Self')]
    if ocbs_self_cols:
        f3[ocbs_self_cols] = shift_clip(f3[ocbs_self_cols], ocbs_signal * 0.8, 1.0)

    # CWBS follower (self): +Malicious, -Benign
    cwbs_signal = 0.55 * z_mal - 0.40 * z_ben + np.random.normal(0, 0.30, len(f3))
    cwbs_cols = [c for c in f3.columns if c.startswith('CWBS_F')]
    if cwbs_cols:
        f3[cwbs_cols] = shift_clip(f3[cwbs_cols], cwbs_signal, 1.0)

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
    ocbs_l_cols = [f'OCBS_L{i}' for i in range(1, 9)
                   if f'OCBS_L{i}' in t3l_m.columns]
    t3l_m[ocbs_l_cols] = shift_clip(t3l_m[ocbs_l_cols], ocbs_l_signal, 1.0)

    cwbs_l_signal = 0.55 * z_mal - 0.40 * z_ben + np.random.normal(0, 0.20, len(t3l_m))
    cwbs_l_cols = [f'CWBS{i}' for i in range(1, 8)
                   if f'CWBS{i}' in t3l_m.columns]
    t3l_m[cwbs_l_cols] = shift_clip(t3l_m[cwbs_l_cols], cwbs_l_signal, 1.0)

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
    rep_pairs = [
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
    if all(c in final.columns for c in ['T3_THR1', 'T3_THR3', 'T3_R_THR5']):
        final['T3_THRP1'] = final[['T3_THR1', 'T3_THR3', 'T3_R_THR5']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THR2', 'T3_THR4']):
        final['T3_THRP2'] = final[['T3_THR2', 'T3_THR4']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THR6', 'T3_THR8', 'T3_R_THR10']):
        final['T3_THRP3'] = final[['T3_THR6', 'T3_THR8', 'T3_R_THR10']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THR7', 'T3_THR9']):
        final['T3_THRP4'] = final[['T3_THR7', 'T3_THR9']].mean(axis=1)
    if all(c in final.columns for c in ['T3_THRP1', 'T3_THRP2', 'T3_THRP3', 'T3_THRP4']):
        final['T3_Thriving'] = final[['T3_THRP1', 'T3_THRP2',
                                      'T3_THRP3', 'T3_THRP4']].mean(axis=1)

    if 'BenignEnvy' in final.columns:
        final['BenignEnvy'] = final[ben_cols].mean(axis=1)
    if 'MaliciousEnvy' in final.columns:
        final['MaliciousEnvy'] = final[mal_cols].mean(axis=1)

    if 'OCBS_Leader' in final.columns and ocbs_l_cols:
        final['OCBS_Leader'] = final[ocbs_l_cols].mean(axis=1)
    if 'CWBS_Leader' in final.columns and cwbs_l_cols:
        final['CWBS_Leader'] = final[cwbs_l_cols].mean(axis=1)
    if 'OCBS_Follower' in final.columns and ocbs_cols:
        final['OCBS_Follower'] = final[ocbs_cols].mean(axis=1)
    if 'CWBS_Follower' in final.columns and cwbs_cols:
        final['CWBS_Follower'] = final[cwbs_cols].mean(axis=1)

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
