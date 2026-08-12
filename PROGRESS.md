# Progress

## State

The Sabelhaus crosswalk memo is in progress on
`sabelhaus-crosswalk-memo`, forked locally from the clean
`qbi-v3-wiring` tip at `cfbf6330`. Work is offline. The outbound deliverable
will be assembled only from the user-designated on-disk artifacts and written
to `~/ops/populace-qbi-port/sabelhaus-crosswalk-memo.md`.

## Done

- Read the repository guidance in `CLAUDE.md`.
- Verified the source worktree, branch tip, and clean starting state.
- Verified all three research-factsheet paths and the designated QBI source
  worktree are present on disk.
- Created the isolated local branch `sabelhaus-crosswalk-memo` from
  `qbi-v3-wiring`; no network, push, email, or publication action is in scope.
- Historicized the preceding QBI remediation journal headings below so their
  state language cannot be mistaken for this task's live state.

## Next

- Extract and reconcile the taxonomy, PUF lineage, SSTB codes and tier logic,
  published aggregates, SCF/SOI sourcing, and benchmark figures.
- Draft and audit the single self-contained memo, including the required
  five-line section-to-artifact source summary.
- Write the audited memo to the required output path and record final checks.

## Historical QBI remediation journal (superseded 2026-08-12)

The following “current” headings described the earlier QBI remediation task
when written. They are retained verbatim except for heading labels and are not
the current state or next actions for the Sabelhaus memo.

## Historical task

Close the adjudicated adversarial-review blockers across the #530 branch
stack, starting on `qbi-port-530` and propagating each fix through
`qbi-v3-wiring`. The work remains offline in
`.claude/worktrees/populace-wt-530`; no push or PR operation is in scope.

## Historical state

- The supervisor's 2026-07-25 review verdict has been read in full.
- This resumed lane found the designated worktree on `qbi-v3-wiring` at
  `6d72411`, with one uncommitted, coherent start on finite-value validation
  in `qbi_simulation.py`; that edit is being completed in place.
- The branch ancestry is intact:
  `qbi-port-530` -> `qbi-v2-engine` -> `repeal-validation-298` ->
  `qbi-v2-content` -> `qbi-v3-wiring`.
- The `qbi-port-530` report restoration is complete. Its
  `FINAL_REPORT_QBI_530.md` contains no forbidden incumbent literal; history
  shows the reviewed literal first enters on descendant commit `e97c6d3`, so
  it will be scrubbed when that content-layer version enters the worktree.
- The base and repeal fixes are merged through `qbi-v2-content`.
- `qbi-v2-content` is merged into `qbi-v3-wiring` at `6d72411`.
- Repeal-benchmark failures are now row-contained and cannot abort payload
  construction; a deliberately failing first entry and succeeding second
  entry prove continuation.
- The QBI 530 report version introduced on the content layer is free of every
  forbidden incumbent-package spelling.
- Items 1-3 have been independently re-audited against branch blobs, commit
  ancestry, implementation, regression coverage, and report corrections; no
  functional gap remains.
- Every ordinary v3 float field is now checked for finiteness before any
  simulation stream is consumed. The required AGI `-inf`/`+inf` outer
  sentinels remain valid.
- The synthetic v1/v2 isolation contract now covers every public output leaf
  for both versions with 13 byte-exact hashes and two support-mask/tolerance
  goldens per version.
- `FINAL_REPORT_QBI_V3_WIRING.md` contains no forbidden incumbent-package
  literal and now distinguishes complete synthetic v1/v2 stream goldens from
  the restricted artifact replay and host-SSTB parity checks.

## Historical done

- Confirmed the exact target worktree and clean starting state.
- Read `AGENTS.md`, `CLAUDE.md`, and the adjudicated review log.
- Confirmed the required layer branches and their current ancestor chain.
- Restored `FINAL_REPORT.md` byte-for-byte from `c09f6db` in commit
  `a49e3f5`.
- Swept all of `FINAL_REPORT_QBI_530.md` on this layer for every forbidden
  incumbent spelling; the result is clean.
- Merged the updated `qbi-port-530` into `qbi-v2-engine` in `f65fd0e`.
- Merged the updated `qbi-v2-engine` into `repeal-validation-298` in
  `b77f29c`.
- Contained per-entry repeal build, simulation, and calculation exceptions,
  replaced the vacuous missing-simulator test, historicized the original
  non-blocking claim, and added the behavior fragment in `a88a3c5`.
- Focused reform-validation pytest passes; Ruff check and format check pass on
  the touched Python files.
- Merged the updated `repeal-validation-298` into `qbi-v2-content` in
  `705b528`.
- Scrubbed the descendant QBI 530 report path and swept the whole report in
  `b045eea`.
- Merged the updated `qbi-v2-content` into `qbi-v3-wiring` in `6d72411`.
- Re-read the original remediation specification and adversarial-review log
  after resumption.
- Verified the exact #462 `FINAL_REPORT.md` blob, the clean QBI-530 report,
  repeal exception-row continuation behavior, dated report correction,
  behavior fragment, and propagation ancestry for fixes 1-3.
- Added exhaustive finite checks for v3's nested public float surface and the
  required behavior fragment in `adfad66`.
- Made both pre-fix NaN corruptions executable regressions, then asserted the
  restored validator rejects the same direct caller objects in `ae5196f`.
- Added and independently captured the complete v2 15-leaf golden surface,
  retained v1's complete golden surface, and made both assert exhaustive
  public-column coverage in `a9b042e`.
- Scrubbed the v3 wiring report, corrected its unsupported full-artifact
  golden claim, and historicized its pre-remediation suite count in `c7e51bc`.
- The complete QBI simulation test module passes (24 passed, 2 skipped);
  Ruff check and format check pass on the touched Python files.

## Historical next

- Run focused contract checks, Ruff, the full tip suite, and the incumbent
  guard from the prescribed plain worktree outside `.claude`.
- Record final verification evidence and the finding-to-commit mapping in the
  output report.

## Historical progress

The completed QBI v3 wiring/evidence, QBI v2 content, and repeal-validation
handoffs remain in `PROGRESS_QBI_V3_WIRING.md`,
`PROGRESS_QBI_V3_EVIDENCE.md`, `PROGRESS_QBI_V2_CONTENT.md`, and
`PROGRESS_REPEAL_VALIDATION.md`. The remaining sections are a prior task's
journal retained for branch history.

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
