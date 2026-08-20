# UK flip-prep progress

## State

Stochastic-ledger drafting is in progress from detached cached `origin/main` commit
`164027e21cfa58a71d701b43211d009d6182e39d` in the isolated worktree
`/Users/maxghenis/PolicyEngine/microcosm/.worktrees/microcosm-uk-flip-prep`.
No package or UK source files will be edited, no builds will run, and nothing
will be pushed.

The requested `git fetch origin main spec-engine-schema` could not resolve
`github.com` in the managed sandbox. The requested sibling worktree path was
outside the writable sandbox, so the worktree is nested under the writable
repository sandbox instead. The locally cached spec ref is
`origin/spec-engine-schema@c4e1eb7fc3ae5246a9b8e5d4a63cb7195aaf8cfa`.

## Done

- Read the repository operating instructions.
- Read the GitNexus exploration skill; its MCP knowledge-graph service is not
  available in this session, so the audit will use exhaustive direct source
  discovery and call tracing.
- Verified the requested worktree path did not already exist.
- Attempted the required fetch and recorded the network limitation.
- Created a fresh detached worktree from the cached `origin/main` ref.
- Verified the lock exposes both `us` and `uk` extras. Dependency sync created
  the isolated `.venv` but could not finish because the managed sandbox could
  not resolve the package index; no dataset build was run.
- Read the cached spec-engine schema branch's Kernels and Rollout F1 sections,
  the US F1 inventory and charter, all three UK drivers, every `uk_runtime`
  module, and the UK declarative stage/geography resources.
- Traced the UK driver graphs and independently enumerated stochastic, hash,
  UUID, and clock sites at AST/source level. Reconciled the stage seed families:
  identity-keyed `0`, SPI/HMRC `42` then `43`, and national sampling `578`.
- Identified a blocking geography default mismatch: the rowwise drivers default
  to seed `42`, while the spec-branch ladder skeleton declares default seed `0`.
- Identified a blocking schema/ABI gap: the current executable spine contract is
  US-stacked-pool-specific and the UK walking skeleton compiles no executable
  producer nodes.
- Wrote `_UK-FLIP-PREP/AUTHORITY-INVENTORY.md`: 30 selected-driver semantic
  authority groups, each with source anchors and a compiled-IR/bundle owner;
  12 distinct missing schema paths are sketched and counted once.

## Next

- Draft and independently cross-check the stochastic ledger/exemptions,
  including exact physical/logical counts and seed reconciliation.
- Write the UK F1 charter under `_UK-FLIP-PREP/`, validate internal counts and
  links, commit each coherent artifact step, and record final counts and risks
  here.
