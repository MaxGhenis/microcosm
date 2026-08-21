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

The final continuation audit independently re-read pkg3's named `22b2c6bc`
scoped-binding regression and its production successors, then traced the live
default build route. It found no missing caller or runtime scope leak. The
canonical policy is reachable as 7 early and 13 late targets with no overlap or
omission; family suffixing cannot broaden the stable `(entity, target)` keys.

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
- Current replay of the complete ACS transfer, calibration-kernel, and
  Schedule-D-kernel modules: 110 tests pass with fit/BLAS widths pinned to one.
- Complete ACS transfer module: 73 tests pass.
- Touched runtime modules: 1,020 tests pass.
- Fresh default repository collection: 6,623 tests reached 100% and exited zero
  in 4,210.702 seconds; pytest's `lastfailed` cache is `{}`.
- Memory-isolated explicit-file replay: all 263 test files covered under the
  manifest digest
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`,
  with 6,549 passed, 74 skipped, and two optional mounted-donor nodes
  deselected. The highest accepted peak was 11,841,650,688 bytes RSS, below 15
  GiB.
- Full `ruff check .`: pass.
- Explicitly unfrozen `uv lock --check`: pass.
- Ruff format check on all 13 changed Python files: pass.
- `git diff --check`: pass.

No runtime or test file changed after `51054801`; the later commits are journal
and verification updates. The committed full-suite and memory-isolated replay
therefore exercise the same implementation tree revalidated by the current
focused runs.

The fresh monolithic full-suite process peaked at 27,285,979,136 bytes, so its
green result is not claimed as memory-compliant. A guarded replay therefore
used fresh processes. Two cache-conditional tests attempted to parse the
locally mounted 3.73 GB SIPP donor and crossed conservative live guards at
15,066,742,784 and 13,073,645,568 bytes; they were terminated below the hard 15
GiB ceiling and explicitly deselected from the accepted replay. Those tests
normally skip when the restricted donor is absent, and both had already passed
in the green monolithic run. No local build or 1% comparison was launched. The
repository-wide format audit also lists 49 pre-existing unrelated files; they
were not changed.

## Commits

- `56fd9bf6` — add sign-aware calibration primitives.
- `974f36c3` — bound exact QRF leaf storage.
- `209eae98` — journal ACS calibration wiring continuation.
- `e16b8b50` — support exact capped ragged QRF leaves.
- `51054801` — wire scoped ACS transfer calibration.
- `a1b31586` — reopen the final wiring continuation audit.
- `0dfa2cf7` — record the independent wiring audit.

## Host handoff

Run the frozen 1% build for this branch, compare it against the existing
`origin/main` 1% baseline, and diff the assigned failure set. Unlike the prior
identical 127-line result, the build now traverses the calibrated production
seam; the committed fixture makes a green test run impossible if that assigned
invocation is removed or leaks to an unassigned target.
