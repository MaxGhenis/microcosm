STATUS: CONTROLS_FAILED — C4 NOT_RUN_UNAVAILABLE_SPECIFICATION (FAIL_CLOSED); C0a/C0b PASS; C5 PASS_DIAGNOSTIC_OUT_OF_ORDER; C2/C3/readings/C1 NOT_RUN

# QRF drift validation Phase 0 — v2.2 permitted rerun

The instrument did not establish the complete control-family pass required by §3.6. C4 is not uniquely executable under A8/A10 and its registered zero-null premise is invalid for A1's one-at-a-time prior marginals. This is a specification/null-validity failure, not an observed numerical control failure. No second refreeze is authorized, so all interventions, readings, cross-fitting, verdicts, and arm flags are NOT_RUN. The machine-readable mirror is `experiments/qrf_drift_validation_phase0.json` (SHA-256 `e6c07946b6fb74e707076677e8f6a04d59e60fbffb7b4a8b251330317fdfa9a0`).

## Control results

### C0a — PASS

The permitted seedless reuse was accepted only after the baseline and candidate pool/gates digests, both candidate checkpoints, all nine banks, and all three A12 predecessors matched their recorded inputs. The four pool/gates rehashes are frozen in `/tmp/qrf_phase0_v22_c0a_reuse_verification.json` SHA-256 `60562a7524a91af4eb1f554acb26e71c208ae6892cc7a273b79b465251783569`; the 17/17 execution-design, D0, prior-E4, checkpoint, bank, and A12 bindings are in `/tmp/qrf_phase0_v22_c0b_input_verification.json` SHA-256 `a7376bd7557863c16b9b6f1dfee41d7f0c5b02c2be27ed899e9cafceb56d3e16`. The independent scope reconstruction matched 36 rung×target×leg comparisons and 72 origin cells digit-for-digit, with zero mismatches. Source for every C0a number below: `/tmp/qrf_phase0_c0a.json` SHA-256 `d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962`.

| Rung | Entity | Origin | Rows | Weight mass | Scope-mask SHA-256 |
| --- | --- | --- | --- | --- | --- |
| candidate-25 | person | asec | 108073 | 81353165.66410413 | `8837da9d8a719f6ea841087dc3a9ead4102422763ff1e04b8673fc9c50608460` |
| candidate-25 | person | acs | 856626 | 79837622.85984892 | `e47f43ef247be25dacaa2ede98f526189b9293b10597156b183814dcebe8d958` |
| candidate-25 | spm_unit | asec | 43961 | 35171435.38891061 | `ae7fd0183aaa7f9a111e3af98f0ab8e6b670470d6a34650c47355fd9fe01f262` |
| candidate-25 | spm_unit | acs | 382903 | 33672580.835061215 | `3cf4d3d77682c28c491484be1a1db2d25c114e8c396febd85e01383707757d0d` |
| baseline1pct | person | asec | 4311 | 80851529.27715749 | `bb51e694ad0b178cd1e1b7e7b4dbf820c15c6bed5c7176fc02ce5f5e7b19b1ec` |
| baseline1pct | person | acs | 34293 | 79926522.10879111 | `bb0aee24799d0f16803ce060dbcbb5823cc1f1fe9cfa9219e586d675d1a48d1d` |
| baseline1pct | spm_unit | asec | 1763 | 35317611.96790099 | `17504d515f864f3b8f8821a457c6cf1c7c3f1a78a88745095bb2aabaebf2b58b` |
| baseline1pct | spm_unit | acs | 15316 | 33672580.835061215 | `ffdfdbd6eee6edb6a5e9db5aa1ccd1402024e95ebe0c822a253ebdf03d60900f` |

The incidence cells are `nonzero rows / weighted incidence`; every value and exact result is sourced by the same C0a artifact and digest.

| Rung | Target | Leg | ASEC | ACS | Exact result |
| --- | --- | --- | --- | --- | --- |
| candidate-25 | child_support_expense | positive | 711 / 0.007268677325187965 | 9938 / 0.0072699659756268065 | PASS |
| candidate-25 | child_support_expense | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| candidate-25 | child_support_received | positive | 1189 / 0.009602187892523867 | 9829 / 0.009601925759774504 | PASS |
| candidate-25 | child_support_received | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| candidate-25 | weeks_unemployed | positive | 3387 / 0.033032275972772224 | 8419 / 0.010301355899161084 | PASS |
| candidate-25 | weeks_unemployed | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| candidate-25 | workers_compensation | positive | 296 / 0.002877717355202308 | 3832 / 0.0028778617265023385 | PASS |
| candidate-25 | workers_compensation | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| candidate-25 | spm_unit_energy_subsidy | positive | 1534 / 0.034001526827678395 | 16655 / 0.0340003890990147 | PASS |
| candidate-25 | spm_unit_energy_subsidy | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| candidate-25 | pre_subsidy_care_expenses | positive | 80 / 0.0007495439208078545 | 735 / 0.0007494944615207989 | PASS |
| candidate-25 | pre_subsidy_care_expenses | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| candidate-25 | self_employment_income_last_year | positive | 2608 / 0.025296566781282438 | 21389 / 0.02529601486800389 | PASS |
| candidate-25 | self_employment_income_last_year | negative | 48 / 0.0004377648581222527 | 2398 / 0.0029238974725717933 | PASS |
| candidate-25 | unemployment_compensation | positive | 1012 / 0.010478203338783127 | 8419 / 0.010301355899161084 | PASS |
| candidate-25 | unemployment_compensation | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| candidate-25 | disability_benefits | positive | 741 / 0.007627671678153712 | 5777 / 0.006115737093261155 | PASS |
| candidate-25 | disability_benefits | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| baseline1pct | child_support_expense | positive | 20 / 0.005237159573230564 | 23 / 0.0008970251113119809 | PASS |
| baseline1pct | child_support_expense | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| baseline1pct | child_support_received | positive | 47 / 0.009283063354192978 | 78 / 0.002254692834042267 | PASS |
| baseline1pct | child_support_received | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| baseline1pct | weeks_unemployed | positive | 134 / 0.03416953710300777 | 24 / 0.0008673738638929873 | PASS |
| baseline1pct | weeks_unemployed | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| baseline1pct | workers_compensation | positive | 12 / 0.0032646339104589438 | 4 / 0.0001554444182874518 | PASS |
| baseline1pct | workers_compensation | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| baseline1pct | spm_unit_energy_subsidy | positive | 63 / 0.03355398370682195 | 169 / 0.008068970861417737 | PASS |
| baseline1pct | spm_unit_energy_subsidy | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| baseline1pct | pre_subsidy_care_expenses | positive | 4 / 0.0007682074097856151 | 18 / 0.00043129087154899923 | PASS |
| baseline1pct | pre_subsidy_care_expenses | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| baseline1pct | self_employment_income_last_year | positive | 103 / 0.024919288036214633 | 1296 / 0.03430769129397444 | PASS |
| baseline1pct | self_employment_income_last_year | negative | 1 / 0.0003481158982156466 | 16 / 0.0004998781004272775 | PASS |
| baseline1pct | unemployment_compensation | positive | 34 / 0.00812938741011336 | 32 / 0.0010719375203290752 | PASS |
| baseline1pct | unemployment_compensation | negative | 0 / 0.0 | 0 / 0.0 | PASS |
| baseline1pct | disability_benefits | positive | 24 / 0.005420071428076496 | 20 / 0.0005337224535418865 | PASS |
| baseline1pct | disability_benefits | negative | 0 / 0.0 | 0 / 0.0 | PASS |

### C0b — PASS

E4 reproduced 36/36 pattern gates, 12,909,037 sign rows, and zero sign/state/index/weight/predictor mismatches. A9 then used 1,000 categorical PCG64 draws on every fit row per pattern with direct fit weights. All 76 repeated-draw cells and all 76 frozen recipient production checks passed; there were zero exact-variance cells. Maximum repeated-draw |z| was 3.2334829878814775 and maximum production |z| was 1.9263536173814484, both below z* = 3.673063850314496. Source for every number in this paragraph and table: `/tmp/qrf_phase0_v22_c0b.json` SHA-256 `1c7bfd65660b14068c4bc96fae4b8d270cb447ea8fbbe42c8ef982c5f1dbf542`; script SHA-256 `6a6b9e7ac7042d15726ac3ff895f10a613d49af5265e26a174f2151f66ad8058`; 17/17 input binding source `/tmp/qrf_phase0_v22_c0b_input_verification.json` SHA-256 `a7376bd7557863c16b9b6f1dfee41d7f0c5b02c2be27ed899e9cafceb56d3e16`.

| Target | Cells | Max absolute MC-mean z | Max absolute production z | Result |
| --- | --- | --- | --- | --- |
| child_support_expense | 8 | 2.152725579867969 | 1.689703931011236 | PASS |
| child_support_received | 8 | 2.116789254893659 | 1.2050899934049064 | PASS |
| weeks_unemployed | 8 | 0.5492557460809435 | 1.5991063122053075 | PASS |
| workers_compensation | 8 | 1.2719495689166678 | 1.9263536173814484 | PASS |
| spm_unit_energy_subsidy | 8 | 0.920087517092918 | 0.7897164727483575 | PASS |
| pre_subsidy_care_expenses | 8 | 0.6305272825037852 | 1.3159388132291368 | PASS |
| self_employment_income_last_year | 12 | 3.2334829878814775 | 1.0269917037565692 | PASS |
| unemployment_compensation | 8 | 1.4553487362057955 | 0.9353787283253425 | PASS |
| disability_benefits | 8 | 1.186755909165937 | 1.4076342353373241 | PASS |

A12's three later-chain predecessor bindings all matched. Every path, byte count, expected/actual digest, and match boolean is mirrored in the JSON. Source for the three full digests below: `/tmp/qrf_phase0_v22_c0b_input_verification.json` SHA-256 `a7376bd7557863c16b9b6f1dfee41d7f0c5b02c2be27ed899e9cafceb56d3e16`.

| A12 predecessor role | SHA-256 | Result |
| --- | --- | --- |
| adult_care_predecessor | `bb2d1b151c3593e280433285fb6fa1e27554391932e359a1d2c2eb80e56c80e0` | PASS |
| prior_year_income_predecessor | `724e123628ad0878cfbbe89dfde3c21f7ba5453cdaa091487aaf13feabfb0835` | PASS |
| model_required_numeric_predecessor | `0aa26da0fd2e6286081eba0616e488a14d0567eeae41b756d2ae5a6a8a84f908` | PASS |

### C4 — NOT_RUN_UNAVAILABLE_SPECIFICATION (FAIL_CLOSED)

A10 binds the intended donor self-substitution concept, the seed labels, z* = 3.673063850314496, 100 stochastic main-group statistics, 20 deterministic empty-G3 zeros, and A1 adds 36 stochastic per-prior statistics. Together with 76 C0b and 2 C2/C3 recovery statistics, the stochastic family has K = 214. It does not bind the target-level pattern×GQ integer allocation, within-stratum sampling/estimator, synthetic-recipient weights, GQ handling, RNG/stream mapping, or all adaptive-trigger details. Each choice changes finite estimates, MC SEs, escalation, and possibly pass/fail. Source for these counts and findings: `/tmp/qrf_phase0_v22_c4_spec_audit.json` SHA-256 `78f005d1655941a07c8ff933644b63f2e575ab54a2fcb8a6661874e14f91fdd6` and `/tmp/qrf_phase0_v22_c4_concept_audit.json` SHA-256 `98960e2ab9827176d0d18ce21cfa5364097c6607aa40389a8638a8e42e4186b5`.

There is also an internal null-validity failure. If X=Y~Bernoulli(1/2) and f(X,Y)=XY, the recipient mean is 1/2 while A1's independent one-at-a-time replacement gives 1/4, a marginal contribution of -1/4 rather than zero. Exact Shapley main-group terms can cancel by coalition/complement symmetry; A1's 36 marginal statistics do not. All counterexample numbers and the affected-statistic count are sourced by the independent concept audit and its digest above.

A full C4 control was not run and no C4 pass or numerical failure is claimed. Before the ambiguity was caught, one non-authoritative child_support_expense/pattern_00 benchmark used an unregistered per-pattern sample size of 478, escalated from 250 to 1,000 replicates after |z| = 2.0861666557573963, and consumed registered indices 0–999. Its three rows happened to pass, but they are not control results and were inspected; continuing after that exposure could make the missing choices outcome-conditioned. The first audit labels the convention incorrect; the independent audit more precisely establishes that it is plausible but unregistered, not uniquely disproven. Full disclosure source: `/tmp/qrf_phase0_v22_c4_spec_audit.json` SHA-256 `78f005d1655941a07c8ff933644b63f2e575ab54a2fcb8a6661874e14f91fdd6`; non-authoritative benchmark SHA-256 `ddf601427ba387deb54b719ab62aafc2725d0c98276371a3ea0463e4aaac6bc3`.

### C5 — PASS (non-authorizing diagnostic)

The A11 writer and independent production-path reader matched all 8/8 exact booleans. Source for every C5 number and digest below: `/tmp/qrf_phase0_v22_c5.json` SHA-256 `7f00827190276615806e26d5c76eda7c413c49640fb843988770f58056dc584c`; writer SHA-256 `0a40ef954c6155c275c2640f1dcb5cae072a8d25501dca256e51e9299da34f12`; reader SHA-256 `8492f0bf8f9b7709d8b02586220836239815bec04adabd185a4746ace537be8e`.

| Pattern | Check | Actual = expected | Result |
| --- | --- | --- | --- |
| pattern_0 | S_q_mask | count=20; mask=b56a90719afc245f1a0f52b0803b915086048e22a82004ad7d2d79ad1b2a581d | PASS |
| pattern_0 | S_o_mask | count=10; mask=9123d018c0ecc13a212a524072b2cc6db22cf2ad1208a91b2866a29423a2072e | PASS |
| pattern_0 | phi | 78/116 = 0.6724137931034483 | PASS |
| pattern_0 | path_census | qrf=20; native=5; outside=3; undecoded=2 | PASS |
| pattern_1 | S_q_mask | count=20; mask=6df7cab595076b1c502e78b680da8d77fbb445d11443b68751c858b628d2024a | PASS |
| pattern_1 | S_o_mask | count=10; mask=c20c7f70473e1ea730ec287462ad13b2dc6ce7cd59b8f9ec1422a05c86e205d3 | PASS |
| pattern_1 | phi | 77/118 = 0.652542372881356 | PASS |
| pattern_1 | path_census | qrf=20; native=5; outside=3; undecoded=2 | PASS |

### C2, C3, and C1

C2: NOT_RUN_CONTROLS_FAILED. C3: NOT_RUN_CONTROLS_FAILED. C1: NOT_RUN_CONTROLS_FAILED. Section 3.6 stopped execution before interventions, readings, and the post-reading gate cross-fit. Source: `experiments/qrf_drift_validation_design.md @ 51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.6 and A8.

## Per-target sections

Every placeholder in this section is a stopped computation, not a zero estimate or a no-defect verdict. Source for the stop: `experiments/qrf_drift_validation_design.md @ 51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.6.

### child_support_expense

Support: positive SUPPORTED; negative DEFERRED_ZERO_CARRIERS. Source: C0a SHA-256 `d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962` and execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.7.

Ledger table:

| Ledger rows | Value | SE | Status |
| --- | --- | --- | --- |
| L0, B1/P6, B2, T1, T2, T3, T4, T5, residual | null | null | NOT_RUN_CONTROLS_FAILED |

Attribution table:

| Attribution rows | Value | MC SE | Status |
| --- | --- | --- | --- |
| G1, G2, G3, per-prior, interaction, marginal audit | null | null | NOT_RUN_CONTROLS_FAILED |

Probes:

| Probe | Status |
| --- | --- |
| P0 | NOT_RUN_CONTROLS_FAILED |
| P1 | NOT_RUN_CONTROLS_FAILED |
| P2 | NOT_RUN_CONTROLS_FAILED |
| P5 | NOT_RUN_CONTROLS_FAILED |
| P6 | NOT_RUN_CONTROLS_FAILED |
| P7 | NOT_RUN_CONTROLS_FAILED |

Verdict:

| Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | --- | --- | --- | --- |
| positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |

### child_support_received

Support: positive SUPPORTED; negative DEFERRED_ZERO_CARRIERS. Source: C0a SHA-256 `d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962` and execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.7.

Ledger table:

| Ledger rows | Value | SE | Status |
| --- | --- | --- | --- |
| L0, B1/P6, B2, T1, T2, T3, T4, T5, residual | null | null | NOT_RUN_CONTROLS_FAILED |

Attribution table:

| Attribution rows | Value | MC SE | Status |
| --- | --- | --- | --- |
| G1, G2, G3, per-prior, interaction, marginal audit | null | null | NOT_RUN_CONTROLS_FAILED |

Probes:

| Probe | Status |
| --- | --- |
| P0 | NOT_RUN_CONTROLS_FAILED |
| P1 | NOT_RUN_CONTROLS_FAILED |
| P2 | NOT_RUN_CONTROLS_FAILED |
| P5 | NOT_RUN_CONTROLS_FAILED |
| P6 | NOT_RUN_CONTROLS_FAILED |
| P7 | NOT_RUN_CONTROLS_FAILED |

Verdict:

| Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | --- | --- | --- | --- |
| positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |

### weeks_unemployed

Support: positive SUPPORTED; negative DEFERRED_ZERO_CARRIERS. Source: C0a SHA-256 `d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962` and execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.7.

Ledger table:

| Ledger rows | Value | SE | Status |
| --- | --- | --- | --- |
| L0, B1/P6, B2, T1, T2, T3, T4, T5, residual | null | null | NOT_RUN_CONTROLS_FAILED |

Attribution table:

| Attribution rows | Value | MC SE | Status |
| --- | --- | --- | --- |
| G1, G2, G3, per-prior, interaction, marginal audit | null | null | NOT_RUN_CONTROLS_FAILED |

Probes:

| Probe | Status |
| --- | --- |
| P0 | NOT_RUN_CONTROLS_FAILED |
| P1 | NOT_RUN_CONTROLS_FAILED |
| P2 | NOT_RUN_CONTROLS_FAILED |
| P5 | NOT_RUN_CONTROLS_FAILED |
| P6 | NOT_RUN_CONTROLS_FAILED |
| P7 | NOT_RUN_CONTROLS_FAILED |

Verdict:

| Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | --- | --- | --- | --- |
| positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |

The requested T5 UC-clearing versus B1 producer-path versus T2 split was NOT_RUN_CONTROLS_FAILED.

### workers_compensation

Support: positive SUPPORTED; negative DEFERRED_ZERO_CARRIERS. Source: C0a SHA-256 `d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962` and execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.7.

Ledger table:

| Ledger rows | Value | SE | Status |
| --- | --- | --- | --- |
| L0, B1/P6, B2, T1, T2, T3, T4, T5, residual | null | null | NOT_RUN_CONTROLS_FAILED |

Attribution table:

| Attribution rows | Value | MC SE | Status |
| --- | --- | --- | --- |
| G1, G2, G3, per-prior, interaction, marginal audit | null | null | NOT_RUN_CONTROLS_FAILED |

Probes:

| Probe | Status |
| --- | --- |
| P0 | NOT_RUN_CONTROLS_FAILED |
| P1 | NOT_RUN_CONTROLS_FAILED |
| P2 | NOT_RUN_CONTROLS_FAILED |
| P5 | NOT_RUN_CONTROLS_FAILED |
| P6 | NOT_RUN_CONTROLS_FAILED |
| P7 | NOT_RUN_CONTROLS_FAILED |

Verdict:

| Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | --- | --- | --- | --- |
| positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |

### spm_unit_energy_subsidy

Support: positive SUPPORTED; negative DEFERRED_ZERO_CARRIERS. Source: C0a SHA-256 `d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962` and execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.7.

Ledger table:

| Ledger rows | Value | SE | Status |
| --- | --- | --- | --- |
| L0, B1/P6, B2, T1, T2, T3, T4, T5, residual | null | null | NOT_RUN_CONTROLS_FAILED |

Attribution table:

| Attribution rows | Value | MC SE | Status |
| --- | --- | --- | --- |
| G1, G2, G3, per-prior, interaction, marginal audit | null | null | NOT_RUN_CONTROLS_FAILED |

Probes:

| Probe | Status |
| --- | --- |
| P0 | NOT_RUN_CONTROLS_FAILED |
| P1 | NOT_RUN_CONTROLS_FAILED |
| P2 | NOT_RUN_CONTROLS_FAILED |
| P5 | NOT_RUN_CONTROLS_FAILED |
| P6 | NOT_RUN_CONTROLS_FAILED |
| P7 | NOT_RUN_CONTROLS_FAILED |

Verdict:

| Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | --- | --- | --- | --- |
| positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |

The baseline1pct cross-rung consistency reading was NOT_RUN_CONTROLS_FAILED.

### pre_subsidy_care_expenses

Support: positive SUPPORTED; negative DEFERRED_ZERO_CARRIERS. Source: C0a SHA-256 `d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962` and execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.7.

Ledger table:

| Ledger rows | Value | SE | Status |
| --- | --- | --- | --- |
| L0, B1/P6, B2, T1, T2, T3, T4, T5, residual | null | null | NOT_RUN_CONTROLS_FAILED |

Attribution table:

| Attribution rows | Value | MC SE | Status |
| --- | --- | --- | --- |
| G1, G2, G3, per-prior, interaction, marginal audit | null | null | NOT_RUN_CONTROLS_FAILED |

Probes:

| Probe | Status |
| --- | --- |
| P0 | NOT_RUN_CONTROLS_FAILED |
| P1 | NOT_RUN_CONTROLS_FAILED |
| P2 | NOT_RUN_CONTROLS_FAILED |
| P5 | NOT_RUN_CONTROLS_FAILED |
| P6 | NOT_RUN_CONTROLS_FAILED |
| P7 | NOT_RUN_CONTROLS_FAILED |

Verdict:

| Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | --- | --- | --- | --- |
| positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |

D0-4's 183 cleared draws remain a bound prior finding only; no Phase-0 T5 row was computed. Source: D0 JSON SHA-256 `fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8`, `/D0-4`.

### self_employment_income_last_year

Support: positive SUPPORTED; negative DEFERRED — 48 unique donor carriers are below the frozen floor of 50. Source: execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, A7 and §3.7.

Ledger table:

| Ledger rows | Value | SE | Status |
| --- | --- | --- | --- |
| L0, B1/P6, B2, T1, T2, T3, T4, T5, residual | null | null | NOT_RUN_CONTROLS_FAILED |

Attribution table:

| Attribution rows | Value | MC SE | Status |
| --- | --- | --- | --- |
| G1, G2, G3, per-prior, interaction, marginal audit | null | null | NOT_RUN_CONTROLS_FAILED |

Probes:

| Probe | Status |
| --- | --- |
| P0 | NOT_RUN_CONTROLS_FAILED |
| P1 | NOT_RUN_CONTROLS_FAILED |
| P2 | NOT_RUN_CONTROLS_FAILED |
| P5 | NOT_RUN_CONTROLS_FAILED |
| P6 | NOT_RUN_CONTROLS_FAILED |
| P7 | NOT_RUN_CONTROLS_FAILED |

Verdict:

| Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | --- | --- | --- | --- |
| positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |

The baseline1pct cross-rung consistency reading was NOT_RUN_CONTROLS_FAILED.

### unemployment_compensation

Support: positive SUPPORTED; negative DEFERRED_ZERO_CARRIERS. Source: C0a SHA-256 `d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962` and execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.7.

Ledger table:

| Ledger rows | Value | SE | Status |
| --- | --- | --- | --- |
| L0, B1/P6, B2, T1, T2, T3, T4, T5, residual | null | null | NOT_RUN_CONTROLS_FAILED |

Attribution table:

| Attribution rows | Value | MC SE | Status |
| --- | --- | --- | --- |
| G1, G2, G3, per-prior, interaction, marginal audit | null | null | NOT_RUN_CONTROLS_FAILED |

Probes:

| Probe | Status |
| --- | --- |
| P0 | NOT_RUN_CONTROLS_FAILED |
| P1 | NOT_RUN_CONTROLS_FAILED |
| P2 | NOT_RUN_CONTROLS_FAILED |
| P5 | NOT_RUN_CONTROLS_FAILED |
| P6 | NOT_RUN_CONTROLS_FAILED |
| P7 | NOT_RUN_CONTROLS_FAILED |

Verdict:

| Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | --- | --- | --- | --- |
| positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |

### disability_benefits

Support: positive SUPPORTED; negative DEFERRED_ZERO_CARRIERS. Source: C0a SHA-256 `d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962` and execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.7.

Ledger table:

| Ledger rows | Value | SE | Status |
| --- | --- | --- | --- |
| L0, B1/P6, B2, T1, T2, T3, T4, T5, residual | null | null | NOT_RUN_CONTROLS_FAILED |

Attribution table:

| Attribution rows | Value | MC SE | Status |
| --- | --- | --- | --- |
| G1, G2, G3, per-prior, interaction, marginal audit | null | null | NOT_RUN_CONTROLS_FAILED |

Probes:

| Probe | Status |
| --- | --- |
| P0 | NOT_RUN_CONTROLS_FAILED |
| P1 | NOT_RUN_CONTROLS_FAILED |
| P2 | NOT_RUN_CONTROLS_FAILED |
| P5 | NOT_RUN_CONTROLS_FAILED |
| P6 | NOT_RUN_CONTROLS_FAILED |
| P7 | NOT_RUN_CONTROLS_FAILED |

Verdict:

| Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | --- | --- | --- | --- |
| positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |

## P8 SSI dependency note

NOT_RUN_CONTROLS_FAILED. SSI remains excluded from the nine-target QRF roster; no tenth target, root-cause share, or control was created. Source: execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §§3.0 and 3.3.

## Cross-target summary

All 18 target×leg rows are stopped placeholders. Source: execution design at `51866036` SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`, §3.6.

| Target | Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | --- | --- | --- | --- | --- |
| child_support_expense | positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| child_support_expense | negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| child_support_received | positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| child_support_received | negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| weeks_unemployed | positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| weeks_unemployed | negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| workers_compensation | positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| workers_compensation | negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| spm_unit_energy_subsidy | positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| spm_unit_energy_subsidy | negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| pre_subsidy_care_expenses | positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| pre_subsidy_care_expenses | negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| self_employment_income_last_year | positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| self_employment_income_last_year | negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| unemployment_compensation | positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| unemployment_compensation | negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| disability_benefits | positive | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |
| disability_benefits | negative | null | null | null | NOT_EVALUATED_CONTROLS_FAILED | null | NOT_EVALUATED_CONTROLS_FAILED |

## Execution discrepancies

The rerun notice says A9–A12 now bind C4. The operative design's A8/A10 text still leaves the reported sampling and RNG choices open, and A10's zero-null claim conflicts with A1's 36 one-at-a-time marginals. The design is the declared authority, so this discrepancy was recorded and C4 stopped fail-closed. Sources: C4 implementation-audit SHA-256 `78f005d1655941a07c8ff933644b63f2e575ab54a2fcb8a6661874e14f91fdd6` and independent concept-audit SHA-256 `98960e2ab9827176d0d18ce21cfa5364097c6607aa40389a8638a8e42e4186b5`.

During final output review, HEAD advanced externally from the frozen execution design at `51866036` (SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`) to A13 commit `849d8270` (current tracked design SHA-256 `937939b2286176cdc3c85f26f2897e18651a6a7ce76d5bdf0698dcf18f553564`). The exact delta only advances the Mission-2 arm-B code pin and does not alter §3 or A1–A12, so no Phase-0 control or stop disposition changed. Both identities are preserved in the machine mirror.

The opening standing orders required a committed PROGRESS.md and a commit after every coherent step; the embedded HEADLESS block said to write only two files and never commit. The opening standing orders were followed. No push, logbook write, network access, or pool build occurred.

C5 was computed concurrently before C4's disposition, so it is reported as a valid exact diagnostic but did not authorize continuation. The prematurely run, non-authoritative C4 benchmark and its exposed seed indices are disclosed in the C4 section and machine mirror.

Heavy reads invoked `nice -n 10`, but the sandbox denied setpriority; C0b observed nice 0. C0b peak RSS was 3281.90625 MB versus the 24576 MB cap. Source: C0b SHA-256 `1c7bfd65660b14068c4bc96fae4b8d270cb447ea8fbbe42c8ef982c5f1dbf542`.

D0-0 records a pre-A8 design digest by chronology. Phase-0 controls executed against v2.2 SHA-256 `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292` at commit `51866036`; the current tracked file adds only A13 and is SHA-256 `937939b2286176cdc3c85f26f2897e18651a6a7ce76d5bdf0698dcf18f553564` at commit `849d8270`. Source: D0 JSON SHA-256 `fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8`, the execution-time git blob, and the current tracked design.

## Source catalog

| Source | SHA-256 |
| --- | --- |
| `experiments/qrf_drift_validation_design.md` | `937939b2286176cdc3c85f26f2897e18651a6a7ce76d5bdf0698dcf18f553564` |
| `experiments/qrf_drift_validation_d0.md` | `c4f3a9c56426025426e56428e9bce697a6cc6112f175be86ef9ef139bf79b601` |
| `experiments/qrf_drift_validation_d0.json` | `fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8` |
| `CLAUDE.md` | `f7ddff2d89f5b1931c5e91d5960c0e784d36d56c189cebab0e10aea39ca1e852` |
| `packages/microcosm-fit/src/microcosm/fit/qrf.py` | `5f47e06c8f0a261ad234625bc75219991be3081da5732730353d6bec3055ae3e` |
| `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py` | `c19168913dd37cb2297f6b63c8dda97d9c1aae165c26a142cb29203a5d299823` |
| `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer_bank.py` | `c153abc389dbfe944b633fc58d402eb47a5cd8bc4ac3acdc4b6eb57f046d3597` |
| `/tmp/qrf_phase0_c0a.json` | `d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962` |
| `/tmp/qrf_phase0_v22_c0a_reuse_verification.json` | `60562a7524a91af4eb1f554acb26e71c208ae6892cc7a273b79b465251783569` |
| `/tmp/qrf_phase0_c0b_replay.json` | `537cedfd35ee02bbcb74ea90814f274a21e6087c449b75294f798146442e66eb` |
| `/tmp/qrf_phase0_v22_c0b.json` | `1c7bfd65660b14068c4bc96fae4b8d270cb447ea8fbbe42c8ef982c5f1dbf542` |
| `/tmp/qrf_phase0_c0b_replay.py` | `6a6b9e7ac7042d15726ac3ff895f10a613d49af5265e26a174f2151f66ad8058` |
| `/tmp/qrf_phase0_v22_c0b_input_verification.json` | `a7376bd7557863c16b9b6f1dfee41d7f0c5b02c2be27ed899e9cafceb56d3e16` |
| `/tmp/qrf_phase0_v22_c4_spec_audit.json` | `78f005d1655941a07c8ff933644b63f2e575ab54a2fcb8a6661874e14f91fdd6` |
| `/tmp/qrf_phase0_v22_c4_concept_audit.json` | `98960e2ab9827176d0d18ce21cfa5364097c6607aa40389a8638a8e42e4186b5` |
| `/tmp/qrf_phase0_v22_c4_benchmark.json` | `ddf601427ba387deb54b719ab62aafc2725d0c98276371a3ea0463e4aaac6bc3` |
| `/tmp/qrf_phase0_v22_c5.json` | `7f00827190276615806e26d5c76eda7c413c49640fb843988770f58056dc584c` |
| `/tmp/qrf_phase0_v22_c5_writer.py` | `0a40ef954c6155c275c2640f1dcb5cae072a8d25501dca256e51e9299da34f12` |
| `/tmp/qrf_phase0_v22_c5_reader.py` | `8492f0bf8f9b7709d8b02586220836239815bec04adabd185a4746ace537be8e` |
| `experiments/qrf_drift_validation_design.md @ 51866036` | `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292` |
