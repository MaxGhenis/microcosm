# Final report: pkg1 ACS calibration wiring

## Outcome

The current `battery-pkg1-puf-tax` tree executes calibration in the default
stacked production path for exactly the assigned PUF-tax targets, plus the
separate Schedule-D joint-parent reconciliation. The requested wiring was
already present in post-host commit `51054801`; the host's identical 127-line
failure sets came from its unwired parent, `e16b8b50` (`51054801^`). Current
production-source blobs remain byte-identical to `51054801`, so this
continuation audited the live call graph and replayed the load-bearing tests
rather than adding a duplicate call site.

No 1% build ran locally. The next 1% comparison belongs to the host and must use
the final committed tree's default stacked entrypoint.

| Evidence tree | Production state | Meaning |
| --- | --- | --- |
| `e16b8b50` (`51054801^`) | Kernel definitions exist, but ACS transfer has no import, selector, or call | This is consistent with the host's zero-effect result |
| `51054801` and current production blobs | Default stacked owners pass exact selectors into the shared post-decode calibration seam | The assigned kernel is callable in production and unassigned targets remain excluded |

## Exact production scope

The frozen PUF-tax policy contains 20 unique ACS `(entity, target)` leaves: 17
person targets and 3 tax-unit targets. Those leaves implement exactly the 15
carrier legs and 23 conditional-amount legs assigned to this work package. The
live stacked transfer surfaces partition them into 7 early-gap-fill targets and
13 late-transfer targets, with no overlap, omission, or selected unassigned
target.

`transfer_acs_inputs` defaults to an empty calibration selection. The default
stacked production owners derive an active exact-key allowlist and explicitly
pass it, caller-owned recipient scopes, and frozen target references into the
transfer seam. The transfer validates that selection against both its requested
surface and `PUF_TAX_TRANSFER_CALIBRATION_POLICY`, then calibrates only the live
selected intersection. An unassigned sibling in the same QRF family and batch
receives neither an adjustment nor reconciliation evidence.

Both banked and in-memory QRF execution converge on the same order:

1. decode predictions;
2. invoke the selected policy's `allocate_weighted_signs`,
   `select_weighted_binary_carriers`, and/or
   `map_sign_preserving_weighted_magnitudes` primitive;
3. apply the existing null-only fill.

The default CLI reaches this seam through `gap_fill_stacked_spine` for the early
owner and `run_stacked_late_producer_dag` for all bounded late owners. The
explicit retiring `--legacy-two-spine` route retains the safe empty default and
is outside this remedy.

Schedule-D is deliberately separate from the ACS QRF calibration seam. The
default tool's `prepare_stacked_tail_derivation` marks only ASEC clone 0 as the
reference and ACS clone 0 as the recipient, and passes that exact prepared frame
to `derive_multispine_pool_inputs`. `_complete_schedule_d_input` consumes the
roles and invokes the preservation-specific
`reconcile_schedule_d_joint_parents` equal-weight-swap kernel before
deterministic leaf derivation.

## Load-bearing wiring regressions

The direct fixture-scale regression
`test_calibration_kernel_is_invoked_only_for_selected_assigned_target` places
assigned `qualified_dividend_income` beside unassigned
`taxable_interest_income` in one family/batch and records calls to the imported
magnitude primitive. It proves that:

- the empty default makes zero calls;
- selecting the assigned target invokes the kernel with only its assigned
  reference;
- the unassigned sibling remains identical to the raw-transfer baseline and
  has no reconciliation receipt; and
- selecting the unassigned target is rejected before fitting or invocation.

Separate stacked fixtures capture the exact early and late production-owner
bindings. Schedule-D fixtures require role creation, exact prepared-frame
handoff, parent-kernel consumption, role removal, preserved parent geometry,
all terminal tool states, and checkpoint resume. Removing the common call,
either owner binding, the prepared-frame handoff, or the Schedule-D reconciler
therefore makes a committed test fail.

This matches pkg3's scoped-binding pattern from regression `22b2c6bc` and
implementation `176c60fc`: a default-empty exact-key selector, request
validation, owner-side active intersection, selected-only execution, and
selected-only evidence.

## Fresh verification

- Nine expanded load-bearing wiring cases passed; a separate replay of the four
  slow tool-entrypoint states passed in 342.35 seconds.
- All 110 tests in the ACS transfer, calibration-primitives, and
  Schedule-D reconciliation modules passed in 21.04 test seconds under a
  14 GiB live root-RSS guard. Maximum root RSS was 600,440,832 bytes.
- The exact 263-file tracked test manifest ran in fresh interpreters with
  fit/BLAS thread widths pinned to one, pytest's cache disabled, and a
  15,032,385,536-byte (14 GiB) live root-RSS guard. Results were 6,549 passed,
  74 skipped, zero failures, zero errors, and exactly two explicit full-donor
  cache-probe deselections. No guard fired.
- Maximum accepted full-suite RSS was 11,843,141,632 bytes in
  `packages/microcosm-data/tests/test_loader.py`, below both the 14 GiB guard
  and the 15 GiB order.
- The two deselected cache probes each independently parse the mounted 3.73 GB
  SIPP donor and cannot execute within this lane's memory ceiling. Every other
  test in both containing files passed. A platform-only PostgreSQL module
  recorded its normal collection skip because `pgserver` is unavailable.
- The tracked-manifest SHA-256 is
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`.
  The 263 JUnit files are in
  `/private/tmp/pkg1-suite-current-retry-42c471aa`; their ordered aggregate
  SHA-256 is
  `7a60dc30fffb02c54030f405f7158ef377e06e0c19f90c706659fed72eb8c6cb`.
- `ruff check .`, Ruff formatting for all 17 branch-changed Python files, an
  explicitly unfrozen `uv lock --check`, `git diff --check`, and the pytest
  `lastfailed` audit all passed. The last-failed cache is `{}`.

An optional wheel-build probe could not begin in this network-restricted
environment: isolated building would need to fetch `hatchling`, and the active
environment does not have that backend installed. No packaging, dependency,
lock, production, or test source changed in this continuation.

## Frozen-gate check

The live runtime comparator declaration is literally equal to `origin/main`:
incidence bounds `(0.8, 1.25)`, conditional quantiles
`(0.10, 0.25, 0.50, 0.75, 0.90)`, quantile-envelope tolerance `0.25`,
categorical-TVD tolerance `0.25`, and the Schedule-D
`monetary_sign_separated` metric are unchanged. Sample/clone seed `578` and
pool seed `0` are also unchanged; no relevant fold changed.

`origin/main` now has newer redundant `us/spec/battery.yaml` and runtime-adapter
representations that this older branch does not contain, but their gate values
agree with this branch's runtime constants. That is branch staleness, not a
band, threshold, or metric change. The Schedule-D kernel's internal
`abs_tol=1e-12` exact-margin assertion is arithmetic validation, not a battery
comparator tolerance.

## Causal commits

- `56fd9bf6` — add the sign-aware calibration primitives.
- `e16b8b50` — last unwired production tree; this is `51054801^`.
- `51054801` — wire exact scoped ACS calibration and its invocation regression.
- `7298590f` — make the Schedule-D prepared-frame handoff load-bearing.
- `86f9dfcd` — cover repeated cold/resumed Schedule-D handoffs.
- `de811725`, `42c471aa`, `2d50f419`, and `4f038481` — reopen the continuation,
  audit current source scope, replay the guarded suite, and record final static
  and frozen-gate evidence.

## Host handoff

Run the frozen 1% comparison from the final committed tree using the default
stacked pipeline; do not pass `--legacy-two-spine`. Diff the assigned failure
set against the existing `origin/main` 1% baseline and inspect the PUF-tax
target reconciliation receipts plus the Schedule-D joint-parent receipt. That
host run—not this source audit—will establish post-wiring empirical effect.
