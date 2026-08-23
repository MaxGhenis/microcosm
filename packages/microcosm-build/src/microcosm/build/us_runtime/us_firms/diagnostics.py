"""JSON-ready diagnostics for observed US firm-frame weights."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from microcosm.calibrate import effective_sample_size

__all__ = ["margin_ratio", "weight_diagnostics"]


def margin_ratio(estimate: float, target: float) -> float | None:
    """Return ``estimate / target``, with ``None`` for a zero target."""
    target = float(target)
    return float(estimate) / target if target != 0.0 else None


def _as_float_vector(values: Iterable[float]) -> np.ndarray:
    """Materialize an array-like or iterator once as a float vector."""
    if hasattr(values, "__array__"):
        return np.asarray(values, dtype=np.float64)
    return np.fromiter(values, dtype=np.float64)


def weight_diagnostics(
    weights: Iterable[float],
    *,
    employment: Iterable[float] | None = None,
    bounds: tuple[float, float] | None = None,
) -> dict[str, object]:
    """Summarize weight spread, Kish ESS, bound hits, and leverage.

    Firm-margin leverage is a row's share of total weight. Employment-margin
    leverage is a row's share of ``weight * employment``. Both definitions are
    published in the returned payload so downstream reports do not have to
    infer what "leverage" meant.
    """
    values = _as_float_vector(weights)
    if values.ndim != 1:
        raise ValueError("weights must be one-dimensional")
    if not np.isfinite(values).all() or (values < 0.0).any():
        raise ValueError("weights must be finite and non-negative")
    if values.size == 0:
        return {
            "records": 0,
            "sum": 0.0,
            "minimum": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p90": None,
            "p99": None,
            "maximum": None,
            "effective_sample_size": 0.0,
            "effective_sample_size_ratio": None,
            "lower_bound_hits": 0,
            "upper_bound_hits": 0,
            "maximum_firm_margin_leverage": None,
            "maximum_employment_margin_leverage": None,
            "leverage_definition": {
                "firm": "max(firm_weight) / sum(firm_weight)",
                "employment": (
                    "max(firm_weight * employment) / "
                    "sum(firm_weight * employment)"
                ),
            },
        }

    total = float(values.sum())
    quantiles = np.quantile(values, [0.25, 0.5, 0.75, 0.9, 0.99])
    ess = float(effective_sample_size(values))
    if bounds is None:
        lower_hits = 0
        upper_hits = 0
    else:
        lower, upper = bounds
        lower_hits = int(
            np.count_nonzero(np.isclose(values, lower, rtol=0.0, atol=1e-12))
        )
        upper_hits = int(
            np.count_nonzero(np.isclose(values, upper, rtol=0.0, atol=1e-12))
        )

    employment_leverage: float | None = None
    if employment is not None:
        counts = _as_float_vector(employment)
        if counts.shape != values.shape:
            raise ValueError("employment must align one-to-one with weights")
        if not np.isfinite(counts).all() or (counts < 0.0).any():
            raise ValueError("employment must be finite and non-negative")
        contributions = values * counts
        contribution_total = float(contributions.sum())
        if contribution_total > 0.0:
            employment_leverage = float(contributions.max() / contribution_total)

    return {
        "records": int(values.size),
        "sum": total,
        "minimum": float(values.min()),
        "p25": float(quantiles[0]),
        "median": float(quantiles[1]),
        "p75": float(quantiles[2]),
        "p90": float(quantiles[3]),
        "p99": float(quantiles[4]),
        "maximum": float(values.max()),
        "effective_sample_size": ess,
        "effective_sample_size_ratio": ess / values.size,
        "lower_bound_hits": lower_hits,
        "upper_bound_hits": upper_hits,
        "maximum_firm_margin_leverage": (
            float(values.max() / total) if total > 0.0 else None
        ),
        "maximum_employment_margin_leverage": employment_leverage,
        "leverage_definition": {
            "firm": "max(firm_weight) / sum(firm_weight)",
            "employment": (
                "max(firm_weight * employment) / "
                "sum(firm_weight * employment)"
            ),
        },
    }
