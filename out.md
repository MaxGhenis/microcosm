ADJUDICATION-BLOCKED

# Dense-reds adjudication verdict

Date: 2026-08-30

Branch: stacked-dense-gate-sweep

## Verdict

The source-level adjudication is complete, and every adjudicated repairable red
except weeks_worked now has a root fix, focused contracts, and independent
review. A read-only in-memory replay over the existing candidate evidence,
after applying the landed producer repairs, also passes the unchanged
post-producer health gate.

Dense certification remains blocked for two separate reasons:

1. The stacked weeks_worked ownership choice is an unresolved Max ruling.
   Actual release execution stops at gate 9480 before ORG; no ownership choice
   was implemented and the gate was not weakened.
2. Candidate-25 predates these repairs and remains the immutable historical
   gate_failed artifact. Max's no-build hold remains in force, so no rebuilt
   pool or dense release exists to certify the repaired code.

No pool, dense, release, or other data build was run. No candidate byte,
publication surface, remote, PR, or branch outside this local lane was changed.

## Immutable evidence boundary

Evidence was read only from
/Users/maxghenis/PolicyEngine/_buildo-runtime/out/candidate-25/.

- pool H5: 3,239,263,159 bytes; SHA-256
  eeea886afec72c4ec6e15d31358920416ea6892ef2dca6bb9a281dc1faf6231b
- pool manifest SHA-256:
  c9ee554939790d854efea9d69897a40376d0c7ea49e40e3f76f268835ebd148a
- historical terminal state: gate_failed; the prior report records the label
  “78/135 battery” without interpreting that numerator

Current source correctly refuses to load this stale candidate as a current
artifact because its source-attested worker identity predates the lane.
Therefore the adjudication was analysis over hash-verified fixed HDF tables,
with only authenticated assembly, stack, and clone receipts restored in
memory. It was not an official loader replay, migration, or build, and it
wrote no evidence artifact.

The reconstructed authenticated support contains 1,970,973 people, 865,460
households, 1,179,864 tax units, 868,956 SPM units, 875,642 families, and
1,572,357 marital units.

## Per-red adjudication

| Defect class / red | Root cause | Fix commit or blocker |
|---|---|---|
| Ownership: farm rent plus six PUF-only tax-detail siblings | Generic late transfer treated all clone-0 native rows as recipients for leaves owned only by PUF support. | Fixed at the ownership root in 0347a009; strict gate regressions in e8d51ab8. |
| Release metadata: prior-year availability | Two release repairs reconstructed Frame without sampling metadata, lost the 0.25 rung, and applied the wrong floor. | Fixed in 961b9c67; no band changed. |
| Provenance: ACS predictor join and archived models | The H5 loader omitted the authenticated assembly receipt, so the release join failed before the six model corridors. | Fixed in 4fd5af67; five-model replay evidence in eb4595b7. |
| Semantic ownership: weeks_worked, hours gate, and ORG | The pool deliberately excludes formula-owned weeks_worked, while the pool-backed release path skips reconstruction. Actual execution stops at gate 9480. | BLOCKER: Max ruling recorded in b62d0b1e and pinned, but not authorized, in 2f7419b2. |
| Housing coherence: 31,133 assistance mismatches | Independent late transfer broke equality between final assistance take-up and measured receipt. | Implemented in WIP 8129c9b7 and independently accepted in 2700ad7f. |
| Housing coherence: positive rent on 260 ACS nonheads | Independent late rent transfer violated the head-carriage contract. | Implemented in 8129c9b7; accepted in 2700ad7f. |
| Source absence / engine boundary: 91,032 nonfinite GQ rents | All are valid ACS TYPEHUGQ 2/3 structural nulls; the combined-origin gate and PolicyEngine copy boundary mishandled them. | Exact source-domain and copy repair in 8129c9b7; null authority tightened in 9ec67cd5; final-write path fixed in 29072fd5. |
| Source domain: housing tenure red | The combined-origin gate applied the three-category ASEC domain to ACS, where OWNED_OUTRIGHT is valid. | Exact per-origin domain repair in 8129c9b7; accepted in 2700ad7f. |
| Engine boundary: 91,032 household and 91,032 SPM tenure nulls | GQ tenure is structurally absent, but PolicyEngine rejects source NaN. | Authority-bound engine-copy defaults in 8129c9b7; sparse/full-tail validation in f82d7bc8; final-write integration in 29072fd5. |
| Dependency order: five AOTC facts | Final tuition transfer ran after deterministic AOTC derivation. Four mismatch counts were 17,290; the 1098-T/exception count was 17,291. | Dependency-bound reconciliation in 8129c9b7; typed policy closure in 0363f739; accepted in 2700ad7f. |
| Dependency order: two WIC reds | Final pregnancy transfer ran after the WIC source draw, causing a 0.004767 weighted none-claim share and 32,078 clone mismatches. | Stable-source redraw and dependency binding in 8129c9b7; typed closure in 0363f739; accepted in 2700ad7f. |
| Raw-source content: fourteen coverage-vintage reds | Seven measured ASEC recodes were absent in each of the 2022 and 2023 cohorts. | Exact pinned source_year plus PERIDNUM sidecar repair in 5d3419d2; no imputation. |
| Engine boundary: SSI simulation-copy failure | Dual ASEC/ACS reporter representations left 495,738 null cells on the ssi_reported input surface; ASEC has measured SSI_VAL, while ACS absence is valid only below age 15. | Bounded measured-anchor coalesce and child-zero copy adapter in 8129c9b7; final writer routed through it in 29072fd5. |
| Producer root: 350,656 real_estate_taxes nulls | The declared joint rent/property-tax producer fit and wrote rent only; ACS structural zeros also lacked an exact source-domain mapper. | Joint ASEC QRF plus ACS TAXAMT repair in 8129c9b7; mapper hardened in 13dc0b34; accepted in 2700ad7f. |
| Native-zero source: three second-home inputs | Each had 582,318 native null tax units despite no native source and an engine default of zero; all authenticated clone payloads are exactly zero. | Ten-leaf expansion in 8129c9b7; reviewed exclusions restored in f2765b54. The unsound intermediate 182a2f45 is superseded. |
| Stage classification: raw-pool health red | The raw pool was observed before the real ACA producer, which replaces both health outputs. | No gate change. The actual read-only post-producer replay passes; evidence committed in 17f1c72e. |
| Artifact state: candidate-25 overall | The artifact predates every continuation repair and remains gate_failed. | Requires a newly authorized current-source build; nothing was “fixed in place.” |

The original seven native-zero leaves are farm_rent_income,
domestic_production_ald, educator_expense,
investment_income_elected_form_4952, salt_refund_income,
long_term_capital_gains_on_collectibles, and
unrecaptured_section_1250_gain. The three added leaves are
second_home_mortgage_balance, second_home_mortgage_interest, and
second_home_mortgage_origination_year.

Commit 8129c9b7 was deliberately preserved with a WIP subject after the prior
process died. Its behavioral pieces are cited only together with independent
acceptance 2700ad7f and the relevant hardeners above. Cross-cutting integrity
commits are 3d972d2f for target-checkpoint invalidation, e524fdac and 6d30b93b
for clone-attachment validation, and d537d066 for source-attestation recuts.
They are not misattributed as the assembly-receipt root fix.

No threshold or signal band was weakened. Housing gate logic was corrected to
use exact per-origin domains and authenticated GQ absences; that is a source
contract repair, not a bypass.

## Actual post-producer health replay

The read-only replay applied the repaired ten-leaf native projection, joint
property-tax producer, pinned ACS predictor join, SCF wealth producer, and the
real ACA source producer entirely in memory.

- real_estate_taxes finished with zero nulls, 453,778 positive person rows,
  and 60,425 unique values
- the ACS predictor join matched all 1,736,840 support rows with zero
  unmatched rows or collisions; semantic SHA-256
  c7723adc889fc655b46103426d21f6c74937434eff51e8f3e6025bdf60972b74
- the ACA closure resolved 483 PolicyEngine input leaves with zero nullable
  semantic inputs outside the bounded SSI/rent/tenure adapters; the empty
  omitted-leaf SHA-256 is
  4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
- the production-equivalent registry contained 32,843 targets, one reviewed
  Medicaid substitution, and three 51-state ACA tables
- the real ACA producer completed 35 bounded batches over 865,460 households
  in 1,608.14 seconds
- the unchanged health_input_signal gate passed with zero failures across all
  1,179,864 tax units: 45,520 take-up true and 1,134,344 false; the benchmark
  ratio has 35,059 distinct values, all within [0.5, 1.5]
- the canonical gate payload SHA-256 is
  fa4df7fa5d392bfcb4e5d43d914ab7d8c1e052f41ba20094fd8b2e996a2f2361

## Archived-model status

The faithful replay restored the authenticated assembly receipt while
preserving the candidate's original transferred hours. Five of six corridors
are green after the receipt fix:

| Archived corridor | Read-only status |
|---|---|
| SCF wealth | Green: bank/stock/bond nonzero shares 0.387899 / 0.112850 / 0.011718. |
| SSI disability | Green: true share 0.073720; zero anchor mismatches. |
| SCF auto loans | Green: interest share 0.271253. |
| SIPP vehicles | Green: owned/value shares 0.835794 / 0.838655. |
| SIPP tips | Green: tip/tipped-occupation shares 0.003864 / 0.078835. |
| ORG wages/FLSA | BLOCKED before ORG: weeks_worked is missing at gate 9480. |

The experiment that invoked the CPS-only hours writer is not an actual-stage
ORG verdict: it invalidly zeroed ACS hours. It remains a labeled
counterfactual and is not used to claim either an ORG pass or failure.

## Open Max rulings

One semantic ruling remains open. The evidence-favored, unauthorized option is
a 2024 release-only, origin-aware measured weeks_worked leaf before gate 9480:

- ASEC lineages use clipped WKSWORK;
- ACS lineages use pinned WKWN, with official blank/NIU mapped to zero;
- both fan out by authenticated source identity; and
- the pool retains its cross-period formula-owned exclusion.

Alternatives are an ASEC-to-ACS statistical transfer or a change to ORG/FLSA
denominator semantics. Commit 2f7419b2 records the evidence-favored option but
authorizes none of them. Gate 9480 must remain unchanged.

Max must separately lift the no-build hold before any artifact work. That is
operational authorization, not a second semantic model ruling. The other five
archived-model ownership questions are resolved by the authenticated ACS join
and replay.

## What a post-hold dense rebuild requires

1. Obtain Max's explicit weeks_worked ownership ruling.
2. Implement only that ruling, add focused contracts, preserve gate 9480, and
   recut every affected typed and source-attested identity.
3. Re-run source, static, and full-suite verification.
4. Obtain explicit authorization lifting the no-build hold.
5. Start a new current-source candidate namespace at the raw-source stage. Do
   not resume candidate-25: current contracts include ASEC raw schema 4,
   stacked authority v12, pool checkpoint materializer v8, and target-frame
   materializer v12, while the late DAG, native-zero roots, and property-tax
   producer have changed.
6. Rebuild the complete stacked pool through all current producers and late
   reconciliations. Require an authenticated simulation_ready terminal pool;
   do not use a gate_failed waiver.
7. Build the dense release from that exact pool and run the current fail-closed
   terminal gates, actual post-producer health gate, all six archived-model
   gates, release certification, and publication preflight.
8. Consider certification or publication only if every receipt and gate is
   green and separate publication authority is granted.

## Repository verification

All five package shards are green. The non-build shards were run fresh before
the final fixture-only build-test commits; no source or non-build test changed
afterward. The complete build shard was then rerun from committed checkpoint
9c25d56f.

| Shard | Result |
|---|---:|
| microcosm-calibrate | 203 passed |
| microcosm-data | 322 passed, 2 skipped |
| microcosm-fit | 93 passed |
| microcosm-frame | 295 passed, 36 skipped |
| microcosm-build | 6,647 passed, 45 skipped |
| Total | 7,560 passed, 83 skipped |

Final static checks:

- repository-wide Ruff: green
- CI inventory: 314 tracked test files; verification=ok
- spec coverage: 41,523/41,523 configuration fields and 41/41 inventory checks
- US bundle check: green at spec SHA-256
  7f4537db123094c556d09bd3a1130940cbdfe351359690b75f88e0afa25101c9
- git diff hygiene: green

The separate untracked weeks-ruling note was never edited or staged and is not
part of this adjudication lane.
