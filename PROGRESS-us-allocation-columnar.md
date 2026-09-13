# US allocation columnar artifact (v2 encoder/decoder) — 2026-09-13

Lane: `microcosm-us-allocation-columnar-20260913`, branch
`us-allocation-columnar-20260913`. Base: fresh `origin/main` `15ebde806`,
fast-forwarded to the compatible continuation `a96fc850942d3fd96d24251c07d9ebc38b79f8de`.

Scope: source-only. Add a compact, deterministic, versioned **v2 private
columnar** allocation encoder/decoder beside the existing row-wise JSON v1
payload in `graph_survey_population._allocation_payload`, plus an integration
proposal. The default v1 host stays byte-for-byte unchanged; no format switch is
propagated to any owner. No push, merge, deploy, native build, test execution or
performance claim.

## State

Tracing the existing typed-column/FrameStore codec surface and the repo's
hand-written bounded binary idiom before any edit. No source edits yet.

## Done

- Inspected worktree status, branch, base, and the assignment.
- Read `SCALING-BLOCKERS.md` as a source map (not proof).
- Read `graph_survey_population.py` v1 allocation path and
  `survey_population_domains.py` key/domain declarations.

## Next

- Finish the codec/consumer/test-lane trace; decide reuse vs. a new module.
- Implement the bounded v2 encoder/decoder and its UNRUN tests.
- Record the integration plan, including the untouched 64 MiB preparation cap.
