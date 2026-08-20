from __future__ import annotations

import numpy as np
import pytest

from microcosm.build.us_runtime.schedule_d_joint_reconciliation import (
    ScheduleDJointReconciliationError,
    reconcile_schedule_d_joint_parents,
)


def test_reroutes_only_equal_weight_direct_positive_values() -> None:
    long_term = np.asarray([100.0, 100.0, 0.0, 0.0])
    direct = np.asarray([0.0, 5.0, 7.0, 0.0])
    long_term_bytes = long_term.tobytes()
    direct_snapshot = direct.copy()

    result = reconcile_schedule_d_joint_parents(
        long_term,
        direct,
        [3.0, 2.0, 3.0, 1.0],
        [40, 20, 30, 10],
        mutable_non_schedule_d=[True, True, True, True],
        target_schedule_d_positive_weight=0.0,
    )

    assert result.long_term_values.tobytes() == long_term_bytes
    np.testing.assert_array_equal(result.non_schedule_d_values, [7.0, 5.0, 0.0, 0.0])
    np.testing.assert_array_equal(long_term, [100.0, 100.0, 0.0, 0.0])
    np.testing.assert_array_equal(direct, direct_snapshot)
    assert not result.long_term_values.flags.writeable
    assert not result.non_schedule_d_values.flags.writeable
    assert result.receipt.method == (
        "heuristic_equal_weight_swap_frontier_v2_not_globally_certified"
    )
    assert result.receipt.before_schedule_d_positive_weight == 3.0
    assert result.receipt.after_schedule_d_positive_weight == 0.0
    assert result.receipt.feasible_schedule_d_weight_min == 0.0
    assert result.receipt.feasible_schedule_d_weight_max == 3.0
    assert result.receipt.selected_swaps == 1
    assert result.receipt.changed_non_schedule_d_rows == 2
    assert result.receipt.positive_carrier_count_before == 2
    assert result.receipt.positive_carrier_count_after == 2
    assert result.receipt.long_term_byte_preserved
    assert result.receipt.positive_value_multiset_preserved
    assert result.receipt.mutable_value_weight_multiset_preserved
    assert result.receipt.weighted_direct_carrier_preserved
    assert result.receipt.weighted_positive_distribution_preserved
    assert result.receipt.direct_positive_weight_before == 5.0
    assert result.receipt.direct_positive_weight_after == 5.0


def test_interior_search_selects_closest_discrete_equal_weight_swaps() -> None:
    result = reconcile_schedule_d_joint_parents(
        [1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 5.0, 7.0, 9.0],
        [1.0, 3.0, 4.0, 1.0, 3.0, 4.0],
        ["a", "b", "c", "d", "e", "f"],
        mutable_non_schedule_d=[True] * 6,
        target_schedule_d_positive_weight=3.0,
    )

    np.testing.assert_array_equal(
        result.non_schedule_d_values,
        [5.0, 0.0, 9.0, 0.0, 7.0, 0.0],
    )
    assert result.receipt.selected_swaps == 2
    assert result.receipt.after_schedule_d_positive_weight == 3.0
    assert result.receipt.absolute_target_error_weight == 0.0
    assert result.receipt.absolute_projected_error_weight == 0.0
    assert result.receipt.absolute_projected_error_weight <= (
        result.receipt.maximum_available_swap_weight
    )
    assert result.receipt.direct_positive_weight_drift == 0.0


def test_exchange_repair_finds_exact_target_missed_by_greedy_prefix() -> None:
    swap_weights = np.asarray((8.0, 7.0, 6.0, 5.0))
    result = reconcile_schedule_d_joint_parents(
        np.concatenate((np.ones(4), np.zeros(4))),
        np.concatenate((np.zeros(4), np.arange(1.0, 5.0))),
        np.concatenate((swap_weights, swap_weights)),
        np.arange(8),
        mutable_non_schedule_d=np.ones(8, dtype=bool),
        # Initial Schedule-D mass is 26; decreasing it by 12 requires 7 + 5.
        target_schedule_d_positive_weight=14.0,
    )

    assert result.receipt.after_schedule_d_positive_weight == 14.0
    assert result.receipt.absolute_projected_error_weight == 0.0
    assert result.receipt.selected_swaps == 2
    assert result.receipt.weighted_direct_carrier_preserved


def test_zero_weight_negative_and_outside_mask_rows_are_immutable() -> None:
    long_term = np.asarray([10.0, -0.0, 10.0, 0.0, 10.0])
    direct = np.asarray([9.0, -4.0, 0.0, 7.0, 0.0])

    result = reconcile_schedule_d_joint_parents(
        long_term,
        direct,
        [1.0, 5.0, 2.0, 2.0, 0.0],
        [1, 2, 3, 4, 5],
        mutable_non_schedule_d=[False, True, True, True, True],
        target_schedule_d_positive_weight=0.0,
    )

    # Seven moves from row 4 to the equal-weight row 3.  Nine is outside
    # provenance, the negative value is signed immutable, and row 5 has no mass.
    np.testing.assert_array_equal(
        result.non_schedule_d_values,
        [9.0, -4.0, 7.0, 0.0, 0.0],
    )
    assert result.receipt.movable_rows == 2
    assert result.receipt.immutable_rows == 3
    assert result.receipt.zero_weight_rows_preserved == 1
    assert result.receipt.selected_swaps == 1
    assert result.receipt.after_schedule_d_positive_weight == 0.0


def test_reconciliation_is_invariant_to_row_order_under_stable_ids() -> None:
    long_term = np.asarray([100.0, 100.0, 0.0, 0.0])
    direct = np.asarray([0.0, 5.0, 7.0, 0.0])
    weights = np.asarray([3.0, 2.0, 3.0, 1.0])
    stable_ids = np.asarray([40, 20, 30, 10])
    mutable = np.ones(4, dtype=bool)
    original = reconcile_schedule_d_joint_parents(
        long_term,
        direct,
        weights,
        stable_ids,
        mutable_non_schedule_d=mutable,
        target_schedule_d_positive_weight=0.0,
    )

    order = np.asarray([2, 0, 3, 1])
    shuffled = reconcile_schedule_d_joint_parents(
        long_term[order],
        direct[order],
        weights[order],
        stable_ids[order],
        mutable_non_schedule_d=mutable[order],
        target_schedule_d_positive_weight=0.0,
    )

    original_by_id = dict(zip(stable_ids, original.non_schedule_d_values, strict=True))
    shuffled_by_id = dict(
        zip(stable_ids[order], shuffled.non_schedule_d_values, strict=True)
    )
    assert shuffled_by_id == original_by_id
    assert shuffled.receipt == original.receipt


def test_large_interior_search_is_scalable_and_row_order_invariant() -> None:
    pairs = 1_000
    long_term = np.concatenate((np.ones(pairs), np.zeros(pairs)))
    direct = np.concatenate((np.zeros(pairs), np.arange(1.0, pairs + 1.0)))
    weights = np.ones(pairs * 2)
    stable_ids = np.arange(pairs * 2)
    target_weight = 413.0

    result = reconcile_schedule_d_joint_parents(
        long_term,
        direct,
        weights,
        stable_ids,
        mutable_non_schedule_d=np.ones(len(weights), dtype=bool),
        target_schedule_d_positive_weight=target_weight,
    )
    assert result.receipt.available_decrease_swaps == pairs
    assert result.receipt.selected_swaps == pairs - int(target_weight)
    assert result.receipt.after_schedule_d_positive_weight == target_weight
    assert result.receipt.absolute_projected_error_weight == 0.0
    assert result.receipt.weighted_positive_distribution_preserved

    order = np.random.default_rng(578).permutation(len(weights))
    shuffled = reconcile_schedule_d_joint_parents(
        long_term[order],
        direct[order],
        weights[order],
        stable_ids[order],
        mutable_non_schedule_d=np.ones(len(weights), dtype=bool),
        target_schedule_d_positive_weight=target_weight,
    )
    assert dict(zip(stable_ids, result.non_schedule_d_values, strict=True)) == dict(
        zip(stable_ids[order], shuffled.non_schedule_d_values, strict=True)
    )
    assert shuffled.receipt == result.receipt


def test_unequal_weights_project_without_changing_weighted_parent_margin() -> None:
    result = reconcile_schedule_d_joint_parents(
        [1.0, 0.0],
        [0.0, 5.0],
        [2.0, 3.0],
        [1, 2],
        mutable_non_schedule_d=[True, True],
        target_schedule_d_positive_weight=0.0,
    )

    np.testing.assert_array_equal(result.non_schedule_d_values, [0.0, 5.0])
    assert result.receipt.feasible_schedule_d_weight_min == 2.0
    assert result.receipt.projected_schedule_d_positive_weight == 2.0
    assert result.receipt.absolute_target_error_weight == 2.0
    assert result.receipt.weighted_direct_carrier_preserved


def test_increase_direction_and_upper_projection_preserve_parent_distribution() -> None:
    arguments = {
        "long_term_values": [1.0, 1.0, 0.0],
        "non_schedule_d_values": [0.0, 7.0, 0.0],
        "weights": [2.0, 3.0, 3.0],
        "stable_ids": [1, 2, 3],
        "mutable_non_schedule_d": [True, True, True],
    }
    exact = reconcile_schedule_d_joint_parents(
        **arguments,
        target_schedule_d_positive_weight=5.0,
    )
    np.testing.assert_array_equal(exact.non_schedule_d_values, [0.0, 0.0, 7.0])
    assert exact.receipt.available_increase_swaps == 1
    assert exact.receipt.after_schedule_d_positive_weight == 5.0
    assert exact.receipt.weighted_positive_distribution_preserved

    projected = reconcile_schedule_d_joint_parents(
        **arguments,
        target_schedule_d_positive_weight=8.0,
    )
    assert projected.receipt.feasible_schedule_d_weight_max == 5.0
    assert projected.receipt.projected_schedule_d_positive_weight == 5.0
    assert projected.receipt.absolute_target_error_weight == 3.0


def test_finite_heterogeneous_weights_use_mask_based_capacity_arithmetic() -> None:
    huge = 1e16
    result = reconcile_schedule_d_joint_parents(
        [1.0, 1.0, 0.0],
        [0.0, 0.0, 9.0],
        [huge, 1.0, huge],
        [1, 2, 3],
        mutable_non_schedule_d=[True, True, True],
        target_schedule_d_positive_weight=1.0,
    )

    np.testing.assert_array_equal(result.non_schedule_d_values, [9.0, 0.0, 0.0])
    assert result.receipt.feasible_schedule_d_weight_min == 1.0
    assert result.receipt.after_schedule_d_positive_weight == 1.0
    assert result.receipt.absolute_target_error_weight == 0.0
    assert result.receipt.weighted_direct_carrier_preserved


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"weights": [1.0, -1.0]}, "weights must be nonnegative"),
        ({"weights": [1.0, np.nan]}, "weights must contain only finite"),
        ({"long_term_values": [1.0, np.inf]}, "long_term_values must contain"),
        ({"non_schedule_d_values": [0.0]}, "must contain 2 rows"),
        ({"stable_ids": [1, 1]}, "duplicate ID"),
        ({"stable_ids": [1, None]}, "finite scalar"),
        ({"mutable_non_schedule_d": [1, 0]}, "boolean array"),
        ({"target_schedule_d_positive_weight": -1.0}, "finite and nonnegative"),
    ],
)
def test_reconciliation_rejects_ambiguous_or_invalid_inputs(
    overrides: dict[str, object],
    match: str,
) -> None:
    arguments: dict[str, object] = {
        "long_term_values": [1.0, 0.0],
        "non_schedule_d_values": [0.0, 1.0],
        "weights": [1.0, 1.0],
        "stable_ids": [1, 2],
        "mutable_non_schedule_d": [True, True],
        "target_schedule_d_positive_weight": 0.5,
    }
    arguments.update(overrides)

    with pytest.raises(ScheduleDJointReconciliationError, match=match):
        reconcile_schedule_d_joint_parents(**arguments)


def test_zero_total_weight_is_not_an_incidence_population() -> None:
    with pytest.raises(
        ScheduleDJointReconciliationError,
        match="positive total recipient weight",
    ):
        reconcile_schedule_d_joint_parents(
            [1.0, 0.0],
            [0.0, 1.0],
            [0.0, 0.0],
            [1, 2],
            mutable_non_schedule_d=[True, True],
            target_schedule_d_positive_weight=0.5,
        )


def test_aggregate_weight_overflow_fails_closed() -> None:
    with pytest.raises(
        ScheduleDJointReconciliationError,
        match="weights must have a finite aggregate",
    ):
        reconcile_schedule_d_joint_parents(
            [1.0, 0.0],
            [0.0, 1.0],
            [np.finfo(np.float64).max, np.finfo(np.float64).max],
            [1, 2],
            mutable_non_schedule_d=[True, True],
            target_schedule_d_positive_weight=0.5,
        )
