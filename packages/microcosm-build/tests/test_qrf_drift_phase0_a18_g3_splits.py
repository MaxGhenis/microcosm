"""Focused tests for the deterministic A18 G3 split seal."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module():
    path = TOOLS / "qrf_drift_phase0_a18_g3_splits.py"
    spec = importlib.util.spec_from_file_location(
        "qrf_drift_phase0_a18_g3_splits",
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


A18 = _load_module()
NODE_DTYPE = np.dtype(
    [("feature_idx", "<i8"), ("gain", "<f8"), ("is_leaf", "u1")]
)


def _predictor(*rows: tuple[int, float, int]) -> SimpleNamespace:
    return SimpleNamespace(nodes=np.asarray(list(rows), dtype=NODE_DTYPE))


def test_split_statistics_sum_nonleaf_gains_across_all_trees() -> None:
    gate = SimpleNamespace(
        _predictors=[
            [_predictor((2, 0.1, 0), (0, -1.0, 1))],
            [
                _predictor((1, 1.5, 0), (0, -1.0, 1)),
                _predictor((2, 0.2, 0), (2, 0.3, 0), (0, -1.0, 1)),
            ],
        ]
    )

    statistics = A18.split_feature_statistics(gate)

    assert list(statistics) == [1, 2]
    assert statistics[1]["split_count"] == 1
    assert statistics[1]["total_split_gain"] == 1.5
    assert statistics[2]["split_count"] == 3
    assert statistics[2]["total_split_gain"] == 0.6
    assert statistics[2]["total_split_gain_hex"] == (0.6).hex()


def test_sealed_table_filters_zero_splits_and_preserves_d0_order() -> None:
    gate = SimpleNamespace(
        _predictors=[[_predictor((2, 4.0, 0), (0, -1.0, 1))]]
    )
    rows = A18.enumerate_g3_columns(
        gate,
        target="target",
        pattern="pattern_00",
        columns=("G1", "prior_a", "prior_b"),
        g3_columns=("prior_a", "prior_b"),
        target_order=3,
        pattern_order=0,
        first_triple_order=7,
        source={"sha256": "a" * 64},
    )

    seal = A18.seal_split_table(rows)

    assert [row["stable_order"]["triple"] for row in rows] == [7, 8]
    assert [row["G3_column"] for row in seal["rows"]] == ["prior_b"]
    assert seal["rows"][0]["table_order"] == 0
    assert seal["rows"][0]["split_count"] == 1
    assert seal["sha256"] == A18.seal_split_table(rows)["sha256"]


def test_largest_gain_tie_breaks_by_stable_table_order() -> None:
    rows = [
        {
            "table_order": 0,
            "target": "first",
            "pattern": "p0",
            "G3_column": "prior",
            "split_count": 2,
            "total_split_gain": 9.0,
            "total_split_gain_hex": 9.0.hex(),
        },
        {
            "table_order": 1,
            "target": "second",
            "pattern": "p0",
            "G3_column": "prior",
            "split_count": 3,
            "total_split_gain": 9.0,
            "total_split_gain_hex": 9.0.hex(),
        },
    ]

    selected = A18.select_largest_gain(rows)

    assert selected is not None
    assert selected["table_order"] == 0
    assert selected["target"] == "first"
    assert A18.select_largest_gain([]) is None
