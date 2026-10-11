"""App tests: every page and control runs, home KPIs equal company_pnl.csv, and the screen text follows the rules."""
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
# Terms a page answer may not use before the page explains them.
TERMS = re.compile(r"\b(CM|GP-C|CR|WAPE)\b|break-even", re.IGNORECASE)


def open_app(page: str | None = None) -> AppTest:
    """Run the app, then switch to a page if given."""
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=60)
    at.run()
    if page:
        at.switch_page(page)
        at.run()
    return at


def tables(at: AppTest) -> list[pd.DataFrame]:
    """Every table and dataframe on the page, as frames."""
    return [x.value for x in list(at.dataframe) + list(at.table)]


def screen_text(at: AppTest) -> list[str]:
    """Titles, markdown and captions on the page."""
    return [x.value for x in list(at.title) + list(at.markdown) + list(at.caption)]


def test_home_runs():
    at = open_app()
    assert not at.exception
    assert at.title[0].value == common.HOME.question
    assert len(at.metric) == 5
    assert not at.warning


@pytest.mark.parametrize("page", PAGES)
def test_page_and_controls_run(page):
    at = open_app(page)
    assert not at.exception, page
    assert not at.warning, page
    assert at.title[0].value == common.PAGES[page].question, "page title = the question it answers"
    # Every control: pick its last option and run again.
    for kind in ["selectbox", "pills", "segmented_control"]:
        for i in range(len(getattr(at, kind))):
            box = getattr(at, kind)[i]
            last = box.options[-1] if kind == "selectbox" else box.proto.options[-1].content
            box.set_value(last)
            at.run()
            assert not at.exception, f"{page}: {kind} {box.label} = {last}"


@pytest.mark.parametrize("page", PAGES)
def test_page_answer_is_short(page):
    at = open_app(page)
    answer = at.session_state["page_answer"].replace("**", "")
    assert len(answer.split()) <= 35, f"{page}: {len(answer.split())} words"
    assert len(re.findall(r"[.!?](\s|$)", answer)) <= 2, f"{page}: more than 2 sentences"
    assert not TERMS.search(answer), f"{page}: term in the answer before it is explained"


@pytest.mark.parametrize("page", [None] + PAGES)
def test_no_snake_case_on_screen(page):
    at = open_app(page)
    for df in tables(at):
        names = [str(x) for x in df.columns] + [str(x) for x in df.index.names if x]
        assert not [n for n in names if "_" in n], f"{page}: {names}"
    # Promo codes always carry their name: 'Bundle (RC101)', never a bare 'RC101'.
    for text in screen_text(at):
        assert not re.search(r"(?<!\()\bRC10[123]\b", text), f"{page}: bare promo code in '{text[:80]}'"


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
    at = open_app(common.DQ)
    check = {x.label: x.value for x in at.metric}["Reconcile check"]
    assert check == "Matches"


def test_action_plan_kpis_equal_scenarios():
    ss = pd.read_csv(common.OUT / "scenario_summary.csv")
    three = ss.groupby("scenario")["operating_profit"].sum()
    shown = {x.label: x.value for x in open_app(common.ACTION).metric}
    assert shown == {s: common.thb(v) for s, v in three.items()}


def test_decision_search_filters():
    at = open_app(common.METHOD)
    total = len(common.decisions())
    at.text_input(key="am_search").set_value("berry").run()
    assert not at.exception
    n = next(int(x.value.split(" of ")[0]) for x in at.caption if " decisions." in x.value)
    assert 0 < n < total


def test_money_format():
    assert common.thb(1_234_567) == "฿1.23M"
    assert common.thb(92_400) == "฿92k"
    assert common.thb(-403_688) == "-฿404k"
    assert common.thb(7_620) == "฿7.6k"
    assert common.thb(-0.2) == "฿0"
    assert common.pct(24.517) == "24.5%"
    assert common.pts(1.234) == "+1.2 pts"
    assert common.promo("RC101 and Double day (RC102)") == "Bundle (RC101) and Double day (RC102)"
    assert common.join([]) == "none" and common.span([]) == ""


def test_app_text_style():
    """No em dashes, emojis or banned words in any app file."""
    for path in [APP / "streamlit_app.py", APP / "common.py", *sorted((APP / "pages").glob("*.py"))]:
        text = path.read_text(encoding="utf-8")
        assert "—" not in text, f"em dash in {path.name}"
        assert not EMOJI.search(text), f"emoji in {path.name}"
        low = text.lower()
        for word in BANNED:
            assert word not in low, f"'{word}' in {path.name}"
