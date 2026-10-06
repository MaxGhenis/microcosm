"""Frozen-support / warm-start selection recovery (microcosm#328).

These tests exercise the identity join that recovers a frozen support onto a
freshly-rebuilt base, and the refusal contract that forbids fabricated or
truncated selections. All fixtures are tiny synthetic frames — no network, no
large H5.

Location copies: ``clone_frame_for_location(frame, K)`` repeats every household
``K`` times and adds ``household_location_clone_index``. Each copy is a
distinct record, so a location-cloned base needs a selection naming copies
(the effective key gains the location column), a ``K = 1`` selection is refused
there, and ``K = 1`` behaviour is pinned byte-for-byte to the pre-location code
(``K1_SELECTION_GOLDEN``). The Hypothesis properties live in
``test_us_warm_start_selection_location_properties.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from microcosm.build.us_runtime.warm_start_selection import (
    DEFAULT_SELECTION_JOIN_KEY,
    SELECTION_JOIN_KEY_COLUMNS,
    SelectionSource,
    load_selection_source_from_h5,
    load_selection_source_from_manifest,
    select_frozen_support,
    write_selection_source_manifest,
)
from microcosm.frame import Frame
from test_support.microcosm_build.us_warm_start_selection import (
    LOCATED_JOIN_KEY,
    LOCATION_COLUMN,
    PRE_LOCATION_UNKNOWN_COLUMN_REFUSAL,
    all_copies_source,
    frame_from_records,
    frame_values,
    household_identities,
    k1_selection_transcript,
    located,
    mass_by_identity,
    pool_records,
    reassigned_ids,
    select_households,
    with_duplicated_household,
)

# A source ASEC household appears twice in the pool: clone 0 (asec channel) and
# clone 1 (puf_tax_detail channel). The identity that survives a base rebuild is
# (source_year, source_household_id, channel, clone) — never the assigned row id.
# The fixture builders live in test_support.microcosm_build.us_warm_start_selection.


def test__given_named_support__then_reduces_base_to_exactly_that_support() -> None:
    # Given a base pool and a source naming 3 of its 8 households (clone-aware)
    base = frame_from_records(pool_records())
    picks = [
        (2024, 11, "asec", 0),
        (2024, 22, "puf_tax_detail", 1),
        (2023, 44, "asec", 0),
    ]
    source = SelectionSource(
        join_key=DEFAULT_SELECTION_JOIN_KEY,
        identities=[list(p) for p in picks],
        provenance={"kind": "test"},
    )

    # When
    reduced, report = select_frozen_support(base, source)

    # Then exactly those households remain, and the report is clean
    assert reduced.n("household") == 3
    assert report.n_selected == 3
    assert report.n_unmapped == 0
    assert report.n_ambiguous == 0
    got = set(
        zip(
            reduced.table("household")["household_support_channel"].tolist(),
            reduced.table("household")["household_support_clone_index"].tolist(),
            strict=True,
        )
    )
    assert ("asec", 0) in got and ("puf_tax_detail", 1) in got


def test__given_reassigned_base_ids__then_recovers_the_same_support() -> None:
    # Given the same source records but assigned to DIFFERENT household ids
    records = pool_records()
    base = frame_from_records(records)
    reassigned = frame_from_records(reassigned_ids(records, [7, 5, 3, 1, 6, 4, 2, 0]))
    picks = [(2024, 11, "asec", 0), (2023, 11, "puf_tax_detail", 1)]
    source = SelectionSource(
        join_key=DEFAULT_SELECTION_JOIN_KEY,
        identities=[list(p) for p in picks],
        provenance={"kind": "test"},
    )

    # When
    from_ordered, _ = select_frozen_support(base, source)
    from_shuffled, _ = select_frozen_support(reassigned, source)

    # Then the identity join recovers the same support regardless of row order
    def support_ids(frame: Frame) -> set[tuple[int, int, str, int]]:
        p = frame.table("person")
        return set(
            zip(
                p["source_year"].tolist(),
                p["source_household_id"].tolist(),
                p["person_support_channel"].tolist(),
                p["person_support_clone_index"].tolist(),
                strict=True,
            )
        )

    assert support_ids(from_ordered) == support_ids(from_shuffled)
    assert from_ordered.n("household") == from_shuffled.n("household") == 2


def test__given_unmappable_identity__then_frozen_mode_refuses() -> None:
    # Given a source identity that does not exist in the base
    base = frame_from_records(pool_records())
    source = SelectionSource(
        join_key=DEFAULT_SELECTION_JOIN_KEY,
        identities=[[2024, 11, "asec", 0], [1999, 99, "asec", 0]],
        provenance={"kind": "test"},
    )

    # When / Then: it refuses loudly and returns nothing (no truncated selection)
    with pytest.raises(ValueError, match="unmapped"):
        select_frozen_support(base, source)


def test__given_key_missing_channel__then_refuses_non_unique_key() -> None:
    # Given a join key without the clone/channel component, a source household's
    # two clones collide, so the key is not unique in the base.
    base = frame_from_records(pool_records())
    source = SelectionSource(
        join_key=("source_year", "source_household_id"),
        identities=[[2024, 11], [2023, 44]],
        provenance={"kind": "test"},
    )

    # When / Then
    with pytest.raises(ValueError, match="unique"):
        select_frozen_support(base, source)


def test__given_ambiguous_source_row__then_refuses() -> None:
    # Given a base where two rows share the full identity key (a malformed base),
    # a matching source identity would be ambiguous.
    records = pool_records()
    dup = dict(records[0])
    dup["person_id"] = 999
    dup["household_id"] = 999
    dup["person_household_id"] = 999
    dup["person_tax_unit_id"] = 999
    dup["person_spm_unit_id"] = 999
    dup["person_family_id"] = 999
    dup["person_marital_unit_id"] = 999
    base = frame_from_records([*records, dup])
    source = SelectionSource(
        join_key=DEFAULT_SELECTION_JOIN_KEY,
        identities=[
            list(records[0][k] for k in ("source_year", "source_household_id"))
            + [
                records[0]["household_support_channel"],
                records[0]["household_support_clone_index"],
            ]
        ],
        provenance={"kind": "test"},
    )

    with pytest.raises(ValueError, match="unique|ambiguous"):
        select_frozen_support(base, source)


def test__given_source_h5_frame__then_loads_identities_from_it() -> None:
    # Given a "source" frame standing in for a published H5
    source_frame = frame_from_records(
        [r for r in pool_records() if r["source_year"] == 2024]
    )

    # When
    source = load_selection_source_from_h5(
        source_frame, join_key=DEFAULT_SELECTION_JOIN_KEY
    )

    # Then it captures one identity per source household
    assert source.n_identities == 4
    assert list(source.join_key) == list(DEFAULT_SELECTION_JOIN_KEY)


def test__given_manifest_roundtrip__then_identities_match_and_integrity_holds(
    tmp_path: Path,
) -> None:
    # Given a selection source distilled from a frame
    source_frame = frame_from_records(pool_records())
    from microcosm.build.us_runtime.h5_io import frame_content_identity

    # A schema-2 manifest records canonical byte and content provenance.
    source = load_selection_source_from_h5(
        source_frame,
        join_key=DEFAULT_SELECTION_JOIN_KEY,
        provenance={
            "kind": "h5",
            "path": "source.h5",
            "sha256": "d" * 64,
            "content_identity_sha256": frame_content_identity(source_frame),
        },
    )
    path = tmp_path / "selection.json"
    write_selection_source_manifest(source, path)

    # When
    reloaded = load_selection_source_from_manifest(path)

    # Then the identities and key match
    assert reloaded.n_identities == source.n_identities
    assert list(reloaded.join_key) == list(source.join_key)
    reloaded_reduced, report = select_frozen_support(
        frame_from_records(pool_records()), reloaded
    )
    assert report.n_selected == source.n_identities

    # And a corrupted integrity hash is rejected
    payload = json.loads(path.read_text())
    payload["identities_sha256"] = "0" * 64
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="identities_sha256|integrity"):
        load_selection_source_from_manifest(path)


def test__given_informed_init_mode__then_drops_unmapped_without_raising() -> None:
    # Given an unmappable identity but informed_init mode
    base = frame_from_records(pool_records())
    source = SelectionSource(
        join_key=DEFAULT_SELECTION_JOIN_KEY,
        identities=[[2024, 11, "asec", 0], [1999, 99, "asec", 0]],
        provenance={"kind": "test"},
    )

    # When: informed_init tolerates unmapped records (they start cold)
    mask, report = source.base_selection_mask(base, mode="informed_init")

    # Then: one mapped, one dropped-and-recorded, no raise
    assert report.n_selected == 1
    assert report.n_unmapped == 1
    assert int(mask.sum()) == 1


# ---------------------------------------------------------------------------
# Location copies (block_location.clone_frame_for_location)
# ---------------------------------------------------------------------------

_PICKS = [
    [2024, 11, "asec", 0],
    [2024, 22, "puf_tax_detail", 1],
    [2023, 44, "asec", 0],
]


def _source(identities, key=LOCATED_JOIN_KEY) -> SelectionSource:
    return SelectionSource(
        join_key=key,
        identities=[list(row) for row in identities],
        provenance={"kind": "test"},
    )


def _replace_household_table(frame: Frame, household: pd.DataFrame) -> Frame:
    tables = {entity: frame.table(entity) for entity in frame.entities}
    tables["household"] = household
    return Frame(tables, frame.schema, {"household": frame.weights_for("household")})


@pytest.mark.parametrize("clones", [2, 3])
def test__given_location_cloned_base__then_selects_exactly_the_named_copies(
    clones: int,
) -> None:
    # Given a K-cloned base and a source naming one copy of three identities
    base = located(frame_from_records(pool_records()), clones)
    picks = [
        [2024, 11, "asec", 0, clones - 1],
        [2024, 22, "puf_tax_detail", 1, 0],
        [2023, 44, "asec", 0, 1],
    ]

    # When
    reduced, report = select_frozen_support(base, _source(picks))

    # Then exactly those copies remain, each with its own w/K weight
    assert report.n_selected == report.n_source == 3
    assert report.n_unmapped == report.n_ambiguous == 0
    assert report.join_key == LOCATED_JOIN_KEY
    assert sorted(household_identities(reduced, LOCATED_JOIN_KEY)) == sorted(
        tuple(row) for row in picks
    )
    np.testing.assert_allclose(reduced.weights_for("household").values, 100.0 / clones)
    # And the receipt has exactly the K=1 fields (no new keys)
    k1_report = select_frozen_support(
        frame_from_records(pool_records()), _source(_PICKS, DEFAULT_SELECTION_JOIN_KEY)
    )[1]
    assert report.as_manifest().keys() == k1_report.as_manifest().keys()


@pytest.mark.parametrize("clones", [2, 3])
def test__given_same_location_cloned_frame_as_source__then_selects_every_copy(
    clones: int,
) -> None:
    # Given a K-cloned base whose own record set is the selection source
    base = located(frame_from_records(pool_records()), clones)

    # When the source H5 is distilled, its key gains the location column
    source = load_selection_source_from_h5(base)
    reduced, report = select_frozen_support(base, source)

    # Then every copy is a distinct identity and the whole base is kept
    assert source.join_key == LOCATED_JOIN_KEY
    assert source.n_identities == report.n_selected == 8 * clones
    assert frame_values(reduced) == frame_values(base)


@pytest.mark.parametrize("clones", [2, 3])
def test__given_all_copies_named__then_selection_commutes_with_location_cloning(
    clones: int,
) -> None:
    # Given the K=1 selection of three identities
    frame = frame_from_records(pool_records())
    k1_source = _source(_PICKS, DEFAULT_SELECTION_JOIN_KEY)
    k1_mask, _ = k1_source.base_selection_mask(frame)
    k1_reduced, k1_report = select_frozen_support(frame, k1_source)

    # When every location copy of those identities is named on the K-cloned base,
    # once directly and once distilled from the K-cloned K=1 support
    base = located(frame, clones)
    named = all_copies_source(k1_source.identities, clones)
    distilled = load_selection_source_from_h5(located(k1_reduced, clones))
    mask, report = named.base_selection_mask(base)
    reduced, _ = select_frozen_support(base, named)

    # Then the mask is the K=1 mask fanned out to every copy, the reduced frame
    # is the K-cloned K=1 support, and the mass of each identity is unchanged
    np.testing.assert_array_equal(mask, np.repeat(k1_mask, clones))
    assert sorted(map(tuple, distilled.identities)) == sorted(
        map(tuple, named.identities)
    )
    assert report.n_selected == clones * k1_report.n_selected
    assert frame_values(reduced) == frame_values(located(k1_reduced, clones))
    k1_mass = mass_by_identity(k1_reduced)
    mass = mass_by_identity(reduced)
    assert mass.keys() == k1_mass.keys()
    for identity, value in k1_mass.items():
        assert mass[identity] == pytest.approx(value, rel=1e-12)


def test__given_location_cloned_source_h5__then_manifest_names_copies_and_round_trips(
    tmp_path: Path,
) -> None:
    # Given a K=3 source frame distilled into a schema-2 manifest
    source_frame = located(frame_from_records(pool_records()), 3)
    source = load_selection_source_from_h5(
        source_frame,
        provenance={
            "kind": "h5",
            "path": "source.h5",
            "sha256": "d" * 64,
            "content_identity_sha256": "e" * 64,
        },
    )
    path = write_selection_source_manifest(source, tmp_path / "selection.json")

    # When
    reloaded = load_selection_source_from_manifest(path)
    mask, report = reloaded.base_selection_mask(source_frame)

    # Then the manifest's key names location copies and selects them all
    assert json.loads(path.read_text())["join_key"] == list(LOCATED_JOIN_KEY)
    assert reloaded.identities_sha256 == source.identities_sha256
    assert mask.all()
    assert report.n_selected == 24


def test__given_copy_index_beyond_k__then_frozen_refuses_and_informed_init_drops() -> (
    None
):
    base = located(frame_from_records(pool_records()), 2)
    source = _source([[2024, 11, "asec", 0, 1], [2024, 11, "asec", 0, 2]])

    with pytest.raises(ValueError, match="unmapped"):
        select_frozen_support(base, source)
    mask, report = source.base_selection_mask(base, mode="informed_init")
    assert report.n_selected == int(mask.sum()) == 1
    assert report.n_unmapped == 1


@pytest.mark.parametrize("clones", [2, 3])
def test__given_location_cloned_base_and_k1_source__then_refuses(clones: int) -> None:
    # A K=1 selection cannot say which location copy of an identity it means.
    base = located(frame_from_records(pool_records()), clones)
    from_h5 = load_selection_source_from_h5(frame_from_records(pool_records()))
    assert from_h5.join_key == DEFAULT_SELECTION_JOIN_KEY

    for source in (_source(_PICKS, DEFAULT_SELECTION_JOIN_KEY), from_h5):
        with pytest.raises(ValueError, match="does not name location copies"):
            select_frozen_support(base, source)


def test__given_location_key_on_k1_frame__then_refuses() -> None:
    frame = frame_from_records(pool_records())

    with pytest.raises(ValueError, match="base frame was never location-cloned"):
        select_frozen_support(frame, _source([[2024, 11, "asec", 0, 0]]))
    with pytest.raises(
        ValueError, match="selection source frame was never location-cloned"
    ):
        load_selection_source_from_h5(frame, join_key=LOCATED_JOIN_KEY)


def test__given_duplicated_key_and_location__then_refuses_as_ambiguous() -> None:
    # Given a K=3 base where a second household repeats the full triple
    # (source identity, support clone, location copy) of household row 4
    clean = located(frame_from_records(pool_records()), 3)
    identity = household_identities(clean, LOCATED_JOIN_KEY)[4]
    base = with_duplicated_household(clean, 4)

    # Then the base, and a source frame carrying it, are refused
    with pytest.raises(ValueError, match="unique|ambiguous") as excinfo:
        select_frozen_support(base, _source([identity]))
    assert LOCATION_COLUMN in str(excinfo.value)
    with pytest.raises(ValueError, match="not unique in the selection source frame"):
        load_selection_source_from_h5(base)
    # And a source repeating one copy is refused as duplicate identities
    with pytest.raises(ValueError, match="duplicate identities"):
        select_frozen_support(clean, _source([identity, identity]))


@pytest.mark.parametrize("bad", [-1, 1.5, np.nan, True, "x"])
def test__given_malformed_location_index__then_refuses(bad: object) -> None:
    base = located(frame_from_records(pool_records()), 3)
    household = base.table("household").copy()
    values = household[LOCATION_COLUMN].astype(object)
    values.iloc[2] = bad
    household[LOCATION_COLUMN] = values
    malformed = _replace_household_table(base, household)
    source = all_copies_source([_PICKS[0]], 3)

    with pytest.raises(ValueError, match="base frame household table: .*nonnegative"):
        select_frozen_support(malformed, source)
    with pytest.raises(ValueError, match="source frame household table: .*nonnegative"):
        load_selection_source_from_h5(malformed)
    with pytest.raises(ValueError, match="selection source identities: .*nonnegative"):
        _source([[2024, 11, "asec", 0, bad]])


def test__given_manifest_with_malformed_location_index__then_refuses(
    tmp_path: Path,
) -> None:
    from microcosm.build.us_runtime.warm_start_selection import _identities_digest

    identities = [[2024, 11, "asec", 0, -1]]
    path = tmp_path / "selection.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "join_key": list(LOCATED_JOIN_KEY),
                "source": {
                    "kind": "h5",
                    "sha256": "d" * 64,
                    "content_identity_sha256": "e" * 64,
                },
                "n_selected": 1,
                "identities_sha256": _identities_digest(LOCATED_JOIN_KEY, identities),
                "identities": identities,
            }
        )
    )

    with pytest.raises(ValueError, match="selection source identities: .*nonnegative"):
        load_selection_source_from_manifest(path)


def test__given_partial_location_metadata__then_refuses() -> None:
    # Person and group tables carry location copies but the household table
    # does not, so which copy a household is cannot be read.
    base = located(frame_from_records(pool_records()), 2)
    partial = _replace_household_table(
        base, base.table("household").drop(columns=[LOCATION_COLUMN])
    )
    source = all_copies_source([_PICKS[0]], 2)

    with pytest.raises(ValueError, match="partial location metadata"):
        select_frozen_support(partial, source)
    with pytest.raises(ValueError, match="partial location metadata"):
        load_selection_source_from_h5(partial)


def test__given_base_missing_a_location_copy__then_refuses() -> None:
    # Household row 4 is copy 1 of (2024, 11, puf_tax_detail, 1).
    base = located(frame_from_records(pool_records()), 3)
    keep = np.ones(base.n("household"), dtype=bool)
    keep[4] = False
    incomplete = select_households(base, keep)

    with pytest.raises(ValueError, match="do not carry all K=3 location copies") as e:
        select_frozen_support(incomplete, _source([[2024, 11, "asec", 0, 0]]))
    assert "[2024, 11, 'puf_tax_detail', 1]" in str(e.value)


def test__given_key_naming_only_the_location_index__then_refuses() -> None:
    with pytest.raises(ValueError, match="cannot identify a record by itself"):
        _source([[0]], key=(LOCATION_COLUMN,))


# ---------------------------------------------------------------------------
# K = 1 is byte-identical to the pre-location code
# ---------------------------------------------------------------------------

#: sha256 per case of ``k1_selection_transcript()`` (results, receipts, the
#: manifest's bytes and every refusal message on the K=1 fixtures), computed by
#: running that same function against the pre-location code: the pristine
#: worktree at 4324432e5 with its own venv, loading this test_support module by
#: path so ``microcosm.build.us_runtime.warm_start_selection`` resolved to the
#: unmodified module.
K1_SELECTION_GOLDEN: dict[str, str] = {}


def test__given_no_location_column__then_matches_the_pre_location_golden() -> None:
    assert k1_selection_transcript() == K1_SELECTION_GOLDEN


def test__given_unknown_key_column__then_refusal_also_lists_the_location_column() -> (
    None
):
    # The only K=1 text change, by design: the whitelist gains one column.
    with pytest.raises(ValueError) as excinfo:
        _source([[1]], key=("household_id",))

    assert str(excinfo.value) == PRE_LOCATION_UNKNOWN_COLUMN_REFUSAL.replace(
        "['household_source_id'",
        "['household_location_clone_index', 'household_source_id'",
    )
    assert SELECTION_JOIN_KEY_COLUMNS[LOCATION_COLUMN] == "household"
    assert LOCATION_COLUMN not in DEFAULT_SELECTION_JOIN_KEY
