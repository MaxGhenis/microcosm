# Axiom policy-derived monetary repair — session journal

Journal for the repair of commit `f6e04467` ("Add authenticated policy-derived
monetary targets") on `feature/axiom-policy-derived-monetary`. Per
[CLAUDE.md](CLAUDE.md), this file is history, not state: check git/GitHub for
current truth.

## State

Repair implemented and rebased onto the repaired relation prerequisite at
`952952a1`. A second exact Sol audit of reviewed head `f336b1dc` identified
seven remaining boundary defects; all now have adversarial regressions and
local fixes. All directly affected tests and downstream shards pass. The full
build shard remains red only on failures reproduced unchanged at exact base
`f336b1dc`; this contained follow-up records rather than modifies those
inherited blockers. Nothing was rebased, pushed, published, or opened during
this follow-up.

## Scope

Repair only the policy layer added by `f6e04467`:

- `packages/microcosm-build/src/microcosm/build/policy_monetary_targets.py`
- `packages/microcosm-build/src/microcosm/build/monetary_profile.py`
- `packages/microcosm-calibrate/src/microcosm/calibrate/policy_monetary_binding.py`
- `packages/microcosm-calibrate/src/microcosm/calibrate/matrix.py`
- `packages/microcosm-calibrate/src/microcosm/calibrate/{solve,score,registry}.py`
- the tests and CI inventory for the above

The relation adapter itself was repaired separately, then incorporated here by
rebasing the policy commits after `f07b79fb` onto exact commit `952952a1`. The
policy layer reads that module's public verifier and restates its schema-v2
numeric/string identity contract locally rather than importing private helpers.

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

## Relation integration

- Rebased the four policy commits byte-equivalently from parent `f07b79fb` onto
  repaired relation commit `952952a1`; the rebase completed without conflicts.
- Adapted live policy replay to the relation verifier's three-argument API. The
  binder now reads and validates the raw float64 output first, then supplies the
  exact one-name live-output mapping authenticated by the materialization
  receipt.
- Removed the temporary verifier monkeypatch from the string-keyed policy test.
  The regression now exercises the real repaired verifier and policy replay
  with canonical string row IDs.
- Corrected the synthetic receipt's engine dtype spelling from the invalid
  `Decimal` to the adapter's native `decimal` vocabulary; the repaired verifier
  now authenticates this declaration against the float kernel/output identity.
- Passed 1,257 tests with 42 optional-environment skips across 1,299 collected
  cases: full calibrate (212 passed), full frame/Axiom (323 passed, 42 skipped),
  and the selected policy/monetary/target build suites (722 passed).
- Repository-wide `ruff check .`, branch-file `ruff format --check`, the
  318-file CI test inventory verifier, and `git diff --check` pass. The
  repository-wide format check still reports 124 pre-existing files outside
  this branch; none of the 15 Python files changed by this relation+policy lane
  are among them.

## Exact Sol follow-up audit of `f336b1dc`

- Added nominal `AxiomPolicyTargetSpec` provenance. The authenticated binder
  and registry reload path emit it, plain `TargetSpec` construction refuses
  authenticated policy metadata, and `dataclasses.replace(spec, metadata={})`
  still produces a nominal `AxiomPolicyTarget` that fails closed at matrix
  compilation.
- Refused direct monetary receipts on every nominal policy target. A policy
  target can therefore neither strip its policy receipt nor swap to the generic
  direct-receipt parser.
- Changed policy replay to return an owned immutable copy of the exact verified
  live target vector. The matrix consumes that vector directly and never calls
  the target's overridable `constraint_row` after authentication.
- Classified raw policy record IDs before NumPy conversion. Mixed raw
  integer/string families and bytes now fail before they can be stringified;
  canonical integer and Unicode arrays retain their existing identities.
- Rejected Python integer observations whose exact value cannot survive the
  required float64 `TargetSpec` representation.
- Restricted policy preparation to a materialization receipt with exactly one
  requested output across all executed entities. Complete multi-output replay
  is not implemented, so partial verification is impossible.
- Recorded `trusted_in_process_python_v1` in every acceptance seal and
  documented the threat model: the private seal is defense in depth inside a
  trusted release interpreter, not a sandbox against hostile same-process
  Python; signed producer and observation artifacts remain the durable
  authority.
- Added adversarial tests for every item above, plus registry JSON restoration
  of the nominal spec classification. The focused policy file passes 84 tests;
  full calibrate passes 212; full frame passes 323 with 42 expected dependency
  skips; and the directly affected build group passes 628.
- Passed repository-wide Ruff, format checks for every changed Python file,
  the 318-file CI test-group inventory verifier, and `git diff --check`.
- Reproduced the full build shard's five failures and six collection/setup
  errors at an untouched detached worktree on exact base `f336b1dc`. Two
  release-target parity failures reject an inherited CBO `source_projection`;
  three country-bundle tests pin stale AM/BE/UK spec digests; six coverage-tool
  cases cascade from stale seed-protocol/owner-map digests. The baseline and
  follow-up produce the same failures, so they are residual stacked-branch
  blockers rather than regressions from this diff.

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

## Known unrelated failures

- Two release-target-parity regeneration cases fail identically at exact base
  `f336b1dc` because an inherited CBO `source_projection` fact is rejected by
  the ledger target's `observed_only` assertion policy.
- Three country-bundle cases pin stale AM/BE/UK spec digests.
- Six coverage-tool cases cascade from stale seed-protocol and compiled owner-
  map digests. All eleven outcomes were reproduced in a detached, untouched
  worktree at `f336b1dc` before this repair was committed.

## Next

- Human review of the integrated relation and policy-derived monetary lane.
- Native Axiom dense-extension and external RuleSpec integration tests remain
  environment-gated; no artifact, publication, push, PR, or merge was performed.
