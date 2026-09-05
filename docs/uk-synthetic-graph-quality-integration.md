# UK synthetic graph and quality integration

`packages/microcosm-build/tests/test_uk_graph_quality_integration.py` exercises
source construction, count calibration, export, reload, and quality aggregation
on four invented households, five benefit units, and five people. It performs
no tax or benefit calculation and requires no PolicyEngine country engine.

The source rows come from the committed, generated UK graph parity fixture;
the test reduces it and adds a second benefit unit to one household. Each
temporary source file receives its actual content digest and byte size in a
separate synthetic source declaration. The production FRS manifest is unchanged.

The graph contains the actual UK factory's CREATE node, bound to
`UKFRSSpineStageTransform`, followed by a test-owned REWEIGHT adapter that calls
`UKNationalCalibrationStage`. That adapter adds temporary all-one measures to
the real person, benefit-unit, and household tables and uses explicit invented
count targets. It retains the current national solver doctrine. Source rows,
memberships, columns, and strata remain unchanged; calibrated household weights
flow to the other entities through `Frame.resolve_weights`.

The count targets use period 2025 while the source observations retain period
2024. This is an explicit infrastructure fixture, with no demographic aging,
price adjustment, or population-representativeness claim. Count targets are
chosen from the fixture's own weighted totals to exercise a feasible solve;
they are not external administrative evidence.

The real UK HDF writer and loader retain table values, nulls, dtypes, indices,
household weight kind, and ordered Frame mass history. The fixture explicitly
sets pandas string storage to `python` throughout because the graph uses that
representation and the HDF reader otherwise follows pandas' configured backend.
It does not claim arbitrary Frame metadata or physical HDF bytes are identical
across writes. Each quality record binds the digest of its actual exported file.

Support and fixed-bin age distributions use the shared quality producer and
canonical typed weight resolution. The explicit national and regional catalogs
have distinct declared vintages and an unknown-region bucket. Every regional
partition, including empty areas, reconciles to its national total. Household
region is broadcast to people using Frame; benefit-unit region is added only
to a separate evidence view after all actual members agree, with explicit ID
alignment. There is no arbitrary representative-member selection.

The tests cover cold execution, required cache replay, changed count targets
reusing the source, direct national-stage weight equality, export/reload parity,
all three entity masses, missing geographic catalog refusal, and benefit-unit
geography disagreement. Run them with the normal workspace test environment:

```bash
uv run pytest packages/microcosm-build/tests/test_uk_graph_quality_integration.py
```

This test-owned adapter emits `synthetic_engineering_not_release` evidence with
`release_eligible: false`. It produces no signed terminal gate, release-cut
attestation, policy evaluation, donor model, or certified reference comparison.
It cannot establish readiness for a UK release. The licensed-source campaign,
local-authority calibration, and policy calculations retain their existing
owners and release requirements.
