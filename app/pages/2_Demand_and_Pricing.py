"""Demand and pricing: when customers buy, what one cup earns, and price decisions."""
import plotly.graph_objects as go
import streamlit as st

import common as c

c.header("Demand and pricing", "When and where customers buy, what one cup earns, and how far we can move prices.")
kitchen = c.pick("Kitchen (demand charts)", c.KITCHENS, "dp_kitchen")
platform = st.sidebar.selectbox("Platform (unit economics)", ["All", "LINE MAN", "Grab"], key="dp_platform")

st.subheader("When do customers buy?")
hm = c.load("demand_heatmap")
hm = hm[hm["kitchen"] == kitchen]
days = hm.sort_values("day_of_week")["day_name"].unique().tolist()
grid = hm.pivot(index="day_name", columns="hour", values="avg_cups_per_hour").reindex(days)
peak = hm.loc[hm["avg_cups_per_hour"].idxmax()]
fig = go.Figure(go.Heatmap(z=grid.to_numpy(), x=grid.columns, y=grid.index, colorscale=c.SEQUENTIAL, xgap=1, ygap=1,
                           colorbar=dict(title="cups/h"),
                           hovertemplate="%{y} %{x}:00<br>%{z:.0f} cups an hour<extra></extra>"))
fig.update_xaxes(title="Hour", dtick=2)
fig.update_yaxes(autorange="reversed")
c.show(fig, f"{'All kitchens' if kitchen == 'All' else kitchen}: busiest hour is {peak['day_name']} {int(peak['hour'])}:00 with {peak['avg_cups_per_hour']:.0f} cups an hour",
       "Average cups sold per hour, by weekday and hour, Sep 2025 to Aug 2026", height=380, legend=False)

left, right = st.columns(2)
with left:
    dp = c.load("daypart_share")
    dp = dp[dp["kitchen"] == kitchen].sort_values("share_pct", ascending=False)
    top = dp.iloc[0]
    fig = go.Figure(go.Bar(x=dp["daypart"], y=dp["share_pct"], marker_color=c.UP,
                           text=dp["share_pct"].round(0).astype(int).astype(str) + "%", textposition="outside",
                           customdata=dp["cups_per_hour"],
                           hovertemplate="%{x}<br>%{y:.1f}% of cups<br>%{customdata:.0f} cups an hour<extra></extra>"))
    fig.update_yaxes(title="% of cups", range=[0, dp["share_pct"].max() * 1.3])
    c.show(fig, f"{top['daypart']} is the biggest daypart ({top['share_pct']:.0f}% of cups)",
           f"{kitchen}: share of cups by daypart", height=380, legend=False)
with right:
    mix = c.load("sales_mix").set_index("sku").reindex(c.ITEMS)
    fig = go.Figure()
    fig.add_bar(x=mix.index, y=mix["share_cups_pct"], name="% of cups", marker_color=c.UP)
    fig.add_bar(x=mix.index, y=mix["share_revenue_pct"], name="% of revenue", marker_color=c.TOTAL)
    fig.update_yaxes(title="%")
    c.show(fig, f"Watermelon sells {mix.loc['Watermelon', 'share_cups_pct']:.0f}% of cups; "
                f"berry {mix.loc[c.BERRY, 'share_cups_pct']:.0f}% of cups but {mix.loc[c.BERRY, 'share_revenue_pct']:.0f}% of revenue",
           "Sales mix, Mar-Aug 2026 (all 5 items on sale), all kitchens", height=380)

st.subheader("What does one cup earn?")
ue = c.load("unit_economics")
ue = ue[ue["level"] == "item"] if platform == "All" else ue[(ue["level"] == "item_platform") & (ue["platform"] == platform)]
ue = ue.set_index("sku").reindex(c.ITEMS)
has_waste = ue["cm_after_waste_per_cup"].notna().all()
y = ue["cm_after_waste_per_cup"] if has_waste else ue["cm_per_cup"]
fig = go.Figure(go.Bar(x=ue.index, y=y, marker_color=[c.UP if v >= 0 else c.DOWN for v in y],
                       text=y.round(2), textposition="outside", hovertemplate="%{x}<br>%{y:.2f} THB a cup<extra></extra>"))
fig.update_yaxes(title="THB a cup")
worst = y.idxmin()
what = "after waste" if has_waste else "before waste (waste has no platform split)"
c.show(fig, f"{worst} earns the least: {y.min():.2f} THB a cup {what}",
       f"CM per cup, Mar-Aug 2026, platform: {platform}", height=380, legend=False)
cols = ["cups", "list_price", "avg_sell_price", "commission_per_cup", "fruit_per_cup", "pack_labor_per_cup", "cm_per_cup"]
if has_waste:
    cols += ["waste_per_cup", "cm_after_waste_per_cup", "waste_rate_pct"]
st.dataframe(ue[cols].round(2), width="stretch")

st.subheader("How much do customers react to price?")
el = c.load("elasticity")
main = el[el["estimate"].str.startswith("1")].set_index("sku").reindex(c.ITEMS)
pr = c.load("price_recommendation")
be = pr.set_index("sku")["breakeven_elasticity"].reindex(c.ITEMS)
fig = go.Figure()
fig.add_scatter(x=main["elasticity"], y=main.index, mode="markers", name="Measured (RC101 vs normal price)",
                marker=dict(color=c.UP, size=11),
                error_x=dict(type="data", symmetric=False, array=main["ci_high_by_day"] - main["elasticity"],
                             arrayminus=main["elasticity"] - main["ci_low_by_day"], color=c.UP),
                hovertemplate="%{y}<br>%{x:.2f}<extra></extra>")
fig.add_scatter(x=be, y=be.index, mode="markers", name="Break-even for the next price step",
                marker=dict(color=c.DOWN, size=11, symbol="x"), hovertemplate="%{y}<br>break-even %{x:.2f}<extra></extra>")
fig.update_xaxes(title="Elasticity (% change in cups for +1% price)")
fig.update_yaxes(autorange="reversed")
room = [s for s in c.ITEMS if main.loc[s, "ci_low_by_day"] > be[s]]
cross = [s for s in c.ITEMS if s not in room]
c.show(fig, f"{len(room)} of 5 items have their whole CI above the break-even; "
            f"{', '.join(cross) if cross else 'none'} cross{'es' if len(cross) == 1 else ''} it",
       "Main elasticity with day-clustered 95% CI; a price rise pays if demand is less sensitive than the break-even",
       height=400)

st.subheader("Price decisions (lesson 6)")
show = pr[["sku", "price_now", "decision", "new_price", "test_price", "cm_change_low", "cm_change_high",
           "confidence", "main_risk"]]
st.dataframe(c.in_k(show, ["cm_change_low", "cm_change_high"]), hide_index=True)
st.caption("CM change is a month, before waste, on the Mar-Aug base. The Sep-Nov value of each action is on the "
           "Forecast and Inventory page.")
