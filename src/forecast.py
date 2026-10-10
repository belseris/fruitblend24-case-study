"""Daily demand panel, prep rule, demand forecasts and newsvendor math."""
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from src.load_clean import BERRY

DAY_KEYS = ["date", "kitchen", "sku"]
SERIES = ["kitchen", "sku"]


def daily_panel(e: pd.DataFrame, sheets: dict) -> pd.DataFrame:
    """Date x kitchen x sku: cups sold, waste and a promo-day flag. Every day the item is on sale."""
    promo = e["base_code"] != "RC000"
    sales = (e.assign(promo_cups=e["units_sold"].where(promo, 0))
             .groupby(DAY_KEYS)
             .agg(sold=("units_sold", "sum"), promo_cups=("promo_cups", "sum"),
                  gross_revenue=("gross_revenue_thb", "sum"), cm=("cm_thb", "sum"),
                  fruit=("fruit_cost_thb", "sum")))
    w = sheets["waste_daily"].set_index(DAY_KEYS)[["units_wasted", "est_waste_cost_thb"]]
    w.columns = ["wasted", "waste_cost"]
    # waste_daily already has one row per kitchen-item-day from the item's first day.
    p = w.join(sales, how="outer").fillna(0.0).reset_index()
    assert len(p) == len(w), "sales on a day without a waste row"
    p["dow"] = p["date"].dt.dayofweek
    p["promo_day"] = p["promo_cups"] > 0
    p["month"] = p["date"].dt.strftime("%Y-%m")
    return p.sort_values(DAY_KEYS).reset_index(drop=True)


def critical_ratio(cu, co):
    """Newsvendor: share of demand to cover. Cu = profit lost per short cup, Co = cost per wasted cup."""
    cr = np.asarray(cu, dtype=float) / (np.asarray(cu, dtype=float) + np.asarray(co, dtype=float))
    return np.clip(cr, 0.05, 0.95)


def prep_rule(p: pd.DataFrame, q: dict, weeks: int = 8, min_obs: int = 4) -> pd.DataFrame:
    """Prep = q-quantile of the last `weeks` normal days with the same weekday, before the day.

    Promo days are left out of the history and get the same prep as a normal day.
    Also returns the mean and std of the same window, for the normal check.
    """
    out = []
    for (_, sku, _), g in p.groupby(SERIES + ["dow"], sort=False):
        normal = g.loc[~g["promo_day"], "sold"]
        roll = normal.rolling(weeks, min_periods=min_obs)
        stats = pd.DataFrame({"prep": roll.quantile(q[sku]), "mu": roll.mean(), "sd": roll.std()})
        # ffill gives promo days the last normal value; shift(1) uses only days before this one.
        out.append(stats.reindex(g.index).ffill().shift(1))
    res = pd.concat(out).reindex(p.index)
    res["prep"] = np.ceil(res["prep"])
    return res


def score_prep(sold, prep, cu, co) -> pd.DataFrame:
    """Waste and short cups and their cost for a given prep level."""
    waste = np.clip(prep - sold, 0, None)
    short = np.clip(sold - prep, 0, None)
    return pd.DataFrame({"waste": waste, "short": short, "cost": waste * co + short * cu})


def normal_waste_short(mu, sd, prep):
    """Expected waste and short cups when demand ~ Normal(mu, sd) and we prep `prep` cups."""
    mu, sd, prep = (np.asarray(x, dtype=float) for x in (mu, sd, prep))
    sd = np.where(sd > 0, sd, 1e-9)
    z = (prep - mu) / sd
    short = sd * (norm.pdf(z) - z * (1 - norm.cdf(z)))
    waste = prep - mu + short
    return waste, short


# Forecast methods. Each takes a daily series (train) and the dates to forecast.
def fc_seasonal_naive(y: pd.Series, dates: pd.DatetimeIndex) -> np.ndarray:
    """Repeat the last week of the training data."""
    last = y.iloc[-7:]
    by_dow = dict(zip(last.index.dayofweek, last.to_numpy()))
    return np.array([by_dow[d] for d in dates.dayofweek], dtype=float)


def fc_weekday_mean(y: pd.Series, dates: pd.DatetimeIndex, weeks: int = 8) -> np.ndarray:
    """Mean of the last `weeks` days with the same weekday."""
    tail = y.iloc[-7 * weeks:]
    by_dow = tail.groupby(tail.index.dayofweek).mean()
    return by_dow.reindex(dates.dayofweek).to_numpy(dtype=float)


def fc_holt_winters(y: pd.Series, dates: pd.DatetimeIndex) -> np.ndarray:
    """Holt-Winters, additive damped trend, additive weekly season."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(y.asfreq("D"), trend="add", damped_trend=True, seasonal="add",
                                   seasonal_periods=7, initialization_method="estimated").fit()
        f = fit.forecast(len(dates)).to_numpy()
    return np.clip(f, 0, None)


METHODS = {"seasonal_naive": fc_seasonal_naive, "weekday_mean_8w": fc_weekday_mean,
           "holt_winters_damped": fc_holt_winters}


def forecast_all(p: pd.DataFrame, train_end, dates: pd.DatetimeIndex, methods=METHODS) -> pd.DataFrame:
    """Forecast every kitchen x item series with each method, trained up to train_end."""
    rows = []
    train = p[p["date"] <= pd.Timestamp(train_end)]
    for (kitchen, sku), g in train.groupby(SERIES):
        y = g.set_index("date")["sold"]
        for name, fn in methods.items():
            rows.append(pd.DataFrame({"date": dates, "kitchen": kitchen, "sku": sku,
                                      "method": name, "forecast": fn(y, dates)}))
    return pd.concat(rows, ignore_index=True)


def wape_bias(df: pd.DataFrame, by) -> pd.DataFrame:
    """WAPE = sum |forecast - actual| / sum actual; bias = sum (forecast - actual) / sum actual."""
    err = df.assign(abs_err=(df["forecast"] - df["sold"]).abs(), err=df["forecast"] - df["sold"])
    g = err.groupby(by)[["sold", "forecast", "abs_err", "err"]].sum()
    g["wape_pct"] = g["abs_err"] / g["sold"] * 100
    g["bias_pct"] = g["err"] / g["sold"] * 100
    return g


def month_ratios(p: pd.DataFrame, base="2025-09", targets=("2025-10", "2025-11")) -> pd.DataFrame:
    """Cups per day in each target month / cups per day in the base month, per kitchen x item."""
    per_day = p[p["month"].isin([base, *targets])].groupby(SERIES + ["month"])["sold"].mean().unstack()
    return per_day[list(targets)].div(per_day[base], axis=0).dropna()


def forecast_horizon(p: pd.DataFrame, method: str, start="2026-09-01", end="2026-11-30",
                     berry_weeks: int = 4) -> pd.DataFrame:
    """Sep from the chosen method; Oct and Nov = Sep weekday level x 2025 month ratio.

    Berry has no 2025 data: flat weekday mean of the last `berry_weeks` weeks.
    """
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    sep = pd.date_range(start, start + pd.offsets.MonthEnd(0), freq="D")
    horizon = pd.date_range(start, end, freq="D")
    train_end = start - pd.Timedelta(days=1)
    old = p[p["sku"] != BERRY]
    f_sep = forecast_all(old, train_end, sep, {method: METHODS[method]})
    sep_dow = f_sep.assign(dow=f_sep["date"].dt.dayofweek).groupby(SERIES + ["dow"])["forecast"].mean()
    ratios = month_ratios(p)
    ratios.columns = ["2026-10", "2026-11"]  # Oct/Sep and Nov/Sep of 2025, used for 2026

    later = []
    for d in horizon[horizon > sep[-1]]:
        r = ratios[d.strftime("%Y-%m")]
        level = sep_dow.xs(d.dayofweek, level="dow")
        later.append(pd.DataFrame({"date": d, "forecast": (level * r.reindex(level.index)).to_numpy()},
                                  index=level.index).reset_index())
    old_fc = pd.concat([f_sep.drop(columns="method")] + later, ignore_index=True)
    old_fc["how"] = np.where(old_fc["date"] <= sep[-1], method, "Sep x 2025 month ratio")

    b = p[(p["sku"] == BERRY) & (p["date"] > train_end - pd.Timedelta(weeks=berry_weeks))
          & (p["date"] <= train_end)]
    b_dow = b.groupby(["kitchen", "dow"])["sold"].mean()
    berry_fc = pd.DataFrame([(d, k, BERRY, b_dow[(k, d.dayofweek)])
                             for d in horizon for k in b["kitchen"].unique()],
                            columns=["date", "kitchen", "sku", "forecast"])
    berry_fc["how"] = f"flat {berry_weeks}-week weekday mean"
    out = pd.concat([old_fc, berry_fc], ignore_index=True)
    out["month"] = out["date"].dt.strftime("%Y-%m")
    out["dow"] = out["date"].dt.dayofweek
    return out.sort_values(DAY_KEYS).reset_index(drop=True)


def demand_cv(p: pd.DataFrame, end, weeks: int = 8) -> pd.Series:
    """Day-to-day noise per kitchen x item: std around the weekday mean / mean, last `weeks` normal weeks."""
    end = pd.Timestamp(end)
    w = p[(p["date"] > end - pd.Timedelta(weeks=weeks)) & (p["date"] <= end) & ~p["promo_day"]].copy()
    w["dev"] = w["sold"] - w.groupby(SERIES + ["dow"])["sold"].transform("mean")
    g = w.groupby(SERIES)
    return np.sqrt(g["dev"].apply(lambda d: (d ** 2).mean())) / g["sold"].mean()
