"""Forecast and inventory: backtest, Sep-Nov forecast, prep rule, waste, scenarios and the profit plan."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

kitchen = c.pick("Kitchen", c.KITCHENS, "fi_kitchen")
item = c.pick("Item", c.ITEMS, "fi_item")


def keep(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the sidebar kitchen and item filters."""
    if kitchen != "All":
        df = df[df["kitchen"] == kitchen]
    if item != "All":
        df = df[df["sku"] == item]
    return df


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
ss = c.load("scenario_summary")
lv = c.load("scenario_levers").set_index("step")
LOW, HIGH = [col for col in lv.columns if col.startswith("elasticity_")]  # low and high elasticity cases
horizon = c.span(fm["month"])
n_months = fm["month"].nunique()

main = fb[fb["test"].str.startswith("Jun-Aug") & (fb["sku"] == "All")].set_index("method")
winner = main.index[main["winner"]][0]
old = fm[fm["sku"] != c.BERRY]
old_gap = (old["forecast"].sum() / old["cups_2025"].sum() - 1) * 100
rule_items = inv.loc[inv["rule"].str.startswith("CR"), "sku"].unique().tolist()
rule_step = lv.index[lv.index.str.startswith("Prep rule")][0]
three = ss.groupby("scenario", sort=False)["operating_profit"].sum()

c.page_header(
    c.PAGES["pages/5_Forecast_and_Inventory.py"][1],
    f"**About {fm['forecast'].sum():,.0f} cups in {horizon}; the old items are {c.spct(old_gap)} vs the same months "
    f"of last year.** Prep {' and '.join(rule_items).replace(c.BERRY, 'berry')} with the new rule "
    f"({c.sthb(lv.loc[rule_step, LOW])} a month) and keep today's prep for the others. "
    f"Even with every action, the {n_months} months lose {c.thb(-three['Action'])} after overhead "
    f"(Base: {c.thb(-three['Base'])}).")

# ---- backtest ----
st.subheader("Which forecast method wins?")
same = fb[~fb["test"].str.startswith("Jun-Aug") & (fb["sku"] == "All")]
bt = pd.DataFrame({"Method": [method_name(m) for m in main.index],
                   "WAPE, Jun-Aug": main["wape_pct"].to_numpy(), "Bias, Jun-Aug": main["bias_pct"].to_numpy()})
for test, g in same.groupby("test", sort=False):
    bt[f"WAPE, {test.split(' (')[0]} only"] = g.set_index("method")["wape_pct"].reindex(main.index).to_numpy()
c.table(bt, pcts=[col for col in bt.columns if col != "Method"], highlight=main["winner"].to_numpy())
st.markdown(f"**{method_name(winner)} wins** with the lowest WAPE in the main test "
            f"({main['test'].iloc[0]}). WAPE = total forecast error as % of actual cups (lower is better). "
            f"Bias = total forecast minus actual, as % of actual (+ = too high). Every method is "
            f"{main['bias_pct'].min():.0f}-{main['bias_pct'].max():.0f}% too high in Jun-Aug: none of them sees the "
            f"rainy-season drop. In one-month tests inside one season they all score "
            f"{same['wape_pct'].min():.0f}-{same['wape_pct'].max():.0f}%.")
c.download(fb, "forecast_backtest")

# ---- forecast ----
st.subheader(f"What will {horizon} sell?")
hist = keep(c.load("item_kitchen_pnl")).groupby("month")["cups"].sum()
f = keep(fm)
fut = f.groupby("month")["forecast"].sum()
label = lambda ms: [pd.Timestamp(f"{m}-01").strftime("%b %y") for m in ms]  # noqa: E731
fig = go.Figure()
fig.add_scatter(x=label(hist.index), y=hist, name="Actual", mode="lines+markers", line=dict(color=c.DARK, width=2),
                hovertemplate="%{x}<br>%{y:,.0f} cups<extra>Actual</extra>")
fig.add_scatter(x=label([hist.index[-1]] + list(fut.index)), y=[hist.iloc[-1]] + list(fut), name="Forecast",
                mode="lines+markers", line=dict(color=c.KEY, width=2, dash="dash"),
                hovertemplate="%{x}<br>%{y:,.0f} cups<extra>Forecast</extra>")
fig.update_yaxes(title="Cups a month", rangemode="tozero")
f_old = f[f["sku"] != c.BERRY]
gap = (f_old["forecast"].sum() / f_old["cups_2025"].sum() - 1) * 100 if f_old["cups_2025"].sum() > 0 else None
c.show(fig, f"{horizon} forecast: {fut.sum():,.0f} cups"
       + (f"; old items {c.spct(gap)} vs the same months of 2025" if gap is not None else
          "; berry is held flat at its latest level"),
       f"Kitchen: {kitchen}, item: {item}. Sep = {method_name(winner).lower()}, Oct-Nov = Sep x last year's "
       "month-to-month change, berry flat", height=400, legend=True)
c.chart_note(f"{c.month_name(fut.index[-1])} is {c.spct((fut.iloc[-1] / fut.iloc[0] - 1) * 100, 0)} "
             f"vs {c.month_name(fut.index[0])}, as last year: order fruit and plan staff for a rising quarter. "
             "Berry has no last year, so its flat forecast is on the high side.")
c.download(f, "forecast_monthly")

# ---- prep ----
st.subheader("How much should each kitchen prep?")
cr = rb[(rb["variant"] == "CR") & (rb["sku"] != "All")].drop_duplicates("sku").set_index("sku")["quantile"]
cheap = cr.drop(rule_items, errors="ignore")
st.markdown(f"A cup we prep and throw away costs its fruit and packaging (**Co**); a cup a customer wants but we do "
            f"not have costs its margin (**Cu**). The rule preps up to the **critical ratio** CR = Cu / (Cu + Co) of "
            f"recent same-weekday demand: berry CR {cr[c.BERRY]:.2f} and PassionFruit {cr['PassionFruit']:.2f} "
            f"(prep lean, waste costs more than a lost sale), the cheap items {cheap.min():.2f}-{cheap.max():.2f} "
            "(close to average demand, so today's prep is already fine).")
mon = keep(inv[inv["level"] == "month"])
tot = mon.groupby("month")[["prep_cups", "fruit_budget_thb", "fruit_budget_downside_thb"]].sum()
cols = st.columns(len(tot))
for col, (month, r) in zip(cols, tot.iterrows()):
    col.metric(f"Prep, {c.month_name(month)}", f"{r['prep_cups']:,.0f} cups", f"fruit {c.thb(r['fruit_budget_thb'])}",
               delta_description=f"{c.thb(r['fruit_budget_downside_thb'])} if fruit costs rise", delta_color="off",
               delta_arrow="off", border=True)
itbl = mon[["month", "kitchen", "sku", "rule", "demand", "prep_cups", "waste_cups", "short_cups", "waste_rate_pct",
            "fruit_budget_thb"]]
c.table(itbl, count=["demand", "prep_cups", "waste_cups", "short_cups"], pcts=["waste_rate_pct"],
        money=["fruit_budget_thb"], highlight=itbl["rule"].str.startswith("CR"))
c.download(itbl, "inventory_plan")
with st.expander(f"Cups to prep per day in {c.month_name(fm['month'].min())}, by weekday"):
    wk = keep(inv[inv["level"].str.startswith("weekday")]).copy()
    wk["day"] = wk["dow"].map(dict(enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])))
    grid = wk.pivot_table(index=["kitchen", "sku"], columns="day", values="prep_cups")
    grid = grid[[d for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] if d in grid.columns]]
    st.dataframe(grid.style.format("{:,.0f}"))
    st.caption("Plan in cups and THB: the data has no grams per cup.")
    c.download(grid.reset_index(), "prep_by_weekday")

aug = rb[(rb["period"] == rb["period"].max()) & rb["variant"].str.contains("lift")]
plan = aug[aug["sku"] != "All"].set_index("sku")["saving_per_month"].reindex(c.ITEMS)
wins = plan[plan > 0]
fig = go.Figure(go.Bar(x=plan.index, y=plan, marker_color=c.colors(plan.index, wins.index),
                       text=[c.sthb(v) for v in plan], textposition="outside", customdata=[c.sthb(v) for v in plan],
                       hovertemplate="%{x}<br>%{customdata} a month<extra></extra>"))
fig.add_hline(y=0, line=dict(color=c.DARK, width=1))
lo, hi = plan.min() * 1.3, plan.max() * 1.4
fig.update_yaxes(title="Saving vs today's prep, a month (฿)", range=[lo, hi], **c.money_ticks(lo, hi))
c.show(fig, f"In {c.month_name(rb['period'].max())} the rule saves {c.thb(wins.sum())} a month on "
            f"{' and '.join(wins.index).replace(c.BERRY, 'berry')}; it loses on the other items",
       f"Backtest: rule ({aug['variant'].iloc[0]}) vs what the kitchens really prepped. Saving = less waste cost "
       "- margin lost on short cups", height=400)
c.how_to_read("This is a newsvendor test: we replay each day with the rule's prep and compare its cost with what "
              "the kitchen really did. Cost = wasted cups x Co + short cups x Cu. Above 0 = the rule is cheaper. "
              "The data has no sold-out log, so today's prep never shows a short cup: the test favours today. "
              "The rule still wins where waste is expensive (low CR), so we use it only there.")
c.chart_note("use the rule for " + " and ".join(wins.index).replace(c.BERRY, "berry") + " only; for the cheap items "
             "today's prep already sits near the right level, and the rule would turn customers away.")

# ---- waste ----
st.subheader("Where does the waste come from?")
wi = ws[ws["level"] == "item"].set_index("group").reindex(c.ITEMS)
share = wi["waste_cost"] / wi["waste_cost"].sum() * 100
fig = go.Figure(go.Bar(x=wi.index, y=wi["thb_per_month"], marker_color=c.colors(wi.index, [c.BERRY], c.LOSS),
                       text=[c.thb(v) for v in wi["thb_per_month"]], textposition="outside",
                       customdata=[f"{c.thb(v)} a month, waste rate {c.pct(r)}" for v, r in
                                   zip(wi["thb_per_month"], wi["waste_rate_pct"])],
                       hovertemplate="%{x}<br>%{customdata}<extra></extra>"))
hi = wi["thb_per_month"].max() * 1.25
fig.update_yaxes(title="Waste cost a month (฿)", range=[0, hi], **c.money_ticks(0, hi))
c.show(fig, f"Berry is {c.pct(share[c.BERRY], 0)} of waste cost with "
            f"{c.pct(wi.loc[c.BERRY, 'sold'] / wi['sold'].sum() * 100)} of cups sold",
       f"Waste cost a month by item (fruit + packaging), {c.data_period()}; berry since launch", height=380)
c.chart_note(f"berry throws away {c.pct(wi.loc[c.BERRY, 'waste_rate_pct'])} of what it preps vs "
             f"{c.pct(wi.drop(c.BERRY)['waste_rate_pct'].min())}-{c.pct(wi.drop(c.BERRY)['waste_rate_pct'].max())} "
             "for the old items: cutting berry waste is the biggest single saving.")
wk_ = ws[ws["level"] == "kitchen"][["group", "sold", "wasted", "waste_cost", "waste_rate_pct", "thb_per_month"]]
c.table(wk_.rename(columns={"group": "kitchen", "waste_rate_pct": "waste rate", "thb_per_month": "waste a month"}),
        count=["sold", "wasted"], money=["waste_cost", "waste a month"], pcts=["waste rate"])
st.caption("Waste by item and kitchen for the full year. The sidebar filters do not apply to this section.")
c.download(ws, "waste_summary")

# ---- scenarios ----
st.subheader(f"What happens to profit in {horizon}?")
op = ss.pivot_table(index="scenario", columns="month", values="operating_profit", sort=False)
op.columns = [c.month_name(m) for m in op.columns]
op[f"{n_months} months"] = op.sum(axis=1)
extra = ss.groupby("scenario", sort=False).agg(revenue=("gross_revenue", "sum"), gp=("gross_profit", "sum"),
                                               waste=("waste_cost", "sum"))
op["Revenue"] = extra["revenue"]
op["GP %"] = extra["gp"] / extra["revenue"] * 100
op["Waste cost"] = extra["waste"]
stbl = op.reset_index().rename(columns={"scenario": "Scenario"})
c.table(stbl, money=[col for col in stbl.columns if col not in ("Scenario", "GP %")], pcts=["GP %"],
        highlight=stbl["Scenario"].eq("Action"))
st.caption(f"Operating profit by month after {c.thb(ss['overhead'].iloc[0])} overhead a month; revenue, GP % and "
           f"waste over {n_months} months. Base = today's prices, promos and prep. Action = the "
           f"{c.load('profit_plan')['in_model'].sum()} costed actions on the home page. Downside = Action with fruit "
           "cost up and demand down.")
c.download(ss, "scenario_summary")

steps = lv[lv["kind"] == "change"][LOW]
best = steps.idxmax()
fig = go.Figure(go.Bar(y=steps.index, x=steps, orientation="h",
                       marker_color=[c.KEY if s == best else (c.LOSS if v < 0 else c.GREY) for s, v in steps.items()],
                       text=[c.sthb(v) for v in steps], textposition="outside", customdata=[c.sthb(v) for v in steps],
                       hovertemplate="%{y}<br>%{customdata} a month<extra></extra>"))
fig.add_vline(x=0, line=dict(color=c.DARK, width=1))
lo, hi = min(steps.min(), 0) * 1.6, steps.max() * 1.35
fig.update_xaxes(title="Operating profit a month vs Base (฿)", range=[lo, hi], **c.money_ticks(lo, hi))
fig.update_yaxes(autorange="reversed")
delist = steps[steps < 0]
c.show(fig, f"The prep rule is the biggest lever ({c.sthb(steps[best])} a month)"
       + (f"; delisting berry would lose {c.thb(-delist.iloc[0])} a month more" if len(delist) else ""),
       "Each lever added one at a time in the same model, so nothing is counted twice. "
       f"Elasticity {LOW.split('_')[1]} (low case)",
       height=380)
stop = c.load("recommendations").set_index("area").loc["Menu", "stop_rule"]
c.chart_note(f"keep berry at the higher price with the prep rule and a stop rule ({stop[0].lower()}{stop[1:]}), "
             "instead of delisting it now.")
c.table(lv.reset_index(), money=[LOW, HIGH])
c.download(lv.reset_index(), "scenario_levers")

st.subheader("Who does what, by when?")
pp = c.load("profit_plan")
c.table(pp, money=["thb_per_month"], highlight=pp["in_model"])
c.download(pp, "profit_plan")

c.method_box(
    f"- **Backtest:** {main['test'].iloc[0]}, the same length as the {horizon} horizon, daily per kitchen and "
    "item. Rolling values use only past days (no look-ahead).\n"
    "- **Forecast:** Sep from the backtest winner; Oct and Nov = Sep x last year's Oct/Sep and Nov/Sep change per "
    "kitchen and item; berry has no last year, so it stays at its latest weekday level.\n"
    "- **Prep rule (newsvendor):** prepared = sold + wasted (there is no prep log). Cu = margin per cup, Co = waste "
    "cost per wasted cup, both from Jun-Aug. On promo days, rule items prep the normal level x the measured promo "
    "lift.\n"
    "- **Scenarios:** one model per month x kitchen x item, so no lever is counted twice. Overhead is the same in "
    "every scenario. Price tests count as 0 until they pass.")
