# Issue triage lane — 2026-09-12 → 2026-09-14 (read-only research lane)

Lane report goes to `~/PolicyEngine/_recovered/scratch-backup/893/triage/out-issue-triage.md`
(the subfleet `-o` path) and `issue-dispositions.json` beside it. Nothing here writes
to GitHub, edits repo-content tracked files, or touches the stash. Branch
`issue-triage-20260912` is local-only (not pushed; pushing would be a GitHub write).
This journal is the lane's own file and is the only tracked file this lane writes.

## State (run 4 — 2026-09-14, live; runs 1–3 historical)

- Base: `origin/main` @ `18271b28d` (merge of #904). Runs 1–2 (2026-09-12) reasoned
  against `0c3f4f651`; **#912 merged 2026-09-12 and #904 merged 2026-09-14**, so every
  run-1 "absent from main" claim is re-derived in run 3.
- **Open issues are 234, not the 230 in the brief** (range #27–#925). New since run 1:
  #915, #920, #922, #925 (and the set is re-pulled at the end to catch mid-lane closures).
- Open PRs: 50 (was 43). PR #893 moved: 404 changed files on 9/11 → **691 files / 250
  commits** on 9/14, so its fold-in set is recomputed from the new head `47a12030f`.
- A sibling PR-triage lane (run 3) is live in this same worktree; it commits via plumbing
  to `refs/heads/triage/journal-20260912`. This lane touches only its own journal path.

## Run 4 (2026-09-14 evening, Opus 5 lane) — live

- Runs 1–3 all died on Fable limits. Run 4 is dispatched as a BUILD-class Opus 5 lane
  (Bash + Write present) and **reuses run 3's corpus, dossiers, indexes and scripts**
  rather than re-deriving them. Scratch copied to this session's scratchpad at
  `scratchpad/triage/` (run 3's dir is left intact).
- Re-verified freshness: `git fetch origin` rc=0, `origin/main` is still
  **`18271b28d`** (merge of #904) — unchanged since run 3, so run 3's ancestor tests
  and absence checks still hold. Re-pulled the open-issue list: **234 issues, byte-identical
  membership** to run 3's pull (0 closed mid-lane, 0 opened).
- **Salvaged run 3's fan-out**: workflow `wf_23f45e52-c68` recorded 38 results and
  89 failures before the limit. Parsed its `journal.jsonl` → **226 of 234 issues have a
  first-pass row**; 8 (#341 #346 #347 #360 #361 #370 #372 #393) have none, and the
  refuter/adjudicator stage never ran. Those 226 rows are treated as **candidates, not
  verdicts** — run 4 re-triages every issue independently and must confirm or overturn
  each with its own evidence.
- Run 4's own fan-out (workflow, Opus 5 subagents): 35 per-batch re-triage agents over all
  234 issues ‖ 11 per-area cluster agents (duplicates/epics) → adversarial verification
  (2 lenses per close-class row: "does the cited artifact deliver the whole ask" and
  "is the citation real / is the survivor valid") ‖ a missed-resolution sweep over every
  KEEP row → per-row adjudication → coherence critics.

## Done (runs 1–2, 2026-09-12 — historical)

- Confirmed the `-o` path from the subfleet run meta; produced a full written plan
  (`out-issue-triage-r1-notools.md`) but **no output**: run 1 had no Write tool, runs 1–2
  both died on Fable limits. Salvage refs hold only the sibling PR lane's journal.

## Done (run 3, 2026-09-14)

- `git fetch origin`; reasoning re-based on `origin/main` @ `18271b28d`.
- Pulled: `open_issues.json` (234, with bodies+labels+comments+assignees),
  `merged_prs.json` (449, merged ≥ 2026-05-01, incl. `closingIssuesReferences`),
  `open_prs.json` (50), `closed_issues.json` (164),
  `timelines.json` (**234/234** issues; cross-reference / connected / disconnected /
  referenced-commit / marked-as-duplicate events via paged GraphQL, 16 batches, rc=0),
  `main_log.txt` (1,732 commits on main; 22,734 lines with bodies),
  PR #893 body + **691 files** + **250 commits** (paginated past the 100 cap).
- Built indexes: merged-PR→issue mention map, closing-reference map, open-PR map,
  git-commit→issue map, issue↔issue reference graph (both directions),
  repo `#nnn` citation map (1,611 hits over `docs/ experiments/ changelog.d/ tools/`
  + root journals), filename-keyed doc/experiment/changelog hits, and the #893
  body/commit/file fold-in map.
- Built **234 dossiers** (`scratchpad/triage/dossiers/<n>.md`) — one per open issue,
  nothing sampled — plus `dossier_index.json`.
- Area map (two-pass country-then-topic; labels are useless here: 211/234 issues carry
  no label and there are zero milestones): us-calibration 90, release-publishing 54,
  uk-spine 38, us-spine 21, axiom-intl 12, calibration 6, engine-bumps 4, build-runtime 4,
  graph-spec 3, chronicle-logbook 1, docs-ci-infra 1. Agents assign the final area.
- Signals: **94 issues idle ≥ 60 days**; **79 have zero number-linked evidence** anywhere
  (no merged-PR mention, no main commit, no #893 tie, no repo citation, no open PR).

## Done (run 3, continued) — judgment fan-out + owner cross-checks

- Wrote `BRIEF.md` (the agents' rulebook: dispositions, precedence, verification commands,
  and the repo traps) and 35 batches over 11 areas.
- Launched workflow `wf_23f45e52-c68`: 11 per-area cluster agents (duplicates/epics)
  ‖ 35 per-batch triage agents → 2 lens-specific adversarial refuters per close-class row
  (lens 1 "does the cited artifact actually deliver it", lens 2 "what residual remains")
  → 1 reconciliation critic.
- **Two parser bugs found and fixed** (both would have corrupted the epic/duplicate layer):
  1. Cross-repo refs — `PolicyEngine/ledger#70`, `rulespec-nz#74`, `policyengine.py#475`,
     `policyengine-uk-data#466` were being read as local issues: **50 false edges out of
     376 (13%)**. But `populace#302` / `microcosm#451` / `PolicyEngine/populace#…` ARE
     local (repo renamed 2026-08-07), and `#552/#364/#467` is three local refs, not one
     qualified ref. Classifier lives in `scratchpad/triage/refs.py`.
  2. Epic membership ≠ mention: a `Related, non-blocking:` line is not a checklist item.
     Only `- [ ]` / `- [x]` lines now count for `MERGE-INTO-EPIC`.
- Owner cross-checks, all independent of the agents and all matching them so far:
  **#746** RESOLVED (PR #756 merged 2026-08-24, commit `05d254aa2` ancestor of main; all
  four sub-asks landed — `_GENERATED_SOURCE_VERSION = "1.819.0"`, take-up totality incl.
  `takes_up_wic_if_eligible`, WIC migration, `engine_abi.lock.json` at 1.819.0).
  **#324** RESOLVED (Max's own 2026-07-07 comment records the pin validated at 1.764.6).
  **#506** delivered (PR #674, merge commit `7c42c5010` ancestor; `validate_evidence_release_dir`
  + tests on main). **#640** delivered (PR #849 merged 2026-09-07 created `logbook_env.py`
  dual-read) — residual: the legacy `POPULACE_LEDGER_*` names are still honoured, so the
  issue's "then drop" step is open. **#890** is NOT resolved: PR #904 landed only the
  target-binding half; the spine half is open draft PR #927.
- Built the cross-cutting evidence the per-batch agents cannot see: the corrected issue
  graph (356 edges), literal epic checklists, a TF-IDF near-duplicate list (37 pairs
  over cosine 0.28), the open-PR→issue map (**32 issues have an open PR**), and
  **29 issues whose stated blocker has since landed** (actionable now).
- Verified command log: `scratchpad/triage/commands_verified.log`, 19 commands, **all rc=0**.
- Wrote `assemble.py` (journal → rows + verdict application), `build_extra.py`, `render.py`
  (report + JSON + structural checks: row/issue bijection, evidence non-empty, no duplicate
  chains, no self-survivors, no journal-file evidence on a close).

## Done (run 3, continued) — owner-only cross-cutting findings

- **`FOLDED-INTO-893` is almost empty, and proving that needed an ancestor test the
  per-batch agents cannot run.** Of #893's 250 commits, **10 are already on `origin/main`**
  (it merged main) and 240 are unique to it. Classifying every `#nnn` citation by that
  split leaves exactly **one** open issue — **#908** — cited by commits unique to #893.
  The 12 apparent #890 citations all sit in the 10 inherited commits, i.e. they are #904's
  work on main, not #893's. `owner_validate.py` now enforces this against every agent row.
- **`MERGE-INTO-EPIC` is similarly narrow.** Only literal `- [ ]` / `- [x]` checklist lines
  count as an epic listing a sub-item; a "Related, non-blocking:" line does not.
  `owner_validate.py` re-greps each claimed parent body and downgrades claims that fail.
- Independent owner spot-checks (8 so far), every one agreeing with the agent verdict:
  #746, #324, #506, #640, #31 (PR #420 — note its body never cites #31, which is exactly why
  it never auto-closed and why the mechanical index called #31 "zero evidence"), plus
  merge/ancestor confirmation for PRs #369, #354, #288, #399, #37. #890 correctly stays open
  (PR #904 landed only the target-binding half; the spine half is draft PR #927).
- Mid-lane closure check wired (`recheck.sh`); first run shows no change (234 → 234).

## Next

- Wait out the fan-out; `assemble.py` → `owner_validate.py` → close-comment pass →
  `build_extra.py` → `render.py`.
- Re-pull the open list for mid-lane closures; spot-check the final RESOLVED-CLOSE set.
- Write `out-issue-triage.md` + `issue-dispositions.json`.

## Run 5 (2026-09-14, evening — Opus 5 BUILD lane) — the completing run

Runs 1–3 died on Fable limits; run 4 pulled a full corpus and owner spot checks but its
own judgment fan-out never wrote a result (`scratchpad/triage/results/` empty). Run 5
runs on Opus 5, salvages runs 3–4 wholesale, and finishes the lane.

### Baseline re-verified from scratch (measured, not assumed)

- `git fetch origin` rc=0 → `origin/main` is **still `18271b28d`** (merge of #904).
  Unchanged since run 3, so every run-3/4 ancestor test and absence check still holds.
- `gh issue list --state open --limit 500` rc=0 → **234 open issues**, range #27–#925,
  **byte-identical membership** to run 4's pull: 0 closed mid-lane, 0 opened.
- Salvaged run 4's scratch (`4370d93b…`) wholesale into this session's scratchpad:
  234 dossiers, 35 batch context packs, the full raw corpus (open/closed issues, 449
  merged PRs, 50 open PRs, 234 timelines, 1,732-commit main log, #893's 691 files /
  250 commits), every index, and every script. Run 3's `ruling_candidates.json` +
  `unblocked.json` pulled in alongside.
- **226 run-3 candidate rows** recovered (`prior_rows.json`). 8 issues have no prior row:
  #341 #346 #347 #360 #361 #370 #372 #393 (exactly batch `us-calibration-6`); #370 now
  has a run-4 owner-verified row. Candidate distribution: 173 KEEP, 26 RESOLVED-CLOSE,
  13 STALE-ASK, 7 RULED-DEFERRED, 6 MERGE-INTO-EPIC, 1 DUPLICATE-CLOSE. These are
  **hypotheses**; run 5 re-derives every one.

### Next

- BRIEF5 rulebook → 35-batch judgment fan-out on Opus → adversarial verification of
  every close-class row → missed-resolution sweep over KEEP → adjudication → render.

### Run-5 owner cross-checks, batch 1 (independent of the agents)

Full text at `scratchpad/triage/r5/owner_notes_run5.md`. Headlines:

- **#893 fold-in re-derived from scratch**: 10 of 250 commits are ancestors of main,
  240 unique; the only OPEN issue cited by a unique commit is **#908**. #890's 10
  citations sit entirely in the inherited commits (= #904's merged work).
  `FOLDED-INTO-893` is available only for #908. *Trap:* `pr893_commits_full.jsonl`
  stores only a headline `msg`; scanning it alone returns ZERO citations. Full bodies
  must come from `git log -1 --format=%B`.
- **0 of 449 merged PRs carry a `closingIssuesReferences` naming a still-open issue** —
  nothing is a missed auto-close; every RESOLVED-CLOSE is argued from artifacts.
- **13 open issues have a same-numbered `changelog.d/` fragment on main** (run 4 said 12;
  #890's fragments are name-suffixed, not prefixed, so a prefix match misses them).
- **Epic layer: 7 epics, 35 literal `- [ ]` (epic,child) pairs**, and the layer has
  chains (#796 and #882 are children of #736; #736 is a child of #665).
- **4 of the 6 MERGE-INTO-EPIC candidates fail the literal-listing test** (verified by
  reading each epic body): #661→#736 and #731→#796 are real checklist items; #395→#578,
  #403→#578, #416→#530, #719→#922 are prose-only "Related:" lines, which the rulebook
  excludes.
- **#224→#213 is a real duplicate**, with a residual that must ride in the close comment:
  CD-target diagnostics and the explicit release-manifest entry are unique to #224.

### Fan-out launched (run 5)

Workflow `wf_66de6532-038`: 35 batch triage agents → lens-specific adversarial refuters
on every close-class row (RESOLVED-CLOSE: whole-ask / citation-real; DUPLICATE-CLOSE:
survivor-valid / unique-residual; MERGE-INTO-EPIC: literal-listing / detail-loss;
RULED-DEFERRED: ruling-real / premise-changed; FOLDED-INTO-893: 893-delivers) ‖ a
STALE-ASK reality check ‖ a per-batch missed-resolution sweep over every KEEP row →
a per-batch adjudicator that re-runs the deciding command itself.

### Citation validator rebuilt (`r5/owner_validate5.py`) — three real bugs fixed

Run 4's `owner_validate4.py` reported 24 findings over the 226 candidate rows. Rebuilt and
corrected, it reports **13**, all genuine. The three bugs, each of which manufactured
false alarms that would have sent agents chasing nothing:

1. **Decimal GitHub comment ids read as commit shas.** `\b([0-9a-f]{9,40})\b` matches
   `4885524525`, so every `#299#issuecomment-4885524525` URL surfaced as
   `CITED-SHA-UNKNOWN`. Now a hex run must contain at least one `a-f`, and
   `issuecomment-\d+` anchors are stripped before scanning.
2. **A 64-char sha256 sliced into two fake shas.** The crosswalk digest
   `c7cb040b1f57ca2e…c4b640cd421e766f…` (64 chars, a file-content sha256, not a commit)
   was reported as the two unknown "shas" `c7cb040b1f57` and `c4b640cd421e` on #314
   and #449. A maximal-run lookaround now rejects any fragment of a longer hex run.
3. **Escaping/arity slips found by running it**: the regex literal had been written with
   `\\w` (a literal backslash class) rather than `\w`, and after the regex was reduced to
   one group `findall` returned strings, so the consumer iterated *characters* — 330
   single-character "shas". Both fixed.

Remaining 13 findings, triaged by the owner: #324 cites `engine_abi.lock` where main has
`engine_abi.lock.json` (typo; artifact present — row text to be corrected); #640 and #697
cite a path's **absence** as the evidence, which is the point, not a defect; #76 `#8352`
and #299/#333 `#893` are cross-repo or incidental mentions the disposition does not rest
on; **#416 (epic #530 has no list line) and #719 (cites OPEN PR #745 and five
non-ancestor commits) are real defects** and match the owner's own epic check.

### Cross-cutting cluster pass launched (a gap the batch fan-out cannot cover)

The 37 TF-IDF near-duplicate pairs mostly **span batches** (#74 is in `us-calibration-1`,
#168 in `us-calibration-2`), so no batch agent can read both sides of a candidate
duplicate. Built the pairs into **15 connected components** and added the **7 epic
families**, and launched workflow `wf_6783fa4b-567`: 22 cluster agents judging
DUPLICATE-OF / SUBSUMED-BY-EPIC / OVERLAPS / DISTINCT, each proposed close then
challenged by an independent agent (duplicates: would work actually be dropped;
epics: is there a literal `- [ ]` line, and does it create a chain).

Observation to test, not assume: the highest near-duplicate cosine in the whole repo is
**0.503** (#867 housing benefit vs #869 JSA claimants — two different programs with the
same class of defect). True duplicates usually score far higher, so the expected finding
is that this repo has very few real duplicates and many adjacent-but-distinct issues.
The cluster agents are told DISTINCT is the expected answer and a good one.

### Owner sweep: the PR half of every RESOLVED-CLOSE is sound

Ran all **26** RESOLVED-CLOSE candidates' cited PRs through corpus state +
`git merge-base --is-ancestor <mergeCommit> origin/main`: **26/26 MERGED with a
verified-ancestor merge commit**, zero citing an open or unreachable PR. So the open
question on each row is only whether that PR delivers the issue's *whole* ask — which is
what the `whole-ask` refuter lens tests.

Two rows verified at source by the owner: **#546/PR #557** (main carries
`TARGET_MATERIALIZATION_CACHE_SCHEMA_VERSION = 3` "Bumped 2 -> 3 for #557" and both
identity digests in `REFORM_VECTOR_CACHE_CONTEXT_KEYS`) — ask delivered.
**#511/PR #517** (mortgage measures rebound to `deductible_mortgage_interest`, both rows
registered `allow_incumbent_improvement=False`) — delivered, **but reading the code
surfaced a residual the evidence had not**: the amount row still carries
`max_abs_relative_error=0.20` with an in-file comment to ratchet it "once microcosm#515
lands and a run holds 0.15", and #515 is CLOSED. That ratchet is now due.

### Assembler + report scaffolding written

`assemble5.py` merges rows by precedence (workflow-adjudicated > run-5 stage-1 salvage >
run-3 candidate, each row tagged with its `_source`) and applies cluster overrides only
where an independent challenger upheld them. `build_extra5.py` generates the report's
cross-cutting sections. `render5.py` emits the report + JSON and runs the structural gate.

### Cluster pass, early returns

First 10 clusters back: **17 DISTINCT, 6 OVERLAPS-CONSIDER-MERGING, 0 DUPLICATE-OF,
0 SUBSUMED-BY-EPIC** — consistent with the 0.503 cosine ceiling. Example of the bar being
held: #346 vs #347 (cosine 0.448) ruled DISTINCT because #346 asks for the *capability*
(informed-init L0 reselection) and #347 for a *country run* that explicitly depends on it;
their 0.448 comes from Max cross-posting one correction comment to both.

### Owner verification of the deferral layer + a coherence defect

Read 3 of the 7 `RULED-DEFERRED` rulings at source on main and all three hold exactly as
cited: **#467** (`uk/source_stages.json:3162-3170` declares the CGT-band fence with
`"calibration_permitted": false`, 76 fenced facts, a rationale, a promotion path and an
adjudication pointer to #552 — a reviewed refusal of precisely what #467 asks);
**#687** (`uk/frs_release.json` pins `frs_2024_25`, noting "Adopted from the old E11 scope
(microcosm#723)" — the 2023 build is the road not taken); **#697**
(`specs/us_imputation_lineage.yaml` ABSENT from main, deleted by ancestor `f85c24840`;
`docs/spec-engine.md` is "v3 — APPROVED by Max 2026-08-16" and rules it "retired at the flip").

**Coherence defect caught by extending the validator: #224 is closed as a duplicate into
#213, but #213 is itself `STALE-ASK`.** That would leave the 20k-sample ask carried only by
an issue this same report asks Max whether he still wants. Added `SURVIVOR-IS-STALE-ASK`
and `EPIC-CHAIN` checks so the pair must be resolved before either line is published.

**STALE-ASK floor re-measured:** all 12 candidates are genuinely idle 63–90 days
(recomputed from `updatedAt` plus every comment date). Of the **94** issues idle ≥ 60 days,
only 12 are STALE-ASK and **55 are KEEP** — silence is not treated as evidence.

### Whole-corpus citation audit (owner, mechanical)

Extracted every repo path and backticked symbol from the evidence of all 40 close-class
rows and checked each against `origin/main`:

- **96 cited paths → 1 absent**, and that one is `specs/us_imputation_lineage.yaml` on
  **#697**, where the absence *is* the evidence (retired at the spec-engine flip).
- **53 cited symbols → 1 with zero files on main**: `work_experience_inputs` on **#719**,
  which exists only in still-open PR #745 — independent corroboration that #719 is
  misdispositioned (its claimed epic #922 names it only in a prose `Related:` line).

With the 26/26 PR-ancestry result, the citation layer holds: the only failures are the two
rows the validator already flagged, and both are real defects rather than noise.

Two more rows read at source: **#57/PR #855** (`calibrate/hierarchy.py` present on main with
`HierarchyCategory`/`HierarchyGeography`/`HierarchyDimension`) confirmed; **#449/PR #741**
confirmed, but with a correction — the evidence says the parity knob was "retired", while
`gate_congressional_district_targets` still exists and is merely **defaulted to `True`**
(`tools/build_us_fiscal_refresh_release.py:2307`), with the `False` path still exercised in
tests. The close comment must say "defaulted", not "retired".

### Cluster pass complete (`wf_6783fa4b-567`, 28 agents, 0 errors)

**107 relations: 90 DISTINCT, 13 OVERLAPS-CONSIDER-MERGING, 4 SUBSUMED-BY-EPIC, and
zero DUPLICATE-OF.** The hypothesis held: across all 15 near-duplicate clusters — cosine
ceiling 0.503 — **not one pair is a true duplicate**. This repo files adjacent work as
separate, well-specified issues. The 13 overlaps are real and reported as a
"consider merging" section rather than closed, e.g. #471 and #472 open with "Audit finding
1 / finding 8 of #468, split out as its own increment", and #546 is a sharper restatement
of #380's gap 2 on the same `REFORM_VECTOR_CACHE_CONTEXT_KEYS` cache.

Of the 4 epic-subsumption proposals (#262 #263 #264 #265 → epic #259), the independent
challengers **overturned three**: each has a genuine literal `- [ ]` line in #259, but
closing it would drop tracked work that main itself points at — `be/source_stages.json:80`
("the base population stage (populace#262 owns the runtime)"),
`be/release_contract.json:38` (#262 owns the destination guards), and `be/gates.json:4`
("External-oracle implementation ... remains separate work in #264 and is not implemented
here"). Form passed, substance failed — which is the right order.

**Owner override on #265 (documented in `assemble5.py`, not silent).** Its challenger
returned UPHOLD, but its own `unique_to_this_issue` lists five concrete publishing
mechanics that exist only in #265 and are undelivered on main (a BE path in
`publish_release.sh`, `latest.json` uploaded last as the atomic pointer, the
`populace-be-staging` telemetry repo named in `be/release_contract.json` with no writer,
the BE Slack alert, and a `("be", year)` DatasetSpec in `microcosm-data/registry.py`).
The batch agent independently reached KEEP on the same evidence, and merging one of five
epic children while #262/#263/#264 all stay open is incoherent. **#265 stays KEEP.**

### The near-duplicate detector had a proven false negative — gap closed

The one real duplicate in this repo, **#224 → #213** (both ask for a small ~20k calibrated
national US dataset for Colab/web/CI), was found by a *batch* agent reading dossiers, not
by the near-duplicate detector. Recomputing TF-IDF cosine for that pair:
**0.162 — well under run 3's 0.28 threshold.** They use different vocabulary
("L0 sparsification" vs "calibrated national sample") for the same ask.

So "the cluster pass found zero duplicates" was only ever a statement about the 37
above-threshold pairs, and the absolute threshold demonstrably misses real duplicates.
But #213 and #224 are each other's **top-ranked match** — a rank-based test catches what
the threshold missed.

Mitigation: recomputed the full 234×234 TF-IDF matrix and took **mutual top-1 nearest
neighbours** (a is b's best match *and* b is a's). That yields 52 pairs, **33 of them not
in the original 37-pair set**, spanning 66 issues and reaching as low as cosine 0.130.
Launched workflow `wf_97f1f4e3-e0f` over those 33 as a second cluster pass with the same
challenger gate, so the duplicate layer no longer rests on an absolute cutoff that is
known to have failed once.

### Correction: my #449 "overstatement" note was itself a conflation

I earlier flagged the #449 evidence for saying PR #741 "retired" the CD knob while
`gate_congressional_district_targets` still exists on main. Those are **two different
flags** and both observations are true:
`include_congressional_district_targets` (inclusion) is genuinely gone — `git grep` over
all of `origin/main` returns one hit, in the `_LANE-NOTES.md` journal — while
`gate_congressional_district_targets` (gating) is still live and defaults `True`.
`us/spec/calibration.yaml:15-20` reconciles them: `cd_policy:
always_present_report_attainment`, `congressional_district: {included: true,
gate_by_default: false}`. The evidence was accurate; no row change is needed.

### Verification is overturning candidates, in both directions

173 of 234 rows in. **8 differ from the run-3 candidate** — and the interesting thing is
that they move both ways, which is what an honest verification layer looks like:

- `RESOLVED-CLOSE → KEEP`: **#32** (inventory half landed, the HSA/childcare input-depth
  gap did not), **#258** (PR #229 routed net VAT through the Axiom rules engine, but the
  near-threshold density half is still on main), **#449** (CD surface unconditional, epic's
  other deliverables open — re-scope rather than close).
- `RESOLVED-CLOSE → STALE-ASK`: **#296**, where main's own artifacts falsify the issue's
  premise (`build_j_recert/base_j.summary.json` records ASEC 2022/2023/2024 row counts
  matching the pinned Census files exactly) while the number is still used as a live
  handle — so the right output is a question to Max, not a close.
- `KEEP → RESOLVED-CLOSE`: **#250**, delivered by PR #277 (`10881bfa5`, ANCESTOR), which
  created `us_runtime/geography_ladder.py` with `county_fips` derived for every household.
- `STALE-ASK → KEEP`: **#48**, **#366**. `RULED-DEFERRED → MERGE-INTO-EPIC`: **#687**.

Zero rows came back `UNDETERMINED` and zero at low confidence (150 high, 23 medium).

### All 35 batches in — 234/234 rows, every one run-5 derived

No row now falls back to a run-3 candidate. Stage-1 distribution: 183 KEEP, 28
RESOLVED-CLOSE, 10 STALE-ASK, 6 RULED-DEFERRED, 6 MERGE-INTO-EPIC, 1 DUPLICATE-CLOSE.
Zero rows returned `UNDETERMINED`; zero at low confidence. The verify / sweep / adjudicate
stages are still running and can still move rows.

### Two cross-batch collisions only an owner pass could catch

**1. A mutual duplicate chain that would have deleted an ask.** The `us-calibration-2`
agent closed **#213 into #224**; the `release-publishing-1` agent closed **#224 into #213**.
Each was right that the pair is a duplicate and neither could see the other's batch —
but applying both would have closed *both* issues and removed the 20k-sample ask from the
tracker entirely. Owner adjudication: **#213 is the survivor and stays open**; it is
strictly better specified (HDF5 schema parity, household integrity across
tax_unit/spm_unit/family/marital_unit, the named calibration target list, bundle
registration so `pe.us.managed_microsimulation(dataset='populace_us_20k')` resolves), more
recently active (2026-07-03 vs 2026-06-29), and carries the verified free-Colab data point.
Neither ask is delivered: `microcosm-data/registry.py` declares exactly three DatasetSpecs
on main (uk-2023-compact, uk-2025-dense, us-2024-compact) and no ~20k US variant.
#224's two unique requirements ride in its close comment.

**2. The "literal checklist" rule was too narrow, and fixing it changed exactly one row.**
Neither epic #530 nor epic #922 uses checkboxes *at all* — they track work as numbered
items. Re-classified every MERGE-INTO-EPIC row by whether its parent tracks it as a work
item in that epic's own list format, excluding bare `Related:` asides:
#395→#578 (numbered item 1), #403→#578 (numbered item 2), #661→#736 (checkbox),
#687→#796 (checkbox), #719→#922 (numbered item 5), #731→#796 (checkbox) — **all valid**.
Only **#416→#530 fails**: #530 runs its plan as 8 numbered items and #416 is in none of
them, appearing solely as "- Related: #416 (whether `*_would_be_qualified` should be
derivations rather than QRF targets)". A cross-reference is not a commitment to do the
work, so **#416 is downgraded to KEEP** — and nothing on main answers it either
(`git grep 'qbi_assumptions_v2|sstb_crosswalk' origin/main` → no hits, no commit cites
#416, no `changelog.d/416-*`). This also corrects my own earlier note, which had called
#395/#403/#719 invalid under the checkbox-only reading.

### Validator: 7 findings, all adjudicated benign and published as such

Cross-repo numbers (#8352 and #8860 are policyengine-us PRs), deliberate statements of
absence (#299 "Not in PR #893", #333 "not cited in PR #893", #697's retired spec), a
truncated file-content sha256 read as a commit (#314), and one correct-and-deliberate open
PR (#719's #745, which epic #922 tracks *because* it is still a draft). Two regex defects
in the validator were fixed along the way: a `.lock.json` path truncated to `.lock`, and
the earlier sha/comment-id bugs.

### Second cluster pass complete (`wf_97f1f4e3-e0f`, 33 agents, 0 errors)

Both passes merged: **170 relations — 151 DISTINCT, 15 OVERLAPS-CONSIDER-MERGING,
4 SUBSUMED-BY-EPIC, and still zero DUPLICATE-OF**, now covering 70 pairs down to
cosine **0.130** (not just the 37 above 0.28). The rank-based sweep found no duplicate the
threshold sweep had missed, which is the answer that makes the original result trustworthy
rather than an artifact of the cutoff: the duplicate layer of this repo really is
**one pair, #224 → #213**, and it was found by reading dossiers, not by similarity.

The new pass also produced the sharpest boundary evidence in the report, e.g. #736 vs #796
(cosine 0.413, the highest unexamined pair): they are deliberately complementary registers
— #736 is the contract/calibration-target side, #796 the spine/frame side — and #736's own
body line 21 *hands* `local_authority_support_floor_excluded` and
`council_tax_band_h_spine_support_absent` to #796 "because the fix is frame rows for those
areas, not targets". Merging either way would have destroyed a deliberate partition.

### Report pipeline green end-to-end

`assemble5.py → owner_validate5.py → build_extra5.py → render5.py` runs clean:
**234 rows, 0 structural errors, 0 warnings**. Draft is ~600 KB because section 2 carries
the full evidence for every issue (~2 KB each) — that bulk *is* the deliverable, and the
summary table gives a short pointer per row for navigation.

Fixes made while reviewing the draft: section 6 and 7 were emitted out of order; section 4
("consider merging") was empty and is now wired to the 8 deduped overlapping pairs from the
cluster passes; the validator block was computed but never rendered; and every headline
figure was hardcoded — the idle-≥60d KEEP count had already drifted from 55 to 64 as rows
finalized, so all of them are now computed from `final_rows.json` at render time.

Section 4 turned out to be one of the most useful parts: it names concrete merge actions
(e.g. "add literal `- [ ] #471` and `- [ ] #472` lines to #468 and mark findings 1 and 8 as
tracked there, leaving #468 to carry 2-7") and flags that #468/#472's cited line numbers
have drifted with the populace→microcosm rename (the preflight call is
`us_runtime/release_gate_preflight.py:827`, not `:776`).

### Remaining

Verify / sweep / adjudicate stages of `wf_66de6532-038` are still running and can still
move rows. On completion: reassemble from the adjudicated rows, run the close-comment pass,
re-run the validator, regenerate, and write the two deliverables.

### The close-first list is tiered by what happens to the residual

First attempt split it by "has a residual / doesn't" and **Tier 1 came out empty**: not one
of the 28 RESOLVED-CLOSE rows closes with literally nothing left over. That is an honest
finding but a useless category, so the split was rebuilt around the question that actually
matters when closing — *does the leftover work have somewhere to live?*

- **Tier 1 (24): close; the residual already has a home.** Whatever the cited artifact does
  not cover is explicitly carried by another issue or PR named in the residual.
- **Tier 2 (1): close only if the comment records the residual.** Exactly one row —
  **#31** — has leftover work that names no successor: its fix-direction bullet "before
  changing any UK formula/input surface, compare stored aggregate vs formula-recomputed
  aggregate and record the result" has no standing instrument on main (the only
  `frozen_vs_recomputed` symbol is `uk_runtime/size_evaluation.py:864`, a dataset-size
  metric, not a formula-owned column audit). Close it and that item exists nowhere.
- **Tier 3 (4): closable, but read first.** #70, #361, #473, #512 — medium confidence,
  each with a named soft edge (an acceptance criterion only an out-of-PR-CI certification
  run can settle; a successor PR still open and non-ancestor; a mechanism delivered for the
  named cases but not generically).

### Mid-lane closure recheck: zero churn

Re-pulled the open-issue list and re-fetched `origin/main` at the end of the lane
(`gh rc=0`): **still exactly 234 open issues, identical membership, and main still
`18271b28d`**. Nothing closed or opened while the triage ran, so no row in the report
describes an issue whose state has since moved. That fact is now stated in the report's
method section rather than left implicit.

### The verification layer is doing real work — and it reshaped the epic category

Early returns from the refuters: **8 UPHOLD, 8 OVERTURN, 6 AMEND**, while **15 of 15
missed-resolution sweeps over the KEEP rows returned ZERO overturns**. So the KEEP layer is
solid and the close-class rows are where the contest is — which is the right shape.

The most consequential challenge: a refuter overturning #731 argued that in epics #796 and
#736 the checkbox *mirrors* child state (`[x]` = child CLOSED, `[ ]` = child OPEN), so the
epic is an index, not a container. Measured it myself over every checkbox line naming a known
issue (excluding PR numbers, which my first pass wrongly counted):

| epic | checkbox matches child state |
|---|---|
| #796 | 43/58 |
| #736 | 23/41 |
| #665 | 14/17 |
| #259 | 6/9 |
| #925 / #882 / #454 | 1/1 each |

**Directionally right, literally overstated**: the pattern holds exactly inside the block the
refuter read (#796's "Filed spine issue" lines) but not across the whole body, and most
misses are *stale* unchecked boxes for children that closed without the epic being updated.

What survives is the part that matters: **these epics index independently-tracked children
rather than absorbing them.** Closing a child because the epic lists it destroys the child's
specification and leaves a checkbox pointing at an emptied issue. That is why refuters
overturned **#661, #687, #719 and #731 to KEEP**, each citing concrete content that would be
lost. `MERGE-INTO-EPIC` may collapse to near-zero once the adjudicators finish.

**This also corrects my own earlier call on #719.** I had accepted it under the "numbered work
item" standard, but epic #922's item 5 reads "**Industry and worked-last-year on the
records.** #745 (`work_experience_inputs` stage; parent #719) is still a draft" — the tracked
unit is **PR #745**, with #719 only named parenthetically as its parent. Two independent
refuters caught that; they are right and I was wrong.

### #31's Tier-2 residual verified at source

Since #31 is the one close whose leftover names no successor, I checked its residual claim
rather than trusting it. `git grep -n frozen_vs_recomputed origin/main -- packages/ tools/`
finds exactly one implementation: `uk_runtime/size_evaluation.py:864`,
`frozen_vs_recomputed(run: RowwiseRun, surface_evaluation: ...)`, docstring "Compare frozen
national contributions with recomputed surface values" — a **dataset-size** surface metric
feeding `frozen_vs_recomputed_max` (:1033, :1124, :1164), not an audit of UK formula-owned
columns. No other stored-vs-recomputed per-column report exists on main. The residual stands:
closing #31 without recording it erases the only trace of that fix-direction bullet.

### Collector for the adjudicated rows written (`collect_wf.py`)

Pulls the workflow's final per-batch returns out of `journal.jsonl` into `r5/wf_final.json`,
which `assemble5.py` already consumes at highest precedence. Running tally as the verify
stage works through its queue: **11 UPHOLD / 13 OVERTURN / 10 AMEND** across the close-class
refuters, and **17 of 17 KEEP-sweeps returning zero overturns**. A ~38% challenge rate on
close-class rows against a clean KEEP layer is the expected shape — the contested decisions
are the ones that close things.

### The KEEP sweep is a real negative result, and the report now says so

Checked that the missed-resolution sweeps were doing work rather than returning empty: they
enumerate the exact KEEP rows of their batch, and **94 KEEP issues have now been individually
re-checked for "is this already done / already duplicated / already ruled" — with zero
overturns**. That negative result is worth as much as the closes: it is the evidence that
this backlog is long because the work is real, not because finished work was left open.

Added an "Adversarial verification" block to the report that reads its numbers live from the
workflow journal (refuter verdict split, KEEP rows swept, sweep overturns, rows decided by an
adjudicator) so the figures cannot drift from what actually ran.

(Two shell-quoting slips fixed along the way: an unquoted heredoc let zsh evaluate the
backticked `KEEP`/`STALE-ASK` literals as commands and silently blank them, and `T` was not
exported into the python child on the first repair attempt.)

### Refuter verdicts persisted as salvage — and MERGE-INTO-EPIC is collapsing

Saved all refuter verdicts and KEEP-sweeps to `r5/refuter_verdicts.json` / `r5/keep_sweeps.json`
so the AMEND corrections (which carry materially better residuals than the originals, e.g.
#324, #252, #731) survive even if adjudication does not finish. 39 verdicts over 23 issues.

The signal is consistent and one-directional on the epic layer — **all six**
`MERGE-INTO-EPIC` rows drew at least one OVERTURN:

| row | lens verdicts |
|---|---|
| #395 | OVERTURN, OVERTURN |
| #719 | OVERTURN, OVERTURN |
| #661 | UPHOLD, OVERTURN |
| #687 | UPHOLD, OVERTURN |
| #403 | OVERTURN, AMEND |
| #731 | OVERTURN, AMEND |

That is the independent confirmation of the structural finding above: in this repo an epic
is an index over independently-tracked children, so closing a child into it destroys the
child's specification. #416 (already downgraded by owner adjudication) drew OVERTURN + AMEND
from the agents too, which agrees.

Clean UPHOLDs on the close side: **#470 and #640 (both lenses), #697 (both lenses), #31,
#159, #419, #454**. The three `STALE-ASK` reality checks that returned so far — **#104, #303,
#305** — all say KEEP: each is a clear, still-true, well-specified item that nobody has worked
on, which is exactly the case the rulebook says must never become an ask.

### The headline claim was wrong, and the way it was wrong is the finding

The KEEP missed-resolution sweep produced its first overturns — **two proposed duplicates
that neither similarity pass had ever examined**: #390 → #578 (Build L epic subsumed by the
"US base v2" scope-hardening Max ratified 2026-07-29) and #424 → #644 (SSI eligible-mass
shortfall restated on a two-builds-newer measurement).

Checked whether the similarity passes had seen either pair: **neither was a candidate.**
Cosines: #390~#578 = **0.135**, #424~#644 = **0.236**, both under the 0.28 threshold and
neither a mutual top-1 pair. Together with #224~#213 at **0.162**, that means **every
duplicate candidate in this report was found by an agent reading both issue bodies in full,
and lexical similarity found none of them** — across 70 pairs and two independent passes.

So the earlier headline ("exactly one duplicate ... two cluster passes returned no second
duplicate") was reading a null result from the wrong instrument. Rewritten to say what is
actually true: these issues use dense, fast-moving domain vocabulary, so the same ask filed
three weeks later shares almost no words with the first, and similarity-based triage of this
repo should be treated as unreliable. That is a more useful finding than the tidy claim it
replaced — and it is exactly why the multi-modal design (similarity **and** a read-everything
sweep) mattered.

**Neither new duplicate is being taken on the sweep's word.** DUPLICATE-CLOSE is the
highest-stakes disposition and these two never got the challenger the cluster duplicates did,
so `wf_fab767b7-c08` puts both through the same two lenses (same-ask / detail-loss, defaulting
to OVERTURN). My own read is that **#424 is an overlap rather than a duplicate**: #424 is an
aggregate eligible-mass shortfall with four named candidate causes, while #644's sharper
claim is an age-*composition* defect (+55% at 18-24, -85% at 60-64) and it explicitly says
"Do not force eligibility to recipient counts". The challenge decides, not me.

### Both paths now consume the duplicate challenge, and a rejection is recorded, not dropped

`assemble5.py` (the normal path) and `fallback_adjudicate.py` (the insurance path) both read
`r5/dup_challenge.json` and apply a sweep-proposed duplicate **only where both lenses upheld
it**. A rejected proposal is not silently discarded either: the row keeps its KEEP
disposition and gains an `owner_note` saying a sweep proposed closing it as a duplicate of
#N and an independent two-lens challenge rejected it. That way the report shows the
near-miss and its reasoning rather than looking like the question was never asked.

Also extended the fallback to cover sweep duplicates, so the insurance path produces the same
answer as the normal path if adjudication never lands.

### Both sweep duplicates rejected — 4/4 challenge lenses OVERTURN

`wf_fab767b7-c08` returned 4 agents, 0 errors, **all four lenses OVERTURN**. Neither
proposed duplicate survives, so the duplicate count stays at exactly one (#224 → #213) —
but now because it was tested, not because nothing else was looked at.

**#424 → #644 dies on arithmetic.** #424 measures modeled eligible mass at ~2M scaled
against SSA's 7,404,820 recipients — 27% *of* recipients, structurally impossible, saturating
the take-up gate in every band. #644 measures Build P at 9.99M payable adults against SSA's
6.288M adult recipients — 159% *of* recipients — and its 20.7% gap is against Urban/ATTIS's
*eligible* benchmark of 12.602M, a different denominator entirely. Opposite signs, different
benchmarks, different regimes. #424 also spans under-18 (1,001,922 recipients) while #644 is
titled and scoped to adult bands. My own read — overlap, not duplicate — was right, but the
challenge found the far stronger argument.

**#390 → #578 dies on content and on repo behaviour.** Grepping #578's body plus all 13
comments returns **zero** hits for `#296`, `#380`, `#388`, `#346`, `#330`, "warm-start",
"protect-list", "TANF", "HSA", "small-state" — or for `#390` itself. #578 replaces #390's
*method* (exact-k selection for warm-start reselection), which makes #390 superseded in
method, not duplicated in ask. The decisive point: #578's ratified scope-hardening retires a
sibling **by name** ("the separate local-area artifact is RETIRED... the #512 lane ends as a
product") and **#512 is still open**, updated a week after that ratification. A repo that
keeps open the issue #578 explicitly terminates will not have meant #390 — which #578 never
names — closed as its duplicate.

### The headline was wrong twice, in opposite directions, and is now right for a stated reason

First it claimed one duplicate from a similarity null result (wrong instrument). Then, after
the sweep, it cited #390 and #424 *as* duplicates (premature — they had not been challenged).
The final text says what is actually true: similarity contributed **nothing**; all three
candidates came from reading bodies; an adversarial challenge killed two; **#224 → #213** is
the one real duplicate. Each rejected candidate keeps its KEEP row plus an `owner_note`
recording the near-miss and why it was refused, so the reasoning is visible rather than the
question looking unasked.

### Salvage-path bug found and fixed: the journal never records stage returns

`collect_wf.py` was looking for the workflow's stage-3 `batch_id` objects in
`journal.jsonl`. **They are never there** — the journal records only `agent()` results, and
stage-2/stage-3 returns are plain JS objects computed inside the script, visible only in the
final workflow result. Worse, adjudicator agents return the **same `{"rows": [...]}` shape**
as stage-1 triage agents, so shape alone cannot tell them apart and my collector would have
silently merged adjudicated rows into the triage bucket (or missed them entirely).

Fixed by mapping `result.agentId` → `agent-<id>.meta.json`'s `description` (the `agent()`
label), which matches **122/122**. The collector now separates `triage:` from `adjudicate:`
from `verify:` from `sweep-keep:` reliably, and adjudicated rows win the merge.
Current: 234 triage rows, 0 adjudicated (none spawned yet), 63 refuter verdicts
(20 UPHOLD / 17 OVERTURN / 26 AMEND), 24 sweeps covering **127** KEEP issues.

### A third sweep overturn — and it contradicts a verified KEEP head-on

**#253 → RESOLVED-CLOSE citing PR #399.** Unlike the two duplicates, this one proposes
*closing on delivery*, and it directly contradicts the batch agent's own high-confidence
KEEP, which reads: `with_us_education_inputs` (`us_runtime/education_inputs.py:186`) is
"factual-input-only" — it restores ASEC `ED_VAL` via a pinned `PERIDNUM` join and derives the
five affirmative AOTC flags *from* positive tuition, but **never predicts tuition**, so it
delivers the flag half of the ask and none of the tuition half. It also notes main still
names this issue as the live tracker at
`tools/build_us_release_input_coverage_manifest.py:666` (`"issue": "PolicyEngine/microcosm#253"`).

Two agents read the same repo and disagree on whether a declared stage output means the leaf
is imputed. Launched `wf_0d25090f-d8f` with whole-ask and citation-real lenses to settle it
by running the commands, rather than letting a single adjudicator arbitrate a factual
dispute about what `education_inputs` actually computes.

### #253 settled at source: declared-output membership is not ownership

Rather than wait for the challenge, I read the code. `education_inputs.py` on main settles it
against the sweep, in its own words:

- `:74-78` `US_EDUCATION_INPUTS_OUTPUT_COLUMNS` **does** list `qualified_tuition_expenses` —
  which is what the sweep saw.
- `:80-81` the comment directly above the next constant: *"Qualified tuition is produced
  upstream by the PUF tax-detail operator. This stage validates and consumes it, but must not
  claim or rewrite it."*
- `:82-86` `US_EDUCATION_INPUTS_OWNED_OUTPUT_COLUMNS` **excludes** tuition — it owns only
  `educational_assistance` plus the five AOTC flags.
- `:88-92` `US_EDUCATION_INPUTS_REQUIRED_SOURCE_COLUMNS` lists tuition as a required **input**.
- `:198` docstring: the fill "is an exact per-income-year `PERIDNUM` join and **never predicts
  a value**."

So the stage consumes tuition to derive AOTC flags; nothing on main imputes it. The batch
agent's KEEP was right and the sweep misread declared-output membership as ownership.
**#253 is locked to KEEP** in the owner adjudication map with that evidence, so no later
stage can flip it without confronting these lines.

### A fourth sweep overturn, and this one is a real improvement: #777

The sweep proposed KEEP → RULED-DEFERRED on #777, and it is right. Verified myself: the
ruling is the issue's **own body**, authored by MaxGhenis 2026-08-25 with zero comments
since, line 13 — *"**Sequencing:** needs engine-side consumer variables first ... Parking
this issue so the design intent from #767 is not lost."* And its stated precondition is
verifiably unmet: grepping main for
`redetermination|verification_propensity|fails_program_redetermination|documentation_propensity`
returns exactly one file, `us/engine_abi.lock.json`, whose only hit is the unrelated Nebraska
CCDF variable `ne_child_care_subsidy_at_redetermination`. Applied.

That is the sweep earning its cost: an issue carrying its own parking ruling that the batch
pass had read as ordinary live work. Running totals — 150 KEEP issues swept, 4 overturns:
two duplicates (both rejected on challenge), one resolution claim (rejected at source), and
one genuine deferral (applied).

### Collector labelling corrected

`collect_wf.py` was writing stage-1 triage rows into `wf_final.json`, which made the
assembler stamp them `run5-verified` when they had been through no verification at all. It
now emits **only adjudicated rows**; stage-1 rows reach the assembler from `r5/rows/*.json`
and keep the honest `run5-triage` label.

### STALE-ASK reality checks are discriminating, and #296 is the row I could not settle

Seven of ten stale checks are back: **#303, #305, #104, #388 → KEEP** (idle but clear,
still-true and unworked — the case the rulebook says must never become an ask), **#159 and
#419 UPHELD** as genuine STALE-ASK, and **#296 → RESOLVED-CLOSE**. The #305 overturn is the
model of what these checks are for: it found that Max *applied* the very convention #305
defines twelve days ago (#848 labeled `tier:standard` on 2026-09-02), so the issue is an
operating policy, not an abandoned ask.

**#296 is the most contested row in the lane** — run-3 said RESOLVED-CLOSE, the run-5 batch
agent said STALE-ASK, the stale check says RESOLVED-CLOSE. I tried to settle it and **my
first inference was wrong**: I found `us/source_stages.json:740` / `sources.yaml:841` pinning
`asecpub23csv.zip` and concluded the spine still pins ASEC 2023, but reading the surrounding
block shows that pin belongs to the **`weeks_unemployed_input`** stage, one narrow leaf. The
`asecpub24`/`asecpub25` references on main are in `education_assistance_source.py`, another
sidecar. So `source_stages.json` settles nothing here — the pool's ASEC vintages arrive as
`census_cps_*.h5` build inputs, not as a pin readable off main.

What *is* checkable: **no `changelog.d/296-*` fragment on main and no commit citing #296**,
and the strongest positive evidence is an *experiment* receipt, which this lane's own rules
rank below code — while artifact certification runs outside PR CI where I cannot reach it.

So I am deliberately **not** locking #296. Leaving it at `STALE-ASK` is the honest outcome:
that disposition exists exactly for a well-specified issue whose delivery state cannot be
settled from the repo and whose right next step is a question to Max. That question is
already written into its `next_step`.

### #253 challenge: both lenses OVERTURN, and the challenge corrected the row it upheld

`wf_0d25090f-d8f` returned 2 agents, 0 errors, **both OVERTURN** — the KEEP stands and the
sweep's RESOLVED-CLOSE is refused. Two things came out of it that I had not found myself:

**A stronger decider than mine.** I had settled it on a source comment; the challenge found
main *enforces* it in a test: `packages/microcosm-build/tests/test_us_education_inputs.py:312`
`test_with_inputs_does_not_rewrite_upstream_tuition` asserts byte-equality of the column, and
the spec ownership matrix (`us/spec/imputation.yaml:33359-33439`) records all six
`qualified_tuition_expenses` rows for this producer as `owns_final: false`,
`action: consume_only_byte_exact_noop`. The manifest `outputs` list the sweep relied on is a
passthrough declaration, not authorship.

**The KEEP's own evidence was overstated, and is now fixed.** Main *does* carry a whole-pool
QRF imputation of this leaf — `late/person/puf_tax_itemization__batch_2` declares
`model: regime_gated_qrf`, `output_coverage_scope: whole_pool`, and the leaf is absent from
`ecps_parity_known_gaps.json` so the parity gate requires it populated. So the
**structural-zero half of #253 is delivered**; "still only a PUF-QRF clone output" was wrong.
What keeps the issue alive is narrower and better stated: the leaf's *level* is a
PUF-donor-rate reproduction with no SOI anchor (every guard added is a structural-zero floor
the reported state already passes — `_TUITION_SHARE_BAND = (0.001, 0.05)`,
`min_nonzero_records: 500`, and an `aotc_abolition` probe whose $100M `min_abs_effect` cannot
detect a ~$3B shortfall), the five AOTC flags are a tautology on the tuition mask
(`education_inputs.py:179` sets `aotc_student = tuition > 0.0`, `:182` assigns it to all five
including the half-time flag), and no education-credit calibration target exists.

It also caught a methodological slip in the original KEEP: its `git grep -rni 'ipeds|nces'`
was unanchored and matched the substring inside "refe**rences**"; the word-anchored
`\b(IPEDS|ipeds|NCES)\b` returns zero hits, which is the claim that actually holds.

Row rewritten with the corrected evidence, residual and next step, plus an `owner_note`
recording the near-miss and one thing neither side could check read-only: PR #399's body
cites a $12.28B AOTC abolition probe, but that figure lives only in the PR body, is a total
rather than the nonrefundable concept the $7.55B benchmark uses, and never reached an
artifact on main.

**Adjudicators are now running** (2 spawned) — stage 3 has begun.

### Finalisation is now one ordered command (`finalize.sh`), after an ordering bug

Running the steps by hand produced a stale report: `build_extra5.py` read
`final_rows.json` **before** `assemble5.py` had merged the adjudicated rows into it, so the
report printed "Rows whose final disposition came from an adjudicator: **0**" while #303 had
in fact been adjudicated. `finalize.sh` now runs collect → assemble → validate → build
sections → render → worktree-clean check in dependency order, so the sequence cannot be got
wrong on the final pass.

### The populace→microcosm rename trap caught one citation

The re-run surfaced a new validator finding: **#546** cites
`packages/populace-build/tests/test_us_fiscal_refresh_builder.py`, which is **absent** from
main after the 2026-08-07 rename — the artifact lives at `packages/microcosm-build/...`. The
substance is fine; a reader following the citation would just find nothing. Swept all 234
rows for pre-rename paths: **exactly one** occurrence, so the trap is otherwise well handled.

Rather than silently rewrite an agent's cited claim, added a general rule to `assemble5.py`:
where a row cites a `packages/populace-build/...` path that is absent from main *and* the
`packages/microcosm-build/...` equivalent exists, append a visible bracketed
`[lane correction: ...]` naming both paths. It is a rule, not a one-off patch, so a
re-run after more adjudication will catch any new instance.

State: 184 KEEP · 28 RESOLVED-CLOSE · 8 STALE-ASK · 7 RULED-DEFERRED · 6 MERGE-INTO-EPIC ·
1 DUPLICATE-CLOSE. Adjudicators at 5 and climbing; STALE-ASK has already fallen 10 → 8 as
they land.

### Adjudication is landing, and it confirms the predicted collapse

First adjudicated rows, all three changed and all three in the predicted direction:
**#303 STALE-ASK → KEEP**, **#305 STALE-ASK → KEEP**, **#661 MERGE-INTO-EPIC → KEEP** (the
first epic row to fall). The #303 adjudicator is a good example of re-running the deciding
command rather than arbitrating: it checked whether anyone still wants the work and found
`gh api repos/PolicyEngine/microcosm/issues/263/comments` showing MaxGhenis on the Belgium
lane 16 days ago ("In progress on branch be-contract-gates-diagnostic"), with the BE country
package live on main — so idle, but plainly still wanted.

### Fifth sweep overturn: #30 → RESOLVED-CLOSE, and it is a real contest

The sweep argues the lane "found only the source-coverage half (PR #53) and missed the PR
that delivers the headline ask" — **PR #405** ("Chesterton's-fence audit: wire NIPA
wages/proprietors, net worth, LIHEAP; fence every exclusion"), which I verified is MERGED
2026-07-13 with `dc7031882` an ANCESTOR of main. It walks all five acceptance criteria.

But the standing KEEP says the four `bea-nipa-*` aliases sit in `REVIEWED_EXCLUDED_ALIASES`
reasoned "not certified by this release", and that Build P calibrates **only 2** BEA targets:
`total_wages_salaries` and `proprietors_income`. Those are exactly the two the PR title says
it wired. So both sides are citing true facts and the dispute is really about scope — did
#30 ask for the NIPA controls that landed, or for the fuller coverage still fenced out?
Sent to the same two-lens challenge (`wf_7f15ca95-935`) rather than decided on either side's
framing.

Running sweep totals: **176 KEEP issues swept, 5 overturns** — 2 duplicates (both rejected),
2 resolution claims (#253 rejected, #30 under challenge), 1 deferral (#777, applied).

### Adjudication at 8 rows: 5 changed, 3 upheld with materially better evidence

| row | stage-1 → adjudicated |
|---|---|
| #303, #305, #104 | STALE-ASK → **KEEP** |
| #661, #731 | MERGE-INTO-EPIC → **KEEP** |
| #217, #252, #324 | RESOLVED-CLOSE → **RESOLVED-CLOSE** (upheld, evidence rewritten) |

The upheld rows are not no-ops — these are the AMEND cases, and the adjudicators nearly
doubled their evidence: #324 went 1,166 → 2,265 characters of evidence and 629 → 1,451 of
residual, now citing the two author comments that discharge each committed opener item by
`issuecomment-` id.

**#731's adjudicator produced the rigorous version of my own epic measurement.** I had found
the checkbox/child-state correspondence to be 43/58 across #796's whole body and called the
refuter's "every `[x]` is CLOSED, every `[ ]` is OPEN" claim directionally right but
overstated. The adjudicator checked the specific section rather than the whole body and got
**21/21**: all twelve `[x]` entries (785, 791, 750, 688, 685, 807, 808, 809, 828, 832, 834,
862) CLOSED and all nine `[ ]` entries (725, 721, 713, 687, 840, 866, 867, 868, 869) OPEN.
So the claim holds exactly *within* the "Filed spine issues" block — which is what I said —
and that block is a mirror index of separately-tracked issues, which is why merging into it
destroys the child. Independent convergence on the finding from a sharper angle.

### Adjudication at 39 rows — and it reshaped the result

| disposition | stage-1 | after adjudication |
|---|---:|---:|
| KEEP | 183 | **195** |
| RESOLVED-CLOSE | 28 | **27** |
| RULED-DEFERRED | 6 | **6** |
| STALE-ASK | 10 | **3** |
| DUPLICATE-CLOSE | 1 | **3** |
| MERGE-INTO-EPIC | 6 | **0** |

**`MERGE-INTO-EPIC` collapsed to zero** — all six (#395, #403, #661, #687, #719, #731) were
adjudicated to KEEP, each on the detail-loss lens. That is the single biggest structural
finding of the lane: in this repo an epic is a mirror index over separately-tracked children,
so "the epic lists it" is never grounds to close the child.

`STALE-ASK` fell 10 → 3 for the same reason the rulebook gives: idle-but-clear is KEEP, not a
question. Notable individual flips: **#145** and **#250** RESOLVED-CLOSE → KEEP (adjudicators
found undelivered halves), **#296** STALE-ASK → RESOLVED-CLOSE (I had deliberately left this
one unlocked because I could not settle it myself — the adjudicator could), **#566**
RULED-DEFERRED → KEEP.

### Two more general correction rules, both fired once

Adjudicated rows brought two new citation defects, and both are now fixed by rules rather
than patches:

1. **Mistyped 40-char shas.** #361 cites PR #399's merge commit as
   `79335e459d8711528…` where it is `79335e459d8711578…` — one digit. The 12-char prefix
   resolves, so the conclusion stands, but a reader pasting the full string gets "not a valid
   object". The rule annotates any 40-char hex that fails to resolve while its prefix
   succeeds, naming the real sha.
2. **Pre-rename paths** (already in place) fired on #546.

Both emit a visible `[lane correction: …]` rather than silently rewriting an agent's claim.

Remaining validator output: 11 findings, all adjudicated benign and published with a
per-finding explanation, plus **1 warning worth keeping visible** — #746's evidence cites
`_LANE-NOTES.md:230`, a root journal. It is used as context (the row's load-bearing check is
`git grep … returns nothing`) and the journal line was added by PR #756's own commit, but
CLAUDE.md is explicit that root journals are history, not state, so the warning stays in the
report rather than being suppressed.
