"""Tune with expanding-window time series CV on the sparse data.

Folds are sequential, not random: N_FOLDS cutoffs every STEP_DAYS days, the last one HORIZON_DAYS before the end of the
data. Each fold trains on everything up to its cutoff and validates on the next HORIZON_DAYS days (look-ahead only).
Selection metric: mean absolute log error on the *sparse* validation readings, weighted by hours (what you'd have in
practice), averaged over both pollutants and folds. Error against the full-data truth is recorded alongside.

Writes outputs/cv_results.csv and outputs/cv_summary.md.
"""
import argparse
import itertools
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from model import KEY, TARGETS, Encoding, fit, predict

HERE = Path(__file__).parent
N_FOLDS, HORIZON_DAYS, STEP_DAYS = 12, 15, 30
CUTOFFS = pd.Timestamp("2017-02-28") - pd.Timedelta(days=HORIZON_DAYS) - pd.to_timedelta(
    STEP_DAYS * np.arange(N_FOLDS - 1, -1, -1), unit="D")
CHECKPOINTS = [100, 200, 300, 500, 750, 1000]
GRID = [dict(rough=r, spacing=s) for r, s in itertools.product([1e2, 1e3, 1e4, 1e5], [15, 30, 60])]
FIXED = dict(lr=5e-3, hidden=64, weight_decay=1e-4, station_l2=1e-3, schedule=max(CHECKPOINTS), seed=0)


def load():
    sparse = pd.read_parquet(HERE / "data" / "daily_sparse.parquet")
    full = pd.read_parquet(HERE / "data" / "daily_full.parquet")
    return sparse, full


def smooth_truth(full: pd.DataFrame, window: int = 31) -> pd.DataFrame:
    """The 'true prevailing level': centred rolling mean of the full-data daily means (log scale), n set to 1."""
    out = []
    for (st, pol), g in full.sort_values("date").groupby(["station", "pollutant"]):
        s = np.log(g.set_index("date")["value"]).asfreq("D").rolling(window, center=True, min_periods=window // 2).mean()
        out.append(pd.DataFrame({"station": st, "pollutant": pol, "date": s.index, "value": np.exp(s.values), "n": 1.0}))
    return pd.concat(out).dropna()


def wmae_log(obs, pred, w):
    ok = ~np.isnan(pred) & ~np.isnan(obs)
    return np.average(np.abs(np.log(pred[ok]) - np.log(obs[ok])), weights=w[ok])


def score(val, pred, prefix):
    r = val.merge(pred, on=KEY + ["pollutant"])
    out = {}
    for t in TARGETS:
        s = r[r["pollutant"] == t]
        out[f"{prefix}_{t}"] = wmae_log(s["value"].to_numpy(float), s["pred"].to_numpy(float), s["n"].to_numpy(float))
    out[f"{prefix}_mean"] = np.mean([out[f"{prefix}_{t}"] for t in TARGETS])
    return out


def run_config(i_cfg):
    torch.set_num_threads(1)
    i, cfg = i_cfg
    cfg = {**FIXED, **cfg}
    sparse, full = load()
    level = smooth_truth(full)
    rows = []
    for fold, cutoff in enumerate(CUTOFFS, 1):
        end = cutoff + pd.Timedelta(days=HORIZON_DAYS)
        train = sparse[sparse["date"] <= cutoff]
        val_sparse = sparse[(sparse["date"] > cutoff) & (sparse["date"] <= end)]
        val_full = full[(full["date"] > cutoff) & (full["date"] <= end)]
        val_level = level[(level["date"] > cutoff) & (level["date"] <= end)]
        enc = Encoding.fit(train, end=end)
        keys = val_full[KEY].drop_duplicates()

        def evaluate(step, model):
            pred = predict(model, enc, keys)
            rows.append(dict(config=i, fold=fold, step=step, rough=cfg["rough"], spacing=cfg["spacing"],
                             **score(val_sparse, pred, "sparse"), **score(val_full, pred, "truth"),
                             **score(val_level, pred, "level")))

        fit(enc, enc.wide(train), cfg, max(CHECKPOINTS), on_checkpoint=evaluate, checkpoints=CHECKPOINTS)
    return rows


def baseline_scores(sparse, full):
    """Per-station trailing 30-day hour-weighted mean of the sparse data, held flat over the next HORIZON_DAYS days."""
    rows = []
    for fold, cutoff in enumerate(CUTOFFS, 1):
        end = cutoff + pd.Timedelta(days=HORIZON_DAYS)
        hist = sparse[(sparse["date"] > cutoff - pd.Timedelta(days=30)) & (sparse["date"] <= cutoff)]
        level = (hist.assign(lw=np.log(hist["value"]) * hist["n"]).groupby(["station", "pollutant"])
                 .apply(lambda g: np.exp(g["lw"].sum() / g["n"].sum())).rename("pred").reset_index())
        for name, val in [("sparse", sparse), ("truth", full), ("level", smooth_truth(full))]:
            v = val[(val["date"] > cutoff) & (val["date"] <= end)].merge(level, on=["station", "pollutant"])
            rows.append(dict(fold=fold, kind=name, **{t: wmae_log(v.loc[v["pollutant"] == t, "value"].to_numpy(float),
                                                                    v.loc[v["pollutant"] == t, "pred"].to_numpy(float),
                                                                    v.loc[v["pollutant"] == t, "n"].to_numpy(float))
                                                       for t in TARGETS}))
    return pd.DataFrame(rows).groupby("kind")[TARGETS].mean()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()
    out = HERE / "outputs"
    out.mkdir(exist_ok=True)
    with Pool(args.workers) as pool:
        res = pd.DataFrame([r for rows in pool.map(run_config, list(enumerate(GRID))) for r in rows])
    res.to_csv(out / "cv_results.csv", index=False)
    summ = (res.groupby(["config", "rough", "spacing", "step"])
            .agg(sparse_mean=("sparse_mean", "mean"), sparse_sd=("sparse_mean", "std"),
                 **{f"sparse_{t}": (f"sparse_{t}", "mean") for t in TARGETS},
                 truth_mean=("truth_mean", "mean"), level_mean=("level_mean", "mean"))
            .reset_index().sort_values("sparse_mean"))
    base = baseline_scores(*load())
    lines = [f"# Time series CV ({pd.Timestamp.now():%Y-%m-%d %H:%M})", "",
             f"{len(CUTOFFS)} sequential expanding folds (cutoffs {CUTOFFS[0]:%Y-%m-%d} to {CUTOFFS[-1]:%Y-%m-%d}, every {STEP_DAYS} days), "
             f"{HORIZON_DAYS}-day look-ahead validation; {len(GRID)} configs × {len(CHECKPOINTS)} step counts. "
             "Metric: hour-weighted mean absolute log error (0.10 ≈ 10% typical error). `sparse_*` = against the thinned "
             "readings (used for selection); `truth_mean` = against full-data daily means; `level_mean` = against the "
             "31-day centred mean of the full data (the true smooth level).", "",
             "## Top 10", "", summ.head(10).drop(columns="config").round(4).to_markdown(index=False, floatfmt="g"), "",
             "## Baseline: trailing 30-day mean of the sparse data per station", "",
             base.round(4).to_markdown(floatfmt="g")]
    (out / "cv_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
