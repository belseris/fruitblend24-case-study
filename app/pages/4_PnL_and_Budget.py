"""P&L and budget: statement, variance, GP bridge, item and kitchen gaps, menu matrix, decisions."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

c.header("P&L and budget", "Where the money goes, why we miss the budget, and which items and kitchens make money.")
kitchen = c.pick("Kitchen (statement and menu matrix)", c.KITCHENS, "pl_kitchen")

LINES = [("Cups sold", "cups"), ("Gross revenue", "gross_revenue"), ("Commission", "commission"),
         ("Net revenue", "net_revenue"), ("Fruit cost", "fruit"), ("Packaging + labor", "pack_labor"),
         ("Contribution margin (GP-B)", "cm"), ("Waste cost", "waste_cost"), ("Gross profit (GP-C)", "gross_profit"),
         ("Kitchen overhead", "overhead"), ("Operating profit", "operating_profit")]

st.subheader(f"P&L statement: {'company' if kitchen == 'All' else kitchen}")
src = c.load("company_pnl") if kitchen == "All" else c.load("kitchen_pnl").query("kitchen == @kitchen")
st_df = src.set_index("month")[[col for _, col in LINES]].T
st_df.index = [label for label, _ in LINES]
st_df["FY"] = st_df.sum(axis=1)
pct = pd.DataFrame([st_df.loc["Gross profit (GP-C)"] / st_df.loc["Gross revenue"] * 100,
                    st_df.loc["Operating profit"] / st_df.loc["Gross revenue"] * 100],
                   index=["GP-C % of revenue", "Operating margin %"])
money = st_df.drop(index="Cups sold") / 1000
table = pd.concat([st_df.loc[["Cups sold"]], money, pct]).round(1)
st.dataframe(table, width="stretch")
st.caption("THB thousands; cups in cups; % lines in %. Overhead is fixed per kitchen and never split to items.")

st.subheader("Which months miss the budget, and why?")
v = c.load("budget_variance")
fig = go.Figure()
fig.add_bar(x=v["month"], y=v["revenue_effect"] / 1000, name="Revenue effect (revenue gap x budget margin)",
            marker_color=c.TOTAL)
fig.add_bar(x=v["month"], y=v["margin_effect"] / 1000, name="Margin effect (revenue x margin gap)", marker_color=c.DOWN)
fig.add_scatter(x=v["month"], y=v["gp_var"] / 1000, name="GP variance", mode="markers",
                marker=dict(color=c.INK, size=9, symbol="diamond"))
fig.update_layout(barmode="relative")
fig.update_yaxes(title="THB thousands")
jja = v[v["month"].isin(["2026-06", "2026-07", "2026-08"])]
c.show(fig, f"GP {v['gp_var'].sum() / 1000:,.0f}k vs budget = revenue effect {v['revenue_effect'].sum() / 1000:,.0f}k "
            f"+ margin effect {v['margin_effect'].sum() / 1000:,.0f}k; "
            f"Jun-Aug margin effect alone {jja['margin_effect'].sum() / 1000:,.0f}k",
       "GP variance vs budget by month, split into revenue and margin effects, THB thousands", height=440)
show = v[["month", "gross_revenue", "budget_revenue", "revenue_var_pct", "gross_profit", "budget_gp", "gp_var",
          "gp_var_pct", "gp_pct", "revenue_effect", "margin_effect"]]
st.dataframe(c.in_k(show, ["gross_revenue", "budget_revenue", "gross_profit", "budget_gp", "gp_var", "revenue_effect",
                           "margin_effect"]).round(1), hide_index=True)

st.subheader("From budget GP to actual GP")
b = c.load("gp_bridge")
measure = np.where(b["kind"] == "total", "total", "relative")
measure[0] = "absolute"
gaps = b.set_index("step")["thb"]
fig = go.Figure(go.Waterfall(
    x=b["step"].str.replace(" margin gap", ""), y=b["thb"] / 1000, measure=measure,
    text=(b["thb"] / 1000).round(0).astype(int), textposition="outside",
    increasing=dict(marker_color=c.UP), decreasing=dict(marker_color=c.DOWN), totals=dict(marker_color=c.TOTAL),
    connector=dict(line=dict(color="#c3c2b7", width=1)), hovertemplate="%{x}<br>%{y:,.0f}k THB<extra></extra>"))
fig.update_yaxes(title="THB thousands", range=[6800, 8900])
c.show(fig, f"Berry ({gaps['MixedBerryPremium margin gap'] / 1000:,.0f}k) and PassionFruit "
            f"({gaps['PassionFruit margin gap'] / 1000:,.0f}k) cost more GP than the revenue shortfall "
            f"({gaps['Revenue effect'] / 1000:,.0f}k)",
       "Full year, THB thousands (axis starts at 6,800). Item bar = item GP - item revenue x 25.9%", height=460,
       legend=False)

st.subheader("Which items are below the budget margin, month by month?")
ig = c.load("item_gap")
grid = ig.pivot(index="sku", columns="month", values="gap").reindex([s for s in c.ITEMS if s in ig["sku"].unique()])
lim = np.nanmax(np.abs(grid.to_numpy())) / 1000
neg = (grid < 0).sum(axis=1)
fig = go.Figure(go.Heatmap(z=grid / 1000, x=grid.columns, y=grid.index, zmid=0, zmin=-lim, zmax=lim,
                           colorscale=c.DIVERGING, xgap=2, ygap=2, text=(grid / 1000).round(0), texttemplate="%{text}",
                           colorbar=dict(title="THB k"), hovertemplate="%{y} %{x}<br>%{z:,.1f}k<extra></extra>"))
c.show(fig, f"PassionFruit is below the budget margin in {neg['PassionFruit']} of 12 months, "
            f"berry in {neg[c.BERRY]} of {grid.loc[c.BERRY].notna().sum()} months on sale",
       "Item gap = item GP - item revenue x 25.9% budget margin, THB thousands", height=360, legend=False)

st.subheader("Which kitchens make money after overhead?")
k = c.load("kitchen_pnl")
heat = k.pivot(index="kitchen", columns="month", values="operating_profit")
heat = heat.loc[heat.sum(axis=1).sort_values().index]
lim = np.abs(heat.to_numpy()).max() / 1000
below = (heat < 0).sum(axis=1)
fig = go.Figure(go.Heatmap(z=heat / 1000, x=heat.columns, y=heat.index, zmid=0, zmin=-lim, zmax=lim,
                           colorscale=c.DIVERGING, xgap=2, ygap=2, text=(heat / 1000).round(0), texttemplate="%{text}",
                           colorbar=dict(title="THB k"), hovertemplate="%{y} %{x}<br>%{z:,.0f}k<extra></extra>"))
c.show(fig, f"BKK_Ladprao loses money in {below['BKK_Ladprao']} of 12 months and BKK_Sukhumvit in "
            f"{below['BKK_Sukhumvit']}; Pattaya kitchens lose only in the rainy months",
       "Operating profit per kitchen and month (GP-C - fixed overhead), THB thousands", height=360, legend=False)
kfy = k.groupby("kitchen")[["gross_revenue", "gross_profit", "overhead", "operating_profit"]].sum()
kfy["op_margin_pct"] = kfy["operating_profit"] / kfy["gross_revenue"] * 100
kfy["months_below_0"] = below
st.dataframe(c.in_k(kfy.reset_index(), ["gross_revenue", "gross_profit", "overhead", "operating_profit"]).round(1),
             hide_index=True)

st.subheader("Menu engineering (Mar-Aug 2026)")
mm = c.load("menu_matrix").query("kitchen == @kitchen").set_index("sku").reindex(c.ITEMS)
fig = go.Figure()
for sku, r in mm.iterrows():
    fig.add_scatter(x=[r["cups_per_day"]], y=[r["gp_per_cup"]], mode="markers+text", name=sku,
                    marker=dict(size=14, color=c.ITEM_COLORS[sku], line=dict(color="#fcfcfb", width=2)),
                    text=[f"{sku} ({r['menu_class']})"], textposition="top center",
                    hovertemplate=f"{sku}<br>%{{x:.0f}} cups a day<br>%{{y:.2f}} THB GP per cup<extra></extra>")
fig.add_vline(x=mm["pop_line"].iloc[0], line=dict(color=c.TOTAL, dash="dash", width=1))
fig.add_hline(y=mm["profit_line"].iloc[0], line=dict(color=c.TOTAL, dash="dash", width=1))
fig.add_hline(y=0, line=dict(color="#c3c2b7", width=1))
fig.update_xaxes(title="Cups sold per day", range=[0, mm["cups_per_day"].max() * 1.15])
fig.update_yaxes(title="GP-C per cup after waste, THB")
stars = mm.index[mm["menu_class"] == "Star"].tolist()
c.show(fig, f"{' and '.join(stars)} are Stars; berry earns {mm.loc[c.BERRY, 'gp_per_cup']:.2f} THB a cup after waste",
       f"{kitchen}: cups per day vs GP per cup after waste. Dashed lines = averages (cut lines)", height=460,
       legend=False)

st.subheader("What do we do per item and kitchen?")
pf = c.load("portfolio_decision")
st.dataframe(c.in_k(pf[["level", "name", "problem", "cause", "action", "thb_month_low", "thb_month_high", "in_plan",
                        "confidence"]], ["thb_month_low", "thb_month_high"]), hide_index=True)
st.caption("Lesson 9 view on the Mar-Aug base. Kitchen rows are shares of the item rows, so only in_plan rows add up. "
           "The Sep-Nov values from one model are on the Forecast and Inventory page.")
