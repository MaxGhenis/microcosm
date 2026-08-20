# UK stochastic, hash, and ambient audit

## Result

An AST/source audit of all **55** `uk_runtime/*.py` modules (including
`__init__.py`) and the three requested UK drivers found **84 physical
callsites**:

| Class | Physical sites | Ledger/broker-owned | Typed exemptions |
| --- | ---: | ---: | ---: |
| Stochastic or seeded lifecycle | 47 | 32 | 15 |
| Deterministic hash | 17 | 0 | 17 |
| Ambient clock, UUID, or backoff | 20 | 1 | 19 |
| **Total** | **84** | **33** | **51** |

The 32 owned stochastic physical sites collapse/expand into **32 logical
draw-site ledger rows**: five hash-helper delegations expand to 18 output-keyed
streams, while ten QRF lifecycle calls bind to five model-chain rows. The one
behavior-affecting clock has a separate broker record. The 51 exemptions are
fully typed below; there are no unclassified sites.

This is an analysis of cached `origin/main@164027e21cfa58a71d701b43211d009d6182e39d`.
Line numbers refer to that tree. The strict count covers the requested UK files.
Reachable shared-kernel dependencies are called out separately and are not
double-counted.

## Proposed logical draw-site ledger

### Identity-keyed hash streams

All L01–L18 use the same exact family contract: BLAKE2b with an eight-byte
digest over UTF-8 `f"{int(seed)}:{salt}:{entity_id}"`; interpret the digest as
an unsigned big-endian 64-bit integer and divide by `2**64`. Each entity is
stateless and independent, so entity/table ordering changes only output array
order and never a shared cursor. There is no reset boundary.

| ID | Draw-site id | `rng_family` | `seed_material` | `consumption_order` | `reset_boundary` |
| --- | --- | --- | --- | --- | --- |
| L01 | `uk_frs_take_up.would_claim_child_benefit` | `BLAKE2b-64 identity uniform` | seed 0; salt `would_claim_child_benefit`; `benunit_id` | One digest per benefit unit; stateless | None |
| L02 | `uk_frs_take_up.child_benefit_opts_out` | Same | seed 0; salt `child_benefit_opts_out`; `benunit_id` | One digest per benefit unit; stateless | None |
| L03 | `uk_frs_take_up.would_claim_pc` | Same | seed 0; salt `would_claim_pc`; `benunit_id` | One digest per benefit unit; stateless | None |
| L04 | `uk_frs_take_up.would_claim_uc` | Same | seed 0; salt `would_claim_uc`; `benunit_id` | One digest per benefit unit; stateless | None |
| L05 | `uk_frs_take_up.would_claim_tfc` | Same | seed 0; salt `would_claim_tfc`; `benunit_id` | One digest per benefit unit; stateless | None |
| L06 | `uk_frs_take_up.would_claim_extended_childcare` | Same | seed 0; salt `would_claim_extended_childcare`; `benunit_id` | One digest per benefit unit; stateless | None |
| L07 | `uk_frs_take_up.would_claim_universal_childcare` | Same | seed 0; salt `would_claim_universal_childcare`; `benunit_id` | One digest per benefit unit; stateless | None |
| L08 | `uk_frs_take_up.would_claim_targeted_childcare` | Same | seed 0; salt `would_claim_targeted_childcare`; `benunit_id` | One digest per benefit unit; stateless | None |
| L09 | `uk_frs_take_up.maximum_extended_childcare_hours_usage` | Same | seed 0; salt equals output; `benunit_id` | One digest per benefit unit, then clipped-normal inverse CDF | None |
| L10 | `uk_frs_person_draws.would_claim_marriage_allowance` | Same | seed 0; salt equals output; `person_id` | One digest per person; stateless | None |
| L11 | `uk_frs_person_draws.would_claim_scp` | Same | seed 0; salt equals output; `person_id` | One digest per person, compared with age-band rate | None |
| L12 | `uk_frs_person_draws.attends_private_school_random_draw` | Same | seed 0; salt equals output; `person_id` | One digest per person; emitted directly | None |
| L13 | `uk_frs_household_draws.household_owns_tv` | Same | seed 0; salt equals output; `household_id` | One digest per household; stateless | None |
| L14 | `uk_frs_household_draws.would_evade_tv_licence_fee` | Same | seed 0; salt equals output; `household_id` | One digest per household; stateless | None |
| L15 | `uk_frs_household_draws.main_residential_property_purchased_is_first_home` | Same | seed 0; salt equals output; `household_id` | One digest per household; stateless | None |
| L16 | `uk_frs_household_draws.property_purchased` | Same | seed 0; salt equals output; `household_id` | One digest per household; stateless | None |
| L17 | `uk_frs_brma_benunit` | Same | seed 0; salt `brma`; `benunit_id` | One digest per benefit unit; inverse CDF over sorted count categories | None |
| L18 | `uk_frs_brma_household_pick` | Same | seed 0; salt `brma:household_pick`; `household_id` | One digest per household; member options sorted by `benunit_id` | None |

The physical helper implementation is
`packages/microcosm-build/src/microcosm/build/stochastic_assignment.py:21-44`.
The five UK delegations that own these 18 logical rows appear in the physical
manifest below.

### Sequential/model streams

| ID | Draw-site id | `rng_family` | `seed_material` | `consumption_order` | `reset_boundary` |
| --- | --- | --- | --- | --- | --- |
| L19 | `uk_cgt_within_band_amounts` | NumPy `Generator(PCG64)` | `SeedSequence((seed_base=552, int(time_period)))` | Fixed CGT allocation/band order, highest-gain band first; `count` uniforms only for nonempty allocations | New generator per CGT stage invocation |
| L20 | `uk_oa_ladder_assignment` | NumPy `Generator(PCG64)` | Rowwise run seed; current drivers default 42 | Sorted region groups; constituency choice first; then OA choices by sorted chosen constituency; input ladder order and weights sealed | New generator per assignment call |
| L21 | `uk_rowwise_crosswalk_geography` | NumPy `Generator(PCG64)` | Rowwise run seed; current driver default 42 | Clone order, sorted country/region keys, initial choices, then collision-resample loop up to 50; crosswalk row order and collision history sealed | New generator per assignment call |
| L22 | `uk_national_household_sample` | NumPy `Generator(PCG64)` in shared sampler | Sample seed, default 578 | Sorted stratum keys and unit IDs; one without-replacement choice per partially selected stratum; fraction 1 consumes nothing | New generator per sample call only when fraction < 1 |
| L23 | `uk_spi_support_unstratified` | NumPy `Generator(PCG64)` | Source operation/run seed 42 | One without-replacement position choice; selected set emitted in input household order | New generator per support-copy call |
| L24 | `uk_spi_support_replacement` | NumPy `Generator(PCG64)` | Source operation/run seed 42 | Sorted `(clone_index, capital-gains flag, region)` dead strata; one without-replacement choice per stratum; final IDs restored to base input order | New generator per replacement call |
| L25 | `uk_spi_donor_age_jitter` | NumPy `Generator(PCG64)` | Build seed 42 by default | One vector uniform in raw donor row order, mapped within published age bands | New generator per donor preparation |
| L26 | `uk_spi_donor_bootstrap` | pandas weighted sample using NumPy legacy `RandomState(MT19937)` under the pinned pandas ABI | Build seed 42 by default, donor FACT weights | 100,000 replacement draws in pandas-emitted order | pandas reconstructs state for each `.sample` call |
| L27 | `uk_spi_qrf_stage1` | Shared QRF `SeedSequence(42).spawn(2)`: PCG64 child 0 fit, child 1 draws; estimator RNGs derived by the QRF ABI | Stage-1 seed 42; tree count 100 | Exact 18-target source order. Fit once, predict SPI recipients, then predict all 18 targets again for canonical base rows even though only `dividend_income` is retained; the draw cursor advances across both predicts | New QRF object/child pair per stage-1 construction |
| L28 | `uk_spi_qrf_stage2` | Same QRF family | Stage-2 seed 43 (`seed + 1`); tree count 100 | Exact authored 29-target stage-2 order; one recipient prediction | New QRF object/child pair per stage-2 construction |
| L29 | `uk_was_qrf_segment_1` | Same QRF family | Seed 0 | `owned_land`, then `property_wealth` | `start_chain` creates a fresh fit/draw child pair for this segment |
| L30 | `uk_was_qrf_segment_2` | Same QRF family | Seed 0 | `corporate_wealth_excl_isa`, then `stocks_and_shares_isa`; derived `corporate_wealth` is not drawn | Fresh `start_chain`; deliberately repeats seed 0 |
| L31 | `uk_was_qrf_segment_3` | Same QRF family | Seed 0 | `gross_financial_wealth`, `net_financial_wealth`, `main_residence_value`, `other_residential_property_value`, `non_residential_property_value`, `savings`, `num_vehicles`, `student_loan_balance`, `cash_isa` | Fresh `start_chain`; deliberately repeats seed 0 |
| L32 | `uk_rowwise_l0_gate` | Torch global generator / HardConcrete calibration ABI | Rowwise solve seed, driver default 42 | Current selected L0=0 path consumes no random draw; if enabled, epoch, record, and budget-search evaluation order are exact authority | Reset at `calibrate()` and each seeded L0 evaluation; reserved conditional site |

L27–L31 must bind the certified F1 shared-QRF implementation digest, target
order, bootstrap order, estimator derivation, and draw-cursor behavior. Merely
recording the constructor seed is insufficient.

### Behavior-affecting clock broker record

| ID | Site | Family/material | Consumption and reset |
| --- | --- | --- | --- |
| C01 | `uk_runtime/weighted_integrity.py:474` | UTC calendar date supplied by `ClockBroker` or sealed run request as `exclusions_evaluated_on` | Resolve exactly once before the stage/gate chain and receipt it; reset per build. Crossing midnight must not silently change exclusion-expiry verdicts. |

## Physical stochastic/seeded manifest — 47 sites

Each owned row maps to one or more logical ledger IDs above. Exempt rows name an
exact typed exemption.

| Site | Physical API | Disposition |
| --- | --- | --- |
| `uk_runtime/cgt_imputation.py:471` | `np.random.default_rng((seed, time_period))` | L19 |
| `uk_runtime/cgt_imputation.py:517` | `rng.random(count)` | L19 |
| `uk_runtime/geography_ladder.py:658` | `np.random.default_rng(seed)` | L20 |
| `uk_runtime/geography_ladder.py:689` | `rng.choice(...)` | L20 |
| `uk_runtime/geography_ladder.py:703` | `rng.choice(...)` | L20 |
| `uk_runtime/rowwise_geography.py:312` | `np.random.default_rng(seed)` | L21 |
| `uk_runtime/rowwise_geography.py:704` | `rng.choice(...)` | L21 |
| `uk_runtime/rowwise_geography.py:731` | `rng.choice(...)` | L21 |
| `uk_runtime/spi_income.py:373` | `DataFrame.sample(..., random_state=seed)` | L26 |
| `uk_runtime/spi_income.py:631` | `np.random.default_rng(seed)` | L25 |
| `uk_runtime/spi_income.py:635` | `rng.random(len(raw))` | L25 |
| `uk_runtime/spi_support.py:676` | `np.random.default_rng(seed)` | L23 |
| `uk_runtime/spi_support.py:678` | `rng.choice(..., replace=False)` | L23 |
| `uk_runtime/spi_support.py:729` | `np.random.default_rng(seed)` | L24 |
| `uk_runtime/spi_support.py:740` | `rng.choice(..., replace=False)` | L24 |
| `uk_runtime/firm_generation.py:711` | `torch.manual_seed` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:712` | `np.random.seed` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:857` | `torch.distributions.Beta(...).sample` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:859` | `torch.randn` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:865` | `torch.rand` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:866` | `torch.rand` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:899` | `torch.randint` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:902` | `torch.normal` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:905` | `torch.rand` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:910` | `np.random.shuffle` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:936` | `torch.randperm` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:1072` | `torch.manual_seed` | `experimental_library_only_firm_generator`; second reset, presently no optimizer draw |
| `uk_runtime/firm_generation.py:1384` | `torch.rand` | `experimental_library_only_firm_generator` |
| `uk_runtime/firm_generation.py:1385` | `torch.normal` | `experimental_library_only_firm_generator` |
| `uk_runtime/frs_take_up.py:173` | `stable_identity_uniforms(...)` | L01–L09 |
| `uk_runtime/frs_person_draws.py:88` | `stable_identity_uniforms(...)` | L10–L12 |
| `uk_runtime/frs_household_draws.py:86` | `stable_identity_uniforms(...)` | L13–L16 |
| `uk_runtime/frs_brma.py:111` | `stable_identity_uniforms(...)` | L17 |
| `uk_runtime/frs_brma.py:146` | `stable_identity_uniforms(...)` | L18 |
| `uk_runtime/spi_income.py:443` | QRF constructor | L27 |
| `uk_runtime/spi_income.py:443` | QRF `.fit(...)` | L27 |
| `uk_runtime/spi_income.py:449` | fitted QRF `.predict(...)` | L27 |
| `uk_runtime/spi_income.py:511` | QRF constructor | L28 |
| `uk_runtime/spi_income.py:511` | QRF `.fit(...)` | L28 |
| `uk_runtime/spi_income.py:517` | fitted QRF `.predict(...)` | L28 |
| `uk_runtime/spi_income.py:538` | stage-1 fitted QRF `.predict(...)` | L27; advances after the SPI prediction |
| `uk_runtime/was_wealth.py:364` | `RegimeGatedQRF(...)` constructor | L29–L31 |
| `uk_runtime/was_wealth.py:369` | `model.start_chain(...)` | L29–L31; three dynamic invocations |
| `uk_runtime/was_wealth.py:381` | `model.fit_draw_next(...)` | L29–L31; once per ordered target |
| `uk_runtime/hmrc_calibration.py:340` | seeded `calibrate(...)` lifecycle | `ambient_rng_reset_without_draw`: dormant from requested drivers; fixed L0=0/no-target-selection path only resets Torch |
| `uk_runtime/local_rowwise.py:540` | seeded `calibrate(...)` lifecycle | L32; current profile consumes zero but future activation is fail-closed |
| `uk_runtime/national_sampling.py:335` | shared `sample_frame_households(...)` stochastic delegation | L22 |

The 14 firm sites are callable only in an experimental firm-generation
profile, not the selected national/rowwise producer graph. Their exemption is
valid only while that profile remains closed. If selected later, each becomes a
ledger site and must pin Torch/NumPy versions, device/backend, global-reset
scope, and exact tensor/record order.

## Deterministic hash manifest — 17 typed exemptions

These calls do not draw. They remain in the physical census so a future use of
a hash as a stochastic selector cannot hide among ordinary integrity hashes.

| Site | API/use | Typed exemption |
| --- | --- | --- |
| `uk_runtime/content_identity.py:59` | SHA-256 frame identity | `content_identity` |
| `uk_runtime/content_identity.py:75` | `pandas.util.hash_pandas_object` table rows | `content_identity` |
| `uk_runtime/content_identity.py:85` | `pandas.util.hash_pandas_object` strata | `content_identity` |
| `uk_runtime/take_up_contract.py:88` | SHA-256 canonical contract | `content_identity` |
| `uk_runtime/weighted_integrity.py:825` | SHA-256 canonical registry | `content_identity` |
| `tools/build_uk_national_dataset.py:804` | SHA-256 run configuration | `content_identity` |
| `tools/build_uk_rowwise_candidate.py:139` | SHA-256 candidate identity | `content_identity` |
| `tools/build_uk_rowwise_dataset.py:231` | SHA-256 rowwise identity | `content_identity` |
| `uk_runtime/frs_hmrc_leaves.py:889` | SHA-256 input file | `source_integrity` |
| `uk_runtime/hmrc_capital_gains.py:254` | SHA-256 source file | `source_integrity` |
| `uk_runtime/hmrc_income.py:909` | SHA-256 source file | `source_integrity` |
| `uk_runtime/hmrc_restoration.py:768` | SHA-256 candidate/input | `source_integrity` |
| `uk_runtime/release_input_coverage.py:1186` | SHA-256 source coverage input | `source_integrity` |
| `uk_runtime/spi_income.py:1073` | SHA-256 SPI donor | `source_integrity` |
| `tools/build_uk_national_dataset.py:1008` | streaming artifact SHA-256 | `source_integrity` |
| `tools/build_uk_rowwise_candidate.py:1019` | streaming artifact SHA-256 | `source_integrity` |
| `tools/build_uk_rowwise_dataset.py:1439` | streaming artifact SHA-256 | `source_integrity` |

The two pandas hashes are deliberately environment-sensitive content identity,
not portable artifact hashes; the pinned runtime environment is part of the
run identity. No built-in `hash`, direct `RandomState` constructor, stdlib
`random`, `secrets`, `os.urandom`, or UUIDv1 site exists in the requested
scope.

## Ambient manifest — 20 sites

| Site | API/use | Disposition |
| --- | --- | --- |
| `uk_runtime/diagnostics.py:488` | `uuid.uuid4()` temp filename | `operational_nonce` |
| `uk_runtime/national_build.py:269` | `uuid.uuid4()` temp H5 filename | `operational_nonce` |
| `tools/build_uk_national_dataset.py:374` | `uuid.uuid4()` attempt ID | `operational_nonce` |
| `tools/build_uk_national_dataset.py:388` | `uuid.uuid4()` build ID | `operational_nonce` |
| `tools/build_uk_national_dataset.py:1138` | `uuid.uuid4()` temp filename | `operational_nonce` |
| `tools/build_uk_rowwise_candidate.py:116` | `uuid.uuid4()` build ID | `operational_nonce` |
| `tools/build_uk_rowwise_dataset.py:206` | `uuid.uuid4()` build ID | `operational_nonce` |
| `uk_runtime/weighted_integrity.py:474` | `datetime.now(UTC).date()` exclusion-expiry date | **C01, behavior-affecting clock; not exempt** |
| `tools/build_uk_national_dataset.py:530` | `datetime.now(UTC)` attempt timestamp | `operational_timestamp` |
| `tools/build_uk_rowwise_candidate.py:267` | `datetime.now(UTC)` attempt timestamp | `operational_timestamp` |
| `tools/build_uk_rowwise_candidate.py:746` | `datetime.now(UTC)` manifest timestamp | `operational_timestamp` |
| `tools/build_uk_rowwise_dataset.py:299` | `datetime.now(UTC)` attempt timestamp | `operational_timestamp` |
| `tools/build_uk_rowwise_dataset.py:472` | `datetime.now(UTC)` manifest timestamp | `operational_timestamp` |
| `tools/build_uk_rowwise_dataset.py:792` | `datetime.now(UTC)` dry-run manifest timestamp | `operational_timestamp` |
| `tools/build_uk_rowwise_dataset.py:930` | `datetime.now(UTC)` ladder manifest timestamp | `operational_timestamp` |
| `tools/build_uk_rowwise_dataset.py:1064` | `datetime.now(UTC)` ladder plan timestamp | `operational_timestamp` |
| `tools/build_uk_national_dataset.py:529` | `time.perf_counter()` attempt start | `attempt_timing` |
| `tools/build_uk_rowwise_candidate.py:266` | `time.perf_counter()` attempt start | `attempt_timing` |
| `tools/build_uk_rowwise_dataset.py:298` | `time.perf_counter()` attempt start | `attempt_timing` |
| `uk_runtime/geography_sources.py:1663` | `time.sleep(...)` retry backoff | `network_retry_backoff`; no numerical consumption |

Operational nonce/timestamp/timing fields are excluded from numerical and node
identity only through the sealed comparison vector; they are still brokered and
receipted. The retry exemption owns delay only, never permission to accept
unhashed mutable source bytes.

## Declared-seed reconciliation

| Surface | Declaration versus execution | Verdict for flip |
| --- | --- | --- |
| FRS take-up/person/household draws | `source_stages.json` declares seed 0 per output; all runtime maps and helper calls use 0. `take_up_contract.json` seed 42 values describe offline fitting receipts, while historical take-up seed 100 is provenance. | **Match.** The compiler must not misclassify offline 42 or incumbent 100 as runtime streams. |
| BRMA | Source operation declares seed 0; runtime uses 0 for both `brma` and `brma:household_pick`. | **Match**, but one authored operation must compile two reset-free logical sites. |
| CGT | `cgt_source_stages.json` declares `seed_base: 552` and period mixing; runtime constructs `(552, time_period)`. | **Match.** `deterministic: true` means seeded-deterministic, not draw-free. |
| SPI support | Authored support operation declares 42; runtime support/replacement defaults and assertions use 42. | **Match**, with two distinct reset boundaries L23/L24. |
| SPI/HMRC QRF alternate spine | `source_stages.json`'s `hmrc_spi_income_spine` declares strict-read 42, stage 1 seed 42, and stage 2 seed 43. Runtime independently resets seed 42 for donor age jitter, pandas bootstrap, and QRF stage 1, then constructs stage 2 with `seed + 1`. | **Partly descriptive, not sufficient.** The strict read is draw-free and cannot own all three seed-42 streams; each needs a ledger row. |
| SPI/HMRC active national stage | The driver selects `hmrc_spi_income` (`tools/build_uk_national_dataset.py:839`), whose `hmrc_income_source_stages.json` operations contain no seed fields. CLI default 42 is the live owner and derives 43. | **Active-path authority gap.** Bundle mode must compile explicit 42/43 sites into the selected node. |
| WAS | Source declares one seed-0 QRF chain with a 14-name chain order including derived `corporate_wealth`; runtime executes three fresh seed-0 chains and draws 13 outputs. | **Reset/order mismatch in representation.** Author L29–L31 and mark `corporate_wealth` derived. |
| National rung sampling | Runtime/driver declare sample seed 578; it is outside source stages. | **Unowned until** `spine.sampling` and the seed map carry L22. |
| Geography | Ladder kernel defaults to 0; both rowwise drivers default/pass 42; the spec-branch geography skeleton also says default 0. Crosswalk order/retry behavior has no declarative seed protocol. | **Blocking conflict.** Seal run seed 42 if preserving production bytes, and author L20/L21 exactly. |
| Rowwise calibration | Driver passes 42, library default is 0, current L0 is disabled. | **Conditional ownership required.** L32 prevents future L0 activation from introducing an undeclared draw. |
| Firm generator | Defaults to 42 and mutates NumPy/Torch global RNGs, but is outside the selected driver graph. | Typed experimental exemption only while profile-closed. |

## Reachable shared-kernel closure

These sites sit outside the requested 58-file physical count but must be pinned
or brokered by the upstream certified F1 ABI:

- `microcosm/build/stochastic_assignment.py:33` implements the BLAKE2b draw
  used by L01–L18.
- `microcosm/build/frame_sampling.py:258,267` constructs/consumes the PCG64
  generator behind L22.
- `microcosm-fit/qrf.py` owns SeedSequence spawning, weighted bootstrap,
  estimator seeds, and draw uniforms for L27–L31. On this baseline,
  `qrf.py:640` calls ambient `default_rng()` before restoring serialized state.
  UK F1 must inherit the US F1 correction (`Generator(PCG64(0))` before state
  restore) and its implementation digest.
- `microcosm-calibrate/solve.py:1126,1600` owns Torch resets and conditional
  HardConcrete draws behind calibration.
- The three drivers call shared `resolve_predecessor`, which reads
  `POPULACE_LOGBOOK_PREV_ROW_DIGEST`; shared logbook code also reads a duration
  clock and generates temp nonces. Those environment/clock/UUID operations must
  pass through the certified brokers even though they are not UK-file sites.

## Highest-risk findings

1. The active `hmrc_spi_income` stage has no authored seed fields. Seed 42 is
   reused across three unrelated RNG families, then 43 is derived in code.
2. The WAS document says one chain; runtime resets the same seed for three
   chains and treats one documented chain member as derived rather than drawn.
3. Exclusion expiry depends on the current UTC date and can change a gate
   verdict for identical inputs and seeds.
4. Geography has a live 42-versus-spec-0 conflict, and both sequential routes
   depend on sealed source row/group/collision order.
5. The baseline shared QRF restore touches ambient entropy. UK dispatch must be
   conditional on inheriting the certified F1 broker/fix.
6. Firm-generation helpers mutate global NumPy/Torch state and can vary by
   backend/device. They must remain outside the selected profile or receive a
   separate full ledger.
