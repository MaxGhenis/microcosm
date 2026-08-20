"""Reconcile the joint carrier geometry of the two Schedule-D parents.

The derived Schedule-D input is positive when long-term capital gains are
positive and non-Schedule-D capital gains are nonpositive.  Calibrating those
parents independently can therefore preserve both marginal carrier rates while
misstating their intersection.  This module repairs only that intersection:
long-term values are byte-preserved and positive non-Schedule-D values may swap
with zeros only across rows carrying the exact same population weight.

Rows must already be aligned to the grain at which Schedule-D incidence is
decided.  The caller owns entity aggregation, provenance, and conversion of the
comparison incidence into an absolute target numerator.  The equal-weight swap
contract preserves the weighted non-Schedule-D carrier margin and conditional
amount distribution exactly, and never changes a zero-weight row.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from numbers import Integral, Real
from typing import TypeVar

import numpy as np

__all__ = [
    "SCHEDULE_D_JOINT_ROLE_COLUMN",
    "SCHEDULE_D_JOINT_ROLE_EXCLUDED",
    "SCHEDULE_D_JOINT_ROLE_RECIPIENT",
    "SCHEDULE_D_JOINT_ROLE_REFERENCE",
    "SCHEDULE_D_RECONCILED_PERSON_COLUMNS",
    "ScheduleDJointReconciliation",
    "ScheduleDJointReconciliationError",
    "ScheduleDJointReconciliationReceipt",
    "reconcile_schedule_d_joint_parents",
]

SCHEDULE_D_RECONCILED_PERSON_COLUMNS: tuple[str, ...] = (
    "non_sch_d_capital_gains",
    "schedule_d_capital_gain_distributions",
)
"""Complete person-column mutation/output surface of Schedule-D reconciliation."""

SCHEDULE_D_JOINT_ROLE_COLUMN = "schedule_d_joint_reconciliation_role"
"""Transient person-table column carrying source-neutral reconciliation roles."""

SCHEDULE_D_JOINT_ROLE_EXCLUDED = 0
"""Rows outside the clone-0 by-origin comparison and adjustment populations."""

SCHEDULE_D_JOINT_ROLE_REFERENCE = 1
"""Rows defining the comparison incidence supplied by the source-aware caller."""

SCHEDULE_D_JOINT_ROLE_RECIPIENT = 2
"""Rows whose joint-parent carrier geometry the source-blind kernel may adjust."""

_T = TypeVar("_T", bound=np.generic)


class ScheduleDJointReconciliationError(ValueError):
    """The requested reconciliation has invalid or ambiguous inputs."""


@dataclass(frozen=True)
class ScheduleDJointReconciliationReceipt:
    """Capacity, allocation, and preservation facts for one reconciliation."""

    method: str
    requested_schedule_d_positive_weight: float
    total_weight: float
    before_schedule_d_positive_rows: int
    before_schedule_d_positive_weight: float
    before_schedule_d_positive_share: float
    after_schedule_d_positive_rows: int
    after_schedule_d_positive_weight: float
    after_schedule_d_positive_share: float
    feasible_schedule_d_weight_min: float
    feasible_schedule_d_weight_max: float
    projected_schedule_d_positive_weight: float
    absolute_target_error_weight: float
    absolute_projected_error_weight: float
    available_decrease_swaps: int
    available_increase_swaps: int
    selected_swaps: int
    maximum_available_swap_weight: float
    maximum_selected_swap_weight: float
    movable_rows: int
    immutable_rows: int
    zero_weight_rows_preserved: int
    changed_non_schedule_d_rows: int
    positive_carrier_count_before: int
    positive_carrier_count_after: int
    direct_positive_weight_before: float
    direct_positive_weight_after: float
    direct_positive_weight_drift: float
    long_term_byte_preserved: bool
    positive_value_multiset_preserved: bool
    mutable_value_weight_multiset_preserved: bool
    weighted_direct_carrier_preserved: bool
    weighted_positive_distribution_preserved: bool


@dataclass(frozen=True)
class ScheduleDJointReconciliation:
    """Read-only reconciled parent arrays and their audit receipt."""

    long_term_values: np.ndarray
    non_schedule_d_values: np.ndarray
    receipt: ScheduleDJointReconciliationReceipt

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "long_term_values",
            _readonly_copy(self.long_term_values),
        )
        object.__setattr__(
            self,
            "non_schedule_d_values",
            _readonly_copy(self.non_schedule_d_values),
        )


@dataclass(frozen=True)
class _SwapOpportunity:
    """One disjoint, exactly weight-matched positive/zero exchange."""

    weight: float
    positive_source: int
    zero_destination: int


def reconcile_schedule_d_joint_parents(
    long_term_values: Sequence[float] | np.ndarray,
    non_schedule_d_values: Sequence[float] | np.ndarray,
    weights: Sequence[float] | np.ndarray,
    stable_ids: Sequence[object] | np.ndarray,
    *,
    mutable_non_schedule_d: Sequence[bool] | np.ndarray,
    target_schedule_d_positive_weight: float,
) -> ScheduleDJointReconciliation:
    """Reroute weight-matched direct positives toward a Schedule-D target.

    A legal move exchanges one positive value and one zero value between the
    long-term-positive and long-term-nonpositive groups.  Both rows must have
    positive, byte-identical float64 weights and belong to
    ``mutable_non_schedule_d``.  Negative values, zero-weight rows, and every
    row outside that mask are immutable.

    Legal swaps are disjoint and generated deterministically within exact
    weight buckets.  A descending-weight greedy subset plus deterministic
    single-toggle and one-for-one-exchange repairs approaches an interior target
    in ``O(n log n)`` time and linear memory.  Capacity projection and the
    remaining indivisible-row error are reported explicitly; no global optimum
    is claimed.
    """

    long_term_raw, long_term = _numeric_vector(
        long_term_values,
        name="long_term_values",
    )
    n = len(long_term)
    direct_raw, direct = _numeric_vector(
        non_schedule_d_values,
        n=n,
        name="non_schedule_d_values",
    )
    calibrated_weights = _weights(weights, n=n)
    id_keys = _stable_id_keys(stable_ids, n=n)
    mutable_requested = _boolean_vector(
        mutable_non_schedule_d,
        n=n,
        name="mutable_non_schedule_d",
    )
    target_weight = _target_weight(target_schedule_d_positive_weight)
    total_weight = _checked_sum(calibrated_weights, name="weights")
    if total_weight <= 0.0:
        raise ScheduleDJointReconciliationError(
            "Schedule-D reconciliation requires positive total recipient weight."
        )

    long_term_snapshot = np.ascontiguousarray(long_term_raw).tobytes()
    direct_snapshot = direct_raw.copy()
    positive_before = direct > 0.0
    long_term_positive = long_term > 0.0
    schedule_before = long_term_positive & (direct <= 0.0)

    # Negative values carry a distinct signed parent margin, while zero-weight
    # rows supply no population capacity.  Both remain immutable even when the
    # caller's provenance mask marks them mutable.
    movable = mutable_requested & (calibrated_weights > 0.0) & (direct >= 0.0)
    before_weight = _checked_sum(
        calibrated_weights[schedule_before],
        name="before Schedule-D carrier weights",
    )
    direct_weight_before = _checked_sum(
        calibrated_weights[positive_before],
        name="before direct-positive carrier weights",
    )

    decrease_opportunities = _weight_matched_opportunities(
        positive_sources=movable & positive_before & ~long_term_positive,
        zero_destinations=movable & ~positive_before & long_term_positive,
        weights=calibrated_weights,
        id_keys=id_keys,
    )
    increase_opportunities = _weight_matched_opportunities(
        positive_sources=movable & positive_before & long_term_positive,
        zero_destinations=movable & ~positive_before & ~long_term_positive,
        weights=calibrated_weights,
        id_keys=id_keys,
    )
    decrease_destinations = np.zeros(n, dtype=bool)
    for opportunity in decrease_opportunities:
        decrease_destinations[opportunity.zero_destination] = True
    increase_sources = np.zeros(n, dtype=bool)
    for opportunity in increase_opportunities:
        increase_sources[opportunity.positive_source] = True
    feasible_min = _checked_sum(
        calibrated_weights[schedule_before & ~decrease_destinations],
        name="minimum feasible Schedule-D carrier weights",
    )
    feasible_max = _checked_sum(
        calibrated_weights[schedule_before | increase_sources],
        name="maximum feasible Schedule-D carrier weights",
    )
    projected_weight = min(max(target_weight, feasible_min), feasible_max)

    if projected_weight < before_weight:
        direction = -1.0
        opportunities = decrease_opportunities
        requested_change = before_weight - projected_weight
    elif projected_weight > before_weight:
        direction = 1.0
        opportunities = increase_opportunities
        requested_change = projected_weight - before_weight
    else:
        direction = 0.0
        opportunities = ()
        requested_change = 0.0

    selected = _select_swap_subset(
        opportunities,
        requested_change=requested_change,
        id_keys=id_keys,
    )
    output = direct_raw.copy()
    for opportunity in selected:
        source = opportunity.positive_source
        destination = opportunity.zero_destination
        output[source], output[destination] = output[destination], output[source]

    output_numeric = output.astype(np.float64, copy=False)
    positive_after = output_numeric > 0.0
    schedule_after = long_term_positive & (output_numeric <= 0.0)
    after_weight = _checked_sum(
        calibrated_weights[schedule_after],
        name="after Schedule-D carrier weights",
    )
    direct_weight_after = _checked_sum(
        calibrated_weights[positive_after],
        name="after direct-positive carrier weights",
    )
    expected_schedule = schedule_before.copy()
    if direction < 0.0:
        for opportunity in selected:
            expected_schedule[opportunity.zero_destination] = False
    elif direction > 0.0:
        for opportunity in selected:
            expected_schedule[opportunity.positive_source] = True
    if not np.array_equal(schedule_after, expected_schedule):
        raise AssertionError("Schedule-D swaps do not match their carrier receipt.")

    long_term_preserved = (
        np.ascontiguousarray(long_term_raw).tobytes() == long_term_snapshot
    )
    positive_multiset_preserved = _positive_multiset_equal(
        direct_snapshot,
        output,
    )
    mutable_weight_multiset_preserved = _value_weight_multiset(
        direct_snapshot[movable],
        calibrated_weights[movable],
    ) == _value_weight_multiset(output[movable], calibrated_weights[movable])
    weighted_positive_distribution_preserved = _value_weight_multiset(
        direct_snapshot[positive_before],
        calibrated_weights[positive_before],
    ) == _value_weight_multiset(
        output[positive_after],
        calibrated_weights[positive_after],
    )
    immutable = ~movable
    if not np.array_equal(output[immutable], direct_snapshot[immutable]):
        raise AssertionError("Schedule-D reconciliation changed an immutable row.")
    if int(positive_after.sum()) != int(positive_before.sum()):
        raise AssertionError("Schedule-D reconciliation changed positive count.")
    if not long_term_preserved:
        raise AssertionError("Schedule-D reconciliation changed long-term values.")
    if not positive_multiset_preserved or not mutable_weight_multiset_preserved:
        raise AssertionError("Schedule-D reconciliation changed parent value support.")
    weighted_direct_preserved = math.isclose(
        direct_weight_after,
        direct_weight_before,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    if not weighted_direct_preserved or not weighted_positive_distribution_preserved:
        raise AssertionError(
            "Schedule-D reconciliation changed the weighted direct-parent margin."
        )

    all_opportunity_weights = [
        item.weight for item in (*decrease_opportunities, *increase_opportunities)
    ]
    receipt = ScheduleDJointReconciliationReceipt(
        method="heuristic_equal_weight_swap_frontier_v2_not_globally_certified",
        requested_schedule_d_positive_weight=target_weight,
        total_weight=total_weight,
        before_schedule_d_positive_rows=int(schedule_before.sum()),
        before_schedule_d_positive_weight=before_weight,
        before_schedule_d_positive_share=before_weight / total_weight,
        after_schedule_d_positive_rows=int(schedule_after.sum()),
        after_schedule_d_positive_weight=after_weight,
        after_schedule_d_positive_share=after_weight / total_weight,
        feasible_schedule_d_weight_min=feasible_min,
        feasible_schedule_d_weight_max=feasible_max,
        projected_schedule_d_positive_weight=projected_weight,
        absolute_target_error_weight=abs(after_weight - target_weight),
        absolute_projected_error_weight=abs(after_weight - projected_weight),
        available_decrease_swaps=len(decrease_opportunities),
        available_increase_swaps=len(increase_opportunities),
        selected_swaps=len(selected),
        maximum_available_swap_weight=max(all_opportunity_weights, default=0.0),
        maximum_selected_swap_weight=max(
            (item.weight for item in selected),
            default=0.0,
        ),
        movable_rows=int(movable.sum()),
        immutable_rows=int((~movable).sum()),
        zero_weight_rows_preserved=int((calibrated_weights == 0.0).sum()),
        changed_non_schedule_d_rows=int(np.count_nonzero(output != direct_snapshot)),
        positive_carrier_count_before=int(positive_before.sum()),
        positive_carrier_count_after=int(positive_after.sum()),
        direct_positive_weight_before=direct_weight_before,
        direct_positive_weight_after=direct_weight_after,
        direct_positive_weight_drift=direct_weight_after - direct_weight_before,
        long_term_byte_preserved=long_term_preserved,
        positive_value_multiset_preserved=positive_multiset_preserved,
        mutable_value_weight_multiset_preserved=mutable_weight_multiset_preserved,
        weighted_direct_carrier_preserved=weighted_direct_preserved,
        weighted_positive_distribution_preserved=(
            weighted_positive_distribution_preserved
        ),
    )
    return ScheduleDJointReconciliation(long_term_raw, output, receipt)


def _weight_matched_opportunities(
    *,
    positive_sources: np.ndarray,
    zero_destinations: np.ndarray,
    weights: np.ndarray,
    id_keys: tuple[tuple[str, object], ...],
) -> tuple[_SwapOpportunity, ...]:
    source_buckets = _weight_buckets(positive_sources, weights)
    destination_buckets = _weight_buckets(zero_destinations, weights)
    opportunities: list[_SwapOpportunity] = []
    shared_keys = sorted(
        source_buckets.keys() & destination_buckets.keys(),
        key=_weight_bucket_order_key,
    )
    for weight_key in shared_keys:
        sources = sorted(source_buckets[weight_key], key=id_keys.__getitem__)
        destinations = sorted(
            destination_buckets[weight_key],
            key=id_keys.__getitem__,
        )
        weight = float(np.frombuffer(weight_key, dtype=np.float64)[0])
        opportunities.extend(
            _SwapOpportunity(weight, source, destination)
            for source, destination in zip(sources, destinations, strict=False)
        )
    return tuple(opportunities)


def _weight_buckets(
    mask: np.ndarray,
    weights: np.ndarray,
) -> dict[bytes, list[int]]:
    buckets: dict[bytes, list[int]] = {}
    for position in np.flatnonzero(mask).tolist():
        key = np.asarray(weights[position], dtype=np.float64).tobytes()
        buckets.setdefault(key, []).append(position)
    return buckets


def _weight_bucket_order_key(weight_key: bytes) -> tuple[float, bytes]:
    return float(np.frombuffer(weight_key, dtype=np.float64)[0]), weight_key


def _select_swap_subset(
    opportunities: Sequence[_SwapOpportunity],
    *,
    requested_change: float,
    id_keys: tuple[tuple[str, object], ...],
) -> tuple[_SwapOpportunity, ...]:
    if requested_change <= 0.0 or not opportunities:
        return ()
    ordered = sorted(
        opportunities,
        key=lambda item: (
            -item.weight,
            id_keys[item.positive_source],
            id_keys[item.zero_destination],
        ),
    )
    selected = np.zeros(len(ordered), dtype=bool)
    realized = 0.0
    for index, opportunity in enumerate(ordered):
        proposed = realized + opportunity.weight
        if abs(proposed - requested_change) < abs(realized - requested_change):
            selected[index] = True
            realized = proposed

    # Disclosed deterministic repairs reduce dependence on unlucky greedy
    # choices without turning the large-cohort path into an unbounded subset
    # search.  Ties prefer fewer relocations, then canonical opportunity order.
    selected_count = int(selected.sum())
    best_key = (abs(realized - requested_change), selected_count, -1)
    best_toggle: int | None = None
    for index, opportunity in enumerate(ordered):
        candidate = realized + (
            -opportunity.weight if selected[index] else opportunity.weight
        )
        candidate_count = selected_count + (-1 if selected[index] else 1)
        key = (abs(candidate - requested_change), candidate_count, index)
        if key < best_key:
            best_key = key
            best_toggle = index
    if best_toggle is not None:
        selected[best_toggle] = ~selected[best_toggle]
        realized += (
            ordered[best_toggle].weight
            if selected[best_toggle]
            else -ordered[best_toggle].weight
        )

    exchange = _best_single_exchange(
        ordered,
        selected=selected,
        realized=realized,
        requested_change=requested_change,
    )
    if exchange is not None:
        remove_index, add_index = exchange
        selected[remove_index] = False
        selected[add_index] = True
    return tuple(
        opportunity for index, opportunity in enumerate(ordered) if selected[index]
    )


def _best_single_exchange(
    ordered: Sequence[_SwapOpportunity],
    *,
    selected: np.ndarray,
    realized: float,
    requested_change: float,
) -> tuple[int, int] | None:
    selected_indices = np.flatnonzero(selected).tolist()
    unselected_indices = np.flatnonzero(~selected).tolist()
    if not selected_indices or not unselected_indices:
        return None
    unselected_by_weight = sorted(
        (ordered[index].weight, index) for index in unselected_indices
    )
    unselected_weights = [item[0] for item in unselected_by_weight]
    current_error = abs(realized - requested_change)
    best_key: tuple[float, int, int] | None = None
    best_exchange: tuple[int, int] | None = None
    residual = requested_change - realized
    for remove_index in selected_indices:
        desired_add_weight = ordered[remove_index].weight + residual
        insertion = bisect.bisect_left(unselected_weights, desired_add_weight)
        candidate_positions = {
            max(0, insertion - 1),
            min(len(unselected_by_weight) - 1, insertion),
        }
        for candidate_position in candidate_positions:
            add_weight, add_index = unselected_by_weight[candidate_position]
            candidate = realized - ordered[remove_index].weight + add_weight
            key = (abs(candidate - requested_change), remove_index, add_index)
            if best_key is None or key < best_key:
                best_key = key
                best_exchange = (remove_index, add_index)
    if best_key is None or best_key[0] >= current_error:
        return None
    return best_exchange


def _numeric_vector(
    values: Sequence[float] | np.ndarray,
    *,
    name: str,
    n: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(values)
    if raw.ndim != 1:
        raise ScheduleDJointReconciliationError(f"{name} must be one-dimensional.")
    if n is not None and len(raw) != n:
        raise ScheduleDJointReconciliationError(
            f"{name} must contain {n} rows; got {len(raw)}."
        )
    if raw.dtype.kind not in "iuf":
        raise ScheduleDJointReconciliationError(f"{name} must be a real numeric array.")
    numeric = raw.astype(np.float64, copy=False)
    if not np.isfinite(numeric).all():
        raise ScheduleDJointReconciliationError(
            f"{name} must contain only finite values."
        )
    return raw.copy(), numeric


def _weights(values: Sequence[float] | np.ndarray, *, n: int) -> np.ndarray:
    _, result = _numeric_vector(values, name="weights", n=n)
    if (result < 0.0).any():
        raise ScheduleDJointReconciliationError("weights must be nonnegative.")
    _checked_sum(result, name="weights")
    return result


def _boolean_vector(
    values: Sequence[bool] | np.ndarray,
    *,
    name: str,
    n: int,
) -> np.ndarray:
    result = np.asarray(values)
    if result.ndim != 1 or result.dtype.kind != "b":
        raise ScheduleDJointReconciliationError(
            f"{name} must be a one-dimensional boolean array."
        )
    if len(result) != n:
        raise ScheduleDJointReconciliationError(
            f"{name} must contain {n} rows; got {len(result)}."
        )
    return result.astype(bool, copy=False)


def _stable_id_keys(
    values: Sequence[object] | np.ndarray,
    *,
    n: int,
) -> tuple[tuple[str, object], ...]:
    array = np.asarray(values, dtype=object)
    if array.ndim != 1 or len(array) != n:
        raise ScheduleDJointReconciliationError(
            f"stable_ids must be one-dimensional with {n} rows."
        )
    keys: list[tuple[str, object]] = []
    seen: set[tuple[str, object]] = set()
    for position, raw in enumerate(array.tolist()):
        value = raw.item() if isinstance(raw, np.generic) else raw
        if isinstance(value, bool):
            raise ScheduleDJointReconciliationError(
                f"stable_ids contains boolean ID at position {position}."
            )
        if isinstance(value, (str, bytes)):
            if not value:
                raise ScheduleDJointReconciliationError(
                    f"stable_ids contains a missing ID at position {position}."
                )
            key: tuple[str, object] = (type(value).__name__, value)
        elif isinstance(value, Integral):
            key = ("number", int(value))
        elif isinstance(value, Real):
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ScheduleDJointReconciliationError(
                    f"stable_ids contains a missing ID at position {position}."
                )
            key = ("number", numeric)
        else:
            raise ScheduleDJointReconciliationError(
                "stable_ids must contain finite scalar strings, bytes, or numbers; "
                f"position {position} contains {value!r}."
            )
        if key in seen:
            raise ScheduleDJointReconciliationError(
                f"stable_ids contains duplicate ID {value!r}."
            )
        seen.add(key)
        keys.append(key)
    return tuple(keys)


def _target_weight(value: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ScheduleDJointReconciliationError(
            "target_schedule_d_positive_weight must be finite and nonnegative."
        ) from error
    if not math.isfinite(result) or result < 0.0:
        raise ScheduleDJointReconciliationError(
            "target_schedule_d_positive_weight must be finite and nonnegative."
        )
    return result


def _checked_sum(values: Iterable[float] | np.ndarray, *, name: str) -> float:
    try:
        result = math.fsum(sorted(float(value) for value in values))
    except OverflowError as error:
        raise ScheduleDJointReconciliationError(
            f"{name} must have a finite aggregate."
        ) from error
    if not math.isfinite(result):
        raise ScheduleDJointReconciliationError(f"{name} must have a finite aggregate.")
    return result


def _positive_multiset_equal(before: np.ndarray, after: np.ndarray) -> bool:
    return _byte_multiset(before[before > 0]) == _byte_multiset(after[after > 0])


def _byte_multiset(values: np.ndarray) -> tuple[bytes, ...]:
    contiguous = np.ascontiguousarray(values)
    return tuple(
        sorted(
            contiguous[index : index + 1].tobytes() for index in range(len(contiguous))
        )
    )


def _value_weight_multiset(
    values: np.ndarray,
    weights: np.ndarray,
) -> tuple[tuple[bytes, bytes], ...]:
    contiguous_values = np.ascontiguousarray(values)
    contiguous_weights = np.ascontiguousarray(weights, dtype=np.float64)
    return tuple(
        sorted(
            (
                contiguous_values[index : index + 1].tobytes(),
                contiguous_weights[index : index + 1].tobytes(),
            )
            for index in range(len(contiguous_values))
        )
    )


def _readonly_copy(values: np.ndarray) -> np.ndarray:
    result = np.ascontiguousarray(np.asarray(values)).copy()
    result.setflags(write=False)
    return result
