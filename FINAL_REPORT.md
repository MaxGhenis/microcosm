# Final report: pkg1 ACS calibration wiring

## Outcome

Completed the wiring continuation on `battery-pkg1-puf-tax`. The PUF-tax
calibration kernels now execute in the default stacked production ACS transfer
path for exactly the assigned 20 targets (15 carrier checks and 23
conditional-amount checks, 38 assigned rows total), with the Schedule-D
joint-parent repair executing in the default stacked derive path.

No frozen battery band, incidence threshold, QED ceiling, quantile, seed, fold,
or comparator changed. No continuation 1% build was run; the host retains the
next frozen branch/baseline comparison.

## Production wiring

- `transfer_acs_inputs` now calibrates decoded QRF predictions at the common
  banked/non-banked seam before null-only recipient filling.
- Activation is a default-empty exact `(entity, target)` selector, following
  pkg3's scoped-binding pattern. It fails closed outside both the caller's
  requested transfer surface and the frozen pkg1 policy.
- The stacked early and late owners pass only their active assigned keys and
  bind source-aware recipient scopes plus the exact frozen reference rows.
  Unassigned siblings in the same QRF family never enter a calibration kernel.
- Schedule-D reconciliation consumes transient source-neutral clone-0 roles in
  `_complete_schedule_d_input`, removes the marker, byte-preserves the
  long-term parent, and uses exact-equal-weight swaps for the mutable
  `non_sch_d_capital_gains` parent before deriving the leaf.
- The Schedule-D operator contract and kernel receipt explicitly disclose both
  the mutable parent and derived leaf. Its role-authority SHA covers the final
  role counts. Independent review confirmed this derive-only declaration does
  not enter any early or late ACS transfer surface.

## Load-bearing regression

The fixture wiring test places assigned `qualified_dividend_income` beside
unassigned `taxable_interest_income` in the same `puf_tax_itemization` batch and
records the production-imported magnitude kernel:

- default selection: zero calibration calls;
- assigned selection: calls only with the assigned target/reference;
- unassigned sibling: bit-equal raw output and no reconciliation receipt;
- attempted unassigned selection: rejected before fitting.

The stacked mixed-family regression independently verifies that the production
owner passes only the assigned tuple and emits a receipt only for that target.
The Schedule-D regressions prove real invocation, role consumption/removal,
parent preservation, and legacy no-op behavior without the transient marker.

Independent scope and call-flow audits found all 20 targets reachable (7 in
early gap-fill and 13 in late bounded groups) with no leakage to unassigned
siblings, including within suffixed mixed batches. The retiring explicit
`--legacy-two-spine` compatibility path remains byte-stable and outside this
default stacked remedy.

## Verification

- Four load-bearing assigned/unassigned and Schedule-D wiring fixtures: pass.
- Complete ACS transfer module: 73 tests pass.
- Touched runtime modules: 1,020 tests pass.
- Complete repository at implementation HEAD (`d9a38965`): 6,551 passed, 74
  skipped (6,625 collected), with 1,890 established warnings and pytest's
  `lastfailed` cache `{}`. The run reached 100% and exited 0 in 53:11.
- Full `ruff check .`: pass.
- `uv lock --check`: pass.
- Ruff format check on all 13 changed Python files: pass.
- `git diff --check`: pass.

An earlier full-suite verification was wrapped in macOS `/usr/bin/time -l` to
seek an RSS receipt. After pytest completed, that wrapper returned 1 because
its own `sysctl kern.clockrate` probe is forbidden by the sandbox; `time -l
true` reproduces the same wrapper-only failure. The fresh 6,625-test
verification above ran pytest directly and exited zero. No local build was
launched. The repository-wide format audit also lists 49 pre-existing
unrelated files; they were not changed.

## Commits

- `56fd9bf6` — add sign-aware calibration primitives.
- `974f36c3` — bound exact QRF leaf storage.
- `209eae98` — journal ACS calibration wiring continuation.
- `e16b8b50` — support exact capped ragged QRF leaves.
- `51054801` — wire scoped ACS transfer calibration.

## Host handoff

Run the frozen 1% build for this branch, compare it against the existing
`origin/main` 1% baseline, and diff the assigned failure set. Unlike the prior
identical 127-line result, the build now traverses the calibrated production
seam; the committed fixture makes a green test run impossible if that assigned
invocation is removed or leaks to an unassigned target.
