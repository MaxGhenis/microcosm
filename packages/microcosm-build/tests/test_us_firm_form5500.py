"""Focused tests for the US Form 5500 source readers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from microcosm.build.us_runtime.us_firms import form5500


def _write_main(directory: Path, year: int, rows: list[dict]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    defaults = {
        "SPONS_DFE_EIN": "123456789",
        "BUSINESS_CODE": "541990",
        "SPONS_DFE_LOC_US_STATE": "CA",
        "TYPE_PLAN_ENTITY_CD": "2",
        "TOT_PARTCP_BOY_CNT": 120,
        "TOT_ACTIVE_PARTCP_CNT": 100,
    }
    path = directory / f"f_5500_{year}_latest.csv"
    pd.DataFrame([{**defaults, **row} for row in rows]).to_csv(
        path, index=False
    )
    return path


def _write_sf(directory: Path, year: int, rows: list[dict]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    defaults = {
        "SF_SPONS_EIN": "987654321",
        "SF_BUSINESS_CODE": "722511",
        "SF_SPONS_US_STATE": "TX",
        "SF_TYPE_PLAN_ENTITY_CD": "1",
        "SF_TOT_ACT_PARTCP_BOY_CNT": 8,
        "SF_TOT_ACT_PARTCP_EOY_CNT": 9,
    }
    path = directory / f"f_5500_sf_{year}_latest.csv"
    pd.DataFrame([{**defaults, **row} for row in rows]).to_csv(
        path, index=False
    )
    return path


def test_missing_file_names_microcosm_staging_variable(tmp_path):
    with pytest.raises(
        FileNotFoundError, match="MICROCOSM_US_FIRM_DATA_DIR"
    ):
        form5500.read_main_filings(2023, tmp_path)


def test_missing_source_column_fails_loudly(tmp_path):
    pd.DataFrame([{"SPONS_DFE_EIN": "1"}]).to_csv(
        tmp_path / "f_5500_2023_latest.csv", index=False
    )
    with pytest.raises(ValueError, match="missing columns"):
        form5500.read_main_filings(2023, tmp_path)


def test_sf_uses_eoy_and_retains_boy_measure(tmp_path):
    _write_sf(
        tmp_path,
        2023,
        [
            {
                "SF_TOT_ACT_PARTCP_BOY_CNT": 98,
                "SF_TOT_ACT_PARTCP_EOY_CNT": 12,
            }
        ],
    )
    out = form5500.read_sf_filings(2023, tmp_path)
    assert out.loc[0, "active_participants_boy"] == 98
    assert out.loc[0, "active_participants_eoy"] == 12
    assert out.loc[0, "participant_timing"] == "end_of_year"
    assert (
        out.loc[0, "employment_measure_source_field"]
        == "SF_TOT_ACT_PARTCP_EOY_CNT"
    )


def test_main_retains_total_boy_separately_from_active_eoy(tmp_path):
    _write_main(
        tmp_path,
        2023,
        [{"TOT_PARTCP_BOY_CNT": 140, "TOT_ACTIVE_PARTCP_CNT": 101}],
    )
    out = form5500.read_main_filings(2023, tmp_path)
    assert out.loc[0, "total_participants_boy"] == 140
    assert pd.isna(out.loc[0, "active_participants_boy"])
    assert out.loc[0, "active_participants_eoy"] == 101


def test_form_specific_entity_code_systems_are_not_conflated(tmp_path):
    _write_main(
        tmp_path,
        2023,
        [{"SPONS_DFE_EIN": "111111111", "TYPE_PLAN_ENTITY_CD": "1"}],
    )
    _write_sf(
        tmp_path,
        2023,
        [{"SF_SPONS_EIN": "222222222", "SF_TYPE_PLAN_ENTITY_CD": "1"}],
    )
    out = form5500.read_sponsors(2023, tmp_path)
    indexed = out.set_index("sponsor_ein")
    assert indexed.loc["111111111", "plan_entity_type"] == "multiemployer"
    assert indexed.loc["222222222", "plan_entity_type"] == "single_employer"
    assert (
        indexed.loc["111111111", "plan_entity_code_system"]
        == "form_5500_type_plan_entity_cd"
    )
    assert (
        indexed.loc["222222222", "plan_entity_code_system"]
        == "form_5500_sf_type_plan_entity_cd"
    )


def test_sponsor_max_selects_one_coherent_filing(tmp_path):
    _write_main(
        tmp_path,
        2023,
        [
            {
                "SPONS_DFE_EIN": "111111111",
                "TOT_ACTIVE_PARTCP_CNT": 90,
                "BUSINESS_CODE": "541990",
                "SPONS_DFE_LOC_US_STATE": "CA",
                "TYPE_PLAN_ENTITY_CD": "2",
            },
            {
                "SPONS_DFE_EIN": "111111111",
                "TOT_ACTIVE_PARTCP_CNT": 80,
                "BUSINESS_CODE": "722511",
                "SPONS_DFE_LOC_US_STATE": "TX",
                "TYPE_PLAN_ENTITY_CD": "1",
            },
        ],
    )
    out = form5500.read_sponsors(2023, tmp_path, forms=("5500",))
    assert len(out) == 1
    row = out.iloc[0]
    assert row["active_participants_eoy"] == 90
    assert row["naics_code"] == "541990"
    assert row["naics_sector"] == "54"
    assert row["state"] == "CA"
    assert row["plan_entity_code"] == "2"
    assert row["filings"] == 2
    assert row["plan_entity_code_conflict"]
    assert row["plan_entity_type_conflict"]
    assert row["naics_code_conflict"]
    assert set(row["naics_codes"].split("|")) == {"541990", "722511"}


def test_sponsor_preserves_cross_form_entity_strata(tmp_path):
    _write_main(
        tmp_path,
        2023,
        [
            {
                "SPONS_DFE_EIN": "111111111",
                "TYPE_PLAN_ENTITY_CD": "1",
                "TOT_ACTIVE_PARTCP_CNT": 60,
            }
        ],
    )
    _write_sf(
        tmp_path,
        2023,
        [
            {
                "SF_SPONS_EIN": "111111111",
                "SF_TYPE_PLAN_ENTITY_CD": "1",
                "SF_TOT_ACT_PARTCP_EOY_CNT": 50,
            }
        ],
    )
    row = form5500.read_sponsors(2023, tmp_path).iloc[0]
    assert set(row["plan_entity_strata"].split("|")) == {
        "form_5500_type_plan_entity_cd:1",
        "form_5500_sf_type_plan_entity_cd:1",
    }
    assert set(row["plan_entity_types"].split("|")) == {
        "multiemployer",
        "single_employer",
    }
    assert row["source_forms"] == "5500|5500-SF"


def test_ein_and_full_naics_are_normalised_strictly(tmp_path):
    _write_main(
        tmp_path,
        2023,
        [
            {
                "SPONS_DFE_EIN": "12-3456789",
                "BUSINESS_CODE": "1234",
            },
            {
                "SPONS_DFE_EIN": "12A3456789",
                "BUSINESS_CODE": "54-1990",
            },
        ],
    )
    out = form5500.read_main_filings(2023, tmp_path)
    assert out.loc[0, "sponsor_ein"] == "123456789"
    assert pd.isna(out.loc[0, "naics_code"])
    assert pd.isna(out.loc[0, "naics_sector"])
    assert pd.isna(out.loc[1, "sponsor_ein"])
    assert pd.isna(out.loc[1, "naics_code"])


def test_equal_maximum_uses_row_order_independent_metadata_tie_break(tmp_path):
    rows = [
        {
            "SPONS_DFE_EIN": "111111111",
            "TOT_ACTIVE_PARTCP_CNT": 90,
            "BUSINESS_CODE": "722511",
            "SPONS_DFE_LOC_US_STATE": "TX",
        },
        {
            "SPONS_DFE_EIN": "111111111",
            "TOT_ACTIVE_PARTCP_CNT": 90,
            "BUSINESS_CODE": "541990",
            "SPONS_DFE_LOC_US_STATE": "CA",
        },
    ]
    forward = tmp_path / "forward"
    reverse = tmp_path / "reverse"
    _write_main(forward, 2023, rows)
    _write_main(reverse, 2023, list(reversed(rows)))
    left = form5500.read_sponsors(2023, forward, forms=("5500",)).iloc[0]
    right = form5500.read_sponsors(2023, reverse, forms=("5500",)).iloc[0]
    selected_columns = [
        "active_participants_eoy",
        "naics_code",
        "state",
        "plan_entity_code",
    ]
    assert left[selected_columns].to_dict() == right[selected_columns].to_dict()
    assert left["naics_code"] == "541990"


def test_fractional_active_counts_are_rejected_not_truncated(tmp_path):
    _write_main(
        tmp_path,
        2023,
        [{"TOT_ACTIVE_PARTCP_CNT": 49.5}],
    )
    with pytest.raises(ValueError, match="refuses to truncate people"):
        form5500.read_main_filings(2023, tmp_path)


def test_requested_forms_are_validated_before_files_are_read(tmp_path):
    with pytest.raises(ValueError, match="Unknown Form 5500 variant"):
        form5500.read_sponsors(2023, tmp_path, forms=("5500-EZ",))
    with pytest.raises(ValueError, match="must not be repeated"):
        form5500.read_sponsors(2023, tmp_path, forms=("5500", "5500"))
    with pytest.raises(ValueError, match="At least one"):
        form5500.read_sponsors(2023, tmp_path, forms=())


def test_sponsor_aggregation_drops_zero_and_records_rules(tmp_path):
    _write_main(
        tmp_path,
        2023,
        [
            {"SPONS_DFE_EIN": "111111111", "TOT_ACTIVE_PARTCP_CNT": 0},
            {"SPONS_DFE_EIN": "222222222", "TOT_ACTIVE_PARTCP_CNT": 5},
            {"SPONS_DFE_EIN": "not-an-ein", "TOT_ACTIVE_PARTCP_CNT": 7},
        ],
    )
    out = form5500.read_sponsors(2023, tmp_path, forms=("5500",))
    assert list(out["sponsor_ein"]) == ["222222222"]
    rules = out.attrs["aggregation"]
    assert rules["invalid_ein_rows_dropped"] == 1
    assert rules["sponsors_without_positive_active_participants_dropped"] == 1
    assert rules["single_employer_filter_applied"] is False
    assert "canonical_band" not in out


_REAL_DATA = form5500.firm_data_dir()
_HAS_REAL_5500 = all(
    (_REAL_DATA / name).exists()
    for name in (
        "f_5500_2023_latest.csv",
        "f_5500_sf_2023_latest.csv",
    )
)


@pytest.mark.skipif(not _HAS_REAL_5500, reason="Form 5500 files not staged")
def test_real_2023_source_row_counts_are_pinned():
    main = form5500.read_main_filings(2023, _REAL_DATA)
    short = form5500.read_sf_filings(2023, _REAL_DATA)
    assert len(main) == 231_725
    assert len(short) == 763_552
