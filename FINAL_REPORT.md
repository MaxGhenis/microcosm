# Final report: pkg1 PUF capital-gains tail guard

## Outcome

Implementation commit `8422cb15` fixes both the real transfer regression and
the guard's attribution semantics. The checkpointed 1% inputs did contain a
material increase hidden by the four-decimal error text; after the route-aware
assignment fix, a no-build replay is bit-identical pre/post and the unchanged
over-threshold state is reported without failing.

No numeric gate/comparator control, AGI band, seed, or fold was tuned. No host
build ran in this lane. The serial host queue should rerun the 1% build from
`8422cb15` or the later docs-only branch tip.

## Full-precision checkpoint reproduction

The supplied assembled checkpoint was replayed without fitting, checkpoint
writes, or a build:

| Measurement | Value | IEEE-754 hex |
| --- | ---: | --- |
| Pre-stage top-100 share | `0.84607664843916197` | `0x1.b130f55de9360p-1` |
| Pre-fix post-stage share | `0.84611424753688269` | `0x1.b135e2fbb37c9p-1` |
| Post minus pre | `3.7599097720719676e-05` | `0x1.3b677291a4000p-15` |

The increase is about 37,599 times the unchanged `1e-9` numerical-noise
tolerance, so it was real rather than exact equality or a rounding artifact.
Both measurements had 805 carriers and 425 distinct values. The replay
authenticated all 47 survey-transfer, 1 housing-transfer, and 65 primary-QRF
target banks; before/after checkpoint fingerprints were unchanged. Peak root
RSS was 3,373,678,592 bytes.
The full reproducibility receipt is in
`experiments/578_puf_capital_gains_tail_guard_replay.md`.

## Generating mechanism and correction

Input inspection found that all 15,228 selected tail donors had zero
`non_sch_d_capital_gains`, while the recipient predictions contained 805
positive and 22,374 zero values for the direct-route leg. In the pre-fix tree, recipient
assignment keyed filing status and nearest AGI band but then used seeded order
without the donor's reporting route
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1520-1556`
at `5abaf92c`). The clone stage then transferred the selected donor joint vector
into the chosen recipient-weight slice
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1695-1812`
at `5abaf92c`). That allowed a zero-direct-leg non-direct-route donor to replace
a positive direct-route recipient. The direct Form-1040 and Schedule-D reporting
routes are structurally exclusive on a real return
(`packages/microcosm-build/src/microcosm/build/us_runtime/capital_gain_distributions.py:1-18`).

The correction derives route and modeled ST+LT order from the validated
tax-unit aggregate of all person-grain capital-gains values
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1791-1827`).
Support is now sufficient only when each filing-status/reporting-route stratum
has enough recipients
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1891-2008`).
Within the unchanged nearest-AGI-band search, the allocator selects only the
matching route and prioritizes the largest modeled ST+LT tail value before the
existing seeded/source-ID ties
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2011-2064`).
The donor joint vector remains donor-owned and is copied verbatim
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2087-2096`).

A corrected replay of the same authenticated checkpoint inputs measured pre and
post as exactly `0.84607664843916197`, with delta `0`, 805 carriers, and 425
distinct values. It emitted
`pre_existing_over_threshold_not_worsened`, returned no stage-attributable
failure, did not modify the checkpoint tree, and peaked at 3,313,057,792 bytes.

## Guard semantics

The guard now measures raw finite positive weighted absolute mass for every
column before applying the production minimum-carrier eligibility rule
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:610-654`).
It records pre/post shares, delta, carriers, distinct values, raw threshold
flags, production eligibility, the material-worsening verdict, and an explicit
classification. It fails only when all three facts are true:

1. `post - pre > 1e-9`;
2. raw post-stage share is above the unchanged `0.75` threshold; and
3. post-stage carriers meet the unchanged 500-record production minimum.

Those controls remain top-k 100, threshold `0.75`, minimum 500, and tolerance
`1e-9`
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:81-83`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:601-605`).
The complete disposition and full-precision public failure message are derived
from the measurements
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:657-820`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:940-972`).
Thus equal and sub-tolerance increases pass; an eligible material increase over
threshold fails; an unchanged pre-existing exceedance is a non-failing report;
and a structurally thin raw exceedance remains visible but production-gate
ineligible.

Manifest schema 3 stores this attribution receipt, and validation recomputes
every boolean and classification from the sealed shares and carrier counts
instead of trusting stored verdict text
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:76-83`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1030-1036`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1488-1636`).
Both pool routes execute the shared transfer, so the legacy semantic checkpoint
identity also binds the current tail schema/support contract while omitting only
the stacked late-producer schedule
(`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:10492-10500`,
`tools/build_us_multispine_pool.py:958-1002`,
`tools/build_us_multispine_pool.py:2388-2407`,
`tools/build_us_multispine_pool.py:3844-3897`).

## Regression coverage and verification

Dedicated tests cover equal pre/post, a sub-tolerance increase, a real eligible
increase, and an unchanged pre-existing over-threshold state
(`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:1191-1293`).
Additional tests bind route preservation, route-specific support, multi-person
tax-unit aggregation, modeled-tail ordering, persisted non-failure reporting,
the exact public failure text, and rehashed receipt-tamper rejection
(`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:641-897`,
`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:1346-1442`).

Final-tree guarded test receipts:

| Package | Result | Peak root RSS (bytes) |
| --- | ---: | ---: |
| microcosm-frame | 294 passed, 36 skipped | 6,527,254,528 |
| microcosm-fit | 125 passed | 417,792,000 |
| microcosm-calibrate | 201 passed | 466,321,408 |
| microcosm-data | 275 passed, 1 skipped | 12,270,026,752 |
| microcosm-build | 5,672 passed, 37 skipped | 7,022,198,784 |
| **Total** | **6,567 passed, 74 skipped, 0 failures/errors** | — |

The build sweep used 226 fresh per-file processes. Its manifest SHA-256 is
`855d762df4e85fd40df7ff299d444ec5f13d43111d25d731bee1bef73cef79d6` and
receipt SHA-256 is
`67b18e5af01d1ed68134911a0f02449a7dedc8c316fa3da6f16b6a62b53afc22`.
Exactly two mounted-cache probes were deselected:
`test_cached_full_donor_matches_pinned_household_support` and
`test_cached_full_donor_matches_locked_response_and_weight_facts`.

One non-accepted attempt to run the first 3.73 GB cache probe alone crossed from
below its sampled cutoff to 17,501,945,856 bytes before the monitor terminated
it. It violated the lane memory order, produced no accepted test evidence, and
was not retried; the second probe reads the same source and was not attempted.
All accepted replays and suites stayed below 15 GiB. Tracked-file Ruff and
`git diff --check` passed.

## Host handoff

The serial host owner should rerun the prohibited-in-lane 1% build from
implementation commit `8422cb15` (or the docs-only final branch tip), using the
unchanged threshold/band/gate configuration. Expected guard evidence for the
replayed failing column is a full-precision non-failing entry with pre = post =
`0.84607664843916197`, delta `0`, and classification
`pre_existing_over_threshold_not_worsened`.
