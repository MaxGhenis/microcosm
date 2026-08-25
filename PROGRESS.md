# Progress: remove late-transfer calibration

## State

In progress as of 2026-08-25. The runtime calibration module, application
sites, calibration-selected QRF evidence plumbing, authority component, and F0
policy declaration have been removed. The retained `late_transfer` names are
the ordinary 19-group QRF producer DAG, not the deleted calibration layer.

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

## Next

1. Remove or adapt layer-specific tests and fixtures while preserving generic
   late-producer DAG and transfer row-accounting coverage.
2. Regenerate the US bundle and coverage evidence, then re-pin all moved
   authority, field-usage, seed, and country-envelope identities canonically.
3. Add the removal changelog fragment and run focused tests.
4. Run repository Ruff and one pytest process per package shard, then record
   all evidence and the checkpoint-reuse verdict in `out.md`.

## Historical prior lane

The stacked-pool CD-vintage provenance journal that previously occupied this
file was complete on 2026-08-24. Its final state is preserved at commit
`19854a9f`; it is not current guidance for this lane.
