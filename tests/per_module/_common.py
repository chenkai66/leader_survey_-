"""Shared test helper for per-module test files."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
PASS = []
def chk(name, cond, detail=""):
    PASS.append(bool(cond))
    status = "PASS" if cond else "**FAIL**"
    print(f"  [{status}] {name} {detail}")
def summary(exit=True):
    print(f"\n{sum(PASS)}/{len(PASS)} passed")
    if exit:
        sys.exit(0 if all(PASS) else 1)
