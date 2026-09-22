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
[does not hold](#5-outside-housing) — and the reason is a live defect on
`main`, not a consequence of the universe rule — and the release's single
poverty consumer [fails silently rather than loudly](#6-consumers) under
nullable indicators, in the one code path where every neighbouring path
fails loudly.

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
reconciliation on the *native* units (`spm_role_source.py:345`), so the
property survives pooling and cloning.

This is consistent with the measured counts: the published national default
`populace-us-2024-spm-20260915` has **0** SPM units without a classified adult
over the same 166,321 persons / 59,900 units, and the July Build P donor's 28
come from the absence of the native role column, not from a universe problem.

**And the producer could not condition on an ASEC record-type field even if it
wanted to: Microcosm reads none.** `H_TYPE`, `HRHTYPE`, `H_HHTYPE`, `HUNITS`,
`H_LIVQRT` and the string "armed forces" have zero occurrences in this
repository. The ASEC *household* fields read in production source are `H_SEQ`
and `HSUP_WGT` (`asec_pool.py:243`, `:402-404`), `GESTFIPS`
(`asec_pool.py:286-292`, remapped to the frame column `state_fips`) and
`H_TENURE` (`asec_pool.py:298-304`);
`_attach_household_attributes(frame, ("state_fips", "H_TENURE"))`
(`asec_pool.py:183`) then promotes those two already-mapped columns from the
person table onto the household table rather than re-reading the raw ASEC
household table. Two artifact-gated tests additionally read the household
aggregates `HSURVAL`/`HSUR_YN`
(`test_us_survivor_benefits_exclusion.py:140,148`) and `HFINVAL`/`HFIN_YN`
(`test_us_financial_assistance_exclusion.py:147,156`). None of these is a
record-type field. `TYPEHUGQ` is an ACS PUMS field and every group-quarters
mechanism in the repo is ACS-only — do not transplant it onto the ASEC arm.
The ASEC ruling is therefore necessarily **spine-level**, which is the right
level given §1's Census finding, but it must be written as a declaration with
its own refusal rather than derived from a per-record field that does not
exist.

Three things narrow the ASEC spine, and none of them is a universe predicate:
a smoke-only head-N truncation (`asec_pool.py:245-248`), a seeded uniform
household subsample with mass renormalization on the production stacked spine
(`stacked_spine.py:635-651`), and a refusal — not a silent drop — of
non-positive household weights (`asec_checkpoint.py:479-483`). Random sampling
does not change a universe; it is safe to declare the whole spine `INCLUDED`
regardless of which subsample a build takes.

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

**5 — Release H5. `TYPEHUGQ` reaches it.** This is worth stating carefully,
because the obvious guess is wrong in both directions.

The unexpected-column gate is conditional on a *closed* contract:

```
packages/microcosm-frame/src/microcosm/frame/adapters/policyengine_us.py:958-968
        unexpected: set[str] = set()
        if contract.closed:
            allowed = (...)
            unexpected = present_columns - allowed
```

and in production the contract is not closed. Every release tool constructs the
adapter with no argument — `tools/build_us_acs_local_release.py:227`, `:303`,
`:1220`; `tools/build_us_fiscal_refresh_release.py:11306`;
`tools/_legacy/build_us_acs_multispine_base.py:361`, `:1085` — which yields
`ExportContract.empty()`, "a contract with no constraints (everything passes)"
(`packages/microcosm-frame/src/microcosm/frame/rules.py:135-137`), with
`closed` defaulting to false (`rules.py:123`). Unknown columns pass silently.

And `TYPEHUGQ` is not flagged as formula-owned either, precisely because it is
unknown to the engine: "Names unknown to the tax-benefit system are not
flagged: they cannot be classified as formula-owned here"
(`policyengine_us.py:699-701`).

**Net: the raw Census code survives end to end, on the household table, ACS
rows only. The semantic flag does not exist and the producer must define it.**
So the producer is not rescuing a fact that is about to be lost — it is
translating a raw source code into the variable, entity and vocabulary the
engine asks for. That is a weaker motivation than "otherwise the information
disappears", and the note should not overclaim it.

One consequence that must not be garbled, because it is a live footgun:
interpreting `TYPEHUGQ` on a pooled file **requires the spine tag**. ASEC rows
carry it as NaN (stage 4), so `TYPEHUGQ.isin([2, 3])` is safe but
`TYPEHUGQ == 1` means "ACS housing unit", **not** "not group quarters" — ASEC
rows fail that test too. Every existing consumer pairs the code test with a
spine test, and the producer must do the same:

```
tools/_legacy/build_us_acs_multispine_base.py:599-604
    kind = pd.to_numeric(household["TYPEHUGQ"], errors="coerce")
    gq_households = household.loc[
        household[spine_column("household")].eq(ACS_2024_1YR_SPINE)
        & kind.isin([2, 3]),
        "household_id",
    ]
```

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
`ages_changed: False` (`spm_role_source.py:357-394`). Nothing in it fits,
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
plain object column of member-name strings — there is no bytes, `EnumArray` or
fixed-width `"S"` encoding anywhere in microcosm-frame's writer. **Store
`"OUTSIDE"`, not `2`, not `"SPMUniverseStatus.OUTSIDE"`, not the label text.**
The engine reads it back with `.decode_to_str()` and compares against member
names (`policyengine-us#9462` `policyengine_us/spm.py:70-77`).

The live precedent to copy is `ssn_card_type`, which maps integer source codes
straight to member names:

```
packages/microcosm-build/src/microcosm/build/us_runtime/immigration.py:360-366
    code_to_name = {0: "NONE", 1: "CITIZEN",
                    2: "NON_CITIZEN_VALID_EAD", 3: "OTHER_NON_CITIZEN"}
    result["ssn_card_type"] = pd.Series(ssn_codes, index=result.index).map(code_to_name)
```

declared in the catalog as `dtype: string` / `unit: categorical`
(`us/spec/catalogs.yaml:1164-1173`). Note this differs from the
*enrichment-lane* storage discussed in §3: that path writes fixed-width bytes
into an existing PyTables record and rejects object dtypes outright. Two paths,
two encodings — do not carry one's rule into the other.

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
`spm_role_source.py:83-85`:

| Code | Condition |
| --- | --- |
| `SPM_UNIVERSE_UNKNOWN_HOUSEHOLD_KIND` | any in-scope ACS household row whose `TYPEHUGQ` ∉ {1,2,3} (including missing on an ACS-channel row) |
| `SPM_UNIVERSE_MIXED_HOUSEHOLD` | one household row resolving to more than one kind (cannot arise natively; reachable after a bad merge) |
| `SPM_UNIVERSE_UNIT_SPANS_KINDS` | one SPM unit whose members sit in households of different kinds |
| `SPM_UNIVERSE_EMPTY_UNIT` | a `spm_unit_id` present in the `spm_unit` table with no member in `person.person_spm_unit_id` |
| `SPM_UNIVERSE_ORPHAN_MEMBER` | a `person_spm_unit_id` absent from the `spm_unit` table |
| `SPM_UNIVERSE_UNDECLARED_SPINE` | a support channel the producer has no universe ruling for |
| `SPM_UNIVERSE_GQ_MULTI_PERSON` | a `TYPEHUGQ` 2/3 household with more than one native person (mirrors `stacked_spine.py:434-437`) |
| `SPM_UNIVERSE_DEGRADED_PARTITION` | the frame's SPM partition silently degraded to the household fallback (see below) |

`SPM_UNIVERSE_UNIT_SPANS_KINDS` is the one that earns its keep. Natively it is
unreachable — ACS GQ households have `NP == 1`. It becomes reachable the
moment a future spine, a donor merge, or a clone-index bug puts a GQ person
into a multi-person unit, and at that point silently picking a majority kind
would be a fabricated universe decision. Refuse.

`SPM_UNIVERSE_EMPTY_UNIT` and `SPM_UNIVERSE_ORPHAN_MEMBER` are listed because
the brief asks for them, and they are worth keeping even though
`spm_role_source.py:264-268` already asserts exact membership coverage — its
`set(parent.person_spm_unit_id) == set(spm.spm_unit_id)` is bidirectional, so
it refuses both directions today. Two independent assertions of the same
invariant is the right cost here.

`SPM_UNIVERSE_DEGRADED_PARTITION` closes the largest silent-failure mode in
this area, and it is not hypothetical:

```
packages/microcosm-frame/src/microcosm/frame/units.py:124-129
    * **SPM unit**: the native ``SPM_ID`` when fully present (passthrough),
      otherwise ``household_id`` (documented fallback). ... A
      partially missing ``SPM_ID`` (any NaN) also triggers the household
      fallback.
```

One NaN `SPM_ID` on one ASEC person row silently converts **every** SPM unit in
the frame into a household, and `asec_pool` explicitly tolerates NaN `SPM_ID`
when globalizing (`asec_pool.py:363-380`). A universe producer that declared
`INCLUDED` over a silently-degraded partition would be attesting to a unit
structure that does not exist. Assert the partition is native before declaring
anything over it, and refuse — do not probe, do not warn. (I did not read
`microunit.units.assign_spm_partition` itself; the fallback behaviour above is
Microcosm's own documented contract, **not** a claim about that package's
implementation.)

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

Two named non-goals. First, declaring a unit outside the measurement universe
is **not** permission to synthesize its unmeasured attributes. The graph-native
line states this as an enforced invariant in both directions — a missing role
is permitted *only* when the unit is `OUTSIDE`, and is then filled with an
explicit caller-supplied placeholder rather than a guess:

```
microcosm-native-child-source-050c58a60-20260921
packages/microcosm-build/src/microcosm/build/us_runtime/current_survey_spm_projection.py:322-327
    missing = nullable.isna().to_numpy()
    _require(
        np.all(~missing | (person_status == OUTSIDE)), "NULL_ROLE_REQUIRES_OUTSIDE"
    )
    columns = {
        ("person", ROLE_INPUT): nullable.fillna(outside_role_placeholder).astype(bool),
```

That pairing is the right shape and should be carried over: a null role inside
the universe is a defect, a null role outside it is expected, and the
placeholder that resolves it is the caller's declared choice rather than the
producer's invention.

Second, `OUTSIDE` never changes a unit's weight, its membership, or its
presence in the file: the fiscal population is unchanged, only its SPM
measurability is declared.

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
packages/microcosm-data/src/microcosm/data/h5_enrichment.py:120-140
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

Three separate things therefore change, and none of them is only a rename.

1. **Entity — the largest of the three, and it is not "smallest" anything.**
   `_TABLE` is `person/table` (`h5_enrichment.py:22`), the validator's evidence
   CSV is keyed `person_id`/`person_spm_unit_id`
   (`source_enrichment.py:160`), and `added_variable` pins entity `person`
   (`source_enrichment.py:321-329`). An `spm_unit`-entity variable is a second
   table, a second registration-attribute set and a second evidence key. It
   should be scoped and reviewed as its own piece of work, not folded into a
   generalization PR as if it were arity.
2. **Dtype — nine bool-typed sites, not one.** The 1-byte record growth is
   arithmetic, not naming: `compound.set_size(old_size + 1)`
   (`h5_enrichment.py:138`) and the splice
   `extended.view(np.uint8).reshape(-1, old_size + 1)[:, :old_size]`
   (`h5_enrichment.py:161-163`). A non-bool column changes the offset math, the
   HDF member type (`NATIVE_B8`), `FIELD_n_FILL`, the `<name>_dtype`/`_kind`/
   `_meta` attributes (`h5_enrichment.py:74-81`), the validator's bitfield
   assertion (`source_enrichment.py:182-186`), the Boolean domain check
   (`h5_enrichment.py:377`), the evidence CSV's literal `False`/`True` parse
   (`source_enrichment.py:164`), the registered-`value_type` check
   (`source_enrichment.py:1148-1155`), the `.astype(bool)` loader cast
   (`source_enrichment.py:1193-1194`) and the `(False, True)` precedence probe
   (`source_enrichment.py:1287-1293`).
3. **Arity.** `ROLE` → a sequence of `(entity, column, dtype, values)`
   descriptors; `operation` → a sorted list of declared operations;
   `EXPECTED_COUNTS` (`source_enrichment.py:111-118`) → keyed per variable.
   The preservation report's `role_sha256`, `appended_field` and
   `record_size_increase_bytes: 1` (`h5_enrichment.py:400-408`) are compared
   for exact equality against the producer's recorded copy
   (`source_enrichment.py:365-369`), so they are contract, not cosmetics.

**One hard constraint that shapes all of it: the lane cannot be run twice,
once per variable.** The parent is pinned to one exact pre-role Build P digest
(`source_enrichment.py:56-58`, `tools/build_us_spm_role_enrichment.py:117-118`)
and the writer refuses a parent that already carries the column
(`h5_enrichment.py:98-99`). Two columns means **one pass, one new H5, one new
release id** — so the arity generalization is not optional convenience, it is
the only shape that works.

**Smallest safe generalization:** make `append_native_spm_role` a thin
compatibility wrapper over `append_native_source_columns(parent, candidate,
columns=[...])`, where each descriptor declares its entity table, its HDF
member type, and its values; keep the *existing* boolean/person path
byte-identical and prove it with the existing tests; add the string and
`spm_unit` paths as new code with their own exactness proofs. Generalize the
descriptor list, not the verification.

Two constraints on where the shared pieces live. The writer has no path for an
object or variable-length dtype: it grows the record by raw byte arithmetic
(`compound.set_size(old_size + 1)`, `h5_enrichment.py:138`) and splices rows as
flat bytes (`extended.view(np.uint8).reshape(-1, old_size + 1)[:, :old_size]`,
`:161-163`), which a pointer-backed field cannot express, and
`compare_h5_enrichment` rebuilds the expected compound type by the same size
arithmetic (`:344-357`). So the status must be a fixed-width byte string. The
module's two explicit object rejections do **not** cover the appended column —
`:100-101` guards the *parent* table (called on `parent[_TABLE]` at `:124` and
`:321`), and `:221-222` guards attribute and non-person-table dataset values
(`:250`, `:300`, `:380`) — so the generalized descriptor list needs its own
dtype guard rather than inheriting one. Size it to the full engine domain,
not to what the producer emits: `"UNRESOLVED"` is 10 bytes, so `S10`, even
though a producer never writes that value (§2). Sizing to the emitted set
(`"INCLUDED"`, 8 bytes) would silently truncate any later read-back of a
defaulted value. And
the shared constant must live in `microcosm-data` and be imported by
`microcosm-build`, never the reverse: the data shard deliberately does not
depend on the build shard, and a build test checks the resulting parity
(`source_enrichment.py:80-82`); `docs/shared-constants.md:12-13` requires the
single canonical definition to live in the lowest package dependency shared by
all consumers, and `:21-22` requires a unit test whenever a consumer derives a
second view of it.

**Do not loosen** the single-parent exactness core: the SHA-256 checks before,
during and after the copy (`h5_enrichment.py:118-119`, `132-133`, `185-186`),
`O_CREAT | O_EXCL` destination creation (`h5_enrichment.py:128`, which "also
refuses aliases/symlinks to the parent"), the unlink-on-any-exception
(`h5_enrichment.py:190-192`), the schema-5 inheritance assertions
(`source_enrichment.py:304-320`), and `all_preexisting_variables_exact`
(`h5_enrichment.py:394`, enforced by the exact-equality comparison of the whole
preservation report at `source_enrichment.py:365-369`). Those are not
single-variable; they are
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
| 6 | Release input coverage manifest — **generated, and a closed surface**: add the name to `POST_REFERENCE_ECPS_REQUIRED_INPUTS` in *both* copies, then regenerate. Declared columns must equal the eCPS populated layers ∪ that set (`release_input_coverage.py:681`, `:686-695`), and the committed file is asserted against the generator (`tests/test_release_input_coverage.py:1534-1543`), so it cannot be hand-edited | `us_runtime/release_input_coverage.py:141-161` **and** `tools/build_us_release_input_coverage_manifest.py:69-83`, then regenerate `us/release_input_coverage_manifest.json` | column |
| 7 | Release input coverage checker | `packages/microcosm-build/src/microcosm/build/us_runtime/release_input_coverage.py` | column |
| 8 | Validation input coverage — a *curated* leaf→provision registry (`:106`, docstring `:23-33`), checked registry → declared `source_stages.json` outputs (`:179`, `:220-253`), never exported-column → registry. `assert_validation_leaf_registry_current` (`:310-380`) rejects any leaf the engine computes with a formula (`:362`) | `us_runtime/validation_input_coverage.py:106`, `:310-380` | only a formula-free input leaf whose absence zeroes a scored validation row — **not** this column while §4 is unresolved |
| 9 | Spine blindness inventory — `_OTHER_US_RUNTIME_MODULES` / `_SPINE_BLIND_OPERATOR_MODULES`; `_CLASSIFIED_US_RUNTIME_MODULES` must cover every `us_runtime` module or the test fails on both unclassified **and** stale names | `packages/microcosm-build/tests/test_us_spine_blindness.py:150-151`, `:217`, `:316-317`, `:3259`, `:3275` | module |
| 10 | Engine ABI lock (`{"engine":{"package":"policyengine-us","version":"2.2.1"}}`) | `packages/microcosm-build/src/microcosm/build/us/engine_abi.lock.json:1` | column (on engine bump) |
| 11 | Country package resource inventory — the closed `{path, kind, schema_id}` file set; it holds **no** engine pin (its only version field is `"schema_version": 1`), so an engine bump moves nothing here. An undeclared or missing packaged file fails `_assert_file_closure` ("country package file closure failed") | `us/country_package.json`, generated from `tools/generate_us_bundle_from_constants.py:138`, `:258-260`; enforced at `packages/microcosm-build/src/microcosm/build/spec_engine/loader.py:209-223` | a new packaged file under `build/us/` — **not** an engine bump |
| 12 | Engine specifiers — three files, all `policyengine-us>=2.2.1,<3` | `packages/microcosm-build/pyproject.toml:33`, `packages/microcosm-frame/pyproject.toml:18`, `packages/microcosm-data/pyproject.toml:30` | column (on engine bump) |
| 13 | `uv.lock` re-lock | `uv.lock` | column (on engine bump) |
| 14 | Spec identities — the seven attested artifacts; a `us_runtime` module that a kernel node keys to moves its `spec_sha256` | `docs/spec-engine.md`, `packages/microcosm-build/src/microcosm/build/us/spec/*.yaml` | module, **if** kernel-attested |
| 15 | Spec inventory coverage test — `EXPECTED_CHECKS` / `EXPECTED_COUNTS` are computed from the compiled bundle, not from a filesystem scan, so they move only when a spec object count or digest moves | `packages/microcosm-build/tests/test_spec_engine_inventory_coverage.py:27-69`, `:105-141` | module, **if** the spec keys it (strictly downstream of 14) |
| 16 | CI test grouping — `test_us_spm_universe_source.py` → suffix `s…` → the `us-qs` engine group | `tools/ci_test_groups.py:126-141`; verify with `tools/ci_test_groups.py --verify` | module |
| 17 | Changelog fragment | `changelog.d/` | both |
| 18 | `CLAUDE.md` if the release flow changes | `CLAUDE.md` | both |

**Two entries it must NOT appear in.** `us/spec/imputation.yaml` and any
calibration target surface. Do not be misled by the fifteen
`module: microcosm.build.us_runtime.*` keys in `imputation.yaml` (e.g. `:6528`,
`module: microcosm.build.us_runtime.adult_care`): each is the
`runtime_resolver` of a `post_clone_source` node's `source_stage_ref`
(`:6524-6530`, `purpose: legacy_runtime_verification_evidence`), registering a
declared external source read — not a QRF. `adult_care.py` contains no QRF at
all. The file keys QRFs by model and family instead (`models:
regime_gated_qrf` at `:88-89`, `targets:` at `:128-191`). This producer
declares no new source read: it derives its status from columns already on the
frame. The precedent is exact — the repo's two existing source-declaration
modules, `spm_role_source.py` and `education_assistance_source.py`, appear
nowhere under `build/us/`, in neither `imputation.yaml`, `spec/sources.yaml`
nor `source_stages.json`. What they *are* registered in is exactly the two
entries this producer inherits: the producer source pin, which lists both by
exact path (`PRODUCER_SOURCE_FILES`, `source_enrichment.py:122-123`, mirrored
in `tools/build_us_spm_role_enrichment.py:42-43` — item 1 above), and
classification in `tests/test_us_spine_blindness.py:239` and `:296` (both
inside `_OTHER_US_RUNTIME_MODULES`, `:217` — item 9).

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
disagree about. (Because every ASEC unit is `INCLUDED`, the TVD reduces
exactly to the ACS channel's weighted `OUTSIDE` share —
`_categorical_total_variation_distance`, `spine_agreement.py:862-870`. On the
legacy ACS 2024 spine 183,206 of 1,531,614 SPM units are group quarters, 12.0%
unweighted, from the same counts audit as the 5,246 above; the *weighted* share
is unmeasured here, and group-quarters rows are not weightless, because
`acs_pums.py:590-615` substitutes the placeholder person's `PWGTP` for the
`WGTP == 0` household weight. It would pass the 0.25 tolerance today, which
makes registering it worse, not better: it would pass quietly while sitting
within a small factor of failing the day a spine with more group quarters is
added.)

The good news is that the registry is not an open door: it must *exactly*
cover the chartered surface derived from the declared ACS transfer families,
the derived-transfer expectations, the take-up contract and `_SIMULATED_OUTPUTS`
— so a column cannot be added to it without first being made a declared
transfer, derived, take-up or simulated target. Since the producer must never
become any of those (above), the status cannot drift into the agreement gate by
accident. Say so in the module docstring anyway, so the reasoning is on the
record rather than rediscovered.

**Packaging.** Item 6 adds no new *file* under `build/us/` — it edits an
existing JSON — so the country package's declared file closure does not move.
The wheel config never moves for a data file either: hatch ships the whole
package directory (`packages/microcosm-build/pyproject.toml:62`
`ignore-vcs = true`, `:65` `packages = ["src/microcosm"]`; the `force-include`
table at `:67` is empty), which is why the twenty-odd JSON resources already
under `build/us/` need no per-file declaration. What a *new* JSON sidecar under
`build/us/` would move is the two-place resource declaration:
`LEGACY_RESOURCE_PATHS` (`tools/generate_us_bundle_from_constants.py:138`) and
the generated `resources` list in `us/country_package.json`. That closure is
enforced by `_assert_file_closure`
(`packages/microcosm-build/src/microcosm/build/spec_engine/loader.py:209-224`),
which fails `load_bundle` with `undeclared=['<name>']`. That check also runs at
the *end* of regeneration rather than the start — `validate_generated_bundle`
is a one-line `load_bundle(US_PACKAGE_ROOT)`
(`tools/generate_us_bundle_from_constants.py:425-428`) called at `:453-454`,
after `write_generated_files` has already written every byte at `:391-393`, and
it is skippable with `--skip-validation`. So forgetting `LEGACY_RESOURCE_PATHS`
does not deadlock regeneration: it emits the bytes and then fails the closure
check. Declare the path and rerun.

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

This gate is unconditional. Per §1 stage 5 the production contract is
`ExportContract.empty()` with `closed=False`, so the unexpected-column gate
never fires — which means **formula-owned and enum-domain are the only two
gates that bite in production**, and the status column runs straight into the
first of them.

It is worth being precise about where the mismatch lives, because it is not a
bug on either side. PolicyEngine-core lets a dataset column win over a formula
through the holder cache
(`policyengine_core/simulations/simulation.py:757-760`), so the engine's design
— "the formula supplies the default, the dataset is authoritative" — is
internally coherent. Microcosm's adapter simply has no vocabulary for that
third category: it knows "input leaf" and "computed output" and nothing in
between.

**And this hits twice.** `spm_unit_ordinary_housing_subsidy_reported` — the
other input the engine asks a dataset to supply for `OUTSIDE` units (§5) — is
built the same way: `default_value = -1` *and* a `def formula`
(`policyengine_us/variables/household/income/spm_unit/spm_unit_ordinary_housing_subsidy_reported.py:5-13`).
Whatever resolves this for the status resolves it for the reported subsidy too,
which is an argument for fixing the category rather than special-casing one
name.

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
declares the variable *and* accepts it as an input.

"Held back" has to be an explicit decision, not a default, because the naive
implementation behaves perversely. On today's pin the column is **unknown** to
the engine, so `_engine_computed_columns` does not flag it — its predicate is
`column in variables and _is_engine_computed(variables[column], period=period)`
(`policyengine_us.py:1078-1084`), and an unknown name fails the first
conjunct. `_enum_domain_failures` skips it for the same reason
(`policyengine_us.py:1096-1097`: `if column in structural or column not in
variables: continue`). And the unexpected gate is off. **It would be silently written into the release
H5 as an unrecognized column.** On a post-#9462 pin it becomes known, carries a
formula, and is **refused**. So doing nothing gets *worse* when the engine
improves: harmless-but-meaningless today, hard build failure later. That
inversion is the reason to write the capability check deliberately now rather
than discover it at the pin bump. This is the right shape,
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

**Can an ACS group-quarters unit ever carry positive housing assistance after
the donor transfer? Yes. Nothing in this repo prevents it, and several things
actively require it to be decided one way or the other.**

This is the part of the brief whose expected answer ("structurally null, per
`_reviewed_limitations`") turns out to be wrong, so the chain is given in full.

### First, the two housing concepts must be kept apart

Microcosm never produces a housing *amount*. Its entire housing output surface
is five columns:

```
packages/microcosm-build/src/microcosm/build/us_runtime/housing_inputs.py:107-118
US_HOUSING_PERSON_OUTPUT_COLUMNS: tuple[str, ...] = ("pre_subsidy_rent",)
US_HOUSING_HOUSEHOLD_OUTPUT_COLUMNS: tuple[str, ...] = ("tenure_type",)
US_HOUSING_SPM_UNIT_OUTPUT_COLUMNS: tuple[str, ...] = (
    "receives_housing_assistance",
    "takes_up_housing_assistance_if_eligible",
    "spm_unit_tenure_type",
)
```

`pre_subsidy_rent` is *rent*, not subsidy. `housing_assistance` and
`spm_unit_capped_housing_subsidy` are engine-computed and exist in this repo
only as a take-up program label, an operator family name, and prose. So the
defensible sentence is **not** "Microcosm writes positive housing assistance";
it is "Microcosm writes a True receipt flag that the engine turns into a
positive capped subsidy". The engine half:

```
policyengine-us#9462  policyengine_us/variables/gov/hud/housing_assistance.py:3-19
class housing_assistance(Variable):
    entity = SPMUnit
    defined_for = "is_eligible_for_housing_assistance"
    def formula(spm_unit, period, parameters):
        if parameters(period).gov.hud.abolition: return 0
        takes_up = spm_unit("takes_up_housing_assistance_if_eligible", period)
        return spm_unit("hud_hap", period) * takes_up
```

On the ASEC donor path both booleans are the same thresholded source amount —
`SPM_CAPHOUSESUB > 0` (`housing_inputs.py:528-529`, over the SPM-unit-constant
subsidy at `housing_inputs.py:500-507`). The dollar amount never becomes a
model output column and is never transferred to ACS rows. The raw ASEC column
itself is not discarded: it is declared in the ASEC source surface
(`us/spec/sources.yaml:2385-2392`) and survives the clone on ASEC-scope person
rows as a declared post-clone input of the immigration producer
(`us/spec/imputation.yaml:9642-9649`,
`@effective:raw_person:SPM_CAPHOUSESUB`, `producing_stage:
post_clone_input_surface`, `required_scope: asec_source`;
`us_late_producer_registry.py:950-977`), which reads it as
`_float_column(person, "SPM_CAPHOUSESUB") > 0` (`immigration.py:563`). What
crosses into the housing surface is only the boolean.

### Second, the ACS native path produces no housing-assistance flag at all

ACS `RNTP`/`GRNTP` are kept as rent *predictors* and are deliberately never
mapped to `pre_subsidy_rent` (`acs_inputs.py:7-9`). On group quarters ACS `TEN`
is blank, so `tenure_type` and `spm_unit_tenure_type` come out NULL rather than
failing — only non-NaN codes are validated against the enum
(`acs_inputs.py:207-211`).

Which means every ACS housing flag arrives by **transfer from the ASEC donor**.

### Third, the transfer has no group-quarters carve-out for the flags

`takes_up_housing_assistance_if_eligible` is a hand-declared spm_unit transfer
target with no GQ condition:

```
packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:446-450
    "spm_unit": {
        # Housing-assistance receipt is source-observed in the raw pool. ...
        "benefit_participation": ("takes_up_housing_assistance_if_eligible",),
```

and `receives_housing_assistance` is a target too — auto-added as the spm_unit
family `source_operator_housing_inputs`, because the pool plan appends every
pre-clone source-operator output that is not already declared, not
ACS-native-complete, and not formula-owned
(`multispine_pool.py:755-769`). The attested spec confirms it, over **all**
recipient rows and with **no** absence rule:

```
packages/microcosm-build/src/microcosm/build/us/spec/imputation.yaml:1282-1312
- id: early/asec_survey_to_acs/spm_unit/source_operator_housing_inputs
  recipient_contract:
    selection: all_rows_in_declared_recipient_channel
  targets:
  - name: receives_housing_assistance
```

The donor pool is not a degenerate all-False draw. On the ASEC donor path both
flags carry the same `SPM_CAPHOUSESUB > 0` threshold
(`housing_inputs.py:528-529`) — they cannot differ, and a build in which they
do is a terminal failure (`housing_inputs.py:1262-1263`, raised at
`:1337-1343`) — and the build refuses unless the pool-wide receipt share falls
inside the enforced plausibility band `[0.005, 0.08]`
(`_HOUSING_ASSISTANCE_SHARE_BAND`, `housing_inputs.py:174`, checked at
`:1359-1369` and again on the PUF-tax-detail channel at `:1378-1384`). For
order of magnitude only, the pinned incumbent enhanced-CPS parity reference — a
frozen external artifact, not this build's donor — records a 2.0% receipt share
(`us/ecps_parity_reference.json:130`, scoped by that file's header at `:3`).

### Fourth, the carve-out that *does* exist is scoped by a literal string

`pre_subsidy_rent` is genuinely protected. There is a named, enforced absence
rule:

```
packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:1714-1720
_ACS_GQ_RENT_ABSENCE_RULE_ID = "acs_native_group_quarters_without_housing_unit"
_ACS_GQ_RENT_ABSENCE_SELECTION = "acs_typehugq_2_or_3_person"
_ACS_GQ_RENT_ABSENCE_REASON = (
    "ACS TYPEHUGQ 2/3 rows have no observed housing unit; rent must remain "
    "structurally absent rather than be synthesized as zero or donor housing."
)
```

But the gap-fill plan routes families into the direction that owns that rule by
comparing the **family name to the literal string `"housing"`**
(`stacked_spine.py:1868-1900`, with `_GAP_FILL_HOUSING_FAMILY = "housing"` at
`stacked_spine.py:1702`). `source_operator_housing_inputs` and
`benefit_participation` are not spelled `"housing"`, so they land in
`asec_survey_to_acs`, which is constructed with zero absence rules.

The carve-out looks concept-scoped. It is string-scoped. That is the defect.

And it cannot be widened by configuration — the absence-rule machinery is
hard-coded to that one rule and raises on any other combination:

```
packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py:9659-9667
    if (rule.rule_id != _ACS_GQ_RENT_ABSENCE_RULE_ID
        or rule.selection != _ACS_GQ_RENT_ABSENCE_SELECTION
        or rule.entity != "person"
        or rule.column != "pre_subsidy_rent" ...
```

### Fifth, the build is *required* to fill the flag

A residual null on a rule-less target is a terminal build failure
(`stacked_spine.py:10200-10207`: "undeclared gap-fill residual is forbidden").
The legacy tool says the same thing directly — anything other than
person/`pre_subsidy_rent` left unmodeled on ACS rows is a `SystemExit`
(`tools/_legacy/build_us_acs_multispine_base.py:562-571`). And the catalog
forbids absence as a representation:

```
packages/microcosm-build/src/microcosm/build/us/spec/catalogs.yaml:1549-1557
- key: spm_unit.receives_housing_assistance
  entity: spm_unit
  dtype: bool
  nullable: false
  domain: source_operator_housing_inputs
```

The repo's own architecture doc states the whole rule in one line: "every
recipient null is filled except the exact ACS group-quarters rent rule"
(`docs/us-multispine-operator-ordering.md:968`, and again at `:984`).

So the build **must** write `True` or `False` on every ACS group-quarters SPM
unit, and the draw that decides which is a QRF over a donor whose receipt share
the build pins inside [0.5%, 8%].

### And `_reviewed_limitations` does not cover it

The brief expected this record to supply the guarantee. It does not — its
`affected_columns` list tenure, rent and property tax only:

```
tools/_legacy/build_us_acs_multispine_base.py:652-677
    "id": "acs_group_quarters_housing_universe",
    "status": "reviewed_structural_absence",
    "affected_columns": {
        "household": ["tenure_type", "acs_monthly_contract_rent",
                      "acs_monthly_gross_rent", "acs_annual_property_tax"],
        "spm_unit": ["spm_unit_tenure_type"], ...
```

Neither `receives_housing_assistance` nor
`takes_up_housing_assistance_if_eligible` appears. The reviewed limitation is
real and correctly scoped to what it covers; it simply does not cover the
flags.

### The remaining engine-side hop, and why the conclusion survives it

With `pre_subsidy_rent` absent, `hud_gross_rent` is not automatically zero: it
`adds ["pre_subsidy_rent", "hud_utility_allowance"]`
(`policyengine_us/variables/gov/hud/hud_gross_rent.py:13`), and
`hud_utility_allowance` is a *Household* variable set per public housing agency
by bedroom size, "encoded for the counties PolicyEngine models (LA County, the
Texas TDHCA service area, and four Kansas PHAs)"
(`policyengine_us/variables/gov/hud/hud_utility_allowance.py:9-20`). Then
`hud_hap = min(max_subsidy, max(0, hud_gross_rent − hud_ttp))`
(`hud_hap.py:14-19`).

One hop I did **not** read and do not need to: `hud_ttp`'s magnitude for a
zero-income group-quarters minor. The eligibility hop I *did* read, and it does
not gate — `is_eligible_for_housing_assistance` returns
`receives_housing_assistance | (is_renter & is_income_eligible)`
(`is_eligible_for_housing_assistance.py:88`; the module-level
`housing_assistance_eligibility_from_income_limits` repeats it at `:66`), so a
True receipt flag makes the unit eligible irrespective of tenure. A missing
tenure would not screen it out in any case: `spm_unit_tenure_type` declares
`default_value = SPMUnitTenureType.RENTER` (`spm_unit_tenure_type.py:14`), so
an absent tenure reads as RENTER rather than as a disqualifier.
`housing_assistance`'s `defined_for` is therefore satisfied by the drawn flag
alone — which strengthens this section rather than qualifying it. `hud_ttp`
decides the *magnitude* of the leak. It does not decide its existence, because
the Microcosm-side conclusion is already established without it: a True receipt
flag on a group-quarters unit is not a structural impossibility, it is a
modelled draw the build is required to make.

### What must be added

Not a claim — a structural policy, and the repo already has the pattern to
copy. `_pregnancy_structural_policy_identity` forces `False` on structurally
ineligible rows rather than nulling them, and receipts the count:

```
packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:147-181
    "ineligible_missing_value": False,
    "qrf_scope": "one_eligible_representative_per_source_person",
```

enforced at `acs_transfer.py:1181`. A group-quarters housing rule would set
`receives_housing_assistance` and `takes_up_housing_assistance_if_eligible` to
`False` on the `acs_typehugq_2_or_3` mask, with its own receipt. That respects
`nullable: false`, satisfies the no-residual gate, and states the decision
rather than letting a QRF make it.

Four places it lands (the first three read this session, the fourth inferred):
a structural-eligibility policy plus receipt in `acs_transfer.py` alongside
`_pregnancy_structural_policy_identity`; registration in
`acs_transfer_execution_contract_identity`'s `structural_target_policies`
(`acs_transfer.py:313-320`); the stacked-spine terminal contract
(`stacked_spine.py:10085` onward); and the attested `imputation.yaml` entry.

Whatever form it takes, the remedy is **not** to assert the engine computes
zero. The engine doc is explicit that a computed zero is not evidence:
"accepting the country's computed/input assistance of zero does not certify
observed nonreceipt; the release still must validate its source inputs."

**Two adjacent risks worth recording while this is open.** `county_fips` is a
`declared_absent_engine_input` on the simulation projection
(`us/engine_abi.lock.json`, `remaining_stage_input_manifest.rows`), and the
2.x capped-subsidy path needs five-digit string county FIPS for an SPM unit
with positive housing assistance — so a group-quarters unit that draws a True
flag may hit the geography contract before the housing one. And the mapping
from Microcosm's `TYPEHUGQ` 2/3 mask to whatever the engine ultimately calls
`OUTSIDE` should be asserted, not assumed equal; today no `OUTSIDE` token
exists anywhere in this repo.

Run M2 ([§7](#7-plan)) before writing any of this. It is a frame-column
cross-tab, it costs seconds, and it converts this entire section from a
mechanism argument into a count.

## 6. Consumers

There is exactly **one** production consumer of SPM poverty in the repo, and
it is a report, never a gate: `reform_validation`'s rate path. The full
enumeration is at the end of this section. The risk is entirely concentrated
in one function.

### `reform_validation._person_rate` — the only place that fails silently

The 104 state SPM poverty levels are `statistic="rate"` specs over `in_poverty`
(`us_runtime/reform_validation.py:592-611`), evaluated by `_person_rate`
(`reform_validation.py:920-954`). The aggregation is a hand-rolled weighted
share — **not** a mean, and there is no `.astype(bool)` and no `~` negation
anywhere in the path:

```
packages/microcosm-build/src/microcosm/build/us_runtime/reform_validation.py:933-954
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

Three distinct silent failures follow, all within those twenty lines.

**(1) Nulled persons become "not poor" and stay in the denominator.**
`np.asarray(values) > 0` evaluates `NaN > 0` as `False` (IEEE 754: every
ordered comparison with NaN is false), at `reform_validation.py:935`. Every
affected state rate moves *down*, by a real number, in a JSON that publishes
fine and looks fine.

**(2) The denominator half of the universe rule has no implementation and
cannot arrive by itself.** The mask is initialised all-True over every person
(`reform_validation.py:936`) and is narrowed only by `mask_variable` and by
state. Nothing in the engine change narrows it — "outside units leave the
denominator" is a *consumer* obligation, and this is the consumer.

**(3) A fully outside slice publishes `0.0`, a real-looking 0% poverty rate —
and it does so both before and after the obvious fix.** The two routes are
different and both need closing. *Today*, every flag in the slice is `False`
(route 1) while the denominator stays positive, because the mask is all-True;
the numerator is zero and the function returns `0.0` without ever reaching the
`denominator == 0` branch. *After* narrowing the mask to observed persons, the
same slice empties the denominator and reaches
`if denominator == 0: return 0.0` (`reform_validation.py:951-953`) — and
returns `0.0` again. A fix that only corrects the denominator moves the bug
without removing it.

Contrast this with the dollar rows, and the asymmetry is the whole point: a
`statistic="total"` level goes through `.sum()`, which propagates NaN
(`reform_validation.py:649`), into `_finite`, which turns NaN into `None`
(`reform_validation.py:167-169`), into a writer with `allow_nan=False`
(`reform_validation.py:1034`). So **were a nullable measure ever to reach a
dollar row, it would surface as an explicit `null`; only the rate path
converts missingness into a plausible number.** (The dollar rows are not
themselves at risk here — they measure tax variables such as `income_tax`,
`cdcc` and `alternative_minimum_tax`, not poverty. The point is the contrast
in machinery, not a shared exposure.) This is the single most important
consumer fact in the design.

This is also exactly the pattern the engine doc forbids: "Do not cast these
indicators to `bool`, negate them with `~`, or use them directly as Boolean
selection masks. Compare an observed indicator with `1` when selecting poor
units and separately retain its missingness mask."

The fix, all inside `_person_rate`:

```python
raw = np.asarray(values, dtype=float)
observed = ~np.isnan(raw)
flags = raw == 1
mask &= observed                 # outside persons leave the denominator
...
if denominator == 0:
    return None                  # missing rate, not 0.0
```

and that `None` must propagate out through `_level_total`
(`reform_validation.py:956-976`): `_person_rate` (`:920`) and `_level_total`
(`:956`) are the two `-> float` annotations today, and both become
`-> float | None`. The row assembly needs no change — it already guards a
missing total (`None if total is None else _finite(total)`,
`reform_validation.py:998` and `:1002`, with `_finite` itself already
`-> float | None` at `:167-169`). What matters is that the missing rate reach
it as `None` rather than a bare `NaN`, because the writer serializes with
`allow_nan=False` (`:1034`). The engine doc: "An empty eligible denominator
yields a missing rate; serialize it as JSON `null`."

The `mask_variable` comparison (`is_child`, `> 0`) is left alone — `is_child`
is a real boolean and is not among the nullable outputs — but note that 52 of
the 104 rows carry it, so half the surface has a second denominator that would
need the same treatment if any masking variable ever became nullable.

`US_RELEASE_SPM_SELECTION` (`reform_validation.py:684`) is unaffected —
geography selection is orthogonal to universe scope — but its stated intent,
that "a later change to the engine default cannot silently reinterpret the 104
state SPM poverty levels", is precisely the failure above arriving by a
different door. It is also the natural place to declare a *universe* selection
alongside the geography one.

### `state_spm_poverty_levels.json`

104 entries, every one `variable: "in_poverty"`, `statistic: "rate"`,
`period: 2024`; 51 state codes plus 2 national rows; 52 overall and 52 child.
Benchmarks are Census P60-287, state rows on 2022–2024 three-year averages.

### Poverty as target and as gate — one verified, one narrower than the brief

**Never a calibration target: verified.** `git grep -i poverty` returns zero
hits across `microcosm-calibrate`, `microcosm-fit`, `microcosm-frame` and
`microcosm-graph`, and zero in `fiscal_targets.py` and `target_aging.py`. The
code says so itself:

```
packages/microcosm-build/src/microcosm/build/us_runtime/reform_validation.py:598-604
    ... Poverty is nowhere in the calibration target surface, so these are
    genuinely out-of-sample; the person/child *counts* in each state are
    calibrated, which pins the denominators but not the rates.
```

**Never a release gate: true today, but not a standing principle — and the
brief's phrasing should be narrowed.** No `us/gates.json` exists at all, and
the gate vocabulary is a closed frozenset with no poverty member
(`packages/microcosm-build/src/microcosm/build/country_spec.py:112-145`,
`ALLOWED_GATE_FUNCTIONS`). But the doctrine document explicitly reserves the
right:

```
docs/us-fact-to-target.md:34-36
Release gates may *fail* a certification on a held-out poverty regression;
*fitting* the statistic is categorically different and prohibited.
```

The prohibition is on **fitting**, not on gating. So the correct standing
statement is: *poverty is never a calibration target, and is not a gate today;
gating on a held-out poverty regression remains permitted and would be a
deliberate future decision.* The design must not foreclose it, and must not
overstate it either.

**Second-order effect, worth stating before the numbers move.** The
denominators *are* calibrated (person and child counts by state), and outside
persons leave the poverty denominator while remaining in the calibrated
population. The published rate becomes "poor persons ÷ in-universe persons" —
the SPM-consistent quantity Census publishes, and a correctness *improvement*
— but it is no longer the denominator the calibration pins. That is a
comparability discontinuity, and it should be announced, not discovered.

**Publication does not catch it.** The publication gate reads
`reform_validation.json` but keys only on `out_of_sample_simulated`
(`packages/microcosm-data/src/microcosm/data/publish_cli.py:141`), never on a
poverty value. A release whose 104 rates are silently deflated publishes
cleanly.

### `check_spm_composition` (PR #948)

PR PolicyEngine/microcosm#948, `spm-composition-preflight`, head `e03e84f37`,
base `main`, OPEN and **draft on purpose** — its body ends "Draft on purpose:
not ready, not to be merged."

`check_spm_composition` lands in
`packages/microcosm-build/src/microcosm/build/us_runtime/release_gate_preflight.py`
and reproduces the engine's classification over frame columns with no engine
and no solve — `adult = (age >= 18) | ((age >= 15) & role)` — grading the
selected frame when given one, because "a pool unit the selection drops never
reaches the engine". It asserts no poverty number: it checks a *precondition*
for the 104 rows being computable at all.

**Under the universe rule it would over-refuse.** `_spm_composition` grades
every `spm_unit` row with no universe predicate whatsoever — it reads only
person `age`, the role/head/spouse columns, and the membership column. The
smallest correct change is a universe-status argument restricting
`composition.offending` to `INCLUDED` units, keeping the unconditional count as
a reported detail (it already reports several parallel counts in `details`).

**And there is a direct collision worth resolving explicitly.** #948's
`SPM_COMPOSITION_REMEDY` text declares that re-grouping child-only SPM units
is *not* a remedy, precisely **because** doing so "changes the poverty
measurement the 104 state SPM poverty levels exist to" track. The universe
rule does exactly that: it removes those units from measurement. So the
universe rule is, by #948's own criterion, the thing #948 rules out — unless
the distinction is stated. The distinction is real and should be written into
that remedy text: re-grouping changes *which unit a person is measured in*,
which is a fabrication; a universe declaration changes *whether the source
measures them at all*, which is a source fact. These two must land together
(§7, PR 3).

### Full consumer enumeration

`git grep -n -E "in_poverty|in_deep_poverty|person_in_poverty|spm_unit_is_in_spm_poverty|poverty_rate|spm_resources|spm_poverty"` over
`packages/`, `tools/`, `experiments/` and `docs/`:

| Consumer | Class | Effect of the change |
| --- | --- | --- |
| `us_runtime/reform_validation.py:47`, `:586-611`, `:920-954`, `:956-1010` | **report** (release path) | The three silent failures above. Must be fixed. |
| `us/state_spm_poverty_levels.json` | config | 104 rows; unchanged, but its rates move. |
| `tools/build_us_fiscal_refresh_release.py:260`, `:263-264`, `:7475-7521`, `:11731-11742` | report (invokes the above) | Inherits the fix. |
| `us_runtime/spm_resources.py:44-134` | report library, **zero production consumers** (tests only) | A second, independent poverty-rate implementation. Needs the same universe treatment *if ever wired in*; today it is dead and should be left alone or deleted, not half-fixed. |
| `experiments/957-static-aging/benchmark.py:421-422`, `:452-457` | comparison script | Maps the spm_unit variable to person and takes weighted MicroSeries means, including boolean-indexed sub-means that would each need their own universe denominator. |
| `us_runtime/reform_coverage_smoke.py:123` | **gate**, but scores dollars (`spm_unit_benefits`), never a poverty number | Fail-closed under NaN (`NaN >= min_abs_effect` is False). Safe by accident, but safe. |
| `packages/microcosm-build/tests/test_reform_validation.py:1203-1247` | test | The only place denominator semantics are pinned numerically (integer 1/0 indicators, no null case). Its four assertions are *invariant* under the fix — with no NaN present, poor ÷ observed equals poor ÷ all — so PR 4 adds null-bearing cases here rather than repairing a red test. This is where the null case belongs. |
| `us/country_package.json`, `tools/generate_us_bundle_from_constants.py` | bundle generation | No behavioural change. |

No gate in `docs/gate-battery-contract.md`'s battery asserts on a poverty
number.

One further note on nullability's ownership: the release cannot pin it by
writing a column. `policyengine-us` 2.0.0 "rejects derived SPM outputs
(including the `in_poverty` alias) from stored datasets and requires observed
county inputs" (`packages/microcosm-data/pyproject.toml:24-26`). The indicator
is engine-derived at read time, so its nullability is an engine-side property
throughout.

## 7. Plan

Measurements are counts only. Nothing here opens a payload beyond what the
named tool already does.

### Can start before the engine release

**PR 1 — `us_runtime` producer, no export.** ~400 lines + tests.
`spm_universe_source.py` with the rule, the eight refusals, and a provenance
dict in `spm_role_source.py`'s idiom. Attaches the status as a frame column;
does **not** touch the adapter. Registry entries 1, 9, 16, 17 from §3.
Tests on invented fixtures: ACS housing → `INCLUDED`; ACS GQ (`TYPEHUGQ` 2 and
3 separately) → `OUTSIDE`; ASEC → `INCLUDED`; each refusal with a
minimal frame that triggers exactly it; a clone inheriting its native row's
status; and a negative control proving a zero-adult *housing* unit is
`INCLUDED` (the anti-inference test — this is the one that would have caught
the tempting wrong design in §2). Depends on nothing.

**PR 2 — group-quarters housing structural policy.** ~250 lines + tests, and
larger than the brief assumed. Not a pre-export assertion: a structural
eligibility policy in `acs_transfer.py` in the shape of
`_pregnancy_structural_policy_identity`, forcing `receives_housing_assistance`
and `takes_up_housing_assistance_if_eligible` to `False` on the
`acs_typehugq_2_or_3` mask with its own receipt, plus registration in
`structural_target_policies` (`acs_transfer.py:313-320`), the stacked-spine
terminal contract (`stacked_spine.py:10085` onward) and the attested
`imputation.yaml` entry. Setting `False` — rather than nulling — is forced by
`catalogs.yaml:1549-1557` (`nullable: false`) and by the no-residual gate
(`stacked_spine.py:10200-10207`). Tests: an invented ACS group-quarters unit
must come out `False` on both flags with the count receipted; a housing unit
must be untouched; the policy must refuse if the mask is empty when group
quarters are present (so it cannot silently no-op). Depends on PR 1 and on M2.
**This is a defect on `main` independent of the universe rule** — the QRF is
drawing a housing-receipt flag for records with no housing unit today — so it
stands on its own and can be argued separately if the universe work slips.

**PR 3 — `check_spm_composition` becomes universe-aware.** ~60 lines + tests,
**in microcosm#948 or immediately after it merges**. Restricts the offending
set to `INCLUDED` units; keeps the unconditional count as a detail. Tests: a
frame with one zero-adult `OUTSIDE` unit passes; the same unit `INCLUDED`
refuses. Depends on PR 1 and on #948 landing.

**PR 4 — nullable-safe `_person_rate`.** ~40 lines + tests. The §6 fix, landed
*before* any engine bump so the bump cannot silently move 104 published rates.
Tests: an invented indicator array of `{0, 1, NaN}` must produce
poor ÷ observed, not poor ÷ all; an all-`NaN` slice must serialize as JSON
`null` through `write_reform_validation`. Note what that second test actually
pins: today an all-`NaN` slice returns `0.0` (every flag false, denominator
positive) and serializes *cleanly*, so the test fails on the published value —
`0.0` where `null` belongs — not on an `allow_nan=False` error.
`allow_nan=False` (`reform_validation.py:1034`) bites only on a bare `NaN`,
which is exactly why the fix returns `None`. Depends on nothing;
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
`pyproject.toml` files, `uv.lock`, `engine_abi.lock.json`, the adapter's
`_GENERATED_VARIABLE_GROUPS` tuple and both `_GENERATED_*_SHA256` digest maps,
and every spec identity those move (§3, entries 4–5, 10, 12–14 — *not* 11,
which carries no engine pin). This is a known, documented procedure, not a
discovery task. Depends on the engine release.

**PR 8 — capability gate becomes a requirement.** ~30 lines. A release on a
capable engine must export the status. Depends on PR 6 and PR 7. Without this,
PR 6 is a permanent silent no-op.

### The measurements

| # | Measurement | For | Cost |
| --- | --- | --- | --- |
| M1 | Count native ACS households by `TYPEHUGQ` ∈ {1,2,3}, and the SPM units each resolves to, on the legacy ACS 2024 spine | PR 1 — confirms the producer's partition reproduces the measured 1,348,408 housing-unit / 183,206 group-quarters split of the 1,531,614 native ACS SPM units, that the 5,246 zero-classified-adult units (§2) are a strict *subset* of the group-quarters side rather than the bucket itself, and that nothing lands in a fourth bucket | Reuses the loader of `audit_acs_spm_universe.py` — an out-of-repo counts-only scratch tool, not a committed one; measured full-run cost 678 s wall / 12.2 GB peak RSS. The in-repo starting point is `_acs_group_quarters_counts` (`tools/_legacy/build_us_acs_multispine_base.py:757-785`), which already returns household / person / `spm_unit` counts for `TYPEHUGQ` ∈ {2,3} on a built frame and needs only the `TYPEHUGQ == 1` arm |
| M2 | Among ACS `TYPEHUGQ` 2/3 units: count with `receives_housing_assistance == True` and with `takes_up_housing_assistance_if_eligible == True`, on a built pool | PR 2 — converts §5 from a mechanism argument into a count, and sizes the defect | Frame columns only, no engine; seconds. No receipt or gate reports this cross-tab today, so the realized number is currently unknown |
| M3 | Count `INCLUDED` units without a classified adult, on the selected frame | PR 3 — the residual after the universe rule; should be 0 on ACS housing units and 0 on the September 15 national parent | `check_spm_composition`, ~0.05 s per #948 |
| M4a | Re-run the 104 state SPM rates under the fixed `_person_rate` on today's pin and diff against the current published values | PR 4 — a regression check that the fix moves **nothing** today: `in_poverty` is `value_type = bool` on 2.2.1, so nothing is NaN, `observed` is all-True and `raw == 1` equals `raw > 0`. A non-zero diff would itself be a finding | One baseline simulation; already the release's cost |
| M4b | The 104 rates recomputed with `OUTSIDE` persons removed from the denominator — before the bump by masking with PR 1's held-back universe column outside `_person_rate`, after it by `_person_rate` itself — against the current published values | PR 7 (with PR 6) — this is where the discontinuity §6 predicts actually appears; sizes it before it surprises anyone | One baseline simulation plus the frame column; already the release's cost |

M2 is the one that can change the design. Run it first.

### What this does not do

It does not drop group quarters from any file (the fiscal population is
unchanged), does not move a weight, does not add a calibration target, and does
not publish or promote anything.

It also does not make poverty a release gate — but note the precise claim, per
§6: fitting a poverty statistic is prohibited doctrine
(`docs/us-fact-to-target.md:34-36`), while *gating* on a held-out poverty
regression is explicitly reserved as permitted. Nothing here forecloses that
future choice; nothing here takes it either.

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

**Q-C. Group-quarters housing (§5).** The brief expected group-quarters
housing inputs to be structurally null. They are not: `pre_subsidy_rent` is
carved out by a rule scoped to the literal family name `"housing"`, while
`receives_housing_assistance` and `takes_up_housing_assistance_if_eligible`
are rule-less QRF targets over all ACS rows, `nullable: false`, that the build
is *required* to fill. So today's ACS builds are drawing a housing-receipt
flag for records with no housing unit. Force both flags `False` on the
group-quarters mask (a structural policy, PR 2), or supply an explicit
`spm_unit_ordinary_housing_subsidy_reported` path for units that draw True?
*Recommend forcing `False`, after M2.* It matches the reviewed limitation's
own reasoning — no observed housing unit — and reuses the pregnancy policy
pattern already in the repo. If M2 returns a large count, that is a finding
about the donor transfer worth reporting on its own, not just an input to this
design. And worth deciding explicitly: **this is a defect on `main` today**,
so it may deserve its own issue rather than riding the universe lane.

**Q-D. The published-rate discontinuity (§6).** The 104 state SPM rates will
move when outside persons leave the denominator — correctly, toward the
Census-consistent quantity, but visibly.
*Recommend landing PR 4 before any pin bump — where it is numerically inert
(M4a) — and publishing M4b's before/after with the pin bump (PR 7), the point
at which the rates actually move*, so the move is an announced consequence of a
known change rather than something noticed later in a dashboard.

**Q-E. Scope of PR 1's ASEC ruling (§1).** This note rules every ASEC record
`INCLUDED` on the strength of the Census quote plus the zero-adult
reconciliation already enforced at `spm_role_source.py:141-144`. That is a
source-universe judgement, not a measurement.
*Recommend encoding it as a named, cited constant with its own refusal* — so
that if a future ASEC vintage ever admits an institutionalized record, the
producer refuses rather than silently declaring it in-universe.
