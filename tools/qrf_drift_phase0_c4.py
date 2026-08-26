#!/usr/bin/env python3
"""Run the A14/A15/A16 Phase-0 C4 exchangeability control.

The control restores each production gate from its bank state, allocates one
target-level evaluation budget across the registered pattern-by-GQ strata, and
constructs two iid fit-weight PPS samples per pattern and replicate:

* ``R0`` from the C4-specific stream is the synthetic recipient endpoint.
* ``d(j)`` from the P2 donor stream supplies coalition substitutions.

Only ``v_null(all) - v_null(empty)`` for each present nonzero sign class is a
stochastic C4 gate.  Null Shapley and per-prior values are retained as paired
replicate baselines for P2; they are descriptive and are never tested against
zero.  Magnitude forests are neither loaded nor refit.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import qrf_drift_phase0_replay as replay
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier

WORKTREE = Path(__file__).resolve().parents[1]
D0_JSON = WORKTREE / "experiments/qrf_drift_validation_d0.json"
DESIGN_MD = WORKTREE / "experiments/qrf_drift_validation_design.md"
A16_BINDING = WORKTREE / "experiments/qrf_drift_validation_a16_binding_texts.md"
DEFAULT_C0B = Path("/tmp/qrf_phase0_v22_c0b.json")
DEFAULT_OUT = Path("/tmp/qrf_phase0_a17_c4.json")
DEFAULT_PARTIAL = Path("/tmp/qrf_phase0_a17_c4.partial.json")

EXPECTED_AUTHORITY_DIGESTS = {
    str(D0_JSON): "fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8",
    str(DESIGN_MD): "a91d19cc6a3c7e55db28159189ce0ccc76ddbf972247a20cc6eabbb59d5719bc",
    str(A16_BINDING): "7e288bce7496e1e7f41e33f078be2043673ca54ff31182caf2ce92eab68a81c1",
}
EXPECTED_CHECKPOINT_DIGESTS = {
    "assembled.checkpoint.h5": (
        "eb25f70bb3a93ba2e749a21f4b85adde99327dd00264c66be2417fde0be20b05"
    ),
    "transferred.checkpoint.h5": (
        "fc9d196bdb19ab55a67dccb2c9fb484e533310c2d42ae7c7c6ac4ef1eb8d05fd"
    ),
}
EXPECTED_PREDECESSOR_DIGESTS = {
    "000__is_incapable_of_self_care.h5": (
        "bb2d1b151c3593e280433285fb6fa1e27554391932e359a1d2c2eb80e56c80e0"
    ),
    "038__previous_year_income_available.h5": (
        "724e123628ad0878cfbbe89dfde3c21f7ba5453cdaa091487aaf13feabfb0835"
    ),
    "018__tax_exempt_private_pension_income.h5": (
        "0aa26da0fd2e6286081eba0616e488a14d0567eeae41b756d2ae5a6a8a84f908"
    ),
}
EXPECTED_C0B_SHA256 = (
    "1c7bfd65660b14068c4bc96fae4b8d270cb447ea8fbbe42c8ef982c5f1dbf542"
)

INITIAL_REPLICATES = 250
ESCALATED_REPLICATES = 1_000
MAX_TARGET_SAMPLE = 100_000
OVERALL_CONTROL_K = 122
C4_STOCHASTIC_K = 40
Z_STAR = 3.526967430023352
OVERALL_ROSTER_SHA256 = (
    "348386d9675172b65550ef7cb157fb1387e1d45331f61253aefe40dbe8f2bbc9"
)
GROUP_BITS = {"G1": 1, "G2": 2, "G3": 4}
GROUP_ORDER = ("G1", "G2", "G3")
GQ_ORDER = ("H", "2", "3", "U")


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def array_identity(values: np.ndarray) -> dict[str, Any]:
    array = np.ascontiguousarray(values)
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": hashlib.sha256(array.tobytes(order="C")).hexdigest(),
    }


def peak_rss_mb() -> float:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return float(raw) / (1024.0 * 1024.0)
    return float(raw) / 1024.0


def seed_from_label(label: str) -> int:
    return int.from_bytes(
        hashlib.sha256(label.encode("utf-8")).digest()[:8],
        "big",
        signed=False,
    )


def r0_label(target: str, pattern: str, replicate: int) -> str:
    return f"qrf-drift-v2.3|C4|r0|{target}|{pattern}|{replicate}"


def donor_label(target: str, pattern: str, replicate: int) -> str:
    return f"qrf-drift-v2|P2|donor|{target}|{pattern}|{replicate}"


def p2_rows_label(
    target: str,
    pattern: str,
    gq: str,
    replicate: int,
) -> str:
    return f"qrf-drift-v2|P2|rows|{target}|{replicate}|{pattern}|{gq}"


def weighted_choice(
    label: str,
    probabilities: np.ndarray,
    size: int,
) -> np.ndarray:
    """Apply the A15.5 choice contract with a fresh generator per label."""
    rng = np.random.Generator(np.random.PCG64(seed_from_label(label)))
    return rng.choice(
        len(probabilities),
        size=size,
        replace=True,
        p=probabilities,
    ).astype(np.int64, copy=False)


def _gq_codes(values: np.ndarray) -> np.ndarray:
    """Encode household TYPEHUGQ as H/2/3/U without casting nulls."""
    result = np.full(len(values), 9, dtype=np.int8)
    invalid: list[str] = []
    for position, raw in enumerate(np.asarray(values, dtype=object)):
        if raw is None:
            continue
        if isinstance(raw, bytes):
            raw = raw.decode()
        try:
            if bool(np.asarray(raw != raw).item()):
                continue
        except (TypeError, ValueError):
            pass
        text = str(getattr(raw, "name", raw)).upper()
        if text in {"1", "H", "HOUSING_UNIT", "HOUSING UNIT"}:
            result[position] = 1
        elif text in {"2", "INSTITUTIONAL"}:
            result[position] = 2
        elif text in {"3", "NONINSTITUTIONAL", "NON-INSTITUTIONAL"}:
            result[position] = 3
        else:
            invalid.append(str(raw))
    if invalid:
        raise ValueError(f"unsupported TYPEHUGQ value(s): {invalid[:5]}")
    return result


def _gq_key(values: np.ndarray) -> np.ndarray:
    result = np.full(len(values), "U", dtype="U1")
    result[values == 1] = "H"
    result[values == 2] = "2"
    result[values == 3] = "3"
    return result


def role_for_target(target_spec: dict[str, Any]) -> str:
    if target_spec["entity"] == "spm_unit":
        return "late_spm_unit"
    if target_spec["stage"] == "early_gap_fill":
        return "early_person"
    return "late_person"


def _load_surfaces(d0: dict[str, Any]) -> dict[str, Any]:
    """Load selected checkpoint columns into shared donor/recipient surfaces."""
    target_specs = d0["D0-2"]["targets"]
    predictor_specs = d0["D0-7"]["targets"]
    stage_root = Path(
        d0["D0-0"]["artifacts"]["candidate-25"]["checkpoint_directories"]
        ["stage_root"]["path"]
    )
    assembled_path = stage_root / "assembled.checkpoint.h5"
    transferred_path = stage_root / "transferred.checkpoint.h5"

    bank_cache: dict[Path, dict[str, Any]] = {}
    current_banks: dict[str, dict[str, Any]] = {}
    all_model_targets: set[str] = set()
    for target, spec in target_specs.items():
        bank = replay.load_bank(Path(spec["target_bank_file"]), bank_cache)
        current_banks[target] = bank
        all_model_targets.update(bank["metadata"]["target"]["model_targets"])

    assembled_cp = replay.SelectedCheckpoint(assembled_path)
    assembled_inputs = replay.load_person_inputs(assembled_cp, set())
    assembled_inputs["household.TYPEHUGQ"] = assembled_cp.column(
        "household",
        "TYPEHUGQ",
    )
    assembled_loaded = list(assembled_cp.loaded)
    assembled_cp.close()

    transferred_cp = replay.SelectedCheckpoint(transferred_path)
    transferred_inputs = replay.load_person_inputs(
        transferred_cp,
        all_model_targets,
    )
    transferred_inputs["household.TYPEHUGQ"] = transferred_cp.column(
        "household",
        "TYPEHUGQ",
    )
    transferred_inputs["spm_unit.spm_unit_energy_subsidy"] = (
        transferred_cp.column("spm_unit", "spm_unit_energy_subsidy")
    )
    transferred_loaded = list(transferred_cp.loaded)
    transferred_cp.close()

    assembled_person = replay.person_surface(
        assembled_inputs,
        role="recipient",
    )
    transferred_person_donor = replay.person_surface(
        transferred_inputs,
        role="donor",
    )
    transferred_person_recipient = replay.person_surface(
        transferred_inputs,
        role="recipient",
    )
    assembled_pw = replay.person_weights(assembled_inputs)
    transferred_pw = replay.person_weights(transferred_inputs)

    assembled_asec0 = (
        (assembled_inputs["person_support_channel"] == "asec")
        & (assembled_inputs["person_support_clone_index"] == 0)
    )
    assembled_acs = assembled_inputs["person_support_channel"] == "acs"
    transferred_asec0 = (
        (transferred_inputs["person_support_channel"] == "asec")
        & (transferred_inputs["person_support_clone_index"] == 0)
    )
    transferred_asec1 = (
        (transferred_inputs["person_support_channel"] == "asec")
        & (transferred_inputs["person_support_clone_index"] == 1)
    )
    transferred_acs = transferred_inputs["person_support_channel"] == "acs"

    assembled_household_gq = _gq_codes(
        assembled_inputs["household.TYPEHUGQ"]
    )
    transferred_household_gq = _gq_codes(
        transferred_inputs["household.TYPEHUGQ"]
    )
    assembled_person_gq = replay.broadcast_by_id(
        assembled_inputs["household.household_id"],
        assembled_household_gq,
        assembled_inputs["person_household_id"],
    )
    transferred_person_gq = replay.broadcast_by_id(
        transferred_inputs["household.household_id"],
        transferred_household_gq,
        transferred_inputs["person_household_id"],
    )

    if not np.array_equal(
        assembled_inputs["person_source_id"][assembled_asec0],
        transferred_inputs["person_source_id"][transferred_asec0],
    ):
        raise ValueError("early donor row order changed between checkpoints")

    early_donor_surface = replay.subset_surface(
        transferred_person_donor,
        transferred_asec0,
    )
    early_recipient_surface = replay.subset_surface(
        assembled_person,
        assembled_acs,
    )
    late_donor_surface = replay.subset_surface(
        transferred_person_donor,
        transferred_asec1,
    )
    late_recipient_surface = replay.subset_surface(
        transferred_person_recipient,
        transferred_acs,
    )
    early_donor_weights = assembled_pw[assembled_asec0]
    early_recipient_weights = assembled_pw[assembled_acs]
    late_donor_weights = transferred_pw[transferred_asec1]
    late_recipient_weights = transferred_pw[transferred_acs]
    early_recipient_physical = np.flatnonzero(assembled_acs)
    late_recipient_physical = np.flatnonzero(transferred_acs)

    early_donor_targets = {
        name: replay.as_float(transferred_inputs[name][transferred_asec0])
        for name in all_model_targets
        if name in transferred_inputs
    }
    late_donor_targets = {
        name: replay.as_float(transferred_inputs[name][transferred_asec1])
        for name in all_model_targets
        if name in transferred_inputs
    }

    spm_ids = transferred_inputs["spm_unit.spm_unit_id"]
    transferred_group_donor = replay.group_surface(
        transferred_person_donor,
        transferred_inputs["person_spm_unit_id"],
        spm_ids,
    )
    transferred_group_recipient = replay.group_surface(
        transferred_person_recipient,
        transferred_inputs["person_spm_unit_id"],
        spm_ids,
    )
    transferred_gw = replay.group_weights(
        transferred_pw,
        transferred_inputs["person_spm_unit_id"],
        spm_ids,
    )
    spm_channel = transferred_inputs["spm_unit.spm_unit_support_channel"]
    spm_clone = transferred_inputs["spm_unit.spm_unit_support_clone_index"]
    spm_asec1 = (spm_channel == "asec") & (spm_clone == 1)
    spm_acs = spm_channel == "acs"

    group_donor_surface = replay.subset_surface(
        transferred_group_donor,
        spm_asec1,
    )
    group_recipient_surface = replay.subset_surface(
        transferred_group_recipient,
        spm_acs,
    )
    group_donor_weights = transferred_gw[spm_asec1]
    group_recipient_weights = transferred_gw[spm_acs]
    group_recipient_physical = np.flatnonzero(spm_acs)

    spm_positions = np.searchsorted(
        spm_ids,
        transferred_inputs["person_spm_unit_id"],
    )
    spm_gq_low = np.full(len(spm_ids), 127, dtype=np.int16)
    spm_gq_high = np.full(len(spm_ids), -128, dtype=np.int16)
    np.minimum.at(spm_gq_low, spm_positions, transferred_person_gq)
    np.maximum.at(spm_gq_high, spm_positions, transferred_person_gq)
    if not np.array_equal(spm_gq_low, spm_gq_high):
        raise ValueError("SPM unit members differ in TYPEHUGQ")
    spm_gq = spm_gq_low.astype(np.int8)
    group_donor_targets = {
        "spm_unit_energy_subsidy": replay.as_float(
            transferred_inputs["spm_unit.spm_unit_energy_subsidy"][spm_asec1]
        )
    }

    early_optional = tuple(
        name
        for name in replay.OPT_PERSON
        if any(
            name in step["state_after"]["predictors"]
            for target in (
                "self_employment_income_last_year",
                "unemployment_compensation",
            )
            for step in current_banks[target]["metadata"]["pattern_steps"]
        )
    )
    pattern_sets = {
        "early_person": replay.make_patterns(
            early_recipient_surface,
            replay.REQ_PERSON,
            early_optional,
        ),
        "late_person": replay.make_patterns(
            late_recipient_surface,
            replay.REQ_PERSON,
            replay.OPT_PERSON,
        ),
        "late_spm_unit": replay.make_patterns(
            group_recipient_surface,
            replay.REQ_GROUP,
            replay.OPT_GROUP,
        ),
    }

    roles = {
        "early_person": {
            "donor_surface": early_donor_surface,
            "recipient_surface": early_recipient_surface,
            "donor_targets": early_donor_targets,
            "donor_weights": early_donor_weights,
            "recipient_weights": early_recipient_weights,
            "recipient_physical": early_recipient_physical,
            "recipient_clone0": (
                assembled_inputs["person_support_clone_index"][assembled_acs] == 0
            ),
            "recipient_gq": assembled_person_gq[assembled_acs],
            "recipient_stable_id": assembled_inputs["person_id"][assembled_acs],
            "patterns": pattern_sets["early_person"],
        },
        "late_person": {
            "donor_surface": late_donor_surface,
            "recipient_surface": late_recipient_surface,
            "donor_targets": late_donor_targets,
            "donor_weights": late_donor_weights,
            "recipient_weights": late_recipient_weights,
            "recipient_physical": late_recipient_physical,
            "recipient_clone0": (
                transferred_inputs["person_support_clone_index"][transferred_acs]
                == 0
            ),
            "recipient_gq": transferred_person_gq[transferred_acs],
            "recipient_stable_id": transferred_inputs["person_id"][transferred_acs],
            "patterns": pattern_sets["late_person"],
        },
        "late_spm_unit": {
            "donor_surface": group_donor_surface,
            "recipient_surface": group_recipient_surface,
            "donor_targets": group_donor_targets,
            "donor_weights": group_donor_weights,
            "recipient_weights": group_recipient_weights,
            "recipient_physical": group_recipient_physical,
            "recipient_clone0": spm_clone[spm_acs] == 0,
            "recipient_gq": spm_gq[spm_acs],
            "recipient_stable_id": spm_ids[spm_acs],
            "patterns": pattern_sets["late_spm_unit"],
        },
    }
    return {
        "d0": d0,
        "target_specs": target_specs,
        "predictor_specs": predictor_specs,
        "bank_cache": bank_cache,
        "current_banks": current_banks,
        "roles": roles,
        "stage_root": stage_root,
        "assembled_path": assembled_path,
        "transferred_path": transferred_path,
        "assembled_loaded": assembled_loaded,
        "transferred_loaded": transferred_loaded,
    }


def load_analysis_data(d0: dict[str, Any]) -> dict[str, Any]:
    """Public loader reused by C4 and later P2 executors."""
    data = _load_surfaces(d0)
    for target, spec in data["target_specs"].items():
        role_name = role_for_target(spec)
        actual = [item["name"] for item in data["roles"][role_name]["patterns"]]
        expected = [item["name"] for item in spec["patterns"]]
        if actual != expected:
            raise ValueError(
                f"availability-pattern mismatch for {target}: {actual} != {expected}"
            )
    return data


def fit_gate_context(
    data: dict[str, Any],
    target: str,
    pattern_name: str,
    c0b_lookup: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Restore one exact production gate and bind it to adopted C0b."""
    target_spec = data["target_specs"][target]
    predictor_target = data["predictor_specs"][target]
    bank = data["current_banks"][target]
    role_name = role_for_target(target_spec)
    role = data["roles"][role_name]
    d0_pattern = next(
        item for item in target_spec["patterns"] if item["name"] == pattern_name
    )
    predictor_pattern = next(
        item
        for item in predictor_target["patterns"]
        if item["name"] == pattern_name
    )
    recorded_step = next(
        item
        for item in bank["metadata"]["pattern_steps"]
        if item["pattern"] == pattern_name
    )
    state, state_sha, state_source = replay.state_before_for_pattern(
        bank,
        pattern_name,
        data["bank_cache"],
    )
    if state_sha != recorded_step["state_before_sha256"]:
        raise ValueError(f"state-before SHA mismatch for {target}/{pattern_name}")

    predictors = tuple(state["predictors"])
    completed = tuple(state["completed_targets"])
    columns = (*predictors, *completed)
    expected_columns = tuple(predictor_pattern["effective_gate_columns"])
    if columns != expected_columns:
        raise ValueError(
            f"D0 effective columns mismatch for {target}/{pattern_name}: "
            f"{columns} != {expected_columns}"
        )

    donor_surface = role["donor_surface"]
    donor_targets = role["donor_targets"]
    donor_x = np.column_stack(
        [
            donor_surface[name] if name in donor_surface else donor_targets[name]
            for name in columns
        ]
    ).astype(np.float64, copy=False)
    current_target = bank["metadata"]["target"]["model_target"]
    donor_y = donor_targets[current_target]
    donor_weights = np.asarray(role["donor_weights"], dtype=np.float64)
    if (
        not np.isfinite(donor_x).all()
        or not np.isfinite(donor_y).all()
        or not np.isfinite(donor_weights).all()
        or (donor_weights <= 0).any()
    ):
        raise ValueError(f"invalid donor fit input for {target}/{pattern_name}")
    if len(donor_x) != d0_pattern["donor_fit_rows"]:
        raise ValueError(f"D0 donor row mismatch for {target}/{pattern_name}")

    labels = replay.sign_labels(donor_y)
    fit_rng = np.random.default_rng()
    fit_rng.bit_generator.state = copy.deepcopy(state["fit_rng_state"])
    gate_seed = int(fit_rng.integers(0, 2**31 - 1))
    gate = HistGradientBoostingClassifier(random_state=gate_seed)
    gate.fit(donor_x, labels, sample_weight=donor_weights)
    gate_classes = np.asarray(gate.classes_, dtype=np.int8)
    if not np.array_equal(gate_classes, np.unique(labels)):
        raise ValueError(f"gate class mismatch for {target}/{pattern_name}")
    donor_probabilities = np.asarray(
        gate.predict_proba(donor_x),
        dtype=np.float64,
    )

    groups = {
        name: tuple(predictor_pattern[name]) for name in GROUP_ORDER
    }
    flattened = [name for group in groups.values() for name in group]
    if len(flattened) != len(set(flattened)) or set(flattened) != set(columns):
        raise ValueError(
            f"D0 feature groups do not partition {target}/{pattern_name}"
        )
    group_indexes = {
        group: np.asarray(
            [columns.index(name) for name in names],
            dtype=np.int64,
        )
        for group, names in groups.items()
    }

    adopted = c0b_lookup[(target, pattern_name)]
    bindings = {
        "gate_seed": gate_seed == adopted["gate_seed"],
        "state_before_sha256": (
            state_sha == adopted["state_before_sha256_actual"]
        ),
        "weights": (
            replay.weight_identity(donor_weights)
            == adopted["weight_sha256_actual"]
        ),
        "classes": (
            [int(value) for value in gate_classes] == adopted["gate_classes"]
        ),
        "donor_probabilities": (
            array_identity(donor_probabilities)["sha256"]
            == adopted["fit_gate_probability_matrix_sha256"]
        ),
    }
    if not all(bindings.values()):
        raise ValueError(
            f"adopted C0b gate binding mismatch for {target}/{pattern_name}: "
            f"{bindings}"
        )

    probabilities = donor_weights / donor_weights.sum(dtype=np.float64)
    probabilities[-1] += 1.0 - probabilities.sum(dtype=np.float64)
    return {
        "target": target,
        "pattern": pattern_name,
        "target_spec": target_spec,
        "d0_pattern": d0_pattern,
        "predictor_pattern": predictor_pattern,
        "role_name": role_name,
        "role": role,
        "bank": bank,
        "state": state,
        "state_before_sha256": state_sha,
        "state_before_source": state_source,
        "columns": columns,
        "groups": groups,
        "group_indexes": group_indexes,
        "donor_x": donor_x,
        "donor_y": donor_y,
        "donor_labels": labels,
        "donor_weights": donor_weights,
        "donor_probabilities": donor_probabilities,
        "donor_choice_probabilities": probabilities,
        "gate": gate,
        "gate_seed": gate_seed,
        "gate_classes": gate_classes,
        "c0b_bindings": bindings,
    }


def _largest_remainder_with_minimum_one(
    weights: np.ndarray,
    total: int,
) -> np.ndarray:
    """A16 finding 3 allocation in the already-registered stratum order."""
    weights = np.asarray(weights, dtype=np.float64)
    positive = weights > 0.0
    positive_count = int(positive.sum())
    if total < positive_count:
        raise ValueError(
            f"target sample {total} is below {positive_count} positive strata"
        )
    result = np.zeros(len(weights), dtype=np.int64)
    result[positive] = 1
    remaining = total - positive_count
    if remaining == 0:
        return result
    quotas = np.zeros(len(weights), dtype=np.float64)
    quotas[positive] = remaining * weights[positive] / weights[positive].sum()
    floors = np.floor(quotas).astype(np.int64)
    result += floors
    unassigned = total - int(result.sum())
    ranked = sorted(
        np.flatnonzero(positive).tolist(),
        key=lambda position: (-(quotas[position] - floors[position]), position),
    )
    for position in ranked[:unassigned]:
        result[position] += 1
    if int(result.sum()) != total or (result[positive] < 1).any():
        raise AssertionError("largest-remainder allocation did not close")
    return result


def target_allocation(data: dict[str, Any], target: str) -> dict[str, Any]:
    """Recover S_q and freeze the target-level pattern-by-GQ allocation."""
    target_spec = data["target_specs"][target]
    role = data["roles"][role_for_target(target_spec)]
    bank = data["current_banks"][target]
    gq_keys = _gq_key(role["recipient_gq"])
    strata: list[dict[str, Any]] = []

    for d0_pattern, pattern in zip(
        target_spec["patterns"],
        role["patterns"],
        strict=True,
    ):
        if d0_pattern["name"] != pattern["name"]:
            raise ValueError(f"pattern order mismatch while allocating {target}")
        positions = pattern["positions"]
        physical = role["recipient_physical"][positions]
        sq = role["recipient_clone0"][positions] & np.isfinite(bank["raw"][physical])
        sq_count = int(sq.sum())
        sq_weights = role["recipient_weights"][positions][sq]
        if sq_count != d0_pattern["clone0_recipient_rows"]:
            raise ValueError(
                f"S_q count mismatch for {target}/{pattern['name']}: "
                f"{sq_count} != {d0_pattern['clone0_recipient_rows']}"
            )
        if not np.isclose(
            sq_weights.sum(dtype=np.float64),
            d0_pattern["clone0_recipient_weight_sum"],
            rtol=0.0,
            atol=1e-8,
        ):
            raise ValueError(
                f"S_q weight mismatch for {target}/{pattern['name']}"
            )
        pattern_gq = gq_keys[positions][sq]
        pattern_weights = sq_weights
        pattern_stable_ids = role["recipient_stable_id"][positions][sq]
        stable_order = np.argsort(pattern_stable_ids, kind="stable")
        pattern_gq = pattern_gq[stable_order]
        pattern_weights = pattern_weights[stable_order]
        pattern_stable_ids = pattern_stable_ids[stable_order]
        for gq in GQ_ORDER:
            mask = pattern_gq == gq
            selected_weights = pattern_weights[mask]
            selected_ids = pattern_stable_ids[mask]
            strata.append(
                {
                    "pattern": pattern["name"],
                    "gq": gq,
                    "row_count": int(mask.sum()),
                    "weight_sum": float(selected_weights.sum(dtype=np.float64)),
                    "stable_entity_id_identity": array_identity(selected_ids),
                }
            )

    total_rows = sum(item["row_count"] for item in strata)
    total_weight = math.fsum(item["weight_sum"] for item in strata)
    if total_rows != target_spec["clone0_recipient_rows"]:
        raise ValueError(
            f"target S_q row mismatch for {target}: "
            f"{total_rows} != {target_spec['clone0_recipient_rows']}"
        )
    if not np.isclose(
        total_weight,
        target_spec["clone0_recipient_weight_sum"],
        rtol=0.0,
        atol=1e-7,
    ):
        raise ValueError(f"target S_q weight mismatch for {target}")
    sample_size = min(MAX_TARGET_SAMPLE, total_rows)
    allocations = _largest_remainder_with_minimum_one(
        np.asarray([item["weight_sum"] for item in strata], dtype=np.float64),
        sample_size,
    )
    for item, allocation in zip(strata, allocations, strict=True):
        item["allocation"] = int(allocation)
        item["exact_weight_share"] = (
            item["weight_sum"] / total_weight if total_weight else 0.0
        )
        item["p2_rows_seed_template"] = (
            "qrf-drift-v2|P2|rows|"
            f"{target}|<r>|{item['pattern']}|{item['gq']}"
        )

    pattern_sample_sizes = {
        pattern["name"]: sum(
            item["allocation"]
            for item in strata
            if item["pattern"] == pattern["name"]
        )
        for pattern in role["patterns"]
    }
    if sum(pattern_sample_sizes.values()) != sample_size:
        raise AssertionError("pattern allocations do not sum to target sample")
    return {
        "target": target,
        "S_q_rows": total_rows,
        "S_q_weight_sum": total_weight,
        "target_sample_size": sample_size,
        "positive_strata": sum(item["weight_sum"] > 0.0 for item in strata),
        "stratum_order": "D0 pattern order, then H,2,3,U",
        "strata": strata,
        "pattern_sample_sizes": pattern_sample_sizes,
    }


def _empty_replicate_arrays(
    context: dict[str, Any],
    count: int,
    *,
    include_baselines: bool,
) -> dict[str, Any]:
    classes = len(context["gate_classes"])
    values: dict[str, Any] = {
        "v_null_empty": np.empty((count, classes), dtype=np.float64),
        "v_null_all": np.empty((count, classes), dtype=np.float64),
        "null_total": np.empty((count, classes), dtype=np.float64),
    }
    if include_baselines:
        values["coalitions"] = np.empty((count, classes, 8), dtype=np.float64)
        values["shapley"] = np.empty((count, classes, 3), dtype=np.float64)
        values["priors"] = {
            name: np.empty((count, classes), dtype=np.float64)
            for name in context["groups"]["G3"]
        }
    return values


def _coalition_baselines(
    context: dict[str, Any],
    base_x: np.ndarray,
    substitution_x: np.ndarray,
    base_mean: np.ndarray,
    all_mean: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Evaluate descriptive C4 null coalitions on fixed paired samples."""
    groups = context["groups"]
    active_mask = 7 if groups["G3"] else 3
    active_masks = list(range(active_mask + 1))
    coalition = np.empty((8, len(context["gate_classes"])), dtype=np.float64)
    coalition[0] = base_mean
    coalition[active_mask] = all_mean
    partial_masks = [mask for mask in active_masks if mask not in {0, active_mask}]

    prior_names = list(groups["G3"])
    extra_priors = prior_names if len(prior_names) > 1 else []
    block_specs: list[tuple[str, int | str]] = [
        ("coalition", mask) for mask in partial_masks
    ] + [("prior", name) for name in extra_priors]
    block_means: dict[tuple[str, int | str], np.ndarray] = {}
    if block_specs:
        sample_size = len(base_x)
        evaluation_x = np.tile(base_x, (len(block_specs), 1))
        for block_position, (kind, value) in enumerate(block_specs):
            block = evaluation_x[
                block_position * sample_size : (block_position + 1) * sample_size
            ]
            if kind == "coalition":
                mask = int(value)
                for group, bit in GROUP_BITS.items():
                    if mask & bit:
                        indexes = context["group_indexes"][group]
                        if len(indexes):
                            block[:, indexes] = substitution_x[:, indexes]
            else:
                column = context["columns"].index(str(value))
                block[:, column] = substitution_x[:, column]
        probabilities = np.asarray(
            context["gate"].predict_proba(evaluation_x),
            dtype=np.float64,
        ).reshape(len(block_specs), sample_size, -1)
        for block_position, spec in enumerate(block_specs):
            block_means[spec] = probabilities[block_position].mean(axis=0)
    for mask in partial_masks:
        coalition[mask] = block_means[("coalition", mask)]
    if active_mask == 3:
        for mask in range(8):
            coalition[mask] = coalition[mask & 3]

    shapley = np.zeros((len(context["gate_classes"]), 3), dtype=np.float64)
    for group_position, group in enumerate(GROUP_ORDER):
        bit = GROUP_BITS[group]
        if not groups[group]:
            continue
        other_bits = [other for other in (1, 2, 4) if other != bit]
        for subset in range(8):
            if subset & bit or subset & ~sum(other_bits):
                continue
            subset_size = int(bool(subset & other_bits[0])) + int(
                bool(subset & other_bits[1])
            )
            weight = 1.0 / 3.0 if subset_size in {0, 2} else 1.0 / 6.0
            shapley[:, group_position] += weight * (
                coalition[subset | bit] - coalition[subset]
            )

    priors: dict[str, np.ndarray] = {}
    if len(prior_names) == 1:
        priors[prior_names[0]] = coalition[4] - coalition[0]
    elif prior_names:
        for name in prior_names:
            priors[name] = block_means[("prior", name)] - coalition[0]
    return coalition, shapley, priors


def run_replicate_range(
    context: dict[str, Any],
    sample_size: int,
    start: int,
    stop: int,
    *,
    include_baselines: bool,
) -> dict[str, Any]:
    """Run a contiguous registered replicate range for one pattern."""
    values = _empty_replicate_arrays(
        context,
        stop - start,
        include_baselines=include_baselines,
    )
    probabilities = context["donor_choice_probabilities"]
    donor_x = context["donor_x"]
    donor_p = context["donor_probabilities"]
    target = context["target"]
    pattern = context["pattern"]
    first_indexes: dict[str, Any] | None = None
    last_indexes: dict[str, Any] | None = None

    for offset, replicate in enumerate(range(start, stop)):
        base_index = weighted_choice(
            r0_label(target, pattern, replicate),
            probabilities,
            sample_size,
        )
        substitution_index = weighted_choice(
            donor_label(target, pattern, replicate),
            probabilities,
            sample_size,
        )
        base_mean = donor_p[base_index].mean(axis=0)
        all_mean = donor_p[substitution_index].mean(axis=0)
        values["v_null_empty"][offset] = base_mean
        values["v_null_all"][offset] = all_mean
        values["null_total"][offset] = all_mean - base_mean
        if include_baselines:
            coalition, shapley, priors = _coalition_baselines(
                context,
                donor_x[base_index],
                donor_x[substitution_index],
                base_mean,
                all_mean,
            )
            values["coalitions"][offset] = coalition.T
            values["shapley"][offset] = shapley
            for name, contribution in priors.items():
                values["priors"][name][offset] = contribution
        if offset == 0:
            first_indexes = {
                "replicate": replicate,
                "R0": array_identity(base_index),
                "donor": array_identity(substitution_index),
            }
        if offset == stop - start - 1:
            last_indexes = {
                "replicate": replicate,
                "R0": array_identity(base_index),
                "donor": array_identity(substitution_index),
            }
    values["index_identities"] = {
        "first": first_indexes,
        "last": last_indexes,
    }
    return values


def concatenate_replicates(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in ("v_null_empty", "v_null_all", "null_total"):
        result[name] = np.concatenate((first[name], second[name]), axis=0)
    if "coalitions" in first:
        for name in ("coalitions", "shapley"):
            result[name] = np.concatenate((first[name], second[name]), axis=0)
        result["priors"] = {
            name: np.concatenate((first["priors"][name], second["priors"][name]))
            for name in first["priors"]
        }
    result["index_identities"] = {
        "first": first["index_identities"]["first"],
        "last": second["index_identities"]["last"],
    }
    return result


def summarize(values: np.ndarray) -> dict[str, Any]:
    vector = np.asarray(values, dtype=np.float64)
    count = len(vector)
    estimate = float(vector.mean())
    sd = float(vector.std(ddof=1)) if count > 1 else 0.0
    mcse = sd / math.sqrt(count) if count else 0.0
    if mcse > 0.0:
        ratio: float | str = abs(estimate) / mcse
        passed = abs(estimate) <= Z_STAR * mcse
        trigger = 2.0 <= ratio <= 4.0
    elif estimate == 0.0:
        ratio = 0.0
        passed = True
        trigger = False
    else:
        ratio = "inf"
        passed = False
        trigger = False
    return {
        "value": estimate,
        "replicate_sd": sd,
        "mcse": mcse,
        "abs_value_over_mcse": ratio,
        "sidak_z": Z_STAR,
        "absolute_threshold": Z_STAR * mcse,
        "pass": bool(passed),
        "escalation_trigger_at_this_R": bool(trigger),
        "replicates": count,
    }


def c4_statistic_id(
    target: str,
    pattern: str,
    leg: str,
) -> str:
    return (
        f"r=control|t={target}|p={pattern}|l={leg}|row=C4_null_total|"
        "g=_|prior=_|gq=_|d=_|rep=_|fold=_|v=paired"
    )


def gated_statistics(
    context: dict[str, Any],
    values: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for class_position, class_code in enumerate(context["gate_classes"]):
        if int(class_code) not in {-1, 1}:
            continue
        leg = replay.label_name(int(class_code))
        vector = values["null_total"][:, class_position]
        rows.append(
            {
                "id": c4_statistic_id(
                    context["target"],
                    context["pattern"],
                    leg,
                ),
                "target": context["target"],
                "pattern": context["pattern"],
                "leg": leg,
                "row": "C4_null_total",
                "family": "C4_null_total",
                "gated": True,
                "status": "PASS" if summarize(vector)["pass"] else "FAIL",
                **summarize(vector),
                "replicate_values": [float(value) for value in vector],
                "replicate_values_identity": array_identity(vector),
            }
        )
    return rows


def _matrix_payload(values: np.ndarray) -> dict[str, Any]:
    return {
        "values": np.asarray(values, dtype=np.float64).tolist(),
        "identity": array_identity(values),
    }


def cell_payload(
    context: dict[str, Any],
    values: dict[str, Any],
    sample_size: int,
    *,
    include_baselines: bool,
) -> dict[str, Any]:
    class_order = [
        replay.label_name(int(value)) for value in context["gate_classes"]
    ]
    replicate_count = len(values["null_total"])
    payload: dict[str, Any] = {
        "target": context["target"],
        "pattern": context["pattern"],
        "entity": context["target_spec"]["entity"],
        "stage": context["target_spec"]["stage"],
        "sample_size": sample_size,
        "replicates": replicate_count,
        "class_order": class_order,
        "gate_classes": [int(value) for value in context["gate_classes"]],
        "gate_seed": context["gate_seed"],
        "state_before_sha256": context["state_before_sha256"],
        "state_before_source": context["state_before_source"],
        "donor_fit_rows": len(context["donor_x"]),
        "donor_x_identity": array_identity(context["donor_x"]),
        "donor_y_identity": array_identity(context["donor_y"]),
        "donor_weight_identity": replay.weight_identity(
            context["donor_weights"]
        ),
        "donor_probability_identity": array_identity(
            context["donor_probabilities"]
        ),
        "columns": list(context["columns"]),
        "groups": {
            name: list(columns) for name, columns in context["groups"].items()
        },
        "c0b_bindings": context["c0b_bindings"],
        "seed_streams": {
            "R0_first": r0_label(
                context["target"], context["pattern"], 0
            ),
            "R0_last": r0_label(
                context["target"], context["pattern"], replicate_count - 1
            ),
            "donor_first": donor_label(
                context["target"], context["pattern"], 0
            ),
            "donor_last": donor_label(
                context["target"], context["pattern"], replicate_count - 1
            ),
            "derivation": "first 8 SHA-256 bytes, big-endian uint64, numpy PCG64",
            "fresh_generator_per_complete_label": True,
            "sampling": "Generator.choice(replace=True, p=fit_weight/sum)",
            "index_identities": values["index_identities"],
        },
        "replicate_arrays": {
            "v_null_empty": _matrix_payload(values["v_null_empty"]),
            "v_null_all": _matrix_payload(values["v_null_all"]),
            "null_total": _matrix_payload(values["null_total"]),
        },
        "p2_baselines_included": include_baselines,
    }
    if include_baselines:
        payload["replicate_arrays"].update(
            {
                "coalitions_mask_order_0_to_7": _matrix_payload(
                    values["coalitions"]
                ),
                "shapley_group_order_G1_G2_G3": _matrix_payload(
                    values["shapley"]
                ),
                "per_prior_marginals": {
                    name: _matrix_payload(matrix)
                    for name, matrix in values["priors"].items()
                },
            }
        )
    return payload


def _number(value: float) -> str:
    """RFC 8785/ECMAScript-compatible finite binary64 spelling."""
    if not math.isfinite(value):
        raise ValueError("nonfinite numbers must be encoded as strings")
    if value == 0.0:
        return "0"
    raw = repr(float(value)).lower()
    absolute = abs(value)
    if 1e-6 <= absolute < 1e21:
        if "e" in raw:
            coefficient, exponent_text = raw.split("e")
            exponent = int(exponent_text)
            sign = ""
            if coefficient.startswith("-"):
                sign = "-"
                coefficient = coefficient[1:]
            digits = coefficient.replace(".", "")
            decimal_position = (
                coefficient.index(".") if "." in coefficient else len(coefficient)
            ) + exponent
            if decimal_position <= 0:
                raw = sign + "0." + "0" * (-decimal_position) + digits
            elif decimal_position >= len(digits):
                raw = sign + digits + "0" * (decimal_position - len(digits))
            else:
                raw = (
                    sign
                    + digits[:decimal_position]
                    + "."
                    + digits[decimal_position:]
                )
        if raw.endswith(".0"):
            raw = raw[:-2]
        return raw
    if "e" not in raw:
        return raw[:-2] if raw.endswith(".0") else raw
    coefficient, exponent_text = raw.split("e")
    exponent = int(exponent_text)
    if coefficient.endswith(".0"):
        coefficient = coefficient[:-2]
    return f"{coefficient}e{'+' if exponent >= 0 else ''}{exponent}"


def canonical_bytes(value: Any) -> bytes:
    def encode(item: Any) -> str:
        if item is None:
            return "null"
        if item is True:
            return "true"
        if item is False:
            return "false"
        if isinstance(item, str):
            return json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        if isinstance(item, int) and not isinstance(item, bool):
            return str(item)
        if isinstance(item, float):
            return _number(item)
        if isinstance(item, list):
            return "[" + ",".join(encode(value) for value in item) + "]"
        if isinstance(item, dict):
            keys = sorted(item)
            return "{" + ",".join(
                encode(key) + ":" + encode(item[key]) for key in keys
            ) + "}"
        raise TypeError(f"unsupported canonical JSON type: {type(item)!r}")

    return encode(value).encode("utf-8")


def write_canonical_result(path: Path, result: dict[str, Any]) -> str:
    result["statistics"] = sorted(
        result.get("statistics", []),
        key=lambda item: item["id"],
    )
    scope = dict(result)
    scope.pop("canonical_sha256", None)
    result["canonical_sha256"] = hashlib.sha256(canonical_bytes(scope)).hexdigest()
    path.write_bytes(canonical_bytes(result) + b"\n")
    return sha256_file(path)


def verify_inputs(
    d0: dict[str, Any],
    c0b_path: Path,
) -> dict[str, Any]:
    expected = dict(EXPECTED_AUTHORITY_DIGESTS)
    stage_root = Path(
        d0["D0-0"]["artifacts"]["candidate-25"]["checkpoint_directories"]
        ["stage_root"]["path"]
    )
    for filename, digest in EXPECTED_CHECKPOINT_DIGESTS.items():
        expected[str(stage_root / filename)] = digest
    for item in d0["D0-0"]["artifacts"]["candidate-25"][
        "bank_target_checkpoints"
    ]:
        expected[item["path"]] = item["sha256"]
    found_predecessors: dict[str, Path] = {}
    for path in stage_root.rglob("*.h5"):
        if path.name in EXPECTED_PREDECESSOR_DIGESTS:
            found_predecessors[path.name] = path
    missing = set(EXPECTED_PREDECESSOR_DIGESTS) - set(found_predecessors)
    if missing:
        raise ValueError(f"missing predecessor bank(s): {sorted(missing)}")
    for filename, path in found_predecessors.items():
        expected[str(path)] = EXPECTED_PREDECESSOR_DIGESTS[filename]
    expected[str(c0b_path)] = EXPECTED_C0B_SHA256

    rows: list[dict[str, Any]] = []
    for raw_path, expected_sha in expected.items():
        path = Path(raw_path)
        actual_sha = sha256_file(path)
        rows.append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256_expected": expected_sha,
                "sha256_actual": actual_sha,
                "match": actual_sha == expected_sha,
            }
        )
    failed = [item["path"] for item in rows if not item["match"]]
    if failed:
        raise ValueError(f"pinned input digest mismatch: {failed}")
    return {
        "all_match": True,
        "file_count": len(rows),
        "files": rows,
    }


def expected_c4_ids(
    data: dict[str, Any],
    targets: list[str],
) -> list[str]:
    result: list[str] = []
    for target in targets:
        for pattern in data["target_specs"][target]["patterns"]:
            for leg in ("negative", "positive"):
                if leg in pattern["classes"]:
                    result.append(c4_statistic_id(target, pattern["name"], leg))
    return sorted(result)


def _base_result(
    *,
    mode: str,
    targets: list[str],
    input_verification: dict[str, Any],
    data: dict[str, Any],
    c0b_path: Path,
    started_unix: float,
) -> dict[str, Any]:
    return {
        "artifact_kind": "qrf_drift_phase0_a17_c4",
        "schema_version": 1,
        "status": "RUNNING",
        "mode": mode,
        "scope": {
            "rung": "candidate-25 pre-calibration",
            "targets": targets,
            "target_count": len(targets),
            "full_target_count": len(data["target_specs"]),
        },
        "authority": {
            "design": {
                "path": str(DESIGN_MD),
                "sha256": EXPECTED_AUTHORITY_DIGESTS[str(DESIGN_MD)],
                "commit": "1c315579",
            },
            "a16_binding": {
                "path": str(A16_BINDING),
                "sha256": EXPECTED_AUTHORITY_DIGESTS[str(A16_BINDING)],
            },
            "d0": {
                "path": str(D0_JSON),
                "sha256": EXPECTED_AUTHORITY_DIGESTS[str(D0_JSON)],
            },
            "adopted_c0b": {
                "path": str(c0b_path),
                "sha256": EXPECTED_C0B_SHA256,
            },
        },
        "control_roster": {
            "overall_K": OVERALL_CONTROL_K,
            "C4_stochastic_K": C4_STOCHASTIC_K,
            "sidak_z": Z_STAR,
            "overall_ordered_ids_sha256": OVERALL_ROSTER_SHA256,
            "gated_C4_definition": (
                "one null total per target, pattern, and present nonzero class"
            ),
            "support_floor_applied": False,
        },
        "estimator": {
            "target_N": "min(100000, |S_q,target|)",
            "allocation": (
                "pattern x GQ in D0/H,2,3,U order; one per positive-mass "
                "stratum, remaining N-m by largest remainder"
            ),
            "C4_pattern_N": "sum of the target allocation over GQ",
            "R0": "fit-weight PPS with replacement from the pattern fit rows",
            "donor": (
                "independent fit-weight PPS with replacement from the same rows"
            ),
            "analysis_weights": "unit weights; no carried or inverse weights",
            "gated_statistic": "v_null(all)-v_null(empty)",
            "mcse": "SD(ddof=1)/sqrt(R)",
            "pass": f"abs(value) <= {Z_STAR} * MCSE",
            "initial_replicates": INITIAL_REPLICATES,
            "escalated_replicates": ESCALATED_REPLICATES,
            "escalation": (
                "per target, iff any gated C4 ratio at R=250 is in [2,4]"
            ),
            "descriptive_null_baselines": (
                "generated separately in p2-baselines mode; never C4-gated"
            ),
        },
        "input_verification": input_verification,
        "sources": {
            "streamed_columns": {
                "assembled": data["assembled_loaded"],
                "transferred": data["transferred_loaded"],
            }
        },
        "allocations": [],
        "targets": [],
        "cells": [],
        "statistics": [],
        "deterministic_empty_G3_checks": [],
        "summary": {},
        "execution_diagnostics": {
            "python": sys.version,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "platform": platform.platform(),
            "pid": os.getpid(),
            "process_nice_value": os.getpriority(os.PRIO_PROCESS, 0),
            "started_unix": started_unix,
        },
    }


def _write_partial(path: Path, result: dict[str, Any]) -> None:
    result["execution_diagnostics"]["peak_rss_mb_so_far"] = peak_rss_mb()
    write_canonical_result(path, result)


def run_control_mode(
    result: dict[str, Any],
    data: dict[str, Any],
    c0b_lookup: dict[tuple[str, str], dict[str, Any]],
    targets: list[str],
    fixed_replicates: int | None,
    partial_path: Path,
) -> None:
    expected_ids = expected_c4_ids(data, targets)
    for target in targets:
        target_started = time.perf_counter()
        allocation = target_allocation(data, target)
        result["allocations"].append(allocation)
        pattern_names = [
            item["name"] for item in data["target_specs"][target]["patterns"]
        ]
        contexts = {
            pattern: fit_gate_context(data, target, pattern, c0b_lookup)
            for pattern in pattern_names
        }
        initial_stop = fixed_replicates or INITIAL_REPLICATES
        pattern_values = {
            pattern: run_replicate_range(
                contexts[pattern],
                allocation["pattern_sample_sizes"][pattern],
                0,
                initial_stop,
                include_baselines=False,
            )
            for pattern in pattern_names
        }
        initial_statistics = [
            statistic
            for pattern in pattern_names
            for statistic in gated_statistics(
                contexts[pattern],
                pattern_values[pattern],
            )
        ]
        triggers = [
            {
                "id": item["id"],
                "abs_value_over_mcse": item["abs_value_over_mcse"],
            }
            for item in initial_statistics
            if item["escalation_trigger_at_this_R"]
        ]
        escalated = fixed_replicates is None and bool(triggers)
        if escalated:
            for pattern in pattern_names:
                extension = run_replicate_range(
                    contexts[pattern],
                    allocation["pattern_sample_sizes"][pattern],
                    INITIAL_REPLICATES,
                    ESCALATED_REPLICATES,
                    include_baselines=False,
                )
                pattern_values[pattern] = concatenate_replicates(
                    pattern_values[pattern],
                    extension,
                )

        target_statistics: list[dict[str, Any]] = []
        for pattern in pattern_names:
            context = contexts[pattern]
            values = pattern_values[pattern]
            cell = cell_payload(
                context,
                values,
                allocation["pattern_sample_sizes"][pattern],
                include_baselines=False,
            )
            result["cells"].append(cell)
            target_statistics.extend(gated_statistics(context, values))
            if not context["groups"]["G3"]:
                result["deterministic_empty_G3_checks"].append(
                    {
                        "target": target,
                        "pattern": pattern,
                        "value": 0.0,
                        "pass": True,
                        "basis": (
                            "G3 has zero columns; duplicated coalitions make the "
                            "G3 Shapley contribution exact zero"
                        ),
                    }
                )
        result["statistics"].extend(target_statistics)
        target_pass = all(item["pass"] for item in target_statistics)
        result["targets"].append(
            {
                "target": target,
                "replicates_initial": initial_stop,
                "replicates_final": len(
                    pattern_values[pattern_names[0]]["null_total"]
                ),
                "fixed_replicate_override": fixed_replicates is not None,
                "escalated": escalated,
                "escalation_triggers_at_250": triggers,
                "gated_cells": len(target_statistics),
                "pass": target_pass,
                "elapsed_seconds": time.perf_counter() - target_started,
            }
        )
        print(
            f"C4 {target}: cells={len(target_statistics)} "
            f"R={len(pattern_values[pattern_names[0]]['null_total'])} "
            f"escalated={escalated} pass={target_pass} "
            f"seconds={result['targets'][-1]['elapsed_seconds']:.1f}",
            flush=True,
        )
        _write_partial(partial_path, result)

    actual_ids = sorted(item["id"] for item in result["statistics"])
    if actual_ids != expected_ids:
        raise ValueError(
            "C4 gated ID mismatch: "
            f"missing={sorted(set(expected_ids) - set(actual_ids))}, "
            f"extra={sorted(set(actual_ids) - set(expected_ids))}"
        )
    if len(targets) == len(data["target_specs"]) and len(actual_ids) != 40:
        raise ValueError(f"full C4 roster has {len(actual_ids)} cells, not 40")


def run_p2_baseline_mode(
    result: dict[str, Any],
    data: dict[str, Any],
    c0b_lookup: dict[tuple[str, str], dict[str, Any]],
    targets: list[str],
    control: dict[str, Any],
    requested_replicates: int | None,
    partial_path: Path,
) -> None:
    control_targets = {item["target"]: item for item in control["targets"]}
    control_cells = {
        (item["target"], item["pattern"]): item for item in control["cells"]
    }
    for target in targets:
        if target not in control_targets or not control_targets[target]["pass"]:
            raise ValueError(f"C4 control is not a recorded pass for {target}")
        target_started = time.perf_counter()
        allocation = target_allocation(data, target)
        result["allocations"].append(allocation)
        control_replicates = int(control_targets[target]["replicates_final"])
        replicate_count = requested_replicates or control_replicates
        if replicate_count < control_replicates:
            raise ValueError(
                f"P2 baseline R={replicate_count} is below C4 R={control_replicates}"
            )
        pattern_names = [
            item["name"] for item in data["target_specs"][target]["patterns"]
        ]
        for pattern in pattern_names:
            context = fit_gate_context(data, target, pattern, c0b_lookup)
            values = run_replicate_range(
                context,
                allocation["pattern_sample_sizes"][pattern],
                0,
                replicate_count,
                include_baselines=True,
            )
            recorded = control_cells[(target, pattern)]["replicate_arrays"]
            prefix = control_replicates
            for name in ("v_null_empty", "v_null_all", "null_total"):
                expected = np.asarray(recorded[name]["values"], dtype=np.float64)
                if not np.array_equal(values[name][:prefix], expected):
                    raise ValueError(
                        f"P2 baseline endpoint changed for {target}/{pattern}/{name}"
                    )
            result["cells"].append(
                cell_payload(
                    context,
                    values,
                    allocation["pattern_sample_sizes"][pattern],
                    include_baselines=True,
                )
            )
        result["targets"].append(
            {
                "target": target,
                "C4_control_replicates": control_replicates,
                "P2_null_baseline_replicates": replicate_count,
                "extension_beyond_C4_is_descriptive_only": (
                    replicate_count > control_replicates
                ),
                "elapsed_seconds": time.perf_counter() - target_started,
            }
        )
        print(
            f"P2 null baselines {target}: R={replicate_count} "
            f"seconds={result['targets'][-1]['elapsed_seconds']:.1f}",
            flush=True,
        )
        _write_partial(partial_path, result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("control", "p2-baselines"),
        default="control",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        help="ordered target subset; default is the full D0 target order",
    )
    parser.add_argument(
        "--replicates",
        type=int,
        help=(
            "fixed control smoke count (non-authoritative), or P2 baseline "
            "extension count"
        ),
    )
    parser.add_argument("--c0b-json", type=Path, default=DEFAULT_C0B)
    parser.add_argument(
        "--control-json",
        type=Path,
        help="completed C4 control artifact, required by p2-baselines mode",
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--partial", type=Path, default=DEFAULT_PARTIAL)
    args = parser.parse_args()
    if args.replicates is not None and args.replicates < 2:
        parser.error("--replicates must be at least 2")
    if args.mode == "p2-baselines" and args.control_json is None:
        parser.error("--control-json is required in p2-baselines mode")
    return args


def main() -> None:
    args = parse_args()
    started_unix = time.time()
    started_perf = time.perf_counter()
    for path, expected in EXPECTED_AUTHORITY_DIGESTS.items():
        actual = sha256_file(Path(path))
        if actual != expected:
            raise ValueError(f"authority digest mismatch for {path}: {actual}")
    d0 = json.loads(D0_JSON.read_text())
    input_verification = verify_inputs(d0, args.c0b_json)
    c0b = json.loads(args.c0b_json.read_text())
    if not (
        c0b["status"] == "PASS"
        and c0b["summary"]["e4_bit_identical_pass"]
        and c0b["summary"]["e2_repeated_draw_control_pass"]
        and c0b["summary"]["identity_digest_mismatch_count"] == 0
    ):
        raise ValueError("adopted C0b artifact is not a clean E4/E2 pass")
    c0b_lookup = {
        (item["target"], item["pattern"]): item for item in c0b["patterns"]
    }
    data = load_analysis_data(d0)
    all_targets = list(data["target_specs"])
    targets = args.targets or all_targets
    unknown = [target for target in targets if target not in data["target_specs"]]
    if unknown:
        raise ValueError(f"unknown target(s): {unknown}")
    if len(targets) != len(set(targets)):
        raise ValueError("--targets contains duplicates")

    result = _base_result(
        mode=args.mode,
        targets=targets,
        input_verification=input_verification,
        data=data,
        c0b_path=args.c0b_json,
        started_unix=started_unix,
    )
    _write_partial(args.partial, result)

    if args.mode == "control":
        run_control_mode(
            result,
            data,
            c0b_lookup,
            targets,
            args.replicates,
            args.partial,
        )
        failed = [item["id"] for item in result["statistics"] if not item["pass"]]
        result["summary"] = {
            "targets_run": len(targets),
            "gated_cells_run": len(result["statistics"]),
            "full_C4_stochastic_K": C4_STOCHASTIC_K,
            "deterministic_empty_G3_checks_run": len(
                result["deterministic_empty_G3_checks"]
            ),
            "targets_escalated": [
                item["target"] for item in result["targets"] if item["escalated"]
            ],
            "failed_count": len(failed),
            "failed_ids": failed,
            "all_run_cells_pass": not failed,
        }
        if args.replicates is not None:
            result["status"] = "NON_AUTHORITATIVE_FIXED_REPLICATE_RUN"
        elif failed:
            result["status"] = "FAIL"
        elif targets == all_targets:
            result["status"] = "PASS"
        else:
            result["status"] = "PARTIAL_TARGETS_PASS"
    else:
        control = json.loads(args.control_json.read_text())
        run_p2_baseline_mode(
            result,
            data,
            c0b_lookup,
            targets,
            control,
            args.replicates,
            args.partial,
        )
        result["summary"] = {
            "targets_run": len(targets),
            "cells_run": len(result["cells"]),
            "control_source": {
                "path": str(args.control_json),
                "sha256": sha256_file(args.control_json),
            },
            "control_decisions_reopened": False,
        }
        result["status"] = "P2_NULL_BASELINES_COMPLETE"

    result["execution_diagnostics"].update(
        {
            "finished_unix": time.time(),
            "elapsed_seconds": time.perf_counter() - started_perf,
            "peak_rss_mb": peak_rss_mb(),
        }
    )
    output = args.out or (
        DEFAULT_OUT
        if args.mode == "control"
        else Path("/tmp/qrf_phase0_a17_c4_p2_baselines.json")
    )
    output_sha = write_canonical_result(output, result)
    args.partial.unlink(missing_ok=True)
    print(f"RESULT {output} sha256={output_sha} status={result['status']}")


if __name__ == "__main__":
    main()
