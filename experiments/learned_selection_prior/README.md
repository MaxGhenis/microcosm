# Learned selection-prior experiment (populace#346)

**Question.** Can a model trained on the frozen 57,240-record Build G selection
predict membership well enough to serve as an L0 *initialization* prior — and
what features actually predict selection? This tests Max's #346 correction:
initialize L0 selection probability by **target-contribution share**
`pᵢ ∝ f(maxₜ wᵢ·|vᵢₜ|/|targetₜ|)`, **not** dense-weight-proportional (which
starves the irreplaceable thin-tail carriers — rare records with large per-unit
value `vᵢₜ` but small calibrated weight `wᵢ`).

Init-only, n=1 lineage. The optimizer + gates still decide the final selection;
a prior only sets where the search starts.

## Data (all local — Build G campaign; nothing synthetic)

| piece | source | grain |
|---|---|---|
| **label** y ∈ {0,1} | `_buildg-runtime/forensics/frozen_support_mask.npy` (337,704 bool, Σ=57,240) — built by `forensics/join_check.py` joining base↔cert on the unique 4-key `(source_year, source_household_id, household_support_channel, household_support_clone_index)`, 0 missing, ordered by `household_id` | household |
| base pool (18833fb6) | `_worktrees/populace-build-f/out/base-f-20260705/base_populace_us_2024_puf_support.h5` (337,704 hh, 3-yr ASEC×2 PUF clone) | 337,704 |
| **dense weight** wᵢ (feat a) | Build G DENSE calibration — **recomputed** (see below); the #299 dense arm raised at the export gate before persisting it | 337,704 |
| **value matrix** vᵢₜ (feat b) | `_buildg-runtime/checkpoints/buildg-dense/target_frame_checkpoint.h5` — all 5,521 targets are `entity=household, filter=None, measure=column`, so A[t,i] = household column `measure.name`; b (|targetₜ|) from the dense `calibration_diagnostics.json` `targets[].target` | 5,521 × 337,704 |
| raw base weight (feat c) | base H5 household weight (`initial_weights` in the constraint problem) | 337,704 |
| demographics (feat d) | base H5 via `policyengine_us.data.USSingleYearDataset` (hh size, age structure, income, state) | 337,704 |
| support channel + source year (feat e) | base H5 person/household identity | 337,704 |

## Dense-weight recovery (STEP 01)

The #299 DENSE arm's calibrated `household_weight` was **never persisted**: the
release raised `RuntimeError` at the export-mass gate (4 unidentified PUF columns)
*before* writing the export H5. It is **deterministically recoverable**, not
synthetic: the expensive target materialization is cached in
`checkpoints/buildg-dense/target_frame_checkpoint.h5`, and every solver option is
recorded (adam, 1500 epochs, lr 0.02, mass=conserve, ratio 5.0, λ0=0, λ2=0,
seed 0). `scripts/01_recompute_dense_weights.sh` re-runs the exact dense command
with `--allow-input-mass-drift` (bypasses only the export gate; checkpoint
identity is independent of the flag → cache hit, no re-materialization), which
writes the export H5 with `household_weight`.

**Verification invariants** (must match to prove identical weights):
`final_loss=0.0413937`, `ESS=81206.15`, `top_1pct_weight_share=0.10600402`,
`realized_max_weight_ratio=5.0`, `initial_loss=0.2063060`.

## Leakage guard

Features are weights + contribution shares + leverage + demographics. **None is
derived from the label** (selection membership). The label comes only from the
manifest join. Contribution-share / leverage features are the *same quantities
the L0 optimizer implicitly used* — that is the hypothesis under test, not ML
leakage: we are asking whether the selection is explainable by
contribution/leverage structure. Excluded: the selection mask itself, any
selection rank, and the incumbent 57k refit weights.

## Layout

- `scripts/` — detached runners (nohup + pidfile; real exit codes; staging-only).
- `src/` — feature extraction + EDA + modeling + harness-scoring code.
- `out/`, `artifacts/` — gitignored; large blobs live under `_buildg-runtime`.

Artifact pointers (outside repo):
- recompute run: `_buildg-runtime/out/learned-prior/densewts/…` + log under `_buildg-runtime/logs/learned-prior/`.
