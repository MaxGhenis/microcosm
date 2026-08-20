# Battery burndown progress

## State

Analysis is complete on branch `battery-burndown`, based on `arm-split-base` at
`7d6749990933ac072ac257ae76d666aa16b84d25`. The owner-facing,
machine-readable, and progress reports include the final independent artifact,
source, exclusion, classification, and QBI checkpoint-authentication audits. No
builds or pushes were performed, and no code, gate, band, or threshold was
changed.

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
- Classified the 93 checks as 57 FIX-CANDIDATE, 0
  REVIEWED-EXCLUSION-CANDIDATE, and 36 BLOCKER; the corresponding physical-leg
  counts are 37, 0, and 23.
- Found zero sparse-artifact and zero measurement-mismatch exclusion candidates.
  Release-authenticated checkpoint evidence proves both dead clone-0/native QBI
  booleans are live, green clone-1 PUF-role signals with all nine coupled
  identities reconciled; waiving clone 0 would remove the only pool-terminal
  signal checks, so both are comparator role-scope FIX-CANDIDATEs.
- Established that all 93 checks/60 physical legs must be resolved and grouped
  them into ten owner work packages; a conjunctive battery has no smaller red
  subset whose resolution alone makes it pass.
- Incorporated independent comparator and exclusion-mechanism QA, including
  variable-specific health actions, tied-arm auxiliary evidence, exact UK
  wiring, clone-role provenance, QBI identity coverage, and Keogh support
  semantics.
- Corrected the QRF mechanism account: a realized gated zero-inflated/sign-mixed
  regime already has a donor-sample-weighted sign gate, while degenerate and
  single-sign regimes bypass it. `QRFChainStepResult` exposes the realized
  regime, but the ACS-transfer provenance and checkpoint types do not persist
  it. Per-target regime claims are therefore hypotheses until recomputed from
  frozen donor support, and future receipts must persist the result.
- Separated the already-red baseline retirement repair from the synthesis's
  bundle-only predictor-replacement factorial, which remains a future landing
  guardrail rather than an explanation for baseline failures.
- Rejected the eligibility arm as the unemployment fix despite its green
  battery check because the synthesis records a statistically significant
  unemployment money-OOS regression; the named fix preserves baseline
  predictors and directly calibrates the positive-amount quantiles.
- Confirmed that the current UK QRF-tail and input-mass exclusion registers are
  empty and that the sole live schema-2 entry is the degenerate
  `household.source_year` exclusion; the audit uses UK only as machinery
  precedent, not as a substantive US waiver.
- Recorded the UK precedent's attestation limit: degenerate binding evidence
  exposes full resolved receipts, while input-mass evidence hashes only its
  reference and QRF-tail declares no binding evidence hook. Any future US
  criterion machinery must fully seal resolved receipts.
- Authenticated the baseline simulated checkpoint through its publication
  manifest, release/run IDs, checkpoint identity, and QBI transition authority;
  independently extracted green clone-1 incidences for both SSTB flags and zero
  violations across all nine coupled QBI identities.
- Corrected Schedule-D to its operative tax-unit parent aggregation,
  share/exclusivity formula, and first-person allocation; corrected adult-care
  to its mutable-carrier clearing path, which preserves immutable positives and
  leaves surviving magnitudes unchanged.
- Added the categorical-TVD comparator path to the mechanism overview and
  hardened the canonical transfer citation through the fitted-output return.
- Made the ten work packages an explicit coverage partition rather than a claim
  of ten independent fixes. Clearing all 93 current failures is necessary, but
  certification still requires rerunning all 211 legs because isolated arms
  demonstrate that a remedy can create new red legs.
- Ranked five non-overlapping work packages by current-red coverage, including
  physical legs: PUF tax 38/25, retirement 16/11, source operators 13/7, rare
  signed tails 9/5, and QBI source/joint model 8/4 (checks/physical legs). The
  separate two-check QBI terminal-role FIX is not combined to inflate ranking.
- Made every generic transfer-surface action regime-recomputation-first and
  required future regime receipts, coupled-identity guardrails, and a full
  211-leg rerun, avoiding an unsupported assumption that each realized fit used
  a gated regime.
- Incorporated the final source audit: narrowed the generic mechanism to the
  transfer surface, documented the missing realized-regime receipt, added the
  operative Schedule-D citation, and cited the manifest readiness conjunction.
- Revalidated exact baseline ordering, Markdown/JSON row parity, class and
  package arithmetic, arm winners and deltas, all four artifact hashes,
  mirrored terminal payloads, 132 comparisons/211 legs, and all source-line
  endpoints.
- Independently recomputed every baseline value and arm winner with zero
  discrepancies, then corrected clone/origin scope, exact comparator formulas
  and zero conventions, target routing, the proposed retirement factorial, and
  UK exclusion ownership. The stricter QBI audit changed exactly two
  dispositions from conditional reviewed exclusions to concrete fixes.
- Completed a final independent mechanism/classification audit with no count or
  disposition changes. Added the exact QRF regime taxonomy and Boolean encoder
  citations, narrowed the UK receipt-attestation account, and made tied-arm
  auxiliary semantics explicit.
- Re-audited comparator and reviewed-exclusion source claims independently and
  hardened two citation edges: the distinct US terminal-gate names and the UK
  binding-evidence-to-attestation path, including signing-key conditionality.
  This changed no row, value, classification, work package, or recommendation.
- Final report SHA-256:
  `83c9971d45fc084407a6e9900118d065ac8d20d4beed5a2097d35068bfdcf1ab`;
  JSON SHA-256:
  `fdd5415f78a5634f12b597778070f5d1df760b7ae837f28e07fb22bb631a3629`.

## Next

- Prioritize the five coverage-ranked workstreams in `ADJUDICATION.md`, starting
  with the 38-check/25-leg PUF-tax cluster and the 16-check/11-leg baseline
  retirement audit/refit. Keep the future retirement bundle factorial as a
  separate landing guardrail; it clears no baseline red.
- Implement the two QBI terminal-role fixes with continuously enforced clone-1
  comparisons and coupled identities; do not replace them with exclusions.
- Implement and rebuild only in separately authorized change lanes; publication
  remains gated until a future release battery is green.
