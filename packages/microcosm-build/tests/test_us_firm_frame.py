"""Synthetic and conditional real-data tests for the US firm frame builder."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from microcosm.build.us_runtime.us_firms.artifact import (
    verify_us_firm_artifact,
    write_us_firm_artifact,
)
from microcosm.build.us_runtime.us_firms.form5500 import (
    firm_data_dir,
    read_sponsors,
)
from microcosm.build.us_runtime.us_firms.frame import (
    FIRM_TABLE_COLUMNS,
    USFirmBuildConfig,
    USFirmBuildResult,
    USFirmCoverageError,
    build_us_firm_frame,
    osha_measurement_reference,
    synthetic_us_firm_source_receipt,
)
from microcosm.build.us_runtime.us_firms.osha_ita import (
    apply_quality_rule,
    read_ita,
)
from microcosm.build.us_runtime.us_firms.staging import verify_staged_sources
from microcosm.build.us_runtime.us_firms.targets import (
    USFirmTargets,
    load_bds_validation_harness,
    load_susb_migration_harness,
)


def _sponsor(
    ein: str,
    employment: int,
    naics_code: str | None,
    *,
    state: str = "CA",
    entity_code: str = "2",
) -> dict[str, object]:
    sector = naics_code[:2] if naics_code is not None else pd.NA
    return {
        "sponsor_ein": ein,
        "active_participants_eoy": employment,
        "naics_code": naics_code if naics_code is not None else pd.NA,
        "naics_sector": sector,
        "state": state,
        "plan_entity_code": entity_code,
        "plan_entity_code_system": "form_5500_type_plan_entity_cd",
        "plan_entity_type": "single_employer",
        "plan_entity_strata": f"form_5500_type_plan_entity_cd:{entity_code}",
        "plan_entity_types": "single_employer",
        "plan_entity_code_conflict": False,
        "plan_entity_type_conflict": False,
        "naics_codes": naics_code if naics_code is not None else pd.NA,
        "naics_code_conflict": False,
        "source_form": "5500",
        "source_forms": "5500",
        "source_year": 2023,
        "source_filename": "synthetic_form_5500.csv",
        "filings": 1,
        "observation_unit": "plan_sponsor_ein",
        "employment_measure": "active_plan_participants",
        "participant_timing": "end_of_year",
        "employment_measure_source_field": "TOT_ACTIVE_PARTCP_CNT",
        "employment_is_lower_bound": False,
        "active_participants_boy": pd.NA,
        "total_participants_boy": employment,
    }


def _sponsors() -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            _sponsor("000000001", 1, "321111"),
            _sponsor("000000002", 9, "331110"),
            _sponsor("000000003", 10, "451110"),
            _sponsor("000000004", 40, "452210"),
            _sponsor("000000005", 5, "551114"),
            _sponsor("000000006", 8, "551112"),
            _sponsor("000000007", 500, "111110"),
            _sponsor("000000008", 800, "111120"),
            _sponsor("000000009", 20, None),
            _sponsor("000000010", 100, "921110"),
        ]
    )
    frame.attrs["aggregation"] = {
        "deduplication_rule": "synthetic coherent maximum",
        "single_employer_filter_applied": False,
    }
    frame.attrs["measurement_model"] = {
        "observation_unit": "plan_sponsor_ein",
        "participant_timing": "end_of_year",
        "employment_proxy_relation": "not_ordered_across_plan_entity_strata",
    }
    return frame


def _source_receipt(sponsors: pd.DataFrame):
    return synthetic_us_firm_source_receipt(
        sponsors,
        fixture_name="test_us_firm_frame.synthetic_sponsors.v1",
    )


def _targets(*, add_uncovered: bool = False) -> USFirmTargets:
    rows = [
        {
            "calibration_sector": "31-33",
            "calibration_band": "LT10",
            "firms": 4,
            "employment": 20,
            "employment_in_scope": True,
        },
        {
            "calibration_sector": "44-45",
            "calibration_band": "B10_49",
            "firms": 4,
            "employment": 100,
            "employment_in_scope": True,
        },
        {
            "calibration_sector": "55",
            "calibration_band": "LT10",
            "firms": 10,
            "employment": 50,
            "employment_in_scope": False,
        },
        {
            "calibration_sector": "11",
            "calibration_band": "B500_PLUS",
            "firms": 2,
            "employment": 600,
            "employment_in_scope": True,
        },
    ]
    if add_uncovered:
        rows.append(
            {
                "calibration_sector": "62",
                "calibration_band": "B50_99",
                "firms": 3,
                "employment": 210,
                "employment_in_scope": True,
            }
        )
    detail = pd.DataFrame(
        [
            {
                "calibration_sector": "31-33",
                "calibration_band": "LT10",
                "entrsize_code": "02",
                "employment_lower_bound": 1,
                "employment_upper_bound": 9,
                "firms": 4,
                "employment": 20,
            },
            {
                "calibration_sector": "44-45",
                "calibration_band": "B10_49",
                "entrsize_code": "04",
                "employment_lower_bound": 10,
                "employment_upper_bound": 49,
                "firms": 4,
                "employment": 100,
            },
            {
                "calibration_sector": "55",
                "calibration_band": "LT10",
                "entrsize_code": "02",
                "employment_lower_bound": 1,
                "employment_upper_bound": 9,
                "firms": 10,
                "employment": 50,
            },
            {
                "calibration_sector": "11",
                "calibration_band": "B500_PLUS",
                "entrsize_code": "25",
                "employment_lower_bound": 500,
                "employment_upper_bound": pd.NA,
                "firms": 2,
                "employment": 600,
            },
        ]
    )
    return USFirmTargets(
        calibration_cells=pd.DataFrame(rows),
        detail_cells=detail,
        source_mode="synthetic_migration_fixture",
        provenance={
            "source_mode": "synthetic_migration_fixture",
            "us_total_firms": 20,
            "us_total_employment": 770,
        },
    )


def _bds() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "year": [2022, 2022, 2022],
            "calibration_band": ["LT10", "B100_499", "B500_PLUS"],
            "firms": [10, 2, 2],
            "employment": [70, 300, 600],
        }
    )
    frame.attrs.update(
        {"held_out": True, "extract_sha256": "ef" * 32}
    )
    return frame


def test_synthetic_builder_emits_conformant_raw_employment_frame() -> None:
    sponsors = _sponsors()
    result = build_us_firm_frame(
        sponsors,
        _targets(),
        source_provenance=_source_receipt(sponsors),
        bds_validation=_bds(),
    )
    firms = result.firms

    assert tuple(firms.columns) == FIRM_TABLE_COLUMNS
    assert firms["firm_id"].tolist() == list(range(1, 9))
    assert firms["source_firm_id"].tolist() == [
        f"{value:09d}" for value in range(1, 9)
    ]
    assert "calibration_band" not in firms
    assert firms["employment"].tolist() == [1, 9, 10, 40, 5, 8, 500, 800]
    assert set(firms.loc[firms["naics_sector"].isin(["32", "33"]), "calibration_sector"]) == {
        "31-33"
    }
    assert set(firms.loc[firms["naics_sector"].isin(["45"]), "calibration_sector"]) == {
        "44-45"
    }
    assert firms.loc[firms["calibration_sector"].eq("55"), "employment_in_scope"].eq(False).all()
    assert firms.loc[firms["calibration_sector"].eq("11"), "employment_in_scope"].eq(False).all()
    assert firms["source_manifest_sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert firms["firm_weight"].between(0.1, 140.0).all()

    coverage = result.coverage.set_index(
        ["calibration_sector", "calibration_band"]
    )
    assert coverage.loc[("31-33", "LT10"), "estimated_firms"] == pytest.approx(4)
    assert coverage.loc[("31-33", "LT10"), "estimated_employment"] == pytest.approx(20)
    assert coverage.loc[("44-45", "B10_49"), "estimated_employment"] == pytest.approx(100)
    assert coverage.loc[("55", "LT10"), "calibration_status"] == (
        "firm_only_declared_employment_exclusion"
    )
    assert coverage.loc[("11", "B500_PLUS"), "calibration_status"] == (
        "firm_only_infeasible_employment_support"
    )
    assert result.diagnostics["filters"] == {
        "source_sponsors": 10,
        "missing_or_invalid_full_naics_dropped": 1,
        "unmatched_susb_calibration_cell_dropped": 1,
        "firm_rows_out": 8,
    }
    assert result.diagnostics["unmatched_donor_cells_dropped"] == [
        {
            "calibration_sector": "92",
            "calibration_band": "B100_499",
            "observed_records": 1,
            "observed_employment_sum": 100,
        }
    ]
    assert result.diagnostics["source_provenance"]["status"] == (
        "synthetic_fixture"
    )
    assert result.diagnostics["margins"]["employment_in_scope"][
        "ratio"
    ] == pytest.approx(1.0)
    assert len(result.diagnostics["coverage_table"]) == 4
    assert len(result.diagnostics["recorded_attempts"]) == 2
    assert result.diagnostics["bds_national_heldout"]["status"] == "computed"
    holdout = result.diagnostics["bds_national_heldout"]["cells"]
    lt10 = next(row for row in holdout if row["calibration_band"] == "LT10")
    assert lt10["susb_firms"] == 14
    assert lt10["frame_to_susb_firm_ratio"] == pytest.approx(1.0)
    assert result.diagnostics["weight_distribution"][
        "effective_sample_size"
    ] > 0
    cell_weight = result.diagnostics["coverage_table"][0]["weight_diagnostics"]
    assert "maximum_firm_margin_leverage" in cell_weight
    assert "maximum_employment_margin_leverage" in cell_weight


def test_builder_fails_with_complete_zero_support_table() -> None:
    sponsors = _sponsors()
    with pytest.raises(USFirmCoverageError) as captured:
        build_us_firm_frame(
            sponsors,
            _targets(add_uncovered=True),
            source_provenance=_source_receipt(sponsors),
        )

    coverage = captured.value.coverage
    assert len(coverage) == 5
    missing = coverage[coverage["observed_records"].eq(0)]
    assert missing[["calibration_sector", "calibration_band"]].to_dict(
        "records"
    ) == [{"calibration_sector": "62", "calibration_band": "B50_99"}]


def test_builder_reports_bound_residual_instead_of_breaking_bound() -> None:
    sponsors = pd.DataFrame(
        [
            _sponsor("000000001", 1, "521110"),
            _sponsor("000000002", 9, "521110"),
        ]
    )
    sponsors.attrs.update(_sponsors().attrs)
    targets = USFirmTargets(
        calibration_cells=pd.DataFrame(
            [
                {
                    "calibration_sector": "52",
                    "calibration_band": "LT10",
                    "firms": 1_000,
                    "employment": 5_000,
                    "employment_in_scope": True,
                }
            ]
        ),
        detail_cells=None,
        source_mode="synthetic_ledger_fixture",
        provenance={"source_mode": "synthetic_ledger_fixture"},
    )
    result = build_us_firm_frame(
        sponsors,
        targets,
        source_provenance=_source_receipt(sponsors),
    )

    assert result.firms["firm_weight"].tolist() == [140.0, 140.0]
    cell = result.coverage.iloc[0]
    assert cell["calibration_status"] == "dual_margin_bounded_residual"
    assert cell["estimated_firms"] == 280.0
    assert cell["firm_margin_ratio"] == pytest.approx(0.28)
    assert cell["weight_diagnostics"]["upper_bound_hits"] == 2
    assert "absolute weight bounds bind" in cell["calibration_reason"]


def test_builder_refuses_unverified_or_stale_source_receipts() -> None:
    sponsors = _sponsors()
    with pytest.raises(TypeError, match="VerifiedUSFirmStaging"):
        build_us_firm_frame(
            sponsors,
            _targets(),
            source_provenance={"manifest_sha256": "ab" * 32},  # type: ignore[arg-type]
        )

    receipt = _source_receipt(sponsors)
    changed = sponsors.copy()
    changed.loc[0, "active_participants_eoy"] = 2
    with pytest.raises(ValueError, match="does not match donor content"):
        build_us_firm_frame(
            changed,
            _targets(),
            source_provenance=receipt,
        )


def test_builder_refuses_contradictory_reader_metadata_and_bds() -> None:
    with pytest.raises(ValueError, match="attested implementation identity"):
        USFirmBuildConfig(calibration_method="caller_supplied_label")

    contradictory = _sponsors()
    contradictory.loc[0, "naics_sector"] = "99"
    with pytest.raises(ValueError, match="must match full naics_code"):
        build_us_firm_frame(
            contradictory,
            _targets(),
            source_provenance=_source_receipt(contradictory),
        )

    sponsors = _sponsors()
    unproven_bds = _bds()
    unproven_bds.attrs.clear()
    with pytest.raises(ValueError, match="held_out=True"):
        build_us_firm_frame(
            sponsors,
            _targets(),
            source_provenance=_source_receipt(sponsors),
            bds_validation=unproven_bds,
        )


def test_osha_reference_requires_cap_and_preserves_measurement_warning() -> None:
    raw = pd.DataFrame(
        {
            "record_id": ["r1", "r2", "r3"],
            "establishment_id": ["e1", "e2", "e3"],
            "ein": ["000000001", "000000002", "000000002"],
            "annual_average_employees": [1, 4, 5],
            "bandable": [True, True, True],
            "hours_implausible": [False, False, False],
        }
    )
    with pytest.raises(ValueError, match="explicit cap"):
        osha_measurement_reference(_sponsors(), raw)

    cleaned = apply_quality_rule(raw, max_employees=100)
    receipt = osha_measurement_reference(_sponsors(), cleaned)
    assert receipt["matched_eins"] == 2
    assert receipt["agreement_rate"] == pytest.approx(1.0)
    assert receipt["osha_quality_rule"]["max_employees"] == 100
    assert receipt["osha_aggregation"]["rows_aggregated"] == 3
    assert receipt["osha_aggregation"]["repeated_establishment_ids"] == 0
    assert receipt["osha_aggregation"]["deduplication_applied"] is False
    assert "does not reconcile" in receipt["measurement_warning"]


def test_builder_and_artifact_are_deterministic_and_hash_bound(
    tmp_path: Path,
) -> None:
    sponsors = _sponsors()
    first = build_us_firm_frame(
        sponsors,
        _targets(),
        source_provenance=_source_receipt(sponsors),
        bds_validation=_bds(),
    )
    reversed_sponsors = _sponsors().iloc[::-1].copy()
    reversed_targets = _targets()
    reversed_targets = USFirmTargets(
        calibration_cells=reversed_targets.calibration_cells.iloc[::-1].copy(),
        detail_cells=reversed_targets.detail_cells.iloc[::-1].copy(),
        source_mode=reversed_targets.source_mode,
        provenance=reversed_targets.provenance,
    )
    second = build_us_firm_frame(
        reversed_sponsors,
        reversed_targets,
        source_provenance=_source_receipt(reversed_sponsors),
        bds_validation=_bds().iloc[::-1].copy(),
    )
    pd.testing.assert_frame_equal(first.firms, second.firms)
    assert first.diagnostics["build_identity_sha256"] == second.diagnostics[
        "build_identity_sha256"
    ]

    first_paths = write_us_firm_artifact(first, tmp_path / "first")
    second_paths = write_us_firm_artifact(second, tmp_path / "second")
    for name in ("firms.parquet", "diagnostics.json", "manifest.json"):
        left = first_paths.directory / name
        right = second_paths.directory / name
        assert hashlib.sha256(left.read_bytes()).digest() == hashlib.sha256(
            right.read_bytes()
        ).digest()
    receipt = verify_us_firm_artifact(first_paths.directory)
    assert receipt["rows"] == 8
    assert receipt["manifest_sha256"] == first_paths.manifest_sha256

    first_paths.diagnostics.write_text("{}\n")
    with pytest.raises(ValueError, match="diagnostics.json SHA-256"):
        verify_us_firm_artifact(first_paths.directory)


def test_artifact_failure_leaves_destination_absent(tmp_path: Path) -> None:
    sponsors = _sponsors()
    result = build_us_firm_frame(
        sponsors,
        _targets(),
        source_provenance=_source_receipt(sponsors),
    )
    invalid = USFirmBuildResult(
        firms=result.firms,
        coverage=result.coverage,
        diagnostics={"not_json": float("nan")},
        config=result.config,
    )
    destination = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="Out of range float"):
        write_us_firm_artifact(invalid, destination)
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_artifact_refuses_invalid_firm_schema_and_added_entries(
    tmp_path: Path,
) -> None:
    sponsors = _sponsors()
    result = build_us_firm_frame(
        sponsors,
        _targets(),
        source_provenance=_source_receipt(sponsors),
    )
    invalid_firms = result.firms.copy()
    invalid_firms.loc[0, "naics_code"] = "32"
    invalid = USFirmBuildResult(
        firms=invalid_firms,
        coverage=result.coverage,
        diagnostics=result.diagnostics,
        config=result.config,
    )
    destination = tmp_path / "invalid"
    with pytest.raises(ValueError, match="six-digit"):
        write_us_firm_artifact(invalid, destination)
    assert not destination.exists()

    paths = write_us_firm_artifact(result, tmp_path / "valid")
    (paths.directory / "unexpected").mkdir()
    with pytest.raises(ValueError, match="file set changed"):
        verify_us_firm_artifact(paths.directory)


_REAL_DATA = firm_data_dir()
_HAS_REAL_BUILD = all(
    path.exists()
    for path in (
        _REAL_DATA / "source_manifest.json",
        _REAL_DATA / "f_5500_2023_latest.csv",
        _REAL_DATA / "f_5500_sf_2023_latest.csv",
        _REAL_DATA / "ITA_300A_Summary_Data_2025.csv",
    )
)


@pytest.mark.skipif(not _HAS_REAL_BUILD, reason="US firm sources not staged")
@pytest.mark.slow
def test_real_frame_build_rehashes_sources_and_pins_computed_evidence() -> None:
    staged = verify_staged_sources(_REAL_DATA)
    sponsors = read_sponsors(2023, _REAL_DATA)
    raw_osha = read_ita(2025, _REAL_DATA)
    cleaned_osha = apply_quality_rule(raw_osha, max_employees=613_000)
    osha_receipt = osha_measurement_reference(sponsors, cleaned_osha)
    result = build_us_firm_frame(
        sponsors,
        load_susb_migration_harness(),
        source_provenance=staged,
        bds_validation=load_bds_validation_harness(),
        osha_reference=osha_receipt,
    )

    assert len(result.coverage) == 97
    assert result.coverage["observed_records"].min() >= 10
    assert result.firms["firm_weight"].between(0.1, 140.0).all()
    assert result.diagnostics["legacy_claim_comparison"][
        "positive_susb_cells_97"
    ]["target_geometry_reproduced"]
    assert result.diagnostics["osha_independent_measurement_reference"][
        "matched_eins"
    ] > 0
    # The corrected EOY/crosswalk/scope build records the empirical values in
    # the hash-bound diagnostics; legacy numbers are not copied into assertions
    # until a staged run actually reproduces them.
    json.dumps(result.diagnostics, allow_nan=False)
