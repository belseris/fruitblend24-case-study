"""Assumptions and method: decision log, definitions, limits and next steps."""
import pandas as pd
import streamlit as st

import common as c

c.header("Assumptions and method", "Every judgment call with its reason and impact, how the numbers are built, "
                                   "and what the data cannot tell us.")


def decisions() -> pd.DataFrame:
    """Parse the table in docs/decisions.md into a frame."""
    rows = []
    for line in c.read_doc("decisions.md").splitlines():
        if line.startswith("| 20"):
            cells = [x.strip() for x in line.strip().strip("|").split(" | ")]
            rows.append(cells[:5])
    return pd.DataFrame(rows, columns=["Date", "Lesson", "Decision", "Reason", "Impact"])


st.subheader("Decision log")
d = decisions()
lessons = sorted(d["Lesson"].unique(), key=lambda x: int(x) if x.isdigit() else 99)
pick = st.selectbox("Lesson", ["All"] + lessons, key="am_lesson")
shown = d if pick == "All" else d[d["Lesson"] == pick]
st.caption(f"{len(shown)} of {len(d)} decisions. Source: docs/decisions.md")
st.dataframe(shown, hide_index=True, column_config={
    "Decision": st.column_config.TextColumn(width="large"), "Reason": st.column_config.TextColumn(width="large"),
    "Impact": st.column_config.TextColumn(width="medium")})

st.subheader("How the numbers are built")
st.markdown("""
- **Cleaning:** 742 rows dropped (372 exact copies, 370 non-menu names), 31 raw names mapped to 5 items, raw - removed = clean to 0.01 THB.
- **Gross revenue** = price after discount x cups. **Commission** = gross revenue x platform rate (LINE MAN 30%, Grab 24%).
- **CM (GP-B)** = net revenue - fruit (weekly cost per cup) - packaging + labor. **GP-C** = CM - waste (main definition).
- **Operating profit** = GP-C - fixed kitchen overhead (670k a month). Overhead is never split to items.
- **Budget variance** = revenue effect (revenue gap x budget margin) + margin effect (revenue x margin gap); both checked to add up.
- **Elasticity:** log-log regression per item, RC101 bundle days vs normal price, with hour, weekday, kitchen, platform and month controls.
- **Promo value:** promo CM - baseline cups x list-price CM + waste effect + side effects; baseline = same kitchen, item, platform, month, weekday and hour on normal days.
- **Prep rule:** newsvendor critical ratio Cu / (Cu + Co); prep = that quantile of the last 8 normal same-weekday days, no look-ahead.
- **Forecast:** seasonal naive for Sep (backtest winner), Oct-Nov = Sep x 2025 month ratio, berry flat.
- **Scenarios:** one model per month x kitchen x item; levers added one at a time, so the total has no double counting.
""")

st.subheader("Limits")
st.markdown("""
- **No sold-out data.** Sales are what was sold, not what customers wanted. Today's prep looks better than it is, and the prep rule's short cups are counted as lost sales.
- **Few promo days.** Elasticities come from 3-8 bundle days per item; RC102 has 12 days. New users from promos are not measured.
- **Waste has no platform.** Platform views are before waste.
- **Berry has 6 months of history** and no rainy season of last year; its flat forecast is on the high side.
- **No grams per cup**, so plans are in cups and THB, not kilos of fruit.
- **Overhead is one number per kitchen.** We cannot tell which part can be cut.
- **One year of data.** The forecast cannot learn a season change it has never seen (Jun-Aug backtest error 45-63%).
""")

st.subheader("What I would do with more time")
st.markdown("""
1. Start a sold-out log (item, time, cups) and re-test the prep rule on the 3 cheap items after 4 weeks.
2. Run the price and promo tests with a control kitchen and read them weekly against the stop rules.
3. Get grams per cup and supplier prices to turn the prep plan into a fruit purchase plan, and a berry cost quote.
4. Split overhead into fixed and avoidable parts per kitchen, to size the Bangkok options.
5. Add order counts per platform to see basket size and test platform-only prices or promos.
""")
