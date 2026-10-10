"""Shared app helpers: load outputs, format THB, page header, chart style and colors."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DOCS = ROOT / "docs"

ITEMS = ["Watermelon", "Pineapple", "Guava", "PassionFruit", "MixedBerryPremium"]
KITCHENS = ["Pattaya_Central", "Pattaya_Beach", "BKK_Sukhumvit", "BKK_Ladprao"]
BERRY = "MixedBerryPremium"
# Same colors as the notebooks, so a chart in the app looks like the one in the notebook.
ITEM_COLORS = dict(zip(ITEMS, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
SCENARIO_COLORS = {"Base": "#52514e", "Action": "#2a78d6", "Action + delist berry": "#1baf7a", "Downside": "#e34948"}
UP, DOWN, TOTAL, MID, INK = "#2a78d6", "#e34948", "#52514e", "#f0efec", "#0b0b0b"
DIVERGING = [[0, DOWN], [0.5, MID], [1, UP]]
SEQUENTIAL = [[0, "#cde2fb"], [0.5, "#5598e7"], [1, "#0d366b"]]
OVERHEAD_MONTH = 670_000


@st.cache_data
def load(name: str) -> pd.DataFrame:
    """Read one table from outputs/ (the app never reads raw data)."""
    return pd.read_csv(OUT / f"{name}.csv")


@st.cache_data
def read_doc(name: str) -> str:
    """Read a markdown file from docs/."""
    return (DOCS / name).read_text(encoding="utf-8")


def thb(x: float, digits: int | None = None) -> str:
    """THB in short form: 31.15M, -404k, 860."""
    a = abs(x)
    if a >= 1e6:
        return f"{x / 1e6:,.{2 if digits is None else digits}f}M"
    if a >= 1e3:
        return f"{x / 1e3:,.{0 if digits is None else digits}f}k"
    return f"{x:,.{0 if digits is None else digits}f}"


def in_k(df: pd.DataFrame, cols, digits: int = 1) -> pd.DataFrame:
    """THB columns in thousands for tables; the header says so."""
    out = df.copy()
    for col in cols:
        out[col] = (out[col] / 1000).round(digits)
    return out.rename(columns={col: f"{col} (THB k)" for col in cols})


def header(title: str, caption: str) -> None:
    """Page title and one line on what the page answers."""
    st.title(title)
    st.caption(caption)


def show(fig: go.Figure, title: str, sub: str, height: int = 430, legend: bool = True) -> None:
    """Draw a chart. Title = the finding (';' starts a new line), sub = what is plotted."""
    text = title.replace("; ", ";<br>") + f"<br><span style='font-size:12px;color:{TOTAL}'>{sub}</span>"
    fig.update_layout(
        template="plotly_white", height=height, showlegend=legend,
        title=dict(text=text, x=0, xanchor="left", font=dict(size=16, color=INK)),
        margin=dict(t=100, l=10, r=10, b=40), font=dict(size=13),
        legend=dict(orientation="h", y=-0.15, x=0, xanchor="left", yanchor="top"))
    st.plotly_chart(fig, theme=None)


def pick(label: str, options: list[str], key: str, all_label: str = "All") -> str:
    """Sidebar select box with an 'All' option first."""
    return st.sidebar.selectbox(label, [all_label] + list(options), key=key)
