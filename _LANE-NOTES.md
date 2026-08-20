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

- Run the complete suite on the reviewed removal-only tree, then commit the
  first independently runnable factorial snapshot.

## 2026-08-19 — removal-only implementation

### State

- The removal-only snapshot is implemented, independently reviewed, and fully
  suite-green. It is ready for its coherent commit.

### Surgery and mechanism evidence

- `declared_acs_transfer_predictor_sets` removes exactly the Social Security
  and retirement analogues only when the entity is `person` and the family is
  `puf_tax_itemization`; it also omits the already unavailable investment
  feature from every realized early surface
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:374-403`).
- Explicit sets are normalized with exact entity/family coverage and direct
  target-overlap rejection, then selected in declared order for ordinary and
  banked fits
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1031-1145,1375-1590,1949-1996,2495-2570`).
- The early gap-fill call forwards the authority-bound declaration, while the
  post-PUF call still supplies no `predictor_sets` argument and therefore keeps
  the legacy execution contract
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:1696-1701,1820-1870,2210-2230,7746-7762,8509-8522`).

### Verification

- Passed: lineage spec 8, ACS transfer 61, stacked spine 225, late-producer DAG
  30, and focused early/late wiring plus authority tests 17.
- Independent read-only review found a stale v10 checkpoint-identity assertion
  and an extra-empty-entity exact-validation hole. Authority expectation is
  now v11; both transfer and stacked-plan normalization reject the empty extra
  entity, with three focused regressions passing.
- Ruff on every changed Python file and `git diff --check` pass. The frozen
  control scan found no production band, threshold, seed, fold, comparator,
  estimator, or batch-size change.
- The complete removal tree collected 6,535 tests and exited 0, with expected
  skips and pre-existing warnings only. Repository-wide `ruff check .` passes.

### Snapshot

- Removal-only is committed at
  `1a8ad451c6eff17d405ef75cbdd014de72447153`.

## 2026-08-19 — broad-addition-only implementation

### State

- Broad-addition-only is implemented, independently reviewed, and fully
  suite-green. It is ready for its coherent commit.

### Surgery and mechanism evidence

- The early person/PUF optional tuple retains employment, self-employment,
  Social Security, and retirement, then carries exactly 14 reviewed non-veteran
  additions in a fixed 20-column order. Investment remains excluded
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:191-212,438-464`).
- CPS donor materialization declares exactly the 14 canonical predictor
  columns and validates/recode-maps their reviewed ASEC physical sources before
  the early transfer
  (`packages/microcosm-build/src/microcosm/build/us_runtime/cps_carried.py:114-151,160-337,581-741`).
- Recipient materialization decodes only the 11 required retained ACS raw
  columns. Raw decoding is row-scoped to recipients whose entire reviewed
  canonical surface is empty, preventing donor/recipient source semantics from
  being mixed
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_pums.py:72-99`; `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:2199-2488`).
- Twenty optional predictors require non-aliasing availability codes; the
  encoding is now guarded `uint64` and its identity is contract-bound
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:275-278,310-324,1993-2006`).
- Canonical source predictors are explicitly owned, excluded from transfer
  targets, and merged as optional CPS outputs for sparse fixtures
  (`packages/microcosm-build/src/microcosm/build/us_runtime/multispine_pool.py:637-640,728-741,2196-2211,2694-2744`).
- The post-PUF transfer call remains predictor-set-free, so the broad treatment
  does not alter late wiring
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:8512-8524`).

### Verification

- Passed 650 affected checks: 164 source/spec/ACS/PUF support, 296
  multispine/stacked, and 190 plan/pool-tool.
- A separate read-only review approved the exact 20-column order, exactly 14
  non-veteran mappings, source ownership, canonical/raw row fence, uint64
  capacity guard, unchanged late call, and spec mirror with no blockers.
- Ruff check/format, Python compilation, and `git diff --check` pass on the
  broad patch.
- The complete broad tree collected 6,571 tests and exited 0, with expected
  skips and pre-existing warnings only. Repository-wide `ruff check .`, final
  diff hygiene, and the frozen-control scan pass.
