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

**Finding F1 is already in hand: the plan's Path-B chain does not connect.**
B1 ran exactly as BUILD-PLAN-main.md §3 prescribes and succeeded (rc 0, 122 s,
7.07 GB peak). B2 then rejected B1's output in 31.7 s:

    ValueError: Frame checkpoint .../asec_raw_stage.h5 is missing HDF group
    '_populace_frame_checkpoint'.

`build_us_asec_pooled_source_base.py --out-h5` writes a plain pooled H5;
`build_us_multispine_pool.py --asec-raw-stage-h5` demands a **Frame
checkpoint** with a raw-stage binding. `load_asec_raw_stage_checkpoint`
(`packages/microcosm-build/src/microcosm/build/us_runtime/asec_checkpoint.py:145-180`)
documents this: *"Only the dedicated auxiliary producer artifact is accepted."*
The sole producer on main is Path A's `build_us_puf_support_base.py`, in its
`source_construction` stage, via `_ensure_asec_raw_stage_checkpoint`
(`tools/build_us_puf_support_base.py:1691-1693, 1811-1868`), and only when
`--asec-h5` is supplied. So **Path B cannot start without running Path A's base
stage first** — which BUILD-PLAN-main.md §1 states in prose, and §3's Stage B1
command contradicts.

A1 (`build_us_puf_support_base.py --stage all`) therefore launched
2026-09-16T03:59:37Z as a **prerequisite of B2**, not only as the amendment's
second lineage.

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

## B3's argument surface is much larger than the plan says (read at source, 2026-09-16)

`--exact-k` is not a five-flag group. `tools/build_us_fiscal_refresh_release.py:1618-1690`
forces ALL of: the five (`--exact-k`, `--exact-k-pi-hi`, `--pool-manifest`,
`--pool-manifest-sha256`, `--pool-release-id`), **plus** an explicit non-negative
`--seed`, `--no-staging`, `--incumbent-diagnostics`,
`--incumbent-diagnostics-sha256`, `--frozen-target-surface-sha256`,
`--ledger-facts-sha256` **and** `--ledger-manifest-sha256`; and it forbids
`--base-h5`, `--dense-default-dataset`, `--evidence-release` and any
`--selection-source-*`. BUILD-PLAN-main.md §3 lists five of the twelve.

Three consequences, each a candidate finding:

- **L1 — the pinned Ledger feed is structurally unusable in this arm.**
  `--ledger-manifest-sha256` requires `--ledger-facts` to be a Chronicle
  *consumer artifact directory* (`manifest.json` + `consumer_facts.jsonl`).
  A bare feed raises: *"A manifest hash pin was provided but the Ledger feed is
  a bare consumer-facts file with no manifest"*
  (`packages/microcosm-build/src/microcosm/build/ledger_artifact.py:258-262`).
  The plan's release-stage pin `consumer_facts_buildn_v9_4.jsonl` (b3c0835…) is
  a bare file, and a bounded search of every `_build*-runtime` root plus
  `~/PolicyEngine/chronicle` finds **no consumer artifact directory anywhere on
  this machine** — only bare `consumer_facts_*.jsonl` and one chronicle test
  fixture.
- **I1 — the incumbent diagnostics ARE obtainable.** The certified release
  publishes `calibration_diagnostics.json`
  (sha `870449b44e86b13b25bcea1a57f0e7af37f4d4db18be815eea3acdf9fe6eb40e`,
  19,512,724 B). Downloaded read-only from
  `policyengine/populace-us@populace-us-2024-spm-20260915`; the recomputed
  sha256 matches the manifest exactly. Its `target_surface` block carries
  `sha256 49bb0fe3dfd4c399e7b3f900b0e5ba29d9d72413d9170dfc155a9fa5e91c6f6f`,
  `n_targets 5659`, `n_records 57240`.
- **S1' — the frozen-surface check pins the rung.** `--frozen-target-surface-sha256`
  is compared post-calibration against the surface the run actually compiles
  (`tools/build_us_fiscal_refresh_release.py:11108-11117`), so the exact-k arm
  demands the run reproduce the incumbent's surface. The incumbent's is over
  57,240 records; a 1% pool is far smaller.

## Established since (all reproduced, all with verbatim errors)

- **F2** — plan §2 Stage A1 omits `--puf-source-year-csv`; A1 died at stage 3 of
  24 after 205.10 s, peak RSS 12.37 GB.
- **F3** — S5 is enforced in code: `outer_stage_runtime.py:277` refuses a
  checkpoint dir whose run_config changed. Fresh dir `base-q2` used.
- **F5 / F6** — the two structural B3 blockers (bare Ledger feed; frozen target
  surface pinned to the incumbent's 5,659 x 57,240 rung).
- **F7** — the plan mislabels the pool rungs. `build_us_multispine_pool.py:618`
  and `:345` make the label fraction x 100, so the plan's "f025 (2.5%),
  9.6-14 h" is the **25%** rung. Full scale is ~4x that, not ~40x.
- **Loader check answered.** `loader.py:440` (guarded by the test at `:437`)
  reproduced verbatim. Correction to Phase 1: it is one line but not one
  package — Core 3.31.0 also fails the certified `==3.32.5`. The certified H5
  itself opens cleanly through `USSingleYearDataset` under 1.819.0
  (57,240 households / 166,321 persons). And `microcosm.data` has **no
  local-path entry point at all**.
- **Publisher validate-only mode exists**: `microcosm-publish-release <dir>
  --preflight-only`, Hub-free, confirmed live. No `--dry-run`/`--check-only`.

Report deliverable: `~/PolicyEngine/_recovered/scratch-backup/893/lanes/out-main-build-phase2.md`,
with the master copy at `out-main-build-phase2.SALVAGED-COPY.md` (Phase 1's
lesson: never let the only copy sit at the `-o` path).

## Next

B2 relaunch against `checkpoints/base-q1/asec_raw_stage.checkpoint.h5` → B2 (1% rung, `tools/us_stacked_pool_smoke.sh.example`
verbatim) → B3 release from the pool manifest → preflight gates → publisher
contract check (no publish) → loader checks → Path A (if memory allows).


## Adversarial verification pass (16 agents, 2026-09-16 ~04:40Z)

Three skeptics per finding, each assigned a distinct lens and told to refute.
Results:

- **F1 — claim stands, wording fixed.** No other producer exists anywhere
  (exhaustive `write_frame_checkpoint` call-site sweep). But Path B owes Path A
  only the `source_construction` stage, not the whole base build, and the
  monolithic `--stage all` *without* `--checkpoint-dir` never emits the artifact.
- **F5 (ledger) — claim stands**, independently confirmed: 111 machine-wide
  `consumer_facts*.jsonl`, none with a sibling `manifest.json`.
- **F6 — MATERIALLY WRONG, corrected.** The surface digest hashes only the
  target-identity rows; `n_records` is a sibling report field, not an input
  (`microcosm/calibrate/diagnostics.py:179-199`, re-read directly to confirm).
  A 1% pool is NOT excluded by record count. What stands instead: the comparison
  runs *after* the multi-hour ladder, and its raise is conditional. Corrected in
  both the receipt and the report; the original reason must not be repeated.

New reachability facts folded into the receipt: `--exact-k N` semantics and the
pool-load-time cardinality check; a gate_failed pool cannot enter the exact-k
arm at all; `chronicle build-consumer-artifact` exists but refuses the pinned
feed and would mint a new identity (hand-writing a manifest would be fabricated
provenance — not done, and recommended against); preflight on a Path-B pool with
the only available Path-A selection manifest is a guaranteed `selection_carryover`
FAIL; the publisher preflight needs `--artifact-root`.


## A1 (Path A base stage) COMPLETE — rc 0, 2026-09-16T05:34Z

First completed from-raw-sources US base build on today's main.
**5,058.35 s wall (1 h 24 m), peak RSS 65.10 GB, 0 swaps.**
`base_populace_us_2024_puf_support.h5`, 2,351,269,694 B, sha256
`033821f140a2230ff4c2cf887bbfaae6536f4585a0edf4ea0ae3ca57b23d71ad`.
168,852 base households / 432,523 persons -> 352,932 expanded / 907,382.

Revises the plan on both axes: the plan's "18 min" is July's figure (this is
4.6x it, on a loaded box), and the plan left A1's memory blank while
`SYSTEM_REQUIREMENTS.md` projects ~29 GB for the WHOLE end-to-end build —
the base stage alone is 2.2x that.

Preflight gates launched against that base H5 (a cheap preview of the release
gates, and the direct test of whether main's fresh base carries the frozen
support Build P's selection source names).

B2 still running (transfer target 35/47 at 05:36Z, ~1 h 30 m in).


## Preflight + publisher contract check DONE (2026-09-16 ~05:45Z)

**Preflight on Path A's fresh base: rc 1, 32.58 s, peak RSS 9.76 GB.**
One hard failure, quantified:
`selection_carryover` FAIL — "Frozen support does not preserve the PUF
capital-gains own-tail stratum: missing 15228 donor(s), extra 0 donor(s).
Regenerate the selection-source manifest from the rebuilt support before
release." -> **F8: the plan's Stage A2 cannot run against a freshly built base.**
Build P's frozen support is bound to July's base.
**F9**: the preflight misreports a supplied `--ledger-facts` as
"not provided" (`inputs.ledger_facts` in the JSON records the file); the true
cause is the upstream selection failure. Predicted by the verification pass from
`release_gate_preflight.py:878,:886-896`, reproduced live. Its tally also labels
SKIPPED checks as AT-RISK.

**Publisher contract check: `--preflight-only` exists and was exercised live.**
Hub-free, no credentials, rc 1 with 46 enumerated contract failures as a bare
traceback on stderr (empty stdout). Pointed at the HF cache dir, which holds only
2 of 9 artifacts — so those failures demonstrate the checker runs, they are NOT a
judgement on the certified release. Recorded that caveat explicitly.

A2 rewritten with two documented deviations forced by F8 (drop the stale
selection manifest; drop its dependent `--selection-mass-protection`, whose only
purpose is protecting carriers inside a frozen selection). Both are supported
configurations on the `--base-h5` arm, not bypasses. A2 stays QUEUED until B2
finishes — 85 GB + 64 GiB will not co-exist on a 128 GB box.


## B2 / B3 DONE — Path B's answer is in (2026-09-16 06:14-06:17Z)

**B2: rc 1, 2 h 10 m, peak RSS 66.92 GiB, 0 swaps.** Pool built:
36,734 households / 80,395 persons, H5 155,054,588 B
(`7b626086a2d87ab929d7acbc29a5bd2a194a261569a76e82f63999f007e55754`),
manifest `7c9d9b27c41390fd2b2845db16cf55871af216260eef82a57cc26a6e13ca1078`.
**`status=gate_failed`, `simulation_ready=False`** — `us_stacked_completeness`
passed, `us_by_origin_battery` failed (health-coverage incidence ratios outside
[0.8, 1.25], one envelope-distance breach, one dead comparison). These are NOT
the `insufficient_support` receipts the docstring says to expect at 1%; no
quality claim is made either way.

Two corrections it confirms: the minted id carries **f001** (F7), and the run
**exceeded the committed example's own "<=64 GiB" envelope** at 66.92 GiB while
staying inside its 2-4 h envelope.

**B3: rc 1 in 23.91 s.** `ValueError: US multispine pool manifest ... is not
simulation-ready.` (`us_runtime/h5_io.py:1119`). **This is the S2 answer and it
is NOT the zero-support gate** — a gate_failed pool cannot enter the exact-k arm
at all, and `--allow-gate-failed-base-pool` requires `--base-h5` so it is
unavailable on the pool arm by construction. No bypass sought; none exists.
B3 never reached F5's Ledger blocker or F6's frozen surface — the red battery
stops it first.

**Preflight on the pool**: refused at the same simulation-ready gate.

**F10 — the plan's A1 and A2 are mutually incompatible.** A2 refused the base
A1 built from the plan's own command: CD crosswalk `383a6666…` != expected
`c7cb040b…` (`build_us_fiscal_refresh_release.py:2729`). The plan's SS1 calls
`c7cb040b…` "Path B (pinned)" and gives it only a `_buildo-runtime` path; it is
in fact **packaged in the repo** and required by the release stage on ANY base.
A1 relaunched 06:18:30Z with the packaged crosswalk, fresh `base-q3`, separate
`--out` so the first base survives.

## Next

A1d -> A2 (Path A release, the amendment's second lineage) -> final report.


## TERMINAL FINDING F11 (2026-09-16 07:07Z) — both chains blocked on the Ledger feed

A1 attempt 4 (packaged crosswalk): **rc 0, 46 m 28 s, peak RSS 72.47 GB**, base
sha `475ca33fcdbf60f107ba212c762e9e9ea9587e96b5a645750e61aaa2395b7822`.

A2 attempt 2 against it: **rc 1 in 49.59 s** —
`LedgerHierarchyMetadataError: ... dimension 'bea_nipa.series_code' requires
exactly one non-empty label, got []`
(`ledger_targets.py:1023`, via `fiscal_targets.py:982`).

**Tested every Ledger feed on the machine through the same entry point: all five
fail identically**, same fact id. Mechanism confirmed by reading the validator
AND surveying the feed: of 37,405 rows, **0 carry
`layout.groupby_dimension_label` and 0 carry non-null `dimension_labels`** — the
two and only two sources `_validate_chronicle_hierarchy_labels`
(`ledger_targets.py:1009-1019`) will accept. Its docstring states it refuses
identifier-derived substitutes, so this is deliberate strictness against a feed
generation that predates the contract.

**Net: on today's main, with this machine's inputs, NEITHER documented chain
reaches calibration.** Path B stops at its own red pool battery (B3,
`h5_io.py:1119`). Path A gets a clean base but cannot compile a target surface
(F11). The Ledger feed blocks both arms for different reasons — F5 (no
manifest-bearing artifact) in the exact-k arm, F11 (no dimension labels) in the
base-h5 arm.

## Remaining

Write the final report: answer, stage table, gates verbatim, loader result,
questions for Max.
