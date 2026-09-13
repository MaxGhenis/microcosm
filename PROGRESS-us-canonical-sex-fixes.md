# Canonical sex source-only review fixes

Owned branch: `microcosm-us-canonical-sex-fixes-20260913`, based on
`a1e251c9b2c642b399bf6cf861df7ae00e9986e9`. The freshly fetched
`origin/main` at setup was `15ebde806cd1a262363f7217fe535c7234ff757f`;
the base contains it (243 ahead, zero behind). The builder checkout was
preserved. No push or accepted host integration was performed.

## Changes

- Extend the maintained preparation executable fence to the canonical sex
  qualifier and graph fragment. Check explicit source identities and live
  functions, code, defaults, closures, methods and contract constants around
  owner callbacks. Bind the actual host function callback as well.
- Keep the independent expected-population reconstruction unchanged. All 42
  pre-existing top-level functions outside the qualifier/factory edits have
  identical ASTs to the base, including the numerical binding and verification
  functions.
- Incorporate all 13 test function bodies from builder commit
  `4f2ee9ede430d90e80f19139570d3d3b6a979cc1` unchanged. This includes the
  corrected unowned-column assertion, actual post-CREATE REWEIGHT/cold/required
  path, and verification against the actual retained incoming population.
  Incorporation was manual because this branch already had dirty fence work.
  The two fixtures use opaque mutable callback-counter state to keep the
  executable closure configuration unchanged; the first fixture also supplies
  the new mutation hook. No duplicate structural fixture was retained.
- Add 36 adversaries: nine function/code/default/constant/callback mutations
  at the first and final owner callbacks of each of the two graph nodes. Add
  one refusal case for an opaque callable object without a function seal.
- Add a separate source-owner test file using the maintained
  `_demographic_arguments` fixture and actual authenticated preparation. Two
  cases cover known/unresolved source observations; ten mutate executable
  behavior at the first/final direct preparation borrow. No source issuer or
  checked accessor is replaced by a stand-in. These tests construct invented
  source bytes and need a separate resource scope from the pure/graph tests.

## Verification and limits

Actually passed: Ruff check and format check; `git diff --check`; stdlib
AST parsing/compilation without execution; `tools/ci_test_groups.py --verify`
(`verification=ok`); exact AST preservation checks described above.

The source roster is 39 test functions / 100 parametrized cases: 38 in
`test_us_current_survey_sex.py`, 50 in its graph test file, and 12 in its
source-owner test file. **None were executed here.** No project import, native
data, engine, model, fit, host run or dataset build occurred. Writing actual-owner
tests is not evidence that they pass; invented graph fixtures do not establish
source authority.

Root must independently review and freeze this source before an invented-only
runtime packet executes the first two files. The third file needs its own
reviewed invented-source packet, using the maintained real owners. Genuine native
source qualification and accepted country-host integration remain later steps.
