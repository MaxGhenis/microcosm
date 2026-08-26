"""Focused tests for the A18 branch-2 C3 executor."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module():
    path = TOOLS / "qrf_drift_phase0_a18_c3.py"
    spec = importlib.util.spec_from_file_location("qrf_drift_phase0_a18_c3", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOLS))
    return module


C3 = _load_module()


def _context() -> tuple[dict[str, object], np.ndarray]:
    rng = np.random.default_rng(291)
    x = rng.normal(size=(48, 3))
    x[:, 2] = (x[:, 2] > 0.0).astype(np.float64)
    labels = (2.5 * x[:, 2] + 0.4 * x[:, 0] > 1.0).astype(np.int8)
    weights = np.linspace(1.0, 3.0, len(x), dtype=np.float64)
    gate = HistGradientBoostingClassifier(
        random_state=17,
        max_iter=8,
        max_leaf_nodes=7,
        min_samples_leaf=2,
        learning_rate=0.2,
    ).fit(x, labels, sample_weight=weights)
    context: dict[str, object] = {
        "gate": gate,
        "gate_classes": np.asarray(gate.classes_, dtype=np.int8),
        "columns": ("demographic", "income", "prior"),
        "groups": {"G1": ("demographic",), "G2": ("income",), "G3": ("prior",)},
        "group_indexes": {
            "G1": np.asarray([0], dtype=np.int64),
            "G2": np.asarray([1], dtype=np.int64),
            "G3": np.asarray([2], dtype=np.int64),
        },
        "donor_x": x,
        "donor_weights": weights,
        "donor_probabilities": gate.predict_proba(x),
    }
    transformed = x.copy()
    transformed[transformed[:, 2] > 0.0, 2] = 0.0
    return context, transformed


def _brute_coalition_delta(
    context: dict[str, object],
    transformed: np.ndarray,
) -> np.ndarray:
    x = np.asarray(context["donor_x"])
    weights = np.asarray(context["donor_weights"])
    gate = context["gate"]
    original_rows: list[np.ndarray] = []
    transformed_rows: list[np.ndarray] = []
    pair_weights: list[float] = []
    masks: list[int] = []
    for mask in range(8):
        for i in range(len(x)):
            for j in range(len(x)):
                original = x[i].copy()
                changed = transformed[i].copy()
                for group in C3.GROUPS:
                    if mask & C3.c4.GROUP_BITS[group]:
                        indexes = context["group_indexes"][group]
                        original[indexes] = x[j, indexes]
                        changed[indexes] = x[j, indexes]
                original_rows.append(original)
                transformed_rows.append(changed)
                pair_weights.append(float(weights[i] * weights[j]))
                masks.append(mask)
    original_probability = gate.predict_proba(np.asarray(original_rows))[:, 1]
    transformed_probability = gate.predict_proba(np.asarray(transformed_rows))[:, 1]
    differences = transformed_probability - original_probability
    result = np.zeros(8, dtype=np.float64)
    denominator = float(weights.sum() ** 2)
    for mask in range(8):
        selected = np.asarray(masks) == mask
        result[mask] = float(
            np.dot(np.asarray(pair_weights)[selected], differences[selected])
            / denominator
        )
    return result


def test_exact_oracle_matches_brute_weighted_cartesian_shapley() -> None:
    context, transformed = _context()

    exact = C3.compute_exact_oracle(context, transformed, chunk_pairs=137)
    brute = _brute_coalition_delta(context, transformed)

    np.testing.assert_allclose(
        exact["coalition_mask_order_0_to_7"],
        brute,
        rtol=0.0,
        atol=2e-15,
    )
    np.testing.assert_allclose(
        exact["oracle_group_order_G1_G2_G3"],
        C3.a17.shapley_from_coalitions(brute),
        rtol=0.0,
        atol=2e-15,
    )
    assert exact["coalition_mask_order_0_to_7"][4:] == [0.0, 0.0, 0.0, 0.0]


def test_full_replicate_route_evaluates_nonduplicated_g3_coalitions() -> None:
    context, transformed = _context()
    row_index = np.asarray([0, 1, 2, 3], dtype=np.int64)
    donor_index = np.asarray([7, 8, 9, 10], dtype=np.int64)
    r0_index = np.asarray([14, 15, 16, 17], dtype=np.int64)
    slices = [
        {"start": 0, "stop": 2, "exact_weight_share": 0.75},
        {"start": 2, "stop": 4, "exact_weight_share": 0.25},
    ]

    values = C3.evaluate_replicate(
        context,
        transformed,
        row_index,
        donor_index,
        r0_index,
        slices,
    )

    # G3 substitution overwrites the intervention, but masks 4--6 remain real
    # gate evaluations and need not duplicate their G3-absent counterparts.
    np.testing.assert_array_equal(
        values["real_coalitions"][4:7],
        values["paired_base_coalitions"][4:7],
    )
    assert not np.array_equal(
        values["real_coalitions"][1:4],
        values["real_coalitions"][5:8],
    )
    np.testing.assert_allclose(
        values["paired_delta"],
        C3.a17.shapley_from_coalitions(values["real_coalitions"])
        - C3.a17.shapley_from_coalitions(values["paired_base_coalitions"]),
        rtol=0.0,
        atol=0.0,
    )


def test_transform_prefers_observed_carriers_then_uses_fallback() -> None:
    context = {
        "columns": ("x", "prior"),
        "groups": {"G3": ("prior",)},
        "donor_x": np.asarray([[1.0, 0.0], [2.0, 3.0], [3.0, -2.0]]),
    }
    selected = {"G3_column": "prior", "row_sha256": "a" * 64}

    transformed, evidence = C3.transform_inputs(context, selected)

    assert evidence["operation_branch"] == "ZERO_OBSERVED_CARRIERS"
    assert evidence["observed_fit_row_carriers"] == 1
    np.testing.assert_array_equal(transformed[:, 1], [0.0, 0.0, -2.0])

    context["donor_x"] = np.asarray([[1.0, -4.0], [2.0, -2.0], [3.0, 0.0]])
    transformed, evidence = C3.transform_inputs(context, selected)

    assert evidence["operation_branch"] == "DECLARED_1_25X_FALLBACK"
    assert evidence["observed_fit_row_carriers"] == 0
    np.testing.assert_array_equal(transformed[:, 1], [-5.0, -2.5, 0.0])


def test_retargeted_control_keeps_ratified_c3_roster_slots() -> None:
    ids = [C3.statistic_id(group) for group in C3.GROUPS]

    assert all("t=child_support_received|" in statistic_id for statistic_id in ids)
    assert all("pre_subsidy_care_expenses" not in statistic_id for statistic_id in ids)
