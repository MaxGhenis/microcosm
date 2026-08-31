# Axiom policy-derived monetary repair — session journal

Journal for the repair of commit `f6e04467` ("Add authenticated policy-derived
monetary targets") on `feature/axiom-policy-derived-monetary`. Per
[CLAUDE.md](CLAUDE.md), this file is history, not state: check git/GitHub for
current truth.

## State

Repair implemented and verified locally. All six review findings were first
reproduced with executable probes, then closed. A follow-up exact audit found
that the initial stripping regression still supplied the external acceptance:
stripping both all target metadata and the optional compiler argument demoted
the row to an ordinary target. The registry now emits a nominal
`AxiomPolicyTarget` classification outside metadata, and the exact combined
stripping probe fails closed. Nothing was pushed and no PR was opened.

## Scope

Repair only the policy layer added by `f6e04467`:

- `packages/microcosm-build/src/microcosm/build/policy_monetary_targets.py`
- `packages/microcosm-build/src/microcosm/build/monetary_profile.py`
- `packages/microcosm-calibrate/src/microcosm/calibrate/policy_monetary_binding.py`
- `packages/microcosm-calibrate/src/microcosm/calibrate/matrix.py`
- `packages/microcosm-calibrate/src/microcosm/calibrate/{solve,score,registry}.py`
- the tests and CI inventory for the above

Out of scope by instruction: `microcosm.frame.adapters.axiom` and the relation
adapter tests (repaired in a separate worktree from parent `f07b79fb`). This
branch reads that module's public verifier and restates its schema-v2 numeric
identity contract locally rather than importing private helpers.

## Findings and how each was closed

1. **Receipt/output mixing (HIGH).** `bind_materialization_output()` binds a
   materialization receipt to one exact calendar-year period, output entity,
   requested output variable, row count, and canonical typed value/row
   identity. It runs at preparation, on the serialized payload, and again
   against the live frame. The prepared receipt (schema v3) now carries the
   materialized identities so the frameless payload validator can check them.
2. **Self-attestable acceptance (HIGH).** `AxiomPolicyTrustRoot` holds
   operator-supplied, mutually distinct producer and observation keys.
   `build_axiom_policy_acceptances()` verifies both signed artifacts and mints
   sealed `AxiomPolicyAcceptance` values under a process-private HMAC key, so
   callers cannot construct one. Each acceptance pins the typed `Target.key`
   and the exact accepted set; a row whose key is accepted but whose receipt
   was stripped fails the compilation.
3. **Public API plumbing (HIGH).** Keyword-only `policy_acceptances` on
   `calibrate()` and `score_targets()`. `refit_l0_selection()` and
   `calibrate_l0_refit()` refuse policy rows by name — a subset frame cannot
   reproduce a full-pool receipt and no subset receipt exists yet.
4. **Profile contracts (MEDIUM).** `requires_policy_output` now requires
   `period_match_policy="exact"` and an `annual_flow` basis.
5. **Lossy acceptance key (MEDIUM).** Acceptances are keyed by the typed
   `(name, period)` identity; row-name-keyed mappings are refused by name.
6. **Type coercion (MEDIUM).** `_same()` refuses cross-type equality
   throughout; shapes must be `list[int]`; observed values must be `float` in
   the receipt and `int`/`float` at bind.

## Follow-up exact audit

- Reproduced the remaining combined-stripping bypass by removing the complete
  metadata mapping and omitting `policy_acceptances`; the PIT row compiled as
  an ordinary target before the follow-up fix.
- Added the nominal `AxiomPolicyTarget` emitted only after `TargetSpec`
  validates the policy receipt. `dataclasses.replace(..., metadata={})`
  preserves that concrete type, so the compiler still requires the receipt and
  independent acceptance even after every serialized marker is removed.
- Preserved the ordinary `Target` class and all public matrix, calibration, and
  scoring signatures. Existing authenticated policy paths and ordinary/direct
  target paths remain green.
- Generalized policy row, membership, and target identities to the relation
  adapter's canonical integer and string ID families. Numeric IDs remain
  little-endian int64; string IDs use canonical JSON UTF-8 identities. Mixed,
  boolean, float, cross-family, and incoherent encoding declarations fail
  closed.
- Re-ran 934 focused and broader policy/calibration tests, repository-wide
  Ruff, touched-file formatting, the CI test inventory verifier, and
  `git diff --check` successfully.

## Done

- Read the review, `AGENTS.md`, `CLAUDE.md`, and every file `f6e04467` touched.
- Reproduced all six findings (11 distinct bypasses) with a probe harness.
- Implemented the fixes above; rewrote the policy-monetary test suite.
- `uv run pytest` focused + regression: 923 passed (calibrate shard, policy
  monetary, monetary profile/targets, ledger targets, gates, target
  materialization, exact-k ladder, US fiscal targets).
- `ruff check .` clean; touched files `ruff format` clean;
  `tools/ci_test_groups.py --verify` ok with the test file in `fast/rest` and
  `engine us-am:build`; `git diff --check` clean.

## Known unrelated failure

`packages/microcosm-build/tests/test_release_target_parity.py::TestRegeneration`
fails identically before and after this repair (a CBO `source_projection` fact
rejected by `ledger_targets.py` assertion policy). Verified by restoring the
pre-repair files and re-running.

## Next

- Rebase/merge alongside the separately repaired parent `f07b79fb` and re-run
  the policy tests against the repaired relation adapter.
