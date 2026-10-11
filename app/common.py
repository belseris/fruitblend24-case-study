"""Shared app helpers: load outputs, number formats, cards, page layout, charts and the sidebar."""
import math
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DOCS = ROOT / "docs"
XLSX = OUT / "FruitBlend24_PnL.xlsx"

APP_NAME = "FruitBlend24 Analysis"
AUTHOR = "Ratthapak Sinsiri"
GITHUB_URL = "https://github.com/belseris/fruitblend24-case-study"
LIVE_APP_URL = "https://fruitblend24.streamlit.app"

ITEMS = ["Watermelon", "Pineapple", "Guava", "PassionFruit", "MixedBerryPremium"]
KITCHENS = ["Pattaya_Central", "Pattaya_Beach", "BKK_Sukhumvit", "BKK_Ladprao"]
BERRY = "MixedBerryPremium"

# One accent for the point of a chart, grey for context, red for losses, green only for profit above 0.
KEY, LOSS, GAIN, GREY, DARK, INK, MID = "#2a78d6", "#e34948", "#2f9e66", "#bdbcb6", "#52514e", "#0b0b0b", "#e6e5e1"
HILITE = "#e3eefb"  # table row highlight
SEQUENTIAL = [[0, "#eef4fc"], [0.5, "#5598e7"], [1, "#0d366b"]]


class PageInfo(NamedTuple):
    menu: str  # name in the sidebar menu
    question: str  # page title = the question the page answers
    step: str | None  # short name in the story bar (None = not a story step)


# Page file -> menu name, question, story step. Navigation, story bar, links and tests all read this.
HOME = PageInfo("Summary", "FruitBlend24: where profit is lost and what to do next", None)
PAGES = {
    "pages/1_Data_Quality.py": PageInfo("Data quality", "Can we trust the data?", "Trust the data"),
    "pages/2_Demand_and_Pricing.py": PageInfo("Demand and pricing", "When do people buy, and is our price right?",
                                              "Demand and price"),
    "pages/3_Promotions.py": PageInfo("Promotions", "Which promotions make money?", "Promotions"),
    "pages/4_PnL_and_Budget.py": PageInfo("Profit vs budget", "Where did profit go vs budget?", "Profit vs budget"),
    "pages/5_Forecast_and_Prep.py": PageInfo("Forecast and prep",
                                             "What will we sell in Sep-Nov, and how much should we prep?",
                                             "Forecast and prep"),
    "pages/6_Action_Plan.py": PageInfo("Action plan", "What is Sep-Nov profit with and without the plan?",
                                       "Action plan"),
    "pages/7_Assumptions_and_Method.py": PageInfo("Assumptions and method",
                                                  "What did we assume, and how are the numbers built?", None),
}
DQ, DEMAND, PROMO_PAGE, PNL, FORECAST, ACTION, METHOD = PAGES
STORY = [p for p, info in PAGES.items() if info.step]

PROMO = {"RC101": "Bundle (RC101)", "RC102": "Double day (RC102)", "RC103": "Rainy season (RC103)"}

# Column name on screen for every table. Columns not listed lose their "_" (see label()).
NAMES = {
    "gross_revenue": "Revenue", "gross_profit": "Gross profit", "operating_profit": "Operating profit",
    "overhead": "Overhead", "waste_cost": "Waste cost", "waste_rate_pct": "Waste rate", "gp_pct": "GP %",
    "thb_month_low": "฿ a month (low)", "thb_month_high": "฿ a month (high)", "thb_per_month": "฿ a month",
    "in_plan": "In plan", "in_model": "In model", "kind": "Type", "level": "Level", "rows": "Rows", "cups": "Cups",
    "sku": "Item", "kitchen": "Kitchen", "month": "Month", "table": "Table", "category": "Category",
    "issue": "Issue", "effect": "Effect", "action": "Action", "confidence": "Confidence", "revenue_thb": "Revenue",
    "cost_thb": "Cost filled", "pct_rows": "% of rows", "item_name_raw": "Raw name", "step": "Step",
    "owner": "Owner", "start_date": "Start", "kpi": "KPI to watch", "stop_rule": "Stop rule", "name": "Name",
    "problem": "Problem", "cause": "Cause", "note": "Note", "source": "Source", "sold": "Sold", "wasted": "Wasted",
    "revenue_change_thb": "Revenue changed", "budget_revenue": "Budget revenue", "budget_gp": "Budget GP", "gp_var": "GP vs budget",
    "revenue_effect": "Revenue effect", "margin_effect": "Margin effect", "line": "Step", "code": "Promo",
    "platform": "Platform", "decision": "Decision", "change": "Change", "promo_days": "Promo days",
    "main_risk": "Main risk", "rule": "Rule", "demand": "Demand", "prep_cups": "Prep (cups)",
    "waste_cups": "Wasted (cups)", "short_cups": "Short (cups)", "fruit_budget_thb": "Fruit budget",
    "thb_per_month_waste": "Waste a month", "elasticity_-1.5": "฿ a month (elasticity -1.5)",
    "elasticity_-0.5": "฿ a month (elasticity -0.5)", "examples": "Examples", "revenue": "Revenue",
    "gp_month": "Gross profit a month", "overhead_month": "Overhead a month", "op_month": "Operating profit a month",
    "cut_needed": "Overhead cut to break even", "cut_pct": "Cut as % of overhead",
}


# ---- data ----

@st.cache_data
def load(name: str) -> pd.DataFrame:
    """Read one table from outputs/ (the app never reads raw data)."""
    return pd.read_csv(OUT / f"{name}.csv")


@st.cache_data
def read_doc(name: str) -> str:
    """Read a markdown file from docs/."""
    return (DOCS / name).read_text(encoding="utf-8")


@st.cache_data
def read_bytes(path: Path) -> bytes:
    """File content for a download button."""
    return Path(path).read_bytes()


@st.cache_data
def decisions() -> pd.DataFrame:
    """The decision table in docs/decisions.md as a frame. The file's 'Lesson' column is shown as 'Step'."""
    rows = []
    for line in read_doc("decisions.md").splitlines():
        if line.startswith("| 20"):
            cells = [x.strip() for x in line.strip().strip("|").split(" | ")]
            rows.append(cells[:5])
    return pd.DataFrame(rows, columns=["Date", "Step", "Decision", "Reason", "Impact"])


@st.cache_data
def action_gap() -> dict:
    """Sep-Nov after all actions: what is still lost a month, for the company and for Bangkok."""
    ss, sc = load("scenario_summary"), load("scenarios")
    overhead = load("kitchen_pnl").groupby("kitchen")["overhead"].mean()
    n = ss["month"].nunique()
    bkk_oh = overhead.filter(like="BKK").sum()
    bkk_gp = sc[(sc["scenario"] == "Action") & sc["kitchen"].str.startswith("BKK")]["gross_profit"].sum()
    company = ss.loc[ss["scenario"] == "Action", "operating_profit"].sum() / n
    review = load("recommendations").set_index("area").get("thb_month_high", pd.Series(dtype=float))
    return {"company_month": company, "bkk_month": bkk_gp / n - bkk_oh, "bkk_overhead": bkk_oh,
            "share_of_bkk_overhead": -company / bkk_oh * 100 if bkk_oh else float("nan"),
            "review_high": review.get("Kitchens", float("nan"))}


@st.cache_data
def breakeven_by_kitchen(scenario: str = "Action") -> pd.DataFrame:
    """Per kitchen, a month in the forecast months: gross profit, overhead, and the overhead cut that reaches 0."""
    sc = load("scenarios")
    months = load("scenario_summary")["month"].nunique()
    gp = sc[sc["scenario"] == scenario].groupby("kitchen")["gross_profit"].sum() / months
    overhead = load("kitchen_pnl").groupby("kitchen")["overhead"].mean()
    t = pd.DataFrame({"gp_month": gp, "overhead_month": overhead}).reindex(KITCHENS)
    t["op_month"] = t["gp_month"] - t["overhead_month"]
    t["cut_needed"] = (-t["op_month"]).clip(lower=0)
    t["cut_pct"] = t["cut_needed"] / t["overhead_month"] * 100
    return t.rename_axis("kitchen").reset_index()


def approach_note() -> tuple[Path, str] | None:
    """The note to download: the approach note once it exists, else the executive summary."""
    for name, label in [("approach_note.pdf", "Approach note (PDF)"), ("approach_note.md", "Approach note"),
                        ("executive_summary.md", "Executive summary")]:
        if (DOCS / name).exists():
            return DOCS / name, label
    return None


# ---- number and text format ----

def thb(x: float) -> str:
    """Money in short form: ฿31.15M, -฿404k, ฿7.6k, ฿457."""
    a = abs(x)
    if a >= 1e6:
        body = f"{a / 1e6:,.2f}M"
    elif a >= 1e4:
        body = f"{a / 1e3:,.0f}k"
    elif a >= 1e3:
        body = f"{a / 1e3:,.1f}k"
    else:
        body = f"{a:,.0f}"
    zero = body.strip("0.k") == ""
    return f"{'-' if x < 0 and not zero else ''}฿{body}"


def sthb(x: float) -> str:
    """Money with a sign: +฿92k, -฿764k."""
    return ("+" if x > 0 else "") + thb(x)


def thb_range(lo: float, hi: float) -> str:
    """A low-high money range: +฿27k to +฿52k (one value if both are the same)."""
    return sthb(lo) if thb(lo) == thb(hi) else f"{sthb(lo)} to {sthb(hi)}"


def thb_full(x: float) -> str:
    """Exact money for checks: ฿31,276,898.60."""
    return f"{'-' if x < 0 else ''}฿{abs(x):,.2f}"


def baht(x: float, digits: int = 2) -> str:
    """Money per cup: ฿13.14, -฿1.92."""
    return f"{'-' if x < 0 else ''}฿{abs(x):,.{digits}f}"


def pct(x: float, digits: int = 1) -> str:
    """A percent value: 24.5%."""
    return f"{x:,.{digits}f}%"


def spct(x: float, digits: int = 1) -> str:
    """A percent change with a sign: +1.2%."""
    return f"{x:+,.{digits}f}%"


def pts(x: float) -> str:
    """A change in percentage points: +1.2 pts."""
    return f"{x:+.1f} pts"


def month_name(m: str) -> str:
    """'2026-09' -> 'Sep 2026'."""
    return pd.Timestamp(f"{str(m)[:7]}-01").strftime("%b %Y")


def month_short(m: str) -> str:
    """'2026-09' -> 'Sep 26' (for axes and table columns)."""
    return pd.Timestamp(f"{str(m)[:7]}-01").strftime("%b %y")


def span(months) -> str:
    """Month range in words: 'Sep-Nov 2026' or 'Sep 2025 to Aug 2026'."""
    months = [str(m)[:7] for m in months]
    if not months:
        return ""
    first, last = pd.Timestamp(f"{min(months)}-01"), pd.Timestamp(f"{max(months)}-01")
    if first.year == last.year:
        return f"{first:%b}-{last:%b %Y}"
    return f"{first:%b %Y} to {last:%b %Y}"


def data_period() -> str:
    """The months the data covers, from the P&L."""
    return span(load("company_pnl")["month"])


def last_updated() -> str:
    """Date of the newest file in outputs/."""
    newest = max(p.stat().st_mtime for p in OUT.iterdir() if p.is_file())
    return datetime.fromtimestamp(newest).strftime("%d %b %Y")


def promo(text: str) -> str:
    """Write promo codes with their names: RC101 -> Bundle (RC101). Safe to call twice."""
    text = str(text)

    def name(m):
        code = m.group()
        named = PROMO[code].removesuffix(f"{code})")  # 'Bundle (': the code already has its name
        return code if text[:m.start()].endswith(named) else PROMO[code]

    return re.sub(r"\bRC10[123]\b", name, text)


def short_item(s: str) -> str:
    """MixedBerryPremium -> berry, for running text."""
    return str(s).replace(BERRY, "berry")


def title_case(s: str) -> str:
    """Decision values on screen: 'keep + test' -> 'Keep + test'."""
    s = str(s)
    return s[:1].upper() + s[1:]


def join(words, empty: str = "none") -> str:
    """['a', 'b', 'c'] -> 'a, b and c'. Safe for an empty list."""
    words = [str(w) for w in words]
    if not words:
        return empty
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"


def label(col: str) -> str:
    """Column name on screen: no snake_case."""
    if col in NAMES:
        return NAMES[col]
    return title_case(col.replace("_", " ")) if "_" in col else col


# ---- page layout ----

def config() -> None:
    """Same page setup on every page."""
    st.set_page_config(page_title=APP_NAME, layout="wide")


def story_bar(current: str | None = None) -> None:
    """The 6 steps of the story in one row; the current step is highlighted, the others are links."""
    with st.container(horizontal=True, gap="small", vertical_alignment="center"):
        for i, page in enumerate(STORY, 1):
            text = f"{i} {PAGES[page].step}"
            if page == current:
                st.badge(text, color="primary")
            else:
                st.page_link(page, label=text)


def page_header(page: str, answer: str) -> None:
    """Story bar, then title = the question, then the answer (max 2 sentences, number first)."""
    config()
    story_bar(page)
    st.title(PAGES[page].question)
    st.markdown(answer)
    st.session_state["page_answer"] = answer  # the tests check its length and words


def next_page(page: str, label: str | None = None) -> None:
    """Link to the next step at the bottom of a page."""
    st.divider()
    st.page_link(page, label=label or f"Next: {PAGES[page].question}")


@contextmanager
def card(title: str, so_what: str | None = None, how_to_read: str | None = None, method: str | None = None):
    """A bordered card: finding as the title, help in popovers, 'So what' at the bottom."""
    with st.container(border=True):
        # A wrapping row: the title takes the full width and the help buttons sit on the right under it.
        # A no-wrap row would squeeze the title and show a scrollbar in narrow cards.
        with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small"):
            st.markdown(f"**{title}**", width="stretch")
            if how_to_read:
                with st.popover("How to read"):
                    st.markdown(how_to_read)
            if method:
                with st.popover("Method"):
                    st.markdown(method)
        yield
        if so_what:
            st.caption(f"So what: {so_what}")


def kpi(label: str, value: str, delta: str | None = None, series=None, help: str | None = None, **kw) -> None:
    """A KPI tile with an optional area sparkline (series = values over time, oldest first)."""
    chart = None if series is None else [float(x) for x in series]
    st.metric(label, value, delta, border=True, help=help, chart_data=chart, chart_type="area", height="stretch",
              **kw)


def kpi_row(tiles: list[dict]) -> None:
    """KPI tiles side by side; each dict holds kpi() arguments."""
    for col, tile in zip(st.columns(len(tiles)), tiles):
        with col:
            kpi(**tile)


def best_worst(what: str, best_label: str, best: str, worst_label: str, worst: str) -> None:
    """Best and worst of one kind (kitchen, item) on two short lines."""
    st.markdown(f"Best {what}: **{best_label}** :green[{best}]  \nWorst {what}: **{worst_label}** :red[{worst}]")


def choose(label: str, options: list[str], key: str, all_label: str | None = "All") -> str:
    """A pill control for one chart or table; 'All' first and selected by default."""
    opts = ([all_label] if all_label else []) + list(options)
    return st.pills(label, opts, default=opts[0], required=True, key=key, width="stretch")


def download(df: pd.DataFrame, name: str, label: str = "Download this table (CSV)") -> None:
    """CSV download of a table."""
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=f"{name}.csv", mime="text/csv",
                       key=f"dl_{name}", on_click="ignore")


def fit_height(n_rows: int, max_rows: int = 20) -> int | str:
    """Table height that shows every row of a short table (no inner scroll)."""
    return 35 * (n_rows + 1) + 3 if n_rows <= max_rows else "auto"


def _draw(df: pd.DataFrame, money, pcts, count, per_cup, dec, exact, highlight, static=False, **kw) -> None:
    """Draw one formatted table with screen names. static = a plain table that wraps long text."""
    df = df.reset_index(drop=True)
    for col in df.columns[df.dtypes == bool]:
        df[col] = df[col].map({True: "Yes", False: "No"})
    text = df.select_dtypes(exclude="number").columns
    df[text] = df[text].fillna("").map(promo)  # promo codes always with their names
    fmt = {**{col: thb for col in money}, **{col: pct for col in pcts}, **{col: "{:,.0f}".format for col in count},
           **{col: baht for col in per_cup}, **{col: "{:,.2f}".format for col in dec},
           **{col: thb_full for col in exact}}
    fmt = {label(col): f for col, f in fmt.items() if col in df.columns}
    df = df.rename(columns=label)
    sty = df.style.format(fmt, na_rep="-")
    if highlight is not None:
        mark = pd.Series(highlight).reset_index(drop=True)
        sty = sty.apply(lambda r: [f"background-color: {HILITE}" if mark[r.name] else "" for _ in r], axis=1)
    if static:
        st.table(sty.hide(axis="index"), border="horizontal")
        return
    if "column_config" in kw:
        kw["column_config"] = {label(k): v for k, v in kw["column_config"].items()}
    st.dataframe(sty, hide_index=True, **({"height": fit_height(len(df))} | kw))


def table(df: pd.DataFrame, money=(), pcts=(), count=(), per_cup=(), dec=(), exact=(), highlight=None, cols=None,
          name: str | None = None, raw: pd.DataFrame | None = None, **kw) -> None:
    """Show a table with screen names and ฿/% formats (values stay numbers, so sorting works).

    cols = the few columns that make the point; then the full table goes in a 'Full table' expander.
    static=True draws a plain table that wraps long text (for action and rule columns).
    name = file name of the CSV download; raw = the frame to download if not df.
    """
    fmt = dict(money=money, pcts=pcts, count=count, per_cup=per_cup, dec=dec, exact=exact, highlight=highlight)
    wide = cols is not None and len(cols) < len(df.columns)
    _draw(df[list(cols)] if wide else df, **fmt, **kw)
    if wide:
        with st.expander("Full table"):
            _draw(df, **fmt, **{k: v for k, v in kw.items() if k != "column_config"})
            if name:
                download(df if raw is None else raw, name)
    elif name:
        download(df if raw is None else raw, name)


# ---- charts ----

def colors(index, keys, color: str = KEY) -> list[str]:
    """Accent color for the key bars, grey for the rest."""
    return [color if i in keys else GREY for i in index]


def money_ticks(lo: float, hi: float, n: int = 5) -> dict:
    """Axis ticks written as ฿ (-฿400k, ฿1.20M), about n steps from lo to hi."""
    raw = (hi - lo) / n
    if raw <= 0:
        return {}
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    vals = [math.floor(lo / step) * step + i * step for i in range(n + 2)]
    vals = [v for v in vals if lo - step / 2 <= v <= hi + step / 2]
    return dict(tickvals=vals, ticktext=[thb(v) for v in vals])


def show(fig: go.Figure, height: int = 360, legend: bool = False, key: str | None = None) -> None:
    """Draw a Plotly chart in the app style: no title (the card has it), transparent, small margins."""
    fig.update_layout(
        height=height, showlegend=legend, title=None, hoverlabel=dict(font_size=13),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=36 if legend else 8, l=4, r=8, b=4),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, xanchor="left", title=None))
    fig.update_xaxes(gridcolor=MID, zerolinecolor=MID, automargin=True)
    fig.update_yaxes(gridcolor=MID, zerolinecolor=MID, automargin=True)
    st.plotly_chart(fig, theme="streamlit", key=key, config={"displaylogo": False, "displayModeBar": False})


def area_around_zero(x: list[str], y: list[float]) -> go.Figure:
    """Profit over time as an area: green above 0, red below 0 (the line crosses 0 between points)."""
    xs, ys = list(range(len(y))), list(y)
    px, py = [], []  # points with the 0 crossings added, so each color stops exactly at 0
    for i in range(len(ys)):
        if i and (ys[i - 1] < 0) != (ys[i] < 0):
            t = ys[i - 1] / (ys[i - 1] - ys[i])
            px.append(xs[i - 1] + t)
            py.append(0.0)
        px.append(xs[i])
        py.append(ys[i])
    fig = go.Figure()
    fig.add_scatter(x=px, y=[max(v, 0) for v in py], fill="tozeroy", mode="none", fillcolor="rgba(47,158,102,0.35)",
                    hoverinfo="skip")
    fig.add_scatter(x=px, y=[min(v, 0) for v in py], fill="tozeroy", mode="none", fillcolor="rgba(227,73,72,0.35)",
                    hoverinfo="skip")
    fig.add_scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=DARK, width=1.5), marker=dict(size=4),
                    customdata=[[m, thb(v)] for m, v in zip(x, ys)],
                    hovertemplate="%{customdata[0]}<br>%{customdata[1]}<extra></extra>")
    fig.add_hline(y=0, line=dict(color=DARK, width=1))
    ends = [0, len(x) - 1] if x else []
    fig.update_xaxes(tickvals=ends, ticktext=[x[i] for i in ends], tickangle=0, showgrid=False)
    return fig


# ---- sidebar ----

def sidebar() -> None:
    """App info, links and downloads; the same on every page."""
    sb = st.sidebar
    sb.divider()
    sb.markdown(f"**{APP_NAME}**  \nAnalyst case study for Atmind Group  \nby {AUTHOR}")
    links = [f"[GitHub repo]({GITHUB_URL})"] + ([f"[Live app]({LIVE_APP_URL})"] if LIVE_APP_URL else [])
    sb.markdown(" · ".join(links))
    if XLSX.exists():
        sb.download_button("Download FruitBlend24_PnL.xlsx", read_bytes(XLSX), file_name=XLSX.name, key="dl_xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           on_click="ignore")
    note = approach_note()
    if note:
        path, text = note
        sb.download_button(f"Download {text.lower()}", read_bytes(path), file_name=path.name, key="dl_note",
                           mime="application/pdf" if path.suffix == ".pdf" else "text/markdown", on_click="ignore")
    sb.caption(f"Data period: {data_period()}  \nLast updated: {last_updated()}")

