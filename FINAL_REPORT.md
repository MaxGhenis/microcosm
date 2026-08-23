# Final report: US firm frame port

## Outcome

The US observed-sponsor frame implementation is complete locally on
`us-firms-frame-port`, based on `origin/main` at `d69131a3`. The work moves
population-artifact construction into `microcosm-build`, while keeping the
dynamics seam limited to consuming raw firm employment and applying its
canonical IC2 bands and gates.

The port adapts Vahid Ahmadi's work from
[microcosm-dynamics #386](https://github.com/PolicyEngine/microcosm-dynamics/pull/386)
and
[#390](https://github.com/PolicyEngine/microcosm-dynamics/pull/390), and
addresses the concerns recorded in
[#392](https://github.com/PolicyEngine/microcosm-dynamics/issues/392).
Substantive port commits carry
`Co-authored-by: Vahid Ahmadi <vahid@policyengine.org>`.

No restricted source was downloaded or staged, no real-data artifact was
built, and no artifact was published or promoted. The implementation and its
secrets-free tests therefore establish code and artifact contracts, not
empirical certification.

## Ported and where

- `packages/microcosm-build/src/microcosm/build/us_runtime/us_firms/`
  contains strict Form 5500 and OSHA ITA readers, immutable source pins,
  fail-closed staging, the Ledger target adapter, hash-pinned SUSB and BDS
  migration harnesses, the observed-sponsor frame builder, diagnostics, and
  the atomic artifact writer/verifier.
- `packages/microcosm-calibrate/src/microcosm/calibrate/entropy.py` provides
  the public receipt-bearing bounded exponential dual-moment calibration
  required by a standalone firm table. This avoids fabricating person-to-firm
  memberships merely to enter the current person/group `Frame` solver.
- `tools/stage_us_firm_microdata.py` and
  `tools/build_us_firm_frame.py` provide explicit local staging and build
  entry points. Staging admits only exact byte and SHA-256 matches, and the
  build CLI refuses an implicit target authority or an existing output
  directory.
- `docs/us-firm-support-plan.md` records phases, source measurement models,
  the Ledger boundary, the `populace-us-firms` contract, the raw-employment
  dynamics seam, and unresolved certification decisions. A sentence-case
  changelog fragment is included.
- Reader, staging, target, frame, artifact, and CLI tests live in
  `packages/microcosm-build/tests/test_us_firm_*.py`; calibration tests live
  in `packages/microcosm-calibrate/tests/test_entropy.py`.

The Form donor unit is one selected plan-sponsor EIN, not a demonstrated SUSB
enterprise. OSHA establishments remain an independent measurement reference
and are never unioned into the Form-only donor frame.

## Deliberately not ported

The following remain dynamics concerns and were not copied:

- `assignment.py`;
- `ic1.py`;
- `spell_imputation.py`;
- worker-firm linkage and IC1 spell schemas;
- dynamics E-gates; and
- `firms/banding.py`, which remains the canonical IC2 bander.

This lane also did not add a dynamics consumer, worker links, a release,
artifact publication or promotion, reviewer requests, or a merge. No
`populace-*` legacy package was touched.

## Acceptance-gate status

| Gate | Status | Evidence and remaining work |
|---|---|---|
| 1. Observation unit and establishment-to-enterprise reconciliation | **Open** | Form sponsor EINs, OSHA establishments, and SUSB enterprises are documented as different units. They have not been reconciled to a common legal enterprise. |
| 2. Single-employer filtering or explicit plan-entity strata | **Closed in implementation** | No single-employer claim is made. The readers and frame preserve source plan/entity codes, source-specific types, aggregate strata, and conflicts. The production filtering policy remains a certification choice. |
| 3. Preserve plan/entity type, full NAICS, ownership, and OSHA establishment IDs | **Closed in implementation** | Reader contracts preserve full NAICS and Form strata, plus OSHA ownership, record IDs, and establishment IDs. OSHA identifiers remain in the independent-reference evidence rather than the Form-only firm table. |
| 4. Participant timing and per-source measurement models | **Partial** | Main and SF filings consistently use end-of-year active participants, and the artifact records explicit source measurement models. Alignment of plan-year endpoints with SUSB's March 12 measure is unresolved. |
| 5. Committed, hash-bound coverage build with every rule | **Partial** | The implementation binds source, target, configuration, output, and diagnostic hashes and records filters, caps, recodes, deduplication, and the 31-33 / 44-45 / 48-49 crosswalk. Synthetic artifacts exercise the contract, but no real coverage artifact was built and exact crop/animal-production and government-universe reconciliation remains open. |
| 6. Complete cells plus weight, leverage, and ESS diagnostics | **Partial** | The builder emits the complete positive-cell table, rectangular-grid receipt, unmatched donor cells, margin ratios, quantiles, bound hits, leverage, and Kish effective sample size globally and per cell. Only synthetic evidence was produced in this lane. |
| 7. Actual employment margins with held-out validation | **Partial** | SUSB employment margins enter the bounded dual-moment solve, with NAICS 55 excluded before that solve. BDS is held out from calibration and compared over three exactly nesting bands. No real donor build ran, and BDS employment is explicitly non-comparable under the frame's scope exclusion. |

Gates 1, 4, 5, 6, and 7 must not be described as closed until a verified
real-data artifact resolves their remaining empirical and universe questions.

## Reproduced numbers

The following were reproduced from the committed, hash-pinned target extracts
or source manifest:

| Quantity | Reproduced result | Interpretation |
|---|---:|---|
| Positive SUSB sector-by-size cells | 97 | Target geometry only: 97 positive cells in a 100-cell rectangle. The absent cells are NAICS 99 at 50-99, 100-499, and 500+. |
| Published SUSB detail rows | 446 | These aggregate into the 97 calibration cells. |
| Distinct SUSB detail size codes | 23 | The earlier prose count of 22 is not reproduced. |
| Sector-summed SUSB firms | 6,461,497 | Non-additive across sectors; this is not the national unique-enterprise count. |
| National unique SUSB firms | 6,395,635 | Read from the pinned national total row. |
| SUSB employment | 135,748,407 | Full target-extract employment. |
| In-scope SUSB employment | 132,086,430 | Employment after excluding NAICS 55 from the employment margin. |
| Pinned raw download bytes | 244,927,049 | Three immutable downloads, before expanded staging. |

The legacy donor-dependent claims were not repeated as facts:

| Claim to verify | Status |
|---|---|
| 987,039 observed records | **Not reproduced** without staged raw sources. |
| At least ten sponsors in every one of 97 cells | **Not reproduced**; only the 97-cell target geometry was reproduced. |
| 43,001 Form/OSHA overlaps and 66.3% band agreement | **Not reproduced** without staged raw sources. |
| 1.024 calibrated employment ratio | **Not reproduced** without a verified real build. |
| Weight bound 140 | **Configuration reproduced** as bounds `(0.1, 140)`; the empirical knee was not reproduced. |
| 24% NAICS 55 weighted employment share | **Not reproduced** without a verified real build. |
| Failed-attempt ratios 2.058 and 2.517 and prior BDS ratios | **Not reproduced**; the attempts and comparison mechanisms are recorded, not their legacy empirical results. |

Conditional tests compute and pin real-source evidence when exact staged files
exist and skip cleanly in secrets-free PR CI.

## Validation

- Full workspace, run one process per shard: **7,205 passed, 78 skipped, 0
  failed**.
- `microcosm-build`: **6,332 passed, 41 skipped**.
- `microcosm-calibrate`: **210 passed**.
- `microcosm-frame`: **295 passed, 36 skipped**.
- `microcosm-fit`: **93 passed**.
- `microcosm-data`: **275 passed, 1 skipped**.
- The focused US-firm contract suite passed **65 tests with 4 conditional
  real-data skips**.
- Repository-wide `ruff check .` and `git diff --check`: green.
- `microcosm-calibrate` wheel:
  `e50708b10599b1434c90fee6ffafb1e9c667e38c3951ff028f2ffbe5903192a7`;
  ZIP integrity and source identity passed.
- `microcosm-build` wheel:
  `98f6fd312245408d0e0bab24a58352c752c6b93cfe2e4f551097d33b70d2ba65`;
  2,316,925 bytes, 365 valid ZIP entries, all 13 US-firm package entries
  byte-identical to source. A clean temporary installation imported every
  module and loaded all resources, reproducing 97 calibration cells and 446
  detail cells.

The offline worktree could not run a fresh `uv sync`, and the existing
Microcosm venv contained co-installed NumPy and scikit-learn versions newer
than this branch's lock. An initial run correctly failed its version-attested
spec hashes; it was discarded rather than re-pinning valid expectations.

Final tests used a read-only Python 3.14 environment whose NumPy 2.4.6,
scikit-learn 1.8.0, quantile-forest 1.4.2, and PolicyEngine-US 1.764.6 match
`uv.lock`. Workspace package sources came first, followed by that locked
site-packages directory and a fallback dependency directory in inherited
`PYTHONPATH`, so worker subprocesses saw the same environment. Pytest ran one
process per shard as CI does. Repository-wide Ruff ran through
`uv run --active --no-sync`; the exact literal `uv run pytest` remains an
offline-environment limitation, not an unrun behavioral suite.

## Draft pull request

Requested title:

> US firm frame: port observed Form 5500 readers and SUSB-calibrated frame
> builder from microcosm-dynamics #386/#390

PR URL: **Not available.** The connected GitHub branch-creation write returned
`user cancelled MCP tool call`. The sandboxed shell also cannot resolve
`github.com`, so it cannot fall back to `git push`. The remote branch and
draft PR were not created. No reviewers were requested and nothing was merged.

## Open questions for Vahid's review

- Should the publishable population unit remain a sponsor EIN, or must sponsors
  be reconciled to SUSB legal enterprises first?
- Should certification filter to single-employer plans, release explicit
  plan-entity strata, or split sponsors with conflicting source types?
- Which Form participant fields and plan-year endpoints are authoritative for
  alignment to the SUSB March 12 employment measure?
- What exact crop/animal-production and government exclusions define the
  common calibration universe?
- Is maximum-filing selection the right coherent Form metadata rule when
  multiple filings disagree?
- Should repeated OSHA establishment submissions be summed by EIN as the
  current reference model does, or deduplicated under a different documented
  measurement model?
- Do the legacy raw-data figures reproduce under the stricter reader contracts,
  and does the empirical evidence still justify the OSHA cap and weight bound?

## Follow-ups and blockers

- Publish Census SUSB sector-by-enterprise-size facts as a named Chronicle
  package and register the corresponding Ledger `us_firms` target profile.
  Until then, the committed SUSB extract remains a labelled migration harness,
  never production authority.
- Stage and verify the external Form and OSHA pins outside git, then build the
  real hash-bound coverage artifact and resolve gates 1 and 4-7.
- Add the dynamics consumer only after artifact certification; keep IC2 banding
  and E-gates repo-pinned in dynamics.
- Restore GitHub write authorization or network access, push
  `us-firms-frame-port`, and open the requested draft PR without reviewers.
