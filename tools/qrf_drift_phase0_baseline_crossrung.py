#!/usr/bin/env python3
"""Replay the two baseline1pct cross-rung P0/P1 positive-leg readings.

The primary P1 executor deliberately prioritized the candidate-25 ledger and
left the baseline gate-dependent levels unavailable.  This helper fills only
the frozen A15.53 cross-rung matrix:

* ``self_employment_income_last_year`` / positive; and
* ``spm_unit_energy_subsidy`` / positive.

It restores each gate from the banked pre-target chain state, fits the
unchanged production ``HistGradientBoostingClassifier`` on the pinned 1%
donor projection, and verifies the replay against two independent bank
bindings: every realized sign draw and the exact post-draw RNG state.  It does
not fit or replay a magnitude forest.  Raw magnitude draws come from the
pinned banks, while codec and structural surfaces use the production readers
already registered by the sealed Step-0 operator table.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd
import qrf_drift_phase0_c4 as c4
import qrf_drift_phase0_p1 as p1
import qrf_drift_phase0_replay as replay
from sklearn.ensemble import HistGradientBoostingClassifier

WORKTREE = Path(__file__).resolve().parents[1]
D0_JSON = WORKTREE / "experiments/qrf_drift_validation_d0.json"
DESIGN_MD = WORKTREE / "experiments/qrf_drift_validation_design.md"
A16_BINDING = WORKTREE / "experiments/qrf_drift_validation_a16_binding_texts.md"
DEFAULT_STEP0 = Path("/private/tmp/qrf_phase0_a17_terminal_report.json")
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_baseline_crossrung.json")
TARGETS = (
    "self_employment_income_last_year",
    "spm_unit_energy_subsidy",
)
TOP_LEVEL_ROWS = ("L0", "B1", "B2", "T1", "T2", "T3", "T4", "T5")
EXPECTED_D0_SHA256 = p1.EXPECTED_D0_SHA256
EXPECTED_DESIGN_SHA256 = p1.EXPECTED_DESIGN_SHA256
EXPECTED_A16_BINDING_SHA256 = p1.EXPECTED_A16_BINDING_SHA256


class BaselineSurfaceUnavailableError(RuntimeError):
    """One of the exact baseline surfaces cannot be bound to its bank."""

    def __init__(self, stage: str, evidence: dict[str, Any]) -> None:
        super().__init__(f"baseline1pct {stage} surface is unavailable")
        self.stage = stage
        self.evidence = evidence


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _peak_rss_mb() -> float:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return float(raw) / (1024.0 * 1024.0)
    return float(raw) / 1024.0


def _baseline_d0_view(d0: dict[str, Any]) -> dict[str, Any]:
    """Point the generic frozen-surface loader at the D0-pinned 1% rung."""
    result = copy.deepcopy(d0)
    artifact = copy.deepcopy(result["D0-0"]["artifacts"]["baseline1pct"])
    result["D0-0"]["artifacts"]["candidate-25"] = artifact
    banks = {row["target"]: row["path"] for row in artifact["bank_target_checkpoints"]}
    if set(banks) != set(result["D0-2"]["targets"]):
        raise ValueError("baseline target-bank roster differs from D0-2")
    for target, spec in result["D0-2"]["targets"].items():
        spec["target_bank_file"] = banks[target]
    return result


def _index_identity(values: np.ndarray) -> dict[str, Any]:
    """Reproduce the production QRF row-order fingerprint."""
    index = pd.Index(np.asarray(values, dtype=np.int64))
    hashes = pd.util.hash_pandas_object(
        index,
        index=False,
        categorize=False,
    ).to_numpy(dtype="<u8", copy=False)
    return {
        "length": len(index),
        "class_name": type(index).__name__,
        "dtype": str(index.dtype),
        "names_repr": repr(tuple(index.names)),
        "sha256": hashlib.sha256(hashes.tobytes(order="C")).hexdigest(),
    }


def _donor_index_values(
    target_spec: dict[str, Any],
    projection: dict[str, dict[str, np.ndarray]],
) -> np.ndarray:
    """Recover the production input index for the two registered operators."""
    if target_spec["entity"] == "spm_unit":
        # The producer creates its group donor DataFrame with a fresh Index.
        return np.arange(len(projection["J1"]["values"]), dtype=np.int64)
    # The early direct-transfer table retains physical person positions.
    return np.asarray(projection["J1"]["physical"], dtype=np.int64)


def _gate_choices(
    probabilities: np.ndarray, classes: np.ndarray, uniforms: np.ndarray
) -> np.ndarray:
    probabilities = np.asarray(probabilities, dtype=np.float64)
    classes = np.asarray(classes)
    uniforms = np.asarray(uniforms, dtype=np.float64)
    if probabilities.ndim != 2 or len(probabilities) != len(uniforms):
        raise ValueError("gate choice arrays do not align")
    cumulative = np.cumsum(probabilities, axis=1)
    chosen = (cumulative >= uniforms[:, None]).argmax(axis=1)
    return classes[chosen]


def _fit_gate_context(
    data: dict[str, Any],
    target: str,
    pattern: dict[str, Any],
    projection: dict[str, dict[str, np.ndarray]],
) -> dict[str, Any]:
    """Restore and bind one baseline gate without a changed-data refit."""
    target_spec = data["target_specs"][target]
    role = data["roles"][c4.role_for_target(target_spec)]
    bank = data["current_banks"][target]
    name = pattern["name"]
    step = next(
        row for row in bank["metadata"]["pattern_steps"] if row["pattern"] == name
    )
    before, before_sha, before_source = replay.state_before_for_pattern(
        bank,
        name,
        data["bank_cache"],
    )
    if before_sha != step["state_before_sha256"]:
        raise BaselineSurfaceUnavailableError(
            "gate_state",
            {
                "target": target,
                "pattern": name,
                "reason": "recovered pre-target state digest differs from bank step",
                "expected": step["state_before_sha256"],
                "actual": before_sha,
            },
        )

    columns = (*tuple(before["predictors"]), *tuple(before["completed_targets"]))
    predictor_pattern = next(
        row
        for row in data["predictor_specs"][target]["patterns"]
        if row["name"] == name
    )
    if columns != tuple(predictor_pattern["effective_gate_columns"]):
        raise BaselineSurfaceUnavailableError(
            "gate_columns",
            {
                "target": target,
                "pattern": name,
                "bank_columns": list(columns),
                "D0_columns": predictor_pattern["effective_gate_columns"],
            },
        )

    donor_x = np.column_stack(
        [
            role["donor_surface"][column]
            if column in role["donor_surface"]
            else role["donor_targets"][column]
            for column in columns
        ]
    ).astype(np.float64, copy=False)
    donor_y = np.asarray(
        role["donor_targets"][bank["metadata"]["target"]["model_target"]],
        dtype=np.float64,
    )
    donor_weights = np.asarray(role["donor_weights"], dtype=np.float64)
    expected_donor_index = step["state_after"]["donor_index"]
    donor_index = _index_identity(_donor_index_values(target_spec, projection))
    weight_sha = replay.weight_identity(donor_weights)
    bindings = {
        "state_before_sha256": True,
        "effective_gate_columns": True,
        "donor_rows": len(donor_y) == int(expected_donor_index["length"]),
        "donor_index": donor_index == expected_donor_index,
        "donor_weight_order": weight_sha == before["weight_sha256"],
    }
    if not all(bindings.values()):
        raise BaselineSurfaceUnavailableError(
            "donor_fit_input",
            {
                "target": target,
                "pattern": name,
                "bindings": bindings,
                "donor_index_expected": expected_donor_index,
                "donor_index_actual": donor_index,
                "weight_sha256_expected": before["weight_sha256"],
                "weight_sha256_actual": weight_sha,
            },
        )
    if (
        not np.isfinite(donor_x).all()
        or not np.isfinite(donor_y).all()
        or not np.isfinite(donor_weights).all()
        or (donor_weights <= 0.0).any()
    ):
        raise BaselineSurfaceUnavailableError(
            "donor_fit_input",
            {"target": target, "pattern": name, "reason": "nonfinite fit surface"},
        )

    fit_rng = np.random.default_rng()
    fit_rng.bit_generator.state = copy.deepcopy(before["fit_rng_state"])
    gate_seed = int(fit_rng.integers(0, 2**31 - 1))
    gate = HistGradientBoostingClassifier(random_state=gate_seed)
    donor_labels = replay.sign_labels(donor_y)
    gate.fit(donor_x, donor_labels, sample_weight=donor_weights)
    gate_classes = np.asarray(gate.classes_, dtype=np.int8)
    if not np.array_equal(gate_classes, np.unique(donor_labels)):
        raise BaselineSurfaceUnavailableError(
            "gate_fit",
            {
                "target": target,
                "pattern": name,
                "expected_classes": [int(value) for value in np.unique(donor_labels)],
                "actual_classes": [int(value) for value in gate_classes],
            },
        )

    physical = role["recipient_physical"][pattern["positions"]]
    recipient_index = _index_identity(physical)
    expected_recipient_index = step["state_after"]["recipient_index"]
    if recipient_index != expected_recipient_index:
        raise BaselineSurfaceUnavailableError(
            "recipient_pattern",
            {
                "target": target,
                "pattern": name,
                "expected": expected_recipient_index,
                "actual": recipient_index,
            },
        )
    context_for_x = {
        "role": role,
        "columns": columns,
        "bank": bank,
        "target": target,
        "pattern": name,
    }
    recipient_x = p1._recipient_x(data, context_for_x, pattern["positions"])
    recipient_probabilities = np.asarray(
        gate.predict_proba(recipient_x),
        dtype=np.float64,
    )

    # Production consumes one magnitude-quantile vector before the gate
    # categorical uniforms.  Forest evaluation consumes no additional draws.
    draw_rng = np.random.default_rng()
    draw_rng.bit_generator.state = copy.deepcopy(before["draw_rng_state"])
    draw_rng.random(len(recipient_x))
    gate_uniforms = draw_rng.random(len(recipient_x))
    replayed_signs = _gate_choices(
        recipient_probabilities,
        gate_classes,
        gate_uniforms,
    )
    raw = np.asarray(bank["raw"][physical], dtype=np.float64)
    raw_signs = replay.sign_labels(raw)
    sign_match = np.array_equal(replayed_signs, raw_signs)
    draw_state_match = (
        draw_rng.bit_generator.state == step["state_after"]["draw_rng_state"]
    )
    if not sign_match or not draw_state_match:
        raise BaselineSurfaceUnavailableError(
            "gate_replay",
            {
                "target": target,
                "pattern": name,
                "realized_sign_mismatch_rows": int((replayed_signs != raw_signs).sum()),
                "post_draw_rng_state_matches": draw_state_match,
            },
        )

    donor_probabilities = np.asarray(gate.predict_proba(donor_x), dtype=np.float64)
    return {
        "target": target,
        "pattern": name,
        "role": role,
        "bank": bank,
        "columns": columns,
        "donor_x": donor_x,
        "donor_y": donor_y,
        "donor_weights": donor_weights,
        "donor_probabilities": donor_probabilities,
        "gate": gate,
        "gate_seed": gate_seed,
        "gate_classes": gate_classes,
        "state_before_sha256": before_sha,
        "state_before_source": before_source,
        "bindings": {
            **bindings,
            "recipient_index": True,
            "realized_gate_signs": True,
            "post_draw_rng_state": True,
        },
        "recipient_x": recipient_x,
        "recipient_probabilities": recipient_probabilities,
        "recipient_index": recipient_index,
        "realized_sign_mismatch_rows": 0,
        "raw_boundary_rows": int(
            ((raw != 0.0) & (np.abs(raw) <= replay.ZERO_ATOL)).sum()
        ),
    }


def _pattern_readings(
    data: dict[str, Any],
    target: str,
    sq: np.ndarray,
    projection: dict[str, dict[str, np.ndarray]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    target_spec = data["target_specs"][target]
    role = data["roles"][c4.role_for_target(target_spec)]
    recipient_weights = np.asarray(role["recipient_weights"], dtype=np.float64)
    sq_total_weight = float(recipient_weights[sq].sum(dtype=np.float64))
    results: list[dict[str, Any]] = []
    contexts: dict[str, dict[str, Any]] = {}
    for pattern in role["patterns"]:
        context = _fit_gate_context(data, target, pattern, projection)
        name = pattern["name"]
        contexts[name] = context
        pattern_sq = sq[pattern["positions"]]
        weights = recipient_weights[pattern["positions"]][pattern_sq]
        recipient_probabilities = context["recipient_probabilities"][pattern_sq]
        alpha = float(weights.sum(dtype=np.float64) / sq_total_weight)
        legs: dict[str, Any] = {}
        for leg, sign in p1.LEGS.items():
            matches = np.flatnonzero(context["gate_classes"] == sign)
            donor_probability = (
                context["donor_probabilities"][:, matches[0]]
                if len(matches)
                else np.zeros(len(context["donor_y"]), dtype=np.float64)
            )
            recipient_probability = (
                recipient_probabilities[:, matches[0]]
                if len(matches)
                else np.zeros(len(weights), dtype=np.float64)
            )
            checked_alpha, e2_variance = p1._pattern_weight_terms(
                weights,
                recipient_probability,
                sq_total_weight,
            )
            if checked_alpha != alpha:
                raise ValueError(f"baseline alpha changed by leg for {target}/{name}")
            legs[leg] = {
                "m_observed": p1._weighted_summary(
                    context["donor_y"],
                    context["donor_weights"],
                    sign=sign,
                ),
                "P_D": p1._probability_summary(
                    donor_probability,
                    context["donor_weights"],
                ),
                "P_R": p1._probability_summary(recipient_probability, weights),
                "e2_conditional_variance_contribution": e2_variance,
            }
        results.append(
            {
                "pattern": name,
                "alpha": alpha,
                "S_q_rows": int(pattern_sq.sum()),
                "S_q_weight_sum": float(weights.sum(dtype=np.float64)),
                "S_q_mask": p1.mask_identity(pattern_sq),
                "gate_classes": [int(value) for value in context["gate_classes"]],
                "gate_seed": int(context["gate_seed"]),
                "state_before_sha256": context["state_before_sha256"],
                "state_before_source": context["state_before_source"],
                "gate_bindings": context["bindings"],
                "realized_sign_mismatch_rows": 0,
                "raw_boundary_rows": context["raw_boundary_rows"],
                "donor_probability_identity": p1.array_identity(
                    context["donor_probabilities"]
                ),
                "recipient_probability_identity": p1.array_identity(
                    context["recipient_probabilities"]
                ),
                "legs": legs,
            }
        )
    if not math.isclose(
        math.fsum(row["alpha"] for row in results),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-14,
    ):
        raise ValueError(f"baseline pattern alphas do not close for {target}")
    return results, contexts


def _baseline_support(d0: dict[str, Any], target: str) -> dict[str, Any]:
    target_data = d0["D0-1"]["rungs"]["baseline1pct"][target]
    counts = {
        origin: int(
            target_data[origin]["legs"]["positive"][
                "unique_clone_deduplicated_source_rows_clone0"
            ]
        )
        for origin in ("asec", "acs")
    }
    supported = all(value >= 50 for value in counts.values())
    return {
        "status": "SUPPORTED" if supported else "INSUFFICIENT_SUPPORT_NO_VERDICT",
        "floor": 50,
        "asec_unique_sources": counts["asec"],
        "acs_unique_sources": counts["acs"],
    }


def _dominant_label(rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    values = {name: abs(float(rows[name]["value"])) for name in TOP_LEVEL_ROWS}
    total = math.fsum(values.values())
    if total == 0.0:
        return {"row": "NA", "share": "NA", "sum_abs": 0.0}
    order = {name: index for index, name in enumerate(TOP_LEVEL_ROWS)}
    row = sorted(values, key=lambda name: (-values[name], order[name]))[0]
    return {"row": row, "share": float(values[row] / total), "sum_abs": float(total)}


def _d0_incidence_check(
    d0: dict[str, Any],
    target: str,
    j0: dict[str, Any],
    i_acs: dict[str, Any],
) -> dict[str, Any]:
    row = d0["D0-1"]["rungs"]["baseline1pct"][target]
    expected_j0 = float(row["asec"]["legs"]["positive"]["gate_incidence"])
    expected_i = float(row["acs"]["legs"]["positive"]["gate_incidence"])
    result = {
        "J0_expected": expected_j0,
        "J0_actual": float(j0["value"]),
        "J0_bit_exact": float(j0["value"]) == expected_j0,
        "I_acs_expected": expected_i,
        "I_acs_actual": float(i_acs["value"]),
        "I_acs_bit_exact": float(i_acs["value"]) == expected_i,
        "source": "D0-1/rungs/baseline1pct/<target>/<origin>/legs/positive/gate_incidence",
    }
    if not result["J0_bit_exact"] or not result["I_acs_bit_exact"]:
        raise BaselineSurfaceUnavailableError(
            "D0_incidence", {"target": target, **result}
        )
    return result


def _read_hdf_column(h5: h5py.File, pointer: str) -> np.ndarray:
    """Read one column from a D0 pointer of the form ``/path[:,N]``."""
    marker = "[:,"
    if marker not in pointer or not pointer.endswith("]"):
        raise ValueError(f"unsupported D0 HDF column pointer: {pointer}")
    dataset, raw_column = pointer.split(marker, maxsplit=1)
    column = int(raw_column[:-1])
    return np.asarray(h5[dataset][:, column])


def _pool_terminal_on_role(
    d0: dict[str, Any],
    target: str,
    target_spec: dict[str, Any],
    role: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Read and stable-ID align the D0-4 terminal surface from pool.h5."""
    d0_terminal = next(row for row in d0["D0-4"]["targets"] if row["target"] == target)
    pool_path = Path(d0["D0-4"]["pool"])
    entity = target_spec["entity"]
    id_pointer = (
        "/person/block8_values[:,16]"
        if entity == "person"
        else "/spm_unit/block4_values[:,0]"
    )
    with h5py.File(pool_path, "r") as h5:
        pool_ids = _read_hdf_column(h5, id_pointer)
        pool_values = replay.as_float(
            _read_hdf_column(h5, d0_terminal["terminal_dataset"])
        )
    joined = p1._stable_join(pool_ids, role["recipient_stable_id"])
    return pool_values[joined], {
        "path": str(pool_path),
        "terminal_dataset": d0_terminal["terminal_dataset"],
        "entity_id_dataset": id_pointer,
        "pool_value_identity": p1.array_identity(pool_values),
        "role_joined_value_identity": p1.array_identity(pool_values[joined]),
        "role_stable_id_identity": p1.array_identity(role["recipient_stable_id"]),
    }


def _run_target(
    data: dict[str, Any],
    aux: dict[str, Any],
    operator_table: list[dict[str, Any]],
    original_d0: dict[str, Any],
    target: str,
) -> dict[str, Any]:
    target_spec = data["target_specs"][target]
    role = data["roles"][c4.role_for_target(target_spec)]
    bank = data["current_banks"][target]
    projection = p1._projection(aux, target, target_spec)
    raw_full = np.asarray(bank["raw"], dtype=np.float64)
    decoded_full, codec = p1._production_codec(
        raw_full,
        projection["J1"]["values"],
        target,
        target_spec,
        operator_table,
    )
    raw_role = raw_full[role["recipient_physical"]]
    decoded_role = decoded_full[role["recipient_physical"]]
    structural_role, structural = p1._structural_surface(
        data,
        aux,
        target,
        target_spec,
        decoded_full,
        operator_table,
    )
    checkpoint_terminal_role = p1._terminal_on_role(aux, role, target, target_spec)
    terminal_role, pool_terminal_source = _pool_terminal_on_role(
        original_d0,
        target,
        target_spec,
        role,
    )
    scope = np.asarray(role["recipient_clone0"], dtype=bool)
    sq = (
        scope
        & np.isfinite(raw_role)
        & np.isfinite(decoded_role)
        & np.isfinite(structural_role)
    )
    so = scope & ~sq
    weights = np.asarray(role["recipient_weights"], dtype=np.float64)
    scope_weights = weights[scope]
    sq_weights = weights[sq]
    phi = float(sq_weights.sum(dtype=np.float64) / scope_weights.sum(dtype=np.float64))

    role_drawn = np.isfinite(raw_role)
    terminal_equal = role_drawn & (
        raw_role.view(np.uint64) == np.asarray(terminal_role).view(np.uint64)
    )
    structural_equal = role_drawn & (
        np.asarray(structural_role).view(np.uint64)
        == np.asarray(terminal_role).view(np.uint64)
    )
    checkpoint_equal = np.asarray(checkpoint_terminal_role).view(
        np.uint64
    ) == np.asarray(terminal_role).view(np.uint64)
    if (
        not terminal_equal[role_drawn].all()
        or not structural_equal[role_drawn].all()
        or not checkpoint_equal.all()
    ):
        raise BaselineSurfaceUnavailableError(
            "terminal_replay",
            {
                "target": target,
                "raw_terminal_unequal_rows": int((role_drawn & ~terminal_equal).sum()),
                "structural_terminal_unequal_rows": int(
                    (role_drawn & ~structural_equal).sum()
                ),
                "checkpoint_pool_unequal_rows": int((~checkpoint_equal).sum()),
            },
        )

    d0_terminal = next(
        row for row in original_d0["D0-4"]["targets"] if row["target"] == target
    )
    d0_lineage = next(
        row
        for row in original_d0["D0-5"]["recipient_raw_and_terminal"]["baseline1pct"][
            "targets"
        ]
        if row["target"] == target
    )
    full_drawn = np.isfinite(raw_full)
    p0_bindings = {
        "raw_draw_sha256_D0_4": bank["metadata"]["raw_draw_sha256"]
        == d0_terminal["raw_draw_sha256"],
        "raw_draw_sha256_D0_5": bank["metadata"]["raw_draw_sha256"]
        == d0_lineage["raw_draw_sha256"],
        "raw_rows_D0_4": len(raw_full) == int(d0_terminal["raw_rows"]),
        "raw_rows_D0_5": len(raw_full) == int(d0_lineage["raw_rows"]),
        "drawn_rows_D0_4": int(full_drawn.sum()) == int(d0_terminal["drawn_rows"]),
        "drawn_rows_D0_5": int(full_drawn.sum())
        == int(d0_lineage["raw_finite_recipient_rows"]),
        "terminal_role_bitwise": bool(terminal_equal[role_drawn].all()),
        "structural_role_bitwise": bool(structural_equal[role_drawn].all()),
        "checkpoint_pool_terminal_bitwise": bool(checkpoint_equal.all()),
        "clone0_projection_internal": int(sq.sum())
        == int(np.isfinite(raw_role[scope]).sum()),
    }
    if not all(p0_bindings.values()) or phi != 1.0 or so.any():
        raise BaselineSurfaceUnavailableError(
            "P0_mask",
            {
                "target": target,
                "bindings": p0_bindings,
                "phi": phi,
                "S_o_rows": int(so.sum()),
            },
        )

    scope_full = np.zeros(len(raw_full), dtype=bool)
    sq_full = np.zeros(len(raw_full), dtype=bool)
    scope_full[role["recipient_physical"][scope]] = True
    sq_full[role["recipient_physical"][sq]] = True
    path_census = p1._path_census(
        np.ones(int(scope.sum()), dtype=bool),
        np.ones(int(scope.sum()), dtype=bool),
        np.isfinite(raw_role[scope]),
        np.isfinite(decoded_role[scope]),
    )
    path_census.pop("_passed")
    p0 = {
        "status": "PASS_A17_BASELINE_SCOPE_AND_TERMINAL",
        "scope_rows": int(scope.sum()),
        "S_q_rows": int(sq.sum()),
        "S_o_rows": int(so.sum()),
        "phi": phi,
        "scope_mask": p1.mask_identity(scope_full),
        "S_q_mask": p1.mask_identity(sq_full),
        "S_o_mask": p1.mask_identity(scope_full & ~sq_full),
        "scope_role_axis_mask": p1.mask_identity(scope),
        "S_q_role_axis_mask": p1.mask_identity(sq),
        "full_bank_drawn_mask": p1.mask_identity(full_drawn),
        "path_census": path_census,
        "bindings": p0_bindings,
        "D0_4": d0_terminal,
        "D0_5": d0_lineage,
        "pool_terminal_source": pool_terminal_source,
    }

    pattern_rows, contexts = _pattern_readings(
        data,
        target,
        sq,
        projection,
    )
    j0 = p1._weighted_summary(
        projection["J0"]["values"],
        projection["J0"]["weights"],
        sign=1,
    )
    j1 = p1._weighted_summary(
        projection["J1"]["values"],
        projection["J1"]["weights"],
        sign=1,
    )
    j2 = p1._combined_level(
        [(row["alpha"], row["legs"]["positive"]["m_observed"]) for row in pattern_rows]
    )
    p_d = p1._combined_level(
        [(row["alpha"], row["legs"]["positive"]["P_D"]) for row in pattern_rows]
    )
    p_r = p1._combined_level(
        [(row["alpha"], row["legs"]["positive"]["P_R"]) for row in pattern_rows]
    )
    i_raw = p1._weighted_summary(raw_role[sq], sq_weights, sign=1)
    i_dec = p1._weighted_summary(decoded_role[sq], sq_weights, sign=1)
    i_q = p1._weighted_summary(structural_role[sq], sq_weights, sign=1)
    i_acs = p1._weighted_summary(terminal_role[scope], scope_weights, sign=1)
    i_o = p1._weighted_summary(terminal_role[so], weights[so], sign=1)
    d_level = p1._difference(j0, i_acs)
    incidence_binding = _d0_incidence_check(original_d0, target, j0, i_acs)

    j2_both = {
        leg: p1._combined_level(
            [(row["alpha"], row["legs"][leg]["m_observed"]) for row in pattern_rows]
        )
        for leg in p1.LEGS
    }
    j1_both = {
        leg: p1._weighted_summary(
            projection["J1"]["values"],
            projection["J1"]["weights"],
            sign=sign,
        )
        for leg, sign in p1.LEGS.items()
    }
    b2 = p1._b2_telescope(
        j1_both,
        j2_both,
        p1._b2_pattern_surfaces(
            data,
            target,
            projection,
            pattern_rows,
            contexts,
        ),
    )

    rows = {
        "L0": {"value": 0.0, "se": 0.0, "variance": 0.0, "empty_set": True},
        "B1": p1._difference(j0, j1, scale=phi),
        "B2": p1._difference(j1, j2, scale=phi),
        "T1": p1._difference(j2, p_d, scale=phi),
        "T2": p1._difference(p_d, p_r, scale=phi),
        "T3": {
            "value": float(phi * (p_r["value"] - i_raw["value"])),
            "variance": float(
                phi
                * phi
                * math.fsum(
                    row["legs"]["positive"]["e2_conditional_variance_contribution"]
                    for row in pattern_rows
                )
            ),
        },
        "T4": p1._difference(i_raw, i_dec, scale=phi),
        "T5": p1._difference(i_dec, i_q, scale=phi),
    }
    rows["T3"]["se"] = float(math.sqrt(max(rows["T3"]["variance"], 0.0)))
    residual = float(d_level["value"])
    for name in TOP_LEVEL_ROWS:
        residual -= float(rows[name]["value"])
    tolerance = 1e-9 * max(abs(float(d_level["value"])), 1e-12)
    rows["residual"] = {
        "value": float(residual),
        "se": "NA",
        "family": None,
        "tolerance": float(tolerance),
        "passes": abs(residual) <= tolerance,
    }
    if not rows["residual"]["passes"]:
        raise BaselineSurfaceUnavailableError(
            "ledger_closure",
            {"target": target, "residual": residual, "tolerance": tolerance},
        )
    scaled_b2 = math.fsum(
        float(row["value"]) for row in b2["legs"]["positive"]["rows"].values()
    )
    if not math.isclose(
        scaled_b2,
        float(rows["B2"]["value"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise BaselineSurfaceUnavailableError(
            "B2_closure",
            {"target": target, "subrow_sum": scaled_b2, "B2": rows["B2"]["value"]},
        )

    levels = {
        "J0": j0,
        "J1": j1,
        "J2": j2,
        "P_D": p_d,
        "P_R": p_r,
        "I_raw": i_raw,
        "I_dec": i_dec,
        "I_q": i_q,
        "I_o": i_o,
        "I_acs": i_acs,
        "D": d_level,
    }
    return {
        "status": "COMPLETE",
        "target": target,
        "leg": "positive",
        "P0": p0,
        "levels": levels,
        "ledger": rows,
        "pattern_rows": pattern_rows,
        "B2_diagnostics": b2,
        "codec": codec,
        "structural": {
            **structural,
            "raw_terminal_unequal_rows": 0,
            "structural_terminal_unequal_rows": 0,
            "checkpoint_pool_unequal_rows": 0,
            "A17_15_iii": "PASS",
        },
        "support": _baseline_support(original_d0, target),
        "dominant_label": _dominant_label(rows),
        "D0_incidence_binding": incidence_binding,
        "source": {
            "bank": str(bank["path"]),
            "bank_file_sha256": next(
                row["sha256"]
                for row in original_d0["D0-0"]["artifacts"]["baseline1pct"][
                    "bank_target_checkpoints"
                ]
                if row["target"] == target
            ),
            "raw_draw_sha256": bank["metadata"]["raw_draw_sha256"],
            "assembled_checkpoint": str(data["assembled_path"]),
            "transferred_checkpoint": str(data["transferred_path"]),
        },
    }


def _checkpoint_pin(d0: dict[str, Any], filename: str) -> str:
    return next(
        row["sha256"]
        for row in d0["D0-11"]["builds"]["baseline1pct"]["files"]
        if row["filename"] == filename
    )


def _verify_inputs(d0: dict[str, Any], d0_path: Path) -> dict[str, Any]:
    artifact = d0["D0-0"]["artifacts"]["baseline1pct"]
    root = Path(d0["D0-11"]["builds"]["baseline1pct"]["root"])
    expected: dict[Path, str] = {
        d0_path: EXPECTED_D0_SHA256,
        DESIGN_MD: EXPECTED_DESIGN_SHA256,
        A16_BINDING: EXPECTED_A16_BINDING_SHA256,
        root / "assembled.checkpoint.h5": _checkpoint_pin(
            d0, "assembled.checkpoint.h5"
        ),
        root / "transferred.checkpoint.h5": _checkpoint_pin(
            d0, "transferred.checkpoint.h5"
        ),
        Path(artifact["files"]["pool_h5"]["path"]): artifact["files"]["pool_h5"][
            "sha256"
        ],
    }
    for row in artifact["bank_target_checkpoints"]:
        expected[Path(row["path"])] = row["sha256"]
    checks: list[dict[str, Any]] = []
    for path, expected_sha in expected.items():
        actual_sha = p1.sha256_file(path)
        checks.append(
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256_expected": expected_sha,
                "sha256_actual": actual_sha,
                "match": actual_sha == expected_sha,
            }
        )
    failed = [row["path"] for row in checks if not row["match"]]
    if failed:
        raise ValueError(f"baseline cross-rung input digest mismatch: {failed}")
    return {"status": "PASS", "files": checks, "all_inputs_live_hashed": True}


def run(
    d0_path: Path,
    step0_path: Path,
    *,
    authoritative: bool = False,
) -> dict[str, Any]:
    started = time.time()
    d0 = json.loads(d0_path.read_text())
    input_verification = _verify_inputs(d0, d0_path)
    operator_table, operator_verification = p1._load_operator_table(step0_path)
    data = c4.load_analysis_data(_baseline_d0_view(d0))
    aux = p1._load_candidate_aux(data)
    targets: dict[str, Any] = {}
    unavailable: dict[str, Any] = {}
    for target in TARGETS:
        try:
            targets[target] = _run_target(
                data,
                aux,
                operator_table,
                d0,
                target,
            )
        except (BaselineSurfaceUnavailableError, p1.SurfaceUnavailableError) as error:
            evidence = getattr(error, "evidence", {"error": str(error)})
            stage = getattr(error, "stage", "unknown")
            targets[target] = {
                "status": "UNAVAILABLE_FAIL_CLOSED",
                "target": target,
                "leg": "positive",
                "stage": stage,
                "evidence": evidence,
            }
            unavailable[target] = {"stage": stage, "evidence": evidence}

    payload: dict[str, Any] = {
        "artifact_kind": "qrf_drift_phase0_baseline_crossrung_p0_p1",
        "schema_version": 1,
        "status": "COMPLETE" if not unavailable else "PARTIAL",
        "rung": "baseline1pct",
        "authority": {
            "D0": {"path": str(d0_path), "sha256": p1.sha256_file(d0_path)},
            "design": {"path": str(DESIGN_MD), "sha256": p1.sha256_file(DESIGN_MD)},
            "A16_binding": {
                "path": str(A16_BINDING),
                "sha256": p1.sha256_file(A16_BINDING),
            },
            "input_verification": input_verification,
            "sealed_step0_operator_source": operator_verification,
        },
        "baseline1pct": {"targets": targets},
        "unavailable_targets": unavailable,
        "execution": {
            "authoritative": authoritative,
            "elapsed_seconds": float(time.time() - started),
            "peak_rss_mb": _peak_rss_mb(),
            "python": sys.version,
            "no_magnitude_forest_refit": True,
            "gate_replay_rule": (
                "unchanged HGB fit from banked pre-target state; exact realized "
                "sign-draw and post-draw RNG-state validation"
            ),
        },
    }
    digest_scope = {
        key: value
        for key, value in payload.items()
        if key not in {"execution", "content_sha256"}
    }
    payload["content_sha256"] = hashlib.sha256(
        canonical_json(digest_scope).encode("utf-8")
    ).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d0-json", type=Path, default=D0_JSON)
    parser.add_argument("--step0-json", type=Path, default=DEFAULT_STEP0)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--authoritative",
        action="store_true",
        help="mark the execution as the Phase-0 authoritative baseline reading",
    )
    args = parser.parse_args()
    result = run(
        args.d0_json,
        args.step0_json,
        authoritative=args.authoritative,
    )
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        f"baseline cross-rung {result['status']}: "
        f"targets={len(result['baseline1pct']['targets'])} "
        f"elapsed={result['execution']['elapsed_seconds']:.3f}s "
        f"sha256={result['content_sha256']}"
    )


if __name__ == "__main__":
    main()
