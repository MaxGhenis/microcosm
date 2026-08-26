"""Focused estimator tests for the A18 Phase-0 P2 executor."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module():
    path = TOOLS / "qrf_drift_phase0_p2.py"
    spec = importlib.util.spec_from_file_location("qrf_drift_phase0_p2", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOLS))
    return module


P2 = _load_module()


def test_exact_stratum_shares_replace_sample_allocation_shares() -> None:
    values = np.asarray([[1.0], [3.0], [8.0], [10.0], [12.0]])
    slices = [
        {"start": 0, "stop": 2, "exact_weight_share": 0.8},
        {"start": 2, "stop": 5, "exact_weight_share": 0.2},
    ]

    result = P2.combine_stratum_means(values, slices)

    np.testing.assert_allclose(result, [0.8 * 2.0 + 0.2 * 10.0])
    assert result[0] != values.mean()


def test_null_reference_and_exact_shapley_closure() -> None:
    real = np.asarray(
        [
            1.0,
            3.0,
            4.0,
            6.0,
            6.0,
            8.0,
            9.0,
            11.0,
        ]
    )
    null = np.asarray(
        [
            0.5,
            1.0,
            1.5,
            2.0,
            2.0,
            2.5,
            3.0,
            3.5,
        ]
    )

    raw_phi = P2.shapley_from_coalitions(real)
    null_phi = P2.shapley_from_coalitions(null)
    referenced = raw_phi - null_phi
    delta_nr = (real[7] - real[0]) - (null[7] - null[0])

    np.testing.assert_allclose(raw_phi, [2.0, 3.0, 5.0])
    np.testing.assert_allclose(null_phi, [0.5, 1.0, 1.5])
    np.testing.assert_allclose(referenced, [1.5, 2.0, 3.5])
    np.testing.assert_allclose(referenced.sum(), delta_nr, atol=2e-15)
    exact = P2.exact_shapley_closure(
        np.asarray([referenced.sum() - delta_nr]),
        np.asarray([delta_nr]),
    )
    assert exact["pass"] is True


def test_escalation_is_triggered_once_by_any_registered_vector() -> None:
    # mean=3, SD=sqrt(2), MCSE=1, so the registered ratio is exactly 3.
    decision = P2.reading_escalation_decision(
        {
            "G1": np.asarray([2.0, 4.0]),
            "e_D": np.asarray([0.0, 0.0]),
        }
    )

    assert decision["trigger"] is True
    assert decision["triggered_statistics"] == ["G1"]
    assert decision["statistics"]["G1"]["abs_value_over_mcse"] == 3.0
    assert decision["statistics"]["e_D"]["escalation_trigger"] is False


def test_all_coalitions_and_one_at_a_time_priors_share_donor_rows() -> None:
    base = np.zeros((2, 4), dtype=np.float64)
    donor = np.asarray([[2.0, 3.0, 5.0, 7.0], [4.0, 5.0, 7.0, 11.0]])
    groups = {
        "G1": np.asarray([0]),
        "G2": np.asarray([1]),
        "G3": np.asarray([2, 3]),
    }

    def predict(values: np.ndarray) -> np.ndarray:
        return values.sum(axis=1, keepdims=True)

    def mean(values: np.ndarray) -> np.ndarray:
        return values.mean(axis=0)

    coalitions = P2.evaluate_coalitions(
        base,
        donor,
        groups,
        predict,
        mean,
    )
    priors = P2.evaluate_per_prior(
        base,
        donor,
        ("g1", "g2", "prior_a", "prior_b"),
        ("prior_a", "prior_b"),
        predict,
        mean,
        np.asarray([0.0]),
    )

    np.testing.assert_allclose(coalitions[0], [0, 3, 4, 7, 15, 18, 19, 22])
    np.testing.assert_allclose(priors["prior_a"], [6.0])
    np.testing.assert_allclose(priors["prior_b"], [9.0])
    np.testing.assert_allclose(
        P2.shapley_from_coalitions(coalitions)[0],
        [3.0, 4.0, 15.0],
    )


def test_categorical_marginal_has_kish_level_detail_and_support_evidence() -> None:
    donor = np.asarray([0.0, 0.0, 1.0, 1.0])
    donor_weights = np.asarray([1.0, 1.0, 1.0, 3.0])
    recipient = np.asarray([0.0, 1.0, 2.0])
    recipient_weights = np.asarray([1.0, 2.0, 1.0])

    audit = P2.marginal_audit(
        donor,
        donor_weights,
        recipient,
        recipient_weights,
        feature="fixture_category",
        categories=[0.0, 1.0, 2.0],
    )

    assert audit["feature_kind"] == "categorical"
    assert audit["category_order"] == [0.0, 1.0, 2.0]
    assert audit["donor"]["kish_effective_n"] == 3.0
    np.testing.assert_allclose(audit["categories"][1]["donor"]["mean"], 2 / 3)
    np.testing.assert_allclose(audit["categories"][1]["recipient"]["mean"], 0.5)
    np.testing.assert_allclose(
        audit["one_feature_recipient_outside_donor_support_share"], 0.25
    )
    assert audit["donor_copied_substitution_outside_donor_support_share"] == 0.0
    assert audit["categories"][2]["difference_se"] > 0.0


def test_pattern_closure_failure_invalidates_target_aggregate() -> None:
    pattern_payloads = [
        {
            "pattern": "p0",
            "legs": [{"leg": "positive", "attribution_status": "VALIDATED"}],
        },
        {
            "pattern": "p1",
            "legs": [
                {
                    "leg": "positive",
                    "attribution_status": "NOT_VALIDATED_CLOSURE_FAILURE",
                }
            ],
        },
    ]
    pattern_data = [
        {"context": {"pattern": pattern, "gate_classes": np.asarray([1])}}
        for pattern in ("p0", "p1")
    ]
    pattern_arrays = {
        pattern: {
            "null_referenced_shapley": np.full((4, 1, 3), value, dtype=np.float64)
        }
        for pattern, value in (("p0", 1.0), ("p1", 2.0))
    }
    support = {
        "positive": {"pass": True, "status": "SUPPORTED"},
        "negative": {"pass": False, "status": "INSUFFICIENT_SUPPORT_NO_VERDICT"},
    }

    aggregates, statistics = P2._aggregate_groups(
        "fixture",
        pattern_data,
        pattern_payloads,
        pattern_arrays,
        {"p0": 0.5, "p1": 0.5},
        support,
    )

    positive = next(item for item in aggregates if item["leg"] == "positive")
    assert positive["status"] == "NOT_VALIDATED_PATTERN_CLOSURE_FAILURE"
    assert positive["attribution_validated"] is False
    assert positive["invalid_patterns"] == ["p1"]
    positive_stats = [item for item in statistics if item["leg"] == "positive"]
    assert len(positive_stats) == 3
    assert all(item["status"] == positive["status"] for item in positive_stats)
    assert all(
        item["family"] is None and item["gated"] is False for item in positive_stats
    )
