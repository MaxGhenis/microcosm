"""populace#346 — STEP 01b (fast path): recover dense weights WITHOUT ACA re-prep.

The release-tool path re-materializes the base frame (ACA microsim, ~25+ min)
before it ever reaches the cached target-frame checkpoint. But the checkpoint h5
already stores the fully materialized frame — loading it directly via the tool's
own `_read_target_frame_checkpoint` skips ACA entirely. We then replay the EXACT
dense `calibrate(...)` call (options read from the dense diagnostics) and verify
`final_loss == 0.0413937` (ESS 81206.15). Deterministic recovery, not synthesis.

--verify-only: compile registry + load frame from checkpoint (seconds), print the
registry version + initial fit, and stop (de-risk the identity match before the
~19-min solve).
"""
from __future__ import annotations
import argparse, sys, time
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
OUT = RT / "out/learned-prior/densewts_direct"
OUT.mkdir(parents=True, exist_ok=True)

# recorded dense-arm invariants (verification anchors)
FINAL_LOSS = 0.041393692879099726
INIT_LOSS = 0.20630604028701782
ESS = 81206.15366419907
TOP1 = 0.10600402099296712


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-only", action="store_true")
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
    log(f"registry version = {registry0.version}  (expected {REG_VERSION_EXPECTED})  "
        f"n_specs={len(target_specs)}")

    identity = R._target_frame_checkpoint_identity(
        base_dataset_sha256=BASE_SHA, policyengine_us_version=PEUS, seed=0,
        target_period=R.PERIOD, target_registry_version=registry0.version,
        congressional_district_vintage_crosswalk_sha256=None)
    log(f"checkpoint identity: {identity}")

    loaded = R._read_target_frame_checkpoint(
        CKPT, identity=identity, target_specs=target_specs,
        gate_congressional_district_targets=False)
    if loaded is None:
        log("CHECKPOINT MISS — identity mismatch; cannot fast-load. Report + fall back.")
        sys.exit(4)
    frame, registry, _comp = loaded
    log(f"checkpoint HIT: frame n(household)={frame.n('household')} n_targets={len(registry)}")

    tlw = R._fiscal_target_loss_weights(registry)
    if args.verify_only:
        log("verify-only: frame + registry loaded from checkpoint OK. "
            "Ready for the solve; stopping.")
        return

    log("calibrating (adam, 1500 epochs, lr 0.02, mass=conserve, ratio 5.0, "
        "l2=0, seed 0) — ~19 min ...")
    result = calibrate(
        frame, registry.to_target_set(), epochs=1500, learning_rate=0.02,
        max_weight_ratio=5.0, seed=0, mass="conserve", l2_lambda=0.0,
        target_loss_weights=tlw, target_loss_cap=R.US_FISCAL_TARGET_LOSS_CAP,
        warm_start_weights=None)
    w = np.asarray(result.weights, dtype=np.float64)
    log(f"DONE. final_loss={result.final_loss:.10f} (recorded {FINAL_LOSS}) "
        f"initial_loss={result.initial_loss:.6f} (recorded {INIT_LOSS})")
    ess = (w.sum() ** 2) / (w ** 2).sum()
    log(f"ESS={ess:.2f} (recorded {ESS:.2f})  n_nonzero={(w>0).sum()}")
    ok = abs(result.final_loss - FINAL_LOSS) < 1e-5
    log(f"VERIFICATION {'PASS' if ok else 'FAIL'} (final_loss match to 1e-5)")
    np.save(OUT / "dense_household_weight.npy", w)
    np.save(OUT / "dense_initial_weight.npy", np.asarray(result.initial_weights, float))
    log(f"saved dense weights to {OUT}/dense_household_weight.npy  ({time.time()-t0:.1f}s)")
    if not ok:
        sys.exit(5)


if __name__ == "__main__":
    main()
