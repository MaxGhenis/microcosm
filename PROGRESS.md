# Progress: US firm frame port

## State

Implementation is starting on branch `us-firms-frame-port` from
`origin/main` at `d69131a3`. The lane is reading the source PRs, adversarial
review, ADR, and Microcosm precedents before changing production code. No data
has been staged, no artifact has been built or published, and nothing has been
pushed.

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

## Next

- Audit every required dynamics input and Microcosm reference against the seven
  acceptance gates.
- Implement and test the US firm readers, staging manifest, target boundary,
  calibrated frame builder, and hash-bound diagnostics in coherent commits.
- Add the US support plan and changelog, run shard and workspace validation,
  build the touched wheel, update `FINAL_REPORT.md`, push, and open the required
  draft pull request.
