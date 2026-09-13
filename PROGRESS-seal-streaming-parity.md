# Lane journal — seal streaming / selection / scalar-packing parity (2026-09-13)

Session-handoff journal for the `us-seal-streaming-parity-20260913` lane. Per
[CLAUDE.md](CLAUDE.md), the root `PROGRESS.md` is cumulative shared history and
is **not** touched by this lane; this file is the lane's own state/done/next
record and is historical after the branch merges.

## Scope

Three separate, byte-compatible source-only optimizations, from the completed
source review at
`_recovered/scratch-backup/893/codex-takeover-20260912/native-successor-efficiency-result.md`
(read 2026-09-13; the review compared against `aaf31747a`, this branch is on the
reviewed root `47efa3fb4`).

The names in the dispatch packet are descriptive, not literal. The actual
owners, confirmed by inspection before any edit:

| Packet name | Actual owner |
| --- | --- |
| `graph_full_puf_enrichment._frame_physical_seal` | `graph_full_puf_enrichment._population_stamp` (`packages/microcosm-build/src/microcosm/build/us_runtime/graph_full_puf_enrichment.py:147`) |
| `population._series_physical_parts` | `microcosm.graph.population._storage_parts` (`packages/microcosm-graph/src/microcosm/graph/population.py:2739`) |
| `executor._update_scalar` | `microcosm.graph.executor._update_scalar` (`packages/microcosm-graph/src/microcosm/graph/executor.py:408`) |

## Hard constraints held for the whole lane

- No pushes, no publication, no native/archive/store reads, no simulations, no
  engine execution, no production imports or test execution.
- Only this checkout is edited. No delegation.
- No live check removed, no full digest cached, no digested order/length
  framing changed, no source substituted, no final-lifetime check bypassed.
- The prior native run **stopped without a final receipt**; nothing in this lane
  claims its cost or its stopping cause as proven.
- Runtime behaviour of everything below is **untested in this lane** by
  instruction. Parity is argued from source and encoded in tests that root runs.

## State

Inspection complete, implementation starting. This section is updated on every
commit; the "Done" list below is what is actually committed.

## Done

1. Inspected checkout (`47efa3fb4`, clean, `origin/main` +214), repo CLAUDE.md,
   AGENTS.md, CI test-group rules, and the three owners' real contracts.
2. Located and read the completed source review (its stated relative path did
   not resolve; the real path is under `_recovered/scratch-backup/893/`).
3. Established the identity blast radius by reading the code that binds it —
   see "Identity consequences" below.

## Planned commits

4. Candidate 1 — stream `_population_stamp` parts into the unchanged `_digest`.
5. Candidate 2a — `_storage_parts` accepts `slice(None)`; whole-series callers
   inside `microcosm-graph` and the reviewed enrichment site use it; the unused
   `isna()` moved below the masked-storage branch.
6. Candidate 2b — the four remaining whole-series build call sites, split out so
   root can revert the extra pin churn without touching 2a.
7. Candidate 3 — exact-`float` `struct.pack("=d", ...)` fast path in
   `_update_scalar`, NumPy/subclass fallback retained.
8. Parity tests against verbatim copies of the pre-change implementations, plus
   the mutation-sensitivity battery (one test file per candidate).
9. Changelog fragments (one per candidate) and
   `docs/seal-streaming-parity-method.md` (method, limits, benchmark plan).

## Identity consequences (read, not assumed)

- `microcosm.graph.executor` and `microcosm.graph.population` are **not** in
  `_DIRECT_KERNEL_MODULES` / `_QRF_KERNEL_MODULES`
  (`packages/microcosm-build/src/microcosm/build/spec_engine/seeds.py:308,353`),
  so the seven spec-engine identity artifacts do **not** move.
- Both **are** in `graph_implementation_inventory.json`. Their pinned
  `contracts` entries hold only non-stdlib `imports` plus two digests over
  unbound uses and resource accesses (`graph_implementation.py:202-283`).
  `struct` is stdlib and is excluded by the `is_stdlib` branch, so no contract
  entry changes. The runtime `implementation_manifest` module digests do change.
- `graph_full_puf_enrichment.py` is not in that inventory, but it defines
  `FullPufMaskKernel` and `FullPufAttachKernel`, whose `implementation_hash`
  is `source_hash(type(self), ...)` over the defining module's bytes
  (`packages/microcosm-graph/src/microcosm/graph/kernel.py:457`). Those two
  kernels' implementation hashes, node keys and cache identities therefore
  move. That is expected: source identity is not data-digest identity.
- No kernel class is defined in `executor.py` or `population.py`, so no
  kernel implementation hash moves from candidates 2 or 3.

## Next (root, not this lane)

1. Independent review of the frozen file list in `RESULT.md`.
2. Bounded guard: the parity/mutation tests, then the separate-process
   benchmark in `docs/seal-streaming-parity-method.md`.
3. Decide whether to keep or revert candidate 2b (extra call sites, extra
   producer-identity churn, no measured benefit yet).
4. Normal reconstruction and review of the moved producer/cache identities.
