"""populace#346 — STEP 06: mechanism diagnostic for the fourth-arm contrast.

Explains WHY the learned top-K support calibrates far worse than the frozen
support, from the label-independent core (no solve needed):
  - target COVERAGE: how many of the 5,521 targets have zero support (no selected
    record carries a nonzero value) under each selection — the record-level
    analogue of the zero-support gate. More uncovered targets => higher loss floor.
  - income-tax OVER-LOADING: the pre-solve, mass-repaired income-tax estimate vs
    the SOI target (why learned lands +60.88% and can't recover under ratio 5.0).
  - top-1% weight concentration after mass repair.
Selections compared: learned_hgb, learned_logit, contrib_share, frozen.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from scipy import sparse

RT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior")
CORE = RT / "core"; SELD = RT / "selections"; OUT = RT / "refit-direct"
BENCH = 334_200_000.0
IT = "irs_soi.ty2022.historic_table_2.us.all.income_tax_liability_amount@2024"
SS = "ssa_supplement.cy2024.oasdi_ssi_payments.social_security_benefits.payment_amount@2024"


def main():
    A = sparse.load_npz(CORE / "A_value_matrix.npz").tocsr()
    b = np.load(CORE / "b_target_vector.npy")
    names = json.load(open(CORE / "target_names.json"))
    row = {nm: i for i, nm in enumerate(names)}
    meta = np.load(CORE / "core_meta.npz", allow_pickle=True)
    base_w = meta["base_weight"].astype(float)
    hh_size = meta["hh_size"].astype(float)
    n_targets, n = A.shape
    # per-target support count over ALL records (for reference)
    Acsc = A.tocsc()
    Abin = (A != 0)
    out = {}
    for name in ["learned_hgb", "learned_logit", "contrib_share", "frozen"]:
        sel = np.load(SELD / f"sel_{name}.npy")
        pop0 = float((base_w[sel] * hh_size[sel]).sum())
        factor = BENCH / pop0
        w_init = base_w[sel] * factor          # mass-repaired initial weights
        # coverage: targets with zero support among selected records
        sub = Abin[:, sel]
        support = np.asarray(sub.sum(axis=1)).ravel()
        uncovered = int((support == 0).sum())
        # pre-solve income-tax & SS estimate
        Asub = A[:, sel]
        est_it = float(Asub[row[IT]].dot(w_init))
        est_ss = float(Asub[row[SS]].dot(w_init))
        it_pct = (est_it - b[row[IT]]) / b[row[IT]] * 100
        ss_pct = (est_ss - b[row[SS]]) / b[row[SS]] * 100
        w_sorted = np.sort(w_init)[::-1]
        top1 = float(w_sorted[: max(1, len(w_sorted) // 100)].sum() / w_init.sum())
        out[name] = {
            "n": int(sel.size), "pre_repair_person_pop": pop0,
            "mass_repair_factor": factor, "uncovered_targets": uncovered,
            "pre_solve_income_tax_pct": it_pct, "pre_solve_ss_pct": ss_pct,
            "top1pct_weight_share_initial": top1,
        }
        print(f"{name:14s} uncovered_targets={uncovered:4d}/{n_targets}  "
              f"repair_factor={factor:.3f}  pre-solve IT={it_pct:+.1f}%  SS={ss_pct:+.1f}%  "
              f"top1%wt={top1:.3f}")
    json.dump(out, open(OUT / "mechanism_diag.json", "w"), indent=2)
    print(f"\nsaved {OUT}/mechanism_diag.json")


if __name__ == "__main__":
    main()
