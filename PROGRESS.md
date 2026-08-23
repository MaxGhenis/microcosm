# Progress: US firm frame port

## State

Implementation and local validation are complete on branch
`us-firms-frame-port` from `origin/main` at `d69131a3`. The required source
PRs, adversarial review, ADR, and Microcosm precedents have been audited. No
external data has been staged, no real-data artifact has been built or
published, and nothing has been pushed. Synthetic test artifacts exist only
in pytest temporary directories.

Remote publication is blocked: the connected GitHub branch-creation write
returned `user cancelled MCP tool call`, while the sandboxed shell cannot
resolve `github.com`. The remote branch and draft PR therefore do not exist.

This dated lane state supersedes the completed replacement-scorecard journal
that was present on the branch point; that journal remains available in git
history at `d69131a3`.

## Done

- Read the repository agent guide and confirmed the uv-workspace,
  namespace-package, PR-CI/certification, wheel, and root-journal rules.
- Confirmed the requested branch and base commit, the PolicyEngine/microcosm
  origin, and an otherwise clean tracked worktree.
- Identified `.ceremony-log/` as pre-existing untracked workspace state and
  left it untouched.
- Reproduced the committed SUSB migration extract's 97 positive sector-by-size
  target cells, 6,461,497 non-additive sector firm counts, and 135,748,407
  employees; all raw-data-dependent claims remain unverified.
- Identified and addressed the calibration API mismatch: standalone firm tables
  cannot be represented by the current person/group `Frame`, so a public,
  receipt-bearing bounded moment calibration entry point was added to
  `microcosm-calibrate` instead of fabricating person-to-firm memberships.
- Passed all 210 `microcosm-calibrate` tests and focused Ruff checks for the new
  public API.
- Added the US firm support plan and changelog, documenting artifact ownership,
  source measurement models, the Ledger/migration boundary, the raw-employment
  dynamics seam, the non-additive SUSB sector margin, and unresolved unit and
  timing questions.
- Ported the Form 5500 and OSHA ITA readers. Form variants now use a consistent
  end-of-year participant measure, select one coherent size-defining filing,
  preserve full NAICS and plan/entity strata, and refuse fractional counts;
  OSHA retains record/establishment identifiers and ownership and still
  requires an explicit quality cap. The 25 fixture tests pass and two pinned
  real-data tests skip because no external files are staged.
- Added fail-closed external staging for the three immutable raw pins (a
  244,927,049-byte download set): exact size and SHA-256 admission, atomic
  partial-file adoption, exact ZIP-member extraction, a 3 GB raw-plus-expanded
  ceiling, and a rehashing builder receipt. All nine staging and CLI tests pass;
  no source download was attempted.
- Added the production Ledger consumer-facts target adapter and separately
  named, hash-pinned SUSB/BDS migration harnesses. The SUSB harness reproduces
  97 positive cells, 446 published detail rows, 6,461,497 non-additive sector
  firm counts, 135,748,407 employment, and 132,086,430 employment after the
  NAICS 55 scope exclusion. All 18 target tests pass.
- Added the observed sponsor-frame builder and hash-bound artifact contract.
  Production builds rehash a typed staging receipt at the build boundary;
  secrets-free fixtures use a separately labelled donor-content receipt.
  The output preserves raw employment and source/entity strata, excludes
  NAICS 55 before the employment solve, uses the public bounded dual-moment
  calibration API, and reports bounded and support-infeasible residuals rather
  than hiding them.
- Added the complete positive target-cell table and rectangular-grid receipt,
  unmatched donor-cell evidence, global and per-cell weight/leverage/Kish-ESS
  diagnostics, both failed post-stratification attempts, source-specific OSHA
  aggregation evidence, and a BDS firm-margin comparison that separates
  frame/SUSB error from SUSB/BDS disagreement. Nine synthetic contract tests
  pass and the pinned real-data builder test skips because no source files are
  staged.
- Added an atomic three-file `populace-us-firms` artifact writer and verifier.
  Both sides validate the firm table and Parquet metadata; the manifest binds
  firm bytes, diagnostics, configuration, row count, and the build identity.
- Added a local artifact build CLI that refuses an implicit target choice,
  re-verifies pinned staging, requires explicit acknowledgement of the SUSB
  migration harness, leaves OSHA dormant without an explicit employee cap,
  and refuses an existing output directory. Four CLI tests pass and the
  conditional real-data build skips without staged files.
- Corrected the ported target sidecar's loader and seam ownership references,
  re-pinned both sidecar receipts, and kept its QWI/J2J entries explicitly
  labelled as dynamics-reference provenance rather than frame targets. The
  offline staging `--list` path now bypasses the heavyweight US runtime import
  and completes without creating the configured data directory. All 28 staging
  and target tests pass after the correction.
- Completed lock-matched validation, one process per shard: 6,332 build tests
  passed with 41 skips; 210 calibrate tests passed; 295 frame tests passed with
  36 skips; 93 fit tests passed; and 275 data tests passed with one skip. The
  workspace total is 7,205 passed, 78 skipped, and zero failed.
- Diagnosed and discarded an initial contaminated-venv result: its NumPy 2.5.1
  and scikit-learn 1.9.0 differed from the lock's 2.4.6 and 1.8.0, changing
  intentionally version-bound seed/spec hashes. A wrapper-only fallback also
  failed to reach QRF child processes. Direct inherited `PYTHONPATH` with the
  exact locked environment made both the focused failures and the complete
  build shard green without source or pin changes.
- Passed repository-wide `ruff check .` and `git diff --check`.
- Built and inspected both touched wheels. The calibrate wheel SHA-256 is
  `e50708b10599b143c90fee6ffafb1e9c667e38c3951ff028f2ffbe5903192a7`.
  The 2,316,925-byte build wheel SHA-256 is
  `98f6fd312245408d0e0bab24a58352c752c6b93cfe2e4f551097d33b70d2ba65`;
  all 365 ZIP entries validate and all 13 US-firm entries are byte-identical to
  source.
- Replaced the historical root report with the structured US firm port report,
  including deliberate exclusions, all seven acceptance gates, reproduced and
  unreproduced figures, Vahid review questions, and publication blockers.

## Next

- Restore GitHub write authorization or network access, push
  `us-firms-frame-port`, and open the required draft pull request without
  reviewers.
- Publish a Chronicle SUSB package and activate a Ledger `us_firms` target
  profile before treating production targets as available.
- Stage the exact external pins outside git and run real-data certification to
  resolve acceptance gates 1 and 4-7 before artifact promotion.
