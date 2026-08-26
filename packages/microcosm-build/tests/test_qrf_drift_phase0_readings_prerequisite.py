"""Focused tests for the Phase-0 readings-before-C1 barrier."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module():
    path = TOOLS / "qrf_drift_phase0_readings_prerequisite.py"
    spec = importlib.util.spec_from_file_location(
        "qrf_drift_phase0_readings_prerequisite",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOLS))
    return module


BARRIER = _load_module()


def _sealed_reading_barrier(completed: dict[str, str]) -> dict[str, object]:
    return {
        "artifact_kind": "qrf_drift_phase0_readings_prerequisite",
        "status": "READINGS_COMPLETE",
        "readings_complete": True,
        "completed_readings": completed,
        "next_phase": "C1",
        "authority": {
            "design": {
                "sha256": BARRIER.c1.enumeration.EXPECTED_AUTHORITY_DIGESTS[
                    str(BARRIER.c1.DESIGN)
                ]
            }
        },
        "statistics": [],
    }


def test_c1_accepts_only_the_exact_terminal_reading_dispositions(
    tmp_path: Path,
) -> None:
    path = tmp_path / "readings.json"
    payload = _sealed_reading_barrier(dict(BARRIER.COMPLETED_READINGS))
    BARRIER.c4.write_canonical_result(path, payload)

    _verified, source = BARRIER.c1.verify_readings(path)

    assert source["completed_readings"] == ["P0", "P1", "P2", "P5", "P6", "P7"]
    payload.pop("canonical_sha256")
    payload["completed_readings"] = {
        **BARRIER.COMPLETED_READINGS,
        "P2": "PARTIAL",
    }
    BARRIER.c4.write_canonical_result(path, payload)
    with pytest.raises(ValueError, match="lacks dispositions.*P2"):
        BARRIER.c1.verify_readings(path)


def test_declared_p2_closure_failure_is_complete_but_not_validated() -> None:
    leg = {
        "support": {"pass": True, "status": "SUPPORTED"},
        "closures": {
            "e_D": {"status": "FAIL", "pass": False},
            "e_R": {"status": "PASS", "pass": True},
            "e_T": {"status": "PASS", "pass": True},
        },
        "exact_shapley_closure": {"status": "PASS", "pass": True},
        "attribution_status": "NOT_VALIDATED_CLOSURE_FAILURE",
    }
    closures: Counter[str] = Counter()
    attributions: Counter[str] = Counter()

    BARRIER._verify_p2_leg(leg, "fixture", closures, attributions)

    assert closures == {"FAIL": 1, "PASS": 2, "exact_PASS": 1}
    assert attributions == {"NOT_VALIDATED_CLOSURE_FAILURE": 1}
    leg["attribution_status"] = "VALIDATED"
    with pytest.raises(ValueError, match="attribution status is inconsistent"):
        BARRIER._verify_p2_leg(leg, "fixture", Counter(), Counter())


def test_p2_joint_domain_unavailability_must_be_exact() -> None:
    disposition = {
        "status": "UNAVAILABLE_D0_NOT_ENUMERATED",
        "no_predicates_invented": True,
        "predicates": [],
        "pattern_invalidation_decision": "NOT_EVALUABLE",
        "threshold": 0.01,
        "violation_share": "NA",
        "source": {
            "checked_pointer": "/D0-7",
            "sha256": BARRIER._expected_digest(BARRIER.D0_JSON),
        },
    }

    BARRIER._verify_joint_unavailable(disposition, "fixture")

    disposition["predicates"] = ["invented"]
    with pytest.raises(ValueError, match="joint hybrid-domain disposition changed"):
        BARRIER._verify_joint_unavailable(disposition, "fixture")


def test_p2_descriptive_defaults_receipt_is_exact(tmp_path: Path) -> None:
    path = tmp_path / "p2_defaults.json"
    BARRIER.p2.p2_defaults.write_payload(path)
    _payload, receipt = BARRIER.p2.verify_reading_defaults(path)

    assert BARRIER.verify_p2_descriptive_defaults_receipt(receipt) == receipt

    mutations = [
        lambda value: value.update(sha256="0" * 64),
        lambda value: value.update(canonical_sha256="0" * 64),
        lambda value: value.update(status="COMPLETE"),
        lambda value: value["implementation"].update(sha256="0" * 64),
        lambda value: value["source_files"][0].update(sha256="0" * 64),
        lambda value: value["scope"].update(scientific_estimator_changed=True),
    ]
    for mutate in mutations:
        changed = copy.deepcopy(receipt)
        mutate(changed)
        with pytest.raises(ValueError, match="not current/exact"):
            BARRIER.verify_p2_descriptive_defaults_receipt(changed)

    with pytest.raises(ValueError, match="lacks.*descriptive-default receipt"):
        BARRIER.verify_p2_descriptive_defaults_receipt(None)


def test_p5_a16_binding_must_match_the_live_bound_file() -> None:
    payload = {
        "authority": {
            "A16_binding": {
                "path": str(BARRIER.A16_BINDING),
                "sha256": BARRIER._expected_digest(BARRIER.A16_BINDING),
            }
        }
    }

    BARRIER.verify_a16_binding_authority(payload, "fixture")

    payload["authority"]["A16_binding"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="A16 binding authority changed"):
        BARRIER.verify_a16_binding_authority(payload, "fixture")
    payload["authority"]["A16_binding"]["sha256"] = BARRIER._expected_digest(
        BARRIER.A16_BINDING
    )
    payload["authority"]["A16_binding"]["path"] = str(BARRIER.DESIGN)
    with pytest.raises(ValueError, match="A16 binding path changed"):
        BARRIER.verify_a16_binding_authority(payload, "fixture")


def test_baseline_scientific_seal_excludes_only_execution(
    tmp_path: Path,
) -> None:
    path = tmp_path / "baseline.json"
    payload = {
        "artifact_kind": "fixture",
        "scientific": {"value": 1},
        "execution": {"elapsed_seconds": 1.0},
    }
    payload["content_sha256"] = BARRIER.c1.compact_json_sha256(
        {"artifact_kind": "fixture", "scientific": {"value": 1}}
    )
    path.write_text(json.dumps(payload))

    BARRIER.load_baseline(path)
    payload["execution"]["elapsed_seconds"] = 2.0
    path.write_text(json.dumps(payload))
    BARRIER.load_baseline(path)
    payload["scientific"]["value"] = 2
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="scientific seal mismatch"):
        BARRIER.load_baseline(path)


def test_p5_partition_is_six_disjoint_shards_covering_all_targets() -> None:
    targets = tuple(f"t{index}" for index in range(9))
    scopes = [["t0", "t1", "t2", "t3"], ["t4"], ["t5"], ["t6"], ["t7"], ["t8"]]

    BARRIER.verify_p5_target_partition(scopes, targets)

    overlapping = [*scopes[:-1], ["t7"]]
    with pytest.raises(ValueError, match="target scopes overlap"):
        BARRIER.verify_p5_target_partition(overlapping, targets)
    missing = [*scopes[:-1], ["unknown"]]
    with pytest.raises(ValueError, match="do not cover all targets"):
        BARRIER.verify_p5_target_partition(missing, targets)


def test_artifact_record_has_direct_reconciliation_fields() -> None:
    payload = {"artifact_kind": "fixture", "status": "COMPLETE"}
    source = {
        "path": "/tmp/fixture.json",
        "sha256": "a" * 64,
        "self_excluding_sha256": "b" * 64,
        "targets": ["target"],
    }

    record = BARRIER.artifact_record(payload, source)

    assert record == {
        "path": "/tmp/fixture.json",
        "sha256": "a" * 64,
        "canonical_sha256": "b" * 64,
        "artifact_kind": "fixture",
        "status": "COMPLETE",
        "targets": ["target"],
    }
