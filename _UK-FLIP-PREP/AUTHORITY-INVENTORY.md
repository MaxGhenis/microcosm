# UK bundle-flip authority inventory

## Result

The three named UK drivers and their supporting `uk_runtime` surface expose
**87 independently movable authority surfaces**: 86 on an active or support
path and one exported but currently undispatched firm-generation surface.
This inventory uses one row per control surface that can change behavior or
artifact identity independently; adjacent constants implementing one policy
are deliberately grouped.

The UK bundle on the inspected `origin/spec-engine-schema` snapshot is not
yet an executable authority. `uk/country_package.json:35-134` classifies the
CGT, gate, HMRC, source-stage, take-up, target, and evidence resources as
`legacy_json`; `spec_engine/compiler_ir.py:442-454` drops every such resource.
The country-bundle proof at `tests/test_spec_engine_country_bundles.py:75-78`
then requires `producer_graph.present == false` and zero compiled nodes, while
lines 107-123 classify all UK kernel IDs as contract-only. Consequently, a
mapping below names the *required flip owner*, not an owner the current UK IR
already supplies.

Scope is the locally cached `origin/main` at
`164027e21cfa58a71d701b43211d009d6182e39d` and the cached
`origin/spec-engine-schema`. The specified three drivers and all 57
`uk_runtime/*.py` modules were read. Declarative values are repeated here only
when a driver or whole-stage adapter reconstructs, overrides, or fails to
consume them. Paths below are relative to
`packages/microcosm-build/src/microcosm/build/` unless they begin with
`tools/`.

Owner shorthand: `SRC` sources/stage DAG; `SP` spine; `IMP` imputation;
`TAKE` take-up; `GEO` geography; `CAL` calibration; `BAT` battery; `PUB`
publication; `CAT` catalogs/typed inventory; `VIN` vintage authorities;
`PLAN` compiled plan lock/materializer ABI.

## Authority ledger

### National driver

| ID | Constants-era authority and construction site | Required compiled owner at the flip |
| --- | --- | --- |
| A001 | Release regex, tier alternation, and grandfathered June ID (`tools/build_uk_national_dataset.py:80-85`) | `PUB.release.{pattern,line.legacy_prefixes}` plus compiled tier validation |
| A002 | Named sklearn singleton refusal, exit code 3, and pipeline ID (`tools/build_uk_national_dataset.py:94-96`) | `NEW-SCHEMA-NEEDED execution.pipelines[].failure_policies` |
| A003 | Only accepted sampling rungs: 0.01, 0.10, 1.0 (`tools/build_uk_national_dataset.py:100-113`) | `SP.sampling` and `PUB.release.rung_fractions` |
| A004 | CLI defaults/precedence: build seed 42, 100 QRF estimators, full fraction, sample seed 578, release/gate/checkpoint posture (`tools/build_uk_national_dataset.py:118-235`) | `NEW-SCHEMA-NEEDED run_request.parameters`, `IMP.models`, seed map, `PUB`, and `BAT` |
| A005 | Release-candidate/rung/schema-1 incompatibility fences (`tools/build_uk_national_dataset.py:311-332`) | `PUB.promotion` eligibility and `SP.sampling.assertions` |
| A006 | Committed-versus-override precedence for exclusion/evidence registers (`tools/build_uk_national_dataset.py:336-367`) | `NEW-SCHEMA-NEEDED catalogs.evidence_resources` and `BAT.gates` |
| A007 | Attempt/build ID grammar, including rung, both seeds, clock, and nonce (`tools/build_uk_national_dataset.py:370-389`) | `PUB.attempts` operational identity projection |
| A008 | Certified candidate, raw FRS, SPI, HMRC, and CGT source-pin roles (`tools/build_uk_national_dataset.py:397-415`) | `SRC.sources[].artifacts` and `VIN` |
| A009 | Logbook dispositions and rung-abort receipt kind/schema/stage/remedy (`tools/build_uk_national_dataset.py:437-524`) | `PUB.audit_chain`, `PUB.attempts`, and `execution.pipelines[].failure_policies` |
| A010 | Default terminal/evidence/replay/build/rung sidecar suffixes (`tools/build_uk_national_dataset.py:685-704`) | `NEW-SCHEMA-NEEDED execution.pipelines[].artifact_protocol` and `PLAN` artifact vector |
| A011 | Manual retained-leaf -> SPI -> bespoke CGT stage roster and sampling/gate/checkpoint placement (`tools/build_uk_national_dataset.py:824-853`) | `NEW-SCHEMA-NEEDED execution.pipelines` and `execution.nodes`; compiled stage DAG |
| A012 | Artifact roster; receipt schemas 3/5; dependency distribution; build/evidence payloads (`tools/build_uk_national_dataset.py:868-913,968-1132`) | `execution.pipelines[].artifact_protocol`, `PLAN`, and `PUB` receipts |

### Rowwise candidate driver

| ID | Constants-era authority and construction site | Required compiled owner at the flip |
| --- | --- | --- |
| A013 | Bound target family, five artifact names, free-mass solve knobs, pipeline ID (`tools/build_uk_rowwise_candidate.py:77-88`) | `CAL.target_surface`, `CAL.solver`, `GEO`, and pipeline artifact protocol |
| A014 | Candidate attempt/build ID grammar and fixed `f100` posture (`tools/build_uk_rowwise_candidate.py:112-164`) | `PUB.attempts` and release projection |
| A015 | Defaults: two clones, seed 42, 512 epochs, LR 0.15, `2024_pcon`, optional lineage modulus (`tools/build_uk_rowwise_candidate.py:221-230`) | `run_request.parameters`, `CAL`, `GEO`, `VIN`, and seed map |
| A016 | Hard refusal unless mass conservation is false (`tools/build_uk_rowwise_candidate.py:255-261`) | `CAL.solver.hard_constraints/mass` |
| A017 | Same-loaded-ladder assignment/target binding and clone parameters (`tools/build_uk_rowwise_candidate.py:332-363`) | `execution.pipelines`, `GEO.assignment`, and `CAL.target_surface` |
| A018 | Exact solver arguments and mandatory post-calibration geography gate (`tools/build_uk_rowwise_candidate.py:411-458`) | `CAL.solver` and `NEW-SCHEMA-NEEDED battery.gates` |
| A019 | Gate/artifact roster and the constituency household constant-one target surface (`tools/build_uk_rowwise_candidate.py:479-611`) | `CAL.target_surface`, `GEO.ladder_source`, `BAT`, and `PUB` |
| A020 | Dry-run/manifest schemas, free-mass chain, health/support gates, filenames, atomic publish order (`tools/build_uk_rowwise_candidate.py:624-950`) | `execution.pipelines[].artifact_protocol`, `PLAN`, and `PUB.promotion` |

### Rowwise dataset driver

| ID | Constants-era authority and construction site | Required compiled owner at the flip |
| --- | --- | --- |
| A021 | Crosswalk/dataset/manifest/coverage/plan names, bottom-15 report, pipeline ID (`tools/build_uk_rowwise_dataset.py:68-75`) | Pipeline artifact protocol and `PUB` |
| A022 | `2024_pcon`, two-clone, and seed-42 defaults (`tools/build_uk_rowwise_dataset.py:111-129`) | `GEO.assignment`, `VIN`, `run_request.parameters`, and seed map |
| A023 | Four crosswalk policy switches and optional lineage modulus (`tools/build_uk_rowwise_dataset.py:142-173`) | `NEW-SCHEMA-NEEDED geography.assignment.clone_contract` |
| A024 | Route/f100/seed/time/nonce build-ID and identity fields (`tools/build_uk_rowwise_dataset.py:197-231`) | `PUB.attempts` and compiled node identity |
| A025 | Ladder-versus-crosswalk route selection and stale-sidecar policy (`tools/build_uk_rowwise_dataset.py:350-394`) | `NEW-SCHEMA-NEEDED geography.assignment.routes` and pipeline plan |
| A026 | Route-specific clone and assignment arguments (`tools/build_uk_rowwise_dataset.py:439-451`) | `GEO.assignment.clone_contract` |
| A027 | Manifest schema and route-specific gate roster (`tools/build_uk_rowwise_dataset.py:469-532`) | `battery.gates`, pipeline artifact protocol, and `PUB` |
| A028 | Reserved output names, exact four-country requirement, and run-parameter receipt (`tools/build_uk_rowwise_dataset.py:543-700`) | `CAT`, `GEO.validation`, and `PLAN` |
| A029 | Dry-run parity, analytic/realized support, bottom ordering, geography-column vector, mass gate, publish order (`tools/build_uk_rowwise_dataset.py:722-1406`) | `GEO.validation`, `battery.gates`, and pipeline artifact protocol |

### National frame, protocol, and sampling runtime

| ID | Constants-era authority and construction site | Required compiled owner at the flip |
| --- | --- | --- |
| A030 | Entity/table/weight/time metadata and mass-log relative tolerance `1e-9` (`uk_runtime/national_frame.py:54-63,130-177,230-283`) | `SP.assembly`, `CAT`, bundle target period, and `PLAN` |
| A031 | H5 table/attribute/order and atomic-write protocol (`uk_runtime/national_build.py:90-92,175-305`) | `execution.pipelines[].artifact_protocol` or expanded `SP.pipeline_contract.artifact_protocol` |
| A032 | Sampling/checkpoint/release-candidate contract, exclusion clock, preflight battery (`uk_runtime/national_build.py:338-480`) | `SP.sampling`, `PUB`, `BAT`, and `PLAN` |
| A033 | Sample-before-provenance ordering, stage execution, terminal gate, signed-full versus unsigned-rung rule (`uk_runtime/national_build.py:495-615`) | Compiled pipeline/stage DAG, `BAT`, and `PUB.promotion` |
| A034 | Checkpoint record protocol and fitting-stage set `{hmrc_spi_income, was_wealth}` (`uk_runtime/national_build.py:618-683,768-811`) | Pipeline artifact protocol, producer graph, and `BAT` |
| A035 | Rung map and default sampling seed 578 (`uk_runtime/national_sampling.py:63-72`) | `SP.sampling`, `PUB.release.rung_fractions`, and seed map |
| A036 | Source-family reversal, decimal ID arithmetic, derivative offsets, forced argmax, strata/quota/normalization (`uk_runtime/national_sampling.py:123-370`) | `NEW-SCHEMA-NEEDED spine.sampling.source_family_reversal` |
| A037 | Frame content-identity header, covered surfaces, order, and hash algorithm (`uk_runtime/content_identity.py:41-124`) | `execution.nodes` implementation ABI/identity protocol and `PLAN` reuse key |
| A038 | `household_is_` provenance-column discovery convention (`uk_runtime/provenance_flags.py:12-50`) | `CAT` column classification |
| A039 | Checkpoint metadata key/round trip plus UK tier/release field grammar (`uk_runtime/stage_checkpoints.py:31-114`; `uk_runtime/release_identity.py:24-153`) | Pipeline artifact/identity protocol and `PUB.release` |

### Source transforms outside the declarative operation executor

| ID | Constants-era authority and construction site | Required compiled owner at the flip |
| --- | --- | --- |
| A040 | Nonnegative output roster projected from the manifest (`uk_runtime/source_runtime.py:28-46`) | `SRC.stages[].nonnegative_outputs` (already declarative; retain as assertion) |
| A041 | Manual stage-ID-to-callable registry, sole operation handler, period precedence, country fallback (`uk_runtime/source_runtime.py:49-184`) | `execution.nodes`, source operation/kernel bindings, bundle target period |
| A042 | Fourteen FRS tables, period 2023, weeks/year, coded maps, and output roster (`uk_runtime/frs_spine.py:40-229`) | `SRC` artifacts/operations/outputs, `VIN`, and `CAT` |
| A043 | FRS coercion, ID arithmetic/order, raw formulas, benefit splits, pension q95 clip, salary-sacrifice/property/housing rules (`uk_runtime/frs_spine.py:247-750`) | `execution.nodes[].{kernel,resolved_params,implementation_digest}` |
| A044 | Employment status/sector maps, defaults, and SIC clipping (`uk_runtime/frs_employment.py:24-117`) | `SRC` operation parameters and executable node |
| A045 | Scotland code 12, council-tax donor cells, water netting, week factor, and no-donor zero (`uk_runtime/frs_council_tax.py:26-103`) | `SRC` operation parameters/node |
| A046 | Disability output/category order, Jan-1 policy lookup, `rate-1` threshold, baseline/fiscal split (`uk_runtime/frs_disability.py:20-280`) | `SRC` operation, `VIN`, and engine ABI |
| A047 | Education level/code maps, unknown age 1000, branch order, EMA fill/annualization (`uk_runtime/frs_education.py:26-252`) | `SRC` operation parameters/node |
| A048 | 2025 DSA boundary, eligibility variables, proportional waterfall (`uk_runtime/frs_education_grants.py:21-187`) | `SRC` operation and `VIN` |
| A049 | Legacy proxy statuses and JSA/age/hours/education thresholds (`uk_runtime/frs_legacy_proxies.py:29-173`) | `SRC` operation parameters/node |
| A050 | BRMA predictor/cell keys, count resource, collapse salts, seed 0 (`uk_runtime/frs_brma.py:28-160`) | `SRC`, `IMP`, and seed map |
| A051 | Take-up outputs/anchors/pipelines/rates, seed 0, SCP age rule, 0.05 signal gate (`uk_runtime/frs_take_up.py:30-238`) | `NEW-SCHEMA-NEEDED take_up.{rate_catalog,continuous_distributions,resolution}`, `TAKE.programs`, `BAT`, seed map |
| A052 | Person/household draw output maps, rates/salts, seed 0, SCP age rule (`uk_runtime/frs_person_draws.py:24-90`; `frs_household_draws.py:24-88`) | `TAKE`/`IMP` assignment nodes and seed map |
| A053 | Allowed take-up evidence statuses and latest-effective-date-at-build-year resolver (`uk_runtime/take_up_contract.py:23-169`) | `take_up.rate_catalog` and `take_up.resolution` |

### HMRC, CGT, SPI, and WAS runtime

| ID | Constants-era authority and construction site | Required compiled owner at the flip |
| --- | --- | --- |
| A054 | FRS 2023-24 -> 2023 mapping, week factor, benefit/VAR2 formulas, retained leaves, lineage propagation (`uk_runtime/frs_hmrc_leaves.py:53-123,357-893`) | `SRC` operations and `VIN` |
| A055 | SPI channel names, 10,000 donors, 50% prior, clone/ID metadata, replacement strata/quota, mass transition (`uk_runtime/spi_support.py:33-177,199-443`) | `SRC`, `SP.support_roles/support_source_pool`, and seed map |
| A056 | Sorted-stratum sampling and exact-total floating correction order (`uk_runtime/spi_support.py:710-1006`) | `IMP` kernel ABI and seed ledger |
| A057 | SPI donor pin, 100,000 bootstrap, formulas/tolerances, output/predictor/age/region maps (`uk_runtime/spi_income.py:52-224`) | `SRC` artifacts/operations and `IMP` |
| A058 | Stage-1 seed, stage-2 `seed+1`, estimator count, FACT bootstrap/design-fit policy, predictor/output order (`uk_runtime/spi_income.py:329-569`) | `IMP.models`, producer nodes, and seed map; assert declared 42/43 |
| A059 | Alternative SPI-spine stage/output/predictor/channel/gate roster and defaults (`uk_runtime/spi_spine.py:79-187,341-409`) | Producer graph, `SRC`, `IMP`, `SP`, `BAT` |
| A060 | HMRC source pin/vintage, bands/components, 208-fact count, ODS positions/scales (`uk_runtime/hmrc_income.py:45-335`) | `SRC`, `VIN`, and `CAL.targets` |
| A061 | HMRC operation order/equality and canonical eight fences with 0/0/208 classification (`uk_runtime/hmrc_source_contract.py:71-914`; `hmrc_replay.py:169-378`) | `SRC` operations, `battery.gates`, and publication evidence |
| A062 | Certified candidate identity; seed/QRF/prior/sample defaults; support -> impute -> importance order; effective-mass floor (`uk_runtime/hmrc_restoration.py:87-217,497-658,840-861`) | `SRC.base_candidate`, producer graph, `BAT`, and seed map |
| A063 | HMRC taxpayer definition/interest bridge/208 surface and solver 256/.02/5/.05/42/conserve-mass contract (`uk_runtime/hmrc_calibration.py:57-63,92-387`) | `CAL.target_surface`, `CAL.solver`, and seed map |
| A064 | CGT ODS pin/sheets/bands/totals/scales/tolerances/parser (`uk_runtime/hmrc_capital_gains.py:58-122,316-488`) | `SRC` artifact/operations and `VIN` |
| A065 | CGT seed 552, proxy, June-1 instant, distributions, 2% repair, allocation floor, ranking/remainder/mass rules (`uk_runtime/cgt_imputation.py:95-140,159-220,223-419,432-563`) | `SRC`/`IMP` executable node and seed map |
| A066 | Table-1 £65.9bn/378k target pair, AEA 2022-26 map, taxpayer/support rules (`uk_runtime/fiscal_targets.py:62-138`; `cgt_calibration.py:49-207`) | `CAL.target_surface` and `VIN`; preserve distinction from Table-3 facts |
| A067 | WAS pin, predictors/outputs/raw maps, sentinels, NI -> Wales, seed 0, three-segment QRF chain and waterfall (`uk_runtime/was_wealth.py:26-151,231-535`) | `SRC`, `IMP`, producer nodes, and seed map |
| A068 | Wealth rewrite list, land-value resource, owner-only regional unweighted-mean scale (`uk_runtime/regional_uprating.py:23-106`) | `SRC` operation/resources |

### Geography and local calibration runtime

| ID | Constants-era authority and construction site | Required compiled owner at the flip |
| --- | --- | --- |
| A069 | Official URLs, OA/DZ counts, NI 1% ceiling, join/code/tie-break policy, retries/timeouts, first matching archive member (`uk_runtime/geography_sources.py:26-114,498-930,1641-1720`) | `SRC`/`GEO`; `NEW-SCHEMA-NEEDED sources.artifacts[].archive_member` |
| A070 | Ladder column schema, exact-left joins, unmatched refusal, population filtering, NPZ payload/country concatenation (`uk_runtime/oa_ladder_sources.py:38-222`) | `GEO.ladder_source` and artifact materializer protocol |
| A071 | Ladder layer/order/regex/regions/schema/attrs, weighted constituency-to-OA draw, vintage assertion (`uk_runtime/geography_ladder.py:96-419`) | `GEO.assignment`, `layer_vintages`, draw spec, and seed map |
| A072 | London [.08,.20], ward/ITL [.98,1], constituency >=.99 gates and sorted draw order (`uk_runtime/geography_ladder.py:476-713`) | `battery.gates`, `GEO`, and seed ledger |
| A073 | Crosswalk columns and country/region maps/coverage (`uk_runtime/rowwise_geography.py:18-237`) | `GEO.assignment` and `CAT` |
| A074 | Clone defaults, country/region/constituency/collision policy, 50 retries, zero-population policy, decimal IDs/lineage (`uk_runtime/rowwise_geography.py:240-737`) | `geography.assignment.clone_contract` and seed map |
| A075 | Rowwise table/column roster, mass tolerance `1e-9`, clone routes/defaults, H5/metadata, lineage modulus (`uk_runtime/rowwise_dataset.py:49-1003`) | `execution.pipelines`, `GEO.clone_contract`, and artifact protocol |
| A076 | Constituency/LA household sums, same-artifact binding, positive/sorted targets (`uk_runtime/ladder_targets.py:26-95`) | `CAL.target_surface` and `GEO.ladder_source` |
| A077 | Local metric registry/order and PolicyEngine formulas/grains (`uk_runtime/local_targets.py:18-277`) | `CAL.target_surface`, producer graph, and `CAT` |
| A078 | Census URLs/review date/family rules and seven adjudication fences (`uk_runtime/local_target_census.py:62-575`) | `SRC`, `VIN`, `CAL.target_surface`, `battery.gates`, evidence catalog |
| A079 | Local loss cap 10, max weight ratio 100, uniform row weighting, scale/weight rules (`uk_runtime/local_doctrine.py:42-113`) | `CAL.solver` |
| A080 | Matrix/order/unreachable/past-cap/target naming and 512/.15/free-mass/l0=0/budget10/seed0 defaults (`uk_runtime/local_rowwise.py:111-685`) | `CAL.target_surface`, `CAL.solver`, producer node, seed map |
| A081 | Metadata exclusions and automatic numeric target-column selection (`uk_runtime/local_geography.py:23-89`) | `CAL.target_surface` and `CAT`; compile the selected columns explicitly |

### Gates, publication evidence, and dormant surface

| ID | Constants-era authority and construction site | Required compiled owner at the flip |
| --- | --- | --- |
| A082 | Diagnostics schema, geography vocabulary, default zero-weight strata, ESS/top-1%, 10% scoreboard (`uk_runtime/diagnostics.py:46-64,85-129,168-459`) | `battery.gates`, thresholds, and `PUB` receipt schema |
| A083 | Coverage aliases/statuses/effective-mass floor `1e-6`/review date and gate semantics (`uk_runtime/release_input_coverage.py:57-97,981-1099`) | `battery.gates`, evidence catalog, and `CAT` aliases |
| A084 | Candidate/reference names, .25 error cap, zero-weight declarations, export allow/missing/exclusion rosters (`uk_runtime/terminal_gates.py:72-223,467-745`) | `battery.gates`, thresholds/registry, and `CAT` |
| A085 | Reference descriptor/digests/register schema plus executable 17-gate dispatch and parameter/evidence keys (`uk_runtime/weighted_integrity.py:156-264`; `battery_bindings.py:659-775`) | `battery.gates`, reference registry, `VIN`, evidence catalog |
| A086 | Parity resource/schema conventions and ODS MIME/parser/chunk behavior (`uk_runtime/parity_reference.py:28-237`; `ods_tables.py:32-172`) | `BAT` reference registry and source-reader/materializer ABI |
| A087 | **Dormant/out-of-path:** firm vintages/targets/bands/sectors, Axiom ABI, generator/RNG defaults, solver, validation/allocation (`uk_runtime/firm_generation.py:46-209,211-362,685-800,815-1056,1189-1533`) | `NEW-SCHEMA-NEEDED firm_population`; exported by `uk_runtime/__init__.py` but not dispatched by the three named drivers |

## Schema gap register

There are **14 distinct schema fields needed across ten schema families**.
This count is after folding the physical national/local pipeline, failure,
artifact, and identity details into `execution.pipelines`, and folding exact
whole-stage transform semantics into `execution.nodes`. It does not count
ordinary new rows within an already adequate field.

| Field | Minimal field sketch | Why existing schema is insufficient |
| --- | --- | --- |
| `execution.pipelines` | `{id, entrypoint, nodes, edges, order, failure_policies, artifact_protocol, checkpoint_resume, publication}` | No physical UK pipeline or logical-to-physical checkpoint map exists. |
| `execution.nodes` | `{id, kernel, source_stage_ref, deps, inputs, outputs, capabilities, write_scopes, resolved_params, seed_sites, implementation_digest}` | UK compilation emits zero nodes; whole-stage adapters bypass operation records. |
| `run_request.parameters` | `{name, type, default, allowed, surface, override_precedence, affects_identity, receipt_key}` | CLI defaults and precedence are not a typed/resolved authority. |
| `geography.assignment.routes` | `{default, alternatives, selection_rule, exact_legacy_route}` | Ladder and crosswalk are manually selected and have different semantics. |
| `geography.assignment.clone_contract` | `{n_clones, id_multiplier, lineage_modulus, country/region_constraints, collision_policy, max_retries, zero_population_policy}` | Current geography schema describes a ladder draw, not rowwise clone identity. |
| `calibration.target_surface` | `{source_ref, family, area_type, metric_nodes, bounds, matrix, mass_policy, same_artifact_binding}` | Current calibration schema is US-shaped and cannot express UK constituency-household/local metrics. |
| `battery.gates` | `{id, kernel, phase, inputs, population, denominator, slices, threshold, missing_policy, failure_semantics, evidence_refs}` | Current schema requires exactly two US metric gates; UK runs 17 heterogeneous gates. |
| `take_up.rate_catalog` | `{program, effective_date, status, source, value, fitting_receipt}` | UK rates are date-keyed and evidence-bearing, unlike the US-constant schema. |
| `take_up.continuous_distributions` | `{program, family, params, clipping, unit, seed_site}` | UK includes clipped-normal hours as well as binary assignments. |
| `take_up.resolution` | `{as_of, precedence, ambiguity_policy, resolved_receipt}` | Latest-effective-date selection is currently runtime-only. |
| `catalogs.evidence_resources` | `{id, role, schema_id, sha256, vintage, review/expiry_policy, override_policy}` | UK exclusion, coverage, parity, and target resources are discarded `legacy_json`. |
| `spine.sampling.source_family_reversal` | `{canonical_selector, clone_index, multiplier_rule, derivative_offsets, forced_argmaxs, strata, quota, normalization}` | Generic fraction/seed fields do not define UK clone-family reversal. |
| `sources.artifacts[].archive_member` | `{name_or_pattern, uniqueness_required}` | Geography download currently selects the first matching archive member. |
| `firm_population` | `{sources, target_profile, bands, generator, vat_rules, solver, validation, publication}` | Exported UK firm generation has no normalized domain, though it is outside the named-driver path. |

No new field is required for release line/pattern/rungs, generic source
assets/vintages, CGT source operations, or the four-part stochastic ledger:
the existing publication, source, vintage, and compiled seed-map models can own
them once generalized UK resources are authored and compiled.

## Immediate flip blockers and risks

1. The bundle has no executable UK graph: all real execution still comes from
   the three drivers and their manual transform registries.
2. Source-stage prose does not close the exact FRS transformations, and a
   manifest seed change would not change several module-local seed constants.
3. National publication/signing and multiple receipt schemas remain driver
   authorities; local rowwise execution has no checkpoint/resume envelope.
4. The crosswalk path downloads partly unpinned inputs and selects an archive
   member by first match; this is ambient source selection, not just I/O.
5. The two local geography routes, clone ID arithmetic, and target binding have
   no shared compiled owner.
6. The firm generator is dormant for this flip but is exported runtime
   authority and contains global, backend-sensitive stochastic behavior.

## Completeness statement

All 57 scoped runtime modules were classified. `uk_runtime/__init__.py` has
exports only and adds no independent authority. `firm_generation.py` is the
sole module whose authority is exported but not reachable from the three
specified drivers; it is retained as A087. Modules with thin wrappers or
validators are represented with their controlling module in A039-A086 rather
than being silently omitted. No UK package source was changed and no build was
run for this analysis.
