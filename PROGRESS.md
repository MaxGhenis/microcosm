# UK flip-prep progress

## State

Complete. All three analysis artifacts and the review reconciliation are
committed. Final non-build verification passed on review commit `cdbadd15`;
this journal update records the handoff state.
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
  UK drivers, and all 55 `uk_runtime` modules.
- Completed the 87-group UK authority ledger and mapped it to compiled owners,
  including 11 new schema/IR fields and five existing-field generalizations.
- Wrote `_UK-FLIP-PREP/AUTHORITY-INVENTORY.md`.
- Closed the AST/semantic stochastic census at 79 actual scoped calls (80 AST
  candidates including one deterministic false positive): 40 ledger-bound
  calls, 38 true exemptions, and one required policy-clock binding, lowering
  to 34 logical ledger rows (32 draw/hash-draw, two reset-only controls).
- Reconciled source-stage seeds 0/42/43 with runtime behavior and separated the
  historical take-up fitting seed 42 from live seed-0 assignments.
- Wrote `_UK-FLIP-PREP/STOCHASTIC-AUDIT.md`.
- Drafted the UK F1 dispatch charter as a one-day post-US-certification
  playbook, with an explicit pre-dispatch P0 schema/compiler closure gate.
- Embedded the final analysis report, headline counts, and top risks in
  `_UK-FLIP-PREP/UK-F1-CHARTER-DRAFT.md` so no fourth output is required.
- Reconciled two independent adversarial reviews: corrected exact compiled
  owner paths and schema taxonomy, added two implicit temp-name nonce sites,
  separated the policy evaluation date from operational clocks in cache-key
  doctrine, and closed the UK tier/grandfathered-release grammar.
- Verified 87 authority rows; 34 logical stochastic rows; 40 non-ledger
  classifications (38 true exemptions, one policy-clock binding, one false
  positive); the 9+2 new-field split and five generalizations; all 55 runtime
  module mentions; exactly three output files; and `git diff --check`.
- Confirmed the review commit had a clean worktree. Only `PROGRESS.md` and the
  three requested analysis outputs changed from the fresh base. No source
  edit, dataset build, test build, branch push, or María-owned worktree touch
  occurred.

## Next

- Owner collects the three files. A future UK F1 lane starts only after the US
  F1 certification and every charter P0 prerequisite are green; there is no
  remaining in-scope work for this analysis lane.
