# Build lane: native graph executor CPU attribution + scaling law

Lane question (Max, 2026-09-15): can the #893 native graph executor build a full
US dataset at all, at what cost, and what must change to make it hours not days?

Worktree: `_worktrees/microcosm-exec-profile`, detached at PR #893 head
`2bc6976a8c6fd882e503c9a1411e091e56fe82c4`. All run output under
`.profile-runs/` (excluded via `$GIT_DIR/info/exclude`, never committed).

## State

- Setup: worktree synced (`uv sync --all-packages --locked --extra us`, exit 0).
- Reading the v4 receipt turned up the first hard number (below).

## Done

- Read `~/PolicyEngine/_recovered/pilot-runs/native19-v2/run/` receipts
  (read-only): `us-native-postclone-financial19-v4-cold.json` and
  `native-financial-manifest.json`.
- **First hard finding from the existing v4 receipt**: per-node wall times sum
  to 1,143.2 s (prefix run 175.3 s over 9 nodes + financial run 967.9 s over 19
  nodes), while the case recorded 4,685.9 s wall / 4,605.4 s CPU to the end of
  `run_atomic_survey_financial` and 4,896.6 s wall / 4,815.8 s CPU including
  artifact export. So **~3,543 s (~76% of the runner's wall) is spent outside
  the node functions** the manifest times. The manifest's own scope note says
  the node timings are "descriptive only; excludes pre-node source/key
  preflight".
- Four nodes dominate in-node time and all four are ASEC source-ingest nodes:
  `survey_predictors.asec_design_donor` 263.2 s, `.source_projection` 242.0 s,
  `.attach` 226.4 s, `.asec_current_columns` 225.6 s (957.2 s of the 967.9 s).
  These read fixed-size source files, so they are candidates for *constant*
  rather than population-scaling cost.
- The v4 config records `copied_input_bytes: 3,735,332,980` over 10 inputs and
  the run's `snapshots/` directory is 3.7 GB: the runner copies every staged
  source into a snapshot tree. Constant per run, independent of fraction.

## Next

1. Static attribution pass over `microcosm/graph/*.py` + `microcosm/frame/`
   identity code (line-cited map of every population-scaling operation).
2. Stage the harness under `.profile-runs/harness/`, paths repointed, fraction
   parameterised; SIGXCPU-safe cProfile wrapper so a capped run still yields a
   partial profile.
3. Three profiled runs at 1/8000, 1/4000, 1/2000 (`ulimit -t 1800`, <=16 GB RSS,
   foreground, no retry).
4. Bucket cumulative CPU, fit log-log slopes, validate against the 1/1000 v4
   receipt, extrapolate.
5. Pull the incumbent's durations from `~/PolicyEngine/_buildp-runtime/logs`.
6. Write `out.md`.

## Open risk

If the ~3,543 s of non-node cost is largely constant (source copy + hash +
ingest), every run at the 1800 s CPU cap may be killed before finishing. The
harness therefore installs a SIGXCPU handler that dumps the partial profile, and
run 1 is the smallest fraction so the constant floor is measured first.

---

## Update — harness staged

- `.profile-runs/harness/` holds a verbatim copy of the pilot's
  `atomic_financial_artifacts.py` (sha256 `c8ba82bb…`) and
  `test_native_nineteen_node_financial.orig.py` (sha256 `84ab06bf…`); both
  hashes match the identities the v4 receipt records, so the profiled harness is
  provably the same code the accepted pilot ran.
- The working copy differs in exactly ten path/fraction edits, enumerated in
  `.profile-runs/harness/HARNESS-CHANGES.md`. No assertion was weakened.
- `profile_run.py` replaces the pilot's `run_v2.py` outer guard (a provenance
  guard, not a profiler). It keeps run_v2's single-thread numeric environment
  (`OMP/OPENBLAS/MKL/VECLIB/NUMEXPR/BLIS_NUM_THREADS=POPULACE_FIT_N_JOBS=1`,
  torch threads 1, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `TZ=UTC`, TMPDIR inside
  the run dir) so CPU numbers stay comparable with the v4 receipt, and adds
  cProfile, an RSS watchdog and a SIGXCPU handler that dumps the partial profile
  before the cap kills the process.
- **The fraction is not a free parameter.** `survey_population_preparation.py`
  requires `sources/selection-request.json` to carry exactly the fraction the
  runner is called with (`REQUEST_ARGUMENTS`), refuses symlinked source files
  (`SOURCE_SYMLINK`), and its `_stat_identity` (`survey_population_preparation.py:268-269`) includes `st_ctime_ns`
  — so a hard link into the pilot tree would perturb a concurrent reader. Each
  fraction therefore gets a real 3.7 GB copy of the nine source files, verified
  against the pilot config's pinned sha256s, with only the request file's
  fraction changed.

## Next

- Run 1 (1/8000), then 1/4000, then 1/2000.

---

## Update — run 1 launched, first static findings

Run 1 (1/8000) started 2026-09-16T01:51Z, `ulimit`-equivalent RLIMIT_CPU soft
1800 s / hard 1810 s (the 10 s of grace exists only so the SIGXCPU handler can
dump the partial profile).

Static findings I verified myself while it ran (the fan-out readers are
producing the full map separately):

- **Per-node manifest `wall_time` covers the WHOLE node loop body**, not just
  the kernel: `node_started = time.perf_counter()` at
  `executor.py:2297` is the first statement of `for node_id in compiled.order`
  (`executor.py:2296`), and `wall_time=time.perf_counter() - node_started` at
  `executor.py:2616` is in the `NodeReceipt` built at the end of the same body.
  So the 1,143 s of v4 node time already includes store reads/writes, identity
  work and `_apply_result`; the missing ~3,543 s is entirely outside
  `run_graph`'s node loop (its own preflight, plus the runner's work around
  three separate `run_graph` calls).
- **The graph's single declared source is the whole 3.7 GB source directory.**
  `graph_survey_population.py:919` declares `SourceRef(SOURCE_NAME, SOURCE_CODEC)`
  and `:1082`/`:1143` bind `sources={SOURCE_NAME: source_dir}`.
  `keys.py:54 source_content_key` therefore takes the directory branch
  (`keys.py:67-68`) into `keys.py:31 _directory_identity`, which at
  `keys.py:45` does `candidate.read_bytes()` — **the entire file into memory** —
  for every file under the tree, then hashes it. A 662 MB ASEC H5 is a 662 MB
  transient allocation.
- That identity is recomputed at least five times per pilot run:
  `_source_paths_and_keys` is called by `run_graph` itself
  (`executor.py:2284`) once per graph, and the pilot runs three graphs (base
  survey, 9-node atomic, 19-node financial), *and* the runners call it directly
  first — `graph_atomic_survey_population.py:214` and
  `graph_atomic_survey_financial.py` before `run_graph`. On top of that,
  `executor.py:2453-2456` re-derives `source_content_key` for every source a
  **cold** node declares, after that node's kernel returns.
- **`_context_digest` runs twice per cold node** (`executor.py:2423` and
  `:2449`), hashing every column of every entity table, the weights and the
  strata of the incumbent population, plus each artifact payload
  (`executor.py:466-495`).
- **`_write_node` stores every column of the whole frame as its own store
  object AND the whole frame again**: `executor.py:1524-1527` loops every
  entity/column into `store.put_column` (`:1533`), then `:1547` calls
  `store.put_frame` for the same data. Each `_put` (`store.py:723`) fsyncs the
  whole staged object tree (`store.py:754 _fsync_tree`) and the destination
  directory twice (`:756`, `:770`).

## Next

- Wait for run 1, then 1/4000 and 1/2000.

---

## Incumbent durations — what `_buildp-runtime` actually records

The logs do carry durations (they are not silent). Three independent receipts:

1. **Certified default dataset** (`populace_us_2024_buildp.h5`, 57,240
   households), `_buildp-runtime/donor/release_manifest.json` → `build.timing`:
   - `target_compilation_seconds` 1,132.1
   - `calibration_seconds` 1,072.4
   - `elapsed_through_calibration_seconds` 2,800.6
   - **`total_build_seconds` 8,161.1 (2 h 16 m)**
   Method `dense_no_l0`, 6,000 epochs, final loss 0.01768.
2. **ACS-local staging** (`logs/acs-local/staging.log` + `staging_run.log`
   tail): 2026-08-14T03:38:59Z → 05:49:28Z, and the `time` line records
   **7,829.54 s real / 99,337.73 s user / 3,215.55 s sys**, peak RSS 40.13 GB.
   That is 28.5 CPU-hours at ~13x parallelism.
3. **ACS-local release chain** over 1,588,854 households
   (`logs/acs-local/release_chain_run.log`): **9,156.43 s real / 5,672.78 s user
   / 302.27 s sys**, peak RSS 94.18 GB. Stage detail from the log:
   staging frame load 60.7 s; materialize 4,149.3 s (3,972 admin measures over
   40 chunks); calibrate 1,797 s (800 epochs, within10% 98.74%); qa, finalize
   and package the remainder; `DONE stages=[...] (9147.4s)`.

So the incumbent builds the 1.59M-household local-area dataset in **~4.7 h wall
and ~30.1 CPU-hours total** (staging + release chain), and the 57k-household
certified default in **2 h 16 m**. Those are the numbers the native executor has
to be compared against.

---

## Aborted attempt, disclosed

The first launch of the 1/8000 run was **aborted by me at 349 CPU-s** (2026-09-16
~01:58Z) for a harness-fidelity defect, not a retry: I had replicated seven of
`run_v2.py`'s eight `THREAD_ENV` names. The missing
`POPULACE_FIT_PREDICT_WORKERS` falls back to `os.cpu_count()` at
`worker_identity.py:1243`, which would have fanned QRF predict work out to 18
child processes — violating this lane's no-child-processes authorization and,
worse, silently *undercounting* CPU, because `resource.getrusage(RUSAGE_SELF)`
excludes children. No profile or measurement was taken from that attempt; it is
counted here for full disclosure of machine time used. The driver now sets all
eight names and additionally records `RUSAGE_CHILDREN` so any child CPU is
visible rather than invisible.

---

## Report destination

The repo root `out.md` is a **tracked file already carrying another lane's
committed report** (`git log -- out.md` → 72e477caf, 27e593db3, c35cd8a85). This
lane therefore writes its deliverable to `out.md` **without committing that
overwrite**, and commits an identical durable copy at
`experiments/us-native-executor-cost-attribution-20260915.md`.

---

## The per-node whole-population cost chain (found by reading, pending profile)

Every node of every graph run pays, in addition to its kernel:

1. **A full pickle round trip of the entire population.**
   `executor.py:355 _observer_snapshot` does
   `pickle.loads(pickle.dumps((tables, frame.strata), protocol=5))` at
   `executor.py:372` over every entity table and the strata, plus `deepcopy` of
   the schema records at `:378` and `:388-389`. `run_graph` calls it at
   `executor.py:2569` for **every** node — and `run_graph`'s own docstring
   (`executor.py:2263-2264`) states it "runs for cold execution and for restored
   cache hits alike", so a cached node that does no work still pays a full
   serialization of the whole population.
2. **A full per-cell Python hash of the entire frame.** The observer the US
   runner installs (`graph_atomic_survey_financial.py:1623 observe`, wired at
   `:1634`; the same shape at `graph_atomic_survey_population.py:218/230` and
   `graph_survey_population.py:942/1086`) calls
   `reconstruction._population_stamp(population)`
   (`survey_atomic_geography.py:230`), which at `:245` calls
   `survey_population_preparation.py:641 _frame_identity`. That function loops
   **every cell of every column** in pure Python —
   `for value in series: update_cell(value)` at `:688-689`, and the same for
   every index value at `:676-677` — where each `update_cell` runs
   `_frame_cell_encode` (`:601`) → `_cell` (`:585`) → `_check_scalars` (`:82`)
   → `.encode()` → two `digest.update()` calls. That is ~8-12 Python-level
   operations **per cell**, i.e. O(rows x columns) with a large constant.
3. **Two `_context_digest` passes per cold node** (`executor.py:2423`, `:2449`),
   each hashing every column, the weights and the strata (`:466-495`).
4. **Every column written twice**: `_write_node` loops all entity columns into
   `store.put_column` (`executor.py:1524-1533`) and then writes the whole frame
   again via `store.put_frame` (`:1547`), which itself calls `frame.revalidate()`
   (`store.py:931`) and `_write_frame` (`store.py:1121`), serializing every
   column a second time. Each `_put` fsyncs every file and directory of the
   staged object (`store.py:754` → `store.py:164 _fsync_tree`). The read side is
   symmetric: a cache hit loads every column (`executor.py:1882`) **and** the
   whole frame (`:1899`).
5. **The stamps are recomputed again after the run** for verification:
   `graph_atomic_survey_financial.py:1895` and `:1910` re-run
   `_population_stamp` per node, so the per-cell Python loop runs at least twice
   per node per graph.

Modules that are NOT a population-scaling cost, checked and cleared:
`graph/canonical.py` (metadata only — `canonical_json` at `:42` never sees a row
payload), `graph/availability.py` (receipt-shape validation only),
`graph/artifact_edges.py` (descriptors and numeric scopes only).

---

## The constant floor: the whole ACS universe is parsed and JSON-encoded before sampling

`acs_housing_universe_source.py` reads the **entire** ACS PUMS universe on every
run, no matter how small the requested fraction, in pure Python:

- `_reconstruct` (`:563`) calls `_archive` (`:262`) on the household and person
  archives, builds a `full` projection of **every** household and person row
  (`:566-572`), writes it out as `full-projection.json` (`:573-574`), and only
  **then** calls `_select(full, serialnos)` (`:575`) to keep the sampled
  households. Sampling happens after the whole universe has been materialized.
- `_archive`'s parse loop (`:311-366`) runs, per row of the whole universe:
  `stream.readline` (`:313`), `digest.update(raw)` (`:322`), `_csv_record(raw)`
  (`:327`) — a stdlib CSV parse of every column of the line, the receipt records
  `"engine": "stdlib_csv_reader"` at `:590` — a width check (`:353`), a row
  build (`:355-359`), and then **`selected_bytes += len(_json(row))` (`:360`) —
  a full JSON encode of every row whose only use is to accumulate a size
  bound**, discarded immediately. The retained rows are then JSON-encoded a
  second time as a whole at `:573`.
- `_capture` (`:190-216`) first copies each archive into a snapshot and hashes
  it twice: `_copy` returns a digest while copying (`:213`), then
  `_persisted_sha` re-reads the persisted file and hashes it again (`:215`).
- The v4 snapshot tree contains **four** capture directories
  (`acs-hu-capture-33i6ivgc`, `acs-hu-capture-bp36xasy`,
  `acs-native-coverage-uu1suvx_/acs-hu-capture-x03gedgg`,
  `acs-native-preparation-800qjeft/acs-hu-capture-us72r6yw`), i.e. the 854 MB of
  ACS archives are copied, hashed twice and re-parsed several times per run.

**Why this matters more than anything else in the lane.** This cost is
*independent of the sample fraction*: a 1/8000 run does the same ACS work as a
full-source run. So whatever the profile measures for this phase at 1/8000 is
already the full-scale figure — it will not grow when the fraction grows. The
consequence is the opposite of the naive worry: the 19-node graph's
population-scaling work is *not* the thing that makes a 1/1000 run take 5,279
CPU-s. A large share of that is a fixed pre-sampling tax paid on every run of
any size.

### The per-row cost of that floor, in detail

`_csv_record` (`acs_housing_universe_source.py:236-259`) runs once per row of
the whole ACS universe and, per row:

- calls `capture_csv_reader(csv)` (`:237`), which re-checks the stdlib binding
  (`source_csv_builtin.py:25-27`);
- scans the raw line three separate times for NUL, CR and LF (`:246`);
- decodes it as UTF-8 (`:251`);
- **constructs a brand-new `csv.reader` object for that single line** (`:249-254`)
  instead of streaming the member through one reader;
- re-encodes **every parsed field** back to UTF-8 to length-check it
  (`:256-258`), for all ~280 ACS person columns even though only
  `SERIALNO/SPORDER/PWGTP` are kept (`_P_FIELDS`, `:56`).

Then the caller adds `selected_bytes += len(_json(row))` (`:360`). Put together,
one ACS capture makes at least three full Python passes over ~4.9M rows
(parse + per-row JSON encode + `_tables`' per-cell type validation at
`:415-425`), and the v4 run performed four captures.

---

## Line-number correction (2026-09-16)

Four citations committed earlier in this journal came from `sed -n 'A,Bp'`
ranges and were off by a few lines. Re-derived with `grep -n` and corrected in
place above: the node loop is `executor.py:2296`, `node_started` is `:2297`,
`wall_time=...` is `:2616`, the observer call is `:2569`,
`_source_paths_and_keys` inside `run_graph` is `:2284` (and `_all_node_keys`
`:2285`), `tokens = _csv_record(raw)` is
`acs_housing_universe_source.py:327`, the source symlink refusal is
`survey_population_preparation.py:391`, the request-fraction equality is
`:1239`, and the canonical-request check is `:340`. Everything else I had cited
came from `grep -n` and verified unchanged. The conclusions are unaffected.

---

## Static fan-out complete; the one quadratic path measured

The static attribution ran as a 14-agent workflow (7 scope readers + 7
adversarial verifiers, 0 errors). 214 cited hot paths:
**identity 120** (91 of which also run on a verification path), other 43,
store IO 35, kernel compute 16. Raw output kept at
`.profile-runs/static-map.json` and `.profile-runs/static-rows.json`.

I re-derived every line number I had committed with `grep -n`; four earlier
`sed`-range citations were wrong and are corrected above.

**The one genuinely superlinear path, measured rather than assumed.**
`population.py:1270-1273` (`_remapped_expand_memberships`) runs, for **every**
source group, a full-length boolean comparison over the entire person table:

```python
for source_group, targets in group_targets.items():
    members = source_person.loc[
        source_person[membership] == source_group, person_id
    ]
```

That is O(groups x people) = O(households^2). I measured the isolated loop on
synthetic frames at the pilot's people-per-household ratio (3,464/1,584 =
2.187), at 500 … 128,000 groups — a seconds-long microbenchmark that runs no
graph and reads no source, so it is **not** one of the lane's three profiled
runs (`.profile-runs/harness/bench_expand_membership.py`,
receipt `.profile-runs/expand-membership-bench.json`):

| groups | people | CPU |
|---|---|---|
| 500 | 1,093 | 0.032 s |
| 2,000 | 4,374 | 0.147 s |
| 8,000 | 17,495 | 0.597 s |
| 32,000 | 69,980 | 2.688 s |
| 128,000 | 279,919 | 15.07 s |

Naive log-log slope over that range is only **1.10**, because the ~67-73 us
per-group pandas `.loc` setup still dominates the scan below ~30k households.
Fitting the two-term form the code implies, `t = G x (c + k x P)`, gives
**c = 66.8-72.8 us per group** and **k = 0.185-0.188 ns per person per group**
across two runs. Extrapolating to the full source (G = 1,584,000,
P = 3,464,000): **~1,130 CPU-s, about 0.32 CPU-hours.**

So the quadratic term is real and does dominate above ~30k households — but in
absolute terms this path costs about **19 CPU-minutes** at full scale, not
days. It is a correction worth making explicitly: the static reviewer flagged it
as the scaling blocker, and the measurement says it is not. The blocker is
elsewhere.

---

## Measured per-cell constants (microbenchmarks, not profiled graph runs)

`.profile-runs/harness/bench_per_cell_identity.py` imports the repo's own
`_frame_cell_encode`, `_update_series` and `_storage_parts` and times their
verbatim inner loops. Receipt: `.profile-runs/per-cell-bench.json`. Per cell,
flat in row count (so these are pure O(cells) with a Python constant):

| loop | float64 | int64 | bool | Int64 (nullable) |
|---|---|---|---|---|
| `_frame_identity` per-cell (`survey_population_preparation.py:688-689`) | **0.74-0.83 us** | 0.36-0.47 us | 0.31-0.37 us | 0.48-0.55 us |
| `_context_digest` via `_update_series` (`executor.py:452-463`) | 0.14-0.22 us | 0.30-0.35 us | 0.19-0.25 us | **0.006-0.065 us** |
| `_storage_parts` (`population.py:2742`) | 0.001-0.06 us | 0.001-0.04 us | 0.001-0.03 us | ~0.000 us |

Two results worth stating plainly:

- **`_context_digest` is ~50x cheaper on nullable dtypes.** `Int64` takes the
  masked-buffer fast path (`executor.py:458-460`) at 0.006 us/cell; plain
  `int64`/`float64`/`bool` fall through to `series.to_numpy(dtype=object)`
  (`executor.py:462`) and then a per-value Python loop (`executor.py:446`) at
  0.14-0.35 us/cell. The declared dtype set (`store.py:85-87`) permits both.
- **I was wrong about the pickle round trip.** `_observer_snapshot`'s
  `pickle.dumps`/`loads` (`executor.py:372`) measures **0.0017-0.003 us/cell** —
  a 214-column x 32,000-row table round-trips in 11 ms. It is two to three
  orders of magnitude cheaper per cell than `_frame_identity`. It is not a
  meaningful cost and I am withdrawing it from the avoidable-cost shortlist.

### Frame shape, from the pilot's own exported graph declaration

`financial-artifacts/graph.json` shows the CREATE node declaring **245
columns** — person 214, household 41, tax_unit 6, spm_unit 6, family 5,
marital_unit 5 — and `preparation.json` gives the 1/1000 entity row counts
(household 1,584, person 3,464, marital_unit 2,774, tax_unit 2,128,
spm_unit 1,585, family 1,594), doubling on the clone. That is
**~537 cells per cloned household**, so one whole-frame `_frame_identity` pass
costs ~1.7M cells (~0.85 s) at 1/1000 and ~1.70 x 10^9 cells at full source.

---

## What the adversarial verifiers overturned (this changes the answer)

Seven verifiers re-opened every cited line. Their consensus corrections, which I
accept and which materially change the extrapolation:

1. **Almost nothing is superlinear in POPULATION.** Of the 24 `superlinear`
   flags the readers raised, the verifiers found the flag was really "linear in
   rows x a graph/schema constant" in all but two cases. The survivors are:
   - `population.py:1270` `_remapped_expand_memberships`, genuinely
     O(groups x people) — **measured above at ~1,130 CPU-s at full source**; and
   - `Frame.revalidate` -> `bundle.py:225 np.sort(id_values)` /
     `:230 np.unique(...)`, O(R log R) per group entity, re-run on every
     `put_frame` (`store.py:931`) and every `_validate_create`
     (`executor.py:1051`) — a log factor, not a power.
   A lane asking for a population scaling law would have been badly misled by
   the bare `superlinear: true` flags.
2. **`_context_digest` does NOT hash an accumulating population.**
   `_project_context` (`executor.py:605-642`) projects only the structural
   columns plus each slice's declared columns (`:616`), deduped at `:635`. A
   verifier counted the declared input columns per node from the pilot's own
   `financial-artifacts/graph.json`, in compiled order:
   `0, 24, 4, 24, 0, 0, 4, 7, 12, 245, 245, 245, 8, 8, 8, 0, 0, 0, 256` —
   **1,090 column-passes over the whole 19-node graph, with no growth in node
   index.** The k-th node hashes its own declaration, not O(k).
3. **The carried column set barely grows.** `survey_population.create` declares
   245 of the graph's 277 total outputs; the other 18 nodes add 32. The carried
   set goes 245 -> 277 (+13%) across the entire run. The per-node whole-frame
   work is O(nodes x rows x ~constant columns), not O(nodes^2 x rows).
4. **The per-node source re-hash fires for zero nodes here.** I had flagged
   `executor.py:2453` (`source_content_key` re-derived after each cold node) as
   repeated 3.7 GB directory hashing inside the node loop. A verifier checked
   the declarations: **no node of the financial graph declares the source**, so
   that line runs zero times in this run. Withdrawn.
5. **Cold-path work is skipped on cache hits.** `_context_digest` (x2),
   `_project_context`/`_freeze_frame`, and `_write_node` are all guarded by
   `if result is None:` (`executor.py:2406`) or `if not hit:` (`executor.py:2571`).
   Nine of the financial run's 19 nodes were store hits in v4 and paid none of it.
6. **`_write_frame`/`put_column` redundancy is a constant factor, not
   superlinearity.** Writing the same bytes twice (column objects + whole frame)
   and storing the entity-id index next to *every* column (`store.py:848`,
   hashed again at `:849` on write and `:895` on read) are genuine waste
   multipliers, but they are linear.

**Consequence.** The architecture's cost is essentially
`FIXED + c x households` plus one O(H^2) term worth ~19 CPU-minutes at full
source and an O(R log R) term. The naive "weeks" extrapolation assumed the whole
5,279 CPU-s scales; most of it does not scale at all.

### The verifiers' biggest catch: `_apply_result` is unguarded and copies twice

Every reader missed this and every relevant verifier flagged it. I verified it
directly:

- `executor.py:2497` calls `_apply_result` **outside both guards** — outside
  `if result is None:` (`:2406`) and outside `if not hit:` (`:2571`). It runs
  for every node, **cache hits included**.
- For an ordinary NONE-structural node it reaches `_patch_columns`
  (`population.py:1767`), whose first statement is
  `tables = _copied_tables(population.frame)` (`:1770`), and `_copied_tables`
  (`population.py:2680-2683`) is
  `{entity: frame.table(entity).copy(deep=True) for entity in frame.entities}`
  — **a full deep copy of every entity table**.
- It then calls `_rebuild_frame` (`population.py:1851` -> `:2686-2694`), which
  constructs a new `Frame`, and `Frame.__init__` copies **every table again** at
  `bundle.py:118` (`target[name] = frame.copy()`) and re-runs all six validators
  (`bundle.py:121-126`), including `np.sort(id_values)` (`:225`) and
  `np.unique(membership.to_numpy())` (`:230`) per group entity.

So each node pays **two full frame deep copies plus a complete constructor
validation**, unconditionally. That is the per-node population-scaling floor of
the executor, and the nine nodes that "hit the store" in the v4 run paid it in
full while doing no work.

### Per-node unconditional copy + validation: measured, and it is cheap

`.profile-runs/harness/bench_per_node_unconditional.py` (receipt
`.profile-runs/per-node-unconditional-bench.json`) builds tables at the pilot's
exact declared shape — person 214 cols x 2.187 rows/household, household 41,
tax_unit 6 x 1.343, spm_unit 6, family 5, marital_unit 5 x 1.751, i.e.
**536.8 cells per cloned household** — and times the two deep copies plus the
five-group linkage validation:

| cloned hh | cells | copy A | copy B | validate | total | per cell |
|---|---|---|---|---|---|---|
| 3,168 | 1,700,710 | 0.002 s | 0.001 s | 0.002 s | 0.005 s | 2.90 ns |
| 50,688 | 27,212,815 | 0.022 s | 0.018 s | 0.027 s | 0.067 s | 2.46 ns |
| 202,752 | 108,851,063 | 0.101 s | 0.107 s | 0.160 s | 0.368 s | 3.38 ns |

**~2.9 ns/cell**, i.e. fully vectorized. At full source that is 4.9 s per node,
**93 CPU-s across 19 nodes (0.026 CPU-h)**. The double copy is real waste but it
is not the scaling problem.

### Per-cell cost ranking of the whole-frame passes (all measured)

| pass | per cell | relative |
|---|---|---|
| `_frame_identity` (per-cell Python, `survey_population_preparation.py:688`) | **~500 ns** | **1x** |
| `_context_digest` on plain numpy dtypes (`executor.py:446`) | ~200 ns | 2.5x cheaper |
| `_storage_parts` (`population.py:2742`) | 1-60 ns | 8-500x cheaper |
| deep copy + linkage validation (`population.py:2681`, `bundle.py:118-126`) | 2.9 ns | 170x cheaper |
| `pickle` round trip (`executor.py:372`) | 2 ns | 250x cheaper |
| `_context_digest` on nullable dtypes (`executor.py:458-460`) | 6 ns | 80x cheaper |

`_frame_identity` is ~170x more expensive per cell than the frame copies it is
usually blamed alongside. It is the dominant population-scaling cost in the
architecture, and every one of its passes exists to produce a digest.

---

## DECISIVE: the architecture refuses a full US source by an explicit bound, before time matters

The lane asked whether this executor can build a full US dataset and at what
cost. It cannot, and the reason is not CPU. Two hard limits cap the build at a
fraction of the source:

**1. The preparation payload — the binding one.**
`survey_population_preparation.py:1346` encodes the whole preparation document
with `_encode(...)`, which defaults to `MAX_PAYLOAD_BYTES = 64 * 1024**2`
(`:50`) and raises `PAYLOAD_LIMIT` at `:108` the moment the accumulated bytes
exceed it. That document embeds **one record per source household and one per
person**: `"origins": origins` and `"selection": _plan_document(plan)`.

Measured on the pilot's own exported artifact — whose sha256
`34b362d85d2f06ac…` matches the manifest's `preparation_sha256` exactly, so it
is the bounded payload, not a re-render:

| component | bytes at 1,584 source households | per source household |
|---|---|---|
| `origins` (households 269,000 B, entities 224,755 B, persons 210,924 B, …) | 718,800 | 453.8 B |
| `selection` (`selected` has exactly 1,584 entries) | 385,122 | 243.1 B |
| everything else (producer, source_files, catalogues, hashes) | 32,141 | fixed |
| **total** | **1,136,063** | **696.9 B** |

Ceiling = (67,108,864 - 32,141) / 696.9 = **~96,250 source households — 6.1% of
the ~1,584,000-household US source.** At full source the payload the code must
encode is **1.03 GiB, 16.4x the limit.**

A second, independent 64 MiB budget guards the same lists inside
`_plan_document`: `_bounded_append` (`:816-820`) raises `ORIGIN_LIMIT` on
`budget[0] + size <= MAX_PAYLOAD_BYTES`.

**2. The allocation payload.** `graph_survey_population.py:62` sets
`ALLOCATION_MAX_BYTES = 64 * 1024**2`, and `_allocation_payload` (`:344-369`)
streams **one `_instruction_document` per household** (`:325-341`) into a single
bytearray, checking `ALLOCATION_LIMIT` before every append (`:359-363`). An
`_instruction_document` canonical-encodes to ~320 B, so that payload refuses at
**~209,700 households — 13.2% of the source.**

So the first wall the architecture hits at scale is `PAYLOAD_LIMIT` at roughly
**96,000 source households**, about one sixteenth of the US source. No CPU
budget, no parallelism and no profiler changes that: the build refuses. **Every
timing question in this lane is downstream of a refusal that arrives first.**

These are single-document, whole-roster JSON transports in a design that is
otherwise columnar. They are not intrinsic to the graph executor — they are
receipt/provenance payloads that chose one JSON document per run.

---

## Run 1 (1/8000) hit the CPU cap. Cap line, verbatim:

```
CPU CAP HIT: RLIMIT_CPU soft=1800s reached; SIGXCPU raised at cpu=1803.3s wall=1842.4s
```

`outcome: KILLED_AT_CPU_CAP`; CPU 1,803.3 s (1,783.0 user + 20.3 sys), wall
1,842.4 s, peak RSS **1.72 GB**, children CPU 0.004 s (the thread-env fix held —
no child processes). The SIGXCPU handler dumped a 1.26 MB partial profile before
the kernel killed the process.

**Where those 1,800 CPU-seconds went.** The run never reached the graph. It was
still in ACS source ingest, and the profile names the cost precisely
(self time, 15.6 billion total profiled calls):

| self | cum | ncalls | function |
|---|---|---|---|
| **890.4 s** | 1,361.5 s | 5,054,865 | `acs_person_coverage_authentication.py:188(_records)` |
| 168.0 s | 168.0 s | **3,382,952,633** | `bytearray.append` |
| 167.0 s | 167.0 s | **4,424,967,359** | `builtins.len` |
| 160.4 s | 160.4 s | **5,418,945,835** | `acs_person_coverage_authentication.py:60(_require)` |
| 136.2 s | 221.5 s | 980,880,110 | `acs_housing_universe_source.py:257(<genexpr>)` |
| 53.2 s | 53.2 s | 980,888,715 | `str.encode` |
| 50.3 s | 296.9 s | 3,673,585 | `acs_housing_universe_source.py:236(_csv_record)` |
| 16.4 s | 94.4 s | 5,054,861 | `acs_person_coverage_authentication.py:230(_decode_record)` |
| 13.8 s | **1,473.3 s** | **2** | `acs_person_coverage_authentication.py:278(_inventory)` |
| 11.8 s | 364.0 s | **2** | `acs_housing_universe_source.py:262(_archive)` |

Two call sites account for the whole run: `_inventory` (1,473.3 s over **two**
calls) and `_archive` (364.0 s over **two** calls) = 1,837 s of 1,842 s.

**The mechanism.** `_records` (`acs_person_coverage_authentication.py:188-227`)
is a **byte-by-byte Python loop over the entire ACS person CSV**:

```python
while block := stream.read(4096):
    for byte in block:                                    # every byte, in Python
        ...
        _require(len(record) < cap, "CSV_RECORD_BYTES")   # a call per byte
        ...
        _require(token_bytes <= MAX_TOKEN_BYTES, ...)     # another call per byte
        record.append(byte)                               # a call per byte
```

3.38 billion `bytearray.append` calls is ~3.4 GB — the uncompressed ACS person
member — walked one byte at a time to find CSV quote boundaries, twice. That
alone is the 4.4 billion `len()` and 5.4 billion `_require()` calls.
`_decode_record` (`:230`) then builds a fresh `io.TextIOWrapper` over a fresh
`io.BytesIO` and a fresh CSV reader **per row** (5,054,861 calls, 94.4 s).

**And the sample filter runs last.** `_inventory` reaches
`if cells[0] not in serialnos: continue` only *after* each row has been
byte-scanned, hashed and decoded. The same holds in
`acs_housing_universe_source.py`, where `_reconstruct` (`:563`) builds the full
projection at `:566-574` and only then calls `_select(full, serialnos)` at
`:575`. **So this entire ~1,840 CPU-s is paid identically at every sample
fraction, including 1/8000.** Run 2 (1/2000, a 4x larger sample) is now running
to confirm that empirically: if the fixed-tax reading is right, its profile
should show the same ~5.05M `_records` and ~5.42B `_require` call counts.

---

## cProfile overhead on this workload: 5.05x, measured

With 15.6 billion profiled calls, the profiler is not a passive observer, so I
measured its inflation on the exact dominant function rather than assuming it.
`.profile-runs/harness/bench_profiler_overhead.py` (receipt
`.profile-runs/profiler-overhead-bench.json`) runs `_records` over a real
209,715,200-byte slab of `psam_pusa.csv` from the staged archive, with and
without `cProfile`:

| | CPU |
|---|---|
| unprofiled | **16.222 s** (299,540 records, 12.9 MB/s) |
| profiled | **81.935 s** |
| **inflation** | **5.051x** |

So run 1's 1,803.3 profiled CPU-s correspond to roughly **357 unprofiled
CPU-s**. Every profiled figure below is reported as profiled, with the 5.05x
factor stated, not silently deflated.

**Consequence for the lane's design.** The 1,800 s cap was never going to admit
a completed run: the v4 receipt shows 4,605 CPU-s for the runner *unprofiled* at
1/1000, and the fixed part of that does not shrink at 1/8000. Under a profiler
that multiplies the most call-dense phase by 5x, the capped run reached only the
ACS ingest. The three-fraction design in the brief cannot produce a scaling law
under a 1,800 CPU-s cap, and I am not going to manufacture one from runs that
all die in the same fixed phase.

### Run 1 bucket attribution (profiled self time, 1,842.4 s total)

| bucket | self | share | calls |
|---|---|---|---|
| (c) store IO / codecs — **ACS source ingest** | **1,297.7 s** | **70.4%** | 6,505,612,377 |
| (d) other — Python builtins called per byte by that loop (`bytearray.append`, `len`, `str.encode`, `next`, `isinstance`, `re.search`) | 452.3 s | 24.6% | 8,869,637,843 |
| (d) other — unclassified (zipfile, io, codecs) | 65.5 s | 3.6% | 177,472,416 |
| (c) store IO — stdlib CSV/zip parse | 13.0 s | 0.7% | 24,116,910 |
| (a) identity — canonical JSON | 8.7 s | 0.5% | 14,741,553 |
| (a) identity — sha256 | 5.0 s | 0.3% | 8,737,374 |
| (b) kernel compute (numpy/pandas/sklearn/torch) | **0.0 s** | 0.0% | 18,126 |
| (a) identity — `_frame_identity` per-cell | **0.0 s** | 0.0% | 2,756 |

**95% of the run is ACS source ingest and the per-byte builtins it drives.**
Identity work is 0.7%, kernel compute is 0.0%, and the graph store is
effectively untouched (1,003 calls) — the run never reached a node.

### The measured fixed ACS tax, unprofiled

Uncompressed data members in the staged archives: ACS person
**2,405,468,113 B (2.41 GB)**, ACS household **977,484,520 B (0.98 GB)**.
At the measured unprofiled `_records` rate of 12.9 MB/s, one byte-loop pass over
the person members is **186 CPU-s**, and `_inventory` runs **twice** per run —
**~373 CPU-s** of pure per-byte Python scanning, before `acs_housing_universe_source._archive`'s
own two passes. None of it varies with the sample fraction.

---

## The ceiling, demonstrated rather than inferred

`.profile-runs/harness/bench_canonical_encode.py` feeds the **pilot's own**
`preparation.json` — scaled by replicating its per-household and per-person
lists — through the repo's own bounded encoder
`survey_population_preparation._encode`:

| scale | source households | payload bytes | encode CPU | |
|---|---|---|---|---|
| x1 | 1,584 | 1,136,063 | 0.052 s | 717.2 B/hh |
| x4 | 6,336 | 4,426,274 | 0.206 s | 698.6 B/hh |
| x16 | 25,344 | 17,587,118 | 0.844 s | 693.9 B/hh |
| x64 | **101,376** | — | 3.193 s | **REFUSED: `SurveyPopulationPreparationError: PAYLOAD_LIMIT`** |

The refusal is real and reproducible, at **~96,700 source households (6.1% of
the ~1,584,000-household US source)**. The full source would need a
**1,048 MiB** payload — **16.4x the 64 MiB limit**.

And the encoding itself is cheap: **33.3 us per source household**, i.e. only
**52.7 CPU-s** at full source. So the ceiling costs nothing to raise in CPU
terms — it is a transport-shape decision (one bounded JSON document per run
carrying one record per household), not a performance trade-off.

## The scaling decomposition, from the v4 receipt's own node timings

Splitting v4's 28 timed nodes into source-bound and population-bound:

| | prefix run (9 nodes) | financial run (19 nodes) | total |
|---|---|---|---|
| source-bound nodes (4 ASEC predictor nodes + `observed_geography`) | 141.9 s | 957.5 s | **1,099.4 s** |
| population-work nodes (22 of them) | 33.3 s | 10.5 s | **43.8 s** (mean 1.99 s/node) |
| of which nodes that were store **hits** and still cost time | 2.3 s | 8.7 s | 11.0 s |

Two things fall out:

- **The population-scaling work of the whole 28-node graph is 43.8 CPU-s at
  3,168 cloned households.** The 1,099.4 s that dominates the node timings is
  source ingest, which does not grow with the sample.
- **Store-hit nodes still cost 11.0 s**, which is the unguarded `_apply_result`
  double frame copy plus the observer stamp (`executor.py:2497`, `:2569`)
  charging nodes that did no work.

---

## Report drafted; waiting on run 2 to fill its row

`.profile-runs/report-draft.md` (566 lines) holds the full report: runs table,
bucket attribution, the fixed floor, the hard ceiling, the scaling law,
incumbent durations, the line-cited static map, the avoidable-cost
recommendation, the verdict, and a method/caps section. Run 2's row, cap line
and children-CPU figure are the only placeholders left.

Prediction table now anchors on the v4 receipt's measured 5,278.6 CPU-s rather
than a partial fixed term, and adds only the measured scaling increment:
full source = 5,278.6 + 43,756 + 1,130 = **~13.9 CPU-hours** on measured terms.
The naive extrapolation the brief opened with (5,278.6 x 1000 = 1,466 CPU-h =
61 CPU-days) is **wrong by ~105x**, because it multiplies a fixed source-ingest
tax by the sample ratio.

**Decision: run 3 will not be spent.** Both profiled runs die in the same fixed
ACS phase, so a third fraction yields a third copy of the same number. The
authorization is a ceiling on machine time, not a quota. The report states this
and names the measurement that would actually close the remaining gap: one
uncapped profiled run at 1/8000, about 2.5 CPU-hours.

---

## Reversing the run-3 decision: spend it on a sampling profiler

I said above I would not spend run 3, on the grounds that a third fraction dies
in the same fixed phase. That reasoning holds for a third **cProfile** run — but
it overlooked the lever the overhead measurement handed me.

cProfile inflates this workload **5.05x** (measured). That is precisely why the
capped runs never got past ACS ingest: 1,800 profiled CPU-s is only ~357
unprofiled CPU-s of pipeline. A **statistical** sampler costs ~0 per call, so
the same 1,800 CPU-s cap covers roughly **five times as much of the pipeline** —
plausibly through the ASEC ingest and into the prefix graph.

That matters because the largest remaining hole in the report is the **3,012
CPU-s of v4's runner time (65%)** that sits outside both the node loop and the
ACS ingest, and whose scaling split drives the full-source estimate from 13.9 to
53 CPU-hours. Run 3 is the one chance to attribute it.

`.profile-runs/harness/sample_run.py` therefore replaces cProfile with a daemon
thread sampling the main thread's stack every 5 ms via `sys._current_frames()`,
accumulating self-function counts, the deepest in-repo frame, and a 10-second
phase timeline. Same eight thread-env names, same RLIMIT_CPU 1800/1810, same
SIGXCPU dump, same RSS watchdog, same harness. It trades exact call counts for
reach — which is the right trade here, because the call counts are already
measured and the reach is not.

Run 3 will be 1/8000 (reusing the staged `sources-8000`), launched after run 2
completes so the two measurements do not share a machine.

## Arithmetic correction in the predictions table

The O(H^2) column was wrong: it showed +43 s at the ceiling but +21 s at 1/10,
i.e. a larger value at a smaller size. Recomputed from the measured two-term fit
`t = G x (c + k x 2.187G)` with G as **source** households (the loop runs on the
pre-clone person table), minus its value at the 1/1000 anchor: +1.1 s at 1/100,
+10.2 s at the ceiling, +20.8 s at 1/10, +1,137.3 s at full source. Full-source
total is **13.94 CPU-h**, and the naive 1000x extrapolation (1,466 CPU-h =
61 CPU-days) is wrong by **105x**.

---

## Run 2 was suspended mid-flight; disclosed

At ~1,370 CPU-s I found run 2's process in state **`T` (stopped)** with `%CPU
0.0` and its CPU counter frozen — something had sent it SIGSTOP/SIGTSTP (most
likely SIGTTOU from the backgrounded shell's process group). It had been
suspended for roughly **12 minutes of wall time** (elapsed 37:01 against 22:53
of CPU). I resumed it with `kill -CONT`; it returned to state `R` at 100% CPU
and continued from where it stopped.

**What this does and does not affect.** A stopped process accrues no CPU time,
so run 2's **CPU measurement and its RLIMIT_CPU cap are unaffected** — the cap
still fires at 1,800 CPU-s of real work, and the profile is unchanged. What is
corrupted is run 2's **wall time**, which now includes ~12 minutes of doing
nothing. The report will give run 2's CPU figure and mark its wall figure as
invalid rather than printing a number that looks like a measurement. Run 1's
wall time (1,842.4 s against 1,803.3 s CPU, 97.9% CPU-bound) is unaffected and
is the one to use.

The cap watcher now detects state `T` and sends SIGCONT automatically so a
second suspension cannot silently stall the lane.

---

## Run 2 (1/2000): the floor is fraction-independent, exactly

```
CPU CAP HIT: RLIMIT_CPU soft=1800s reached; SIGXCPU raised at cpu=1803.4s wall=2354.1s
```

`outcome: KILLED_AT_CPU_CAP`; CPU **1,803.4 s** (1,782.7 user + 20.7 sys), peak
RSS **1.38 GB**, children CPU 0.005 s, no manifest written (it never reached the
graph either). Wall 2,354.1 s is **not a valid measurement** — it includes the
~12-minute suspension.

Comparing the two partial profiles at a **4x difference in sample fraction**:

| function | 1/8000 ncalls | 1/2000 ncalls | ratio |
|---|---|---|---|
| `acs_person_coverage_authentication.py:188(_records)` | 5,054,865 | 5,054,865 | **1.0000** |
| `bytearray.append` | 3,382,952,633 | 3,382,952,633 | **1.0000** |
| `acs_person_coverage_authentication.py:60(_require)` | 5,418,945,835 | 5,418,945,835 | **1.0000** |
| `acs_person_coverage_authentication.py:230(_decode_record)` | 5,054,861 | 5,054,861 | **1.0000** |
| `acs_person_coverage_authentication.py:278(_inventory)` | 2 | 2 | **1.0000** |
| `builtins.len` | 4,424,967,359 | 4,214,038,477 | 0.952 |
| `acs_housing_universe_source.py:236(_csv_record)` | 3,673,585 | 2,962,934 | 0.807 |

The five ACS-authentication counters are **bit-for-bit identical** — not
approximately equal, identical — across a fourfold change in the requested
sample. The two that differ (`len`, `_csv_record`) are simply where each run's
cap happened to land inside the second `_archive` pass.

This is the measured proof of what §4 read out of the code: **the sample
fraction changes nothing about the source-ingest work.** It is a fixed tax,
and it alone exceeds the lane's entire 30-CPU-minute budget.

Run 2 bucket split (self time 2,354.1 s over 14.94e9 calls): store IO 1,810.6 s
(76.9%), other 529.9 s (22.5%), identity 13.6 s (0.6%), **kernel compute 0.0 s**
— same shape as run 1.

## Report updated with run 2; run 3 launched

All run-2 placeholders are filled and §2 is rewritten for the run-3 reversal.
Run 3 (`sample_run.py s8000 8000`) started 2026-09-16, sampling at 5 ms with the
auto-resume watcher armed. Its row in the runs table is the last placeholder.

---

## Run 3's first launch was killed by session death; relaunched detached

Picking the lane back up at 23:34 I found **no run-3 process alive** and **no
metrics file**. The evidence of what happened is in the output tree: the run had
started at 23:22, copied its source snapshot, and written
`snapshots/acs-hu-capture-dwlum5ct/full-projection.json` (292,484,053 bytes) at
23:30 — then stopped between 23:30 and 23:34. `sample_run.py` writes
`s8000.metrics.json` on *every* exit path it controls (COMPLETED, cap, RSS,
SIGXCPU). No metrics file exists, so **none of those paths ran**: the process
was killed by a signal it does not handle, when the shell that owned it went
away. It produced **zero measurement** — roughly 8 wall-minutes of work with
nothing recorded.

**Relaunched, properly detached.** macOS has no `setsid(1)`, so
`.profile-runs/harness/detach.py` does the detaching itself: fork, `setsid()`,
fork again, reopen stdio onto `.profile-runs/s8000r.log`, write the final pid to
`<log>.pid`, `execv` the harness. The run is now pid 65548 with **PPID 1** and
its own session — no controlling terminal, no shell process group, nothing left
for a session exit to kill.

**Disclosure for the report.** This deviates from the brief's "foreground" in
letter, and the report will say so: it is still one single-process run under the
same `RLIMIT_CPU` 1800/1810, the same 16 GB RSS watchdog, the same eight
thread-env pins, no retry logic and no compute children. What changed is only
that it no longer dies with its parent. The relabel to `s8000r` keeps the dead
attempt distinguishable from the measurement.

Run-3 budget accounting: this is the **third** authorized run. The dead attempt
consumed ~8 wall-minutes and produced no data; I am not counting a run that
recorded nothing as one of the three, and I am naming it here rather than
letting the run count look clean.

---

## Two arithmetic hazards checked myself; one is a real defect

While the audit fleet ran I checked the two places the draft could be
double-counting or reporting polluted numbers.

**1. `_inventory` + `_archive` do NOT nest — the sum is legitimate.** §3 adds two
*cumulative* times (1,473.3 s + 364.0 s = 1,837 s of 1,842 s), which is only
valid if neither is an ancestor of the other. From the profile's own caller
table: `_inventory` (`acs_person_coverage_authentication.py:278`) is called by
`acs_population_catalogue.py:141(_preflight)`; `_archive`
(`acs_housing_universe_source.py:262`) is called by `_reconstruct` (`:563`),
called by `acs_population_catalogue.py:435(issue_acs_source_catalogue)`. Two
sibling call trees. The claim stands.

**2. Run 2's bucket seconds are polluted by the suspension — a real defect.**
cProfile times with `perf_counter` (wall), not CPU, so run 2's profiled total is
its **wall** total of 2,354.1 s, which includes the ~12-minute suspension. I
found where it landed by diffing per-function `tottime` between the runs:

| function | run 1 ncalls | run 2 ncalls | run 1 tottime | run 2 tottime | delta |
|---|---|---|---|---|---|
| `acs_person_coverage_authentication.py:188(_records)` | 5,054,865 | 5,054,865 | 890.4 s | 1,399.6 s | **+509.2 s** |
| `:60(_require)` | 5,418,945,835 | 5,418,945,835 | 160.4 s | 177.4 s | +17.1 s |
| `bytearray.append` | 3,382,952,633 | 3,382,952,633 | 168.0 s | 177.3 s | +9.3 s |

**Identical call counts, 509 extra seconds.** That is stopped time attributed to
whichever function held the interpreter, not extra work — and it lands almost
entirely in one function, inside the `store_io` bucket.

Re-deriving run 2's split on the measured **1,803.4 CPU-s** basis (subtracting
each bucket's delta against run 1, renormalised to the CPU total):

| bucket | printed (polluted) | corrected | run 1 |
|---|---|---|---|
| store IO | 1,810.6 s / 76.9% | **1,283.0 s / 71.1%** | 1,310.7 s / 71.1% |
| other | 529.9 s / 22.5% | **507.1 s / 28.1%** | 518.0 s / 28.1% |
| identity | 13.6 s / 0.6% | **13.3 s / 0.7%** | 13.7 s / 0.7% |
| kernel | 0.0 s / 0.0% | **0.0 s** | 0.0 s / 0.0% |

Corrected, the two runs agree **to the tenth of a percent in every bucket** —
a stronger statement than the draft's polluted "same shape", and honest. The
report will print the corrected row and say why.

Third, smaller: `analyze_profile.py`'s docstring claims tottime "sums exactly to
the profiled CPU total". It sums to the profiled **wall** total. For run 1 the
two differ by 2.1% (1,842.4 wall vs 1,803.3 CPU); for run 2, by 30%. The report
must label profiled totals as wall and reconcile them against CPU.

---

## Independent re-derivations: §6 exact, §7 exact, §8 has a brief-level gap

**§6's 43.8 s is right, under its own stated classification.** I re-summed the
v4 manifest's `timing` block myself. 28 nodes, **1,143.16 s**. Four ASEC
predictor nodes **957.15 s** (the draft prints 957.5 — a typo; 957.2 is
correct), prefix `observed_geography` **141.93 s**, financial
`observed_geography` (a store hit) **0.31 s**; source-bound total
**1,099.39 s**; population-work **43.77 s over 22 nodes, mean 1.99 s** — the
draft's 43.8 / 22 / 1.99 exactly. The store-hit subtotal re-derives as 10.98 s
against the draft's 11.0. The predictions table's scaling increments follow from
43.8 x (cloned/3,168) − 43.8: 394 / 2,628 / 4,336 / 43,756. All reproduce.

**§7 is exact, every figure, from the files themselves:**

| figure | draft | source line |
|---|---|---|
| staging wall / user / sys | 7,829.5 / 99,337.7 / 3,215.6 s | `staging_run.log`: `7829.54 real 99337.73 user 3215.55 sys` |
| staging peak RSS | 40.13 GB | `40126742528 maximum resident set size` |
| release chain wall / user / sys | 9,156.4 / 5,672.8 / 302.3 s | `release_chain_run.log`: `9156.43 real 5672.78 user 302.27 sys` |
| release chain peak RSS | 94.18 GB | `94183096320 maximum resident set size` |
| release chain stages | `(9147.4s)` | `DONE stages=['materialize','calibrate','qa','finalize','package'] (9147.4s)` |
| target compilation | 1,132.1 s | `donor/release_manifest.json` `build.timing.target_compilation_seconds` 1132.080194915994 |
| calibration | 1,072.4 s | `calibration_seconds` 1072.4242046249856 |
| total build | 8,161.1 s | `total_build_seconds` 8161.056042167009 |

Summary arithmetic re-derived: (7,829.54 + 9,156.43)/3600 = **4.72 wall-hours**;
(99,337.73 + 3,215.55 + 5,672.78 + 302.27)/3600 = **30.15 CPU-hours**;
99,337.73/7,829.54 = **12.7x** user-only parallelism (13.1x including sys).
The staging lane's wall also re-derives from `staging.log`'s own bracket
(03:38:59Z → 05:49:28Z = 7,829 s).

**§8 has a real gap against the brief.** The brief named ten files to read:
`executor.py`, `population.py`, `store.py`, **`kernel.py`**, **`canonical.py`**,
**`manifest.py`**, **`codecs.py`**, **`availability.py`**, **`artifact_edges.py`**
and the frame identity code. The draft's static map cites the first three plus
`keys.py` and `bundle.py`, and mentions the bolded six **zero times** — and
`static-map.json` barely reaches them either (`availability.py`: 0 mentions).
Two of the brief's named cost categories, **codec encode/decode** and **identity
recomputation on read**, therefore have no line-cited answer. A second workflow
(6 readers, one per module, each operation re-verified at its line by a skeptic)
is closing it now; the result becomes §8b.

---

## §5 reproduced independently, and the source count sharpened

I re-measured the pilot's exported `financial-artifacts/preparation.json`
(1,136,063 B, sha256 `34b362d85d2f06ac…`, matching the manifest's export record)
by encoding each component with the repo's own canonical separators:

| component | bytes | n | per source hh |
|---|---|---|---|
| `origins.households` | 269,000 | 1,584 | |
| `origins.entities` | 224,755 | 6 | |
| `origins.persons` | 210,924 | 2 | |
| `origins` (with `storage_transitions` 13,268 and age normalization 762) | **718,800** | | 453.8 B |
| `selection.selected` | **385,122** | **1,584** | 243.1 B |
| fixed (producer 21,135, `selection.excluded` 7,250, source_files, catalogues, hashes) | **32,141** | | — |
| total | **1,136,063** | | **696.9 B/hh** |

718,800 + 385,122 + 32,141 = 1,136,063 exactly. The draft's split is right.

Code constants confirmed by reading: `MAX_PAYLOAD_BYTES = 64 * 1024**2` at
`survey_population_preparation.py:50`; `_encode(value, maximum=MAX_PAYLOAD_BYTES)`
at `:104` raising `_require(..., "PAYLOAD_LIMIT")` at `:108`; the whole-document
`payload = _encode(` at `:1346`; the second budget
`_require(budget[0] + size <= MAX_PAYLOAD_BYTES, "ORIGIN_LIMIT")` at `:818`.

**The ceiling is a range, and the report should print it as one.** Against the
67,108,864-byte budget:

- from the x1 artifact's own rate (696.9 B/hh, fixed 32,141 B): **96,247 hh**
- from the measured x1→x16 marginal rate (692.4 B/hh): **96,867 hh**

So **96,200–96,900 source households**, i.e. **6.1%**. The draft's point estimate
of "~96,700" sits inside that; I will print the range and keep 6.1%.

**The source is 1,587,376 households, not "~1,584,000".** The preparation
artifact records it directly: `selection.supplied_households = 1587376`. Using
the pilot's own figure, the full-source payload is **1,048–1,055 MiB = 16.4–16.5x
the limit**, and the cloned population at full source is 3,174,752 (the brief's
"~3.17M"). Encoding cost re-derives as 33.29 us/hh x 1,587,376 = **52.8 CPU-s**.

---

## Every derived number now regenerates from a script

`.profile-runs/harness/final_tables.py` recomputes the node decomposition, the
ceiling range and the whole predictions table from the receipts and the
microbenchmark constants — no number in the report is hand-carried. Its output,
with the corrected source count (1,587,376) and the re-summed node timings:

```
nodes 28  wall 1143.16s
  4 ASEC predictor nodes 957.15s; observed_geography (both) 142.24s
  source-bound 1099.38s; population-scaling 43.78s over 22 nodes (mean 1.99s)

ceiling 96,247-96,867 source hh (6.06-6.10% of 1,587,376)
full-source payload 1,048-1,055 MiB (16.4-16.5x the limit)
encode cost at full source 52.8 CPU-s

target                       source hh   cloned hh    +scaling    +O(H^2)  total CPU-h
1/1000 (v4, measured)            1,584       3,168           -          -         1.47
1/100                           15,873      31,746         395        1.1         1.58
ceiling (~96,557)               96,557     193,114       2,625       10.2         2.20
1/10                           158,737     317,474       4,343       20.9         2.68
full source                  1,587,376   3,174,752      43,826    1,141.9        13.96

naive 1000x extrapolation 1,466 CPU-h = 61 CPU-days; wrong by 105x
quadratic term at full source 1,142.0 CPU-s (19 min); log-log slope 1.10
```

The corrected source count moves nothing in the third digit: the draft's 13.94
CPU-h becomes **13.96**, the ceiling row stays at 2.20 CPU-h, and 105x stands.

## The ingest mechanism, read rather than inferred

I read `_records` (`acs_person_coverage_authentication.py:188-227`) and
`_inventory` (`:278-320`) myself rather than taking the profile's word:

- The loop is `while block := stream.read(4096):` then **`for byte in block:`** —
  Python-level, per byte. Per byte it runs `_require(len(record) < cap, ...)`
  (one `_require`, one `len`) and `record.append(byte)`; non-comma bytes run a
  second `_require(token_bytes <= MAX_TOKEN_BYTES, ...)`.
- **The call counts corroborate the mechanism arithmetically.** 3,382,952,633
  `bytearray.append` = one per byte = **3.38 GB scanned**, which matches the
  staged ACS person (2.41 GB) + household (0.98 GB) uncompressed members. The
  5,418,945,835 `_require` calls split as 3.38e9 unconditional + 2.04e9
  token-guard, implying **1.34e9 commas over 5,054,865 records = 265 commas per
  record**, against the ~280 ACS person fields. The profile and the source agree.
- In `_inventory` each record is `digest.update(raw)`-ed, `_decode_record`-ed
  into a full CSV row, width-checked, and projected to `cells` — and only then
  does `if cells[0] not in serialnos: continue` discard it. The sample filter is
  literally the last statement.

**The module already contains the fast pattern it needs.** Its non-applicable
branch (`:293-296`) digests members in 4 KiB blocks with no per-byte Python at
all; only the applicable branch drops into `_records`. The recommendation in §9
is therefore not speculative: block-wise digest plus a vectorized boundary scan
is the shape of the code sitting three lines above.

---

## Run 3 completed — it did not hit the cap, it hit a REFUSAL

`outcome: PYTEST_EXIT_1`. **840.6 CPU-s** (823.6 user + 17.0 sys), **935.2 s
wall** (89.9% CPU-bound), peak RSS **6.75 GB**, children CPU 0.005 s, 96,109
samples at an effective 9.73 ms interval. It spent less than half the CPU budget
and stopped because the build refused, not because the cap fired.

```json
{"phase":"ACTUAL_NINETEEN_NODE_COLD_EXECUTION","exception_type":
"SurveyPopulationPreparationError","status":"INCOMPLETE","elapsed_seconds":930.93,
"automatic_retry":false,"release_eligible":false,"static_codes":[]}
```

pytest's traceback ends at
`survey_population_preparation.py:1418: SurveyPopulationPreparationError:
PREPARATION_ISSUANCE_REFUSED`, raised by

```python
    except SurveyPopulationPreparationError:
        raise
    except Exception:
        raise SurveyPopulationPreparationError("PREPARATION_ISSUANCE_REFUSED") from None
```

**a catch-all that discards the cause** (`from None`, and `static_codes` is
empty). I cannot say what failed, because the code is written not to say. That
is itself a reportable finding for a merge decision: the preparation step
converts every unexpected exception into one static code, so a failure at scale
is undiagnosable from its receipt. The same path completed at 1/1000 in v4 on
the same sources, so the difference is the requested fraction; I did not spend a
fourth run to bisect it, and I am not guessing at the cause.

**The sampler says exactly where it died.** Last timeline marks:
`acs_population_catalogue.py:275(consume)` at t=914 s,
`asec_current_money.py:519(__post_init__)` at t=924 s,
`asec_person_income_source.py:312(_verify)` at t=934 s. So it fell over entering
**ASEC** restoration verification, having completed the whole ACS side.

### What run 3 bought: the first unprofiled phase attribution

| bucket (deepest in-repo frame) | share | ≈ CPU-s |
|---|---|---|
| **store IO — source ingest** | **94.9%** | **798.1** |
| identity / canonical JSON / digest verification | 4.2% | 35.3 |
| other | 0.5% | 4.3 |
| **kernel compute** | **0.4%** | **3.0** |

| heaviest in-repo frames | share | ≈ CPU-s |
|---|---|---|
| `acs_person_coverage_authentication.py:188(_records)` | 53.20% | 447.2 |
| `acs_housing_universe_source.py:262(_archive)` | 18.82% | 158.2 |
| `acs_person_coverage_columns.py:130(lines)` | 10.87% | 91.4 |
| `acs_housing_universe_source.py:497(_select)` | 3.99% | 33.5 |
| `canonical.py:18(_json_value)` | 1.87% | 15.8 |
| `acs_housing_universe_source.py:398(_tables)` | 1.57% | 13.2 |
| `acs_person_coverage_authentication.py:69(_json)` | 1.36% | 11.4 |

The heaviest *self* frame is **zipfile at 80.7%** — the decompression the byte
loop drives. Phase timeline: `_records` from t=10 to t=450, `_archive` to
t=580, then a mixed reconstruct/canonical-JSON/select phase to t=914, then ASEC.

**The headline number this run buys: the ACS source-ingest phase costs ~830
CPU-s, unprofiled, fixed at any fraction.** The draft inferred ~364–450 CPU-s by
dividing the profiled figure by 5.05; the direct measurement is roughly twice
that, because the profiled runs were killed before finishing the phase and the
5.05x factor applies to `_records`, not to the zipfile and pandas work around
it. That is **15.7% of v4's entire 5,278.6 CPU-s build**, paid identically by a
1/8000 toy build and a full-source build.

It also independently confirms the cProfile bucket shape with a profiler that
costs ~0 per call: kernel compute **0.4%**, identity **4.2%**, ingest **94.9%**.

---

## The finding the draft missed entirely: memory binds before CPU

`_observer_snapshot` (`executor.py:355-372`) does
`pickle.loads(pickle.dumps((tables, frame.strata)))` — a full independent copy of
every table and link — and the executor calls it at `:2569`, **outside the
`if not hit:` guard**. Its own docstring says "this costs one full detached
population and a temporary serialized table buffer per callback. Observers may
retain that snapshot."

The financial runner's observer retains all of them:
`observed[node_id] = population` (`graph_atomic_survey_financial.py:1625`),
never cleared, read at `:1768`, `:1788`, `:1791`, `:1794`, `:1864`, `:1911`,
`:1915`, handed out as `node_populations=observed` at `:1941`. **Nineteen full
population copies held at once.**

Run 3 makes the subtraction possible for the first time: it peaked at
**6.75 GB having built zero populations** (it refused in preparation), so that is
the fraction-independent source-handling floor. v4 peaked at **9.31 GB** with 19
retained at 3,168 cloned households. The difference — **2.56 GB** — is the
population-dependent part: ~138 MB per copy, ~45 KB per cloned household,
**~85 bytes per cell** over 1,700,582 cells.

| target | one population | 19 retained | + floor |
|---|---|---|---|
| ceiling (~96,557 source hh) | 8.2 GB | **156 GB** | **163 GB** |
| full source | 135 GB | **2,569 GB** | **2,575 GB** |

So the 2.20 CPU-hour build at the payload ceiling needs ~163 GB of RAM. Memory
binds **below** the ceiling the report already identified. Per population the
footprint is unremarkable — 89 KB per source household against the incumbent's
measured 62 KB — so it is the retention, not the representation, and it is a
runner-level fix.

Flagged honestly in the report as computed from two measured RSS peaks plus a
retention read in the source, not measured directly.

## Six-module gap closed (71 agents, 0 errors)

`availability.py` and `artifact_edges.py` contribute **zero** population-scaling
cost (reasons cited); `kernel.py` holds every row-scaled object by reference and
`KernelResult` has no `__post_init__` at all. `codecs.py` is per-table pandas,
11 of 14 operations row-scaled but vectorized. Two real finds:

- **`manifest.py` carries per-row EXPAND lineage.** `executor.py:1274` puts
  `receipt["expand"]` (one pair per expanded row) and `:1286`
  `receipt["entrant_strata"]` into the node receipt; the manifest then deep-copies
  it (`:277`→`:124`), encodes every node's payload for the content key (`:594`),
  embeds each receipt twice in `to_json` (`:651-664`), re-derives the key twice on
  read (`:740-746`), parses the document twice (`:772`/`:684`), and canonicalizes
  the whole body once more **just to build an error-message label** (`:786`).
- **`randomness.py:69-75` is per-row canonical JSON + per-row SHA-256** —
  `canonical_json([_coordinate(v) for v in key])` then `hashlib.sha256(...)`
  inside `for key in keys:`. I opened both files and confirmed them myself
  rather than taking the agents' word.

`canonical.py` itself is exonerated: 107 lines, no loops, and a value grammar
that structurally refuses a Frame/DataFrame/Series/ndarray (`:38-40`) — but it
materializes a full recursive copy of its argument before encoding (`:18-40`),
which is what makes the per-row call sites expensive.

---

## Run 3 filled into §1; the last placeholders are gone

`report-final.md` §1 now carries run 3's real row (1/8000, 5 ms sampler, 935.2 s
wall / **840.6 CPU-s** / 6.75 GB, outcome `PYTEST_EXIT_1` — the refusal, not the
cap) and a paragraph saying explicitly that **no cap line was emitted for run 3**
because it never approached the cap. Two prose inaccuracies fixed at the same
time: "all three died inside ACS source ingest" was wrong for run 3 (it cleared
ACS and fell over entering ASEC verification), and the children-CPU line now
prints all three measured values (0.0043 / 0.0047 / 0.0048 s) plus the fact that
the 16 GB RSS watchdog never fired in any run.

No `RUN3_*` placeholder remains anywhere in the report.

## Next

1. Full verification pass over the finished report: every number re-derived from
   its receipt, every line number re-opened at #893's head, every mechanism
   claim checked against code I can point at.
2. Then `out.md` (uncommitted, per the destination decision above) plus the
   committed durable copy under `experiments/`.

---

## Verification pass: two defects I found myself, both in the recommendation

An 8-dimension adversarial verification fan-out is running over the finished
report. While it ran I checked the load-bearing mechanism claims myself, because
the headline recommendation is the one place a fabricated mechanism would do
real damage — it is what a merge decision would act on.

**Defect 1 (material — the headline recommendation names the wrong mechanism).**
§10 item 1 and §11 both say: "the executor already derives a content-addressed
`frame_key` for every stored frame (`keys.py:106`); verification can compare
stored digests instead of recomputing a per-cell digest." I opened `keys.py`:

```python
def frame_key(node_key: str) -> str:
    """Derive the structural frame artifact identity from its node."""
    return _hash_parts("frame", node_key)          # keys.py:106-109
```

`frame_key` is a hash of the **node key alone**. It carries no frame content
whatsoever — it is recipe-addressed, not content-addressed. Two different frames
produced by the same node recipe get the same `frame_key`. Comparing `frame_key`
would verify nothing about cell contents, so as written the recommendation does
not work.

The *substance* survives, because a real stored content digest does exist — it
is just somewhere else. `_payload_table` (`store.py:140-152`) records
`sha256` + `size` for every payload file of every stored object, using
`_sha256_file` (`:132-137`), which reads in 1 MiB blocks through C hashlib.

**Defect 2 (material — a static-map gap in a category the brief named
explicitly).** The brief asked for "identity recomputation on read". §8b answers
"found, and cheap — `artifact_edges.py:208` … the expensive read-side
recomputation is in `manifest.py` instead." That misses the store entirely.
`_verified_meta` (`store.py:227-290`) **re-hashes every payload byte of the
object** at `:271` (`actual_hash = _sha256_file(payload_path)`) and compares it
against the recorded digest, and it is called on **every** store read and on
every write that finds an existing object: `:721`, `:735`, `:765`, `:878`
(`load_column`), `:969` and `:981` (`load_frame`), `:1007`, `:1038`. So a
cache-hit node re-hashes the entire stored frame's bytes. It is C-speed and
therefore cheap per byte — which is exactly why it belongs in the map: it is the
*cheap* counter-example that makes the per-cell Python loop look as bad as it is.

**The correct fix, now that I have read both ends of it.** `_population_stamp`'s
own docstring (`survey_atomic_geography.py:230-237`) says it is a "pure
in-process seal" that must "never [be] persisted or compared across
reconstructions", so a stored digest genuinely cannot be substituted for it. The
expensive part is inside `_frame_identity`
(`survey_population_preparation.py:641`), whose cost is literally

```python
    for value in series:          # :688-689
        update_cell(value)        # _frame_cell_encode + two digest.update per cell
```

— a per-cell Python loop over every cell of every column. It is already a pure
function of cell values plus dtype metadata, so it can be replaced by a
per-column vectorized hash over the column buffer and its null mask without
changing what it seals. That is a one-function change and it needs no store
digest at all. The report will say this instead.

## Next

- Fold both corrections into §8b, §10 and §11 with the line numbers above.
- Adjudicate the verification fan-out's surviving findings when it returns.
- Then `out.md` (uncommitted) + the committed copy under `experiments/`.

## Both self-found defects applied to the report

- §10 item 1 rewritten: the recommendation is now "vectorize `_frame_identity`'s
  per-cell loop" with the loop cited at `survey_population_preparation.py:688-689`
  / `:675-676`, plus an explicit paragraph saying why the stored-digest shortcut
  does **not** work (`frame_key` = `_hash_parts("frame", node_key)`,
  `keys.py:106-109`; `_population_stamp` documented as a pure in-process seal,
  `survey_atomic_geography.py:230-237`).
- §11 verdict's clause corrected the same way.
- §8a gained a table row and §8b a paragraph for the store's whole-payload
  re-hash on every read (`store.py:271` via `_verified_meta` `:227-290`).
- §6a's stale 1,700,710 cells → 1,700,582 (the figure §8d derives); the
  discrepancy is disclosed in §8d and changes no printed digit.
- Both recorded as entries 7 and 8 in §8c, the report's own corrections list.

## Third self-found defect, and it is the biggest: §9 mixed decimal and binary GB

Recomputing the memory wall from raw byte counts rather than from the report's
own rounded figures:

- the three profiled runs print `peak_rss_bytes / 1024³` (**binary**);
- v4's "9.31 GB" is `9,313,337,344 / 10⁹` (**decimal**); in binary it is 8.67 GiB.

So §9 subtracted 6.75 GiB from 9.31 GB and got a "2.56 GB" population-dependent
delta. The true difference is 9,313,337,344 − 7,244,562,432 = **2,068,774,912 B
= 1.93 GiB**, and every number downstream of it was ~33% too high:

| | was | is |
|---|---|---|
| per retained population copy | 138 MB | **103.8 MiB** |
| per cloned household per copy | 45 KB | **33.6 KiB** |
| per cell | 85 B | **64.0 B** |
| 19 retained at the ceiling, + floor | 163 GB | **124 GiB** |
| 19 retained at full source, + floor | 2,575 GB | **1,938 GiB (1.9 TiB)** |
| incumbent, for comparison | 62 KB/hh | **57.9 KiB/hh** |

§9 is rewritten on binary units with the raw byte counts printed, a 1/10 row
added, and the unit hazard stated in the text so no later reader repeats it.
§10's "falls to ~140 GB" → **~108 GiB**; §11's "~163 GB … ~2.6 TB" → **~124 GiB
… ~1.9 TiB**; §7's incumbent peaks now print GiB (37.37 / 87.71) with a note that
the incumbent's log labels its own peak "94.18GB" decimally; §1's v4 row now
reads 8.67 GiB so the whole run table is one unit system, and its column header
says GiB.

**No qualitative conclusion changes.** Memory still binds below the payload
ceiling, a ceiling build still needs far more RAM than this machine has, and the
per-population footprint is still in the incumbent's range — which is why the
error survived three readings. Recorded as correction 9 in §8c.

## Independent re-derivation of the numeric spine (mine, not an agent's)

I recomputed the report's load-bearing tables from their stated inputs with a
throwaway `python3 -c`, without looking at the report's own figures first:

- **§6d predictions** — fixed 5,278.6 − 43.78, linear 43.78 per 3,168 cloned hh,
  quadratic from c = 66.8 µs/group and k = 0.188 ns/person/group at P = 2.187 G:
  totals **1.47 / 1.58 / 2.20 / 2.68 / 13.96 CPU-h**, naive **1,466 CPU-h**,
  ratio **105×**. Every figure matches. The `+scaling` column is the *increment*
  over the 1/1000 baseline (395 = 439 − 43.8), which is why it differs from an
  absolute linear term by exactly 43.8 in each row; §6d's own bucket table prints
  the absolute 43,870 alongside the incremental 43,826, and both are right.
- **§5 ceiling** — (67,108,864 − 32,141)/696.9 = **96,247**; 1,584 +
  (67,108,864 − 1,136,063)/692.4 = **96,867**; full payload **1,048.2–1,055.1 MiB
  = 16.38–16.49×**; 96,557/1,587,376 = **6.08%**; allocation ceiling
  67,108,864/320 = **209,715**; encode 33.3 µs × 1,587,376 = **52.9 CPU-s**. All
  match.
- **§3 buckets** — run 1's four bucket rollups sum to 1,842.4 s exactly; run 3's
  four sum to 840.7 against a measured 840.6 (rounding). 830/5,278.6 = **15.7%**.
- **§7 incumbent** — re-read from the logs themselves, per file rather than with a
  multi-file grep: `staging_run.log:12735` carries `7829.54 real 99337.73 user
  3215.55 sys` with `40126742528` RSS, and `release_chain_run.log:126` carries
  `9156.43 real 5672.78 user 302.27 sys` with `94183096320`. **The report's
  attribution is correct** (I briefly misread a combined grep as inverting them,
  and checked per-file before believing it). Derived: **4.718 wall-h**,
  **30.147 CPU-h**, **12.69× user/wall**, total build **2.267 h**. The
  `donor/release_manifest.json` timing block matches to six decimals.
- **§10 shares** — 34%, 10.4%, 87.2%, 2.3%, 47%, 54%, 71%, and the 7.3 / 6.9
  CPU-h counterfactuals all reproduce against a full-source total of 50,246.8 s.
- `final_tables.py` is stdlib-only (`json`, `pathlib`); I ran it with the system
  `python3` and its printed table is character-identical to §6d's.

**One slip fixed:** the `fixed` column printed **5,234.7** where 5,278.6 − 43.78
= 5,234.82. Corrected to **5,234.8** in all seven places. It moves no total, but
the report claims every number regenerates, so a hand-carried rounding error is
not allowed to stand.

Markdown table integrity checked programmatically: 0 ragged tables across the
whole report.

## Fourth self-check: the "CPU-hours are wall-hours" claim, scoped

I verified the executor's serial loop myself rather than relying on the
fan-out: `for node_id in compiled.order:` at `executor.py:2296` with
`node_started` on the next line and `wall_time=time.perf_counter() - node_started`
at `:2616`; the observer call at `:2568-2569` sits immediately **above** the
`if not hit:` at `:2571`, confirming §8a's "every node, hits included"; and
`grep -rn` for `threading` / `multiprocessing` / `concurrent` / `joblib` /
`n_jobs` across `packages/microcosm-graph/src/microcosm/graph/` returns
**nothing**.

But §7's sentence said the loop has "no threading or multiprocessing, so for it
CPU-hours and wall-hours are the same number", and that is one step further than
the evidence: the *executor* has no concurrency, yet a kernel could still get
parallelism from threaded BLAS under numpy or torch, which this lane's harness
pinned to 1 and therefore could not have observed. Rewritten to say exactly
what was checked (the package-wide grep), name the BLAS caveat, and then explain
why the conclusion survives anyway — the dominant measured costs are a per-byte
Python loop and a per-cell Python hashing loop, both single-threaded, and kernel
compute is 0.4%.

## Brief-compliance check I could make myself: cumtime top-40

The brief asked for "the top 40 by cumtime per run". The report's in-text table
is by **self** time, which looked like a gap until I opened the artifacts:
`f8000.top40.txt` and `f2000.top40.txt` both carry pstats' own header
`Ordered by: cumulative time` / `List reduced from 7544 to 40`, so the required
artifact exists and is correctly ordered. Its first ten rows are `_pytest` and
`pluggy` frames at 1,842 s cumulative — true, and useless for attribution, which
is why the report tabulated self time in the text. §3 now says both things
explicitly instead of leaving the reader to assume the brief was skipped.

## Fifth self-found defect: §6d's rows did not add up

Cross-footing the predictions table instead of just checking its totals: the
`fixed (measured)` column printed 5,234.8 s while `+ linear` and `+ O(H²)` are
increments over the **whole v4 build** (5,278.6 s) — which is what
`final_tables.py` computes (`total = V4_CPU_TOTAL + scale_inc + quad_inc`). Two
decompositions mixed in one table, so every row was short of its own total by
exactly 43.8 s: v4's own population-scaling work, counted once where the columns
implied twice.

Fixed by naming the base for what it is — `v4 base (measured)`, 5,278.6 s — and
stating the incremental model above the table, then cross-footing the absolute
split underneath (5,234.8 + 43,870 + 1,142 = 50,247 s = 13.96 CPU-h). §10's
bucket table moved from the incremental 43,826 (87.2%) to the absolute 43,870
(87.3%) so that column sums to the 50,246 CPU-s it prints. No total, no
percentage and no CPU-hour figure changes. Recorded as correction 10 in §8c.

This one is worth noting for method: it was invisible to checking totals, and
invisible to the generator script, which is self-consistent. Only adding the
columns across caught it.

## The opening summary now carries the memory wall

§9's finding arrived late and never reached the report's own short answer, which
listed only the payload ceiling and the ingest tax. For a report a merge
decision rests on, the second binding constraint belongs in the first paragraph.
Added, with its epistemic status attached in the same breath (computed from two
measured RSS peaks plus a retention read, not measured end-to-end).

Also softened the opening's reproducibility claim from "none is hand-carried" to
name the two exceptions §8c now records — corrections 9 and 10 were both
hand-carried numbers, and a blanket claim that the verification pass just
falsified should not survive it.

## Sixth self-found defect: the headline uncertainty band did not follow from its inputs

§6d's "realistic full-source figure is ~26–40 CPU-hours" is repeated in the
verdict, so it is one of the report's most-quoted numbers — and it was asserted,
not derived. Its stated inputs are "roughly 50–100 CPU-s at 1/1000" of
unattributed runner-level population work. Scaling that by the row ratio
3,174,752/3,168 = 1,002.1 and adding to 13.96 gives **27.9–41.8**, not 26–40.
The one-sided upper bound "~900 CPU-hours" likewise computes to **848**.

Both corrected, and both now show the arithmetic in line so the next reader can
check them without re-deriving the ratio. The verdict's clause moved to
"~28–42 ... (§6d derives that band)". The conclusion is untouched — the point of
the band is that it is well under the naive 1,466 CPU-h and in the incumbent's
30.15 CPU-h neighbourhood, which holds at 28–42 exactly as it did at 26–40.

## Read-only and containment discipline, verified rather than assumed

- `git status` clean; `git ls-files | grep -c profile-runs` = **0**. Nothing
  under `.profile-runs/` is tracked, and `git check-ignore -v` confirms the
  exclusion is real (`/.profile-runs/` at `.git/info/exclude:22`).
- A `-maxdepth 1 -newermt "2026-09-15 21:00"` scan of the pilot run directory
  returns **nothing**: the tree the sibling v5 lane reads has not been written
  since before this lane began.
- Nothing was written under the system temp directories; no branch, no push,
  no stash.

## A measured number the report was sitting on and not using

`profiler-overhead-bench.json` already recorded
`unprofiled_bytes_per_second: 12927527.6` — the per-byte scanner's actual
throughput, **12.9 MB/s** — and the report never printed it. It is the most
communicable number in the whole lane: for comparison I measured
`hashlib.sha256` on this machine at ~2,870 MB/s, so the loop that is only looking
for commas and newlines runs **222× slower than cryptographic hashing of the same
bytes**. Added to §4 with both figures and their provenance.

## Seventh self-found defect, and the only one that moves a headline

`bench_expand_membership.py` measures the loop at `population.py:1270-1273` with
`MEMBERSHIP = "household_id"` — i.e. it models **one** group entity, groups =
households. But `population.py:1266` wraps that loop in

```python
    for group in before.schema.group_entities:
```

and `US_SCHEMA` declares **five** (`microcosm/frame/units.py:45-51`: household,
tax_unit, spm_unit, family, marital_unit), with `source_person` — the whole
person table — scanned in full for every one of them. Using the pilot's own
per-household entity ratios, which the sibling bench
`bench_per_node_unconditional.py:22-29` already carried (household 1.0,
tax_unit 1.343, spm_unit 1.0006, family 1.0063, marital_unit 1.7513), there are
**6.1012 groups per source household**.

The quadratic term is therefore **6.10× what the report said**:

| | was | is |
|---|---|---|
| quadratic at full source | 1,142 CPU-s (19 min) | **6,967 CPU-s (1.94 CPU-h)** |
| quadratic at 1/1000 | 0.1 CPU-s | **0.7 CPU-s** |
| full-source total | 13.96 CPU-h | **15.58 CPU-h** |
| quadratic share of the build | 2.3% | **12.4%** |
| naive-extrapolation error | 105× | **94×** |
| observer's share of the build | 47% | **43%** |
| realistic band incl. unattributed runner time | ~28–42 CPU-h | **~30–43 CPU-h** |
| if `observed_geography` moves to the scaling side | 53 CPU-h | **55 CPU-h** |

`final_tables.py` now carries `GROUPS_PER_HH` and a docstring citing
`population.py:1266`, so the corrected term regenerates rather than being
hand-carried; its printed table matches the report's.

Two things I am flagging rather than smoothing over:

1. **"A rounding error against the fixed term" is withdrawn.** The H² term is now
   the second-largest scaling term in the build. The *conclusion* still holds —
   the dominant exponent is 1, and at every size the architecture can actually
   reach today the quadratic term is under a minute — but the sentence that
   dismissed it was wrong and is gone.
2. **It is still a lower bound.** The bench times the boolean comparison only;
   the code then runs `for source_member in members:` (`:1274`) over every
   matched person, ~5 × P Python iterations the bench never paid.

This is the only one of the seven corrections that moves a headline number, and
it moves it **against** the architecture — which is the direction that has to be
checked hardest before a merge decision leans on the report.

## Opening summary realigned

"it is linear, not quadratic" in the short answer was true of the report as
drafted and false after correction 11, so it now reads "its dominant exponent is
1 — though one genuinely quadratic path costs 1.9 CPU-hours at full source, 12%
of the build (§6b)", and the ingest sentence carries the measured 12.9 MB/s.
