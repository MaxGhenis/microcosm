# Final report: pkg1 ACS calibration wiring

## Outcome

The current `battery-pkg1-puf-tax` tree wires the calibration kernels into the
default stacked production path for exactly the assigned PUF-tax surface and
the separate Schedule-D parent check. The production implementation is
`51054801`; later production blobs are byte-identical to that commit. This
continuation re-established the call path, exact scope, and load-bearing tests
from source and fresh execution.

The host's identical 127-line 1% result remains valid evidence for the unwired
tree it tested. No post-wiring 1% result exists yet, so this report establishes
production callability and regression coverage—not empirical 1% efficacy. No
1% build ran in this continuation.

| Evidence tree | Production state | Evidence |
| --- | --- | --- |
| `e16b8b50` (`51054801^`) | Kernel definitions exist, but ACS transfer has no import, selector, or call | Matches the host's zero-effect/no-caller diagnosis |
| `51054801` and current production blobs | Default stacked owners pass exact selectors into the common post-decode calibration seam | Direct source trace plus assigned-call/unassigned-non-call fixtures |

## Wiring and exact scope

- The frozen PUF-tax policy contains 20 unique ACS `(entity, target)` leaves:
  17 person and 3 tax-unit targets. They cover 15 carrier checks and 23
  conditional-amount checks, exactly the assigned 38 work-package rows.
- The canonical stacked surfaces partition those targets into 7 early-gap-fill
  and 13 late-transfer targets, with zero overlap, omission, or selected
  unassigned target.
- Generic `transfer_acs_inputs` deliberately defaults to an empty calibration
  selection. The default stacked production owners—not generic library
  defaults—derive the active exact-key allowlist, bind caller-owned opaque
  recipient scopes and frozen target references, and pass that allowlist into
  transfer.
- `transfer_acs_inputs` validates the allowlist against both the requested
  transfer surface and `PUF_TAX_TRANSFER_CALIBRATION_POLICY`, intersects it
  with live incomplete targets per family/batch, and invokes calibration only
  for that intersection.
- Banked and in-memory QRF modes converge on one seam: decode predictions,
  invoke `allocate_weighted_signs`,
  `select_weighted_binary_carriers`, and
  `map_sign_preserving_weighted_magnitudes` for selected targets, then run
  the existing null-only fill. Unassigned siblings receive neither mutation
  nor reconciliation evidence.
- The default CLI reaches the seam through both
  `gap_fill_stacked_spine` (early) and
  `run_stacked_late_producer_dag` (late). The explicit retiring
  `--legacy-two-spine` route retains the empty selector and is outside this
  remedy.

Schedule-D is a separate assigned parent check. The default tool calls
`prepare_stacked_tail_derivation`, which assigns only ASEC clone 0 as the
reference role and ACS clone 0 as the recipient role, then passes that prepared
frame to `derive_multispine_pool_inputs`. Its first relevant operator,
`_complete_schedule_d_input`, consumes the transient role and invokes the
preservation-specific `reconcile_schedule_d_joint_parents` kernel before
deterministic leaf derivation.

The old build's source-level absence of a caller proves non-execution; its zero
calibration log lines merely corroborate that fact. The current seam records
nested target reconciliation receipts rather than console messages, so the
host's new run should inspect receipts and stage identity as well as the
failure-set diff.

## Load-bearing regressions

The fixture-scale transfer regression places assigned
`qualified_dividend_income` beside unassigned
`taxable_interest_income` in the same bounded family and records calls to the
real imported magnitude kernel. It proves:

- empty selection makes zero calls;
- the assigned selection invokes the kernel with only its assigned reference;
- the unassigned sibling is unchanged from the raw-transfer baseline and has
  no reconciliation receipt; and
- attempting to select the unassigned target fails before fitting or calling
  the kernel.

The stacked-owner fixture independently captures the production boundary and
requires exactly `(("person", "qualified_dividend_income"),)` despite the
same unassigned sibling. Schedule-D fixtures require role production,
prepared-frame handoff, parent-kernel consumption, role removal, preserved
parent geometry, and the marker-absent compatibility no-op. Removing the
kernel call, either owner selector, the prepared-frame handoff, or the
Schedule-D reconciler makes a committed fixture fail.

## Fresh verification

- Three focused load-bearing fixtures: 3 passed in 8.71 seconds.
- Complete ACS transfer, calibration-kernel, and Schedule-D modules: 110
  passed in 14.99 seconds.
- Resource-compliant repository replay: all 263 tracked test files ran in
  fresh interpreters with fit/BLAS widths pinned to one, pytest's cache
  disabled, and a 14 GiB live RSS guard. Results were 6,549 passed, 74 skipped,
  zero failures, zero errors, and exactly 2 explicit cache-probe deselections.
- The two deselections were
  `test_cached_full_donor_matches_pinned_household_support` and
  `test_cached_full_donor_matches_locked_response_and_weight_facts`. Each
  independently parses the mounted 3.73 GB SIPP donor and cannot execute
  within this lane's memory ceiling; every other test in both files passed.
- Maximum accepted RSS was 11,845,517,312 bytes in
  `packages/microcosm-data/tests/test_loader.py`, below both the 14 GiB guard
  and 15 GiB charter ceiling.
- Test manifest SHA-256:
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`.
  Fresh TSV receipt:
  `/private/tmp/pkg1-wiring-suite-fresh.xtCkap/receipt.tsv`, SHA-256
  `1fb02742e382b0cba3c89567120b581e53b04aa3f4edb12aa2b2f822e63eb410`.
- Full `ruff check .`: pass.
- Ruff formatting for all 17 branch-changed Python files: pass.
- Explicitly unfrozen `uv lock --check`: pass.
- `git diff --check`: pass.
- Pytest `lastfailed` cache: `{}`.

The canonical incidence bounds, conditional quantiles, and both battery
tolerances compare literally equal to `origin/main`. This continuation made
no band, threshold, quantile, seed, fold, comparator, dependency, or lock
change. The user-provided `_WIRING-CONTINUATION.md` remains untracked and
untouched.

## Causal commits

- `56fd9bf6` — add the sign-aware calibration primitives.
- `e16b8b50` — last unwired production tree; this is `51054801^`.
- `51054801` — wire exact scoped ACS calibration and its invocation
  regression.
- `7298590f` — make the Schedule-D prepared-frame handoff load-bearing.
- `86f9dfcd` — cover repeated cold/resumed Schedule-D handoffs.
- `432a0487` through `4527382c` — current source audit, focused/module
  tests, guarded suite replay, and static-gate receipts.

## Host handoff

Run the frozen 1% comparison from the final committed current tree using the
default stacked pipeline. Do not pass `--legacy-two-spine`. Diff the assigned
failure set against the existing `origin/main` 1% baseline and inspect the
PUF-tax reconciliation receipts plus the Schedule-D joint-parent receipt. That
host run—not this source audit—will determine the post-wiring effect size.
