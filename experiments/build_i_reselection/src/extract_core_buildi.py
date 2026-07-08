"""populace#359 Build I — STEP 1: extract the label-independent core (Build H registry).

Adapts the verified build-g extract_core.py to the Build H DENSE frame checkpoint
(registry d71c59514e3a, 5533 targets, 337,704 households) and adds the raw
export-mass INPUT columns (per household) for the 5 gate columns, plus a CANONICAL
frozen-selection <-> certified-manifest <-> base-frame positional bridge built
with the release tool's own frame loader + warm_start_selection helpers (so my
identities are byte-identical to what the release joins/consumes).

Outputs (aligned to the checkpoint == base household_id-sorted order):
  - A/b/final_estimate (target measure matrix), base_weight, demographics.
  - export_effval.npz : per-household effective value of each of the 5 gate columns
      (person cols summed per household; tax_unit col summed per household).
  - base_identities.npy : canonical [source_year, source_household_id, channel,
      clone] per household (object array) for Step 5 manifest construction.
  - core_meta.npz : frozen_pos (canonical, via manifest join) + cross-check vs the
      build-g forensic mask.

STAGING/LOCAL ONLY. Every number from source artifacts.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import h5py
from scipy import sparse

sys.path.insert(0, "tools")
import build_us_fiscal_refresh_release as release  # noqa: E402
from populace.build.us_runtime.warm_start_selection import (  # noqa: E402
    DEFAULT_SELECTION_JOIN_KEY,
    _base_household_key_frame,
    load_selection_source_from_manifest,
)

RT_H = Path("/Users/maxghenis/PolicyEngine/_buildh-runtime")
RT_I = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime")
CKPT = RT_H / "checkpoints/buildh-dense/target_frame_checkpoint.h5"
DIAG = (RT_H / "out/buildh-run/dense/releases/"
        "populace-us-2024-buildh-dense-warmstart-b449eb7-20260708T100442Z/"
        "calibration_diagnostics.json")
BASE = Path("/Users/maxghenis/PolicyEngine/_worktrees/populace-build-f/out/"
            "base-f-20260705/base_populace_us_2024_puf_support.h5")
MASK = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/forensics/frozen_support_mask.npy")
MANIFEST = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/inputs/"
                "certified_57k_selection_source.json")
OUT = RT_I / "out/core"
OUT.mkdir(parents=True, exist_ok=True)

REG_EXPECTED = "d71c59514e3a"
N_EXPECTED = 337704
K_EXPECTED = 57240

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
    final_est = np.array([float(t.get("final_estimate", 0.0)) for t in targets], dtype=np.float64)
    log(f"targets: {len(targets)}  (b<=0: {int((b<=0).sum())})  diag final_loss={diag['final_loss']}")
    assert len(targets) == 5533, len(targets)

    # ---- A from checkpoint target-measure columns ----
    with h5py.File(CKPT, "r") as f:
        ij = json.loads(f.attrs["identity_json"])
        assert ij["target_registry_version"] == REG_EXPECTED, ij["target_registry_version"]
        hh = f["tables/household"]
        cols = json.loads(hh.attrs["columns_json"])
        name2idx = {c: i for i, c in enumerate(cols)}
        colgrp = hh["columns"]

        def read_col(name):
            return np.asarray(colgrp[f"{name2idx[name]:05d}/values"], dtype=np.float64)

        ck_household_id = np.asarray(colgrp[f"{name2idx['household_id']:05d}/values"]).astype(np.int64)
        state_fips = np.asarray(colgrp[f"{name2idx['state_fips']:05d}/values"]).astype(np.int64)
        n = ck_household_id.size
        assert n == N_EXPECTED and np.all(np.diff(ck_household_id) > 0), "ckpt hid not ascending"
        wgrp = f["weights/household"]
        base_weight = np.asarray(wgrp["values"], dtype=np.float64)
        log(f"ckpt registry={ij['target_registry_version']} n={n} "
            f"base_weight sum={base_weight.sum():.6g} min={base_weight.min():.4g} max={base_weight.max():.4g}")

        rows, colsi, data = [], [], []
        for t, meas in enumerate(tgt_measures):
            v = read_col(meas)
            nz = np.nonzero(v)[0]
            rows.append(np.full(nz.size, t, dtype=np.int32))
            colsi.append(nz.astype(np.int32))
            data.append(v[nz])
        rows = np.concatenate(rows); colsi = np.concatenate(colsi); data = np.concatenate(data)
        A = sparse.coo_array((data, (rows, colsi)), shape=(len(targets), n)).tocsr()
        log(f"A: shape={A.shape} nnz={A.nnz}")
        age = np.stack([read_col(AGE_COL.format(bnd)) for bnd in AGE_BANDS], axis=1)
        hh_size = age.sum(axis=1)
        agi = read_col(AGI_COL)

    # ---- base frame via the release tool's own loader (canonical order) ----
    log("loading base frame via release._load_frame ...")
    base_frame = release._load_frame(BASE)
    household = base_frame.table("household")
    person = base_frame.table("person")
    tax_unit = base_frame.table("tax_unit")
    bf_hid = household["household_id"].to_numpy().astype(np.int64)
    assert bf_hid.size == n, (bf_hid.size, n)
    assert np.array_equal(bf_hid, ck_household_id), "base frame household order != checkpoint order"
    log(f"base frame household order == checkpoint order: True (n={n})")
    raw_base_weight = household["household_weight"].to_numpy().astype(np.float64) \
        if "household_weight" in household.columns else base_weight

    # ---- canonical identities per household (for Step 5 manifest construction) ----
    base_key = _base_household_key_frame(base_frame, DEFAULT_SELECTION_JOIN_KEY)
    assert list(base_key.columns) == list(DEFAULT_SELECTION_JOIN_KEY), list(base_key.columns)
    assert not base_key.duplicated().any(), "base pool identities not unique under join key"
    base_identities = base_key.to_numpy()  # (n,4) object: [source_year,source_household_id,channel,clone]
    source_year = base_key["source_year"].to_numpy().astype(np.int64)
    channel = base_key["household_support_channel"].to_numpy().astype(str)
    log(f"base identities unique: True; source_year dist={dict(zip(*np.unique(source_year, return_counts=True)))}")

    # ---- export-mass INPUT columns, per household (base-frame order) ----
    hid_to_pos = {int(h): i for i, h in enumerate(bf_hid)}
    p_pos = np.array([hid_to_pos[int(h)] for h in person["person_household_id"].to_numpy()], dtype=np.int64)
    export_effval = {}
    for col in ["miscellaneous_income", "home_mortgage_interest", "estate_income",
                "non_sch_d_capital_gains"]:
        vals = person[col].to_numpy().astype(np.float64)
        eff = np.zeros(n, dtype=np.float64); np.add.at(eff, p_pos, vals)
        export_effval[col] = eff
        log(f"export {col}: nonzero_hh={int((eff!=0).sum())} base_mass={float((raw_base_weight*eff).sum()):.6g}")
    # first_home_mortgage_interest (tax_unit) -> household via first person's household
    p_tu = person["person_tax_unit_id"].to_numpy().astype(np.int64)
    tu_pos = {}
    for tuid, pos in zip(p_tu, p_pos):
        tu_pos.setdefault(int(tuid), pos)
    eff = np.zeros(n, dtype=np.float64)
    for tuid, val in zip(tax_unit["tax_unit_id"].to_numpy().astype(np.int64),
                         tax_unit["first_home_mortgage_interest"].to_numpy().astype(np.float64)):
        pos = tu_pos.get(int(tuid))
        if pos is not None:
            eff[pos] += val
    export_effval["first_home_mortgage_interest"] = eff
    log(f"export first_home_mortgage_interest: nonzero_hh={int((eff!=0).sum())} base_mass={float((raw_base_weight*eff).sum()):.6g}")

    # ---- CANONICAL frozen selection via the manifest's own join ----
    src = load_selection_source_from_manifest(MANIFEST)
    assert src.n_identities == K_EXPECTED, src.n_identities
    mask, report = src.base_selection_mask(base_frame, mode="frozen_support")
    frozen_pos = np.nonzero(mask)[0].astype(np.int64)
    log(f"manifest join: n_selected={report.n_selected} n_unmapped={report.n_unmapped} "
        f"n_ambiguous={report.n_ambiguous} -> frozen_pos={frozen_pos.size}")
    assert frozen_pos.size == K_EXPECTED and report.n_unmapped == 0

    # cross-check vs build-g forensic mask
    y = np.load(MASK).astype(np.int8)
    fm_pos = np.nonzero(y == 1)[0].astype(np.int64)
    xcheck = np.array_equal(frozen_pos, fm_pos)
    log(f"cross-check frozen manifest-join == build-g forensic mask: {xcheck} "
        f"(overlap={np.intersect1d(frozen_pos, fm_pos).size})")

    # ---- base-weight A/b sanity ----
    est_base = A @ base_weight
    ok = b != 0
    within10_base = float((np.abs(est_base[ok] - b[ok]) / np.abs(b[ok]) <= 0.10).mean())
    log(f"A/b base-weight within-10% = {within10_base:.4f}")

    # ---- save ----
    sparse.save_npz(OUT / "A_value_matrix.npz", A)
    np.save(OUT / "b_target_vector.npy", b)
    np.save(OUT / "final_estimate.npy", final_est)
    json.dump(tgt_names, open(OUT / "target_names.json", "w"))
    json.dump(tgt_measures, open(OUT / "target_measures.json", "w"))
    np.save(OUT / "base_identities.npy", base_identities, allow_pickle=True)
    np.savez(OUT / "core_meta.npz",
             household_id=ck_household_id, state_fips=state_fips, source_year=source_year,
             channel=channel, base_weight=base_weight, raw_base_weight=raw_base_weight,
             frozen_pos=frozen_pos, forensic_mask_matches=xcheck, hh_size=hh_size, agi=agi)
    np.savez(OUT / "export_effval.npz", **export_effval)
    log(f"saved core to {OUT}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
