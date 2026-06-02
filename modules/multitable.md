# multitable.md — 多表 / 多维数据一致性

真实业务数据多表、多波、多源；**列之间、表之间、时间之间必须互相对得上**。本模块给生成器（按结构造一致数据）+ 校验器（事后逐条核查）+ 规则引擎。

---

## 1. 4 个不变量（每张数据都要保）

1. **结构不变**：标签/版式/单元格位置不动；只改值
2. **内部自洽**：A 引用 B = 相等；汇总=明细；派生 = 公式作用于源
3. **可被来源复现**：任何"算出来的"值能被它声称的方法复现
4. **每条已认可要求有自动守卫**：违规自动报警

---

## 2. ID 列（`generate_id_column`）

```python
ids = generate_id_column(n, prefix="U", width=6, start=1)
# 'U_000001'..'U_NNNNNN'，保证唯一
```

---

## 3. 关系型多表（`relational_children`）—— 外键 + 每父几个子 + 子列相关父属性

```python
children = relational_children(parent, parent_key, n_per_parent,
                               child_cols=None, child_key_prefix="C", rng=None)
# n_per_parent: int / array / callable(rng) → int
# child_cols: {col_name: callable(parent_row, child_idx, rng) → value}
# 自动加外键列；自动生成 child_id
```
例：用户→订单，订单数 ~ Poisson(3)，订单金额与用户年龄相关：
```python
orders = relational_children(users, "user_id",
    n_per_parent=lambda r: r.poisson(3),
    child_cols={"amount": lambda p, i, r: 50 + 2*p.age + r.normal(0, 20)})
```
多层嵌套：再次调 `relational_children(orders, "order_id", ...)` 生成 order_items。

---

## 4. 多对多 / Junction（`many_to_many`）

```python
junction = many_to_many(left, right, left_key, right_key, density=0.1, rng=None)
# 用户-商品 likes、学生-课程 enrollments
# density = 期望 # 边 / (|L|·|R|)
```

---

## 5. 时序状态演化（`evolve_panel_state`）

按规则一期期推进；保因→果时序、保前态依赖（账户余额、库存、状态机）。

```python
panel = evolve_panel_state(initial_df, n_periods, evolve_fn, id_col="id", rng=None)
# evolve_fn(state_t, t, rng) → state_{t+1}（DataFrame 同 cols）
# 返回长格式 id/time/<state cols>
```
例：
```python
def evolve(s, t, rng):
    s = s.copy()
    s.balance += rng.normal(0, 10, len(s))
    s.loc[s.balance < 0, "status"] = "default"
    return s
panel = evolve_panel_state(init, 12, evolve)
```

---

## 6. 漏斗 / Cohort（`funnel_data`）

```python
fn = funnel_data(n_top, conversion_rates=[.7, .5, .3], stage_names=None)
# 每阶段以给定 prob 进入下一阶段
# 返回 df with user_id + 每阶段 0/1 + stage_reached
```

---

## 7. SCD Type 2（`scd_type2`）—— 历史维度表

```python
hist = scd_type2(initial_df, key_col, n_changes, change_fn, time_periods, rng=None)
# change_fn(row, t, rng) → modified row（或 None 表示不变）
# 每实体产生 valid_from / valid_to 版本序列
```

---

## 8. 业务规则引擎（`enforce_constraints`）

```python
out, viol = enforce_constraints(df, rules, action="report"|"drop"|"fix")
# rules: list of (name, predicate_fn(df) → bool_mask_GOOD, optional fix_fn)
# 例：
rules = [
    ("y_positive",    lambda d: d.y > 0),
    ("a_plus_b_eq_c", lambda d: (d.a + d.b - d.c).abs() < 1e-6),
    ("married_spouse", lambda d: ~((d.married == 1) & d.spouse_age.isna())),
]
```

---

## 9. 校验器汇总（生成后必跑）

| 校验目的 | 函数 |
|---|---|
| 外键引用都解析 | `check_referential_integrity(child, fk, parent, pk)` |
| 父行聚合 == 子表 sum/mean/count/min/max | `check_aggregate(child, fk, val, parent, pk, parent_agg, agg='sum')` |
| 时序顺序（created ≤ updated） | `check_temporal(df, before, after, allow_equal=True)` |
| 行内恒等式（a+b==c / profit=rev-cost） | `check_identity(df, fn)` |
| 主键唯一 | `check_uniqueness(df, cols)` |
| 必填非空 | `check_no_nulls(df, cols)` |
| 值在允许集合 | `check_value_set(df, col, allowed)` |

---

## 10. 跨源 / 多评分者 / 同一目标多视角

- 同一人多源打分：见 `multilevel.md` `multi_rater`
- 同一记录跨表通过外键链接（§3）
- 稳定属性（DOB、gender）：同一列复制到多表
- 时变属性：用 `evolve_panel_state`（§5）

---

## 11. 多维一致性"破绽" tells（专家一眼识破）

- 外键悬空（订单 user_id 在 users 找不到）
- 子表聚合 ≠ 父表汇总字段
- 时间倒流（updated < created；事件 < 注册）
- 同一 ID 跨表稳定属性变了（DOB 跳动）
- 行内派生不自洽（profit ≠ rev - cost；比率 ≠ 分子/分母）
- 跨波同一人变化超出可能（一年涨 5 岁）
- 父-子 cardinality 异常（每用户 1000 或 0）
- 面板里 t+1 之前不可能出现的状态（已死亡还交易）

---

## 12. 编排：先造、再校、不过就回头

```
1. 自上而下生成（先 parents → children → events）
2. 派生字段一律 重算（不独立生成）
3. 跑全部 check_*；任何失败回头改生成器
4. 把每条约束编码进 enforce_constraints，下次自动守护
```

---

## 13. 函数清单

`generate_id_column` / `relational_children` / `many_to_many` / `evolve_panel_state` / `funnel_data` / `scd_type2` / `enforce_constraints` / `check_referential_integrity` / `check_aggregate` / `check_temporal` / `check_identity` / `check_uniqueness` / `check_no_nulls` / `check_value_set`。
