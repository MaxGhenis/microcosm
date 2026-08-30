# Authorized stacked `weeks_worked` implementation (v3)

Date: 2026-08-30

Branch: `stacked-dense-gate-sweep`

Plan SHA-256: `e89dd0facbc6d22f296f65ff18520333af0f8ecc6c2b706c1fd6a2b98d49e729`

## State

Implementation in progress. The declarative 2024 source stage, provenance-owner
runtime, dedicated fail-closed gate, release-builder/manifest integration, and
consumer/period-boundary regressions are complete and green. Repository-wide
verification remains. The authorized v3 ruling is the binding scope: code,
spec, and tests only; no data build, artifact mutation, publication, push, or
PR. Candidate-25 remains read-only evidence.

## Done

- Read `PROGRESS.md`, `CLAUDE.md`, `AGENTS.md`, and the complete binding plan
  before implementation.
- Verified the plan file byte identity against Max's authorized SHA-256.
- Found only the untracked r3 plan in the inherited tree and preserved it
  honestly at WIP commit `b71ca20a`; no inherited implementation edits were
  present.
- Reconfirmed the non-negotiable boundaries: 2024 release-only materialization,
  provenance-owner routing, exact source authentication and clone fan-out,
  an additive weeks-specific gate, unchanged pool exclusion/gate 9480/hours
  gate/thresholds, and 2025 carry-forward rather than direct materialization.
- Traced the typed source compiler, provenance-owner allowlist, stacked release
  ordering, manifest receipt pattern, period-aware frame adapter, ORG/FLSA
  consumers, SPM formula, and PolicyEngine-US 1.819.0 carry-forward formula.
- Added the generated `stacked_release_weeks_worked` source declaration and
  closed-vocabulary `derive_stacked_release_weeks_worked` kernel registration.
  The stage pins the 2024 ACS person ZIP, exact raw fields and domains, the
  accepted reference-window mismatch, and Microcosm ownership of the ACS blank
  recode. Regenerated `spec/sources.yaml` through the repository generator.
- Added the release-only provenance-owner runtime. It authenticates the pool
  HDF5/manifest identity and ACS archive, scans the complete two-member archive,
  validates `WKWN` and `FWKWNP`, asserts the exact joint blank/allocation table,
  performs an exact one-to-one `SERIALNO + SPORDER` join, and only then fans out
  through validated `person_source_id` across clone roles 0/1/2.
- Added the dedicated additive weeks gate and source receipt: raw ASEC/ACS
  domains; exact archive/period identities; exact join counts and key digest;
  origin x clone-role joint table; zero per-source clone disagreements;
  Microcosm blank-recode counts; canonical source-value digest; conflicting
  pre-existing-value rejection; and a byte-sensitive only-weeks column diff.
- Closed adversarial review findings before commit: extra selected raw keys now
  fail the exact semantic-key-set assertion, coherent all-clone value tampering
  fails the source-value binding, and rehashed raw-domain receipts are validated
  semantically rather than trusted as self-describing JSON.
- Focused weeks tests pass 22/22 with Ruff green. Compatibility tests pass
  544/544 across source runtime, the unchanged hours stage, and the complete
  source-blindness/provenance-owner contract.
- Typed-source/spec compatibility passes 61/61, and the US bundle generator
  `--check` is green. Updated the deliberate source-stage count/hash pins and
  the BE/UK spec identities changed by the shared closed-operation schema; the
  generated US spec identity is
  `e9ea75c7cc5a1613f0fde007f1061ad23dbf8e2d3c4574523c5469f77b8209ed`.
- Committed the declarative/runtime/gate step at `268ad894`.
- Wired the stage only for authenticated stacked inputs, immediately after the
  base frame is loaded and before capital-gains-tail checks, weeks-unemployed,
  frozen-support selection, and the unchanged hours signal gate. Both the
  explicit pool-manifest route and an identified `--base-h5` pool use the one
  returned `AuthenticatedPoolH5`; the stage re-verifies its bytes and receipts
  its H5 and manifest digests. Legacy bare H5 behavior is unchanged.
- Added immediate fail-closed release handling and telemetry. The source receipt
  and dedicated gate receipt now propagate through `build_manifest.json`,
  `release_manifest.json`, and calibration diagnostics; both manifests carry
  the origin x clone-role table, raw joint allocation table through the source
  receipt, disagreement counts, and only-weeks column diff evidence.
- The complete release-builder suite passes 235/235 with focused Ruff green,
  including executable order/authentication checks, the exact-k stacked path,
  the provenance-aware gate roster, and a four-location manifest round trip.
- Added a composed measured-leaf regression that runs the release weeks source
  stage and then the real ORG/FLSA operator. It proves the authorized values
  reach ORG's `52 / weeks` annualization, zero weeks use the deliberate income
  bypass, positive weeks retain the actual-income FLSA premium, zero weeks
  suppress that premium, and the ORG stage preserves the measured leaf.
- Added a registered-`requires_us` live PolicyEngine-US 1.819.0 SPM regression:
  the fixture's 10- and 20-week values produce exactly $349.945 and $699.890 of
  `spm_unit_work_expenses`; zero-income adults and child earners do not
  contribute.
- Strengthened the period-boundary adapter regression. A 2024
  `weeks_worked` leaf round-trips through `USSingleYearDataset`, the installed
  2025 formula carries it forward unchanged, and a direct 2025 dataset write
  fails as formula-owned without creating a file.
- Both focused consumer files pass 62/62 (24 release-weeks and 38 frame-adapter
  cases), with focused Ruff green.
- The final anti-rot pass exposed and closed the remaining spec-attestation
  follow-through: the measured stage adds 35 authored fields, taking the exact
  ledger from 41,523 to 41,558 and source stages from 37 to 38. Re-pinned the
  exact source-stage pointer inventory, compiler projections, seed-map/source-
  manifest/checkpoint identities, and regenerated the committed coverage
  report. All 35 field-usage/inventory/coverage tests pass, focused Ruff is
  green, and `spec_engine_coverage.py --check` proves 41,558/41,558 fields and
  41/41 inventory checks.
- Independent final plan audits found one declaration/runtime mismatch before
  completion: the new source-stage artifact had a mistyped ACS archive digest
  while the runtime correctly enforced the established official archive pin.
  Corrected the declaration to
  `afdc6d90c6e2f0bab365ed32d95ba4c4d8ac651162f46ac7861295b2dc469894`,
  regenerated the US bundle and every dependent compiler attestation, and
  added an explicit test binding the declared digest and row count to the
  runtime constants. The 24-test weeks suite plus both direct identity tests,
  focused Ruff, generator `--check`, and coverage `--check` are green. Both
  independent audits report no remaining v3 plan gap.

## Next

- Commit the corrected ACS declaration and dependent identities.
- Rerun the complete affected spec corridor and build shard against the
  committed final tree. The frame, fit, data, and calibrate shards are already
  green; finalize the journal and required output report afterward.

---

> **Historical material below.** Earlier sections are accurate for their
> completed lanes but are not current implementation state.

# Stacked dense-release gate sweep: farm-rent and remaining single-spine gates

Date: 2026-08-29

Completed: 2026-08-30

Branch: `stacked-dense-gate-sweep`

Lane base: `7d44c0b5`

## Continuation: post-farm fail-fast adjudication

### State

Complete on 2026-08-30 with verdict `ADJUDICATION-BLOCKED`. Continuation r3
recovered the interrupted 31-file implementation from salvage `38b424f8`,
preserved it without history rewriting at WIP `8129c9b7`, independently
reviewed every producer and adapter cluster, corrected the unsound pieces in
follow-up commits, completed the read-only post-producer health replay, and
passed repository-wide verification. The authoritative verdict report is
`out.md`, committed at `ce643527`; its first line is
`ADJUDICATION-BLOCKED`.

The lane-local adjudication work is finished. Dense certification remains
blocked on the explicit Max ruling for stacked `weeks_worked`/ORG ownership
and the separate no-build hold. Candidate-25 remains the immutable historical
`gate_failed` artifact; no pool/release artifact, publication surface, remote,
or data build was modified or run.

### Done

- Read this 918-line journal in full before inspecting the worktree, then read
  `CLAUDE.md` and the GitNexus debugging workflow. The repository remains
  unindexed, so review uses direct source, tests, immutable evidence, and
  executable call/dataflow receipts without generating unrelated index state.
- Inventoried the inherited r2 tree: 31 tracked files, 4,595 insertions and 254
  deletions, plus the r3 lane prompt. `git diff --check` was clean. The tracked
  tree exactly matched salvage `38b424f8`, whose sole parent is `615710d7`;
  only the session prompt differs between the preserved r2 salvage and r3.
- Preserved the complete inherited tracked implementation at `8129c9b7` with
  an honest WIP message. It appears to contain the joint `acs_rent`
  property-tax producer and native ACS source-domain receipt, the ten-leaf
  native-zero expansion, authority-bound SSI/rent/tenure engine-copy adapters,
  stacked receipt propagation, generated spec/schema identity changes, and
  focused fixtures. None of that inherited work is accepted merely by the
  snapshot commit.
- Ran the first producer corridor: all 43 ACS-input and housing-input cases
  pass. The broader stacked-spine/late-DAG/pool runtime cases were green, but
  24 typed-spec cases errored because the inherited generated bindings outran
  their closed JSON schema and reverse projector. The narrow schema/projector
  repair is in progress; no stale generated identity will be hand-edited.
- Independent integration review found stale current-version locks outside the
  inherited diff. Commit `2ebd0a2c` updates stacked authority v12 and pool
  checkpoint materializer v8 expectations, retains v7 as an explicitly tested
  legacy checkpoint, and passes all 12 affected cases with focused Ruff.
- The complete SSI/H5/release-builder adapter corridor passes 323 tests. Added
  missing sparse-tenure and candidate-style full-clone/version-2-tail
  regressions. The latter exposed a real loader defect: nested receipts are
  frozen inside `Frame`, so shallow `dict` equality rejected an otherwise
  exact version-2 receipt. Commit `f82d7bc8` compares JSON-normalized receipts;
  both new cases and focused Ruff pass. The adapters still alter only engine
  table copies and reject selected-batch lineage drift.
- Closed the inherited typed-spec/schema mismatch at `0363f739`. The JSON
  schema now admits the structural-reconciliation policy, native-zero
  authority kind, and three second-home keys; the reverse projector restores
  typed source-stage references and the exact numeric legacy policy form.
  The official bundle generator changes only `spec/imputation.yaml`, its
  `--check` mode passes, and the complete spec-bundle/core-contract corridor is
  green.
- Recut the downstream source-attested compiler identities at `b6599ff7`
  after independent bundle, projector, and coverage-ledger reviews found only
  expected identity drift. The official coverage generator and `--check`
  report 41,523/41,523 configuration fields and 41/41 inventory checks; BE and
  UK envelope digests match their independently computed values. A 13-file
  compiler corridor, including seed, loader, coverage, compiler-IR, legacy
  adapter, and stacked-authority suites, passes after two final hidden pins
  were corrected; focused Ruff and `git diff --check` are clean.
- Re-read `CLAUDE.md`, confirmed the PR-CI/certification boundary and the
  root-journal history convention, and verified a clean
  `stacked-dense-gate-sweep` worktree at `2422669e` before this continuation.
- Re-read the GitNexus debugging workflow. The prior committed sweep already
  records that this repository has no local GitNexus index or query resources;
  no unrelated index state will be generated. Source, tests, immutable HDF,
  and builder-stage replay will provide the call/dataflow receipts.
- Reconfirmed the standing constraints: commit every coherent step, maintain
  this journal from the start, do not modify pool/release artifacts, do not
  push, and make `out.md` the final report with the required first line.
- Traced the post-farm release order in current `_main`. On an authenticated
  pool, the prior-year (`9578`) and housing (`9601`) gates consume the loaded
  base after only release-owned value repairs and SNAP take-up; the education
  (`9703`), pregnancy, and WIC (`9782`) source writers are explicitly skipped
  when `pool_frame is not None`, so those gates consume the corresponding pool
  content. The reported-coverage vintage gate (`9748`) likewise consumes that
  frame directly.
- Confirmed the release-only divergence for health: the first
  `_health_input_signal_gate` call (`10261`) follows
  `_with_aca_marketplace_source_outputs`, which replaces both required tax-unit
  columns; the second call is on the later export frame. A raw-pool health red
  is therefore not an actual-stage verdict unless it survives that producer.
- Confirmed the merged ACS predictor join (`9828`) precedes exactly the six
  archived-model producer/gate pairs: SCF wealth, SSI disability criteria, SCF
  auto loans, SIPP vehicles, SIPP tips, and ORG wages/FLSA. The order is also
  executable-contracted by
  `test_acs_predictor_join_precedes_all_six_archived_model_stages`.
- Exact-compared the requested surfaces with the farm repair's seven
  PUF-detail/native-zero leaves. Housing, education/AOTC, reported coverage,
  WIC, ACA health, prior-year income, ACS predictor inputs, and all six model
  outputs are disjoint from those seven leaves; any existing red on those
  surfaces is independent of the rebuild unless a later release producer
  materializes it.
- Reproduced the prior-year discrepancy at the true release boundary. The
  authenticated stack receipt supplies version 4 / `sample_fraction=0.25`, and
  the gate passes the candidate bytes at weighted availability
  `0.042838786938937584` against the derived `[0.0125, 0.50]` band. However,
  both unconditional release value repairs reconstructed `Frame` without its
  metadata; line 9578 therefore saw no rung, applied `[0.05, 0.50]`, and
  emitted `previous-year availability weighted share 0.042839 outside
  [0.050000, 0.500000].`
- Fixed that dense-blocking release-path plumbing defect at its root: the
  Social Security component and non-schedule-D capital-gain value repairs now
  preserve `frame.metadata` exactly alongside strata, weights, and mass log.
  Their focused regressions carry a production-like rung receipt through each
  constructor. The two focused tests pass and focused Ruff/diff checks are
  green. No authored prior-year band or threshold changed.
- Found and repaired the next actual-stage blocker before the six archived
  models. The schema-9 manifest authenticates a version-1
  `assembly_receipt`, but the H5 loader restored only the stack/rung and late-
  producer receipts. Consequently `join_acs_release_predictors` aborted with
  `ACS release predictor join: receipt-validated support provenance has no
  assembly manifest 'us_spine_assembly_manifest'.` The loader now requires the
  receipt on a stacked envelope, restores it verbatim, and validates its native
  channel counts and all live cross-grain links. Legacy schema-4 compatibility
  remains unchanged (a legacy receipt is restored and checked when present).
  The 36-case stacked/scoring/release loader corridor passes, including
  missing-receipt and live-count-tamper refusals; focused Ruff/diff checks are
  green.
- The faithful archived replay also exposed a previously hidden release skip:
  the multispine projection deliberately omits `person.weeks_worked`, but the
  release calls the hours-worked reconstruction only on the non-pool path.
  The true line-9480 gate therefore emits `person columns missing:
  ['weeks_worked'].`, and ORG would later refuse the same missing predictor.
  This is independent of the seven-leaf rebuild. Unconditionally invoking the
  legacy source writer is not a valid repair: the ASEC raw columns are null on
  physical ACS rows, so it erases their transferred weekly/last-week hours,
  makes all three ACS hours surfaces zero, and the gate instead emits `worked
  share 0.263 outside plausibility band [0.35, 0.62].` A release fix therefore
  requires an owner ruling on the stacked period-scoped `weeks_worked`
  semantics (native ACS weeks, ASEC-model transfer, or formula ownership). No
  modeling choice or gate weakening will be made in this lane without that
  ruling.
- An independent source/receipt audit confirmed the exact ownership boundary.
  The candidate carries raw ASEC `WKSWORK` plus both transferred hours leaves,
  and its manifest records a passing 53-value weeks source surface followed by
  `pool_excluded_outputs_removed.person=['weeks_worked']`. The ACS loader and
  #805 join both omit `WKWN`; moreover #805 runs after the hours gate. The
  pinned official ACS archive does contain `WKWN` on 1,767,132 of 3,422,888
  people with the exact 1..52 domain (blank for its official NIU population),
  so the evidence-favored smallest ruling is: authorize a **2024 release-only,
  origin-aware measured leaf** before the hours gate—ASEC lineages use clipped
  `WKSWORK`, ACS lineages use pinned `WKWN` with official blank/NIU mapped to
  zero, and both fan out by authenticated source identity—while retaining the
  pool's cross-period formula-owned exclusion. Alternatives are the larger
  modeling choices of ASEC-to-ACS statistical transfer or changing ORG/FLSA's
  denominator semantics. None is authorized here.
- Replayed the four candidate housing failures exactly. The 31,133 assistance
  mismatches and 260 positive-rent nonheads are physical-ACS coherence defects
  caused by independent late target transfers. The other two failures reopen
  the prior single-spine gate ruling with concrete authority receipts: all
  91,032 nonfinite rents are physical-ACS `TYPEHUGQ` 2/3 group-quarters rows
  whose absence receipt requires structural null, and `OWNED_OUTRIGHT` is a
  valid physical-ACS `TEN` category. The exact gate text is: (1)
  `takes_up_housing_assistance_if_eligible differs from measured
  receives_housing_assistance on 31133 SPM unit(s).`; (2) `nonfinite
  pre_subsidy_rent: 91032.`; (3) `positive rent on non-head people: 260.`;
  and (4) `household tenure_type does not carry the three locked ASEC
  categories: ['NONE', 'OWNED_OUTRIGHT', 'OWNED_WITH_MORTGAGE', 'RENTED'].`
- Replayed the education red: all five AOTC facts disagree with final positive
  qualified tuition on physical ACS rows because their independent final
  transfer runs after the source operator's deterministic derivation. Four
  mismatch counts are 17,290; the 1098-T/exception fact has 17,291. Replayed
  the WIC red: physical-ACS independent transfer yields exact failures
  `takes_up_wic_if_eligible: none weighted claim share 0.004767 outside
  [0.000, 0.000]` and `takes_up_wic_if_eligible: 32078 support-clone claim
  mismatch(es)`. These mechanisms are disjoint from and persist after the
  farm seven-leaf repair.
- Replayed all 14 vintage failures: seven reported-coverage outputs have zero
  reporters over 78,289 `asec/2022` rows and again over 77,846 `asec/2023`
  rows. The frozen Census-derived H5 cohorts carried only `NOW_GRP` and
  `NOW_MRK`; this is a genuine ASEC raw-stage content defect, not sampling or
  a gate assumption. The already pinned official 2023/2024/2025 ASEC CSV
  person members contain every missing measured recode with complete unique
  `PERIDNUM` keys and no null values, so the bounded repair is an exact,
  authenticated `(source_year, PERIDNUM)` sidecar join—never imputation.
- Completed the six archived-model reconciliation with the candidate's
  original transferred hours preserved and only the authenticated assembly
  receipt restored so the merged #805 join could execute. Five producer/gate
  pairs are green with empty failure lists: SCF wealth (bank/stock/bond
  weighted nonzero shares 0.387899/0.112850/0.011718), SSI disability (true
  share 0.073720; zero anchor mismatches), SCF auto loans (interest share
  0.271253), SIPP vehicles (owned/value shares 0.835794/0.838655), and SIPP
  tips (tip/tipped-occupation shares 0.003864/0.078835). Thus #805 does
  populate the ACS predictors before those actual producers; the seven farm
  leaves are irrelevant.
- Isolated ORG in a separate counterfactual only after deliberately running
  the invalid CPS-only hours writer. The #805-dependent carried bands all turn
  green (`cps_race` 1.0; Hispanic 0.194239; detailed occupation 0.819802;
  never-worked 0.256790; military 0.002039; computer science 0.019799;
  education 0.289775; farmer 0.003423), directly rebutting the old null-ACS
  predictor prognosis. But the writer's zeroed ACS hours make ORG emit
  `hourly_wage: weighted nonzero share 0.2483 outside [0.4, 0.7].` and
  `is_paid_hourly: weighted nonzero share 0.1222 outside [0.15, 0.4].` This is
  not an actual-stage ORG verdict; actual execution stops on missing
  `weeks_worked`. The evidence-favored ruling is an origin-aware, source-
  direct ACS `WKWN` mapping carried ephemerally by the release join while ASEC
  retains measured `WKSWORK`, but authorizing that formula-owned release
  materialization remains outside this lane.
- Implemented the genuine reported-coverage content repair at the producing
  ASEC raw stage. A new pinned-source loader reuses the existing official ASEC
  archive/member SHA-256 authorities, requires complete unique 22-digit
  `PERIDNUM` keys, redundant Census identity agreement, exact `{1, 2}` domains,
  and consistency with any already-present value, then joins all seven
  measured recodes by `(source_year, PERIDNUM)`. Each column receives its own
  audit/mapping receipt. Raw checkpoint schema 4 now requires those columns
  and mappings, so schema-3 artifacts fail closed. Read-only real-data replay
  matched 290,398/290,398 locked 2022+2023 H5 people and restored nonzero
  reporters (including Medicaid 28,184/26,367 and CHAMPVA 260/335). The focused
  source/builder/checkpoint corridor passes 297 cases, the gate/source-closure
  corridor passes 16, and targeted Ruff/format checks are green. No evidence
  artifact or authored gate threshold changed.
- Reproduced the first PolicyEngine dataset-boundary failure hidden behind the
  archived-model ordering. At the true pre-SSI-take-up boundary, all 261,605
  blank ACS `ssi_reported` cells belong to people below age 15, while ASEC has
  234,133 blank `ssi_reported` cells but a complete measured `SSI_VAL` for all
  of them (including 186,207 people age 15 or older). The first selected-
  household SSI simulation batch therefore raises `Unable to set value for
  variable "ssi_reported", as the input contains NaN values.` The bounded
  adapter must coalesce the already-reviewed ASEC/ACS reporter anchor, convert
  only the below-age-15 combined blank to zero, and leave the source `Frame`
  byte-unchanged; adult blanks and conflicting reporters remain refusals.
- Measured the other PolicyEngine copy-boundary structural-null universe
  exactly. All 91,032 blank `pre_subsidy_rent` rows are authority-valid ACS
  `TYPEHUGQ` 2/3 lineages: 45,510 clone-0, 45,510 clone-1, and 12 clone-2 rows.
  The 45,510 unique sources fan out to 45,498 two-role and 12 three-role live
  lineages, with person/household channel, clone role, and null tenure aligned
  exactly. A clone-0-only artifact rule would wrongly exclude 45,522 valid
  rows. Simulation batches preserve the whole-pool manifest but not its live
  counts, so they cannot self-authenticate against aggregate digests. The
  implementation will validate the full frame once, bind every authorized
  person/household/source lineage, and let a selected batch materialize zero
  only in its engine-copy when every blank row matches that prevalidated set.
- After both bounded adapters cleared the first SSI batch, PolicyEngine exposed
  the next exact dense blocker: `Unable to set value for variable
  "real_estate_taxes", as the input contains NaN values.` This is not another
  safe blanket-zero case. The candidate has 350,656 nulls, all on clone 0:
  every 108,073 ASEC native person (42,213 heads / 65,860 nonheads) and 242,583
  ACS native people (90,030 heads / 152,553 nonheads); every clone-positive
  value is finite. The producing `acs_rent` manifest already declares the
  archived joint `rent` + `real_estate_taxes` target sample, but the runtime
  fits and writes rent only. ASEC heads therefore genuinely lack their intended
  QRF output, while ACS `TAXAMT` structural absences need exact source-universe
  zeros and observed owner values must remain measured. The no-weakening root
  repair is in progress at that housing producer/native mapper; the engine-copy
  adapter will not guess or zero this mixed universe.
- Implemented the three requested post-transfer identity repairs without
  changing a signal band. The housing gap-fill authority now reconciles final
  physical-ACS assistance take-up to measured receipt, zeros positive finite
  rent only on ACS nonheads outside the authenticated group-quarters absence
  universe, preserves ASEC bytes, and hashes both dependencies and live
  outputs. The housing gate consumes that same lineage authority: only true
  `NaN` on ACS `TYPEHUGQ` 2/3 remains an allowed structural absence; infinity
  and materialized group-quarters rent still fail, and tenure categories are
  checked against the exact ASEC three-category and ACS four-category source
  domains. The focused housing/stacked/spine-blindness corridor is green.
- The late-producer registry now carries explicit whole-pool dependencies from
  final qualified tuition to the AOTC group and from final pregnancy to the
  WIC group. After independent recipient transfer, the AOTC operator restores
  all five source facts to exactly `qualified_tuition_expenses > 0`; the WIC
  operator reruns the pinned source derivation by stable person identity. Both
  preserve ASEC producer bytes and bind dependency/output digests. WIC's
  structural seed is cross-bound to the model seed and the source callback's
  canonical `POOL_RANDOM_SEED=0`; a noncanonical aggregate or execution seed
  fails closed. Registry v18 has 71 explicit edges. Focused verification is
  277 stacked-spine cases, 55 late-DAG/housing cases, and both reviewed
  spine-blindness checks, all green with focused Ruff.
- Completed a full exact null census of the PolicyEngine dataset input surface
  after the bounded SSI/rent adapters. Besides the separately adjudicated
  property-tax surface, only group-quarters tenure and the three legacy
  second-home inputs remain. Each second-home leaf has exactly 582,318 clone-0
  null tax units and 597,546 clone-positive values; every clone-positive value
  is bit/value zero. PolicyEngine declares each input's default as zero and a
  direct dataset probe raises `Unable to set value for variable
  "second_home_mortgage_balance", as the input contains NaN values.` The root
  source contract is therefore the existing primary-PUF rule: preserve the
  authenticated finite clone payload bit-exact and write exact zero on native
  clone 0, expanding that independently justified contract from seven to ten
  leaves while keeping the three all-default targets out of late QRF transfer.
- The 91,032 blank household tenure rows and 91,032 blank SPM-unit tenure rows
  are exactly the same ACS `TYPEHUGQ` 2/3 lineage universe as structural rent:
  45,510 clone-0, 45,510 clone-1, and 12 clone-2 rows, with no nonblank GQ
  tenure. Their source absence must remain intact. PolicyEngine owns the
  simulation defaults (`tenure_type=NONE`,
  `spm_unit_tenure_type=RENTER`) but refuses the `NaN` inputs. The bounded
  repair is therefore engine-copy-only under the already authenticated full-
  frame GQ lineage authority, including exact household/SPM identity sets
  carried into sparse batches; no source cell or persisted frame is rewritten.
- Accepted the property-tax producer repair and ten-leaf native-zero expansion
  after an independent source/receipt review. The immutable candidate H5 is
  3,239,263,159 bytes with SHA-256
  `eeea886afec72c4ec6e15d31358920416ea6892ef2dca6bb9a281dc1faf6231b`;
  its manifest SHA-256 is
  `c9ee554939790d854efea9d69897a40376d0c7ea49e40e3f76f268835ebd148a`.
  Every second-home leaf has 582,318 null native rows, 582,318 finite-zero
  clone-1 rows, and 15,228 finite-zero clone-2 rows. `real_estate_taxes` has
  350,656 native nulls but no clone nulls; its positive counts are 234,483,
  181,057, and 11,176 on roles 0/1/2 respectively, with no positive native
  nonhead. This supports the joint ASEC QRF + measured ACS source-domain root
  and exact native-zero contract, not an engine default or gate exception.
- Hardened the ACS property-tax mapper at `13dc0b34`: nonnumeric observed
  `TAXAMT` now fails at the mapper boundary, while renter/group-quarters
  structural zero no longer requires an irrelevant `ADJHSG`; owner amounts
  remain adjustment-bound. All ten focused property-tax cases and Ruff pass.
- Independent adapter/H5 review found three fail-closed holes and each now has
  a regression. `9ec67cd5` binds rent authority to the exact observed-null
  lineage set so a newly introduced GQ null cannot reuse a broader structural
  universe. `e524fdac` rejects clone-receipt version booleans, coerced counts,
  noncanonical count rules, and extra keys. `6d30b93b` applies that exact
  receipt validation at manifest-only readiness and cross-binds eligible
  households to the assembly receipt, so launcher preflight cannot defer a
  clone mismatch until full H5 loading.
- Independent whole-lane review found the inherited adapters were used for
  target/reform simulations but not the final H5 write. `29072fd5` factors the
  authenticated SSI/rent/tenure materialization into one engine-copy table
  path and routes the final writer through a copied Frame under the same full-
  support authority; the source Frame remains byte-exact. Behavioral copy and
  AST call-site regressions pass. `3d972d2f` advances the target-frame
  materializer identity to v12 so old checkpoints and transitively bound reform
  vectors cannot warm-hit across the new engine-input semantics.
- A first follow-up (`182a2f45`) incorrectly removed the three second-home
  degenerate exclusions. Independent candidate review proved every preserved
  clone payload is exactly zero, so `f2765b54` restores the reviewed exclusions
  without rewriting history. This is fail-closed: the gate passes today's
  justified all-zero leaves and will reject any exclusion whose future clone
  payload becomes nondefault. No threshold, formula, or weeks ownership choice
  changed.
- Three independent reviews now accept the property/native-zero and bounded
  adapter integrations. Focused clone-receipt, manifest/H5, sparse authority,
  final-write, ACS mapping, compiler/spec, and Ruff corridors are green. The
  separate untracked weeks ruling prompt was never staged or modified.
- Completed the actual post-producer health replay as read-only analysis over
  candidate-25. Reverified the immutable H5/manifest identities above, restored
  only their authenticated assembly/stack/clone receipts onto directly read
  fixed tables (the historical frozen checkpoint schedule correctly cannot
  masquerade as the current late-DAG schedule), and validated assembly plus
  full-clone attachment before replay. The reconstructed support has 1,970,973
  people, 865,460 households, 1,179,864 tax units, 868,956 SPM units, 875,642
  families, and 1,572,357 marital units.
- Replayed every repaired upstream root in memory with no artifact write:
  ten-leaf clone-0 structural projection, the joint ASEC/ACS property-tax
  producer, the pinned ACS predictor join, and the actual SCF wealth producer.
  Property tax finished with zero nulls, 453,778 positive person rows, and
  60,425 unique values. The ACS join matched all 1,736,840 support rows with
  zero unmatched rows/collisions and semantic SHA-256
  `c7723adc889fc655b46103426d21f6c74937434eff51e8f3e6025bdf60972b74`.
  The unchanged SCF wealth gate passed at bank/stock/bond nonzero shares
  0.3878991327/0.1128501657/0.0117176352.
- Audited the complete ACA dependency closure before simulation: its four
  roots resolve to 483 PolicyEngine input leaves, and after the producer replay
  there are **zero** nullable semantic inputs outside the exact bounded-copy
  authorities. The remaining nulls are only `ssi_reported` (495,738), GQ rent
  (91,032), GQ household tenure (91,032), and GQ SPM tenure (91,032), all on
  the previously authenticated adapter surfaces. The canonical empty omitted-
  leaf list has SHA-256
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- Compiled the production-equivalent target registry from Ledger facts SHA-256
  `b3c0835631a446eb96aa84d86f3ee962d15ca356174c7114db52974f1cacc080`
  with default target aging and the canonical congressional-district
  crosswalk: 32,843 target specs, one reviewed Medicaid substitution, and
  three ACA source tables of 51 states each. The real ACA source producer then
  completed all 35 bounded batches over 865,460 households in 1,608.14 seconds.
- The unchanged `health_input_signal` gate passes with no failures over all
  1,179,864 tax units. Both outputs have zero nulls:
  `takes_up_aca_if_eligible` has two values (45,520 true / 1,134,344 false),
  while `selected_marketplace_plan_benchmark_ratio` has 35,059 distinct values
  in the required `[0.5, 1.5]` support. The non-exclusive diagnostics among
  45,520 marketplace takers are 30,327 strictly below benchmark, 11,563
  strictly above, and 3,632 within the neutral `isclose` tolerance; the
  tolerance category overlaps the strict-side categories, so these counts are
  not a partition. None is outside support. The canonical 1,053-byte gate
  payload has SHA-256
  `fa4df7fa5d392bfcb4e5d43d914ab7d8c1e052f41ba20094fd8b2e996a2f2361`.
  This replay ran no pool/dense/release build and modified no candidate byte.
- Repository verification exposed one legitimate source-attestation recut,
  not a behavioral failure. The only seed-inventoried source changed since
  `b6599ff7` is `puf_support.py`, where `e524fdac`/`6d30b93b` hardened clone-
  receipt validation. Reviewed identities are now seed protocol
  `674b63ad...2e00`, compiled seed map `1063879c...efde`, US spec
  `7f4537db...01c9`, BE spec `018439ef...4e51`, UK spec
  `60a2604b...702a`, and minimal-loader vector `c324198d...de4b`. Re-pinned
  only the established five identity/evidence surfaces; no YAML, schema, seed
  site, owner, RNG, or runtime semantics changed, and the arbitrary checkpoint
  fixture remains unchanged. The focused 38-case compiler/coverage/loader/live-
  binding corridor passes, as do the US bundle generator check, coverage at
  41,523/41,523 fields plus 41/41 inventory checks, focused Ruff, and diff
  hygiene.
- Ran all five pytest package shards from a clean committed source state. The
  calibrate shard passed 203 tests; data passed 322 with 2 skipped; fit passed
  93; and frame passed 295 with 36 skipped. The first complete build shard
  passed 6,616 with 45 skipped and exposed exactly 31 stale-fixture failures:
  two ACS fixtures omitted newly required `TYPEHUGQ`, six L0 export fixtures
  omitted newly required `real_estate_taxes`, 21 shared late-transfer fixtures
  omitted the now-required education/WIC structural receipts, and two clone
  tests expected the older generic error after validation became deliberately
  version-first. There were no errors.
- Repaired each fixture-only cluster without changing production behavior or a
  gate. `55dcce8d` adds an occupied-unit `TYPEHUGQ` to the ACS fixture;
  `e125a207` adds nonconstant head-carried property tax to the L0 fixture;
  `e79ad178` creates canonical signed education/WIC structural receipts,
  live-bound when a frame exists; and `e98c8398` matches the intentional
  clone-version error precedence. The complete ACS and L0 files pass 5 and 49
  tests respectively; 14 targeted late-receipt/clone cases and an independent
  five-case representative rerun pass; focused Ruff and diff hygiene are
  green. The complete build-shard result from that committed state is recorded
  next.
- Reran the complete build shard from committed checkpoint `9c25d56f`: 6,647
  passed, 45 skipped, 0 failed, and 0 errors in 3,439.43 seconds. Combined with
  the fresh calibrate/data/fit/frame shards above, repository-wide pytest is
  7,560 passed and 83 skipped across all five package shards. No test was
  omitted because of a failure retry.
- Final repository Ruff passes. `tools/ci_test_groups.py --verify` reports 314
  tracked test files and `verification=ok`; `tools/spec_engine_coverage.py
  --check` reports 41,523/41,523 configuration fields and 41/41 inventory
  checks; and `tools/generate_us_bundle_from_constants.py --check` passes at US
  spec SHA-256
  `7f4537db123094c556d09bd3a1130940cbdfe351359690b75f88e0afa25101c9`.
  `git diff --check` is green. The tracked tree is clean; the separate untracked
  weeks-ruling note remains untouched and excluded from this lane.
- Wrote the final 2026-08-30 verdict report at `ce643527`. It contains the
  required per-red root/fix/blocker table, the exact 5/6 archived-model status,
  the open Max ruling, the read-only health replay, and the precise
  current-source rebuild/certification sequence. Its blocked verdict does not
  claim that candidate-25 was repaired or certified in place.

### Next

No further lane-local work is authorized. Max must first rule on stacked
`weeks_worked` ownership; any implementation must preserve gate 9480 and recut
affected identities. Max must separately lift the no-build hold before a new
current-source candidate can be built. The exact raw-stage pool, dense-release,
six-model, certification, and preflight sequence is in `out.md`. Candidate-25
must not be resumed or modified. The separate untracked ruling note was never
edited or staged and is not part of this lane.

---

> **Historical sweep state below.** It was complete at `2422669e`; the
> continuation state above is current for this lane.

## State

Complete on 2026-08-29. The immutable candidate-25 evidence proves that the
farm-rent failure is a writer defect, not channel-attribution drift, clone
fan-out, or a gate defect. The stacked primary PUF producer correctly owns
clone-positive PUF-support rows, but the generic post-PUF late producer treats
every clone-0 row as an authorized recipient and predicts
`farm_rent_income` over both physical ACS and ASEC native rows. The same
ownership mismatch affects six other source-unobserved PUF-detail leaves and
would trip the next strict gate one build at a time. The repair makes the
primary PUF stage explicitly materialize structural zero on native rows for
all seven leaves, retain and validate clone-positive payloads, exclude those
whole-pool-complete leaves from predictive late transfer, and leave every gate
threshold intact. That root repair and an executable complete gate ledger are
now implemented. The seven writer surfaces and all six affected gate modules
have focused stacked regressions. A first full-suite pass exposed and the lane
has now recut every closed compiler-coverage identity affected by the smaller
producer graph. The latest restart reached 922 passing cases before exposing
the loader's one resolved-seed-protocol semantic-hash golden. That exact
vector is now recut and its full loader/schema corridor passes. The clean
repository-wide suite, Ruff, and CI test-file partition checks are green. The
complete receipts, roster, history, changed-file inventory, and verification
handoff are in `out.md`.

The pool, sibling manifests/gates, and release logs under
`/Users/maxghenis/PolicyEngine/_buildo-runtime/out/candidate-25/` are evidence
only: they were not modified or rebuilt. No pool/release artifact, launchd job,
publication, push, or PR was performed. The completed final handoff is
`out.md`, beginning with `SWEEP-COMPLETE`.

## Done

- Read `CLAUDE.md`; recorded the flat-test rule, PR-CI/certification boundary,
  required full-suite and Ruff commands, and root-journal history convention.
- Read the GitNexus debugging and CLI workflows. The local CLI reports that
  this repository is not indexed; no index was generated because doing so
  would create unrelated repository/global state. The execution and producer
  trace will instead be proved directly from source, tests, HDF data, and the
  authenticated manifest receipts.
- Confirmed a clean `stacked-dense-gate-sweep` worktree at lane base
  `7d44c0b5` before starting.
- Identified the inherited `PROGRESS.md`, `FINAL_REPORT.md`, and `out.md` as
  historical lane journals; this section is the current lane state.
- Verified the immutable manifest and HDF byte-for-byte against their sibling
  SHA-256 receipt files. The current loader correctly refuses to authenticate
  this older candidate because its frozen primary-QRF worker binding differs
  from current source; after that expected boundary, all measurements below
  were made by fixed-table, read-only HDF access with inherited household
  importance weights reconstructed exactly.
- Measured `farm_rent_income != 0` on the base-support operator role:
  5,314 of 964,699 clone-0 people, or 0.550845% unweighted and 0.554078%
  weighted (893,122.0409190694 / 161,190,788.52395308). The signal contains
  3,125 positive and 2,189 negative rows, a weighted total of
  5,573,148,282.564434, and a weighted absolute total of
  14,861,079,373.331043.
- Split the contamination by physical origin: 647 / 108,073 ASEC rows carry
  501,191.0979286348 / 81,353,165.66410413 weight (0.616068%), while
  4,667 / 856,626 ACS rows carry 391,930.9429904348 /
  79,837,622.85984892 weight (0.490910%). Every flagged row has clone index
  zero and consistent person/household physical channel, source ID, source
  row, spine ID, and clone lineage. The canonical flagged-row receipt SHA-256
  is `90385859bb275ac6394eb7487dd20e4bdf684779127e0cf74bdeb1119b0797e5`.
- Rejected clone fan-out as the mechanism: all 5,314 native rows have a clone-1
  counterpart, but 5,236 counterparts are zero and only 11 values are
  bit-equal. Rejected a gate-column bug because `support_role_series`
  intentionally maps clone zero to the base-support operator role and 647
  physically ASEC-native rows are genuinely contaminated.
- Traced the final producer in the manifest to
  `transfer:person/puf_tax_itemization__batch_3`: the target receipt records
  1,006,274 `puf_clone` producer rows and exactly 964,699 authorized/imputed
  native recipients. Its checkpoint raw-draw bits equal every final clone-0
  cell and every flagged nonzero cell, with raw-draw SHA-256
  `67831fe4ac1269bfe1ffa00faf26034e3f10dde7df5333e4673b7c1e6005ed3d`.
  This confirms mechanism (a), a generic late-writer scope bug.
- Replayed the source-zero support gates over the real final pool. In addition
  to farm rent, predictive late transfer contaminates `domestic_production_ald`
  (2,095 native tax units), `educator_expense` (20,371 native people),
  `investment_income_elected_form_4952` (1,657), `salt_refund_income`
  (67,310), `long_term_capital_gains_on_collectibles` (601), and
  `unrecaptured_section_1250_gain` (2,960). These are correct contamination
  sentinels and will not be weakened or skipped.
- Established the shared source contract for the seven leaves from their
  runtime gates and `source_stages.json`: they are PUF tax-detail support only
  and therefore structural zero on the native operator role. Other PUF-derived
  leaves are not being generalized into this rule because some intentionally
  use late native-row models.
- Reconstructed #794 precisely. It did enumerate farm business at the release
  call site, but grouped it with the six related gates as "intentionally
  unchanged" after a static role-semantics review. It replayed only repaired
  gates, never executed that unchanged group against the final pool, never
  traced their assertions to the later generic writer receipts, and had no
  executable roster-to-test ledger. The new sweep will bind the actual release
  call roster to a reviewed semantic ledger and real-pool verdict for every
  classified gate.
- Declared the exact seven PUF-only/native-zero outputs once in `puf_support`.
  The primary stacked PUF stage now refuses pre-materialized native cells,
  proves every clone-positive value finite, records the payload digest, writes
  exact zero only to clone-0 rows, verifies clone-positive bytes unchanged,
  and emits a target-level receipt for both person and tax-unit grains.
- Promoted those seven primary outputs from `puf_clone` to `whole_pool`
  ownership, removed them from post-PUF predictive transfer, and advanced the
  late registry to schema 17 and primary execution config to schema 5. The
  bounded late schedule is now 18 groups / 63 targets; the primary output
  inventory remains 65 and the terminal 134-variable diagnostic surface is
  unchanged.
- Regenerated and validated the typed US bundle at spec SHA-256
  `94153c2d9bb5ebb6b2b604cc7a514d11a8f41ed1a1b8dbdaf24ca77ac973569f`.
  Its schema carries the seven new universe doctrines, and its generator pins
  the 37-node / 69-edge / 220-compiled-output graph plus the exact schedule,
  overlap-ownership, surface, and authority digests.
- Added writer regressions that cover every declared leaf, prove native-zero
  materialization and bit-exact PUF payload preservation, refuse preexisting
  native contamination leaf by leaf, and exercise the integrated primary-PUF
  callback. The prior educator-expense test that required predictive native
  transfer now uses `qualified_tuition_expenses`, an intentionally modeled
  late leaf, so it no longer enshrines the defect.
- Focused writer/DAG tests pass through the full stacked executor, and focused
  bundle/compiler/legacy-adapter tests pass after source-derived identity
  regeneration. Focused Ruff is green.
- Added an AST-backed inventory contract over every direct release-gate call.
  It requires exact call counts and defining modules, divides the complete
  roster into reviewed support/source-sensitive and out-of-class sets, and
  requires semantic-marker discovery plus explicit source-presence cases to
  equal the reviewed sensitive roster. Future direct calls cannot silently
  bypass the sweep.
- Added assembled ASEC+ACS stacked-frame regressions to all six gate modules
  affected by the seven repaired leaves. Every gate accepts native structural
  zero with nonzero clone-positive PUF detail, and every gate still rejects a
  genuinely misplaced nonzero on either a physical ASEC-native or ACS-native
  clone-0 row. The capital-details regression checks each of its two leaves
  independently.
- The executable roster test passes. The six gate files pass together (120
  cases), focused Ruff passes, and `tools/ci_test_groups.py --verify` reports
  all 313 tracked flat test files assigned with `verification=ok`.
- Ran the full suite until it exposed the complete first red cluster, then
  stopped at 852 passed / 3 failed / 6 errors to repair it before restarting.
  Every failure was a stale closed identity derived from the intentional
  producer-graph contraction: field-usage totals/pointer claims, the
  generation-0 inventory vector, the committed coverage report, and the BE/UK
  envelopes that share the source-attested `legacy-v1` seed protocol.
- Re-derived all affected identities from the compiled bundle. The coverage
  ledger now proves 41,347/41,347 fields consumed (31,583 authored + 9,764
  resolved), and the inventory proves 41/41 items over 37 producer nodes, 69
  edges, 220 compiled outputs, 18 late groups, and 63 late targets. The
  committed coverage report is regenerated rather than hand-edited.
- Re-pinned BE and UK to their new resolved envelope hashes. Their authored
  resources are unchanged; the only moving resolved binding is the shared
  seed protocol, whose attested kernel inventory includes the changed
  `puf_support` source. Also refreshed the constants-adapter US spec binding.
- The full field-usage, inventory, coverage-tool, and country-bundle focused
  corridor passes; the coverage generator `--check`, the multispine adapter
  identity case, and focused Ruff all pass.
- A reverse-pin sweep found the remaining downstream fixture and plan-lock
  counts before the restarted full suite reached them. Updated typed closure,
  plan-lock, HDF/publication receipts, and the live-producer fixture to the
  37-node / 18-group / 63-target graph.
- Strengthened the transfer partition test around the new ownership boundary:
  48 early transfer targets + 63 late transfer targets + 7 primary-owned
  native-zero outputs exactly equal the unchanged 118-target full declaration;
  the late surface remains 36 PUF-produced + 29 source-produced - 2 overlaps.
  Focused typed/plan/DAG, partition, tool-entrypoint, and HDF tests pass.
- The next full run passed 894 cases before finding one final static owner-count
  assertion: the `acs_qrf_fit_draw` seed site has 19 owners after removal of
  batch 5, not 20. Replaced the numeric assertion with an exact typed owner-set
  proof derived from the canonical transfer-group registry (one pipeline owner
  plus every live transfer producer). The full identity-contract file and Ruff
  pass.
- The following full restart passed 922 cases before finding the one remaining
  shared identity: the rich-minimal loader golden includes the resolved
  `legacy-v1` seed protocol. That protocol directly attests the changed
  `puf_support` kernel source, so its implementation receipt—and therefore the
  fixture spec hash—moved from `9f5b3727...` to `6ab67805...` even though the
  fixture itself does not author US imputation resources. The closed schema
  catalog also changed, but its grammar receipt is carried by the bundle lock,
  not this semantic envelope. Recut the exact golden without weakening its
  surface-separation assertions; all 33 loader, schema,
  imputation-semantics, and stacked-authority cases pass.
- The final literal full-suite run completed green from zero: 7,485 passed,
  83 skipped, and 2,354 warnings in 3,602.68 seconds (1:00:02). The warnings
  are pre-existing numerical, pandas fragmentation/chained-assignment, and
  sparse-tensor diagnostics; there were no failures or errors.
- Final `uv run ruff check .` reports `All checks passed!`.
- Final `tools/ci_test_groups.py --verify` reports 313 tracked test files and
  `verification=ok`.
- Wrote the final handoff to `out.md`; its literal first line is
  `SWEEP-COMPLETE`, and it includes the immutable receipts, full gate roster,
  #794 miss analysis, changed files, and test evidence.

## Next

No lane work remains. The dispatcher can review and push the committed branch;
this lane did not push or open a PR.

---

> **Historical material below.** The remaining sections predate this lane and
> must not be read as current state.

# ACS predictor release join

> **Historical note (2026-08-28).** This journal describes the
> `acs-predictor-release-join` lane as of 2026-08-27. The branch has since
> been merged into the `stacked-release-fix-train` integration branch
> together with the #794 gate-alignment and #798/#799 pregnancy/prior-year
> fixes, with spec envelope digests and coverage evidence regenerated over
> the union tree. Treat the "State"/"Next" sections below as history;
> check git/GitHub for current truth.

## State

Complete on 2026-08-27. The owner-approved release-time join from stacked-pool
ACS source lineage to the SHA-pinned 2024 one-year ACS person/household zips is
implemented, receipted, real-pool exercised, and fully verified. It populates
the six archived donor models' CPS-named predictors through reviewed
native-ACS crosswalks with strict hash, lineage, collision, totality, universe,
and clone-fan-out contracts. Model selection logic and every gate threshold
remain unchanged. The completed evidence and handoff are in `out.md`. No
network access, pool build, release build, publication, push, retraining,
threshold change, or launcher-contract edit occurred.

## Done

- Read `CLAUDE.md` and the prior weeksgate report's six owner-ruling items with
  their release-call and model-consumer evidence.
- Confirmed the requested branch `acs-predictor-release-join` is clean at
  `606cbd69`, based on `stacked-release-gate-alignment`.
- Read the GitNexus exploration and impact-analysis workflows. This workspace
  exposes neither GitNexus repository resources nor query tools, so the same
  call/dependency analysis will be performed directly from source and tests.
- Recorded the required source zips and SHA-256 pins, strict exact/total join
  contract, explicit crosswalk and receipt requirements, and verification
  boundary.
- Proved that `person_source_id` is not a reversible ACS key: ACS people are
  sorted by `(SERIALNO, SPORDER)`, receive a zero-based raw spine ID, and then
  receive a collision-dependent assembly offset. The pool retains the raw
  spine ID, `source_row_id`, `source_person_id`, household `SERIALNO`, and clone
  metadata, so the release join will use the retained semantic
  `(SERIALNO, integral SPORDER)` key and treat `person_source_id` only as the
  one-to-many clone fan-out identity.
- Audited the supplied candidate pool read-only: 856,626 distinct ACS source
  people expand to 1,736,840 rows (856,626 clone 0, 856,626 clone 1, and
  23,588 clone 2), with no duplicate `(person_source_id, clone_index)` pair.
  Every ACS row agrees with its raw spine/source lineage, and all selected
  people match the pinned raw person archive exactly.
- Verified both local archives against the charter pins. The person archive
  has 3,422,888 unique `(SERIALNO, SPORDER)` rows and no household orphans;
  the household archive has 1,631,969 unique serials, including 1,531,614
  occupied records. Both contain every requested native predictor.
- Established the disability universes from the pinned archive and the
  archived repository mapping: DEAR/DEYE are complete at every age;
  DREM/DPHY/DDRS are asked from age 5; DOUT from age 15; native code 1 is the
  consumer's difficulty bin and code 2 (plus an age-valid universe blank) is
  its non-difficulty bin.
- Established the consumed race/Hispanic bins: both SCF models distinguish
  White, Black, Asian, Hispanic, and Other; ORG distinguishes Hispanic,
  non-Hispanic White, non-Hispanic Black, and Other. `RAC1P`/`HISP` can map
  exactly to those bins without inventing detailed CPS combinations.
- Recovered the complete 2024 Census detailed-occupation-to-`POCCU2` consumed
  grouping from the native ASEC relationship and confirmed that ACS `OCCP`
  uses the same detailed codes. `PEIOOCC` is therefore a direct carry, while
  `POCCU2` will use an explicit reviewed 53-bin table; blank out-of-universe
  occupation maps to code 0, military to 52, and code 9920 to 53.
- Confirmed ACS `TEN` maps to the SPM vehicle model's three consumed tenure
  bins (mortgaged owner, outright owner, non-owner); no-cash-rent and verified
  group-quarters blanks belong to the non-owner bin. Confirmed the SSI model's
  `SSI_VAL` use is only the `> 0` reporter anchor and that native ACS `SSIP` is
  already carried as harmonized `ssi_reported`, observed exactly from age 15.
- Added the dedicated `acs_release_predictors` release boundary. It verifies
  the two canonical archive pins before opening either zip, streams only
  selected households, validates exact archive members and headers, rejects
  raw/person/clone collisions, binds retained pool lineage to
  `(SERIALNO, SPORDER)`, requires total one-to-one source-person matching, and
  fans mapped values to clones only through `person_source_id`.
- Added explicit disability, race/Hispanic, 530-code occupation, and tenure
  tables. A canonical crosswalk payload is pinned at SHA-256
  `1d4906242e9c73e31b3283659e5cad8242b8cbc42914ab6fa59547a10c8770e9`
  and rides the JSON-ready join receipt with per-model/per-predictor
  ASEC-native, ACS-joined, and still-null counts.
- Preserved CPS disability universe semantics (`-1` below the question age)
  and the ACS occupation universe. Blank `PEIOOCC` uses the CPS NIU sentinel
  `-1`; blank `POCCU2` remains 0 through age 15 and maps to the consumed
  no-occupation code 53 only from age 16. This explicitly preserves the
  one-year ACS/CPS source-universe gap instead of assigning every ACS
  15-year-old a never-worked status without source evidence. The explicit
  occupation table covers every one of the 530 codes in the pinned ACS person
  archive and every consumed POCCU2 bin.
- Changed the SSI-disability reporter read, without source routing, to
  row-wise coalesce measured ASEC `SSI_VAL` with harmonized native ACS
  `ssi_reported`. Adult blanks and conflicting dual reporters fail; genuine
  below-age-15 ACS blanks remain null in the frame and become false only for
  the consumer's `> 0` predicate.
- Hardened the join after independent crosswalk review: raw ACS `SSIP` and
  `ADJINC` now travel through the pinned join and must agree exactly with every
  native clone-0 `ssi_reported` value under the established adjusted-dollar
  formula. Raw `ESR`/`OCCP` must obey their exact age-16 universes, and all
  ASEC predictor receipt cells must be numeric and finite with complete,
  nonnegative `SSI_VAL`.
- Updated the SSI signal diagnostic to use the same row-wise reporter coalesce
  as the model consumer, while retaining the archived native-role anchor
  scope. A lost positive ACS-native reporter can therefore no longer evade the
  release gate merely because `SSI_VAL` is null on physical ACS rows.
- Added focused tests for crosswalk identity/all consumed bins, exact join and
  clone invariance, ASEC byte preservation, receipt contents, missing joins,
  raw and source-identity collisions, hash refusal, no-ACS identity, and SSI
  coalescing/universe refusal. Coverage now also fixes the age-15 occupation
  gap, malformed ESR refusal, malformed ASEC SSI refusal, raw SSI attestation,
  and gate-side ACS reporter preservation. The complete join, SSI, and
  source-blindness test files pass together, and focused Ruff is green.

- The release CLI now accepts the person/household zip and lowercase 64-hex
  SHA-256 options as an all-or-none set. It invokes the authenticated join
  after the last unrelated native-input gate and before SCF wealth, therefore
  before all six archived donor-model stages, then carries the complete join
  receipt into both `build_manifest.json` and `release_manifest.json`.
- Added parser refusal tests, a source-order contract over all six model calls,
  an end-to-end mocked main corridor that verifies the exact four join
  arguments and runtime ordering, an AST contract that binds the saved receipt
  to the sole manifest call, and JSON round-trip assertions for both manifests.
  Focused Ruff, five parser/order/manifest cases, and all six parametrized main
  corridor cases pass.
- Exercised the hardened join read-only on the complete supplied candidate.
  The 3,239,263,147-byte H5 matches its frozen manifest SHA-256
  `871b7e6467675a1e9475b54fd1baf64c53c0f75a3258b8357303a8df0d53642d`.
  The current official loader refuses that older candidate before H5 loading
  because its archived primary-QRF worker binding predates this branch's
  execution identity; this is an existing candidate/code-version mismatch.
  Loading those independently manifest-hash-verified bytes with their frozen
  assembly receipt allowed the join boundary itself to be tested without
  writing an artifact.
- The real join passed every source, raw-key, universe, SSI-attestation,
  totality, collision, and clone-fan-out check: 856,626 unique ACS source
  people matched 856,626 raw people in 382,903 households and populated
  1,736,840 support rows (856,626 each at clone indices 0 and 1, plus 23,588
  at clone index 2). Every CPS-named predictor consumed by the six models has
  234,133 valid ASEC-native and 1,736,840 ACS-joined cells with zero nulls.
  The logical SSI reporter anchor has 234,133 ASEC cells, 1,475,235 observed
  ACS cells, and exactly 261,605 preserved child-universe null support rows.
- The first real-data attempt exposed fixed-format HDF's expected object dtype
  for mixed-source columns. Tightened the ASEC validator to inspect each cell,
  accepting object-wrapped real numbers while still refusing strings,
  nonfinite values, nulls, and negative SSI. A focused H5-shape regression and
  all 15 join tests pass before the successful full-pool rerun.
- Added `changelog.d/acs-release-predictor-join.fixed.md`, describing the
  pinned release join, reviewed mappings, fail-closed lineage, dual-manifest
  receipts, and unchanged model/gate behavior.
- Repository Ruff passes, and the CI inventory verifier reports 310 tracked
  tests with `verification=ok`. Four complete pytest shards pass in separate
  processes: frame 295 passed/36 skipped, fit 93 passed, calibrate 203 passed,
  and data 318 passed/2 skipped.
- The first complete build-shard process reached 100% with 6,575 passed and 45
  skipped, plus five failures and six fixture errors. All eleven were the same
  expected source-attestation drift: `ssi_disability_criteria.py` belongs to
  both the direct and QRF seed-kernel inventories, so this task's runtime edit
  moved the seed protocol, compiled US seed map, every country spec identity,
  the minimal loader golden, and the generated coverage evidence. No ACS join,
  release CLI, manifest, archived-model behavior, or gate test failed.
- Applied the repository's established five-file source-identity repin only:
  seed protocol `59a098f9...31d8b`, US seed map `ce3850d8...e42ab`, US spec
  `16b7d5e6...dca38`, UK spec `2f921e4c...33a62`, BE spec
  `c87a0012...34ba`, and minimal-loader golden `b4946105...f2af`; regenerated
  `docs/evidence/spec-engine/us-f0-coverage.json`. All 25 affected cases and
  focused Ruff pass. The US bundle generator `--check` passes at the new spec
  identity, and coverage `--check` passes at 42,122/42,122 fields and 41/41
  inventory checks.
- Re-ran the complete build shard after the reviewed repin: 6,586 passed and
  45 skipped, with exit code 0. Re-ran final repository Ruff, the 310-file CI
  inventory verifier, both retained spec `--check` commands, and
  `git diff --check`; all pass. Wrote the required final report to `out.md`.

## Next

- No work remains in this lane. The dispatcher owns rebasing and the launcher
  contract update. A future authorized build must produce a pool whose current
  source-attested worker identity passes the official release loader; the
  supplied older candidate is useful join evidence but cannot be promoted.

# Weeksgate: stacked release gates and integer-week provenance

## State

Complete on 2026-08-27. Real-pool provenance has refuted the proposed
post-transfer amount-mapping mechanism: every fractional week is an ACS-origin
non-native clone prediction outside the calibration's clone-0 recipient scope.
The source codec, weeks-gate architecture, source-scope, clone-layout, and
stable-identity repairs are implemented and focused-tested. The complete
release-call roster is classified; six archived-model input assumptions require
owner rulings and are deliberately reported instead of guessed. Repository-wide
Ruff, the CI inventory verifier, and all five full pytest shards pass in their
required independent processes. The completed provenance, audit, verification,
judgment calls, and host-owned checkpoint-rerun consequence are in `out.md`.
No network access, artifact build, publication, push, pool build, or release
build is in scope.

## Done

- Read `CLAUDE.md` and the GitNexus debugging workflow.
- Confirmed branch `stacked-release-gate-alignment` is clean at `4f453746`.
- Confirmed the local GitNexus CLI is installed but the repository is not yet
  indexed. Its offline analyzer parsed the repository but could not register
  the index because the sandbox forbids writes to `~/.gitnexus`; the generated
  local index was moved out of the worktree to `/private/tmp`.
- Recorded the four requested workstreams: fractional-week provenance and PUF
  misclassification; integer-support calibration repair; stacked/legacy weeks
  gate alignment; and the full release-side gate archaeology sweep.
- Recorded the required verification boundary: repository Ruff plus one pytest
  process per shard, with no pool/release builds.
- Read the fixed-format HDF5 blocks directly and classified all 369 noninteger
  `weeks_unemployed` rows: 360 are ACS clone 1 (355 UC=0, 5 UC>0) and 9 are ACS
  clone 2 (all UC=0); all are positive, all 369 values are distinct, and the
  exact range is 1.0003521955067698--37.796501228614694.
- Confirmed zero nonintegers on ASEC rows and ACS clone 0. The receipted
  calibration covers exactly the 856,626 ACS clone-0 rows, maps 8,419 carrier
  amounts onto observed ASEC support with zero donor-support violations, and
  records QED 0.5882352941176471 to 0.0.
- Reproduced the 5,218-row false "PUF" classification: the legacy role helper
  calls every clone index above zero `puf_tax_detail`, regardless of raw source
  channel. The rows are all ACS-origin clones: 4,733 integer clone-1 rows, 355
  fractional clone-1 rows, 121 integer clone-2 rows, and 9 fractional clone-2
  rows with nonzero weeks while UC is nonpositive.
- Traced the actual fractional mechanism to the ACS transfer target codec:
  PolicyEngine-US declares `weeks_unemployed` as physical `float`, so the
  generic QRF path treats it as continuous even though its reviewed source
  contract is integer-supported. The later calibration repairs clone 0 only.
- Bound every final fractional value bit-for-bit to the late-transfer target
  bank. Its raw QRF draw contains 711 nonintegers: 342 ACS clone 0, 360 clone 1,
  and 9 clone 2. Post-transfer calibration changes 13,417 clone-0 rows and
  eliminates all 342 clone-0 fractions; the 369 out-of-scope clone fractions
  pass through unchanged.
- Added `weeks_unemployed` to the ACS transfer's authority-bound discrete
  numeric target registry. The existing codec now snaps every prediction to
  actual observed ASEC donor support, and the execution-contract identity
  receipts the policy alongside the two mortgage-year targets.
- Added a focused ACS-transfer regression proving weeks predictions retain
  observed integer support and the execution contract declares the target.
- Regenerated the checked-in US imputation authority so
  `transfer_execution.discrete_numeric_targets` includes `weeks_unemployed`.
  The generator's compile and byte-staleness checks pass at bundle spec SHA
  `821d5838da3ac368170e61e017f1a72648f93e8a011aa40e33b8c2b4b14511f3`
  at that source-fix step; the later runtime/seed identity repin below
  supersedes this intermediate digest. The spec-bundle and imputation-
  semantics suites pass.
- Passed the complete ACS-transfer test file (65 tests), the complete
  post-transfer calibration receipt-contract file (47 tests), focused Ruff,
  and `git diff --check` using the prebuilt `.venv` directly. A task-local
  `UV_CACHE_DIR` later allowed the required `uv run --no-sync` commands to run
  against that same prebuilt environment without accessing `~/.cache/uv`.
- Modernized the weeks summary/gate to derive its roster from actual assembled
  source channels, while retaining the legacy ASEC/PUF role path. The ASEC
  source-validity scope, direct native-clone reconciliation scope, and reviewed
  UC-constraint scope are now distinct and explicitly receipted in details.
- Kept all four plausibility-band tuples and every numeric threshold unchanged;
  non-ASEC assembled channels use the unchanged legacy recipient band.
- Added stacked ASEC+ACS and legacy ASEC+PUF fixtures covering roster detection,
  raw-source scoping, native reconciliation, and UC constraint ownership. The
  complete weeks file passes (26 passed, 1 skipped) with focused Ruff.
- Replayed the updated gate over the supplied pool's exact live arrays and
  weights. It now reports 234,133 valid ASEC source rows, 108,073 exact native
  reconciliation rows, 982,686 UC-constrained rows, zero source/UC failures,
  both unchanged channel bands passing, and only the genuine 369 nonintegers.
- Added a centralized provenance-owner API that distinguishes validated
  physical source channels from legacy clone-operator roles. The weeks gate
  now consumes that API rather than reading provenance columns directly, and
  both repository source-blindness tripwires pass alongside the stacked and
  legacy provenance/weekly-signal suites.
- Made WIC's deterministic draw key prefer the assembly-unique
  `person_source_id` on multispine frames, before the source-local raw identity
  triple. Distinct ASEC/ACS records can no longer collide when their vintages
  align, while all support clones of one assembled person retain the same draw
  and the legacy key order remains unchanged.
- Completed the release-tool call-roster audit. It found unambiguous physical
  ASEC scoping repairs in SSI take-up, workers' compensation, alimony,
  retirement contributions/distributions, and Medicare; clone-2 layout fixes
  in Head Start, voluntary filing, and prior-year income; and a stable-key fix
  in WIC. Archived ASEC-only predictor assumptions in SSI disability, SCF
  wealth, SCF auto loans, and SIPP vehicles require explicit model-owner
  rulings and will be reported rather than guessed.
- Reworked the assembled Head Start and voluntary-filing receiver layouts to
  key by assembly-unique source ID plus explicit clone index, accept clone 2
  and later, reject duplicate source/clone rows, choose clone 0 (or the lowest
  surviving clone) deterministically, and fan one source-level decision to all
  clones. Their legacy role-only duplicate contract remains unchanged.
- Replaced occurrence-pair clone diagnostics in voluntary filing and
  prior-year income with all-clone grouping on assembled source IDs, so a
  clone-2-only divergence is now detected. Focused tests and Ruff passed for
  all three module/test pairs.
- Scoped Medicare and retirement release diagnostics to physical ASEC source
  rows, separating raw-source validity from native direct-carry reconciliation
  where transferred clones intentionally differ. Kept the producer kernels
  origin-blind: the authenticated-pool release path skips those producers, and
  indirect physical-source routing would violate the repository's population-
  operator boundary. Their 60 focused module/source-blindness tests and Ruff
  pass after that review correction.
- Scoped alimony and workers' compensation raw validity to every physical ASEC
  clone and exact source-carry checks to physical ASEC native rows, leaving all
  clone-operator plausibility bands unchanged. Stacked ASEC+ACS and legacy
  ASEC+PUF fixtures pass (28 alimony and 21 workers' compensation tests).
- Changed SSI reporter-lineage capture to validate `SSI_VAL` only on physical
  ASEC rows and accept null ACS raw-source cells. Assignment remains source-
  blind: it consumes the source-ID set captured before L0, or obtains that set
  through the reporter helper when no explicit set is supplied. The complete
  SSI take-up file passes (71 tests).
- Fixed SSI-disability's non-fatal clone-divergence diagnostic to group every
  assembled clone by source person, so clone-2-only divergence is reported.
  The existing decision not to make divergence gate-fatal remains unchanged
  for an owner ruling; the complete focused file and source-blindness checks
  pass.
- Narrowed physical-channel resolution to a gate/reporter-only provenance API,
  removed its general runtime/PUF-support re-exports, and added a static exact-
  caller contract (including internal mask-helper callers). A future derive,
  impute, or wrapper use now fails the source-blindness suite instead of
  passing through indirection.
- Replayed the repaired release gates read-only against the supplied pool.
  Alimony, Medicare, retirement contributions/distributions, workers'
  compensation, and SSI reporter capture pass; the weeks gate now fails only
  on the genuine 369 fractional values. Prior-year income remains outside its
  unchanged availability band and WIC finds pregnant nonfemale rows, both
  genuine data/spec outcomes rather than stacked-layout archaeology.
- Completed an adversarial review of the repaired code and focused tests with
  no additional implementation defect found. It confirmed six owner-ruling
  items: SSI disability criteria, SCF wealth, SCF auto loans, SIPP vehicles,
  SIPP tips, and ORG wages/FLSA all consume ASEC-only archived predictors on a
  frame whose 1,736,840 physical ACS rows carry null source cells. ORG is
  guaranteed to fail its unchanged race/occupation bands; SIPP tips' unchanged
  tipped-occupation band passes while the ACS channel is dead.
- Passed repository-wide Ruff and the CI test-group inventory verifier. The
  calibrate, data, fit, and frame shards pass in four independent pytest
  processes.
- Corrected the reviewed WIC seed protocol to match the implemented assembled-
  multispine key precedence: assembly-unique `person_source_id` first, then the
  unchanged legacy raw/support/person fallbacks. An exact seed-grammar test now
  binds that order.
- Re-pinned the fail-closed spec-engine proof after adding one authored
  transfer-execution field and one resolved seed-protocol field: 42,122 total
  fields (32,352 authored and 9,770 resolved), complete exact-pointer claims,
  and all 41 inventory checks. Regenerated the committed coverage report and
  validated the final US spec SHA
  `5f44d96d45e9aabcea2d565ef063d68bfc0652df1b38b08aa31ce6896d15f371`.
- Verified in a detached `origin/main` worktree, using the same prebuilt venv,
  that the old BE, UK, and minimal-spec golden vectors still pass there. Their
  current repins therefore reflect this branch's attested runtime and seed-
  protocol changes rather than environment drift. All 102 tests in the eight
  directly affected spec-engine files pass; generated-bundle and coverage-
  report byte checks, focused Ruff, and `git diff --check` also pass.
- Ran the full build shard after that coherent spec repin. It reached 100% with
  exactly one failure and no errors: the multispine constants-adapter fixture
  still expected the former live US spec SHA. Updated only that live-binding
  expectation to the regenerated final SHA; the separate arbitrary checkpoint
  identity fixture remains deliberately unchanged.
- Passed the complete multispine-pool-tool file after that correction and
  committed the coherent fixture repin as `12a918ed`.
- Reran the entire build shard from zero in one process: 6,608 tests collected,
  100% reached, and pytest exited 0 with expected skips only. All five full
  package shards, repository-wide Ruff, generated-artifact checks, the spec
  coverage proof, the CI test inventory, and `git diff --check` are green.
- Wrote the final provenance tables, mechanism verdict, per-file rationale,
  exhaustive release-gate audit, owner-ruling list, verification evidence, and
  judgment calls to `out.md`.

## Next

- Host session: rerun `late_transfer -> simulated -> terminal-gates` from the
  candidate checkpoints because the discrete weeks codec changes pool content.
- Review the six archived-model owner rulings in `out.md`; do not reinterpret
  their missing ACS predictors through a gate-only threshold/scope change.

# Historical: gate-failed base-pool release lane

## State

Complete on 2026-08-26. Containment, opt-in carriage, and preflight surfacing
are implemented and fully verified. The implementation rejects both redundant
green-pool waivers and any release-manifest receipt that does not exactly match
the pool authenticated by preflight; the preflight's historically required
base/selection inputs and exit semantics are unchanged. No pool or release was
built, no artifact was published, and nothing was pushed.

## Done

- Confirmed the assigned branch and worktree.
- Recorded the v2 charter: close the legacy bare-H5 multispine bypass, add an
  explicit release-build opt-in, carry the authenticated red verdict, and
  surface it in publication preflight without making it an automatic
  publication failure.
- Confirmed that no network, artifact builds, publishing, or pushes are in
  scope.
- Traced the strict manifest loader, current stacked-only terminal-failure
  exception, H5 identity stamp, pool sidecar naming, legacy release arm,
  release manifests, and both preflight output modes.
- Reviewed the salvage branch's final source and test diff line by line. Its
  shared classifier/path-binding/receipt approach closes the bypass without
  changing either loader's contract and was retained with the subsequent
  coherence corrections recorded below.
- Completed the `simulation_ready` / `gate_failed` / loader consumer audit.
  Exact-k remains deliberately strict and head-to-head scoring remains the
  existing authenticated evidence exception.
- Identified report-only downstream caveats: stacked producer metadata still
  names only the k-ladder readiness consumer; red pool publication returns
  status 1 and stops shell chains; ACS-local derivatives keep a donor revision
  but do not project the nested red verdict; generic release consumers tolerate
  and ignore the additive receipt.
- Added a release/preflight-specific authenticated pool loader over the shared
  `require_simulation_ready` seam. The strict simulation-ready and existing
  scoring-only loader contracts remain unchanged.
- Closed the bare-H5 path by detecting either the canonical sibling manifest
  or the H5's stamped pool identity, requiring the sidecar, authenticating the
  publication triple, and binding it to the exact requested H5 path.
- Added `--allow-gate-failed-base-pool` only to the legacy `--base-h5` arm.
  It admits only a current authenticated stacked `gate_failed` pool, rejects a
  green or non-pool use, and never affects the exact-k arm.
- Added the self-contained `base_pool` receipt to both manifests, including
  status/readiness, immutable pool identities, flag use, gates JSON SHA-256,
  failure count/list, and the complete terminal verdict.
- Kept the static preflight inputs mandatory, authenticated its base identically,
  displayed red evidence prominently without changing its exit calculation,
  and required optional release-manifest carriage to match the authenticated
  receipt exactly.
- Hardened carried verdict normalization so nested pass/failure pairs and the
  aggregate verdict must be coherent and a red battery cannot report zero
  failures.
- Passed focused Ruff and the complete builder/H5/preflight test files after
  the containment changes.
- Passed the broader exact-k, launcher, release-contract, and publish-guard
  regression suites.
- Passed repository-wide Ruff and the CI test-group inventory verifier.
- Passed every pytest shard in its own process: build 6,545 passed / 45
  skipped; calibrate 203 passed; data 318 passed / 2 skipped; fit 93 passed;
  frame 295 passed / 36 skipped. Aggregate: 7,454 passed, 83 skipped.
- Confirmed `git diff --check` is clean and that no battery bounds,
  tolerances, plans, or terminal gate logic changed.
- Wrote the complete handoff, consumer audit, manifest schema, verification
  receipts, and commit inventory to `out.md`.

## Next

- Human review and merge of `release-from-gate-failed-pool`.
- Any later artifact operation remains separate: an operator must deliberately
  choose the red-pool flag, then run publication preflight and make the human
  publication decision. This lane performed none of those operations.

## Historical prior lane

The stacked-pool-to-release CD-vintage provenance lane previously maintained
this journal and completed before this work began. It authenticated and
applied household geography after source assembly, carried that authority
through checkpoint and publication identities, published verified CD-vintage
H5 attributes, and reached the unchanged release guard through the shared
fixed/table-aware reader. Its final verification was 7,241 passed, 77 skipped,
with repository-wide Ruff and anti-rot checks green. Full details remain at
commit `2263df36` (the parent of this lane's first journal commit).

The still-earlier PolicyEngine-US 1.819.0 lock-bump lane merged into
`origin/main` at `7b90bb18` on 2026-08-24; its final state remains at commit
`05d254aa` and its detailed receipts remain in the historical section of
`_LANE-NOTES.md`.
