"""Contracts for standalone bounded moment calibration."""

from __future__ import annotations

import numpy as np
import pytest

from microcosm.calibrate import calibrate_bounded_moment


def test_bounded_moment_hits_feasible_count_and_total() -> None:
    result = calibrate_bounded_moment(
        np.array([1.0, 3.0]),
        target_count=4.0,
        target_total=10.0,
    )

    assert result.status == "calibrated"
    assert result.weights == pytest.approx([1.0, 3.0])
    assert result.count_residual == pytest.approx(0.0)
    assert result.total_residual == pytest.approx(0.0)
    assert result.exact


def test_bounded_moment_reports_bound_residual_without_rescaling() -> None:
    result = calibrate_bounded_moment(
        np.array([1.0, 3.0]),
        target_count=4.0,
        target_total=10.0,
        weight_bounds=(0.1, 2.0),
        max_bound_iterations=1,
    )

    assert result.weights == pytest.approx([1.0, 2.0])
    assert result.clipped_high == 1
    assert result.count_residual == pytest.approx(-1.0)
    assert result.total_residual == pytest.approx(-3.0)
    assert not result.exact


def test_bounded_moment_returns_named_infeasible_support() -> None:
    result = calibrate_bounded_moment(
        np.array([2.0, 4.0]),
        target_count=3.0,
        target_total=15.0,
        weight_bounds=(0.1, 140.0),
    )

    assert result.weights is None
    assert result.status == "infeasible_support"
    assert result.reason == "target mean 5 is outside observed support [2, 4]"
    assert result.iterations == 0


@pytest.mark.parametrize(
    ("values", "kwargs", "message"),
    [
        ([], {}, "non-empty one-dimensional"),
        ([1.0, np.nan], {}, "finite numbers"),
        ([1.0], {"target_count": 0.0}, "target_count"),
        ([1.0], {"weight_bounds": (0.0, 1.0)}, "weight_bounds"),
    ],
)
def test_bounded_moment_rejects_invalid_inputs(values, kwargs, message) -> None:
    options = {"target_count": 1.0, "target_total": 1.0, **kwargs}
    with pytest.raises(ValueError, match=message):
        calibrate_bounded_moment(np.asarray(values), **options)
