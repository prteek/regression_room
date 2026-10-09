"""Final fit on all sparse data with the best time-series CV settings (15-day look-ahead); compare joint vs single-target models vs a
simple smoothing baseline against the ground truth.

Day types (per station x pollutant):
- observed: the sparse data has readings that day (denoising);
- unobserved: no readings that day, outside the gap blocks (filling isolated holes);
- gap: inside the original 20-60 day gap blocks (filling long gaps; never used for tuning);
- other-observed: this pollutant missing but the other one observed that day (where joint modelling should help).
Truth: the 31-day centred mean of the full hourly data ("level") and the full-data daily mean ("daily").

Writes outputs/evaluation.md, outputs/predictions.parquet and outputs/final_*.pt.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from cv import CHECKPOINTS, FIXED, load, smooth_truth, wmae_log
from model import KEY, TARGETS, Encoding, fit, predict

HERE = Path(__file__).parent


def best_config():
    r = pd.read_csv(HERE / "outputs" / "cv_results.csv")
    b = r.groupby(["rough", "spacing", "step"])["sparse_mean"].mean().idxmin()
    return {**FIXED, "rough": b[0], "spacing": int(b[1])}, int(b[2])


def baseline(sparse: pd.DataFrame, keys: pd.DataFrame, half_window: int = 15) -> pd.DataFrame:
    """Hour-weighted mean of log readings within +-half_window days of each day, per station x pollutant."""
    out = []
    for (st, pol), g in sparse.groupby(["station", "pollutant"]):
        s = g.set_index("date")
        lw = (np.log(s["value"]) * s["n"]).asfreq("D").fillna(0)
        n = s["n"].asfreq("D").fillna(0)
        w = 2 * half_window + 1
        lvl = np.exp(lw.rolling(w, center=True, min_periods=1).sum() / n.rolling(w, center=True, min_periods=1).sum())
        out.append(pd.DataFrame({"station": st, "pollutant": pol, "date": lvl.index, "pred": lvl.values}))
    return keys.merge(pd.concat(out), on=KEY + ["pollutant"], how="left")


def main():
    torch.set_num_threads(6)
    out = HERE / "outputs"
    sparse, full = load()
    level = smooth_truth(full)
    gaps = pd.read_parquet(HERE / "data" / "gaps.parquet").assign(gap=True)
    cfg, steps = best_config()
    enc = Encoding.fit(sparse, end=sparse["date"].max())
    w = enc.wide(sparse)
    grid = enc.grid()

    preds = {}
    model = fit(enc, w, cfg, steps)
    torch.save(model.state_dict(), out / "final_joint.pt")
    preds["joint"] = predict(model, enc, grid)
    single = []
    for t in TARGETS:
        m = fit(enc, w, cfg, steps, use=[t])
        torch.save(m.state_dict(), out / f"final_single_{t}.pt")
        single.append(predict(m, enc, grid).query("pollutant == @t"))
    preds["single-target"] = pd.concat(single)
    preds["±15-day mean"] = baseline(sparse, grid.merge(pd.DataFrame({"pollutant": TARGETS}), how="cross"))
    allp = pd.concat([p.assign(model=k) for k, p in preds.items()], ignore_index=True)
    allp.to_parquet(out / "predictions.parquet", index=False)

    # Day types
    cells = grid.merge(pd.DataFrame({"pollutant": TARGETS}), how="cross")
    obs = sparse[KEY + ["pollutant"]].assign(observed=True)
    cells = cells.merge(obs, on=KEY + ["pollutant"], how="left").merge(gaps, on=KEY + ["pollutant"], how="left")
    cells["observed"] = cells["observed"].fillna(False).astype(bool)
    cells["gap"] = cells["gap"].fillna(False).astype(bool)
    other = obs.assign(pollutant=obs["pollutant"].map({TARGETS[0]: TARGETS[1], TARGETS[1]: TARGETS[0]})).rename(columns={"observed": "other_obs"})
    cells = cells.merge(other, on=KEY + ["pollutant"], how="left")
    cells["other_obs"] = cells["other_obs"].fillna(False).astype(bool)
    types = {"observed": cells["observed"], "unobserved": ~cells["observed"] & ~cells["gap"], "gap": cells["gap"],
             "other-observed": ~cells["observed"] & cells["other_obs"]}

    rows = []
    for truth_name, truth in [("level", level), ("daily", full)]:
        for tname, sel in types.items():
            c = cells[sel][KEY + ["pollutant"]].merge(truth[KEY + ["pollutant", "value", "n"]], on=KEY + ["pollutant"])
            for mname, p in preds.items():
                r = c.merge(p, on=KEY + ["pollutant"])
                for t in TARGETS:
                    s = r[r["pollutant"] == t]
                    rows.append(dict(truth=truth_name, day_type=tname, model=mname, pollutant=t, days=len(s),
                                     error=wmae_log(s["value"].to_numpy(float), s["pred"].to_numpy(float), np.ones(len(s)))))
    res = pd.DataFrame(rows)
    # the sparse readings themselves, as an estimate of the level on observed days
    raw = cells[types["observed"]][KEY + ["pollutant"]].merge(sparse, on=KEY + ["pollutant"]).merge(
        level[KEY + ["pollutant", "value"]].rename(columns={"value": "lvl"}), on=KEY + ["pollutant"])
    raw_err = raw.groupby("pollutant").apply(lambda g: np.mean(np.abs(np.log(g["value"]) - np.log(g["lvl"]))))

    tab = res.pivot_table(index=["truth", "day_type", "pollutant"], columns="model", values="error").round(3)
    tab["days"] = res.groupby(["truth", "day_type", "pollutant"])["days"].first()
    lines = [f"# Final evaluation ({pd.Timestamp.now():%Y-%m-%d %H:%M})", "",
             f"Settings from time-series CV (15-day look-ahead): rough {cfg['rough']:g}, spacing {cfg['spacing']} days, {steps} steps. "
             "Error = mean absolute log error against the truth (0.10 ≈ 10%).", "",
             tab.reset_index().to_markdown(index=False, floatfmt="g"), "",
             f"Raw sparse readings as an estimate of the level on observed days: "
             + ", ".join(f"{t} {raw_err[t]:.3f}" for t in TARGETS)]
    (out / "evaluation.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
