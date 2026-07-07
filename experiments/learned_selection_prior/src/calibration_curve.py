"""populace#346 — STEP 03c: reliability (calibration) curve for the OOF models.

Reads the saved out-of-fold probabilities (model_scores_{tag}.npz) and reports,
for each model, a reliability curve (mean predicted prob vs empirical selection
rate per bin) plus the Brier score and the base rate. No refit — the OOF scores
already are honest held-out predictions.

Two binnings: equal-width [0,1] deciles and equal-count (quantile) deciles.
Saves reliability_{tag}.json to out/learned-prior/models/.

Usage: calibration_curve.py --tag {base|augment}
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import numpy as np

MODELS = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/models")


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def reliability(score, y, n_bins=10, strategy="uniform"):
    score = np.asarray(score, float); y = np.asarray(y, int)
    if strategy == "uniform":
        edges = np.linspace(0.0, 1.0, n_bins + 1)
    else:  # quantile
        edges = np.unique(np.quantile(score, np.linspace(0, 1, n_bins + 1)))
    idx = np.clip(np.digitize(score, edges[1:-1]), 0, len(edges) - 2)
    rows = []
    for b in range(len(edges) - 1):
        m = idx == b
        if not m.any():
            continue
        rows.append({
            "bin": b,
            "n": int(m.sum()),
            "mean_pred": float(score[m].mean()),
            "frac_pos": float(y[m].mean()),
            "lo": float(edges[b]), "hi": float(edges[b + 1]),
        })
    brier = float(np.mean((score - y) ** 2))
    return {"strategy": strategy, "n_bins": n_bins, "brier": brier, "bins": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    s = np.load(MODELS / f"model_scores_{args.tag}.npz")
    y = s["label"].astype(int)
    out = {"tag": args.tag, "base_rate": float(y.mean()), "models": {}}
    for key in ("oof_hgb", "oof_logit"):
        if key not in s.files:
            continue
        out["models"][key] = {
            "uniform": reliability(s[key], y, 10, "uniform"),
            "quantile": reliability(s[key], y, 10, "quantile"),
        }
        u = out["models"][key]["uniform"]
        log(f"{args.tag}/{key}: Brier={u['brier']:.5f}  base_rate={y.mean():.4f}")
        log("  bin  n       mean_pred  frac_pos")
        for r in u["bins"]:
            log(f"  [{r['lo']:.1f},{r['hi']:.1f}) {r['n']:7d}  {r['mean_pred']:.4f}   {r['frac_pos']:.4f}")
    json.dump(out, open(MODELS / f"reliability_{args.tag}.json", "w"), indent=2)
    log(f"saved reliability_{args.tag}.json")


if __name__ == "__main__":
    main()
