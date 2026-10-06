# US public and private pensions (#1068)

PolicyEngine-US models pension income in four input leaves:
`taxable_public_pension_income`, `tax_exempt_public_pension_income`,
`taxable_private_pension_income` and `tax_exempt_private_pension_income`.
`taxable_pension_income` adds the two taxable leaves and `pension_income` adds
all four, so federal income tax sees only their sum. State rules read the
public leaves directly: AZ, ID (through `public_pension_income`), MI, MN, MO and
NE in PolicyEngine-US 2.2.1, joined by AL, KS, LA, MA and NY in
PolicyEngine/policyengine-us#9512, which also narrowed NY's $20,000 pension
exclusion to the private leaf.

Until this change microcosm wrote every CPS, PUF and ACS pension dollar to the
private leaves, as the archived eCPS pipeline did. Public-pension
exemptions therefore never applied in microsimulation.

## CPS: the ASEC pension source codes

The ASEC asks for up to two pension sources. `PEN_SC1`/`PEN_SC2` give the source
(Census cpsmar24.pdf) and `PEN_VAL1`/`PEN_VAL2` the amounts;
`PNSN_VAL = PEN_VAL1 + PEN_VAL2` on every row of the three pinned person members.

| code | source | leaf |
|---:|---|---|
| 1 | company pension | private |
| 2 | union pension | private |
| 3 | federal government pension | public |
| 4 | state government pension | public |
| 5 | local government pension | public |
| 6 | US military pension | public |
| 7 | US Railroad Retirement | public |
| 8 | other | private |
| – | `ANN_VAL` (annuities) | private |

- **Military (6).** Military pensions stay public rather than moving to
  PolicyEngine-US `military_retirement_pay`. No federal gross income source
  reads that variable (`gov/irs/gross_income/sources.yaml` lists
  `taxable_pension_income`, which adds only the two taxable pension leaves), so
  moving them would drop military retired pay from AGI. Writing both would
  count the same dollar twice in states that read both, for example ID
  (2021-2024), NE (2024 and later), LA and MI.
- **Railroad (7).** Tier 2 has no dedicated PolicyEngine-US variable. Public
  treatment lands in AGI either way, and every state rule that reads the leaves
  treats public at least as favourably as private.
- **Uncoded amounts.** Two income-year-2022 persons report `PEN_VAL2 = $1,271`
  with `PEN_SC2 = 0` and a state government first source. An amount whose code
  is 0 takes the class of the person's other, coded source. Both codes 0 with a
  positive amount never occurs and is refused.
- **Taxable fraction.** Public and private use the same
  `TAXABLE_PENSION_FRACTION = 0.590`, so every taxable and tax-exempt total is
  unchanged. PolicyEngine-US has no per-sector taxable share either.

The pinned `census_cps_*.h5` inputs carry `PEN_SC1`, `PEN_SC2`, `PNSN_VAL` and
`ANN_VAL` but not `PEN_VAL1`/`PEN_VAL2`. The #720 restoration
(`asec_census_person_columns`) appends the amounts from each vintage's pinned
Census person member by exact `PERIDNUM` join, and checks the codes the H5
carries against the member. A frame with positive `PNSN_VAL` and no source
columns is refused rather than read as all private.

### Measured public share

MARSUPWT-weighted (÷100) shares of `PNSN_VAL` in the pinned person members,
computed 2026-09-28:

| ASEC (income year) | `PNSN_VAL` | public (3-7) | military (6) | railroad (7) | two sources, one public and one private |
|---|---:|---:|---:|---:|---:|
| 2023 (2022) | $457.6B | 56.9% | 5.1% | 0.42% | 103 persons, 2.1% of dollars |
| 2024 (2023) | $484.7B | 58.9% | 5.4% | 0.17% | 127 persons, 2.7% of dollars |
| 2025 (2024) | $505.6B | 58.6% | 5.2% | 0.21% | 108 persons, 2.2% of dollars |

The mixed-source persons are why the split needs `PEN_VAL1`/`PEN_VAL2` rather
than the codes alone.

## PUF clones

The PUF reports one taxable pension total, E01700, which the primary QRF chain
imputes onto `taxable_private_pension_income`. Cloning copies every column from
the native twin, including its CPS public leaves, so without a split a clone
would carry the PUF total plus the twin's public pension.
`puf_support._reconcile_puf_pension_components` runs in finalization, next to
the Social Security component reconcile:

- each clone tax unit's imputed total is split by the public share of its
  copied CPS taxable pension;
- a unit whose twin reports no pension takes the clone arm's weighted public
  share among units that do;
- public plus private equals the imputed total, exactly.

The split does not add a QRF target, so the chain's target order, the draws of
every other PUF output and the frozen `source_stages.json` are unchanged. The
clone's tax-exempt pension leaves remain copies of the twin, as before.

## ACS rows

ACS `RETP` is a predictor, not a decomposed total. The ASEC donor's analog,
`__acs_transfer_retirement_income`, now sums all four pension leaves plus
`taxable_ira_distributions` (`acs_transfer._DONOR_COMBINED_COMPONENTS`, mirrored
in the late-transfer registry and the stored-input register). Without that, the
donor analog would drop government pensions that `RETP` includes: the 2023 ACS
Subject Definitions count company, union, federal, state and local government
and U.S. military pensions as retirement income. The public leaves reach ACS
rows as transfer targets in the automatic `source_operator_cps_carried` family.

A donor built before this change carries neither public leaf. Its private
leaves hold every pension dollar, so the public pair is exactly zero there, and
the analog sums the components the donor has
(`acs_transfer._PRE_PENSION_SPLIT_ABSENT_COMPONENTS`) instead of disappearing.
The ACS local lane stages from such published donors. Any other missing
component still drops the analog, as before.

## Release contract

Both public leaves are hard requirements of the release coverage manifest
(`US_PUBLIC_PENSION_REQUIRED_INPUTS`). Every published default predates the
split, so the gate is red on them until a national build persists the leaves.
ASEC raw-stage checkpoints built before this change lack `PEN_VAL1`/`PEN_VAL2`
and are refused by the split; rebuild them.
