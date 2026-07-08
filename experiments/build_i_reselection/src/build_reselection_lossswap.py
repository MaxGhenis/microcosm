"""populace#359 Build I — STEP 3b: loss-swap reselection (the diagnosed fix).

Diagnosis (Step 4a/4b): misc export = net_income_leg − net_loss_leg. net_income is
hit perfectly; the export is killed by the net_LOSS leg overshooting because the
sparse frame is mass-repaired ×5.2 so the 5.0 ratio cap permits 26× effective
weights, and the solve MAXES high-income negative-misc carriers (their per-target
contribution is ~0% — they are convenient high-income records, and nothing
penalises their misc loss). Adding negative carriers makes it worse (−201%…−232%).

Fix: REMOVE the biggest-|misc| negative carriers (the ones the solve maxes into a
huge net_loss) and REPLACE them with high-AGI, misc-ZERO "absorber" records so the
solve maxes those for the high-income targets instead — contributing ~0 to net_loss.
Keep the small-|misc| negative carriers so the misc net_loss target retains support
(never zero it → that would create a zero-support cell outside the 2 reviewed
exclusions). Warm-start from frozen; protect P_structural; hold 57,240.

Usage: build_reselection_lossswap.py --rm-loss K --absorber {agi,lowlev} [--add-pos P] [--tag T]
STAGING/LOCAL ONLY.
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import numpy as np

CORE = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime/out/core")
PROT = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime/out/protect")
OUT = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime/out/selections")
K = 57240


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rm-loss", type=int, required=True, help="remove top-K biggest-|misc| neg carriers")
    ap.add_argument("--absorber", choices=["agi", "lowlev"], default="agi")
    ap.add_argument("--add-pos", type=int, default=0, help="also add top-P positive-misc for net_income margin")
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    Krm = args.rm_loss
    tag = args.tag or f"buildi_rmloss{Krm}_{args.absorber}_pos{args.add_pos}"

    meta = np.load(CORE / "core_meta.npz", allow_pickle=True)
    eff = np.load(CORE / "export_effval.npz")
    prot = np.load(PROT / "protect.npz")
    n = meta["household_id"].size
    frozen = meta["frozen_pos"].astype(np.int64)
    bw = meta["base_weight"]; agi = meta["agi"]; misc = eff["miscellaneous_income"]
    P = prot["P_structural"].astype(np.int64); max_lev = prot["max_lev_per_record"]
    misc_rank = prot["misc_rank"].astype(np.int64)
    in_frozen = np.zeros(n, bool); in_frozen[frozen] = True
    in_P = np.zeros(n, bool); in_P[P] = True

    # ---- REMOVE: top-Krm biggest-|misc| NEGATIVE carriers in frozen, not in P_structural ----
    fneg = frozen[(misc[frozen] < 0) & (~in_P[frozen])]
    fneg_by_absmisc = fneg[np.argsort(-np.abs(misc[fneg]))]
    rm_loss = fneg_by_absmisc[:Krm]
    n_neg_frozen = int((misc[frozen] < 0).sum())
    log(f"frozen neg carriers={n_neg_frozen} (P-protected {int(in_P[frozen][misc[frozen]<0].sum())}); "
        f"removing top-{Krm} by |misc| (|misc| range [{np.abs(misc[rm_loss]).min():.4g}, {np.abs(misc[rm_loss]).max():.4g}]); "
        f"neg carriers KEPT for net_loss support = {n_neg_frozen - rm_loss.size}")

    # optional positive-misc additions (net_income margin)
    add_pos = misc_rank[:args.add_pos] if args.add_pos else np.array([], np.int64)

    # ---- ADD absorbers: high-AGI misc-ZERO non-frozen records (or low-leverage misc-zero) ----
    n_add = rm_loss.size + add_pos.size
    cand = np.where((~in_frozen) & (misc == 0))[0]
    cand = cand[~np.isin(cand, add_pos)]
    if args.absorber == "agi":
        absorbers = cand[np.argsort(-agi[cand])][:rm_loss.size]  # highest AGI
        log(f"absorbers: {absorbers.size} high-AGI misc-zero (AGI range [{agi[absorbers].min():.4g}, {agi[absorbers].max():.4g}])")
    else:
        absorbers = cand[np.argsort(max_lev[cand])][:rm_loss.size]  # lowest leverage
        log(f"absorbers: {absorbers.size} low-leverage misc-zero")
    additions = np.unique(np.concatenate([add_pos, absorbers]))

    # ---- also remove low-leverage misc-zero fillers if additions > rm_loss (from add_pos) ----
    extra_rm = additions.size - rm_loss.size
    if extra_rm > 0:
        removable = frozen[(misc[frozen] == 0) & (~in_P[frozen]) & (~np.isin(frozen, additions))]
        removable = removable[np.argsort(max_lev[removable])]
        rm_extra = removable[:extra_rm]
    else:
        rm_extra = np.array([], np.int64)
    removals = np.unique(np.concatenate([rm_loss, rm_extra]))
    # balance sizes exactly
    assert removals.size == additions.size, (removals.size, additions.size)

    keep = frozen[~np.isin(frozen, removals)]
    new_sel = np.sort(np.unique(np.concatenate([keep, additions]))).astype(np.int64)
    assert new_sel.size == K, new_sel.size
    assert np.intersect1d(removals, P).size == 0

    overlap = np.intersect1d(new_sel, frozen).size
    misc_after = int((misc[new_sel] != 0).sum())
    neg_after = int((misc[new_sel] < 0).sum())
    OUT.mkdir(parents=True, exist_ok=True)
    np.save(OUT / f"sel_{tag}.npy", new_sel)
    rep = {"tag": tag, "rm_loss": int(rm_loss.size), "add_pos": int(add_pos.size),
           "absorbers": int(absorbers.size), "absorber_kind": args.absorber,
           "n_selected": int(new_sel.size), "overlap_with_frozen": int(overlap),
           "overlap_frac": overlap / K, "neg_carriers_after": neg_after,
           "misc_nonzero_after": misc_after}
    json.dump(rep, open(OUT / f"report_{tag}.json", "w"), indent=2)
    log(f"{tag}: overlap={overlap} ({overlap/K:.3%}) neg_after={neg_after} misc_after={misc_after} -> sel_{tag}.npy")


if __name__ == "__main__":
    main()
