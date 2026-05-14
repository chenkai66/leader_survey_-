"""
Constraint Validator for Leadership Survey Data (Study 3).

Validates EVERY requirement extracted from:
  - complete_project_record.md (full client conversation history)
  - 原始客户提供文件/Study3_final measurement plan.docx
  - 原始客户提供文件/研究相关信息260319study3.docx
  - 第一轮结果后客户反馈/YUYU模型重要更新.docx

Pipeline expectation:
    project_root/
        data/         <-- 9 xlsx files + study3_mcfa.dat
        results/      <-- 6 model output xlsx
        code/         <-- this file lives here
        原始客户提供文件/  第一轮交付结果/  第一轮结果后客户反馈/

Returns exit code 0 iff every check passes.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
DATA = ROOT / 'data'
RES = ROOT / 'results'

# Likert max for the main 1-7 instruments
L7 = (1, 7)

PASS, FAIL = 'PASS', 'FAIL'
_results = []  # collected check outcomes


def check(name: str, cond: bool, detail: str = '') -> bool:
    status = PASS if cond else FAIL
    line = f'  [{status}] {name}'
    if detail:
        line += f' -- {detail}'
    print(line)
    _results.append(bool(cond))
    return bool(cond)


def section(title: str) -> None:
    print('\n' + '-' * 60)
    print(title)
    print('-' * 60)


def almost(a: float, b: float, tol: float = 1e-6) -> bool:
    if pd.isna(a) or pd.isna(b):
        return False
    return abs(a - b) < tol


def load() -> dict:
    files = {
        't1_raw':            DATA / 'T1_raw.xlsx',
        't1':                DATA / 'T1_cleaned.xlsx',
        't2_raw':            DATA / 'T2_raw.xlsx',
        't2':                DATA / 'T2_cleaned.xlsx',
        't3l_raw':           DATA / 'T3_leader_raw.xlsx',
        't3l':               DATA / 'T3_leader_cleaned.xlsx',
        't3f_raw':           DATA / 'T3_follower_raw.xlsx',
        't3f':               DATA / 'T3_follower_cleaned.xlsx',
        'final':             DATA / 'final_merged_analysis_data.xlsx',
    }
    out = {}
    for k, p in files.items():
        if not p.exists():
            print(f'MISSING: {p}')
            sys.exit(2)
        out[k] = pd.read_excel(p)
    return out


def main() -> int:
    print('=' * 70)
    print('LEADER-SURVEY CONSTRAINT VALIDATOR  (v2 — comprehensive)')
    print('=' * 70)

    d = load()
    t1, t1r = d['t1'], d['t1_raw']
    t2, t2r = d['t2'], d['t2_raw']
    t3l, t3lr = d['t3l'], d['t3l_raw']
    t3f, t3fr = d['t3f'], d['t3f_raw']
    final = d['final']

    # ---------------------------------------------------------------- 1
    section('1. SAMPLE-SIZE EXPECTATIONS  (T1=90, T2=85, T3=79)')
    check('T1 cleaned leaders == 90', t1['LeaderID'].nunique() == 90,
          f'got {t1["LeaderID"].nunique()}')
    check('T2 cleaned leaders == 85', t2['LeaderID'].nunique() == 85,
          f'got {t2["LeaderID"].nunique()}')
    check('T3 leader cleaned rows == 79', len(t3l) == 79, f'got {len(t3l)}')
    check('T3 follower cleaned leaders == 79', t3f['LeaderID'].nunique() == 79,
          f'got {t3f["LeaderID"].nunique()}')
    check('Final merged leaders == 79', final['LeaderID'].nunique() == 79,
          f'got {final["LeaderID"].nunique()}')

    # ---------------------------------------------------------------- 2
    section('2. RAW > CLEANED  (some rows must be dropped on cleaning)')
    for label, raw, clean in [('T1', t1r, t1), ('T2', t2r, t2),
                              ('T3 leader', t3lr, t3l),
                              ('T3 follower', t3fr, t3f)]:
        check(f'{label}: raw rows > cleaned rows',
              len(raw) > len(clean),
              f'{len(raw)} > {len(clean)}')

    # ---------------------------------------------------------------- 3
    section('3. >=3 SUBORDINATES PER LEADER (final analysis sample)')
    g = final.groupby('LeaderID').size()
    check('final: every leader has >= 3 followers', g.min() >= 3,
          f'min={g.min()}, max={g.max()}, mean={g.mean():.2f}')
    check('T3 follower cleaned: every leader has >= 3 followers',
          t3f.groupby('LeaderID').size().min() >= 3,
          f'min={t3f.groupby("LeaderID").size().min()}')

    # ---------------------------------------------------------------- 4
    section('4. ATTENTION-CHECK ITEMS PRESENT')
    check('T1 has EMP9_AttCheck',  'EMP9_AttCheck'  in t1.columns)
    check('T2 has MAL6_AttCheck',  'MAL6_AttCheck'  in t2.columns)
    check('T3 follower has OCBS7_AttCheck', 'OCBS7_AttCheck' in t3f.columns)
    check('T3 leader has CWBS6_AttCheck',   'CWBS6_AttCheck' in t3l.columns)
    # Attention check should NOT enter composite scoring
    if 'EMP9_AttCheck' in t1.columns and 'Empowering' in t1.columns:
        emp_items = [c for c in t1.columns if c.startswith('EMP') and c != 'EMP9_AttCheck'
                     and c not in ('EMPP1', 'EMPP2', 'EMPP3', 'EMPP4', 'Empowering')]
        # Empowering composite excludes attention check
        expected = t1[emp_items].mean(axis=1)
        diff = (t1['Empowering'] - expected).abs().max()
        check('Empowering composite EXCLUDES EMP9_AttCheck',
              diff < 1e-6, f'max abs diff = {diff:.6f}')

    # ---------------------------------------------------------------- 5
    section('5. CLID  (numeric Mplus cluster id)')
    check('CLID exists in final', 'CLID' in final.columns)
    if 'CLID' in final.columns:
        check('CLID dtype is numeric', pd.api.types.is_numeric_dtype(final['CLID']))
        check('CLID range [1, 79]',
              final['CLID'].min() == 1 and final['CLID'].max() == 79,
              f'[{final["CLID"].min()}, {final["CLID"].max()}]')
        m = final[['LeaderID', 'CLID']].drop_duplicates()
        check('CLID 1:1 with LeaderID', len(m) == 79, f'unique pairs={len(m)}')

    # ---------------------------------------------------------------- 6
    section('6. LeaderEducation  (range 2-5, no NaN)')
    if 'LeaderEducation' in final.columns:
        col = final['LeaderEducation']
        check('LeaderEducation min >= 2', col.min() >= 2, f'min={col.min()}')
        check('LeaderEducation max <= 5', col.max() <= 5, f'max={col.max()}')
        check('LeaderEducation no NaN', col.isna().sum() == 0,
              f'NaN count={col.isna().sum()}')
        check('LeaderEducation integer', col.dropna().apply(lambda x: float(x).is_integer()).all())

    # ---------------------------------------------------------------- 7
    section('7. GRAND-MEAN CENTERING  (mean(_C) ~ 0; _C = orig - grand_mean exactly)')
    must_center = ['Autocratic', 'Empowering', 'Narcissism', 'PowerDistance',
                   'FollowerAge', 'TenureWithLeader', 'InteractionFreq', 'T1_Thriving',
                   'WorkingYears']
    for v in must_center:
        c = f'{v}_C'
        if c not in final.columns:
            check(f'{c} exists', False, 'missing')
            continue
        check(f'{c} mean ~ 0', abs(final[c].mean()) < 1e-3,
              f'mean={final[c].mean():.6f}')
        if v in final.columns:
            expected = final[v] - final[v].mean()
            diff = (final[c] - expected).abs().max()
            check(f'{c} == {v} - grand_mean', diff < 1e-6, f'max diff={diff:.2e}')

    # No dummy variable should be centered
    centered_dummies = [c for c in final.columns
                        if c.endswith('_C') and ('Gender_' in c or 'Edu_' in c)]
    check('Dummies NOT centered', not centered_dummies,
          f'leak: {centered_dummies}' if centered_dummies else 'ok')

    # ---------------------------------------------------------------- 8
    section('8. NARCISSISM IS NOT A MODERATOR  (no ×Narcissism interaction columns)')
    bad = [c for c in final.columns if 'Narcissism' in c and ('x' in c or '×' in c
           or 'X_' in c or '_x_' in c or 'Interaction' in c)]
    check('no narcissism×leadership interaction columns in final', not bad,
          f'found: {bad}' if bad else 'clean')

    # ---------------------------------------------------------------- 9
    section('9. DUPLICATE / MISMATCHED IDs IN RAW DATA')
    if 'FollowerID' in t1r.columns:
        n_dup = t1r['FollowerID'].duplicated().sum()
        check('T1 raw: ~10 duplicate IDs (1 <= n <= 10)', 1 <= n_dup <= 10,
              f'count={n_dup}')
    if 'FollowerID' in t2r.columns:
        n_dup = t2r['FollowerID'].duplicated().sum()
        check('T2 raw: <=5 duplicate IDs', 1 <= n_dup <= 5, f'count={n_dup}')
        # T2 duplicate rows: answers must be identical
        dup_mask = t2r.duplicated(subset='FollowerID', keep=False)
        if dup_mask.any():
            grp = t2r[dup_mask].groupby('FollowerID')
            ok = True
            for _, sub in grp:
                v = sub.drop(columns='FollowerID', errors='ignore')
                if not (v.fillna('NA').nunique() <= 1).all():
                    ok = False
                    break
            check('T2 dup rows have identical answers', ok)
    if 'LeaderID' in t3lr.columns:
        n_dup = t3lr['LeaderID'].duplicated().sum()
        check('T3 leader raw: <=1 duplicate ID', 0 < n_dup <= 1, f'count={n_dup}')

    # Mismatched IDs
    if 'FollowerID' in t1.columns and 'FollowerID' in t2r.columns:
        mismatch = set(t2r['FollowerID']) - set(t1['FollowerID'])
        check('T2 raw: 3 unmatchable FollowerIDs', len(mismatch) >= 3,
              f'count={len(mismatch)}')
    if 'LeaderID' in t2.columns and 'LeaderID' in t3lr.columns:
        mismatch = set(t3lr['LeaderID']) - set(t2['LeaderID'])
        check('T3 leader raw: 1 unmatchable LeaderID', len(mismatch) >= 1,
              f'count={len(mismatch)}')

    # ---------------------------------------------------------------- 10
    section('10. MISSING-VALUE PATTERN  (T1 ~10 non-core, T2 zero, T3-leader ~3)')
    check('T1 raw total missing in [5, 15]',
          5 <= int(t1r.isna().sum().sum()) <= 15,
          f'missing={t1r.isna().sum().sum()}')
    # T1 missing must NOT be in core / mediator / outcome / control / attention / id
    core_t1 = {f'AUT{i}' for i in range(1, 7)}
    core_t1 |= {f'EMP{i}' for i in range(1, 13)}
    core_t1 |= {f'EMPP{i}' for i in range(1, 5)}
    core_t1 |= {f'THR{i}' for i in range(1, 11)} | {'R_THR5', 'R_THR10'}
    core_t1 |= {f'THRP{i}' for i in range(1, 5)}
    core_t1 |= {f'NARC{i}' for i in range(1, 7)}
    core_t1 |= {f'PD{i}' for i in range(1, 7)}
    core_t1 |= {'EMP9_AttCheck', 'LeaderID', 'FollowerID',
                'Autocratic', 'Empowering', 'Narcissism',
                'PowerDistance', 'Thriving', 'T1_Thriving',
                'FollowerAge', 'TenureWithLeader', 'InteractionFreq'}
    miss_in_core = [c for c in t1r.columns
                    if c in core_t1 and t1r[c].isna().any()]
    check('T1 missing NOT in core/mediator/outcome/control/AC/ID',
          not miss_in_core, f'leak: {miss_in_core}' if miss_in_core else 'ok')

    check('T2 raw: ZERO missing values',
          int(t2r.isna().sum().sum()) == 0,
          f'missing={t2r.isna().sum().sum()}')
    check('T3 leader raw: missing in [1, 5]',
          1 <= int(t3lr.isna().sum().sum()) <= 5,
          f'missing={t3lr.isna().sum().sum()}')
    # T3 leader missing must not be in CWBS/OCBS items / attention / IDs
    core_t3l = {f'CWBS{i}' for i in range(1, 8)}
    core_t3l |= {f'OCBS_L{i}' for i in range(1, 9)}
    core_t3l |= {'CWBS6_AttCheck', 'LeaderID'}
    miss = [c for c in t3lr.columns if c in core_t3l and t3lr[c].isna().any()]
    check('T3 leader missing NOT in core/AC/ID',
          not miss, f'leak: {miss}' if miss else 'ok')

    # ---------------------------------------------------------------- 11
    section('11. CORE COMPOSITE SCORES MATCH ITEM AVERAGES')
    # Autocratic = mean(AUT1..AUT6)
    aut_items = [f'AUT{i}' for i in range(1, 7)]
    if all(c in t1.columns for c in aut_items + ['Autocratic']):
        diff = (t1['Autocratic'] - t1[aut_items].mean(axis=1)).abs().max()
        check('Autocratic == mean(AUT1..AUT6)', diff < 1e-6, f'max diff={diff:.2e}')
    # Empowering = mean(EMP1..EMP12 minus AC)
    emp_items = [f'EMP{i}' for i in range(1, 13)]
    if all(c in t1.columns for c in emp_items + ['Empowering']):
        diff = (t1['Empowering'] - t1[emp_items].mean(axis=1)).abs().max()
        check('Empowering == mean(EMP1..EMP12)', diff < 1e-6, f'max diff={diff:.2e}')
    # Narcissism, PowerDistance
    for sc, items in [('Narcissism', [f'NARC{i}' for i in range(1, 7)]),
                      ('PowerDistance', [f'PD{i}' for i in range(1, 7)])]:
        present = [c for c in items if c in t1.columns]
        if sc in t1.columns and present:
            diff = (t1[sc] - t1[present].mean(axis=1)).abs().max()
            check(f'{sc} == mean of items', diff < 1e-6, f'max diff={diff:.2e}')
    # BenignEnvy, MaliciousEnvy in final
    if 'BenignEnvy' in final.columns:
        ben_items = [f'BEN{i}' for i in range(1, 6)]
        if all(c in final.columns for c in ben_items):
            diff = (final['BenignEnvy'] - final[ben_items].mean(axis=1)).abs().max()
            check('BenignEnvy == mean(BEN1..BEN5)', diff < 1e-6, f'max diff={diff:.2e}')
    if 'MaliciousEnvy' in final.columns:
        mal_items = [f'MAL{i}' for i in range(1, 6)]
        if all(c in final.columns for c in mal_items):
            diff = (final['MaliciousEnvy'] - final[mal_items].mean(axis=1)).abs().max()
            check('MaliciousEnvy == mean(MAL1..MAL5)', diff < 1e-6, f'max diff={diff:.2e}')

    # ---------------------------------------------------------------- 12
    section('12. PARCEL DEFINITIONS (Empowering & Thriving by theory)')
    cases = [
        ('EMPP1', ['EMP1', 'EMP2', 'EMP3']),
        ('EMPP2', ['EMP4', 'EMP5', 'EMP6']),
        ('EMPP3', ['EMP7', 'EMP8', 'EMP9']),
        ('EMPP4', ['EMP10', 'EMP11', 'EMP12']),
        ('THRP1', ['THR1', 'THR3', 'R_THR5']),
        ('THRP2', ['THR2', 'THR4']),
        ('THRP3', ['THR6', 'THR8', 'R_THR10']),
        ('THRP4', ['THR7', 'THR9']),
    ]
    for parcel, items in cases:
        if all(c in t1.columns for c in items + [parcel]):
            diff = (t1[parcel] - t1[items].mean(axis=1)).abs().max()
            check(f'{parcel} = mean({", ".join(items)})', diff < 1e-6,
                  f'max diff={diff:.2e}')

    # ---------------------------------------------------------------- 13
    section('13. REVERSE CODING  (R_THR5 = 8 - THR5; R_THR10 = 8 - THR10 on 1-7)')
    # Note: cleaned data already has reversed columns; we cannot recover original
    # THR5/THR10. Validate that R_THR* are within 1..7 and the parcel formula uses them.
    for col in ('R_THR5', 'R_THR10'):
        if col in t1.columns:
            check(f'{col} in [1, 7]',
                  t1[col].min() >= 1 and t1[col].max() <= 7,
                  f'[{t1[col].min()}, {t1[col].max()}]')

    # ---------------------------------------------------------------- 14
    section('14. LIKERT RANGES  (1-7 main scales; 1-5 categorical)')
    for col in ['AUT1', 'AUT6', 'EMP1', 'EMP12', 'THR1', 'THR9',
                'NARC1', 'NARC6', 'PD1']:
        if col in t1.columns:
            mn, mx = t1[col].min(), t1[col].max()
            check(f'{col} in 1..7', mn >= 1 and mx <= 7, f'[{mn}, {mx}]')
    for col in ['BEN1', 'BEN5', 'MAL1', 'MAL5']:
        if col in t2.columns:
            mn, mx = t2[col].min(), t2[col].max()
            check(f'{col} in 1..7', mn >= 1 and mx <= 7, f'[{mn}, {mx}]')
    if 'FollowerEducation' in t1.columns:
        mn, mx = t1['FollowerEducation'].min(), t1['FollowerEducation'].max()
        check('FollowerEducation in 1..5', mn >= 1 and mx <= 5, f'[{mn}, {mx}]')
    if 'InteractionFreq' in t1.columns:
        mn, mx = t1['InteractionFreq'].min(), t1['InteractionFreq'].max()
        check('InteractionFreq in 1..5', mn >= 1 and mx <= 5, f'[{mn}, {mx}]')

    # ---------------------------------------------------------------- 15
    section('15. NO MISSING in core analysis variables of FINAL data')
    final_core = ['LeaderID', 'FollowerID', 'CLID',
                  'Autocratic', 'Empowering', 'Narcissism', 'PowerDistance',
                  'BenignEnvy', 'MaliciousEnvy',
                  'T3_Thriving', 'OCBS_Leader', 'CWBS_Leader',
                  'OCBS_Follower', 'CWBS_Follower',
                  'Autocratic_C', 'Empowering_C', 'Narcissism_C',
                  'PowerDistance_C', 'WorkingYears_C']
    for col in final_core:
        if col in final.columns:
            n = final[col].isna().sum()
            check(f'final.{col} no NaN', n == 0, f'NaN={n}')

    # ---------------------------------------------------------------- 16
    section('16. DUMMY VARIABLES')
    for d in ['Gender_Female', 'Edu_HighSchool', 'Edu_Associate',
              'Edu_Master', 'Edu_Doctoral']:
        if d in final.columns:
            vals = sorted(final[d].dropna().unique().tolist())
            check(f'{d} in {{0,1}}',
                  set(vals).issubset({0, 1}), f'values={vals}')

    # ---------------------------------------------------------------- 17
    section('17. HYPOTHESIS DIRECTIONS  (correlations on FINAL data)')
    # Theoretical signs we EXPECT (from model graph + theory):
    #   Autocratic     ↑Malicious envy   → corr > 0
    #   Empowering     ↑Benign envy      → corr > 0
    #   Empowering     ↓Malicious envy   → corr < 0
    #   Malicious envy ↑CWBS             → corr > 0 (against leader-rated CWBS_Leader)
    #   Malicious envy ↓Thriving         → corr < 0
    #   Benign envy    ↑Thriving         → corr > 0
    #   Benign envy    ↑OCBS             → corr > 0 (against OCBS_Leader)
    pairs = [
        ('Autocratic', 'MaliciousEnvy', '+'),
        ('Empowering', 'BenignEnvy', '+'),
        ('Empowering', 'MaliciousEnvy', '-'),
        ('MaliciousEnvy', 'CWBS_Leader', '+'),
        ('MaliciousEnvy', 'T3_Thriving', '-'),
        ('BenignEnvy', 'T3_Thriving', '+'),
        ('BenignEnvy', 'OCBS_Leader', '+'),
    ]
    for x, y, sign in pairs:
        if x in final.columns and y in final.columns:
            r = final[[x, y]].corr().iloc[0, 1]
            ok = (r > 0 and sign == '+') or (r < 0 and sign == '-')
            check(f'corr({x}, {y}) sign == {sign}', ok, f'r={r:+.3f}')

    # ---------------------------------------------------------------- 18
    section('18. MODEL OUTPUT FILES PRESENT')
    expected = ['Model1.xlsx', 'Model2.xlsx', 'Model3.xlsx',
                'measurement appendix.xlsx', 'ICC空模型.xlsx',
                'YUYU样本量变化.xlsx']
    for f in expected:
        check(f'results/{f} exists', (RES / f).exists())

    # ---------------------------------------------------------------- 19
    section('19. MODEL OUTPUTS — STRUCTURAL/CONTENT CHECKS')
    # Model1 must NOT contain "Narcissism (moderator)" anywhere
    try:
        wb = pd.ExcelFile(RES / 'Model1.xlsx')
        text_blob = ''
        for s in wb.sheet_names:
            text_blob += pd.read_excel(wb, sheet_name=s, header=None).astype(str).to_csv()
        check('Model1.xlsx: no "Narcissism (moderator)" string',
              'Narcissism (moderator)' not in text_blob)
        check('Model1.xlsx: contains "(mediator path)" for narcissism',
              '(mediator path)' in text_blob)
    except Exception as e:
        check('Model1.xlsx readable', False, str(e))

    # Model3 sign sanity
    try:
        m3 = pd.read_excel(RES / 'Model3.xlsx', header=None)
        # find row "Leader-rated Estimate" ; column for "Malicious Env -> OCBS_L"
        header = m3.iloc[1].tolist()
        leader_row = m3[m3.iloc[:, 0].astype(str).str.contains('Leader-rated', na=False)]
        if not leader_row.empty:
            row = leader_row.iloc[0]
            for label, expected_sign in [
                    ('Malicious Env -> OCBS_L', '-'),
                    ('Benign Env -> CWBS_L', '-'),
                    ('Malicious Env -> CWBS_L', '+'),
                    ('Benign Env -> OCBS_L', '+'),
                    ('Autocratic -> Malicious Env', '+'),
                    ('Empowering -> Benign Env', '+'),
                    ('Malicious Env -> Thriving', '-'),
                    ('Benign Env -> Thriving', '+')]:
                if label in header:
                    j = header.index(label)
                    v = row.iloc[j]
                    try:
                        v = float(v)
                    except Exception:
                        v = float('nan')
                    ok = ((v > 0 and expected_sign == '+') or
                          (v < 0 and expected_sign == '-'))
                    check(f'Model3 {label} sign={expected_sign}', ok, f'val={v:+.3f}')
    except Exception as e:
        check('Model3 sign block', False, str(e))

    # measurement appendix must have Single-Construct CFA with cluster adjustment
    try:
        wb = pd.ExcelFile(RES / 'measurement appendix.xlsx')
        names = wb.sheet_names
        check('appendix has Single-Construct CFA sheet',
              any('Single-Construct CFA' in s for s in names),
              f'sheets={names}')
        text_blob = ''
        for s in names:
            text_blob += pd.read_excel(wb, sheet_name=s, header=None).astype(str).to_csv()
        check('appendix mentions TYPE=COMPLEX  (cluster-adjusted CFA)',
              'TYPE=COMPLEX' in text_blob.replace(' ', '') or
              'TYPE = COMPLEX' in text_blob)
        check('appendix mentions CLUSTER',
              'CLUSTER' in text_blob.upper())
    except Exception as e:
        check('appendix structure', False, str(e))

    # YUYU: row 26 should equal final mean follower count
    try:
        yu = pd.read_excel(RES / 'YUYU样本量变化.xlsx', header=None)
        # last numeric in column C ~ 5.5
        avg = final.groupby('LeaderID').size().mean()
        last = pd.to_numeric(yu.iloc[:, 2], errors='coerce').dropna().iloc[-1]
        check('YUYU avg followers/leader matches final',
              abs(avg - last) < 0.1, f'final={avg:.2f} sheet={last}')
    except Exception as e:
        check('YUYU sample-attrition consistency', False, str(e))

    # ICC values plausible
    try:
        icc = pd.read_excel(RES / 'ICC空模型.xlsx', header=None)
        col_b = pd.to_numeric(icc.iloc[:, 1], errors='coerce').dropna()
        check('ICC values all in (0, 0.5)',
              ((col_b > 0) & (col_b < 0.5)).all(),
              f'values={col_b.tolist()}')
    except Exception as e:
        check('ICC plausibility', False, str(e))

    # ---------------------------------------------------------------- 20
    section('20. MCFA Mplus DATA FILE')
    mcfa = DATA / 'study3_mcfa.dat'
    check('study3_mcfa.dat exists', mcfa.exists())
    if mcfa.exists():
        with open(mcfa, encoding='utf-8', errors='ignore') as f:
            head = [next(f) for _ in range(3) if True]
        # ensure CLID is the first numeric column on every row
        ok = all(line.strip().split()[0].lstrip('-').replace('.', '').isdigit()
                 for line in head if line.strip())
        check('first column of mcfa.dat is numeric (CLID)', ok)
        with open(mcfa, encoding='utf-8', errors='ignore') as f:
            lines = [ln for ln in f if ln.strip()]
        check('mcfa.dat row count == 438', len(lines) == 438,
              f'rows={len(lines)}')

    # ---------------------------------------------------------------- 21
    section('21. CROSS-WAVE ID INTEGRITY  (no orphaned followers in final)')
    final_fids = set(final['FollowerID'])
    t1_clean_fids = set(t1['FollowerID'])
    orphans = final_fids - t1_clean_fids
    check('every final follower exists in T1 cleaned',
          not orphans, f'orphans={len(orphans)}' if orphans else 'ok')
    t2_fids = set(t2['FollowerID'])
    check('every final follower exists in T2 cleaned',
          not (final_fids - t2_fids),
          f'missing={len(final_fids - t2_fids)}')
    t3f_fids = set(t3f['FollowerID'])
    check('every final follower exists in T3-follower cleaned',
          not (final_fids - t3f_fids),
          f'missing={len(final_fids - t3f_fids)}')
    final_lids = set(final['LeaderID'])
    t3l_lids = set(t3l['LeaderID'])
    check('every final leader exists in T3-leader cleaned',
          not (final_lids - t3l_lids),
          f'missing={len(final_lids - t3l_lids)}')

    # ---------------------------------------------------------------- 22
    section('22. NO DUPLICATE IDs IN CLEANED DATA')
    for label, df, key in [('T1', t1, 'FollowerID'), ('T2', t2, 'FollowerID'),
                           ('T3 follower', t3f, 'FollowerID'),
                           ('T3 leader', t3l, 'LeaderID'),
                           ('final', final, 'FollowerID')]:
        if key in df.columns:
            n = df[key].duplicated().sum()
            check(f'{label} cleaned: no duplicate {key}', n == 0, f'count={n}')

    # ---------------------------------------------------------------- summary
    print('\n' + '=' * 70)
    n_pass = sum(_results)
    n_total = len(_results)
    n_fail = n_total - n_pass
    print(f'SUMMARY:  {n_pass}/{n_total} passed,  {n_fail} failed')
    if n_fail == 0:
        print('ALL CONSTRAINTS SATISFIED.')
    else:
        print(f'WARNING: {n_fail} constraints violated.')
    print('=' * 70)
    return 0 if n_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
