# Progress: QRF drift decomposition Phase 0 v2.2 rerun

## State

Phase-0 is complete as a terminal fail-closed report on the one permitted
rerun. C0a PASSED after all recorded reuse digests matched. C0b PASSED: E4
reproduced 36/36 gates and 12,909,037 sign rows with zero mismatches; A9
passed all 76 fit-row repeated-
draw cells and all 76 recipient production-realization checks. C5 recovered
all 8/8 fixture predicates exactly.

C4 cannot be run uniquely or interpreted as the registered zero null. A8 and
A10 leave the target-level pattern-by-GQ allocation, sampling estimator,
synthetic-recipient weights, GQ treatment, RNG stream mapping, and adaptive
details unbound. Independently, A10's statement that every stochastic output
has expectation zero is false for A1's 36 one-at-a-time prior marginals when
the substituted prior is correlated with retained predictors. This is a
specification/null-validity failure, not an observed numerical C4 failure.
Section 3.6 therefore blocks C2/C3, all readings, C1, and verdicts. No second
refreeze is authorized.

The opening standing orders require this committed journal and coherent-step
commits. They conflict with the embedded headless instruction to write only
the two Phase-0 outputs and make no commits. The opening standing orders are
being followed; the discrepancy is recorded in the final outputs.
There will be no push, pool build, publication, promotion, or logbook write.

## Done

- Read `experiments/qrf_drift_validation_design.md`, including v2.1/A8 and
  v2.2 amendments A9--A12, then both D0 bindings, then `CLAUDE.md`, in the
  required order.
- Began from the v2.2 amendment commit `51866036` and found the stopped run's
  two Phase-0 outputs untracked. During final review, HEAD advanced externally
  to A13 `849d8270`; its exact delta only updates the Mission-2 arm-B code pin.
  The report binds both the execution design (`91472a8e...`) and current A13
  design (`937939b2...`); no Phase-0 rule or disposition changed.
- Bound the terminal rule: any numerical C0a/C0b/C4/C5 failure on this rerun
  stops the instrument permanently; C2/C3 failures invalidate P2 only.
- Rehashed both C0a pool/gates pairs, the candidate assembled/transferred
  checkpoints, all nine target banks, and A12's three predecessor banks. Every
  digest matches D0/A12 and the stopped-run evidence, so v2.2 permits reuse of
  seedless C0a and E4. The execution-time design digest is
  `91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292`.
- Ran A9 exactly on fit rows with 1,000 PCG64 categorical draws per pattern,
  seeded from the first 64 SHA-256 bits of the v2.2 prefix. The repeated-draw
  maximum absolute z was 3.2334829878814775 and the frozen production maximum
  was 1.9263536173814484, both below 3.673063850314496. The frozen evidence is
  `/tmp/qrf_phase0_v22_c0b.json` SHA-256
  `1c7bfd65660b14068c4bc96fae4b8d270cb447ea8fbbe42c8ef982c5f1dbf542`.
- Constructed and independently read A11's fixture. C5 PASSED 8/8; evidence
  `/tmp/qrf_phase0_v22_c5.json` SHA-256
  `7f00827190276615806e26d5c76eda7c413c49640fb843988770f58056dc584c`.
- Audited C4 twice without running a full control. The implementation audit is
  `/tmp/qrf_phase0_v22_c4_spec_audit.json` SHA-256
  `78f005d1655941a07c8ff933644b63f2e575ab54a2fcb8a6661874e14f91fdd6`;
  the independent specification/null-validity audit is
  `/tmp/qrf_phase0_v22_c4_concept_audit.json` SHA-256
  `98960e2ab9827176d0d18ce21cfa5364097c6607aa40389a8638a8e42e4186b5`.
- Disclosed a non-authoritative C4 benchmark that ran before the A8 ambiguity
  was caught. It consumed indices 0--999 for one child-support-expense pattern
  under a plausible but unregistered per-pattern convention; it cannot be
  treated as a control result or silently reused. No other C4 cells and no
  downstream reading seeds were consumed.
- Rendered `experiments/qrf_drift_validation_phase0.md` SHA-256
  `5ecdb4501577413dd48e4801b2b1f9e04694ab8188c36d48b89f185b52d5c7d4`
  and its machine mirror `experiments/qrf_drift_validation_phase0.json`
  SHA-256
  `e6c07946b6fb74e707076677e8f6a04d59e60fbffb7b4a8b251330317fdfa9a0`.
- Validated JSON syntax and MD/JSON status parity; all 20 source digests; the
  historical git blob and current design; 9 target sections; 18 target-leg
  rows; all stopped ledger/attribution/probe/verdict placeholders; C0a,
  C0b, C5, and A12 counts; table column consistency; and no trailing
  whitespace. Two independent read-only reviews found no remaining blocker.

## Next

No execution or repository work remains. Hand off `CONTROLS_FAILED`. Do not
run C2/C3, readings, C1, another refreeze, a pool build, or any further C4
seed.

## Historical prior lane

The stacked-pool CD-vintage provenance journal previously at this path is
historical as of 2026-08-26. Its final text remains available in commit
`51866036` and does not describe the current task.
