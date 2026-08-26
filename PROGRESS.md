# Progress: D0-10 design-v2 parity restoration

## State

In progress as of 2026-08-26 on `parsimony-qrf-only`. This lane will restore
only the late-recipient positive-unemployment-compensation weeks rule and the
canonical `max_targets_per_fit` validation guard required by design v2 §4.1.
The #742 margin-calibration removal remains out of scope for restoration.

The prebuilt `.venv` is present. No dependency sync, network operation, push,
pool/release build, publication, or promotion is in scope.

## Done

- Read `CLAUDE.md` and the GitNexus debugging workflow.
- Confirmed the requested branch, clean starting worktree, local base and
  removal commits, and executable prebuilt environment.
- Established this committed state/done/next journal before modifying code.

## Next

1. Derive the exact two removed hunks from `bb796cb7..2d973984`, cross-read the
   local `origin/main` versions, and inventory every other removal for the
   reviewer-only reclassification list.
2. Restore only the two D0-10 parity items, adding or restoring focused tests
   where the original hunks require them.
3. Run Ruff, focused weeks/transfer-guard tests, and the full suite; then write
   the final evidence to `out.md` and commit the completed journal/report.

## Historical prior lane

The margin-calibration-removal journal that previously occupied this file was
complete on 2026-08-26. Its final state is preserved at commit `2d973984`; it
is not current guidance for this parity-restoration lane.
