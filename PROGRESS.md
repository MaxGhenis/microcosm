# Battery package 1 progress

## State

The 2026-08-25 frame-concentration follow-up is open. The fresh serial-host
1% run passed the prior tail-guard failure and now stops earlier while
validating the sealed tail manifest: the recorded frame-concentration share
for `long_term_capital_gains_on_collectibles` is outside `[0, 1]`. The immediate
read-only, no-build replay is complete. It reproduced the offending pre-stage
share as `1.0000000000000002`: the descending-order numerator is
`7754874867.9770155`, while the frame-order denominator over the identical 19
positive carriers is `7754874867.9770136`. The signed-component audit establishes
that both the stage comparator and shared battery already use weighted absolute
mass, so cancellation is impossible; collectibles is source-enforced
nonnegative. The constructionally bounded top/remainder reduction is now shared
by every concentration surface and pinned to the fresh checkpoint. A corrected
no-build replay validates with pre-stage share exactly `1.0`, and the complete
263-file admissible test manifest is green (6,568 passed/74 skipped; two known
full-donor probes deselected under the memory ceiling). Implementation commit
`f1ad8128` contains the fix, regression, replay evidence, and journals;
`FINAL_REPORT.md` is refreshed for failure #3. Only serial host handoff remains.
Thresholds, bands, gates, seeds, and folds remain frozen; clamping is forbidden.
No pool build or push is authorized, and all processes must remain below
15 GiB RSS. Existing unrelated untracked helper/continuation files remain
untouched.

The preceding 2026-08-21 capital-gains tail-guard continuation is complete
locally.
Implementation commit `8422cb15` contains the verified mechanism and guard
fixes. `FINAL_REPORT.md` carries the exact replay, verification, and handoff
evidence; only the serial host queue's prohibited-in-lane 1% rerun remains.
The pre-fix guarded checkpoint replay measured a real
`non_sch_d_capital_gains` increase from `0.84607664843916197` to
`0.84611424753688269` (delta `3.7599097720719676e-05`, versus the unchanged
`1e-9` noise tolerance). The corrected transfer now matches the donor and
recipient direct-vs-Schedule-D reporting route and replaces modeled ST+LT tail
recipients before seeded ties
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2011-2064`).
A second no-build replay of the same authenticated
checkpoint inputs measured pre and post both as `0.84607664843916197`, with
exact delta `0`; the guard reports
`pre_existing_over_threshold_not_worsened` and does not fail. Numeric gate and
comparator controls, AGI bands, seeds, and folds remain frozen. No host build
has run in this lane.
All accepted replay/test receipts remain below 15 GiB RSS; one rejected attempt
to run a mounted 3.73 GB SIPP cache probe jumped through its conservative cutoff
before the monitor could terminate it, and is disclosed below. The existing
unrelated untracked helper/continuation files remain untouched.

## Done

- Replayed the fresh `f80593d...` assembled and primary-QRF checkpoints without
  a build, fit, or write. The pre-stage collectibles numerator
  `7754874867.9770155` (`0x1.ce39fff3fa1dbp+32`) divided by denominator
  `7754874867.9770136` (`0x1.ce39fff3fa1d9p+32`) produces
  `1.0000000000000002` (`0x1.0000000000001p+0`); post is valid at
  `0.99956427491666788`. The replay authenticated all 65 target banks, left a
  123-input fingerprint unchanged, and peaked at 3,108,896,768 bytes RSS.
- Established the mechanism: all 19 pre-stage collectibles carriers and their
  weights are positive, and the numerator/denominator contain the identical
  weighted magnitudes but sum them in descending/frame order respectively.
  This is floating reduction order, not signed-sum cancellation or an upstream
  negative total. The full method and identities are in
  `experiments/578_puf_collectibles_concentration_replay.md`.
- Audited the complete concentration implementation. Raw frame receipts, the
  shared battery gate, and tail distribution receipts all define concentration
  over weighted absolute mass; all three independently reduce the top subset
  and full set, so all three require the same top/remainder construction. The
  six measured frame components include genuine signed legs; pooled magnitude
  concentration differs from the battery's per-leg comparison but is compatible
  with its no-cancellation treatment.
- Added one shared nonnegative-mass top-share reduction. It partitions carriers
  into disjoint top and remainder sets and constructs total mass as
  `top_mass + remainder_mass`, which makes the subset bound structural without
  a clamp or tolerance. Raw frame receipts, the shared tail gate, and tail
  distribution receipts all use it
  (`packages/microcosm-build/src/microcosm/build/gates.py:2595-2603`,
  `packages/microcosm-build/src/microcosm/build/gates.py:2650-2689`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:641-649`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2724-2726`).
- Added a bit-exact regression containing all 19 fresh-checkpoint values and
  weights. It proves the legacy numerator/denominator/share hex values, requires
  exact `1.0` for all six validated components, exercises mixed-sign raw,
  shared-gate, and distribution paths, and passes the sealed receipt validator
  (`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:1489-1616`).
- Replayed the full corrected tail against the same authenticated checkpoint
  without a build. Pre-stage collectibles now has bit-identical top and total
  mass `7754874867.9770136` and exact share `1.0`; post is valid at
  `0.99956427491666811`. The manifest validator passed with digest
  `ad5432d3a7c614419fba8aa442ef156d5441c1e1173f2b68036f63767a818e49`.
  The 121-file checkpoint fingerprint was unchanged; peak RSS was
  2,587,181,056 bytes.
- Ran the complete 263-file tracked test manifest in fresh guarded processes:
  6,568 passed, 74 skipped, zero failures/errors. Manifest SHA-256 is
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`;
  receipt SHA-256 is
  `e0cfce598cac7b5d5d8fcd64c7f11d4958e8877f3463c3292ced49bc85398287`.
  Maximum root RSS was 11,850,612,736 bytes in the data loader. The only
  deselections were the two previously documented full-donor cache probes that
  cannot run below the lane's memory ceiling; every other test in their files
  passed.
- Tracked-file Ruff, Ruff formatting over the three changed Python files,
  `uv lock --check`, and `git diff --check` all pass. Three independent reviews
  found no blocking issue; one also passed randomized size/range partition
  properties and verified every fixture float bit-for-bit against f80593d.
- Wrote the complete failure-3 outcome, exact reproduction, sign adjudication,
  code-cited correction, fixed replay, verification receipts, and serial-host
  handoff to `FINAL_REPORT.md`.
- Re-read `CLAUDE.md` and the complete GitNexus debugging workflow; inspected
  the current branch, historical journals, output file, and unrelated untracked
  files. Reopened `PROGRESS.md` and `_LANE-NOTES.md` for host failure #3 before
  any production or test edit.
- Re-read `CLAUDE.md` and the complete GitNexus debugging workflow, inspected
  the live branch and worktree, and identified `FINAL_REPORT.md` as the existing
  output file. GitNexus graph endpoints are unavailable in this session, so
  direct source/call-site tracing is the documented fallback.
- Preserved the existing historical journals and unrelated untracked files;
  reopened `PROGRESS.md` and `_LANE-NOTES.md` for the current host failure before
  any production or test edit.
- Established a fresh unchanged-code baseline with the requested per-package
  commands: frame 294 passed/36 skipped, fit 125 passed, calibrate 201 passed,
  data 275 passed/1 skipped, and build 5,656 passed/37 skipped (6,551 passed and
  74 skipped total). Fit/BLAS widths were pinned to one; no host build ran.
- Ruff passed over every tracked Python file. Plain `ruff check .` sees one
  import-order violation only in pre-existing untracked
  `._pkg1_full_suite.py`; that unrelated helper remains untouched and outside
  the commit.
- Replayed the supplied assembled checkpoint without a build and printed full
  IEEE-754 values: pre `0.84607664843916197`, post
  `0.84611424753688269`, delta `3.7599097720719676e-05`. The 14 GiB guard
  recorded 3,373,678,592 bytes peak root RSS; all checkpoint and source-input
  size/mtime fingerprints were unchanged.
- Independently authenticated the primary-QRF and donor inputs: all 15,228
  selected q99.5-tail donors have zero `non_sch_d_capital_gains`; the recipient
  bank has 805 positive and 22,374 zero draws. The committed adjudication is
  `experiments/578_puf_capital_gains_tail_guard_replay.md`.
- Corrected the generating assignment mechanism without changing its filing-
  status or nearest-AGI-band doctrine: recipient candidates now carry tax-unit-
  aggregate modeled capital-gains values and a direct-route identity; support
  and assignment are route-specific; compatible recipients are ordered by
  modeled ST+LT tail magnitude before seeded/source-ID ties
  (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1791-1827`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1891-2008`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2011-2064`).
- Made the guard receipt explicit and derivable: it records full-precision pre,
  post, delta, top-k, unchanged threshold/tolerance/minimum-carrier controls,
  raw pre/post threshold flags, production-gate eligibility, and attribution.
  It fails only when the raw increase exceeds `1e-9`, the raw post share is
  over `0.75`, and the post measurement meets the unchanged 500-carrier floor.
  An unchanged pre-existing exceedance is a non-failing report entry, while a
  thin raw exceedance is reported separately instead of called within-threshold
  (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:610-820`).
- Added separate load-bearing regressions for equal shares, a sub-tolerance
  increase, a material increase, and an unchanged pre-existing exceedance, plus
  reporting-route preservation and modeled-tail recipient ordering
  (`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:641-811`,
  `packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:1191-1391`).
- Replayed the corrected transfer from the same checkpointed inputs without
  fitting, checkpoint writes, or a build. Pre and post are bit-identical at
  `0.84607664843916197` (`0x1.b130f55de9360p-1`), delta is exactly zero, all
  stage-attributable failures are absent, the checkpoint tree is unchanged,
  and peak root RSS was 3,313,057,792 bytes.
- Closed the independent review's coverage findings: tax-unit aggregation is
  load-bearing with a multi-person route/order fixture, route insufficiency is
  tested when status-total capacity is deceptively adequate, public transfer
  pass/fail behavior is bound to exact messages and persisted manifest reports,
  and schema-v3 validation derives every verdict from measured shares/carriers
  and rejects a rehashed altered report
  (`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:657-811`,
  `packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:838-897`,
  `packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:1191-1442`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:76-83`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1030-1036`,
  `packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1488-1636`).
- Advanced the legacy semantic checkpoint identity with the shared tail
  implementation: the common identity binds tail manifest schema 3/support
  contract 2, while the legacy projection removes only the stacked late-
  producer schedule (`tools/build_us_multispine_pool.py:958-1002`). This is
  required because the stacked and legacy routes execute the shared imputation
  and current tail transfer
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:10492-10500`,
  `tools/build_us_multispine_pool.py:2388-2407`,
  `tools/build_us_multispine_pool.py:3844-3897`). The outer schema-4/
  materializer-3 envelope remains. A mocked-build fixture keeps its pool bytes
  stable while its manifest golden advances to bind the current semantic key;
  real tail-affected legacy data may intentionally change under the shared fix.
- Final-tree package receipts: frame 294 passed/36 skipped at 6,527,254,528
  bytes peak RSS; fit 125 passed at 417,792,000 bytes; calibrate 201 passed at
  466,321,408 bytes; data 275 passed/1 skipped at 12,270,026,752 bytes. The
  earlier build directory's cumulative process reached 77% without a test
  failure, then the conservative 14 GiB guard stopped it at 15,554,838,528
  bytes before the binding 15 GiB ceiling.
- The final fresh-process build sweep ran all 226 tracked build test files:
  5,672 passed, 37 skipped, zero failures/errors, and exactly two explicit
  cache-probe deselections. Maximum accepted RSS was 7,022,198,784 bytes. The
  manifest SHA-256 is
  `855d762df4e85fd40df7ff299d444ec5f13d43111d25d731bee1bef73cef79d6`;
  the receipt SHA-256 is
  `67b18e5af01d1ed68134911a0f02449a7dedc8c316fa3da6f16b6a62b53afc22`.
  Combined with the other four package shards, final accepted results are 6,567
  passed, 74 skipped, zero failures/errors, and the same two deselections.
- The deselections are
  `test_cached_full_donor_matches_pinned_household_support` and
  `test_cached_full_donor_matches_locked_response_and_weight_facts`. A guarded
  attempt to run the first probe alone used a 14.875 GiB cutoff, but its next
  sampled allocation was already 17,501,945,856 bytes; the monitor terminated
  it before completion. The second was not attempted. Both parse the same
  mounted 3.73 GB SIPP source; neither is accepted suite evidence.
- Ruff passed over every tracked Python file, and `git diff --check` passed.
  Plain `ruff check .` would additionally scan the preserved untracked helper
  `._pkg1_full_suite.py`, whose pre-existing import-order finding remains outside
  this commit.
- Committed the verified implementation, regressions, replay adjudication, and
  journals as `8422cb15`, then replaced `FINAL_REPORT.md` with the exact
  checkpoint evidence, final suite receipts, memory disclosure, and host
  handoff.

- Re-read `CLAUDE.md`, the continuation brief, and the complete GitNexus
  debugging workflow; inspected the live worktree and branch history; and
  identified `FINAL_REPORT.md` as the requested output file. GitNexus graph
  endpoints are unavailable in this session, so named-commit and direct-source
  call tracing are the active fallback.
- Reopened and committed this live state journal before any production or test
  change, preserving the user-owned untracked continuation brief.
- Re-read pkg3 regression `22b2c6bc` and implementation `176c60fc`. Their
  applicable pattern is a default-empty exact-key selector, validation against
  the requested surface, owner-side intersection, and selected-only execution
  and evidence even when unassigned siblings share a bounded QRF batch.
- Confirmed the causal history boundary: `e16b8b50` has no calibration import,
  selector, or Schedule-D parent call; `51054801` adds all three. Current
  production-source blobs are unchanged from the latter commit.
- Traced `transfer_acs_inputs`: the explicit selector defaults empty, is checked
  against both the requested surface and the frozen PUF-tax policy, intersects
  the actually missing targets, and passes only that exact subset to the
  calibration kernel after prediction decode and before null-only fill.
- Mechanically evaluated the live canonical surfaces. The 20-target policy
  partitions into exactly 7 early-gap-fill and 13 late-DAG targets, with zero
  overlap and zero omission. Each production owner constructs target-specific
  reference authority and passes its exact active selection; other transferred
  targets remain outside the kernel.
- Traced the default CLI into `build_stacked_pool`, early gap fill, every bounded
  late-transfer producer, tail-role preparation, and pool derivation. Only the
  explicit `--legacy-two-spine` branch bypasses this route. Schedule-D assigns
  ASEC clone 0 as reference and ACS clone 0 as recipient, then invokes
  `reconcile_schedule_d_joint_parents` before deterministic leaf derivation.
- Ran five load-bearing fixtures with fit/BLAS widths pinned to one and pytest's
  cache disabled. Assigned primitive invocation, same-batch unassigned
  exclusion, early and late production reference binding, Schedule-D role
  production, and parent-kernel consumption all passed in 6.91 test seconds.
- Three independent read-only audits found no assigned-scope omission,
  unassigned-target leakage, or default-path bypass. One audit replaced the
  production calibration seam with a no-op at runtime; the direct call-recording
  regression failed at its required nonempty-call assertion, proving the test
  cannot remain green when the kernel is unwired.
- Confirmed checkpoint routing is versioned for this calibration/Schedule-D
  materializer: pre-wiring identities cannot resume, transferred resumes rerun
  tail preparation and derivation, and simulated resumes authenticate an
  already-derived frame and receipts.
- Recorded but did not expand scope for one pre-existing non-default API
  inconsistency: a custom partial transfer's Schedule-D execution identity is
  enabled when either parent is requested while its expectation helper names
  both. The default stacked path transfers both parents before the separately
  scoped parent reconciler, so this is not a bypass of the requested wiring.
- Replayed the complete relevant modules in fresh processes with fit/BLAS
  widths pinned to one, pytest's cache disabled, and a 14 GiB live root-RSS
  guard: 73 ACS-transfer, 18 calibration-primitive, and 19 Schedule-D tests all
  passed (110 total). Maximum monitored root RSS was 600,260,608 bytes.
- The first aggregate monitor attempted process-tree enumeration, which macOS
  sandboxing forbids; it produced no accepted receipt. The accepted replays
  monitor the direct pytest process used by the prior lane convention and ran
  each module independently, with no guard event.

- Re-read `CLAUDE.md` and the complete GitNexus exploration workflow, inspected
  the current branch/worktree, and preserved the user-owned untracked
  continuation brief. GitNexus graph resources are unavailable in this
  session, so direct source and named-commit tracing are the active fallback.
- Reopened and committed this current-state journal before any production or
  test edit, per the standing order.
- Located pkg3's named regression at `22b2c6bc` and implementation at
  `176c60fc`. Current pkg1 follows the same default-empty exact-key pattern:
  validate against the requested surface and frozen owner policy, intersect by
  active family, execute only selected targets, and attach evidence only there.
- Traced the default CLI into `build_stacked_pool`, then through early gap fill
  and all late-transfer groups to the common post-decode/pre-fill calibration
  seam. The frozen registry is exactly 20 targets / 15 carrier legs / 23 amount
  legs; its live owner surfaces partition 7 early and 13 late with zero overlap,
  omission, or selected unassigned target. The direct empty-default transfer in
  `_impute_pool` is reachable only behind explicit `--legacy-two-spine`.
- Traced Schedule-D from `prepare_stacked_tail_derivation` into the exact
  prepared frame consumed by `derive_multispine_pool_inputs`, where the
  preservation-specific equal-weight-swap reconciler runs before deterministic
  leaf derivation. This is the Schedule-D kernel selected in the original
  design notes; the generic four-state helper is not the production remedy.
- Audited the committed fixture regressions. The direct same-batch test records
  the imported magnitude primitive, proves default/unassigned non-invocation,
  proves assigned invocation, preserves the unassigned raw-transfer output,
  and rejects an unassigned selector. Separate early and late owner fixtures
  fail if their exact production bindings are removed. Schedule-D role,
  prepared-frame handoff, kernel effect, and checkpoint-resume fixtures fail if
  that path is unwired.
- Three independent read-only reviews found no blocking default-path defect.
  One review replayed nine expanded load-bearing cases successfully. A separate
  replay of the four slow tool-entrypoint cases passed in 342.35 seconds.
- Replayed all 110 tests across ACS transfer, its calibration primitives, and
  the preservation-specific Schedule-D kernel with fit/BLAS widths pinned to
  one, pytest cache disabled, and a 14 GiB live RSS guard. All 110 passed in
  21.04 test seconds; maximum root RSS was 600,440,832 bytes.
- Replayed the exact 263-file tracked manifest (SHA-256
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`)
  in fresh interpreters under the same width constraints and a 14 GiB live
  root-RSS guard. Results were 6,549 passed, 74 skipped, zero failures, zero
  errors, and exactly two explicit full-donor cache-probe deselections; no
  guard event occurred.
- Maximum full-suite RSS was 11,843,141,632 bytes in
  `packages/microcosm-data/tests/test_loader.py`, below both the 14 GiB guard
  and 15 GiB order. The 263 JUnit receipts are in
  `/private/tmp/pkg1-suite-current-retry-42c471aa`; their ordered aggregate
  SHA-256 is
  `7a60dc30fffb02c54030f405f7158ef377e06e0c19f90c706659fed72eb8c6cb`.
- The two deselections were
  `test_cached_full_donor_matches_pinned_household_support` and
  `test_cached_full_donor_matches_locked_response_and_weight_facts`; each
  independently loads the mounted 3.73 GB SIPP donor and cannot run inside the
  lane ceiling. Every other test in both files passed. A platform-only
  PostgreSQL module recorded its ordinary collection skip because `pgserver`
  is not installed.
- Ran `ruff check .`, Ruff formatting checks on all 17 branch-changed Python
  files, an explicitly unfrozen `uv lock --check`, `git diff --check`, and the
  pytest `lastfailed` audit. All passed; the last-failed cache is `{}`.
- Compared the live frozen comparator declaration and its complete gate suffix
  directly with `origin/main`. Incidence bounds `(0.8, 1.25)`, conditional
  quantiles `(0.10, 0.25, 0.50, 0.75, 0.90)`, both `0.25` tolerances, the
  Schedule-D sign-separated metric, sample/clone seed `578`, and pool seed `0`
  are unchanged. No relevant fold, band, threshold, dependency, or lock change
  was introduced.
- Confirmed all current production-source blobs are byte-identical to wiring
  commit `51054801`. An optional wheel probe could not start because isolated
  building would need network access to fetch `hatchling`, while the sandbox's
  environment does not have that backend installed. No packaging or source
  change was made in this continuation; the requested guarded suite and static
  gates are complete.
- Refreshed and committed `FINAL_REPORT.md` at `504ad593` with the causal
  host-tested/current-tree distinction, exact assigned scope, load-bearing
  regression proof, current guarded-suite receipts, frozen-gate comparison,
  and host-only 1% instructions.

- Re-read `CLAUDE.md` and the complete GitNexus exploration workflow, inspected
  the worktree and branch history, and preserved the user-owned untracked
  continuation brief. GitNexus graph resources are unavailable in this
  session, so direct source and named-commit tracing are the active fallback.
- Located pkg3's named scoped-binding regression at `22b2c6bc` and the existing
  candidate pkg1 production wiring at `51054801`; neither historical journal
  claims nor prior receipts are being treated as current evidence.
- Re-read pkg3 implementation `176c60fc` and regression `22b2c6bc`. The current
  wiring follows their default-empty exact-key selector, request validation,
  per-family active intersection, selected-only execution, and selected-only
  evidence pattern.
- Traced the default stacked CLI through both early gap fill and all bounded
  late-transfer groups into the common post-decode/pre-fill calibration seam.
  The frozen 20-target policy partitions into exactly 7 early and 13 late
  targets (17 person and 3 tax-unit), with no overlap, omission, or selected
  unassigned target. The explicit legacy route retains the empty default.
- Traced the Schedule-D parent separately from tail-role preparation to
  `_complete_schedule_d_input`, where the preservation-specific reconciler is
  invoked for ASEC-clone-0 reference and ACS-clone-0 recipient roles before
  deterministic leaf derivation.
- Completed three independent read-only reviews of the pkg3 precedent,
  production call graph, target inventory, and regression landscape. All found
  no current call-path or scope defect.
- Replayed the three load-bearing fixtures for primitive invocation plus
  same-batch unassigned exclusion, exact stacked-owner binding, and Schedule-D
  role consumption. All 3 passed in 8.71 seconds with fit/BLAS widths pinned to
  one and pytest's cache disabled.
- Replayed all 110 tests across the ACS transfer, calibration-kernel, and
  Schedule-D reconciliation modules under the same constrained execution
  widths with pytest's cache disabled. All 110 passed in 14.99 seconds.
- Replayed the exact 263-file tracked manifest (SHA-256
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`)
  in fresh per-file interpreters with fit/BLAS widths pinned to one, pytest's
  cache disabled, and a 14 GiB live RSS guard. Results were 6,549 passed,
  74 skipped, zero failures, zero errors, and exactly 2 documented cache-probe
  deselections; no guard fired.
- The two explicit deselections were
  `test_cached_full_donor_matches_pinned_household_support` and
  `test_cached_full_donor_matches_locked_response_and_weight_facts`, each of
  which independently parses the mounted 3.73 GB SIPP donor and cannot run
  inside this lane's ceiling. Every other test in both files passed.
- Maximum accepted root RSS was 11,845,517,312 bytes in
  `packages/microcosm-data/tests/test_loader.py`, below both the 14 GiB guard
  and 15 GiB charter ceiling. The fresh TSV receipt is
  `/private/tmp/pkg1-wiring-suite-fresh.xtCkap/receipt.tsv`, SHA-256
  `1fb02742e382b0cba3c89567120b581e53b04aa3f4edb12aa2b2f822e63eb410`.
- Ran full Ruff, Ruff formatting checks on all 17 branch-changed Python files,
  an explicitly unfrozen `uv lock --check`, `git diff --check`, and the pytest
  cache audit. All pass; `lastfailed` is `{}`.
- Compared the canonical incidence bounds, conditional quantiles, and both
  comparator tolerances literally with `origin/main`; all frozen battery values
  are unchanged. No seed, fold, comparator, or band edit was made in this
  continuation.
- Rewrote and committed `FINAL_REPORT.md` at `010d546f`, then applied the
  independent report review's two precision corrections at `e5858389`: each
  target invokes only its policy-specified primitive stages, and unassigned
  siblings remain QRF-imputed but receive no calibration adjustment or receipt.

- Re-read `CLAUDE.md` and the complete GitNexus debugging workflow, inspected
  the branch/worktree, and preserved the user-owned untracked continuation
  brief. GitNexus graph endpoints are unavailable in this session, so direct
  source, test, and named-commit tracing will supply the fresh caller evidence.
- Confirmed the host's stated no-caller symptom against the history boundary:
  the current branch advertises candidate wiring in `51054801`, while the
  continuation audit must still prove that the live default build reaches it
  for assigned targets only.
- Re-read pkg3 regression `22b2c6bc` and implementation `176c60fc`. The live
  selector follows the same default-empty exact `(entity, target)`, requested-
  surface validation, active-target intersection, and selected-only execution
  pattern, with an additional fail-closed check against the frozen PUF-tax
  policy.
- Traced the default CLI through early gap fill and every bounded late-transfer
  group to the common post-decode/pre-fill calibration seam. The imported
  primitives are invoked there for both banked and in-memory QRF execution;
  only explicit `--legacy-two-spine` remains outside the remedy.
- Evaluated the live target surfaces mechanically: the 20-target frozen policy
  partitions into 7 early and 13 late targets with zero overlap, omission, or
  extra. Schedule-D separately mints ASEC-clone-0 reference and ACS-clone-0
  recipient roles, then calls the preservation-specific parent reconciler
  before deterministic leaf derivation.
- Completed three independent read-only audits of exact scope, load-bearing
  regressions, and entrypoint/checkpoint routing. All found no blocking defect.
  The host's zero-log observation is not a current execution oracle because
  this seam emits nested reconciliation receipts rather than console lines;
  transferred and simulated resumes intentionally authenticate already-
  processed frames instead of rerunning completed stages.
- Replayed the eight load-bearing test functions (10 parameterized cases) with
  fit/BLAS widths pinned to one, pytest's cache disabled, and a 14 GiB live RSS
  guard. All passed; maximum monitored root RSS was 1,154,236,416 bytes and no
  guard event occurred.
- Replayed all 110 tests in the ACS transfer, calibration-kernel, and
  Schedule-D reconciliation modules under the same controls. They reached
  100%, exited zero, and peaked at 600,391,680 bytes.
- Revalidated the exact 263-file guarded full-suite receipt against the current
  manifest and Git objects. The manifest SHA-256 remains
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`,
  and packages, tools, dependencies, and lock are byte-identical to receipt
  commit `3e93ada6`. Counts remain 6,549 passed, 74 skipped, zero failures,
  zero errors, and two documented mounted-SIPP cache probes deselected; maximum
  accepted RSS was 12,049,039,360 bytes with no guard breach.
- Ran full Ruff, corrected 17-file Ruff formatting check, explicitly unfrozen
  lock freshness, `git diff --check`, and the pytest `lastfailed` audit. All
  pass and `lastfailed` is `{}`. The first formatting invocation placed `-z`
  after the pathspec and treated all paths as one filename; the corrected
  null-delimited invocation passed with all 17 files already formatted.
- Refreshed and committed `FINAL_REPORT.md` at `7fb5d738` with the current
  production trace, checkpoint/logging clarification, three-review verdict,
  fresh guarded replays, bound full-suite receipt, unchanged frozen comparator
  contract, and host-only 1% handoff.

- Read `CLAUDE.md` and the complete GitNexus debugging workflow, inspected the
  branch and worktree, and preserved the user-owned untracked continuation
  brief. GitNexus graph tools are unavailable in this session, so named-commit
  history and direct source tracing will supply the required caller evidence.
- Re-read pkg3 regression `22b2c6bc` and implementation follow-up `176c60fc`.
  The live implementation follows their default-empty, exact-key authority:
  selection is validated against both request and frozen policy, intersected
  with live missing targets, and executed only for that selected subset after
  either QRF decode path and before null-only fill.
- Confirmed the host's no-caller observation against `51054801^`; that tree has
  no calibration import or selection binding. The current tree directly imports
  all three primitives and passes exact selections from both early and late
  production owners.
- Executed the live target inventory. The frozen 20-target policy partitions
  into 7 early and 13 late targets with zero overlap, omission, or extra.
  Source-aware references and opaque recipient scopes remain exact by entity,
  support channel, and clone while the transfer operator remains source-blind.
- Traced the default tool through early gap fill, the bounded late DAG,
  `prepare_stacked_tail_derivation`, and `derive_multispine_pool_inputs`.
  Schedule-D assigns only ASEC clone 0 as reference and ACS clone 0 as recipient,
  invokes `reconcile_schedule_d_joint_parents` before leaf derivation, and drops
  the transient role. The explicit legacy route retains the empty selector.
- Completed three independent read-only audits of the pkg3 precedent,
  production call graph, target inventory, regression load-bearingness, and
  Schedule-D/checkpoint routing. All found no blocking defect.
- Replayed 10 load-bearing cases with fit/BLAS widths pinned to one, pytest's
  cache disabled, and a 14 GiB RSS guard. Assigned invocation, same-batch
  unassigned preservation, early and both late reference owners, Schedule-D
  role production and kernel consumption, three terminal states, and checkpoint
  resume all passed; peak root RSS was 1,064,779,776 bytes with no guard event.
- Replayed all 110 tests in the ACS transfer, calibration-kernel, and Schedule-D
  reconciliation modules under the same guard. They reached 100% and exited
  zero at 601,849,856 bytes peak root RSS.
- Revalidated the committed guarded full-suite receipt against the current
  exact 263-file manifest. Its manifest SHA-256 remains
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`;
  packages, tools, dependencies, and lock have identical Git objects to the
  receipt commit. The result remains 6,549 passed, 74 skipped, zero failures,
  zero errors, 2 documented mounted-SIPP cache probes deselected, and a
  12,049,039,360-byte maximum accepted peak below both 14 and 15 GiB.
- Ran full Ruff, Ruff formatting checks on all 17 branch-changed Python files,
  explicitly unfrozen `uv lock --check`, `git diff --check`, and the pytest
  cache audit. All pass and `lastfailed` is `{}`.
- Refreshed and committed `FINAL_REPORT.md` at `73e9b3fb` with the current
  production trace, three-review verdict, guarded test evidence, unchanged
  frozen comparator contract, and host-only 1% handoff.

- Confirmed the host's zero-caller observation against `51054801^`: that tree
  has no `acs_transfer_calibration` import or `calibration_targets` binding.
  The live tree imports all three primitives and invokes the selected-only
  calibration seam after both decoded QRF modes and before null-only fill.
- Evaluated the live canonical owner surfaces against the frozen policy. All
  20 assigned transfer targets are reachable as 7 early and 13 late targets,
  with zero overlap, omission, or unassigned extra.
- Replayed the eight load-bearing test functions (10 parameterized cases) under
  a 14 GiB root-RSS guard with all fit/BLAS widths pinned to one and pytest's
  cache disabled. Assigned invocation, same-batch unassigned preservation,
  early and both late reference owners, Schedule-D role production and kernel
  consumption, three terminal states, and checkpoint resume all passed; peak
  monitored root RSS was 1,194,409,984 bytes with no guard event.
- Replayed all 110 tests in the ACS transfer, calibration-kernel, and
  Schedule-D reconciliation modules under the same constrained guard. They
  reached 100% and exited zero at 601,669,632 bytes peak root RSS.
- Completed the first independent read-only comparison with pkg3 regression
  `22b2c6bc`, production follow-up `176c60fc`, and its later mixed-family
  hardenings. The live implementation follows the same default-empty exact-key
  authority, per-active-family intersection, and selected-only execution
  pattern; no default-path scope defect was found. The explicit retiring
  `--legacy-two-spine` route intentionally keeps the empty selection.
- Completed two further independent read-only audits of the complete production
  call graph and regression coupling. Both banked and in-memory QRF modes
  converge on the selected-only post-decode seam, bank resumes still traverse
  it, and removing the common call, either owner binding, the prepared
  Schedule-D frame, or the parent reconciler makes a committed fixture fail.
  No blocking implementation or test change remains.
- Traced checkpoint behavior explicitly: cold and assembled routes execute both
  ACS calibration stages plus Schedule-D; transferred resumes authenticate the
  already-calibrated frame and rerun Schedule-D; simulated resumes authenticate
  the persisted post-derive frame. The default CLI selects this stacked route,
  while legacy requires the explicit `--legacy-two-spine` flag.
- Replayed the exact 263-file tracked manifest with SHA-256
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`
  in fresh per-file interpreters under a 14 GiB root-RSS guard. Aggregated JUnit
  counts are 6,549 passed, 74 skipped, zero failures, and zero errors; every
  file has a passing receipt and no guard event occurred. The receipt is
  `/private/tmp/pkg1-wiring-suite-current.lqh0cU/receipt.jsonl` with SHA-256
  `d86159eec7cec6bf7ecf95c05f8ae825397f005d1447896f152796aac1564a96`.
- The only deselections were the two previously documented mounted-SIPP cache
  probes that each parse the 3.73 GB donor and cannot execute within this lane's
  memory ceiling. Every other test in both files passed. Maximum accepted root
  RSS was 12,049,039,360 bytes in
  `packages/microcosm-data/tests/test_loader.py`, below both 14 and 15 GiB.
- Ran full Ruff, Ruff formatting checks on all 17 branch-changed Python files,
  explicitly unfrozen `uv lock --check`, `git diff --check`, and the pytest
  cache audit. All pass and `lastfailed` is `{}`. Runtime is byte-identical to
  wiring commit `51054801`; all Python is byte-identical to guarded evidence
  commit `afbc80aa`.
- Refreshed and committed `FINAL_REPORT.md` at `e91e1655` with the current
  production trace, three-review verdict, fresh guarded-suite receipt, static
  gates, unchanged frozen comparator contract, and host-only 1% handoff.
- Reopened the continuation on 2026-08-21 at `47b22df0`, read `CLAUDE.md` and
  the complete GitNexus exploration workflow, inspected the branch/worktree,
  and preserved the user-owned untracked continuation brief. GitNexus MCP
  graph resources are unavailable in this session, so named-commit and direct
  source tracing will supply the fresh call-edge evidence.
- Replayed 10 parameterized load-bearing cases with all fit/BLAS widths pinned
  to one and pytest's cache disabled. All 10 passed, including three
  terminal-state entrypoint variants and the checkpoint-resume handoff;
  maximum monitored root RSS was 1,146,896,384 bytes.
- Replayed the complete ACS transfer, calibration-kernel, and Schedule-D
  reconciliation modules. All 110 tests reached 100% and exited zero inside
  the exhaustive replay at 602,537,984 bytes maximum monitored root RSS.
- Replayed the exact 263-file tracked manifest with SHA-256
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`.
  Every accepted file ran in a fresh interpreter under a 14 GiB live root-RSS
  guard with constrained execution widths. Aggregated JUnit counts were 6,549
  passed, 74 skipped, zero failures, and zero errors; all 263 files have a
  passing receipt and no accepted guard event occurred.
- The two explicit deselections were
  `test_cached_full_donor_matches_pinned_household_support` and
  `test_cached_full_donor_matches_locked_response_and_weight_facts`. Each
  independently parses the locally mounted 3.73 GB SIPP CSV. A fresh isolated
  attempt of the vehicle node crossed the conservative 14.5 GiB cutoff before
  completing and was terminated; all other tests in both files passed.
- Maximum accepted root RSS was 11,845,337,088 bytes in
  `packages/microcosm-data/tests/test_loader.py`, below both the 14 GiB replay
  guard and 15 GiB charter ceiling. The complete 73-test QRF, 73-test ACS
  transfer, 18-test calibration, 19-test Schedule-D, 72-test multispine pool,
  155-test pool-tool, 231-test stacked-spine, and 495-test source-blindness
  modules all passed inside the replay.
- Ran full Ruff, an explicitly unfrozen `uv lock --check`, Ruff formatting
  checks on all 17 branch-changed Python files, `git diff --check`, and the
  pytest `lastfailed` check. All pass; `lastfailed` is `{}` and no tracked
  working-tree change remains.
- Attempted the GitNexus workflow after `gitnexus status` reported no index.
  The analyzer could not write its sandboxed global registry; the lingering
  process was stopped and its two-file partial local index was moved intact to
  `/private/tmp/microcosm-gitnexus-partial.mf18LA/.gitnexus` before direct
  source/history tracing continued.
- Re-read pkg3's `22b2c6bc` scoped-binding regression, its `176c60fc`
  implementation, and the later mixed-family hardenings. The applicable
  contract is a default-empty exact `(entity, target)` selector, validation
  against the requested surface, per-batch intersection, selected-only
  execution/evidence, and owner-side exact selection.
- Confirmed current implementation commit `51054801` follows that contract:
  `transfer_acs_inputs` validates the selector against both its requested
  surface and the frozen policy, intersects only live missing targets, and
  invokes imported carrier/sign and conditional-magnitude primitives after
  banked or in-memory decoding and before null-only fill.
- Evaluated the live canonical surfaces against the frozen registry: all 20
  assigned targets are reachable as 7 early and 13 late targets, with zero
  overlap, omission, or extra target. Early and bounded late owners bind only
  their exact active keys, including inside mixed suffixed families.
- Traced the default CLI through stacked early gap fill, the bounded late DAG,
  tail preparation, and derive. The Schedule-D parent kernel consumes exact
  ASEC-clone-0 reference and ACS-clone-0 recipient roles before deterministic
  leaf derivation; the prepared frame is passed by identity to derive.
- Independently reviewed the fixture regressions. Removing the imported
  magnitude-kernel call, leaking to a same-family unassigned target, omitting
  the early owner selector, bypassing the prepared Schedule-D frame, skipping
  derive dispatch, or skipping the parent reconciliation makes at least one
  committed fixture fail. One independent focused replay reported 8 passed.
- Kept the explicit retiring `--legacy-two-spine` route outside this default
  remedy. It deliberately passes the selector's empty default; the host must
  use the default stacked path for the frozen comparison.
- Reopened the continuation at `4aaafd4c`, read `CLAUDE.md` and the complete
  GitNexus debugging workflow, inspected the live branch/worktree state, and
  preserved the user-owned untracked continuation brief. GitNexus graph tools
  are unavailable in this session, so local history and direct source tracing
  will provide the fresh call-edge evidence.
- Reopened the continuation at `474d8817`, read `CLAUDE.md` and the complete
  GitNexus debugging workflow, inspected the branch/worktree state, and
  preserved the user-owned untracked continuation brief.
- Confirmed that GitNexus query tools are unavailable in this session; direct
  commit, call-site, and source tracing will provide the required fresh
  evidence.
- Re-read pkg3's named `22b2c6bc` regression and `176c60fc` implementation.
  The applicable pattern is a default-empty exact `(entity, target)` selector,
  validation against the requested surface, owner-side active intersection,
  and selected-only execution/evidence even inside a shared suffixed batch.
- Traced both QRF modes to the common post-decode/pre-fill calibration seam.
  Early gap fill and every bounded late-producer group pass exact active keys;
  the explicit `--legacy-two-spine` compatibility path retains the empty
  selector and is outside the default stacked remedy.
- Evaluated the canonical early and late surfaces against the frozen policy:
  all 20 assigned targets are reachable as 7 early and 13 late targets, with
  no overlap, omission, or extra target.
- Confirmed that the default tool calls `prepare_stacked_tail_derivation`, then
  passes that exact frame to `derive_multispine_pool_inputs`, whose first
  operator invokes the preservation-specific Schedule-D parent kernel before
  deriving the leaf.
- Completed three independent read-only reviews of the pkg3 precedent,
  production transfer path, exact target inventory, invocation regression, and
  Schedule-D route. All found the existing wiring complete and scope-exact.
- Replayed the four core load-bearing fixtures: assigned invocation,
  same-family unassigned non-invocation, production-owner exact selection,
  Schedule-D role consumption/preservation, and marker-absent compatibility.
  All 4 tests passed in 4.96 seconds at 606,699,520 bytes peak RSS.
- Replayed all three terminal variants of the default stacked tool fixture;
  the prepared Schedule-D role frame reached derive in every applicable path.
  All 3 tests passed in 33.93 seconds.
- Replayed the complete ACS transfer, calibration-kernel, and Schedule-D
  reconciliation modules. All 110 tests passed in 6.58 seconds at 601,145,344
  bytes peak RSS.
- Confirmed the tracked test manifest still contains exactly 263 files with
  SHA-256 `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`
  and that source, tests, dependencies, and lock are unchanged from the earlier
  guarded evidence commit `afbc80aa`.
- Replayed every manifest file in a fresh interpreter with all fit and BLAS
  widths pinned to one, pytest's cache disabled, and a 14 GiB live aggregate-
  RSS process-group guard. The accepted result was 6,549 passed, 74 skipped,
  exactly 2 documented cache-only SIPP nodes deselected, zero failures, and no
  guard event. Maximum sampled aggregate RSS was 11,495,079,936 bytes in
  `packages/microcosm-data/tests/test_loader.py`, below both 14 and 15 GiB.
- The two exact deselections remain
  `test_cached_full_donor_matches_pinned_household_support` and
  `test_cached_full_donor_matches_locked_response_and_weight_facts`. Their two
  files' remaining tests passed; both cache probes parse the locally mounted
  3.73 GB SIPP donor and are covered by the earlier green monolithic run whose
  27,285,979,136-byte peak is not accepted as resource-compliant evidence.
- Ran full Ruff, Ruff formatting checks on all 17 branch-changed Python files,
  explicitly unfrozen lock freshness, and `git diff --check`; all pass.
- Refreshed `FINAL_REPORT.md` with the current source audit, load-bearing test
  results, exact guarded-suite totals, resource maximum, and frozen 1% host
  handoff.

- Ran the required `uv sync --all-packages --extra us`. The default cache was
  denied by the managed filesystem; a retry with a writable cache reached
  dependency resolution but outbound DNS blocked the missing `msgpack` wheel.
- Read the complete battery adjudication and all 39 assigned machine-readable
  rows from the read-only `microcosm-arm-split` worktree.
- Read every assigned mechanism citation in `acs_transfer.py` and
  `stacked_spine.py`; the frozen comparator separately measures weighted sign
  incidence and conditional absolute-amount quantiles.
- Confirmed the named remedy must change the transfer artifact, not the frozen
  incidence band, QED ceiling, quantiles, seeds, folds, or comparators.
- Established a green full-suite baseline: 6,509 tests collected and pytest
  exited 0 using the locked `microcosm-arm-split` environment with this
  worktree's five `src` trees on `PYTHONPATH`. The long-running 44% block was
  traced to expected real PolicyEngine-US memory regressions.
- Extracted the exact registry: 20 continuous targets representing 15
  incidence/carrier checks and 23 conditional-amount checks (38 total).
- Added pure array kernels that separate weighted carrier/sign allocation from
  sign-preserving weighted inverse-ECDF amount mapping. Immutable and
  zero-weight rows are preserved; infeasible support and malformed IDs or
  weights fail closed with capacity/error receipts.
- Added a preservation-specific Schedule-D kernel that byte-preserves the
  long-term parent and permits only exact-equal-weight positive/zero swaps.
  This preserves the weighted non-Schedule-D carrier margin and conditional
  value distribution exactly while projecting unattainable joint targets into
  a disclosed feasible interval.
- Corrected conditional magnitude ranks to include immutable native carriers
  in the final-domain denominator and ordering, while leaving their bytes fixed.
- Added 37 focused behavioral test cases across the two kernels; all pass. The
  complete 495-case runtime source-blindness module and Ruff also pass.
- Reran the complete repository suite after both audit-driven corrections;
  pytest reached 100% and exited 0 with only the established warnings/skips.
- Committed the verified primitive layer as `56fd9bf6`.
- Implemented the common banked/non-banked post-decode, pre-fill calibration
  seam for the exact 20-target registry (15 carrier legs and 23 conditional
  amount legs), with immutable native cells and zero-weight raw draws preserved.
- Added a source-aware stacked-spine scope authority that maps every exact
  `(entity, support channel, clone)` identity to a stable opaque ID and passes
  only the aligned neutral IDs into the source-blind transfer operator.
- Integrated Schedule-D parent reconciliation through a transient neutral role
  marker, exact equal-weight swaps, receipt propagation, and the terminal
  remaining-stage manifest.
- Launched a genuine pre-integration 1% control at sample fraction `0.01`,
  sample seed `578`, clone attachment fraction `1.0`, and clone seed `578`, with
  both QRF widths pinned to one and no predecessor logbook digest. Stopped it
  after target 10 when the profiler showed single-target peaks of 63.67, 60.83,
  58.80, and 29.04 GB. The partial output is not an accepted control artifact.
- Traced those peaks to `quantile_forest` padding every tree/node to the one
  global largest leaf and then copying the complete dense tensor. Work is in
  progress on exact multiplicity-preserving ragged storage; a sampling cap was
  rejected because it would change raw draws and every later chain condition.
- Replaced that unlimited-leaf dense tensor with exact ragged bootstrap
  multiplicities. Randomized continuous, repeated, negative, and 1,001-point
  transition grids are bit-identical to the installed dense backend; explicit
  capped models continue to use the installed implementation.
- Verified the complete 46-test QRF module with both execution widths pinned to
  one. A 30,000-row/100-tree stress case projected 170.28 GiB for the inherited
  dense tensor, retained 37.11 MiB in the ragged store, and peaked at 0.371 GiB
  RSS. The atom-heavy stress retained 2.97 MiB and peaked at 0.227 GiB.
- Closed independent-review findings before commit: membership now consumes
  sklearn's public fitted bootstrap indices (including its 1.9 sample-weight
  contract), quantile-forest is exactly pinned to the reviewed 1.4.2 private
  kernel, and a fixed `q=0` reproducer preserves the dense backend's endpoint
  result bit for bit. Private signature and kernel-semantic drift fail closed.
- Reran the expanded 51-test QRF module and the complete repository suite with
  the locked quantile-forest 1.4.2 interpreter and all execution widths pinned
  to one; both reached 100% and exited zero. Full Ruff, targeted format, lock
  freshness, and `git diff --check` also pass.
- Attempted the packaging check required after changing the fit dependency.
  The offline builder cannot resolve uncached `hatchling`, and outbound DNS was
  already unavailable during setup; no wheel was produced and no dependency
  or check was bypassed.
- Committed the unlimited-leaf support boundary as `974f36c3`.
- Started a fresh off-chain 1% pre-remedy control with the exact frozen sample
  and clone seeds, no predecessor logbook digest, and both QRF widths pinned to
  one. The first 41 primary targets succeeded; continuous targets that had
  previously projected 29--64 GB recorded only 1.03--1.28 GB peaks.
- Stopped that run immediately after
  `estate_income_would_be_qualified` recorded a 55,823,466,496-byte peak. Its
  five-value target activates the unchanged 4,096-sample near-discrete cap;
  the ragged subclass still delegated every explicit cap to the inherited
  `(trees, max_nodes, outputs, cap)` dense tensor. The partial build is invalid
  and will not be accepted or resumed.
- Extended exact ragged membership to configured integer and fractional caps,
  preserving quantile-forest 1.4.2's compiled leaf grouping, ascending leaf
  order, per-tree Python RNG seed/shuffle stream, selected bootstrap positions,
  inverse-sorter mapping, and resolved `ceil(fraction * n)` width. The frozen
  4,096 cap, its seed, and all selected occurrences remain unchanged.
- Added dense/ragged bit-equality coverage over capped continuous and repeated
  targets, integer and fractional caps, multiple seeds, both endpoints, the
  production quantile grid, selected counts, projection shapes, and global RNG
  state. A dedicated fixture exercises a 5,200-member leaf under the exact
  production 4,096 cap.
- Verified a 12,000-row, 48-tree, 32-atom capped stress case: the inherited
  dense tensor projects to 21,801,467,904 bytes while the exact ragged payload
  retains 10,623,840 bytes and peaks at 273,088,512 bytes RSS. Independent fuzz
  review found all 160 capped and 100 unlimited comparisons bit-identical.
- Revalidated the carried capped-leaf correction in this worktree: all 73 QRF
  tests pass with execution widths pinned to one; focused Ruff, format, and
  `git diff --check` pass. The complete repository suite remains reserved for
  the final wired state.
- Received the host's paired 1% result: branch and `origin/main` each produced
  the same 127 failure lines, with zero fixed and zero introduced. Direct source
  and log inspection established that `acs_transfer_calibration.py` is never
  called by the ACS transfer build path, so the kernel cannot affect artifacts.
- Began the wiring continuation under the frozen gate: inspect pkg3's scoped ACS
  binding pattern, bind only the assigned PUF-tax rows plus Schedule-D parent,
  and add a fixture regression that fails if assigned invocation disappears or
  leaks to an unassigned target. No local 1% build is authorized for this
  continuation.
- Restored the reviewed post-decode/pre-fill integration for both banked and
  in-memory ACS QRF paths, including opaque source-aware recipient scopes,
  target-specific frozen references, immutable native cells, and external
  reconciliation receipts.
- Mirrored pkg3's scoped-binding pattern with a default-empty explicit
  `(entity, target)` selector. Selection fails closed outside the requested
  surface or the frozen 20-target policy; stacked early and late owners pass
  exactly the currently active assigned keys, including inside suffixed mixed
  batches.
- Added a call-recording regression with assigned `qualified_dividend_income`
  and unassigned `taxable_interest_income` in the same family. With no selector
  the kernel has zero calls; with the assigned selector the imported magnitude
  kernel is called only with the assigned reference, the unassigned output is
  bit-equal to its raw baseline, and an attempted unassigned selector fails
  before fit.
- Wired the Schedule-D parent kernel at the default stacked derive seam (the
  late transfer deliberately suppresses ACS-local Schedule-D derivation).
  Transient clone-0 roles are consumed and removed; the long-term parent bytes
  and weighted direct-parent distribution remain preserved.
- Focused wiring/Schedule-D tests, all 73 ACS transfer tests, and 1,020 tests
  spanning the pure kernels, multispine runtime, stacked spine, late DAG, build
  tool, and source-blindness guards reach 100% and exit zero. Only established
  pandas fragmentation warnings are emitted.
- Closed independent review with no remaining blocker. The Schedule-D operator
  contract now names both `non_sch_d_capital_gains` and its derived leaf, its
  kernel receipt repeats that exact surface, and the transient role-authority
  SHA covers the disclosed role counts. Re-review confirmed this later derive
  contract cannot enter any early or late ACS transfer surface.
- Committed the scoped production integration and its load-bearing regressions
  as `51054801` (`Wire scoped ACS transfer calibration`).
- Ran the complete repository collection with all fit/BLAS widths pinned to
  one: 6,623 tests reached 100% with no failure/error marker and pytest's
  `lastfailed` cache is empty. The surrounding macOS `time -l` process returned
  1 only after pytest because its own `sysctl kern.clockrate` probe is forbidden
  by the sandbox; `time -l true` reproduces that wrapper-only status.
- Full Ruff and lock freshness pass; all 13 changed Python files pass Ruff
  formatting and `git diff --check`. The repository-wide format audit still
  names 49 pre-existing unrelated files, which were left untouched.
- Finalized this terminal journal and `FINAL_REPORT.md` for the committed host
  handoff.
- Independently re-audited the committed wiring against pkg3's scoped-binding
  precedent and the production call graph. Both reviews found no unassigned
  target leakage: the default stacked build reaches all 20 assigned targets
  (7 early and 13 late), including mixed suffixed batches, and reaches the
  Schedule-D kernel only in the later derive stage. At that calibration-only
  commit, the retiring explicit `--legacy-two-spine` route was outside the
  remedy; the current tail section above supersedes its semantic-key claim.
- Re-ran the four load-bearing wiring fixtures and the complete 110-test ACS
  calibration/transfer/Schedule-D kernel set; both exited zero. A fresh full
  repository run at implementation HEAD `d9a38965` then completed in 53:11
  with 6,551 passed, 74 skipped, 1,890 established warnings, and an empty
  `lastfailed` cache (6,625 collected). Full Ruff, lock freshness, and
  `git diff --check` pass.
- Re-read pkg3's named `22b2c6bc` scoped-binding regression and its production
  successor `176c60fc`. The committed pkg1 boundary follows the same
  default-empty stable `(entity, target)` selection, owner-side active-surface
  intersection, and selected-only receipt pattern.
- Re-audited the current default build call graph from
  `tools/build_us_multispine_pool.py` through early gap fill, the bounded late
  producer DAG, and `transfer_acs_inputs`. Both banked and in-memory QRF paths
  converge on the post-decode/pre-fill calibration seam; the Schedule-D parent
  kernel remains isolated to the later derive stage.
- Re-ran the four invocation/scope/Schedule-D load-bearing fixtures and the
  complete 73-test ACS transfer module with all fit and BLAS widths pinned to
  one; both exited zero. Full Ruff, targeted formatting, unfrozen lock
  freshness, and `git diff --check` pass.
- Ran the default 6,623-test repository collection to 100% and exit zero in
  4,210.702 seconds. Its process reached 27,285,979,136 bytes RSS, so that green
  result is not treated as memory-compliance evidence.
- Replayed the exact 263-file manifest
  (`f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`)
  in fresh guarded processes. Accepted results were 6,549 passed and 74
  skipped; the maximum accepted peak was 11,841,650,688 bytes. The two
  cache-conditional tests that each parse the mounted 3.73 GB SIPP donor were
  explicitly deselected after isolated live guards stopped them at
  15,066,742,784 and 13,073,645,568 bytes, respectively, both below the hard
  15 GiB ceiling. Both had already passed in the green monolithic run, but
  neither resource profile is accepted under this charter.
- Preserved the user-provided `_WIRING-CONTINUATION.md` as the sole untracked
  file and did not stage or modify it.
- Reopened the continuation audit at `b5b3bc9b`; confirmed the committed tree
  already imports the calibration primitives into `acs_transfer.py`, exposes a
  default-empty exact-target selector, and contains an assigned-versus-
  unassigned call-recording regression. Further production-path and test
  verification is in progress.
- Re-read pkg3's named `22b2c6bc` scoped-binding regression and production
  successors `176c60fc`, `887df056`, and `94b7aecb`. The pkg1 selector has the
  same default-empty exact `(entity, target)`, active-surface intersection, and
  selected-only execution shape, with an additional fail-closed 20-target
  policy check. Independent review found no unassigned runtime mutation leak.
- Independently traced the default CLI through stacked gap-fill, the bounded
  late-producer DAG, and the derive stage. Live canonical constants partition
  the policy into 7 early and 13 late targets with no overlap or omission;
  banked and in-memory fits converge on the same post-decode/pre-fill seam.
  Schedule-D derivation is disabled in every late group, then its clone-0 role
  authority is consumed by the parent reconciliation before leaf derivation.
- Replayed the four load-bearing call/scope/Schedule-D fixtures; all passed.
  Replayed the complete 110-test ACS transfer, calibration-kernel, and
  Schedule-D-kernel set with all fit/BLAS widths pinned to one; all passed.
  Runtime code is unchanged from `51054801`, the implementation tree already
  covered by the committed full-suite and guarded-replay evidence.
- Re-ran full Ruff, an explicitly unfrozen `uv lock --check`, and
  `git diff --check`; all passed. The first lock invocation inherited
  `UV_FROZEN=1` and therefore checked validity only, so the accepted freshness
  result is the explicit `env -u UV_FROZEN ... uv lock --check` replay.
- Updated the terminal `FINAL_REPORT.md`. The only untracked file remains the
  user-provided `_WIRING-CONTINUATION.md`, preserved byte-for-byte and excluded
  from every commit.
- Revalidated the terminal implementation at pre-audit tip `a9d930ef` with
  three independent read-only reviews covering the exact early/late production
  scope, the load-bearing assigned-versus-unassigned invocation regression,
  and the Schedule-D derive path. All three found no blocking wiring or runtime
  scope defect. Replayed the four load-bearing fixtures and the complete
  110-test ACS transfer/calibration/Schedule-D set; both exited zero. Full
  Ruff, explicitly unfrozen lock freshness, and `git diff --check` also pass.
  No 1% build ran.
- Reopened the host-requested wiring continuation at `ea2fb474`. Preserved the
  user-owned `_WIRING-CONTINUATION.md`, confirmed the implementation and its
  earlier verification commits are present, and began a fresh source/test
  audit rather than relying on the root journal's historical state claims.
- Re-read pkg3's named regression `22b2c6bc` and production scoping commits
  `176c60fc`, `887df056`, and `94b7aecb`. The current pkg1 boundary mirrors
  their default-empty exact `(entity, target)` selection, active-surface
  intersection, and selected-only evidence shape, with an additional frozen
  20-target policy check. No default-stacked scope leak was found.
- Traced the default CLI into the stacked early and late owners. Both banked
  and in-memory QRF fits converge on the imported post-decode/pre-fill kernel
  seam. The explicit retiring `--legacy-two-spine` route deliberately retains
  its empty selector and is outside the default production remedy.
- Re-ran the four load-bearing assigned/unassigned and Schedule-D fixtures;
  all passed. Re-ran the complete ACS transfer, calibration-kernel, and
  Schedule-D-kernel modules with all fit/BLAS widths pinned to one; all 110
  tests passed.
- Completed three independent read-only reviews of the pkg3 precedent,
  production call graph/exact target inventory, and wiring-test/Schedule-D
  coverage. The live policy intersection is exactly 20 of 20 assigned targets:
  7 early and 13 late, with no overlap, omission, or unassigned invocation.
  Seven independently selected wiring/order nodes also passed.
- Confirmed with an empty Python/test/dependency diff that runtime remains
  identical to `51054801`, the implementation tree covered by the committed
  6,551-passed/74-skipped full-suite run and the exact 263-file guarded replay
  whose highest accepted peak was 11,841,650,688 bytes. The two unrelated
  cache-conditional 3.73-GB SIPP nodes remain covered by the green monolithic
  run but excluded from the accepted resource profile, as previously recorded.
- Re-ran full Ruff, explicitly unfrozen lock freshness, `git diff --check`,
  and the empty pytest `lastfailed` check; all passed. Finalized the current
  `FINAL_REPORT.md` without changing runtime or tests.
- Reopened the wiring task at `2874f562`, loaded the current repository rules,
  preserved the user-provided untracked continuation brief, and began fresh
  read-only reviews of the pkg3 scope pattern, production transfer path, and
  load-bearing invocation regression.
- Read pkg3's named `22b2c6bc` regression and production successor
  `176c60fc`. The applicable boundary is default-empty exact
  `(entity, target)` selection, active-surface intersection, and selected-only
  evidence; a shared family or suffixed batch is not calibration authority.
- Traced `tools/build_us_multispine_pool.py` through the default stacked early
  gap fill, bounded late-producer DAG, and post-transfer derive stage. Both ACS
  QRF modes converge on the same imported post-decode/pre-fill seam, while the
  Schedule-D parent repair consumes its transient role only in derive.
- Evaluated the live canonical surfaces against
  `PUF_TAX_TRANSFER_CALIBRATION_POLICY`: exactly 20 of 20 targets are reachable
  (7 early, 13 late), with no overlap, omission, or out-of-policy target.
- Ran the four load-bearing nodes with all fit/BLAS widths pinned to one. The
  primitive call recorder, production-owner exact-scope receipt, Schedule-D
  role consumption/preservation, and legacy no-marker behavior all passed.
- Confirmed runtime, tests, dependencies, and lock remain byte-identical to
  implementation commit `51054801`; later commits through this audit are
  journals and reports only.
- Completed three fresh independent read-only audits of the pkg3 precedent,
  default production call graph, exact target inventory, fixture strength, and
  Schedule-D path. All found the committed wiring complete and target-exact.
- Replayed the complete 110-test ACS transfer, calibration-kernel, and
  Schedule-D-kernel set with all fit/BLAS widths pinned to one; all passed.
- Re-ran full Ruff, explicitly unfrozen `uv lock --check`, Ruff formatting on
  all 17 branch-changed Python files, `git diff --check`, and the pytest
  `lastfailed` check; all passed. The only untracked file is the untouched
  user-provided continuation brief.
- Reopened the current host continuation, read `CLAUDE.md` and the complete
  GitNexus debugging skill, inspected branch/worktree state, and preserved the
  user-owned untracked continuation brief. Fresh source and regression audits
  are underway before accepting any historical completion claim.
- Attempted the GitNexus debugging trace. This worktree was not indexed, and
  analysis could not register it because the sandbox denies writes to the
  global `~/.gitnexus/registry.json`; the analyzer cleaned up its partial local
  artifact. Continued with direct source/call-site tracing.
- Re-read pkg3's named regression commit `22b2c6bc` and its production follow-up
  `176c60fc`. The applicable pattern is default-empty exact `(entity, target)`
  selection, validation against the requested surface, per-family
  intersection, and selected-only evidence even for mixed bounded batches.
- Confirmed `transfer_acs_inputs` normalizes the exact selection against both
  the requested surface and the frozen PUF-tax policy, intersects it with live
  missing targets, invokes `_calibrate_puf_tax_predictions` after either QRF
  path decodes and before null-only fill, and passes only the selected target
  arrays to the imported kernels.
- Traced the default build CLI through `gap_fill_stacked_spine`, the bounded
  late-producer DAG, and `derive_multispine_pool_inputs`. Both stacked transfer
  owners bind exact active selections and caller-owned references; the derive
  chain invokes `_complete_schedule_d_input`, which consumes the transient
  Schedule-D role and calls `reconcile_schedule_d_joint_parents` before leaf
  derivation.
- Evaluated the live canonical surfaces against
  `PUF_TAX_TRANSFER_CALIBRATION_POLICY`: all 20 assigned targets are reachable
  as 7 early and 13 late targets, with zero overlap and zero omission.
- Inspected the existing load-bearing regressions. The low-level same-batch
  call recorder proves assigned invocation and unassigned non-invocation; the
  stacked-owner fixture separately proves the production caller passes only
  the assigned tuple; Schedule-D fixtures prove role consumption, parent
  preservation, and the marker-absent compatibility no-op.
- Re-ran the four load-bearing invocation/scope/Schedule-D fixtures with all
  fit and BLAS widths pinned to one and pytest's cache disabled. All four
  passed; the process peaked at 608,157,696 bytes RSS.
- Re-ran the complete ACS transfer, calibration-kernel, and Schedule-D-kernel
  modules under the same controls. All 110 tests passed; the process peaked at
  600,834,048 bytes RSS.
- Found and closed one narrow Schedule-D regression gap: producer-role and
  consumer-kernel tests were separately load-bearing, but the stubbed default
  tool fixture returned the original frame from tail preparation. It now
  returns a distinct frame carrying the transient role, and the derive stub
  asserts exact object handoff and role presence before consuming it. A future
  regression from `derive_multispine_pool_inputs(derivation_input)` back to the
  unprepared `current` frame can no longer remain green.
- Re-ran all three terminal-state variants of the stacked tool entrypoint
  fixture after that hardening; all passed at 1,243,398,144 bytes peak RSS.
  Focused Ruff, formatting, and `git diff --check` pass.
- Began the exact 263-file resource-isolated suite replay under a 14 GiB live
  guard. The first pass through the modified tool module exposed a fixture-only
  assumption: its checkpoint-resume test legitimately prepares and derives
  twice, while the new assertion required one lifetime call. Changed the
  assertion to require every derive call to receive the most recently prepared
  frame, preserving the intended handoff guarantee across cold and resumed
  builds.
- Re-ran the complete 155-test multispine tool module after that correction;
  it reached 100% and exited zero at 1,333,870,592 bytes peak RSS. The broader
  isolated replay will resume from the next file.
- Completed the exact 263-file manifest replay with SHA-256
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`.
  Every file exited zero in a fresh process with fit/BLAS widths pinned to one
  and a 14 GiB live guard. Aggregated results were 6,549 passed, 74 skipped,
  and 2 explicitly deselected cache-only nodes; collection independently found
  6,623 runnable items plus the two import/environment skips.
- The two deselections are
  `test_cached_full_donor_matches_pinned_household_support` and
  `test_cached_full_donor_matches_locked_response_and_weight_facts`. Both parse
  the locally mounted 3.73 GB SIPP donor and were previously observed unable to
  complete within this lane's memory ceiling; all other tests in their files
  passed. No guard fired in the accepted replay.
- The maximum accepted peak was 11,844,042,752 bytes in
  `packages/microcosm-data/tests/test_loader.py`, below the 15 GiB ceiling.
  The complete 73-test QRF module, 73-test ACS transfer module, 18-test ACS
  calibration module, 19-test Schedule-D kernel module, 72-test multispine
  pool module, 155-test pool-tool module, and 231-test stacked-spine module all
  passed inside the replay.
- Ran full `ruff check .`, an explicitly unfrozen `uv lock --check`, Ruff
  formatting checks on all 17 branch-changed Python files, `git diff --check`,
  and the pytest `lastfailed` check. All pass; `lastfailed` is `{}`.
- Confirmed that the only Python/dependency change after runtime implementation
  commit `51054801` is the 21-line Schedule-D handoff regression in
  `test_us_multispine_pool_tool.py`; runtime, dependencies, and lock remain
  unchanged. The only untracked file is the untouched user continuation brief.
- Reopened the host continuation at `342876fc`, committed the current
  state/done/next journal as `0b78c148`, and treated all historical completion
  claims as untrusted pending live source and test evidence.
- Attempted the prescribed GitNexus trace. The repository is not indexed and
  `gitnexus analyze` cannot write its global registry under the managed
  sandbox; its partial local artifact was moved out of the worktree before
  direct call-site tracing continued.
- Re-read pkg3's `22b2c6bc` regression and `176c60fc` production follow-up.
  The current selector matches their default-empty exact `(entity, target)`,
  requested-surface validation, owner-side active intersection, and
  selected-only execution/evidence pattern; batch or family membership grants
  no authority.
- Traced the default CLI through `build_stacked_pool`, early gap fill, the
  bounded late-producer DAG, tail preparation, and pool derivation. Both banked
  and in-memory transfer paths invoke the imported calibration seam after
  decoding and before null-only fill. The unselected direct call in
  `_impute_pool` belongs only to explicit `--legacy-two-spine` compatibility.
- Evaluated the live canonical surfaces against the frozen policy: exactly 20
  of 20 targets are reachable, split into 7 early and 13 late targets with no
  overlap, omission, or extra target. Schedule-D remains separately scoped by
  a transient clone-0 role consumed by `_complete_schedule_d_input` before leaf
  derivation.
- Re-ran the four load-bearing fixtures covering imported-kernel invocation,
  same-batch unassigned non-invocation, production-owner exact selection, and
  Schedule-D role consumption/preservation. All four passed in 8.77 seconds
  with fit and BLAS widths pinned to one and pytest's cache disabled.
- Completed three independent read-only reviews of the pkg3 precedent,
  production call graph/checkpoint routing, and load-bearing regression set.
  All found no blocking defect. Removing or bypassing the early owner, late
  owner, common transfer seam, Schedule-D derive dispatch, or prepared-frame
  handoff makes at least one committed test fail.
- Re-ran all 110 tests in the ACS transfer, calibration-kernel, and Schedule-D
  reconciliation modules with fit and BLAS widths pinned to one and pytest's
  cache disabled. They reached 100% and exited zero in 237.03 seconds.
- Confirmed the runtime, tests, dependencies, and lock are byte-identical to
  `afbc80aa`, whose exact 263-file resource-isolated suite replay recorded
  6,549 passed, 74 skipped, 2 cache-only mounted-SIPP nodes explicitly
  deselected, and an 11,844,042,752-byte maximum accepted peak below 15 GiB.
  Only `PROGRESS.md` and `FINAL_REPORT.md` changed after that evidence commit.
- Re-ran full Ruff, explicitly unfrozen lock freshness, and `git diff --check`;
  all pass. No implementation or regression change was needed during this
  final audit because the requested wiring and load-bearing tests are already
  present in the live tree.
- Reopened the continuation at `a3e00a68`, read `CLAUDE.md` and the complete
  GitNexus debugging skill, and inspected the live branch/worktree before
  trusting historical journal claims. GitNexus graph tools are unavailable in
  this session, so direct source and Git call-path tracing is the fallback.
- Re-read pkg3 regression `22b2c6bc` and its implementation follow-up
  `176c60fc`. Their applicable pattern is a default-empty exact
  `(entity, target)` selector, validation against the requested surface,
  owner-side active intersection, and selected-only evidence even when an
  unassigned sibling shares a bounded QRF batch.
- Confirmed the host's zero-caller evidence describes the tree before
  `51054801`: the predecessor has no calibration import or selector, while the
  current tree directly imports all three primitives, validates selection
  against the requested surface and frozen policy, intersects live missing
  targets, and invokes the common post-decode/pre-fill seam for banked and
  in-memory QRF execution.
- Evaluated the live canonical surfaces against the frozen 20-target policy.
  Early gap fill reaches 7 exact targets and the bounded late DAG reaches the
  other 13, with zero overlap, omission, or unassigned target.
- Traced the default tool from `gap_fill_stacked_spine` through
  `run_stacked_late_producer_dag`, `prepare_stacked_tail_derivation`, and
  `derive_multispine_pool_inputs`. The prepared frame assigns ASEC clone 0 as
  Schedule-D reference and ACS clone 0 as recipient; `_complete_schedule_d_input`
  consumes those roles and invokes `reconcile_schedule_d_joint_parents` before
  deriving the Schedule-D leaf. The explicit legacy route remains outside the
  remedy.
- Replayed 10 load-bearing fixture cases with all fit/BLAS widths pinned to one,
  pytest's cache disabled, and a 14 GiB root-RSS guard. They cover the imported
  assigned-kernel call and same-batch unassigned non-call; exact early-owner and
  both late-owner references; Schedule-D role production and parent-kernel
  consumption/preservation; all three terminal tool states; and checkpoint
  resume. All passed at 1,146,896,384 bytes maximum root RSS with no guard event.
- Replayed the exact 263-file tracked test manifest from a fresh receipt at
  `/private/tmp/pkg1-wiring-suite.p1I5ZN/receipt.jsonl`; its SHA-256 is
  `f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`.
  Every file ran in a fresh interpreter with fit/BLAS widths pinned to one,
  pytest's cache disabled, and a 14 GiB root-RSS guard. Aggregated results were
  6,549 passed, 74 skipped, zero failures, and zero errors; no guard fired.
- The maximum fresh root RSS was 11,845,337,088 bytes in
  `packages/microcosm-data/tests/test_loader.py`, below both the 14 GiB guard
  and 15 GiB charter ceiling. The complete 73-test fit QRF, 73-test ACS
  transfer, 18-test calibration-kernel, 19-test Schedule-D, 72-test multispine
  pool, 155-test pool-tool, 231-test stacked-spine, and 495-test
  source-blindness modules all passed inside this replay.
- The only deselections were the two previously documented cache probes
  `test_cached_full_donor_matches_pinned_household_support` and
  `test_cached_full_donor_matches_locked_response_and_weight_facts`. Each
  independently parses the locally mounted 3.73 GB SIPP donor and exceeds this
  lane's memory ceiling; every other test in both files passed.
- Ran full Ruff, Ruff formatting checks on all 17 branch-changed Python files,
  an explicitly unfrozen `uv lock --check`, and `git diff --check`; all pass.
  The first Ruff attempt hit uv's sandbox-denied home cache and the first lock
  attempt inherited `UV_FROZEN=1`; clean retries used a writable temporary
  cache and removed that environment override before recording success.
- Refreshed and committed `FINAL_REPORT.md` at `44e06476` with the live wiring
  trace, guarded test evidence, unchanged frozen gates, and host handoff.

## Next

- Return the committed tip to the serial host queue; do not run or push a pool
  build from this lane.
