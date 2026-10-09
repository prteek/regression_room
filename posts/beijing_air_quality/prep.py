"""Prepare daily station data and a deliberately sparse version that mimics thin, patchy observations.

data/daily_full.parquet   - every station x day: mean PM2.5 / PM10 over all valid hours, n = valid hours (ground truth)
data/daily_sparse.parquet - the same days, but each pollutant only sees a Poisson(LAMBDA) random subset of its valid hours
                            (drawn independently per pollutant, so often only one is observed), plus GAP_BLOCKS runs of
                            GAP_MIN..GAP_MAX consecutive empty days per station and pollutant. n = hours kept.
"""
import glob
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
POLLUTANTS = ["PM2.5", "PM10"]
LAMBDA = 1.2
GAP_BLOCKS, GAP_MIN, GAP_MAX = 2, 20, 60
SEED = 0

# Urban core vs suburban monitoring sites (grouping used as the "district" level)
AREA = {"Dongsi": "urban", "Tiantan": "urban", "Guanyuan": "urban", "Wanshouxigong": "urban", "Nongzhanguan": "urban",
        "Gucheng": "urban", "Aotizhongxin": "urban", "Wanliu": "urban",
        "Changping": "suburban", "Dingling": "suburban", "Huairou": "suburban", "Shunyi": "suburban"}


def load_hourly() -> pd.DataFrame:
    files = glob.glob(str(HERE / "data" / "PRSA_Data_20130301-20170228" / "*.csv"))
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df["date"] = pd.to_datetime(df[["year", "month", "day"]])
    return df[["station", "date", "hour"] + POLLUTANTS]


def daily(hourly: pd.DataFrame) -> pd.DataFrame:
    """Long format: station, area, date, pollutant, value (mean over hours), n (hours)."""
    long = hourly.melt(id_vars=["station", "date", "hour"], value_vars=POLLUTANTS, var_name="pollutant").dropna()
    out = long.groupby(["station", "date", "pollutant"])["value"].agg(value="mean", n="count").reset_index()
    return out.assign(area=out["station"].map(AREA))


def thin(hourly: pd.DataFrame, rng) -> pd.DataFrame:
    """Keep a Poisson(LAMBDA) random subset of valid hours per station x day x pollutant, then cut gap blocks."""
    long = hourly.melt(id_vars=["station", "date", "hour"], value_vars=POLLUTANTS, var_name="pollutant").dropna()
    long = long.sample(frac=1, random_state=SEED)  # random order within each cell
    keys = long[["station", "date", "pollutant"]].drop_duplicates()
    keys["k"] = rng.poisson(LAMBDA, len(keys))
    long = long.merge(keys, on=["station", "date", "pollutant"])
    long["rank"] = long.groupby(["station", "date", "pollutant"]).cumcount()
    kept = long[long["rank"] < long["k"]]

    days = pd.date_range(hourly["date"].min(), hourly["date"].max())
    gaps = []
    for st in sorted(hourly["station"].unique()):
        for pol in POLLUTANTS:
            for _ in range(GAP_BLOCKS):
                length = rng.integers(GAP_MIN, GAP_MAX + 1)
                start = rng.integers(0, len(days) - length)
                gaps.append(pd.DataFrame({"station": st, "pollutant": pol, "date": days[start:start + length]}))
    gaps = pd.concat(gaps).drop_duplicates().assign(in_gap=True)
    kept = kept.merge(gaps, on=["station", "date", "pollutant"], how="left")
    kept = kept[kept["in_gap"].isna()]
    out = kept.groupby(["station", "date", "pollutant"])["value"].agg(value="mean", n="count").reset_index()
    return out.assign(area=out["station"].map(AREA)), gaps.drop(columns="in_gap")


def main():
    rng = np.random.default_rng(SEED)
    hourly = load_hourly()
    full = daily(hourly)
    sparse, gaps = thin(hourly, rng)
    full.to_parquet(HERE / "data" / "daily_full.parquet", index=False)
    sparse.to_parquet(HERE / "data" / "daily_sparse.parquet", index=False)
    gaps.to_parquet(HERE / "data" / "gaps.parquet", index=False)

    cells = len(hourly["station"].unique()) * hourly["date"].nunique()
    wide = sparse.pivot_table(index=["station", "date"], columns="pollutant", values="n").notna()
    print(f"station-days: {cells:,}")
    for name, d in [("full", full), ("sparse", sparse)]:
        for pol in POLLUTANTS:
            s = d[d["pollutant"] == pol]
            print(f"{name:6s} {pol:5s}: observed {len(s) / cells:6.1%}, mean hours per observed day {s['n'].mean():5.2f}")
    print(f"sparse: both observed {wide.all(axis=1).sum() / cells:.1%}, exactly one {(wide.sum(axis=1) == 1).sum() / cells:.1%}")
    print(f"gap days removed: {len(gaps):,}")


if __name__ == "__main__":
    main()
