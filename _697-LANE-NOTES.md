# microcosm#697 lane notes — column closure and take-up tracing

Recorded 2026-08-15 on branch `lineage-column-closure-697`, starting from
`f7173120`.

## Delivered artifact inventory

- Added `tools/emit_artifact_column_inventory.py`, which inventories any built
  pool H5 as sorted, unique `entity/column` names.
- When a manifest is supplied, the generator checks artifact basename, size,
  and the actual streamed SHA-256 before copying provenance into the fixture.
- Committed `specs/us_pool_column_inventory.json` for `probe-f025-r1`:
  - artifact: `populace_us_2024_stacked_pool_probe.h5`
  - SHA-256: `c2789a2edcdc57a7317de6a65a4d4ed0cce842ade8483c420f2a7d1d21d6bbb5`
  - publication run: `d8198a9e4ab94e8083a26a0f63d8511a`
  - inventory size: 392 columns across six entities
- A fresh generator run against the supplied read-only f025 H5 and manifest was
  byte-identical to the committed fixture.

## Exact-one closure

The global artifact owner counts are:

| Lineage class | Columns |
| --- | ---: |
| modeled (union of imputed targets and computed outputs) | 123 |
| measured/native | 203 |
| take-up | 13 |
| receipts/provenance | 7 |
| structural | 43 |
| assigned by geography ladder | 3 |
| reasoned unclassified debt | 0 |
| **total** | **392** |

`imputed_families` and `computed_producers` are two declarations of one modeled
class because 90 artifact columns intentionally occur in both stage layers.
Where an existing modeled declaration also names a more specific native,
structural, or take-up artifact owner, the spec uses an explicit and
column-local `supersedes_modeled: true`; there is no blanket precedence rule.

The full lowercase ASEC carried surface is also enumerated. Four columns are
globally measured/native; the remaining mixed-channel columns retain the
modeled owner because the other support channel imputes them. A conformance
test compares this documentary split to the live `CPS_CARRIED_*` surfaces.

The audit's heuristic structural allowance had treated
`puf_capital_gains_tail_transfer_weight` as structural. Code tracing showed it
is one of the six capital-gains-tail donor provenance outputs, so it is owned by
`receipts` with the other five. The seventh receipt-class column is the
deterministically completed Schedule D distribution input.

The supplied transient `_closure_audit_unclaimed.json` was consumed as an audit
cross-check, then removed rather than committed; the pinned inventory and
closure resolver now reproduce its purpose without a second partial fixture.

The geography contribution is intentionally a minimal, replaceable
`geography.assigned_by_ladder` block for `puma`, `puma_geoid`, and `state_fips`.
Every entry says `mechanics: pending microcosm#696 lane`.

## f025 take-up findings

Only TANF and EITC are stochastic draws in the built f025 pool. Medicare and
housing are complete transferred/measured assignments. The other nine columns
were entirely filled with the installed engine's disclosed `true` default at
the pool seed stage. Dedicated fiscal source stages later replace five of those
nine (SNAP, Medicaid, SSI, Head Start, and ACA); those downstream mechanisms are
recorded separately in the spec so they are not mistaken for f025 production.

| Flag | f025 true / false | Artifact mechanism | Dedicated downstream mechanism |
| --- | ---: | --- | --- |
| `takes_up_snap_if_eligible` | 868,956 / 0 | engine default | reporter anchor, national precursor, then greedy state count targeting |
| `takes_up_tanf_if_eligible` | 190,743 / 678,213 | stable Bernoulli at 0.219 | none |
| `takes_up_eitc` | 814,010 / 365,854 | stable Bernoulli at child-count rates | none |
| `takes_up_medicaid_if_eligible` | 1,970,973 / 0 | engine default | reporter-anchored CMS state count targeting |
| `takes_up_chip_if_eligible` | 1,970,973 / 0 | engine default | none; CHIP concept split remains unresolved |
| `takes_up_basic_health_program_if_eligible` | 1,970,973 / 0 | engine default | none; rate source remains unresolved |
| `takes_up_medicare_if_eligible` | 460,082 / 1,510,891 | measured MCARE mapping and transfer | none |
| `takes_up_ssi_if_eligible` | 1,970,973 / 0 | engine default | reporter anchors plus SSA-derived age-band priors; not exact flag count matching |
| `takes_up_dc_ptc` | 1,179,864 / 0 | engine default | none; model-relative 0.32 is rejected |
| `takes_up_head_start_if_eligible` | 1,970,973 / 0 | engine default | stable source-person SIPP QRF for ages 3-5 |
| `takes_up_early_head_start_if_eligible` | 1,970,973 / 0 | engine default | none; the available SIPP item does not identify EHS |
| `takes_up_housing_assistance_if_eligible` | 24,415 / 844,541 | receipt-derived transfer | none |
| `takes_up_aca_if_eligible` | 1,179,864 / 0 | engine default | Marketplace reporter anchors and CMS state count targeting |

For every flag, the spec records artifact producer/stage, probability source,
unit and eligibility conditioning, seed/determinism, calibration status, f025
counts, live contract treatment/default/rate status, and module-and-line source
citations. The conformance test compares the structured contract facts and
seeded rate values to the checked-in live contract.

## Dashboard and conformance

- Added an additive `counts.coverage` object to the lineage emitter with
  `claimed`, `total`, `per_class`, `unclaimed`, `multiply_claimed`, and
  reasoned-unclassified `debt` fields.
- Added only data for the new classes; no site rendering changed.
- Added `packages/microcosm-build/tests/test_lineage_column_closure.py` rather
  than modifying the existing lineage conformance test.
- The closure test pins the f025 fixture header and 392-column boundary, rejects
  unknown or multiply claimed columns, requires all `takes_up_*` columns and
  mechanism fields, checks live take-up-contract and ASEC-carried surfaces, and
  rejects a false manifest SHA.
- `MICROCOSM_LINEAGE_POOL_H5` opts into regeneration drift checking; the test
  skips when the environment variable is absent.

Validation recorded for this lane:

```text
.venv/bin/python -m pytest packages/microcosm-build/tests/test_lineage_column_closure.py packages/microcosm-build/tests/test_imputation_lineage_spec.py -q
......s......

MICROCOSM_LINEAGE_POOL_H5=<f025 H5> .venv/bin/python -m pytest packages/microcosm-build/tests/test_lineage_column_closure.py -q
.......

.venv/bin/ruff check .
All checks passed!
```

No pool/release pipeline build or certification was run. The supplied f025 H5
and manifest were read only. This lane used no network, made no push, and did
not modify `PROGRESS.md`, `predictor_sets`, or `imputed_families`.

## Local commits recorded before this journal

- `e5e37adf` — Add pool column inventory fixture (#697)
- `1b588f45` — Declare total pool column lineage (#697)
- `adf81d65` — Enforce lineage column closure (#697)
