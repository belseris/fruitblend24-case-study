"""Write FruitBlend24_PnL.xlsx with live formulas, and check the formulas in Python."""
import re

import numpy as np
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

FONT = "Arial"
BLUE = Font(name=FONT, color="0000FF")      # numbers typed in from the data
BLACK = Font(name=FONT, color="000000")     # formulas on the same sheet
GREEN = Font(name=FONT, color="008000")     # links to another sheet
BOLD = Font(name=FONT, bold=True)
TITLE = Font(name=FONT, bold=True, size=14)
NOTE = Font(name=FONT, italic=True, color="52514E")
HEAD_FILL = PatternFill("solid", fgColor="E1E0D9")
THB = '#,##0;(#,##0);"-"'
PCT = '0.0%;(0.0%);"-"'
PER_CUP = '#,##0.00;(#,##0.00);"-"'

# Statement layout: (label, P&L column or None, formula on rows by key). Inputs have no formula.
LINES = [
    ("cups", "Cups sold", "cups", None),
    ("list", "List revenue", "list_revenue", None),
    ("disc", "Discount", "discount", None),
    ("rev", "Gross revenue", None, "{list}-{disc}"),
    ("comm", "Commission", "commission", None),
    ("net", "Net revenue", None, "{rev}-{comm}"),
    ("fruit", "Fruit cost", "fruit", None),
    ("pack", "Packaging + labor", "pack_labor", None),
    ("cm", "Contribution margin (GP-B)", None, "{net}-{fruit}-{pack}"),
    ("waste", "Waste cost", "waste_cost", None),
    ("gp", "Gross profit (GP-C)", None, "{cm}-{waste}"),
    ("oh", "Kitchen overhead", "overhead", None),
    ("op", "Operating profit", None, "{gp}-{oh}"),
    ("gp_pct", "GP-C % of gross revenue", None, "IFERROR({gp}/{rev},0)"),
    ("op_pct", "Operating margin %", None, "IFERROR({op}/{rev},0)"),
    ("comm_pct", "Commission % of gross revenue", None, "IFERROR({comm}/{rev},0)"),
    ("fruit_pct", "Fruit % of gross revenue", None, "IFERROR({fruit}/{rev},0)"),
    ("waste_pct", "Waste % of gross revenue", None, "IFERROR({waste}/{rev},0)"),
]
BOLD_LINES = {"rev", "net", "cm", "gp", "op"}


def _header(ws, row, labels, first="Line"):
    for j, text in enumerate([first] + labels, start=1):
        cell = ws.cell(row=row, column=j, value=text)
        cell.font, cell.fill = BOLD, HEAD_FILL
        cell.alignment = Alignment(horizontal="center" if j > 1 else "left")


def _statement_block(ws, top, months, values, link=None):
    """Write one statement block. values: month x column frame. link(key, month_col) -> formula."""
    rows = {key: top + i for i, (key, *_rest) in enumerate(LINES)}
    n = len(months)
    fy_col = n + 2
    for key, label, col, formula in LINES:
        r = rows[key]
        ws.cell(row=r, column=1, value=label).font = BOLD if key in BOLD_LINES else BLACK
        is_pct = key.endswith("_pct")
        for j in range(2, fy_col + 1):
            letter = get_column_letter(j)
            refs = {k: f"{letter}{rr}" for k, rr in rows.items()}
            if formula:
                cell = ws.cell(row=r, column=j, value="=" + formula.format(**refs))
                cell.font = BOLD if key in BOLD_LINES else BLACK
            elif j == fy_col:
                cell = ws.cell(row=r, column=j, value=f"=SUM(B{r}:{get_column_letter(n + 1)}{r})")
                cell.font = BLACK
            elif link:
                cell = ws.cell(row=r, column=j, value=link(key, letter, r))
                cell.font = GREEN
            else:
                cell = ws.cell(row=r, column=j, value=float(values.loc[months[j - 2], col]))
                cell.font = BLUE
            cell.number_format = PCT if is_pct else THB
    return rows


def write_pnl_xlsx(path, company, kitchen, contrib, variance, overhead):
    """Company P&L, Kitchen P&L, Item x Kitchen, Budget variance and Definitions sheets."""
    months = company["month"].tolist()
    kitchens = sorted(kitchen["kitchen"].unique())
    wb = Workbook()

    # Kitchen P&L first, so the company sheet can link to it.
    wk = wb.active
    wk.title = "Kitchen P&L"
    wk["A1"], wk["A1"].font = "Kitchen P&L, THB by month", TITLE
    wk["A2"] = "Blue = numbers from the data. Black = formulas. Overhead is fixed per kitchen and never split to items."
    wk["A2"].font = NOTE
    block_rows = {}
    top = 4
    for name in kitchens:
        wk.cell(row=top, column=1, value=name).font = BOLD
        _header(wk, top + 1, months + ["FY"])
        vals = kitchen[kitchen["kitchen"] == name].set_index("month")
        block_rows[name] = _statement_block(wk, top + 2, months, vals)
        top += len(LINES) + 4

    # Company P&L = sum of the kitchen blocks.
    wc = wb.create_sheet("Company P&L", 0)
    wc["A1"], wc["A1"].font = "FruitBlend24 company P&L, THB, Sep 2025 to Aug 2026", TITLE
    wc["A2"] = ("Green = sum of the 4 kitchens on 'Kitchen P&L'. Black = formulas. "
                "Main gross profit = GP-C (after commission, fruit, packaging + labor and waste).")
    wc["A2"].font = NOTE
    _header(wc, 4, months + ["FY"])

    def link(key, letter, _r):
        cells = [f"'Kitchen P&L'!{letter}{block_rows[k][key]}" for k in kitchens]
        return "=" + "+".join(cells)

    comp_rows = _statement_block(wc, 5, months, None, link=link)

    # Item x Kitchen, full year.
    wi = wb.create_sheet("Item x Kitchen")
    wi["A1"], wi["A1"].font = "Item x kitchen, full year Sep 2025 to Aug 2026, THB", TITLE
    wi["A2"] = "Berry sells from 2026-03-01 only. No overhead here: items are judged on GP-C."
    wi["A2"].font = NOTE
    heads = ["Kitchen", "Item", "Cups", "Gross revenue", "Commission", "Fruit", "Packaging + labor",
             "Waste cups", "Waste cost", "CM (GP-B)", "GP-C", "GP-C %", "GP-C per cup", "Waste rate %"]
    for j, h in enumerate(heads, start=1):
        cell = wi.cell(row=4, column=j, value=h)
        cell.font, cell.fill = BOLD, HEAD_FILL
    fy = contrib.groupby(["kitchen", "sku"])[["cups", "gross_revenue", "commission", "fruit",
                                               "pack_labor", "waste_units", "waste_cost"]].sum()
    r = 5
    for (kname, sku), row in fy.iterrows():
        wi.cell(row=r, column=1, value=kname).font = BLACK
        wi.cell(row=r, column=2, value=sku).font = BLACK
        for j, col in enumerate(fy.columns, start=3):
            cell = wi.cell(row=r, column=j, value=float(row[col]))
            cell.font, cell.number_format = BLUE, THB
        for j, f, fmt in [(10, f"=D{r}-E{r}-F{r}-G{r}", THB), (11, f"=J{r}-I{r}", THB),
                          (12, f"=IFERROR(K{r}/D{r},0)", PCT), (13, f"=IFERROR(K{r}/C{r},0)", PER_CUP),
                          (14, f"=IFERROR(H{r}/(C{r}+H{r}),0)", PCT)]:
            cell = wi.cell(row=r, column=j, value=f)
            cell.font, cell.number_format = BLACK, fmt
        r += 1
    last = r - 1
    wi.cell(row=r, column=1, value="Total").font = BOLD
    for j in range(3, 12):
        letter = get_column_letter(j)
        cell = wi.cell(row=r, column=j, value=f"=SUM({letter}5:{letter}{last})")
        cell.font, cell.number_format = BOLD, THB
    for j, f, fmt in [(12, f"=IFERROR(K{r}/D{r},0)", PCT), (13, f"=IFERROR(K{r}/C{r},0)", PER_CUP),
                      (14, f"=IFERROR(H{r}/(C{r}+H{r}),0)", PCT)]:
        cell = wi.cell(row=r, column=j, value=f)
        cell.font, cell.number_format = BOLD, fmt
    fy_letter = get_column_letter(len(months) + 2)
    wi.cell(row=r + 1, column=1, value="Check: GP-C minus Company P&L FY (should be 0)").font = NOTE
    cell = wi.cell(row=r + 1, column=11, value=f"=K{r}-'Company P&L'!{fy_letter}{comp_rows['gp']}")
    cell.font, cell.number_format = GREEN, THB
    item_total_row = r

    # Budget variance by month.
    wv = wb.create_sheet("Budget variance")
    wv["A1"], wv["A1"].font = "Actual vs budget by month, THB (GP = GP-C)", TITLE
    wv["A2"] = ("GP variance = revenue effect (revenue gap x budget margin) + margin effect "
                "(actual revenue x (actual margin - budget margin)). Check column should be 0.")
    wv["A2"].font = NOTE
    vh = ["Month", "Actual revenue", "Budget revenue", "Revenue variance", "Revenue variance %",
          "Actual GP", "Budget GP", "GP variance", "GP variance %", "Actual GP %", "Budget GP %",
          "Revenue effect", "Margin effect", "Check"]
    for j, h in enumerate(vh, start=1):
        cell = wv.cell(row=4, column=j, value=h)
        cell.font, cell.fill = BOLD, HEAD_FILL
    vv = variance.set_index("month")
    for i, mo in enumerate(months):
        r = 5 + i
        letter = get_column_letter(i + 2)
        wv.cell(row=r, column=1, value=mo).font = BLACK
        cells = {
            2: (f"='Company P&L'!{letter}{comp_rows['rev']}", GREEN, THB),
            3: (float(vv.loc[mo, "budget_revenue"]), BLUE, THB),
            6: (f"='Company P&L'!{letter}{comp_rows['gp']}", GREEN, THB),
            7: (float(vv.loc[mo, "budget_gp"]), BLUE, THB),
        }
        for j, (val, font, fmt) in cells.items():
            cell = wv.cell(row=r, column=j, value=val)
            cell.font, cell.number_format = font, fmt
        _variance_formulas(wv, r)
    r = 5 + len(months)
    wv.cell(row=r, column=1, value="FY").font = BOLD
    for j in [2, 3, 6, 7]:
        letter = get_column_letter(j)
        cell = wv.cell(row=r, column=j, value=f"=SUM({letter}5:{letter}{r - 1})")
        cell.font, cell.number_format = BOLD, THB
    _variance_formulas(wv, r, bold=True)

    # Definitions.
    wd = wb.create_sheet("Definitions")
    wd["A1"], wd["A1"].font = "Definitions and sources", TITLE
    oh_text = ", ".join(f"{k} {v / 1000:,.0f}k" for k, v in
                        overhead.set_index("kitchen")["fixed_monthly_overhead_thb"].items())
    rows = [
        ("Source", "data/raw/FruitBlend24_Intern_Case_Data.xlsx, cleaned in notebooks 01-02 (see docs/decisions.md)."),
        ("Period", "2025-09-01 to 2026-08-31. Month = calendar month of the order date."),
        ("List revenue", "List price x cups. List price = base_price_thb in cost_assumptions."),
        ("Discount", "List revenue - gross revenue (promo codes RC101, RC102, RC103)."),
        ("Gross revenue", "price_thb x units_sold: what the customer paid, after discount."),
        ("Commission", "Gross revenue x platform rate (LINE MAN 30%, Grab 24%)."),
        ("Net revenue", "Gross revenue - commission."),
        ("Fruit cost", "Cups x weekly fruit cost per cup (week = Monday of the order date)."),
        ("Packaging + labor", "Cups x packaging + labor per cup (cost_assumptions)."),
        ("GP-A", "Gross revenue - fruit - packaging + labor (no commission, no waste). Check only."),
        ("GP-B / CM", "Net revenue - fruit - packaging + labor (no waste). Check only."),
        ("Gross profit (GP-C)", "GP-B - waste cost. Main definition: waste is a real variable cost "
                                "and the budget note does not define GP."),
        ("Waste cost", "waste_daily est_waste_cost_thb (fruit + packaging), plus 6 filled kitchen-days "
                       "and the berry launch-day cost (about 4.5k THB filled in total)."),
        ("Kitchen overhead", f"Fixed per month: {oh_text}. Never split to items."),
        ("Operating profit", "GP-C - kitchen overhead."),
        ("Budget", "Flat 2.7M THB revenue and 0.7M THB GP a month (25.9% margin), set at the start of the year."),
        ("Revenue effect", "(Actual revenue - budget revenue) x budget GP %."),
        ("Margin effect", "Actual revenue x (actual GP % - budget GP %) = GP - revenue x budget GP %."),
        ("Item or kitchen gap", "Its GP - its revenue x budget GP %. Gaps add up to the margin effect."),
        ("Colors", "Blue = numbers from the data. Black = formulas. Green = links to another sheet."),
    ]
    for i, (a, b) in enumerate(rows, start=3):
        wd.cell(row=i, column=1, value=a).font = BOLD
        wd.cell(row=i, column=2, value=b).font = BLACK
        wd.cell(row=i, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    wd.column_dimensions["A"].width = 22
    wd.column_dimensions["B"].width = 110

    for ws in [wc, wk]:
        ws.column_dimensions["A"].width = 32
        for j in range(2, len(months) + 3):
            ws.column_dimensions[get_column_letter(j)].width = 13
        ws.freeze_panes = "B5" if ws is wc else "B4"
    for ws, widths in [(wi, [18, 20] + [14] * 12), (wv, [10] + [15] * 13)]:
        for j, wdt in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(j)].width = wdt
        ws.freeze_panes = "A5"
    wb.calculation.fullCalcOnLoad = True  # Excel computes every formula when the file opens
    wb.save(path)
    return {"company_rows": comp_rows, "kitchen_rows": block_rows, "item_total_row": item_total_row,
            "fy_col": fy_letter}


def _variance_formulas(ws, r, bold=False):
    font = BOLD if bold else BLACK
    for j, f, fmt in [
        (4, f"=B{r}-C{r}", THB), (5, f"=IFERROR(D{r}/C{r},0)", PCT),
        (8, f"=F{r}-G{r}", THB), (9, f"=IFERROR(H{r}/G{r},0)", PCT),
        (10, f"=IFERROR(F{r}/B{r},0)", PCT), (11, f"=IFERROR(G{r}/C{r},0)", PCT),
        (12, f"=D{r}*K{r}", THB), (13, f"=F{r}-B{r}*K{r}", THB), (14, f"=L{r}+M{r}-H{r}", THB),
    ]:
        cell = ws.cell(row=r, column=j, value=f)
        cell.font, cell.number_format = font, fmt


# A small evaluator for the formulas above: + - * /, SUM(range), IFERROR, cell and sheet links.
_REF = r"(?:'([^']+)'!)?\$?([A-Z]{1,3})\$?(\d+)"


class FormulaCheck:
    """Evaluate the workbook formulas without Excel, to test them against pandas."""

    def __init__(self, path):
        self.wb = load_workbook(path)
        self.memo = {}

    def value(self, sheet, ref):
        key = (sheet, ref)
        if key not in self.memo:
            v = self.wb[sheet][ref].value
            if isinstance(v, str) and v.startswith("="):
                v = self._eval(sheet, v[1:])
            self.memo[key] = np.float64(0.0 if v is None else v)
        return self.memo[key]

    def _range(self, sheet, a, b):
        ws = self.wb[sheet]
        return sum(self.value(sheet, c.coordinate) for row in ws[f"{a}:{b}"] for c in row)

    def _eval(self, sheet, expr):
        def sum_sub(m):
            sh = m.group(1) or sheet
            return f"_r({sh!r},'{m.group(2)}{m.group(3)}','{m.group(4)}{m.group(5)}')"
        expr = re.sub(r"SUM\(" + _REF + r":\$?([A-Z]{1,3})\$?(\d+)\)", sum_sub, expr)
        expr = re.sub(r"(?<![\w'])" + _REF,
                      lambda m: f"_v({(m.group(1) or sheet)!r},'{m.group(2)}{m.group(3)}')", expr)
        expr = expr.replace("IFERROR(", "_iferror(")
        with np.errstate(divide="ignore", invalid="ignore"):
            return eval(expr, {"_r": self._range, "_v": self.value,
                               "_iferror": lambda a, b: a if np.isfinite(a) else b})
