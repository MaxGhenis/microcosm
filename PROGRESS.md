# UK flip-prep progress

## State

The authority inventory is complete; this journal update accompanies its
commit. The stochastic audit and F1 dispatch-charter draft are in progress.
Dependencies are synced with both locked country extras. The worktree is detached at
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
- Read `docs/spec-engine.md` from the cached `origin/spec-engine-schema`
  reference, including the Kernels and Rollout F1 sections.
- Read the US F1 authority-inventory template and charter, all three specified
  UK drivers, and all 57 `uk_runtime` modules.
- Completed the 87-row UK authority census and mapped it to compiled owners,
  including 14 concrete schema gaps.
- Wrote `_UK-FLIP-PREP/AUTHORITY-INVENTORY.md`.

## Next

- Write and commit the stochastic audit with its closed callsite census.
- Write and commit the UK F1 charter draft, finalize the output-file report,
  and verify counts, links, and worktree state.
