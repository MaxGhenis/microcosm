# Phase P arm-split lane notes

## Setup and fixed authority (2026-08-17)

- Worktree `/Users/maxghenis/PolicyEngine/_worktrees/microcosm-arm-split` was
  clean on `arm-split-base` at `f71731202b6ff1f0dfa757b6b52aa87ff2a34161`.
- `uv sync --all-packages --extra us` resolved the 118-package lock but the
  sandbox could not reach PyPI. No network operation was attempted afterward.
  The complete lock-identical environment from the read-only predictor-sets
  worktree was copied locally and its five editable paths were rebound to this
  worktree. The lock and root `pyproject.toml` are byte-identical between
  `f7173120` and the rejected branch.
- Comparator: `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/stacked-f025-r1/`,
  stacked identity
  `9be8ecdf82356f38998e8b620ee36d9134f554fe89a8eafd8406f438e2b5aad6`.
- The gate retains round 1's fold seed `20260816`, forest seed `260816`,
  bootstrap seed `8162026`, 2,000 replicates, 256 clusters, five quantiles,
  `[0.8, 1.25]` ratio band, and all forest/missingness settings. Only each
  candidate artifact's authority and target-bank receipt digests may differ.
- Builds are off-chain: no `--logbook-prev-row-digest`, the
  `POPULACE_LOGBOOK_PREV_ROW_DIGEST` environment variable is removed, and the
  global `logbook-pending-chain.txt` is never read or written.

## Round-1 decomposition boundary

The rejected bundle changed more than target order and the two named early
predictor classes. It also made every late transfer execute with the eight-field
PUF tax-detail predictor set. Baseline runtime calls the late transfer without
an explicit predictor set (`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:8420`
at `f7173120`), while `a6893634` passes the new declaration. The round-1 verdict
confirms the executed difference in every late row under
`.oos_pinball_loss[].{baseline,candidate}.predictor_set`; 14 of its 21 money
regressions were late transfers. None of Max's three arm definitions authorizes
that late-PUF swap, so every arm retains the live baseline late-transfer
surface. The synthesis must not assign those 14 bundled regressions to one of
the three early interventions.

## Eligibility observability audit

Read-only source artifact:
`/Users/maxghenis/PolicyEngine/_worktrees/microcosm-predictor-sets/_buildo-runtime/out/stacked-f025-predictor-sets-r1/populace_us_2024_stacked_pool.checkpoints/stacked/5c1c042b4b9e65e9a4114d2c3c850ebdda0933dd48cf5dfa97212164bc4b7305/assembled.checkpoint.h5`.
The ACS recipient mask is `person_support_channel == "acs"` and contains
856,626 rows.

| Raw field | Observed ACS rows | Null ACS rows | Qualifies |
|---|---:|---:|---:|
| `MIL` | 708,870 | 147,756 | no |
| `DEAR` | 856,626 | 0 | yes |
| `DEYE` | 856,626 | 0 | yes |
| `DDRS` | 819,036 | 37,590 | no |
| `DPHY` | 819,036 | 37,590 | no |
| `DREM` | 819,036 | 37,590 | no |
| `DOUT` | 729,029 | 127,597 | no |
| `HINS3` | 856,626 | 0 | yes |

Therefore the eligibility arm admits exactly difficulty-hearing (`DEAR`),
difficulty-seeing (`DEYE`), and own Medicare coverage (`HINS3`). No veteran
predictor is fully observed. The MIL-only dtype harmonization from `cf4530b2`
is not needed in that minimal arm.

## Arm records

Arm implementation, test, build, and gate receipts are appended on the branch
that owns each arm.

## Synthesis continuation (2026-08-19)

- State: synthesize on `arm-split-base` from immutable evidence only: round-1
  bundle verdict commit `df6bd65b`, order verdict commit `9d6eecb4`,
  eligibility verdict commit `1ffea7ae`, and bounded investment verdict commit
  `5cf6a306`.
- Done: each arm has complete 32-family/118-target/74-money/211-leg evidence;
  each arm's configuration, after removing only its candidate integrity
  binding, hashes to the round-1 value
  `10f29427d83c340973869fb735188967aff9a4eea770b066f604e7a28a0b5e5a`.
  All accepted arm runs stayed below 20 GiB RSS.
- Fixed interpretation: this is full predictor-set attribution, not a
  publication or CHAMPVA project. The synthesis will report CHAMPVA as one of
  all 211 battery legs and will not attribute the bundle-only late-PUF change
  to any of the three isolated arms.
- Fixed boundary: generate only
  `experiments/phase_p_arm_split/SYNTHESIS.md`; do not build, use network, push,
  edit `PROGRESS.md`, or access `logbook-pending-chain.txt`.
- Next: construct the source-qualified 74-target and 211-leg four-way tables,
  derive cautious attribution and landability conclusions, validate every row
  against the four verdicts, then commit the final report.
- Done: `tools/synthesize_phase_p_arm_split.py` authenticates the four verdict
  digests, asserts complete and identical target/leg keys and baselines, asserts
  the frozen normalized configuration, and emits the synthesis deterministically.
  Independent review found exactly 74 unique money rows with 14 cells each,
  211 unique battery rows with 7 cells each, and four clause rows with five
  cells each; every displayed value, diagnostic, stored transition, CI flag,
  source path, and digest matches its verdict.
- Result: order is A FAIL / B PASS / C PASS but all 74 money deltas are exactly
  zero. Eligibility is FAIL / FAIL / FAIL with five significant improvements,
  five significant regressions, and six battery exits. Investment is FAIL /
  PASS / FAIL with three significant improvements, no significant money
  regressions, and three battery exits. No arm improves money without battery
  damage, so there is no F1 bundle handoff.
- Attribution: no isolated arm reproduces the round-1
  `social_security_retirement` blowup. The contrast localizes it to the broad
  bundle predictor replacement or interactions; removal of the direct social-
  security and retirement-income predictors is a next-isolation hypothesis,
  not an identified unique cause. Eligibility reproduces ten bundle transition
  classes, investment reproduces the TANF exit direction, order reproduces no
  crossing, and 24 of 35 bundle crossings remain unassigned to an isolated arm.
- Deliverable: `experiments/phase_p_arm_split/SYNTHESIS.md`, SHA-256
  `a12d7d599ac25493197123347ab73ba1fe00e2dd838009fd0da2f9b4a3eb4215`.
  It includes the exhaustive source-tagged money and battery tables, frozen
  clause table, attribution, explicit no-handoff block with schema field names,
  and evidence-driven next experiments.
- State: synthesis complete. Next: stop; the owner adjudicates.
