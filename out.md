SWEEP-COMPLETE

# Stacked dense-release gate sweep final report

Date: 2026-08-29

Branch: `stacked-dense-gate-sweep`

Lane base: `7d44c0b5`

## Outcome

The candidate-25 farm-rent failure was a writer defect. The post-PUF generic
late-transfer producer used clone-positive PUF-detail rows as donors, then
predicted `farm_rent_income` into every null clone-0 recipient. On a stacked
ASEC+ACS frame, clone 0 is the native operator role for both physical spines;
farm rent is PUF-only and must instead be structural zero there.

The source contract is unambiguous: ASEC `FRSE_VAL` supplies measured
`farm_operations_income`, while PUF `E27200` supplies `farm_rent_income`.
`source_stages.json` explicitly preserves measured ASEC operations income and
replaces only the PUF support channel.

The same ownership defect affected six other PUF-only leaves guarded by strict
source-zero release gates. The fix moves all seven leaves to whole-pool primary
ownership: the primary PUF stage preserves the clone-positive payload, writes
exact zero to native rows, receipts both facts, and excludes the leaves from
generic late prediction. No gate, band, threshold, or contamination assertion
was weakened; there is no stacked-frame skip or special-case gate bypass.

The complete release-call roster is now executable-ledgered: 62 distinct
gate-like boundaries / 68 invocations, comprising 38 support/source-sensitive
boundaries and 24 explicitly reviewed out-of-class boundaries. Every valid
candidate-25 raw-pool replay was performed; post-selection and post-producer
checks are marked N/A where the raw pool is not a valid stage observation.

No evidence artifact was modified or rebuilt. No release or pool build,
launchd edit, publication, push, or PR was performed.

## Immutable evidence and authentication

Evidence was read only from:

- `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/candidate-25/pool/pool.h5`
- `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/candidate-25/pool/pool.manifest.json`
- `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/candidate-25/pool/pool.gates.json`
- `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/candidate-25/release-dense/release.log`
- `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/candidate-25/run-candidate.log`

The pool manifest SHA-256 is
`c9ee554939790d854efea9d69897a40376d0c7ea49e40e3f76f268835ebd148a`;
the H5 SHA-256 is
`eeea886afec72c4ec6e15d31358920416ea6892ef2dca6bb9a281dc1faf6231b`.
Both matched their sibling receipts byte for byte. The run ID is
`ce95a75a46e74b6b841e407bfa8261e9`. The terminal pool is the expected carried
`gate_failed` pool (78/135 battery), which predates this lane and was not
changed.

The current loader correctly refuses to authenticate this older pool because
its frozen, source-attested primary-QRF worker binding differs from current
source. After recording that expected refusal, the audit used fixed HDF tables
read only and reconstructed inherited household importance weights. It did not
rewrite, migrate, or rebuild the evidence.

## Farm-rent root-cause receipts

### Measured contamination

On the native/operator role (`support_role_series == "asec"`, equivalently
clone index 0 on this assembled frame), `farm_rent_income != 0` on 5,314 of
964,699 people:

- unweighted share: `0.0055084539` = 0.550845%;
- weighted numerator / denominator:
  `893122.0409190694 / 161190788.52395308`;
- weighted share: `0.005540775928311504` = 0.554078%;
- signs: 3,125 positive and 2,189 negative;
- weighted signed total: `5573148282.564434`;
- weighted absolute total: `14861079373.331043`.

The physical-source split proves that both stacked native spines were written:

| Physical `person_support_channel` | Nonzero / native rows | Nonzero weight / native weight | Weighted share |
|---|---:|---:|---:|
| `asec` | 647 / 108,073 | 501191.0979286348 / 81353165.66410413 | 0.616068% |
| `acs` | 4,667 / 856,626 | 391930.9429904348 / 79837622.85984892 | 0.490910% |

Every flagged row has `person_support_clone_index == 0`. The audited lineage
columns—`person_support_channel`, `person_support_clone_index`,
`person_source_id`, `person_spine_source_id`, `source_row_id`, the linked
household's support/source/spine IDs, and person-to-household membership—agree.
The canonical flagged-row receipt SHA-256 is
`90385859bb275ac6394eb7487dd20e4bdf684779127e0cf74bdeb1119b0797e5`.

### Final producer provenance

The manifest target receipt at
`.stage_receipts.impute.stacked_post_puf_transfer.targets["person/puf_tax_itemization/farm_rent_income"]`
records:

- `producer_roles = ["puf_clone"]`;
- `producer_rows = 1006274`;
- `authorized_null_rows = 964699`;
- `imputed_rows = 964699`;
- `residual_null_rows = 0`.

The producer schedule maps the target to
`transfer:person/puf_tax_itemization__batch_3`. That execution group's receipt
records `donor_channel = "asec"`, `donor_clone_index = 1`, donor selection
`owner_projection_of_asec_origin_clone_1`, and recipient selection
`target_specific_complement_of_declared_producer_rows`. The transfer checkpoint
SHA-256 is
`d44963ba6959cfdbfc4ee8d67f98312b0225f62909c85f8e77ea5a861ebd557e`;
the canonical raw-draw SHA-256 is
`67831fe4ac1269bfe1ffa00faf26034e3f10dde7df5333e4673b7c1e6005ed3d`.
The checkpoint raw draw is bit-identical to every final clone-0 cell and every
flagged nonzero cell. This is the direct writer receipt.

### Candidate mechanisms

| Mechanism | Verdict | Receipt |
|---|---|---|
| (a) late producer writes farm rent to native rows | **Confirmed** | Batch 3 authorized and imputed all 964,699 native recipients; raw draw equals final bytes. |
| (b) support-channel attribution drift | Rejected | All physical ASEC/ACS, source-row, spine-ID, person/household, membership, and clone receipts agree. |
| (c) clone fan-out copied PUF values onto base rows | Rejected | All 5,314 rows have a clone-1 counterpart, but 5,236 counterparts are zero and only 11 are bit-equal. |
| (d) gate reads the wrong stacked column | Rejected | `support_role_series` deliberately derives operator role from clone index; clone 0 is native, and 647 physically ASEC-native rows are genuinely nonzero. |

## Whole-class writer repair

Real-pool replay found seven leaves with the same source contract and writer
defect:

| Leaf | Entity | Old final producer | Native nonzero rows | Weighted native nonzero share | Strict gate |
|---|---|---|---:|---:|---|
| `farm_rent_income` | person | `transfer:person/puf_tax_itemization__batch_3` | 5,314 | 0.554078% | farm business income |
| `educator_expense` | person | `transfer:person/puf_tax_itemization__batch_2` | 20,371 | 2.205508% | educator expense |
| `investment_income_elected_form_4952` | person | `transfer:person/puf_tax_itemization__batch_2` | 1,657 | 0.174060% | Form 4952 |
| `salt_refund_income` | person | `transfer:person/puf_tax_itemization__batch_1` | 67,310 | 7.514085% | SALT refund |
| `long_term_capital_gains_on_collectibles` | person | `transfer:person/puf_tax_itemization__batch_1` | 601 | 0.062477% | capital-gain details |
| `domestic_production_ald` | tax unit | `transfer:tax_unit/puf_tax_itemization` | 2,095 | 0.432583% | domestic production |
| `unrecaptured_section_1250_gain` | tax unit | `transfer:tax_unit/puf_tax_itemization` | 2,960 | 0.558256% | capital-gain details |

The old manifest records 964,699 authorized/imputed native recipients and
1,006,274 PUF-clone producer rows for each person leaf. It records 582,318
authorized/imputed native recipients and 597,546 PUF-clone producer rows for
each tax-unit leaf.

The repair declares these exact seven leaves once as
`PUF_TAX_DETAIL_NATIVE_ZERO_OUTPUTS`. The primary stacked PUF stage now:

1. refuses a pre-materialized native value, so upstream contamination cannot
   be silently overwritten;
2. requires every clone-positive PUF value to be finite;
3. hashes the clone-positive payload;
4. writes exact zero only on clone-0/native rows;
5. proves the clone-positive payload remains bit-identical; and
6. emits target-level person and tax-unit receipts.

Those outputs now have `whole_pool` primary ownership and are absent from the
predictive late registry. The late schedule contracts from 19 groups / 70
targets to 18 / 63, while the full target declaration remains complete:
48 early transfer + 63 late transfer + 7 primary native-zero = 118 targets.
The primary output inventory remains 65 and the terminal diagnostic surface
remains 134 variables. The typed US bundle validates at spec SHA-256
`94153c2d9bb5ebb6b2b604cc7a514d11a8f41ed1a1b8dbdaf24ca77ac973569f`;
the compiled producer graph is 37 nodes / 69 edges / 220 outputs.

## Exhaustive dense/sparse release-gate roster

Verdict terms:

- **fixed writer**: the old real pool correctly fails; the writer is repaired
  and the strict gate is unchanged.
- **stacked-safe**: the support/source semantics hold on the real pool.
- **stacked-safe, unrelated red**: the reviewed semantics hold, but another
  genuine content condition in the old candidate is red.
- **stage N/A**: the check consumes output created after the supplied raw pool;
  replaying it at the pool boundary would not be a valid observation.
- **out-of-class N/A**: the boundary is on the release path but does not inspect
  support channels, source presence, or single-spine row semantics.

### Fixed at the writer (6 calls)

| Boundary | Calls | Defining module | Real-pool verdict |
|---|---:|---|---|
| `us_capital_gain_details_signal_gate` | 1 | `capital_gain_details` | fixed writer; both leaves failed correctly |
| `us_domestic_production_ald_signal_gate` | 1 | `domestic_production` | fixed writer |
| `us_educator_expense_signal_gate` | 1 | `educator_expenses` | fixed writer |
| `us_farm_business_income_signal_gate` | 1 | `farm_business_income` | fixed writer |
| `us_form_4952_election_signal_gate` | 1 | `form_4952` | fixed writer |
| `us_salt_refund_income_signal_gate` | 1 | `salt_refund_income` | fixed writer |

### Stacked-safe or valid initial-pool semantics (25 invocations)

| Boundary | Calls | Defining module | Real-pool verdict |
|---|---:|---|---|
| `_health_input_signal_gate` | 2 | release builder | initial stacked semantics safe; unrelated candidate red, then post-stage N/A |
| `assert_puf_capital_gains_tail_survives_selection` | 2 | `puf_capital_gains_tail` | initial preservation passes; post-selection invocation N/A |
| `join_acs_release_predictors` | 1 | `acs_release_predictors` | source boundary stacked-safe |
| `us_alimony_signal_gate` | 1 | `alimony` | stacked-safe |
| `us_child_support_signal_gate` | 1 | `child_support` | stacked-safe |
| `us_childcare_signal_gate` | 1 | `childcare` | stacked-safe |
| `us_disability_benefits_signal_gate` | 1 | `disability_benefits` | stacked-safe |
| `us_education_inputs_signal_gate` | 1 | `education_inputs` | stacked-safe; unrelated AOTC content red |
| `us_energy_subsidy_signal_gate` | 1 | `energy_subsidy` | stacked-safe |
| `us_housing_inputs_signal_gate` | 1 | `housing_inputs` | stacked-safe; unrelated content red |
| `us_medicare_take_up_signal_gate` | 1 | `medicare_take_up` | stacked-safe |
| `us_pregnancy_signal_gate` | 1 | `pregnancy` | stacked-safe |
| `us_prior_year_income_signal_gate` | 1 | `prior_year_income` | authenticated-pool stacked-safe |
| `us_qbi_inputs_signal_gate` | 1 | `qbi_inputs` | stacked-safe |
| `us_reported_coverage_vintage_signal_gate` | 2 | `support_provenance` | source semantics safe; genuine missing-vintage red, then post-stage N/A |
| `us_retirement_contributions_signal_gate` | 1 | `retirement_contributions` | stacked-safe |
| `us_retirement_distributions_signal_gate` | 1 | `retirement_distributions` | stacked-safe |
| `us_ssi_take_up_reporter_source_ids` | 1 | `ssi_take_up` | source boundary stacked-safe |
| `us_weeks_unemployed_signal_gate` | 2 | `weeks_unemployed` | initial replay passes; post-selection invocation N/A |
| `us_wic_claim_signal_gate` | 1 | `wic_claim` | stacked-safe; unrelated producer/content red |
| `us_workers_compensation_signal_gate` | 1 | `workers_compensation` | stacked-safe |

### Stage-conditional N/A on the supplied raw pool (11 boundaries / 13 calls)

| Boundary | Calls | Defining module | Why N/A at raw-pool boundary |
|---|---:|---|---|
| `_exact_k_puf_tail_support_gate` | 1 | release builder | requires exact-K selection output |
| `us_org_wages_signal_gate` | 1 | `org_wages` | release producer has not run |
| `us_other_health_insurance_signal_gate` | 2 | `other_health_insurance` | release producer/final stage has not run |
| `us_scf_auto_loans_signal_gate` | 1 | `scf_auto_loans` | release producer has not run |
| `us_scf_wealth_signal_gate` | 1 | `scf_wealth` | release producer has not run |
| `us_sipp_head_start_signal_gate` | 1 | `sipp_head_start` | release producer has not run |
| `us_sipp_tips_signal_gate` | 1 | `sipp_tips` | release producer has not run |
| `us_sipp_vehicles_signal_gate` | 1 | `sipp_vehicles` | release producer has not run |
| `us_ssi_disability_criteria_signal_gate` | 1 | `ssi_disability_criteria` | release producer has not run |
| `us_ssi_take_up_gate` | 2 | `ssi_take_up` | release producer/final stage has not run |
| `us_voluntary_filing_signal_gate` | 1 | `voluntary_filing` | release producer has not run |

### Reviewed out-of-class boundaries (24 calls)

| Boundary | Calls | Defining module | Verdict |
|---|---:|---|---|
| `_base_population_scale_gate` | 1 | release builder | out-of-class N/A |
| `_degenerate_input_signal_gate` | 1 | release builder | out-of-class N/A |
| `_ecps_parity_gate` | 1 | release builder | out-of-class N/A |
| `_exact_k_frozen_register_fit_gate` | 1 | release builder | out-of-class N/A |
| `_export_input_mass_gate` | 1 | release builder | out-of-class N/A |
| `_input_mass_reference_gate` | 1 | release builder | out-of-class N/A |
| `_qrf_tail_concentration_gate` | 1 | release builder | out-of-class N/A |
| `target_profile_coverage_gate` | 1 | `gates` | out-of-class N/A |
| `us_casualty_loss_signal_gate` | 1 | `casualty_losses` | out-of-class N/A |
| `us_eligibility_inputs_signal_gate` | 1 | `eligibility_inputs` | out-of-class N/A |
| `us_hours_worked_signal_gate` | 1 | `hours_worked` | out-of-class N/A |
| `us_immigration_composition_gate` | 1 | `immigration` | out-of-class N/A |
| `us_medicaid_take_up_gate` | 1 | `medicaid_take_up` | out-of-class N/A |
| `us_misc_itemized_signal_gate` | 1 | `misc_itemized` | out-of-class N/A |
| `us_reform_coverage_smoke_gate` | 1 | `reform_coverage_smoke` | out-of-class N/A |
| `us_register_consistency_gate` | 1 | `register_consistency` | out-of-class N/A |
| `us_relationship_inputs_signal_gate` | 1 | `relationship_inputs` | out-of-class N/A |
| `us_release_input_coverage_gate` | 1 | `release_input_coverage` | out-of-class N/A |
| `us_release_target_parity_gate` | 1 | `release_target_parity` | out-of-class N/A |
| `us_snap_discretionary_exemption_signal_gate` | 1 | `snap_discretionary_exemption` | out-of-class N/A |
| `us_snap_state_take_up_gate` | 1 | `snap_state_take_up` | out-of-class N/A |
| `us_snap_take_up_signal_gate` | 1 | `snap_take_up` | out-of-class N/A |
| `us_take_up_signal_gate` | 1 | `take_up` | out-of-class N/A |
| `us_validation_input_coverage_gate` | 1 | `validation_input_coverage` | out-of-class N/A |

The counts reconcile exactly: 6 fixed + 25 safe/mixed + 13 stage-N/A = 44
in-class invocations across 38 names; adding 24 out-of-class invocations yields
68 direct invocations across 62 names.

## Why the #794 roster sweep missed this gate

#794 did find the farm-business call and the six sibling source-zero gates, but
classified that group as “intentionally unchanged” after a static operator-role
review. Its real-pool replay covered only the gates it modified. It did not run
the unchanged group against the final stacked pool, did not trace each gate's
asserted target through the later transfer receipt, and did not exact-compare
the release call roster to an executable semantic ledger. Farm-business bytes
therefore remained unchanged, and the generic late writer stayed outside the
review boundary.

The replacement method parses `_main` with AST, exact-compares every direct
gate-like call's name, defining module, and multiplicity, scans imported source
for support/source/clone markers, includes explicit source-presence boundaries,
and requires the discovered set to equal the reviewed 38-name ledger. Each
fixed gate is also bound to named acceptance and contamination regressions. A
new or moved direct gate now fails the ledger instead of silently entering an
“unchanged” bucket.

## Regression coverage

Each fixed gate has an assembled ASEC+ACS fixture with clone 0/1/2 semantics.
It must accept native exact zero with nonzero PUF-detail clones and reject a
genuinely misplaced native value independently on physical ASEC and ACS rows:

- `test_us_farm_business_income.py`
- `test_us_educator_expenses.py`
- `test_us_form_4952.py`
- `test_us_salt_refund_income.py`
- `test_us_domestic_production.py`
- `test_us_capital_gain_details.py` (both capital-detail leaves independently)

Writer regressions cover all seven declared leaves, pre-existing native
contamination refusal, exact native-zero materialization, finite clone payloads,
bit-exact clone preservation, integrated primary callback behavior, transfer
partition completeness, producer DAG/schedule identities, HDF/publication
receipts, seed-owner closure, and typed-spec/coverage identities. The six gate
files plus roster passed 120 focused cases. The loader/schema corridor passed
33 focused cases after the shared seed-protocol hash recut.

## Files changed

Runtime/spec ownership and receipts:

- `packages/microcosm-build/src/microcosm/build/spec_engine/{field_usage.py,imputation_semantics.py,inventory_coverage.py,stacked_authority_semantics.py}`
- `packages/microcosm-build/src/microcosm/build/spec_engine/schema/imputation.schema.json`
- `packages/microcosm-build/src/microcosm/build/us/spec/{imputation.yaml,spine.yaml}`
- `packages/microcosm-build/src/microcosm/build/us_runtime/{multispine_pool.py,puf_support.py,stacked_spine.py,us_late_overlap_ownership.py,us_late_producer_registry.py}`

Tests:

- `packages/microcosm-build/tests/test_imputation_lineage_spec.py`
- `packages/microcosm-build/tests/test_spec_engine_{compiler_ir,country_bundles,coverage_tool,field_usage,identity_contracts,imputation_semantics,inventory_coverage,legacy_adapter,loader,plan_lock,stacked_authority_semantics,typed_closure}.py`
- `packages/microcosm-build/tests/test_us_{capital_gain_details,domestic_production,educator_expenses,farm_business_income,fiscal_refresh_builder,form_4952,late_producer_dag,multispine_pool,multispine_pool_h5_io,multispine_pool_tool,salt_refund_income,spec_bundle,stacked_spine}.py`

Generated evidence, documentation, tooling, and handoff:

- `docs/evidence/spec-engine/us-f0-coverage.json`
- `docs/spec-engine.md`
- `docs/us-multispine-operator-ordering.md`
- `tools/spec_engine_coverage.py`
- `tools/us_bundle_generation/imputation.py`
- `PROGRESS.md`
- `out.md`

## Verification

- `uv run pytest`: **7,485 passed, 83 skipped**, 2,354 warnings, 3,602.68s
  (1:00:02), no failures or errors.
- `uv run ruff check .`: **All checks passed!**
- `uv run python tools/ci_test_groups.py --verify`: **313 tracked test files,
  `verification=ok`**.
- Generated spec coverage `--check`: green.
- Worktree handoff: committed, clean, not pushed; no PR opened.
