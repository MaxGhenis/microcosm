"""populace#359 Build I — STEP 2: protect-list construction (dominant carrier per target).

Implements the corrected #346 point 4: records that are the sole/dominant carrier of
ANY target's support are protected from pruning — the record-level analogue of the
zero-support gate's cell-level check. Preserves the frozen selection's balanced
portfolio (#346 point 3) so a warm-start reselection can add misc support without
starving the other 5,532 targets.

Two components, saved separately so Step 3 can compose them:
  - P_structural : union over the 5,533 targets of each target's dominant carrier(s).
      Dominant carrier(s) of target t = the argmax-leverage record ALWAYS, plus any
      record with leverage_it = |A[t,i]| / Σ_j|A[t,j]| >= TAU (co-dominant / sole
      carriers of concentrated targets). Never removed in the reselection.
  - misc_rank : positive-`miscellaneous_income` carriers outside the frozen set,
      ranked by |misc|, with cumulative base-weighted mass — the explicit misc
      dominant-carrier list (the active fix). Step 3 takes the top-N.

Reports every count. Fast, low-memory (sparse row scan over A). STAGING/LOCAL ONLY.
"""
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
from scipy import sparse

CORE = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime/out/core")
OUT = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime/out/protect")
OUT.mkdir(parents=True, exist_ok=True)
TAU = 0.5  # leverage threshold for a co-dominant/sole carrier (>50% of a target's abs mass)


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    t0 = time.time()
    A = sparse.load_npz(CORE / "A_value_matrix.npz").tocsr()
    b = np.load(CORE / "b_target_vector.npy")
    names = json.load(open(CORE / "target_names.json"))
    meta = np.load(CORE / "core_meta.npz", allow_pickle=True)
    eff = np.load(CORE / "export_effval.npz")
    bw = meta["base_weight"]
    frozen = meta["frozen_pos"]
    n = A.shape[1]; T = A.shape[0]
    misc = eff["miscellaneous_income"]
    in_frozen = np.zeros(n, bool); in_frozen[frozen] = True
    log(f"A {A.shape} nnz={A.nnz}; frozen={frozen.size}; TAU={TAU}")

    # ---- per-target leverage scan: dominant carriers + per-record max leverage ----
    Aabs = abs(A)
    row_abs_sum = np.asarray(Aabs.sum(axis=1)).ravel()  # Σ_j|A[t,j]| per target
    indptr, indices, data = Aabs.indptr, Aabs.indices, Aabs.data
    top1_carrier = np.full(T, -1, np.int64)
    top1_leverage = np.zeros(T, np.float64)
    max_lev_per_record = np.zeros(n, np.float64)  # how irreplaceable each record is
    n_carriers_ge_tau = np.zeros(T, np.int64)
    protect_structural = set()
    for t in range(T):
        s, e = indptr[t], indptr[t + 1]
        if e == s or row_abs_sum[t] <= 0:
            continue
        idx = indices[s:e]; val = data[s:e]
        lev = val / row_abs_sum[t]
        # per-record running max leverage
        np.maximum.at(max_lev_per_record, idx, lev)
        jmax = int(np.argmax(lev))
        top1_carrier[t] = idx[jmax]; top1_leverage[t] = lev[jmax]
        protect_structural.add(int(idx[jmax]))
        ge = idx[lev >= TAU]
        n_carriers_ge_tau[t] = ge.size
        protect_structural.update(int(i) for i in ge.tolist())
    P = np.array(sorted(protect_structural), dtype=np.int64)
    log(f"P_structural: {P.size} records ({P.size/n:.3%} of pool); "
        f"targets with a >=TAU carrier: {int((n_carriers_ge_tau>0).sum())}/{T}; "
        f"targets whose top-1 carrier leverage>=0.9 (near-sole): {int((top1_leverage>=0.9).sum())}")

    # coverage of P by the frozen set (portfolio-preservation check)
    P_in_frozen = int(in_frozen[P].sum())
    log(f"P_structural in frozen: {P_in_frozen}/{P.size} ({P_in_frozen/P.size:.3%}); "
        f"P_structural NOT in frozen (structural additions): {P.size - P_in_frozen}")

    # ---- contribution share (weighted) context: max_t bw_i*|A[t,i]|/|b_t| ----
    # per-record max contribution share (the #346 formula signal)
    bpos = np.where(b != 0, np.abs(b), np.inf)
    contrib_max = np.zeros(n, np.float64)
    for t in range(T):
        s, e = indptr[t], indptr[t + 1]
        if e == s:
            continue
        idx = indices[s:e]; val = data[s:e]
        share = (bw[idx] * val) / bpos[t]
        np.maximum.at(contrib_max, idx, share)
    log(f"contrib_max: median={np.median(contrib_max):.4g} p99={np.percentile(contrib_max,99):.4g} "
        f"max={contrib_max.max():.4g}")

    # ---- misc dominant-carrier ranking (positive, outside frozen) ----
    pos_out = np.where((misc > 0) & (~in_frozen))[0]
    order = pos_out[np.argsort(-misc[pos_out])]  # desc by misc value
    cum_base = np.cumsum(bw[order] * misc[order])
    misc_rank = order  # positions, ranked
    # how many of these are already dominant carriers of misc's own targets
    log(f"misc addable positive carriers: {pos_out.size}; "
        f"cumulative base mass @[200,500,1000,1500,2000]="
        f"{[float(cum_base[min(k,cum_base.size)-1]) for k in (200,500,1000,1500,2000)]}")

    # frozen misc support (for the before/after report)
    log(f"frozen misc-nonzero: {int((misc[frozen]!=0).sum())} "
        f"(pos {int((misc[frozen]>0).sum())} / neg {int((misc[frozen]<0).sum())}); "
        f"frozen positive-misc base mass {float((bw[frozen]*misc[frozen]*(misc[frozen]>0)).sum()):.4g}")

    np.savez(OUT / "protect.npz",
             P_structural=P, top1_carrier=top1_carrier, top1_leverage=top1_leverage,
             n_carriers_ge_tau=n_carriers_ge_tau, max_lev_per_record=max_lev_per_record,
             contrib_max=contrib_max, misc_rank=misc_rank, misc_rank_cumbase=cum_base,
             tau=TAU)
    report = {
        "tau": TAU, "n_pool": int(n), "n_targets": int(T), "frozen": int(frozen.size),
        "P_structural_size": int(P.size),
        "P_structural_in_frozen": int(P_in_frozen),
        "P_structural_additions": int(P.size - P_in_frozen),
        "targets_with_ge_tau_carrier": int((n_carriers_ge_tau > 0).sum()),
        "targets_near_sole_top1_ge_0.9": int((top1_leverage >= 0.9).sum()),
        "misc_addable_positive": int(pos_out.size),
        "misc_cum_base_at": {str(k): float(cum_base[min(k, cum_base.size) - 1])
                             for k in (200, 500, 1000, 1500, 2000)},
        "frozen_positive_misc_base_mass": float((bw[frozen] * misc[frozen] * (misc[frozen] > 0)).sum()),
    }
    json.dump(report, open(OUT / "protect_report.json", "w"), indent=2)
    log(f"saved protect artifacts to {OUT}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
