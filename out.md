STATUS: DONE. Design-v2 §4.1 parity is restored for both D0-10 violations, the full test suite and Ruff pass, and the #742 margin-calibration treatment remains removed.

RESTORATION COMMIT SHA: dbd8a657d2545420f5504e097e4c2f84e7002c59.

RESTORED HUNKS: packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:7745 restores the canonical gap-fill guard verbatim. It rejects every max_targets_per_fit value other than DEFAULT_ACS_TRANSFER_MAX_TARGETS_PER_FIT, currently 8.

RESTORED HUNKS: packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:8525 restores the late-recipient weeks structural rule without calibration plumbing. The original ACS clone-0 recipient mask, before-null/after-nonnull mutable mask, and positive-unemployment-compensation allowed mask clear only disallowed positive weeks_unemployed draws to exact 0.0. The rule is applied immediately after raw late transfer at packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:8809.

RESTORED HUNKS: packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:3755 restores the terminal rule that rejects any positive ACS clone-0 weeks_unemployed carrier whose unemployment_compensation is nonpositive.

RESTORED TESTS: packages/microcosm-build/tests/test_us_stacked_spine.py:1687 covers the canonical max_targets_per_fit guard. Packages/microcosm-build/tests/test_us_stacked_spine.py:3135 proves that an ineligible mutable ACS draw is cleared while an eligible draw and producer values are preserved. Packages/microcosm-build/tests/test_us_stacked_spine.py:3241 covers terminal rejection of positive weeks with nonpositive unemployment compensation.

TEST SUMMARY: UV_CACHE_DIR=/private/tmp/microcosm-parsimony-uv-cache uv run --no-sync ruff check . passed. The writable cache override was required only because the sandbox denied access to the default user cache; no sync or installation occurred.

TEST SUMMARY: The three direct D0-10 regression nodes passed, 3 passed. The complete focused files packages/microcosm-build/tests/test_us_weeks_unemployed.py, packages/microcosm-build/tests/test_us_stacked_spine.py, and packages/microcosm-build/tests/test_us_multispine_pool_tool.py passed with 436 passed and 1 skipped.

TEST SUMMARY: The full suite passed in the repository's five memory-safe package shards. microcosm-build had 6425 passed and 40 skipped. microcosm-calibrate had 203 passed. microcosm-data had 318 passed and 2 skipped. microcosm-fit had 93 passed. microcosm-frame had 295 passed and 36 skipped. The total was 7334 passed and 78 skipped.

DEVIATIONS: The max_targets_per_fit guard and its test were restored verbatim. A verbatim weeks hunk revert was impossible because its old allowed-row wiring called the intentionally deleted margin-calibration kernel. The smallest re-anchor places the same masks, disallowed-positive clamp, and terminal rejection directly in the late-transfer owner. This is an implementation-location deviation only; no margin matching, calibration target declarations, calibration schema, calibration authority, calibration receipts, QRF regime evidence, or diagnostic calibration tools were restored.

SCOPE: The removed post_transfer_calibration.py module remains absent. Relative to 2d973984, runtime and test changes are confined to stacked_spine.py and test_us_stacked_spine.py; PROGRESS.md and this report are the only journal changes.

REVIEWER RECLASSIFICATION: Everything else removed by bb796cb7..2d973984 was left untouched. The original whole-path removal census, whose mixed-path counts also include the two D0-10 hunks, comprises nonruntime journal/changelog/report changes, 4 paths and 51 deletions; consequential evidence/inventory/hash/version repins, 11 paths and 52 deletions; calibration policy/schema/authority/generator removal, 4 paths and 467 deletions; calibration runtime/application/receipt/regime-evidence removal, 5 paths and 3695 deletions; associated test removal, 10 paths and 3054 deletions; and two calibration diagnostic tools with 588 deletions.

REVIEWER RECLASSIFICATION: The clearest remaining allowed-versus-parity questions are the removed special_constraint and constraint_masks declarations/schema/authority bindings; the removed public adult-care qualifying-row helper and direct tests even though equivalent reconciliation logic was inlined; the removed calibration-selected QRF regime-evidence and receipt validation; the removed generic special-constraint and coupled-constraint tests; and the semantic coupled-constraint audit portion of the removed weeks checkpoint diagnostic. D0-10 currently classifies those remaining changes as allowed treatment, test/diagnostic-only, or consequential differences and identifies no third source parity violation. This task did not act on them.

No network operation, dependency sync, push, pool or release build, publication, or promotion occurred.
