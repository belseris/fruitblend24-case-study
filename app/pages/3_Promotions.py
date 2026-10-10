"""Promotions: needed vs actual lift, net CM per code, and the keep/modify/kill decisions."""
import plotly.graph_objects as go
import streamlit as st

import common as c

c.header("Promotions", "Does each promo sell enough extra cups to pay for its discount, waste and side effects?")

summ = c.load("promo_summary")
inc = c.load("promo_incremental")
dec = c.load("promo_decision")

# Break-even lift = CM at list price / CM at promo price - 1, summed over platforms.
cp = summ[summ["level"] == "code_platform"].groupby("base_code")[["cm_thb_if_full_price", "cm_thb_promo"]].sum()
sk = (summ[summ["level"] == "code_platform_sku"].query("base_code == 'RC101'")
      .groupby("sku")[["cm_thb_if_full_price", "cm_thb_promo"]].sum())
need = {f"{code}": (r["cm_thb_if_full_price"] / r["cm_thb_promo"] - 1) * 100 for code, r in cp.iterrows()}
need.update({f"RC101 {s}": (r["cm_thb_if_full_price"] / r["cm_thb_promo"] - 1) * 100 for s, r in sk.iterrows()})
got = {r["code"]: r["actual_lift_pct"] for _, r in inc[inc["level"] == "code"].iterrows()}
got.update({f"RC101 {r['sku']}": r["actual_lift_pct"] for _, r in inc[inc["level"] == "rc101_sku"].iterrows()})
labels = ["RC102", "RC103", "RC101"] + [f"RC101 {s}" for s in c.ITEMS]

st.subheader("Do promos sell enough extra cups?")
fig = go.Figure()
fig.add_bar(x=labels, y=[need[k] for k in labels], name="Lift needed to break even", marker_color=c.TOTAL,
            hovertemplate="%{x}<br>needs +%{y:.0f}%<extra></extra>")
fig.add_bar(x=labels, y=[got[k] for k in labels], name="Lift measured vs baseline", marker_color=c.UP,
            hovertemplate="%{x}<br>got +%{y:.0f}%<extra></extra>")
fig.update_yaxes(title="% more cups than the baseline")
short = [k for k in labels if got[k] < need[k]]
c.show(fig, f"{len(short)} of {len(labels)} promo groups lift less than they need, before waste; "
            f"RC102 lifts +{got['RC102']:.0f}% but needs +{need['RC102']:.0f}%",
       "Break-even lift (CM at list price / CM at promo price - 1) vs measured lift, Sep 2025 to Aug 2026", height=420)

st.subheader("What does each code earn after waste and side effects?")
codes = inc[inc["level"] == "code"].set_index("code")
net = codes["net"] / 12
fig = go.Figure(go.Bar(x=net.index, y=net / 1000, marker_color=[c.UP if v >= 0 else c.DOWN for v in net],
                       text=(net / 1000).round(1), textposition="outside",
                       hovertemplate="%{x}<br>%{y:.1f}k THB a month<extra></extra>"))
fig.update_yaxes(title="THB thousands a month")
c.show(fig, f"All {len(net)} codes lose CM after waste: {net.sum() / 1000:.1f}k THB a month together",
       "Net incremental CM a month = promo CM - baseline cups x list-price CM + waste effect + spillover + pull-forward",
       height=380, legend=False)
st.dataframe(c.in_k(codes.reset_index()[["code", "cups", "baseline_cups", "actual_lift_pct", "inc", "waste", "net"]],
                    ["inc", "waste", "net"]), hide_index=True)

st.subheader("Keep, modify or kill?")
pick = st.selectbox("Decision", ["All", "Kill", "Modify + test"], key="pr_decision")
d = dec if pick == "All" else dec[dec["decision"] == pick]
st.dataframe(c.in_k(d[["code", "platform", "sku", "decision", "change", "net_per_month_new_prices", "kill_saving",
                       "modify_net", "confidence", "main_risk"]], ["net_per_month_new_prices", "kill_saving", "modify_net"]),
             hide_index=True)
st.caption(f"Kill rows save {dec['kill_saving'].sum() / 1000:.1f}k THB a month; Modify rows add about "
           f"{dec['modify_net'].sum() / 1000:.1f}k only if their 4-week tests pass. "
           "Promo days waste about the same share as normal days: more cups, because they sell more.")
