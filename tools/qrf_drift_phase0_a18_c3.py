#!/usr/bin/env python3
"""Run the A18 branch-2, re-targeted C3 control only.

The selected target, pattern, and G3 column come exclusively from the sealed
A18 split-enumeration artifact.  C4 and the already passing C2 control are
verified and adopted by digest; neither is recomputed.  The new C3 follows
the corrected A16-12/13/14 same-i,j paired Shapley route on the reproduced
frozen gate and retains the independent-R0 null route as a descriptive audit.
No Phase-0 reading or magnitude forest is evaluated here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import qrf_drift_phase0_a18_g3_splits as enumeration
import qrf_drift_phase0_c2c3 as a17
import qrf_drift_phase0_c4 as c4
import qrf_drift_phase0_replay as replay
import sklearn

CONTROL = "C3"
TARGET_GROUP = "G3"
GROUPS = ("G1", "G2", "G3")
POSITIVE_CLASS = 1
ROSTER_TARGET = "child_support_received"
INITIAL_REPLICATES = 250
ESCALATED_REPLICATES = 1_000

DEFAULT_ENUMERATION = Path(
    "/private/tmp/qrf_phase0_a18_g3_split_enumeration.json"
)
DEFAULT_C0B = Path("/private/tmp/qrf_phase0_v22_c0b.json")
DEFAULT_C4 = Path("/private/tmp/qrf_phase0_a17_c4.json")
DEFAULT_A17_C2C3 = Path("/private/tmp/qrf_phase0_a17_c2c3.json")
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_a18_c3.json")
DEFAULT_PARTIAL = Path("/private/tmp/qrf_phase0_a18_c3.partial.json")

EXPECTED_ENUMERATION_SHA256 = (
    "e853cc8e41c1c2d98dde605a8ca951dfb283246062cf04e280e688291b5d1314"
)
EXPECTED_ENUMERATION_CANONICAL_SHA256 = (
    "6f45c63094d5b5d5e48a0f60088ab43a58debbfb708c1e9fd0fa4d2dfb2c2dd3"
)
EXPECTED_SPLIT_TABLE_SHA256 = (
    "cfbc1dc7ddece6b9895306eb2e34865da79f0f882f52724a06dfc9bf412c264d"
)
EXPECTED_SELECTED_ROW_SHA256 = (
    "0cc8cd8f220e9c2f3ae48fdef141546356d2d780fdd72607f25c0957cf08b91b"
)
EXPECTED_C4_SHA256 = (
    "8cd95aafcdb896b8f6bedc86dcb030c912b277a6b28ba87d69bac0d79a5c06c5"
)
EXPECTED_C4_CANONICAL_SHA256 = (
    "ac3622032553c9aded22b4e182bc5db764c12232fe71c343b18a71aec31dae98"
)
EXPECTED_A17_C2C3_SHA256 = (
    "78a20b894457395add4253fd1772c3fa66194bda8b4aba69a40f10e1bfc2fa2a"
)
EXPECTED_A17_C2C3_CANONICAL_SHA256 = (
    "65eb83dbdd77e79548b78abc34b4898ae3c972347e5eb35a8d40f481c82756d7"
)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(c4.canonical_bytes(value)).hexdigest()


def verify_canonical_payload(
    payload: dict[str, Any],
    *,
    expected_canonical_sha256: str,
    label: str,
) -> None:
    stored = payload.get("canonical_sha256")
    scope = dict(payload)
    scope.pop("canonical_sha256", None)
    actual = canonical_sha256(scope)
    if stored != actual or actual != expected_canonical_sha256:
        raise ValueError(
            f"{label} canonical seal mismatch: stored={stored}, actual={actual}, "
            f"expected={expected_canonical_sha256}"
        )


def verify_enumeration_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Verify all internal table and selected-row seals, then return selection."""
    verify_canonical_payload(
        payload,
        expected_canonical_sha256=EXPECTED_ENUMERATION_CANONICAL_SHA256,
        label="A18 enumeration",
    )
    if (
        payload.get("artifact_kind")
        != "qrf_drift_phase0_a18_g3_split_enumeration"
        or payload.get("status") != "SEALED"
    ):
        raise ValueError("A18 enumeration is not a sealed enumeration artifact")
    if payload.get("authority", {}).get("design", {}).get("sha256") != (
        enumeration.EXPECTED_AUTHORITY_DIGESTS[str(enumeration.DESIGN_MD)]
    ):
        raise ValueError("A18 enumeration does not bind the operative design")
    input_verification = payload.get("input_verification", {})
    if input_verification.get("all_match") is not True or not all(
        item.get("match") is True for item in input_verification.get("files", [])
    ):
        raise ValueError("A18 enumeration input verification is not a clean pass")

    all_triples = payload.get("all_G3_triples", {})
    rows = all_triples.get("rows", [])
    if (
        all_triples.get("row_count") != len(rows)
        or all_triples.get("sha256") != canonical_sha256(rows)
    ):
        raise ValueError("A18 all-triples audit seal mismatch")
    recomputed_table = enumeration.seal_split_table(rows)
    recorded_table = payload.get("sealed_split_table")
    if recomputed_table != recorded_table:
        raise ValueError("A18 filtered split table does not reproduce from audit rows")
    if recorded_table.get("sha256") != EXPECTED_SPLIT_TABLE_SHA256:
        raise ValueError("A18 split-table digest is not the ratified seal")

    recomputed_selected = enumeration.select_largest_gain(recorded_table["rows"])
    disposition = payload.get("mechanical_disposition", {})
    selected = disposition.get("selected")
    if (
        disposition.get("branch") != 2
        or disposition.get("action") != "RETARGET_C3_TO_LARGEST_GAIN_TRIPLE"
        or selected != recomputed_selected
    ):
        raise ValueError("A18 branch-2 selected row does not reproduce mechanically")
    table_order = int(selected["table_order"])
    if not 0 <= table_order < len(recorded_table["rows"]):
        raise ValueError("A18 selected table index is out of bounds")
    selected_row = recorded_table["rows"][table_order]
    row_sha = canonical_sha256(selected_row)
    if (
        selected.get("row_sha256") != row_sha
        or row_sha != EXPECTED_SELECTED_ROW_SHA256
    ):
        raise ValueError("A18 selected-row digest is not the ratified seal")
    for key in (
        "target",
        "pattern",
        "G3_column",
        "split_count",
        "total_split_gain",
        "total_split_gain_hex",
    ):
        if selected[key] != selected_row[key]:
            raise ValueError(f"A18 selected summary disagrees on {key}")
    return {
        "selected": selected,
        "selected_row": selected_row,
        "table_sha256": recorded_table["sha256"],
        "all_triples_sha256": all_triples["sha256"],
    }


def load_and_verify_enumeration(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    actual_sha = c4.sha256_file(path)
    if actual_sha != EXPECTED_ENUMERATION_SHA256:
        raise ValueError(
            f"A18 enumeration file digest mismatch: {actual_sha} != "
            f"{EXPECTED_ENUMERATION_SHA256}"
        )
    payload = json.loads(path.read_text())
    return payload, verify_enumeration_payload(payload)


def verify_adopted_controls(
    c4_path: Path,
    a17_c2c3_path: Path,
) -> dict[str, Any]:
    """Verify and compactly adopt C4 and C2 without executing either control."""
    actual_c4_sha = c4.sha256_file(c4_path)
    if actual_c4_sha != EXPECTED_C4_SHA256:
        raise ValueError(f"adopted C4 digest mismatch: {actual_c4_sha}")
    c4_payload = json.loads(c4_path.read_text())
    verify_canonical_payload(
        c4_payload,
        expected_canonical_sha256=EXPECTED_C4_CANONICAL_SHA256,
        label="adopted C4",
    )
    c4_summary = c4_payload.get("summary", {})
    if not (
        c4_payload.get("status") == "PASS"
        and c4_summary.get("all_run_cells_pass") is True
        and c4_summary.get("gated_cells_run") == 40
        and c4_summary.get("failed_count") == 0
        and c4_summary.get("deterministic_empty_G3_checks_run") == 20
    ):
        raise ValueError("adopted C4 artifact is not the ratified full PASS")

    actual_c23_sha = c4.sha256_file(a17_c2c3_path)
    if actual_c23_sha != EXPECTED_A17_C2C3_SHA256:
        raise ValueError(f"adopted A17 C2/C3 digest mismatch: {actual_c23_sha}")
    c23_payload = json.loads(a17_c2c3_path.read_text())
    verify_canonical_payload(
        c23_payload,
        expected_canonical_sha256=EXPECTED_A17_C2C3_CANONICAL_SHA256,
        label="adopted A17 C2/C3",
    )
    c2 = c23_payload.get("controls", {}).get("C2", {})
    c3 = c23_payload.get("controls", {}).get("C3", {})
    c2_statistics = [
        item for item in c23_payload.get("statistics", []) if item.get("control") == "C2"
    ]
    if not (
        c23_payload.get("status") == "UNDERPOWERED"
        and c2.get("status") == "PASS"
        and c2.get("pass") is True
        and c2.get("group_recoveries_pass") is True
        and c2.get("power", {}).get("pass") is True
        and len(c2_statistics) == 3
        and all(item.get("pass") is True for item in c2_statistics)
        and c3.get("status") == "UNDERPOWERED"
        and c3.get("group_recoveries_pass") is True
        and c3.get("power", {}).get("absolute_oracle") == 0.0
    ):
        raise ValueError("A17 artifact is not exactly C2 PASS / old C3 UNDERPOWERED")
    c4_prerequisite = c23_payload.get("C4_prerequisite", {})
    if (
        c4_prerequisite.get("sha256") != EXPECTED_C4_SHA256
        or c4_prerequisite.get("pass") is not True
    ):
        raise ValueError("A17 C2 artifact does not bind the adopted C4 PASS")

    return {
        "C4": {
            "adoption_rule": "A14.7 digest match; no recomputation",
            "path": str(c4_path.resolve()),
            "sha256": actual_c4_sha,
            "canonical_sha256": c4_payload["canonical_sha256"],
            "status": c4_payload["status"],
            "gated_cells_passed": c4_summary["gated_cells_run"],
            "deterministic_exact_zeros_passed": c4_summary[
                "deterministic_empty_G3_checks_run"
            ],
        },
        "C2": {
            "adoption_rule": "A14.7 digest match; no recomputation",
            "path": str(a17_c2c3_path.resolve()),
            "sha256": actual_c23_sha,
            "canonical_sha256": c23_payload["canonical_sha256"],
            "control_payload_sha256": canonical_sha256(c2),
            "statistics_sha256": canonical_sha256(c2_statistics),
            "status": c2["status"],
            "group_recoveries_pass": c2["group_recoveries_pass"],
            "power": c2["power"],
            "statistic_ids": [item["id"] for item in c2_statistics],
        },
    }


def rows_label(target: str, pattern: str, replicate: int, gq: str) -> str:
    return (
        f"qrf-drift-v2.3|C3|rows|{target}|{replicate}|{pattern}|{gq}"
    )


def donor_label(target: str, pattern: str, replicate: int) -> str:
    return f"qrf-drift-v2.3|C3|donor|{target}|{pattern}|{replicate}"


def r0_label(target: str, pattern: str, replicate: int) -> str:
    return f"qrf-drift-v2.3|C3|r0|{target}|{pattern}|{replicate}"


def statistic_id(group: str) -> str:
    return (
        f"r=control|t={ROSTER_TARGET}|p=_|l=_|row=C3_oracle_error|g={group}|"
        "prior=_|gq=_|d=_|rep=_|fold=_|v=final"
    )


def transform_inputs(
    context: dict[str, Any],
    selected: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply A18's carrier-zero transform or its mechanical fallback."""
    column = selected["G3_column"]
    if column not in context["groups"]["G3"]:
        raise ValueError(f"sealed C3 column is not G3 in reproduced gate: {column}")
    position = context["columns"].index(column)
    transformed = context["donor_x"].copy()
    before = transformed[:, position].copy()
    carriers = before > 0.0
    carrier_count = int(carriers.sum())
    if carrier_count:
        transformed[carriers, position] = 0.0
        operation = "observed fit-row carriers x>0 set to zero"
        branch = "ZERO_OBSERVED_CARRIERS"
        observed_max: float | str = "NA"
    else:
        observed_max = float(np.max(before))
        transformed[:, position] = np.minimum(before * 1.25, observed_max)
        operation = "min(1.25*x, observed pattern fit-row max)"
        branch = "DECLARED_1_25X_FALLBACK"
    changed = transformed[:, position] != before
    return transformed, {
        "selection_source": "sealed A18 largest-gain row",
        "selected_row_sha256": selected["row_sha256"],
        "column": column,
        "column_position": position,
        "operation_branch": branch,
        "operation": operation,
        "observed_fit_row_carriers": carrier_count,
        "observed_max": observed_max,
        "changed_raw_rows": int(changed.sum()),
        "carrier_mask_identity": c4.array_identity(carriers.astype(np.uint8)),
        "raw_before_identity": c4.array_identity(before),
        "raw_after_identity": c4.array_identity(transformed[:, position]),
    }


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


def _coalition_indexes(
    context: dict[str, Any],
    mask: int,
    used: tuple[int, ...],
) -> tuple[np.ndarray, np.ndarray]:
    donor_indexes = {
        int(index)
        for group in GROUPS
        if mask & c4.GROUP_BITS[group]
        for index in context["group_indexes"][group]
    }
    j_indexes = np.asarray(
        [index for index in used if index in donor_indexes],
        dtype=np.int64,
    )
    i_indexes = np.asarray(
        [index for index in used if index not in donor_indexes],
        dtype=np.int64,
    )
    return i_indexes, j_indexes


def exact_coalition_delta(
    context: dict[str, Any],
    base_bins: np.ndarray,
    transformed_bins: np.ndarray,
    mask: int,
    *,
    chunk_pairs: int,
) -> tuple[float, dict[str, Any]]:
    """Evaluate A16-12's finite weighted i,j oracle for one coalition."""
    if mask & c4.GROUP_BITS["G3"]:
        return 0.0, {
            "exact_zero": True,
            "reason": "G3 donor substitution overwrites the intervened G3 column",
            "weighted_cartesian_pairs_evaluated": 0,
        }
    used = a17.used_feature_indexes(context["gate"])
    i_indexes, j_indexes = _coalition_indexes(context, mask, used)
    changed = np.any(
        base_bins[:, i_indexes] != transformed_bins[:, i_indexes],
        axis=1,
    )
    if not changed.any():
        return 0.0, {
            "exact_zero": True,
            "reason": "no transformed fit row crossed a used frozen-gate bin",
            "weighted_cartesian_pairs_evaluated": 0,
            "changed_bin_rows": 0,
        }

    weights = context["donor_weights"]
    base_i = base_bins[changed][:, i_indexes]
    transformed_i = transformed_bins[changed][:, i_indexes]
    i_signature = np.column_stack((base_i, transformed_i))
    i_unique, i_mass, i_counts = _aggregate_signatures(
        i_signature,
        weights[changed],
    )
    if len(j_indexes):
        j_unique, j_mass, j_counts = _aggregate_signatures(
            base_bins[:, j_indexes],
            weights,
        )
    else:
        j_unique = np.empty((1, 0), dtype=base_bins.dtype)
        j_mass = np.asarray([weights.sum(dtype=np.float64)], dtype=np.float64)
        j_counts = np.asarray([len(weights)], dtype=np.int64)

    i_width = len(i_indexes)
    positive = a17.positive_position(context)
    total_weight = float(weights.sum(dtype=np.float64))
    i_chunk = min(len(i_unique), max(1, math.isqrt(chunk_pairs)))
    j_chunk = min(len(j_unique), max(1, chunk_pairs // i_chunk))
    contributions: list[float] = []
    pairs_evaluated = 0
    for i_start in range(0, len(i_unique), i_chunk):
        i_stop = min(len(i_unique), i_start + i_chunk)
        for j_start in range(0, len(j_unique), j_chunk):
            j_stop = min(len(j_unique), j_start + j_chunk)
            i_block = i_unique[i_start:i_stop]
            j_block = j_unique[j_start:j_stop]
            pair_count = len(i_block) * len(j_block)
            original = np.zeros(
                (pair_count, base_bins.shape[1]),
                dtype=base_bins.dtype,
            )
            transformed = original.copy()
            repeated_i = np.repeat(i_block, len(j_block), axis=0)
            tiled_j = np.tile(j_block, (len(i_block), 1))
            original[:, i_indexes] = repeated_i[:, :i_width]
            transformed[:, i_indexes] = repeated_i[:, i_width:]
            if len(j_indexes):
                original[:, j_indexes] = tiled_j
                transformed[:, j_indexes] = tiled_j
            combined = np.concatenate((transformed, original), axis=0)
            probabilities = a17.predict_proba_binned(context, combined)[:, positive]
            differences = probabilities[:pair_count] - probabilities[pair_count:]
            pair_weights = np.multiply.outer(
                i_mass[i_start:i_stop],
                j_mass[j_start:j_stop],
            ).reshape(-1)
            contributions.append(float(np.dot(pair_weights, differences)))
            pairs_evaluated += pair_count
    numerator = math.fsum(contributions)
    value = numerator / (total_weight * total_weight)
    return value, {
        "exact_zero": False,
        "used_feature_indexes": list(used),
        "i_owned_used_feature_indexes": i_indexes.tolist(),
        "j_owned_used_feature_indexes": j_indexes.tolist(),
        "changed_bin_rows": int(changed.sum()),
        "unchanged_bin_rows_omitted_as_exact_zero": int((~changed).sum()),
        "i_unique_bin_signatures": len(i_unique),
        "j_unique_bin_signatures": len(j_unique),
        "weighted_cartesian_pairs_evaluated": pairs_evaluated,
        "chunk_pair_limit": chunk_pairs,
        "i_chunk": i_chunk,
        "j_chunk": j_chunk,
        "i_counts_identity": c4.array_identity(i_counts),
        "j_counts_identity": c4.array_identity(j_counts),
        "i_masses_identity": c4.array_identity(i_mass),
        "j_masses_identity": c4.array_identity(j_mass),
        "numerator": numerator,
        "denominator": total_weight * total_weight,
    }


def compute_exact_oracle(
    context: dict[str, Any],
    transformed: np.ndarray,
    *,
    chunk_pairs: int,
) -> dict[str, Any]:
    gate = context["gate"]
    base_bins = np.ascontiguousarray(gate._bin_mapper.transform(context["donor_x"]))
    transformed_bins = np.ascontiguousarray(gate._bin_mapper.transform(transformed))
    private_probabilities = a17.predict_proba_binned(context, base_bins)
    if not np.array_equal(private_probabilities, context["donor_probabilities"]):
        raise ValueError("private binned prediction is not bit-identical to C0b gate")
    transformed_probabilities = a17.predict_proba_binned(
        context,
        transformed_bins,
    )
    positive = a17.positive_position(context)
    weights = context["donor_weights"]
    difference = (
        transformed_probabilities[:, positive] - private_probabilities[:, positive]
    )
    direct_delta = float(
        np.dot(weights, difference) / weights.sum(dtype=np.float64)
    )

    coalitions = np.empty(8, dtype=np.float64)
    coalition_audits: list[dict[str, Any]] = []
    for mask in range(8):
        if mask == 0:
            value = direct_delta
            audit = {
                "exact_zero": direct_delta == 0.0,
                "reason": "direct fit-weighted per-row frozen-gate difference",
                "weighted_cartesian_pairs_evaluated": len(weights),
            }
        else:
            value, audit = exact_coalition_delta(
                context,
                base_bins,
                transformed_bins,
                mask,
                chunk_pairs=chunk_pairs,
            )
        coalitions[mask] = value
        coalition_audits.append({"mask": mask, "value": value, **audit})
    oracle = a17.shapley_from_coalitions(coalitions)
    shapley_residual = float(oracle.sum(dtype=np.float64) - (coalitions[7] - coalitions[0]))
    if abs(shapley_residual) > 1e-12 * max(abs(coalitions[7] - coalitions[0]), 1.0):
        raise ValueError(f"exact Shapley oracle does not close: {shapley_residual}")
    return {
        "formula": (
            "Delta(S)=W^-2 sum_ij w_i*w_j*[p+(z_S(Tx_i,x_j))-"
            "p+(z_S(x_i,x_j))]"
        ),
        "coalition_mask_order_0_to_7": coalitions.tolist(),
        "coalition_identity": c4.array_identity(coalitions),
        "coalition_audits": coalition_audits,
        "oracle_group_order_G1_G2_G3": oracle.tolist(),
        "oracle_identity": c4.array_identity(oracle),
        "target_group": TARGET_GROUP,
        "target_group_oracle": float(oracle[GROUPS.index(TARGET_GROUP)]),
        "shapley_closure_residual": shapley_residual,
        "direct_difference_nonzero_rows": int(np.count_nonzero(difference)),
        "direct_difference_identity": c4.array_identity(difference),
        "base_bins_identity": c4.array_identity(base_bins),
        "transformed_bins_identity": c4.array_identity(transformed_bins),
        "private_binned_prediction_identity": c4.array_identity(
            private_probabilities
        ),
        "transformed_binned_prediction_identity": c4.array_identity(
            transformed_probabilities
        ),
    }


def sample_rows(
    target: str,
    pattern: str,
    replicate: int,
    plan: list[dict[str, Any]],
    probabilities: np.ndarray,
) -> np.ndarray:
    pieces = [
        c4.weighted_choice(
            rows_label(target, pattern, replicate, item["gq"]),
            probabilities,
            item["allocation"],
        )
        for item in plan
        if item["allocation"] > 0
    ]
    if not pieces:
        raise ValueError("C3 rows plan is empty")
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
    aggregation_slices: list[dict[str, Any]],
) -> dict[str, np.ndarray]:
    """Evaluate all eight coalitions for full-route and same-i,j C3 paths."""
    base = context["donor_x"]
    donor = base[donor_index]
    path_bases = {
        "real": transformed[row_index],
        "null": base[r0_index],
        "paired_base": base[row_index],
    }
    positive = a17.positive_position(context)
    known_empty = {
        "null": a17.flat_unit_mean(
            context["donor_probabilities"][r0_index, positive]
        ),
        "paired_base": a17.exact_stratum_weighted_mean(
            context["donor_probabilities"][row_index, positive],
            aggregation_slices,
        ),
    }
    donor_endpoint = context["donor_probabilities"][donor_index, positive]
    known_all = {
        "real": a17.exact_stratum_weighted_mean(
            donor_endpoint,
            aggregation_slices,
        ),
        "paired_base": a17.exact_stratum_weighted_mean(
            donor_endpoint,
            aggregation_slices,
        ),
        "null": a17.flat_unit_mean(donor_endpoint),
    }

    # For masks containing G3, the donor substitution overwrites the selected
    # intervention, so real and paired_base inputs are identical and share one
    # prediction.  All other partial coalitions are evaluated explicitly.
    specs = (
        [("real", mask) for mask in range(4)]
        + [("paired_base", mask) for mask in range(1, 7)]
        + [("null", mask) for mask in range(1, 7)]
    )
    blocks = [
        _hybrid_block(context, path_bases[path], donor, mask)
        for path, mask in specs
    ]
    probabilities = (
        context["gate"]
        .predict_proba(np.concatenate(blocks))[:, positive]
        .reshape(len(specs), len(row_index))
    )
    predicted_means: dict[tuple[str, int], float] = {}
    for position, (path, mask) in enumerate(specs):
        if path == "null":
            mean = a17.flat_unit_mean(probabilities[position])
        else:
            mean = a17.exact_stratum_weighted_mean(
                probabilities[position],
                aggregation_slices,
            )
        predicted_means[(path, mask)] = mean

    coalitions: dict[str, np.ndarray] = {}
    for path in path_bases:
        values = np.empty(8, dtype=np.float64)
        values[0] = predicted_means[(path, 0)] if path == "real" else known_empty[path]
        values[7] = known_all[path]
        for mask in range(1, 7):
            if path == "real" and mask & c4.GROUP_BITS["G3"]:
                values[mask] = predicted_means[("paired_base", mask)]
            else:
                values[mask] = predicted_means[(path, mask)]
        coalitions[path] = values
    shapley = {
        path: a17.shapley_from_coalitions(values)
        for path, values in coalitions.items()
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
    plan: list[dict[str, Any]],
    start: int,
    stop: int,
) -> dict[str, Any]:
    count = stop - start
    arrays: dict[str, Any] = {
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
    aggregation_slices = a17.stratum_aggregation_slices(plan)
    first_indexes: dict[str, Any] | None = None
    last_indexes: dict[str, Any] | None = None
    target = context["target"]
    pattern = context["pattern"]
    for offset, replicate in enumerate(range(start, stop)):
        rows = sample_rows(target, pattern, replicate, plan, probabilities)
        donor = c4.weighted_choice(
            donor_label(target, pattern, replicate),
            probabilities,
            sample_size,
        )
        r0 = c4.weighted_choice(
            r0_label(target, pattern, replicate),
            probabilities,
            sample_size,
        )
        values = evaluate_replicate(
            context,
            transformed,
            rows,
            donor,
            r0,
            aggregation_slices,
        )
        for name, array in arrays.items():
            if name != "index_identities":
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
        if (offset + 1) % 25 == 0 or offset + 1 == count:
            print(f"C3 replicate {replicate + 1}/{stop}", flush=True)
    arrays["index_identities"] = {
        "first": first_indexes,
        "last": last_indexes,
    }
    return arrays


def concatenate_ranges(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, Any]:
    names = (
        "real_shapley",
        "null_shapley",
        "paired_base_shapley",
        "recovered",
        "paired_delta",
        "real_coalitions",
        "null_coalitions",
        "paired_base_coalitions",
    )
    result = {
        name: np.concatenate((first[name], second[name]), axis=0) for name in names
    }
    result["index_identities"] = {
        "first": first["index_identities"]["first"],
        "last": second["index_identities"]["last"],
    }
    return result


def control_statistics(
    target: str,
    pattern: str,
    column: str,
    arrays: dict[str, Any],
    oracle: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for position, group in enumerate(GROUPS):
        vector = arrays["paired_delta"][:, position]
        summary = a17.error_summary(vector, float(oracle[position]))
        rows.append(
            {
                "id": statistic_id(group),
                "control": CONTROL,
                "target": ROSTER_TARGET,
                "pattern": pattern,
                "evaluated_target": target,
                "evaluated_pattern": pattern,
                "evaluated_column": column,
                "group": group,
                "target_group": group == TARGET_GROUP,
                "family": "C2_C3_group_errors",
                "gated": True,
                "estimator_array": "paired_delta",
                "pairing": "same_i_j",
                "status": "PASS" if summary["pass"] else "FAIL",
                **summary,
                "replicate_values": [float(value) for value in vector],
                "replicate_values_identity": c4.array_identity(vector),
                "source": {
                    "design": str(enumeration.DESIGN_MD),
                    "design_sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[
                        str(enumeration.DESIGN_MD)
                    ],
                    "d0_sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[
                        str(enumeration.D0_JSON)
                    ],
                    "adopted_c0b_sha256": enumeration.EXPECTED_C0B_SHA256,
                    "binding": "A16 findings 12-14 plus A18 branch 2",
                    "official_recovery_array": "paired_delta",
                    "exact_oracle_pointer": (
                        "/exact_oracle/oracle_group_order_G1_G2_G3"
                    ),
                },
            }
        )
    return rows


def _array_payload(values: np.ndarray) -> dict[str, Any]:
    return {
        "values": np.asarray(values, dtype=np.float64).tolist(),
        "identity": c4.array_identity(values),
    }


def control_payload(
    context: dict[str, Any],
    arrays: dict[str, Any],
    oracle: np.ndarray,
    plan: list[dict[str, Any]],
    initial_triggers: list[dict[str, Any]],
    escalated: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    target = context["target"]
    pattern = context["pattern"]
    column = context["selected_G3_column"]
    statistics = control_statistics(target, pattern, column, arrays, oracle)
    target_position = GROUPS.index(TARGET_GROUP)
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
    replicate_count = len(arrays["paired_delta"])
    slices = a17.stratum_aggregation_slices(plan)
    payload = {
        "control": CONTROL,
        "roster_target": ROSTER_TARGET,
        "evaluated_target": target,
        "evaluated_pattern": pattern,
        "evaluated_column": column,
        "target_group": TARGET_GROUP,
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
                    "exact_weight_share": slice_item["exact_weight_share"],
                    "slice_start": slice_item["start"],
                    "slice_stop": slice_item["stop"],
                    "first": rows_label(target, pattern, 0, item["gq"]),
                    "last": rows_label(
                        target,
                        pattern,
                        replicate_count - 1,
                        item["gq"],
                    ),
                }
                for item, slice_item in zip(plan, slices, strict=True)
            ],
            "donor_first": donor_label(target, pattern, 0),
            "donor_last": donor_label(target, pattern, replicate_count - 1),
            "r0_first": r0_label(target, pattern, 0),
            "r0_last": r0_label(target, pattern, replicate_count - 1),
            "derivation": "first 8 SHA-256 bytes, big-endian uint64, PCG64",
            "index_identities": arrays["index_identities"],
        },
        "oracle_by_group": {
            group: float(oracle[position]) for position, group in enumerate(GROUPS)
        },
        "replicate_arrays": {
            name: _array_payload(arrays[name])
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
        "official_recovery": {
            "array": "paired_delta",
            "pairing": "same_i_j",
            "rostered": True,
        },
        "independent_r0_full_route_descriptive_audit": [
            {
                "group": group,
                "rostered": False,
                **a17.error_summary(
                    arrays["recovered"][:, position],
                    float(oracle[position]),
                ),
                "replicate_values_identity": c4.array_identity(
                    arrays["recovered"][:, position]
                ),
            }
            for position, group in enumerate(GROUPS)
        ],
        "power": {
            "target_group": TARGET_GROUP,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enumeration-json", type=Path, default=DEFAULT_ENUMERATION)
    parser.add_argument("--c0b-json", type=Path, default=DEFAULT_C0B)
    parser.add_argument("--c4-json", type=Path, default=DEFAULT_C4)
    parser.add_argument("--a17-c2c3-json", type=Path, default=DEFAULT_A17_C2C3)
    parser.add_argument(
        "--replicates",
        type=int,
        help="fixed non-authoritative smoke count; default is adaptive 250/1000",
    )
    parser.add_argument(
        "--chunk-pairs",
        type=int,
        default=2_000_000,
        help="maximum binned Cartesian pairs per exact-oracle prediction chunk",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--partial", type=Path, default=DEFAULT_PARTIAL)
    args = parser.parse_args()
    if args.replicates is not None and args.replicates < 2:
        parser.error("--replicates must be at least 2")
    if args.chunk_pairs < 1:
        parser.error("--chunk-pairs must be positive")
    return args


def _write_partial(path: Path, result: dict[str, Any]) -> None:
    result["execution_diagnostics"]["peak_rss_mb_so_far"] = c4.peak_rss_mb()
    c4.write_canonical_result(path, result)


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    enumeration_payload, enumeration_evidence = load_and_verify_enumeration(
        args.enumeration_json
    )
    selected = enumeration_evidence["selected"]
    selected_row = enumeration_evidence["selected_row"]
    adoptions = verify_adopted_controls(args.c4_json, args.a17_c2c3_json)

    d0 = json.loads(enumeration.D0_JSON.read_text())
    input_verification = enumeration.verify_inputs(d0, args.c0b_json)
    c0b = json.loads(args.c0b_json.read_text())
    if not (
        c0b.get("status") == "PASS"
        and c0b.get("summary", {}).get("e4_bit_identical_pass") is True
        and c0b.get("summary", {}).get("e2_repeated_draw_control_pass") is True
    ):
        raise ValueError("adopted C0b artifact is not a clean PASS")
    c0b_lookup = {
        (item["target"], item["pattern"]): item for item in c0b["patterns"]
    }

    data = c4.load_analysis_data(d0)
    target = selected["target"]
    pattern = selected["pattern"]
    context = c4.fit_gate_context(data, target, pattern, c0b_lookup)
    context["selected_G3_column"] = selected["G3_column"]
    if not all(context["c0b_bindings"].values()):
        raise ValueError("re-targeted C3 gate does not bind adopted C0b")
    split_statistics = enumeration.split_feature_statistics(context["gate"])
    selected_index = context["columns"].index(selected["G3_column"])
    reproduced_split = split_statistics.get(selected_index)
    for key in (
        "split_count",
        "total_split_gain",
        "total_split_gain_hex",
        "split_gain_sequence_identity",
    ):
        if reproduced_split is None or reproduced_split[key] != selected_row[key]:
            raise ValueError(f"selected split row does not reproduce on {key}")
    if enumeration.gate_nodes_identity(context["gate"]) != selected_row["source"][
        "gate_nodes"
    ]:
        raise ValueError("selected gate node digest differs from enumeration")

    allocation = c4.target_allocation(data, target)
    plan = [
        {
            "gq": item["gq"],
            "row_count": item["row_count"],
            "weight_sum": item["weight_sum"],
            "allocation": item["allocation"],
        }
        for item in allocation["strata"]
        if item["pattern"] == pattern and item["weight_sum"] > 0.0
    ]
    transformed, transformation = transform_inputs(context, selected)
    result: dict[str, Any] = {
        "artifact_kind": "qrf_drift_phase0_a18_c3",
        "schema_version": 1,
        "status": "RUNNING",
        "authority": {
            "design": {
                "path": str(enumeration.DESIGN_MD),
                "sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[
                    str(enumeration.DESIGN_MD)
                ],
                "commit": "8d553796e846012e7dc2663d7ffe108b6f965cca",
                "amendment": "v2.7/A18 branch 2",
            },
            "a16_binding": {
                "path": str(enumeration.A16_BINDING),
                "sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[
                    str(enumeration.A16_BINDING)
                ],
                "findings": [12, 13, 14],
            },
            "d0": {
                "path": str(enumeration.D0_JSON),
                "sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[
                    str(enumeration.D0_JSON)
                ],
            },
            "enumeration": {
                "path": str(args.enumeration_json.resolve()),
                "sha256": EXPECTED_ENUMERATION_SHA256,
                "canonical_sha256": enumeration_payload["canonical_sha256"],
                "table_sha256": enumeration_evidence["table_sha256"],
                "selected_row_sha256": selected["row_sha256"],
            },
            "adopted_c0b": {
                "path": str(args.c0b_json.resolve()),
                "sha256": enumeration.EXPECTED_C0B_SHA256,
            },
        },
        "input_verification": input_verification,
        "adopted_controls": adoptions,
        "scope": {
            "rung": "candidate-25 pre-calibration",
            "target": target,
            "pattern": pattern,
            "G3_column": selected["G3_column"],
            "selection_rule": "largest total G3 split gain; D0 order tie-break",
            "selection": selected,
            "pattern_sample_size": sum(item["allocation"] for item in plan),
            "pattern_allocation": plan,
            "pattern_stratum_aggregation": a17.stratum_aggregation_slices(plan),
            "target_allocation": allocation,
            "positive_class": "positive",
            "gate_classes": [int(value) for value in context["gate_classes"]],
            "readings_computed": False,
            "magnitude_forests_loaded": False,
        },
        "control_roster": {
            "overall_K": c4.OVERALL_CONTROL_K,
            "adopted_C4_K": c4.C4_STOCHASTIC_K,
            "adopted_C2_group_errors_K": 3,
            "rerun_C3_group_errors_K": 3,
            "sidak_z": c4.Z_STAR,
            "overall_ordered_ids_sha256": c4.OVERALL_ROSTER_SHA256,
            "ids": [statistic_id(group) for group in GROUPS],
            "note": (
                "A18 branch 2 evaluates a new triple inside the three sealed "
                "child_support_received C3 slots; K, ordered roster digest, "
                "and the bound Sidak z are unchanged"
            ),
        },
        "estimator": {
            "official_recovery_array": "paired_delta",
            "official_pairing": "same_i_j",
            "official_recovery": (
                "Shapley(T(rows), donor) - Shapley(rows, donor), using "
                "identical i,j draws over all eight coalitions"
            ),
            "independent_r0_array": "recovered",
            "independent_r0_role": "descriptive_full_A14_route_not_rostered",
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
            "fixed_replicate_override": args.replicates,
            "escalation": (
                "at R=250, append C3 r=250..999 iff any of its three official "
                "abs oracle-error/MCSE ratios is in [2,4]"
            ),
            "pass": "each of three abs(error) <= z*MCSE",
            "power": "abs(G3 oracle) > 5*z*G3 MCSE at final R",
        },
        "gate_context": {
            "gate_seed": context["gate_seed"],
            "state_before_sha256": context["state_before_sha256"],
            "state_before_source": context["state_before_source"],
            "columns": list(context["columns"]),
            "groups": {group: list(context["groups"][group]) for group in GROUPS},
            "donor_x_identity": c4.array_identity(context["donor_x"]),
            "donor_y_identity": c4.array_identity(context["donor_y"]),
            "donor_weight_identity": replay.weight_identity(
                context["donor_weights"]
            ),
            "donor_probability_identity": c4.array_identity(
                context["donor_probabilities"]
            ),
            "gate_nodes": enumeration.gate_nodes_identity(context["gate"]),
            "c0b_bindings": context["c0b_bindings"],
        },
        "transformation": transformation,
        "exact_oracle": {},
        "control": {},
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
    _write_partial(args.partial, result)

    oracle_started = time.perf_counter()
    exact = compute_exact_oracle(
        context,
        transformed,
        chunk_pairs=args.chunk_pairs,
    )
    exact["elapsed_seconds"] = time.perf_counter() - oracle_started
    result["exact_oracle"] = exact
    print(
        "exact C3 oracle "
        f"{exact['oracle_group_order_G1_G2_G3']} "
        f"seconds={exact['elapsed_seconds']:.1f}",
        flush=True,
    )
    _write_partial(args.partial, result)

    initial_stop = args.replicates or INITIAL_REPLICATES
    arrays = run_replicate_range(
        context,
        transformed,
        plan,
        0,
        initial_stop,
    )
    oracle = np.asarray(
        exact["oracle_group_order_G1_G2_G3"],
        dtype=np.float64,
    )
    initial_statistics = control_statistics(
        target,
        pattern,
        selected["G3_column"],
        arrays,
        oracle,
    )
    triggers = [
        {"id": item["id"], "abs_error_over_mcse": item["abs_error_over_mcse"]}
        for item in initial_statistics
        if item["escalation_trigger_at_this_R"]
    ]
    escalated = args.replicates is None and bool(triggers)
    if escalated:
        extension = run_replicate_range(
            context,
            transformed,
            plan,
            INITIAL_REPLICATES,
            ESCALATED_REPLICATES,
        )
        arrays = concatenate_ranges(arrays, extension)

    control, statistics = control_payload(
        context,
        arrays,
        oracle,
        plan,
        triggers,
        escalated,
    )
    result["control"] = control
    result["statistics"] = statistics
    expected_ids = sorted(statistic_id(group) for group in GROUPS)
    if sorted(item["id"] for item in statistics) != expected_ids:
        raise ValueError("re-targeted C3 three-cell roster mismatch")

    if args.replicates is not None:
        status = "NON_AUTHORITATIVE_FIXED_REPLICATE_RUN"
    else:
        status = control["status"]
    result["status"] = status
    result["summary"] = {
        "adopted_C4_status": adoptions["C4"]["status"],
        "adopted_C2_status": adoptions["C2"]["status"],
        "rerun_C3_status": control["status"],
        "rostered_cells": len(statistics),
        "rostered_cells_passed": sum(item["pass"] for item in statistics),
        "failed_ids": [item["id"] for item in statistics if not item["pass"]],
        "escalated_to_1000": escalated,
        "all_three_recoveries_pass": all(item["pass"] for item in statistics),
        "power_check_pass": control["power"]["pass"],
        "terminal_gated_disposition": (
            "NON_AUTHORITATIVE_SMOKE"
            if args.replicates is not None
            else "PROCEED"
            if status == "PASS"
            else "STOP_BEFORE_READINGS"
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
