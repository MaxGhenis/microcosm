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
guessed. The two baseline1pct cross-rung rows currently bind D/J0/Iq/raw/T5
but leave gate-dependent rows `NOT_RUN_PRIORITY_RULE`.

P2, P5, C1, and verdicts have not yet executed. No pool build,
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
- Preserved the complete A17 terminal journal below as historical evidence.

## Next

1. Execute P2 for the six severe-drift targets, then remaining reading work in
   A8 priority order. Record anything predicted to exceed the bound runtime as
   `NOT_RUN_PRIORITY` with the mechanical estimate.
2. Seal the reading boundary, execute C1, then compute VERDICTS from the
   sealed additive ledger and available probes.
3. Render and validate the Markdown/JSON reports while leaving both output
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
