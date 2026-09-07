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
- [x] Interpretation resource JSON + versioned JSON Schema
- [x] Source-only validator + shared growth-refusal guard
- [x] Source/invented test proof — 136 tests, all passing
- [x] Named-document authenticity run under the pinned bounded runtime
- [ ] Reports at `/private/tmp/us-puf-period-interpretation-REPORT.{md,json}`

## What landed

| Artifact | Path |
| --- | --- |
| Resource | `packages/microcosm-build/src/microcosm/build/us_source_interpretation/puf_2015_statistical_period_interpretation.json` |
| Schema | `.../us_source_interpretation/puf_2015_statistical_period_interpretation.schema.json` |
| Validator + guard | `packages/microcosm-build/src/microcosm/build/puf_2015_statistical_period_interpretation.py` |
| Tests | `packages/microcosm-build/tests/test_us_puf_2015_statistical_period_interpretation.py` |

The module is stdlib-only and sits directly under `microcosm/build/`, not under
`us_runtime`, whose package initialization eagerly imports the whole US stage
graph. It is also loadable straight from its file with no package import at
all, which the document-authenticity run exercises: that run imported no
numpy, pandas, rules engine, frame, graph or calibrate module.

Three guarantees are structural rather than asserted in data:
`GrowthAdmission.admitted` is a read-only property returning `False`;
`DocumentaryVerification.verified` is derived from re-authenticated bytes; and
a resource that serializes a verification flag is refused outright.

## Verification evidence

Pinned runtime `.../microcosm-us-launch-current-main-20260905/.venv/bin/python`
(3.14.4, sha256 `bf4ea262…`), every parent and child under
`-I -B -S -X pycache_prefix=<fresh absent absolute>`, explicit source roots and
plain dependency site-packages with no `.pth` processing.

`RLIMIT_AS` is **not settable on this host** — measured, not assumed:
`setrlimit` returns "current limit exceeds maximum limit". CPU is therefore
capped by `RLIMIT_CPU` (kernel-enforced on macOS) and wall time and RSS by a
supervisor that polls and SIGKILLs the child process group. No cap is claimed
that is not applied.

- Tests: 136 passed, 11.7s child CPU, 13.5s wall, 0.82 GiB peak RSS, one thread.
- Loaded-source git-byte proof: 125 of 125 loaded worktree source files match
  their `HEAD` blob SHA-1 exactly, including the module and the test file.
- Document authenticity: 20 pin checks pass — 2 PDFs, 2 retained texts, 14
  page-text hashes recomputed under the declared method, 2 renders — plus 4
  side pins (raw source definition, historical extraction receipt, independent
  reproduction, historical report). A one-substring mutation control fails
  closed, and growth stays refused with verified pins and with a claimed review.

## Next

Write the reports, then hand to root for source review before any integration.
No push, PR, merge or deploy from this branch.
