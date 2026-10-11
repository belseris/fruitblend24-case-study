# FruitBlend24: executive summary

Data: 12 months of online orders (Sep 2025 to Aug 2026), 4 kitchens, LINE MAN and Grab. All money in THB.
Gross profit (GP) = revenue after discount - platform commission - fruit - packaging and labor - waste.

## Bottom line

FruitBlend24 lost 404k THB after kitchen overhead in the last 12 months and missed its GP budget by 764k (-9.1%): berry and PassionFruit earn below the budget margin, and the two Bangkok kitchens do not cover their overhead. The GP definition matters: before waste (GP-B) the year is +97k vs budget. We use GP-C because waste is a real cost and the budget note does not leave it out.
Four actions add 92k to 118k THB a month and cut the Sep-Nov loss from 685k to about 408k. That still leaves about 136k a month: to break even, costs must fall by 40% of the 340k monthly Bangkok overhead, more than the overhead review is sized for (up to 51.7k).

## Five insights

**1. The company misses budget and is loss-making after overhead; the Bangkok kitchens drive the loss.**
GP 7.64M vs 8.4M budget (-764k); operating profit -404k. Bangkok kitchens -1.11M after overhead, Pattaya +0.70M.
Chart: notebook 04, section 6 (operating profit per kitchen and month).

**2. Mixed Berry loses money after waste: -1.92 THB a cup on average (Mar-Aug), 20.5% thrown away; in August alone it lost 43k (-17 THB a cup) as fruit cost rose and sales fell.**
CM 10.02 THB a cup before waste, waste 11.94 THB a cup (Mar-Aug). Berry is 39% of all waste THB with 4.5% of cups.
Chart: notebook 04, section 7 (menu matrix); notebook 05, section 1 (waste by item).

**3. No promo code pays back: -14.6k THB in an average month of the year after waste; promo days waste more cups (+81% on Double day (RC102)), in line with the extra sales.**
Bundle (RC101), Double day (RC102) and Rainy season (RC103) all lose CM after waste and side effects. Double day sells +75% and wastes +81% cups, so the waste rate stays about the same. Stopping the Kill rows saves 7.0k in an average month of the year, and 11.5k a month in the Sep-Nov model.
Chart: notebook 03, section 10 (which promos earn back their cost).

**4. Price headroom on Watermelon and PassionFruit: customers would have to react much more strongly to price than we measured before a rise stops paying.**
Watermelon: a rise stops paying at -2.24; we measured -1.66 (day-level -1.81). PassionFruit: -3.50 vs -1.24. At the cautious end of what we measured (Watermelon -1.91, PassionFruit -1.59, berry -1.51), the 4 actions still add 84k a month.
Chart: notebook 02, section 2 (price simulation, +5 THB at elasticity -0.5 to -1.5).

**5. Waste is 860k a year; the prep rule for berry and PassionFruit saves about 30-40k a month.**
+29.6k in the August backtest, +40.2k in the Sep-Nov model. The rule loses for Watermelon, Pineapple and Guava, which waste only 3-6% today.
Chart: notebook 05, section 3 (today vs rule by month).

## Recommendations

THB a month = change in operating profit vs today, Sep-Nov 2026. Low and high = price elasticity -1.5 and -0.5. Each action has its full effect from its start date (no ramp-up).

| Area | Action | THB a month (low-high) | Confidence | Key assumption | Owner |
|---|---|---|---|---|---|
| Waste | Prep berry and PassionFruit at the critical-ratio level + 0.1; on promo days x the measured lift | 38.8k-40.2k | Medium | No sold-out data today; berry is planned to sell out on ~17% of demand, costed as lost profit only (not lost repeat customers) | Kitchen managers, ops lead |
| Pricing | Watermelon 45 -> 49, PassionFruit 65 -> 69 THB | 27.2k-51.9k | Medium | Elasticity -1.5 to -0.5 (stress test at the measured -1.91 / -1.59: plan still +84k a month); roll back if cups fall more than 17% / 19% | Revenue manager |
| Menu | Berry 89 -> 99 THB; delist if GP per cup is below 0 for 4 weeks | 13.5k-15.9k | Low | Berry fruit at the Jun-Aug mean (45.1 THB); at the late-Aug 51.2 THB, ~11k a month less | Menu owner |
| Promotions | Stop Bundle (RC101) on Watermelon, PassionFruit, berry and Rainy season (RC103) on both apps | 11.5k | High | Promo cups fall back to the measured baseline | Marketing / platform manager |
| **Total** | **Rows above together, one model (Action vs Base)** | **92.4k-118.1k** | Medium | From scenarios.csv, not a sum of rows | COO |
| Tests (not in total) | 4 weeks: Pineapple and Guava at 55 THB in one kitchen; Bundle (RC101) Pineapple quiet hours, Guava 10%; Double day (RC102) at 12% without berry | 0-77.6k | Low | Only if tests pass; based on Mar-Aug, so smaller in Sep-Nov | Revenue analyst |
| Kitchens (not in total) | Review Bangkok overhead (rent, staff hours) on 1 Nov | 0-51.7k | Low | High = close Ladprao, all overhead avoidable, no customer moves | Finance / COO |

Start dates, KPIs and stop rules: `outputs/profit_plan.csv` and `outputs/recommendations.csv`.

## 3-month outlook (Sep-Nov 2026)

Operating profit, THB thousands. Overhead 670k a month in every scenario.

| Scenario | Sep | Oct | Nov | 3 months |
|---|---|---|---|---|
| Base (today's prices, promos and prep) | -267 | -257 | -161 | -685 |
| Action (4 actions above) | -173 | -160 | -75 | -408 |
| Action + delist berry | -186 | -175 | -89 | -450 |
| Downside (Action, fruit +15%, demand -10%) | -291 | -282 | -214 | -787 |

- Demand: old items within 3% of Sep-Nov 2025; Nov is 15-20% above Sep. Berry is held flat at its August level, which is on the high side (it fell every month since launch).
- Budget: Action revenue 6.26M vs 8.1M budget and GP 1.60M vs 2.1M (Sep-Nov budget assumed flat at 2.7M / 0.7M a month, as Sep 2025 to Aug 2026). GP margin rises to 25.6%, near the budget's 25.9%, but low-season volume is too small to cover overhead. The budget is flat every month, so last year's misses follow the season (only Mar-May beat it); even on budget, the year plans only 360k operating profit after 8.04M overhead.
- Delisting berry is 14k a month worse than keeping it at 99 THB with the prep rule, so the stop rule decides.
- In a bad quarter the plan still helps: Downside -787k vs -1,106k for today's way under the same shock.

## What we need to confirm

1. **A/B tests:** the 4-week price and promo tests above, each against a control kitchen or the same-weekday baseline. Price rises are tracked against the forecast.
2. **Sold-out data:** a log of item, time and cups when a kitchen runs out. Today a sold-out is almost never visible (0.1-0.3% of days have zero waste), so all waste and prep results assume no hidden sold-outs.
3. **Grams per cup:** fruit is bought by weight, but the data has cups only. With grams per cup the inventory plan becomes a purchase plan.
4. **Platform split:** the data has cups by platform, not orders. Can a promo run on one app only? Can berry have a LINE MAN-only price (30% vs 24% commission)? How many orders and cups per order per app?
5. **Bangkok overhead:** which part of the 340k a month can be cut (break-even in Sep-Nov needs about 136k), and when the leases end.

Sources: notebooks 01-06, `outputs/`, decisions in `docs/decisions.md`.
