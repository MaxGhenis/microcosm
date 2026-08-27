# Progress: QRF drift decomposition Phase 0 v2.7/A18

## State

The fifth Phase-0 execution attempt is active under design commit `8d553796`
(v2.7/A18). The governing design through A18, both D0 binding files, and
`CLAUDE.md` have been read in the required order. The worktree started this
attempt with only the two requested Phase-0 output files modified by the prior
A17 terminal run; they remain deliberately uncommitted.

A18 supersedes the prior C3 terminal disposition. Its required first seal is
now complete: 32 frozen-gate `(target, pattern, G3 column)` triples were
enumerated, 31 have at least one split, and the sealed table SHA-256 is
`cfbc1dc7ddece6b9895306eb2e34865da79f0f882f52724a06dfc9bf412c264d`.
The artifact is `/private/tmp/qrf_phase0_a18_g3_split_enumeration.json`,
SHA-256 `e853cc8e41c1c2d98dde605a8ca951dfb283246062cf04e280e688291b5d1314`;
an independent second run is byte-identical. A18 branch 2 therefore applies.
The mechanically selected C3 triple is `pre_subsidy_care_expenses`,
`pattern_03_76a0101a`, `is_incapable_of_self_care`: 16 splits and total split
gain `190276014528.88873` (binary64
`0x1.626aac8e071c2p+37`). The old child-support C3 is not adopted.

The adoption audit has also rehashed the complete prior evidence/input bundle.
Every A17 PASS and Step-0 seal matches; only the expected design authority hash
changed at A18. C0a, C0b, C4, C5, C2, and the setup seals are therefore
adopted. The twice-byte-identical formal receipt is
`/private/tmp/qrf_phase0_a18_adoption.json`, SHA-256
`3141b65caa148ca0de1d2eb227c42e3ea7a59b2de25f59ccaf3a59c543c386c1`,
canonical SHA-256
`8d7f50828c5e901eb98ef03644e6c7b67c4da84cc52e41b23970a83b9922a552`.
It rehashes 56 unique recorded inputs, reproduces all six Step-0 seals and all
6,155 IDs, preserves the three stable C3 roster slots without mutation, and
explicitly excludes the old C3. K remains 122, z* remains
`3.526967430023352`, and the ordered roster digest remains `348386d967…`.
C3 has now executed fresh on the selected triple and PASSED. The authoritative
artifact is `/private/tmp/qrf_phase0_a18_c3.json`, SHA-256
`7c0f5632075dc1b095fd186c1d5fb73e74ed3a4490008a500bb9c027cabd074f`,
canonical SHA-256
`71160b99a83e9269e69ff647797b7ee519e31e2667dc3d5a1f4470d2309f0449`.
It zeroed 1,835 observed fit-row carriers. The exact G1/G2/G3 oracles are
`-0.000022805925420829536`, `-0.0003167611543923057`, and
`0.0014874884953640108`. All three paired recovery cells pass at R=250 with a
maximum absolute error of 0.790215 MCSE and no escalation. The G3 power
threshold is `0.00009107088687955122`, so the strict
`0.0014874884953640108 > 0.00009107088687955122` condition passes. A second
full run reproduces the exact oracle, every replicate array, every statistic,
and every non-runtime payload bit for bit. Controls are complete and readings
are now authorized. The primary-rung P0/P1/P6/P7 reading has subsequently
completed for all nine targets. Its authoritative artifact is
`/private/tmp/qrf_phase0_p1.json`, SHA-256
`165fff994c0f5facc16b22e065fc3e2d08e210ab4c1a4539f7a440c087b39ab3`.
All nine whole-bank P0 counts reconcile with D0-3 and the candidate D0-5
raw-draw lineage; every clone-0 ledger has phi=1 and empty S_o. All 18
top-level ledgers and all 18 B2 telescopes close. An independent rerun has an
identical scientific payload after removing only elapsed-time/RSS fields;
that normalized payload SHA-256 is
`83249700d316f2c3125deb34b0fdbeb90735c1dc96f507287272445c9927a396`.
Producer stages sealed `NO_SURFACE` remain explicitly unavailable rather than
guessed. An isolated baseline1pct replay is now implemented for the two
A15.53 positive-leg cross-rung cells. The authoritative artifact is
`/private/tmp/qrf_phase0_baseline_crossrung.json`, file SHA-256
`30f4d46ae4152655f7470efadf6c02941d65847ed38caf4ed037f4c28aa36cd2`,
with scientific content seal
`bf73b65a33716a417a82e85efc73a25ca10327b9488bee9fe152b662262cbb8e`.
It reproduces all eight realized gate-sign vectors and post-draw RNG states,
closes both ledgers exactly, and matches D0-1 incidence bit for bit.

The A8-priority severe-six P2 tranche is sealed at
`/private/tmp/qrf_phase0_a18_p2_severe6.json`, SHA-256
`1a812299b16a7b072742ac02e1fee87c8bd39ee4b867f9215f084d47c57a3d53`.
All 24 C4 endpoint reproductions pass. Child-support expense, weeks, and
workers compensation followed the target-wide R=1,000 escalation rule; the
other three remained at R=250. Reading closures invalidate child-support
expense pattern 02 and weeks patterns 00/02, so those aggregate attributions
are correctly `NOT_VALIDATED_PATTERN_CLOSURE_FAILURE`; their sealed T2 ledger
rows still stand. The corrected all-nine P2 replay is now complete at
`/private/tmp/qrf_phase0_a18_p2.json`, file SHA-256
`ffe323579ecafd3ce05fcc75d68b19000b81560543cf6a6c97df8763b7e18b24`,
canonical SHA-256
`96b162a89fc725c50e7c10c237ed802d89efa83e0c947d7b3589f77a9d0ca2f9`.
It contains exactly 2,322 Step-0 fragments with all static fields passing and
36/36 C4 endpoint reproductions. Six targets escalated to R=1,000. In
addition to the severe-tranche failures above, UC patterns 00/02 fail reading
closure. The strict readings verifier reports 31 validated pre-domain cells,
five closure-failed cells, four insufficient-support cells, 114 ordinary
closure passes, six ordinary failures, and 40 exact Shapley passes. Its final
scientific statistic tuples and every target scientific payload after removing
its seal, runtime, and descriptive marginal audit are byte-identical to the
pre-default artifact. The sealed
default receipt is exact; all five recorded source hashes reverify; both
semantic Boolean priors are categorical with ordered levels `[0, 1]` and
unchanged base audit numerics; and the imported A18 verifier is recorded.
D0 still enumerates no A16-31 joint hybrid-domain predicates. That gated
validity check is therefore unevaluable: all supported group and per-prior P2
estimates remain visible as descriptive numbers but will be normalized
`NOT_VALIDATED` in the final report, outside Holm and H3/H4 decisions. The
exact P5 executor is independently reviewed
and ready. Its sealed estimate is 24 cache-distinct metric surfaces,
479,723,507,273 recipient-donor pairs, and 5,098,887,772,670 feature-pair
costs; the fourfold-conservative cached projection is 11.38 hours, within
A8. Six disjoint target shards preserve every safe cache reuse while making
the long run durable. The first P5 attempt completed its largest
683,997-recipient surface, then rejected the target on a fixed `1e-6`
decile-weight closure epsilon. Direct reconstruction proved all 856,626 rows
were assigned exactly once while valid binary64 reduction orders differ by
`1.30e-6` to `3.14e-6`. The stopped attempt produced no P5 artifact. A
downstream audit then found that aggregate row counts alone could overstate
their diagnostic power and that the later decile-to-T2 check still used a
scale-blind `2e-14` floor. The executor now certifies every global S_q row
exactly once (with missing, duplicate, and unexpected-row identities),
separately bounds weight and drift regrouping at 4,096 binary64 ULPs on the
natural survey-weight scale, and records both residuals. The first shard will
restart from this committed code. That restart and the energy singleton then
exposed a post-distance assembly bug before either artifact was written: P5
looked for a nonexistent Boolean `pass` member in P1's frozen support record,
whose exact contract is the `status` string. The shared run was stopped before
editing its live-hashed source. P5 now validates and consumes exactly
`SUPPORTED` or `INSUFFICIENT_SUPPORT_NO_VERDICT`; eleven focused P5 tests and
all 92 Phase-0 tests pass. The final replay has now sealed the energy shard at
`/private/tmp/qrf_phase0_a18_p5_energy.json`, file SHA-256
`177db0d8f1484920b9bcb46390bc719fc3d639b8086ee7b0a93e2f2dafa8ed78`,
canonical SHA-256
`db8633337c2e1ea9e4a64b9679ec07a2cf1e4870bee9c6eb39ceaefebed55a19`.
All 382,903 S_q rows are certified exactly once; its weight residual is
`3.0547380447387695e-7` against a `3.0517578125e-5` bound, and its positive
and negative T2 regrouping residuals are `1.1210650463500116e-16` and zero.
The 62-row manifest passes with ordered-ID SHA-256
`b8061efc89120409d0bb4276e50489c85f0e37f126a20ded3486aecae5742e57`.
The shared four-target shard is now sealed at
`/private/tmp/qrf_phase0_a18_p5_late_base.json`, file SHA-256
`f58014e2bed9b2bcfe94f3ec558b88edfda251af40c8d4a6bd043942d3ed0e92`,
canonical SHA-256
`85ac408e7653e12d9e690c1a380fe4ad2c7ad343b5262537330a429f5bcff588`.
Its 248-row manifest passes with the expected ordered-ID SHA-256
`cf5cb3e32381b1e17b4a6e758ed6ced0e476b8a791911a9879d0848bc5eb7804`.
An independent 1,754-assertion audit has no failures. The
child-support-received singleton is also sealed at
`/private/tmp/qrf_phase0_a18_p5_csr.json`, file SHA-256
`da6a2397a194ef89526885bd38659de66427b178061d27b8588fe3b2815c71cd`,
canonical SHA-256
`53c6a0362590a56052b475b77b18af890c22579416a0a66eddd47af4c15d04f5`;
its expected ordered-ID SHA-256 is
`97b3fc740d724e0cac56818c25565fc9600d7494fc0ba35613c2c63e9b317c65`.
An independent 509-assertion audit has no artifact failures. The adult-care
singleton is sealed at `/private/tmp/qrf_phase0_a18_p5_care.json`, file
SHA-256 `0227f997bdeaf3bbb615601302d562ddd5f3d61a4a483a790951aba426a3adc6`,
canonical SHA-256
`1129b2bba6217703d248f202fd910b39ccf8cf93a757c4dfcfe71c43579852e6`;
its expected ordered-ID SHA-256 is
`1450c5a6e8c9c5e00a82fdebeb7b5763197f8520560bfed279b3b3b092ec6b8b`.
An independent 509-assertion audit has zero failures. The unemployment-
compensation singleton is sealed at `/private/tmp/qrf_phase0_a18_p5_uc.json`,
file SHA-256
`0a357c82a505f0fec1cb686361f0ad3cdd141244699dcf3c96cc5cbc0e3c430e`,
canonical SHA-256
`a04fae1ba38c42c05f5a44a0755b5d8cecd6df7465568d7b619d822050d3f09d`;
its expected ordered-ID SHA-256 is
`56599d01aedbdc9a321957cec45eb79e3c66d2b1c5abd65df7c4dd94b541808e`.
An independent 509-assertion audit has zero failures. The SEILY singleton is
sealed at `/private/tmp/qrf_phase0_a18_p5_seily.json`, file SHA-256
`55fa699104e493245163653042d4c11c16f77cb15e0da8adf9a8e375cbbe23d6`,
canonical SHA-256
`68b45d3b5845a6aefffb1cc53f8a6040750cb4e1432b7674ebd82e3ef78fdbac`;
its expected ordered-ID SHA-256 is
`64746e61c549b7b87e2aba49265da8876b9c221824066b94c54c0d0b0337b4fb`.
An independent 509-assertion audit has zero failures. Across all six P5
shards, 4,479 independent artifact assertions plus 179 union assertions pass;
all nine targets occur exactly once, all 558 statistics are unique, and the
combined ordered-ID SHA-256 is
`18b08b8e8fc08368b078426f4239217438d573ea00307245e6b2c362d3018444`.
The strict readings barrier is `READINGS_COMPLETE` at
`/private/tmp/qrf_phase0_a18_readings_barrier.json`, file SHA-256
`fb7b4ad41f5c6d08201208ab9938d5ba75fe4eddb5f1aec3553a1dceb63f2515`,
canonical SHA-256
`2b9ffc6838b37f7ea226f0f100bc2dedb9e2e5d6d28bafc72f40cb818bd15101`.
It records no priority omissions and authorizes C1. C1 is active from source
SHA-256 `6cef30aa36abef40879761d45c3a6313932d653665a13fcae53b4a8e155c6f31`.
Verdicts have not yet executed. No pool build,
refit-with-changes, network access, publication, promotion, or logbook write
is authorized or planned.

## Done

- Read `experiments/qrf_drift_validation_design.md` in full through A18.
- Read `experiments/qrf_drift_validation_d0.md` and parsed the D0 JSON pins,
  counts, regimes, receipts, integrity evidence, predictor/applicability
  matrices, control enumeration, support bindings, and checkpoint census.
- Read `CLAUDE.md`; confirmed the PR-CI/certification boundary and root-journal
  convention.
- Confirmed the branch is at A18 commit `8d553796` and only
  `experiments/qrf_drift_validation_phase0.md` and `.json` were dirty at the
  start of this attempt.
- Added and committed the frozen-gate A18 enumerator and focused tests in
  commit `aa29b1e5`; five focused tests, Ruff, and `git diff --check` pass.
- Reconstructed all 36 C0b-bound gates, enumerated all 32 applicable G3
  triples, sealed the 31-row nonzero-split table, and selected A18 branch 2 by
  the largest-gain rule. The authoritative artifact matches the independent
  integration artifact byte for byte.
- Rehashed the A17 setup, C0a, C0b, C4, C5, and C2 evidence and their bound
  data/code inputs without mismatch. The prior C3 result remains excluded.
- Added and committed the A18 adoption verifier in commit `534b7d10`. Its
  five focused tests and Ruff pass; two full verification runs are
  byte-identical and seal the branch-2 adoption receipt above.
- Preserved the prior A17 terminal JSON in
  `/private/tmp/qrf_phase0_a17_terminal_report.json` before the requested
  output path is reused, with its original SHA-256 `e65378071b…`.
- Added and committed the retargeted C3-only executor in commit `95db4e1e`.
  Nine focused and neighboring tests pass. A two-replicate, explicitly
  non-authoritative smoke zeroed 1,835 observed carriers and recovered a
  nonzero exact G3 oracle, so it does not decide the control.
- Ran the authoritative retargeted C3 at R=250. All three recovery cells and
  the A16-14 power test pass; no target-wide escalation was triggered. An
  independent complete rerun reproduces every scientific value and replicate
  array exactly.
- Repaired and committed the deterministic P0/P1/P6/P7 executor in commit
  `6b001164`; six focused tests, Ruff, formatting, compile, and seal preflight
  pass. Follow-up commits bind candidate I_q to the pre-calibration structural
  surface (`47da4cd7`) and candidate P0 lineage to D0-5 rather than D0-4's
  baseline-only terminal comparison (`7ef29548`).
- Executed P0/P1/P6/P7 twice. All nine targets are COMPLETE; all P0 gates,
  18 ledger closures, and 18 B2 closures pass; every non-runtime value is
  reproduced exactly. Positive legs are supported. Negative legs are
  explicitly insufficient support, including the frozen SEILY count of 48.
- Quantified weeks_unemployed positive drift `0.03287028417973478`: B1 is
  `0.026927608409477565`, T5 UC-clearing is `0.005892551588426899`, and T2 is
  `0.00015434837856797244`. Adult-care T5 is `0.0020038161254599483` with
  3,788 candidate pre-calibration rows cleared, extending D0-4's separately
  sealed 183 baseline cleared draws.
- Implemented the two-cell A15.53 baseline1pct replay. Focused tests and Ruff
  pass; the integration replay closes both ledgers, binds every unchanged HGB
  gate to its banked realized signs and RNG state, and produces complete
  top-level rows and dominant labels without a changed-data magnitude refit.
- Ran the authoritative baseline replay from its committed source. Its
  scientific content seal exactly matches the prior integration run. SEILY's
  dominant row is T2 (share `0.9012480263187225`); energy's dominant row is
  T2 (share `0.49554921511098193`); both registered legs are supported.
- Completed and preserved the severe-six P2 priority tranche: six target
  seals, 1,408 manifest fragments, 24/24 exact C4 endpoint reproductions, and
  a PASS static-field manifest. Closure failures remain explicit rather than
  being averaged away or treated as control failures.
- Implemented the exact A16 P5 Gower reading with bounded-memory all-donor
  search, fit-weighted inverse-CDF IQRs, categorical/zero-IQR semantics,
  equal-k scoring, weighted midpoint deciles, exact T2 closure, and A16-36
  concentration. It live-rehashes all candidate checkpoints and banks,
  validates every P5 fragment against the adopted Step-0 roster, records all
  source-code digests, and writes canonical JSON. Seven focused tests and
  Ruff pass; an independent review found no numerical blocker. Cutoff-tied
  donor identities are not materialized because their exact binary64
  distances, and therefore every reported score, are identical; this exact
  equivalence is disclosed in the artifact.
- Diagnosed the first P5 post-distance stop as a scale-blind internal
  floating-sum check, not missing decile assignments or a numerical control
  failure. The final hardening certifies every S_q row exactly once, rejects a
  balanced drop/duplicate even when equal weights make aggregate totals close,
  and records separate 4,096-ULP natural-scale bounds for weight and decile
  drift regrouping. Its regressions reproduce both former false rejections.
  Ten focused P5 tests, all 88 Phase-0 tests, Ruff, formatting, and diff checks
  pass.
- Diagnosed the next P5 stop after energy completed all four distance surfaces
  as an assembly-only mismatch with P1's exact support-record API. No artifact
  was written and no computed metric was accepted. Replaced the invented
  `support["pass"]` access with a fail-closed interpreter of P1's registered
  `status` values, added a regression that rejects the old shape, and stopped
  the still-live shared shard before changing its source. Eleven focused P5
  tests, all 92 Phase-0 tests, Ruff, formatting, and diff checks pass. A
  non-authoritative real-input smoke replaced only the expensive distance
  kernel with deterministic zero scores and exercised the complete remaining
  assembly path: target status complete, 62/62 manifest rows, exact-once
  partition, and both leg drift closures all pass. It wrote no artifact.
- Sealed the authoritative energy P5 singleton from the final committed
  executor. It is `COMPLETE_TARGET_SUBSET`; its file/canonical and ordered-ID
  hashes are recorded above; all 62 Step-0 rows and all live authority/source
  bindings pass; 382,903 rows are assigned exactly once with no missing,
  duplicate, or unexpected row; and both decile-to-T2 closures are inside the
  recorded natural-scale bounds. An independent 510-assertion audit rehashed
  all authority, source, and 18 live input bindings (including both multi-GB
  checkpoints), recomputed the canonical bytes, manifest slice, assignment
  masks/counts, P1 T2/support equality, and drift residuals with zero failure.
- Sealed the authoritative shared four-target P5 shard from the same executor.
  Child-support expense, weeks unemployed, workers compensation, and
  disability benefits are all complete; the first target computed four exact
  all-donor metric surfaces and the other three used the twelve mechanically
  valid cache hits. All 248 Step-0 rows pass. An independent 1,754-assertion
  audit rehashed every authority/source/live-input binding, reproduced the
  canonical bytes and exact manifest slice, and certified 856,626 expected
  rows exactly once for every target. Each target's weight residual is
  `1.6540288925170898e-6` within `6.103515625e-5`; all eight leg closures,
  P1 T2/phi/support equalities, pattern rosters, Gower metrics, pooled mirrors,
  and concentration calculations pass.
- Sealed the authoritative child-support-received P5 singleton. All 62
  Step-0 rows pass. Its independent 509-assertion audit rehashed every
  authority/source/live-input binding, reproduced the canonical bytes and
  exact manifest slice, and certified 856,626 expected rows exactly once.
  Its weight residual is `1.6391277313232422e-6` within
  `6.103515625e-5`; its negative drift residual is zero and positive drift
  residual is `5.970701363877673e-16`, with all P1 equality, metric, pooled,
  concentration, and A8 checks passing.
- Sealed the authoritative adult-care P5 singleton. All 62 Step-0 rows pass.
  Its independent 509-assertion audit rehashed every authority/source/live
  input, reproduced the canonical bytes and exact manifest slice, and
  certified 856,626 expected rows exactly once. Its weight residual is
  `1.6540288925170898e-6` within `6.103515625e-5`; its negative drift
  residual is zero and positive drift residual is
  `-5.421010862427522e-17`, with all P1 equality, exact Gower, pooled,
  concentration, and A8 checks passing.
- Sealed the authoritative unemployment-compensation P5 singleton. All 62
  Step-0 rows pass. Its independent 509-assertion audit rehashed every
  authority/source/live input, reproduced the canonical bytes and exact
  manifest slice, and certified 856,626 expected rows exactly once. Its
  weight residual is `3.2782554626464844e-6` within `0.0001220703125`;
  its negative drift residual is zero and positive drift residual is
  `-2.1250362580715887e-17`, with all P1 equality, exact Gower, pooled,
  concentration, and A8 checks passing.
- Sealed the authoritative SEILY P5 singleton. All 62 Step-0 rows pass. Its
  independent 509-assertion audit rehashed every authority/source/live input,
  reproduced the canonical bytes and exact manifest slice, and certified
  856,626 expected rows exactly once. Its weight residual is
  `3.2782554626464844e-6` within `0.0001220703125`; both signed drift
  closures pass, including the support-floor negative leg. A separate
  179-assertion union audit verifies the exact six-shard, nine-target,
  558-statistic P5 roster with no duplicates or omissions. All six P5 shards
  together passed 4,479 artifact assertions with zero failures.
- Sealed the strict post-readings prerequisite. It rehashes the adopted
  controls, fresh C3, P0/P1/P6/P7, corrected P2 and its default receipt, all
  six P5 shards and A16 binding, and baseline cross-rung artifact. Its
  dispositions are P0/P1/P5/P7 `COMPLETE`, P2 `NOT_VALIDATED`, and P6
  `COMPLETE_WITH_NO_SURFACE`; there are no A8 priority omissions and the next
  required phase is C1.
- Completed P2 for all nine targets. Its resume path reverified the whole
  severe-six artifact and every nested target seal before appending care,
  SEILY, and UC. The final manifest is 2,322/2,322 with no missing, duplicate,
  or extra IDs, all 36 adopted-C4 prefixes reproduce exactly, and every
  pattern's exact Shapley identity passes. Aggregate attributions are marked
  `NOT_VALIDATED_PATTERN_CLOSURE_FAILURE` for child-support expense, weeks,
  and UC; the ledger T2 rows remain valid independently.
- Independently audited P2 through 36,010 internal checks. All live input,
  target, artifact, roster, C4 endpoint, Shapley, closure, aggregate, and
  escalation checks reproduce. Corrected the descriptive marginal audit so
  `is_incapable_of_self_care` and `previous_year_income_available` use
  registered Boolean category order 0/1, and added the imported A18 verifier
  to the executor's recorded `source_files`. Focused tests and Ruff pass.
- Sealed A16's pre-reading default for the otherwise unspecified NON_GATED P2
  category presentation: semantic booleans use 0/1; tenure uses 0/1/2/3 then
  ascending observed extras; FIPS uses ascending observed binary64 levels.
  The twice-identical artifact is
  `/private/tmp/qrf_phase0_a18_p2_defaults.json`, file SHA-256
  `99c507e0ec4c5b39e8bb9785d3c41d4ac9a9c8e7331e429c0c27e458113346c8`,
  canonical SHA-256
  `854ea209b422b9dd2c1fc6848ffc135c0988d410e3c27dad50eebf52e6e25c0a`.
  Sixteen focused P2/default tests, Ruff, and format checks pass.
- Regenerated all nine P2 targets from the corrected committed executor after
  sealing that default. The file and canonical hashes are the authoritative
  values above; 2,322/2,322 manifest rows, all live inputs and sources, all 36
  C4 endpoints, every exact Shapley identity, closure/escalation dispositions,
  and the two Boolean category audits verify. The strict barrier verifier
  accepts the computation as complete and assigns the required global
  `NOT_VALIDATED` reading disposition because D0 has zero joint hybrid-domain
  predicates. Scientific statistics and all target scientific payloads after
  removing seal/runtime and marginal-audit fields exactly match the preserved
  pre-default artifact.
- Implemented the fail-closed readings-before-C1 barrier. It verifies and
  directly binds the adopted controls, fresh C3, complete P0/P1/P6/P7,
  complete-but-`NOT_VALIDATED` P2, both baseline cross-rung readings, and
  exactly six disjoint P5 shards whose union is all nine targets. The barrier
  now also rebuilds and exactly reconciles the sealed P2 descriptive-default
  receipt and rehashes each P5 shard's A16 binding. C1 recognizes the exact
  terminal P2/P6 dispositions without treating them as validated science and
  excludes the support-floor SEILY negative leg from F5 Holm even when its
  estimator fits are numerically supported. Sixteen focused barrier/C1 tests,
  Ruff, formatting, and diff checks pass. The authoritative barrier awaits
  completion of all P5 shards.
- Implemented and independently reviewed the A18 final report assembler. It
  preserves all 6,155 Step-0 IDs; binds the exact enumeration/adoption/C3 and
  readings/C1 sequence; embeds the full 31-row G3 enumeration in the JSON
  mirror; normalizes the unevaluable A16-31 P2 attributions `NOT_VALIDATED`;
  excludes invalid/unsupported rows from Holm; recovers persisted P6 bridge
  values; uses clone-0 support counts; and carries sourced adult-care/weeks
  highlights plus the assembler digest for derived verdicts. Twenty-four
  focused and 53 broader tests pass; a real partial replay is schema-valid.
- Hardened the A18 assembler after a fresh output-contract audit: F4 now uses
  the one global 36-cell TYPEHUGQ-adjustment Holm family; every additive share
  is mirrored and rendered; Holm, probe, and required-highlight derivations
  carry the assembler source digest; absent-class C1 legs are explicitly
  inapplicable; and P0 prints leg-qualified phi rows plus its complete
  first-failure census. Twenty-seven focused finalizer tests pass.
- Completed the P6 mirror hardening against the sealed P1 fixture. Structured
  and deterministic-string seeds now survive exactly; all 90 per-pattern
  transfer-fit cells are populated; clone/value/weight populations retain
  their masks, sign counts, weighted mass, incidence, seeds, and B1 closure;
  and all 504 legitimately unavailable cells carry explicit sealed evidence.
  The exact nested P6 payload is mirrored once per target and the Markdown
  ledger renders its unavailable evidence. Twenty-nine focused tests pass,
  including the real sealed fixture; an end-to-end temporary 6,155-cell
  assembly passes the frozen JSON Schema and canonical seal.
- Added a fail-closed report-contract layer around the immutable permissive
  Step-0 schema. It checks the exact target/leg/ledger/share/probe mirror, all
  eligible F4 Holm results, P6 evidence, P8 and recursive report-section
  source/catalog digests, plus Markdown target, share-vector, P0-census,
  cross-summary, and source-catalog coverage. A real temporary assembly passes
  the frozen schema, manual report contract, Markdown mirror, and canonical
  seal; all 98 Phase-0 tests and Ruff pass. Partial assembly without P1 now
  also renders cleanly rather than indexing absent required highlights.
- Closed the final report's barrier-aware completeness and provenance audit.
  The exact 312 A16-31 P2 domain placeholders and 504 sealed P6 no-surface
  evidence cells remain `UNAVAILABLE` in the authoritative flat statistics,
  but cease to make the run `PARTIAL` only when the exact bound barrier says
  P2 `NOT_VALIDATED` and P6 `COMPLETE_WITH_NO_SURFACE`; mutated or unexpected
  unavailable rows still fail closed. P6 flat/bridge derivations now cite the
  finalizer source, render in producer-transition order, and recursively use
  six-significant-digit Markdown while preserving exact JSON. Every P0 census
  path now cites the hard-pinned execution-commit census implementation and
  sealed target production code anchor. The report contract accepts only the
  exact sealed P2 metadata lineage shape plus a cataloged artifact source.
  Focused tests no longer read either dirty report output and instead use
  deterministic in-memory manifests or the sealed A17 Step-0 fixture. All 33
  focused and 101 Phase-0 tests pass; Ruff and diff checks pass. A real
  P0/P1/P2/P5/P6/P7/barrier assembly validates completely and is partial only
  for the not-yet-supplied 810 registered C1 cells.
- Preserved the complete A17 terminal journal below as historical evidence.

## Next

1. Complete the active all-target C1 run, then compute VERDICTS from the
   sealed additive ledger and valid probes.
2. Render and validate the Markdown/JSON reports while leaving both output
   files uncommitted, then commit the final journal state separately.

## Historical A17 terminal snapshot

### State

The Max-approved A17 restart is terminal from design commit `1c315579`.
The governing v2 design, every amendment through v2.6/A17, both D0 bindings,
and `CLAUDE.md` have been read in the required order. The worktree began with
only the two requested Phase-0 output files modified by the prior A16
fail-closed attempt. They have now been replaced by the final A17 report and
remain uncommitted as required.

Execution has cleared the deterministic A17 setup boundary. The sealed Step-0
deliverables and adopted C0a/C0b/C5 evidence re-verified; the mechanical
control roster is K=122 with z*=3.526967430023352 and ordered-ID digest
`348386d9675172b65550ef7cb157fb1387e1d45331f61253aefe40dbe8f2bbc9`.
A17-15(i), A16-15(ii), and A17-15(iii) all pass 9/9. Fresh C4 passed all 40
stochastic null-total cells and all 20 deterministic empty-G3 checks. The
corrected authoritative C2/C3 run then passed all six oracle-error recovery
cells and C2 power, but C3 is numerically UNDERPOWERED: its exact target-group
oracle and MCSE are both zero, so the strict required comparison is `0 > 0`
and fails. The FINAL RUN NOTICE requires a stop and return to Max on any
numerical control failure. No reading has been opened or computed.

The authoritative outputs have status `CONTROLS_FAILED — C3_UNDERPOWERED`.
The JSON canonical digest (excluding its own field) is
`e1e3e22fee3c2b64d4bf7a9bf4911b37b82bbb0c5cf38d84fb4959de70f7e407`;
the JSON file SHA-256 is
`e65378071bf9e9519b51eba30c63fd89ca08d982e35610bb5017fcf599e29142`,
and the Markdown file SHA-256 is
`5c9a60bb6364cf87fcc4f89ff1ba0bf7cacc88decde48be262d225e0e2035d68`.

No pool build, refit-with-changes, network access, publication, promotion, or
logbook write is authorized or planned. Bounded gate refits and deterministic
replay are allowed by the design.

### Done

- Read `experiments/qrf_drift_validation_design.md` in full through A17.
- Read `experiments/qrf_drift_validation_d0.md` and parsed the complete D0
  JSON structure, pins, counts, regime, receipt, integrity, predictor,
  applicability, control-roster, support, and checkpoint bindings.
- Read `CLAUDE.md` and confirmed the PR-CI/certification boundary and root
  journal convention.
- Inspected Git state and confirmed that only
  `experiments/qrf_drift_validation_phase0.md` and `.json` were dirty at
  start, matching the requested uncommitted outputs.
- Began read-only audits of prior-run evidence, A16 binding texts and sealed
  deliverables, and the existing execution implementation.
- Added and committed the deterministic A17 setup verifier. Its twice-stable
  evidence artifact is `/private/tmp/qrf_phase0_a17_setup.json`, SHA-256
  `eed8e569e19a5be0e3de67d6f11cb2cb2b7d583d7e3bc2a1602c2492206c81bd`.
- Re-verified the sealed operator table, JSON Schema, ordered 6,155-ID
  manifest, empty adjudication table, recorded defaults, and composite seals.
- Re-verified and adopted C0a (36 comparisons / 72 cells), C0b (36 bit-exact
  gates and 76 E2 roster cells), and C5 (8 exact fixture booleans).
- Passed A17-15(i) on all nine full-bank receipt populations and A16-15(ii) on
  all nine bank/alignment populations, including both D0 lineage digests.
- Passed A17-15(iii) on all nine baseline populations. Adult care has exactly
  the registered 183 unequal rows (sorted little-endian int64 digest
  `7fe71e4ff4795ee968daf0acbd3f24db0db105b538508f099bd83a6e7d44dda3`),
  clone split 88/88/7, positive raw values, terminal positive-zero bits, and
  no additional unequal row.
- Added and committed the shared QRF replay primitives and C4 executor. A
  fixed-two-replicate smoke exercised all four child-support-received pattern
  cells; the authoritative path remains the registered 250/1,000 schedule.
- Ran authoritative C4. All 40 stochastic cells passed at
  z*=3.526967430023352, and all 20 structural empty-G3 checks were exact zero.
  `weeks_unemployed` and `self_employment_income_last_year` triggered the
  registered target-wide extension to 1,000 replicates; every other target
  remained at 250. The evidence is
  `/private/tmp/qrf_phase0_a17_c4.json`, SHA-256
  `8cd95aafcdb896b8f6bedc86dcb030c912b277a6b28ba87d69bac0d79a5c06c5`.
- Independently audited C4 against A14/A15/A16. The audit reproduced all
  allocations, 40 means/SDs/MCSEs/threshold decisions, both prefix-250
  escalation triggers, the 40-ID roster, 20 empty-G3 zeros, 36 adopted-gate
  bindings, and 18 input pins with no finding or stop condition.
- Added and committed the deterministic P0/P1/P6/P7 executor, including the
  candidate pre-calibration ledger and the two authorized baseline cross-rung
  readings. It passed static and synthetic helper validation. It has not been
  executed because §3.6 requires C2/C3 to finish first; no readings artifact
  exists.
- Added the C2/C3 executor, then rejected its first artifact after independent
  audit found that the six rostered rows used an independent-R0 baseline and
  flattened stratum pieces. Corrected and committed the executor so official
  errors, MCSEs, escalation, and power use A16-12's identical-i,j pairing;
  real/paired paths combine unit means with exact GQ weight shares, while the
  descriptive independent-R0 path uses the required flat donor-side mean.
  Focused regression tests pass 2/2 and independent re-audit found no remaining
  issue.
- Ran corrected authoritative C2/C3 at R=250. All six recovery cells pass with
  maximum |error|/MCSE 1.4260746053761308 and no escalation. C2's exact
  G1/G2/G3 oracles are 0.00015910033578738115,
  0.0008930130267351436, and 0; its power gate passes. C3's three exact
  oracles and MCSEs are zero; its strict power gate fails as UNDERPOWERED.
  Evidence: `/private/tmp/qrf_phase0_a17_c2c3.json`, SHA-256
  `78a20b894457395add4253fd1772c3fa66194bda8b4aba69a40f10e1bfc2fa2a`.
- Added and committed the A17 report finalizer. It preserves every sealed
  Step-0 object, validates the 6,155-ID manifest and schema, and hard-rejects
  the superseded intervention estimator semantics.
- Made the terminal report explicit about A17's exact 183-row adult-care
  exception and C3's 397 observed carriers, zero frozen-gate G3 splits, zero
  nonzero exact differences, and failed strict `0 > 0` power inequality.
- Applied A16-56/default-3 round-half-even six-significant-digit rendering to
  Markdown numeric cells. Added all 20 deterministic empty-G3 checks to the
  JSON control mirror and reported their 20/20 exact-zero PASS in Markdown.
- Rendered both requested output files deterministically. The final rerender
  reproduced their file hashes byte for byte.
- Independently audited the final files with no remaining finding: JSON
  Schema and canonical hash PASS; all five Step-0 object seals and their
  composite PASS; the ordered K=122 roster PASS; required-ID/statistic
  completeness is 6,155/6,155 with zero duplicate, missing, or extra IDs; all
  27 unique source references match their bytes; nine target sections, 18
  legs, 162 ledger rows, and 18 cross-target rows mirror JSON; Appendix A is
  byte-exact; and every Markdown float token follows the bound precision.

### Next

1. Return the terminal C3 power result to Max. Do not open readings or C1
   without a new owner-logged amendment/restart authority.
2. Leave `experiments/qrf_drift_validation_phase0.md` and `.json` uncommitted
   as required; there is no remaining in-scope execution step.

### Historical prior runs

Earlier journal states and terminal reports remain available in Git history.
They describe v2.2/A14/A16 stops and are not current authority after A17.
