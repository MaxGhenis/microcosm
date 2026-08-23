from __future__ import annotations

from pathlib import Path

import pytest

from microcosm.build.us_runtime.us_firms import targets as target_module
from microcosm.build.us_runtime.us_firms.targets import (
    BDS_EXTRACT_SHA256,
    CALIBRATION_BANDS,
    CALIBRATION_TARGET_COLUMNS,
    SUSB_EXTRACT_SHA256,
    TARGET_PROVENANCE_SHA256,
    USFirmLedgerTargetProfile,
    calibration_band_for_employment,
    calibration_sector_for_naics,
    load_bds_validation_harness,
    load_susb_migration_harness,
    us_firm_targets_from_ledger_facts,
)


def test_private_calibration_geometry_has_explicit_edges_and_crosswalk() -> None:
    assert [
        calibration_band_for_employment(value)
        for value in (1, 9, 10, 49, 50, 99, 100, 499, 500)
    ] == [
        "LT10",
        "LT10",
        "B10_49",
        "B10_49",
        "B50_99",
        "B50_99",
        "B100_499",
        "B100_499",
        "B500_PLUS",
    ]
    assert calibration_sector_for_naics("311111") == "31-33"
    assert calibration_sector_for_naics("32") == "31-33"
    assert calibration_sector_for_naics("33") == "31-33"
    assert calibration_sector_for_naics("441110") == "44-45"
    assert calibration_sector_for_naics("45") == "44-45"
    assert calibration_sector_for_naics("481111") == "48-49"
    assert calibration_sector_for_naics("49") == "48-49"
    assert calibration_sector_for_naics("541110") == "54"
    assert calibration_sector_for_naics("31-33") == "31-33"

    for invalid in (0, -1, 1.5, float("nan"), True, "unknown"):
        with pytest.raises(ValueError):
            calibration_band_for_employment(invalid)
    with pytest.raises(ValueError, match="valid sector"):
        calibration_sector_for_naics("--")


def test_susb_migration_harness_reproduces_pinned_97_cell_geometry() -> None:
    targets = load_susb_migration_harness()
    cells = targets.calibration_cells

    assert targets.source_mode == "migration_harness"
    assert targets.provenance["extract_sha256"] == SUSB_EXTRACT_SHA256
    assert targets.provenance["production_target_authority"] == (
        "ledger_consumer_facts"
    )
    assert list(cells.columns) == list(CALIBRATION_TARGET_COLUMNS)
    assert len(cells) == 97
    assert int(cells["firms"].sum()) == 6_461_497
    assert int(cells["employment"].sum()) == 135_748_407
    assert int(cells.loc[cells["employment_in_scope"], "employment"].sum()) == (
        132_086_430
    )
    assert set(cells.loc[~cells["employment_in_scope"], "calibration_sector"]) == {"55"}
    assert set(cells["calibration_sector"]) >= {"31-33", "44-45", "48-49"}
    assert not set(cells["calibration_sector"]) & {"31", "32", "33", "44", "45"}

    sector_99 = cells[cells["calibration_sector"] == "99"]
    assert sector_99["calibration_band"].tolist() == ["LT10", "B10_49"]


def test_susb_migration_harness_retains_fine_detail_for_diagnostics() -> None:
    targets = load_susb_migration_harness()
    detail = targets.detail_cells

    assert detail is not None
    assert len(detail) == 446
    assert {
        "entrsize_code",
        "entrsize_label",
        "employment_lower_bound",
        "employment_upper_bound",
        "employment_noise_flag",
    } <= set(detail.columns)
    open_ended = detail[detail["entrsize_code"] == "25"]
    assert open_ended["employment_upper_bound"].isna().all()
    assert set(open_ended["calibration_band"]) == {"B500_PLUS"}


def test_susb_migration_harness_refuses_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = tmp_path / "susb.csv"
    changed.write_bytes(target_module.SUSB_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(target_module, "SUSB_PATH", changed)

    with pytest.raises(ValueError, match="hash mismatch"):
        load_susb_migration_harness()


def test_susb_migration_harness_refuses_provenance_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = tmp_path / "target_provenance.json"
    changed.write_bytes(target_module.TARGET_PROVENANCE_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(target_module, "TARGET_PROVENANCE_PATH", changed)

    assert TARGET_PROVENANCE_SHA256 == (
        "262e2194c1b9e7f0acf02964febf2a7beffacf29c16791cda2ddd31932eaf46b"
    )
    with pytest.raises(ValueError, match="hash mismatch"):
        load_susb_migration_harness()


def test_bds_validation_harness_exposes_only_complete_exact_bands() -> None:
    targets = load_bds_validation_harness()

    assert targets["calibration_band"].tolist() == [
        "LT10",
        "B100_499",
        "B500_PLUS",
    ]
    assert targets["firms"].tolist() == [4_302_222, 89_541, 23_240]
    assert targets["employment"].tolist() == [14_307_542, 18_085_296, 70_851_104]
    assert targets.attrs["extract_sha256"] == BDS_EXTRACT_SHA256
    assert targets.attrs["held_out"] is True
    assert targets.attrs["excluded_inexact_categories"] == [
        "c) 10 to 19",
        "d) 20 to 99",
    ]


def test_ledger_target_adapter_requires_explicit_complete_profile() -> None:
    with pytest.raises(ValueError, match="does not cover"):
        USFirmLedgerTargetProfile(
            firm_count_record_set_id="test.susb.firms",
            employment_record_set_id="test.susb.employment",
            firm_count_measure_id="firms",
            employment_measure_id="employment",
            sector_dimension_id="test.naics_sector",
            size_dimension_id="test.enterprise_size",
            size_value_to_calibration_band={"small": "LT10"},
        )

    with pytest.raises(TypeError, match="USFirmLedgerTargetProfile"):
        us_firm_targets_from_ledger_facts([], target_profile={})  # type: ignore[arg-type]


def test_ledger_target_adapter_validates_and_materializes_consumer_facts() -> None:
    profile = _ledger_profile()
    targets = us_firm_targets_from_ledger_facts(
        _ledger_facts(sectors=("31", "55")),
        target_profile=profile,
    )
    cells = targets.calibration_cells

    assert targets.source_mode == "ledger_consumer_facts"
    assert targets.detail_cells is None
    assert list(cells.columns) == list(CALIBRATION_TARGET_COLUMNS)
    assert len(cells) == 10
    assert set(cells["calibration_sector"]) == {"31-33", "55"}
    assert set(cells["calibration_band"]) == set(CALIBRATION_BANDS)
    assert (
        cells.loc[cells["calibration_sector"] == "55", "employment_in_scope"]
        .eq(False)
        .all()
    )
    assert targets.provenance["firm_count_record_set_id"] == "test.susb.firms"
    assert targets.provenance["target_periods"] == [
        {"type": "calendar_year", "value": 2022}
    ]
    identities = targets.provenance["cell_fact_identities"]
    assert len(identities) == 10
    assert identities[0] == {
        "calibration_sector": "31-33",
        "calibration_band": "LT10",
        "firm_count_aggregate_fact_keys": [
            "arch.aggregate_fact.v2:test.susb.firms:31:LT10"
        ],
        "employment_aggregate_fact_keys": [
            "arch.aggregate_fact.v2:test.susb.employment:31:LT10"
        ],
        "period": {"type": "calendar_year", "value": 2022},
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("entity", "expected 'firm'"),
        ("aggregation", "expected 'sum'"),
        ("dimension", "must carry dimensions"),
        ("duplicate", "Duplicate Ledger"),
        ("missing_measure", "do not cover the same source cells"),
        ("incomplete_grid", "omit calibration cell"),
        ("negative", "invalid non-negative value"),
        ("missing_key", "missing aggregate_fact_key"),
        ("period", "different periods"),
    ],
)
def test_ledger_target_adapter_fails_closed(
    mutation: str,
    message: str,
) -> None:
    facts = _ledger_facts(sectors=("31",))
    if mutation == "entity":
        facts[0]["entity"]["name"] = "person"
    elif mutation == "aggregation":
        facts[0]["aggregation"]["method"] = "mean"
    elif mutation == "dimension":
        del facts[0]["dimensions"]["test.naics_sector"]
    elif mutation == "duplicate":
        facts.append(facts[0].copy())
    elif mutation == "missing_measure":
        facts.pop()
    elif mutation == "incomplete_grid":
        facts = [
            fact
            for fact in facts
            if fact["dimensions"]["test.enterprise_size"] != "B500_PLUS"
        ]
    elif mutation == "negative":
        facts[0]["value"] = -1
    elif mutation == "missing_key":
        del facts[0]["aggregate_fact_key"]
    elif mutation == "period":
        facts[1]["period"] = {"type": "calendar_year", "value": 2023}
    else:  # pragma: no cover - parametrization is exhaustive
        raise AssertionError(mutation)

    with pytest.raises(ValueError, match=message):
        us_firm_targets_from_ledger_facts(
            facts,
            target_profile=_ledger_profile(),
        )


def test_ledger_target_adapter_aggregates_symmetric_composite_sectors() -> None:
    targets = us_firm_targets_from_ledger_facts(
        _ledger_facts(sectors=("31", "32", "33")),
        target_profile=_ledger_profile(),
    )
    cells = targets.calibration_cells

    assert len(cells) == 5
    assert set(cells["calibration_sector"]) == {"31-33"}
    assert cells["firms"].tolist() == [3.0, 6.0, 9.0, 12.0, 15.0]


def _ledger_profile() -> USFirmLedgerTargetProfile:
    return USFirmLedgerTargetProfile(
        firm_count_record_set_id="test.susb.firms",
        employment_record_set_id="test.susb.employment",
        firm_count_measure_id="firms",
        employment_measure_id="employment",
        sector_dimension_id="test.naics_sector",
        size_dimension_id="test.enterprise_size",
        size_value_to_calibration_band={band: band for band in CALIBRATION_BANDS},
    )


def _ledger_facts(*, sectors: tuple[str, ...]) -> list[dict[str, object]]:
    facts: list[dict[str, object]] = []
    for sector in sectors:
        for index, band in enumerate(CALIBRATION_BANDS, start=1):
            facts.append(
                _ledger_fact(
                    record_set_id="test.susb.firms",
                    measure_id="firms",
                    sector=sector,
                    band=band,
                    value=index,
                )
            )
            facts.append(
                _ledger_fact(
                    record_set_id="test.susb.employment",
                    measure_id="employment",
                    sector=sector,
                    band=band,
                    value=index * 10,
                )
            )
    return facts


def _ledger_fact(
    *,
    record_set_id: str,
    measure_id: str,
    sector: str,
    band: str,
    value: float,
) -> dict[str, object]:
    return {
        "aggregate_fact_key": (
            f"arch.aggregate_fact.v2:{record_set_id}:{sector}:{band}"
        ),
        "layout": {
            "record_set_id": record_set_id,
            "measure_id": measure_id,
        },
        "entity": {"name": "firm"},
        "aggregation": {"method": "sum"},
        "period": {"type": "calendar_year", "value": 2022},
        "dimensions": {
            "test.naics_sector": sector,
            "test.enterprise_size": band,
        },
        "value": value,
    }
