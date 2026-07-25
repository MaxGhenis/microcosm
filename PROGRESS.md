# Progress

## Current task

Close the adjudicated adversarial-review blockers across the #530 branch
stack, starting on `qbi-port-530` and propagating each fix through
`qbi-v3-wiring`. The work remains offline in
`.claude/worktrees/populace-wt-530`; no push or PR operation is in scope.

## Current state

- The supervisor's 2026-07-25 review verdict has been read in full.
- The designated worktree started clean, and the branch ancestry is intact:
  `qbi-port-530` -> `qbi-v2-engine` -> `repeal-validation-298` ->
  `qbi-v2-content` -> `qbi-v3-wiring`.
- The `qbi-port-530` report restoration is complete. Its
  `FINAL_REPORT_QBI_530.md` contains no forbidden incumbent literal; history
  shows the reviewed literal first enters on descendant commit `e97c6d3`, so
  it will be scrubbed when that content-layer version enters the worktree.

## Current done

- Confirmed the exact target worktree and clean starting state.
- Read `AGENTS.md`, `CLAUDE.md`, and the adjudicated review log.
- Confirmed the required layer branches and their current ancestor chain.
- Restored `FINAL_REPORT.md` byte-for-byte from `c09f6db` in commit
  `a49e3f5`.
- Swept all of `FINAL_REPORT_QBI_530.md` on this layer for every forbidden
  incumbent spelling; the result is clean.

## Current next

- Propagate `qbi-port-530` through `qbi-v2-engine`, then implement repeal-entry
  exception containment on `repeal-validation-298`.
- Propagate through content/wiring and add finite-v3 validation plus complete
  v1/v2 stream regression coverage; scrub the descendant report literals as
  each affected report enters the worktree.
- Run the full tip suite and the incumbent guard from the prescribed plain
  worktree outside `.claude`, then record commit/evidence mappings.

## Historical progress

The remaining sections are a prior task's journal retained for branch history.

## State

Populace #516 whole-row donor outlier screen is complete on
`mortgage-donor-outlier-screen` (rebased onto `origin/main` after the #515
interim carve merged as #525). The `puf_tax_detail` donor now drops tax units
whose grouped raw mortgage interest reaches $10M before the #515 carve
(pinned-artifact effect: 3,066 rows, weight 3,684 of ~161M, removing $2.947T
of phantom mortgage-interest mass), with the checkpoint schema bumped to v3
so post-carve pre-screen checkpoints rebuild.

## Done

- Confirmed a clean starting worktree at `aef1c56`.
- Read the repository guidance and established the #515 donor carve as the
  screen's required downstream boundary.
- Started source-level audits of every donor-frame consumer, checkpoint
  validation, row-count pins, and existing donor-fact summaries.
- Attempted the requested GitNexus impact workflow; the managed filesystem
  denied its global registry write. Its local index also exposed a broad
  `build/` ignore mismatch, so the completed impact audit uses direct source
  call sites and tests.
- Added `US_PUF_DONOR_MORTGAGE_OUTLIER_CEILING = 10_000_000.0` with the
  structural rationale and pinned-artifact receipts.
- Added a whole-row screen on grouped raw person `home_mortgage_interest`
  after tax-unit assembly, before the #515 carve, with retained-index reset.
- Confirmed no downstream consumer pairs donor rows to the original HDF arrays
  or carries a stale donor-length vector; values and weights always originate
  from the same screened frame.
- Bumped the primary QRF checkpoint schema from v2 to v3 and made the stale
  checkpoint regression track the live constant while retaining literal-v1
  corruptions.
- Added regression coverage for the exact grouped boundary, whole-row removal,
  retained/carved $5M row, raw-$10.5M pre-carve ordering, and constant.
- Requested suites pass: PUF support/QRF 53; plan/gates 195; fiscal targets
  139; populace-data 138 with 1 skip. The directly affected tail-bound suite
  adds 12 passes. Ruff format/check and `git diff --check` are clean.
- Wrote `SOL_516_REPORT.md` with the exact seam, consumer-by-consumer file:line
  audit, expected 208,611-row real-artifact effect, verification results, count
  sweep, and deliberately untouched surfaces.

## Next

- PR #527 review cycle, then merge. After both #525 and #527: rebuild the
  base/release; the mortgage critical-fit ratchet (0.20 -> 0.15) waits on a
  run that holds per `us_critical_targets.py`.
- Root record-level ETL carve stays open on populace#515.
