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

Phase 1 opened. Environment synced and pinned.

## Done

- Verified HEAD = `51c3143829b88382270f5af0714ae28fba14f803`, tree clean.
- `uv sync --all-packages --locked --extra us` → rc 0. Venv is Python 3.14.4.
- Pinned the environment main's lock actually produces:
  - policyengine-us **1.819.0**
  - policyengine-core **3.31.0**
  - policyengine-us-spm-calculator **ABSENT** (not in the `us` extra)
  - numpy 2.4.6, torch 2.12.0, scikit-learn 1.8.0, pandas 3.0.3
- Noted `tools/_legacy/` contains exactly one module:
  `build_us_acs_multispine_base.py`.

## Next

1. Reconstruct Build P lineage from `~/PolicyEngine/_build[e-p]-runtime/` receipts.
2. Map the from-scratch chain as main defines it today (incl. where
   `microcosm.graph.run_graph` sits, if anywhere).
3. Inventory raw inputs on disk (path/size/sha256); list gated/missing.
4. Smoke every stage entry point (`--help` + smallest supported smoke); record
   rc and first error verbatim.
5. Engine recommendation (1.819.0 lock vs certified 2.2.1 / spm 1.0.0 / core 3.32.5).
6. Resource estimate per stage; write both deliverables.

## Open questions for Max

(collected in the out.md deliverable as questions with options)
