"""Shared app helpers: load outputs, number formats, page layout, chart style and the sidebar."""
import math
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DOCS = ROOT / "docs"
XLSX = OUT / "FruitBlend24_PnL.xlsx"

APP_NAME = "FruitBlend24 case study"
AUTHOR = "Ratthapak Sinsiri"
GITHUB_URL = "https://github.com/belseris/fruitblend24-case-study"
LIVE_APP_URL = ""  # TODO: paste the Streamlit Cloud link after the first deploy.

ITEMS = ["Watermelon", "Pineapple", "Guava", "PassionFruit", "MixedBerryPremium"]
KITCHENS = ["Pattaya_Central", "Pattaya_Beach", "BKK_Sukhumvit", "BKK_Ladprao"]
BERRY = "MixedBerryPremium"

# One highlight color per chart, the rest grey. Same blue and red as the notebooks.
KEY, LOSS, GREY, DARK, INK, MID = "#2a78d6", "#e34948", "#bdbcb6", "#52514e", "#0b0b0b", "#f0efec"
HILITE = "#e3eefb"  # table row highlight
SEQUENTIAL = [[0, "#cde2fb"], [0.5, "#5598e7"], [1, "#0d366b"]]

# Page file -> (menu title, the question the page answers). Home and navigation both read this.
HOME = ("Executive Summary", "What should we do, and what is it worth?")
PAGES = {
    "pages/1_Data_Quality.py": ("Data Quality", "Can we trust the data?"),
    "pages/2_Demand_and_Pricing.py": ("Demand and Pricing", "When and what do people buy, and is our price right?"),
    "pages/3_Promotions.py": ("Promotions", "Which promotions make money?"),
    "pages/4_PnL_and_Budget.py": ("P&L and Budget", "Where did profit go vs budget?"),
    "pages/5_Forecast_and_Inventory.py": ("Forecast and Inventory", "What will we sell Sep-Nov and how much to prep?"),
    "pages/6_Assumptions_and_Method.py": ("Assumptions and Method", "What did we assume, and how are the numbers built?"),
}
METHOD_PAGE = "pages/6_Assumptions_and_Method.py"


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
    """The decision table in docs/decisions.md as a frame."""
    rows = []
    for line in read_doc("decisions.md").splitlines():
        if line.startswith("| 20"):
            cells = [x.strip() for x in line.strip().strip("|").split(" | ")]
            rows.append(cells[:5])
    return pd.DataFrame(rows, columns=["Date", "Lesson", "Decision", "Reason", "Impact"])


def approach_note() -> tuple[Path, str]:
    """The note to download: the approach note once it exists, else the executive summary."""
    for name, label in [("approach_note.pdf", "Approach note (PDF)"), ("approach_note.md", "Approach note"),
                        ("executive_summary.md", "Executive summary")]:
        if (DOCS / name).exists():
            return DOCS / name, label
    raise FileNotFoundError("no note in docs/")


# ---- number format ----

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


def month_name(m: str) -> str:
    """'2026-09' -> 'Sep 2026'."""
    return pd.Timestamp(f"{m}-01").strftime("%b %Y")


def span(months) -> str:
    """Month range in words: 'Sep-Nov 2026' or 'Sep 2025 to Aug 2026'."""
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


# ---- page layout ----

def page_header(question: str, answer: str) -> None:
    """Page title = the question; under it the short answer, number first."""
    st.title(question)
    st.markdown(answer)


def chart_note(so_what: str) -> None:
    """One line under a chart: what it means for the business."""
    st.caption(f"So what: {so_what}")


def how_to_read(text: str) -> None:
    """Help for charts that need it (waterfall, matrix, newsvendor)."""
    with st.expander("How to read this"):
        st.markdown(text)


def method_box(text: str) -> None:
    """Method and assumptions at the bottom of a page, with a link to the decision log."""
    st.divider()
    with st.expander("Method and assumptions"):
        st.markdown(text)
        st.page_link(METHOD_PAGE, label="All decisions, glossary and data limits")


def download(df: pd.DataFrame, name: str, label: str = "Download this table (CSV)") -> None:
    """CSV download of the table on the page."""
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=f"{name}.csv", mime="text/csv",
                       key=f"dl_{name}", on_click="ignore")


def fit_height(n_rows: int, max_rows: int = 20) -> int | str:
    """Table height that shows every row of a short table (no inner scroll)."""
    return 35 * (n_rows + 1) + 3 if n_rows <= max_rows else "auto"


def table(df: pd.DataFrame, money=(), pcts=(), count=(), per_cup=(), dec=(), highlight=None, **kw) -> None:
    """Show a table with ฿ and % formats. Values stay numbers, so sorting still works."""
    df = df.reset_index(drop=True)
    text = df.select_dtypes(exclude="number").columns
    df[text] = df[text].fillna("")
    fmt = {**{col: thb for col in money}, **{col: pct for col in pcts}, **{col: "{:,.0f}".format for col in count},
           **{col: baht for col in per_cup}, **{col: "{:,.2f}".format for col in dec}}
    sty = df.style.format(fmt, na_rep="-")
    if highlight is not None:
        mark = pd.Series(highlight).reset_index(drop=True)
        sty = sty.apply(lambda r: [f"background-color: {HILITE}" if mark[r.name] else "" for _ in r], axis=1)
    st.dataframe(sty, hide_index=True, **({"height": fit_height(len(df))} | kw))


def pick(label: str, options: list[str], key: str, all_label: str = "All") -> str:
    """Sidebar filter with 'All' first (the default)."""
    return st.sidebar.selectbox(label, [all_label] + list(options), key=key)


# ---- charts ----

def colors(index, keys, color: str = KEY) -> list[str]:
    """Highlight color for the key bars, grey for the rest."""
    return [color if i in keys else GREY for i in index]


def money_ticks(lo: float, hi: float, n: int = 5) -> dict:
    """Axis ticks written as ฿ (-฿400k, ฿1.20M), about n steps from lo to hi."""
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    vals = [math.floor(lo / step) * step + i * step for i in range(n + 2)]
    vals = [v for v in vals if lo - step / 2 <= v <= hi + step / 2]
    return dict(tickvals=vals, ticktext=[thb(v) for v in vals])


def show(fig: go.Figure, title: str, sub: str, height: int = 420, legend: bool = False) -> None:
    """Draw a Plotly chart. Title = the finding ('; ' starts a new line), sub = what is plotted, with units."""
    text = title.replace("; ", ";<br>") + f"<br><span style='font-size:12px;color:{DARK}'>{sub}</span>"
    fig.update_layout(
        template="plotly_white", height=height, showlegend=legend, hoverlabel=dict(font_size=13),
        paper_bgcolor="white", plot_bgcolor="white",
        title=dict(text=text, x=0, xanchor="left", font=dict(size=16, color=INK)),
        margin=dict(t=100, l=10, r=10, b=90 if legend else 40), font=dict(size=13),
        # The legend sits at the bottom edge of the figure, below the x-axis title.
        legend=dict(orientation="h", yref="container", y=0.01, yanchor="bottom", x=0, xanchor="left"))
    fig.update_xaxes(gridcolor=MID, zerolinecolor=MID)
    fig.update_yaxes(gridcolor=MID, zerolinecolor=MID)
    st.plotly_chart(fig, theme=None, config={"displaylogo": False})


# ---- sidebar ----

def sidebar() -> None:
    """App info, links and downloads; shown under the page filters on every page."""
    sb = st.sidebar
    sb.divider()
    sb.markdown(f"**{APP_NAME}**  \nAnalyst case study for Atmind Group  \nby {AUTHOR}")
    links = [f"[GitHub repo]({GITHUB_URL})"] + ([f"[Live app]({LIVE_APP_URL})"] if LIVE_APP_URL else [])
    sb.markdown(" · ".join(links))
    sb.download_button("P&L workbook (xlsx)", read_bytes(XLSX), file_name=XLSX.name, key="dl_xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", on_click="ignore")
    note, label = approach_note()
    sb.download_button(label, read_bytes(note), file_name=note.name, key="dl_note",
                       mime="application/pdf" if note.suffix == ".pdf" else "text/markdown", on_click="ignore")
    sb.caption(f"Data: {data_period()}  \nLast updated: {last_updated()}")
