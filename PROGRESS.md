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
  (`SOURCE_SYMLINK`), and its `_stat_identity` (line 269) includes `st_ctime_ns`
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
  `executor.py:2303` is the first statement of `for node_id in compiled.order`
  (`executor.py:2302`), and `wall_time=time.perf_counter() - node_started` at
  `executor.py:2612` is in the `NodeReceipt` built at the end of the same body.
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
  (`executor.py:2283`) once per graph, and the pilot runs three graphs (base
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
