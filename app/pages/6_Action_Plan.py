"""Action plan: Sep-Nov operating profit per scenario, the value of each lever, and who does what."""
import plotly.graph_objects as go
import streamlit as st

import common as c

ss = c.load("scenario_summary").sort_values("month")
lv = c.load("scenario_levers").set_index("step")
pp = c.load("profit_plan")
rec = c.load("recommendations").set_index("area")
LOW, HIGH = [col for col in lv.columns if col.startswith("elasticity_")]  # low and high elasticity cases
horizon = c.span(ss["month"])
n_months = ss["month"].nunique()
order = list(dict.fromkeys(ss["scenario"]))
three = ss.groupby("scenario", sort=False)["operating_profit"].sum().reindex(order)
overhead = ss.groupby("scenario", sort=False)["overhead"].sum().iloc[0]

c.page_header(
    c.ACTION,
    f"**{horizon} operating profit: Base {c.thb(three.get('Base', 0))}, Action {c.thb(three.get('Action', 0))}, "
    f"Downside {c.thb(three.get('Downside', 0))}.** Even with all actions the period loses money after overhead; "
    "the rest needs a Bangkok overhead review.")

HELP = {"Base": "Today's prices, promos and prep.",
        "Action": "Price rises, stop the losing promos, the prep rule and berry at the higher price.",
        "Action + delist berry": "Action, and berry taken off the menu.",
        "Downside": "Action with fruit cost up and demand down (sizes in the decision log, lesson 11)."}
base = three.get("Base", 0)
c.kpi_row([
    dict(label=s, value=c.thb(v), delta=None if s == "Base" else f"{c.sthb(v - base)} vs Base",
         delta_arrow="auto", series=ss.loc[ss["scenario"] == s, "operating_profit"],
         help=f"Operating profit over {horizon} after {c.thb(overhead)} overhead. {HELP.get(s, '')}")
    for s, v in three.items()
])

left, right = st.columns([2, 3])
with left:
    op = ss.pivot_table(index="scenario", columns="month", values="operating_profit", sort=False)
    op.columns = [c.month_name(m) for m in op.columns]
    op[f"{n_months} months"] = op.sum(axis=1)
    extra = ss.groupby("scenario", sort=False).agg(revenue=("gross_revenue", "sum"), gp=("gross_profit", "sum"),
                                                   waste=("waste_cost", "sum"))
    op["GP %"] = extra["gp"] / extra["revenue"] * 100
    op["Revenue"] = extra["revenue"]
    op["Waste cost"] = extra["waste"]
    stbl = op.reset_index().rename(columns={"scenario": "Scenario"})
    month_cols = [col for col in stbl.columns if col not in ("Scenario", "GP %", "Revenue", "Waste cost")]
    gain = three.get("Action", 0) - base
    with c.card(f"The plan cuts the {horizon} loss by {c.thb(gain)}, but no scenario covers the overhead",
                so_what=f"low-season sales do not cover the {c.thb(overhead / n_months)} monthly overhead. The "
                        f"Bangkok overhead review ({rec.loc['Kitchens', 'start_date'] if 'Kitchens' in rec.index else 'Q4'}"
                        ") is the gap that is left.",
                method="One model per month x kitchen x item, so no lever is counted twice. Overhead is the same in "
                       "every scenario. Price tests count as 0 until they pass. Downside = Action with fruit cost "
                       "up and demand down."):
        c.table(stbl, cols=["Scenario"] + month_cols + ["GP %"], pcts=["GP %"],
                money=month_cols + ["Revenue", "Waste cost"], highlight=stbl["Scenario"].eq("Action"),
                name="scenario_summary", raw=ss)

with right:
    steps = lv[lv["kind"] == "change"][LOW]
    best = steps.idxmax() if len(steps) else None
    labels = [c.promo(s).replace(" + ", "<br>+ ") for s in steps.index]
    fig = go.Figure(go.Bar(y=labels, x=steps, orientation="h",
                           marker_color=[c.KEY if s == best else (c.LOSS if v < 0 else c.GREY) for s, v in steps.items()],
                           text=[c.sthb(v) for v in steps], cliponaxis=False,
                           textposition=["inside" if v < 0 else "outside" for v in steps],
                           customdata=[c.sthb(v) for v in steps],
                           hovertemplate="%{y}<br>%{customdata} a month<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=c.DARK, width=1))
    width = max(steps.max(), 0) - min(steps.min(), 0)
    lo, hi = min(steps.min(), 0) - width * 0.1, max(steps.max(), 0) + width * 0.25
    fig.update_xaxes(title="Operating profit a month vs Base (฿)", range=[lo, hi], **c.money_ticks(lo, hi))
    fig.update_yaxes(autorange="reversed")
    delist = steps[steps < 0]
    stop = rec.loc["Menu", "stop_rule"] if "Menu" in rec.index else ""
    with c.card(f"{c.promo(best)} is the biggest lever ({c.sthb(steps[best])} a month)" if best else "Levers",
                so_what=(f"delisting berry would lose {c.thb(-delist.iloc[0])} a month more. " if len(delist) else "")
                        + f"Keep berry at the higher price with the prep rule and a stop rule ({stop[:1].lower()}"
                          f"{stop[1:]}) instead of delisting it now.",
                how_to_read=f"Each bar adds one lever to the same model in turn, so nothing is counted twice: the "
                            f"bars before 'Delist berry' add up to Action vs Base, and 'Delist berry' is the extra "
                            f"step to Action + delist berry. Values use elasticity {LOW.split('_')[1]} (the cautious "
                            f"case); the full table also shows {HIGH.split('_')[1]}."):
        c.show(fig, height=300)
        with st.expander("Full table"):
            c.table(lv.reset_index().assign(step=lambda d: d["step"].map(c.promo), kind=lambda d: d["kind"].map(
                c.title_case)), money=[LOW, HIGH], name="scenario_levers", raw=lv.reset_index())

plan = pp.assign(action=pp["action"].map(c.promo), stop_rule=pp["stop_rule"].map(c.promo))
with c.card(f"Who does what, by when: {pp['in_model'].sum()} actions in the model, {(~pp['in_model']).sum()} tests "
            "and reviews on top",
            so_what="each action has an owner, a start date, a number to watch and a stop rule, so a bad result is "
                    "caught in weeks, not at the end of the quarter. Rows not in the model count as 0 until they pass."):
    c.table(plan, cols=["action", "owner", "start_date", "stop_rule", "thb_per_month"], static=True,
            money=["thb_per_month"], highlight=pp["in_model"], name="profit_plan", raw=pp)

c.next_page(c.METHOD, label=f"Next: {c.PAGES[c.METHOD].question} (glossary and decision log)")
