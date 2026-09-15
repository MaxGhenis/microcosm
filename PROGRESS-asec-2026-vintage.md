# ASEC 2026 vintage rollover — layer 1 (code-owned identities)

Lane journal. Branch `asec-2026-vintage-rollover`, cut from #893 head `4fc4ee6dd`.
Started 2026-09-15. Nothing pushed; no branch created; `uv.lock` untouched.
Per CLAUDE.md "Root journals are history, not state" — this file is accurate when
written, historical afterwards.

## Decision being implemented (Max, 2026-09-15)

The pooled ASEC window ROLLS to income years `{2023, 2024, 2025}` (survey files
`pppub24/25/26`). Income year 2022 (`pppub23`) leaves the roster.

## State

- Environment synced (`uv sync --all-packages --locked --extra us --extra uk`, exit 0).
- Survey-2026 registry pins recomputed from the local archive with the module's own
  audit formulas; the survey-2025 archive recomputed as a control and reproduces
  every pinned field exactly.

## Done

- (nothing code-side yet)

## Next

1. Registry entry: add survey-2026/income-2025, drop income-2022.
2. Roll the hard-coded roster across the US runtime modules.
3. Roll the invented-fixture vintages in the ASEC-facing tests.
4. US spec constants + regeneration; report identity drift.
5. Verification battery.

## Layer 2 (NOT this lane)

The `asec_raw_stage` checkpoint (sha `51e9fafc…`, 653 MB) is built from gated
Hugging Face inputs. No checkpoint is invented here.
