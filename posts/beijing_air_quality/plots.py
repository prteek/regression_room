"""Plots of the final fits against the ground truth; writes outputs/series_<station>.png and outputs/gap_zoom.png."""
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

from cv import load, smooth_truth
from model import TARGETS

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
STYLE = {"joint": dict(color="tab:blue", lw=1.8), "single-target": dict(color="tab:purple", lw=1.2, ls="--"),
         "±15-day mean": dict(color="tab:orange", lw=1.0, alpha=0.8)}


def panel(ax, st, pol, sparse, full, level, preds, gaps, start=None, end=None):
    sel = lambda d: d[(d["station"] == st) & (d["pollutant"] == pol) & d["date"].between(start or d["date"].min(), end or d["date"].max())]
    for i, (a, b) in enumerate(sel(gaps).groupby((sel(gaps)["date"].diff().dt.days != 1).cumsum())["date"].agg(["min", "max"]).itertuples(index=False)):
        ax.axvspan(a, b, color="gold", alpha=0.25, label="gap block (test)" if i == 0 else None)
    f, s, l = sel(full), sel(sparse), sel(level)
    ax.plot(f["date"], f["value"], color="0.85", lw=0.6, label="full-data daily mean")
    ax.scatter(s["date"], s["value"], s=3 + 3 * s["n"], color="0.35", alpha=0.6, label="sparse readings (size = hours)")
    ax.plot(l["date"], l["value"], color="black", lw=1.5, label="true level (31-day mean, full data)")
    for name, p in preds.items():
        q = sel(p)
        ax.plot(q["date"], q["pred"], label=name, **STYLE[name])
    ax.set_yscale("log")
    ax.set_title(f"{st} · {pol}", fontsize=9)
    ax.tick_params(labelsize=8)


def main():
    out = HERE / "outputs"
    sparse, full = load()
    level = smooth_truth(full)
    gaps = pd.read_parquet(HERE / "data" / "gaps.parquet")
    allp = pd.read_parquet(out / "predictions.parquet")
    preds = {m: g.drop(columns="model") for m, g in allp.groupby("model")}

    stations = ["Dongsi", "Huairou", "Aotizhongxin"]  # urban core, suburban, station with the longest natural gap
    fig, axes = plt.subplots(len(stations), 2, figsize=(16, 3.4 * len(stations)), sharex=True)
    for r, st in enumerate(stations):
        for c, pol in enumerate(TARGETS):
            panel(axes[r, c], st, pol, sparse, full, level, preds, gaps)
    axes[0, 0].legend(fontsize=7, loc="upper right", ncol=2)
    fig.suptitle("Final fits on sparse data vs ground truth (log scale)", fontsize=12)
    fig.tight_layout()
    fig.savefig(out / "series.png", dpi=110)

    # Zoom on the longest gap blocks
    blocks = (gaps.sort_values("date").groupby(["station", "pollutant"])
              .apply(lambda g: g.groupby((g["date"].diff().dt.days != 1).cumsum())["date"].agg(["min", "max", "count"]))
              .reset_index().sort_values("count", ascending=False))
    top = blocks.drop_duplicates("station").head(4)
    fig, axes = plt.subplots(2, 2, figsize=(16, 8))
    for ax, b in zip(axes.flat, top.itertuples(index=False)):
        pad = pd.Timedelta(days=60)
        panel(ax, b.station, b.pollutant, sparse, full, level, preds, gaps, b.min - pad, b.max + pad)
        ax.set_title(f"{b.station} · {b.pollutant} · {b.count}-day gap", fontsize=9)
    axes[0, 0].legend(fontsize=7, loc="upper right", ncol=2)
    fig.suptitle("Filling the longest gap blocks (never used for tuning)", fontsize=12)
    fig.tight_layout()
    fig.savefig(out / "gap_zoom.png", dpi=110)


if __name__ == "__main__":
    main()
