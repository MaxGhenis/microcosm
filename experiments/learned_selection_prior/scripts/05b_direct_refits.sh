#!/bin/bash
# populace#346 — STEP 05b: fourth-arm DIRECT refits (learned + frozen control).
#
# Runs src/direct_replay_learned_refit.py for each selection SERIALLY (one
# CPU-heavy process at a time — courtesy to the sibling build-h3 release run).
# This is the DIRECT checkpoint-load path (cache HIT, no ACA re-prep, no export,
# no gates), NOT a full release run. Each solve ~20 min.
#
#   learned_hgb : fourth arm — top-57,240 by OOF HGB probability
#   frozen      : matched control — the certified 57,240 on the SAME dense
#                 registry (isolates selection quality; both see all 5,521 targets)
#
# STAGING/LOCAL ONLY. Detached (nohup + pidfile from the caller). Real exit codes.
set -u
WT=/Users/maxghenis/PolicyEngine/_worktrees/populace-build-g-run
SELD=/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/selections
LOGD=/Users/maxghenis/PolicyEngine/_buildg-runtime/logs/learned-prior
SCRIPT=$WT/experiments/learned_selection_prior/src/direct_replay_learned_refit.py
cd "$WT" || exit 3

for TAG in learned_hgb frozen; do
  LOG="$LOGD/refit_direct_${TAG}.log"
  echo "[$(date -u +%FT%TZ)] START direct refit tag=$TAG" | tee "$LOG"
  .venv/bin/python "$SCRIPT" --selection "$SELD/sel_${TAG}.npy" --tag "$TAG" >> "$LOG" 2>&1
  rc=$?
  echo "$rc" > "$LOGD/refit_direct_${TAG}_rc.txt"
  echo "[$(date -u +%FT%TZ)] DONE tag=$TAG rc=$rc" | tee -a "$LOG"
  if [ "$rc" -ne 0 ]; then
    echo "[$(date -u +%FT%TZ)] ABORT chain: $TAG failed rc=$rc" | tee -a "$LOG"
    echo "ABORTED_AT=$TAG rc=$rc" > "$LOGD/refit_direct_chain.marker"
    exit "$rc"
  fi
done
echo "ALL_DONE" > "$LOGD/refit_direct_chain.marker"
echo "[$(date -u +%FT%TZ)] chain complete (learned_hgb + frozen)"
