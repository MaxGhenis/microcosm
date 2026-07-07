"""populace#346 — STEP 04b: build positional 57,240-record selections + overlap.

Produces the selections the fourth-arm direct solve consumes (positional indices
into the household_id-sorted checkpoint frame, 0..337703), plus the overlap
analysis vs the frozen certified selection.

Selections (each exactly K=57,240 records):
  - learned_hgb   : top-K by OOF HGB probability  (the fourth arm)
  - learned_logit : top-K by OOF logistic probability (secondary)
  - contrib_share : top-K by max contribution share (Max's formula baseline)
  - frozen        : the certified 57,240 (label positives) — matched control

Tie-breaking (documented): rank by score DESCENDING; exact ties broken by
ascending record index (household_id order) via lexsort((index, -score)). Take
the first K, then store ascending positions.

Overlap context: |learned ∩ frozen|, |contrib_share ∩ frozen|, and the random-
selection expected overlap E = rate * K = 0.1695 * 57240 ≈ 9702.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

CORE = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/core")
MODELS = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/models")
OUT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/selections")
OUT.mkdir(parents=True, exist_ok=True)
K = 57240


def topk_positions(score: np.ndarray, k: int = K) -> np.ndarray:
    n = score.size
    order = np.lexsort((np.arange(n), -score))  # score desc, ties by index asc
    sel = np.sort(order[:k])
    return sel.astype(np.int64)


def main():
    s = np.load(MODELS / "model_scores_base.npz")
    y = s["label"].astype(int)
    n = y.size
    frozen = np.nonzero(y == 1)[0].astype(np.int64)
    assert frozen.size == K, frozen.size
    frozen_set = set(frozen.tolist())
    rate = y.mean()

    sels = {
        "learned_hgb": topk_positions(s["oof_hgb"].astype(float)),
        "learned_logit": topk_positions(s["oof_logit"].astype(float)),
        "contrib_share": topk_positions(s["formula_max_share"].astype(float)),
        "frozen": frozen,
    }
    report = {"n": int(n), "K": K, "base_rate": float(rate),
              "random_expected_overlap_with_frozen": float(rate * K),
              "selections": {}}
    for name, sel in sels.items():
        np.save(OUT / f"sel_{name}.npy", sel)
        ov = len(frozen_set.intersection(sel.tolist()))
        report["selections"][name] = {
            "n": int(sel.size),
            "overlap_with_frozen": int(ov),
            "overlap_frac_of_K": ov / K,
            "lift_vs_random": (ov / K) / rate,
        }
        print(f"{name:14s} n={sel.size} overlap_with_frozen={ov} "
              f"({ov/K:.1%})  lift_vs_random={((ov/K)/rate):.2f}x")
    print(f"random expected overlap = {rate*K:,.0f} ({rate:.1%})")
    json.dump(report, open(OUT / "overlap_report.json", "w"), indent=2)
    print(f"saved selections + overlap_report.json to {OUT}")


if __name__ == "__main__":
    main()
