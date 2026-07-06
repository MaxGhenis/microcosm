# Build G — pin-bump validation pass (pe-us 1.752.2 → 1.764.x) — PROGRESS

Task: PolicyEngine/populace **#324** (Build G opener). Quantify pe-us model drift across the
Build F release window (1.752.2 → 1.764.0, 28 releases) BEFORE Build G commits to a pin.
**Validation-only pass. No build runs, no register commits, no pushes to main.**

Worktree: `/Users/maxghenis/PolicyEngine/_worktrees/populace-build-g` (branch `build-g` off `origin/main`).
Runtime home (OUTSIDE repo): `/Users/maxghenis/PolicyEngine/_buildg-runtime/` (inputs/ logs/ checkpoints/ venvs/ out/ parked/).
All long compute detached (nohup + pidfile + log). PROGRESS committed every step.

## Fixed inputs (verified, do NOT rebuild)
- **Base F artifact** (REUSE): `~/PolicyEngine/_worktrees/populace-build-f/out/base-f-20260705/base_populace_us_2024_puf_support.h5`
  - sha256 `18833fb68e60ee74461608d81a5c5ab7d52435e17026d9e3b062d9de18d6871f` — **VERIFIED** matches required `18833fb6…`.
  - 3-year ASEC pool (2024+2023+2022 equal thirds) → 2× PUF clone = 168,852 hh (person 432,523; tax_unit 231,007). base weight total 134.69M (pre-334.2M release rescale).
  - All four #278 leaves present with mass.
- **Incumbent pin (Build F / uv.lock)** = policyengine-us **1.752.2**, core 3.26.11.
- **New pin**: `>=1.745.0,<2` resolves upward. PyPI latest at run time = **1.765.3**. Issue names the window ceiling as **1.764.0**.
  - DECISION: record the natural resolution (build-g worktree sync), AND build a dedicated **1.764.0** venv so the critical-fit drift is measured over exactly the issue's named window (1.752.2 → 1.764.0). If natural resolution is 1.765.x, report both and note 1.765 delta separately.

## The four validation tasks (#324)
1. **eCPS parity gate (ratchet mode)** at the new pin vs pinned incumbent reference
   (`packages/populace-build/src/populace/build/us/ecps_parity_reference.json`, 158 vars, pinned to incumbent
   eCPS sha `0a6b961a…`). Expected legit deltas: state income tax for ME/NE/ND/NY/OH/RI from 1.756.9
   uprating-placement fix (33 frozen param files now uprate) + 1.756.8 explicit 2026 values.
   Deliverable: per-variable delta table (variable, old est, new est, delta, attributable-release+changelog cite,
   PROPOSED register disposition). **Proposals only — lead gates them, no register commits.**
2. **Take-up contract assertion** (#315 engine-asserted contract, `us/take_up_contract.json` +
   `us_runtime/take_up_contract.py`): run take-up contract tests at new pin; confirm no model-side seeding
   appeared for data-seeded flags and defaults didn't shift semantics. Pass/fail per flag (13 flags, all
   data_seeded at 1.752.2).
3. **Critical-fit spot checks**: compute federal income tax liability (amount/returns), taxable SS
   (amount/returns), EITC amount, ACTC claims on the base at BOTH pins (two small venvs). Pure model drift
   BEFORE calibration.
4. **New-input inventory**: scan 1.753–1.764 changelogs for anything touching populace's input surface
   beyond the known SNAP/ABAWD wave. New person-level inputs consuming engine defaults = future
   degenerate-gate candidates.

## Deliverable
Triage report → committed to this file + posted as ONE comment on populace#324: drift tables, per-delta
attributions, register-entry proposals, take-up verdict, new-input inventory, go/no-go for pinning 1.764.x.

## Steps
- [x] 0. Read #324, #299 (Build E/F campaign comments), #315/#316/#317. Set up worktree, verify base sha, mirror runtime layout.
- [x] 1. Env: `uv sync --all-packages --extra us` (build-g). **RESOLVED pe-us = 1.752.2** (uv.lock honored; sync does NOT bump the pin — that requires `uv lock --upgrade`). Built dedicated venvs `venv-1752` + `venv-1764`, BOTH pinned to **core 3.26.11** (match Build F env) so critical-fit isolates pure pe-us drift. New-pin CEILING under `<2` = **1.765.3** (PyPI latest); issue names 1.764.0 as the window; both reported.
- [x] 2. Fetched + parsed pe-us CHANGELOG 1.752.3→1.765.3 (scratchpad/peus_changelog.md, lines 1-418). Attribution map built (see Log). Confirmed 1.756.9 uprating-placement fix (33 files / 107 nodes ME,NE,ND,NY,OH,RI) + 1.756.8 explicit 2026 values + 1.764.1 NY IT-196 phase-out wiring.
- [x] 3. Task 1 — eCPS parity. **RESULT: parity gate is PIN-INVARIANT on the frozen base.** Ran the actual gate at BOTH pins. Both report the SAME 2 unexempted gaps (`selected_marketplace_plan_benchmark_ratio` ref 100%/cand 0%; `takes_up_aca_if_eligible` ref 67.1%/cand 0%) — pre-existing base-vs-reference gaps (base-F is the raw pre-ACA-stage base; the release ACA stage populates these before the gate, which is why Build F's release passed). **The pin bump introduces ZERO new parity gaps.** The state-income-tax "movement" #324 predicts lives entirely in COMPUTED OUTPUTS (state_income_tax is not an engine input) → measured in task 3, not the input-column gate. Artifacts: out/parity_scope_1752.json, out/parity_scope_1764.json.
- [x] 4. Task 2 — take-up contract. **VERDICT: PASS, all 13 flags @ 1.764.0.** 14/14 contract tests pass. Per-flag: 13 flags present (no add/remove), ALL still `data_seeded` (default=True, no formula) — ZERO migrated to model_simulated; every asserted engine fact (entity/value_type/default/engine_class) matches the checked-in contract field-by-field. No model-side seeding appeared; no default-semantics shift. Log: logs/takeup_contract_1764.log.
- [~] 5. Task 3 — critical-fit at 1.752.2 & 1.764.0 on base-F. **METHOD NOTE:** the full 337,704-hh Microsimulation is dominated by pe-us per-household `numpy.random.seed` (stochastic take-up/imputation) — ~7min PER aggregation, confirmed via `sample`. Reworked to a **deterministic 40,000-hh subsample** (`Microsimulation.subsample(n=40000, seed=42, quantize_weights=True)`): identical households drawn at BOTH pins (fixed seed) so the between-pin delta carries ZERO sampling noise, and quantize_weights keeps aggregate totals unbiased (full-base scale). Percentage drift is scale-stable. Timing test: full sim + subsample + income_tax + ss + eitc in ~99s (vs 7min+ for income_tax alone on full base). Sanity: income_tax ≈ $2.00T, taxable_ss ≈ $0.467T, eitc ≈ $30.8B on the uncalibrated 2024 base (consistent with Build F's pre-calibration undershoot). Chain DETACHED (run_critical_fit.sh). Awaiting probe_1752.json + probe_1764.json.
- [x] 6. Task 4 — new-input inventory. **engine inputs 841 → 863 (+24 added, −2 removed).** ALL 24 added default to 0/False and base-F populates NONE (all cand_share=0) → all consume engine defaults. Classified below. Removed 2 (`small_area_fair_market_rent`, `safmr_used_for_hcv`) = stubbed→parameterized (1.754.0), not a loss.
- [ ] 7. Assemble triage report → this file + populace#324 comment. Go/no-go.

## Task 3 — critical-fit RESULTS (40k subsample, both pins, core 3.26.11 fixed)
FEDERAL (both pins complete, rc=0):
| target | 1.752.2 | 1.764.0 | delta% |
|---|---|---|---|
| Federal income tax — amount | $2,000.25B | $2,004.04B | **+0.190%** |
| Federal income tax — returns | 122.20M | 122.19M | −0.008% |
| Taxable Social Security — amount | $466.94B | $467.46B | **+0.110%** |
| Taxable Social Security — returns | 28.069M | 28.079M | +0.036% |
| EITC — amount | $30.822B | $30.808B | **−0.045%** |
| EITC — returns | 13.549M | 13.546M | −0.025% |
| Refundable CTC (ACTC) — amount | $21.614B | $21.619B | +0.025% |
| ACTC — claims | 10.431M | 10.431M | 0.000% |
**All federal aggregates move < 0.2% — negligible, well-behaved drift.** The +0.19% fed income tax is consistent with the 1.756.x federal base changes (non-Sch-D cap-gain-distribution inclusion, OBBBA clean-energy termination, saver's credit thresholds) roughly offsetting. Supporting: AGI $15.22T, employment income $11.27T, capital gains $231.7B, SNAP $74.7B, TANF $13.5B (all near-identical between pins).
- [x] 5. Task 3 DONE (federal + state).
- [x] 7. Triage report assembled + posted to #324.

STATE income tax by state (fixed via standalone probe_state_tax.py — household-level aggregation; 40k subsample, seed 42):
| state | 1.752.2 | 1.764.0 | delta% | attribution |
|---|---|---|---|---|
| ME | $2.698B | $2.713B | +0.55% | 1.756.9 uprating unfreeze (12 files) |
| NE | $2.826B | $2.827B | +0.04% | 1.756.8 explicit 2026 + 1.756.9 |
| ND | $0.213B | $0.214B | +0.34% | 1.756.9 uprating unfreeze (5 files) |
| **NY** | **$43.56B** | **$55.98B** | **+28.51%** | **1.764.1 IT-196 §68 overall-limitation wiring (+1.756.8 phase-out unfreeze)** |
| OH | $11.14B | $11.16B | +0.15% | 1.756.9 uprating unfreeze (1 file) |
| RI | $2.476B | $2.477B | +0.03% | 1.756.8/1.756.9 |
| ALL states | $468.14B | $490.41B | +4.76% | NY dominates |
**THE headline drift: NY +28.5% (+$12.4B).** NOT the modest uprating effect — traced to **1.764.1** ("wired NY's orphaned itemized-deduction phase-out into IT-196 Line 40 pre-TCJA overall limitation, 26 USC 68 via NY Tax Law 615"). CONFIRMED on-disk: `ny/.../itemized/phase_out/start.yaml` param changed AND NY itemized-deduction variable `.py` sources changed (ny_salt_deduction.py, pre_tcja/*). Directionally correct (NY was omitting the §68 overall limitation → under-taxing high-deduction filers); reduces NY itemized deductions → raises NY taxable income → +28.5% NY tax. Large but LEGITIMATE. The other 5 states = the expected small uprating-unfreeze moves #324 predicted. Federal essentially flat (<0.2%). Full table: out/drift_table.md.

## Task 1 — register-entry PROPOSALS (lead-gated, NOT committed). Full text: `_buildg-runtime/out/register_proposals.md`
- **No pin-attributable register entries.** The bump adds zero parity gaps (base frozen; new engine inputs not in the 158-var reference).
- **Surfaced (pre-existing, not pin-induced): 2 unexempted ACA-family gaps** the raw base fails at BOTH pins: `takes_up_aca_if_eligible` (ref 67.1%/cand 0%, NOT in register) + `selected_marketplace_plan_benchmark_ratio` (ref 100%/cand 0%, NOT in register). Root: both are populated by the native ACA source stage (`source_stages.json`, #76/#168) which runs BEFORE the parity gate in the RELEASE — so Build F's release passed while the RAW base does not carry them. The other 10 seed-class take-up flags DO carry #312 register entries; ACA was scoped out of take-up seeding and never given a parity exemption. Proposed reason'd exemptions drafted (issue #76). Alternative: measure candidate on the post-ACA-stage frame instead of the raw base. Lead decides.
- Register today = 110 entries (dict-keyed): #38×42, #298×16, #32×15, #312×13, #49×8, #253×7, #242×5, #274×4.

## Task 1/3 mechanistic cross-check — the 1.756.9 uprating fix IS real on-disk
Diffed the ME/NE/ND/NY/OH/RI income-tax param TREES between the two installed pins (venv-1752 vs venv-1764):
income-tax param FILES changed: **ME 12, NE 5, ND 5, NY 1, OH 1, RI 6 = 30 files** (the rest of the changelog's "33 files/107 nodes" = RI/NY contrib reforms). Concrete diff (ME pension-exclusion phaseout start.yaml) shows EXACTLY the fix: `uprating:` moved from sibling-of-`values:` (loader ignored → FROZEN) to under `metadata:` (loader honors → uprates via gov.irs.uprating). ME MAIN brackets (single/joint/hoh/separate/surviving_spouse) all differ too → ME income tax moves for a broad filer set at post-freeze years. Direction: unfreezing uprating widens brackets / raises exclusions at 2024+ → generally LOWERS state income tax where inflation had been frozen out. This CONFIRMS the #324-predicted legitimate deltas are real correctness improvements; §3 critical-fit quantifies the aggregate. Saved: out/state_tax_param_diffs.txt.

## Task 4 — new-input inventory (degenerate-gate candidates), classified
24 new engine INPUT variables at 1.764.0 (all default False/0, none carried by base-F):
- **SNAP/ABAWD wave (6, KNOWN — #248/#249/#250 already flagged in #324):** `is_snap_abawd_discretionary_exempt` (person), `is_snap_workfare_participant` (person), `weekly_snap_work_program_hours` (person, float), `has_applied_for_unemployment_compensation` (person), `is_complying_with_tanf_work_requirements` (person), `is_in_substance_use_treatment_program` (person). Releases 1.758.0/1.762.0/1.764.0.
- **State childcare CCAP/CCDP enrollment (13, NEW beyond SNAP wave):** ND — `is_nd_ccap_enrolled`(spm_unit), `nd_ccap_provider_qris_step`(person,enum), `nd_ccap_provider_type`(person,enum); MT — `mt_ccap_enrolled`(spm_unit), `mt_ccap_care_time`(person,enum), `mt_ccap_provider_type`(person,enum); NM — `nm_ccap_enrolled`(spm_unit), `nm_ccap_focus_level`(person,enum), `nm_ccap_non_traditional_hours`(person,float), `nm_ccap_provider_type`(person,enum); NV — `nv_ccdp_enrolled`(spm_unit), `nv_ccdp_provider_star_rating`(person,enum), `nv_ccdp_provider_type`(person,enum). Releases 1.756.0/1.761.0/1.762.0/1.763.0. **Low fiscal-drift risk (state childcare subsidy, opt-in enrollment default False → programs simply don't fire); but they ARE new person/spm-level inputs consuming defaults → degenerate-gate candidates if populace ever targets these programs.**
- **Local income tax (4, NEW beyond SNAP wave):** `in_yonkers`(household,bool), `ny_yonkers_nonresident_earnings`(person,float), `in_wilmington`(household,bool), `de_wilmington_nonresident_earnings`(person,float). Release 1.757.0.
- **Capital gains (1, NEW):** `schedule_d_capital_gain_distributions`(person,float). Release 1.756.0. (Sibling `capital_gain_distributions` is ALSO a person-level input but pre-existed 1.752.2 — not new.) **This one flows into the income-tax base → the one new input with fiscal-drift potential; but base carries 0 at both pins so it is a definitional-consistency item, not a between-pin mover on this base.**

## Attribution map (pe-us 1.752.3 → 1.765.3), for tasks 1 & 4
State income tax / parity-relevant:
- **1.756.8** — explicit 2026 values added to NE, ME, RI income tax params; 2024-25 values to NY itemized-deduction phase-out threshold (unfroze via #8905).
- **1.756.9** — moved `uprating:` from sibling-of-`values:` to `metadata:` across **33 param files / 107 nodes**: ME, NE, ND, NY, OH, RI state income tax + RI & NY contrib reforms. Loader had silently ignored them → thresholds/amounts frozen at last explicit value. Adds `test_uprating_placement.py` guard. **← the #324-predicted fix.**
- **1.764.1** — wired NY orphaned itemized-deduction phase-out into IT-196 Line 40 (26 USC 68 overall limitation via NY Tax Law 615) — reduces NY itemized deductions.
- **1.765.2** — CO income tax (199A addback, 2026 fed-deduction-addback exemptions, 2026 CDCC, low-income childcare sunset) [only if pin goes to 1.765.x].
- **1.765.1** — PA retirement-plan distribution exemption + NJ 529 deduction relocation [1.765.x only].
- **1.765.3** — CA AMT itemized double-add fix, AZ property tax credit, LA FITAP / NV TANF rounding [1.765.x only].
Capital-gains / income base (affects income tax + critical-fit):
- **1.756.2** — non-Schedule-D capital gain distributions included in gross income, preferential-rate cap-gains base, and NII.
- **1.756.0** — new inputs `schedule_d_capital_gain_distributions` + `capital_gain_distributions`.
- **1.756.6** — Saver's Credit 2024/25/26 joint AGI thresholds; 2020 UC exclusion AGI fix.
- **1.756.7** — residential clean energy / EE home improvement / clean vehicle credits terminated under OBBBA (Pub. L. 119-21).
OBBBA / federal:
- **1.756.7** clean-energy termination (above); **1.756.1/1.756.4** disabled-adult-dependent CTC/EITC child-count fixes.
SNAP/ABAWD input WAVE (known, task-4 baseline): 1.758.0 (discretionary-exemption PERSON-LEVEL input), 1.760.0 (state-coverage doc), 1.761.0 (former-foster-youth exemption + IHCIA Indian exemption input), 1.762.0 (work-program hours + workfare), 1.763.0 (Alaska borough waivers by county FIPS), 1.764.0 (work-registration exemption hooks: TANF-compliance, drug/alcohol treatment, UC applicants).
NEW inputs BEYOND SNAP wave (task-4 degenerate-gate candidates): `care_expenses` (1.752.3), `capital_gain_distributions` + `schedule_d_capital_gain_distributions` (1.756.0), `employment_income_before_lsr` migration (1.764.3 — 156 fixtures moved off derived `employment_income`; **flag if populace seeds employment_income**), `state_code_str` backfill (1.756.5), `county_fips`→county mapping (1.755.5).

## Log
- **2026-07-06T~1005Z start.** Read #324 + #299 (all 6 comments: Build E terminal result, Build F 5-attempt campaign + attempt-6 pre-flight/close) + #315 (take-up contract) + #316 (parity gate wiring) + #317 (compile survivability). Build F verdict: not certifiable; dense parent one mis-referenced gate from clean (#327), sparse blocked on uncommitted informed-L0 (#328); reusable asset = base `18833fb6`.
- Worktree `build-g` created off origin/main HEAD `e179ba5` (#319 state-legislative validation suite; 3 commits ahead of the ed78097 Build F HEAD). Clean.
- Base-F sha VERIFIED `18833fb6…`. Runtime `_buildg-runtime/` created mirroring `_buildf-runtime` layout.
- pe-us pin `>=1.745.0,<2` (all three `[us]` extras); uv.lock incumbent = 1.752.2; PyPI latest = 1.765.3.
- Parity reference read: 158 vars, incumbent eCPS sha `0a6b961a…` rev `21280dca…`.
- Launched detached `uv sync --all-packages --extra us` (build-g). Writing PROGRESS + committing.

---

# FINAL TRIAGE REPORT (posted to #324)

## Build G opener — pin-bump validation pass (pe-us 1.752.2 → 1.764.0)

Validation-only pass per this issue. **No build runs, no register commits, no pushes to `main`.** All compute detached; the battery ran against the **reused** Build F base artifact `base-f-20260705/base_populace_us_2024_puf_support.h5` (sha `18833fb6…`, **verified before use**; 3-year ASEC pool → 2× PUF clone = **337,704 hh**). Worktree `build-g` off `origin/main` (HEAD `e179ba5`, which includes #319); runtime scratch in `~/PolicyEngine/_buildg-runtime/`.

### Resolved versions
- **Incumbent pin (Build F / `uv.lock`):** policyengine-us **1.752.2**, core 3.26.11.
- **`uv sync --all-packages --extra us` resolves to 1.752.2** — the lock is honored; `uv sync` alone does **not** move the pin (that needs `uv lock --upgrade`). The pin *spec* is `>=1.745.0,<2`.
- **New-pin candidate: 1.764.0** (this issue's named window ceiling). The spec's live ceiling under `<2` is **1.765.3** (current PyPI latest) — 28 releases shipped in the window; battery targets 1.764.0, 1.765.x-only changes listed separately.
- Critical-fit run in two isolated venvs, **both pinned to core 3.26.11**, so the only moving part is policyengine-us (clean single-variable drift).

---

### 1. eCPS parity gate (ratchet mode) — **PIN-INVARIANT; zero new gaps from the bump**

The gate compares **input-column** nonzero shares of the (frozen) base against the frozen 158-var incumbent-eCPS reference. Because the base H5 is frozen, candidate shares are pin-invariant; the only pin-sensitive input is the engine input-variable **scope** (841 → 863 vars). None of the 24 new engine inputs are in the frozen reference, so none can create a parity failure.

**Confirmed empirically — ran the actual `parity_gate` at BOTH pins; identical result:**

| | 1.752.2 | 1.764.0 |
|---|---|---|
| reference-populated layers | 158 | 158 |
| register exemptions | 110 | 110 |
| **unexempted gaps** | **2** | **2** (same two) |

The 2 unexempted gaps are **pre-existing, not pin-induced** — both ACA-family, both populated by the native ACA source stage (`source_stages.json`, #76/#168) which runs *before* the parity gate in the **release**, so Build F's release passed while the **raw base** does not carry them:

| layer | ref share | candidate | in register? |
|---|---:|---:|---|
| `takes_up_aca_if_eligible` | 67.1% | 0% | no |
| `selected_marketplace_plan_benchmark_ratio` | 100% | 0% | no |

The state-income-tax movement this issue anticipated does **not** appear in the input-column parity gate — `state_income_tax` is a computed **output**, not an engine input. It is quantified in §3 (that is where the uprating fix actually shows up).

**Register-entry proposals (PROPOSALS ONLY — lead gates; nothing committed):**
- **No pin-attributable entries** (the bump adds zero gaps).
- Two **pre-existing** ACA-family exemptions proposed (reason'd, → #76): exempt `takes_up_aca_if_eligible` and `selected_marketplace_plan_benchmark_ratio` by name, noting they are populated by the native ACA stage before the gate. **Alternative** the lead may prefer: measure candidate shares on the post-ACA-stage frame rather than the raw base, in which case no entry is needed. Flagging the stage-ordering, not deciding it.

---

### 2. Take-up contract assertion (#315) — **PASS, all 13 flags @ 1.764.0**

Ran the engine-asserted take-up contract tests at the new pin: **14/14 pass** (incl. the field-by-field engine-fact check and the "no `model_simulated` flag is seeded" consistency guard).

Per-flag verdict at 1.764.0 (engine facts vs the checked-in contract, built against 1.752.2):

- **13 flags present** — no additions, no removals (no new `takes_up_*` variable appeared).
- **All 13 remain `data_seeded`** (`default=True`, no formula) — **zero migrated to `model_simulated`**. The model-side take-up migration referenced in #312/#315 still has not landed at 1.764.0.
- Every asserted engine fact (`entity`, `value_type`, `default`, `engine_class`) matches field-by-field. **No model-side seeding appeared for the data-seeded flags; no default-semantics shift.**

| treatment | flags |
|---|---|
| seed | `takes_up_eitc`, `takes_up_tanf_if_eligible` |
| out_of_scope | `takes_up_snap_if_eligible`, `takes_up_aca_if_eligible` |
| near_universal | `takes_up_medicare_if_eligible` |
| rate_unsourced | medicaid, chip, basic_health_program, ssi, dc_ptc, head_start, early_head_start, housing_assistance |

---

### 3. Critical-fit spot checks — pure model drift on the base, BEFORE calibration

Computed on the base at both pins over a **deterministic 40,000-hh subsample** (`Microsimulation.subsample(n=40000, seed=42, quantize_weights=True)`). The full 337,704-hh sim is dominated by pe-us per-household RNG re-seeding (stochastic take-up/imputation), ~7 min *per aggregation*; the fixed-seed subsample draws the **same households at both pins**, so the between-pin delta carries **zero sampling noise**, and weight-quantization keeps aggregates at full-base scale. Percentage drift is scale-stable. (Base is uncalibrated — magnitudes are pre-calibration; the *deltas* are the signal.)

**Federal — negligible, well-behaved drift (all < 0.2%):**

| target | 1.752.2 | 1.764.0 | Δ | Δ% |
|---|---:|---:|---:|---:|
| Federal income tax — amount | $2,000.25B | $2,004.04B | +$3.79B | **+0.190%** |
| Federal income tax — returns (>0) | 122.20M | 122.19M | −0.01M | −0.008% |
| Taxable Social Security — amount | $466.94B | $467.46B | +$0.51B | **+0.110%** |
| Taxable Social Security — returns (>0) | 28.069M | 28.079M | +0.010M | +0.036% |
| EITC — amount | $30.822B | $30.808B | −$0.014B | −0.045% |
| EITC — returns (>0) | 13.549M | 13.546M | −0.003M | −0.025% |
| Refundable CTC (ACTC) — amount | $21.614B | $21.619B | +$0.005B | +0.025% |
| ACTC — claims (>0) | 10.431M | 10.431M | 0.000M | 0.000% |

The +0.19% federal income tax is consistent with the 1.756.x federal-base changes (non-Sch-D cap-gain-distribution inclusion `1.756.2`, OBBBA clean-energy-credit termination `1.756.7`, Saver's Credit thresholds `1.756.6`) roughly offsetting. Supporting aggregates: AGI +0.17%, taxable income +0.21%, SNAP +0.29% (from the SNAP work-requirement changes), employment income / capital gains / TANF flat.

**State income tax by state (the #324-predicted movers) — one material mover:**

| state | 1.752.2 | 1.764.0 | Δ | Δ% | attribution |
|---|---:|---:|---:|---:|---|
| ME | $2.698B | $2.713B | +$0.015B | +0.55% | `1.756.9` uprating unfreeze (12 param files) |
| NE | $2.826B | $2.827B | +$0.001B | +0.04% | `1.756.8` explicit 2026 + `1.756.9` |
| ND | $0.213B | $0.214B | +$0.001B | +0.34% | `1.756.9` uprating unfreeze (5 files) |
| **NY** | **$43.56B** | **$55.98B** | **+$12.42B** | **+28.51%** | **`1.764.1` IT-196 §68 overall-limitation wiring** (+ `1.756.8` phase-out unfreeze) |
| OH | $11.14B | $11.16B | +$0.017B | +0.15% | `1.756.9` uprating unfreeze (1 file) |
| RI | $2.476B | $2.477B | +$0.001B | +0.03% | `1.756.8`/`1.756.9` |
| **ALL states** | **$468.14B** | **$490.41B** | **+$22.27B** | **+4.76%** | NY dominates |

**Headline: NY state income tax +28.5% (+$12.4B).** This is *not* the modest uprating effect — traced to **1.764.1**: "Wired New York's orphaned itemized-deduction phase-out parameter into the IT-196 Line 40 pre-TCJA overall limitation (26 U.S.C. 68 via NY Tax Law 615)." Confirmed on-disk: the NY `itemized/phase_out/start.yaml` parameter changed **and** the NY itemized-deduction variable sources changed (`ny_salt_deduction.py`, `pre_tcja/*`). It reduces NY itemized deductions → raises NY taxable income → raises NY tax. **Directionally correct** (NY was omitting the §68 overall limitation, under-taxing high-deduction filers) — a legitimate correctness improvement, but large enough that Build G's calibration starts from a materially different NY (and national state-tax) position than Build F did. The other five states show exactly the small uprating-unfreeze moves this issue anticipated.

I confirmed the `1.756.9` uprating fix mechanistically on-disk (the exact "`uprating:` moved from sibling-of-`values:` to `metadata:`" diff): **30 income-tax parameter files changed across ME/NE/ND/NY/OH/RI** (ME 12, NE 5, ND 5, NY 1, OH 1, RI 6), the balance of the changelog's "33 files / 107 nodes" being RI/NY contrib reforms.

---

### 4. New input surface (1.753–1.764) beyond the SNAP/ABAWD wave

Engine **input variables 841 → 863 (+24 added, −2 removed).** All 24 added default to `False`/`0` and base-F populates **none** (all consume engine defaults) → degenerate-gate (#286) candidates the moment populace targets the owning program.

- **SNAP/ABAWD wave (6, already tracked #248/#249/#250):** `is_snap_abawd_discretionary_exempt`, `is_snap_workfare_participant`, `weekly_snap_work_program_hours`, `has_applied_for_unemployment_compensation`, `is_complying_with_tanf_work_requirements`, `is_in_substance_use_treatment_program` (person-level). This is the SNAP work-requirement input carriage already scoped for Build G.
- **State childcare CCAP/CCDP enrollment (13, NEW beyond the SNAP wave):** ND/MT/NM/NV enrollment (`*_enrolled`, spm_unit) + provider-type/quality/hours (person, mostly enums). Releases 1.756.0/1.761.0/1.762.0/1.763.0. Low fiscal risk (opt-in, default off → the program simply does not fire); relevant only if populace targets these state childcare programs — then they are #286 candidates.
- **Local income tax (4, NEW):** `in_yonkers`, `ny_yonkers_nonresident_earnings`, `in_wilmington`, `de_wilmington_nonresident_earnings` (`1.757.0`).
- **Capital gains (1, NEW):** `schedule_d_capital_gain_distributions` (`1.756.0`) — the one new input that flows into the federal income-tax base. Base carries 0 at both pins (a definitional-consistency item, not a between-pin mover on this base). If populace later imputes cap-gain distributions, carry it **and** the pre-existing `capital_gain_distributions` together.
- **Removed (2), no action:** `small_area_fair_market_rent`, `safmr_used_for_hcv` — moved from stubbed inputs to parameterized/computed (`1.754.0`); they leave the input scope cleanly.

---

### Go / no-go recommendation

**GO — pin Build G to 1.764.x, with two documented follow-ups.**

The bump is safe and mostly beneficial:
- **Parity gate: unchanged** — zero new gaps (proven at both pins).
- **Take-up contract: PASS, all 13 flags** — no model-side seeding appeared, no semantics shifted.
- **Federal critical-fit: negligible drift** (< 0.2% on every target) — calibration's federal starting point is essentially unchanged.
- **State critical-fit: the only material mover is NY (+28.5%), and it is a legitimate correctness fix** (the §68 IT-196 overall limitation NY was previously omitting), not a regression. The five other named states move by the small amounts the uprating-placement fix predicts.

Follow-ups the lead should gate, none blocking:
1. **Expect NY / national state-tax targets to re-seat.** NY state income tax rises ~28% and the national state-income-tax total ~4.8% purely from the model. Build G's calibration and any Build-F-vs-Build-G results comparison must attribute this to `1.764.1`, not to data or weighting changes. If a state-income-tax fiscal target is in the feed, confirm it reflects the post-§68 NY (else calibration will fight a correct model).
2. **Two pre-existing ACA parity-register gaps** (`takes_up_aca_if_eligible`, `selected_marketplace_plan_benchmark_ratio`) — add reason'd exemptions (→ #76) or measure parity on the post-ACA-stage frame. Independent of the bump; surfaced by this pass.
3. **New-input watch (not now):** the 13 state-childcare + 4 local-tax + 1 cap-gains-distribution inputs are default-consuming; add to the #286 degenerate-gate watch if/when populace targets those programs. The 6 SNAP/ABAWD inputs are already the scoped Build G SNAP-carriage item.

If the lead prefers to ride the very latest, the same battery should be re-run at **1.765.3** before committing — 1.765.1/1.765.2/1.765.3 add PA/NJ/CO/CA/AZ state-tax fixes not covered here (none touch populace's input surface, but they would move the state critical-fit further).

---

*Battery artifacts (all under `~/PolicyEngine/_buildg-runtime/`, staging/local only — prod HF and latest.json untouched): `probe_pin.py`, `probe_state_tax.py`, `out/probe_{1752,1764}.json`, `out/state_tax_{1752,1764}.json`, `out/parity_scope_{1752,1764}.json`, `out/drift_table.md`, `out/register_proposals.md`. Reproduction: base sha `18833fb6…`, core 3.26.11 both pins, subsample n=40000 seed=42, period 2024. Full working log in `PROGRESS_BUILDG.md` on branch `build-g`.*
