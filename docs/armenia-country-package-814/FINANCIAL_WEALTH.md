# Armenia financial and wealth targets

The opt-in `financial_wealth_targets.json` profile adds 16 monetary references.
The default eight count/indicator references remain unchanged. Loading the
package validates and fingerprints the inventory; it does **not** activate its
rows. Observed levels remain in external fact catalogs, not country-spec JSON.

This responds to the 2026-08-29 request to add income, tax, benefit and wealth
targets. It expands the original engine-free v1 scope while preserving that
diagnostic and its gates.

## Verified 2024 sources

| Measure | Amount, AMD | Accounting basis | Measurement status |
| --- | ---: | --- | --- |
| Registered gross payroll | 2,620,917,043,149 | Calendar-year flow | Prepared donor wage proxy in local experiment |
| Personal income-tax receipts | 650,077,932,447 | Annual Treasury cash revenue | Unfitted; Armenian payment/rules and cash-liability bridge required |
| Funded-pension social payments | 103,394,814,097 | Annual Treasury cash revenue | Unfitted; contribution bridge required |
| Budget pension expenditure | 518,865,909,740 | Annual Treasury cash expenditure | Unfitted; program, residence and payment bridge required |
| Budget allowance expenditure | 507,331,722,650 | Annual Treasury cash expenditure | Unfitted; broad expenditure, not family benefits alone |
| Resident household bank deposits | 2,900,189,597,000 | Closing stock, 2024-12-31 | Prepared donor account-assets proxy in local experiment |
| Household bank and credit-organization loans | 3,308,743,260,000 | Closing stock, 2024-12-31 | Unfitted; comprehensive debt-principal columns missing |
| Mandatory pension-fund net assets | 1,073,872,544,864.94 | Closing NAV, 2024-12-31 | Unfitted; entitlement and residence bridge required |

Payroll uses ArmStat's [monthly wages](https://armstat.am/file/doc/99570268.xlsx)
and [corresponding employee counts](https://armstat.am/file/doc/99570293.xlsx),
sheet `Ամիս -Month-Месяц`, cells `BZ6:CK6` in each workbook. Sum the twelve
monthly count × mean products, not December × 12 or two independent annual
averages. Rounded means imply a rounding bound, not a sampling standard error.
ArmStat defines [gross wages](https://sdg.armstat.am/8-5-1-a/) as cash and
in-kind remuneration before compulsory deductions. Register coverage is not
all household labor income, self-employment or informal earnings. Multiple-job
deduplication is not established by the published workbook.

Fiscal amounts come from the English sheet of the Ministry of Finance's
[execution workbook](https://minfin.am/website/images/files/2022-2024.xlsx),
column F, labeled 2024 actual. Rows 12, 14, 33 and 32 give income tax,
funded-pension social payments, pensions and allowances respectively, in
million AMD. Convert to AMD once. Footnote A49 explains that 2024 mortgage-
interest refunds moved from deductions against income-tax revenue to
allowance expenditure. Thus income tax is gross of those refunds, and
allowances cannot be labeled family/social benefits. The combined pensions-
and-allowances parent is reconciliation evidence, not another independent row.

Deposits use the CBA [sector workbook](https://old.cba.am/stat/stat_data_eng/5_Deposits%20by%20sectors_eng.xlsx),
sheet `deposits`, December 2024 column `KO`, rows 15, 22, 32 and 39. These
combine demand/time and dram/foreign-currency deposits. All four are already
million AMD equivalents and exclude accrued interest; do not convert the
foreign-currency cells again. They exclude physical currency, deposits abroad,
nonresidents and NPISH.

The CBA [loans workbook](https://old.cba.am/stat/stat_data_eng/6_loans%20by%20sectors_eng.xlsx)
separates household bank loans (3,120,303.293 million AMD) from credit-
organization loans (188,439.967 million AMD). The profile keeps the lender
references separate; the table above shows their sum. Source coverage includes
leases/factoring and bank repos and excludes accrued interest. Neither
first-home mortgages nor original auto financing represents this entire stock.

Mandatory pension NAV uses the CBA [pension series](https://old.cba.am/stat/stat_data_eng/PF_series_eng.xlsx),
sheet `NAV structure31.07.24`, cell `B9`, dated 2024-12-31. It is a funded
entitlement-pool proxy, not the present value of state pension promises.
Members, active contributors and pension recipients are distinct populations.
Do not double-count household entitlements and the fund's underlying assets.

Reproducible local harvests:

- `PolicyEngine/_local_runs/armenia-814-financial-sources/`: 54 observations,
  12 pinned raw sources, extractors, exact cells and rounding checks.
- `PolicyEngine/_local_runs/armenia-814-wealth-sources/`: 34 candidates,
  eight pinned sources, extraction/identity checks, and separate physical
  housing-stock context.

These are unissued source catalogs, not a published `ledger-am` release.

## Historical accounts and missing wealth coverage

ArmStat's [2025 publication, table 6.8](https://armstat.am/file/article/finansner_2025_6.pdf)
ends at **2023-12-31** and combines households and nonprofit institutions
serving households (**S14+S15**). It reports financial assets of 7,102,676 million
AMD, liabilities of 2,941,529 million AMD, and financial net worth of 4,161,147
million AMD. Seven profile references retain this evidence as
`historical_validation_only`. They are not relabeled 2024 or household-only.

Financial net worth excludes nonfinancial assets. No verified household
market-value total for housing, land or all nonfinancial wealth is included.
ArmStat housing area and dwelling counts describe physical properties, not
resident ownership or market values.

The donor's account, stock and bond fields cover only part of financial
wealth. Its signed SCF `net_worth` is independently imputed, not reconciled
from those leaves, and cannot bind to financial net worth. Its
`auto_loan_balance` is original financing, not remaining principal. Neither
that field nor mortgage debt alone can bind to comprehensive liabilities.

## Measurement and activation

Shared `MonetaryBasis` records currency, base units, annual-flow or closing-
stock timing, sector, perimeter and valuation. Prepared amounts have an
explicit positive transport factor, source identities, a frozen value vector
and a bridge receipt. The receipt also binds exact integer entity IDs in row
order. The compiler checks these IDs and amount bytes against the Frame before
accepting a monetary row. Binding rejects forecasts, incompatible bases,
nonfinite amounts, unsupported rows and unresolved policy/coverage bridges.
Monetary rows use prepared amounts without a separate filter; apply any masking
before freezing the vector. Receipt-bearing compilation failures are fatal,
while ordinary targets retain their existing reported-skip behavior. These
hashes establish alignment and provenance identity, not source truth or concept
equivalence.

`load_country_spec("am").monetary_profile` exposes the inventory separately
from `.target_references`. Only wages and deposits currently have
`requires_prepared_measure` status. Other states refuse activation even when
a numerically convenient US tax or benefit column is available. The existing
TargetRegistry/Frame compiler and Microcosm solver perform calibration; this
does not introduce a country-specific Python runtime or parallel policy engine.

The official 2024 ILCS household and member workbooks expose mapped salary,
self-employment, pension and benefit receipt columns. A local authenticated
native-spine validation covers 5,184 households and 17,744 present members.
At the published design weights, its observed monthly totals are AMD 155.373
billion of wages, AMD 31.972 billion of self-employment income, AMD 37.050
billion of pensions, AMD 2.040 billion of family benefits, AMD 1.665 billion
of childbirth benefits, AMD 2.047 billion of under-two benefits, and AMD 4.465
billion of other benefits. These figures remain validation-only: survey
receipt concepts, under-reporting, annualization, program coverage and the
Treasury cash perimeter are not yet proven equivalent. They are donor
features or holdouts, not calibration observations merely because the columns
now have names. The local source files also remain outside release artifacts
until ArmStat redistribution terms are resolved.

## Local experiment

`PolicyEngine/_local_runs/armenia-814-financial-wealth/run_financial_calibration.py`
reuses the hash-pinned original demographic builder and weights. It retains
all 616 demographic/household/employment rows and adds national payroll and
deposits, for **618 targets**. The wage source is stored
`employment_income_before_lsr`, not a newly calculated Armenian policy output.
`Frame.place(..., how="sum")` aggregates every donor person carrier to the
household; head-only selection would omit 210 asset carriers.

The level transport is an explicit model assumption: the
[2024 Armenia/US nominal GDP-per-capita ratio](https://api.worldbank.org/v2/country/ARM;USA/indicator/NY.GDP.PCAP.CD?date=2024&format=json)
times the [CBA exchange rate](https://old.cba.am/stat/stat_data_eng/8_Exchange_rates_eng.xls).
Use 392.73 AMD/USD for annual flows and 396.56 for closing stocks. GDP per
capita does **not** validate wealth levels or concentration. The experiment
predeclares stock-factor multipliers of 0.5, 1 and 2, keeping income transport
and targets constant and reporting every scenario. No factor is chosen for
the best fit and no amount is rescaled individually to its target total.

Amounts freeze before the solve; only calibrated household weights change.
SCF 2022 and SIPP `pu2023` December wealth source dates remain disclosed:
an H5 model year of 2024 does not prove current-date observation or full price
harmonization. Wage formality and money-market/foreign-bank account coverage
remain explicit proxy assumptions.

Outputs include full per-target diagnostics, source/measurement hashes,
frozen arrays, weights, weight health, and independent remeasurement. Numeric
remeasurement verifies implementation, not aggregate fit or distributional
truth. No release gates or tolerances changed. No publication, certification,
signing, dashboard upload or default-dataset change occurs.

## Measured result

The central 2,048-epoch run exceeds the payroll target by **0.0047%** and the
deposit target by **0.1167%**. Of 618 targets, **611 are within 1%** and
616 within 10%; median absolute relative error is 0.0930%. The two misses
above 10% are 6+-person households in Yerevan (-15.57%) and Kotayk (-15.39%).
Population, household and employment family totals differ by +0.0192%,
-1.0974% and -0.1515%, respectively.

| Stock multiplier | Payroll error | Deposit error | Kish ESS over clones | Modeled deposit top-10% share |
| --- | ---: | ---: | ---: | ---: |
| 0.5 | +0.0274% | +0.1540% | 15,361 | 88.07% |
| 1 (central) | +0.0047% | +0.1167% | 24,980 | 78.78% |
| 2 | +0.0544% | +0.1129% | 24,892 | 72.30% |

All three use the same targets, demographic features, wage amounts, warm start
and solver budget. The ownership-share range is a scenario sensitivity
envelope, not a confidence interval. Central maximum/minimum weight ratio is
956,703; the heaviest 1% of records carry 27.80% of weight. All weights are
positive and finite. Kish ESS over replicated donor records is not a count
of independent Armenian households.

Independent verification reproduces all 1,854 achieved cells across the three
runs, the source targets and reported summaries. Monetary remeasurement
differs by at most 0.000977 AMD. Source/array/ID/transport hashes and all 45
scenario artifact hashes match. A separate post-review check recompiles the
six monetary rows under the final compiler guard with exactly identical
coefficients. The preserved runtime snapshots disclose the guard-only change;
no amount, target, weight or solver was changed after the runs.

Local results and receipts are in
`PolicyEngine/_local_runs/armenia-814-financial-wealth/README.md`, with final
scenario directories named `central-2048`, `low_stock_scale-2048` and
`high_stock_scale-2048`. Dashboard-format JSON exists locally; it has not been
uploaded to the calibration dashboard.

## What a no-local-wealth-survey result establishes

The experiment constructs a synthetic household-deposit distribution tied to
an Armenian administrative stock total and demographic constraints, without
using an Armenian wealth survey. It still borrows donor structure from US
wealth surveys. Different transport and concentration assumptions can fit
similar totals while yielding different ownership shares.

Comprehensive distributional wealth accounts additionally need consistent
financial assets, debt, housing/land and other nonfinancial assets; household
and residence boundaries; valuation/date reconciliation; and distributional
evidence or reported uncertainty. This is a deposit component and a broader
source-backed inventory, not a completed national wealth balance sheet.
