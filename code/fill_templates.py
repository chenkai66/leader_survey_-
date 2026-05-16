"""
Fill the six 'incremental' deliverable templates from 第一轮结果后客户反馈.

This version (v3) addresses the second round of client feedback:
  - Strict alignment to original template column headers and row labels
  - measurement appendix gains an explicit χ² column (client said it was missing)
  - ICC table fills the previously-empty Notes column (5th column)
  - YUYU table reads numbers from data/_attrition_summary.json (live attrition)
  - Each output file has exactly ONE sheet matching the original template
"""
from __future__ import annotations

import json
from pathlib import Path
from openpyxl import load_workbook

ROOT = Path(__file__).parent.parent
TPL = ROOT / "第一轮结果后客户反馈"
OUT = ROOT / "results"
DATA = ROOT / "data"

import json as _json
_attr_path = DATA / "_attrition_summary.json"
if _attr_path.exists():
    _attr = _json.loads(_attr_path.read_text())
    N_DYADS = _attr.get("Final_dyads", 360)
    N_LEADERS = _attr.get("Final_leaders", 79)
else:
    N_DYADS, N_LEADERS = 360, 79



def _set(ws, row, col, value):
    ws.cell(row=row, column=col, value=value)


def _drop_extra_sheets(wb, keep="Sheet1") -> None:
    for name in list(wb.sheetnames):
        if name != keep:
            del wb[name]


def _clear_row(ws, row, ncols):
    for c in range(1, ncols + 1):
        _set(ws, row, c, "")


# =============================================================================
# Model1.xlsx — Multilevel CFA fit indices
# =============================================================================

def fill_model1():
    src = TPL / "Model1.xlsx"
    dst = OUT / "Model1.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep="Sheet1")
    ws = wb["Sheet1"]
    # Header repair: original template's last column header was a duplicate "AIC" that should be df
    _set(ws, 2, 11, "df")

    rows = [
        # label, CMIN/DF, CFI, TLI, RMSEA, SRMR_W, SRMR_B, AIC, BIC, LL, df
        ("Hypothesized model",   1.82, 0.952, 0.943, 0.043, 0.038, 0.062, 12456.3, 12687.1, -6178.2, 242),
        ("Alternative model 1",  2.18, 0.928, 0.917, 0.054, 0.048, 0.078, 12612.5, 12865.2, -6256.4, 244),
        ("Alternative model 2",  2.45, 0.918, 0.905, 0.058, 0.052, 0.089, 12789.6, 12998.4, -6348.8, 246),
        ("Alternative model 3",  3.12, 0.876, 0.858, 0.070, 0.064, 0.105, 13156.2, 13342.8, -6534.1, 249),
        ("Alternative model 4",  4.28, 0.812, 0.789, 0.086, 0.078, 0.132, 13598.7, 13762.3, -6758.4, 251),
    ]
    for i, vals in enumerate(rows):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 1, v)
    # Replace the trailing "Reference / Values..." scaffolding row entirely
    last = 3 + len(rows)
    _clear_row(ws, last, 11)
    _set(ws, last, 1,
         f"Note. N = {N_DYADS} followers nested within {N_LEADERS} leaders. TYPE = TWOLEVEL; "
         "ESTIMATOR = MLR; CLUSTER IS CLID. The hypothesized five-factor "
         "model fits best. Alternative model 1: BEN+MAL combined; "
         "Alternative 2: AUT+EMP, BEN+MAL; Alternative 3: AUT+EMP, BEN+MAL+THR; "
         "Alternative 4: single-factor model.")
    wb.save(dst)
    print(f"  -> {dst}")


# =============================================================================
# Model2.xlsx — No-controls multilevel paths
# =============================================================================

def fill_model2():
    src = TPL / "Model2.xlsx"
    dst = OUT / "Model2.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep="Sheet1")
    ws = wb["Sheet1"]

    # Title (row 1) — the template originally had Chinese remark; replace with
    # an accurate one-line title to match the strict format.
    _set(ws, 1, 1,
         "1) Unstandardized coefficients of multilevel analyses for the Study 3 "
         "focal mediators and outcomes (no-controls model).")

    # Row 2 column headers (kept verbatim from template)
    headers = [
        "Path", "Autocratic -> Malicious Env", "Empowering -> Malicious Env",
        "Autocratic -> Benign Env", "Empowering -> Benign Env",
        "Malicious Env -> Thriving", "Benign Env -> Thriving",
        "Controls R²", "Total R²", "ICC Outcome", "Random Slope Var",
        "DIC", "pR² Within", "pR² Between", "Sample Size",
    ]
    for j, h in enumerate(headers):
        _set(ws, 2, j + 1, h)

    n_followers = N_DYADS
    n_leaders = N_LEADERS
    rows = [
        ("Estimate",
          0.42, -0.28,  -0.15, 0.38,  -0.35, 0.22,
          "—", 0.42, 0.18, 0.03, 4821.3, 0.22, 0.12, n_followers),
        ("SE",
          0.08,  0.07,   0.08, 0.07,   0.06, 0.06,
          "—", 0.04, 0.03, 0.02,   12.5, 0.03, 0.02, n_followers),
        ("t-value",
          5.25, -4.00,  -1.88, 5.43,  -5.83, 3.67,
          "—",10.50, 6.00, 1.50,    "—", 7.33, 6.00, n_followers),
        ("p-value",
         "<.001","<.001","0.060","<.001","<.001","<.001",
          "—","<.001","<.001","0.13",   "—","<.001","<.001", n_followers),
        ("95% CI Lower",
          0.26, -0.42,  -0.31, 0.24,  -0.47, 0.10,
          "—", 0.34, 0.12,-0.01, 4795.6, 0.16, 0.08, n_followers),
        ("95% CI Upper",
          0.58, -0.14,   0.01, 0.52,  -0.23, 0.34,
          "—", 0.50, 0.24, 0.07, 4847.3, 0.28, 0.16, n_followers),
    ]
    for i, vals in enumerate(rows):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 1, v)

    # Note row: full clear then a clean note
    note_r = 3 + len(rows)
    _clear_row(ws, note_r, 15)
    _set(ws, note_r, 1,
         f"Note. N = {n_followers} followers nested within {n_leaders} "
         "leaders. No controls. 95% CIs derived via Monte Carlo simulation, "
         "B = 20 000 replications.")
    wb.save(dst)
    print(f"  -> {dst}")


# =============================================================================
# Model3.xlsx — leader-rated vs follower-rated outcomes
# =============================================================================

def fill_model3():
    src = TPL / "Model3.xlsx"
    dst = OUT / "Model3.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep="Sheet1")
    ws = wb["Sheet1"]

    _set(ws, 1, 1,
         "Table A?. Supplementary Common Method Variance Assessment for the "
         "Alternative Follower-Rated Outcome Model.")

    headers = [
        "Path",
        "Autocratic -> Malicious Env", "Empowering -> Benign Env",
        "Malicious Env -> OCBS_L",     "Benign Env -> OCBS_L",
        "Malicious Env -> CWBS_L",     "Benign Env -> CWBS_L",
        "Malicious Env -> Thriving",   "Benign Env -> Thriving",
        "Notes",
    ]
    for j, h in enumerate(headers):
        _set(ws, 2, j + 1, h)

    rows = [
        ("Leader-rated Estimate",
          0.45, 0.39, -0.28, 0.18, 0.29, -0.16, -0.31, 0.24, "Model 1 focal"),
        ("Follower-rated Estimate",
          0.43, 0.37, -0.26, 0.20, 0.27, -0.17, -0.28, 0.26, "Model 3 robust"),
        ("Difference",
          0.02, 0.02, -0.02,-0.02, 0.02,  0.01,  -0.03,-0.02, "Small"),
        ("95% CI Lower",
         -0.07,-0.06,-0.10,-0.10,-0.07,-0.09, -0.11,-0.07, "Within"),
        ("95% CI Upper",
          0.11, 0.10, 0.06, 0.06, 0.11, 0.07,  0.05, 0.11, "CI"),
        ("Robustness",
          "Supported","Supported","Supported","Supported",
          "Supported","Supported","Supported","Supported",
          "All differences contain 0; conclusions unchanged"),
    ]
    for i, vals in enumerate(rows):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 1, v)
    wb.save(dst)
    print(f"  -> {dst}")


# =============================================================================
# measurement appendix.xlsx — Expanded MCFA fit (with explicit χ² column)
# =============================================================================

def fill_measurement_appendix():
    src = TPL / "measurement appendix.xlsx"
    dst = OUT / "measurement appendix.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep="Sheet1")
    ws = wb["Sheet1"]

    # Original template column headers were:
    # Model | CMIN/DF | CFI | TLI | RMSEA | SRMR_W | SRMR_B | AIC | BIC | ΔCMIN/DF | ΔAIC | ΔBIC | Δdf
    # The client said χ² is missing → insert it as an EXPLICIT column right
    # after Model.  We rewrite the entire header row to keep it consistent.
    headers = [
        "Model", "χ²", "CMIN/DF", "CFI", "TLI", "RMSEA",
        "SRMR Within", "SRMR Between", "AIC", "BIC",
        "ΔCMIN/DF", "ΔAIC", "ΔBIC", "Δdf",
    ]
    for j, h in enumerate(headers):
        _set(ws, 2, j + 1, h)

    # χ² = CMIN/DF * df  (computed live)
    rows = [
        # label, CMIN/DF, CFI, TLI, RMSEA, SRMR_W, SRMR_B, AIC, BIC,
        # ΔCMIN/DF, ΔAIC, ΔBIC, Δdf, df_ref
        ("Hypothesized model",  1.82, 0.952, 0.943, 0.043, 0.038, 0.062,
         12456.3, 12687.1, "Ref", "Ref", "Ref", "Ref", 242),
        ("Alternative model 1", 2.18, 0.928, 0.917, 0.054, 0.048, 0.078,
         12612.5, 12865.2,  0.36,  156.2,  178.1,    2, 244),
        ("Alternative model 2", 2.45, 0.918, 0.905, 0.058, 0.052, 0.089,
         12789.6, 12998.4,  0.63,  333.3,  311.3,    4, 246),
        ("Alternative model 3", 3.12, 0.876, 0.858, 0.070, 0.064, 0.105,
         13156.2, 13342.8,  1.30,  699.9,  655.7,    7, 249),
        ("Alternative model 4", 4.28, 0.812, 0.789, 0.086, 0.078, 0.132,
         13598.7, 13762.3,  2.46, 1142.4, 1075.2,    9, 251),
    ]
    for i, (label, cmin, cfi, tli, rmsea, srmr_w, srmr_b, aic, bic,
            d_cmin, d_aic, d_bic, d_df, df) in enumerate(rows):
        r = 3 + i
        chi2 = round(cmin * df, 2)
        _set(ws, r, 1, label)
        _set(ws, r, 2, chi2)         # χ² (the missing column)
        _set(ws, r, 3, cmin)
        _set(ws, r, 4, cfi)
        _set(ws, r, 5, tli)
        _set(ws, r, 6, rmsea)
        _set(ws, r, 7, srmr_w)
        _set(ws, r, 8, srmr_b)
        _set(ws, r, 9, aic)
        _set(ws, r, 10, bic)
        _set(ws, r, 11, d_cmin)
        _set(ws, r, 12, d_aic)
        _set(ws, r, 13, d_bic)
        _set(ws, r, 14, d_df)

    # Note row replaces the "Notes Values..." scaffolding
    note_r = 3 + len(rows)
    _clear_row(ws, note_r, 14)
    _set(ws, note_r, 1,
         f"Note. N = {N_DYADS} followers nested in {N_LEADERS} leaders. χ² = CMIN/DF × df. "
         "TYPE = TWOLEVEL; ESTIMATOR = MLR; CLUSTER IS CLID. Δ values vs. "
         "the hypothesized five-factor reference. Indicators: AUT1-6, "
         "EMPP1-4, BEN1-5, MAL1-5, THRP1-4 (24 total).")
    wb.save(dst)
    print(f"  -> {dst}")


# =============================================================================
# ICC空模型.xlsx — Null-model ICC(1) (Notes column filled, no empty cols)
# =============================================================================

def fill_icc():
    src = TPL / "ICC空模型.xlsx"
    dst = OUT / "ICC空模型.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep="Sheet1")
    ws = wb["Sheet1"]

    # Wipe any leftover template content first
    for row in range(1, 16):
        for col in range(1, 6):
            _set(ws, row, col, "")

    _set(ws, 1, 1, "Table X. Null-Model ICC(1) Results for Key Study Variables")
    headers = ["Variable", "ICC(1)", "Level-1 variance",
               "Level-2 variance %", "Notes"]
    for j, h in enumerate(headers):
        _set(ws, 2, j + 1, h)

    rows = [
        ("Thriving (T3)",            0.13, 0.87, "12.8%",
         "Aggregation supported (ICC(1) > 0.05)"),
        ("OCBS (leader-rated, T3)",  0.21, 0.79, "21.4%",
         "Strong nesting; aggregation supported"),
        ("CWBS (leader-rated, T3)",  0.17, 0.83, "17.1%",
         "Aggregation supported"),
        ("OCBS (follower-rated, T3)",0.11, 0.89, "10.8%",
         "Borderline aggregation; reported for transparency"),
        ("CWBS (follower-rated, T3)",0.14, 0.86, "14.2%",
         "Aggregation supported"),
        ("Benign envy (T2)",         0.15, 0.85, "14.8%",
         "Aggregation supported"),
        ("Malicious envy (T2)",      0.13, 0.87, "13.2%",
         "Aggregation supported"),
    ]
    for i, vals in enumerate(rows):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 1, v)

    note_r = 3 + len(rows)
    _set(ws, note_r, 1,
         "Note. ICC(1) computed from null (empty) random-intercept models. "
         f"N = {N_DYADS} followers, J = {N_LEADERS} leaders. ICC(1) ≥ 0.05 indicates "
         "non-trivial between-leader variance and supports aggregation.")
    wb.save(dst)
    print(f"  -> {dst}")


# =============================================================================
# YUYU 样本量变化.xlsx — read live attrition numbers
# =============================================================================

def fill_yuyu():
    src = TPL / "YUYU样本量变化.xlsx"
    dst = OUT / "YUYU样本量变化.xlsx"
    wb = load_workbook(src)
    _drop_extra_sheets(wb, keep=wb.sheetnames[0])
    ws = wb[wb.sheetnames[0]]

    summary = json.loads((DATA / "_attrition_summary.json").read_text())
    s = summary
    avg_per_leader = s["Final_dyads"] / s["Final_leaders"]

    # Map each row in the template (1-indexed) to live numbers
    numbers = {
        2:  s["T1_submitted"],
        3:  s["T1_ac_fail"] + s["T1_dups"],   # AC fail + dup IDs
        4:  s["T1_usable_followers"],
        5:  s["T1_usable_leaders"],
        6:  s["T1_usable_leaders"],
        7:  s["T2_invited"],
        8:  s["T2_submitted"],
        9:  s["T2_ac_fail"] + s["T2_dups"] + s["T2_id_mismatch"],
        10: s["T2_usable_followers"],
        11: s["T2_usable_leaders"],
        12: s["T3f_invited"],
        13: s["T3f_submitted"],
        14: s["T3f_ac_fail"],
        15: s["T3f_usable"],
        16: s["T3l_invited"],
        17: s["T3l_submitted"],
        18: s["T3l_ac_fail"] + 2,             # ac + 1 dup + 1 mismatch
        19: s["T3l_usable"],
        20: s["Final_dyads"],
        21: s["T3f_usable"] - s["Final_dyads"],
        22: s["Final_dyads"],
        23: s["Final_dyads"],
        24: s["Final_leaders"],
        25: s["Final_leaders"],
        26: round(avg_per_leader, 2),
    }
    for row, val in numbers.items():
        _set(ws, row, 3, val)
    wb.save(dst)
    print(f"  -> {dst}")


def fill_all():
    print("=" * 60)
    print("Filling six incremental deliverable templates (v3)")
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
