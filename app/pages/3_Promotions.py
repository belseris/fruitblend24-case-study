"""Promotions: lift needed vs lift measured, net profit per code, keep/modify/kill and waste on promo days."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

summ = c.load("promo_summary")
inc = c.load("promo_incremental")
dec = c.load("promo_decision")
ws = c.load("waste_summary")
months = c.load("company_pnl")["month"].nunique()
levers = c.load("scenario_levers").set_index("step")["elasticity_-1.5"]

codes = inc[inc["level"] == "code"].set_index("code")
net_month = codes["net"] / months
kill, modify = dec[dec["decision"] == "Kill"], dec[dec["decision"] == "Modify + test"]

# Waste on days with and without a promo for that item.
pw = ws[ws["level"] == "item x promo day"].copy()
pw[["sku", "promo"]] = pw["group"].str.split(" | ", regex=False, expand=True)
pw = pw.pivot(index="sku", columns="promo", values=["wasted_per_kitchen_day", "waste_rate_pct"]).reindex(c.ITEMS)
more = (pw[("wasted_per_kitchen_day", "True")] / pw[("wasted_per_kitchen_day", "False")] - 1) * 100

c.page_header(
    c.PROMO_PAGE,
    f"**{c.thb(net_month.sum())} a month: all {len(codes)} promo codes lose money after waste and side effects.** "
    f"Stop {len(kill)} of {len(dec)} promo rows (saves {c.thb(kill['kill_saving'].sum())} a month) and test changes "
    f"on the other {len(modify)} (up to {c.sthb(modify['modify_net'].sum())}).")

c.kpi_row([
    dict(label="Promo loss a month", value=c.thb(net_month.sum()),
         series=[net_month.get(k, 0) for k in c.PROMO],
         help="Net profit of all promo codes vs normal days, after extra waste and side effects. Average month "
              f"over {c.data_period()}."),
    dict(label="Saving if Kill rows stop", value=c.thb(kill["kill_saving"].sum()),
         delta=f"{len(kill)} of {len(dec)} rows", delta_color="off", delta_arrow="off",
         help="Profit a month we get back by stopping the promo rows marked Kill, at the new prices, average month "
              f"over {c.data_period()}. In the Sep-Nov model the same stop is worth "
              f"{c.thb(levers.filter(like='Kill').iloc[0])} a month (Action plan page)."),
    dict(label="Upside if tests pass", value=c.sthb(modify["modify_net"].sum()),
         delta=f"range {c.thb(modify['modify_low'].sum())} to {c.thb(modify['modify_high'].sum())}",
         delta_color="off", delta_arrow="off",
         help="Profit a month if the changed promos (Modify + test) work as measured. 0 until a test passes."),
    dict(label="Extra promo-day waste a month", value=c.thb(-codes["waste"].sum() / months),
         delta=f"{more.min():.0f}-{more.max():.0f}% more cups wasted", delta_color="off", delta_arrow="off",
         help="Waste cost on promo days above comparable normal days, all codes, a month."),
])

# ---- lift and net ----
cp = summ[summ["level"] == "code_platform"].groupby("base_code")[["cups", "cm_thb_if_full_price", "cm_thb_promo"]].sum()
sk = (summ[summ["level"] == "code_platform_sku"].query("base_code == 'RC101'")
      .groupby("sku")[["cm_thb_if_full_price", "cm_thb_promo"]].sum())
need = {c.promo(code): (r["cm_thb_if_full_price"] / r["cm_thb_promo"] - 1) * 100 for code, r in cp.iterrows()}
need |= {f"{c.promo('RC101')}: {c.short_item(s)}": (r["cm_thb_if_full_price"] / r["cm_thb_promo"] - 1) * 100
         for s, r in sk.iterrows()}
got = {c.promo(code): r["actual_lift_pct"] for code, r in codes.iterrows()}
got |= {f"{c.promo('RC101')}: {c.short_item(r['sku'])}": r["actual_lift_pct"]
        for _, r in inc[inc["level"] == "rc101_sku"].iterrows()}
order = [c.promo(k) for k in ["RC102", "RC103", "RC101"]] + [f"{c.promo('RC101')}: {c.short_item(s)}" for s in c.ITEMS]
labels = [k for k in order if k in need and k in got]
short = [k for k in labels if got[k] < need[k]]
rc102 = c.promo("RC102")

left, right = st.columns(2)
with left:
    fig = go.Figure()
    fig.add_bar(y=labels, x=[need[k] for k in labels], name="Lift needed to break even", marker_color=c.GREY,
                orientation="h", hovertemplate="%{y}<br>needs %{x:+.0f}% cups<extra></extra>")
    fig.add_bar(y=labels, x=[got[k] for k in labels], name="Lift measured vs normal days", marker_color=c.KEY,
                orientation="h", hovertemplate="%{y}<br>sold %{x:+.0f}% cups<extra></extra>")
    fig.update_xaxes(title="% more cups than on normal days", ticksuffix="%")
    fig.update_yaxes(autorange="reversed")
    ex = cp.loc["RC102"] if "RC102" in cp.index else None
    with c.card(f"{len(short)} of {len(labels)} promo groups sell fewer extra cups than they need",
                so_what=f"{c.join([k for k in labels if k not in short], 'no promo group')} sells enough extra cups to "
                        "pay for its discount, even before waste. A promo can still bring new customers, but the data "
                        "cannot measure that.",
                how_to_read="**Break-even lift** = how many more cups a promo must sell just to earn the same profit "
                            "as at full price: profit per cup at full price / profit per cup at the promo price - 1. "
                            + (f"Example: {rc102} cuts profit from {c.baht(ex['cm_thb_if_full_price'] / ex['cups'])} "
                               f"to {c.baht(ex['cm_thb_promo'] / ex['cups'])} a cup, so it needs "
                               f"{c.spct(need[rc102], 0)} more cups. " if ex is not None else "")
                            + "Grey = needed, blue = what it really sold vs the same hours on normal days."):
        c.show(fig, height=380, legend=True)

with right:
    worst = net_month.idxmin()
    x = [c.promo(k) for k in net_month.index]
    fig = go.Figure(go.Bar(x=x, y=net_month, marker_color=c.colors(net_month.index, [worst], c.LOSS),
                           text=[c.thb(v) for v in net_month], textposition="outside", cliponaxis=False,
                           customdata=[c.thb(v) for v in net_month],
                           hovertemplate="%{x}<br>%{customdata} a month<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=c.DARK, width=1))
    lo = net_month.min() * 1.35
    fig.update_yaxes(title="Net profit a month (฿)", range=[lo, 0], **c.money_ticks(lo, 0, 4))
    with c.card(f"All {len(net_month)} codes lose money: {c.thb(net_month.sum())} a month; {c.promo(worst)} "
                "loses the most",
                so_what=f"stopping every code would add about {c.thb(-net_month.sum())} a month (average month of "
                        "the year); the decision table "
                        "keeps the versions that a small change could turn positive.",
                how_to_read="Start from the profit the promo days earned. Take away what the same hours would have "
                            "earned on a normal day at full price (the baseline cups). Add the extra waste on promo "
                            "days and the side effects: other items sold more or less, and sales pulled from the "
                            "next days. Below 0 = we would have earned more without the promo.",
                method="**Baseline** = mean cups of normal hours with the same kitchen, item, platform, month, "
                       "weekday and hour (month is in the key because the rainy-season code only runs in the rainy "
                       "months). The range comes from a bootstrap over promo days. The one promo day in Songkran "
                       "week is left out: every item sold far above baseline that day."):
        c.show(fig, height=380)
        ntbl = codes.reset_index()[["code", "cups", "baseline_cups", "actual_lift_pct", "inc", "waste", "spill", "pull",
                                    "net"]]
        ntbl["code"] = ntbl["code"].map(c.promo)
        ntbl["net_month"] = ntbl["net"] / months
        ntbl = ntbl.rename(columns={"baseline_cups": "Baseline cups", "actual_lift_pct": "Lift",
                                    "inc": "Profit vs baseline", "waste": "Extra waste", "spill": "Other items",
                                    "pull": "Pull-forward", "net": "Net (year)", "net_month": "Net a month"})
        c.table(ntbl, cols=["code", "Lift", "Extra waste", "Net a month"],
                count=["cups", "Baseline cups"], pcts=["Lift"], name="promo_net_by_code",
                money=["Profit vs baseline", "Extra waste", "Other items", "Pull-forward", "Net (year)", "Net a month"])

# ---- decisions ----
with c.card(f"Kill {len(kill)} promo rows, change and test {len(modify)}, keep none",
            so_what=f"Kill rows save {c.thb(kill['kill_saving'].sum())} a month. Modify rows add "
                    f"{c.sthb(modify['modify_net'].sum())} a month only if their tests pass.",
            method="**Kill** if the best change is still below 0. **Modify + test** if one change (smaller discount, "
                   "quiet hours only, no berry) turns it positive. Tests run for a few weeks against a control. "
                   "Limits: the double-day code has few days, and new customers from promos are not in the data."):
    pick = c.choose("Decision", sorted(dec["decision"].unique()), key="pr_decision")
    d = dec if pick == "All" else dec[dec["decision"] == pick]
    dtbl = pd.DataFrame({
        "Promo": [c.promo(code) + ("" if p == "All" else f" on {p}") for code, p in zip(d["code"], d["platform"])],
        "Item": d["sku"].replace("All", "All items").to_numpy(),
        "Decision": d["decision"].map(c.title_case).to_numpy(), "Change": d["change"].map(c.title_case).to_numpy(),
        "฿ a month": [s if dd == "Kill" else m for dd, s, m in zip(d["decision"], d["kill_saving"], d["modify_net"])],
        "Confidence": d["confidence"].to_numpy(),
        "Promo days": d["promo_days"].to_numpy(), "Today a month": d["net_per_month_new_prices"].to_numpy(),
        "Main risk": d["main_risk"].map(c.promo).to_numpy()})
    c.table(dtbl, cols=["Promo", "Item", "Decision", "Change", "฿ a month", "Confidence"],
            money=["฿ a month", "Today a month"], count=["Promo days"], highlight=d["decision"].eq("Kill"),
            name="promo_decision", raw=dec)
    st.caption("฿ a month = saving if a Kill row stops, or the gain if a Modify + test row passes its test, at the new "
               "Watermelon and PassionFruit prices.")

# ---- waste ----
rate_gap = (pw[("waste_rate_pct", "True")] - pw[("waste_rate_pct", "False")]).abs().max()
names = [c.short_item(s) for s in pw.index]
fig = go.Figure()
fig.add_bar(x=names, y=pw[("wasted_per_kitchen_day", "False")], name="Normal day", marker_color=c.GREY,
            hovertemplate="%{x}<br>normal day: %{y:.1f} cups wasted<extra></extra>")
fig.add_bar(x=names, y=pw[("wasted_per_kitchen_day", "True")], name="Promo day", marker_color=c.KEY,
            hovertemplate="%{x}<br>promo day: %{y:.1f} cups wasted<extra></extra>")
fig.update_yaxes(title="Cups wasted per kitchen a day")
with c.card(f"Promo days waste {more.min():.0f}-{more.max():.0f}% more cups, but the waste rate moves less than "
            f"{rate_gap:.1f} points",
            so_what="promo days waste more cups because they sell more cups; the waste rate barely moves. Extra waste "
                    "cost vs comparable normal days: " + ", ".join(f"{c.promo(k)} {c.thb(-v)} a year" for k, v in codes["waste"].items())
                    + ". When a promo stops, prep must come down with it."):
    c.show(fig, height=320, legend=True)
    wtbl = pd.DataFrame({"Item": pw.index,
                         "Waste rate, normal day": pw[("waste_rate_pct", "False")].to_numpy(),
                         "Waste rate, promo day": pw[("waste_rate_pct", "True")].to_numpy(),
                         "Cups wasted a day, normal": pw[("wasted_per_kitchen_day", "False")].to_numpy(),
                         "Cups wasted a day, promo": pw[("wasted_per_kitchen_day", "True")].to_numpy()})
    with st.expander("Full table"):
        c.table(wtbl, pcts=["Waste rate, normal day", "Waste rate, promo day"],
                dec=["Cups wasted a day, normal", "Cups wasted a day, promo"], name="waste_on_promo_days")

c.next_page(c.PNL)
