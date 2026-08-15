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
