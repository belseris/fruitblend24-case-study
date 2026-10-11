"""FruitBlend24 case app: summary (home page) and navigation."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

c.config()

# Page with the detail for each recommendation area.
AREA_PAGE = {"Waste": c.FORECAST, "Pricing": c.DEMAND, "Menu": c.PNL, "Promotions": c.PROMO_PAGE,
             "Tests": c.DEMAND, "Kitchens": c.PNL}
# Plain headline per area; the exact action from recommendations.csv goes in the page it links to.
AREA_HEADLINE = {"Waste": "Prep berry and PassionFruit to demand, not by habit",
                 "Pricing": "Raise the Watermelon and PassionFruit prices",
                 "Menu": "Fix the berry price, then decide if berry stays",
                 "Promotions": "Stop the promo codes that lose money"}
# What a first-time reader should look at first on each page.
LOOK_FIRST = {
    c.DQ: "The reconcile card: raw minus removed equals clean",
    c.DEMAND: "Profit per cup by item, then the price decisions",
    c.PROMO_PAGE: "The decision table: which codes to stop and which to test",
    c.PNL: "The budget-to-actual waterfall, then the four kitchen cards",
    c.FORECAST: "The three forecast tiles, then the prep rule backtest",
    "pages/6_Action_Plan.py": "The four scenario tiles, then who does what, by when",
    c.METHOD: "The glossary, then search the decision log",
}


def totals() -> dict:
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
    """One line on the business, with counts taken from the outputs."""
    kitchens = c.load("kitchen_pnl")["kitchen"].unique()
    apps = c.join(c.load("kitchen_platform_share")["platform"].unique())
    hours = c.load("demand_heatmap")["hour"].nunique()
    return (f"Online smoothie brand: {len(kitchens)} kitchens in Pattaya and Bangkok, sells only on {apps}, "
            f"{hours} hours a day. Data: {c.data_period()}.")


def kpi_row(k: dict) -> None:
    """Five full-year KPIs with the gap to budget and a 12-month sparkline."""
    m = c.load("company_pnl").sort_values("month")
    rev_gap, gp_gap = k["gross_revenue"] - k["budget_revenue"], k["gross_profit"] - k["budget_gp"]
    c.kpi_row([
        dict(label="Revenue", value=c.thb(k["gross_revenue"]),
             delta=f"{c.sthb(rev_gap)} ({c.spct(rev_gap / k['budget_revenue'] * 100)})",
             series=m["gross_revenue"],
             help=f"Price paid after discounts x cups, before platform commission. Budget {c.thb(k['budget_revenue'])}."),
        dict(label="Gross profit (GP-C)", value=c.thb(k["gross_profit"]),
             delta=f"{c.sthb(gp_gap)} ({c.spct(gp_gap / k['budget_gp'] * 100)})",
             series=m["gross_profit"],
             help="GP-C = revenue minus commission, fruit, packaging + labor and waste. "
                  f"Budget {c.thb(k['budget_gp'])}."),
        dict(label="GP %", value=c.pct(k["gp_pct"]), delta=c.pts(k["gp_pct"] - k["budget_gp_pct"]),
             series=m["gp_pct"],
             help=f"Gross profit (GP-C) as % of revenue. Budget {c.pct(k['budget_gp_pct'])}."),
        dict(label="Operating profit", value=c.thb(k["operating_profit"]),
             delta=c.sthb(k["operating_profit"] - k["budget_op"]),
             series=m["operating_profit"],
             help=f"GP-C minus fixed kitchen overhead. Budget = budget GP minus the same overhead "
                  f"({c.sthb(k['budget_op'])})."),
        dict(label="Waste cost", value=c.thb(k["waste_cost"]),
             delta=f"{c.pct(k['waste_cost'] / k['gross_revenue'] * 100)} of revenue", delta_color="off",
             delta_arrow="off", series=m["waste_cost"],
             help="Fruit and packaging of cups made and thrown away. There is no waste budget."),
    ])
    st.caption(f"Full year, {c.data_period()}. Arrows = gap to budget. The small charts show the 12 months, oldest first.")


def gp_vs_budget() -> None:
    """Monthly gross profit vs the flat monthly budget."""
    v = c.load("budget_variance").sort_values("month")
    gaps = c.load("gp_bridge").set_index("step")["thb"]
    big = [s.replace(" margin gap", "") for s in gaps.index
           if s.endswith("margin gap") and gaps[s] < gaps["Revenue effect"]]
    x = [c.month_short(m) for m in v["month"]]
    below = v["gp_var"] < 0
    fig = go.Figure()
    for name, mask, color in [("Below budget", below, c.KEY), ("At or above budget", ~below, c.GREY)]:
        if mask.any():
            fig.add_bar(x=[xx for xx, b in zip(x, mask) if b], y=v.loc[mask, "gross_profit"], name=name,
                        marker_color=color, customdata=[c.thb(y) for y in v.loc[mask, "gross_profit"]],
                        hovertemplate="%{x}<br>Gross profit %{customdata}<extra></extra>")
    fig.add_scatter(x=x, y=v["budget_gp"], name="Budget", mode="lines", line=dict(color=c.DARK, width=2, dash="dot"),
                    customdata=[c.thb(y) for y in v["budget_gp"]],
                    hovertemplate="%{x}<br>Budget %{customdata}<extra></extra>")
    hi = max(v["gross_profit"].max(), v["budget_gp"].max()) * 1.1
    fig.update_xaxes(categoryorder="array", categoryarray=x)
    fig.update_yaxes(title="Gross profit a month (฿)", range=[0, hi], **c.money_ticks(0, hi, 4))
    with c.card(f"Gross profit missed budget in {below.sum()} of {len(v)} months, {c.sthb(v['gp_var'].sum())} "
                "for the year",
                so_what=f"lower sales explain {c.thb(-v['revenue_effect'].sum())} of the gap and lower margins "
                        f"{c.thb(-v['margin_effect'].sum())}. Fixing the margin of "
                        f"{c.join(c.short_item(s) for s in big)} matters more than selling more."):
        c.show(fig, height=320, legend=True)


def actions() -> None:
    """Top 3 costed actions from recommendations.csv, then the one-model total."""
    rec = c.load("recommendations")
    is_total = rec["area"].str.startswith("Total")
    costed = rec[rec["in_total"] & ~is_total]
    top = costed.nlargest(3, "thb_month_low")
    with c.card("3 things to do now"):
        for i, (_, r) in enumerate(top.iterrows(), 1):
            st.markdown(f"**{i}. {AREA_HEADLINE.get(r['area'], c.promo(r['action']))}**  \n"
                        f"{c.thb_range(r['thb_month_low'], r['thb_month_high'])} a month · "
                        f"confidence {r['confidence']}")
            page = AREA_PAGE.get(r["area"], c.DQ)
            st.page_link(page, label=f"Detail: {c.PAGES[page].menu}")
        if is_total.any():
            total = rec[is_total].iloc[0]
            st.caption(f"All {len(costed)} costed actions together: "
                       f"{c.thb_range(total['thb_month_low'], total['thb_month_high'])} a month in one model "
                       "(not a sum of the rows, so nothing is counted twice).")


def kitchens() -> None:
    """Operating profit by kitchen, Bangkok vs Pattaya."""
    kp = c.load("kitchen_pnl").groupby("kitchen")["operating_profit"].sum().sort_values()
    bkk, pattaya = kp.filter(like="BKK").sum(), kp.filter(like="Pattaya").sum()
    fig = go.Figure(go.Bar(y=kp.index, x=kp, orientation="h", marker_color=c.colors(kp.index, kp.index[kp < 0], c.LOSS),
                           text=[c.thb(x) for x in kp], textposition=["inside" if x < 0 else "outside" for x in kp], cliponaxis=False,
                           customdata=[c.thb(x) for x in kp], hovertemplate="%{y}<br>%{customdata}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=c.DARK, width=1))
    width = max(kp.max(), 0) - min(kp.min(), 0)
    lo, hi = min(kp.min(), 0) - width * 0.35, max(kp.max(), 0) + width * 0.45
    fig.update_xaxes(title="Operating profit, full year (฿)", range=[lo, hi], **c.money_ticks(lo, hi, 3))
    with c.card(f"Bangkok loses {c.thb(-bkk)} after overhead; Pattaya makes {c.thb(pattaya)}",
                so_what="the price and waste fixes help every kitchen, but only an overhead review can bring "
                        "Bangkok to break-even."):
        c.show(fig, height=240)


def menu() -> None:
    """Small menu matrix: cups a day vs gross profit per cup."""
    mm = c.load("menu_matrix").query("kitchen == 'All'").set_index("sku")
    dot = {"Star": c.KEY, "Dog": c.LOSS}
    names = [c.short_item(s) for s in mm.index]
    fig = go.Figure(go.Scatter(
        x=mm["cups_per_day"], y=mm["gp_per_cup"], mode="markers+text", text=names,
        textposition=["top center" if k == "Star" else "bottom center" for k in mm["menu_class"]],
        marker=dict(size=12, color=[dot.get(k, c.GREY) for k in mm["menu_class"]]),
        customdata=list(zip(mm["menu_class"], [c.baht(x) for x in mm["gp_per_cup"]])),
        hovertemplate="%{text} (%{customdata[0]})<br>%{x:.0f} cups a day<br>%{customdata[1]} a cup<extra></extra>"))
    if len(mm):
        fig.add_vline(x=mm["pop_line"].iloc[0], line=dict(color=c.GREY, width=1))
        fig.add_hline(y=mm["profit_line"].iloc[0], line=dict(color=c.GREY, width=1))
    fig.update_traces(cliponaxis=False)
    fig.update_xaxes(title="Cups a day", range=[0, mm["cups_per_day"].max() * 1.25] if len(mm) else None)
    if len(mm):
        fig.update_yaxes(range=[min(mm["gp_per_cup"].min(), 0) - 3, mm["gp_per_cup"].max() + 4])
    fig.update_yaxes(title="Gross profit a cup (฿)", tickprefix="฿")
    stars = [c.short_item(s) for s in mm.index[mm["menu_class"] == "Star"]]
    dogs = [c.short_item(s) for s in mm.index[mm["menu_class"] == "Dog"]]
    with c.card(f"{c.join(stars)} are Stars; {c.join(dogs)} are Dogs",
                so_what="protect the Stars; fix the price and waste of the Dogs before selling more of them.",
                how_to_read="Each dot is one item, Mar to Aug 2026. Right of the line = more cups a day than the "
                            "average item. Above the line = more gross profit per cup (after waste) than the "
                            "average cup. **Star** = both, **Dog** = neither."):
        c.show(fig, height=240)


def scorecard(k: dict) -> None:
    """GP vs budget as a progress bar, then the best and worst kitchen and item."""
    kp = c.load("kitchen_pnl").groupby("kitchen")["operating_profit"].sum()
    gaps = c.load("gp_bridge").set_index("step")["thb"]
    items = gaps[gaps.index.str.endswith("margin gap")].rename(lambda s: c.short_item(s.replace(" margin gap", "")))
    reached = k["gross_profit"] / k["budget_gp"]
    with c.card(f"Gross profit reached {c.pct(reached * 100)} of budget",
                so_what="the gap is in a few places, so a few targeted fixes can close most of it."):
        st.progress(min(max(reached, 0.0), 1.0), text=f"{c.thb(k['gross_profit'])} of {c.thb(k['budget_gp'])}")
        if len(kp):
            c.best_worst("kitchen", kp.idxmax(), c.sthb(kp.max()), kp.idxmin(), c.sthb(kp.min()))
        if len(items):
            c.best_worst("item", items.idxmax(), c.sthb(items.max()), items.idxmin(), c.sthb(items.min()))
        st.caption("Kitchens by operating profit for the year; items by gross profit vs the budget margin.")


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
         f"{c.thb(-bkk)} after overhead; the Pattaya kitchens make {c.thb(pattaya)}.", c.PNL),
        (f"**{c.thb(v['gp_var'].sum())} gross profit vs budget.** Berry ({c.thb(gaps[f'{c.BERRY} margin gap'])}) and "
         f"PassionFruit ({c.thb(gaps['PassionFruit margin gap'])}) earn below the {c.pct(budget_margin)} budget "
         f"margin; lower sales cost only {c.thb(-gaps['Revenue effect'])}.", c.PNL),
        (f"**{c.thb(m['waste_cost'].sum())} of fruit thrown away in a year.** Berry is "
         f"{c.pct(ws.loc[c.BERRY, 'waste_cost'] / ws['waste_cost'].sum() * 100, 0)} of it with "
         f"{c.pct(ws.loc[c.BERRY, 'sold'] / ws['sold'].sum() * 100)} of cups, and "
         f"{'loses' if berry_cup < 0 else 'earns'} {c.baht(abs(berry_cup))} a cup after waste.", c.FORECAST),
        (f"**{c.thb(codes['net'].sum() / len(m))} a month from promotions.** All {len(codes)} promo codes "
         f"({c.join(c.promo(x) for x in codes['code'])}) lose money after the discount, extra waste and side effects.",
         c.PROMO_PAGE),
        (f"**{step} on Watermelon and PassionFruit still adds profit.** Customers react less to price "
         f"({pr.loc['Watermelon', 'elasticity']:.2f} and {pr.loc['PassionFruit', 'elasticity']:.2f}) than the level "
         f"where a rise stops paying ({pr.loc['Watermelon', 'breakeven_elasticity']:.2f} and "
         f"{pr.loc['PassionFruit', 'breakeven_elasticity']:.2f}).", c.DEMAND),
    ]


def home() -> None:
    """Summary page."""
    st.title(c.HOME.question)
    st.markdown(intro())
    c.story_bar()

    k = totals()
    kpi_row(k)

    left, right = st.columns([2, 1])
    with left:
        gp_vs_budget()
    with right:
        actions()

    for col, draw in zip(st.columns(3), [kitchens, menu, lambda: scorecard(k)]):
        with col:
            draw()

    with c.card("What we found"):
        for text, page in findings():
            left, right = st.columns([5, 1], vertical_alignment="center")
            left.markdown(text)
            right.page_link(page, label=c.PAGES[page].menu)

    with st.expander("How to use this app"):
        guide = pd.DataFrame([(i.menu, i.question, LOOK_FIRST.get(p, "")) for p, i in c.PAGES.items()],
                             columns=["Page", "Question it answers", "Look at first"])
        st.table(guide, hide_index=True, border="horizontal")
        st.caption("Each card title is the finding. Use 'How to read' and 'Method' on a card for help; "
                   "the sidebar has the Excel P&L and the GitHub repo.")

    with st.expander("About me"):
        st.markdown(
            f"**{c.AUTHOR}**, 4th-year student, Data Science and Software Innovation, Ubon Ratchathani University.  \n"
            "Applying for the Revenue / Data Analyst Intern role at Atmind Group.  \n"
            "Email: ratthapak.si.66@ubu.ac.th · GitHub: [github.com/belseris](https://github.com/belseris)\n\n"
            "I did the work in Python: pandas for cleaning and the P&L, statsmodels for price sensitivity and the "
            "forecast, Plotly and Streamlit for this app.  \nEvery number is reconciled with asserts (raw to clean, "
            "items and kitchens to company), and the app, the notebooks and the Excel P&L read the same outputs.")

    c.next_page(c.DQ)


pages = [st.Page(home, title=c.HOME.menu, default=True)] + [st.Page(p, title=i.menu) for p, i in c.PAGES.items()]
st.navigation(pages).run()
c.sidebar()
