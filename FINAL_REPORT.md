# Final report: retirement predictor factorial

## Outcome

Implemented both frozen-gate treatment arms as independently runnable snapshots
off `origin/main` (`164027e2`):

- removal-only at `1a8ad451c6eff17d405ef75cbdd014de72447153`;
- broad-addition-only, retaining the direct Social Security and retirement
  predictors, at `539e415defb27bf103a40081239f123ce9d76c6d`.

Both snapshots are independently reviewed and complete-suite green. No band,
threshold, seed, fold, comparator, estimator, target order, or late-transfer
predictor contract was relaxed or replaced.

The code and static `f001`/seed-578 wiring proof are complete. The artifact
measurement portion is not: no cold 1% build was launched because the existing
1% stage receipt records 84,729,479,168 bytes peak RSS (78.91 GiB), while this
lane requires every process to remain below 15 GiB. Therefore all 16 after
values are honestly `NOT_RUN_RSS_CAP / not measured`, and this report makes no
claim that either arm measurably improves a check. Starting a known-over-cap
path—or treating a guard kill as a result—would violate the standing order and
would not yield valid experimental evidence.

No 25% build was run. The owner-run protocol is in
[`experiments/retirement_factorial/OWNER_25PCT_CHARTER.md`](experiments/retirement_factorial/OWNER_25PCT_CHARTER.md),
and is locked until a memory-safe cold or authenticated-resume path is first
demonstrated under its fail-closed guard.

## Treatment isolation

The removal snapshot changes only the early person/`puf_tax_itemization`
optional predictor surface: it removes
`__acs_transfer_social_security_income` and
`__acs_transfer_retirement_income`, leaving employment, self-employment,
household-head, and tenure. Every other early family retains its realized
baseline surface, and the late transfer retains the legacy call without an
explicit `predictor_sets` argument
(`1a8ad451:packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:151-167,374-403`;
`1a8ad451:packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:7746-7762,8509-8522`).

The broad snapshot restores those two direct-income predictors and adds
exactly 14 synthesized non-veteran predictors: marital status, relationship,
household count, six disability flags, usual hours, weeks worked,
self-employed-worker status, Medicare coverage, and foreign-born status.
Investment remains excluded. The early person/PUF tuple has exactly 20 ordered
columns; all other early families and the late transfer remain baseline
(`539e415:packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:191-212,438-467`;
`539e415:packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:8512-8524`).

The broad snapshot includes the minimum supporting donor/recipient surface:
reviewed ASEC mappings, required ACS raw columns and decoding, canonical source
ownership, a recipient-only raw-source fence, and a guarded `uint64`
availability-pattern code so 20 optional positions cannot alias
(`packages/microcosm-build/src/microcosm/build/us_runtime/cps_carried.py:114-151,160-337,581-741`;
`packages/microcosm-build/src/microcosm/build/us_runtime/acs_pums.py:72-99`;
`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:275-324,1991-2006,2199-2488`;
`packages/microcosm-build/src/microcosm/build/us_runtime/multispine_pool.py:637-640,728-741,2196-2211,2694-2744`).

## Safe f001 wiring proof

The proof invokes the pre-input configured-identity and canonical stacked
authority logic without reading or materializing survey frames. That identity
binds the six input hashes, `sample_fraction=0.01`, `sample_seed=578`, clone
controls, and authority, then routes each configuration to its own checkpoint
namespace
(`tools/build_us_multispine_pool.py:1031-1040,1150-1178`).

| Arm | Early person/PUF optional count | Authority SHA-256 | Gap-fill-plan SHA-256 | Configured f001 namespace digest |
|---|---:|---|---|---|
| removal-only | 4 | `16892c623844c21955ddcd4b39b829613db749b195922cbe2b5337aeb8c4cbdd` | `6ad7b75b193950cfb273daa1660df7e94440cc24e0806963bff5c333a94b0fdd` | `490866d5bfdc5981e6ff376375f0d414ed3800bb7c81abb98d27d41128f26549` |
| broad-addition-only | 20 | `7f6eab189fa51627c4e78c3cfcd2517f723a909d9197e538fbfec888261d564a` | `642646981e96fe67cc29e687a8a8362691bcc571c5c491426243e836f16202d6` | `adce8ee394cc2315422c00f3cc2838a866215e3a6ff90cb79a55b68c7a6c4c95` |

Both receipts are canonical and report that the live gap-fill-plan digest
matches its declared digest. They prove exact ordered wiring and cache
separation at the requested 1% controls. They are not build artifacts, gate
verdicts, or measurements. The full receipt and reproduction method are in
[`experiments/retirement_factorial/F001_WIRING_PROOF.md`](experiments/retirement_factorial/F001_WIRING_PROOF.md).

## Sixteen assigned checks: before and after

The before column is the official f025 gate artifact (SHA-256
`685cad63d4dc62234da72501c5a3ce9ec5a81fcd3f7b412b61474a9c1d8b423b`).
Every baseline row is `BLOCKER / FAIL`. The criterion values and full support
context are preserved in
[`experiments/retirement_factorial/ASSIGNED_CHECKS.md`](experiments/retirement_factorial/ASSIGNED_CHECKS.md).

| Ordinal | Exact check ID | Criterion | Before f025 | Removal f001 after | Broad f001 after |
|---:|---|---|---:|---|---|
| 7 | `person/model_required_numeric/tax_exempt_private_pension_income[clone_0]/positive#incidence` | incidence | 1.5540575408000976 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 19 | `person/puf_tax_itemization/taxable_private_pension_income[clone_0]/positive#incidence` | incidence | 1.5633139716502966 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 20 | `person/puf_tax_itemization/taxable_ira_distributions[clone_0]/positive#incidence` | incidence | 1.3692265605479346 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 21 | `person/puf_tax_itemization/social_security_retirement[clone_0]/positive#quantile` | QED | 0.5399065173295705 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 22 | `person/puf_tax_itemization/social_security_disability[clone_0]/positive#incidence` | incidence | 0.777259623970176 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 23 | `person/puf_tax_itemization/social_security_disability[clone_0]/positive#quantile` | QED | 1.3265580996694013 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 24 | `person/puf_tax_itemization/social_security_dependents[clone_0]/positive#incidence` | incidence | 1.6270067039916964 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 25 | `person/puf_tax_itemization/social_security_dependents[clone_0]/positive#quantile` | QED | 1.255813953488372 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 26 | `person/puf_tax_itemization/social_security_survivors[clone_0]/positive#quantile` | QED | 0.9842613410924481 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 76 | `person/source_operator_retirement_distributions/keogh_distributions[clone_0]/positive#incidence` | incidence | 0.0 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 77 | `person/source_operator_retirement_distributions/taxable_401k_distributions[clone_0]/positive#incidence` | incidence | 0.7928580784010778 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 78 | `person/source_operator_retirement_distributions/taxable_401k_distributions[clone_0]/positive#quantile` | QED | 0.46153846153846156 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 79 | `person/source_operator_retirement_distributions/taxable_403b_distributions[clone_0]/positive#incidence` | incidence | 0.7260054960806753 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 80 | `person/source_operator_retirement_distributions/taxable_403b_distributions[clone_0]/positive#quantile` | QED | 1.4639175257731958 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 81 | `person/source_operator_retirement_distributions/taxable_sep_distributions[clone_0]/positive#incidence` | incidence | 17.073910540208754 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |
| 82 | `person/source_operator_retirement_distributions/taxable_sep_distributions[clone_0]/positive#quantile` | QED | 1.7696335078534031 | NOT_RUN_RSS_CAP / not measured | NOT_RUN_RSS_CAP / not measured |

Count invariant: 16 rows = 9 incidence + 7 QED, covering 11 physical legs.

## Verification receipts

- Required `uv sync --all-packages --extra us`: attempted first; default cache
  was sandbox-denied, then a `/tmp` cache retry stopped at locked dependency
  download because network/DNS is unavailable. No lock or dependency file
  changed.
- Baseline complete suite: 6,525 collected, exit 0. Focused QRF-chain suite:
  26 passed in 302.42 seconds.
- Removal snapshot: targeted suites green; complete suite 6,535 collected,
  exit 0; repository-wide `ruff check .` and diff hygiene clean.
- Broad snapshot: 650 affected checks green; complete suite 6,571 collected,
  exit 0; repository-wide `ruff check .`, diff hygiene, changed-file format,
  byte-compilation, and frozen-control scan clean.
- Repository-wide `ruff format --check .` retains 49 pre-existing failures in
  unrelated files; no unrelated formatting was applied.

The provisioned arm-split virtual environment was used only as the interpreter,
with all five package roots forced to this worktree through `PYTHONPATH` and
`LOKY_MAX_CPU_COUNT=1`.

## Resource evidence and handoff

The block is empirical, not speculative:

- historical f001 stage profile:
  `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/smoke-f001-r10/populace_us_2024_stacked_pool_verify.checkpoints/stacked/2e45c4d60f66b4321bc00ffa22816470bf162c59fd91956514832f97e066ed3c/primary-qrf/stage_profile.json`,
  `peak_rss_bytes=84729479168`;
- historical f025 order-arm supervisor:
  `/Users/maxghenis/PolicyEngine/_worktrees/microcosm-arm-split/_buildo-runtime/out/stacked-f025-arm-order-r1/build.status.json`,
  `max_rss_raw=81026367488`.

The owner charter pins both implementation SHAs, the six input paths and
hashes, frozen OOS config hash, baseline artifacts, exact serial command, full
artifact/report schema, and abort conditions. It requires a 14 GiB fail-closed
root-plus-descendant guard and expressly prohibits the Logbook predecessor
argument and any contact with `logbook-pending-chain.txt`.

## Commits and publication

- `eac44dbe` — start the committed state/done/next journal.
- `1a8ad451` — isolate the removal-only arm.
- `539e415d` — isolate the broad-addition-only arm.
- `6d5efead` — record the exact check ledger, f001 wiring proof, owner charter,
  lane notes, and final report.

Nothing was pushed. The owner retains publication authority.

---

# Historical base report: microcosm #462 register alignment

## Outcome

Completed the split-PR remediation on `loss-contract-alignment`, based on
`origin/main` at `7b6e10b`. The change is now register alignment only: one
shared critical-target register, one shared congressional-district classifier,
two consumers, builder contract-row gating, and behavioral containment of the
publish contract.

The critical-row loss multiplier was removed entirely per
[microcosm#492](https://github.com/PolicyEngine/microcosm/issues/492). There is no
constant, CLI option, validation, loss overlay, telemetry, diagnostics/scorer
provenance, or historical replay pin left. `_fiscal_target_loss_weights` is
source-identical to `origin/main`, and its output therefore preserves main's
bit-level behavior for the same registry and family multipliers.

## Sol round-1 findings

1. **Table 1.4 selector parity:** removed the builder-only
   `accepted_name_prefixes=("irs_soi.",)` constraint. The adapter now has
   exactly the shared requirement's substring and suffix selectors. The
   outside-prefix reproduction is builder-rejected.
2. **Congressional-district parity:** added exported, stdlib-only
   `is_congressional_district_target(name, metadata)` and made the publisher
   and builder classifiers thin wrappers. It ORs layout dimension, source-id
   token, geography level, geography scope, truthy CD GEOID, and name token.
   The builder's exact/semantic, Table 1.4, and zero-support paths now see the
   same registry metadata.
3. **Recorded relative-error shape:** a matched row with missing/`None`
   `relative_error` now fails with the publish-contract message instead of
   silently passing after recomputation. Existing non-numeric and stale-value
   checks remain.
4. **Behavioral anti-drift:** the load-bearing test now runs adversarial rows
   through both consumers for exact-name, family+role, Table pattern,
   missing/non-finite values, and a disallowed incumbent escape at the 0.25
   hard stop. A production Ledger compile supplies six separate CD evidence
   rows; builder and publisher exclude identical six-name sets and counts.
   Field comparisons remain as fast checks, and any added conjunctive prefix
   is proven to trip the guard.

The [#490](https://github.com/PolicyEngine/microcosm/issues/490) medical 0.25
adjudication tolerance and its adjacent comment in `us_critical_targets.py`
remain byte-for-byte unchanged, as required.

## Reproduction receipts

The Table 1.4 prefix reproduction now returns:

```text
SOI Table 1.4 national dollar fit failed: other.table_1_4.all.bad_amount@2024: relative_error=1 exceeds 0.25 for SOI Pub 1304 Table 1.4 national dollar rows (soi_table_1_4_national_dollar_rows); target=100.0, final_estimate=200.0.
```

The missing-relative-error reproduction now returns:

```text
SOI Table 1.4 national dollar fit failed: irs_soi.ty2023.table_1_4.all.adversarial_amount@2024: missing recorded relative_error; the publish contract requires a numeric value.
```

The CD reproduction has the owner-mandated exclusion result:

```text
builder_excluded=True
publisher_excluded=True
builder_failures=[]
```

Calling that row "rejected" would contradict the required OR-union exclusion
semantics. The two malformed critical rows are rejected; the CD row is
symmetrically excluded by both consumers.

## Verification

The requested suite ran with `UV_NO_SYNC=1` to use the already-synced workspace
environment in the network-restricted sandbox:

```text
uv run --package microcosm-build --extra us --group dev python -m pytest packages/microcosm-data/tests packages/microcosm-build/tests/test_us_fiscal_refresh_builder.py packages/microcosm-build/tests/test_us_state_files_scorer.py -q
264 passed, 3 skipped (267 collected)
```

Additional receipts:

- Complete `test_gates.py`: passed.
- Required multiplier grep: zero Python hits.
- Ruff check: clean on all ten touched Python files.
- Ruff format check: clean on the eight non-exempt touched Python files; the
  two historical experiment files were not reformatted, as instructed.
- `git diff --check`: clean.
- The medical adjudication block compares byte-for-byte equal to pre-fix
  commit `068854d`.
- Pytest emitted non-failing macOS temporary-directory cleanup warnings; no
  test failed.

## Remediation commits

- `5077f95` — start microcosm#462 Sol remediation progress.
- `c48ba37` — remove the microcosm#462 loss multiplier per microcosm#492.
- `afa910a` — fix Sol finding 1 selector parity.
- `89f74f4` — fix Sol finding 2 CD classifier parity.
- `77040fb` — fix Sol finding 3 relative-error shape.
- `bad7145` — fix Sol finding 4 behavioral containment.
- `3c96514` — apply the finding-2 classifier's required Ruff formatting.

Nothing was pushed at the time of this report; the branch was subsequently
pushed and merged as #491 (2026-07-22).

The sandbox rejected writing
`/Users/maxghenis/PolicyEngine/_reviews/sol-491-fix-out.md` with `Operation not
permitted`; the full completion report is therefore committed here and will be
printed to stdout as the requested fallback.
