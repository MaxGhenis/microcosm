# Final report: merge `origin/main` into PR #769

## Outcome

PR branch `battery-rare-signed-tails` now contains the provisioned
`origin/main` tip `bb796cb7ba577e59d400b84334433c2724d755ce`. Main advanced while
the first merge was being validated, so the result is intentionally expressed
as two merge commits:

- `91ba6058e7df2ed8ee9bb7dd439c99a583a13db8` merges `f9d3b483` and
  preserves PR #769's carrier/regime receipts together with main's policy fold
  and CD-provenance contract.
- `962e92e51445addf2fcc208764071ffe9781e175` catches up through PR #743 at
  `bb796cb7` and combines its UK package descriptor with the shared protocol
  already changed by PR #769.

No build, certification, publication, logbook mutation, or push was performed.

## Conflicts resolved

The first merge resolved 21 paths. Each resolution is also justified
individually in merge commit `91ba6058`:

1. `FINAL_REPORT.md` — kept the branch-local lane report (`--ours`); it carried
   no production behavior.
2. `PROGRESS.md` — kept the PR #769 state/done/next journal (`--ours`).
3. `_LANE-NOTES.md` — kept the branch-local historical journal (`--ours`) as
   required.
4. `docs/evidence/spec-engine/us-f0-coverage.json` — regenerated from the
   semantic union instead of choosing either stale parent report.
5. `packages/microcosm-build/src/microcosm/build/spec_engine/field_usage.py` —
   retained both parents' claims/classifications and re-pinned the merged
   ledger.
6. `packages/microcosm-build/src/microcosm/build/spec_engine/inventory_coverage.py`
   — retained policy/CD-provenance and carrier/regime inventory surfaces, then
   re-derived every moved projection identity.
7. `packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py` —
   preserved complete fitted `regimes` and selected policy `target_regimes` as
   distinct receipt fields across cold, banked, rebuilt, and resumed paths.
8. `packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py` —
   preserved complete group/aggregate realized regimes alongside calibration
   ownership, policy, schedule, QRF, live-output, and CD-provenance evidence.
9. `packages/microcosm-build/tests/test_spec_engine_country_bundles.py` — kept
   both country assertions and re-derived the union-tree envelopes.
10. `packages/microcosm-build/tests/test_spec_engine_coverage_tool.py` — kept
    complete coverage invariants and re-pinned measured union totals.
11. `packages/microcosm-build/tests/test_spec_engine_field_usage.py` — kept both
    usage/mutation suites and re-pinned exact field partitions.
12. `packages/microcosm-build/tests/test_spec_engine_legacy_adapter.py` — kept
    policy-fold assertions and re-pinned the generation-0 authority identity.
13. `packages/microcosm-build/tests/test_spec_engine_loader.py` — kept loader
    separation coverage and re-derived its semantic-hash golden.
14. `packages/microcosm-build/tests/test_spec_engine_stacked_authority_semantics.py`
    — retained the verified CD crosswalk and full authority projection, then
    re-derived the authority/component pins.
15. `packages/microcosm-build/tests/test_us_acs_transfer.py` — combined complete
    realized-regime and selected donor-regime coverage, including persistence,
    rebuild, canonicalization, and drift rejection.
16. `packages/microcosm-build/tests/test_us_multispine_pool_h5_io.py` — retained
    H5/CD provenance and policy-owner fixtures while adding complete regime
    receipts and rejecting the stale materializer.
17. `packages/microcosm-build/tests/test_us_multispine_pool_tool.py` — combined
    CD/geography, H5, policy-fold, and regime persistence assertions; covered
    the composed version identities and stale-version rejection.
18. `packages/microcosm-build/tests/test_us_spec_bundle.py` — kept the merged
    bundle contract and re-derived the late-schedule payload pin.
19. `packages/microcosm-build/tests/test_us_stacked_spine.py` — combined complete
    and selected regimes with calibration-owner validation and fail-closed
    malformed/tampered/noncanonical receipt tests.
20. `tools/build_us_multispine_pool.py` — preserved both behavioral sides and
    advanced the independently colliding stacked materializer from 12 to 13.
21. `tools/spec_engine_coverage.py` — re-derived the pointer-inventory digest
    from the merged field ledger.

The catch-up merge had one conflict, justified in `962e92e5`:

22. `packages/microcosm-build/tests/test_spec_engine_country_bundles.py` — kept
    BE at PR #769's shared-protocol digest because #743 changes no BE input;
    derived UK `c105a4f0...` from that protocol plus #743's new normative UK
    country-package descriptor. Neither parent's UK digest represented the
    combined tree.

No conflict was genuinely contradictory, and no behavioral change from either
side was dropped.

## Pins moved

- Field/coverage ledger: 41,381 to 42,121 configuration fields; 32,161 to
  32,351 authored fields; 9,220 to 9,770 resolved fields; 47 to 49 claims; and
  40/40 to 41/41 inventory checks. Final modes are 13,970 legacy, 27,700
  compiler, 348 validation, and 103 identity; generation-0 effects are 38,443
  legacy and 3,678 no-effect.
- Pointer inventory: `85fb15ef...` to
  `ac68e5901331f35db05e5c5e2b09720672e495707396cde57e5328f46a150904`.
- Inventory projections were re-derived for authority `0f1149e1...`, early
  families `4aa9f736...`, full checkpoint `9c66ec00...`, gap-fill schedule
  `1c31f986...`, graph nodes `7125ad28...`, geography assignment
  `f49425ca...`, late families `d91f9ff0...`, late resource semantics
  `b16398cc...`, late schedule `dcf3c6d2...`, seed map `fe169403...`, seed
  protocol `77eca073...`, source manifest `cd5ba892...`, and take-up
  `fa186dae...`.
- Country envelopes: BE `05e345f9...`; US `4232a165...`; UK first moved to
  `0d7509b2...` for the first union and then to `c105a4f0...` for the #743
  catch-up union.
- Related goldens: loader semantic vector `4a2a4625...`; stacked authority
  components, including late-schedule component `0ecd1ae2...`; compiled
  schedule payload `a4829dd9...`; legacy source/take-up compatibility
  `dc58a0d7...`/`a9e70fb3...`; and legacy pool manifest `1e42f08b...`.
- Receipt/artifact identities compose as: ACS bank schema/materializer 2,
  late-producer receipt 4, pool-stage checkpoint 8, legacy checkpoint 4,
  pool manifest 9, H5 materializer 3, stacked authority 11, and stacked
  checkpoint materializer 13. Version 13 is the union-only advance because
  both parents independently used 12 for different semantics.
- #743's already self-consistent UK gate pins were retained: gate manifest
  `4f66eea7e593b795da93217e9ac8b3b53ca1f82375ec346b3a2ecbb558b89cb6`
  and derived spec fingerprint
  `26fdbcccfaa01e9afa116339cfaa870f76fc6ed3bd5db57fec498781ff3efc64`.

## Verification

- Required `uv sync --all-packages --extra us`: passed before merge; lock
  moved `policyengine-core` 3.26.11 to 3.31.0 and `policyengine-us` 1.764.6 to
  1.819.0.
- Final resource-compliant shards: `microcosm-calibrate` 203 passed;
  `microcosm-fit` 93 passed; `microcosm-frame` 295 passed/36 skipped; and
  `microcosm-data` 318 passed/2 skipped.
- The authoritative `microcosm-build` package test execution ran all 272 test
  files in isolated processes, passed every runnable file, accounted for two
  documented conditional-empty integration modules, and peaked at
  8,384,086,016 bytes RSS. The preliminary monolithic run reported 6,528
  passed/40 skipped but is excluded as resource gate evidence for the reason
  below. The first merge's complete isolated run reported 6,456 passed/40
  skipped and peaked at
  9,097,543,680 bytes, below 15 GiB; it is contextual rather than final gate
  evidence because it used the temporary timeout workaround disclosed below.
- Ruff passed. The US bundle generator check passed. Live envelope digests
  match BE `05e345f9...`, UK `c105a4f0...`, and US `4232a165...`.
  Spec-engine coverage passed at 42,121/42,121 fields and 41/41 inventory
  checks. Frozen realized-regime evidence passed its repository checker with
  all documented authority inputs.
- Staged whitespace, unresolved-path, and exact conflict-marker checks passed
  before each merge commit.

One preliminary monolithic `microcosm-build` test invocation passed all tests
but its long-lived process accumulated 19,242,991,616 bytes RSS. It is not
counted as valid gate evidence; the complete file-isolated rerun above
supersedes it and stayed below the required cap.

During first-merge validation, four `test_us_trade_imdb_bulk.py` child-process
cases initially hit their fixed 60-second import timeout on the busy host. They
passed with a temporary child-only namespace preload that was then deleted.
The final resource-compliant run subsequently passed the entire trade IMDB
bulk test file unchanged and without that shim.

## Remaining risk

- GitHub DNS was unavailable for every fetch attempt. The merged and verified
  target is the provisioned local `origin/main` at `bb796cb7`; if upstream has
  advanced beyond that inaccessible ref, the owner must refresh before push.
- Builds were forbidden, so wheel/package-build, 1% off-chain pool, full-scale
  pool, certification, and publication gates remain intentionally unexecuted.
- `test_logbook_chain_scopes_pg.py` and `test_uk_efrs_weighted_totals.py` were
  conditionally empty locally; their environment-specific coverage still
  requires the applicable CI/owner environments.
- The owner must push the branch and observe PR CI. No push was attempted.
