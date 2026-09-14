# Issue triage lane — 2026-09-12 → 2026-09-14 (read-only research lane)

Lane report goes to `~/PolicyEngine/_recovered/scratch-backup/893/triage/out-issue-triage.md`
(the subfleet `-o` path) and `issue-dispositions.json` beside it. Nothing here writes
to GitHub, edits repo-content tracked files, or touches the stash. Branch
`issue-triage-20260912` is local-only (not pushed; pushing would be a GitHub write).
This journal is the lane's own file and is the only tracked file this lane writes.

## State (run 3 — 2026-09-14, live)

- Base: `origin/main` @ `18271b28d` (merge of #904). Runs 1–2 (2026-09-12) reasoned
  against `0c3f4f651`; **#912 merged 2026-09-12 and #904 merged 2026-09-14**, so every
  run-1 "absent from main" claim is re-derived in run 3.
- **Open issues are 234, not the 230 in the brief** (range #27–#925). New since run 1:
  #915, #920, #922, #925 (and the set is re-pulled at the end to catch mid-lane closures).
- Open PRs: 50 (was 43). PR #893 moved: 404 changed files on 9/11 → **691 files / 250
  commits** on 9/14, so its fold-in set is recomputed from the new head `47a12030f`.
- A sibling PR-triage lane (run 3) is live in this same worktree; it commits via plumbing
  to `refs/heads/triage/journal-20260912`. This lane touches only its own journal path.

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

## Next

- Write the agent BRIEF + batches; launch the judgment workflow (per-area cluster passes
  for duplicates/epics ‖ per-batch dispositions → evidence hunt → adversarial verification
  of every close-class claim → reconciliation).
- Render `out-issue-triage.md` + `issue-dispositions.json`; run structural checks;
  personally spot-check ≥5 RESOLVED-CLOSE rows against the cited diffs; re-pull the open
  list for mid-lane closures.
