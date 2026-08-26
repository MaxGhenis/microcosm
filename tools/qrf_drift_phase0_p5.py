#!/usr/bin/env python3
"""Run the exact A16-frozen Phase-0 P5 Gower-distance reading.

The executor restores the C0b-bound incidence gates and evaluates every
candidate-25 ``S_q`` row against every donor fit row in its availability
pattern.  Distances are streamed in bounded recipient blocks; no approximate
nearest-neighbour index is used.  Metric scores are cached in memory when the
role, pattern, effective columns, and all metric arrays are bit-identical
across targets.

The selected-neighbour identity at an exact distance tie cannot change the
reported arithmetic mean because every tied candidate contributes the same
binary64 distance.  The output therefore records the normative A16 key and
the exact score-equivalence proof, while deliberately not materializing
neighbour identities.  A sorted distance vector fixes the arithmetic
reduction order; no neighbour identity is reported or used downstream.
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
import qrf_drift_phase0_c4 as c4
import qrf_drift_phase0_p1 as p1
import qrf_drift_phase0_p2 as p2

WORKTREE = Path(__file__).resolve().parents[1]
DESIGN = WORKTREE / "experiments/qrf_drift_validation_design.md"
D0_JSON = WORKTREE / "experiments/qrf_drift_validation_d0.json"
A16_BINDING = WORKTREE / "experiments/qrf_drift_validation_a16_binding_texts.md"

DEFAULT_ADOPTION = Path("/private/tmp/qrf_phase0_a18_adoption.json")
DEFAULT_C3 = Path("/private/tmp/qrf_phase0_a18_c3.json")
DEFAULT_C4 = Path("/private/tmp/qrf_phase0_a17_c4.json")
DEFAULT_C0B = Path("/private/tmp/qrf_phase0_v22_c0b.json")
DEFAULT_P1 = Path("/private/tmp/qrf_phase0_p1.json")
DEFAULT_MANIFEST = Path("/private/tmp/qrf_phase0_a17_terminal_report.json")
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_a18_p5.json")

DESIGN_SHA256 = "5c8e55293215a7d1350c93825b1a4daf04e212bb84d17408b8750ed5d9d4e754"
D0_SHA256 = "fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8"
A16_SHA256 = "7e288bce7496e1e7f41e33f078be2043673ca54ff31182caf2ce92eab68a81c1"
STEP0_MANIFEST_SHA256 = (
    "e65378071bf9e9519b51eba30c63fd89ca08d982e35610bb5017fcf599e29142"
)

TARGETS = p1.TARGETS
LEGS = p1.LEGS
K_NEIGHBOURS = 25
DEFAULT_BLOCK_SIZE = 32

# A15-32: these are the categorical members of the complete D0-7 effective
# column universe.  Counts and monetary/hour/age columns remain numeric even
# when their observed support happens to contain only two values.
CATEGORICAL_COLUMNS = frozenset(
    {
        "is_female",
        "__acs_transfer_state_fips",
        "__acs_transfer_is_household_head",
        "__acs_transfer_tenure_code",
        "__acs_transfer_group_tenure_code",
        "is_incapable_of_self_care",
        "previous_year_income_available",
    }
)

# Local non-authoritative calibration on the actual pinned
# child_support_expense/pattern_00_36785ebf surface.  It includes exact
# binary64 distance accumulation, top-25 partition, and ordered reduction for
# all 478 S_q rows.  The conservative disposition multiplies the observed
# kernel projection by four.
BENCHMARK = {
    "kind": "actual_pinned_surface_non_authoritative_smoke",
    "target": "child_support_expense",
    "pattern": "pattern_00_36785ebf",
    "block_size": 32,
    "donor_rows": 108_073,
    "recipient_rows": 478,
    "features": 6,
    "feature_pair_costs": 309_953_364,
    "elapsed_seconds": 0.6226019160239957,
    "feature_pair_costs_per_second": 497_835_544.70791906,
    "score_sha256": "8e4fb543bf6e96ec8983ada907ae89caa3955ec4652f86ff417cb14b150d6540",
    "conservative_multiplier": 4.0,
}


def require(condition: bool, message: str) -> None:
    """Raise a uniform fail-closed error."""
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_rss_mb() -> float:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return float(raw) / (1024.0 * 1024.0)
    return float(raw) / 1024.0


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(c4.canonical_bytes(value)).hexdigest()


def compact_sha256(value: Any) -> str:
    return hashlib.sha256(c4.canonical_json(value).encode()).hexdigest()


def verify_p1_artifact(path: Path, c0b_path: Path) -> dict[str, Any]:
    """Verify the P1 seal and the T2/phi surfaces consumed by P5."""
    payload = json.loads(path.read_text())
    recorded = payload.get("content_sha256")
    scope = dict(payload)
    scope.pop("content_sha256", None)
    require(recorded == compact_sha256(scope), "P1 self-excluding seal mismatch")
    require(
        payload.get("artifact_kind") == "qrf_drift_phase0_p0_p1_p6_p7"
        and payload.get("status") == "COMPLETE",
        "P1 is not the complete all-target reading",
    )
    authority = payload.get("authority", {})
    require(
        authority.get("design", {}).get("sha256") == DESIGN_SHA256
        and authority.get("D0", {}).get("sha256") == D0_SHA256,
        "P1 authority changed",
    )
    require(
        authority.get("direct_C0b_evidence", {}).get("sha256") == sha256_file(c0b_path),
        "P1 and P5 do not share the same direct C0b evidence",
    )
    readings = payload.get("candidate-25", {}).get("targets", {})
    require(
        set(readings) == set(TARGETS)
        and all(readings[target].get("status") == "COMPLETE" for target in TARGETS),
        "P1 target roster is incomplete or reordered",
    )
    return payload


def weighted_inverse_cdf(
    values: np.ndarray,
    weights: np.ndarray,
    quantile: float,
) -> float:
    """Return the fit-weighted inverse empirical CDF at ``quantile``."""
    x = np.asarray(values, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    require(len(x) == len(w) and len(x) > 0, "weighted CDF input is empty/misaligned")
    require(
        np.isfinite(x).all() and np.isfinite(w).all() and (w > 0.0).all(),
        "weighted CDF input is nonfinite or nonpositive",
    )
    require(0.0 <= quantile <= 1.0, "weighted CDF quantile is outside [0,1]")
    order = np.argsort(x, kind="stable")
    ordered_x = x[order]
    cumulative = np.cumsum(w[order], dtype=np.float64)
    cutoff = float(quantile * cumulative[-1])
    position = int(np.searchsorted(cumulative, cutoff, side="left"))
    position = min(position, len(ordered_x) - 1)
    return float(ordered_x[position])


def metric_definition(
    donor_x: np.ndarray,
    donor_weights: np.ndarray,
    columns: tuple[str, ...],
) -> dict[str, Any]:
    """Freeze categorical semantics and donor-weighted numeric IQRs."""
    matrix = np.asarray(donor_x, dtype=np.float64)
    weights = np.asarray(donor_weights, dtype=np.float64)
    require(
        matrix.ndim == 2 and matrix.shape[1] == len(columns), "metric columns differ"
    )
    require(len(matrix) == len(weights), "metric donor weights differ")
    unknown = set(CATEGORICAL_COLUMNS) - {
        name
        for target in json.loads(D0_JSON.read_text())["D0-7"]["targets"].values()
        for pattern in target["patterns"]
        for name in pattern["effective_gate_columns"]
    }
    require(
        not unknown, f"categorical roster contains non-D0 columns: {sorted(unknown)}"
    )
    features: list[dict[str, Any]] = []
    for position, name in enumerate(columns):
        if name in CATEGORICAL_COLUMNS:
            features.append(
                {
                    "name": name,
                    "position": position,
                    "semantics": "categorical_exact_mismatch",
                    "q25": "NA",
                    "q75": "NA",
                    "iqr": "NA",
                }
            )
            continue
        q25 = weighted_inverse_cdf(matrix[:, position], weights, 0.25)
        q75 = weighted_inverse_cdf(matrix[:, position], weights, 0.75)
        iqr = float(q75 - q25)
        require(iqr >= 0.0, f"negative weighted IQR for {name}")
        features.append(
            {
                "name": name,
                "position": position,
                "semantics": (
                    "numeric_zero_iqr_exact_mismatch"
                    if iqr == 0.0
                    else "numeric_abs_over_iqr_capped_one"
                ),
                "q25": q25,
                "q75": q75,
                "iqr": iqr,
            }
        )
    return {"columns": list(columns), "features": features}


def exact_gower_knn_scores(
    donor_x: np.ndarray,
    recipient_x: np.ndarray,
    definition: dict[str, Any],
    *,
    k: int = K_NEIGHBOURS,
    block_size: int = DEFAULT_BLOCK_SIZE,
    progress_label: str | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Compute exact all-donor Gower kNN means in bounded blocks."""
    donor = np.asarray(donor_x, dtype=np.float64)
    recipient = np.asarray(recipient_x, dtype=np.float64)
    require(
        donor.ndim == recipient.ndim == 2
        and donor.shape[1] == recipient.shape[1]
        and donor.shape[1] == len(definition["features"]),
        "Gower matrices or definition differ",
    )
    require(
        np.isfinite(donor).all() and np.isfinite(recipient).all(),
        "Gower input is nonfinite",
    )
    require(block_size > 0 and k > 0 and len(donor) > 0, "invalid Gower block/k/pool")
    used_k = min(k, len(donor))
    scores = np.empty(len(recipient), dtype=np.float64)
    started = time.monotonic()
    last_progress = started

    for start in range(0, len(recipient), block_size):
        stop = min(start + block_size, len(recipient))
        block = recipient[start:stop]
        distance = np.zeros((len(block), len(donor)), dtype=np.float64)
        for feature in definition["features"]:
            position = int(feature["position"])
            semantics = feature["semantics"]
            if semantics == "categorical_exact_mismatch":
                distance += block[:, position, None] != donor[None, :, position]
            elif semantics == "numeric_zero_iqr_exact_mismatch":
                distance += block[:, position, None] != donor[None, :, position]
            else:
                component = np.abs(block[:, position, None] - donor[None, :, position])
                component /= float(feature["iqr"])
                np.minimum(component, 1.0, out=component)
                distance += component
        distance /= donor.shape[1]
        nearest = np.partition(distance, used_k - 1, axis=1)[:, :used_k]
        # Sorting the selected distances fixes the binary64 reduction order.
        # A16's source-ID tie key chooses identities only among equal values,
        # so it cannot change this score.
        nearest.sort(axis=1)
        scores[start:stop] = nearest.sum(axis=1, dtype=np.float64) / used_k

        now = time.monotonic()
        if progress_label and (now - last_progress >= 45.0 or stop == len(recipient)):
            print(
                json.dumps(
                    {
                        "P5_progress": progress_label,
                        "recipient_rows_complete": stop,
                        "recipient_rows_total": len(recipient),
                        "elapsed_seconds": now - started,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            last_progress = now

    diagnostics = {
        "requested_k": k,
        "used_k": used_k,
        "pool_under_25": len(donor) < K_NEIGHBOURS,
        "donor_rows": len(donor),
        "recipient_rows": len(recipient),
        "feature_count": donor.shape[1],
        "pairwise_distances": int(len(donor) * len(recipient)),
        "feature_pair_costs": int(len(donor) * len(recipient) * donor.shape[1]),
        "block_size": block_size,
        "elapsed_seconds": time.monotonic() - started,
        "normative_tie_rule": ["stable_source_row_id", "D0_fit_ordinal"],
        "tie_identity_materialized": False,
        "tie_score_invariance": (
            "the arithmetic mean uses only distance values; all rows tied at "
            "a cutoff have the same binary64 distance"
        ),
        "exact_all_donor_search": True,
        "approximation": False,
    }
    return scores, diagnostics


def weighted_decile_bins(
    scores: np.ndarray,
    stable_entity_ids: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply the A16-35 weighted-midpoint bin rule within one pattern."""
    score = np.asarray(scores, dtype=np.float64)
    ids = np.asarray(stable_entity_ids)
    w = np.asarray(weights, dtype=np.float64)
    require(len(score) == len(ids) == len(w) and len(score) > 0, "decile inputs differ")
    require(
        np.isfinite(score).all() and np.isfinite(w).all() and (w > 0).all(),
        "bad decile inputs",
    )
    order = np.lexsort((ids, score))
    sorted_w = w[order]
    cumulative = np.cumsum(sorted_w, dtype=np.float64)
    before = cumulative - sorted_w
    midpoint_fraction = (before + sorted_w / 2.0) / cumulative[-1]
    sorted_bins = np.minimum(9, np.floor(10.0 * midpoint_fraction).astype(np.int8))
    bins = np.empty(len(score), dtype=np.int8)
    bins[order] = sorted_bins
    return bins, {
        "sort": ["score", "stable_entity_id"],
        "weight_sum": float(cumulative[-1]),
        "bin_rows": np.bincount(bins, minlength=10).astype(int).tolist(),
        "bin_weight": np.bincount(bins, weights=w, minlength=10).tolist(),
    }


def decile_partition_closure(
    bin_weight: np.ndarray,
    bin_rows: np.ndarray,
    assignment_counts: np.ndarray,
    expected_mask: np.ndarray,
    *,
    total_weight: float,
) -> dict[str, Any]:
    """Verify exact-once row assignment and aggregate decile closure.

    ``np.bincount`` reduces each bin in a different order from the original
    full-vector sum.  On the 856,626-row child-support surface that legitimate
    roundoff exceeds 1e-6 even though every row appears exactly once.  Row
    identity is therefore certified separately from the aggregate row and
    weight checks; the weight check uses a bounded ULP allowance only for
    reduction-order drift.
    """
    weights = np.asarray(bin_weight, dtype=np.float64)
    rows = np.asarray(bin_rows, dtype=np.int64)
    raw_counts = np.asarray(assignment_counts)
    raw_expected = np.asarray(expected_mask)
    require(
        weights.shape == rows.shape == (10,)
        and np.isfinite(weights).all()
        and (weights >= 0.0).all()
        and (rows >= 0).all(),
        "P5 decile closure inputs are malformed",
    )
    require(
        raw_counts.ndim == raw_expected.ndim == 1
        and raw_counts.shape == raw_expected.shape
        and raw_counts.dtype.kind in {"i", "u"},
        "P5 decile assignment certificate inputs are malformed",
    )
    require(
        raw_expected.dtype.kind == "b",
        "P5 expected decile assignment mask is not boolean",
    )
    counts = np.asarray(raw_counts, dtype=np.int64)
    expected = np.asarray(raw_expected, dtype=bool)
    require((counts >= 0).all(), "P5 decile assignment counts are negative")
    expected_rows = int(expected.sum())
    missing = expected & (counts == 0)
    duplicated = expected & (counts > 1)
    unexpected = (~expected) & (counts > 0)
    exact_once = np.array_equal(counts, expected.astype(np.int64))
    assignment_slots = int(counts.sum(dtype=np.int64))
    assignment_certificate = {
        "status": "PASS" if exact_once else "FAIL",
        "exactly_once": bool(exact_once),
        "expected_rows": expected_rows,
        "assignment_slots": assignment_slots,
        "exactly_once_rows": int((expected & (counts == 1)).sum()),
        "missing_rows": int(missing.sum()),
        "duplicated_rows": int(duplicated.sum()),
        "duplicate_assignment_slots": int(
            np.maximum(counts[expected] - 1, 0).sum(dtype=np.int64)
        ),
        "unexpected_rows": int(unexpected.sum()),
        "unexpected_assignment_slots": int(counts[~expected].sum(dtype=np.int64)),
        "expected_mask_identity": p1.mask_identity(expected),
        "assignment_count_identity": c4.array_identity(np.asarray(counts, dtype="<i8")),
        "missing_mask_identity": p1.mask_identity(missing),
        "duplicated_mask_identity": p1.mask_identity(duplicated),
        "unexpected_mask_identity": p1.mask_identity(unexpected),
    }
    observed_weight = math.fsum(float(value) for value in weights)
    residual = observed_weight - float(total_weight)
    scale = max(abs(observed_weight), abs(float(total_weight)), 1.0)
    tolerance = 4096.0 * float(np.spacing(scale))
    observed_rows = int(rows.sum(dtype=np.int64))
    row_count_pass = observed_rows == expected_rows
    row_assignment_link_pass = observed_rows == assignment_slots
    weight_pass = abs(residual) <= tolerance
    return {
        "status": (
            "PASS"
            if exact_once
            and row_count_pass
            and row_assignment_link_pass
            and weight_pass
            else "FAIL"
        ),
        "bin_row_count": observed_rows,
        "expected_row_count": expected_rows,
        "bin_row_count_matches_expected": row_count_pass,
        "bin_row_count_matches_assignment_slots": row_assignment_link_pass,
        "exact_once_assignment": assignment_certificate,
        "bin_weight_sum": observed_weight,
        "expected_weight_sum": float(total_weight),
        "weight_residual": residual,
        "weight_tolerance": tolerance,
        "weight_reduction_order_within_4096_ulps": weight_pass,
        "tolerance_basis": (
            "4096 binary64 ULPs at total-weight scale cover only alternate "
            "summation order; exact-once global row counts separately certify "
            "row identity"
        ),
    }


def decile_drift_closure(
    bin_drift_mass: np.ndarray,
    *,
    total_weight: float,
    expected_conditional: float,
) -> dict[str, Any]:
    """Compare regrouped decile drift with T2 on its natural weight scale."""
    masses = np.asarray(bin_drift_mass, dtype=np.float64)
    require(
        masses.shape == (10,)
        and np.isfinite(masses).all()
        and math.isfinite(total_weight)
        and total_weight > 0.0
        and math.isfinite(expected_conditional),
        "P5 decile drift closure inputs are malformed",
    )
    observed_mass = math.fsum(float(value) for value in masses)
    decile_drift = masses / total_weight
    observed_conditional = math.fsum(float(value) for value in decile_drift)
    residual = float(observed_conditional - expected_conditional)
    natural_scale = max(abs(float(total_weight)), 1.0)
    mass_tolerance = 4096.0 * float(np.spacing(natural_scale))
    conditional_tolerance = float(mass_tolerance / total_weight)
    within_tolerance = abs(residual) <= conditional_tolerance
    return {
        "status": "PASS" if within_tolerance else "FAIL",
        "decile_drift_mass_sum": observed_mass,
        "decile_drift_sum": observed_conditional,
        "conditional_T2": float(expected_conditional),
        "conditional_residual": residual,
        "mass_equivalent_residual": float(residual * total_weight),
        "natural_total_weight_scale": float(total_weight),
        "mass_tolerance": mass_tolerance,
        "conditional_tolerance": conditional_tolerance,
        "within_natural_scale_4096_ulps": within_tolerance,
        "tolerance_basis": (
            "4096 binary64 ULPs at total-weight scale divided by total weight; "
            "exact-once assignment is certified independently, so this allowance "
            "covers only binary64 reduction-order drift"
        ),
    }


def support_floor_passes(support: dict[str, Any]) -> bool:
    """Interpret the exact P1 support record without inventing a Boolean field."""
    status = support.get("status")
    require(
        status in {"SUPPORTED", "INSUFFICIENT_SUPPORT_NO_VERDICT"},
        "P5 received an invalid P1 support disposition",
    )
    return status == "SUPPORTED"


def work_estimate(
    d0: dict[str, Any],
    *,
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> dict[str, Any]:
    """Derive literal and safe identical-surface-cached work from D0."""
    literal_pairs = 0
    literal_costs = 0
    surfaces: dict[tuple[Any, ...], dict[str, int]] = {}
    largest: dict[str, Any] | None = None
    for target, target_spec in d0["D0-2"]["targets"].items():
        predictor_patterns = {
            row["name"]: row for row in d0["D0-7"]["targets"][target]["patterns"]
        }
        for pattern in target_spec["patterns"]:
            columns = tuple(
                predictor_patterns[pattern["name"]]["effective_gate_columns"]
            )
            pairs = int(pattern["donor_fit_rows"] * pattern["clone0_recipient_rows"])
            costs = int(pairs * len(columns))
            literal_pairs += pairs
            literal_costs += costs
            key = (
                target_spec["entity"],
                target_spec["stage"],
                pattern["name"],
                columns,
            )
            surfaces.setdefault(key, {"pairs": pairs, "costs": costs})
            if largest is None or pairs > largest["pairs"]:
                largest = {
                    "target": target,
                    "pattern": pattern["name"],
                    "donor_rows": pattern["donor_fit_rows"],
                    "recipient_rows": pattern["clone0_recipient_rows"],
                    "features": len(columns),
                    "pairs": pairs,
                    "full_distance_matrix_bytes": pairs * 8,
                }
    cached_pairs = sum(item["pairs"] for item in surfaces.values())
    cached_costs = sum(item["costs"] for item in surfaces.values())
    cached_projected = cached_costs / BENCHMARK["feature_pair_costs_per_second"]
    cached_conservative = cached_projected * BENCHMARK["conservative_multiplier"]
    literal_projected = literal_costs / BENCHMARK["feature_pair_costs_per_second"]
    literal_conservative = literal_projected * BENCHMARK["conservative_multiplier"]
    max_donors = max(
        pattern["donor_fit_rows"]
        for target in d0["D0-2"]["targets"].values()
        for pattern in target["patterns"]
    )
    require(block_size > 0, "P5 block size must be positive")
    scratch = block_size * max_donors * 8 * 3
    return {
        "literal_target_pattern_surfaces": 36,
        "literal_recipient_rows": sum(
            pattern["clone0_recipient_rows"]
            for target in d0["D0-2"]["targets"].values()
            for pattern in target["patterns"]
        ),
        "literal_pairwise_distances": literal_pairs,
        "literal_feature_pair_costs": literal_costs,
        "identical_metric_surfaces": len(surfaces),
        "cached_pairwise_distances": cached_pairs,
        "cached_feature_pair_costs": cached_costs,
        "largest_surface": largest,
        "benchmark": BENCHMARK,
        "projected_cached_kernel_seconds": cached_projected,
        "conservative_cached_kernel_seconds": cached_conservative,
        "conservative_cached_kernel_hours": cached_conservative / 3600.0,
        "projected_literal_kernel_seconds": literal_projected,
        "conservative_literal_kernel_seconds": literal_conservative,
        "conservative_literal_kernel_hours": literal_conservative / 3600.0,
        "default_block_scratch_upper_bound_bytes": scratch,
        "scratch_block_size": block_size,
        "disposition": (
            "MECHANICALLY_FEASIBLE_EXACT_UNDER_A8"
            if literal_conservative <= 20.0 * 3600.0
            else "NOT_RUN_PRIORITY_EXCEEDS_A8"
        ),
        "qualification": (
            "projection covers the distance/top-k kernel; checkpoint loading, "
            "36 exact gate restorations, probability evaluation, and report "
            "assembly are additional"
        ),
    }


def metric_cache_key(
    context: dict[str, Any],
    recipient_x: np.ndarray,
) -> tuple[str, dict[str, Any]]:
    """Hash every array that can affect a metric score."""
    payload = {
        "role": context["role_name"],
        "pattern": context["pattern"],
        "columns": list(context["columns"]),
        "donor_x": c4.array_identity(context["donor_x"]),
        "donor_weights": c4.array_identity(context["donor_weights"]),
        "recipient_x": c4.array_identity(recipient_x),
    }
    return canonical_sha256(payload), payload


def statistic_id(
    target: str,
    leg: str,
    row: str,
    *,
    decile: str = "_",
    variant: str = "_",
) -> str:
    return (
        f"r=candidate-25|t={target}|p=_|l={leg}|row={row}|g=_|prior=_|"
        f"gq=_|d={decile}|rep=_|fold=_|v={variant}"
    )


def statistic_fragment(
    target: str,
    leg: str,
    row: str,
    *,
    value: float | str,
    status: str,
    decile: str = "_",
    variant: str = "_",
    source_pointer: str,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": statistic_id(target, leg, row, decile=decile, variant=variant),
        "rung": "candidate-25",
        "target": target,
        "pattern": "_",
        "leg": leg,
        "row": row,
        "group": "_",
        "prior": "_",
        "gq": "_",
        "decile": decile,
        "repeat": "_",
        "fold": "_",
        "variant": variant,
        "record_type": "scalar",
        "family": None,
        "gated": False,
        "value": value,
        "se": "NA",
        "mcse": "NA",
        "status": status,
        "source": {
            "path": str(DESIGN),
            "sha256": DESIGN_SHA256,
            "pointer": source_pointer,
        },
        "sources": sources,
    }


def validate_manifest_fragments(
    statistics: list[dict[str, Any]],
    manifest_path: Path,
    targets: tuple[str, ...],
) -> dict[str, Any]:
    """Reject any P5 ID/static-field divergence from the sealed Step-0 roster."""
    require(
        sha256_file(manifest_path) == STEP0_MANIFEST_SHA256,
        "P5 requires the A18-adopted Step-0 manifest artifact",
    )
    payload = json.loads(manifest_path.read_text())
    p2.verify_self_canonical(payload, "P5 Step-0 manifest")
    manifest = payload.get("step0", {}).get("required_id_manifest")
    require(isinstance(manifest, list), "manifest JSON lacks the Step-0 ID list")
    target_set = set(targets)
    expected = {
        item["id"]: item
        for item in manifest
        if item.get("dimensions", {}).get("rung") == "candidate-25"
        and item.get("dimensions", {}).get("target") in target_set
        and item.get("dimensions", {}).get("row") in {"P5_decile", "P5_concentration"}
    }
    require(
        len(expected) == 62 * len(targets),
        "sealed manifest does not contain the complete requested P5 roster",
    )
    ids = [row["id"] for row in statistics]
    require(len(ids) == len(set(ids)), "P5 output contains duplicate statistic IDs")
    actual = set(ids)
    require(
        actual == set(expected),
        "P5 manifest mismatch: "
        f"missing={sorted(set(expected) - actual)[:10]}, "
        f"extra={sorted(actual - set(expected))[:10]}",
    )
    by_id = {row["id"]: row for row in statistics}
    static_mismatches: list[dict[str, Any]] = []
    for statistic_id_value, registered in expected.items():
        row = by_id[statistic_id_value]
        dimensions = registered["dimensions"]
        actual_static = {
            "family": row.get("family"),
            "gated": row.get("gated"),
            "record_type": row.get("record_type"),
            "dimensions": {
                "rung": row.get("rung"),
                "target": row.get("target"),
                "pattern": row.get("pattern"),
                "leg": row.get("leg"),
                "row": row.get("row"),
                "group": row.get("group"),
                "prior": row.get("prior"),
                "gq": row.get("gq"),
                "decile": row.get("decile"),
                "repeat": row.get("repeat"),
                "fold": row.get("fold"),
                "variant": row.get("variant"),
            },
            "status_allowed": row.get("status") in registered["allowed_statuses"],
        }
        expected_static = {
            "family": registered.get("family"),
            "gated": registered.get("gated"),
            "record_type": registered.get("record_type"),
            "dimensions": dimensions,
            "status_allowed": True,
        }
        if actual_static != expected_static:
            static_mismatches.append(
                {
                    "id": statistic_id_value,
                    "expected": expected_static,
                    "actual": actual_static,
                }
            )
    require(
        not static_mismatches,
        f"P5 manifest static-field mismatch: {static_mismatches[:5]}",
    )
    return {
        "status": "PASS",
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "fragment_count": len(ids),
        "ordered_ids_sha256": canonical_sha256(sorted(ids)),
        "static_fields_and_allowed_statuses_pass": True,
    }


def _leg_probability(
    probability_matrix: np.ndarray,
    classes: np.ndarray,
    sign: int,
) -> np.ndarray:
    match = np.flatnonzero(np.asarray(classes) == sign)
    if len(match) == 0:
        return np.zeros(len(probability_matrix), dtype=np.float64)
    require(len(match) == 1, "gate has a duplicated sign class")
    return np.asarray(probability_matrix[:, match[0]], dtype=np.float64)


def _target_t2(p1_payload: dict[str, Any], target: str, leg: str) -> dict[str, float]:
    result = p1_payload["candidate-25"]["targets"][target]
    t2 = result["P1"]["ledger"][leg]["rows"]["T2"]
    phi = float(result["P0"]["phi"])
    require(phi > 0.0, f"P5 has zero phi for {target}")
    return {"value": float(t2["value"]), "se": float(t2["se"]), "phi": phi}


def run_target(
    data: dict[str, Any],
    target: str,
    c0b_lookup: dict[tuple[str, str], dict[str, Any]],
    p1_payload: dict[str, Any],
    p1_path: Path,
    metric_cache: dict[str, dict[str, Any]],
    *,
    block_size: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, int]]:
    """Compute all P5 rows for one target."""
    target_started = time.monotonic()
    target_spec = data["target_specs"][target]
    role = data["roles"][c4.role_for_target(target_spec)]
    bank = data["current_banks"][target]
    raw_role = np.asarray(bank["raw"])[role["recipient_physical"]]
    sq = np.asarray(role["recipient_clone0"], dtype=bool) & np.isfinite(raw_role)
    weights_role = np.asarray(role["recipient_weights"], dtype=np.float64)
    total_weight = float(weights_role[sq].sum(dtype=np.float64))
    require(
        int(sq.sum()) == int(target_spec["clone0_recipient_rows"])
        and math.isclose(
            total_weight,
            float(target_spec["clone0_recipient_weight_sum"]),
            rel_tol=0.0,
            abs_tol=1e-7,
        ),
        f"P5 S_q does not match D0 for {target}",
    )

    bin_weight = np.zeros(10, dtype=np.float64)
    bin_rows = np.zeros(10, dtype=np.int64)
    bin_distance_mass = np.zeros(10, dtype=np.float64)
    bin_drift_mass = {leg: np.zeros(10, dtype=np.float64) for leg in LEGS}
    assignment_counts = np.zeros(len(sq), dtype=np.int64)
    patterns: list[dict[str, Any]] = []
    cache_counts = {"hits": 0, "misses": 0}

    for d0_pattern, pattern in zip(
        target_spec["patterns"], role["patterns"], strict=True
    ):
        pattern_name = pattern["name"]
        require(pattern_name == d0_pattern["name"], "P5 pattern order changed")
        context = c4.fit_gate_context(data, target, pattern_name, c0b_lookup)
        positions = pattern["positions"]
        pattern_sq = sq[positions]
        weights = weights_role[positions][pattern_sq]
        stable_ids = np.asarray(role["recipient_stable_id"])[positions][pattern_sq]
        recipient_all = p1._recipient_x(data, context, positions)
        recipient_probabilities = np.asarray(
            context["gate"].predict_proba(recipient_all), dtype=np.float64
        )
        adopted = c0b_lookup[(target, pattern_name)]
        require(
            c4.array_identity(recipient_probabilities)["sha256"]
            == adopted["recipient_gate_probability_matrix_sha256"],
            f"P5 recipient gate binding failed for {target}/{pattern_name}",
        )
        recipient_x = np.asarray(recipient_all[pattern_sq], dtype=np.float64)
        recipient_p = recipient_probabilities[pattern_sq]
        require(
            len(recipient_x) == int(d0_pattern["clone0_recipient_rows"]),
            f"P5 pattern S_q differs from D0 for {target}/{pattern_name}",
        )

        cache_key, cache_binding = metric_cache_key(context, recipient_x)
        if cache_key in metric_cache:
            cached = metric_cache[cache_key]
            scores = cached["scores"]
            metric = cached["metric"]
            diagnostic = {
                **cached["diagnostic"],
                "cache_hit": True,
                "first_target": cached["first_target"],
            }
            cache_counts["hits"] += 1
        else:
            metric = metric_definition(
                context["donor_x"], context["donor_weights"], context["columns"]
            )
            scores, diagnostic = exact_gower_knn_scores(
                context["donor_x"],
                recipient_x,
                metric,
                block_size=block_size,
                progress_label=f"{target}/{pattern_name}",
            )
            diagnostic["cache_hit"] = False
            metric_cache[cache_key] = {
                "scores": scores,
                "metric": metric,
                "diagnostic": diagnostic,
                "first_target": target,
            }
            cache_counts["misses"] += 1

        bins, bin_diagnostic = weighted_decile_bins(scores, stable_ids, weights)
        global_positions = np.asarray(positions, dtype=np.int64)[pattern_sq]
        require(
            len(global_positions) == len(bins)
            and (global_positions >= 0).all()
            and (global_positions < len(sq)).all(),
            f"P5 decile row identities differ for {target}/{pattern_name}",
        )
        np.add.at(assignment_counts, global_positions, 1)
        bin_rows += np.bincount(bins, minlength=10).astype(np.int64)
        bin_weight += np.bincount(bins, weights=weights, minlength=10)
        bin_distance_mass += np.bincount(bins, weights=weights * scores, minlength=10)
        legs: dict[str, Any] = {}
        for leg, sign in LEGS.items():
            donor_p = _leg_probability(
                context["donor_probabilities"], context["gate_classes"], sign
            )
            row_p = _leg_probability(recipient_p, context["gate_classes"], sign)
            donor_mean = float(
                np.dot(context["donor_weights"], donor_p)
                / np.asarray(context["donor_weights"]).sum(dtype=np.float64)
            )
            drift = donor_mean - row_p
            bin_drift_mass[leg] += np.bincount(
                bins, weights=weights * drift, minlength=10
            )
            p1_pattern = next(
                row
                for row in p1_payload["candidate-25"]["targets"][target]["P1"][
                    "pattern_rows"
                ]
                if row["pattern"] == pattern_name
            )
            expected_donor = float(p1_pattern["legs"][leg]["P_D"]["value"])
            expected_recipient = float(p1_pattern["legs"][leg]["P_R"]["value"])
            recipient_mean = float(
                np.dot(weights, row_p) / weights.sum(dtype=np.float64)
            )
            require(
                math.isclose(donor_mean, expected_donor, rel_tol=0.0, abs_tol=2e-15)
                and math.isclose(
                    recipient_mean, expected_recipient, rel_tol=0.0, abs_tol=2e-15
                ),
                f"P5 probability surface differs from P1 for {target}/{pattern_name}/{leg}",
            )
            legs[leg] = {
                "donor_pattern_mean": donor_mean,
                "recipient_pattern_mean": recipient_mean,
            }

        patterns.append(
            {
                "pattern": pattern_name,
                "columns": list(context["columns"]),
                "metric": metric,
                "metric_cache_key": cache_key,
                "metric_cache_binding": cache_binding,
                "distance_score_identity": c4.array_identity(scores),
                "distance": diagnostic,
                "deciles": bin_diagnostic,
                "legs": legs,
            }
        )

    partition_closure = decile_partition_closure(
        bin_weight,
        bin_rows,
        assignment_counts,
        sq,
        total_weight=total_weight,
    )
    require(
        partition_closure["status"] == "PASS",
        f"P5 decile partition does not close for {target}: "
        f"{json.dumps(partition_closure, sort_keys=True)}",
    )
    statistics: list[dict[str, Any]] = []
    legs_output: dict[str, Any] = {}
    p1_sha = sha256_file(p1_path)
    for leg in LEGS:
        t2 = _target_t2(p1_payload, target, leg)
        drift = bin_drift_mass[leg] / total_weight
        expected_conditional = t2["value"] / t2["phi"]
        drift_closure = decile_drift_closure(
            bin_drift_mass[leg],
            total_weight=total_weight,
            expected_conditional=expected_conditional,
        )
        require(
            drift_closure["status"] == "PASS",
            f"P5 decile drift does not close to P1 T2 for {target}/{leg}: "
            f"{json.dumps(drift_closure, sort_keys=True)}",
        )
        support = p1._support(data["d0"], target, leg)
        support_pass = support_floor_passes(support)
        row_status = "OK" if support_pass else "INSUFFICIENT_SUPPORT_NO_VERDICT"
        denominator = float(np.abs(drift).sum(dtype=np.float64))
        concentration_defined = denominator > 0.0 and abs(t2["value"]) > 2.0 * t2["se"]
        concentration: float | str = (
            float(abs(drift[9]) / denominator) if concentration_defined else "NA"
        )
        concentration_status = (
            row_status
            if concentration_defined or not support_pass
            else "NOT_APPLICABLE"
        )
        legs_output[leg] = {
            "support": support,
            "T2": t2,
            "decile_drift": drift.tolist(),
            "drift_sum": drift_closure["decile_drift_sum"],
            "conditional_T2": expected_conditional,
            "drift_closure": drift_closure,
            "absolute_drift_denominator": denominator,
            "concentration": concentration,
            "concentration_defined": concentration_defined,
            "concentration_ge_half": (
                bool(concentration >= 0.5) if isinstance(concentration, float) else "NA"
            ),
            "H5_requires_loaded_F1_T2_in_addition": True,
        }
        common_sources = [
            {
                "path": str(D0_JSON),
                "sha256": D0_SHA256,
                "pointer": f"/D0-2/targets/{target}",
            },
            {
                "path": str(p1_path),
                "sha256": p1_sha,
                "pointer": f"/candidate-25/targets/{target}/P1/ledger/{leg}/rows/T2",
            },
        ]
        for decile in range(10):
            decile_text = f"{decile:02d}"
            weight_share = float(bin_weight[decile] / total_weight)
            mean_distance: float | str = (
                float(bin_distance_mass[decile] / bin_weight[decile])
                if bin_weight[decile] > 0.0
                else "NA"
            )
            decile_status = row_status if bin_weight[decile] > 0.0 else "NOT_APPLICABLE"
            for variant, value in (
                ("drift", float(drift[decile])),
                ("mean_distance", mean_distance),
                ("weight", weight_share),
            ):
                statistics.append(
                    statistic_fragment(
                        target,
                        leg,
                        "P5_decile",
                        value=value,
                        status=decile_status,
                        decile=decile_text,
                        variant=variant,
                        source_pointer="/A16-35/A16-36",
                        sources=common_sources,
                    )
                )
        statistics.append(
            statistic_fragment(
                target,
                leg,
                "P5_concentration",
                value=concentration,
                status=concentration_status,
                source_pointer="/A16-36/A16-37",
                sources=common_sources,
            )
        )

    return (
        {
            "status": "COMPLETE",
            "target": target,
            "S_q_rows": int(sq.sum()),
            "S_q_weight": total_weight,
            "patterns": patterns,
            "pooled_deciles": {
                "rows": bin_rows.tolist(),
                "weight": bin_weight.tolist(),
                "weight_share": (bin_weight / total_weight).tolist(),
                "mean_distance": [
                    float(bin_distance_mass[i] / bin_weight[i])
                    if bin_weight[i] > 0.0
                    else "NA"
                    for i in range(10)
                ],
            },
            "decile_partition_closure": partition_closure,
            "legs": legs_output,
            "elapsed_seconds": time.monotonic() - target_started,
        },
        statistics,
        cache_counts,
    )


def run(
    *,
    d0_path: Path,
    adoption_path: Path,
    c3_path: Path,
    c4_path: Path,
    c0b_path: Path,
    p1_path: Path,
    manifest_path: Path,
    targets: tuple[str, ...],
    block_size: int,
) -> dict[str, Any]:
    """Run P5 for the requested ordered target subset."""
    started = time.monotonic()
    require(sha256_file(DESIGN) == DESIGN_SHA256, "design digest changed")
    require(sha256_file(D0_JSON) == D0_SHA256, "D0 digest changed")
    require(sha256_file(A16_BINDING) == A16_SHA256, "A16 binding digest changed")
    require(d0_path.resolve() == D0_JSON.resolve(), "P5 requires the ratified D0 path")
    require(
        len(targets) > 0 and len(set(targets)) == len(targets),
        "target subset is empty/duplicated",
    )
    require(
        list(targets) == [target for target in TARGETS if target in targets],
        "P5 target subset must preserve registered order",
    )
    p2.verify_reading_prerequisites(adoption_path, c3_path, c4_path, c0b_path)
    p1_payload = verify_p1_artifact(p1_path, c0b_path)
    d0 = json.loads(d0_path.read_text())
    input_verification = p1._verify_inputs(
        d0,
        d0_path,
        c0b_path,
        include_baseline=False,
    )
    estimate = work_estimate(d0, block_size=block_size)
    require(
        estimate["disposition"] == "MECHANICALLY_FEASIBLE_EXACT_UNDER_A8",
        "exact P5 exceeds the A8 execution budget under the sealed estimate",
    )
    c0b_payload = json.loads(c0b_path.read_text())
    lookup = p1._c0b_lookup(c0b_payload)
    data = c4.load_analysis_data(d0)
    metric_cache: dict[str, dict[str, Any]] = {}
    target_results: dict[str, Any] = {}
    statistics: list[dict[str, Any]] = []
    cache_counts = {"hits": 0, "misses": 0}
    for target in targets:
        result, fragments, target_cache = run_target(
            data,
            target,
            lookup,
            p1_payload,
            p1_path,
            metric_cache,
            block_size=block_size,
        )
        target_results[target] = result
        statistics.extend(fragments)
        for name in cache_counts:
            cache_counts[name] += target_cache[name]
        print(
            json.dumps(
                {
                    "P5_target_complete": target,
                    "elapsed_seconds": result["elapsed_seconds"],
                    "cache": target_cache,
                },
                sort_keys=True,
            ),
            flush=True,
        )
    statistics.sort(key=lambda row: row["id"])
    require(len(statistics) == 62 * len(targets), "P5 manifest fragment count changed")
    manifest_validation = validate_manifest_fragments(
        statistics,
        manifest_path,
        targets,
    )
    source_paths = (
        Path(__file__),
        Path(c4.__file__),
        Path(p1.__file__),
        Path(p2.__file__),
        Path(p1.replay.__file__),
    )
    source_files = [
        {
            "path": str(path.resolve()),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in source_paths
    ]
    payload = {
        "artifact_kind": "qrf_drift_phase0_a18_p5",
        "schema_version": 1,
        "status": "COMPLETE" if targets == TARGETS else "COMPLETE_TARGET_SUBSET",
        "authority": {
            "design": {"path": str(DESIGN), "sha256": DESIGN_SHA256},
            "D0": {"path": str(D0_JSON), "sha256": D0_SHA256},
            "A16_binding": {"path": str(A16_BINDING), "sha256": A16_SHA256},
            "adoption": {
                "path": str(adoption_path),
                "sha256": sha256_file(adoption_path),
            },
            "C3": {"path": str(c3_path), "sha256": sha256_file(c3_path)},
            "C4": {"path": str(c4_path), "sha256": sha256_file(c4_path)},
            "C0b": {"path": str(c0b_path), "sha256": sha256_file(c0b_path)},
            "P1": {"path": str(p1_path), "sha256": sha256_file(p1_path)},
            "Step0_manifest": {
                "path": str(manifest_path),
                "sha256": sha256_file(manifest_path),
            },
        },
        "input_verification": input_verification,
        "source_files": source_files,
        "manifest_validation": manifest_validation,
        "scope": {
            "rung": "candidate-25",
            "targets": list(targets),
            "k": K_NEIGHBOURS,
            "effective_columns": "D0-7 base plus present priors",
            "numeric": "fit-weighted inverse-CDF IQR; capped absolute distance",
            "categorical": sorted(CATEGORICAL_COLUMNS),
            "nearest": "exact all-donor search; equal neighbour weights",
            "cutoff_tie_implementation": (
                "A16-34 identity choice is not materialized because the reported "
                "arithmetic mean depends only on the k smallest binary64 distance "
                "values; every identity tied at the cutoff has that exact value"
            ),
            "cutoff_tie_score_equivalence": "EXACT",
            "deciles": "A16-35 weighted midpoint bins within pattern, pooled by rank",
            "concentration": "A16-36; F3 retired by A16-37",
        },
        "feasibility": estimate,
        "targets": target_results,
        "statistics": statistics,
        "execution": {
            "elapsed_seconds": time.monotonic() - started,
            "peak_rss_mb": peak_rss_mb(),
            "block_size": block_size,
            "metric_cache": cache_counts,
            "metric_cache_entries": len(metric_cache),
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d0", type=Path, default=D0_JSON)
    parser.add_argument("--adoption", type=Path, default=DEFAULT_ADOPTION)
    parser.add_argument("--c3", type=Path, default=DEFAULT_C3)
    parser.add_argument("--c4", type=Path, default=DEFAULT_C4)
    parser.add_argument("--c0b", type=Path, default=DEFAULT_C0B)
    parser.add_argument("--p1", type=Path, default=DEFAULT_P1)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--block-size", type=int, default=DEFAULT_BLOCK_SIZE)
    parser.add_argument(
        "--targets",
        nargs="+",
        choices=TARGETS,
        default=list(TARGETS),
        help="ordered registered target subset; defaults to all nine",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = run(
        d0_path=args.d0.resolve(),
        adoption_path=args.adoption.resolve(),
        c3_path=args.c3.resolve(),
        c4_path=args.c4.resolve(),
        c0b_path=args.c0b.resolve(),
        p1_path=args.p1.resolve(),
        manifest_path=args.manifest.resolve(),
        targets=tuple(args.targets),
        block_size=args.block_size,
    )
    output_sha256 = c4.write_canonical_result(args.out, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "out": str(args.out),
                "sha256": output_sha256,
                "canonical_sha256": payload["canonical_sha256"],
                "statistics": len(payload["statistics"]),
                "elapsed_seconds": payload["execution"]["elapsed_seconds"],
                "peak_rss_mb": payload["execution"]["peak_rss_mb"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
