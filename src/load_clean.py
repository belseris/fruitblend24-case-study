"""Load the raw FruitBlend24 workbook and build clean tables."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "FruitBlend24_Intern_Case_Data.xlsx"
MAPPING_FILE = ROOT / "data" / "processed" / "item_mapping.csv"
CLEAN_FILE = ROOT / "data" / "processed" / "orders_clean.parquet"

SKUS = ["Watermelon", "Pineapple", "Guava", "PassionFruit", "MixedBerryPremium"]
BERRY = "MixedBerryPremium"
BERRY_LAUNCH = pd.Timestamp("2026-03-01")
# After mapping, one row should exist per key. Same-key rows are kept and summed later.
KEY = ["date", "hour", "kitchen", "sku", "rate_code"]

LOG_COLUMNS = ["table", "category", "issue", "rows", "pct_rows",
               "revenue_thb", "revenue_change_thb", "cost_thb", "effect", "action"]


def week_monday(dates: pd.Series) -> pd.Series:
    """Monday of the week, to join with weekly_fruit_cost."""
    return dates - pd.to_timedelta(dates.dt.dayofweek, unit="D")


def load_raw(path: Path = RAW_FILE) -> dict[str, pd.DataFrame]:
    """Read every sheet of the raw workbook. The file is never changed."""
    return pd.read_excel(path, sheet_name=None)


def load_mapping(path: Path = MAPPING_FILE) -> pd.DataFrame:
    """Read item_mapping.csv with stripped names."""
    m = pd.read_csv(path, encoding="utf-8")
    # Strip so that "Pineapple smoothie " (trailing space) still matches.
    m["item_name_raw"] = m["item_name_raw"].str.strip()
    m["sku"] = m["sku"].str.strip()
    bad = set(m["sku"]) - set(SKUS) - {"DROP"}
    assert not bad, f"Mapping has values that are not a SKU or DROP: {bad}"
    assert not m["item_name_raw"].duplicated().any(), "A raw name is mapped twice"
    return m[["item_name_raw", "sku"]]


def _log_row(table, category, issue, rows, n_total, revenue=0.0, revenue_change=0.0,
             cost=0.0, effect="fixed", action=""):
    return {"table": table, "category": category, "issue": issue, "rows": int(rows),
            "pct_rows": round(rows / n_total * 100, 3), "revenue_thb": round(float(revenue), 2),
            "revenue_change_thb": round(float(revenue_change), 2), "cost_thb": round(float(cost), 2),
            "effect": effect, "action": action}


def _split_cost_assumptions(ca: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The sheet holds two tables: cost per cup per SKU, then overhead per kitchen."""
    first_col = ca.columns[0]
    unit_cost = ca[ca[first_col].isin(SKUS)].copy()
    for col in ["packaging_cost_per_cup_thb", "labor_cost_per_cup_thb", "base_price_thb"]:
        unit_cost[col] = unit_cost[col].astype(float)
    unit_cost["pack_labor_per_cup_thb"] = (unit_cost["packaging_cost_per_cup_thb"]
                                           + unit_cost["labor_cost_per_cup_thb"])

    # The second table starts after a header row whose first cell is "kitchen".
    header_row = ca.index[ca[first_col] == "kitchen"][0]
    overhead = ca.loc[header_row + 1:].dropna(how="all").copy()
    overhead.columns = ca.loc[header_row].tolist()
    overhead = overhead.loc[:, overhead.columns.notna()]
    overhead["fixed_monthly_overhead_thb"] = overhead["fixed_monthly_overhead_thb"].astype(float)

    assert sorted(unit_cost["sku"]) == sorted(SKUS), "unit_cost does not have the 5 SKUs"
    return unit_cost.reset_index(drop=True), overhead.reset_index(drop=True)


def load_tables(raw: dict | None = None, return_log: bool = False):
    """Clean reference tables. Same sheet names, plus unit_cost and kitchen_overhead."""
    raw = load_raw() if raw is None else raw
    t = {name: raw[name].copy() for name in
         ["rate_code_dim", "platform_dim", "sku_code_dim", "platform_commission_rate"]}
    log = []

    t["unit_cost"], t["kitchen_overhead"] = _split_cost_assumptions(raw["cost_assumptions"])

    budget = raw["monthly_budget"].copy()
    budget["month"] = pd.to_datetime(budget["month"])
    t["monthly_budget"] = budget

    # Fruit cost: berry launch day (Sunday) falls in week 2026-02-23, which has no berry cost.
    fc = raw["weekly_fruit_cost"].copy()
    fc["week_start"] = pd.to_datetime(fc["week_start"])
    assert (fc["week_start"].dt.dayofweek == 0).all(), "week_start is not always a Monday"
    fc["is_filled"] = False
    launch_week = BERRY_LAUNCH - pd.Timedelta(days=BERRY_LAUNCH.dayofweek)
    first_week = fc.loc[fc["sku"] == BERRY, "week_start"].min()
    has_launch_week = ((fc["sku"] == BERRY) & (fc["week_start"] == launch_week)).any()
    if not has_launch_week:
        copy_row = fc[(fc["sku"] == BERRY) & (fc["week_start"] == first_week)].assign(
            week_start=launch_week, is_filled=True)
        fc = pd.concat([fc, copy_row]).sort_values(["week_start", "sku"]).reset_index(drop=True)
        cost = copy_row["fruit_cost_per_cup_thb"].iloc[0]
        log.append(_log_row(
            "weekly_fruit_cost", "missing", f"No berry fruit cost for launch week {launch_week.date()}",
            1, len(fc), effect="filled",
            action=f"Copy week {first_week.date()} ({cost:.2f} THB per cup)"))
    t["weekly_fruit_cost"] = fc

    w = raw["waste_daily"].copy()
    w["date"] = pd.to_datetime(w["date"])
    w["is_filled"] = False
    n_waste_raw = len(w)

    # Blank waste cost: berry launch day. Use the weighted cost per wasted cup of the first cost week.
    blank = w["est_waste_cost_thb"].isna()
    assert ((w.loc[blank, "sku"] == BERRY) & (w.loc[blank, "date"] == BERRY_LAUNCH)).all(), \
        "Blank waste cost outside berry launch day"
    week1 = w[(w["sku"] == BERRY) & w["date"].between(first_week, first_week + pd.Timedelta(days=6))]
    cost_per_cup = week1["est_waste_cost_thb"].sum() / week1["units_wasted"].sum()
    w.loc[blank, "est_waste_cost_thb"] = w.loc[blank, "units_wasted"] * cost_per_cup
    w.loc[blank, "is_filled"] = True
    log.append(_log_row(
        "waste_daily", "missing", "Blank waste cost on berry launch day",
        blank.sum(), n_waste_raw, cost=w.loc[blank, "est_waste_cost_thb"].sum(), effect="filled",
        action=f"Units x {cost_per_cup:.2f} THB per wasted cup (week {first_week.date()})"))

    # Missing kitchen-days: every kitchen x SKU x day from the SKU's first day.
    days = pd.date_range(w["date"].min(), w["date"].max(), freq="D")
    grid = pd.MultiIndex.from_product([days, w["kitchen"].unique(), SKUS],
                                      names=["date", "kitchen", "sku"]).to_frame(index=False)
    grid = grid[~((grid["sku"] == BERRY) & (grid["date"] < BERRY_LAUNCH))]
    check = grid.merge(w[["date", "kitchen", "sku"]], how="left", indicator=True, validate="one_to_one")
    missing = check.loc[check["_merge"] == "left_only", ["date", "kitchen", "sku"]]
    means = (w[~w["is_filled"]].groupby(["kitchen", "sku"])[["units_wasted", "est_waste_cost_thb"]]
             .mean().reset_index())
    fill = missing.merge(means, on=["kitchen", "sku"], how="left", validate="many_to_one")
    fill["is_filled"] = True
    w = pd.concat([w, fill]).sort_values(["date", "kitchen", "sku"]).reset_index(drop=True)
    log.append(_log_row(
        "waste_daily", "missing", "Missing kitchen-day rows",
        len(fill), n_waste_raw, cost=fill["est_waste_cost_thb"].sum(), effect="filled",
        action="Add row with kitchen x SKU mean units and cost, is_filled=True"))
    assert len(w) == len(grid), "waste_daily still does not cover every kitchen-day"
    t["waste_daily"] = w

    log = pd.DataFrame(log, columns=LOG_COLUMNS)
    return (t, log) if return_log else t


def clean_orders(raw: dict | None = None, mapping: pd.DataFrame | None = None):
    """Clean orders_hourly step by step. Returns (clean orders, DQ log)."""
    raw = load_raw() if raw is None else raw
    mapping = load_mapping() if mapping is None else mapping
    o = raw["orders_hourly"].copy()
    n_raw = len(o)
    log = []

    def add(category, issue, mask, effect, action, revenue_change=0.0):
        log.append(_log_row("orders_hourly", category, issue, mask.sum(), n_raw,
                            revenue=o.loc[mask, "gross_revenue_thb"].sum(),
                            revenue_change=revenue_change, effect=effect, action=action))

    # 1. Exact duplicates: same export twice.
    mask = o.duplicated(keep="first")
    add("duplicate", "Exact duplicate rows (extra copies)", mask, "removed", "Drop, keep first row")
    o = o[~mask]

    # 2. Map raw names to the 5 SKUs.
    o["item_name_raw"] = o["item_name_raw"].str.strip()
    o = o.merge(mapping, on="item_name_raw", how="left", validate="many_to_one", indicator=True)
    unmapped = o.loc[o["_merge"] == "left_only", "item_name_raw"].unique()
    assert len(unmapped) == 0, f"Names missing from item_mapping.csv: {list(unmapped)}"
    o = o.drop(columns="_merge")
    renamed = o["item_name_raw"] != o["sku"]
    add("naming", f"{o['item_name_raw'].nunique()} raw names (language, typos, case, spaces)",
        renamed, "fixed", "Map with item_mapping.csv to 5 SKUs or DROP")

    # 3. Not menu items.
    mask = o["sku"] == "DROP"
    add("not a sale", "Non-menu names (test menu, empty cup, combo)", mask, "removed", "Drop")
    o = o[~mask]

    # 4. A real sale has at least 1 cup and a price above 0.
    mask = (o["units_sold"] <= 0) | (o["price_thb"] <= 0)
    add("invalid value", "units_sold <= 0 or price_thb <= 0", mask, "removed", "Drop")
    o = o[~mask]

    # 5. Revenue must be units x price.
    new_rev = o["units_sold"] * o["price_thb"]
    mask = ~np.isclose(o["gross_revenue_thb"], new_rev, atol=0.01)
    add("invalid value", "gross_revenue_thb != units x price", mask, "fixed",
        "Recalculate as units x price", revenue_change=(new_rev - o["gross_revenue_thb"]).sum())
    o["gross_revenue_thb"] = new_rev

    # 6. Split PLATFORM-BASECODE[-SKUCODE].
    parts = o["rate_code"].str.split("-", n=2, expand=True).reindex(columns=[0, 1, 2])
    o["platform_code"], o["base_code"], o["sku_code"] = parts[0], parts[1], parts[2]
    is_rc101 = o["base_code"] == "RC101"
    o["flag_unknown_code"] = (
        ~o["platform_code"].isin(raw["platform_dim"]["platform_code"])
        | ~o["base_code"].isin(raw["rate_code_dim"]["base_code"])
        | (is_rc101 & ~o["sku_code"].isin(raw["sku_code_dim"]["sku_code"]))
        | (~is_rc101 & o["sku_code"].notna())
    )
    add("code", "rate_code not in the dim tables", o["flag_unknown_code"], "flagged", "Keep, flag_unknown_code")

    # 7. The bundle code names one SKU. It should be the SKU of the row.
    code_sku = o["sku_code"].map(raw["sku_code_dim"].set_index("sku_code")["sku"])
    o["flag_rc101_mismatch"] = is_rc101 & (code_sku != o["sku"])
    add("code", "RC101 SKU part does not match the item", o["flag_rc101_mismatch"],
        "flagged", "Keep, flag_rc101_mismatch")

    # 8. Berry sales before launch cannot be real.
    mask = (o["sku"] == BERRY) & (o["date"] < BERRY_LAUNCH)
    add("not a sale", f"Berry rows before launch {BERRY_LAUNCH.date()}", mask, "removed", "Drop")
    o = o[~mask]

    # 9. Different raw names of one SKU in the same hour are real sales. Keep them.
    mask = o.duplicated(KEY, keep=False)
    add("same key", "Rows sharing date-hour-kitchen-sku-rate_code", mask, "info",
        "Keep, sum by key in the enrich step")

    cols = ["date", "hour", "day_of_week", "kitchen", "item_name_raw", "sku", "rate_code",
            "platform_code", "base_code", "sku_code", "price_thb", "units_sold",
            "gross_revenue_thb", "flag_unknown_code", "flag_rc101_mismatch"]
    o = o[cols].reset_index(drop=True)
    return o, pd.DataFrame(log, columns=LOG_COLUMNS)


def reconcile(raw_orders: pd.DataFrame, clean: pd.DataFrame, log: pd.DataFrame) -> pd.DataFrame:
    """Raw - removed (+ fixes) = clean, for rows and revenue."""
    o_log = log[log["table"] == "orders_hourly"]
    removed = o_log[o_log["effect"] == "removed"]
    lines = [{"line": "Raw orders_hourly", "rows": len(raw_orders),
              "revenue_thb": raw_orders["gross_revenue_thb"].sum()}]
    for _, r in removed.iterrows():
        lines.append({"line": f"- {r['issue']}", "rows": -r["rows"], "revenue_thb": 0.0 - r["revenue_thb"]})
    # Recalculated revenue changes THB but not rows.
    lines.append({"line": "+ Revenue recalculated as units x price", "rows": 0,
                  "revenue_thb": o_log["revenue_change_thb"].sum()})
    lines.append({"line": "Expected clean", "rows": sum(x["rows"] for x in lines),
                  "revenue_thb": sum(x["revenue_thb"] for x in lines)})
    lines.append({"line": "Actual clean", "rows": len(clean),
                  "revenue_thb": clean["gross_revenue_thb"].sum()})
    table = pd.DataFrame(lines).set_index("line")
    table.loc["Difference"] = table.loc["Actual clean"] - table.loc["Expected clean"]
    table["rows"] = table["rows"].astype(int)
    table["revenue_thb"] = table["revenue_thb"].round(2)
    return table


def load_clean(path: Path = CLEAN_FILE) -> pd.DataFrame:
    """Read the saved clean orders."""
    return pd.read_parquet(path)
