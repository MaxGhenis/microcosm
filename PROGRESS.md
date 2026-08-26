# Progress: QRF drift decomposition Phase 0 v2.6/A17

## State

The Max-approved A17 restart is active from design commit `1c315579`.
The governing v2 design, every amendment through v2.6/A17, both D0 bindings,
and `CLAUDE.md` have been read in the required order. The worktree began with
only the two requested Phase-0 output files modified by the prior A16
fail-closed attempt; they remain uncommitted and are treated as reusable
diagnostic evidence, not as final A17 results.

Execution has cleared the deterministic A17 setup boundary. The sealed Step-0
deliverables and adopted C0a/C0b/C5 evidence re-verified; the mechanical
control roster is K=122 with z*=3.526967430023352 and ordered-ID digest
`348386d9675172b65550ef7cb157fb1387e1d45331f61253aefe40dbe8f2bbc9`.
A17-15(i), A16-15(ii), and A17-15(iii) all pass 9/9. Fresh C4 has also passed
all 40 stochastic null-total cells and all 20 deterministic empty-G3 checks.
The next gated action is C2/C3. A numerical failure of any gated control will
stop the run; non-gated gaps use the A16 recorded-default rule and do not stop
execution.

No pool build, refit-with-changes, network access, publication, promotion, or
logbook write is authorized or planned. Bounded gate refits and deterministic
replay are allowed by the design.

## Done

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
- Added and committed the deterministic P0/P1/P6/P7 executor, including the
  candidate pre-calibration ledger and the two authorized baseline cross-rung
  readings. It passed static and synthetic helper validation. It has not been
  executed because §3.6 requires C2/C3 to finish first; no readings artifact
  exists.

## Next

1. Run C2/C3 against the six exact group-specific oracles and apply their
   recovery and power gates. Stop on any gated numerical failure.
2. If controls permit, compute P0/P1 for all targets, prioritized P2 and the
   remaining readings, then C1 and mechanical verdicts.
3. Render and validate the authoritative JSON and Markdown mirror, leaving
   both output files uncommitted.

## Historical prior runs

Earlier journal states and terminal reports remain available in Git history.
They describe v2.2/A14/A16 stops and are not current authority after A17.
