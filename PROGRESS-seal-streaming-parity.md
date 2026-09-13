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

Source patch complete on this branch, source-only checks green, **runtime
untested by instruction**. Nothing was pushed. Root reviews the frozen file
list and runs the bounded guard.

## Done

1. Inspected checkout (`47efa3fb4`, clean, `origin/main` +214), repo CLAUDE.md,
   AGENTS.md, CI test-group rules, and the three owners' real contracts.
2. Located and read the completed source review (its stated relative path did
   not resolve; the real path is under `_recovered/scratch-backup/893/`).
3. Established the identity blast radius by reading the code that binds it —
   see "Identity consequences" below.
4. `11f715993` — candidate 1: stream `_population_stamp` parts into the
   unchanged `_digest` (`chain`, as `_table_stamp` already did).
5. `4633fd0e8` — candidate 2a: `_storage_parts` accepts `slice(None)`;
   `storage_equal`'s whole-series path and the reviewed enrichment
   `_series_parts` use it; the unused `isna()` moved below the masked branch.
6. `c6f727e93` — candidate 2b: the five remaining whole-series build call
   sites, split out so root can revert the extra identity churn on its own.
7. `1a84114d7` — candidate 3: exact-`float` `struct.pack("=d", ...)` fast path
   in `_update_scalar`; NumPy scalars and `float` subclasses keep the array
   path, and no earlier identity check is reordered.
8. Parity tests against verbatim copies of the pre-change implementations, plus
   the mutation battery — five flat test files, each in the CI group it should
   be in (`tools/ci_test_groups.py --verify` exits 0, none `[defaulted]`).
9. One changelog fragment per candidate, and
   `docs/seal-streaming-parity-method.md` (method, limits, benchmark plan).

## Source-only verification performed here

- `ast.parse` of every touched file with `/opt/homebrew/bin/python3 -I -B -S`.
- `ruff format` + `ruff check` (0.15.0) on every touched file: clean.
- `python3 -I -B -S tools/ci_test_groups.py --verify`: exit 0; the five new
  test files land in `fast/rest` and in `engine/us-am` (four) and
  `engine/us-not` (one); none appears under `[defaulted]`.
- A stdlib-only AST replication of `graph_implementation._dependency_details`
  confirms the pinned `contracts` entries for `microcosm.graph/executor.py` and
  `microcosm.graph/population.py` still match: `struct` is excluded as stdlib,
  and neither module contains any `_RESOURCE_CALLS` name.

No test, import, build, simulation, native/archive/store read or benchmark was
executed in this lane.

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
