# Pre-registered evaluation design: QRF drift diagnosis + imputation-approach validation

Status: DESIGN FROZEN BEFORE ANY NEW COMPUTATION. Written 2026-08-25 on
`qrf-drift-validation` (off origin/main bb796cb7). Charter:
`~/PolicyEngine/_buildo-runtime/scripts/charter_qrf_drift_validation.md`.
Every mechanism claim below is code-read this session at the cited anchor.
Every data-derived number is either quoted from an existing artifact (cited)
or left as a **[D0]** constant to be bound from existing artifacts before any
new computation runs. Nothing in this design may be revised after Phase-0
results exist, except by an explicitly logged amendment stating what was
learned and why the change cannot be outcome-motivated.

The test this document sets for itself: *when the numbers arrive, the verdict
should follow mechanically from rules written here — no post-hoc judgment
calls.* Wherever a judgment could occur, this document makes it now.

---

## 1. The evidence being explained (corrected)

From the pkg3 1% verify build (`experiments/battery_burndown_pkg3_evidence.md`,
sample fraction 0.01, seed 578), positive-leg weighted incidence, ASEC-origin
vs ACS-origin rows within the stacked artifact, **before** the #742
calibration layer:

| target | asec incidence | acs drawn incidence | ratio acs/asec |
|---|---|---|---|
| child_support_expense | 0.005237 | 0.000897 | **0.171** |
| child_support_received | 0.009283 | 0.002255 | **0.243** |
| weeks_unemployed | 0.034170 | 0.000867 | **0.025** |
| workers_compensation | 0.003265 | 0.000155 | **0.048** |
| spm_unit_energy_subsidy | 0.033554 | 0.008069 | **0.240** |
| pre_subsidy_care_expenses | 0.000768 | 0.000431 | 0.561 |
| self_employment_income_last_year | 0.024919 | 0.034308 | 1.377 (over) |
| ssi (simulated_output) | 0.020373 | 0.027330 | 1.341 (over) |

Correction to the charter's shorthand: "0.17 vs 0.24" are **ratios** for the
two child-support targets, not incidences. The real severity is 4–40×
underdraw of rare positive carriers, in the same direction for five unrelated
transfer variables, with two mild *over*draws elsewhere. Any explanation must
account for the *magnitude and the shared direction*, not just nonzero drift.
A smooth covariate-shift story (recipient demographics slightly different)
predicts drifts of tens of percent, not 40×. A mechanical story (rows that
never receive a draw; a feature the gate reads that is wildly different or
missing on one side) predicts exactly this signature. The design below is
built to separate those cleanly.

## 2. Estimands and verified mechanics (code anchors)

These are the facts the accounting rests on. Each was read this session;
re-verify anchors before the lane runs (files move).

**E1 — battery incidence.** `_weighted_nonzero_incidence(values[rows],
weights[rows])` per origin, over the battery's scope rows within the one
stacked artifact; comparison is ACS-over-ASEC ratio with bounds [0.8, 1.25]
(`stacked_spine.py` `_battery_incidence_comparison`, ~13635; bounds in
`_by_origin_battery_evaluate` docstring, ~13245). Positive/negative legs are
separated for monetary targets (`_battery_sign_separated_comparison`). The
denominator is **all scope rows of that origin**, not only rows the QRF drew.
This is the estimand every drift number in this experiment refers to; scope
definitions come from the production authority's metric registry, never
re-derived by hand.

**E2 — gate draw identity.** Sign classes are inverse-CDF samples from
`predict_proba`: `cumulative >= u` argmax (`qrf.py::_gate_draw_with_rng`,
950–962). Therefore, over any row set R with weights w,
E[weighted drawn nonzero incidence on R] = Σ_R w·(1 − p_zero) / Σ_R w
exactly, with binomial-scale noise. No thresholding, no tuning, no clipping.

**E3 — gate fit.** `HistGradientBoostingClassifier(random_state=s)` with
default hyperparameters, fit with `sample_weight` = resolved design weights
directly (`qrf.py::_fit_gate`, 1389–1442). Weighted in-sample mean predicted
probability of a class approximately equals the weighted observed class share
(boosting on weighted log-loss); the *exact* in-sample gap is measured, not
assumed (term T1 below).

**E4 — gate reproducibility without forests.** In `_fit_target` the gate
seed is the **first** integer drawn from the fit RNG for a gated target
(`qrf.py:1428`), before any forest bootstrap (`qrf.py:1352`). So a target's
gate is reproduced bit-identically from: chain state before that target
(`fit_rng_state_json`, `QRFChainState`, qrf.py:648–880) + donor table +
weights + config. No forest fits needed. Analysis-time gate reproduction is
cheap and receipted by the state's weight/index SHA-256 digests.

**E5 — chain asymmetry.** Fit features for target t = predictors + donor
**observed** completed targets; draw features = predictors + recipient **raw
drawn** priors (`qrf.py::fit_draw_next`, 1151–1231). Chained drift can
propagate; conditioning on drawn (noisier, possibly shifted) priors is
mechanically different from conditioning on observed ones.

**E6 — transfer predictors.** Required: `age`, `is_female`, state FIPS
(broadcast). Optional (availability-pattern) features:
employment/self-employment/social-security/retirement/investment income,
household-head, tenure — recipient side built from ACS-native reports, donor
side from summed ASEC components (`acs_transfer.py:95–190`,
`_DONOR_COMBINED_COMPONENTS`). All are natively observed on both sides;
chained-imputed features enter only as prior targets within the same fitted
family (≤8 targets per fit, `DEFAULT_ACS_TRANSFER_MAX_TARGETS_PER_FIT`).
Recipient rows are partitioned by availability pattern; **one separately
seeded QRF per pattern**, fit on donor rows complete for that predictor set
and the family targets (`acs_transfer.py:926`, `:1489–1515`). "The gate" for
a target is a set of per-pattern gates.

**E7 — coverage rule.** The transfer fills **only null recipient cells**;
rows failing row-level complete-case masks for a pattern's predictors are
kept out of the QRF (`acs_transfer.py` module docstring, `:98`). What value a
never-drawn row carries at battery time is a pipeline question
(`CANONICAL_STACKED_GAP_FILL_PLAN`, `stacked_spine.py`), deliberately left as
Phase-0 probe P0 rather than asserted here.

**E8 — universe mismatch.** The ACS spine retains group-quarters persons,
institutional and noninstitutional, PWGTP-weighted (`acs_pums.py:130–147,
307–308, 398–408`). CPS-ASEC's universe is civilian noninstitutional. The
recipient contains people the donor structurally cannot represent.

**E9 — arm A mechanism.** The #742 layer is a deterministic two-part edit of
mutable draws: carrier-prevalence prefix selection toward the weighted
**donor** margin + five-quantile mapping of mutable positive amounts onto
reference support; positive leg only; negatives byte-exact
(`post_transfer_calibration.py` docstring + `_QUANTILES`). Spec roster
(`POST_TRANSFER_CALIBRATION_SPECS`, :193–263): late_transfer =
pre_subsidy_care_expenses, child_support_expense, child_support_received,
disability_benefits (preserve_recipient), weeks_unemployed,
workers_compensation, spm_unit_energy_subsidy; early_gap_fill =
unemployment_compensation (preserve_recipient),
self_employment_income_last_year.

**E10 — measurement non-equivalence of "shared" features (documented, not
computed).** ASEC income is prior calendar year; ACS income is a rolling
12-month reference with ADJINC adjustment; ACS bundles
interest+dividends+net-rental in one item while the donor side sums distinct
ASEC series. "Shared features should be pretty similar" is a hypothesis
(H3), not a premise, and the feature audit (P3) tests it per feature.

## 3. Mission 1 — drift decomposition

### 3.1 The accounting identity (exhaustive, additive)

For one target t and the battery's ACS scope S with artifact weights w. Let
D = I_asec − I_acs (the battery gap). Partition S by **value provenance**
(P0): rows drawn by the QRF (S_q, weighted share φ), rows carrying values
from any other path (S_o): native, gap-filled, defaulted, untouched-null →
whatever the artifact stores. Then, exactly:

    I_acs = φ·I_q + (1−φ)·I_o                                   (L0)

and within S_q, using E2:

    I_asec − I_q = (I_asec − P̄_donor)      T1  in-sample calibration gap
                 + (P̄_donor − P̄_acs)       T2  covariate/spine shift
                 + (P̄_acs − I_q)           T3  draw noise (E[T3]=0)

where P̄ is the weighted mean of (1 − p_zero) from the reproduced per-pattern
gates (E4), P̄_donor over the pattern's donor training rows with fit weights,
P̄_acs over S_q with artifact weights, both aggregated over patterns by their
weighted shares (pattern-level terms retained in the output — the pattern
mixture is itself a named component, T2m). Every term is computed and the
table must sum to D exactly, with T3 compared against its pre-computed
binomial SE (§3.6). **Nothing is allowed to hide in a residual: the residual
IS a row of the table.**

### 3.2 Attribution of T2 (feature groups)

Substitution estimator, pre-declared: for feature group g, re-evaluate the
gate on S_q with group g's columns replaced by values quantile-mapped to the
pattern's donor training marginal (weighted, per pattern; joint within the
group; seeded map). Contribution(g) = P̄_acs(substituted g) − P̄_acs. Groups,
fixed now:

  G1 demographics (age, is_female, state)
  G2 native income/tenure optional features (the E6 seven)
  G3 chained prior draws (within-family completed targets)
  G4 availability-pattern mixture (recomposition to donor pattern shares)
  G5 GQ membership (computed as a subgroup deletion, not substitution:
     recompute D excluding GQ rows; contribution = D − D_noGQ)

Single-group substitutions plus the all-groups substitution; the gap between
Σ contributions and the all-groups effect is the **interaction term**,
reported, never allocated. Direction check: the all-groups substitution
should recover P̄_donor to within tolerance — if it does not, the estimator
is broken and no attribution is reported (fail closed).

### 3.3 Negative controls (the decomposition is not trusted without them)

  C1 **donor-half self-transfer.** Split donor rows in half by seeded draw;
     fit the family QRF on half A (same config/seeds discipline as
     production), draw onto half B's observed features; run the same
     three-term identity. Expectation if the machinery and estimator are
     sound and the drift is genuinely recipient-side: T1 ≈ 0, T2 ≈ 0,
     ratio ≈ 1 within noise. A material within-survey gap reclassifies that
     much of the "spine shift" as estimator pathology, not survey
     difference.
  C2 **synthetic covariate tilt.** Construct recipient′ = donor half B
     resampled with a known tilt on one G2 feature (declared tilt, seeded).
     The machinery must attribute the induced drift to that feature's group
     within tolerance and report ≈ 0 elsewhere.
  C3 **synthetic chained corruption.** Same, but corrupt one chained prior
     column by a declared shift; the machinery must charge G3.
  The tolerances for C1–C3 are set by the same SE formulas of §3.6.
  **If any control fails, the instrument is fixed before any real reading is
  reported; real readings from a failed instrument are discarded unseen**
  (computed last, controls first, enforced by lane script order).

### 3.4 Hypothesis register (fixed before data; discriminating signatures)

| id | mechanism | pre-data plausibility given §1 | signature that confirms | signature that refutes |
|---|---|---|---|---|
| H0 coverage/provenance | never-drawn rows dilute I_acs (E7) | HIGH — only story that naturally yields uniform 4–40× | L0: φ low or I_o ≈ 0 with large (1−φ) | φ ≈ 1 |
| H1 in-sample miscalibration | gate mean proba ≠ donor incidence | LOW (E3) | T1 dominant | T1 ≈ 0 |
| H2 estimator generalization | within-survey holdout gap | LOW–MED | C1 gap material | C1 clean |
| H3a genuine composition shift (incl. GQ) | recipient really differs on native features | MED for mild drift; LOW for 40× | T2 dominant, G1/G2/G5 loaded, feature marginals genuinely differ (P3) | G1/G2 ≈ 0 |
| H3b feature-construction mismatch | same-named feature built differently (E10) | MED | T2 via G2 with marginal gaps concentrated in specific engineered features; unit-level forensics confirm | G2 ≈ 0 |
| H4 chained propagation | prior targets' drift compounds (E5) | MED | G3 loaded; drift trends with chain position (P4) | G3 ≈ 0, no trend |
| H5 extrapolation | recipient rows in donor-thin regions | LOW–MED | drift concentrates in thin-support rows (P5) | uniform across support |
| H6 draw mechanics | identity E2 broken in production path | VERY LOW (code-read) | T3 beyond noise | T3 within noise |

The register's job at verdict time: the observed pattern across
(L0, T1–T3, G1–G5, C1, P3–P5) must match exactly one row — or the verdict is
explicitly "mixture", with shares. **Pre-declared verdict rule:** a single
component ≥ 60% of |D| (after instrument validation) names the root cause; a
named root cause that is a *defect* (H0 coverage bug, H3b construction bug,
H4 chain-order defect) creates arm D; H3a ("the surveys genuinely differ")
is **not** a defect — under H3a the plain QRF is doing its job and the
drift-vs-donor-margin is a modeling convention question that the ONE target
surface arbitrates, not the battery (§4.5).

### 3.5 Probes (deliverables per target)

  P0 provenance/coverage table (L0), per target: φ, I_q, I_o, path census
     with code anchors for each path.
  P1 three-term identity table (T1/T2/T3 + pattern mixture detail).
  P2 attribution table (G1–G5 + interaction).
  P3 feature-marginal audit: weighted donor-vs-recipient marginals per gate
     feature, per pattern, with two-sample SEs; engineered features compared
     at the *construction* level (units, reference period, bundling) with
     the constructing code cited on each side.
  P4 chain-depth curve: per-target |drift| vs within-family chain position,
     with incidence level as covariate (position correlates with rarity;
     the partial trend is the evidence, not the raw one).
  P5 extrapolation probe: per-row donor support (gate leaf population /
     nearest-donor distance on the pattern feature set, definitions fixed in
     the lane charter before running); drift concentration ratio in the
     bottom support decile.

Target order: the §1 table, worst ratio first; all seven late_transfer specs
plus the two early_gap_fill ones; SSI's *over*draw (simulated_output) is kept
as a contrast case — a correct mechanism story should explain sign reversals,
not just underdraws.

### 3.6 Measurability, bound at D0 (before any new computation)

SE(I) ≈ sqrt(deff · p(1−p)/n) per origin/leg; SE(ratio) by delta method.
**[D0-1]** n and deff per target scope/origin from the pkg3 artifact.
**[D0-2]** replicate SDs of battery incidence per target from the existing
repeat 1% builds (pkg1 r2/r3/r4, pkg3 r2/r3/r4 under
`_buildo-runtime/out/battery-verify/`) — the empirical noise floor that all
"material" claims are measured against. **[D0-3]** minimum-support rule: a
target/leg with expected positive rows < 50 on either origin at 1% is
reported "insufficient support at 1%; defer to 25%" — never a confident
verdict. The D0 constants are appended to this file in one commit before the
Phase-0 lane is dispatched; they are inputs, not results.

## 4. Mission 2 — arm validation

### 4.1 Arms (inputs of record)

  A calibrated incumbent: candidate-25 artifacts
    (`_buildo-runtime/out/candidate-25/`, launcher `run-candidate.sh` is the
    seed/input record; build running as of 2026-08-25, never rebuilt here).
  B parsimony: plain QRF + weight calibration
    (worktree `_worktrees/microcosm-parsimony`, sol lane
    `20260825-231707-parsimony`; consume `battery-lanes/parsimony.out`).
  C two-step beta (Max's proposal), closed-form, spec-declared, receipted:
    - gate stage: per-target logit offset δ_t applied to p_nonzero, solved by
      monotone 1-D bisection so the recipient weighted mean corrected
      probability equals the weighted donor margin; tolerance 1e-6 in
      incidence; solved once per target per pattern from donor references
      only; never iterated against any scorecard.
    - amount stage: per-leg skewed quantile draw, u ~ Beta(a,1) replacing
      Uniform in E2's amount path; a solved by monotone 1-D bisection so the
      drawn weighted positive-leg **mean** matches the donor weighted
      positive-leg mean. Declared statistic = mean, decided now: the ONE
      target surface is sums, and mean×carriers is the quantity weight
      calibration downstream actually consumes; the median shift is reported
      as a side effect, not targeted. Known cost: skewed u shrinks draw
      variance; the battery's five conditional quantiles are mandatory
      output so the cost is visible.
    - C is only coherent if Phase 0 shows the gap is NOT H0/H3b/H4-defect:
      correcting a coverage bug with a sampler skew would be tuning over a
      defect. **Gate: arm C is built only under H1/H3a/H5/mixture verdicts.**
  D root-cause fix: only if Phase 0 names a defect; plain QRF + the fix, no
    adjustment layer.

All arms: same seeds/epochs/inputs as the candidate chain (read from
`run-candidate.sh`); same pool inputs; 1% first (1%-rung doctrine), 25% only
for arms that clear their 1% gates and only after the running candidate
chain releases the host (serial-queue discipline, `.max-go`, AC power).

### 4.2 Primary metrics (the charter's four; roles fixed now)

  M-1 post-weight-calibration loss and %-within-10 on the ONE target
      surface — the product arbiter.
  M-2 rare-transfer counts/incidence at fixed weights — the degeneracy
      guard (calibration can hide a dead variable by upweighting carriers;
      an arm that zeroes a variable cannot win regardless of M-1).
  M-3 by-origin battery (incidence + five conditional quantiles) —
      donor-fidelity diagnostic and variance-cost report; NOT the arbiter
      (§4.5).
  M-4 wall-time per stage — cost axis (the ~2.5→10 min/target regression is
      itself evidence; per-arm timings recorded from build logs).

### 4.3 Secondary, non-arbitrating diagnostics (declared now so they cannot
be cherry-picked later)

  S-1 conditional-structure preservation: weighted regression of drawn
      value on (age, employment-income feature, state-mean income), donor vs
      each arm; arm A's prefix selection and C's skew both risk breaking
      value–covariate structure that plain QRF preserves — this makes that
      cost visible symmetrically.
  S-2 C's variance shrinkage: five-quantile spread ratio vs B.

### 4.4 Decision rule (pre-registered)

Paired same-seed comparisons. Materiality per metric =
max(2 × replicate SD from [D0-2], floor of 1.0 point for %-within-10).
Rules, in order:
  1. If D exists and is within materiality of the best arm on M-1 while
     passing M-2: **D wins** (a removed defect dominates any added layer).
  2. Else **B wins unless** another arm beats B on M-1 by more than
     materiality AND passes M-2. Max's parsimony ruling is the standing
     default being tested, so B is the null, not the underdog.
  3. If A or C materially beats B: the scorecard goes to Max with the M-1
     delta, the M-3 fidelity picture, and the S-1/S-2 structure costs — the
     accuracy-for-parsimony trade is his call, quantified. This experiment
     never flips anything.
  4. Ties on M-1 break to: M-2, then fewer moving parts (B ≻ D ≻ C ≻ A),
     then M-4.
Promotion to 25%: an arm must clear its 1% gates artifact and improve or
hold every [D0-3]-measurable target's M-2 standing vs its own 1% baseline.

### 4.5 Which margin is "right" (doctrine, fixed now)

Donor-margin fidelity (M-3) is a convention, not truth: ASEC's incidence is
not admin truth for the ACS population, and under H3a a "drifted" margin may
be the *correct* conditional answer. The admin-anchored truth Max chose
lives in the ONE target surface; M-1 is therefore the only arbiter. No new
truth sources enter through this experiment.

## 5. Discipline

- No gate/threshold/band/fold/seed tuning toward passing, anywhere. C's
  parameters derive from donor margins only, frozen in spec before any
  scorecard run; the solve scripts emit receipts (inputs, tolerances,
  solutions, digests).
- Phase 0 runs read-only over existing checkpoints + cheap deterministic
  gate reproductions (E4) + the C1–C3 control fits (donor-half HGB fits,
  bounded minutes of CPU, no forest fits, no pool builds); RAM footprint
  stays modest while the candidate build owns the host; builds only through
  the serial queue.
- Off-chain: `env -u POPULACE_LOGBOOK_PREV_ROW_DIGEST` + `--no-staging`.
- Implementation → sol lanes (`subfleet run -m sol -t build`), headless,
  no-network, pre-built venvs; lane charters carry a HEADLESS EXECUTION
  block and this file by reference; scripts run controls before readings
  (§3.3 fail-closed order).
- Every number in the final report traces to a script + input digests; the
  report leads with the L0/T/G table and the plain-language verdict, then
  the arm scorecard; publish/promote is never a side effect; Max flips
  latest.

## 6. Order of work

  D0  bind constants (§3.6) from existing artifacts; append here; commit.
  P-lane  Phase-0 sol lane: controls C1–C3 first (instrument validation),
      then P0–P5 on the §1 targets at 1%; decomposition tables + verdict
      per §3.4.
  Gate  arm D and/or arm C become concrete per §4.1's gates; specs written,
      frozen, committed before any arm build.
  1%  arms built same-seed; primary metrics; decision rule §4.4.
  25%  finalists only, post-candidate-chain, head-to-head via
      `tools/score_us_release_head_to_head.py` (#748) with live incumbent
      column; multi-column scorecard to Max.
