# microcosm#696 lane notes

## State

- Branch: `block-first-geography-696` at starting commit
  `f71731202b6ff1f0dfa757b6b52aa87ff2a34161`.
- Working tree was clean at lane start.
- Implementing the 2026-08-15 block-first ruling: one population-weighted 2020
  tabulation-block draw at spine construction, followed only by deterministic
  geography derivations, before cross-spine gap fill.
- No network, pipeline build, push, `PROGRESS.md`, or other root-journal use.

## Done

- Read `CLAUDE.md` and mapped the stacked assembly/gap-fill, authority,
  checkpoint-identity, input-pin, geography-ladder, predictor, and lineage-spec
  surfaces.
- Verified offline artifact SHA-256 values:
  - supplied block ladder:
    `7ba39b959068181b56a7ce1dc8f2477b31af33f28d0a1803ff6cba84cdfab06b`
  - validation-only PUMA ladder:
    `39a2ab2abeab07a88362af7ab2940e0e1d50a297c919e4bbc6fb65bab51147d8`
- Inspected the supplied block ladder: schema v1, 5,769,942 populated blocks,
  but no PUMA array or tract-to-PUMA relationship. It cannot implement an ACS
  within-observed-PUMA draw or deterministic PUMA derivation by itself.
- Chosen contract-safe resolution: extend the block-ladder artifact/builder to
  schema v2 with the primary-source 2020 tract-to-PUMA relationship embedded;
  schema v1 must refuse as missing the required PUMA vintage/data. Regenerate
  only this input artifact from the provided local cache for unit/contract
  verification. The existing PUMA ladder remains validation-only.
- Inspected the actual raw ASEC v3 artifact at
  `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/591-pawtyp-pool/asec-producer-checkpoints/asec_raw_stage.checkpoint.h5`
  (653,410,492 bytes; SHA-256
  `51e9fafcd6f16140018fa90c7afbeb6d79008bfc8c122e437d23a399b30553fe`).
  Its household table is exactly `household_id`, `state_fips`, `H_TENURE`;
  no entity contains `county_fips`, county/GTCO, or PUMA data. The v3 schema
  therefore requires the state-only ASEC fallback. Adding identified county is
  a future checkpoint-schema change and is out of this lane's scope.
- Added the schema-v2 geography lineage section and its shape contract test,
  plus the two optional geography predictors and their channel caveats in the
  spec, before runtime implementation.

## Next

- Implement schema-v2 block ladder, block-first construction, authority/input
  identity binding, optional geography predictors, and focused tests.
- Run the required unit/contract test surface and Ruff, add changelog, commit
  locally, and leave the tree clean.
