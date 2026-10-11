"""Data quality: what was removed, fixed and filled, and the reconcile check."""
import streamlit as st

import common as c

rec = c.load("reconcile").set_index("line")
log = c.load("dq_log")
names = c.load("item_mapping")
company = c.load("company_pnl")

raw, clean, diff = rec.loc["Raw orders_hourly"], rec.loc["Actual clean"], rec.loc["Difference"]
rows_out, rev_out = raw["rows"] - clean["rows"], raw["revenue_thb"] - clean["revenue_thb"]
matches = diff["rows"] == 0 and abs(diff["revenue_thb"]) < 0.005
menu = names[names["sku"] != "DROP"]
dropped = names[names["sku"] == "DROP"]

c.page_header(
    c.DQ,
    f"**{'Yes' if matches else 'Not yet'}: {rows_out:,.0f} of {raw['rows']:,.0f} rows "
    f"({c.pct(rows_out / raw['rows'] * 100)}) were removed, worth {c.thb(rev_out)}.** Raw minus removed "
    f"{'equals' if matches else 'does not equal'} clean exactly, and {len(names)} raw names map to "
    f"{menu['sku'].nunique()} menu items.")

c.kpi_row([
    dict(label="Raw rows", value=f"{raw['rows']:,.0f}", help="Rows in the orders_hourly sheet of the raw Excel file."),
    dict(label="Clean rows", value=f"{clean['rows']:,.0f}",
         delta=f"{-rows_out:,.0f} ({c.pct(rows_out / raw['rows'] * 100)})", delta_color="off",
         help="Rows left after removing exact copies and names that are not menu items."),
    dict(label="Revenue removed", value=c.thb(rev_out), delta=f"{c.pct(rev_out / raw['revenue_thb'] * 100)} of raw",
         delta_color="off", delta_arrow="off", help="Revenue of the removed rows: not real sales."),
    dict(label="Reconcile check", value="Matches" if matches else "Does not match",
         delta=f"difference {c.thb_full(diff['revenue_thb'])}", delta_color="off", delta_arrow="off",
         help="Raw revenue minus removed revenue must equal clean revenue."),
])

left, right = st.columns([2, 3])
with left:
    removed_thb = rec.loc[rec.index.str.startswith(("-", "+")), "revenue_thb"].sum()
    with c.card(f"Raw minus removed {'equals' if matches else 'does not equal'} clean exactly",
                so_what="every baht on the later pages traces back to the raw file.",
                how_to_read="Start at the raw file. Each '-' line is a group of rows we removed; a '+' line is a "
                            "fix that changes revenue. 'Expected clean' = raw plus these lines. 'Actual clean' is "
                            "what the clean data really holds. 'Difference' must be 0."):
        steps = rec.reset_index()
        c.table(steps, count=["rows"], exact=["revenue_thb"], highlight=steps["line"].isin(["Actual clean", "Difference"]))
        st.caption(f"Raw {c.thb_full(raw['revenue_thb'])} {'-' if removed_thb < 0 else '+'} "
                   f"{c.thb_full(abs(removed_thb))} = {c.thb_full(rec.loc['Expected clean', 'revenue_thb'])}; "
                   f"clean data holds {c.thb_full(clean['revenue_thb'])}.")
        c.download(rec.reset_index(), "reconcile")

with right:
    by_sku = (names.groupby("sku").agg(raw_names=("item_name_raw", "size"), rows=("rows", "sum"),
                                       revenue=("revenue_thb", "sum"),
                                       examples=("item_name_raw", lambda s: ", ".join(s.head(3))))
              .reindex([s for s in c.ITEMS + ["DROP"] if s in set(names["sku"])]).reset_index())
    with c.card(f"{len(names)} raw names map to {menu['sku'].nunique()} menu items; {len(dropped)} names are not "
                "menu items",
                so_what=f"the {len(dropped)} non-menu names ({c.join(dropped['item_name_raw'])}) are "
                        f"{dropped['rows'].sum():,} rows and {c.thb(dropped['revenue_thb'].sum())}; they are dropped, "
                        "the rest keep every sale.",
                method="Names differ by language, typos, upper/lower case and spaces. The mapping was proposed by "
                       "code and then checked by hand (no name left for review). Every menu name has one full "
                       "price, and its bundle code names the same item, so the mapping is safe."):
        c.table(by_sku.rename(columns={"sku": "Menu item"}), money=["revenue"], count=["raw_names", "rows"],
                highlight=by_sku["sku"].eq("DROP"))
        with st.expander(f"All {len(names)} raw names"):
            item = c.choose("Menu item", list(by_sku["sku"]), key="dq_sku")
            shown = names if item == "All" else names[names["sku"] == item]
            c.table(shown, money=["revenue_thb"], count=["rows", "cups"])
            c.download(names, "item_mapping")

changed = log[log["rows"].gt(0) & log["effect"].isin(["removed", "filled"])]
with c.card(f"{len(log)} checks run; {len(changed)} changed the data ({log.loc[log['effect'] == 'removed', 'rows'].sum():,} "
            f"rows removed, {log.loc[log['effect'] == 'filled', 'rows'].sum():,} rows filled)",
            so_what="the cleaning touched under 1% of rows. Checks with 0 rows ran and found nothing, so the "
                    "codes, prices and dates are usable as they are.",
            method="- The raw Excel file is never changed. Cleaning runs in `src/load_clean.py` and notebook 01.\n"
                   "- **Remove** only what is not a real sale: exact copies of a row (same export twice) and "
                   "non-menu names (test menu, empty cup, combo) with random prices and no cost data.\n"
                   "- **Fix** real sales that were recorded badly: raw names go to one of the menu items.\n"
                   "- **Flag, do not drop** rows we are not sure about (unknown promo codes, bundle codes that name "
                   "another item).\n"
                   "- **Fill** missing cost and waste rows with the same kitchen and item's mean, so waste is not "
                   "shown as 0.\n"
                   "- Every step goes into this log with rows and ฿, and an assert checks raw - removed = clean."):
    dq = log.rename(columns={"revenue_thb": "Revenue (raw)"}).assign(effect=lambda d: d["effect"].map(c.title_case))
    c.table(dq, cols=["issue", "rows", "pct_rows", "Revenue (raw)", "effect", "action"], name="dq_log", raw=log,
            money=["Revenue (raw)", "cost_thb", "revenue_change_thb"], pcts=["pct_rows"], count=["rows"],
            highlight=log["rows"].gt(0) & log["effect"].isin(["removed", "filled"]), static=True)
    with st.expander("What was filled?"):
        filled = log[log["effect"] == "filled"]
        waste = company["waste_cost"].sum()
        c.table(filled[["table", "issue", "rows", "cost_thb", "action"]], money=["cost_thb"], count=["rows"])
        st.caption(f"Filled waste cost: {c.thb(filled['cost_thb'].sum())} of {c.thb(waste)} waste in the year "
                   f"({c.pct(filled['cost_thb'].sum() / waste * 100)}). Filled rows carry a filled flag in the data, "
                   "so a check can leave them out.")

c.next_page(c.DEMAND)
