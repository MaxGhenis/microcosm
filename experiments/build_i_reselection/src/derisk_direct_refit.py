"""populace#359 Build I — STEP 4: de-risk a candidate selection via the direct path.

Loads the Build H DENSE target-frame checkpoint ONCE (registry d71c59514e3a HIT),
then for each named selection: restrict -> base-population mass repair (334.2M) ->
recompile registry against the reduced frame -> calibrate (dense config: adam 1500
ep, lr 0.02, ratio 5.0, mass=conserve, l2=0, seed 0) -> report. Reuses the release
tool's own helpers so restriction/scale/target surface match the certified sparse
path exactly (populace#328). NOT a release run (no export H5, no full gates).

Reports per selection: final_loss / within-10% / ESS, income tax (SOI) / SS (SSA)
pct, the 5 export-mass gate columns' export mass = Σ_hh w_solved * effval_hh
(person_weight == household_weight by broadcast; validated against frozen $9.55B),
and the zero-support cells (target>0, |initial_est|<=1e-9, |final_est|<=1e-9).

Run FROZEN first as the matched control (misc export must reproduce $9.54992e9).

Usage: derisk_direct_refit.py --selections frozen sel_buildi_N1500.npy [...]
STAGING/LOCAL ONLY. Every number written to out/derisk/.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, "tools")
import build_us_fiscal_refresh_release as release  # noqa: E402
from populace.calibrate import calibrate  # noqa: E402

RT_H = Path("/Users/maxghenis/PolicyEngine/_buildh-runtime")
RT_I = Path("/Users/maxghenis/PolicyEngine/_buildi-runtime")
CKPT = RT_H / "checkpoints/buildh-dense/target_frame_checkpoint.h5"
FACTS = RT_H / "inputs/consumer_facts_buildh_v8.jsonl"
FACTS_SHA = "94b7155f7ca9e2de32ddb3a0add2fff2d8c66e73147fe5bd112cff3ba69b1669"
BASE_SHA = "18833fb68e60ee74461608d81a5c5ab7d52435e17026d9e3b062d9de18d6871f"
PEUS = "1.764.6"
REG_EXPECTED = "d71c59514e3a"
CORE = RT_I / "out/core"
SELDIR = RT_I / "out/selections"
OUT = RT_I / "out/derisk"
OUT.mkdir(parents=True, exist_ok=True)
K = 57240

IT_TARGET = "irs_soi.ty2022.historic_table_2.us.all.income_tax_liability_amount@2024"
SS_TARGET = "ssa_supplement.cy2024.oasdi_ssi_payments.social_security_benefits.payment_amount@2024"
GATE_COLS = ["miscellaneous_income", "home_mortgage_interest",
             "first_home_mortgage_interest", "estate_income", "non_sch_d_capital_gains"]
# export-mass reference masses (Build H input_mass_parity; ±50% band, $1B floor)
REF_MASS = {"miscellaneous_income": 4.74006e10}  # others computed in the release; misc is the gate-critical one


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def load_sel(name, n):
    if name == "frozen":
        return np.load(CORE / "core_meta.npz", allow_pickle=True)["frozen_pos"].astype(np.int64)
    p = SELDIR / name if (SELDIR / name).exists() else Path(name)
    arr = np.load(p)
    return np.sort(np.asarray(arr, dtype=np.int64))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selections", nargs="+", required=True)
    args = ap.parse_args()
    t0 = time.time()

    # export effvals + A/b for aggregates
    eff = np.load(CORE / "export_effval.npz")
    from scipy import sparse
    A = sparse.load_npz(CORE / "A_value_matrix.npz").tocsr()
    b = np.load(CORE / "b_target_vector.npy")
    names = json.load(open(CORE / "target_names.json"))
    name2row = {nm: i for i, nm in enumerate(names)}

    log("compiling registry (v8, no microsim) ...")
    ledger = release.load_ledger_consumer_artifact(FACTS, expected_facts_sha256=FACTS_SHA)
    registry0 = release.compile_us_fiscal_target_registry(
        ledger.facts, target_period=release.PERIOD,
        include_congressional_district_targets=False,
        congressional_district_vintage_crosswalk=None,
        age_targets=True, allow_unaged_dollar_targets=False,
        extra_support_exclusions=None)
    target_specs = registry0.specs
    active = release.TargetRegistry(target_specs, country="us")
    log(f"registry version={active.version} n_specs={len(target_specs)}")
    assert active.version == REG_EXPECTED, active.version

    identity = release._target_frame_checkpoint_identity(
        base_dataset_sha256=BASE_SHA, policyengine_us_version=PEUS, seed=0,
        target_period=release.PERIOD, target_registry_version=active.version,
        congressional_district_vintage_crosswalk_sha256=None)
    loaded = release._read_target_frame_checkpoint(
        CKPT, identity=identity, target_specs=target_specs,
        gate_congressional_district_targets=False)
    if loaded is None:
        log("CHECKPOINT MISS — STOP"); sys.exit(4)
    frame, registry_full, _ = loaded
    n = int(frame.n("household"))
    hid = frame.table("household")["household_id"].to_numpy()
    assert np.all(np.diff(hid) > 0)
    log(f"checkpoint HIT: n(household)={n} n(person)={int(frame.n('person'))} full_targets={len(registry_full)}")

    results = {}
    for name in args.selections:
        sel = load_sel(name, n)
        assert sel.size == K, (name, sel.size)
        log(f"===== {name}: {sel.size} records =====")
        reduced = release._select_households_by_position(frame, sel)
        assert np.array_equal(reduced.table("household")["household_id"].to_numpy(), hid[sel])
        reduced, repair = release._with_base_population_mass_repair(reduced)
        registry, _ = release._compile_materialized_target_registry(
            reduced, target_specs, gate_congressional_district_targets=False)
        tlw = release._fiscal_target_loss_weights(registry)
        log(f"  mass repair factor={repair['factor']:.6f} pop={repair['repaired_population']:,.0f}; "
            f"recompiled targets={len(registry)}")
        res = calibrate(reduced, registry.to_target_set(), epochs=1500, learning_rate=0.02,
                        max_weight_ratio=5.0, seed=0, mass="conserve", l2_lambda=0.0,
                        target_loss_weights=tlw, target_loss_cap=release.US_FISCAL_TARGET_LOSS_CAP,
                        warm_start_weights=None)
        w = np.asarray(res.weights, dtype=np.float64)
        ess = (w.sum() ** 2) / (w ** 2).sum()

        # aggregates from core A/b (Asub @ w)
        Asub = A[:, sel]
        est = Asub @ w
        def pct(nm):
            t = name2row[nm]; bt = float(b[t]); return (float(est[t]) - bt) / bt * 100.0 if bt else float("nan")
        ok = b != 0
        within10 = float((np.abs(est[ok] - b[ok]) / np.abs(b[ok]) <= 0.10).mean())

        # export masses (Σ w * effval[sel]); person_weight == household_weight
        exp_mass = {c: float((w * eff[c][sel]).sum()) for c in GATE_COLS}
        misc_ref = REF_MASS["miscellaneous_income"]
        misc_pct = (exp_mass["miscellaneous_income"] - misc_ref) / misc_ref * 100.0
        in_band = 0.5 >= abs(misc_pct) / 100.0

        # zero-support cells (target>0, |init|<=1e-9, |final|<=1e-9) over reduced registry diagnostics
        zs = []
        for d in res.diagnostics:
            if float(getattr(d, "target", 0.0)) > 0.0 \
               and abs(float(getattr(d, "initial_estimate", 0.0))) <= 1e-9 \
               and abs(float(getattr(d, "final_estimate", 0.0))) <= 1e-9:
                zs.append(d.name)

        rec = {
            "n_records": int(w.size), "n_targets": int(len(registry)),
            "final_loss": float(res.final_loss), "initial_loss": float(res.initial_loss),
            "within_10pct": within10, "ess": float(ess),
            "income_tax_soi_pct": pct(IT_TARGET), "social_security_ssa_pct": pct(SS_TARGET),
            "export_mass": exp_mass, "misc_export_pct_vs_ref": misc_pct,
            "misc_in_band": bool(in_band), "misc_ref": misc_ref,
            "n_zero_support": len(zs), "zero_support_names": sorted(zs),
            "mass_repair_factor": float(repair["factor"]),
        }
        results[name] = rec
        log(f"  final_loss={rec['final_loss']:.8f} within10={within10:.4f} ESS={ess:,.0f} "
            f"income_tax={rec['income_tax_soi_pct']:+.2f}% SS={rec['social_security_ssa_pct']:+.2f}%")
        log(f"  MISC export={exp_mass['miscellaneous_income']:.5g} vs ref {misc_ref:.5g} "
            f"= {misc_pct:+.1f}%  IN_BAND={in_band}")
        log(f"  home_mtg={exp_mass['home_mortgage_interest']:.4g} first_home_mtg={exp_mass['first_home_mortgage_interest']:.4g} "
            f"estate={exp_mass['estate_income']:.4g} non_sch_d={exp_mass['non_sch_d_capital_gains']:.4g}")
        log(f"  zero_support cells={len(zs)}")
        np.save(OUT / f"weights_{name.replace('.npy','').replace('sel_','')}.npy", w)

    json.dump(results, open(OUT / "derisk_results.json", "w"), indent=2)
    log(f"saved derisk_results.json to {OUT}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
