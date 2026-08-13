# Business-income taxonomy and SOI/PUF crosswalk

Prepared for John Sabelhaus and Dan Feenberg. This memo records the person-level business-income taxonomy used by PolicyEngine/populace for Section 199A, its PUF lineage, the current SSTB classification, and the published aggregates used to check the resulting deduction. Dollar amounts are nominal for the tax year shown.

## The taxonomy

The meeting separated tax treatment from data classification. The same separation is used below: **F** means a PolicyEngine-US formula owns the treatment; **D** means populace classifies or constructs a data input; **D -> F** means a populace classification feeds a statutory engine formula. The supplied QBI artifacts do not state the SECA, Additional Medicare Tax, or NIIT treatment of these income concepts, so those three columns identify formula ownership without adding unsupported yes/no rules. `qbi_inputs.py` states the boundary directly: PolicyEngine-US owns the QBI deduction formulas and statutory limits.

| Business-income concept | Populace person-level input | SECA | Additional Medicare Tax | NIIT | QBID-eligible input | SSTB clawback |
|---|---|---|---|---|---|---|
| Self-employment | `self_employment_income_before_lsr` | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **D** — qualification is derived from source income not equal to zero, with a positive-income host gate; this row is the non-SSTB route | **D -> F** — occupation/industry classification selects the route; the engine applies statutory limits |
| SSTB self-employment | `sstb_self_employment_income_before_lsr` | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **D** — the same qualified positive Schedule C source is routed here when `business_is_sstb` is true; it is not a separate source amount | **D -> F** — census-code SSTB status is the data classification; the engine owns the income-threshold phaseout/clawback |
| Partnership and S corporation | `partnership_income + s_corp_income` (the assumptions source is `partnership_s_corp_income`) | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **D, provisional** — 0.90 qualification prior because the aggregate source cannot separate guaranteed-payment and reasonable-compensation exclusions | **D -> F, provisional** — when there is no positive qualified Schedule C income, a positive qualified partnership/S-corporation source can receive the passive SSTB prior: 0.264 below $200,000 AGI and 0.170 at or above; the engine applies the clawback |
| Rental | `rental_income` | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **D, provisional** — 0.70 qualification prior because trade-or-business and rental safe-harbor facts are unobserved | **D** — no rental-specific SSTB route appears in the supplied classifier |
| Farm operations | `farm_operations_income` | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **D** — qualification is derived from source income not equal to zero | **D** — no farm-operations-specific SSTB route appears in the supplied classifier |
| Farm rent | `farm_rent_income` | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **D, provisional** — 0.80 qualification prior because participation and operating facts are unobserved | **D** — no farm-rent-specific SSTB route appears in the supplied classifier |
| Estate | `estate_income` | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **F** — engine formula; not classified in the QBI data artifacts | **D, provisional** — 0.60 qualification prior because the aggregate does not identify whether a distribution retains qualified-business character | **D -> F, provisional** — when there is no positive qualified Schedule C income, a positive qualified estate source can receive the same 0.264/0.170 AGI-band passive SSTB prior; the engine applies the clawback |

The 0.90, 0.70, 0.80, and 0.60 qualification rates and the two passive SSTB rates are priors, not observations. The $200,000 AGI division is explicitly a coarse proxy for filing-status-specific modified-taxable-income thresholds. Both `qbi_assumptions_v2.json` and `qbi_assumptions_v3.json` preserve these qualification and SSTB derivations.

## PUF crosswalk

The PUF lineage below distinguishes the source concept from what is physically present in the pinned processed `puf_2024.h5`. That file is labeled 2024 but contains effective-2021 values. It has 74 arrays and no `qbi_simulation_version` attribute.

| Business-income concept | PUF E-code lineage | What the pinned processed PUF supplies |
|---|---|---|
| Self-employment | `E00900` | Direct `self_employment_income`, used as `self_employment_income_before_lsr` and as a QBI predictor |
| SSTB self-employment | No independent E-code; routed from the `E00900` total | No physical SSTB split; populace constructs `sstb_self_employment_income_before_lsr` from the host SSTB classification |
| Partnership and S corporation | `E26270` in release 1.8.0 | One combined `partnership_s_corp_income` array; the current donor uses it as the partnership fallback and sets the S-corporation fallback to zero |
| Rental | `E25850 - E25860` | Derived `rental_income` |
| Farm operations | `E02100` is the raw Schedule F lineage recognized by the QBI source normalizer | No `farm_operations_income` array. The physical `farm_income` array is `T27800`, a distinct Schedule J concept, and is not a substitute |
| Farm rent | `E27200` | Direct `farm_rent_income` |
| Estate | `E26390 - E26400` | Derived `estate_income` |

The current Section 199A contract has exactly 15 person-level leaves:

1. `estate_income_would_be_qualified`
2. `farm_operations_income_would_be_qualified`
3. `farm_rent_income_would_be_qualified`
4. `partnership_s_corp_income_would_be_qualified`
5. `rental_income_would_be_qualified`
6. `self_employment_income_would_be_qualified`
7. `sstb_self_employment_income_would_be_qualified`
8. `business_is_sstb`
9. `qualified_bdc_income`
10. `qualified_reit_and_ptp_income`
11. `sstb_self_employment_income_before_lsr`
12. `sstb_unadjusted_basis_qualified_property`
13. `sstb_w2_wages_from_qualified_business`
14. `unadjusted_basis_qualified_property`
15. `w2_wages_from_qualified_business`

The exact HDF supplies none of that surface authoritatively. Fourteen names are absent. The fifteenth, `w2_wages_from_qualified_business`, is an obsolete deterministic proxy, `0.16 * max(0, E00900 + E26270 + E02100 + E27200)`, rather than the versioned QBI model. The historically observed complete 15-leaf “PUF” was created later by a retired loader that opened the file read-write, simulated or replaced leaves, and stamped version 1. Populace reads the pinned bytes directly and therefore constructs the surface explicitly.

The current construction first derives or draws qualification flags from the seven source concepts, classifies positive Schedule C income using the census-to-Section 1.199A-5 crosswalk, and uses the provisional AGI-band prior only for passive-only partnership/S-corporation or estate income. It then constructs employer presence and business form from SCF shapes, W-2 wage and UBIA intensities from SOI industry tables, and level/form targets from JCT. Version 1 remains the production default; versions 2 and 3 are explicit opt-ins pending review.

| Construction evidence | Fields used | Role and limitation |
|---|---|---|
| [2022 Survey of Consumer Finances codebook](https://www.federalreserve.gov/econres/files/codebk2022.txt) and [summary macro](https://www.federalreserve.gov/econres/files/bulletin.macro.txt), reporting calendar-year 2021 businesses | Ownership/active management/count `X3103`/`X3104`/`X3105`; industry `X3107`/`X3207`; headcount `X3111`/`X3211`; legal form `X3119`/`X3219`; receipts `X3131`/`X3231`; pretax net income `X3132`/`X3232`; ownership share `X3128`/`X3228`; weight `X42001` | Supplies form-by-income employer and margin shapes. Headcount includes owners, family, unpaid workers, and paid workers, so headcount greater than one is only an upper-bound employer proxy. SCF has no W-2 wage bill or UBIA field. Public LLC is combined with LP/LLP. Version 3 preserves SCF shapes and shifts log odds to JCT employer targets. |
| SOI nonfarm sole proprietorship [Table 1, TY2023](https://www.irs.gov/pub/irs-soi/23sp01br.xls) and [Table 2, TY2023](https://www.irs.gov/pub/irs-soi/23sp02is.xls) | Payroll or salaries and wages, receipts, depreciation | Provisional sole-proprietor wage share. Schedule C has no balance sheet, so depreciation flow over receipts is explicitly only a UBIA-intensity proxy. |
| SOI partnership [Table 1, TY2023](https://www.irs.gov/pub/irs-soi/23pa01.xlsx) and [Table 3, TY2023](https://www.irs.gov/pub/irs-soi/23pa03.xlsx) | Cost of labor plus salaries and wages; receipts; gross depreciable assets | Provisional partnership wage and UBIA analogs. Wages exclude guaranteed payments to partners; gross book depreciable assets are the closest published analog to UBIA, not tax-basis UBIA. |
| SOI S-corporation [Table 6.1, TY2022](https://www.irs.gov/pub/irs-soi/22co61ccr.xlsx) | Officer compensation plus salaries and wages; receipts; gross depreciable assets | Provisional S-corporation wage and UBIA analogs. The vintage differs from the TY2023 sole-proprietor and partnership tables. |
| [JCT December 2024 Section 199A study](https://www.warren.senate.gov/imo/media/doc/jct_report_on_199a.pdf) | 2022 total deduction, entity-form shares, threshold split, and zero-employee share | Anchors aggregate levels and form/employer calibration; it does not identify record-level industry, wages, UBIA, or SSTB status. |

## SSTB crosswalk excerpt

The live `sstb_crosswalk_v1.json` contains 53 occupation codes classified `clear_sstb`, each with probability 1 and a per-code regulatory rationale. This is the complete clear list:

| Section 1.199A-5 field | 2018 Census occupation codes and titles |
|---|---|
| Health (33) | `3065` Emergency medicine physicians; `3070` Radiologists; `3090` Other physicians; `3100` Surgeons; `3010` Dentists; `3110` Physician assistants; `3120` Podiatrists; `3000` Chiropractors; `3040` Optometrists; `3050` Pharmacists; `3140` Audiologists; `3150` Occupational therapists; `3160` Physical therapists; `3200` Radiation therapists; `3210` Recreational therapists; `3220` Respiratory therapists; `3230` Speech-language pathologists; `3030` Dietitians and nutritionists; `3250` Veterinarians; `3255` Registered nurses; `3256` Nurse anesthetists; `3257` Nurse midwives; `3258` Nurse practitioners; `3261` Acupuncturists; `3270` Healthcare diagnosing or treating practitioners, all other; `3310` Dental hygienists; `3500` Licensed practical and licensed vocational nurses; `1821` Clinical and counseling psychologists; `1822` School psychologists; `1825` Other psychologists; `2001` Substance abuse and behavioral disorder counselors; `2003` Marriage and family therapists; `2004` Mental health counselors |
| Law (4) | `2100` Lawyers; `2105` Judicial law clerks; `2110` Judges, magistrates, and other judicial workers; `2145` Paralegals and legal assistants |
| Accounting (2) | `0800` Accountants and auditors; `0940` Tax preparers |
| Actuarial science (1) | `1200` Actuaries |
| Performing arts (6) | `2700` Actors; `2710` Producers and directors; `2740` Dancers and choreographers; `2751` Music directors and composers; `2752` Musicians and singers; `2755` Disc jockeys, except radio |
| Performing arts and athletics (1) | `2770` Entertainers and performers, sports and related workers, all other |
| Athletics (2) | `2721` Athletes and sports competitors; `2722` Coaches and scouts |
| Financial services and investing/investment management (1) | `0845` Financial and investment analysts |
| Financial services (1) | `0850` Personal financial advisors |
| Brokerage, dealing, trading, and financial services (1) | `4820` Securities, commodities, and financial services sales agents |
| Consulting (1) | `0710` Management analysts |

The remaining 48 mapped occupations are ambiguous and explicitly provisional. A seeded draw applies the code-specific probability to positive qualified Schedule C income; codes absent from the relevant map receive probability zero.

| Provisional tier | Codes | Interpretation recorded in the crosswalk |
|---:|---:|---|
| 0.10 | 4 | Strongly non-SSTB-leaning mixed or adjacent work |
| 0.20 | 20 | Health technician, assistant, and support occupations not clearly within the named professional tier |
| 0.30 | 24 | Mixed residual or fact-dependent occupations spanning SSTB and non-SSTB work |

All three ambiguous tiers use the same de minimis rationale from Section 1.199A-5(c)(1): a mixed business remains outside SSTB status when SSTB receipts are under 10 percent for gross receipts of $25 million or less, or under 5 percent above $25 million. Three examples show why the probability is attached to a code rather than treated as a legal conclusion:

- `0735` Market research analysts and marketing specialists, probability 0.10: research deliverables and marketing execution versus strategic advice; the crosswalk leans non-SSTB.
- `3300` Clinical laboratory technologists and technicians, probability 0.20: direct diagnostic services, but not clearly a “similar healthcare professional”; the no-patient-contact regulatory example cuts against SSTB status.
- `2850` Writers and authors, probability 0.30: songwriters and screenwriters participate in creating performing arts, while novelists and copywriters do not.

The resource also contains 27 rows for 2017 Census industry codes and 101 occupation rows in total. Industry is designed to take precedence when configured, but the current host has `PEIOOCC` and AGI without a detailed-industry field, so `industry_column` is null and occupation is the live fallback. Pure W-2 workers are outside this SSTB data gate, and the narrow reputation-or-skill category is deliberately unmapped because endorsements, likeness, and appearance income are not an occupation or industry. The full JSON is available on request.

## Published QBID aggregates

These publications answer the July question about whether SOI publishes QBI aggregates. It does: Publication 1304 gives national and AGI-class deduction counts and amounts, while Publication 4801 gives Form 8995/8995-A counts and line-item aggregates.

### SOI Publication 1304, Table 1.4

[Table 1.4, “All Returns: Sources of Income, Adjustments, and Tax Items, by Size of Adjusted Gross Income, Tax Year 2023”](https://www.irs.gov/pub/irs-soi/23in14ar.xls), columns 137 and 138, reports:

| AGI class | Returns with QBID | Deduction amount |
|---|---:|---:|
| All returns | 26,567,412 | $214.627238 billion |
| $100,000 under $200,000 | 7,343,237 | $31.39 billion |
| $200,000 under $500,000 | 5,009,601 | $46.00 billion |
| $500,000 under $1 million | 1,101,063 | $21.08 billion |
| $1 million or more, summed from the published classes | 610,564 | $92.19 billion |

The $1 million-or-more group is 2.3 percent of claimants and 43.0 percent of deduction dollars. The all-return amount is the published value in thousands of dollars converted to billions; AGI-class amounts above are rounded to two decimals.

### SOI Publication 4801, TY2023

[Publication 4801, revision June 2026](https://www.irs.gov/pub/irs-pdf/p4801.pdf), reports 42,284,606 Forms 8995, of which 40,243,872 were e-filed, and 4,101,411 Forms 8995-A. These are form counts, not counts of positive deductions: line 15 reports 26,551,995 positive QBID computations, close to the Publication 1304 claimant count. Publication 4801 does not publish separate deduction amounts for the two forms.

| Form 8995 line | Published frequency | Published amount |
|---|---:|---:|
| 3 — prior-year qualified-business net-loss carryforward | 11,962,310 | ($1,388.249205 billion) |
| 6 — qualified REIT dividends and publicly traded partnership income | 13,920,511 | $21.066514 billion |
| 7 — prior-year qualified REIT dividend/PTP loss carryforward | 250,043 | ($4.207042 billion) |
| 9 — REIT/PTP component | 12,773,280 | $4.202821 billion |
| 15 — qualified business income deduction | 26,551,995 | $214.512296 billion |
| 16 — qualified-business net-loss carryforward to the next year | 15,699,182 | ($1,663.981817 billion) |
| 17 — qualified REIT dividend/PTP loss carryforward to the next year | 218,343 | ($4.155050 billion) |

Parentheses reproduce the publication's negative amounts. The table's source amounts are in thousands of dollars; they are converted here to billions.

### JCT December 2024 study

The [JCT staff study, “Data Related to Deductions Claimed Under Code Section 199A”](https://www.warren.senate.gov/imo/media/doc/jct_report_on_199a.pdf), reports the following 2022 figures.

| JCT table | Population | Count | Deduction | Tax-liability decrease |
|---|---|---:|---:|---:|
| Table 1 | All tax units with the deduction | 25.6 million | $216.0787 billion | $64.2691 billion |
| Table 2 | Below the phaseout threshold | 23.4 million | $95.2643 billion | $19.9335 billion |
| Table 2 | Above the phaseout threshold | 2.1 million | $120.8143 billion | $44.3356 billion |

The report's narrative describes approximately 8.5 percent of claimants as above the phaseout range; they receive 55.9 percent of deduction dollars and 69.0 percent of the tax-liability reduction. Table 1 also reports a $2.9 billion REIT/PTP component.

| JCT table | Additional 2022 split | Count | Deduction | Share of deduction |
|---|---|---:|---:|---:|
| Table 5 | Businesses with zero employees | 17.054 million | $76.0 billion | 35.7% |
| Table 6 | Estates and trusts | 0.183 million | $5.1 billion | 2.4% |
| Table 6 | Partnerships | 2.059 million | $36.0 billion | 16.9% |
| Table 6 | S corporations | 3.129 million | $112.7 billion | 52.9% |
| Table 6 | Sole proprietorships | 14.839 million | $59.3 billion | 27.8% |

## Where our numbers stand

The current modeled total recorded for this comparison is $214.8 billion. The closest published totals are SOI TY2023 at $214.627238 billion, JCT TY2022 at $216.0787 billion, and the local SOI Historic Table 2 TY2022 file at $215.679578 billion (`A04475`, with `N04475` equal to 25,430,690). These are different vintages and statistical products, so proximity is a level check rather than a same-year validation. The item initially described as an HT2 target-scale bug was a source-line mapping defect: the target package had mapped QBID to `A03270`/`N03270` ($31.307205 billion and 3,711,990 returns) instead of `A04475`/`N04475`. The filed repository correction removed those misaligned direct QBI hard targets; the repository records it as change #125, commit `6ec6e4fe`. No separate issue identifier appears in the designated artifact set.

## Artifact summary

1. **The taxonomy** — `packages/populace-build/src/populace/build/us_runtime/qbi_inputs.py`, `us/qbi_assumptions_v2.json`, and `us/qbi_assumptions_v3.json`.
2. **PUF crosswalk** — `experiments/qbi-port-530/PUF_2024_ARTIFACT_AUDIT.md`, `qbi_inputs.py`, the v2/v3 assumptions, `FACTSHEET-scf-business-vars.jsonl`, and `FACTSHEET-soi-industry-tables.jsonl`.
3. **SSTB crosswalk excerpt** — `packages/populace-build/src/populace/build/us/sstb_crosswalk_v1.json` and the v2/v3 SSTB-classification assumptions.
4. **Published QBID aggregates** — `~/ops/populace-qbi-port/research/FACTSHEET-199a-publications.jsonl`, with the linked SOI Publication 1304, SOI Publication 4801, and JCT tables.
5. **Where our numbers stand** — the run total specified for this memo, the publication factsheet, local `22in55cmcsv.csv`, and repository correction `6ec6e4fe`.
