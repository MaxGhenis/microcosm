"""populace#346 — STEP 05 (direct path): fourth-arm refit on a restricted selection.

Loads the Build G DENSE target-frame checkpoint (cache HIT — no ACA re-prep, no
base re-materialization), restricts it to a positional 57,240-record selection,
applies the base-population mass repair (334.2M persons, exactly as the release
tool's certified sequence), recompiles the target registry against the reduced
frame, and solves with the EXACT dense solver config (adam, 1500 epochs, lr 0.02,
max_weight_ratio 5.0, mass=conserve, l2=0, seed 0).

This is deliberately NOT a full release run: no export H5, no mass/immigration
gates, no ACA microsim. It reuses the release tool's own
``_select_households_by_position`` + ``_with_base_population_mass_repair`` +
``_compile_materialized_target_registry`` helpers so the restriction, the scale,
and the target surface match the certified sparse path (populace#328) exactly —
the only thing that differs from the frozen-sparse arm is *which* 57,240 records
are chosen and that no selection-specific zero-support exclusions are applied
(a history-free comparison; see #346).

Reports final_loss / initial_loss / within-10% / ESS + the two critical-target
aggregates (federal income tax vs SOI, Social Security vs SSA), all computed the
same way the release diagnostics compute them:
    pct = (sum_i w_i * v_it - b_t) / b_t   for the US income-tax / SSA target rows.

Usage:
  direct_replay_learned_refit.py --selection SEL.npy --tag learned_hgb [--dry-run]
    SEL.npy : int positions (0..337703) of the selected records, OR a length-337704
              bool mask. Positions index the checkpoint frame in household_id order
              (extract_core verified checkpoint rows are household_id-sorted 0..n-1).
  --dry-run : load + restrict + repair + recompile + a 2-epoch calibrate smoke test,
              then stop (de-risk the pipeline before the ~20-min solve).
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, "tools")
import build_us_fiscal_refresh_release as R  # noqa: E402
from populace.calibrate import calibrate  # noqa: E402

RT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime")
CKPT = RT / "checkpoints/buildg-dense/target_frame_checkpoint.h5"
FACTS = Path("/Users/maxghenis/PolicyEngine/_buildf-runtime/inputs/consumer_facts_buildf_v7.jsonl")
FACTS_SHA = "735f326a73c3d911a0db288708cadfcb5aa6bfe3740e0a13cf1bc34ed955d9c1"
BASE_SHA = "18833fb68e60ee74461608d81a5c5ab7d52435e17026d9e3b062d9de18d6871f"
PEUS = "1.764.6"
REG_VERSION_EXPECTED = "e035007bba5b"
CORE = RT / "out/learned-prior/core"
OUT = RT / "out/learned-prior/refit-direct"
OUT.mkdir(parents=True, exist_ok=True)

K = 57240
# critical-target names (US-total; identical target value across all arms)
IT_TARGET = "irs_soi.ty2022.historic_table_2.us.all.income_tax_liability_amount@2024"
SS_TARGET = "ssa_supplement.cy2024.oasdi_ssi_payments.social_security_benefits.payment_amount@2024"


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def load_selection(path: Path, n: int) -> np.ndarray:
    arr = np.load(path)
    if arr.dtype == bool or (arr.size == n and set(np.unique(arr)).issubset({0, 1})):
        pos = np.nonzero(arr.astype(bool))[0]
    else:
        pos = np.asarray(arr, dtype=np.int64)
    pos = np.unique(pos)
    assert pos.min() >= 0 and pos.max() < n, (pos.min(), pos.max(), n)
    return pos


def critical_aggregates(sel_positions: np.ndarray, w_solved: np.ndarray) -> dict:
    """Income-tax(SOI) and SS(SSA) pct error from the SAME core A the diagnostics use.

    est_t = sum_i w_i * v_it over the selected records; pct = (est - b_t)/b_t.
    """
    from scipy import sparse
    A = sparse.load_npz(CORE / "A_value_matrix.npz").tocsr()
    b = np.load(CORE / "b_target_vector.npy")
    names = json.load(open(CORE / "target_names.json"))
    name2row = {nm: i for i, nm in enumerate(names)}
    Asub = A[:, sel_positions]  # (n_targets, K) aligned to sel order == w_solved order
    est = Asub @ w_solved
    out = {}
    for label, nm in (("income_tax_soi", IT_TARGET), ("social_security_ssa", SS_TARGET)):
        t = name2row[nm]
        bt = float(b[t]); et = float(est[t])
        out[label] = {"target": bt, "estimate": et,
                      "pct": (et - bt) / bt * 100.0 if bt else float("nan")}
    # global within-10% over the DENSE registry b (nonzero targets), for context
    ok = b != 0
    est_all = est
    within10 = float((np.abs(est_all[ok] - b[ok]) / np.abs(b[ok]) <= 0.10).mean())
    out["within_10pct_dense_registry_b"] = within10
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    t0 = time.time()

    log("loading feed + compiling target registry (no microsim) ...")
    ledger = R.load_ledger_consumer_artifact(FACTS, expected_facts_sha256=FACTS_SHA)
    registry0 = R.compile_us_fiscal_target_registry(
        ledger.facts, target_period=R.PERIOD,
        include_congressional_district_targets=False,
        congressional_district_vintage_crosswalk=None,
        age_targets=True, allow_unaged_dollar_targets=False,
        extra_support_exclusions=None)
    target_specs = registry0.specs
    log(f"registry version = {registry0.version} (expected {REG_VERSION_EXPECTED}) "
        f"n_specs={len(target_specs)}")

    identity = R._target_frame_checkpoint_identity(
        base_dataset_sha256=BASE_SHA, policyengine_us_version=PEUS, seed=0,
        target_period=R.PERIOD, target_registry_version=registry0.version,
        congressional_district_vintage_crosswalk_sha256=None)
    loaded = R._read_target_frame_checkpoint(
        CKPT, identity=identity, target_specs=target_specs,
        gate_congressional_district_targets=False)
    if loaded is None:
        log("CHECKPOINT MISS — identity mismatch; cannot fast-load. STOP + report.")
        sys.exit(4)
    frame, registry_full, _comp = loaded
    n = int(frame.n("household"))
    log(f"checkpoint HIT: frame n(household)={n} n(person)={int(frame.n('person'))} "
        f"n_targets_full={len(registry_full)}")

    sel = load_selection(Path(args.selection), n)
    assert sel.size == K, f"selection has {sel.size} records, expected {K}"
    hid = frame.table("household")["household_id"].to_numpy()
    # extract_core verified the checkpoint rows are in base-household_id-SORTED
    # order (positional match to the label/feature arrays at frac 1.0); the ids
    # themselves are not 0..n-1. The invariant we rely on is strictly ascending
    # ids, so positional indices into the label/features address the same rows.
    assert np.all(np.diff(hid) > 0), "checkpoint household_id not strictly ascending"
    log(f"selection: {sel.size} positions; min={sel.min()} max={sel.max()} "
        f"(checkpoint hid range {hid.min()}..{hid.max()})")

    # ---- restrict to the selection (release tool's own helper) ----
    reduced = R._select_households_by_position(frame, sel)
    rh = reduced.table("household")["household_id"].to_numpy()
    assert np.array_equal(rh, hid[sel]), "reduced household order != selection order"
    pop0 = R._person_population(reduced)
    log(f"reduced: n(household)={int(reduced.n('household'))} "
        f"n(person)={int(reduced.n('person'))} person_pop(before repair)={pop0:,.0f}")

    # ---- base-population mass repair to 334.2M (certified sequence, line 5190) ----
    reduced, repair = R._with_base_population_mass_repair(reduced)
    log(f"mass repair: applied={repair['applied']} factor={repair['factor']:.6f} "
        f"repaired_pop={repair['repaired_population']:,.0f} "
        f"benchmark={repair['benchmark']:,.0f}")

    # ---- recompile the target registry against the REDUCED frame (release-faithful) ----
    registry, _rc = R._compile_materialized_target_registry(
        reduced, target_specs, gate_congressional_district_targets=False)
    log(f"recompiled registry against reduced frame: n_targets={len(registry)} "
        f"(full={len(registry_full)})")
    tlw = R._fiscal_target_loss_weights(registry)

    epochs = 2 if args.dry_run else 1500
    log(f"calibrating (adam, {epochs} epochs, lr 0.02, ratio 5.0, mass=conserve, "
        f"l2=0, seed 0){' — DRY RUN smoke test' if args.dry_run else ' — ~20 min'} ...")
    result = calibrate(
        reduced, registry.to_target_set(), epochs=epochs, learning_rate=0.02,
        max_weight_ratio=5.0, seed=0, mass="conserve", l2_lambda=0.0,
        target_loss_weights=tlw, target_loss_cap=R.US_FISCAL_TARGET_LOSS_CAP,
        warm_start_weights=None)
    w = np.asarray(result.weights, dtype=np.float64)
    ess = (w.sum() ** 2) / (w ** 2).sum()
    log(f"final_loss={result.final_loss:.10f} initial_loss={result.initial_loss:.6f} "
        f"ESS={ess:.2f} n_nonzero={int((w>0).sum())} n_records={w.size}")

    agg = critical_aggregates(sel, w)
    log(f"income_tax(SOI): target={agg['income_tax_soi']['target']:.4g} "
        f"est={agg['income_tax_soi']['estimate']:.4g} "
        f"pct={agg['income_tax_soi']['pct']:+.2f}%")
    log(f"social_security(SSA): target={agg['social_security_ssa']['target']:.4g} "
        f"est={agg['social_security_ssa']['estimate']:.4g} "
        f"pct={agg['social_security_ssa']['pct']:+.2f}%")
    log(f"within_10pct (dense-registry b, {len(target_specs)} targets ref) = "
        f"{agg['within_10pct_dense_registry_b']:.4f}")

    if args.dry_run:
        log("DRY RUN OK — restriction + repair + recompile + calibrate all run. Stopping.")
        return

    summary = {
        "tag": args.tag, "selection": str(args.selection),
        "n_records": int(w.size), "n_targets": int(len(registry)),
        "final_loss": float(result.final_loss),
        "initial_loss": float(result.initial_loss),
        "ess": float(ess), "n_nonzero": int((w > 0).sum()),
        "mass_repair_factor": float(repair["factor"]),
        "repaired_population": float(repair["repaired_population"]),
        "aggregates": agg,
        "solver": {"epochs": 1500, "lr": 0.02, "max_weight_ratio": 5.0,
                   "mass": "conserve", "l2_lambda": 0.0, "seed": 0},
        "elapsed_s": time.time() - t0,
    }
    np.save(OUT / f"weights_{args.tag}.npy", w)
    json.dump(summary, open(OUT / f"summary_{args.tag}.json", "w"), indent=2)
    log(f"saved weights + summary to {OUT} (tag={args.tag})  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
