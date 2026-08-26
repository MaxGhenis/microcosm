"""Synthetic regressions for the isolated baseline cross-rung executor."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module():
    path = TOOLS / "qrf_drift_phase0_baseline_crossrung.py"
    spec = importlib.util.spec_from_file_location(
        "qrf_drift_phase0_baseline_crossrung",
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


BASELINE = _load_module()


def test_gate_choices_use_production_cumulative_rule() -> None:
    probabilities = np.asarray(
        [
            [0.1, 0.2, 0.7],
            [0.4, 0.6, 0.0],
            [0.0, 0.5, 0.5],
        ]
    )
    classes = np.asarray([-1, 0, 1])
    uniforms = np.asarray([0.31, 0.40, 0.99])

    choices = BASELINE._gate_choices(probabilities, classes, uniforms)

    assert choices.tolist() == [1, -1, 1]


def test_baseline_d0_view_changes_only_loader_path_authority() -> None:
    d0 = {
        "D0-0": {
            "artifacts": {
                "candidate-25": {"name": "candidate"},
                "baseline1pct": {
                    "name": "baseline",
                    "bank_target_checkpoints": [
                        {"target": "a", "path": "/baseline/a.h5"},
                        {"target": "b", "path": "/baseline/b.h5"},
                    ],
                },
            }
        },
        "D0-2": {
            "targets": {
                "a": {"target_bank_file": "/candidate/a.h5"},
                "b": {"target_bank_file": "/candidate/b.h5"},
            }
        },
    }

    result = BASELINE._baseline_d0_view(d0)

    assert d0["D0-0"]["artifacts"]["candidate-25"]["name"] == "candidate"
    assert result["D0-0"]["artifacts"]["candidate-25"]["name"] == "baseline"
    assert result["D0-2"]["targets"]["a"]["target_bank_file"] == "/baseline/a.h5"
    assert result["D0-2"]["targets"]["b"]["target_bank_file"] == "/baseline/b.h5"


def test_dominant_label_is_absolute_and_stable_on_ties() -> None:
    rows = {name: {"value": 0.0, "se": 0.0} for name in BASELINE.TOP_LEVEL_ROWS}
    rows["B1"]["value"] = -2.0
    rows["T2"]["value"] = 2.0

    result = BASELINE._dominant_label(rows)

    assert result == {"row": "B1", "share": 0.5, "sum_abs": 4.0}


def test_index_identity_distinguishes_index_class_and_order() -> None:
    first = BASELINE._index_identity(np.asarray([4, 1, 9]))
    second = BASELINE._index_identity(np.asarray([4, 9, 1]))

    assert first["class_name"] == "Index"
    assert first["dtype"] == "int64"
    assert first["sha256"] != second["sha256"]


def test_baseline_support_uses_frozen_50_unique_floor() -> None:
    d0 = {
        "D0-1": {
            "rungs": {
                "baseline1pct": {
                    "target": {
                        "asec": {
                            "legs": {
                                "positive": {
                                    "unique_clone_deduplicated_source_rows_clone0": 50
                                }
                            }
                        },
                        "acs": {
                            "legs": {
                                "positive": {
                                    "unique_clone_deduplicated_source_rows_clone0": 49
                                }
                            }
                        },
                    }
                }
            }
        }
    }

    result = BASELINE._baseline_support(d0, "target")

    assert result["status"] == "INSUFFICIENT_SUPPORT_NO_VERDICT"
    assert result["floor"] == 50
    assert result["asec_unique_sources"] == 50
    assert result["acs_unique_sources"] == 49
