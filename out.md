# Parsimony lane final report

Date: 2026-08-26
Branch: `parsimony-qrf-only`
Base: `origin/main` at `bb796cb7`

## Outcome

The PR #742 post-draw calibration layer is removed end to end. Mutable US
transfer values now leave the ordinary regime-gated QRF transfer path without
carrier-prevalence prefix selection or five-quantile amount remapping; weight
calibration remains the sole downstream adjustment surface.

The implementation diff excluding this report is 35 files, 186 insertions, and
7,907 deletions. Repository Ruff, the canonical spec/evidence checks, and all
five CI-parity pytest shards pass. No pool/release build, calibration run,
publication, push, network access, dependency install, or packaging change was
performed.

Checkpoint verdict: **NO, the existing candidate-25 QRF/transfer checkpoints
are not valid for supported reuse on this branch.** The raw ACS bank payloads
are pre-calibration QRF draws, but every supported lookup authenticates them
under the full stacked authority. Removing the authority component advances
v11 to v12, changes the base digest/namespace, and causes old identities to be
bypassed or rebuilt. On the timing alternatives supplied in the task, candidate
2 therefore follows the cold approximately 13-hour path, not the approximately
1-hour warm path.

## Diff summary by file

### Journal and changelog

- `PROGRESS.md` — maintains the requested state/done/next journal from lane
  initialization through verified completion and records the checkpoint verdict.
- `changelog.d/742-us-post-transfer-calibration-policy-spec.added.md` — removes
  the now-false unreleased fragment that announced the deleted policy.
- `changelog.d/us-late-transfer-calibration.removed.md` — records removal of the
  two-part `late_transfer` adjustment in the repository's `removed` convention.

### Spec, authority, and generated evidence

- `docs/evidence/spec-engine/us-f0-coverage.json` — regenerates the F0 proof for
  92 fewer authored policy fields, eight authority components, and the moved
  spec/seed/authority/checkpoint identities.
- `packages/microcosm-build/src/microcosm/build/spec_engine/field_usage.py` —
  removes the policy pointers from the closed F0 ledger and canonically re-pins
  exact counts and the imputation-model pointer inventory.
- `packages/microcosm-build/src/microcosm/build/spec_engine/inventory_coverage.py`
  — removes the calibration authority item and re-pins the source-attested seed,
  stacked-authority, checkpoint-base, and authority-component evidence.
- `packages/microcosm-build/src/microcosm/build/spec_engine/schema/imputation.schema.json`
  — removes required `post_draw_calibration` fields and the complete policy
  schema definition.
- `packages/microcosm-build/src/microcosm/build/spec_engine/stacked_authority_semantics.py`
  — stops projecting and digesting the deleted policy as a stacked-authority
  component.
- `packages/microcosm-build/src/microcosm/build/us/spec/battery.yaml` — advances
  the stacked authority binding monotonically from version 11 to version 12.
- `packages/microcosm-build/src/microcosm/build/us/spec/imputation.yaml` — removes
  the authored two-part policy and its target declarations.
- `tools/spec_engine_coverage.py` — re-pins the regenerated exact pointer ledger.
- `tools/us_bundle_generation/imputation.py` — removes generation of the policy
  payload and its insertion into the QRF model declaration.

### Runtime and operational tools

- `packages/microcosm-build/src/microcosm/build/us_runtime/post_transfer_calibration.py`
  — deletes the entire implementation, specs, prefix schedule, identity,
  application API, and receipt validator.
- `packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py` —
  removes calibration imports, authority/application sites, candidate-row and
  regime-evidence plumbing, receipt requirements, and live replay diagnostics;
  retains independent target-surface, row-count, aggregate, bank, and DAG gates.
- `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py` —
  removes calibration-only regime evidence and the exported carrier-candidate
  helper, while retaining the unrelated Schedule-D/adult-care structural repair
  and inlining the qualifying mask used by that repair.
- `packages/microcosm-build/src/microcosm/build/us_runtime/acs_multispine.py` —
  removes the serializer exception for deleted `target_regimes` provenance.
- `tools/build_us_multispine_pool.py` — removes the parallel receipt serializer
  accommodation for deleted regime evidence.
- `tools/audit_us_post_transfer_child_support_checkpoints.py` — deletes the
  calibration-specific child-support checkpoint audit.
- `tools/reproduce_us_post_transfer_weeks_checkpoint.py` — deletes the
  calibration-specific weeks-unemployed reproducer.

### Tests

- `packages/microcosm-build/tests/test_imputation_lineage_spec.py` — removes the
  code/spec identity assertion for the deleted policy.
- `packages/microcosm-build/tests/test_spec_engine_country_bundles.py` — re-pins
  BE/UK envelopes moved by the shared source-attested seed inventory; no BE/UK
  implementation or authored spec changed.
- `packages/microcosm-build/tests/test_spec_engine_coverage_tool.py` — updates
  exact field/mode/effect totals after deleting 92 policy pointers.
- `packages/microcosm-build/tests/test_spec_engine_field_usage.py` — updates the
  exact F0 field-ledger totals and uniqueness assertion.
- `packages/microcosm-build/tests/test_spec_engine_inventory_coverage.py` —
  updates the authority component count from nine to eight.
- `packages/microcosm-build/tests/test_spec_engine_legacy_adapter.py` — re-pins
  the generation-zero stacked-authority digest.
- `packages/microcosm-build/tests/test_spec_engine_loader.py` — re-pins the
  source-attested loader semantic golden.
- `packages/microcosm-build/tests/test_spec_engine_stacked_authority_semantics.py`
  — removes the component assertion and re-pins the eight-component authority.
- `packages/microcosm-build/tests/test_us_acs_multispine.py` — removes the
  calibration-only regime-evidence serialization case.
- `packages/microcosm-build/tests/test_us_acs_transfer.py` — removes
  calibration regime-selection/helper tests while retaining normal transfer and
  deterministic reconciliation coverage.
- `packages/microcosm-build/tests/test_us_multispine_pool_h5_io.py` — removes
  calibration-owner content from canonical late-transfer receipt fixtures.
- `packages/microcosm-build/tests/test_us_multispine_pool_tool.py` — removes
  calibration fixtures, constraints, tamper cases, and checkpoint mutations;
  preserves generic receipt, target, aggregate, transition, and checkpoint gates.
- `packages/microcosm-build/tests/test_us_post_transfer_calibration.py` — deletes
  the dedicated 1,195-line layer test module.
- `packages/microcosm-build/tests/test_us_spec_bundle.py` — removes calibration
  identity expectations; authored SHA fields again represent asset pins only.
- `packages/microcosm-build/tests/test_us_spine_blindness.py` — removes the
  deleted module from the source-blind runtime graph and re-pins 69 to 68 modules.
- `packages/microcosm-build/tests/test_us_stacked_spine.py` — removes layer-only
  fixtures/application/tamper/authority cases, advances v12 stale-version
  coverage, and preserves independent accounting, QRF-bank, checkpoint, and DAG
  tests.

## Canonical identity movement

The repository's generators and fail-closed attestation tests, rather than
unreviewed hash substitution, produced and checked these values:

- US `spec_sha256`: `84f55c520fec17651e750a698dd2ae2343e6a20e54743081aca4fcbed66d72cf`
- BE `spec_sha256`: `02b80d544556b83737c7866b82353176a5abb61b73d63c50d43ca1837e93b2a4`
- UK `spec_sha256`: `cbdb471edc6a15c0b22e3bc20990a3beee2becff30d743b99676d0711fb9eb61`
- seed protocol: `9f96e9c64e8738c7a5aa87924072bc9e843a0e69b4522f17ccffd0266310e70b`
- compiled seed map: `e4b18f21d35ddceb54cec9c91017b3a8e027c413917f982f68e2a4012927e9fe`
- stacked authority: `ea4caa8c0d678b1485d640ca472eed55f0705aafc7ee4d940628977dfec04a53`
- full checkpoint base: `9e2ed8a1882bb863475c83486bfbc284c6ce842b73081935ab87ee2d90131643`
- loader semantic golden: `30bbedd2b4daccf913e558bddc2eb15c8e1cb7c26cad74c60d5f970673a2c60d`
- F0 ledger: 32,259 authored + 9,769 resolved = 42,028 fields;
  41/41 inventory checks covered.

Canonical commands, both final exit 0:

```text
UV_CACHE_DIR=/private/tmp/microcosm-parsimony-uv-cache uv run --no-sync python tools/generate_us_bundle_from_constants.py --check
US bundle spec_sha256=84f55c520fec17651e750a698dd2ae2343e6a20e54743081aca4fcbed66d72cf

UV_CACHE_DIR=/private/tmp/microcosm-parsimony-uv-cache uv run --no-sync python tools/spec_engine_coverage.py --check
spec-engine coverage: 42028/42028 configuration fields; 41/41 inventory checks
```

## Checkpoint reuse analysis

Verdict: **NO.** Candidate 1's `candidate-25/pool/checkpoints` namespace is not
a valid checkpoint source for candidate 2 under the supported runtime.

1. The authority itself is deliberately versioned: v12 removes the post-draw
   policy and v11 bound it (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:1692-1695`).
   The authority receipt returns both the versioned identity and its digest
   (`stacked_spine.py:3332-3341`, `stacked_spine.py:3470-3485`).
2. The complete authority is embedded in the pool checkpoint base identity
   (`tools/build_us_multispine_pool.py:1345-1451`, specifically line 1397) and
   the pre-discovery configured identity (`tools/build_us_multispine_pool.py:1454-1471`,
   specifically line 1470).
3. That configured identity is SHA-hashed into `stacked/<digest>`
   (`tools/build_us_multispine_pool.py:1474-1483`). `main` computes and selects
   this root before checkpoint discovery (`tools/build_us_multispine_pool.py:5197-5200`,
   `tools/build_us_multispine_pool.py:5213-5234`), so the old v11 directory is
   not selected. Discovery also recomputes the complete identity and rejects a
   mismatched manifest as stale (`tools/build_us_multispine_pool.py:1539-1548`).
4. Every pool-stage identity spreads the entire base identity before adding the
   stage/index (`tools/build_us_multispine_pool.py:1978-1988`), and stage loads
   require exact equality, returning `identity_mismatch` otherwise
   (`tools/build_us_multispine_pool.py:2411-2448`).
5. Per-target banks route through digest-derived `primary-qrf/<digest>` and
   `acs-transfer/<digest>` directories (`tools/build_us_multispine_pool.py:697-711`),
   and sibling directories with other identities are explicitly bypassed
   (`tools/build_us_multispine_pool.py:715-760`). Gap-bank and late-group
   identities inherit the full transferred-stage identity
   (`tools/build_us_multispine_pool.py:3289-3297`,
   `tools/build_us_multispine_pool.py:3300-3319`), including at late-bank
   construction (`tools/build_us_multispine_pool.py:3726-3740`).
6. `AcsTransferTargetBankStore` normalizes and hashes the complete supplied
   identity (`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer_bank.py:57-75`),
   requires exact embedded equality (`acs_transfer_bank.py:171-187`), and
   reports/rebuilds mismatches (`acs_transfer_bank.py:394-424`).
7. Primary-PUF QRF is also bound to the base digest: routing is computed at
   `tools/build_us_multispine_pool.py:3693-3699` and lines 3722-3725, inserted
   into the late-resource binding at lines 3765-3777, and checked against the
   checkpoint directory basename at
   `packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:10205-10216`.

The nuance does not change the verdict: ACS banks store exact raw chained draws
(`acs_transfer.py:1412-1427`), produced directly by `fit_draw_next` and
checkpointed before calibration (`acs_transfer.py:1598-1648`; write path
`acs_transfer_bank.py:258-278`). The repository provides no content-only
compatibility path. Copying or relabeling those bytes would evade the declared
identity contract and was deliberately not attempted.

## Complete `post_transfer|late_transfer` reference disposition

Command audited after implementation and before adding this self-referential
report:

```text
git grep -n -i -E 'post_transfer|late_transfer' -- . ':!out.md'
```

Result: **390 hits across 28 tracked files**. Classification totals are 356
ordinary late-transfer QRF producer/DAG/resource/checkpoint hits (A), 30
deterministic post-transfer structure/reconciliation hits unrelated to the
deleted calibration (B), four journal/changelog history hits (H), and **zero
missed calibration-layer hits**.

Every hit is accounted for below. Line lists are exact at the report commit.

- `PROGRESS.md` — H: 6, 19, 51.
- `changelog.d/us-late-transfer-calibration.removed.md` — H: 1.
- `docs/us-multispine-operator-ordering.md` — A: 687, 721, 728.
- `packages/microcosm-build/src/microcosm/build/spec_engine/imputation_semantics.py`
  — B: 165, 199, 201, 221, 223, 237; A: 437, 980, 1123, 1651.
- `packages/microcosm-build/src/microcosm/build/spec_engine/resolver.py` — A:
  983, 986, 1051.
- `packages/microcosm-build/src/microcosm/build/spec_engine/schema/geography.schema.json`
  — B: 43 (`legacy_post_transfer`, a geography-order enum).
- `packages/microcosm-build/src/microcosm/build/spec_engine/schema/imputation.schema.json`
  — B: 348, 676; A: 1785, 2105, 2124.
- `packages/microcosm-build/src/microcosm/build/spec_engine/stacked_authority_semantics.py`
  — A: 316, 569.
- `packages/microcosm-build/src/microcosm/build/spec_engine/typed_closure.py` —
  A: 202, 274.
- `packages/microcosm-build/src/microcosm/build/us/spec/imputation.yaml` — B:
  319. The other 176 are A, grouped without omission:
  - producer `kind`: 14499, 15476, 16434, 17453, 18490, 19518, 20546, 21544,
    22512, 23470, 24478, 25446, 26404, 27382, 28380, 29338, 30296, 31254,
    32221;
  - model-config input/effective bindings: 14854, 14857, 15822, 15825, 16780,
    16783, 17799, 17802, 18836, 18839, 19864, 19867, 20892, 20895, 21890,
    21893, 22858, 22861, 23816, 23819, 24824, 24827, 25792, 25795, 26750,
    26753, 27728, 27731, 28726, 28729, 29684, 29687, 30642, 30645, 32042,
    32045, 33063, 33066;
  - target-bank input/effective bindings: 14863, 14866, 15831, 15834, 16789,
    16792, 17808, 17811, 18845, 18848, 19873, 19876, 20901, 20904, 21899,
    21902, 22867, 22870, 23825, 23828, 24833, 24836, 25801, 25804, 26759,
    26762, 27737, 27740, 28735, 28738, 29693, 29696, 30651, 30654, 32051,
    32054, 33072, 33075;
  - person model-config resource IDs: 15450, 16409, 17421, 18458, 19486,
    20514, 21515, 22486, 23445, 24448, 25420, 26379, 27355, 28351, 29313,
    30271, 31229;
  - model-config resource kinds: 15454, 16413, 17425, 18462, 19490, 20518,
    21519, 22490, 23449, 24452, 25424, 26383, 27359, 28355, 29317, 30275,
    31233, 32200, 33212;
  - person target-bank resource IDs: 15456, 16415, 17427, 18464, 19492,
    20520, 21521, 22492, 23451, 24454, 25426, 26385, 27361, 28357, 29319,
    30277, 31235;
  - target-bank resource kinds: 15460, 16419, 17431, 18468, 19496, 20524,
    21525, 22496, 23455, 24458, 25430, 26389, 27365, 28361, 29323, 30281,
    31239, 32206, 33218;
  - non-person resource IDs: 32196, 32202, 33208, 33214;
  - late ownership terminology: 33252, 33261, 33309, 33405, 33501.
- `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py` — B:
  269, 581, 1066, 1102, 1126, 1127, 1128.
- `packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py` — A:
  193, 206, 207, 3846, 4226, 4227, 4248, 4545, 4566, 4610, 5573, 5586,
  5611, 5617, 5623, 5631, 5638, 5643, 5656, 5665, 5670, 5674, 5679,
  5683, 5709, 5786, 5789, 5791, 5801, 5803, 6683, 6699, 7168, 7648,
  7664, 7670, 7671, 7672, 8521, 9317, 9334, 9355, 9489, 9520, 9557,
  9559, 9628, 9631, 9684, 9689, 9691, 9704, 9706, 9798.
- `packages/microcosm-build/src/microcosm/build/us_runtime/us_late_overlap_ownership.py`
  — A: 116, 145, 192.
- `packages/microcosm-build/src/microcosm/build/us_runtime/us_late_producer_registry.py`
  — B: 1182, 1184, 1194; A: 71, 93, 94, 95, 155, 156, 1172, 1174,
  1177, 1179, 1393, 1398, 1399, 1406, 1418, 1422, 1494, 1741, 1889,
  1893, 1936, 2001, 2087, 2100, 2101, 2122, 2124.
- `packages/microcosm-build/tests/test_imputation_lineage_spec.py` — A: 20,
  47, 103, 108.
- `packages/microcosm-build/tests/test_spec_engine_identity_contracts.py` — A:
  29, 52.
- `packages/microcosm-build/tests/test_spec_engine_imputation_semantics.py` — A:
  40, 176, 178, 181.
- `packages/microcosm-build/tests/test_spec_engine_loader.py` — B: 331.
- `packages/microcosm-build/tests/test_spec_engine_resolver.py` — A: 153, 363.
- `packages/microcosm-build/tests/test_us_acs_transfer.py` — B: 1994.
- `packages/microcosm-build/tests/test_us_late_producer_dag.py` — A: 51, 59,
  344, 353, 390, 424, 654, 891, 903, 904, 939, 940, 1180, 1351.
- `packages/microcosm-build/tests/test_us_multispine_pool_h5_io.py` — A: 774,
  793, 809, 881, 883, 975.
- `packages/microcosm-build/tests/test_us_multispine_pool_tool.py` — A: 1048,
  1063, 1152, 1213, 1216, 1219, 1652, 1658, 2642, 2647.
- `packages/microcosm-build/tests/test_us_spec_bundle.py` — B: 779; A: 370,
  750, 856.
- `packages/microcosm-build/tests/test_us_stacked_spine.py` — B: 4228; A:
  3127, 4180, 4181, 4184, 4198, 4199, 4200, 4212, 4240, 4245, 4920,
  5008, 5106, 5115, 5118.
- `tools/build_us_multispine_pool.py` — A: 228, 3740.
- `tools/us_bundle_generation/identity_contracts.py` — A: 25, 108.
- `tools/us_bundle_generation/imputation.py` — B: 714, 715, 723, 727,
  749, 764; A: 63, 649, 652, 935, 942, 943, 973, 1085, 1227, 1237,
  1345, 1924, 2020, 2288, 2290.

An additional case-insensitive hyphenated sweep (`post-transfer|late-transfer`)
found 49 hits across 14 files (48 locations not already above). All are also
accounted for: H at `PROGRESS.md:1`, `_698-SOL-REVIEW.md:208`, and
`changelog.d/578-pool-stage-checkpoints.added.md:2`; B at documentation lines
50/920/1026, `engine_abi.py:87`, `imputation_semantics.py:201/204/206/214/224`,
`acs_transfer.py:312/435`, `multispine_pool.py:350/606/1596/2852`,
`test_us_acs_multispine.py:70`, and generator lines 701/716/750; A at
documentation lines 298/384/440, `imputation_semantics.py:1128/1136`,
`resolver.py:1055`, `stacked_spine.py:3817/7186/8466/8519/8524/9337/9365/9370/9377/9399/9404/9438/9784`,
registry lines 5/119/327, pool-tool test line 2650, and generator lines
977/994/1090/1098.

Zero-hit deleted-symbol sweep:

```text
POST_TRANSFER_CALIBRATION_SPECS
PostTransferCalibrationSpec
PostTransferCalibrationResult
PostTransferCalibrationFrameResult
post_transfer_calibration_policy_identity
post_transfer_calibration_spec
post_transfer_calibration_spec_for_target
calibrate_post_transfer_values
apply_post_transfer_calibration
validate_post_transfer_calibration_receipt
_apply_stacked_post_transfer_calibrations
addition_candidate_rows
target_regimes
regime_evidence_targets
acs_adult_care_qualifying_rows
```

Broad co-occurrence searches for transfer plus calibration terminology found
only the current progress journal and removal changelog. Carrier-prevalence,
prefix-selection/schedule, five-quantile-mapping, and addition-candidate residue
searches were empty. Remaining generic `CALIBRATION_SUMMARY_*` names belong to
the separate weight-calibration spec surface.

## Verification evidence

The default uv cache location is outside the writable sandbox. The first setup
attempt emitted `error: Failed to initialize cache at
/Users/maxghenis/.cache/uv ... Operation not permitted`; every recorded command
thereafter used the local, non-network cache override
`UV_CACHE_DIR=/private/tmp/microcosm-parsimony-uv-cache` with `--no-sync`.

Final required checks:

| Check | Exit | Result |
|---|---:|---|
| `uv run --no-sync ruff check .` | 0 | `All checks passed!` |
| `uv run --no-sync pytest packages/microcosm-build` | 0 | 6,422 passed, 40 skipped, 1,973 warnings in 3,955.42s |
| `uv run --no-sync pytest packages/microcosm-calibrate` | 0 | 203 passed, 2 warnings in 30.82s |
| `uv run --no-sync pytest packages/microcosm-data` | 0 | 318 passed, 2 skipped in 12.56s |
| `uv run --no-sync pytest packages/microcosm-fit` | 0 | 93 passed, 1 warning in 42.92s |
| `uv run --no-sync pytest packages/microcosm-frame` | 0 | 295 passed, 36 skipped, 1 warning in 129.04s |

Aggregate: 7,331 passed, 78 skipped, zero failures. The warnings are existing
numeric/runtime, pandas chained-assignment, sparse-tensor beta, optional-core,
and fragmented-frame warnings; no new warning category was introduced by this
deletion.

Focused migration evidence included full passes for the surviving stacked-spine
test file and the H5/pool-tool receipt/checkpoint subsets. Expected anti-rot
failures were used as the canonical re-pin mechanism and then eliminated. The
material diagnostic excerpts were:

```text
AssertionError: build_us_multispine_pool.py must reach the pinned 69-module runtime graph; reached 68
configuration field count changed: expected 42120, got 42028
imputation_models: stale pointer claim; expected 96/e4d6b6b747fcec1c027e0f1c2d1905274c0426217a61383b02e75baadb93db4d, got 4/93d4b493904c7318725feb66dc594bba4eef7cdd73fc983397572414d45ce6a8
```

The first focused group initially reported `1 failed, 562 passed`; the 68-module
pin rerun passed. The complete anti-rot group initially reported `5 failed, 106
passed` (authored/coverage totals, BE envelope, UK envelope, and loader golden),
then the exact seven-test failure rerun reported `7 passed`. Inventory oracles
also explicitly reported the moved seed protocol/map, stacked authority, and
full checkpoint base before their canonical values were accepted. There are no
unresolved failures.

`git diff --check` passes. Packaging/dependency files are unchanged, so the
conditional wheel build and clean-venv install/import gate in `CLAUDE.md` was
not triggered.

## Judgment calls and deliberate non-actions

- I treated `late_transfer` as the established 19-group, 70-target producer
  phase, not as a synonym for the deleted calibration. Those DAG/resource/bank
  contracts remain intact.
- I retained `post_transfer_structure`, `_apply_post_transfer_structure`,
  Schedule-D reconstruction, adult-care carrier reconciliation, and
  `legacy_post_transfer` geography ordering. They are deterministic structural
  repairs/ordering that predate or are independent of the two-part draw skew.
- I retained target-set closure, per-target row counts, aggregate reconstruction,
  transfer-bank identity, execution transition, and checkpoint receipt gates.
  Only requirements whose sole producer was the deleted calibration layer were
  removed.
- I advanced authority version 11 to 12 rather than rolling back to 10, retaining
  monotonic stale-version protection. I did not bump either materializer version:
  the changed authority is already an explicit complete identity component and
  demonstrably changes the namespace/digests.
- I removed the unreleased “policy added” changelog fragment and replaced it
  with a `removed` fragment so release notes do not claim both states.
- BE/UK envelope goldens legitimately moved because the shared seed attestation
  hashes the edited US ACS transfer source. No UK spec/runtime/test behavior was
  changed.
- GitNexus graph tools were unavailable, so I used repository-native `rg`,
  `git grep`, history, import-graph tests, and exact identity constructors as the
  analysis fallback.
- Deliberately untouched: `packages/microcosm-fit/src/microcosm/fit/qrf.py`, all
  `packages/microcosm-calibrate/**`, UK runtime/spec code, all gate thresholds,
  bands, folds, seeds, losses, and packaging/dependency metadata.
- Deliberately not done: no manual checkpoint migration/relabeling, sampler
  skew, pool/release build, candidate scoring, calibration, publication, push,
  network operation, or dependency sync/install.

## Commit ledger

- `7f9292723cb95174c256440ffd4a8afafba13e21` — Start late-transfer parsimony lane
- `ba47c785a93ca3f8c1766717abb2efcc7120f591` — Remove post-transfer calibration runtime
- `902ac41f59a8f37418dcb82307c02777b6a9b0f3` — Remove late-transfer calibration tests
- `dc6e2d8282ba18a566a79d66c1c05508852e8e70` — Re-pin spec identities after calibration removal
- `6b57d0d7e8677f6739021cc9c3a874bc4af294fb` — Record parsimony lane verification
- `SELF` — Write parsimony lane final report (this commit; its concrete SHA is
  necessarily obtained with `git rev-parse HEAD` because a commit cannot contain
  its own hash)

The report commit includes the final completed `PROGRESS.md` state. The final
handoff checks require `git status --short` to emit no lines and
`git diff --check` to exit 0.
