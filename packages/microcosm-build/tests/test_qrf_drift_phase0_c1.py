"""Focused tests for the A18 C1 gate-scoped cross-fitting executor."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module():
    path = TOOLS / "qrf_drift_phase0_c1.py"
    spec = importlib.util.spec_from_file_location("qrf_drift_phase0_c1", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOLS))
    return module


C1 = _load_module()


def test_global_partition_is_deterministic_and_order_independent() -> None:
    households = np.asarray([90, 5, 30, 5, 12, 44, 71, 30], dtype=np.int64)

    first = C1.stable_household_partition(households, repeat=2)
    second = C1.stable_household_partition(households[::-1], repeat=2)

    np.testing.assert_array_equal(first["stable_ids"], [5, 12, 30, 44, 71, 90])
    np.testing.assert_array_equal(first["stable_ids"], second["stable_ids"])
    np.testing.assert_array_equal(
        first["folds_by_stable_id"], second["folds_by_stable_id"]
    )
    resolved = C1.folds_for_rows(households, first)
    assert resolved[1] == resolved[3]
    assert resolved[2] == resolved[7]
    assert first["label"] == "qrf-drift-v2.3|C1|repeat-2"


def test_gate_seed_is_one_independent_raw_value_low_32_bits() -> None:
    target = "fixture_target"
    pattern = "pattern_03_fixture"
    repeat = 3
    fold = 4
    label = f"qrf-drift-v2.3|C1|{target}|{pattern}|{repeat}|{fold}"
    seed = int.from_bytes(hashlib.sha256(label.encode()).digest()[:8], "big")
    expected = int(np.random.PCG64(seed).random_raw()) & 0xFFFF_FFFF

    actual = C1.gate_random_state(target, pattern, repeat, fold)

    assert actual == expected
    # Exercising the separate partition stream cannot change a gate seed.
    C1.stable_household_partition(np.arange(20, dtype=np.int64), repeat=repeat)
    assert C1.gate_random_state(target, pattern, repeat, fold) == expected


def test_pooled_estimand_concatenates_heldout_rows_before_hajek_mean() -> None:
    folds = []
    for fold, weight in enumerate((100.0, 1.0, 1.0, 1.0, 1.0)):
        folds.append(
            {
                "status": "SUPPORTED",
                "fold": fold,
                "weights": np.asarray([weight]),
                "predicted": np.asarray([1.0 if fold == 0 else 0.0]),
                "observed": np.asarray([0.0]),
            }
        )

    result = C1.pooled_heldout_estimand(folds)

    assert result["status"] == "SUPPORTED"
    assert result["value"] == 100.0 / 104.0
    assert result["fit_weight_sum"] == 104.0
    assert result["value"] != np.mean([1.0, 0.0, 0.0, 0.0, 0.0])


def test_unsupported_pattern_propagates_without_alpha_renormalization() -> None:
    patterns = [
        {
            "pattern": "p0",
            "status": "SUPPORTED",
            "alpha": 0.8,
            "value": 0.25,
        },
        {
            "pattern": "p1",
            "status": "UNSUPPORTED",
            "alpha": 0.2,
            "value": "NA",
        },
    ]

    result = C1.combine_pattern_repeat(patterns)

    assert result["status"] == "UNSUPPORTED"
    assert result["unavailable_patterns"] == ["p1"]
    assert result["alpha_renormalized"] is False


def test_repeat_se_is_sample_sd_divided_by_two() -> None:
    values = [1.0, 2.0, 4.0, 8.0]
    repeats = [
        {"status": "SUPPORTED", "repeat": repeat, "value": value}
        for repeat, value in enumerate(values)
    ]

    result = C1.repeat_mean_and_se(repeats)

    assert result["status"] == "SUPPORTED"
    assert result["value"] == np.mean(values)
    assert result["se"] == np.std(values, ddof=1) / 2.0
    assert result["repeat_variance"] == np.var(values, ddof=1)
    assert result["se_variance"] == np.var(values, ddof=1) / 4.0
    assert result["se_formula"] == "SD(ddof=1)/2"


def test_sealed_d0_roster_has_800_fold_cells_and_10_summaries() -> None:
    d0 = json.loads((ROOT / "experiments/qrf_drift_validation_d0.json").read_text())
    targets = list(d0["D0-2"]["targets"])

    fold_ids = C1.expected_fold_ids(d0, targets)
    target_ids = C1.expected_target_ids(d0, targets)

    assert len(fold_ids) == len(set(fold_ids)) == 800
    assert len(target_ids) == len(set(target_ids)) == 10


def test_readings_barrier_is_explicit_and_fail_closed(tmp_path: Path) -> None:
    barrier = {
        "artifact_kind": "qrf_drift_phase0_readings_prerequisite",
        "status": "READINGS_COMPLETE",
        "readings_complete": True,
        "completed_readings": ["P0", "P1", "P2", "P5", "P6", "P7"],
        "next_phase": "C1",
        "authority": {
            "design": {
                "sha256": C1.enumeration.EXPECTED_AUTHORITY_DIGESTS[str(C1.DESIGN)]
            }
        },
        "statistics": [],
    }
    path = tmp_path / "readings.json"
    C1.c4.write_canonical_result(path, barrier)

    _, source = C1.verify_readings(path)

    assert source["completed_readings"] == ["P0", "P1", "P2", "P5", "P6", "P7"]
    barrier.pop("canonical_sha256")
    barrier["completed_readings"].remove("P2")
    C1.c4.write_canonical_result(path, barrier)
    with pytest.raises(ValueError, match="lacks dispositions"):
        C1.verify_readings(path)
