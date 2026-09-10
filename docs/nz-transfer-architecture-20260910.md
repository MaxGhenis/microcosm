# NZ transfer architecture reconciliation — 10 September 2026

This note describes development work on `nz-us-transfer-candidate-20260910`,
based on upstream repository `origin/main` at
`6f7571e1a` (the repository names its PolicyEngine remote `origin`, not
`upstream`). It is implementation evidence, not dataset certification. The US
integration source checkout was inspected without reading its runtime or error
artifacts.

This is a bounded readiness packet. The local presentation ports are preparatory
code pending reconciliation with the upstream shared-adapter work. Development
will wait for an approved US donor after the tiny fixture checks; these ports do
not authorize further shared-engine changes or a population build.

## Existing NZ work to retain

PR [821](https://github.com/PolicyEngine/microcosm/pull/821), branch
`codex/nz-transport-microcosm`, adds a country specification, sources, targets,
gates, export/release contracts, and a real Axiom Frame bridge. Its branch-only
delta against its merge base is 26 files. A straight comparison to present main
also contains unrelated changes from the intervening history, so that comparison
is not a suitable port checklist.

The useful adapter changes are `NZ_SCHEMA` (person, household, family),
`AxiomPeriod` (explicit dates and period kind), and dense engine materialization
of period/unit boundaries. Port them independently of old spec resolver changes.
The old branch does not provide the current executable NZ shared graph.

The older [plan](nz-take-up-engine-plan.md) and
[target inventory](nz-calibration-targets.md) remain useful source inventories.
PR821's historical sparse Build-P US extract is not the desired donor contract.
Prefer a pinned full common US Frame with all support arms/clones retained;
national calibration and pruning are downstream choices. Receipt counts and
spending observations cannot calibrate full entitlement into an apparent take-up
estimate. Individual income margins also do not observe NZ couples' joint
income, housing costs or liquid assets.

## Current shared APIs

`microcosm.frame.EntitySchema` defines entity membership. Persons carry
`person_household_id` and `person_family_id`; group tables carry `household_id`
and `family_id`. `Frame` validates these links. Keep recipient families distinct
from US tax units; preserve the US units only as donor provenance. Only household
weights should anchor the candidate. Derived measures should use Frame mapping
and aggregation operations rather than independent entity weights.

`microcosm.graph` provides `Graph`, `Node`, `Slice`, `Owned`, `SourceRef`,
`StructuralDelta`, `WeightTransition`, `KernelRegistry`, `compile_graph`,
`run_graph`, and `ContentStore`. The source codecs `csv-tables` and `frame-store`
both exist on the base commit. The latter loads a verified content-store Frame
directory and is a useful eventual donor handoff format.

Only a CREATE node returns `KernelResult.frame`. It should load the source bytes
through a declared codec, validate the donor contract, construct recipient
entities and retain explicit donor IDs. Subsequent nonstructural kernels receive
only their declared `KernelContext.tables` slices and return entity-indexed
column patches. Structure must not be rebuilt invisibly inside these kernels.

EXPAND kernels return new IDs mapped to old IDs in `KernelResult.expand`; the
executor carries every column and records clone lineage. They also return the
appropriate weights. FILTER removes support explicitly; do not use it merely to
turn the donor into an already-pruned national extract. REWEIGHT returns typed
weights and declares `WeightTransition("household", "calibrated", mass=...)`.
The mass contract concerns weighted person mass, including stratum/partition
accounting. Choose a declared transition when changing population scale.

The shipped imputation wrapper is `microcosm.fit.kernels.QRF_KERNEL`
(`fit.qrf@1`). Its one input slice carries both donor and recipient rows,
predictors, `is_donor`, a complementary recipient mask, and `donor_target`.
Its one float64 output declares that recipient mask. `donor_target` must be a
different coordinate from the output to avoid ownership cycles. The executor
seed is default; explicitly select the parameter-seeded variant if needed. Its
receipt retains fit/draw details and the trusted store retains the fitted model.
It declares platform-level reproducibility, not cross-platform equality.

`microcosm.calibrate.kernels.CALIBRATE_ADAM` wraps the real shared optimizer.
Its target parameter is a tuple of `(name, measure_column, filter_column, value,
standard_error)` tuples. All target columns must be in the declared calibrated
entity slice. It records `diagnostics_payload(result)` in the receipt, including
per-target achieved values. It transports but does **not** use target standard
errors in its loss (`consumes_se=False`). Do not describe the fit as uncertainty
weighted. Holdout targets must stay out of the optimizer's target tuple and be
evaluated on the resulting weights separately.

Useful executable references are
`packages/microcosm-graph/tests/fixtures/parity/kernels/calibrate/graph.json`,
`packages/microcosm-fit/tests/test_kernels.py`, and
`packages/microcosm-graph/tests/_toy.py`. The latter is a graph-contract fixture,
not a source of NZ population or policy assumptions.

## Geography and donor dependency

The US integration checkout includes country-neutral
`microcosm.build.atomic_geography` and `graph_atomic_geography` modules. The
public operations are `encode_atomic_support`, `decode_atomic_support`,
`validate_assignment_spec`, `assign_atomic`, `derive_geography`, and
`validate_geography`. `atomic_geography_nodes` declares support import,
assignment, derivation and integrity-gate nodes; countries supply normalized
support bytes and declarations. These modules are not on this task's base and
their graph adapters require the newer typed artifact and raw-source APIs.

Do not port the US PUMA/tract/CD rules or observed-geography qualifiers as NZ
recipient geography. For the first honest fixture, declared NZ fixture atoms
and a reproducible assignment are sufficient if clearly labeled as invented
support. A population candidate needs actual NZ atomic-area support and mappings
to relevant policy areas. US location may remain lineage. The eventual donor
handoff must state the source commit, file/directory digests, scope, support
arms, clone policy, entity IDs, measurement periods, source access constraints,
and whether any location/pruning operation has already occurred.

## Reused Orrery export

The task ports the reusable `microcosm.graph.explorer` adapter and tests from
`1b8be6a5e69ad44f442bd01b192dc1501fdd663e` (CLI adoption, descended from original
adapter `b97659bf8a58b130de3c88395904b15bb7382aa4`). It also ports the bounded
`graph_schema` producer and tests from
`07573bd8ed63ceb9ae5234395dbfd949c431dcd7`. The only schema adaptation removes
typed `ArtifactInput`/`ArtifactOutput`/`ArtifactType` references absent from this
base. No graph runtime interface or Orrery source changed.

`graph_schema(compiled)` recompiles the actual declarations and checks the
compiler tables before exporting visible field versions and input bindings.
`graph_explorer_json(schema)` converts the result to Orrery's existing
`graph-explorer/v1` format. Both are value-only operations.

`graph_run_explorer_document(compiled, manifest, reports=report)` adds recorded
receipts to the corresponding operation nodes and a distinct diagnostics node
for every top-level report section. Exact integers are preserved with transport
tags. It checks country, node roster and kernel references; those checks alone
do not authenticate the declaration-to-run association. The owning runner must
retain that association from execution. Report values are supplied evidence and
never inferred gate or release verdicts.

The saved-run command validates the manifest and referenced content-store
artifacts before invoking the unchanged Orrery CLI:

```sh
uv run python tools/export_nz_transfer_orrery.py \
  --graph run/graph.json --manifest run/manifest.json --report run/report.json \
  --viewer-cli /path/to/orrery/package/dist/cli.js --out run/nz.html
```

It also writes `nz.graph-explorer.json` and `nz.export.json`; the latter records
CLI, document and HTML digests. The CLI is an explicit input, with no implicit
download, upgrade or deployment. The development check used the existing
accepted `@axiom-foundation/graph-explorer` 0.3.0 archive, SHA-256
`a612db7c1e51e8f7bbde9240ca71d7412443911fff8361593055189391ec9a33`, from source
`b7ea50fbea9ffa062ec2136fca9a73096c50f587`. This is a known accepted local
artifact, not a claim about the newest available Orrery release.

Validation: 52 targeted schema, adapter and evidence-binding tests pass. A real
five-operation toy graph was run through the shared executor, saved, loaded with
artifact validation and exported through that exact Orrery CLI. The output
contained 19 nodes/22 edges, five receipt-bearing operations and four labeled
diagnostic sections; Orrery's own `parseGraphDocument` accepted it. This checks
the export integration only. Browser QA and the actual NZ candidate's fit,
holdout, AS coverage and entitlement evidence are separate checks.
