"""P&L and budget: statement, GP definitions, budget bridge, kitchens after overhead, menu matrix, decisions."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

kitchen = c.pick("Kitchen", c.KITCHENS, "pl_kitchen")
item = c.pick("Item (P&L table)", c.ITEMS, "pl_item")

company = c.load("company_pnl")
v = c.load("budget_variance")
bridge = c.load("gp_bridge")
kp = c.load("kitchen_pnl")
gaps = bridge.set_index("step")["thb"]
budget_margin = v["budget_margin_pct"].iloc[0]
fy = company.sum(numeric_only=True)
kfy = kp.groupby("kitchen")[["gross_revenue", "gross_profit", "overhead", "operating_profit"]].sum()
bkk, pattaya = kfy["operating_profit"].filter(like="BKK").sum(), kfy["operating_profit"].filter(like="Pattaya").sum()
big = [s for s in bridge["step"] if s.endswith("margin gap") and gaps[s] < gaps["Revenue effect"]]

c.page_header(
    c.PAGES["pages/4_PnL_and_Budget.py"][1],
    f"**Gross profit was {c.thb(fy['gross_profit'])} vs a {c.thb(v['budget_gp'].sum())} budget "
    f"({c.sthb(v['gp_var'].sum())}).** Lower sales explain {c.thb(v['revenue_effect'].sum())}; lower margins "
    f"explain {c.thb(v['margin_effect'].sum())}, mostly " + " and ".join(
        f"{s.replace(' margin gap', '').replace(c.BERRY, 'berry')} ({c.thb(gaps[s])})" for s in big)
    + f". After {c.thb(fy['overhead'])} kitchen overhead the company lost {c.thb(-fy['operating_profit'])}: "
      f"Bangkok {c.thb(bkk)}, Pattaya {c.sthb(pattaya)}.")

# ---- statement ----
LINES = [("Cups sold", "cups"), ("Gross revenue", "gross_revenue"), ("Commission", "commission"),
         ("Net revenue", "net_revenue"), ("Fruit", "fruit"), ("Packaging + labor", "pack_labor"),
         ("Contribution margin (GP-B)", "cm"), ("Waste", "waste_cost"), ("Gross profit (GP-C)", "gross_profit"),
         ("Kitchen overhead", "overhead"), ("Operating profit", "operating_profit")]
if item != "All":
    src = c.load("item_kitchen_pnl").query("sku == @item")
    src = src if kitchen == "All" else src[src["kitchen"] == kitchen]
    lines = LINES[:-2]  # overhead is never split to items
elif kitchen != "All":
    src, lines = kp[kp["kitchen"] == kitchen], LINES
else:
    src, lines = company, LINES
scope = " / ".join(x for x in [kitchen, item] if x != "All") or "company"
st.subheader(f"What does the P&L look like? ({scope})")
stmt = src.groupby("month")[[col for _, col in lines]].sum().T
stmt.columns = [pd.Timestamp(f"{m}-01").strftime("%b %y") for m in stmt.columns]
stmt.index = [label for label, _ in lines]
stmt["Full year"] = stmt.sum(axis=1)
ratio = [("GP-C % of revenue", "Gross profit (GP-C)")] + ([("Operating margin %", "Operating profit")]
                                                           if item == "All" else [])
for label, line in ratio:
    stmt.loc[label] = stmt.loc[line] / stmt.loc["Gross revenue"] * 100
money = [label for label, _ in lines if label != "Cups sold"]
pct_rows = [label for label, _ in ratio]
sty = (stmt.style.format(c.thb, subset=pd.IndexSlice[money, :])
       .format("{:,.0f}", subset=pd.IndexSlice[["Cups sold"], :])
       .format(c.pct, subset=pd.IndexSlice[pct_rows, :])
       .apply(lambda r: [f"background-color: {c.HILITE}" if r.name in ("Gross profit (GP-C)", "Operating profit")
                         else "" for _ in r], axis=1))
st.dataframe(sty, height=c.fit_height(len(stmt)))
st.caption("Costs are shown as positive amounts and taken away. "
           + ("Overhead is fixed per kitchen and never split to items, so an item stops at GP-C."
              if item != "All" else "Overhead is fixed per kitchen and never split to items."))
c.download(stmt.reset_index(names="line"), "pnl_statement")

# ---- GP definitions ----
st.subheader("Which gross profit definition fits the budget?")
defs = pd.DataFrame({
    "Definition": ["GP-A", "GP-B", "GP-C (used)"],
    "Takes away": ["fruit, packaging + labor", "GP-A items + platform commission", "GP-B items + waste"],
    "Full year": [fy["gp_a"], fy["gp_b"], fy["gross_profit"]]})
defs["% of revenue"] = defs["Full year"] / fy["gross_revenue"] * 100
defs["vs budget %"] = (defs["% of revenue"] - budget_margin).map(lambda x: f"{x:+.1f} pts")
c.table(defs, money=["Full year"], pcts=["% of revenue"], highlight=defs["Definition"].str.contains("used"))
a, b, gc = defs["% of revenue"]
st.markdown(f"Why GP-C: the budget margin is {c.pct(budget_margin)}. GP-A ({c.pct(a)}) is far above it, so the budget "
            f"is after commission. GP-B ({c.pct(b)}) and GP-C ({c.pct(gc)}) are both close; waste is a real cost "
            "and the budget note does not leave it out, so we use the lower and safer one, GP-C.")

# ---- bridge ----
st.subheader("From budget GP to actual GP")
steps = bridge["step"].str.replace(" margin gap", "").str.replace(c.BERRY, "Berry").tolist()
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
key = [s.replace(" margin gap", "").replace(c.BERRY, "Berry") for s in big]
bar_color = [c.DARK if k == "total" else (c.LOSS if s in key else c.GREY) for k, s in zip(bridge["kind"], steps)]
label = [c.thb(x) if k == "total" else c.sthb(x) for k, x in zip(bridge["kind"], bridge["thb"])]
fig = go.Figure(go.Bar(x=steps, y=[abs(e - s) for s, e in zip(start, end)], base=[min(s, e) for s, e in zip(start, end)],
                       marker_color=bar_color, text=label, textposition="outside", customdata=label,
                       hovertemplate="%{x}<br>%{customdata}<extra></extra>"))
for i in range(len(steps) - 1):
    fig.add_shape(type="line", x0=i + 0.4, x1=i + 0.6, y0=end[i], y1=end[i], line=dict(color=c.GREY, width=1))
inner = [y for y in start + end if y != 0]
pad = (max(inner) - min(inner)) * 0.25
lo, hi = min(inner) - pad, max(inner) + pad
fig.update_yaxes(title="Gross profit, full year (฿)", range=[lo, hi], **c.money_ticks(lo, hi))
c.show(fig, " and ".join(f"{k} ({c.thb(gaps[s])})" for k, s in zip(key, big))
       + f" cost more GP than the sales shortfall ({c.thb(gaps['Revenue effect'])})",
       f"Budget GP to actual GP, full year. Item bar = item GP - item revenue x {c.pct(budget_margin)} budget margin",
       height=460)
c.how_to_read(f"Start on the left at the budget GP. Each bar in the middle moves GP up or down; the label shows by "
              f"how much. **Revenue effect** = sales below budget, valued at the budget margin "
              f"({c.pct(budget_margin)}). Each **item bar** = item GP - item revenue x the budget margin: below 0 "
              f"means the item earns a lower margin than the budget. The last bar is actual GP. The axis starts at "
              f"{c.thb(lo)}, not 0, so the steps are easy to see.")
c.chart_note("selling more would not close the gap. The margin of " + " and ".join(key)
             + " must be fixed (price, fruit cost, waste); the other items are above the budget margin.")
with st.expander("Month by month vs budget"):
    vt = v[["month", "gross_revenue", "budget_revenue", "gross_profit", "budget_gp", "gp_var", "revenue_effect",
            "margin_effect", "gp_pct"]].rename(columns={"gp_var": "GP vs budget", "gp_pct": "GP %"})
    c.table(vt, money=["gross_revenue", "budget_revenue", "gross_profit", "budget_gp", "GP vs budget",
                       "revenue_effect", "margin_effect"], pcts=["GP %"], highlight=vt["GP vs budget"].lt(0))
    st.caption(f"GP misses the budget in {(v['gp_var'] < 0).sum()} of {len(v)} months. GP vs budget = revenue effect "
               "+ margin effect in every month (checked in notebook 04).")
    c.download(v, "budget_variance")

# ---- kitchens ----
st.subheader("Which kitchens make money after overhead?")
order = kfy.sort_values("operating_profit")
fig = go.Figure(go.Bar(y=order.index, x=order["operating_profit"], orientation="h",
                       marker_color=c.colors(order.index, order.index[order["operating_profit"] < 0], c.LOSS),
                       text=[c.thb(x) for x in order["operating_profit"]], textposition="outside",
                       customdata=[c.thb(x) for x in order["operating_profit"]],
                       hovertemplate="%{y}<br>%{customdata}<extra></extra>"))
fig.add_vline(x=0, line=dict(color=c.DARK, width=1))
lo, hi = order["operating_profit"].min() * 1.35, max(order["operating_profit"].max() * 1.35, 0)
fig.update_xaxes(title="Operating profit, full year (฿)", range=[lo, hi], **c.money_ticks(lo, hi))
c.show(fig, f"Bangkok kitchens lose {c.thb(-bkk)} after overhead; Pattaya kitchens make {c.thb(pattaya)}",
       f"Operating profit = GP-C - fixed kitchen overhead, {c.data_period()}", height=340)
below = kp.pivot(index="kitchen", columns="month", values="operating_profit").lt(0).sum(axis=1)
worst = order.index[0]
c.chart_note(f"{worst} is below 0 in {below[worst]} of {kp['month'].nunique()} months. Price and waste fixes help "
             "every kitchen, but only an overhead review (rent, staff hours) can bring Bangkok to break-even.")
ktbl = kfy.assign(op_margin=kfy["operating_profit"] / kfy["gross_revenue"] * 100,
                  months_below_0=below).reindex(order.index).reset_index()
c.table(ktbl.rename(columns={"op_margin": "operating margin", "months_below_0": "months below 0"}),
        money=["gross_revenue", "gross_profit", "overhead", "operating_profit"], pcts=["operating margin"],
        count=["months below 0"], highlight=ktbl["operating_profit"].lt(0))
c.download(ktbl, "kitchen_operating_profit")

# ---- menu matrix ----
st.subheader("Which items are Stars and which are Dogs?")
mm = c.load("menu_matrix").query("kitchen == @kitchen").set_index("sku").reindex(c.ITEMS)
pop, prof = mm["pop_line"].iloc[0], mm["profit_line"].iloc[0]
dot = {"Star": c.KEY, "Dog": c.LOSS}
fig = go.Figure(go.Scatter(
    x=mm["cups_per_day"], y=mm["gp_per_cup"], mode="markers+text", text=mm.index, textposition="top center",
    marker=dict(size=14, color=[dot.get(k, c.DARK) for k in mm["menu_class"]], line=dict(color="white", width=2)),
    customdata=list(zip(mm["menu_class"], [c.baht(x) for x in mm["gp_per_cup"]])),
    hovertemplate="%{text} (%{customdata[0]})<br>%{x:.0f} cups a day<br>%{customdata[1]} GP a cup<extra></extra>"))
fig.add_vline(x=pop, line=dict(color=c.GREY, width=1))
fig.add_hline(y=prof, line=dict(color=c.GREY, width=1))
x_hi = mm["cups_per_day"].max() * 1.15
y_lo, y_hi = min(mm["gp_per_cup"].min(), 0) - 3, mm["gp_per_cup"].max() + 3
for name, x, y, ax in [("Star", x_hi, y_hi, "right"), ("Plowhorse", x_hi, y_lo, "right"),
                       ("Puzzle", 0, y_hi, "left"), ("Dog", 0, y_lo, "left")]:
    fig.add_annotation(x=x, y=y, text=name.upper(), showarrow=False, xanchor=ax,
                       yanchor="top" if y == y_hi else "bottom", font=dict(color=c.DARK, size=12))
fig.update_xaxes(title="Cups sold a day", range=[0, x_hi])
fig.update_yaxes(title="GP-C per cup after waste (฿)", range=[y_lo, y_hi], tickprefix="฿")
stars, dogs = mm.index[mm["menu_class"] == "Star"].tolist(), mm.index[mm["menu_class"] == "Dog"].tolist()
c.show(fig, f"{' and '.join(stars)} are Stars; {' and '.join(dogs)} are Dogs "
            f"(berry {c.baht(mm.loc[c.BERRY, 'gp_per_cup'])} a cup after waste)",
       f"{'All kitchens' if kitchen == 'All' else kitchen}, {c.load('sales_mix')['period'].iloc[0]}: cups a day vs GP "
       "per cup. Lines = average item (popularity) and average cup (profit)", height=480)
c.how_to_read("Each dot is a menu item in the months when all items are on sale. Right of the vertical line = sells "
              "more cups a day than the average item. Above the horizontal line = earns more GP per cup after waste "
              "than the average cup. **Star**: popular and profitable, protect it. **Plowhorse**: popular, low "
              "profit, fix price or cost. **Puzzle**: profitable, not popular, sell it more. **Dog**: neither, fix "
              "it or take it off the menu.")
c.chart_note(f"PassionFruit is a Dog but still earns {c.baht(mm.loc['PassionFruit', 'gp_per_cup'])} a cup, so fix "
             f"its price; berry loses money on every cup, so it gets a price rise and a stop rule.")

# ---- decisions ----
st.subheader("What do we do per item and kitchen?")
pf = c.load("portfolio_decision")
ptbl = pf[["level", "name", "problem", "action", "thb_month_low", "thb_month_high", "in_plan", "confidence"]].rename(
    columns={"thb_month_low": "a month (low)", "thb_month_high": "a month (high)", "in_plan": "in plan"})
c.table(ptbl, money=["a month (low)", "a month (high)"], highlight=ptbl["in plan"])
st.caption("Values on the Mar-Aug base, before the Sep-Nov model. Kitchen rows are shares of the item rows, so only "
           "rows in the plan add up. The Sep-Nov value of the plan, from one model, is on the Forecast and "
           "Inventory page.")
c.download(pf, "portfolio_decision")

c.method_box(
    "- **P&L:** gross revenue (after discount) - commission = net revenue; - fruit - packaging + labor = CM (GP-B); "
    "- waste = gross profit (GP-C); - fixed kitchen overhead = operating profit. Month = calendar month of the order.\n"
    "- **Items** are judged on GP-C, **kitchens** on operating profit. Overhead is never split to items.\n"
    "- **Budget variance** = revenue effect ((actual - budget revenue) x budget GP %) + margin effect (actual "
    "revenue x (actual - budget GP %)). The two add up exactly, and the item gaps add up to the margin effect. "
    "There is no item or kitchen budget, so all use the company budget margin.\n"
    "- **Menu matrix:** popularity line = plain mean of the items' cups a day; profit line = cup-weighted GP per cup.\n"
    "- The Excel P&L uses live formulas and is checked in Python against these numbers.")
