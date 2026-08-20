# Battery burndown progress

## State

Analysis is complete on branch `battery-burndown`, based on `arm-split-base` at
`7d6749990933ac072ac257ae76d666aa16b84d25`. The owner-facing and
machine-readable reports are committed at `b654db68`. No builds or pushes were
performed, and no code, gate, band, or threshold was changed.

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
- Enumerated every failed criterion once in `ADJUDICATION.md` and
  `adjudication.json`, including baseline evidence, best-arm movement,
  line-cited mechanism, disposition, named work, and S/M/L effort.
- Classified the 93 checks as 55 FIX-CANDIDATE, 2 conditional
  REVIEWED-EXCLUSION-CANDIDATE, and 36 BLOCKER; the corresponding physical-leg
  counts are 35, 2, and 23.
- Found zero sparse-artifact exclusion candidates. The two measurement-mismatch
  candidates are clone-0/native QBI dead booleans and remain conditional on
  clone-1 PUF-role signal/identity proof plus new authenticated US exclusion
  machinery.
- Established that all 93 checks/60 physical legs must be resolved and grouped
  them into ten owner work packages; a conjunctive battery has no smaller red
  subset whose resolution alone makes it pass.
- Incorporated independent comparator and exclusion-mechanism QA, including
  variable-specific health actions, tied-arm auxiliary evidence, exact UK
  wiring, clone-role provenance, QBI identity coverage, and Keogh support
  semantics.
- Revalidated exact baseline ordering, Markdown/JSON row parity, class and
  package arithmetic, arm winners and deltas, all four artifact hashes,
  mirrored terminal payloads, 132 comparisons/211 legs, and all source-line
  endpoints.
- Final report SHA-256:
  `fe58f3fdbea13379eaf8953b312fe0a32a6fc4b3e7ac716f83447a60815737e8`;
  JSON SHA-256:
  `246f1627e0b88d6427044bd7d1d10dd09b5ae163ad0888c24e338c4668ec6fa6`.

## Next

- Owner adjudicates the two conditional QBI scope candidates; absent the stated
  proof and new US machinery, treat them as BLOCKERs rather than exclusions.
- Prioritize the five resolution packages in `ADJUDICATION.md`, starting with
  the 38-check PUF-tax hurdle/quantile cluster and the 16-check retirement
  factorial/model-data cluster.
- Implement and rebuild only in separately authorized change lanes; publication
  remains gated until a future release battery is green.
