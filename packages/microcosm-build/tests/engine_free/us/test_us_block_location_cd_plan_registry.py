"""Attaching the pinned block -> CD-plan registry to a location ladder.

``attach_pinned_cd_plan_registry`` loads the registry with the pinned loader
and attaches every plan before the draw. Invariants, each over synthetic
ladders and registries (``test_support.microcosm_build.us_cd_plan_registry``;
the properties hold for every input Hypothesis generates):

1. Pinning: only the file whose SHA-256 is the packaged provenance's
   ``output_sha256`` loads; any other registry is refused before it is read.
2. Differential: a registry whose current (119th) plan differs from the
   ladder's own district on any ladder block, or that omits a ladder block, is
   refused; on success every ladder block agrees.
3. Lookup: for every household and plan ``p``,
   ``congressional_district_geoid__<p>`` is the registry's district of the
   drawn block, in the household's state, and the release gate passes.
4. No redraw: attaching the registry never moves a drawn block and leaves
   every other geography column unchanged; it only adds the non-current plan
   columns.
5. Receipt: the manifest's ``cd_plan_registry`` record carries the loaded
   file's digest and the plans with known deviations, and the plans' sources
   (known deviations included) are carried verbatim; without a registry the
   manifest has no such key.

The opt-in test at the bottom attaches the real registry to the real ladder
when ``MICROCOSM_US_CD_PLAN_REGISTRY`` and ``MICROCOSM_US_BLOCK_LADDER`` point
at them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pytest

from microcosm.build.us_runtime.block_location import (
    US_CD_PLAN_COLUMN_PREFIX,
    assign_us_block_location,
    attach_pinned_cd_plan_registry,
    load_us_location_ladder,
    location_geography_columns,
    pinned_cd_plan_registry_sha256,
    stale_cd_plan_columns,
    us_block_location_gate,
    us_block_location_manifest,
    verify_pinned_cd_plan_registry_file,
)
from microcosm.build.us_runtime.cd_plan_registry import (
    PRIMARY_CD_PLAN,
    load_us_cd_plan_registry,
)
from test_support.microcosm_build.us_block_location import (
    synthetic_blocks,
    write_location_ladder,
)
from test_support.microcosm_build.us_cd_plan_registry import (
    KNOWN_DEVIATIONS,
    REGISTRY_PLAN_APPORTIONMENT,
    file_sha256,
    pin_cd_plan_registry,
    registry_ready_blocks,
    write_cd_plan_registry,
)

hypothesis = pytest.importorskip("hypothesis")
st = pytest.importorskip("hypothesis.strategies")
given = hypothesis.given
settings = hypothesis.settings
HealthCheck = hypothesis.HealthCheck

_PROPERTY = settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
#: At-large states (AK, DE, DC), multi-seat states (AL, NY, RI) and states
#: whose seat count changed between the 2010 and 2020 apportionments (MT 1->2,
#: NY 27->26, WV 3->2).
_STATE_POOL = (1, 2, 10, 11, 30, 36, 44, 54)
_NON_CURRENT = tuple(p for p in REGISTRY_PLAN_APPORTIONMENT if p != PRIMARY_CD_PLAN)


def _files(directory: Path, arrays: dict[str, np.ndarray], **registry_kwargs):
    ladder_path = write_location_ladder(directory / "ladder.npz", arrays)
    registry_path = write_cd_plan_registry(
        directory / "registry.npz", arrays, **registry_kwargs
    )
    return ladder_path, registry_path


def _household(ladder, rng: np.random.Generator, n: int) -> pd.DataFrame:
    """Households of every source-geography kind in the ladder's states."""

    block_state = ladder.block_geoid // 10**13
    states = np.unique(block_state)
    rows = []
    for index in range(n):
        kind = index % 3
        state = int(rng.choice(states))
        if kind == 0:
            puma = int(rng.choice(np.unique(ladder.puma[block_state == state])))
            rows.append((state, puma, 0))
        elif kind == 1:
            county = int(
                rng.choice(
                    np.unique(ladder.block_geoid[block_state == state] // 10**10)
                )
            )
            rows.append((state, 0, county))
        else:
            rows.append((state, 0, 0))
    return pd.DataFrame(
        {
            "household_id": rng.choice(10**9, size=n, replace=False),
            "state_fips": [row[0] for row in rows],
            "puma": [row[1] for row in rows],
            "county": [row[2] for row in rows],
            "group": -1,
            "weight": rng.uniform(0.5, 50.0, size=n),
        }
    )


def _assign(ladder, household, *, seed: int, clones: int = 1) -> pd.DataFrame:
    return assign_us_block_location(
        household,
        ladder,
        seed=seed,
        clones=clones,
        weights=household["weight"].to_numpy(),
        puma_column="puma",
        county_column="county",
        identification_group_column="group",
        identified_counties={},
    )


@st.composite
def _scenario(draw):
    states = tuple(
        sorted(
            draw(
                st.lists(
                    st.sampled_from(_STATE_POOL), min_size=1, max_size=4, unique=True
                )
            )
        )
    )
    arrays = registry_ready_blocks(
        synthetic_blocks(draw(st.integers(0, 10_000)), states=states)
    )
    return arrays, draw(st.integers(0, 10_000))


# --------------------------------------------------------------------------
# 1. Pinning
# --------------------------------------------------------------------------


def test_the_pinned_loader_refuses_an_unpinned_registry(tmp_path, monkeypatch):
    arrays = registry_ready_blocks(synthetic_blocks(3))
    ladder_path, registry_path = _files(tmp_path, arrays)
    ladder = load_us_location_ladder(ladder_path)

    # The packaged pin is the real artifact, so a synthetic file is refused.
    with pytest.raises(ValueError, match="SHA-256"):
        attach_pinned_cd_plan_registry(ladder, registry_path)

    # Pinned to another synthetic file, this one is still refused.
    other = write_cd_plan_registry(
        tmp_path / "other.npz", arrays, known_deviations=False
    )
    assert file_sha256(other) != file_sha256(registry_path)
    pin_cd_plan_registry(monkeypatch, other)
    with pytest.raises(ValueError, match="SHA-256"):
        attach_pinned_cd_plan_registry(ladder, registry_path)

    pin_cd_plan_registry(monkeypatch, registry_path)
    attached, record = attach_pinned_cd_plan_registry(ladder, registry_path)
    assert record["sha256"] == file_sha256(registry_path)


# --------------------------------------------------------------------------
# 2. Differential against the ladder's own plan
# --------------------------------------------------------------------------


def test_a_registry_that_disagrees_on_the_current_plan_is_refused(
    tmp_path, monkeypatch
):
    arrays = registry_ready_blocks(synthetic_blocks(3, states=(10, 44)))
    rhode_island = np.flatnonzero(arrays["block_geoid"] // 10**13 == 44)
    block = int(arrays["block_geoid"][rhode_island[0]])
    current = int(arrays["congressional_district_geoid"][rhode_island[0]])
    moved = 4401 if current == 4402 else 4402
    ladder_path, registry_path = _files(
        tmp_path, arrays, overrides={PRIMARY_CD_PLAN: {block: moved}}
    )
    # The registry itself is valid: the one-block move keeps every roster.
    load_us_cd_plan_registry(registry_path)
    pin_cd_plan_registry(monkeypatch, registry_path)

    with pytest.raises(ValueError, match="disagrees with the ladder's own copy on 1"):
        attach_pinned_cd_plan_registry(
            load_us_location_ladder(ladder_path), registry_path
        )


def test_a_registry_that_omits_a_ladder_block_is_refused(tmp_path, monkeypatch):
    arrays = registry_ready_blocks(synthetic_blocks(3, states=(10, 44)))
    ladder_path = write_location_ladder(tmp_path / "ladder.npz", arrays)
    fewer = {key: np.asarray(value)[1:] for key, value in arrays.items()}
    registry_path = write_cd_plan_registry(tmp_path / "registry.npz", fewer)
    pin_cd_plan_registry(monkeypatch, registry_path)

    with pytest.raises(ValueError, match="omits 1 ladder block"):
        attach_pinned_cd_plan_registry(
            load_us_location_ladder(ladder_path), registry_path
        )


# --------------------------------------------------------------------------
# 3-4. Lookup, and no redraw
# --------------------------------------------------------------------------


@_PROPERTY
@given(scenario=_scenario(), seed=st.integers(0, 2**32), clones=st.integers(1, 3))
def test_plan_columns_are_the_registry_lookup_and_nothing_is_redrawn(
    scenario, seed, clones
):
    arrays, household_seed = scenario
    with TemporaryDirectory() as directory, pytest.MonkeyPatch.context() as patch:
        ladder_path, registry_path = _files(Path(directory), arrays)
        pin_cd_plan_registry(patch, registry_path)
        ladder = load_us_location_ladder(ladder_path)
        attached, record = attach_pinned_cd_plan_registry(ladder, registry_path)
        registry = load_us_cd_plan_registry(registry_path)

    household = _household(ladder, np.random.default_rng(household_seed), 12)
    plain = _assign(ladder, household, seed=seed, clones=clones)
    table = _assign(attached, household, seed=seed, clones=clones)

    # 4. No redraw: every column of the plain draw is unchanged; the attach
    # adds exactly the non-current plan columns.
    added = [f"{US_CD_PLAN_COLUMN_PREFIX}{plan}" for plan in _NON_CURRENT]
    assert list(location_geography_columns(attached)) == [
        *location_geography_columns(ladder),
        *added,
    ]
    assert set(table.columns) == {*plain.columns, *added}
    assert len(table.columns) == len(plain.columns) + len(added)
    pd.testing.assert_frame_equal(table[list(plain.columns)], plain)

    # 3. Lookup: each plan column is the registry's district of the block.
    blocks = table["block_geoid"].astype(np.int64).to_numpy()
    index = np.searchsorted(registry.block_geoid, blocks)
    assert (registry.block_geoid[index] == blocks).all()
    for plan in REGISTRY_PLAN_APPORTIONMENT:
        column = record["columns"][plan]
        districts = table[column].to_numpy(dtype=np.int64)
        assert (districts == registry.plans[plan][index]).all(), plan
        assert (districts // 100 == table["state_fips"].to_numpy()).all(), plan
    assert record["columns"][PRIMARY_CD_PLAN] == "congressional_district_geoid"
    assert us_block_location_gate(table, attached).passed


def test_the_gate_refuses_a_tampered_plan_column(tmp_path, monkeypatch):
    arrays = registry_ready_blocks(synthetic_blocks(4, states=(36, 44, 54)))
    ladder_path, registry_path = _files(tmp_path, arrays)
    pin_cd_plan_registry(monkeypatch, registry_path)
    attached, _ = attach_pinned_cd_plan_registry(
        load_us_location_ladder(ladder_path), registry_path
    )
    table = _assign(attached, _household(attached, np.random.default_rng(0), 9), seed=7)
    assert us_block_location_gate(table, attached).passed

    column = f"{US_CD_PLAN_COLUMN_PREFIX}117th_congress"
    tampered = table.copy()
    tampered.loc[0, column] = tampered.loc[0, column] + 1
    result = us_block_location_gate(tampered, attached)
    assert not result.passed
    assert any(line.startswith(f"{column}: 1 row(s)") for line in result.failures)
    missing = table.drop(columns=column)
    assert not us_block_location_gate(missing, attached).passed


# --------------------------------------------------------------------------
# 5. Receipt
# --------------------------------------------------------------------------


def test_the_manifest_records_the_registry_only_when_attached(tmp_path, monkeypatch):
    arrays = registry_ready_blocks(synthetic_blocks(5, states=(10, 30, 44, 54)))
    ladder_path, registry_path = _files(tmp_path, arrays)
    digest = pin_cd_plan_registry(monkeypatch, registry_path)
    ladder = load_us_location_ladder(ladder_path)
    attached, record = attach_pinned_cd_plan_registry(ladder, registry_path)
    household = _household(ladder, np.random.default_rng(1), 8)

    plain = us_block_location_manifest(
        _assign(ladder, household, seed=3), ladder, seed=3, clones=1
    )
    manifest = us_block_location_manifest(
        _assign(attached, household, seed=3),
        attached,
        seed=3,
        clones=1,
        cd_plan_registry=record,
    )

    assert "cd_plan_registry" not in plain
    assert manifest["cd_plan_registry"] == record
    assert record == {
        "sha256": digest,
        "pinned_by": (
            "microcosm.build.us_runtime/us_cd_plan_registry.provenance.json "
            "output_sha256"
        ),
        "blocks": len(load_us_cd_plan_registry(registry_path)),
        "plans": sorted(REGISTRY_PLAN_APPORTIONMENT),
        "columns": {
            "117th_congress": "congressional_district_geoid__117th_congress",
            "118th_congress": "congressional_district_geoid__118th_congress",
            "119th_congress": "congressional_district_geoid",
            "120th_congress": "congressional_district_geoid__120th_congress",
        },
        "known_deviations": {"117th_congress": ["37"], "120th_congress": ["29"]},
        "primary_plan_check": {
            "plan": PRIMARY_CD_PLAN,
            "ladder_blocks": len(ladder),
            "blocks_disagreeing": 0,
        },
    }
    # The registry covers every ladder block plus the roster fillers.
    assert record["blocks"] > len(ladder)
    plans = manifest["block_ladder"]["congressional_district_plans"]
    assert set(plans) == set(REGISTRY_PLAN_APPORTIONMENT)
    for plan, deviations in KNOWN_DEVIATIONS.items():
        assert plans[plan]["known_deviations"] == deviations
        assert plans[plan]["primary"] is False
    assert plans[PRIMARY_CD_PLAN]["primary"] is True
    assert plans[PRIMARY_CD_PLAN]["registry"]["vintage"] == PRIMARY_CD_PLAN
    assert manifest["geography_columns"][-3:] == [
        f"{US_CD_PLAN_COLUMN_PREFIX}{plan}" for plan in _NON_CURRENT
    ]
    # Everything else is the plain manifest's.
    for key in set(plain) - {"block_ladder", "geography_columns"}:
        assert manifest[key] == plain[key], key
    json.dumps(manifest)


# --------------------------------------------------------------------------
# Opt-in: the real registry against the real ladder
# --------------------------------------------------------------------------


@pytest.mark.skipif(
    not (
        os.environ.get("MICROCOSM_US_CD_PLAN_REGISTRY")
        and os.environ.get("MICROCOSM_US_BLOCK_LADDER")
    ),
    reason=(
        "set MICROCOSM_US_CD_PLAN_REGISTRY and MICROCOSM_US_BLOCK_LADDER to the "
        "built artifacts to check them"
    ),
)
def test_the_pinned_registry_attaches_to_the_real_ladder():
    ladder = load_us_location_ladder(os.environ["MICROCOSM_US_BLOCK_LADDER"])
    attached, record = attach_pinned_cd_plan_registry(
        ladder, os.environ["MICROCOSM_US_CD_PLAN_REGISTRY"]
    )

    assert set(attached.congressional_district_plans) == set(
        REGISTRY_PLAN_APPORTIONMENT
    )
    assert record["primary_plan_check"]["ladder_blocks"] == len(ladder)
    assert record["known_deviations"] == {
        "117th_congress": ["37"],
        "120th_congress": ["29"],
    }
    sources = attached.congressional_district_plan_sources
    assert sources["117th_congress"]["apportionment"] == "2010_census"
    assert "37" in sources["117th_congress"]["known_deviations"]
    assert "29" in sources["120th_congress"]["known_deviations"]


# --------------------------------------------------------------------------
# Early pin check and stale plan columns
# --------------------------------------------------------------------------


def test_the_early_pin_check_hashes_and_refuses_before_loading(tmp_path, monkeypatch):
    arrays = registry_ready_blocks(synthetic_blocks(3, states=(10, 44)))
    _, registry_path = _files(tmp_path, arrays)

    with pytest.raises(ValueError, match="expected the pinned"):
        verify_pinned_cd_plan_registry_file(registry_path)
    with pytest.raises(FileNotFoundError):
        verify_pinned_cd_plan_registry_file(tmp_path / "missing.npz")

    digest = pin_cd_plan_registry(monkeypatch, registry_path)
    assert pinned_cd_plan_registry_sha256() == digest
    assert verify_pinned_cd_plan_registry_file(registry_path) == digest


def test_stale_plan_columns_are_the_ones_the_ladder_does_not_write(
    tmp_path, monkeypatch
):
    arrays = registry_ready_blocks(synthetic_blocks(3, states=(10, 44)))
    ladder_path, registry_path = _files(tmp_path, arrays)
    pin_cd_plan_registry(monkeypatch, registry_path)
    ladder = load_us_location_ladder(ladder_path)
    attached, _ = attach_pinned_cd_plan_registry(ladder, registry_path)
    plan_columns = [f"{US_CD_PLAN_COLUMN_PREFIX}{plan}" for plan in _NON_CURRENT]
    columns = ["household_id", "congressional_district_geoid", *plan_columns]

    assert stale_cd_plan_columns(columns, ladder) == sorted(plan_columns)
    assert stale_cd_plan_columns(columns, attached) == []
    assert stale_cd_plan_columns(
        [*columns, f"{US_CD_PLAN_COLUMN_PREFIX}121st_congress"], attached
    ) == [f"{US_CD_PLAN_COLUMN_PREFIX}121st_congress"]
