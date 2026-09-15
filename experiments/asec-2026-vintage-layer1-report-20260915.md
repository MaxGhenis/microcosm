# ASEC 2026 vintage rollover — layer 1 report

Lane: `asec-2026-vintage-rollover`, cut from PR #893 head `4fc4ee6dd`, in
`~/PolicyEngine/_worktrees/microcosm-asec-2026-vintage`. **Nothing pushed, no
branch created, no PR opened, `uv.lock` untouched, the stash never used.**
Date 2026-09-15.

Decision implemented (Max, 2026-09-15): the pooled ASEC window rolls to income
years `{2023, 2024, 2025}` (survey files `pppub24/25/26`); income year 2022
(`pppub23`) leaves the roster.

---

## 1. The invariant this lane had to establish first

The plan's "roll the roster everywhere" runs into a distinction the old window
hid: **the pooled roster and the current-money anchor are different things, and
only the roster rolls here.**

Read from the code, not assumed:

- `current_asec_income_routing_source.CURRENT_INCOME_YEAR = 2024`, and a family
  of `p[0] == 2024` / `source_year == 2024` selections in
  `current_asec_interest_source`, `current_asec_dividend_source`,
  `current_asec_unemployment_source`, `current_social_security_source`,
  `current_survey_health_source`, `current_survey_housing`,
  `current_survey_person_status_source`, `puf55_survey_recipients`,
  `asec_2024_native_population` and `current_asec_demographics`.
- Those same functions assert, in the same breath, `acs_doc["source_year"] ==
  acs_doc["survey_year"] == 2024` (`current_survey_person_status_source:372`,
  `current_survey_health_source:257`), `acs_receipt["vintage"] == 2024`
  (`current_social_security_source:194`), `header["target_year"] == 2024`
  (everywhere money is read), `PUF59 output_money_year == 2024`
  (`puf59_canonical_artifact:40`) and `national_age_activation.acs_year == 2024`.
- `multispine_pool.POOL_TIME_PERIOD` is 2024 and the release line is
  `microcosm-us-2024`.

So the current anchor is pinned to the ACS 2024 vintage, the PUF money year and
the C-CPI-U 2024 price target — none of which roll in this lane. Income year
2024 is still inside the new window, so **every `== 2024` selection keeps its
meaning and is deliberately untouched**, including `hhpub25.csv` as the anchor
household member, `catalogue_cohorts: [2024]`, `population_cohorts: [2024]` and
the module name `asec_2024_native_population`. Moving the anchor needs an ACS
2025 and a new price target; that is layers 2-3, not this one.

Everything below follows that rule.

---

## 2. The registry entry as pinned

`education_assistance_source.ASEC_EDUCATION_ASSISTANCE_ARCHIVES` gained the
survey-2026 / income-2025 entry and dropped income-2022:

```python
        AsecEducationArchive(
            survey_year=2026,
            income_year=2025,
            zip_url=(
                "https://www2.census.gov/programs-surveys/cps/datasets/2026/"
                "march/asecpub26csv.zip"
            ),
            zip_size_bytes=139_103_894,
            zip_sha256=(
                "fe819d0d2fc4470c282e76c247b8aa8b6054811619730307e9f2fe6186707d93"
            ),
            member="pppub26.csv",
            member_size_bytes=259_887_437,
            member_crc32="477a9e19",
            member_sha256=(
                "f78920699bf671cc211cb720ff8c6274392524a22138aedaf9e3954f91ba4334"
            ),
            rows=134_729,
            positive_rows=2_574,
            weighted_positive_share=0.022465627092607597,
            weighted_total=84_013_616_601.91,
        ),
```

**Every field recomputed in this lane** from the local
`~/PolicyEngine/_buildm-runtime/inputs/asec_education/asecpub26csv.zip`, with
the module's own audit formulas transcribed independently (`ED_VAL > 0` rows,
`A_FNLWGT/100` weighted positive share, `dot(A_FNLWGT/100, ED_VAL)`). The two
surviving entries were recomputed the same way as controls and reproduce their
existing pins **exactly, field for field** (diff = `{}` for all three):

| income year | rows | ED_VAL>0 rows | weighted positive share | weighted total | vs pinned |
|---|---|---|---|---|---|
| 2023 (pppub24) | 144,265 | 2,971 | 0.022189613802856226 | 72,008,253,866.15 | exact match |
| 2024 (pppub25) | 142,125 | 2,948 | 0.023247141039884213 | 83,164,893,924.73 | exact match |
| 2025 (pppub26) | 134,729 | 2,574 | 0.022465627092607597 | 84,013,616,601.91 | new, measured |

Also verified on the same read: `PERIDNUM` unique in all three members, `ED_VAL`
finite and non-negative in all three.

### Other measured per-vintage pins rolled the same way

| pin | income 2023 | income 2024 | income 2025 | control |
|---|---|---|---|---|
| `spm_role_source` Census SPM units | 58,711 | 58,147 | **55,401** | 2023/2024 reconciled through `spm_role_source._load_source` and matched their pins |
| `public_assistance_type_source` PAW_TYP counts (codes 0..3) | (143_555, 398, 298, 14) | (141_415, 406, 289, 15) | **(134_163, 317, 223, 26)** | 2023/2024 matched their pins exactly |
| `public_assistance_type_source` PAW-positive rows | 710 | 710 | **566** | matched |
| `public_assistance_type_source` TANF-typed positive rows | 412 | 421 | **343** | matched |
| `native_household_origin` household member | hhpub24.csv | hhpub25.csv | **hhpub26.csv, 88,026 rows, 32,204,490 bytes, sha `e5e1ab43…`** | 2023/2024 pins re-measured and matched |
| `source_enrichment.CENSUS_PERSON_PINS` / `CENSUS_ARCHIVE_PINS` | survey 2024 | survey 2025 | **survey 2026** | `test_us_spm_role_source` registry-parity check is green |

`reported_coverage_source` needs no new pin, but its source availability was
checked: **all 71 `NOW_*` recodes, including the seven `#720` restores, are
present with codes `{1, 2}` in pppub24, pppub25 and pppub26**, so the sidecar
has a source for the whole new window.

Two prose statistics were re-measured rather than shifted. The PAW_TYP
conflation claim in `public_assistance_type_source` and `cps_carried` now reads
"in the 2024 ASEC (income year 2023), 266 of 655 PAW-positive SPM units — 40.6%
unweighted, 38.9% SPM-weighted — have no member reporting a TANF type". The same
SPM_ID/SPM_WEIGHT aggregation reproduced the retiring income-2022 sentence
(271 of 682, 39.7%, 42.6%) exactly as a control.

`source_enrichment.EXPECTED_COUNTS` rolled its two registry-derived sums —
`total_source_people` 432,523 → **421,119** and `total_source_units` 176,039 →
**172,259** — and left the four counts that are measured against the parent
population, with a comment saying only re-running the enrichment producer can
move them.

---

## 3. Roster edits, module by module

**Derived from the registry** (no literal left, so the next rollover moves
nothing here):

| module | what now derives |
|---|---|
| `asec_person_coverage_source` | `SOURCE_YEARS = ASEC_EDUCATION_ASSISTANCE_INCOME_YEARS` (landed in `6711f1b4`) |
| `asec_prepared_source` | `SOURCE_YEARS`, cohort/member filenames (landed in `6711f1b4`) |
| `asec_coverage_authentication` | member-path set, pin cohort tuple, pin cardinality and the capture loop, all via `literal.SOURCE_YEARS` |
| `asec_current_money_source` | `SOURCE_YEAR_MAPPING` set and the ED_VAL registered-pin loop and its count |
| `asec_person_income_source` | `MEMBER_PATHS` set; the incumbent-completeness check now follows `ASEC_EDUCATION_ASSISTANCE_INCOME_YEARS[-1]` instead of a literal 2024 |
| `asec_income_observations` | new public `SOURCE_YEARS`, and `_PRICE_YEARS = SOURCE_YEARS` |
| `graph_asec_income` | bound-coordinate check and cohort-count loop read `source.SOURCE_YEARS` |
| `tools/us_bundle_generation/core.py` | the `asec_raw_stage` vintage authorities are generated one-per-pooled-income-year from the registry |

**Rolled in place** (module has no registry import, or the literal is a receipt
value; `{2022, 2023, 2024}` → `{2023, 2024, 2025}`):

| module | sites |
|---|---|
| `asec_current_money` | cohort-pin tuple (`:289`), person/household scope sets (`:547-548`), decoded year vector (`:1062`), price-factor year tuple (`:477`), and the `AMOUNT_DOMAIN` slack factor `174.4/163.6` → `174.4/170.0` (the target-year index over the earliest pooled year's) |
| `asec_2024_native_population` | person-path year membership, path set, `parent_custody.cohorts` |
| `asec_population_catalogue` | `parent_custody.cohorts` |
| `asec_housing_status`, `asec_housing_universe` | `INCOME_YEAR` domains |
| `graph_native_household_origin` | `ASEC_SOURCES` names (`native_origin_asec_2023/24/25`) and the zip against them |
| `survey_population_domains` | cohort identity |
| `current_asec_demographics` | the three-cohort `pppub` path map |
| `asec_original_household_weights` | `MEMBER_REGISTRY` income-year membership |
| `current_survey_person_status_source` | student-pin roster |
| `survey_population_preparation` | `_SOURCE_ROSTER` (`pppub24/25/26.csv`), the per-member byte-limit loop, and the three-cohort `person_member_paths` |
| `puf_diagnostic_consumer` | `ASEC_HOST_COHORT` text-year membership |
| `spm_role_source` | SPM unit counts (landed in `0eb7eae7`) |
| `native_household_origin` | `_ASEC_MEMBER_PINS` (landed in `6711f1b4`) |
| `microcosm-data/source_enrichment` | census person/archive pins, the two derived totals |
| docstrings/comments | `asec_person_coverage_source`, `wic_claim`, `public_assistance_type_source`, `cps_carried`, `support_provenance` (#720 note now says which window it was observed on), `docs/us-native-spm-role-source-enrichment.md`, `docs/us-survey-person-status.md` |

**Deliberately NOT rolled** — the current-money anchor family listed in §1, the
ASEC data-dictionary PDF pins (see §6), `weeks_unemployed`'s survey-2023 LKWEEKS
sidecar (see §7 Q3), and every non-ASEC vintage the sweep turned up (SCF 2022,
the ACS 2022 rent donor, IRS SOI `ty2022`, congressional-district 2022, WIC
CY2022, SIPP 2023, PUF tax-2015).

---

## 4. Fixture edits

The invented-member mechanism is unchanged everywhere; only vintages and the
coordinates that follow from them moved.

- `test_us_asec_checkpoint` — the two-cohort invented checkpoint shifts to the
  first two pooled years; every audit key, source receipt, path and
  `source_year` with it. ACS provenance strings untouched.
- `test_us_asec_coverage_authentication` — uniform cohort shift (10 lines).
- `test_us_asec_demographic_source` — uniform shift including the
  intentionally-invalid year, which stays one below the window.
- `test_us_asec_current_money_source` — invented `source_year`, support-channel
  strings, per-cohort state codes, registry pin loops, sidecar survey years, and
  the restatement expectation `174.4/163.6` → `174.4/170.0`.
- `test_us_asec_person_income_source` — key offset `(year - 2022)` →
  `(year - 2023)`, the "last cohort" mutation target, the swapped-member pair,
  the invalid mapping key, and a new two-sided restatement assertion (the 2024
  cohort at nominal, the 2025 cohort scaled by `174.4/178.7`).
- `test_us_asec_household_coverage_fields` — cohort fixtures roll; the
  **survey-year dictionary position/page assertions are untouched** because the
  module still pins the survey-2023..2025 dictionaries.
- `test_us_asec_2024_native_population` — the one fixture where two readings of
  "2024" came apart. The extra household, its group row, its `PERIDNUM` keys and
  the member file it is written into now all follow the **anchor** cohort
  (income 2024, the invented `hhpub25.csv` that lists it) rather than the last
  rows of the person table, which are now income 2025. The member-file key
  offset is measured from the anchor cohort instead of assumed to be two, which
  restores the fixture invariant `PERIDNUM == person_id - 100`.
- Current-source tests (`income_routing`, `dividend`, `interest`,
  `child_support`, `retirement_detail`, `current_property_income_sources`,
  `child_property_income_source_owner`, `graph_us_survey_enrichment`,
  `survey_social_security`, `graph_atomic_completion_host`, the two predictor
  tests) — the current cohort's two people moved from person ids 105/106 to
  103/104, because the invented frame orders cohorts by income year. **This one
  was not cosmetic**: `test_us_current_property_income_sources` keys its only
  nonzero-weight property donor on person 105, so leaving it there emptied the
  QRF donor set to the single zero-weight extra household and
  `test_us_current_survey_property_graph` failed with "Probabilities contain
  NaN" out of `fit/qrf.py:_weighted_bootstrap`.
- `test_us_current_survey_puf_host` — the missing-money parametrisation's older
  cohort.
- `test_us_bundle_core_contracts` — the pinned `asec_raw_stage` source row and
  the full vintage-record id set.
- `test_us_asec_prepared_resources` — the income-observations resource digest
  (mirrors the price cascade below).
- `microcosm-data/tests/test_source_enrichment` — its survey-year
  parametrisation now reads the pin registry instead of repeating the window.

---

## 5. The price basis: the one runtime break the roll created

Rolling `asec_current_money`'s pooled-year tuple made every pooled read refuse
with `KeyError('2025')` at `asec_current_money.py:474`, because
`price_factors` compiles one C-CPI-U restatement factor per pooled income year
and the pinned basis carried cells for 2022-2024 only. This is a hard break, not
a stale comment, and it is code-owned rather than gated.

Resolved as a **pure extension, with the restatement target left at 2024**:

- `asec_current_money_price_basis_v1.json` now pins **Census P60-289**
  (`https://www2.census.gov/programs-surveys/demo/tables/p60/289/annual-index-value_annual-percent-change.xls`,
  sha256 `d97e18f47cf7943a13ca43cec2b7a7b7c7337294d3bb205e6c0452094c813dd7`,
  43,008 bytes), with cells `{2023: 170.0, 2024: 174.4, 2025: 178.7}`.
- The workbook was downloaded and read directly. **Control**: the previously
  pinned P60-286 workbook was downloaded in the same run and reproduced its
  pinned sha256 `8a5ef078b02c48c9e6414f3ca0cbdfe4a013ce6acf1a3fda42e6bd9c7da49e48`
  exactly, and P60-289 reprints 2022, 2023 and 2024 identically (163.6 / 170.0 /
  174.4). Every existing factor is therefore bit-identical.
- The 2025 cell carries the workbook's own footnote in a new `cell_notes` field:
  October 2025 has no published monthly C-CPI-U because of the 2025 lapse in
  appropriations, and BLS approximated it as the geometric mean of the September
  and November index values.

**Consequence worth seeing:** `174.4 / 178.7 ≈ 0.9759`, so for the first time
the newest pooled vintage is restated *down* into target dollars.
`test_us_asec_person_income_source` now asserts both halves explicitly.

Digest cascade, all re-pinned:

| identity | before | after |
|---|---|---|
| price-basis resource (`RESOURCE_PINS[1]`) | `88cec207…` | `12fb7ce3…` |
| `asec_income_observations_v1.json` (`RESOURCE_SHA256`) | `6e37855d…` | `a227b967…` |

The income-observations resource also rolled its `monetary_basis` keys to
2023-2025 (same 2024 valuation text). Its per-cohort **dictionary citations did
not roll** — see §6 — and it now carries a `cohorts_note` saying so in place, so
the stale block cannot be read as current.

---

## 6. Spec and inventory identity drift

| identity | before | after | why it moved |
|---|---|---|---|
| `spec_sha256` (generated US bundle) | `46e205463f593c4148c94b3ad7223e0d6b8d4117bedcb82da3bc2d82f7d5fc65` | `3c6142926fb8dbe82d240c8751e929d8b31cdec670190490fcbd54aedac99bba` | `sources.yaml` `asec_raw_stage` vintages/authorities and `vintages.yaml` records + compatibility cliques rolled |
| `field_usage` claim `resolved_vintage_authorities` | 63 / `5f2edfe9826e1200e2b8706780c9f53b7c61f01aad8cab5907f08c37a0b1ead2` | 63 / `f637644c345ba6ad77e6ab395827a723c857bee9bd47a1bd1fffa8dc308de2ef` | same pointer count, renamed `asec_20NN` paths |
| US implementation contract for `asec_person_coverage_source` | imports without `education_assistance_source` | with it | its registry import landed in `6711f1b4` without the matching inventory entry; recomputing every contract through `graph_implementation._dependency_contract` now reports zero drift |

`sources.yaml` still pins the **income-2022..2024** raw-stage checkpoint
(`51e9fafcd6f16140018fa90c7afbeb6d79008bfc8c122e437d23a399b30553fe`,
653,410,492 bytes) under the new vintage authorities. That inconsistency is
deliberate and is exactly what layer 2 closes; no checkpoint was invented.

### ASEC data-dictionary evidence — measured, not pinned

Five places pin the ASEC public-use dictionary PDFs by **survey** year
2023/2024/2025 with per-field page numbers:
`asec_person_coverage_source.coverage_field_contract`,
`asec_demographic_source.ASEC_DICTIONARY_AUTHORITY` +
`pdf_page_1based_by_survey_year`, `asec_original_household_weights._DICTIONARIES`,
`asec_household_coverage_fields._field`, and the two packaged JSON resources
(`asec_current_money_domains_v1.json`, `asec_income_observations_v1.json`) whose
per-cohort entries carry `pdf_page` and `excerpt_sha256`.

Measured in this lane so the follow-up is cheap:

- `asec2025_ddl_pub_full.pdf` downloaded and reproduced its pinned sha256
  `5cb80973326ef8b625fbaae70d80b0c641ce5d2b3911abd2fb4427abd5908a6f` — control.
- `asec2026_ddl_pub_full.pdf` exists and is complete: **659,697 bytes, sha256
  `074b68df209b748dafabc887485180eb0b91d3d7e25a3514626f0b15060e73eb`, 107
  pages** (the 2025 file is 94 pages).
- The 2026 dictionary **reorders record types** (Household first; the 2025 file
  leads with Family), so page offsets must be re-derived, not shifted. The
  `page if year < 2025 else page + 7` rule in
  `asec_household_coverage_fields._field` is dead for 2026.

**Not pinned here, on purpose.** A text-extraction sweep of the 2026 file gives
candidate definition pages (PRPERTYP 27, HSUP_WGT 2, H_SEQ 2, H_HHTYPE 3,
HRHTYPE 4, H_LIVQRT 3, H_NUMPER 5, PAW_YN/PAW_TYP/ED_VAL 58, PAW_VAL 61,
A_FNLWGT 26, SPM_ID 62, SPM_HEAD 59, LKWEEKS 45), but **the same method does not
reproduce the 2025 pinned pages** — the two files' column layouts differ — so
the method is uncontrolled and these numbers are candidates for review, not
evidence. The `excerpt_sha256` values cannot be reproduced at all without the
reviewed excerpting method.

---

## 7. What layer 2 has to build

| artifact | producing tool | consuming code / tests |
|---|---|---|
| **The income-2023..2025 raw-stage checkpoint** (replacing sha `51e9fafc…`, 653 MB), built from the gated Hugging Face inputs | the ASEC raw-stage build, then `tools/generate_us_bundle_from_constants.py` to re-pin | `us/spec/sources.yaml` `asec_raw_stage`; `test_us_bundle_core_contracts`; every certification/build lane |
| **`asec_current_money_source._SOURCE_PINS`** — the reviewed parent checkpoint digest, the household-observation receipt digest, and the three per-cohort digests (currently `(2022, 7ccca976…), (2023, cb578173…), (2024, ec36604c…)`) | the same rebuild | `asec_current_money_source._load` / `_validate_attachment` |
| **The income-2025 `census_cps` frozen H5** (person/household tables) | the ASEC input build | `weeks_unemployed`, `reported_coverage_source`, and `test_us_relationship_inputs::test_locked_artifacts_confirm_source_presence_and_absence`, which passes today against the locked income-2022..2024 H5s named in `experiments/build_j_recert/base_j.summary.json` and will need a new expectation set (its `expected_heads` are per-vintage `P_SEQ == 1` counts) |
| **A re-run native-SPM-role source enrichment** | `tools/build_us_spm_role_enrichment.py` | `source_enrichment.EXPECTED_COUNTS` — `persons_joined` 166,321, `native_spm_units` 59,900, `minor_only_units_resolved` 28, `classification_changed_units_vs_age_only` 132 all still describe the old pool |
| **ASEC-2026 dictionary evidence** (page numbers + excerpt digests) | manual review of `asec2026_ddl_pub_full.pdf` (identity measured above) | the five pin sites in §6, and the `cohorts` blocks of `asec_current_money_domains_v1.json` and `asec_income_observations_v1.json` |
| **`ecps_parity_known_gaps.json` and `release_input_coverage_manifest.json`** — packaged evidence keyed to the old pooled H5 filenames | `tools/build_us_release_input_coverage_manifest.py`, `tools/build_us_target_parity_manifest.py` | release gates; not touched here because their content is measured against the gated inputs |

Also downstream and out of scope here: the pooled support spine and catalogue,
ASEC-derived calibration targets, the #720 coverage recodes across the new
window, the certification battery, national/CD calibration, a native pilot
re-run, and the release manifest.

---

## 8. Verification — every command and its exit code

Run from the worktree with `UV_OFFLINE=1 uv run --no-sync`.

| command | exit | result |
|---|---|---|
| `python tools/ci_test_groups.py --verify` | **0** | `verification=ok`, no `[defaulted]` files |
| `python3 -I -B -S packages/microcosm-build/tests/test_ci_test_groups.py` | **0** | 15 tests OK |
| `ruff check .` | **0** | All checks passed |
| `ruff format --check <54 changed .py>` | **1** | 51 formatted; the 3 that fail already fail at `4fc4ee6dd` (see below) |
| `python tools/generate_us_bundle_from_constants.py --check` | **0** | `spec_sha256=3c614292…`, no stale files |
| us_runtime import sweep (269 modules) | **0** | 0 failures |
| US implementation contract recompute (all contracts) | **0** | 0 drifted, classifications closed |
| `python tools/spec_engine_coverage.py --check` | **1** | **pre-existing**, see below |
| ASEC-facing battery, per-file processes | see §9 | |

### `tools/spec_engine_coverage.py --check` is red **before** this lane

It fails on `seed_protocol_and_owner_map_digests_exact` — "seed protocol content
digest differs", "compiled seed map digest differs". Measured at this branch's
HEAD with this lane's four spec-side files reverted to their committed state:
**identical observed digests, identical failure**
(`seed_protocol` observed `358f218e…` vs expected `5f93b3ec…`; `seed_map`
observed `327ce987…` vs expected `da07a54a…`). The seed protocol's
`implementation_sha256` is computed only from the bundle's seed-protocol
declaration, and neither `bundle.yaml` nor any `spec_engine` module has changed
since `4fc4ee6dd`. **Not re-pinned here** — adopting someone else's unfinished
identity move is exactly the wrong thing to do silently. It needs whoever moved
the attested module to re-record it.

The only coverage drift this lane caused was
`resolved_vintage_authorities`, which is re-pinned (§6).

Second pre-existing item: `ruff format --check` fails on three files that
already fail it at `4fc4ee6dd` — `us_runtime/wic_claim.py`,
`tests/test_us_bundle_core_contracts.py` and `tools/us_bundle_generation/core.py`
(verified by checking out each file at the base and re-running the check). Every
reported reformat hunk is in a region this lane did not touch. CI runs
`ruff check .` only, which is green, so nothing is gated on it; not fixed here
because reformatting untouched regions would bury the rollover diff.

---

## 9. Test results

Baseline at this lane's start (after the first four commits, which had rolled
the registry but nothing else): **456 failed/errored** across the ASEC-facing
battery, and the same 456 ids after the first tranche of source edits — the
registry roll had invalidated every invented-cohort fixture.

**Final: all 39 ASEC-facing test files pass — 2,002 tests, 0 failures, 0
errors.** Files: `test_us_asec_*` (12), `test_us_current_asec_*` (8),
`test_us_current_survey_*` (17), `test_us_education_*` (2),
`test_us_graph_atomic_person_status.py`, `test_us_graph_puf55_survey_recipients.py`.

The battery was run **one file per pytest process**, the way CI runs it. Mixing
these files in a single process trips `IMPLEMENTATION_SOURCE_CHANGED` (modules
that read their own source bytes) and module-scoped fixture reuse; that is a
harness artifact of an ad-hoc combined run, not a rollover signal —
`test_us_current_survey_household_roles_graph` passes alone and fails in a mixed
run both before and after this lane.

---

## 10. Questions for Max

**Q1 — the price target year.** This lane kept the C-CPI-U restatement target at
2024 and extended the basis with the 2025 cell, because the dataset target
period, the ACS vintage, the PUF money year and the release line are all 2024;
the newest pooled vintage is therefore deflated into 2024 dollars for the first
time.
*(a)* Keep target 2024 (what is implemented). *(b)* Move the target to 2025,
which renames `RECIPE`/`PAW_VAL_2024_price`/`census_ccpiu_annual_2024`, changes
every money value and every downstream digest, and only makes sense together
with a move of the whole target period to 2025.

**Q2 — the 2025 index's approximated month.** The pinned 2025 annual C-CPI-U
(178.7) includes a BLS-approximated October 2025 value (geometric mean of
September and November) because of the appropriations lapse.
*(a)* Accept it, as implemented, with the provenance recorded in the resource.
*(b)* Hold the pooled window at two vintages, or hold the rollover, until BLS
publishes a revised October.

**Q3 — the weeks-unemployed sidecar.** `weeks_unemployed`'s LKWEEKS repair is
specific to income year 2022 (`ASEC_2023_WEEKS_UNEMPLOYED_SOURCE_YEAR = 2022`,
`asecpub23csv.zip` / `pppub23.csv`). With 2022 out of the pool, `has_2022` is
permanently `False` and the whole repair path, its CLI flag
`--asec-2023-weeks-unemployed-source`, and its `source_stages.json` stage
declaration are inert. Its spec authority `asec_2022` was dropped from the
generated bundle by this lane's registry-derived authorities.
*(a)* Leave it inert (what is implemented) and retire it in a follow-up.
*(b)* Retire it now — delete the repair, the flag, the stage declaration and the
`asecpub23` pin — which is a larger, separate diff.

**Q4 — the third pooled vintage in the spec clique.** `sources.yaml` declares
`asec_raw_stage` with two vintages (`asec_2025`, `asec_2024` after the roll) and
three authorities, and the reviewed compatibility clique pairs only those two.
Before the roll the odd one out was `asec_2022`, whose authority value came from
the weeks-unemployed repair year. With 2022 gone, that asymmetry no longer has a
reason.
*(a)* Keep the structure-preserving shift (what is implemented): two vintages,
`asec_2023` compatible only with `target_2024`. *(b)* Declare all three pooled
vintages on the source and put all three in one clique — a reviewed-relation
change that should land with the layer-2 checkpoint re-pin.

**Q5 — the dictionary evidence.** §6 shows the ASEC-2026 dictionary exists and
is identified, but the page/excerpt facts cannot be derived by a controlled
method. *(a)* Treat it as a layer-2 review item (what is implemented: the five
pin sites still describe survey 2023-2025). *(b)* Commission a reviewed
extraction now, so the dictionary pins roll with the rest of layer 1.
