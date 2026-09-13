"""Canonical survey sex, qualified from the retained current source owners.

Scope fence. This module is descriptive. It issues no source, no population
and no release authority, it reads no member bytes of its own, and it is
deliberately not wired into the accepted country enrichment host. It borrows
two maintained owners and re-states neither of their contracts:

* ASEC sex comes from :mod:`.current_asec_demographics`, which reconstructs the
  real parent through :mod:`.asec_demographic_source`. Binding needs a printed
  ``A_SEX`` code **and** a printed ``AXSEX`` code; allocation is a separate
  state that survives an unbound sex. Nothing here maps "not 2" onto male, and
  code ``0`` stays null.
* ACS sex is the value the current source modules already qualify: ``SEX`` is a
  required person column whose source chunks admit only ``1``/``2``
  (:mod:`.acs_pums`), and :mod:`.acs_inputs` records the canonical mapping
  ``SEX == 2`` into ``is_female``. That relation is **verified against the live
  issued Frame here**, not assumed from those modules' text.

What this module refuses to assume, stated once:

* ACS allocation provenance is **unresolved**. No ``FSEXP`` column exists in the
  declared ACS readset anywhere in this runtime, so an ACS row's allocation
  knownness is false. An absent allocation flag is neither a male value nor an
  invented "not allocated" code, and the label stays "Census-published ACS",
  never "respondent-unallocated". Supplying real ACS allocation evidence is a
  separate, separately reviewed source projection.
* The two surveys therefore do **not** have equivalent allocation evidence
  today, and no receipt written here may claim they do.
* No age gate, headship inference, learned value, carried fallback or default
  fills an unresolved cell. Unresolved stays null.

Returned values are detached. A graph host must requalify the live owners and
compare materialized descendants, including after replay.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
import pandas as pd

from microcosm.graph.population import PopulationError, dtype_for_token, token_for_dtype

from . import asec_demographic_source as demographic
from . import current_asec_demographics as demographics
from . import survey_population_preparation as source
from .support_provenance import (
    spine_source_id_column,
    support_channel_column,
    support_clone_index_column,
    support_source_id_column,
)

PROTOCOL = "microcosm.us.current-survey-sex.v1"
#: The one canonical leaf this seam may write on a receiving population.
CANONICAL_COLUMN = "is_female"
#: Every other observation is namespaced so it cannot impersonate that leaf.
SOURCE_PREFIX = "sex_source_"
MAX_PERSONS = 64 * 1024**2 // 32
MAX_RECEIPT_BYTES = 64 * 1024
SURVEYS = ("acs", "asec")

SURVEY_COLUMN = SOURCE_PREFIX + "survey"
NATIVE_ID_COLUMN = SOURCE_PREFIX + "native_person_id"
CODE_COLUMN = SOURCE_PREFIX + "code"
ALLOCATION_CODE_COLUMN = SOURCE_PREFIX + "allocation_code"
BINDING_STATE_COLUMN = SOURCE_PREFIX + "binding_state"
UNBOUND_REASON_COLUMN = SOURCE_PREFIX + "unbound_reason"
ALLOCATION_STATE_COLUMN = SOURCE_PREFIX + "allocation_state"
CODE_KNOWN_COLUMN = SOURCE_PREFIX + "code_known"
VALUE_KNOWN_COLUMN = SOURCE_PREFIX + "value_known"
ALLOCATION_KNOWN_COLUMN = SOURCE_PREFIX + "allocation_known"
ORIGIN_COLUMN = SOURCE_PREFIX + "origin"
UNIVERSE_COLUMN = SOURCE_PREFIX + "universe"
OBSERVATION_YEAR_COLUMN = SOURCE_PREFIX + "observation_year"
VALUE_COLUMN = SOURCE_PREFIX + CANONICAL_COLUMN

#: The private rowwise projection, in body order, with its declared tokens.
COLUMN_TOKENS: tuple[tuple[str, str], ...] = (
    (SURVEY_COLUMN, "string"),
    (NATIVE_ID_COLUMN, "int64"),
    (CODE_COLUMN, "Int64"),
    (ALLOCATION_CODE_COLUMN, "Int64"),
    (BINDING_STATE_COLUMN, "int64"),
    (UNBOUND_REASON_COLUMN, "int64"),
    (ALLOCATION_STATE_COLUMN, "int64"),
    (CODE_KNOWN_COLUMN, "bool"),
    (VALUE_KNOWN_COLUMN, "bool"),
    (ALLOCATION_KNOWN_COLUMN, "bool"),
    (ORIGIN_COLUMN, "string"),
    (UNIVERSE_COLUMN, "string"),
    (OBSERVATION_YEAR_COLUMN, "int64"),
    (VALUE_COLUMN, "boolean"),
)
COLUMNS: tuple[str, ...] = tuple(name for name, _token in COLUMN_TOKENS)

#: ASEC allocation-state code -> the label the maintained ASEC projection
#: already publishes. Recomputed and compared against it, never replaced.
ASEC_ORIGIN_BY_ALLOCATION_STATE: dict[int, str] = MappingProxyType(
    {0: "unresolved_allocation", 1: "source_no_change", 2: "census_allocated"}
)
#: The ACS person sex codes this seam admits. They are pinned to the current
#: source modules, not to a printed dictionary page this lane did not read:
#: ``acs_pums._validate_source_chunk`` admits ``{1, 2}`` only and ``acs_inputs``
#: records the canonical transformation below.
ACS_SEX_CODES: dict[int, str] = MappingProxyType({1: "male", 2: "female"})
ACS_SEX_TRANSFORMATION = "SEX == 2"
#: Census published this ACS value; its allocation provenance is unresolved.
ACS_ORIGIN = "census_published_acs_allocation_unresolved"
#: The ACS scope is the module's required person readset, not a printed quote.
ACS_UNIVERSE = "acs_required_person_readset"
ASEC_OBSERVATION_YEAR = 2025
ACS_OBSERVATION_YEAR = 2024
INCOME_YEAR = 2024

#: The only keys a public graph receipt may carry. Every value is an aggregate
#: count, a digest, a contract reference or a closed flag; no row, identity or
#: source code belongs here.
PUBLIC_RECEIPT_KEYS = frozenset(
    {
        "protocol",
        "canonical_column",
        "canonical_dtype",
        "declared_rewrite",
        "contract_sha256",
        "projection_sha256",
        "receiving_version",
        "receiving_rows",
        "original_persons",
        "clone_indices",
        "preserved_cells",
        "filled_cells",
        "unresolved_cells",
        "acs_originals",
        "asec_originals",
        "code_known_originals",
        "value_known_originals",
        "allocation_known_originals",
        "asec_census_allocated_originals",
        "acs_allocation_provenance",
        "equivalent_allocation_evidence_claim",
        "unallocated_observation_claim",
        "source_admission_issued",
        "population_admission_issued",
        "release_eligible",
    }
)


def require(condition, reason):
    if not condition:
        raise ValueError("CURRENT_SURVEY_SEX_" + reason)


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _shared_code_tables():
    """Bind the maintained owner's code meanings instead of restating them.

    A change to any of these tables must be reviewed against this seam rather
    than silently reinterpreted here, so the pin refuses instead of drifting.
    """
    binding = dict(demographic.SEX_BINDING_STATES)
    reasons = dict(demographic.SEX_UNBOUND_REASONS)
    allocation = dict(demographic.SEX_ALLOCATION_STATES)
    require(
        binding == {0: "unbound", 1: "bound_male", 2: "bound_female"}
        and reasons
        == {
            0: "bound",
            1: "sex_code_outside_printed_codes",
            2: "allocation_flag_outside_printed_codes",
        }
        and allocation == {0: "undetermined", 1: "no_change", 2: "census_allocated"}
        and dict(demographic.A_SEX.named_codes) == {1: "Male", 2: "Female"}
        and dict(demographic.AXSEX.named_codes) == {0: "No change", 4: "Allocated"}
        and demographic.A_SEX.printed_range == (1, 2)
        and demographic.AXSEX.printed_range == (0, 4)
        and demographic.A_SEX.universe_as_printed == "All Persons"
        and list(demographic.AXSEX.unnamed_in_range_codes) == [1, 2, 3],
        "SHARED_CODE_TABLES_CHANGED",
    )
    return binding, reasons, allocation


def _code(value, reason):
    """Accept a plain integer code; a bool or float is not a source code."""
    require(type(value) is int or type(value) is np.int64, reason)
    return int(value)


def asec_sex_observation(a_sex, axsex):
    """Classify one ASEC observation from its two printed source codes.

    Binding needs both codes printed. Allocation is independent of sex
    namedness, exactly as the maintained source owner classifies it, so an
    allocated flag on an unnamed sex code stays allocated **and** unbound.
    """
    _shared_code_tables()
    a_sex, axsex = _code(a_sex, "ASEC_CODE_TYPE"), _code(axsex, "ASEC_CODE_TYPE")
    code_known = a_sex in demographic.A_SEX.named_codes
    allocation_known = axsex in demographic.AXSEX.named_codes
    allocation_state = 0
    if allocation_known:
        allocation_state = 1 if axsex == 0 else 2
    binding_state = 0
    if code_known and allocation_known:
        binding_state = 1 if a_sex == 1 else 2
    reason = 0
    if not code_known:
        reason = 1
    elif not allocation_known:
        reason = 2
    return {
        SURVEY_COLUMN: "asec",
        CODE_COLUMN: a_sex,
        ALLOCATION_CODE_COLUMN: axsex,
        BINDING_STATE_COLUMN: binding_state,
        UNBOUND_REASON_COLUMN: reason,
        ALLOCATION_STATE_COLUMN: allocation_state,
        CODE_KNOWN_COLUMN: code_known,
        VALUE_KNOWN_COLUMN: binding_state != 0,
        ALLOCATION_KNOWN_COLUMN: allocation_known,
        ORIGIN_COLUMN: ASEC_ORIGIN_BY_ALLOCATION_STATE[allocation_state],
        UNIVERSE_COLUMN: demographic.A_SEX.universe_as_printed,
        OBSERVATION_YEAR_COLUMN: ASEC_OBSERVATION_YEAR,
        VALUE_COLUMN: None if binding_state == 0 else binding_state == 2,
    }


def acs_sex_observation(sex):
    """Classify one ACS observation; its allocation provenance stays unresolved.

    The value is the one the current ACS source modules already qualify. The
    allocation state is ``undetermined`` rather than ``no_change``: this seam
    has no ACS allocation observation and must not manufacture one.
    """
    _shared_code_tables()
    sex = _code(sex, "ACS_CODE_TYPE")
    code_known = sex in ACS_SEX_CODES
    binding_state = sex if code_known else 0
    return {
        SURVEY_COLUMN: "acs",
        CODE_COLUMN: sex,
        ALLOCATION_CODE_COLUMN: None,
        BINDING_STATE_COLUMN: binding_state,
        UNBOUND_REASON_COLUMN: 0 if code_known else 1,
        ALLOCATION_STATE_COLUMN: 0,
        CODE_KNOWN_COLUMN: code_known,
        VALUE_KNOWN_COLUMN: code_known,
        ALLOCATION_KNOWN_COLUMN: False,
        ORIGIN_COLUMN: ACS_ORIGIN,
        UNIVERSE_COLUMN: ACS_UNIVERSE,
        OBSERVATION_YEAR_COLUMN: ACS_OBSERVATION_YEAR,
        VALUE_COLUMN: None if not code_known else sex == 2,
    }


def sex_contract_document():
    """The declared contract, recorded in every receipt this seam writes."""
    _shared_code_tables()
    return {
        "protocol": PROTOCOL,
        "canonical_column": CANONICAL_COLUMN,
        "canonical_meaning": "true=female; false=male; null=unresolved",
        "canonical_null_policy": (
            "preserve_unresolved; no_age_gate, headship, default, carried "
            "fallback or modelled value"
        ),
        "columns": [{"column": n, "dtype": t} for n, t in COLUMN_TOKENS],
        "shared_code_tables": {
            "binding_state": {
                str(k): v for k, v in sorted(demographic.SEX_BINDING_STATES.items())
            },
            "unbound_reason": {
                str(k): v for k, v in sorted(demographic.SEX_UNBOUND_REASONS.items())
            },
            "allocation_state": {
                str(k): v for k, v in sorted(demographic.SEX_ALLOCATION_STATES.items())
            },
        },
        "asec": {
            "value_field": demographic.A_SEX.document(),
            "allocation_field": demographic.AXSEX.document(),
            "binding_requires": ["A_SEX in printed codes", "AXSEX in printed codes"],
            "unnamed_in_range_allocation_codes": list(
                demographic.AXSEX.unnamed_in_range_codes
            ),
            "allocated_code_meaning": "census_allocated; not agent-modelled",
            "origin_labels": {
                str(k): v for k, v in sorted(ASEC_ORIGIN_BY_ALLOCATION_STATE.items())
            },
            "observation_year": ASEC_OBSERVATION_YEAR,
            "composed_stage_unbound_guard_changed": False,
        },
        "acs": {
            "value_codes": {str(k): v for k, v in sorted(ACS_SEX_CODES.items())},
            "value_authority": [
                "acs_pums: SEX is a required person column and source chunks "
                "admit only the codes 1 and 2",
                "acs_inputs: the canonical mapping is recorded as "
                + ACS_SEX_TRANSFORMATION,
            ],
            "value_relation_verified_against_issued_frame": ACS_SEX_TRANSFORMATION,
            "printed_dictionary_page_read_by_this_lane": False,
            "universe_is_printed_dictionary_quote": False,
            "allocation_field_in_declared_readset": None,
            "allocation_flag_searched": "FSEXP",
            "allocation_provenance": "unresolved",
            "allocation_knownness": False,
            "absent_allocation_flag_is_a_code": False,
            "unallocated_observation_claim": False,
            "origin_label": ACS_ORIGIN,
            "observation_year": ACS_OBSERVATION_YEAR,
        },
        "equivalent_allocation_evidence_claim": False,
        "income_year": INCOME_YEAR,
        "source_admission_issued": False,
        "population_admission_issued": False,
        "release_eligible": False,
    }


def contract_sha256():
    return _sha(source._encode(sex_contract_document(), maximum=MAX_RECEIPT_BYTES))


def _observation_table(rows, index):
    """Materialize classified observations at their declared storage exactly."""
    require(
        type(index) is pd.Index
        and index.name == "person_id"
        and str(index.dtype) == "int64"
        and index.is_unique
        and len(rows) == len(index)
        and 0 < len(index) <= MAX_PERSONS,
        "OBSERVATION_AXIS",
    )
    table = pd.DataFrame(index=index.copy())
    for name, token in COLUMN_TOKENS:
        values = [row[name] for row in rows]
        if token in ("string", "Int64", "boolean"):
            table[name] = pd.array(
                [pd.NA if v is None else v for v in values],
                dtype=dtype_for_token(token),
            )
        else:
            table[name] = np.asarray(values, dtype=dtype_for_token(token))
    require(
        tuple(table.columns) == COLUMNS
        and all(
            token_for_dtype(table[name].dtype) == token for name, token in COLUMN_TOKENS
        ),
        "OBSERVATION_STORAGE",
    )
    return table


def _projection_bytes(table):
    require(tuple(table.columns) == COLUMNS, "PROJECTION_COLUMNS")
    return table.reset_index().to_json(orient="table", index=False).encode()


def _table_stamp(table):
    return (
        tuple(table.columns),
        tuple(str(dtype) for dtype in table.dtypes),
        str(table.index.dtype),
        table.index.name,
        _sha(_projection_bytes(table)),
    )


def _check_asec_projection(values, receipt):
    """Bind the detached ASEC person values to their producer's exact receipt."""
    require(
        type(values) is demographics.CurrentAsecDemographicValues
        and type(receipt) is bytes
        and values.receipt == receipt,
        "ASEC_RECEIPT",
    )
    document = json.loads(receipt)
    require(
        _sha(values.person.reset_index(drop=True).to_json(orient="table").encode())
        == document.get("person_projection_sha256"),
        "ASEC_PROJECTION_DIGEST",
    )
    return document


def _asec_rows(selected, asec_person):
    """Recheck every raw ASEC code against the producer's published states."""
    require(
        {
            "native_person_id",
            "asec_A_SEX",
            "asec_AXSEX",
            "asec_sex_binding_state",
            "asec_sex_allocation_state",
            "is_female",
            "sex_known",
            "sex_universe",
            "sex_origin",
        }
        <= set(asec_person)
        and asec_person.index.is_unique
        and asec_person.index.name == "person_id",
        "ASEC_SOURCE_COLUMNS",
    )
    require(set(selected.index) == set(asec_person.index), "ASEC_PERSON_ROSTER")
    aligned = asec_person.reindex(selected.index)
    require(
        np.array_equal(
            aligned.native_person_id.to_numpy(dtype=np.int64),
            selected.native_person_id.to_numpy(dtype=np.int64),
        ),
        "ASEC_PERSON_JOIN",
    )
    rows = []
    for (
        native,
        a_sex,
        axsex,
        binding,
        allocation,
        female,
        known,
        universe,
        origin,
    ) in aligned.loc[
        :,
        [
            "native_person_id",
            "asec_A_SEX",
            "asec_AXSEX",
            "asec_sex_binding_state",
            "asec_sex_allocation_state",
            "is_female",
            "sex_known",
            "sex_universe",
            "sex_origin",
        ],
    ].itertuples(index=False, name=None):
        row = asec_sex_observation(a_sex, axsex)
        require(
            row[BINDING_STATE_COLUMN] == int(binding)
            and row[ALLOCATION_STATE_COLUMN] == int(allocation)
            and row[VALUE_KNOWN_COLUMN] == bool(known)
            and row[ORIGIN_COLUMN] == origin
            and row[UNIVERSE_COLUMN] == universe
            and (
                pd.isna(female)
                if row[VALUE_COLUMN] is None
                else bool(female) == row[VALUE_COLUMN]
            ),
            "ASEC_STATE_DISAGREEMENT",
        )
        rows.append({**row, NATIVE_ID_COLUMN: int(native)})
    return rows


def _acs_rows(selected, acs_person):
    """Verify the issued ACS Frame's own recorded sex relation, then keep it."""
    require(
        {"person_id", "SEX", CANONICAL_COLUMN} <= set(acs_person)
        and acs_person.index.is_unique,
        "ACS_SOURCE_COLUMNS",
    )
    native = selected.native_person_id.to_numpy(dtype=np.int64)
    require(set(native) <= set(acs_person.index), "ACS_NATIVE_JOIN")
    aligned = acs_person.reindex(native)
    codes = pd.to_numeric(aligned.SEX, errors="coerce")
    require(
        codes.notna().all()
        and codes.eq(codes.astype("int64")).all()
        and pd.api.types.is_bool_dtype(aligned[CANONICAL_COLUMN].dtype)
        and aligned[CANONICAL_COLUMN].notna().all()
        and np.array_equal(
            aligned[CANONICAL_COLUMN].to_numpy(dtype=bool),
            codes.to_numpy(dtype=np.int64) == 2,
        ),
        "ACS_SEX_IDENTITY",
    )
    rows = []
    for source_id, code, female in zip(
        native,
        codes.to_numpy(dtype=np.int64),
        aligned[CANONICAL_COLUMN].to_numpy(dtype=bool),
        strict=True,
    ):
        row = acs_sex_observation(int(code))
        require(row[VALUE_COLUMN] == bool(female), "ACS_STATE_DISAGREEMENT")
        rows.append({**row, NATIVE_ID_COLUMN: int(source_id)})
    return rows


def _selected(person):
    """Project the stacked person axis onto its channel and native identity."""
    channel, native = (
        support_channel_column("person"),
        spine_source_id_column("person"),
    )
    require(
        {"person_id", channel, native} <= set(person)
        and str(person.person_id.dtype) == "int64"
        and person.person_id.is_unique
        and str(person[native].dtype) == "int64",
        "STACKED_PERSON_AXIS",
    )
    channels = person[channel].astype(object)
    require(
        all(type(value) is str for value in channels) and set(channels) <= set(SURVEYS),
        "STACKED_CHANNEL_ROSTER",
    )
    return pd.DataFrame(
        {
            "survey": channels.to_numpy(),
            "native_person_id": person[native].to_numpy(dtype=np.int64),
        },
        index=pd.Index(person.person_id.to_numpy(dtype=np.int64), name="person_id"),
    )


def _project(person, acs_person, asec_person):
    """Pure alignment from just-qualified values; it carries no authority."""
    selected = _selected(person)
    by_survey = {name: selected.loc[selected.survey.eq(name)] for name in SURVEYS}
    require(
        sum(len(part) for part in by_survey.values()) == len(selected),
        "SURVEY_PARTITION",
    )
    classified = {}
    if len(by_survey["asec"]):
        classified.update(
            dict(
                zip(
                    by_survey["asec"].index,
                    _asec_rows(by_survey["asec"], asec_person),
                    strict=True,
                )
            )
        )
    if len(by_survey["acs"]):
        classified.update(
            dict(
                zip(
                    by_survey["acs"].index,
                    _acs_rows(by_survey["acs"], acs_person),
                    strict=True,
                )
            )
        )
    require(set(classified) == set(selected.index), "CLASSIFIED_ROSTER")
    rows = [classified[person_id] for person_id in selected.index]
    require(
        all(
            row[SURVEY_COLUMN] == survey
            for row, survey in zip(rows, selected.survey, strict=True)
        ),
        "CLASSIFIED_SURVEY",
    )
    return _observation_table(rows, selected.index)


@dataclass(frozen=True)
class QualifiedCurrentSurveySex:
    """Detached values; retained bytes grant no downstream admission."""

    source_frame: object
    rows: pd.DataFrame
    projection: bytes
    receipt: bytes


def sex_projection_seal(value):
    """Seal the actual returned values across a host's last source borrow."""
    require(type(value) is QualifiedCurrentSurveySex, "QUALIFIED_TYPE")
    require(type(value.projection) is bytes and type(value.receipt) is bytes, "SEALED")
    document = json.loads(value.receipt)
    require(
        value.projection == _projection_bytes(value.rows)
        and document["projection_sha256"] == _sha(value.projection)
        and document["protocol"] == PROTOCOL,
        "PROJECTION_BINDING",
    )
    return (
        source._frame_identity(value.source_frame),
        _table_stamp(value.rows),
        value.projection,
        value.receipt,
    )


def _receipt(table, *, preparation_sha256, acs_native_sha256, asec_receipt_sha256):
    counts = _counts(table)
    return source._encode(
        {
            "protocol": PROTOCOL,
            "preparation_sha256": preparation_sha256,
            "acs_native_sha256": acs_native_sha256,
            "asec_demographic_sha256": asec_receipt_sha256,
            "contract_sha256": contract_sha256(),
            "contract": sex_contract_document(),
            "projection_sha256": _sha(_projection_bytes(table)),
            "columns": list(COLUMNS),
            **counts,
            "source_admission_issued": False,
            "population_admission_issued": False,
            "release_eligible": False,
        },
        maximum=MAX_RECEIPT_BYTES,
    )


def _counts(table):
    """Aggregate counts only; no identity, code or row belongs in a receipt."""
    survey = table[SURVEY_COLUMN].astype(object)
    return {
        "original_persons": int(len(table)),
        "acs_originals": int(survey.eq("acs").sum()),
        "asec_originals": int(survey.eq("asec").sum()),
        "code_known_originals": int(table[CODE_KNOWN_COLUMN].sum()),
        "value_known_originals": int(table[VALUE_KNOWN_COLUMN].sum()),
        "allocation_known_originals": int(table[ALLOCATION_KNOWN_COLUMN].sum()),
        "asec_census_allocated_originals": int(
            (survey.eq("asec") & table[ALLOCATION_STATE_COLUMN].eq(2)).sum()
        ),
    }


def qualify_current_survey_sex(preparation):
    """Qualify canonical sex for every selected original person of both arms.

    This re-runs the maintained ASEC demographic owner and reauthenticates the
    issued ACS coverage Frame. It reads no member bytes itself; the ASEC owner
    does, under its own pins. Unknown ASEC codes stay unresolved, and ACS keeps
    its already-qualified value with unresolved allocation provenance.
    """
    require(
        type(preparation) is source.AuthenticatedSurveyPopulationPreparation,
        "PREPARATION_TYPE",
    )
    entry = preparation._checked()
    state = entry[2]
    acs_native, acs_frame = state.native[0], state.source_frames[0]
    source.acs_native.verify_acs_native_coverage(acs_native, acs_frame)
    acs_owned = source.acs_native._owned(acs_native)
    acs_payload = acs_owned.payload
    require(json.loads(acs_payload)["vintage"] == ACS_OBSERVATION_YEAR, "ACS_PERIOD")
    asec = demographics.qualify_current_asec_demographics(preparation)
    asec_receipt = asec.receipt
    asec_document = _check_asec_projection(asec, asec_receipt)
    require(
        asec_document["sex_observation_year"] == ASEC_OBSERVATION_YEAR
        and asec_document["income_year"] == INCOME_YEAR
        and asec_document["preparation_sha256"] == _sha(entry[1]),
        "ASEC_PERIOD",
    )
    acs_person = acs_frame.person.set_index("person_id", drop=False)
    table = _project(state.frame.person, acs_person, asec.person)
    receipt = _receipt(
        table,
        preparation_sha256=_sha(entry[1]),
        acs_native_sha256=_sha(acs_payload),
        asec_receipt_sha256=_sha(asec_receipt),
    )
    result = QualifiedCurrentSurveySex(
        state.frame, table, _projection_bytes(table), receipt
    )
    # Finish every owner borrow before the pure comparisons below, so a
    # callback during the last source check cannot change a retained input or
    # a detached output unnoticed.
    source.acs_native.verify_acs_native_coverage(acs_native, acs_frame)
    final_entry = preparation._checked()
    require(
        final_entry is entry
        and source._ISSUED.get(id(preparation)) is entry
        and preparation.payload == entry[1]
        and source.acs_native._ISSUED.get(acs_native) is acs_owned
        and acs_native.payload == acs_payload
        and acs_owned.frame is acs_frame
        and asec.receipt == asec_receipt,
        "FINAL_ISSUANCE",
    )
    source._pure_final(state)
    _check_asec_projection(asec, asec_receipt)
    require(
        _table_stamp(_project(state.frame.person, acs_person, asec.person))
        == _table_stamp(table)
        and result.receipt == receipt
        and sex_projection_seal(result)[1] == _table_stamp(table),
        "FINAL_PROJECTION",
    )
    return result


def _person_table(receiving):
    people = getattr(receiving, "person", None)
    require(type(people) is pd.DataFrame, "RECEIVING_PERSON_TABLE")
    return people


def canonical_dtype_token(receiving):
    """The token the canonical leaf must be declared with on this population.

    An absent leaf is created as a nullable Boolean. An incumbent keeps its own
    declared storage, because a rewrite must match the incumbent exactly.
    """
    people = _person_table(receiving)
    if CANONICAL_COLUMN not in people:
        return "boolean"
    try:
        token = token_for_dtype(people[CANONICAL_COLUMN].dtype)
    except (PopulationError, TypeError):
        raise ValueError("CURRENT_SURVEY_SEX_INCUMBENT_DTYPE_NOT_DECLARABLE") from None
    require(token in ("bool", "boolean"), "INCUMBENT_DTYPE")
    return token


def _incumbent(people, count):
    """Normalize the incumbent leaf to an explicit known mask and bool values."""
    if CANONICAL_COLUMN not in people:
        return np.zeros(count, dtype=bool), np.zeros(count, dtype=bool)
    values = pd.array(people[CANONICAL_COLUMN], dtype=dtype_for_token("boolean"))
    known = ~np.asarray(pd.isna(values), dtype=bool)
    resolved = np.zeros(count, dtype=bool)
    resolved[known] = np.asarray(values[known], dtype=bool)
    return known, resolved


def _bind(qualified, receiving):
    """Fan each qualified original onto exactly its two unchanged clones.

    Integers never travel through a float. An existing known cell is preserved
    and verified against its qualified source-bound observation; only a null
    cell whose binding is known is filled; a conflict or a known incumbent
    without a current qualified binding refuses for explicit adjudication.
    """
    require(type(qualified) is QualifiedCurrentSurveySex, "QUALIFIED_TYPE")
    rows = qualified.rows
    require(
        tuple(rows.columns) == COLUMNS
        and rows.index.name == "person_id"
        and str(rows.index.dtype) == "int64"
        and rows.index.is_unique,
        "QUALIFIED_AXIS",
    )
    people = _person_table(receiving)
    require("person_id" in people, "RECEIVING_PERSON_AXIS")
    ids = people.person_id
    original = people[support_source_id_column("person")]
    clone = people[support_clone_index_column("person")]
    native = people[spine_source_id_column("person")]
    channel = people[support_channel_column("person")].astype(object)
    require(str(ids.dtype) == "int64" and ids.is_unique, "RECEIVING_ID_AXIS")
    require(
        str(original.dtype) == str(clone.dtype) == str(native.dtype) == "int64",
        "CLONE_AXIS_DTYPE",
    )
    token = canonical_dtype_token(receiving)
    original = original.to_numpy(dtype=np.int64)
    require(
        len(original) == 2 * len(rows) and set(original) == set(rows.index),
        "CLONE_SOURCE_ROSTER",
    )
    expected = rows.reindex(original)
    require(
        np.array_equal(
            native.to_numpy(dtype=np.int64),
            expected[NATIVE_ID_COLUMN].to_numpy(dtype=np.int64),
        )
        and list(channel) == list(expected[SURVEY_COLUMN].astype(object)),
        "CLONE_SOURCE_IDENTITY",
    )
    clone = clone.to_numpy(dtype=np.int64)
    pairs = pd.MultiIndex.from_arrays((original, clone))
    require(pairs.is_unique and bool(np.isin(clone, (0, 1)).all()), "CLONE_PAIR")
    count = len(people)
    qualified_known = expected[VALUE_KNOWN_COLUMN].to_numpy(dtype=bool)
    qualified_value = np.zeros(count, dtype=bool)
    values = expected[VALUE_COLUMN]
    present = ~np.asarray(pd.isna(values), dtype=bool)
    require(bool(np.array_equal(present, qualified_known)), "QUALIFIED_KNOWNNESS")
    qualified_value[present] = np.asarray(values[present], dtype=bool)
    incumbent_known, incumbent_value = _incumbent(people, count)
    asec = np.asarray([value == "asec" for value in channel], dtype=bool)
    unbound = incumbent_known & ~qualified_known
    require(not bool((unbound & asec).any()), "KNOWN_ASEC_INCUMBENT_UNBOUND")
    require(not bool(unbound.any()), "KNOWN_INCUMBENT_WITHOUT_QUALIFIED_BINDING")
    require(
        not bool(
            (
                incumbent_known & qualified_known & (incumbent_value != qualified_value)
            ).any()
        ),
        "CANONICAL_CONFLICT",
    )
    resolved = incumbent_known | qualified_known
    bound = np.where(incumbent_known, incumbent_value, qualified_value)
    require(token == "boolean" or bool(resolved.all()), "UNRESOLVED_UNDER_BOOL_LEAF")
    if token == "boolean":
        column = pd.array(bound, dtype=dtype_for_token("boolean"))
        column[~resolved] = pd.NA
    else:
        column = bound
    series = pd.Series(
        column,
        index=pd.Index(ids.to_numpy(dtype=np.int64), name="person_id"),
        name=CANONICAL_COLUMN,
    )
    summary = {
        "canonical_dtype": token,
        "receiving_rows": int(count),
        "clone_indices": sorted(int(value) for value in set(clone)),
        "preserved_cells": int(incumbent_known.sum()),
        "filled_cells": int((~incumbent_known & qualified_known).sum()),
        "unresolved_cells": int((~resolved).sum()),
    }
    return series, summary


def sex_columns_for_population(value, receiving_frame):
    """Return the one canonical leaf this fragment writes on a receiving frame."""
    series, _summary = _bind(value, receiving_frame)
    return {("person", CANONICAL_COLUMN): series}


def sex_binding_receipt(value, receiving_frame, *, receiving_version, declared_rewrite):
    """Closed public aggregate metadata; no row, identity or code may appear."""
    require(
        type(receiving_version) is str
        and 0 < len(receiving_version) <= 256
        and type(declared_rewrite) is bool,
        "RECEIPT_INPUT",
    )
    _series, summary = _bind(value, receiving_frame)
    document = json.loads(value.receipt)
    receipt = {
        "protocol": PROTOCOL,
        "canonical_column": CANONICAL_COLUMN,
        "declared_rewrite": declared_rewrite,
        "contract_sha256": document["contract_sha256"],
        "projection_sha256": document["projection_sha256"],
        "receiving_version": receiving_version,
        "acs_allocation_provenance": "unresolved",
        "equivalent_allocation_evidence_claim": False,
        "unallocated_observation_claim": False,
        "source_admission_issued": False,
        "population_admission_issued": False,
        "release_eligible": False,
        **summary,
        **{
            key: document[key]
            for key in (
                "original_persons",
                "acs_originals",
                "asec_originals",
                "code_known_originals",
                "value_known_originals",
                "allocation_known_originals",
                "asec_census_allocated_originals",
            )
        },
    }
    require(set(receipt) == PUBLIC_RECEIPT_KEYS, "PUBLIC_RECEIPT_ROSTER")
    require(
        all(
            type(v) is bool
            or type(v) is int
            or type(v) is str
            or (type(v) is list and all(type(i) is int for i in v))
            for v in receipt.values()
        ),
        "PUBLIC_RECEIPT_AGGREGATES",
    )
    return receipt
