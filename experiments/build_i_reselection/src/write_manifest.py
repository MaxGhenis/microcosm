"""populace#359 Build I — STEP 5: write the new selection-source manifest.

Takes a candidate selection (positions 0..337703 into the base household_id-sorted
order) and emits a selection-source manifest byte-compatible with the release
tool's `--selection-source-manifest` path, using the module's own
`write_selection_source_manifest` (so `identities_sha256` is computed by the
canonical recipe). Round-trips through `load_selection_source_from_manifest` +
`base_selection_mask` to prove the release will select EXACTLY these households.

Usage: write_manifest.py --selection sel_buildi_N1500.npy --out PATH.json [--n-add N]
STAGING/LOCAL ONLY.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, "tools")
import build_us_fiscal_refresh_release as release  # noqa: E402
from populace.build.us_runtime.warm_start_selection import (  # noqa: E402
    DEFAULT_SELECTION_JOIN_KEY, SelectionSource,
    _base_household_key_frame, write_selection_source_manifest,
    load_selection_source_from_manifest,
)

RT_I = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime")
BASE = Path("/Users/maxghenis/PolicyEngine/_worktrees/populace-build-f/out/"
            "base-f-20260705/base_populace_us_2024_puf_support.h5")
BASE_SHA = "18833fb68e60ee74461608d81a5c5ab7d52435e17026d9e3b062d9de18d6871f"
PARENT_SEL_SHA = "77363a4715c0d5acf54f5c1187d896c093cfcbfedceabe9b7b268a6cb46945c9"
SELDIR = RT_I / "out/selections"
K = 57240


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-add", type=int, default=None)
    args = ap.parse_args()

    p = SELDIR / args.selection if (SELDIR / args.selection).exists() else Path(args.selection)
    sel = np.sort(np.asarray(np.load(p), dtype=np.int64))
    assert sel.size == K and np.unique(sel).size == K, sel.size
    log(f"selection {sel.size}; loading base frame ...")

    base_frame = release._load_frame(BASE)
    base_key = _base_household_key_frame(base_frame, DEFAULT_SELECTION_JOIN_KEY)
    n = len(base_key)
    assert sel.max() < n
    sub = base_key.iloc[sel]
    # canonical python-typed identity rows aligned to join key
    identities = []
    for row in sub.itertuples(index=False, name=None):
        sy, shid, ch, cl = row
        identities.append([int(sy), int(shid), str(ch), int(cl)])
    log(f"built {len(identities)} identity rows")

    provenance = {
        "kind": "reselection",
        "method": "buildi-warmstart-misc-protect-swap",
        "issue": "PolicyEngine/populace#359",
        "base_h5_sha256": BASE_SHA,
        "parent_selection_identities_sha256": PARENT_SEL_SHA,
        "parent_selection": "certified_57k_selection_source (populace-us-2024-sparse-l0-refit-57k-71a0887)",
        "n_add": args.n_add,
    }
    src = SelectionSource(join_key=DEFAULT_SELECTION_JOIN_KEY, identities=identities,
                          provenance=provenance)
    out = Path(args.out)
    write_selection_source_manifest(src, out)
    log(f"wrote manifest {out}  identities_sha256={src.identities_sha256[:16]}… n_selected={src.n_identities}")

    # round-trip integrity + join verification
    reloaded = load_selection_source_from_manifest(out)
    mask, report = reloaded.base_selection_mask(base_frame, mode="frozen_support")
    got = np.nonzero(mask)[0].astype(np.int64)
    ok = np.array_equal(got, sel)
    log(f"round-trip: n_selected={report.n_selected} n_unmapped={report.n_unmapped} "
        f"n_ambiguous={report.n_ambiguous}; join==selection: {ok}")
    assert report.n_unmapped == 0 and report.n_ambiguous == 0 and ok, "manifest does not reselect exactly"
    log("manifest verified: the release will select EXACTLY this 57,240-record support.")


if __name__ == "__main__":
    main()
