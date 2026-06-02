"""Run every test_<module>.py and aggregate pass/fail."""
import subprocess, sys, glob, os
HERE = os.path.dirname(os.path.abspath(__file__))   # absolute, never empty
test_files = sorted(f for f in glob.glob(os.path.join(HERE, "test_*.py")) if "_common" not in f)
totals = {"pass": 0, "fail": 0}
failed = []
for f in test_files:
    name = os.path.basename(f)[5:-3]
    print(f"\n========== {name} ==========")
    py = sys.executable or "python3"
    r = subprocess.run([py, f], capture_output=True, text=True, cwd=HERE)
    print(r.stdout, end="")
    # parse "N/M passed" from last line regardless of exit code
    for line in r.stdout.splitlines()[::-1]:
        if "passed" in line and "/" in line:
            a, _, rest = line.strip().partition("/")
            b = rest.split()[0]
            try:
                totals["pass"] += int(a); totals["fail"] += int(b) - int(a)
            except ValueError:
                pass
            break
    if r.returncode != 0:
        failed.append(name)
        if r.stderr: print(r.stderr, end="")
print(f"\n===========================================")
print(f"TOTAL: {totals['pass']} passed, {totals['fail']} failed across {len(test_files)} modules")
if failed: print(f"FAILED modules: {failed}")
sys.exit(0 if not failed and totals["fail"] == 0 else 1)
