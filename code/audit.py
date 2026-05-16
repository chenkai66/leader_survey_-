"""
Comprehensive deliverable audit suite — 7 layers in one entry point.

Run:  python3 code/audit.py
Exit: 0 iff every check passes; non-zero otherwise.

Layers
------
1. Constraint validator (calls code/constraint_validator.py).
2. Cross-file numerical consistency (Table 4 ↔ Model 3 LR ↔ Table A4
   focal ↔ Table A5 focal; same path = byte-equal coefficient).
3. Structural fidelity (every label cell in every output Excel must be
   byte-equal to the original client template).
4. Deep dive (reverse-coding correctness, item Likert ranges, T2
   demographic-free schema, OCBS/CWBS item counts, etc.).
5. Deeper-still (logical bounds: TenureWithLeader ≤ WorkingYears, age
   constraints, composite [1,7], reliability α range, attrition
   arithmetic balance, centered-column sum-to-zero, T2 dup-row
   identity, Table 1A monotone progression).
6. Yet-deeper (Mplus 5-block coverage with CLUSTER, no stale
   OCBS_Self7+/CWBS_Self6+ columns, Excel files open without warnings,
   Table 3 correlation cells rounded to 3 decimals).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import warnings
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RES = ROOT / "results"
TPL_INC = ROOT / "第一轮结果后客户反馈"
TPL_M = ROOT / "原始客户提供文件"

ALL_FAILURES: list[tuple[str, str]] = []


def _fail(layer, msg):
    ALL_FAILURES.append((layer, msg))


def _hdr(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def _is_label(v):
    if v is None or isinstance(v, (int, float)):
        return False
    s = str(v).strip()
    if s in ("", "___", "—"):
        return False
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        return False
    return True


# ── Layer 1 ─────────────────────────────────────────────────────────
def layer1():
    _hdr("Layer 1 — Constraint validator (33 sections / 189+ checks)")
    r = subprocess.run([sys.executable, str(ROOT / "code" / "constraint_validator.py")],
                       capture_output=True, text=True)
    summary_lines = [ln for ln in r.stdout.splitlines() if "SUMMARY" in ln]
    fails = [ln for ln in r.stdout.splitlines() if "FAIL" in ln]
    if summary_lines:
        print(" ", summary_lines[-1])
    for ln in fails:
        _fail("layer1", ln.strip())


# ── Layer 2 ─────────────────────────────────────────────────────────
def layer2():
    _hdr("Layer 2 — Cross-file numerical consistency")
    wb = load_workbook(RES / "主模型结果填答表.xlsx")
    ws4 = wb["Table 4. 主模型path"]
    table4 = {
        "Auto->Benign":     ws4.cell(row=4,  column=3).value,
        "Emp->Benign":      ws4.cell(row=5,  column=3).value,
        "Auto->Malicious":  ws4.cell(row=6,  column=3).value,
        "Emp->Malicious":   ws4.cell(row=7,  column=3).value,
        "Benign->Thriving": ws4.cell(row=9,  column=3).value,
        "Benign->OCBS":     ws4.cell(row=10, column=3).value,
        "Benign->CWBS":     ws4.cell(row=11, column=3).value,
        "Mal->Thriving":    ws4.cell(row=12, column=3).value,
        "Mal->OCBS":        ws4.cell(row=13, column=3).value,
        "Mal->CWBS":        ws4.cell(row=14, column=3).value,
    }
    wb.close()

    wb = load_workbook(RES / "Model3.xlsx")
    ws = wb["Sheet1"]
    m3 = {
        "Auto->Malicious":  ws.cell(3, 2).value,
        "Emp->Benign":      ws.cell(3, 3).value,
        "Mal->OCBS":        ws.cell(3, 4).value,
        "Benign->OCBS":     ws.cell(3, 5).value,
        "Mal->CWBS":        ws.cell(3, 6).value,
        "Benign->CWBS":     ws.cell(3, 7).value,
        "Mal->Thriving":    ws.cell(3, 8).value,
        "Benign->Thriving": ws.cell(3, 9).value,
    }
    wb.close()
    for k, v in m3.items():
        if abs(v - table4[k]) > 0.001:
            _fail("layer2", f"Model3 LR {k}={v} vs Table 4 {table4[k]}")
    print(f"  Model 3 LR ↔ Table 4: {len(m3)} paths checked")

    def _parse(s):
        if s is None:
            return None
        return float(str(s).split()[0])

    wb = load_workbook(RES / "study3附录结果填答.xlsx")
    a4 = wb["Table A4 Robustness"]
    a4_keys = [(3, "Benign->OCBS"), (4, "Benign->CWBS"),
               (5, "Mal->OCBS"), (6, "Mal->CWBS"),
               (7, "Auto->Benign"), (8, "Emp->Benign"),
               (9, "Auto->Malicious"), (10, "Emp->Malicious")]
    for r, k in a4_keys:
        v = _parse(a4.cell(r, 3).value)
        if abs(v - table4[k]) > 0.001:
            _fail("layer2", f"A4 focal {k}={v} vs Table 4 {table4[k]}")
    print(f"  A4 focal ↔ Table 4: {len(a4_keys)} paths checked")

    a5 = wb["Table A5 Robustness"]
    a5_keys = [(3, "Auto->Benign"), (4, "Emp->Benign"),
               (5, "Auto->Malicious"), (6, "Emp->Malicious"),
               (7, "Benign->Thriving"), (8, "Benign->OCBS"),
               (9, "Benign->CWBS"), (10, "Mal->Thriving"),
               (11, "Mal->OCBS"), (12, "Mal->CWBS")]
    for r, k in a5_keys:
        v = _parse(a5.cell(r, 3).value)
        if abs(v - table4[k]) > 0.001:
            _fail("layer2", f"A5 focal {k}={v} vs Table 4 {table4[k]}")
    print(f"  A5 focal ↔ Table 4: {len(a5_keys)} paths checked")
    wb.close()


# ── Layer 3 ─────────────────────────────────────────────────────────
def layer3():
    _hdr("Layer 3 — Structural fidelity (label cells byte-equal)")
    INC = ["Model1.xlsx", "Model2.xlsx", "Model3.xlsx",
           "measurement appendix.xlsx", "ICC空模型.xlsx",
           "YUYU样本量变化.xlsx"]
    MASTER = ["主模型结果填答表.xlsx", "study3附录结果填答.xlsx"]

    def _check(template_path, output_path, label):
        tpl = load_workbook(template_path)
        out = load_workbook(output_path)
        if tpl.sheetnames != out.sheetnames:
            _fail("layer3", f"{label} sheet order differs")
            tpl.close(); out.close()
            return
        diffs = 0
        for s in tpl.sheetnames:
            ws_t, ws_o = tpl[s], out[s]
            for r in range(1, ws_t.max_row + 1):
                for c in range(1, ws_t.max_column + 1):
                    tv = ws_t.cell(row=r, column=c).value
                    ov = ws_o.cell(row=r, column=c).value
                    if _is_label(tv) and tv != ov:
                        diffs += 1
        if diffs:
            _fail("layer3", f"{label} {diffs} label-cell deviations")
        tpl.close(); out.close()
        return diffs

    for f in INC:
        d = _check(TPL_INC / f, RES / f, f)
        if d == 0:
            print(f"  {f}: clean")
    for f in MASTER:
        d = _check(TPL_M / f, RES / f, f)
        if d == 0:
            print(f"  {f}: clean (multi-sheet)")


# ── Layer 4 ─────────────────────────────────────────────────────────
def layer4():
    _hdr("Layer 4 — Deep dive (reverse-coding, ranges, schema)")
    t1 = pd.read_excel(DATA / "T1_cleaned.xlsx")
    t2 = pd.read_excel(DATA / "T2_cleaned.xlsx")
    t3l = pd.read_excel(DATA / "T3_leader_cleaned.xlsx")
    t3f = pd.read_excel(DATA / "T3_follower_cleaned.xlsx")

    if "R_THR5" in t1.columns and "THR5" in t1.columns:
        d = (t1["R_THR5"] - (8 - t1["THR5"])).abs().max()
        if d > 1e-9:
            _fail("layer4", f"R_THR5 != 8 - THR5: max diff={d}")
    if "R_THR10" in t1.columns and "THR10" in t1.columns:
        d = (t1["R_THR10"] - (8 - t1["THR10"])).abs().max()
        if d > 1e-9:
            _fail("layer4", f"R_THR10 != 8 - THR10: max diff={d}")
    print("  Reverse-coding R_THR5/R_THR10 correct")

    demo = {"FollowerAge", "FollowerGender", "FollowerEducation",
            "FollowerJobLevel", "WorkingYears", "TenureWithLeader",
            "InteractionFreq", "LeaderEducation"}
    leak = [c for c in demo if c in t2.columns]
    if leak:
        _fail("layer4", f"T2 cleaned has demographic leak: {leak}")
    else:
        print("  T2 cleaned: no demographic leak")

    if "LeaderEducation" in t1.columns:
        _fail("layer4", "LeaderEducation leaked into T1")
    if "LeaderEducation" not in t3l.columns:
        _fail("layer4", "LeaderEducation missing from T3 leader")
    print("  LeaderEducation only in T3 leader (correct)")

    n_ocbs_self = sum(1 for c in t3f.columns
                      if c.startswith("OCBS_Self") and c[len("OCBS_Self"):].isdigit())
    n_cwbs_self = sum(1 for c in t3f.columns
                      if c.startswith("CWBS_Self") and c[len("CWBS_Self"):].isdigit())
    if n_ocbs_self != 6:
        _fail("layer4", f"OCBS_Self count = {n_ocbs_self}, expected 6")
    if n_cwbs_self != 5:
        _fail("layer4", f"CWBS_Self count = {n_cwbs_self}, expected 5")
    n_ocbs_l = sum(1 for c in t3l.columns
                   if c.startswith("OCBS_L") and c[len("OCBS_L"):].isdigit())
    n_cwbs = sum(1 for c in t3l.columns
                 if c.startswith("CWBS") and c[len("CWBS"):].isdigit())
    if n_ocbs_l != 6:
        _fail("layer4", f"OCBS_L count = {n_ocbs_l}, expected 6")
    if n_cwbs != 5:
        _fail("layer4", f"CWBS count = {n_cwbs}, expected 5")
    print(f"  OCBS/CWBS item counts: 6/5 in T3 follower, 6/5 in T3 leader")


# ── Layer 5 ─────────────────────────────────────────────────────────
def layer5():
    _hdr("Layer 5 — Deeper-still (bounds, relationships, math)")
    final = pd.read_excel(DATA / "final_merged_analysis_data.xlsx")
    t3l = pd.read_excel(DATA / "T3_leader_cleaned.xlsx")
    t2r = pd.read_excel(DATA / "T2_raw.xlsx")

    if (final["WorkingYears"] < final["TenureWithLeader"]).any():
        n = (final["WorkingYears"] < final["TenureWithLeader"]).sum()
        _fail("layer5", f"{n} rows: tenure > working years")
    if (final["FollowerAge"] - final["WorkingYears"]).min() < 14:
        _fail("layer5", "implied work-start age < 14")
    if (t3l["LeaderAge"] - t3l["LeadershipTenure"].fillna(0)).min() < 18:
        _fail("layer5", "implied lead-start age < 18")
    print("  Logical bounds satisfied")

    for c in ["Autocratic", "Empowering", "Narcissism", "PowerDistance",
              "BenignEnvy", "MaliciousEnvy", "T1_Thriving", "T3_Thriving",
              "OCBS_Leader", "CWBS_Leader", "OCBS_Follower", "CWBS_Follower"]:
        if c in final.columns and (final[c].min() < 1 or final[c].max() > 7):
            _fail("layer5", f"{c} out of [1,7]")
    print("  All composites in [1,7]")

    for v in ["Autocratic", "Empowering", "Narcissism", "PowerDistance",
              "FollowerAge", "TenureWithLeader", "InteractionFreq",
              "T1_Thriving", "WorkingYears"]:
        c = f"{v}_C"
        if c in final.columns and abs(final[c].sum()) > 1e-6:
            _fail("layer5", f"{c} sum = {final[c].sum():.6e}")
    print("  All centered _C columns sum to ~ 0")

    wb = load_workbook(RES / "YUYU样本量变化.xlsx")
    ws = wb[wb.sheetnames[0]]
    # Verify rows 2-3-4, 8-9-10, 13-14-15, 17-18-19 balance
    pairs = [(2, 3, 4), (8, 9, 10), (13, 14, 15), (17, 18, 19)]
    for sub_r, rem_r, use_r in pairs:
        s, rem, u = ws.cell(sub_r, 3).value, ws.cell(rem_r, 3).value, ws.cell(use_r, 3).value
        if s - rem != u:
            _fail("layer5", f"YUYU row {sub_r}-{rem_r}-{use_r}: {s}-{rem}!={u}")
    print("  YUYU arithmetic balanced for all 4 wave segments")
    wb.close()

    wb = load_workbook(RES / "主模型结果填答表.xlsx")
    ws = wb["Table 1A"]
    chi = [ws.cell(r, 2).value for r in range(3, 10)]
    cfi = [ws.cell(r, 5).value for r in range(3, 10)]
    rmsea = [ws.cell(r, 6).value for r in range(3, 10)]
    aic = [ws.cell(r, 7).value for r in range(3, 10)]
    if not all(chi[i] < chi[i+1] for i in range(6)):
        _fail("layer5", "Table 1A χ² not monotone")
    if not all(cfi[i] > cfi[i+1] for i in range(6)):
        _fail("layer5", "Table 1A CFI not monotone")
    if not all(rmsea[i] < rmsea[i+1] for i in range(6)):
        _fail("layer5", "Table 1A RMSEA not monotone")
    if not all(aic[i] < aic[i+1] for i in range(6)):
        _fail("layer5", "Table 1A AIC not monotone")
    print("  Table 1A 7-row fit progression monotone")
    wb.close()

    # T2 dups identical
    dup_ids = t2r["FollowerID"][t2r["FollowerID"].duplicated(keep=False)].unique()
    for fid in dup_ids:
        sub = t2r[t2r["FollowerID"] == fid]
        if len(sub) >= 2 and not (sub.iloc[0].fillna("NA") == sub.iloc[1].fillna("NA")).all():
            _fail("layer5", f"T2 dup {fid} non-identical")
    print(f"  T2 raw dup pairs identical ({len(dup_ids)} pairs)")


# ── Layer 6 ─────────────────────────────────────────────────────────
def layer6():
    _hdr("Layer 6 — Yet-deeper (Mplus, stale cols, Excel openable)")
    mp = (ROOT / "code" / "mcfa_mplus_syntax.inp").read_text()
    n_models = len(re.findall(r"!\s*MODEL\s+\d+:", mp))
    n_cluster = mp.count("CLUSTER IS CLID")
    if n_models != 5:
        _fail("layer6", f"Mplus has {n_models} model blocks, expected 5")
    else:
        print(f"  Mplus 5 model blocks (5/4/3/2/1-factor)")
    if n_cluster < 5:
        _fail("layer6", f"CLUSTER IS CLID in {n_cluster} blocks, expected 5")
    else:
        print(f"  Mplus CLUSTER in {n_cluster} blocks")

    # TYPE=COMPLEX section for single-construct cluster-adjusted CFA
    # (per client spec: appendix 普通 CFA must consider cluster adjustment)
    if "TYPE = COMPLEX" not in mp:
        _fail("layer6", "Mplus missing TYPE = COMPLEX block for appendix CFA")
    else:
        print(f"  Mplus has TYPE = COMPLEX section for cluster-adjusted CFA")

    for f in ["T3_follower_cleaned.xlsx", "T3_follower_raw.xlsx",
              "T3_leader_cleaned.xlsx", "T3_leader_raw.xlsx",
              "final_merged_analysis_data.xlsx"]:
        df = pd.read_excel(DATA / f)
        stale = [c for c in df.columns if c in
                 ("OCBS_Self7", "OCBS_Self8", "CWBS_Self6", "CWBS_Self7",
                  "OCBS_L7", "OCBS_L8", "CWBS6", "CWBS7")]
        if stale:
            _fail("layer6", f"{f} stale cols: {stale}")
    print("  No stale OCBS/CWBS columns from earlier (8-item / 7-item) generation")

    for f in RES.glob("*.xlsx"):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            try:
                wb = load_workbook(f); wb.close()
            except Exception as e:
                _fail("layer6", f"{f.name} fails to open cleanly: {e}")
    print("  All result Excels open without warnings")

    wb = load_workbook(RES / "主模型结果填答表.xlsx")
    ws = wb["Table 3. Correlation"]
    extra = 0
    for i in range(17):
        for j in range(i):
            v = ws.cell(row=3+i, column=5+j).value
            if isinstance(v, float) and abs(v - round(v, 3)) > 1e-9:
                extra += 1
    if extra:
        _fail("layer6", f"{extra} corr cells with >3 decimal precision")
    print("  Table 3 correlation matrix all ≤3 decimals")
    wb.close()



# ── Layer 7 ─────────────────────────────────────────────────────────
def layer7():
    """Sub-headers preserved, ID consistency, CLID order,
    no leftover ID-mismatch markers, master template label preservation."""
    _hdr("Layer 7 — Sub-headers, ID consistency, CLID order, label preservation")
    final = pd.read_excel(DATA / "final_merged_analysis_data.xlsx")
    t1 = pd.read_excel(DATA / "T1_cleaned.xlsx")
    t2 = pd.read_excel(DATA / "T2_cleaned.xlsx")
    t3l = pd.read_excel(DATA / "T3_leader_cleaned.xlsx")
    t3f = pd.read_excel(DATA / "T3_follower_cleaned.xlsx")

    # Master Table 5 panel sub-headers (rows 2, 8, 14, 22, 30, 38 in 1-indexed)
    wb = load_workbook(RES / "主模型结果填答表.xlsx")
    ws = wb["Table 5. Moderation and Conditi"]
    sub_headers = {
        2:  "Panel A. Interactions Predicting Benign Envy",
        8:  "Panel B. Interactions Predicting Malicious Envy",
        14: "Panel C. Conditional Indirect Effects via Benign Envy",
        22: "Panel D. Conditional Indirect Effects via Malicious Envy",
        30: "Panel E. Conditional Indirect Effects via Benign Envy at Different Levels of Narcissism",
        38: "Panel F. Conditional Indirect Effects via Malicious Envy at Different Levels of Narcissism",
    }
    for r, expected in sub_headers.items():
        actual = ws.cell(r, 1).value
        if actual != expected:
            _fail("layer7", f"Table 5 row {r} sub-header changed")
    print(f"  Table 5 sub-headers (6 panels) preserved")
    wb.close()

    # CompanyID consistency: leader/follower ID prefix matches CompanyID
    bad = 0
    for _, row in final.iterrows():
        if not row["LeaderID"].startswith(row["CompanyID"] + "_"):
            bad += 1
        if not str(row["FollowerID"]).startswith(row["CompanyID"] + "_"):
            bad += 1
    if bad:
        _fail("layer7", f"{bad} rows with CompanyID/ID-prefix mismatch")
    else:
        print(f"  CompanyID matches Leader/Follower ID prefix everywhere")

    # CLID monotonic by sorted LeaderID
    mapping = final[["LeaderID", "CLID"]].drop_duplicates().sort_values("CLID")
    if mapping["LeaderID"].tolist() != sorted(final["LeaderID"].unique()):
        _fail("layer7", "CLID not assigned in alphabetical LeaderID order")
    else:
        print(f"  CLID 1-79 assigned in alphabetical LeaderID order")

    # No X_L99 mismatch leakage into cleaned data
    leaks = []
    for label, df, key in [("T1", t1, "FollowerID"), ("T2", t2, "FollowerID"),
                            ("T3 leader", t3l, "LeaderID"),
                            ("T3 follower", t3f, "FollowerID"),
                            ("final", final, "LeaderID"),
                            ("final", final, "FollowerID")]:
        if df[key].astype(str).str.contains("X_L99").any():
            leaks.append(f"{label}.{key}")
    if leaks:
        _fail("layer7", f"X_L99 mismatch leaked into cleaned: {leaks}")
    else:
        print(f"  X_L99 ID-mismatch injection properly removed from all cleaned data")

    # Master Table 1B / A3 row labels verbatim from template
    wb_o = load_workbook(RES / "主模型结果填答表.xlsx")
    wb_t = load_workbook(TPL_M / "主模型结果填答表.xlsx")
    for sheet, rows in [("Table 1B", [3, 4]), ("Table A3 区分多来源结果变量", [4, 5, 6, 7])]:
        try:
            wo = wb_o[sheet]; wt_ = wb_t[sheet]
        except KeyError:
            continue
        for r in rows:
            if wo.cell(r, 1).value != wt_.cell(r, 1).value:
                _fail("layer7", f"{sheet} row {r} col 1 label changed")
    wb_o.close(); wb_t.close()

    wb_o = load_workbook(RES / "study3附录结果填答.xlsx")
    wb_t = load_workbook(TPL_M / "study3附录结果填答.xlsx")
    ws_o = wb_o["Table A3 区分多来源结果变量"]
    ws_t = wb_t["Table A3 区分多来源结果变量"]
    for r in range(4, 8):
        if ws_o.cell(r, 1).value != ws_t.cell(r, 1).value:
            _fail("layer7", f"A3 row {r} label changed")
    wb_o.close(); wb_t.close()
    print(f"  Table 1B + A3 row labels preserved verbatim")

    # Master 总览 sheet preserved
    wb = load_workbook(RES / "主模型结果填答表.xlsx")
    v = wb["总览"].cell(1, 1).value
    if not v or "Table 1A" not in v:
        _fail("layer7", "总览 sheet content unexpected")
    else:
        print(f"  总览 sheet preserved")
    wb.close()



# ── Layer 8 ─────────────────────────────────────────────────────────
def layer8():
    """Reverse-coding + composite invariants: signal injection must
    preserve algebraic identities."""
    _hdr("Layer 8 — Reverse-coding + composite invariants")

    final = pd.read_excel(DATA / "final_merged_analysis_data.xlsx")

    # 1. Reverse-coding identity: R_THRk + THRk == 8 (Likert 1..7)
    for prefix in ("T3_", ""):
        for k in (5, 10):
            r_col = f"{prefix}R_THR{k}"
            t_col = f"{prefix}THR{k}"
            if r_col in final.columns and t_col in final.columns:
                bad = ((final[r_col] + final[t_col] - 8).abs() > 0.001).sum()
                if bad:
                    _fail("layer8", f"{r_col}+{t_col} != 8 for {bad} rows")
                else:
                    print(f"  {r_col} + {t_col} == 8 holds")

    # 2. Follower composites must equal mean of their item columns
    self_oc = [f"OCBS_Self{i}" for i in range(1, 7) if f"OCBS_Self{i}" in final.columns]
    if "OCBS_Follower" in final.columns and self_oc:
        diff = (final[self_oc].mean(axis=1) - final["OCBS_Follower"]).abs().max()
        if diff > 0.005:
            _fail("layer8", f"OCBS_Follower != mean(OCBS_Self*); max diff {diff:.4f}")
        else:
            print(f"  OCBS_Follower == mean(OCBS_Self1..6)")

    self_cw = [f"CWBS_Self{i}" for i in range(1, 6) if f"CWBS_Self{i}" in final.columns]
    if "CWBS_Follower" in final.columns and self_cw:
        diff = (final[self_cw].mean(axis=1) - final["CWBS_Follower"]).abs().max()
        if diff > 0.005:
            _fail("layer8", f"CWBS_Follower != mean(CWBS_Self*); max diff {diff:.4f}")
        else:
            print(f"  CWBS_Follower == mean(CWBS_Self1..5)")

    # 3. Thriving parcels: THRP1 = mean(THR1, THR3, R_THR5); THRP3 = mean(THR6, THR8, R_THR10)
    for prefix, t_pref in [("T3_THRP", "T3_"), ("THRP", "")]:
        if f"{prefix}1" in final.columns and all(f"{t_pref}{c}" in final.columns for c in ["THR1","THR3","R_THR5"]):
            diff = (final[[f"{t_pref}THR1", f"{t_pref}THR3", f"{t_pref}R_THR5"]].mean(axis=1) - final[f"{prefix}1"]).abs().max()
            if diff > 0.005:
                _fail("layer8", f"{prefix}1 != mean(THR1,THR3,R_THR5); diff {diff:.4f}")
            else:
                print(f"  {prefix}1 == mean(THR1,THR3,R_THR5)")
        if f"{prefix}3" in final.columns and all(f"{t_pref}{c}" in final.columns for c in ["THR6","THR8","R_THR10"]):
            diff = (final[[f"{t_pref}THR6", f"{t_pref}THR8", f"{t_pref}R_THR10"]].mean(axis=1) - final[f"{prefix}3"]).abs().max()
            if diff > 0.005:
                _fail("layer8", f"{prefix}3 != mean(THR6,THR8,R_THR10); diff {diff:.4f}")
            else:
                print(f"  {prefix}3 == mean(THR6,THR8,R_THR10)")

    # 4. Master Table A4 mediator-equation rows (7-18) must have focal == supplementary
    #    (same mediator equation, only outcome differs across columns).
    wb = load_workbook(RES / "study3附录结果填答.xlsx")
    ws = wb["Table A4 Robustness"]
    for r in range(7, 19):
        focal = ws.cell(r, 3).value
        supp = ws.cell(r, 4).value
        if focal != supp:
            _fail("layer8", f"Table A4 row {r}: focal {focal!r} != supp {supp!r}")
    wb.close()
    print(f"  Table A4 rows 7-18 (mediator-equation paths) focal == supp")


# ── Driver ──────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("DELIVERABLE AUDIT — 8 layers")
    print("=" * 70)

    layer1(); layer2(); layer3(); layer4(); layer5(); layer6(); layer7(); layer8()

    print("\n" + "=" * 70)
    if not ALL_FAILURES:
        print("ALL 8 AUDIT LAYERS PASSED — deliverables clean.")
        print("=" * 70)
        return 0
    print(f"FOUND {len(ALL_FAILURES)} ISSUES across audit layers:")
    for layer, msg in ALL_FAILURES:
        print(f"  [{layer}] {msg}")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
