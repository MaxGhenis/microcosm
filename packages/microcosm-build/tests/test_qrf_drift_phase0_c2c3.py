"""Focused regression tests for the A16 C2/C3 control estimator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_control_module():
    path = TOOLS / "qrf_drift_phase0_c2c3.py"
    spec = importlib.util.spec_from_file_location("qrf_drift_phase0_c2c3", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOLS))
    return module


C2C3 = _load_control_module()


def test_stratum_aggregation_uses_exact_shares_not_allocations() -> None:
    plan = [
        {"gq": "H", "allocation": 2, "weight_sum": 90.0},
        {"gq": "2", "allocation": 8, "weight_sum": 10.0},
    ]
    values = np.asarray([1.0, 3.0, *([100.0] * 8)])

    slices = C2C3.stratum_aggregation_slices(plan)
    estimate = C2C3.exact_stratum_weighted_mean(values, slices)

    assert [item["exact_weight_share"] for item in slices] == [0.9, 0.1]
    assert estimate == pytest.approx(0.9 * 2.0 + 0.1 * 100.0)
    assert estimate != pytest.approx(float(values.mean()))


def test_rostered_statistics_use_same_i_j_paired_delta() -> None:
    oracle = np.asarray([0.1, 0.2, 0.3])
    arrays = {
        "paired_delta": np.asarray(
            [
                [0.09, 0.19, 0.29],
                [0.11, 0.21, 0.31],
            ]
        ),
        "recovered": np.full((2, 3), 99.0),
    }

    statistics = C2C3.control_statistics("C2", arrays, oracle)

    assert [item["estimate"] for item in statistics] == pytest.approx(oracle)
    assert all(item["estimator_array"] == "paired_delta" for item in statistics)
    assert all(item["pairing"] == "same_i_j" for item in statistics)
