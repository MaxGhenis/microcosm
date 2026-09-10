# NZ transfer readiness — 10 September 2026

**Frozen preparation, awaiting an approved US donor.** Max's updated sequencing
keeps the US common-Frame launch first. This packet preserves local implementation
and tiny synthetic checks. It does not authorize donor acquisition, a real NZ
population build, deployment, publication, or take-up estimation.

Owned branch: `nz-us-transfer-candidate-20260910`, fresh from PolicyEngine
`origin/main` at `6f7571e1ab8c516154289bd8ebf75cb2646f03b5`.
The US owner's source reference is PR893 at
`f4e5ec4eb761e26f65667f693ef37d3ea68adfc8`; no approved full new-architecture
artifact, locator, manifest hash, distribution approval, or donor certification
exists yet. Source code is not a donor release. Existing dirty checkouts and
the old NZ branch remain untouched.

## Required donor handoff

The proposed thin input is **one authenticated full Frame plus one immutable
handoff manifest**, not a country-specific exported H5. NZ should accept it only
after the US owner explicitly identifies it as available for this use.

| Manifest field | Required content |
| --- | --- |
| Identity | Schema version; artifact ID/namespace; source commit; manifest SHA-256; every file's SHA-256 and size; complete directory inventory; immutable URI or approved local path. |
| State | Explicit development/release status, selected graph stage, validation report, known failed gates, full/pruned scope, geography status, and approval for NZ development use. Never infer this from package version or filename. |
| Software | Source revisions for all shards, `uv.lock` hash, resolved distribution versions, graph JSON/hash, run-manifest/hash and source/assembly receipts. Current `0.1.0` strings alone are inadequate development identities. |
| Entities | Unprojected person, household, tax_unit, spm_unit, family and marital_unit tables; exact int64 IDs and every person-to-group membership. Preserve original tables in provenance even when NZ only projects selected measurements. |
| Lineage | On every entity: `{entity}_spine_source_id`, `{entity}_source_id`, `{entity}_support_channel`, `{entity}_support_clone_index`; source-origin keys and clone paths; inventory/counts for every support arm. |
| Stable origin | Literal `survey_geography_origin_key`, currently JSON `[channel, source_year, survey_year, raw_native_id]`, plus household clone index. Preserve leading zeroes. Numeric remapped household IDs are not cross-cohort identities. |
| Weights | Household is the calibrated weight source. Identify design/importance/calibrated stage; preserve design/source-origin values. State clone mass allocation; PUF-detail clone 1 is support on ACS/ASEC, not another PUF population. |
| Measurement | Per-field entity, concept, dtype, null/value codes, currency, stock/flow, period start/end, survey/source years, growth transformations, observation/imputation status, donor selection and coverage. ACS, ASEC and PUF conventions differ. |
| Use terms | Source access and distribution restrictions, permitted transformations, publication limits, and permitted storage. No public redistributability inferred from public source code or another dataset's terms. |

The eventual admission check must authenticate all files and receipts, validate
the stated schema and complete support roster, and distinguish missing values
from measured zero. It must refuse an unsupported stage or unapproved use.
The current executable admission is intentionally **fixture-only** and refuses
other input status; it is not a production donor approval mechanism.

Recipient IDs retain namespaced donor keys containing the exact source artifact
identity and decimal-string source IDs. Original US groups remain provenance.
NZ family/assessment units require a separately reviewed relationship mapping;
US tax/SPM units cannot silently become NZ benefit units. The tiny fixture
explicitly splits unrelated adults and includes multifamily households, but
does not implement the complete legal NZ family definition.

## Shared API observations for the US owner

1. At base `6f7571e1a`, `ContentStore.put_frame`/`load_frame` round-trip tables,
   memberships, strata and weights, **but not general `Frame.metadata`**.
   A fixture with metadata `status=synthetic_fixture` returns without that
   metadata. **This is a main-baseline gap already addressed in unmerged PR893**
   at `f4e5ec4eb761e26f65667f693ef37d3ea68adfc8`: its tagged complete metadata
   codec binds a metadata hash and refuses changed metadata under the same key,
   stale codecs and malformed metadata. Source inspection on 10 September
   verified `packages/microcosm-graph/src/microcosm/graph/store.py` SHA-256
   `1f594051931419585babd72229e9de7d2a9e8827e39d835fb52add0e23cad386`
   and `packages/microcosm-graph/tests/test_frame_metadata_store.py` SHA-256
   `3d501901be632437a285bee625d3c19b9af3561564d6d30b129fdd9bc10699f3`.
   Those tests cover nested types, identity and corruption; they were inspected,
   not rerun in the US owner's checkout. Keep approval, measurement,
   restrictions and status in an authenticated handoff manifest regardless of
   metadata-codec support. No shared runtime patch was made here. The US donor
   still awaits full host and post-clone acceptance; this clarification does
   not unfreeze the NZ build.
2. The US integration's `atomic_geography_nodes` and typed artifact APIs are
   ahead of this base. NZ must adopt the accepted shared version once stable;
   avoid porting US location semantics. Fixture geography uses explicitly
   synthetic REGC2025 support atoms. Actual AS needs SAU2017-based policy-area
   mappings with effective dates, not a region-to-area guess.
3. The existing Axiom AS core has 39 root inputs but no bound final entitlement
   composition. Its weekly rate can remain positive when its separate non-rate
   judgment fails. The NZ helper uses shared `simulate.rules@1`, widens native
   judgment storage from int8 to graph-supported int64 without changing codes,
   and refuses annualization or an unqualified rate-only result.
4. Shared Adam calibration records standard errors but does not consume them.
   The diagnostic packet must not imply uncertainty-weighted fitting. QRF is
   reproducible on the same pinned platform, not guaranteed bitwise across OSes.

## PR821 integration assessment

The old draft is still open/conflicting at
`9f7deadd41f286242200937ad6cd4de92449b18f`. A read-only `git merge-tree` against
the owned base finds content conflicts in:

- `packages/microcosm-build/tests/test_country_spec.py`
- `packages/microcosm-build/tests/test_spec_engine_country_bundles.py`

Its 26-file branch delta provides useful NZ source/spec/export/gate declarations
and bounded WFF/Axiom tests. It does not contain a current shared transfer graph
or donor build. Its old sparse Build-P donor pin is not the new handoff. Preserve
the WFF cases and explicit period/Decimal checks; reconcile country discovery,
resolver/schema changes and tests against the accepted graph architecture before
porting. A conflict-free merge of the other files would not establish semantic
compatibility. This packet deliberately leaves PR821 and its branch intact.

Related draft state checked 10 September:

| Work | Head | State relevant to readiness |
| --- | --- | --- |
| Chronicle #209, WFF facts | `eb6ca1b3bcb56fe3e62afdf7fd5d84174337b6b1` | Open/conflicting; claimed non-zero assessed entitlement, not eligible population or cash paid. |
| Chronicle #211, population | `83335a44109f91ca52e8c1a4654499af74c4333c` | Open/conflicting; broad ages, not detailed age-by-sex. |
| rulespec-nz #117 | `3b663b3e6eb6408351154990be0c4b92d42c92da` | Open draft, mergeable/unstable; WFF reform handoff, not AS certification. |
| policyengine.py #508 | `5e933c78a9635e2e272f338d2d0dc0c0e1c5f0df` | Open draft; source-only pilot, no approved dataset established. Mergeability initially unknown. |
| calibration-diagnostics #175 | `e480d7563714011a79f84c716bf7784eadbf9520` | Open draft, clean/mergeable; release dashboard wiring, not a release manifest. |

The [evidence audit](nz-transfer-evidence-20260910.md) reconciles #343, #820,
wealth #592 and the local Chronicle income notes. The [architecture note](nz-transfer-architecture-20260910.md)
records retained work and the unchanged Orrery adapter lineage.

## Prepared executable evidence

`tools/build_nz_transfer_candidate.py` defaults to 72 invented people in 32
households and 36 recipient families, with two mass-split support clones.
It runs seven nodes through real `microcosm.graph`, `Frame.place`, `fit.qrf@1`
and `calibrate.adam@1`. No US policy result becomes an NZ measurement or output.

The graph exposes explicit fixture currency/period multipliers and synthetic
geography, a weight-aware asset-imputation exercise, household-based target
contributions, calibration and fit/holdout/AS coverage diagnostics. The asset
draw is a contract exercise, not an AS cash-asset proxy. The factor 1.6 is an
illustrative test input, not verified FX, purchasing-power conversion, or NZ
income uprating. Unknown AS fields remain absent. The general graph source
retains all six original donor tables and exact lineage.

The observed selection is 20 fit cells, 12 held-out regional-age cells and one
accounting check from Stats NZ's June 2025 population workbook, pinned to
SHA-256 `001e8a896cfb50f5ed17836dc815b235e3bcca55ee91c9869a2afaeb054b50a6`.
The national accounting total initializes design scale, so it is not an
independent validation target. Holdout cells never enter the solver. Published
rounding and outside-region coverage remain explicit; the NZ-minus-regions
600-person difference is not fabricated as a measured outside-region count.

The tiny run **fails demographic fit**, includes empty-support holdout cells,
and has **zero complete AS-input families**. This is expected workflow evidence.
Its gate remains `evidence_absent` regardless of fit, and its artifact status is
`development_fixture_only`. No population estimate is released or certified.

The [real AS checks](nz-as-core-readiness.md) separately run a named synthetic
sole-parent/two-child renter case through actual Axiom and the shared executor.
Raising assets to NZD20,000 changes the non-rate judgment to -1 while the
independent rate stays NZD305/week. This demonstrates the missing final
entitlement boundary; neither output is a take-up estimate.

Reproduce the bounded graph using the workspace lock:

```bash
env -u UV_FROZEN uv sync --all-packages --locked
.venv/bin/python tools/build_nz_transfer_candidate.py --out /tmp/nz-transfer-smoke
.venv/bin/pytest packages/microcosm-build/tests/test_nz_transfer.py
```

Use the existing Orrery renderer through `tools/export_nz_transfer_orrery.py`;
see its help and the architecture note. The local presentation ports add no
runtime changes and remain preparatory pending upstream adapter reconciliation.

## Next steps after the dependency is cleared

1. Receive the explicitly approved donor and handoff manifest; verify every
   identity/use term and accepted shared operator version. Resume only then or
   on further direction from Max.
2. Replace fixture-only admission and relationship/measurement declarations
   with reviewed NZ mappings. Bind the actual NZ atomic geography and source
   periods. Preserve all donor support before any calibration/pruning decision.
3. Reconcile and activate cell-pinned demographic/income/tenure/component-asset
   evidence. Inspect revised IRD TY2025 data and the housing-series caveats.
   Separate inherited household dependence from NZ observations; prespecify
   sensitivity scenarios for joint income, housing and threshold asset mass.
4. Supply legal/means/housing AS inputs, delegated rates and a real Axiom final
   entitlement composition, then validate per-case outputs. General residence
   and programme exclusions cannot be assumed away silently.
5. Run a small actual donor transfer and fit/holdout review before scaling.
   Keep receipt/spending outside full-entitlement calibration; verify Treasury
   comparators' take-up settings. Only then design the take-up estimate.

No IDI access or Treasury coefficient release is needed for the public-data
preparation above. Neither substitutes for the actual donor or AS inputs.
