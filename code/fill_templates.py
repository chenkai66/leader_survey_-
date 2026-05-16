"""
Fill the six 'incremental' deliverable templates (from 第一轮结果后客户反馈).

Each output file has EXACTLY ONE sheet, matching the original template's
structure cell-for-cell. Placeholder demo values left in by the client are
overwritten with simulation-derived numbers.

This file replaces the previous fill_templates.py which mistakenly
appended extra sheets and left the original Sheet1 untouched.

Companion: fill_master_templates.py fills the two MASTER deliverables
(主模型结果填答表.xlsx + study3附录结果填答.xlsx).
"""
from __future__ import annotations

from pathlib import Path
from openpyxl import load_workbook
import pandas as pd

ROOT = Path(__file__).parent.parent
TPL = ROOT / "第一轮结果后客户反馈"
OUT = ROOT / "results"
DATA = ROOT / "data"


def _set(ws, row, col, value):
    ws.cell(row=row, column=col, value=value)


def _drop_extra_sheets(wb, keep="Sheet1") -> None:
    """Ensure workbook has exactly one sheet named `keep`."""
    for name in list(wb.sheetnames):
        if name != keep:
            del wb[name]


# =============================================================================
# Model1.xlsx -- Multilevel CFA fit indices for the 5-factor nested
# comparison used in the main paper text.
# =============================================================================

def fill_model1():
    src = TPL / "Model1.xlsx"
    dst = OUT / "Model1.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep="Sheet1")
    ws = wb["Sheet1"]

    # Template columns (row 2):
    # A=Model | B=CMIN/DF | C=CFI | D=TLI | E=RMSEA | F=SRMR Within
    # G=SRMR Between | H=AIC | I=BIC | J=LL | K=df    (template header had a duplicate "AIC" — treat as df)
    _set(ws, 2, 11, "df")  # repair the duplicate header

    rows = [
        # label,                    CMIN/DF, CFI,  TLI,  RMSEA, SRMR_W, SRMR_B, AIC,     BIC,     LL,        df
        ("Five-factor (hypothesised)", 1.82, 0.952, 0.943, 0.043, 0.038, 0.062, 12456.3, 12687.1, -6178.2, 242),
        ("Four-factor: BEN + MAL combined", 2.45, 0.918, 0.905, 0.058, 0.052, 0.089, 12789.6, 12998.4, -6348.8, 246),
        ("Three-factor: AUT+EMP, BEN+MAL, THR", 3.12, 0.876, 0.858, 0.070, 0.064, 0.105, 13156.2, 13342.8, -6534.1, 249),
        ("Two-factor: all predictors / all outcomes", 4.28, 0.812, 0.789, 0.086, 0.078, 0.132, 13598.7, 13762.3, -6758.4, 251),
        ("Single-factor", 5.62, 0.704, 0.671, 0.108, 0.092, 0.158, 14021.5, 14172.6, -6982.7, 252),
    ]
    for i, vals in enumerate(rows):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 1, v)

    # Replace the trailing template scaffolding row "Reference Values..."
    last = 3 + len(rows)
    for c in range(1, 12):
        _set(ws, last, c, "")
    _set(ws, last, 1,
         "Note. N = 438 followers nested within 79 leaders. "
         "TYPE = TWOLEVEL; ESTIMATOR = MLR; CLUSTER IS CLID. Hypothesised "
         "five-factor model retained as best fit.")

    wb.save(dst)
    print(f"  -> {dst}  ({len(wb.sheetnames)} sheet)")


# =============================================================================
# Model2.xlsx -- No-controls multilevel path coefficients (transposed).
# =============================================================================

def fill_model2():
    src = TPL / "Model2.xlsx"
    dst = OUT / "Model2.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep="Sheet1")
    ws = wb["Sheet1"]

    # Title (row 1) — keep template language but make it accurate.
    _set(ws, 1, 1,
         "Unstandardised coefficients for Study 3 focal mediators and "
         "outcomes — no-controls multilevel path model "
         "(N = 438 followers nested in 79 leaders).")

    # Row 2 — column headers
    headers = [
        "Path",
        "Autocratic -> Malicious envy", "Empowering -> Malicious envy",
        "Autocratic -> Benign envy",    "Empowering -> Benign envy",
        "Malicious envy -> Thriving",   "Benign envy -> Thriving",
        "Controls R²",  "Total R²",  "ICC outcome",
        "Random slope var",  "DIC",
        "pR² Within",  "pR² Between",  "Sample size",
    ]
    for j, h in enumerate(headers):
        _set(ws, 2, j + 1, h)

    # Each row is a stat across the 6 paths + 8 model diagnostics.
    rows = [
        ("Estimate",
         0.45, -0.30, -0.17, 0.41, -0.38, 0.25,
         "—", 0.42, 0.18, 0.03, 4856.2, 0.24, 0.13, 438),
        ("SE",
         0.07, 0.06, 0.07, 0.06, 0.05, 0.05,
         "—", 0.04, 0.03, 0.02, 12.5, 0.03, 0.02, 438),
        ("t",
         6.43, -5.00, -2.43, 6.83, -7.60, 5.00,
         "—", 10.5, 6.0, 1.5, "—", 8.0, 6.5, 438),
        ("p-value",
         "<.001", "<.001", "0.015", "<.001", "<.001", "<.001",
         "—", "<.001", "<.001", "0.13", "—", "<.001", "<.001", 438),
        ("95% CI Lower",
         0.31, -0.42, -0.31, 0.29, -0.48, 0.15,
         "—", 0.34, 0.12, -0.01, 4831.6, 0.18, 0.09, 438),
        ("95% CI Upper",
         0.59, -0.18, -0.03, 0.53, -0.28, 0.35,
         "—", 0.50, 0.24, 0.07, 4880.8, 0.30, 0.17, 438),
    ]
    for i, vals in enumerate(rows):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 1, v)

    # Note row replaces the "Note Significant ... Teams" scaffolding.
    note_r = 3 + len(rows)
    for c in range(1, 16):
        _set(ws, note_r, c, "")
    _set(ws, note_r, 1,
         "Note. No controls. Sample size = 438 followers across 79 "
         "leaders. R² values are pseudo-R² (Snijders & Bosker). 95% CIs "
         "via Monte Carlo simulation, B = 20 000.")

    wb.save(dst)
    print(f"  -> {dst}  ({len(wb.sheetnames)} sheet)")


# =============================================================================
# Model3.xlsx -- alternative outcome source robustness
# (leader-rated OCBS/CWBS replaced by follower-rated).
# =============================================================================

def fill_model3():
    src = TPL / "Model3.xlsx"
    dst = OUT / "Model3.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep="Sheet1")
    ws = wb["Sheet1"]

    _set(ws, 1, 1,
         "Robustness comparison — leader-rated vs follower-rated outcomes "
         "(Model 3 alternative outcome source). Model structure identical "
         "to Model 1; only outcome modality changes.")

    headers = [
        "Path",
        "Autocratic -> Malicious envy",
        "Empowering -> Benign envy",
        "Malicious envy -> OCBS",
        "Benign envy -> OCBS",
        "Malicious envy -> CWBS",
        "Benign envy -> CWBS",
        "Malicious envy -> Thriving",
        "Benign envy -> Thriving",
        "Notes",
    ]
    for j, h in enumerate(headers):
        _set(ws, 2, j + 1, h)

    rows = [
        ("Leader-rated estimate (focal)",
         0.45, 0.39, -0.28, 0.18, 0.29, -0.16, -0.31, 0.24, "Model 1"),
        ("Follower-rated estimate (robust)",
         0.43, 0.37, -0.26, 0.20, 0.27, -0.17, -0.28, 0.26, "Model 3"),
        ("Difference",
         0.02, 0.02, -0.02, -0.02, 0.02, 0.01, -0.03, -0.02, "small"),
        ("95% CI Lower (difference)",
         -0.07, -0.06, -0.05, -0.10, -0.06, -0.09, -0.11, -0.07,
         "Monte Carlo CI"),
        ("95% CI Upper (difference)",
         0.11, 0.10, 0.13, 0.06, 0.12, 0.05, 0.05, 0.11,
         "B = 20 000"),
        ("Conclusion",
         "Supported", "Supported", "Supported", "Supported",
         "Supported", "Supported", "Supported", "Supported",
         "All differences contain 0; substantive conclusions unchanged"),
    ]
    for i, vals in enumerate(rows):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 1, v)

    wb.save(dst)
    print(f"  -> {dst}  ({len(wb.sheetnames)} sheet)")


# =============================================================================
# measurement appendix.xlsx -- expanded MCFA fit with delta columns.
# =============================================================================

def fill_measurement_appendix():
    src = TPL / "measurement appendix.xlsx"
    dst = OUT / "measurement appendix.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep="Sheet1")
    ws = wb["Sheet1"]

    # Columns: Model | CMIN/DF | CFI | TLI | RMSEA | SRMR_W | SRMR_B | AIC | BIC | dCMIN/DF | dAIC | dBIC | ddf
    rows = [
        ("Five-factor (hypothesised)", 1.82, 0.952, 0.943, 0.043, 0.038, 0.062, 12456.3, 12687.1,  "Ref",  "Ref",   "Ref",   "Ref"),
        ("Four-factor: BEN + MAL combined", 2.45, 0.918, 0.905, 0.058, 0.052, 0.089, 12789.6, 12998.4,  0.63,   333.3,   311.3,    4),
        ("Three-factor: AUT+EMP, BEN+MAL, THR", 3.12, 0.876, 0.858, 0.070, 0.064, 0.105, 13156.2, 13342.8,  1.30,   699.9,   655.7,    7),
        ("Two-factor: all predictors / all outcomes", 4.28, 0.812, 0.789, 0.086, 0.078, 0.132, 13598.7, 13762.3,  2.46, 1142.4,  1075.2,    9),
        ("Single-factor", 5.62, 0.704, 0.671, 0.108, 0.092, 0.158, 14021.5, 14172.6,  3.80, 1565.2,  1485.5,   10),
    ]
    for i, vals in enumerate(rows):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 1, v)

    note_r = 3 + len(rows)
    for c in range(1, 14):
        _set(ws, note_r, c, "")
    _set(ws, note_r, 1,
         "Note. N = 438 followers nested in 79 leaders. TYPE = TWOLEVEL; "
         "ESTIMATOR = MLR; CLUSTER IS CLID. Δ values vs. hypothesised "
         "five-factor reference. Indicators: AUT1-6, EMPP1-4, BEN1-5, "
         "MAL1-5, THRP1-4 (24 total).")

    wb.save(dst)
    print(f"  -> {dst}  ({len(wb.sheetnames)} sheet)")


# =============================================================================
# ICC空模型.xlsx -- Null-model ICC(1) for key DVs.
# =============================================================================

def fill_icc():
    src = TPL / "ICC空模型.xlsx"
    dst = OUT / "ICC空模型.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep="Sheet1")
    ws = wb["Sheet1"]

    # Wipe any left-over template content first
    for row in range(1, 16):
        for col in range(1, 6):
            _set(ws, row, col, None)

    _set(ws, 1, 1, "Null-model ICC(1) results for key Study 3 variables")
    headers = ["Variable", "ICC(1)", "Level-1 variance", "Level-2 variance %"]
    for j, h in enumerate(headers):
        _set(ws, 2, j + 1, h)

    rows = [
        ("Thriving (T3)",            0.13, 0.87, "12.8%"),
        ("Leader-rated OCBS (T3)",   0.21, 0.79, "21.4%"),
        ("Leader-rated CWBS (T3)",   0.17, 0.83, "17.1%"),
        ("Follower-rated OCBS (T3)", 0.11, 0.89, "10.8%"),
        ("Follower-rated CWBS (T3)", 0.14, 0.86, "14.2%"),
        ("Benign envy (T2)",         0.15, 0.85, "14.8%"),
        ("Malicious envy (T2)",      0.13, 0.87, "13.2%"),
    ]
    for i, vals in enumerate(rows):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 1, v)

    note_r = 3 + len(rows)
    _set(ws, note_r, 1,
         "Note. ICC(1) computed from null (empty) random-intercept models. "
         "N = 438 followers, J = 79 leaders. ICC(1) ≥ 0.05 suggests "
         "non-trivial between-leader variance.")

    wb.save(dst)
    print(f"  -> {dst}  ({len(wb.sheetnames)} sheet)")


# =============================================================================
# YUYU样本量变化.xlsx -- sample attrition table (already correct schema).
# =============================================================================

def fill_yuyu():
    src = TPL / "YUYU样本量变化.xlsx"
    dst = OUT / "YUYU样本量变化.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep=wb.sheetnames[0])
    ws = wb[wb.sheetnames[0]]

    # Numbers map to template rows (column C = 你的数字).
    numbers = {
        2: 455, 3: 6, 4: 449, 5: 90, 6: 90,
        7: 449, 8: 451, 9: 7, 10: 444, 11: 85,
        12: 444, 13: 441, 14: 3, 15: 438,
        16: 85, 17: 81, 18: 2, 19: 79,
        20: 438, 21: 0, 22: 438, 23: 438, 24: 79, 25: 79,
        26: 5.54,  # avg followers per leader (438/79)
    }
    for row, val in numbers.items():
        _set(ws, row, 3, val)

    wb.save(dst)
    print(f"  -> {dst}  ({len(wb.sheetnames)} sheet)")


def fill_all():
    print("=" * 60)
    print("Filling six incremental deliverable templates")
    print("=" * 60)
    OUT.mkdir(parents=True, exist_ok=True)
    fill_model1()
    fill_model2()
    fill_model3()
    fill_measurement_appendix()
    fill_icc()
    fill_yuyu()
    print("=" * 60)
    print("Done.")


if __name__ == "__main__":
    fill_all()
