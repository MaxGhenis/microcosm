# UK flip-prep progress

## State

Independent validation is in progress over the completed draft from detached cached `origin/main` commit
`164027e21cfa58a71d701b43211d009d6182e39d` in the isolated worktree
`/Users/maxghenis/PolicyEngine/microcosm/.worktrees/microcosm-uk-flip-prep`.
All three requested analysis artifacts and this journal are committed. No
package or UK source file was edited, no dataset build was run, and nothing was
pushed.

On 2026-08-20, a fresh reviewer resumed this clean lane after finding the
pre-existing committed draft. The reviewer rechecked ancestry/scope and retried
`uv sync --all-packages --extra us --extra uk` with a writable temporary cache.
The lock resolved all 118 packages, then installation stopped at the managed
network boundary while fetching `policyengine-core==3.26.11` from PyPI. No
dataset build ran. Independent read-only reviews of authority coverage and the
stochastic census are in progress. The charter review is complete: it hardened
machine-decidable seed/gate/consumer dispatch conditions, network brokering,
release-identity sealing, PR-CI fixtures, the concrete resume predicate, and the
15-GiB/24-hour preflight envelope.

The requested `git fetch origin main spec-engine-schema` could not resolve
`github.com` in the managed sandbox. The requested sibling worktree path was
outside the writable sandbox, so the worktree is nested under the writable
repository sandbox instead. The locally cached spec ref is
`origin/spec-engine-schema@c4e1eb7fc3ae5246a9b8e5d4a63cb7195aaf8cfa`.

## Done

- Read the repository operating instructions.
- Read the GitNexus exploration skill; its MCP knowledge-graph service was not
  available in this session, so the audit used exhaustive direct source
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
- Wrote `_UK-FLIP-PREP/STOCHASTIC-AUDIT.md`: 87 physical AST/source sites
  (48 stochastic/seeded, 17 deterministic hashes, 22 ambient), with 33 owned
  physical sites mapped to 32 logical draw-ledger rows plus one clock-broker
  record and 54 exact typed exemptions. The report reconciles all seed
  0/42/43/552/578 surfaces.
- Wrote `_UK-FLIP-PREP/UK-F1-CHARTER-DRAFT.md`: a dispatch-gated one-day lane
  that consumes the certified US F1 ABI, closes the 30/12 authority surface,
  requires independent stochastic coverage, and certifies four cold UK graphs
  with f001 national inputs plus a separate resume proof, keeping aggregate
  lane RSS below 15 GiB.
- Cross-checked the Markdown manifests against source and their own arithmetic:
  30 A-rows, 12 N-rows, 48 stochastic rows, 17 hash rows, 22 ambient rows, and
  32 logical ledger rows. `git diff --check` passed.

## Next

- The owner can collect the three files listed below.
- Before dispatch, land and certify the country-neutral US F1 executor/broker
  ABI, N01–N12, the UK executable graph, and the required generalizations of
  existing battery/calibration/publication/spine fields.
- Re-run fetch and the locked dependency sync in a network-enabled environment;
  this analysis did not require or authorize a dataset build.

## Final report

| Measure | Count |
| --- | ---: |
| Coherent authority groups | 30 |
| Physical stochastic/hash/ambient callsites | 87 |
| Logical draw-site ledger rows | 32 |
| Behavior-affecting clock records | 1 |
| New schema field paths required | 12 |

The physical census is 48 stochastic/seeded sites, 17 deterministic hashes,
and 22 ambient sites. Its disposition is 33 ledger/broker-owned physical sites
and 54 typed exemptions. The 12 new paths are additional to required
country-neutral generalization of existing schema fields.

Top risks are:

1. The active `hmrc_spi_income` node declares no runtime 42/43 seed authority,
   while code reuses 42 across three independent families and derives 43.
2. The authored WAS contract describes one seed-0 chain, but runtime resets
   three seed-0 chains and draws a different effective target sequence.
3. The UK walking skeleton compiles no executable producer nodes, and the
   existing physical pipeline ABI is US-specific.
4. Geography conflicts on seed 0 versus the production drivers' 42; the live
   crosswalk path also reads 13 mutable, unauthenticated URLs.
5. Exclusion expiry reads the current UTC date and can change gate results for
   otherwise identical inputs.
6. The ladder gate is absent from `uk/gates.json`, and the current battery,
   calibration, publication, and spine fields still constrain US concepts;
   candidate receipts also hardcode `f100` even for an f001 national input.

Outputs:

- `_UK-FLIP-PREP/AUTHORITY-INVENTORY.md`
- `_UK-FLIP-PREP/STOCHASTIC-AUDIT.md`
- `_UK-FLIP-PREP/UK-F1-CHARTER-DRAFT.md`
