"""Readers for observed Form 5500 plan-sponsor filings.

The source observation is a filing and the aggregated observation is a plan
sponsor EIN.  Neither is a Census SUSB enterprise.  Active participants are
plan-covered workers, not the sponsor's complete workforce, so consumers must
retain the measurement metadata emitted here when using the count as an
employment proxy.

The main and short forms use different entity-type code systems.  This module
keeps the source code, its code system, and all strata seen for a sponsor.  It
does not apply the unresolved single-employer filter.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = [
    "FIRM_DATA_DIR_ENV",
    "MAIN_COLUMNS",
    "SF_COLUMNS",
    "firm_data_dir",
    "read_main_filings",
    "read_sf_filings",
    "read_sponsors",
]

FIRM_DATA_DIR_ENV = "MICROCOSM_US_FIRM_DATA_DIR"
_DEFAULT_DATA_DIR = Path("~/PolicyEngine/firm-data").expanduser()

_STAGING_HINT = (
    "Stage the pinned US firm source files under ~/PolicyEngine/firm-data "
    f"(or set {FIRM_DATA_DIR_ENV})."
)

# Names verified against the DOL layouts for the staged 2023 files.  The main
# form reports total beginning-of-year participants and active end-of-year
# participants; those are distinct measures and remain distinct here.
MAIN_COLUMNS = {
    "SPONS_DFE_EIN": "sponsor_ein",
    "BUSINESS_CODE": "naics_code",
    "SPONS_DFE_LOC_US_STATE": "state",
    "TYPE_PLAN_ENTITY_CD": "plan_entity_code",
    "TOT_PARTCP_BOY_CNT": "total_participants_boy",
    "TOT_ACTIVE_PARTCP_CNT": "active_participants_eoy",
}

# Form 5500-SF supplies both beginning- and end-of-year active-participant
# fields.  Using the EOY field makes the active measure consistent with the
# main-form field instead of silently combining different timings.
SF_COLUMNS = {
    "SF_SPONS_EIN": "sponsor_ein",
    "SF_BUSINESS_CODE": "naics_code",
    "SF_SPONS_US_STATE": "state",
    "SF_TYPE_PLAN_ENTITY_CD": "plan_entity_code",
    "SF_TOT_ACT_PARTCP_BOY_CNT": "active_participants_boy",
    "SF_TOT_ACT_PARTCP_EOY_CNT": "active_participants_eoy",
}

_FILING_COLUMNS = (
    "sponsor_ein",
    "naics_code",
    "naics_sector",
    "state",
    "plan_entity_code",
    "plan_entity_code_system",
    "plan_entity_type",
    "active_participants_boy",
    "total_participants_boy",
    "active_participants_eoy",
    "participant_timing",
    "employment_measure",
    "employment_measure_source_field",
    "employment_is_lower_bound",
    "observation_unit",
    "source_form",
    "source_year",
    "source_filename",
)

_MAIN_ENTITY_TYPES = {
    "1": "multiemployer",
    "2": "single_employer",
    "3": "multiple_employer",
    "4": "direct_filing_entity",
}

# The SF line-A codes are not interchangeable with TYPE_PLAN_ENTITY_CD on the
# main form.  In particular, SF code 1 means single-employer while main-form
# code 1 means multiemployer.
_SF_ENTITY_TYPES = {
    "1": "single_employer",
    "2": "multiple_employer",
    "3": "one_participant",
    "4": "foreign",
}

_ALLOWED_FORMS = ("5500", "5500-SF")


def firm_data_dir() -> Path:
    """Return the out-of-repository directory holding staged source files."""
    configured = os.environ.get(FIRM_DATA_DIR_ENV)
    if configured:
        return Path(configured).expanduser()
    return _DEFAULT_DATA_DIR


def _resolve(name: str, data_dir: Path | None) -> Path:
    root = data_dir if data_dir is not None else firm_data_dir()
    path = root / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. {_STAGING_HINT}")
    return path


def _normalise_ein(series: pd.Series) -> pd.Series:
    """Return strict, digits-only, zero-padded nine-character EINs.

    A bare one-to-nine digit value or the conventional ``12-3456789`` form is
    accepted.  Other punctuation and embedded letters are not silently
    stripped into a different identifier.
    """
    text = series.astype("string").str.strip()
    valid = text.str.fullmatch(r"\d{1,9}") | text.str.fullmatch(r"\d{2}-\d{7}")
    digits = text.where(valid).str.replace("-", "", regex=False)
    return digits.str.zfill(9)


def _normalise_naics(series: pd.Series) -> pd.Series:
    """Return a full six-digit principal business code or ``NA``."""
    text = series.astype("string").str.strip()
    return text.where(text.str.fullmatch(r"\d{6}"))


def _normalise_entity_code(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return text.where(text.ne(""))


def _integer_count(series: pd.Series, *, source_field: str) -> pd.Series:
    """Coerce a source count while refusing to truncate fractional people."""
    numeric = pd.to_numeric(series, errors="coerce")
    finite = numeric.notna() & np.isfinite(numeric)
    fractional = finite & numeric.ne(np.floor(numeric))
    nonfinite = numeric.notna() & ~np.isfinite(numeric)
    if bool((fractional | nonfinite).any()):
        bad = series[fractional | nonfinite].head(3).tolist()
        raise ValueError(
            f"{source_field} contains non-integral participant counts {bad}; "
            "the reader refuses to truncate people."
        )
    return numeric.astype("Int64")


def _check_columns(path: Path, mapping: dict[str, str], form: str) -> None:
    header = pd.read_csv(path, nrows=0)
    missing = [column for column in mapping if column not in header.columns]
    if missing:
        raise ValueError(
            f"Form {form} file {path.name} is missing columns {missing}; "
            "the DOL layout changed and the reader must be re-verified "
            "against the published layout."
        )


def _harmonise(
    frame: pd.DataFrame,
    mapping: dict[str, str],
    *,
    form: str,
    year: int,
    filename: str,
) -> pd.DataFrame:
    out = frame[list(mapping)].rename(columns=mapping).copy()
    out["sponsor_ein"] = _normalise_ein(out["sponsor_ein"])
    out["naics_code"] = _normalise_naics(out["naics_code"])
    out["naics_sector"] = out["naics_code"].str[:2]
    out["state"] = out["state"].astype("string").str.strip().str.upper()
    out["plan_entity_code"] = _normalise_entity_code(
        out["plan_entity_code"]
    )

    if form == "5500":
        code_system = "form_5500_type_plan_entity_cd"
        entity_types = _MAIN_ENTITY_TYPES
        active_source_field = "TOT_ACTIVE_PARTCP_CNT"
    else:
        code_system = "form_5500_sf_type_plan_entity_cd"
        entity_types = _SF_ENTITY_TYPES
        active_source_field = "SF_TOT_ACT_PARTCP_EOY_CNT"

    out["plan_entity_code_system"] = code_system
    mapped_type = out["plan_entity_code"].map(entity_types)
    out["plan_entity_type"] = mapped_type.mask(
        out["plan_entity_code"].notna() & mapped_type.isna(), "unmapped"
    )

    for target, source in (
        ("active_participants_boy", "SF_TOT_ACT_PARTCP_BOY_CNT"),
        ("total_participants_boy", "TOT_PARTCP_BOY_CNT"),
        ("active_participants_eoy", active_source_field),
    ):
        if target in out:
            out[target] = _integer_count(out[target], source_field=source)
        else:
            out[target] = pd.Series(pd.NA, index=out.index, dtype="Int64")

    out["participant_timing"] = "end_of_year"
    out["employment_measure"] = "active_plan_participants"
    out["employment_measure_source_field"] = active_source_field
    # Across the retained plan-entity strata this proxy is not ordered with
    # enterprise employment: a multiemployer plan can span employers, and an
    # active-participant count can include people who are not current sponsor
    # employees.  Do not repeat the source prototype's lower-bound claim.
    out["employment_is_lower_bound"] = False
    out["observation_unit"] = "plan_filing"
    out["source_form"] = form
    out["source_year"] = int(year)
    out["source_filename"] = filename
    out = out.loc[:, list(_FILING_COLUMNS)]
    out.attrs["measurement_model"] = {
        "observation_unit": "plan_filing",
        "employment_measure": "active_plan_participants",
        "participant_timing": "end_of_year",
        "employment_proxy_relation": "not_ordered_across_plan_entity_strata",
        "cleaning_applied": False,
    }
    return out


def read_main_filings(year: int, data_dir: Path | None = None) -> pd.DataFrame:
    """Read one row per main Form 5500 filing without filtering rows."""
    name = f"f_5500_{year}_latest.csv"
    path = _resolve(name, data_dir)
    _check_columns(path, MAIN_COLUMNS, "5500")
    frame = pd.read_csv(
        path,
        usecols=list(MAIN_COLUMNS),
        dtype={
            "SPONS_DFE_EIN": "string",
            "BUSINESS_CODE": "string",
            "TYPE_PLAN_ENTITY_CD": "string",
        },
        low_memory=False,
    )
    return _harmonise(
        frame,
        MAIN_COLUMNS,
        form="5500",
        year=year,
        filename=name,
    )


def read_sf_filings(year: int, data_dir: Path | None = None) -> pd.DataFrame:
    """Read one row per Form 5500-SF filing without filtering rows."""
    name = f"f_5500_sf_{year}_latest.csv"
    path = _resolve(name, data_dir)
    _check_columns(path, SF_COLUMNS, "5500-SF")
    frame = pd.read_csv(
        path,
        usecols=list(SF_COLUMNS),
        dtype={
            "SF_SPONS_EIN": "string",
            "SF_BUSINESS_CODE": "string",
            "SF_TYPE_PLAN_ENTITY_CD": "string",
        },
        low_memory=False,
    )
    return _harmonise(
        frame,
        SF_COLUMNS,
        form="5500-SF",
        year=year,
        filename=name,
    )


def _validate_forms(forms: tuple[str, ...]) -> None:
    if not forms:
        raise ValueError("At least one of '5500' / '5500-SF' is required.")
    unknown = set(forms) - set(_ALLOWED_FORMS)
    if unknown:
        raise ValueError(f"Unknown Form 5500 variant(s) {sorted(unknown)}.")
    if len(forms) != len(set(forms)):
        raise ValueError("Form 5500 variants must not be repeated.")


def _joined_unique(series: pd.Series) -> object:
    values = sorted({str(value) for value in series.dropna() if str(value)})
    return "|".join(values) if values else pd.NA


def _stratum(row: pd.Series) -> str:
    code = row["plan_entity_code"]
    rendered_code = str(code) if pd.notna(code) else "not_reported"
    return f"{row['plan_entity_code_system']}:{rendered_code}"


def read_sponsors(
    year: int,
    data_dir: Path | None = None,
    *,
    forms: tuple[str, ...] = _ALLOWED_FORMS,
) -> pd.DataFrame:
    """Return one observed plan-sponsor row per valid sponsor EIN.

    Multiple plan filings under one EIN overlap, so the filing with maximum
    end-of-year active participants defines the sponsor's size.  Every field
    on the selected row (NAICS, state, form, and entity type) comes from that
    same filing.  Separate aggregate columns retain all entity strata, entity
    types, NAICS codes, and source forms observed for the sponsor.

    Rows with missing/invalid EINs or no positive active count cannot define a
    sponsor record and are reported in ``DataFrame.attrs['aggregation']``.
    No single-employer filter is applied.
    """
    _validate_forms(forms)

    readers = {
        "5500": read_main_filings,
        "5500-SF": read_sf_filings,
    }
    parts = [readers[form](year, data_dir) for form in forms]
    filings = pd.concat(parts, ignore_index=True)
    rows_in = len(filings)
    invalid_ein = filings["sponsor_ein"].isna()
    valid = filings.loc[~invalid_ein].copy()
    valid["_plan_entity_stratum"] = valid.apply(_stratum, axis=1)

    grouped = valid.groupby("sponsor_ein", sort=True, dropna=False)
    sponsor_metadata = grouped.agg(
        filings=("source_form", "size"),
        source_forms=("source_form", _joined_unique),
        plan_entity_strata=("_plan_entity_stratum", _joined_unique),
        plan_entity_types=("plan_entity_type", _joined_unique),
        naics_codes=("naics_code", _joined_unique),
    ).reset_index()
    sponsor_metadata["plan_entity_code_conflict"] = (
        sponsor_metadata["plan_entity_strata"].str.count(r"\|").fillna(-1) >= 1
    )
    sponsor_metadata["plan_entity_type_conflict"] = (
        sponsor_metadata["plan_entity_types"].str.count(r"\|").fillna(-1) >= 1
    )
    sponsor_metadata["naics_code_conflict"] = (
        sponsor_metadata["naics_codes"].str.count(r"\|").fillna(-1) >= 1
    )

    # Equal-size filings use a declared lexical metadata order, followed by
    # descending beginning-of-year counts.  Thus CSV row order cannot change
    # which coherent filing supplies the selected fields.
    tie_break_columns = [
        "source_form",
        "naics_code",
        "state",
        "plan_entity_code_system",
        "plan_entity_code",
        "source_filename",
        "active_participants_boy",
        "total_participants_boy",
    ]
    chosen = (
        valid.sort_values(
            ["sponsor_ein", "active_participants_eoy", *tie_break_columns],
            ascending=[
                True,
                False,
                True,
                True,
                True,
                True,
                True,
                True,
                False,
                False,
            ],
            na_position="last",
            kind="mergesort",
        )
        .drop_duplicates("sponsor_ein", keep="first")
        .drop(columns=["_plan_entity_stratum"])
    )
    out = chosen.merge(
        sponsor_metadata,
        on="sponsor_ein",
        how="left",
        validate="one_to_one",
    )
    no_positive_active = out["active_participants_eoy"].isna() | (
        out["active_participants_eoy"] < 1
    )
    out = out.loc[~no_positive_active].copy()
    out["observation_unit"] = "plan_sponsor_ein"
    out = out.sort_values("sponsor_ein", kind="mergesort").reset_index(drop=True)
    out.attrs["aggregation"] = {
        "source_rows": int(rows_in),
        "invalid_ein_rows_dropped": int(invalid_ein.sum()),
        "sponsors_without_positive_active_participants_dropped": int(
            no_positive_active.sum()
        ),
        "sponsors_out": int(len(out)),
        "deduplication_rule": (
            "maximum end-of-year active participants; all selected metadata "
            "comes from the same filing; equal maxima use lexical source "
            "form, full NAICS, state, entity code system/code, and filename, "
            "then descending beginning-of-year participant counts"
        ),
        "single_employer_filter_applied": False,
    }
    out.attrs["measurement_model"] = {
        "observation_unit": "plan_sponsor_ein",
        "employment_measure": "maximum overlapping active plan participants",
        "participant_timing": "end_of_year",
        "employment_proxy_relation": "not_ordered_across_plan_entity_strata",
        "enterprise_reconciliation": "not_resolved",
    }
    return out
