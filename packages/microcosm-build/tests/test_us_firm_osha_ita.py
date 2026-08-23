"""Focused tests for the OSHA ITA independent-reference reader."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from microcosm.build.us_runtime.us_firms import osha_ita


def _write_ita(directory: Path, year: int, rows: list[dict]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    defaults = {
        "ID": "record-1",
        "establishment_ID": "establishment-1",
        "ein": "123456789",
        "company_name": "ACME CORP",
        "establishment_name": "ACME PLANT 1",
        "state": "OH",
        "naics_code": "332999",
        "naics_year": 2022,
        "annual_average_employees": 120,
        "establishment_type": "1",
        "year_filing_for": year,
    }
    records = []
    for index, row in enumerate(rows):
        record = {**defaults, "ID": f"record-{index + 1}", **row}
        record.setdefault(
            "total_hours_worked",
            float(record["annual_average_employees"]) * 2_000,
        )
        records.append(record)
    path = directory / f"ITA_300A_Summary_Data_{year}.csv"
    pd.DataFrame(records).to_csv(path, index=False)
    return path


def test_missing_file_names_microcosm_staging_variable(tmp_path):
    with pytest.raises(
        FileNotFoundError, match="MICROCOSM_US_FIRM_DATA_DIR"
    ):
        osha_ita.read_ita(2025, tmp_path)


def test_missing_source_column_fails_loudly(tmp_path):
    pd.DataFrame([{"ein": "1"}]).to_csv(
        tmp_path / "ITA_300A_Summary_Data_2025.csv", index=False
    )
    with pytest.raises(ValueError, match="missing columns"):
        osha_ita.read_ita(2025, tmp_path)


def test_reader_preserves_source_ids_ownership_and_full_naics(tmp_path):
    _write_ita(
        tmp_path,
        2025,
        [
            {
                "ID": "submission-42",
                "establishment_ID": "site-17",
                "ein": "12-3456789",
                "naics_code": "622110",
                "naics_year": 2022,
                "establishment_type": "2",
            }
        ],
    )
    row = osha_ita.read_ita(2025, tmp_path).iloc[0]
    assert row["record_id"] == "submission-42"
    assert row["establishment_id"] == "site-17"
    assert row["ein"] == "123456789"
    assert row["naics_code"] == "622110"
    assert row["naics_sector"] == "62"
    assert row["naics_year"] == 2022
    assert row["establishment_type"] == "2"
    assert row["ownership"] == "state_government"


def test_short_or_punctuated_naics_is_not_fabricated(tmp_path):
    _write_ita(
        tmp_path,
        2025,
        [
            {"naics_code": "6221"},
            {"naics_code": "62-2110"},
        ],
    )
    out = osha_ita.read_ita(2025, tmp_path)
    assert out["naics_code"].isna().all()
    assert out["naics_sector"].isna().all()


def test_requested_year_must_match_every_source_row(tmp_path):
    _write_ita(tmp_path, 2025, [{"year_filing_for": 2024}])
    with pytest.raises(ValueError, match="requested for 2025"):
        osha_ita.read_ita(2025, tmp_path)


def test_missing_or_fractional_source_year_is_rejected(tmp_path):
    _write_ita(tmp_path, 2025, [{"year_filing_for": 2024.5}])
    with pytest.raises(ValueError, match="missing or non-integral"):
        osha_ita.read_ita(2025, tmp_path)


def test_read_applies_no_cap_filter_or_band(tmp_path):
    _write_ita(
        tmp_path,
        2025,
        [{"annual_average_employees": 120_000_000, "total_hours_worked": 10}],
    )
    out = osha_ita.read_ita(2025, tmp_path)
    assert len(out) == 1
    assert out.loc[0, "annual_average_employees"] == 120_000_000
    assert "canonical_band" not in out
    assert out.attrs["measurement_model"]["cleaning_applied"] is False
    assert (
        out.attrs["measurement_model"]["frame_role"]
        == "independent_measurement_reference"
    )


def test_hours_flag_has_an_inclusive_physical_boundary(tmp_path):
    _write_ita(
        tmp_path,
        2025,
        [
            {"annual_average_employees": 10, "total_hours_worked": 87_600},
            {"annual_average_employees": 10, "total_hours_worked": 87_610},
        ],
    )
    out = osha_ita.read_ita(2025, tmp_path)
    assert list(out["hours_implausible"]) == [False, True]


def test_fractional_and_zero_employment_are_flagged_not_removed(tmp_path):
    _write_ita(
        tmp_path,
        2025,
        [
            {"annual_average_employees": 0},
            {"annual_average_employees": 3.5},
            {"annual_average_employees": 4},
        ],
    )
    out = osha_ita.read_ita(2025, tmp_path)
    assert len(out) == 3
    assert list(out["bandable"]) == [False, False, True]


def test_quality_rule_requires_an_explicit_integer_cap(tmp_path):
    _write_ita(tmp_path, 2025, [{}])
    out = osha_ita.read_ita(2025, tmp_path)
    with pytest.raises(TypeError):
        osha_ita.apply_quality_rule(out)
    for cap in (0, 100.5, True):
        with pytest.raises(ValueError, match="integer >= 1"):
            osha_ita.apply_quality_rule(out, max_employees=cap)


def test_quality_rule_records_disjoint_removal_counts(tmp_path):
    _write_ita(
        tmp_path,
        2025,
        [
            {"annual_average_employees": 50},
            {"annual_average_employees": 0},
            {"annual_average_employees": 10, "total_hours_worked": 900_000},
            {"annual_average_employees": 5_000_000},
        ],
    )
    raw = osha_ita.read_ita(2025, tmp_path)
    cleaned = osha_ita.apply_quality_rule(raw, max_employees=100_000)
    assert list(cleaned["annual_average_employees"]) == [50]
    assert "canonical_band" not in cleaned
    rule = cleaned.attrs["quality_rule"]
    assert rule["rows_in"] == 4
    assert rule["rows_out"] == 1
    assert rule["dropped_unbandable"] == 1
    assert rule["dropped_hours_implausible"] == 1
    assert rule["dropped_above_max_employees"] == 1
    assert rule["employment_out"] == 50.0
    assert rule["banding_applied"] is False


def test_quality_rule_can_retain_hours_implausible_rows(tmp_path):
    _write_ita(
        tmp_path,
        2025,
        [{"annual_average_employees": 10, "total_hours_worked": 900_000}],
    )
    raw = osha_ita.read_ita(2025, tmp_path)
    kept = osha_ita.apply_quality_rule(
        raw,
        max_employees=100_000,
        drop_hours_implausible=False,
    )
    assert len(kept) == 1
    assert kept.attrs["quality_rule"]["dropped_hours_implausible"] == 0


def test_quality_rule_rejects_unannotated_input():
    with pytest.raises(ValueError, match="pass the output of read_ita"):
        osha_ita.apply_quality_rule(
            pd.DataFrame({"annual_average_employees": [10]}),
            max_employees=1_000,
        )


_REAL_DATA = osha_ita.firm_data_dir()
_HAS_REAL_ITA = (
    _REAL_DATA / "ITA_300A_Summary_Data_2025.csv"
).exists()


@pytest.mark.skipif(not _HAS_REAL_ITA, reason="OSHA ITA file not staged")
def test_real_2025_source_totals_are_pinned():
    out = osha_ita.read_ita(2025, _REAL_DATA)
    assert len(out) == 383_283
    assert int(out["annual_average_employees"].sum()) == 321_889_014
    assert int(out["hours_implausible"].sum()) == 1_996
