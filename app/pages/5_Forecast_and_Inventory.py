"""Forecast and inventory: backtest, Sep-Nov forecast, prep plan, prep rule, scenarios and profit plan."""
import plotly.graph_objects as go
import streamlit as st

import common as c

c.header("Forecast and inventory", "What Sep-Nov 2026 will sell, how much to prep, and what the plan does to profit.")
kitchen = c.pick("Kitchen", c.KITCHENS, "fi_kitchen")
item = c.pick("Item", c.ITEMS, "fi_item")


def keep(df):
    """Apply the sidebar kitchen and item filters."""
    if kitchen != "All":
        df = df[df["kitchen"] == kitchen]
    if item != "All":
        df = df[df["sku"] == item]
    return df


st.subheader("Which forecast method wins?")
fb = c.load("forecast_backtest")
main = fb[fb["test"].str.startswith("Jun-Aug") & (fb["sku"] == "All")].set_index("method")
winner = main.index[main["winner"]][0]
fig = go.Figure()
fig.add_bar(x=main.index, y=main["wape_pct"], name="WAPE %", marker_color=c.TOTAL)
fig.add_bar(x=main.index, y=main["bias_pct"], name="Bias %", marker_color=c.DOWN)
fig.update_yaxes(title="% of actual cups")
c.show(fig, f"{winner} wins (WAPE {main.loc[winner, 'wape_pct']:.1f}%), but every method is "
            f"{main['bias_pct'].min():.0f}-{main['bias_pct'].max():.0f}% too high: none sees the rainy-season drop",
       "Backtest: train up to 31 May 2026, test Jun-Aug 2026, daily kitchen x item forecasts", height=380)
same = fb[~fb["test"].str.startswith("Jun-Aug")].pivot(index="method", columns="test", values="wape_pct").round(1)
st.caption("Same-season checks (one month ahead), WAPE %: the methods score about the same when the season does not change.")
st.dataframe(same, width="stretch")

st.subheader("What will Sep-Nov sell?")
hist = keep(c.load("item_kitchen_pnl")).groupby("month")["cups"].sum()
fm = keep(c.load("forecast_monthly"))
fut = fm.groupby("month")["forecast"].sum()
ly = fm.groupby("month")["cups_2025"].sum(min_count=1)
fig = go.Figure()
fig.add_scatter(x=hist.index, y=hist, name="Actual", mode="lines+markers", line=dict(color=c.INK, width=2))
fig.add_scatter(x=[hist.index[-1]] + list(fut.index), y=[hist.iloc[-1]] + list(fut), name="Forecast",
                mode="lines+markers", line=dict(color=c.UP, width=2, dash="dash"))
fig.update_yaxes(title="Cups a month")
old = fm[fm["sku"] != c.BERRY]
gap = (old["forecast"].sum() / old["cups_2025"].sum() - 1) * 100 if old["cups_2025"].sum() > 0 else float("nan")
title = (f"Sep-Nov forecast {fut.sum():,.0f} cups; old items {gap:+.1f}% vs Sep-Nov 2025" if old.size
         else f"Sep-Nov forecast {fut.sum():,.0f} cups; berry is held flat at its August level")
c.show(fig, title, f"Kitchen: {kitchen}, item: {item}. Sep = {winner}, Oct-Nov = Sep x 2025 month ratio, berry flat",
       height=400)

st.subheader("How much to prep and buy?")
inv = c.load("inventory_plan")
mon = keep(inv[inv["level"] == "month"])
tot = mon.groupby("month")[["demand", "prep_cups", "waste_cups", "short_cups", "fruit_budget_thb",
                            "fruit_budget_downside_thb"]].sum()
cols = st.columns(3)
for col, (month, r) in zip(cols, tot.iterrows()):
    col.metric(f"Prep {month}", f"{r['prep_cups']:,.0f} cups",
               f"fruit {c.thb(r['fruit_budget_thb'])} THB ({c.thb(r['fruit_budget_downside_thb'])} at +15%)",
               delta_color="off", border=True)
st.dataframe(c.in_k(mon[["month", "kitchen", "sku", "rule", "demand", "prep_cups", "waste_cups", "short_cups",
                         "waste_rate_pct", "fruit_budget_thb"]].round(0), ["fruit_budget_thb"]), hide_index=True)
wk = keep(inv[inv["level"].str.startswith("weekday")])
st.caption("Cups to prep per day in Sep 2026, by weekday (0 = Monday). Plan in cups and THB: the data has no grams per cup.")
st.dataframe(wk.pivot_table(index=["kitchen", "sku"], columns="dow", values="prep_cups").astype(int), width="stretch")

st.subheader("Does the prep rule beat today's prep?")
rb = c.load("prep_rule_backtest")
plan = rb[(rb["period"] == "2026-08") & (rb["variant"] == "CR+0.1, promo x lift")].set_index("sku").reindex(c.ITEMS)
fig = go.Figure(go.Bar(x=plan.index, y=plan["saving_per_month"] / 1000,
                       marker_color=[c.UP if v >= 0 else c.DOWN for v in plan["saving_per_month"]],
                       text=(plan["saving_per_month"] / 1000).round(1), textposition="outside",
                       hovertemplate="%{x}<br>%{y:.1f}k THB a month<extra></extra>"))
fig.update_yaxes(title="THB thousands a month")
wins = plan[plan["saving_per_month"] > 0]
c.show(fig, f"In August the rule saves {wins['saving_per_month'].sum() / 1000:.1f}k a month on "
            f"{' and '.join(wins.index)}; it loses on the 3 cheap items",
       "Saving vs today's prep (waste x Co + short x Cu), Aug 2026, CR + 0.1, promo days x lift. "
       "No sold-out data, so this favours today", height=400, legend=False)
st.dataframe(rb[rb["sku"] != "All"].pivot_table(index="sku", columns=["period", "variant"], values="saving_per_month")
             .reindex(c.ITEMS).round(0), width="stretch")

st.subheader("What happens to profit in Sep-Nov?")
ss = c.load("scenario_summary")
fig = go.Figure()
for name, g in ss.groupby("scenario", sort=False):
    fig.add_bar(x=g["month"], y=g["operating_profit"] / 1000, name=name, marker_color=c.SCENARIO_COLORS.get(name, c.TOTAL),
                hovertemplate=name + "<br>%{x}: %{y:,.0f}k THB<extra></extra>")
fig.add_hline(y=0, line=dict(color="#c3c2b7", width=1))
fig.update_layout(barmode="group")
fig.update_yaxes(title="THB thousands")
three = ss.groupby("scenario")["operating_profit"].sum()
c.show(fig, f"Every scenario loses money in Sep-Nov; Action cuts the loss from {-three['Base'] / 1000:.0f}k "
            f"to {-three['Action'] / 1000:.0f}k",
       "Operating profit (GP-C - 670k overhead) by month, THB thousands. Elasticity -1.5", height=440)
tbl = ss.pivot_table(index="scenario", columns="month", values="operating_profit", sort=False)
tbl["3 months"] = tbl.sum(axis=1)
st.dataframe((tbl / 1000).round(1), width="stretch")
lv = c.load("scenario_levers")
st.caption("Lever bridge (THB k a month): one lever at a time in the same model, so nothing is counted twice.")
st.dataframe(c.in_k(lv, ["elasticity_-1.5", "elasticity_-0.5"]), hide_index=True)

st.subheader("Who does what, by when?")
st.dataframe(c.in_k(c.load("profit_plan"), ["thb_per_month"]), hide_index=True)
