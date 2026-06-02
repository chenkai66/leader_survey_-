"""Test the harness functions: inventory, help, recipes, generate_from_spec, validate."""
from _common import chk, summary
import numpy as np, calibrate as C
chk("INVENTORY has 11 categories", len(C.INVENTORY) == 12)  # 12 incl domain-specific
chk("list_functions returns 130+", len(C.list_functions()) >= 130)
chk("list_functions by category", len(C.list_functions("regression")) >= 8)
# Recipes
chk("RECIPES non-empty", len(C.RECIPES) >= 15)
chk("show_recipe returns code", C.show_recipe("ab_test_power_sim") is not None)
chk("show_recipe unknown returns None", C.show_recipe("nonexistent_xyz") is None)
# Spec → df → validate
spec = {"n": 1500,
        "columns": [{"name":"a","dist":"normal","mean":5,"sd":1},
                    {"name":"b","dist":"lognormal","mu":0,"sigma":0.5}],
        "correlations": {("a","b"): 0.3},
        "constraints": [{"type":"range","col":"a","lo":0,"hi":10}]}
df = C.generate_from_spec(spec, rng=np.random.default_rng(0))
chk("generate_from_spec shape", len(df) == 1500 and set(df.columns) == {"a","b"})
chk("generate_from_spec range enforced", df.a.min() >= 0 and df.a.max() <= 10)
report = C.validate(df, spec)
chk("validate reports summary", "summary" in report)
chk("validate all pass", "0 fail" in report["summary"].replace("/", " ") or all(item[-1] for item in report["distribution"] + report["correlation"]))
# Seed
S = C.Seed(42); r1 = S.rng().standard_normal(5)
S2 = C.Seed(42); r2 = S2.rng().standard_normal(5)
chk("Seed reproducibility", np.allclose(r1, r2))
summary()
