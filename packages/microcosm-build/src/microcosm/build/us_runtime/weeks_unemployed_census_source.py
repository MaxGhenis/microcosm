"""Verify carried ASEC ``LKWEEKS`` against each pooled year's Census member.

Every pinned processed ASEC HDF5 except income year 2022 carries person-level
``LKWEEKS``, and source construction copies it into the pooled frame verbatim
(:mod:`.asec_pool` keeps every H5 person column). Only income year 2022 is
repaired, from the pinned ``asecpub23csv.zip`` sidecar, by
:func:`.weeks_unemployed.fill_asec_2022_weeks_unemployed_source`.

A pool without income year 2022 therefore needs no sidecar. Its raw-stage
artifact still has to say where ``LKWEEKS`` came from, and it says it with the
same exact ``(source_year, PERIDNUM)`` join the ``ED_VAL`` and ``PAW_TYP``
mappings use, against the same pinned Census person member of each pooled
year (:data:`.spm_role_source.ASEC_SPM_ROLE_SOURCES`, whose coordinates are
:data:`.education_assistance_source.ASEC_EDUCATION_ASSISTANCE_ARCHIVES`).
The join verifies and never fills. A pooled row whose carried value is
missing, invalid, or different from its Census person is refused. The base
build's pre-clone stages read the source-construction frame, not the raw-stage
artifact, so a value filled here would be one the base build never uses.

The member is read through
:func:`.spm_role_source.read_pinned_asec_person_columns`, the verified reader
the SPM role stage and the #720 Census person-column restore share. It accepts
the official archive or its extracted person CSV and re-hashes after reading.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from microcosm.build.us_runtime.spm_role_source import (
    ASEC_SPM_ROLE_SOURCES,
    AsecSpmRoleSource,
    _exact_person_keys,
    read_pinned_asec_person_columns,
)

__all__ = [
    "ASEC_WEEKS_UNEMPLOYED_CENSUS_COLUMNS",
    "ASEC_WEEKS_UNEMPLOYED_CENSUS_IDENTITY_COLUMNS",
    "load_asec_weeks_unemployed_census_sources",
    "verify_asec_weeks_unemployed_census_sources",
]

_SOURCE = "LKWEEKS"
_JOIN_KEY = "PERIDNUM"
_EXAMPLES = 5

#: Census identity carried by both the pooled frame and the person member.
#: After the exact key join each must agree row for row, so a join that pairs
#: the wrong people cannot pass on a coincidence of keys.
ASEC_WEEKS_UNEMPLOYED_CENSUS_IDENTITY_COLUMNS: tuple[str, ...] = (
    "PH_SEQ",
    "P_SEQ",
    "A_LINENO",
)
ASEC_WEEKS_UNEMPLOYED_CENSUS_COLUMNS: tuple[str, ...] = (
    _JOIN_KEY,
    *ASEC_WEEKS_UNEMPLOYED_CENSUS_IDENTITY_COLUMNS,
    _SOURCE,
)


def _examples(values: pd.Series | pd.Index | np.ndarray) -> list[str]:
    return [str(value) for value in list(values)[:_EXAMPLES]]


def _is_integer(values: pd.Series) -> bool:
    return pd.api.types.is_integer_dtype(values) and not pd.api.types.is_bool_dtype(
        values
    )


def _integer_values(values: pd.Series, *, label: str) -> np.ndarray:
    """Return exact integers, refusing missing, fractional, or non-numeric values."""

    if pd.api.types.is_bool_dtype(values):
        raise ValueError(f"{label} must be complete finite integers, not booleans.")
    # A boolean inside an object column would otherwise coerce to 0 or 1.
    boolean = values.map(lambda value: isinstance(value, (bool, np.bool_))).to_numpy(
        dtype=bool
    )
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=np.float64)
    valid = np.isfinite(numeric) & np.equal(numeric, np.floor(numeric)) & ~boolean
    if not valid.all():
        rows = values.index[~valid]
        raise ValueError(
            f"{label} must be complete finite integers; {int((~valid).sum())} "
            f"row(s) are not, e.g. at {_examples(rows)}."
        )
    return numeric.astype(np.int64)


def load_asec_weeks_unemployed_census_sources(
    paths: Mapping[int, str | Path],
    *,
    income_years: tuple[int, ...],
    pins: Mapping[int, AsecSpmRoleSource] | None = None,
) -> pd.DataFrame:
    """Read ``PERIDNUM``, identity, and ``LKWEEKS`` from each pinned member.

    Args:
        paths: One official Census survey archive or extracted person CSV per
            income year, in the ``--asec-education-source`` vocabulary (the
            paths :func:`.spm_independence_role.resolve_asec_spm_role_source_paths`
            returns).
        income_years: The pooled income years to read.
        pins: Reviewed member pins; defaults to
            :data:`.spm_role_source.ASEC_SPM_ROLE_SOURCES`.

    Returns:
        One row per member person with ``source_year`` and the columns of
        :data:`ASEC_WEEKS_UNEMPLOYED_CENSUS_COLUMNS`. ``attrs["member_rows"]``
        maps each income year to its member's person count.

    Raises:
        ValueError: An unpinned year or a year without a path; a member that
            fails its pins; a person count that differs from the pin; a
            ``PERIDNUM`` that is not a unique exact 22-digit string; or an
            identity or ``LKWEEKS`` value that is missing, not an integer, or
            (for ``LKWEEKS``) outside ``{-1, 0, ..., 52}``.
    """

    registry = ASEC_SPM_ROLE_SOURCES if pins is None else pins
    years = tuple(sorted({int(year) for year in income_years}))
    if not years:
        raise ValueError("ASEC LKWEEKS census verification needs an income year.")
    frames: list[pd.DataFrame] = []
    member_rows: dict[int, int] = {}
    for year in years:
        pin = registry.get(year)
        if pin is None:
            raise ValueError(
                f"No pinned Census ASEC person member covers income year {year}; "
                f"pinned income years: {sorted(registry)}."
            )
        if pin.income_year != year or pin.survey_year != year + 1:
            raise ValueError(
                f"Census ASEC person pin is for income year {pin.income_year} "
                f"(survey {pin.survey_year}), not income year {year}."
            )
        if year not in paths:
            raise ValueError(
                f"No Census ASEC person member path was supplied for income year "
                f"{year}."
            )
        label = f"ASEC {pin.survey_year} {pin.member} LKWEEKS member"
        try:
            source, _form = read_pinned_asec_person_columns(
                Path(paths[year]),
                pin,
                label,
                ASEC_WEEKS_UNEMPLOYED_CENSUS_COLUMNS,
            )
        except ValueError as error:
            # Pin mismatches arrive labelled; a member header without one of
            # the columns arrives as pandas' unlabelled usecols message.
            message = str(error)
            raise ValueError(
                message if message.startswith(label) else f"{label}: {message}"
            ) from error
        if len(source) != pin.persons:
            raise ValueError(
                f"{label} holds {len(source)} persons; the pin records {pin.persons}."
            )
        source[_JOIN_KEY] = _exact_person_keys(source[_JOIN_KEY], label)
        duplicated = source[_JOIN_KEY].duplicated(keep=False)
        if duplicated.any():
            raise ValueError(
                f"{label} repeats {int(duplicated.sum())} PERIDNUM rows, e.g. "
                f"{_examples(source.loc[duplicated, _JOIN_KEY].drop_duplicates())}."
            )
        for column in (*ASEC_WEEKS_UNEMPLOYED_CENSUS_IDENTITY_COLUMNS, _SOURCE):
            if not _is_integer(source[column]):
                raise ValueError(
                    f"{label} column {column} parsed as {source[column].dtype}, not "
                    "integer: the member has blank, fractional or text values there."
                )
        weeks = source[_SOURCE].to_numpy(dtype=np.int64)
        outside = ~((weeks == -1) | ((weeks >= 0) & (weeks <= 52)))
        if outside.any():
            raise ValueError(
                f"{label} LKWEEKS has {int(outside.sum())} values outside "
                f"{{-1, 0, ..., 52}}, e.g. {_examples(np.unique(weeks[outside]))}."
            )
        source.insert(0, "source_year", np.full(len(source), year, dtype=np.int64))
        frames.append(source)
        member_rows[year] = int(len(source))
    result = pd.concat(frames, ignore_index=True)
    result.attrs["member_rows"] = member_rows
    return result


def verify_asec_weeks_unemployed_census_sources(
    person: pd.DataFrame,
    source: pd.DataFrame,
) -> dict[str, dict[str, int]]:
    """Verify every pooled row's carried ``LKWEEKS`` against its Census person.

    The person table is read, never modified. For each income year in
    ``person["source_year"]`` the rows' ``PERIDNUM`` keys must be unique exact
    22-digit strings present in that year's member, the redundant identity
    columns must agree row for row, and the carried ``LKWEEKS`` must be a
    complete integer equal to the member's value.

    Args:
        person: The pooled person table after source construction.
        source: :func:`load_asec_weeks_unemployed_census_sources` output.

    Returns:
        A per-year audit keyed by the income year as a string, each entry with
        integer ``rows`` (frame rows of that year), ``verified_rows`` (rows
        whose carried value equals the member; always ``rows``),
        ``member_rows``, ``positive_rows``, ``niu_rows`` (value ``-1``),
        ``minimum`` and ``maximum``. The summed ``rows`` equal ``len(person)``.

    Raises:
        ValueError: A missing column, an income year the source does not
            cover, a repeated or uncovered key, an identity mismatch, or a
            carried value that is missing, invalid, or differs from the member.
    """

    missing_person = [
        column
        for column in (
            "source_year",
            _JOIN_KEY,
            _SOURCE,
            "P_SEQ",
            "A_LINENO",
        )
        if column not in person
    ]
    if "source_household_id" not in person and "PH_SEQ" not in person:
        missing_person.append("source_household_id or PH_SEQ")
    if missing_person:
        raise ValueError(
            "ASEC LKWEEKS census verification requires person column(s) "
            f"{missing_person}. Only income year 2022 lacks LKWEEKS, and a pool "
            "containing it restores the column from the pinned sidecar instead."
        )
    missing_source = [
        column
        for column in ("source_year", *ASEC_WEEKS_UNEMPLOYED_CENSUS_COLUMNS)
        if column not in source
    ]
    if missing_source:
        raise ValueError(
            f"ASEC LKWEEKS census source is missing column(s): {missing_source}."
        )
    member_rows = source.attrs.get("member_rows")
    if not isinstance(member_rows, Mapping):
        raise ValueError(
            "ASEC LKWEEKS census source lacks its member_rows audit; load it "
            "with load_asec_weeks_unemployed_census_sources."
        )

    years = _integer_values(person["source_year"], label="ASEC frame source_year")
    source_years = _integer_values(
        source["source_year"], label="ASEC LKWEEKS census source_year"
    )
    uncovered = sorted(set(years.tolist()) - set(source_years.tolist()))
    if uncovered:
        raise ValueError(
            "ASEC LKWEEKS census source does not cover pooled income year(s) "
            f"{uncovered}."
        )
    weeks = _integer_values(person[_SOURCE], label="Carried ASEC LKWEEKS")
    household_column = (
        "source_household_id" if "source_household_id" in person else "PH_SEQ"
    )
    audit: dict[str, dict[str, int]] = {}
    for year in sorted(set(years.tolist())):
        label = f"ASEC income year {year}"
        year_mask = years == year
        keys = _exact_person_keys(
            person.loc[year_mask, _JOIN_KEY].reset_index(drop=True),
            f"{label} frame",
        )
        duplicated = keys.duplicated(keep=False)
        if duplicated.any():
            raise ValueError(
                f"{label} frame repeats {int(duplicated.sum())} PERIDNUM rows, "
                f"e.g. {_examples(keys[duplicated].drop_duplicates())}."
            )
        member = source.loc[source_years == year].reset_index(drop=True)
        member_index = pd.Index(member[_JOIN_KEY])
        positions = member_index.get_indexer(keys)
        absent = positions < 0
        if absent.any():
            raise ValueError(
                f"{int(absent.sum())} {label} frame persons have no row in its "
                f"Census member, e.g. PERIDNUM {_examples(keys[absent])}."
            )
        aligned = member.iloc[positions].reset_index(drop=True)
        frame_rows = person.index[year_mask]
        for member_column, frame_column in (
            ("PH_SEQ", household_column),
            ("P_SEQ", "P_SEQ"),
            ("A_LINENO", "A_LINENO"),
        ):
            observed = _integer_values(
                person.loc[year_mask, frame_column],
                label=f"{label} frame {frame_column}",
            )
            expected = aligned[member_column].to_numpy(dtype=np.int64)
            mismatch = observed != expected
            if mismatch.any():
                raise ValueError(
                    f"{label} redundant identity mismatch for {frame_column} "
                    f"against Census {member_column} at frame row(s): "
                    f"{_examples(frame_rows[mismatch])}."
                )
        carried = weeks[year_mask]
        expected_weeks = aligned[_SOURCE].to_numpy(dtype=np.int64)
        disagree = carried != expected_weeks
        if disagree.any():
            raise ValueError(
                f"{label} carried LKWEEKS disagrees with its Census member at "
                f"{int(disagree.sum())} row(s), e.g. frame row(s) "
                f"{_examples(frame_rows[disagree])}."
            )
        count = int(year_mask.sum())
        audit[str(year)] = {
            "maximum": int(carried.max()),
            "member_rows": int(member_rows[year]),
            "minimum": int(carried.min()),
            "niu_rows": int((carried == -1).sum()),
            "positive_rows": int((carried > 0).sum()),
            "rows": count,
            "verified_rows": count,
        }
    covered = sum(entry["rows"] for entry in audit.values())
    if covered != len(person):
        raise AssertionError(
            f"ASEC LKWEEKS census verification covered {covered} of "
            f"{len(person)} person rows."
        )
    return audit
