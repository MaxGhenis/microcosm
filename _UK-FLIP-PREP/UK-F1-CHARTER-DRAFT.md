# UK F1 — make the compiled UK bundle authoritative

**Status:** dispatch draft. Do not dispatch until the certified US F1
executor/broker ABI is pinned, every N01–N12 schema prerequisite in
`AUTHORITY-INVENTORY.md` has landed, and the existing US-specific battery,
calibration, publication-rung, and spine pipeline fields accept the UK bundle.
The seed, geography, clock, gate, and consumer blockers below must be closed by
machine evidence, not merely acknowledged in an audit.

## Why this lane exists

US F1 makes the generic compiled executor, brokers, seed ledger, plan lock, and
two-tier comparator real. UK F1 consumes that certified country-neutral ABI and
makes the UK bundle—not driver constants—construct the authorities for:

1. the national staging build;
2. the rowwise geography dataset, including the production OA-ladder route and
   the retained crosswalk compatibility profile; and
3. the ladder-derived rowwise calibration candidate.

Constants mode remains the generation-0 oracle until F2. This is a
behavior-preserving authority flip, not a UK redesign.

## Dispatch condition

Start only when all of the following are true:

- The owner identifies the certified US F1 commit and evidence digests for the
  immutable projection/patch/diff executor; RNG, file, environment, and clock
  brokers; seed-site coverage scanner; execution ABI; plan lock; comparator;
  and resume predicate.
- A UK-capable, country-neutral schema has closed N01–N12. In particular, it
  represents multiple physical pipelines, executable source-stage nodes,
  source-family sampling, named geography routes/clone policy, target catalogs,
  UK release dimensions, and artifact/checkpoint protocols.
- The UK bundle compiles a nonempty complete producer graph for all three
  pipelines. The current six-resource walking skeleton, absent producer graph,
  and empty compiled-node set are a hard stop.
- Compiled seed ownership covers L01–L32 and C01 with zero unbound physical
  sites. Tests prove active `hmrc_spi_income` owns separate 42/42/42/43 streams,
  WAS owns three independently reset seed-0 chains, and both geography profiles
  resolve to incumbent seed 42 without a hidden bundle default of 0.
- Every UK gate and calibration field required by the binding executable
  contract is compiled and mutation-tested: formula, input/stage,
  population/denominator, slices, reference digest, support/ESS, absolute and
  relative bounds, uncertainty rule, missing-slice policy, severity/failure
  mapping, target scaling and row weights, cap/zero/negative behavior,
  objective/mass constraints, initialization, optimizer/schedule/dtype,
  stopping, infeasibility, priorities, and attainment. In particular, the OA
  ladder gate is no longer absent from the compiled battery.
- The generation-0 UK oracle commit, policyengine-uk environment, licensed
  inputs, public-source bytes, OA ladder/crosswalk, exclusion registers, and
  signing/evidence inputs are content-pinned and available locally.
- The two preflight artifacts remain current: 30 authority groups/12 missing
  field paths and an independent 87-physical-site stochastic/hash/ambient
  baseline. Every source delta since that audit is adjudicated before a run.
- A generated dependency inventory identifies every UK closure, segment, and
  dashboard consumer of constants-era authorities. Each is either retargeted to
  compiler output in this F1 lane or evidenced absent; prose scoping is not a
  substitute for the inventory required by the F1 rollout.
- Prior cold-f001 stage telemetry, with at least 25% memory and 20% wall-time
  contingency, proves the four serialized graphs, tests, and resume exercise fit
  below 15 GiB aggregate RSS and within 24 hours. A stage without safe telemetry
  is a stop-before-launch condition.

If UK-specific schema/compiler work remains at dispatch, this is not yet a
one-day flip lane: stop and land that prerequisite separately.

## Binding intent

`--config-authority constants` must execute the untouched generation-0 path.
`--config-authority bundle` may construct semantic authority only from
`CompiledSpecIR`, compiled nodes, the sealed run request, and explicit broker
capabilities. It may not reconstruct values from constants, a generated legacy
payload, parser defaults, or permissive fallback code.

File, environment, clock, RNG, UUID/nonce, and network access is denied unless
the certified capability/broker policy explicitly authorizes and receipts it.
Certification never permits a live geography download.

Compile-back is exact: the complete authored UK bundle must reproduce the
legacy payload used by constants mode before execution begins. Field-usage
coverage is fail-closed; a parsed or compiled authority field that no executable
consumer reads fails the lane.

The flip preserves exact legacy-v1 stochastic and geography behavior. It does
not repair the model, tune a gate, switch to block-first geography, consolidate
source manifests, or reinterpret a declared seed.

## Scale established by preflight

The lane is sized for these reviewed surfaces:

- **30 semantic authority groups** across the national, geography, rowwise,
  calibration, gate, publication, checkpoint, and artifact paths.
- **12 schema field paths** that must be present before dispatch, plus
  country-neutral generalization of existing US-specific battery, calibration,
  publication-rung, and spine pipeline fields.
- **87 physical UK-file callsites**: 48 stochastic/seeded, 17 deterministic
  hashes, and 22 ambient calls. The reviewed disposition is 33 owned physical
  sites and 54 typed exemptions.
- **32 logical draw-site rows** plus one behavior-affecting clock record. The
  seed families are identity-keyed 0; CGT 552 mixed with period; SPI/HMRC 42
  followed by 43; national sample 578; and rowwise geography/calibration 42.
- Three physical pipelines, two geography profiles, one selected local target
  family, and one restricted cold certification graph.

These numbers are baselines, not magic acceptance constants. The independent
scanner must produce an exact explained delta after upstream F1 merges; an
unexplained addition, deletion, or reclassification fails.

## Ownership

- **Upstream US F1 owner:** supplies and certifies the country-neutral executor,
  brokers, capabilities, seed protocol machinery, coverage scanner, plan lock,
  comparator, artifact collection, and resume semantics. UK does not fork them.
- **UK schema/compiler prerequisite owner:** before dispatch, lands the complete
  resources, UK executable graph/nodes, physical pipeline ABI, N01–N12 fields,
  seed sites, geography profiles, release dimensions, target catalog,
  compile-back projection, and field-usage coverage. The one-day flip lane
  verifies and consumes this work; it does not author missing schema/specs.
- **UK runtime owner:** adds the authority-mode selector to all three drivers
  and binds bundle mode to compiled IR/brokers. Constants mode stays untouched.
- **Certification/data owner:** provides licensed inputs, adjudicates evidence,
  signs reports, and alone may push, publish, promote, or flip `latest`.

## Dispatch card

Unless the owner substitutes and records another fresh location, use branch
`spec-engine-uk-f1` in
`/Users/maxghenis/PolicyEngine/_worktrees/microcosm-uk-f1`, journal in
`_UK-F1-LANE-NOTES.md`, and write certification evidence to
`docs/evidence/spec-engine/uk-f1-certification.json` plus the adjacent `.md`
summary. Nothing in this draft authorizes touching an existing UK branch.

The first environment command is exactly:

```bash
uv sync --all-packages --extra us --extra uk
```

Before dispatch, the owner and lane author must place copy-paste-ready command
vectors for constants A/B, bundle C/D, and fixture kill/resume in the journal.
They must contain resolved absolute input/output paths, exact content digests,
the noncanonical f001 release id, mode, seeds, ladder pin, comparison-plan pin,
broker policy, resume policy, and telemetry wrapper. Placeholder commands do not
satisfy dispatch.

## Sealed inputs and run request

Record one immutable `plan_lock` before execution. It contains all content
digests, upstream ABI/implementation digests, bundle/spec identity, oracle code
pin, exact artifact/comparison vectors, and typed run-request values.

The restricted certification request seals f001 for the national input
deliberately, making live defaults and certification overrides explicit:

| Surface | Sealed values |
| --- | --- |
| National | target period/source year 2023; build seed 42; QRF estimators 100; sample fraction 0.01; sample seed 578; rung `f001`; non-release-candidate posture; exact owner-approved noncanonical f001 `release_id`; compiled source tier; compiled cardinality source and expected resolved count |
| SPI/HMRC | separate ledger sites for age jitter 42, donor bootstrap 42, QRF stage 1 seed 42, QRF stage 2 seed 43; exact donor size and ordered targets |
| CGT | seed base 552 mixed with target period; exact ordered allocation/band surface |
| Rowwise geography | production route `ladder`; two clones; run seed 42; constituency vintage `2024_pcon`; exact ladder content pin; preserved clone/ID/weight semantics |
| Crosswalk fixture | named compatibility route; run seed 42; exact pinned crosswalk bytes; collision policy and 50-retry cap; never live-download during certification |
| Candidate solve | target family `census_households/constituency`; epochs 512; learning rate 0.15; free mass; target records null; L0 0; budget iterations 10; loss cap 10; max weight ratio 100; seed 42; preserve the incumbent hardcoded candidate receipt/build rung tag `f100` pending a separate owner ruling |
| Operational | fresh output/checkpoint roots per cold run; no pending production logbook chain; injected exclusion-evaluation date; no live network after dependency sync; heavy runs serialized; aggregate process-tree watchdog soft-stops at 12 GiB and hard-kills at 14 GiB, with stop-before-launch telemetry headroom as the primary fence |

Filesystem paths and licensed handles are operational bindings. Route, source
identity, seed, vintage, clone count, solver behavior, gate posture, and release
dimensions are semantic and enter the plan/node slices as appropriate.

## Non-goals

- No threshold, seed, target, model, QRF, source ordering, geography, or release
  naming change.
- No derived-v2/block-first geography, target re-unification, new fiscal
  calibration, or firm-generation activation.
- No source-stage consolidation or cleanup hidden inside the authority flip.
- No relabeling of the candidate's incumbent `f100` receipt/build identity to
  match the national f001 certification override.
- No F2 deletion. Constants mode remains runnable and is retained as oracle.
- No full-scale release, `latest` promotion, push, or publication from this
  lane. The owner receives commands and evidence.
- No edits to María’s branches, external `policyengine-uk` sources, or the
  prelanded `packages/microcosm-build/src/microcosm/build/uk/` bundle resources.
  If those need changes, stop and return them to the prerequisite owner.
- No non-UK consumer retargeting. UK closure/segment/dashboard consumers found
  by the generated dependency inventory are binding F1 scope and may not be
  deferred; a zero result must be preserved as machine evidence.
- No reroll, tolerance relaxation, or canonicalization invented after observing
  a mismatch.

## One-day execution sequence

Every numbered step is one coherent commit and updates the lane journal.

### 0. Preflight and freeze

Pin the certified upstream F1 ABI/evidence and the generation-0 oracle. Run
`uv sync --all-packages --extra us --extra uk`, then deny live network for all
certification processes. Run the relevant constants baseline/tests, copy the two UK
preflight reports into the lane evidence, seal the run request, and prove the
tree is clean. Resolve every N01–N12 field and every source delta before moving
on. Freeze the dispatch card's fully expanded commands and verify cold-f001
stage telemetry, the 24-hour budget, and the 12/14/15-GiB process-tree fences.

### 1. Compile and prove coverage

Compile the complete UK bundle and require:

- exact compile-back to the generation-0 payload;
- a nonempty executable node for every national, rowwise, candidate, gate, and
  artifact stage;
- exact ownership of all 30 inventory rows;
- no ignored or fallback-owned authority fields;
- country-neutral validation of the UK battery/calibration/publication
  resources; and
- compiler-emitted physical plans for national, ladder rowwise, crosswalk
  compatibility, and candidate calibration.

For every gate and calibration doctrine field named in the dispatch condition,
run a mutation that changes the compiled plan or fails load. A named Python gate
or solver with code-resident semantics does not close authority.

Do not start runtime changes if this proof is incomplete.

### 2. Close brokers and stochastic coverage

Run an independent filesystem/AST scanner—not one derived from the seed
registry—over all UK production files and reachable shared kernels. Bind every
owned site to the audited ledger/broker contract and every exemption to its
typed profile. Prove:

- all identity-keyed seed-0 vectors and both BRMA salts;
- CGT `(552, period)` consumption;
- independent SPI seed-42 resets and stage-2 seed 43;
- three independently reset WAS seed-0 segments;
- national sampling seed 578 and fraction-1 zero consumption;
- ladder/crosswalk seed-42 sequential order and collision behavior;
- current rowwise L0 zero consumption plus fail-closed future activation;
- one injected exclusion-evaluation date; and
- no direct RNG, environment, file, UUID, clock, HTTP client, or socket access
  outside broker policy. The independent scanner covers network constructors and
  calls as well as stochastic/hash/ambient sites.

The experimental firm exemption must remain unreachable. Inheriting the US F1
QRF state-restore fix and implementation digest is mandatory.

### 3. Flip the national pipeline

Add/use the authority selector in `build_uk_national_dataset.py`. Bundle mode
constructs source bindings, the selected stage graph (including CGT), run
parameters, sampling, frame/H5 ABI, checkpoints, gates/evidence, release
identity, attempts, and artifact ordering from compiled IR/plan projections.
Constants mode is unchanged.

Run cold fixture-scale dual-mode receipts after each logical stage. Each receipt
records input/config projection, seed cursor/sites, output identity, weight/mass
transition, checkpoint identity, gate verdict/detail, and artifacts.

### 4. Flip rowwise and calibration pipelines

Bind the rowwise dataset and candidate drivers to compiled geography profiles,
clone/entity semantics, target catalog/matrix, solve doctrine, gate timing, and
artifact protocols.

The ladder route is the restricted certification route. The crosswalk route
must have a pinned fixture-scale dual-mode proof; if it is not supported for
production, retain it as an explicitly typed compatibility profile rather than
silently dropping it. Never fetch mutable source URLs during equality runs.

### 5. Complete stage receipts and adversarial fixtures

For all 30 authority rows, produce a constants/bundle receipt with equal
normative digest and no unexplained structural difference. Include adversarial
tests for out-of-scope writes, missing source declarations, changed group/row
order, geography vintage mismatch, seed cursor drift, undeclared gate, missing
FitWeightRecord, and changed checkpoint identity.

Land a secrets-free PR-CI gate that executes cold dual-mode fixtures for all
three drivers and both geography profiles and requires an empty normative diff.
It must use permitted fixture bytes, begin from empty output/cache roots, and
fail on an unlisted operational difference. A one-off lane test is insufficient.

### 6. Run cold certification and resume proof

Run four fresh restricted certification graphs, each using a newly built f001
national input and no artifact, checkpoint, model, or bank reuse:

- constants A;
- constants B;
- bundle C; and
- bundle D.

Each graph fans out from one national staging H5 to two independent consumers:
the rowwise OA-ladder dataset driver and the rowwise calibrated-candidate
driver. Both receive that same frozen national H5 and the same ladder pin; the
candidate never consumes the rowwise dataset output. Its incumbent `f100`
receipt/build tag is preserved and compared exactly even though its national
input is the sealed f001 override. Require `A = B`, `C = D`, and `A = C` under
the sealed comparator. Require zero resumed stages in all four cold graphs. Run
heavy stages serially, record wall time and aggregate lane peak RSS per
stage/mode, and abort before aggregate lane RSS reaches 15 GiB.

The cold predicate is concrete: `--resume-policy=forbid` refuses any pre-existing
manifest/checkpoint before loading; every durable stage and model/target bank
reports `initialized` rather than `resumed`/`checkpoint`; and one typed
`resume_audit` records per-stage and per-bank attempted/resumed counts, all
required zero. The UK field names may differ from the US pool, but the predicate
may not be weakened to one aggregate boolean.

Separately exercise kill/resume at fixture scale after a durable stage boundary,
resume only under the compiler-emitted predicate, and require its final
normative vector to equal an uninterrupted fixture build. This is not a fifth
certification graph, and resume evidence does not substitute for the four cold
runs.

### 7. Close and hand off

Retarget every UK closure/segment/dashboard consumer found by the generated
dependency inventory to compiler outputs and prove zero constants-era reads; if
the inventory is empty, retain the zero-result evidence. Write machine-readable
and human UK F1 certification evidence at the dispatch-card paths, record
constants/F2 retention, and hand the owner exact f010/f100/full commands and
expected identities. Do not push or publish.

## Required tests and evidence

- Baseline/relevant full test suite in constants and bundle modes; schema,
  loader, round-trip, compile-back, mutation, field-usage, and plan-lock tests.
- Parser/path tests proving constants mode does not load the bundle and bundle
  mode cannot construct semantic constants outside IR.
- Complete producer-graph and node-slice tests for all three drivers and both
  geography profiles; an empty UK node set fails.
- A durable secrets-free per-PR cold dual-mode fixture gate for all three drivers
  and both geography profiles.
- Independent AST coverage with zero unbound/stale rows, plus runtime broker
  enforcement (including network denial) and golden legacy vectors for each seed
  family/reset boundary.
- Full gate/calibration field-usage and mutation coverage for the executable
  semantics enumerated in the dispatch condition.
- Per-logical-stage synthetic dual-mode receipts and every declared UK gate run
  with identical threshold, direction, status, and detail.
- Four cold certification graphs with f001 national inputs and incumbent
  `f100` candidate receipt tags, plus one separate fixture-scale kill/resume
  proof, with commands, environment/code/spec pins, artifact identities,
  comparisons, gate table, broker logs, checkpoint evidence, wall time, and
  RSS.
- A leak/waiver register. No silent exemption or post-hoc comparison rule is
  acceptable.

## Equality contract

Use the certified F1 two-tier comparator and compiler-emitted sealed comparison
vector.

1. **Normative artifacts:** exact bytes for every artifact the physical ABI
   declares normative, including entity tables/column order/dtypes, typed weight
   vectors and mass log, checkpoints, target/matrix surfaces, calibration
   weights, stochastic outputs, gate verdicts/details, compiled seed map, and
   the plan-derived publication/artifact vector. An H5 structural comparison is
   also emitted for diagnosis; it never excuses a normative byte mismatch.
2. **Provenance/operational surfaces:** compare structurally under explicit
   sealed rows only. `identity_generation` and the provenance triad are expected
   generation differences and must equal loader outputs; `config_authority`
   must equal the selected mode. Absolute paths, durations, UUID nonces,
   operational timestamps, host/executable strings, and similar readouts may be
   excluded only when predeclared. The sealed semantic
   `exclusions_evaluated_on` date must compare equal and is never an operational
   exclusion. Any unlisted difference fails. Node reuse keys remain equal
   across modes.

Unlike the US D6 migration, this draft authorizes no UK release-prefix change:
the inventoried `populace-uk-<year>-<tier>-k<count>` identity is normative. A
future `microcosm-uk` transition requires a separate owner ruling and sealed
normalization row; it must not appear opportunistically in UK F1.

## Acceptance

- All N01–N12 prerequisites resolved and the complete UK producer graph compiles
  with zero ignored authority fields.
- Every one of the 30 authority rows is constructed from compiled IR in bundle
  mode; constants mode remains untouched.
- Independent stochastic coverage is complete; all declared/runtime seeds and
  reset boundaries reconcile; the semantic clock is injected; direct network is
  denied; exact release tier/cardinality/id precedence is sealed and tested.
- Fixture and stage receipts show no normative differences.
- The secrets-free PR-CI dual-mode gate and the generated UK consumer-retarget
  inventory are green.
- Cold-graph `A=B`, `C=D`, and `A=C` with f001 national inputs and preserved
  `f100` candidate receipt tags; resume proof passes; all gates match; no hidden
  reuse; heavy runs are serialized and aggregate lane RSS stays below 15 GiB.
- Nothing is tuned, pushed, published, promoted, or run above the restricted
  certification scale.
- Journal, machine evidence, human summary, and owner handoff are complete.

## Stop conditions

Stop immediately and leave the last coherent commit/test state if:

- US F1 is uncertified, its ABI/evidence pin is missing, or an upstream drift is
  unexplained;
- any N01–N12 path is unresolved, compile-back differs, executable UK nodes are
  absent, or field usage reports an ignored/fallback authority;
- any physical stochastic/hash/ambient delta lacks a reviewed ledger binding or
  typed exemption;
- active `hmrc_spi_income` still obtains 42/43 from CLI/code rather than the
  compiled selected node, WAS reset boundaries are not explicit, or geography
  seed 0 versus 42 is unresolved;
- the exclusion-evaluation date remains ambient;
- within-mode nondeterminism, cross-mode normative mismatch, gate difference,
  unlisted receipt difference, hidden reuse, or resume-predicate failure occurs;
- required licensed/pinned inputs, signing/evidence, or authenticated geography
  bytes are unavailable;
- aggregate lane RSS approaches 15 GiB, heavy runs would overlap, or success
  would require a reroll/tune; prior telemetry lacks the required headroom; the
  12-GiB soft or 14-GiB hard watchdog fires; or the 24-hour budget is no longer
  credible; or
- work would require touching María’s branches, external `policyengine-uk`, or
  the prelanded UK bundle resources.

## Owner handoff

Provide the commit chain, upstream executor/broker ABI and evidence digests,
oracle pin, spec SHA and compile-back proof, sealed run request and `plan_lock`,
independent callsite coverage, complete draw ledger/exemptions, exact commands
and environment, per-stage receipts, artifact/comparison/gate results,
checkpoint/resume evidence, peak RSS/wall time, leaks/waivers, and the
constants/F2 retention plan. Include owner-only f010/f100/full commands and
expected identities. The lane itself neither pushes nor publishes.
