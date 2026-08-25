# Final report: pkg1 PUF collectibles concentration share

## Outcome

Implementation commit `f1ad8128` fixes the fresh 1% failure without clamping,
threshold tuning, or changing sign doctrine. The failure was not division of
signed sums and not an upstream negative collectibles total. It was floating
reduction order: the top-100 numerator and full denominator contained the same
19 positive weighted magnitudes but summed them in different orders.

One shared disjoint top/remainder reduction now makes the subset relation
structural across the raw frame comparator, shared production gate, and tail
distribution receipt. The exact fresh checkpoint regression, corrected
no-build replay, complete admissible suite, static checks, and three independent
reviews are green. No pool build ran and nothing was pushed.

## Exact checkpoint reproduction

The read-only replay used stacked checkpoint
`f80593d730bedafc652b6d6b0bbee462f7fac97d3cfd555b9b9e526e5dfcab6e`,
assembled identity
`5394c11e947380ece2070e1c1657161009626975665e25efd3e01050913c7faf`,
and primary-QRF identity
`d5d71f37fd312c2740461134121e2b0de28a101e4f655369d439994c3fc4d4e5`.
It authenticated all 65 QRF targets, finalized their stored draws, ran the tail
transfer, and reached the same validator exception without fitting, writing, or
building. The full method and input identities are in
`experiments/578_puf_collectibles_concentration_replay.md`.

The offending receipt was **pre-stage** collectibles; post-stage was valid:

| Side | carriers | top-100 numerator | denominator | share |
| --- | ---: | ---: | ---: | ---: |
| pre | 19 | `7754874867.9770155` (`0x1.ce39fff3fa1dbp+32`) | `7754874867.9770136` (`0x1.ce39fff3fa1d9p+32`) | `1.0000000000000002` (`0x1.0000000000001p+0`) |
| post | 202 | `8754318797.3040924` (`0x1.04e626e6a6ec8p+33`) | `8758134936.3790798` (`0x1.0503444c3085bp+33`) | `0.99956427491666788` (`0x1.ffc6e37e08b9bp-1`) |

The pre numerator exceeds its denominator by
`1.9073486328125e-06`. All 19 values and weights are positive, and there are
15 distinct carrier values. Since `top_k=100`, both operands contain exactly
the same 19 `abs(value) * weight` terms. The old code summed the denominator in
frame order and the numerator after reordering the terms, producing a two-ULP
mass difference and one-ULP ratio overshoot. The strict manifest validator was
right to reject the impossible share
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1569-1575`).

The replay authenticated build-log SHA-256
`91e9a106eec431e6c203a76c1ef1aca5893ab0fdb8422e78630d41c89e3602cb`
and collectibles-target SHA-256
`f61f823125b057370404eb9000e58bed8eb404adb5559da4c2608e6baf1435c9`.
Its complete 123-input fingerprint was unchanged before and after. Peak RSS was
3,108,896,768 bytes.

## Root-cause and sign adjudication

The concentration computation already forms weighted absolute mass for every
column, including signed columns
(`packages/microcosm-build/src/microcosm/build/gates.py:2514-2526`,
`packages/microcosm-build/src/microcosm/build/gates.py:2588-2603`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:632-649`).
Its numerator and denominator therefore cannot cancel positive and negative
legs. The fresh six-component audit confirms that only the all-carrier
collectibles reduction escaped `[0,1]`:

| Component | Pre +/− | Post +/− | Pre share | Post share |
| --- | ---: | ---: | ---: | ---: |
| long-term before response | 1,523/0 | 4,230/11 | `0.86013552154801576` | `0.58669767611870127` |
| collectibles | 19/0 | 202/0 | `1.0000000000000002` | `0.99956427491666788` |
| non-Schedule-D | 805/0 | 805/0 | `0.84607664843916197` | `0.84607664843916197` |
| short-term | 1,522/1 | 2,699/1,145 | `0.86215761523487267` | `0.71053093985728166` |
| short-term + long-term | 1,523/1 | 4,249/1 | `0.85971569008878168` | `0.60066468966945119` |
| unrecaptured section 1250 | 149/0 | 951/0 | `0.99998025879168606` | `0.95160284772377746` |

Collectibles itself is source-enforced nonnegative: the PUF detail carry rejects
negative E24518 values, and QRF finalization declares and clips the output
nonnegative
(`packages/microcosm-build/src/microcosm/build/us_runtime/capital_gain_details.py:112-148`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_support.py:369-403`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_support.py:1939-1945`).
The fresh target bank had 36 positive, 23,143 zero, and zero negative raw draws;
the finalized pre-stage frame had 19 positive and zero negative carriers. A
negative collectibles total would be an upstream contract violation, but none
exists here.

The battery separately checks positive/negative incidence and conditional
absolute-magnitude quantiles by sign leg
(`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:12352-12415`).
Pooled weighted-absolute-mass concentration asks a different but compatible
question: whether a few records dominate total magnitude across both signs.
It already prevents cancellation, so neither signed-net division nor new
per-sign concentration thresholds is warranted.

## Fix

The common helper partitions finite nonnegative carrier masses into disjoint
top and remainder sets, sums each set once, and constructs the denominator as
`top_mass + remainder_mass`
(`packages/microcosm-build/src/microcosm/build/gates.py:2650-2689`). With
nonnegative partial sums, `top_mass <= total_mass` is true by construction. If
the top set contains every carrier, the remainder is zero and numerator and
denominator reuse the same binary64 sum, producing exact `1.0`. Nonfinite or
overflowed totals fail closed. No clamp or numerical tolerance is involved.

All three audited concentration sites now use that helper:

- the shared tail concentration gate
  (`packages/microcosm-build/src/microcosm/build/gates.py:2595-2603`);
- raw pre/post frame receipts
  (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:641-649`); and
- tail distribution receipts
  (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2724-2726`).

Receipt shape and intended weighted-absolute-mass semantics did not change, so
the manifest/control schema was not bumped. A bump would incorrectly invalidate
the authenticated QRF prediction bank even though this correction occurs only
in downstream receipt arithmetic. Threshold `0.75`, top-k 100, minimum carriers
500, worsening tolerance `1e-9`, AGI bands, seeds, folds, and reviewed
exclusions are unchanged.

## Regression and corrected replay

The regression embeds all 19 fresh-checkpoint values and weights bit-for-bit in
source order. It pins the legacy numerator, denominator, and ratio hexadecimal
values; requires exact `1.0` rather than `pytest.approx`; covers every one of the
six manifest columns; passes the sealed receipt validator; and exercises mixed
signs through the raw, shared-gate, and distribution paths
(`packages/microcosm-build/tests/test_us_puf_capital_gains_tail.py:1489-1616`).

The corrected full tail replay of the same authenticated checkpoint passed:

| Side | top mass | constructed total | share |
| --- | ---: | ---: | ---: |
| pre | `7754874867.9770136` (`0x1.ce39fff3fa1d9p+32`) | identical | exactly `1.0` (`0x1.0000000000000p+0`) |
| post | `8754318797.3040943` (`0x1.04e626e6a6ec9p+33`) | `8758134936.3790798` (`0x1.0503444c3085bp+33`) | `0.99956427491666811` (`0x1.ffc6e37e08b9dp-1`) |

The sealed manifest validated with digest
`ad5432d3a7c614419fba8aa442ef156d5441c1e1173f2b68036f63767a818e49`.
The 121-file/295,172,085-byte checkpoint fingerprint remained
`59f998b384801ada06b9434e94f4a358d2424e3cf7192b48eecddcf485ef2d1c`.
Runtime was 12.2643 seconds and peak RSS was 2,587,181,056 bytes. No fit, pool
build, checkpoint write, or source mutation occurred.

## Verification

The complete 263-file tracked test manifest ran in fresh per-file processes
under a 14 GiB root-RSS guard:

| Package | Files | Result | Peak root RSS (bytes) |
| --- | ---: | ---: | ---: |
| microcosm-build | 226 | 5,673 passed, 37 skipped | 7,028,719,616 |
| microcosm-calibrate | 9 | 201 passed | 432,570,368 |
| microcosm-data | 8 | 275 passed, 1 skipped | 11,850,612,736 |
| microcosm-fit | 6 | 125 passed | 411,074,560 |
| microcosm-frame | 14 | 294 passed, 36 skipped | 4,849,188,864 |
| **Total** | **263** | **6,568 passed, 74 skipped, 0 failures/errors** | — |

Manifest SHA-256 is
`f6e949d9813a614da9a3916a37c1dd8071b392d21cac7d8e06bed233becd0d64`;
receipt SHA-256 is
`e0cfce598cac7b5d5d8fcd64c7f11d4958e8877f3463c3292ced49bc85398287`.
Maximum accepted RSS was 11,850,612,736 bytes, below both the 14 GiB guard and
15 GiB task ceiling.

Exactly two previously documented mounted full-donor cache probes were
deselected because they cannot run below the memory ceiling:
`test_cached_full_donor_matches_pinned_household_support` and
`test_cached_full_donor_matches_locked_response_and_weight_facts`. Every other
test in both files passed. These are the only suite exclusions.

Tracked-file Ruff, Ruff formatting over all changed Python files,
`uv lock --check`, and `git diff --check` pass. Three independent reviews found
no blocking issue; review additionally passed randomized size/range partition
properties and verified every checkpoint fixture float bit-for-bit.

## Host handoff

The serial host queue should rerun the prohibited-in-lane 1% build from
implementation commit `f1ad8128` or the later report-only tip. The existing
primary-QRF checkpoint is reusable because its predictions and identity
semantics did not change. Expected behavior is that pre-stage collectibles
seals as exactly `1.0`, post-stage remains below one, and manifest validation
continues past the failure reported in the supplied build log.
