# Progress: QRF drift decomposition Phase 0 v2.6/A17

## State

The Max-approved A17 restart is active from design commit `1c315579`.
The governing v2 design, every amendment through v2.6/A17, both D0 bindings,
and `CLAUDE.md` have been read in the required order. The worktree began with
only the two requested Phase-0 output files modified by the prior A16
fail-closed attempt; they remain uncommitted and are treated as reusable
diagnostic evidence, not as final A17 results.

Execution is at setup. The next gated action is to verify the sealed step-0
deliverables and their digests, then re-evaluate A16-15(i)/(iii) under A17's
full-bank and registered-183-row populations. Adopted C0a, C0b, and C5 results
will be reused only after their input and evidence digests re-verify. A
numerical failure of any gated control will stop the run; non-gated gaps use
the A16 recorded-default rule and do not stop execution.

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

## Next

1. Verify the A16 incorporated binding-text digest and locate/re-hash the
   sealed operator table, JSON Schema, ordered ID manifest, K=122 roster, and
   adult-care 183-row registered set.
2. Re-run the A17 setup gates and adopt C0a/C0b/C5 only on digest match.
3. Run C4, then C2/C3. Stop only on a gated numerical failure.
4. If controls permit, compute P0/P1 for all targets, prioritized P2 and the
   remaining readings, then C1 and mechanical verdicts.
5. Render and validate the authoritative JSON and Markdown mirror, leaving
   both output files uncommitted.

## Historical prior runs

Earlier journal states and terminal reports remain available in Git history.
They describe v2.2/A14/A16 stops and are not current authority after A17.
