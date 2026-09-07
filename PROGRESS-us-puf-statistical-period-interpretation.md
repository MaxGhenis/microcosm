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
- [x] Source/invented test proof — 148 tests, all passing
- [x] Named-document authenticity run under the pinned bounded runtime
- [x] Adversarial clause audit: 235 verdicts, 232 satisfied, 3 claimed gaps
- [x] Reports at `/private/tmp/us-puf-period-interpretation-REPORT.{md,json}`

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

- Tests: 148 passed, 12.3s child CPU, 12.4s wall, 0.76 GiB peak RSS, one thread.
- Loaded-source git-byte proof: 125 of 125 loaded worktree source files match
  their `HEAD` blob SHA-1 exactly, including the module and the test file.
- Document authenticity: 20 pin checks pass — 2 PDFs, 2 retained texts, 14
  page-text hashes recomputed under the declared method, 2 renders — plus 5
  side pins (raw source definition, historical extraction receipt, independent
  reproduction, prior URL-match receipt, historical report). A one-substring
  mutation control fails closed, and growth stays refused with verified pins
  and with a claimed review. That run imported no numpy, pandas, rules engine,
  frame, graph or calibrate module at all.

## Adversarial clause audit

The adjudication's plan and companion evidence were decomposed into 235 atomic
normative clauses and audited against the committed artifacts, with each
claimed gap put to three independent refuters. 232 satisfied, 3 claimed gaps,
all 3 refuted 3/3. Two of those refutations were not accepted at face value and
were fixed anyway in `93b5fb49`:

- The plan enumerates **blurring** among the four things PDF page 4 describes
  and requires the later audit to "State blurring and aggregate-record
  treatment". The resource had recorded the other three treatments and dropped
  blurring. It now carries all of them in the publisher's own wording, the
  validator refuses a resource that drops one, and the deferred audit protocol
  carries the requirement verbatim.
- The resource claimed the public archive copy had been byte-matched in a
  pinned URL-check receipt without pinning that receipt. It now binds the
  receipt (`34d5fa33…`, 649 bytes) together with the document identity it
  attests, and the validator refuses an attestation that disagrees with the
  document pin it names. The authenticity run re-authenticates it as a fifth
  side pin.

Two ride-along paths the audit noted are also closed: unknown keys inside the
`convention` block are refused by both the schema and the validator, and the
page-level hash-mismatch branch of documentary verification — previously
unexercised — now has a test that keeps the container authentic while a page
pin disagrees.

## Next

Root reviews the source before any integration. Nothing was pushed; there is no
PR, no merge, no deploy, and no release or growth authority anywhere in this
branch. The later source-period audit and the mandatory convention sensitivity
comparison remain described, unauthorized and uncalculated.

One packaging check could not be run locally: hatchling is absent from the
pinned environment and dependency installs are out of scope, so wheel inclusion
of `us_source_interpretation/*.json` was not built and confirmed here. It
follows the same shape as the existing `src/microcosm/build/us/*.json` data
directory, and the repo's `wheels` lane runs the suite against installed
wheels, where `test_packaged_resource_states_the_adjudicated_period` would fail
loudly if the resource were omitted.

---

# Successor session — root/independent review fixes (2026-09-07)

Everything above this line is the first session's journal, historical as
written. This section is the successor session's own state; check git for
current truth.

## Mandate

Continue from clean `db0ed2859440347a4ef1e198e3af1d4bdb74bdb0`. The original
source, report and proofs stay frozen — this session fixes the two actionable
P2 findings of the independent review and nothing else.

Governing review (hash-verified this session):

- `/Users/maxghenis/architecture-reviews/microcosm-20260904/us-puf-period-interpretation-independent-review-final-20260907.json`
  sha256 `07daf3be573cd11c60367a401f301fe1820affb6c84d489831ae64b060834b9c`
  — matches the mandate's pin exactly.
- companion markdown `…-final-20260907.md`
  sha256 `1b19fb70ab1c25e2d491baea80364c1d5838a06fa919fe3dd8abb86799e03921`
- the first session's governing plan is unchanged:
  `us-puf-statistical-period-adjudication-plan-20260907.md` sha256
  `2138216029d6e341a054ed785e692a7738268291a03a25812250ea399247ec6d`
  — re-verified on disk this session.

Verdict under repair: REQUEST_CHANGES, two P2 findings, growth refusal already
unconditional and not in question.

- **P2A** `documentary_display` trusts any `DocumentaryVerification`. The
  verdict binds neither the resource it was issued for nor the complete pin
  roster, and the class is publicly constructible, so a verdict issued for
  interpretation A authenticates a changed interpretation B, and a single
  hand-built successful `PinCheck` authenticates anything.
- **P2B** `load_interpretation` validates every other block but omits
  `disagreement_record`, so the published schema's requirement that the
  code-page conflict stay `unresolved_and_recorded_verbatim` with
  `corrected: false` is unenforced at the actual loader.

## Scope held from the prior session

Unchanged and re-asserted: growth refused unconditionally for every input;
the convention stays `proposed` with a null review; no PUF, price, factor,
target, store, H5 or ZIP data is read; no opaque price acceptance; no B19001,
B25003, derived or shared-holdout use; the old source period, dataset and
recipes are untouched; no external publication, push, PR, merge, cloud call,
message or dependency install. Named public documentary files retained under
prior authority may be rehashed only if needed — no repeated full PDF
extraction.

## State

- [x] Review `.md` + `.json` read; JSON sha256 matches the mandate pin
- [x] Successor journal seeded and committed
- [x] Red-before proof reproducing both findings at `db0ed285`
- [ ] P2A fix — verifier-issued, resource-and-roster-bound verdict
- [ ] P2B fix — loader enforcement of the revision-1 conflict fields
- [ ] Actual-source invented tests for both
- [ ] Green-after proof, same harness
- [ ] Existing interpretation suite re-run once
- [ ] Frozen report at `/private/tmp/us-puf-period-root-review-fixes-REPORT.{md,json}`
- [ ] Root/independent peer review of the final source

## Red-before proof

A single probe witnesses both findings and is re-run unchanged after the fix,
so the same bytes serve as both proofs. It records what the actual source does
and, per witness, what the repaired source must do; `all_expected_after_fix`
is the whole verdict.

- probe `/private/tmp/us-puf-period-root-review-fixes-probe.py`
  sha256 `71c0e00d0b0bb42a9b6a3df0e5a243618b343d8321b186ba11c04f6b6e289854`
- red witness `/private/tmp/us-puf-period-root-review-fixes-red.json`
  sha256 `c845102e5fde782ff0be5bdeb883f95731a7a3ab99075d222b513025680a6b89`
- supervisor receipt `…-red-receipt.json`
  sha256 `ee04df4ae75af3a6ca548caa603916cd9f86b68a1f99c9f54a28662c0e3adee5`

Runtime: pinned 3.14.4 (`bf4ea262…`) under `-I -B -S` with a fresh absent
absolute `pycache_prefix`, 180s `RLIMIT_CPU`, 240s wall and 2 GiB RSS enforced
by the same supervisor the first session used, plus a 20 ms in-process RSS
watchdog. Child exit 0, 0.25s CPU, 0.31s wall, 36 MiB peak RSS, nothing killed.
No cap was raised. `RLIMIT_AS` remains unsettable on this host, as measured
before.

Loaded-source Git proof: the module, the test file and the packaged resource
JSON were read from the worktree and each matched **both** the current `HEAD`
blob and the reviewed `db0ed285` blob byte for byte. The probe imports no
project package at all — the module is loaded straight from its file, so the
packaged resource is read as proved worktree bytes rather than through
`importlib.resources`.

`all_expected_after_fix: false`. Eleven witnesses fail, reproducing both
findings against the reviewed bytes:

- **P2A** a verdict issued for A authenticates a changed PDF pin, a changed
  page pin, a changed render pin and a changed resource identity; the reuse is
  symmetric. A hand-built single passing `PinCheck`, a copy of a genuine
  verdict's public checks, and a one-check subset of a genuine roster all
  authenticate. An empty verdict constructs. There is no resolver-backed
  display path.
- **P2B** all fifteen conflict mutations load without a single refusal —
  `corrected: true`, `status: resolved_by_caller`, `status: unknown`, a missing
  status, every missing required conflict field, a missing sub-block, and both
  `page3_page4_edition_difference` constants flipped true.

## Next

Fix P2A, then P2B, then extend the actual-source invented tests, then re-run
this probe unchanged and the existing interpretation suite once.
