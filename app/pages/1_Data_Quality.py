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
    c.PAGES["pages/1_Data_Quality.py"][1],
    f"**{'Yes' if matches else 'Not yet'}: {c.pct(rows_out / raw['rows'] * 100)} of rows "
    f"and {c.pct(rev_out / raw['revenue_thb'] * 100)} of revenue were removed.** "
    f"We dropped {rows_out:,.0f} of {raw['rows']:,.0f} rows ({c.thb(rev_out)} of {c.thb(raw['revenue_thb'])}), "
    f"and raw minus removed {'equals' if matches else 'does not equal'} clean exactly. "
    f"{len(names)} raw item names map to {menu['sku'].nunique()} menu items.")

cols = st.columns(4)
cols[0].metric("Raw rows", f"{raw['rows']:,.0f}", border=True)
cols[1].metric("Clean rows", f"{clean['rows']:,.0f}", f"{-rows_out:,.0f} ({c.pct(rows_out / raw['rows'] * 100)})",
               delta_color="off", border=True)
cols[2].metric("Revenue removed", c.thb(rev_out), c.pct(rev_out / raw["revenue_thb"] * 100),
               delta_description="of raw revenue", delta_color="off", delta_arrow="off", border=True)
cols[3].metric("Reconcile check", "Matches" if matches else "Does not match",
               f"difference {c.thb_full(diff['revenue_thb'])}", delta_color="off", delta_arrow="off", border=True)

st.subheader("Does raw - removed = clean?")
removed_thb = rec.loc[rec.index.str.startswith(("-", "+")), "revenue_thb"].sum()
st.markdown(f"Raw {c.thb_full(raw['revenue_thb'])} {'-' if removed_thb < 0 else '+'} removed "
            f"{c.thb_full(abs(removed_thb))} = {c.thb_full(rec.loc['Expected clean', 'revenue_thb'])}. "
            f"Clean data has {c.thb_full(clean['revenue_thb'])}. **{'Matches' if matches else 'Does not match'}.**")
show = rec.reset_index().rename(columns={"line": "Step", "rows": "Rows", "revenue_thb": "Revenue"})
st.dataframe(show.style.format({"Rows": "{:,.0f}", "Revenue": c.thb_full}), hide_index=True,
             height=c.fit_height(len(show)))
c.download(rec.reset_index(), "reconcile")

st.subheader("What did we remove, fix or fill?")
st.caption("One row per check. Checks with 0 rows were run and found nothing.")
dq = log[["table", "category", "issue", "rows", "pct_rows", "revenue_thb", "cost_thb", "effect", "action"]].rename(
    columns={"pct_rows": "% of rows", "revenue_thb": "Revenue", "cost_thb": "Cost filled"})
c.table(dq, money=["Revenue", "Cost filled"], pcts=["% of rows"], count=["rows"],
        highlight=dq["rows"].gt(0) & dq["effect"].isin(["removed", "filled"]),
        column_config={"rows": st.column_config.NumberColumn(width="small"),
                       "action": st.column_config.TextColumn(width="large")})
c.download(log, "dq_log")

st.subheader(f"How do {len(names)} raw names become {menu['sku'].nunique()} menu items?")
by_sku = (names.groupby("sku").agg(raw_names=("item_name_raw", "size"), rows=("rows", "sum"), cups=("cups", "sum"),
                                   revenue=("revenue_thb", "sum"),
                                   examples=("item_name_raw", lambda s: ", ".join(s.head(3))))
          .reindex([s for s in c.ITEMS + ["DROP"] if s in set(names["sku"])]).reset_index())
st.markdown(f"Names differ by language, typos, upper/lower case and spaces. Every menu name has one full price, "
            f"and its bundle code names the same item, so the mapping is safe. {len(dropped)} names are not menu "
            f"items ({', '.join(dropped['item_name_raw'])}): {dropped['rows'].sum():,} rows, "
            f"{c.thb(dropped['revenue_thb'].sum())}, dropped.")
c.table(by_sku.rename(columns={"sku": "Menu item", "raw_names": "Raw names", "revenue": "Revenue",
                               "examples": "Examples"}),
        money=["Revenue"], count=["Raw names", "rows", "cups"], highlight=by_sku["sku"].eq("DROP"))
with st.expander(f"All {len(names)} raw names"):
    item = st.selectbox("Menu item", ["All"] + list(by_sku["sku"]), key="dq_sku")
    shown = names if item == "All" else names[names["sku"] == item]
    c.table(shown, money=["revenue_thb"], count=["rows", "cups"])
    c.download(names, "item_mapping")

st.subheader("What was filled?")
filled = log[log["effect"] == "filled"]
waste = company["waste_cost"].sum()
c.table(filled[["table", "issue", "rows", "cost_thb", "action"]].rename(columns={"cost_thb": "Cost filled"}),
        money=["Cost filled"], count=["rows"])
st.caption(f"Filled waste cost: {c.thb(filled['cost_thb'].sum())} of {c.thb(waste)} waste in the year "
           f"({c.pct(filled['cost_thb'].sum() / waste * 100)}). Filled rows carry is_filled=True in the data, "
           "so a check can leave them out.")

c.method_box(
    "- The raw Excel file is never changed. Cleaning runs in `src/load_clean.py` and notebook 01.\n"
    "- **Remove** only what is not a real sale: exact copies of a row (same export twice) and non-menu names "
    "(test menu, empty cup, combo) with random prices and no cost data.\n"
    "- **Fix** real sales that were recorded badly: raw names go to one of the menu items with a mapping file "
    "that was checked by hand.\n"
    "- **Flag, do not drop** rows we are not sure about (unknown rate codes, bundle codes that name another item).\n"
    "- **Fill** missing cost and waste rows with the same kitchen and item's mean, so waste is not shown as 0.\n"
    "- Every step goes into the data quality log with rows and THB, and an assert checks raw - removed = clean.")
