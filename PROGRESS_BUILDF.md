# Build F — certified-lineage rerun of the populace US release pipeline — PROGRESS

Task: PolicyEngine/populace #299 Build F. Rerun the EXACT Build E release recipe but on the
**certified 337k dense-support lineage** instead of the 224k experiment pool, on current main
(HEAD ed78097) with all of this week's merged hardening. Emit BOTH the dense-parent artifact
and the sparse L0+refit (~50-60k) headline product. STAGING ONLY — never touch prod HF / latest.json.

Worktree: /Users/maxghenis/PolicyEngine/_worktrees/populace-build-f (branch build-f off origin/main ed78097)
Runtime home (OUTSIDE repo): /Users/maxghenis/PolicyEngine/_buildf-runtime/  (inputs/ checkpoints/ logs/ parked/)
Gated outputs only, under worktree: out/base-f-*, out/release-f-*.

Guardrails: staging/local only. --no-staging on the release for unattended runs. NEVER touch
policyengine/populace-us prod repo, latest.json, or root files. Publication is NOT ours.

================================================================================
## PHASE 0 — CERTIFIED-LINEAGE RECIPE (reconstructed BEFORE building; no guessing)
================================================================================

### The core question answered: what is the certified 337k pool, and can we reproduce it on main?
**YES — reproducible on current main. The certified pool = a 3-YEAR ASEC pool (2024+2023+2022),
equal-thirds shares, mass anchored to target-year 2024, then a 2x PUF-tax-detail support clone.**

### Decisive evidence (shas + counts)

**1. The live default carries THREE source years + two support channels (frame-loader read).**
Live default `populace-us-2024-sparse-l0-refit-57k-71a0887-national-only-20260701`
(HF snapshot 14a2fb9d..., == current `main` ref 053baf6c..., 57,240 hh):
  person.source_year distribution: {2022: 54452, 2023: 54665, 2024: 57185}  <- THREE years
  person.support_channel: {asec: 65955, puf_tax_detail: 100347}             <- 2 channels (clone idx 0/1)
  household.support_channel: {asec: 22187, puf_tax_detail: 35053}
This is the POST-L0-selection artifact; source_year counts are survivors, not pool shares.

**2. Record-count arithmetic closes EXACTLY on a 3-year pool + 2x clone.**
Raw CPS ASEC households (policyengine-us-data storage census_cps_YYYY.h5):
  2024 = 55,762 hh ; 2023 = 56,251 hh ; 2022 = 56,839 hh
  3-year union = 168,852 hh  ->  x2 PUF support clone  =  337,704 hh
  == the "32,633 targets x 337,704 households" production calibration problem in #285.  EXACT MATCH.
Contrast (the WRONG pool): cd-concept experiment pool (HF 7c9ac04..., 224,026 hh) carries only
TWO source years {2023: 288530, 2024: 284250 persons}, 112,013 asec hh x2 = 224,026. This is the
B/D step-isolation base, NOT the certified lineage. Build E ran on THIS and failed (loss 0.125,
within-10% 48.4%, ESS 5,728). Build E's verdict was correct.

**3. Share vector = equal thirds (1/3 each). Not a guess — three convergent reasons:**
  (a) The committed 2-year spine (packages/populace-build/src/populace/build/us/support_spine.json,
      only commit b451bc7 "#221", never changed) declares current 2024 @0.5 + prior 2023 @0.5 —
      "each source contributes an equal share of the target-year population; mass anchored to 2024."
      The 3-year generalization preserving identical semantics is 1/3 / 1/3 / 1/3.
  (b) asec_pool.py `_resolved_shares` DEFAULTS to `1/len(sources)` when no shares are declared.
      So passing 3 `--asec-h5` mappings with NO explicit shares yields equal thirds by the code's
      own default — i.e., equal thirds IS the builder's canonical 3-year pool.
  (c) Shares only rescale WEIGHTS, not record counts (337,704 is share-invariant). And the release
      builder UNCONDITIONALLY rescales the whole base to the Census 2024 person benchmark 334.2M
      (base_population_scale.mass_repair, present in EVERY published manifest incl. f0af251 and the
      live default). So the pooled total is re-anchored regardless; equal thirds gives the least-
      opinionated, target-year-anchored starting-weight distribution.
Raw weighted person pops (per year, x0.01 ASEC scale): 2024=325.95M, 2023=320.89M, 2022=318.77M —
each ~ a full US population; equal thirds => each contributes ~108.6M pre-334.2M-rescale.

**4. No 3-year spine exists in the repo (any branch).** Scanned origin + all local branches
(codex/asec-*, codex/pooled-asec-*, rescue/*asec-pooling*, local-area-spine): every support_spine.json
is 2-year 0.5/0.5. The certified `runs/fixed-lambda-3asec-lam008-maincache-20260630` run config
(named in #285) was ad-hoc and never committed; its precalibration_frame.pkl is NOT on disk.
=> We reconstruct the 3-year pool by passing 3 `--asec-h5` years to the base builder (spec-less
   mode = equal thirds), which is exactly what the builder's default share logic produces.

**5. f0af251 is NOT the 337k pool.** The #299 phrase "337k dense support (f0af251)" is loose
shorthand for the certified LINEAGE tag. The published f0af251 artifact (HF d8f5cff...) is a
75,112-record, 4,582-target, June-20 intermediate (loss 0.042, l0_lambda 0, max_weight_ratio 5.0,
built_with policyengine-us 1.729.0) with its lineage columns stripped. It is an older derived file,
not the pre-selection pool. The certified reference band (loss ~0.044, within-10% ~94.7%) in the
Build F brief is the LIVE-DEFAULT 57,240 quality, reached by L0+refit on the 337,704 3-year pool.

### CERTIFIED BASE RECIPE (to reproduce on main)
- Pool: 3-year raw CPS ASEC, target year 2024:
    2024 = census_cps_2024.h5 (offset 0), 2023 = census_cps_2023.h5 (offset -1), 2022 = census_cps_2022.h5 (offset -2)
    shares: equal thirds (spec-less: builder default 1/len). Mass anchored to 2024.
  Raw sources (policyengine-us-data storage, Census colnames PH_SEQ/HSUP_WGT/PRCITSHP/SPM_CHILDCAREXPNS):
    ~/PolicyEngine/policyengine-us-data/policyengine_us_data/storage/census_cps_2024.h5 (142,125 persons / 55,762 hh)
    ~/PolicyEngine/policyengine-us-data/policyengine_us_data/storage/census_cps_2023.h5 (144,265 persons / 56,251 hh)
    ~/PolicyEngine/policyengine-us-data/policyengine_us_data/storage/census_cps_2022.h5 (146,133 persons / 56,839 hh)
- Then in ONE run of build_us_puf_support_base.py (asec-mode, current main):
    carry (#278 childcare leaf) -> immigration (PRCITSHP #266) -> 2x PUF-tax-detail support clone
    -> PUF QRF impute (IRA/HSA/pension #278 leaves) + weights_audit (#308) -> CD assign (119th vintage)
    -> block-ladder + geography_ladder gate.
  PUF donor: ~/PolicyEngine/policyengine-us-data/policyengine_us_data/storage/puf_2024.h5 (211,677 rows).
  seed 0, n_estimators 32 (builder defaults). target-year 2024.
- Expected base: 168,852 pool hh -> 337,704 post-clone hh, all 4 #278 leaves present with mass.

### FEED (target surface) — REUSE Build E v5 (pool-independent target facts)
/Users/maxghenis/PolicyEngine/_builde-runtime/inputs/consumer_facts_builde_aging_v5.jsonl
  37,098 rows, sha256 a5d34d4aad325d8c79c45ea4944c7eec3a4e51e30a9997c3efa1da4571976816
  = curated 37,053-fact SELECTED surface + 24 CBO income_by_source (ty2023-26) + 21 national SOI
    table-1.1/1.4 actuals, deduped on lineage.source_record_id.
  Justification: fiscal targets are national/state/CD aggregates, INDEPENDENT of which base pool
  expresses them. Build E proved the full multi-year splice (160k) OVER-BINDS (curated feed is a
  SELECTED surface). v5 is the correct hybrid curated+aging feed. Copy to _buildf-runtime/inputs/,
  re-verify sha + aging pair (CBO 2024 & 2023 present) + dedup before use.
  Period contract needs the CBO series + national SOI 1.1/1.4 chain rows — v5 has them (#287 chain).

### RELEASE RECIPE (build_us_fiscal_refresh_release.py, current main)
Default path = SPARSE L0+refit (this is ALREADY the headline product). Emits sparse
populace_us_2024.h5. `--dense-default-dataset` flips to dense no-L0 (diagnostic parent).
Key defaults: max_weight_ratio 5.0, l0_refit_lambda_share 0.8, l2_lambda default, refit_l2_lambda
= l2_lambda unless overridden, learning_rate 0.02, epochs 1500+1500 (L0 select then refit).
Gates wired (all UNCONDITIONAL/blocking): parity_gate (ratchet vs pinned incumbent #316),
input_mass_parity_gate, default_valued_columns_gate (#286 degenerate + reviewed exclusion register),
us_validation_input_coverage_gate (#278/#279 untargeted-input zeroing — SystemExit on fail),
us_immigration_composition_gate, us_take_up_participation_diagnostics + us_take_up_signal_gate (#312),
weights audit (#308), calibration diagnostics (loss / within-10% / ESS).

### L0 max-weight-ratio decision (per brief: try default before reaching for 50)
Certified pool is HEALTHIER (337,704 vs 224,026 => 1.5x more support). f0af251 ran at ratio 5.0.
=> FIRST attempt: default max_weight_ratio 5.0 (the certified/f0af251 value). Only if L0 selection
is mass-infeasible at 5.0 on this pool do we fall back to Build E's --max-weight-ratio 50 and
DOCUMENT it (do not iterate). Record realized max ratio in the gate table either way.

### CACHE KEY components (record all — brief requirement)
base_dataset_sha256 (from base-f summary) + reform vector + policyengine_us_version + target_period(2024)
+ CD-crosswalk sha. Checkpoint root = /Users/maxghenis/PolicyEngine/_buildf-runtime/checkpoints/build-f
(OUTSIDE repo — in-repo checkpoints re-dirty the tree and block #317 resume).

### Reused vs rebuilt vs replaced (summary)
- REUSE: v5 aging feed (target surface, pool-independent); CD vintage crosswalk (#205, from build-e-base);
  block-ladder NPZ (geography, pool-independent) if still on disk; asec_pool machinery (on main via #221/#134).
- REBUILD: the BASE POOL — 3-year ASEC (2024+2023+2022) instead of Build E's 2-year (2024+2023).
  This is THE change that makes Build F certified-lineage.
- REPLACE: nothing E-specific carried blindly; base built fresh from raw ASEC on current main.

### Known-correct guard behaviors to SATISFY (not fight)
- clone-guard: refuses published artifacts as raw base -> build base from raw ASEC (asec-mode). OK.
- period contract: needs CBO + national SOI 1.1/1.4 chain rows -> v5 has them. OK.
- reference-ambiguity dedup: on lineage.source_record_id (arch->ledger rename = same record_id). v5 deduped. OK.
- full-splice over-binds -> use hybrid curated+aging (v5), NOT 160k splice. OK.
- SOCA package: park for local ledger runs if ledger involved (mv aside/restore). v5 already built,
  so no ledger run needed for the feed; monitor.

================================================================================
## TIMELINE (append every step)
================================================================================

### 2026-07-05 ~18:40 ET — Phase 0 COMPLETE, worktree + env set up
- Read #299 (Build E outcome + Build F rec), #285 (production lineage: 32,633 x 337,704, 3asec),
  #309 (refit_l2_anchor design/uniform/initial semantics), Build E PROGRESS.md + chain script.
- Reconstructed certified recipe (above). Verdict: reproducible on main, NO guessing. Not blocked.
- Worktree build-f created off origin/main ed78097. Runtime dir _buildf-runtime/ mirrored.
- `uv sync --all-packages --extra us` launched detached (log logs/uv_sync.log, pid uv_sync.pid).

### NEXT (planned)
1. Verify env: .venv imports populace.build + policyengine_us + tables + torch.
2. Locate/confirm block-ladder NPZ + CD crosswalk on disk (reuse; rebuild only if missing).
3. Copy v5 feed to _buildf-runtime/inputs/, re-verify sha + aging pair + dedup.
4. Launch base rebuild DETACHED (asec-mode, 3 years) -> out/base-f-YYYYMMDD/. Verify summary gates.
5. Launch release DETACHED (checkpoint-root outside repo, --no-staging): dense parent + sparse L0+refit.
6. Extract BOTH gate tables + calibration metrics vs certified reference. Verdict.

### 2026-07-05 ~19:05 ET — steps 1–5 EXECUTED BY LEAD during agent session-limit outage
- Env verified (imports OK incl. torch). v5 feed copied to _buildf-runtime/inputs, sha VERIFIED
  (a5d34d4a...). CD crosswalk + provenance + us_block_ladder_2020.npz copied from build-e-base.
- build_f_chain.sh written (mirrors build_e_chain.sh) and launched DETACHED (nohup, pid in
  logs/chain.pid): base (3x --asec-h5 spec-less = equal thirds, --ledger-facts for CD assign,
  crosswalk + block-ladder passed) -> release SPARSE (default path, headline) -> release DENSE
  (--dense-default-dataset, same checkpoint-root so compile reuses).
- Logs: _buildf-runtime/logs/{chain.log, base_f.log, release_f_sparse.log, release_f_dense.log}.
- AGENT RESUME BRIEF: check chain.log; if chain still running, WAIT on it (do not relaunch);
  when done, execute step 6 (extract BOTH gate tables + calibration metrics vs certified
  reference loss ~0.044 / within-10% ~94.7%; realized max-weight-ratio; cache-key components)
  and write the verdict. If base failed, read base_f.log — likely suspects: spec-less 3-year
  shares behavior, --ledger-facts CD fact coverage through the crosswalk, block-ladder gate.

### 2026-07-06 ~00:10 ET — AGENT RESUMED as monitor for attempt 3 (do NOT relaunch while running)
Verified the lead's overnight state independently before waiting on the chain:

**BASE (out/base-f-20260705, sha 18833fb6...) — CERTIFIED LINEAGE CONFIRMED via frame loader:**
- H5 household rows = 337,704 (NOT the summary's 168,852 — that field is the PRE-CLONE pool count).
- household_support_channel: asec 168,852 / puf_tax_detail 168,852 (perfect 50/50 clone).
- person.source_year: 2024=284,250 / 2023=288,530 / 2022=292,266 (the 3-year pool). EXACT match to
  #285 production dimensions.
- All 4 #278 leaves present with mass: traditional_ira_contributions_desired (person, nz 8,141),
  self_employed_pension_contributions_desired (person, nz 1,924), health_savings_account_ald
  (TAX_UNIT, nz 2,802, $13.8M — lives on tax_unit not person), spm_unit_pre_subsidy_childcare_expenses
  (spm_unit, nz 21,552, $202.6M).
- summary gates: weights_audit.passed=True, geography_ladder.gate.passed=True.

**FAILURE MODES (attempts 1-2) confirmed from logs + attempt-2 dense diagnostics:**
- DENSE attempt-2 diagnostics (v6-less): final_loss 0.04295, within-10% 85.8%, and EVERY structural
  gate PASSES (target_profile_coverage, health_input_signal, degenerate_input_signal (#286),
  base_population_scale, immigration_composition, ecps_parity (#316), validation_input_coverage
  (#278/#279)). The ONLY release_gates failure = "20 positive fiscal targets have zero materialized
  support" — all 20 are cms_medicaid ...total_chip_enrollment (M-CHIP states incl CA). v6 removes
  exactly these 20 rows (verified: v5 37,098 -> v6 37,078; the 20 removed are all CHIP; v6 sha
  9f8edbb9... matches).
- SPARSE attempt-2: L0 pruned to 54,093 survivors; mass='conserve' infeasible at max_weight_ratio 5.0
  (the L0 selection starves at the tight ratio). Fix = --max-weight-ratio 50 (my Phase-0 pre-registered
  fallback; the certified/f0af251 default is 5.0 but Build E also needed 50 at this pool scale).

**CERTIFIED REFERENCE BARS pinned (for the verdict):**
- SPARSE headline: live default `sparse-l0-refit-57k` default_dataset.final_loss = 0.04401 (~0.044),
  within-10% ~94.7% (brief). That is a 1,500-epoch dense POLISH of a FROZEN 57,240 support.
- DENSE parent: f0af251 (75,112) final_loss 0.0423, within-10% 86.4% — build-f dense 0.04295/85.8%
  already matches this almost exactly (on a fuller 337,704 pool -> stronger support).
- eCPS parity: pinned per-variable nonzero-share ref from incumbent enhanced_cps_2024.h5 (ratchet;
  computed once, never recomputed).

**CACHE-KEY components recorded:** base_dataset_sha256=18833fb6... ; reform vector = US_JCT_TAX_
EXPENDITURE_REFORMS / default reform specs (unchanged on main); policyengine_us 1.752.2 ;
target_period 2024 ; CD-crosswalk sha (from #205 provenance) ; feed v6 sha 9f8edbb9...

**DEVIATIONS from the pure certified recipe (to flag prominently in the report):**
1. Feed = v6 (v5 minus the 20 M-CHIP total_chip_enrollment rows). Reason: target-concept mismatch —
   CMS total_chip_enrollment = M-CHIP+S-CHIP; the model materializes separate-CHIP only, so those 20
   are structurally un-materializable (issue #170's class). This is a reason'd degenerate-target
   exclusion, not a quality shortcut. (Follow-up: proper fix is an M-CHIP support/expansion, or split
   the CMS target into M-CHIP vs S-CHIP components.)
2. SPARSE max_weight_ratio 50 (not the certified 5.0). Reason: L0 mass='conserve' infeasibility at 5.0
   on this pool. Pre-registered fallback; documented, NOT iterated. Realized ratio to be read from
   attempt-3 sparse diagnostics.

Extractor staged: /private/tmp/.../scratchpad/extract_gates.py (both gate tables + calib-vs-cert).
Monitor armed on chain.log terminal states. WAITING on attempt 3 (sparse calibration long pole).

### 2026-07-06 ~00:30 ET — validated the v6 CHIP fix is sound (attempt 3 should clear dense degenerate gate)
Traced the degenerate-target mechanism to confirm v6 actually removes the failing targets (not just
masks feed rows that would re-derive):
- The 20 failing targets = cms_medicaid ...total_chip_enrollment @2024-12 for exactly the 20 M-CHIP
  states (ak,ca,dc,hi,il,ky,md,me,mi,mn,nc,nd,ne,nh,nm,oh,ok,sc,vt,wy). These run CHIP as Medicaid
  expansion => "CHIP enrollment" is counted inside Medicaid; the model materializes SEPARATE-CHIP only
  => zero support. Correct #170-class diagnosis.
- CRITICAL check: fiscal_targets._with_derived_chip_enrollment_targets DERIVES total_chip_enrollment
  from (total_medicaid_chip_enrollment MINUS medicaid_enrollment). If that re-fired, removing feed rows
  wouldn't help. It does NOT: the derivation keys on target_role=='medicaid_enrollment', but the feed
  carries 'total_medicaid_enrollment' (0 rows match 'medicaid_enrollment') => the derivation loop finds
  an empty medicaid dict and appends nothing. So the 20 direct feed rows are the ONLY source of those
  targets; removing them removes them for good.
- v6 keeps 32 S-CHIP states @2024-12 (al,ar,az,co,ct,de,fl,ga,...) which DID materialize (the original
  failure named exactly 20, not 52). So v6 = 20 M-CHIP removed + 32 S-CHIP kept = 52 states, internally
  consistent. Dense should now pass the degenerate-target gate.

### CACHE-KEY (final, for report)
- base_dataset_sha256: 18833fb68e60ee74461608d81a5c5ab7d52435e17026d9e3b062d9de18d6871f
- policyengine_us_version: 1.752.2 ; policyengine_core: 3.26.11
- target_period: 2024 ; seed: 0
- congressional_district_vintage_crosswalk_sha256: 383a666631aafd4f584816935ae340960fb3fc127929dccf61d223790a82140b
- feed v6 sha256: 9f8edbb90c8a86705aa0dbe2ec0ce7c8347a59f9d068f315f58d5aaeaecfd90d (37,078 rows)
- reform vector: default US_JCT_TAX_EXPENDITURE_REFORMS / load_default_reform_specs (unchanged on main)
- NOTE: target-frame checkpoint identity is feed-INDEPENDENT by design (base sim values don't depend on
  which facts you calibrate toward); the feed only sets the target registry. v6-vs-v5 does not require
  recompiling the target FRAME, only re-running calibration against the trimmed registry.

Attempt 3 RUNNING (03:45:20Z start; sparse in target compilation as of 00:30 ET). Monitor armed.
