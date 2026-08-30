from __future__ import annotations

import copy
import hashlib
import io
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
import pytest

import microcosm.build.us_runtime.org_wages as org_wages
import microcosm.build.us_runtime.release_weeks_worked as module
from microcosm.build.us_runtime.puf_support import clone_us_frame_for_puf_support
from microcosm.build.us_runtime.release_weeks_worked import (
    US_RELEASE_WEEKS_WORKED_OPERATION,
    US_RELEASE_WEEKS_WORKED_STAGE_NAME,
    ReleaseWeeksWorkedResult,
    us_release_weeks_worked_gate,
    us_release_weeks_worked_stage_spec,
    with_us_release_weeks_worked,
)
from microcosm.build.us_runtime.source_runtime import us_source_operation_handlers
from microcosm.build.us_runtime.spine_assembly import assemble_spines
from microcosm.build.us_runtime.support_provenance import (
    support_channel_column,
    support_clone_index_column,
)
from microcosm.frame import US_SCHEMA, Frame, WeightKind, Weights

_FIXTURE_CROSSTAB = {
    "blank": {"allocated": 0, "not_allocated": 1},
    "nonblank": {"allocated": 1, "not_allocated": 1},
}
_POOL_IDENTITY = {
    "period": 2024,
    "pool_h5_sha256": "a" * 64,
    "pool_manifest_sha256": "b" * 64,
}


def _source_frame(*, acs: bool) -> Frame:
    if acs:
        household_ids = np.asarray([1, 2], dtype=np.int64)
        person_ids = np.asarray([0, 1, 2], dtype=np.int64)
        memberships = np.asarray([1, 1, 2], dtype=np.int64)
        source_people = np.asarray([1, 2, 1], dtype=np.int64)
        serials = ["2024HU0000001", "2024GQ0000002"]
    else:
        household_ids = np.asarray([1], dtype=np.int64)
        person_ids = np.asarray([0], dtype=np.int64)
        memberships = np.asarray([1], dtype=np.int64)
        source_people = np.asarray([1], dtype=np.int64)
        serials = ["ASEC0000000001"]

    offsets = {
        "tax_unit": 100,
        "spm_unit": 200,
        "family": 300,
        "marital_unit": 400,
    }
    person = pd.DataFrame(
        {
            "person_id": person_ids,
            "person_household_id": memberships,
            "age": np.full(len(person_ids), 35.0),
            "source_row_id": person_ids,
            "source_year": 2024,
            "source_household_id": memberships,
            "source_person_id": source_people,
            "SPORDER": source_people,
            "WKSWORK": np.nan if acs else 20.0,
        }
    )
    for entity, offset in offsets.items():
        person[f"person_{entity}_id"] = memberships + offset

    household = pd.DataFrame(
        {"household_id": household_ids, "SERIALNO": serials}
    )
    tables: dict[str, pd.DataFrame] = {"person": person, "household": household}
    for entity, offset in offsets.items():
        tables[entity] = pd.DataFrame({f"{entity}_id": household_ids + offset})

    return Frame(
        tables,
        US_SCHEMA,
        {
            "household": Weights(
                np.ones(len(household_ids), dtype=np.float64),
                WeightKind.DESIGN,
            )
        },
        pd.Series(["acs_2024_1yr" if acs else "asec_2024"] * len(person)),
    )


def _stacked_frame() -> Frame:
    assembled = assemble_spines(
        {"asec": _source_frame(acs=False), "acs": _source_frame(acs=True)},
        household_mass_shares={"asec": 0.5, "acs": 0.5},
    )
    cloned = clone_us_frame_for_puf_support(assembled)
    return _with_one_acs_tail_clone(cloned)


def _with_one_acs_tail_clone(frame: Frame) -> Frame:
    person = frame.table("person")
    person_channel = support_channel_column("person")
    person_clone = support_clone_index_column("person")
    selected_mask = person[person_channel].eq("acs") & person[person_clone].eq(1)
    selected_position = int(np.flatnonzero(selected_mask.to_numpy())[-1])
    selected_person = person.iloc[[selected_position]].copy()

    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    for link in frame.links:
        tables[link] = frame.link(link).copy()
    appended_positions: dict[str, int] = {}
    replacement_memberships: dict[str, int] = {}
    for entity in frame.schema.group_entities:
        id_column = frame.schema.entity_id_column(entity)
        membership_column = frame.schema.membership_column(entity)
        old_id = selected_person[membership_column].iloc[0]
        source_table = frame.table(entity)
        old_position = int(
            np.flatnonzero(source_table[id_column].eq(old_id).to_numpy())[0]
        )
        appended_positions[entity] = old_position
        clone = source_table.iloc[[old_position]].copy()
        new_id = int(pd.to_numeric(source_table[id_column]).max()) + 1
        clone[id_column] = new_id
        clone[support_clone_index_column(entity)] = 2
        replacement_memberships[membership_column] = new_id
        tables[entity] = pd.concat([tables[entity], clone], ignore_index=True)

    person_id = frame.schema.entity_id_column("person")
    selected_person[person_id] = int(pd.to_numeric(person[person_id]).max()) + 1
    selected_person[person_clone] = 2
    for membership_column, replacement in replacement_memberships.items():
        selected_person[membership_column] = replacement
    tables["person"] = pd.concat(
        [tables["person"], selected_person], ignore_index=True
    )

    weights: dict[str, Weights] = {}
    for entity in frame.weighted_entities:
        existing = frame.weights_for(entity)
        position = appended_positions[entity]
        values = np.append(existing.values, existing.values[position])
        weights[entity] = Weights(values, existing.kind)
    strata = pd.concat(
        [frame.strata, frame.strata.iloc[[selected_position]]], ignore_index=True
    )
    return Frame(
        tables,
        frame.schema,
        weights,
        strata,
        mass_log=frame.mass_log,
        metadata=frame.metadata,
    )


def _raw_person() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SERIALNO": ["2024HU0000001", "2024HU0000001", "2024GQ0000002"],
            "SPORDER": [1, 2, 1],
            "WKWN": [np.nan, 10, 52],
            "FWKWNP": [0, 1, 0],
        }
    )


def _write_person_zip(
    path: Path,
    person: pd.DataFrame,
    *,
    member_names: tuple[str, str] = ("psam_pusa.csv", "psam_pusb.csv"),
) -> str:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for member, rows in zip(
            member_names,
            (person.iloc[:2], person.iloc[2:]),
            strict=True,
        ):
            buffer = io.StringIO()
            rows.to_csv(buffer, index=False)
            archive.writestr(member, buffer.getvalue())
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _weeks(
    frame: Frame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    raw_person: pd.DataFrame | None = None,
    member_names: tuple[str, str] = ("psam_pusa.csv", "psam_pusb.csv"),
) -> ReleaseWeeksWorkedResult:
    archive = tmp_path / "csv_pus.zip"
    sha256 = _write_person_zip(
        archive,
        _raw_person() if raw_person is None else raw_person,
        member_names=member_names,
    )
    monkeypatch.setattr(module, "ACS_2024_PERSON_ZIP_SHA256", sha256)
    monkeypatch.setattr(module, "ACS_2024_PERSON_ROW_COUNT", 3)
    monkeypatch.setattr(
        module,
        "ACS_2024_WKWN_ALLOCATION_CROSSTAB",
        copy.deepcopy(_FIXTURE_CROSSTAB),
    )
    return with_us_release_weeks_worked(
        frame,
        time_period=2024,
        acs_person_zip=archive,
        acs_person_sha256=sha256,
        pool_identity=_POOL_IDENTITY,
        chunksize=1,
    )


def test_stage_is_closed_registered_and_documents_the_authorized_mapping() -> None:
    stage = us_release_weeks_worked_stage_spec()
    assert stage.stage == US_RELEASE_WEEKS_WORKED_STAGE_NAME
    operation = next(
        item for item in stage.operations if item.kind == US_RELEASE_WEEKS_WORKED_OPERATION
    )
    assert operation.parameters == module._OPERATION_PARAMETERS
    assert stage.outputs == ("weeks_worked",)
    assert "rolling 12 months" in stage.notes
    assert "calendar 2023" in stage.notes
    assert "reported-or-allocated" in stage.notes
    acs_person_artifact = next(
        artifact
        for artifact in stage.artifacts
        if artifact.get("format") == "census_acs_pums_person_zip"
    )
    assert acs_person_artifact["sha256"] == module.ACS_2024_PERSON_ZIP_SHA256
    assert acs_person_artifact["expected_rows"] == module.ACS_2024_PERSON_ROW_COUNT
    assert us_source_operation_handlers()[US_RELEASE_WEEKS_WORKED_OPERATION] is (
        module.derive_us_release_weeks_worked_from_manifest
    )


def test_release_mapping_is_origin_aware_clone_stable_and_fully_receipted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = _stacked_frame()
    result = _weeks(before, tmp_path, monkeypatch)
    person = result.frame.table("person")
    channel = person[support_channel_column("person")]

    assert person.loc[channel.eq("asec"), "weeks_worked"].eq(20).all()
    acs = person.loc[channel.eq("acs")]
    canonical_values = (
        acs.groupby("person_source_id", sort=False)["weeks_worked"].first().tolist()
    )
    assert sorted(canonical_values) == [0.0, 10.0, 52.0]
    assert (
        acs.groupby("person_source_id")["weeks_worked"]
        .nunique(dropna=False)
        .eq(1)
        .all()
    )

    receipt = result.receipt
    assert receipt["artifacts"]["authenticated_pool"] == _POOL_IDENTITY
    assert receipt["raw_domains"]["acs_archive"][
        "WKWN_blank_nonblank_by_allocation"
    ] == _FIXTURE_CROSSTAB
    assert receipt["join"]["unmatched_pool_source_people"] == 0
    assert receipt["mapping"]["acs_blank_recode"]["owner"] == "Microcosm"
    assert receipt["mapping"]["acs_blank_recode"]["output"] == 0

    gate = us_release_weeks_worked_gate(before, result)
    assert gate.passed, gate.failures
    assert gate.details["by_source_channel_and_clone_index"] == {
        "asec": {"0": 1, "1": 1, "2": 0},
        "acs": {"0": 3, "1": 3, "2": 1},
    }
    assert gate.details["per_source_clone_disagreements"] == {"asec": 0, "acs": 0}
    assert gate.details["column_diff"]["changed_columns"] == [
        "person.weeks_worked"
    ]
    assert (
        gate.details["column_diff"]["non_weeks_person_sha256_before"]
        == gate.details["column_diff"]["non_weeks_person_sha256_after"]
    )


def test_measured_release_weeks_flow_through_org_and_flsa(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _stacked_frame()
    person = frame.table("person")
    person["is_female"] = False
    person["PRDTRACE"] = 1
    person["PRDTHSP"] = 0
    person["POCCU2"] = 20
    person["employment_income_before_lsr"] = 26_000.0
    person["weekly_hours_worked_before_lsr"] = 40.0
    person["hours_worked_last_week"] = 50.0
    person["state_fips"] = 6
    measured = _weeks(frame, tmp_path, monkeypatch)
    measured_weeks = measured.frame.table("person")["weeks_worked"].to_numpy(
        dtype=np.float64
    )

    captured: dict[str, pd.DataFrame] = {}

    class Fitted:
        def predict(self, features: pd.DataFrame) -> pd.DataFrame:
            captured["features"] = features.copy()
            return pd.DataFrame(
                {
                    "hourly_wage": np.full(len(features), 25.0),
                    "is_paid_hourly": np.ones(len(features)),
                },
                index=features.index,
            )

    class CaptureQRF:
        def __init__(self, **kwargs: object) -> None:
            pass

        def fit(self, *args: object, **kwargs: object) -> Fitted:
            return Fitted()

    monkeypatch.setattr("microcosm.fit.QRF", CaptureQRF)
    monkeypatch.setattr(
        org_wages,
        "_flsa_policy",
        lambda year: (107_432.0, 35_568.0, 57_470.4, 40.0, 1.5),
    )
    donor = pd.DataFrame(
        {
            "employment_income": [52_000.0],
            "weekly_hours_worked": [40.0],
            "age": [35.0],
            "is_female": [0.0],
            "is_hispanic": [0.0],
            "race_wbho": [1.0],
            "state_fips": [6.0],
            "hourly_wage": [25.0],
            "is_paid_hourly": [1.0],
            "sample_weight": [1.0],
        }
    )

    consumed = org_wages.with_us_org_wages_inputs(
        measured.frame,
        seed=0,
        time_period=2024,
        org_donor=donor,
    )
    expected_feature_income = np.divide(
        52.0 * 26_000.0,
        measured_weeks,
        out=np.full_like(measured_weeks, 26_000.0),
        where=measured_weeks > 0,
    )
    np.testing.assert_allclose(
        captured["features"]["employment_income"].to_numpy(),
        expected_feature_income,
    )
    expected_premium = np.where(
        measured_weeks > 0,
        np.float32(26_000.0 / 11.0),
        np.float32(0.0),
    )
    output_person = consumed.table("person")
    np.testing.assert_array_equal(
        output_person["weeks_worked"].to_numpy(), measured_weeks
    )
    np.testing.assert_allclose(
        output_person["fsla_overtime_premium"].to_numpy(), expected_premium
    )


@pytest.mark.requires_us
def test_authorized_2024_weeks_values_drive_live_spm_work_expenses() -> None:
    import policyengine_us

    def work_expenses(weeks: int) -> float:
        simulation = policyengine_us.Simulation(
            situation={
                "people": {
                    "adult_worker": {
                        "age": {2024: 40},
                        "weeks_worked": {2024: weeks},
                        "employment_income": {2024: 20_000},
                    },
                    "adult_nonworker": {
                        "age": {2024: 38},
                        "weeks_worked": {2024: 30},
                        "employment_income": {2024: 0},
                    },
                    "child": {
                        "age": {2024: 12},
                        "weeks_worked": {2024: 52},
                        "employment_income": {2024: 500},
                    },
                },
                "spm_units": {
                    "spm_unit": {
                        "members": ["adult_worker", "adult_nonworker", "child"]
                    }
                },
            }
        )
        return float(simulation.calculate("spm_unit_work_expenses", 2024)[0])

    ten_week_result = work_expenses(10)
    twenty_week_result = work_expenses(20)
    assert ten_week_result == pytest.approx(349.945, abs=0.001)
    assert twenty_week_result == pytest.approx(699.890, abs=0.001)
    assert twenty_week_result - ten_week_result == pytest.approx(349.945, abs=0.001)


@pytest.mark.parametrize("bad_value", [np.nan, 52.5, 53, -1])
def test_asec_wkswork_domain_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_value: float,
) -> None:
    frame = _stacked_frame()
    person = frame.table("person")
    person.loc[person[support_channel_column("person")].eq("asec"), "WKSWORK"] = (
        bad_value
    )
    with pytest.raises(ValueError, match="ASEC WKSWORK"):
        _weeks(frame, tmp_path, monkeypatch)


@pytest.mark.parametrize(
    ("column", "bad_value", "match"),
    [
        ("WKWN", 0, "ACS WKWN"),
        ("WKWN", 12.5, "ACS WKWN"),
        ("WKWN", 53, "ACS WKWN"),
        ("WKWN", "not-a-number", "ACS WKWN"),
        ("FWKWNP", 2, "ACS FWKWNP"),
    ],
)
def test_acs_raw_domains_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    column: str,
    bad_value: object,
    match: str,
) -> None:
    raw = _raw_person()
    raw[column] = raw[column].astype(object)
    raw.loc[1, column] = bad_value
    with pytest.raises(ValueError, match=match):
        _weeks(_stacked_frame(), tmp_path, monkeypatch, raw_person=raw)


def test_archive_authentication_precedes_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = tmp_path / "csv_pus.zip"
    sha256 = _write_person_zip(archive, _raw_person())
    monkeypatch.setattr(module, "ACS_2024_PERSON_ZIP_SHA256", sha256)
    with pytest.raises(ValueError, match="pin must be the reviewed"):
        with_us_release_weeks_worked(
            _stacked_frame(),
            time_period=2024,
            acs_person_zip=archive,
            acs_person_sha256="0" * 64,
            pool_identity=_POOL_IDENTITY,
        )


def test_archive_member_inventory_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="archive members differ"):
        _weeks(
            _stacked_frame(),
            tmp_path,
            monkeypatch,
            member_names=("psam_pusa.csv", "unexpected.csv"),
        )


def test_semantic_join_must_be_total(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _raw_person()
    raw.loc[2, "SERIALNO"] = "2024UNSELECTED"
    with pytest.raises(ValueError, match="exact raw/pool semantic-key set"):
        _weeks(_stacked_frame(), tmp_path, monkeypatch, raw_person=raw)


def test_semantic_join_rejects_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _raw_person()
    raw.loc[2, ["SERIALNO", "SPORDER"]] = raw.loc[
        1, ["SERIALNO", "SPORDER"]
    ].to_numpy()
    with pytest.raises(ValueError, match="key collision"):
        _weeks(_stacked_frame(), tmp_path, monkeypatch, raw_person=raw)


def test_conflicting_preexisting_weeks_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = _stacked_frame()
    frame.table("person")["weeks_worked"] = 99.0
    with pytest.raises(ValueError, match="conflicting pre-existing"):
        _weeks(frame, tmp_path, monkeypatch)


def test_gate_rejects_clone_disagreement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = _stacked_frame()
    result = _weeks(before, tmp_path, monkeypatch)
    person = result.frame.table("person")
    clone = person[support_clone_index_column("person")].eq(1)
    person.loc[person.index[clone][0], "weeks_worked"] += 1

    gate = us_release_weeks_worked_gate(before, result)
    assert not gate.passed
    assert any("clone disagreement" in failure for failure in gate.failures)


def test_gate_rejects_nonweeks_column_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = _stacked_frame()
    result = _weeks(before, tmp_path, monkeypatch)
    result.frame.table("person").loc[0, "age"] += 1

    gate = us_release_weeks_worked_gate(before, result)
    assert not gate.passed
    assert any("non-output digest changed" in failure for failure in gate.failures)


def test_gate_rejects_coherent_all_clone_value_tamper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = _stacked_frame()
    result = _weeks(before, tmp_path, monkeypatch)
    person = result.frame.table("person")
    source_id = person.loc[
        person[support_channel_column("person")].eq("acs"), "person_source_id"
    ].iloc[0]
    person.loc[person["person_source_id"].eq(source_id), "weeks_worked"] = 1

    gate = us_release_weeks_worked_gate(before, result)
    assert not gate.passed
    assert any("source-value receipt" in failure for failure in gate.failures)


def test_gate_rejects_coherent_registered_operation_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = _stacked_frame()
    original = module.derive_us_release_weeks_worked_from_manifest

    def coherently_swapped_operation(frame, operation, context):
        output = original(frame, operation, context)
        channel_column = support_channel_column("person")
        acs = output[channel_column].eq("acs")
        by_source = output.loc[acs].groupby("person_source_id")["weeks_worked"].first()
        nonzero = by_source.loc[by_source.gt(0)]
        left_source, right_source = nonzero.index[:2]
        left_value, right_value = nonzero.iloc[:2]
        output.loc[
            acs & output["person_source_id"].eq(left_source), "weeks_worked"
        ] = right_value
        output.loc[
            acs & output["person_source_id"].eq(right_source), "weeks_worked"
        ] = left_value
        return output

    monkeypatch.setattr(
        module,
        "derive_us_release_weeks_worked_from_manifest",
        coherently_swapped_operation,
    )
    result = _weeks(before, tmp_path, monkeypatch)

    gate = us_release_weeks_worked_gate(before, result)

    assert not gate.passed
    assert any("source-value receipt" in failure for failure in gate.failures)


def test_allocation_swap_with_unchanged_marginals_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _raw_person()
    raw["FWKWNP"] = [1, 0, 0]
    with pytest.raises(ValueError, match="allocation cross-tab changed"):
        _weeks(_stacked_frame(), tmp_path, monkeypatch, raw_person=raw)


def test_gate_rejects_joint_crosstab_tamper_even_with_fresh_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = _stacked_frame()
    result = _weeks(before, tmp_path, monkeypatch)
    receipt = copy.deepcopy(result.receipt)
    receipt["raw_domains"]["acs_archive"][
        "WKWN_blank_nonblank_by_allocation"
    ] = {
        "blank": {"allocated": 1, "not_allocated": 0},
        "nonblank": {"allocated": 0, "not_allocated": 2},
    }
    receipt["sha256"] = module._canonical_sha256(
        {key: value for key, value in receipt.items() if key != "sha256"}
    )
    tampered = ReleaseWeeksWorkedResult(frame=result.frame, receipt=receipt)

    gate = us_release_weeks_worked_gate(before, tampered)
    assert not gate.passed
    assert any("joint receipt changed" in failure for failure in gate.failures)


@pytest.mark.parametrize(
    ("mutation", "failure_text"),
    [
        ("asec_domain", "live ASEC raw-domain counts"),
        ("asec_source_year", "live ASEC source-year rows"),
        ("acs_source_people", "live ACS source-person counts"),
        ("acs_support_rows", "live ACS support-row count"),
        ("acs_clone_counts", "live ACS clone-role counts"),
        ("acs_semantic_key", "live ACS semantic keys"),
    ],
)
def test_gate_rejects_rehashed_receipt_that_contradicts_live_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    failure_text: str,
) -> None:
    before = _stacked_frame()
    result = _weeks(before, tmp_path, monkeypatch)
    receipt = copy.deepcopy(result.receipt)
    if mutation == "asec_domain":
        receipt["raw_domains"]["asec_WKSWORK"]["minimum"] = 1
    elif mutation == "asec_source_year":
        receipt["period_identity"]["asec_source_year_rows"] = {"1900": 2}
    elif mutation == "acs_source_people":
        receipt["join"]["acs_source_people"] = 1
        receipt["join"]["selected_raw_person_rows"] = 1
        receipt["join"]["matched_pool_source_people"] = 1
    elif mutation == "acs_support_rows":
        receipt["join"]["acs_support_rows"] = 8
        receipt["join"]["acs_support_rows_by_clone_index"] = {
            "0": 4,
            "1": 3,
            "2": 1,
        }
    elif mutation == "acs_clone_counts":
        receipt["join"]["acs_support_rows_by_clone_index"] = {
            "0": 2,
            "1": 4,
            "2": 1,
        }
    else:
        assert mutation == "acs_semantic_key"
        receipt["join"]["semantic_key_sha256"] = "0" * 64
    receipt["sha256"] = module._canonical_sha256(
        {key: value for key, value in receipt.items() if key != "sha256"}
    )
    tampered = ReleaseWeeksWorkedResult(frame=result.frame, receipt=receipt)

    gate = us_release_weeks_worked_gate(before, tampered)

    assert not gate.passed
    assert any(failure_text in failure for failure in gate.failures)


def test_direct_2025_materialization_is_rejected() -> None:
    with pytest.raises(ValueError, match="only for period 2024"):
        with_us_release_weeks_worked(
            _stacked_frame(),
            time_period=2025,
            acs_person_zip="unused.zip",
            acs_person_sha256="0" * 64,
            pool_identity=_POOL_IDENTITY,
        )
