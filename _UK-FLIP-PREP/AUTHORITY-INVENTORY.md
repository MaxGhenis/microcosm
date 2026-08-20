# UK bundle-flip authority inventory

## Result

The three UK drivers currently construct **30 coherent semantic authority
groups** outside the declarative source-stage operations. Twelve distinct field
paths are absent from the spec-engine schema and are sketched below as
`NEW-SCHEMA-NEEDED` N01–N12.

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
| A09 | Candidate posture and named failure policy — `tools/build_uk_national_dataset.py:87-96,291-331,499-524`; `uk_runtime/national_build.py:449-459,569-599` | Evidence gaps block candidate posture; schema-1 coverage aliases are forbidden for candidates; only an exact sklearn singleton signature is a sampled-rung exit-3/reroll exception; unsigned full builds fail while unsigned rungs are allowed. | Battery blocking modes and **N09**. |
| A10 | Content-addressed run identity and dependency roster — `tools/build_uk_national_dataset.py:938-1003` | Run identity includes exact inputs, parameters, source contracts, and the hardcoded dependency names `h5py`, `numpy`, `pandas`, `quantile-forest`, `scikit-learn`, and `tables`. | Compiler plan/node reuse keys and generated engine ABI lock. Package versions and code pins are execution authority, not normative bundle fields. |
| A11 | Checkpoint/resume protocol — `uk_runtime/national_build.py:432-447,618-683`; `uk_runtime/stage_checkpoints.py:31-73` | Writes one checkpoint per logical stage, with a fixed metadata envelope and completed-stage resume/transform semantics. | **N01** logical stages plus **N03** artifact records; the compiled plan owns the checkpoint DAG and resume predicate. |
| A12 | UK gate plan, phases, and evidence wiring — `uk_runtime/national_build.py:470-600`; `uk_runtime/battery_bindings.py:650-725` | Runs preflight gates before load and terminal gates immediately before writing; maps named evidence/artifacts into a hardcoded registry and applies candidate blocking posture. Thresholds mostly live in `uk/gates.json`, but execution and wiring do not. | `ir.resource("battery")`, compiled battery projections, and the stage DAG. The current battery schema is US-specific and must be generalized; that is an existing-field generalization, not a new path in the N-count. |
| A13 | Gate and diagnostics values still resident in code — `uk_runtime/terminal_gates.py:72-74,132-223`; `uk_runtime/weighted_integrity.py:156-260`; `uk_runtime/release_input_coverage.py:57-93`; `uk_runtime/diagnostics.py:45-64` | Fixes candidate/reference labels, known-missing/export column vocabularies, reference identity, coverage aliases, a 1ppm distributional floor, geography levels, and a separate 10% diagnostics pass threshold. Many terminal values duplicate `gates.json` or committed registers. | Battery parameters/reference resources, catalogs, and **N03** report schema. Code copies become generated constants or drift assertions. |
| A14 | Fit-weight evidence capability roster — `uk_runtime/national_build.py:768-811` | Hardcodes only `hmrc_spi_income` and `was_wealth` as stages that owe `FitWeightRecord` evidence. | `ir.nodes[*].capabilities.fit_uses_weights`, producer-node output contracts, and battery evidence projections. |
| A15 | Attempt/build/report names — `tools/build_uk_national_dataset.py:370-389,499-524,673-711,1019-1208` | Fixes attempt/build ID templates, pipeline ID, sidecar suffixes, aggregate/report kinds, and schema names. | `publication.attempts`, `publication.audit_chain`, and **N03**. Clock and UUID fragments are brokered operational outputs. |
| A16 | Physical gate-artifact placement and publish order — `uk_runtime/national_build.py:523-615,831-854`; `tools/build_uk_national_dataset.py:685-711,855-932` | Distinguishes the schema-4 signed terminal report from the last-written schema-1 alias and orders replay, evidence, reports, build record, gate, then staging H5 publication. | **N01** stage DAG, **N03** artifact dependencies/order, and `publication.promotion`. |

## Rowwise, geography, and calibration builds

| ID | Authority constructed in code | Current behavior | Flip owner |
| --- | --- | --- | --- |
| A17 | Geography route choice — `tools/build_uk_rowwise_dataset.py:92-107,345-451,613-627`; `tools/build_uk_rowwise_candidate.py:210-230,351-363` | The rowwise dataset chooses mutually exclusive ladder or crosswalk routes; absent crosswalk means live source assembly; ladder forbids separate coverage-code checks. The candidate is ladder-only. | **N10** named assignment routes and a typed run-request selector. The current geography schema has only one `ladder_source`. |
| A18 | Official geography source/assembly inventory — `uk_runtime/geography_sources.py:26-114,117-907,1641-1663`; `uk_runtime/oa_ladder_sources.py:37-65` | Embeds 18 public URL constants; 13 distinct defaults are consumed by the active no-crosswalk driver path, while the other five definitions serve the separately built ladder artifact or dormant helpers. It also fixes expected EW/Scotland/NI row counts, a 1% NI unmatched-postcode bound, and source assembly defaults. Crosswalk sources are mutable and not content-pinned. | `ir.resource("sources")`, `ir.vintage_authorities`, and compiled source nodes. Timeout, retry, User-Agent, and backoff belong to the execution profile/broker. Certification must use pinned bytes. |
| A19 | Crosswalk schema and geography vocabularies — `uk_runtime/rowwise_geography.py:18-91`; `tools/build_uk_rowwise_dataset.py:630-642` | Fixes required/output columns, area-type names, FRS region-to-country/region-code aliases, UK country codes, and CSV dtype treatment. | Geography derive/assertions, catalogs/domains, and compiled-node parameters; adapter maps should be generated where possible. |
| A20 | Crosswalk selection controls — `tools/build_uk_rowwise_dataset.py:128-170,439-450,675-700`; `uk_runtime/rowwise_geography.py:240-258` | Defaults to two clones and seed 42; requires all countries and nonblank constituencies; constrains to region; forbids zero-population distributions; avoids constituency collisions across clones with at most 50 retries. | **N10**, **N11**, `ir.seed_stream_map`, and typed run-request values. |
| A21 | Clone ID, weight, and lineage semantics — `uk_runtime/rowwise_dataset.py:45-67,110-133,267-315,420-445,555-569,875-914`; `uk_runtime/rowwise_geography.py:259-267`; `tools/build_uk_rowwise_dataset.py:162-171` | Uses one collision-free multiplier across entity IDs/foreign keys, emits clone indices, divides household weight by clone count, appends an exact mass record, optionally derives pool lineage by ID modulus, and applies `1e-9` mass tolerance. Ladder assignment intentionally has no cross-clone collision retry. | **N11**, **N02**, and **N03**. |
| A22 | OA-ladder artifact ABI and layer vocabulary — `uk_runtime/geography_ladder.py:92-178`; `uk_runtime/oa_ladder_sources.py:37-49` | Fixes derived/output layer order, London/EW region codes, artifact kind/schema/attributes, NPZ arrays, and GSS/ward/ITL code grammars. | Existing geography assignment/derive/assertion/layer-vintage fields, catalogs, and **N03**. The skeleton lists layers but not the artifact ABI or code domains. |
| A23 | Ladder draw plan and vintage refusal — `uk_runtime/geography_ladder.py:331-370,643-713`; `tools/build_uk_rowwise_candidate.py:221-230,354-363`; `tools/build_uk_rowwise_dataset.py:111-129,885-909,1029-1049` | Within preserved region, draws constituency by household totals, then OA by population; all other layers derive from the OA; requires `2024_pcon`. Kernel default is 0, but both production drivers default/pass 42. | Existing `geography.assignment.draw`, `derive`, `default_seed`, `seed`, and `layer_vintages`, plus `ir.seed_stream_map`. The 0-versus-42 discrepancy is a pre-dispatch blocker. |
| A24 | Ladder release gate — `uk_runtime/geography_ladder.py:476-640`; `tools/build_uk_rowwise_candidate.py:435-458`; `tools/build_uk_rowwise_dataset.py:1040-1054` | Enforces nesting/code validity and weighted nonempty shares: London 0.08–0.20, ward/ITL 0.98–1.00, constituency at least 0.99. Runs after assignment and again after candidate calibration. | UK battery metric/gate record referenced by the stage DAG. It is absent from current `uk/gates.json`; `geography.validation` can reference it once authored. |
| A25 | Target-family choice and provenance — `tools/build_uk_rowwise_candidate.py:77,368-374,577-610`; `uk_runtime/ladder_targets.py:26-95` | Binds exactly `census_households/constituency`; target controls are sorted sums of OA household counts and must derive from the same loaded ladder object used for assignment. | **N12**, selected by generalized calibration targets. Python object identity becomes a compiled content-pin equality. |
| A26 | Rowwise target matrix, naming, and ordering — `uk_runtime/local_rowwise.py:201-209,425-467`; `tools/build_uk_rowwise_candidate.py:589-610` | Uses a constant-one household metric, constituency assignment column, target code, incoming target-frame order, `{area_type}/{code}/{metric}` names, household weights, and a fail-closed complete surface. | Generalized calibration target matrix plus **N12** and compiled target nodes. Current calibration schema is US-specific. |
| A27 | Local solve doctrine and run options — `uk_runtime/local_doctrine.py:40-113`; `tools/build_uk_rowwise_candidate.py:84-88,221-230,411-422,802-827`; `uk_runtime/local_rowwise.py:470-554,609-639` | Capped relative-error loss, default target scales, uniform target weights, loss cap 10, max weight ratio 100, 512 epochs, LR 0.15, free mass, no target record count, L0=0, 10 budget iterations, and driver seed 42 (library default 0). | Country-neutral `ir.resource("calibration").solver/targets/release_modes` and run-request projection. Existing fields suffice once generalized. |
| A28 | Calibration mass/weight transition and post-gate — `uk_runtime/local_rowwise.py:498-554,642-665`; `tools/build_uk_rowwise_candidate.py:426-464,723-799` | Rejects zero base weights; FREE_MASS permits target-driven mass change; advances weight kind to CALIBRATED; requires the kernel mass record/reason; reruns the ladder gate; emits the weight-kind chain and support evidence. | Calibration hard constraints/attainment, producer-node output contract, battery gate, and **N03** artifact records. |
| A29 | Rowwise release/artifact protocol — `tools/build_uk_rowwise_candidate.py:78-88,112-117,142-164,723-827,903-910`; `tools/build_uk_rowwise_dataset.py:68-75,469-565,675-700` | Fixes filenames, manifest schema/build kind, `adjudicated_partial` candidate scope, diagnostics/support/past-cap sidecars, pipeline IDs, and build-ID templates. Candidate build and attempt identities hardcode rung tag `f100`, even when their national input is an f001 certification override. | **N03**, `publication.attempts`, and `publication.audit_chain`; UUID/time components stay operational. Preserve the incumbent `f100` tag at the flip unless the owner separately rules and inventories a semantic relabel. |
| A30 | Optional coverage and dry-run policy — `tools/build_uk_rowwise_dataset.py:73,119-127,661-672,1015-1060`; `tools/build_uk_rowwise_candidate.py:614-630` | Requires the four named UK countries unless waived, optionally checks constituency/LA code surfaces, uses a bottom-support count of 15, and makes dry-run execute the real assignment/gate while skipping solve/write. | Geography assertions, battery diagnostic metrics, **N03**, and a run mode in the execution profile—not an alternate semantic graph. |

## `NEW-SCHEMA-NEEDED` fields

These are **12 distinct field paths**, counted once even when several authority
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
| N09 | `publication.release.candidate_policy = {required_scale, required_signed_battery, forbidden_compat_outputs[], named_dev_exemptions[]}` |
| N10 | `geography.assignment.routes[] = {id, source_ref, kernel, availability_or_fallback, parameters, validation_refs[], output_columns[]}` |
| N11 | `geography.assignment.clone_policy = {n_clones, weight_split, id_strategy, lineage_fields[], collision_scope[], collision_policy, max_retries}` |
| N12 | `catalogs.targets[] = {id, family, geography, grain, measure, source_ref, aggregation, vintage_ref, universe, order}` |

The following are not added to the count because the semantic field already
exists but its schema is US-specific: publication rung fractions, battery
gates/metrics, calibration solver/targets, and the top-level spine pipeline
contract. They still must be made country-neutral before UK compilation can
succeed. In particular, the present F1 spine execution contract fixes the US
pipeline/artifact vocabulary, while the UK walking skeleton has no executable
producer nodes.

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
  30-row selected producer graph and must remain a closed experimental profile.
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
   records.
6. The publication schema's US release line/rung constraints do not describe
   the UK `populace-uk` tier/cardinality namespace, and the candidate's
   hardcoded `f100` receipt tag does not reflect an f001 national input.
