# Battery burndown progress

## State

Analysis is complete on branch `battery-burndown`, based on `arm-split-base` at
`7d6749990933ac072ac257ae76d666aa16b84d25`. The owner-facing and
machine-readable reports, including the independent source/data audit, are
committed through `a0ab70c7`. No builds or pushes were
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
- Corrected the QRF mechanism account: the fitter already has a
  sample-weighted regime/sign gate, so FIX actions calibrate existing gate
  probabilities and post-draw conditional quantiles rather than proposing a
  new hurdle.
- Separated the already-red baseline retirement repair from the synthesis's
  bundle-only predictor-replacement factorial, which remains a future landing
  guardrail rather than an explanation for baseline failures.
- Rejected the eligibility arm as the unemployment fix despite its green
  battery check because the synthesis records a statistically significant
  unemployment money-OOS regression; the named fix preserves baseline
  predictors and directly calibrates the positive-amount quantiles.
- Confirmed that the current UK QRF-tail and input-mass exclusion registers are
  empty and that the sole live schema-2 entry is the degenerate
  `household.source_year` exclusion; the US candidates borrow machinery
  precedent, not a substantive tail/mass waiver.
- Tightened QBI claims to the canonical clone-0 battery declaration, explicit
  post-transfer QBI reconciliation order, and the need for independent
  clone-1 signal/identity proof before either measurement-mismatch candidate
  could be approved.
- Revalidated exact baseline ordering, Markdown/JSON row parity, class and
  package arithmetic, arm winners and deltas, all four artifact hashes,
  mirrored terminal payloads, 132 comparisons/211 legs, and all source-line
  endpoints.
- Final report SHA-256:
  `3dba8b78b334c3306c6a0b5f548c81848e8512791d6b213bdcc3dd01595f6b4b`;
  JSON SHA-256:
  `76ded5d327b6400b67bb0c91def098f502889a3309924c31e272cc38b4088390`.

## Next

- Owner adjudicates the two conditional QBI scope candidates; absent the stated
  proof and new US machinery, treat them as BLOCKERs rather than exclusions.
- Prioritize the five resolution packages in `ADJUDICATION.md`, starting with
  the 38-check PUF-tax regime-gate/quantile cluster and the 16-check baseline
  retirement audit/refit plus bundle-factorial guardrail.
- Implement and rebuild only in separately authorized change lanes; publication
  remains gated until a future release battery is green.
