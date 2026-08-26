#!/usr/bin/env python3
"""Run the A16 paired C2/C3 attribution controls.

The six rostered recoveries are the full A14 route: Shapley on transformed
synthetic-recipient fit rows minus Shapley on the independent R0 null, with the
same donor substitutions.  A separate same-i,j paired-delta route audits the
A16-12 oracle semantics but does not add control-family cells.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import qrf_drift_phase0_c4 as c4
import qrf_drift_phase0_replay as replay
import sklearn

TARGET = "child_support_received"
PATTERN = "pattern_03_76a0101a"
POSITIVE_CLASS = 1
CONTROLS = ("C2", "C3")
GROUPS = ("G1", "G2", "G3")
C2_COLUMN = "__acs_transfer_employment_income"
C3_COLUMN = "child_support_expense"
TARGET_GROUP = {"C2": "G2", "C3": "G3"}
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_a17_c2c3.json")
DEFAULT_PARTIAL = Path("/private/tmp/qrf_phase0_a17_c2c3.partial.json")
INITIAL_REPLICATES = 250
ESCALATED_REPLICATES = 1_000
EXPECTED_C3_CARRIERS = 397


def rows_label(control: str, replicate: int, gq: str) -> str:
    return (
        f"qrf-drift-v2.3|{control}|rows|{TARGET}|{replicate}|{PATTERN}|{gq}"
    )


def donor_label(control: str, replicate: int) -> str:
    return f"qrf-drift-v2.3|{control}|donor|{TARGET}|{PATTERN}|{replicate}"


def r0_label(control: str, replicate: int) -> str:
    return f"qrf-drift-v2.3|{control}|r0|{TARGET}|{PATTERN}|{replicate}"


def statistic_id(control: str, group: str) -> str:
    return (
        f"r=control|t={TARGET}|p=_|l=_|row={control}_oracle_error|g={group}|"
        "prior=_|gq=_|d=_|rep=_|fold=_|v=final"
    )


def used_feature_indexes(gate: Any) -> tuple[int, ...]:
    used: set[int] = set()
    for iteration in gate._predictors:
        for predictor in iteration:
            nodes = predictor.nodes
            used.update(
                int(value)
                for value in nodes["feature_idx"][nodes["is_leaf"] == 0]
            )
    return tuple(sorted(used))


def split_feature_counts(gate: Any) -> dict[int, int]:
    counts: dict[int, int] = {}
    for iteration in gate._predictors:
        for predictor in iteration:
            nodes = predictor.nodes
            for value in nodes["feature_idx"][nodes["is_leaf"] == 0]:
                index = int(value)
                counts[index] = counts.get(index, 0) + 1
    return counts


def predict_proba_binned(context: dict[str, Any], values: np.ndarray) -> np.ndarray:
    """Predict directly on frozen HGB bins without a lossy raw representative."""
    gate = context["gate"]
    binned = np.ascontiguousarray(values)
    raw = np.zeros(
        (len(binned), gate.n_trees_per_iteration_),
        dtype=gate._baseline_prediction.dtype,
        order="F",
    )
    raw += gate._baseline_prediction
    gate._predict_iterations(binned, gate._predictors, raw, True, 1)
    return np.asarray(gate._loss.predict_proba(raw), dtype=np.float64)


def positive_position(context: dict[str, Any]) -> int:
    positions = np.flatnonzero(context["gate_classes"] == POSITIVE_CLASS)
    if len(positions) != 1:
        raise ValueError(f"positive gate class absent or duplicated: {positions}")
    return int(positions[0])


def transform_inputs(
    context: dict[str, Any],
    control: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    transformed = context["donor_x"].copy()
    if control == "C2":
        position = context["columns"].index(C2_COLUMN)
        observed_max = float(np.max(transformed[:, position]))
        before = transformed[:, position].copy()
        transformed[:, position] = np.minimum(before * 1.25, observed_max)
        changed = transformed[:, position] != before
        evidence = {
            "column": C2_COLUMN,
            "column_position": position,
            "operation": "min(1.25*x, observed pattern fit-row max)",
            "observed_max": observed_max,
            "changed_raw_rows": int(changed.sum()),
            "raw_before_identity": c4.array_identity(before),
            "raw_after_identity": c4.array_identity(transformed[:, position]),
        }
    elif control == "C3":
        position = context["columns"].index(C3_COLUMN)
        before = transformed[:, position].copy()
        carriers = before > 0.0
        transformed[carriers, position] = 0.0
        if int(carriers.sum()) != EXPECTED_C3_CARRIERS:
            raise ValueError(
                f"C3 observed carrier count {int(carriers.sum())} != "
                f"{EXPECTED_C3_CARRIERS}"
            )
        evidence = {
            "column": C3_COLUMN,
            "column_position": position,
            "operation": "observed fit-row carriers x>0 set to zero",
            "observed_carriers": int(carriers.sum()),
            "expected_carriers": EXPECTED_C3_CARRIERS,
            "carrier_mask_identity": c4.array_identity(carriers.astype(np.uint8)),
            "raw_before_identity": c4.array_identity(before),
            "raw_after_identity": c4.array_identity(transformed[:, position]),
        }
    else:
        raise ValueError(f"unknown control {control}")
    return transformed, evidence


def shapley_from_coalitions(coalitions: np.ndarray) -> np.ndarray:
    """Exact three-player Shapley in G1/G2/G3 order."""
    values = np.asarray(coalitions, dtype=np.float64)
    result = np.zeros(3, dtype=np.float64)
    for group_position, group in enumerate(GROUPS):
        bit = c4.GROUP_BITS[group]
        other_bits = [value for value in (1, 2, 4) if value != bit]
        for subset in range(8):
            if subset & bit or subset & ~sum(other_bits):
                continue
            size = int(bool(subset & other_bits[0])) + int(
                bool(subset & other_bits[1])
            )
            weight = 1.0 / 3.0 if size in {0, 2} else 1.0 / 6.0
            result[group_position] += weight * (
                values[subset | bit] - values[subset]
            )
    return result


def _aggregate_signatures(
    signature: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    unique, inverse = np.unique(signature, axis=0, return_inverse=True)
    masses = np.bincount(inverse, weights=weights, minlength=len(unique)).astype(
        np.float64,
        copy=False,
    )
    counts = np.bincount(inverse, minlength=len(unique)).astype(
        np.int64,
        copy=False,
    )
    return unique, masses, counts


def exact_c2_g1_delta(
    context: dict[str, Any],
    base_bins: np.ndarray,
    transformed_bins: np.ndarray,
    *,
    chunk_pairs: int,
) -> tuple[float, dict[str, Any]]:
    """Compute b=Delta({G1}) by exact compressed weighted Cartesian product."""
    used = set(used_feature_indexes(context["gate"]))
    g1 = np.asarray(
        [index for index in context["group_indexes"]["G1"] if index in used],
        dtype=np.int64,
    )
    g2 = np.asarray(
        [index for index in context["group_indexes"]["G2"] if index in used],
        dtype=np.int64,
    )
    g3 = [index for index in context["group_indexes"]["G3"] if index in used]
    if g3:
        raise ValueError(f"G3 unexpectedly used by the frozen gate: {g3}")
    intervention_index = context["columns"].index(C2_COLUMN)
    changed = base_bins[:, intervention_index] != transformed_bins[:, intervention_index]
    if not changed.any():
        return 0.0, {
            "changed_bin_rows": 0,
            "proof": "no transformed row crossed a frozen gate bin",
        }

    weights = context["donor_weights"]
    i_signature = np.column_stack(
        (base_bins[changed][:, g2], transformed_bins[changed][:, g2])
    )
    i_unique, i_mass, i_counts = _aggregate_signatures(
        i_signature,
        weights[changed],
    )
    j_unique, j_mass, j_counts = _aggregate_signatures(
        base_bins[:, g1],
        weights,
    )
    g2_count = len(g2)
    positive = positive_position(context)
    total_weight = float(weights.sum(dtype=np.float64))
    chunk_i = max(1, chunk_pairs // len(j_unique))
    contributions: list[float] = []
    pairs_evaluated = 0
    template = np.zeros((1, base_bins.shape[1]), dtype=base_bins.dtype)

    for start in range(0, len(i_unique), chunk_i):
        stop = min(len(i_unique), start + chunk_i)
        i_block = i_unique[start:stop]
        block_size = len(i_block)
        pair_count = block_size * len(j_unique)
        original = np.repeat(template, pair_count, axis=0)
        transformed = original.copy()
        tiled_g1 = np.tile(j_unique, (block_size, 1))
        repeated_i = np.repeat(i_block, len(j_unique), axis=0)
        original[:, g1] = tiled_g1
        transformed[:, g1] = tiled_g1
        original[:, g2] = repeated_i[:, :g2_count]
        transformed[:, g2] = repeated_i[:, g2_count:]
        combined = np.concatenate((transformed, original), axis=0)
        probabilities = predict_proba_binned(context, combined)[:, positive]
        differences = probabilities[:pair_count] - probabilities[pair_count:]
        pair_weights = np.multiply.outer(i_mass[start:stop], j_mass).reshape(-1)
        contributions.append(float(np.dot(pair_weights, differences)))
        pairs_evaluated += pair_count

    numerator = math.fsum(contributions)
    value = numerator / (total_weight * total_weight)
    return value, {
        "changed_bin_rows": int(changed.sum()),
        "unchanged_bin_rows_omitted_as_exact_zero": int((~changed).sum()),
        "G1_used_feature_indexes": [int(value) for value in g1],
        "G2_used_feature_indexes": [int(value) for value in g2],
        "G1_unique_bin_tuples": len(j_unique),
        "changed_G2_original_transformed_unique_tuples": len(i_unique),
        "weighted_cartesian_pairs_evaluated": pairs_evaluated,
        "chunk_pair_limit": chunk_pairs,
        "i_tuple_counts_identity": c4.array_identity(i_counts),
        "j_tuple_counts_identity": c4.array_identity(j_counts),
        "i_tuple_masses_identity": c4.array_identity(i_mass),
        "j_tuple_masses_identity": c4.array_identity(j_mass),
        "numerator": numerator,
        "denominator": total_weight * total_weight,
    }


def compute_exact_oracles(
    context: dict[str, Any],
    transformed: dict[str, np.ndarray],
    *,
    chunk_pairs: int,
) -> dict[str, Any]:
    gate = context["gate"]
    base = context["donor_x"]
    base_bins = np.ascontiguousarray(gate._bin_mapper.transform(base))
    used = used_feature_indexes(gate)
    split_counts = split_feature_counts(gate)
    used_names = [context["columns"][index] for index in used]
    private_probabilities = predict_proba_binned(context, base_bins)
    if not np.array_equal(private_probabilities, context["donor_probabilities"]):
        raise ValueError("private binned prediction is not bit-identical to C0b gate")
    positive = positive_position(context)
    weights = context["donor_weights"]
    weight_sum = float(weights.sum(dtype=np.float64))
    result: dict[str, Any] = {
        "gate_used_feature_indexes": list(used),
        "gate_used_feature_names": used_names,
        "gate_split_counts_by_feature": {
            context["columns"][index]: count
            for index, count in sorted(split_counts.items())
        },
        "gate_split_count_G3": sum(
            split_counts.get(int(index), 0)
            for index in context["group_indexes"]["G3"]
        ),
        "base_bins_identity": c4.array_identity(base_bins),
        "private_binned_prediction_identity": c4.array_identity(
            private_probabilities
        ),
        "private_prediction_bit_identical_to_adopted_C0b": True,
        "controls": {},
    }
    if result["gate_split_count_G3"] != 0:
        raise ValueError("frozen gate unexpectedly splits on G3")

    for control in CONTROLS:
        tx = transformed[control]
        tx_bins = np.ascontiguousarray(gate._bin_mapper.transform(tx))
        tx_probabilities = predict_proba_binned(context, tx_bins)
        direct_difference = tx_probabilities[:, positive] - private_probabilities[:, positive]
        a_value = float(np.dot(weights, direct_difference) / weight_sum)
        if control == "C2":
            b_value, product_audit = exact_c2_g1_delta(
                context,
                base_bins,
                tx_bins,
                chunk_pairs=chunk_pairs,
            )
            coalitions = np.asarray(
                [a_value, b_value, 0.0, 0.0, a_value, b_value, 0.0, 0.0],
                dtype=np.float64,
            )
            proof = (
                "G3 is unused, so masks differing only by G3 coincide; masks "
                "containing G2 overwrite the intervened feature and have Delta=0"
            )
        else:
            if not np.array_equal(tx_probabilities, private_probabilities):
                raise ValueError("C3 changed a frozen-gate probability")
            if np.any(direct_difference != 0.0):
                raise ValueError("C3 direct probability difference is not exact zero")
            b_value = 0.0
            coalitions = np.zeros(8, dtype=np.float64)
            product_audit = {
                "weighted_cartesian_pairs_evaluated": 0,
                "proof": (
                    "the only transformed column has zero splits in every frozen "
                    "gate tree; all hybrid probabilities are unchanged"
                ),
            }
            proof = product_audit["proof"]
        oracle = shapley_from_coalitions(coalitions)
        result["controls"][control] = {
            "Delta_empty_a": a_value,
            "Delta_G1_b": b_value,
            "coalition_mask_order_0_to_7": coalitions.tolist(),
            "coalition_identity": c4.array_identity(coalitions),
            "oracle_group_order_G1_G2_G3": oracle.tolist(),
            "oracle_identity": c4.array_identity(oracle),
            "target_group": TARGET_GROUP[control],
            "target_group_oracle": float(oracle[GROUPS.index(TARGET_GROUP[control])]),
            "direct_difference_nonzero_rows": int(
                np.count_nonzero(direct_difference)
            ),
            "direct_difference_identity": c4.array_identity(direct_difference),
            "transformed_bins_identity": c4.array_identity(tx_bins),
            "derivation": proof,
            "product_audit": product_audit,
        }
    return result


def sample_rows(
    control: str,
    replicate: int,
    plan: list[dict[str, Any]],
    probabilities: np.ndarray,
) -> np.ndarray:
    """Concatenate per-GQ fit-row samples in the registered GQ order."""
    pieces = [
        c4.weighted_choice(
            rows_label(control, replicate, item["gq"]),
            probabilities,
            item["allocation"],
        )
        for item in plan
        if item["allocation"] > 0
    ]
    if not pieces:
        raise ValueError("C2/C3 rows plan is empty")
    return np.concatenate(pieces)


def _hybrid_block(
    context: dict[str, Any],
    base: np.ndarray,
    donor: np.ndarray,
    mask: int,
) -> np.ndarray:
    result = base.copy()
    for group in GROUPS:
        if mask & c4.GROUP_BITS[group]:
            indexes = context["group_indexes"][group]
            if len(indexes):
                result[:, indexes] = donor[:, indexes]
    return result


def evaluate_replicate(
    context: dict[str, Any],
    transformed: np.ndarray,
    row_index: np.ndarray,
    donor_index: np.ndarray,
    r0_index: np.ndarray,
) -> dict[str, np.ndarray]:
    """Evaluate full-route and same-i,j paired Shapley for one replicate."""
    base = context["donor_x"]
    donor = base[donor_index]
    path_bases = {
        "real": transformed[row_index],
        "null": base[r0_index],
        "paired_base": base[row_index],
    }
    positive = positive_position(context)
    known_empty = {
        "null": float(context["donor_probabilities"][r0_index, positive].mean()),
        "paired_base": float(
            context["donor_probabilities"][row_index, positive].mean()
        ),
    }
    known_all = float(
        context["donor_probabilities"][donor_index, positive].mean()
    )

    # The frozen gate has no G3 splits.  Evaluate masks 0..3 and duplicate the
    # G3 variants exactly; real empty is transformed and therefore predicted.
    specs = [
        ("real", 0),
        ("real", 1),
        ("real", 2),
        ("null", 1),
        ("null", 2),
        ("paired_base", 1),
        ("paired_base", 2),
    ]
    blocks = [
        _hybrid_block(context, path_bases[path], donor, mask)
        for path, mask in specs
    ]
    probabilities = context["gate"].predict_proba(np.concatenate(blocks))[
        :, positive
    ].reshape(len(specs), len(row_index))
    predicted_means = {
        spec: float(probabilities[position].mean())
        for position, spec in enumerate(specs)
    }
    coalitions: dict[str, np.ndarray] = {}
    for path in path_bases:
        values = np.empty(8, dtype=np.float64)
        values[0] = (
            predicted_means[(path, 0)] if path == "real" else known_empty[path]
        )
        values[1] = predicted_means[(path, 1)]
        values[2] = predicted_means[(path, 2)]
        values[3] = known_all
        for mask in range(4, 8):
            values[mask] = values[mask & 3]
        coalitions[path] = values
    shapley = {
        path: shapley_from_coalitions(values) for path, values in coalitions.items()
    }
    return {
        "real_coalitions": coalitions["real"],
        "null_coalitions": coalitions["null"],
        "paired_base_coalitions": coalitions["paired_base"],
        "real_shapley": shapley["real"],
        "null_shapley": shapley["null"],
        "paired_base_shapley": shapley["paired_base"],
        "recovered": shapley["real"] - shapley["null"],
        "paired_delta": shapley["real"] - shapley["paired_base"],
    }


def run_replicate_range(
    context: dict[str, Any],
    transformed: np.ndarray,
    control: str,
    plan: list[dict[str, Any]],
    start: int,
    stop: int,
) -> dict[str, Any]:
    count = stop - start
    arrays = {
        name: np.empty((count, 3), dtype=np.float64)
        for name in (
            "real_shapley",
            "null_shapley",
            "paired_base_shapley",
            "recovered",
            "paired_delta",
        )
    }
    arrays.update(
        {
            name: np.empty((count, 8), dtype=np.float64)
            for name in (
                "real_coalitions",
                "null_coalitions",
                "paired_base_coalitions",
            )
        }
    )
    probabilities = context["donor_choice_probabilities"]
    sample_size = sum(item["allocation"] for item in plan)
    first_indexes: dict[str, Any] | None = None
    last_indexes: dict[str, Any] | None = None
    for offset, replicate in enumerate(range(start, stop)):
        rows = sample_rows(control, replicate, plan, probabilities)
        donor = c4.weighted_choice(
            donor_label(control, replicate),
            probabilities,
            sample_size,
        )
        r0 = c4.weighted_choice(
            r0_label(control, replicate),
            probabilities,
            sample_size,
        )
        values = evaluate_replicate(context, transformed, rows, donor, r0)
        for name, array in arrays.items():
            array[offset] = values[name]
        identities = {
            "replicate": replicate,
            "rows": c4.array_identity(rows),
            "donor": c4.array_identity(donor),
            "r0": c4.array_identity(r0),
        }
        if offset == 0:
            first_indexes = identities
        if offset == count - 1:
            last_indexes = identities
        if (offset + 1) % 25 == 0:
            print(
                f"{control} replicate {replicate + 1}/{stop}",
                flush=True,
            )
    arrays["index_identities"] = {
        "first": first_indexes,
        "last": last_indexes,
    }
    return arrays


def concatenate_ranges(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, Any]:
    result = {
        name: np.concatenate((first[name], second[name]), axis=0)
        for name in (
            "real_shapley",
            "null_shapley",
            "paired_base_shapley",
            "recovered",
            "paired_delta",
            "real_coalitions",
            "null_coalitions",
            "paired_base_coalitions",
        )
    }
    result["index_identities"] = {
        "first": first["index_identities"]["first"],
        "last": second["index_identities"]["last"],
    }
    return result


def error_summary(values: np.ndarray, oracle: float) -> dict[str, Any]:
    vector = np.asarray(values, dtype=np.float64)
    estimate = float(vector.mean())
    error = estimate - oracle
    sd = float(vector.std(ddof=1)) if len(vector) > 1 else 0.0
    mcse = sd / math.sqrt(len(vector))
    if mcse > 0.0:
        ratio: float | str = abs(error) / mcse
        passed = abs(error) <= c4.Z_STAR * mcse
        trigger = 2.0 <= ratio <= 4.0
    elif error == 0.0:
        ratio = 0.0
        passed = True
        trigger = False
    else:
        ratio = "inf"
        passed = False
        trigger = False
    return {
        "estimate": estimate,
        "oracle": oracle,
        "value": error,
        "replicate_sd": sd,
        "mcse": mcse,
        "abs_error_over_mcse": ratio,
        "absolute_threshold": c4.Z_STAR * mcse,
        "pass": bool(passed),
        "escalation_trigger_at_this_R": bool(trigger),
        "replicates": len(vector),
    }


def control_statistics(
    control: str,
    arrays: dict[str, Any],
    oracle: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for position, group in enumerate(GROUPS):
        vector = arrays["recovered"][:, position]
        summary = error_summary(vector, float(oracle[position]))
        rows.append(
            {
                "id": statistic_id(control, group),
                "control": control,
                "target": TARGET,
                "pattern": PATTERN,
                "group": group,
                "target_group": group == TARGET_GROUP[control],
                "family": "C2_C3_group_errors",
                "gated": True,
                "status": "PASS" if summary["pass"] else "FAIL",
                **summary,
                "replicate_values": [float(value) for value in vector],
                "replicate_values_identity": c4.array_identity(vector),
                "source": {
                    "design": str(c4.DESIGN_MD),
                    "design_sha256": c4.EXPECTED_AUTHORITY_DIGESTS[
                        str(c4.DESIGN_MD)
                    ],
                    "d0_sha256": c4.EXPECTED_AUTHORITY_DIGESTS[str(c4.D0_JSON)],
                    "adopted_c0b_sha256": c4.EXPECTED_C0B_SHA256,
                    "binding": "A16 findings 12-14",
                    "exact_oracle_pointer": (
                        f"/exact_oracles/controls/{control}/"
                        "oracle_group_order_G1_G2_G3"
                    ),
                },
            }
        )
    return rows


def array_payload(values: np.ndarray) -> dict[str, Any]:
    return {
        "values": np.asarray(values, dtype=np.float64).tolist(),
        "identity": c4.array_identity(values),
    }


def paired_audit_rows(
    arrays: dict[str, Any],
    oracle: np.ndarray,
) -> list[dict[str, Any]]:
    return [
        {
            "group": group,
            "rostered": False,
            **error_summary(arrays["paired_delta"][:, position], float(oracle[position])),
            "replicate_values_identity": c4.array_identity(
                arrays["paired_delta"][:, position]
            ),
        }
        for position, group in enumerate(GROUPS)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c0b-json", type=Path, default=c4.DEFAULT_C0B)
    parser.add_argument(
        "--c4-json",
        type=Path,
        default=Path("/private/tmp/qrf_phase0_a17_c4.json"),
    )
    parser.add_argument(
        "--skip-c4-prerequisite",
        action="store_true",
        help="smoke only; allowed only with --replicates",
    )
    parser.add_argument(
        "--replicates",
        type=int,
        help="fixed non-authoritative smoke count; default is adaptive 250/1000",
    )
    parser.add_argument(
        "--chunk-pairs",
        type=int,
        default=2_000_000,
        help="maximum b-oracle Cartesian rows per prediction chunk",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--partial", type=Path, default=DEFAULT_PARTIAL)
    args = parser.parse_args()
    if args.replicates is not None and args.replicates < 2:
        parser.error("--replicates must be at least 2")
    if args.chunk_pairs < 1:
        parser.error("--chunk-pairs must be positive")
    if args.skip_c4_prerequisite and args.replicates is None:
        parser.error("--skip-c4-prerequisite requires fixed --replicates")
    return args


def _base_result(
    *,
    input_verification: dict[str, Any],
    c0b_path: Path,
    c4_prerequisite: dict[str, Any],
    allocation: dict[str, Any],
    plan: list[dict[str, Any]],
    context: dict[str, Any],
    transformation_evidence: dict[str, Any],
    fixed_replicates: int | None,
) -> dict[str, Any]:
    return {
        "artifact_kind": "qrf_drift_phase0_a17_c2c3",
        "schema_version": 1,
        "status": "RUNNING",
        "authority": {
            "design": {
                "path": str(c4.DESIGN_MD),
                "sha256": c4.EXPECTED_AUTHORITY_DIGESTS[str(c4.DESIGN_MD)],
                "commit": "1c315579",
            },
            "a16_binding": {
                "path": str(c4.A16_BINDING),
                "sha256": c4.EXPECTED_AUTHORITY_DIGESTS[str(c4.A16_BINDING)],
                "findings": [12, 13, 14],
            },
            "d0": {
                "path": str(c4.D0_JSON),
                "sha256": c4.EXPECTED_AUTHORITY_DIGESTS[str(c4.D0_JSON)],
            },
            "adopted_c0b": {
                "path": str(c0b_path),
                "sha256": c4.EXPECTED_C0B_SHA256,
            },
        },
        "input_verification": input_verification,
        "C4_prerequisite": c4_prerequisite,
        "scope": {
            "target": TARGET,
            "pattern": PATTERN,
            "largest_share_pattern": True,
            "pattern_sample_size": sum(item["allocation"] for item in plan),
            "pattern_allocation": plan,
            "target_allocation": allocation,
            "positive_class": "positive",
            "gate_classes": [int(value) for value in context["gate_classes"]],
        },
        "control_roster": {
            "overall_K": c4.OVERALL_CONTROL_K,
            "C2_C3_group_errors_K": 6,
            "sidak_z": c4.Z_STAR,
            "overall_ordered_ids_sha256": c4.OVERALL_ROSTER_SHA256,
            "ids": [
                statistic_id(control, group)
                for control in CONTROLS
                for group in GROUPS
            ],
        },
        "estimator": {
            "official_recovery": (
                "Shapley(T(rows), donor) - Shapley(r0, donor); the donor "
                "sequence is position-paired across paths"
            ),
            "semantic_audit": (
                "Shapley(T(rows), donor) - Shapley(rows, donor), using "
                "identical i,j draws; descriptive, not an extra K cell"
            ),
            "sampling": (
                "fresh PCG64 per complete literal label; fit-weight PPS with "
                "replacement; unit analysis weights"
            ),
            "exact_oracle": (
                "finite W^-2 weighted i,j expectation on frozen HGB split-bin "
                "signatures, chunked without refit"
            ),
            "replicates_initial": INITIAL_REPLICATES,
            "replicates_escalated": ESCALATED_REPLICATES,
            "fixed_replicate_override": fixed_replicates,
            "escalation": (
                "at R=250, append both controls to R=1000 iff any of six "
                "official abs oracle-error/MCSE ratios is in [2,4]"
            ),
            "pass": "each of six abs(error) <= z*MCSE",
            "power": "abs(target-group oracle) > 5*z*target-group MCSE",
        },
        "gate_context": {
            "gate_seed": context["gate_seed"],
            "state_before_sha256": context["state_before_sha256"],
            "state_before_source": context["state_before_source"],
            "columns": list(context["columns"]),
            "groups": {
                group: list(context["groups"][group]) for group in GROUPS
            },
            "donor_x_identity": c4.array_identity(context["donor_x"]),
            "donor_y_identity": c4.array_identity(context["donor_y"]),
            "donor_weight_identity": replay.weight_identity(
                context["donor_weights"]
            ),
            "donor_probability_identity": c4.array_identity(
                context["donor_probabilities"]
            ),
            "c0b_bindings": context["c0b_bindings"],
        },
        "transformations": transformation_evidence,
        "exact_oracles": {},
        "controls": {},
        "statistics": [],
        "summary": {},
        "execution_diagnostics": {
            "python": sys.version,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "platform": platform.platform(),
            "pid": os.getpid(),
            "started_unix": time.time(),
        },
    }


def _write_partial(path: Path, result: dict[str, Any]) -> None:
    result["execution_diagnostics"]["peak_rss_mb_so_far"] = c4.peak_rss_mb()
    c4.write_canonical_result(path, result)


def control_payload(
    control: str,
    arrays: dict[str, Any],
    oracle: np.ndarray,
    plan: list[dict[str, Any]],
    initial_triggers: list[dict[str, Any]],
    escalated: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    statistics = control_statistics(control, arrays, oracle)
    target_position = GROUPS.index(TARGET_GROUP[control])
    target_row = statistics[target_position]
    power_threshold = 5.0 * c4.Z_STAR * target_row["mcse"]
    power_pass = abs(float(oracle[target_position])) > power_threshold
    group_pass = all(item["pass"] for item in statistics)
    if not group_pass:
        status = "FAIL"
    elif not power_pass:
        status = "UNDERPOWERED"
    else:
        status = "PASS"
    replicate_count = len(arrays["recovered"])
    payload = {
        "control": control,
        "target": TARGET,
        "pattern": PATTERN,
        "target_group": TARGET_GROUP[control],
        "sample_size": sum(item["allocation"] for item in plan),
        "replicates_initial": INITIAL_REPLICATES,
        "replicates_final": replicate_count,
        "escalated": escalated,
        "escalation_triggers_at_250": initial_triggers,
        "streams": {
            "rows": [
                {
                    "gq": item["gq"],
                    "allocation": item["allocation"],
                    "first": rows_label(control, 0, item["gq"]),
                    "last": rows_label(control, replicate_count - 1, item["gq"]),
                }
                for item in plan
                if item["allocation"] > 0
            ],
            "donor_first": donor_label(control, 0),
            "donor_last": donor_label(control, replicate_count - 1),
            "r0_first": r0_label(control, 0),
            "r0_last": r0_label(control, replicate_count - 1),
            "derivation": "first 8 SHA-256 bytes, big-endian uint64, PCG64",
            "index_identities": arrays["index_identities"],
        },
        "oracle_by_group": {
            group: float(oracle[position])
            for position, group in enumerate(GROUPS)
        },
        "replicate_arrays": {
            name: array_payload(arrays[name])
            for name in (
                "recovered",
                "paired_delta",
                "real_shapley",
                "null_shapley",
                "paired_base_shapley",
                "real_coalitions",
                "null_coalitions",
                "paired_base_coalitions",
            )
        },
        "paired_same_i_j_semantic_audit": paired_audit_rows(arrays, oracle),
        "power": {
            "target_group": TARGET_GROUP[control],
            "effect": float(oracle[target_position]),
            "absolute_oracle": abs(float(oracle[target_position])),
            "target_group_mcse": target_row["mcse"],
            "threshold_5_z_mcse": power_threshold,
            "strict_greater_than": True,
            "pass": power_pass,
            "status": "PASS" if power_pass else "UNDERPOWERED",
        },
        "group_recoveries_pass": group_pass,
        "pass": group_pass and power_pass,
        "status": status,
    }
    return payload, statistics


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    for path, expected in c4.EXPECTED_AUTHORITY_DIGESTS.items():
        actual = c4.sha256_file(Path(path))
        if actual != expected:
            raise ValueError(f"authority digest mismatch for {path}: {actual}")
    d0 = json.loads(c4.D0_JSON.read_text())
    input_verification = c4.verify_inputs(d0, args.c0b_json)
    c0b = json.loads(args.c0b_json.read_text())
    if not (
        c0b["status"] == "PASS"
        and c0b["summary"]["e4_bit_identical_pass"]
        and c0b["summary"]["e2_repeated_draw_control_pass"]
    ):
        raise ValueError("adopted C0b artifact is not a clean pass")
    c0b_lookup = {
        (item["target"], item["pattern"]): item for item in c0b["patterns"]
    }

    if args.skip_c4_prerequisite:
        c4_prerequisite = {
            "status": "SKIPPED_NON_AUTHORITATIVE_SMOKE",
            "pass": False,
        }
    else:
        control_artifact = json.loads(args.c4_json.read_text())
        if control_artifact["status"] != "PASS":
            raise ValueError(
                f"C4 prerequisite is not a full PASS: {control_artifact['status']}"
            )
        c4_prerequisite = {
            "path": str(args.c4_json),
            "sha256": c4.sha256_file(args.c4_json),
            "status": control_artifact["status"],
            "pass": True,
        }

    data = c4.load_analysis_data(d0)
    allocation = c4.target_allocation(data, TARGET)
    largest = max(
        data["target_specs"][TARGET]["patterns"],
        key=lambda item: item["clone0_recipient_weighted_share"],
    )
    if largest["name"] != PATTERN:
        raise ValueError(f"bound largest pattern changed: {largest['name']}")
    plan = [
        {
            "gq": item["gq"],
            "row_count": item["row_count"],
            "weight_sum": item["weight_sum"],
            "allocation": item["allocation"],
        }
        for item in allocation["strata"]
        if item["pattern"] == PATTERN and item["weight_sum"] > 0.0
    ]
    context = c4.fit_gate_context(data, TARGET, PATTERN, c0b_lookup)
    transformed: dict[str, np.ndarray] = {}
    transformation_evidence: dict[str, Any] = {}
    for control in CONTROLS:
        transformed[control], transformation_evidence[control] = transform_inputs(
            context,
            control,
        )
    result = _base_result(
        input_verification=input_verification,
        c0b_path=args.c0b_json,
        c4_prerequisite=c4_prerequisite,
        allocation=allocation,
        plan=plan,
        context=context,
        transformation_evidence=transformation_evidence,
        fixed_replicates=args.replicates,
    )
    _write_partial(args.partial, result)

    oracle_started = time.perf_counter()
    exact = compute_exact_oracles(
        context,
        transformed,
        chunk_pairs=args.chunk_pairs,
    )
    exact["elapsed_seconds"] = time.perf_counter() - oracle_started
    result["exact_oracles"] = exact
    print(
        "exact oracles "
        + " ".join(
            f"{control}={exact['controls'][control]['oracle_group_order_G1_G2_G3']}"
            for control in CONTROLS
        )
        + f" seconds={exact['elapsed_seconds']:.1f}",
        flush=True,
    )
    _write_partial(args.partial, result)

    initial_stop = args.replicates or INITIAL_REPLICATES
    arrays = {
        control: run_replicate_range(
            context,
            transformed[control],
            control,
            plan,
            0,
            initial_stop,
        )
        for control in CONTROLS
    }
    oracles = {
        control: np.asarray(
            exact["controls"][control]["oracle_group_order_G1_G2_G3"],
            dtype=np.float64,
        )
        for control in CONTROLS
    }
    initial_statistics = {
        control: control_statistics(control, arrays[control], oracles[control])
        for control in CONTROLS
    }
    triggers = {
        control: [
            {
                "id": item["id"],
                "abs_error_over_mcse": item["abs_error_over_mcse"],
            }
            for item in initial_statistics[control]
            if item["escalation_trigger_at_this_R"]
        ]
        for control in CONTROLS
    }
    escalated = args.replicates is None and any(triggers.values())
    if escalated:
        for control in CONTROLS:
            extension = run_replicate_range(
                context,
                transformed[control],
                control,
                plan,
                INITIAL_REPLICATES,
                ESCALATED_REPLICATES,
            )
            arrays[control] = concatenate_ranges(arrays[control], extension)

    all_statistics: list[dict[str, Any]] = []
    for control in CONTROLS:
        payload, statistics = control_payload(
            control,
            arrays[control],
            oracles[control],
            plan,
            triggers[control],
            escalated,
        )
        result["controls"][control] = payload
        all_statistics.extend(statistics)
    result["statistics"] = all_statistics
    expected_ids = sorted(
        statistic_id(control, group)
        for control in CONTROLS
        for group in GROUPS
    )
    actual_ids = sorted(item["id"] for item in all_statistics)
    if actual_ids != expected_ids or len(actual_ids) != 6:
        raise ValueError("six-cell C2/C3 roster mismatch")

    control_statuses = {
        control: result["controls"][control]["status"] for control in CONTROLS
    }
    if args.replicates is not None:
        status = "NON_AUTHORITATIVE_FIXED_REPLICATE_RUN"
    elif "FAIL" in control_statuses.values():
        status = "FAIL"
    elif "UNDERPOWERED" in control_statuses.values():
        status = "UNDERPOWERED"
    else:
        status = "PASS"
    result["status"] = status
    result["summary"] = {
        "rostered_cells": len(all_statistics),
        "rostered_cells_passed": sum(item["pass"] for item in all_statistics),
        "failed_ids": [item["id"] for item in all_statistics if not item["pass"]],
        "control_statuses": control_statuses,
        "escalated_to_1000": escalated,
        "all_six_recoveries_pass": all(item["pass"] for item in all_statistics),
        "all_power_checks_pass": all(
            result["controls"][control]["power"]["pass"] for control in CONTROLS
        ),
        "terminal_gated_disposition": (
            "PROCEED" if status == "PASS" else "STOP_BEFORE_READINGS"
        ),
    }
    result["execution_diagnostics"].update(
        {
            "finished_unix": time.time(),
            "elapsed_seconds": time.perf_counter() - started,
            "peak_rss_mb": c4.peak_rss_mb(),
        }
    )
    output_sha = c4.write_canonical_result(args.out, result)
    args.partial.unlink(missing_ok=True)
    print(f"RESULT {args.out} sha256={output_sha} status={status}", flush=True)


if __name__ == "__main__":
    main()
