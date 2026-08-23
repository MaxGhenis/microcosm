# Progress: US firm frame port

## State

Implementation is active on branch `us-firms-frame-port` from `origin/main` at
`d69131a3`. The required source PRs, adversarial review, ADR, and Microcosm
precedents have been audited. No external data has been staged, no artifact has
been built or published, and nothing has been pushed.

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

## Next

- Implement and test the US firm readers, staging manifest, target boundary,
  calibrated frame builder, and hash-bound diagnostics in coherent commits.
- Run shard and workspace validation, build the touched wheels, update
  `FINAL_REPORT.md`, push, and open the required draft pull request.
