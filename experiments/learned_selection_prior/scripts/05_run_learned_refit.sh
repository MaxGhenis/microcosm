#!/bin/bash
# populace#346 — STEP 05: frozen-support refit on the LEARNED selection (fourth arm).
# Mirrors the Build G SPARSE command (frozen-support manifest + dense polish,
# lambda=0, ratio 5.0, #327 export-mass reference + sparse zero-support exclusions),
# but with the LEARNED manifest instead of the certified 57k manifest. Produces the
# critical-fit table for the #299 fourth-arm row.
#
# Reuses the buildg-sparse target-frame checkpoint (same feed + same sparse
# exclusions => registry a9897709 => cache HIT, no re-materialization). Copies the
# checkpoint h5 into a fresh root so the original buildg-sparse artifacts are untouched.
# STAGING/LOCAL ONLY. DETACHED (nohup + pidfile). arg1 = manifest path, arg2 = tag.
set -u
MANIFEST="${1:?manifest path required}"
TAG="${2:?tag required}"
RT=/Users/maxghenis/PolicyEngine/_buildg-runtime
WT=/Users/maxghenis/PolicyEngine/_worktrees/populace-build-g-run
BASE=/Users/maxghenis/PolicyEngine/_worktrees/populace-build-f/out/base-f-20260705/base_populace_us_2024_puf_support.h5
REF=$RT/forensics/populace_us_2024.h5
SPARSE_EXCL=$RT/inputs/sparse_zero_support_exclusions_buildg.json
FACTS=/Users/maxghenis/PolicyEngine/_buildf-runtime/inputs/consumer_facts_buildf_v7.jsonl
OUT=$RT/out/learned-prior/refit-$TAG
CKROOT=$RT/checkpoints/learned-$TAG
LOGD=$RT/logs/learned-prior
mkdir -p "$OUT" "$CKROOT" "$LOGD"
LOG="$LOGD/refit_$TAG.log"

cd "$WT" || exit 3
source .venv/bin/activate 2>/dev/null
FACTS_SHA=$(shasum -a 256 "$FACTS" | cut -d' ' -f1)
SHORT=$(git rev-parse --short HEAD)

# seed the target-frame checkpoint from buildg-sparse (registry a9897709) for a HIT
if [ ! -f "$CKROOT/target_frame_checkpoint.h5" ]; then
  cp "$RT/checkpoints/buildg-sparse/target_frame_checkpoint.h5" "$CKROOT/" 2>/dev/null \
    && echo "[$(date -u +%FT%TZ)] seeded target-frame checkpoint (expect cache HIT)" | tee "$LOG"
fi

RID="populace-us-2024-buildg-learned-$TAG-$SHORT-$(date -u +%Y%m%dT%H%M%SZ)"
echo "[$(date -u +%FT%TZ)] LEARNED REFIT start tag=$TAG id=$RID manifest=$MANIFEST" | tee -a "$LOG"

python tools/build_us_fiscal_refresh_release.py \
  --base-h5 "$BASE" \
  --selection-source-manifest "$MANIFEST" \
  --dense-default-dataset \
  --ledger-facts "$FACTS" \
  --ledger-facts-sha "$FACTS_SHA" \
  --export-input-mass-reference-h5 "$REF" \
  --zero-support-exclusions "$SPARSE_EXCL" \
  --out "$OUT" \
  --release-id "$RID" \
  --checkpoint-root "$CKROOT" \
  --seed 0 \
  --allow-input-mass-drift \
  --no-staging \
  >> "$LOG" 2>&1
rc=$?
echo "[$(date -u +%FT%TZ)] LEARNED REFIT exited rc=$rc id=$RID" | tee -a "$LOG"
echo "$rc" > "$LOGD/refit_${TAG}_rc.txt"
find "$OUT" -name calibration_diagnostics.json | tee -a "$LOG"
echo "DONE" > "$LOGD/refit_${TAG}.marker"
