#!/usr/bin/env python3
"""Seal the Phase-0 readings-before-C1 prerequisite.

This is a fail-closed barrier, not a scientific estimator.  It verifies the
sealed controls and every reading artifact required before C1, records any
declared P2 validation failures without upgrading them to valid results, and
emits the compact canonical artifact accepted by the C1 executor.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import qrf_drift_phase0_c1 as c1
import qrf_drift_phase0_c4 as c4
import qrf_drift_phase0_p2 as p2

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "experiments/qrf_drift_validation_design.md"
D0_JSON = ROOT / "experiments/qrf_drift_validation_d0.json"
A16_BINDING = ROOT / "experiments/qrf_drift_validation_a16_binding_texts.md"

DEFAULT_ADOPTION = Path("/private/tmp/qrf_phase0_a18_adoption.json")
DEFAULT_C3 = Path("/private/tmp/qrf_phase0_a18_c3.json")
DEFAULT_P1 = Path("/private/tmp/qrf_phase0_p1.json")
DEFAULT_P2 = Path("/private/tmp/qrf_phase0_a18_p2.json")
DEFAULT_BASELINE = Path("/private/tmp/qrf_phase0_baseline_crossrung.json")
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_readings_prerequisite.json")

A18_COMMIT = "8d553796e846012e7dc2663d7ffe108b6f965cca"
EXPECTED_P5_SHARDS = 6
EXPECTED_CROSS_RUNG_TARGETS = (
    "self_employment_income_last_year",
    "spm_unit_energy_subsidy",
)
EXPECTED_P1_LEGS = {"negative", "positive"}
EXPECTED_GQ_STRATA = {"H", "2", "3", "U"}
EXPECTED_P2_CLOSURES = {"e_D", "e_R", "e_T"}
P2_JOINT_UNAVAILABLE = "UNAVAILABLE_D0_NOT_ENUMERATED"
COMPLETED_READINGS = {
    "P0": "COMPLETE",
    "P1": "COMPLETE",
    "P2": "NOT_VALIDATED",
    "P5": "COMPLETE",
    "P6": "COMPLETE_WITH_NO_SURFACE",
    "P7": "COMPLETE",
}


def require(condition: bool, message: str) -> None:
    """Raise one uniform fail-closed error."""
    if not condition:
        raise ValueError(message)


def _expected_digest(path: Path) -> str:
    return c1.enumeration.EXPECTED_AUTHORITY_DIGESTS[str(path)]


def verify_live_authority() -> dict[str, Any]:
    """Verify and return the operative A18 authority files."""
    files = []
    for path in (DESIGN, D0_JSON, A16_BINDING):
        expected = _expected_digest(path)
        actual = c4.sha256_file(path)
        require(actual == expected, f"operative authority changed: {path}")
        files.append(
            {
                "path": str(path.resolve()),
                "sha256": actual,
            }
        )
    return {
        "amendment": "v2.7/A18",
        "commit": A18_COMMIT,
        "design": files[0],
        "D0": files[1],
        "A16_binding": files[2],
    }


def _authority_file(payload: dict[str, Any], *names: str) -> dict[str, Any]:
    authority = payload.get("authority")
    require(isinstance(authority, dict), "artifact lacks an authority object")
    for name in names:
        value = authority.get(name)
        if isinstance(value, dict):
            return value
    raise ValueError(f"artifact authority lacks every key {names!r}")


def verify_artifact_authority(payload: dict[str, Any], label: str) -> None:
    """Require the artifact to bind the current design and D0 digests."""
    design = _authority_file(payload, "design", "Design")
    d0 = _authority_file(payload, "D0", "d0")
    require(
        design.get("sha256") == _expected_digest(DESIGN),
        f"{label} design authority changed",
    )
    require(
        d0.get("sha256") == _expected_digest(D0_JSON),
        f"{label} D0 authority changed",
    )


def verify_a16_binding_authority(payload: dict[str, Any], label: str) -> None:
    """Require an artifact to bind the exact live A16 closure text."""
    binding = _authority_file(payload, "A16_binding")
    bound_path = binding.get("path")
    require(
        isinstance(bound_path, str)
        and Path(bound_path).resolve() == A16_BINDING.resolve(),
        f"{label} A16 binding path changed",
    )
    actual = c4.sha256_file(A16_BINDING)
    require(
        actual == _expected_digest(A16_BINDING),
        "operative A16 binding authority changed",
    )
    require(
        binding.get("sha256") == actual,
        f"{label} A16 binding authority changed",
    )


def verify_p2_descriptive_defaults_receipt(
    receipt: Any,
) -> dict[str, Any]:
    """Rebuild and exactly reconcile the pre-P2 descriptive-default receipt."""
    require(
        isinstance(receipt, dict),
        "P2 lacks its sealed descriptive-default receipt",
    )
    recorded_path = receipt.get("path")
    require(
        isinstance(recorded_path, str) and Path(recorded_path).is_file(),
        "P2 descriptive-default receipt does not name a live file",
    )
    _payload, expected = p2.verify_reading_defaults(Path(recorded_path))
    require(
        receipt == expected,
        "P2 descriptive-default receipt is not current/exact",
    )
    return expected


def source_record(payload: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """Attach the scientific identity fields to a loaded-file receipt."""
    return {
        **source,
        "artifact_kind": payload.get("artifact_kind"),
        "status": payload.get("status"),
    }


def artifact_record(
    payload: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    """Return the stable direct-reconciliation record used by finalization."""
    record = {
        "path": source["path"],
        "sha256": source["sha256"],
        "canonical_sha256": source["self_excluding_sha256"],
        "artifact_kind": payload.get("artifact_kind"),
        "status": payload.get("status"),
    }
    if "targets" in source:
        record["targets"] = source["targets"]
    return record


def _verify_residual(row: dict[str, Any], label: str) -> None:
    require(row.get("passes") is True, f"{label} residual did not pass")
    value = row.get("value")
    tolerance = row.get("tolerance")
    require(
        isinstance(value, (int, float)) and isinstance(tolerance, (int, float)),
        f"{label} residual lacks numeric value/tolerance",
    )
    require(
        abs(float(value)) <= float(tolerance), f"{label} residual exceeds tolerance"
    )


def _verify_input_checks(checks: dict[str, Any], label: str) -> None:
    status_pass = checks.get("status") == "PASS"
    boolean_pass = checks.get("all_match") is True
    require(status_pass or boolean_pass, f"{label} input verification is not PASS")
    files = checks.get("files", [])
    require(isinstance(files, list), f"{label} input verification files are malformed")
    require(
        all(item.get("match") is True for item in files),
        f"{label} contains a mismatched live input",
    )


def verify_p1(
    path: Path,
    expected_targets: tuple[str, ...],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify the complete primary P0/P1/P6/P7 artifact."""
    payload, source = c1.load_sealed_json(path, "P0/P1/P6/P7")
    require(
        payload.get("artifact_kind") == "qrf_drift_phase0_p0_p1_p6_p7",
        "wrong P0/P1/P6/P7 artifact kind",
    )
    require(payload.get("status") == "COMPLETE", "P0/P1/P6/P7 is not complete")
    verify_artifact_authority(payload, "P0/P1/P6/P7")
    require(
        payload.get("unavailable_targets") in ([], {}),
        "P0/P1/P6/P7 has unavailable targets",
    )
    _verify_input_checks(
        payload.get("authority", {}).get("input_verification", {}),
        "P0/P1/P6/P7",
    )
    targets = payload.get("candidate-25", {}).get("targets")
    require(isinstance(targets, dict), "P0/P1/P6/P7 lacks candidate-25 targets")
    require(set(targets) == set(expected_targets), "P0/P1/P6/P7 target roster changed")

    for target in expected_targets:
        result = targets[target]
        label = f"P0/P1/P6/P7 {target}"
        require(
            result.get("target") == target and result.get("status") == "COMPLETE",
            f"{label} is not complete",
        )
        p0 = result.get("P0", {})
        require(p0.get("status") == "PASS_A17_SCOPE_RECOVERY", f"{label} P0 failed")
        require(p0.get("phi") == 1.0, f"{label} P0 phi changed")
        for field in (
            "full_bank_matches_receipt",
            "raw_draw_digest_matches_D0_5_candidate",
            "raw_rows_match_D0_5_candidate",
            "finite_rows_match_D0_5_candidate",
        ):
            require(p0.get(field) is True, f"{label} P0 check failed: {field}")

        p1 = result.get("P1", {})
        ledger = p1.get("ledger", {})
        require(set(ledger) == EXPECTED_P1_LEGS, f"{label} ledger legs changed")
        for leg in sorted(EXPECTED_P1_LEGS):
            _verify_residual(
                ledger[leg].get("rows", {}).get("residual", {}), f"{label} {leg}"
            )
        b2 = p1.get("B2_diagnostics", {})
        require(b2.get("status") == "COMPLETE", f"{label} B2 is incomplete")
        require(
            set(b2.get("legs", {})) == EXPECTED_P1_LEGS
            and all(item.get("passes") is True for item in b2["legs"].values()),
            f"{label} B2 closure failed",
        )

        p6 = result.get("P6", {})
        require(
            p6.get("status") == "COMPLETE_WITH_NO_SURFACE_ROWS",
            f"{label} P6 lacks its declared NO_SURFACE disposition",
        )
        p7 = result.get("P7", {})
        require(
            set(p7.get("strata", {})) == EXPECTED_GQ_STRATA,
            f"{label} P7 strata changed",
        )
        require(set(p7.get("legs", {})) == EXPECTED_P1_LEGS, f"{label} P7 legs changed")
        for leg, rows in p7["legs"].items():
            require(
                "adjustment_TYPEHUGQ_2" in rows and "adjustment_TYPEHUGQ_3" in rows,
                f"{label} P7 {leg} does not separate TYPEHUGQ 2/3",
            )

    source["targets"] = list(expected_targets)
    return payload, source


def load_baseline(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the baseline artifact using its declared scientific seal scope."""
    require(path.is_file(), f"missing baseline cross-rung artifact: {path}")
    payload = json.loads(path.read_text())
    require(isinstance(payload, dict), "baseline cross-rung is not a JSON object")
    recorded = payload.get("content_sha256")
    require(isinstance(recorded, str), "baseline cross-rung lacks content_sha256")
    scope = {
        key: value
        for key, value in payload.items()
        if key not in {"execution", "content_sha256"}
    }
    actual = c1.compact_json_sha256(scope)
    require(recorded == actual, "baseline cross-rung scientific seal mismatch")
    return payload, {
        "path": str(path.resolve()),
        "sha256": c4.sha256_file(path),
        "self_excluding_sha256": recorded,
        "self_seal_scope": "excludes execution and content_sha256",
    }


def verify_baseline(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify both frozen positive-leg baseline cross-rung readings."""
    payload, source = load_baseline(path)
    require(
        payload.get("artifact_kind") == "qrf_drift_phase0_baseline_crossrung_p0_p1",
        "wrong baseline cross-rung artifact kind",
    )
    require(payload.get("status") == "COMPLETE", "baseline cross-rung is incomplete")
    require(payload.get("rung") == "baseline1pct", "baseline cross-rung rung changed")
    verify_artifact_authority(payload, "baseline cross-rung")
    require(
        payload.get("unavailable_targets") == {}, "baseline has unavailable targets"
    )
    authority = payload.get("authority", {})
    _verify_input_checks(authority.get("input_verification", {}), "baseline cross-rung")
    require(
        authority.get("sealed_step0_operator_source", {}).get("status") == "PASS",
        "baseline Step-0 operator source did not pass",
    )
    targets = payload.get("baseline1pct", {}).get("targets", {})
    require(
        set(targets) == set(EXPECTED_CROSS_RUNG_TARGETS),
        "baseline cross-rung target roster changed",
    )
    for target in EXPECTED_CROSS_RUNG_TARGETS:
        result = targets[target]
        label = f"baseline cross-rung {target}"
        require(
            result.get("target") == target
            and result.get("leg") == "positive"
            and result.get("status") == "COMPLETE",
            f"{label} is incomplete",
        )
        p0 = result.get("P0", {})
        require(
            p0.get("status") == "PASS_A17_BASELINE_SCOPE_AND_TERMINAL",
            f"{label} P0 failed",
        )
        bindings = p0.get("bindings", {})
        require(bindings and all(bindings.values()), f"{label} has a failed P0 binding")
        incidence = result.get("D0_incidence_binding", {})
        require(
            incidence.get("J0_bit_exact") is True
            and incidence.get("I_acs_bit_exact") is True,
            f"{label} does not reproduce D0 incidence exactly",
        )
        _verify_residual(result.get("ledger", {}).get("residual", {}), label)
        b2 = result.get("B2_diagnostics", {})
        require(b2.get("status") == "COMPLETE", f"{label} B2 is incomplete")
        require(
            set(b2.get("legs", {})) == EXPECTED_P1_LEGS
            and all(item.get("passes") is True for item in b2["legs"].values()),
            f"{label} B2 closure failed",
        )
        require(
            result.get("support", {}).get("status") == "SUPPORTED",
            f"{label} lacks frozen support",
        )
    source["targets"] = list(EXPECTED_CROSS_RUNG_TARGETS)
    return payload, source


def _verify_joint_unavailable(value: dict[str, Any], label: str) -> None:
    require(
        value.get("status") == P2_JOINT_UNAVAILABLE
        and value.get("no_predicates_invented") is True
        and value.get("predicates") == []
        and value.get("pattern_invalidation_decision") == "NOT_EVALUABLE"
        and value.get("threshold") == 0.01
        and value.get("violation_share") == "NA",
        f"{label} joint hybrid-domain disposition changed",
    )
    source = value.get("source", {})
    require(
        source.get("checked_pointer") == "/D0-7"
        and source.get("sha256") == _expected_digest(D0_JSON),
        f"{label} joint hybrid-domain source changed",
    )


def _verify_p2_leg(
    value: dict[str, Any],
    label: str,
    closure_counts: Counter[str],
    attribution_counts: Counter[str],
) -> None:
    closures = value.get("closures", {})
    require(set(closures) == EXPECTED_P2_CLOSURES, f"{label} closure roster changed")
    closure_pass = True
    for name in sorted(EXPECTED_P2_CLOSURES):
        item = closures[name]
        status = item.get("status")
        passed = item.get("pass")
        require(status in {"PASS", "FAIL"}, f"{label} {name} has invalid status")
        require(passed is (status == "PASS"), f"{label} {name} status/pass disagree")
        closure_counts[status] += 1
        closure_pass &= bool(passed)
    exact = value.get("exact_shapley_closure", {})
    exact_status = exact.get("status")
    exact_pass = exact.get("pass")
    require(
        exact_status in {"PASS", "FAIL"}, f"{label} exact closure has invalid status"
    )
    require(
        exact_pass is (exact_status == "PASS"),
        f"{label} exact closure status/pass disagree",
    )
    closure_counts[f"exact_{exact_status}"] += 1
    support = value.get("support", {})
    support_pass = support.get("pass") is True
    if support_pass:
        expected = (
            "VALIDATED"
            if closure_pass and exact_pass
            else "NOT_VALIDATED_CLOSURE_FAILURE"
        )
    else:
        require(
            support.get("status") == "INSUFFICIENT_SUPPORT_NO_VERDICT",
            f"{label} unsupported leg lacks its frozen disposition",
        )
        expected = "INSUFFICIENT_SUPPORT_NO_VERDICT"
    actual = value.get("attribution_status")
    require(actual == expected, f"{label} attribution status is inconsistent")
    attribution_counts[str(actual)] += 1


def verify_p2(
    path: Path,
    d0: dict[str, Any],
    adoption_source: dict[str, Any],
    c3_source: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Verify complete P2 computation and its declared non-validation."""
    payload, source = c1.load_sealed_json(path, "P2")
    require(payload.get("artifact_kind") == "qrf_drift_phase0_a18_p2", "wrong P2 kind")
    require(payload.get("status") == "COMPLETE", "P2 is not all-target complete")
    verify_artifact_authority(payload, "P2")
    _verify_input_checks(payload.get("input_verification", {}), "P2")
    prerequisites = payload.get("prerequisites", {})
    require(prerequisites.get("status") == "PASS", "P2 prerequisites did not pass")
    verify_p2_descriptive_defaults_receipt(prerequisites.get("P2_descriptive_defaults"))
    require(
        prerequisites.get("adoption", {}).get("sha256") == adoption_source["sha256"],
        "P2 does not bind the adopted controls input",
    )
    require(
        prerequisites.get("fresh_C3", {}).get("sha256") == c3_source["sha256"],
        "P2 does not bind the fresh C3 input",
    )

    expected_targets = tuple(d0["D0-2"]["targets"])
    scope = payload.get("scope", {})
    require(
        scope.get("all_targets_in_D0_order") == list(expected_targets)
        and scope.get("completed_targets") == list(expected_targets),
        "P2 scope is not complete in D0 order",
    )
    targets = payload.get("targets", [])
    require(
        [item.get("target") for item in targets] == list(expected_targets),
        "P2 target roster/order changed",
    )

    statistics = payload.get("statistics", [])
    ids = [item.get("id") for item in statistics]
    require(all(isinstance(item, str) for item in ids), "P2 statistic ID is malformed")
    require(len(ids) == len(set(ids)), "P2 has duplicate statistic IDs")
    manifest = payload.get("manifest_validation", {})
    require(
        manifest.get("status") == "PASS"
        and manifest.get("static_fields_pass") is True
        and manifest.get("fragment_count") == len(statistics),
        "P2 Step-0 manifest validation failed",
    )
    summary = payload.get("summary", {})
    require(
        summary.get("targets_complete") == len(expected_targets)
        and summary.get("targets_total") == len(expected_targets)
        and summary.get("targets_remaining") == []
        and summary.get("statistics") == len(statistics)
        and summary.get("all_C4_endpoint_reproductions_pass") is True,
        "P2 completion summary is inconsistent",
    )

    closure_counts: Counter[str] = Counter()
    attribution_counts: Counter[str] = Counter()
    stats_by_target: Counter[str] = Counter(item.get("target") for item in statistics)
    for result in targets:
        target = result["target"]
        label = f"P2 {target}"
        require(result.get("status") == "COMPLETE", f"{label} is incomplete")
        nested = dict(result)
        nested_sha = nested.pop("canonical_sha256", None)
        require(
            nested_sha == c1.canonical_sha256(nested),
            f"{label} nested canonical seal mismatch",
        )
        require(
            result.get("statistics_count") == stats_by_target[target],
            f"{label} statistic count changed",
        )
        target_ids = sorted(
            item["id"] for item in statistics if item.get("target") == target
        )
        require(
            result.get("statistic_ids_sha256") == c1.canonical_sha256(target_ids),
            f"{label} statistic ID seal changed",
        )
        _verify_joint_unavailable(result.get("joint_hybrid_domain", {}), label)

        expected_patterns = d0["D0-2"]["targets"][target]["patterns"]
        patterns = result.get("patterns", [])
        require(
            [item.get("pattern") for item in patterns]
            == [item["name"] for item in expected_patterns],
            f"{label} pattern roster/order changed",
        )
        per_leg_statuses: dict[str, list[str]] = {"negative": [], "positive": []}
        for pattern, registered in zip(patterns, expected_patterns, strict=True):
            pattern_label = f"{label} {pattern['pattern']}"
            require(
                pattern.get("C4_endpoint_reproduction", {}).get("status") == "PASS",
                f"{pattern_label} did not reproduce C4 endpoints",
            )
            _verify_joint_unavailable(
                pattern.get("joint_hybrid_domain", {}),
                pattern_label,
            )
            expected_legs = [name for name in registered["classes"] if name != "zero"]
            legs = pattern.get("legs", [])
            require(
                [item.get("leg") for item in legs] == expected_legs,
                f"{pattern_label} leg roster/order changed",
            )
            for leg in legs:
                leg_label = f"{pattern_label} {leg['leg']}"
                _verify_p2_leg(leg, leg_label, closure_counts, attribution_counts)
                per_leg_statuses[leg["leg"]].append(leg["attribution_status"])

        aggregates = result.get("aggregates", [])
        require(
            {item.get("leg") for item in aggregates} == EXPECTED_P1_LEGS,
            f"{label} aggregate leg roster changed",
        )
        by_leg = {item["leg"]: item for item in aggregates}
        for leg in EXPECTED_P1_LEGS:
            statuses = per_leg_statuses[leg]
            if not statuses:
                expected_status = "NOT_APPLICABLE_CLASS_ABSENT"
                expected_validated: bool | None = None
            elif result.get("support", {}).get(leg, {}).get("pass") is not True:
                expected_status = "INSUFFICIENT_SUPPORT_NO_VERDICT"
                expected_validated = False
            elif all(status == "VALIDATED" for status in statuses):
                expected_status = "VALIDATED"
                expected_validated = True
            else:
                expected_status = "NOT_VALIDATED_PATTERN_CLOSURE_FAILURE"
                expected_validated = False
            require(
                by_leg[leg].get("status") == expected_status
                and by_leg[leg].get("attribution_validated") is expected_validated,
                f"{label} {leg} aggregate disposition is inconsistent",
            )

    disposition = {
        "computation_status": "COMPLETE",
        "validation_status": "NOT_VALIDATED",
        "reason": "A16-31 joint hybrid-domain predicates absent from frozen D0-7",
        "joint_hybrid_domain": {
            "status": P2_JOINT_UNAVAILABLE,
            "targets": len(expected_targets),
            "patterns": sum(
                len(value["patterns"]) for value in d0["D0-2"]["targets"].values()
            ),
            "predicates": 0,
        },
        "closure_dispositions": dict(sorted(closure_counts.items())),
        "attribution_dispositions": dict(sorted(attribution_counts.items())),
    }
    source["targets"] = list(expected_targets)
    source["disposition"] = "NOT_VALIDATED"
    return payload, source, disposition


def verify_p5_shards(
    paths: tuple[Path, ...],
    expected_targets: tuple[str, ...],
    adoption_source: dict[str, Any],
    c3_source: dict[str, Any],
    p1_source: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Verify six sealed P5 shards whose disjoint union is all nine targets."""
    require(len(paths) == EXPECTED_P5_SHARDS, "exactly six P5 shards are required")
    resolved = [path.resolve() for path in paths]
    require(len(resolved) == len(set(resolved)), "P5 shard paths are duplicated")
    target_owner: dict[str, str] = {}
    shard_scopes: list[list[str]] = []
    sources: list[dict[str, Any]] = []
    total_statistics = 0
    for path in paths:
        payload, source = c1.load_sealed_json(path, f"P5 shard {path}")
        require(
            payload.get("artifact_kind") == "qrf_drift_phase0_a18_p5",
            f"wrong P5 shard kind: {path}",
        )
        verify_artifact_authority(payload, f"P5 shard {path}")
        verify_a16_binding_authority(payload, f"P5 shard {path}")
        scope_targets = payload.get("scope", {}).get("targets")
        require(
            isinstance(scope_targets, list) and scope_targets,
            f"P5 shard {path} has no targets",
        )
        normalized = [target for target in expected_targets if target in scope_targets]
        require(scope_targets == normalized, f"P5 shard {path} target order changed")
        shard_scopes.append(scope_targets)
        require(
            payload.get("status")
            == (
                "COMPLETE"
                if scope_targets == list(expected_targets)
                else "COMPLETE_TARGET_SUBSET"
            ),
            f"P5 shard {path} completion status is inconsistent",
        )
        _verify_input_checks(payload.get("input_verification", {}), f"P5 shard {path}")
        authority = payload.get("authority", {})
        for key, expected_sha in (
            ("adoption", adoption_source["sha256"]),
            ("C3", c3_source["sha256"]),
            ("P1", p1_source["sha256"]),
        ):
            require(
                authority.get(key, {}).get("sha256") == expected_sha,
                f"P5 shard {path} does not bind the verified {key} input",
            )
        feasibility = payload.get("feasibility", {})
        require(
            feasibility.get("disposition") == "MECHANICALLY_FEASIBLE_EXACT_UNDER_A8",
            f"P5 shard {path} is not the exact A8 computation",
        )
        targets = payload.get("targets", {})
        require(
            set(targets) == set(scope_targets),
            f"P5 shard {path} target payload changed",
        )
        require(
            all(
                value.get("target") == target and value.get("status") == "COMPLETE"
                for target, value in targets.items()
            ),
            f"P5 shard {path} has an incomplete target",
        )
        statistics = payload.get("statistics", [])
        ids = [item.get("id") for item in statistics]
        require(
            len(statistics) == 62 * len(scope_targets) and len(ids) == len(set(ids)),
            f"P5 shard {path} statistic roster changed",
        )
        require(
            {item.get("target") for item in statistics} == set(scope_targets),
            f"P5 shard {path} statistics target roster changed",
        )
        manifest = payload.get("manifest_validation", {})
        require(
            manifest.get("status") == "PASS"
            and manifest.get("fragment_count") == len(statistics)
            and manifest.get("static_fields_and_allowed_statuses_pass") is True,
            f"P5 shard {path} manifest validation failed",
        )
        for target in scope_targets:
            require(
                target in expected_targets,
                f"P5 shard {path} has unknown target {target}",
            )
            require(
                target not in target_owner,
                f"P5 target appears in multiple shards: {target}",
            )
            target_owner[target] = str(path.resolve())
        source["targets"] = scope_targets
        sources.append(source_record(payload, source))
        total_statistics += len(statistics)

    verify_p5_target_partition(shard_scopes, expected_targets)
    order = {target: index for index, target in enumerate(expected_targets)}
    sources.sort(key=lambda item: min(order[target] for target in item["targets"]))
    return sources, {
        "status": "COMPLETE",
        "shards": len(sources),
        "targets": list(expected_targets),
        "target_to_shard": {
            target: target_owner[target] for target in expected_targets
        },
        "statistics": total_statistics,
        "priority_omissions": [],
    }


def verify_p5_target_partition(
    shard_scopes: list[list[str]],
    expected_targets: tuple[str, ...],
) -> None:
    """Require six nonempty, disjoint shards whose union is the D0 roster."""
    require(len(shard_scopes) == EXPECTED_P5_SHARDS, "P5 does not have six shards")
    flattened = [target for scope in shard_scopes for target in scope]
    require(all(scope for scope in shard_scopes), "P5 contains an empty shard")
    require(len(flattened) == len(set(flattened)), "P5 target scopes overlap")
    require(
        set(flattened) == set(expected_targets), "P5 shards do not cover all targets"
    )


def run(
    *,
    adoption_path: Path,
    c3_path: Path,
    p1_path: Path,
    p2_path: Path,
    p5_paths: tuple[Path, ...],
    baseline_path: Path,
) -> dict[str, Any]:
    """Verify every prerequisite and assemble the canonical barrier payload."""
    authority = verify_live_authority()
    d0 = json.loads(D0_JSON.read_text())
    expected_targets = tuple(d0["D0-2"]["targets"])
    require(len(expected_targets) == 9, "D0 target roster no longer has nine targets")

    adoption_payload, adoption_source = c1.verify_adoption(adoption_path)
    c3_payload, c3_source = c1.verify_c3(c3_path, adoption_payload)
    p1_payload, p1_source = verify_p1(p1_path, expected_targets)
    p2_payload, p2_source, p2_disposition = verify_p2(
        p2_path,
        d0,
        adoption_source,
        c3_source,
    )
    baseline_payload, baseline_source = verify_baseline(baseline_path)
    p5_sources, p5_disposition = verify_p5_shards(
        p5_paths,
        expected_targets,
        adoption_source,
        c3_source,
        p1_source,
    )

    return {
        "artifact_kind": "qrf_drift_phase0_readings_prerequisite",
        "schema_version": 1,
        "status": "READINGS_COMPLETE",
        "readings_complete": True,
        "completed_readings": dict(COMPLETED_READINGS),
        "next_phase": "C1",
        "authority": authority,
        "controls": {
            "status": "PASS",
            "adoption": artifact_record(adoption_payload, adoption_source),
            "fresh_C3": artifact_record(c3_payload, c3_source),
        },
        "reading_dispositions": {
            "P0": {"status": "COMPLETE", "targets": list(expected_targets)},
            "P1": {"status": "COMPLETE", "targets": list(expected_targets)},
            "P2": p2_disposition,
            "P5": p5_disposition,
            "P6": {
                "status": "COMPLETE_WITH_NO_SURFACE",
                "targets": list(expected_targets),
                "source_status": "COMPLETE_WITH_NO_SURFACE_ROWS",
            },
            "P7": {"status": "COMPLETE", "targets": list(expected_targets)},
            "baseline_cross_rung": {
                "status": "COMPLETE",
                "targets": list(EXPECTED_CROSS_RUNG_TARGETS),
                "leg": "positive",
            },
        },
        "inputs": {
            "P0_P1_P6_P7": source_record(p1_payload, p1_source),
            "P2": source_record(p2_payload, p2_source),
            "P5_shards": p5_sources,
            "baseline_cross_rung": source_record(baseline_payload, baseline_source),
        },
        "artifacts": {
            "P1": artifact_record(p1_payload, p1_source),
            "P2": artifact_record(p2_payload, p2_source),
            "baseline_crossrung": artifact_record(
                baseline_payload,
                baseline_source,
            ),
            "P5": [
                {
                    "path": item["path"],
                    "sha256": item["sha256"],
                    "canonical_sha256": item["self_excluding_sha256"],
                    "artifact_kind": item["artifact_kind"],
                    "status": item["status"],
                    "targets": item["targets"],
                }
                for item in p5_sources
            ],
        },
        "priority_omissions": [],
        "statistics": [],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adoption-json", type=Path, default=DEFAULT_ADOPTION)
    parser.add_argument("--c3-json", type=Path, default=DEFAULT_C3)
    parser.add_argument("--p1-json", type=Path, default=DEFAULT_P1)
    parser.add_argument("--p2-json", type=Path, default=DEFAULT_P2)
    parser.add_argument(
        "--p5-json",
        type=Path,
        nargs=EXPECTED_P5_SHARDS,
        required=True,
        metavar="PATH",
        help="exactly six disjoint sealed P5 shards covering all nine targets",
    )
    parser.add_argument("--baseline-json", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run(
        adoption_path=args.adoption_json,
        c3_path=args.c3_json,
        p1_path=args.p1_json,
        p2_path=args.p2_json,
        p5_paths=tuple(args.p5_json),
        baseline_path=args.baseline_json,
    )
    output_sha = c4.write_canonical_result(args.out, result)
    print(
        json.dumps(
            {
                "canonical_sha256": result["canonical_sha256"],
                "out": str(args.out.resolve()),
                "sha256": output_sha,
                "status": result["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
