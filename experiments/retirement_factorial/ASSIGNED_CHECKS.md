# Retirement factorial assigned checks

## Authority and run state

This ledger is an exact extraction of the 16 adjudications whose
`action_group` is `retirement_model_and_data` in the read-only arm-split
`experiments/battery_burndown/adjudication.json`. The baseline is the official
25% (`f025`) gate artifact with SHA-256
`685cad63d4dc62234da72501c5a3ce9ec5a81fcd3f7b412b61474a9c1d8b423b`.
Its adjudication classification is `BLOCKER` for every row, and its criterion
status is `FAIL` for every row.

The two independently runnable treatment snapshots are:

- Removal-only: `1a8ad451c6eff17d405ef75cbdd014de72447153`.
- Broad-addition-only, retaining the baseline Social Security and retirement
  predictors: `539e415defb27bf103a40081239f123ce9d76c6d`.

Neither arm has a 1% measurement. A cold `f001` build was not launched because
the historical 1% receipt records maximum RSS of **84,729,479,168 bytes**, in
direct conflict with this lane's mandatory **less-than-15-GiB** per-process
ceiling. Starting a path already known to exceed that ceiling, or reporting a
memory-guard kill as experimental evidence, would not be a valid measurement.
Accordingly every arm cell below is explicitly `NOT_RUN_RSS_CAP / not measured`;
there is no before/after or improvement claim.

## What the criteria measure

All 16 checks are positive legs of the monetary sign-separated battery. For an
incidence criterion, the value is ACS weighted positive-leg incidence divided
by ASEC weighted positive-leg incidence; the recorded supports are the
unweighted positive-row counts on each origin
([`stacked_spine.py:11969-12003`](../../packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py#L11969-L12003),
[`stacked_spine.py:12075-12079`](../../packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py#L12075-L12079)).
For a quantile criterion, the criterion value is QED: the maximum symmetric
relative distance over the weighted conditional absolute-value quantiles,
evaluated only with adequate nonzero support
([`stacked_spine.py:12004-12023`](../../packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py#L12004-L12023),
[`stacked_spine.py:12082-12110`](../../packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py#L12082-L12110)).
The comparator and its frozen tolerances are declared without widening at
[`stacked_spine.py:11517-11533`](../../packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py#L11517-L11533).

The factorial changes the early PUF family's conditioning columns, which are
selected in declared order and partitioned by recipient availability before
each fit
([`acs_transfer.py:1450-1510`](../../packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py#L1450-L1510),
[`acs_transfer.py:1991-2016`](../../packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py#L1991-L2016),
[`acs_transfer.py:2019-2088`](../../packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py#L2019-L2088)).
The fitted mechanism models `P(targets | predictors)` with deterministic seeded
weighted-bootstrap forests; gated regimes fit a weighted sign classifier and
sign-conditional magnitude forests
([`qrf.py:1006-1030`](../../packages/microcosm-fit/src/microcosm/fit/qrf.py#L1006-L1030),
[`qrf.py:1371-1442`](../../packages/microcosm-fit/src/microcosm/fit/qrf.py#L1371-L1442),
[`qrf.py:1445-1455`](../../packages/microcosm-fit/src/microcosm/fit/qrf.py#L1445-L1455)).

## Exact assigned rows

`f025 criterion value` is the value adjudicated for the named criterion. The
adjacent ratio/QED and incidence/support columns preserve all available
baseline context even when that context is not the row's adjudicated
criterion.

| Ordinal | Full check_id | Criterion | Official status | f025 criterion value | f025 ratio / band | f025 QED | f025 incidence ASEC / ACS | f025 nonzero rows ASEC / ACS | Removal f001 | Broad f001 |
|---:|---|---|---|---:|---|---:|---|---|---|---|
| 7 | `person/model_required_numeric/tax_exempt_private_pension_income[clone_0]/positive#incidence` | incidence | BLOCKER; FAIL | 1.5540575408000976 | 1.5540575408000976 / out_of_band | 0.1042830540037244 | 0.06605645354737383 / 0.10265552975380765 | 6406 / 110336 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 19 | `person/puf_tax_itemization/taxable_private_pension_income[clone_0]/positive#incidence` | incidence | BLOCKER; FAIL | 1.5633139716502966 | 1.5633139716502966 / out_of_band | 0.12389380530973454 | 0.06605645354737383 / 0.10326697674827831 | 6406 / 111027 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 20 | `person/puf_tax_itemization/taxable_ira_distributions[clone_0]/positive#incidence` | incidence | BLOCKER; FAIL | 1.3692265605479346 | 1.3692265605479346 / out_of_band | 0.19679633867276888 | 0.016338573555624365 / 0.022371208873826987 | 1556 / 24373 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 21 | `person/puf_tax_itemization/social_security_retirement[clone_0]/positive#quantile` | quantile (QED) | BLOCKER; FAIL | 0.5399065173295705 | 1.0103361841007599 / in_band | 0.5399065173295705 | 0.15247001254769427 / 0.1540459706672324 | 15440 / 170783 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 22 | `person/puf_tax_itemization/social_security_disability[clone_0]/positive#incidence` | incidence | BLOCKER; FAIL | 0.777259623970176 | 0.777259623970176 / out_of_band | 1.3265580996694013 | 0.018028942069815028 / 0.014013168733764516 | 1935 / 13616 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 23 | `person/puf_tax_itemization/social_security_disability[clone_0]/positive#quantile` | quantile (QED) | BLOCKER; FAIL | 1.3265580996694013 | 0.777259623970176 / out_of_band | 1.3265580996694013 | 0.018028942069815028 / 0.014013168733764516 | 1935 / 13616 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 24 | `person/puf_tax_itemization/social_security_dependents[clone_0]/positive#incidence` | incidence | BLOCKER; FAIL | 1.6270067039916964 | 1.6270067039916964 / out_of_band | 1.255813953488372 | 0.002137667908376034 / 0.003478000017835715 | 263 / 3180 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 25 | `person/puf_tax_itemization/social_security_dependents[clone_0]/positive#quantile` | quantile (QED) | BLOCKER; FAIL | 1.255813953488372 | 1.6270067039916964 / out_of_band | 1.255813953488372 | 0.002137667908376034 / 0.003478000017835715 | 263 / 3180 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 26 | `person/puf_tax_itemization/social_security_survivors[clone_0]/positive#quantile` | quantile (QED) | BLOCKER; FAIL | 0.9842613410924481 | 0.849837855127699 / in_band | 0.9842613410924481 | 0.003714438292128042 / 0.0031566702711862886 | 398 / 3094 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 76 | `person/source_operator_retirement_distributions/keogh_distributions[clone_0]/positive#incidence` | incidence | BLOCKER; FAIL | 0.0 | 0.0 / out_of_band | null | 0.000014357302720622315 / 0.0 | 2 / 0 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 77 | `person/source_operator_retirement_distributions/taxable_401k_distributions[clone_0]/positive#incidence` | incidence | BLOCKER; FAIL | 0.7928580784010778 | 0.7928580784010778 / out_of_band | 0.46153846153846156 | 0.021047631434205676 / 0.016687784613818434 | 2057 / 16979 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 78 | `person/source_operator_retirement_distributions/taxable_401k_distributions[clone_0]/positive#quantile` | quantile (QED) | BLOCKER; FAIL | 0.46153846153846156 | 0.7928580784010778 / out_of_band | 0.46153846153846156 | 0.021047631434205676 / 0.016687784613818434 | 2057 / 16979 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 79 | `person/source_operator_retirement_distributions/taxable_403b_distributions[clone_0]/positive#incidence` | incidence | BLOCKER; FAIL | 0.7260054960806753 | 0.7260054960806753 / out_of_band | 1.4639175257731958 | 0.0016107958211948464 / 0.0011694466192512434 | 161 / 1371 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 80 | `person/source_operator_retirement_distributions/taxable_403b_distributions[clone_0]/positive#quantile` | quantile (QED) | BLOCKER; FAIL | 1.4639175257731958 | 0.7260054960806753 / out_of_band | 1.4639175257731958 | 0.0016107958211948464 / 0.0011694466192512434 | 161 / 1371 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 81 | `person/source_operator_retirement_distributions/taxable_sep_distributions[clone_0]/positive#incidence` | incidence | BLOCKER; FAIL | 17.073910540208754 | 17.073910540208754 / out_of_band | 1.7696335078534031 | 0.0006809676849103125 / 0.011626781332931739 | 61 / 9406 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 82 | `person/source_operator_retirement_distributions/taxable_sep_distributions[clone_0]/positive#quantile` | quantile (QED) | BLOCKER; FAIL | 1.7696335078534031 | 17.073910540208754 / out_of_band | 1.7696335078534031 | 0.0006809676849103125 / 0.011626781332931739 | 61 / 9406 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |

Count invariant: **16 criterion rows = 9 incidence + 7 quantile/QED, covering
11 distinct physical `leg_id` values.**

## Owner-fill schema

The owner should preserve the rows and baseline columns above and replace an
arm's `NOT_RUN_RSS_CAP` cells only from an authenticated terminal gate artifact
for the exact commit and sample controls. A compact machine-readable sidecar or
review note should carry this shape:

```yaml
arm: removal | broad
commit: <exact 40-character SHA above>
sample_fraction: <0.01 for f001 or 0.25 for owner f025>
sample_seed: 578
gate_artifact:
  path: <path>
  sha256: <sha256>
rss:
  max_bytes: <measured peak for the guarded process tree>
  guard_status: passed_below_cap
checks:
  <exact full check_id>:
    criterion: incidence | quantile
    criterion_value: <number or null>
    criterion_status: PASS | FAIL | NOT_TESTED
    ratio_band_status: in_band | out_of_band | not_ratio_comparable
    ratio_acs_over_asec: <number or null>
    quantile_envelope_distance: <number or null>
    asec_incidence: <number>
    acs_incidence: <number>
    nonzero_rows:
      asec: <integer>
      acs: <integer>
```

Acceptance requires all 16 exact `check_id` keys, the same nine/seven criterion
split, and the same 11 physical legs. Missing, renamed, unsupported, guard-killed,
or non-authenticated results remain not measured; they must not be converted to
an improvement, pass, or before/after claim.
