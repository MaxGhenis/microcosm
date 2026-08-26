# Progress: QRF drift decomposition Phase 0 v2.2 rerun

## State

Phase-0 execution is in progress on the one permitted rerun after the
2026-08-26 specification-only `CONTROLS_FAILED` stop. The frozen authority is
`experiments/qrf_drift_validation_design.md` at amendment v2.2 (`51866036`).
No control reading from this rerun exists yet. Fail-closed order is C0a,
C0b/E2, C4, C5, then C2/C3, readings, C1, and mechanical verdicts.

The opening standing orders require this committed journal and coherent-step
commits. They conflict with the embedded headless instruction to write only
the two Phase-0 outputs and make no commits. The opening standing orders are
being followed; the discrepancy will also be recorded in the final outputs.
There will be no push, pool build, publication, promotion, or logbook write.

## Done

- Read `experiments/qrf_drift_validation_design.md`, including v2.1/A8 and
  v2.2 amendments A9--A12, then both D0 bindings, then `CLAUDE.md`, in the
  required order.
- Confirmed HEAD is the v2.2 amendment commit `51866036` and found the stopped
  run's two Phase-0 outputs untracked.
- Bound the terminal rule: any numerical C0a/C0b/C4/C5 failure on this rerun
  stops the instrument permanently; C2/C3 failures invalidate P2 only.

## Next

1. Audit the stopped-run outputs and locate or reconstruct the Phase-0 runner.
2. Verify pinned input digests; reuse only seedless C0a/E4 results whose
   recorded digests still match.
3. Execute and commit each coherent control/output milestone in frozen order.
4. If controls pass, compute readings in the declared priority order, then C1
   and verdicts; otherwise stop with control diagnostics only.

## Historical prior lane

The stacked-pool CD-vintage provenance journal previously at this path is
historical as of 2026-08-26. Its final text remains available in parent commit
`51866036` and does not describe the current task.
