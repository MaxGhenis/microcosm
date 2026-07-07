"""populace#346 — STEP 02a: extract the label-independent core.

Builds, all aligned to household_id order (0..337703):
  - A  : sparse CSR (n_targets=5521, n_records=337704) = per-household value v_it
         (all targets are entity=household/filter=None/measure=column, so
          A[t,:] is exactly the checkpoint household column measure.name).
  - b  : target vector |target_t| (RHS), from the dense calibration_diagnostics.
  - base_weight : the frame's pre-calibration household weight (feature c).
  - demographics from the SAME checkpoint frame (household size, age structure,
    AGI income) + source_year from the base person table (feature d/e).
  - label y from frozen_support_mask.npy (verified aligned to household_id).

No feature here is derived from the label. Saves to OUT_DIR for the modeling
stages. Uses the venv-1764 interpreter (h5py/pandas/numpy/scipy).
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import h5py
from scipy import sparse

RT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime")
CKPT = RT / "checkpoints/buildg-dense/target_frame_checkpoint.h5"
DIAG = (RT / "out/buildg-run/releases/"
        "populace-us-2024-buildg-dense-129165b-20260706T231920Z/calibration_diagnostics.json")
BASE = Path("/Users/maxghenis/PolicyEngine/_worktrees/populace-build-f/out/"
            "base-f-20260705/base_populace_us_2024_puf_support.h5")
MASK = RT / "forensics/frozen_support_mask.npy"
OUT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/core")
OUT.mkdir(parents=True, exist_ok=True)

# national age bands (household columns) -> household age structure
AGE_BANDS = ["0_to_4","5_to_9","10_to_14","15_to_19","20_to_24","25_to_29",
             "30_to_34","35_to_39","40_to_44","45_to_49","50_to_54","55_to_59",
             "60_to_64","65_to_69","70_to_74","75_to_79","80_to_84","85_plus"]
AGE_COL = "census_pep.cy2024.national_resident_population_age.{}.population"
AGI_COL = "cbo.revenue_projection.ty2024.income_by_source.adjusted_gross_income.projected_amount"


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    t0 = time.time()
    diag = json.load(open(DIAG))
    targets = diag["targets"]
    tgt_names = [t["name"] for t in targets]
    tgt_measures = [t["measure"]["name"] for t in targets]
    b = np.array([float(t["target"]) for t in targets], dtype=np.float64)
    final_est = np.array([float(t["final_estimate"]) for t in targets], dtype=np.float64)
    log(f"targets: {len(targets)}  (b<=0: {(b<=0).sum()})")

    with h5py.File(CKPT, "r") as f:
        hh = f["tables/household"]
        cols = json.loads(hh.attrs["columns_json"])
        name2idx = {c: i for i, c in enumerate(cols)}
        colgrp = hh["columns"]

        def read_col(name):
            idx = name2idx[name]
            return np.asarray(colgrp[f"{idx:05d}/values"], dtype=np.float64)

        household_id = np.asarray(colgrp[f"{name2idx['household_id']:05d}/values"]).astype(np.int64)
        state_fips = np.asarray(colgrp[f"{name2idx['state_fips']:05d}/values"]).astype(np.int64)
        source_id = np.asarray(colgrp[f"{name2idx['household_source_id']:05d}/values"]).astype(np.int64)
        channel = np.asarray(colgrp[f"{name2idx['household_support_channel']:05d}/values"]).astype(str)
        clone = np.asarray(colgrp[f"{name2idx['household_support_clone_index']:05d}/values"]).astype(np.int64)
        n = household_id.size
        log(f"records: {n}  household_id monotonic 0..n-1: "
            f"{np.array_equal(household_id, np.arange(n))}")

        # base weight from the frame's stored weights
        wgrp = f["weights/household"]
        base_weight = np.asarray(wgrp["values"], dtype=np.float64)
        log(f"base_weight: sum={base_weight.sum():.6g} min={base_weight.min():.4g} "
            f"max={base_weight.max():.4g} kind={wgrp.attrs.get('kind')}")

        # ---- build A (targets x records) sparse ----
        rows, colsi, data = [], [], []
        dense_row_count = 0
        for t, meas in enumerate(tgt_measures):
            v = read_col(meas)
            nz = np.nonzero(v)[0]
            if nz.size == n:
                dense_row_count += 1
            rows.append(np.full(nz.size, t, dtype=np.int32))
            colsi.append(nz.astype(np.int32))
            data.append(v[nz])
            if (t + 1) % 1000 == 0:
                log(f"  built {t+1}/{len(tgt_measures)} target rows")
        rows = np.concatenate(rows); colsi = np.concatenate(colsi); data = np.concatenate(data)
        A = sparse.coo_array((data, (rows, colsi)), shape=(len(targets), n)).tocsr()
        log(f"A: shape={A.shape} nnz={A.nnz} (diag says 17709184) fully-dense-rows={dense_row_count}")

        # ---- demographics from the same frame ----
        age = np.stack([read_col(AGE_COL.format(bnd)) for bnd in AGE_BANDS], axis=1)  # (n,18)
        hh_size = age.sum(axis=1)
        n_child = age[:, :4].sum(axis=1)          # 0-19
        n_young_adult = age[:, 4:9].sum(axis=1)   # 20-44
        n_mid = age[:, 9:13].sum(axis=1)          # 45-64
        n_elderly = age[:, 13:].sum(axis=1)       # 65+
        agi = read_col(AGI_COL)

    # ---- base identity/weight/source_year, sorted by household_id (== MASK order) ----
    # The checkpoint household rows are stored in base-household_id-sorted order
    # (verified: (source_id,channel,clone) match positionally at frac 1.0). The
    # mask (forensics/join_check.py) is ALSO in base-household_id-sorted order.
    # So checkpoint columns, base rows, and the label are already aligned by
    # POSITION — no reorder; we VERIFY the positional identity match instead.
    log("loading base identity/weight/source_year (USSingleYearDataset) ...")
    from policyengine_us.data import USSingleYearDataset
    ds = USSingleYearDataset(file_path=str(BASE))
    bh = ds.household.sort_values("household_id").reset_index(drop=True)
    psy = (ds.person[["person_household_id", "source_year"]]
           .drop_duplicates("person_household_id"))
    bh = bh.merge(psy, left_on="household_id", right_on="person_household_id", how="left")
    assert len(bh) == n, (len(bh), n)
    # POSITIONAL alignment assertion (checkpoint order vs base-hid-sorted order)
    m_sid = (bh.household_source_id.to_numpy().astype(np.int64) == source_id).mean()
    m_ch = (bh.household_support_channel.to_numpy().astype(str) == channel).mean()
    m_cl = (bh.household_support_clone_index.to_numpy().astype(np.int64) == clone).mean()
    m_hid = (bh.household_id.to_numpy().astype(np.int64) == household_id).mean()
    log(f"POSITIONAL alignment ckpt<->base: source_id={m_sid:.4f} channel={m_ch:.4f} "
        f"clone={m_cl:.4f} household_id={m_hid:.4f}")
    assert m_sid == 1.0 and m_ch == 1.0 and m_cl == 1.0 and m_hid == 1.0, \
        "checkpoint rows are NOT in base-household_id order — alignment broken"
    source_year = bh.source_year.to_numpy().astype(np.int64)
    raw_base_weight = bh.household_weight.to_numpy().astype(np.float64)
    log(f"raw H5 base weight vs checkpoint initial weight: max abs diff="
        f"{np.abs(raw_base_weight - base_weight).max():.4g} "
        f"(expected small: base_population_scale mass repair)")

    # ---- verify A/b against the recorded base (initial) fit ----
    est_base = A @ base_weight
    ok = b != 0
    within10_base = float((np.abs(est_base[ok] - b[ok]) / np.abs(b[ok]) <= 0.10).mean())
    log(f"A/b check: base-weight within-10% = {within10_base:.4f} "
        f"(dense FINAL fraction_within_10pct recorded = 0.8616)")
    # income-tax national SOI liability estimate under base weights (context)

    # ---- label ----
    y = np.load(MASK).astype(np.int8)
    assert y.size == n and int(y.sum()) == 57240, (y.size, int(y.sum()))
    log(f"label: n={y.size} positives={int(y.sum())} rate={y.mean():.4f}")

    # ---- save ----
    sparse.save_npz(OUT / "A_value_matrix.npz", A)
    np.save(OUT / "b_target_vector.npy", b)
    np.save(OUT / "final_estimate.npy", final_est)
    json.dump(tgt_names, open(OUT / "target_names.json", "w"))
    json.dump(tgt_measures, open(OUT / "target_measures.json", "w"))
    np.savez(OUT / "core_meta.npz",
             household_id=household_id, state_fips=state_fips, source_id=source_id,
             channel=channel, clone=clone, source_year=source_year,
             base_weight=base_weight, raw_base_weight=raw_base_weight, label=y,
             hh_size=hh_size, n_child=n_child, n_young_adult=n_young_adult,
             n_mid=n_mid, n_elderly=n_elderly, agi=agi, age_bands=age)
    log(f"saved core to {OUT}  ({time.time()-t0:.1f}s)")
    # quick sanity: population target vs weighted hh_size
    pop_est = (base_weight * hh_size).sum()
    log(f"sanity: weighted person count (base) = {pop_est:,.0f} (benchmark ~334.2M)")


if __name__ == "__main__":
    main()
