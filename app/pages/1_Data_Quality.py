"""Data quality: what was removed, fixed and filled, and the reconcile check."""
import plotly.graph_objects as go
import streamlit as st

import common as c

c.header("Data quality", "What we removed, fixed and filled before any analysis, and proof that the totals still tie out.")

log = c.load("dq_log")
rec = c.load("reconcile").set_index("line")
names = c.load("item_mapping")

raw, clean = rec.loc["Raw orders_hourly"], rec.loc["Actual clean"]
removed_rows, removed_rev = raw["rows"] - clean["rows"], raw["revenue_thb"] - clean["revenue_thb"]
cols = st.columns(4)
cols[0].metric("Raw rows", f"{raw['rows']:,.0f}", border=True)
cols[1].metric("Clean rows", f"{clean['rows']:,.0f}", f"-{removed_rows:,.0f} ({removed_rows / raw['rows'] * 100:.1f}%)",
               delta_color="off", border=True)
cols[2].metric("Revenue removed", c.thb(removed_rev), f"{removed_rev / raw['revenue_thb'] * 100:.2f}% of raw",
               delta_color="off", border=True)
cols[3].metric("Reconcile difference", f"{rec.loc['Difference', 'revenue_thb']:,.2f} THB", border=True)

st.subheader("Does raw - removed = clean?")
st.dataframe(rec.reset_index().rename(columns={"revenue_thb": "revenue (THB)"}), hide_index=True)

st.subheader("Data quality log")
st.dataframe(log[["table", "category", "issue", "rows", "pct_rows", "revenue_thb", "cost_thb", "effect", "action"]],
             hide_index=True)

st.subheader("Which raw names became which menu item?")
by_sku = names.groupby("sku").agg(names=("item_name_raw", "size"), rows=("rows", "sum"), revenue=("revenue_thb", "sum"))
by_sku = by_sku.reindex([s for s in c.ITEMS + ["DROP"] if s in by_sku.index])
drop = by_sku.loc["DROP"] if "DROP" in by_sku.index else None
fig = go.Figure(go.Bar(x=by_sku.index, y=by_sku["names"],
                       marker_color=[c.ITEM_COLORS.get(s, c.TOTAL) for s in by_sku.index],
                       text=by_sku["names"], textposition="outside",
                       hovertemplate="%{x}<br>%{y} raw names<extra></extra>"))
fig.update_yaxes(title="Raw names", range=[0, by_sku["names"].max() * 1.3])
c.show(fig, f"{len(names)} raw names map to {len(c.ITEMS)} menu items; "
            f"{int(drop['names']) if drop is not None else 0} non-menu names ({c.thb(drop['revenue'] if drop is not None else 0)} THB) are dropped",
       "Number of raw spellings per menu item (language, typos, case, spaces)", height=380, legend=False)
sku = st.selectbox("Show the names of", ["All"] + list(by_sku.index), key="dq_sku")
shown = names if sku == "All" else names[names["sku"] == sku]
st.dataframe(shown, hide_index=True)

st.subheader("What was filled?")
filled = log[log["effect"] == "filled"]
st.dataframe(filled[["table", "issue", "rows", "cost_thb", "action"]], hide_index=True)
st.caption(f"Filled waste cost: {filled['cost_thb'].sum():,.0f} THB of 860.3k for the year. "
           "Filled rows carry is_filled=True in the data, so they can be left out in a check.")
