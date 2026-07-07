"""populace#346 — STEP 02c: headline EDA facts (selected vs not).

Answers Max's specific #346 question: are LOW dense-weight / HIGH
contribution-share records over-represented among the selected? Produces:
  - selection rate over a dense-weight x max-contribution-share quantile grid,
  - point-biserial-style separation (AUC of a single feature vs label),
  - the decisive contrast: corr(dense weight, selected) vs corr(share, selected),
  - quantile tables (p10/50/90) of each feature for selected vs unselected.

Usage: eda_headline.py --tag dense   (uses features_{tag}.npz + core_meta)
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score

FEAT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/features")
CORE = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/core")
OUT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/eda")
OUT.mkdir(parents=True, exist_ok=True)


def qbin(x, q):
    """Quantile-bin index 0..q-1 (rank-based; robust to ties/heavy tails)."""
    ranks = np.argsort(np.argsort(x))
    return np.minimum((ranks * q // len(x)).astype(int), q - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    f = np.load(FEAT / f"features_{args.tag}.npz", allow_pickle=True)
    y = f["label"].astype(int)
    w = f["weight_used"].astype(float)            # dense (or base) weight
    share = f["max_share_tgt"].astype(float)      # Max's max contribution share
    carrier = f["max_carrier"].astype(float)      # dominant-carrier / leverage proxy
    n = y.size
    base_rate = y.mean()
    out = {"tag": args.tag, "n": int(n), "base_rate": float(base_rate)}

    # single-feature AUCs (which lone signal best separates selected?)
    out["auc_single"] = {
        "dense_weight": float(roc_auc_score(y, w)),
        "log_dense_weight": float(roc_auc_score(y, np.log1p(w))),
        "max_contribution_share": float(roc_auc_score(y, share)),
        "max_carrier": float(roc_auc_score(y, carrier)),
    }
    # decisive correlations with the selection indicator
    out["corr_with_selected"] = {
        "dense_weight": float(np.corrcoef(w, y)[0, 1]),
        "max_contribution_share": float(np.corrcoef(share, y)[0, 1]),
        "max_carrier": float(np.corrcoef(carrier, y)[0, 1]),
    }
    # quantiles p10/50/90 for selected vs unselected
    def q(v, m):
        return [float(np.quantile(v[m], p)) for p in (0.1, 0.5, 0.9)]
    out["quantiles_p10_50_90"] = {
        name: {"selected": q(v, y == 1), "unselected": q(v, y == 0)}
        for name, v in [("dense_weight", w), ("max_contribution_share", share),
                        ("max_carrier", carrier)]
    }

    # 5x5 selection-rate grid: dense-weight quantile (rows) x share quantile (cols)
    Q = 5
    wb = qbin(w, Q); sb = qbin(share, Q)
    grid = np.zeros((Q, Q)); cnt = np.zeros((Q, Q))
    for i in range(Q):
        for j in range(Q):
            m = (wb == i) & (sb == j)
            cnt[i, j] = m.sum()
            grid[i, j] = y[m].mean() if m.sum() else np.nan
    out["grid_selection_rate"] = grid.tolist()
    out["grid_counts"] = cnt.astype(int).tolist()

    # Max's hypothesis cell: LOW weight (row 0) & HIGH share (col Q-1)
    lo_w_hi_s = grid[0, Q - 1]
    hi_w_lo_s = grid[Q - 1, 0]
    out["hypothesis"] = {
        "low_weight_high_share_selrate": float(lo_w_hi_s),
        "high_weight_low_share_selrate": float(hi_w_lo_s),
        "lift_low_weight_high_share_vs_baserate": float(lo_w_hi_s / base_rate),
    }

    print(json.dumps(out, indent=2))
    json.dump(out, open(OUT / f"eda_headline_{args.tag}.json", "w"), indent=2)
    # human-readable grid
    print(f"\n=== selection-rate grid ({args.tag}); rows=dense-weight quintile (0=low), "
          f"cols=max-share quintile (0=low); base rate={base_rate:.3f} ===")
    hdr = "        " + "".join(f" share_q{j}" for j in range(Q))
    print(hdr)
    for i in range(Q):
        print(f"weight_q{i} " + "".join(f"  {grid[i,j]:6.3f}" for j in range(Q)))


if __name__ == "__main__":
    main()
