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
