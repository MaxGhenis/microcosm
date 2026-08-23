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

## Next

- Implement and test the US firm readers, staging manifest, target boundary,
  calibrated frame builder, and hash-bound diagnostics in coherent commits.
- Add the US support plan and changelog, run shard and workspace validation,
  build the touched wheel, update `FINAL_REPORT.md`, push, and open the required
  draft pull request.
