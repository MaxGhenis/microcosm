# Axiom policy-derived monetary repair — session journal

Journal for the repair of commit `f6e04467` ("Add authenticated policy-derived
monetary targets") on `feature/axiom-policy-derived-monetary`. Per
[CLAUDE.md](CLAUDE.md), this file is history, not state: check git/GitHub for
current truth.

## State

In progress. Reproducing the six policy-layer findings from the exact
independent review before writing any fix.

## Scope

Repair only the policy layer added by `f6e04467`:

- `packages/microcosm-build/src/microcosm/build/policy_monetary_targets.py`
- `packages/microcosm-build/src/microcosm/build/monetary_profile.py`
- `packages/microcosm-calibrate/src/microcosm/calibrate/policy_monetary_binding.py`
- `packages/microcosm-calibrate/src/microcosm/calibrate/matrix.py`
- `packages/microcosm-calibrate/src/microcosm/calibrate/monetary_binding.py`
- `packages/microcosm-calibrate/src/microcosm/calibrate/{solve,score}.py`
- the tests and CI inventory for the above

Out of scope by instruction: `microcosm.frame.adapters.axiom` and the relation
adapter tests (repaired in a separate worktree from parent `f07b79fb`).

## Findings to repair

1. HIGH — materialization receipts can be mixed with unrelated outputs/periods.
2. HIGH — acceptance is self-attestable and fully strippable.
3. HIGH — accepted targets cannot use public `calibrate()` / `score_targets()`.
4. MEDIUM — policy profiles accept contracts the binder always rejects.
5. MEDIUM — acceptance lookup uses the lossy `row_name` display identity.
6. MEDIUM — numeric/schema types do not consistently fail closed.

## Done

- Read the review, `AGENTS.md`, `CLAUDE.md`, and every file `f6e04467` touched.
- Read the parent's `verify_axiom_materialization_receipt` contract (read-only).
- Baseline: `test_policy_monetary_targets.py` + `test_monetary_profile.py` green.

## Next

- Write executable probes for all six findings, confirm each reproduces.
- Implement the defensive fixes; add adversarial + positive public-path tests.
- Run focused tests, ruff, `tools/ci_test_groups.py --verify`, `git diff --check`.
