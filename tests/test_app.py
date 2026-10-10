"""App tests: every page and filter runs without an exception; page 0 KPIs equal notebook 04."""
import sys
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import common  # noqa: E402

PAGES = ["pages/1_Data_Quality.py", "pages/2_Demand_and_Pricing.py", "pages/3_Promotions.py",
         "pages/4_PnL_and_Budget.py", "pages/5_Forecast_and_Inventory.py", "pages/6_Assumptions_and_Method.py"]
# Full-year totals from notebook 04, section 1 and section 9 (THB).
NB04 = {"revenue": 31_146_932.57, "gp": 7_636_312.43, "op": -403_687.57, "waste": 860_307.21,
        "budget_revenue": 32_400_000, "budget_gp": 8_400_000}


def open_app(page: str | None = None) -> AppTest:
    """Run the app, then switch to a page if given."""
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=60)
    at.run()
    if page:
        at.switch_page(page)
        at.run()
    return at


def test_summary_page_runs():
    at = open_app()
    assert not at.exception
    assert len(at.metric) == 4


@pytest.mark.parametrize("page", PAGES)
def test_page_and_filters_run(page):
    at = open_app(page)
    assert not at.exception, page
    assert at.title, f"{page} has no title"
    # Every sidebar filter: pick its last option and run again.
    for i in range(len(at.sidebar.selectbox)):
        box = at.sidebar.selectbox[i]
        box.set_value(box.options[-1])
        at.run()
        assert not at.exception, f"{page}: filter {box.label} = {box.options[-1]}"


def test_kpis_match_notebook_04():
    m = pd.read_csv(common.OUT / "company_pnl.csv")
    v = pd.read_csv(common.OUT / "budget_variance.csv")
    assert abs(m["gross_revenue"].sum() - NB04["revenue"]) < 0.01
    assert abs(m["gross_profit"].sum() - NB04["gp"]) < 0.01
    assert abs(m["operating_profit"].sum() - NB04["op"]) < 0.01
    assert abs(m["waste_cost"].sum() - NB04["waste"]) < 0.01
    assert v["budget_revenue"].sum() == NB04["budget_revenue"] and v["budget_gp"].sum() == NB04["budget_gp"]

    shown = {x.label: x.value for x in open_app().metric}
    assert shown["Revenue (FY)"] == common.thb(NB04["revenue"]) == "31.15M"
    assert shown["Gross profit (FY)"] == common.thb(NB04["gp"]) == "7.64M"
    assert shown["Operating profit (FY)"] == common.thb(NB04["op"]) == "-404k"
    assert shown["Waste per month"] == common.thb(NB04["waste"] / 12, 1) == "71.7k"
