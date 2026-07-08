# Build I — selection-side misc-income support fix for a certifiable 57k default successor

Task: PolicyEngine/populace **#359 Build I**. Fix the ONE Build H (#299) gate failure —
`miscellaneous_income` export mass **−79.9%** on the FROZEN-57k — by fixing the SELECTION, not the
targets. Build H proved the target side works (DENSE passed 0/35 export-mass with the same registry
`d71c59514e3a`; misc reaches −42.0% in-band on the full frame). The deployable frozen-57k's misc
support (~2,145 nonzero records) is too thin to hold the $47.4B national SOI level in the ±50% band.

**STAGING/LOCAL ONLY** — never prod HF / latest.json. Publication + default-flip is Max's call.
Chunked compute (<30-min processes). Detached (nohup/pidfile/rc/append logs). Three-strike stop per
chunk. Every number verbatim from artifacts. Never @-mention; --body-file for GitHub bodies.

## Runtime + branch
- Worktree: `/Users/maxghenis/PolicyEngine/_worktrees/populace-build-h-run` branch **build-i-run**
  (off build-h-run HEAD `b42fbfe`, which carries the d71c59514e3a registry wiring + main merged).
- NEW runtime home (durable, outside repos): `/Users/maxghenis/PolicyEngine/_buildi-runtime/`.
- venv: `.venv/bin/python`, policyengine-us **1.764.6** / core 3.26.11.

## Frozen invariants (inherit Build H exactly; ONLY the SELECTION changes)
base **18833fb6**, pe-us 1.764.6, period 2024, λ=0, seed 0, feed v8 `94b7155f` (37,058+ facts),
registry **d71c59514e3a / 5533 specs**, CD-crosswalk `383a6666`, reform = default
`US_JCT_TAX_EXPENDITURE_REFORMS`. Export-mass reference = live-default 57k `c2065b642ab0…`
(`populace_us_2024.h5`), ±50% band, $1B floor. Parent weights = published Build H dense
(`populace-us-2024-buildh-dense-warmstart-b449eb7-20260708T100442Z`, final_loss 0.04018).

## Design (per #359 + corrected #346 + learned-prior fourth-arm evidence)
1. **Pool**: full 337,704 (Build H dense frame checkpoint `buildh-dense`, registry d71c59514e3a HITS).
2. **Protect-list**: dominant carrier(s) of EACH of the 5533 targets by contribution-share / leverage
   (`wᵢ·|vᵢₜ|/|targetₜ|` and `|vᵢₜ|/Σⱼ|vⱼₜ|`), **misc carriers explicit**. Report counts.
3. **Warm-start reselection**: initialize from the frozen 57,240 (NOT cold; NOT weight-proportional;
   NOT hard top-K — #346 fourth arm blows up at 0.330). Add protected records the frozen set lacks
   (chiefly high-leverage misc carriers); remove an equal count of the most-substitutable
   (lowest-leverage) NON-protected frozen records → stay at **57,240**. The weight solve rebalances
   the balanced portfolio (#346 point 3: protect dominant carriers of EACH target to preserve balance).
4. **De-risk** (fast, ~5 min direct-refit, no export): solve the candidate on the reduced frame; check
   misc export mass in-band + income tax / within-10% not regressed BEFORE the full release. Iterate
   (three-strike) on protect-list size.
5. **Sparse release** via the chunked path (single ~22-min process: ACA on full frame → reduce to new
   57,240 → cold solve → gates), --selection-source-manifest = the NEW manifest, 19-cell zero-support
   exclusions RECOMPUTED for the new selection.
6. **Gates**: full Build H protocol — structural + export-mass with ONLY the 2 reviewed exclusions
   (estate_income, non_sch_d_capital_gains, band-math-justified); misc + BOTH mortgage columns LIVE.
   Bar: meet/beat Build H frozen-57k diagnostics (final_loss 0.03092, within-10% 89.01%, income tax
   +0.45%) AND pass export-mass parity.

## Gate facts (verbatim from Build H input_mass_parity.json)
- enforced gate = `export_vs_base_frame`; reference `populace_us_2024.h5`; relative_tolerance 0.5;
  minimum_reference_total 1.0e9.
- misc reference mass = **4.74006e10** ($47.4006B) → band [2.37003e10, 7.11009e10]. Frozen export
  mass = **9.54992e9** (−79.9%, FAIL). Dense achieves −42.0% (in-band) on the identical target.
- reviewed_exclusions carry over unchanged (target-side, selection-independent): estate_income (ref
  ~2.1× SOI), non_sch_d_capital_gains (ref ~8× SOI). Verbatim justifications stored in Build H JSON.
- misc calibration TARGET ≠ misc EXPORT column: target measures = `irs_soi.ty2023.table_1_4.all.
  other_income_net_{income,loss}_amount` (net income $66.12B met; net loss $13.28B → final $38.64B);
  export column = raw `miscellaneous_income` INPUT (person-level), gated vs the reference h5.

## Manifest schema (certified_57k_selection_source.json, must reproduce for the NEW selection)
schema_version 1; join_key `["source_year","source_household_id","household_support_channel",
"household_support_clone_index"]`; source{kind,path,sha256 c2065b64,repo_id,revision}; n_selected;
identities_sha256 (recipe TBD from selection-seam mapping — my naive json.dumps did NOT match 77363a47);
identities = list of `[source_year:int, source_household_id:int, channel:str, clone:int]`.
Frozen field dist: source_year {2024:19749, 2023:19005, 2022:18486}; channel {asec:22187,
puf_tax_detail:35053}; clone {0↔asec, 1↔puf_tax_detail}.

## TIMELINE
### 2026-07-08
- **Step 0 (setup).** Read #359 (ratified design), #299 Build H verdict comment
  (`4914302628`), both #346 comments (design correction `4902880142` + learned-prior fourth-arm
  `4905374475`), PROGRESS_BUILDH.md, the learned_selection_prior experiment code (extract_core /
  direct_replay_learned_refit / build_selections), and the Build H shell scripts + release invocations.
  Created branch **build-i-run** @ b42fbfe and runtime `_buildi-runtime/{inputs,logs,out,checkpoints,
  scratch,src}`. Verified: Build H dense checkpoint identity registry **d71c59514e3a**, 5533 targets,
  337,704 households, all identity cols present, weights kind=calibrated. Located certified dense
  diagnostics + input_mass_parity (gate params above). Dispatched a code-exploration agent to map the
  #330 selection seam (manifest read/write, identities_sha256 recipe, `_select_households_by_position`,
  zero-support recompute, mass-repair / registry-recompile helpers).

- **Step 1 (core extracted; canonical bridge; misc structure).** Adapted extract_core to the Build H
  DENSE checkpoint (`experiments/build_i_reselection/src/extract_core_buildi.py`). **Strike 1**: first
  build hand-rolled identity tuples using the checkpoint `household_source_id` (household col) for the
  join field `source_household_id` (a PERSON col reduced "first" per household) → 37,632 unmapped. Fixed
  by building identities via the module's own `_base_household_key_frame` + `load_selection_source_from_
  manifest(...).base_selection_mask` (canonical, byte-identical to the release join). rc=0 (27s):
  registry d71c59514e3a, **A 5533×337704 nnz 17,784,800**, base frame order == checkpoint order,
  **manifest join n_unmapped=0 n_ambiguous=0 → 57,240 frozen positions == build-g forensic mask
  (overlap 57,240)**. Saved A/b/final_estimate + core_meta (base_weight, frozen_pos) + export_effval
  (5 gate cols, per household) + base_identities (canonical, for Step 5 manifest).
  **misc carrier structure (household-level, verbatim):** pool misc-nonzero **7,526** (pos 5,085 / neg
  2,441); frozen **1,957** (pos 1,167 / neg 790); addable-outside-frozen **5,569** (pos 3,918 / neg
  1,651). POSITIVE-misc base-weighted mass: pool **$21.32B**, frozen **$7.42B**, addable **$13.9B**
  (top-500 addable = $10.78B, top-1000 = $12.54B). Misc export must reach ≥$23.70B (band lower edge;
  ref $47.4006B ±50%); dense reaches $27.5B. → add the top-N positive-misc carriers frozen lacks, swap
  out low-leverage misc-zero frozen records, let the solve rebalance.

- **Step 2 (protect-list; `build_protect_list.py`).** Per-target leverage scan (`|v_it|/Σ_j|v_jt|`) +
  weighted contribution share. **P_structural = 4,122 records** (1.221% of pool) = union of each
  target's top-1 leverage carrier ∪ records with leverage≥0.5. Only **35/5533 targets have any ≥0.5
  carrier; 7 are near-sole (≥0.9)** — the pool is overwhelmingly DIFFUSE (substitutable carriers), so
  frozen certifies on all non-misc targets via substitutes even though 2,542 targets' GLOBAL top-1
  carrier sits outside frozen. Implication: force in ONLY the misc deficit; remove lowest-max-leverage
  misc-zero non-dominant frozen records; the diffuse portfolio self-heals under the solve. P_structural∩
  frozen = 1,580 (removal-protected). contrib_max max 15.5 (thin-tail carrier — the #346 case, protected).
  misc addable-positive cumulative base mass: N=500 $10.78B, 1000 $12.54B, 1500 $13.22B, 2000 $13.64B
  (frozen positive-misc base $7.42B; pool $21.32B → dense export $27.5B in-band).
