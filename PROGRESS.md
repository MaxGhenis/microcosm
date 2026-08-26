# Progress: candidate-chain smoke CD-vintage provenance defect

Date: 2026-08-24

Branch: `candidate-25pct-runbook`

## State

Complete. Current main has a stacked-pool/release producer-consumer
contract gap, not an omitted stage-1 or stage-2a runbook argument. The release
always selects a CD-vintage crosswalk and preflights the input H5, while the
production stacked-pool surface cannot assign household districts, stamp the
required provenance, or publish the table-format node the guard probes. The
detailed code-cited finding is committed in
`experiments/candidate_25pct/cd_vintage_provenance_defect.md`.

Per the requested boundary, `run-candidate.sh` and `--dry-run` remain unchanged;
no guard or vintage code was weakened; no H5 was altered; no pool/release build
or smoke rerun was launched; and `smoke_r2.md` was not created.

## Done

- Read `CLAUDE.md`, including the PR-CI/certification boundary and root-journal
  conventions.
- Read the GitNexus debugging and exploration skill instructions selected for
  this code-path investigation.
- Confirmed the worktree is clean on `candidate-25pct-runbook` at
  `7c14a3ba1186dc2a2ba6125ee0d3000aaf140345`.
- Identified `FINAL_REPORT.md` as the existing repository output report for
  this branch; it will be replaced only after the investigation is resolved.
- Traced the release CD path end to end: unconditional packaged crosswalk,
  strict preflight before Ledger compilation, later target-fact translation,
  and diagnostic-only CD gate handling.
- Traced the production stacked-pool parser, source boundary, operator graph,
  publication manifest, nullable writer, and the separate PUF-support producer.
- Verified the stacked writer deliberately emits fixed-format entity groups
  while the release guard recognizes only a compound `household/table` node.
- Read-only inspected the existing 1% H5 and release log: both required root
  attrs, the semantic household CD column, and the physical table node are
  absent; the packaged crosswalk digest itself is correct.
- Compared the relevant runtime files with `origin/main` at `7b90bb18`; they are
  byte-identical.
- Ran five focused parser/default/guard/writer tests; all passed.
- Documented the exact missing current-main producer, provenance, H5-reader,
  and integration-test wiring in the defect report.
- Replaced `FINAL_REPORT.md` with the final stop disposition.
- Passed `git diff --check` and confirmed the runbook, guard, vintage module,
  existing H5, and external smoke state remain unchanged.

## Next

1. Open a separate current-main implementation PR for the authenticated
   stacked-pool CD assignment/provenance and fixed-H5 reader contract documented
   in `experiments/candidate_25pct/cd_vintage_provenance_defect.md`.
2. Only after that main fix lands, update the candidate runbook to pass and
   dry-run-verify the new supported inputs, then rerun the authorized 1% smoke.

---
<!-- merged 2026-08-26: sections from candidate-25pct-runbook (above) and main (below, via microcosm#786) both retained; journals are history -->

# Gate-failed base-pool release lane

## State

Complete on 2026-08-26. Containment, opt-in carriage, and preflight surfacing
are implemented and fully verified. The implementation rejects both redundant
green-pool waivers and any release-manifest receipt that does not exactly match
the pool authenticated by preflight; the preflight's historically required
base/selection inputs and exit semantics are unchanged. No pool or release was
built, no artifact was published, and nothing was pushed.

## Done

- Confirmed the assigned branch and worktree.
- Recorded the v2 charter: close the legacy bare-H5 multispine bypass, add an
  explicit release-build opt-in, carry the authenticated red verdict, and
  surface it in publication preflight without making it an automatic
  publication failure.
- Confirmed that no network, artifact builds, publishing, or pushes are in
  scope.
- Traced the strict manifest loader, current stacked-only terminal-failure
  exception, H5 identity stamp, pool sidecar naming, legacy release arm,
  release manifests, and both preflight output modes.
- Reviewed the salvage branch's final source and test diff line by line. Its
  shared classifier/path-binding/receipt approach closes the bypass without
  changing either loader's contract and was retained with the subsequent
  coherence corrections recorded below.
- Completed the `simulation_ready` / `gate_failed` / loader consumer audit.
  Exact-k remains deliberately strict and head-to-head scoring remains the
  existing authenticated evidence exception.
- Identified report-only downstream caveats: stacked producer metadata still
  names only the k-ladder readiness consumer; red pool publication returns
  status 1 and stops shell chains; ACS-local derivatives keep a donor revision
  but do not project the nested red verdict; generic release consumers tolerate
  and ignore the additive receipt.
- Added a release/preflight-specific authenticated pool loader over the shared
  `require_simulation_ready` seam. The strict simulation-ready and existing
  scoring-only loader contracts remain unchanged.
- Closed the bare-H5 path by detecting either the canonical sibling manifest
  or the H5's stamped pool identity, requiring the sidecar, authenticating the
  publication triple, and binding it to the exact requested H5 path.
- Added `--allow-gate-failed-base-pool` only to the legacy `--base-h5` arm.
  It admits only a current authenticated stacked `gate_failed` pool, rejects a
  green or non-pool use, and never affects the exact-k arm.
- Added the self-contained `base_pool` receipt to both manifests, including
  status/readiness, immutable pool identities, flag use, gates JSON SHA-256,
  failure count/list, and the complete terminal verdict.
- Kept the static preflight inputs mandatory, authenticated its base identically,
  displayed red evidence prominently without changing its exit calculation,
  and required optional release-manifest carriage to match the authenticated
  receipt exactly.
- Hardened carried verdict normalization so nested pass/failure pairs and the
  aggregate verdict must be coherent and a red battery cannot report zero
  failures.
- Passed focused Ruff and the complete builder/H5/preflight test files after
  the containment changes.
- Passed the broader exact-k, launcher, release-contract, and publish-guard
  regression suites.
- Passed repository-wide Ruff and the CI test-group inventory verifier.
- Passed every pytest shard in its own process: build 6,545 passed / 45
  skipped; calibrate 203 passed; data 318 passed / 2 skipped; fit 93 passed;
  frame 295 passed / 36 skipped. Aggregate: 7,454 passed, 83 skipped.
- Confirmed `git diff --check` is clean and that no battery bounds,
  tolerances, plans, or terminal gate logic changed.
- Wrote the complete handoff, consumer audit, manifest schema, verification
  receipts, and commit inventory to `out.md`.

## Next

- Human review and merge of `release-from-gate-failed-pool`.
- Any later artifact operation remains separate: an operator must deliberately
  choose the red-pool flag, then run publication preflight and make the human
  publication decision. This lane performed none of those operations.

## Historical prior lane

The stacked-pool-to-release CD-vintage provenance lane previously maintained
this journal and completed before this work began. It authenticated and
applied household geography after source assembly, carried that authority
through checkpoint and publication identities, published verified CD-vintage
H5 attributes, and reached the unchanged release guard through the shared
fixed/table-aware reader. Its final verification was 7,241 passed, 77 skipped,
with repository-wide Ruff and anti-rot checks green. Full details remain at
commit `2263df36` (the parent of this lane's first journal commit).

The still-earlier PolicyEngine-US 1.819.0 lock-bump lane merged into
`origin/main` at `7b90bb18` on 2026-08-24; its final state remains at commit
`05d254aa` and its detailed receipts remain in the historical section of
`_LANE-NOTES.md`.
