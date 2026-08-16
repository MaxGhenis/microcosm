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
