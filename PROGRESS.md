# Progress: D0-10 design-v2 parity restoration

## State

Implementation complete and verification in progress as of 2026-08-26 on
`parsimony-qrf-only`. This lane restores only the late-recipient
positive-unemployment-compensation weeks rule and the canonical
`max_targets_per_fit` validation guard required by design v2 §4.1. The #742
margin-calibration removal remains absent.

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
- Restored the canonical `gap_fill_stacked_spine` width guard verbatim and its
  original focused regression test.
- Re-anchored the weeks rule directly after late QRF transfer: the original ACS
  clone-0 mutable mask and positive-UC allowed mask now clear only disallowed
  positive draws to exact `0.0`, followed by the original terminal error check.
  No margin matching, calibration spec, receipt, schema, authority, or regime
  evidence was restored.
- Added focused evaluator and terminal-mutation coverage for the weeks rule.
- Passed touched-file Ruff and the three focused D0-10 regressions (3 passed).

## Next

1. Run the complete weeks-specific and stacked-transfer test files.
2. Run repository-wide Ruff and the full test suite, sharded only if memory
   requires it.
3. Write the final evidence to `out.md`, complete this journal, and commit the
   verification report.

## Historical prior lane

The margin-calibration-removal journal that previously occupied this file was
complete on 2026-08-26. Its final state is preserved at commit `2d973984`; it
is not current guidance for this parity-restoration lane.
