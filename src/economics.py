"""Unit economics: join prices and costs to each order row, then CM per cup."""
import numpy as np
import pandas as pd

from src.load_clean import BERRY, BERRY_LAUNCH, KEY, week_monday

# Money columns per row. All are THB for the whole row (price x cups), not per cup.
MONEY = ["list_revenue_thb", "discount_thb", "gross_revenue_thb", "commission_thb", "net_revenue_thb",
         "fruit_cost_thb", "pack_labor_thb", "cm_thb"]
JOINED = ["commission_rate", "discount_pct", "fruit_cost_per_cup_thb", "pack_labor_per_cup_thb", "base_price_thb"]


def enrich(df: pd.DataFrame, sheets: dict) -> pd.DataFrame:
    """Add list price, discount, commission, fruit and pack/labor cost and CM to each order row."""
    n_rows = len(df)
    # Same-key rows must be summed before this step (decision log, lesson 4). Today there are none.
    assert not df.duplicated(KEY).any(), "same-key rows found: sum them before enrich()"
    e = df.copy()
    e["week_start"] = week_monday(e["date"])
    e = e.merge(sheets["platform_commission_rate"][["platform_code", "commission_rate"]],
                on="platform_code", how="left", validate="many_to_one")
    e = e.merge(sheets["rate_code_dim"][["base_code", "discount_pct"]],
                on="base_code", how="left", validate="many_to_one")
    e = e.merge(sheets["weekly_fruit_cost"][["week_start", "sku", "fruit_cost_per_cup_thb"]],
                on=["week_start", "sku"], how="left", validate="many_to_one")
    e = e.merge(sheets["unit_cost"][["sku", "pack_labor_per_cup_thb", "base_price_thb"]],
                on="sku", how="left", validate="many_to_one")

    assert len(e) == n_rows, "a join added or lost rows"
    missing = e[JOINED].isna().sum()
    assert not missing.any(), f"rows without a price or cost: {missing[missing > 0].to_dict()}"

    # Berry launch day (Sunday) sits in week 2026-02-23, which holds a copy of the 2026-03-02 cost.
    fc = sheets["weekly_fruit_cost"].set_index(["week_start", "sku"])["fruit_cost_per_cup_thb"]
    launch_cost = e.loc[(e["sku"] == BERRY) & (e["date"] == BERRY_LAUNCH), "fruit_cost_per_cup_thb"]
    assert len(launch_cost) > 0, "no berry rows on launch day"
    assert (launch_cost == fc[(BERRY_LAUNCH + pd.Timedelta(days=1), BERRY)]).all()

    # List price = base_price_thb. The price on the code must give the same number.
    e["list_price_thb"] = e["base_price_thb"]
    implied = e["price_thb"] / (1 - e["discount_pct"])
    assert np.isclose(implied, e["list_price_thb"], atol=0.01).all(), "price / (1 - discount) != base_price_thb"

    cups = e["units_sold"]
    e["list_revenue_thb"] = e["list_price_thb"] * cups
    e["discount_thb"] = e["list_revenue_thb"] - e["gross_revenue_thb"]
    # Commission is a share of what the customer paid (after discount).
    e["commission_thb"] = e["gross_revenue_thb"] * e["commission_rate"]
    e["net_revenue_thb"] = e["gross_revenue_thb"] - e["commission_thb"]
    e["fruit_cost_thb"] = e["fruit_cost_per_cup_thb"] * cups
    e["pack_labor_thb"] = e["pack_labor_per_cup_thb"] * cups
    e["cm_thb"] = e["net_revenue_thb"] - e["fruit_cost_thb"] - e["pack_labor_thb"]
    return e


def unit_economics(e: pd.DataFrame, by) -> pd.DataFrame:
    """Per-cup economics by group: sum money first, then divide by cups (weighted)."""
    g = e.groupby(by)[["units_sold"] + MONEY].sum()
    cups = g["units_sold"]
    out = pd.DataFrame({
        "cups": cups,
        "list_price": g["list_revenue_thb"] / cups,
        "discount_per_cup": g["discount_thb"] / cups,
        "avg_sell_price": g["gross_revenue_thb"] / cups,
        "commission_per_cup": g["commission_thb"] / cups,
        "fruit_per_cup": g["fruit_cost_thb"] / cups,
        "pack_labor_per_cup": g["pack_labor_thb"] / cups,
        "cm_per_cup": g["cm_thb"] / cups,
        # CM % of what the customer paid (after discount, before commission).
        "cm_pct": g["cm_thb"] / g["gross_revenue_thb"] * 100,
        "gross_revenue_thb": g["gross_revenue_thb"],
        "total_cm_thb": g["cm_thb"],
    })
    return out
