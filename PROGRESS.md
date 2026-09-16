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
