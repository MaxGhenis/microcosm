# Progress: remove late-transfer calibration

## State

In progress as of 2026-08-25. This lane removes only the US
`late_transfer` post-transfer calibration layer so QRF draws flow directly to
weight calibration. The worktree started clean on branch
`parsimony-qrf-only` at base `bb796cb7`.

No pool/release build, publication, push, dependency installation, or network
operation is in scope or has occurred.

## Done

- Read the repository operating instructions and confirmed the requested
  branch, base commit, and clean starting state.
- Selected repository-native reference and call-site analysis as the fallback
  because GitNexus graph tools are unavailable in this session.

## Next

1. Inventory every `post_transfer` and `late_transfer` reference and trace the
   transfer-checkpoint identity code.
2. Remove the layer, its exclusive plumbing, declarations, receipt gates, and
   layer-specific tests without changing QRF fitting or weight calibration.
3. Re-pin attested identities through the canonical test flow, add a changelog
   fragment, and commit each coherent implementation step.
4. Run repository Ruff and one pytest process per package shard, then record
   all evidence and the checkpoint-reuse verdict in `out.md`.

## Historical prior lane

The stacked-pool CD-vintage provenance journal that previously occupied this
file was complete on 2026-08-24. Its final state is preserved at commit
`19854a9f`; it is not current guidance for this lane.
