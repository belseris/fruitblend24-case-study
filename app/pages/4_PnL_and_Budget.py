"""Profit vs budget: statement, GP definitions, budget bridge, kitchens after overhead, menu matrix, decisions."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

company = c.load("company_pnl").sort_values("month")
v = c.load("budget_variance").sort_values("month")
bridge = c.load("gp_bridge")
kp = c.load("kitchen_pnl")
gaps = bridge.set_index("step")["thb"]
budget_margin = v["budget_margin_pct"].iloc[0]
fy = company.sum(numeric_only=True)
kfy = kp.groupby("kitchen")[["gross_revenue", "gross_profit", "overhead", "operating_profit"]].sum()
bkk, pattaya = kfy["operating_profit"].filter(like="BKK").sum(), kfy["operating_profit"].filter(like="Pattaya").sum()
big = [s for s in bridge["step"] if s.endswith("margin gap") and gaps[s] < gaps["Revenue effect"]]
big_names = [c.short_item(s.replace(" margin gap", "")) for s in big]
n_months = len(company)

c.page_header(
    c.PNL,
    f"**{c.thb(v['gp_var'].sum())} gross profit vs budget: {c.thb(-v['revenue_effect'].sum())} from lower sales, "
    f"{c.thb(-v['margin_effect'].sum())} from lower margins, mostly {c.join(big_names)}.** After overhead the company "
    f"lost {c.thb(-fy['operating_profit'])}; Bangkok lost {c.thb(-bkk)}.")

c.kpi_row([
    dict(label="Gross profit vs budget", value=c.sthb(v["gp_var"].sum()), series=v["gp_var"],
         delta=c.spct(v["gp_var"].sum() / v["budget_gp"].sum() * 100), delta_description="of budget",
         help="Actual gross profit (GP-C) minus budget gross profit, full year. Chart = by month."),
    dict(label="Revenue effect", value=c.sthb(v["revenue_effect"].sum()), series=v["revenue_effect"],
         help=f"Part of the gap from lower sales: revenue gap x budget margin ({c.pct(budget_margin)})."),
    dict(label="Margin effect", value=c.sthb(v["margin_effect"].sum()), series=v["margin_effect"],
         help="Part of the gap from a lower margin: actual revenue x (actual GP % - budget GP %)."),
    dict(label="Operating profit", value=c.thb(fy["operating_profit"]), series=company["operating_profit"],
         delta=f"{(company['operating_profit'] < 0).sum()} of {n_months} months below 0", delta_color="off",
         delta_arrow="off", help="Gross profit (GP-C) minus fixed kitchen overhead."),
])

# ---- statement ----
LINES = [("Cups sold", "cups"), ("Gross revenue", "gross_revenue"), ("Commission", "commission"),
         ("Net revenue", "net_revenue"), ("Fruit", "fruit"), ("Packaging + labor", "pack_labor"),
         ("Contribution margin (GP-B)", "cm"), ("Waste", "waste_cost"), ("Gross profit (GP-C)", "gross_profit"),
         ("Kitchen overhead", "overhead"), ("Operating profit", "operating_profit")]


def statement(src: pd.DataFrame, lines: list, by_quarter: bool) -> pd.DataFrame:
    """P&L lines as rows; months (or 3-month blocks) and the full year as columns."""
    stmt = src.groupby("month")[[col for _, col in lines]].sum().T.sort_index(axis=1)
    if by_quarter:
        months = list(stmt.columns)
        blocks = [months[i:i + 3] for i in range(0, len(months), 3)]
        stmt = pd.DataFrame({f"{c.month_short(b[0])} to {c.month_short(b[-1])}": stmt[b].sum(axis=1) for b in blocks})
    else:
        stmt.columns = [c.month_short(m) for m in stmt.columns]
    stmt.index = [name for name, _ in lines]
    stmt["Full year"] = stmt.sum(axis=1)
    stmt.loc["GP-C % of revenue"] = stmt.loc["Gross profit (GP-C)"] / stmt.loc["Gross revenue"] * 100
    if "Operating profit" in stmt.index:
        stmt.loc["Operating margin %"] = stmt.loc["Operating profit"] / stmt.loc["Gross revenue"] * 100
    return stmt


def draw_statement(stmt: pd.DataFrame) -> None:
    """Statement with ฿, cups and % rows formatted, key lines highlighted."""
    pct_rows = [r for r in stmt.index if "%" in r]
    money = [r for r in stmt.index if r not in pct_rows + ["Cups sold"]]
    sty = (stmt.style.format(c.thb, subset=pd.IndexSlice[money, :])
           .format("{:,.0f}", subset=pd.IndexSlice[["Cups sold"], :])
           .format(c.pct, subset=pd.IndexSlice[pct_rows, :])
           .apply(lambda r: [f"background-color: {c.HILITE}" if r.name in ("Gross profit (GP-C)", "Operating profit")
                             else "" for _ in r], axis=1))
    st.dataframe(sty, height=c.fit_height(len(stmt)))


below_company = (company["operating_profit"] < 0).sum()
with c.card(f"The company loses money after overhead in {below_company} of {n_months} months",
            so_what="costs are shown as positive amounts and taken away. Overhead is fixed per kitchen and never "
                    "split to items, so an item stops at gross profit (GP-C).",
            method="Gross revenue (after discount) - commission = net revenue; - fruit - packaging + labor = "
                   "contribution margin (GP-B); - waste = gross profit (GP-C); - fixed kitchen overhead = operating "
                   "profit. Month = calendar month of the order. The Excel P&L uses live formulas and is checked in "
                   "Python against these numbers."):
    kitchen = c.choose("Kitchen", c.KITCHENS, key="pl_kitchen")
    item = c.choose("Item", c.ITEMS, key="pl_item")
    if item != "All":
        src = c.load("item_kitchen_pnl").query("sku == @item")
        src = src if kitchen == "All" else src[src["kitchen"] == kitchen]
        lines = LINES[:-2]  # overhead is never split to items
    elif kitchen != "All":
        src, lines = kp[kp["kitchen"] == kitchen], LINES
    else:
        src, lines = company, LINES
    scope = " / ".join(x for x in [kitchen, item] if x != "All") or "Company"
    st.caption(f"{scope}, by 3-month block. The month-by-month statement is under 'Full table'.")
    draw_statement(statement(src, lines, by_quarter=True))
    with st.expander("Full table"):
        full = statement(src, lines, by_quarter=False)
        draw_statement(full)
        c.download(full.reset_index(names="Line"), "pnl_statement")

# ---- GP definitions and bridge ----
left, right = st.columns([1, 2])
with left:
    defs = pd.DataFrame({
        "Definition": ["GP-A", "GP-B", "GP-C (used)"],
        "Takes away": ["Fruit, packaging + labor", "GP-A items + commission", "GP-B items + waste"],
        "Full year": [fy["gp_a"], fy["gp_b"], fy["gross_profit"]]})
    defs["% of revenue"] = defs["Full year"] / fy["gross_revenue"] * 100
    defs["Gap to budget"] = (defs["% of revenue"] - budget_margin).map(c.pts)
    a, b, gc = defs["% of revenue"]
    with c.card(f"GP-C fits the {c.pct(budget_margin)} budget margin and counts waste",
                so_what=f"GP-A ({c.pct(a)}) is far above the budget, so the budget is after commission. GP-B "
                        f"({c.pct(b)}) and GP-C ({c.pct(gc)}) are both close; waste is a real cost and the budget "
                        "note does not leave it out, so we use the lower and safer one, GP-C."):
        c.table(defs, cols=["Definition", "% of revenue", "Gap to budget"], money=["Full year"], pcts=["% of revenue"],
                highlight=defs["Definition"].str.contains("used"))

with right:
    steps = [c.short_item(s.replace(" margin gap", "")).capitalize() if c.BERRY in s else s.replace(" margin gap", "")
             for s in bridge["step"]]
    start, end, run = [], [], 0.0
    for kind, x in zip(bridge["kind"], bridge["thb"]):
        if kind == "total":
            start.append(0.0)
            end.append(x)
            run = x
        else:
            start.append(run)
            run += x
            end.append(run)
    key = [steps[list(bridge["step"]).index(s)] for s in big]
    bar_color = [c.DARK if k == "total" else (c.LOSS if s in key else c.GREY) for k, s in zip(bridge["kind"], steps)]
    text = [c.thb(x) if k == "total" else c.sthb(x) for k, x in zip(bridge["kind"], bridge["thb"])]
    fig = go.Figure(go.Bar(x=steps, y=[abs(e - s) for s, e in zip(start, end)],
                           base=[min(s, e) for s, e in zip(start, end)], marker_color=bar_color, text=text,
                           textposition="outside", cliponaxis=False, customdata=text,
                           hovertemplate="%{x}<br>%{customdata}<extra></extra>"))
    for i in range(len(steps) - 1):
        fig.add_shape(type="line", x0=i + 0.4, x1=i + 0.6, y0=end[i], y1=end[i], line=dict(color=c.GREY, width=1))
    inner = [y for y in start + end if y != 0]
    pad = (max(inner) - min(inner)) * 0.25
    lo, hi = min(inner) - pad, max(inner) + pad
    fig.update_yaxes(title="Gross profit, full year (฿)", range=[lo, hi], **c.money_ticks(lo, hi))
    with c.card(f"{c.join(f'{k} ({c.thb(gaps[s])})' for k, s in zip(key, big))} cost more than the sales shortfall "
                f"({c.thb(gaps['Revenue effect'])})",
                so_what=f"selling more would not close the gap. The margin of {c.join(big_names)} must be fixed "
                        "(price, fruit cost, waste); the other items are above the budget margin.",
                how_to_read=f"Start on the left at the budget gross profit. Each bar in the middle moves it up or "
                            f"down; the label shows by how much. **Revenue effect** = sales below budget, valued at "
                            f"the budget margin ({c.pct(budget_margin)}). Each **item bar** = item gross profit - item "
                            f"revenue x the budget margin: below 0 means the item earns a lower margin than the "
                            f"budget. The last bar is actual gross profit. The axis starts at {c.thb(lo)}, not 0, so "
                            "the steps are easy to see.",
                method="Variance = revenue effect ((actual - budget revenue) x budget GP %) + margin effect (actual "
                       "revenue x (actual - budget GP %)). The two add up exactly, and the item gaps add up to the "
                       "margin effect. There is no item or kitchen budget, so all use the company budget margin."):
        c.show(fig, height=380)
        with st.expander("Month by month vs budget"):
            vt = v[["month", "gross_revenue", "budget_revenue", "gross_profit", "budget_gp", "gp_var",
                    "revenue_effect", "margin_effect", "gp_pct"]]
            c.table(vt, money=["gross_revenue", "budget_revenue", "gross_profit", "budget_gp", "gp_var",
                               "revenue_effect", "margin_effect"], pcts=["gp_pct"], highlight=vt["gp_var"].lt(0),
                    name="budget_variance", raw=v)
            st.caption(f"Gross profit misses the budget in {(v['gp_var'] < 0).sum()} of {len(v)} months. GP vs budget "
                       "= revenue effect + margin effect in every month (checked in notebook 04).")

# ---- kitchens: small multiples ----
below = kp.pivot(index="kitchen", columns="month", values="operating_profit").lt(0).sum(axis=1)
for col, k in zip(st.columns(len(c.KITCHENS)), c.KITCHENS):
    series = kp[kp["kitchen"] == k].sort_values("month")
    if series.empty:
        continue
    fig = c.area_around_zero([c.month_short(m) for m in series["month"]], series["operating_profit"].tolist())
    fig.update_yaxes(title="Operating profit (฿)", **c.money_ticks(series["operating_profit"].min(),
                                                                 series["operating_profit"].max(), 3))
    with col, c.card(f"{k}: {c.sthb(series['operating_profit'].sum())} a year"):
        c.show(fig, height=180)
        st.caption(f"{below.get(k, 0)} of {series['month'].nunique()} months below 0")
st.caption("Monthly operating profit after overhead; green = above 0, red = below 0. So what: Bangkok is below 0 in "
           "most months, Pattaya only in the rainy months.")

left, right = st.columns(2)
with left:
    order = kfy.sort_values("operating_profit")
    ktbl = order.assign(op_margin=order["operating_profit"] / order["gross_revenue"] * 100,
                        months_below_0=below.reindex(order.index)).reset_index()
    worst = order.index[0] if len(order) else ""
    with c.card(f"Bangkok kitchens lose {c.thb(-bkk)} after overhead; Pattaya kitchens make {c.thb(pattaya)}",
                so_what=f"{worst} is below 0 in {below.get(worst, 0)} of {n_months} months. Price and waste fixes help "
                        "every kitchen, but only an overhead review (rent, staff hours) can bring Bangkok to "
                        "break-even."):
        c.table(ktbl.rename(columns={"op_margin": "Operating margin", "months_below_0": "Months below 0"}),
                cols=["kitchen", "gross_profit", "overhead", "operating_profit"],
                money=["gross_revenue", "gross_profit", "overhead", "operating_profit"], pcts=["Operating margin"],
                count=["Months below 0"], highlight=ktbl["operating_profit"].lt(0), name="kitchen_operating_profit")

with right:
    mm_all = c.load("menu_matrix")
    company_mm = mm_all[mm_all["kitchen"] == "All"]
    with c.card(f"{c.join(c.short_item(s) for s in company_mm.loc[company_mm['menu_class'] == 'Star', 'sku'])} are "
                f"Stars; {c.join(c.short_item(s) for s in company_mm.loc[company_mm['menu_class'] == 'Dog', 'sku'])} "
                "are Dogs in the menu matrix",
                how_to_read="Each dot is a menu item in the months when all items are on sale. Right of the vertical "
                            "line = sells more cups a day than the average item. Above the horizontal line = earns "
                            "more gross profit per cup after waste than the average cup. **Star**: popular and "
                            "profitable, protect it. **Plowhorse**: popular, low profit, fix price or cost. "
                            "**Puzzle**: profitable, not popular, sell it more. **Dog**: neither, fix it or take it "
                            "off the menu.",
                method="Popularity line = plain mean of the items' cups a day; profit line = cup-weighted gross "
                       "profit per cup."):
        mk = c.choose("Kitchen", c.KITCHENS, key="pl_matrix_kitchen")
        mm = mm_all.query("kitchen == @mk").set_index("sku").reindex(c.ITEMS).dropna(subset=["cups_per_day"])
        stars = [c.short_item(s) for s in mm.index[mm["menu_class"] == "Star"]]
        dogs = [c.short_item(s) for s in mm.index[mm["menu_class"] == "Dog"]]
        st.markdown(f"{'All kitchens' if mk == 'All' else mk}: Stars {c.join(stars)}; Dogs {c.join(dogs)}.")
        dot = {"Star": c.KEY, "Dog": c.LOSS}
        fig = go.Figure(go.Scatter(
            x=mm["cups_per_day"], y=mm["gp_per_cup"], mode="markers+text", text=[c.short_item(s) for s in mm.index],
            textposition=["top center" if k == "Star" else "bottom center" for k in mm["menu_class"]],
            cliponaxis=False,
            marker=dict(size=13, color=[dot.get(k, c.DARK) for k in mm["menu_class"]], line=dict(color="white", width=2)),
            customdata=list(zip(mm["menu_class"], [c.baht(x) for x in mm["gp_per_cup"]])),
            hovertemplate="%{text} (%{customdata[0]})<br>%{x:.0f} cups a day<br>%{customdata[1]} a cup<extra></extra>"))
        if len(mm):
            pop, prof = mm["pop_line"].iloc[0], mm["profit_line"].iloc[0]
            fig.add_vline(x=pop, line=dict(color=c.GREY, width=1))
            fig.add_hline(y=prof, line=dict(color=c.GREY, width=1))
            x_hi = mm["cups_per_day"].max() * 1.2
            y_lo, y_hi = min(mm["gp_per_cup"].min(), 0) - 3, mm["gp_per_cup"].max() + 4
            for name, x, y, ax in [("Star", x_hi, y_hi, "right"), ("Plowhorse", x_hi, y_lo, "right"),
                                   ("Puzzle", 0, y_hi, "left"), ("Dog", 0, y_lo, "left")]:
                fig.add_annotation(x=x, y=y, text=name.upper(), showarrow=False, xanchor=ax,
                                   yanchor="top" if y == y_hi else "bottom", font=dict(color=c.DARK, size=11))
            fig.update_xaxes(range=[0, x_hi])
            fig.update_yaxes(range=[y_lo, y_hi])
        fig.update_xaxes(title="Cups sold a day")
        fig.update_yaxes(title="Gross profit per cup after waste (฿)", tickprefix="฿")
        c.show(fig, height=330)
        if c.BERRY in mm.index and "PassionFruit" in mm.index:
            st.caption(f"So what: PassionFruit still earns {c.baht(mm.loc['PassionFruit', 'gp_per_cup'])} a cup, so "
                       f"fix its price; berry earns {c.baht(mm.loc[c.BERRY, 'gp_per_cup'])} a cup after waste, so it "
                       "gets a price rise and a stop rule.")

# ---- decisions ----
pf = c.load("portfolio_decision")
ptbl = pf.assign(level=pf["level"].map(c.title_case), action=pf["action"].map(c.promo),
                 problem=pf["problem"].map(c.promo), name=pf["name"].map(c.promo))
with c.card(f"{pf['in_plan'].sum()} item and promo rows make the plan; kitchen rows are shares of them",
            so_what="values are on the Mar-Aug base, before the Sep-Nov model. Only rows in the plan add up. The "
                    "Sep-Nov value of the plan, from one model, is on the Action plan page."):
    c.table(ptbl, cols=["level", "name", "action", "thb_month_low", "thb_month_high", "in_plan"],
            money=["thb_month_low", "thb_month_high"], highlight=pf["in_plan"], name="portfolio_decision", raw=pf,
            static=True)

c.next_page(c.FORECAST)
