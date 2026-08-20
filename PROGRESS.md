# Retirement factorial progress

## State (2026-08-19)

The `battery-retirement-factorial` lane is active from clean `origin/main` at
`164027e2`. Removal-only is committed at `1a8ad451`; broad-addition-only is
implemented, independently reviewed, and suite-green. It is ready for its
coherent commit. No frozen gate control has changed.

The required `uv sync --all-packages --extra us` was attempted first. The
default cache was sandbox-denied; retrying with `UV_CACHE_DIR` under `/tmp`
created `.venv` but dependency download stopped because this sandbox has no
DNS/network access. Baseline verification therefore used the provisioned
arm-split environment with this worktree's package sources forced on
`PYTHONPATH`.

## Done (2026-08-19)

- Confirmed the worktree was clean and `HEAD == origin/main == 164027e2`.
- Read `CLAUDE.md`, the arm-split adjudication Markdown/JSON, all 16 assigned
  `retirement_model_and_data` rows, and their cited comparator/QRF source.
- Read the arm-split synthesis treatment boundary and prescribed next
  factorial (`experiments/phase_p_arm_split/SYNTHESIS.md:27-32,346-352,376-380`
  in the read-only arm-split worktree).
- Confirmed the 16 checks are artifact measurements: monetary incidence is
  weighted ACS/ASEC carrier prevalence and QED is the maximum normalized
  p10/p25/p50/p75/p90 carrier-amount separation
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:11860-11930,11990-12021`),
  while the artifact values come from availability-pattern chained-QRF draws
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:896-916,1581-1648`).
- Attempted the GitNexus exploration/impact workflow; no GitNexus MCP graph is
  exposed in this session, so direct history, source, tests, and diff checks
  are the evidence fallback.
- Resolved the removal arm as early `person/puf_tax_itemization` baseline minus
  only the two direct-income predictors, and the broad arm as the baseline
  surface retaining those predictors plus the 14 synthesized non-veteran
  fields. All other early families and the late transfer remain baseline.
- Established a clean baseline suite: 6,525 tests collected, exit 0, with
  expected skips/warnings only. The focused QRF-chain suite separately passed
  26 tests in 302.42 seconds.
- Audited historical build receipts: the old 1% process reached
  84,729,479,168 bytes RSS and a 25% arm reached 81,026,367,488 bytes. A cold
  build is therefore forbidden by this lane's `<15 GiB` standing order; this
  is an evidence blocker, not permission to weaken the memory ceiling.
- Committed the initial state/done/next journal as `eac44dbe` after the clean
  baseline suite.
- Implemented removal-only per-family predictor declarations and bound them to
  stacked authority v11. Only early person/PUF loses the two direct-income
  predictors; non-PUF early families and late transfer retain baseline wiring.
- Targeted removal verification passes: lineage 8, ACS transfer 61, stacked
  spine 225, late DAG 30, plus the focused wiring/authority set 17. A separate
  review found and fixed one stale v10 test mirror and one exact-validation
  hole for an extra empty predictor entity; their three regressions pass.
- The complete removal tree passes all 6,535 collected tests (exit 0, expected
  skips/warnings only). Repository-wide `ruff check .` and `git diff --check`
  also pass.
- Committed the independently runnable removal-only snapshot as
  `1a8ad451c6eff17d405ef75cbdd014de72447153`.
- Transformed the working tree into broad-addition-only: the two baseline
  direct-income predictors are restored and exactly 14 synthesized non-veteran
  fields are added to early person/PUF. Other early and late families remain
  baseline.
- Broad affected verification passes 650 checks across source/spec, ACS/PUF,
  multispine/stacked, plan, and pool-tool modules. Independent review, Ruff,
  formatting, byte-compilation, and diff hygiene report no blocker.
- The complete broad tree passes all 6,571 collected tests (exit 0, expected
  skips/warnings only). Repository-wide `ruff check .`, `git diff --check`, and
  the final frozen-control scan pass.

## Next (2026-08-19)

1. Commit the suite-green broad-addition snapshot and record its exact SHA.
2. Preserve both arms' wiring proofs; do not cold-launch the known over-cap 1%
   materialization path.
3. Write the fail-closed owner-run 25% build-and-gate charter, including the
   prerequisite memory-safe path and serial RAM-guarded protocol.
4. Report every assigned check honestly as measured or not measured, finish
   `_LANE-NOTES.md`, and write `FINAL_REPORT.md`.

## Historical base entry

## State

Microcosm #516 whole-row donor outlier screen is complete on
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
  139; microcosm-data 138 with 1 skip. The directly affected tail-bound suite
  adds 12 passes. Ruff format/check and `git diff --check` are clean.
- Wrote `SOL_516_REPORT.md` with the exact seam, consumer-by-consumer file:line
  audit, expected 208,611-row real-artifact effect, verification results, count
  sweep, and deliberately untouched surfaces.

## Next

- PR #527 review cycle, then merge. After both #525 and #527: rebuild the
  base/release; the mortgage critical-fit ratchet (0.20 -> 0.15) waits on a
  run that holds per `us_critical_targets.py`.
- Root record-level ETL carve stays open on microcosm#515.
