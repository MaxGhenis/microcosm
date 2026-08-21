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
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:779-805`).
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
four-decimal `0.8461 -> 0.8461` display hid a real stage regression. The live
guard already defines worsening as `post > pre + tolerance` and fails only the
intersection of that condition with a post-stage threshold exceedance
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:613-659`).

## Generating mechanism

A separate read-only bank inspection found:

- 15,228 selected q99.5-tail donors, all with
  `non_sch_d_capital_gains == 0`;
- 23,179 primary-QRF recipient predictions: 805 positive, 22,374 zero, and no
  negative values; and
- selected donors by filing-status code: 2,454 single, 11,994 joint, 508
  separate, and 272 head-of-household.

The allocator currently queues recipients by seeded random order inside filing
status and AGI band, then searches nearest bands
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1520-1556`).
The clone stage writes the selected donor joint vector verbatim, subtracts the
assigned weight from the original recipient, and gives that exact weight to the
clone
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1695-1744`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1779-1812`).
For this zero-valued donor leg, selecting a positive recipient therefore removes
recipient mass while adding zero. Removing below-top-100 mass shrinks the
denominator without shrinking the numerator and produces the measured increase.

The correction must preserve the direct Form-1040 versus Schedule-D reporting
route when selecting a recipient, then rank compatible recipients by their
modeled tax-unit aggregate ST+LT tail value. The two reporting routes are
structurally exclusive on a real return
(`packages/microcosm-build/src/microcosm/build/us_runtime/capital_gain_distributions.py:1-18`),
and the existing frame measurement establishes the correct tax-unit aggregation
for person-grain capital-gains values
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1980-2018`).
This changes the generating assignment mechanism without changing the donor
vectors, threshold, AGI bands, gate, or numerical-noise tolerance.

