"""Scenario P&L for Sep-Nov 2026: one model per month x kitchen x item, levers applied in order."""
import numpy as np
import pandas as pd
from scipy.stats import norm

from src.forecast import normal_waste_short
from src.load_clean import BERRY

CODES = ["RC101", "RC102", "RC103"]
RAINY = {"2026-09", "2026-10"}           # RC103 runs in the rainy months only
KEYS = ["month", "kitchen", "sku"]
LINES = ["demand", "cups", "short_cups", "waste_cups", "prep_cups", "gross_revenue", "commission",
         "fruit", "pack_labor", "waste_cost", "gross_profit"]


def promo_per_month(e: pd.DataFrame) -> pd.DataFrame:
    """Promo cups and discount THB a month per code x kitchen x item, from the 12 months of history."""
    e = e.assign(month=e["date"].dt.strftime("%Y-%m"))
    on_sale = e.groupby("sku")["month"].nunique()
    rainy_hist = {"2025-09", "2025-10", "2026-06", "2026-07", "2026-08"}
    rainy_on_sale = e[e["month"].isin(rainy_hist)].groupby("sku")["month"].nunique()
    g = (e[e["base_code"] != "RC000"].groupby(["base_code", "kitchen", "sku"])
         [["units_sold", "discount_thb"]].sum().reset_index())
    # RC103 is spread over the rainy months only; RC101/RC102 over every month on sale.
    months = np.where(g["base_code"] == "RC103", g["sku"].map(rainy_on_sale), g["sku"].map(on_sale))
    g["promo_cups"] = g["units_sold"] / months
    g["discount"] = g["discount_thb"] / months
    return g[["base_code", "kitchen", "sku", "promo_cups", "discount"]]


def promo_lift(promo_inc: pd.DataFrame) -> dict:
    """Cups on promo / baseline cups from lesson 7: RC101 per item, RC102/RC103 per code."""
    lift = {}
    for _, r in promo_inc.iterrows():
        if r["level"] == "rc101_sku":
            lift[("RC101", r["sku"])] = r["cups"] / r["baseline_cups"]
        elif r["level"] == "code" and r["code"] != "RC101":
            lift[(r["code"], "All")] = r["cups"] / r["baseline_cups"]
    return lift


def build_inputs(fc: pd.DataFrame, p: pd.DataFrame, e: pd.DataFrame, sheets: dict,
                 promo_inc: pd.DataFrame, cv: pd.Series, cost_months: list[str]) -> pd.DataFrame:
    """One row per month x kitchen x item with demand, prices, costs, promo and waste inputs."""
    d = (fc.groupby(KEYS).agg(demand=("forecast", "sum"), days=("date", "nunique")).reset_index())
    uc = sheets["unit_cost"].set_index("sku")
    d["list_price"] = d["sku"].map(uc["base_price_thb"])
    d["pack_cup"] = d["sku"].map(uc["pack_labor_per_cup_thb"])

    recent = e[e["date"].dt.strftime("%Y-%m").isin(cost_months)]
    by_ki = recent.groupby(["kitchen", "sku"])[["commission_thb", "gross_revenue_thb"]].sum()
    comm = (by_ki["commission_thb"] / by_ki["gross_revenue_thb"]).rename("comm_rate")
    by_i = recent.groupby("sku")[["fruit_cost_thb", "units_sold"]].sum()
    fruit = (by_i["fruit_cost_thb"] / by_i["units_sold"]).rename("fruit_cup")
    pw = p[p["month"].isin(cost_months)]
    w_i = pw.groupby("sku")[["waste_cost", "wasted"]].sum()
    co = (w_i["waste_cost"] / w_i["wasted"]).rename("co")
    w_ki = (pw.groupby(["kitchen", "sku"])["wasted"].sum() / pw.groupby(["kitchen", "sku"])["date"].nunique()
            ).rename("habit_waste_per_day")
    d = (d.join(comm, on=["kitchen", "sku"]).join(fruit, on="sku").join(co, on="sku")
         .join(w_ki, on=["kitchen", "sku"]).join(cv.rename("cv"), on=["kitchen", "sku"]))

    pm = promo_per_month(e)
    lift = promo_lift(promo_inc)
    for code in CODES:
        x = pm[pm["base_code"] == code].set_index(["kitchen", "sku"])
        d[f"promo_{code}"] = d.join(x["promo_cups"], on=["kitchen", "sku"])["promo_cups"].fillna(0.0)
        d[f"disc_{code}"] = d.join(x["discount"], on=["kitchen", "sku"])["discount"].fillna(0.0)
        if code == "RC103":
            off = ~d["month"].isin(RAINY)
            d.loc[off, [f"promo_{code}", f"disc_{code}"]] = 0.0
        d[f"lift_{code}"] = d["sku"].map(lambda s, c=code: lift.get((c, s), lift.get((c, "All"), 1.0)))
    assert not d.isna().any().any(), f"missing inputs: {d.columns[d.isna().any()].tolist()}"
    return d


def _killed(d, code, kill):
    return d["sku"].isin([s for c, s in kill if c == code]) | ((code, "All") in kill)


def run(d: pd.DataFrame, s: dict, eps: float = -1.5) -> pd.DataFrame:
    """Apply one scenario to the inputs. Order: promos, price, demand shock, prep rule, delist."""
    out = d[KEYS].copy()
    kill = s.get("kill", set())
    prices = s.get("prices", {})
    dm, fm = s.get("demand_mult", 1.0), s.get("fruit_mult", 1.0)

    # 1. A killed promo loses its lift: promo cups go back to baseline cups, at list price.
    cups = d["demand"].copy()
    disc = pd.Series(0.0, index=d.index)
    for code in CODES:
        k = _killed(d, code, kill)
        cups -= (d[f"promo_{code}"] * (1 - 1 / d[f"lift_{code}"])).where(k, 0.0)
        disc += d[f"disc_{code}"].where(~k, 0.0)

    # 2. List price change moves cups with constant elasticity; promo discount % stays the same.
    new_price = d["sku"].map(prices).fillna(d["list_price"])
    ratio = new_price / d["list_price"]
    f = ratio ** eps
    plan_demand = cups * f
    demand = plan_demand * dm
    disc = disc * f * ratio * dm
    revenue_full = demand * new_price - disc

    # 3. Costs per cup. Fruit shock also raises the cost of a wasted cup (its fruit part).
    fruit_cup = d["fruit_cup"] * fm
    co = d["co"] + d["fruit_cup"] * (fm - 1)

    # 4. Waste: habit items keep today's cups a day; rule items prep at the critical ratio.
    waste = d["habit_waste_per_day"] * d["days"]
    short = pd.Series(0.0, index=d.index)
    rule = d["sku"].isin(s.get("rule_items", []))
    if rule.any():
        z = d["sku"].map(s["z"])
        sd = d["cv"] * demand
        prep = plan_demand * dm * (1 + z * d["cv"])   # prep follows demand (rolling rule)
        w_r, s_r = normal_waste_short(demand, sd, prep)
        waste = waste.where(~rule, w_r)
        short = short.where(~rule, s_r)
    sold = demand - short

    out["demand"] = demand
    out["cups"] = sold
    out["short_cups"] = short
    out["waste_cups"] = waste
    out["prep_cups"] = sold + waste   # prepared = sold + wasted
    out["gross_revenue"] = revenue_full * sold / demand
    out["commission"] = out["gross_revenue"] * d["comm_rate"]
    out["fruit"] = sold * fruit_cup
    out["pack_labor"] = sold * d["pack_cup"]
    out["waste_cost"] = waste * co
    out["gross_profit"] = (out["gross_revenue"] - out["commission"] - out["fruit"]
                           - out["pack_labor"] - out["waste_cost"])
    if s.get("delist"):
        out.loc[out["sku"] == BERRY, LINES] = 0.0
    return out


def rule_z(d: pd.DataFrame, s: dict, eps: float = -1.5, add: float = 0.1) -> pd.DataFrame:
    """Cu, Co, CR, CR used (+ add) and z per item, with Cu = CM per cup at the scenario's own prices."""
    keep = {k: v for k, v in s.items() if k in ("kill", "prices")}
    tmp = run(d, keep, eps)
    tmp["cm"] = tmp["gross_revenue"] - tmp["commission"] - tmp["fruit"] - tmp["pack_labor"]
    g = tmp.groupby("sku")[["cm", "cups"]].sum()
    t = pd.DataFrame({"cu": g["cm"] / g["cups"], "co": d.groupby("sku")["co"].first()})
    t["cr"] = np.clip(t["cu"] / (t["cu"] + t["co"]), 0.05, 0.95)
    t["cr_used"] = np.minimum(t["cr"] + add, 0.95)
    t["z"] = norm.ppf(t["cr_used"])
    return t


def summary(res: pd.DataFrame, sheets: dict, budget_rev: float = 2_700_000, budget_gp: float = 700_000):
    """Month-level P&L with overhead, operating profit and budget gaps."""
    m = res.groupby("month")[LINES].sum()
    m["overhead"] = sheets["kitchen_overhead"]["fixed_monthly_overhead_thb"].sum()
    m["operating_profit"] = m["gross_profit"] - m["overhead"]
    m["gp_pct"] = m["gross_profit"] / m["gross_revenue"] * 100
    m["budget_revenue"], m["budget_gp"] = budget_rev, budget_gp
    m["revenue_vs_budget"] = m["gross_revenue"] - budget_rev
    m["gp_vs_budget"] = m["gross_profit"] - budget_gp
    return m
