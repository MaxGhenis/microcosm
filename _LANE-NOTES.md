# Battery package 1 lane notes

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
