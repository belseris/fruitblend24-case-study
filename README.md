# FruitBlend24: where profit is lost and what to do next

Analyst case study for Atmind Group (Revenue / Data Analyst Intern): 12 months of smoothie orders turned into a P&L,
a budget gap analysis, price and promo decisions, a Sep-Nov forecast and a costed action plan.

**Live app:** [fruitblend24.streamlit.app](https://fruitblend24.streamlit.app)

## Key findings

- **-฿404k operating profit in 12 months.** The Bangkok kitchens lose ฿1.11M after overhead; Pattaya makes ฿704k.
- **Gross profit (GP-C) ฿7.64M vs ฿8.40M budget (-฿764k).** Lower sales explain ฿325k, lower margins ฿439k, mostly
  berry (-฿686k) and PassionFruit (-฿420k). Before waste (GP-B) the year is +฿97k vs budget; we use GP-C because
  waste is a real cost.
- **Berry loses ฿1.92 a cup after waste**: 20.5% of what it preps is thrown away, and it is 39% of all waste cost with
  4.5% of cups.
- **All 3 promo codes lose money**, about ฿15k a month after waste and side effects.
- **Four actions add ฿92k to ฿118k a month** and cut the Sep-Nov 2026 loss from ฿685k to ฿408k (cautious case).
  Breaking even needs about ฿136k a month more in cost cuts, 40% of the Bangkok overhead.

## View the notebooks

The notebooks are saved with their outputs, so you can read them without running anything.

- **All notebooks (GitHub Pages):** [belseris.github.io/fruitblend24-case-study](https://belseris.github.io/fruitblend24-case-study/)

| Notebook | GitHub Pages (HTML, interactive charts) | nbviewer (backup) |
| --- | --- | --- |
| 01 Data quality | [HTML](https://belseris.github.io/fruitblend24-case-study/notebooks/01_data_quality.html) | [nbviewer](https://nbviewer.org/github/belseris/fruitblend24-case-study/blob/main/notebooks/01_data_quality.ipynb) |
| 02 Demand and pricing | [HTML](https://belseris.github.io/fruitblend24-case-study/notebooks/02_demand_pricing.html) | [nbviewer](https://nbviewer.org/github/belseris/fruitblend24-case-study/blob/main/notebooks/02_demand_pricing.ipynb) |
| 03 Promotions | [HTML](https://belseris.github.io/fruitblend24-case-study/notebooks/03_promotions.html) | [nbviewer](https://nbviewer.org/github/belseris/fruitblend24-case-study/blob/main/notebooks/03_promotions.ipynb) |
| 04 P&L and budget | [HTML](https://belseris.github.io/fruitblend24-case-study/notebooks/04_pnl_budget.html) | [nbviewer](https://nbviewer.org/github/belseris/fruitblend24-case-study/blob/main/notebooks/04_pnl_budget.ipynb) |
| 05 Forecast and inventory | [HTML](https://belseris.github.io/fruitblend24-case-study/notebooks/05_forecast_inventory.html) | [nbviewer](https://nbviewer.org/github/belseris/fruitblend24-case-study/blob/main/notebooks/05_forecast_inventory.ipynb) |
| 06 Summary numbers | [HTML](https://belseris.github.io/fruitblend24-case-study/notebooks/06_summary.html) | [nbviewer](https://nbviewer.org/github/belseris/fruitblend24-case-study/blob/main/notebooks/06_summary.ipynb) |

On GitHub itself the charts show as static PNG images.

## What is in the repo

```
app/            Streamlit app: streamlit_app.py (summary), pages/1-7, common.py (shared helpers)
notebooks/      01 data quality, 02 demand and pricing, 03 promotions, 04 P&L and budget,
                05 forecast and prep, 06 summary (checks the numbers in the docs)
src/            cleaning, unit economics, P&L, forecast and scenario code the notebooks call
outputs/        tables the notebooks write and the app reads, plus FruitBlend24_PnL.xlsx (live formulas)
docs/           approach_note.md, executive_summary.md, decisions.md (every judgment call),
                index.html + notebooks/*.html (the GitHub Pages site)
data/raw/       the case workbook (never changed); data/processed/ the name mapping and clean log
tests/          app tests: every page and control runs, KPIs equal the P&L, screen text rules
```

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

On macOS or Linux, activate with `source .venv/bin/activate`. The app only reads `outputs/` and `docs/`.

`requirements.txt` holds only what the app needs, so Streamlit Cloud installs it fast. `requirements-dev.txt` adds
the notebook and test packages (scipy, statsmodels, jupyter, pytest).

## Re-run the analysis

```powershell
pip install -r requirements-dev.txt
Get-ChildItem notebooks/0*.ipynb | Sort-Object Name | ForEach-Object { jupyter nbconvert --to notebook --execute --inplace $_.FullName }
pytest -q
```

Dev note: the notebooks save a PNG copy of each plotly chart so GitHub can show it. That needs `kaleido`
(`pip install kaleido`, it uses your installed Chrome). It is not in the requirements files because the app does not
use it. To rebuild the HTML pages after a run:
`jupyter nbconvert --to html notebooks/0*.ipynb --output-dir docs/notebooks`.

Run the notebooks in order (01 to 06). Each one asserts its key totals, so a run that ends without an error means:

- raw minus removed rows = clean
- items and kitchens add up to the company
- the budget gap = revenue effect + margin effect

The app, the notebooks and the Excel P&L all read the same `outputs/`, so they show the same numbers.

## Data note

The data is the synthetic (mock) workbook given for this case study: 12 months, Sep 2025 to Aug 2026, 4 kitchens,
LINE MAN and Grab only. All figures are illustrative. The raw file in `data/raw/` is never edited; cleaning is in
`src/load_clean.py` and notebook 01. The workbook is kept in the repo so every number can be rebuilt; it will be
removed if the case owner asks.

## Author

Ratthapak Sinsiri, Data Science and Software Innovation, Ubon Ratchathani University ·
[github.com/belseris](https://github.com/belseris)
