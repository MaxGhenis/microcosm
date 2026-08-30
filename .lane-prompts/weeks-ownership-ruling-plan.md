# Ruling: stacked `weeks_worked` ownership (2024 release-only measured leaf) — v3

Revision 3. Round 1 (REQUEST-CHANGES) endorsed the direction — 2024 input
leaf, ACS `WKWN` as the source-direct analog, pool exclusion retained — with
six required changes. Round 2 (REQUEST-CHANGES) found four satisfied and
required two receipt tightenings, both adopted here: (3) joint
blank/nonblank × allocation cross-tab instead of marginals, with validated
`FWKWNP` domain and the 305,606-total count; (5) origin × clone-role
cross-tab instead of marginals. The v1 tests/Ruff/repo-suite commitment
round 2 flagged as dropped is restored.

## Defect

The multispine pool strips `weeks_worked` as a formula-owned output
(`US_HOURS_WORKED_POOL_EXCLUDED_COLUMNS`, receipted as
`pool_excluded_outputs_removed.person=['weeks_worked']`), and the ACS loader
(`acs_pums.py`) omits `WKWN`. The stacked 2024 release path then lacks the
`person.weeks_worked` column that gate 9480 requires and that ORG/FLSA and
`spm_unit_work_expenses` consume. Evidence provenance, stated precisely: the
candidate's sealed release log stopped earlier, on the farm-rent gate; the
missing-weeks failure is established by faithful replay of the release path
over candidate evidence, not by the sealed log's terminal failure. The legacy
fiscal-refresh reconstruction is CPS-only — running it on the pool zeroes ACS
hours (worked share 0.263 vs [0.35, 0.62]) — so it is not a valid owner.

## Why the guards were green

Installed `policyengine-us` 1.819.0 defines no 2024 formula for
`weeks_worked` — only `formula_2025`, a pure carry-forward
(`person("weeks_worked", period.last_year)`). The ownership classifier
(`resolve_formula_owned_outputs`) is period-blind ("has a formula ⇒
formula-owned"), and the parity test proves agreement between two any-period
guard sets — not correct 2024 ownership. The final export guard is already
period-aware; the specific gap is the static classifier/boundary. In 2024 the
variable is a plain input with no owner on the pool path.

## The ruling being gated

Authorize a **2024 release-only, origin-aware measured weeks leaf**, applied
in the stacked release path before the hours gate and before frozen-support
selection (or, if applied after, with explicit coverage of support selections
where clone 1 survives without clone 0). All clone roles present in
candidate-25 (0, 1, and 2) must be covered.

### Value semantics

- **ASEC-lineage persons**: `weeks_worked` ← raw `WKSWORK`, validated as
  integral `0–52`. Validation, not clipping — out-of-domain values fail
  closed rather than being silently clamped.
- **ACS-lineage persons**: `weeks_worked` ← pinned official `WKWN` — an exact
  numeric `1–52` field (not categorical) present on 1,767,132 of 3,422,888
  people. Accept only blank or integral `1–52`; anything else fails closed.
  **Validated ACS blanks are structurally recoded by Microcosm to 0** (Census
  supplies blanks, not zeros — the recode is ours and is receipted as such).
  Zero is coherent for the consumers: ORG bypasses annualization and FLSA
  suppresses premiums at zero weeks — consequential model semantics, adopted
  deliberately.
- **Accepted reference-window mismatch, recorded explicitly**: ACS 2024
  `WKWN` covers the rolling 12 months before interview (persons 16+); ASEC
  2024 `WKSWORK` covers calendar 2023 (persons 15+). The stacked values do
  not share one reference window. This mismatch is accepted as inherent to
  the stacked design (each lineage carries its own survey's measured value)
  and is documented in the spec stage notes.
- **"Measured" qualified**: per `FWKWNP`, 305,604 of 1,767,132 nonblank ACS
  values (17.29%) are Census-allocated; the pinned archive carries 305,606
  total `FWKWNP=1` rows (including two allocated blanks). The leaf is
  described as **source-direct reported-or-allocated**. The `FWKWNP` domain
  is validated, and allocation status is receipted as a **joint `WKWN`
  blank/nonblank × allocation-status cross-tabulation** (or an
  identity-bound status digest) — separate marginals are insufficient, since
  they can remain unchanged while cells are swapped or omitted.

### Authentication and ordering

- `person_support_channel` selects physical ACS vs ASEC origin; it is **not**
  identity. For ACS: authenticate the pinned archive (hash), join one-to-one
  on `SERIALNO + SPORDER`, and only then fan out by validated
  `person_source_id`.
- Origin routing lives at an approved provenance-owner boundary (pattern:
  `acs_release_predictors.py`) — **not** inside `hours_worked.py`, whose
  source-blindness contract stands.
- Declared as a spec-driven source stage with manifest receipts, like every
  other measured mapping.

### Fail-closed receipts and tests (new weeks-specific gate)

The existing hours signal gate only requires multiple values and would accept
invalid domains or clone-inconsistent values; a dedicated weeks gate is
required, receipting/asserting:

- archive hashes and period identity;
- raw domain counts; validated `FWKWNP` domain; the joint `WKWN`
  blank/nonblank × allocation-status cross-tab (per the value-semantics
  section above);
- exact join totality (matched/unmatched/collisions; tamper rejection);
- an **origin × clone-role cross-tab** covering roles 0/1/2 (pattern:
  `support_provenance.py` `by_source_channel_and_clone_index`) — not
  separate origin and role marginals — with zero per-source clone
  disagreements;
- rejection of conflicting pre-existing values;
- proof that only `weeks_worked` changed (column-diff receipt).

All implementation lands with focused green tests and Ruff, and the
repository-wide suite green (restored from v1; standing lane requirement).

### Consumer and period-boundary regressions

- 2024: input/export behavior; ORG/FLSA consumption; the
  `spm_unit_work_expenses` SPM result.
- 2025: carry-forward via `formula_2025` works from the 2024 leaf; direct
  materialization of a 2025 `weeks_worked` column is rejected.

### Explicitly retained/unchanged

- The pool's cross-period formula-owned exclusion stays — from 2025 on the
  engine's carry-forward formula correctly owns the variable.
- No weakening of gate 9480, the hours signal gate, or any existing
  threshold; the new weeks gate is additive.
- Not adopted (fairly rejected per round 1): ASEC→ACS statistical transfer of
  weeks; changes to ORG/FLSA denominator semantics.

## Sequencing constraints

- No data builds (Max's hold stands); code + spec + tests only.
- Implementation lands in the `stacked-dense-gate-sweep` worktree only after
  the running r3 adjudication lane completes (no concurrent writers).
- Follow-up (not part of this ruling): make the static ownership
  classifier/boundary period-aware, or treat pure carry-forward formulas as
  delegating to a base-period input, so this class of gap fails closed at
  build time.

## Evidence base

- Lane audit commit `2f7419b2` (journal assertions; not itself a candidate
  receipt) and the candidate manifest's 53-value weeks surface +
  `pool_excluded_outputs_removed` receipt.
- Code reads: `hours_worked.py:81`, `multispine_pool.py:1812`,
  `acs_pums.py:72`, `puf_support.py:2606`,
  `test_us_multispine_pool.py:3394`, installed `policyengine_us`
  `weeks_worked` variable source; ACS/ASEC 2024 data dictionaries (reference
  windows, universes); pinned ACS archive `WKWN`/`FWKWNP` counts.

Max's authorization (2026-08-29): "if you and sol agree, sure" — conditional
on Fable main + sol peer agreement via this gate. Fable main approves this v3
revision.
