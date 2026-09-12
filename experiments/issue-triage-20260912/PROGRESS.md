# Issue triage lane — 2026-09-12 (read-only research lane)

Lane report goes to `~/PolicyEngine/_recovered/scratch-backup/893/triage/out-issue-triage.md`
(the subfleet `-o` path) and `issue-dispositions.json` beside it. Nothing here writes
to GitHub, edits tracked files, or touches the stash. Branch `issue-triage-20260912`
is local-only (not pushed; pushing would be a GitHub write).

## State
- Base: origin/main @ 0c3f4f651 (Merge PR #911). Open issues: 230 (27..908). Open PRs: 43.
- Raw data pulled to the session scratchpad: open/closed issues, merged/open/closed PRs,
  230 issue timelines, origin/main git log, PR #893 body/commits/files + its added docs.

## Done
- 07:3x Scouting: -o path confirmed from run meta.json; gh auth OK; counts verified.
- Pulled: issues_open.json (230), issues_closed.json (164), prs_merged.json (444),
  prs_open.json (43), prs_closed_all.json (471; 27 unmerged), timelines/ (230/230, rc=0),
  gitlog_main.txt (1682 commits; 634 distinct #refs), pr893.json (100 files, 96 commits).
- Built indexes: pr_issue_refs.json (144 open issues have >=1 PR ref; 121 have a merged PR
  mention; 0 have a closing keyword from a merged PR), gitlog_issue_refs.json (81 open
  issues referenced in main commits), repo_doc_refs.json (50 open issues cited in docs/
  journals/receipts; 11 via #893's added docs).

## Next
- Build per-issue dossiers; fan out triage (per-batch) + duplicate clustering (per-area);
  adversarially verify every closable claim; script-check evidence; render out.md + JSON.
