# Retirement factorial lane notes

## 2026-08-19 — lane start

### State

- Branch/worktree: `battery-retirement-factorial` in the named retirement
  worktree, clean from `origin/main` at `164027e2`.
- Assigned outcome: two minimal early-PUF factorial arms plus 1% wiring proof,
  16-check measurements, and an owner-run 25% charter. This lane will not run
  a 25% build or publish/push anything.
- Frozen controls: sample fraction `0.01`, sample seed `578`, and existing
  bands, thresholds, seeds, folds, target order, and comparators. Builds are
  off-chain and must not pass `--logbook-prev-row-digest` or touch
  `logbook-pending-chain.txt`.

### Evidence read before implementation

- The synthesis isolates the unresolved treatment as loss of
  `__acs_transfer_social_security_income` and
  `__acs_transfer_retirement_income` versus simultaneous broad additions; it
  prescribes removal-only and broad-addition-only arms
  (`experiments/phase_p_arm_split/SYNTHESIS.md:346-352,376-380` in the read-only
  arm-split worktree).
- The assigned 16 BLOCKER checks all use the monetary sign-separated battery:
  weighted carrier incidence is compared to the fixed inclusive ratio band,
  and supported legs use weighted conditional quantiles and fixed QED
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:11860-11930,11990-12021`).
- The transferred artifact is generated per predictor-availability pattern by
  a deterministic chained QRF fit/draw; predictors enter the donor and
  recipient model frames at the fit call
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:896-916,1581-1648`).

### Environment receipt

- `uv sync --all-packages --extra us` first failed because the managed sandbox
  denied the default cache path.
- The exact sync retried with `UV_CACHE_DIR` under `/tmp`; it created `.venv`
  and then failed downloading locked `jinja2==3.1.6` because network/DNS is
  unavailable. No dependency or lockfile was changed.
- A complete baseline suite used the provisioned arm-split interpreter while
  forcing this worktree's five package source roots on `PYTHONPATH`: 6,525
  tests collected, exit 0, expected skips/warnings only. The focused plan/QRF
  chain passed 26 tests in 302.42 seconds. `LOKY_MAX_CPU_COUNT=1` constrained
  child-process parallelism.
- `ruff check .` and `git diff --check` pass. Repository-wide
  `ruff format --check .` has a pre-existing 49-file baseline failure, all
  outside this lane's current changes; no unrelated formatting was applied.

### Resolved treatment boundary

- The global optional predictor declaration must remain unchanged; selecting
  a per-family ordered predictor surface only at the early transfer isolates
  the treatment. The early call is distinct from the late transfer
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:7673-7682,8420-8432`).
- Removal-only resolves early `person/puf_tax_itemization` to employment,
  self-employment, household-head, and tenure predictors. Broad-addition-only
  retains baseline employment, self-employment, social-security, retirement,
  household-head, and tenure predictors, then appends the 14 synthesized
  non-veteran predictors. Predictor order is part of the availability-pattern
  seed identity
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1792-1811,2907-2922`).
- Every other early family keeps its realized baseline surface. The late PUF
  transfer receives no explicit predictor set, preserving its legacy contract
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:8420-8432`).

### Resource finding

- Historical receipts report 84,729,479,168 bytes maximum RSS for an old 1%
  build and 81,026,367,488 bytes for a 25% arm. Both exceed the mandatory
  `<15 GiB` ceiling by a wide margin. A 14 GiB fail-closed guard would correctly
  abort the present cold path, so neither a 1% nor 25% cold build may be
  launched until a memory-safe path or authenticated low-memory resume is
  proven. A guard abort is not experimental evidence.

### Next

- Encode the removal-only early predictor declaration and contract tests,
  prove the early/late wiring boundary, run the suite, and commit the first
  independently runnable factorial snapshot.
