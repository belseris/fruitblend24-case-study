"""App tests: every page and filter runs, home KPIs equal company_pnl.csv, and the app text follows the style rules."""
import re
import sys
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import common  # noqa: E402

PAGES = list(common.PAGES)
# Full-year totals from notebook 04, section 1 and section 9 (THB): the CSV must still match the notebook.
NB04 = {"gross_revenue": 31_146_932.57, "gross_profit": 7_636_312.43, "operating_profit": -403_687.57,
        "waste_cost": 860_307.21, "budget_revenue": 32_400_000, "budget_gp": 8_400_000}
BANNED = ["let's", "dive into", "comprehensive", "robust", "leverage", "crucial", "it's worth noting",
          "in conclusion", "key takeaways", "this analysis provides"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿✅❌]")


def open_app(page: str | None = None) -> AppTest:
    """Run the app, then switch to a page if given."""
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=60)
    at.run()
    if page:
        at.switch_page(page)
        at.run()
    return at


def test_home_runs():
    at = open_app()
    assert not at.exception
    assert at.title[0].value == common.HOME.question
    assert len(at.metric) == 5
    assert not at.warning


@pytest.mark.parametrize("page", PAGES)
def test_page_and_filters_run(page):
    at = open_app(page)
    assert not at.exception, page
    assert not at.warning, page
    assert at.title[0].value == common.PAGES[page][1], "page title = the question it answers"
    # Every filter: pick its last option and run again.
    for i in range(len(at.selectbox)):
        box = at.selectbox[i]
        box.set_value(box.options[-1])
        at.run()
        assert not at.exception, f"{page}: filter {box.label} = {box.options[-1]}"


def test_kpis_equal_company_pnl():
    m = pd.read_csv(common.OUT / "company_pnl.csv")
    v = pd.read_csv(common.OUT / "budget_variance.csv")
    fy = m.sum(numeric_only=True)
    for col in ["gross_revenue", "gross_profit", "operating_profit", "waste_cost"]:
        assert abs(fy[col] - NB04[col]) < 0.01, col
    assert v["budget_revenue"].sum() == NB04["budget_revenue"] and v["budget_gp"].sum() == NB04["budget_gp"]

    shown = {x.label: x.value for x in open_app().metric}
    assert shown == {
        "Revenue": common.thb(fy["gross_revenue"]),
        "Gross profit (GP-C)": common.thb(fy["gross_profit"]),
        "GP %": common.pct(fy["gross_profit"] / fy["gross_revenue"] * 100),
        "Operating profit": common.thb(fy["operating_profit"]),
        "Waste cost": common.thb(fy["waste_cost"]),
    }
    assert shown["Revenue"] == "฿31.15M" and shown["Operating profit"] == "-฿404k"


def test_reconcile_matches():
    at = open_app("pages/1_Data_Quality.py")
    check = {x.label: x.value for x in at.metric}["Reconcile check"]
    assert check == "Matches"


def test_decision_search_filters():
    at = open_app("pages/6_Assumptions_and_Method.py")
    total = len(common.decisions())
    at.text_input(key="am_search").set_value("berry").run()
    assert not at.exception
    n = int(at.caption[0].value.split(" of ")[0])
    assert 0 < n < total


def test_money_format():
    assert common.thb(1_234_567) == "฿1.23M"
    assert common.thb(92_400) == "฿92k"
    assert common.thb(-403_688) == "-฿404k"
    assert common.thb(7_620) == "฿7.6k"
    assert common.thb(-0.2) == "฿0"
    assert common.pct(24.517) == "24.5%"


def test_app_text_style():
    """No em dashes, emojis or banned words in any app file."""
    for path in [APP / "streamlit_app.py", APP / "common.py", *sorted((APP / "pages").glob("*.py"))]:
        text = path.read_text(encoding="utf-8")
        assert "—" not in text, f"em dash in {path.name}"
        assert not EMOJI.search(text), f"emoji in {path.name}"
        low = text.lower()
        for word in BANNED:
            assert word not in low, f"'{word}' in {path.name}"
