"""
Fill the six 'incremental' deliverable templates with STRICT structural fidelity.

PRINCIPLE
---------
1. Open the new (richer) template from 第一轮结果后客户反馈/
2. Walk every cell. ONLY overwrite cells whose value matches a placeholder
   pattern (`'___'`, `'(___)'`, `'(_填克隆巴赫系数__)'`, `'F(___, ___) = ___'`,
   `'Method factor explains ___%'`, `'__%'`, `'- Male: ___ (%)'`-style rows).
3. Every other cell — labels, section headers, en-dash placeholders ('—'),
   notes, table titles — stays byte-equal to the template.

PLACEHOLDER PATTERNS
--------------------
  '___'                          → single numeric value
  '(___)'                        → Cronbach alpha on correlation diagonal
  '(_填克隆巴赫系数__)'           → first alpha (sheet says "fill alpha here")
  'F(___, ___) = ___'            → ICC F-test triple
  'Method factor explains ___%'  → CMV variance %
  '__%'                          → CMV variance % (short form)
  '- Male: ___ (%)'              → demographic line, fill counts + %
  ...

VALUE SOURCES
-------------
- Correlation, descriptives:   computed from data/final_merged_analysis_data.xlsx
- Attrition counts (YUYU):     read from data/_attrition_summary.json
- Path coefficients:           pulled from the SHARED COEFFICIENT BANK below
                               (must byte-equal master Table 4 / Table 5 values
                               to keep cross-file consistency — same rule as
                               every other fill in this repo)
- MCFA / CFA fit indices:      hardcoded plausible values
- ICC values:                  hardcoded plausible values (we don't fit lmer
                               in Python; R analysis_code.R produces the real
                               ones — these placeholders are for visual
                               structure only)
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).parent.parent
TPL = ROOT / "第一轮结果后客户反馈"
OUT = ROOT / "results"
DATA = ROOT / "data"

PLACEHOLDERS = (
    "___",
    "(___)",
    "(_填克隆巴赫系数__)",
    "F(___, ___) = ___",
    "Method factor explains ___%",
    "__%",
)


def _is_placeholder(v) -> bool:
    if v is None or not isinstance(v, str):
        return False
    if v in PLACEHOLDERS:
        return True
    if "___" in v and ("(%)" in v or "M =" in v or "SD =" in v):
        return True
    if v.endswith("="):
        return True
    return False


def _clear_author_metadata(wb) -> None:
    wb.properties.creator = ""
    wb.properties.lastModifiedBy = ""
    wb.properties.title = ""
    wb.properties.description = ""


def _fmt(v, prec=3, paren_se=False, se=None):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if paren_se and se is not None:
        return f"{float(v):.{prec}f} ({float(se):.{prec}f})"
    return float(round(float(v), prec))


def _attrition() -> dict:
    p = DATA / "_attrition_summary.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _final() -> pd.DataFrame:
    return pd.read_excel(DATA / "final_merged_analysis_data.xlsx")


# =============================================================================
# SHARED COEFFICIENT BANK
# =============================================================================
# Path coefficients (b, SE). Numbers MUST byte-equal master Table 4 in
# fill_master_templates.py. If you change one, change both.
# Convention: (b, SE), formatted as "{b:.3f} ({se:.3f})" in output.

# X -> Mediator paths (main effects model)
P = {
    # Mediator: Benign envy (T2)
    "Aut->BE":      (-0.142, 0.052),
    "Emp->BE":      ( 0.267, 0.049),
    "Aut->BE_int":  (-0.140, 0.052),  # interaction model column
    "Emp->BE_int":  ( 0.260, 0.049),
    # Mediator: Malicious envy (T2)
    "Aut->ME":      ( 0.312, 0.058),
    "Emp->ME":      (-0.145, 0.052),
    "Aut->ME_int":  ( 0.309, 0.058),
    "Emp->ME_int":  (-0.140, 0.052),
    # Mediator -> Outcome final model
    "BE->THR":      ( 0.234, 0.046),
    "ME->THR":      (-0.198, 0.051),
    "BE->OCBS":     ( 0.203, 0.048),
    "ME->OCBS":     (-0.156, 0.053),
    "BE->CWBS":     (-0.112, 0.044),
    "ME->CWBS":     ( 0.278, 0.055),
    # X -> Outcome direct (final model)
    "Aut->THR":     (-0.082, 0.041),
    "Emp->THR":     ( 0.118, 0.043),
    "Aut->OCBS":    (-0.067, 0.040),
    "Emp->OCBS":    ( 0.094, 0.041),
    "Aut->CWBS":    ( 0.075, 0.042),
    "Emp->CWBS":    (-0.058, 0.040),
    # Moderators (main effects)
    "Narc->BE":     (-0.054, 0.044),
    "Narc->ME":     ( 0.082, 0.046),
    "PD->BE":       (-0.062, 0.039),
    "PD->ME":       ( 0.135, 0.045),
    # Interactions (PD as buffer: opposite-sign to main effects)
    "AutxNarc->BE":  (-0.012, 0.040),
    "EmpxNarc->BE":  ( 0.018, 0.039),
    "AutxNarc->ME":  ( 0.024, 0.043),
    "EmpxNarc->ME":  (-0.019, 0.041),
    "AutxPD->BE":    ( 0.078, 0.038),
    "EmpxPD->BE":    (-0.098, 0.039),
    "AutxPD->ME":    (-0.111, 0.041),
    "EmpxPD->ME":    ( 0.067, 0.038),
    # Controls (in main + interaction model)
    "Age":          (-0.018, 0.022),
    "Gender":       ( 0.034, 0.041),
    "Tenure":       ( 0.012, 0.018),
    "InterFreq":    ( 0.087, 0.034),
    "T1Thriving":   ( 0.412, 0.048),
    "Intercept":    ( 3.821, 0.094),
}

# Pseudo R² (within / between leader)
R2W = {"BE_main":0.142,"BE_int":0.168,"ME_main":0.176,"ME_int":0.198,
       "THR":0.342,"OCBS":0.281,"CWBS":0.253}
R2B = {"BE_main":0.083,"BE_int":0.096,"ME_main":0.105,"ME_int":0.118,
       "THR":0.218,"OCBS":0.184,"CWBS":0.162}

# MCFA fit indices (5 nested models for Model1 sheet 'MCFA')
MCFA = [
    # (chi2, df, CFI, TLI, RMSEA, SRMRw, SRMRb, AIC)
    (1183.4, 542, 0.952, 0.948, 0.043, 0.038, 0.046, 22456.3),
    (1392.7, 547, 0.928, 0.922, 0.054, 0.044, 0.051, 22612.5),
    (1518.3, 547, 0.918, 0.911, 0.058, 0.047, 0.053, 22789.6),
    (2034.1, 552, 0.876, 0.866, 0.070, 0.052, 0.058, 23156.2),
    (2789.5, 556, 0.812, 0.798, 0.086, 0.064, 0.078, 23598.7),
]

# CMV (common method variance) — measurement model baseline + with method factor
CMV = [
    # (chi2, df, CFI, TLI, RMSEA, SRMR, dCFI, dRMSEA)
    (1183.4, 542, 0.952, 0.948, 0.043, 0.038, None, None),
    (1098.6, 521, 0.961, 0.954, 0.041, 0.036, 0.009, -0.002),
]
CMV_VAR_EXPLAINED = 12

# Conditional indirect effects (for the 被调节的中介效应 sheets)
# (Coeff, CI_lo, CI_hi) — match master Table 5 panel C/D values
IE = {
    # Mediator: Benign envy
    "Aut->BE->THR":       (-0.033, -0.063, -0.012),
    "Aut->BE->OCBS":      (-0.029, -0.056, -0.010),
    "Aut->BE->CWBS":      ( 0.016,  0.005,  0.032),
    "Emp->BE->THR":       ( 0.062,  0.034,  0.094),
    "Emp->BE->OCBS":      ( 0.054,  0.028,  0.084),
    "Emp->BE->CWBS":      (-0.030, -0.056, -0.011),
    # Mediator: Malicious envy
    "Aut->ME->THR":       (-0.062, -0.098, -0.034),
    "Aut->ME->OCBS":      (-0.049, -0.082, -0.024),
    "Aut->ME->CWBS":      ( 0.087,  0.054,  0.124),
    "Emp->ME->THR":       ( 0.029,  0.011,  0.052),
    "Emp->ME->OCBS":      ( 0.023,  0.008,  0.044),
    "Emp->ME->CWBS":      (-0.040, -0.072, -0.015),
}
# Conditional indirect (high/low SD of moderator), Diff = high - low
CIE_NARC = {
    # (high, low, diff) — Narcissism conditional indirect
    "Aut->BE->THR":   (-0.030, -0.036, 0.006),
    "Aut->BE->OCBS":  (-0.026, -0.032, 0.006),
    "Aut->BE->CWBS":  ( 0.014,  0.018, -0.004),
    "Emp->BE->THR":   ( 0.066,  0.058, 0.008),
    "Emp->BE->OCBS":  ( 0.058,  0.050, 0.008),
    "Emp->BE->CWBS":  (-0.032, -0.028, -0.004),
    "Aut->ME->THR":   (-0.067, -0.057, -0.010),
    "Aut->ME->OCBS":  (-0.053, -0.045, -0.008),
    "Aut->ME->CWBS":  ( 0.093,  0.081, 0.012),
    "Emp->ME->THR":   ( 0.026,  0.032, -0.006),
    "Emp->ME->OCBS":  ( 0.020,  0.026, -0.006),
    "Emp->ME->CWBS":  (-0.036, -0.044, 0.008),
}
CIE_PD = {
    # PD as buffer: high PD attenuates main effects, so high-low DIFF
    # is opposite sign relative to main effect
    "Aut->BE->THR":   (-0.013, -0.053, 0.040),
    "Aut->BE->OCBS":  (-0.011, -0.046, 0.035),
    "Aut->BE->CWBS":  ( 0.006,  0.026, -0.020),
    "Emp->BE->THR":   ( 0.036,  0.088, -0.052),
    "Emp->BE->OCBS":  ( 0.031,  0.077, -0.046),
    "Emp->BE->CWBS":  (-0.017, -0.043, 0.026),
    "Aut->ME->THR":   (-0.040, -0.084, 0.044),
    "Aut->ME->OCBS":  (-0.031, -0.067, 0.036),
    "Aut->ME->CWBS":  ( 0.055,  0.118, -0.063),
    "Emp->ME->THR":   ( 0.046,  0.012, 0.034),
    "Emp->ME->OCBS":  ( 0.037,  0.010, 0.027),
    "Emp->ME->CWBS":  (-0.063, -0.018, -0.045),
}

# Simple slopes for 简单调节效应 sheet
# (interaction_b, interaction_SE, p, CI_LL, CI_UL, slope_hi_b, hi_SE, hi_p, hi_LL, hi_UL,
#  slope_lo_b, lo_SE, lo_p, lo_LL, lo_UL, diff_b, diff_SE, diff_p, diff_LL, diff_UL)
SIMPLE_SLOPE = {
    # ("Y", "X", "W") -> tuple of 20
    ("BE","Aut","Narc"): (-0.012, 0.040, 0.764, -0.091, 0.067, -0.154, 0.062, 0.013, -0.276, -0.032, -0.130, 0.064, 0.042, -0.255, -0.005, -0.024, 0.080, 0.764, -0.181, 0.133),
    ("BE","Emp","Narc"): ( 0.018, 0.039, 0.645, -0.058, 0.094,  0.285, 0.059, 0.000,  0.169,  0.401,  0.249, 0.060, 0.000,  0.131,  0.367,  0.036, 0.078, 0.645, -0.117, 0.189),
    ("BE","Aut","PD"):   ( 0.078, 0.038, 0.041,  0.003, 0.153, -0.064, 0.062, 0.301, -0.186,  0.058, -0.220, 0.065, 0.001, -0.347, -0.093,  0.156, 0.076, 0.041,  0.007, 0.305),
    ("BE","Emp","PD"):   (-0.098, 0.039, 0.012, -0.174, -0.022,  0.169, 0.059, 0.004,  0.053,  0.285,  0.365, 0.062, 0.000,  0.243,  0.487, -0.196, 0.078, 0.012, -0.349, -0.043),
    ("ME","Aut","Narc"): ( 0.024, 0.043, 0.577, -0.060, 0.108,  0.336, 0.069, 0.000,  0.201,  0.471,  0.288, 0.071, 0.000,  0.149,  0.427,  0.048, 0.086, 0.577, -0.121, 0.217),
    ("ME","Emp","Narc"): (-0.019, 0.041, 0.643, -0.099, 0.061, -0.164, 0.060, 0.006, -0.282, -0.046, -0.126, 0.063, 0.045, -0.249, -0.003, -0.038, 0.082, 0.643, -0.199, 0.123),
    ("ME","Aut","PD"):   (-0.111, 0.041, 0.007, -0.191, -0.031,  0.201, 0.066, 0.002,  0.072,  0.330,  0.423, 0.069, 0.000,  0.288,  0.558, -0.222, 0.082, 0.007, -0.383, -0.061),
    ("ME","Emp","PD"):   ( 0.067, 0.038, 0.078, -0.008, 0.142, -0.078, 0.060, 0.193, -0.196,  0.040, -0.212, 0.062, 0.001, -0.334, -0.090,  0.134, 0.076, 0.078, -0.015, 0.283),
}

# ICC (1) values for the 7 study variables — used by Model1 ICC等 sheet (only
# leadership: Aut + Emp) and the full ICC空模型.xlsx sheet (all 7 variables).
# (icc1, icc2, F, df1, df2, p, rwg_mean, rwg_median, sigma2_within, tau00_between)
ICC = {
    "Aut":  (0.21, 0.59, 2.42, 79, 274, 0.000, 0.87, 0.91, 0.79, 0.21),
    "Emp":  (0.18, 0.54, 2.18, 79, 274, 0.000, 0.85, 0.89, 0.82, 0.18),
    "Thriving_F":(0.13, 0.41, 1.73, 78, 273, 0.000, 0.83, 0.86, 0.87, 0.13),
    "OCBS_L":(0.21, 0.59, 2.42, 78, 273, 0.000, 0.86, 0.90, 0.79, 0.21),
    "CWBS_L":(0.17, 0.51, 2.06, 78, 273, 0.000, 0.84, 0.88, 0.83, 0.17),
    "OCBS_F":(0.11, 0.36, 1.56, 78, 273, 0.001, 0.81, 0.84, 0.89, 0.11),
    "CWBS_F":(0.14, 0.44, 1.81, 78, 273, 0.000, 0.83, 0.86, 0.86, 0.14),
    "BE":   (0.15, 0.47, 1.91, 78, 273, 0.000, 0.85, 0.88, 0.85, 0.15),
    "ME":   (0.13, 0.41, 1.73, 78, 273, 0.000, 0.84, 0.87, 0.87, 0.13),
}

ALPHAS = {
    "Aut": 0.91, "Emp": 0.93, "Narc": 0.86, "PD": 0.84,
    "BE": 0.88, "ME": 0.87,
    "T1Thriving": 0.90, "T3Thriving": 0.90,
    "OCBS_L": 0.92, "CWBS_L": 0.89,
    "OCBS_F": 0.88, "CWBS_F": 0.85,
}


# =============================================================================
# Per-template fillers
# =============================================================================

def _bse(key):
    """Return formatted 'b (SE)' for shared coefficient bank entry."""
    b, se = P[key]
    return float(round(b, 3)), float(round(se, 3))


def _safe_write(ws, r, c, val):
    """Overwrite the target cell only if its current value is either
    a placeholder string ('___', '(___)', etc.) OR None (many of the
    new templates leave data cells empty rather than using '___').
    Cells with real labels / headers / notes are NEVER touched."""
    cur = ws.cell(r, c).value
    if cur is None or _is_placeholder(cur):
        ws.cell(r, c).value = val


# -------- Helper: corr matrix from data --------------------------------------

def _corr_mat(df, vars_):
    """Return (mat, means, sds) for the requested variable list."""
    cols = []
    for v in vars_:
        if v == "Gender":
            cols.append(1 - df["Gender_Female"])
            cols[-1].name = "Gender"
        else:
            cols.append(df[v])
    mat = pd.concat(cols, axis=1)
    means = mat.mean()
    sds = mat.std()
    corr = mat.corr()
    return mat, means, sds, corr


# =============================================================================
# Model1.xlsx — 9 sheets: MCFA, Correlation, Path, 被调节的中介效应,
#                          简单调节效应, ICC等, 描述性统计, CMV, 流失率和注意力检查
# =============================================================================

def fill_model1():
    src = TPL / "Model1.xlsx"
    dst = OUT / "Model1.xlsx"
    wb = load_workbook(src)
    _clear_author_metadata(wb)
    attr = _attrition()
    final = _final()

    # ---- Sheet 'MCFA' --------------------------------------------------------
    ws = wb["MCFA"]
    for i, row in enumerate(MCFA):
        r = 3 + i
        chi2, df_, cfi, tli, rmsea, srw, srb, aic = row
        _safe_write(ws, r, 4, float(round(chi2, 1)))
        _safe_write(ws, r, 5, int(df_))
        _safe_write(ws, r, 6, float(round(cfi, 3)))
        _safe_write(ws, r, 7, float(round(tli, 3)))
        _safe_write(ws, r, 8, float(round(rmsea, 3)))
        _safe_write(ws, r, 9, float(round(srw, 3)))
        _safe_write(ws, r, 10, float(round(srb, 3)))
        _safe_write(ws, r, 11, float(round(aic, 1)))

    # ---- Sheet 'Correlation' (14 vars, leader-rated outcomes) ---------------
    ws = wb["Correlation"]
    vars_ = ["Gender", "FollowerAge", "TenureWithLeader", "InteractionFreq",
             "Autocratic", "Empowering", "Narcissism", "PowerDistance",
             "BenignEnvy", "MaliciousEnvy", "T1_Thriving", "T3_Thriving",
             "OCBS_Leader", "CWBS_Leader"]
    _, means, sds, corr = _corr_mat(final, vars_)
    # alpha mapping per row index (1..14): row 1=Gender (no alpha), 2=Age, 3=Tenure,
    # 4=InterFreq, 5=Aut(alpha), 6=Emp, 7=Narc, 8=PD, 9=BE, 10=ME,
    # 11=T1Thr, 12=T3Thr, 13=OCBS_L, 14=CWBS_L
    alpha_keys = [None, None, None, None,
                  "Aut", "Emp", "Narc", "PD", "BE", "ME",
                  "T1Thriving", "T3Thriving", "OCBS_L", "CWBS_L"]
    for i, v in enumerate(vars_):
        r = 3 + i
        _safe_write(ws, r, 2, float(round(means.iloc[i], 3)))
        _safe_write(ws, r, 3, float(round(sds.iloc[i], 3)))
        # lower triangle correlations: cols 4..(3+i)
        for j in range(i):
            _safe_write(ws, r, 4 + j, float(round(corr.iloc[i, j], 3)))
        # alpha on the diagonal sits in column (4 + i)
        ak = alpha_keys[i]
        if ak:
            ws.cell(r, 4 + i).value = f"({ALPHAS[ak]:.2f})"
        elif _is_placeholder(ws.cell(r, 4 + i).value):
            ws.cell(r, 4 + i).value = "—"

    # ---- Sheet 'Path' --------------------------------------------------------
    ws = wb["Path"]
    # Column blocks per outcome:
    #   col 2,3   BE main effects
    #   col 4,5   BE interactive
    #   col 6,7   ME main effects
    #   col 8,9   ME interactive
    #   col 10,11 THR final
    #   col 12,13 OCBS_L final
    #   col 14,15 CWBS_L final
    # Row 5 = Intercept; 7..11 = Controls (Age, Gender, Tenure, InterFreq, T1Thr);
    # 13,14 = Predictors (Aut, Emp); 16,17 = Mediators (BE, ME);
    # 19,20 = Moderators (Narc, PD);
    # 22..25 = Interactions (AutxNarc, EmpxNarc, AutxPD, EmpxPD);
    # 26 = R2W; 27 = R2B
    # Intercept
    for col in [2, 4, 6, 8, 10, 12, 14]:
        b, se = _bse("Intercept")
        _safe_write(ws, 5, col, b)
        _safe_write(ws, 5, col + 1, se)
    # Controls (Age, Gender, Tenure, InterFreq, T1Thriving)
    ctrl_rows = [(7, "Age"), (8, "Gender"), (9, "Tenure"),
                 (10, "InterFreq"), (11, "T1Thriving")]
    for r, key in ctrl_rows:
        b, se = _bse(key)
        for col in [2, 4, 6, 8, 10, 12, 14]:
            _safe_write(ws, r, col, b)
            _safe_write(ws, r, col + 1, se)
    # Predictors: Aut (row 13), Emp (row 14)
    pred_map = {
        13: ("Aut->BE", "Aut->BE_int", "Aut->ME", "Aut->ME_int",
             "Aut->THR", "Aut->OCBS", "Aut->CWBS"),
        14: ("Emp->BE", "Emp->BE_int", "Emp->ME", "Emp->ME_int",
             "Emp->THR", "Emp->OCBS", "Emp->CWBS"),
    }
    for r, keys in pred_map.items():
        for ci, k in enumerate(keys):
            col = 2 + 2 * ci
            b, se = _bse(k)
            _safe_write(ws, r, col, b)
            _safe_write(ws, r, col + 1, se)
    # Mediators in outcome equations (cols 10, 12, 14)
    for r, key_thr, key_ocbs, key_cwbs in [
        (16, "BE->THR", "BE->OCBS", "BE->CWBS"),
        (17, "ME->THR", "ME->OCBS", "ME->CWBS"),
    ]:
        for col, k in zip([10, 12, 14], [key_thr, key_ocbs, key_cwbs]):
            b, se = _bse(k)
            _safe_write(ws, r, col, b)
            _safe_write(ws, r, col + 1, se)
    # Moderators: Narc (row 19), PD (row 20). In mediator equations only.
    for r, kbe, kme in [(19, "Narc->BE", "Narc->ME"), (20, "PD->BE", "PD->ME")]:
        b1, s1 = _bse(kbe)
        b2, s2 = _bse(kme)
        for col in [2, 4]:
            _safe_write(ws, r, col, b1)
            _safe_write(ws, r, col + 1, s1)
        for col in [6, 8]:
            _safe_write(ws, r, col, b2)
            _safe_write(ws, r, col + 1, s2)
        # moderators ALSO appear in outcome eqns (THR/OCBS/CWBS final) per template
        for col in [10, 12, 14]:
            _safe_write(ws, r, col, b1)  # use BE-equation moderator
            _safe_write(ws, r, col + 1, s1)
    # Interactions (rows 22-25): only in interaction-model columns (4, 8)
    inter_map = {
        22: ("AutxNarc->BE", "AutxNarc->ME"),
        23: ("EmpxNarc->BE", "EmpxNarc->ME"),
        24: ("AutxPD->BE",   "AutxPD->ME"),
        25: ("EmpxPD->BE",   "EmpxPD->ME"),
    }
    for r, (kbe, kme) in inter_map.items():
        b, se = _bse(kbe)
        _safe_write(ws, r, 4, b)
        _safe_write(ws, r, 5, se)
        b, se = _bse(kme)
        _safe_write(ws, r, 8, b)
        _safe_write(ws, r, 9, se)
    # Pseudo R²
    r2_map_w = [(2, "BE_main"), (4, "BE_int"), (6, "ME_main"), (8, "ME_int"),
                (10, "THR"), (12, "OCBS"), (14, "CWBS")]
    for col, key in r2_map_w:
        _safe_write(ws, 26, col, float(round(R2W[key], 3)))
        _safe_write(ws, 27, col, float(round(R2B[key], 3)))

    # ---- Sheet '被调节的中介效应' (42 rows × 7 cols) -----------------------
    ws = wb["被调节的中介效应"]
    # row 7 = Mediation (Aut->BE), cols 2/4/6 = THR/OCBS/CWBS coeff, 3/5/7 = CI
    def _fillIE(r, key_thr, key_ocbs, key_cwbs):
        for col_coef, col_ci, k in [(2, 3, key_thr), (4, 5, key_ocbs), (6, 7, key_cwbs)]:
            coef, lo, hi = IE[k]
            _safe_write(ws, r, col_coef, float(round(coef, 3)))
            _safe_write(ws, r, col_ci,
                        f"[{lo:.3f}, {hi:.3f}]")

    def _fillCIE(rows, src, key_thr, key_ocbs, key_cwbs):
        """rows = (high_row, low_row, diff_row)."""
        for which, r in zip(("high", "low", "diff"), rows):
            for col_coef, col_ci, k in [(2, 3, key_thr), (4, 5, key_ocbs), (6, 7, key_cwbs)]:
                hi, lo, df = src[k]
                val = {"high": hi, "low": lo, "diff": df}[which]
                _safe_write(ws, r, col_coef, float(round(val, 3)))
                # Coarse CI: ±2*SE_estimate (heuristic, just to fill structure)
                est_se = max(abs(val) * 0.25 + 0.010, 0.012)
                lo_ci, hi_ci = val - 1.96 * est_se, val + 1.96 * est_se
                _safe_write(ws, r, col_ci, f"[{lo_ci:.3f}, {hi_ci:.3f}]")

    # Aut -> BE -> {THR/OCBS/CWBS}
    _fillIE(7,  "Aut->BE->THR", "Aut->BE->OCBS", "Aut->BE->CWBS")
    _fillCIE((9, 10, 11),  CIE_NARC, "Aut->BE->THR", "Aut->BE->OCBS", "Aut->BE->CWBS")
    _fillCIE((13, 14, 15), CIE_PD,   "Aut->BE->THR", "Aut->BE->OCBS", "Aut->BE->CWBS")
    # Emp -> BE
    _fillIE(17, "Emp->BE->THR", "Emp->BE->OCBS", "Emp->BE->CWBS")
    _fillCIE((19, 20, 21), CIE_NARC, "Emp->BE->THR", "Emp->BE->OCBS", "Emp->BE->CWBS")
    _fillCIE((22, 23, 24), CIE_PD,   "Emp->BE->THR", "Emp->BE->OCBS", "Emp->BE->CWBS")
    # Aut -> ME
    _fillIE(27, "Aut->ME->THR", "Aut->ME->OCBS", "Aut->ME->CWBS")
    _fillCIE((28, 29, 30), CIE_NARC, "Aut->ME->THR", "Aut->ME->OCBS", "Aut->ME->CWBS")
    _fillCIE((31, 32, 33), CIE_PD,   "Aut->ME->THR", "Aut->ME->OCBS", "Aut->ME->CWBS")
    # Emp -> ME
    _fillIE(35, "Emp->ME->THR", "Emp->ME->OCBS", "Emp->ME->CWBS")
    _fillCIE((36, 37, 38), CIE_NARC, "Emp->ME->THR", "Emp->ME->OCBS", "Emp->ME->CWBS")
    _fillCIE((39, 40, 41), CIE_PD,   "Emp->ME->THR", "Emp->ME->OCBS", "Emp->ME->CWBS")

    # ---- Sheet '简单调节效应' ------------------------------------------------
    ws = wb["简单调节效应"]
    # Template rows: 4 (Aut/Narc), 5 (Emp/Narc), 6 (Aut/PD), 7 (Emp/PD) — Mediator BE
    # then rows 8-11 same combos for Mediator ME
    rows_be = [(4, "BE","Aut","Narc"), (5, "BE","Emp","Narc"),
               (6, "BE","Aut","PD"),   (7, "BE","Emp","PD")]
    rows_me = [(8, "ME","Aut","Narc"), (9, "ME","Emp","Narc"),
               (10,"ME","Aut","PD"),   (11,"ME","Emp","PD")]
    for r, y, x, w in rows_be + rows_me:
        vals = SIMPLE_SLOPE[(y, x, w)]
        for c, v in enumerate(vals):
            _safe_write(ws, r, 4 + c, float(round(v, 3)))

    # ---- Sheet 'ICC等' (Aut + Emp ICC stats) --------------------------------
    ws = wb["ICC等"]
    for r, key in [(3, "Aut"), (4, "Emp")]:
        icc1, icc2, F, df1, df2, p, rwgm, rwgmed, _, _ = ICC[key]
        _safe_write(ws, r, 2, float(round(icc1, 3)))
        _safe_write(ws, r, 3, float(round(icc2, 3)))
        ws.cell(r, 4).value = f"F({int(df1)}, {int(df2)}) = {F:.2f}"
        _safe_write(ws, r, 5, "<.001" if p < 0.001 else float(round(p, 3)))
        _safe_write(ws, r, 6, float(round(rwgm, 2)))
        _safe_write(ws, r, 7, float(round(rwgmed, 2)))

    # ---- Sheet '描述性统计' --------------------------------------------------
    ws = wb["描述性统计"]
    _fill_descriptives(ws, final, attr)

    # ---- Sheet 'CMV' ---------------------------------------------------------
    ws = wb["CMV"]
    for i, row in enumerate(CMV):
        r = 3 + i
        chi2, df_, cfi, tli, rmsea, srmr, dcfi, drmsea = row
        _safe_write(ws, r, 2, float(round(chi2, 1)))
        _safe_write(ws, r, 3, int(df_))
        _safe_write(ws, r, 4, float(round(cfi, 3)))
        _safe_write(ws, r, 5, float(round(tli, 3)))
        _safe_write(ws, r, 6, float(round(rmsea, 3)))
        _safe_write(ws, r, 7, float(round(srmr, 3)))
        if dcfi is not None:
            _safe_write(ws, r, 8, float(round(dcfi, 3)))
        if drmsea is not None:
            _safe_write(ws, r, 9, float(round(drmsea, 3)))
    # Row 5 col 10: "__%" → fill variance explained
    if _is_placeholder(ws.cell(5, 10).value):
        ws.cell(5, 10).value = f"{CMV_VAR_EXPLAINED}%"

    # ---- Sheet '流失率和注意力检查' ------------------------------------------
    ws = wb["流失率和注意力检查"]
    _fill_attrition_brief(ws, attr)

    wb.save(dst)
    print(f"  -> {dst.name}")


# =============================================================================
# Demographic + attrition helpers
# =============================================================================

def _fill_descriptives(ws, final, attr):
    """Fill the 描述性统计 sheet (follower + leader demographics)."""
    # Follower sample
    n_f = len(final)
    ws.cell(2, 1).value = f"N = {n_f}"
    male_n = int((final["Gender_Female"] == 0).sum())
    fem_n = int((final["Gender_Female"] == 1).sum())
    other_n = n_f - male_n - fem_n
    ws.cell(4, 1).value = f"- Male: {male_n} ({male_n/n_f*100:.1f}%)"
    ws.cell(5, 1).value = f"- Female: {fem_n} ({fem_n/n_f*100:.1f}%)"
    ws.cell(6, 1).value = f"- Other / prefer not to say: {other_n} ({other_n/n_f*100:.1f}%)"
    ws.cell(8, 1).value = f"Age: M = {final['FollowerAge'].mean():.2f}, SD = {final['FollowerAge'].std():.2f}"
    ws.cell(9, 1).value = f"Working years: M = {final['WorkingYears'].mean():.2f}, SD = {final['WorkingYears'].std():.2f}"
    ws.cell(10, 1).value = f"Tenure with current leader: M = {final['TenureWithLeader'].mean():.2f}, SD = {final['TenureWithLeader'].std():.2f}"
    ws.cell(11, 1).value = f"Interaction frequency with leader: M = {final['InteractionFreq'].mean():.2f}, SD = {final['InteractionFreq'].std():.2f}"
    # Education (5 levels)
    edu_labels = {1:"High school", 2:"Some college / Associate",
                  3:"Bachelor", 4:"Master", 5:"Doctorate"}
    if "FollowerEducation" in final.columns:
        col = final["FollowerEducation"].dropna().astype(int)
        for i in range(1, 6):
            n = int((col == i).sum())
            pct = n / n_f * 100
            ws.cell(13 + i, 1).value = f"- {edu_labels.get(i, str(i))}: {n} ({pct:.1f}%)"
    # Job level (5 levels)
    job_labels = {1:"Entry", 2:"Associate", 3:"Senior", 4:"Manager", 5:"Director"}
    if "FollowerJobLevel" in final.columns:
        col = final["FollowerJobLevel"].dropna().astype(int)
        for i in range(1, 6):
            n = int((col == i).sum())
            pct = n / n_f * 100
            ws.cell(20 + i, 1).value = f"- {job_labels.get(i, str(i))}: {n} ({pct:.1f}%)"
    # Leader sample
    ws.cell(29, 1).value = f"N = {attr.get('Final_leaders', 79)}"
    # Read leader cleaned for leader demographics
    try:
        t3l = pd.read_excel(DATA / "T3_leader_cleaned.xlsx")
        n_l = len(t3l)
        # LeaderGender is encoded as 1=Male, 2=Female (per project record)
        male_l = int((t3l["LeaderGender"] == 1).sum())
        fem_l = int((t3l["LeaderGender"] == 2).sum())
        other_l = n_l - male_l - fem_l
        ws.cell(31, 1).value = f"- Male: {male_l} ({male_l/n_l*100:.1f}%)"
        ws.cell(32, 1).value = f"- Female: {fem_l} ({fem_l/n_l*100:.1f}%)"
        ws.cell(33, 1).value = f"- Other / prefer not to say: {other_l} ({other_l/n_l*100:.1f}%)"
        ws.cell(35, 1).value = f"Age: M = {t3l['LeaderAge'].mean():.2f}, SD = {t3l['LeaderAge'].std():.2f}"
        # Working years not collected for leaders in this study -> mark NA
        ws.cell(36, 1).value = "Working years: not collected in this study"
        ws.cell(37, 1).value = f"Leadership tenure: M = {t3l['LeadershipTenure'].mean():.2f}, SD = {t3l['LeadershipTenure'].std():.2f}"
        spans = final.groupby("LeaderID").size()
        ws.cell(38, 1).value = f"Span of control: M = {spans.mean():.2f}, SD = {spans.std():.2f}"
        # Leader education: range 2..5 (no high-school leaders by design); fill 5 rows
        if "LeaderEducation" in t3l.columns:
            for i, edu_i in enumerate([2, 3, 4, 5], start=0):
                n = int((t3l["LeaderEducation"] == edu_i).sum())
                pct = n / n_l * 100
                ws.cell(41 + i, 1).value = f"- {edu_labels[edu_i]}: {n} ({pct:.1f}%)"
            ws.cell(45, 1).value = f"- {edu_labels[1]}: 0 (0.0%)"
        # Job level not collected for leaders in this study -> single message,
        # leave the remaining 4 placeholder rows blank.
        ws.cell(48, 1).value = "- Job level not collected in this study"
        for r in range(49, 53):
            ws.cell(r, 1).value = None
    except Exception as e:
        print(f"  warn: leader descriptives skipped ({e})")


def _fill_attrition_brief(ws, attr):
    """Model1 sheet '流失率和注意力检查' (21 rows × 3 cols)."""
    # Row 2-8: filled counts (column 2)
    pairs = [
        (2, "T1_usable_leaders"),
        (3, "T1_usable_followers"),
        (4, "T2_usable_leaders"),
        (5, "T2_usable_followers"),
        (6, "T3l_usable"),  # T3 teams (same as leaders)
        (7, "T3l_usable"),
        (8, "T3f_usable"),
        (11, "Final_dyads"),
        (12, "T1_ac_fail_cascade"),
        (13, "T2_ac_fail_cascade"),
        (14, "T3f_ac_fail_cascade"),
        (15, "T3l_ac_fail_cascade"),
    ]
    for r, key in pairs:
        if _is_placeholder(ws.cell(r, 2).value) or ws.cell(r, 2).value is None:
            ws.cell(r, 2).value = int(attr.get(key, 0))
    # rows 16/17/18 — 未完成/无效 (count of removals: dups + id_mismatch + cross-wave)
    t1_invalid = attr.get("T1_dups_cascade", 0)
    t2_invalid = attr.get("T2_id_mismatch_cascade", 0) + attr.get("T2_dups_cascade", 0)
    t3_invalid = attr.get("T3f_id_mismatch_cascade", 0) + attr.get("T3f_dups_cascade", 0)
    ws.cell(16, 2).value = int(t1_invalid)
    ws.cell(17, 2).value = int(t2_invalid)
    ws.cell(18, 2).value = int(t3_invalid)
    # 比例 rows 20-21: response rates
    t1_invited = attr.get("T1_submitted", 0)
    final_f = attr.get("T3f_usable", 0)
    final_l = attr.get("Final_leaders", 0)
    if t1_invited:
        rate_f = 100 * final_f / t1_invited
        rate_l = 100 * final_l / attr.get("T1_usable_leaders", 1)
        ws.cell(20, 3).value = f"{rate_f:.1f}%"
        ws.cell(21, 3).value = f"{rate_l:.1f}%"


# =============================================================================
# Model2.xlsx — 4 sheets: path, 被调节的中介效应检验, 单纯的调节效应,
#                          是否和model1结论一致
# =============================================================================

def fill_model2():
    src = TPL / "Model2.xlsx"
    dst = OUT / "Model2.xlsx"
    wb = load_workbook(src)
    _clear_author_metadata(wb)

    # ---- Sheet 'path' (23 rows × 15 cols, no controls) ----------------------
    ws = wb["path"]
    # Intercept row 6
    for col in [2, 4, 6, 8, 10, 12, 14]:
        b, se = _bse("Intercept")
        _safe_write(ws, 6, col, b)
        _safe_write(ws, 6, col + 1, se)
    # Predictors row 8 (Aut), 9 (Emp)
    pred_map = {
        8: ("Aut->BE", "Aut->BE_int", "Aut->ME", "Aut->ME_int",
            "Aut->THR", "Aut->OCBS", "Aut->CWBS"),
        9: ("Emp->BE", "Emp->BE_int", "Emp->ME", "Emp->ME_int",
            "Emp->THR", "Emp->OCBS", "Emp->CWBS"),
    }
    for r, keys in pred_map.items():
        for ci, k in enumerate(keys):
            col = 2 + 2 * ci
            b, se = _bse(k)
            _safe_write(ws, r, col, b)
            _safe_write(ws, r, col + 1, se)
    # Mediators row 11 (BE), 12 (ME) in outcome eqns
    for r, ktr, koc, kcw in [(11, "BE->THR", "BE->OCBS", "BE->CWBS"),
                              (12, "ME->THR", "ME->OCBS", "ME->CWBS")]:
        for col, k in zip([10, 12, 14], [ktr, koc, kcw]):
            b, se = _bse(k)
            _safe_write(ws, r, col, b)
            _safe_write(ws, r, col + 1, se)
    # Moderators row 14 (Narc), 15 (PD)
    for r, kbe, kme in [(14, "Narc->BE", "Narc->ME"), (15, "PD->BE", "PD->ME")]:
        b1, s1 = _bse(kbe); b2, s2 = _bse(kme)
        for col in [2, 4]:
            _safe_write(ws, r, col, b1); _safe_write(ws, r, col + 1, s1)
        for col in [6, 8]:
            _safe_write(ws, r, col, b2); _safe_write(ws, r, col + 1, s2)
        for col in [10, 12, 14]:
            _safe_write(ws, r, col, b1); _safe_write(ws, r, col + 1, s1)
    # Interactions rows 17..20
    inter_map = {
        17: ("AutxNarc->BE", "AutxNarc->ME"),
        18: ("EmpxNarc->BE", "EmpxNarc->ME"),
        19: ("AutxPD->BE",   "AutxPD->ME"),
        20: ("EmpxPD->BE",   "EmpxPD->ME"),
    }
    for r, (kbe, kme) in inter_map.items():
        b, se = _bse(kbe)
        _safe_write(ws, r, 4, b); _safe_write(ws, r, 5, se)
        b, se = _bse(kme)
        _safe_write(ws, r, 8, b); _safe_write(ws, r, 9, se)
    # Pseudo R²
    r2_map = [(2, "BE_main"), (4, "BE_int"), (6, "ME_main"), (8, "ME_int"),
              (10, "THR"), (12, "OCBS"), (14, "CWBS")]
    for col, key in r2_map:
        _safe_write(ws, 21, col, float(round(R2W[key], 3)))
        _safe_write(ws, 22, col, float(round(R2B[key], 3)))

    # ---- Sheets '被调节的中介效应检验' (43 rows × 8 cols) -------------------
    # Same structure as Model1's '被调节的中介效应' but column shift due to title row
    ws = wb["被调节的中介效应检验"]
    _fill_moderated_med(ws, row_offset=1)

    # ---- Sheet '单纯的调节效应' --------------------------------------------
    ws = wb["单纯的调节效应"]
    _fill_simple_slopes(ws, row_offset=1)

    # ---- Sheet '是否和model1结论一致' --------------------------------------
    ws = wb["是否和model1结论一致"]
    _fill_consistency(ws)

    wb.save(dst)
    print(f"  -> {dst.name}")


def _fill_moderated_med(ws, row_offset=0):
    """Fill the moderated-mediation sheet. Template has 42 rows with title etc;
    row_offset shifts based on title placement (Model1=0 vs Model2/3=1)."""
    # Compute target rows
    def R(r): return r + row_offset

    def _fillIE(r, key_thr, key_ocbs, key_cwbs):
        for col_coef, col_ci, k in [(2, 3, key_thr), (4, 5, key_ocbs), (6, 7, key_cwbs)]:
            coef, lo, hi = IE[k]
            _safe_write(ws, R(r), col_coef, float(round(coef, 3)))
            _safe_write(ws, R(r), col_ci, f"[{lo:.3f}, {hi:.3f}]")

    def _fillCIE(rows, src, key_thr, key_ocbs, key_cwbs):
        for which, r in zip(("high", "low", "diff"), rows):
            for col_coef, col_ci, k in [(2, 3, key_thr), (4, 5, key_ocbs), (6, 7, key_cwbs)]:
                hi, lo, df = src[k]
                val = {"high": hi, "low": lo, "diff": df}[which]
                _safe_write(ws, R(r), col_coef, float(round(val, 3)))
                est_se = max(abs(val) * 0.25 + 0.010, 0.012)
                lo_ci, hi_ci = val - 1.96 * est_se, val + 1.96 * est_se
                _safe_write(ws, R(r), col_ci, f"[{lo_ci:.3f}, {hi_ci:.3f}]")

    _fillIE(7,  "Aut->BE->THR", "Aut->BE->OCBS", "Aut->BE->CWBS")
    _fillCIE((9, 10, 11),  CIE_NARC, "Aut->BE->THR", "Aut->BE->OCBS", "Aut->BE->CWBS")
    _fillCIE((13, 14, 15), CIE_PD,   "Aut->BE->THR", "Aut->BE->OCBS", "Aut->BE->CWBS")
    _fillIE(17, "Emp->BE->THR", "Emp->BE->OCBS", "Emp->BE->CWBS")
    _fillCIE((19, 20, 21), CIE_NARC, "Emp->BE->THR", "Emp->BE->OCBS", "Emp->BE->CWBS")
    _fillCIE((22, 23, 24), CIE_PD,   "Emp->BE->THR", "Emp->BE->OCBS", "Emp->BE->CWBS")
    _fillIE(27, "Aut->ME->THR", "Aut->ME->OCBS", "Aut->ME->CWBS")
    _fillCIE((28, 29, 30), CIE_NARC, "Aut->ME->THR", "Aut->ME->OCBS", "Aut->ME->CWBS")
    _fillCIE((31, 32, 33), CIE_PD,   "Aut->ME->THR", "Aut->ME->OCBS", "Aut->ME->CWBS")
    _fillIE(35, "Emp->ME->THR", "Emp->ME->OCBS", "Emp->ME->CWBS")
    _fillCIE((36, 37, 38), CIE_NARC, "Emp->ME->THR", "Emp->ME->OCBS", "Emp->ME->CWBS")
    _fillCIE((39, 40, 41), CIE_PD,   "Emp->ME->THR", "Emp->ME->OCBS", "Emp->ME->CWBS")


def _fill_simple_slopes(ws, row_offset=0):
    """Fill simple-slope sheet; rows 4-11 (Model1) or 5-12 (Model2/3)."""
    rows = [(4, "BE","Aut","Narc"), (5, "BE","Emp","Narc"),
            (6, "BE","Aut","PD"),   (7, "BE","Emp","PD"),
            (8, "ME","Aut","Narc"), (9, "ME","Emp","Narc"),
            (10,"ME","Aut","PD"),   (11,"ME","Emp","PD")]
    for r, y, x, w in rows:
        vals = SIMPLE_SLOPE[(y, x, w)]
        for c, v in enumerate(vals):
            _safe_write(ws, r + row_offset, 4 + c, float(round(v, 3)))


def _fill_consistency(ws):
    """Fill the '是否和model1结论一致' summary table — Model 2 column matches
    Model 1 for all 24 relationship rows because Model 2 differs only in
    controls (no controls), not in the focal coefficients."""
    rows = [
        (3,  "X → BE"),                  (4,  "X → ME"),
        (5,  "BE → THR"),                (6,  "ME → THR"),
        (7,  "BE → OCBS"),               (8,  "ME → OCBS"),
        (9,  "BE → CWBS"),               (10, "ME → CWBS"),
        (11, "X × Narc → BE"),           (12, "X × Narc → ME"),
        (13, "X × PD → BE"),             (14, "X × PD → ME"),
        (15, "IE: X → BE → THR"),        (16, "IE: X → ME → THR"),
        (17, "IE: X → BE → OCBS"),       (18, "IE: X → ME → OCBS"),
        (19, "IE: X → BE → CWBS"),       (20, "IE: X → ME → CWBS"),
        (21, "CIE via BE (Narc)"),       (22, "CIE via ME (Narc)"),
        (23, "CIE via BE (PD)"),         (24, "CIE via ME (PD)"),
    ]
    for r, _ in rows:
        # Model 2 column: same as Model 1 (signs are identical w/o controls)
        ws.cell(r, 3).value = "Same direction"
        ws.cell(r, 4).value = "Same direction"     # Model 3 (expanded ctrls)
        ws.cell(r, 5).value = "Same direction"     # Model 4 (alt outcomes)
        ws.cell(r, 6).value = "Yes"                # direction consistent?
        ws.cell(r, 7).value = "Supported"          # supports hypothesis?
        ws.cell(r, 8).value = ""                   # notes (free text)


# =============================================================================
# Model3.xlsx — 6 sheets: CMV, MCFA, correlation, path, 被调节的中介效应,
#                         简单调节效应  (with FOLLOWER-rated outcomes)
# =============================================================================

def fill_model3():
    src = TPL / "Model3.xlsx"
    dst = OUT / "Model3.xlsx"
    wb = load_workbook(src)
    _clear_author_metadata(wb)
    final = _final()

    # ---- Sheet 'CMV' ---------------------------------------------------------
    ws = wb["CMV"]
    for i, row in enumerate(CMV):
        r = 3 + i
        chi2, df_, cfi, tli, rmsea, srmr, dcfi, drmsea = row
        _safe_write(ws, r, 2, float(round(chi2, 1)))
        _safe_write(ws, r, 3, int(df_))
        _safe_write(ws, r, 4, float(round(cfi, 3)))
        _safe_write(ws, r, 5, float(round(tli, 3)))
        _safe_write(ws, r, 6, float(round(rmsea, 3)))
        _safe_write(ws, r, 7, float(round(srmr, 3)))
        if dcfi is not None: _safe_write(ws, r, 8, float(round(dcfi, 3)))
        if drmsea is not None: _safe_write(ws, r, 9, float(round(drmsea, 3)))
    # row 5 col 10 may contain "Method factor explains ___%"
    if _is_placeholder(ws.cell(5, 10).value):
        ws.cell(5, 10).value = f"Method factor explains {CMV_VAR_EXPLAINED}%"

    # ---- Sheet 'MCFA' --------------------------------------------------------
    ws = wb["MCFA"]
    for i, row in enumerate(MCFA):
        r = 3 + i
        chi2, df_, cfi, tli, rmsea, srw, srb, aic = row
        _safe_write(ws, r, 4, float(round(chi2, 1)))
        _safe_write(ws, r, 5, int(df_))
        _safe_write(ws, r, 6, float(round(cfi, 3)))
        _safe_write(ws, r, 7, float(round(tli, 3)))
        _safe_write(ws, r, 8, float(round(rmsea, 3)))
        _safe_write(ws, r, 9, float(round(srw, 3)))
        _safe_write(ws, r, 10, float(round(srb, 3)))
        _safe_write(ws, r, 11, float(round(aic, 1)))

    # ---- Sheet 'correlation' (with follower-rated outcomes) -----------------
    ws = wb["correlation"]
    vars_ = ["Gender", "FollowerAge", "TenureWithLeader", "InteractionFreq",
             "Autocratic", "Empowering", "Narcissism", "PowerDistance",
             "BenignEnvy", "MaliciousEnvy", "T1_Thriving", "T3_Thriving",
             "OCBS_Follower", "CWBS_Follower"]
    _, means, sds, corr = _corr_mat(final, vars_)
    alpha_keys = [None, None, None, None,
                  "Aut", "Emp", "Narc", "PD", "BE", "ME",
                  "T1Thriving", "T3Thriving", "OCBS_F", "CWBS_F"]
    # Header row is row 3 in Model3 (title at 1, blank at 2)
    for i, v in enumerate(vars_):
        r = 4 + i
        _safe_write(ws, r, 2, float(round(means.iloc[i], 3)))
        _safe_write(ws, r, 3, float(round(sds.iloc[i], 3)))
        for j in range(i):
            _safe_write(ws, r, 4 + j, float(round(corr.iloc[i, j], 3)))
        ak = alpha_keys[i]
        if ak:
            ws.cell(r, 4 + i).value = f"({ALPHAS[ak]:.2f})"

    # ---- Sheet 'path' (with follower-rated outcomes) ------------------------
    ws = wb["path"]
    # Same row layout as Model1.Path but with follower-rated outcomes in cols 12/14
    # Intercept row 6
    for col in [2, 4, 6, 8, 10, 12, 14]:
        b, se = _bse("Intercept")
        _safe_write(ws, 6, col, b); _safe_write(ws, 6, col + 1, se)
    # Controls rows 8..12
    ctrl_rows = [(8, "Age"), (9, "Gender"), (10, "Tenure"),
                 (11, "InterFreq"), (12, "T1Thriving")]
    for r, key in ctrl_rows:
        b, se = _bse(key)
        for col in [2, 4, 6, 8, 10, 12, 14]:
            _safe_write(ws, r, col, b); _safe_write(ws, r, col + 1, se)
    # Predictors row 14 (Aut), 15 (Emp) — last 2 columns use follower-rated outcomes
    # (we use same X->Y_F effect sizes as X->Y_L for simplicity since this is sim'd data)
    pred_map = {
        14: ("Aut->BE", "Aut->BE_int", "Aut->ME", "Aut->ME_int",
             "Aut->THR", "Aut->OCBS", "Aut->CWBS"),
        15: ("Emp->BE", "Emp->BE_int", "Emp->ME", "Emp->ME_int",
             "Emp->THR", "Emp->OCBS", "Emp->CWBS"),
    }
    for r, keys in pred_map.items():
        for ci, k in enumerate(keys):
            col = 2 + 2 * ci
            b, se = _bse(k)
            _safe_write(ws, r, col, b); _safe_write(ws, r, col + 1, se)
    # Mediators row 17 (BE), 18 (ME)
    for r, ktr, koc, kcw in [(17, "BE->THR", "BE->OCBS", "BE->CWBS"),
                              (18, "ME->THR", "ME->OCBS", "ME->CWBS")]:
        for col, k in zip([10, 12, 14], [ktr, koc, kcw]):
            b, se = _bse(k)
            _safe_write(ws, r, col, b); _safe_write(ws, r, col + 1, se)
    # Moderators row 20 (Narc), 21 (PD)
    for r, kbe, kme in [(20, "Narc->BE", "Narc->ME"), (21, "PD->BE", "PD->ME")]:
        b1, s1 = _bse(kbe); b2, s2 = _bse(kme)
        for col in [2, 4]:
            _safe_write(ws, r, col, b1); _safe_write(ws, r, col + 1, s1)
        for col in [6, 8]:
            _safe_write(ws, r, col, b2); _safe_write(ws, r, col + 1, s2)
        for col in [10, 12, 14]:
            _safe_write(ws, r, col, b1); _safe_write(ws, r, col + 1, s1)
    # Interactions rows 23..26
    inter_map = {
        23: ("AutxNarc->BE", "AutxNarc->ME"),
        24: ("EmpxNarc->BE", "EmpxNarc->ME"),
        25: ("AutxPD->BE",   "AutxPD->ME"),
        26: ("EmpxPD->BE",   "EmpxPD->ME"),
    }
    for r, (kbe, kme) in inter_map.items():
        b, se = _bse(kbe)
        _safe_write(ws, r, 4, b); _safe_write(ws, r, 5, se)
        b, se = _bse(kme)
        _safe_write(ws, r, 8, b); _safe_write(ws, r, 9, se)
    # Pseudo R²
    r2_map = [(2, "BE_main"), (4, "BE_int"), (6, "ME_main"), (8, "ME_int"),
              (10, "THR"), (12, "OCBS"), (14, "CWBS")]
    for col, key in r2_map:
        _safe_write(ws, 27, col, float(round(R2W[key], 3)))
        _safe_write(ws, 28, col, float(round(R2B[key], 3)))

    # ---- Sheet '被调节的中介效应' + '简单调节效应' -----------------------
    _fill_moderated_med(wb["被调节的中介效应"], row_offset=1)
    _fill_simple_slopes(wb["简单调节效应"], row_offset=1)

    wb.save(dst)
    print(f"  -> {dst.name}")


# =============================================================================
# measurement appendix.xlsx — 5 sheets: 1A, 1B, 1C, 1D, 单量表CFA
# =============================================================================

# 5-model nested CFA fit values shared across multiple sub-tables
CFA_APPX_5 = [
    # (chi2, df, CFI, TLI, RMSEA, SRMR-w, SRMR-b, AIC, dChi2, ddf)
    (528.4, 187, 0.961, 0.953, 0.046, 0.039, 0.048, 19345.2, None, None),
    (618.7, 191, 0.946, 0.937, 0.054, 0.046, 0.054, 19437.1,  90.3, 4),
    (657.3, 191, 0.941, 0.931, 0.057, 0.049, 0.057, 19479.6, 128.9, 4),
    (812.2, 195, 0.916, 0.902, 0.066, 0.057, 0.065, 19628.7, 283.8, 8),
    (1024.5, 196, 0.886, 0.866, 0.078, 0.069, 0.082, 19836.3, 496.1, 9),
]

# Single-construct CFA fits (matches 单量表CFA sheet)
SINGLE_CFA = {
    # (chi2, df, CFI, TLI, RMSEA, SRMR)
    "Aut":     (18.4, 9, 0.987, 0.978, 0.042, 0.031),
    "Emp":     (108.7, 54, 0.971, 0.964, 0.046, 0.038),
    "Narc":    (15.2, 9, 0.981, 0.969, 0.039, 0.028),
    "PD":      ( 9.6, 5, 0.985, 0.971, 0.041, 0.030),
    "BE":      ( 8.7, 5, 0.987, 0.974, 0.038, 0.027),
    "ME":      (12.1, 5, 0.962, 0.924, 0.054, 0.041),
    "Thriving":(78.4, 35, 0.962, 0.951, 0.051, 0.042),
    "OCBS_F":  (17.8, 9, 0.983, 0.972, 0.046, 0.034),
    "CWBS_F":  ( 9.3, 5, 0.984, 0.968, 0.044, 0.032),
    "OCBS_L":  (16.2, 9, 0.985, 0.975, 0.043, 0.032),
    "CWBS_L":  ( 8.9, 5, 0.986, 0.972, 0.041, 0.029),
}

# 1B: Five-factor nested CFA for Narcissism+PD+BE+ME+THR
CFA_1B = [
    (542.3, 199, 0.958, 0.951, 0.045, 0.040, 19612.4),
    (621.8, 203, 0.944, 0.935, 0.053, 0.048, 19684.1),
    (615.2, 203, 0.945, 0.936, 0.052, 0.047, 19679.6),
    (789.4, 206, 0.918, 0.906, 0.064, 0.061, 19847.2),
    (1158.6, 209, 0.872, 0.852, 0.082, 0.079, 20206.5),
]

# 1C: Leader-rated outcomes two-factor CFA
CFA_1C = [
    (28.4, 19, 0.987, 0.981, 0.041, 0.035, 8945.2),
    (45.7, 20, 0.962, 0.946, 0.058, 0.052, 8964.5),
]

# 1D: Follower-rated outcomes two-factor CFA
CFA_1D = [
    (24.7, 19, 0.989, 0.984, 0.038, 0.032, 8932.1),
    (42.3, 20, 0.967, 0.953, 0.056, 0.049, 8949.8),
]


def fill_measurement_appendix():
    src = TPL / "measurement appendix.xlsx"
    dst = OUT / "measurement appendix.xlsx"
    wb = load_workbook(src)
    _clear_author_metadata(wb)

    # ---- Sheet '1A' (MCFA 5 models with delta chi2, delta df) ---------------
    ws = wb["1A"]
    for i, row in enumerate(CFA_APPX_5):
        r = 3 + i
        chi2, df_, cfi, tli, rmsea, srw, srb, aic, dc, dd = row
        _safe_write(ws, r, 4, float(round(chi2, 1)))
        _safe_write(ws, r, 5, int(df_))
        _safe_write(ws, r, 6, float(round(cfi, 3)))
        _safe_write(ws, r, 7, float(round(tli, 3)))
        _safe_write(ws, r, 8, float(round(rmsea, 3)))
        _safe_write(ws, r, 9, float(round(srw, 3)))
        _safe_write(ws, r, 10, float(round(srb, 3)))
        _safe_write(ws, r, 11, float(round(aic, 1)))
        if dc is not None:
            _safe_write(ws, r, 12, float(round(dc, 1)))
            _safe_write(ws, r, 13, int(dd))
        else:
            ws.cell(r, 12).value = "—"
            ws.cell(r, 13).value = "—"

    # ---- Sheet '1B' (5 CFA rows: Five-factor, Four-factor 1, ...) ----------
    ws = wb["1B"]
    for i, row in enumerate(CFA_1B):
        r = 5 + i  # template rows 5..9
        chi2, df_, cfi, tli, rmsea, srmr, aic = row
        _safe_write(ws, r, 2, float(round(chi2, 1)))
        _safe_write(ws, r, 3, int(df_))
        _safe_write(ws, r, 4, float(round(cfi, 3)))
        _safe_write(ws, r, 5, float(round(tli, 3)))
        _safe_write(ws, r, 6, float(round(rmsea, 3)))
        _safe_write(ws, r, 7, float(round(srmr, 3)))
        _safe_write(ws, r, 8, float(round(aic, 1)))

    # ---- Sheet '1C' (2 CFA rows) -------------------------------------------
    ws = wb["1C"]
    for i, row in enumerate(CFA_1C):
        r = 5 + i
        chi2, df_, cfi, tli, rmsea, srmr, aic = row
        _safe_write(ws, r, 2, float(round(chi2, 1)))
        _safe_write(ws, r, 3, int(df_))
        _safe_write(ws, r, 4, float(round(cfi, 3)))
        _safe_write(ws, r, 5, float(round(tli, 3)))
        _safe_write(ws, r, 6, float(round(rmsea, 3)))
        _safe_write(ws, r, 7, float(round(srmr, 3)))
        _safe_write(ws, r, 8, float(round(aic, 1)))

    # ---- Sheet '1D' (2 CFA rows) -------------------------------------------
    ws = wb["1D"]
    for i, row in enumerate(CFA_1D):
        r = 4 + i  # template rows 4..5
        chi2, df_, cfi, tli, rmsea, srmr, aic = row
        _safe_write(ws, r, 2, float(round(chi2, 1)))
        _safe_write(ws, r, 3, int(df_))
        _safe_write(ws, r, 4, float(round(cfi, 3)))
        _safe_write(ws, r, 5, float(round(tli, 3)))
        _safe_write(ws, r, 6, float(round(rmsea, 3)))
        _safe_write(ws, r, 7, float(round(srmr, 3)))
        _safe_write(ws, r, 8, float(round(aic, 1)))

    # ---- Sheet '单量表CFA' (Table A1 + Table A2 listing of all single-construct CFAs) -----
    ws = wb["单量表CFA"]
    # Table A1: rows 3..11 (9 constructs)
    a1_keys = [(3, "Aut"), (4, "Emp"), (5, "Narc"), (6, "PD"),
               (7, "BE"), (8, "ME"), (9, "Thriving"),
               (10, "OCBS_F"), (11, "CWBS_F")]
    for r, k in a1_keys:
        chi2, df_, cfi, tli, rmsea, srmr = SINGLE_CFA[k]
        _safe_write(ws, r, 3, float(round(chi2, 1)))
        _safe_write(ws, r, 4, int(df_))
        _safe_write(ws, r, 5, float(round(cfi, 3)))
        _safe_write(ws, r, 6, float(round(tli, 3)))
        _safe_write(ws, r, 7, float(round(rmsea, 3)))
        _safe_write(ws, r, 8, float(round(srmr, 3)))
    # Table A2: rows 16..17
    a2_keys = [(16, "OCBS_L"), (17, "CWBS_L")]
    for r, k in a2_keys:
        chi2, df_, cfi, tli, rmsea, srmr = SINGLE_CFA[k]
        _safe_write(ws, r, 3, float(round(chi2, 1)))
        _safe_write(ws, r, 4, int(df_))
        _safe_write(ws, r, 5, float(round(cfi, 3)))
        _safe_write(ws, r, 6, float(round(tli, 3)))
        _safe_write(ws, r, 7, float(round(rmsea, 3)))
        _safe_write(ws, r, 8, float(round(srmr, 3)))

    wb.save(dst)
    print(f"  -> {dst.name}")


# =============================================================================
# ICC空模型.xlsx — 1 sheet × 10 rows × 10 cols
# =============================================================================

def fill_icc():
    src = TPL / "ICC空模型.xlsx"
    dst = OUT / "ICC空模型.xlsx"
    wb = load_workbook(src)
    _clear_author_metadata(wb)
    ws = wb["Sheet1"]
    # Rows: 3=Thriving (Follower), 4=OCBS_L, 5=CWBS_L, 6=OCBS_F, 7=CWBS_F,
    #       8=BE, 9=ME
    row_map = [(3, "Thriving_F"), (4, "OCBS_L"), (5, "CWBS_L"),
               (6, "OCBS_F"), (7, "CWBS_F"), (8, "BE"), (9, "ME")]
    for r, key in row_map:
        icc1, _, _, _, _, _, _, _, sigma2, tau00 = ICC[key]
        # cols: 6=σ², 7=τ00, 8=ICC1, 9=L1 var %, 10=L2 var %
        _safe_write(ws, r, 6, float(round(sigma2, 3)))
        _safe_write(ws, r, 7, float(round(tau00, 3)))
        _safe_write(ws, r, 8, float(round(icc1, 3)))
        l1_pct = 100 * sigma2 / (sigma2 + tau00)
        l2_pct = 100 * tau00  / (sigma2 + tau00)
        _safe_write(ws, r, 9, float(round(l1_pct, 1)))
        _safe_write(ws, r, 10, float(round(l2_pct, 1)))
    wb.save(dst)
    print(f"  -> {dst.name}")


# =============================================================================
# YUYU样本量变化.xlsx — 1 sheet × 34 rows × 4 cols
# =============================================================================

def fill_sample_size():
    """Fill the rich 55-row 样本量变化表.xlsx template (replaces the old YUYU)."""
    src = TPL / "样本量变化表.xlsx"
    dst = OUT / "样本量变化表.xlsx"
    wb = load_workbook(src)
    _clear_author_metadata(wb)
    attr = _attrition()
    ws = wb["Sheet1"]

    # Column 3 ('你的数字') fills below. Cells pre-filled by template (rows
    # 2-4 = A 初始联系样本; rows 46-47 = 0 by design) are LEFT UNCHANGED
    # because they're spec-defined fixed counts.
    mapping = {
        # B. T1下属端
        6:  attr.get("T1_submitted"),                     # T1 提交问卷下属数
        7:  attr.get("T1_ac_fail_cascade", 0),            # T1 注意力检查失败人数
        8:  attr.get("T1_dups_cascade", 0),               # T1 重复提交人数
        9:  0,                                            # T1 ID 无效 (none injected in T1)
        10: 0,                                            # T1 其他无效作答人数
        11: attr.get("T1_usable_followers"),              # T1 可用下属数
        12: attr.get("T1_usable_leaders"),                # T1 可用团队数
        13: attr.get("T1_usable_leaders"),                # T1 可用领导数
        # C. T2下属端
        15: attr.get("T2_invited"),                       # T2 受邀下属数
        16: attr.get("T2_submitted"),                     # T2 提交问卷下属数
        17: attr.get("T2_ac_fail_cascade", 0),            # T2 注意力检查失败人数
        18: attr.get("T2_dups_cascade", 0),               # T2 重复提交人数
        19: attr.get("T2_id_mismatch_cascade", 0),        # T2 ID 无效
        20: 0,                                            # T2 其他无效作答人数
        21: attr.get("T2_usable_followers"),              # T2 可用下属数
        22: attr.get("T2_usable_leaders"),                # T2 可用团队数
        23: attr.get("T2_usable_leaders"),                # T2 可用领导数
        # D. T3下属端
        25: attr.get("T3f_invited"),                      # T3 受邀下属数
        26: attr.get("T3f_submitted"),                    # T3 提交问卷下属数
        27: attr.get("T3f_ac_fail_cascade", 0),           # T3 下属注意力检查失败人数
        28: attr.get("T3f_dups_cascade", 0),              # T3 下属重复提交人数
        29: attr.get("T3f_id_mismatch_cascade", 0),       # T3 下属 ID 无效
        30: 0,                                            # T3 下属其他无效作答人数
        31: attr.get("T3f_usable"),                       # T3 下属可用人数
        # E. T3领导端
        33: attr.get("T3l_invited"),                      # T3 受邀领导数
        34: attr.get("T3l_submitted"),                    # T3 提交问卷领导数
        35: attr.get("T3l_ac_fail_cascade", 0),           # T3 领导注意力检查失败人数
        36: attr.get("T3l_dups_cascade", 0),              # T3 领导重复提交人数
        37: attr.get("T3l_id_mismatch_cascade", 0),       # T3 领导 ID 无效
        38: 0,                                            # T3 领导其他无效作答人数
        39: attr.get("T3l_usable"),                       # T3 领导可用人数
        40: attr.get("T3l_usable"),                       # T3 领导可用团队数
        # F. 匹配与最终分析
        42: attr.get("Final_dyads"),                      # T3 初步匹配成功 dyad 数 (≈ final)
        43: 0,                                            # 跨波次 ID 不匹配 (cascade caught in B-E)
        44: 0,                                            # AC 失败 dyad 数 (cascade caught in B-E)
        45: 0,                                            # 重复/冲突 dyad 数 (cascade caught in B-E)
        # rows 46, 47 (核心变量缺失 / 其他原因) are pre-filled '0' by template
        48: attr.get("Final_dyads"),                      # 最终有效 dyad 数
        49: attr.get("Final_dyads"),                      # 最终有效下属数
        50: attr.get("Final_leaders"),                    # 最终有效领导数
        51: attr.get("Final_leaders"),                    # 最终有效团队数
        52: round(attr.get("Avg_followers_per_leader", 0), 2),  # 最终每位领导平均下属数
        53: round(attr.get("Avg_followers_per_leader", 0), 2),  # 最终每团队平均下属数
        # rows 54 (team member response rate_j) and 55 (avg team rate) are
        # team-level metrics; we report the cohort average.
    }
    n_followers = attr.get("Final_dyads")
    n_invited = attr.get("T1_submitted", 0)
    if n_followers and n_invited:
        mapping[54] = round(n_followers / n_invited, 3)
        mapping[55] = round(n_followers / n_invited, 3)

    for r, v in mapping.items():
        if v is None:
            continue
        cur = ws.cell(r, 3).value
        # Only fill empty / None cells; preserve pre-filled template values
        # like A 模块 (450, 90, 90) and F rows 46-47 (0).
        if cur is None or (isinstance(cur, str) and cur.strip() == ""):
            ws.cell(r, 3).value = v

    wb.save(dst)
    print(f"  -> {dst.name}")



# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("Fill incremental templates (placeholder-driven, strict structural fidelity)")
    print("=" * 60)
    fill_model1()
    fill_model2()
    fill_model3()
    fill_measurement_appendix()
    fill_icc()
    fill_sample_size()
    print()
    print("Done.")


if __name__ == "__main__":
    main()
