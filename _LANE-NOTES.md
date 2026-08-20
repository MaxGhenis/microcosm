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
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:11517-11533,11952-12023,12075-12113`).
- The transferred artifact is generated per predictor-availability pattern by
  a deterministic chained QRF fit/draw; predictors enter the donor and
  recipient model frames at the fit call
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1438-1581,1606-1775,1991-2088`).

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
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:181-212,438-467`;
  `packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:1918-1952,7750-7760,8512-8524`).
- Removal-only resolves early `person/puf_tax_itemization` to employment,
  self-employment, household-head, and tenure predictors. Broad-addition-only
  retains baseline employment, self-employment, social-security, retirement,
  household-head, and tenure predictors, then appends the 14 synthesized
  non-veteran predictors. Predictor order is part of the availability-pattern
  seed identity
  (`1a8ad451:packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:151-167,374-403`;
  `539e415:packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:191-212,438-467`;
  `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1991-2016,3569-3578`).
- Every other early family keeps its realized baseline surface. The late PUF
  transfer receives no explicit predictor set, preserving its legacy contract
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:8512-8524`).

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
  (`1a8ad451:packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:374-403`).
- Explicit sets are normalized with exact entity/family coverage and direct
  target-overlap rejection, then selected in declared order for ordinary and
  banked fits
  (`1a8ad451:packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1031-1145,1375-1590,1949-1996,2495-2570`).
- The early gap-fill call forwards the authority-bound declaration, while the
  post-PUF call still supplies no `predictor_sets` argument and therefore keeps
  the legacy execution contract
  (`1a8ad451:packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:1696-1701,1820-1870,2210-2230,7746-7762,8509-8522`).

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
  suite-green.

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

### Snapshot

- Broad-addition-only is committed at
  `539e415defb27bf103a40081239f123ce9d76c6d`.

## 2026-08-19 — f001 wiring proof and measurement disposition

### Static f001 wiring proof

- The pre-input configured identity binds the six configured input hashes,
  `sample_fraction`, fraction token, sample seed, clone controls, and the full
  stacked authority. Its canonical digest selects a non-mixing checkpoint
  namespace
  (`tools/build_us_multispine_pool.py:1031-1040,1150-1178`).
- The stacked authority serializes each direction's ordered predictor sets and
  seals their canonical component digests
  (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:2211-2240,2426-2455,3335-3461`).
- At exact `f001`/seed `578`, removal resolves to the four optional predictors
  employment, self-employment, household head, and tenure. Its authority SHA
  is `16892c623844c21955ddcd4b39b829613db749b195922cbe2b5337aeb8c4cbdd`,
  gap-fill-plan SHA is
  `6ad7b75b193950cfb273daa1660df7e94440cc24e0806963bff5c333a94b0fdd`,
  and configured namespace digest is
  `490866d5bfdc5981e6ff376375f0d414ed3800bb7c81abb98d27d41128f26549`.
- At the same controls, broad resolves to the declared 20 optional predictors,
  retaining Social Security and retirement and adding exactly the 14 reviewed
  non-veteran features
  (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:191-212,438-467`).
  Its authority SHA is
  `7f6eab189fa51627c4e78c3cfcd2517f723a909d9197e538fbfec888261d564a`,
  gap-fill-plan SHA is
  `642646981e96fe67cc29e687a8a8362691bcc571c5c491426243e836f16202d6`,
  and configured namespace digest is
  `adce8ee394cc2315422c00f3cc2838a866215e3a6ff90cb79a55b68c7a6c4c95`.
- This proof is deliberately pre-input: the CLI computes that identity before
  verifying/loading inputs and discovering an authenticated resume
  (`tools/build_us_multispine_pool.py:4138-4221`). It proves exact f001 wiring
  and cache separation, not a materialized artifact, gate verdict, or check
  value.

### Sixteen-check disposition

- The official f025 before values and exact check IDs are recorded in
  `experiments/retirement_factorial/ASSIGNED_CHECKS.md`: 16 BLOCKER/FAIL rows,
  comprising 9 incidence and 7 QED criteria across 11 physical legs.
- No cold f001 build was launched. The historical f001 stage receipt records
  84,729,479,168 bytes peak RSS, so a run through the same cold path would
  knowingly violate this lane's `<15 GiB` rule. Removal and broad after values
  are therefore `NOT_RUN_RSS_CAP / not measured` for every check; no measurable
  improvement is claimed.
- A guard kill would be an aborted measurement, not evidence. The owner must
  first demonstrate a memory-safe build/resume path, then populate the exact
  rows from authenticated artifacts without changing any comparator or frozen
  control.

### Owner handoff

- `experiments/retirement_factorial/OWNER_25PCT_CHARTER.md` pins both arm SHAs,
  all six source paths/hashes, the frozen Phase-P configuration, a strictly
  serial off-chain protocol, and a 14 GiB fail-closed process-tree guard.
- The charter explicitly forbids a cold 25% launch until the memory-safe
  prerequisite is demonstrated. It never passes a Logbook predecessor digest
  and never reads or writes `logbook-pending-chain.txt`.
