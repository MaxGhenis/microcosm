# Lane: can main's live code build a US dataset from raw sources? (Phase 1: map + smoke)

Worktree `~/PolicyEngine/_worktrees/microcosm-main-build-check`, detached at
`origin/main` `51c3143829b88382270f5af0714ae28fba14f803`. Started 2026-09-15.
**No push, no branches, no stash, no publishing, no Hugging Face writes, no
full build in this phase.** Local commits on detached HEAD only.

Deliverables live OUTSIDE the repo (root `out.md` and root `PROGRESS.md` are
tracked files owned by other lanes — see CLAUDE.md "Root journals are history"):
- `~/PolicyEngine/_recovered/scratch-backup/893/lanes/BUILD-PLAN-main.md`
- `~/PolicyEngine/_recovered/scratch-backup/893/lanes/out-main-can-build-map.md`

## State

Phase 1 complete pending the verification pass + final report. Lineage
reconstructed, all 14 entry points smoked, inputs pinned, both deliverables
written to the lanes dir.

**2026-09-15 23:14 — the lane restarted and the subfleet wrapper truncated the
`-o` path `out-main-can-build-map.md` to 0 bytes.** Content was salvaged from
the prior session's transcript (`88061ab5-…jsonl`, the `cat > … <<'OUTEOF'`
heredoc at record 612 plus the critic patch at record 643) and replayed;
the file is back at 503 lines and byte-identical to what was lost.
`BUILD-PLAN-main.md` was never at the `-o` path and survived intact (457 lines).
A restart-proof copy now lives beside it as
`out-main-can-build-map.SALVAGED-COPY.md`. **Lesson: never let the only copy of
a lane deliverable sit at the `-o` path.**

## Done

- Verified HEAD = `51c3143829b88382270f5af0714ae28fba14f803`, tree clean.
- `uv sync --all-packages --locked --extra us` → rc 0. Venv is Python 3.14.4.
- Pinned the environment main's lock actually produces:
  - policyengine-us **1.819.0**
  - policyengine-core **3.31.0**
  - spm-calculator **0.3.1** (transitive via pe-us). NOTE: an earlier entry in
    this file said "policyengine-us-spm-calculator ABSENT" — that was a
    wrong-package-name query; no such distribution exists. The real package is
    `spm-calculator`, it IS installed, and four pe-us variable modules import
    it. The certified enrichment used spm_calculator **1.0.0**.
  - numpy 2.4.6, torch 2.12.0, scikit-learn 1.8.0, pandas 3.0.3
- Noted `tools/_legacy/` contains exactly one module:
  `build_us_acs_multispine_base.py`.

## Next

**2026-09-15 23:24 — the `-o` path was truncated a SECOND time** (subfleet
retried the lane after `max@policyengine.org` hit a hard limit; see
`out-main-can-build-map.lane.log`). Restored again from
`out-main-can-build-map.SALVAGED-COPY.md`; sha256
`a5d51dfd98a4b4df06f2a1e5f49042338a3a36960f0d59be6f30fa7161505391` on both.
The verification pass launched by `be0067bb0` never executed — the lane died at
launch. Relaunched 23:3x as workflow `wf_c0567a59-9a2` (9 verify dimensions →
adversarial second opinion on every non-CONFIRMED check → completeness critic).
Script: `.../workflows/scripts/verify-build-lane-deliverables-wf_c0567a59-9a2.js`.

Both deliverables are written and restored. A 9-dimension adversarial
verification pass is running over every load-bearing claim in both of them
(engine/constraints, tool source + line numbers, graph + git archaeology,
inputs on disk incl. recomputed sha256, July lineage receipts, resource
receipts, smoke re-runs, completeness-vs-brief, plan executability), each
non-confirmed finding getting an adversarial second opinion. Remaining: fold
the surviving corrections into both deliverables, then final report.

## Open questions for Max

(collected in the out.md deliverable as questions with options)

## Findings so far (2026-09-15)

### Lineage — Build P was NOT built where the brief assumed
- `_buildp-runtime/donor/` **downloaded** Build P on 2026-08-13 via
  `fetch_donor.sh` (`hf_hub_download` of `policyengine/populace-us`, revision
  `populace-us-2024-buildp-sparse-rmloss100-cae8640-20260728T011454Z`). That
  directory is a *consumer* of Build P for the ACS-local overlay, not its
  build site.
- The real build site is `_buildo-runtime` (263 GB), scripts
  `scripts/buildp_staged_base.sh` and `scripts/buildp_sparse9.sh`.
- Build P ran on microcosm `cae8640f9e65e274aea65c7916cb37b956978e32`
  (2026-07-27 21:14 EDT), an ancestor of today's HEAD and **1,468 commits
  behind** it. The base stage pinned `ffe2f04`.
- Manifest confirms: `built_at 2026-07-28T03:56:03Z`, pe-us `==1.764.6`,
  core `==3.26.11`, `elapsed_through_calibration_seconds 2800.57`,
  **`total_build_seconds 8161.06`** (~2h16m for the release stage alone).
- `selection_source.mode = frozen_support`, `kind = reselection` over a prior
  base — so **Build P was itself not a from-raw-sources build**; it reselected
  over a base-m-derived support.
- Ledger feed used: `consumer_facts_buildn_v9_4.jsonl`, 37,405 rows,
  sha256 `b3c0835631a446eb96aa84d86f3ee962d15ca356174c7114db52974f1cacc080`.

### The July chain used the LEGACY arm
`build_us_multispine_pool.py` was **not** in the Build P chain. July ran:
`build_us_puf_support_base.py --stage all` (raw ASEC/PUF/ACS -> base H5) then
`build_us_fiscal_refresh_release.py --base-h5 ... --selection-source-manifest ...`.
Today main documents `--base-h5` as legacy and `--pool-manifest` as the
current arm.

### Flag survival: 1 of 34 Build P flags is gone
All Build P flags still exist on main except **`--zero-support-exclusions`**,
removed 2026-08-21 by `1e5f75e50` ("refactor(us): make target membership
scale-invariant", -66 lines from the tool). The zero-support gate itself
remains and is now **unwaivable**.

### Smoke: all 14 entry points execute on main
`--help` rc=0 for all 10 primary tools plus 4 geography/manifest tools.
Argument-validation smokes reach each tool's own `main()` validation logic
(not import errors), proving the code paths still execute under today's lock.

### Newly discovered required prerequisites (not in the brief's candidate list)
- `build_us_puf_support_base.py` **requires** `--block-ladder-artifact`
  (from `tools/build_us_block_ladder_artifact.py`) or explicit
  `--without-block-ladder` (microcosm #275).
- `build_us_multispine_pool.py` **requires** `--puma-ladder` +
  `--congressional-district-vintage-crosswalk` and both sha256 pins.

### No dry-run surface anywhere
No US build tool exposes `--dry-run`, `--smoke`, `--preflight-only`, or
`--check-only`. The only sampling levers are `--max-households`,
`--asec-max-households`, and `--sample-fraction`/`--sample-seed`.

### `--pool-release-id` does NOT require a publish
`publication_run_id` is a local `uuid.uuid4().hex` written by
`build_us_multispine_pool.py`; `build_us_multispine_pool.py` makes no network
calls. fiscal_refresh only asserts the operator-supplied id matches the
manifest. No Hugging Face round trip is implied.

## Deliverables written (2026-09-15)

- `~/PolicyEngine/_recovered/scratch-backup/893/lanes/BUILD-PLAN-main.md` (452 lines)
- `~/PolicyEngine/_recovered/scratch-backup/893/lanes/out-main-can-build-map.md` (478 lines)

### Additional verified findings

- **Graph executor is absent from the US chain.** Zero `tools/build_us_*.py`
  import `microcosm.graph`. The only production `run_graph` caller is
  `tools/build_uk_frs_spine.py`. Brief correction: the node graph merged in
  **#836** (`90293e0a`, 2026-09-02), not #847.
- **Main cannot load its own certified default dataset.** The certified default
  declares pe-us `>=2.0.0,<2.3`; microcosm-data's `us` extra caps at `<2` and
  `loader.py:437` fail-closes on the mismatch.
- **Path B has never produced a full-scale artifact**, on any commit or machine:
  f025 measured 9.6-14 h; f100 exceeded a 24 h cap twice on a 16-CPU/330-GB box.
- **`build_us_fiscal_refresh_release.py` defaults `--base-h5` to a Hugging Face
  download**, so the no-argument path is a refresh of a published dataset, not a
  from-scratch build.
- **Two CD crosswalks are needed**: Path A uses `383a6666…`; the stacked pool
  hard-pins `c7cb040b…` (`build_us_multispine_pool.py:363-365`) and rejects the
  other. Both are on disk. The PUMA ladder is shared and its on-disk copy
  matches main's `_STACKED_PUMA_LADDER_SHA256` exactly.
- **#893 diff**: at the brief's `2bc6976a8`, only `uv.lock` differs among the
  twelve tool paths — but `packages/` differs by 404 files / 177,595 insertions
  (`us_runtime/` alone 187 files / 96,911). The tools are identical; their
  behaviour is not. The 893 worktree also moved mid-session to `f7bb88525`.
- **`SYSTEM_REQUIREMENTS.md` is structurally stale**: its core memory formula
  describes code deleted 2026-06-25 by `578d2ad59`; measured peak was 85 GB vs
  its projected 29 GB.

### Critic pass — corrections applied

- **The `asec_raw_stage` digest is NOT a gate.** `build_us_multispine_pool.py:960-965`
  verifies it with `_verify_file(..., args.asec_raw_stage_h5_sha256)` —
  self-consistency only. Contrast `:954-959`, which hard-raises when
  `--acs-rent-h5-sha256 != ACS_2022_RENT_ARTIFACT_SHA256`. An earlier draft of
  the report implied the missing pinned artifact could block the pool; corrected.
  Three distinct `asec_raw_stage.checkpoint.h5` files exist on disk
  (653,334,557 / 653,419,922 B) and none matches the `sources.yaml` pin
  (653,410,492 B).
- **`tools/build_us_puf_support_base.py`'s docstring is stale** (lines 1-7 claim
  it "starts from an existing Microcosm US H5") while `:282-288` is a required
  mutually-exclusive `--base-h5 | --asec-h5` group whose `--asec-h5` arm builds
  from raw pooled ASEC. This is the single most load-bearing tool in the
  from-scratch chain, and the stale sentence is plausibly why the chain looked
  broken from outside.
- `tools/ci_test_groups.py --verify` → `verification=ok`, rc 0 on this tree.
- Lane repo footprint: exactly one file (`PROGRESS-main-build-check.md`).
