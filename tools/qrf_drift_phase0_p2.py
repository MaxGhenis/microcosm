#!/usr/bin/env python3
"""Run the A18-authorized Phase-0 P2 incidence-gate reading.

The executor restores the C0b-bound production gates, evaluates all eight
G1/G2/G3 hot-deck coalitions on the registered A8 recipient samples, and
subtracts the paired C4 exchangeability baseline replicate by replicate.  It
also emits the full-row A16-31 marginal audit.  Magnitude forests are neither
loaded nor refit.

The output is resumable at target boundaries.  A run may therefore execute the
six priority targets first and append the remaining targets later with
``--resume`` while preserving the registered D0 target order.
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
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import numpy as np
import qrf_drift_phase0_a18_g3_splits as a18_enumeration
import qrf_drift_phase0_c4 as c4
import qrf_drift_phase0_replay as replay
import sklearn

WORKTREE = Path(__file__).resolve().parents[1]
DESIGN_MD = WORKTREE / "experiments/qrf_drift_validation_design.md"
D0_JSON = WORKTREE / "experiments/qrf_drift_validation_d0.json"
A16_BINDING = WORKTREE / "experiments/qrf_drift_validation_a16_binding_texts.md"

DEFAULT_ADOPTION = Path("/private/tmp/qrf_phase0_a18_adoption.json")
DEFAULT_C3 = Path("/private/tmp/qrf_phase0_a18_c3.json")
DEFAULT_C0B = Path("/private/tmp/qrf_phase0_v22_c0b.json")
DEFAULT_C4 = Path("/private/tmp/qrf_phase0_a17_c4.json")
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_a18_p2.json")

INITIAL_REPLICATES = 250
ESCALATED_REPLICATES = 1_000
GROUPS = ("G1", "G2", "G3")
LEGS = ("positive", "negative")
CLASS_BY_LEG = {"negative": -1, "positive": 1}
CLOSURE_ROWS = ("e_D", "e_R", "e_T")
P2_ROWS = {
    "P2_group_pattern",
    "P2_group_aggregate",
    "P2_prior_pattern",
    "P2_marginal_audit",
    "P2_escalation",
    *CLOSURE_ROWS,
}
DESIGN_SHA256 = "5c8e55293215a7d1350c93825b1a4daf04e212bb84d17408b8750ed5d9d4e754"
A18_COMMIT = "8d553796e846012e7dc2663d7ffe108b6f965cca"
SUPPORT_FLOOR = 50


def require(condition: bool, message: str) -> None:
    """Raise a uniform fail-closed error."""
    if not condition:
        raise ValueError(message)


def canonical_sha256(value: Any) -> str:
    """Hash a JSON-safe value with the sealed Phase-0 encoder."""
    return hashlib.sha256(c4.canonical_bytes(value)).hexdigest()


def verify_self_canonical(payload: dict[str, Any], label: str) -> str:
    """Verify an artifact's self-excluding canonical payload digest."""
    recorded = payload.get("canonical_sha256")
    scope = dict(payload)
    scope.pop("canonical_sha256", None)
    actual = canonical_sha256(scope)
    require(recorded == actual, f"{label} canonical payload seal mismatch")
    return actual


def _finite_or_string(value: float) -> float | str:
    value = float(value)
    if math.isnan(value):
        return "NA"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    return 0.0 if value == 0.0 else value


def _array_payload(values: np.ndarray) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "values": array.tolist(),
        "identity": c4.array_identity(array),
    }


def statistic_id(
    target: str,
    *,
    pattern: str = "_",
    leg: str = "_",
    row: str,
    group: str = "_",
    prior: str = "_",
    variant: str = "_",
) -> str:
    """Build one ID in the sealed A16-55 dimension grammar."""
    return (
        f"r=candidate-25|t={target}|p={pattern}|l={leg}|row={row}|"
        f"g={group}|prior={prior}|gq=_|d=_|rep=_|fold=_|v={variant}"
    )


def statistic_fragment(
    *,
    target: str,
    pattern: str = "_",
    leg: str = "_",
    row: str,
    group: str = "_",
    prior: str = "_",
    variant: str = "_",
    value: float | str,
    se: float | str = "NA",
    mcse: float | str = "NA",
    family: str | None = None,
    gated: bool = False,
    status: str,
    source_pointer: str,
) -> dict[str, Any]:
    """Return a current-manifest-compatible scalar fragment."""
    return {
        "id": statistic_id(
            target,
            pattern=pattern,
            leg=leg,
            row=row,
            group=group,
            prior=prior,
            variant=variant,
        ),
        "rung": "candidate-25",
        "target": target,
        "pattern": pattern,
        "leg": leg,
        "row": row,
        "group": group,
        "prior": prior,
        "variant": variant,
        "value": value,
        "se": se,
        "mcse": mcse,
        "family": family,
        "gated": gated,
        "status": status,
        "source": {
            "pointer": source_pointer,
            "design_sha256": DESIGN_SHA256,
            "d0_sha256": a18_enumeration.EXPECTED_AUTHORITY_DIGESTS[
                str(a18_enumeration.D0_JSON)
            ],
        },
    }


def verify_reading_prerequisites(
    adoption_path: Path,
    c3_path: Path,
    c4_path: Path,
    c0b_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Verify the sealed A18 adoption and fresh passing branch-2 C3."""
    adoption = json.loads(adoption_path.read_text())
    c3_payload = json.loads(c3_path.read_text())
    c4_payload = json.loads(c4_path.read_text())
    c0b_payload = json.loads(c0b_path.read_text())
    verify_self_canonical(adoption, "A18 adoption")
    verify_self_canonical(c3_payload, "A18 C3")
    verify_self_canonical(c4_payload, "adopted C4")

    require(
        adoption.get("artifact_kind") == "qrf_drift_phase0_a18_branch2_adoption"
        and adoption.get("status") == "SEALED_ADOPTION",
        "A18 branch-2 adoption is not sealed",
    )
    adoption_authority = adoption.get("authority", {})
    require(
        adoption_authority.get("commit") == A18_COMMIT
        and adoption_authority.get("commit_design_blob_sha256") == DESIGN_SHA256
        and any(
            item.get("sha256") == DESIGN_SHA256 and item.get("match") is True
            for item in adoption_authority.get("files", [])
        ),
        "A18 adoption does not bind the operative design",
    )
    require(
        adoption.get("branch2", {}).get("branch") == 2
        and adoption.get("readings_authorized") is False,
        "A18 adoption is not the pre-C3 branch-2 disposition",
    )
    adopted = adoption.get("controls", {}).get("adopted_controls", {})
    for name in ("C0a", "C0b", "C5", "A17_setup", "C4", "C2"):
        require(
            str(adopted.get(name, {}).get("status", "")).startswith("PASS"),
            f"A18 adoption lacks passing {name}",
        )

    require(
        c3_payload.get("artifact_kind") == "qrf_drift_phase0_a18_c3"
        and c3_payload.get("status") == "PASS",
        "fresh retargeted C3 is not PASS",
    )
    c3_control = c3_payload.get("control", {})
    c3_summary = c3_payload.get("summary", {})
    require(
        c3_control.get("status") == "PASS"
        and c3_control.get("pass") is True
        and c3_control.get("group_recoveries_pass") is True
        and c3_control.get("power", {}).get("pass") is True,
        "fresh retargeted C3 recovery or power did not pass",
    )
    require(
        c3_summary.get("rerun_C3_status") == "PASS"
        and c3_summary.get("all_three_recoveries_pass") is True
        and c3_summary.get("power_check_pass") is True
        and c3_summary.get("terminal_gated_disposition") == "PROCEED",
        "fresh C3 summary does not authorize readings",
    )
    require(
        c3_payload.get("authority", {}).get("design", {}).get("sha256")
        == DESIGN_SHA256,
        "fresh C3 does not bind the operative design",
    )
    require(
        c3_payload.get("scope", {}).get("selection")
        == adoption.get("branch2", {}).get("selected"),
        "fresh C3 selection differs from the sealed adoption",
    )

    c4_sha = c4.sha256_file(c4_path)
    c0b_sha = c4.sha256_file(c0b_path)
    require(
        c4_payload.get("status") == "PASS"
        and c4_payload.get("summary", {}).get("all_run_cells_pass") is True
        and c4_payload.get("summary", {}).get("gated_cells_run") == 40,
        "adopted C4 is not the full 40-cell PASS",
    )
    require(
        all(item.get("pass") is True for item in c4_payload.get("statistics", [])),
        "adopted C4 contains a failed statistic",
    )
    require(
        c3_payload.get("adopted_controls", {}).get("C4", {}).get("sha256") == c4_sha,
        "fresh C3 does not bind the supplied C4 artifact",
    )
    require(
        c3_payload.get("authority", {}).get("adopted_c0b", {}).get("sha256") == c0b_sha,
        "fresh C3 does not bind the supplied C0b artifact",
    )
    require(
        c0b_payload.get("status") == "PASS"
        and c0b_payload.get("summary", {}).get("e4_bit_identical_pass") is True
        and c0b_payload.get("summary", {}).get("e2_repeated_draw_control_pass") is True,
        "adopted C0b is not a clean E4/E2 pass",
    )
    return adoption, c3_payload, c4_payload, c0b_payload


def combine_stratum_means(
    values: np.ndarray,
    slices: Iterable[dict[str, Any]],
) -> np.ndarray:
    """Combine unit-weight stratum means with exact registered shares."""
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim == 1:
        matrix = matrix[:, None]
    result = np.zeros(matrix.shape[1], dtype=np.float64)
    share_sum = 0.0
    for item in slices:
        start = int(item["start"])
        stop = int(item["stop"])
        share = float(item["exact_weight_share"])
        require(stop > start, "positive-mass stratum has no sampled rows")
        result += share * matrix[start:stop].mean(axis=0)
        share_sum += share
    require(
        math.isclose(share_sum, 1.0, rel_tol=0.0, abs_tol=2e-15),
        f"stratum shares do not sum to one: {share_sum}",
    )
    return result


def stratum_slices(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert one pattern's positive-mass plan to contiguous sample slices."""
    result: list[dict[str, Any]] = []
    start = 0
    for item in plan:
        count = int(item["allocation"])
        if count <= 0:
            continue
        result.append(
            {
                "gq": item["gq"],
                "start": start,
                "stop": start + count,
                "allocation": count,
                "exact_weight_share": float(item["exact_pattern_share"]),
            }
        )
        start += count
    return result


def shapley_from_coalitions(coalitions: np.ndarray) -> np.ndarray:
    """Compute exact three-player Shapley values along mask axis 0..7."""
    values = np.asarray(coalitions, dtype=np.float64)
    require(values.shape[-1] == 8, "coalition mask axis must have length eight")
    result = np.zeros((*values.shape[:-1], 3), dtype=np.float64)
    for group_position, group in enumerate(GROUPS):
        bit = c4.GROUP_BITS[group]
        others = [other for other in (1, 2, 4) if other != bit]
        for subset in range(8):
            if subset & bit:
                continue
            subset_size = int(bool(subset & others[0])) + int(bool(subset & others[1]))
            coefficient = 1.0 / 3.0 if subset_size in {0, 2} else 1.0 / 6.0
            result[..., group_position] += coefficient * (
                values[..., subset | bit] - values[..., subset]
            )
    return result


def evaluate_coalitions(
    base_x: np.ndarray,
    substitution_x: np.ndarray,
    group_indexes: dict[str, np.ndarray],
    predict_proba: Callable[[np.ndarray], np.ndarray],
    mean_function: Callable[[np.ndarray], np.ndarray],
    *,
    known_empty: np.ndarray | None = None,
    known_all: np.ndarray | None = None,
) -> np.ndarray:
    """Evaluate all eight coalitions, duplicating only empty feature groups."""
    base = np.asarray(base_x, dtype=np.float64)
    substitution = np.asarray(substitution_x, dtype=np.float64)
    require(base.shape == substitution.shape, "paired coalition matrices differ")
    means: list[np.ndarray] = []
    for mask in range(8):
        if mask == 0 and known_empty is not None:
            means.append(np.asarray(known_empty, dtype=np.float64))
            continue
        if mask == 7 and known_all is not None:
            means.append(np.asarray(known_all, dtype=np.float64))
            continue
        hybrid = base.copy()
        for group in GROUPS:
            if mask & c4.GROUP_BITS[group]:
                indexes = np.asarray(group_indexes[group], dtype=np.int64)
                if len(indexes):
                    hybrid[:, indexes] = substitution[:, indexes]
        means.append(mean_function(np.asarray(predict_proba(hybrid))))
    return np.stack(means, axis=1)


def evaluate_per_prior(
    base_x: np.ndarray,
    substitution_x: np.ndarray,
    columns: tuple[str, ...],
    prior_names: tuple[str, ...],
    predict_proba: Callable[[np.ndarray], np.ndarray],
    mean_function: Callable[[np.ndarray], np.ndarray],
    empty_mean: np.ndarray,
) -> dict[str, np.ndarray]:
    """Evaluate A1 one-at-a-time prior marginals from the common donor row."""
    result: dict[str, np.ndarray] = {}
    for prior in prior_names:
        hybrid = np.asarray(base_x, dtype=np.float64).copy()
        position = columns.index(prior)
        hybrid[:, position] = substitution_x[:, position]
        result[prior] = mean_function(np.asarray(predict_proba(hybrid))) - empty_mean
    return result


def mc_summary(values: np.ndarray) -> dict[str, Any]:
    """Summarize a registered replicate vector with A15.9 MCSE."""
    vector = np.asarray(values, dtype=np.float64)
    require(vector.ndim == 1 and len(vector) >= 2, "MC vector needs >=2 values")
    estimate = float(vector.mean())
    sd = float(vector.std(ddof=1))
    mcse = sd / math.sqrt(len(vector))
    if mcse > 0.0:
        ratio: float | str = abs(estimate) / mcse
        trigger = 2.0 <= ratio <= 4.0
    elif estimate == 0.0:
        ratio = 0.0
        trigger = False
    else:
        ratio = "inf"
        trigger = False
    return {
        "value": estimate,
        "replicate_sd": sd,
        "mcse": mcse,
        "abs_value_over_mcse": ratio,
        "replicates": len(vector),
        "escalation_trigger": trigger,
        "replicate_values_identity": c4.array_identity(vector),
    }


def reading_escalation_decision(
    vectors: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Apply the one-time [2,4] trigger to one target-pattern-leg roster."""
    summaries = {name: mc_summary(values) for name, values in vectors.items()}
    triggers = [
        name for name, summary in summaries.items() if summary["escalation_trigger"]
    ]
    finite_ratios = [
        float(summary["abs_value_over_mcse"])
        for summary in summaries.values()
        if summary["abs_value_over_mcse"] != "inf"
    ]
    return {
        "trigger": bool(triggers),
        "triggered_statistics": triggers,
        "max_abs_value_over_mcse": max(finite_ratios, default=0.0),
        "statistics": summaries,
    }


def weighted_moments(values: np.ndarray, weights: np.ndarray) -> dict[str, float]:
    """Return A16-31 weighted population moments and Kish effective n."""
    x = np.asarray(values, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)
    require(
        x.ndim == w.ndim == 1 and len(x) == len(w) and len(x) > 0,
        "weighted moments require aligned nonempty vectors",
    )
    require(
        np.isfinite(x).all() and np.isfinite(w).all() and (w > 0.0).all(),
        "weighted moments received nonfinite/nonpositive inputs",
    )
    weight_sum = float(w.sum(dtype=np.float64))
    weight_sum_squares = float(np.dot(w, w))
    mean = float(np.dot(w, x) / weight_sum)
    variance = float(np.dot(w, (x - mean) ** 2) / weight_sum)
    effective_n = weight_sum * weight_sum / weight_sum_squares
    return {
        "rows": len(x),
        "weight_sum": weight_sum,
        "weight_sum_squares": weight_sum_squares,
        "kish_effective_n": effective_n,
        "mean": mean,
        "variance": variance,
        "mean_se": math.sqrt(max(variance, 0.0) / effective_n),
    }


def standardized_difference(
    recipient: dict[str, float],
    donor: dict[str, float],
) -> float:
    """Apply the binding A16-31 pooled weighted-variance SMD formula."""
    difference = recipient["mean"] - donor["mean"]
    scale = math.sqrt((recipient["variance"] + donor["variance"]) / 2.0)
    if scale > 0.0:
        return difference / scale
    if difference == 0.0:
        return 0.0
    return math.copysign(math.inf, difference)


def difference_se(
    recipient: dict[str, float],
    donor: dict[str, float],
) -> float:
    """Apply A16-31's independent two-sample Kish difference SE."""
    return math.sqrt(
        recipient["variance"] / recipient["kish_effective_n"]
        + donor["variance"] / donor["kish_effective_n"]
    )


def categorical_feature(name: str) -> bool:
    """Return the frozen transfer semantics used for categorical detail."""
    return (
        name == "is_female"
        or name.endswith("_is_household_head")
        or name.endswith("_state_fips")
        or name.endswith("_tenure_code")
    )


def registered_categories(
    name: str,
    donor: np.ndarray,
    recipient: np.ndarray,
) -> tuple[list[float], str]:
    """Return deterministic semantic levels and disclose their provenance."""
    observed = sorted(
        float(value) for value in np.unique(np.concatenate((donor, recipient)))
    )
    if name == "is_female" or name.endswith("_is_household_head"):
        base = [0.0, 1.0]
        source = "production semantic boolean order 0,1"
    elif name.endswith("_tenure_code"):
        base = [0.0, 1.0, 2.0, 3.0]
        source = "production replay.TENURE_CODES numeric order"
    else:
        base = observed
        source = (
            "ascending observed FIPS; D0 orders the feature but does not "
            "enumerate category levels"
        )
    extras = [value for value in observed if value not in base]
    return [*base, *extras], source


def marginal_audit(
    donor_values: np.ndarray,
    donor_weights: np.ndarray,
    recipient_values: np.ndarray,
    recipient_weights: np.ndarray,
    *,
    feature: str,
    categories: list[float] | None = None,
) -> dict[str, Any]:
    """Compute the full A16-31 numeric and categorical marginal evidence."""
    donor = np.asarray(donor_values, dtype=np.float64)
    recipient = np.asarray(recipient_values, dtype=np.float64)
    donor_stats = weighted_moments(donor, donor_weights)
    recipient_stats = weighted_moments(recipient, recipient_weights)
    categorical = categories is not None or categorical_feature(feature)

    if categorical:
        if categories is None:
            category_order, category_source = registered_categories(
                feature, donor, recipient
            )
        else:
            category_order = [float(value) for value in categories]
            category_source = "caller-supplied registered fixture order"
        category_rows: list[dict[str, Any]] = []
        for category in category_order:
            donor_indicator = (donor == category).astype(np.float64)
            recipient_indicator = (recipient == category).astype(np.float64)
            donor_level = weighted_moments(donor_indicator, donor_weights)
            recipient_level = weighted_moments(recipient_indicator, recipient_weights)
            category_rows.append(
                {
                    "category": category,
                    "donor": donor_level,
                    "recipient": recipient_level,
                    "difference": recipient_level["mean"] - donor_level["mean"],
                    "smd": _finite_or_string(
                        standardized_difference(recipient_level, donor_level)
                    ),
                    "difference_se": difference_se(recipient_level, donor_level),
                }
            )
        donor_support = set(float(value) for value in np.unique(donor))
        violation = np.asarray(
            [float(value) not in donor_support for value in recipient],
            dtype=np.float64,
        )
    else:
        category_rows = []
        category_order = []
        category_source = "not categorical"
        low = float(donor.min())
        high = float(donor.max())
        violation = ((recipient < low) | (recipient > high)).astype(np.float64)

    recipient_weight_sum = float(np.sum(recipient_weights, dtype=np.float64))
    violation_share = float(np.dot(recipient_weights, violation) / recipient_weight_sum)
    return {
        "feature": feature,
        "feature_kind": "categorical" if categorical else "numeric",
        "donor": donor_stats,
        "recipient": recipient_stats,
        "difference": recipient_stats["mean"] - donor_stats["mean"],
        "smd": _finite_or_string(standardized_difference(recipient_stats, donor_stats)),
        "difference_se": difference_se(recipient_stats, donor_stats),
        "categories": category_rows,
        "category_order": category_order,
        "category_order_source": category_source,
        "one_feature_recipient_outside_donor_support_share": violation_share,
        "donor_copied_substitution_outside_donor_support_share": 0.0,
        "donor_copied_zero_basis": (
            "every substituted value is selected from this feature's donor row"
        ),
        "donor_values_identity": c4.array_identity(donor),
        "recipient_values_identity": c4.array_identity(recipient),
        "donor_weights_identity": replay.weight_identity(donor_weights),
        "recipient_weights_identity": replay.weight_identity(recipient_weights),
    }


def _find_prior_bank(
    data: dict[str, Any],
    context: dict[str, Any],
    prior: str,
) -> dict[str, Any]:
    """Resolve a chained recipient input to its position-aligned raw bank."""
    current_descriptor = context["bank"]["metadata"]["target"]
    current_directory = Path(context["bank"]["path"]).resolve().parent
    candidates: list[dict[str, Any]] = []
    for bank in data["bank_cache"].values():
        if Path(bank["path"]).resolve().parent != current_directory:
            continue
        descriptor = bank["metadata"]["target"]
        if descriptor.get("model_target") != prior:
            continue
        if descriptor.get("entity") != current_descriptor.get("entity"):
            continue
        if descriptor.get("family") != current_descriptor.get("family"):
            continue
        candidates.append(bank)
    if not candidates:
        path = replay.find_bank_for_target(current_directory, prior)
        candidates.append(replay.load_bank(path, data["bank_cache"]))
    require(
        len(candidates) == 1,
        f"expected one raw prior bank for {context['target']}/{prior}, got "
        f"{[str(item['path']) for item in candidates]}",
    )
    return candidates[0]


def recipient_pattern_data(
    data: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Recover the stable, full-row S_q gate input matrix for one pattern."""
    role = context["role"]
    pattern = next(
        item for item in role["patterns"] if item["name"] == context["pattern"]
    )
    positions = pattern["positions"]
    physical = role["recipient_physical"][positions]
    sq = role["recipient_clone0"][positions] & np.isfinite(
        context["bank"]["raw"][physical]
    )
    selected_positions = positions[sq]
    selected_physical = physical[sq]
    columns: list[np.ndarray] = []
    prior_sources: dict[str, Any] = {}
    for name in context["columns"]:
        if name in role["recipient_surface"]:
            values = role["recipient_surface"][name][selected_positions]
        else:
            bank = _find_prior_bank(data, context, name)
            values = bank["raw"][selected_physical]
            prior_sources[name] = {
                "path": str(Path(bank["path"]).resolve()),
                "sha256": c4.sha256_file(Path(bank["path"])),
                "raw_draw_sha256": bank["metadata"]["raw_draw_sha256"],
            }
        columns.append(np.asarray(values, dtype=np.float64))
    x = np.column_stack(columns)
    weights = np.asarray(
        role["recipient_weights"][selected_positions], dtype=np.float64
    )
    stable_ids = np.asarray(role["recipient_stable_id"][selected_positions])
    gq = c4._gq_key(role["recipient_gq"][selected_positions])
    order = np.argsort(stable_ids, kind="stable")
    x = x[order]
    weights = weights[order]
    stable_ids = stable_ids[order]
    gq = gq[order]
    require(
        len(x) == context["d0_pattern"]["clone0_recipient_rows"],
        f"S_q row mismatch for {context['target']}/{context['pattern']}",
    )
    require(
        np.isfinite(x).all() and np.isfinite(weights).all() and (weights > 0.0).all(),
        f"invalid recipient gate inputs for {context['target']}/{context['pattern']}",
    )
    return {
        "x": x,
        "weights": weights,
        "stable_ids": stable_ids,
        "gq": gq,
        "prior_sources": prior_sources,
        "x_identity": c4.array_identity(x),
        "weight_identity": replay.weight_identity(weights),
        "stable_id_identity": c4.array_identity(stable_ids),
    }


def pattern_sampling_plan(
    allocation: dict[str, Any],
    recipient: dict[str, Any],
    pattern: str,
) -> list[dict[str, Any]]:
    """Bind registered allocations to stable recipient rows and PPS vectors."""
    rows = [
        item
        for item in allocation["strata"]
        if item["pattern"] == pattern and item["weight_sum"] > 0.0
    ]
    pattern_weight = math.fsum(float(item["weight_sum"]) for item in rows)
    plan: list[dict[str, Any]] = []
    for item in rows:
        gq = item["gq"]
        indexes = np.flatnonzero(recipient["gq"] == gq)
        weights = recipient["weights"][indexes]
        require(
            len(indexes) == item["row_count"]
            and math.isclose(
                float(weights.sum(dtype=np.float64)),
                float(item["weight_sum"]),
                rel_tol=0.0,
                abs_tol=1e-8,
            ),
            f"recipient stratum mismatch for {pattern}/{gq}",
        )
        probabilities = weights / weights.sum(dtype=np.float64)
        probabilities[-1] += 1.0 - probabilities.sum(dtype=np.float64)
        plan.append(
            {
                "pattern": pattern,
                "gq": gq,
                "row_count": len(indexes),
                "weight_sum": float(item["weight_sum"]),
                "allocation": int(item["allocation"]),
                "exact_target_share": float(item["exact_weight_share"]),
                "exact_pattern_share": float(item["weight_sum"]) / pattern_weight,
                "indexes": indexes,
                "probabilities": probabilities,
                "stable_entity_id_identity": item["stable_entity_id_identity"],
            }
        )
    require(
        math.isclose(
            math.fsum(item["exact_pattern_share"] for item in plan),
            1.0,
            rel_tol=0.0,
            abs_tol=2e-15,
        ),
        f"pattern GQ shares do not close for {pattern}",
    )
    return plan


def sample_recipient_rows(
    target: str,
    pattern: str,
    replicate: int,
    plan: list[dict[str, Any]],
) -> np.ndarray:
    """Draw every positive pattern×GQ stratum from its literal child stream."""
    parts: list[np.ndarray] = []
    for item in plan:
        local = c4.weighted_choice(
            c4.p2_rows_label(target, pattern, item["gq"], replicate),
            item["probabilities"],
            item["allocation"],
        )
        parts.append(item["indexes"][local])
    return np.concatenate(parts).astype(np.int64, copy=False)


def evaluate_replicate(
    context: dict[str, Any],
    recipient: dict[str, Any],
    plan: list[dict[str, Any]],
    replicate: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate paired real/null coalitions and A1 priors for one replicate."""
    sample_size = sum(int(item["allocation"]) for item in plan)
    rows = sample_recipient_rows(context["target"], context["pattern"], replicate, plan)
    donor = c4.weighted_choice(
        c4.donor_label(context["target"], context["pattern"], replicate),
        context["donor_choice_probabilities"],
        sample_size,
    )
    r0 = c4.weighted_choice(
        c4.r0_label(context["target"], context["pattern"], replicate),
        context["donor_choice_probabilities"],
        sample_size,
    )
    base_x = recipient["x"][rows]
    donor_x = context["donor_x"][donor]
    slices = stratum_slices(plan)

    def real_mean(probabilities: np.ndarray) -> np.ndarray:
        return combine_stratum_means(probabilities, slices)

    real_empty = real_mean(context["gate"].predict_proba(base_x))
    real_all = real_mean(context["donor_probabilities"][donor])
    real_coalitions = evaluate_coalitions(
        base_x,
        donor_x,
        context["group_indexes"],
        context["gate"].predict_proba,
        real_mean,
        known_empty=real_empty,
        known_all=real_all,
    )
    real_priors = evaluate_per_prior(
        base_x,
        donor_x,
        context["columns"],
        context["groups"]["G3"],
        context["gate"].predict_proba,
        real_mean,
        real_empty,
    )

    null_base_mean = context["donor_probabilities"][r0].mean(axis=0)
    null_all_mean = context["donor_probabilities"][donor].mean(axis=0)
    null_coalition_mask_first, null_shapley, null_priors = c4._coalition_baselines(
        context,
        context["donor_x"][r0],
        donor_x,
        null_base_mean,
        null_all_mean,
    )
    null_coalitions = null_coalition_mask_first.T
    real_shapley = shapley_from_coalitions(real_coalitions)
    values = {
        "real_coalitions": real_coalitions,
        "null_coalitions": null_coalitions,
        "real_shapley": real_shapley,
        "null_shapley": null_shapley,
        "null_referenced_shapley": real_shapley - null_shapley,
        "real_priors": real_priors,
        "null_priors": null_priors,
        "null_referenced_priors": {
            name: real_priors[name] - null_priors[name] for name in real_priors
        },
    }
    identities = {
        "replicate": replicate,
        "recipient_rows": c4.array_identity(rows),
        "donor_rows": c4.array_identity(donor),
        "C4_R0_rows": c4.array_identity(r0),
    }
    return values, identities


def run_pattern_range(
    context: dict[str, Any],
    recipient: dict[str, Any],
    plan: list[dict[str, Any]],
    start: int,
    stop: int,
) -> dict[str, Any]:
    """Execute and retain a contiguous registered P2 replicate range."""
    count = stop - start
    classes = len(context["gate_classes"])
    arrays = {
        "real_coalitions": np.empty((count, classes, 8), dtype=np.float64),
        "null_coalitions": np.empty((count, classes, 8), dtype=np.float64),
        "real_shapley": np.empty((count, classes, 3), dtype=np.float64),
        "null_shapley": np.empty((count, classes, 3), dtype=np.float64),
        "null_referenced_shapley": np.empty((count, classes, 3), dtype=np.float64),
        "real_priors": {
            name: np.empty((count, classes), dtype=np.float64)
            for name in context["groups"]["G3"]
        },
        "null_priors": {
            name: np.empty((count, classes), dtype=np.float64)
            for name in context["groups"]["G3"]
        },
        "null_referenced_priors": {
            name: np.empty((count, classes), dtype=np.float64)
            for name in context["groups"]["G3"]
        },
    }
    first_identity: dict[str, Any] | None = None
    last_identity: dict[str, Any] | None = None
    for offset, replicate in enumerate(range(start, stop)):
        values, identities = evaluate_replicate(context, recipient, plan, replicate)
        for name in (
            "real_coalitions",
            "null_coalitions",
            "real_shapley",
            "null_shapley",
            "null_referenced_shapley",
        ):
            arrays[name][offset] = values[name]
        for kind in (
            "real_priors",
            "null_priors",
            "null_referenced_priors",
        ):
            for prior in arrays[kind]:
                arrays[kind][prior][offset] = values[kind][prior]
        if offset == 0:
            first_identity = identities
        last_identity = identities
        if (offset + 1) % 25 == 0 or offset + 1 == count:
            print(
                f"P2 {context['target']}/{context['pattern']} "
                f"replicate {replicate + 1}/{stop}",
                flush=True,
            )
    arrays["index_identities"] = {
        "first": first_identity,
        "last": last_identity,
    }
    return arrays


def concatenate_ranges(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, Any]:
    """Append only the registered r=250..999 extension."""
    result: dict[str, Any] = {}
    for name in (
        "real_coalitions",
        "null_coalitions",
        "real_shapley",
        "null_shapley",
        "null_referenced_shapley",
    ):
        result[name] = np.concatenate((first[name], second[name]), axis=0)
    for kind in ("real_priors", "null_priors", "null_referenced_priors"):
        result[kind] = {
            prior: np.concatenate((first[kind][prior], second[kind][prior]), axis=0)
            for prior in first[kind]
        }
    result["index_identities"] = {
        "first": first["index_identities"]["first"],
        "last": second["index_identities"]["last"],
    }
    return result


def exact_pattern_endpoints(
    context: dict[str, Any],
    recipient: dict[str, Any],
    *,
    chunk_rows: int,
) -> dict[str, Any]:
    """Compute exact full-row P_D/P_R for every gate class."""
    donor_weights = context["donor_weights"]
    donor = np.average(context["donor_probabilities"], axis=0, weights=donor_weights)
    numerator = np.zeros(len(context["gate_classes"]), dtype=np.float64)
    for start in range(0, len(recipient["x"]), chunk_rows):
        stop = min(start + chunk_rows, len(recipient["x"]))
        probabilities = context["gate"].predict_proba(recipient["x"][start:stop])
        numerator += np.sum(
            recipient["weights"][start:stop, None] * probabilities,
            axis=0,
            dtype=np.float64,
        )
    recipient_mean = numerator / recipient["weights"].sum(dtype=np.float64)
    return {
        "P_D": donor,
        "P_R": recipient_mean,
        "P_D_identity": c4.array_identity(donor),
        "P_R_identity": c4.array_identity(recipient_mean),
    }


def closure_vectors(
    arrays: dict[str, Any],
    endpoints: dict[str, Any],
    class_position: int,
) -> dict[str, np.ndarray]:
    """Construct the binding A16-29 per-pattern closure vectors."""
    real = arrays["real_coalitions"][:, class_position]
    null = arrays["null_coalitions"][:, class_position]
    nr = arrays["null_referenced_shapley"][:, class_position]
    p_d = float(endpoints["P_D"][class_position])
    p_r = float(endpoints["P_R"][class_position])
    delta_nr = (real[:, 7] - real[:, 0]) - (null[:, 7] - null[:, 0])
    return {
        "e_D": real[:, 7] - p_d,
        "e_R": real[:, 0] - p_r,
        "delta_NR": delta_nr,
        "e_T": nr.sum(axis=1) - (p_d - p_r),
        "exact_shapley_error": nr.sum(axis=1) - delta_nr,
    }


def closure_result(values: np.ndarray) -> dict[str, Any]:
    """Summarize and gate one closure residual at three corresponding MCSEs."""
    summary = mc_summary(values)
    threshold = 3.0 * float(summary["mcse"])
    passed = abs(float(summary["value"])) <= threshold
    return {
        **summary,
        "multiplier": 3.0,
        "absolute_threshold": threshold,
        "pass": bool(passed),
        "status": "PASS" if passed else "FAIL",
    }


def exact_shapley_closure(
    error: np.ndarray,
    delta_nr: np.ndarray,
) -> dict[str, Any]:
    """Apply the A16-29 relative float identity on every replicate."""
    err = np.abs(np.asarray(error, dtype=np.float64))
    denominator = np.maximum(np.abs(delta_nr), 1e-12)
    limits = 1e-9 * denominator
    passed = bool(np.all(err <= limits))
    return {
        "pass": passed,
        "status": "PASS" if passed else "FAIL",
        "maximum_absolute_error": float(err.max(initial=0.0)),
        "maximum_error_over_allowed": float(
            np.max(np.divide(err, limits, out=np.zeros_like(err), where=limits > 0))
        ),
        "error_identity": c4.array_identity(error),
        "rule": "abs(sum(phi_NR)-Delta_NR) <= 1e-9*max(abs(Delta_NR),1e-12)",
    }


def verify_c4_endpoints(
    context: dict[str, Any],
    arrays: dict[str, Any],
    c4_cell: dict[str, Any],
) -> dict[str, Any]:
    """Reproduce the adopted C4 endpoints for their recorded prefix exactly."""
    require(
        c4_cell["gate_classes"] == [int(value) for value in context["gate_classes"]],
        "C4 class order changed",
    )
    require(
        c4_cell["sample_size"]
        == arrays["index_identities"]["first"]["recipient_rows"]["shape"][0],
        "reading sample size differs from adopted C4",
    )
    recorded = c4_cell["replicate_arrays"]
    expected_empty = np.asarray(recorded["v_null_empty"]["values"], dtype=np.float64)
    expected_all = np.asarray(recorded["v_null_all"]["values"], dtype=np.float64)
    count = min(len(expected_empty), len(arrays["null_coalitions"]))
    actual_empty = arrays["null_coalitions"][:count, :, 0]
    actual_all = arrays["null_coalitions"][:count, :, 7]
    require(
        np.array_equal(actual_empty, expected_empty[:count])
        and np.array_equal(actual_all, expected_all[:count]),
        f"adopted C4 endpoints did not reproduce for "
        f"{context['target']}/{context['pattern']}",
    )
    return {
        "status": "PASS",
        "recorded_replicates": len(expected_empty),
        "reading_replicates": len(arrays["null_coalitions"]),
        "verified_prefix_replicates": count,
        "v_null_empty_identity": c4.array_identity(actual_empty),
        "v_null_all_identity": c4.array_identity(actual_all),
        "extension_beyond_adopted_C4_is_descriptive_baseline": (
            len(arrays["null_coalitions"]) > len(expected_empty)
        ),
    }


def support_evidence(d0: dict[str, Any], target: str, leg: str) -> dict[str, Any]:
    """Read the frozen D0-1 unique-carrier support decision."""
    rung = d0["D0-1"]["rungs"]["candidate-25"][target]
    origins: dict[str, Any] = {}
    for origin in ("asec", "acs"):
        row = rung[origin]["legs"][leg]
        # The estimand and A7's owner-ratified SEILY disposition are clone-0.
        # Retain the all-clone diagnostic so the D0 definition discrepancy is
        # visible rather than silently selecting the larger count.
        count = int(row["unique_clone_deduplicated_source_rows_clone0"])
        origins[origin] = {
            "unique_clone_deduplicated_source_rows_clone0": count,
            "unique_clone_deduplicated_source_rows_all_clones": int(
                row["unique_clone_deduplicated_source_rows_all_clones"]
            ),
            "pass": count >= SUPPORT_FLOOR,
        }
    passed = all(item["pass"] for item in origins.values())
    return {
        "floor": SUPPORT_FLOOR,
        "origins": origins,
        "pass": passed,
        "status": "SUPPORTED" if passed else "INSUFFICIENT_SUPPORT_NO_VERDICT",
        "decision_count_basis": (
            "clone-0 unique rows: battery estimand and A7 explicitly ratify "
            "SEILY negative=48 as DEFERred"
        ),
        "source": {
            "path": str(D0_JSON),
            "sha256": a18_enumeration.EXPECTED_AUTHORITY_DIGESTS[
                str(a18_enumeration.D0_JSON)
            ],
            "pointer": f"/D0-1/rungs/candidate-25/{target}",
        },
    }


def _pattern_leg_vectors(
    arrays: dict[str, Any],
    endpoints: dict[str, Any],
    class_position: int,
) -> dict[str, np.ndarray]:
    closures = closure_vectors(arrays, endpoints, class_position)
    vectors = {
        f"group_{group}": arrays["null_referenced_shapley"][:, class_position, position]
        for position, group in enumerate(GROUPS)
    }
    vectors.update({name: closures[name] for name in CLOSURE_ROWS})
    return vectors


def _serialize_pattern(
    context: dict[str, Any],
    recipient: dict[str, Any],
    plan: list[dict[str, Any]],
    arrays: dict[str, Any],
    endpoints: dict[str, Any],
    initial_decisions: dict[str, Any],
    escalated: bool,
    c4_verification: dict[str, Any],
    supports: dict[str, Any],
    joint_domain: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build one nested pattern reading and its sealed-manifest fragments."""
    target = context["target"]
    pattern = context["pattern"]
    stats: list[dict[str, Any]] = []
    leg_payloads: list[dict[str, Any]] = []
    for class_position, class_code in enumerate(context["gate_classes"]):
        if int(class_code) not in {-1, 1}:
            continue
        leg = replay.label_name(int(class_code))
        supported = supports[leg]["pass"]
        status = "PASS" if supported else "INSUFFICIENT_SUPPORT_NO_VERDICT"
        raw_shapley = arrays["real_shapley"][:, class_position]
        null_shapley = arrays["null_shapley"][:, class_position]
        nr_shapley = arrays["null_referenced_shapley"][:, class_position]
        group_rows: list[dict[str, Any]] = []
        for group_position, group in enumerate(GROUPS):
            variants = {
                "raw": raw_shapley[:, group_position],
                "null": null_shapley[:, group_position],
                "null_referenced": nr_shapley[:, group_position],
            }
            variant_payload = {
                name: {**mc_summary(vector), "array": _array_payload(vector)}
                for name, vector in variants.items()
            }
            group_rows.append({"group": group, "variants": variant_payload})
            for variant, summary in variant_payload.items():
                stats.append(
                    statistic_fragment(
                        target=target,
                        pattern=pattern,
                        leg=leg,
                        row="P2_group_pattern",
                        group=group,
                        variant=variant,
                        value=float(summary["value"]),
                        mcse=float(summary["mcse"]),
                        family=None,
                        gated=False,
                        status=status
                        if variant == "null_referenced"
                        else "DESCRIPTIVE",
                        source_pointer=(
                            f"/targets/{target}/patterns/{pattern}/legs/{leg}/"
                            f"groups/{group}/{variant}"
                        ),
                    )
                )

        closure_arrays = closure_vectors(arrays, endpoints, class_position)
        closures = {
            name: {
                **closure_result(closure_arrays[name]),
                "array": _array_payload(closure_arrays[name]),
            }
            for name in CLOSURE_ROWS
        }
        exact_closure = exact_shapley_closure(
            closure_arrays["exact_shapley_error"],
            closure_arrays["delta_NR"],
        )
        closure_pass = all(item["pass"] for item in closures.values())
        attribution_status = (
            "INSUFFICIENT_SUPPORT_NO_VERDICT"
            if not supported
            else "VALIDATED"
            if closure_pass and exact_closure["pass"]
            else "NOT_VALIDATED_CLOSURE_FAILURE"
        )
        for name, summary in closures.items():
            stats.append(
                statistic_fragment(
                    target=target,
                    pattern=pattern,
                    leg=leg,
                    row=name,
                    value=float(summary["value"]),
                    mcse=float(summary["mcse"]),
                    family="F2" if supported else None,
                    gated=supported,
                    status=summary["status"] if supported else attribution_status,
                    source_pointer=(
                        f"/targets/{target}/patterns/{pattern}/legs/{leg}/"
                        f"closures/{name}"
                    ),
                )
            )

        priors: list[dict[str, Any]] = []
        prior_sum = np.zeros(len(nr_shapley), dtype=np.float64)
        for prior in context["groups"]["G3"]:
            vectors = {
                "raw": arrays["real_priors"][prior][:, class_position],
                "null": arrays["null_priors"][prior][:, class_position],
                "null_referenced": arrays["null_referenced_priors"][prior][
                    :, class_position
                ],
            }
            prior_sum += vectors["null_referenced"]
            summaries = {
                name: {**mc_summary(vector), "array": _array_payload(vector)}
                for name, vector in vectors.items()
            }
            priors.append({"prior": prior, "variants": summaries})
            for variant, summary in summaries.items():
                stats.append(
                    statistic_fragment(
                        target=target,
                        pattern=pattern,
                        leg=leg,
                        row="P2_prior_pattern",
                        prior=prior,
                        variant=variant,
                        value=float(summary["value"]),
                        mcse=float(summary["mcse"]),
                        family=None,
                        gated=False,
                        status=(
                            "DESCRIPTIVE"
                            if supported
                            else "INSUFFICIENT_SUPPORT_NO_VERDICT"
                        ),
                        source_pointer=(
                            f"/targets/{target}/patterns/{pattern}/legs/{leg}/"
                            f"priors/{prior}/{variant}"
                        ),
                    )
                )
        interaction = nr_shapley[:, GROUPS.index("G3")] - prior_sum
        interaction_summary = {
            **mc_summary(interaction),
            "array": _array_payload(interaction),
            "definition": "G3 null-referenced Shapley minus sum of A1 marginals",
            "descriptive_only": True,
        }

        initial = initial_decisions[leg]
        max_ratio = float(initial["max_abs_value_over_mcse"])
        for variant, value, row_status in (
            (
                "R250",
                max_ratio,
                "TRIGGER" if initial["trigger"] else "NO_TRIGGER",
            ),
            (
                "R1000",
                float(ESCALATED_REPLICATES) if escalated else "NA",
                "RUN" if escalated else "NOT_RUN_NO_TARGET_TRIGGER",
            ),
            (
                "decision",
                1.0 if escalated else 0.0,
                "ESCALATE_TARGET" if escalated else "KEEP_R250",
            ),
        ):
            stats.append(
                statistic_fragment(
                    target=target,
                    pattern=pattern,
                    leg=leg,
                    row="P2_escalation",
                    variant=variant,
                    value=value,
                    family=None,
                    gated=False,
                    status=row_status,
                    source_pointer=(
                        f"/targets/{target}/patterns/{pattern}/legs/{leg}/escalation"
                    ),
                )
            )
        leg_payloads.append(
            {
                "leg": leg,
                "class_code": int(class_code),
                "class_position": class_position,
                "support": supports[leg],
                "P_D": float(endpoints["P_D"][class_position]),
                "P_R": float(endpoints["P_R"][class_position]),
                "T2_pattern": float(
                    endpoints["P_D"][class_position] - endpoints["P_R"][class_position]
                ),
                "groups": group_rows,
                "priors": priors,
                "G3_within_group_interaction": interaction_summary,
                "closures": closures,
                "Delta_NR": {
                    **mc_summary(closure_arrays["delta_NR"]),
                    "array": _array_payload(closure_arrays["delta_NR"]),
                },
                "exact_shapley_closure": exact_closure,
                "escalation": initial,
                "attribution_status": attribution_status,
                "joint_hybrid_domain": joint_domain,
            }
        )

    payload = {
        "pattern": pattern,
        "columns": list(context["columns"]),
        "groups": {group: list(context["groups"][group]) for group in GROUPS},
        "gate": {
            "seed": context["gate_seed"],
            "classes": [int(value) for value in context["gate_classes"]],
            "state_before_sha256": context["state_before_sha256"],
            "state_before_source": context["state_before_source"],
            "c0b_bindings": context["c0b_bindings"],
            "donor_x_identity": c4.array_identity(context["donor_x"]),
            "donor_probability_identity": c4.array_identity(
                context["donor_probabilities"]
            ),
        },
        "recipient": {
            "rows": len(recipient["x"]),
            "x_identity": recipient["x_identity"],
            "weight_identity": recipient["weight_identity"],
            "stable_id_identity": recipient["stable_id_identity"],
            "prior_sources": recipient["prior_sources"],
        },
        "sampling": {
            "sample_size": sum(item["allocation"] for item in plan),
            "strata": [
                {
                    key: item[key]
                    for key in (
                        "gq",
                        "row_count",
                        "weight_sum",
                        "allocation",
                        "exact_target_share",
                        "exact_pattern_share",
                        "stable_entity_id_identity",
                    )
                }
                for item in plan
            ],
            "slices": stratum_slices(plan),
            "analysis_weights": "unit within draws; exact stratum shares",
            "index_identities": arrays["index_identities"],
        },
        "replicates": len(arrays["real_coalitions"]),
        "replicate_arrays": {
            name: _array_payload(arrays[name])
            for name in (
                "real_coalitions",
                "null_coalitions",
                "real_shapley",
                "null_shapley",
                "null_referenced_shapley",
            )
        },
        "exact_endpoints": {
            "P_D": [float(value) for value in endpoints["P_D"]],
            "P_R": [float(value) for value in endpoints["P_R"]],
            "P_D_identity": endpoints["P_D_identity"],
            "P_R_identity": endpoints["P_R_identity"],
        },
        "C4_endpoint_reproduction": c4_verification,
        "legs": leg_payloads,
    }
    return payload, stats


def _marginal_fragments(
    target: str,
    pattern: str,
    audits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for audit in audits:
        feature = audit["feature"]
        variants: list[tuple[str, float | str, float | str, str]] = [
            (
                "donor_mean",
                audit["donor"]["mean"],
                audit["donor"]["mean_se"],
                "DESCRIPTIVE",
            ),
            (
                "recipient_mean",
                audit["recipient"]["mean"],
                audit["recipient"]["mean_se"],
                "DESCRIPTIVE",
            ),
            ("smd", audit["smd"], "NA", "DESCRIPTIVE"),
            (
                "difference_se",
                audit["difference_se"],
                "NA",
                "DESCRIPTIVE",
            ),
            (
                "domain_violation_share",
                audit["one_feature_recipient_outside_donor_support_share"],
                "NA",
                "DESCRIPTIVE_NOT_A16_JOINT_GATE",
            ),
        ]
        for variant, value, se, status in variants:
            rows.append(
                statistic_fragment(
                    target=target,
                    pattern=pattern,
                    row="P2_marginal_audit",
                    prior=feature,
                    variant=variant,
                    value=value,
                    se=se,
                    family=None,
                    gated=False,
                    status=status,
                    source_pointer=(
                        f"/targets/{target}/patterns/{pattern}/marginal_audit/"
                        f"{feature}/{variant}"
                    ),
                )
            )
    return rows


def _aggregate_groups(
    target: str,
    pattern_data: list[dict[str, Any]],
    pattern_arrays: dict[str, dict[str, Any]],
    alpha: dict[str, float],
    supports: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Aggregate official group rows from replicate-level alpha sums."""
    aggregates: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    contexts_by_pattern = {item["context"]["pattern"]: item for item in pattern_data}
    for leg in LEGS:
        class_code = CLASS_BY_LEG[leg]
        present = all(
            class_code in [int(value) for value in item["context"]["gate_classes"]]
            for item in pattern_data
        )
        if not present:
            for group in GROUPS:
                stats.append(
                    statistic_fragment(
                        target=target,
                        leg=leg,
                        row="P2_group_aggregate",
                        group=group,
                        value="NA",
                        family=None,
                        gated=False,
                        status="NOT_APPLICABLE_CLASS_ABSENT",
                        source_pointer=f"/targets/{target}/aggregates/{leg}/{group}",
                    )
                )
            aggregates.append(
                {"leg": leg, "status": "NOT_APPLICABLE_CLASS_ABSENT", "groups": []}
            )
            continue
        group_rows: list[dict[str, Any]] = []
        supported = supports[leg]["pass"]
        for group_position, group in enumerate(GROUPS):
            vector: np.ndarray | None = None
            summation_order: list[dict[str, Any]] = []
            for pattern, weight in alpha.items():
                context = contexts_by_pattern[pattern]["context"]
                class_position = [
                    int(value) for value in context["gate_classes"]
                ].index(class_code)
                contribution = (
                    weight
                    * pattern_arrays[pattern]["null_referenced_shapley"][
                        :, class_position, group_position
                    ]
                )
                vector = (
                    contribution.copy() if vector is None else vector + contribution
                )
                summation_order.append({"pattern": pattern, "alpha": weight})
            assert vector is not None
            summary = {**mc_summary(vector), "array": _array_payload(vector)}
            group_rows.append(
                {
                    "group": group,
                    **summary,
                    "alpha_summation_order": summation_order,
                }
            )
            stats.append(
                statistic_fragment(
                    target=target,
                    leg=leg,
                    row="P2_group_aggregate",
                    group=group,
                    value=float(summary["value"]),
                    mcse=float(summary["mcse"]),
                    family="F2" if supported else None,
                    gated=supported,
                    status=("PASS" if supported else "INSUFFICIENT_SUPPORT_NO_VERDICT"),
                    source_pointer=f"/targets/{target}/aggregates/{leg}/{group}",
                )
            )
        aggregates.append(
            {
                "leg": leg,
                "status": (
                    "SUPPORTED" if supported else "INSUFFICIENT_SUPPORT_NO_VERDICT"
                ),
                "support": supports[leg],
                "groups": group_rows,
            }
        )
    return aggregates, stats


def _joint_domain_unavailable(d0: dict[str, Any]) -> dict[str, Any]:
    """Record the binding absence without constructing a replacement predicate."""
    d0_7 = d0.get("D0-7", {})
    explicitly_present = any(
        key in d0_7
        for key in (
            "joint_hybrid_domain_predicates",
            "joint_domain_predicates",
            "hybrid_domain_predicates",
        )
    )
    require(
        not explicitly_present, "D0 joint predicates appeared; executor needs review"
    )
    return {
        "status": "UNAVAILABLE_D0_NOT_ENUMERATED",
        "predicates": [],
        "violation_share": "NA",
        "threshold": 0.01,
        "pattern_invalidation_decision": "NOT_EVALUABLE",
        "no_predicates_invented": True,
        "source": {
            "path": str(D0_JSON),
            "sha256": a18_enumeration.EXPECTED_AUTHORITY_DIGESTS[
                str(a18_enumeration.D0_JSON)
            ],
            "checked_pointer": "/D0-7",
        },
    }


def run_target(
    data: dict[str, Any],
    d0: dict[str, Any],
    c0b_lookup: dict[tuple[str, str], dict[str, Any]],
    c4_cells: dict[tuple[str, str], dict[str, Any]],
    target: str,
    *,
    chunk_rows: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute one complete, independently sealable target reading."""
    started = time.perf_counter()
    allocation = c4.target_allocation(data, target)
    pattern_names = [item["name"] for item in data["target_specs"][target]["patterns"]]
    contexts = {
        pattern: c4.fit_gate_context(data, target, pattern, c0b_lookup)
        for pattern in pattern_names
    }
    recipients = {
        pattern: recipient_pattern_data(data, contexts[pattern])
        for pattern in pattern_names
    }
    plans = {
        pattern: pattern_sampling_plan(allocation, recipients[pattern], pattern)
        for pattern in pattern_names
    }
    endpoints = {
        pattern: exact_pattern_endpoints(
            contexts[pattern], recipients[pattern], chunk_rows=chunk_rows
        )
        for pattern in pattern_names
    }
    arrays = {
        pattern: run_pattern_range(
            contexts[pattern],
            recipients[pattern],
            plans[pattern],
            0,
            INITIAL_REPLICATES,
        )
        for pattern in pattern_names
    }
    initial_decisions: dict[str, dict[str, Any]] = {}
    target_trigger = False
    for pattern in pattern_names:
        decisions: dict[str, Any] = {}
        context = contexts[pattern]
        for class_position, class_code in enumerate(context["gate_classes"]):
            if int(class_code) not in {-1, 1}:
                continue
            leg = replay.label_name(int(class_code))
            decision = reading_escalation_decision(
                _pattern_leg_vectors(
                    arrays[pattern], endpoints[pattern], class_position
                )
            )
            decisions[leg] = decision
            target_trigger |= decision["trigger"]
        initial_decisions[pattern] = decisions
    if target_trigger:
        for pattern in pattern_names:
            extension = run_pattern_range(
                contexts[pattern],
                recipients[pattern],
                plans[pattern],
                INITIAL_REPLICATES,
                ESCALATED_REPLICATES,
            )
            arrays[pattern] = concatenate_ranges(arrays[pattern], extension)

    supports = {leg: support_evidence(d0, target, leg) for leg in LEGS}
    joint_domain = _joint_domain_unavailable(d0)
    alpha = {
        pattern: float(
            contexts[pattern]["d0_pattern"]["clone0_recipient_weight_sum"]
            / data["target_specs"][target]["clone0_recipient_weight_sum"]
        )
        for pattern in pattern_names
    }
    require(
        math.isclose(math.fsum(alpha.values()), 1.0, rel_tol=0.0, abs_tol=2e-15),
        f"alpha weights do not close for {target}",
    )

    pattern_payloads: list[dict[str, Any]] = []
    pattern_runtime: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    for pattern in pattern_names:
        context = contexts[pattern]
        c4_verification = verify_c4_endpoints(
            context, arrays[pattern], c4_cells[(target, pattern)]
        )
        audits = [
            marginal_audit(
                context["donor_x"][:, position],
                context["donor_weights"],
                recipients[pattern]["x"][:, position],
                recipients[pattern]["weights"],
                feature=feature,
            )
            for position, feature in enumerate(context["columns"])
        ]
        pattern_payload, pattern_stats = _serialize_pattern(
            context,
            recipients[pattern],
            plans[pattern],
            arrays[pattern],
            endpoints[pattern],
            initial_decisions[pattern],
            target_trigger,
            c4_verification,
            supports,
            joint_domain,
        )
        pattern_payload["alpha"] = alpha[pattern]
        pattern_payload["marginal_audit"] = audits
        pattern_payload["joint_hybrid_domain"] = joint_domain
        pattern_payloads.append(pattern_payload)
        stats.extend(pattern_stats)
        stats.extend(_marginal_fragments(target, pattern, audits))
        pattern_runtime.append(
            {
                "context": context,
                "recipient": recipients[pattern],
            }
        )

    aggregates, aggregate_stats = _aggregate_groups(
        target, pattern_runtime, arrays, alpha, supports
    )
    stats.extend(aggregate_stats)
    payload: dict[str, Any] = {
        "target": target,
        "status": "COMPLETE",
        "rung": "candidate-25 pre-calibration",
        "replicates_initial": INITIAL_REPLICATES,
        "replicates_final": (
            ESCALATED_REPLICATES if target_trigger else INITIAL_REPLICATES
        ),
        "escalated": target_trigger,
        "target_wide_escalation_rule": True,
        "alpha": alpha,
        "allocation": allocation,
        "support": supports,
        "patterns": pattern_payloads,
        "aggregates": aggregates,
        "joint_hybrid_domain": joint_domain,
        "statistics_count": len(stats),
        "statistic_ids_sha256": canonical_sha256(sorted(item["id"] for item in stats)),
        "elapsed_seconds": time.perf_counter() - started,
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload, stats


def _manifest_ids_for_targets(
    path: Path,
    targets: set[str],
) -> set[str]:
    """Read only the P2-compatible portion of the sealed Step-0 manifest."""
    payload = json.loads(path.read_text())
    manifest = payload.get("step0", {}).get("required_id_manifest")
    require(isinstance(manifest, list), "manifest JSON lacks Step-0 ID list")
    result = {
        item["id"]
        for item in manifest
        if item.get("dimensions", {}).get("target") in targets
        and item.get("dimensions", {}).get("row") in P2_ROWS
    }
    require(result, "manifest contains no requested P2 IDs")
    return result


def validate_manifest_fragments(
    statistics: list[dict[str, Any]],
    manifest_path: Path | None,
    targets: set[str],
) -> dict[str, Any]:
    """Reject duplicate/missing/extra P2 fragments when a manifest is supplied."""
    ids = [item["id"] for item in statistics if item["target"] in targets]
    require(len(ids) == len(set(ids)), "P2 output contains duplicate statistic IDs")
    if manifest_path is None:
        return {
            "status": "NOT_REQUESTED",
            "fragment_count": len(ids),
            "ordered_ids_sha256": canonical_sha256(sorted(ids)),
        }
    expected = _manifest_ids_for_targets(manifest_path, targets)
    actual = set(ids)
    require(
        actual == expected,
        "P2 manifest mismatch: "
        f"missing={sorted(expected - actual)[:10]}, "
        f"extra={sorted(actual - expected)[:10]}",
    )
    return {
        "status": "PASS",
        "manifest_path": str(manifest_path.resolve()),
        "manifest_sha256": c4.sha256_file(manifest_path),
        "fragment_count": len(ids),
        "ordered_ids_sha256": canonical_sha256(sorted(ids)),
    }


def _base_result(
    *,
    all_targets: list[str],
    prerequisites: dict[str, Any],
    input_verification: dict[str, Any],
    source_files: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_kind": "qrf_drift_phase0_a18_p2",
        "schema_version": 1,
        "status": "RUNNING",
        "authority": {
            "design": {
                "path": str(DESIGN_MD),
                "sha256": DESIGN_SHA256,
                "commit": A18_COMMIT,
                "amendment": "v2.7/A18",
            },
            "d0": {
                "path": str(D0_JSON),
                "sha256": a18_enumeration.EXPECTED_AUTHORITY_DIGESTS[
                    str(a18_enumeration.D0_JSON)
                ],
            },
            "a16_binding": {
                "path": str(A16_BINDING),
                "sha256": a18_enumeration.EXPECTED_AUTHORITY_DIGESTS[
                    str(a18_enumeration.A16_BINDING)
                ],
            },
        },
        "prerequisites": prerequisites,
        "input_verification": input_verification,
        "source_files": source_files,
        "scope": {
            "rung": "candidate-25 pre-calibration",
            "all_targets_in_D0_order": all_targets,
            "completed_targets": [],
            "requested_target_history": [],
        },
        "estimator": {
            "target_sample_N": "min(100000, |S_q,target|)",
            "strata": "D0 pattern order then H,2,3,U",
            "allocation": (
                "one per positive-mass stratum; remainder by largest remainder"
            ),
            "within_stratum": "artifact-weight PPS with replacement",
            "analysis_weights": "unit; exact stratum weighted-share combination",
            "donor_stream": ("qrf-drift-v2|P2|donor|<target>|<pattern>|<r>"),
            "recipient_stream": ("qrf-drift-v2|P2|rows|<target>|<r>|<pattern>|<gq>"),
            "null_stream": ("qrf-drift-v2.3|C4|r0|<target>|<pattern>|<r>"),
            "coalitions": list(range(8)),
            "common_donor_draws": True,
            "null_reference": "real replicate minus paired C4 replicate",
            "replicates": "250; target-wide 1000 iff any reading ratio in [2,4]",
            "closures": "per-pattern e_D/e_R/e_T at 3 MCSE plus exact Shapley",
            "target_aggregation": "alpha-weight replicate sums before mean/MCSE",
            "marginal_scope": "full donor fit rows versus full S_q recipient rows",
            "magnitude_forests_loaded": False,
        },
        "targets": [],
        "statistics": [],
        "manifest_validation": {},
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


def _write_result(path: Path, result: dict[str, Any]) -> str:
    result["targets"] = sorted(
        result["targets"],
        key=lambda item: result["scope"]["all_targets_in_D0_order"].index(
            item["target"]
        ),
    )
    result["statistics"] = sorted(result["statistics"], key=lambda item: item["id"])
    return c4.write_canonical_result(path, result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--targets",
        nargs="+",
        help="target subset; execution is normalized to D0 order",
    )
    parser.add_argument("--adoption-json", type=Path, default=DEFAULT_ADOPTION)
    parser.add_argument("--c3-json", type=Path, default=DEFAULT_C3)
    parser.add_argument("--c0b-json", type=Path, default=DEFAULT_C0B)
    parser.add_argument("--c4-json", type=Path, default=DEFAULT_C4)
    parser.add_argument("--manifest-json", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="append missing requested targets to a compatible canonical artifact",
    )
    parser.add_argument(
        "--prediction-chunk-rows",
        type=int,
        default=100_000,
        help="full-row P_R prediction chunk size",
    )
    args = parser.parse_args()
    if args.prediction_chunk_rows < 1:
        parser.error("--prediction-chunk-rows must be positive")
    return args


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    adoption, c3_payload, c4_payload, c0b_payload = verify_reading_prerequisites(
        args.adoption_json,
        args.c3_json,
        args.c4_json,
        args.c0b_json,
    )
    d0 = json.loads(D0_JSON.read_text())
    input_verification = a18_enumeration.verify_inputs(d0, args.c0b_json)
    data = c4.load_analysis_data(d0)
    all_targets = list(data["target_specs"])
    unknown = set(args.targets or ()) - set(all_targets)
    require(not unknown, f"unknown target(s): {sorted(unknown)}")
    require(
        args.targets is None or len(args.targets) == len(set(args.targets)),
        "--targets contains duplicates",
    )
    requested = [
        target
        for target in all_targets
        if args.targets is None or target in args.targets
    ]
    c0b_lookup = {
        (item["target"], item["pattern"]): item for item in c0b_payload["patterns"]
    }
    c4_cells = {(item["target"], item["pattern"]): item for item in c4_payload["cells"]}
    prerequisites = {
        "status": "PASS",
        "readings_authorized_by": "sealed A18 adoption plus fresh C3 PASS",
        "adoption": {
            "path": str(args.adoption_json.resolve()),
            "sha256": c4.sha256_file(args.adoption_json),
            "canonical_sha256": adoption["canonical_sha256"],
        },
        "fresh_C3": {
            "path": str(args.c3_json.resolve()),
            "sha256": c4.sha256_file(args.c3_json),
            "canonical_sha256": c3_payload["canonical_sha256"],
            "status": c3_payload["status"],
        },
        "adopted_C4": {
            "path": str(args.c4_json.resolve()),
            "sha256": c4.sha256_file(args.c4_json),
            "canonical_sha256": c4_payload["canonical_sha256"],
        },
        "adopted_C0b": {
            "path": str(args.c0b_json.resolve()),
            "sha256": c4.sha256_file(args.c0b_json),
        },
    }
    source_files = [
        {"path": str(path.resolve()), "sha256": c4.sha256_file(path)}
        for path in (Path(__file__), Path(c4.__file__), Path(replay.__file__))
    ]

    if args.out.exists():
        require(args.resume, f"output exists; pass --resume: {args.out}")
        result = json.loads(args.out.read_text())
        verify_self_canonical(result, "resumed P2")
        for target_payload in result.get("targets", []):
            nested = dict(target_payload)
            recorded_nested = nested.pop("canonical_sha256", None)
            require(
                recorded_nested == canonical_sha256(nested),
                f"resumed target seal changed: {target_payload.get('target')}",
            )
        require(
            result.get("artifact_kind") == "qrf_drift_phase0_a18_p2"
            and result.get("authority", {}).get("design", {}).get("sha256")
            == DESIGN_SHA256
            and result.get("prerequisites") == prerequisites
            and result.get("input_verification") == input_verification,
            "existing P2 artifact is not resume-compatible",
        )
        require(
            result.get("source_files") == source_files,
            "P2 implementation changed since the resumable artifact was sealed",
        )
    else:
        require(not args.resume, "--resume requested but output does not exist")
        result = _base_result(
            all_targets=all_targets,
            prerequisites=prerequisites,
            input_verification=input_verification,
            source_files=source_files,
        )
    result["scope"]["requested_target_history"].append(requested)
    completed = {item["target"] for item in result["targets"]}
    for target in requested:
        if target in completed:
            print(f"P2 {target}: already complete, resume skip", flush=True)
            continue
        target_payload, target_statistics = run_target(
            data,
            d0,
            c0b_lookup,
            c4_cells,
            target,
            chunk_rows=args.prediction_chunk_rows,
        )
        result["targets"].append(target_payload)
        result["statistics"].extend(target_statistics)
        completed.add(target)
        result["scope"]["completed_targets"] = [
            name for name in all_targets if name in completed
        ]
        result["status"] = "RUNNING"
        result["summary"] = {
            "targets_complete": len(completed),
            "targets_total": len(all_targets),
            "last_completed_target": target,
        }
        output_sha = _write_result(args.out, result)
        print(
            f"P2 {target}: sealed target sha256={target_payload['canonical_sha256']} "
            f"artifact_sha256={output_sha}",
            flush=True,
        )

    completed = {item["target"] for item in result["targets"]}
    result["scope"]["completed_targets"] = [
        name for name in all_targets if name in completed
    ]
    validation_targets = set(result["scope"]["completed_targets"])
    result["manifest_validation"] = validate_manifest_fragments(
        result["statistics"], args.manifest_json, validation_targets
    )
    result["status"] = (
        "COMPLETE" if completed == set(all_targets) else "TARGET_SUBSET_COMPLETE"
    )
    result["summary"] = {
        "targets_complete": len(completed),
        "targets_total": len(all_targets),
        "targets_remaining": [name for name in all_targets if name not in completed],
        "targets_escalated": [
            item["target"] for item in result["targets"] if item["escalated"]
        ],
        "statistics": len(result["statistics"]),
        "all_C4_endpoint_reproductions_pass": all(
            pattern["C4_endpoint_reproduction"]["status"] == "PASS"
            for target_payload in result["targets"]
            for pattern in target_payload["patterns"]
        ),
    }
    result["execution_diagnostics"].update(
        {
            "finished_unix": time.time(),
            "elapsed_seconds_this_invocation": time.perf_counter() - started,
            "peak_rss_mb": c4.peak_rss_mb(),
        }
    )
    output_sha = _write_result(args.out, result)
    print(
        f"RESULT {args.out} sha256={output_sha} status={result['status']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
