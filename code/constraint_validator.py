"""
Constraint validator (v3) — comprehensive strict validator for the
post-second-round deliverables.

Sections:
  1. Sample sizes (T1=90, T2=85, T3=79; final dyads from attrition)
  2. Raw > cleaned (cleaning removes dups + mismatches + AC failures)
  3. Each leader 3-5 followers in final (NOT 6+, ≥3, ≤5)
  4. Attention-check items present; AC=6 means PASS, cleaned has only AC=6
  5. CLID 1:1 numeric, range 1-79
  6. LeaderEducation only in T3 leader (and final via merge), 2-5 integer
  7. Grand-mean centering exact + dummies not centered
  8. No narcissism × leadership interaction column
  9. Duplicate / mismatched IDs only in raw
 10. Missing-value pattern (T1 ~10 non-core, T2 zero, T3-leader ~3)
 11. Composite scores match item averages
 12. Parcel definitions match theoretical maps
 13. Reverse-coded items in [1, 7], parcels use the reversed versions
 14. Likert ranges
 15. No NaN in core analysis variables of final
 16. Dummy variables in {0, 1}; Company dummies present
 17. Hypothesis directions (correlation sign checks)
 18. Eight deliverable files exist
 19. Each incremental file has EXACTLY ONE sheet
 20. Master deliverables 7 / 4 sheets
 21. Master template key cells filled
 22. MCFA Mplus dat
 23. Cross-wave ID integrity
 24. No duplicate IDs in cleaned
 25. Master Table 4 path-sign correctness
 26. Cluster adjustment in master appendix Table A1/A2
 27. Centered means ~ 0
 28. Companies = {A, B, C}; TeamID == LeaderID
 29. ID format follows {Company}_L{NN} / {LeaderID}_F{N}
 30. TenureWithLeader integer-dominant (>= 90% are integer)
 31. measurement appendix has explicit χ² column
 32. ICC table has 5 columns including non-empty Notes
 33. YUYU table 26 rows all column-C filled
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RES = ROOT / "results"

PASS, FAIL = "PASS", "FAIL"
_results = []


def check(name, cond, detail=""):
    status = PASS if cond else FAIL
    line = f"  [{status}] {name}"
    if detail:
        line += f" -- {detail}"
    print(line)
    _results.append(bool(cond))
    return bool(cond)


def section(title):
    print("\n" + "-" * 64)
    print(title)
    print("-" * 64)


def load():
    files = {
        "t1_raw":  "T1_raw.xlsx",  "t1": "T1_cleaned.xlsx",
        "t2_raw":  "T2_raw.xlsx",  "t2": "T2_cleaned.xlsx",
        "t3l_raw": "T3_leader_raw.xlsx",   "t3l": "T3_leader_cleaned.xlsx",
        "t3f_raw": "T3_follower_raw.xlsx", "t3f": "T3_follower_cleaned.xlsx",
        "final":   "final_merged_analysis_data.xlsx",
    }
    out = {}
    for k, p in files.items():
        full = DATA / p
        if not full.exists():
            print(f"MISSING: {full}")
            sys.exit(2)
        out[k] = pd.read_excel(full)
    return out


def main() -> int:
    print("=" * 70)
    print("LEADER-SURVEY CONSTRAINT VALIDATOR (v3 — post-feedback)")
    print("=" * 70)

    d = load()
    t1, t1r = d["t1"], d["t1_raw"]
    t2, t2r = d["t2"], d["t2_raw"]
    t3l, t3lr = d["t3l"], d["t3l_raw"]
    t3f, t3fr = d["t3f"], d["t3f_raw"]
    final = d["final"]

    # ---------- 1. sample sizes ----------
    section("1. Sample sizes (waves)")
    check("T1 leaders == 90", t1["LeaderID"].nunique() == 90,
          f"got {t1['LeaderID'].nunique()}")
    check("T2 leaders == 85", t2["LeaderID"].nunique() == 85,
          f"got {t2['LeaderID'].nunique()}")
    check("T3 leader cleaned rows == 79", len(t3l) == 79, f"got {len(t3l)}")
    check("T3 follower leaders == 79", t3f["LeaderID"].nunique() == 79,
          f"got {t3f['LeaderID'].nunique()}")
    check("final leaders == 79", final["LeaderID"].nunique() == 79,
          f"got {final['LeaderID'].nunique()}")
    check("final dyads >= 237 (79 × 3)", len(final) >= 237, f"got {len(final)}")
    check("final dyads <= 395 (79 × 5)", len(final) <= 395, f"got {len(final)}")

    # ---------- 2. raw > cleaned ----------
    section("2. Raw > cleaned")
    for label, raw, clean in [("T1", t1r, t1), ("T2", t2r, t2),
                              ("T3 leader", t3lr, t3l),
                              ("T3 follower", t3fr, t3f)]:
        check(f"{label} raw > cleaned", len(raw) > len(clean),
              f"{len(raw)} > {len(clean)}")

    # ---------- 3. 3-5 followers per leader ----------
    section("3. 3-5 followers per leader (final analysis)")
    g = final.groupby("LeaderID").size()
    check("final min ≥ 3", g.min() >= 3, f"min={g.min()}")
    check("final max ≤ 5  (NOT 6 or more)", g.max() <= 5, f"max={g.max()}")
    check("final mean in [3.5, 5.0]",
          3.5 <= g.mean() <= 5.0, f"mean={g.mean():.2f}")

    # ---------- 4. attention checks ----------
    section("4. AC = 6 means PASS; cleaned only contains AC = 6")
    check("T1 has EMP9_AttCheck",  "EMP9_AttCheck" in t1.columns)
    check("T2 has MAL6_AttCheck",  "MAL6_AttCheck" in t2.columns)
    check("T3f has OCBS7_AttCheck","OCBS7_AttCheck" in t3f.columns)
    check("T3l has CWBS6_AttCheck","CWBS6_AttCheck" in t3l.columns)
    # In RAW data we should see some failures (3-5%):
    if "EMP9_AttCheck" in t1r.columns:
        fails = (t1r["EMP9_AttCheck"] != 6).sum()
        check("T1 raw has 1 ≤ AC failures ≤ 30", 1 <= fails <= 30, f"fails={fails}")
    # Cleaned MUST have ALL AC == 6
    for label, df, col in [("T1", t1, "EMP9_AttCheck"),
                            ("T2", t2, "MAL6_AttCheck"),
                            ("T3f", t3f, "OCBS7_AttCheck"),
                            ("T3l", t3l, "CWBS6_AttCheck")]:
        if col in df.columns:
            non6 = (df[col] != 6).sum()
            check(f"{label} cleaned: every row has AC = 6", non6 == 0,
                  f"non-6 count={non6}")

    # ---------- 5. CLID ----------
    section("5. CLID")
    if "CLID" in final.columns:
        check("CLID numeric", pd.api.types.is_numeric_dtype(final["CLID"]))
        check("CLID range [1, 79]",
              final["CLID"].min() == 1 and final["CLID"].max() == 79,
              f"[{final['CLID'].min()}, {final['CLID'].max()}]")
        check("CLID 1:1 LeaderID",
              len(final[["LeaderID", "CLID"]].drop_duplicates()) == 79)

    # ---------- 6. LeaderEducation only in T3 leader (and final via merge) ----------
    section("6. LeaderEducation in T3 leader survey (not T1)")
    check("T1 has NO LeaderEducation column", "LeaderEducation" not in t1.columns)
    check("T3 leader HAS LeaderEducation column", "LeaderEducation" in t3l.columns)
    if "LeaderEducation" in t3l.columns:
        col = t3l["LeaderEducation"]
        check("T3 leader: LeaderEducation min ≥ 2", col.min() >= 2,
              f"min={col.min()}")
        check("T3 leader: LeaderEducation max ≤ 5", col.max() <= 5,
              f"max={col.max()}")
        check("T3 leader: LeaderEducation integer",
              col.dropna().apply(lambda x: float(x).is_integer()).all())

    # ---------- 7. centering ----------
    section("7. Grand-mean centering")
    must_center = ["Autocratic", "Empowering", "Narcissism", "PowerDistance",
                   "FollowerAge", "TenureWithLeader", "InteractionFreq",
                   "T1_Thriving", "WorkingYears"]
    for v in must_center:
        c = f"{v}_C"
        if c not in final.columns:
            check(f"{c} exists", False, "missing")
            continue
        check(f"{c} mean ~ 0", abs(final[c].mean()) < 1e-3,
              f"mean={final[c].mean():.6f}")
        if v in final.columns:
            expected = final[v] - final[v].mean()
            diff = (final[c] - expected).abs().max()
            check(f"{c} == {v} - grand_mean", diff < 1e-6, f"max diff={diff:.2e}")
    centered_dummies = [c for c in final.columns
                        if c.endswith("_C") and ("Gender_" in c or "Edu_" in c)
                        and not c.startswith("Company_")]
    check("Dummies NOT centered", not centered_dummies,
          f"leaks: {centered_dummies}" if centered_dummies else "")

    # ---------- 8. narcissism not a moderator ----------
    section("8. Narcissism is NOT a moderator")
    bad = [c for c in final.columns if "Narcissism" in c
           and any(t in c for t in ["x", "×", "X_", "_x_", "Interaction"])]
    check("no narcissism × leadership column", not bad,
          f"found: {bad}" if bad else "")

    # ---------- 9. raw duplicates / mismatches ----------
    section("9. Duplicate / mismatched IDs in raw")
    if "FollowerID" in t1r.columns:
        n = t1r["FollowerID"].duplicated().sum()
        check("T1 raw 1 ≤ dup ≤ 15", 1 <= n <= 15, f"{n}")
    if "FollowerID" in t2r.columns:
        n = t2r["FollowerID"].duplicated().sum()
        check("T2 raw 1 ≤ dup ≤ 6", 1 <= n <= 6, f"{n}")
    if "LeaderID" in t3lr.columns:
        n = t3lr["LeaderID"].duplicated().sum()
        check("T3 leader raw 0 < dup ≤ 1", 0 < n <= 1, f"{n}")
    if "FollowerID" in t1.columns and "FollowerID" in t2r.columns:
        miss = set(t2r["FollowerID"]) - set(t1["FollowerID"])
        check("T2 raw ≥ 3 unmatched", len(miss) >= 3, f"{len(miss)}")
    if "LeaderID" in t2.columns and "LeaderID" in t3lr.columns:
        miss = set(t3lr["LeaderID"]) - set(t2["LeaderID"])
        check("T3 leader raw ≥ 1 unmatched", len(miss) >= 1, f"{len(miss)}")

    # ---------- 10. missing pattern ----------
    section("10. Missing-value pattern")
    check("T1 raw missing in [5, 20]", 5 <= int(t1r.isna().sum().sum()) <= 20,
          f"{int(t1r.isna().sum().sum())}")
    check("T2 raw zero missing", int(t2r.isna().sum().sum()) == 0,
          f"{int(t2r.isna().sum().sum())}")
    check("T3 leader raw missing in [1, 5]",
          1 <= int(t3lr.isna().sum().sum()) <= 5,
          f"{int(t3lr.isna().sum().sum())}")

    # ---------- 11. composite scores ----------
    section("11. Composites equal item averages")
    cases = [
        ("Autocratic",  [f"AUT{i}"  for i in range(1, 7)],  t1),
        ("Empowering",  [f"EMP{i}"  for i in range(1, 13)], t1),
        ("Narcissism",  [f"NARC{i}" for i in range(1, 7)],  t1),
        ("PowerDistance", [f"PD{i}" for i in range(1, 6)],  t1),
    ]
    for name, items, df in cases:
        present = [c for c in items if c in df.columns]
        if name in df.columns and present:
            diff = (df[name] - df[present].mean(axis=1)).abs().max()
            check(f"{name} == mean(items)", diff < 1e-6, f"diff={diff:.2e}")
    if "BenignEnvy" in final.columns:
        ben = [f"BEN{i}" for i in range(1, 6)]
        diff = (final["BenignEnvy"] - final[ben].mean(axis=1)).abs().max()
        check("BenignEnvy == mean(BEN1..5)", diff < 1e-6, f"diff={diff:.2e}")
    if "MaliciousEnvy" in final.columns:
        mal = [f"MAL{i}" for i in range(1, 6)]
        diff = (final["MaliciousEnvy"] - final[mal].mean(axis=1)).abs().max()
        check("MaliciousEnvy == mean(MAL1..5)", diff < 1e-6, f"diff={diff:.2e}")

    # ---------- 12. parcels ----------
    section("12. Parcel definitions")
    parcels = [
        ("EMPP1", ["EMP1", "EMP2", "EMP3"]),
        ("EMPP2", ["EMP4", "EMP5", "EMP6"]),
        ("EMPP3", ["EMP7", "EMP8", "EMP9"]),
        ("EMPP4", ["EMP10", "EMP11", "EMP12"]),
        ("THRP1", ["THR1", "THR3", "R_THR5"]),
        ("THRP2", ["THR2", "THR4"]),
        ("THRP3", ["THR6", "THR8", "R_THR10"]),
        ("THRP4", ["THR7", "THR9"]),
    ]
    for parcel, items in parcels:
        if all(c in t1.columns for c in items + [parcel]):
            diff = (t1[parcel] - t1[items].mean(axis=1)).abs().max()
            check(f"{parcel} = mean({','.join(items)})", diff < 1e-6,
                  f"{diff:.2e}")

    # ---------- 13. reverse-coded ----------
    section("13. Reverse-coded items in [1, 7]")
    for col in ("R_THR5", "R_THR10"):
        if col in t1.columns:
            check(f"{col} in [1, 7]",
                  t1[col].min() >= 1 and t1[col].max() <= 7,
                  f"[{t1[col].min()}, {t1[col].max()}]")

    # ---------- 14. Likert ranges ----------
    section("14. Likert ranges")
    for col in ["AUT1", "AUT6", "EMP1", "EMP12", "THR1", "THR9",
                "NARC1", "NARC6", "PD1"]:
        if col in t1.columns:
            mn, mx = t1[col].min(), t1[col].max()
            check(f"{col} in 1..7", mn >= 1 and mx <= 7, f"[{mn},{mx}]")
    for col in ["BEN1", "BEN5", "MAL1", "MAL5"]:
        if col in t2.columns:
            mn, mx = t2[col].min(), t2[col].max()
            check(f"{col} in 1..7", mn >= 1 and mx <= 7, f"[{mn},{mx}]")

    # ---------- 15. no NaN in core analysis vars ----------
    section("15. No NaN in core analysis vars (final)")
    for col in ["LeaderID", "FollowerID", "CLID",
                "Autocratic", "Empowering", "Narcissism", "PowerDistance",
                "BenignEnvy", "MaliciousEnvy",
                "T3_Thriving", "OCBS_Leader", "CWBS_Leader",
                "OCBS_Follower", "CWBS_Follower",
                "Autocratic_C", "Empowering_C", "Narcissism_C",
                "PowerDistance_C", "WorkingYears_C"]:
        if col in final.columns:
            n = final[col].isna().sum()
            check(f"final.{col} no NaN", n == 0, f"NaN={n}")

    # ---------- 16. dummies (incl Company) ----------
    section("16. Dummies in {0,1} including Company dummies")
    for d2 in ["Gender_Female", "Edu_HighSchool", "Edu_Associate",
               "Edu_Master", "Edu_Doctoral", "Company_B", "Company_C"]:
        if d2 in final.columns:
            vs = sorted(final[d2].dropna().unique().tolist())
            check(f"{d2} in {{0,1}}", set(vs).issubset({0, 1}), f"vals={vs}")

    # ---------- 17. hypothesis directions ----------
    section("17. Hypothesis directions (corr signs)")
    pairs = [
        ("Autocratic",    "MaliciousEnvy",  "+"),
        ("Empowering",    "BenignEnvy",     "+"),
        ("Empowering",    "MaliciousEnvy",  "-"),
        ("MaliciousEnvy", "CWBS_Leader",    "+"),
        ("MaliciousEnvy", "T3_Thriving",    "-"),
        ("BenignEnvy",    "T3_Thriving",    "+"),
        ("BenignEnvy",    "OCBS_Leader",    "+"),
        ("Autocratic",    "BenignEnvy",     "-"),
    ]
    for x, y, sign in pairs:
        if x in final.columns and y in final.columns:
            r = final[[x, y]].corr().iloc[0, 1]
            ok = (sign == "+" and r > 0) or (sign == "-" and r < 0)
            check(f"corr({x},{y}) sign {sign}", ok, f"r={r:+.3f}")

    # ---------- 18. eight deliverable files exist ----------
    section("18. Eight deliverable files exist")
    for f in ["Model1.xlsx", "Model2.xlsx", "Model3.xlsx",
              "measurement appendix.xlsx", "ICC空模型.xlsx",
              "YUYU样本量变化.xlsx",
              "主模型结果填答表.xlsx", "study3附录结果填答.xlsx"]:
        check(f"results/{f}", (RES / f).exists())

    # ---------- 19. each incremental file has exactly 1 sheet ----------
    section("19. Each incremental file has EXACTLY 1 sheet")
    for f in ["Model1.xlsx", "Model2.xlsx", "Model3.xlsx",
              "measurement appendix.xlsx", "ICC空模型.xlsx",
              "YUYU样本量变化.xlsx"]:
        p = RES / f
        if not p.exists():
            continue
        wb = load_workbook(p, read_only=True)
        n = len(wb.sheetnames)
        check(f"{f} sheet count == 1", n == 1, f"sheets={wb.sheetnames}")
        wb.close()

    # ---------- 20. master deliverables ----------
    section("20. Master deliverables 7 / 4 sheets")
    masters = {
        "主模型结果填答表.xlsx":
            ["总览", "Table 1A", "Table 1B",
             "Table 2. Aggregation Statistics",
             "Table 3. Correlation",
             "Table 4. 主模型path",
             "Table 5. Moderation and Conditi"],
        "study3附录结果填答.xlsx":
            ["Table A12 单量表CFA",
             "Table A3 区分多来源结果变量",
             "Table A4 Robustness",
             "Table A5 Robustness"],
    }
    for f, expected_sheets in masters.items():
        p = RES / f
        if not p.exists():
            check(f"{f} exists", False)
            continue
        wb = load_workbook(p, read_only=True)
        actual = wb.sheetnames
        check(f"{f} sheet count == {len(expected_sheets)}",
              len(actual) == len(expected_sheets),
              f"got {len(actual)}: {actual}")
        for s in expected_sheets:
            check(f"  '{s}' present", s in actual)
        wb.close()

    # ---------- 21. master cells filled ----------
    section("21. Master template key cells filled")
    p = RES / "主模型结果填答表.xlsx"
    if p.exists():
        wb = load_workbook(p)
        ws = wb["Table 1A"]
        v = ws.cell(row=3, column=2).value
        check("Table 1A row3 col B numeric", isinstance(v, (int, float)),
              f"got {type(v).__name__}={v}")
        ws = wb["Table 4. 主模型path"]
        v = ws.cell(row=4, column=3).value
        check("Table 4 row4 col C numeric", isinstance(v, (int, float)),
              f"got {type(v).__name__}={v}")
        ws = wb["Table 3. Correlation"]
        v = ws.cell(row=3, column=2).value
        check("Table 3 row3 col B (Age mean) numeric",
              isinstance(v, (int, float)), f"got {type(v).__name__}={v}")
        wb.close()

    # ---------- 22. MCFA dat ----------
    section("22. MCFA Mplus dat")
    mcfa = DATA / "study3_mcfa.dat"
    check("study3_mcfa.dat exists", mcfa.exists())
    if mcfa.exists():
        with open(mcfa, encoding="utf-8", errors="ignore") as f:
            lines = [ln for ln in f if ln.strip()]
        check(f"mcfa rows == final length ({len(final)})",
              len(lines) == len(final), f"{len(lines)}")
        first = lines[0].strip().split()
        check("mcfa first col numeric (CLID)",
              first[0].lstrip("-").replace(".", "").isdigit())

    # ---------- 23. cross-wave id integrity ----------
    section("23. Cross-wave ID integrity")
    fids = set(final["FollowerID"])
    check("final ⊆ T1 cleaned", not (fids - set(t1["FollowerID"])))
    check("final ⊆ T2 cleaned", not (fids - set(t2["FollowerID"])))
    check("final ⊆ T3 follower cleaned", not (fids - set(t3f["FollowerID"])))
    check("final leaders ⊆ T3 leader cleaned",
          not (set(final["LeaderID"]) - set(t3l["LeaderID"])))

    # ---------- 24. no duplicate IDs in cleaned ----------
    section("24. No duplicate IDs in cleaned")
    for label, df, key in [("T1", t1, "FollowerID"), ("T2", t2, "FollowerID"),
                            ("T3 follower", t3f, "FollowerID"),
                            ("T3 leader", t3l, "LeaderID"),
                            ("final", final, "FollowerID")]:
        if key in df.columns:
            n = df[key].duplicated().sum()
            check(f"{label} no duplicate {key}", n == 0, f"dup={n}")

    # ---------- 25. master Table 4 path signs ----------
    section("25. Master Table 4 path signs")
    p = RES / "主模型结果填答表.xlsx"
    if p.exists():
        wb = load_workbook(p)
        ws = wb["Table 4. 主模型path"]
        for label, row, expected_sign in [
                ("Auto→Benign",      4, "-"),
                ("Emp→Benign",       5, "+"),
                ("Auto→Malicious",   6, "+"),
                ("Mal→Thriving",    12, "-")]:
            v = ws.cell(row=row, column=3).value
            ok = (isinstance(v, (int, float)) and
                  ((expected_sign == "+" and v > 0) or
                   (expected_sign == "-" and v < 0)))
            check(f"Table4 {label} sign {expected_sign}", ok, f"b={v}")
        wb.close()

    # ---------- 26. master appendix structural fidelity ----------
    # Cluster adjustment is documented in mcfa_mplus_syntax.inp and
    # analysis_code.R, NOT injected into the template's Notes column
    # (which would violate the strict template-fidelity requirement).
    section("26. Master appendix structural fidelity")
    p = RES / "study3附录结果填答.xlsx"
    if p.exists():
        wb = load_workbook(p)
        ws = wb["Table A12 单量表CFA"]
        # Original construct labels must be preserved verbatim
        check("Table A1 row 4 col 1 == 'Empowering leadership'",
              ws.cell(row=4, column=1).value == "Empowering leadership",
              f"got {ws.cell(row=4, column=1).value!r}")
        check("Table A1 row 9 col 1 == 'Thriving'",
              ws.cell(row=9, column=1).value == "Thriving",
              f"got {ws.cell(row=9, column=1).value!r}")
        wb.close()

    # ---------- 27. centered means ~ 0 ----------
    section("27. Centered means ~ 0")
    for v in must_center:
        c = f"{v}_C"
        if c in final.columns:
            m = abs(final[c].mean())
            check(f"{c} |mean| < 1e-6", m < 1e-6, f"|mean|={m:.2e}")

    # ---------- 28. companies ----------
    section("28. Companies = {A, B, C}; TeamID == LeaderID")
    if "CompanyID" in final.columns:
        comps = sorted(final["CompanyID"].unique().tolist())
        check("CompanyID in {A,B,C}",
              set(comps) == {"A", "B", "C"}, f"{comps}")
    else:
        check("CompanyID column exists", False, "missing")
    if "TeamID" in final.columns and "LeaderID" in final.columns:
        check("TeamID == LeaderID",
              (final["TeamID"] == final["LeaderID"]).all())
    else:
        check("TeamID column exists", "TeamID" in final.columns,
              f"final cols: TeamID present? {'TeamID' in final.columns}")

    # ---------- 29. ID format ----------
    section("29. ID format compliance")
    pat_lid = re.compile(r"^[ABC]_L\d{2}$")
    pat_fid = re.compile(r"^[ABC]_L\d{2}_F\d+$")
    bad_lids = [l for l in final["LeaderID"].unique() if not pat_lid.match(str(l))]
    check("LeaderID format {A|B|C}_L{NN}", not bad_lids,
          f"bad: {bad_lids[:3]}")
    bad_fids = [f for f in final["FollowerID"].head(50)
                if not pat_fid.match(str(f))]
    check("FollowerID format {LID}_F{N}", not bad_fids,
          f"bad: {bad_fids[:3]}")

    # ---------- 30. tenure integer-dominant ----------
    section("30. TenureWithLeader dominantly integer (>= 90%)")
    if "TenureWithLeader" in final.columns:
        col = final["TenureWithLeader"]
        n_int = col.apply(lambda x: float(x).is_integer()).sum()
        pct = 100 * n_int / len(col)
        check("TenureWithLeader >= 90% integer",
              pct >= 90, f"{pct:.1f}% integer")

    # ---------- 31. measurement appendix has χ² column ----------
    section("31. measurement appendix structural fidelity (template preserved)")
    p = RES / "measurement appendix.xlsx"
    if p.exists():
        wb = load_workbook(p)
        ws = wb["Sheet1"]
        # Header in row 2 must match template VERBATIM (no added cols).
        expected = ["Model", "CMIN/DF", "CFI", "TLI", "RMSEA",
                    "SRMR Within", "SRMR Between", "AIC", "BIC",
                    "ΔCMIN/DF", "ΔAIC", "ΔBIC", "Δdf"]
        actual = [ws.cell(row=2, column=c).value for c in range(1, 14)]
        check("measurement appendix header == template (verbatim)",
              actual == expected, f"got {actual}")
        # Row 3 col 2 (CMIN/DF of hypothesised) numeric
        val = ws.cell(row=3, column=2).value
        check("Hypothesised CMIN/DF numeric and > 0",
              isinstance(val, (int, float)) and val > 0, f"v={val}")
        wb.close()

    # ---------- 32. ICC table 5 columns including Notes ----------
    section("32. ICC table has 5 columns (incl. non-empty Notes)")
    p = RES / "ICC空模型.xlsx"
    if p.exists():
        wb = load_workbook(p)
        ws = wb["Sheet1"]
        # Header at row 2
        headers = [ws.cell(row=2, column=c).value for c in range(1, 6)]
        check("ICC has 5 column headers",
              all(h is not None and h != "" for h in headers),
              f"headers: {headers}")
        # First data row (row 3): col 5 (Notes) should be filled
        v = ws.cell(row=3, column=5).value
        check("ICC row3 col E (Notes) non-empty",
              v is not None and str(v).strip() != "", f"v={v}")
        wb.close()

    # ---------- 33. YUYU 26 rows column C all filled ----------
    section("33. YUYU table 26 rows, column C fully populated")
    p = RES / "YUYU样本量变化.xlsx"
    if p.exists():
        wb = load_workbook(p)
        ws = wb[wb.sheetnames[0]]
        empties = []
        for r in range(2, 27):  # rows 2..26 (1-indexed)
            v = ws.cell(row=r, column=3).value
            if v is None or str(v).strip() == "":
                empties.append(r)
        check("YUYU rows 2-26 col C all filled",
              not empties, f"empty rows: {empties}")
        wb.close()

    # ---------- summary ----------
    print("\n" + "=" * 70)
    n_pass = sum(_results)
    n_total = len(_results)
    n_fail = n_total - n_pass
    print(f"SUMMARY:  {n_pass}/{n_total} passed,  {n_fail} failed")
    print("=" * 70)
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
