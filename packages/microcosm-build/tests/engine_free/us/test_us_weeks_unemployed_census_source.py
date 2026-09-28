"""Verify-only Census join for carried ASEC ``LKWEEKS`` (pools without 2022).

A pool without income year 2022 reads no LKWEEKS sidecar: every pooled H5
carries the column. The raw stage binds it to each pooled year's pinned Census
person member through
:mod:`microcosm.build.us_runtime.weeks_unemployed_census_source`, which reads
the member through the shared verified reader and refuses any carried value
that is missing or differs. These tests pin the reader's refusals, the join's
audit and refusals, the join's for-all properties, and its agreement with the
legacy income-2022 sidecar fill on frames both can check.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from microcosm.build.us_runtime.spm_role_source import AsecSpmRoleSource
from microcosm.build.us_runtime.weeks_unemployed import (
    fill_asec_2022_weeks_unemployed_source,
)
from microcosm.build.us_runtime.weeks_unemployed_census_source import (
    ASEC_WEEKS_UNEMPLOYED_CENSUS_COLUMNS,
    load_asec_weeks_unemployed_census_sources,
    verify_asec_weeks_unemployed_census_sources,
)

_YEARS = (2023, 2024, 2025)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _member(year: int, rows: int = 6) -> pd.DataFrame:
    """A complete synthetic Census person member for one income year."""

    offset = (year - 2000) * 1_000
    return pd.DataFrame(
        {
            # Leading zeros: a numeric parse would change the key.
            "PERIDNUM": [f"{offset + number:022}" for number in range(rows)],
            "PH_SEQ": [1 + number // 2 for number in range(rows)],
            "P_SEQ": [1 + number % 2 for number in range(rows)],
            "A_LINENO": [1 + number % 2 for number in range(rows)],
            "A_AGE": [30 + number for number in range(rows)],
            "LKWEEKS": [
                (number * 7) % 53 - (1 if number == 3 else 0) for number in range(rows)
            ],
        }
    )


def _write(tmp_path: Path, year: int, member: pd.DataFrame):
    """Write ``member`` as a CSV and as a Census-style archive; return their pin."""

    survey = (year + 1) % 100
    name = f"pppub{survey:02d}.csv"
    directory = tmp_path / str(year)
    directory.mkdir(parents=True, exist_ok=True)
    csv = directory / name
    member.to_csv(csv, index=False)
    archive = directory / f"asecpub{survey:02d}csv.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as out:
        out.write(csv, arcname=name)
        out.writestr(f"hhpub{survey:02d}.csv", "H_SEQ\n1\n")
    pin = AsecSpmRoleSource(
        income_year=year,
        survey_year=year + 1,
        csv_sha256=_digest(csv),
        csv_size_bytes=csv.stat().st_size,
        persons=len(member),
        units=0,
        official_archive_url=f"https://example.invalid/asecpub{survey:02d}csv.zip",
        archive_sha256=_digest(archive),
        member=name,
    )
    return csv, archive, pin


def _frame_from_members(members: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """The pooled person table source construction would carry: H5 == member."""

    parts = []
    for year, member in sorted(members.items()):
        part = member.drop(columns=["PH_SEQ", "A_AGE"]).copy()
        part.insert(0, "source_year", np.int64(year))
        part.insert(1, "source_household_id", member["PH_SEQ"].to_numpy())
        # Reverse the rows: the join must key, never copy by position.
        parts.append(part.iloc[::-1])
    return pd.concat(parts, ignore_index=True)


def _census_source(members: dict[int, pd.DataFrame]) -> pd.DataFrame:
    parts = []
    for year, member in sorted(members.items()):
        part = member[list(ASEC_WEEKS_UNEMPLOYED_CENSUS_COLUMNS)].copy()
        part.insert(0, "source_year", np.int64(year))
        parts.append(part)
    source = pd.concat(parts, ignore_index=True)
    source.attrs["member_rows"] = {
        year: int(len(member)) for year, member in members.items()
    }
    return source


# -- the reader --------------------------------------------------------------


@pytest.mark.parametrize("form", ["csv", "archive"])
def test_loader_reads_each_pinned_member_in_either_form(
    tmp_path: Path, form: str
) -> None:
    members = {year: _member(year, rows=4 + index) for index, year in enumerate(_YEARS)}
    paths = {}
    pins = {}
    for year, member in members.items():
        csv, archive, pin = _write(tmp_path, year, member)
        paths[year] = csv if form == "csv" else archive
        pins[year] = pin

    source = load_asec_weeks_unemployed_census_sources(
        paths, income_years=(2025, 2023, 2024), pins=pins
    )

    assert source.attrs["member_rows"] == {2023: 4, 2024: 5, 2025: 6}
    assert source["source_year"].tolist() == [2023] * 4 + [2024] * 5 + [2025] * 6
    assert list(source.columns) == [
        "source_year",
        *ASEC_WEEKS_UNEMPLOYED_CENSUS_COLUMNS,
    ]
    expected = pd.concat(
        [members[year]["LKWEEKS"] for year in _YEARS], ignore_index=True
    )
    assert source["LKWEEKS"].tolist() == expected.tolist()
    # Leading zeros survive: keys are read as text.
    assert source["PERIDNUM"].str.len().eq(22).all()


def test_loader_refuses_an_unpinned_or_unmapped_year(tmp_path: Path) -> None:
    csv, _archive, pin = _write(tmp_path, 2023, _member(2023))
    with pytest.raises(ValueError, match="No pinned Census ASEC person member"):
        load_asec_weeks_unemployed_census_sources(
            {2024: csv}, income_years=(2024,), pins={2023: pin}
        )
    with pytest.raises(ValueError, match="No Census ASEC person member path"):
        load_asec_weeks_unemployed_census_sources(
            {}, income_years=(2023,), pins={2023: pin}
        )
    with pytest.raises(ValueError, match="needs an income year"):
        load_asec_weeks_unemployed_census_sources(
            {2023: csv}, income_years=(), pins={2023: pin}
        )


def test_loader_refuses_a_pin_for_another_income_year(tmp_path: Path) -> None:
    csv, _archive, pin = _write(tmp_path, 2023, _member(2023))
    with pytest.raises(ValueError, match="is for income year 2023"):
        load_asec_weeks_unemployed_census_sources(
            {2024: csv}, income_years=(2024,), pins={2024: pin}
        )


def test_loader_refuses_bytes_that_differ_from_the_pin(tmp_path: Path) -> None:
    csv, archive, pin = _write(tmp_path, 2023, _member(2023))
    csv.write_text(csv.read_text().replace(",7\n", ",8\n"))
    with pytest.raises(ValueError, match="LKWEEKS member CSV"):
        load_asec_weeks_unemployed_census_sources(
            {2023: csv}, income_years=(2023,), pins={2023: pin}
        )
    archive.write_bytes(archive.read_bytes() + b"\0")
    with pytest.raises(ValueError, match="archive SHA-256 mismatch"):
        load_asec_weeks_unemployed_census_sources(
            {2023: archive}, income_years=(2023,), pins={2023: pin}
        )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda m: m.drop(columns=["LKWEEKS"]), "LKWEEKS member: .*LKWEEKS"),
        (
            lambda m: m.assign(LKWEEKS=[*m.LKWEEKS[:-1], 53]),
            r"outside \{-1, 0, \.\.\., 52\}",
        ),
        (
            lambda m: m.assign(LKWEEKS=[*m.LKWEEKS[:-1], None]),
            "LKWEEKS parsed as float64",
        ),
        (lambda m: m.assign(P_SEQ=[*m.P_SEQ[:-1], 1.5]), "P_SEQ parsed as float64"),
        (
            lambda m: m.assign(PERIDNUM=[*m.PERIDNUM[:-1], m.PERIDNUM.iloc[0]]),
            "repeats 2 PERIDNUM rows",
        ),
        (
            lambda m: m.assign(PERIDNUM=[*m.PERIDNUM[:-1], "123"]),
            "exact 22-digit strings",
        ),
    ],
    ids=[
        "missing-column",
        "out-of-domain",
        "blank",
        "fractional-identity",
        "repeated-key",
        "short-key",
    ],
)
def test_loader_refuses_an_invalid_member(tmp_path: Path, mutate, message: str) -> None:
    member = mutate(_member(2023))
    csv, _archive, pin = _write(tmp_path, 2023, member)
    with pytest.raises(ValueError, match=message):
        load_asec_weeks_unemployed_census_sources(
            {2023: csv}, income_years=(2023,), pins={2023: pin}
        )


def test_loader_refuses_a_member_whose_person_count_differs(tmp_path: Path) -> None:
    csv, _archive, pin = _write(tmp_path, 2023, _member(2023))
    short = AsecSpmRoleSource(**{**pin.__dict__, "persons": pin.persons + 1})
    with pytest.raises(ValueError, match="the pin records 7"):
        load_asec_weeks_unemployed_census_sources(
            {2023: csv}, income_years=(2023,), pins={2023: short}
        )


# -- the join ----------------------------------------------------------------


def test_join_verifies_every_row_and_audits_each_year() -> None:
    members = {2023: _member(2023, rows=6), 2025: _member(2025, rows=4)}
    person = _frame_from_members(members)
    before = person.copy(deep=True)

    audit = verify_asec_weeks_unemployed_census_sources(person, _census_source(members))

    pd.testing.assert_frame_equal(person, before)
    assert audit == {
        "2023": {
            "maximum": 35,
            "member_rows": 6,
            "minimum": 0,
            "niu_rows": 0,
            "positive_rows": 5,
            "rows": 6,
            "verified_rows": 6,
        },
        "2025": {
            "maximum": 20,
            "member_rows": 4,
            "minimum": 0,
            "niu_rows": 0,
            "positive_rows": 3,
            "rows": 4,
            "verified_rows": 4,
        },
    }


def test_join_counts_a_partial_frame_against_the_whole_member() -> None:
    # --asec-max-households keeps a subset of each member's persons.
    members = {2024: _member(2024, rows=8)}
    person = _frame_from_members(members).iloc[:3].reset_index(drop=True)
    audit = verify_asec_weeks_unemployed_census_sources(person, _census_source(members))
    assert audit["2024"]["rows"] == audit["2024"]["verified_rows"] == 3
    assert audit["2024"]["member_rows"] == 8


def _mutated(column: str, value: object):
    def mutate(person: pd.DataFrame) -> pd.DataFrame:
        result = person.copy()
        result[column] = result[column].astype(object)
        result.loc[2, column] = value
        return result

    return mutate


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (_mutated("LKWEEKS", 51), "carried LKWEEKS disagrees"),
        (_mutated("LKWEEKS", np.nan), "Carried ASEC LKWEEKS must be complete"),
        (_mutated("LKWEEKS", 2.5), "Carried ASEC LKWEEKS must be complete"),
        (_mutated("LKWEEKS", True), "Carried ASEC LKWEEKS must be complete"),
        (_mutated("P_SEQ", 9), "identity mismatch for P_SEQ"),
        (_mutated("A_LINENO", 9), "identity mismatch for A_LINENO"),
        (
            _mutated("source_household_id", 99),
            "identity mismatch for source_household_id",
        ),
        (_mutated("PERIDNUM", "9" * 22), "have no row in its Census member"),
        (
            lambda p: p.assign(
                PERIDNUM=[p.PERIDNUM.iloc[0]] * 2 + list(p.PERIDNUM[2:])
            ),
            "frame repeats 2 PERIDNUM rows",
        ),
        (
            lambda p: p.drop(columns=["LKWEEKS"]),
            r"requires person column\(s\) \['LKWEEKS'\]",
        ),
        (
            lambda p: p.assign(source_year=np.int64(2022)),
            r"does not cover pooled income year\(s\) \[2022\]",
        ),
    ],
    ids=[
        "different-value",
        "missing-value",
        "fractional-value",
        "boolean-value",
        "p-seq",
        "a-lineno",
        "household",
        "absent-key",
        "repeated-key",
        "missing-column",
        "uncovered-year",
    ],
)
def test_join_refuses_what_it_cannot_verify(mutate, message: str) -> None:
    members = {2023: _member(2023)}
    person = mutate(_frame_from_members(members))
    with pytest.raises(ValueError, match=message):
        verify_asec_weeks_unemployed_census_sources(person, _census_source(members))


def test_join_requires_the_loaders_member_rows_audit() -> None:
    members = {2023: _member(2023)}
    source = _census_source(members)
    source.attrs.clear()
    with pytest.raises(ValueError, match="member_rows audit"):
        verify_asec_weeks_unemployed_census_sources(
            _frame_from_members(members), source
        )


@st.composite
def _pools(draw):
    """A pooled frame drawn from members of a subset of the pinned years."""

    years = draw(st.sets(st.sampled_from(_YEARS), min_size=1))
    members = {}
    chosen = {}
    for year in sorted(years):
        rows = draw(st.integers(min_value=1, max_value=12))
        weeks = draw(
            st.lists(
                st.integers(min_value=-1, max_value=52), min_size=rows, max_size=rows
            )
        )
        member = _member(year, rows=rows).assign(LKWEEKS=weeks)
        members[year] = member
        chosen[year] = draw(
            st.lists(
                st.integers(min_value=0, max_value=rows - 1),
                min_size=1,
                max_size=rows,
                unique=True,
            )
        )
    frame = pd.concat(
        [
            _frame_from_members({year: members[year].iloc[rows]})
            for year, rows in chosen.items()
        ],
        ignore_index=True,
    )
    order = draw(st.permutations(list(range(len(frame)))))
    return members, frame.iloc[order].reset_index(drop=True)


@settings(max_examples=200, deadline=None)
@given(pool=_pools())
def test_join_properties_hold_for_every_verified_pool(pool) -> None:
    members, person = pool
    source = _census_source(members)
    before = person.copy(deep=True)

    audit = verify_asec_weeks_unemployed_census_sources(person, source)

    # The person table is read, never written.
    pd.testing.assert_frame_equal(person, before)
    # One entry per frame year; rows == verified == the frame count, summing
    # to the frame; member_rows is the member's size.
    counts = person["source_year"].value_counts()
    assert set(audit) == {str(year) for year in counts.index}
    assert sum(entry["rows"] for entry in audit.values()) == len(person)
    for year, entry in audit.items():
        values = person.loc[person["source_year"] == int(year), "LKWEEKS"]
        assert entry["rows"] == entry["verified_rows"] == int(counts[int(year)])
        assert entry["member_rows"] == len(members[int(year)])
        assert entry["minimum"] == int(values.min())
        assert entry["maximum"] == int(values.max())
        assert entry["niu_rows"] == int(values.eq(-1).sum())
        assert entry["positive_rows"] == int(values.gt(0).sum())
    # Deterministic.
    assert verify_asec_weeks_unemployed_census_sources(person, source) == audit


@settings(max_examples=200, deadline=None)
@given(pool=_pools(), data=st.data())
def test_join_refuses_any_single_perturbed_value(pool, data) -> None:
    members, person = pool
    row = data.draw(st.integers(min_value=0, max_value=len(person) - 1))
    original = int(person.loc[row, "LKWEEKS"])
    replacement = data.draw(
        st.integers(min_value=-1, max_value=52).filter(lambda value: value != original)
    )
    person.loc[row, "LKWEEKS"] = replacement
    with pytest.raises(ValueError, match="carried LKWEEKS disagrees"):
        verify_asec_weeks_unemployed_census_sources(person, _census_source(members))


@settings(max_examples=200, deadline=None)
@given(pool=_pools(), data=st.data())
def test_join_agrees_with_the_legacy_sidecar_check(pool, data) -> None:
    """Differential: on frames that carry LKWEEKS, both joins accept the same set.

    The legacy income-2022 fill also cross-checks values a frame already
    carries against its sidecar. Relabel one drawn year's rows as the sidecar
    year, optionally perturb one value, and both must accept or both refuse,
    leaving LKWEEKS unchanged when they accept.
    """

    members, person = pool
    year = data.draw(st.sampled_from(sorted(members)))
    rows = person.loc[person["source_year"] == year].reset_index(drop=True)
    if data.draw(st.booleans()):
        row = data.draw(st.integers(min_value=0, max_value=len(rows) - 1))
        rows.loc[row, "LKWEEKS"] = (int(rows.loc[row, "LKWEEKS"]) + 1) % 53
    sidecar = members[year][["PH_SEQ", "P_SEQ", "A_LINENO", "PERIDNUM", "LKWEEKS"]]

    def verify() -> bool:
        try:
            verify_asec_weeks_unemployed_census_sources(
                rows, _census_source({year: members[year]})
            )
        except ValueError:
            return False
        return True

    def legacy() -> pd.DataFrame | None:
        try:
            return fill_asec_2022_weeks_unemployed_source(
                rows.assign(source_year=np.int64(2022)), sidecar
            )
        except ValueError:
            return None

    filled = legacy()
    assert verify() is (filled is not None)
    if filled is not None:
        assert filled["LKWEEKS"].tolist() == rows["LKWEEKS"].tolist()
