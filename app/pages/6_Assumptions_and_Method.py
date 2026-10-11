"""Assumptions and method: searchable decision log, glossary, how the numbers are built, data limits."""
import pandas as pd
import streamlit as st

import common as c

d = c.decisions()
company = c.load("company_pnl")
fy = company.sum(numeric_only=True)

c.page_header(
    c.PAGES["pages/6_Assumptions_and_Method.py"][1],
    f"**{len(d)} judgment calls are logged, each with its reason and its impact in THB.** Search them below, then "
    "read the glossary and what the data cannot tell us.")

# ---- decision log ----
st.subheader("Decision log")
left, right = st.columns([3, 1])
term = left.text_input("Search decisions", placeholder="e.g. berry, waste, RC102, overhead", key="am_search")
lessons = sorted(d["Lesson"].unique(), key=lambda x: int(x) if x.isdigit() else 99)
lesson = right.selectbox("Lesson", ["All"] + lessons, key="am_lesson")
shown = d if lesson == "All" else d[d["Lesson"] == lesson]
if term:
    hit = shown.apply(lambda col: col.str.contains(term, case=False, regex=False)).any(axis=1)
    shown = shown[hit]
st.caption(f"{len(shown)} of {len(d)} decisions. Source: docs/decisions.md (Lesson = step of the case study). "
           "Click a row to read it in full below the table.")
sel = st.dataframe(shown, hide_index=True, on_select="rerun", selection_mode="single-row", key="am_table",
                   column_config={"Decision": st.column_config.TextColumn(width="large"),
                                  "Reason": st.column_config.TextColumn(width="large"),
                                  "Impact": st.column_config.TextColumn(width="medium")})
rows = sel.selection.rows if sel else []
if len(shown):
    one = shown.iloc[rows[0] if rows else 0]
    st.markdown(f"**{'Selected' if rows else 'First'} decision (lesson {one['Lesson']}, {one['Date']})**")
    st.table(one[["Decision", "Reason", "Impact"]].to_frame(), border="horizontal", hide_header=True)
c.download(shown, "decisions")

# ---- glossary ----
st.subheader("Glossary")
ue = c.load("unit_economics").query("level == 'item'").set_index("sku")
el = c.load("elasticity").query("estimate.str.startswith('1')", engine="python").set_index("sku")
ps = c.load("promo_summary").query("level == 'code_platform'").groupby("base_code")[
    ["cm_thb_if_full_price", "cm_thb_promo"]].sum()
fb = c.load("forecast_backtest")
win = fb[fb["test"].str.startswith("Jun-Aug") & (fb["sku"] == "All") & fb["winner"]].iloc[0]
rb = c.load("prep_rule_backtest").query("variant == 'CR' and sku != 'All'").drop_duplicates("sku").set_index("sku")
rev = fy["gross_revenue"]
w_e = el.loc["Watermelon", "elasticity"]
gloss = pd.DataFrame([
    ("CM (contribution margin)", "What one cup leaves after platform commission, fruit and packaging + labor. "
     "Before waste.", f"Watermelon {c.baht(ue.loc['Watermelon', 'cm_per_cup'])} a cup"),
    ("GP-A", "Revenue - fruit - packaging + labor. Ignores commission and waste.", c.pct(fy["gp_a"] / rev * 100)),
    ("GP-B", "GP-A - platform commission. Same as total CM.", c.pct(fy["gp_b"] / rev * 100)),
    ("GP-C (our gross profit)", "GP-B - waste. The main definition in this app.",
     f"{c.thb(fy['gross_profit'])} ({c.pct(fy['gross_profit'] / rev * 100)})"),
    ("Operating profit", "GP-C - fixed kitchen overhead (rent, staff). Used to judge kitchens, never items.",
     c.thb(fy["operating_profit"])),
    ("Elasticity", "% change in cups when the price goes up 1%. Closer to 0 = customers care less about price.",
     f"Watermelon {w_e:.2f}: a 10% higher price sells about {abs(w_e) * 10:.0f}% fewer cups"),
    ("Break-even lift", "How many more cups a promo must sell to earn the same CM as at full price.",
     f"RC102 needs {c.spct((ps.loc['RC102', 'cm_thb_if_full_price'] / ps.loc['RC102', 'cm_thb_promo'] - 1) * 100, 0)}"),
    ("WAPE", "Total forecast error as % of actual cups. Lower is better.", f"winner {c.pct(win['wape_pct'])}"),
    ("Bias", "Total forecast minus actual, as % of actual. + = the forecast is too high.",
     f"winner {c.spct(win['bias_pct'])}"),
    ("Critical ratio (CR)", "Cu / (Cu + Co): Cu = margin lost on a cup we did not have, Co = cost of a cup thrown "
     "away. The share of demand the prep should cover.",
     f"berry {rb.loc[c.BERRY, 'quantile']:.2f}, Watermelon {rb.loc['Watermelon', 'quantile']:.2f}"),
    ("Newsvendor", "The rule for stock that spoils in a day: prep up to the CR point of expected demand, not the "
     "average.", "used for berry and PassionFruit"),
], columns=["Term", "Meaning", "In this case"])
st.table(gloss, hide_index=True, border="horizontal")

# ---- how the numbers are built ----
st.subheader("How the numbers are built")
rec = c.load("reconcile").set_index("line")
names = c.load("item_mapping")
plat = c.load("unit_economics").query("level == 'item_platform'")
rate = (plat["commission_per_cup"] * plat["cups"]).groupby(plat["platform"]).sum() / \
    plat.groupby("platform")["gross_revenue_thb"].sum() * 100
oh = c.load("kitchen_pnl").groupby("kitchen")["overhead"].mean()
st.markdown(
    f"- **Cleaning:** {rec.loc['Raw orders_hourly', 'rows'] - rec.loc['Actual clean', 'rows']:,.0f} rows dropped "
    f"(exact copies and non-menu names), {len(names)} raw names mapped to "
    f"{names.loc[names['sku'] != 'DROP', 'sku'].nunique()} items, raw - removed = clean "
    f"(difference {c.thb_full(rec.loc['Difference', 'revenue_thb'])}).\n"
    f"- **Gross revenue** = price after discount x cups. **Commission** = gross revenue x platform rate ("
    + ", ".join(f"{p} {c.pct(r, 0)}" for p, r in rate.items()) + ").\n"
    "- **CM (GP-B)** = net revenue - fruit (that week's cost per cup) - packaging + labor. **GP-C** = CM - waste.\n"
    f"- **Operating profit** = GP-C - fixed kitchen overhead ({c.thb(oh.sum())} a month: "
    + ", ".join(f"{k} {c.thb(v)}" for k, v in oh.sort_values().items()) + "). Overhead is never split to items.\n"
    "- **Budget variance** = revenue effect (revenue gap x budget margin) + margin effect (revenue x margin gap); "
    "an assert checks they add up.\n"
    "- **Elasticity:** log-log regression per item, bundle days vs normal price, with hour, weekday, kitchen, "
    "platform and month controls.\n"
    "- **Promo value:** promo CM - baseline cups x full-price CM + extra waste + side effects; baseline = same "
    "kitchen, item, platform, month, weekday and hour on normal days.\n"
    "- **Prep rule:** newsvendor CR; prep = that quantile of recent same-weekday normal days, no look-ahead.\n"
    "- **Scenarios:** one model per month x kitchen x item; levers are added one at a time, so the total has no "
    "double counting.\n"
    "- **Same numbers everywhere:** the notebooks write `outputs/`; this app and the Excel P&L only read them.")

# ---- limits ----
st.subheader("What the data cannot tell us")
dec = c.load("promo_decision")
pc = c.load("promo_platform_check").set_index("code")
trend = c.load("monthly_item_trend").query("sku == @c.BERRY").sort_values("month")
berry_months = trend["month"].str[:7].tolist()
falling = (trend["cups_per_day"].diff().dropna() < 0).all()
promo_days = el["promo_days"]
bias = fb[fb["test"].str.startswith("Jun-Aug") & (fb["sku"] == "All")]["bias_pct"]
normal = pc.loc[pc.index.str.contains("normal")].iloc[0]
st.markdown(
    "- **No sold-out data.** Sales show what was sold, not what customers wanted. Today's prep looks better than it "
    "is, and the prep rule's short cups are counted as lost sales.\n"
    f"- **Few promo days.** RC102 (double day) ran on only {dec.loc[dec['code'] == 'RC102', 'promo_days'].max()} "
    f"days; elasticities rest on {promo_days.min()}-{promo_days.max()} bundle days per item. New customers from "
    "promos are not in the data.\n"
    f"- **Berry has no last year.** It is on sale since {c.month_name(berry_months[0])} ({len(berry_months)} months), "
    "so its Sep-Nov forecast cannot be checked against last year. It is held flat"
    + (", which is on the high side: its sales fell every month since launch.\n" if falling else ".\n")
    + f"- **Platform split on promo days.** On {pc.loc['RC101', 'one_platform_days']} of {pc.loc['RC101', 'item_days']} "
      f"RC101 item-days ({c.pct(pc.loc['RC101', 'one_platform_pct'], 0)}) the item sold on one app only, vs "
      f"{c.pct(normal['one_platform_pct'], 0)} on normal days (RC102 {pc.loc['RC102', 'one_platform_days']} of "
      f"{pc.loc['RC102', 'item_days']}, RC103 {pc.loc['RC103', 'one_platform_days']} of "
      f"{pc.loc['RC103', 'item_days']}). Lifts by platform are not reliable, so promos are judged per code.\n"
    "- **Waste has no platform**, so platform views are before waste.\n"
    "- **No grams per cup**, so the prep plan is in cups and THB, not kilos of fruit.\n"
    "- **Overhead is one number per kitchen.** We cannot tell which part could be cut.\n"
    f"- **One year of data.** A forecast cannot learn a season change it has never seen: every method was "
    f"{bias.min():.0f}-{bias.max():.0f}% too high in the Jun-Aug backtest.")
c.download(pc.reset_index(), "promo_platform_check", "Download the platform check (CSV)")

# ---- next ----
st.subheader("What I would do with more time")
st.markdown(
    "- Start a sold-out log (item, time, cups) in every kitchen, then re-test the prep rule on the cheap items.\n"
    "- Run the price and promo tests against a control kitchen and read them weekly against the stop rules.\n"
    "- Get grams per cup, supplier prices and an overhead split per kitchen, to turn the plan into a fruit purchase "
    "plan and size the Bangkok options.")
