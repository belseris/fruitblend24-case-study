"""Forecast and prep: backtest, Sep-Nov forecast, prep rule and where the waste comes from."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c


def method_name(m: str) -> str:
    """Readable forecast method name."""
    if m.startswith("weekday_mean_"):
        return f"Weekday mean, last {m.split('_')[-1].rstrip('w')} weeks"
    return {"seasonal_naive": "Seasonal naive (repeat the last week)",
            "holt_winters_damped": "Holt-Winters (damped trend, weekly season)"}.get(m, m)


fb = c.load("forecast_backtest")
fm = c.load("forecast_monthly")
inv = c.load("inventory_plan")
rb = c.load("prep_rule_backtest")
ws = c.load("waste_summary")
horizon = c.span(fm["month"])

main = fb[fb["test"].str.startswith("Jun-Aug") & (fb["sku"] == "All")].set_index("method")
winner = main.index[main["winner"]][0] if main["winner"].any() else main["wape_pct"].idxmin()
old = fm[fm["sku"] != c.BERRY]
old_gap = (old["forecast"].sum() / old["cups_2025"].sum() - 1) * 100
rule_items = inv.loc[inv["rule"].str.startswith("CR"), "sku"].unique().tolist()

c.page_header(
    c.FORECAST,
    f"**{fm['forecast'].sum():,.0f} cups forecast for {horizon}; the old items are {c.spct(old_gap)} vs the same "
    f"months of 2025.** Prep {c.join(c.short_item(s) for s in rule_items)} with a new rule and keep today's prep for "
    "the rest.")

by_month = fm.groupby("month")[["forecast"]].sum()
old_month = old.groupby("month")[["forecast", "cups_2025"]].sum()
c.kpi_row([
    dict(label=f"Forecast, {c.month_name(m)}", value=f"{r['forecast']:,.0f} cups",
         delta=c.spct((old_month.loc[m, "forecast"] / old_month.loc[m, "cups_2025"] - 1) * 100),
         delta_description=f"old items vs {c.month_short(str(int(m[:4]) - 1) + m[4:])}",
         help="All items, all kitchens. The delta compares the 4 old items with the same month last year "
              "(berry has no last year).")
    for m, r in by_month.iterrows()
])

# ---- forecast ----
with c.card(f"{horizon}: about {fm['forecast'].sum():,.0f} cups, rising month by month as last year",
            method=f"Sep from the backtest winner ({method_name(winner).lower()}); Oct and Nov = Sep x last "
                   "year's Oct/Sep and Nov/Sep change per kitchen and item. Berry has no last year, so it stays "
                   "at its latest weekday level."):
    kitchen = c.choose("Kitchen", c.KITCHENS, key="fc_kitchen")
    item = c.choose("Item", c.ITEMS, key="fc_item")

    def keep(df: pd.DataFrame) -> pd.DataFrame:
        """Apply the kitchen and item controls."""
        if kitchen != "All":
            df = df[df["kitchen"] == kitchen]
        if item != "All":
            df = df[df["sku"] == item]
        return df

    hist = keep(c.load("item_kitchen_pnl")).groupby("month")["cups"].sum()
    f = keep(fm)
    fut = f.groupby("month")["forecast"].sum()
    fig = go.Figure()
    if len(hist):
        fig.add_scatter(x=[c.month_short(m) for m in hist.index], y=hist, name="Actual", mode="lines+markers",
                        line=dict(color=c.DARK, width=2), hovertemplate="%{x}<br>%{y:,.0f} cups<extra>Actual</extra>")
    if len(hist) and len(fut):
        fig.add_scatter(x=[c.month_short(m) for m in [hist.index[-1]] + list(fut.index)],
                        y=[hist.iloc[-1]] + list(fut), name="Forecast", mode="lines+markers",
                        line=dict(color=c.KEY, width=2, dash="dash"),
                        hovertemplate="%{x}<br>%{y:,.0f} cups<extra>Forecast</extra>")
    fig.update_yaxes(title="Cups a month", rangemode="tozero")
    fig.update_xaxes(tickangle=0, nticks=6)
    f_old = f[f["sku"] != c.BERRY]
    gap = (f_old["forecast"].sum() / f_old["cups_2025"].sum() - 1) * 100 if f_old["cups_2025"].sum() > 0 else None
    st.markdown(f"{'All kitchens' if kitchen == 'All' else kitchen}, {'all items' if item == 'All' else item}: "
                f"{fut.sum():,.0f} cups"
                + (f"; old items {c.spct(gap)} vs the same months of 2025." if gap is not None else
                   "; berry is held flat at its latest level."))
    c.show(fig, height=290, legend=True)
    if len(fut) > 1:
        st.caption(f"So what: {c.month_name(fut.index[-1])} is {c.spct((fut.iloc[-1] / fut.iloc[0] - 1) * 100, 0)} "
                   f"vs {c.month_name(fut.index[0])}, as last year: order fruit and plan staff for a rising "
                   "quarter. Berry has no last year, so its flat forecast is on the high side.")
    c.download(f, "forecast_monthly")


# ---- backtest and prep rule ----
cr = rb[(rb["variant"] == "CR") & (rb["sku"] != "All")].drop_duplicates("sku").set_index("sku")["quantile"]
cheap = cr.drop(rule_items, errors="ignore")
left, right = st.columns(2)
with left:
    same = fb[~fb["test"].str.startswith("Jun-Aug") & (fb["sku"] == "All")]
    bt = pd.DataFrame({"Method": [method_name(m).split(" (")[0] for m in main.index],
                       "WAPE, Jun-Aug": main["wape_pct"].to_numpy(), "Bias, Jun-Aug": main["bias_pct"].to_numpy()})
    for test, g in same.groupby("test", sort=False):
        bt[f"WAPE, {test.split(' (')[0]} only"] = g.set_index("method")["wape_pct"].reindex(main.index).to_numpy()
    with c.card(f"{method_name(winner).split(' (')[0]} wins the backtest, but every method misses the rainy-season "
                "drop",
                so_what=f"every method is {main['bias_pct'].min():.0f}-{main['bias_pct'].max():.0f}% too high in "
                        f"Jun-Aug; inside one season they all score {same['wape_pct'].min():.0f}-"
                        f"{same['wape_pct'].max():.0f}%. So the forecast adds last year's month-to-month change on top.",
                method=f"Train up to May 31, test {main['test'].iloc[0].split(' (')[0]}: the same length as the "
                       f"{horizon} horizon, daily per kitchen and item. Rolling values use only past days (no "
                       "look-ahead). The two one-month tests check each method inside one season."):
        st.markdown("**WAPE** = total forecast error as % of actual cups (lower is better). **Bias** = forecast minus "
                    "actual, as % of actual (+ = too high).")
        c.table(bt, cols=["Method", "WAPE, Jun-Aug", "Bias, Jun-Aug"],
                pcts=[col for col in bt.columns if col != "Method"], highlight=main["winner"].to_numpy(), name="forecast_backtest", raw=fb)

with right:
    aug = rb[(rb["period"] == rb["period"].max()) & rb["variant"].str.contains("lift")]
    saving = aug[aug["sku"] != "All"].set_index("sku")["saving_per_month"].reindex(c.ITEMS)
    wins = saving[saving > 0]
    fig = go.Figure(go.Bar(x=[c.short_item(s) for s in saving.index], y=saving,
                           marker_color=[c.KEY if s in wins.index else c.LOSS for s in saving.index],
                           text=[c.sthb(v) for v in saving], textposition="outside", cliponaxis=False,
                           customdata=[c.sthb(v) for v in saving],
                           hovertemplate="%{x}<br>%{customdata} a month<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=c.DARK, width=1))
    lo, hi = min(saving.min(), 0) * 1.3, max(saving.max(), 0) * 1.4
    fig.update_yaxes(title="Saving vs today's prep, a month (฿)", range=[lo, hi], **c.money_ticks(lo, hi))
    with c.card(f"In {c.month_name(rb['period'].max())} the rule saves {c.thb(wins.sum())} a month on "
                f"{c.join(c.short_item(s) for s in wins.index)}; it loses on the other items",
                so_what=f"use the rule for {c.join(c.short_item(s) for s in wins.index)} only; for the cheap items "
                        "today's prep already sits near the right level, and the rule would turn customers away.",
                how_to_read="We replay each day with the rule's prep and compare its cost with what the kitchen "
                            "really did. Cost = wasted cups x Co (fruit and packaging of a cup thrown away) + short cups "
                            "x Cu (profit lost on a cup a customer wanted). Above 0 = the rule is cheaper. "
                            "The data has no sold-out log, so today's prep never shows a short cup: the test favours "
                            "today. The rule still wins where waste is expensive (low CR), so we use it only there."):
        c.show(fig, height=330)

# ---- prep plan ----
mon = inv[inv["level"] == "month"]
rule_rows = mon[mon["sku"].isin(rule_items)].groupby("sku")[["short_cups", "demand"]].sum()
short = (rule_rows["short_cups"] / rule_rows["demand"]).reindex([x for x in c.ITEMS if x in rule_rows.index])
plan = mon.pivot_table(index=["sku", "rule"], columns="month", values="prep_cups", aggfunc="sum")
plan.columns = [c.month_name(m) for m in plan.columns]
plan["Fruit budget"] = mon.groupby(["sku", "rule"])["fruit_budget_thb"].sum()
plan = plan.reset_index().set_index("sku").reindex([s for s in c.ITEMS if s in set(mon["sku"])]).reset_index()
plan["rule"] = plan["rule"].map(c.title_case)
months = [col for col in plan.columns if col not in ("sku", "rule", "Fruit budget")]
with c.card(f"Prep {c.join(c.short_item(s) for s in rule_items)} lean; keep today's prep for the cheap items "
            "(highlighted rows use the new rule)",
            so_what=f"the rule runs out on purpose: it leaves "
                    + c.join(f"{c.pct(short[s_] * 100, 0)} of {c.short_item(s_)}" for s_ in short.index)
                    + " demand unserved in Sep-Nov. A lost cup is costed as lost profit only; lost repeat customers "
                    "and app ranking are not, so the stop rule watches sold-outs every week. Fruit budget for "
                    f"{horizon}: {c.thb(mon['fruit_budget_thb'].sum())}, or {c.thb(mon['fruit_budget_downside_thb'].sum())} "
                    "if fruit costs rise.",
            method="Prepared = sold + wasted (there is no prep log). Cu = profit per cup, Co = waste cost per "
                   "wasted cup, both from Jun-Aug. Prep = the CR + 0.1 quantile of the last 8 normal same-weekday "
                   "days, no look-ahead. On promo days, rule items prep the normal level x the measured promo "
                   "lift."):
    st.markdown(f"A cup we prep and throw away costs its fruit and packaging (**Co**); a cup a customer wants but "
                f"we do not have costs its profit (**Cu**). Prep up to the **critical ratio** CR = Cu / (Cu + Co) "
                f"of recent demand: berry {cr.get(c.BERRY, float('nan')):.2f}, PassionFruit "
                f"{cr.get('PassionFruit', float('nan')):.2f}, the cheap items {cheap.min():.2f}-{cheap.max():.2f}.")
    c.table(plan, count=months, money=["Fruit budget"], highlight=plan["rule"].str.startswith("CR"))
    with st.expander("Full table: month x kitchen x item"):
        itbl = mon[["month", "kitchen", "sku", "rule", "demand", "prep_cups", "waste_cups", "short_cups",
                    "waste_rate_pct", "fruit_budget_thb"]]
        c.table(itbl, count=["demand", "prep_cups", "waste_cups", "short_cups"], pcts=["waste_rate_pct"],
                money=["fruit_budget_thb"], highlight=itbl["rule"].str.startswith("CR"), name="inventory_plan")
    with st.expander(f"Cups to prep per day in {c.month_name(fm['month'].min())}, by weekday"):
        wk = inv[inv["level"].str.startswith("weekday")].copy()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        wk["day"] = wk["dow"].map(dict(enumerate(day_names)))
        grid = wk.pivot_table(index=["kitchen", "sku"], columns="day", values="prep_cups")
        grid = grid[[d for d in day_names if d in grid.columns]].reset_index()
        c.table(grid, count=[d for d in day_names if d in grid.columns], name="prep_by_weekday")

# ---- waste ----
wi = ws[ws["level"] == "item"].set_index("group").reindex(c.ITEMS)
wk_ = ws[ws["level"] == "kitchen"].set_index("group").reindex(c.KITCHENS)
share = wi["waste_cost"] / wi["waste_cost"].sum() * 100
left, right = st.columns(2)
with left:
    fig = go.Figure(go.Bar(x=[c.short_item(s) for s in wi.index], y=wi["thb_per_month"],
                           marker_color=c.colors(wi.index, [c.BERRY], c.LOSS),
                           text=[c.thb(v) for v in wi["thb_per_month"]], textposition="outside", cliponaxis=False,
                           customdata=[f"{c.thb(v)} a month, waste rate {c.pct(r)}" for v, r in
                                       zip(wi["thb_per_month"], wi["waste_rate_pct"])],
                           hovertemplate="%{x}<br>%{customdata}<extra></extra>"))
    hi = wi["thb_per_month"].max() * 1.25
    fig.update_yaxes(title="Waste cost a month (฿)", range=[0, hi], **c.money_ticks(0, hi))
    with c.card(f"Berry is {c.pct(share[c.BERRY], 0)} of waste cost with "
                f"{c.pct(wi.loc[c.BERRY, 'sold'] / wi['sold'].sum() * 100)} of cups sold",
                so_what=f"berry throws away {c.pct(wi.loc[c.BERRY, 'waste_rate_pct'])} of what it preps vs "
                        f"{c.pct(wi.drop(c.BERRY)['waste_rate_pct'].min())}-"
                        f"{c.pct(wi.drop(c.BERRY)['waste_rate_pct'].max())} for the old items: cutting berry waste is "
                        "the biggest single saving."):
        c.show(fig, height=300)

with right:
    fig = go.Figure(go.Bar(x=wk_.index, y=wk_["thb_per_month"],
                           marker_color=c.colors(wk_.index, [wk_["waste_rate_pct"].idxmax()]),
                           text=[c.thb(v) for v in wk_["thb_per_month"]], textposition="outside", cliponaxis=False,
                           customdata=[f"{c.thb(v)} a month, waste rate {c.pct(r)}" for v, r in
                                       zip(wk_["thb_per_month"], wk_["waste_rate_pct"])],
                           hovertemplate="%{x}<br>%{customdata}<extra></extra>"))
    hi = wk_["thb_per_month"].max() * 1.25
    fig.update_yaxes(title="Waste cost a month (฿)", range=[0, hi], **c.money_ticks(0, hi))
    top_k = wk_["waste_rate_pct"].idxmax()
    others = wk_.drop(top_k)["waste_rate_pct"]
    with c.card(f"{top_k} has the highest waste rate: {c.pct(wk_.loc[top_k, 'waste_rate_pct'])} of what it preps",
                so_what=f"{top_k} throws away {c.pct(wk_.loc[top_k, 'waste_rate_pct'])} of what it preps vs "
                        f"{c.pct(others.min())}"
                        + ("" if c.pct(others.min()) == c.pct(others.max()) else f"-{c.pct(others.max())}")
                        + " in the other kitchens: its prep habits need the closest look."):
        c.show(fig, height=300)
        with st.expander("Full table"):
            c.table(ws[ws["level"] == "kitchen"][["group", "sold", "wasted", "waste_cost", "waste_rate_pct",
                                                 "thb_per_month"]].rename(columns={"group": "kitchen",
                                                                                   "thb_per_month": "Waste a month"}),
                    count=["sold", "wasted"], money=["waste_cost", "Waste a month"], pcts=["waste_rate_pct"],
                    name="waste_summary", raw=ws)
st.caption(f"Waste by item and kitchen for the full year, {c.data_period()}; berry since its launch.")

c.next_page(c.ACTION)
