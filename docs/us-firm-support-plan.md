# US firm support plan

## Decision and ownership

Microcosm owns construction and release of the US firm population artifact.
The standalone artifact is named `populace-us-firms`; dynamics consumes that
artifact but does not construct it. This follows the existing UK firm plan and
the US tariff runtime's treatment of non-household population artifacts.

The first frame uses observed Form 5500 plan-sponsor records and calibrates
their weights to SUSB firm-count and employment margins. It does not create
synthetic firm rows. OSHA ITA establishments remain an independent measurement
reference and are never unioned with the plan-sponsor donor population.

The implementation is ported, with credit, from Vahid Ahmadi's
`microcosm-dynamics` pull requests #386 and #390. Worker-to-firm assignment,
the IC1 spell schema, spell imputation, dynamics E-gates, and the canonical IC2
bander remain in dynamics. In particular, the Microcosm artifact carries raw
employment counts; dynamics applies its canonical 10/50/100/500 IC2 banding at
the consumption seam.

## Observation and measurement contracts

The sources do not observe one interchangeable unit or one interchangeable
employment concept.

| Source | Row or donor unit | Employment measure | Timing | Use |
|---|---|---|---|---|
| Form 5500 main | Filing, aggregated to sponsor EIN | Active plan participants | End of plan year | Frame donor |
| Form 5500-SF | Filing, aggregated to sponsor EIN | Active plan participants | End of plan year | Frame donor |
| OSHA ITA Form 300A | Establishment submission | Annual average employees | Calendar year | Independent measurement reference |
| SUSB 2022 | Legal enterprise within published industry and size cells | March 12 employment | 2022 | Calibration target authority |
| BDS 2022 | National firm-size cell | Annual employment stock | 2022 | Held-out national comparison where bands nest exactly |

A sponsor EIN is a filer key, not a demonstrated SUSB legal-enterprise key.
Multiple plans may overlap, so sponsor aggregation uses the maximum reported
active-participant count rather than a sum and takes metadata from that same
size-defining filing. Conflicting full NAICS codes, states, forms, and
plan-entity codes remain explicit provenance; they are not silently discarded.

Form 5500 plan-entity codes are source-specific strata. The initial port does
not assume that every filing is single-employer and does not silently pool a
single-employer plan with a multiemployer, multiple-employer, direct-filing, or
other plan/entity code. Whether production should filter to single-employer
plans or release explicit plan-entity strata is an open certification decision.

OSHA employment is establishment-level and its reporting universe is selected
by industry and size. OSHA cleaning therefore requires an explicit employment
cap, records every removal, and has no default cap. It is evidence about
cross-source measurement disagreement, never an enterprise reconciliation.

## Population and target universes

The calibration support uses a private build-time SUSB cell mapping. That
mapping combines NAICS 31, 32, and 33 as `31-33`; 44 and 45 as `44-45`; and 48
and 49 as `48-49` on both donor and target sides. Its employment intervals
mirror the SUSB detail aggregation needed to construct the five target cells.
It is not the IC2 wire type and is not exported as a canonical firm-size band.

SUSB excludes government establishments, Public Administration (NAICS 92),
crop and animal production, and nonemployers. The exact six-digit Form 5500
rules needed to reconcile crop and animal production remain open; the builder
must record rather than conceal any presently unresolved universe difference.

SUSB industry firm counts are non-additive for multi-industry enterprises.
Consequently, the sum of sector targets is not a national unique-enterprise
count. Both the sector-summed and national totals must appear in diagnostics,
and the artifact must not describe their difference as calibration error or
claim that sector weighting solves the sponsor-to-enterprise reconciliation.

NAICS 55 donors remain in the firm-count margin but their employment is outside
the employment margin: one plan sponsor can cover operating subsidiaries whose
workers SUSB assigns to other sectors. Rows carry
`employment_in_scope = false`; the exclusion is applied before calibration,
not merely attached after fitting.

## Target authority and migration boundary

Production target values come only from Ledger consumer facts selected by an
explicit target profile. The consumer-facts adapter requires caller-supplied
record-set, measure, sector-dimension, and size-dimension selectors; Microcosm
does not invent Chronicle package IDs or silently choose a target record set.
Diagnostics retain every selected fact key and target-period identity.

No Chronicle SUSB package or Ledger US firm target profile exists yet. The
committed SUSB 2022 extract is therefore a clearly named migration harness
only. It supports port-parity tests and a secrets-free synthetic PR-CI build,
but it is not a production fallback. The named follow-up is to create and
publish a Chronicle source package for the Census SUSB 2022 sector-by-enterprise
size facts and then register an explicit Ledger `us_firms` target profile.

BDS is not a calibration target. It is a national held-out reference only for
the bands that require no allocation: 1-9, 100-499, and 500+. BDS 20-99
straddles the 50 boundary, so the builder does not fabricate separate 10-49 and
50-99 comparisons.

## Artifact contract

The output is a standalone, firm-entity-conformant table with stable ordering
and at least these fields:

- `firm_id`, `source_firm_id`, and `source_firm_key`;
- positive `firm_weight`;
- raw employment and `employment_in_scope`;
- full NAICS, source NAICS sector, and SUSB calibration sector;
- plan/entity strata and conflict fields;
- source form, vintage, measurement timing, and hash provenance.

The current frame kernel requires a person entity and at least one partition
group, so a standalone firm population cannot truthfully be assembled as a
`microcosm.frame.Frame`. The builder emits the same standalone firm table
contract used by the UK precedent and does not fabricate a person-to-firm
partition. Supporting a native single-entity `Frame` is a separate kernel
follow-up.

Every build writes the firm table, the complete target-cell diagnostic table,
and a manifest that hashes both. The diagnostic artifact records all filters,
caps, recodes, deduplication choices, source measurement models, target fact
identities or migration-harness hashes, solver settings, failed calibration
attempts, margin ratios, bound hits, weight quantiles, maximum leverage, and
Kish effective sample size per cell and overall.

## Phase 1: pinned staging and readers

- Keep record-level data outside Git, by default under
  `~/PolicyEngine/firm-data/`.
- Pin raw URL, exact byte size, and SHA-256 for each source.
- Download to a partial file, verify before adoption, and refuse changed bytes.
- Enforce a 3 GB aggregate raw-and-expanded preflight limit.
- Preserve source identifiers and measurements without implicit cleaning.
- Cover readers and tamper refusal with small secrets-free fixtures.

## Phase 2: target activation

- Consume explicit Ledger facts in the production path.
- Keep the SUSB CSV loader named and labelled as a migration harness.
- Materialize the full positive sector-by-calibration-size cell table.
- Preserve target fact identities, national totals, noise flags, and the
  sector-count non-additivity warning.

## Phase 3: observed donor frame

- Aggregate filings coherently to sponsor EIN without summing overlapping
  plans.
- Preserve full NAICS and plan-entity strata.
- Drop only records that cannot be attached to a declared calibration cell,
  recording each filter and count.
- Assign deterministic identifiers and retain raw employment.

## Phase 4: dual-margin calibration

- Reproduce the firm-only and finer-SUSB-strata attempts as diagnostics.
- Apply the bounded maximum-entropy count-and-employment tilt through the
  public `microcosm.calibrate` API.
- Declare the absolute lower and upper weight bounds in configuration and the
  artifact; the ported `(0.1, 140)` bounds are a claim to re-certify, not a
  global calibrator default.
- Hold only the firm margin for declared employment exclusions or an
  infeasible observed support, and report every residual.

## Phase 5: diagnostics and certification

- Emit every positive target cell, including zero-support cells before a
  fail-closed build stops.
- Report count, both margins, ratios, weight distribution, bound hits,
  leverage, and effective sample size per cell.
- Run the national BDS comparisons only on exactly nesting bands.
- When staged raw sources exist, reproduce and pin empirical reader and frame
  facts. PR CI skips those tests cleanly and never downloads gated data.

Real-data certification and artifact publication are deliberately outside PR
CI. This implementation lane does not publish or promote `populace-us-firms`.

## Phase 6: dynamics seam

- Release a separately versioned `populace-us-firms` artifact after its
  certification gates pass.
- Dynamics consumes firm identifiers, raw employment, weights, and provenance.
- Dynamics owns worker-firm assignment and applies its repo-pinned IC1/IC2
  contracts at the seam.
- Dynamics E-gates remain repo-pinned validation references. They do not become
  Microcosm frame target values and are not copied into this repository.

## Open questions

- Is the publishable observation unit a plan-sponsor EIN, or must sponsors be
  reconciled to SUSB legal enterprises first?
- Should production filter to single-employer plans, split plan/entity strata,
  or retain a set-valued stratum when one EIN reports conflicting types?
- Which main and SF fields are the authoritative common active-participant
  concept, and how should plan-year timing align with SUSB 2022 March 12
  employment?
- Which exact full-NAICS exclusions reconcile crop and animal production, and
  how should government ownership be identified in each source?
- Should metadata always follow the maximum-participant filing, or should some
  conflicts split one sponsor into multiple observations?
- How should one-row-per-sponsor output reconcile SUSB's non-additive industry
  firm counts with the national unique-enterprise margin?
- What executable evidence supports the legacy 987,039-record count, 66.3%
  agreement, 1.024 employment ratio, weight-bound sensitivity, and NAICS 55
  share claims?
