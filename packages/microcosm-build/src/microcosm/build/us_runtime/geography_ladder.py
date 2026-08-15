"""US block-first geography-ladder assignment.

The US artifact's geography spine is anchored at the 2020 census tabulation
block. Each ACS household draws a populated block strictly within its observed
2020 PUMA; each ASEC household (whose v3 checkpoint carries no identified
county) draws a populated block within its state. Every other geography is a
deterministic function of that one block: tract and county are structural
prefixes; PUMA and congressional district, place, state legislative districts,
and metro/CBSA come from aligned block crosswalks in the ladder artifact. One
national dataset, filter by geography, at any grain (microcosm #275; no
per-area files, the standing rule).

The older congressional-district-first assignment API remains available for
backward compatibility, but new spine construction uses
:func:`assign_us_block_first_geography`. Drawing the block first closes the
failure mode where a later block-within-CD draw could escape the ACS record's
observed PUMA.

Vintage discipline follows the country-spec geography-spine schema
(``vintage_policy: "error"``): the ladder artifact records one vintage per
derived layer, the loader refuses an artifact that omits any of them, and the
assignment refuses a ladder whose congressional-district vintage differs from
the vintage the household CDs were assigned under. A silent partial join on
mismatched geography vintages is the failure these checks exist to forbid
(the #205 lesson).

Column names follow the policyengine-us household input surface
(``block_geoid``, ``tract_geoid``, ``county_fips``, ``place_fips``, ``sldu``,
``sldl``, ``cbsa_code``): the exported artifact carries engine inputs, never
formula outputs, so ``in_nyc``/``nyc_income_tax`` recompute from the county
rung instead of being persisted (the #34 regression).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np
import pandas as pd

from microcosm.build.gates import GateResult
from microcosm.build.us_runtime.congressional_district_geography import (
    CONGRESSIONAL_DISTRICT_GEOID_COLUMN,
)
from microcosm.frame import Frame

#: Derived (crosswalk-sourced) layers the ladder artifact must carry a
#: vintage for. Tract and county are structural prefixes of the block geoid
#: and share the block anchor's own vintage.
US_BLOCK_LADDER_DERIVED_LAYERS = (
    "puma",
    "congressional_district",
    "sldu",
    "sldl",
    "place",
    "cbsa",
)

#: Household spine columns the ladder assignment writes, in write order.
#: Every name is a policyengine-us household input variable.
US_GEOGRAPHY_LADDER_COLUMNS = (
    "block_geoid",
    "tract_geoid",
    "county_fips",
    "place_fips",
    "sldu",
    "sldl",
    "cbsa_code",
)

#: All geography columns written by the block-first construction. ``state_fips``
#: is already present and is checked against the selected block's prefix.
US_BLOCK_FIRST_GEOGRAPHY_COLUMNS = (
    "block_geoid",
    "tract_geoid",
    "county_fips",
    "puma",
    CONGRESSIONAL_DISTRICT_GEOID_COLUMN,
    "place_fips",
    "sldu",
    "sldl",
    "cbsa_code",
)

#: The five NYC borough county FIPS codes (Bronx, Kings, New York, Queens,
#: Richmond) — the county rung's regression anchor from microcosm #34.
US_NYC_COUNTY_FIPS = ("36005", "36047", "36061", "36081", "36085")

US_BLOCK_LADDER_SCHEMA_VERSION = 2
US_BLOCK_LADDER_KIND = "us_block_ladder"

#: Exact vintages accepted by block-first construction. These are deliberately
#: constants rather than caller-selectable knobs: joining a different vintage
#: is a new artifact schema and construction authority, never a silent option.
US_BLOCK_LADDER_CANONICAL_VINTAGES: Mapping[str, str] = MappingProxyType(
    {
        "block": "2020_tabulation_blocks",
        "puma": "2020_puma",
        "congressional_district": "119th_congress",
        "sldu": "2020_baf",
        "sldl": "2020_baf",
        "place": "2020_census",
        "cbsa": "omb_2023_delineations",
    }
)

GEOGRAPHY_LADDER_ARTIFACT_SHA256_ATTR = "populace_geography_ladder_artifact_sha256"
GEOGRAPHY_LADDER_VINTAGES_ATTR = "populace_geography_ladder_vintages"
US_BLOCK_FIRST_GEOGRAPHY_RECEIPT_KEY = "us_block_first_geography_receipt"
US_BLOCK_FIRST_GEOGRAPHY_RECEIPT_VERSION = 1

_BLOCK_FIRST_GEOGRAPHY_STAGE = "spine_construction_before_gap_fill"
_BLOCK_FIRST_GEOGRAPHY_OPERATOR = "assign_us_block_first_geography"

_REQUIRED_ARRAY_KEYS = (
    "block_geoid",
    "population",
    "puma",
    "congressional_district_geoid",
    "sldu",
    "sldl",
    "place_fips",
    "cbsa_code",
)


@dataclass(frozen=True)
class UsBlockLadder:
    """The national block ladder: one row per populated 2020 census block.

    Attributes:
        block_geoid: 15-digit block geoids stored as ``int64`` (leading state
            zeros restored by zero-filling to 15 on assignment).
        population: 2020 census population per block (the sampling weight),
            strictly positive — unpopulated blocks cannot host households and
            are excluded at artifact build time.
        puma: 2020 PUMA geoid (``state_fips * 10**5 + PUMA5CE``) containing
            the block's 2020 tract. PUMAs are unions of whole 2020 tracts.
        congressional_district_geoid: Microcosm ``state_fips * 100 + district``
            convention; at-large and delegate districts are district ``00``.
        sldu: State-legislative upper-district 3-character codes; ``""`` where
            the block is in no SLDU.
        sldl: State-legislative lower-district 3-character codes; ``""`` where
            the block is in no SLDL (e.g. Nebraska's unicameral legislature).
        place_fips: 5-digit place FIPS as ``int32``; ``0`` where the block is
            in no incorporated place or CDP.
        cbsa_code: 5-digit CBSA code as ``int32``; ``0`` outside every
            metro/micro area.
        metadata: The artifact's embedded metadata, including one vintage per
            derived layer.
    """

    block_geoid: np.ndarray
    population: np.ndarray
    puma: np.ndarray
    congressional_district_geoid: np.ndarray
    sldu: np.ndarray
    sldl: np.ndarray
    place_fips: np.ndarray
    cbsa_code: np.ndarray
    metadata: Mapping[str, Any]

    def __len__(self) -> int:
        return len(self.block_geoid)

    @property
    def layer_vintages(self) -> dict[str, str]:
        """Vintage per derived layer, plus the block anchor's own vintage."""
        layers = self.metadata["layers"]
        vintages = {
            layer: str(layers[layer]["vintage"])
            for layer in US_BLOCK_LADDER_DERIVED_LAYERS
        }
        vintages["block"] = str(self.metadata["block_vintage"])
        return vintages


def load_us_block_ladder(path: str | Path) -> UsBlockLadder:
    """Load and validate a US block-ladder artifact (NPZ).

    The artifact is a single national file (never per-area files) built by
    ``tools/build_us_block_ladder_artifact.py`` from primary Census/OMB
    sources. Every validation failure raises — a ladder that loads is a
    ladder every assignment invariant holds for.
    """

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"US block ladder artifact not found: {source}")
    with np.load(source, allow_pickle=False) as payload:
        missing = [key for key in _REQUIRED_ARRAY_KEYS if key not in payload.files]
        if missing:
            raise ValueError(
                f"US block ladder artifact is missing required key(s): {missing}."
            )
        if "metadata_json" not in payload.files:
            raise ValueError(
                "US block ladder artifact is missing required key 'metadata_json'."
            )
        arrays = {key: np.asarray(payload[key]) for key in _REQUIRED_ARRAY_KEYS}
        metadata = _metadata_from_scalar(payload["metadata_json"])

    _validate_ladder_metadata(metadata)
    block = _int64_array(arrays["block_geoid"], label="block_geoid")
    n = len(block)
    if n == 0:
        raise ValueError("US block ladder artifact has zero blocks.")
    for key in _REQUIRED_ARRAY_KEYS:
        if len(arrays[key]) != n:
            raise ValueError(
                f"US block ladder array {key!r} has length {len(arrays[key])}, "
                f"expected {n} (aligned to block_geoid)."
            )

    if (block <= 0).any() or (block >= 10**15).any():
        bad = block[(block <= 0) | (block >= 10**15)][:5].tolist()
        raise ValueError(
            f"block_geoid values must be 15-digit block codes; invalid: {bad}."
        )
    unique_blocks = np.unique(block)
    if len(unique_blocks) != n:
        raise ValueError(
            f"block_geoid values must be unique; {n - len(unique_blocks)} "
            "duplicate row(s)."
        )
    if (np.diff(block) <= 0).any():
        raise ValueError(
            "block_geoid values must be sorted ascending for deterministic "
            "universe slices."
        )

    population = np.asarray(arrays["population"], dtype=np.float64)
    if not np.isfinite(population).all() or (population <= 0).any():
        raise ValueError(
            "population must be positive and finite for every block; "
            "unpopulated blocks belong outside the artifact."
        )

    puma = _int64_array(arrays["puma"], label="puma")
    puma_state = puma // 10**5
    invalid_puma = (puma_state < 1) | (puma_state > 56)
    if invalid_puma.any():
        bad = puma[invalid_puma][:5].tolist()
        raise ValueError(
            "puma must be state_fips*10**5+PUMA5CE for a 2020 PUMA; "
            f"invalid: {bad}."
        )
    block_state = block // 10**13
    puma_mismatched = puma_state != block_state
    if puma_mismatched.any():
        examples = [
            f"block {b:015d} -> puma {p:07d}"
            for b, p in zip(
                block[puma_mismatched][:5].tolist(),
                puma[puma_mismatched][:5].tolist(),
                strict=True,
            )
        ]
        raise ValueError(
            "block_geoid state prefix must match puma state; mismatched "
            f"row(s): {examples}."
        )
    same_tract = np.diff(block // 10**4) == 0
    split_tract = same_tract & (np.diff(puma) != 0)
    if split_tract.any():
        positions = np.nonzero(split_tract)[0][:5]
        examples = [
            f"tract {block[position] // 10**4:011d} -> "
            f"PUMAs {puma[position]:07d}/{puma[position + 1]:07d}"
            for position in positions.tolist()
        ]
        raise ValueError(
            "each 2020 tract must map to exactly one 2020 PUMA; conflicting "
            f"row(s): {examples}."
        )

    cd = _int64_array(
        arrays["congressional_district_geoid"],
        label="congressional_district_geoid",
    )
    if ((cd < 100) | (cd > 9999)).any():
        bad = cd[(cd < 100) | (cd > 9999)][:5].tolist()
        raise ValueError(
            "congressional_district_geoid must be state_fips*100+district; "
            f"invalid: {bad}."
        )
    cd_state = cd // 100
    mismatched = block_state != cd_state
    if mismatched.any():
        examples = [
            f"block {b:015d} -> cd {c}"
            for b, c in zip(
                block[mismatched][:5].tolist(),
                cd[mismatched][:5].tolist(),
                strict=True,
            )
        ]
        raise ValueError(
            "block_geoid state prefix must match congressional_district_geoid "
            f"state; mismatched row(s): {examples}."
        )

    sldu = _sld_array(arrays["sldu"], label="sldu")
    sldl = _sld_array(arrays["sldl"], label="sldl")
    place = _code_array(arrays["place_fips"], label="place_fips", upper=99999)
    cbsa = _code_array(arrays["cbsa_code"], label="cbsa_code", upper=99999)

    return UsBlockLadder(
        block_geoid=block,
        population=population,
        puma=puma,
        congressional_district_geoid=cd,
        sldu=sldu,
        sldl=sldl,
        place_fips=place,
        cbsa_code=cbsa,
        metadata=metadata,
    )


def assign_us_block_first_geography(
    household: pd.DataFrame,
    ladder: UsBlockLadder,
    *,
    seed: int = 0,
    state_fips_column: str = "state_fips",
    puma_column: str = "puma",
) -> pd.DataFrame:
    """Assign one population-weighted block in each record's observed universe.

    A positive, non-null ``puma`` is observed ACS geography and restricts the
    block draw to that exact 2020 PUMA. A null/absent ``puma`` is an ASEC v3
    record and restricts the draw to its state; county fallback is intentionally
    unavailable until a future raw-checkpoint schema carries identified county.
    The selected block then deterministically supplies all nine geography
    columns in :data:`US_BLOCK_FIRST_GEOGRAPHY_COLUMNS`.

    Vintage, seed, input-PUMA, and universe-coverage checks all run before the
    random generator is created. Draw groups and candidate blocks have stable
    sorted order, so equal inputs and seeds produce equal assignments.
    """

    _validate_ladder_metadata(ladder.metadata)
    _validate_seed(seed)
    if state_fips_column not in household.columns:
        raise ValueError(
            f"household table must contain {state_fips_column!r} before "
            "block-first geography assignment."
        )

    state_strings = _state_fips_strings(household[state_fips_column])
    state_values = state_strings.astype(np.int64)
    observed_mask, observed_puma = _parse_observed_puma(
        household,
        ladder,
        state_values=state_values,
        puma_column=puma_column,
    )
    fallback_mask = ~observed_mask
    ladder_state = ladder.block_geoid // 10**13
    _validate_block_universe_coverage(
        observed_puma=observed_puma[observed_mask],
        fallback_state=state_values[fallback_mask],
        ladder=ladder,
        ladder_state=ladder_state,
    )

    rng = np.random.default_rng(int(seed))
    assigned_index = np.full(len(household), -1, dtype=np.int64)
    observed_positions = np.nonzero(observed_mask)[0]
    _draw_blocks_within_universe(
        assigned_index,
        row_positions=observed_positions,
        row_universe=observed_puma[observed_mask],
        ladder_universe=ladder.puma,
        ladder=ladder,
        rng=rng,
        universe_label="observed PUMA",
    )
    fallback_positions = np.nonzero(fallback_mask)[0]
    _draw_blocks_within_universe(
        assigned_index,
        row_positions=fallback_positions,
        row_universe=state_values[fallback_mask],
        ladder_universe=ladder_state,
        ladder=ladder,
        rng=rng,
        universe_label="state",
    )
    if (assigned_index < 0).any():
        raise AssertionError("block-first geography left household rows unassigned.")

    selected_puma = ladder.puma[assigned_index]
    # The construction's defining self-check: because 2020 PUMAs are unions
    # of whole tracts, a block drawn in an ACS record's PUMA must derive back
    # to that exact observed PUMA.
    assert np.array_equal(
        selected_puma[observed_mask], observed_puma[observed_mask]
    ), "ACS block-first geography escaped an observed PUMA."

    block_values = ladder.block_geoid[assigned_index]
    block_strings = np.asarray(
        [f"{value:015d}" for value in block_values.tolist()], dtype=object
    )
    block_state = np.asarray(
        [value[:2] for value in block_strings.tolist()], dtype=object
    )
    if not np.array_equal(block_state, state_strings):
        mismatched = block_state != state_strings
        examples = [
            f"state_fips {state} -> block {block}"
            for state, block in zip(
                state_strings[mismatched][:5].tolist(),
                block_strings[mismatched][:5].tolist(),
                strict=True,
            )
        ]
        raise AssertionError(
            "block-first geography escaped a household state: " f"{examples}."
        )

    assigned = household.copy()
    assigned["block_geoid"] = block_strings
    assigned["tract_geoid"] = np.asarray(
        [value[:11] for value in block_strings.tolist()], dtype=object
    )
    assigned["county_fips"] = np.asarray(
        [value[:5] for value in block_strings.tolist()], dtype=object
    )
    assigned["puma"] = np.asarray(
        [f"{value:07d}" for value in selected_puma.tolist()], dtype=object
    )
    assigned[CONGRESSIONAL_DISTRICT_GEOID_COLUMN] = (
        ladder.congressional_district_geoid[assigned_index].astype(np.int64)
    )
    assigned["place_fips"] = _fips_strings(
        ladder.place_fips[assigned_index], width=5
    )
    assigned["sldu"] = ladder.sldu[assigned_index].astype(object)
    assigned["sldl"] = ladder.sldl[assigned_index].astype(object)
    assigned["cbsa_code"] = _fips_strings(
        ladder.cbsa_code[assigned_index], width=5
    )
    return assigned


def us_block_first_geography_receipt(
    source_household: pd.DataFrame,
    assigned_household: pd.DataFrame,
    ladder: UsBlockLadder,
    *,
    seed: int,
    ladder_artifact_sha256: str,
    state_fips_column: str = "state_fips",
    puma_column: str = "puma",
) -> dict[str, object]:
    """Build the checkpoint-authority receipt for one block-first assignment."""

    _validate_ladder_metadata(ladder.metadata)
    _validate_seed(seed)
    _validate_sha256(ladder_artifact_sha256)
    if len(source_household) != len(assigned_household):
        raise ValueError(
            "block-first geography source and assigned household row counts differ."
        )
    if state_fips_column not in source_household:
        raise ValueError(
            f"block-first geography source lacks {state_fips_column!r}."
        )
    source_state = _state_fips_strings(source_household[state_fips_column]).astype(
        np.int64
    )
    observed_mask, observed_puma = _parse_observed_puma(
        source_household,
        ladder,
        state_values=source_state,
        puma_column=puma_column,
    )
    assigned_puma = _strict_geoid_array(
        assigned_household["puma"], label="puma", width=7
    )
    if not np.array_equal(
        assigned_puma[observed_mask], observed_puma[observed_mask]
    ):
        raise AssertionError(
            "ACS derived PUMA does not equal the source record's observed PUMA."
        )

    return {
        "version": US_BLOCK_FIRST_GEOGRAPHY_RECEIPT_VERSION,
        "stage": _BLOCK_FIRST_GEOGRAPHY_STAGE,
        "operator": _BLOCK_FIRST_GEOGRAPHY_OPERATOR,
        "seed": int(seed),
        "ladder_artifact_sha256": ladder_artifact_sha256,
        "ladder": {
            "schema_version": US_BLOCK_LADDER_SCHEMA_VERSION,
            "kind": US_BLOCK_LADDER_KIND,
            "sampling_basis": "population",
            "layer_vintages": ladder.layer_vintages,
        },
        "draw_universes": {
            "acs": "observed_puma",
            "asec": "state",
            "asec_county_status": "absent_from_v3_checkpoint",
        },
        "columns": list(US_BLOCK_FIRST_GEOGRAPHY_COLUMNS),
        "household_rows": int(len(source_household)),
        "observed_puma_rows": int(observed_mask.sum()),
        "state_fallback_rows": int((~observed_mask).sum()),
        "acs_derived_puma_equals_observed": True,
    }


def validate_us_block_first_geography(
    household: pd.DataFrame,
    ladder: UsBlockLadder,
    receipt: Mapping[str, Any],
    *,
    expected_seed: int | None = None,
    expected_ladder_artifact_sha256: str | None = None,
    source_household: pd.DataFrame | None = None,
    state_fips_column: str = "state_fips",
    puma_column: str = "puma",
) -> Mapping[str, Any]:
    """Fail closed unless live geography and its construction receipt agree.

    The live table is rejoined to the ladder by block and every derived value
    is checked. Passing ``source_household`` additionally replays the ACS
    observed-PUMA self-check against the pre-assignment values; the Frame
    wrapper always supplies it before returning.
    """

    _validate_ladder_metadata(ladder.metadata)
    required_receipt_keys = {
        "version",
        "stage",
        "operator",
        "seed",
        "ladder_artifact_sha256",
        "ladder",
        "draw_universes",
        "columns",
        "household_rows",
        "observed_puma_rows",
        "state_fallback_rows",
        "acs_derived_puma_equals_observed",
    }
    if not isinstance(receipt, Mapping) or set(receipt) != required_receipt_keys:
        missing = sorted(required_receipt_keys - set(receipt)) if isinstance(
            receipt, Mapping
        ) else sorted(required_receipt_keys)
        extra = sorted(set(receipt) - required_receipt_keys) if isinstance(
            receipt, Mapping
        ) else []
        raise ValueError(
            "block-first geography receipt fields differ: "
            f"missing={missing}, extra={extra}."
        )
    if receipt["version"] != US_BLOCK_FIRST_GEOGRAPHY_RECEIPT_VERSION:
        raise ValueError("block-first geography receipt version is unsupported.")
    if receipt["stage"] != _BLOCK_FIRST_GEOGRAPHY_STAGE:
        raise ValueError("block-first geography receipt stage is not canonical.")
    if receipt["operator"] != _BLOCK_FIRST_GEOGRAPHY_OPERATOR:
        raise ValueError("block-first geography receipt operator is not canonical.")
    _validate_seed(receipt["seed"])
    if expected_seed is not None and int(receipt["seed"]) != int(expected_seed):
        raise ValueError(
            "block-first geography receipt seed does not match construction config."
        )
    artifact_sha256 = receipt["ladder_artifact_sha256"]
    _validate_sha256(artifact_sha256)
    if (
        expected_ladder_artifact_sha256 is not None
        and artifact_sha256 != expected_ladder_artifact_sha256
    ):
        raise ValueError(
            "block-first geography receipt ladder SHA-256 does not match "
            "construction config."
        )
    expected_ladder_receipt = {
        "schema_version": US_BLOCK_LADDER_SCHEMA_VERSION,
        "kind": US_BLOCK_LADDER_KIND,
        "sampling_basis": "population",
        "layer_vintages": ladder.layer_vintages,
    }
    if _plain_mapping(receipt["ladder"]) != expected_ladder_receipt:
        raise ValueError(
            "block-first geography receipt ladder config/vintages disagree "
            "with the live ladder."
        )
    expected_universes = {
        "acs": "observed_puma",
        "asec": "state",
        "asec_county_status": "absent_from_v3_checkpoint",
    }
    if _plain_mapping(receipt["draw_universes"]) != expected_universes:
        raise ValueError("block-first geography receipt draw universes are invalid.")
    if tuple(receipt["columns"]) != US_BLOCK_FIRST_GEOGRAPHY_COLUMNS:
        raise ValueError("block-first geography receipt columns are not canonical.")
    if receipt["household_rows"] != len(household):
        raise ValueError(
            "block-first geography receipt household row count disagrees with "
            "the live table."
        )
    observed_count = receipt["observed_puma_rows"]
    fallback_count = receipt["state_fallback_rows"]
    if (
        not isinstance(observed_count, int)
        or isinstance(observed_count, bool)
        or not isinstance(fallback_count, int)
        or isinstance(fallback_count, bool)
        or observed_count < 0
        or fallback_count < 0
        or observed_count + fallback_count != len(household)
    ):
        raise ValueError("block-first geography receipt universe counts are invalid.")
    if receipt["acs_derived_puma_equals_observed"] is not True:
        raise ValueError("block-first geography receipt lacks the ACS PUMA self-check.")

    missing_columns = sorted(
        set((*US_BLOCK_FIRST_GEOGRAPHY_COLUMNS, state_fips_column))
        - set(household.columns)
    )
    if missing_columns:
        raise ValueError(
            "block-first geography live household table is missing column(s): "
            f"{missing_columns}."
        )
    live_block = _strict_geoid_array(
        household["block_geoid"], label="block_geoid", width=15
    )
    ladder_positions = np.searchsorted(ladder.block_geoid, live_block)
    covered = ladder_positions < len(ladder)
    if covered.any():
        covered_positions = np.nonzero(covered)[0]
        covered[covered_positions] = (
            ladder.block_geoid[ladder_positions[covered_positions]]
            == live_block[covered_positions]
        )
    if not covered.all():
        missing_blocks = [
            f"{value:015d}" for value in live_block[~covered][:5].tolist()
        ]
        raise ValueError(
            "block-first geography live table contains block(s) absent from "
            f"the ladder: {missing_blocks}."
        )

    expected_block = np.asarray(
        [f"{value:015d}" for value in live_block.tolist()], dtype=object
    )
    expected_values: dict[str, np.ndarray] = {
        "block_geoid": expected_block,
        "tract_geoid": np.asarray(
            [value[:11] for value in expected_block.tolist()], dtype=object
        ),
        "county_fips": np.asarray(
            [value[:5] for value in expected_block.tolist()], dtype=object
        ),
        "puma": np.asarray(
            [
                f"{value:07d}"
                for value in ladder.puma[ladder_positions].tolist()
            ],
            dtype=object,
        ),
        "place_fips": _fips_strings(
            ladder.place_fips[ladder_positions], width=5
        ),
        "sldu": ladder.sldu[ladder_positions].astype(object),
        "sldl": ladder.sldl[ladder_positions].astype(object),
        "cbsa_code": _fips_strings(ladder.cbsa_code[ladder_positions], width=5),
    }
    for column, expected in expected_values.items():
        actual = household[column].astype(str).to_numpy(dtype=object)
        if not np.array_equal(actual, expected):
            raise ValueError(
                f"block-first geography column {column!r} is not the "
                "deterministic value derived from block_geoid."
            )
    actual_cd = _household_cd_series(
        household[CONGRESSIONAL_DISTRICT_GEOID_COLUMN],
        label=CONGRESSIONAL_DISTRICT_GEOID_COLUMN,
    ).to_numpy()
    expected_cd = ladder.congressional_district_geoid[ladder_positions]
    if not np.array_equal(actual_cd, expected_cd):
        raise ValueError(
            "block-first geography congressional district is not derived "
            "from block_geoid."
        )
    state_strings = _state_fips_strings(household[state_fips_column])
    block_state = np.asarray(
        [value[:2] for value in expected_block.tolist()], dtype=object
    )
    if not np.array_equal(state_strings, block_state):
        raise ValueError(
            "block-first geography state_fips disagrees with block_geoid prefix."
        )

    if source_household is not None:
        if len(source_household) != len(household):
            raise ValueError(
                "block-first source household row count differs from live table."
            )
        source_state = _state_fips_strings(
            source_household[state_fips_column]
        ).astype(np.int64)
        observed_mask, source_puma = _parse_observed_puma(
            source_household,
            ladder,
            state_values=source_state,
            puma_column=puma_column,
        )
        if int(observed_mask.sum()) != observed_count:
            raise ValueError(
                "block-first geography receipt observed-PUMA count disagrees "
                "with the source table."
            )
        live_puma = _strict_geoid_array(
            household["puma"], label="puma", width=7
        )
        if not np.array_equal(
            live_puma[observed_mask], source_puma[observed_mask]
        ):
            raise AssertionError(
                "ACS derived PUMA does not equal the source record's observed PUMA."
            )
    return receipt


def with_household_us_block_first_geography(
    frame: Frame,
    ladder: UsBlockLadder,
    *,
    seed: int = 0,
    ladder_artifact_sha256: str,
    state_fips_column: str = "state_fips",
    puma_column: str = "puma",
) -> Frame:
    """Assign and receipt block-first geography on the household table."""

    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    source_household = tables["household"].copy()
    tables["household"] = assign_us_block_first_geography(
        source_household,
        ladder,
        seed=seed,
        state_fips_column=state_fips_column,
        puma_column=puma_column,
    )
    receipt = us_block_first_geography_receipt(
        source_household,
        tables["household"],
        ladder,
        seed=seed,
        ladder_artifact_sha256=ladder_artifact_sha256,
        state_fips_column=state_fips_column,
        puma_column=puma_column,
    )
    validate_us_block_first_geography(
        tables["household"],
        ladder,
        receipt,
        expected_seed=seed,
        expected_ladder_artifact_sha256=ladder_artifact_sha256,
        source_household=source_household,
        state_fips_column=state_fips_column,
        puma_column=puma_column,
    )
    for link_name in frame.links:
        tables[link_name] = frame.link(link_name).copy()
    weights = {entity: frame.weights_for(entity) for entity in frame.weighted_entities}
    return Frame(
        tables,
        frame.schema,
        weights,
        frame.strata,
        mass_log=frame.mass_log,
        metadata={
            **frame.metadata,
            US_BLOCK_FIRST_GEOGRAPHY_RECEIPT_KEY: receipt,
        },
    )


def assign_us_geography_ladder(
    household: pd.DataFrame,
    ladder: UsBlockLadder,
    *,
    seed: int = 0,
    expected_congressional_district_vintage: str | None = None,
    state_fips_column: str = "state_fips",
    cd_column: str = CONGRESSIONAL_DISTRICT_GEOID_COLUMN,
) -> pd.DataFrame:
    """Assign each household one census block and the derived ladder columns.

    Blocks are sampled within the household's assigned congressional district
    proportional to 2020 block population, so the calibrated CD (and state)
    distributions are preserved exactly while every finer and coarser layer
    becomes filterable. Requires CD assignment to have run first; a household
    CD absent from the ladder is an error (the districts either predate the
    ladder's CD vintage or the ladder was built for another vintage — both
    are vintage mismatches, never silently partial-joined).
    """

    for column in (state_fips_column, cd_column):
        if column not in household.columns:
            raise ValueError(
                f"household table must contain {column!r} before geography-"
                "ladder assignment (assign congressional districts first)."
            )
    if expected_congressional_district_vintage is not None:
        ladder_cd_vintage = ladder.layer_vintages["congressional_district"]
        if ladder_cd_vintage != expected_congressional_district_vintage:
            raise ValueError(
                "US block ladder congressional-district vintage "
                f"{ladder_cd_vintage!r} does not match the vintage household "
                f"districts were assigned under "
                f"({expected_congressional_district_vintage!r})."
            )

    household_cd = _household_cd_series(household[cd_column], label=cd_column)
    ladder_cds = np.unique(ladder.congressional_district_geoid)
    missing_cds = sorted(set(household_cd.tolist()) - set(ladder_cds.tolist()))
    if missing_cds:
        raise ValueError(
            "US block ladder has no blocks for household congressional "
            f"district geoid(s): {missing_cds[:10]} "
            f"({len(missing_cds)} total). The household districts and the "
            "ladder artifact must share a CD vintage."
        )

    order = np.argsort(ladder.congressional_district_geoid, kind="stable")
    sorted_cd = ladder.congressional_district_geoid[order]
    assigned_index = np.empty(len(household), dtype=np.int64)
    rng = np.random.default_rng(seed)
    cd_groups = household_cd.groupby(household_cd, sort=True).groups
    cd_group_order = list(cd_groups)
    assert cd_group_order == sorted(household_cd.unique().tolist()), (
        "Block-ladder RNG congressional-district groups must be sorted unique "
        "normalized geoids."
    )
    for cd_value in cd_group_order:
        positions = cd_groups[cd_value]
        lo = int(np.searchsorted(sorted_cd, cd_value, side="left"))
        hi = int(np.searchsorted(sorted_cd, cd_value, side="right"))
        block_rows = order[lo:hi]
        weights = ladder.population[block_rows]
        probabilities = weights / weights.sum()
        assigned_index[np.asarray(positions, dtype=np.int64)] = rng.choice(
            block_rows,
            size=len(positions),
            replace=True,
            p=probabilities,
        )

    block_values = ladder.block_geoid[assigned_index]
    block_str = np.array([f"{value:015d}" for value in block_values.tolist()])
    state_str = _state_fips_strings(household[state_fips_column])
    block_state = np.array([value[:2] for value in block_str.tolist()])
    mismatched = block_state != state_str
    if mismatched.any():
        examples = [
            f"state_fips {state} -> block {blocked}"
            for state, blocked in zip(
                state_str[mismatched][:5].tolist(),
                block_str[mismatched][:5].tolist(),
                strict=True,
            )
        ]
        raise ValueError(
            "Assigned block state prefix disagrees with household state_fips "
            f"(CD assignment and ladder are inconsistent): {examples}."
        )

    assigned = household.copy()
    assigned["block_geoid"] = block_str
    assigned["tract_geoid"] = np.array([value[:11] for value in block_str.tolist()])
    assigned["county_fips"] = np.array([value[:5] for value in block_str.tolist()])
    assigned["place_fips"] = _fips_strings(ladder.place_fips[assigned_index], width=5)
    assigned["sldu"] = ladder.sldu[assigned_index].astype(object)
    assigned["sldl"] = ladder.sldl[assigned_index].astype(object)
    assigned["cbsa_code"] = _fips_strings(ladder.cbsa_code[assigned_index], width=5)
    return assigned


def with_household_us_geography_ladder(
    frame: Frame,
    ladder: UsBlockLadder,
    *,
    seed: int = 0,
    expected_congressional_district_vintage: str | None = None,
) -> Frame:
    """Return ``frame`` with the household geography ladder assigned."""

    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    tables["household"] = assign_us_geography_ladder(
        tables["household"],
        ladder,
        seed=seed,
        expected_congressional_district_vintage=(
            expected_congressional_district_vintage
        ),
    )
    for link_name in frame.links:
        tables[link_name] = frame.link(link_name).copy()
    weights = {entity: frame.weights_for(entity) for entity in frame.weighted_entities}
    return Frame(
        tables,
        frame.schema,
        weights,
        frame.strata,
        mass_log=frame.mass_log,
        metadata=frame.metadata,
    )


def us_geography_ladder_assignment_summary(
    household: pd.DataFrame,
    ladder: UsBlockLadder,
    *,
    weight_values: np.ndarray | None = None,
) -> dict[str, Any]:
    """Summarize ladder assignment coverage for provenance logs.

    Weighted shares use household weights when provided (the spot-check
    surface for comparing filtered grains against ACS population totals);
    otherwise unweighted row shares.
    """

    applied = all(column in household.columns for column in US_GEOGRAPHY_LADDER_COLUMNS)
    weights = (
        np.asarray(weight_values, dtype=np.float64)
        if weight_values is not None
        else np.ones(len(household), dtype=np.float64)
    )
    if len(weights) != len(household):
        raise ValueError(
            f"weight_values length {len(weights)} does not match household "
            f"rows {len(household)}."
        )
    summary: dict[str, Any] = {
        "applied": applied,
        "household_rows": int(len(household)),
        "ladder_blocks": int(len(ladder)),
        "layer_vintages": ladder.layer_vintages,
        "sampling_basis": str(ladder.metadata["sampling_basis"]),
    }
    if not applied:
        return summary
    total = float(weights.sum())
    for column in US_GEOGRAPHY_LADDER_COLUMNS:
        values = household[column].astype(str).to_numpy()
        nonempty = values != ""
        summary[f"assigned_{column}_values"] = int(
            pd.Series(values[nonempty]).nunique()
        )
        summary[f"{column}_nonempty_weighted_share"] = (
            float(weights[nonempty].sum() / total) if total > 0 else 0.0
        )
    county = household["county_fips"].astype(str).to_numpy()
    nyc = np.isin(county, US_NYC_COUNTY_FIPS)
    summary["nyc_weighted_household_share"] = (
        float(weights[nyc].sum() / total) if total > 0 else 0.0
    )
    return summary


def us_geography_ladder_gate(
    household: pd.DataFrame,
    weight_values: np.ndarray,
    *,
    state_fips_column: str = "state_fips",
    cd_column: str = CONGRESSIONAL_DISTRICT_GEOID_COLUMN,
    nyc_share_bounds: tuple[float, float] = (0.005, 0.06),
    nyc_share_of_new_york_bounds: tuple[float, float] = (0.20, 0.65),
    place_share_bounds: tuple[float, float] = (0.40, 0.95),
    cbsa_share_bounds: tuple[float, float] = (0.75, 0.99),
    sld_min_share: float = 0.95,
) -> GateResult:
    """Gate the exported geography ladder: structure, coverage, and NYC mass.

    The NYC checks are the permanent form of the microcosm #34 regression:
    recomputing ``in_nyc`` from the county rung must never silently collapse
    NYC to zero. NYC holds roughly 2.6% of national household weight and
    roughly 42% of New York State's, so the default bounds fail on collapse
    (0%) and on gross misassignment, not on calibration noise. Place/CBSA/SLD
    coverage bounds are population anchors: about 76% of people live in a
    census place, about 93% in a CBSA, and everyone outside DC and Nebraska's
    missing lower chamber has both state legislative districts.
    """

    failures: list[str] = []
    details: dict[str, object] = {}
    weights = np.asarray(weight_values, dtype=np.float64)
    if len(weights) != len(household):
        raise ValueError(
            f"weight_values length {len(weights)} does not match household "
            f"rows {len(household)}."
        )

    missing_columns = [
        column
        for column in (*US_GEOGRAPHY_LADDER_COLUMNS, state_fips_column, cd_column)
        if column not in household.columns
    ]
    if missing_columns:
        failures.append(
            f"household table is missing geography column(s): {missing_columns}"
        )
        return GateResult(
            name="us_geography_ladder",
            passed=False,
            failures=tuple(failures),
            details=details,
        )

    block = household["block_geoid"].astype(str).to_numpy()
    tract = household["tract_geoid"].astype(str).to_numpy()
    county = household["county_fips"].astype(str).to_numpy()
    for label, values, width in (
        ("block_geoid", block, 15),
        ("tract_geoid", tract, 11),
        ("county_fips", county, 5),
    ):
        bad = ~(np.char.str_len(values.astype(np.str_)) == width) | ~np.char.isdigit(
            values.astype(np.str_)
        )
        if bad.any():
            failures.append(
                f"{label}: {int(bad.sum())}/{len(values)} row(s) are not "
                f"{width}-digit codes; examples {sorted(set(values[bad]))[:5]}"
            )
    prefix_checks = (
        ("tract_geoid", tract, np.array([value[:11] for value in block.tolist()])),
        ("county_fips", county, np.array([value[:5] for value in block.tolist()])),
        (
            state_fips_column,
            _state_fips_strings(household[state_fips_column]),
            np.array([value[:2] for value in block.tolist()]),
        ),
    )
    for label, values, expected in prefix_checks:
        mismatched = values != expected
        if mismatched.any():
            failures.append(
                f"{label}: {int(mismatched.sum())}/{len(values)} row(s) "
                "disagree with the block_geoid prefix"
            )
    cd_state = (
        _household_cd_series(household[cd_column], label=cd_column) // 100
    ).to_numpy()
    block_state = np.array([int(value[:2]) for value in block.tolist()])
    cd_mismatch = cd_state != block_state
    if cd_mismatch.any():
        failures.append(
            f"{cd_column}: {int(cd_mismatch.sum())}/{len(block)} row(s) "
            "have a state prefix disagreeing with block_geoid"
        )

    total = float(weights.sum())
    if total <= 0:
        failures.append("household weights sum to zero; shares are undefined")
        return GateResult(
            name="us_geography_ladder",
            passed=False,
            failures=tuple(failures),
            details=details,
        )

    nyc_mask = np.isin(county, US_NYC_COUNTY_FIPS)
    nyc_share = float(weights[nyc_mask].sum() / total)
    details["nyc_weighted_household_share"] = nyc_share
    low, high = nyc_share_bounds
    if not low <= nyc_share <= high:
        failures.append(
            f"NYC weighted household share {nyc_share:.4f} outside "
            f"[{low}, {high}] (the #34 in_nyc collapse regression)"
        )
    new_york = _state_fips_strings(household[state_fips_column]) == "36"
    new_york_total = float(weights[new_york].sum())
    if new_york_total > 0:
        nyc_of_ny = float(weights[nyc_mask & new_york].sum() / new_york_total)
        details["nyc_weighted_share_of_new_york"] = nyc_of_ny
        low, high = nyc_share_of_new_york_bounds
        if not low <= nyc_of_ny <= high:
            failures.append(
                f"NYC weighted share of New York State {nyc_of_ny:.4f} "
                f"outside [{low}, {high}]"
            )
    else:
        failures.append("New York State carries zero household weight")

    for label, bounds in (
        ("place_fips", place_share_bounds),
        ("cbsa_code", cbsa_share_bounds),
    ):
        values = household[label].astype(str).to_numpy()
        share = float(weights[values != ""].sum() / total)
        details[f"{label}_nonempty_weighted_share"] = share
        low, high = bounds
        if not low <= share <= high:
            failures.append(
                f"{label} nonempty weighted share {share:.4f} outside [{low}, {high}]"
            )
    for label in ("sldu", "sldl"):
        values = household[label].astype(str).to_numpy()
        share = float(weights[values != ""].sum() / total)
        details[f"{label}_nonempty_weighted_share"] = share
        if share < sld_min_share:
            failures.append(
                f"{label} nonempty weighted share {share:.4f} below {sld_min_share}"
            )

    return GateResult(
        name="us_geography_ladder",
        passed=not failures,
        failures=tuple(failures),
        details=details,
    )


def _validate_seed(seed: Any) -> None:
    if (
        isinstance(seed, (bool, np.bool_))
        or not isinstance(seed, (int, np.integer))
        or int(seed) < 0
    ):
        raise ValueError("block-first geography seed must be a non-negative integer.")


def _validate_sha256(value: Any) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(
            "block-first geography ladder_artifact_sha256 must be 64 "
            "lowercase hexadecimal characters."
        )


def _parse_observed_puma(
    household: pd.DataFrame,
    ladder: UsBlockLadder,
    *,
    state_values: np.ndarray,
    puma_column: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the observed-ACS mask and normalized PUMA geoids.

    Null, blank, and numeric zero values are the ASEC state-fallback marker.
    Any other supplied value must be an integer 2020 PUMA covered by the
    ladder and belonging to the row's state.
    """

    n = len(household)
    normalized = np.full(n, -1, dtype=np.int64)
    if puma_column not in household.columns:
        return np.zeros(n, dtype=bool), normalized
    series = pd.Series(household[puma_column]).reset_index(drop=True)
    blank = series.map(
        lambda value: isinstance(value, str) and not value.strip()
    ).to_numpy(dtype=bool)
    provided = (~series.isna()).to_numpy(dtype=bool) & ~blank
    numeric = pd.to_numeric(series, errors="coerce").to_numpy(dtype=np.float64)
    malformed = provided & ~np.isfinite(numeric)
    if malformed.any():
        bad = series.to_numpy()[malformed][:5].tolist()
        raise ValueError(f"puma contains malformed observed value(s): {bad}.")
    negative = provided & (numeric < 0)
    if negative.any():
        bad = series.to_numpy()[negative][:5].tolist()
        raise ValueError(f"puma contains negative geoid value(s): {bad}.")
    observed = provided & (numeric > 0)
    non_integer = observed & (numeric != np.floor(numeric))
    if non_integer.any():
        bad = series.to_numpy()[non_integer][:5].tolist()
        raise ValueError(f"puma contains non-integer geoid value(s): {bad}.")
    normalized[observed] = numeric[observed].astype(np.int64)

    missing = sorted(
        set(normalized[observed].tolist()) - set(ladder.puma.tolist())
    )
    if missing:
        raise ValueError(
            "US block ladder has no blocks for observed household puma "
            f"geoid(s): {missing[:10]} ({len(missing)} total). The household "
            "PUMAs and ladder artifact must share the canonical 2020 vintage."
        )
    puma_state = normalized[observed] // 10**5
    wanted_state = state_values[observed]
    mismatched = puma_state != wanted_state
    if mismatched.any():
        examples = [
            f"state {state:02d} -> puma {puma:07d}"
            for state, puma in zip(
                wanted_state[mismatched][:5].tolist(),
                normalized[observed][mismatched][:5].tolist(),
                strict=True,
            )
        ]
        raise ValueError(
            "observed household puma state disagrees with state_fips: "
            f"{examples}."
        )
    return observed, normalized


def _validate_block_universe_coverage(
    *,
    observed_puma: np.ndarray,
    fallback_state: np.ndarray,
    ladder: UsBlockLadder,
    ladder_state: np.ndarray,
) -> None:
    missing_pumas = sorted(
        set(np.unique(observed_puma).tolist()) - set(np.unique(ladder.puma).tolist())
    )
    if missing_pumas:
        raise ValueError(
            "US block ladder has no populated blocks for observed PUMA(s): "
            f"{missing_pumas[:10]}."
        )
    missing_states = sorted(
        set(np.unique(fallback_state).tolist())
        - set(np.unique(ladder_state).tolist())
    )
    if missing_states:
        formatted = [f"{state:02d}" for state in missing_states[:10]]
        raise ValueError(
            "US block ladder has no populated blocks for ASEC state_fips "
            f"value(s): {formatted}."
        )


def _draw_blocks_within_universe(
    assigned_index: np.ndarray,
    *,
    row_positions: np.ndarray,
    row_universe: np.ndarray,
    ladder_universe: np.ndarray,
    ladder: UsBlockLadder,
    rng: np.random.Generator,
    universe_label: str,
) -> None:
    if len(row_positions) == 0:
        return
    order = np.argsort(ladder_universe, kind="stable")
    sorted_universe = ladder_universe[order]
    universe_groups = np.unique(row_universe)
    assert np.array_equal(universe_groups, np.sort(universe_groups)), (
        f"block-first RNG {universe_label} groups must be sorted."
    )
    for universe in universe_groups.tolist():
        positions = row_positions[row_universe == universe]
        lo = int(np.searchsorted(sorted_universe, universe, side="left"))
        hi = int(np.searchsorted(sorted_universe, universe, side="right"))
        candidates = order[lo:hi]
        if len(candidates) == 0:
            raise AssertionError(
                f"validated {universe_label} universe {universe} lost coverage."
            )
        weights = ladder.population[candidates]
        assigned_index[positions] = rng.choice(
            candidates,
            size=len(positions),
            replace=True,
            p=weights / weights.sum(),
        )


def _strict_geoid_array(values: Any, *, label: str, width: int) -> np.ndarray:
    series = pd.Series(values).reset_index(drop=True)
    strings = series.astype(str).to_numpy(dtype=str)
    valid = (np.char.str_len(strings) == width) & np.char.isdigit(strings)
    if not valid.all():
        bad = series[~valid].head(5).tolist()
        raise ValueError(
            f"{label} must contain canonical {width}-digit geoids; invalid: {bad}."
        )
    return strings.astype(np.int64)


def _plain_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("block-first geography receipt contains a non-mapping.")
    result: dict[str, Any] = {}
    for key, nested in value.items():
        if isinstance(nested, Mapping):
            result[str(key)] = _plain_mapping(nested)
        else:
            result[str(key)] = nested
    return result


def _metadata_from_scalar(value: np.ndarray) -> dict[str, Any]:
    if value.shape != ():
        raise ValueError("metadata_json must be a scalar JSON string.")
    raw = value.item()
    if isinstance(raw, bytes):
        raw = raw.decode()
    if not isinstance(raw, str):
        raise ValueError("metadata_json must be a scalar JSON string.")
    metadata = json.loads(raw)
    if not isinstance(metadata, dict):
        raise ValueError("metadata_json must decode to an object.")
    return metadata


def _validate_ladder_metadata(metadata: Mapping[str, Any]) -> None:
    if metadata.get("schema_version") != US_BLOCK_LADDER_SCHEMA_VERSION:
        raise ValueError(
            "US block ladder metadata schema_version must be "
            f"{US_BLOCK_LADDER_SCHEMA_VERSION}, got "
            f"{metadata.get('schema_version')!r}."
        )
    if metadata.get("kind") != US_BLOCK_LADDER_KIND:
        raise ValueError(
            f"US block ladder metadata kind must be {US_BLOCK_LADDER_KIND!r}, "
            f"got {metadata.get('kind')!r}."
        )
    block_vintage = str(metadata.get("block_vintage") or "")
    expected_block_vintage = US_BLOCK_LADDER_CANONICAL_VINTAGES["block"]
    if block_vintage != expected_block_vintage:
        raise ValueError(
            "US block ladder block_vintage must be the canonical "
            f"{expected_block_vintage!r}, got {block_vintage!r} "
            "(vintage_policy: error)."
        )
    if metadata.get("sampling_basis") != "population":
        raise ValueError(
            "US block ladder sampling_basis must be the canonical "
            f"'population', got {metadata.get('sampling_basis')!r}."
        )
    layers = metadata.get("layers")
    if not isinstance(layers, Mapping):
        raise ValueError("US block ladder metadata must carry a layers mapping.")
    missing = [layer for layer in US_BLOCK_LADDER_DERIVED_LAYERS if layer not in layers]
    if missing:
        raise ValueError(
            f"US block ladder metadata layers are missing: {missing}. Every "
            "derived layer records its own vintage (vintage_policy: error)."
        )
    for layer in US_BLOCK_LADDER_DERIVED_LAYERS:
        spec = layers[layer]
        if not isinstance(spec, Mapping) or not str(spec.get("vintage") or ""):
            raise ValueError(
                f"US block ladder layer {layer!r} must record a non-empty vintage."
            )
        if not str(spec.get("source") or ""):
            raise ValueError(
                f"US block ladder layer {layer!r} must record a non-empty "
                "source citation."
            )
        expected_vintage = US_BLOCK_LADDER_CANONICAL_VINTAGES[layer]
        actual_vintage = str(spec["vintage"])
        if actual_vintage != expected_vintage:
            raise ValueError(
                f"US block ladder layer {layer!r} vintage must be the canonical "
                f"{expected_vintage!r}, got {actual_vintage!r} "
                "(vintage_policy: error)."
            )


def _int64_array(values: np.ndarray, *, label: str) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype.kind not in ("i", "u"):
        raise ValueError(f"{label} must be an integer array, got dtype {array.dtype}.")
    return array.astype(np.int64, copy=False)


def _sld_array(values: np.ndarray, *, label: str) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype.kind != "U":
        raise ValueError(f"{label} must be a unicode array, got {array.dtype}.")
    lengths = np.char.str_len(array)
    bad = (lengths != 0) & (lengths != 3)
    if bad.any():
        raise ValueError(
            f"{label} codes must be empty or 3 characters; invalid: "
            f"{sorted(set(array[bad].tolist()))[:5]}."
        )
    unassigned_markers = np.isin(array, ("ZZZ", "ZZ", "999"))
    if unassigned_markers.any():
        raise ValueError(
            f"{label} carries Census unassigned marker(s) "
            f"{sorted(set(array[unassigned_markers].tolist()))}; the artifact "
            "builder normalizes unassigned districts to ''."
        )
    return array


def _code_array(values: np.ndarray, *, label: str, upper: int) -> np.ndarray:
    array = _int64_array(values, label=label)
    if ((array < 0) | (array > upper)).any():
        bad = array[(array < 0) | (array > upper)][:5].tolist()
        raise ValueError(f"{label} codes must be in [0, {upper}]; invalid: {bad}.")
    return array.astype(np.int32, copy=False)


def _household_cd_series(values: Any, *, label: str) -> pd.Series:
    series = pd.Series(values).reset_index(drop=True)
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.isna().any():
        bad = series[numeric.isna()].head(5).tolist()
        raise ValueError(f"{label} contains non-numeric value(s): {bad}.")
    numeric_values = numeric.to_numpy(dtype=np.float64)
    if not np.isfinite(numeric_values).all():
        raise ValueError(f"{label} contains non-finite value(s).")
    if (numeric_values != np.floor(numeric_values)).any():
        bad = series[numeric_values != np.floor(numeric_values)].head(5).tolist()
        raise ValueError(f"{label} must contain integer geoids; invalid: {bad}.")
    integers = numeric_values.astype(np.int64)
    invalid = (integers < 100) | (integers > 9999)
    if invalid.any():
        raise ValueError(
            f"{label} must be state_fips*100+district; invalid: "
            f"{integers[invalid][:5].tolist()}."
        )
    return pd.Series(integers)


def _state_fips_strings(values: Any) -> np.ndarray:
    series = pd.Series(values)
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.isna().any():
        bad = series[numeric.isna()].head(5).tolist()
        raise ValueError(f"state_fips contains non-numeric value(s): {bad}.")
    numeric_values = numeric.to_numpy(dtype=np.float64)
    if (numeric_values != np.floor(numeric_values)).any():
        raise ValueError("state_fips must contain integer values.")
    integers = numeric_values.astype(np.int64)
    if ((integers < 1) | (integers > 99)).any():
        raise ValueError(
            "state_fips must contain two-digit state FIPS codes; invalid: "
            f"{integers[(integers < 1) | (integers > 99)][:5].tolist()}."
        )
    return np.array([f"{value:02d}" for value in integers.tolist()])


def _fips_strings(values: np.ndarray, *, width: int) -> np.ndarray:
    array = np.asarray(values, dtype=np.int64)
    return np.array(
        [("" if value == 0 else f"{value:0{width}d}") for value in array.tolist()],
        dtype=object,
    )


__all__ = [
    "GEOGRAPHY_LADDER_ARTIFACT_SHA256_ATTR",
    "GEOGRAPHY_LADDER_VINTAGES_ATTR",
    "US_BLOCK_FIRST_GEOGRAPHY_COLUMNS",
    "US_BLOCK_FIRST_GEOGRAPHY_RECEIPT_KEY",
    "US_BLOCK_FIRST_GEOGRAPHY_RECEIPT_VERSION",
    "US_BLOCK_LADDER_CANONICAL_VINTAGES",
    "US_BLOCK_LADDER_DERIVED_LAYERS",
    "US_BLOCK_LADDER_KIND",
    "US_BLOCK_LADDER_SCHEMA_VERSION",
    "US_GEOGRAPHY_LADDER_COLUMNS",
    "US_NYC_COUNTY_FIPS",
    "UsBlockLadder",
    "assign_us_block_first_geography",
    "assign_us_geography_ladder",
    "load_us_block_ladder",
    "us_block_first_geography_receipt",
    "us_geography_ladder_assignment_summary",
    "us_geography_ladder_gate",
    "validate_us_block_first_geography",
    "with_household_us_block_first_geography",
    "with_household_us_geography_ladder",
]
