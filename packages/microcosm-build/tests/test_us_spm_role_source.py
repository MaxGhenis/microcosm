"""Pinned source roles must explain complete, unchanged native SPM units."""

import hashlib
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from microcosm.build.us_runtime.spm_role_source import (
    ASEC_SPM_ROLE_SOURCES,
    EVIDENCE_SPM_ROLE,
    AsecSpmRoleSource,
    derive_spm_role_source,
    independent_minor_role,
)

pytest.importorskip("tables")


def test_release_contract_pins_match_actual_source_acquisition():
    from microcosm.build.us_runtime.education_assistance_source import (
        ASEC_EDUCATION_ASSISTANCE_ARCHIVES,
    )
    from microcosm.data.source_enrichment import CENSUS_ARCHIVE_PINS, CENSUS_PERSON_PINS

    assert (
        set(CENSUS_ARCHIVE_PINS)
        == set(CENSUS_PERSON_PINS)
        == {pin.survey_year for pin in ASEC_EDUCATION_ASSISTANCE_ARCHIVES.values()}
    )
    for income_year, pin in ASEC_EDUCATION_ASSISTANCE_ARCHIVES.items():
        assert CENSUS_PERSON_PINS[pin.survey_year] == pin.member_sha256
        assert CENSUS_ARCHIVE_PINS[pin.survey_year] == {
            "income_year": income_year,
            "official_archive_url": pin.zip_url,
            "archive_sha256": pin.zip_sha256,
            "member": pin.member,
        }
        role = ASEC_SPM_ROLE_SOURCES[income_year]
        assert role.survey_year == pin.survey_year
        assert role.csv_sha256 == pin.member_sha256
        assert role.income_year == income_year
        assert role.official_archive_url == pin.zip_url
        assert role.archive_sha256 == pin.zip_sha256
        assert role.member == pin.member


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def population(tmp_path):
    # A minor spouse is independent, while a same-age dependent child is not.
    # Unit 100 is cloned into native units 10 and 40 with the same source IDs.
    source = pd.DataFrame(
        {
            "PERIDNUM": [f"{number:022}" for number in range(1, 7)],
            "SPM_ID": [100, 100, 100, 200, 200, 300],
            "PH_SEQ": [1, 1, 1, 2, 2, 3],
            "P_SEQ": [1, 2, 3, 1, 2, 1],
            "A_LINENO": [1, 2, 3, 1, 2, 1],
            "A_AGE": [17, 16, 10, 40, 16, 15],
            "SPM_HAGE": [17, 17, 17, 40, 40, 15],
            "SPM_HEAD": [1, 0, 0, 1, 0, 1],
            "SPM_NUMADULTS": [2, 2, 2, 1, 1, 1],
            "SPM_NUMKIDS": [1, 1, 1, 1, 1, 0],
            "SPM_NUMPER": [3, 3, 3, 2, 2, 1],
            "A_FAMTYP": [1, 1, 1, 1, 1, 4],
            "A_FAMREL": [1, 2, 3, 1, 3, 1],
            "A_SPOUSE": [2, 1, 0, 0, 0, 0],
            "PECOHAB": [0, 0, 0, 0, 0, 0],
        }
    )
    source_path = tmp_path / "pppub25.csv"
    source.to_csv(source_path, index=False)
    parent = pd.concat([source, source.iloc[:3]], ignore_index=True)
    parent["source_row_id"] = [0, 1, 2, 3, 4, 5, 0, 1, 2]
    parent["source_year"] = 2024
    parent["source_person_id"] = parent.PERIDNUM
    parent["source_household_id"] = parent.PH_SEQ
    parent["person_id"] = np.arange(1001, 1010)
    parent["person_spm_unit_id"] = [10, 10, 10, 20, 20, 30, 40, 40, 40]
    parent["age"] = parent.A_AGE.astype(float)
    # The pooled producer globalizes SPM_ID, so raw ID equality is incorrect.
    parent["SPM_ID"] = parent.SPM_ID.map({100: 1, 200: 2, 300: 3})
    # Frozen older source HDFs lack relationship columns; optional equality
    # checks must not fill those cells just because the CSV carries the data.
    parent = parent.drop(columns=["SPM_HEAD"])
    parent["A_FAMREL"] = parent.A_FAMREL.astype(float)
    parent.loc[:2, "A_FAMREL"] = np.nan
    parent_path = tmp_path / "parent.h5"
    parent.to_hdf(parent_path, key="person")
    pd.DataFrame({"spm_unit_id": [10, 20, 30, 40]}).to_hdf(parent_path, key="spm_unit")
    pin = AsecSpmRoleSource(
        income_year=2024,
        survey_year=2025,
        csv_sha256=_digest(source_path),
        csv_size_bytes=source_path.stat().st_size,
        persons=6,
        units=3,
        official_archive_url="https://example.invalid/fixture.zip",
        archive_sha256="a" * 64,
        member="pppub25.csv",
    )
    return parent_path, source_path, pin


def _derive(population):
    parent, source, pin = population
    return derive_spm_role_source(
        parent,
        {2024: source},
        expected_parent_sha256=_digest(parent),
        source_pins={2024: pin},
    )


def _change_parent(population, change):
    parent_path, _, _ = population
    parent = pd.read_hdf(parent_path, "person")
    change(parent)
    parent.to_hdf(parent_path, key="person")


def _change_source(population, change):
    parent_path, source_path, pin = population
    source = pd.read_csv(source_path, dtype={"PERIDNUM": str})
    change(source)
    source.to_csv(source_path, index=False)
    return (
        parent_path,
        source_path,
        replace(
            pin,
            csv_sha256=_digest(source_path),
            csv_size_bytes=source_path.stat().st_size,
        ),
    )


def test_role_is_primitive_before_age_gate():
    people = pd.DataFrame(
        {
            "A_AGE": [14, 16, 17, 40, 16, 16],
            "SPM_HEAD": [1, 0, 0, 1, 0, 0],
            "A_FAMTYP": [0, 1, 4, 1, 1, 2],
            "A_FAMREL": [0, 2, 1, 1, 3, 1],
        }
    )
    role = independent_minor_role(people)
    assert role.tolist() == [True, True, True, True, False, False]
    adult = people.A_AGE.ge(18) | (people.A_AGE.ge(15) & role)
    assert adult.tolist() == [False, True, True, True, False, False]


def test_derivation_joins_clones_without_changing_parent(population):
    parent, _, _ = population
    before = parent.read_bytes()
    result = _derive(population)
    assert parent.read_bytes() == before
    assert result.role.dtype == np.bool_
    assert result.role.tolist() == [
        True,
        True,
        False,
        True,
        False,
        True,
        True,
        True,
        False,
    ]
    assert list(result.evidence) == [
        "person_id",
        "person_spm_unit_id",
        EVIDENCE_SPM_ROLE,
    ]
    assert result.evidence.person_id.tolist() == list(range(1001, 1010))
    assert result.provenance["total_source_units"] == 3
    assert result.provenance["native_spm_units"] == 4
    assert result.provenance["complete_source_membership_units"] == 4
    assert result.provenance["minor_only_units_resolved"] == 3
    assert result.provenance["independent_minor_persons"] == 5
    assert result.provenance["adult_child_person_count_mismatch_units"] == 0
    assert (
        result.provenance["source_checks"][0][
            "extra_independent_minor_people_vs_head_only"
        ]
        == 1
    )
    assert result.provenance["nonmissing_optional_raw_fields_checked"]["A_FAMREL"] == 6


def test_rejects_wrong_parent_identity(population):
    parent, source, pin = population
    with pytest.raises(ValueError, match="Parent H5 SHA-256"):
        derive_spm_role_source(
            parent,
            {2024: source},
            expected_parent_sha256="0" * 64,
            source_pins={2024: pin},
        )


def test_rejects_unpinned_csv(population):
    parent, source, pin = population
    with pytest.raises(ValueError, match="CSV SHA-256"):
        _derive((parent, source, replace(pin, csv_sha256="0" * 64)))


def test_rejects_missing_source_year(population):
    parent, _, pin = population
    with pytest.raises(ValueError, match="must match exactly"):
        derive_spm_role_source(
            parent, {}, expected_parent_sha256=_digest(parent), source_pins={2024: pin}
        )


@pytest.mark.parametrize(
    "column", ["A_AGE", "P_SEQ", "SPM_NUMADULTS", "A_FAMTYP", "source_row_id"]
)
def test_rejects_parent_source_disagreement(population, column):
    _change_parent(
        population, lambda frame: frame.__setitem__(column, frame[column] + 1)
    )
    with pytest.raises(ValueError, match=f"{column} disagrees"):
        _derive(population)


def test_rejects_unmatched_parent_person(population):
    _change_parent(
        population, lambda frame: frame.loc.__setitem__((0, "PERIDNUM"), "9" * 22)
    )
    with pytest.raises(ValueError, match="unmatched parent persons"):
        _derive(population)


def test_rejects_lossy_person_id_coercion(population):
    _change_parent(
        population,
        lambda frame: frame.__setitem__("PERIDNUM", frame.PERIDNUM.astype(float)),
    )
    with pytest.raises(ValueError, match="exact 22-digit strings"):
        _derive(population)


def test_rejects_native_membership_mixing_even_when_counts_match(population):
    # Units 10 and 40 are source clones; switching their third members is valid,
    # but switching a source member between different source units is not.
    def exchange(frame):
        frame.loc[2, "person_spm_unit_id"] = 20
        frame.loc[4, "person_spm_unit_id"] = 10

    _change_parent(population, exchange)
    with pytest.raises(ValueError, match="combines distinct source units"):
        _derive(population)


def test_rejects_duplicate_source_member_inside_native_unit(population):
    def duplicate(frame):
        # Move a complete clone into its source unit, keeping native IDs present.
        frame.loc[6, "person_spm_unit_id"] = 10

    _change_parent(population, duplicate)
    with pytest.raises(ValueError, match="repeats a source person"):
        _derive(population)


def test_reconciles_full_source_not_just_selected_parent_units(population):
    parent, source, pin = population
    # Remove unit 300 from parent; its deliberately false raw count must still
    # fail full-source reconciliation even though the parent never joins it.
    person = pd.read_hdf(parent, "person").query("person_spm_unit_id != 30")
    person.to_hdf(parent, key="person")
    pd.DataFrame({"spm_unit_id": [10, 20, 40]}).to_hdf(parent, key="spm_unit")
    changed = _change_source(
        (parent, source, pin),
        lambda frame: frame.loc.__setitem__((5, "SPM_NUMADULTS"), 0),
    )
    with pytest.raises(ValueError, match="adult/child/person count reconciliation"):
        _derive(changed)


def test_rejects_duplicate_source_keys(population):
    changed = _change_source(
        population,
        lambda frame: frame.loc.__setitem__((1, "PERIDNUM"), frame.loc[0, "PERIDNUM"]),
    )
    with pytest.raises(ValueError, match="duplicate PERIDNUM"):
        _derive(changed)


def _source_frame(population, *, income_year=2024, shuffle=False):
    from microcosm.frame import EntitySchema, Frame, WeightKind, Weights

    parent_path, source_path, pin = population
    person = pd.read_hdf(parent_path, "person")
    person["source_year"] = income_year
    if shuffle:
        person = person.sample(frac=1, random_state=42).reset_index(drop=True)
    person["source_row_id"] = np.arange(len(person))
    person["person_household_id"] = person.person_spm_unit_id
    # The model age can be advanced independently of the fixed source role.
    person["age"] += 5
    spm = pd.read_hdf(parent_path, "spm_unit")
    return (
        Frame(
            {
                "person": person,
                "spm_unit": spm,
                "household": spm.rename(columns={"spm_unit_id": "household_id"}),
            },
            EntitySchema(group_entities=("household", "spm_unit")),
            {"household": Weights(np.ones(len(spm)), WeightKind.DESIGN)},
        ),
        source_path,
        replace(pin, income_year=income_year, survey_year=income_year + 1),
    )


@pytest.mark.parametrize("income_year", [2022, 2023, 2024])
@pytest.mark.parametrize("archive", [False, True])
def test_ordinary_frame_role_preserves_clones_keys_and_boolean_checkpoints(
    population, tmp_path, income_year, archive
):
    from zipfile import ZipFile

    from microcosm.build.frame_checkpoint import (
        load_frame_checkpoint,
        write_frame_checkpoint,
    )
    from microcosm.build.us_runtime.spm_role_source import (
        NATIVE_SPM_ROLE,
        with_us_spm_role_source,
    )

    frame, source, pin = _source_frame(
        population, income_year=income_year, shuffle=True
    )
    if archive:
        archive_path = tmp_path / "source.zip"
        with ZipFile(archive_path, "w") as output:
            output.write(source, arcname=pin.member)
        source = archive_path
        pin = replace(pin, archive_sha256=_digest(source))
    delivered, receipt = with_us_spm_role_source(
        frame, {income_year: source}, source_pins={income_year: pin}
    )
    expected = independent_minor_role(
        pd.read_csv(population[1], dtype={"PERIDNUM": str}).set_index("PERIDNUM")
    )
    assert delivered.table("person")[NATIVE_SPM_ROLE].dtype == np.bool_
    assert delivered.table("person")[NATIVE_SPM_ROLE].tolist() == (
        frame.table("person").PERIDNUM.map(expected).tolist()
    )
    pd.testing.assert_frame_equal(
        delivered.table("person").drop(columns=NATIVE_SPM_ROLE), frame.table("person")
    )
    assert receipt["source_checks"][0]["survey_year"] == income_year + 1
    assert receipt["complete_source_membership_units"] == 4
    assert receipt["total_source_units"] == 3
    checkpoint = write_frame_checkpoint(
        tmp_path / "role.frame.h5", delivered, metadata=receipt
    )
    reloaded = load_frame_checkpoint(checkpoint)
    checked, selected_receipt = with_us_spm_role_source(
        reloaded.frame.select(reloaded.frame.table("person").person_spm_unit_id.ne(20)),
        {income_year: source},
        source_pins={income_year: pin},
    )
    assert checked.table("person")[NATIVE_SPM_ROLE].dtype == np.bool_
    assert selected_receipt["complete_source_membership_units"] == 3
    assert selected_receipt["total_source_units"] == 3
    assert reloaded.metadata == receipt


def test_ordinary_frame_rejects_partial_units_and_altered_role(population):
    from microcosm.build.us_runtime.spm_role_source import (
        NATIVE_SPM_ROLE,
        with_us_spm_role_source,
    )

    frame, source, pin = _source_frame(population)
    args = ({2024: source},)
    with pytest.raises(ValueError, match="adult/child/person count"):
        with_us_spm_role_source(
            frame.select(frame.table("person").person_id.ne(1002)),
            *args,
            source_pins={2024: pin},
        )
    delivered, _ = with_us_spm_role_source(frame, *args, source_pins={2024: pin})
    delivered.table("person").loc[0, NATIVE_SPM_ROLE] = False
    with pytest.raises(ValueError, match="disagrees with source"):
        with_us_spm_role_source(delivered, *args, source_pins={2024: pin})
    delivered.table("person")[NATIVE_SPM_ROLE] = 1
    with pytest.raises(ValueError, match="must be boolean"):
        with_us_spm_role_source(delivered, *args, source_pins={2024: pin})


@pytest.mark.requires_us
def test_ordinary_role_survives_real_country_h5_export_and_reload(population, tmp_path):
    from policyengine_us.data import USSingleYearDataset

    from microcosm.build.us_runtime.spm_role_source import (
        NATIVE_SPM_ROLE,
        with_us_spm_role_source,
    )
    from microcosm.frame import US_SCHEMA, Frame
    from microcosm.frame.adapters.policyengine_us import PolicyEngineUSEngine

    partial_frame, source, pin = _source_frame(population)
    tables = {
        entity: partial_frame.table(entity).copy() for entity in partial_frame.entities
    }
    for group in ("tax_unit", "family", "marital_unit"):
        tables[group] = tables["spm_unit"].rename(
            columns={"spm_unit_id": f"{group}_id"}
        )
        tables["person"][f"person_{group}_id"] = tables["person"].person_spm_unit_id
    source_frame = Frame(
        tables, US_SCHEMA, {"household": partial_frame.weights_for("household")}
    )
    delivered, _ = with_us_spm_role_source(
        source_frame, {2024: source}, source_pins={2024: pin}
    )
    dataset_path = tmp_path / "role.h5"
    PolicyEngineUSEngine().write_dataset(delivered, dataset_path, period=2024)
    native = USSingleYearDataset(file_path=str(dataset_path))
    assert native.person[NATIVE_SPM_ROLE].dtype == np.bool_
    assert (
        native.person[NATIVE_SPM_ROLE].tolist()
        == delivered.table("person")[NATIVE_SPM_ROLE].tolist()
    )
