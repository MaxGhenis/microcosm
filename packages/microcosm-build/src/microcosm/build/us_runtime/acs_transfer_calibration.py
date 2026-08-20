"""Deterministic array kernels for post-QRF ACS transfer calibration.

The transfer model draws a sign/carrier and a conditional amount in one
pipeline.  The terminal agreement battery measures those two surfaces
separately, so calibration must do the same: first allocate weighted carrier
or sign classes, then map magnitudes within each realized sign.  This module is
deliberately independent of :class:`~microcosm.frame.Frame`; callers retain
ownership of entity alignment and provenance.

All mutations are positionally aligned and deterministic under row reordering
when the same stable IDs are supplied.  Positive-weight immutable rows constrain
the feasible target and are reported as a projection.  Zero-weight rows are
always immutable: they provide no calibration capacity and their values must
not change merely because they happen to accompany a weighted population.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Integral, Real

import numpy as np

__all__ = [
    "SCHEDULE_D_JOINT_STATES",
    "AllocationReceipt",
    "CalibrationCapacityError",
    "ConditionalMagnitudeReceipt",
    "ScheduleDJointCarrierAllocation",
    "SignAllocation",
    "SignPreservingMagnitudeMapping",
    "WeightedBinaryCarrierSelection",
    "allocate_schedule_d_joint_carriers",
    "allocate_weighted_signs",
    "map_sign_preserving_weighted_magnitudes",
    "select_weighted_binary_carriers",
]

SCHEDULE_D_JOINT_STATES = (
    "neither_positive",
    "schedule_d_parent_only",
    "non_schedule_d_parent_only",
    "positive_overlap",
)


class CalibrationCapacityError(ValueError):
    """A requested conditional calibration has no weighted donor capacity."""


@dataclass(frozen=True)
class AllocationReceipt:
    """Weighted capacity, projection, and realization for a class allocation."""

    class_labels: tuple[str, ...]
    requested_weight: tuple[float, ...]
    projected_weight: tuple[float, ...]
    realized_weight: tuple[float, ...]
    immutable_weight: tuple[float, ...]
    capacity_lower: tuple[float, ...]
    capacity_upper: tuple[float, ...]
    projection_error: tuple[float, ...]
    allocation_error: tuple[float, ...]
    positive_weight_total: float
    mutable_weight_total: float
    immutable_positive_weight_rows: int
    zero_weight_rows_preserved: int
    changed_positive_weight_rows: int

    @property
    def maximum_absolute_projection_error(self) -> float:
        """Largest class-mass movement required by immutable capacity."""

        return max((abs(value) for value in self.projection_error), default=0.0)

    @property
    def maximum_absolute_allocation_error(self) -> float:
        """Largest class-mass error left by indivisible recipient weights."""

        return max((abs(value) for value in self.allocation_error), default=0.0)


@dataclass(frozen=True)
class WeightedBinaryCarrierSelection:
    """A read-only binary carrier mask and its weighted allocation receipt."""

    carriers: np.ndarray
    receipt: AllocationReceipt

    def __post_init__(self) -> None:
        object.__setattr__(self, "carriers", _readonly(self.carriers, np.bool_))


@dataclass(frozen=True)
class SignAllocation:
    """Read-only ``-1 / 0 / 1`` signs and their weighted allocation receipt."""

    signs: np.ndarray
    receipt: AllocationReceipt

    def __post_init__(self) -> None:
        signs = _readonly(self.signs, np.int8)
        if not np.isin(signs, (-1, 0, 1)).all():
            raise ValueError("Sign allocations may contain only -1, 0, and 1.")
        object.__setattr__(self, "signs", signs)


@dataclass(frozen=True)
class ConditionalMagnitudeReceipt:
    """One sign's recipient-to-reference weighted inverse-ECDF mapping."""

    sign: int
    recipient_carrier_rows: int
    recipient_carrier_weight: float
    reference_carrier_rows: int
    reference_carrier_weight: float
    mapped_rows: int
    mapped_weight: float
    immutable_rows: int
    immutable_weight: float
    maximum_fixed_cdf_excess_weight: float
    maximum_residual_cdf_adjustment_weight: float
    maximum_inverse_cdf_overshoot: float


@dataclass(frozen=True)
class SignPreservingMagnitudeMapping:
    """Read-only calibrated values plus one receipt for each present sign."""

    values: np.ndarray
    conditional: tuple[ConditionalMagnitudeReceipt, ...]
    zero_weight_rows_preserved: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", _readonly(self.values, np.float64))


@dataclass(frozen=True)
class ScheduleDJointCarrierAllocation:
    """Joint positive-carrier states for the two Schedule-D parent amounts."""

    schedule_d_parent_positive: np.ndarray
    non_schedule_d_parent_positive: np.ndarray
    states: np.ndarray
    receipt: AllocationReceipt

    def __post_init__(self) -> None:
        first = _readonly(self.schedule_d_parent_positive, np.bool_)
        second = _readonly(self.non_schedule_d_parent_positive, np.bool_)
        states = _readonly(self.states, np.uint8)
        if not (
            len(first) == len(second) == len(states)
            and np.array_equal(states, first.astype(np.uint8) + 2 * second)
        ):
            raise ValueError("Schedule-D joint states disagree with carrier masks.")
        object.__setattr__(self, "schedule_d_parent_positive", first)
        object.__setattr__(self, "non_schedule_d_parent_positive", second)
        object.__setattr__(self, "states", states)


def select_weighted_binary_carriers(
    initial_carriers: Sequence[bool] | np.ndarray,
    carrier_scores: Sequence[float] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    stable_ids: Sequence[object] | np.ndarray,
    *,
    target_share: float,
    immutable: Sequence[bool] | np.ndarray | None = None,
) -> WeightedBinaryCarrierSelection:
    """Select carriers by score to approach one weighted target share.

    Higher scores receive carrier status first; stable IDs resolve score ties.
    The closest prefix is used, so the remaining allocation error transparently
    reflects indivisible row weights instead of fractionalizing a person.
    """

    carriers = _boolean_vector(initial_carriers, name="initial_carriers")
    n = len(carriers)
    scores = _finite_vector(carrier_scores, n=n, name="carrier_scores")
    calibrated_weights = _weights(weights, n=n, name="weights")
    id_keys = _stable_id_keys(stable_ids, n=n, name="stable_ids")
    fixed = _immutable_mask(immutable, n=n) | (calibrated_weights == 0.0)
    share = _share(target_share, name="target_share")

    requested, projected, immutable_weight, mutable_total = _project_targets(
        initial_labels=carriers.astype(np.int8),
        weights=calibrated_weights,
        immutable=fixed,
        target_shares=np.asarray((1.0 - share, share)),
        classes=2,
    )
    result = carriers.copy()
    mutable_positions = np.flatnonzero(~fixed)
    mutable_target = projected[1] - immutable_weight[1]
    ranked = sorted(
        mutable_positions.tolist(),
        key=lambda index: (-scores[index], id_keys[index]),
    )
    selected_count = _nearest_prefix_count(
        calibrated_weights[np.asarray(ranked, dtype=np.int64)],
        mutable_target,
    )
    result[mutable_positions] = False
    if selected_count:
        result[np.asarray(ranked[:selected_count], dtype=np.int64)] = True

    receipt = _allocation_receipt(
        labels=result.astype(np.int8),
        initial_labels=carriers.astype(np.int8),
        weights=calibrated_weights,
        immutable=fixed,
        requested=requested,
        projected=projected,
        immutable_weight=immutable_weight,
        mutable_total=mutable_total,
        class_labels=("noncarrier", "carrier"),
        classes=2,
    )
    return WeightedBinaryCarrierSelection(result, receipt)


def allocate_weighted_signs(
    values: Sequence[float] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    stable_ids: Sequence[object] | np.ndarray,
    *,
    target_shares: Sequence[float] | np.ndarray,
    immutable: Sequence[bool] | np.ndarray | None = None,
) -> SignAllocation:
    """Allocate negative, zero, and positive signs independently of magnitude.

    Raw values provide class preference only.  Their magnitudes are not emitted
    here; use :func:`map_sign_preserving_weighted_magnitudes` after applying the
    returned signs to keep the hurdle and conditional-amount stages separate.
    """

    raw = _finite_vector(values, name="values")
    n = len(raw)
    calibrated_weights = _weights(weights, n=n, name="weights")
    id_keys = _stable_id_keys(stable_ids, n=n, name="stable_ids")
    fixed = _immutable_mask(immutable, n=n) | (calibrated_weights == 0.0)
    initial = np.sign(raw).astype(np.int8)
    initial_labels = initial + 1
    scores = np.column_stack((-raw, -np.abs(raw), raw))
    shares = _shares(target_shares, classes=3, name="target_shares")
    labels, receipt = _allocate_classes(
        initial_labels=initial_labels,
        scores=scores,
        weights=calibrated_weights,
        id_keys=id_keys,
        target_shares=shares,
        immutable=fixed,
        class_labels=("negative", "zero", "positive"),
    )
    return SignAllocation(labels.astype(np.int8) - 1, receipt)


def map_sign_preserving_weighted_magnitudes(
    values: Sequence[float] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    stable_ids: Sequence[object] | np.ndarray,
    reference_values: Sequence[float] | np.ndarray,
    reference_weights: Sequence[float] | np.ndarray,
    reference_stable_ids: Sequence[object] | np.ndarray,
    *,
    immutable: Sequence[bool] | np.ndarray | None = None,
) -> SignPreservingMagnitudeMapping:
    """Map each nonzero sign through a weighted empirical inverse CDF.

    Recipient weighted mid-ranks are evaluated against the reference sign's
    left-continuous weighted inverse ECDF.  Explicitly immutable carriers remain
    in the recipient rank denominator and ordering, so native values constrain
    the final-domain conditional shape even though their own bytes do not move.
    Negative values are mapped by magnitude and restored as negative, so no row
    can cross zero or change sign.  Zero-weight rows do not participate.
    """

    raw = _finite_vector(values, name="values")
    n = len(raw)
    calibrated_weights = _weights(weights, n=n, name="weights")
    id_keys = _stable_id_keys(stable_ids, n=n, name="stable_ids")
    fixed = _immutable_mask(immutable, n=n) | (calibrated_weights == 0.0)

    reference = _finite_vector(reference_values, name="reference_values")
    reference_n = len(reference)
    donor_weights = _weights(
        reference_weights,
        n=reference_n,
        name="reference_weights",
    )
    donor_id_keys = _stable_id_keys(
        reference_stable_ids,
        n=reference_n,
        name="reference_stable_ids",
    )

    output = raw.copy()
    receipts: list[ConditionalMagnitudeReceipt] = []
    for sign in (-1, 1):
        recipient_carrier = np.sign(raw) == sign
        recipient_weighted = recipient_carrier & (calibrated_weights > 0.0)
        mutable_carrier = recipient_weighted & ~fixed
        reference_carrier = (np.sign(reference) == sign) & (donor_weights > 0.0)
        recipient_weight = _checked_sum(
            calibrated_weights[recipient_weighted],
            name="recipient carrier weights",
        )
        mutable_weight = _checked_sum(
            calibrated_weights[mutable_carrier],
            name="mutable recipient carrier weights",
        )
        reference_weight = _checked_sum(
            donor_weights[reference_carrier],
            name="reference carrier weights",
        )
        if mutable_carrier.any() and reference_weight <= 0.0:
            label = "negative" if sign < 0 else "positive"
            raise CalibrationCapacityError(
                f"Cannot map {label} recipient magnitudes without positive-weight "
                f"{label} reference support."
            )

        maximum_overshoot = 0.0
        maximum_fixed_excess = 0.0
        maximum_residual_adjustment = 0.0
        if mutable_carrier.any():
            mutable_positions = np.flatnonzero(mutable_carrier)
            mutable_order = sorted(
                mutable_positions.tolist(),
                key=lambda index: (abs(raw[index]), id_keys[index]),
            )
            recipient_order_array = np.asarray(mutable_order, dtype=np.int64)
            ordered_weights = calibrated_weights[recipient_order_array]
            probabilities = (
                np.cumsum(ordered_weights) - 0.5 * ordered_weights
            ) / mutable_weight

            reference_positions = np.flatnonzero(reference_carrier)
            reference_order = sorted(
                reference_positions.tolist(),
                key=lambda index: (abs(reference[index]), donor_id_keys[index]),
            )
            reference_order_array = np.asarray(reference_order, dtype=np.int64)
            reference_magnitudes = np.abs(reference[reference_order_array])
            reference_cdf = np.cumsum(donor_weights[reference_order_array])
            reference_cdf /= reference_cdf[-1]

            immutable_positions = np.flatnonzero(recipient_weighted & fixed)
            immutable_magnitudes = np.abs(raw[immutable_positions])
            immutable_weights = calibrated_weights[immutable_positions]
            immutable_cdf_weight = np.asarray(
                [
                    _checked_sum(
                        immutable_weights[immutable_magnitudes <= reference_magnitude],
                        name="immutable conditional CDF weights",
                    )
                    for reference_magnitude in reference_magnitudes
                ],
                dtype=np.float64,
            )
            desired_recipient_cdf_weight = reference_cdf * recipient_weight
            raw_residual_cdf_weight = (
                desired_recipient_cdf_weight - immutable_cdf_weight
            )
            residual_cdf_weight = np.maximum.accumulate(
                np.clip(raw_residual_cdf_weight, 0.0, mutable_weight)
            )
            residual_cdf_weight[-1] = mutable_weight
            residual_cdf = residual_cdf_weight / mutable_weight
            maximum_fixed_excess = float(
                np.max(
                    np.maximum(
                        immutable_cdf_weight - desired_recipient_cdf_weight,
                        0.0,
                    )
                )
            )
            maximum_residual_adjustment = float(
                np.max(np.abs(residual_cdf_weight - raw_residual_cdf_weight))
            )
            inverse_positions = np.minimum(
                np.searchsorted(residual_cdf, probabilities, side="left"),
                len(residual_cdf) - 1,
            )
            mapped = reference_magnitudes[inverse_positions]
            output[recipient_order_array] = sign * mapped
            maximum_overshoot = float(
                np.max(residual_cdf[inverse_positions] - probabilities)
            )

        immutable_carrier = recipient_weighted & fixed
        receipts.append(
            ConditionalMagnitudeReceipt(
                sign=sign,
                recipient_carrier_rows=int(recipient_weighted.sum()),
                recipient_carrier_weight=recipient_weight,
                reference_carrier_rows=int(reference_carrier.sum()),
                reference_carrier_weight=reference_weight,
                mapped_rows=int(mutable_carrier.sum()),
                mapped_weight=mutable_weight,
                immutable_rows=int(immutable_carrier.sum()),
                immutable_weight=_checked_sum(
                    calibrated_weights[immutable_carrier],
                    name="immutable recipient carrier weights",
                ),
                maximum_fixed_cdf_excess_weight=maximum_fixed_excess,
                maximum_residual_cdf_adjustment_weight=(maximum_residual_adjustment),
                maximum_inverse_cdf_overshoot=maximum_overshoot,
            )
        )

    if not np.array_equal(np.sign(output), np.sign(raw)):
        raise AssertionError("Conditional magnitude mapping changed a recipient sign.")
    return SignPreservingMagnitudeMapping(
        output,
        tuple(receipts),
        zero_weight_rows_preserved=int((calibrated_weights == 0.0).sum()),
    )


def allocate_schedule_d_joint_carriers(
    schedule_d_parent_values: Sequence[float] | np.ndarray,
    non_schedule_d_parent_values: Sequence[float] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    stable_ids: Sequence[object] | np.ndarray,
    *,
    target_state_shares: Sequence[float] | np.ndarray,
    immutable: Sequence[bool] | np.ndarray | None = None,
) -> ScheduleDJointCarrierAllocation:
    """Allocate all four joint positive-carrier states of Schedule-D parents.

    State order is ``neither``, Schedule-D parent only, non-Schedule-D parent
    only, and positive overlap.  Modeling overlap explicitly prevents two
    independent binary calibrations from manufacturing or erasing the parent
    intersection that controls the derived Schedule-D carrier condition.
    """

    first = _finite_vector(schedule_d_parent_values, name="schedule_d_parent_values")
    n = len(first)
    second = _finite_vector(
        non_schedule_d_parent_values,
        n=n,
        name="non_schedule_d_parent_values",
    )
    calibrated_weights = _weights(weights, n=n, name="weights")
    id_keys = _stable_id_keys(stable_ids, n=n, name="stable_ids")
    fixed = _immutable_mask(immutable, n=n) | (calibrated_weights == 0.0)
    initial_first = first > 0.0
    initial_second = second > 0.0
    initial_states = initial_first.astype(np.uint8) + 2 * initial_second
    scores = np.column_stack(
        (
            -first - second,
            first - second,
            -first + second,
            first + second,
        )
    )
    shares = _shares(
        target_state_shares,
        classes=4,
        name="target_state_shares",
    )
    states, receipt = _allocate_classes(
        initial_labels=initial_states,
        scores=scores,
        weights=calibrated_weights,
        id_keys=id_keys,
        target_shares=shares,
        immutable=fixed,
        class_labels=SCHEDULE_D_JOINT_STATES,
    )
    states = states.astype(np.uint8)
    return ScheduleDJointCarrierAllocation(
        schedule_d_parent_positive=(states & 1) != 0,
        non_schedule_d_parent_positive=(states & 2) != 0,
        states=states,
        receipt=receipt,
    )


def _allocate_classes(
    *,
    initial_labels: np.ndarray,
    scores: np.ndarray,
    weights: np.ndarray,
    id_keys: tuple[tuple[str, object], ...],
    target_shares: np.ndarray,
    immutable: np.ndarray,
    class_labels: tuple[str, ...],
) -> tuple[np.ndarray, AllocationReceipt]:
    """Greedily allocate indivisible rows after projecting class targets."""

    classes = len(class_labels)
    requested, projected, immutable_weight, mutable_total = _project_targets(
        initial_labels=initial_labels,
        weights=weights,
        immutable=immutable,
        target_shares=target_shares,
        classes=classes,
    )
    result = initial_labels.copy()
    remaining = np.flatnonzero(~immutable).tolist()
    residual_targets = projected - immutable_weight
    class_order = sorted(
        range(classes), key=lambda item: (residual_targets[item], item)
    )
    for position, class_index in enumerate(class_order[:-1]):
        alternatives = class_order[position + 1 :]
        ranked = sorted(
            remaining,
            key=lambda row: (
                -(
                    scores[row, class_index]
                    - max(scores[row, other] for other in alternatives)
                ),
                id_keys[row],
            ),
        )
        ranked_array = np.asarray(ranked, dtype=np.int64)
        selected_count = _nearest_prefix_count(
            weights[ranked_array],
            residual_targets[class_index],
        )
        selected = ranked[:selected_count]
        if selected:
            result[np.asarray(selected, dtype=np.int64)] = class_index
        selected_set = set(selected)
        remaining = [row for row in remaining if row not in selected_set]
    if remaining:
        result[np.asarray(remaining, dtype=np.int64)] = class_order[-1]

    receipt = _allocation_receipt(
        labels=result,
        initial_labels=initial_labels,
        weights=weights,
        immutable=immutable,
        requested=requested,
        projected=projected,
        immutable_weight=immutable_weight,
        mutable_total=mutable_total,
        class_labels=class_labels,
        classes=classes,
    )
    return result, receipt


def _project_targets(
    *,
    initial_labels: np.ndarray,
    weights: np.ndarray,
    immutable: np.ndarray,
    target_shares: np.ndarray,
    classes: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    total = _checked_sum(weights, name="allocation weights")
    requested = target_shares * total
    immutable_weight = _class_weight_totals(
        initial_labels,
        weights,
        mask=immutable,
        classes=classes,
        name="immutable allocation weights",
    )
    mutable_total = _checked_sum(
        weights[~immutable],
        name="mutable allocation weights",
    )
    residual = _project_to_simplex(requested - immutable_weight, mutable_total)
    projected = immutable_weight + residual
    return requested, projected, immutable_weight, mutable_total


def _project_to_simplex(values: np.ndarray, total: float) -> np.ndarray:
    """Euclidean projection onto nonnegative vectors summing to ``total``."""

    if total < 0.0 or not math.isfinite(total):  # pragma: no cover - caller guard
        raise ValueError("Simplex total must be finite and nonnegative.")
    if total == 0.0:
        return np.zeros_like(values, dtype=np.float64)
    ordered = np.sort(np.asarray(values, dtype=np.float64))[::-1]
    cumulative = np.cumsum(ordered) - total
    indices = np.arange(1, len(ordered) + 1)
    admissible = ordered - cumulative / indices > 0.0
    rho = int(np.flatnonzero(admissible)[-1])
    theta = cumulative[rho] / float(rho + 1)
    projected = np.maximum(np.asarray(values, dtype=np.float64) - theta, 0.0)
    # Bind the floating-point residual to one class so receipts remain conserving.
    projected[int(np.argmax(projected))] += total - float(projected.sum())
    return projected


def _allocation_receipt(
    *,
    labels: np.ndarray,
    initial_labels: np.ndarray,
    weights: np.ndarray,
    immutable: np.ndarray,
    requested: np.ndarray,
    projected: np.ndarray,
    immutable_weight: np.ndarray,
    mutable_total: float,
    class_labels: tuple[str, ...],
    classes: int,
) -> AllocationReceipt:
    realized = _class_weight_totals(
        labels,
        weights,
        mask=np.ones(len(labels), dtype=bool),
        classes=classes,
        name="realized allocation weights",
    )
    changed = (labels != initial_labels) & (weights > 0.0)
    total = _checked_sum(weights, name="allocation weights")
    capacity_upper = immutable_weight + mutable_total
    return AllocationReceipt(
        class_labels=class_labels,
        requested_weight=_float_tuple(requested),
        projected_weight=_float_tuple(projected),
        realized_weight=_float_tuple(realized),
        immutable_weight=_float_tuple(immutable_weight),
        capacity_lower=_float_tuple(immutable_weight),
        capacity_upper=_float_tuple(capacity_upper),
        projection_error=_float_tuple(projected - requested),
        allocation_error=_float_tuple(realized - projected),
        positive_weight_total=total,
        mutable_weight_total=mutable_total,
        immutable_positive_weight_rows=int((immutable & (weights > 0.0)).sum()),
        zero_weight_rows_preserved=int((weights == 0.0).sum()),
        changed_positive_weight_rows=int(changed.sum()),
    )


def _nearest_prefix_count(weights: np.ndarray, target: float) -> int:
    if len(weights) == 0 or target <= 0.0:
        return 0
    cumulative = np.concatenate((np.zeros(1), np.cumsum(weights)))
    errors = np.abs(cumulative - target)
    return int(np.argmin(errors))


def _class_weight_totals(
    labels: np.ndarray,
    weights: np.ndarray,
    *,
    mask: np.ndarray,
    classes: int,
    name: str,
) -> np.ndarray:
    return np.asarray(
        [
            _checked_sum(
                weights[mask & (labels == class_index)],
                name=name,
            )
            for class_index in range(classes)
        ],
        dtype=np.float64,
    )


def _shares(
    values: Sequence[float] | np.ndarray, *, classes: int, name: str
) -> np.ndarray:
    shares = _finite_vector(values, n=classes, name=name)
    if (shares < 0.0).any():
        raise ValueError(f"{name} must be nonnegative.")
    total = _checked_sum(shares, name=name)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{name} must sum to 1; got {total:.17g}.")
    shares = shares / total
    return shares


def _share(value: float, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite probability.") from error
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1].")
    return result


def _weights(
    values: Sequence[float] | np.ndarray,
    *,
    n: int,
    name: str,
) -> np.ndarray:
    result = _finite_vector(values, n=n, name=name)
    if (result < 0.0).any():
        raise ValueError(f"{name} must be nonnegative.")
    _checked_sum(result, name=name)
    return result


def _checked_sum(values: Sequence[float] | np.ndarray, *, name: str) -> float:
    try:
        result = math.fsum(sorted(float(value) for value in values))
    except OverflowError as error:
        raise ValueError(f"{name} must have a finite aggregate.") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} must have a finite aggregate.")
    return result


def _finite_vector(
    values: Sequence[float] | np.ndarray,
    *,
    n: int | None = None,
    name: str,
) -> np.ndarray:
    try:
        result = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a one-dimensional numeric array.") from error
    if result.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional.")
    if n is not None and len(result) != n:
        raise ValueError(f"{name} must contain {n} rows; got {len(result)}.")
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must contain only finite values.")
    return result


def _boolean_vector(values: Sequence[bool] | np.ndarray, *, name: str) -> np.ndarray:
    result = np.asarray(values)
    if result.ndim != 1 or result.dtype.kind != "b":
        raise ValueError(f"{name} must be a one-dimensional boolean array.")
    return result.astype(np.bool_, copy=False)


def _immutable_mask(
    values: Sequence[bool] | np.ndarray | None,
    *,
    n: int,
) -> np.ndarray:
    if values is None:
        return np.zeros(n, dtype=bool)
    result = _boolean_vector(values, name="immutable")
    if len(result) != n:
        raise ValueError(f"immutable must contain {n} rows; got {len(result)}.")
    return result


def _stable_id_keys(
    values: Sequence[object] | np.ndarray,
    *,
    n: int,
    name: str,
) -> tuple[tuple[str, object], ...]:
    array = np.asarray(values, dtype=object)
    if array.ndim != 1:
        raise ValueError(f"{name} must be a one-dimensional array of scalar IDs.")
    if len(array) != n:
        raise ValueError(f"{name} must contain {n} rows; got {len(array)}.")
    keys: list[tuple[str, object]] = []
    seen: set[tuple[str, object]] = set()
    for position, raw in enumerate(array.tolist()):
        value = raw.item() if isinstance(raw, np.generic) else raw
        if value is None or value is np.ma.masked:
            raise ValueError(f"{name} contains a missing ID at position {position}.")
        if isinstance(value, (str, bytes)):
            if len(value) == 0:
                raise ValueError(
                    f"{name} contains a missing ID at position {position}."
                )
            key: tuple[str, object] = (type(value).__name__, value)
        elif isinstance(value, Integral):
            key = ("number", int(value))
        elif isinstance(value, Real):
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(
                    f"{name} contains a missing ID at position {position}."
                )
            key = ("number", numeric)
        else:
            raise ValueError(
                f"{name} contains unsupported non-scalar ID {value!r} at "
                f"position {position}."
            )
        if key in seen:
            raise ValueError(f"{name} contains duplicate ID {value!r}.")
        seen.add(key)
        keys.append(key)
    return tuple(keys)


def _readonly(values: np.ndarray, dtype: type[np.generic]) -> np.ndarray:
    result = np.ascontiguousarray(np.asarray(values, dtype=dtype))
    result.setflags(write=False)
    return result


def _float_tuple(values: np.ndarray) -> tuple[float, ...]:
    return tuple(float(value) for value in values)
