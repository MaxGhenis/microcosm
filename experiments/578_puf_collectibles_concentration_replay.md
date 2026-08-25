# PUF collectibles concentration checkpoint replay

Date: 2026-08-25  
Code: `c5cf548af2063f583ae41be52d4ff7c4ce012078`  
Host checkpoint:
`pool.checkpoints/stacked/f80593d730bedafc652b6d6b0bbee462f7fac97d3cfd555b9b9e526e5dfcab6e`

## Method and identity

This was a read-only replay, not a pool build. It loaded the authenticated
assembled checkpoint with its bound frame metadata, ran the deterministic CPS
predictor and ACS earnings-universe preparation steps, attached the configured
full PUF support clone (`fraction=1.0`, `seed=578`), authenticated all 65
primary-QRF target checkpoints, and finalized their stored raw draws. It then
loaded the SHA-bound PUF donor, ran the capital-gains tail transfer with the
configured seed, and invoked the production receipt validator. No model was
fitted and no checkpoint or output was written.

The replay authenticated these identities:

- build log SHA-256
  `91e9a106eec431e6c203a76c1ef1aca5893ab0fdb8422e78630d41c89e3602cb`;
- stacked checkpoint identity
  `f80593d730bedafc652b6d6b0bbee462f7fac97d3cfd555b9b9e526e5dfcab6e`;
- assembled identity
  `5394c11e947380ece2070e1c1657161009626975665e25efd3e01050913c7faf`
  and H5 SHA-256
  `8bd7fdc6c22a5f50ced2582eb537f2b702a87df2972fcbad29d3e4b6ac195e81`;
- primary-QRF identity
  `d5d71f37fd312c2740461134121e2b0de28a101e4f655369d439994c3fc4d4e5`,
  manifest-file SHA-256
  `3e5657f483013efaa11669d8e5d967557c94913c192989dd9b999c59be924edb`,
  and collectibles target SHA-256
  `f61f823125b057370404eb9000e58bed8eb404adb5559da4c2608e6baf1435c9`;
- donor H5 SHA-256
  `7669f5b5281f20080e77204f9bd4aabfad0aa101fa283e22caf9ba8d61d4d6df`,
  source CSV SHA-256
  `0a7fd643edb1acc55c507db795914b41d232922be78c149b58d111f4672499df`,
  and loaded donor-table SHA-256
  `cab8f65b0e091656501a1d497a30ad11ad3f75b77fc035ed78751e6316bb0187`.

The complete 123-input size/content fingerprint was identical before and after:
`7bfe3293d731ac3d5ba650582452c6b20815ce6e7bae3c2f41ca6625fc0d89a1`
(738,145,898 bytes). The full tail replay took 15.28 seconds and peaked at
3,108,896,768 bytes RSS, below 15 GiB.

## Exact failure

The offending receipt is the **pre-stage**
`long_term_capital_gains_on_collectibles` share. The post-stage share is valid.
All quantities below are IEEE-754 binary64 values printed with 17 significant
digits and hexadecimal form.

| Side | carriers | numerator | denominator | share |
| --- | ---: | ---: | ---: | ---: |
| pre | 19 | `7754874867.9770155` (`0x1.ce39fff3fa1dbp+32`) | `7754874867.9770136` (`0x1.ce39fff3fa1d9p+32`) | `1.0000000000000002` (`0x1.0000000000001p+0`) |
| post | 202 | `8754318797.3040924` (`0x1.04e626e6a6ec8p+33`) | `8758134936.3790798` (`0x1.0503444c3085bp+33`) | `0.99956427491666788` (`0x1.ffc6e37e08b9bp-1`) |

The pre-stage numerator exceeds the denominator by exactly
`1.9073486328125e-06`. All 19 carrier values and all 19 weights are positive;
there are no negative collectibles values and 15 distinct carrier values.
Because 19 is below `top_k=100`, the numerator and denominator contain the
same 19 weighted magnitudes. The only difference is reduction order: the
numerator sorts descending before summing, while the denominator sums in frame
order (`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:637-645`).
The resulting two-ULP mass difference becomes a one-ULP ratio overshoot, which
the manifest validator correctly rejects
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:1572-1578`).

## All-component sign and share audit

Every numerator and denominator below sums `weight * abs(tax-unit value)`.
Signs are carrier-value incidence, not the ratio's arithmetic. The only invalid
share is the pre-stage collectibles reduction.

| Component | Pre +/− | Post +/− | Pre share | Post share |
| --- | ---: | ---: | ---: | ---: |
| `long_term_capital_gains_before_response` | 1,523/0 | 4,230/11 | `0.86013552154801576` | `0.58669767611870127` |
| `long_term_capital_gains_on_collectibles` | 19/0 | 202/0 | `1.0000000000000002` | `0.99956427491666788` |
| `non_sch_d_capital_gains` | 805/0 | 805/0 | `0.84607664843916197` | `0.84607664843916197` |
| `short_term_capital_gains` | 1,522/1 | 2,699/1,145 | `0.86215761523487267` | `0.71053093985728166` |
| `short_term_plus_long_term_capital_gains` | 1,523/1 | 4,249/1 | `0.85971569008878168` | `0.60066468966945119` |
| `unrecaptured_section_1250_gain` | 149/0 | 951/0 | `0.99998025879168606` | `0.95160284772377746` |

## Root-cause and semantic adjudication

This is not division of signed sums. The raw comparator explicitly defines
mass as `abs(value) * weight`, and the shared battery gate documents and uses
the same weighted-absolute-mass definition for signed columns
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:632-645`,
`packages/microcosm-build/src/microcosm/build/gates.py:2514-2526`,
`packages/microcosm-build/src/microcosm/build/gates.py:2595-2605`). The signed
short-term, long-term, and combined vectors have valid magnitude shares, so
negative-leg cancellation is already excluded.

Collectibles itself is a rare nonnegative component within a vector that also
contains signed legs. The archived PUF carry rejects negative E24518 values
(`packages/microcosm-build/src/microcosm/build/us_runtime/capital_gain_details.py:132-148`),
and QRF finalization declares and clips the collectibles output nonnegative
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_support.py:369-403`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_support.py:1939-1946`).
The fresh target bank has 36 positive, 23,143 zero, and zero negative raw
draws; the finalized pre-stage frame has 19 positive and zero negative
collectibles carriers. There is therefore no upstream negative-total defect to
repair and no reason to replace concentration with a signed net ratio or new
per-sign thresholds.

The generating defect is numerical construction: three sites independently
sum a selected top set and its containing full set in different orders. Besides
the failing raw receipt, the same latent assumption appears in the shared tail
gate (`packages/microcosm-build/src/microcosm/build/gates.py:2595-2605`) and the
tail distribution receipt
(`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2733-2740`,
`packages/microcosm-build/src/microcosm/build/us_runtime/puf_capital_gains_tail.py:2771-2772`).
The honest correction is one common weighted-absolute-mass reduction: partition
the carriers into disjoint top and remainder sets, sum each set once, and form
the denominator as `top_mass + remainder_mass`. It constructionally preserves
`numerator <= denominator`; when every carrier is in the top set, numerator and
denominator are the same float and the share is exactly one. This is the same
declared mathematical measure, not a clamp, tolerance, threshold change, or
sign-policy change.
