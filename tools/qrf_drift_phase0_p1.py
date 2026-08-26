#!/usr/bin/env python3
"""Compute the deterministic Phase-0 P0/P1/P6/P7 readings.

The primary (candidate-25) path reuses the exact, C0b-bound gate loader from
``qrf_drift_phase0_c4``.  It never refits a magnitude forest.  The target
banks provide the raw recipient draws, the stage checkpoint provides the
native donor projections, and the two registered post-draw rules are replayed
explicitly:

* adult-care qualifying-person/one-carrier reconciliation; and
* weeks-unemployed clearing where unemployment compensation is non-positive.

Producer stages which existed only in memory during the build are emitted as
``NO_SURFACE`` diagnostics.  They are not guessed or reconstructed.  B1 stays
the one additive J0-J1 bridge, as required by A15.18--21.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import qrf_drift_phase0_c4 as c4
import qrf_drift_phase0_replay as replay

WORKTREE = Path(__file__).resolve().parents[1]
D0_JSON = WORKTREE / "experiments/qrf_drift_validation_d0.json"
ADOPTED_REPORT = WORKTREE / "experiments/qrf_drift_validation_phase0.json"
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_p1.json")
ZERO_ATOL = 1e-6
LEGS = {"positive": 1, "negative": -1}
TARGETS = (
    "child_support_expense",
    "child_support_received",
    "weeks_unemployed",
    "workers_compensation",
    "spm_unit_energy_subsidy",
    "pre_subsidy_care_expenses",
    "self_employment_income_last_year",
    "unemployment_compensation",
    "disability_benefits",
)
CROSS_RUNG_TARGETS = (
    "self_employment_income_last_year",
    "spm_unit_energy_subsidy",
)


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
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_identity(values: np.ndarray) -> dict[str, Any]:
    return c4.array_identity(np.asarray(values))


def mask_identity(mask: np.ndarray) -> dict[str, Any]:
    values = np.ascontiguousarray(np.asarray(mask, dtype=np.uint8))
    return {
        "rows": int(values.sum()),
        "length": int(len(values)),
        "dtype": values.dtype.str,
        "sha256": hashlib.sha256(values.tobytes(order="C")).hexdigest(),
    }


def peak_rss_mb() -> float:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return float(raw) / (1024.0 * 1024.0)
    return float(raw) / 1024.0


def _text(values: np.ndarray) -> np.ndarray:
    return np.asarray(values).astype(str)


def _weighted_summary(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    sign: int,
) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if len(values) != len(weights):
        raise ValueError("value/weight length mismatch")
    if len(values) == 0:
        return {
            "value": "NA",
            "se": "NA",
            "variance": "NA",
            "rows": 0,
            "weight_sum": 0.0,
            "weight_sum_squares": 0.0,
            "kish_effective_n": "NA",
            "carrier_rows": 0,
            "carrier_weight_mass": 0.0,
            "empty_set": True,
        }
    if not np.isfinite(values).all() or not np.isfinite(weights).all():
        raise ValueError("non-finite value/weight in weighted incidence")
    if (weights <= 0).any():
        raise ValueError("non-positive analysis weight")
    carrier = values > ZERO_ATOL if sign > 0 else values < -ZERO_ATOL
    weight_sum = weights.sum(dtype=np.float64)
    weight_sum_squares = np.square(weights).sum(dtype=np.float64)
    incidence = weights[carrier].sum(dtype=np.float64) / weight_sum
    n_eff = weight_sum * weight_sum / weight_sum_squares
    variance = incidence * (1.0 - incidence) / n_eff
    return {
        "value": float(incidence),
        "se": float(math.sqrt(max(variance, 0.0))),
        "variance": float(variance),
        "rows": int(len(values)),
        "weight_sum": float(weight_sum),
        "weight_sum_squares": float(weight_sum_squares),
        "kish_effective_n": float(n_eff),
        "carrier_rows": int(carrier.sum()),
        "carrier_weight_mass": float(weights[carrier].sum(dtype=np.float64)),
        "empty_set": False,
    }


def _probability_summary(
    probabilities: np.ndarray,
    weights: np.ndarray,
) -> dict[str, Any]:
    probabilities = np.asarray(probabilities, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if len(probabilities) == 0:
        raise ValueError("probability level cannot use an empty population")
    if (
        not np.isfinite(probabilities).all()
        or not np.isfinite(weights).all()
        or (weights <= 0).any()
        or (probabilities < 0).any()
        or (probabilities > 1).any()
    ):
        raise ValueError("invalid probability level")
    weight_sum = weights.sum(dtype=np.float64)
    weight_sum_squares = np.square(weights).sum(dtype=np.float64)
    mean = np.dot(weights, probabilities) / weight_sum
    n_eff = weight_sum * weight_sum / weight_sum_squares
    variance = mean * (1.0 - mean) / n_eff
    return {
        "value": float(mean),
        "se": float(math.sqrt(max(variance, 0.0))),
        "variance": float(variance),
        "rows": int(len(probabilities)),
        "weight_sum": float(weight_sum),
        "weight_sum_squares": float(weight_sum_squares),
        "kish_effective_n": float(n_eff),
    }


def _combined_level(parts: list[tuple[float, dict[str, Any]]]) -> dict[str, Any]:
    value = math.fsum(alpha * float(level["value"]) for alpha, level in parts)
    variance = math.fsum(
        alpha * alpha * float(level["variance"]) for alpha, level in parts
    )
    return {
        "value": float(value),
        "se": float(math.sqrt(max(variance, 0.0))),
        "variance": float(variance),
        "components": len(parts),
    }


def _difference(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    scale: float = 1.0,
) -> dict[str, Any]:
    value = scale * (float(left["value"]) - float(right["value"]))
    variance = scale * scale * (float(left["variance"]) + float(right["variance"]))
    return {
        "value": float(value),
        "se": float(math.sqrt(max(variance, 0.0))),
        "variance": float(variance),
    }


def _support(d0: dict[str, Any], target: str, leg: str) -> dict[str, Any]:
    target_data = d0["D0-1"]["rungs"]["candidate-25"][target]
    asec = target_data["asec"]["legs"][leg]
    acs = target_data["acs"]["legs"][leg]
    asec_count = int(asec["unique_clone_deduplicated_source_rows_clone0"])
    acs_count = int(acs["unique_clone_deduplicated_source_rows_clone0"])
    supported = asec_count >= 50 and acs_count >= 50
    return {
        "status": "SUPPORTED" if supported else "INSUFFICIENT_SUPPORT_NO_VERDICT",
        "floor": 50,
        "asec_unique_sources": asec_count,
        "acs_unique_sources": acs_count,
        "reason": (
            "both clone-0 source counts meet the frozen 50-unique floor"
            if supported
            else "at least one clone-0 source count is below the frozen 50-unique floor"
        ),
    }


def _receipt_for_target(d0: dict[str, Any], target: str) -> dict[str, Any]:
    return next(
        row
        for row in d0["D0-3"]["candidate"]["target_receipts"]
        if row["target"] == target
    )


def _c0b_lookup(adopted: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    patterns = adopted["controls"]["C0b"]["result_compacted"]["patterns"]
    lookup = {(row["target"], row["pattern"]): row for row in patterns}
    if len(lookup) != 36:
        raise ValueError(f"expected 36 adopted C0b patterns, got {len(lookup)}")
    return lookup


def _stable_join(source_ids: np.ndarray, wanted_ids: np.ndarray) -> np.ndarray:
    source_ids = np.asarray(source_ids)
    wanted_ids = np.asarray(wanted_ids)
    order = np.argsort(source_ids, kind="stable")
    sorted_ids = source_ids[order]
    positions = np.searchsorted(sorted_ids, wanted_ids)
    if (positions >= len(sorted_ids)).any() or not np.array_equal(
        sorted_ids[positions], wanted_ids
    ):
        raise ValueError("stable IDs do not join exactly")
    return order[positions]


def _load_candidate_aux(data: dict[str, Any]) -> dict[str, Any]:
    """Load only P1 columns not retained by the C4 analysis context."""
    checkpoint = replay.SelectedCheckpoint(data["transferred_path"])
    person_names = (
        "person_id",
        "person_source_id",
        "person_household_id",
        "person_spm_unit_id",
        "person_support_channel",
        "person_support_clone_index",
        "person_tax_unit_id",
        "tax_unit_role_input",
        "is_incapable_of_self_care",
        *[target for target in TARGETS if target != "spm_unit_energy_subsidy"],
    )
    person = {name: checkpoint.column("person", name) for name in person_names}
    household_ids = checkpoint.column("household", "household_id")
    household_weights = checkpoint.household_weights()
    person_weights = replay.broadcast_by_id(
        household_ids,
        household_weights,
        person["person_household_id"],
    ).astype(np.float64, copy=False)
    spm_names = (
        "spm_unit_id",
        "spm_unit_source_id",
        "spm_unit_support_channel",
        "spm_unit_support_clone_index",
        "spm_unit_energy_subsidy",
    )
    spm = {name: checkpoint.column("spm_unit", name) for name in spm_names}
    spm_weights = replay.group_weights(
        person_weights,
        person["person_spm_unit_id"],
        spm["spm_unit_id"],
    )
    loaded = list(checkpoint.loaded)
    checkpoint.close()
    return {
        "person": person,
        "person_weights": person_weights,
        "spm_unit": spm,
        "spm_unit_weights": spm_weights,
        "loaded_columns": loaded,
    }


def _projection(
    aux: dict[str, Any],
    target: str,
    target_spec: dict[str, Any],
) -> dict[str, dict[str, np.ndarray]]:
    if target_spec["entity"] == "person":
        table = aux["person"]
        weights = aux["person_weights"]
        channel = _text(table["person_support_channel"])
        clone = np.asarray(table["person_support_clone_index"], dtype=np.int64)
        values = replay.as_float(table[target])
        stable_ids = table["person_id"]
        source_ids = table["person_source_id"]
    else:
        table = aux["spm_unit"]
        weights = aux["spm_unit_weights"]
        channel = _text(table["spm_unit_support_channel"])
        clone = np.asarray(table["spm_unit_support_clone_index"], dtype=np.int64)
        values = replay.as_float(table[target])
        stable_ids = table["spm_unit_id"]
        source_ids = table["spm_unit_source_id"]
    clone0 = (channel == "asec") & (clone == 0)
    j1_clone = 0 if target_spec["stage"] == "early_gap_fill" else 1
    j1 = (channel == "asec") & (clone == j1_clone)
    clone2 = (channel == "asec") & (clone == 2)

    def selected(mask: np.ndarray) -> dict[str, np.ndarray]:
        return {
            "values": values[mask],
            "weights": weights[mask],
            "stable_ids": stable_ids[mask],
            "source_ids": source_ids[mask],
            "physical": np.flatnonzero(mask),
        }

    return {"J0": selected(clone0), "J1": selected(j1), "clone2": selected(clone2)}


def _terminal_on_role(
    aux: dict[str, Any],
    role: dict[str, Any],
    target: str,
    target_spec: dict[str, Any],
) -> np.ndarray:
    if target_spec["entity"] == "spm_unit":
        return replay.as_float(aux["spm_unit"][target])[role["recipient_physical"]]
    values = replay.as_float(aux["person"][target])
    if target_spec["stage"] == "early_gap_fill":
        joined = _stable_join(aux["person"]["person_id"], role["recipient_stable_id"])
        return values[joined]
    return values[role["recipient_physical"]]


def _structural_surface(
    data: dict[str, Any],
    aux: dict[str, Any],
    target: str,
    target_spec: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return post-structural values in the target role's recipient order."""
    role = data["roles"][c4.role_for_target(target_spec)]
    bank = data["current_banks"][target]
    physical = role["recipient_physical"]
    raw_role = bank["raw"][physical]
    decoded = raw_role.copy()
    diagnostic: dict[str, Any] = {
        "codec": "identity_numeric",
        "codec_exact": True,
        "structural_rule": "identity",
        "cleared_positive_rows": 0,
    }
    if target == "weeks_unemployed":
        unemployment = replay.as_float(aux["person"]["unemployment_compensation"])[
            physical
        ]
        structural = decoded.copy()
        clear = (
            np.isfinite(structural) & (structural > ZERO_ATOL) & ~(unemployment > 0.0)
        )
        structural[clear] = 0.0
        diagnostic.update(
            {
                "structural_rule": "weeks_requires_positive_unemployment_compensation",
                "cleared_positive_rows": int(clear.sum()),
                "cleared_mask": mask_identity(clear),
                "unemployment_positive_rows": int((unemployment > 0.0).sum()),
                "code_authority": "A16-23/A13 pin 95f48a08 semantic recipient rule",
            }
        )
        return structural, diagnostic
    if target == "pre_subsidy_care_expenses":
        from microcosm.build.us_runtime.acs_transfer import (
            reconcile_acs_adult_care,
        )

        person = aux["person"]
        full_raw = np.asarray(bank["raw"], dtype=np.float64)
        mutable = np.isfinite(full_raw)
        expenses = replay.as_float(person[target]).copy()
        expenses[mutable] = full_raw[mutable]
        structural_frame = pd.DataFrame(
            {
                "pre_subsidy_care_expenses": expenses,
                "is_incapable_of_self_care": person["is_incapable_of_self_care"],
                "tax_unit_role_input": person["tax_unit_role_input"],
                "person_tax_unit_id": person["person_tax_unit_id"],
            }
        )
        reconciled, counts = reconcile_acs_adult_care(
            structural_frame,
            mutable_rows=mutable,
        )
        structural_full = replay.as_float(reconciled.to_numpy(copy=False))
        before_positive = mutable & (full_raw > ZERO_ATOL)
        after_positive = mutable & (structural_full > ZERO_ATOL)
        clear = before_positive & ~after_positive
        diagnostic.update(
            {
                "structural_rule": "adult_care_qualifying_one_per_tax_unit",
                "cleared_positive_rows": int(clear.sum()),
                "cleared_mask": mask_identity(clear),
                "production_counts": counts,
                "code_authority": "microcosm.build.us_runtime.acs_transfer.reconcile_acs_adult_care",
            }
        )
        return structural_full[physical], diagnostic
    return decoded, diagnostic


def _recipient_x(
    data: dict[str, Any],
    context: dict[str, Any],
    pattern_positions: np.ndarray,
) -> np.ndarray:
    role = context["role"]
    physical = role["recipient_physical"][pattern_positions]
    columns: list[np.ndarray] = []
    for name in context["columns"]:
        if name in role["recipient_surface"]:
            columns.append(role["recipient_surface"][name][pattern_positions])
        else:
            prior_path = replay.find_bank_for_target(
                Path(context["bank"]["path"]).parent,
                name,
            )
            prior = replay.load_bank(prior_path, data["bank_cache"])
            columns.append(prior["raw"][physical])
    result = np.column_stack(columns).astype(np.float64, copy=False)
    if not np.isfinite(result).all():
        raise ValueError(
            f"non-finite recipient gate input for {context['target']}/{context['pattern']}"
        )
    return result


def _pattern_readings(
    data: dict[str, Any],
    target: str,
    c0b_lookup: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    target_spec = data["target_specs"][target]
    role = data["roles"][c4.role_for_target(target_spec)]
    bank = data["current_banks"][target]
    total_weight = float(target_spec["clone0_recipient_weight_sum"])
    contexts: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for _d0_pattern, pattern in zip(
        target_spec["patterns"], role["patterns"], strict=True
    ):
        name = pattern["name"]
        context = c4.fit_gate_context(data, target, name, c0b_lookup)
        contexts[name] = context
        positions = pattern["positions"]
        physical = role["recipient_physical"][positions]
        sq = role["recipient_clone0"][positions] & np.isfinite(bank["raw"][physical])
        weights = role["recipient_weights"][positions][sq]
        recipient_x = _recipient_x(data, context, positions)
        recipient_probabilities = np.asarray(
            context["gate"].predict_proba(recipient_x),
            dtype=np.float64,
        )
        adopted = c0b_lookup[(target, name)]
        probability_binding = (
            array_identity(recipient_probabilities)["sha256"]
            == adopted["recipient_gate_probability_matrix_sha256"]
        )
        if not probability_binding:
            raise ValueError(
                f"recipient probability binding failed for {target}/{name}"
            )
        recipient_sq_probability = recipient_probabilities[sq]
        alpha = weights.sum(dtype=np.float64) / total_weight
        legs: dict[str, Any] = {}
        for leg, sign in LEGS.items():
            match = np.flatnonzero(context["gate_classes"] == sign)
            donor_p = (
                context["donor_probabilities"][:, match[0]]
                if len(match)
                else np.zeros(len(context["donor_y"]), dtype=np.float64)
            )
            recipient_p = (
                recipient_sq_probability[:, match[0]]
                if len(match)
                else np.zeros(len(weights), dtype=np.float64)
            )
            observed = _weighted_summary(
                context["donor_y"],
                context["donor_weights"],
                sign=sign,
            )
            donor_level = _probability_summary(donor_p, context["donor_weights"])
            recipient_level = _probability_summary(recipient_p, weights)
            e2_variance_numerator = np.dot(
                np.square(weights),
                recipient_p * (1.0 - recipient_p),
            )
            legs[leg] = {
                "m_observed": observed,
                "P_D": donor_level,
                "P_R": recipient_level,
                "e2_conditional_variance_contribution": float(
                    e2_variance_numerator / (total_weight * total_weight)
                ),
            }
        results.append(
            {
                "pattern": name,
                "alpha": float(alpha),
                "S_q_rows": int(sq.sum()),
                "S_q_weight_sum": float(weights.sum(dtype=np.float64)),
                "S_q_mask": mask_identity(sq),
                "gate_classes": [int(value) for value in context["gate_classes"]],
                "gate_seed": int(context["gate_seed"]),
                "state_before_sha256": context["state_before_sha256"],
                "donor_probability_identity": array_identity(
                    context["donor_probabilities"]
                ),
                "recipient_probability_identity": array_identity(
                    recipient_probabilities
                ),
                "recipient_probability_matches_adopted_C0b": probability_binding,
                "legs": legs,
            }
        )
    if not math.isclose(math.fsum(row["alpha"] for row in results), 1.0, abs_tol=1e-14):
        raise ValueError(f"pattern alpha weights do not close for {target}")
    return results, contexts


def _native_stage_payload(
    values: np.ndarray,
    weights: np.ndarray,
    stable_ids: np.ndarray,
) -> dict[str, Any]:
    return {
        "status": "AVAILABLE",
        "row_count": int(len(values)),
        "row_identity": array_identity(stable_ids),
        "values_identity": array_identity(np.asarray(values, dtype=np.float64)),
        "weights_identity": array_identity(np.asarray(weights, dtype=np.float64)),
        "unweighted_sign_counts": {
            "negative": int((values < -ZERO_ATOL).sum()),
            "zero": int((np.abs(values) <= ZERO_ATOL).sum()),
            "positive": int((values > ZERO_ATOL).sum()),
        },
        "weighted_sign_mass": {
            "negative": float(weights[values < -ZERO_ATOL].sum(dtype=np.float64)),
            "zero": float(weights[np.abs(values) <= ZERO_ATOL].sum(dtype=np.float64)),
            "positive": float(weights[values > ZERO_ATOL].sum(dtype=np.float64)),
        },
        "incidence": {
            leg: _weighted_summary(values, weights, sign=sign)["value"]
            for leg, sign in LEGS.items()
        },
    }


def _producer_ledger(
    adopted: dict[str, Any],
    target: str,
    projection: dict[str, dict[str, np.ndarray]],
    bank: dict[str, Any],
    sq_values: np.ndarray,
    sq_weights: np.ndarray,
    sq_ids: np.ndarray,
    decoded: np.ndarray,
    structural: np.ndarray,
) -> dict[str, Any]:
    operator_rows = [
        row
        for row in adopted.get("step0", {}).get("operator_table", [])
        if row.get("target") == target
    ]
    stages: list[dict[str, Any]] = []
    for operator_row in operator_rows:
        stage = operator_row["stage"]
        status = operator_row["surface_status"]
        row: dict[str, Any] = {
            "stage": stage,
            "declared_surface_status": status,
            "dataset": operator_row["dataset"],
            "source_code": operator_row["source_code"],
            "transformation": operator_row["transformation"],
        }
        if stage == "J1_donor_projection":
            row.update(
                _native_stage_payload(
                    projection["J1"]["values"],
                    projection["J1"]["weights"],
                    projection["J1"]["stable_ids"],
                )
            )
        elif stage == "recipient_raw_draw":
            row.update(_native_stage_payload(sq_values, sq_weights, sq_ids))
        elif stage == "recipient_codec":
            row.update(_native_stage_payload(decoded, sq_weights, sq_ids))
        elif stage == "recipient_structural":
            row.update(_native_stage_payload(structural, sq_weights, sq_ids))
        elif status in {"NO_SURFACE", "PERSISTED_ONLY_AFTER_PRODUCER"}:
            row.update(
                {
                    "status": "NO_SURFACE",
                    "value": "NA",
                    "se": "NA",
                    "evidence": (
                        "The sealed A16-20 operator table declares no distinct persisted "
                        "surface. A15.21 forbids whole-pipeline replay or guessing."
                    ),
                }
            )
        elif status == "PERSISTED_METADATA":
            row.update(
                {
                    "status": "AVAILABLE_METADATA_ONLY",
                    "pattern_steps": len(bank["metadata"]["pattern_steps"]),
                    "bank_path": str(bank["path"]),
                }
            )
        else:
            row.update(
                {
                    "status": "UNAVAILABLE",
                    "value": "NA",
                    "se": "NA",
                    "evidence": "No deterministic reader is registered for this diagnostic surface.",
                }
            )
        stages.append(row)

    boundary = (np.abs(projection["J1"]["values"]) > 0.0) & (
        np.abs(projection["J1"]["values"]) <= ZERO_ATOL
    )
    boundary_rows = int(boundary.sum())
    boundary_bridge = {
        "id": "B1|J1_donor_projection|boundary_bridge",
        "status": "AVAILABLE",
        "nonadditive": True,
        "boundary_rows": boundary_rows,
        "value": {"positive": 0.0, "negative": 0.0},
        "rule": "same-row exact-sign incidence minus 1e-6 QRF-sign incidence",
    }

    clone_bridge: dict[str, Any] = {"status": "UNAVAILABLE"}
    j0 = projection["J0"]
    j1 = projection["J1"]
    if len(j0["source_ids"]) == len(j1["source_ids"]):
        joined = _stable_join(j1["source_ids"], j0["source_ids"])
        if np.array_equal(j1["source_ids"][joined], j0["source_ids"]):
            clone_bridge = {
                "status": "AVAILABLE",
                "rows": int(len(j0["source_ids"])),
                "source_id_identity": array_identity(j0["source_ids"]),
                "legs": {},
            }
            for leg, sign in LEGS.items():
                j0_level = _weighted_summary(j0["values"], j0["weights"], sign=sign)
                j1_on_j0 = _weighted_summary(
                    j1["values"][joined], j0["weights"], sign=sign
                )
                j1_native = _weighted_summary(j1["values"], j1["weights"], sign=sign)
                clone_bridge["legs"][leg] = {
                    "producer_value_bridge": float(
                        j0_level["value"] - j1_on_j0["value"]
                    ),
                    "clone_weight_bridge": float(
                        j1_on_j0["value"] - j1_native["value"]
                    ),
                    "sum_equals_B1": float(j0_level["value"] - j1_native["value"]),
                }
    seeds = {
        step["pattern"]: int(step["state_after"]["model_config"]["seed"])
        for step in bank["metadata"]["pattern_steps"]
    }
    clone2 = projection["clone2"]
    clone2_payload = (
        _native_stage_payload(clone2["values"], clone2["weights"], clone2["stable_ids"])
        if len(clone2["values"])
        else {"status": "EMPTY", "row_count": 0}
    )
    return {
        "status": "COMPLETE_WITH_NO_SURFACE_ROWS",
        "additive_parent": "B1",
        "stages": stages,
        "pattern_model_seeds": seeds,
        "boundary_bridge": boundary_bridge,
        "clone_value_and_weight_bridge": clone_bridge,
        "clone_2_tail_exclusion": {
            "nonadditive": True,
            **clone2_payload,
        },
    }


def _gq_reading(
    role: dict[str, Any],
    sq: np.ndarray,
    values: np.ndarray,
    weights: np.ndarray,
    j0_levels: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    codes = np.asarray(role["recipient_gq"])[sq]
    labels = {1: "H", 2: "2", 3: "3", 9: "U"}
    output: dict[str, Any] = {"strata": {}, "legs": {}}
    total_weight = weights.sum(dtype=np.float64)
    for code, label in labels.items():
        mask = codes == code
        output["strata"][label] = {
            "row_count": int(mask.sum()),
            "weight_sum": float(weights[mask].sum(dtype=np.float64)),
            "omega": float(weights[mask].sum(dtype=np.float64) / total_weight),
            "legs": {
                leg: _weighted_summary(values[mask], weights[mask], sign=sign)
                for leg, sign in LEGS.items()
            },
        }
    for leg in LEGS:
        housing = output["strata"]["H"]["legs"][leg]
        base = (
            "NA"
            if housing["value"] == "NA"
            else float(j0_levels[leg]["value"] - housing["value"])
        )
        adjustments: dict[str, Any] = {}
        for label in ("2", "3", "U"):
            stratum = output["strata"][label]
            level = stratum["legs"][leg]
            adjustments[label] = (
                "NA"
                if level["value"] == "NA" or housing["value"] == "NA"
                else float(stratum["omega"] * (housing["value"] - level["value"]))
            )
        output["legs"][leg] = {
            "J0_minus_I_H": base,
            "adjustment_TYPEHUGQ_2": adjustments["2"],
            "adjustment_TYPEHUGQ_3": adjustments["3"],
            "adjustment_unprojectable": adjustments["U"],
        }
    return output


def _run_candidate_target(
    data: dict[str, Any],
    aux: dict[str, Any],
    adopted: dict[str, Any],
    c0b_lookup: dict[tuple[str, str], dict[str, Any]],
    target: str,
) -> dict[str, Any]:
    target_spec = data["target_specs"][target]
    role = data["roles"][c4.role_for_target(target_spec)]
    bank = data["current_banks"][target]
    projection = _projection(aux, target, target_spec)
    raw_role = bank["raw"][role["recipient_physical"]]
    scope = np.asarray(role["recipient_clone0"], dtype=bool)
    sq = scope & np.isfinite(raw_role)
    so = scope & ~sq
    scope_weights = np.asarray(role["recipient_weights"], dtype=np.float64)[scope]
    sq_weights = np.asarray(role["recipient_weights"], dtype=np.float64)[sq]
    phi = sq_weights.sum(dtype=np.float64) / scope_weights.sum(dtype=np.float64)
    structural_role, structural_diagnostic = _structural_surface(
        data, aux, target, target_spec
    )
    decoded_role = raw_role.copy()
    terminal_role = _terminal_on_role(aux, role, target, target_spec)
    precal_role = terminal_role.copy()
    precal_role[sq] = structural_role[sq]
    terminal_compare = np.isfinite(raw_role)
    structural_terminal_unequal = terminal_compare & (
        np.asarray(structural_role).view(np.uint64)
        != np.asarray(terminal_role).view(np.uint64)
    )

    receipt = _receipt_for_target(data["d0"], target)
    full_drawn = np.isfinite(bank["raw"])
    p0 = {
        "status": "PASS_A17_SCOPE_RECOVERY",
        "scope_rows": int(scope.sum()),
        "S_q_rows": int(sq.sum()),
        "S_o_rows": int(so.sum()),
        "scope_mask": mask_identity(scope),
        "S_q_mask": mask_identity(sq),
        "S_o_mask": mask_identity(so),
        "phi": float(phi),
        "full_bank_drawn_rows": int(full_drawn.sum()),
        "full_bank_drawn_mask": mask_identity(full_drawn),
        "receipt_authorized_null_rows": int(receipt["authorized_null_rows"]),
        "full_bank_matches_receipt": int(full_drawn.sum())
        == int(receipt["authorized_null_rows"]),
        "path_census": {
            "authorized": int(scope.sum()),
            "null_before": int(scope.sum()),
            "drawn": int(sq.sum()),
            "finite_decode": int(sq.sum()),
            "first_failure_authorized": 0,
            "first_failure_null_before": 0,
            "first_failure_drawn": int(so.sum()),
            "first_failure_finite_decode": 0,
        },
        "receipt": receipt,
    }
    if not p0["full_bank_matches_receipt"] or not np.array_equal(sq, scope):
        raise ValueError(f"A17/P0 mask recovery failed for {target}")

    pattern_results, contexts = _pattern_readings(data, target, c0b_lookup)
    j0_levels = {
        leg: _weighted_summary(
            projection["J0"]["values"], projection["J0"]["weights"], sign=sign
        )
        for leg, sign in LEGS.items()
    }
    j1_levels = {
        leg: _weighted_summary(
            projection["J1"]["values"], projection["J1"]["weights"], sign=sign
        )
        for leg, sign in LEGS.items()
    }
    levels_by_leg: dict[str, Any] = {}
    ledger_by_leg: dict[str, Any] = {}
    for leg, sign in LEGS.items():
        j2 = _combined_level(
            [(row["alpha"], row["legs"][leg]["m_observed"]) for row in pattern_results]
        )
        p_d = _combined_level(
            [(row["alpha"], row["legs"][leg]["P_D"]) for row in pattern_results]
        )
        p_r = _combined_level(
            [(row["alpha"], row["legs"][leg]["P_R"]) for row in pattern_results]
        )
        i_raw = _weighted_summary(raw_role[sq], sq_weights, sign=sign)
        i_dec = _weighted_summary(decoded_role[sq], sq_weights, sign=sign)
        i_q = _weighted_summary(structural_role[sq], sq_weights, sign=sign)
        i_acs = _weighted_summary(precal_role[scope], scope_weights, sign=sign)
        i_o = _weighted_summary(
            precal_role[so], role["recipient_weights"][so], sign=sign
        )
        d_level = _difference(j0_levels[leg], i_acs)
        levels = {
            "J0": j0_levels[leg],
            "J1": j1_levels[leg],
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
        levels_by_leg[leg] = levels
        rows = {
            "L0": {
                "value": 0.0,
                "se": 0.0,
                "variance": 0.0,
                "empty_set": True,
            },
            "B1": _difference(j0_levels[leg], j1_levels[leg], scale=phi),
            "B2": _difference(j1_levels[leg], j2, scale=phi),
            "T1": _difference(j2, p_d, scale=phi),
            "T2": _difference(p_d, p_r, scale=phi),
            "T3": {
                "value": float(phi * (p_r["value"] - i_raw["value"])),
                "variance": float(
                    phi
                    * phi
                    * math.fsum(
                        row["legs"][leg]["e2_conditional_variance_contribution"]
                        for row in pattern_results
                    )
                ),
            },
            "T4": _difference(i_raw, i_dec, scale=phi),
            "T5": _difference(i_dec, i_q, scale=phi),
        }
        rows["T3"]["se"] = float(math.sqrt(max(rows["T3"]["variance"], 0.0)))
        ordered = ("L0", "B1", "B2", "T1", "T2", "T3", "T4", "T5")
        residual = float(d_level["value"])
        for name in ordered:
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
            raise ValueError(f"ledger closure failed for {target}/{leg}: {residual}")
        ledger_by_leg[leg] = {
            "support": _support(data["d0"], target, leg),
            "rows": rows,
        }

    b2 = {
        "status": "COMPLETE",
        "fixed_order": [
            "role_channel",
            "family_complete_case",
            "pattern_predictor_complete_case",
            "weight_basis",
            "pattern_standardization",
        ],
        "order_dependence_disclosed": True,
        "patterns": [
            {
                "pattern": row["pattern"],
                "alpha": row["alpha"],
                "donor_projection_rows": int(len(contexts[row["pattern"]]["donor_y"])),
                "family_complete_case_rows": int(
                    len(contexts[row["pattern"]]["donor_y"])
                ),
                "predictor_complete_case_rows": int(
                    len(contexts[row["pattern"]]["donor_y"])
                ),
                "fit_weight_identity": array_identity(
                    contexts[row["pattern"]]["donor_weights"]
                ),
                "collapsed": False,
            }
            for row in pattern_results
        ],
        "legs": {
            leg: {
                "role_channel_to_family_complete_case": 0.0,
                "family_to_predictor_complete_case": 0.0,
                "predictor_to_weight_basis": 0.0,
                "weight_basis_to_pattern_standardization": float(
                    j1_levels[leg]["value"] - levels_by_leg[leg]["J2"]["value"]
                ),
                "sum_equals_B2": float(ledger_by_leg[leg]["rows"]["B2"]["value"] / phi),
            }
            for leg in LEGS
        },
    }
    p6 = _producer_ledger(
        adopted,
        target,
        projection,
        bank,
        raw_role[sq],
        sq_weights,
        role["recipient_stable_id"][sq],
        decoded_role[sq],
        structural_role[sq],
    )
    p7 = _gq_reading(
        role,
        sq,
        structural_role[sq],
        sq_weights,
        j0_levels,
    )
    return {
        "status": "COMPLETE",
        "target": target,
        "entity": target_spec["entity"],
        "stage": target_spec["stage"],
        "P0": p0,
        "P1": {
            "levels": levels_by_leg,
            "ledger": ledger_by_leg,
            "pattern_rows": pattern_results,
            "structural": {
                **structural_diagnostic,
                "terminal_unequal_rows": int(structural_terminal_unequal.sum()),
                "terminal_unequal_mask": mask_identity(structural_terminal_unequal),
                "terminal_comparison_is_diagnostic": True,
            },
            "codec": {
                "kind": "identity_numeric",
                "bitwise_equal": True,
            },
            "B2_diagnostics": b2,
        },
        "P6": p6,
        "P7": p7,
        "source": {
            "bank": str(bank["path"]),
            "bank_raw_sha256": bank["metadata"]["raw_draw_sha256"],
            "checkpoint": str(data["transferred_path"]),
            "checkpoint_sha256": c4.EXPECTED_CHECKPOINT_DIGESTS[
                "transferred.checkpoint.h5"
            ],
            "D0": str(D0_JSON),
            "D0_sha256": c4.EXPECTED_AUTHORITY_DIGESTS[str(D0_JSON)],
        },
    }


def _baseline_person_basic(
    d0: dict[str, Any],
    target: str,
    bank_path: Path,
    stage_root: Path,
) -> dict[str, Any]:
    assembled = replay.SelectedCheckpoint(stage_root / "assembled.checkpoint.h5")
    assembled_channel = _text(assembled.column("person", "person_support_channel"))
    assembled_clone = np.asarray(
        assembled.column("person", "person_support_clone_index"), dtype=np.int64
    )
    assembled_hh = assembled.column("person", "person_household_id")
    assembled_hh_ids = assembled.column("household", "household_id")
    assembled_weights = replay.broadcast_by_id(
        assembled_hh_ids, assembled.household_weights(), assembled_hh
    )
    assembled.close()
    bank = replay.load_bank(bank_path, {})
    scope = (assembled_channel == "acs") & (assembled_clone == 0)
    sq = scope & np.isfinite(bank["raw"])
    raw = bank["raw"][sq]
    raw_weights = assembled_weights[sq]

    transferred = replay.SelectedCheckpoint(stage_root / "transferred.checkpoint.h5")
    channel = _text(transferred.column("person", "person_support_channel"))
    clone = np.asarray(
        transferred.column("person", "person_support_clone_index"), dtype=np.int64
    )
    values = replay.as_float(transferred.column("person", target))
    person_hh = transferred.column("person", "person_household_id")
    hh_ids = transferred.column("household", "household_id")
    weights = replay.broadcast_by_id(hh_ids, transferred.household_weights(), person_hh)
    transferred.close()
    j0_mask = (channel == "asec") & (clone == 0)
    j0 = _weighted_summary(values[j0_mask], weights[j0_mask], sign=1)
    iq = _weighted_summary(raw, raw_weights, sign=1)
    d_level = _difference(j0, iq)
    return _baseline_basic_result(target, bank, scope, sq, j0, iq, d_level)


def _baseline_group_basic(
    d0: dict[str, Any],
    target: str,
    bank_path: Path,
    stage_root: Path,
) -> dict[str, Any]:
    checkpoint = replay.SelectedCheckpoint(stage_root / "transferred.checkpoint.h5")
    person_hh = checkpoint.column("person", "person_household_id")
    person_spm = checkpoint.column("person", "person_spm_unit_id")
    hh_ids = checkpoint.column("household", "household_id")
    person_weights = replay.broadcast_by_id(
        hh_ids, checkpoint.household_weights(), person_hh
    )
    spm_ids = checkpoint.column("spm_unit", "spm_unit_id")
    weights = replay.group_weights(person_weights, person_spm, spm_ids)
    channel = _text(checkpoint.column("spm_unit", "spm_unit_support_channel"))
    clone = np.asarray(
        checkpoint.column("spm_unit", "spm_unit_support_clone_index"), dtype=np.int64
    )
    values = replay.as_float(checkpoint.column("spm_unit", target))
    checkpoint.close()
    bank = replay.load_bank(bank_path, {})
    scope = (channel == "acs") & (clone == 0)
    sq = scope & np.isfinite(bank["raw"])
    j0_mask = (channel == "asec") & (clone == 0)
    j0 = _weighted_summary(values[j0_mask], weights[j0_mask], sign=1)
    iq = _weighted_summary(bank["raw"][sq], weights[sq], sign=1)
    d_level = _difference(j0, iq)
    return _baseline_basic_result(target, bank, scope, sq, j0, iq, d_level)


def _baseline_basic_result(
    target: str,
    bank: dict[str, Any],
    scope: np.ndarray,
    sq: np.ndarray,
    j0: dict[str, Any],
    iq: dict[str, Any],
    d_level: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "PARTIAL_DECLARED_CROSS_RUNG_PRIORITY",
        "target": target,
        "leg": "positive",
        "P0": {
            "scope_rows": int(scope.sum()),
            "S_q_rows": int(sq.sum()),
            "phi": float(sq.sum() / scope.sum()),
            "scope_mask": mask_identity(scope),
            "S_q_mask": mask_identity(sq),
        },
        "levels": {
            "J0": j0,
            "I_raw": iq,
            "I_dec": iq,
            "I_q": iq,
            "I_acs": iq,
            "D": d_level,
            "J1": {"value": "NA", "se": "NA", "status": "NOT_RUN_PRIORITY_RULE"},
            "J2": {"value": "NA", "se": "NA", "status": "NOT_RUN_PRIORITY_RULE"},
            "P_D": {"value": "NA", "se": "NA", "status": "NOT_RUN_PRIORITY_RULE"},
            "P_R": {"value": "NA", "se": "NA", "status": "NOT_RUN_PRIORITY_RULE"},
        },
        "ledger": {
            "L0": {"value": 0.0, "se": 0.0},
            "B1": {"value": "NA", "se": "NA", "status": "NOT_RUN_PRIORITY_RULE"},
            "B2": {"value": "NA", "se": "NA", "status": "NOT_RUN_PRIORITY_RULE"},
            "T1": {"value": "NA", "se": "NA", "status": "NOT_RUN_PRIORITY_RULE"},
            "T2": {"value": "NA", "se": "NA", "status": "NOT_RUN_PRIORITY_RULE"},
            "T3": {"value": "NA", "se": "NA", "status": "NOT_RUN_PRIORITY_RULE"},
            "T4": {"value": 0.0, "se": float(math.sqrt(2.0) * iq["se"])},
            "T5": {"value": 0.0, "se": float(math.sqrt(2.0) * iq["se"])},
            "residual": {"value": "NA", "se": "NA", "status": "NOT_RUN_PRIORITY_RULE"},
        },
        "raw_draw_sha256": bank["metadata"]["raw_draw_sha256"],
        "note": (
            "The frozen cross-rung matrix requests D and top-level rows. Under the "
            "wall-clock priority rule this executor binds D/J0/Iq/raw/T5 now and "
            "marks gate-dependent rows explicitly NOT_RUN."
        ),
    }


def _run_baseline(d0: dict[str, Any]) -> dict[str, Any]:
    artifact = d0["D0-0"]["artifacts"]["baseline1pct"]
    stage_root = Path(artifact["checkpoint_directories"]["stage_root"]["path"])
    banks = {
        row["target"]: Path(row["path"]) for row in artifact["bank_target_checkpoints"]
    }
    return {
        "self_employment_income_last_year": _baseline_person_basic(
            d0,
            "self_employment_income_last_year",
            banks["self_employment_income_last_year"],
            stage_root,
        ),
        "spm_unit_energy_subsidy": _baseline_group_basic(
            d0,
            "spm_unit_energy_subsidy",
            banks["spm_unit_energy_subsidy"],
            stage_root,
        ),
    }


def run(
    d0_path: Path,
    adopted_path: Path,
    *,
    include_baseline: bool,
) -> dict[str, Any]:
    started = time.time()
    d0 = json.loads(d0_path.read_text())
    adopted = json.loads(adopted_path.read_text())
    if sha256_file(d0_path) != c4.EXPECTED_AUTHORITY_DIGESTS[str(D0_JSON)]:
        raise ValueError("D0 digest mismatch")
    lookup = _c0b_lookup(adopted)
    data = c4.load_analysis_data(d0)
    aux = _load_candidate_aux(data)
    targets: dict[str, Any] = {}
    for target in TARGETS:
        target_started = time.time()
        targets[target] = _run_candidate_target(data, aux, adopted, lookup, target)
        targets[target]["elapsed_seconds"] = time.time() - target_started
    baseline = (
        _run_baseline(d0)
        if include_baseline
        else {
            target: {"status": "NOT_RUN_COMMAND_OPTION"}
            for target in CROSS_RUNG_TARGETS
        }
    )
    output = {
        "artifact_kind": "qrf_drift_phase0_p0_p1_p6_p7",
        "schema_version": 1,
        "status": "COMPLETE" if include_baseline else "COMPLETE_CANDIDATE_ONLY",
        "authority": {
            "D0": {"path": str(d0_path), "sha256": sha256_file(d0_path)},
            "design": {
                "path": str(c4.DESIGN_MD),
                "sha256": sha256_file(c4.DESIGN_MD),
            },
            "A16_binding": {
                "path": str(c4.A16_BINDING),
                "sha256": sha256_file(c4.A16_BINDING),
            },
            "adopted_C0b_report": {
                "path": str(adopted_path),
                "C0b_full_evidence_sha256": c4.EXPECTED_C0B_SHA256,
                "patterns": len(lookup),
            },
        },
        "candidate-25": {"targets": targets},
        "baseline1pct": {"targets": baseline},
        "execution": {
            "elapsed_seconds": time.time() - started,
            "peak_rss_mb": peak_rss_mb(),
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "checkpoint_columns": aux["loaded_columns"],
        },
    }
    output["content_sha256"] = hashlib.sha256(
        canonical_json(output).encode("utf-8")
    ).hexdigest()
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d0", type=Path, default=D0_JSON)
    parser.add_argument("--adopted-report", type=Path, default=ADOPTED_REPORT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Run the complete candidate reading but omit the diagnostic 1%% rung.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run(
        args.d0.resolve(),
        args.adopted_report.resolve(),
        include_baseline=not args.skip_baseline,
    )
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(
        canonical_json(
            {
                "status": result["status"],
                "out": str(args.out),
                "sha256": sha256_file(args.out),
                "content_sha256": result["content_sha256"],
                "elapsed_seconds": result["execution"]["elapsed_seconds"],
                "peak_rss_mb": result["execution"]["peak_rss_mb"],
            }
        )
    )


if __name__ == "__main__":
    main()
