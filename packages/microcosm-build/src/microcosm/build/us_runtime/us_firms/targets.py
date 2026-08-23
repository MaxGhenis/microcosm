"""US firm calibration targets and migration-only Census harnesses.

Production callers must supply Ledger consumer facts and an explicit
:class:`USFirmLedgerTargetProfile`. The committed SUSB and BDS extracts are
hash-pinned migration and validation harnesses; neither is a production target
fallback. The size labels in this module describe private SUSB calibration
cells only. They do not port or replace dynamics' canonical IC2 bander.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pandas as pd

__all__ = [
    "BDS_EXTRACT_SHA256",
    "CALIBRATION_BANDS",
    "CALIBRATION_TARGET_COLUMNS",
    "SUSB_DETAIL_SIZE_INTERVALS",
    "SUSB_DETAIL_SIZE_TO_CALIBRATION_BAND",
    "SUSB_EXTRACT_SHA256",
    "TARGET_PROVENANCE_SHA256",
    "USFirmLedgerTargetProfile",
    "USFirmTargets",
    "calibration_band_for_employment",
    "calibration_sector_for_naics",
    "load_bds_validation_harness",
    "load_susb_migration_harness",
    "us_firm_targets_from_ledger_facts",
]

TARGET_DATA_DIR = Path(__file__).with_name("target_data")
SUSB_PATH = TARGET_DATA_DIR / "susb_us_sector_size_2022.csv"
BDS_PATH = TARGET_DATA_DIR / "bds_us_firm_size_1978_2022.csv"
SOURCE_SIDECAR_PATH = TARGET_DATA_DIR / "employer_firm_target_sources.md"
TARGET_PROVENANCE_PATH = TARGET_DATA_DIR / "target_provenance.json"

SUSB_EXTRACT_SHA256 = "b2db9502cf71480f4284cbeb8b78f31e8eb77f63963f679c167bfd40ade9d5e0"
BDS_EXTRACT_SHA256 = "0cbfec27392d4d328ddf8be9800c30a65d954d3a50ef170e9c98fc4babc82b31"
SOURCE_SIDECAR_SHA256 = (
    "a3e978316ff3487b66c066a4ea508e0ca0bb38be38c6d24eb0247e12199cd938"
)
TARGET_PROVENANCE_SHA256 = (
    "5b9eb0b42a3bc189fc7b1f75118d7f8a5db3448d2ce719aacbd904f71c29477d"
)

SUSB_US_TOTAL_FIRMS_2022 = 6_395_635
SUSB_US_TOTAL_EMPLOYMENT_2022 = 135_748_407
SUSB_CALIBRATION_CELL_COUNT_2022 = 97
SUSB_CALIBRATION_FIRMS_2022 = 6_461_497
SUSB_CALIBRATION_EMPLOYMENT_2022 = 135_748_407
SUSB_IN_SCOPE_EMPLOYMENT_2022 = 132_086_430

CALIBRATION_BANDS: tuple[str, ...] = (
    "LT10",
    "B10_49",
    "B50_99",
    "B100_499",
    "B500_PLUS",
)
CALIBRATION_TARGET_COLUMNS: tuple[str, ...] = (
    "calibration_sector",
    "calibration_band",
    "firms",
    "employment",
    "employment_in_scope",
)

# These intervals only aggregate the SUSB enterprise-size source into the
# frame builder's constraint cells. Dynamics owns the IC2 wire bander.
SUSB_DETAIL_SIZE_INTERVALS: dict[str, tuple[int, int | None]] = {
    "02": (1, 4),
    "03": (5, 9),
    "04": (10, 14),
    "05": (15, 19),
    "06": (20, 24),
    "07": (25, 29),
    "08": (30, 34),
    "09": (35, 39),
    "10": (40, 49),
    "11": (50, 74),
    "12": (75, 99),
    "13": (100, 149),
    "14": (150, 199),
    "15": (200, 299),
    "16": (300, 399),
    "17": (400, 499),
    "18": (500, 749),
    "19": (750, 999),
    "31": (1_000, 1_499),
    "22": (1_500, 1_999),
    "23": (2_000, 2_499),
    "24": (2_500, 4_999),
    "25": (5_000, None),
}
SUSB_DETAIL_SIZE_LABELS: dict[str, str] = {
    "02": "<5",
    "03": "5-9",
    "04": "10-14",
    "05": "15-19",
    "06": "20-24",
    "07": "25-29",
    "08": "30-34",
    "09": "35-39",
    "10": "40-49",
    "11": "50-74",
    "12": "75-99",
    "13": "100-149",
    "14": "150-199",
    "15": "200-299",
    "16": "300-399",
    "17": "400-499",
    "18": "500-749",
    "19": "750-999",
    "31": "1,000-1,499",
    "22": "1,500-1,999",
    "23": "2,000-2,499",
    "24": "2,500-4,999",
    "25": "5,000+",
}

_COMPOSITE_SECTOR_CROSSWALK: dict[str, str] = {
    "31": "31-33",
    "32": "31-33",
    "33": "31-33",
    "44": "44-45",
    "45": "44-45",
    "48": "48-49",
    "49": "48-49",
}
_PUBLISHED_COMPOSITE_SECTORS = frozenset({"31-33", "44-45", "48-49"})
_EMPLOYMENT_OUT_OF_SCOPE_SECTORS = frozenset({"55"})

_SUSB_COLUMNS: tuple[str, ...] = (
    "naics_sector",
    "naics_description",
    "entrsize_code",
    "entrsize_label",
    "firms",
    "establishments",
    "employment",
    "employment_noise_flag",
    "annual_payroll_kusd",
)
_BDS_COLUMNS: tuple[str, ...] = (
    "year",
    "fsize",
    "firms",
    "estabs",
    "emp",
    "denom",
    "estabs_entry",
    "estabs_entry_rate",
    "estabs_exit",
    "estabs_exit_rate",
    "job_creation",
    "job_creation_rate",
    "job_destruction",
    "job_destruction_rate",
    "net_job_creation",
    "net_job_creation_rate",
    "reallocation_rate",
    "firmdeath_firms",
    "firmdeath_emp",
)
_BDS_SIZE_CATEGORIES: tuple[str, ...] = (
    "a) 1 to 4",
    "b) 5 to 9",
    "c) 10 to 19",
    "d) 20 to 99",
    "e) 100 to 499",
    "f) 500 to 999",
    "g) 1000 to 2499",
    "h) 2500 to 4999",
    "i) 5000 to 9999",
    "j) 10000+",
)
_BDS_EXACT_VALIDATION_CATEGORIES: dict[str, tuple[str, ...]] = {
    "LT10": ("a) 1 to 4", "b) 5 to 9"),
    "B100_499": ("e) 100 to 499",),
    "B500_PLUS": (
        "f) 500 to 999",
        "g) 1000 to 2499",
        "h) 2500 to 4999",
        "i) 5000 to 9999",
        "j) 10000+",
    ),
}


def calibration_band_for_employment(count: object) -> str:
    """Return the private SUSB calibration cell for a positive headcount.

    This helper is build-time target geometry, not dynamics' canonical IC2
    banding implementation or wire type.
    """

    if isinstance(count, bool):
        raise ValueError("Firm employment must be a positive integer, not bool.")
    try:
        numeric = float(count)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Firm employment is not numeric: {count!r}.") from exc
    if not math.isfinite(numeric) or numeric <= 0 or not numeric.is_integer():
        raise ValueError(f"Firm employment must be a positive integer: {count!r}.")
    employment = int(numeric)
    if employment < 10:
        return "LT10"
    if employment < 50:
        return "B10_49"
    if employment < 100:
        return "B50_99"
    if employment < 500:
        return "B100_499"
    return "B500_PLUS"


def _detail_size_to_calibration_band(
    interval: tuple[int, int | None],
) -> str:
    lower, upper = interval
    band = calibration_band_for_employment(lower)
    if upper is not None and calibration_band_for_employment(upper) != band:
        raise RuntimeError(f"SUSB detail interval {interval!r} crosses a cell edge.")
    return band


SUSB_DETAIL_SIZE_TO_CALIBRATION_BAND: dict[str, str] = {
    code: _detail_size_to_calibration_band(interval)
    for code, interval in SUSB_DETAIL_SIZE_INTERVALS.items()
}


def calibration_sector_for_naics(value: object) -> str:
    """Map a full NAICS code or sector into a symmetric SUSB sector key."""

    raw = str(value).strip()
    if raw in _PUBLISHED_COMPOSITE_SECTORS:
        return raw
    if len(raw) < 2 or not raw.isdigit():
        raise ValueError(f"NAICS value does not contain a valid sector: {value!r}.")
    sector = raw[:2]
    return _COMPOSITE_SECTOR_CROSSWALK.get(sector, sector)


@dataclass(frozen=True)
class USFirmLedgerTargetProfile:
    """Explicit selectors for a future US firm Ledger target profile."""

    firm_count_record_set_id: str
    employment_record_set_id: str
    firm_count_measure_id: str
    employment_measure_id: str
    sector_dimension_id: str
    size_dimension_id: str
    size_value_to_calibration_band: Mapping[str, str]

    def __post_init__(self) -> None:
        selector_fields = (
            "firm_count_record_set_id",
            "employment_record_set_id",
            "firm_count_measure_id",
            "employment_measure_id",
            "sector_dimension_id",
            "size_dimension_id",
        )
        for field_name in selector_fields:
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string.")
        firm_selector = (
            self.firm_count_record_set_id,
            self.firm_count_measure_id,
        )
        employment_selector = (
            self.employment_record_set_id,
            self.employment_measure_id,
        )
        if firm_selector == employment_selector:
            raise ValueError("Firm-count and employment Ledger selectors must differ.")

        size_mapping = {
            str(source_value): str(target_band)
            for source_value, target_band in self.size_value_to_calibration_band.items()
        }
        if not size_mapping:
            raise ValueError("size_value_to_calibration_band must not be empty.")
        unknown_bands = sorted(set(size_mapping.values()) - set(CALIBRATION_BANDS))
        if unknown_bands:
            raise ValueError(
                f"Ledger size mapping has unknown calibration band(s): {unknown_bands}."
            )
        missing_bands = sorted(set(CALIBRATION_BANDS) - set(size_mapping.values()))
        if missing_bands:
            raise ValueError(
                "Ledger size mapping does not cover calibration band(s): "
                f"{missing_bands}."
            )
        object.__setattr__(
            self,
            "size_value_to_calibration_band",
            MappingProxyType(size_mapping),
        )


@dataclass(frozen=True)
class USFirmTargets:
    """Stable calibration cells and optional source-detail evidence."""

    calibration_cells: pd.DataFrame
    detail_cells: pd.DataFrame | None
    source_mode: str
    provenance: Mapping[str, Any]


def us_firm_targets_from_ledger_facts(
    facts: Iterable[Mapping[str, Any] | object],
    *,
    target_profile: USFirmLedgerTargetProfile,
) -> USFirmTargets:
    """Materialize production US firm targets from Ledger consumer facts.

    The profile is mandatory because no Chronicle SUSB package or registered
    Ledger record-set selector exists yet. Ledger rows must explicitly carry
    both sector and size dimensions. Every sector must cover all five private
    calibration cells, including explicit zero cells where applicable.
    """

    if not isinstance(target_profile, USFirmLedgerTargetProfile):
        raise TypeError("target_profile must be a USFirmLedgerTargetProfile.")
    fact_rows = tuple(facts)
    firm_rows = _ledger_measure_rows(
        fact_rows,
        record_set_id=target_profile.firm_count_record_set_id,
        measure_id=target_profile.firm_count_measure_id,
        target_profile=target_profile,
    )
    employment_rows = _ledger_measure_rows(
        fact_rows,
        record_set_id=target_profile.employment_record_set_id,
        measure_id=target_profile.employment_measure_id,
        target_profile=target_profile,
    )
    if set(firm_rows) != set(employment_rows):
        missing_employment = sorted(set(firm_rows) - set(employment_rows))
        missing_firms = sorted(set(employment_rows) - set(firm_rows))
        raise ValueError(
            "Ledger US firm measures do not cover the same source cells; "
            f"missing employment={missing_employment}, missing firms={missing_firms}."
        )

    source_rows: list[dict[str, object]] = []
    identities_by_cell: dict[tuple[str, str], dict[str, object]] = {}
    target_periods: dict[tuple[str, str], dict[str, object]] = {}
    firm_fact_keys = {row[3] for row in firm_rows.values()}
    employment_fact_keys = {row[3] for row in employment_rows.values()}
    reused_fact_keys = sorted(firm_fact_keys & employment_fact_keys)
    if reused_fact_keys:
        raise ValueError(
            "Ledger US firm measures reuse aggregate_fact_key identity: "
            f"{reused_fact_keys}."
        )
    for source_key in sorted(firm_rows):
        sector, band, firms, firm_fact_key, firm_period = firm_rows[source_key]
        (
            employment_sector,
            employment_band,
            employment,
            employment_fact_key,
            employment_period,
        ) = employment_rows[source_key]
        if (employment_sector, employment_band) != (sector, band):
            raise ValueError(f"Ledger US firm cell mapping differs for {source_key!r}.")
        if employment_period != firm_period:
            raise ValueError(
                f"Ledger US firm measures have different periods for {source_key!r}."
            )
        source_rows.append(
            {
                "calibration_sector": sector,
                "calibration_band": band,
                "firms": firms,
                "employment": employment,
            }
        )
        cell_identity = identities_by_cell.setdefault(
            (sector, band),
            {
                "calibration_sector": sector,
                "calibration_band": band,
                "firm_count_aggregate_fact_keys": [],
                "employment_aggregate_fact_keys": [],
                "period": firm_period,
            },
        )
        if cell_identity["period"] != firm_period:
            raise ValueError(
                f"Ledger US firm source rows mix periods within {sector}/{band}."
            )
        cell_identity["firm_count_aggregate_fact_keys"].append(firm_fact_key)
        cell_identity["employment_aggregate_fact_keys"].append(employment_fact_key)
        period_key = (str(firm_period["type"]), str(firm_period["value"]))
        target_periods[period_key] = firm_period

    if len(target_periods) != 1:
        raise ValueError(
            "Ledger US firm targets must share one target-period identity; got "
            f"{list(target_periods.values())}."
        )

    grouped = (
        pd.DataFrame(source_rows)
        .groupby(["calibration_sector", "calibration_band"], as_index=False)[
            ["firms", "employment"]
        ]
        .sum()
    )
    _require_complete_calibration_grid(grouped)
    cells = _finalize_calibration_cells(grouped)
    cell_identities = []
    for cell_key in sorted(identities_by_cell, key=_cell_sort_key):
        identity = identities_by_cell[cell_key]
        identity["firm_count_aggregate_fact_keys"] = sorted(
            identity["firm_count_aggregate_fact_keys"]
        )
        identity["employment_aggregate_fact_keys"] = sorted(
            identity["employment_aggregate_fact_keys"]
        )
        cell_identities.append(identity)
    provenance = {
        "source_mode": "ledger_consumer_facts",
        "detail_cells_available": False,
        "firm_count_record_set_id": target_profile.firm_count_record_set_id,
        "employment_record_set_id": target_profile.employment_record_set_id,
        "firm_count_measure_id": target_profile.firm_count_measure_id,
        "employment_measure_id": target_profile.employment_measure_id,
        "sector_dimension_id": target_profile.sector_dimension_id,
        "size_dimension_id": target_profile.size_dimension_id,
        "target_periods": list(target_periods.values()),
        "cell_fact_identities": cell_identities,
    }
    return USFirmTargets(
        calibration_cells=cells,
        detail_cells=None,
        source_mode="ledger_consumer_facts",
        provenance=provenance,
    )


def load_susb_migration_harness() -> USFirmTargets:
    """Load the pinned SUSB extract as a labelled migration harness only."""

    _verify_pinned_file(SUSB_PATH, SUSB_EXTRACT_SHA256)
    provenance = _load_target_provenance(
        "susb_us_sector_size_2022.csv",
        SUSB_EXTRACT_SHA256,
    )
    susb = pd.read_csv(
        SUSB_PATH,
        dtype={"naics_sector": "string", "entrsize_code": "string"},
    )
    if tuple(susb.columns) != _SUSB_COLUMNS:
        raise ValueError(f"SUSB extract columns changed: {list(susb.columns)}.")
    if susb.duplicated(["naics_sector", "entrsize_code"]).any():
        raise ValueError("SUSB extract has duplicate sector by ENTRSIZE cells.")
    for column in ("firms", "employment"):
        values = pd.to_numeric(susb[column], errors="raise")
        if values.isna().any() or (values < 0).any() or (values % 1 != 0).any():
            raise ValueError(f"SUSB {column} values must be non-negative integers.")
        susb[column] = values.astype("int64")

    total = susb[(susb["naics_sector"] == "--") & (susb["entrsize_code"] == "01")]
    if len(total) != 1:
        raise ValueError("SUSB extract lacks a unique US total row.")
    if int(total.iloc[0]["firms"]) != SUSB_US_TOTAL_FIRMS_2022:
        raise ValueError("SUSB US total firms changed from the pinned value.")
    if int(total.iloc[0]["employment"]) != SUSB_US_TOTAL_EMPLOYMENT_2022:
        raise ValueError("SUSB US total employment changed from the pinned value.")

    detail = susb[
        (susb["naics_sector"] != "--")
        & susb["entrsize_code"].isin(SUSB_DETAIL_SIZE_INTERVALS)
    ].copy()
    _validate_susb_detail_labels(detail)
    detail["source_naics_sector"] = detail["naics_sector"].astype(str)
    detail["calibration_sector"] = detail["source_naics_sector"].map(
        calibration_sector_for_naics
    )
    detail["calibration_band"] = detail["entrsize_code"].map(
        SUSB_DETAIL_SIZE_TO_CALIBRATION_BAND
    )
    detail["employment_lower_bound"] = detail["entrsize_code"].map(
        lambda code: SUSB_DETAIL_SIZE_INTERVALS[str(code)][0]
    )
    detail["employment_upper_bound"] = pd.array(
        [SUSB_DETAIL_SIZE_INTERVALS[str(code)][1] for code in detail["entrsize_code"]],
        dtype="Int64",
    )
    detail = detail[
        [
            "calibration_sector",
            "source_naics_sector",
            "naics_description",
            "entrsize_code",
            "entrsize_label",
            "employment_lower_bound",
            "employment_upper_bound",
            "calibration_band",
            "firms",
            "employment",
            "employment_noise_flag",
        ]
    ]
    detail = _sort_target_cells(detail, detail_order="employment_lower_bound")

    grouped = detail.groupby(
        ["calibration_sector", "calibration_band"],
        as_index=False,
    )[["firms", "employment"]].sum()
    cells = _finalize_calibration_cells(grouped)
    if len(cells) != SUSB_CALIBRATION_CELL_COUNT_2022:
        raise ValueError(
            f"SUSB calibration cell count changed: {len(cells)}; "
            f"expected {SUSB_CALIBRATION_CELL_COUNT_2022}."
        )
    if int(cells["firms"].sum()) != SUSB_CALIBRATION_FIRMS_2022:
        raise ValueError("SUSB sector-cell firm total changed from the pinned value.")
    if int(cells["employment"].sum()) != SUSB_CALIBRATION_EMPLOYMENT_2022:
        raise ValueError(
            "SUSB sector-cell employment total changed from the pinned value."
        )
    in_scope = cells.loc[cells["employment_in_scope"], "employment"].sum()
    if int(in_scope) != SUSB_IN_SCOPE_EMPLOYMENT_2022:
        raise ValueError("SUSB in-scope employment changed from the pinned value.")

    harness_provenance = {
        "source_mode": "migration_harness",
        "production_target_authority": "ledger_consumer_facts",
        "detail_cells_available": True,
        "extract_sha256": SUSB_EXTRACT_SHA256,
        "source": provenance,
        "us_total_firms": SUSB_US_TOTAL_FIRMS_2022,
        "us_total_employment": SUSB_US_TOTAL_EMPLOYMENT_2022,
        "calibration_cell_count": SUSB_CALIBRATION_CELL_COUNT_2022,
        "calibration_firms": SUSB_CALIBRATION_FIRMS_2022,
        "calibration_employment": SUSB_CALIBRATION_EMPLOYMENT_2022,
    }
    return USFirmTargets(
        calibration_cells=cells,
        detail_cells=detail,
        source_mode="migration_harness",
        provenance=harness_provenance,
    )


def load_bds_validation_harness(*, year: int = 2022) -> pd.DataFrame:
    """Load complete, exact BDS comparison bands for held-out validation.

    BDS' 20-99 class crosses the 50-worker cell edge, so neither B10_49 nor
    B50_99 has a complete BDS comparison margin. The returned frame therefore
    contains only LT10, B100_499, and B500_PLUS.
    """

    _verify_pinned_file(BDS_PATH, BDS_EXTRACT_SHA256)
    provenance = _load_target_provenance(
        "bds_us_firm_size_1978_2022.csv",
        BDS_EXTRACT_SHA256,
    )
    bds = pd.read_csv(BDS_PATH)
    if tuple(bds.columns) != _BDS_COLUMNS:
        raise ValueError(f"BDS extract columns changed: {list(bds.columns)}.")
    if tuple(sorted(bds["fsize"].unique())) != tuple(sorted(_BDS_SIZE_CATEGORIES)):
        raise ValueError("BDS firm-size categories changed.")
    if int(bds["year"].min()) != 1978 or int(bds["year"].max()) != 2022:
        raise ValueError("BDS extract year range changed.")
    selected = bds[bds["year"] == year].copy()
    if len(selected) != len(_BDS_SIZE_CATEGORIES):
        raise ValueError(f"BDS extract lacks the complete firm-size grid for {year}.")
    for column in ("firms", "emp"):
        values = pd.to_numeric(selected[column], errors="raise")
        if values.isna().any() or (values < 0).any() or (values % 1 != 0).any():
            raise ValueError(f"BDS {column} values must be non-negative integers.")
        selected[column] = values.astype("int64")

    rows: list[dict[str, object]] = []
    for band, categories in _BDS_EXACT_VALIDATION_CATEGORIES.items():
        band_rows = selected[selected["fsize"].isin(categories)]
        if set(band_rows["fsize"]) != set(categories):
            raise ValueError(f"BDS {year} lacks source rows for {band}.")
        rows.append(
            {
                "year": year,
                "calibration_band": band,
                "firms": int(band_rows["firms"].sum()),
                "employment": int(band_rows["emp"].sum()),
                "source_categories": " | ".join(categories),
            }
        )
    result = pd.DataFrame(rows)
    result["_band_order"] = result["calibration_band"].map(
        {band: index for index, band in enumerate(CALIBRATION_BANDS)}
    )
    result = result.sort_values("_band_order").drop(columns="_band_order")
    result = result.reset_index(drop=True)
    result.attrs.update(
        {
            "source_mode": "validation_migration_harness",
            "held_out": True,
            "extract_sha256": BDS_EXTRACT_SHA256,
            "source": provenance,
            "excluded_inexact_categories": [
                "c) 10 to 19",
                "d) 20 to 99",
            ],
        }
    )
    return result


def _ledger_measure_rows(
    facts: tuple[Mapping[str, Any] | object, ...],
    *,
    record_set_id: str,
    measure_id: str,
    target_profile: USFirmLedgerTargetProfile,
) -> dict[
    tuple[str, str],
    tuple[str, str, float, str, dict[str, object]],
]:
    rows: dict[
        tuple[str, str],
        tuple[str, str, float, str, dict[str, object]],
    ] = {}
    fact_keys: set[str] = set()
    for fact in facts:
        if (
            _fact_at(fact, "layout", "record_set_id") != record_set_id
            or _fact_at(fact, "layout", "measure_id") != measure_id
        ):
            continue
        _validate_ledger_fact(fact, record_set_id, measure_id)
        raw_sector = _dimension_value(fact, target_profile.sector_dimension_id)
        raw_size = _dimension_value(fact, target_profile.size_dimension_id)
        if raw_sector is None or raw_size is None:
            raise ValueError(
                f"Ledger US firm fact {record_set_id}/{measure_id} must carry "
                f"dimensions {target_profile.sector_dimension_id!r} and "
                f"{target_profile.size_dimension_id!r}."
            )
        source_key = (str(raw_sector).strip(), str(raw_size).strip())
        if source_key in rows:
            raise ValueError(
                f"Duplicate Ledger US firm fact for {record_set_id}/{measure_id}/"
                f"{source_key[0]}/{source_key[1]}."
            )
        band = target_profile.size_value_to_calibration_band.get(source_key[1])
        if band is None:
            raise ValueError(
                f"Ledger US firm fact has unmapped size value {source_key[1]!r}."
            )
        aggregate_fact_key = _fact_at(fact, "aggregate_fact_key")
        if not isinstance(aggregate_fact_key, str) or not aggregate_fact_key:
            raise ValueError(
                f"Ledger US firm fact {record_set_id}/{measure_id} is missing "
                "aggregate_fact_key."
            )
        if aggregate_fact_key in fact_keys:
            raise ValueError(
                f"Ledger US firm facts reuse aggregate_fact_key {aggregate_fact_key!r}."
            )
        fact_keys.add(aggregate_fact_key)
        period_type = _fact_at(fact, "period", "type")
        period_value = _fact_at(fact, "period", "value")
        if not isinstance(period_type, str) or not period_type or period_value is None:
            raise ValueError(
                f"Ledger US firm fact {aggregate_fact_key!r} is missing its "
                "period identity."
            )
        rows[source_key] = (
            calibration_sector_for_naics(source_key[0]),
            band,
            _numeric_ledger_value(fact),
            aggregate_fact_key,
            {"type": period_type, "value": period_value},
        )
    if not rows:
        raise ValueError(
            f"Ledger US firm facts are missing {record_set_id}/{measure_id} rows."
        )
    return rows


def _require_complete_calibration_grid(frame: pd.DataFrame) -> None:
    sectors = set(frame["calibration_sector"].astype(str))
    actual = set(
        zip(
            frame["calibration_sector"].astype(str),
            frame["calibration_band"].astype(str),
            strict=True,
        )
    )
    expected = {(sector, band) for sector in sectors for band in CALIBRATION_BANDS}
    missing = sorted(expected - actual)
    if missing:
        raise ValueError(
            "Ledger US firm targets omit calibration cell(s); publish explicit "
            f"zero cells where needed: {missing}."
        )


def _finalize_calibration_cells(frame: pd.DataFrame) -> pd.DataFrame:
    cells = frame.copy()
    for column in ("firms", "employment"):
        cells[column] = pd.to_numeric(cells[column], errors="raise")
        if cells[column].isna().any() or (cells[column] < 0).any():
            raise ValueError(f"US firm target {column} values must be non-negative.")
    inconsistent_zero = (cells["firms"] == 0) & (cells["employment"] != 0)
    if inconsistent_zero.any():
        bad = cells.loc[
            inconsistent_zero,
            ["calibration_sector", "calibration_band"],
        ].to_dict("records")
        raise ValueError(f"Zero-firm target cells have employment: {bad}.")
    cells = cells[cells["firms"] > 0].copy()
    cells["employment_in_scope"] = ~cells["calibration_sector"].isin(
        _EMPLOYMENT_OUT_OF_SCOPE_SECTORS
    )
    cells = _sort_target_cells(cells)
    if cells.duplicated(["calibration_sector", "calibration_band"]).any():
        raise ValueError("US firm calibration targets contain duplicate cells.")
    return cells[list(CALIBRATION_TARGET_COLUMNS)]


def _sort_target_cells(
    frame: pd.DataFrame,
    *,
    detail_order: str | None = None,
) -> pd.DataFrame:
    result = frame.copy()
    result["_sector_order"] = result["calibration_sector"].str[:2].astype(int)
    result["_band_order"] = result["calibration_band"].map(
        {band: index for index, band in enumerate(CALIBRATION_BANDS)}
    )
    order = ["_sector_order", "_band_order"]
    if detail_order is not None:
        order.append(detail_order)
    result = result.sort_values(order, kind="stable")
    return result.drop(columns=["_sector_order", "_band_order"]).reset_index(drop=True)


def _cell_sort_key(cell: tuple[str, str]) -> tuple[int, int]:
    sector, band = cell
    return int(sector[:2]), CALIBRATION_BANDS.index(band)


def _validate_susb_detail_labels(detail: pd.DataFrame) -> None:
    labels = (
        detail[["entrsize_code", "entrsize_label"]]
        .drop_duplicates()
        .set_index("entrsize_code")["entrsize_label"]
        .astype(str)
        .to_dict()
    )
    if labels != SUSB_DETAIL_SIZE_LABELS:
        raise ValueError(f"SUSB detail ENTRSIZE labels changed: {labels}.")


def _validate_ledger_fact(
    fact: Mapping[str, Any] | object,
    record_set_id: str,
    measure_id: str,
) -> None:
    entity_name = _fact_at(fact, "entity", "name")
    if entity_name != "firm":
        raise ValueError(
            f"Ledger US firm fact {record_set_id}/{measure_id} has entity "
            f"{entity_name!r}; expected 'firm'."
        )
    aggregation = _fact_at(fact, "aggregation", "method")
    if aggregation != "sum":
        raise ValueError(
            f"Ledger US firm fact {record_set_id}/{measure_id} has aggregation "
            f"{aggregation!r}; expected 'sum'."
        )


def _numeric_ledger_value(fact: Mapping[str, Any] | object) -> float:
    value = _fact_at(fact, "value")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Ledger US firm fact has non-numeric value {value!r}."
        ) from exc
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(
            f"Ledger US firm fact has invalid non-negative value {value!r}."
        )
    return numeric


def _dimension_value(fact: Mapping[str, Any] | object, dimension_id: str) -> Any:
    value = _fact_at(fact, "dimensions", dimension_id)
    if value is not None:
        return value
    return _fact_at(fact, "filters", dimension_id)


def _fact_at(fact: Mapping[str, Any] | object, *path: str) -> Any:
    value: Any = fact
    for key in path:
        if isinstance(value, Mapping):
            value = value.get(key)
        else:
            value = getattr(value, key, None)
        if value is None:
            return None
    return value


def _load_target_provenance(
    artifact_name: str,
    expected_sha256: str,
) -> Mapping[str, Any]:
    _verify_pinned_file(SOURCE_SIDECAR_PATH, SOURCE_SIDECAR_SHA256)
    _verify_pinned_file(TARGET_PROVENANCE_PATH, TARGET_PROVENANCE_SHA256)
    with TARGET_PROVENANCE_PATH.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if payload.get("status") != "migration_harness_only":
        raise ValueError("US firm target provenance lost its migration-only status.")
    artifact = payload.get("artifacts", {}).get(artifact_name)
    if not isinstance(artifact, Mapping):
        raise ValueError(f"US firm target provenance omits {artifact_name}.")
    if artifact.get("extract_sha256") != expected_sha256:
        raise ValueError(f"US firm target provenance hash changed for {artifact_name}.")
    return dict(artifact)


def _verify_pinned_file(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Pinned US firm target extract not found: {path}.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected_sha256:
        raise ValueError(
            f"Pinned US firm target extract hash mismatch for {path.name}: "
            f"expected {expected_sha256}, got {actual}."
        )
