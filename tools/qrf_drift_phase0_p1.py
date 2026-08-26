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
DESIGN_MD = WORKTREE / "experiments/qrf_drift_validation_design.md"
A16_BINDING = WORKTREE / "experiments/qrf_drift_validation_a16_binding_texts.md"
DEFAULT_C0B = Path("/private/tmp/qrf_phase0_v22_c0b.json")
DEFAULT_STEP0 = WORKTREE / "experiments/qrf_drift_validation_phase0.json"
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_p1.json")
ZERO_ATOL = 1e-6
EXPECTED_D0_SHA256 = "fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8"
EXPECTED_DESIGN_SHA256 = (
    "5c8e55293215a7d1350c93825b1a4daf04e212bb84d17408b8750ed5d9d4e754"
)
EXPECTED_A16_BINDING_SHA256 = (
    "7e288bce7496e1e7f41e33f078be2043673ca54ff31182caf2ce92eab68a81c1"
)
EXPECTED_C0B_SHA256 = "1c7bfd65660b14068c4bc96fae4b8d270cb447ea8fbbe42c8ef982c5f1dbf542"
EXPECTED_OPERATOR_TABLE_SHA256 = (
    "447f7c9f00220440b7ad3825223f01fec8bed28e16e6eda2a851afdda64a6e23"
)
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
    array = np.asarray(values)
    if array.dtype.kind not in {"O", "S", "U"}:
        return c4.array_identity(array)
    normalized: list[object] = []
    for value in array.reshape(-1):
        if isinstance(value, bytes):
            normalized.append({"bytes_hex": value.hex()})
        else:
            scalar = value.item() if isinstance(value, np.generic) else value
            missing = pd.isna(scalar)
            is_missing = (
                bool(missing) if isinstance(missing, (bool, np.bool_)) else False
            )
            normalized.append(None if is_missing else str(scalar))
    payload = canonical_json({"shape": list(array.shape), "values": normalized}).encode(
        "utf-8"
    )
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "encoding": "canonical_json_logical_values_v1",
    }


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


class SurfaceUnavailableError(RuntimeError):
    """A registered reading surface cannot be replayed deterministically."""

    def __init__(self, stage: str, evidence: dict[str, Any]) -> None:
        super().__init__(f"registered {stage} surface is unavailable")
        self.stage = stage
        self.evidence = evidence


def _carrier_mask(values: np.ndarray, sign: int, *, atol: float = 0.0) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if sign not in {-1, 1}:
        raise ValueError(f"unsupported leg sign {sign}")
    return values > atol if sign > 0 else values < -atol


def _weighted_summary(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    sign: int,
    atol: float = 0.0,
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
    carrier = _carrier_mask(values, sign, atol=atol)
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
        "sign_rule": "exact_gt_lt_zero" if atol == 0.0 else f"qrf_atol_{atol:g}",
    }


def _path_census(
    authorized: np.ndarray,
    null_before: np.ndarray,
    drawn: np.ndarray,
    finite_decode: np.ndarray,
) -> dict[str, Any]:
    """Assign every scoped row to the first failed A16-16 path predicate."""
    masks = [
        np.asarray(mask, dtype=bool)
        for mask in (authorized, null_before, drawn, finite_decode)
    ]
    if len({len(mask) for mask in masks}) != 1:
        raise ValueError("path-census masks do not share one scope axis")
    authorized_mask, null_mask, drawn_mask, decoded_mask = masks
    first_failure = {
        "authorized": ~authorized_mask,
        "null_before": authorized_mask & ~null_mask,
        "drawn": authorized_mask & null_mask & ~drawn_mask,
        "finite_decode": authorized_mask & null_mask & drawn_mask & ~decoded_mask,
    }
    passed = authorized_mask & null_mask & drawn_mask & decoded_mask
    partition = passed.copy()
    for mask in first_failure.values():
        if np.any(partition & mask):
            raise ValueError("path-census first-failure masks overlap")
        partition |= mask
    if not partition.all():
        raise ValueError("path-census first-failure masks do not exhaust scope")
    return {
        "stage_pass_rows": {
            "authorized": int(authorized_mask.sum()),
            "null_before": int((authorized_mask & null_mask).sum()),
            "drawn": int((authorized_mask & null_mask & drawn_mask).sum()),
            "finite_decode": int(passed.sum()),
        },
        "first_failure_rows": {
            name: int(mask.sum()) for name, mask in first_failure.items()
        },
        "first_failure_masks": {
            name: mask_identity(mask) for name, mask in first_failure.items()
        },
        "passed_rows": int(passed.sum()),
        "passed_mask": mask_identity(passed),
        "_passed": passed,
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


def _c0b_lookup(c0b_evidence: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Read the full, direct C0b replay artifact; merged reports are not evidence."""
    patterns = c0b_evidence.get("patterns")
    if not isinstance(patterns, list):
        raise ValueError("direct C0b evidence must expose a top-level patterns array")
    lookup = {(row["target"], row["pattern"]): row for row in patterns}
    if len(lookup) != 36:
        raise ValueError(f"expected 36 direct C0b patterns, got {len(lookup)}")
    return lookup


def _load_operator_table(
    step0_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(step0_path.read_text())
    step0 = payload.get("step0")
    if not isinstance(step0, dict):
        raise ValueError("Step-0 source has no sealed step0 object")
    rows = step0.get("operator_table")
    seals = step0.get("seals")
    if not isinstance(rows, list) or not isinstance(seals, dict):
        raise ValueError("Step-0 source lacks its operator table or seals")
    actual = hashlib.sha256(canonical_json(rows).encode("utf-8")).hexdigest()
    embedded = seals.get("operator_table_sha256")
    if actual != embedded or actual != EXPECTED_OPERATOR_TABLE_SHA256:
        raise ValueError(
            "Step-0 operator-table seal mismatch: "
            f"actual={actual}, embedded={embedded}, expected={EXPECTED_OPERATOR_TABLE_SHA256}"
        )
    targets = {row.get("target") for row in rows}
    if targets != set(TARGETS):
        raise ValueError(f"Step-0 operator targets mismatch: {sorted(targets)}")
    source_checks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        source = row.get("source_code")
        if not isinstance(source, dict) or not isinstance(source.get("path"), str):
            raise ValueError("operator row lacks a pinned source-code object")
        relative = source["path"]
        if relative in seen:
            continue
        seen.add(relative)
        path = WORKTREE / relative
        actual_source = sha256_file(path)
        expected_source = source.get("sha256")
        size = path.stat().st_size
        match = actual_source == expected_source and size == int(
            source.get("bytes", -1)
        )
        source_checks.append(
            {
                "path": str(path),
                "bytes": size,
                "sha256_expected": expected_source,
                "sha256_actual": actual_source,
                "match": match,
            }
        )
    failed = [row["path"] for row in source_checks if not row["match"]]
    if failed:
        raise ValueError(f"operator source-code pin mismatch: {failed}")
    return rows, {
        "path": str(step0_path),
        "sha256": sha256_file(step0_path),
        "operator_table_sha256": actual,
        "operator_rows": len(rows),
        "source_code": source_checks,
        "status": "PASS",
    }


def _checkpoint_pin(d0: dict[str, Any], build: str, filename: str) -> str:
    census = d0["D0-11"]["builds"][build]
    return next(row["sha256"] for row in census["files"] if row["filename"] == filename)


def _verify_inputs(
    d0: dict[str, Any],
    d0_path: Path,
    c0b_path: Path,
    *,
    include_baseline: bool,
) -> dict[str, Any]:
    expected: dict[Path, str] = {
        d0_path: EXPECTED_D0_SHA256,
        DESIGN_MD: EXPECTED_DESIGN_SHA256,
        A16_BINDING: EXPECTED_A16_BINDING_SHA256,
        c0b_path: EXPECTED_C0B_SHA256,
    }
    for build in ("candidate-25", "baseline1pct"):
        if build == "baseline1pct" and not include_baseline:
            continue
        root = Path(d0["D0-11"]["builds"][build]["root"])
        for filename in ("assembled.checkpoint.h5", "transferred.checkpoint.h5"):
            expected[root / filename] = _checkpoint_pin(d0, build, filename)
        bank_targets = d0["D0-0"]["artifacts"][build]["bank_target_checkpoints"]
        for item in bank_targets:
            if build == "candidate-25" or item["target"] in CROSS_RUNG_TARGETS:
                expected[Path(item["path"])] = item["sha256"]

    candidate_root = Path(d0["D0-11"]["builds"]["candidate-25"]["root"])
    found_predecessors: dict[str, Path] = {}
    for path in candidate_root.rglob("*.h5"):
        if path.name in c4.EXPECTED_PREDECESSOR_DIGESTS:
            found_predecessors[path.name] = path
    missing = set(c4.EXPECTED_PREDECESSOR_DIGESTS) - set(found_predecessors)
    if missing:
        raise ValueError(f"missing predecessor bank(s): {sorted(missing)}")
    for filename, path in found_predecessors.items():
        expected[path] = c4.EXPECTED_PREDECESSOR_DIGESTS[filename]

    checks: list[dict[str, Any]] = []
    for path, expected_sha in expected.items():
        actual_sha = sha256_file(path)
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
        raise ValueError(f"P1 input digest mismatch: {failed}")
    return {
        "status": "PASS",
        "files": checks,
        "all_inputs_live_hashed": True,
    }


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


def _operator_row(
    operator_table: list[dict[str, Any]], target: str, stage: str
) -> dict[str, Any]:
    matches = [
        row
        for row in operator_table
        if row.get("target") == target and row.get("stage") == stage
    ]
    if len(matches) != 1:
        raise SurfaceUnavailableError(
            stage,
            {
                "target": target,
                "reason": "registered Step-0 operator row is missing or duplicated",
                "matching_rows": len(matches),
            },
        )
    return matches[0]


def _production_codec(
    raw: np.ndarray,
    donor_values: np.ndarray,
    target: str,
    target_spec: dict[str, Any],
    operator_table: list[dict[str, Any]],
) -> tuple[np.ndarray, dict[str, Any]]:
    row = _operator_row(operator_table, target, "recipient_codec")
    if row.get("surface_status") != "DERIVED_FROM_PERSISTED_RAW":
        raise SurfaceUnavailableError(
            "recipient_codec",
            {
                "target": target,
                "reason": "Step-0 does not authorize deterministic derivation from raw",
                "operator_row": row,
            },
        )
    try:
        from microcosm.build.us_runtime import acs_transfer

        donor_series = pd.Series(np.asarray(donor_values), name=target)
        encoding = acs_transfer._target_encoding(donor_series, target=target)
        production = acs_transfer._prediction_values(
            np.asarray(raw, dtype=np.float64),
            encoding=encoding,
            entity=target_spec["entity"],
            target=target,
        )
        decoded = replay.as_float(np.asarray(production))
    except Exception as error:
        raise SurfaceUnavailableError(
            "recipient_codec",
            {
                "target": target,
                "reason": "registered production codec could not be replayed",
                "error_type": type(error).__name__,
                "error": str(error),
                "operator_row": row,
            },
        ) from error
    if len(decoded) != len(raw):
        raise SurfaceUnavailableError(
            "recipient_codec",
            {
                "target": target,
                "reason": "production codec changed row count",
                "raw_rows": len(raw),
                "decoded_rows": len(decoded),
                "operator_row": row,
            },
        )
    support = getattr(encoding, "support", None)
    return decoded, {
        "status": "AVAILABLE_REPLAYED",
        "kind": encoding.kind,
        "model_target": encoding.model_target,
        "support_identity": (
            None if support is None else array_identity(np.asarray(support))
        ),
        "source_code": row["source_code"],
        "source_anchor": row["source_anchor"],
        "transformation": row["transformation"],
        "raw_identity": array_identity(np.asarray(raw, dtype=np.float64)),
        "decoded_identity": array_identity(decoded),
        "bitwise_equal": np.array_equal(
            np.asarray(raw, dtype=np.float64).view(np.uint64),
            decoded.view(np.uint64),
        ),
    }


def _structural_surface(
    data: dict[str, Any],
    aux: dict[str, Any],
    target: str,
    target_spec: dict[str, Any],
    decoded_full: np.ndarray,
    operator_table: list[dict[str, Any]],
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return post-structural values in the target role's recipient order."""
    role = data["roles"][c4.role_for_target(target_spec)]
    physical = role["recipient_physical"]
    row = _operator_row(operator_table, target, "recipient_structural")
    if row.get("surface_status") != "DERIVED_FROM_PERSISTED_RAW":
        raise SurfaceUnavailableError(
            "recipient_structural",
            {
                "target": target,
                "reason": "Step-0 does not authorize structural replay",
                "operator_row": row,
            },
        )
    decoded = np.asarray(decoded_full, dtype=np.float64)
    diagnostic: dict[str, Any] = {
        "status": "AVAILABLE_REPLAYED",
        "structural_rule": "identity",
        "cleared_positive_rows": 0,
        "source_code": row["source_code"],
        "source_anchor": row["source_anchor"],
        "transformation": row["transformation"],
    }
    if target == "weeks_unemployed":
        unemployment = replay.as_float(aux["person"]["unemployment_compensation"])
        if len(unemployment) != len(decoded):
            raise SurfaceUnavailableError(
                "recipient_structural",
                {
                    "target": target,
                    "reason": "UC structural predictor does not align to bank rows",
                    "decoded_rows": len(decoded),
                    "unemployment_rows": len(unemployment),
                    "operator_row": row,
                },
            )
        structural = decoded.copy()
        clear = np.isfinite(structural) & (structural > 0.0) & ~(unemployment > 0.0)
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
        return structural[physical], diagnostic
    if target == "pre_subsidy_care_expenses":
        from microcosm.build.us_runtime.acs_transfer import (
            reconcile_acs_adult_care,
        )

        person = aux["person"]
        mutable = np.isfinite(decoded)
        expenses = replay.as_float(person[target]).copy()
        if len(expenses) != len(decoded):
            raise SurfaceUnavailableError(
                "recipient_structural",
                {
                    "target": target,
                    "reason": "adult-care structural inputs do not align to bank rows",
                    "decoded_rows": len(decoded),
                    "person_rows": len(expenses),
                    "operator_row": row,
                },
            )
        expenses[mutable] = decoded[mutable]
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
        before_positive = mutable & (decoded > 0.0)
        after_positive = mutable & (structural_full > 0.0)
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
    if row.get("transformation") != "identity structural transform":
        raise SurfaceUnavailableError(
            "recipient_structural",
            {
                "target": target,
                "reason": "no registered reader for nonidentity structural transform",
                "operator_row": row,
            },
        )
    return decoded[physical].copy(), diagnostic


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


def _pattern_weight_terms(
    weights: np.ndarray,
    probabilities: np.ndarray,
    sq_total_weight: float,
) -> tuple[float, float]:
    """Return alpha and E2 variance on the conditional S_q denominator."""
    weights = np.asarray(weights, dtype=np.float64)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if len(weights) != len(probabilities) or sq_total_weight <= 0.0:
        raise ValueError("invalid S_q pattern weight terms")
    alpha = float(weights.sum(dtype=np.float64) / sq_total_weight)
    numerator = float(np.dot(np.square(weights), probabilities * (1.0 - probabilities)))
    return alpha, float(numerator / (sq_total_weight * sq_total_weight))


def _pattern_readings(
    data: dict[str, Any],
    target: str,
    c0b_lookup: dict[tuple[str, str], dict[str, Any]],
    sq: np.ndarray,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    target_spec = data["target_specs"][target]
    role = data["roles"][c4.role_for_target(target_spec)]
    recipient_weights = np.asarray(role["recipient_weights"], dtype=np.float64)
    sq_total_weight = float(recipient_weights[sq].sum(dtype=np.float64))
    if sq_total_weight <= 0.0:
        raise ValueError(f"pattern readings require positive S_q weight for {target}")
    contexts: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for _d0_pattern, pattern in zip(
        target_spec["patterns"], role["patterns"], strict=True
    ):
        name = pattern["name"]
        context = c4.fit_gate_context(data, target, name, c0b_lookup)
        contexts[name] = context
        positions = pattern["positions"]
        pattern_sq = sq[positions]
        weights = recipient_weights[positions][pattern_sq]
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
        recipient_sq_probability = recipient_probabilities[pattern_sq]
        alpha = float(weights.sum(dtype=np.float64) / sq_total_weight)
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
            checked_alpha, e2_contribution = _pattern_weight_terms(
                weights, recipient_p, sq_total_weight
            )
            if checked_alpha != alpha:
                raise ValueError(f"pattern alpha changed by leg for {target}/{name}")
            legs[leg] = {
                "m_observed": observed,
                "P_D": donor_level,
                "P_R": recipient_level,
                "e2_conditional_variance_contribution": e2_contribution,
            }
        results.append(
            {
                "pattern": name,
                "alpha": float(alpha),
                "S_q_rows": int(pattern_sq.sum()),
                "S_q_weight_sum": float(weights.sum(dtype=np.float64)),
                "S_q_mask": mask_identity(pattern_sq),
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
    *,
    seed: object = "DETERMINISTIC_NO_RANDOM_STAGE",
) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    stable_ids = np.asarray(stable_ids)
    if not (len(values) == len(weights) == len(stable_ids)):
        raise ValueError("native producer stage arrays do not align")
    if not np.isfinite(values).all() or not np.isfinite(weights).all():
        raise ValueError("native producer stage contains nonfinite values or weights")
    negative = values < 0.0
    positive = values > 0.0
    zero = values == 0.0
    return {
        "status": "AVAILABLE",
        "row_count": int(len(values)),
        "native_row_identity": array_identity(stable_ids),
        "row_mask_digest_basis": "ordered native stable entity IDs",
        "values_identity": array_identity(values),
        "weights_identity": array_identity(weights),
        "seed": seed,
        "unweighted_sign_counts": {
            "negative": int(negative.sum()),
            "zero": int(zero.sum()),
            "positive": int(positive.sum()),
        },
        "weighted_sign_mass": {
            "negative": float(weights[negative].sum(dtype=np.float64)),
            "zero": float(weights[zero].sum(dtype=np.float64)),
            "positive": float(weights[positive].sum(dtype=np.float64)),
        },
        "incidence": {
            leg: _weighted_summary(values, weights, sign=sign)["value"]
            for leg, sign in LEGS.items()
        },
    }


def _boundary_bridge(
    values: np.ndarray,
    weights: np.ndarray,
    *,
    stage: str,
) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if len(values) != len(weights):
        raise ValueError("boundary bridge value/weight length mismatch")
    boundary = (values != 0.0) & (np.abs(values) <= ZERO_ATOL)
    legs: dict[str, Any] = {}
    for leg, sign in LEGS.items():
        exact = _weighted_summary(values, weights, sign=sign)
        qrf = _weighted_summary(values, weights, sign=sign, atol=ZERO_ATOL)
        legs[leg] = {
            "value": float(exact["value"] - qrf["value"]),
            "exact_incidence": exact["value"],
            "qrf_incidence": qrf["value"],
            "same_weight_sum": exact["weight_sum"],
        }
    return {
        "id": f"B1|{stage}|boundary_bridge",
        "status": "AVAILABLE",
        "nonadditive": True,
        "boundary_rows": int(boundary.sum()),
        "boundary_weight_mass": float(weights[boundary].sum(dtype=np.float64)),
        "boundary_mask": mask_identity(boundary),
        "legs": legs,
        "value": {leg: row["value"] for leg, row in legs.items()},
        "rule": "same-row exact-sign incidence minus 1e-6 QRF-sign incidence",
    }


def _producer_ledger(
    operator_table: list[dict[str, Any]],
    target: str,
    projection: dict[str, dict[str, np.ndarray]],
    bank: dict[str, Any],
    fit_contexts: dict[str, dict[str, Any]],
    sq_values: np.ndarray,
    sq_weights: np.ndarray,
    sq_ids: np.ndarray,
    decoded: np.ndarray,
    structural: np.ndarray,
) -> dict[str, Any]:
    operator_rows = [row for row in operator_table if row.get("target") == target]
    if not operator_rows:
        raise ValueError(f"no sealed operator rows for {target}")
    seeds = {
        step["pattern"]: int(step["state_after"]["model_config"]["seed"])
        for step in bank["metadata"]["pattern_steps"]
    }
    recipient_seed = {"kind": "per_pattern_model_seed", "values": seeds}
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
                    seed="DETERMINISTIC_PERSISTED_PROJECTION",
                )
            )
        elif stage == "recipient_raw_draw":
            row.update(
                _native_stage_payload(
                    sq_values, sq_weights, sq_ids, seed=recipient_seed
                )
            )
        elif stage == "recipient_codec":
            row.update(
                _native_stage_payload(decoded, sq_weights, sq_ids, seed=recipient_seed)
            )
        elif stage == "recipient_structural":
            row.update(
                _native_stage_payload(
                    structural, sq_weights, sq_ids, seed=recipient_seed
                )
            )
        elif status in {"NO_SURFACE", "PERSISTED_ONLY_AFTER_PRODUCER"}:
            row.update(
                {
                    "status": "NO_SURFACE",
                    "value": "NA",
                    "se": "NA",
                    "seed": {
                        "status": "UNAVAILABLE",
                        "reason": "the sealed stage has no persisted row surface or seed receipt",
                    },
                    "evidence": (
                        "The sealed A16-20 operator table declares no distinct persisted "
                        "surface. A15.21 forbids whole-pipeline replay or guessing."
                    ),
                }
            )
        elif status == "PERSISTED_METADATA":
            fit_patterns: list[dict[str, Any]] = []
            for pattern, context in fit_contexts.items():
                if len(context["donor_y"]) != len(projection["J1"]["stable_ids"]):
                    raise SurfaceUnavailableError(
                        "transfer_fit_rows",
                        {
                            "target": target,
                            "pattern": pattern,
                            "reason": "fit-row metadata cannot align to J1 stable IDs",
                        },
                    )
                fit_patterns.append(
                    {
                        "pattern": pattern,
                        **_native_stage_payload(
                            context["donor_y"],
                            context["donor_weights"],
                            projection["J1"]["stable_ids"],
                            seed=seeds[pattern],
                        ),
                    }
                )
            row.update(
                {
                    "status": "AVAILABLE_METADATA_AND_REPLAYED_FIT_SURFACES",
                    "pattern_steps": len(bank["metadata"]["pattern_steps"]),
                    "bank_path": str(bank["path"]),
                    "patterns": fit_patterns,
                    "aggregation": (
                        "per-pattern only; overlapping fit populations are not "
                        "invented as one aggregate stage"
                    ),
                    "seed": recipient_seed,
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

    boundary_bridge = _boundary_bridge(
        projection["J1"]["values"],
        projection["J1"]["weights"],
        stage="J1_donor_projection",
    )

    clone_bridge: dict[str, Any] = {
        "status": "UNAVAILABLE",
        "evidence": "J0 and J1 native source populations do not align one-to-one",
    }
    j0 = projection["J0"]
    j1 = projection["J1"]
    if len(j0["source_ids"]) == len(j1["source_ids"]):
        joined = _stable_join(j1["source_ids"], j0["source_ids"])
        if np.array_equal(j1["source_ids"][joined], j0["source_ids"]):
            clone_bridge = {
                "status": "AVAILABLE",
                "rows": int(len(j0["source_ids"])),
                "source_id_identity": array_identity(j0["source_ids"]),
                "seed": "DETERMINISTIC_PERSISTED_CLONE_PROJECTION",
                "J0_native": _native_stage_payload(
                    j0["values"],
                    j0["weights"],
                    j0["stable_ids"],
                    seed="DETERMINISTIC_PERSISTED_PROJECTION",
                ),
                "J1_on_J0_rows_and_weights": _native_stage_payload(
                    j1["values"][joined],
                    j0["weights"],
                    j0["stable_ids"],
                    seed="DETERMINISTIC_PERSISTED_CLONE_PROJECTION",
                ),
                "J1_native": _native_stage_payload(
                    j1["values"],
                    j1["weights"],
                    j1["stable_ids"],
                    seed="DETERMINISTIC_PERSISTED_PROJECTION",
                ),
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
    clone2 = projection["clone2"]
    clone2_payload = _native_stage_payload(
        clone2["values"],
        clone2["weights"],
        clone2["stable_ids"],
        seed="DETERMINISTIC_PERSISTED_PROJECTION",
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
        if housing["value"] == "NA":
            base: dict[str, Any] = {
                "value": "NA",
                "se": "NA",
                "variance": "NA",
                "status": "INAPPLICABLE_EMPTY_HOUSING_STRATUM",
            }
        else:
            base_variance = float(j0_levels[leg]["variance"]) + float(
                housing["variance"]
            )
            base = {
                "value": float(j0_levels[leg]["value"] - housing["value"]),
                "se": float(math.sqrt(max(base_variance, 0.0))),
                "variance": base_variance,
                "status": "AVAILABLE_DESCRIPTIVE",
                "variance_rule": "independent_Kish_binomial_delta",
            }
        adjustments: dict[str, Any] = {}
        for label in ("2", "3", "U"):
            stratum = output["strata"][label]
            level = stratum["legs"][leg]
            if level["value"] == "NA" or housing["value"] == "NA":
                adjustments[label] = {
                    "value": "NA",
                    "se": "NA",
                    "variance": "NA",
                    "status": "INAPPLICABLE_EMPTY_STRATUM",
                    "omega_fixed": float(stratum["omega"]),
                }
            else:
                omega = float(stratum["omega"])
                variance = (
                    omega
                    * omega
                    * (float(housing["variance"]) + float(level["variance"]))
                )
                adjustments[label] = {
                    "value": float(omega * (housing["value"] - level["value"])),
                    "se": float(math.sqrt(max(variance, 0.0))),
                    "variance": float(variance),
                    "status": (
                        "AVAILABLE_F4"
                        if label in {"2", "3"}
                        else "AVAILABLE_DESCRIPTIVE"
                    ),
                    "omega_fixed": omega,
                    "variance_rule": "independent_Kish_binomial_delta",
                }
        output["legs"][leg] = {
            "J0_minus_I_H": base,
            "adjustment_TYPEHUGQ_2": adjustments["2"],
            "adjustment_TYPEHUGQ_3": adjustments["3"],
            "adjustment_unprojectable": adjustments["U"],
        }
    return output


def _b2_telescope(
    j1_levels: dict[str, dict[str, Any]],
    j2_levels: dict[str, dict[str, Any]],
    patterns: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute the cumulative A16-22 donor-selection telescope."""
    if not patterns:
        raise ValueError("B2 telescope has no patterns")
    if not math.isclose(
        math.fsum(float(row["alpha"]) for row in patterns),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-14,
    ):
        raise ValueError("B2 pattern alphas do not close")
    stage_specs = (
        ("role_channel", "role_mask", "native_weights"),
        ("family_complete_case", "family_mask", "native_weights"),
        (
            "pattern_predictor_complete_case",
            "predictor_mask",
            "native_weights",
        ),
        ("weight_basis", "predictor_mask", "fit_weights"),
    )
    diagnostics: list[dict[str, Any]] = []
    per_pattern_levels: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for pattern in patterns:
        values = np.asarray(pattern["values"], dtype=np.float64)
        native_weights = np.asarray(pattern["native_weights"], dtype=np.float64)
        fit_weights = np.asarray(pattern["fit_weights"], dtype=np.float64)
        masks = {
            name: np.asarray(pattern[name], dtype=bool)
            for name in ("role_mask", "family_mask", "predictor_mask")
        }
        if not all(
            len(array) == len(values)
            for array in (*masks.values(), native_weights, fit_weights)
        ):
            raise ValueError(f"B2 arrays do not align for {pattern['pattern']}")
        if np.any(masks["family_mask"] & ~masks["role_mask"]) or np.any(
            masks["predictor_mask"] & ~masks["family_mask"]
        ):
            raise ValueError(f"B2 masks are not cumulative for {pattern['pattern']}")
        if (
            not np.isfinite(values[masks["role_mask"]]).all()
            or not np.isfinite(native_weights[masks["role_mask"]]).all()
            or not np.isfinite(fit_weights[masks["predictor_mask"]]).all()
            or (native_weights[masks["role_mask"]] <= 0.0).any()
            or (fit_weights[masks["predictor_mask"]] <= 0.0).any()
        ):
            raise ValueError(
                f"invalid B2 value/weight surface for {pattern['pattern']}"
            )
        pattern_levels: dict[str, dict[str, dict[str, Any]]] = {leg: {} for leg in LEGS}
        stage_rows: dict[str, Any] = {}
        for stage, mask_name, weight_name in stage_specs:
            mask = masks[mask_name]
            weights = native_weights if weight_name == "native_weights" else fit_weights
            if not mask.any():
                raise SurfaceUnavailableError(
                    "B2",
                    {
                        "pattern": pattern["pattern"],
                        "stage": stage,
                        "reason": "cumulative selection produced an empty fit population",
                    },
                )
            stage_rows[stage] = {
                "row_count": int(mask.sum()),
                "row_mask": mask_identity(mask),
                "weight_identity": array_identity(weights[mask]),
                "weight_basis": weight_name,
            }
            for leg, sign in LEGS.items():
                pattern_levels[leg][stage] = _weighted_summary(
                    values[mask], weights[mask], sign=sign
                )
        per_pattern_levels[pattern["pattern"]] = pattern_levels
        diagnostics.append(
            {
                "pattern": pattern["pattern"],
                "alpha": float(pattern["alpha"]),
                "seed": pattern.get("seed", "UNAVAILABLE"),
                "stages": stage_rows,
                "levels": pattern_levels,
                "collapsed": bool(pattern.get("collapsed", False)),
            }
        )

    legs: dict[str, Any] = {}
    for leg in LEGS:
        aggregate: dict[str, dict[str, Any]] = {"J1": j1_levels[leg]}
        for stage, _mask_name, _weight_name in stage_specs:
            aggregate[stage] = _combined_level(
                [
                    (
                        float(pattern["alpha"]),
                        per_pattern_levels[pattern["pattern"]][leg][stage],
                    )
                    for pattern in patterns
                ]
            )
        aggregate["pattern_standardization"] = j2_levels[leg]
        transitions = (
            ("role_channel", "J1", "role_channel"),
            (
                "family_complete_case",
                "role_channel",
                "family_complete_case",
            ),
            (
                "pattern_predictor_complete_case",
                "family_complete_case",
                "pattern_predictor_complete_case",
            ),
            (
                "weight_basis",
                "pattern_predictor_complete_case",
                "weight_basis",
            ),
            (
                "pattern_standardization",
                "weight_basis",
                "pattern_standardization",
            ),
        )
        rows = {
            name: _difference(aggregate[before], aggregate[after])
            for name, before, after in transitions
        }
        total = math.fsum(float(row["value"]) for row in rows.values())
        expected = float(j1_levels[leg]["value"] - j2_levels[leg]["value"])
        closure = expected - total
        tolerance = 1e-12 * max(abs(expected), 1.0)
        if abs(closure) > tolerance:
            raise ValueError(f"B2 telescope does not close for {leg}: {closure}")
        legs[leg] = {
            "levels": aggregate,
            "rows": rows,
            "sum": float(total),
            "expected_J1_minus_J2": expected,
            "closure_residual": float(closure),
            "closure_tolerance": float(tolerance),
            "passes": True,
        }
    return {
        "status": "COMPLETE",
        "fixed_order": [name for name, _mask, _weights in stage_specs]
        + ["pattern_standardization"],
        "order_dependence_disclosed": True,
        "patterns": diagnostics,
        "legs": legs,
    }


def _b2_pattern_surfaces(
    data: dict[str, Any],
    target: str,
    projection: dict[str, dict[str, np.ndarray]],
    pattern_results: list[dict[str, Any]],
    contexts: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    target_spec = data["target_specs"][target]
    role = data["roles"][c4.role_for_target(target_spec)]
    family_targets = [
        name
        for name, spec in data["target_specs"].items()
        if spec["family"] == target_spec["family"]
        and c4.role_for_target(spec) == c4.role_for_target(target_spec)
        and name in role["donor_targets"]
    ]
    family_mask = np.ones(len(projection["J1"]["values"]), dtype=bool)
    for name in family_targets:
        family_mask &= np.isfinite(role["donor_targets"][name])
    output: list[dict[str, Any]] = []
    for reading in pattern_results:
        context = contexts[reading["pattern"]]
        values = np.asarray(context["donor_y"], dtype=np.float64)
        if len(values) != len(projection["J1"]["values"]) or not np.array_equal(
            values.view(np.uint64),
            np.asarray(projection["J1"]["values"], dtype=np.float64).view(np.uint64),
        ):
            raise SurfaceUnavailableError(
                "B2",
                {
                    "target": target,
                    "pattern": reading["pattern"],
                    "reason": "fit rows cannot be aligned exactly to native J1 rows",
                    "fit_rows": len(values),
                    "J1_rows": len(projection["J1"]["values"]),
                },
            )
        predictor_mask = family_mask & np.isfinite(context["donor_x"]).all(axis=1)
        output.append(
            {
                "pattern": reading["pattern"],
                "alpha": reading["alpha"],
                "values": values,
                "native_weights": projection["J1"]["weights"],
                "fit_weights": context["donor_weights"],
                "role_mask": np.ones(len(values), dtype=bool),
                "family_mask": family_mask.copy(),
                "predictor_mask": predictor_mask,
                "seed": int(context["gate_seed"]),
                "collapsed": len(context["gate_classes"]) == 1,
            }
        )
    return output


def _run_candidate_target(
    data: dict[str, Any],
    aux: dict[str, Any],
    operator_table: list[dict[str, Any]],
    c0b_lookup: dict[tuple[str, str], dict[str, Any]],
    target: str,
) -> dict[str, Any]:
    target_spec = data["target_specs"][target]
    role = data["roles"][c4.role_for_target(target_spec)]
    bank = data["current_banks"][target]
    projection = _projection(aux, target, target_spec)
    raw_full = np.asarray(bank["raw"], dtype=np.float64)
    decoded_full, codec_diagnostic = _production_codec(
        raw_full,
        projection["J1"]["values"],
        target,
        target_spec,
        operator_table,
    )
    raw_role = raw_full[role["recipient_physical"]]
    decoded_role = decoded_full[role["recipient_physical"]]
    scope = np.asarray(role["recipient_clone0"], dtype=bool)
    scope_positions = np.flatnonzero(scope)
    path_census = _path_census(
        np.ones(len(scope_positions), dtype=bool),
        np.ones(len(scope_positions), dtype=bool),
        np.isfinite(raw_role[scope]),
        np.isfinite(decoded_role[scope]),
    )
    sq = np.zeros(len(scope), dtype=bool)
    sq[scope_positions[path_census.pop("_passed")]] = True
    so = scope & ~sq
    scope_weights = np.asarray(role["recipient_weights"], dtype=np.float64)[scope]
    sq_weights = np.asarray(role["recipient_weights"], dtype=np.float64)[sq]
    scope_weight_sum = float(scope_weights.sum(dtype=np.float64))
    if scope_weight_sum <= 0.0:
        raise ValueError(f"P0 scope has no positive weight for {target}")
    phi = float(sq_weights.sum(dtype=np.float64) / scope_weight_sum)
    structural_role, structural_diagnostic = _structural_surface(
        data, aux, target, target_spec, decoded_full, operator_table
    )
    terminal_role = _terminal_on_role(aux, role, target, target_spec)
    precal_role = terminal_role.copy()
    precal_role[sq] = structural_role[sq]
    terminal_compare = sq
    structural_terminal_unequal = terminal_compare & (
        np.asarray(structural_role).view(np.uint64)
        != np.asarray(terminal_role).view(np.uint64)
    )
    if structural_terminal_unequal.any():
        raise SurfaceUnavailableError(
            "recipient_structural",
            {
                "target": target,
                "reason": "replayed post-structural surface disagrees with pinned terminal",
                "unequal_rows": int(structural_terminal_unequal.sum()),
                "unequal_mask": mask_identity(structural_terminal_unequal),
                "operator_row": _operator_row(
                    operator_table, target, "recipient_structural"
                ),
            },
        )

    receipt = _receipt_for_target(data["d0"], target)
    full_drawn = np.isfinite(raw_full)
    d0_lineage = next(
        row for row in data["d0"]["D0-4"]["targets"] if row["target"] == target
    )
    raw_digest_matches_d0 = (
        bank["metadata"]["raw_draw_sha256"] == d0_lineage["raw_draw_sha256"]
    )
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
        "raw_draw_digest_matches_D0_4": raw_digest_matches_d0,
        "path_census": path_census,
        "receipt": receipt,
    }
    if not p0["full_bank_matches_receipt"] or not raw_digest_matches_d0:
        raise ValueError(f"A17/P0 mask recovery failed for {target}")
    if phi == 0.0:
        raise SurfaceUnavailableError(
            "conditional_P1",
            {
                "target": target,
                "reason": "S_q has zero artifact weight; only the L0 branch is defined",
                "P0": p0,
            },
        )

    pattern_results, contexts = _pattern_readings(data, target, c0b_lookup, sq)
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
    j2_by_leg = {
        leg: _combined_level(
            [(row["alpha"], row["legs"][leg]["m_observed"]) for row in pattern_results]
        )
        for leg in LEGS
    }
    b2 = _b2_telescope(
        j1_levels,
        j2_by_leg,
        _b2_pattern_surfaces(data, target, projection, pattern_results, contexts),
    )
    levels_by_leg: dict[str, Any] = {}
    ledger_by_leg: dict[str, Any] = {}
    for leg, sign in LEGS.items():
        j2 = j2_by_leg[leg]
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
        if so.any():
            l0 = _difference(j0_levels[leg], i_o, scale=1.0 - phi)
            l0["empty_set"] = False
        else:
            l0 = {
                "value": 0.0,
                "se": 0.0,
                "variance": 0.0,
                "empty_set": True,
            }
        rows = {
            "L0": l0,
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
    b2["phi_fixed"] = phi
    for leg in LEGS:
        for subrow in b2["legs"][leg]["rows"].values():
            subrow["ledger_value"] = float(phi * subrow["value"])
            subrow["ledger_variance"] = float(phi * phi * subrow["variance"])
            subrow["ledger_se"] = float(math.sqrt(max(subrow["ledger_variance"], 0.0)))
        scaled_sum = math.fsum(
            row["ledger_value"] for row in b2["legs"][leg]["rows"].values()
        )
        b2["legs"][leg]["scaled_sum"] = float(scaled_sum)
        b2["legs"][leg]["top_level_B2"] = ledger_by_leg[leg]["rows"]["B2"]
        if not math.isclose(
            scaled_sum,
            float(ledger_by_leg[leg]["rows"]["B2"]["value"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError(f"scaled B2 subrows do not close for {target}/{leg}")
    p6 = _producer_ledger(
        operator_table,
        target,
        projection,
        bank,
        contexts,
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
                "terminal_replay_gate": "PASS",
            },
            "codec": {
                **codec_diagnostic,
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
    return _baseline_basic_result(
        target,
        bank,
        scope,
        sq,
        assembled_weights[scope],
        raw_weights,
        j0,
        iq,
        d_level,
    )


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
    return _baseline_basic_result(
        target,
        bank,
        scope,
        sq,
        weights[scope],
        weights[sq],
        j0,
        iq,
        d_level,
    )


def _baseline_basic_result(
    target: str,
    bank: dict[str, Any],
    scope: np.ndarray,
    sq: np.ndarray,
    scope_weights: np.ndarray,
    sq_weights: np.ndarray,
    j0: dict[str, Any],
    iq: dict[str, Any],
    d_level: dict[str, Any],
) -> dict[str, Any]:
    phi = float(
        np.asarray(sq_weights, dtype=np.float64).sum(dtype=np.float64)
        / np.asarray(scope_weights, dtype=np.float64).sum(dtype=np.float64)
    )
    return {
        "status": "PARTIAL_DECLARED_CROSS_RUNG_PRIORITY",
        "target": target,
        "leg": "positive",
        "P0": {
            "scope_rows": int(scope.sum()),
            "S_q_rows": int(sq.sum()),
            "phi": phi,
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
    c0b_path: Path,
    step0_path: Path,
    *,
    include_baseline: bool,
) -> dict[str, Any]:
    started = time.time()
    d0 = json.loads(d0_path.read_text())
    c0b_evidence = json.loads(c0b_path.read_text())
    operator_table, step0_verification = _load_operator_table(step0_path)
    input_verification = _verify_inputs(
        d0,
        d0_path,
        c0b_path,
        include_baseline=include_baseline,
    )
    lookup = _c0b_lookup(c0b_evidence)
    data = c4.load_analysis_data(d0)
    aux = _load_candidate_aux(data)
    targets: dict[str, Any] = {}
    for target in TARGETS:
        target_started = time.time()
        try:
            targets[target] = _run_candidate_target(
                data, aux, operator_table, lookup, target
            )
        except SurfaceUnavailableError as error:
            targets[target] = {
                "status": "FAIL_CLOSED_SURFACE_UNAVAILABLE",
                "target": target,
                "stage": error.stage,
                "evidence": error.evidence,
            }
        targets[target]["elapsed_seconds"] = time.time() - target_started
    baseline = (
        _run_baseline(d0)
        if include_baseline
        else {
            target: {"status": "NOT_RUN_COMMAND_OPTION"}
            for target in CROSS_RUNG_TARGETS
        }
    )
    unavailable = [
        target
        for target, result in targets.items()
        if result["status"] == "FAIL_CLOSED_SURFACE_UNAVAILABLE"
    ]
    output = {
        "artifact_kind": "qrf_drift_phase0_p0_p1_p6_p7",
        "schema_version": 1,
        "status": (
            "PARTIAL_SURFACE_UNAVAILABLE"
            if unavailable
            else ("COMPLETE" if include_baseline else "COMPLETE_CANDIDATE_ONLY")
        ),
        "unavailable_targets": unavailable,
        "authority": {
            "D0": {"path": str(d0_path), "sha256": sha256_file(d0_path)},
            "design": {
                "path": str(DESIGN_MD),
                "sha256": sha256_file(DESIGN_MD),
            },
            "A16_binding": {
                "path": str(A16_BINDING),
                "sha256": sha256_file(A16_BINDING),
            },
            "direct_C0b_evidence": {
                "path": str(c0b_path),
                "sha256": sha256_file(c0b_path),
                "patterns": len(lookup),
            },
            "sealed_step0_operator_source": step0_verification,
            "input_verification": input_verification,
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
    parser.add_argument("--c0b-json", type=Path, default=DEFAULT_C0B)
    parser.add_argument("--step0-json", type=Path, default=DEFAULT_STEP0)
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
        args.c0b_json.resolve(),
        args.step0_json.resolve(),
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
