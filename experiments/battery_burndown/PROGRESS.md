# Battery burndown progress

## State

Evidence collection complete; adjudication drafting is in progress on branch
`battery-burndown`, based on
`arm-split-base` at `7d6749990933ac072ac257ae76d666aa16b84d25`.
No builds, pushes, or gate/threshold changes are in scope.

## Done

- Read the repository operating instructions.
- Confirmed the source branch and preserved unrelated untracked files.
- Created the dedicated analysis branch and report directory.
- Read and hashed all four gate artifacts and read the arm-attribution synthesis.
- Reconciled the apparent count: 93 failing comparator checks cover 60 unique
  physical legs (43 incidence, 48 quantile-envelope, and 2 dead-comparison
  checks); 33 physical legs fail both incidence and magnitude.
- Verified all 211 battery legs and the 132 comparison objects across baseline,
  order, eligibility, and investment artifacts.
- Traced the pool-tool wiring, comparator formulas, support rules, and terminal
  pass aggregation to exact source lines.
- Audited the UK schema-2 reviewed-exclusion path and confirmed that the US
  f025 `by_origin_battery` API has no exclusion argument, register, or binding.
- Calculated best isolated-arm movement for all 93 baseline failures. Eight
  checks turn green under eligibility, but eligibility adds eleven new failures;
  no isolated arm is landable and only one physical baseline-red leg becomes
  wholly green in any arm.

## Next

- Assign an honest FIX / REVIEWED-EXCLUSION / BLOCKER disposition to every
  failed check, including a concrete action or named missing evidence.
- Derive class counts, the minimal green set, and the five highest-leverage
  work packages.
- Validate Markdown/JSON completeness, internal counts, and source citations.
