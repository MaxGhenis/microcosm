# Canonical survey sex source projection and binding fragment

Lane journal for `us-canonical-sex-binding-20260913` (worktree
`_worktrees/microcosm-us-canonical-sex-binding-20260913`). Accurate when
written; check git/GitHub afterwards. This is a lane journal, not the root
`PROGRESS.md`, which belongs to another lane and is cumulative.

Base: clean head `a96fc850942d3fd96d24251c07d9ebc38b79f8de`, which root
confirmed includes freshly fetched `origin/main` `15ebde`.

## Scope

Implement the bounded seam described in the reviewed plan
`codex-canonical-sex-binding-20260913/PLAN.md`:

- `current_survey_sex.py` — a descriptive, source-owner-backed helper that
  reuses `qualify_current_asec_demographics` and `verify_acs_native_coverage`
  and returns rowwise qualified sex values with separate code/value/allocation
  knownness.
- `graph_current_survey_sex.py` — a typed two-node graph fragment
  (`survey_sex.source_projection` + `survey_sex.bind`) usable independently of
  the accepted 38-node US host.

Root decision carried into the implementation: preserve the validated ACS
source `SEX` value with explicitly **unknown** allocation provenance. Never
label it unallocated and never fabricate `FSEXP`. ASEC uses the existing
qualified `A_SEX` plus `AXSEX` with raw/binding/allocation knownness. The
historical composed-stage unbound guard is untouched. No age gate, headship,
default or imputation.

## Runtime status (read this before believing anything is green)

This lane is **static-check only** by explicit instruction. `pytest`,
country/source imports, native data, engine, fit, installation and network
fetches were **not** run here. The tests added by this lane are **unexecuted**.
Runtime belongs to a separately frozen, root-reviewed invented-only packet.

## State

In progress.

## Done

- Read the plan and re-verified its central citations against the checkout:
  `asec_demographic_source.py` sex/allocation code tables and the
  both-fields-named binding rule, `current_asec_demographics.py` person
  projection columns, `acs_inputs.py`/`current_survey_predictors.py` ACS
  `SEX`/`is_female` path, `current_survey_health_coverage.py` +
  `graph_current_survey_health.py` as the fragment template, and
  `graph_current_survey_geography.py` as the qualifier/kernel template.
- Recorded the `microcosm.graph` `Owned(rewrite=True)` contract that a
  declared full-column rewrite must satisfy.

## Next

- Write `current_survey_sex.py` and `graph_current_survey_sex.py`.
- Write `test_us_current_survey_sex.py` (pure/declaration cases) and
  `test_us_current_survey_sex_graph.py` (tiny invented-source graph controls).
- Run only the permitted static checks: stdlib AST, ruff, and
  `tools/ci_test_groups.py --verify`.
- Write `BUILD-RESULT.md` into the packet directory.
