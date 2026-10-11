# FruitBlend24: where profit is lost and what to do next

Analyst case study for Atmind Group (Revenue / Data Analyst Intern), by Ratthapak Sinsiri.

FruitBlend24 is an online smoothie brand: 4 kitchens in Pattaya and Bangkok, sold only on LINE MAN and Grab,
open 24 hours. This project uses 12 months of orders (Sep 2025 to Aug 2026) to explain why profit is below
budget, and what to do in Sep to Nov 2026 to grow profit and cut waste.

**Live app:** _link added after the first deploy on Streamlit Community Cloud_

**Run locally:** `pip install -r requirements.txt` then `streamlit run app/streamlit_app.py`

## What is in the repo

| Path | What it holds |
| --- | --- |
| `app/` | Streamlit app: summary page, 7 pages (data quality to action plan), shared helpers in `common.py` |
| `notebooks/` | 01 data quality, 02 demand and pricing, 03 promotions, 04 P&L and budget, 05 forecast and prep, 06 summary |
| `src/` | Cleaning, unit economics, P&L, forecast and scenario code that the notebooks call |
| `outputs/` | Tables the notebooks write and the app reads, plus `FruitBlend24_PnL.xlsx` (live formulas) |
| `docs/` | `decisions.md` (every judgment call with reason and impact) and `executive_summary.md` |
| `tests/` | App tests: every page and control runs, KPIs equal the P&L, screen text rules |

## How the numbers stay the same everywhere

- The raw Excel file in `data/raw/` is never changed. Notebook 01 cleans it and checks raw minus removed = clean.
- The notebooks write every table to `outputs/`. The app and the Excel P&L only read these files, so the app,
  the notebooks and the P&L show the same numbers.
- Asserts check the key totals: items and kitchens add up to the company, and the budget gap = revenue effect +
  margin effect.

## Rebuild the outputs

`pip install -r requirements-dev.txt`, then run the notebooks in order (01 to 06) with Restart and Run All.
Run the app tests with `pytest -q`.
