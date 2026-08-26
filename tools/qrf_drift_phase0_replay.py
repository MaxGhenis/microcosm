"""Shared, forest-free QRF replay primitives for the Phase-0 executors.

This module is deliberately small enough to audit against the production
transfer code.  It reads only the checkpoint columns needed to reconstruct the
gate fit surfaces and restores the pattern state recorded in the target banks.
It does not execute magnitude forests or mutate any pinned artifact.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd

from microcosm.build import frame_checkpoint

ZERO_ATOL = 1e-6

REQ_PERSON = (
    "age",
    "is_female",
    "__acs_transfer_state_fips",
)
OPT_PERSON = (
    "__acs_transfer_employment_income",
    "__acs_transfer_self_employment_income",
    "__acs_transfer_social_security_income",
    "__acs_transfer_retirement_income",
    "__acs_transfer_interest_dividend_rental_income",
    "__acs_transfer_is_household_head",
    "__acs_transfer_tenure_code",
)
REQ_GROUP = (
    "__acs_transfer_person_count",
    "__acs_transfer_age_sum",
    "__acs_transfer_female_count",
    "__acs_transfer_state_fips",
)
GROUP_NAME = {
    "__acs_transfer_employment_income": (
        "__acs_transfer_group_employment_income_sum"
    ),
    "__acs_transfer_self_employment_income": (
        "__acs_transfer_group_self_employment_income_sum"
    ),
    "__acs_transfer_social_security_income": (
        "__acs_transfer_group_social_security_income_sum"
    ),
    "__acs_transfer_retirement_income": (
        "__acs_transfer_group_retirement_income_sum"
    ),
    "__acs_transfer_interest_dividend_rental_income": (
        "__acs_transfer_group_investment_income_sum"
    ),
    "__acs_transfer_is_household_head": "__acs_transfer_group_head_count",
    "__acs_transfer_tenure_code": "__acs_transfer_group_tenure_code",
}
OPT_GROUP = tuple(GROUP_NAME[name] for name in OPT_PERSON)

SS_COMPONENTS = (
    "social_security_retirement",
    "social_security_disability",
    "social_security_dependents",
    "social_security_survivors",
)
RET_COMPONENTS = (
    "taxable_private_pension_income",
    "tax_exempt_private_pension_income",
    "taxable_ira_distributions",
)
INV_COMPONENTS = (
    "taxable_interest_income",
    "tax_exempt_interest_income",
    "qualified_dividend_income",
    "non_qualified_dividend_income",
    "rental_income",
    "estate_income",
)
TENURE_CODES = {
    "NONE": 0.0,
    "OWNED_WITH_MORTGAGE": 1.0,
    "OWNED WITH MORTGAGE": 1.0,
    "OWNER_WITH_MORTGAGE": 1.0,
    "OWNER WITH MORTGAGE": 1.0,
    "OWNED_OUTRIGHT": 2.0,
    "OWNED OUTRIGHT": 2.0,
    "OWNER_WITHOUT_MORTGAGE": 2.0,
    "OWNER WITHOUT MORTGAGE": 2.0,
    "RENTED": 3.0,
    "RENTER": 3.0,
}


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def mapping_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def weight_identity(weights: np.ndarray) -> str:
    values = np.asarray(weights)
    digest = hashlib.sha256()
    digest.update(values.dtype.str.encode("ascii"))
    digest.update(str(values.shape).encode("ascii"))
    digest.update(np.ascontiguousarray(values).tobytes(order="C"))
    return digest.hexdigest()


def as_float(values: np.ndarray) -> np.ndarray:
    return pd.Series(values, copy=False).to_numpy(
        dtype=np.float64,
        na_value=np.nan,
        copy=False,
    )


def complete_sum(columns: list[np.ndarray]) -> np.ndarray:
    result = as_float(columns[0]).copy()
    for values in columns[1:]:
        result += as_float(values)
    return result


def tenure_values(values: np.ndarray) -> np.ndarray:
    result = np.full(len(values), np.nan, dtype=np.float64)
    invalid: list[str] = []
    for position, raw in enumerate(values):
        if pd.isna(raw):
            continue
        if isinstance(raw, bytes):
            raw = raw.decode()
        name = getattr(raw, "name", None)
        key = str(name if name is not None else raw).upper()
        if key not in TENURE_CODES:
            invalid.append(str(raw))
            continue
        result[position] = TENURE_CODES[key]
    if invalid:
        raise ValueError(f"unsupported tenure value(s): {invalid[:5]}")
    return result


class SelectedCheckpoint:
    """Column-selective reader for a populace-frame checkpoint."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.h5 = h5py.File(path, "r")
        self.root = self.h5["_populace_frame_checkpoint"]
        self.metadata = json.loads(bytes(self.root["metadata_json"][:]).decode())
        self.table_index = {
            table["name"]: position
            for position, table in enumerate(self.metadata["tables"])
        }
        self.loaded: list[str] = []

    def column(self, table_name: str, column_name: str) -> np.ndarray:
        table_position = self.table_index[table_name]
        table = self.metadata["tables"][table_position]
        column_position = next(
            position
            for position, spec in enumerate(table["columns"])
            if spec["name"] == column_name
        )
        spec = table["columns"][column_position]
        group = self.root[
            f"tables/t{table_position:05d}/columns/c{column_position:05d}"
        ]
        series = frame_checkpoint._read_series(
            group,
            spec,
            self.path,
            label=f"{table_name}.{column_name}",
        )
        self.loaded.append(f"{table_name}.{column_name}")
        return series.to_numpy(copy=False)

    def household_weights(self) -> np.ndarray:
        specs = self.metadata["weights"]
        position = next(
            position
            for position, spec in enumerate(specs)
            if spec["entity"] == "household"
        )
        self.loaded.append("@weights.household")
        return np.asarray(
            self.root[f"weights/w{position:05d}"][:],
            dtype=np.float64,
        )

    def close(self) -> None:
        self.h5.close()


def broadcast_by_id(
    source_ids: np.ndarray,
    source_values: np.ndarray,
    membership: np.ndarray,
) -> np.ndarray:
    positions = np.searchsorted(source_ids, membership)
    if (
        (positions < 0).any()
        or (positions >= len(source_ids)).any()
        or not np.array_equal(source_ids[positions], membership)
    ):
        raise ValueError("membership does not resolve exactly against sorted ids")
    return np.asarray(source_values)[positions]


def load_person_inputs(
    checkpoint: SelectedCheckpoint,
    targets: set[str],
) -> dict[str, np.ndarray]:
    person_names = {
        "person_id",
        "person_source_id",
        "person_household_id",
        "person_spm_unit_id",
        "person_support_channel",
        "person_support_clone_index",
        "age",
        "is_female",
        "is_household_head",
        "employment_income_before_lsr",
        "self_employment_income_before_lsr",
        "acs_social_security_income",
        "acs_retirement_income",
        "acs_interest_dividend_rental_income",
        *SS_COMPONENTS,
        *RET_COMPONENTS,
        *INV_COMPONENTS,
        *targets,
    }
    available = {
        spec["name"]
        for spec in checkpoint.metadata["tables"][
            checkpoint.table_index["person"]
        ]["columns"]
    }
    result = {
        name: checkpoint.column("person", name)
        for name in sorted(person_names & available)
    }
    for name in ("household_id", "state_fips", "tenure_type"):
        result[f"household.{name}"] = checkpoint.column("household", name)
    for name in (
        "spm_unit_id",
        "spm_unit_support_channel",
        "spm_unit_support_clone_index",
    ):
        result[f"spm_unit.{name}"] = checkpoint.column("spm_unit", name)
    result["household.weight"] = checkpoint.household_weights()
    return result


def person_surface(
    inputs: dict[str, np.ndarray],
    *,
    role: str,
) -> dict[str, np.ndarray]:
    if role not in {"donor", "recipient"}:
        raise ValueError(f"unknown person feature role {role!r}")
    household_id = inputs["household.household_id"]
    membership = inputs["person_household_id"]
    state = broadcast_by_id(
        household_id,
        inputs["household.state_fips"],
        membership,
    )
    tenure = broadcast_by_id(
        household_id,
        tenure_values(inputs["household.tenure_type"]),
        membership,
    )
    return {
        "age": as_float(inputs["age"]),
        "is_female": as_float(inputs["is_female"]),
        "__acs_transfer_state_fips": as_float(state),
        "__acs_transfer_employment_income": as_float(
            inputs["employment_income_before_lsr"]
        ),
        "__acs_transfer_self_employment_income": as_float(
            inputs["self_employment_income_before_lsr"]
        ),
        "__acs_transfer_social_security_income": (
            complete_sum([inputs[name] for name in SS_COMPONENTS])
            if role == "donor" and all(name in inputs for name in SS_COMPONENTS)
            else as_float(inputs["acs_social_security_income"])
        ),
        "__acs_transfer_retirement_income": (
            complete_sum([inputs[name] for name in RET_COMPONENTS])
            if role == "donor" and all(name in inputs for name in RET_COMPONENTS)
            else as_float(inputs["acs_retirement_income"])
        ),
        "__acs_transfer_interest_dividend_rental_income": (
            complete_sum([inputs[name] for name in INV_COMPONENTS])
            if role == "donor" and all(name in inputs for name in INV_COMPONENTS)
            else as_float(inputs["acs_interest_dividend_rental_income"])
        ),
        "__acs_transfer_is_household_head": as_float(
            inputs["is_household_head"]
        ),
        "__acs_transfer_tenure_code": tenure,
    }


def person_weights(inputs: dict[str, np.ndarray]) -> np.ndarray:
    return broadcast_by_id(
        inputs["household.household_id"],
        inputs["household.weight"],
        inputs["person_household_id"],
    ).astype(np.float64, copy=False)


def group_surface(
    person: dict[str, np.ndarray],
    person_spm_membership: np.ndarray,
    spm_ids: np.ndarray,
) -> dict[str, np.ndarray]:
    positions = np.searchsorted(spm_ids, person_spm_membership)
    if not np.array_equal(spm_ids[positions], person_spm_membership):
        raise ValueError("person SPM membership does not resolve")
    n_groups = len(spm_ids)
    counts = np.bincount(positions, minlength=n_groups).astype(np.float64)
    age_sum = np.bincount(
        positions,
        weights=person["age"],
        minlength=n_groups,
    ).astype(np.float64)
    female_sum = np.bincount(
        positions,
        weights=person["is_female"],
        minlength=n_groups,
    ).astype(np.float64)

    person_state = person["__acs_transfer_state_fips"]
    finite_state = np.isfinite(person_state)
    state_counts = np.bincount(
        positions,
        weights=finite_state.astype(np.int64),
        minlength=n_groups,
    )
    state_low = np.full(n_groups, np.inf, dtype=np.float64)
    state_high = np.full(n_groups, -np.inf, dtype=np.float64)
    np.minimum.at(state_low, positions[finite_state], person_state[finite_state])
    np.maximum.at(state_high, positions[finite_state], person_state[finite_state])
    if ((state_counts > 0) & (state_low != state_high)).any():
        raise ValueError("SPM unit spans states")
    state = np.full(n_groups, np.nan, dtype=np.float64)
    state_complete = (counts > 0) & (state_counts == counts)
    state[state_complete] = state_low[state_complete]

    result = {
        "__acs_transfer_person_count": counts,
        "__acs_transfer_age_sum": age_sum,
        "__acs_transfer_female_count": female_sum,
        "__acs_transfer_state_fips": state,
    }
    total_counts = np.bincount(positions, minlength=n_groups)
    for person_name, group_name in GROUP_NAME.items():
        values = person[person_name]
        finite = np.isfinite(values)
        observed = np.bincount(
            positions,
            weights=finite.astype(np.int64),
            minlength=n_groups,
        )
        complete = observed == total_counts
        if person_name == "__acs_transfer_tenure_code":
            low = np.full(n_groups, np.inf, dtype=np.float64)
            high = np.full(n_groups, -np.inf, dtype=np.float64)
            np.minimum.at(low, positions[finite], values[finite])
            np.maximum.at(high, positions[finite], values[finite])
            group_values = np.full(n_groups, np.nan, dtype=np.float64)
            consistent = complete & (low == high)
            group_values[consistent] = low[consistent]
        else:
            group_values = np.bincount(
                positions,
                weights=np.where(finite, values, 0.0),
                minlength=n_groups,
            ).astype(np.float64)
            group_values[~complete] = np.nan
        result[group_name] = group_values
    return result


def group_weights(
    person_weight_values: np.ndarray,
    person_spm_membership: np.ndarray,
    spm_ids: np.ndarray,
) -> np.ndarray:
    positions = np.searchsorted(spm_ids, person_spm_membership)
    n_groups = len(spm_ids)
    low = np.full(n_groups, np.inf, dtype=np.float64)
    high = np.full(n_groups, -np.inf, dtype=np.float64)
    np.minimum.at(low, positions, person_weight_values)
    np.maximum.at(high, positions, person_weight_values)
    if (low != high).any():
        raise ValueError("SPM group members carry unequal household weights")
    return low


def subset_surface(
    surface: dict[str, np.ndarray],
    mask: np.ndarray,
) -> dict[str, np.ndarray]:
    return {name: values[mask] for name, values in surface.items()}


def make_patterns(
    recipient: dict[str, np.ndarray],
    required: tuple[str, ...],
    optional: tuple[str, ...],
) -> list[dict[str, Any]]:
    eligible = np.ones(len(next(iter(recipient.values()))), dtype=bool)
    for name in required:
        eligible &= np.isfinite(recipient[name])
    if not eligible.all():
        raise ValueError(
            f"{int((~eligible).sum())} recipient rows have incomplete required "
            "predictors"
        )
    codes = np.zeros(len(eligible), dtype=np.uint16)
    for bit, name in enumerate(optional):
        codes |= np.isfinite(recipient[name]).astype(np.uint16) << bit
    patterns: list[dict[str, Any]] = []
    for position, code in enumerate(np.unique(codes[eligible])):
        observed = tuple(
            name
            for bit, name in enumerate(optional)
            if int(code) & (1 << bit)
        )
        indexes = np.flatnonzero(eligible & (codes == code))
        digest = hashlib.sha256("\0".join(observed).encode()).hexdigest()[:8]
        patterns.append(
            {
                "name": f"pattern_{position:02d}_{digest}",
                "observed": observed,
                "positions": indexes,
                "code": int(code),
            }
        )
    return patterns


def load_bank(
    path: Path,
    cache: dict[Path, dict[str, Any]],
) -> dict[str, Any]:
    if path in cache:
        return cache[path]
    with h5py.File(path, "r") as h5:
        metadata = json.loads(bytes(h5["metadata_json"][:]).decode())
        bits = np.asarray(h5["raw_draw_bits"][:], dtype="<u8")
    raw = bits.view("<f8")
    actual_raw_sha = hashlib.sha256(bits.tobytes(order="C")).hexdigest()
    if actual_raw_sha != metadata["raw_draw_sha256"]:
        raise ValueError(f"raw draw SHA mismatch for {path}")
    value = {"path": path, "metadata": metadata, "raw": raw}
    cache[path] = value
    return value


def find_bank_for_target(directory: Path, target: str) -> Path:
    candidates = sorted(directory.glob(f"*__{target}.h5"))
    if len(candidates) != 1:
        raise ValueError(
            f"expected one bank for {target!r} in {directory}, got {candidates}"
        )
    return candidates[0]


def initial_state(after: dict[str, Any]) -> dict[str, Any]:
    state = copy.deepcopy(after)
    state["completed_targets"] = []
    state["recipient_index"] = None
    seed = state["model_config"]["seed"]
    fit_seed, draw_seed = np.random.SeedSequence(seed).spawn(2)
    state["fit_rng_state"] = np.random.default_rng(fit_seed).bit_generator.state
    state["draw_rng_state"] = np.random.default_rng(draw_seed).bit_generator.state
    return state


def state_before_for_pattern(
    current: dict[str, Any],
    pattern_name: str,
    bank_cache: dict[Path, dict[str, Any]],
) -> tuple[dict[str, Any], str, str]:
    metadata = current["metadata"]
    descriptor = metadata["target"]
    step = next(
        item
        for item in metadata["pattern_steps"]
        if item["pattern"] == pattern_name
    )
    after = step["state_after"]
    if len(after["completed_targets"]) == 1:
        state = initial_state(after)
        source = "reconstructed_start_chain"
    else:
        current_target = descriptor["model_target"]
        model_targets = descriptor["model_targets"]
        current_position = model_targets.index(current_target)
        previous_target = model_targets[current_position - 1]
        previous_path = find_bank_for_target(
            Path(current["path"]).parent,
            previous_target,
        )
        previous = load_bank(previous_path, bank_cache)
        previous_step = next(
            item
            for item in previous["metadata"]["pattern_steps"]
            if item["pattern"] == pattern_name
        )
        state = copy.deepcopy(previous_step["state_after"])
        source = str(previous_path)
    return state, mapping_sha256(state), source


def sign_labels(values: np.ndarray) -> np.ndarray:
    result = np.zeros(len(values), dtype=np.int8)
    result[values > ZERO_ATOL] = 1
    result[values < -ZERO_ATOL] = -1
    return result


def label_name(label: int) -> str:
    return {-1: "negative", 0: "zero", 1: "positive"}[int(label)]
