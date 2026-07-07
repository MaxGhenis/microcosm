"""populace#346 — STEP 03b: augment base features with dense-FINAL-weight features.

Tests the task's question directly: does the recovered Build G DENSE final weight
(densewts_direct/dense_household_weight.npy, final_loss 0.0413937) add ANY signal
for predicting selection BEYOND the base contribution/leverage/demographic
features? If not, that is the strongest form of Max's #346 catch: even the fully
solved dense weight — not just the raw base weight — is uninformative about which
records the selection keeps.

Builds features_augment.npz = EXACTLY the base feature columns (so the base model
is a strict nested subset) PLUS these dense-final-weight columns:
    dense_weight, log1p_dense_weight, dense_weight_rank (fractional 0..1),
    dense_x_max_share_tgt, dense_x_max_carrier, dense_x_sum_carrier,
    dense_x_n_targets_touched
weight_used is left = BASE weight so the nested comparison is clean; the standalone
predictive power of the dense FINAL weight is reported here explicitly (AUC/AP) as
the rigorous successor to the base run's base-weight "Prior: dense weight" row.
"""
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score

FEAT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/features")
DENSE = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/densewts_direct/dense_household_weight.npy")
MODELS = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/models")


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    t0 = time.time()
    base = np.load(FEAT / "features_base.npz", allow_pickle=True)
    names = [str(n) for n in base["feature_names"]]
    feats = {n: base[n] for n in names}          # includes "label"
    y = base["label"].astype(int)
    n = y.size
    dw = np.load(DENSE).astype(np.float64)
    assert dw.size == n, (dw.size, n)
    log(f"base features={len([k for k in feats if k!='label'])} n={n}  "
        f"dense weight: sum={dw.sum():.6g} min={dw.min():.4g} max={dw.max():.4g}")

    # dense-FINAL-weight-derived features
    rank = np.argsort(np.argsort(dw)) / (n - 1)   # fractional rank 0..1
    dense_cols = {
        "dense_weight": dw,
        "log1p_dense_weight": np.log1p(dw),
        "dense_weight_rank": rank,
        "dense_x_max_share_tgt": dw * feats["max_share_tgt"],
        "dense_x_max_carrier": dw * feats["max_carrier"],
        "dense_x_sum_carrier": dw * feats["sum_carrier"],
        "dense_x_n_targets_touched": dw * feats["n_targets_touched"],
    }
    for k, v in dense_cols.items():
        feats[k] = v.astype(np.float64)

    # rigorous standalone predictive power of the dense FINAL weight (monotonic
    # transforms share AUC; AP differs). This is the successor to the base run's
    # base-weight "Prior: dense weight" ablation row (AUC 0.504532).
    standalone = {
        "dense_final_weight": {
            "roc_auc": float(roc_auc_score(y, dw)),
            "pr_auc": float(average_precision_score(y, dw)),
        },
        "log1p_dense_final_weight": {
            "roc_auc": float(roc_auc_score(y, np.log1p(dw))),
            "pr_auc": float(average_precision_score(y, np.log1p(dw))),
        },
    }
    log(f"standalone dense FINAL weight: AUC={standalone['dense_final_weight']['roc_auc']:.6f} "
        f"AP={standalone['dense_final_weight']['pr_auc']:.6f}  "
        f"(base run base-weight row was AUC 0.504532 / AP 0.170923)")

    feature_names = np.array(list(feats.keys()))  # includes "label"
    out = FEAT / "features_augment.npz"
    np.savez(out, **feats, feature_names=feature_names)
    MODELS.mkdir(parents=True, exist_ok=True)
    json.dump(standalone, open(MODELS / "dense_weight_standalone.json", "w"), indent=2)
    log(f"saved {out}  (added {len(dense_cols)} dense cols; "
        f"total features={len(feats)-1})  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
