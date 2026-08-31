CLASSIFIER-FIX-COMPLETE

# Period-aware ownership classification — continuation lane

Date: 2026-08-30

Branch: `stacked-dense-gate-sweep`

Lane base: `1d580e43` (the quota-dead sol lane's last commit; original lane
base `dc7e09cb`)

> The previous lane report this file carried — the authorized stacked
> `weeks_worked` implementation v3 — remains at commit `5ef9237e`.

## Result

Both parts are complete. The sol lane's classifier core is correct and is now
independently verified rather than asserted; the one production caller its
audit missed is fixed; the three red-test classes it left behind (it never got
CPU to run them) are fixed; the spec attestations its kernel edits legitimately
moved are refreshed; and part 2's adapter question is adjudicated against read
engine source on both readings of the ambiguous name.

### Part 1 — verified, and completed

**The core behaves as specified.** Against installed PolicyEngine-US 1.819.0 /
Core 3.31.0, the import-free source index carries 6,146 variables: 5,218
computed at 2024, 5,219 at 2025. `weeks_worked` resolves `INPUT` at 2024 and
`DELEGATION` at 2025/2026/2030, each with material owner `INPUT` at
`(2024, 1, 1)` and the full year-by-year chain. The chain arithmetic matches
Core's own `Period.last_year`
(`start.offset("first-of", "year").period("year").offset(-1)` — the prior
calendar year beginning 1 January, even from a sub-annual period), the
recognizer accepts only the exact `return entity(name, period.last_year)` body
so a transformed carry-forward stays a material formula, and unbounded
delegation raises rather than resolving (regression present).

**The dated view is a strict widening of the static one.** The static
all-vintage `variables()` projection holds 924 names; the dated view holds 928
at 2024 and 927 at 2025, with `variables()` a subset of both. The difference is
`weeks_worked` plus three New Jersey variables whose only formula commences in
2026 (`nj_property_tax_relief`, `nj_property_tax_relief_income`,
`nj_staynj_eligible`). None of the three is referenced anywhere in microcosm, so
the widening reaches no gate, manifest, transfer target, or pool boundary.

**The static seed sets cannot deadlock a build.** All six
`PUF_TAX_DETAIL_FORMULA_OWNED_OUTPUTS` entries are still engine-owned at both
2024 and 2025, so `assert_formula_owned_blocklist_current` passes at the release
period. The twelve-name `FORMULA_OWNED_SOURCE_COLUMNS` pool exclusion diverges
only on `weeks_worked` at 2024 — exactly what the upgraded parity test asserts —
and the exclusion itself is unchanged.

**The caller audit is closed with an orthogonal proof.** An AST sweep of
`packages/` and `tools/` for calls to every dated entry point reports six call
sites without an explicit `period`: three are the UK path's own periodless
`default_values` (deliberately out of this US-scoped fix) and three are the
`pytest.raises(TypeError)` proofs that the period is mandatory. No unintentional
periodless US ownership call site remains.

**One production caller was missed, and is fixed.**
`assert_validation_leaf_registry_current` classified registry leaves with the
periodless `Variable.is_input_variable()` and carried an implicit `period=2026`
default that the release tool never passed. Ownership now resolves through the
adapter's dated `variable_ownership`/`input_variables` APIs, `period` is a
required keyword, and the release caller passes the new explicit
`US_VALIDATION_PROVISION_PERIOD` (2026 — the provision evaluation period, which
is deliberately not the 2024 dataset build period). The change was proved
behavior-preserving before it was made: exactly zero variables are any-vintage
formula-owned yet uncomputed at 2026, and all thirteen registry leaves carry no
formula at any vintage.

**The parity coverage proves dated resolution, not set agreement.**
`test_formula_owned_source_boundary_matches_installed_source_index` asserts 11
owners at 2024 and 12 at 2025 with the ownership kinds and the delegated owner
period; the frame suite adds exact source-vs-live agreement at both periods and
an end-to-end regression that writes `weeks_worked` as a 2024 input, reloads it
through a real `Microsimulation`, proves the 2025 carry-forward returns the 2024
values, and blocks a direct 2025 write.

### Part 2 — adjudicated on both readings

The lane prompt names "the microcosm-frame PolicyEngine-US adapter's
`_derived_metadata`", but that identifier exists only in the Axiom adapter, so
both readings were carried out.

The PolicyEngine-US reading is the metadata index the sol lane made dated and
this lane verified above.

The Axiom reading was adjudicated against `axiom-rules-engine` at
`8430cdea0ba6ce6c5d90cfafaa90b89e0474df76` (the four cited files clean at that
commit). RuleSpec derived rules *are* effective-dated (`DerivedVersionSpec`
carries `effective_from`/`effective_to`, `src/spec.rs`), but the dense compiler
keeps only the single unbounded version's commencement date
(`CompiledDerived.effective_from`, `src/dense.rs`) and `check_commencement`
fails the entire execution with `MissingDerivedFormulaVersion` when the period
starts before *any* plan rule commences. A pre-commencement period therefore has
no lawful answer the dataset could supply, so the export contract's period-blind
rejection of derived names cannot reproduce the `weeks_worked` defect class
there. The commencement date is not exposed to Python (`DerivedMetadata` and its
pyo3 handle carry name/id/entity/dtype/unit/period/source, where `period` is the
authored granularity), so relaying a dated pre-commencement message needs an
engine-side surface addition, not an adapter classifier change. The finding is
recorded in the adapter docstring rather than replaced by a speculative fix.

## Commits (this lane, on `1d580e43`)

- `9a9ee665` Require an explicit period for validation leaf ownership
- `f55898c9` Record the Axiom derived-metadata period verdict
- `1572e341` Journal the caller-audit completeness proof
- `f95b0df9` Journal the input-view counts and chain arithmetic proof
- `0e180d34` Format the three files this lane left drifted
- `855f40ec` Fix the red US-path stub in the UK coverage test
- `0c02834d` Correct the PUF donor stub's source-year expectation
- `1ba3a592` Refresh the seed attestations this lane's kernel edits moved
- `PLACEHOLDER_REPORT_COMMIT` Report the completed period-aware classifier fix

## Red tests the sol lane left behind (all fixed)

1. `test_uk_release_input_coverage.py::test_default_us_coverage_path_is_unchanged`
   asserted the US default probe receives `['dividend_income']`. The gate probes
   only manifest-relevant columns, and this manifest's single required column is
   absent from the frame, so the probe receives no names. The stub now records
   the call and asserts both the empty list and the forwarded 2024 period.
2. `test_us_puf_support_base_builder.py::test_main_runs_cps_only_inputs_before_clone_and_after_puf_then_fails_gate`
   (ten parametrizations) asserted the builder forwards a non-`None` source-year
   PUF CSV, but this fixture's args namespace omits it and `_run_all` forwards
   the documented `None`.
3. The spec identities moved.
   `microcosm.build.us_runtime.acs_transfer`, `puf_qrf_chain`, and `puf_support`
   are attested kernel source modules whose bytes `source_inventory_sha256`
   hashes into the seed protocol digest, which feeds the compiled seed map and
   the spec binding; the period plumbing edited all three, and since the
   branch's last attestation refresh (`deb42a37`) no other commit touches them.
   Refreshed exactly the two moved digests (`seed_protocol`
   `a16b77d7…`→`7ea964c4…`, `seed_map` `44c64c54…`→`2c43e303…`), re-pinned the
   pool-tool spec-binding fixture (`e9ea75c7…`→`2f08db42…`), and regenerated
   `docs/evidence/spec-engine/us-f0-coverage.json`, whose diff carries those two
   digests and nothing else. The spec binding is asserted out of every
   checkpoint identity, so no pool checkpoint is invalidated.

## Focused verification

Focused corridors only — the repository-wide suite is deferred by instruction
while candidate-26 holds this machine's cores from another worktree. Every run
below is `uv run pytest` on this lane's tree:

| corridor | result |
| --- | --- |
| frame adapter + metadata index (`test_policyengine_us_adapter.py`, `test_policyengine_us_metadata_index.py`) | 59 passed |
| pool / stacked spine / PUF support (`test_us_multispine_pool.py`, `test_us_stacked_spine.py`, `test_us_puf_support.py`) | 411 passed |
| ACS + coverage (`test_puf_qrf_chain.py`, `test_release_input_coverage.py`, `test_uk_release_input_coverage.py`, `test_us_acs_local_release_tool.py`, `test_us_acs_multispine.py`, `test_us_acs_multispine_legacy_builder.py`, `test_us_acs_transfer.py`) | 259 passed, 3 skipped, 1 failed → fixed; the failing file re-ran 44 passed, 3 skipped |
| remaining touched build files + late-producer DAG (16 files) | 727 passed, 11 failed → all fixed; the PUF file re-ran 10 passed, the pool-tool digest test re-ran green |
| spec engine (`test_spec_engine_seeds.py`, `test_spec_engine_inventory_coverage.py`, `test_country_spec.py`, `test_us_spec_bundle.py`) | 115 passed, 1 failed → fixed by the attestation refresh |
| post-refresh confirmation (inventory coverage, coverage tool, field usage, pool-tool spec binding) | 36 passed |
| weeks corridor (`test_us_release_weeks_worked.py`, `test_us_hours_worked.py`, `test_us_org_wages.py`, `test_us_plan.py`, `test_us_l0_refit_export.py`) | 154 passed |
| validation input coverage (this lane's new regressions) | 18 passed |

A consolidated single-process re-run of all 32 files was still executing when
this report was written; every file in it has already passed individually on
this tree, and its purpose is one-tree confirmation rather than new coverage.

Static checks: `ruff check` green on all 48 Python files this lane touched;
`ruff format --check` flags six of them, and all six were verified already
drifted at the lane base `dc7e09cb` (checked against the base blobs), so the
lane leaves no new drift — the three it did drift were formatted, and the
pre-existing ones are deliberately left unreflowed; `git diff --check` clean;
`tools/ci_test_groups.py --verify` reports `verification=ok`.

## Deliberately unchanged

No gate threshold, pool exclusion list, release path ordering, or authorized
weeks-stage behavior was touched. Candidate evidence stayed read-only. Nothing
was pushed, no PR was opened, and no build ran.

## Deferred

- **Repository-wide pytest.** The candidate-26 build owns this machine's cores
  from another worktree; the lane ran focused corridors only, as instructed. The
  full suite still needs one clean run after that build finishes.
- **UK ownership classification.** `policyengine_uk._is_engine_computed` and the
  UK release coverage path (`uk_runtime/release_input_coverage.py`, and
  `tools/build_uk_efrs_parity_reference.py`) remain periodless — the same defect
  class, deliberately outside this US-scoped fix. Closing it needs a UK dated
  view and a UK certification re-run.
- **Axiom engine surface.** Per-rule commencement dates are not exposed to
  Python, so the adapter cannot pre-empt a pre-commencement run with a dated
  message. That is upstream `axiom-rules-engine` work.
- **Post-`end` semantics, recorded not changed.** A variable past its `end` date
  classifies as `INPUT` in both the dated source index and the live classifier,
  while PolicyEngine Core's `set_input` silently drops inputs for such periods —
  so persisting one is inert rather than harmful. Pre-existing, pinned by an
  existing regression, and left alone.
