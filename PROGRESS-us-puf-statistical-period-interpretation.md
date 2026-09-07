# PROGRESS — PUF 2015 statistical-period interpretation resource

Session journal for the source-only implementation of the adjudicated PUF
statistical reference period. Accurate when written; check git for current
truth (see CLAUDE.md, "Root journals are history, not state").

## Scope

Documentary interpretation only. This branch adds a versioned interpretation
resource, its schema, a source-only validator and a growth-refusal guard. It
carries **zero growth, scientific or release authority**: the first schema
revision refuses growth unconditionally for every convention state.

Governing plan (exact revision, hash-verified this session):

- `/Users/maxghenis/architecture-reviews/microcosm-20260904/us-puf-statistical-period-adjudication-plan-20260907.md`
  sha256 `2138216029d6e341a054ed785e692a7738268291a03a25812250ea399247ec6d`
- companion `us-puf-statistical-period-adjudication-evidence-20260907.json`
  sha256 `ceadc35518334cb995dd65e89537e82f7591e10ab7080b5d7a3ad12147defdf0`
- durable gate `20260907-024937-plan-d77cb2b9` COMPLETE (root + peer agree on
  this exact revision).

## Parent selection

Branched from `origin/main` `c1b8324183819cf91511c002bf724a2676524e87` — the
only canonical remote is `origin` (PolicyEngine/microcosm). The read-only
reference worktree `microcosm-us-origin-cap-puf-integration-20260907`
(HEAD `669edf780d4b45e09eb4e38a9e458798b04352d2`, clean) sits 310 commits
ahead of `origin/main` and is **not** an ancestor of it; adopting it would
import hundreds of unrelated accepted development commits. The interpretation
resource binds the predecessor raw source definition by *identity and hash*,
never by import, so no raw-definition implementation dependency requires that
parent. No existing checkout is edited, reset, rebased or cleaned.

## State

- [x] Verified plan / evidence / source-definition / pinned-runtime hashes
- [x] Fresh worktree from `origin/main`, PROGRESS journal seeded
- [ ] Interpretation resource JSON + schema
- [ ] Source-only validator + growth-refusal guard
- [ ] Source/invented test proof
- [ ] Named-document authenticity run under the pinned bounded runtime
- [ ] Reports at `/private/tmp/us-puf-period-interpretation-REPORT.{md,json}`

## Next

Author the resource and validator under `microcosm/build/` (outside eager
`us_runtime` initialization), stdlib-only, with caller-supplied byte
resolvers and no hardcoded absolute paths in the package.
