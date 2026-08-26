"""Focused synthetic regressions for the deterministic Phase-0 P1 executor."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module():
    path = TOOLS / "qrf_drift_phase0_p1.py"
    spec = importlib.util.spec_from_file_location("qrf_drift_phase0_p1", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOLS))
    return module


P1 = _load_module()


def test_exact_incidence_and_qrf_boundary_bridge_are_distinct() -> None:
    values = np.asarray([-1e-7, 0.0, 1e-7, 1e-6, 2e-6, -2e-6])
    weights = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    exact = P1._weighted_summary(values, weights, sign=1)
    bridge = P1._boundary_bridge(
        values,
        weights,
        stage="J1_donor_projection",
    )

    assert exact["carrier_rows"] == 3
    assert exact["value"] == pytest.approx(12.0 / 21.0)
    assert bridge["boundary_rows"] == 3
    assert bridge["boundary_weight_mass"] == 8.0
    assert bridge["legs"]["positive"]["value"] == pytest.approx(7.0 / 21.0)
    assert bridge["legs"]["negative"]["value"] == pytest.approx(1.0 / 21.0)
    assert bridge["legs"]["positive"]["exact_incidence"] == exact["value"]


def test_phi_below_one_uses_conditional_sq_denominator_once() -> None:
    scope_weight = 10.0
    first_alpha, first_e2 = P1._pattern_weight_terms(
        np.asarray([1.0]), np.asarray([0.2]), 3.0
    )
    second_alpha, second_e2 = P1._pattern_weight_terms(
        np.asarray([2.0]), np.asarray([0.4]), 3.0
    )
    phi = 3.0 / scope_weight

    assert first_alpha == pytest.approx(1.0 / 3.0)
    assert second_alpha == pytest.approx(2.0 / 3.0)
    assert first_alpha + second_alpha == pytest.approx(1.0)
    assert phi * phi * (first_e2 + second_e2) == pytest.approx(1.12 / 100.0)

    census = P1._path_census(
        np.asarray([True, False, True, True]),
        np.asarray([True, True, True, True]),
        np.asarray([True, True, False, True]),
        np.asarray([True, True, True, False]),
    )
    assert census["passed_rows"] == 1
    assert census["first_failure_rows"] == {
        "authorized": 1,
        "null_before": 0,
        "drawn": 1,
        "finite_decode": 1,
    }


def test_b2_cumulative_telescope_closes_with_nonzero_subrows() -> None:
    values = np.asarray([1.0, 0.0, -1.0, 1.0])
    native = np.ones(4)
    patterns = [
        {
            "pattern": "p0",
            "alpha": 0.25,
            "values": values,
            "native_weights": native,
            "fit_weights": np.asarray([1.0, 3.0, 1.0, 1.0]),
            "role_mask": np.asarray([True, True, True, True]),
            "family_mask": np.asarray([True, True, True, False]),
            "predictor_mask": np.asarray([True, True, False, False]),
            "seed": 11,
        },
        {
            "pattern": "p1",
            "alpha": 0.75,
            "values": values,
            "native_weights": native,
            "fit_weights": np.asarray([2.0, 1.0, 1.0, 1.0]),
            "role_mask": np.asarray([True, True, True, True]),
            "family_mask": np.asarray([True, True, False, True]),
            "predictor_mask": np.asarray([True, False, False, True]),
            "seed": 12,
        },
    ]
    j1 = {
        leg: P1._weighted_summary(values, native, sign=sign)
        for leg, sign in P1.LEGS.items()
    }
    j2 = {}
    for leg, sign in P1.LEGS.items():
        parts = []
        for pattern in patterns:
            mask = pattern["predictor_mask"]
            parts.append(
                (
                    pattern["alpha"],
                    P1._weighted_summary(
                        values[mask], pattern["fit_weights"][mask], sign=sign
                    ),
                )
            )
        j2[leg] = P1._combined_level(parts)

    result = P1._b2_telescope(j1, j2, patterns)

    positive = result["legs"]["positive"]
    assert positive["passes"] is True
    assert positive["sum"] == pytest.approx(
        j1["positive"]["value"] - j2["positive"]["value"]
    )
    assert any(abs(row["value"]) > 0.0 for row in positive["rows"].values())
    assert all("se" in row and "variance" in row for row in positive["rows"].values())
    assert result["patterns"][0]["stages"]["family_complete_case"]["row_count"] == 3
    assert (
        result["patterns"][0]["stages"]["pattern_predictor_complete_case"]["row_count"]
        == 2
    )


def test_p6_no_surface_remains_unavailable_and_is_not_guessed() -> None:
    operator_table = [
        {
            "target": "synthetic",
            "stage": "fit_sample_5000",
            "surface_status": "NO_SURFACE",
            "dataset": "in-memory",
            "source_code": {"path": "synthetic.py", "sha256": "00"},
            "transformation": "sample",
        }
    ]
    projection = {
        "J0": {
            "values": np.asarray([1.0, 0.0]),
            "weights": np.asarray([1.0, 1.0]),
            "stable_ids": np.asarray([1, 2]),
            "source_ids": np.asarray([10, 20]),
        },
        "J1": {
            "values": np.asarray([1e-7, 0.0]),
            "weights": np.asarray([1.0, 1.0]),
            "stable_ids": np.asarray([1, 2]),
            "source_ids": np.asarray([10, 20]),
        },
        "clone2": {
            "values": np.asarray([], dtype=np.float64),
            "weights": np.asarray([], dtype=np.float64),
            "stable_ids": np.asarray([], dtype=np.int64),
            "source_ids": np.asarray([], dtype=np.int64),
        },
    }
    bank = {
        "path": Path("synthetic.h5"),
        "metadata": {
            "pattern_steps": [
                {
                    "pattern": "p0",
                    "state_after": {"model_config": {"seed": 123}},
                }
            ]
        },
    }

    result = P1._producer_ledger(
        operator_table,
        "synthetic",
        projection,
        bank,
        {},
        np.asarray([1e-7, 0.0]),
        np.asarray([1.0, 1.0]),
        np.asarray([1, 2]),
        np.asarray([1e-7, 0.0]),
        np.asarray([1e-7, 0.0]),
    )

    stage = result["stages"][0]
    assert stage["status"] == "NO_SURFACE"
    assert stage["value"] == "NA"
    assert stage["seed"]["status"] == "UNAVAILABLE"
    assert "unweighted_sign_counts" not in stage
    assert result["boundary_bridge"]["legs"]["positive"]["value"] == 0.5


def test_registered_production_codec_is_replayed_not_asserted() -> None:
    operator_table = [
        {
            "target": "weeks_unemployed",
            "stage": "recipient_codec",
            "surface_status": "DERIVED_FROM_PERSISTED_RAW",
            "source_code": {"path": "weeks_unemployed.py", "sha256": "00"},
            "source_anchor": "codec",
            "transformation": "production _prediction_values codec",
        }
    ]
    raw = np.asarray([0.0, 2.1, 5.0, np.nan])

    decoded, evidence = P1._production_codec(
        raw,
        np.asarray([0.0, 2.0, 5.0]),
        "weeks_unemployed",
        {"entity": "person"},
        operator_table,
    )

    assert decoded[:3].tolist() == [0.0, 2.1, 5.0]
    assert np.isnan(decoded[3])
    assert evidence["status"] == "AVAILABLE_REPLAYED"
    assert evidence["kind"] == "continuous"
    assert evidence["bitwise_equal"] is True


def test_p7_gq_adjustments_have_independent_kish_delta_se() -> None:
    values = np.asarray([1.0, 0.0, 1.0, 0.0, 0.0, 0.0])
    weights = np.ones(6)
    role = {"recipient_gq": np.asarray([1, 1, 2, 2, 3, 3])}
    sq = np.ones(6, dtype=bool)
    j0_values = np.asarray([1.0, 1.0, 0.0, 0.0])
    j0_weights = np.ones(4)
    j0 = {
        leg: P1._weighted_summary(j0_values, j0_weights, sign=sign)
        for leg, sign in P1.LEGS.items()
    }

    result = P1._gq_reading(role, sq, values, weights, j0)

    type2 = result["legs"]["positive"]["adjustment_TYPEHUGQ_2"]
    type3 = result["legs"]["positive"]["adjustment_TYPEHUGQ_3"]
    assert type2["status"] == "AVAILABLE_F4"
    assert type2["value"] == 0.0
    assert type2["se"] == pytest.approx(1.0 / 6.0)
    assert type3["status"] == "AVAILABLE_F4"
    assert type3["value"] == pytest.approx(1.0 / 6.0)
    assert type3["variance"] == pytest.approx(1.0 / 72.0)
    assert result["legs"]["positive"]["adjustment_unprojectable"]["status"] == (
        "INAPPLICABLE_EMPTY_STRATUM"
    )
    assert math.isfinite(type3["se"])
