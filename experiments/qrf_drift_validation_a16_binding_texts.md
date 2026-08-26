OPEN: 3, 4, 5, 6, 12, 13, 14, 15, 20, 22, 23, 24, 25, 26, 27, 29, 30, 31, 34, 35, 36, 37, 41, 42, 43, 46, 47, 49, 50, 51, 52, 54, 55, 56.

Finding 3 remains open because a positive-mass stratum may receive zero draws while A15.4 requires its estimate; replace the rule with “Give every positive-mass stratum one draw, allocate the remaining \(N-m\) draws by largest remainder in registered order, and fail closed if \(N<m\).”

Finding 4’s mathematics is sound conditional on nonempty strata—PPS with replacement plus unit-weight analysis targets §3.1’s weighted \(P_R/P_D\), and identically distributed \(R0\) and \(d(j)\) endpoints restore zero expected C4 total—but add “A15.4 replaces A14.1, A14.3, and §3.2’s carried-weight Hájek rules; use \(\bar y_h=R_h^{-1}\sum_t y_{i_t}\) and combine as \(\sum_h(W_h/W)\bar y_h\), with no carried or inverse-probability weights.”

Finding 5 remains open because the replicate origin and child-key byte grammar are absent; add “Use \(r=0,\ldots,R-1\), labels `qrf-drift-v2|P2|rows|<target>|<r>|<pattern>|<gq>`, `qrf-drift-v2|P2|donor|<target>|<pattern>|<r>`, and `qrf-drift-v2.3|C4|r0|<target>|<pattern>|<r>`, where `<gq>` is exactly `H`, `2`, `3`, or `U`, and initialize one fresh generator per complete label.”

Finding 6 remains open because “class present” can include the zero class although A14 gates sign legs; replace it with “Roster only present nonzero sign classes mapped to registered positive or negative legs, never the zero class, and freeze the ordered cell IDs before deriving \(K\) and \(z^*\).”

Finding 12 remains open because gate interactions can assign legitimate null-referenced Shapley effect to nonintervened groups, making the target-group-equals-total and other-groups-zero condition unattainable; replace it with “For each coalition \(S\), define \(\Delta(S)=W^{-2}\sum_{i,j}w_iw_j[p_+(z_S(Tx_i,x_j))-p_+(z_S(x_i,x_j))]\), where \(z_S\) takes groups in \(S\) from \(x_j\), Shapley \(\Delta\), pair identical \(i,j\) draws, and compare every recovered group with its own exact oracle.”

Finding 13 remains open because the ellipsis seed label and adaptive schedule are not executable; add literal `C2` and `C3` `rows`, `donor`, and `r0` labels, use \(r=0,\ldots,249\), check once at 250, and append only \(r=250,\ldots,999\) when any rostered oracle-error ratio lies in \([2,4]\).

Finding 14 remains open because six group checks are imposed while only two statistics enter \(K\), and “median contribution MCSE” is undefined; replace it with “Roster the six C2/C3-by-G1/G2/G3 oracle errors in \(K\), pass each when \(|\hat\phi_g-\phi_g^{oracle}|\le z^*MCSE_g\), and require \(|\phi_{target}^{oracle}|>5z^*MCSE_{target}\) at final \(R\), otherwise UNDERPOWERED.”

Finding 15 remains open because populated bank positions and aggregate receipts cannot establish rowwise owner authorization or target-null-before status; require deterministic recovery of both masks from a pinned pre-transfer checkpoint, rowwise equality with bank positions, and target-level failure when replay or equality is unavailable.

Finding 20 remains open because “documented from code at execution” delegates the operator mapping to implementers; require a pre-execution normative table fixing every operator-stage dataset, entity key, input and output column, weight, transformation order, and `NO_SURFACE` status.

Finding 22 remains open because order alone does not fix overlapping-pattern normalization or the native-to-fit weight transition; add “Start each pattern from an \(\alpha_k\)-weighted copy of J1, apply filters cumulatively, use inherited native weights before the weight-basis step and D0 fit weights afterward, and define each subrow as the preceding aggregate level minus the next.”

Finding 23 remains open because “production” implementations are not fully pinned and weeks clearing is assigned to both T5 and T6; pin every codec and structural function by path and source digest and state that semantic UC clearing is always T5 while T6 contains only the remaining #742 margin-calibration edit.

Finding 24 remains open because Kish and delta-method propagation remain underdefined; add “Treat \(\phi\) and \(\alpha\) as fixed, set \(n_{\mathrm{eff}}=(\sum w)^2/\sum w^2\) and \(\operatorname{Var}(\mu)=\mu(1-\mu)/n_{\mathrm{eff}}\), set covariance between distinct primitive levels to zero, propagate each exact §3.1 expression by its gradient, propagate NA, and use E2 only for T3.”

Finding 25 remains open because A15.25 includes the residual in F1 while A15.27 excludes it from Holm; replace it with “F1 contains exactly the applicable finite rows L0, B1, B2, and T1–T5, including exact zeros but excluding NA, unsupported, and residual rows.”

Finding 26 remains open because the boundary bridge is neither named nor formulated; define `B1|<stage>|boundary_bridge` as the same-row, same-weight difference between exact-leg incidence and the corresponding \(10^{-6}\) QRF-leg incidence, with zero for no boundary rows, NA for `NO_SURFACE`, and nonadditive B1-diagnostic status.

Finding 27 remains open because the residual’s summation order and `se` value are missing; add “Compute residual as \(D-(L0+B1+B2+T1+T2+T3+T4+T5)\) in that binary64 order from unrounded cells, set `se="NA"` and `family=null`, and use it only for deterministic closure.”

Finding 29 remains open because neither the null-referenced total nor the relative-error denominator is defined; add “For each target-pattern-leg define \(e_D=v_{real}(all)-P_D\), \(e_R=v_{real}(\emptyset)-P_R\), \(\Delta_{NR}=[v_{real}(all)-v_{real}(\emptyset)]-[v_{null}(all)-v_{null}(\emptyset)]\), and \(e_T=\sum_g\phi_g^{NR}-(P_D-P_R)\), gate all three residuals at three corresponding MCSEs, and require \(|\sum_g\phi_g^{NR}-\Delta_{NR}|\le10^{-9}\max(|\Delta_{NR}|,10^{-12})\).”

Finding 30 remains open because A15.30 gives two target-leg closure rows while A14.5 and A15.29 operate per pattern and require total closure; replace it with “Each target-leg F2 contains its three \(\alpha\)-aggregated group rows and \(e_D,e_R,e_T\) for every applicable pattern, while exact identities, priors, interactions, and dependence rows remain outside Holm.”

Finding 31 remains open because standardized-difference and Kish formulas are absent and a donor-copied value cannot fall outside that donor feature’s observed range; define weighted \(s^2=\sum w(x-\mu)^2/\sum w\), \(SMD=(\mu_R-\mu_D)/\sqrt{(s_R^2+s_D^2)/2}\), \(SE_\Delta=\sqrt{s_R^2/n_R+s_D^2/n_D}\), category-level indicators in D0 order, and D0-enumerated joint hybrid-domain predicates whose artifact-weighted violation share above 0.01 invalidates the pattern.

Finding 34 remains open because arithmetic neighbor weighting conflicts with §3.3’s weighted mean; add “A15.34 replaces §3.3’s weighted-mean phrase, every selected neighbor has weight \(1/k\), and ties use `(stable_source_row_id, D0_fit_ordinal)`.”

Finding 35 remains open because weighted decile boundaries and ties are unspecified; add “Within each pattern sort by `(score, stable_entity_id)`, assign row \(i\) to \(\min(9,\lfloor10(cumw_{before}+w_i/2)/W\rfloor)\), pool equal-numbered bins with original artifact weights, and designate bin 9 as bottom support.”

Finding 36 remains open because its denominator conflicts with §3.3 and permits 0/0; add “A15.36 replaces §3.3’s denominator, \(d_j=\sum_{i\in j}w_i(\bar p_{D,k(i)}-p_{R,i})/\sum_{S_q}w_i\), concentration is \(|d_9|/\sum_j|d_j|\) only when that denominator is positive, and it is NA when the denominator is zero or \(|T2|\le2SE(T2)\).”

Finding 37 remains open because removing concentration from Holm contradicts A2’s F3; add “A15.37 replaces A2/F3, F3 is retired, and H5 holds exactly when concentration is at least 0.5 and the corresponding F1 T2 row is loaded.”

Finding 41 remains open because repeat numbering and the precise permutation operation are missing; add “For \(r=0,1,2,3\), apply `Generator(PCG64(seed(label))).permutation` to globally stable-ID-sorted households and assign permutation position \(j\) to zero-based fold \(j\bmod5\).”

Finding 42 remains open because a PCG64 label is not itself an HGB `random_state`; add “Initialize PCG64 from the A15.5 seed, take one `random_raw()` value masked to its low 32 bits as the HGB integer `random_state`, and consume no C1 partition-stream state.”

Finding 43 remains open because unsupported-fold propagation is undefined; add “Any required unsupported fold makes that pattern-repeat and resulting target-leg statistic UNSUPPORTED without \(\alpha\) renormalization; otherwise concatenate all five held-out folds per pattern-repeat, then combine by fixed \(\alpha_k\) and average \(r=0,\ldots,3\).”

Finding 46 remains open because independent variance contradicts §3.5’s paired uncertainty; add “A15.46 replaces ‘paired uncertainty’, fixes covariance to zero, and defines \(SE(D)=\sqrt{SE(J0)^2+SE(I_{ACS})^2}\).”

Finding 47 remains open because the p-value distribution and zero-SE rules are absent; add “Use \(u=MCSE\) for MC-only rows and `se` otherwise, \(z=x/u\), \(p=2\Phi(-|z|)\), sort by `(p ascending, |z| descending, stable_id)`, apply Holm step-down at \(0.05/(m-i+1)\), treat \(u=0,x=0\) as \(p=1\), \(u=0,x\ne0\) as \(p=0\), and exclude NA from \(m\).”

Finding 49 remains open because probe order does not uniquely map overlapping evidence to official labels; add “Emit every qualifying additive parent ordered by decreasing share then stable row ID, designate the first as primary, and attach all satisfied mechanism tags in H0–H7 order under L0→H0, B1/B2→H7, T1→H1/H2, T2→H3a/H3b/H4/H5, T3→H6a, and T4/T5→H6b, with probes unable to create or reroute a parent.”

Finding 50 remains open because mixed or conflicting intent evidence has no authority rule; add “A D0-pinned owner-adjudication table is the sole authority, each classification cites its committed normative spec, matching receipt, and merged PR, and any absent or conflicting entry is UNRESOLVED.”

Finding 51 remains open because no-verdict routing does not define reported shares or cancellation at zero denominators; add “Let \(S=\sum|c|\), report all shares and cancellation as NA when \(S=0\), report shares \(|c_j|/S\) and cancellation `inf` when \(S>0,D=0\), and otherwise report cancellation \(S/|D|\), even for a nonmaterial gap.”

Finding 52 remains open because “precedence” does not say first-match versus cumulative and leaves mixed defect/unresolved cases contradictory; replace it with “Rule 1 alone is terminal; otherwise rules 2–4 are cumulative per parent, a loaded adjudicated defect with share at least 0.25 creates D and blocks C and B-validation, dominance is still reported, and a loaded UNRESOLVED parent with share at least 0.25 blocks C but neither creates nor cancels D.”

Finding 54 remains open because “disagreement” has no pairing or tolerance; add “Use no cross-rung pairing, flag numeric tension when \(|x_{25}-x_1|>3\sqrt{u_{25}^2+u_1^2}\) under independent rungs or when dominant labels differ, return NA when either cell is unavailable, and never gate on the flag.”

Finding 55 remains open because the flat ID collides across required dimensions and no normative schema or noncircular roster exists; require a SHA-pinned JSON Schema and pre-reading ordered required-ID manifest with explicit rung, target, pattern, leg, row, group, prior, GQ, decile, repeat, fold, and variant dimensions, rejecting duplicate, missing, and extra IDs and typing every control, raw/null/paired, escalation, mask/digest, K, and cross-rung record.

Finding 56 remains open because canonical ordering, digest scope, negative zero, negative infinity, and decision precision are absent; add “All decisions use unrounded binary64, canonical bytes are RFC 8785 UTF-8 JSON with statistics sorted by ID, negative zero normalizes to zero, nonfinite strings are exactly `NA`, `inf`, and `-inf`, lowercase SHA-256 covers the canonical bytes excluding its own field, and Markdown uses round-half-even to six significant digits and is never compared.”

The inconsistencies requiring explicit reconciliation are A15.4 versus A14.1/A14.3 and §3.2, A15.12–14 versus A3 and A14.6, A15.23 versus §3.1/E9 and A13, A15.25 versus A15.27, A15.30 versus A14.5, A15.34/A15.36 versus §3.3, A15.37 versus A2/F3, and A15.46/A15.50–52 versus §3.5; each later rule must expressly identify what it replaces.