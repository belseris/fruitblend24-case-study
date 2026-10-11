"""FruitBlend24 case app: executive summary (home page) and navigation."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

st.set_page_config(page_title=c.APP_NAME, layout="wide")

# Page with the evidence for each recommendation area.
AREA_PAGE = {"Waste": "pages/5_Forecast_and_Inventory.py", "Pricing": "pages/2_Demand_and_Pricing.py",
             "Menu": "pages/4_PnL_and_Budget.py", "Promotions": "pages/3_Promotions.py",
             "Tests": "pages/2_Demand_and_Pricing.py", "Kitchens": "pages/4_PnL_and_Budget.py"}
# Plain headline per area; the exact action from recommendations.csv goes under it.
AREA_HEADLINE = {"Waste": "Prep berry and PassionFruit to demand, not by habit",
                 "Pricing": "Raise the Watermelon and PassionFruit prices",
                 "Menu": "Fix the berry price, then decide if berry stays",
                 "Promotions": "Stop the promo codes that lose money"}


def kpis() -> dict:
    """Full-year totals for the KPI row, from company_pnl.csv and budget_variance.csv."""
    m, v = c.load("company_pnl"), c.load("budget_variance")
    k = {col: m[col].sum() for col in ["gross_revenue", "gross_profit", "operating_profit", "waste_cost", "overhead"]}
    k["budget_revenue"], k["budget_gp"] = v["budget_revenue"].sum(), v["budget_gp"].sum()
    # The budget has no operating profit line, so use budget GP minus the same fixed overhead.
    k["budget_op"] = k["budget_gp"] - k["overhead"]
    k["gp_pct"] = k["gross_profit"] / k["gross_revenue"] * 100
    k["budget_gp_pct"] = k["budget_gp"] / k["budget_revenue"] * 100
    return k


def intro() -> str:
    """Two lines on the business and the questions, with counts taken from the outputs."""
    kitchens = c.load("kitchen_pnl")["kitchen"].unique()
    pattaya = sum(k.startswith("Pattaya") for k in kitchens)
    apps = " and ".join(c.load("kitchen_platform_share")["platform"].unique())
    hours = c.load("demand_heatmap")["hour"].nunique()
    months = c.load("company_pnl")["month"]
    horizon = c.span(c.load("forecast_monthly")["month"])
    return (f"FruitBlend24 is an online-only smoothie brand: {len(kitchens)} kitchens ({pattaya} in Pattaya, "
            f"{len(kitchens) - pattaya} in Bangkok) sell {c.load('sales_mix')['sku'].nunique()} smoothies on {apps}, "
            f"{hours} hours a day.  \nThis app uses {len(months)} months of orders ({c.span(months)}) to answer two "
            f"questions: why profit is below budget, and what to do in {horizon} to grow profit and cut waste.")


def kpi_row(k: dict) -> None:
    """Five full-year KPIs with the gap to budget."""
    cols = st.columns(5)
    rev_gap, gp_gap = k["gross_revenue"] - k["budget_revenue"], k["gross_profit"] - k["budget_gp"]
    cols[0].metric("Revenue", c.thb(k["gross_revenue"]),
                   f"{c.sthb(rev_gap)} ({c.spct(rev_gap / k['budget_revenue'] * 100)})", border=True,
                   help=f"Budget {c.thb(k['budget_revenue'])}")
    cols[1].metric("Gross profit (GP-C)", c.thb(k["gross_profit"]),
                   f"{c.sthb(gp_gap)} ({c.spct(gp_gap / k['budget_gp'] * 100)})", border=True,
                   help=f"Budget {c.thb(k['budget_gp'])}")
    cols[2].metric("GP %", c.pct(k["gp_pct"]), f"{k['gp_pct'] - k['budget_gp_pct']:+.1f} pts", border=True,
                   help=f"Budget {c.pct(k['budget_gp_pct'])}")
    cols[3].metric("Operating profit", c.thb(k["operating_profit"]), c.sthb(k["operating_profit"] - k["budget_op"]),
                   border=True, help=f"The budget has no operating profit line. Budget operating profit here = "
                                     f"budget GP ({c.thb(k['budget_gp'])}) - kitchen overhead ({c.thb(k['overhead'])}) "
                                     f"= {c.sthb(k['budget_op'])}.")
    cols[4].metric("Waste cost", c.thb(k["waste_cost"]), f"{c.pct(k['waste_cost'] / k['gross_revenue'] * 100)} of revenue",
                   delta_color="off", delta_arrow="off", border=True, help="There is no waste budget.")
    st.caption(f"Full year, {c.data_period()}. Arrows = gap to budget (budget: revenue {c.thb(k['budget_revenue'])}, "
               f"GP {c.thb(k['budget_gp'])} = {c.pct(k['budget_gp_pct'])}, operating profit {c.sthb(k['budget_op'])} "
               f"after the same overhead). GP-C = revenue after discount - platform commission - fruit - packaging "
               "and labor - waste. Operating profit = GP-C - fixed kitchen overhead.")


def actions() -> None:
    """Top 3 costed actions from recommendations.csv, then the one-model total."""
    rec = c.load("recommendations")
    total = rec[rec["area"].str.startswith("Total")].iloc[0]
    costed = rec[rec["in_total"] & ~rec["area"].str.startswith("Total")]
    top = costed.nlargest(3, "thb_month_low")
    cols = st.columns(3)
    for col, (_, r) in zip(cols, top.iterrows()):
        with col.container(border=True):
            st.markdown(f"**{AREA_HEADLINE.get(r['area'], r['area'])}**")
            st.markdown(f"#### {c.thb_range(r['thb_month_low'], r['thb_month_high'])} a month")
            st.caption(r["action"])
            st.markdown(f"Confidence: **{r['confidence']}**  \nOwner: {r['owner']}  \nStart: {r['start_date']}")
            st.page_link(AREA_PAGE[r["area"]], label=f"Evidence: {c.PAGES[AREA_PAGE[r['area']]][0]}")
    rest = costed.drop(top.index)
    extra = "; ".join(f"{r['action'][0].lower()}{r['action'][1:]} ({c.thb_range(r['thb_month_low'], r['thb_month_high'])} "
                      f"a month, confidence {r['confidence']})" for _, r in rest.iterrows())
    st.markdown(f"Also start now: {extra}. All {len(costed)} actions together add "
                f"**{c.thb_range(total['thb_month_low'], total['thb_month_high'])} a month** in one scenario model "
                "(not a sum of the cards, so nothing is counted twice). Price tests and the Bangkok overhead review "
                "are extra and not in this total.")


def findings() -> list[tuple[str, str]]:
    """Five one-line findings, number first, each with the page that shows it."""
    kp = c.load("kitchen_pnl").groupby("kitchen")["operating_profit"].sum()
    bkk, pattaya = kp.filter(like="BKK").sum(), kp.filter(like="Pattaya").sum()
    m = c.load("company_pnl")
    v = c.load("budget_variance")
    gaps = c.load("gp_bridge").set_index("step")["thb"]
    ws = c.load("waste_summary").query("level == 'item'").set_index("group")
    ue = c.load("unit_economics").query("level == 'item'").set_index("sku")
    codes = c.load("promo_incremental").query("level == 'code'")
    pr = c.load("price_recommendation").set_index("sku")
    up = pr[pr["decision"] == "raise"]
    steps = (up["new_price"] - up["price_now"]).unique()
    step = f"+฿{steps[0]:.0f}" if len(steps) == 1 else "A price rise"
    budget_margin = v["budget_margin_pct"].iloc[0]
    berry_cup = ue.loc[c.BERRY, "cm_after_waste_per_cup"]
    return [
        (f"**{c.thb(m['operating_profit'].sum())} operating profit in {len(m)} months.** The Bangkok kitchens lose "
         f"{c.thb(-bkk)} after overhead; the Pattaya kitchens make {c.thb(pattaya)}.", "pages/4_PnL_and_Budget.py"),
        (f"**{c.thb(v['gp_var'].sum())} gross profit vs budget.** Berry ({c.thb(gaps[f'{c.BERRY} margin gap'])}) and "
         f"PassionFruit ({c.thb(gaps['PassionFruit margin gap'])}) earn below the {c.pct(budget_margin)} budget "
         f"margin; lower sales cost only {c.thb(-gaps['Revenue effect'])}.", "pages/4_PnL_and_Budget.py"),
        (f"**{c.thb(m['waste_cost'].sum())} of fruit thrown away in a year.** Berry is "
         f"{c.pct(ws.loc[c.BERRY, 'waste_cost'] / ws['waste_cost'].sum() * 100, 0)} of it with "
         f"{c.pct(ws.loc[c.BERRY, 'sold'] / ws['sold'].sum() * 100)} of cups, and "
         f"{'loses' if berry_cup < 0 else 'earns'} {c.baht(abs(berry_cup))} a cup after waste.",
         "pages/5_Forecast_and_Inventory.py"),
        (f"**{c.thb(codes['net'].sum() / len(m))} a month from promotions.** All {len(codes)} promo codes lose money "
         "after the discount, extra waste and side effects.", "pages/3_Promotions.py"),
        (f"**{step} on Watermelon and PassionFruit still adds profit.** Customers react less to price "
         f"({pr.loc['Watermelon', 'elasticity']:.2f} and {pr.loc['PassionFruit', 'elasticity']:.2f}) than the "
         f"break-even level ({pr.loc['Watermelon', 'breakeven_elasticity']:.2f} and "
         f"{pr.loc['PassionFruit', 'breakeven_elasticity']:.2f}).", "pages/2_Demand_and_Pricing.py"),
    ]


def scenario_chart() -> None:
    """Sep-Nov operating profit per scenario; Action highlighted."""
    ss = c.load("scenario_summary")
    order = list(dict.fromkeys(ss["scenario"]))
    three = ss.groupby("scenario")[["operating_profit", "budget_gp", "overhead"]].sum().reindex(order)
    budget_op = three["budget_gp"].iloc[0] - three["overhead"].iloc[0]
    horizon = c.span(ss["month"])
    fig = go.Figure(go.Bar(
        y=three.index, x=three["operating_profit"], orientation="h",
        marker_color=c.colors(three.index, ["Action"]), text=[c.thb(x) for x in three["operating_profit"]],
        textposition="outside", customdata=[c.thb(x) for x in three["operating_profit"]],
        hovertemplate="%{y}<br>%{customdata}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=c.DARK, width=1))
    fig.add_vline(x=budget_op, line=dict(color=c.DARK, width=1, dash="dot"))
    fig.add_annotation(x=budget_op, y=1, yref="paper", text=f"Budget {c.sthb(budget_op)}", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(color=c.DARK, size=12))
    lo, hi = three["operating_profit"].min() * 1.3, max(budget_op, 0) - three["operating_profit"].min() * 0.35
    fig.update_xaxes(title=f"Operating profit, {horizon} (฿)", range=[lo, hi], **c.money_ticks(lo, hi))
    fig.update_yaxes(autorange="reversed")
    base, action = three.loc["Base", "operating_profit"], three.loc["Action", "operating_profit"]
    overhead = three["overhead"].iloc[0]
    c.show(fig, f"The plan cuts the {horizon} loss from {c.thb(-base)} to {c.thb(-action)}; "
                "no scenario covers the kitchen overhead",
           f"Operating profit over {horizon} after {c.thb(overhead)} overhead. "
           "Base = today's prices, promos and prep; Downside = Action with fruit cost up and demand down",
           height=380)
    total = c.load("recommendations").query("area.str.startswith('Total')").iloc[0]
    review = c.load("profit_plan").query("not in_model")["start_date"].max()
    c.chart_note(f"the actions are worth {c.thb_range(total['thb_month_low'], total['thb_month_high'])} a month, "
                 f"but low-season sales do not cover the {c.thb(overhead / ss['month'].nunique())} monthly overhead. "
                 f"Bangkok overhead is the gap that is left; its review starts {review}.")


def home() -> None:
    """Executive summary page."""
    st.title("FruitBlend24: How to grow profit and cut waste")
    st.markdown(intro())
    kpi_row(kpis())

    st.subheader("The 3 things to do now")
    actions()

    st.subheader("What we found")
    for text, page in findings():
        left, right = st.columns([5, 1], vertical_alignment="center")
        left.markdown(text)
        right.page_link(page, label=c.PAGES[page][0])

    st.subheader("What the plan does to Sep-Nov profit")
    scenario_chart()

    st.subheader("How to use this app")
    guide = pd.DataFrame([c.HOME] + list(c.PAGES.values()), columns=["Page", "Question it answers"])
    st.dataframe(guide, hide_index=True)
    st.caption("Use the menu on the left. Pages with data by kitchen or item have filters in the sidebar; "
               "every table has a CSV download.")

    with st.expander("About me"):
        st.markdown(
            f"**{c.AUTHOR}**, 4th-year student, Data Science and Software Innovation, Ubon Ratchathani University.  \n"
            "Applying for the Revenue / Data Analyst Intern role at Atmind Group.  \n"
            "Email: ratthapak.si.66@ubu.ac.th · GitHub: [github.com/belseris](https://github.com/belseris)\n\n"
            "I did the work in Python: pandas for cleaning and the P&L, statsmodels for price sensitivity and the "
            "forecast, Plotly and Streamlit for this app.  \nEvery total is reconciled with asserts (raw to clean, "
            "items and kitchens to company), so the app, the notebooks and the Excel P&L show the same numbers.")


pages = [st.Page(home, title=c.HOME[0], default=True)] + [st.Page(p, title=t) for p, (t, _) in c.PAGES.items()]
st.navigation(pages).run()
c.sidebar()
