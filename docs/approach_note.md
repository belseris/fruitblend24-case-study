# FruitBlend24: approach note

Ratthapak Sinsiri · Revenue / Data Analyst Intern case, Atmind Group · data Sep 2025 to Aug 2026

## The question

FruitBlend24 sells 5 smoothies from 4 kitchens, only on LINE MAN and Grab. Profit is below budget. I wanted to answer
three things: where the profit goes, which levers (price, promos, prep, menu) fix it, and what Sep-Nov 2026 looks like
with and without those levers.

## 1. Make the data trustworthy first

- 31 raw item names (Thai, English, typos) map to the 5 menu items with a mapping file I checked by hand.
- I removed only rows that are not real sales: 372 exact copies and 370 non-menu rows (742 rows, ฿130k, 0.42% of
  revenue). Unsure rows are flagged, not dropped. Missing waste rows are filled and flagged.
- An assert checks raw minus removed = clean (123,655 rows, ฿31,146,932.57, difference 0). Every step is in the data
  quality log with rows and ฿.

## 2. Build the P&L, then compare with the budget

- Revenue (after discount) - platform commission - fruit (that week's cost) - packaging + labor - waste = gross
  profit (GP-C). GP-C - fixed kitchen overhead = operating profit.
- I chose GP-C because the budget margin (25.9%) is after commission, and waste is a real cost. GP-B (27.3%) is the
  less careful option and changes the headline: before waste the year is +฿97k vs budget, not -฿764k. Both are shown.
- Items are judged on GP-C; kitchens on operating profit. Overhead is never split to items.
- The budget gap is split into a revenue effect and a margin effect, and an assert checks they add up.

**Result:** GP-C ฿7.64M vs ฿8.40M budget (-฿764k): ฿325k from lower sales, ฿439k from lower margins, mostly berry
(-฿686k) and PassionFruit (-฿420k). Operating profit is -฿404k; Bangkok loses ฿1.11M, Pattaya makes ฿704k.

## 3. Test each lever with the data

- **Price:** log-log regression per item on Bundle (RC101) days vs normal price, with hour, weekday, kitchen,
  platform and month controls. A rise is safe only if customers react less than the break-even level: Watermelon
  -1.66 vs -2.24, PassionFruit -1.24 vs -3.50. Pineapple and Guava are too close, so they get a test first. Stress test at the
  cautious end of what we measured (Watermelon -1.91, PassionFruit -1.59, berry -1.51): the plan still adds ฿84k a month.
- **Promotions:** each promo hour is compared with the same kitchen, item, platform, month, weekday and hour on normal
  days, then extra waste and side effects are added. All 3 codes lose money (about ฿15k a month). Stopping the worst
  rows saves ฿7.0k in an average month of the year (฿11.5k a month in the Sep-Nov model).
- **Waste:** berry throws away 20.5% of what it preps and loses ฿1.92 a cup after waste. A newsvendor rule (prep to
  the critical ratio Cu / (Cu + Co)) beats today's prep only where waste is expensive: berry and PassionFruit
  (+฿29.6k in the August backtest). For the cheap items today's prep is already close to right. The rule runs out
  on purpose (17% of berry and 8% of PassionFruit demand); a lost cup is costed as lost profit only.
- **Forecast:** three methods backtested on Jun-Aug 2026 (trained to 31 May). Seasonal naive wins (WAPE 46.6%), but
  every method misses the rainy-season drop, so Oct and Nov use last year's month-to-month change. Sep-Nov: about 131k
  cups, old items -2.0% vs 2025.

## 4. Put the levers in one model

One model per month x kitchen x item, so no lever is counted twice. Sep-Nov operating profit:

| Base | Action | Action + delist berry | Downside |
|---|---|---|---|
| -฿685k | -฿408k | -฿450k | -฿787k |

The 4 actions add ฿92k to ฿118k a month (elasticity -1.5 to -0.5). Even so, low-season sales do not cover the ฿670k
monthly overhead: Action still loses about ฿136k a month. Breaking even needs costs ฿136k a month lower, 40% of the
฿340k Bangkok overhead, while the overhead review is sized at up to ฿51.7k. That gap is the next decision. Keeping
berry at 99 THB with the prep rule and a stop rule beats delisting it now.

## Limits

No sold-out log (today's prep looks better than it is; lost repeat customers are not costed), few promo days per code, berry has no last year, waste has no
platform split, and there are no grams per cup. Each limit and every judgment call is in `docs/decisions.md`.

## How to check my numbers

The notebooks write `outputs/`; the app and the Excel P&L only read it. `pytest -q` checks the app against the P&L,
and each notebook asserts its totals.
