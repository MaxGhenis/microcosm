# Dense-reds adjudication — continuation (r3)

You are resuming an interrupted lane in this exact worktree
(`/Users/maxghenis/PolicyEngine/_worktrees/microcosm-farmgate`, branch
`stacked-dense-gate-sweep`). Two prior processes died mid-work; the lane's full
state is journaled in `PROGRESS.md` at the repo root. **Read PROGRESS.md in
full before touching anything** — it is the authoritative record of what is
done, what is in progress, and what is blocked.

## Where you are

- 12 continuation commits already landed (HEAD `615710d7`). All prior fixes
  have focused green tests + Ruff.
- The previous attempt (r2, a sol lane) worked ~6 hours and left a **large
  uncommitted diff** in the tree (~32 files: the `acs_rent` property-tax root
  repair, native-zero leaf expansion, spec-schema changes, extensive
  stacked_spine.py and housing_inputs.py work, plus test updates). The same
  state is also preserved at salvage commit `38b424f8`
  (`refs/codex-salvage/stacked-dense-gate-sweep-20260829-233908-31011`).
  It died without journaling, so PROGRESS.md does NOT describe this diff.
- **FIRST ACTION, before anything else:** review the dirty diff against
  PROGRESS.md's plan, then commit it as one or more WIP commits with honest
  messages describing what it appears to contain — so no further work can be
  lost. Then evaluate it: keep and finish what is sound, rewrite what is not
  (via `git revert`/follow-up commits, not history rewrites).
- **Commit discipline:** commit after EVERY completed sub-step from here on.
  Never accumulate more than ~30 minutes of work uncommitted. The r2 failure
  mode was six hours of work held in the tree.

## Remaining work (from PROGRESS.md "### Next")

1. Finish the property-tax producer root repair and the native-zero source
   repairs (ten-leaf expansion incl. the three second-home inputs).
2. Bounded SSI/rent/tenure simulation-copy adapters (engine-copy-only, at the
   dataset boundary; no engine behavior changes).
3. Independent integration review of all fixes landed so far.
4. The actual post-producer health replay (replay gates against the existing
   candidate evidence — this is analysis over existing artifacts, NOT a build).
5. Write the verdict report to the out path (first line must be
   `ADJUDICATION-COMPLETE` or `ADJUDICATION-BLOCKED`, then the verdict).
6. Repository-wide verification: full test suite + Ruff on everything touched.

## Hard constraints (unchanged from the original charter)

- **NO DATA BUILDS.** Max's directive: no pool/dense builds of any kind until
  he says so. Replays over existing evidence only.
- The candidate-25 pool and release evidence at
  `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/candidate-25/` are
  **read-only**. Never modify, never rebuild.
- No push, no PRs, no remote writes. Commit locally after every completed step.
- Keep PROGRESS.md updated as you go (it is your journal and your successor's).
- The stacked `weeks_worked`/ORG ownership question is an **explicit Max
  ruling** — commit `2f7419b2` records the evidence-favored option but
  authorizes nothing. Do not implement any weeks ownership choice, do not
  weaken gate 9480. Leave it as a documented dense blocker in the verdict.
- No gate weakening anywhere; root repairs only.
- Repairs are lane-local: no changes to publication surfaces or artifacts.

## Verdict report contents

Per-red adjudication table (defect class, root cause, fix commit or blocker),
the open Max rulings (weeks_worked ownership foremost), archived-model gate
status (5/6 green post assembly-receipt fix; ORG blocked on weeks), and a
precise statement of what a post-hold dense rebuild would need.
