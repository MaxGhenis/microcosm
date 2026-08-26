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

**A8 — §3.2 compute rule (pre-registered, not improvised).** At the 25% rung
each Shapley replicate evaluates on a seeded weighted-stratified subsample of
min(100,000, |S_q|) recipient rows (strata: pattern × GQ status; unbiased for
the weighted mean; the replicate spread's MC SE then covers donor-draw and
row-subsample randomness together). Replicates are adaptive with a fixed
escalation rule: 250 first; any target-pattern where a contribution's
|value|/MC-SE falls in [2, 4] escalates to the full 1,000; seeds unchanged
(`qrf-drift-v2|target|pattern|replicate`). C1 is scoped to gates (the H2
question is incidence generalization; no forests, no amount draws) and runs
after the ledger readings, consistent with §3.6's "C1 never gates the
instrument".

## Amendment v2.2 (2026-08-26, logged after CONTROLS_FAILED, before any reading)

Trigger: Phase-0 run 20260826-100441 stopped fail-closed
(`experiments/qrf_drift_validation_phase0.{md,json}`): C0a PASSED 72/72 and
the E4 gate replay PASSED (36/36 gates, 12,909,037 signs, 0 mismatches), but
C0b's E2 check, C4's null, and C5's fixture were not uniquely specified and
the lane correctly refused to choose. No reading was computed. Per §3.6 this
is the one permitted refreeze: ALL control seed prefixes bump to
`qrf-drift-v2.2|…` (reading seeds unchanged — none were consumed). If any
control fails NUMERICALLY on the rerun, the instrument is invalid-terminal
and the failure table goes to Max.

**A9 — C0b/E2 repeated-draw protocol.** Per pattern × sign class: R = 1,000
replicate categorical draws from the reproduced gate's probabilities, PCG64
seeded from the first 64 bits of SHA-256 of
`qrf-drift-v2.2|C0b|<target>|<pattern>|<replicate>`. Pass iff
|mean replicate weighted drawn share − expected E2 share| ≤ z*·SD_exact/√R
with z* = 3.673063850314496 (these 76 cells are the ones already counted in
K = 214), AND the frozen production draw's own single-realization |z| ≤ z*.
Zero-exact-variance cells (every row's p ∈ {0,1}) are exact checks outside
the z family: drawn share must equal expected exactly.

**A10 — C4 null construction.** The no-change null is a donor
self-substitution exchangeability null: run the full §3.2 machinery with the
recipient rows replaced by an independent seeded fit-weight-proportional
donor-row sample of the A8 subsample size, so source and target coincide by
construction and every stochastic contribution has expectation zero. Seeds:
`qrf-drift-v2.2|C4|<target>|<pattern>|<replicate>`. Pass per statistic iff
|contribution| ≤ z*·(its MC SE); the 20 deterministic empty-G3 outputs are
exact zero checks outside the z family.

**A11 — C5 fixture instance (unique by construction).** Rows i = 0…59;
household h(i) = ⌊i/3⌋ (20 households of 3); pattern p(i) = i mod 2; weights
w(i) = 1 + (i mod 7). Provenance by index: i ∈ [0,39] QRF-drawn (in scope,
authorized, null-before, finite raw draw = 100+i, decode succeeds);
i ∈ [40,49] native non-null (value 200+i; not null-before); i ∈ [50,55]
outside-authorized (null-before, no draw); i ∈ [56,59] undecoded
(authorized, null-before, finite raw draw = 300+i, decode fails). Expected
S_q = {i ≤ 39}, split by pattern; S_o = scope \ S_q; expected φ_p and the
path census follow arithmetically from the construction. One writer
serializes the fixture (mini bank + terminal frame) from this paragraph;
the production-path P0 reader recovers masks independently; the 8 A4
booleans compare them. Writer and reader must share no mask code.

**A12 — D0-0 supplement (accepted).** Three later-chain predecessor
checkpoints used by the E4 replay were hashed at first use and are hereby
pinned: adult-care predecessor bb2d1b15…, prior-year-income predecessor
724e1236…, model-required-numeric predecessor 0aa26da0… (full digests in the
Phase-0 report). The D0-0 "design sha" row records the pre-A8 file by
chronology; the operative design is always the current committed file.

**A13 — arm-B code pin updated (2026-08-26).** The §4.1 parity correction is
done: sol run 20260826-100442-bparity-fix restored the weeks-requires-UC
recipient rule and the max_targets_per_fit guard on `parsimony-qrf-only`
(restoration commit dbd8a657, evidence HEAD 95f48a08; ruff clean; full suite
7,334 passed / 78 skipped; #742 margin-calibration removal retained). Arm B's
code input of record is now **95f48a08**; the §4.1 build-time receipt check
binds against it.

## Amendment v2.3 (2026-08-26, after second fail-closed stop; no reading exists)

Run 20260826-105336: C0a PASS, C0b PASS (36/36 gates; 76/76 repeated-draw
checks — E2 numerically verified), C5 PASS 8/8 (diagnostic, adopted below).
C4 stopped on a REAL mathematical defect in A10 plus missing operational
bindings, both correctly refused. The lane also disclosed one
non-authoritative benchmark (child_support_expense/pattern_00, replicate
indices 0–999, unregistered size-478 convention; its three rows passed);
its streams are burned by the relabeling below, and every convention bound
here is a generic default chosen without reference to its values.

**A14 — C4 respecified (REPLACES A10 in full); estimator completions.**
A10's "every stochastic contribution has expectation zero" is FALSE for
partial coalitions: hot-deck hybrids decouple cross-group joints, so
per-group and per-prior quantities are nonzero under exchangeability
(counterexample recorded in the run-2 report). The corrected design:

1. Subsampling (completes A8). Per target, per replicate r: the S_q
   evaluation subsample of size min(100,000, |S_q|) is allocated across
   recipient strata (pattern × GQ class) proportional to stratum weighted
   share, integerized by largest remainder; within stratum, rows are drawn
   WITH replacement with probability proportional to artifact weight; every
   mean is a Hájek (self-normalized) weighted mean over the drawn rows.
2. Streams (PCG64; seed = first 64 bits of SHA-256 of the label):
   reading rows `qrf-drift-v2|P2|rows|<target>|<r>`; reading donor draw
   `qrf-drift-v2|P2|donor|<target>|<pattern>|<r>`; C4 synthetic-recipient
   rows `qrf-drift-v2.3|C4|r0|<target>|<pattern>|<r>`. The C4 null run
   consumes the READING donor-draw stream values (same d(j) per replicate —
   deliberate pairing for variance reduction; declared here).
3. C4 null run: identical machinery with the recipient rows replaced by
   R0 = a fit-weight-proportional with-replacement sample of the same
   per-pattern size from that pattern's donor fit rows, each drawn row
   carrying its donor fit weight (donor side has no GQ strata; allocation
   is per pattern only), Hájek means throughout.
4. GATED C4 statistics (Šidák family members): per target × pattern ×
   applicable leg, ONLY the null total effect v_null(all) − v_null(∅) —
   zero-expectation by construction (both ends are Hájek means over iid
   weighted donor draws) — plus the 20 deterministic empty-G3 exact zeros.
   All other C4 outputs (per-group Shapley, per-prior marginals under the
   null) are measured NULL BASELINES, never pass/fail.
5. Readings become null-referenced: every reported §3.2 contribution
   (per group; per prior) = raw real-run value − paired C4 null value,
   with MC SEs from the paired replicate differences. The closure check
   remains in the reading family: v_real(all) must estimate P_D within
   3 MC SE per target × pattern. A1's per-prior marginals are retained as
   DESCRIPTIVE null-referenced quantities only; the §3.4 G3 evidence is
   the null-referenced G3 Shapley row, never the marginals.
6. K and z*: the gated stochastic family = 76 C0b + 2 C2/C3 + the C4
   null-total cells counted mechanically from the D0-7 applicability
   matrix. Hand-counted K values are void; the run computes K by this
   rule, records the enumeration, and derives z* by the bound Šidák
   formula. Escalation (A8) triggers on the gated statistics of the
   target-pattern plus its null-referenced reading contributions,
   evaluated once at replicate 250 (any |value|/MC-SE in [2,4] → 1,000).
7. Adoption: run-2's C0a, C0b, and C5 PASSes are adopted as official on
   input-digest re-verification; only C4 (and the not-yet-run C2/C3,
   readings, C1) execute fresh.

## Amendment v2.4 / A15 (2026-08-26): complete operational bindings

Input: the whole-path unique-executability audit (sol run
20260826-114554-spec-audit, 56 findings, none numerical). Each finding is
bound below by its audit number. Where a finding exposed a defect, the fix
is named. No reading exists; nothing here was chosen with sight of any
result. The §3.6 fail-closed rule and every §3.5 verdict rule stand; A15
only makes them uniquely executable.

1. P0 mask recovery is instrument SETUP: masks/φ are computed first (they
   are deterministic and seedless), feed C4 allocation, and the ledger
   LEVELS stay sealed until controls pass. The P0 report emits in reading
   order.
2. GQ strata = {H, 2, 3, U(nprojectable)} via the entity's parent
   household TYPEHUGQ; SPM units project via their household.
3. Stratum order = (D0 pattern order, then H,2,3,U); largest-remainder ties
   break by that order; zero allocations to positive-mass strata are
   allowed; float accumulation in that fixed order.
4. DEFECT FIX (double-weighting): within-stratum sampling is
   weight-proportional WITH replacement and analysis uses UNIT weights
   within the drawn sample (Hansen–Hurwitz self-weighting); stratum
   estimates combine by exact stratum weighted shares. Applies to reading
   subsamples, C4's R0, and C2/C3 evaluation alike. This restores the C4
   null-total zero-expectation premise.
5. Seeds: first 8 bytes of the SHA-256 digest, BIG-ENDIAN uint64, into
   numpy PCG64; per-stratum child streams: label + "|" + stratum key;
   sampling via Generator.choice(replace=True, p=…) over rows in D0-2
   stable fit-row order (donor) / stable entity-id ascending (recipient);
   the shared d(j) aligns by drawn-row sequence position.
6. K counts one C4 null-total per target × pattern × class present in that
   pattern's D0-2 fitted regime (no support-floor exclusion).
7. C4 escalation triggers ONLY on C4's own gated statistics; reading (P2)
   escalation happens in the reading phase on its own statistics.
8. Escalation is per TARGET: any triggering pattern escalates every
   pattern of that target to 1,000 replicates.
9. MCSE = SD(ddof=1)/√R (paired versions use per-replicate differences);
   pass = |value| ≤ z*·MCSE; deterministic exact checks fail on any
   nonzero; MCSE = 0 with value 0 → no trigger, value ≠ 0 → fail.
10. C2 transforms the chosen pattern's exact fit rows, evaluated through
    the FROZEN gate (no refit); cap = that pattern's fit-row observed max.
11. C3's carrier mask = fit rows with OBSERVED child_support_expense > 0
    (the audit is right that fit rows carry observed priors).
12. C2/C3 validate the FULL A14 attribution route: synthetic recipient =
    the (transformed) fit rows; run null-referenced Shapley; pass =
    target-group contribution within 3×MCSE of the exact oracle (the
    fit-weighted mean per-row frozen-gate probability difference, signed)
    AND every other group within 3×MCSE of zero.
13. C2/C3 use the A14 stream scheme with `qrf-drift-v2.3|C2/C3|…` labels;
    R = 250 with the #8 escalation rule; A3's oracle/10 replicate-scaling
    clause is superseded by this design.
14. Power: |oracle| must exceed 5 × (z* × the cell's median contribution
    MCSE); otherwise UNDERPOWERED → larger declared magnitude via logged
    amendment. The two K-rostered recovery statistics are the two
    target-group recoveries.
15. P0 primary route = bank raw-draw non-NaN positions per target
    (position-aligned per D0-4) ∩ battery scope, cross-checked against
    D0-3 receipts and D0-4 digests; any disagreement fails that target
    closed. No assembled-checkpoint replay is required for P0.
16. Decode success = finite codec output; structural survival belongs to
    T5, not S_q; path census assigns first-failure in order
    authorized → null-before → drawn → finite-decode.
17. Empty S_o: I_o/SE = NA, L0 = 0, schema flag empty_set = true.
18. B1 = J0 − J1 as ONE additive bridge row; J0 and J1 each on native
    rows/weights (J1 = the stage's donor projection).
19. The producer ladder (P6) is DIAGNOSTIC: per-stage native weighted
    incidences with named populations; only aggregate B1 is additive.
20. Operator-specific stage dictionaries are documented from code at
    execution; template stages an operator lacks are omitted.
21. No full-pipeline replay: ladder stages read persisted surfaces only;
    stages with none are NO_SURFACE.
22. B2 = sequential telescope in the fixed order role/channel → family
    complete-case → pattern predictor complete-case → weight basis →
    pattern standardization; order-dependence disclosed.
23. Decoded surface recomputed from banked raw draws via the production
    codec; T5 recomputed via the production structural functions (weeks:
    the parity-restored recipient rule, pin 95f48a08; the incumbent
    embeds it in the calibration kernel = T6 there); recomputation
    disagreeing with the D0-4-proven baseline terminal fails that target
    closed.
24. P1 SEs: independent Kish-binomial per level; differences treat levels
    as independent (conservative), except T3 which uses the exact E2
    conditional variance.
25. F1 = top-level rows {L0, B1, B2, T1–T5} plus the residual row.
26. Producer intermediates use exact-zero classification; boundary mass
    found there adds the declared bridge row.
27. Residual computed at full precision; |residual| ≤ 1e-9·max(|D|,1e-12)
    else the run fails closed; residual is excluded from shares and Holm.
28. P2 official rows = target × leg G1/G2/G3; GQ strata combine by exact
    stratum shares, patterns by exact α_k.
29. Closure gates (reading family): v_real(all) vs P_D AND v_real(∅) vs
    P_R within 3×MCSE each; Shapley-sum-vs-total is an exact float check
    (≤1e-9 rel). Failure → that pattern's attribution NOT_VALIDATED
    (T2 itself stands via P_D − P_R).
30. F2 = G1/G2/G3 rows + the two closure statistics per target × leg;
    per-prior and interaction/dependence rows are descriptive.
31. Marginal audit is descriptive (not Holm): weighted means/proportions,
    standardized differences, Kish SEs, full-row scope; donor-support
    violations (substituted value outside donor observed range) > 1% of
    rows → attribution NOT_VALIDATED for that cell.
32. P5 uses effective gate columns (base + present priors) with
    state/tenure/boolean categorical semantics.
33. P5 numeric distance: fit-weighted inverse-CDF quartiles, |x−y|/IQR
    capped at 1; zero-IQR features cost 0 if equal else 1.
34. P5 k=25 nearest by distance, ties by donor stable source-row id;
    score = arithmetic mean of the 25 distances; pools under 25 rows use
    all rows and flag.
35. P5 deciles: within-pattern artifact-weighted deciles pooled by rank;
    bottom support = highest mean distance.
36. Concentration = |worst-decile sum of w·(p̄_D,pattern − p_R,i)| /
    Σ_deciles |decile sums|; inapplicable when |T2| < 2×SE.
37. The 50% concentration predicate is deterministic, outside Holm; H5
    additionally requires T2 loaded in the ledger.
38. P7 outcome surface = post-structural pre-calibration values (I_q's
    basis).
39. F4 = the two GQ-adjustment terms per target × leg, independent
    Kish-binomial delta SEs; empty strata inapplicable.
40. C1 clusters on the original support household id, one global
    partition per repeat shared across targets.
41. C1 splitter: households sorted by stable id, shuffled by PCG64
    (`qrf-drift-v2.3|C1|repeat-<r>`), dealt round-robin into 5 folds.
42. C1 fold gates seeded `qrf-drift-v2.3|C1|<target>|<pattern>|<repeat>|<fold>`;
    production regimes bind (no redetection); class-lost or failed fits →
    UNSUPPORTED cells, never zero.
43. C1 estimand = Hájek fit-weight mean of held-out class-ℓ proba minus
    observed leg incidence, pooled within repeat, α_k across patterns,
    averaged over 4 repeats.
44. C1 SE = between-repeat SD(ddof=1)/2; family F5 (one statistic per
    target × leg), 3×SE + Holm loading; descriptive for H2.
45. Verdict share universe = F1's top-level rows minus the residual.
46. Var(D) = Var(J0) + Var(I_acs), independent Kish-binomial
    (conservative, declared).
47. "Loaded" = |value| ≥ 3×SE AND two-sided Holm-significant at family
    α = 0.05; Holm ties by |z| then row name.
48. A named defect classifies its PARENT additive row's share for gating;
    diagnostics name the mechanism; no proration.
49. The root-cause label must be an additive parent row; probes only
    select among hypotheses consistent with it (order: P2 → P5 →
    marginal audit → C1); inconsistent probe signals are reported
    anomalies, never verdicts.
50. Bug-vs-by-design requires a pinned committed spec/receipt/PR
    reference; absent one, material defect-candidates are UNRESOLVED
    (block C for that target, create no D until owner adjudication by
    logged amendment).
51. |D| ≤ 2×SE(D) → "no material gap", no verdict, no gating; otherwise
    shares over Σ|c|.
52. Precedence: (1) no-material-gap; (2) qualifying defect rows create D
    and block C even without dominance; (3) dominance labeling;
    (4) material-but-UNRESOLVED blocks C without creating D.
53. Cross-rung matrix: baseline1pct, positive legs of
    self_employment_income_last_year and spm_unit_energy_subsidy;
    content = D, top-level rows, dominant label.
54. Cross-rung disagreement is diagnostic ("cross-rung tension" flag),
    never blocking.
55. The JSON is a flat statistics array keyed by stable ids
    (`<target>|<leg>|<row>`) with {value, se, mcse, family, gated,
    status} plus masks/digests/enumerations; Markdown derives from it;
    completeness = every enumerated id present.
56. JSON is authoritative (binary64 shortest-roundtrip; "NA"/"inf"
    strings; lowercase hex digests); Markdown displays 6 significant
    digits.

## Amendment v2.5 / A16 (2026-08-26): closure texts, supersessions, regress rule

Input: the A15 closure verification (sol run 20260826-121300-a15-verify; 34
items OPEN with proposed exact texts). A16 adopts the verifier's texts
verbatim for items 3, 4, 5, 6, 12, 13, 14, 22, 23, 24, 25, 26, 27, 29, 30,
31, 34, 35, 36, 37, 41, 42, 43, 46, 47, 49, 51, 52, 54, 56 — those
paragraphs of `battery-lanes/a15-verify.out` (SHA-256 recorded by the lane)
are incorporated by reference as binding text, with the file quoted in full
as an appendix of the Phase-0 report. The remaining four are bound as
follows, with rationale:

**A16-15 (P0 masks; owner-adjudicated).** The verifier's pre-transfer
checkpoint requirement is unsatisfiable: D0-11 proves no such checkpoint
exists. The bank-position route is retained as primary WITH three GATED
exact checks per target: (i) |S_q mask| equals the receipt's
authorized_null_rows exactly; (ii) the D0-4 lineage/alignment digests
re-verify; (iii) on baseline1pct, terminal equals raw on drawn rows (already
proven, re-asserted). Rationale: the transfer fills only null cells and the
banks' raw-draw NaN structure identifies drawn rows per target (D0-4);
rows with native values are never drawn and land in S_o. Any check failing
fails that target closed. This is an owner design adjudication made without
sight of any reading.

**A16-20 (operator table) and A16-55 (schema + ID manifest).** Both become
SEALED STEP-0 DELIVERABLES of the execution lane: before any statistic is
computed, the lane writes (a) the normative operator-stage table (every
dataset, entity key, input/output column, weight, transformation order,
NO_SURFACE status, with code anchors) and (b) the SHA-pinned JSON Schema
plus the ordered required-ID manifest with explicit rung/target/pattern/
leg/row/group/prior/GQ/decile/repeat/fold/variant dimensions; both are
digest-recorded in the report before readings begin, and completeness is
validated against them (duplicates, missing, and extras all reject).

**A16-50 (adjudication table).** The D0-pinned owner-adjudication table is
the sole bug-vs-by-design authority and STARTS EMPTY; every entry must cite
a committed normative spec, matching receipt, and merged PR; absent or
conflicting entries are UNRESOLVED (block C per precedence rule 4; create
no D). Entries are added only by owner-logged amendment.

**Supersession table** (each later rule expressly replaces the named
earlier text): A15.4+A16 replace A14.1/A14.3 carried-weight Hájek wording
and §3.2's "retain recipient artifact weights"; A16-12/13/14 replace A3's
oracle/10 scaling and A14.6's two-statistic C2/C3 roster (now six);
A16-23 replaces the §3.1/E9 placement of weeks clearing (semantic UC
clearing is always T5; T6 is only the #742 margin edit; A13's pin governs
the T5 implementation); A16-25 replaces A15.25 (residual excluded from F1);
A16-30 replaces A14.5's closure placement (per-pattern e_D, e_R, e_T);
A16-34/36 replace §3.3's weighted-mean neighbor phrase and concentration
denominator; A16-37 retires F3 (A2 amended); A16-46 replaces §3.5's
"paired uncertainty" with the independent-variance formula; A16-49/51/52
replace §3.5's precedence prose as written there.

**Regress rule (final).** From this amendment on, the execution lane does
not stop for specification gaps in NON-GATED (descriptive/diagnostic)
statistics: it resolves each by a deterministic default recorded in a
sealed report appendix BEFORE computing the affected statistic, and flags
the statistic `default_resolved`. GATED statistics (control pass/fail,
closure gates, Holm-family members, verdict inputs) still fail closed on
any ambiguity. This bounds the spec-iteration cycle without weakening any
gate.
