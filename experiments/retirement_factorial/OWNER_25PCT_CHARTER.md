# Retirement predictor factorial: owner-run f025 charter

## Status and authorization boundary

This is the fixed protocol for two owner-run 25% arms. It is a charter, not an
execution receipt. **No 25% build or gate was run while authoring it.**

Cold f025 execution is currently **not authorized** under the standing
`<15 GiB RSS per process` rule. A historical order-arm build recorded
`max_rss_raw = 81026367488` bytes (75.46 GiB) in
`/Users/maxghenis/PolicyEngine/_worktrees/microcosm-arm-split/_buildo-runtime/out/stacked-f025-arm-order-r1/build.status.json`.
A historical 1% stacked stage profile recorded `peak_rss_bytes = 84729479168`
in
`/Users/maxghenis/PolicyEngine/_buildo-runtime/out/smoke-f001-r10/populace_us_2024_stacked_pool_verify.checkpoints/stacked/2e45c4d60f66b4321bc00ffa22816470bf162c59fd91956514832f97e066ed3c/primary-qrf/stage_profile.json`.
These observations do not predict that every future implementation must exceed
the limit; they do make an unguarded cold f025 attempt inadmissible.

The owner may unlock the commands below only after a cold-build implementation
or resumable execution path has been demonstrated to remain below the hard
limit under the fail-closed guard specified here. An RSS stop is an aborted
measurement, never arm evidence.

## Scientific question and immutable treatment pins

The arm-split synthesis localizes the retirement regression to the bundle's
broad early-PUF predictor replacement or an interaction. It specifically calls
for a removal/addition factorial
(`/Users/maxghenis/PolicyEngine/_worktrees/microcosm-arm-split/experiments/phase_p_arm_split/SYNTHESIS.md:346-352,376-379`).
The two artifact code pins are immutable:

| Arm | Exact build revision | Treatment |
|---|---|---|
| removal-only | `1a8ad451c6eff17d405ef75cbdd014de72447153` | Remove only `__acs_transfer_social_security_income` and `__acs_transfer_retirement_income` from the early person/`puf_tax_itemization` optional set. |
| broad-addition-only, direct retained | `539e415defb27bf103a40081239f123ce9d76c6d` | Retain those two direct income predictors and add the reviewed broad non-veteran predictor set. |

At the removal pin, the baseline optional tuple names both direct predictors
and the family declaration removes exactly those names for early person
`puf_tax_itemization`
(`1a8ad451:packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:151-167,374-401`).
At the broad pin, the ordered 20-feature tuple retains both direct predictors
and adds marital status, relationship, household size, six disability fields,
usual hours, weeks worked, self-employed-worker status, Medicare, and
foreign-born status; that tuple is selected only for early person
`puf_tax_itemization`
(`539e415:packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:156-212,438-467`).

The declaration is frozen into each early gap-fill direction and passed
explicitly to the early transfer
(`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:1918-1952,7738-7760`).
The late transfer still calls `transfer_acs_inputs` without an explicit
`predictor_sets` argument, so neither arm contains the bundle's separate
late-PUF predictor swap
(`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:8273-8289,8498-8524`).
This wiring boundary must be authenticated from each built artifact's
authority, execution-contract, gap-fill-plan, and target-bank receipts.

Predictor order is part of the treatment: optional-feature positions define
recipient availability-pattern codes, and the ordered observed tuple enters the
pattern seed
(`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1991-2010,3564-3578`).
Predictions are applied only to recipient nulls and their imputed masks are
recorded
(`packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:1171-1234,3668-3697`).
Do not sort, substitute, or approximate either arm's predictor tuple.

## Owner preflight

Run the arms strictly serially: removal build, removal gate/report, then broad
build, broad gate/report. Never overlap either a build or a standalone gate
with the other arm. Use an exclusive owner lock covering the whole sequence.

Before each build:

1. Detach at the exact SHA above; require `git rev-parse HEAD` to equal it and
   `git status --porcelain` to be empty.
2. Run `uv sync --all-packages --extra us`, `uv run pytest`, and
   `uv run ruff check .`. Store command, exit code, start/end timestamps, and
   logs in the arm's supervisor receipt. Any nonzero result aborts the arm.
3. Require all six inputs below to exist and match their SHA-256 values before
   launch. The build driver independently verifies the same pins, and its
   checkpoint identity binds the verified inputs, sample fraction/seed, clone
   fraction/seed, stack manifest, and stacked authority
   (`tools/build_us_multispine_pool.py:1035-1105`).
4. Require the arm output directory not to exist. Do not reuse or overwrite an
   old directory or checkpoint tree.
5. Require no other Microcosm build/gate process and no prior owner lock.
6. Require `POPULACE_LOGBOOK_PREV_ROW_DIGEST`, `POPULACE_LEDGER_URL`,
   `POPULACE_LEDGER_KEY`, and `POPULACE_LEDGER_API_KEY` to be absent. Never pass
   `--logbook-prev-row-digest`. Never read, write, or reference
   `logbook-pending-chain.txt`. The driver otherwise resolves the predecessor
   from the CLI or environment
   (`tools/build_us_multispine_pool.py:520-525,3965-3977`).

### Fixed input ledger

| Input | Absolute path | SHA-256 |
|---|---|---|
| ASEC raw-stage H5 | `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/591-pawtyp-pool/asec-producer-checkpoints/asec_raw_stage.checkpoint.h5` | `51e9fafcd6f16140018fa90c7afbeb6d79008bfc8c122e437d23a399b30553fe` |
| ACS household archive | `/Users/maxghenis/PolicyEngine/_worktrees/populace-acs-clone/inputs/acs_2024_1yr/8281008e53de98f0ef81e7a2ee5a8725991dda1ecfd2713ead73246425e515d0/csv_hus.zip` | `8281008e53de98f0ef81e7a2ee5a8725991dda1ecfd2713ead73246425e515d0` |
| ACS person archive | `/Users/maxghenis/PolicyEngine/_worktrees/populace-acs-clone/inputs/acs_2024_1yr/afdc6d90c6e2f0bab365ed32d95ba4c4d8ac651162f46ac7861295b2dc469894/csv_pus.zip` | `afdc6d90c6e2f0bab365ed32d95ba4c4d8ac651162f46ac7861295b2dc469894` |
| ACS rent donor | `/Users/maxghenis/PolicyEngine/policyengine-us-data/policyengine_us_data/storage/acs_2022.h5` | `0b319b496f19a6913066f9c5ea572edfda3d78a187be6f375846617d0b441bd4` |
| processed PUF H5 | `/Users/maxghenis/PolicyEngine/policyengine-us-data/policyengine_us_data/storage/puf_2024.h5` | `7669f5b5281f20080e77204f9bd4aabfad0aa101fa283e22caf9ba8d61d4d6df` |
| source-year PUF CSV | `/Users/maxghenis/PolicyEngine/policyengine-us-data/policyengine_us_data/storage/puf_2015.csv` | `0a7fd643edb1acc55c507db795914b41d232922be78c149b58d111f4672499df` |

The build CLI requires these path/hash pairs
(`tools/build_us_multispine_pool.py:406-479`), recognizes `0.25` as rung
`f025` (`tools/build_us_multispine_pool.py:277-283`), and exposes the frozen
sampling and clone controls
(`tools/build_us_multispine_pool.py:496-517`).

## Hard RSS guard: prerequisite, not an escape hatch

The owner supervisor must:

- create a new process group for each build or gate;
- cap `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
  `VECLIB_MAXIMUM_THREADS`, `NUMEXPR_NUM_THREADS`, and
  `LOKY_MAX_CPU_COUNT` at `1`;
- enumerate the root process and all descendants at least every 250 ms;
- record both maximum individual RSS and aggregate process-tree RSS;
- immediately send `SIGSTOP` and then `SIGKILL` to the entire process group
  when either measure reaches 14 GiB;
- fail closed and stop the process group if polling, descendant enumeration,
  process-group ownership, or receipt writing fails; and
- offer no elapsed-time, free-memory, or manual override.

The 14 GiB stop margin is mandatory to keep every process below 15 GiB despite
polling latency. A guard that merely checks free memory before launch, monitors
only the root PID, or has a timeout escape hatch does not authorize execution.
The guard itself must first pass a synthetic child/grandchild allocation and
kill test, with its JSONL trace retained.

## Exact build payload

The supervisor, not an interactive shell, launches this exact payload after
setting `OUT_DIR` to the arm-specific fresh directory:

- removal:
  `/Users/maxghenis/PolicyEngine/_worktrees/microcosm-retirement-factorial/_buildo-runtime/out/stacked-f025-retirement-removal-only-r1`
- broad:
  `/Users/maxghenis/PolicyEngine/_worktrees/microcosm-retirement-factorial/_buildo-runtime/out/stacked-f025-retirement-broad-add-retain-direct-r1`

```bash
env \
  -u POPULACE_LOGBOOK_PREV_ROW_DIGEST \
  -u POPULACE_LEDGER_URL \
  -u POPULACE_LEDGER_KEY \
  -u POPULACE_LEDGER_API_KEY \
  PYTHONUNBUFFERED=1 \
  OMP_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 \
  NUMEXPR_NUM_THREADS=1 \
  LOKY_MAX_CPU_COUNT=1 \
  .venv/bin/python tools/build_us_multispine_pool.py \
  --sample-fraction 0.25 \
  --sample-seed 578 \
  --clone-attachment-fraction 1.0 \
  --clone-attachment-seed 578 \
  --asec-raw-stage-h5 /Users/maxghenis/PolicyEngine/_buildo-runtime/out/591-pawtyp-pool/asec-producer-checkpoints/asec_raw_stage.checkpoint.h5 \
  --asec-raw-stage-h5-sha256 51e9fafcd6f16140018fa90c7afbeb6d79008bfc8c122e437d23a399b30553fe \
  --acs-household-zip /Users/maxghenis/PolicyEngine/_worktrees/populace-acs-clone/inputs/acs_2024_1yr/8281008e53de98f0ef81e7a2ee5a8725991dda1ecfd2713ead73246425e515d0/csv_hus.zip \
  --acs-household-zip-sha256 8281008e53de98f0ef81e7a2ee5a8725991dda1ecfd2713ead73246425e515d0 \
  --acs-person-zip /Users/maxghenis/PolicyEngine/_worktrees/populace-acs-clone/inputs/acs_2024_1yr/afdc6d90c6e2f0bab365ed32d95ba4c4d8ac651162f46ac7861295b2dc469894/csv_pus.zip \
  --acs-person-zip-sha256 afdc6d90c6e2f0bab365ed32d95ba4c4d8ac651162f46ac7861295b2dc469894 \
  --acs-rent-h5 /Users/maxghenis/PolicyEngine/policyengine-us-data/policyengine_us_data/storage/acs_2022.h5 \
  --acs-rent-h5-sha256 0b319b496f19a6913066f9c5ea572edfda3d78a187be6f375846617d0b441bd4 \
  --puf-h5 /Users/maxghenis/PolicyEngine/policyengine-us-data/policyengine_us_data/storage/puf_2024.h5 \
  --puf-h5-sha256 7669f5b5281f20080e77204f9bd4aabfad0aa101fa283e22caf9ba8d61d4d6df \
  --puf-source-year-csv /Users/maxghenis/PolicyEngine/policyengine-us-data/policyengine_us_data/storage/puf_2015.csv \
  --puf-source-year-csv-sha256 0a7fd643edb1acc55c507db795914b41d232922be78c149b58d111f4672499df \
  --checkpoint-root "$OUT_DIR/populace_us_2024_stacked_pool.checkpoints" \
  --out "$OUT_DIR/populace_us_2024_stacked_pool.h5"
```

Do not add any argument, particularly `--logbook-prev-row-digest`. A resume is
permitted only inside the same fresh arm directory, with the same exact
revision and command, after an ordinary non-memory interruption; the checkpoint
identity binds all sampling and authority fields cited above. Never resume
after an RSS stop until the underlying memory behavior is fixed and the owner
re-authorizes it.

## Build artifact and receipt contract

Each arm directory must contain:

- `build.status.json`: arm, exact revision, full argv/environment allowlist,
  suite receipts, input preflight hashes, start/end time, exit code, terminal
  disposition, and abort reason if any;
- `build.guard.jsonl` and `build.log`: every monitor sample/event and complete
  stdout/stderr;
- `populace_us_2024_stacked_pool.h5`;
- `populace_us_2024_stacked_pool.manifest.json`;
- `populace_us_2024_stacked_pool.gates.json`; and
- `populace_us_2024_stacked_pool.checkpoints/`, including exactly one
  identity-routed `stacked/*/simulated.checkpoint.h5` and its operational
  receipts.

The driver derives the manifest, gate sidecar, and checkpoint paths from the
output H5 (`tools/build_us_multispine_pool.py:535-569`). It runs completeness
and by-origin battery as the two terminal gates
(`tools/build_us_multispine_pool.py:3264-3274`) and writes the identical
terminal payload under `terminal_gates` and compatibility alias
`agreement_gate`
(`tools/build_us_multispine_pool.py:3710-3720`). Count it once. `GateReport`
passes only if every evaluator passes and emits one name-keyed manifest
(`packages/microcosm-build/src/microcosm/build/gates.py:180-204,299-309`).

Exit `0` is a green terminal build. Exit `1` may still be valid technical
evidence when the known terminal gates are red: the driver deliberately writes
the non-ready artifact set and then returns `1`
(`tools/build_us_multispine_pool.py:4422-4429`). Accept exit `1` only when
publication completed, all required files and authenticated receipts are
complete, the two gate aliases are byte-equivalent as parsed JSON, and no
`logbook-receipts/*/error.json` exists. Any exception writes an error receipt and is an abort,
not a red-but-measured arm
(`tools/build_us_multispine_pool.py:4371-4408`).

After all build, gate, and completion outputs are written, hash every retained
artifact and receipt, then mark the arm directory closed. Never edit a closed
artifact directory. Preserve an aborted directory and label it `ABORTED`; a
new attempt gets a new `rN` suffix.

## Frozen standalone Phase-P gate

The reference runner is
`arm-order:tools/predictor_set_oos_gate.py`, byte SHA-256
`319cd4292577c5c88322fcfe6205e176a354094950b98ca45047f7f2bb320ca1`.
It resolves exactly one gates JSON and exactly one simulated checkpoint from
each artifact directory
(`arm-order:tools/predictor_set_oos_gate.py:567-600`).

Before use, derive a candidate-bound copy from those exact bytes. The only
permitted source/config difference is the candidate's:

- canonical stacked-authority identity;
- gap-fill-plan identity; and
- early target-bank identities for each direction.

The baseline bindings stay pinned to:

- artifact directory
  `/Users/maxghenis/PolicyEngine/_buildo-runtime/out/stacked-f025-r1`;
- code pin `f71731202b6ff1f0dfa757b6b52aa87ff2a34161`;
- stacked identity
  `9be8ecdf82356f38998e8b620ee36d9134f554fe89a8eafd8406f438e2b5aad6`;
- gates SHA-256
  `685cad63d4dc62234da72501c5a3ce9ec5a81fcd3f7b412b61474a9c1d8b423b`;
- input-pins digest
  `59587db52a879614fa55989c47b30bfe689e4c035296c306bf788e781670b682`;
- simulated checkpoint SHA-256
  `5b47eb0ded02f4031e235b7a6e07506b5bd38f87827644752d26f4263e492f5a`;
  and
- operational-receipts SHA-256
  `cb9ed4abb7586b6128f6aeefc9a4923e7e5934844bc3bd56e458299ac28e8c27`.

Audit the source diff against the reference and fail if any executable logic,
baseline binding, band, threshold, fold, seed, quantile, forest setting,
bootstrap setting, clause, target allowlist, or comparator changes. Record both
the reference and candidate-bound runner hashes. After removing only the
candidate integrity binding from `config` and canonicalizing JSON with sorted
keys and compact separators, its SHA-256 must equal
`10f29427d83c340973869fb735188967aff9a4eea770b066f604e7a28a0b5e5a`.

The frozen settings are:

- fold seed `20260816`, five folds, held-out fold `0`;
- quantiles `0.10, 0.25, 0.50, 0.75, 0.90`;
- forest seed `260816` and `32` estimators, with all other forest,
  missingness, weighting, and teacher-forcing settings byte-identical;
- bootstrap seed `8162026`, `256` clusters, `2,000` replicates, and 95%
  confidence;
- inclusive incidence band `[0.8, 1.25]`;
- quantile-envelope ceiling `0.25`; and
- unchanged CHAMPVA clause A, money-OOS non-worsening clause B, and no
  battery-exit clause C.

The production comparator uses exactly the same incidence band, five
quantiles, and QED ceiling
(`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:11397-11400,11942-11948,11969-12022,12085-12113`).
Changing a comparator, seed, fold, estimator setting, target list, or clause
invalidates the experiment.

For each arm, run the candidate-bound gate under the same hard RSS guard:

```bash
.venv/bin/python /ABSOLUTE/PATH/TO/AUDITED/predictor_set_oos_gate.py \
  --baseline /Users/maxghenis/PolicyEngine/_buildo-runtime/out/stacked-f025-r1 \
  --candidate "$OUT_DIR" \
  --output "$OUT_DIR/phase_p/verdict.json" \
  --markdown-output "$OUT_DIR/phase_p/report.md"
```

Run once with `OUT_DIR` bound to the current arm-specific directory declared
above. The runner's interface is exactly these four paths and returns nonzero
for a failed verdict
(`arm-order:tools/predictor_set_oos_gate.py:3498-3528`). A clause FAIL is valid
measured evidence; `measurement_integrity` failure, exception, RSS stop, or
incomplete output is an abort.

Keep each arm directory open through this gate and its completion receipt,
then hash every retained file and mark the directory closed. The generated
verdict/report stay inside that arm's fresh ignored `_buildo-runtime/out/`
directory; do not write them under tracked `experiments/`. This preserves the
clean-worktree preflight when switching from removal to broad without deleting
or modifying the closed removal evidence.

Accept a gate result only if it contains the complete, authenticated
`32-family / 118-target / 74-money-target / 211-battery-leg` sweep. Any missing,
extra, duplicate, or unexpectedly untestable row aborts. Gate the removal
artifact, write its completion receipt, and close its directory before checking
out the broad revision.

## Sixteen assigned BLOCKER checks

These are nine incidence criteria and seven conditional
quantile-envelope-distance criteria across eleven physical positive-money
legs. Every baseline criterion is officially `FAIL`. Values are from the
frozen baseline gates artifact and the
`retirement_model_and_data` rows in
`/Users/maxghenis/PolicyEngine/_worktrees/microcosm-arm-split/experiments/battery_burndown/adjudication.json`.

| Ordinal | Check ID | Criterion | Baseline value |
|---:|---|---|---:|
| 7 | `person/model_required_numeric/tax_exempt_private_pension_income[clone_0]/positive#incidence` | incidence ratio | 1.5540575408000976 |
| 19 | `person/puf_tax_itemization/taxable_private_pension_income[clone_0]/positive#incidence` | incidence ratio | 1.5633139716502966 |
| 20 | `person/puf_tax_itemization/taxable_ira_distributions[clone_0]/positive#incidence` | incidence ratio | 1.3692265605479346 |
| 21 | `person/puf_tax_itemization/social_security_retirement[clone_0]/positive#quantile` | QED | 0.5399065173295705 |
| 22 | `person/puf_tax_itemization/social_security_disability[clone_0]/positive#incidence` | incidence ratio | 0.777259623970176 |
| 23 | `person/puf_tax_itemization/social_security_disability[clone_0]/positive#quantile` | QED | 1.3265580996694013 |
| 24 | `person/puf_tax_itemization/social_security_dependents[clone_0]/positive#incidence` | incidence ratio | 1.6270067039916964 |
| 25 | `person/puf_tax_itemization/social_security_dependents[clone_0]/positive#quantile` | QED | 1.255813953488372 |
| 26 | `person/puf_tax_itemization/social_security_survivors[clone_0]/positive#quantile` | QED | 0.9842613410924481 |
| 76 | `person/source_operator_retirement_distributions/keogh_distributions[clone_0]/positive#incidence` | incidence ratio | 0.0 |
| 77 | `person/source_operator_retirement_distributions/taxable_401k_distributions[clone_0]/positive#incidence` | incidence ratio | 0.7928580784010778 |
| 78 | `person/source_operator_retirement_distributions/taxable_401k_distributions[clone_0]/positive#quantile` | QED | 0.46153846153846156 |
| 79 | `person/source_operator_retirement_distributions/taxable_403b_distributions[clone_0]/positive#incidence` | incidence ratio | 0.7260054960806753 |
| 80 | `person/source_operator_retirement_distributions/taxable_403b_distributions[clone_0]/positive#quantile` | QED | 1.4639175257731958 |
| 81 | `person/source_operator_retirement_distributions/taxable_sep_distributions[clone_0]/positive#incidence` | incidence ratio | 17.073910540208754 |
| 82 | `person/source_operator_retirement_distributions/taxable_sep_distributions[clone_0]/positive#quantile` | QED | 1.7696335078534031 |

Keogh QED is not one of the assigned checks: its two ASEC and zero ACS carrier
rows are insufficient for QED, while its incidence criterion is still a real
failure
(`packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:11969-12009`;
`/Users/maxghenis/PolicyEngine/_worktrees/microcosm-arm-split/experiments/battery_burndown/ADJUDICATION.md:69-96`).

## Required before/after report

Produce one machine-readable row per check and a source-qualified Markdown
table. Each row must contain:

```json
{
  "ordinal": 7,
  "check_id": "...#incidence",
  "criterion": "incidence",
  "baseline": {
    "criterion_value": 1.5540575408000976,
    "official_status": "FAIL",
    "asec_incidence": 0.0,
    "acs_incidence": 0.0,
    "nonzero_rows": {"asec": 0, "acs": 0}
  },
  "removal": {
    "criterion_value": 0.0,
    "official_status": "PASS|FAIL",
    "asec_incidence": 0.0,
    "acs_incidence": 0.0,
    "nonzero_rows": {"asec": 0, "acs": 0},
    "delta": 0.0,
    "distance_to_frozen_pass_region": 0.0,
    "movement": "to_green|toward_green|unchanged|away_from_green",
    "artifact": {
      "revision": "1a8ad451c6eff17d405ef75cbdd014de72447153",
      "gates_path": "...",
      "gates_sha256": "...",
      "stacked_identity": "..."
    }
  },
  "broad": {
    "criterion_value": 0.0,
    "official_status": "PASS|FAIL",
    "asec_incidence": 0.0,
    "acs_incidence": 0.0,
    "nonzero_rows": {"asec": 0, "acs": 0},
    "delta": 0.0,
    "distance_to_frozen_pass_region": 0.0,
    "movement": "to_green|toward_green|unchanged|away_from_green",
    "artifact": {
      "revision": "539e415defb27bf103a40081239f123ce9d76c6d",
      "gates_path": "...",
      "gates_sha256": "...",
      "stacked_identity": "..."
    }
  }
}
```

The numeric placeholders above are schema examples, not measurements. Replace
them directly from each gates artifact.

For incidence ratio `r`, distance to the frozen inclusive pass region is
`max(0, 0.8 - r, r - 1.25)`. For QED `q` it is
`max(0, q - 0.25)`. `delta` is candidate minus baseline for the same
criterion. Classify:

- `to_green` when the candidate's exact criterion passes;
- `toward_green` when it remains red and its distance strictly decreases;
- `unchanged` when its distance is exactly equal; and
- `away_from_green` when its distance increases.

Use the evaluator's official criterion status, not a rounded display value.
Report enough digits to round-trip JSON. For a QED row, still report its
physical leg's incidence and carrier counts. Missing criterion value, missing
support fields, changed check identity, or unexpected untestability aborts the
16-check report. This descriptive movement classification never changes the
frozen comparator.

## Interpretation matrix

Interpret the paired arms only after both complete:

| Removal-only | Broad additions with direct predictors retained | Supported interpretation |
|---|---|---|
| harms retirement checks | safe or materially safer | Loss of direct Social Security/retirement predictors is the leading main-effect explanation. |
| safe or materially safer | harms retirement checks | The broad additions are the leading main-effect explanation. |
| harms | harms | Evidence for multiple/additive main effects; do not claim a unique driver. |
| safe | safe | The historical replacement harm requires an interaction or another bundle component. |

“Harms” and “safe” must be justified across the complete 74-money/211-battery
sweep and the 16 assigned rows, not from a single target. A green or improved
assigned row is diagnostic movement, not permission to land an arm. Technical
factorial evidence may be valid even when the full terminal build remains red
because of pre-existing baseline failures; landability still requires all
frozen Phase-P clauses, no new battery damage, and owner adjudication.

Do not treat the historical round-1 bundle as a clean third factorial cell. It
also changed late-PUF and other bundled components, and the arm synthesis
explicitly declines a bundle handoff
(`/Users/maxghenis/PolicyEngine/_worktrees/microcosm-arm-split/experiments/phase_p_arm_split/SYNTHESIS.md:27-32,346-352,370-379`).

## Abort conditions and owner completion receipt

Abort and preserve evidence on any:

- wrong SHA, dirty pre-build tree, missing/failed suite receipt, or treatment
  wiring that differs from the code-cited declarations;
- missing/mismatched input, seed, sample fraction, clone fraction, or clone
  seed;
- pre-existing output directory, concurrent run, absent owner lock, configured
  logbook predecessor, or any contact with `logbook-pending-chain.txt`;
- guard failure, 14 GiB stop, escaped descendant, or incomplete monitor trace;
- exception/error receipt, incomplete publication, ambiguous checkpoint
  identity, missing canonical authority, wrong gap-fill/target-bank binding, or
  evidence that the late predictor surface changed;
- non-identical `terminal_gates` and `agreement_gate` payloads;
- standalone gate logic/config drift, normalized config hash mismatch,
  measurement-integrity failure, or incomplete 32/118/74/211 sweep; or
- missing, duplicated, renamed, or unexpectedly untestable assigned check.

The owner's completion receipt must give, for each arm: exact build SHA; suite
commands and results; input hashes; full command; output directory; build exit
and disposition; maximum individual and aggregate RSS; hashes for H5,
manifest, gates, simulated checkpoint, operational receipts, build status,
guard trace, gate runner, verdict, and report; authenticated stacked,
gap-fill-plan, and target-bank identities; Phase-P clause results; full-sweep
counts; and the 16-row before/after table. It must state explicitly whether
each run was completed, completed-red, or aborted and why.
