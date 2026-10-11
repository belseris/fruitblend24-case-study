"""Promotions: lift needed vs lift measured, net CM per code, keep/modify/kill and waste on promo days."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

summ = c.load("promo_summary")
inc = c.load("promo_incremental")
dec = c.load("promo_decision")
ws = c.load("waste_summary")
months = c.load("company_pnl")["month"].nunique()

codes = inc[inc["level"] == "code"].set_index("code")
net_month = codes["net"] / months
kill, modify = dec[dec["decision"] == "Kill"], dec[dec["decision"] == "Modify + test"]

c.page_header(
    c.PAGES["pages/3_Promotions.py"][1],
    f"**None of them: all {len(codes)} codes lose money after waste and side effects, "
    f"{c.thb(net_month.sum())} a month together.** Stop {len(kill)} of {len(dec)} promo rows "
    f"(saves {c.thb(kill['kill_saving'].sum())} a month). Change and test the other {len(modify)} "
    f"(up to {c.sthb(modify['modify_net'].sum())} a month if the tests pass). Keep: none.")

# ---- lift ----
st.subheader("Do promos sell enough extra cups?")
cp = summ[summ["level"] == "code_platform"].groupby("base_code")[["cups", "cm_thb_if_full_price", "cm_thb_promo"]].sum()
sk = (summ[summ["level"] == "code_platform_sku"].query("base_code == 'RC101'")
      .groupby("sku")[["cm_thb_if_full_price", "cm_thb_promo"]].sum())
need = {code: (r["cm_thb_if_full_price"] / r["cm_thb_promo"] - 1) * 100 for code, r in cp.iterrows()}
need |= {f"RC101 {s}": (r["cm_thb_if_full_price"] / r["cm_thb_promo"] - 1) * 100 for s, r in sk.iterrows()}
got = {code: r["actual_lift_pct"] for code, r in codes.iterrows()}
got |= {f"RC101 {r['sku']}": r["actual_lift_pct"] for _, r in inc[inc["level"] == "rc101_sku"].iterrows()}
labels = [k for k in ["RC102", "RC103", "RC101"] + [f"RC101 {s}" for s in c.ITEMS] if k in need and k in got]
ex = cp.loc["RC102"]
st.markdown(f"**Break-even lift** = how many more cups a promo must sell just to earn the same CM as at full price "
            f"(CM per cup at full price / CM per cup at promo price - 1). Example: RC102 cuts CM from "
            f"{c.baht(ex['cm_thb_if_full_price'] / ex['cups'])} to {c.baht(ex['cm_thb_promo'] / ex['cups'])} a cup, "
            f"so it needs {c.spct(need['RC102'], 0)} more cups.")
fig = go.Figure()
fig.add_bar(x=labels, y=[need[k] for k in labels], name="Lift needed to break even", marker_color=c.GREY,
            hovertemplate="%{x}<br>needs %{y:+.0f}% cups<extra></extra>")
fig.add_bar(x=labels, y=[got[k] for k in labels], name="Lift measured vs normal days", marker_color=c.KEY,
            hovertemplate="%{x}<br>sold %{y:+.0f}% cups<extra></extra>")
fig.update_yaxes(title="% more cups than on normal days", ticksuffix="%")
short = [k for k in labels if got[k] < need[k]]
c.show(fig, f"{len(short)} of {len(labels)} promo groups sell fewer extra cups than they need, even before waste; "
            f"RC102 sells {c.spct(got['RC102'], 0)} but needs {c.spct(need['RC102'], 0)}",
       f"Break-even lift vs measured lift, {c.data_period()}. RC101 = bundle on one item, RC102 = double day, "
       "RC103 = rainy season", height=420, legend=True)
ok = [k for k in labels if k not in short]
c.chart_note(("no promo group" if not ok else " and ".join(ok)) + " sells enough extra cups to pay for its "
             "discount. A promo can still be worth it for new customers, but the data cannot measure that.")

# ---- net ----
st.subheader("What does each code earn after waste and side effects?")
worst = net_month.idxmin()
fig = go.Figure(go.Bar(x=net_month.index, y=net_month, marker_color=c.colors(net_month.index, [worst], c.LOSS),
                       text=[c.thb(v) for v in net_month], textposition="outside",
                       customdata=[c.thb(v) for v in net_month], hovertemplate="%{x}<br>%{customdata} a month<extra></extra>"))
fig.add_hline(y=0, line=dict(color=c.DARK, width=1))
lo = net_month.min() * 1.35
fig.update_yaxes(title="Net CM a month (฿)", range=[lo, 0], **c.money_ticks(lo, 0, 4))
c.show(fig, f"All {len(net_month)} codes lose CM: {c.thb(net_month.sum())} a month together; "
            f"{worst} loses the most ({c.thb(net_month[worst])})",
       "Net incremental CM a month = promo CM - normal-day cups x full-price CM + extra waste + side effects",
       height=380)
c.how_to_read("Start from the CM the promo days earned. Take away what the same hours would have earned on a normal "
              "day at full price (the baseline cups). Add the extra waste on promo days and the side effects: other "
              "items sold more or less, and sales pulled from the next days. Below 0 means we would have earned "
              "more without the promo.")
c.chart_note(f"stopping every code would add about {c.thb(-net_month.sum())} a month; the table below keeps the "
             "versions that a small change could turn positive.")
ntbl = codes.reset_index()[["code", "cups", "baseline_cups", "actual_lift_pct", "inc", "waste", "spill", "pull", "net"]]
ntbl["net a month"] = ntbl["net"] / months
ntbl = ntbl.rename(columns={"baseline_cups": "baseline cups", "actual_lift_pct": "lift", "inc": "CM vs baseline",
                            "waste": "extra waste", "spill": "other items", "pull": "pull-forward", "net": "net (year)"})
c.table(ntbl, count=["cups", "baseline cups"], pcts=["lift"],
        money=["CM vs baseline", "extra waste", "other items", "pull-forward", "net (year)", "net a month"])
c.download(ntbl, "promo_net_by_code")

# ---- decisions ----
st.subheader("Keep, modify or kill?")
pick = st.selectbox("Decision", ["All"] + sorted(dec["decision"].unique()), key="pr_decision")
d = dec if pick == "All" else dec[dec["decision"] == pick]
dtbl = d[["code", "platform", "sku", "decision", "change", "promo_days", "net_per_month_new_prices", "kill_saving",
          "modify_net", "confidence", "main_risk"]].rename(columns={
    "sku": "item", "promo_days": "promo days", "net_per_month_new_prices": "today a month",
    "kill_saving": "saving if killed", "modify_net": "if the test passes", "main_risk": "main risk"})
c.table(dtbl, count=["promo days"], money=["today a month", "saving if killed", "if the test passes"],
        highlight=d["decision"].eq("Kill"))
st.caption(f"Kill rows save {c.thb(kill['kill_saving'].sum())} a month. Modify rows add "
           f"{c.sthb(modify['modify_net'].sum())} a month only if their tests pass "
           f"(range {c.thb(modify['modify_low'].sum())} to {c.thb(modify['modify_high'].sum())}). "
           "Today = net CM a month at the new Watermelon and PassionFruit prices.")
c.download(dec, "promo_decision")

# ---- waste ----
st.subheader("Do promo days waste more?")
pw = ws[ws["level"] == "item x promo day"].copy()
pw[["sku", "promo"]] = pw["group"].str.split(" | ", regex=False, expand=True)
pw = pw.pivot(index="sku", columns="promo", values=["wasted_per_kitchen_day", "waste_rate_pct"]).reindex(c.ITEMS)
more = (pw[("wasted_per_kitchen_day", "True")] / pw[("wasted_per_kitchen_day", "False")] - 1) * 100
rate_gap = (pw[("waste_rate_pct", "True")] - pw[("waste_rate_pct", "False")]).abs().max()
fig = go.Figure()
fig.add_bar(x=pw.index, y=pw[("wasted_per_kitchen_day", "False")], name="Normal day", marker_color=c.GREY,
            hovertemplate="%{x}<br>normal day: %{y:.1f} cups wasted<extra></extra>")
fig.add_bar(x=pw.index, y=pw[("wasted_per_kitchen_day", "True")], name="Promo day", marker_color=c.KEY,
            hovertemplate="%{x}<br>promo day: %{y:.1f} cups wasted<extra></extra>")
fig.update_yaxes(title="Cups wasted per kitchen a day")
c.show(fig, f"Promo days waste {more.min():.0f}-{more.max():.0f}% more cups, but the waste rate moves less than "
            f"{rate_gap:.1f} points",
       f"Cups wasted per kitchen a day on days with and without a promo for that item, {c.data_period()}",
       height=400, legend=True)
extra = codes["waste"]
c.chart_note("kitchens already prep more on promo days, and they sell more too. Extra waste cost vs comparable "
             "normal days: " + ", ".join(f"{k} {c.thb(-v)} a year" for k, v in extra.items())
             + ". When a promo stops, prep must come down with it.")
wtbl = pd.DataFrame({"Item": pw.index,
                     "Waste rate, normal day": pw[("waste_rate_pct", "False")].to_numpy(),
                     "Waste rate, promo day": pw[("waste_rate_pct", "True")].to_numpy(),
                     "Cups wasted a day, normal": pw[("wasted_per_kitchen_day", "False")].to_numpy(),
                     "Cups wasted a day, promo": pw[("wasted_per_kitchen_day", "True")].to_numpy()})
c.table(wtbl, pcts=["Waste rate, normal day", "Waste rate, promo day"],
        dec=["Cups wasted a day, normal", "Cups wasted a day, promo"])
c.download(wtbl, "waste_on_promo_days")

c.method_box(
    "- **Baseline** = mean cups of normal hours with the same kitchen, item, platform, month, weekday and hour. "
    "Month is in the key because the rainy-season code only runs in the rainy months.\n"
    "- **Net** = promo CM - baseline cups x CM at full price + extra waste + side effects (other items on bundle "
    "days, sales pulled from the next days). The range comes from a bootstrap over promo days.\n"
    "- The one promo day in Songkran week is left out: every item sold far above baseline that day, so it has no "
    "fair baseline.\n"
    "- **Rules:** Kill if the best change is still below 0; Modify + test if one change (smaller discount, quiet "
    "hours only, no berry) turns it positive. Tests run for a few weeks against a control.\n"
    "- **Limits:** the double-day code has few days, and new customers from promos are not in the data.")
