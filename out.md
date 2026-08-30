WEEKS-IMPL-COMPLETE

# Authorized stacked `weeks_worked` implementation v3

Date: 2026-08-30

Branch: `stacked-dense-gate-sweep`

Plan SHA-256: `e89dd0facbc6d22f296f65ff18520333af0f8ecc6c2b706c1fd6a2b98d49e729`

## Result

The authorized ruling is implemented exactly as a 2024 release-only,
origin-aware measured source stage in the authenticated stacked release path.
It runs before frozen-support selection and the unchanged hours signal gate.
ASEC lineages use validated integral `WKSWORK` values in [0, 52]. ACS lineages
use the pinned 2024 `WKWN` source, accepting only blank or integral values in
[1, 52] and structurally recoding blanks to zero under an explicit Microcosm
recode receipt. Invalid values fail closed; no clipping is used.

Origin routing is owned by the provenance-aware release boundary, not the
source-blind hours stage. The source is declared in `sources.yaml` through a
closed-vocabulary operation and registered kernel, with generated bundle and
compiler identities refreshed. Authentication binds the pinned archive bytes,
an exact one-to-one `SERIALNO + SPORDER` join, validated `person_source_id`
fan-out, and clone roles 0/1/2.

The 2024 measured leaf reaches export, the real ORG/FLSA path, and
`spm_unit_work_expenses`. The installed 2025 formula carries forward the 2024
leaf unchanged, while direct 2025 materialization is rejected. Pool
cross-period exclusion, gate 9480, the hours signal gate, and every existing
threshold remain unchanged.

## Fail-closed receipts implemented

- authenticated pool H5/manifest identity, release period, pinned ACS archive
  SHA-256, exact archive-member scan, and source-row identities;
- raw ASEC `WKSWORK` domain, row/year counts, and raw ACS `WKWN` plus validated
  `FWKWNP` domains;
- the exact joint ACS `WKWN` blank/nonblank by allocation-status cross-tab;
- exact semantic key set/digest and one-to-one `SERIALNO + SPORDER` join,
  including source-person, support-row, clone, and match counts;
- the joint origin by clone-role table using the established
  `by_source_channel_and_clone_index` pattern, exact global roles 0/1/2, and
  zero per-source clone disagreements;
- ACS blank-to-zero recode ownership/counts, conflicting pre-existing-value
  rejection, and an independently derived canonical source-value digest bound
  to authenticated staged `WKSWORK`/joined `WKWN` rather than self-attested
  operation output;
- byte-sensitive column-diff proof that only `weeks_worked` changed; and
- source/gate receipt propagation through build, release, and calibration
  manifests. Target-frame checkpoint materializer v13 prevents a pre-weeks
  checkpoint from bypassing the measured leaf.

## Commits

- `b71ca20a` — preserve the authorized ruling plan as inherited WIP.
- `ff9f9b7c` — start the committed implementation journal.
- `268ad894` — add the authenticated declarative source stage, runtime, gate,
  and primary adversarial tests.
- `0fe9a074` — wire the stage before release selection and hours gating, with
  manifest propagation.
- `51736ae6`, `55521f39` — bind ORG/FLSA, SPM, export, and 2025 period-boundary
  regressions.
- `deb42a37`, `4266de0e` — refresh compiler attestations and bind the official
  ACS archive identity.
- `62570929` — journal the resumed final verification.
- `55d345fe` — invalidate target checkpoints created before the weeks stage.
- `e943aeb0` — bind gate receipts independently to live measured sources and
  add coherent-fresh-rehash attack regressions.
- `b8ea8252`, `51ea5721`, `d074f0d0` — refresh the remaining exact semantic
  identities and classify weeks as a release-only source declaration.

## Verification

- Focused weeks gate/runtime: 31 passed.
- Complete release builder: 235 passed.
- Consumer/period-boundary regression files: 62 passed.
- Complete spec-engine/bundle corridor: 311 passed.
- Complete multispine pool-tool file: 187 passed.
- Plan/source-runtime/spec-bundle corridor: 95 passed.
- Repository-wide suite from clean commit `d074f0d0`: 7,592 passed, 83 skipped,
  2,462 warnings in 3,902.41 seconds (1:05:02).
- Repository-wide Ruff: green.
- CI inventory: 315 tracked test files; verification green.
- Generated US bundle check: green at
  `e9ea75c7cc5a1613f0fde007f1061ad23dbf8e2d3c4574523c5469f77b8209ed`.
- Spec coverage: 41,558/41,558 fields and 41/41 inventory checks.
- Diff/status hygiene at the tested implementation commit: clean.

## Deviations and operational boundary

There are no deviations from the binding plan. The independent-digest gate
hardening, live-count re-derivations, release-only source classification, and
checkpoint v13 bump are necessary fail-closed/integration follow-through for
the plan's authenticated measured source and only-weeks guarantees; they do
not change its semantics, gates, or thresholds.

No data build was run. Candidate-25 was not modified. No artifact was
published, and no push or PR was created.
