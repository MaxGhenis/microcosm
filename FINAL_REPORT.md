# Final report: pkg1 ACS calibration wiring

## Outcome

Completed the wiring continuation on `battery-pkg1-puf-tax`. The production
implementation at `51054801` imports and invokes the PUF-tax calibration
kernels from the default stacked ACS transfer path for exactly the assigned 20
targets (15 carrier checks and 23 conditional-amount checks, representing all
38 PUF-tax work-package rows). The preservation-specific Schedule-D parent
kernel executes later in the mandatory default-stacked derive path, before the
deterministic Schedule-D leaf is produced.

Fresh source tracing plus three independent reviews found no missing production
caller or unassigned-target leak in the current tree. The canonical transfer
surfaces partition the frozen policy into 7 early and 13 late targets, with
zero overlap and zero omission. The earlier identical 127-line host comparison
therefore describes the pre-wiring tree; the current default-stacked path now
contains the production call. No comparator band, incidence threshold, QED
ceiling, quantile, seed, fold, or comparator changed. No continuation 1% build
ran; the host retains that frozen comparison.

## Production wiring

- `transfer_acs_inputs` exposes a default-empty exact `(entity, target)`
  selector. It validates requested keys against both the active transfer
  surface and `PUF_TAX_TRANSFER_CALIBRATION_POLICY`, then intersects them with
  actually incomplete targets.
- Banked and in-memory QRF paths converge on the same seam: decode raw draws,
  calibrate copies for selected targets only, then perform the existing
  null-only recipient fill. Raw chain priors, bank checkpoints, native cells,
  zero-weight draws, and unassigned siblings remain unchanged.
- The stacked early and late owners derive exact active selections and bind
  caller-owned opaque recipient scopes plus target-specific frozen references.
  Family names and bounded-batch suffixes never grant calibration authority.
- The default CLI reaches early gap fill, the bounded late-producer DAG, and
  then `prepare_stacked_tail_derivation` followed by
  `derive_multispine_pool_inputs`. Late transfer groups deliberately suppress
  ACS-local Schedule-D derivation.
- The derive chain runs `_complete_schedule_d_input` first. It consumes the
  transient ASEC-clone-0 reference and ACS-clone-0 recipient roles, invokes
  `reconcile_schedule_d_joint_parents`, removes the role marker, preserves the
  long-term parent byte-for-byte and the weighted direct-parent distribution,
  then derives `schedule_d_capital_gain_distributions`.
- The retiring explicit `--legacy-two-spine` compatibility route remains
  outside this default-stacked remedy.

## Load-bearing regressions

The fixture-scale ACS wiring regression places assigned
`qualified_dividend_income` beside unassigned `taxable_interest_income` in the
same `puf_tax_itemization` batch and records calls to the imported magnitude
kernel. It proves:

- default selection makes zero calibration calls;
- assigned selection invokes the real kernel with the assigned reference;
- the unassigned sibling remains bit-equal to its raw baseline and receives no
  reconciliation receipt; and
- attempting to select the unassigned target fails before fitting.

The stacked-owner fixture separately captures the production call and proves
that only the assigned tuple is passed. Schedule-D role-producer and
kernel-consumer fixtures prove clone-0 role scope, role consumption/removal,
parent preservation, target incidence, and the marker-absent compatibility
no-op.

This continuation added one further tool-level regression: tail preparation
returns a distinct frame carrying the transient Schedule-D role, and every
derive call—cold or resumed—must receive that exact most-recently prepared
frame before consuming the marker. A regression from
`derive_multispine_pool_inputs(derivation_input)` to the unprepared `current`
frame can no longer remain green.

## Verification

- Fresh four-test replay of the load-bearing assigned/unassigned,
  production-owner, and Schedule-D fixtures: 4 passed in 8.77 seconds. The
  committed resource profile for this unchanged set peaked at 608,157,696
  bytes RSS.
- Fresh complete ACS transfer, calibration-kernel, and Schedule-D-kernel
  replay: 110 passed in 237.03 seconds. The committed resource profile for this
  unchanged set peaked at 600,834,048 bytes RSS.
- Complete multispine tool module after handoff hardening: 155 tests pass; peak
  RSS 1,333,870,592 bytes.
- Exact 263-file test manifest
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`:
  6,549 passed, 74 skipped, and 2 explicitly deselected cache-only nodes. Every
  file exited zero in a fresh process with fit/BLAS widths pinned to one and a
  14 GiB live guard. The maximum accepted peak was 11,844,042,752 bytes RSS in
  `packages/microcosm-data/tests/test_loader.py`, below 15 GiB.
- The two deselections were the vehicle-support and voluntary-filing checks
  that each parse the locally mounted 3.73 GB SIPP donor. Prior guarded runs
  established that these environment-conditional nodes cannot complete inside
  this lane's memory ceiling; all other tests in both files passed. No accepted
  process reached the guard.
- Full `ruff check .`: pass.
- Explicitly unfrozen `uv lock --check`: pass.
- Ruff formatting for all 17 branch-changed Python files: pass.
- `git diff --check`: pass.
- Pytest `lastfailed` cache: `{}`.

Runtime, dependencies, and lock are unchanged after implementation commit
`51054801`; the only later Python change is the 21-line Schedule-D handoff
regression in `test_us_multispine_pool_tool.py`. The user-provided
`_WIRING-CONTINUATION.md` remains untracked and untouched.

## Key commits

- `56fd9bf6` — add sign-aware calibration primitives.
- `974f36c3` — bound exact QRF leaf storage.
- `e16b8b50` — support exact capped ragged QRF leaves.
- `51054801` — wire scoped ACS transfer calibration.
- `7298590f` — pin the Schedule-D prepare-to-derive handoff.
- `86f9dfcd` — support repeated cold/resumed handoffs in that fixture.
- `afbc80aa` — record the guarded full-suite replay.
- `0b78c148` — reopen and bind the current host continuation.
- `43bf500f` — record the fresh scoped wiring verification checkpoint.

## Host handoff

Run the frozen 1% build for this branch with the default stacked pipeline,
compare it against the existing `origin/main` 1% baseline, and diff the
assigned failure set. Do not pass `--legacy-two-spine`. Unlike the earlier
identical 127-line comparison, the default build now traverses the calibrated
production seam, and the committed regressions make missing assigned
invocation, unassigned batch leakage, or loss of the Schedule-D prepared-frame
handoff fail in the fixture suite.
