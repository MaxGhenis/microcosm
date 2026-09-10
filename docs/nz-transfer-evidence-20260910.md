# NZ transfer evidence audit, 10 September 2026

The first reproducible transfer experiment can use **20 published demographic cells** for fitting and **12 region-by-age cells** for holdout diagnostics. The donor fixture remains synthetic. Matching these observations establishes a working measurement/calibration path; it does not establish that the transferred income, wealth, family structure, or AS entitlement distribution represents New Zealand.

The machine-readable selection is [observed_targets.json](../packages/microcosm-build/tests/fixtures/nz_transfer/observed_targets.json). It preserves source cells, original reference date, publication vintage, geography, units, and fit/holdout roles. No targets have been aged to 2026-27.

## Source and project state

Live GitHub reads on 10 September 2026 found:

| Work | State and usable boundary |
| --- | --- |
| [Microcosm #343](https://github.com/PolicyEngine/microcosm/issues/343) | Open. Its broad take-up ambition does not establish target activation or justify fitting entitlement to administrative receipts. |
| [Microcosm #820](https://github.com/PolicyEngine/microcosm/issues/820) | Open. The prior package is a transport/export contract and real-Axiom fixture bridge. Period, NZD, family, target, and publication bridges remain explicit prerequisites. |
| [Chronicle #211](https://github.com/PolicyEngine/chronicle/pull/211) | Open, `DIRTY/CONFLICTING`, head `83335a44109f91ca52e8c1a4654499af74c4333c`; CI successes are from 30 August. Supplies 85 provisional population facts: 16 regions plus directly published NZ totals, each for all ages and four broad age bands. It does **not** supply sex, five-year-age, or single-year-age cells. |
| [Chronicle #209](https://github.com/PolicyEngine/chronicle/pull/209) | Open, `DIRTY/CONFLICTING`, head `eb6ca1b3bcb56fe3e62afdf7fd5d84174337b6b1`; CI successes are from 30 August. Its 330 TY2024 WFF facts describe families with non-zero administrative final entitlements and assessed amounts, not every eligible family or cash paid during a fiscal year. |
| [Chronicle income #210](https://github.com/PolicyEngine/chronicle/issues/210) | Open. The local `nz/ird-income-source-targets` checkout has staged/unstaged source-package work and is behind main. Source notes describe 3,946 historical TY2024 facts; this is not a merged/activated target dependency. |
| [Wealth #592](https://github.com/PolicyEngine/microcosm/issues/592) | Open. Correctly identifies missing asset evidence, but fitting household net worth does not by itself validate a family cash-asset test. |

The reviewed local references were the prior NZ take-up plan and target inventory, the Chronicle population and income source notes, and the old NZ package. Existing checkouts were read without altering their changes.

## Runnable demographic selection

The [Stats NZ workbook](https://www.stats.govt.nz/assets/Uploads/Subnational-population-estimates/Subnational-population-estimates-At-30-June-2025/Download-data/subnational-population-estimates-at-30-june-2025-provisional.xlsx) was retrieved again directly on 10 September 2026. It still matches the Chronicle pin: **97,990 bytes**, SHA-256 `001e8a896cfb50f5ed17836dc815b235e3bcca55ee91c9869a2afaeb054b50a6`. The [release](https://www.stats.govt.nz/information-releases/subnational-population-estimates-at-30-june-2025/) was published 29 October 2025.

All cells below measure persons in the provisional **estimated resident population at 30 June 2025**, on the 2023 census base. They cover all sexes. Regional boundaries are at 1 January 2025. These are point-in-time counts, not annual average populations.

| Fit: national age | Persons | Workbook cell |
| --- | ---: | --- |
| 0–14 | 971,300 | Table 3!D64 |
| 15–39 | 1,829,300 | Table 3!E64 |
| 40–64 | 1,624,000 | Table 3!F64 |
| 65+ | 900,100 | Table 3!G64 |

Fit the 16 regional all-age cells in Table 1!D7:D22 as the second margin family. Their exact values and REGC codes are in the JSON. Hold out the following cross-tab cells from both calibration and any fitted geography/imputation step:

| Holdout region | 0–14 | 15–39 | 40–64 | 65+ | Cells |
| --- | ---: | ---: | ---: | ---: | --- |
| Auckland, 02 | 339,300 | 679,700 | 553,000 | 244,000 | Table 3!D13:G13 |
| Wellington, 09 | 90,800 | 193,900 | 170,900 | 87,900 | Table 3!D34:G34 |
| Canterbury, 13 | 119,600 | 239,600 | 215,100 | 123,900 | Table 3!D49:G49 |

The national total is **5,324,700** (Table 1!D25), while the 16 regional totals sum to **5,324,100**. The publisher includes areas outside regions in NZ and warns that independently rounded cells may not add to totals. Preserve the 600-person discrepancy; it is not an observed outside-region target. Wellington's four age cells also sum to 543,500 versus its independently published 543,400 all-age total.

Do not demand exact simultaneous equality over only 16-region support. Use transparent numerical tolerances and display absolute residuals. If outside-region support is added, its allocation is an explicitly modelled assumption unless separately observed. The historical 2% engineering gate is not an estimate of source uncertainty. Fit loss, held-out error, weight concentration, effective sample size, unsupported cells, and retained household counts should remain separate diagnostics.

ERP also includes populations that a private-household-only donor may not cover. A production transfer needs an explicit target-universe bridge or appropriate support for those populations. The fixture experiment should keep this unresolved boundary visible.

## Corrections to older assumptions

**Treasury AS outputs cannot be assumed to represent full take-up.** Treasury's [August 2024 TAWA methodology report](https://www.treasury.govt.nz/sites/default/files/2024-08/tawa-model-methodology.pdf), in its discussion of take-up, documents separate AS logistic models for beneficiaries, superannuitants, and other families, followed by a hybrid administrative/random assignment procedure. This contradicts the inventory's blanket claim that Treasury outputs assume full take-up. Treat DistributionExplorer AS values as external model comparators until that precise artifact's scenario, population, and take-up configuration are verified. The same report describes distinct approaches for core benefits. No Treasury output is automatically the denominator of an AS take-up calculation.

**IRD's live income vintage changed.** The [taxable-income download page](https://www.ird.govt.nz/about-us/tax-statistics/revenue-refunds/income-distribution/tax-on-taxable-income-datasets), updated 10 September 2026, now advertises an August 2026 workbook with new TY2025 data and revisions to TY2021–24. The local September 2025 taxable-income pin remains historical evidence; it must not be described as current. The new workbook link was verified on the publisher page, but a direct download returned HTTP 403 in this audit, so no new byte pin or values are asserted.

**Income concepts remain separate.** US market earnings, NZ taxable personal income, gross PAYE wages, AS chargeable income, and WFF family scheme income require distinct mappings. The local Chronicle notes preserve April 2023–March 2024 coverage and NZD-million conversion, unknown age/income, and independent totals. Currency conversion alone cannot produce an NZ income distribution. Initial fixture conversion factors are test inputs; production transforms need NZ evidence and separate period adjustments. WFF's income table is conditional on claim/administrative entitlement, with source-specific partner and non-filer treatment. It is not an unconditional couple-income distribution.

**Receipt and spending are separate outcomes.** Keep recipient counts, assessed entitlement, accrued expenditure, and cash paid distinct. A year-end caseload is not a person-year denominator; annual expenditure divided by it is not automatically a mean annual award. Observed spending cannot force full entitlement to equal receipt. The earlier 43.9% survey statistic concerns self-reported receipt among potentially eligible survey respondents, not a dollar-weighted take-up rate.

## Wealth evidence and its limits

The official [June 2024 household net-worth workbook](https://www.stats.govt.nz/assets/Uploads/Household-net-worth-statistics/Household-net-worth-statistics-Year-ended-June-2024/Download-data/household-net-worth-statistics-year-ended-june-2024.xlsx) was retrieved on 10 September: **386,546 bytes**, SHA-256 `2fb942322e5131824a15007e7b0742c4f8220822c7e8f9adee83bae154913f9e`, published 26 September 2025. Useful follow-up measurements include currency/deposits and other asset classes by income quintile (Tables 3.01–3.04), reporting status, and individual age.

| Example measurement, YE June 2024 | NZD | Source cell | Published relative sampling error |
| --- | ---: | --- | ---: |
| Median currency/deposits, households with non-zero holdings | 16,000 | Table1.01!C15 × 1,000 | 8.0%, D15 |
| Mean currency/deposits, households with non-zero holdings | 75,000 | Table1.01!G15 × 1,000 | 9.2%, H15 |
| Mean currency/deposits, all households | 72,000 | Table1.03!G14 × 1,000 | 9.2%, H14 |
| Median total household net worth | 529,000 | Table1.01!C36 × 1,000 | 6.2%, D36 |

These source values are rounded to thousands; non-zero-holding and all-household universes differ. They are follow-up evidence, not active fixture targets. A fixed 2% fit threshold should not be mistaken for their statistical precision.

AS [cash assets](https://map.workandincome.govt.nz/map/income-support/extra-help/accommodation-supplement/cash-assets-01.html) aggregate the client and partner's assessable, realisable resources, with exclusions including the home, personal-use vehicle, locked KiwiSaver/retirement accounts, and specified payments. Total net worth is therefore an unsuitable direct proxy. Component means or medians also do not identify the probability of being below the NZD8,100/NZD16,200 limits conditional on family income and housing costs. Retain US donor dependence as inherited structure, expose component mapping and assumptions, and run alternative joint-distribution and threshold-mass scenarios before an AS take-up estimate.

## Accommodation Supplement input coverage

The old [real-Axiom bridge work](https://github.com/PolicyEngine/microcosm/pull/821) exercised WFF. It is not proof of AS computability. The real rules engine must determine its requested-output dependency closure; the transfer graph must report every missing substantive input instead of filling unknowns with zero.

| Input group | Required evidence/bridge |
| --- | --- |
| Assessment unit | Client/partner relationship, dependent children, ages, financial independence where relevant, split/shared arrangements. Construct NZ policy families; US tax/SPM units are provenance only. |
| Legal and programme qualifications | Residence/citizenship status, occupation of the home, student-allowance eligibility, social-housing/IRRS status, residential-care and other funding exclusions; programme-specific exceptions need explicit coverage. |
| Weekly qualifying costs | Distinguish rent, board, joint ownership and owner costs; allocate client/partner shares and subtract boarder/renter contributions, excluded premises areas, or other adjustments. |
| Owner components | Required mortgage principal and interest, rates net of rebate, insurance and allowable other costs. Rent data cannot fill these. |
| Means test | Assessable client-plus-partner assets, chargeable income, beneficiary/NZS/VP classification, delegated base rate and applicable income cutout. Annual wage totals alone are insufficient. |
| Geography and dates | NZ atomic geography and effective AS area, source boundary versions, weekly assessment period, and rule-effective dates. A 2025 population calibration is not a claim that policy was evaluated in 2025. |

These requirements follow Work and Income's [qualifications](https://map.workandincome.govt.nz/map/income-support/extra-help/accommodation-supplement/qualifications.html), [accommodation-cost categories](https://map.workandincome.govt.nz/map/income-support/extra-help/accommodation-supplement/accommodation-costs-01.html), and [owner-cost guidance](https://map.workandincome.govt.nz/map/income-support/extra-help/accommodation-supplement/home-ownership-01.html). Its [current headline limits](https://www.workandincome.govt.nz/products/a-z-benefits/accommodation-supplement.html) are NZD8,100 for single people and NZD16,200 for couples or sole parents; exceptions still require rule/input coverage.

The [AS area definitions](https://map.workandincome.govt.nz/map/deskfile/extra-help-information/accommodation-supplement-tables/definitions-of-areas.html) use **Statistical Area Units 2017** and explicitly reject equivalence with similarly named suburbs/towns. A REGC2025 region or one TA-to-one-area lookup is not sufficient. The [2027 change factsheet](https://www.msd.govt.nz/about-msd-and-our-work/newsroom/budget/2025/factsheets/changes-to-the-accommodation-supplement-through-budget-2025.html) also exempts NZS, VP, and SLP recipients from the homeowner entry-threshold rise. The old plan's unqualified 30%-to-40% statement needs that scope.

[MBIE bond data](https://www.tenancy.govt.nz/about-tenancy-services/data-and-statistics/rental-bond-data/) describes private new-tenancy bonds, uses SA2-2019, applies privacy rounding/suppression, and now carries a system-migration warning: provisional records may be incomplete or revised. On 10 September the monthly series extends to July 2026. [MBIE's comparison guidance](https://www.tenancy.govt.nz/rent-bond-and-bills/market-rent/difference-between-mbie-and-trade-me-rental-figures/) explicitly says it does not measure rent paid by all tenants. Use it as an imputation/validation input with those selections, not a hard all-renter rent target.

For each AS run, report unweighted and household-weight-derived assessment-unit coverage by input, joint complete-input coverage, explicit assumed versus observed values, and output availability. Only a complete, validated assessment may be counted as zero entitlement. The first candidate may legitimately report AS unavailable; the next milestone must supply an AS-capable candidate and validate real-runtime cases before any take-up total.

## Proposed replacement for the older take-up-plan paragraphs

> Full entitlement must be calculated by the validated NZ rules engine over a population with explicit input coverage. Treasury DistributionExplorer outputs are external model comparisons whose take-up settings and population basis must be checked individually. TAWA's published methodology models partial Accommodation Supplement take-up, so its AS totals must not be labelled a full-entitlement denominator without separate evidence. Administrative receipt counts and expenditure describe different outcomes and accounting periods. They remain validation evidence for a separately specified receipt layer and must not force modelled full entitlement to equal observed spending.

Apply that replacement to the old target inventory's “Dollar-level calibration design” and Treasury sections, and to the take-up plan's “Aggregates” and “Take-up computation” paragraphs when those documents are reconciled. This audit leaves the reference-branch documents untouched.

## Immediate implementation choices

1. Run the shared graph against the honest synthetic donor fixture and the pinned demographic selection. Label observed targets, inherited donor structure, and synthetic fixture values separately in Orrery.
2. Keep the 12 cross-tab cells held out. Record support and calibration residuals without tuning the same experiment to its holdouts.
3. Retain donor record/entity IDs and source revision through currency, period, family, geography, imputation, calibration, and pruning nodes. Drop US tax/benefit outputs from NZ inputs.
4. Stage income, housing and component-wealth fact ingestion/mapping as separate follow-ups. Preserve actual publication vintages and sampling/rounding metadata.
5. Keep entitlement, receipt, and fiscal comparisons distinct. This audit enables development without IDI or Treasury take-up coefficients; it does not certify population or take-up estimates.

The current work stops at the readiness packet and tiny fixture validations, then freezes pending an approved immutable US donor handoff. It does not authorize or require a full NZ population build before that dependency is available.
