# Progress: QRF drift decomposition Phase 0 v2.2 rerun

## State

Phase-0 execution is in progress on the one permitted rerun after the
2026-08-26 specification-only `CONTROLS_FAILED` stop. The frozen authority is
`experiments/qrf_drift_validation_design.md` at amendment v2.2 (`51866036`).
C0a is validly reused and PASSED after every recorded input digest matched.
The deterministic E4 half of C0b is also validly reused (36/36 gates,
12,909,037 sign rows, zero mismatches) after its complete recorded input set
matched. A9's newly seeded E2 half and C4/C5 are running. Fail-closed order is
C0a, C0b/E2, C4, C5, then C2/C3, readings, C1, and mechanical verdicts.

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
- Rehashed both C0a pool/gates pairs, the candidate assembled/transferred
  checkpoints, all nine target banks, and A12's three predecessor banks. Every
  digest matches D0/A12 and the stopped-run evidence, so v2.2 permits reuse of
  seedless C0a and E4. The operative design digest is
  `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`.

## Next

1. Complete A9 C0b/E2, A10 C4, and A11 C5 and audit their scratch evidence.
2. If all instrument controls pass, run C2/C3 and freeze P2's disposition.
3. Execute and commit each coherent control/output milestone in frozen order.
4. Compute readings in the declared priority order, then C1
   and verdicts; otherwise stop with control diagnostics only.

## Historical prior lane

The stacked-pool CD-vintage provenance journal previously at this path is
historical as of 2026-08-26. Its final text remains available in parent commit
`51866036` and does not describe the current task.
