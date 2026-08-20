# UK bundle-flip authority inventory

## Result

The three UK drivers currently construct **33 coherent semantic authority
groups** outside the declarative source-stage operations. Eleven distinct field
paths are absent from the spec-engine schema and are sketched below as
`NEW-SCHEMA-NEEDED` N01–N11.

This is an analysis of cached `origin/main@164027e21cfa58a71d701b43211d009d6182e39d`
against cached
`origin/spec-engine-schema@c4e1eb7fc3ae5246a9b8e5d4a63cb7195aaf8cfa`.
An “authority” is one coherent behavioral contract, following the US F1
inventory convention; individual members of one tuple, registry, or artifact
protocol are not inflated into separate counts. Line numbers refer to the
cached `origin/main` worktree.

The intended flip rule is strict: bundle mode obtains semantic values from
`CompiledSpecIR`; code may retain only implementation, validation, and
generated-ABI assertions. Paths, licensed-file handles, retry mechanics,
timestamps, and nonces remain run-request or operational bindings.

The `Stage` and `Affected artifacts` columns follow the US F1 inventory
template. Stage names describe the earliest point at which the authority can
change behavior; a range means the authority persists across those stages.

## National build

| ID | Authority constructed in code | Current behavior | Flip owner |
| --- | --- | --- | --- |
| A01 | Certified base and source pins — `uk_runtime/hmrc_restoration.py:87-93`; `tools/build_uk_national_dataset.py:397-415,759,783-804,961-990` | Accepts a particular candidate filename, revision, tier, hash, and size, then binds adult, benefits, SPI, HMRC, and CGT input identities into the run. | `ir.resource("sources")`, `ir.vintage_authorities`, and compiled source bindings. The skeleton candidate record is a start, but every driver role must compile into an authenticated input binding. |
| A02 | National logical stage roster and order — `tools/build_uk_national_dataset.py:824-845`; `uk_runtime/national_build.py:425-427,509-521` | Cherry-picks retained FRS leaves and `hmrc_spi_income`, then appends CGT with bespoke code rather than selecting one complete authored producer graph. | `ir.producer_graph` and `ir.nodes`; **N01**. This must expose the physical/logical stage order, including CGT and checkpoint boundaries. |
| A03 | Stage run parameters — `tools/build_uk_national_dataset.py:214-235,767-775,968-982`; `uk_runtime/hmrc_restoration.py:203-217,497-510` | Build seed defaults to 42, QRF tree count to 100, donor sampling to its code default, and sampled-rung posture is fanned into transforms. One CLI seed currently feeds several independent RNG families. | Compiled source-operation parameters in `CompiledNode.resolved_params`, `ir.seed_stream_map`, and a typed run-request overlay. No new country field is needed if the source operations are actually compiled. |
| A04 | Entity, frame, and weight contract — `uk_runtime/national_frame.py:54-63,130-177,248-282`; `uk_runtime/national_build.py:90-92` | Fixes the person/benunit/household set, household-only typed weights, DESIGN compatibility default, no link objects, time-period metadata, exported weight column, and mass-log tolerance `1e-9`. | Catalog/carrier ABI plus **N02**. |
| A05 | National H5 physical ABI — `uk_runtime/national_build.py:90-92,250-335,866-877` | Fixes table names/order, pandas HDF table storage/data columns, H5 attributes, atomic temp-file behavior, and attr-less DESIGN/empty-log compatibility. | Compiler-emitted materializer plus **N03** artifact declarations. |
| A06 | Rung domain, sampling default, and releasability — `uk_runtime/national_sampling.py:61-72`; `tools/build_uk_national_dataset.py:100-113,214-235,311-331`; `uk_runtime/national_build.py:437-459,497-502` | Permits only 1%, 10%, and 100% (`f001/f010/f100`), defaults sample seed to 578, makes full fraction a no-op, and prohibits a sampled rung from claiming release-candidate/canonical identity. | `spine.sampling`, generalized `publication.release.rung_fractions`, `ir.seed_stream_map`, and battery/publication gates. The existing publication field must cease requiring the five US rungs. |
| A07 | UK source-family sample selection — `uk_runtime/national_sampling.py:123-258,293-369` | Reverses clone/SPI/CG ID arithmetic to raw FRS family IDs, derives multipliers from live maxima, carries six argmax selectors into a deduplicating forced-family set (therefore at most six distinct families), stratifies by the raw canonical region, renormalizes to full mass, and rechecks the SPI replacement quota. | **N04–N07**. The current sampling schema cannot express the reversal formula, forced retention, source-row strata, or postconditions. |
| A08 | Release namespace, tier, and cardinality — `uk_runtime/release_identity.py:24-64,67-101`; `tools/build_uk_national_dataset.py:80-85` | Allows tiers `frs` and `cps-transfer`; emits `populace-uk-<year>-<tier>-k<count>`; requires positive year/count; recognizes one grandfathered June ID at the rung fence. | Generalized `publication.release.pattern` plus **N08**. A regex alone does not own the tier vocabulary or cardinality source. |
| A09 | Candidate posture and named failure policy — `tools/build_uk_national_dataset.py:87-96,291-331,499-524`; `uk_runtime/national_build.py:449-459,569-599` | Evidence gaps block candidate posture; schema-1 coverage aliases are forbidden for candidates; only an exact sklearn singleton signature is a sampled-rung exit-3/reroll exception; unsigned full builds fail while unsigned rungs are allowed. | Battery blocking modes and **N09** own release eligibility. The exact singleton retry is generated executor ABI/execution policy, not normative release policy. |
| A10 | Content-addressed run identity and dependency roster — `tools/build_uk_national_dataset.py:938-1003`; `uk_runtime/release_input_coverage.py:481-517`; `uk_runtime/cgt_imputation.py:159-195,618-633` | Run identity includes exact inputs, parameters, source contracts, and the hardcoded dependency names `h5py`, `numpy`, `pandas`, `quantile-forest`, `scikit-learn`, and `tables`. Active gates load installed `policyengine-uk`, and CGT loads both `policyengine-uk` and `policyengine-core`, but neither installed version is in that six-package roster. Hashing `uv.lock` does not prove the environment actually executing the build matches it. | Compiler plan/node reuse keys and a generated, verified engine ABI lock that records every reachable installed distribution, including `policyengine-uk` and `policyengine-core`. Package versions and code pins are execution authority, not normative bundle fields. |
| A11 | Checkpoint/resume protocol — `uk_runtime/national_build.py:432-447,618-683`; `uk_runtime/stage_checkpoints.py:31-73` | Writes one checkpoint per logical stage, with a fixed metadata envelope and completed-stage resume/transform semantics. | **N01** logical stages plus **N03** artifact records; the compiled plan owns the checkpoint DAG and resume predicate. |
| A12 | UK gate plan, phases, evidence wiring, and signing posture — `uk_runtime/national_build.py:470-600`; `uk_runtime/battery_bindings.py:650-725`; `gate_battery.py:94-141,946-1036` | Runs preflight gates before load and terminal gates immediately before writing; maps named evidence/artifacts into a hardcoded registry and applies candidate blocking posture. The generated country signing-key environment name, 32-byte key rule, HMAC ABI, and signing-key presence affect `shippable` and whether a full-scale H5 may be written. Thresholds mostly live in `uk/gates.json`, but execution, wiring, and signing posture do not. | `ir.resource("battery")`, compiled battery projections, the stage DAG, and the F1 secret/signing broker plus generated attestation ABI. The current battery schema is US-specific and must be generalized; that is an existing-field generalization, not a new path in the N-count. |
| A13 | Gate, diagnostic, and packaged-resource values still resident in code — `uk_runtime/terminal_gates.py:72-74,132-232`; `uk_runtime/weighted_integrity.py:156-261,545-698`; `uk_runtime/release_input_coverage.py:57-81,189-205,380-425,1108-1177`; `uk_runtime/battery_bindings.py:271-282,431-434,565-579,623-626`; `uk_runtime/diagnostics.py:45-64` | Fixes candidate/reference labels, known-missing/export column vocabularies, reference identity, coverage aliases, a 1ppm distributional floor, geography levels, and a separate 10% diagnostics pass threshold. Active package authority includes `release_input_coverage_manifest.json`, `efrs_parity_reference.json`, `efrs_parity_known_gaps.json`, `was_wealth_support_bounds.json`, and all three reviewed-exclusion registers (`input_mass`, `qrf_tail`, `degenerate`). Many values duplicate `gates.json` or committed resources. | Battery parameters and authenticated reference resources, catalogs, and **N03** report schema. Code copies become generated constants or drift assertions; every package resource gets a compiled content pin and usage receipt. |
| A14 | Fit-weight evidence capability roster — `uk_runtime/national_build.py:768-811` | Hardcodes only `hmrc_spi_income` and `was_wealth` as stages that owe `FitWeightRecord` evidence. | `ir.nodes[*].capabilities.fit_uses_weights`, producer-node output contracts, and battery evidence projections. |
| A15 | Attempt/build/report names — `tools/build_uk_national_dataset.py:370-389,499-524,673-711,1019-1208` | Fixes attempt/build ID templates, pipeline ID, sidecar suffixes, aggregate/report kinds, and schema names. | `publication.attempts`, `publication.audit_chain`, and **N03**. Clock and UUID fragments are brokered operational outputs. |
| A16 | Physical gate-artifact placement and publish order — `uk_runtime/national_build.py:470-494,555-615,831-854`; `gate_battery.py:838-863,1027-1036`; `tools/build_uk_national_dataset.py:685-711,855-932` | The battery writes its preflight and terminal schema-4 reports before the staging H5; the compatibility route may last-write a schema-1 coverage alias over that report. Only after `national_build` returns with the H5 does the driver write HMRC evidence/replay, then the aggregate build record, then the terminal Logbook row. | **N01** stage DAG, **N03** artifact dependencies/order, and `publication.promotion`. |
| A31 | Exclusion-evaluation clock — `uk_runtime/national_build.py:359,384-392,466-470,525-527`; `uk_runtime/weighted_integrity.py:464-480` | One UTC date is resolved before stages, threads through all exclusion-consuming terminal gates, and is written as `exclusions_evaluated_on`; without injection it comes from `datetime.now(UTC).date()` and can change gate outcomes for identical data/configuration. The production driver does not pass `now`. | `CompiledSpecIR.surfaces.chain_state` plus the certified F1 clock broker and sealed run-request date. No new country field is needed. |

## Rowwise, geography, and calibration builds

| ID | Authority constructed in code | Current behavior | Flip owner |
| --- | --- | --- | --- |
| A17 | Geography route choice — `tools/build_uk_rowwise_dataset.py:92-107,345-451,613-627`; `tools/build_uk_rowwise_candidate.py:210-230,351-363` | The rowwise dataset chooses mutually exclusive ladder or crosswalk routes; absent crosswalk means live source assembly; ladder forbids separate coverage-code checks. The candidate is ladder-only. | **N10** named assignment routes and a typed run-request selector. The current geography schema has only one `ladder_source`. |
| A18 | Official geography source/assembly inventory — `uk_runtime/geography_sources.py:26-114,117-907,1641-1663`; `uk_runtime/oa_ladder_sources.py:37-65` | Embeds 18 public URL constants; 13 distinct defaults are consumed by the active no-crosswalk driver path, while the other five definitions serve the separately built ladder artifact or dormant helpers. It also fixes expected EW/Scotland/NI row counts, a 1% NI unmatched-postcode bound, and source assembly defaults. Crosswalk sources are mutable and not content-pinned. | `ir.resource("sources")`, `ir.vintage_authorities`, and compiled source nodes. Timeout, retry, User-Agent, and backoff belong to the execution profile/broker. Certification must use pinned bytes. |
| A19 | Crosswalk schema and geography vocabularies — `uk_runtime/rowwise_geography.py:18-91`; `tools/build_uk_rowwise_dataset.py:630-642` | Fixes required/output columns, area-type names, FRS region-to-country/region-code aliases, UK country codes, and CSV dtype treatment. | Geography derive/assertions, catalogs/domains, and compiled-node parameters; adapter maps should be generated where possible. |
| A20 | Crosswalk selection controls — `tools/build_uk_rowwise_dataset.py:128-170,439-450,675-700`; `uk_runtime/rowwise_geography.py:277-377,626-649,698-737` | Defaults to two clones and seed 42; requires each country/region key present among the input households to have candidates (not all four UK nations), requires nonblank constituencies, constrains to region, and forbids zero-population distributions. Cross-clone constituency collision avoidance is best-effort: after at most 50 resamples it returns without a final residual-collision refusal. | **N10**, **N11**, `ir.seed_stream_map`, and typed run-request values. |
| A21 | Clone ID, weight, and lineage semantics — `uk_runtime/rowwise_dataset.py:137-238,290-431,551-569,889-969`; `uk_runtime/rowwise_geography.py:492-546,613-623,848-884`; `tools/build_uk_rowwise_dataset.py:162-171` | Uses one collision-free multiplier across entity IDs and foreign keys, emits clone indices, divides household weight by clone count, appends an exact mass record, optionally derives pool lineage immediately from source IDs by modulus, emits `source_household_id`, `source_household_year`, and `source_household_key` in `<year>:<id>` form, and applies `1e-9` mass tolerance. Ladder assignment intentionally has no cross-clone collision retry. | **N11**, **N02**, and **N03**. |
| A22 | OA-ladder artifact ABI and layer vocabulary — `uk_runtime/geography_ladder.py:92-178`; `uk_runtime/oa_ladder_sources.py:37-49` | Fixes derived/output layer order, London/EW region codes, artifact kind/schema/attributes, NPZ arrays, and GSS/ward/ITL code grammars. | Existing geography assignment/derive/assertion/layer-vintage fields, catalogs, and **N03**. The skeleton lists layers but not the artifact ABI or code domains. |
| A23 | Ladder draw plan and vintage refusal — `uk_runtime/geography_ladder.py:331-370,643-713`; `tools/build_uk_rowwise_candidate.py:221-230,354-363`; `tools/build_uk_rowwise_dataset.py:111-129,885-909,1029-1049` | Within preserved region, draws constituency by household totals, then OA by population; all other layers derive from the OA; requires `2024_pcon`. Kernel default is 0, but both production drivers default/pass 42. | Existing `geography.assignment.draw`, `derive`, `default_seed`, `seed`, and `layer_vintages`, plus `ir.seed_stream_map`. The 0-versus-42 discrepancy is a pre-dispatch blocker. |
| A24 | Ladder release gate — `uk_runtime/geography_ladder.py:476-640`; `tools/build_uk_rowwise_candidate.py:435-458`; `tools/build_uk_rowwise_dataset.py:1040-1054` | Checks code shapes, ITL3-prefix relationships, recognized-country/declared-region consistency, and weighted nonempty shares: London 0.08–0.20, ward/ITL 0.98–1.00, constituency at least 0.99. It does **not** validate OA→LSOA→MSOA→LA/ward/constituency ladder membership. Runs after assignment and again after candidate calibration. | UK battery metric/gate record referenced by the stage DAG. It is absent from current `uk/gates.json`; `geography.validation` can reference it once authored. |
| A25 | Target-family choice and provenance — `tools/build_uk_rowwise_candidate.py:77,368-374,577-610`; `uk_runtime/ladder_targets.py:26-95` | Binds exactly `census_households/constituency`; target controls are sorted sums of OA household counts and must derive from the same loaded ladder object used for assignment. | Generalized existing `calibration.targets` plus an authenticated ladder source/vintage pin. Python object identity becomes compiled content-pin equality; no new catalog path is needed. |
| A26 | Rowwise target matrix, naming, and ordering — `uk_runtime/local_rowwise.py:201-209,425-467`; `tools/build_uk_rowwise_candidate.py:589-610` | Uses a constant-one household metric, constituency assignment column, target code, incoming target-frame order, `{area_type}/{code}/{metric}` names, household weights, and a fail-closed complete surface. | Generalized existing `calibration.targets` and compiled target nodes. The current calibration schema is US-specific, but this is a generalization rather than a new field path. |
| A27 | Local solve doctrine and run options — `uk_runtime/local_doctrine.py:40-113`; `tools/build_uk_rowwise_candidate.py:84-88,221-230,411-422,802-827`; `uk_runtime/local_rowwise.py:470-554,609-639` | Capped relative-error loss, default target scales, uniform target weights, loss cap 10, max weight ratio 100, 512 epochs, LR 0.15, free mass, no target record count, L0=0, 10 budget iterations, and driver seed 42 (library default 0). | Country-neutral `ir.resource("calibration").solver/targets/release_modes` and run-request projection. Existing fields suffice once generalized. |
| A28 | Calibration mass/weight transition and post-gate — `uk_runtime/local_rowwise.py:498-554,642-665`; `tools/build_uk_rowwise_candidate.py:426-464,723-799` | Rejects zero base weights; FREE_MASS permits target-driven mass change; advances weight kind to CALIBRATED; requires the kernel mass record/reason; reruns the ladder gate; emits the weight-kind chain and support evidence. | Calibration hard constraints/attainment, producer-node output contract, battery gate, and **N03** artifact records. |
| A29 | Rowwise release/artifact protocol — `tools/build_uk_rowwise_candidate.py:78-88,112-117,142-164,723-827,903-910,937-972`; `tools/build_uk_rowwise_dataset.py:68-75,439-491,568-594,675-700,900-947`; `uk_runtime/national_build.py:250-305` | Fixes filenames, manifest schema/build kind, `adjudicated_partial` scope, sidecars, pipeline IDs, and build-ID templates. Candidate publication is transactional in fixed dataset→diagnostics→support→past-cap→manifest order with rollback and no overwrite. Dataset publication writes/replaces the H5 first, then coverage and manifest, permits output-H5 replacement, and has no bundle rollback. Candidate build/attempt identities hardcode rung `f100`, even with an f001 national input. | **N03**, `publication.attempts`, and `publication.audit_chain`; UUID/time components stay operational. Preserve the incumbent `f100` tag at the flip unless the owner separately rules and inventories a semantic relabel. |
| A30 | Optional coverage and dry-run policy — `tools/build_uk_rowwise_dataset.py:73,119-127,400-415,613-627,661-672,862-876,1015-1060`; `tools/build_uk_rowwise_candidate.py:614-630` | The four-country coverage assertion runs only when optional area-code CSVs are supplied; the candidate uses a bottom-support count of 15. Candidate dry-run is no-write, but dataset dry-runs write a plan and, when `--crosswalk` is absent, first download/build and write the crosswalk before the dry-run branch. | Geography assertions, battery diagnostic metrics, **N03**, and explicit execution-profile modes. The dataset dry-run's source materialization is a real planned stage, not a no-side-effect promise. |
| A32 | Rowwise input/run identity and source-year binding — `tools/build_uk_rowwise_candidate.py:120-139,317-345,1001-1027`; `tools/build_uk_rowwise_dataset.py:210-231,352-435,597-610,858-896,1430-1443` | Candidate identities pin dataset and ladder SHA/size; dataset identities pin the national H5 and selected crosswalk/ladder SHA/size. Both hash inputs, resolved parameters, and source year, which is explicit or inferred from the H5 time-period prefix. Their `identity_digest` omits the git code pin, which is recorded separately only on the Logbook attempt. | Authenticated compiled input bindings, typed source-year run request, compiler plan/node reuse key, and generated engine ABI/code pin. The code identity must enter the executor identity rather than remain a detached Logbook field. |

## Shared lifecycle authority

| ID | Authority constructed in code | Current behavior | Flip owner |
| --- | --- | --- | --- |
| A33 | Logbook external-chain and sink routing — `tools/build_uk_national_dataset.py:291-310,527-545,922-932`; `tools/build_uk_rowwise_candidate.py:232-247,282-295,524-550`; `tools/build_uk_rowwise_dataset.py:179-194,316-340,521-529,965-974`; `logbook_adoption.py:111-124,208-246`; `logbook.py:398-442,822-894` | All three drivers resolve predecessor digest by CLI-over-environment with disagreement fatal and genesis `null`; each chooses a fixed output-relative spool directory. The shared writer durably spools before an optional best-effort remote POST. `POPULACE_LEDGER_URL`, key, and API-key environment bindings decide whether and where the row is sent; remote failure is recorded but does not fail the build. | `publication.audit_chain`, `CompiledSpecIR.surfaces.chain_state`, a sealed predecessor run-request binding, and the F1 filesystem/network/secret brokers. Sink URL, credentials, timeout, and spool root are operational bindings, not country semantics. |

## Stage and artifact propagation

This companion table supplies the two propagation columns from the US F1
template one-for-one for A01–A33. `Configure` includes input authentication and
plan locking; `publish` includes durable sidecars and the terminal Logbook row.

| ID | Stage | Affected artifacts |
| --- | --- | --- |
| A01 | National configure/input binding | Run config, checkpoints, gate evidence, staging H5, build record, Logbook row |
| A02 | National plan → transforms | Physical plan, stage checkpoints, staging H5, HMRC evidence/replay, build record |
| A03 | National configure → transforms | Stage checkpoints, stochastic outputs in H5, HMRC evidence/replay, build record |
| A04 | National load → materialize | Frame/checkpoints, staging H5 tables/attributes, downstream manifests |
| A05 | National materialize/publish | Staging H5 and every downstream input pin |
| A06 | National configure → sample → publish | Sampling receipt, checkpoints, H5, gate report, build record, Logbook row |
| A07 | National sample | Sampling receipt, sampled H5/checkpoints, terminal gate evidence |
| A08 | National configure/publication | Release ID in gate report, rung-abort receipt, build record, Logbook row |
| A09 | National preflight/terminal | Gate report, rung-abort receipt, H5 presence/absence, Logbook verdict |
| A10 | National configure/resume | Run-config digest, checkpoint identity, build record, Logbook identity |
| A11 | National stage boundaries | Per-stage checkpoints and final H5 |
| A12 | National preflight/terminal/publish | Gate report/attestation, shippability, H5 presence/absence |
| A13 | National preflight/terminal | Gate report or legacy coverage alias, build-record evidence |
| A14 | National terminal | Fit-weight evidence and gate report |
| A15 | National attempt lifecycle | Error/rung-abort receipts, build/report identifiers, Logbook row |
| A16 | National preflight → terminal → publish | Battery reports/alias, H5, HMRC evidence/replay, build record, Logbook row |
| A17 | Rowwise configure/source selection | Crosswalk or ladder binding, rowwise H5/manifest, candidate inputs |
| A18 | Rowwise source assembly | Crosswalk/ladder source artifacts, source pins, rowwise manifest |
| A19 | Rowwise source load | Crosswalk columns/dtypes, rowwise H5 geography columns, manifest |
| A20 | Crosswalk assignment | Rowwise H5 geography columns, coverage summary, manifest |
| A21 | Rowwise clone/materialize | Rowwise and candidate H5s, lineage columns, weight/mass records, manifests |
| A22 | Ladder load/assignment | Ladder NPZ binding, H5 geography columns, rowwise/candidate manifests |
| A23 | Ladder assignment | Stochastic geography columns, gate evidence, rowwise/candidate manifests |
| A24 | Post-assignment and post-calibration gates | Gate details, rowwise/candidate manifests, Logbook verdicts |
| A25 | Candidate target construction | Target frame/provenance, diagnostics, candidate H5/manifest |
| A26 | Candidate matrix construction | Target matrix/names/order, diagnostics/support, candidate H5/manifest |
| A27 | Candidate solve | Candidate weights/H5, diagnostics, past-cap sidecar, manifest |
| A28 | Candidate solve/post-gate | Candidate H5, mass record, support/gate evidence, manifest/Logbook verdict |
| A29 | Rowwise/candidate publish | H5s, diagnostics, support, past-cap, coverage, manifests, Logbook rows |
| A30 | Rowwise source/coverage/dry-run | Generated crosswalk, dry-run plan, coverage summary, manifest |
| A31 | National preflight → terminal | Gate evaluation date/verdict, H5 disposition, gate report/Logbook row |
| A32 | Rowwise/candidate configure | Input/identity digests, source-year filenames and manifests, Logbook rows |
| A33 | All-driver preflight/terminal | Local Logbook spool row and optional remote ledger row |

## `NEW-SCHEMA-NEEDED` fields

These are **11 distinct field paths**, counted once even when several authority
rows consume them.

| ID | Field sketch |
| --- | --- |
| N01 | `spine.pipeline_contract.logical_stages[] = {id, source_stage_ref_or_kernel, after[], checkpoint_boundary, enabled_by, gate_refs[]}` |
| N02 | `spine.entity_contract = {entities[], group_entities[], links[], weight_entities[], exported_weight_columns[], time_period_field, mass_log_tolerance}` |
| N03 | `spine.pipeline_contract.artifacts[] = {id, kind, format, tables[], attrs[], filename_pattern, schema_version, producer_stage, dependencies[], atomic_write, compatibility_defaults}` |
| N04 | `spine.sampling.family_key = {base_id, canonical_filter, reversal_steps:[{when, subtract, factor_formula}], valid_base_universe}` |
| N05 | `spine.sampling.forced_retention[] = {selector, argmax_entity, argmax_surface, reason}` |
| N06 | `spine.sampling.strata[] = {field, source_row}` |
| N07 | `spine.sampling.postconditions[] = {kernel, params}` |
| N08 | `publication.release.dimensions = {tier:{enum[], semantics}, record_count:{source, minimum}}` |
| N09 | `publication.release.candidate_policy = {required_scale, required_signed_battery, forbidden_compat_outputs[]}` |
| N10 | `geography.assignment.routes[] = {id, source_ref, kernel, availability_or_fallback, parameters, validation_refs[], output_columns[]}` |
| N11 | `geography.assignment.clone_policy = {n_clones, weight_split, id_strategy, lineage_fields[], collision_scope[], collision_policy, max_retries}` |

The following are not added to the count because the semantic field already
exists but its schema is US-specific: publication rung fractions, battery
gates/metrics, calibration solver/targets (including A25–A26's target catalog),
and the top-level spine pipeline
contract. They still must be made country-neutral before UK compilation can
succeed. In particular, the present F1 spine execution contract fixes the US
pipeline/artifact vocabulary, while the UK walking skeleton has no executable
producer nodes. `named_dev_exemptions` is likewise generated executor
ABI/execution-retry policy, not part of normative N09 release eligibility.

## Coverage and non-authority dispositions

All 55 `uk_runtime` Python modules and all three requested drivers were
inspected.

- Source-stage mirrors are not double-counted. `frs_spine.py`, the FRS
  transformation modules, `frs_take_up.py`, `frs_person_draws.py`,
  `frs_household_draws.py`, `frs_brma.py`, `was_wealth.py`,
  `regional_uprating.py`, and detailed HMRC/SPI/CGT constants are already
  represented in `source_stages.json`, `hmrc_income_source_stages.json`, or
  `cgt_source_stages.json`. At flip, authored operations must populate
  `CompiledNode.resolved_params`; code copies may only validate drift.
- `firm_generation.py` is imported through the broad package export but no
  requested driver calls its generator. Its authorities are excluded from the
  33-row selected producer graph and must remain a closed experimental profile.
- `uk_runtime/hmrc_calibration.py:57-65,321-328`,
  `uk_runtime/cgt_calibration.py:49-58`, and
  `uk_runtime/fiscal_targets.py:62-138` define dormant calibration authorities.
  The national driver explicitly performs no calibration at
  `tools/build_uk_national_dataset.py:808-812`; enabling them would require a
  separate inventory addition, generalized calibration fields, and ledger
  ownership. Hardcoded fiscal totals must not be promoted into a bundle.
- The broader local target census/registry modules are not selected by the
  candidate's single ladder-derived target family; A25–A28 cover the selected
  path. `parity_reference.py`, `provenance_flags.py`, and source-contract
  modules are validation/reference inputs already covered by A01/A12/A13.
- Parser caps, canonicalization headers, transform registries, and similar
  safety literals—for example `uk_runtime/ods_tables.py:41`,
  `uk_runtime/content_identity.py:41`, and
  `uk_runtime/source_runtime.py:49-112`—belong to attested kernel/generated
  engine ABI, not country policy authority.

## Highest-risk gaps

1. The source-family sample is not representable: its live-ID reversal, six
   argmax selectors deduplicated to at most six forced families,
   canonical-region strata, renormalization, and SPI quota postcondition
   require N04–N07.
2. The UK walking skeleton is not executable. The live driver cherry-picks two
   source stages and inserts CGT, while the compiled UK graph has no nodes and
   the current physical execution contract is US-stacked-specific.
3. Geography would change bytes if the wrong default wins: the spec skeleton
   says 0; both rowwise production drivers pass 42.
4. The ladder gate is absent from `uk/gates.json`, and present battery and
   calibration schemas constrain US concepts.
5. The crosswalk route can download mutable, unhashed public URLs. A one-day
   replay needs a pinned crosswalk/ladder artifact or authenticated source
   records; a dataset "dry-run" can trigger that download and write.
6. National run identity does not record the installed `policyengine-uk` or
   `policyengine-core` versions it executes, and rowwise identity digests omit
   their separately recorded git code pin. A lock hash alone cannot close
   either environment drift path.
7. The exclusion date, signing key, Logbook predecessor, and remote ledger
   destination all enter through ambient clock/environment state. The first two
   can change whether an H5 ships; the latter two can change the audit chain and
   external side effects.
8. The publication schema's US release line/rung constraints do not describe
   the UK `populace-uk` tier/cardinality namespace, and the candidate's
   hardcoded `f100` receipt tag does not reflect an f001 national input.
   Candidate publication is rollback-safe while dataset publication is not, so
   one generic "rowwise publish" implementation would silently change failure
   semantics.
