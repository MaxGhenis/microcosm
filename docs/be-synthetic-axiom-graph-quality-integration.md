# BE synthetic Axiom graph and quality integration

`packages/microcosm-build/tests/test_be_axiom_graph_quality_integration.py`
exercises source construction, real Axiom measure execution, count calibration,
export, reload, and quality aggregation on nine invented people in four
invented households. It is an engineering seam, not a Belgian model.

## What actually executes

The measure node compiles and runs
`be/statutes/income_tax/individual/rate_scale.yaml` from a `rulespec-be`
checkout through `microcosm.frame.adapters.axiom.AxiomEngine` and the native
Axiom dense extension. No tax rule is restated in the test: the kernel hands
the population's own `belgium_pit_taxable_income` column to
`AxiomEngine.materialize` and returns what the engine computed, recording the
module digest, the dense-extension digest, the arithmetic mode, and the
variable's engine-declared entity, dtype, and period in its receipt. The
kernel's `implementation_hash` mixes in the module and extension bytes, so an
edit to the encoded statute or a rebuilt engine rekeys the node instead of
serving a stale cached result.

The source node decodes invented CSV tables through the production
`csv-tables` codec. The reweight node is the shared, country-neutral
`calibrate.adam@1` kernel, registered unmodified; only the source, the
all-ones count measure, and the Axiom measure kernel are test-owned.

## The legal period is read, not chosen

The module carries exactly one version, `effective_from: 2025-01-01` (CIR 1992
article 130, income year 2025 / assessment year 2026), so the slice executes at
2025. The BE bundle's own `dataset_run.target_period` is 2023, bound to
`be_silc_2023`; executing the module there is refused by the engine
(`no formula version at 2023-01-01`) and a test asserts that refusal rather
than letting a convenient period be picked silently. Reconciling the SILC
reference year with the encoded statute's period is real, unfinished work
outside this slice.

## Only inputs leave

The article 130 base tax is a formula the engine owns. Exporting it as a
dataset column would make a derived legal result look like a model input and
would mask any reform, so the adapter's export gate refuses it; a test asserts
the refusal names the column, and the exported frame drops it. The export runs
under a closed contract naming exactly the input surface, and the reload
compares equal on values, order, and dtypes, including the `string` NUTS1 codes
and the `bool` filter column.

One limitation is pinned by its own test: the entity-table format carries
weight *values* in a `household_weight` column but no weight *kind*. A reader
that needs `CALIBRATED` must get it from the frame or a sidecar.

## Geography

Quality artifacts cover the national level and NUTS1 only, matching the BE
`national_and_nuts1_admin_aggregates` gate's declared levels. The NUTS1 vintage
string is read from the country package's own target-reference selectors rather
than spelled in the test, so a spec change cannot leave a stale vintage in an
artifact. Household NUTS1 must be unanimously carried by that household's
members; disagreement is refused rather than resolved by picking a member.

The commune layer is deliberately absent. `clone_assign_communes` is an
unimplemented declaration, and inventing a commune assignment would be a fake;
a test asserts the spine's declared `commune_nis` column appears nowhere in the
export. The NUTS1 codes travel the identical string path, so code-string
preservation is proven there.

## Observed zero versus unknown

The fixture carries a person with a taxable income of exactly zero, whose
article 130 liability is a computed zero, not a null, and who lands in the
lowest distribution bin with no missing mass. Separately, the NUTS1 catalog
declares an `UNKNOWN` bucket that nothing is observed in: it stays visible in
every partition at zero weight, zero records, and null ESS. The BE catalog
declares `person.region_nuts1` non-nullable, so the fixture introduces no null;
a separate test injects one, removes the declared bucket, and asserts the
producer refuses instead of dropping mass.

## CI placement

The file is engine-gated, but its engine is the Axiom rules engine over a
`rulespec-be` checkout, not PolicyEngine-US or -UK. Routing it into either
country lane would attach a Belgian test to another country's release surface,
so `tools/ci_test_groups.py` lists it explicitly in the shared lane. It
collects and skips in 0.16 s wherever the engine and checkout are absent, which
is everywhere in CI today. To run it:

```bash
POPULACE_RULESPEC_BE=/path/to/rulespec-be uv run pytest \
  packages/microcosm-build/tests/test_be_axiom_graph_quality_integration.py
```

with the Axiom Python wrapper and its built dense extension importable.

## What is not claimed

Not Belgian tax-benefit coverage: one module, one derived output, before every
reduction, credit, surcharge, regional reduction, and communal addition. Not
SILC: no restricted microdata is opened, referenced, or approximated, and no
mapping from any wage concept to taxable income is inferred — the module's
single input is supplied directly as an invented figure. Not a population: nine
invented people prove nothing about Belgium. Not calibration evidence: the
count margins are invented, chosen from the fixture's own totals to exercise a
feasible solve, and are not administrative references. Not a release: the
posture is fixed at `synthetic_engineering_not_release`, `release_eligible` is
`false` everywhere it appears, no gate or release kernel is registered, and no
US or UK source, calibration, doctrine, or release behavior is touched.
