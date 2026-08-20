# UK flip-prep progress

## State

Analysis is in progress for the UK bundle-mode flip authority inventory,
stochastic audit, and F1 dispatch-charter draft. Dependencies are synced with
both locked country extras. The worktree is detached at
the locally cached `origin/main` SHA
`164027e21cfa58a71d701b43211d009d6182e39d` (2026-08-19 15:28:43 -0400).

The requested sibling path
`/Users/maxghenis/PolicyEngine/_worktrees/microcosm-uk-flip-prep` is outside
the managed writable sandbox. This fresh fallback worktree is therefore at
`/Users/maxghenis/PolicyEngine/microcosm/.worktrees/microcosm-uk-flip-prep-codex`.
The requested `git fetch origin main spec-engine-schema` was attempted first,
but outbound DNS is unavailable; all remote-tracking references used below
are the locally cached references.

## Done

- Read `CLAUDE.md` and the GitNexus exploration skill.
- Confirmed the literal requested worktree target was absent and did not touch
  any existing UK or Maria-owned worktree.
- Attempted the requested fetch and worktree creation, recording both
  environment constraints above.
- Created this isolated fresh fallback worktree from cached `origin/main`.
- Confirmed that the lock supports the UK extra (`policyengine-uk==2.89.0`)
  alongside the US extra (`policyengine-us==1.764.6`).
- Completed `uv sync --all-packages --extra us --extra uk` offline by cloning
  the F1 lane's matching US environment and the exact cached UK wheel into
  writable, isolated locations. The final successful invocation used
  `--offline --no-build-isolation` plus cached Hatchling dependencies because
  the managed sandbox makes the global uv cache read-only. No dataset,
  calibration, or release build ran.

## Next

- Read the schema branch specification, the US F1 inventory template, all UK
  build drivers, and every `uk_runtime` module.
- Write and commit the three requested files under `_UK-FLIP-PREP/`, updating
  this journal after each coherent step.
