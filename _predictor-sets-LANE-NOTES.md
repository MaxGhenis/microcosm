# Per-family predictor sets lane notes

Date: 2026-08-15
Branch baseline: `per-family-predictor-sets` at `f7173120`

## Scope and boundaries

- This lane implements predictor declaration/materialization machinery only. It does not run the owner's phase-2 f025 OOS quantile-loss sweep, calibrate draws, build a pipeline artifact, publish, push, or modify `PROGRESS.md`.
- Active stacked early and late transfers now pass explicit per-family predictor sets and fail closed on unknown families, missing mappings, missing declared columns, or target leakage. The no-set API path remains only for the explicitly retiring `--legacy-two-spine`/deprecated ACS multispine shims so their promised byte identity is unchanged.
- `post_draw_calibration: null` remains explicit in the lineage spec and is asserted by tests.

## Offline source checks

- ACS names were verified without network access against member `psam_pusa.csv` (286 columns) in `/Users/maxghenis/PolicyEngine/_worktrees/populace-acs-clone/inputs/acs_2024_1yr/afdc6d90c6e2f0bab365ed32d95ba4c4d8ac651162f46ac7861295b2dc469894/csv_pus.zip`. All 44 requested added/reviewed fields are present: `MAR`, `RELSHIPP`, `SCH*`, the six detailed disability items plus `DIS`, `MIL`, `MLP*`, `VPSP`, `DRAT*`, `HINS1`-`HINS7`, `HICOV`, `PRIVCOV`, `PUBCOV`, `ESR`, `COW`, `WKHP`, `WKL`, `WKWN`, `WRK`, `NATIVITY`, `ENG`, `CIT`, `POBP`, and `YOEP`.
- The 2024 PUMS header has no direct `VAP`/VA-payment amount. Available veteran/VA-adjacent evidence (`MIL`, `MLP*`, `VPSP`, `DRAT`, `DRATX`, and `HINS6`) is parsed and retained, while only the donor-comparable service-status signal is active in this PR.
- The locked `census_cps_{2022,2023,2024}.h5` inputs were inspected offline. Every active donor source exists across the pooled mapping surface. Raw 2022/2023 omit `A_EXPRRP`, but the pre-existing ASEC mapping derives its CPS relationship recode before the raw-stage checkpoint; 2024 carries it natively. No checkpoint schema file was widened.
- `A_HGA` education attainment, an English-proficiency counterpart, and a comparable VA service-connected-disability rating are absent from all three locked inputs. The intended blocks record them as `blocked-on-checkpoint-schema` instead of synthesizing them.
- Observed locked CPS domains are enforced: `PEDIS*={-1,1,2}`, `PEIO1COW={0..8}`, `MCARE={0,1,2}`, `PRCITSHP={1..5}`, `PEAFEVER={-1,1,2}`, `A_MJOCC={0..11}`, and `A_EXPRRP={1,2,3,4,5,7,8,9,10,11,12,13,14}`. NIU disability/class-of-worker/veteran sentinels remain `NaN`; raw and pre-carried canonical values outside their reviewed domains fail.

## Design decisions

- The participation family omits the disability block because `is_blind` and `is_disabled` are targets. Those draws lead the first bounded chain, so CHAMPVA/TRICARE/VA/IHS/Medicaid siblings can condition on them without target leakage. Both own-person and three-valued household-any veteran/service status are active, giving CHAMPVA dependents a sponsor-linked signal; work and own Medicare coverage remain additional base eligibility blocks.
- Income composition is split into earned, Social Security, retirement, and investment blocks. The itemization family keeps only earned income, and the numeric family omits retirement, because the excluded aggregates are constructed from those families' own donor targets. One execution-bound validator derives direct and combined source-component overlap from the live feature mappings and refuses the same leakage in runtime plans, spec conformance, and dashboard emission.
- `puma` and `county_fips` appear only as spec rows marked `pending: microcosm#696`; conformance excludes pending rows from live-column parity. Runtime geography materialization already present at the branch baseline was not changed by this lane.
- Late transfer uses the exact eight required `puf_predictor_*` inputs. Tax-unit targets use identity, person targets broadcast by tax-unit membership, and nonnested group targets select the tax unit of the first person in stable person-table order; the projection rule and source precedence are execution-contract bound.
- Census blanks remain native through parsing and predictor codecs. String columns are canonicalized at the ACS parse and transfer-result boundaries using the existing #672 serialization pattern.
- GitNexus indexing was unavailable because its registry path is outside the writable sandbox; review proceeded with repository-local search, cached artifacts, focused contracts, and independent read-only subagent audits.

## Validation

- No network access or pipeline build was used.
- Focused touched-module runs passed 1,023 tests: lineage/dashboard + ACS parse/plan/PUF/checkpoint (443), ACS transfer (99), multispine/stacked-spine (295), and late DAG/tool contracts (186).
- The final broader non-slow `microcosm-build` unit/contract suite passed 5,501 tests, with 30 skipped and the two tests marked `slow` deselected, across four deterministic test-file shards.
- `uv run ruff check .`, changed-file `ruff format --check`, staged and unstaged whitespace checks, and the clean-tree check pass after the local commits.

## Phase P acceptance gate (2026-08-16)

### Rebase and full-suite checkpoint

- Read the binding `Rollout — honest phases` section in
  `/Users/maxghenis/PolicyEngine/_worktrees/microcosm-spec-engine/docs/spec-engine.md`.
  Phase P requires this behavior-changing predictor-set branch to land under
  the #695 mirror only after its own out-of-sample/statistical acceptance gate,
  and before any baseline freeze.
- `git merge-base HEAD f7173120` returned
  `f71731202b6ff1f0dfa757b6b52aa87ff2a34161`; the branch was exactly three
  commits ahead, so no replay was needed and the branch still applies cleanly
  to the requested base.
- The full local US-extra environment suite passed with **6,336 passed, 68
  skipped** in 1,680.07 seconds. Command:
  `UV_CACHE_DIR=/private/tmp/microcosm-predictor-sets-uv-cache uv run --no-sync pytest`.
  This is 835 more passing tests than the prior 5,501-green floor and therefore
  does not drop the required count.
- No network access, Modal work, on-chain build, stash, or `PROGRESS.md` change
  was used for this checkpoint.

### Acceptance-gate machinery

- Added `tools/predictor_set_oos_gate.py`. Its in-file authority block fixes a
  SHA-256 stable-source-id donor fold (seed 20260816, fold 0 of 5 held out), the
  five quantiles, the quantile-forest fit, and a 2,000-replicate paired
  256-cluster bootstrap. None of these are inherited library defaults.
- The sweep binds all 32 lineage families and 118 changed targets to each
  artifact's own executed target order. Baseline models use the legacy
  predictor set; candidate models use the branch declarations. Target-stable
  model seeds keep the paired comparison from acquiring independent Monte
  Carlo noise when the participation reorder crosses a chain boundary.
- The JSON includes every target's weighted held-out pinball loss and paired
  CI, all 211 flattened battery legs with their full receipt-derived gate
  status plus ratio-band transition, and all 16 participation-incidence legs.
  In-band to non-comparable is fail-closed as a leaving-band transition, and
  serialized infinite ratios are out of band.
- The verdict implements the three approved clauses. Any artifact, predictor,
  donor-scarcity, alignment, or bootstrap measurement error writes a named
  `measurement_integrity` FAIL receipt instead of exiting without a verdict.
- Contract validation passed **5 tests** in 1.37 seconds, including real
  fixture-scale HDF/JSON discovery, battery status/transitions, stable-id
  paired bootstrap alignment, a synthetic significant money worsening that
  fails clause b, fail-closed output for synthetic donor scarcity, and refusal
  of unmatched battery failures or unknown statuses. Ruff, format, compile/fit
  smoke, and whitespace checks pass.
- The held baseline was read directly from
  `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/stacked-f025-r1/`: 32
  family receipts, 118 classified targets, 211 flattened battery legs, 93
  failure messages across 60 failed legs, and 16 participation legs parse
  without schema exceptions. Selective checkpoint recomputation reproduced
  the CHAMPVA ASEC incidence 0.000758391845865648, ACS incidence
  0.002821413844669058, and ratio 3.720258676368841 exactly from that artifact.

### Candidate attempt 1: pre-artifact dtype diagnosis

- Launched the candidate setsid-detached and off-chain at commit
  `a510ac764d0faa6804f02082758589a919135353`, using the exact held launcher
  inputs, hashes, sample/attachment fractions, and seeds; explicitly supplied
  the isolated checkpoint root and removed
  `POPULACE_LOGBOOK_PREV_ROW_DIGEST`. The sandbox-writable requested relative
  output is
  `/Users/maxghenis/PolicyEngine/_worktrees/microcosm-predictor-sets/_buildo-runtime/out/stacked-f025-predictor-sets-r1/`.
- This first attempt returned rc=1 at 2026-08-16T23:12:21Z, but it was **not**
  the expected terminal-gate-red completion. It stopped before assembly wrote
  a pool/checkpoint/gates artifact because shared raw `person.MIL` was `int64`
  on ASEC and `float64` on ACS. Receipts:
  `_buildo-runtime/out/stacked-f025-predictor-sets-r1/build.status.json` and
  `_buildo-runtime/out/stacked-f025-predictor-sets-r1/build.log`.
- The offline full-schema audit read the pinned ASEC checkpoint metadata and
  streamed all 3,422,888 ACS person rows from the pinned person zip. Of 42
  newly selected raw ACS fields, only `MIL` overlaps the ASEC person schema;
  ACS has 591,066 native blank `MIL` cells. The 15 canonical carried predictor
  columns are post-assembly float64 outputs and do not collide at this seam.
- The repair is a single reviewed physical harmonization inside the
  ACS-specific stacked boundary: losslessly cast both present raw `MIL`
  columns to float64 before calling strict generic `assemble_spines`. It does
  not fill ACS blanks, change either origin's codes/semantics, or relax generic
  mismatch refusal. Realistic ACS-loader and direct stacked regressions prove
  both origins' codes/blanks and the input frames remain unchanged.
- The ACS PUMS, generic spine-assembly, and stacked-spine test files pass all
  **262 tests** after the repair. Ruff, format, and whitespace checks pass.
  GitNexus graph tools were unavailable in this environment, so the required
  debugging workflow used the exact traceback, repository call chain, pinned
  checkpoint metadata, and streamed pinned input schema instead.

### Candidate attempt 2: pre-artifact investment-predictor diagnosis

- Relaunched the same detached, off-chain probe at commit
  `cf4530b20f2c77df4176ee42937fbd30e542bfa2`. It crossed the repaired dtype
  seam and wrote the 2,347,322,429-byte assembled checkpoint under identity
  `5c1c042b4b9e65e9a4114d2c3c850ebdda0933dd48cf5dfa97212164bc4b7305`,
  then returned rc=1 at 2026-08-16T23:49:08Z before transfer or terminal
  gates. The exact error was the declared but unmapped optional feature
  `__acs_transfer_interest_dividend_rental_income`; receipts are
  `_buildo-runtime/out/stacked-f025-predictor-sets-r1/build.status.json`,
  `_buildo-runtime/out/stacked-f025-predictor-sets-r1/build.log`, and
  `_buildo-runtime/out/stacked-f025-predictor-sets-r1/logbook-receipts/populace-us-2024-stacked-f025-s578-asec42213-acs382903-20260816T233514Z-1c572817/error.json`.
- A production-sized replay from that assembled checkpoint through the exact
  pre-clone source preparation isolated the donor side. All 108,073 ASEC
  donor rows have the prepared taxable-interest, qualified-dividend,
  non-qualified-dividend, and rental leaves, but the stage intentionally has
  no `tax_exempt_interest_income` or `estate_income` columns. The existing
  six-leaf complete-component mapper therefore removed the declared feature.
  The ACS recipient mapping is present and retains its native sparsity:
  729,029 of 964,699 stacked recipient rows are observed.
- The pinned ASEC source already carries the measured survey analogue as raw
  `INT_VAL`, `DIV_VAL`, and `RNT_VAL`. The repair leaves every predictor set,
  order, target, and threshold unchanged: the preferred six-leaf
  PolicyEngine surface remains first, with a complete numeric three-source
  ASEC sum as the execution-bound fallback. The three sources also enter the
  target-leakage registry; missing or nonnumeric components still fail closed.
  No absent estate-income value is synthesized and no target is used before
  its producer.
- On the actual prepared checkpoint, strict resolution now succeeds for all
  3 required and all 17 optional `person/model_required_boolean` predictors.
  The investment feature is observed on 108,073/108,073 donor rows and
  729,029/964,699 recipient rows. The broader ACS-transfer, stacked-spine,
  and multispine-pool run passed its entire selected suite; focused regressions
  cover object-backed raw values, source precedence, missing-component
  refusal, recipient sparsity, identity binding, and leakage refusal. Ruff and
  whitespace checks pass.

### Candidate attempt 3: completed off-chain f025 arm

- Relaunched the exact pinned f025 command setsid-detached at commit
  `f0d249732fbdf4f886333aacc160bc3a73a89774`, with the candidate-local
  checkpoint root and `POPULACE_LOGBOOK_PREV_ROW_DIGEST` removed. It ran from
  2026-08-17T00:03:51.368429Z through 2026-08-17T03:09:28.005266Z and reached
  publication after 11,136.637 seconds. The supervisor recorded peak RSS
  84,097,925,120 bytes and rc=1 in
  `_buildo-runtime/out/stacked-f025-predictor-sets-r1/build.status.json`.
- Rc=1 is the requested terminal-gates-red measurement, not a pipeline error:
  the attempt-3 portion of
  `_buildo-runtime/out/stacked-f025-predictor-sets-r1/build.log` contains no
  traceback, exception, OOM, or kill marker and ends with `US stacked terminal
  gates failed`. Completeness passed with zero failures; the by-origin battery
  tested 132 comparisons with zero untestable comparisons and emitted 77
  failure messages, per
  `_buildo-runtime/out/stacked-f025-predictor-sets-r1/populace_us_2024_stacked_pool.gates.json`.
- The candidate CHAMPVA clone-0 receipt in that gates artifact has ASEC
  incidence 0.000758391845865648, ACS incidence 0.005543057672019064, ratio
  7.3089626454146215, and nonzero rows ASEC 80 / ACS 5,283. These are artifact
  measurements only; the formal Phase-P verdict remains the OOS gate's job.
- The completed candidate files are
  `_buildo-runtime/out/stacked-f025-predictor-sets-r1/populace_us_2024_stacked_pool.h5`
  (3,926,011,964 bytes), its `.gates.json` (4,550,974 bytes), and its
  `.manifest.json` (200,832,034 bytes). The isolated stacked identity is
  `5c1c042b4b9e65e9a4114d2c3c850ebdda0933dd48cf5dfa97212164bc4b7305`;
  its transferred checkpoint is 6,519,174,534 bytes and its simulated
  checkpoint is 6,567,855,699 bytes.
- Candidate-local Logbook row
  `_buildo-runtime/out/stacked-f025-predictor-sets-r1/logbook-spool/752e523ef0812d3cb74a2ac714e9da6fa7a1bb1e09f28cccc754a14f66ea3a7a.json`
  records `prev_row_digest: null`, all phases through publication, completeness
  passed, and the battery failed. The held external
  `/Users/maxghenis/PolicyEngine/_buildo-runtime/logbook-pending-chain.txt`
  remained at its pre-launch 2026-08-16T14:51:20Z modification time and SHA-256
  `14bf8d34ee355a745a7c6ebe83a38ce7307facbfa2bfbef7c190ba44f4d19177`.
  No on-chain row, network call, Modal work, stash, or `PROGRESS.md` edit was
  made.

### Acceptance-gate execution-surface binding

- The completed artifacts exposed a measurement-integrity issue before the
  statistical run: their final simulated frames contain later PolicyEngine
  investment leaves that were not present for the baseline early transfer.
  Scoring those final leaves would leak a later execution surface into the
  early OOS refit. The gate now strips that feature for every early family,
  leaves it unavailable for the baseline, and reconstructs the candidate's
  actually executed `INT_VAL + DIV_VAL + RNT_VAL` person source (plus the
  production SPM aggregation) before resolving the declared predictor order.
- The gate authenticates each arm's stacked authority and gap-fill plan,
  simulated operational-receipt/checkpoint binding, both early target-bank
  identities, and every target checkpoint's path, size, SHA-256, HDF schema,
  content/raw-draw hashes, descriptor, QRF state, and complete predictor
  surface. The baseline and candidate each validate all 48 early targets.
  Sidecar receipts are
  `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/stacked-f025-r1/populace_us_2024_stacked_pool.checkpoints/stacked/9be8ecdf82356f38998e8b620ee36d9134f554fe89a8eafd8406f438e2b5aad6/simulated.checkpoint.receipts.json`
  (SHA-256
  `cb9ed4abb7586b6128f6aeefc9a4923e7e5934844bc3bd56e458299ac28e8c27`)
  and the corresponding candidate sidecar under stacked identity
  `5c1c042b4b9e65e9a4114d2c3c850ebdda0933dd48cf5dfa97212164bc4b7305`
  (SHA-256
  `fb4033a5944034eccf7948a0e690f21774f5d207da8a449db6c948bb85c513e5`).
- Further fail-closed review requires identical unique held-out donor-id sets,
  validates the battery metric/status vocabulary before classification, and
  partitions all 77 generic-numeric changed targets explicitly into 74
  currency-USD targets and the three hour/hour/week targets excluded from
  clause B. Clause-A progress is JSON-safe when a baseline starts in band.
- The primary-session real preflight authenticated 32 families, 118 targets,
  211 battery legs, 16 participation legs, and all 96 early target files. The
  strengthened fixture-scale contract suite passes all **18 tests**; Ruff,
  format, compilation, `git diff --check`, and an independent semantic audit
  are green. The statistical fits have not yet run, and no gate threshold,
  band, seed, fold, or forest parameter changed.
