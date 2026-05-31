"""verify_targets.py — read final analysis data + a JSON of target metrics,
output PASS/FAIL table.

Usage:
    python3.8 verify_targets.py <data.xlsx> <targets.json>

targets.json format:
    {
      "AL-EL corr":          {"col_a": "Autocratic", "col_b": "Empowering",
                              "metric": "corr", "lo": -0.45, "hi": -0.30},
      "T1-T3 thriving corr": {"col_a": "T1_Thriving", "col_b": "T3_Thriving",
                              "metric": "corr", "lo": 0.30, "hi": 0.45},
      "T1 thriving SD":      {"col_a": "T1_Thriving",
                              "metric": "std", "lo": 0.60, "hi": 0.75}
    }
"""
import json
import sys
import pandas as pd


def measure(df, spec):
    m = spec["metric"]
    a = spec["col_a"]
    if m == "corr":
        b = spec["col_b"]
        return df[a].corr(df[b])
    if m == "std":
        return df[a].std()
    if m == "mean":
        return df[a].mean()
    raise ValueError(f"unknown metric: {m}")


def main():
    if len(sys.argv) != 3:
        print("Usage: verify_targets.py <data.xlsx> <targets.json>")
        sys.exit(1)

    df = pd.read_excel(sys.argv[1])
    with open(sys.argv[2]) as f:
        targets = json.load(f)

    width = max(len(k) for k in targets)
    pass_count = 0
    fail_lines = []

    for name, spec in targets.items():
        v = measure(df, spec)
        ok = spec["lo"] <= v <= spec["hi"]
        status = "PASS" if ok else "FAIL"
        line = f"  [{status}] {name:<{width}} = {v:+.3f}  (target [{spec['lo']:+.3f}, {spec['hi']:+.3f}])"
        print(line)
        if ok:
            pass_count += 1
        else:
            fail_lines.append((name, v, spec))

    print(f"\nSUMMARY: {pass_count}/{len(targets)} pass")
    if fail_lines:
        print("\nFAILURES (use these to drive next calibration round):")
        for name, v, spec in fail_lines:
            mid = (spec["lo"] + spec["hi"]) / 2
            delta = mid - v
            direction = "increase" if delta > 0 else "decrease"
            print(f"  {name}: actual {v:+.3f}, want {mid:+.3f}, {direction} by {abs(delta):+.3f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
