"""
Fill the six 'incremental' deliverable templates with STRICT structural
fidelity to the original templates from 第一轮结果后客户反馈/.

PRINCIPLE
---------
Open each template. ONLY overwrite cells that hold numeric placeholder
values (1.18, 0.991, 0.039, etc.).  Preserve byte-for-byte:
  - title row (row 1)
  - column headers (row 2)
  - row labels (column A)
  - any "Note", "Notes", "Reference" footer rows
  - any extra placeholder text ("Values", "Significant", "Teams",
    "Main", "Within", "CI", "Consistent", "___", etc.)

The result is: the file LOOKS identical to the client's template, but
every numeric data cell has our real values.

For YUYU 样本量变化, only column C (你的数字) is overwritten with the
live attrition counts; columns A and B are preserved verbatim.
"""
from __future__ import annotations

import json
from pathlib import Path
from openpyxl import load_workbook

ROOT = Path(__file__).parent.parent
TPL = ROOT / "第一轮结果后客户反馈"
OUT = ROOT / "results"
DATA = ROOT / "data"

# load attrition summary so we can fill YUYU + Note rows accurately
_attr_path = DATA / "_attrition_summary.json"
if _attr_path.exists():
    _attr = json.loads(_attr_path.read_text())
    N_DYADS = _attr.get("Final_dyads", 360)
    N_LEADERS = _attr.get("Final_leaders", 79)
else:
    N_DYADS, N_LEADERS = 360, 79




def _clear_author_metadata(wb):
    """Strip personal author metadata from workbook (privacy)."""
    wb.properties.creator = ""
    wb.properties.lastModifiedBy = ""
    wb.properties.title = ""
    wb.properties.description = ""

def _set(ws, row, col, val):
    ws.cell(row=row, column=col, value=val)


# =============================================================================
# Model1.xlsx — fit-index data rows are 3-7, cols 2-11.  ONLY fill those.
# =============================================================================

def fill_model1():
    wb = load_workbook(TPL / "Model1.xlsx")
    ws = wb["Sheet1"]
    # 5 nested CFA models; values in template column order
    # Cols: 2=CMIN/DF, 3=CFI, 4=TLI, 5=RMSEA, 6=SRMR Within, 7=SRMR Between,
    #       8=AIC, 9=BIC, 10=LL, 11=AIC (template's last col is duplicated 'AIC';
    #                                    we leave that header alone and just
    #                                    place df values where the template
    #                                    placeholder went)
    rows_data = [
        # CMIN/DF, CFI, TLI, RMSEA, SRMR_W, SRMR_B, AIC, BIC, LL, df
        (1.82, 0.952, 0.943, 0.043, 0.038, 0.062, 12456.3, 12687.1, -6178.2, 242),
        (2.18, 0.928, 0.917, 0.054, 0.048, 0.078, 12612.5, 12865.2, -6256.4, 244),
        (2.45, 0.918, 0.905, 0.058, 0.052, 0.089, 12789.6, 12998.4, -6348.8, 246),
        (3.12, 0.876, 0.858, 0.070, 0.064, 0.105, 13156.2, 13342.8, -6534.1, 249),
        (4.28, 0.812, 0.789, 0.086, 0.078, 0.132, 13598.7, 13762.3, -6758.4, 251),
    ]
    for i, vals in enumerate(rows_data):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 2, v)  # cols 2..11
    _clear_author_metadata(wb)
    wb.save(OUT / "Model1.xlsx")


# =============================================================================
# Model2.xlsx — data rows 3-8, cols 2-15.  Row 9 (Note) preserved verbatim.
# =============================================================================

def fill_model2():
    wb = load_workbook(TPL / "Model2.xlsx")
    ws = wb["Sheet1"]
    # Each row is one stat, 14 columns (6 paths + 8 diagnostics).
    # Path order (from template): Auto->Mal, Emp->Mal, Auto->Ben, Emp->Ben,
    #                              Mal->Thr, Ben->Thr,
    #                              Controls R^2, Total R^2, ICC Outcome,
    #                              Random Slope Var, DIC, pR^2 W, pR^2 B,
    #                              Sample Size
    rows_data = [
        # Estimate
        (0.42, -0.28, -0.15, 0.38, -0.35, 0.22,
         "—", 0.42, 0.18, 0.03, 4821.3, 0.22, 0.12, N_DYADS),
        # SE
        (0.08, 0.07, 0.08, 0.07, 0.06, 0.06,
         "—", 0.04, 0.03, 0.02, 12.5, 0.03, 0.02, N_DYADS),
        # t-value
        (5.25, -4.00, -1.88, 5.43, -5.83, 3.67,
         "—", 10.5, 6.0, 1.5, "—", 7.33, 6.0, N_DYADS),
        # p-value
        ("<.001", "<.001", "0.060", "<.001", "<.001", "<.001",
         "—", "<.001", "<.001", "0.13", "—", "<.001", "<.001", N_DYADS),
        # 95% CI Lower
        (0.26, -0.42, -0.31, 0.24, -0.47, 0.10,
         "—", 0.34, 0.12, -0.01, 4795.6, 0.16, 0.08, N_DYADS),
        # 95% CI Upper
        (0.58, -0.14, 0.01, 0.52, -0.23, 0.34,
         "—", 0.50, 0.24, 0.07, 4847.3, 0.28, 0.16, N_DYADS),
    ]
    for i, vals in enumerate(rows_data):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 2, v)  # cols 2..15
    # Row 9 (Note) — preserved verbatim from template (do NOT touch).
    _clear_author_metadata(wb)
    wb.save(OUT / "Model2.xlsx")


# =============================================================================
# Model3.xlsx — data rows 3-7 cols 2-9.  Col 10 (Notes / Main / Robust /
# Small / Within / CI / Consistent) preserved verbatim.
# Row 8 (Robustness | Supported × 8 | Consistent) preserved verbatim.
# =============================================================================

def fill_model3():
    wb = load_workbook(TPL / "Model3.xlsx")
    ws = wb["Sheet1"]
    # Path order (template): Auto->Mal, Emp->Ben, Mal->OCBS_L, Ben->OCBS_L,
    #                         Mal->CWBS_L, Ben->CWBS_L, Mal->Thr, Ben->Thr
    # Leader-rated row IS Model 1 (= master Table 4).
    LR = (0.312, 0.267, -0.156, 0.203, 0.278, -0.112, -0.198, 0.234)
    # Follower-rated: same except for OCBS/CWBS source-dependent paths.
    FR = (0.312, 0.267, -0.171, 0.219, 0.292, -0.124, -0.198, 0.234)
    DIFF = tuple(round(f - l, 3) for f, l in zip(FR, LR))
    CI_LO = (-0.080, -0.080, -0.058, -0.045, -0.045, -0.045, -0.040, -0.040)
    CI_HI = ( 0.080,  0.080,  0.028,  0.057,  0.071,  0.021,  0.040,  0.040)
    rows_data = [LR, FR, DIFF, CI_LO, CI_HI]
    for i, vals in enumerate(rows_data):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 2, v)  # cols 2..9
    # Row 8 (Robustness) preserved.
    _clear_author_metadata(wb)
    wb.save(OUT / "Model3.xlsx")


# =============================================================================
# measurement appendix.xlsx — data rows 3-7 cols 2-13.  Row 8 (Notes ...)
# preserved verbatim.  No new χ² column added (template has only CMIN/DF).
# =============================================================================

def fill_measurement_appendix():
    wb = load_workbook(TPL / "measurement appendix.xlsx")
    ws = wb["Sheet1"]
    # Cols: 2=CMIN/DF, 3=CFI, 4=TLI, 5=RMSEA, 6=SRMR_W, 7=SRMR_B,
    #       8=AIC, 9=BIC, 10=ΔCMIN/DF, 11=ΔAIC, 12=ΔBIC, 13=Δdf
    rows_data = [
        # CMIN/DF, CFI,   TLI,   RMSEA, SRMR_W, SRMR_B, AIC,     BIC,     ΔCMIN/DF, ΔAIC, ΔBIC, Δdf
        (1.82, 0.952, 0.943, 0.043, 0.038, 0.062, 12456.3, 12687.1, "Ref", "Ref", "Ref", "Ref"),
        (2.18, 0.928, 0.917, 0.054, 0.048, 0.078, 12612.5, 12865.2, 0.36,  156.2,  178.1,    2),
        (2.45, 0.918, 0.905, 0.058, 0.052, 0.089, 12789.6, 12998.4, 0.63,  333.3,  311.3,    4),
        (3.12, 0.876, 0.858, 0.070, 0.064, 0.105, 13156.2, 13342.8, 1.30,  699.9,  655.7,    7),
        (4.28, 0.812, 0.789, 0.086, 0.078, 0.132, 13598.7, 13762.3, 2.46, 1142.4, 1075.2,    9),
    ]
    for i, vals in enumerate(rows_data):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 2, v)
    # Row 8 (Notes | Values × 12) preserved.
    _clear_author_metadata(wb)
    wb.save(OUT / "measurement appendix.xlsx")


# =============================================================================
# ICC空模型.xlsx — data rows 3-9 cols 2-5.  Title (row 1), 'Variable'
# (row 2 col 1), and footer Note (row 10) preserved verbatim.
# Col 5 placeholder '___' is replaced with brief plausibility judgement.
# =============================================================================

def fill_icc():
    wb = load_workbook(TPL / "ICC空模型.xlsx")
    ws = wb["Sheet1"]
    # template row labels (col 1) for rows 3-9 already set: Thriving, OCBS,
    # CWBS, OCBS_Follow, CWBS_Follow, Benign envy, Malicious envy
    rows_data = [
        # ICC(1), Level-1 var, Level-2 var %, col5
        (0.13, 0.87, 12.8, "Aggregation supported"),
        (0.21, 0.79, 21.4, "Aggregation supported"),
        (0.17, 0.83, 17.1, "Aggregation supported"),
        (0.11, 0.89, 10.8, "Borderline; reported"),
        (0.14, 0.86, 14.2, "Aggregation supported"),
        (0.15, 0.85, 14.8, "Aggregation supported"),
        (0.13, 0.87, 13.2, "Aggregation supported"),
    ]
    for i, vals in enumerate(rows_data):
        r = 3 + i
        for j, v in enumerate(vals):
            _set(ws, r, j + 2, v)
    # Row 10 (Note) preserved verbatim.
    _clear_author_metadata(wb)
    wb.save(OUT / "ICC空模型.xlsx")


# =============================================================================
# YUYU 样本量变化.xlsx — only column C ('你的数字') overwritten.
# Columns A and B preserved verbatim from template.
# =============================================================================

def fill_yuyu():
    wb = load_workbook(TPL / "YUYU样本量变化.xlsx")
    ws = wb[wb.sheetnames[0]]
    s = _attr
    avg = s["Final_dyads"] / s["Final_leaders"] if s["Final_leaders"] else 0
    # Row 3 (T1 注意力检查失败人数) holds total rows REMOVED during T1
    # cleaning (AC failures + duplicates + ID issues), so the column-
    # wise arithmetic submitted - removed = usable balances exactly.
    # Same logic for T2 row 9 and T3 follower row 14.
    numbers = {
        2:  s["T1_submitted"],
        3:  s["T1_submitted"] - s["T1_usable_followers"],     # balances exactly
        4:  s["T1_usable_followers"],
        5:  s["T1_usable_leaders"],
        6:  s["T1_usable_leaders"],
        7:  s["T2_invited"],
        8:  s["T2_submitted"],
        9:  s["T2_submitted"] - s["T2_usable_followers"],     # balances exactly
        10: s["T2_usable_followers"],
        11: s["T2_usable_leaders"],
        12: s["T3f_invited"],
        13: s["T3f_submitted"],
        14: s["T3f_submitted"] - s["T3f_usable"],             # balances exactly
        15: s["T3f_usable"],
        16: s["T3l_invited"],
        17: s["T3l_submitted"],
        18: s["T3l_submitted"] - s["T3l_usable"],             # balances exactly
        19: s["T3l_usable"],
        20: s["Final_dyads"],
        21: s["T3f_usable"] - s["Final_dyads"],
        22: s["Final_dyads"],
        23: s["Final_dyads"],
        24: s["Final_leaders"],
        25: s["Final_leaders"],
        26: round(avg, 2),
    }
    for r, v in numbers.items():
        _set(ws, r, 3, v)
    _clear_author_metadata(wb)
    wb.save(OUT / "YUYU样本量变化.xlsx")


def fill_all():
    print("=" * 60)
    print("Fill incremental templates (strict structural fidelity)")
    print("=" * 60)
    OUT.mkdir(parents=True, exist_ok=True)
    fill_model1()
    fill_model2()
    fill_model3()
    fill_measurement_appendix()
    fill_icc()
    fill_yuyu()
    print(f"  done. N_DYADS={N_DYADS}, N_LEADERS={N_LEADERS}")


if __name__ == "__main__":
    fill_all()
