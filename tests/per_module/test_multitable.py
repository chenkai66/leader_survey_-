from _common import chk, summary
import numpy as np, pandas as pd, calibrate as C
rng = np.random.default_rng(7)
parents = pd.DataFrame({"user_id": C.generate_id_column(20, "U"),
                        "signup_age": rng.integers(20, 60, 20)})
children = C.relational_children(parents, "user_id",
    n_per_parent=lambda r: r.poisson(3),
    child_cols={"amount": lambda p,i,r: 50 + 5*p.signup_age + r.normal(0, 20)},
    rng=rng)
ok, _ = C.check_referential_integrity(children, "user_id", parents, "user_id")
chk("relational FK integrity", ok)
chk("relational child count varies", children.groupby("user_id").size().nunique() > 1)
parent2 = pd.DataFrame({"pid":["A","B","C"], "total":[10, 20, 30]})
child2 = pd.DataFrame({"pid":["A","A","B","B","C"], "val":[5,5,8,12,30]})
ok, _ = C.check_aggregate(child2, "pid", "val", parent2, "pid", "total", agg="sum")
chk("aggregate consistency", ok)
chk("temporal monotone", C.check_temporal(pd.DataFrame({"a":[1,2],"b":[2,3]}), "a", "b")[0])
chk("identity a+b==c", C.check_identity(pd.DataFrame({"a":[1,2], "b":[2,3], "c":[3,5]}), lambda r: r.a+r.b-r.c)[0])
out, viol = C.enforce_constraints(pd.DataFrame({"x":[1,2,3], "y":[1,0,3]}),
                                   [("y_pos", lambda d: d.y > 0)], action="drop", verbose=False)
chk("enforce_constraints drops", len(out)==2 and viol["y_pos"]==1)
L = pd.DataFrame({"user_id": C.generate_id_column(50, "U")})
R = pd.DataFrame({"item_id": C.generate_id_column(30, "I")})
m = C.many_to_many(L, R, "user_id", "item_id", density=0.05, rng=rng)
chk("many_to_many density approx", 40 < len(m) < 110)
init = pd.DataFrame({"id": C.generate_id_column(10, "A"), "balance": np.full(10, 100.0)})
panel = C.evolve_panel_state(init, 5, lambda s,t,r: s.assign(balance=s.balance + r.normal(0,5,len(s))), rng=rng)
chk("evolve_panel shape n*T", len(panel) == 50 and panel.time.nunique() == 5)
fn = C.funnel_data(1000, [0.7, 0.5, 0.3], rng=rng)
chk("funnel reach monotone non-incr",
    all(fn[f"stage_{i+1}"].sum() >= fn[f"stage_{i+2}"].sum() for i in range(3)))
hist = C.scd_type2(pd.DataFrame({"id":C.generate_id_column(10,"E"),"v":rng.standard_normal(10)}),
                    "id", n_changes=3, change_fn=lambda r,t,rng_: {**r,"v":r["v"]*1.05},
                    time_periods=12, rng=rng)
chk("SCD type-2 has valid_from/to", "valid_from" in hist.columns)
summary()
