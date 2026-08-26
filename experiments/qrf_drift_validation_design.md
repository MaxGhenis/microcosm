# Pre-registered evaluation design: QRF drift diagnosis + imputation-approach validation (v2)

Status: v2, REPLACES v1 (git 4bee683d) IN FULL, before any Phase-0 computation.
v1 was adversarially reviewed by two independent processes before any data work
ran: a 39-agent three-lens fable panel (35 confirmed findings, 13 critical;
findings JSON archived in the session scratchpad) and a gpt-5.6-sol lane
(`_buildo-runtime/out/battery-lanes/design-review.out`, verdict REDESIGN, 16
findings, 9 critical). Every operative section below is rewritten to their
merged, code-verified fixes. No Phase-0 results existed when this revision was
written, so it cannot be outcome-motivated; from here, changes require a logged
amendment, and control seeds are burned on any post-failure refreeze (§3.6).

Charter: `~/PolicyEngine/_buildo-runtime/scripts/charter_qrf_drift_validation.md`.
Branch: `qrf-drift-validation` off origin/main bb796cb7.

The bar is unchanged from v1: when the numbers arrive, the verdict must follow
mechanically from rules written here. v1 failed that bar in review; v2's rules
were themselves reviewed against the failure modes found.

---

## 1. The evidence being explained (corrected provenance)

The headline numbers are the **baseline1pct** build's by-origin battery failure
lines (surfaced as the "greened by pkg3" diff in
`experiments/battery_burndown_pkg3_evidence.md`; baseline1pct = plain QRF, no
#742 calibration layer, sample fraction 0.01, seed 578). v1 misattributed them
to "the pkg3 build" — pkg3 is the 1% build WITH the two-part #742 layer.
Positive-leg weighted incidence, ASEC-origin vs ACS-origin, one artifact:

| target | asec + leg | acs + leg | ratio acs/asec |
|---|---|---|---|
| child_support_expense | 0.005237 | 0.000897 | 0.171 |
| child_support_received | 0.009283 | 0.002255 | 0.243 |
| weeks_unemployed | 0.034170 | 0.000867 | 0.025 |
| workers_compensation | 0.003265 | 0.000155 | 0.048 |
| spm_unit_energy_subsidy | 0.033554 | 0.008069 | 0.240 |
| pre_subsidy_care_expenses | 0.000768 | 0.000431 | 0.561 |
| self_employment_income_last_year | 0.024919 | 0.034308 | 1.377 |
| ssi (simulated_output — NOT a QRF target, §3.0) | 0.020373 | 0.027330 | 1.341 |

Caveats bound in now: these 1% ratios rest on thin positive-row counts (tens of
rows for the worst targets — exact per-target counts bound at D0 with the
clone-deduplication convention of §3.7); the 25% candidate-25 gates confirm the
phenomenon at scale for the un-calibrated families and show two further facts:
weeks_unemployed stays out of band even WITH the #742 layer (ratio 0.31 — its
carrier additions are capped by the UC-positivity constraint), and
self_employment_income_last_year's NEGATIVE leg overdraws 6.7× (the layer is
positive-leg-only, so that is raw QRF + producer behavior). Direction is mixed
across targets (mostly severe underdraw, some overdraw), so the explanation
must be per-target and per-leg, not one story.

## 2. Verified mechanics (code anchors; both reviews re-verified these)

**E1 — battery estimand.** Per-leg weighted incidence (share of values > 0,
resp. < 0, exact comparison — no atol) among **clone-0** origin scope rows with
positive resolved artifact weights, ASEC-over-ACS ratio bounds [0.8, 1.25]
(`stacked_spine.py:13331–13442, 13695–13741`). All nine §1 targets are
`monetary_sign_separated`. Scope includes structural-absence refinements
(:13393–13397). Every drift number in this experiment means THIS estimand.

**E2 — gate draw identity.** Sign classes are inverse-CDF draws from
`predict_proba` (`qrf.py:950–962`): over rows R with weights w, the expected
weighted drawn share of class c equals Σ_R w·p_c / Σ_R w exactly, at exact
conditional draw variance Σ w_i²·p_c,i(1−p_c,i)/(Σ w_i)². Per-leg accounting
uses the class-c probability, never 1−p_zero (THREE_SIGN targets exist:
self_employment_income_last_year is contractually signed —
`prior_year_income.py:201–205`, `qrf.py:138–139`).

**E3 — gate fit.** `HistGradientBoostingClassifier(random_state=s)`, default
hyperparameters, direct `sample_weight` (`qrf.py:1389–1442`). Its true
in-sample calibration gap is measured (T1, §3.2), never assumed.

**E4 — gate reproduction.** For a gated target the gate seed is the first
integer drawn from the fit RNG (`qrf.py:1428`), before any forest bootstrap
(:1352). Per-pattern gates reproduce bit-identically from bank pattern states +
fit rows + weights, forest-free. `_weighted_bootstrap` touches only magnitude
forests, never the gate (`qrf.py:188–217, 1333–1380`).

**E5 — chain asymmetry.** Fit conditions on donor observed prior targets; draw
conditions on recipient raw drawn priors (`qrf.py:1151–1231`).

**E6 — the production late-transfer donor is NOT plain ASEC.** The late
transfer trains on the **clone-1 owner projection** of ASEC-origin rows — the
PUF tax-detail clone, whose income features carry PUF-sourced detail and whose
weights are the halved clone-channel weights (`stacked_spine.py:10140–10249`;
`_post_puf_role_mask` selects channel asec AND clone == PUF_TAX_DETAIL_CLONE_INDEX
= 1, `support_provenance.py:37`; receipt: `owner_projection_of_asec_origin_clone_1`).
The clone-2 capital-gains tail split precedes the late transfer, so tail rows
are in the clone-0 battery basis but not the donor. The EARLY transfer
(unemployment_compensation, self_employment_income_last_year) trains on the
pre-clone whole ASEC channel (`stacked_spine.py:9266–9292`). v1's claim that
shared features are "natively observed on both sides" is FALSE for the late
stage; the identity carries explicit donor-basis bridges (§3.2).

**E7 — producer first hop caps training at 5,000 rows.** Five ASEC-side source
operators subsample their QRF training input to 5,000 rows without sign
stratification or weight-proportional sampling (`child_support.py:323–329`,
`workers_compensation.py:302–308`, `energy_subsidy.py:325–331`,
`disability_benefits.py:342–348`, `prior_year_income.py:449–455`), so a rare
class or much of its weighted mass can thin before `detect_regime`/`_fit_gate`
ever run; the clone-1 producer values the late transfer learns from inherit
this. weeks_unemployed is additionally forced to zero post-draw when
unemployment compensation is nonpositive (`weeks_unemployed.py:900–909,
966–983`).

**E8 — availability patterns.** Recipient rows partition by observed optional
predictors; each pattern gets a separately seeded QRF fit on donor rows
complete for that predictor set AND every family target (≤8 targets per fit;
`acs_transfer.py:1441–1600, 1648–1760, 2039–2058`). Donor training sets
OVERLAP across patterns (no donor-side pattern partition exists). A pattern
whose complete-case donor pool has zero positive carriers silently becomes
DEGENERATE_ZERO and draws all zeros for its rows (only `donor_rows==0` raises;
`acs_transfer.py:1513–1523`, `qrf.py:132–150, 982–983`).

**E9 — post-draw deterministic transforms.** Between raw draw and artifact
value sit: target codec decode, structural reconciliation (adult-care
one-per-tax-unit — `acs_transfer.py:687–739`; weeks-requires-UC), and (arm A
only) the #742 calibration edit (`post_transfer_calibration.py:193–263,
823–900`: positive-leg carrier prefix selection toward the weighted reference
margin + five-quantile amount mapping; negatives byte-exact; spec roster as in
v1 §2-E9). These are deterministic and must never be charged to draw noise.

**E10 — zero conventions differ.** QRF's zero class is |y| ≤ 1e-6
(`qrf.py:87–89`); the battery and calibration use exact >0/<0/!=0. Boundary
mass is measured at D0 and bridged explicitly if nonzero.

**E11 — group-entity targets.** spm_unit_energy_subsidy's gate features are the
group roster (person count, age sum, female count, state, group optional sums —
`acs_transfer.py:168–186`), not the person roster. Feature groups are defined
per target from the actual `AcsTransferPattern.predictors` matrix, frozen at D0.

**E12 — GQ.** The ACS spine retains institutional (TYPEHUGQ 2) and
noninstitutional (TYPEHUGQ 3) group-quarters persons with positive
PWGTP-derived weights (`acs_pums.py:128–148, 394–414, 590–616`); CPS-ASEC is
civilian noninstitutional.

**E13 — ssi is not a QRF transfer target.** Family `simulated_output`,
materialized by the rules-engine formula for all rows of both origins
(`multispine_pool.py:700–715`); it has no gate, patterns, or bank checkpoint.

## 3. Mission 1 — drift decomposition

### 3.0 Applicability matrix

Probes P0–P6 and the identity run on the QRF transfer targets only. ssi is a
non-arbitrating downstream contrast with its own short dependency note (which
imputed inputs feed the ssi formula; no root-cause share, no controls, no arm-C
eligibility). Per-target × per-probe applicability, with each target's
per-pattern regime matrix (read from the pinned build's bank states/manifest),
is frozen at D0 before dispatch.

### 3.1 The accounting identity (per target, per leg ℓ ∈ {+, −}, exact)

Rung: the pinned 25% pre-calibration checkpoints (§3.7). Scope S, artifact
weights, per E1. Provenance partition (P0): S_q = scope ∩ owner-authorized ∩
target-null-before ∩ finite raw draw ∩ successfully decoded fill; S_o = S \ S_q;
φ = weighted share of S_q. Then

    D_ℓ = J0_ℓ − I_acs,ℓ
        = (1−φ)·(J0_ℓ − I_o,ℓ)                            L0  coverage
        + φ·[ (J0_ℓ − J1_ℓ)                               B1  producer hop
            + (J1_ℓ − J2_ℓ)                               B2  fit-row selection
            + (J2_ℓ − P_D,ℓ)                              T1  gate calibration
            + (P_D,ℓ − P_R,ℓ)                             T2  covariate shift
            + (P_R,ℓ − I_raw,ℓ)                           T3  draw noise
            + (I_raw,ℓ − I_dec,ℓ)                         T4  codec
            + (I_dec,ℓ − I_q,ℓ) ]                         T5  structural

where J0 = battery clone-0 ASEC leg incidence (artifact weights); J1 = leg
incidence on the actual donor projection rows for the stage (late: clone-1
projection with its weights; early: pre-clone ASEC channel, so J1 ≡ J0 basis up
to the declared weight bridge); J2 = Σ_k α_k·m_k with m_k the observed leg
incidence on pattern k's exact fit rows with fit weights and α_k pattern k's
artifact-weight share of S_q; P_D = Σ_k α_k·(weighted mean class-ℓ proba on
pattern k's fit rows, fit weights); P_R = Σ_k α_k·(weighted mean class-ℓ proba
on pattern k's S_q rows, artifact weights); I_raw/I_dec/I_q = raw drawn /
decoded / post-structural leg incidence on S_q. On the arm-A build a further
T6 (calibration edit) term closes to the artifact value; on the pinned
pre-calibration basis T6 ≡ 0 by construction and is asserted so.

Sub-ledgers, frozen: **B1** carries the producer first-hop ledger P6 (full ASEC
source → 5k-row sample → detected regime/gate fit → first draw → codec →
producer constraints → clone-1 value; at each transition: row-mask digest,
unweighted sign counts, weighted sign mass, leg incidence, seed) plus the
clone-2 tail exclusion and the clone-weight bridge, each a named row. **B2**
carries role/channel selection, family complete-case, pattern predictor
complete-case, weight-basis change, pattern standardization, and the
per-pattern collapse census (patterns with zero positive carriers / collapsed
regimes, with their recipient weighted shares). φ=0 targets take the L0-only
branch with no conditional terms. All rows are computed; the ledger sums to
D_ℓ exactly; the residual is a row, and every row carries its analytic SE
(§3.7).

Fallback: if S_q masks cannot be recovered (bank raw_draw positions cover
family rows, not target-null rows; `imputed_inputs` is aggregate-only —
`acs_transfer.py:425–446, 1100–1133`), P0 requires the pinned pre-transfer
stage checkpoint or deterministic replay; if neither is available Phase 0
reports P0 = UNAVAILABLE and fails closed for that target. First check, run
before anything else: candidate-25 receipts report authorized == imputed and
zero unmodeled/residual rows for this roster — if the target-specific masks
confirm that, φ = 1 and L0 = 0 (H0 dies cheaply).

### 3.2 Attribution of T2 (Shapley over joint donor-row hot deck)

Feature groups per target from the frozen predictor matrix: G1 demographics
(person targets: age, is_female, state; group targets: their real group
roster), G2 optional income/tenure features (or group sums), G3 chained prior
draws. No G4 (pattern standardization lives in B2); GQ is not a feature group
(§3.4). Estimator, frozen: for each target, pattern, and coalition
c ⊆ {G1,G2,G3} (2³ coalitions), draw one donor fit row per recipient S_q row
with probability proportional to fit weight; copy ALL columns of the coalition
groups from that same donor row (joint within and across substituted groups —
handles categorical columns exactly); retain recipient artifact weights;
common donor draws across coalitions; 1,000 replicates; seed per replicate =
first 64 bits of SHA-256 of `qrf-drift-v2|target|pattern|replicate`; Shapley
contributions from the coalition means; the all-groups coalition's gap from
P_D is the named ledger row "cross-group dependence residual" (zeroed only if
within its threshold, §3.7). Declared limits: substitution estimates
association, partial coalitions create off-manifold hybrids; attribution is
reported not-validated if C2/C3 fail (§3.6) or domain constraints are violated.
Chained-prior (G3) sub-attributions per prior column replace v1's cross-target
chain-depth trend (P4) as the chaining evidence.

### 3.3 Probes

  P0 provenance/coverage: φ, I_q, I_o, path census with code anchor per path;
     mask digests reconciled against authorized/imputed/unmodeled receipts.
  P1 full per-leg ledger table (§3.1) per target.
  P2 T2 Shapley attribution (§3.2) + per-feature weighted marginal audit
     (donor fit rows vs recipient S_q, per pattern, two-sample SEs;
     engineered features compared at construction level with both
     constructing code paths cited).
  P3 producer ledger (B1 sub-ledger; the 5k-cap and constraint transitions).
  P5 extrapolation, metric frozen NOW: per recipient S_q row, weighted mean
     Gower distance to the k=25 nearest donor fit rows of its pattern
     (features = that pattern's gate predictors; numeric scaled by donor
     weighted IQR; categorical/state exact-mismatch cost 1; ties by stable
     entity id); deciles over S_q; report per-decile leg drift; "concentrated"
     iff the bottom support decile carries ≥ 50% of |T2|.
  P6 = B1 ledger (listed for numbering continuity with §3.1).
  P7 GQ population identity (§3.4).
  P8 ssi dependency note (§3.0).

### 3.4 GQ (population identity, outside the additive ledger)

With H = housing-unit, 2/3 = TYPEHUGQ institutional/noninstitutional, ω the
weighted shares of the ACS scope: I_ACS = ω_H·I_H + ω_2·I_2 + ω_3·I_3, hence
D = (J0 − I_H) + ω_2(I_H − I_2) + ω_3(I_H − I_3), reported separately per leg.
GQ never enters §3.2 and is never added to the §3.1 ledger.

### 3.5 Hypothesis register (per target per leg; signatures on the v2 ledger)

| id | mechanism | confirming signature | class |
|---|---|---|---|
| H0 | coverage (never-drawn rows) | L0 dominant | bug-vs-by-design per P0 census criterion (a path with a spec'd, receipted, PR-adjudicated intent is by-design; an emergent/undocumented path is defect-candidate) |
| H1 | gate miscalibration | T1 dominant | estimator property |
| H2 | out-of-sample generalization | C1 cross-fitted gap material | estimator property |
| H3a | genuine composition shift | T2 dominant, loaded on G1/G2 jointly, marginals genuinely differ, P7 may load | not a defect (§4.6) |
| H3b | feature-construction mismatch | T2 via G2 with construction-level forensics | defect |
| H4 | chained propagation | T2 via G3 sub-attributions | defect iff a chain-order/constructive bug is named |
| H5 | extrapolation | P5 concentrated | estimator property |
| H6a | stochastic draw mechanics | T3 beyond its exact-variance band | defect (code) |
| H6b | post-draw transforms | T4/T5 dominant (weeks-requires-UC, adult-care reconciliation land here) | bug-vs-by-design per the same criterion as H0 |
| H7 | donor-basis & selection | B1/B2 dominant; sub-rows name clone hop, 5k cap, complete-case, weight basis, pattern collapse | defect-candidate per sub-row (5k unstratified cap and silent pattern collapse are defect-candidates; clone architecture itself is by-design) |

Verdict mechanics, frozen: shares are |c_j| / Σ_h |c_h| over the additive
ledger rows; report the cancellation index Σ|c_h| / |D|; "dominant" = a row (or
a register row's named row-set, jointly) ≥ 60% of Σ|c| with each named row ≥
its §3.7 threshold; "no dominant cause" whenever the net gap is within its
paired uncertainty. Verdicts are PER TARGET (per leg). Defect-classified rows
that are ≥ 25% of Σ|c| AND ≥ threshold create arm D for that target and block
arm C and B-validation for that target until rebased on the D-fixed base; the
same condition set is used for both the C-block and the D-create (no orphan
zone); material-but-unresolved rows route to "unresolved — no C, no
decomposition-derived D" (code-level forensics may still establish an
H3b/H4/H6-class defect for such targets). Bug-vs-by-design classification for
H0/H6b/H7 rows is adjudicated against the written criterion above and logged
before any D spec exists.

### 3.6 Controls (run first; readings computed only after the family passes)

  C0a basis reproduction: recompute J0 and I_acs from the pinned artifact and
      match the build's published battery lines digit-for-digit.
  C0b gate replay: reproduce every needed per-pattern gate bit-identically
      (state digests) and verify E2 numerically on fit rows via repeated
      categorical draws against the exact conditional variance.
  C1  RECLASSIFIED as H2's scientific probe (not an instrument gate): 5-fold
      household-clustered cross-fitting, 4 repeat partitions (20 folds),
      production complete-case and availability masks reapplied per fold;
      report fold/refit variance; unsupported cells marked, never zero-expected.
  C2  fixed-row paired intervention, frozen: target child_support_received,
      its largest-share pattern, column = the employment-income feature
      (person roster) — donor fit rows transformed x → 1.25·x (clipped at the
      donor observed max); oracle = exact paired per-row gate-probability
      difference; no downstream rerun; seed family `qrf-drift-v2|C2|replicate`.
  C3  same, chained column: child_support_expense set to 0 on its drawn
      carriers among the same rows; oracle likewise exact and paired.
  C4  no-change control: the full §3.2 machinery on untransformed data must
      report every contribution within threshold of zero.
  C5  P0 mask-recovery fixture: a synthetic mini-frame with known masks must
      be recovered exactly.
  Pass rule: thresholds derived at D0 from a 5% family-wise false-failure
  target (Šidák across the enumerated control statistics) against analytic
  SEs; C2/C3 additionally carry a separate must-detect (power) condition on
  their known induced effect. A C0/C4/C5 failure invalidates the instrument:
  fix the documented code defect, log the amendment, refreeze with FRESH
  control seeds, one rerun. A C2/C3 failure invalidates the attribution layer
  (P2) only; L0 and the T-ledger stand if C0 passed. C1 never gates the
  instrument (it is evidence, not calibration).

### 3.7 Rungs, support, noise (bound at D0)

Primary decomposition rung: the candidate-25 **pre-calibration** transfer
checkpoints (they exist and are retained; the 25% pool completed and failed
only terminal gates). 1% baseline1pct is the cross-rung consistency check for
the targets readable there. Support floor: 50 clone-deduplicated unique
positive source rows per origin per leg (physical mirror-clone counts roughly
double; the unique convention is the binding one); legs under the floor at the
primary rung report "insufficient support", full stop. Noise: decomposition
rows carry delta-method analytic SEs built from binomial/Kish-deff components
and E2's exact draw variance; loading/dominance thresholds use k = 3 SEs with
Holm within each probe family (the multiplier and the family enumeration are
D0 constants). Replicate SDs for arm metrics come from §4.3 (the v1 "pkg1/pkg3
r2/r3/r4 repeat builds" DO NOT EXIST; nothing may cite them).

**D0 (one commit, before dispatch):** pin by path + SHA-256 + JSON pointer:
baseline1pct pool.h5 and its bank checkpoints; candidate-25 checkpoint root
(config 3847d30e…) and per-target checkpoint digests; pkg3 (diff context
only); the per-target per-pattern regime matrix; the target-specific
authorized/imputed receipts (calibration-receipt kinds matched specifically,
not bare "post_transfer"); per-target unique and physical positive-row counts
per origin/leg at both rungs; Kish deff; the E10 boundary-mass table; the
weight-calibration ratio cap read from the calibrate config; the frozen
predictor matrix and applicability matrix; the declared control-statistic
enumeration and derived thresholds; arm B's code pin and A/B/C/D receipt-check
fields (§4.2); and the integrity assertion that baseline1pct terminal values
equal checkpoint raw draws on drawn rows (no other edit path).

## 4. Mission 2 — arm validation

### 4.1 Arms

  A calibrated incumbent. 25% column: candidate-25 (gate-red is a recorded
    fact, not a disqualifier for comparison; never rebuilt here) and/or the
    live release via the head-to-head tool. **A has no valid scoreable 1%
    artifact** (both existing 1% incumbent pools failed gates pre-release), so
    A is absent from the 1% rung and every A clause activates only at 25%.
  B parsimony: plain QRF + weight calibration. Code input of record: branch
    `parsimony-qrf-only` at 2d973984 (worktree `_worktrees/microcosm-parsimony`).
    Doctrine, frozen: non-negotiable semantic constraints (weeks-requires-UC,
    adult-care reconciliation, codec/structural rules) are part of variable
    semantics and stay in EVERY arm; only the margin-calibration treatment
    varies. D0 verifies what the branch actually removed; if it stripped
    semantic constraints, the branch is corrected to parity BEFORE building
    (code parity, not tuning) and the correction is logged.
  C two-step closed-form corrections, spec frozen here:
    - Roster: late_transfer match_reference targets only; preserve_recipient
      targets (disability_benefits; unemployment_compensation) get no gate
      correction, mirroring arm A's own carrier policy.
    - Gate stage: ONE δ per target per correction-leg, applied globally
      across patterns (preserves cross-pattern heterogeneity in logit space),
      solved by monotone bisection so the recipient scope's weighted mean
      corrected class probability equals the same clone-0 reference share the
      #742 receipts use (`carrier.reference_positive_share`). Regimes:
      ZERO_INFLATED_POSITIVE/NEGATIVE — binary-class logit offset;
      THREE_SIGN — joint (δ+, δ−) softmax reweight q_c ∝ p_c·exp(δ_c), δ0=0,
      solved against both leg margins; SIGN_ONLY — single positive-vs-negative
      logit (nonzero total not adjustable); POSITIVE_ONLY/NEGATIVE_ONLY/
      DEGENERATE_ZERO — no-op (a class absent from training is never created).
      Constraint clamping precedes the solve (e.g. p+ := 0 where UC ≤ 0);
      infeasible targets emit INFEASIBLE with capacity semantics receipted.
    - Amount stage: transform the SAME uniform vector u the production draw
      consumes as u^(1/a) (RNG stream, gate uniforms, and chain state
      untouched — same-seed pairing survives), per leg, a ∈ [0.05, 20], solved
      by bisection so the drawn weighted leg mean matches the clone-0
      reference leg mean (declared statistic: mean, because the ONE surface is
      sums), relative tolerance 1e-4; solve against decoded pre-structural
      values, then measure the post-structural residual — beyond tolerance
      emits INFEASIBLE_STRUCTURAL and the target is C-ineligible. Receipts:
      source-uniform digest, transformed digest, RNG state, bracket, solution,
      residual. Five conditional quantiles mandatory so the variance cost is
      visible.
    - Eligibility per target per §3.5 (no defect-classified material row).
  D root-cause fix(es): the union of named per-target defect fixes as one
    branch; plain QRF + the fixes, no adjustment layer. Pre-registered
    counterfactual candidates from P3, if implicated: full-source and
    sign-stratified producer sampling (the 5k cap), pattern-collapse repair.
    No D+C hybrids.

Every arm built here (B, C, D — and any A instance) gets a mechanical receipt
check: the build manifest's sample fraction/seeds, clone-attachment seed,
epochs, and provenance-pin SHAs diffed against `run-candidate.sh`'s record; a
mismatch voids that arm's column.

### 4.2 Metrics and endpoints

  Primary endpoint: post-weight-calibration **loss on the ONE target surface**.
  Noninferiority guard: %-within-10, margin 1.0 point (product constant,
  frozen; not an SD multiple).
  M-2 degeneracy predicate, per §1 target/leg, evaluated for EVERY arm
  including B, at fixed pre-calibration design weights: PASS iff
    (i) the leg meets the §3.7 support floor (else DEFER, re-tested at 25%);
    (ii) weighted carrier incidence > 0 while the clone-0 reference leg share
         is nonzero (zero carriers = automatic FAIL);
    (iii) the arm's carrier mass leaves the variable's ONE-surface sum target
         (where one exists) reachable within the D0-bound weight-ratio cap;
    (iv) for challengers: no regression below the same-seed arm-B value minus
         2× the §4.3 replicate SD.
  At D0, the predicate is applied on paper to the already-known §1 numbers and
  the resulting pass/fail/defer table per arm is published BEFORE any build —
  the threshold's consequences are transparent, not discovered.
  M-3 battery (incidence + five quantiles): diagnostic only, never arbitrates.
  M-4 wall-time per stage: cost axis, from build logs.
  S-1 conditional-structure regressions and S-2 variance-shrinkage: declared
  secondary, non-arbitrating, reported for every arm.

### 4.3 Noise for arm metrics

Three same-config, different-seed 1% builds of arm B, scored on the battery
AND the ONE surface, give the replicate SDs (ddof = 1, χ-inflation h(3) = 1.6);
25% bands scale by √(0.01/0.25). Bands and floors are stated per rung in the
rules; comparisons are always same-rung, paired seeds, simultaneous CIs from a
seeded household-level paired bootstrap (B = 1000, percentile).

### 4.4 Decision rules (mechanical; emit one outcome label)

  0. All comparisons same-rung. 1% rung compares B/C/D; A joins at 25% only.
  1. If D exists: D WINS iff noninferior on loss to the best arm (within the
     rung's band) AND passes M-2 (a removed defect dominates an added layer at
     equal accuracy).
  2. Else B is VALIDATED iff noninferior on loss to every eligible arm AND
     passes every M-2 leg. If B fails M-2, B cannot be validated regardless of
     loss — the failure table routes to Max as a B-as-shipped degeneracy
     finding (a product finding, not a ruling on the parsimony doctrine; the
     flip remains Max's).
  3. Else an arm WINS iff superior on loss beyond the band AND passes M-2 and
     the guard; the scorecard with the loss delta, M-2/M-3 tables, and S-1/S-2
     costs goes to Max (this experiment never flips anything).
  4. Ties: larger M-2 passing set wins; then fewer moving parts (B ≻ D ≻ C ≻ A);
     then M-4. Exact equality → INCONCLUSIVE.
  5. All arms fail M-2 → NO WINNER; all failure tables to Max.
  Outcomes: WIN_A / WIN_B / WIN_C / WIN_D / INCONCLUSIVE / NO_WINNER.
  Promotion to 25%: an arm must clear its 1% gates artifact and hold every
  measurable M-2 leg vs its own 1% standing.

### 4.5 Which margin is "right" (unchanged doctrine)

Donor-margin fidelity is a convention, not truth; the ONE target surface is
the only arbiter; no new truth sources enter here. Under H3a the drift is the
QRF answering correctly and "fixing" it toward ASEC margins would be wrong —
which is why M-2 is a degeneracy floor, never a fidelity band.

## 5. Discipline

Unchanged from v1 (no tuning anywhere; C's parameters closed-form from
declared references, frozen pre-scorecard, receipted; off-chain env; sol lanes
headless/no-network with HEADLESS blocks; every number traces to script +
digests; publish/promote never; Max flips latest) with three corrections:
Phase 0's compute includes bounded model refits (per-pattern HGB gates, C1's
fold fits) — still no pool builds, run under the RAM-reclaimable gate at low
priority while anything owns the host; control seeds burn on refreeze (§3.6);
and the §3.6/§3.5/§4.2 threshold constants live in the D0 commit, not in lane
charters.

## 6. Order of work

  D0    bind §3.7's constants and pins; publish the §4.2 paper table; commit.
  P-lane Phase-0 sol lane on the pinned 25% checkpoints: C0/C4/C5 first, then
        C2/C3, then P0–P7 per target; per-target per-leg verdicts per §3.5.
        (First result expected: the φ = 1 check from receipts.)
  Gate  defect verdicts → arm D spec; eligibility → arm C spec; both frozen
        and committed before any arm build. B parity check (§4.1) resolves.
  1%    B ×3 replicates (§4.3) + C/D same-seed; §4.4 at the 1% rung for
        GO/HOLD; A absent.
  25%   finalists only, post-candidate-chain, head-to-head
        (`tools/score_us_release_head_to_head.py`, #748) with the live
        incumbent column; multi-column scorecard to Max.

---

## Amendment v2.1 (2026-08-26, logged pre-Phase-0)

Trigger: the D0 binding lane (sol run 20260826-081114-d0-binding; outputs
`experiments/qrf_drift_validation_d0.{md,json}`) correctly refused to invent
four constants §3.6/§3.7 left unspecified, and bound facts that scope two
rules. No Phase-0 reading exists; these resolutions are specification, not
tuning. Nothing in §3.1–§3.5's identities, estimators, register, or §4.4's
rules changes.

**A1 — C4 control family and per-prior sub-attributions.** The 36 per-leg G3
per-prior sub-attributions ARE C4 control statistics: K = 214, per-statistic
two-sided Šidák z = 3.673063850314496 (family-wise 5%), as computed in D0-8.
The per-prior estimator, frozen: one-at-a-time paired substitution of each
prior column alone from the same drawn donor row (all else at recipient
values), reported as marginal per-prior contributions; they do NOT sum to
G3's Shapley total, and the gap is reported as "G3 within-group interaction",
never allocated.

**A2 — Holm probe families.** F1: the §3.1 ledger rows, one family per
target × leg. F2: the §3.2 Shapley contributions plus A1's per-prior
sub-attributions, one family per target × leg. F3: the P5 concentration
tests, one family across targets. F4: the P7 GQ rows, one family. Loading
threshold k = 3 SEs, Holm within each family as enumerated here.

**A3 — C2/C3 must-detect (power) conditions.** The oracle is exact (E2), so
power is a Monte Carlo question: replicates scale until the MC SE of the
recovered effect is ≤ oracle/10, capped at 10,000 replicates; if the cap
binds, the control is UNDERPOWERED and fails closed (re-specified with a
larger declared magnitude via logged amendment). Detection requires the
recovered effect within 3 MC SEs of the exact oracle AND the oracle effect
exceeding 5× that statistic's C4 null threshold.

**A4 — C5 mini-frame.** Deterministic synthetic frame: 60 person rows in 20
households across 2 availability patterns; per-row provenance fixed by
construction — 40 QRF-drawn (null-before), 10 native nonnull, 6
outside-authorized, 4 undecoded; values seeded from SHA-256 of
`qrf-drift-v2|C5|row-<i>`. Exact-match booleans (8): per pattern, S_q mask
equality, S_o mask equality, φ equality, path-census count equality. These
are exact checks outside the Šidák family (consistent with D0-8's
enumeration).

**A5 — M-2(iii) scope.** D0-9's deterministic census: only
spm_unit_energy_subsidy and unemployment_compensation carry ONE-surface
targets. Clause (iii) is evaluated only for those two, and only at a rung
where the arm's release stage compiled its coefficient row; otherwise the
clause is excluded from the conjunction and the row is marked
NOT-EVALUABLE(iii). The cap is bound: max_weight_ratio = 5.0 (D0-6).

**A6 — accepted absences.** baseline1pct and pkg3 recorded no build commit;
their identity is the D0-0 content digests plus the D0-1 gate cross-check
(72/72 exact) and, for baseline1pct, the D0-4 raw-draw/terminal equality.
This is accepted; no further commit archaeology.

**A7 — D0 facts that close or open register rows at receipt level** (Phase-0
mask-level confirmation still runs): φ = 1 for all nine targets
(authorized == imputed, zero unmodeled/residual — H0 dies at receipts);
pattern collapse census 0/36 (the E8 collapse sub-row of H7 is empty on this
build); T5 is REAL and quantified pre-Phase-0 — pre_subsidy_care_expenses
has 183 rows drawn positive and zero in the terminal artifact (adult-care
reconciliation; D0-4 FINDING) — while all eight other targets are bitwise
raw == terminal on baseline1pct; arm B parity violations CONFIRMED (D0-10):
the parsimony branch removed the weeks-requires-positive-UC recipient rule
and the canonical max_targets_per_fit guard — both restored before any B
build per §4.1's parity doctrine. SEILY's negative leg has 48 unique donor
carriers at 25% (floor 50): that leg is reported with SEs but formally
DEFERred by the frozen §3.7 rule, at both rungs.
