#!/bin/bash
# populace#346 learned-selection-prior experiment — STEP 01
# Recover the Build G DENSE per-household calibrated weight vector (337,704).
#
# WHY: the Build G dense arm (#299) raised RuntimeError at the export-mass gate
# (4 unidentified PUF columns) BEFORE writing the export H5, so the calibrated
# household_weight was never persisted. The expensive target materialization IS
# cached in checkpoints/buildg-dense/target_frame_checkpoint.h5, and all solver
# options are recorded in the dense calibration_diagnostics.json (adam, 1500 ep,
# lr 0.02, mass=conserve, ratio 5.0, l0=0, l2=0, seed 0). Re-running the exact
# dense command with --allow-input-mass-drift (bypasses ONLY the export gate;
# checkpoint identity is independent of that flag → cache hit, no re-materialize)
# deterministically reproduces the weights and lets the export H5 write.
#
# VERIFY: the reproduced final_loss must equal 0.0413937 (ESS 81206.15,
# top_1pct 0.10600402, realized_max_ratio 5.0). If it matches, the weights are
# provably identical to the #299 dense arm. This is RECOVERY, not synthesis.
#
# STAGING/LOCAL ONLY. Never touch prod HF / latest.json. Detached.
set -u
RT=/Users/maxghenis/PolicyEngine/_buildg-runtime
WT=/Users/maxghenis/PolicyEngine/_worktrees/populace-build-g-run
EXP=$WT/experiments/learned_selection_prior
BASE=/Users/maxghenis/PolicyEngine/_worktrees/populace-build-f/out/base-f-20260705/base_populace_us_2024_puf_support.h5
REF=$RT/forensics/populace_us_2024.h5
FACTS=/Users/maxghenis/PolicyEngine/_buildf-runtime/inputs/consumer_facts_buildf_v7.jsonl
OUT=$RT/out/learned-prior/densewts
LOGD=$RT/logs/learned-prior
mkdir -p "$OUT" "$LOGD"
LOG="$LOGD/recompute_dense_weights.log"

cd "$WT" || exit 3
source .venv/bin/activate 2>/dev/null

BASE_SHA=$(shasum -a 256 "$BASE" | cut -d' ' -f1)
FACTS_SHA=$(shasum -a 256 "$FACTS" | cut -d' ' -f1)
SHORT=$(git rev-parse --short HEAD)
echo "[$(date -u +%FT%TZ)] RECOMPUTE DENSE WEIGHTS start commit=$SHORT base=$BASE_SHA" | tee "$LOG"
if [ "$BASE_SHA" != "18833fb68e60ee74461608d81a5c5ab7d52435e17026d9e3b062d9de18d6871f" ]; then
  echo "FATAL base sha mismatch" | tee -a "$LOG"; exit 2
fi

RID="populace-us-2024-buildg-dense-weightsrecover-$(date -u +%Y%m%dT%H%M%SZ)"
echo "[$(date -u +%FT%TZ)] release-id=$RID  (SAME checkpoint root -> target-frame cache HIT)" | tee -a "$LOG"

python tools/build_us_fiscal_refresh_release.py \
  --base-h5 "$BASE" \
  --ledger-facts "$FACTS" \
  --ledger-facts-sha "$FACTS_SHA" \
  --export-input-mass-reference-h5 "$REF" \
  --out "$OUT" \
  --release-id "$RID" \
  --checkpoint-root "$RT/checkpoints/buildg-dense" \
  --seed 0 \
  --dense-default-dataset \
  --allow-input-mass-drift \
  --no-staging \
  >> "$LOG" 2>&1
rc=$?
echo "[$(date -u +%FT%TZ)] release exited rc=$rc id=$RID" | tee -a "$LOG"
echo "$rc" > "$LOGD/recompute_dense_weights_rc.txt"
echo "$RID" > "$LOGD/recompute_dense_weights_release_id.txt"
# locate the exported dataset (dense H5 with household_weight)
find "$OUT" -name "*.h5" | tee -a "$LOG"
echo "DONE" > "$LOGD/recompute_dense_weights.marker"
