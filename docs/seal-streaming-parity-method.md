# Seal streaming, whole-series selection and scalar packing: method and limits

Three bounded source-only optimizations to in-process seals, taken from a
completed source review of the stopped native-successor run. Each is separately
committed and separately revertible. Every one of them is required to be
**byte-compatible**: the digested parts, their order, their length framing and
their bytes are unchanged, and only the work done to produce them differs.

This note records what was changed, why the change is byte-compatible, what has
**not** been established, and the bounded comparison and benchmark that would
establish the performance claims. Nothing here reports a measurement.

## What changed

| # | Owner | Change |
| --- | --- | --- |
| 1 | `microcosm.build.us_runtime.graph_full_puf_enrichment._population_stamp` | Stream the parts into the unchanged `_digest` through `itertools.chain` instead of expanding them into one tuple first. |
| 2 | `microcosm.graph.population._storage_parts` and its whole-series callers | Accept `slice(None)` as the whole-series selector; move the `isna()` call below the masked-storage branch, which never used it. |
| 3 | `microcosm.graph.executor._update_scalar` | Pack an exact Python `float` with `struct.pack("=d", ...)` instead of a one-element `float64` array. |

Change 2 landed as two commits: the helper plus the two reviewed call sites
(`storage_equal`'s whole-series path and the full-PUF `_series_parts`), then the
five remaining US whole-series seal sites (`survey_atomic_geography`,
`population_input_coverage`, `survey_origin_budget`,
`current_survey_predictors`, `puf55_survey_recipients`). The second commit can
be reverted on its own if its extra producer-identity churn is not wanted.

## Why each is byte-compatible

**1 — streaming.** `_digest` already consumes any iterable of parts one at a
time, updating the hash with an 8-byte little-endian length prefix and then the
part. Feeding it a `chain` of the same sub-iterables, in the same order,
presents the same sequence of `bytes` objects. Nothing is reordered, merged,
dropped or cached; only the peak number of simultaneously retained encoded
parts changes. `_table_stamp` in the same module already streamed this way.

**2 — whole-series selection.** For a row-aligned all-True mask `m` and
`slice(None)`, `x[m]` is a copy of every row in row order and `x[:]` is a view
of every row in the same order. Every byte payload in `_storage_parts` is taken
either through `np.ascontiguousarray(...).tobytes()`, which preserves element
order, dtype and byte order and only removes striding, or by an in-order walk
(the `StringDtype` and object branches). So the emitted `(values, nulls)` pair
is identical for the two selector forms. Subset masks are untouched.

The moved `isna()` is only a removal of dead work: the masked-storage branch
returns `_data` and `_mask` and never reads `nulls`. A wrong-length selector
still raises `IndexError` in that branch, now from `data[selected]` rather than
from the discarded `isna()` indexing.

Every converted site passed a selector of exactly its own series' length:
`np.ones(len(series))` at four of them, and `np.ones(len(table))` at
`current_survey_predictors`, where every sealed series is exactly `len(table)`
rows (the index as a Series, and each column). No site's selected rows change.

**3 — exact-float packing.** `struct.pack("=d", v)` writes the native-order
8-byte IEEE-754 double; `np.asarray([v], dtype=np.float64).tobytes()` writes the
same native-order 8 bytes. Both take the value straight from the Python float's
C double, so the sign bit, infinities, subnormals and NaN payloads are carried
identically. The branch tests `type(value) is float` exactly, so `np.floating`
scalars and `float` subclasses keep the array path unchanged, and it sits
immediately before the existing floating branch, so no earlier identity check
(`pd.NA`, `pd.NaT`, `None`) is reordered.

**This byte parity is a prerequisite, not an established result.** It is
asserted directly — `struct.pack("=d", v) == np.asarray([v], np.float64)
.tobytes()` for every special value — by
`packages/microcosm-graph/tests/test_graph_executor_scalar_float.py`, so a
platform where it does not hold fails that test rather than silently shipping.

## What the tests cover

| File | Covers |
| --- | --- |
| `packages/microcosm-build/tests/test_us_graph_full_puf_seal_stream.py` | Streamed parts compared part-for-part against a verbatim copy of the pre-change tuple, over empty, labelled-index, reversed-row, weightless and wide-object-strata populations; twenty visible and hidden mutations must move both stamps. |
| `packages/microcosm-graph/tests/test_graph_storage_parts_whole_series.py` | Both selector forms against a verbatim copy of the pre-change `_storage_parts`, over empty, contiguous, strided, reversed, frame-sliced, non-native-endian, dense, masked, string and object series, with signed zero, subnormals, infinities and distinct NaN payloads; subset masks; hidden `_data`/`_mask` mutations; `storage_equal`'s contract; fail-closed paths. |
| `packages/microcosm-build/tests/test_us_graph_full_puf_seal_selection.py` | `_series_parts`, `_axis_parts` and `_table_stamp` against verbatim pre-change copies, plus table-level mutations. |
| `packages/microcosm-build/tests/test_us_whole_series_selection_sites.py` | Two of the five converted seals against verbatim pre-change copies; a static guard over all five that fails if any call rebuilds an all-True selector. |
| `packages/microcosm-graph/tests/test_graph_executor_scalar_float.py` | Emitted chunks, not just digests, against a verbatim copy of the pre-change `_update_scalar`, for every special float, numpy float16/32/64, a float subclass and every other scalar branch; object and dense arrays end to end. |

## Limits — what is not established here

- **No runtime measurement of any kind was taken.** No test, import, build,
  simulation or benchmark was executed in the lane that wrote this. Every
  performance statement below is a proposal.
- **The prior native run stopped without a final receipt.** Neither its cost
  nor its stopping cause is established, and nothing here claims either. These
  three changes are not a diagnosis of that run.
- **Data-digest parity does not preserve implementation identity.** Source
  hashing binds executable bytes, so the affected producer and cache identities
  move and need normal reconstruction and review:
  - `graph_full_puf_enrichment.py` defines `FullPufMaskKernel` and
    `FullPufAttachKernel`, whose `implementation_hash` is `source_hash` over
    that module's bytes, so their node keys and cache entries change.
  - `microcosm.graph/executor.py` and `microcosm.graph/population.py` are in
    `graph_implementation_inventory.json`, so their module digests inside
    `implementation_manifest` change. Their pinned dependency `contracts` do
    not: those record only non-stdlib imports plus digests over unbound uses
    and resource accesses, and `struct` is stdlib.
  - Neither graph module is in `_DIRECT_KERNEL_MODULES` or
    `_QRF_KERNEL_MODULES`, so the spec-engine seed identities do not move.
- **Nothing here weakens a live check.** No guard, acceptance boundary or
  final-lifetime check was removed, no digest was cached, no source was
  substituted.

## Bounded comparison and benchmark plan

Run only after the parity tests pass. Measure each candidate **separately**, in
**fresh processes**, with numeric thread pools pinned to one, and take baseline
and candidate from the same process-launch discipline. The script below defines
the pre-change implementations inline, so no checkout switching is needed and
both variants run against identical invented inputs.

Invented inputs only: a donor-scale object strata column at the 207,692 rows
the source review named, a float-heavy scalar workload, and a masked/string/
object column mix. No genuine microdata, no store, no archive, no engine.

### Finite resource limits

| Limit | Value | Enforced by |
| --- | --- | --- |
| Rows | ≤ 207,692 | `--rows` (script refuses more) |
| Repeats | 3 per variant | `--repeats` (script refuses more than 5) |
| CPU seconds per process | 300 | `ulimit -t 300` |
| Peak RSS | 4 GiB | script aborts above `--max-rss-mb` |
| Processes | 6 (3 candidates × 2 variants), sequential | the runner loop |
| Threads | 1 | `OMP/OPENBLAS/MKL/NUMEXPR/VECLIB` env vars |

### Proposed commands

```bash
# One fresh process per (candidate, variant). Sequential, never concurrent.
for candidate in stream selection scalar; do
  for variant in baseline candidate; do
    ( ulimit -t 300
      OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
      NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
      uv run python bench_seal_parity.py \
        --candidate "$candidate" --variant "$variant" \
        --rows 207692 --repeats 3 --max-rss-mb 4096 )
  done
done
```

Report, per (candidate, variant): process CPU seconds, wall seconds, peak RSS,
and the invariant digest the run produced. **The two variants' digests must be
equal**; a run whose digests differ is a parity failure, not a slow result.

### The benchmark script

Not committed as a tool and not executed here. Save as `bench_seal_parity.py`
outside the package tree.

```python
"""Invented-data benchmark for three byte-compatible seal optimizations.

Baseline implementations are verbatim copies of the pre-change bodies, so one
process measures one (candidate, variant) pair against identical inputs.
No genuine data, no store, no archive, no engine.
"""

import argparse
import hashlib
import itertools
import json
import resource
import struct
import sys
import time

import numpy as np
import pandas as pd

from microcosm.build.us_runtime import graph_full_puf_enrichment as placement
from microcosm.graph import population as population_ops
from microcosm.graph.executor import _update_scalar


def object_strata(rows):
    array = np.empty(rows, dtype=object)
    for position in range(rows):
        array[position] = f"stratum_{position % 51:02d}_{position}"
    return pd.Series(array)


def mixed_frame_columns(rows):
    return {
        "amount": pd.Series(np.linspace(-1e6, 1e6, rows)),
        "count": pd.Series(np.arange(rows, dtype=np.int64)),
        "nullable": pd.Series(
            pd.arrays.IntegerArray(
                np.arange(rows, dtype=np.int64),
                np.arange(rows) % 7 == 0,
            )
        ),
        "text": pd.Series(
            pd.array(
                [f"v{position}" for position in range(rows)],
                dtype=pd.StringDtype(storage="python", na_value=pd.NA),
            )
        ),
    }


def baseline_series_parts(series):
    yield repr(series.dtype).encode()
    if pd.api.types.is_object_dtype(series.dtype):
        from microcosm.graph import store as store_ops

        yield from (store_ops._encode_object_scalar(v) for v in series)
    else:
        yield from population_ops._storage_parts(
            series, np.ones(len(series), dtype=np.bool_)
        )


def baseline_update_scalar(digest, value):
    if isinstance(value, (float, np.floating)):
        payload = b"f" + np.asarray([value], dtype=np.float64).tobytes()
    else:  # the benchmark workload is float-only by construction
        raise TypeError(type(value).__name__)
    digest.update(len(payload).to_bytes(8, "little"))
    digest.update(payload)


def run_stream(variant, rows):
    """Retention of encoded parts: tuple expansion vs streamed chain."""

    strata = object_strata(rows)
    parts = placement._series_parts(strata)
    if variant == "baseline":
        return placement._digest(tuple(parts))
    return placement._digest(itertools.chain(parts))


def run_selection(variant, rows):
    digest = hashlib.sha256()
    for series in mixed_frame_columns(rows).values():
        if variant == "baseline":
            selected = np.ones(len(series), dtype=np.bool_)
        else:
            selected = slice(None)
        for part in population_ops._storage_parts(series, selected):
            digest.update(len(part).to_bytes(8, "little"))
            digest.update(part)
    return digest.hexdigest()


def run_scalar(variant, rows):
    values = np.linspace(-1e6, 1e6, rows).tolist()  # exact Python floats
    values += [0.0, -0.0, float("inf"), float("-inf"), 5e-324]
    digest = hashlib.sha256()
    update = _update_scalar if variant == "candidate" else baseline_update_scalar
    for value in values:
        update(digest, value)
    return digest.hexdigest()


CANDIDATES = {"stream": run_stream, "selection": run_selection, "scalar": run_scalar}


def peak_rss_mb():
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return usage / (1024 * 1024) if sys.platform == "darwin" else usage / 1024


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", choices=sorted(CANDIDATES), required=True)
    parser.add_argument("--variant", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--rows", type=int, default=207_692)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-rss-mb", type=float, default=4096.0)
    args = parser.parse_args()
    if not 1 <= args.rows <= 207_692:
        raise SystemExit("rows outside the reviewed bound")
    if not 1 <= args.repeats <= 5:
        raise SystemExit("repeats outside the reviewed bound")

    run = CANDIDATES[args.candidate]
    digests, cpu, wall = set(), [], []
    for _ in range(args.repeats):
        started_cpu, started_wall = time.process_time(), time.perf_counter()
        digests.add(run(args.variant, args.rows))
        cpu.append(time.process_time() - started_cpu)
        wall.append(time.perf_counter() - started_wall)
        if peak_rss_mb() > args.max_rss_mb:
            raise SystemExit(f"peak RSS above the {args.max_rss_mb} MiB limit")

    print(
        json.dumps(
            {
                "candidate": args.candidate,
                "variant": args.variant,
                "rows": args.rows,
                "digests": sorted(digests),
                "cpu_seconds": cpu,
                "wall_seconds": wall,
                "peak_rss_mb": peak_rss_mb(),
            }
        )
    )


if __name__ == "__main__":
    main()
```

### What the measurement would and would not establish

It would establish, for these invented inputs on one platform, the CPU, wall
and peak-RSS difference between the pre-change and post-change bodies of each
candidate, separately.

It would **not** establish anything about the stopped native run, about any
end-to-end build, or about seal counts elsewhere in the pipeline. Counting
`_live` scans, canonical serializations, full-frame signatures and checksum
calls — which the source review lists as the substantial remaining costs — is a
separate exercise from this micro-benchmark and is not attempted here.
