"""populace#359 Build I — STEP 3: warm-start reselection (frozen + misc protect-swap).

Corrected-#346 realization that IS wired end-to-end (informed_init L0 is not):
  - initialize from the frozen 57,240 (warm start, NOT cold, NOT weight-proportional).
  - ADD the top-N positive-`miscellaneous_income` carriers the frozen set lacks
    (misc's dominant carriers — the selection-support deficit that failed Build H).
  - REMOVE an equal count of the most-SUBSTITUTABLE frozen records: lowest
    max-leverage (max_t |v_it|/Σ_j|v_jt|), misc-ZERO, and NOT in P_structural
    (never evict a dominant carrier of any target). The diffuse portfolio the
    frozen selection already balances is preserved; the sparse weight solve then
    rebalances (the combinatorial step #346 says a ranked prior cannot replace).
  - hold |selection| == 57,240 exactly.

Usage: build_reselection.py --n-add N [--tag buildi_Nxxxx]
Outputs positions (0..337703) + overlap stats. Step 4 de-risks; Step 5 writes the
manifest. STAGING/LOCAL ONLY.
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import numpy as np

CORE = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime/out/core")
PROT = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime/out/protect")
OUT = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime/out/selections")
OUT.mkdir(parents=True, exist_ok=True)
K = 57240
NEAR_SOLE = 0.9  # also force in any near-sole carrier (>=0.9 leverage) frozen lacks


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-add", type=int, default=0, help="top-N positive-misc carriers to add")
    ap.add_argument("--add-pos", type=int, default=None, help="alias for --n-add")
    ap.add_argument("--add-neg", type=int, default=0, help="top-N |misc| NEGATIVE carriers to add (loss leg)")
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    Npos = args.add_pos if args.add_pos is not None else args.n_add
    Nneg = args.add_neg
    tag = args.tag or f"buildi_pos{Npos}_neg{Nneg}"

    meta = np.load(CORE / "core_meta.npz", allow_pickle=True)
    eff = np.load(CORE / "export_effval.npz")
    prot = np.load(PROT / "protect.npz")
    n = meta["household_id"].size
    frozen = meta["frozen_pos"].astype(np.int64)
    bw = meta["base_weight"]
    misc = eff["miscellaneous_income"]
    P = prot["P_structural"].astype(np.int64)
    max_lev = prot["max_lev_per_record"]
    top1_lev = prot["top1_leverage"]
    top1_carrier = prot["top1_carrier"].astype(np.int64)
    misc_rank = prot["misc_rank"].astype(np.int64)  # positive-misc addable, ranked by misc desc

    in_frozen = np.zeros(n, bool); in_frozen[frozen] = True
    in_P = np.zeros(n, bool); in_P[P] = True

    # ---- additions: top-Npos positive + top-Nneg |misc| negative carriers outside frozen ----
    add_pos = misc_rank[:Npos]
    assert np.all(~in_frozen[add_pos]) and (add_pos.size == 0 or np.all(misc[add_pos] > 0))
    neg_out = np.where((misc < 0) & (~in_frozen))[0]
    neg_rank = neg_out[np.argsort(-np.abs(misc[neg_out]))]  # by |misc| desc
    add_neg = neg_rank[:Nneg]
    # near-sole (>=0.9) carriers of any target that frozen lacks — force in for safety
    near_sole_carriers = np.unique(top1_carrier[(top1_lev >= NEAR_SOLE) & (top1_carrier >= 0)])
    add_near_sole = np.array([c for c in near_sole_carriers if not in_frozen[c]], dtype=np.int64)
    additions = np.unique(np.concatenate([add_pos, add_neg, add_near_sole]))
    n_add = additions.size
    log(f"additions: {n_add}  (pos top-{Npos}={add_pos.size}, neg top-{Nneg}={add_neg.size}, "
        f"near-sole frozen lacks={add_near_sole.size})")

    # ---- removals: lowest max-leverage frozen records, misc-zero, not in P ----
    removable = frozen[(misc[frozen] == 0) & (~in_P[frozen])]
    log(f"removal candidates (frozen, misc==0, not in P_structural): {removable.size}")
    order = removable[np.argsort(max_lev[removable], kind="stable")]  # ascending leverage
    removals = np.sort(order[:n_add])
    assert removals.size == n_add, (removals.size, n_add)
    log(f"removals: {removals.size}  max_lev range [{max_lev[removals].min():.3g}, {max_lev[removals].max():.3g}] "
        f"(vs pool median {np.median(max_lev):.3g})")

    # ---- compose ----
    keep = frozen[~np.isin(frozen, removals)]
    new_sel = np.sort(np.unique(np.concatenate([keep, additions]))).astype(np.int64)
    assert new_sel.size == K, f"selection size {new_sel.size} != {K}"
    # safety asserts
    assert np.intersect1d(removals, P).size == 0, "removed a dominant carrier"
    assert np.intersect1d(removals, additions).size == 0
    assert (misc[removals] == 0).all(), "removed a misc carrier"

    # ---- overlap + misc support stats ----
    overlap = np.intersect1d(new_sel, frozen).size
    entered = np.setdiff1d(new_sel, frozen)
    left = np.setdiff1d(frozen, new_sel)
    misc_before = int((misc[frozen] != 0).sum())
    misc_after = int((misc[new_sel] != 0).sum())
    posbase_before = float((bw[frozen] * misc[frozen] * (misc[frozen] > 0)).sum())
    posbase_after = float((bw[new_sel] * misc[new_sel] * (misc[new_sel] > 0)).sum())
    log(f"selection {new_sel.size}: overlap_with_frozen={overlap} ({overlap/K:.3%}) "
        f"entered={entered.size} left={left.size}")
    log(f"misc-nonzero: frozen {misc_before} -> new {misc_after}  (+{misc_after-misc_before})")
    log(f"positive-misc base mass: frozen {posbase_before:.4g} -> new {posbase_after:.4g}")

    np.save(OUT / f"sel_{tag}.npy", new_sel)
    report = {
        "tag": tag, "add_pos": int(Npos), "add_neg": int(Nneg), "n_add_effective": int(n_add),
        "n_selected": int(new_sel.size), "overlap_with_frozen": int(overlap),
        "overlap_frac": overlap / K, "entered": int(entered.size), "left": int(left.size),
        "removals_maxlev_min": float(max_lev[removals].min()),
        "removals_maxlev_max": float(max_lev[removals].max()),
        "misc_nonzero_frozen": misc_before, "misc_nonzero_new": misc_after,
        "positive_misc_base_mass_frozen": posbase_before,
        "positive_misc_base_mass_new": posbase_after,
        "near_sole_forced_in": int(add_near_sole.size),
    }
    json.dump(report, open(OUT / f"report_{tag}.json", "w"), indent=2)
    log(f"saved sel_{tag}.npy + report to {OUT}")


if __name__ == "__main__":
    main()
