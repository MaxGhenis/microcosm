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

Augmented run (features_augment.npz = base + 7 dense-FINAL-weight cols): standalone
dense FINAL weight AUC 0.639766 / AP 0.280247 (vs base/initial weight 0.504532)
— solving concentrates weight by leverage, so the SOLVED weight ~ contribution
share; but at init time only the base weight (chance) is available. models --tag
augment: RUNNING.

## STEP 04 selections — DONE (positional, household_id-sorted order)
Tie-break: score desc, ties by ascending index (lexsort). Overlap w/ frozen:
| selection | overlap | % of K | lift vs random |
|---|---|---|---|
| learned_hgb (top-57,240 by OOF HGB) | 24,349 | 42.5% | 2.51x |
| learned_logit | 21,713 | 37.9% | 2.24x |
| contrib_share (max-share formula) | 15,575 | 27.2% | 1.61x |
| random expected | 9,702 | 16.9% | 1.00x |

## STEP 05 fourth arm — RUNNING (direct path, NOT a full release run)
src/direct_replay_learned_refit.py: DENSE checkpoint HIT → restrict to selection
→ base-population mass repair to 334.2M → recompile registry (5,521 targets, no
auto-drop) → calibrate (same dense config). Running learned_hgb then frozen
(matched control) serially via scripts/05b_direct_refits.sh. Results pending.
