"""FruitBlend24 case app: executive summary page and navigation."""
import plotly.graph_objects as go
import streamlit as st

import common as c

st.set_page_config(page_title="FruitBlend24 case", layout="wide")


def kpis():
    """FY numbers for the 4 KPI tiles (same as notebook 04)."""
    m = c.load("company_pnl")
    v = c.load("budget_variance")
    rev, gp, op, waste = (m[col].sum() for col in ["gross_revenue", "gross_profit", "operating_profit", "waste_cost"])
    return {"revenue": rev, "budget_revenue": v["budget_revenue"].sum(), "gp": gp, "budget_gp": v["budget_gp"].sum(),
            "op": op, "waste_month": waste / 12, "waste_pct": waste / rev * 100}


def bottom_line() -> str:
    """The 'Bottom line' section of docs/executive_summary.md, so the app and the doc say the same."""
    text = c.read_doc("executive_summary.md")
    part = text.split("## Bottom line", 1)[1].split("\n## ", 1)[0]
    return part.strip()


def summary_page():
    c.header("FruitBlend24: executive summary",
             "12 months of online orders (Sep 2025 to Aug 2026), 4 kitchens, LINE MAN and Grab. Money in THB. "
             "GP = after discount, commission, fruit, packaging + labor and waste.")
    k = kpis()
    cols = st.columns(4)
    rev_gap, gp_gap = k["revenue"] - k["budget_revenue"], k["gp"] - k["budget_gp"]
    cols[0].metric("Revenue (FY)", c.thb(k["revenue"]),
                   f"{c.thb(rev_gap)} ({rev_gap / k['budget_revenue'] * 100:.1f}%) vs budget", border=True)
    cols[1].metric("Gross profit (FY)", c.thb(k["gp"]),
                   f"{c.thb(gp_gap)} ({gp_gap / k['budget_gp'] * 100:.1f}%) vs budget", border=True)
    cols[2].metric("Operating profit (FY)", c.thb(k["op"]),
                   f"{k['op'] / k['revenue'] * 100:.1f}% of revenue, after 8.04M overhead", border=True)
    cols[3].metric("Waste per month", c.thb(k["waste_month"], 1),
                   f"{k['waste_pct']:.1f}% of revenue", delta_color="inverse", border=True)

    st.subheader("Bottom line")
    st.markdown(bottom_line())

    st.subheader("Five insights")
    for _, r in c.load("insights").iterrows():
        st.markdown(f"**{r['rank']}. {r['title']}**  \n{r['evidence']}  \n"
                    f"<span style='color:{c.TOTAL};font-size:0.85em'>Chart: {r['chart']} · "
                    f"confidence: {r['confidence']}</span>", unsafe_allow_html=True)

    st.subheader("Recommendations")
    rec = c.load("recommendations")
    rec["THB a month"] = [f"{c.thb(lo, 1)} to {c.thb(hi, 1)}" if lo != hi else c.thb(lo, 1)
                          for lo, hi in zip(rec["thb_month_low"], rec["thb_month_high"])]
    st.dataframe(rec[["area", "action", "THB a month", "in_total", "confidence", "key_assumption", "owner"]],
                 hide_index=True)
    st.caption("THB a month = change in operating profit vs today, Sep-Nov 2026, elasticity -1.5 (low) to -0.5 (high). "
               "The total comes from one scenario model, not from adding rows.")

    v = c.load("budget_variance")
    miss = (v["gp_var"] < 0).sum()
    worst = v.nsmallest(3, "gp_var")
    fig = go.Figure()
    fig.add_bar(x=v["month"], y=v["gross_profit"] / 1000, name="Actual GP", marker_color=c.UP,
                hovertemplate="%{x}<br>Actual %{y:,.0f}k<extra></extra>")
    fig.add_scatter(x=v["month"], y=v["budget_gp"] / 1000, name="Budget GP", mode="lines",
                    line=dict(color=c.TOTAL, width=2, dash="dash"), hovertemplate="Budget %{y:,.0f}k<extra></extra>")
    fig.update_yaxes(title="THB thousands")
    c.show(fig, f"GP misses budget in {miss} of 12 months; Jun-Aug miss most "
                f"({-worst['gp_var'].max() / 1000:,.0f}k to {-worst['gp_var'].min() / 1000:,.0f}k a month)",
           "Gross profit vs the flat budget of 700k a month, THB thousands")


pages = [
    st.Page(summary_page, title="Executive Summary", default=True),
    st.Page("pages/1_Data_Quality.py", title="Data Quality"),
    st.Page("pages/2_Demand_and_Pricing.py", title="Demand and Pricing"),
    st.Page("pages/3_Promotions.py", title="Promotions"),
    st.Page("pages/4_PnL_and_Budget.py", title="P&L and Budget"),
    st.Page("pages/5_Forecast_and_Inventory.py", title="Forecast and Inventory"),
    st.Page("pages/6_Assumptions_and_Method.py", title="Assumptions and Method"),
]
st.navigation(pages).run()
