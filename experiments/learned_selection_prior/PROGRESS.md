# Learned selection-prior — PROGRESS (populace#346)

Resume log for the learned-selection-prior experiment. Artifacts live under
`_buildg-runtime/out/learned-prior/` (gitignored); logs under
`_buildg-runtime/logs/learned-prior/`. All numbers verbatim from those.

## Build G invariants (shared by every arm here)
base pool 18833fb6 (337,704 hh), pe-us 1.764.6, feed consumer_facts_buildf_v7,
seed 0, λ=0, mass=conserve, max_weight_ratio 5.0, adam 1500ep lr 0.02. Registry
e035007bba5b (5,521 targets). ONE-SEED experiments, staging-only, NOT certified
releases.

## Recorded Build G arms (from release calibration_diagnostics.json)
| arm | n_records | final_loss | within10 | income_tax vs SOI | SS vs SSA |
|---|---|---|---|---|---|
| DENSE (full pool) | 337,704 | 0.041393692879 | 0.8616192719 | +1.23% | +0.05% |
| FROZEN-SPARSE | 57,240 | 0.029643378840 | 0.8914940022 | +0.50% | -0.13% |
| COLD-L0-2026 | (L0) | 0.104231171803 | 0.5539803708 | +17.83% | +6.20% |

income_tax target = irs_soi.ty2022.historic_table_2.us.all.income_tax_liability_amount@2024
SS target = ssa_supplement.cy2024.oasdi_ssi_payments.social_security_benefits.payment_amount@2024
pct = (final_estimate − target)/target. NOTE: FROZEN-SPARSE loss is over the
sparse registry (explicit zero-support exclusions); not directly loss-comparable
to a full-5,521-registry restricted solve — hence the frozen-on-dense control.

## STEP 01 (dense weight recovery) — DONE (verified before this resume)
densewts_direct/dense_household_weight.npy: final_loss 0.0413936929 (matches
recorded dense to 1e-5), ESS 81206.15, n_nonzero 337,704.

## STEP 02/03 model suite — DONE
Baseline OOF (5-fold, seed 0) reproduced exactly (models_base_run2.log):
| prior | roc_auc | pr_auc | precision@57240 |
|---|---|---|---|
| HGB (OOF) | 0.779541 | 0.416292 | 0.425384 |
| Logistic (OOF) | 0.730153 | 0.354553 | 0.379333 |
| Formula: max contribution share | 0.646868 | 0.245671 | 0.272100 |
| Prior: dense weight (base/initial) | 0.504532 | 0.170923 | 0.170510 |

Permutation importance top-5 (HGB, drop in ROC-AUC): sum_carrier 0.058908,
state_fips 0.022851, channel_puf 0.018430, n_targets_touched 0.016101,
sum_share_est 0.014518. (weight_used / log_weight_used absent from top-20.)

Calibration (reliability_base.json): HGB Brier 0.11955, well-calibrated across
bins; logistic Brier 0.12708, overconfident at the top.

Augmented run (features_augment.npz = base + 7 dense-FINAL-weight cols) — DONE:
| model | roc_auc | pr_auc | precision@57240 |
|---|---|---|---|
| HGB augment (base+dense) | 0.797165 | 0.446761 | 0.451555 |
| Logistic augment | 0.765699 | 0.395509 | 0.417226 |
Base HGB 0.779541 → augment 0.797165 (+0.0176). Standalone dense FINAL weight
AUC 0.639766 / AP 0.280247 (vs base/initial weight 0.504532 = chance). The
SOLVED weight ~ contribution share because solving concentrates weight by
leverage — but it is a POST-solve quantity, unavailable at init; at init only the
base weight (chance) exists. Augment top permutation importance: dense_x_sum_carrier
0.114248, channel_puf 0.018907, state_fips 0.016566, n_targets_touched 0.016164,
sum_carrier 0.011628 (the marginal gain flows through the leverage interaction,
not weight level). Augment HGB Brier 0.11615.

## STEP 04 selections — DONE (positional, household_id-sorted order)
Tie-break: score desc, ties by ascending index (lexsort). Overlap w/ frozen:
| selection | overlap | % of K | lift vs random |
|---|---|---|---|
| learned_hgb (top-57,240 by OOF HGB) | 24,349 | 42.5% | 2.51x |
| learned_logit | 21,713 | 37.9% | 2.24x |
| contrib_share (max-share formula) | 15,575 | 27.2% | 1.61x |
| random expected | 9,702 | 16.9% | 1.00x |

## STEP 05 fourth arm — DONE (direct path, NOT a full release run)
src/direct_replay_learned_refit.py: DENSE checkpoint HIT → restrict → mass repair
334.2M → recompile registry (5,521 targets, no auto-drop) → calibrate (dense
config). Both solves ~5 min each (57,240 records), serial via 05b_direct_refits.sh.

| arm | final_loss | within-10% (5521) | income tax vs SOI | SS vs SSA | ESS |
|---|---|---|---|---|---|
| DENSE full pool (recorded) | 0.041393692879 | 0.8616 | +1.23% | +0.05% | 81,206 |
| FROZEN-sparse (recorded, sparse reg) | 0.029643378840 | 0.8915 | +0.50% | -0.13% | — |
| **FROZEN-on-dense (my control)** | **0.029589177138** | 0.8890 | +0.67% | -0.02% | 13,637 |
| **LEARNED-HGB top-K (fourth arm)** | **0.329972962409** | 0.2343 | **+60.88%** | +0.20% | 26,300 |
| COLD-L0-2026 (recorded) | 0.104231171803 | 0.5540 | +17.83% | +6.20% | — |

FROZEN-on-dense (0.02959) reproduces recorded FROZEN-sparse (0.02964) to 4 sig
figs on the FULL 5,521-target registry → methodology validated; learned's blow-up
is real, not an artifact. Learned top-K is WORSE than cold L0.

Mechanism (mechanism_diag.json, pre-solve mass-repaired): learned_hgb income tax
+89.5% (25 uncovered targets) → solver stuck at +60.88%; frozen +44.8% (42
uncovered) → recovers to +0.67%. Frozen leaves MORE targets uncovered yet
calibrates far better → it is JOINT balance, not coverage count: ranking by
marginal selectability over-concentrates income-tax-heavy records; ratio-5.0 +
mass=conserve cannot rebalance. Selection is combinatorial, not rankable.

## Writeup posted
populace#346 comment: https://github.com/PolicyEngine/populace/issues/346#issuecomment-4905374475
(gh --body-file, no @-mentions). Every number verbatim from artifacts + release
calibration_diagnostics.json.

## Verdict
1. Per-record signal (CONFIRMS #346 catch): weight/dense-weight init = chance
   (0.505); contribution-share 0.647; leverage (sum_carrier) = top learned
   feature; learned model 0.780. Init by contribution-share/leverage, NOT weight.
2. Hard top-K by the learned prior does NOT reproduce the frozen edge (0.330 vs
   0.0296) — the prior is an L0 INITIALIZATION, not a selector; the optimizer's
   combinatorial balancing is irreplaceable. (informed_init mode not yet wired,
   so this bounds "prior as replacement," not "prior as warm-start".)
