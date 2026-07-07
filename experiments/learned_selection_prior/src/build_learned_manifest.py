"""populace#346 — STEP 04: build a selection-source manifest from a learned prior.

Selects the top-57,240 base records by a chosen prior score and writes a
selection-source manifest in the exact committed format (reusing the seam's
SelectionSource + write_selection_source_manifest, which auto-computes the
identity digest). This manifest feeds the frozen-support refit (STEP 05), the
fourth arm of the #299 table.

Usage: build_learned_manifest.py --scores model_scores_dense.npz --score oof_hgb --out PATH.json
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np

from populace.build.us_runtime.warm_start_selection import (
    DEFAULT_SELECTION_JOIN_KEY, SelectionSource, write_selection_source_manifest)

CORE = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/core")
MODELS = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/models")
K = 57240


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", required=True, help="model_scores_*.npz filename under models/")
    ap.add_argument("--score", required=True, help="array key: oof_hgb|oof_logit|formula_max_share|dense_weight")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    s = np.load(MODELS / args.scores)
    score = s[args.score].astype(np.float64)
    y = s["label"].astype(int)
    meta = np.load(CORE / "core_meta.npz", allow_pickle=True)
    sy = meta["source_year"].astype(int)
    sid = meta["source_id"].astype(int)
    ch = meta["channel"].astype(str)
    cl = meta["clone"].astype(int)
    n = score.size
    assert sy.size == n

    # top-K by score (ties broken by index; deterministic)
    order = np.lexsort((np.arange(n), -score))  # primary -score asc == score desc
    sel = order[:K]
    sel.sort()
    overlap = int(y[sel].sum())
    print(f"score={args.score}  top-{K} selected; overlap with frozen set = "
          f"{overlap} ({overlap/K:.1%})")

    identities = [[int(sy[i]), int(sid[i]), str(ch[i]), int(cl[i])] for i in sel]
    src = SelectionSource(
        join_key=DEFAULT_SELECTION_JOIN_KEY,
        identities=identities,
        provenance={
            "kind": "learned_prior",
            "score": args.score,
            "scores_file": args.scores,
            "base_dataset_sha256": "18833fb68e60ee74461608d81a5c5ab7d52435e17026d9e3b062d9de18d6871f",
            "note": "top-57240 base records by learned selection-prior probability (populace#346)",
            "overlap_with_frozen": overlap,
        },
    )
    out = Path(args.out)
    write_selection_source_manifest(src, out)
    print(f"wrote manifest {out}  n={src.n_identities}  sha={src.identities_sha256[:12]}")


if __name__ == "__main__":
    main()
