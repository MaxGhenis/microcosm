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

Before/after 1% results will be added after the frozen builds.

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
- Carrier quotas must be donor weighted within each availability pattern;
  conditional magnitude transport should pool each target/sign across patterns
  because the battery measures aggregate carrier quantiles
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
