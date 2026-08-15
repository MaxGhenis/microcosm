# microcosm#696 lane notes

## State

- Branch: `block-first-geography-696` at starting commit
  `f71731202b6ff1f0dfa757b6b52aa87ff2a34161`.
- Working tree was clean at lane start.
- Implementing the 2026-08-15 block-first ruling: one population-weighted 2020
  tabulation-block draw at spine construction, followed only by deterministic
  geography derivations, before cross-spine gap fill.
- Implementation and final unit/contract verification are complete; no
  pipeline build was run.
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
- Implemented the schema-v2 block ladder and block-first assignment. The
  construction uses sorted seeded draw groups, samples by block population,
  derives all nine geography columns from the selected block, self-checks ACS
  PUMA equality, and records a live-validated receipt.
- Added the schema-v2 ladder as the seventh hash-pinned stacked input and bound
  the operator, seed, artifact schema, channel universes, derivations, and
  vintages in stacked authority v11 and checkpoint identity. The retiring
  legacy route does not require or consume this new input.
- Regenerated only the national input artifact from the local primary-source
  cache (not a pipeline build):
  `build/us/us_block_ladder_2020.npz` (19,098,512 bytes), SHA-256
  `1b288ba60368a17fd008524972b066b0b6ef1435261c863415bdde425c514e6c`.
  It contains 5,769,942 populated blocks, 2,462 PUMAs, and population
  331,449,281. Its summary JSON SHA-256 is
  `e8a632a51fa07a22f6b6abf6f14fdbc5d105143ed8cfc73dd34ea0382b1c1ba7`.
  The tract-to-PUMA relationship input used during regeneration re-verified at
  SHA-256 `5262f460b2c8dbe86b00549e916317b1791fdc595c9af72ab18f6f6a67040531`.
- Added a fail-closed schema-v3 ASEC checkpoint assertion: any `GTCO` or other
  county-named field is refused until a dedicated checkpoint-schema change
  can bind identified-county semantics and replace the state-only fallback.
- The opt-in national validation test passed exactly against the supplied
  PUMA ladder: every `(PUMA, CD119)` overlap population and every PUMA total
  matches the block-first aggregation.
- Added `puma` and `county_fips` as optional person/group ACS-transfer
  predictors through the existing availability-pattern machinery; group
  geography is carried as a constant rather than summed.
- Updated the stacked smoke invocation and operator-ordering/PUMA-ladder docs
  for the seventh input, schema/authority versions, and the validation-only
  role of the legacy PUMA overlap ladder.
- Final combined unit/contract run passed for ACS transfer, ASEC checkpoint,
  stacked spine, block ladder/source/overlap, H5/tool integration,
  spine-blindness, PUF support, `test_us_plan.py`, and
  `test_imputation_lineage_spec.py`. The normal offline run skipped only the
  opt-in national overlap case; a separate hash-pinned invocation ran that
  case and passed (`1 passed in 2.76s`).
- `uv run ruff check .`, `bash -n tools/us_stacked_pool_smoke.sh.example`, and
  `git diff --check` passed. A final read-only requirements audit found no
  blocking issue.

## Next

- Owner: use the regenerated ignored schema-v2 artifact and its exact SHA-256
  above for stacked execution; the originally supplied schema-v1 artifact is
  intentionally refused because it lacks the aligned PUMA rung.
- Owner: push the local branch and open the PR. No lane implementation work or
  pipeline build remains.
