"""Focused exact-metric tests for the A18 Phase-0 P5 executor."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module():
    path = TOOLS / "qrf_drift_phase0_p5.py"
    spec = importlib.util.spec_from_file_location("qrf_drift_phase0_p5", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOLS))
    return module


P5 = _load_module()


def test_weighted_inverse_cdf_and_zero_iqr_semantics() -> None:
    values = np.asarray([0.0, 1.0, 100.0])
    weights = np.asarray([1.0, 8.0, 1.0])

    assert P5.weighted_inverse_cdf(values, weights, 0.25) == 1.0
    assert P5.weighted_inverse_cdf(values, weights, 0.75) == 1.0
    definition = P5.metric_definition(
        np.column_stack((values, [0.0, 0.0, 1.0])),
        weights,
        ("age", "is_female"),
    )
    assert definition["features"][0]["semantics"] == "numeric_zero_iqr_exact_mismatch"
    assert definition["features"][1]["semantics"] == "categorical_exact_mismatch"


def test_exact_gower_scores_match_full_sorted_fixture() -> None:
    donor = np.asarray(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [2.0, 1.0],
            [4.0, 1.0],
        ]
    )
    recipient = np.asarray([[1.0, 1.0], [4.0, 0.0]])
    weights = np.ones(4)
    definition = P5.metric_definition(donor, weights, ("age", "is_female"))

    scores, diagnostics = P5.exact_gower_knn_scores(
        donor,
        recipient,
        definition,
        k=2,
        block_size=1,
    )

    expected = []
    iqr = definition["features"][0]["iqr"]
    for row in recipient:
        distances = (
            np.minimum(np.abs(row[0] - donor[:, 0]) / iqr, 1.0)
            + (row[1] != donor[:, 1])
        ) / 2.0
        expected.append(np.sort(distances)[:2].sum(dtype=np.float64) / 2.0)
    np.testing.assert_array_equal(scores, expected)
    assert diagnostics["exact_all_donor_search"] is True
    assert diagnostics["approximation"] is False
    assert diagnostics["pool_under_25"] is True


def test_distance_ties_cannot_change_the_reported_mean() -> None:
    donor = np.asarray([[0.0], [2.0], [2.0], [4.0]])
    recipient = np.asarray([[1.0]])
    definition = P5.metric_definition(donor, np.ones(4), ("age",))

    score, _diagnostics = P5.exact_gower_knn_scores(
        donor, recipient, definition, k=2, block_size=1
    )

    # Both donor rows at the cutoff have the same distance.  Either A16
    # stable-source-id ordering therefore gives the same arithmetic score.
    assert score[0] == 0.5


def test_weighted_midpoint_deciles_use_score_then_stable_id() -> None:
    score = np.asarray([0.0, 0.0, 1.0, 2.0])
    stable_id = np.asarray([20, 10, 30, 40])
    weights = np.asarray([1.0, 1.0, 6.0, 2.0])

    bins, diagnostic = P5.weighted_decile_bins(score, stable_id, weights)

    # Sorted order is source ids 10,20 at the tied score, then 30,40.
    np.testing.assert_array_equal(bins, [1, 0, 5, 9])
    assert diagnostic["sort"] == ["score", "stable_entity_id"]
    assert diagnostic["bin_rows"][9] == 1
    assert sum(diagnostic["bin_weight"]) == 10.0


def test_bound_d0_work_and_conservative_a8_disposition() -> None:
    d0 = json.loads((ROOT / "experiments/qrf_drift_validation_d0.json").read_text())

    estimate = P5.work_estimate(d0)

    assert estimate["literal_target_pattern_surfaces"] == 36
    assert estimate["literal_recipient_rows"] == 7_235_911
    assert estimate["literal_pairwise_distances"] == 757_457_932_367
    assert estimate["literal_feature_pair_costs"] == 7_737_368_701_691
    assert estimate["identical_metric_surfaces"] == 24
    assert estimate["cached_pairwise_distances"] == 479_723_507_273
    assert estimate["cached_feature_pair_costs"] == 5_098_887_772_670
    assert estimate["conservative_cached_kernel_hours"] < 20.0
    assert estimate["conservative_literal_kernel_hours"] < 20.0
    assert estimate["conservative_literal_kernel_hours"] > estimate[
        "conservative_cached_kernel_hours"
    ]
    assert estimate["disposition"] == "MECHANICALLY_FEASIBLE_EXACT_UNDER_A8"


def test_statistic_fragment_uses_sealed_p5_dimensions() -> None:
    row = P5.statistic_fragment(
        "weeks_unemployed",
        "positive",
        "P5_decile",
        value=0.25,
        status="OK",
        decile="09",
        variant="drift",
        source_pointer="/A16-36",
        sources=[],
    )

    assert row["id"] == (
        "r=candidate-25|t=weeks_unemployed|p=_|l=positive|row=P5_decile|"
        "g=_|prior=_|gq=_|d=09|rep=_|fold=_|v=drift"
    )
    assert row["family"] is None
    assert row["gated"] is False
    assert row["record_type"] == "scalar"


def test_manifest_validation_rejects_static_or_status_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = "weeks_unemployed"
    statistics = []
    manifest = []
    for leg in P5.LEGS:
        for decile in range(10):
            decile_text = f"{decile:02d}"
            for variant in ("drift", "mean_distance", "weight"):
                row = P5.statistic_fragment(
                    target,
                    leg,
                    "P5_decile",
                    value=0.0,
                    status="OK",
                    decile=decile_text,
                    variant=variant,
                    source_pointer="/A16-35",
                    sources=[],
                )
                statistics.append(row)
        statistics.append(
            P5.statistic_fragment(
                target,
                leg,
                "P5_concentration",
                value="NA",
                status="NOT_APPLICABLE",
                source_pointer="/A16-36",
                sources=[],
            )
        )
    for row in statistics:
        manifest.append(
            {
                "id": row["id"],
                "dimensions": {
                    name: row[name]
                    for name in (
                        "rung",
                        "target",
                        "pattern",
                        "leg",
                        "row",
                        "group",
                        "prior",
                        "gq",
                        "decile",
                        "repeat",
                        "fold",
                        "variant",
                    )
                },
                "family": None,
                "gated": False,
                "record_type": "scalar",
                "allowed_statuses": ["OK", "NOT_APPLICABLE"],
            }
        )
    path = tmp_path / "manifest.json"
    payload = {"step0": {"required_id_manifest": manifest}}
    payload["canonical_sha256"] = P5.canonical_sha256(payload)
    path.write_text(json.dumps(payload))
    monkeypatch.setattr(P5, "STEP0_MANIFEST_SHA256", P5.sha256_file(path))

    result = P5.validate_manifest_fragments(statistics, path, (target,))

    assert result["status"] == "PASS"
    assert result["fragment_count"] == 62
    statistics[0]["gated"] = True
    with np.testing.assert_raises(ValueError):
        P5.validate_manifest_fragments(statistics, path, (target,))
