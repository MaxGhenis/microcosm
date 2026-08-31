"""Native Armenia ILCS spine: authenticated ingest and refusal contracts."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from microcosm.build.am_runtime import (
    AM_COUNTRY_ATTR,
    AM_DATA_RIGHTS_SHA256_ATTR,
    AM_HOUSEHOLD_WEIGHT_KIND_ATTR,
    AM_ILCS_HOUSEHOLD_ROWS,
    AM_ILCS_MEMBER_ROWS,
    AM_ILCS_OUTPUT_COLUMNS,
    AM_MASS_LOG_ATTR,
    AM_UNIT_RECORD_PUBLICATION_STATUS_ATTR,
    build_am_ilcs_spine,
    load_am_national_frame,
    write_am_national_frame,
)
from microcosm.build.country_spec import load_country_spec
from microcosm.build.source_manifest import SourceStageSpec
from microcosm.build.spec_engine import load_bundle
from microcosm.build.spec_engine.compiler_ir import compile_spec
from microcosm.build.trace import sha256_file
from microcosm.frame import WeightKind, engine_tables
from tools.build_am_ilcs_spine import _build_sidecar, _validate_args


def _raw_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    household = pd.DataFrame(
        {
            "interview__key": ["hh-b", "hh-a"],
            "date_q": [2024.9, 2024.10],
            "hh_02": [11, 1],
            "settlement": [2, 1],
            "members": [3, 1],
            "memnal": [2, 1],
            "Weight": [10.0, 20.0],
            "pweight": [20.0, 20.0],
            "expend": [100_000.0, 200_000.0],
            "monincome": [120_000.0, 210_000.0],
            "totincome": [125_000.0, 215_000.0],
            "nonmoninc": [5_000.0, 5_000.0],
            "y1_3amd.1.00": [80_000.0, 150_000.0],
            "y1_3amd.2.00": [0.0, 40_000.0],
            "y1_3amd.4.00": [40_000.0, 0.0],
            "y1_3amd.6.00": [0.0, 20_000.0],
            "y1_3amd.8.00": [0.0, 0.0],
            "y1_3amd.9.00": [0.0, 0.0],
            "y1_3amd.10.00": [0.0, 0.0],
            "y1_3amd.12.00": [0.0, 0.0],
            "y1_3amd.17.00": [0.0, 0.0],
            "y1_3amd.18.00": [0.0, 0.0],
            "y1_3amd.19.00": [0.0, 0.0],
            "aec_r": [60_000.0, 90_000.0],
            "poverty": [2, 1],
        }
    )
    member = pd.DataFrame(
        {
            "interview__key": ["hh-b", "hh-b", "hh-a"],
            "mem_001__id": [1, 2, 1],
            "weight": [10.0, 10.0, 20.0],
            "date": [2024.9, 2024.9, 2024.10],
            "mem_02": [1, 2, 2],
            "mem_03": [1, 2, 1],
            "mem_05": [40, 39, 55],
            "ed_03": [6, 6, 3],
            "emp_04": [85, np.nan, 1],
            "emp_05": [2, np.nan, 5],
            "emp_10": [40.0, np.nan, 30.0],
            "emplj": [1.0, np.nan, 1.0],
            "unemployed": [np.nan, 1.0, np.nan],
            "activ": [1.0, 1.0, 1.0],
        }
    )
    return household, member


def _write_raw(
    root: Path, household: pd.DataFrame, member: pd.DataFrame
) -> SourceStageSpec:
    pytest.importorskip("openpyxl")
    root.mkdir(parents=True, exist_ok=True)
    household_path = root / "households_2024.xlsx"
    member_path = root / "members_2024.xlsx"
    with pd.ExcelWriter(household_path, engine="openpyxl") as writer:
        household.to_excel(writer, sheet_name="Household - 2024", index=False)
        pd.DataFrame({"Variable": ["expend"], "Label": ["per month in dram"]}).to_excel(
            writer, sheet_name="Labels", index=False
        )
    member.to_excel(member_path, sheet_name="Sheet1", index=False)
    return SourceStageSpec.from_mapping(
        {
            "stage": "ingest_am_ilcs_2024",
            "survey": "synthetic ILCS",
            "source": "https://armstat.am/en/?nid=205",
            "grain": "person_household",
            "artifacts": [
                {
                    "role": "ilcs_table",
                    "table": "household",
                    "kind": "public_microdata",
                    "format": "xlsx",
                    "vintage": "2024",
                    "locator": household_path.name,
                    "sheet": "Household - 2024",
                    "sha256": sha256_file(household_path),
                    "size_bytes": household_path.stat().st_size,
                    "expected_rows": len(household),
                    "runtime_sha256_required": True,
                },
                {
                    "role": "ilcs_table",
                    "table": "member",
                    "kind": "public_microdata",
                    "format": "xlsx",
                    "vintage": "2024",
                    "locator": member_path.name,
                    "sheet": "Sheet1",
                    "sha256": sha256_file(member_path),
                    "size_bytes": member_path.stat().st_size,
                    "expected_rows": len(member),
                    "runtime_sha256_required": True,
                },
            ],
            "operations": [],
            "outputs": list(AM_ILCS_OUTPUT_COLUMNS),
        }
    )


def _build(
    tmp_path: Path,
    household: pd.DataFrame | None = None,
    member: pd.DataFrame | None = None,
):
    default_household, default_member = _raw_tables()
    household = default_household if household is None else household
    member = default_member if member is None else member
    stage = _write_raw(tmp_path, household, member)
    return build_am_ilcs_spine(tmp_path, stage=stage)


def test_packaged_contract_keeps_donor_lane_and_adds_exact_native_pins() -> None:
    spec = load_country_spec("am")
    stages = spec.sources.stage_map()
    assert tuple(stages) == (
        "load_populace_us_support_pool",
        "assign_am_marz",
        "ingest_am_ilcs_2024",
    )
    stage = stages["ingest_am_ilcs_2024"]
    assert stage.outputs == AM_ILCS_OUTPUT_COLUMNS
    artifacts = {artifact["table"]: artifact for artifact in stage.artifacts}
    assert {artifact["kind"] for artifact in artifacts.values()} == {
        "restricted_microdata"
    }
    assert {
        key: artifacts["household"][key]
        for key in ("sha256", "size_bytes", "expected_rows", "runtime_sha256_required")
    } == {
        "sha256": "48527e2de376e7ef88dc04ac9fe2de2fdc1728d34ce2d753ce165ab5c496590e",
        "size_bytes": 2_186_167,
        "expected_rows": AM_ILCS_HOUSEHOLD_ROWS,
        "runtime_sha256_required": True,
    }
    assert {
        key: artifacts["member"][key]
        for key in ("sha256", "size_bytes", "expected_rows", "runtime_sha256_required")
    } == {
        "sha256": "6d52cc9867147043decbc8539dd40ac428468fba0caed60176b28bd7bc1a24f5",
        "size_bytes": 8_613_335,
        "expected_rows": AM_ILCS_MEMBER_ROWS,
        "runtime_sha256_required": True,
    }
    assert (
        compile_spec(load_bundle("am")).resource("spine")["assembly"][
            "mass_anchor_channel"
        ]
        == "populace_us_support"
    )
    assert spec.release_contract is not None
    rights = spec.release_contract.data_rights
    assert rights is not None
    assert rights.access == "public_anonymised_download"
    assert rights.local_analysis == "authorized"
    assert rights.raw_redistribution == "no_express_grant"
    assert (
        rights.derived_unit_record_publication == "blocked_pending_explicit_permission"
    )
    assert rights.permission_record is None


def test_monthly_amount_catalog_is_amd_and_never_implicitly_annualized() -> None:
    bundle = load_bundle("am")
    by_key = {column.key: column for column in bundle.columns}
    monthly = [key for key in by_key if key.endswith("_monthly")]
    assert monthly
    assert {by_key[key].unit for key in monthly} == {"amd"}
    assert {by_key[key].period for key in monthly} == {"month"}


def test_build_maps_native_entities_and_records_weight_and_basis_receipts(
    tmp_path: Path,
) -> None:
    result = _build(tmp_path)
    frame = result.frame
    person = frame.table("person")
    household = frame.table("household")

    assert person["person_id"].tolist() == [1001, 2001, 2002]
    assert household["household_id"].tolist() == [1, 2]
    assert household["ilcs_interview_key"].tolist() == ["hh-a", "hh-b"]
    assert household["survey_month"].tolist() == [10, 9]
    assert household["marz_code_observed"].tolist() == ["YEREVAN", "TAVUSH"]
    assert person["sex"].tolist() == ["FEMALE", "MALE", "FEMALE"]
    assert person["is_employee"].tolist() == [False, True, False]
    assert frame.weights_for("household").kind is WeightKind.DESIGN
    assert frame.weights_for("household").values.tolist() == [20.0, 10.0]
    assert "household_weight" not in household
    assert engine_tables(frame, weighted_entities=("household",))["household"][
        "household_weight"
    ].tolist() == [20.0, 10.0]

    receipt = result.receipt.as_dict()
    assert receipt["join"] == {
        "validation": "many_to_one_total_on_both_sides",
        "household_rows": 2,
        "member_rows": 3,
        "present_member_count_field": "memnal",
        "roster_member_count_field": "members",
        "roster_member_discrepant_households": 1,
    }
    assert receipt["amount_basis"] == {
        "currency": "AMD",
        "definition_period": "month",
        "annualization_factor": 1.0,
        "annualization_applied": False,
        "survey_period": "2024",
    }
    observed = receipt["validation_only_observed_monthly_amd"]
    assert observed["classification"] == "validation_only"
    assert observed["annualization_applied"] is False
    assert observed["totals"]["employment_income_monthly"] == 3_800_000.0
    assert observed["totals"]["pension_income_reported_monthly"] == 400_000.0
    assert observed["totals"]["family_benefit_reported_monthly"] == 400_000.0
    assert "adult_equivalent_consumption_monthly" not in observed["totals"]


def test_dense_ids_are_content_determined_under_source_row_shuffle(
    tmp_path: Path,
) -> None:
    household, member = _raw_tables()
    first = _build(tmp_path / "first", household, member).frame
    second = _build(
        tmp_path / "second",
        household.sample(frac=1, random_state=2).reset_index(drop=True),
        member.sample(frac=1, random_state=3).reset_index(drop=True),
    ).frame
    first_households = first.table("household").set_index("ilcs_interview_key")
    second_households = second.table("household").set_index("ilcs_interview_key")
    assert (
        first_households["household_id"].to_dict()
        == second_households["household_id"].to_dict()
    )
    assert (
        first.table("person")["person_id"].tolist()
        == second.table("person")["person_id"].tolist()
    )


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda household, member: member.__setitem__(
                "interview__key", ["hh-b", "hh-b", "missing"]
            ),
            "member keys absent from households",
        ),
        (
            lambda household, member: member.drop(index=2, inplace=True),
            "households with no present members",
        ),
        (
            lambda household, member: member.__setitem__("mem_001__id", [1, 1, 1]),
            "member key pairs must be unique",
        ),
        (
            lambda household, member: member.__setitem__("mem_001__id", [1, 1000, 1]),
            r"must be in \[1, 999\]",
        ),
        (
            lambda household, member: household.__setitem__("memnal", [1, 1]),
            "memnal must equal joined present-member rows",
        ),
        (
            lambda household, member: household.__setitem__("members", [1, 1]),
            "members must be greater than or equal to memnal",
        ),
        (
            lambda household, member: member.__setitem__("mem_05", [-1, 39, 55]),
            "mem_05 must be a non-negative integer",
        ),
        (
            lambda household, member: member.__setitem__("weight", [10, 11, 20]),
            "member.weight must equal household.Weight",
        ),
        (
            lambda household, member: household.__setitem__("pweight", [21, 20]),
            r"pweight must equal Weight \* memnal",
        ),
        (
            lambda household, member: household.__setitem__("expend", [-1, 1]),
            "expend must be non-negative",
        ),
        (
            lambda household, member: household.__setitem__(
                "expend", ["not-numeric", 1]
            ),
            "expend must be numeric when present",
        ),
        (
            lambda household, member: member.__setitem__(
                "emp_05", [2, "not-numeric", 5]
            ),
            "emp_05 must be numeric when present",
        ),
        (
            lambda household, member: member.__setitem__(
                "activ", [1, "not-numeric", 1]
            ),
            "activ must be numeric when present",
        ),
        (
            lambda household, member: member.__setitem__(
                "date", [2024.02, 2024.01, 2024.10]
            ),
            "member survey month must match",
        ),
    ],
)
def test_adversarial_relationship_weight_and_basis_failures_are_loud(
    tmp_path: Path, mutator, message: str
) -> None:
    household, member = _raw_tables()
    mutator(household, member)
    with pytest.raises(ValueError, match=message):
        _build(tmp_path, household, member)


def test_only_the_observed_compact_september_month_is_normalized(
    tmp_path: Path,
) -> None:
    household, member = _raw_tables()
    household["date_q"] = [2024.2, 2024.10]
    member["date"] = [2024.2, 2024.2, 2024.10]
    with pytest.raises(ValueError, match="months within 2024"):
        _build(tmp_path, household, member)


def test_runtime_authenticates_hash_and_row_count_before_assembly(
    tmp_path: Path,
) -> None:
    household, member = _raw_tables()
    stage = _write_raw(tmp_path, household, member)
    bad_artifacts = [dict(artifact) for artifact in stage.artifacts]
    bad_artifacts[0]["sha256"] = "0" * 64
    bad_stage = SourceStageSpec.from_mapping(
        {
            "stage": stage.stage,
            "survey": stage.survey,
            "source": stage.source,
            "grain": stage.grain,
            "artifacts": bad_artifacts,
            "operations": [],
            "outputs": list(stage.outputs),
        }
    )
    with pytest.raises(ValueError, match="not the pinned"):
        build_am_ilcs_spine(tmp_path, stage=bad_stage)

    bad_artifacts[0]["sha256"] = stage.artifacts[0]["sha256"]
    bad_artifacts[0]["expected_rows"] = 3
    bad_stage = SourceStageSpec.from_mapping(
        {
            "stage": stage.stage,
            "survey": stage.survey,
            "source": stage.source,
            "grain": stage.grain,
            "artifacts": bad_artifacts,
            "operations": [],
            "outputs": list(stage.outputs),
        }
    )
    with pytest.raises(ValueError, match="not the pinned 3"):
        build_am_ilcs_spine(tmp_path, stage=bad_stage)


def test_staging_h5_round_trip_preserves_typed_weights(tmp_path: Path) -> None:
    pytest.importorskip("tables")
    pytest.importorskip("h5py")
    frame = _build(tmp_path / "raw").frame
    output = write_am_national_frame(frame, tmp_path / "am_ilcs_2024.h5")
    loaded, provenance = load_am_national_frame(output)

    assert provenance.source_h5 == output.resolve()
    assert loaded.table("person").equals(frame.table("person"))
    assert loaded.table("household").equals(frame.table("household"))
    assert loaded.weights_for("household").kind is WeightKind.DESIGN
    assert np.array_equal(
        loaded.weights_for("household").values,
        frame.weights_for("household").values,
    )
    h5py = pytest.importorskip("h5py")
    rights = load_country_spec("am").release_contract.data_rights
    assert rights is not None
    with h5py.File(output, mode="r") as file:
        assert file.attrs[AM_COUNTRY_ATTR] == "am"
        assert file.attrs[AM_DATA_RIGHTS_SHA256_ATTR] == rights.sha256
        assert file.attrs[AM_UNIT_RECORD_PUBLICATION_STATUS_ATTR] == (
            "blocked_pending_explicit_permission"
        )


def test_staging_h5_refuses_tampered_weight_metadata(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    pytest.importorskip("tables")
    output = write_am_national_frame(
        _build(tmp_path / "raw").frame,
        tmp_path / "am_ilcs_2024.h5",
    )
    with h5py.File(output, mode="r+") as file:
        file.attrs[AM_HOUSEHOLD_WEIGHT_KIND_ATTR] = "fabricated"
    with pytest.raises(ValueError, match="Unknown stored Armenian household weight"):
        load_am_national_frame(output)


def test_staging_h5_refuses_missing_required_metadata(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    pytest.importorskip("tables")
    output = write_am_national_frame(
        _build(tmp_path / "raw").frame,
        tmp_path / "am_ilcs_2024.h5",
    )
    with h5py.File(output, mode="r+") as file:
        del file.attrs[AM_MASS_LOG_ATTR]
    with pytest.raises(ValueError, match="missing metadata attribute"):
        load_am_national_frame(output)


def test_staging_h5_refuses_tampered_data_rights_metadata(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    pytest.importorskip("tables")
    output = write_am_national_frame(
        _build(tmp_path / "raw").frame,
        tmp_path / "am_ilcs_2024.h5",
    )
    with h5py.File(output, mode="r+") as file:
        file.attrs[AM_DATA_RIGHTS_SHA256_ATTR] = "0" * 64
    with pytest.raises(ValueError, match="data-rights metadata does not match"):
        load_am_national_frame(output)


def test_staging_h5_refuses_tampered_country_metadata(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    pytest.importorskip("tables")
    output = write_am_national_frame(
        _build(tmp_path / "raw").frame,
        tmp_path / "am_ilcs_2024.h5",
    )
    with h5py.File(output, mode="r+") as file:
        file.attrs[AM_COUNTRY_ATTR] = "us"
    with pytest.raises(ValueError, match="data-rights metadata does not match"):
        load_am_national_frame(output)


def test_build_sidecar_binds_inputs_output_and_validation_only_totals(
    tmp_path: Path,
) -> None:
    household, member = _raw_tables()
    raw_dir = tmp_path / "raw"
    stage = _write_raw(raw_dir, household, member)
    result = build_am_ilcs_spine(raw_dir, stage=stage)
    output = write_am_national_frame(result.frame, tmp_path / "am_ilcs_2024.h5")
    payload = _build_sidecar(
        frame=result.frame,
        stage=stage,
        stage_record=SimpleNamespace(
            produced=stage.outputs,
            nonzero_share={},
        ),
        transform=SimpleNamespace(last_receipt=result.receipt),
        output=output,
    )

    assert payload["release_eligible"] is False
    assert payload["publication_authorized"] is False
    rights = load_country_spec("am").release_contract.data_rights
    assert rights is not None
    assert payload["data_rights"] == {
        "sha256": rights.sha256,
        "envelope": rights.as_dict(),
    }
    assert payload["stage"]["name"] == "ingest_am_ilcs_2024"
    assert payload["stage"]["produced"] == list(stage.outputs)
    assert payload["output"]["sha256"] == sha256_file(output)
    assert payload["source_authentication"]["artifacts"]["household"][
        "sha256"
    ] == sha256_file(raw_dir / "households_2024.xlsx")
    spec = load_country_spec("am")
    assert payload["source_authentication"]["country_spec_fingerprint"] == (
        spec.fingerprint
    )
    assert payload["source_authentication"]["typed_spec_sha256"] == (
        spec.resolved_spec.spec_sha256
    )
    implementation_pins = payload["runtime"]["implementation_sha256"]
    assert set(implementation_pins) == {
        "microcosm.build.am_runtime.ilcs_spine",
        "microcosm.build.am_runtime.national_frame",
        "tools/build_am_ilcs_spine.py",
    }
    assert all(
        len(value) == 64 and set(value) <= set("0123456789abcdef")
        for value in implementation_pins.values()
    )
    assert (
        payload["validation_only_observed_monthly_amd"]["totals"][
            "employment_income_monthly"
        ]
        == 3_800_000.0
    )
    assert (
        "adult_equivalent_consumption_monthly"
        not in payload["validation_only_observed_monthly_amd"]["totals"]
    )


def test_native_cli_refuses_raw_or_derived_paths_inside_checkout(
    tmp_path: Path,
) -> None:
    repository = Path(__file__).resolve().parents[3]
    with pytest.raises(ValueError, match="outside the Microcosm repository"):
        _validate_args(
            SimpleNamespace(
                ilcs_raw_dir=repository,
                spine_h5=tmp_path / "frame.h5",
                build_sidecar=tmp_path / "frame.build.json",
            )
        )

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    with pytest.raises(ValueError, match="outside the Microcosm repository"):
        _validate_args(
            SimpleNamespace(
                ilcs_raw_dir=raw_dir,
                spine_h5=repository / "frame.h5",
                build_sidecar=tmp_path / "frame.build.json",
            )
        )
