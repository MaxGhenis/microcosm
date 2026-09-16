# Lane: Phase 2 — execute main's documented from-scratch US chain (Path B, 1% rung)

Worktree `~/PolicyEngine/_worktrees/microcosm-main-build-check`, detached HEAD
`fc17cc2ff` = `origin/main` `51c3143829b88382270f5af0714ae28fba14f803` + Phase 1's
journal commits only (`git diff --name-only 51c3143829..HEAD -- tools packages
pyproject.toml uv.lock` is **empty** — the build code under test is byte-identical
to origin/main).

Runtime root: `~/PolicyEngine/_buildq-runtime/` (NEW, per S6).
Phase 1's `PROGRESS-main-build-check.md` is left exactly as it was.

**Purpose and its limit:** this run answers "does main's code execute its
documented from-scratch chain end to end, and does the result pass the release
stage and the preflight gates?" It runs on main's current lock
(policyengine-us **1.819.0**), so per stop condition S1 its output is **not a
certification candidate** — the certified default `populace-us-2024-spm-20260915`
declares `>=2.0.0,<2.3` and was built with 2.2.1.

## State

B1 (pooled ASEC source frame) launched detached 2026-09-16T03:50:43Z.

## Rules in force

- S1 acknowledged; S2 zero-support gate is a finding, not a workaround;
  S3 abort on RSS >~100 GB or new swap growth; S4 never publish / no HF writes /
  no `--staging`; S5 fresh checkpoint roots; S6 new runtime root.
- Orchestrator amendment (maxghenis-9d, 2026-09-16): (1) after B3 + preflight,
  if nothing else on the box is >20 GB RSS and free memory allows the measured
  85 GB peak, also run Path A into `_buildq-runtime` as a separately named
  lineage (A1 `puf_support_base` → A2 `fiscal_refresh --base-h5` with the July
  release-stage Ledger feed `b3c0835631…`), expecting the zero-support gate;
  report both lineages side by side. (2) **Never** `pkill -f` / `killall` /
  pattern kill on this machine — a sibling lane's `pkill -f pytest` killed a
  guarded 45-node pilot tonight. Kill only pids recorded in
  `_buildq-runtime/launch/*.launch.json`, by exact pid.
- Every long stage runs detached under `_buildq-runtime/launch/spawn.py`, which
  double-forks + `os.setsid()` so the stage is its own session leader (ppid 1),
  in no lane's process group, and survives this session ending. Each stage
  writes `<name>.launch.json` (pid/pgid/sid/argv/shell line), `<name>.pid`,
  `<name>.rss.csv` (20 s samples of tree RSS + system swap + free pages) and
  `<name>.rc`.

## Machine baseline at launch (recorded, `launch/baseline-before-B1.txt`)

`2026-09-16T03:50:43Z` — load avg 132/147/122, **swap already 3,525.81 MB used
of 5,120 MB before this lane started anything**, 83,119 free pages (~1.3 GB).
S3 says "abort if swap becomes non-zero"; it was already non-zero, from other
lanes. This lane therefore monitors the *delta* from this baseline and says so
in the report — it does not claim a zero-swap run.

## Done

- Verified HEAD and that no build code differs from `origin/main`.
- Confirmed every pinned input from BUILD-PLAN-main.md §1 is on disk at the
  pinned path and size; recomputing sha256 for the 14 hashed inputs in the
  background (`inputs/recomputed-sha256.txt`).
- Built the detached launch harness; B1 launched.

## Next

B1 → hash its output → B2 (1% rung, `tools/us_stacked_pool_smoke.sh.example`
verbatim) → B3 release from the pool manifest → preflight gates → publisher
contract check (no publish) → loader checks → Path A (if memory allows).
