"""Demand and pricing: when customers buy, what one cup earns, price sensitivity and price decisions."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

kitchen = c.pick("Kitchen (when do customers buy)", c.KITCHENS, "dp_kitchen")
platform = st.sidebar.selectbox("Platform (what one cup earns)", ["All", "LINE MAN", "Grab"], key="dp_platform")

hm = c.load("demand_heatmap")
mix = c.load("sales_mix").set_index("sku").reindex(c.ITEMS)
ue_all = c.load("unit_economics")
pr = c.load("price_recommendation")
el = c.load("elasticity")

# Busiest hour per city: mean of the kitchens' hourly profiles.
by_kitchen = hm[hm["kitchen"] != "All"].groupby(["kitchen", "hour"])["avg_cups_per_hour"].mean().unstack()
city = by_kitchen.groupby(lambda k: "Pattaya" if k.startswith("Pattaya") else "Bangkok").mean()
peak = city.idxmax(axis=1)
top = mix["share_cups_pct"].idxmax()
item_rows = ue_all[ue_all["level"] == "item"].set_index("sku")
berry_cup = item_rows.loc[c.BERRY, "cm_after_waste_per_cup"]
prs = pr[pr["sku"].isin(c.ITEMS)].set_index("sku")
raise_ = prs[prs["decision"] == "raise"]
test = prs[prs["decision"].str.contains("test")]

c.page_header(
    c.PAGES["pages/2_Demand_and_Pricing.py"][1],
    f"**{top} is {c.pct(mix.loc[top, 'share_cups_pct'], 0)} of cups; Pattaya is busiest at {peak['Pattaya']}:00 "
    f"and Bangkok at {peak['Bangkok']}:00.** "
    + "Raise " + " and ".join(f"{s} ({r['price_now']:.0f} -> {r['new_price']:.0f} THB)" for s, r in raise_.iterrows())
    + f": customers react less than the break-even. Test {' and '.join(test.index)} first. "
      f"Berry {'loses' if berry_cup < 0 else 'earns'} {c.baht(abs(berry_cup))} a cup after waste.")

# ---- when ----
st.subheader("When do customers buy?")
h = hm[hm["kitchen"] == kitchen]
days = h.sort_values("day_of_week")["day_name"].unique().tolist()
grid = h.pivot(index="day_name", columns="hour", values="avg_cups_per_hour").reindex(days)
busy = h.loc[h["avg_cups_per_hour"].idxmax()]
fig = go.Figure(go.Heatmap(z=grid.to_numpy(), x=grid.columns, y=grid.index, colorscale=c.SEQUENTIAL, xgap=1, ygap=1,
                           colorbar=dict(title="cups an hour"),
                           hovertemplate="%{y} %{x}:00<br>%{z:.0f} cups an hour<extra></extra>"))
fig.update_xaxes(title="Hour of day", dtick=2)
fig.update_yaxes(title="Weekday", autorange="reversed")
c.show(fig, f"{'All kitchens' if kitchen == 'All' else kitchen}: busiest hour is {busy['day_name']} "
            f"{int(busy['hour'])}:00 with {busy['avg_cups_per_hour']:.0f} cups an hour",
       f"Average cups sold per hour, by weekday and hour, {c.data_period()}", height=380)
dp = c.load("daypart_share").query("kitchen == 'All'").set_index("daypart")
quiet = dp.nsmallest(2, "cups_per_hour")
c.chart_note(f"{' and '.join(quiet.index)} sell {quiet['cups_per_hour'].min():.0f}-{quiet['cups_per_hour'].max():.0f} "
             f"cups an hour vs {dp['cups_per_hour'].max():.0f} at {dp['cups_per_hour'].idxmax().lower()}. "
             "Staff and prep should follow the peaks; a promo only makes sense in the quiet hours.")
c.how_to_read("Each cell is the average number of cups sold in one hour on one weekday over the year. Darker blue = "
              "more cups. Read across a row for the shape of a day; read down a column to compare weekdays. "
              "Use the sidebar to pick one kitchen.")

st.subheader("Which kitchen peaks when?")
share = c.load("kitchen_platform_share").groupby("kitchen")["kitchen_revenue_share_pct"].first()
peaks = pd.DataFrame({
    "Kitchen": by_kitchen.index,
    "Busiest hour": [f"{h}:00" for h in by_kitchen.idxmax(axis=1)],
    "Cups an hour at peak": by_kitchen.max(axis=1).to_numpy(),
    "Quietest hour": [f"{h}:00" for h in by_kitchen.idxmin(axis=1)],
    "Cups an hour when quiet": by_kitchen.min(axis=1).to_numpy(),
    "% of company revenue": share.reindex(by_kitchen.index).to_numpy(),
}).set_index("Kitchen").reindex(c.KITCHENS).reset_index()
c.table(peaks, count=["Cups an hour at peak", "Cups an hour when quiet"], pcts=["% of company revenue"])
st.caption(f"Hourly averages over all weekdays. Pattaya peaks at {peak['Pattaya']}:00 and Bangkok at "
           f"{peak['Bangkok']}:00, so the two cities need different shift plans.")
c.download(peaks, "kitchen_peaks")

# ---- unit economics ----
st.subheader("What does one cup earn?")
if platform == "All":
    ue = item_rows.reindex(c.ITEMS)
else:
    ue = ue_all[(ue_all["level"] == "item_platform") & (ue_all["platform"] == platform)].set_index("sku").reindex(c.ITEMS)
has_waste = ue["cm_after_waste_per_cup"].notna().all()
y = ue["cm_after_waste_per_cup"] if has_waste else ue["cm_per_cup"]
worst = y.idxmin()
fig = go.Figure(go.Bar(x=ue.index, y=y, marker_color=c.colors(ue.index, [worst], c.LOSS),
                       text=[c.baht(v) for v in y], textposition="outside", customdata=[c.baht(v) for v in y],
                       hovertemplate="%{x}<br>%{customdata} a cup<extra></extra>"))
fig.add_hline(y=0, line=dict(color=c.DARK, width=1))
fig.update_yaxes(title="THB a cup", range=[min(y.min(), 0) - y.max() * 0.2, y.max() * 1.25])
what = "after waste" if has_waste else "before waste (waste has no platform split)"
c.show(fig, f"{worst} earns the least: {c.baht(y.min())} a cup {what}",
       f"Contribution margin per cup, {mix['period'].iloc[0]} (all items on sale), platform: {platform}",
       height=380)
w = ue.loc[worst]
if has_waste:
    c.chart_note(f"{worst} has the highest list price ({c.baht(w['list_price'], 0)}) but fruit costs "
                 f"{c.baht(w['fruit_per_cup'])} and waste {c.baht(w['waste_per_cup'])} a cup "
                 f"({c.pct(w['waste_rate_pct'])} of cups thrown away). Selling more of it does not help until its "
                 "cost or price is fixed.")
else:
    other = ue_all[(ue_all["level"] == "item_platform") & (ue_all["platform"] != platform)].set_index("sku")
    c.chart_note(f"on {platform}, {worst} keeps {c.baht(w['cm_per_cup'])} a cup before waste vs "
                 f"{c.baht(other.loc[worst, 'cm_per_cup'])} on the other app; the gap is the commission rate.")
cols = {"cups": "Cups", "list_price": "List price", "avg_sell_price": "Avg price paid",
        "commission_per_cup": "Commission", "fruit_per_cup": "Fruit", "pack_labor_per_cup": "Pack + labor",
        "cm_per_cup": "CM"}
if has_waste:
    cols |= {"waste_per_cup": "Waste", "cm_after_waste_per_cup": "CM after waste", "waste_rate_pct": "Waste rate"}
tbl = ue[list(cols)].rename(columns=cols).rename_axis("Item").reset_index()
c.table(tbl, count=["Cups"], per_cup=[v for k, v in cols.items() if k not in ("cups", "waste_rate_pct")],
        pcts=["Waste rate"] if has_waste else (), highlight=tbl["Item"].eq(worst))
st.caption("Per cup, money summed before dividing. CM = price paid - commission - fruit - packaging + labor.")
c.download(tbl, f"unit_economics_{platform.replace(' ', '_').lower()}")

# ---- elasticity ----
st.subheader("How much do customers react to price?")
main = el[el["estimate"].str.startswith("1")].set_index("sku").reindex(c.ITEMS)
be = prs["breakeven_elasticity"].reindex(c.ITEMS)
# Same split as the lesson-6 decisions: a new list price now, or a test price first.
room = [s for s in c.ITEMS if prs.loc[s, "new_price"] > prs.loc[s, "price_now"]]
cross = [s for s in c.ITEMS if pd.notna(prs.loc[s, "test_price"])]
fig = go.Figure()
fig.add_scatter(x=main["elasticity"], y=main.index, mode="markers", name="Measured (bundle days vs normal price)",
                marker=dict(color=c.KEY, size=11),
                error_x=dict(type="data", symmetric=False, array=main["ci_high_by_day"] - main["elasticity"],
                             arrayminus=main["elasticity"] - main["ci_low_by_day"], color=c.KEY),
                customdata=main[["ci_low_by_day", "ci_high_by_day"]],
                hovertemplate="%{y}<br>measured %{x:.2f}<br>range %{customdata[0]:.2f} to %{customdata[1]:.2f}"
                              "<extra></extra>")
fig.add_scatter(x=be, y=be.index, mode="markers", name="Break-even for the next price step",
                marker=dict(color=c.DARK, size=11, symbol="x"), hovertemplate="%{y}<br>break-even %{x:.2f}<extra></extra>")
fig.update_xaxes(title="Elasticity (% change in cups for a 1% higher price)")
fig.update_yaxes(autorange="reversed")
c.show(fig, f"{', '.join(room[:-1])} and {room[-1]} can take the next price step; ".replace(c.BERRY, "berry")
            + f"{' and '.join(cross) if cross else 'none'} need a test first",
       "Measured elasticity with its range (by day) vs the break-even elasticity of the next menu price", height=400,
       legend=True)
c.how_to_read("Elasticity = how much cups change when the price goes up 1%. A blue dot is what we measured on bundle "
              "days vs normal days, the line is its likely range. The X is the break-even: if customers reacted "
              "that strongly, the next price step would earn the same money as today. If the whole blue line is to "
              "the right of the X, customers react less than the break-even, so a price rise adds profit.")
c.chart_note(f"raise {' and '.join(raise_.index)} now; berry's rise is part of its cost fix. "
             f"{' and '.join(cross)} have too few promo days or a range that reaches the break-even, so a test in "
             "one kitchen comes first.")
ex = main.assign(breakeven=be)
etbl = pd.DataFrame({"Item": ex.index, "Measured": ex["elasticity"].to_numpy(),
                     "Range (by day)": [f"{lo:.2f} to {hi:.2f}" for lo, hi in zip(ex["ci_low_by_day"], ex["ci_high_by_day"])],
                     "Break-even": ex["breakeven"].to_numpy(), "Promo days": ex["promo_days"].to_numpy(),
                     "Decision": prs["decision"].reindex(ex.index).to_numpy()})
c.table(etbl, dec=["Measured", "Break-even"], count=["Promo days"], highlight=etbl["Item"].isin(room))
lines = []
for s, r in ex.iterrows():
    why = ("room to raise: the whole range is above the break-even" if s in room and s != c.BERRY else
           "room to raise; the rise is part of the berry cost fix" if s in room else
           f"test first: {prs.loc[s, 'main_risk']}")
    lines.append(f"- **{s}:** a 10% higher price sells about {abs(r['elasticity']) * 10:.0f}% fewer cups; {why}.")
st.markdown("\n".join(lines))
c.download(el, "elasticity")

# ---- price decisions ----
st.subheader("What price do we set?")


def cm_text(r) -> str:
    """CM change a month for one price decision, as a ฿ range."""
    if pd.notna(r["cm_change_low"]):
        return c.thb_range(r["cm_change_low"], r["cm_change_high"])
    if pd.notna(r["cm_change_if_test_low"]):
        return f"if the test passes: {c.thb_range(r['cm_change_if_test_low'], r['cm_change_if_test_high'])}"
    return ""


ptbl = pd.DataFrame({
    "Item": pr["sku"], "Price now": pr["price_now"].map(lambda x: c.baht(x, 0)), "Decision": pr["decision"],
    "New price": [c.baht(n, 0) if n != p else "" for n, p in zip(pr["new_price"], pr["price_now"])],
    "Test price": pr["test_price"].map(lambda x: c.baht(x, 0) if pd.notna(x) else ""),
    "CM a month": [cm_text(r) for _, r in pr.iterrows()], "Confidence": pr["confidence"]})
c.table(ptbl, highlight=pr["decision"].eq("raise"))
st.caption(f"CM a month = change before waste on the {pr['base_period'].iloc[0]} base, low to high elasticity. "
           "The Sep-Nov value of each action, from one model, is on the Forecast and Inventory page.")
c.download(pr, "price_recommendation")
with st.expander("Why: main risk and the reason in the decision log"):
    log = c.decisions().query("Lesson == '6'")
    for _, r in pr.iterrows():
        key = "Platform pricing" if "(" in r["sku"] else r["sku"]
        row = log[log["Decision"].str.startswith(f"{key}:")]
        reason = f"  \n{row['Reason'].iloc[0]}" if len(row) else ""
        st.markdown(f"**{r['sku']}** ({r['decision']}). Main risk: {r['main_risk']}.{reason}")

c.method_box(
    "- **Window:** items are compared on the months when all items are on sale (berry launched in March), per cup, "
    "with money summed before dividing.\n"
    "- **CM per cup** = price paid - platform commission - fruit (that week's cost) - packaging + labor. "
    "Waste per cup is by item only: the waste data has no platform.\n"
    "- **Elasticity:** log-log regression per item, bundle-promo days (random schedule) vs normal price, with hour, "
    "weekday, kitchen, platform and month controls. The range is clustered by day, because one promo covers a "
    "whole day.\n"
    "- **Price rule:** raise one menu step only if the whole range and the day-level estimate are above the "
    "break-even of that step, and CM still rises at the cautious elasticity. Otherwise test in one kitchen first.")
