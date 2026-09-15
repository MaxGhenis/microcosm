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
