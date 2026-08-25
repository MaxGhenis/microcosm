# Battery package 1 lane notes

## 2026-08-25 collectibles frame-concentration follow-up

- Host evidence: the fresh 1% serial build passed the prior tail-transfer guard
  and now fails in `_validate_frame_concentration_*` because the sealed share
  for signed component `long_term_capital_gains_on_collectibles` is outside
  `[0, 1]`.
- Frozen constraints: reproduce only from checkpointed inputs; do not run a pool
  build, modify host checkpoints, tune thresholds/bands/gates/seeds/folds, or
  clamp a share. Keep all processes below 15 GiB RSS and do not push.
- Decision rule: print the exact share and its exact numerator/denominator,
  determine whether signed sums make the current ratio invalid, compare the
  definition with the battery's signed-leg treatment, and audit every other
  concentration component before choosing a sign-aware semantic correction or
  an upstream generating fix.
- Required closure: a regression pinned to the reproduced case, whole-suite and
  static-check receipts, code-cited reasoning, committed journal updates after
  each coherent step, and the final report in `FINAL_REPORT.md`.

### Exact fresh-checkpoint replay and adjudication

- Read-only replay identity: stacked `f80593d730bedafc652b6d6b0bbee462f7fac97d3cfd555b9b9e526e5dfcab6e`,
  assembled `5394c11e947380ece2070e1c1657161009626975665e25efd3e01050913c7faf`,
  and primary-QRF `d5d71f37fd312c2740461134121e2b0de28a101e4f655369d439994c3fc4d4e5`.
  It authenticated all 65 target files, ran no fit/build/write, retained the
  exact 123-input fingerprint, and peaked at 3,108,896,768 bytes RSS.
- The offending side is pre-stage collectibles: 19 positive/0 negative
  carriers (15 distinct), numerator `7754874867.9770155`
  (`0x1.ce39fff3fa1dbp+32`), denominator `7754874867.9770136`
  (`0x1.ce39fff3fa1d9p+32`), and share `1.0000000000000002`
  (`0x1.0000000000001p+0`). Post-stage has 202 positive carriers and a valid
  `0.99956427491666788` share. The validator reproduces the host exception.
- Both operands are sums of `abs(value) * weight`; for pre-stage collectibles
  they contain the identical 19 terms because `top_k=100`. Descending numerator
  order versus source-order denominator creates a two-ULP mass difference and
  one-ULP ratio overshoot. This is not signed cancellation. Collectibles is
  nonnegative by source validation and finalization; signed ST/LT/combined legs
  are already measured on magnitude, matching the shared battery semantics.
- The same independent subset/full-set reduction exists in the raw comparator,
  shared tail gate, and tail distribution receipt. The adjudicated fix is a
  shared disjoint top/remainder reduction whose denominator is constructed as
  `top_mass + remainder_mass`. It encodes the mathematical subset invariant
  directly, returns exact one for all-carrier top sets, and is neither a clamp
  nor threshold/sign tuning. Full evidence is in
  `experiments/578_puf_collectibles_concentration_replay.md`.

## 2026-08-21 capital-gains tail-guard continuation

- Host evidence: the wired capital-gains tail stage raised at a displayed
  `non_sch_d_capital_gains` weighted top-100 share of 0.8461 both before and
  after transfer. The supplied build log and `pool.checkpoints` are read-only;
  the first task is a no-build replay that prints both values and their delta at
  full precision.
- Frozen constraints: do not change the concentration threshold or any other
  threshold, band, gate, seed, or fold; do not run a local 1% host build; keep
  all processes below 15 GiB RSS; preserve unrelated untracked files.
- Required semantics: the non-regression guard may fail only for a post-stage
  increase beyond numerical noise. An already over-threshold state that this
  stage did not worsen must be retained in the report without being attributed
  to the transfer.
- Decision rule: if full-precision replay establishes a material increase,
  identify and correct the transfer mechanism before changing guard behavior.
  Regression coverage must include equality, numerical noise, a real increase,
  and unchanged pre-existing threshold exceedance with a report entry.
- Unchanged-code baseline: the five requested package test shards passed with
  6,551 passed and 74 skipped total; tracked-file Ruff passed. Plain repository
  Ruff additionally scans the pre-existing untracked helper
  `._pkg1_full_suite.py` and reports its import order; the helper is preserved
  outside this lane's commits.

### Checkpoint replay receipt

- Guarded no-build replay: pre top-100 share
  `0.84607664843916197`, post `0.84611424753688269`, delta
  `3.7599097720719676e-05`; the delta exceeds the unchanged `1e-9` noise
  tolerance. Both measurements have 805 carriers and 425 distinct values.
- The replay stopped at the comparator, left all checkpoint/source size and
  mtime fingerprints unchanged, and peaked at 3,373,678,592 bytes root RSS.
- Read-only bank inspection found 15,228 selected donors, all zero on
  `non_sch_d_capital_gains`, versus 805 positive and 22,374 zero recipient
  draws. At pre-fix commit `5abaf92c`, the allocator chose seeded recipients
  within status/nearest AGI band, while the clone replaced the chosen recipient
  slice with the donor vector
  (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1520-1556`
  at `5abaf92c`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1695-1812`
  at `5abaf92c`).
  The unsupported cross-route replacement therefore removed positive direct-leg
  mass while adding a zero donor leg; the checkpoint replay measured the
  resulting concentration increase. It was not redraw duplication or float
  noise, and the replay did not separately record the selected carrier's
  top-100 rank.
- Full method, values, identities, and mechanism reasoning are committed in
  `experiments/578_puf_capital_gains_tail_guard_replay.md`.

### Corrected mechanism and replay receipt

- Recipient capital-gains vectors are now validated and aggregated to tax-unit
  grain, with a direct-route flag and modeled ST+LT ordering value attached to
  each candidate
  (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1791-1827`).
  Support is sufficient only when each direct-vs-Schedule-D route within a
  filing status has enough recipients
  (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1891-2008`).
  Assignment retains nearest-band search but cannot cross route, and chooses
  the largest modeled ST+LT values before seeded/source-ID ties
  (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2011-2064`).
- The stage comparator measures raw pre/post shares on the production gate's
  finite positive-mass population, derives threshold state from those shares,
  and derives production eligibility from carrier counts. It fails only when
  `post - pre > 1e-9`, raw post share is over the unchanged `0.75`, and post
  carriers meet the unchanged 500 minimum. Receipts keep raw threshold state
  separate from production eligibility, so a thin raw exceedance is never
  mislabeled as within-threshold
  (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:610-820`).
- The corrected no-build replay authenticated and resumed all 47 survey, one
  housing, and 65 primary-QRF target banks; QRF fitting and target-bank writes
  were replaced with fail-closed sentinels. It measured pre and post as exactly
  `0.84607664843916197` (`0x1.b130f55de9360p-1`) with delta `0`
  (`0x0.0p+0`), 805 carriers, and 425 distinct values on both sides. The report
  entry is `pre_existing_over_threshold_not_worsened`, `stage_guard_failed` is
  false, and the complete stage-failure list is empty.
- The replay fingerprinted the checkpoint tree before and after and found no
  change. Peak root RSS was 3,313,057,792 bytes under the 15,032,385,536-byte
  guard; elapsed time was 47.531 seconds. It did not run a build.
- Separate regressions cover equal pre/post, a sub-tolerance increase, a
  material increase, and an unchanged pre-existing exceedance, while allocation
  regressions make route matching and modeled-tail ordering load-bearing
  (`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:641-811`,
  `packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:1191-1391`).

### Final verification receipt

- Initial independent review confirmed the route-aware allocator, then a
  post-review found and closed two semantic-identity holes. Raw threshold state
  and production eligibility are now separately measured and every stored
  verdict is recomputed from sealed shares/carriers
  (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:657-820`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1488-1636`).
  The legacy checkpoint key now advances with the shared tail schema/support
  contract because the legacy route executes that same transfer; only its
  stacked late-producer schedule is omitted
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:10492-10500`,
  `tools/build_us_multispine_pool.py:958-1002`,
  `tools/build_us_multispine_pool.py:2388-2407`,
  `tools/build_us_multispine_pool.py:3844-3897`).
- Review-driven tests cover multi-person aggregation, wrong-route capacity,
  transfer-level failure/report persistence, thin raw-over reporting, and
  rehashed verdict tampering
  (`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:657-811`,
  `packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:838-897`,
  `packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:1191-1442`).
- Final-tree package receipts under direct-process guards: frame 294 passed/36
  skipped, peak 6,527,254,528 bytes; fit 125 passed, peak 417,792,000;
  calibrate 201 passed, peak 466,321,408; data 275 passed/1 skipped, peak
  12,270,026,752.
- A single cumulative build-directory process reached 77% with no failure, then
  crossed the conservative 14 GiB guard at 15,554,838,528 bytes. That is below
  the binding 15 GiB ceiling but the terminated run is not accepted as suite
  evidence. The build tests were therefore replayed in fresh per-file processes.
- The fresh build manifest contains 226 tracked files (SHA-256
  `855d762df4e85fd40df7ff299d444ec5f13d43111d25d731bee1bef73cef79d6`).
  The final-tree sweep recorded 5,672 passed, 37 skipped, zero failures/errors,
  and maximum accepted root RSS 7,022,198,784 bytes in
  `test_us_trade_imdb_goldens.py`. The receipt at
  `/private/tmp/pkg1-tail-final-suite.kDinVn/receipt.jsonl` has SHA-256
  `67b18e5af01d1ed68134911a0f02449a7dedc8c316fa3da6f16b6a62b53afc22`.
  Across all five package shards, final accepted results are 6,567 passed, 74
  skipped, zero failures/errors, and the same two deselections.
- Exactly two mounted-cache probes were deselected:
  `test_cached_full_donor_matches_pinned_household_support` and
  `test_cached_full_donor_matches_locked_response_and_weight_facts`. A guarded
  attempt to run the first alone could not contain its allocation jump: the
  14.875 GiB cutoff next sampled 17,501,945,856 bytes and terminated the test.
  The second, which parses the same 3.73 GB source, was not attempted. This
  rejected attempt exceeded the lane order and is not accepted evidence; no
  further full-cache probe was run.
- Ruff passed over every tracked Python file and `git diff --check` passed. The
  pre-existing untracked `._pkg1_full_suite.py` import-order finding remains
  outside the commit. No host build ran.
- The verified mechanism/guard implementation and replay adjudication are
  committed at `8422cb15`. `FINAL_REPORT.md` now carries the exact reproduction,
  code-cited mechanism, final receipts, memory disclosure, and serial-host
  handoff in this docs-only closing commit.

## Scope and frozen constraints

- Assigned work package: all 38 checks in
  `puf_tax_sign_hurdle_and_quantile_calibration`, plus the one check in
  `schedule_d_joint_parent_reconciliation`.
- Artifact remedy: separate sign/carrier selection from conditional amount
  shape for PUF-tax transfers, and reconcile Schedule-D parents before the
  deterministic share derivation.
- Frozen: comparator bands, thresholds, quantiles, seeds, folds, and
  comparators. Builds are off-chain at `--sample-fraction 0.01
  --sample-seed 578`; never pass `--logbook-prev-row-digest` and never touch
  `logbook-pending-chain.txt`.

## Mechanism evidence read before implementation

- The monetary comparator creates separate positive and negative carrier
  masks, compares their weighted ACS/ASEC incidence, then compares weighted
  conditional quantiles of absolute amounts
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:11860`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:11930`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:11990`).
- The transfer currently accepts direct chained-QRF raw draws target by target;
  the cited path contains no post-draw sign-prevalence or conditional-quantile
  calibration stage
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:896`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1581`).
- Schedule-D capital-gain distributions are derived after transfer from two
  parent columns using route exclusivity and a packaged share, so their carrier
  rate is controlled by that joint deterministic step rather than an
  independent QRF target
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1130`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1202`).

## Setup receipt

- `uv sync --all-packages --extra us`: default cache initialization denied by
  the sandbox.
- Retry with `UV_CACHE_DIR=/private/tmp/microcosm-pkg1-puf-tax-uv-cache`:
  dependency download stopped at `msgpack==1.1.2` because outbound DNS is
  unavailable. No dependency constraint or lockfile was changed.

## Measurements

The first pre-integration 1% attempt in
`/private/tmp/microcosm-pkg1-puf-tax-before` used the frozen sample/clone
settings and set `POPULACE_FIT_N_JOBS=1` and
`POPULACE_FIT_PREDICT_WORKERS=1`; the QRF implementation binds those controls
only to execution width (`packages/microcosm-fit/src/microcosm/fit/qrf.py:404-460`).
No `--logbook-prev-row-digest` was passed. The run was stopped during primary
target 10 after `stage_profile.json` reported 63,671,549,952 bytes for taxable
interest, 60,830,138,368 for qualified dividends, 58,797,850,624 for
nonqualified dividends, and 29,037,576,192 for short-term gains. Because those
single-process peaks violate the lane's 15 GiB ceiling, the partial output is
not accepted as a control artifact and will not be resumed.

Direct source tracing found that `quantile_forest` first computes one global
largest-leaf width, allocates an `int64 (trees, max_nodes, outputs, max_leaf)`
tensor, holds per-tree slices in a list, and copies them into the final array.
Microcosm currently requests all leaf samples after its external weighted
bootstrap (`packages/microcosm-fit/src/microcosm/fit/qrf.py:463-514`), so thread
width cannot bound this allocation. An adaptive sample cap was rejected because
the dependency shuffles and truncates oversized leaves, changing the ECDF and
therefore later chained targets. The in-progress correction instead stores
exact bootstrap multiplicities in a ragged representation and must prove
bit-exact draws against the dense backend before another build.

Pinned local inputs for both builds:

- ASEC raw-stage checkpoint SHA-256
  `51e9fafcd6f16140018fa90c7afbeb6d79008bfc8c122e437d23a399b30553fe`.
- ACS household/person archives SHA-256 `8281008e...e515d0` and
  `afdc6d90...69894`.
- ACS rent donor SHA-256 `0b319b49...41bd4`, PUF H5 SHA-256
  `7669f5b5...d6df`, and source-year PUF CSV SHA-256
  `0a7fd643...f2499df`.

## Baseline verification

- Full suite command used the read-only adjudication worktree's locked
  interpreter (`policyengine-us==1.764.6`) and this worktree's five source
  roots through `PYTHONPATH`; the failed local sync had not installed the
  namespace packages.
- Pytest collected 6,509 tests, reached 100%, and exited 0. Expected warnings
  and platform/optional skips were emitted; no test failed.
- Collection-order review traced the multi-minute 44% pause to three real
  PolicyEngine-US engine/memory regressions in
  `packages/microcosm-build/tests/test_us_fiscal_refresh_memory.py:237-347`;
  it was not a stalled process.

## Design findings

- Production splits wide PUF families into suffixed batches, and those batches
  also contain retirement, rare-tail, and QBI targets. Calibration therefore
  needs an exact execution-contract-bound `(entity, target, sign, carrier,
  amount)` registry for only the assigned checks
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:2268-2380`;
  `packages/microcosm-build/src/microcosm/build/us_runtime/puf_support.py:208-254`).
- The safe common seam is after banked or in-memory raw family draws complete,
  before decoding and null-only insertion. Calibrating copies there preserves
  raw chained priors, immutable bank checkpoints, codecs, and native cells
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:992-1043`;
  `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1581-1703`;
  `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:2951-3035`).
- Carrier decisions must be deterministic within each availability pattern;
  the conditional magnitude reference pools each donor target/sign because the
  battery measures aggregate carrier quantiles
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1247-1386`;
  `packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:11860-12021`).
- Schedule-D requires the donor-weighted four-state parent table, including a
  real LT-positive/direct-positive overlap. The existing derivation routes that
  overlap away from Schedule D but does not forbid it
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:605-651`).
- A cold historical 1% primary-QRF run peaked at 84,729,479,168 bytes, so it is
  prohibited under this lane's 15 GiB order. Current checkpoint identity does
  not accept the historical cache. A fresh run requires smaller bit-invariant
  prediction chunks plus in-process RSS enforcement before it is safe
  (`packages/microcosm-fit/src/microcosm/fit/qrf.py:318-351`;
  `packages/microcosm-build/src/microcosm/build/stage_profile.py:100-217`).

## Pure calibration kernel receipt

- The hurdle is now an explicit weighted allocation kernel: binary selection
  ranks raw carrier propensity with stable-ID tie breaks, while the three-class
  allocator handles signed targets without conflating sign with magnitude
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer_calibration.py:164-258`).
- Conditional amounts are mapped only after signs are fixed. The kernel ranks
  all final-domain carriers, including immutable native carriers, maps only the
  mutable rows through the donor sign's weighted empirical inverse CDF,
  restores the sign, and asserts that no sign changed
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer_calibration.py:259-382`).
- Immutable rows and zero-weight rows constrain capacity instead of silently
  becoming calibration candidates; receipts disclose target projection and
  indivisible-weight allocation error
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer_calibration.py:501-575`).
- The first Schedule-D subset solver was rejected during review before commit:
  it imposed a 32-row production limit and preserved only unweighted parent
  support. The replacement constructs disjoint positive/zero swaps only within
  exact-equal-weight buckets, so it scales linearly after sorting and preserves
  the weighted direct-parent carrier and conditional value distribution exactly
  (`packages/microcosm-build/src/microcosm/build/us_runtime/schedule_d_joint_reconciliation.py:110-303`).
- The Schedule-D receipt distinguishes the requested target, its feasible
  capacity projection, and the residual indivisible-swap error; unequal-weight,
  signed, native, and zero-weight rows remain immutable
  (`packages/microcosm-build/src/microcosm/build/us_runtime/schedule_d_joint_reconciliation.py:304-386`).
- A second pre-commit audit found crossing immutable amount anchors, a missing
  one-for-one Schedule-D repair, and cancellation-sensitive capacity arithmetic.
  The amount mapper now removes immutable CDF mass before mapping mutable ranks;
  the Schedule-D frontier adds a deterministic exchange repair and derives
  bounds directly from feasible carrier masks (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer_calibration.py:316-389`;
  `packages/microcosm-build/src/microcosm/build/us_runtime/schedule_d_joint_reconciliation.py:190-257`).
- Focused verification: 37 helper test cases and the complete 495-case runtime
  source-blindness module passed; Ruff passed for both helpers, both test
  modules, and the reviewed runtime inventory.
- Commit-boundary verification: the complete repository pytest run reached
  100% and exited 0 after the constrained-CDF and weight-matched reconciliation
  revisions. Its warnings matched the baseline categories; no failure was
  emitted.

## Wiring continuation receipt

- The host's paired 1% comparison found identical 127-line failure sets on this
  branch and `origin/main`: zero fixed and zero introduced. The build log had no
  calibration lines because `acs_transfer_calibration.py` had no production
  caller. Those partial artifacts are evidence of non-execution, not remedy
  results; this continuation did not run another 1% build.
- The common banked/non-banked ACS path now decodes raw QRF predictions, invokes
  PUF-tax calibration on copies, then performs the existing null-only fill.
  Raw chained priors and bank checkpoints remain unchanged. Reconciliation
  receipts are attached only to selected assigned targets.
- Activation mirrors pkg3 commits `22b2c6bc` and `176c60fc`: callers pass a
  default-empty exact `(entity, target)` selection, validated against both the
  requested surface and the frozen 20-target/38-check policy. The stacked early
  and late owners derive that selection from their active surface and pass only
  the same keys for which they bind frozen references.
- The wiring regression puts assigned `qualified_dividend_income` beside
  unassigned `taxable_interest_income` in one `puf_tax_itemization` batch. It
  records the imported magnitude-kernel calls, proves the default makes none,
  proves the assigned selection calls only with the assigned reference, proves
  the unassigned output is bit-equal to its raw baseline with no receipt, and
  proves an attempted unassigned selection fails before fitting.
- The default stacked path suppresses Schedule-D derivation during late ACS
  transfer, so the parent kernel is wired later at `_complete_schedule_d_input`.
  The source-aware owner supplies transient ASEC-clone-0 reference and
  ACS-clone-0 recipient roles; reconciliation consumes and removes the marker,
  byte-preserves the long-term parent, preserves the weighted direct-parent
  carrier/amount distribution, and derives the Schedule-D leaf afterward.
- Independent review closed two receipt-only gaps before commit: the derive
  operator now declares both the mutable `non_sch_d_capital_gains` parent and
  the derived leaf, while the role-authority SHA covers its final row counts.
  Live registry checks confirmed the expanded derive contract does not enter
  the early or late ACS transfer surfaces; no remaining review blocker exists.
- Final validation: four load-bearing assigned/unassigned and Schedule-D wiring
  fixtures pass; all 73 ACS transfer tests pass; 1,020 touched-runtime tests
  pass; and the complete 6,623-test repository collection reaches 100% with no
  failure/error marker and an empty pytest `lastfailed` cache. The macOS
  `time -l` wrapper alone returns 1 after completion because its sandboxed
  `sysctl kern.clockrate` probe fails, reproducible with `time -l true`.
- Full Ruff, lock freshness, changed-file formatting, and `git diff --check`
  pass. The repository-wide formatting audit reports 49 pre-existing unrelated
  files; they remain untouched. No continuation 1% build was run, so the host
  retains the frozen branch/baseline comparison.
- A fresh independent verification at implementation HEAD `d9a38965` re-ran
  the four load-bearing wiring fixtures, the complete 110-test ACS
  calibration/transfer/Schedule-D set, and the repository suite. The full run
  exited zero in 53:11 with 6,551 passed, 74 skipped, 1,890 established
  warnings, and an empty `lastfailed` cache (6,625 collected). Separate scope
  and call-flow audits found no default-stacked leakage or unwired assigned
  target. At that calibration-only implementation HEAD, the explicit retiring
  `--legacy-two-spine` route was outside the remedy; the current tail section
  above supersedes its semantic-key claim.
