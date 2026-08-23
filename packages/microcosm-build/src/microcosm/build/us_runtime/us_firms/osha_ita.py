"""Reader for OSHA ITA Form 300A establishment summaries.

OSHA ITA is an independent establishment-level measurement reference, not a
donor pool for the Form 5500 sponsor frame.  Its reporting universe is selected
by establishment size and industry.  The loader therefore preserves raw
employment and emits quality flags but removes no records.  A consumer that
wants a cleaned reference must call :func:`apply_quality_rule` with an explicit
employee cap.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .form5500 import FIRM_DATA_DIR_ENV, firm_data_dir

__all__ = [
    "ITA_COLUMNS",
    "MAX_ANNUAL_HOURS_PER_EMPLOYEE",
    "apply_quality_rule",
    "read_ita",
]

MAX_ANNUAL_HOURS_PER_EMPLOYEE = 8_760

# Verified against the OSHA ITA summary data dictionary.  ``ID`` identifies a
# submission record; ``establishment_ID`` identifies the establishment.  They
# are separate provenance fields and neither may be reconstructed from EIN.
ITA_COLUMNS = {
    "ID": "record_id",
    "establishment_ID": "establishment_id",
    "ein": "ein",
    "company_name": "company_name",
    "establishment_name": "establishment_name",
    "state": "state",
    "naics_code": "naics_code",
    "naics_year": "naics_year",
    "annual_average_employees": "annual_average_employees",
    "total_hours_worked": "total_hours_worked",
    "establishment_type": "establishment_type",
    "year_filing_for": "year_filing_for",
}

_OWNERSHIP_BY_ESTABLISHMENT_TYPE = {
    "1": "private_industry",
    "2": "state_government",
    "3": "local_government",
}

_STAGING_HINT = (
    "Stage the pinned OSHA ITA summary under ~/PolicyEngine/firm-data "
    f"(or set {FIRM_DATA_DIR_ENV})."
)


def _strict_ein(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    valid = text.str.fullmatch(r"\d{1,9}") | text.str.fullmatch(r"\d{2}-\d{7}")
    return text.where(valid).str.replace("-", "", regex=False).str.zfill(9)


def _strict_naics(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    return text.where(text.str.fullmatch(r"\d{6}"))


def _check_columns(path: Path) -> None:
    header = pd.read_csv(path, nrows=0)
    missing = [column for column in ITA_COLUMNS if column not in header.columns]
    if missing:
        raise ValueError(
            f"OSHA ITA file {path.name} is missing columns {missing}; the "
            "published schema changed and the reader must be re-verified "
            "against the ITA data dictionary."
        )


def _validate_filing_year(series: pd.Series, *, requested_year: int) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    invalid = numeric.isna() | ~np.isfinite(numeric) | numeric.ne(np.floor(numeric))
    if bool(invalid.any()):
        raise ValueError(
            "OSHA ITA year_filing_for contains missing or non-integral values; "
            "the requested source year cannot be verified."
        )
    years = numeric.astype("int64")
    mismatch = years.ne(int(requested_year))
    if bool(mismatch.any()):
        observed = sorted({int(value) for value in years[mismatch].unique()})
        raise ValueError(
            f"OSHA ITA file requested for {requested_year} contains "
            f"year_filing_for values {observed}."
        )
    return years


def read_ita(
    year: int,
    data_dir: Path | None = None,
    *,
    filename: str | None = None,
) -> pd.DataFrame:
    """Read raw Form 300A summaries and attach non-destructive quality flags.

    The requested year must match every ``year_filing_for`` value.  Employment
    is not capped or filtered, including zeros, fractional values, and extreme
    reports.  ``bandable`` merely identifies positive whole-number counts;
    band labels remain a dynamics-seam concern and are not created here.
    """
    root = data_dir if data_dir is not None else firm_data_dir()
    name = filename or f"ITA_300A_Summary_Data_{year}.csv"
    path = root / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. {_STAGING_HINT}")
    _check_columns(path)

    frame = pd.read_csv(
        path,
        usecols=list(ITA_COLUMNS),
        dtype={
            "ID": "string",
            "establishment_ID": "string",
            "ein": "string",
            "naics_code": "string",
            "establishment_type": "string",
        },
        low_memory=False,
    )
    out = frame.rename(columns=ITA_COLUMNS).copy()
    out["record_id"] = out["record_id"].str.strip()
    out["establishment_id"] = out["establishment_id"].str.strip()
    out["ein"] = _strict_ein(out["ein"])
    out["naics_code"] = _strict_naics(out["naics_code"])
    out["naics_sector"] = out["naics_code"].str[:2]
    out["state"] = out["state"].astype("string").str.strip().str.upper()
    out["establishment_type"] = (
        out["establishment_type"].astype("string").str.strip()
    )
    ownership = out["establishment_type"].map(
        _OWNERSHIP_BY_ESTABLISHMENT_TYPE
    )
    out["ownership"] = ownership.mask(
        out["establishment_type"].notna() & ownership.isna(), "unmapped"
    )
    out["year_filing_for"] = _validate_filing_year(
        out["year_filing_for"], requested_year=year
    )

    employment = pd.to_numeric(
        out["annual_average_employees"], errors="coerce"
    )
    hours = pd.to_numeric(out["total_hours_worked"], errors="coerce")
    out["annual_average_employees"] = employment
    out["total_hours_worked"] = hours
    hours_per_employee = (hours / employment.where(employment > 0)).where(
        hours >= 0
    )
    out["hours_per_employee"] = hours_per_employee
    out["hours_implausible"] = hours_per_employee.gt(
        MAX_ANNUAL_HOURS_PER_EMPLOYEE
    ).fillna(False)
    out["bandable"] = (
        employment.notna()
        & np.isfinite(employment)
        & employment.ge(1)
        & employment.eq(np.floor(employment))
    )
    out["source_year"] = int(year)
    out["source_filename"] = name
    out["observation_unit"] = "osha_establishment_submission"
    out["employment_measure"] = "annual_average_employees"
    out["employment_timing"] = "calendar_year_average"
    out.attrs["measurement_model"] = {
        "observation_unit": "osha_establishment_submission",
        "employment_measure": "annual_average_employees",
        "employment_timing": "calendar_year_average",
        "reporting_universe": "osha_ita_reporting_requirements",
        "cleaning_applied": False,
        "frame_role": "independent_measurement_reference",
    }
    return out


def apply_quality_rule(
    frame: pd.DataFrame,
    *,
    max_employees: int,
    drop_hours_implausible: bool = True,
) -> pd.DataFrame:
    """Apply an explicit OSHA employment-quality rule.

    ``max_employees`` intentionally has no default.  The cap is a consequential
    referee choice and must be present in every calling artifact.  Removal
    categories are disjoint and evaluated in this order: unbandable count,
    physically implausible hours (when requested), then employee cap.  The
    complete rule and its effects are attached at ``attrs['quality_rule']``.
    """
    if (
        isinstance(max_employees, bool)
        or not isinstance(max_employees, (int, np.integer))
        or max_employees < 1
    ):
        raise ValueError("max_employees must be an integer >= 1.")
    required = (
        "annual_average_employees",
        "bandable",
        "hours_implausible",
    )
    missing = [column for column in required if column not in frame]
    if missing:
        raise ValueError(
            f"Frame lacks {missing}; pass the output of read_ita()."
        )

    employment = frame["annual_average_employees"]
    keep = frame["bandable"].fillna(False).astype(bool)
    dropped_unbandable = int((~keep).sum())

    dropped_hours = 0
    if drop_hours_implausible:
        hours_bad = frame["hours_implausible"].fillna(False).astype(bool)
        dropped_hours = int((keep & hours_bad).sum())
        keep &= ~hours_bad

    above_cap = employment > int(max_employees)
    dropped_above_cap = int((keep & above_cap.fillna(False)).sum())
    keep &= ~above_cap.fillna(False)

    out = frame.loc[keep].copy()
    employment_out = out["annual_average_employees"].sum()
    out.attrs["quality_rule"] = {
        "rule_id": "explicit_employee_cap_and_hours_consistency",
        "max_employees": int(max_employees),
        "drop_hours_implausible": bool(drop_hours_implausible),
        "max_annual_hours_per_employee": MAX_ANNUAL_HOURS_PER_EMPLOYEE,
        "rows_in": int(len(frame)),
        "rows_out": int(len(out)),
        "dropped_unbandable": dropped_unbandable,
        "dropped_hours_implausible": dropped_hours,
        "dropped_above_max_employees": dropped_above_cap,
        "employment_in": float(employment.sum()),
        "employment_out": float(employment_out),
        "banding_applied": False,
    }
    return out
