"""Opt-in national validation for the block-first PUMA -> CD distribution.

Set ``MICROCOSM_TEST_US_BLOCK_LADDER_V2`` and
``MICROCOSM_TEST_US_PUMA_LADDER_2020`` to the corresponding national NPZ
artifacts to run this contract locally. CI environments without those external
artifacts skip the test cleanly.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np
import pytest

from microcosm.build.us_runtime.geography_ladder import load_us_block_ladder
from microcosm.build.us_runtime.puma_ladder import load_us_puma_ladder

_BLOCK_LADDER_PATH_ENV = "MICROCOSM_TEST_US_BLOCK_LADDER_V2"
_PUMA_LADDER_PATH_ENV = "MICROCOSM_TEST_US_PUMA_LADDER_2020"
_BLOCK_LADDER_SHA_ENV = "MICROCOSM_TEST_US_BLOCK_LADDER_V2_SHA256"
_PUMA_LADDER_SHA_ENV = "MICROCOSM_TEST_US_PUMA_LADDER_2020_SHA256"
_CD_PAIR_SCALE = 10_000


def _external_artifact_path(variable: str) -> Path:
    configured = os.environ.get(variable)
    if configured is None:
        pytest.skip(
            "national block-first overlap validation requires both "
            f"{_BLOCK_LADDER_PATH_ENV} and {_PUMA_LADDER_PATH_ENV}"
        )
    return Path(configured)


def _assert_optional_sha256(path: Path, variable: str) -> None:
    expected = os.environ.get(variable)
    if expected is None:
        return
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    assert digest.hexdigest() == expected.lower()


def test_national_block_first_puma_cd_overlap_matches_puma_ladder() -> None:
    """Block-population aggregation exactly reproduces PUMA-ladder overlaps."""
    block_path = _external_artifact_path(_BLOCK_LADDER_PATH_ENV)
    puma_path = _external_artifact_path(_PUMA_LADDER_PATH_ENV)
    _assert_optional_sha256(block_path, _BLOCK_LADDER_SHA_ENV)
    _assert_optional_sha256(puma_path, _PUMA_LADDER_SHA_ENV)

    block_ladder = load_us_block_ladder(block_path)
    puma_ladder = load_us_puma_ladder(puma_path)

    # Encode each pair in one int64, sort once, and reduce contiguous runs. This
    # avoids a Python dictionary loop over the roughly 5.8 million block rows.
    block_pairs = (
        block_ladder.puma * _CD_PAIR_SCALE
        + block_ladder.congressional_district_geoid
    )
    order = np.argsort(block_pairs)
    sorted_pairs = block_pairs[order]
    pair_starts = np.flatnonzero(
        np.concatenate(([True], sorted_pairs[1:] != sorted_pairs[:-1]))
    )
    actual_pairs = sorted_pairs[pair_starts]
    actual_population = np.add.reduceat(block_ladder.population[order], pair_starts)

    expected_pairs = (
        puma_ladder.cd_overlap_puma * _CD_PAIR_SCALE
        + puma_ladder.cd_overlap_cd
    )
    np.testing.assert_array_equal(actual_pairs, expected_pairs)
    np.testing.assert_array_equal(
        actual_population, puma_ladder.cd_overlap_population
    )

    actual_puma = actual_pairs // _CD_PAIR_SCALE
    puma_starts = np.flatnonzero(
        np.concatenate(([True], actual_puma[1:] != actual_puma[:-1]))
    )
    np.testing.assert_array_equal(actual_puma[puma_starts], puma_ladder.puma)
    np.testing.assert_array_equal(
        np.add.reduceat(actual_population, puma_starts),
        puma_ladder.puma_population,
    )
