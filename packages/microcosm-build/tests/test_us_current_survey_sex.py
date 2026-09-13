"""Invented sex observations against the actual shared code tables and binder.

Every source code, state and label below is read from the maintained ASEC
demographic owner or from the current ACS source modules. The digests and
person identifiers are invented fixture values and claim no source authority,
no issued Frame and no data admission. No member bytes are read here.
"""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from microcosm.build.us_runtime import current_survey_sex as sex
from microcosm.build.us_runtime import graph_current_survey_sex as graph
from microcosm.frame import US_SCHEMA, Frame, WeightKind, Weights
from microcosm.graph import ArtifactInput, ArtifactType

# person_id, native_person_id, survey, sex code, allocation code
DEFAULT = (
    (10, 2, "asec", 2, 4),  # Census-allocated female.
    (20, 3, "acs", 1, None),  # ACS male; allocation provenance unresolved.
    (30, 5, "asec", 9, 0),  # Unprinted sex code; allocation still "no change".
)
INVENTED_DIGESTS = {
    "preparation_sha256": "0" * 64,
    "acs_native_sha256": "1" * 64,
    "asec_receipt_sha256": "2" * 64,
}


def _observation(survey, code, allocation_code, *, native):
    row = (
        sex.asec_sex_observation(code, allocation_code)
        if survey == "asec"
        else sex.acs_sex_observation(code)
    )
    return {**row, sex.NATIVE_ID_COLUMN: native}


def _table(specs=DEFAULT):
    rows = [_observation(s[2], s[3], s[4], native=s[1]) for s in specs]
    index = pd.Index([s[0] for s in specs], name="person_id", dtype="int64")
    return sex._observation_table(rows, index)


def _frame(people):
    people = people.copy(deep=True)
    tables = {"person": people}
    for entity in US_SCHEMA.group_entities:
        people[US_SCHEMA.membership_column(entity)] = people.person_id.to_numpy()
        tables[entity] = pd.DataFrame(
            {US_SCHEMA.entity_id_column(entity): np.sort(people.person_id.to_numpy())}
        )
    return Frame(
        tables,
        US_SCHEMA,
        {"household": Weights(np.ones(len(people)), WeightKind.DESIGN)},
    )


def _qualified(table=None):
    table = _table() if table is None else table
    frame = _frame(pd.DataFrame({"person_id": table.index.to_numpy()}))
    value = sex.QualifiedCurrentSurveySex(
        frame,
        table,
        sex._projection_bytes(table),
        sex._receipt(table, **INVENTED_DIGESTS),
    )
    sex.sex_projection_seal(value)
    return value


def _pairs(table):
    # Reversed, so a binder that trusted row order instead of exact identity
    # would not pass.
    return [(int(original), clone) for original in table.index for clone in (0, 1)][
        ::-1
    ]


def _receiving(table, *, incumbent=None, base=0, dtype="boolean"):
    pairs = _pairs(table)
    people = pd.DataFrame(
        {
            "person_id": np.array(
                [base + position + 1 for position in range(len(pairs))], dtype="int64"
            ),
            sex.support_source_id_column("person"): np.array(
                [original for original, _clone in pairs], dtype="int64"
            ),
            sex.support_clone_index_column("person"): np.array(
                [clone for _original, clone in pairs], dtype="int64"
            ),
            sex.spine_source_id_column("person"): np.array(
                [int(table.at[o, sex.NATIVE_ID_COLUMN]) for o, _clone in pairs],
                dtype="int64",
            ),
            sex.support_channel_column("person"): pd.array(
                [str(table.at[o, sex.SURVEY_COLUMN]) for o, _clone in pairs],
                dtype="string",
            ),
            "unrelated_amount": np.arange(len(pairs), dtype="float64"),
        }
    )
    if incumbent is not None:
        values = [incumbent.get(original, pd.NA) for original, _clone in pairs]
        people[sex.CANONICAL_COLUMN] = (
            pd.array(values, dtype=dtype)
            if dtype != "bool"
            else np.array(values, dtype=bool)
        )
    return SimpleNamespace(person=people)


@pytest.mark.parametrize(
    "a_sex,axsex,female,binding,allocation,origin",
    [
        (1, 0, False, 1, 1, "source_no_change"),
        (1, 4, False, 1, 2, "census_allocated"),
        (2, 0, True, 2, 1, "source_no_change"),
        (2, 4, True, 2, 2, "census_allocated"),
    ],
)
def test_asec_named_codes_bind_and_keep_allocation_separate(
    a_sex, axsex, female, binding, allocation, origin
):
    row = sex.asec_sex_observation(a_sex, axsex)
    assert row[sex.VALUE_COLUMN] is female
    assert row[sex.BINDING_STATE_COLUMN] == binding
    assert row[sex.ALLOCATION_STATE_COLUMN] == allocation
    assert row[sex.UNBOUND_REASON_COLUMN] == 0
    assert row[sex.ORIGIN_COLUMN] == origin
    assert row[sex.CODE_KNOWN_COLUMN]
    assert row[sex.VALUE_KNOWN_COLUMN]
    assert row[sex.ALLOCATION_KNOWN_COLUMN]
    assert row[sex.CODE_COLUMN] == a_sex and row[sex.ALLOCATION_CODE_COLUMN] == axsex


@pytest.mark.parametrize("a_sex", [0, 9])
def test_unprinted_asec_sex_code_never_becomes_male(a_sex):
    """An unbound sex code still carries its own printed allocation flag."""
    row = sex.asec_sex_observation(a_sex, 0)
    assert row[sex.VALUE_COLUMN] is None
    assert row[sex.BINDING_STATE_COLUMN] == 0
    assert row[sex.UNBOUND_REASON_COLUMN] == 1
    assert not row[sex.CODE_KNOWN_COLUMN] and not row[sex.VALUE_KNOWN_COLUMN]
    assert row[sex.ALLOCATION_STATE_COLUMN] == 1
    assert row[sex.ALLOCATION_KNOWN_COLUMN]
    assert row[sex.ORIGIN_COLUMN] == "source_no_change"


@pytest.mark.parametrize("axsex", [1, 2, 3])
def test_unnamed_in_range_allocation_flag_leaves_sex_unbound(axsex):
    """Inside the printed 0:4 range is not the same as a printed code."""
    assert axsex in sex.demographic.AXSEX.unnamed_in_range_codes
    row = sex.asec_sex_observation(2, axsex)
    assert row[sex.VALUE_COLUMN] is None
    assert row[sex.BINDING_STATE_COLUMN] == 0
    assert row[sex.UNBOUND_REASON_COLUMN] == 2
    assert row[sex.CODE_KNOWN_COLUMN]
    assert not row[sex.VALUE_KNOWN_COLUMN]
    assert not row[sex.ALLOCATION_KNOWN_COLUMN]
    assert row[sex.ALLOCATION_STATE_COLUMN] == 0
    assert row[sex.ORIGIN_COLUMN] == "unresolved_allocation"


@pytest.mark.parametrize("code,female", [(1, False), (2, True)])
def test_acs_value_is_preserved_with_unresolved_allocation(code, female):
    row = sex.acs_sex_observation(code)
    assert row[sex.VALUE_COLUMN] is female
    assert row[sex.CODE_KNOWN_COLUMN] and row[sex.VALUE_KNOWN_COLUMN]
    assert not row[sex.ALLOCATION_KNOWN_COLUMN]
    assert row[sex.ALLOCATION_STATE_COLUMN] == 0
    assert row[sex.ALLOCATION_CODE_COLUMN] is None
    assert row[sex.ORIGIN_COLUMN] == sex.ACS_ORIGIN
    assert row[sex.UNBOUND_REASON_COLUMN] == 0


def test_allocation_knownness_separates_the_two_surveys():
    """Both arms can bind the same value while only one observes allocation."""
    asec = sex.asec_sex_observation(2, 4)
    acs = sex.acs_sex_observation(2)
    assert asec[sex.VALUE_COLUMN] is acs[sex.VALUE_COLUMN] is True
    assert asec[sex.ALLOCATION_KNOWN_COLUMN] and not acs[sex.ALLOCATION_KNOWN_COLUMN]
    assert (
        sex.demographic.SEX_ALLOCATION_STATES[asec[sex.ALLOCATION_STATE_COLUMN]]
        == "census_allocated"
    )
    assert (
        sex.demographic.SEX_ALLOCATION_STATES[acs[sex.ALLOCATION_STATE_COLUMN]]
        == "undetermined"
    )
    assert "unallocated" not in acs[sex.ORIGIN_COLUMN]


def test_contract_records_no_acs_allocation_flag_and_no_equivalence_claim():
    document = sex.sex_contract_document()
    assert document["equivalent_allocation_evidence_claim"] is False
    acs = document["acs"]
    assert acs["allocation_field_in_declared_readset"] is None
    assert acs["allocation_flag_searched"] == "FSEXP"
    assert acs["allocation_provenance"] == "unresolved"
    assert acs["allocation_knownness"] is False
    assert acs["absent_allocation_flag_is_a_code"] is False
    assert acs["unallocated_observation_claim"] is False
    assert acs["printed_dictionary_page_read_by_this_lane"] is False
    assert acs["universe_is_printed_dictionary_quote"] is False
    assert document["asec"]["composed_stage_unbound_guard_changed"] is False
    assert document["asec"]["binding_requires"] == [
        "A_SEX in printed codes",
        "AXSEX in printed codes",
    ]
    assert document["source_admission_issued"] is False
    assert document["release_eligible"] is False
    assert sex.contract_sha256() == sex.contract_sha256()


@pytest.mark.parametrize(
    "name,value",
    [
        ("SEX_BINDING_STATES", {0: "unbound", 1: "male", 2: "female"}),
        ("SEX_ALLOCATION_STATES", {0: "undetermined", 1: "no_change"}),
    ],
)
def test_shared_code_tables_are_pinned_to_the_maintained_owner(
    monkeypatch, name, value
):
    monkeypatch.setattr(sex.demographic, name, value)
    with pytest.raises(ValueError, match="SHARED_CODE_TABLES_CHANGED"):
        sex.asec_sex_observation(1, 0)


@pytest.mark.parametrize("value", [True, 1.0, "1", None])
def test_source_codes_must_be_plain_integers(value):
    with pytest.raises(ValueError, match="CODE_TYPE"):
        sex.asec_sex_observation(value, 0)
    with pytest.raises(ValueError, match="CODE_TYPE"):
        sex.acs_sex_observation(value)


def test_binding_fans_each_original_onto_both_clones_and_preserves_unknowns():
    qualified = _qualified()
    receiving = _receiving(qualified.rows)
    before = receiving.person.copy(deep=True)
    columns = sex.sex_columns_for_population(qualified, receiving)
    series = columns[("person", sex.CANONICAL_COLUMN)]
    assert str(series.dtype) == "boolean"
    assert series.index.tolist() == receiving.person.person_id.tolist()
    original = receiving.person[sex.support_source_id_column("person")].to_numpy()
    # Census-allocated female is still a value; an unbound code stays
    # unresolved and never becomes male. Both clones carry the same cell.
    assert series[original == 10].tolist() == [True, True]
    assert series[original == 20].tolist() == [False, False]
    assert series[original == 30].isna().tolist() == [True, True]
    pd.testing.assert_frame_equal(receiving.person, before, check_exact=True)


def test_binding_preserves_matching_incumbents_and_fills_only_known_nulls():
    qualified = _qualified()
    receiving = _receiving(qualified.rows, incumbent={20: False})
    series = sex.sex_columns_for_population(qualified, receiving)[
        ("person", sex.CANONICAL_COLUMN)
    ]
    receipt = sex.sex_binding_receipt(
        qualified, receiving, receiving_version="receiving", declared_rewrite=True
    )
    assert receipt["preserved_cells"] == 2
    assert receipt["filled_cells"] == 2
    assert receipt["unresolved_cells"] == 2
    assert receipt["declared_rewrite"] is True
    assert series.isna().sum() == 2
    assert receipt["value_known_originals"] == 2
    assert receipt["allocation_known_originals"] == 2
    assert receipt["asec_census_allocated_originals"] == 1
    assert receipt["acs_originals"] == 1 and receipt["asec_originals"] == 2


def test_binding_refuses_a_conflicting_known_incumbent():
    qualified = _qualified()
    receiving = _receiving(qualified.rows, incumbent={20: True})
    with pytest.raises(ValueError, match="CANONICAL_CONFLICT"):
        sex.sex_columns_for_population(qualified, receiving)


def test_binding_refuses_a_known_asec_incumbent_without_qualified_binding():
    qualified = _qualified()
    receiving = _receiving(qualified.rows, incumbent={30: False})
    with pytest.raises(ValueError, match="KNOWN_ASEC_INCUMBENT_UNBOUND"):
        sex.sex_columns_for_population(qualified, receiving)


def test_binding_refuses_any_known_incumbent_without_qualified_binding():
    """The seam fails closed even on a code the real ACS reader refuses upstream."""
    table = _table(((10, 2, "asec", 2, 4), (20, 3, "acs", 3, None)))
    qualified = _qualified(table)
    receiving = _receiving(table, incumbent={20: True})
    with pytest.raises(ValueError, match="KNOWN_INCUMBENT_WITHOUT_QUALIFIED_BINDING"):
        sex.sex_columns_for_population(qualified, receiving)


def test_binding_maps_clone_ids_above_exact_float_range():
    """Identities beyond 2**53 must never travel through a float."""
    high = 2**53
    table = _table(
        ((high + 11, high + 101, "asec", 1, 0), (high + 29, high + 307, "acs", 2, None))
    )
    qualified = _qualified(table)
    receiving = _receiving(table, base=high + 1000)
    series = sex.sex_columns_for_population(qualified, receiving)[
        ("person", sex.CANONICAL_COLUMN)
    ]
    assert str(series.index.dtype) == "int64"
    assert series.index.min() > high
    original = receiving.person[sex.support_source_id_column("person")].to_numpy()
    assert series[original == high + 11].tolist() == [False, False]
    assert series[original == high + 29].tolist() == [True, True]


@pytest.mark.parametrize(
    "defect,reason",
    [
        ("duplicate_receiving_id", "RECEIVING_ID_AXIS"),
        ("foreign_origin", "CLONE_SOURCE_ROSTER"),
        ("missing_origin", "CLONE_SOURCE_ROSTER"),
        ("duplicate_clone", "CLONE_PAIR"),
        ("wrong_native", "CLONE_SOURCE_IDENTITY"),
        ("wrong_channel", "CLONE_SOURCE_IDENTITY"),
    ],
)
def test_binding_refuses_invalid_origin_or_clone_axes(defect, reason):
    qualified = _qualified()
    receiving = _receiving(qualified.rows)
    people = receiving.person
    if defect == "duplicate_receiving_id":
        people.loc[0, "person_id"] = int(people.person_id.iloc[1])
    elif defect == "foreign_origin":
        people.loc[0, sex.support_source_id_column("person")] = 99
    elif defect == "missing_origin":
        receiving.person = people.iloc[:-1].reset_index(drop=True)
    elif defect == "duplicate_clone":
        people.loc[0, sex.support_clone_index_column("person")] = int(
            people[sex.support_clone_index_column("person")].iloc[1]
        )
    elif defect == "wrong_native":
        people.loc[0, sex.spine_source_id_column("person")] = 99
    else:
        channel = sex.support_channel_column("person")
        people.loc[0, channel] = "acs" if people[channel].iloc[0] == "asec" else "asec"
    with pytest.raises(ValueError, match=reason):
        sex.sex_columns_for_population(qualified, receiving)


def test_public_receipt_is_closed_aggregate_metadata():
    qualified = _qualified()
    receipt = sex.sex_binding_receipt(
        qualified,
        _receiving(qualified.rows),
        receiving_version="receiving",
        declared_rewrite=False,
    )
    assert set(receipt) == sex.PUBLIC_RECEIPT_KEYS
    assert not set(receipt) & set(sex.COLUMNS)
    text = json.dumps(receipt, sort_keys=True)
    for identity in ("person_id", "native", "A_SEX", "AXSEX", "SEX"):
        assert identity not in text
    assert receipt["acs_allocation_provenance"] == "unresolved"
    assert receipt["equivalent_allocation_evidence_claim"] is False
    assert receipt["unallocated_observation_claim"] is False
    assert receipt["source_admission_issued"] is False
    assert receipt["population_admission_issued"] is False
    assert receipt["release_eligible"] is False
    assert receipt["clone_indices"] == [0, 1]


def test_a_fully_bound_nonnullable_incumbent_keeps_its_own_storage():
    table = _table(((10, 2, "asec", 2, 4), (20, 3, "acs", 1, None)))
    qualified = _qualified(table)
    receiving = _receiving(table, incumbent={10: True, 20: False}, dtype="bool")
    assert sex.canonical_dtype_token(receiving) == "bool"
    series = sex.sex_columns_for_population(qualified, receiving)[
        ("person", sex.CANONICAL_COLUMN)
    ]
    assert str(series.dtype) == "bool"
    assert series.notna().all()


def test_incumbent_dtype_outside_the_graph_vocabulary_refuses():
    """A declarable storage is a precondition, not something to coerce around."""
    qualified = _qualified()
    receiving = _receiving(qualified.rows)
    receiving.person[sex.CANONICAL_COLUMN] = np.array(
        [True, None, False, None, True, None], dtype=object
    )
    with pytest.raises(ValueError, match="INCUMBENT_DTYPE_NOT_DECLARABLE"):
        sex.canonical_dtype_token(receiving)
    with pytest.raises(ValueError, match="INCUMBENT_DTYPE_NOT_DECLARABLE"):
        sex.sex_columns_for_population(qualified, receiving)


def _after():
    return ArtifactInput(
        "ordering", "country.amounts", "attachment", ArtifactType("invented", 1)
    )


def test_declaration_creates_an_absent_leaf_and_rewrites_an_incumbent():
    qualified = _qualified()
    for incumbent, rewrite, dtype in (
        (None, False, "boolean"),
        ({20: False}, True, "boolean"),
    ):
        receiving = _receiving(qualified.rows, incumbent=incumbent)
        projection, bind = graph.current_survey_sex_nodes(
            qualified,
            receiving,
            receiving_version="country.receiving",
            host_pins={},
            after=_after(),
            host_edges=(),
        )
        assert projection.id == graph.SOURCE_NODE and bind.id == graph.BIND_NODE
        assert projection.structural.value == "create"
        assert bind.structural.value == "none"
        assert bind.population == "country.receiving"
        assert bind.outputs == (
            graph.Owned("person", sex.CANONICAL_COLUMN, dtype, rewrite=rewrite),
        )
        assert bind.params["declared_rewrite"] is rewrite
        assert bind.params["canonical_dtype"] == dtype
        assert _after() in bind.artifact_inputs
        assert graph._projection_edge() in bind.artifact_inputs
        assert tuple(c for s in bind.inputs for c in s.columns) == (
            graph._identity_columns()
        )
        assert tuple(o.column for o in projection.outputs) == sex.COLUMNS


def test_declaration_requires_matching_host_edges_and_pins():
    qualified = _qualified()
    receiving = _receiving(qualified.rows)
    edges = (ArtifactInput("preparation", "p", "preparation", ArtifactType("t", 1)),)
    with pytest.raises(ValueError, match="HOST_PINS"):
        graph.current_survey_sex_nodes(
            qualified,
            receiving,
            receiving_version="country.receiving",
            host_pins={},
            after=_after(),
            host_edges=edges,
        )
    with pytest.raises(ValueError, match="HOST_PIN_DIGESTS"):
        graph.current_survey_sex_nodes(
            qualified,
            receiving,
            receiving_version="country.receiving",
            host_pins={"preparation": {"producer_key": "x"}},
            after=_after(),
            host_edges=edges,
        )


def test_public_values_do_not_authorize_a_source_projection():
    with pytest.raises(ValueError, match="PREPARATION_TYPE"):
        sex.qualify_current_survey_sex(SimpleNamespace(payload=b"{}"))


def test_projection_seal_binds_the_returned_rows():
    qualified = _qualified()
    seal = sex.sex_projection_seal(qualified)
    assert sex.sex_projection_seal(_qualified()) == seal
    qualified.rows.loc[10, sex.CODE_COLUMN] = 1
    with pytest.raises(ValueError, match="PROJECTION_BINDING"):
        sex.sex_projection_seal(qualified)
