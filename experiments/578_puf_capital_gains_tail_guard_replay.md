# PUF capital-gains tail guard checkpoint replay

Date: 2026-08-21  
Pre-fix code: `50a8e240` (documentation-only child of production HEAD
`5abca070`)  
Host checkpoint: `pool.checkpoints/stacked/2e45c4d60f66b4321bc00ffa22816470bf162c59fd91956514832f97e066ed3c`

## Method

The no-build replay loaded the deepest valid `assembled` checkpoint, required
all 47 survey-transfer, one housing-transfer, and 65 primary-QRF target banks to
authenticate, and replaced primary-QRF execution with validation-only bank
loading. It intercepted the comparator immediately after the transfer's raw
pre/post measurement and post-stage absolute gate
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:779-805`
at `5abaf92c`).
The replay disabled bytecode writes, passed no checkpoint writer, fingerprinted
the checkpoint tree and three source inputs before and after, and stopped with a
sentinel at the comparator. All fingerprints were unchanged. Peak root RSS was
3,373,678,592 bytes under a 15,032,385,536-byte (14 GiB) guard.

## Full-precision result

| Measurement | IEEE-754 value |
| --- | ---: |
| Pre-stage top-100 share | `0.84607664843916197` (`0x1.b130f55de9360p-1`) |
| Post-stage top-100 share | `0.84611424753688269` (`0x1.b135e2fbb37c9p-1`) |
| Post minus pre | `3.7599097720719676e-05` (`0x1.3b677291a4000p-15`) |
| Numerical-noise tolerance | `1e-9` |
| Unchanged threshold | `0.75` |

Both sides had 805 positive-mass carriers and 425 distinct carrier values. The
delta is positive by 37,599 times the declared noise tolerance, so the host's
four-decimal `0.8461 -> 0.8461` display hid a real stage regression. At pre-fix
commit `5abaf92c`, the guard defined worsening as
`post > pre + tolerance` and failed only the intersection of that condition
with a post-stage threshold exceedance
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:613-659`
at `5abaf92c`).

## Generating mechanism

A separate read-only bank inspection found:

- 15,228 selected q99.5-tail donors, all with
  `non_sch_d_capital_gains == 0`;
- 23,179 primary-QRF recipient predictions: 805 positive, 22,374 zero, and no
  negative values; and
- selected donors by filing-status code: 2,454 single, 11,994 joint, 508
  separate, and 272 head-of-household.

At pre-fix commit `5abaf92c`, the allocator queued recipients by seeded random
order inside filing status and AGI band, then searched nearest bands
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1520-1556`
at `5abaf92c`).
The clone stage wrote the selected donor joint vector verbatim, subtracted the
assigned weight from the original recipient, and gave that exact weight to the
clone
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1695-1744`
at `5abaf92c`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1779-1812`
at `5abaf92c`).
For this zero-valued donor leg, selecting a positive recipient therefore removes
positive recipient mass while adding zero. The replay establishes that this
unsupported cross-route replacement increased the measured concentration; it
did not record the selected carrier's top-100 rank, so no separate claim about
the numerator is needed.

The correction must preserve the direct Form-1040 versus Schedule-D reporting
route when selecting a recipient, then rank compatible recipients by their
modeled tax-unit aggregate ST+LT tail value. The two reporting routes are
structurally exclusive on a real return
(`packages/microcosm-build/src/microcosm/build/us_runtime/capital_gain_distributions.py:1-18`),
and the existing frame measurement establishes the correct tax-unit aggregation
for person-grain capital-gains values
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2497-2535`).
This changes the generating assignment mechanism without changing the donor
vectors, threshold, AGI bands, gate, or numerical-noise tolerance.

## Corrected mechanism

The implementation derives reporting route and modeled tail order from the
validated tax-unit aggregate of the person-grain capital-gains vector
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1791-1827`).
Its support receipt requires capacity separately for both direct and non-direct
routes inside each filing status
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1891-2008`).
The assignment queue still searches the nearest existing AGI band first, but it
now matches route exactly and orders compatible candidates by descending
modeled ST+LT before the seeded and source-ID tie breakers
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2011-2064`).
The transferred donor joint vector remains verbatim
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2087-2096`).

The guard now records the raw `post - pre` delta, unchanged tolerance and
threshold, raw pre/post threshold flags, and production-gate eligibility as
separate facts. It fails only when the raw delta exceeds the numerical-noise
tolerance, the raw post share exceeds the unchanged threshold, and the post
measurement meets the unchanged 500-carrier production minimum. Thus a thin
raw exceedance is reported without being mislabeled as within threshold, and
an unchanged pre-existing exceedance remains a non-failing receipt
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:610-820`).
The failure text prints pre, post, delta, tolerance, raw threshold, carrier
count, and production minimum with 17-significant-digit shares instead of
making a causal claim from four-decimal displays
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:761-770`).

## Corrected checkpoint replay

The post-fix replay reused the same assembled checkpoint and authenticated all
47 survey-transfer, one housing-transfer, and 65 primary-QRF target banks. QRF
fitting and target-bank writes were replaced with fail-closed sentinels. The
replay applied the already-declared ACS earnings-universe predecessor, finalized
the authenticated banks, loaded the same PUF donor inputs, ran the corrected
tail transfer, and intercepted the comparator result. No build ran.

| Measurement | IEEE-754 value |
| --- | ---: |
| Pre-stage top-100 share | `0.84607664843916197` (`0x1.b130f55de9360p-1`) |
| Post-stage top-100 share | `0.84607664843916197` (`0x1.b130f55de9360p-1`) |
| Post minus pre | `0` (`0x0.0p+0`) |
| Numerical-noise tolerance | `1e-9` |
| Unchanged threshold | `0.75` |

Both measurements again have 805 carriers and 425 distinct values. The guard
receipt reports `pre_existing_over_threshold_not_worsened`, its
`stage_guard_failed` field is false, and the complete list of stage-attributable
failures is empty. The checkpoint tree's size/mtime fingerprint was unchanged.
The 14 GiB live root-RSS guard measured a 3,313,057,792-byte peak over 47.531
seconds and did not fire.

The four guard cases are separate regressions: exact equality, a positive delta
below tolerance, a material positive delta, and an unchanged pre-existing
threshold exceedance with a report entry
(`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:1191-1391`).
An additional thin-sample regression pins raw-over reporting separately from
production-gate eligibility, and manifest tamper cases prove that rehashing
cannot detach stored verdicts from their measured shares/carriers
(`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:838-897`,
`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:1296-1343`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1488-1636`).
Separate assignment regressions require exact reporting-route matching and
modeled-tail-before-seed ordering
(`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:641-811`).
