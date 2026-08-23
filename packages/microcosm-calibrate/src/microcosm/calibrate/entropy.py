"""Bounded maximum-entropy calibration for a single numeric moment.

This module is the DataFrame-independent calibration seam.  It is deliberately
small: callers supply one numeric value per observed record and two margins,
the weighted record count and weighted value total.  The resulting exponential
tilt is the maximum-entropy member of that two-margin family before optional
absolute weight bounds are applied.

Absolute bounds can make the margins jointly infeasible.  Bounds are therefore
never hidden behind a nominally exact result: the returned receipt reports both
residuals and the number of records on each bound.  The algorithm is the
bounded free-support tilt used by the observed US firm-frame prototype in
``microcosm-dynamics`` PR #390, promoted here so standalone population artifact
builders do not have to fabricate a person/group :class:`microcosm.frame.Frame`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "BoundedMomentCalibrationResult",
    "calibrate_bounded_moment",
]


@dataclass(frozen=True)
class BoundedMomentCalibrationResult:
    """Receipt for :func:`calibrate_bounded_moment`.

    ``weights`` is ``None`` only when the requested mean is outside the
    observed support.  A successful result may still have non-zero residuals
    when absolute bounds bind; callers decide whether those residuals are
    admissible and publish that decision with the artifact.
    """

    weights: np.ndarray | None
    status: str
    reason: str | None
    target_count: float
    target_total: float
    count_estimate: float | None
    total_estimate: float | None
    count_residual: float | None
    total_residual: float | None
    target_mean: float
    observed_min: float
    observed_max: float
    weight_bounds: tuple[float, float] | None
    iterations: int
    clipped_low: int
    clipped_high: int

    @property
    def exact(self) -> bool:
        """Whether both returned margins agree with their targets numerically."""
        if self.weights is None:
            return False
        return bool(
            abs(float(self.count_residual))
            <= 1e-10 * max(abs(self.target_count), 1.0)
            and abs(float(self.total_residual))
            <= 1e-10 * max(abs(self.target_total), 1.0)
        )


def _solve_tilt(
    values: np.ndarray,
    target_mean: float,
    free: np.ndarray,
    *,
    tolerance: float,
) -> float:
    """Return the Newton-solved exponential-tilt parameter on ``free``."""
    free_values = values[free]
    tilt = 0.0
    for _ in range(200):
        weights = np.exp(
            np.clip(tilt * (free_values - target_mean), -700.0, 700.0)
        )
        total = float(weights.sum())
        if total <= 0.0 or not np.isfinite(total):
            break
        mean = float(weights @ free_values / total)
        variance = float(weights @ np.square(free_values) / total - mean**2)
        if variance <= 0.0 or not np.isfinite(variance):
            break
        step = (target_mean - mean) / variance
        tilt += step
        if abs(step) < tolerance:
            break
    return float(tilt)


def calibrate_bounded_moment(
    values: np.ndarray,
    *,
    target_count: float,
    target_total: float,
    weight_bounds: tuple[float, float] | None = None,
    max_bound_iterations: int = 20,
    tolerance: float = 1e-12,
) -> BoundedMomentCalibrationResult:
    """Calibrate positive record weights to count and numeric-total margins.

    The unconstrained solution has the exponential form
    ``w_i = c * exp(lambda * (x_i - target_mean))``.  Newton iteration solves
    ``lambda`` from the target mean and ``c`` scales weights to the count
    target.  When ``weight_bounds`` is supplied, records outside the bounds are
    removed from the next tilt's free support and all returned weights receive
    a final absolute clip.  That last clip is intentionally *not* followed by a
    rescale, because rescaling would silently violate the declared bound.

    Args:
        values: Finite one-dimensional numeric values, one per observed record.
        target_count: Positive weighted record-count margin.
        target_total: Finite weighted value-total margin.
        weight_bounds: Optional positive absolute ``(lower, upper)`` bounds.
            These are not ratios to initial weights.
        max_bound_iterations: Maximum free-support refinements.
        tolerance: Newton-step stopping tolerance.

    Returns:
        A receipt containing weights, support/bound diagnostics, and both
        residuals.  If the target mean lies outside the observed support,
        ``status`` is ``"infeasible_support"`` and ``weights`` is ``None``.

    Raises:
        ValueError: If inputs are empty, non-finite, incorrectly shaped, or
            declare invalid targets, bounds, or iteration controls.
    """
    observed = np.asarray(values, dtype=np.float64)
    if observed.ndim != 1 or observed.size == 0:
        raise ValueError("values must be a non-empty one-dimensional array")
    if not np.isfinite(observed).all():
        raise ValueError("values must contain only finite numbers")
    if not np.isfinite(target_count) or target_count <= 0.0:
        raise ValueError("target_count must be finite and positive")
    if not np.isfinite(target_total):
        raise ValueError("target_total must be finite")
    if max_bound_iterations < 1:
        raise ValueError("max_bound_iterations must be at least one")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("tolerance must be finite and positive")
    if weight_bounds is not None:
        lower, upper = map(float, weight_bounds)
        if (
            not np.isfinite(lower)
            or not np.isfinite(upper)
            or lower <= 0.0
            or upper < lower
        ):
            raise ValueError(
                "weight_bounds must be finite positive (lower, upper) values "
                "with upper >= lower"
            )
        bounds = (lower, upper)
    else:
        bounds = None

    target_count = float(target_count)
    target_total = float(target_total)
    target_mean = target_total / target_count
    observed_min = float(observed.min())
    observed_max = float(observed.max())
    if not observed_min <= target_mean <= observed_max:
        return BoundedMomentCalibrationResult(
            weights=None,
            status="infeasible_support",
            reason=(
                f"target mean {target_mean:.12g} is outside observed support "
                f"[{observed_min:.12g}, {observed_max:.12g}]"
            ),
            target_count=target_count,
            target_total=target_total,
            count_estimate=None,
            total_estimate=None,
            count_residual=None,
            total_residual=None,
            target_mean=target_mean,
            observed_min=observed_min,
            observed_max=observed_max,
            weight_bounds=bounds,
            iterations=0,
            clipped_low=0,
            clipped_high=0,
        )

    free = np.ones(observed.size, dtype=bool)
    weights = np.ones(observed.size, dtype=np.float64)
    iterations = 0
    for _ in range(max_bound_iterations):
        iterations += 1
        tilt = _solve_tilt(observed, target_mean, free, tolerance=tolerance)
        weights = np.exp(
            np.clip(tilt * (observed - target_mean), -700.0, 700.0)
        )
        weights *= target_count / float(weights.sum())
        if bounds is None:
            break
        lower, upper = bounds
        clipped = (weights < lower) | (weights > upper)
        if not clipped.any() or not (free & ~clipped).any():
            break
        free = ~clipped

    if bounds is not None:
        weights = np.clip(weights, *bounds)
        clipped_low = int(np.count_nonzero(weights <= bounds[0]))
        clipped_high = int(np.count_nonzero(weights >= bounds[1]))
    else:
        clipped_low = 0
        clipped_high = 0
    count_estimate = float(weights.sum())
    total_estimate = float(weights @ observed)
    return BoundedMomentCalibrationResult(
        weights=weights,
        status="calibrated",
        reason=None,
        target_count=target_count,
        target_total=target_total,
        count_estimate=count_estimate,
        total_estimate=total_estimate,
        count_residual=count_estimate - target_count,
        total_residual=total_estimate - target_total,
        target_mean=target_mean,
        observed_min=observed_min,
        observed_max=observed_max,
        weight_bounds=bounds,
        iterations=iterations,
        clipped_low=clipped_low,
        clipped_high=clipped_high,
    )
