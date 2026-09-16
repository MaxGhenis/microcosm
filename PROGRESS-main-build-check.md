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

Phase 1 complete pending final report. Lineage reconstructed, all 14 entry
points smoked, inputs pinned, both deliverables written to the lanes dir.

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

1. Finish inputs inventory (sha256 pins) and resource estimate.
2. Write `BUILD-PLAN-main.md` and `out-main-can-build-map.md` to the lanes dir.

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
