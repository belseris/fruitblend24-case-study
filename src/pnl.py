"""P&L tables: item contribution, kitchen and company P&L, budget variance."""
import numpy as np
import pandas as pd

KEYS = ["month", "kitchen", "sku"]
# Enriched order column -> P&L column. All THB, except cups.
SALES = {"units_sold": "cups", "list_revenue_thb": "list_revenue", "discount_thb": "discount",
         "gross_revenue_thb": "gross_revenue", "commission_thb": "commission",
         "net_revenue_thb": "net_revenue", "fruit_cost_thb": "fruit",
         "pack_labor_thb": "pack_labor", "cm_thb": "cm"}
SUMS = list(SALES.values()) + ["waste_units", "waste_cost", "gp_a", "gp_b", "gross_profit"]

# Statement lines in order: (label, column). Ratios are added after the THB lines.
STATEMENT = [
    ("Cups sold", "cups"),
    ("List revenue", "list_revenue"),
    ("Discount", "discount"),
    ("Gross revenue", "gross_revenue"),
    ("Commission", "commission"),
    ("Net revenue", "net_revenue"),
    ("Fruit cost", "fruit"),
    ("Packaging + labor", "pack_labor"),
    ("Contribution margin (GP-B)", "cm"),
    ("Waste cost", "waste_cost"),
    ("Gross profit (GP-C)", "gross_profit"),
    ("Kitchen overhead", "overhead"),
    ("Operating profit", "operating_profit"),
]
RATIOS = [
    ("GP-C % of gross revenue", "gross_profit", "gross_revenue"),
    ("Operating margin %", "operating_profit", "gross_revenue"),
    ("Commission % of gross revenue", "commission", "gross_revenue"),
    ("Fruit % of gross revenue", "fruit", "gross_revenue"),
    ("Waste % of gross revenue", "waste_cost", "gross_revenue"),
]


def month_key(dates: pd.Series) -> pd.Series:
    """Month as 'YYYY-MM' text, so tables sort and export cleanly."""
    return dates.dt.strftime("%Y-%m")


def add_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Add % columns from summed THB (never average percentages)."""
    out = df.copy()
    rev = out["gross_revenue"].replace(0, np.nan)
    out["gp_pct"] = out["gross_profit"] / rev * 100
    out["waste_rate_pct"] = out["waste_units"] / (out["cups"] + out["waste_units"]).replace(0, np.nan) * 100
    if "operating_profit" in out:
        out["op_margin_pct"] = out["operating_profit"] / rev * 100
    return out


def contribution(e: pd.DataFrame, sheets: dict) -> pd.DataFrame:
    """Month x kitchen x sku: sales, costs, waste and three GP definitions."""
    sales = (e.assign(month=month_key(e["date"])).groupby(KEYS)[list(SALES)].sum()
             .rename(columns=SALES))
    w = sheets["waste_daily"]
    waste = (w.assign(month=month_key(w["date"])).groupby(KEYS)
             .agg(waste_units=("units_wasted", "sum"), waste_cost=("est_waste_cost_thb", "sum")))
    # Outer join: a kitchen can waste an item in a month with no sales of it.
    c = sales.join(waste, how="outer").fillna(0.0).reset_index()
    c["gp_a"] = c["gross_revenue"] - c["fruit"] - c["pack_labor"]   # before commission and waste
    c["gp_b"] = c["cm"]                                              # before waste
    c["gross_profit"] = c["cm"] - c["waste_cost"]                    # GP-C, main definition
    return add_ratios(c)


def kitchen_pnl(c: pd.DataFrame, sheets: dict) -> pd.DataFrame:
    """Month x kitchen P&L with fixed overhead and operating profit."""
    k = c.groupby(["month", "kitchen"])[SUMS].sum().reset_index()
    oh = sheets["kitchen_overhead"][["kitchen", "fixed_monthly_overhead_thb"]]
    k = k.merge(oh, on="kitchen", how="left", validate="many_to_one")
    assert k["fixed_monthly_overhead_thb"].notna().all(), "a kitchen has no overhead row"
    k = k.rename(columns={"fixed_monthly_overhead_thb": "overhead"})
    k["operating_profit"] = k["gross_profit"] - k["overhead"]
    return add_ratios(k)


def company_pnl(k: pd.DataFrame) -> pd.DataFrame:
    """Month-level company P&L = sum of the kitchens."""
    m = k.groupby("month")[SUMS + ["overhead", "operating_profit"]].sum().reset_index()
    return add_ratios(m)


def as_statement(df: pd.DataFrame) -> pd.DataFrame:
    """P&L lines as rows, months as columns, plus an FY total column."""
    lines = [label for label, _ in STATEMENT]
    cols = [col for _, col in STATEMENT]
    s = df.set_index("month")[cols].T
    s.index = lines
    s["FY"] = s.sum(axis=1)
    totals = df[cols].sum()
    for label, num, den in RATIOS:
        by_month = (df.set_index("month")[num] / df.set_index("month")[den] * 100).tolist()
        s.loc[label] = by_month + [totals[num] / totals[den] * 100]
    return s


def budget_variance(m: pd.DataFrame, sheets: dict, gp: str = "gross_profit") -> pd.DataFrame:
    """Revenue and GP vs budget by month. GP variance = revenue effect + margin effect."""
    b = sheets["monthly_budget"].assign(month=lambda d: month_key(d["month"]))
    v = m[["month", "gross_revenue", gp]].merge(
        b[["month", "budget_revenue_thb", "budget_gross_profit_thb"]],
        on="month", how="left", validate="one_to_one")
    assert v["budget_revenue_thb"].notna().all(), "a month has no budget"
    v = v.rename(columns={gp: "gross_profit", "budget_revenue_thb": "budget_revenue",
                          "budget_gross_profit_thb": "budget_gp"})
    v["budget_margin_pct"] = v["budget_gp"] / v["budget_revenue"] * 100
    v["gp_pct"] = v["gross_profit"] / v["gross_revenue"] * 100
    v["revenue_var"] = v["gross_revenue"] - v["budget_revenue"]
    v["revenue_var_pct"] = v["revenue_var"] / v["budget_revenue"] * 100
    v["gp_var"] = v["gross_profit"] - v["budget_gp"]
    v["gp_var_pct"] = v["gp_var"] / v["budget_gp"] * 100
    # Revenue effect: the revenue gap earned at the budget margin.
    v["revenue_effect"] = v["revenue_var"] * v["budget_margin_pct"] / 100
    # Margin effect: actual revenue earned at actual minus budget margin.
    v["margin_effect"] = v["gross_profit"] - v["gross_revenue"] * v["budget_margin_pct"] / 100
    assert np.allclose(v["revenue_effect"] + v["margin_effect"], v["gp_var"]), "variance does not close"
    return v


def margin_gap(c: pd.DataFrame, v: pd.DataFrame, by: str) -> pd.DataFrame:
    """Each group's GP minus its revenue at the budget margin. Sums to the margin effect."""
    g = c.groupby(["month", by])[["gross_revenue", "gross_profit"]].sum().reset_index()
    g = g.merge(v[["month", "budget_margin_pct"]], on="month", how="left", validate="many_to_one")
    g["gp_pct"] = g["gross_profit"] / g["gross_revenue"].replace(0, np.nan) * 100
    g["gap"] = g["gross_profit"] - g["gross_revenue"] * g["budget_margin_pct"] / 100
    check = g.groupby("month")["gap"].sum().reindex(v["month"])
    assert np.allclose(check.to_numpy(), v["margin_effect"].to_numpy()), f"{by} gaps != margin effect"
    return g


def gp_bridge(v: pd.DataFrame, item_gap: pd.DataFrame, by: str = "sku") -> pd.DataFrame:
    """Waterfall steps: budget GP -> revenue effect -> one gap per group -> actual GP."""
    gaps = item_gap.groupby(by)["gap"].sum().sort_values()
    steps = ([("Budget GP", "total", v["budget_gp"].sum()),
              ("Revenue effect", "step", v["revenue_effect"].sum())]
             + [(f"{name} margin gap", "step", val) for name, val in gaps.items()]
             + [("Actual GP", "total", v["gross_profit"].sum())])
    b = pd.DataFrame(steps, columns=["step", "kind", "thb"])
    end = b.loc[b["kind"] == "step", "thb"].sum() + b["thb"].iloc[0]
    assert np.isclose(end, b["thb"].iloc[-1]), "bridge does not close"
    return b


def menu_matrix(c: pd.DataFrame, months: list[str], by: list[str] | None = None) -> pd.DataFrame:
    """Cups per day vs GP per cup after waste. Cut lines are averages within each group."""
    by = by or []
    d = c[c["month"].isin(months)]
    g = d.groupby(by + ["sku"])[["cups", "gross_revenue", "gross_profit", "waste_units"]].sum().reset_index()
    # Days on sale: days of the months where the item sold at least one cup.
    days = (d[d["cups"] > 0].groupby(by + ["sku"])["month"].unique()
            .apply(lambda ms: sum(pd.Period(x).days_in_month for x in ms)).rename("days"))
    g = g.merge(days.reset_index(), on=by + ["sku"], how="left", validate="one_to_one")
    g["cups_per_day"] = g["cups"] / g["days"]
    g["gp_per_cup"] = g["gross_profit"] / g["cups"]
    g["waste_rate_pct"] = g["waste_units"] / (g["cups"] + g["waste_units"]) * 100
    # Popularity line: plain mean of items. Profit line: cup-weighted mean GP per cup.
    if by:
        grp = g.groupby(by)
        g["pop_line"] = grp["cups_per_day"].transform("mean")
        g["profit_line"] = grp["gross_profit"].transform("sum") / grp["cups"].transform("sum")
    else:
        g["pop_line"] = g["cups_per_day"].mean()
        g["profit_line"] = g["gross_profit"].sum() / g["cups"].sum()
    hi_pop = g["cups_per_day"] >= g["pop_line"]
    hi_gp = g["gp_per_cup"] >= g["profit_line"]
    g["menu_class"] = np.select([hi_pop & hi_gp, hi_pop & ~hi_gp, ~hi_pop & hi_gp],
                                ["Star", "Plowhorse", "Puzzle"], "Dog")
    return g
