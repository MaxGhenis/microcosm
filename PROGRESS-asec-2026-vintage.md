# ASEC 2026 vintage rollover — layer 1 (code-owned identities)

Lane journal. Branch `asec-2026-vintage-rollover`, cut from #893 head `4fc4ee6dd`.
Started 2026-09-15. Nothing pushed; no branch created; `uv.lock` untouched.
Per CLAUDE.md "Root journals are history, not state" — this file is accurate when
written, historical afterwards.

## Decision being implemented (Max, 2026-09-15)

The pooled ASEC window ROLLS to income years `{2023, 2024, 2025}` (survey files
`pppub24/25/26`). Income year 2022 (`pppub23`) leaves the roster.

## The invariant this lane established

The pooled roster and the **current-money anchor** are different things and only
the roster rolls here. The current anchor is income year 2024 / survey 2025
(`hhpub25.csv`, `CURRENT_INCOME_YEAR`, `catalogue_cohorts`, `population_cohorts`,
`key[0] == 2024`), and it is pinned to the ACS 2024 vintage, the PUF 2015→2024
money year and the C-CPI-U 2024 price target — none of which roll. Income 2024
is still inside the new window, so every `== 2024` selection keeps its meaning.
Moving the anchor needs an ACS 2025 and a new price target; that is not layer 1.

## Done

- Registry (`education_assistance_source`): survey-2026/income-2025 entry added,
  income-2022 dropped. Every pinned field independently recomputed from the local
  `asecpub26csv.zip`; the 2024 and 2025 archives recomputed as controls and
  reproduce their pins exactly (zip/member size, sha256, crc32, rows, ED_VAL
  positive rows, weighted share, weighted total).
- Roster rolled across 20 US runtime modules plus microcosm-data, deriving from
  the registry wherever the module already imports it.
- Measured per-vintage pins rolled: PAW_TYP audit registry (income-2025 measured),
  SPM unit counts, hhpub26 native member pin, source-enrichment census pins.
- US implementation inventory contract re-recorded for
  `asec_person_coverage_source` (its registry import landed in 6711f1b4 without
  the matching inventory entry).
- US spec constants rolled and the bundle regenerated:
  `spec_sha256 46e20546… → 3c614292…`; the `resolved_vintage_authorities`
  pointer claim re-pinned (63 pointers, `5f2edfe9… → f637644c…`).

- Price basis extended to the new window (Census P60-289, 2025 cell 178.7,
  target year unchanged at 2024); the two digest cascades re-pinned.
- Every invented-cohort fixture rolled, including the ASEC-2024 native
  population fixture where "the anchor cohort" and "the last cohort" came apart.
- **All 39 ASEC-facing test files pass: 2,002 tests, 0 failures, 0 errors**
  (one pytest process per file, as CI runs them).
- Report at `experiments/asec-2026-vintage-layer1-report-20260915.md`, with the
  layer-2 inventory and five decisions for Max.

## Next

Layer 2: rebuild the raw-stage checkpoint from the gated inputs and re-pin it;
then the `_SOURCE_PINS` cohort digests, the income-2025 frozen H5, the
source-enrichment re-run, and the ASEC-2026 dictionary evidence.

## Pre-existing, NOT caused by this lane

`tools/spec_engine_coverage.py --check` already fails at `4fc4ee6dd` with
`seed_protocol_and_owner_map_digests_exact` (seed protocol content digest and
compiled seed map digest). Measured at HEAD with this lane's spec changes
reverted: identical observed digests, identical failure. Not re-pinned here.
`ruff format --check` also already fails on `us_runtime/wic_claim.py` (from
`17ed9a0be`); CI only runs `ruff check`, which is green.

## Layer 2 (NOT this lane)

The `asec_raw_stage` checkpoint (sha `51e9fafc…`, 653 MB) is built from gated
Hugging Face inputs. No checkpoint is invented here; the regenerated spec still
pins the income-2022–2024 artifact against the new vintage authorities, which is
exactly the inconsistency layer 2 must resolve by rebuilding it.
