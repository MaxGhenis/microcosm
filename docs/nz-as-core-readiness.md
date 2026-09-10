# NZ Accommodation Supplement core readiness

This is a development input/engine boundary, not a population estimate or a
release certificate. `microcosm.build.nz_policy` binds the existing shared
`SimulateRulesKernel` to real Axiom software. It does not implement policy
formulas or turn observed receipt/spending into entitlement.

## Pinned content and runtime

Checked on 10 September 2026:

- [RuleSpec NZ main](https://github.com/TheAxiomFoundation/rulespec-nz/tree/5444a0263fdb4ceb1e767eb30d701f71cd38f843)
  was `5444a0263fdb4ceb1e767eb30d701f71cd38f843`. Its AS core blob
  `506a3769e1ee78e7601f1619c0debec3b32e3a7d` matches the local inspected
  checkout `635801507e988a049f0bb4b6cfc9a660a3c587cf`.
- Bound module: `nz/statutes/social_security/accommodation_supplement/core.yaml`.
  SHA-256: `f2feca3c2f1de71623ccd577cd2aed20e8822614aac0ccfc767b5faf4eaa83cc`.
  The binding rejects different module content before execution.
- Real dense execution uses the rehearsal's public-source Axiom runtime pinned
  to `05eac9d2f89dabe5c6673176260762cef3a58f47`, running under Python 3.14.4.
  This reuses software only; it does not reuse any synthetic HLFS records,
  pooled weights, or outputs, nor the US launch owner's private runtime files.
- The graph's `engine_ref` hashes the module, native extension, Python wrapper,
  helper and base adapter bytes, entity schema, and assumption/provenance
  settings. This identifies execution; it does not certify encoded sources.
- [RuleSpec NZ #117](https://github.com/TheAxiomFoundation/rulespec-nz/pull/117)
  remains an open draft at `3b663b3e6eb6408351154990be0c4b92d42c92da`,
  mergeable with an unstable check state. Its Family transport contract is for
  WFF reform comparisons; it does not supply the missing AS composition.

## Input and period contract

The compiled module has 39 eager root inputs on `Family` and no dense relations.
The helper exposes their exact names as `AS_REQUIRED_INPUTS`; the family table
must supply all of them with booleans or numeric dtypes as appropriate.
Amounts named weekly are NZD per week, cash assets are an NZD stock, and premises
areas use a common area unit. No donor currency conversion occurs in the helper.

`accommodation_supplement_input_coverage` reports absent columns, null values,
infinite values, invalid types, and unclassified/assumed input provenance
separately. Zero is a value, never evidence of completeness by itself. Reported
counts are unweighted diagnostics. It does not fill anything. Explicit
`allow_assumptions=True` permits a named scenario using the caller's recorded
assumptions; missing, invalid, or unclassified inputs still block execution.

The current shared Axiom adapter supports calendar-year or month bounds, not an
NZ April-to-March tax year. This binding only permits the April 2026 snapshot
`2026-04` and refuses annualization. Although RuleSpec metadata labels these
rules `Year`, the core formulas and output names define weekly monetary amounts;
calling with a month selects effective rules and does not convert them to a
monthly amount. The exact companion case confirms the weekly rate remains 305.

`make_as_fixture_inputs` explicitly reproduces the 39 values of the first
RuleSpec companion case: a sole-parent renter with two dependent children in
AS Area 1. Every input is labeled `fixture`. Replicating this scenario only
exercises transport and runtime; it is not an imputation model or NZ population.
Keep its graph separate from the US-to-NZ donor fixture graph.

## Validated outputs and missing final entitlement

The helper requires both raw outputs together:

- `accommodation_supplement_non_rate_entitlement_requirements`: holds (`1`),
  does not hold (`-1`), or undetermined (`0`). Storage widens Axiom's `int8` to
  graph-supported `int64`, preserving the codes.
- `accommodation_supplement_rounded_weekly_payment`: the core's rounded weekly
  rate calculation, returned without alteration.

In the official companion renter scenario, cash assets of NZ$1,000 give
judgment `1` and weekly rate NZ$305. Changing only cash assets to NZ$20,000
changes the judgment to `-1` while the independent rate remains NZ$305. The
rate is therefore **not final entitlement**. Python must not combine these
outputs into a new policy formula.

The current upstream tree contains the atomic AS core and its companion tests,
with no AS ProgramSpec or composed final entitlement module. Its module summary
explicitly leaves the delegated base rate and non-beneficiary income cutout as
external inputs. The bound module also does not wire a general residence check.
A final entitlement claim needs the relevant Axiom composition, validated inputs
for those cross-module boundaries, and an appropriate period contract. The
coverage report consequently always records `full_entitlement_computable=false`.
No take-up or receipt estimate is produced.

## Validation and handoff

`packages/microcosm-build/tests/test_nz_policy.py` contains portable coverage
checks and optional real-engine checks. The latter exercise both the direct
adapter and the actual shared graph executor with two fixture families, including
content-verified Frame source loading. They also verify the asset/rate distinction,
period refusal, and explicit assumption handling. No Axiom source files or
shared engine internals were changed.

To run the native checks, provide the pinned Axiom Python package/native
extension on `PYTHONPATH` and set `MICROCOSM_RULESPEC_NZ` to an absolute canonical
RuleSpec checkout containing the pinned AS core. Then run:

```sh
uv run pytest packages/microcosm-build/tests/test_nz_policy.py -q
```

The remaining donor dependency is an approved immutable full Microcosm US Frame
with all support clones and exact lineage. Until that handoff, freeze this small
readiness fixture. Its successful execution provides no evidence that US
housing, asset, relationship, or income distributions represent New Zealand.
