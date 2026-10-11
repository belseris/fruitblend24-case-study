"""Demand and pricing: sales by month and hour, what one cup earns, price sensitivity and price decisions."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

hm = c.load("demand_heatmap")
mix = c.load("sales_mix").set_index("sku").reindex(c.ITEMS)
ue_all = c.load("unit_economics")
pr = c.load("price_recommendation")
el = c.load("elasticity")
trend = c.load("monthly_item_trend")
period = mix["period"].iloc[0]

# Busiest hour per city: mean of the kitchens' hourly profiles.
by_kitchen = hm[hm["kitchen"] != "All"].groupby(["kitchen", "hour"])["avg_cups_per_hour"].mean().unstack()
city = by_kitchen.groupby(lambda k: "Pattaya" if k.startswith("Pattaya") else "Bangkok").mean()
peak = city.idxmax(axis=1)
top = mix["share_cups_pct"].idxmax()
item_rows = ue_all[ue_all["level"] == "item"].set_index("sku")
berry = item_rows.loc[c.BERRY]
prs = pr[pr["sku"].isin(c.ITEMS)].set_index("sku")
raise_ = prs[prs["decision"] == "raise"]

c.page_header(
    c.DEMAND,
    f"**{c.pct(mix.loc[top, 'share_cups_pct'], 0)} of cups are {top}; Pattaya is busiest at {peak['Pattaya']}:00 "
    f"and Bangkok at {peak['Bangkok']}:00.** Raise "
    + c.join(f"{s} to {c.baht(r['new_price'], 0)}" for s, r in raise_.iterrows())
    + f"; berry {'loses' if berry['cm_after_waste_per_cup'] < 0 else 'earns'} "
      f"{c.baht(abs(berry['cm_after_waste_per_cup']))} a cup after waste.")

c.kpi_row([
    dict(label="Top item share", value=c.pct(mix.loc[top, "share_cups_pct"], 0), delta=top, delta_color="off",
         delta_arrow="off", series=mix["share_cups_pct"].sort_values(ascending=False),
         help=f"Share of cups sold, {period} (all items on sale). Chart = the 5 items, largest first."),
    dict(label="Pattaya peak hour", value=f"{peak['Pattaya']}:00", series=city.loc["Pattaya"],
         help="Hour with the most cups, mean of the 2 Pattaya kitchens. Chart = cups an hour, 0:00 to 23:00."),
    dict(label="Bangkok peak hour", value=f"{peak['Bangkok']}:00", series=city.loc["Bangkok"],
         help="Hour with the most cups, mean of the 2 Bangkok kitchens. Chart = cups an hour, 0:00 to 23:00."),
    dict(label="Berry profit a cup", value=c.baht(berry["cm_after_waste_per_cup"]),
         delta=f"after waste ({c.baht(berry['cm_per_cup'])} before)", delta_color="off", delta_arrow="off",
         help=f"Price paid minus commission, fruit, packaging + labor and waste, per cup, {period}."),
])

# ---- sales by month: one small card per item ----
trend["m"] = trend["month"].str[:7]
old = trend[trend["sku"] != c.BERRY].groupby("m")["cups_per_day"].sum()
cols = st.columns(len(c.ITEMS))
for col, item in zip(cols, c.ITEMS):
    t = trend[trend["sku"] == item].sort_values("m")
    if t.empty:
        continue
    change = (t["cups_per_day"].iloc[-1] / t["cups_per_day"].iloc[0] - 1) * 100
    fig = go.Figure(go.Scatter(
        x=[c.month_short(m) for m in t["m"]], y=t["cups_per_day"], mode="lines", fill="tozeroy",
        line=dict(color=c.LOSS if item == c.BERRY else c.KEY, width=2),
        hovertemplate="%{x}<br>%{y:,.0f} cups a day<extra></extra>"))
    fig.update_yaxes(title="Cups a day", rangemode="tozero")
    fig.update_xaxes(tickangle=0, tickvals=[c.month_short(t["m"].iloc[0]), c.month_short(t["m"].iloc[-1])])
    with col, c.card(f"{c.short_item(item).capitalize() if item == c.BERRY else item}: {c.spct(change, 0)} "
                     f"since {c.month_short(t['m'].iloc[0])}"):
        c.show(fig, height=170)
berry_t = trend[trend["sku"] == c.BERRY].sort_values("m")["cups_per_day"]
st.caption(f"So what: the 4 old items together peak in {c.month_name(old.idxmax())} and are lowest in "
           f"{c.month_name(old.idxmin())} (rainy season); berry "
           + ("falls every month since its launch" if (berry_t.diff().dropna() < 0).all() else "moves up and down")
           + ". Each card has its own scale, so read the shape and the % in the title.")

# ---- when ----
dp = c.load("daypart_share").query("kitchen == 'All'").set_index("daypart")
quiet = dp.nsmallest(2, "cups_per_hour")
with c.card(f"{c.join(quiet.index)} sell under half the cups of the busy hours",
            so_what=f"{c.join(quiet.index)} sell {quiet['cups_per_hour'].min():.0f}-{quiet['cups_per_hour'].max():.0f} "
                    f"cups an hour vs {dp['cups_per_hour'].max():.0f} at {dp['cups_per_hour'].idxmax().lower()}. "
                    "Staff and prep should follow the peaks; a promo only makes sense in the quiet hours.",
            how_to_read="Each cell is the average number of cups sold in one hour on one weekday over the year. "
                        "Darker blue = more cups. Read across a row for the shape of a day; read down a column to "
                        "compare weekdays."):
    kitchen = c.choose("Kitchen", c.KITCHENS, key="dp_kitchen", all_label="All")
    h = hm[hm["kitchen"] == kitchen]
    days = h.sort_values("day_of_week")["day_name"].unique().tolist()
    grid = h.pivot(index="day_name", columns="hour", values="avg_cups_per_hour").reindex(days)
    busy = h.loc[h["avg_cups_per_hour"].idxmax()]
    st.markdown(f"**{'All kitchens' if kitchen == 'All' else kitchen}: busiest hour is {busy['day_name']} "
                f"{int(busy['hour'])}:00 with {busy['avg_cups_per_hour']:.0f} cups an hour**")
    fig = go.Figure(go.Heatmap(z=grid.to_numpy(), x=grid.columns, y=grid.index, colorscale=c.SEQUENTIAL, xgap=1,
                               ygap=1, colorbar=dict(title="Cups an hour", thickness=12),
                               hovertemplate="%{y} %{x}:00<br>%{z:.0f} cups an hour<extra></extra>"))
    fig.update_xaxes(title="Hour of day", dtick=2)
    fig.update_yaxes(title="Weekday", autorange="reversed")
    c.show(fig, height=320)

left, right = st.columns(2)
with left:
    share = c.load("kitchen_platform_share").groupby("kitchen")["kitchen_revenue_share_pct"].first()
    peaks = pd.DataFrame({
        "Kitchen": by_kitchen.index,
        "Busiest hour": [f"{h}:00" for h in by_kitchen.idxmax(axis=1)],
        "Cups an hour at peak": by_kitchen.max(axis=1).to_numpy(),
        "Quietest hour": [f"{h}:00" for h in by_kitchen.idxmin(axis=1)],
        "Cups an hour when quiet": by_kitchen.min(axis=1).to_numpy(),
        "% of company revenue": share.reindex(by_kitchen.index).to_numpy(),
    }).set_index("Kitchen").reindex(c.KITCHENS).reset_index()
    with c.card(f"Pattaya peaks at {peak['Pattaya']}:00 and Bangkok at {peak['Bangkok']}:00",
                so_what="the two cities need different shift plans."):
        c.table(peaks, cols=["Kitchen", "Busiest hour", "Quietest hour", "% of company revenue"],
                count=["Cups an hour at peak", "Cups an hour when quiet"], pcts=["% of company revenue"],
                name="kitchen_peaks")

with right:
    all_after = item_rows["cm_after_waste_per_cup"].reindex(c.ITEMS)
    with c.card(f"{c.short_item(all_after.idxmin()).capitalize()} earns the least per cup: "
                f"{c.baht(all_after.min())} after waste",
                how_to_read="**Profit per cup** (contribution margin, CM) = price paid - platform commission - fruit "
                            "(that week's cost) - packaging + labor. **After waste** also takes away the cost of "
                            "cups made and thrown away. Money is summed before dividing by cups."):
        platform = c.choose("Platform", ["LINE MAN", "Grab"], key="dp_platform")
        if platform == "All":
            ue = item_rows.reindex(c.ITEMS)
        else:
            ue = (ue_all[(ue_all["level"] == "item_platform") & (ue_all["platform"] == platform)]
                  .set_index("sku").reindex(c.ITEMS))
        has_waste = ue["cm_after_waste_per_cup"].notna().all()
        y = ue["cm_after_waste_per_cup"] if has_waste else ue["cm_per_cup"]
        worst = y.idxmin()
        what = "after waste" if has_waste else "before waste (waste has no platform split)"
        st.markdown(f"{platform if platform != 'All' else 'Both apps'}: {c.short_item(worst)} earns the least, "
                    f"{c.baht(y.min())} a cup {what}.")
        fig = go.Figure(go.Bar(x=[c.short_item(s) for s in ue.index], y=y,
                               marker_color=c.colors(ue.index, [worst], c.LOSS),
                               text=[c.baht(v) for v in y], textposition="outside", cliponaxis=False,
                               customdata=[c.baht(v) for v in y], hovertemplate="%{x}<br>%{customdata} a cup<extra></extra>"))
        fig.add_hline(y=0, line=dict(color=c.DARK, width=1))
        fig.update_yaxes(title="Profit per cup (฿)", tickprefix="฿",
                         range=[min(y.min(), 0) - y.max() * 0.2, y.max() * 1.25])
        c.show(fig, height=260)
        names = {"cups": "Cups", "list_price": "List price", "avg_sell_price": "Avg price paid",
                 "commission_per_cup": "Commission", "fruit_per_cup": "Fruit", "pack_labor_per_cup": "Pack + labor",
                 "cm_per_cup": "Profit per cup"}
        if has_waste:
            names |= {"waste_per_cup": "Waste", "cm_after_waste_per_cup": "Profit after waste",
                      "waste_rate_pct": "Waste rate"}
        tbl = ue[list(names)].rename(columns=names).rename_axis("Item").reset_index()
        show_cols = (["Item", "Avg price paid", "Profit per cup", "Profit after waste"] if has_waste
                     else ["Item", "Avg price paid", "Commission", "Profit per cup"])
        c.table(tbl, cols=show_cols, count=["Cups"], pcts=["Waste rate"] if has_waste else (),
                per_cup=[v for k, v in names.items() if k not in ("cups", "waste_rate_pct")],
                highlight=tbl["Item"].eq(worst), name=f"unit_economics_{platform.replace(' ', '_').lower()}")
        w = ue.loc[worst]
        if has_waste:
            st.caption(f"So what: {c.short_item(worst)} has the highest list price ({c.baht(w['list_price'], 0)}) but "
                       f"fruit costs {c.baht(w['fruit_per_cup'])} and waste {c.baht(w['waste_per_cup'])} a cup "
                       f"({c.pct(w['waste_rate_pct'])} of cups thrown away). Selling more of it does not help until "
                       "its cost or price is fixed.")
        else:
            other = ue_all[(ue_all["level"] == "item_platform") & (ue_all["platform"] != platform)].set_index("sku")
            st.caption(f"So what: on {platform}, {c.short_item(worst)} keeps {c.baht(w['cm_per_cup'])} a cup before "
                       f"waste vs {c.baht(other.loc[worst, 'cm_per_cup'])} on the other app; the gap is the "
                       "commission rate.")

# ---- elasticity and price decisions ----
main = el[el["estimate"].str.startswith("1")].set_index("sku").reindex(c.ITEMS)
be = prs["breakeven_elasticity"].reindex(c.ITEMS)
# Same split as the lesson-6 decisions: a new list price now, or a test price first.
room = [s for s in c.ITEMS if prs.loc[s, "new_price"] > prs.loc[s, "price_now"]]
cross = [s for s in c.ITEMS if pd.notna(prs.loc[s, "test_price"])]

left, right = st.columns([2, 3])
with left:
    fig = go.Figure()
    names = [c.short_item(s) for s in main.index]
    fig.add_scatter(x=main["elasticity"], y=names, mode="markers", name="Measured (Bundle (RC101) days vs normal)",
                    marker=dict(color=c.KEY, size=11),
                    error_x=dict(type="data", symmetric=False, array=main["ci_high_by_day"] - main["elasticity"],
                                 arrayminus=main["elasticity"] - main["ci_low_by_day"], color=c.KEY),
                    customdata=main[["ci_low_by_day", "ci_high_by_day"]],
                    hovertemplate="%{y}<br>measured %{x:.2f}<br>range %{customdata[0]:.2f} to "
                                  "%{customdata[1]:.2f}<extra></extra>")
    fig.add_scatter(x=be, y=names, mode="markers", name="Break-even for the next price step",
                    marker=dict(color=c.DARK, size=11, symbol="x"),
                    hovertemplate="%{y}<br>break-even %{x:.2f}<extra></extra>")
    fig.update_xaxes(title="Elasticity (% change in cups for a 1% higher price)")
    fig.update_yaxes(autorange="reversed")
    with c.card(f"{c.join(c.short_item(s) for s in room)} can take the next price step; "
                f"{c.join(cross)} need a test first",
                so_what=f"raise {c.join(raise_.index)} now; berry's rise is part of its cost fix. {c.join(cross)} have "
                        "few promo days or a range that reaches the break-even, so a test in one kitchen comes first.",
                how_to_read="**Elasticity** = how much cups change when the price goes up 1%. A blue dot is what we "
                            "measured on Bundle (RC101) days vs normal days; the line is its likely range. The X is "
                            "the **break-even**: if customers reacted that strongly, the next price step would earn "
                            "the same money as today. If the whole blue line is right of the X, customers react "
                            "less, so a price rise adds profit.",
                method="Log-log regression per item, Bundle (RC101) days (random schedule) vs normal price, with "
                       "hour, weekday, kitchen, platform and month controls. The range is clustered by day, because "
                       "one promo covers a whole day. Raise one menu step only if the whole range and the day-level "
                       "estimate are above the break-even, and profit still rises at the cautious elasticity."):
        c.show(fig, height=330, legend=True)
        with st.expander("Per item, in words"):
            lines = []
            for s, r in main.iterrows():
                why = ("room to raise: the whole range is above the break-even" if s in room and s != c.BERRY else
                       "room to raise; the rise is part of the berry cost fix" if s in room else
                       f"test first: {prs.loc[s, 'main_risk']}")
                lines.append(f"- **{s}:** a 10% higher price sells about {abs(r['elasticity']) * 10:.0f}% fewer cups; "
                             f"{why}.")
            st.markdown(c.promo("\n".join(lines)))
            etbl = pd.DataFrame({"Item": main.index, "Measured": main["elasticity"].to_numpy(),
                                 "Range (by day)": [f"{lo:.2f} to {hi:.2f}" for lo, hi in
                                                    zip(main["ci_low_by_day"], main["ci_high_by_day"])],
                                 "Break-even": be.to_numpy(), "Promo days": main["promo_days"].to_numpy()})
            c.table(etbl, dec=["Measured", "Break-even"], count=["Promo days"], name="elasticity", raw=el)


def cm_text(r) -> str:
    """Profit change a month for one price decision, as a ฿ range."""
    if pd.notna(r["cm_change_low"]):
        return c.thb_range(r["cm_change_low"], r["cm_change_high"])
    if pd.notna(r["cm_change_if_test_low"]):
        return f"if test passes: {c.thb_range(r['cm_change_if_test_low'], r['cm_change_if_test_high'])}"
    return ""


with right:
    ptbl = pd.DataFrame({
        "Item": pr["sku"], "Price now": pr["price_now"].map(lambda x: c.baht(x, 0)),
        "Decision": pr["decision"].map(c.title_case),
        "New price": [c.baht(n, 0) if n != p else (f"test {c.baht(t, 0)}" if pd.notna(t) else "")
                      for n, p, t in zip(pr["new_price"], pr["price_now"], pr["test_price"])],
        "Profit a month": [cm_text(r) for _, r in pr.iterrows()], "Confidence": pr["confidence"]})
    with c.card(f"Raise {c.join(raise_.index)}; test {c.join(cross)} before any change",
                so_what=f"profit a month is before waste on the {pr['base_period'].iloc[0]} base, low to high "
                        "elasticity. The Sep-Nov value of each action, from one model, is on the Action plan page."):
        c.table(ptbl, cols=["Item", "Price now", "Decision", "New price", "Profit a month"],
                highlight=pr["decision"].eq("raise"), name="price_recommendation", raw=pr)
        with st.expander("Why: main risk and the reason in the decision log"):
            log = c.decisions().query("Lesson == '6'")
            for _, r in pr.iterrows():
                key = "Platform pricing" if "(" in r["sku"] else r["sku"]
                row = log[log["Decision"].str.startswith(f"{key}:")]
                reason = f"  \n{row['Reason'].iloc[0]}" if len(row) else ""
                st.markdown(c.promo(f"**{r['sku']}** ({c.title_case(r['decision'])}). Main risk: {r['main_risk']}."
                                    f"{reason}"))

c.next_page(c.PROMO_PAGE)
