"""Reporter-anchored, Bernoulli-at-documented-prior SSI take-up tests."""

# ruff: noqa: F401

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from microcosm.build.us_runtime.block_location import clone_frame_for_location
from microcosm.build.us_runtime.fiscal_targets import (
    SSA_SSI_AGE_BAND_RECIPIENTS_TARGET_ROLE,
)
from microcosm.build.us_runtime.ssi_take_up import (
    SSI_TAKE_UP_ARCHIVED_DERIVATION_URL,
    SSI_TAKE_UP_ARCHIVED_RANDOMNESS_URL,
    SSI_TAKE_UP_ARCHIVED_TARGETS_URL,
    SSI_TAKE_UP_SSA_SOURCE_URL,
    US_SSI_TAKE_UP_AGE_TARGETS,
    US_SSI_TAKE_UP_ANCHOR,
    US_SSI_TAKE_UP_BAND_DELIVERY_RELATIVE_TOLERANCE,
    US_SSI_TAKE_UP_ENFORCED_BAND_KEYS,
    US_SSI_TAKE_UP_OUTPUT_COLUMNS,
    US_SSI_TAKE_UP_PRIOR_BASIS_CURRENT_FRAME,
    US_SSI_TAKE_UP_PRIOR_BASIS_RELEASE_ARTIFACT,
    US_SSI_TAKE_UP_STAGE_NAME,
    SSITakeUpBandPriorBasis,
    SSITakeUpPriorBasis,
    _band_prior,
    _source_table,
    _stable_source_draw,
    ssi_take_up_prior_basis_from_artifact,
    ssi_take_up_prior_basis_from_diagnostics,
    us_ssi_take_up_delivery_gate,
    us_ssi_take_up_diagnostics,
    us_ssi_take_up_gate,
    us_ssi_take_up_reporter_source_ids,
    us_ssi_take_up_stage_spec,
    with_us_ssi_take_up,
    write_us_ssi_take_up_diagnostics,
)
from microcosm.build.us_runtime.support_provenance import location_clone_index_column
from microcosm.frame import US_SCHEMA, Frame, WeightKind, Weights

_OUTPUT = US_SSI_TAKE_UP_OUTPUT_COLUMNS[0]
_TARGETS = {target.key: 50.0 for target in US_SSI_TAKE_UP_AGE_TARGETS}
_AGES = {"under_18": 12.0, "18_64": 40.0, "65_plus": 72.0}
# Fixture arithmetic per band: six dual-channel candidates weigh 20.0 each
# and the PUF-only candidate weighs 10.0 (capacity 130.0); the sole anchored
# candidate is source 0 (reporter floor 20.0).
_BAND_CAPACITY = 130.0
_REPORTER_FLOOR = 20.0
_ANCHORED_SOURCE_NUMBERS = {"0", "6"}


def _expected_prior(
    target: float,
    capacity: float = _BAND_CAPACITY,
    floor: float = _REPORTER_FLOOR,
) -> float:
    """The anchored-mass-corrected count-truthful threshold (#507/#508).

    Anchors are always selected, so expected delivered mass at non-anchor
    threshold p is floor + p*(capacity - floor); solving for the target
    gives (target - floor) / (capacity - floor). Saturated bands fall back
    to the reporter rate; an anchor floor at/above the target draws zero.
    """

    if capacity <= target:
        return min(floor / capacity, 1.0)
    if floor >= target:
        return 0.0
    return (target - floor) / (capacity - floor)


def _expected_bernoulli_flag(source_id: str, prior: float, *, seed: int = 17) -> bool:
    """The selection law: anchors unconditionally, else draw below prior."""

    if source_id.split(":")[1] in _ANCHORED_SOURCE_NUMBERS:
        return True
    return _stable_source_draw(source_id, seed=seed) < prior


def _frame(*, stale_output: bool = False) -> tuple[Frame, np.ndarray]:
    """Build three age bands with ASEC/PUF clones and PUF-only support."""

    rows: list[dict[str, object]] = []
    potential: list[float] = []
    person_id = 0
    for band, age in _AGES.items():
        for source_number in range(9):
            if source_number <= 5 or source_number == 8:
                channels = ("asec", "puf_tax_detail")
            elif source_number == 6:
                channels = ("asec",)
            else:
                channels = ("puf_tax_detail",)
            candidate = source_number <= 5 or source_number == 7
            reporter = source_number in {0, 6}
            for channel in channels:
                rows.append(
                    {
                        "person_id": person_id,
                        "person_household_id": person_id,
                        "person_tax_unit_id": person_id,
                        "person_spm_unit_id": person_id,
                        "person_family_id": person_id,
                        "person_marital_unit_id": person_id,
                        "age": age,
                        # PUF copies can carry SSI_VAL, but only direct ASEC
                        # rows are independent reporter anchors.
                        US_SSI_TAKE_UP_ANCHOR: 1_200.0 if reporter else 0.0,
                        "person_source_id": f"{band}:{source_number}",
                        "person_support_channel": channel,
                        _OUTPUT: bool((person_id % 2) == 0) if stale_output else False,
                    }
                )
                potential.append(100.0 if candidate else 0.0)
                person_id += 1

    person = pd.DataFrame(rows)
    ids = person["person_id"].to_numpy()
    tables = {
        "person": person,
        "household": pd.DataFrame({"household_id": ids}),
        "tax_unit": pd.DataFrame({"tax_unit_id": ids}),
        "spm_unit": pd.DataFrame({"spm_unit_id": ids}),
        "family": pd.DataFrame({"family_id": ids}),
        "marital_unit": pd.DataFrame({"marital_unit_id": ids}),
    }
    frame = Frame(
        tables,
        US_SCHEMA,
        {
            "household": Weights(
                values=np.full(len(person), 10.0),
                kind=WeightKind.DESIGN,
            )
        },
    )
    return frame, np.asarray(potential, dtype=np.float64)


def _stacked_frame() -> tuple[Frame, np.ndarray]:
    """Convert the legacy operator fixture to physical ASEC/ACS channels."""

    frame, potential = _frame()
    person = frame.table("person").copy()
    source_number = person["person_source_id"].str.rsplit(":").str[-1].astype(int)
    legacy_roles = person["person_support_channel"].copy()
    person["person_spine_source_id"] = person["person_source_id"]
    person["person_support_clone_index"] = np.where(
        legacy_roles.eq("asec"),
        0,
        1,
    )
    person["person_support_channel"] = np.where(
        source_number.le(6),
        "asec",
        "acs",
    )
    acs_source = person["person_support_channel"].eq("acs")
    person.loc[acs_source, US_SSI_TAKE_UP_ANCHOR] = np.nan
    return _replace_person(frame, person), potential


def _replace_person(frame: Frame, person: pd.DataFrame) -> Frame:
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    tables["person"] = person
    return Frame(
        tables,
        frame.schema,
        {entity: frame.weights_for(entity) for entity in frame.weighted_entities},
        frame.strata,
        mass_log=frame.mass_log,
    )


def _assigned(
    *,
    seed: int = 17,
    targets: dict[str, float] | None = None,
    stale_output: bool = False,
) -> tuple[Frame, Frame, np.ndarray, dict[str, object]]:
    frame, potential = _frame(stale_output=stale_output)
    result, diagnostics = with_us_ssi_take_up(
        frame,
        uncapped_ssi=potential,
        seed=seed,
        targets=targets or _TARGETS,
    )
    return frame, result, potential, diagnostics


# --- Delivered-weight prior basis + hard delivery gate (microcosm#507/#508) ---

_BASIS_SHA = "ab" * 32


def _artifact_basis(
    *,
    capacities: dict[str, float],
    floors: dict[str, float] | None = None,
) -> SSITakeUpPriorBasis:
    resolved_floors = floors or {key: _REPORTER_FLOOR for key in capacities}
    return SSITakeUpPriorBasis(
        kind=US_SSI_TAKE_UP_PRIOR_BASIS_RELEASE_ARTIFACT,
        bands=tuple(
            SSITakeUpBandPriorBasis(
                key=band.key,
                candidate_capacity=float(capacities[band.key]),
                reporter_candidate_floor=float(resolved_floors[band.key]),
            )
            for band in US_SSI_TAKE_UP_AGE_TARGETS
        ),
        source_sha256=_BASIS_SHA,
        source_schema_version=2,
    )


def _release_final_diagnostics() -> dict[str, object]:
    """Genuine final-measurement diagnostics — what us_ssi_take_up.json holds."""

    _, result, potential, stage_diagnostics = _assigned()
    stage_priors = {
        band["age_band"]: band["assignment_prior"]
        for band in stage_diagnostics["age_bands"]
    }
    return us_ssi_take_up_diagnostics(
        result,
        uncapped_ssi=potential,
        seed=17,
        targets=_TARGETS,
        assignment_priors=stage_priors,
        prior_basis=ssi_take_up_prior_basis_from_diagnostics(stage_diagnostics),
    )


def _delivered(diagnostics: dict[str, object], **selected: float) -> dict[str, object]:
    delivered = copy.deepcopy(diagnostics)
    # Delivery is judged on the final release-weight measurement only; the
    # tampered fixture emulates that payload.
    delivered["measurement_phase"] = "release_final"
    for band in delivered["age_bands"]:
        key = str(band["age_band"])
        if key in selected:
            band["selected_recipient_weight"] = float(selected[key])
    return delivered


# --- Location clones (block_location.clone_frame_for_location) ---
#
# A location clone is a distinct copy of its support row that differs only
# in location: it keeps person_source_id, the support channel and the support
# clone index, gains person_location_clone_index, and carries w/K. SSI take-up
# must key copies on (source, channel, clone index, location clone index) and
# keep one Bernoulli decision per source person across every copy.

_LOCATION_CLONE_INDEX = location_clone_index_column("person")


def _clone_indexed_frame() -> tuple[Frame, np.ndarray]:
    """The legacy fixture with explicit support clone indices (ASEC 0, PUF 1)."""

    frame, potential = _frame()
    person = frame.table("person").copy()
    person["person_support_clone_index"] = np.where(
        person["person_support_channel"].eq("asec"), 0, 1
    )
    return _replace_person(frame, person), potential


def _located(
    frame: Frame, potential: np.ndarray, clones: int
) -> tuple[Frame, np.ndarray]:
    """Location-clone ``frame`` ``clones`` times; person rows repeat adjacently."""

    return (
        clone_frame_for_location(frame, clones),
        np.repeat(np.asarray(potential, dtype=np.float64), clones),
    )


def _release_final_of(
    result: Frame,
    potential: np.ndarray,
    stage_diagnostics: dict[str, object],
    *,
    seed: int = 17,
    targets: dict[str, float] | None = None,
) -> dict[str, object]:
    """Diagnose ``result``'s persisted flags as the release-final measurement."""

    return us_ssi_take_up_diagnostics(
        result,
        uncapped_ssi=potential,
        seed=seed,
        targets=targets or _TARGETS,
        assignment_priors={
            band["age_band"]: band["assignment_prior"]
            for band in stage_diagnostics["age_bands"]
        },
        prior_basis=ssi_take_up_prior_basis_from_diagnostics(stage_diagnostics),
    )


def _source_decisions(result: Frame) -> pd.Series:
    """One flag per source person, asserting every copy carries it."""

    grouped = result.table("person").groupby("person_source_id", sort=True)[_OUTPUT]
    assert grouped.nunique().eq(1).all()
    return grouped.first().astype(bool)


def _per_source_person_weight(frame: Frame) -> pd.Series:
    """Resolved person weight summed over every copy of each source person."""

    return (
        pd.Series(
            np.asarray(frame.resolve_weights("person").values, dtype=np.float64),
            index=frame.table("person")["person_source_id"].to_numpy(),
        )
        .groupby(level=0, sort=True)
        .sum()
    )


def _assert_nested_close(
    actual: object, expected: object, *, rel: float = 1e-12, path: str = "$"
) -> None:
    """Exact on structure, strings, bools and ints; ``rel`` on floats.

    Location cloning splits each weight into ``K`` parts, so a float sum over
    copies may differ from the ``K = 1`` sum in its last bits.
    """

    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), path
        for key in expected:
            _assert_nested_close(
                actual[key], expected[key], rel=rel, path=f"{path}.{key}"
            )
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), path
        for position, (left, right) in enumerate(zip(actual, expected, strict=True)):
            _assert_nested_close(left, right, rel=rel, path=f"{path}[{position}]")
    elif isinstance(expected, float) and not isinstance(expected, bool):
        assert isinstance(actual, float), path
        assert actual == pytest.approx(expected, rel=rel, abs=1e-9), path
    else:
        assert type(actual) is type(expected) and actual == expected, path


def _without_channel_rows(diagnostics: dict[str, object]) -> dict[str, object]:
    """Diagnostics minus per-channel row counts, the only K-scaled field."""

    stripped = copy.deepcopy(diagnostics)
    for values in stripped["channel_diagnostics"].values():
        values.pop("rows")
    return stripped


def _person_frame(person: pd.DataFrame, household_weight: np.ndarray) -> Frame:
    """Wrap one-person households the way :func:`_frame` does."""

    ids = person["person_id"].to_numpy()
    return Frame(
        {
            "person": person,
            "household": pd.DataFrame({"household_id": ids}),
            "tax_unit": pd.DataFrame({"tax_unit_id": ids}),
            "spm_unit": pd.DataFrame({"spm_unit_id": ids}),
            "family": pd.DataFrame({"family_id": ids}),
            "marital_unit": pd.DataFrame({"marital_unit_id": ids}),
        },
        US_SCHEMA,
        {
            "household": Weights(
                values=np.asarray(household_weight, dtype=np.float64),
                kind=WeightKind.DESIGN,
            )
        },
    )


#: Synthetic household weights are multiples of 12, so ``w / K`` is exact for
#: every K in 1..4 and per-source mass is conserved bit for bit.
_EXACT_SPLIT_WEIGHT_UNIT = 12.0


def _synthetic_frame(
    sources: list[dict[str, object]], *, clone_indexed: bool
) -> tuple[Frame, np.ndarray]:
    """One person row per (source, channel), each in its own household.

    Each source carries ``band`` (an age-band key), ``copies`` (a list of
    ``(channel, candidate, weight_units)``), and ``reporter`` (its ASEC row
    reports SSI_VAL > 0). Household weight is ``weight_units *``
    :data:`_EXACT_SPLIT_WEIGHT_UNIT`.
    """

    rows: list[dict[str, object]] = []
    potential: list[float] = []
    weights: list[float] = []
    for number, source in enumerate(sources):
        for channel, candidate, weight_units in source["copies"]:
            person_id = len(rows)
            row: dict[str, object] = {
                "person_id": person_id,
                "person_household_id": person_id,
                "person_tax_unit_id": person_id,
                "person_spm_unit_id": person_id,
                "person_family_id": person_id,
                "person_marital_unit_id": person_id,
                "age": _AGES[str(source["band"])],
                US_SSI_TAKE_UP_ANCHOR: (
                    1_200.0 if source["reporter"] and channel == "asec" else 0.0
                ),
                "person_source_id": f"{source['band']}:{number}",
                "person_support_channel": channel,
                _OUTPUT: False,
            }
            if clone_indexed:
                row["person_support_clone_index"] = 0 if channel == "asec" else 1
            rows.append(row)
            potential.append(100.0 if candidate else 0.0)
            weights.append(float(weight_units) * _EXACT_SPLIT_WEIGHT_UNIT)
    return (
        _person_frame(pd.DataFrame(rows), np.asarray(weights)),
        np.asarray(potential, dtype=np.float64),
    )


# --- K = 1 golden (byte-identical to the pre-location-clone code) ---
#
# Computed by running exactly these helpers (_golden_digest, _table_payload,
# _scenario_payload, _duplicate_message) against the ORIGINAL ssi_take_up.py
# at the parent of this change (PR #1047 head 4324432e5), on the fixtures
# above, with seed 17 and _TARGETS. A K = 1 frame carries no
# person_location_clone_index column, so the new code must reproduce the
# assignment flags, both diagnostics payloads, the row/source tables and the
# duplicate-identity error text exactly.

_K1_GOLDEN_SCENARIOS = {
    "legacy_channel_only": _frame,
    "support_clone_indexed": _clone_indexed_frame,
    "stacked_assembled": _stacked_frame,
}
_K1_GOLDEN_DIGESTS = {
    "legacy_channel_only": (
        "c33244a20fb6d31ba625725d4189d78ce59a046d1296e52070b3e656b5cf21d1"
    ),
    "support_clone_indexed": (
        "68172ec5994bb2c5e20d69e2dacbda41d37cd23709dfd56df3ae62de8fdfa154"
    ),
    "stacked_assembled": (
        "68172ec5994bb2c5e20d69e2dacbda41d37cd23709dfd56df3ae62de8fdfa154"
    ),
}
_K1_DUPLICATE_MESSAGES = {
    "legacy_channel_only": (
        "US SSI take-up requires at most one row per clone-aware support "
        "identity ['source_id', 'channel']; duplicate examples "
        "[{'source_id': 'under_18:0', 'channel': 'asec'}]."
    ),
    "support_clone_indexed": (
        "US SSI take-up requires at most one row per clone-aware support "
        "identity ['source_id', 'channel', 'clone_index']; duplicate examples "
        "[{'source_id': 'under_18:0', 'channel': 'asec', 'clone_index': 0}]."
    ),
}


def _golden_digest(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode()).hexdigest()


def _table_payload(table: pd.DataFrame) -> dict[str, object]:
    return {
        "columns": [str(column) for column in table.columns],
        "index": [str(value) for value in table.index.tolist()],
        "values": {str(column): table[column].tolist() for column in table.columns},
    }


def _scenario_payload(frame: Frame, potential: np.ndarray) -> dict[str, object]:
    result, diagnostics = with_us_ssi_take_up(
        frame, uncapped_ssi=potential, seed=17, targets=_TARGETS
    )
    priors = {
        band["age_band"]: band["assignment_prior"] for band in diagnostics["age_bands"]
    }
    final = us_ssi_take_up_diagnostics(
        result,
        uncapped_ssi=potential,
        seed=17,
        targets=_TARGETS,
        assignment_priors=priors,
        prior_basis=ssi_take_up_prior_basis_from_diagnostics(diagnostics),
    )
    rows, source = _source_table(frame, uncapped_ssi=potential, seed=17)
    return {
        "flags": result.table("person")[_OUTPUT].astype(bool).tolist(),
        "assignment_diagnostics": diagnostics,
        "release_final_diagnostics": final,
        "rows": _table_payload(rows),
        "source": _table_payload(source),
    }


def _duplicate_message(frame: Frame, potential: np.ndarray) -> str:
    """Relabel row 1 (under_18:0's PUF copy) as a second ASEC copy."""

    person = frame.table("person").copy()
    person.loc[person.index[1], "person_support_channel"] = "asec"
    if "person_support_clone_index" in person:
        person.loc[person.index[1], "person_support_clone_index"] = 0
    try:
        with_us_ssi_take_up(
            _replace_person(frame, person),
            uncapped_ssi=potential,
            seed=17,
            targets=_TARGETS,
        )
    except ValueError as error:
        return str(error)
    raise AssertionError("expected a duplicate refusal")


__all__ = [name for name in globals() if not name.startswith("__")]
