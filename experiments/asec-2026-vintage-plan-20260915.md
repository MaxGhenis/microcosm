# ASEC 2026 (income year 2025) vintage rollover — scoping, 2026-09-15

## The file (published today)

- `https://www2.census.gov/programs-surveys/cps/datasets/2026/march/asecpub26csv.zip` — 139,103,894 bytes, last-modified 2026-09-15 10:55 GMT, sha256 `fe819d0d2fc4470c282e76c247b8aa8b6054811619730307e9f2fe6186707d93`.
- Members: `pppub26.csv` 259,887,437 bytes, crc32 `477a9e19`, sha256 `f78920699bf671cc211cb720ff8c6274392524a22138aedaf9e3954f91ba4334`, 134,729 persons (PERIDNUM unique = rows); `hhpub26.csv` 88,026 households, 153 columns; `ffpub26.csv` 61,133 families; `asec_csv_repwgt_2026.csv`.
- Sample: 134,729 persons vs 142,125 (2025 file), 144,265 (2024), 146,133 (2023).
- Schema vs `pppub25.csv` (844 → 831 columns): removed `I_M5G1 I_M5G2 I_M5G3 M5GSAME M5G_CBST M5G_DIV M5G_DSCP M5G_MTR1 M5G_MTR3 M5G_MTR4 M5G_REG M5G_ST SPM_BBSUBVAL`; none added. Household: removed `HBBSUB_MNTH HBBSUB_YN HECC_PROBTIME HXCC_PROBTIME I_HBBSUBMNTH I_HBBSUBYN`, added `HTCC_PROBLOSS HXCC_PROBLOSS`. None of the removed columns is referenced anywhere under `packages/microcosm-build/src` or the US spec. All 71 `NOW_*` coverage recodes present (as in the 2025 file; issue #720's gap is the 2023/2024 files).

## Ready registry entry (`education_assistance_source.ASEC_EDUCATION_ASSISTANCE_ARCHIVES`, formulas per lines 461–479)

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

## What the rollover touches (from the tree at #893 head 4fc4ee6dd)

1. Public-file layer (code-owned pins): the registry entry above feeds `_MEMBER_PINS` in `asec_coverage_authentication`, `asec_student_controls`, `asec_original_household_weights`, `current_asec_demographics`, `native_household_origin`, `current_survey_housing`, `education_assistance_source`, `survey_population_preparation`, `source_enrichment` (microcosm-data). The income-year roster `{2022, 2023, 2024}` is hard-coded in 18 modules (`asec_current_money`, `asec_current_money_source`, `asec_person_income_source`, `asec_coverage_authentication`, `asec_original_household_weights`, …) and must become the new window everywhere.
2. Raw-stage layer: `asec_raw_stage` in the generated US spec (`us/spec/sources.yaml`, from `tools/generate_us_bundle_from_constants.py`) pins a 653 MB raw-stage checkpoint (sha 51e9fafc…) with vintages `asec_2023`/`asec_2024` and authorities 2022–2024. The new vintage needs the raw H5 input built from the CSVs (the gated inputs on Hugging Face) and the checkpoint re-pinned; every spec identity downstream (seed map, spec_sha256, bundle digests, loader golden, pool-tool pin) moves.
3. Downstream: pooled support spine and catalogue, ASEC-derived calibration targets, coverage recodes (#720), certification battery, national/CD calibration, a native pilot re-run (local compute needs Max's word), release manifest. This is an epic, not a PR.

## Decision needed (window)

The pooled design stacks three ASEC vintages by income year. Options: (a) roll the window to `{2023, 2024, 2025}` (drop 2022; keeps three vintages; removes one of the two files that lack the `NOW_*` recodes per #720; the smaller 2026 sample argues for keeping three); (b) widen to four `{2022, …, 2025}`. Recommendation: (a).

## Sequencing

After #893 merges (it modifies the same runtime modules). Layer 1 is a bounded build lane; layers 2–3 need the gated inputs and a data build.
