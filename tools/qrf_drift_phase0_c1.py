#!/usr/bin/env python3
"""Run the A18 Phase-0 C1 gate-scoped cross-fitting probe.

C1 is a post-reading scientific probe, not an instrument control.  This
executor therefore refuses to load the pinned fit surfaces until three
prerequisites have been sealed: the A18 branch-2 adoption, the fresh and
powered re-targeted C3 result, and an explicit reading-completion artifact.

The implementation follows A15 findings 40--44 and the A16 closure text:

* original support-household source IDs define clusters;
* one global four-repeat household partition is shared by every target;
* each target/pattern/repeat has five held-out HGB fits with fixed production
  regimes, availability patterns, and complete-case rows;
* a class-lost or failed fit makes the pattern-repeat and target-leg result
  unsupported, without alpha renormalization;
* held-out rows are concatenated before the fit-weight Hajek estimand is
  formed, patterns combine by frozen recipient alpha, and the four repeats
  combine by their mean with SD(ddof=1)/2.

Results are written as canonical per-target shards.  Existing shards are
verified and reused, making ``--targets`` subsets safely resumable.  A full
run emits the 800 sealed fold fragments and 10 F5 target-leg summaries in the
Step-0 ID grammar.  No magnitude forest is loaded or fitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import qrf_drift_phase0_a18_adopt as adoption
import qrf_drift_phase0_a18_g3_splits as enumeration
import qrf_drift_phase0_c4 as c4
import qrf_drift_phase0_replay as replay
import sklearn
from scipy.stats import norm
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "experiments/qrf_drift_validation_design.md"
D0_JSON = ROOT / "experiments/qrf_drift_validation_d0.json"
A16_BINDING = ROOT / "experiments/qrf_drift_validation_a16_binding_texts.md"

DEFAULT_C0B = Path("/private/tmp/qrf_phase0_v22_c0b.json")
DEFAULT_ADOPTION = Path("/private/tmp/qrf_phase0_a18_adoption.json")
DEFAULT_C3 = Path("/private/tmp/qrf_phase0_a18_c3.json")
DEFAULT_OUT_DIR = Path("/private/tmp/qrf_phase0_a18_c1_targets")
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_a18_c1.json")

REPEATS = tuple(range(4))
FOLDS = tuple(range(5))
LEG_CODES = {"negative": -1, "positive": 1}
LEG_ORDER = tuple(LEG_CODES)
REQUIRED_READING_PROBES = ("P0", "P1", "P2", "P5", "P6", "P7")
READING_COMPLETE_KINDS = {
    "qrf_drift_phase0_readings_prerequisite",
    "qrf_drift_phase0_readings",
    "qrf_drift_phase0_p0_p1_p2_p5_p6_p7",
}
READING_COMPLETE_STATUSES = {
    "READINGS_COMPLETE",
    "COMPLETE",
    "COMPLETE_WITH_DECLARED_PRIORITY_OMISSIONS",
}
READING_RECORDED_DISPOSITIONS = {
    "COMPLETE",
    "PASS",
    "NOT_RUN_PRIORITY_RULE",
    "DISPOSITION_RECORDED",
    "NOT_VALIDATED",
    "COMPLETE_WITH_NO_SURFACE",
}


def require(condition: bool, message: str) -> None:
    """Raise a uniform fail-closed error."""
    if not condition:
        raise ValueError(message)


def canonical_sha256(value: Any) -> str:
    """Hash one JSON-safe value with the Phase-0 canonical encoder."""
    return hashlib.sha256(c4.canonical_bytes(value)).hexdigest()


def compact_json_sha256(value: Any) -> str:
    """Hash the compact sorted JSON convention used by the P0/P1 executor."""
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_self_seal(payload: dict[str, Any], label: str) -> str:
    """Verify either supported self-excluding artifact seal."""
    if "canonical_sha256" in payload:
        recorded = payload["canonical_sha256"]
        scope = dict(payload)
        scope.pop("canonical_sha256")
        actual = canonical_sha256(scope)
        require(recorded == actual, f"{label} canonical seal mismatch")
        return str(recorded)
    if "content_sha256" in payload:
        recorded = payload["content_sha256"]
        scope = dict(payload)
        scope.pop("content_sha256")
        actual = compact_json_sha256(scope)
        require(recorded == actual, f"{label} content seal mismatch")
        return str(recorded)
    raise ValueError(f"{label} lacks a supported self-excluding SHA-256 seal")


def load_sealed_json(path: Path, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a JSON object and verify its self seal and file digest."""
    require(path.is_file(), f"missing {label} artifact: {path}")
    payload = json.loads(path.read_text())
    require(isinstance(payload, dict), f"{label} artifact is not a JSON object")
    self_sha = verify_self_seal(payload, label)
    return payload, {
        "path": str(path.resolve()),
        "sha256": c4.sha256_file(path),
        "self_excluding_sha256": self_sha,
    }


def _authority_design_sha(payload: dict[str, Any]) -> str | None:
    authority = payload.get("authority", {})
    for key in ("design", "Design"):
        value = authority.get(key)
        if isinstance(value, dict) and isinstance(value.get("sha256"), str):
            return value["sha256"]
    for value in authority.get("files", []):
        if not isinstance(value, dict) or not isinstance(value.get("path"), str):
            continue
        if Path(value["path"]).resolve() == DESIGN.resolve() and isinstance(
            value.get("sha256"), str
        ):
            return value["sha256"]
    return None


def verify_adoption(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify the compact A18 branch-2 adoption result."""
    payload, source = load_sealed_json(path, "A18 adoption")
    require(
        payload.get("artifact_kind") == "qrf_drift_phase0_a18_branch2_adoption",
        "wrong A18 adoption artifact kind",
    )
    require(payload.get("status") == "SEALED_ADOPTION", "A18 adoption is not sealed")
    require(
        _authority_design_sha(payload)
        == enumeration.EXPECTED_AUTHORITY_DIGESTS[str(DESIGN)],
        "A18 adoption does not bind the operative design",
    )
    live = payload.get("recorded_live_input_verification", {})
    require(
        live.get("status") == "PASS" and live.get("all_match") is True,
        "A18 adoption live-input verification is not a clean PASS",
    )
    step0 = payload.get("step0", {})
    require(
        step0.get("status") == "PASS"
        and step0.get("manifest_count") == adoption.EXPECTED_MANIFEST_COUNT,
        "A18 adoption did not verify the sealed Step-0 manifest",
    )
    roster = payload.get("control_roster", {})
    require(
        roster.get("status") == "PASS"
        and roster.get("K") == adoption.EXPECTED_K
        and roster.get("ordered_ids_sha256") == adoption.EXPECTED_K_DIGEST,
        "A18 adoption control roster changed",
    )
    branch = payload.get("branch2", {})
    require(
        branch.get("branch") == 2
        and branch.get("selected") == adoption.EXPECTED_SELECTED,
        "A18 adoption is not the ratified branch-2 selection",
    )
    controls = payload.get("controls", {})
    adopted = controls.get("adopted_controls", {})
    expected_adopted = ("C0a", "C0b", "C5", "A17_setup", "C4", "C2")
    require(
        all(
            str(adopted.get(name, {}).get("status", "")).startswith("PASS")
            for name in expected_adopted
        ),
        "A18 adoption lacks a required adopted PASS control",
    )
    require(
        controls.get("old_C3_present_in_adopted_controls") is False,
        "A18 adoption incorrectly includes the old C3",
    )
    source["selected_row_sha256"] = branch["selected"]["row_sha256"]
    return payload, source


def verify_c3(
    path: Path,
    adoption_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify that the fresh A18 branch-2 C3 passed recovery and power."""
    payload, source = load_sealed_json(path, "re-targeted C3")
    require(
        payload.get("artifact_kind") == "qrf_drift_phase0_a18_c3",
        "wrong re-targeted C3 artifact kind",
    )
    require(payload.get("status") == "PASS", "re-targeted C3 did not PASS")
    require(
        _authority_design_sha(payload)
        == enumeration.EXPECTED_AUTHORITY_DIGESTS[str(DESIGN)],
        "re-targeted C3 does not bind the operative design",
    )
    require(
        payload.get("scope", {}).get("selection")
        == adoption_payload["branch2"]["selected"],
        "re-targeted C3 selection differs from the adopted A18 selection",
    )
    require(
        payload.get("authority", {}).get("enumeration", {}).get("sha256")
        == adoption_payload.get("evidence", {}).get("enumeration", {}).get("sha256"),
        "re-targeted C3 does not bind the adopted A18 enumeration file",
    )
    require(
        payload.get("input_verification", {}).get("all_match") is True,
        "re-targeted C3 pinned inputs did not verify",
    )
    control = payload.get("control", {})
    summary = payload.get("summary", {})
    require(
        control.get("status") == "PASS"
        and control.get("pass") is True
        and control.get("group_recoveries_pass") is True
        and control.get("power", {}).get("pass") is True,
        "re-targeted C3 recovery or power condition failed",
    )
    require(
        summary.get("terminal_gated_disposition") == "PROCEED"
        and summary.get("all_three_recoveries_pass") is True
        and summary.get("power_check_pass") is True,
        "re-targeted C3 did not authorize readings",
    )
    require(
        payload.get("estimator", {}).get("fixed_replicate_override") is None,
        "non-authoritative fixed-replicate C3 cannot authorize C1",
    )
    roster = payload.get("control_roster", {})
    adopted_roster = adoption_payload.get("control_roster", {})
    require(
        roster.get("overall_K") == adopted_roster.get("K")
        and roster.get("overall_ordered_ids_sha256")
        == adopted_roster.get("ordered_ids_sha256")
        and roster.get("sidak_z") == adopted_roster.get("sidak_z"),
        "re-targeted C3 control roster differs from the adopted roster",
    )
    statistics = payload.get("statistics", [])
    expected_ids = sorted(
        f"r=control|t=child_support_received|p=_|l=_|row=C3_oracle_error|"
        f"g={group}|prior=_|gq=_|d=_|rep=_|fold=_|v=final"
        for group in ("G1", "G2", "G3")
    )
    require(
        sorted(item.get("id") for item in statistics) == expected_ids
        and all(item.get("pass") is True for item in statistics),
        "re-targeted C3 three-cell roster is not a complete PASS",
    )
    source["selected_row_sha256"] = payload["scope"]["selection"]["row_sha256"]
    return payload, source


def _completed_probe_names(payload: dict[str, Any]) -> set[str]:
    candidates = [
        payload.get("completed_readings"),
        payload.get("completed_probes"),
        payload.get("phase_order", {}).get("completed")
        if isinstance(payload.get("phase_order"), dict)
        else None,
        payload.get("readings", {}).get("completed")
        if isinstance(payload.get("readings"), dict)
        else None,
    ]
    for value in candidates:
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return set(value)
        if isinstance(value, dict):
            return {
                str(name)
                for name, status in value.items()
                if status is True
                or str(status).upper() in READING_RECORDED_DISPOSITIONS
            }
    return set()


def verify_readings(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify the explicit barrier proving that readings preceded C1.

    The barrier may be a dedicated small artifact or a sealed combined reading
    bundle.  Either way it must explicitly say that the reading phase is
    complete and record a disposition for every registered pre-C1 probe.
    """
    payload, source = load_sealed_json(path, "readings prerequisite")
    kind = payload.get("artifact_kind")
    require(
        kind in READING_COMPLETE_KINDS,
        f"unsupported readings prerequisite artifact kind: {kind!r}",
    )
    require(
        payload.get("status") in READING_COMPLETE_STATUSES,
        f"readings prerequisite has non-complete status {payload.get('status')!r}",
    )
    phase = payload.get("phase_order", {})
    complete = payload.get("readings_complete") is True or (
        isinstance(phase, dict) and phase.get("readings_complete") is True
    )
    require(complete, "readings prerequisite does not assert completion")
    completed = _completed_probe_names(payload)
    missing = set(REQUIRED_READING_PROBES) - completed
    require(
        not missing, f"readings prerequisite lacks dispositions for {sorted(missing)}"
    )
    next_phase = payload.get("next_phase") or (
        phase.get("next") if isinstance(phase, dict) else None
    )
    require(next_phase == "C1", "readings prerequisite does not place C1 next")
    design_sha = _authority_design_sha(payload)
    require(
        design_sha == enumeration.EXPECTED_AUTHORITY_DIGESTS[str(DESIGN)],
        "readings prerequisite does not bind the operative design",
    )
    source["completed_readings"] = sorted(completed)
    return payload, source


def seed_from_label(label: str) -> int:
    """Return the A15 first-eight-byte, big-endian PCG64 seed."""
    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:8], "big")


def partition_label(repeat: int) -> str:
    return f"qrf-drift-v2.3|C1|repeat-{repeat}"


def gate_label(target: str, pattern: str, repeat: int, fold: int) -> str:
    return f"qrf-drift-v2.3|C1|{target}|{pattern}|{repeat}|{fold}"


def stable_household_partition(
    household_ids: np.ndarray,
    repeat: int,
) -> dict[str, Any]:
    """Return fold assignments indexed by globally sorted unique stable ID."""
    require(repeat in REPEATS, f"invalid C1 repeat {repeat}")
    values = np.asarray(household_ids)
    require(values.ndim == 1 and len(values) > 0, "household IDs must be nonempty 1-D")
    require(
        values.dtype.kind in "iuSU", "household IDs need a stable numeric/string dtype"
    )
    stable_ids = np.unique(values)
    label = partition_label(repeat)
    rng = np.random.Generator(np.random.PCG64(seed_from_label(label)))
    permuted = rng.permutation(stable_ids)
    positions = np.searchsorted(stable_ids, permuted)
    require(
        np.array_equal(stable_ids[positions], permuted),
        "partition permutation lost an ID",
    )
    folds = np.empty(len(stable_ids), dtype=np.int8)
    folds[positions] = np.arange(len(stable_ids), dtype=np.int64) % len(FOLDS)
    return {
        "repeat": repeat,
        "label": label,
        "seed": seed_from_label(label),
        "stable_ids": stable_ids,
        "permuted_ids": permuted,
        "folds_by_stable_id": folds,
    }


def gate_random_state(target: str, pattern: str, repeat: int, fold: int) -> int:
    """Take the low 32 bits of one independent PCG64 raw value."""
    label = gate_label(target, pattern, repeat, fold)
    bit_generator = np.random.PCG64(seed_from_label(label))
    raw = int(bit_generator.random_raw())
    return raw & 0xFFFF_FFFF


def folds_for_rows(
    row_household_ids: np.ndarray,
    partition: dict[str, Any],
) -> np.ndarray:
    """Resolve row clusters against one global partition without hashing."""
    ids = np.asarray(row_household_ids)
    stable_ids = np.asarray(partition["stable_ids"])
    positions = np.searchsorted(stable_ids, ids)
    require(
        (positions < len(stable_ids)).all()
        and np.array_equal(stable_ids[positions], ids),
        "donor household absent from the global C1 partition",
    )
    return np.asarray(partition["folds_by_stable_id"])[positions]


def _fold_dimensions(
    target: str,
    pattern: str,
    leg: str,
    repeat: int,
    fold: int,
) -> dict[str, str]:
    return {
        "rung": "candidate-25",
        "target": target,
        "pattern": pattern,
        "leg": leg,
        "row": "C1_fold_gap",
        "group": "_",
        "prior": "_",
        "gq": "_",
        "decile": "_",
        "repeat": f"{repeat:02d}",
        "fold": f"{fold:02d}",
        "variant": "_",
    }


def _target_dimensions(target: str, leg: str) -> dict[str, str]:
    return {
        "rung": "candidate-25",
        "target": target,
        "pattern": "_",
        "leg": leg,
        "row": "C1_target_gap",
        "group": "_",
        "prior": "_",
        "gq": "_",
        "decile": "_",
        "repeat": "_",
        "fold": "_",
        "variant": "_",
    }


def statistic_id(dimensions: dict[str, str]) -> str:
    """Encode the sealed A16-55 flat ID grammar."""
    return (
        f"r={dimensions['rung']}|t={dimensions['target']}|"
        f"p={dimensions['pattern']}|l={dimensions['leg']}|"
        f"row={dimensions['row']}|g={dimensions['group']}|"
        f"prior={dimensions['prior']}|gq={dimensions['gq']}|"
        f"d={dimensions['decile']}|rep={dimensions['repeat']}|"
        f"fold={dimensions['fold']}|v={dimensions['variant']}"
    )


def target_legs(target_spec: dict[str, Any]) -> tuple[str, ...]:
    present = {
        leg
        for pattern in target_spec["patterns"]
        for leg in pattern["classes"]
        if leg in LEG_CODES
    }
    return tuple(leg for leg in LEG_ORDER if leg in present)


def expected_fold_ids(
    d0: dict[str, Any],
    targets: Iterable[str],
) -> list[str]:
    ids: list[str] = []
    for target in targets:
        spec = d0["D0-2"]["targets"][target]
        for pattern in spec["patterns"]:
            for leg in target_legs(spec):
                for repeat in REPEATS:
                    for fold in FOLDS:
                        ids.append(
                            statistic_id(
                                _fold_dimensions(
                                    target,
                                    pattern["name"],
                                    leg,
                                    repeat,
                                    fold,
                                )
                            )
                        )
    return sorted(ids)


def expected_target_ids(
    d0: dict[str, Any],
    targets: Iterable[str],
) -> list[str]:
    return sorted(
        [
            statistic_id(_target_dimensions(target, leg))
            for target in targets
            for leg in target_legs(d0["D0-2"]["targets"][target])
        ]
    )


def support_for_leg(d0: dict[str, Any], target: str, leg: str) -> dict[str, Any]:
    values = d0["D0-1"]["rungs"]["candidate-25"][target]
    counts = {
        origin: int(
            values[origin]["legs"][leg]["unique_clone_deduplicated_source_rows_clone0"]
        )
        for origin in ("asec", "acs")
    }
    supported = all(value >= 50 for value in counts.values())
    return {
        "status": "SUPPORTED" if supported else "INSUFFICIENT_SUPPORT_NO_VERDICT",
        "floor": 50,
        "asec_unique_sources": counts["asec"],
        "acs_unique_sources": counts["acs"],
        "verdict_eligible": supported,
    }


def pooled_heldout_estimand(folds: list[dict[str, Any]]) -> dict[str, Any]:
    """Form the repeat estimand after concatenating all five held-out folds."""
    unsupported = [item for item in folds if item.get("status") != "SUPPORTED"]
    if unsupported:
        return {
            "status": "UNSUPPORTED",
            "reason": "at least one required held-out fold is unsupported",
            "unsupported_folds": [int(item["fold"]) for item in unsupported],
        }
    require(len(folds) == len(FOLDS), "pooled estimand requires exactly five folds")
    weights = np.concatenate(
        [np.asarray(item["weights"], dtype=np.float64) for item in folds]
    )
    predicted = np.concatenate(
        [np.asarray(item["predicted"], dtype=np.float64) for item in folds]
    )
    observed = np.concatenate(
        [np.asarray(item["observed"], dtype=np.float64) for item in folds]
    )
    require(
        len(weights) == len(predicted) == len(observed) and len(weights) > 0,
        "pooled held-out vectors are misaligned or empty",
    )
    denominator = float(weights.sum(dtype=np.float64))
    require(math.isfinite(denominator) and denominator > 0.0, "invalid held-out weight")
    predicted_numerator = float(np.dot(weights, predicted))
    observed_numerator = float(np.dot(weights, observed))
    predicted_mean = predicted_numerator / denominator
    observed_mean = observed_numerator / denominator
    return {
        "status": "SUPPORTED",
        "value": predicted_mean - observed_mean,
        "predicted_probability": predicted_mean,
        "observed_incidence": observed_mean,
        "fit_weight_sum": denominator,
        "predicted_weighted_sum": predicted_numerator,
        "observed_weighted_sum": observed_numerator,
        "heldout_rows": len(weights),
    }


def combine_pattern_repeat(
    pattern_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Combine fixed-alpha pattern values, propagating any unsupported cell."""
    bad = [item for item in pattern_results if item.get("status") != "SUPPORTED"]
    if bad:
        return {
            "status": "UNSUPPORTED",
            "reason": "required pattern-repeat unavailable; alpha not renormalized",
            "unavailable_patterns": [item["pattern"] for item in bad],
            "alpha_renormalized": False,
        }
    alpha_sum = float(math.fsum(float(item["alpha"]) for item in pattern_results))
    require(abs(alpha_sum - 1.0) <= 1e-12, f"fixed pattern alpha sums to {alpha_sum}")
    value = float(
        math.fsum(
            float(item["alpha"]) * float(item["value"]) for item in pattern_results
        )
    )
    return {
        "status": "SUPPORTED",
        "value": value,
        "alpha_sum": alpha_sum,
        "alpha_renormalized": False,
    }


def repeat_mean_and_se(repeats: list[dict[str, Any]]) -> dict[str, Any]:
    """Average four repeats and compute SD(ddof=1)/2."""
    bad = [item for item in repeats if item.get("status") != "SUPPORTED"]
    if bad:
        return {
            "status": "UNSUPPORTED",
            "value": "NA",
            "se": "NA",
            "reason": "at least one repeat is unsupported",
            "unsupported_repeats": [int(item["repeat"]) for item in bad],
        }
    require(len(repeats) == len(REPEATS), "C1 summary requires four repeats")
    values = np.asarray([item["value"] for item in repeats], dtype=np.float64)
    repeat_variance = float(values.var(ddof=1))
    repeat_sd = float(math.sqrt(repeat_variance))
    return {
        "status": "SUPPORTED",
        "value": float(values.mean(dtype=np.float64)),
        "se": repeat_sd / 2.0,
        "repeat_variance": repeat_variance,
        "repeat_sd": repeat_sd,
        "se_variance": repeat_variance / 4.0,
        "repeat_values": values.tolist(),
        "repeat_values_identity": c4.array_identity(values),
        "se_formula": "SD(ddof=1)/2",
    }


def z_and_p(value: float, se: float) -> tuple[float | str, float]:
    if se == 0.0:
        return (
            (0.0, 1.0)
            if value == 0.0
            else (
                "inf" if value > 0.0 else "-inf",
                0.0,
            )
        )
    z = value / se
    return float(z), float(2.0 * norm.sf(abs(z)))


def holm_f5(statistics: list[dict[str, Any]], full_family: bool) -> dict[str, Any]:
    """Apply the A16-47 F5 Holm rule when all target shards are present."""
    if not full_family:
        for item in statistics:
            item["holm_status"] = "DEFERRED_UNTIL_FULL_F5_FAMILY"
            item["holm_reject"] = "NA"
            item["loaded"] = "NA"
        return {"status": "DEFERRED_PARTIAL_TARGET_SET", "family_size": "NA"}

    finite: list[dict[str, Any]] = []
    for item in statistics:
        if item.get("estimator_status") != "SUPPORTED":
            item["holm_status"] = "EXCLUDED_UNSUPPORTED"
            item["holm_reject"] = "NA"
            item["loaded"] = False
            continue
        value = float(item["value"])
        se = float(item["se"])
        z, p = z_and_p(value, se)
        item["z"] = z
        item["p_two_sided"] = p
        finite.append(item)

    ordered = sorted(
        finite,
        key=lambda item: (
            float(item["p_two_sided"]),
            -abs(float(item["value"]) / float(item["se"]))
            if float(item["se"]) != 0.0
            else (-math.inf if float(item["value"]) != 0.0 else 0.0),
            item["id"],
        ),
    )
    still_rejecting = True
    m = len(ordered)
    order_rows = []
    for index, item in enumerate(ordered):
        threshold = 0.05 / (m - index)
        reject = still_rejecting and float(item["p_two_sided"]) <= threshold
        if not reject:
            still_rejecting = False
        item["holm_status"] = "TESTED"
        item["holm_rank"] = index + 1
        item["holm_threshold"] = threshold
        item["holm_reject"] = reject
        item["loaded"] = abs(float(item["value"])) >= 3.0 * float(item["se"]) and reject
        order_rows.append(
            {"id": item["id"], "p": item["p_two_sided"], "reject": reject}
        )
    return {
        "status": "COMPLETE",
        "family_size": m,
        "alpha": 0.05,
        "order": order_rows,
        "order_sha256": canonical_sha256(order_rows),
    }


def _column_available(
    checkpoint: replay.SelectedCheckpoint, table: str, name: str
) -> bool:
    spec = checkpoint.metadata["tables"][checkpoint.table_index[table]]
    return any(item["name"] == name for item in spec["columns"])


def load_original_donor_households(data: dict[str, Any]) -> dict[str, Any]:
    """Attach original (pre-clone) support-household IDs to all donor roles."""
    checkpoint = replay.SelectedCheckpoint(data["transferred_path"])
    try:
        require(
            _column_available(checkpoint, "household", "household_source_id"),
            "transferred checkpoint lacks original household_source_id lineage",
        )
        household_ids = checkpoint.column("household", "household_id")
        source_ids = checkpoint.column("household", "household_source_id")
        person_households = checkpoint.column("person", "person_household_id")
        person_spm = checkpoint.column("person", "person_spm_unit_id")
        person_channel = checkpoint.column("person", "person_support_channel")
        person_clone = checkpoint.column("person", "person_support_clone_index")
        spm_ids = checkpoint.column("spm_unit", "spm_unit_id")
        spm_channel = checkpoint.column("spm_unit", "spm_unit_support_channel")
        spm_clone = checkpoint.column("spm_unit", "spm_unit_support_clone_index")
        loaded = list(checkpoint.loaded)
    finally:
        checkpoint.close()

    person_sources = replay.broadcast_by_id(
        household_ids, source_ids, person_households
    )
    early_mask = (person_channel == "asec") & (person_clone == 0)
    late_mask = (person_channel == "asec") & (person_clone == 1)

    spm_positions = np.searchsorted(spm_ids, person_spm)
    require(
        (spm_positions < len(spm_ids)).all()
        and np.array_equal(spm_ids[spm_positions], person_spm),
        "person SPM memberships do not resolve",
    )
    require(
        np.asarray(person_sources).dtype.kind in "iu",
        "household source IDs must be integral",
    )
    low = np.full(len(spm_ids), np.iinfo(np.int64).max, dtype=np.int64)
    high = np.full(len(spm_ids), np.iinfo(np.int64).min, dtype=np.int64)
    sources_i8 = np.asarray(person_sources, dtype=np.int64)
    np.minimum.at(low, spm_positions, sources_i8)
    np.maximum.at(high, spm_positions, sources_i8)
    require(np.array_equal(low, high), "SPM-unit members cross original households")
    group_mask = (spm_channel == "asec") & (spm_clone == 1)

    role_ids = {
        "early_person": np.asarray(person_sources[early_mask]),
        "late_person": np.asarray(person_sources[late_mask]),
        "late_spm_unit": np.asarray(low[group_mask]),
    }
    for role_name, values in role_ids.items():
        role = data["roles"][role_name]
        expected = len(next(iter(role["donor_surface"].values())))
        require(
            len(values) == expected, f"{role_name} donor household alignment changed"
        )
        role["donor_household_source_id"] = values
    global_ids = np.unique(np.concatenate(list(role_ids.values())))
    return {
        "roles": role_ids,
        "global_ids": global_ids,
        "loaded_columns": loaded,
        "source_column": "household.household_source_id",
        "definition": "original pre-clone support household ID",
    }


def _class_counts(labels: np.ndarray) -> dict[str, int]:
    unique, counts = np.unique(labels, return_counts=True)
    return {
        replay.label_name(int(label)): int(count)
        for label, count in zip(unique, counts, strict=True)
    }


def fit_fold(
    context: dict[str, Any],
    row_folds: np.ndarray,
    repeat: int,
    fold: int,
) -> dict[str, Any]:
    """Fit one fixed-regime gate and predict its held-out household fold."""
    x = np.asarray(context["donor_x"], dtype=np.float64)
    labels = np.asarray(context["donor_labels"], dtype=np.int8)
    weights = np.asarray(context["donor_weights"], dtype=np.float64)
    households = np.asarray(context["donor_household_source_id"])
    complete = (
        np.isfinite(x).all(axis=1)
        & np.isfinite(labels)
        & np.isfinite(weights)
        & (weights > 0.0)
    )
    require(complete.all(), "frozen production fit surface contains incomplete rows")
    heldout = complete & (row_folds == fold)
    training = complete & (row_folds != fold)
    label = gate_label(context["target"], context["pattern"], repeat, fold)
    seed = gate_random_state(context["target"], context["pattern"], repeat, fold)
    base: dict[str, Any] = {
        "target": context["target"],
        "pattern": context["pattern"],
        "repeat": repeat,
        "fold": fold,
        "partition_label": partition_label(repeat),
        "gate_label": label,
        "gate_random_state": seed,
        "fixed_regime_classes": [int(value) for value in context["gate_classes"]],
        "fixed_effective_columns": list(context["columns"]),
        "complete_case_mask_reapplied": True,
        "complete_case_rows": int(complete.sum()),
        "complete_case_mask_identity": c4.array_identity(complete.astype(np.uint8)),
        "training_rows": int(training.sum()),
        "heldout_rows": int(heldout.sum()),
        "training_households": int(np.unique(households[training]).size),
        "heldout_households": int(np.unique(households[heldout]).size),
        "training_positions_identity": c4.array_identity(
            np.flatnonzero(training).astype("<i8")
        ),
        "heldout_positions_identity": c4.array_identity(
            np.flatnonzero(heldout).astype("<i8")
        ),
        "heldout_household_identity": c4.array_identity(households[heldout]),
        "full_class_counts": _class_counts(labels),
        "training_class_counts": _class_counts(labels[training]),
    }
    if not training.any() or not heldout.any():
        return {
            **base,
            "status": "UNSUPPORTED_EMPTY_FOLD",
            "failure": "training or held-out complete-case set is empty",
        }
    expected_classes = np.asarray(context["gate_classes"], dtype=np.int8)
    training_classes = np.unique(labels[training])
    if not np.array_equal(training_classes, expected_classes):
        return {
            **base,
            "status": "UNSUPPORTED_CLASS_LOST",
            "observed_training_classes": [int(value) for value in training_classes],
            "failure": "training fold lost at least one fixed production class",
        }
    try:
        gate = HistGradientBoostingClassifier(random_state=seed)
        gate.fit(x[training], labels[training], sample_weight=weights[training])
        fitted_classes = np.asarray(gate.classes_, dtype=np.int8)
        if not np.array_equal(fitted_classes, expected_classes):
            return {
                **base,
                "status": "UNSUPPORTED_CLASS_LOST",
                "observed_fitted_classes": [int(value) for value in fitted_classes],
                "failure": "fitted HGB class roster differs from the fixed regime",
            }
        probabilities = np.asarray(gate.predict_proba(x[heldout]), dtype=np.float64)
        if probabilities.shape != (int(heldout.sum()), len(expected_classes)):
            raise ValueError("held-out probability matrix has the wrong shape")
        if not np.isfinite(probabilities).all():
            raise ValueError("held-out probability matrix is nonfinite")
    except Exception as error:  # scientific unsupported cell, retained as evidence
        return {
            **base,
            "status": "UNSUPPORTED_FIT_FAILED",
            "failure_type": type(error).__name__,
            "failure": str(error),
        }
    return {
        **base,
        "status": "SUPPORTED",
        "fitted_gate_nodes": enumeration.gate_nodes_identity(gate),
        "heldout_probability_identity": c4.array_identity(probabilities),
        "heldout_weight_identity": replay.weight_identity(weights[heldout]),
        "_classes": fitted_classes,
        "_labels": labels[heldout],
        "_weights": weights[heldout],
        "_probabilities": probabilities,
    }


def _public_fit_cell(fit: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in fit.items() if not key.startswith("_")}


def fold_fragment(
    fit: dict[str, Any],
    target: str,
    pattern: str,
    leg: str,
    repeat: int,
    fold: int,
    source: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create one sealed manifest fragment and its in-memory pooling vectors."""
    dimensions = _fold_dimensions(target, pattern, leg, repeat, fold)
    static = {
        "id": statistic_id(dimensions),
        "dimensions": dimensions,
        "record_type": "scalar",
        "family": "F5",
        "gated": False,
    }
    code = LEG_CODES[leg]
    fixed_classes = [int(value) for value in fit["fixed_regime_classes"]]
    if code not in fixed_classes:
        result = {
            **static,
            "status": "NOT_APPLICABLE_CLASS_ABSENT",
            "value": "NA",
            "se": "NA",
            "class_code": code,
            "source": source,
        }
        return result, {"status": result["status"], "fold": fold}
    if fit["status"] != "SUPPORTED":
        result = {
            **static,
            "status": fit["status"],
            "value": "NA",
            "se": "NA",
            "class_code": code,
            "source": source,
        }
        return result, {"status": fit["status"], "fold": fold}

    classes = np.asarray(fit["_classes"])
    position = int(np.flatnonzero(classes == code)[0])
    weights = np.asarray(fit["_weights"], dtype=np.float64)
    predicted = np.asarray(fit["_probabilities"], dtype=np.float64)[:, position]
    observed = (np.asarray(fit["_labels"]) == code).astype(np.float64)
    denominator = float(weights.sum(dtype=np.float64))
    predicted_mean = float(np.dot(weights, predicted) / denominator)
    observed_mean = float(np.dot(weights, observed) / denominator)
    result = {
        **static,
        "status": "SUPPORTED",
        "value": predicted_mean - observed_mean,
        "se": "NA",
        "class_code": code,
        "predicted_probability": predicted_mean,
        "observed_incidence": observed_mean,
        "fit_weight_sum": denominator,
        "heldout_rows": len(weights),
        "source": source,
    }
    pooling = {
        "status": "SUPPORTED",
        "fold": fold,
        "weights": weights,
        "predicted": predicted,
        "observed": observed,
    }
    return result, pooling


def _context_source(
    context: dict[str, Any],
    c0b_row: dict[str, Any],
    input_digests: dict[Path, str],
) -> dict[str, Any]:
    bank_path = Path(context["bank"]["path"]).resolve()
    require(bank_path in input_digests, "C1 target bank is outside verified inputs")
    state = context["state_before_source"]
    state_source: dict[str, Any]
    if state == "reconstructed_start_chain":
        state_source = {"kind": state}
    else:
        state_path = Path(state).resolve()
        require(state_path in input_digests, "C1 predecessor bank is unverified")
        state_source = {
            "kind": "bank",
            "path": str(state_path),
            "sha256": input_digests[state_path],
        }
    return {
        "target_bank": {"path": str(bank_path), "sha256": input_digests[bank_path]},
        "state_before": {
            **state_source,
            "state_sha256": context["state_before_sha256"],
        },
        "adopted_C0b_pattern_sha256": canonical_sha256(c0b_row),
        "frozen_gate_nodes": enumeration.gate_nodes_identity(context["gate"]),
        "frozen_gate_probability_identity": c4.array_identity(
            context["donor_probabilities"]
        ),
        "fixed_columns": list(context["columns"]),
        "fixed_classes": [int(value) for value in context["gate_classes"]],
    }


def run_target(
    data: dict[str, Any],
    d0: dict[str, Any],
    c0b_lookup: dict[tuple[str, str], dict[str, Any]],
    target: str,
    partitions: dict[int, dict[str, Any]],
    input_digests: dict[Path, str],
    prerequisites: dict[str, Any],
) -> dict[str, Any]:
    """Compute one canonical target shard."""
    spec = data["target_specs"][target]
    role_name = c4.role_for_target(spec)
    donor_households = np.asarray(data["roles"][role_name]["donor_household_source_id"])
    legs = target_legs(spec)
    fold_statistics: list[dict[str, Any]] = []
    fit_cells: list[dict[str, Any]] = []
    pattern_repeats: list[dict[str, Any]] = []
    context_sources: list[dict[str, Any]] = []
    pooled: dict[tuple[str, int, str], dict[str, Any]] = {}

    for pattern_spec in spec["patterns"]:
        pattern = pattern_spec["name"]
        context = c4.fit_gate_context(data, target, pattern, c0b_lookup)
        context["donor_household_source_id"] = donor_households
        require(
            len(context["donor_x"]) == len(donor_households),
            f"donor household alignment failed for {target}/{pattern}",
        )
        c0b_row = c0b_lookup[(target, pattern)]
        context_source = _context_source(context, c0b_row, input_digests)
        context_sources.append({"pattern": pattern, **context_source})
        alpha = float(pattern_spec["recipient_weighted_share"])

        for repeat in REPEATS:
            row_folds = folds_for_rows(donor_households, partitions[repeat])
            leg_folds: dict[str, list[dict[str, Any]]] = {leg: [] for leg in legs}
            for fold in FOLDS:
                fit = fit_fold(context, row_folds, repeat, fold)
                class_applicability = {
                    leg: (
                        "APPLICABLE"
                        if LEG_CODES[leg] in fit["fixed_regime_classes"]
                        else "NOT_APPLICABLE_CLASS_ABSENT"
                    )
                    for leg in LEG_ORDER
                }
                public_fit = {
                    **_public_fit_cell(fit),
                    "class_applicability": class_applicability,
                    "source": context_source,
                }
                fit_cells.append(public_fit)
                fragment_source = {
                    "design_sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[
                        str(DESIGN)
                    ],
                    "d0_sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[str(D0_JSON)],
                    "A16_binding_sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[
                        str(A16_BINDING)
                    ],
                    "prerequisites": prerequisites,
                    "gate_context_sha256": canonical_sha256(context_source),
                    "fit_cell": {
                        "target": target,
                        "pattern": pattern,
                        "repeat": repeat,
                        "fold": fold,
                        "sha256": canonical_sha256(public_fit),
                    },
                }
                for leg in legs:
                    fragment, pooling = fold_fragment(
                        fit,
                        target,
                        pattern,
                        leg,
                        repeat,
                        fold,
                        fragment_source,
                    )
                    fold_statistics.append(fragment)
                    leg_folds[leg].append(pooling)

            for leg in legs:
                code = LEG_CODES[leg]
                if code not in [int(value) for value in context["gate_classes"]]:
                    result = {
                        "status": "NOT_APPLICABLE_CLASS_ABSENT",
                        "pattern": pattern,
                        "repeat": repeat,
                        "leg": leg,
                        "alpha": alpha,
                        "value": "NA",
                    }
                else:
                    result = {
                        **pooled_heldout_estimand(leg_folds[leg]),
                        "pattern": pattern,
                        "repeat": repeat,
                        "leg": leg,
                        "alpha": alpha,
                    }
                pooled[(pattern, repeat, leg)] = result
                pattern_repeats.append(result)

    summaries: list[dict[str, Any]] = []
    repeat_results: list[dict[str, Any]] = []
    support: dict[str, Any] = {}
    for leg in legs:
        support[leg] = support_for_leg(d0, target, leg)
        leg_repeats: list[dict[str, Any]] = []
        for repeat in REPEATS:
            combined = combine_pattern_repeat(
                [pooled[(pattern["name"], repeat, leg)] for pattern in spec["patterns"]]
            )
            combined.update({"target": target, "leg": leg, "repeat": repeat})
            repeat_results.append(combined)
            leg_repeats.append(combined)
        summary = repeat_mean_and_se(leg_repeats)
        estimator_status = summary["status"]
        dimensions = _target_dimensions(target, leg)
        statistic: dict[str, Any] = {
            "id": statistic_id(dimensions),
            "dimensions": dimensions,
            "record_type": "scalar",
            "family": "F5",
            "gated": True,
            "status": (
                support[leg]["status"]
                if estimator_status == "SUPPORTED"
                else "UNSUPPORTED"
            ),
            "estimator_status": estimator_status,
            "support": support[leg],
            **{key: value for key, value in summary.items() if key != "status"},
            "holm_status": "PENDING_FULL_F5_FAMILY",
            "source": {
                "design_sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[str(DESIGN)],
                "d0_sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[str(D0_JSON)],
                "prerequisites": prerequisites,
                "fold_fragment_ids_sha256": canonical_sha256(
                    sorted(
                        [
                            item["id"]
                            for item in fold_statistics
                            if item["dimensions"]["leg"] == leg
                        ]
                    )
                ),
            },
        }
        if estimator_status == "SUPPORTED":
            z, p = z_and_p(float(statistic["value"]), float(statistic["se"]))
            statistic["z"] = z
            statistic["p_two_sided"] = p
            statistic["three_se_material"] = abs(float(statistic["value"])) >= (
                3.0 * float(statistic["se"])
            )
        summaries.append(statistic)

    fold_statistics.sort(key=lambda item: item["id"])
    summaries.sort(key=lambda item: item["id"])
    expected_folds = expected_fold_ids(d0, [target])
    expected_summaries = expected_target_ids(d0, [target])
    require(
        [item["id"] for item in fold_statistics] == expected_folds,
        f"C1 fold-cell manifest order changed for {target}",
    )
    require(
        [item["id"] for item in summaries] == expected_summaries,
        f"C1 target-summary manifest order changed for {target}",
    )
    return {
        "artifact_kind": "qrf_drift_phase0_a18_c1_target",
        "schema_version": 1,
        "status": (
            "COMPLETE"
            if all(item["estimator_status"] == "SUPPORTED" for item in summaries)
            else "COMPLETE_WITH_UNSUPPORTED_CELLS"
        ),
        "target": target,
        "target_order": list(data["target_specs"]).index(target),
        "role": role_name,
        "legs": list(legs),
        "prerequisites": prerequisites,
        "global_partitions_sha256": canonical_sha256(
            {
                str(repeat): {
                    "label": partitions[repeat]["label"],
                    "stable_ids": c4.array_identity(partitions[repeat]["stable_ids"]),
                    "folds": c4.array_identity(
                        partitions[repeat]["folds_by_stable_id"]
                    ),
                }
                for repeat in REPEATS
            }
        ),
        "donor_household_source_identity": c4.array_identity(donor_households),
        "context_sources": context_sources,
        "support": support,
        "fit_cells": fit_cells,
        "pattern_repeats": pattern_repeats,
        "target_repeats": repeat_results,
        "statistics": sorted(fold_statistics + summaries, key=lambda item: item["id"]),
        "summary": {
            "fit_cells": len(fit_cells),
            "fold_fragments": len(fold_statistics),
            "target_leg_statistics": len(summaries),
            "supported_fits": sum(item["status"] == "SUPPORTED" for item in fit_cells),
            "unsupported_fits": sum(
                item["status"] != "SUPPORTED" for item in fit_cells
            ),
            "not_applicable_class_records": sum(
                status == "NOT_APPLICABLE_CLASS_ABSENT"
                for item in fit_cells
                for status in item["class_applicability"].values()
            ),
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }


def partition_public_payload(partitions: dict[int, dict[str, Any]]) -> dict[str, Any]:
    return {
        "definition": (
            "global stable-ID sort, independent PCG64 permutation per repeat, "
            "permutation position j assigned to fold j mod 5"
        ),
        "repeat_count": len(REPEATS),
        "fold_count": len(FOLDS),
        "household_count": len(partitions[0]["stable_ids"]),
        "stable_household_ids_identity": c4.array_identity(partitions[0]["stable_ids"]),
        "repeats": [
            {
                "repeat": repeat,
                "label": partitions[repeat]["label"],
                "seed": partitions[repeat]["seed"],
                "permuted_ids_identity": c4.array_identity(
                    partitions[repeat]["permuted_ids"]
                ),
                "folds_by_stable_id_identity": c4.array_identity(
                    partitions[repeat]["folds_by_stable_id"]
                ),
                "fold_household_counts": [
                    int(
                        np.count_nonzero(
                            partitions[repeat]["folds_by_stable_id"] == fold
                        )
                    )
                    for fold in FOLDS
                ],
            }
            for repeat in REPEATS
        ],
    }


def target_shard_path(out_dir: Path, target_order: int, target: str) -> Path:
    return out_dir / f"{target_order:03d}__{target}.json"


def write_canonical(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    c4.write_canonical_result(path, payload)
    return {
        "path": str(path.resolve()),
        "sha256": c4.sha256_file(path),
        "canonical_sha256": payload["canonical_sha256"],
    }


def executor_fingerprint() -> dict[str, Any]:
    """Bind resumable shards to this executor and its replay helpers."""
    paths = (
        Path(__file__),
        Path(adoption.__file__),
        Path(enumeration.__file__),
        Path(c4.__file__),
        Path(replay.__file__),
    )
    files = [
        {"path": str(path.resolve()), "sha256": c4.sha256_file(path)} for path in paths
    ]
    return {
        "files": files,
        "files_sha256": canonical_sha256(files),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
    }


def load_reusable_target(
    path: Path,
    target: str,
    prerequisites: dict[str, Any],
    partition_sha: str,
) -> dict[str, Any]:
    payload, _ = load_sealed_json(path, f"C1 target shard {target}")
    require(
        payload.get("artifact_kind") == "qrf_drift_phase0_a18_c1_target"
        and payload.get("target") == target,
        f"existing C1 shard is for the wrong target: {path}",
    )
    require(
        payload.get("status") in {"COMPLETE", "COMPLETE_WITH_UNSUPPORTED_CELLS"},
        f"existing C1 shard is not complete: {path}",
    )
    require(
        payload.get("prerequisites") == prerequisites, f"stale prerequisites in {path}"
    )
    require(
        payload.get("global_partitions_sha256") == partition_sha,
        f"stale global partition in {path}",
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--readings-json",
        type=Path,
        required=True,
        help="sealed reading-completion barrier; C1 cannot run without it",
    )
    parser.add_argument("--adoption-json", type=Path, default=DEFAULT_ADOPTION)
    parser.add_argument("--c3-json", type=Path, default=DEFAULT_C3)
    parser.add_argument("--c0b-json", type=Path, default=DEFAULT_C0B)
    parser.add_argument(
        "--targets",
        nargs="+",
        help="D0-ordered target subset; rerun with all targets to merge shards",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    adoption_payload, adoption_source = verify_adoption(args.adoption_json)
    _, c3_source = verify_c3(args.c3_json, adoption_payload)
    _, readings_source = verify_readings(args.readings_json)
    prerequisites = {
        "A18_adoption": adoption_source,
        "retargeted_C3": c3_source,
        "readings": readings_source,
        "executor": executor_fingerprint(),
    }

    d0 = json.loads(D0_JSON.read_text())
    input_verification = enumeration.verify_inputs(d0, args.c0b_json)
    input_digests = {
        Path(item["path"]).resolve(): item["sha256_actual"]
        for item in input_verification["files"]
    }
    c0b = json.loads(args.c0b_json.read_text())
    require(
        c0b.get("status") == "PASS"
        and c0b.get("summary", {}).get("e4_bit_identical_pass") is True
        and c0b.get("summary", {}).get("e2_repeated_draw_control_pass") is True,
        "adopted C0b is not a clean E4/E2 PASS",
    )
    c0b_lookup = {(item["target"], item["pattern"]): item for item in c0b["patterns"]}
    data = c4.load_analysis_data(d0)
    household_lineage = load_original_donor_households(data)
    partitions = {
        repeat: stable_household_partition(household_lineage["global_ids"], repeat)
        for repeat in REPEATS
    }
    partition_payload = partition_public_payload(partitions)
    partition_sha = canonical_sha256(
        {
            str(repeat): {
                "label": partitions[repeat]["label"],
                "stable_ids": c4.array_identity(partitions[repeat]["stable_ids"]),
                "folds": c4.array_identity(partitions[repeat]["folds_by_stable_id"]),
            }
            for repeat in REPEATS
        }
    )

    all_targets = list(data["target_specs"])
    targets = args.targets or all_targets
    require(len(targets) == len(set(targets)), "--targets contains duplicates")
    unknown = [target for target in targets if target not in data["target_specs"]]
    require(not unknown, f"unknown target(s): {unknown}")
    require(
        targets == [target for target in all_targets if target in set(targets)],
        "--targets must retain D0 stable order",
    )

    shards: list[dict[str, Any]] = []
    reused: list[str] = []
    computed: list[str] = []
    for target in targets:
        order = all_targets.index(target)
        path = target_shard_path(args.out_dir, order, target)
        if path.is_file():
            target_payload = load_reusable_target(
                path,
                target,
                prerequisites,
                partition_sha,
            )
            reused.append(target)
        else:
            target_payload = run_target(
                data,
                d0,
                c0b_lookup,
                target,
                partitions,
                input_digests,
                prerequisites,
            )
            write_canonical(path, target_payload)
            computed.append(target)
        shards.append(
            {
                "target": target,
                "target_order": order,
                "path": str(path.resolve()),
                "sha256": c4.sha256_file(path),
                "canonical_sha256": target_payload["canonical_sha256"],
                "status": target_payload["status"],
            }
        )

    target_payloads = [
        load_sealed_json(Path(item["path"]), f"C1 target shard {item['target']}")[0]
        for item in shards
    ]
    fold_statistics = sorted(
        [
            statistic
            for payload in target_payloads
            for statistic in payload["statistics"]
            if statistic["dimensions"]["row"] == "C1_fold_gap"
        ],
        key=lambda item: item["id"],
    )
    target_statistics = sorted(
        [
            statistic
            for payload in target_payloads
            for statistic in payload["statistics"]
            if statistic["dimensions"]["row"] == "C1_target_gap"
        ],
        key=lambda item: item["id"],
    )
    require(
        [item["id"] for item in fold_statistics] == expected_fold_ids(d0, targets),
        "aggregate C1 fold-cell roster mismatch",
    )
    require(
        [item["id"] for item in target_statistics] == expected_target_ids(d0, targets),
        "aggregate C1 target-leg roster mismatch",
    )
    full_family = targets == all_targets
    holm = holm_f5(target_statistics, full_family)
    if full_family:
        require(len(fold_statistics) == 800, "full C1 run did not emit 800 fold cells")
        require(len(target_statistics) == 10, "full C1 run did not emit 10 summaries")

    result = {
        "artifact_kind": "qrf_drift_phase0_a18_c1",
        "schema_version": 1,
        "status": "COMPLETE" if full_family else "PARTIAL_TARGETS",
        "scope": {
            "rung": "candidate-25 pre-calibration",
            "targets": targets,
            "all_targets": all_targets,
            "target_count": len(targets),
            "full_target_count": len(all_targets),
            "magnitude_forests_loaded": False,
            "runs_after_readings": True,
        },
        "authority": {
            "design": {
                "path": str(DESIGN),
                "sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[str(DESIGN)],
                "amendment": "v2.7/A18 plus A15 findings 40-44 and A16 bindings 41-43",
            },
            "D0": {
                "path": str(D0_JSON),
                "sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[str(D0_JSON)],
            },
            "A16_binding": {
                "path": str(A16_BINDING),
                "sha256": enumeration.EXPECTED_AUTHORITY_DIGESTS[str(A16_BINDING)],
            },
        },
        "prerequisites": prerequisites,
        "input_verification": input_verification,
        "household_lineage": {
            "definition": household_lineage["definition"],
            "source_column": household_lineage["source_column"],
            "loaded_columns": household_lineage["loaded_columns"],
            "global_identity": c4.array_identity(household_lineage["global_ids"]),
            "role_identities": {
                role: c4.array_identity(values)
                for role, values in household_lineage["roles"].items()
            },
        },
        "partition": partition_payload,
        "estimator": {
            "clusters": "original support household_source_id",
            "global_partition": "one partition per repeat shared across targets",
            "repeats": list(REPEATS),
            "folds": list(FOLDS),
            "gate_seed": "fresh PCG64(label).random_raw() low 32 bits",
            "fold_fit": "production HistGradientBoostingClassifier defaults and fixed regime",
            "fold_failure": "UNSUPPORTED pattern-repeat and target-leg; no alpha renormalization",
            "pattern_repeat": "concatenate five held-out folds before fit-weight Hajek mean",
            "target_repeat": "fixed recipient artifact-weight alpha over patterns",
            "target": "mean over four repeats; SE=SD(ddof=1)/2",
            "F5": "one target-leg statistic; three-SE plus A16-47 Holm loading",
        },
        "shards": shards,
        "resume": {"computed_targets": computed, "reused_targets": reused},
        "holm_F5": holm,
        "statistics": fold_statistics + target_statistics,
        "summary": {
            "fit_cells": sum(
                payload["summary"]["fit_cells"] for payload in target_payloads
            ),
            "fold_fragments": len(fold_statistics),
            "target_leg_statistics": len(target_statistics),
            "expected_full_fold_fragments": 800,
            "expected_full_target_leg_statistics": 10,
            "supported_target_legs": sum(
                item["estimator_status"] == "SUPPORTED" for item in target_statistics
            ),
            "unsupported_target_legs": sum(
                item["estimator_status"] != "SUPPORTED" for item in target_statistics
            ),
            "insufficient_support_no_verdict": [
                item["id"]
                for item in target_statistics
                if item["status"] == "INSUFFICIENT_SUPPORT_NO_VERDICT"
            ],
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }
    output = write_canonical(args.out, result)
    print(
        f"RESULT {output['path']} sha256={output['sha256']} "
        f"status={result['status']} folds={len(fold_statistics)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
