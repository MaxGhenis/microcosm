# Progress: D0-10 design-v2 parity restoration

## State

Complete as of 2026-08-26 on `parsimony-qrf-only`. This lane restored only the
late-recipient positive-unemployment-compensation weeks rule and the canonical
`max_targets_per_fit` validation guard required by design v2 §4.1. The #742
margin-calibration removal remains absent. Final evidence is in `out.md`.

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
- Passed repository-wide Ruff.
- Passed the complete focused files `test_us_weeks_unemployed.py`,
  `test_us_stacked_spine.py`, and `test_us_multispine_pool_tool.py`: 436 passed,
  1 skipped.
- Passed the full suite in five memory-safe package shards: build 6,425 passed
  and 40 skipped; calibrate 203 passed; data 318 passed and 2 skipped; fit 93
  passed; frame 295 passed and 36 skipped. Total: 7,334 passed, 78 skipped.
- Confirmed the removed calibration module remains absent and the only runtime
  and test changes relative to `2d973984` are `stacked_spine.py` and
  `test_us_stacked_spine.py`.
- Wrote the final status, hunks, test evidence, re-anchor deviation, and
  reviewer-only reclassification inventory to `out.md`.

## Next

1. Hand the committed branch and `out.md` to the reviewer. No push, pool or
   release build, publication, or promotion was performed.

## Historical prior lane

The margin-calibration-removal journal that previously occupied this file was
complete on 2026-08-26. Its final state is preserved at commit `2d973984`; it
is not current guidance for this parity-restoration lane.
