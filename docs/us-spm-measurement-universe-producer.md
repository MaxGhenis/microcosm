# The Microcosm producer for the US SPM measurement universe

Design note. No production code changes accompany it.

PolicyEngine/policyengine-us#9462 (draft, fixes #9461, branch
`max/spm-measurement-universe-20260914`, head `47e94fa491`) makes the SPM
measurement universe a **source declaration**: a dataset supplies
`spm_unit_spm_universe_status` ∈ {`INCLUDED`, `OUTSIDE`, `UNRESOLVED`} for
every SPM unit and year. `OUTSIDE` units get missing SPM amounts and poverty
indicators and never reach the threshold provider; an undeclared dataset is
`UNRESOLVED` and raises `SPM_UNIVERSE_REQUIRED`.

Microcosm has no producer for that input. At this head
(`origin/main`, `18c6d39a0`), `git grep spm_universe_status` returns nothing
outside this note.

This note answers the seven commissioned questions from files read at this
head. Every mechanism claim carries `file:line`. Claims I did not read are
marked **inferred** or **unverified**.

The headline finding is not in the brief: **as drafted, the engine variable
cannot be exported by Microcosm at all**, for a reason unrelated to the pin.
See [§4](#4-the-engine-version-problem). Two other findings change the plan:
the "outside units have no housing" assumption
[does not hold](#5-outside-housing), and the release's poverty consumer
[fails silently rather than loudly](#6-consumers) under nullable indicators.

---

## 1. Source universes

### What Census says

Fetched this session from
`https://www.census.gov/content/dam/Census/library/working-papers/2020/demo/SEHSD-WP2020-09.pdf`,
pages 6–7, verbatim:

> The poverty universes differ between the two surveys in that all people
> living in group quarters are excluded in the ACS SPM, while people living in
> noninstitutionalized group quarters are included in the CPS SPM. This is
> done because CPS ASEC universe excludes the institutionalized population,
> while the noninstitutionalized population, such as homeless people living in
> shelters and military personnel living with civilians, are included in the
> CPS ASEC universe.[^14] Since there is no way to distinguish these groups
> from other group quarters residents in the ACS PUMS, the ACS sample is
> limited to people living in households.
>
> [^14]: As of 2017, college dorms are excluded from the CPS ASEC sample.

Two things follow, and they are not symmetric.

**ASEC.** The CPS ASEC *sample frame* already equals the CPS SPM universe. The
institutionalized population is outside the survey, not inside it and excluded;
the noninstitutional group quarters that ASEC does sample (shelters, military
personnel living with civilians) are *in* the CPS SPM universe. There is no
"ASEC record outside the CPS SPM universe" to declare. **Every ASEC record is
`INCLUDED`.**

**ACS.** The exclusion is a *data limitation*, not a conceptual one: Census
would include noninstitutional group quarters if the public PUMS let it
distinguish them, and it does not. Microcosm's ACS spine inherits exactly that
limitation, so it must make exactly that exclusion.

### Does the Build P lineage keep any record outside the ASEC universe?

No, and the repo already enforces it. `spm_role_source._reconcile_units`
refuses a zero-adult unit on the **pinned complete Census ASEC CSV** itself:

```
packages/microcosm-build/src/microcosm/build/us_runtime/spm_role_source.py:141-144
    _require(
        bool(units.adults.ge(1).all()),
        f"{label} has an unresolved zero-adult SPM unit.",
    )
```

and reconciles every unit against Census's own published `SPM_NUMADULTS` /
`SPM_NUMKIDS` / `SPM_NUMPER` counts (`spm_role_source.py:124-136`). A pinned
ASEC file that carried a record Census excluded from its SPM universe would
disagree with those counts and refuse. The derivation then re-runs the same
reconciliation on the *native* units (`spm_role_source.py:335`), so the
property survives pooling and cloning.

This is consistent with the measured counts: the published national default
`populace-us-2024-spm-20260915` has **0** SPM units without a classified adult
over the same 166,321 persons / 59,900 units, and the July Build P donor's 28
come from the absence of the native role column, not from a universe problem.

### What field identifies group quarters at each ACS stage

`TYPEHUGQ` is the ACS PUMS household record type. Microcosm reads it, validates
it, and carries it further than I expected.

**1 — Raw load.** Required on the household table:

```
packages/microcosm-build/src/microcosm/build/us_runtime/acs_pums.py:50-60
_HOUSEHOLD_REQUIRED = (
    "SERIALNO", "PUMA", "WGTP", "NP", "ADJHSG",
    "TEN", "RNTP", "GRNTP", "TAXAMT", "TYPEHUGQ",
)
```

**2 — Validation.** `_occupied_households` fixes the code domain and binds it
to the weight convention:

```
packages/microcosm-build/src/microcosm/build/us_runtime/acs_pums.py:398-410
    kind = pd.to_numeric(household["TYPEHUGQ"], errors="coerce")
    if kind.isna().any() or (~kind.isin([1, 2, 3])).any():
        ...raise ValueError(f"ACS TYPEHUGQ contains unsupported code(s): {bad}.")
    weight = pd.to_numeric(household["WGTP"], errors="coerce")
    gq = kind.isin([2, 3])
    if (people.loc[gq] != 1).any():
        raise ValueError("ACS group-quarters placeholders must have NP=1.")
    if (weight.loc[gq] != 0).any() or (weight.loc[~gq] <= 0).any():
        raise ValueError("ACS TYPEHUGQ/WGTP disagree: ...")
```

So at this head: `1` = housing unit, `{2, 3}` = group quarters, every GQ
placeholder is exactly one person with `WGTP == 0`, and an unknown code already
refuses the build. The producer does not need to invent this domain — it
inherits it.

**3 — Staged frame.** `TYPEHUGQ` is an explicit frame column, not a
load-and-drop filter:

```
packages/microcosm-build/src/microcosm/build/us_runtime/acs_pums.py:64-72
_HOUSEHOLD_FRAME_COLUMNS = (
    "NP", "ADJHSG", "TEN", "RNTP", "GRNTP", "TAXAMT", "TYPEHUGQ",
)
```

attached by `_attach_household_source_columns` at `acs_pums.py:298`. This is
the single most useful fact in this section: **the ACS group-quarters kind is
already a frame column on the household table.** The producer reads a value
the source put there; it does not reconstruct one.

**4 — Materialized / stacked frame.** It survives assembly, and the
ACS/ASEC asymmetry is already encoded. `stacked_spine._acs_native_group_quarters_receipt`
binds GQ lineage to immutable assembly-time identifiers:

```
packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:410-437
    kind = pd.to_numeric(household["TYPEHUGQ"], errors="coerce")
    invalid = ~kind.isin((1, 2, 3))
    if invalid.any():
        raise ValueError("Stacked ACS assembly requires every sampled household
            to carry a TYPEHUGQ 1/2/3 source classification; ...")
    gq_households = kind.isin((2, 3))
    ...
    if len(linked_counts) != len(household_ids) or not linked_counts.eq(1).all():
        raise ValueError("Stacked ACS assembly requires exactly one native person
            per TYPEHUGQ 2/3 group-quarters household.")
```

and the selection is a named, versioned lineage constant
(`stacked_spine.py:296-297`: `_ACS_NATIVE_GQ_SELECTION = "TYPEHUGQ in {2,3} on
sampled native ACS rows"`, `_ACS_NATIVE_GQ_LINEAGE_VERSION = 1`).

On the stacked spine `TYPEHUGQ` is a `@effective:validated_structure:` column
and **ASEC rows carry it as missing**, by design — the stacked-spine suite
asserts exactly that split:

```
packages/microcosm-build/tests/test_us_stacked_spine.py:3707-3708
    assert int(household.loc[asec_rows, "TYPEHUGQ"].isna().sum()) == 1_688
    assert int(household.loc[acs_rows, "TYPEHUGQ"].isna().sum()) == 0
```

That asymmetry *is* the universe asymmetry, already in the frame. The producer
formalizes it; it does not introduce it.

**5 — Release H5.** `TYPEHUGQ` does not reach it, and cannot. It is not a
PolicyEngine-US variable, and the export contract is closed against exactly
that:

```
packages/microcosm-frame/src/microcosm/frame/adapters/policyengine_us.py:958-968
        unexpected: set[str] = set()
        if contract.closed:
            allowed = (
                set(contract.required) | set(contract.optional)
                | self._structural_columns() | {_HOUSEHOLD_WEIGHT_COLUMN}
            )
            unexpected = present_columns - allowed
```

**Net: the ACS group-quarters fact is present through the frame and stops at
the export boundary.** The producer's job is to translate it into a variable
the engine knows, at the entity the engine asks for, at that boundary.

### How ACS SPM units are formed

The legacy ACS assembly makes one SPM unit per household (measured: 1,531,614
households → 1,531,614 units), and GQ placeholders are one-person households
(`acs_pums.py:404`). So on the native ACS spine every GQ SPM unit is a
singleton and its kind is unambiguous. **This is a property of native rows
only.** After cloning and stacking, unit membership is rebuilt from support
channels, so the producer must re-derive and re-check kind per unit rather
than assume the singleton property survives — see the mixed-kind refusal in
[§2](#2-the-rule-as-a-source-owned-deterministic-producer).

---

## 2. The rule, as a source-owned deterministic producer

### Shape

Model it on `spm_role_source.py`, which is the repo's archetype for a
source-owned, non-modeling producer: pinned sources verified by size and
SHA-256, reconciliation against published Census counts, a provenance dict
that states what the evidence is and is not, and `weights_used: False` /
`ages_changed: False` (`spm_role_source.py:399-422`). Nothing in it fits,
draws, ages, or weights.

| Property | Value |
| --- | --- |
| Module | `microcosm.build.us_runtime.spm_universe_source` |
| Output variable | `spm_unit_spm_universe_status` |
| Entity | `spm_unit` |
| Period | `YEAR` (the engine declares `definition_period = YEAR`) |
| Stored encoding | Enum **member name** string: `"INCLUDED"` / `"OUTSIDE"` / `"UNRESOLVED"` |
| Inputs (ACS) | `household.TYPEHUGQ`, `person.person_household_id`, `person.person_spm_unit_id`, `spm_unit.spm_unit_id` |
| Inputs (ASEC) | the spine identity; no per-record field is required (see §1) |
| Never | a QRF transfer target, a calibration target, an imputation, a seeded draw |

### Stored encoding, read at head

The adapter derives the enum domain from the engine, not from a constant:

```
packages/microcosm-frame/src/microcosm/frame/adapters/policyengine_us.py:581-586
def _enum_domain(variable: Any) -> tuple[str, ...]:
    possible_values = getattr(variable, "possible_values", None)
    members = getattr(possible_values, "__members__", None)
    if isinstance(members, Mapping):
        return tuple(str(name) for name in members)
    return ()
```

and normalizes a stored cell to a member **name** (`policyengine_us.py:589-599`),
accepting `bytes` (decoded), any object with `.name`, or `str`. Every enum
column is validated cell-by-cell against the domain before a write:

```
packages/microcosm-frame/src/microcosm/frame/adapters/policyengine_us.py:1102-1113
                for value in frame[column].to_numpy(dtype=object):
                    name = _stored_enum_name(value)
                    if name not in allowed:
                        invalid.append("<missing>" if name is None else name)
                if invalid:
                    failures.append(f"{entity}.{column}: {len(invalid)}/{len(frame)} "
                        "value(s) outside enum domain; ...")
```

Enum value types are deliberately absent from `_DTYPE_KIND_BY_VALUE_TYPE` and
fall back to `"str"` (`policyengine_us.py:108-110`,
`variable_metadata` at `policyengine_us.py:645-666`). So the frame column is a
plain string column of member names. **Store `"OUTSIDE"`, not `2`, not
`"SPMUniverseStatus.OUTSIDE"`, not the label text.** The engine reads it back
with `.decode_to_str()` and compares against member names
(`policyengine-us#9462` `policyengine_us/spm.py:70-77`).

On the engine side the variable is (read on that PR's branch,
`policyengine_us/variables/household/income/spm_unit/spm_unit_spm_universe_status.py:5-21`):

```python
class SPMUniverseStatus(Enum):
    INCLUDED = "Included in the declared SPM measurement universe"
    OUTSIDE = "Outside the declared SPM measurement universe"
    UNRESOLVED = "Measurement universe has not been resolved"

class spm_unit_spm_universe_status(Variable):
    value_type = Enum
    possible_values = SPMUniverseStatus
    default_value = SPMUniverseStatus.UNRESOLVED
    entity = SPMUnit
    definition_period = YEAR
```

### The rule

```
ACS native household unit  (TYPEHUGQ == 1)      → INCLUDED
ACS native group quarters  (TYPEHUGQ in {2,3})  → OUTSIDE
ASEC unit                                       → INCLUDED
```

A clone inherits the status of the native row it was cloned from. Never
`UNRESOLVED` on a released file: `UNRESOLVED` is the engine's *absence*
sentinel, not a value a producer emits. A producer that cannot decide must
**refuse**, not write `UNRESOLVED`.

### Refusals

Each is a hard `ValueError`, named, fail-closed, in the `_require` style of
`spm_role_source.py:80-82`:

| Code | Condition |
| --- | --- |
| `SPM_UNIVERSE_UNKNOWN_HOUSEHOLD_KIND` | any in-scope ACS household row whose `TYPEHUGQ` ∉ {1,2,3} (including missing on an ACS-channel row) |
| `SPM_UNIVERSE_MIXED_HOUSEHOLD` | one household row resolving to more than one kind (cannot arise natively; reachable after a bad merge) |
| `SPM_UNIVERSE_UNIT_SPANS_KINDS` | one SPM unit whose members sit in households of different kinds |
| `SPM_UNIVERSE_EMPTY_UNIT` | a `spm_unit_id` present in the `spm_unit` table with no member in `person.person_spm_unit_id` |
| `SPM_UNIVERSE_ORPHAN_MEMBER` | a `person_spm_unit_id` absent from the `spm_unit` table |
| `SPM_UNIVERSE_UNDECLARED_SPINE` | a support channel the producer has no universe ruling for |
| `SPM_UNIVERSE_GQ_MULTI_PERSON` | a `TYPEHUGQ` 2/3 household with more than one native person (mirrors `stacked_spine.py:434-437`) |

`SPM_UNIVERSE_UNIT_SPANS_KINDS` is the one that earns its keep. Natively it is
unreachable — ACS GQ households have `NP == 1`. It becomes reachable the
moment a future spine, a donor merge, or a clone-index bug puts a GQ person
into a multi-person unit, and at that point silently picking a majority kind
would be a fabricated universe decision. Refuse.

`SPM_UNIVERSE_EMPTY_UNIT` is listed because the brief asks for it, and it is
worth keeping even though `spm_role_source.py:294-297` already asserts exact
membership coverage. Two independent assertions of the same invariant is the
right cost here.

### Why this is a declaration, not an inference

The engine is explicit that scope is a construction fact:

```
policyengine-us#9462  policyengine_us/spm.py:56-60
    """Household requests describe included units; datasets must declare scope.

    Data origin is a scalar construction contract, not a demographic inference.
    In particular, missing age or tenure never makes a unit outside the universe.
    """
```

and `docs/engineering/spm-universe.md` on that branch: "The model never infers
scope from missing tenure, age, county or a zero-adult measurement
composition."

The producer must honour that on its own side too. The temptation is real and
should be named: the ACS problem was *discovered* as 5,246 zero-classified-adult
units, and it would be easy to write a producer that marks zero-adult units
`OUTSIDE`. That would be wrong three times over — it would mark a genuine
household-unit data defect as out-of-universe and hide it; it would leave the
1,946 under-15 GQ units and the 3,300 aged-15-to-17 GQ units resolved for
different reasons than the actual one; and it would produce a universe that
changes when the *role* column changes. The correct input is `TYPEHUGQ`, which
is the source's own record-type field, known before any composition is
computed.

Two named non-goals, both from the graph-native line
(`microcosm-native-child-source-050c58a60-20260921`,
`packages/microcosm-build/src/microcosm/build/acs_spm_scope.py:580`): an
`OUTSIDE` unit's *other* SPM inputs are **not** filled, cast or defaulted —
"Nullable roles are never filled or cast, including for OUTSIDE units."
Declaring a unit outside the measurement universe is not permission to
synthesize its unmeasured attributes. And `OUTSIDE` never changes a unit's
weight, its membership, or its presence in the file: the fiscal population is
unchanged, only its SPM measurability is declared.

### Reuse from the graph-native line, and what not to port

Read at `microcosm-native-child-source-050c58a60-20260921` (read-only).

**Reuse (scientific).**

- The exact variable name and three-state vocabulary already agree with
  upstream: `spm_input_contract.py:7-12` defines `UNIVERSE_INPUT =
  "spm_unit_spm_universe_status"` with `INCLUDED` / `OUTSIDE` / `UNRESOLVED`.
  Keep these names identical; there is no reason for two spellings.
- The decision rule is the same one derived independently here:
  `acs_spm_scope.py:346-348` — `_require(authority.household_kind in (2, 3),
  "OUTSIDE_UNIVERSE"); return OUTSIDE, "outside_declared_acs_household_only_analysis"`.
- The named authority for the decision:
  `acs_spm_scope.py:58` `ACS_SPM_OUTSIDE_AUTHORITY = "outside_acs_household_universe"`,
  and the methodology pin `acs_spm_scope.py:60` pointing at page 6 of
  SEHSD-WP2020-09 — the same citation this note verifies in §1.
- The profile framing: a universe declaration belongs to a *named analysis
  scope* (`acs_spm_scope.py:59`,
  `ACS_SPM_PROFILE_NAME = "acs_spm_household_only_analysis_2024"`) rather than
  floating free. A release should record which profile it declared.
- The no-fill rule for outside units (`acs_spm_scope.py:580`), above.

**Do not port (graph-mechanical).** The `ACSAnalysisProfile` admission flags
and their year/vintage assertions (`acs_spm_scope.py:76-90`), the four
authority-ranking tables (`acs_spm_scope.py:30-56`), the evidence-digest and
aggregate-reduction machinery, and every graph node/version/kernel
registration around it. That apparatus exists to rank *contested relationship
evidence* inside a graph issuer. `TYPEHUGQ` is not contested — it is a
one-field source classification with a refusing domain check — and a
`us_runtime` producer has no graph issuer to satisfy. Porting the ranking
tables would import a decision hierarchy that has nothing to rank.

**What it leaves open.** `acs_spm_scope.py` is ACS-only and year-pinned to
2024 (`acs_spm_scope.py:87`). It offers no ASEC ruling, so the
`INCLUDED`-for-all-ASEC finding in §1 is this note's, and it must be carried
explicitly rather than inherited.

---

## 3. Where it lives and what it touches

### Owner and call sites

**Owner:** `packages/microcosm-build/src/microcosm/build/us_runtime/spm_universe_source.py`.

**Legacy ACS path.** `TYPEHUGQ` is authoritative at
`acs_pums.build_acs_pums_unit_frame` (`acs_pums.py:253`), but it is a
*household* column, and the output is a *spm_unit* column whose units do not
exist until `assign_us_unit_structure` has run (`acs_pums.py:288-294`). So the
producer cannot live inside the ACS PUMS parse. The correct insertion is a
late, spine-aware step that reads the assembled frame's `household`, `person`
and `spm_unit` tables together — the same position and signature as
`check_spm_composition` in PR #948, which already does exactly this traversal
for the composition check. Concretely: called from
`tools/_legacy/build_us_acs_multispine_base.py` after assembly and before
export, and from `tools/build_us_acs_local_release.py` on the export frame.

**Fiscal-refresh release tool.** `tools/build_us_fiscal_refresh_release.py`
starts from a published parent rather than rebuilding the spine, and already
carries an `spm_unit` table forward (`tools/build_us_fiscal_refresh_release.py:2624`,
`"spm_unit": dataset.spm_unit.copy()`). It must **carry** the status, not
re-derive it: the parent's `TYPEHUGQ` is gone by then (§1, stage 5). If the
parent has no status column, the refresh must refuse rather than default.

**Source-enrichment lane.** Discussed below; it is the route for the
already-published national default.

### The smallest safe generalization of the enrichment lane

The lane is single-variable in a deeper way than "a constant is hardcoded".

`microcosm.data.h5_enrichment.append_native_spm_role` is hardcoded to one
boolean column on the **person** table, at the HDF type level:

```
packages/microcosm-data/src/microcosm/data/h5_enrichment.py:124-141
    role = np.asarray(role)
    if role.dtype != np.dtype(bool) or role.ndim != 1:
        raise ValueError("Role must be a one-dimensional Boolean array")
    ...
            compound.set_size(old_size + 1)
            # PyTables Boolean columns are HDF bitfields, not enums/integers.
            compound.insert(ROLE.encode(), old_size, h5py.h5t.NATIVE_B8)
```

and `source_enrichment` asserts the written column is that exact HDF type:

```
packages/microcosm-data/src/microcosm/data/source_enrichment.py:182-186
        role_index = table.dtype.names.index(ROLE_VARIABLE)
        if table.id.get_type().get_member_type(role_index) != h5py.h5t.NATIVE_B8 or (
            ...
            raise ValueError("native person role must have PyTables bool bitfield type")
```

and pins the operation by name:

```
packages/microcosm-data/src/microcosm/data/source_enrichment.py:296-297
    if report.get("operation") != "add_native_spm_independent_minor_role":
        failures.append("source enrichment operation must add only the native SPM role")
```

Three separate things therefore change, and only one of them is a refactor:

1. **Entity.** `_TABLE` is `person/table`. The status lives on `spm_unit`.
   The append must target a caller-named entity table.
2. **Dtype.** A 1-byte bitfield becomes a fixed-width string column. In
   PyTables that is a different itemsize, a different column-registration
   story (`_REGISTRATION = {"data_columns", "values_cols", "non_index_axes",
   "info"}`, `h5_enrichment.py:23`) and a different exactness proof. This is
   the real work, and it is not a rename.
3. **Arity.** `ROLE` → a sequence of `(entity, column, dtype, values)`
   descriptors; `operation` → a sorted list of declared operations;
   `EXPECTED_COUNTS` (`source_enrichment.py:111-118`) → keyed per variable.

**Smallest safe generalization:** make `append_native_spm_role` a thin
compatibility wrapper over `append_native_source_columns(parent, candidate,
columns=[...])`, where each descriptor declares its entity table, its HDF
member type, and its values; keep the *existing* boolean/person path
byte-identical and prove it with the existing tests; add the string/`spm_unit`
path as new code with its own exactness proof. Generalize the descriptor
list, not the verification.

**Do not loosen** the single-parent exactness core: the SHA-256 checks before,
during and after the copy (`h5_enrichment.py:118-119`, `135-136`, `185-186`),
`O_CREAT | O_EXCL` destination creation (`h5_enrichment.py:128`, which "also
refuses aliases/symlinks to the parent"), the unlink-on-any-exception
(`h5_enrichment.py:190-192`), the schema-5 inheritance assertions
(`source_enrichment.py:304-320`), and `all_preexisting_variables_exact`
(`source_enrichment.py:394`). Those are not single-variable; they are
single-*parent*, and they are the whole value of the lane.

### Registry, pin and inventory checklist

Ordered. "New module" = a new file under `us_runtime/`. "New column" = a new
exported frame column reaching the release H5.

| # | Entry | `file:line` | Applies to |
| --- | --- | --- | --- |
| 1 | Producer source pin (SHA-256 per file) — add the new module; adding a 7th entry | `packages/microcosm-data/src/microcosm/data/source_enrichment.py:120-127` | module |
| 2 | Enrichment operation name allowlist | `source_enrichment.py:296-297` | column |
| 3 | Enrichment expected counts | `source_enrichment.py:111-118` | column |
| 4 | Adapter generated-variable audit — the `(names, entity, dtype, period, formula_owned)` tuple list; `is_spm_independent_minor_role` sits at `:214` as the precedent | `packages/microcosm-frame/src/microcosm/frame/adapters/policyengine_us.py:156-233` | column |
| 5 | Adapter pinned engine-source digests — `_GENERATED_SOURCE_SHA256`, `_GENERATED_SPM_SOURCE_SHA256` / `_GENERATED_SPM_SOURCE_VERSION` (`"1.0.0"`); `_audit_pinned_sources` fails closed on any drift | `policyengine_us.py:150-155`, `:264-294` | column (on any engine bump) |
| 6 | Release input coverage manifest — a `columns` entry with `status` | `packages/microcosm-build/src/microcosm/build/us/release_input_coverage_manifest.json` (`"columns"` map) | column |
| 7 | Release input coverage checker | `packages/microcosm-build/src/microcosm/build/us_runtime/release_input_coverage.py` | column |
| 8 | Validation input coverage | `us_runtime/validation_input_coverage.py` | column |
| 9 | Spine blindness inventory — `_OTHER_US_RUNTIME_MODULES` / `_SPINE_BLIND_OPERATOR_MODULES`; `_CLASSIFIED_US_RUNTIME_MODULES` must cover every `us_runtime` module or the test fails on both unclassified **and** stale names | `packages/microcosm-build/tests/test_us_spine_blindness.py:150-151`, `:217`, `:316-317`, `:3259`, `:3275` | module |
| 10 | Engine ABI lock (`{"engine":{"package":"policyengine-us","version":"2.2.1"}}`) | `packages/microcosm-build/src/microcosm/build/us/engine_abi.lock.json:1` | column (on engine bump) |
| 11 | Country package pin | `packages/microcosm-build/src/microcosm/build/us/country_package.json` | column (on engine bump) |
| 12 | Engine specifiers — three files, all `policyengine-us>=2.2.1,<3` | `packages/microcosm-build/pyproject.toml:33`, `packages/microcosm-frame/pyproject.toml:18`, `packages/microcosm-data/pyproject.toml:30` | column (on engine bump) |
| 13 | `uv.lock` re-lock | `uv.lock` | column (on engine bump) |
| 14 | Spec identities — the seven attested artifacts; a `us_runtime` module that a kernel node keys to moves its `spec_sha256` | `docs/spec-engine.md`, `packages/microcosm-build/src/microcosm/build/us/spec/*.yaml` | module, **if** kernel-attested |
| 15 | Spec inventory coverage test | `packages/microcosm-build/tests/test_spec_engine_inventory_coverage.py` | module |
| 16 | CI test grouping — `test_us_spm_universe_source.py` → suffix `s…` → the `us-qs` engine group | `tools/ci_test_groups.py:126-141`; verify with `tools/ci_test_groups.py --verify` | module |
| 17 | Changelog fragment | `changelog.d/` | both |
| 18 | `CLAUDE.md` if the release flow changes | `CLAUDE.md` | both |

**Two entries it must NOT appear in.** `us/spec/imputation.yaml` (which keys
QRF modules — e.g. `:6528`, `module: microcosm.build.us_runtime.adult_care`)
and any calibration target surface. A source declaration is neither.

**And a third, which is a genuine trap.** `spine_agreement` gates every
*registered* transferred/imputed/seeded/simulated surface, and it handles
categorical columns:

```
packages/microcosm-build/src/microcosm/build/us_runtime/spine_agreement.py:17-21
Categorical surfaces instead compare the complete weighted category
distribution by total-variation distance, which must be no greater than
``0.25``. Declared joint categorical groups are additionally compared as
tuples, so equal marginals cannot conceal invalid cross-column combinations.
```

A new categorical `spm_unit` column looks exactly like something that belongs
there. It does not. The universe status is *intended* to differ by spine —
that is its entire content — and registering it as an agreement surface would
assert that ASEC and ACS should agree about a fact they are defined to
disagree about. (The TVD would pass today at roughly 0.003, which makes it
worse, not better: it would pass quietly and then fail the day a spine with
more group quarters is added.) Leave it unregistered and say so in the module
docstring, or the next person will add it.

**Packaging.** Item 6 adds no new *file* under `build/us/` — it edits an
existing JSON — so the two-place package-data declaration
(`packages/microcosm-build/pyproject.toml:64-67`, `packages = ["src/microcosm"]`
plus the `force-include` table) does not move. If the design later grows a new
JSON sidecar under `build/us/`, it does.

---

## 4. The engine-version problem

**The pin is not the blocker. The blocker is that the engine variable has a
formula.**

On the engine PR:

```
policyengine-us#9462
policyengine_us/variables/household/income/spm_unit/spm_unit_spm_universe_status.py:20-21
    def formula(spm_unit, period, parameters):
        return default_spm_universe_status(spm_unit)
```

That formula is a *default supplier*, not a computation — it exists because a
static `default_value` cannot be context-dependent, and the design needs
dataset → `UNRESOLVED` but household situation → `INCLUDED`:

```
policyengine-us#9462  policyengine_us/spm.py:61-65
    values = unit.simulation.tax_benefit_system.variables[
        "spm_unit_spm_universe_status"
    ].possible_values
    status = values.UNRESOLVED if unit.simulation.is_over_dataset else values.INCLUDED
    return unit.filled_array(status.index)
```

Microcosm's adapter cannot see that distinction. It classifies any variable
carrying a formula as formula-owned:

```
packages/microcosm-frame/src/microcosm/frame/adapters/policyengine_us.py:529-543
def _is_engine_computed(variable: Any, period: int | str | None = None) -> bool:
    if getattr(variable, "adds", None) or getattr(variable, "subtracts", None):
        return True
    if period is not None:
        return variable.get_formula(str(period)) is not None
    ...
```

and `write_dataset` refuses the export outright when a formula-owned column is
present (`policyengine_us.py:955-987`), with:

> `Export contract violated; nothing was written. ... formula-owned column(s) present: ['spm_unit_spm_universe_status']; ...`

The refusal is deliberate and documented: "persisting a formula-owned variable
as a dataset input pins its baseline and masks reforms"
(`policyengine_us.py:693-696`). It is also the *right* rule in general. It just
mis-fires on a variable whose formula supplies a default that a dataset input
is meant to override.

So, bluntly: **bumping the pin to a release containing #9462 as currently
drafted would not enable the export. It would turn a "variable unknown" failure
into a "formula-owned column present" failure.** This needs resolving before
the engine PR merges, not after, and it is an upstream conversation.

Three resolutions, best first:

**(i) Upstream marker, adapter honours it.** Add a class attribute on the
engine variable — e.g. `is_source_declaration = True` — and teach
`_is_engine_computed` to treat a so-marked variable as an input leaf. This
keeps Microcosm's rule introspective (no hand-maintained list, which is the
whole point of microcosm#301, `policyengine_us.py:693-700`), and it gives every
future source-declared-with-a-default variable the same door. It costs a small
upstream change on a PR that is already open and already conflicted against
main, so the marginal cost is near zero *now* and much higher after it merges.

**(ii) Upstream drops the formula.** Use the static `default_value =
UNRESOLVED` and move the household-situation `INCLUDED` default into
`spm_universe_mask` (which already branches, `policyengine_us/spm.py:68-77`).
Cleanest from Microcosm's side — nothing changes here at all — but it moves
engine behaviour, and household-situation semantics are the engine's call, not
ours.

**(iii) Microcosm-side allowlist.** A `_SOURCE_DECLARED_INPUT_COLUMNS`
frozenset, the complement of `_FORMULA_OWNED_COMPAT_COLUMNS`, excluded from
`_engine_computed_columns` and re-included in `variables()`. Works without any
upstream change and is a ~10-line diff. It also reintroduces precisely the
hand-written list that `formula_owned_outputs` was built to eliminate, and it
will go stale. Acceptable as a *fallback*, and as a bridge if the engine
release lands before the upstream marker does — not as the plan.

**Recommendation: (i), raised on #9462 now, with (iii) held as the bridge.**

### Sequencing, given that

The brief's options (a)/(b)/(c) still apply, and the capability check the brief
hoped for **is** implementable — the adapter genuinely introspects the
installed system rather than checking a version:

```
packages/microcosm-frame/src/microcosm/frame/adapters/policyengine_us.py:673-681
        system_variables = self._tax_benefit_system().variables
        return sorted(
            name for name, variable in system_variables.items()
            if name not in _FORMULA_OWNED_COMPAT_COLUMNS
            and not _is_engine_computed(variable)
        )
```

Today's pin is `policyengine-us>=2.2.1,<3` in three `pyproject.toml` files
(`microcosm-build:33`, `microcosm-frame:18`, `microcosm-data:30`), with
`engine_abi.lock.json:1` pinning `2.2.1` exactly. 2.2.1 has no such variable.

**(a) Carry as a held-back frame column.** The producer runs and the status
lives in the frame; the adapter emits it only when the installed system
declares the variable *and* accepts it as an input. This is the right shape,
and it is the only option that lets the producer, its tests, its refusals, its
registry entries and its measurements all land and stay green now. The
capability predicate is `name in engine.variables()` — which, note, is
*exactly* the predicate that returns `False` today for the blocker reason
above, so the same check covers both the "engine too old" and "engine has it
but as a formula" cases with one line. That is a real advantage. A dataset
built now carries no status column, and a consumer on a post-#9462 engine
would find it `UNRESOLVED` and raise `SPM_UNIVERSE_REQUIRED` — correct and
loud, which is the desired failure.

**(b) Wait for the engine release and bump the pin first.** Blocks all
Microcosm work behind an upstream PR that is 218 commits behind main with 10
conflicted files, whose own CI fails only because the published default
dataset declares no scope — a circular dependency this note's producer is the
way out of. It also wastes the window in which the upstream marker (i) is
cheap to add.

**(c) Both, in order.** Ship (a) now; flip the capability check to a hard
requirement once the pin moves, so a release on a capable engine *must* export
the status rather than silently omitting it. Without that second half, (a)
degrades into a permanent silent no-op.

**Recommendation: (c).** Ship (a) immediately and open the pin-bump follow-up
as a tracked dependency, so the held-back column cannot quietly become
permanent.

One consequence worth stating plainly for a dataset built now and consumed
later: it will have **no** status column, so a future engine treats every unit
as `UNRESOLVED` and refuses SPM measurement for the whole file. That is
strictly better than the status quo (today's `SPM_COMPOSITION_REQUIRED` on the
same files) because it is a named, dataset-level contract failure with a known
remedy, rather than a composition error naming neither unit nor remedy. But it
does mean **files built between now and the pin bump are not SPM-measurable on
the new engine**, and the fiscal-refresh/source-enrichment route is what
upgrades them without a rebuild.

---

## 5. Outside housing

The engine requires, for an `OUTSIDE` unit with positive `housing_assistance`,
an explicit `spm_unit_ordinary_housing_subsidy_reported` between zero and the
assistance; a missing or invalid one raises
`SPM_ORDINARY_HOUSING_VALUE_REQUIRED` (engine doc, "Housing in ordinary
income").

**The question is whether an ACS group-quarters unit can carry positive
`housing_assistance`. The answer is: nothing in this repo guarantees it
cannot.**

`housing_assistance` is engine-computed, not a Microcosm input
(`policyengine_us/variables/gov/hud/housing_assistance.py:3-19` on the PR
branch):

```python
class housing_assistance(Variable):
    entity = SPMUnit
    defined_for = "is_eligible_for_housing_assistance"
    def formula(spm_unit, period, parameters):
        if parameters(period).gov.hud.abolition: return 0
        takes_up = spm_unit("takes_up_housing_assistance_if_eligible", period)
        return spm_unit("hud_hap", period) * takes_up
```

Microcosm supplies one leaf of that chain, and it *is* a donor-transfer target
at `spm_unit` level with no group-quarters exclusion:

```
packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:446-450
    "spm_unit": {
        # Housing-assistance receipt is source-observed in the raw pool. ...
        "benefit_participation": ("takes_up_housing_assistance_if_eligible",),
```

So an ACS group-quarters unit **can** receive `takes_up == True` from the
donor. The zero then has to come from `hud_hap`:

```
policyengine_us/variables/gov/hud/hud_hap.py:14-19
        max_subsidy = spm_unit("hud_max_subsidy", period)
        ttp = spm_unit("hud_ttp", period)
        gross_rent = spm_unit("hud_gross_rent", period)
        rent_minus_ttp = max_(0, gross_rent - ttp)
        return min_(max_subsidy, rent_minus_ttp)
```

and `hud_gross_rent` is an aggregate of two things, not one
(`policyengine_us/variables/gov/hud/hud_gross_rent.py:13`):

```python
    adds = ["pre_subsidy_rent", "hud_utility_allowance"]
```

**`pre_subsidy_rent` is genuinely protected for ACS group quarters.** There is
a named, enforced absence rule:

```
packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:1714-1720
_ACS_GQ_RENT_ABSENCE_RULE_ID = "acs_native_group_quarters_without_housing_unit"
_ACS_GQ_RENT_ABSENCE_SELECTION = "acs_typehugq_2_or_3_person"
_ACS_GQ_RENT_ABSENCE_REASON = (
    "ACS TYPEHUGQ 2/3 rows have no observed housing unit; rent must remain "
    "structurally absent rather than be synthesized as zero or donor housing."
)
```

enforced by refusing any GQ row with synthesized tenure
(`stacked_spine.py:9700-9706` and again at `:9793-9799`), and corroborated by
the transfer side, which reports that `pre_subsidy_rent` "has no donor
housing-tenure feature source" (`acs_transfer.py:917-919`).

**`hud_utility_allowance` is not protected, and it is not zero everywhere.**
It is a *Household*-entity variable set per public housing agency by bedroom
size (`policyengine_us/variables/gov/hud/hud_utility_allowance.py:9-20`),
"encoded for the counties PolicyEngine models (LA County, the Texas TDHCA
service area, and four Kansas PHAs)". A group-quarters placeholder household
in one of those counties gets a positive utility allowance from its geography
alone, with no rent and no tenure involved.

So the chain is:

```
pre_subsidy_rent = 0 (protected)  +  hud_utility_allowance ≥ 0 (NOT protected)
  → hud_gross_rent can be > 0 in LA County / TX TDHCA / four Kansas PHAs
  → hud_hap = min(max_subsidy, max(0, gross_rent − ttp)) can be > 0 if ttp is small
  → housing_assistance > 0, if is_eligible_for_housing_assistance and takes_up
```

Two hops I did **not** verify and which may or may not close the gap:
`hud_ttp`'s magnitude for a zero-income group-quarters minor (plausibly zero,
which would make `rent_minus_ttp` equal the full utility allowance — i.e. the
*worse* case), and whether `is_eligible_for_housing_assistance` excludes a
null-`tenure_type` unit. It reads `SPMUnitTenureType`
(`policyengine_us/variables/gov/hud/is_eligible_for_housing_assistance.py:5-7`),
and the GQ absence rule keeps `tenure_type` null, so the enum default may well
gate it out — **inferred, not read**. I stopped rather than guess, because the
conclusion does not depend on it.

**What must be added.** Not a claim, a gate. Before export, for every unit the
producer declares `OUTSIDE`, assert `housing_assistance == 0` — or, to keep it
inside the frame and out of an engine run, assert the *inputs* that can make it
nonzero are absent: `takes_up_housing_assistance_if_eligible` is False (or the
unit is ineligible) **and** the owning household's utility allowance is zero.
The first form is the honest one and should be preferred if a simulation is
already being run; the second is the cheap pre-export form.

If the gate ever fires, the remedy is *not* to force the input to zero. It is
either to supply the explicit
`spm_unit_ordinary_housing_subsidy_reported` the engine asks for, or to refuse
the build. The engine doc is explicit that a computed zero is not evidence:
"accepting the country's computed/input assistance of zero does not certify
observed nonreceipt; the release still must validate its source inputs."

This is the part of the design most likely to be wrong in an optimistic
reading, and it is worth one actual-data measurement before any code
(see [§7](#7-plan), M2).

---

## 6. Consumers

### `reform_validation` — silently wrong, not loudly broken

The 104 state SPM poverty levels are `statistic="rate"` specs over `in_poverty`
(`us_runtime/reform_validation.py:592-609`), evaluated by `_person_rate`:

```
packages/microcosm-build/src/microcosm/build/us_runtime/reform_validation.py:928-951
        values = baseline.calculate(level.variable, level.period, map_to="person")
        weights = np.asarray(values.weights)
        flags = np.asarray(values) > 0
        mask = np.ones(len(flags), dtype=bool)
        if level.mask_variable:
            mask &= (np.asarray(baseline.calculate(...)) > 0)
        ...
        denominator = float(weights[mask].sum())
        if denominator == 0:
            return 0.0
        return float((flags[mask] * weights[mask]).sum() / denominator)
```

Under nullable indicators, `np.asarray(values) > 0` evaluates `NaN > 0` as
`False`. Outside persons are therefore counted as **not poor** and **left in
the denominator**. Every affected state rate moves *down*, by a real number, in
a JSON that publishes fine and looks fine.

This is exactly the pattern the engine doc forbids: "Do not cast these
indicators to `bool`, negate them with `~`, or use them directly as Boolean
selection masks. Compare an observed indicator with `1` when selecting poor
units and separately retain its missingness mask."

The fix is three lines and must land in the same PR as any pin bump:

```python
observed = ~np.isnan(np.asarray(values, dtype=float))
flags = np.asarray(values) == 1
mask &= observed                 # outside persons leave the denominator
```

Two further changes in the same function:

- `if denominator == 0: return 0.0` must become a missing rate. The engine doc:
  "An empty eligible denominator yields a missing rate; serialize it as JSON
  `null`." And `write_reform_validation` writes with `allow_nan=False`
  (`reform_validation.py:1034`), so a bare `NaN` would raise at serialization
  — the `None` must be threaded explicitly through the row assembly at
  `reform_validation.py:997-1002`.
- The `mask_variable` comparison (`is_child`, `> 0`) is fine; `is_child` is a
  real boolean and is not among the nullable outputs.

`US_RELEASE_SPM_SELECTION` (`reform_validation.py:682-694`) is unaffected —
geography selection is orthogonal to universe scope — but its comment about
"a later change to the engine default cannot silently reinterpret the 104
state SPM poverty levels" is precisely the failure mode above, arriving by a
different door. Worth citing in the fix.

### Poverty is not a target — verified

The brief asserts poverty must never be a target or a release gate. That is
true at this head, and it is asserted in the code's own words:

```
packages/microcosm-build/src/microcosm/build/us_runtime/reform_validation.py:598-604
    ... compared to the Census P60-287 2022–2024 three-year-average state SPM
    rates. Poverty is nowhere in the calibration target surface, so these are
    genuinely out-of-sample; the person/child *counts* in each state are
    calibrated, which pins the denominators but not the rates.
```

`state_spm_poverty_level_specs` feeds `default_baseline_level_specs`
(`reform_validation.py:615-622`), which is a *reporting* surface. The design
must keep it that way: an `OUTSIDE` unit changing a poverty rate must never
change a weight.

Note the second-order effect the docstring itself implies: the denominators
*are* calibrated (person/child counts by state), and outside persons leave the
poverty denominator while staying in the calibrated population. So the
published rate becomes "poor persons ÷ in-universe persons", which is the
correct SPM-consistent quantity and the one Census publishes — but it is not
the same denominator the calibration pins. That is a correctness *improvement*
and a comparability *discontinuity*, and it should be stated when the rates
move, not discovered afterwards.

### `check_spm_composition` (PR #948)

PR PolicyEngine/microcosm#948, `spm-composition-preflight`, head `e03e84f37`,
open. `check_spm_composition` lands in
`packages/microcosm-build/src/microcosm/build/us_runtime/release_gate_preflight.py`
and reproduces the engine's classification over frame columns with no engine
and no solve — `adult = (age >= 18) | ((age >= 15) & role)` — grading the
selected frame when given one, because "a pool unit the selection drops never
reaches the engine" (`gh pr diff 948`, the `check_spm_composition` docstring).

Under the universe rule its verdict must become **conditional on
`INCLUDED`**: a unit outside the measurement universe has no composition
requirement, because the engine never calls the threshold provider for it. The
smallest correct change is a universe-status argument that restricts
`composition.offending` to included units, keeping the unconditional count as a
reported detail (it already reports several parallel counts in `details`).

This is a genuine convergence: #948's instrument answers "which units would
refuse?", and the producer answers "which units should be asked?". Landing the
producer without updating #948 would leave a gate refusing builds for units
the engine has agreed not to measure. **These two must be sequenced together
— see §7, PR 3.**

### The rest

`git grep` for `in_poverty` / `in_deep_poverty` / `person_in_poverty` /
`spm_unit_is_in_spm_poverty` / `spm_resources` across `packages/` and `tools/`
returns, outside tests and fixtures, only:
`us_runtime/reform_validation.py` (above),
`us/state_spm_poverty_levels.json` (its config),
`us/country_package.json`, and
`tools/generate_us_bundle_from_constants.py` (bundle generation). No gate in
`docs/gate-battery-contract.md`'s battery asserts on a poverty number. The
consumer surface is genuinely small; the risk is concentrated entirely in
`_person_rate`.

---

## 7. Plan

Measurements are counts only. Nothing here opens a payload beyond what the
named tool already does.

### Can start before the engine release

**PR 1 — `us_runtime` producer, no export.** ~400 lines + tests.
`spm_universe_source.py` with the rule, the seven refusals, and a provenance
dict in `spm_role_source.py`'s idiom. Attaches the status as a frame column;
does **not** touch the adapter. Registry entries 1, 9, 15, 16, 17 from §3.
Tests on invented fixtures: ACS housing → `INCLUDED`; ACS GQ (`TYPEHUGQ` 2 and
3 separately) → `OUTSIDE`; ASEC → `INCLUDED`; each refusal with a
minimal frame that triggers exactly it; a clone inheriting its native row's
status; and a negative control proving a zero-adult *housing* unit is
`INCLUDED` (the anti-inference test — this is the one that would have caught
the tempting wrong design in §2). Depends on nothing.

**PR 2 — outside-housing gate.** ~120 lines + tests. The §5 pre-export
assertion, plus a `docs/` note recording the `pre_subsidy_rent` /
`hud_utility_allowance` asymmetry so the next reader does not re-derive it.
Tests: an invented `OUTSIDE` unit with a positive utility allowance and
`takes_up == True` must refuse by name; the same unit with a zero allowance
must pass. Depends on PR 1.

**PR 3 — `check_spm_composition` becomes universe-aware.** ~60 lines + tests,
**in microcosm#948 or immediately after it merges**. Restricts the offending
set to `INCLUDED` units; keeps the unconditional count as a detail. Tests: a
frame with one zero-adult `OUTSIDE` unit passes; the same unit `INCLUDED`
refuses. Depends on PR 1 and on #948 landing.

**PR 4 — nullable-safe `_person_rate`.** ~40 lines + tests. The §6 fix, landed
*before* any engine bump so the bump cannot silently move 104 published rates.
Tests: an invented indicator array of `{0, 1, NaN}` must produce
poor ÷ observed, not poor ÷ all; an all-`NaN` slice must serialize as JSON
`null` through `write_reform_validation` (which will fail today on
`allow_nan=False` — that is the point of the test). Depends on nothing;
**land it early**.

**PR 5 — enrichment-lane generalization.** ~300 lines + tests. The §3
descriptor refactor: entity-parameterized, dtype-parameterized,
multi-column. Boolean/person path byte-identical, proven by the existing
tests; string/`spm_unit` path new with its own exactness proof. Registry
entries 1, 2, 3. Depends on PR 1 (for the column it will carry).

### Blocked on upstream

**U1 — raise the formula-owned collision on PolicyEngine/policyengine-us#9462.**
Not a PR here; a comment on that PR, today, proposing the
`is_source_declaration` marker (§4, resolution (i)) while the branch is still
open. This is the highest-value item in the plan per unit of effort and the
only one with a closing window.

**PR 6 — adapter capability gate.** ~80 lines + tests. Emits the status only
when `name in engine.variables()`. Trivial to write, but pointless to merge
before U1 resolves, because the predicate returns `False` for the *wrong*
reason until then. Depends on U1.

**PR 7 — pin bump + generated-variable re-audit.** Engine specifier in three
`pyproject.toml` files, `uv.lock`, `engine_abi.lock.json`,
`country_package.json`, the adapter's `_GENERATED_VARIABLE_GROUPS` tuple and
both `_GENERATED_*_SHA256` digest maps, and every spec identity those move
(§3, entries 4–5, 10–14). This is a known, documented procedure, not a
discovery task. Depends on the engine release.

**PR 8 — capability gate becomes a requirement.** ~30 lines. A release on a
capable engine must export the status. Depends on PR 6 and PR 7. Without this,
PR 6 is a permanent silent no-op.

### The measurements

| # | Measurement | For | Cost |
| --- | --- | --- | --- |
| M1 | Count native ACS households by `TYPEHUGQ` ∈ {1,2,3}, and the SPM units each resolves to, on the legacy ACS 2024 spine | PR 1 — confirms the producer's partition reproduces the known 5,246 / 1,531,614 split and that nothing lands in a fourth bucket | Reuses `audit_acs_spm_universe.py`'s loader; ~11 min, ~12 GB RSS at the measured full-run cost |
| M2 | Among ACS `TYPEHUGQ` 2/3 units: count with `takes_up_housing_assistance_if_eligible == True`, and count whose household sits in a positive-utility-allowance county | PR 2 — decides whether §5 is a live defect or a latent one | Frame columns only, no engine; seconds |
| M3 | Count `INCLUDED` units without a classified adult, on the selected frame | PR 3 — the residual after the universe rule; should be 0 on ACS housing units and 0 on the September 15 national parent | `check_spm_composition`, ~0.05 s per #948 |
| M4 | The 104 state SPM rates under the fixed `_person_rate`, against the current published values | PR 4 — sizes the discontinuity §6 predicts, before it surprises anyone | One baseline simulation; already the release's cost |

M2 is the one that can change the design. Run it first.

### What this does not do

It does not drop group quarters from any file (the fiscal population is
unchanged), does not move a weight, does not add a calibration target, does not
publish or promote anything, and does not make poverty a release gate.

---

## Open questions for Max

Listed in §-order; the recommendation is the sentence after each.

**Q-A. The formula-owned collision (§4).** Resolve upstream with an
`is_source_declaration` marker on the engine variable (i), ask upstream to drop
the formula and move the household default into `spm_universe_mask` (ii), or
add a Microcosm-side allowlist (iii)?
*Recommend (i), raised on #9462 now, with (iii) held as a bridge.* (i) keeps
Microcosm's rule introspective rather than hand-maintained, and it is cheap
only while that PR is open.

**Q-B. Sequencing (§4).** (a) held-back frame column now, (b) wait for the
engine release, or (c) both?
*Recommend (c)* — ship (a) immediately, and open the pin bump as a tracked
dependency so the held-back column cannot quietly become permanent.

**Q-C. The outside-housing gate (§5).** Assert `housing_assistance == 0` on
`OUTSIDE` units (needs a simulation), or assert the frame-side inputs that can
make it nonzero are absent (cheap, pre-export)?
*Recommend the cheap frame-side gate in PR 2, with the simulation-side
assertion added wherever a release already runs one.* Run M2 first: if it
returns zero affected units, the gate is a latent guard and can stay cheap; if
not, the design needs an explicit
`spm_unit_ordinary_housing_subsidy_reported` path and that is a larger
conversation.

**Q-D. The published-rate discontinuity (§6).** The 104 state SPM rates will
move when outside persons leave the denominator — correctly, toward the
Census-consistent quantity, but visibly.
*Recommend landing PR 4 before any pin bump and publishing M4's before/after
alongside it*, so the move is an announced consequence of a known change
rather than something noticed later in a dashboard.

**Q-E. Scope of PR 1's ASEC ruling (§1).** This note rules every ASEC record
`INCLUDED` on the strength of the Census quote plus the zero-adult
reconciliation already enforced at `spm_role_source.py:141-144`. That is a
source-universe judgement, not a measurement.
*Recommend encoding it as a named, cited constant with its own refusal* — so
that if a future ASEC vintage ever admits an institutionalized record, the
producer refuses rather than silently declaring it in-universe.
