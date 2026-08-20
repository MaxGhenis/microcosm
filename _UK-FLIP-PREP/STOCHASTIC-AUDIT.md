# UK stochastic, hash, and ambient-call audit

## Result and method

The scanner classified **80 AST `Call` nodes**, of which **79 are actual
scoped stochastic/hash/ambient/control callsites** and one (`np.power`) is a
deterministic lexical false positive:

- **40 stochastic/control/model calls** covered by a proposed draw ledger;
- **38 true exemptions**: 17 deterministic hashes, nine operational nonces
  (seven explicit UUIDs and two implicit temporary-name allocations), and 12
  operational clocks/timers;
- **one policy-significant ambient clock** that must be brokered and bound;
- **one scanner-only false positive**, reported for census reproducibility.

Those 40 physical calls lower to **34 logical ledger rows**: 32 rows that can
draw or hash-draw and two reset-only calibration-control rows. Five physical
stable-identity helper calls expand to 18 logical output streams. Counts in
this report distinguish 80 classified AST candidates, 79 actual scoped
callsites, and 34 logical ledger sites.

Scope is all 55 `uk_runtime/*.py` modules plus:

- `tools/build_uk_national_dataset.py`;
- `tools/build_uk_rowwise_candidate.py`;
- `tools/build_uk_rowwise_dataset.py`.

The audit used the US F1 `_CallsiteVisitor` lexical classes (`np.random`,
`default_rng`, `RandomState`, framework/model constructors, hashes, UUIDs),
then an AST semantic-boundary pass for five stable-identity calls, two dynamic
QRF constructors, two shared calibrator calls, the shared frame sampler, and
two temporary-name allocations, then an explicit clock pass. No scoped use of
stdlib `random`, `RandomState`, `SeedSequence`/BitGenerator construction,
built-in `hash()`, `secrets`, or explicit OS entropy outside those temp-name
helpers was found. Ordinary hashes are listed as exemptions rather than being
silently discarded.

The count reproduces as 55 F1-lexical calls (30 stochastic/control/model, 17
deterministic hashes, seven UUIDs, and one `np.power` false positive), plus ten
stochastic semantic-boundary calls, plus two temp-name semantic-boundary calls,
plus 13 clock/time calls (12 operational and one policy-significant):
55 + 10 + 2 + 13 = 80.

## Proposed draw-site ledger

For H001-H018, the family is the shared stable-identity kernel: BLAKE2b,
8-byte digest, UTF-8 message `seed:salt:id`, unsigned big-endian integer divided
by `2**64`. It is stateless and order-independent; reset boundary is
`none/per identity`. The categorical inverse CDF is deterministic and does not
consume a second draw.

| ID | Logical site and current callsite | `rng_family` | `seed_material` | `consumption_order` | `reset_boundary` |
| --- | --- | --- | --- | --- | --- |
| H001 | `would_claim_child_benefit` (`uk_runtime/frs_take_up.py:173`) | `blake2b64_identity_uniform` | `0`, salt = output, stable benunit ID | one hash per eligible identity; order-independent | none/per identity |
| H002 | `child_benefit_opts_out` (`uk_runtime/frs_take_up.py:173`) | same | `0`, output salt, stable benunit ID | same | none/per identity |
| H003 | `would_claim_pc` (`uk_runtime/frs_take_up.py:173`) | same | `0`, output salt, stable benunit ID | same | none/per identity |
| H004 | `would_claim_uc` (`uk_runtime/frs_take_up.py:173`) | same | `0`, output salt, stable benunit ID | same | none/per identity |
| H005 | `would_claim_tfc` (`uk_runtime/frs_take_up.py:173`) | same | `0`, output salt, stable benunit ID | same | none/per identity |
| H006 | `would_claim_extended_childcare` (`uk_runtime/frs_take_up.py:173`) | same | `0`, output salt, stable benunit ID | same | none/per identity |
| H007 | `would_claim_universal_childcare` (`uk_runtime/frs_take_up.py:173`) | same | `0`, output salt, stable benunit ID | same | none/per identity |
| H008 | `would_claim_targeted_childcare` (`uk_runtime/frs_take_up.py:173`) | same | `0`, output salt, stable benunit ID | same | none/per identity |
| H009 | `maximum_extended_childcare_hours_usage` (`uk_runtime/frs_take_up.py:173`) | same, then deterministic clipped-normal transform | `0`, output salt, stable benunit ID | same | none/per identity |
| H010 | `would_claim_marriage_allowance` (`uk_runtime/frs_person_draws.py:88`) | `blake2b64_identity_uniform` | `0`, output salt, stable person ID | one hash per identity; order-independent | none/per identity |
| H011 | `would_claim_scp` (`uk_runtime/frs_person_draws.py:88`) | same | `0`, output salt, stable person ID | same | none/per identity |
| H012 | `attends_private_school_random_draw` (`uk_runtime/frs_person_draws.py:88`) | same | `0`, output salt, stable person ID | same | none/per identity |
| H013 | `household_owns_tv` (`uk_runtime/frs_household_draws.py:86`) | `blake2b64_identity_uniform` | `0`, output salt, stable household ID | one hash per identity; order-independent | none/per identity |
| H014 | `would_evade_tv_licence_fee` (`uk_runtime/frs_household_draws.py:86`) | same | `0`, output salt, stable household ID | same | none/per identity |
| H015 | `main_residential_property_purchased_is_first_home` (`uk_runtime/frs_household_draws.py:86`) | same | `0`, output salt, stable household ID | same | none/per identity |
| H016 | `property_purchased` (`uk_runtime/frs_household_draws.py:86`) | same | `0`, output salt, stable household ID | same | none/per identity |
| H017 | BRMA benunit categorical draw (`uk_runtime/frs_brma.py:111`) | `blake2b64_identity_uniform` | `0`, salt `brma`, stable benunit ID | one hash then deterministic inverse CDF | none/per identity |
| H018 | BRMA household-member selection (`uk_runtime/frs_brma.py:146`) | same | `0`, salt `brma:household_pick`, stable household ID | one hash then deterministic member index | none/per identity |
| R019 | CGT allocation quantiles (`uk_runtime/cgt_imputation.py:471,517`) | NumPy `Generator/PCG64` | tuple `(552, int(time_period))` | one uniform per allocated gainer in nested declared band/plan order; gains-descending/person-ID tie order downstream | once per CGT stage invocation |
| R020 | Firm Torch pre-solve generator (`uk_runtime/firm_generation.py:711,857,859,865-866,899,902,905,936,1384-1385`) | global Torch default generator; device/backend/version sensitive | firm config seed, default 42 | exact execution order: turnover/base inputs, employment, VAT; draw branches consume conditionally | reset at `manual_seed` line 711 |
| R021 | Firm NumPy employment shuffle (`uk_runtime/firm_generation.py:712,910`) | NumPy legacy global MT19937 | firm config seed, default 42 | base-employment shuffle; a zero-turnover shuffle continues the same stream if reached | reset once at line 712 |
| R022 | Firm post-solve zero-turnover Torch stream, reset at the calibration boundary (`uk_runtime/firm_generation.py:1072` then shared draw lines 899,902,905) | global Torch default generator | firm config seed, default 42 | current calibration consumes no RNG; later zero-turnover employment draws in execution order. If calibration posture changes, optimizer draws advance this same stream. | reset at line 1072 immediately before calibration |
| R023 | OA-ladder geography (`uk_runtime/geography_ladder.py:658,689,703`) | NumPy `Generator/PCG64` | effective driver seed; CLI default 42, function default 0 | sorted regions -> weighted constituency choices; sorted chosen constituencies -> OA population choices | once per assignment invocation |
| R024 | Crosswalk rowwise geography (`uk_runtime/rowwise_geography.py:312,704,731`) | NumPy `Generator/PCG64` | driver seed, default 42 | clone index ascending and sorted country/region keys; initial draw, then retry rounds 0..49 consume only collision set | once per assignment invocation |
| R025 | Initial SPI support selection (`uk_runtime/spi_support.py:676,678`) | NumPy `Generator/PCG64` | 42 | no-replacement positions, then restore source-row order; skipped when IDs supplied/count absent | once per support-table build |
| R026 | Replacement SPI support selection (`uk_runtime/spi_support.py:729,740`) | NumPy `Generator/PCG64` | 42 | strata sorted by `_stratum_sort_key`; one no-replacement choice per dead quota | once per replacement invocation |
| R027 | SPI donor age within bands (`uk_runtime/spi_income.py:631,635`) | NumPy `Generator/PCG64` | 42 | vector draw in raw donor-row order | once per income-stage run |
| R028 | SPI donor bootstrap (`uk_runtime/spi_income.py:373`) | pandas `DataFrame.sample` legacy MT19937 | 42 via `random_state` | 100,000 replacement draws weighted by `FACT`; returned order controls later consumption; skipped when sample size is null | fresh generator per sample call |
| R029 | SPI QRF stage 1 (`uk_runtime/spi_income.py:443`) | shared QRF `SeedSequence(seed).spawn(2)` / PCG64 fit and draw streams | declared 42 | target/regime fit order, forest/bootstrap draws, then target/row/gated-sign draw order; base redraw can continue stream | once per stage-1 QRF chain |
| R030 | SPI QRF stage 2 (`uk_runtime/spi_income.py:511`) | same shared QRF family | `seed + 1`, therefore declared 43 at default | stage-2 target/regime/row order | once per stage-2 QRF chain |
| R031 | WAS QRF chains (`uk_runtime/was_wealth.py:364`) | shared QRF `SeedSequence(0).spawn(2)` / PCG64 | declared 0 | three code-segment orders: land/property; corporate/ISA; remaining wealth vector | **fresh `start_chain` for each of three segments** |
| R032 | National household-family sample (`uk_runtime/national_sampling.py:335`) | shared frame sampler `Generator/PCG64` | `--sample-seed`, default 578 | sorted region strata and family IDs; one no-replacement choice per partial nonzero group | once iff fraction < 1; fraction 1 constructs no RNG |
| C033 | Candidate local calibration control (`uk_runtime/local_rowwise.py:540`) | shared calibrator Torch global reset | candidate seed, driver default 42 | no draws under current `target_records=None,l0=0`; HardConcrete epoch/evaluation draws become live if posture changes | reset once per `calibrate` call |
| C034 | HMRC calibration control (`uk_runtime/hmrc_calibration.py:340`) | shared calibrator Torch global reset | default 42 | same reset-only current posture; stochastic gate draws if l0/selection is enabled | reset once per `calibrate` call |

R020-R022 are exported/experimental and are not reached by the three named
drivers. They remain ledger rows because the requested scope includes every
`uk_runtime` module.

## Physical callsite closure

This table proves that every one of the **40 ledger-bound AST calls** maps to
at least one row above. The shared firm calls at lines 899, 902, and 905 run
under the line-711 reset before solve and, when adding zero-turnover firms,
under the line-1072 calibration-boundary reset; each physical call is counted
once here.

| Physical callsite(s) | Ledger row(s) |
| --- | --- |
| `frs_take_up.py:173` | H001-H009 |
| `frs_person_draws.py:88` | H010-H012 |
| `frs_household_draws.py:86` | H013-H016 |
| `frs_brma.py:111`; `:146` | H017; H018 |
| `cgt_imputation.py:471`; `:517` | R019 |
| `firm_generation.py:711`; `:712`; `:857`; `:859`; `:865`; `:866`; `:899`; `:902`; `:905`; `:910`; `:936`; `:1072`; `:1384`; `:1385` | R020-R022 |
| `geography_ladder.py:658`; `:689`; `:703` | R023 |
| `rowwise_geography.py:312`; `:704`; `:731` | R024 |
| `spi_support.py:676`; `:678`; `:729`; `:740` | R025-R026 |
| `spi_income.py:373`; `:443`; `:511`; `:631`; `:635` | R027-R030 |
| `was_wealth.py:364` | R031 |
| `national_sampling.py:335` | R032 |
| `local_rowwise.py:540` | C033 |
| `hmrc_calibration.py:340` | C034 |

The physical total is 5 stable-identity calls + 2 CGT + 14 firm + 3 ladder
+ 3 crosswalk + 4 SPI-support + 5 SPI-income + 1 WAS + 1 national sampler +
2 calibrators = 40.

## Non-ledger classifications

### Deterministic content and integrity hashes (17)

These calls do not draw. They must remain implementation-pinned because
pandas hashing in particular depends on algorithm/key/version.

| ID | Callsite | Exemption and constraint |
| --- | --- | --- |
| E001 | `uk_runtime/content_identity.py:59` `hashlib.sha256` | `content_identity`; deterministic canonical frame digest |
| E002 | `uk_runtime/content_identity.py:75` `pd.util.hash_pandas_object` | `content_identity`; pin pandas hash algorithm/key/version |
| E003 | `uk_runtime/content_identity.py:85` `pd.util.hash_pandas_object` | same |
| E004 | `uk_runtime/frs_hmrc_leaves.py:889` `hashlib.sha256` | `source_integrity` |
| E005 | `uk_runtime/hmrc_capital_gains.py:254` `hashlib.sha256` | `source_integrity` |
| E006 | `uk_runtime/hmrc_income.py:909` `hashlib.sha256` | `source_integrity` |
| E007 | `uk_runtime/hmrc_restoration.py:768` `hashlib.sha256` | `source_integrity` |
| E008 | `uk_runtime/release_input_coverage.py:1186` `hashlib.sha256` | `contract_identity` |
| E009 | `uk_runtime/spi_income.py:1073` `hashlib.sha256` | `source_integrity` |
| E010 | `uk_runtime/take_up_contract.py:88` `hashlib.sha256` | `contract_identity` |
| E011 | `uk_runtime/weighted_integrity.py:825` `hashlib.sha256` | `evidence_identity` |
| E012 | `tools/build_uk_national_dataset.py:804` `hashlib.sha256` | `run_config_identity`; deterministic canonical JSON |
| E013 | `tools/build_uk_national_dataset.py:1008` `hashlib.sha256` | `artifact_integrity` |
| E014 | `tools/build_uk_rowwise_candidate.py:139` `hashlib.sha256` | `candidate_identity`; deterministic canonical JSON |
| E015 | `tools/build_uk_rowwise_candidate.py:1019` `hashlib.sha256` | `artifact_integrity` |
| E016 | `tools/build_uk_rowwise_dataset.py:231` `hashlib.sha256` | `rowwise_identity`; deterministic canonical JSON |
| E017 | `tools/build_uk_rowwise_dataset.py:1439` `hashlib.sha256` | `artifact_integrity` |

### Operational nonces (9)

| ID | Callsite | Exemption and constraint |
| --- | --- | --- |
| E018 | `uk_runtime/diagnostics.py:488` `uuid.uuid4` | `operational_nonce`; atomic temp path only |
| E019 | `uk_runtime/national_build.py:269` `uuid.uuid4` | `operational_nonce`; atomic temp H5 only |
| E020 | `tools/build_uk_national_dataset.py:374` `uuid.uuid4` | `operational_nonce`; attempt ID |
| E021 | `tools/build_uk_national_dataset.py:388` `uuid.uuid4` | `operational_nonce`; build ID |
| E022 | `tools/build_uk_national_dataset.py:1138` `uuid.uuid4` | `operational_nonce`; atomic JSON temp path |
| E023 | `tools/build_uk_rowwise_candidate.py:116` `uuid.uuid4` | `operational_nonce`; candidate build ID |
| E024 | `tools/build_uk_rowwise_dataset.py:206` `uuid.uuid4` | `operational_nonce`; rowwise build ID |
| E025 | `uk_runtime/hmrc_replay.py:816` `tempfile.NamedTemporaryFile` | `operational_nonce`; implicit random atomic temp name only |
| E026 | `tools/build_uk_rowwise_candidate.py:667` `tempfile.mkdtemp` | `operational_nonce`; implicit random staging-directory name only |

All nine are barred from numerical identity and node-reuse keys. Any raw
dual-mode receipt comparison must freeze them or apply the sealed operational
normalization vector; calling an entire manifest byte-identical while leaving
these live would be contradictory.

### Operational clocks and timing (12)

| ID | Callsite | Exemption and constraint |
| --- | --- | --- |
| E027 | `uk_runtime/geography_sources.py:1663` `time.sleep` | `operational_retry_timing`; no numerical identity |
| E028 | `tools/build_uk_national_dataset.py:529` `time.perf_counter` | `operational_duration` |
| E029 | `tools/build_uk_national_dataset.py:530` `datetime.now` | `manifest_timestamp` |
| E030 | `tools/build_uk_rowwise_candidate.py:266` `time.perf_counter` | `operational_duration` |
| E031 | `tools/build_uk_rowwise_candidate.py:267` `datetime.now` | `manifest_timestamp` |
| E032 | `tools/build_uk_rowwise_candidate.py:746` `datetime.now` | `manifest_timestamp` |
| E033 | `tools/build_uk_rowwise_dataset.py:298` `time.perf_counter` | `operational_duration` |
| E034 | `tools/build_uk_rowwise_dataset.py:299` `datetime.now` | `manifest_timestamp` |
| E035 | `tools/build_uk_rowwise_dataset.py:472` `datetime.now` | `manifest_timestamp` |
| E036 | `tools/build_uk_rowwise_dataset.py:792` `datetime.now` | `manifest_timestamp` |
| E037 | `tools/build_uk_rowwise_dataset.py:930` `datetime.now` | `manifest_timestamp` |
| E038 | `tools/build_uk_rowwise_dataset.py:1064` `datetime.now` | `manifest_timestamp` |

These calls must be brokered or normalized in operational receipts and must
not enter normative artifacts or reuse identities.

### Not harmless (1) and scanner false positive (1)

| ID | Callsite | Classification and required disposition |
| --- | --- | --- |
| E039 | `uk_runtime/weighted_integrity.py:474` `datetime.now(UTC).date()` | `policy_significant_clock`: the fallback changes exclusion expiry and therefore gate pass/fail. Inject/freeze the bundle evaluation date and receipt it; this is not an operational exemption at the flip. |
| E040 | `uk_runtime/cgt_imputation.py:272` `np.power` | `deterministic_math_false_positive`; Pareto quantile math, no ambient state |

## Declared-seed reconciliation

| Declared surface | Code behavior | Verdict / flip requirement |
| --- | --- | --- |
| `source_stages.json`: all FRS take-up/person/household/BRMA operations `seed: 0` | Module constants at `frs_take_up.py:47,172-175`, `frs_person_draws.py:30,87-90`, `frs_household_draws.py:30-32,85-88`, and BRMA use 0 | Values match today, but transforms do not consume or validate the manifest seeds. Compile one owner and fail on drift. |
| `take_up_contract.json`: several `seed: 42` values | These are historical `fitting_receipt` provenance, not runtime assignment seeds | Preserve as descriptive evidence; do not reconcile them to H001-H016. |
| `source_stages.json`: SPI support `seed: 42` | `spi_support` and canonical `spi_spine` use/validate 42 | Reconciled on canonical source-plan path. |
| `source_stages.json`: `strict_read_private_table: 42`, stage 1 `42`, stage 2 `43` | Strict read has no stochastic consumer. QRF runtime takes `seed` and derives stage 2 as `seed+1` | Default 42/43 reconciles. Canonical `spi_spine` validates it; the current national legacy adapter accepts arbitrary `--seed` and bypasses that validation. Bundle mode must reject a conflict or resolve from IR. |
| `source_stages.json`: WAS QRF `seed: 0` | Runtime uses 0, but resets three separate QRF chains | Value matches; ledger must preserve the three-reset boundary, not describe one continuous stream. |
| `cgt_source_stages.json`: CGT `seed_base: 552` | Runtime uses `(552, int(time_period))` | Reconciled; period mixing must be explicit seed material. |
| Geography spec default stream `0`; ladder function default 0 | Both rowwise drivers pass their CLI seed, default 42 | Two authorities exist. Bundle/run-request resolution must make 42 versus 0 explicit and bind R023/R024. |
| National sample code default 578 | Separate `--sample-seed`; full fraction consumes no RNG | Give R032 its own stream; never alias it to build seed 42. |
| Candidate seed default 42 | Feeds geography and calibration, each with a fresh generator/reset and different family | Bind separate R023/C033 site IDs even when the seed value is equal. |
| Firm config default 42 | Resets global Torch twice and global NumPy once | No declarative owner; bind R020-R022 if this dormant surface enters a compiled path. |

## Reachable shared-kernel defect outside the scoped file census

`packages/microcosm-fit/src/microcosm/fit/qrf.py:640` constructs a bare
`np.random.default_rng()` before restoring serialized state. WAS reaches this
helper for fit/draw restoration. The ambient entropy should not affect result
bytes because state is immediately replaced, but it violates the broker
contract. The US F1 repair replaces it with `Generator(PCG64(0))`; the UK lane
must inherit and verify that certified kernel repair before dual-mode evidence.
It is not included in either the 79-callsite count or the 80-candidate AST
census because the requested physical scope was UK runtime plus the three
drivers.

## Highest-risk findings

1. An arbitrary national `--seed` silently diverges from canonical SPI 42/43
   on the actual legacy-adapter path.
2. Eighteen seed-0 stable-hash streams and WAS duplicate declarations in code
   instead of consuming compiled seed bindings.
3. The shared QRF restore helper touches ambient entropy, and WAS has three
   identical-seed resets rather than one stream.
4. Firm generation uses global Torch/NumPy state and backend-sensitive draws.
5. UUID/temp-name nonces and clocks contaminate raw receipt bytes;
   weighted-integrity's fallback date can additionally change the release
   verdict.
