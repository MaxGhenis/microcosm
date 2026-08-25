# Progress: remove late-transfer calibration

## State

Complete as of 2026-08-26. The runtime and all layer-specific test/fixture
surfaces have been removed. The retained `late_transfer` names are the ordinary
19-group QRF producer DAG, not the deleted calibration layer. The final evidence
report is committed at `out.md`.

No pool/release build, publication, push, dependency installation, or network
operation is in scope or has occurred.

## Done

- Read the repository operating instructions and confirmed the requested
  branch, base commit, and clean starting state.
- Selected repository-native reference and call-site analysis as the fallback
  because GitNexus graph tools are unavailable in this session.
- Inventoried all 761 baseline `post_transfer|late_transfer` hits across 35
  tracked files and classified calibration-specific removals versus legitimate
  QRF-DAG or deterministic structural-reconciliation terminology.
- Removed the calibration module and its two dedicated diagnostic tools; QRF
  outputs now pass directly through the stacked transfer stages.
- Removed calibration-only regime-evidence/receipt plumbing while retaining
  the independent transfer row-accounting receipt gate.
- Removed the policy from the stacked authority and F0 spec projection, and
  advanced the authority binding monotonically from version 11 to 12.
- Determined that candidate-1 checkpoints are not reusable: the canonical
  checkpoint and transfer-bank identities embed the full stacked authority,
  so the v11-to-v12 change routes candidate 2 to a new authenticated namespace.
- Removed the dedicated calibration test module and calibration-only fixtures,
  assertions, tamper cases, and stale runtime-import expectations from the
  surviving transfer suites.
- Preserved and exercised the independent transfer target-surface, row-count,
  aggregate-reconstruction, QRF-bank, checkpoint, and late-producer DAG gates;
  the three largest receipt suites and the adjusted 68-module import-graph pin
  pass their focused checks.
- Ran the canonical US bundle generator (new US spec SHA
  `84f55c520fec17651e750a698dd2ae2343e6a20e54743081aca4fcbed66d72cf`)
  and regenerated a complete 42,028-field, 41-item F0 coverage proof.
- Re-pinned the source-attested seed protocol/map, eight-component stacked
  authority, checkpoint-base identity, country envelopes, and loader semantic
  golden through the repository's failing attestation oracles; the complete
  focused stale-pin rerun passes (7 tests).
- Verified both canonical generators in check mode and replaced the now-stale
  calibration-addition changelog fragment with a removal fragment.
- Passed repository-wide Ruff and the complete test suite in five CI-parity
  shard processes: build 6,422 passed/40 skipped; calibrate 203 passed; data
  318 passed/2 skipped; fit 93 passed; frame 295 passed/36 skipped.
- Completed the final reference and scope audits: 390 underscore-form
  `post_transfer|late_transfer` hits remain, all classified as ordinary late
  QRF-DAG/checkpoint terminology, unrelated deterministic structure, or lane
  history; no deleted calibration symbol or implementation residue remains.

## Next

1. Hand the branch off for a cold candidate-2 build and the requested
   three-column scorecard; those build/publication actions remain outside this
   lane and were deliberately not run here.

## Historical prior lane

The stacked-pool CD-vintage provenance journal that previously occupied this
file was complete on 2026-08-24. Its final state is preserved at commit
`19854a9f`; it is not current guidance for this lane.
