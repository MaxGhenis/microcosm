# Progress: D0-10 design-v2 parity restoration

## State

Audit complete and implementation in progress as of 2026-08-26 on
`parsimony-qrf-only`. This lane will restore only the late-recipient
positive-unemployment-compensation weeks rule and the canonical
`max_targets_per_fit` validation guard required by design v2 §4.1. The #742
margin-calibration removal remains out of scope for restoration.

The prebuilt `.venv` is present. No dependency sync, network operation, push,
pool/release build, publication, or promotion is in scope.

## Done

- Read `CLAUDE.md` and the GitNexus debugging workflow.
- Confirmed the requested branch, clean starting worktree, local base and
  removal commits, and executable prebuilt environment.
- Established this committed state/done/next journal before modifying code.
- Cross-read D0-10 and its JSON mirror, `bb796cb7..2d973984`, and local
  `origin/main`; upstream and the merge base are byte-identical for both rules.
- Isolated the self-contained canonical gap-fill width guard and its focused
  test. It has no dependency on calibration plumbing.
- Isolated all three parts of the weeks rule: the late ACS mutable allowed-row
  mask in `stacked_spine.py`, the disallowed-positive clamp in the removed
  calibration kernel, and the terminal live-frame validation in
  `stacked_spine.py`. This rule requires a minimal non-calibration re-anchor.
- Inventoried all other deletions into bookkeeping, consequential repins,
  calibration policy/schema/authority/generator, runtime/receipt/evidence,
  tests, and diagnostic-tool categories for reviewer-only reclassification.

## Next

1. Restore the exact gap-fill guard hunk and re-anchor the weeks mutable clamp
   plus terminal live-frame check directly in the late-transfer owner.
2. Restore/add focused guard, weeks reconciliation, and terminal mutation tests.
3. Run Ruff, focused weeks/transfer-guard tests, and the full suite; then write
   the final evidence to `out.md` and commit the completed journal/report.

## Historical prior lane

The margin-calibration-removal journal that previously occupied this file was
complete on 2026-08-26. Its final state is preserved at commit `2d973984`; it
is not current guidance for this parity-restoration lane.
