from __future__ import annotations

import numpy as np
import pytest

from microcosm.build.us_runtime.acs_transfer_calibration import (
    SCHEDULE_D_JOINT_STATES,
    CalibrationCapacityError,
    allocate_schedule_d_joint_carriers,
    allocate_weighted_signs,
    map_sign_preserving_weighted_magnitudes,
    select_weighted_binary_carriers,
)


def test_binary_carrier_selection_is_stable_id_deterministic_and_read_only() -> None:
    ids = np.asarray((30, 10, 20, 40))
    weights = np.asarray((2.0, 1.0, 1.0, 0.0))
    scores = np.zeros(4)
    initial = np.asarray((False, False, False, True))

    result = select_weighted_binary_carriers(
        initial,
        scores,
        weights,
        ids,
        target_share=0.5,
    )

    # Equal scores break on stable ID, selecting IDs 10 and 20 for weight 2.
    assert dict(zip(ids, result.carriers, strict=True)) == {
        30: False,
        10: True,
        20: True,
        40: True,
    }
    assert result.receipt.realized_weight == (2.0, 2.0)
    assert result.receipt.allocation_error == (0.0, 0.0)
    assert result.receipt.zero_weight_rows_preserved == 1
    assert not result.carriers.flags.writeable

    permutation = np.asarray((2, 0, 3, 1))
    reordered = select_weighted_binary_carriers(
        initial[permutation],
        scores[permutation],
        weights[permutation],
        ids[permutation],
        target_share=0.5,
    )
    assert dict(zip(ids[permutation], reordered.carriers, strict=True)) == dict(
        zip(ids, result.carriers, strict=True)
    )


def test_binary_carrier_selection_receipts_immutable_capacity_projection() -> None:
    result = select_weighted_binary_carriers(
        np.asarray((True, False)),
        np.asarray((0.0, 1.0)),
        np.asarray((8.0, 2.0)),
        np.asarray((1, 2)),
        target_share=0.1,
        immutable=np.asarray((True, False)),
    )

    np.testing.assert_array_equal(result.carriers, (True, False))
    assert result.receipt.requested_weight == (9.0, 1.0)
    assert result.receipt.immutable_weight == (0.0, 8.0)
    assert result.receipt.capacity_lower == (0.0, 8.0)
    assert result.receipt.capacity_upper == (2.0, 10.0)
    assert result.receipt.projected_weight == (2.0, 8.0)
    assert result.receipt.projection_error == (-7.0, 7.0)
    assert result.receipt.maximum_absolute_projection_error == 7.0


def test_three_class_sign_allocation_separates_hurdle_from_amounts() -> None:
    values = np.asarray((-5.0, -1.0, 0.0, 1.0, 5.0, 99.0))
    weights = np.asarray((1.0, 1.0, 1.0, 1.0, 1.0, 0.0))
    result = allocate_weighted_signs(
        values,
        weights,
        np.arange(6),
        target_shares=(0.2, 0.4, 0.4),
    )

    np.testing.assert_array_equal(result.signs, (-1, 0, 0, 1, 1, 1))
    assert result.receipt.realized_weight == (1.0, 2.0, 2.0)
    assert result.receipt.requested_weight == (1.0, 2.0, 2.0)
    assert result.receipt.zero_weight_rows_preserved == 1
    assert result.receipt.changed_positive_weight_rows == 1
    assert not result.signs.flags.writeable


def test_sign_preserving_weighted_inverse_ecdf_maps_each_sign_conditionally() -> None:
    values = np.asarray((1.0, 2.0, 3.0, -1.0, -2.0, 9.0))
    weights = np.asarray((1.0, 1.0, 2.0, 1.0, 1.0, 0.0))
    reference_values = np.asarray((10.0, 20.0, -100.0, -200.0, 999.0))
    reference_weights = np.asarray((1.0, 3.0, 3.0, 1.0, 0.0))

    result = map_sign_preserving_weighted_magnitudes(
        values,
        weights,
        np.arange(6),
        reference_values,
        reference_weights,
        np.arange(100, 105),
    )

    np.testing.assert_array_equal(
        result.values, (10.0, 20.0, 20.0, -100.0, -100.0, 9.0)
    )
    np.testing.assert_array_equal(np.sign(result.values), np.sign(values))
    assert result.zero_weight_rows_preserved == 1
    assert [receipt.mapped_rows for receipt in result.conditional] == [2, 3]
    assert [receipt.reference_carrier_weight for receipt in result.conditional] == [
        4.0,
        4.0,
    ]
    assert not result.values.flags.writeable


def test_magnitude_mapping_preserves_explicit_immutable_rows() -> None:
    result = map_sign_preserving_weighted_magnitudes(
        (1.0, 2.0),
        (1.0, 1.0),
        (1, 2),
        (10.0,),
        (1.0,),
        (10,),
        immutable=np.asarray((True, False)),
    )

    np.testing.assert_array_equal(result.values, (1.0, 10.0))
    positive = result.conditional[1]
    assert positive.immutable_rows == 1
    assert positive.immutable_weight == 1.0
    assert positive.mapped_rows == 1


def test_immutable_carriers_constrain_final_domain_quantile_ranks() -> None:
    result = map_sign_preserving_weighted_magnitudes(
        (100.0, 1.0, 2.0),
        (1.0, 1.0, 1.0),
        (1, 2, 3),
        (10.0, 20.0, 30.0),
        (1.0, 1.0, 1.0),
        (10, 20, 30),
        immutable=np.asarray((True, False, False)),
    )

    # The fixed 100 occupies the upper recipient rank.  Ranking only the two
    # mutable rows would incorrectly map the second one to the donor maximum.
    np.testing.assert_array_equal(result.values, (100.0, 10.0, 20.0))
    assert result.conditional[1].recipient_carrier_weight == 3.0
    assert result.conditional[1].mapped_weight == 2.0
    assert result.conditional[1].immutable_weight == 1.0


def test_immutable_anchor_reserves_donor_mass_across_final_value_order() -> None:
    result = map_sign_preserving_weighted_magnitudes(
        (20.0, 1.0, 2.0),
        (1.0, 1.0, 1.0),
        (1, 2, 3),
        (10.0, 20.0, 30.0),
        (1.0, 1.0, 1.0),
        (10, 20, 30),
        immutable=np.asarray((True, False, False)),
    )

    # The fixed 20 reserves the middle donor mass.  Raw-rank mapping would
    # instead emit (20, 10, 20) and duplicate the middle of the final domain.
    np.testing.assert_array_equal(result.values, (20.0, 10.0, 30.0))
    positive = result.conditional[1]
    assert positive.maximum_fixed_cdf_excess_weight == 0.0
    assert positive.maximum_residual_cdf_adjustment_weight == 0.0


def test_magnitude_mapping_fails_without_matching_reference_sign_capacity() -> None:
    with pytest.raises(CalibrationCapacityError, match="negative reference support"):
        map_sign_preserving_weighted_magnitudes(
            (-1.0,),
            (1.0,),
            (1,),
            (10.0,),
            (1.0,),
            (2,),
        )


def test_schedule_d_joint_allocation_retains_all_four_states_including_overlap() -> (
    None
):
    result = allocate_schedule_d_joint_carriers(
        (1.0, 1.0, -1.0, -1.0, 100.0),
        (1.0, -1.0, 1.0, -1.0, 100.0),
        (1.0, 1.0, 1.0, 1.0, 0.0),
        (4, 2, 3, 1, 5),
        target_state_shares=(0.25, 0.25, 0.25, 0.25),
    )

    assert result.receipt.class_labels == SCHEDULE_D_JOINT_STATES
    assert result.receipt.realized_weight == (1.0, 1.0, 1.0, 1.0)
    np.testing.assert_array_equal(result.states, (3, 1, 2, 0, 3))
    np.testing.assert_array_equal(
        result.schedule_d_parent_positive,
        (True, True, False, False, True),
    )
    np.testing.assert_array_equal(
        result.non_schedule_d_parent_positive,
        (True, False, True, False, True),
    )
    assert result.receipt.zero_weight_rows_preserved == 1
    assert not result.states.flags.writeable


@pytest.mark.parametrize("bad_weights", ((1.0, -1.0), (1.0, np.nan), (1.0, np.inf)))
def test_allocators_fail_closed_on_invalid_weights(
    bad_weights: tuple[float, float],
) -> None:
    with pytest.raises(ValueError, match="weights"):
        select_weighted_binary_carriers(
            np.asarray((False, True)),
            (0.0, 1.0),
            bad_weights,
            (1, 2),
            target_share=0.5,
        )


@pytest.mark.parametrize(
    ("ids", "message"),
    (
        ((1, 1), "duplicate ID"),
        ((1, None), "missing ID"),
        ((1, np.nan), "missing ID"),
    ),
)
def test_allocators_fail_closed_on_duplicate_or_missing_stable_ids(
    ids: tuple[object, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        allocate_weighted_signs(
            (-1.0, 1.0),
            (1.0, 1.0),
            ids,
            target_shares=(0.5, 0.0, 0.5),
        )


def test_magnitude_mapping_validates_reference_ids_even_for_zero_weight_rows() -> None:
    with pytest.raises(ValueError, match="reference_stable_ids.*duplicate ID"):
        map_sign_preserving_weighted_magnitudes(
            (1.0,),
            (1.0,),
            (1,),
            (10.0, 99.0),
            (1.0, 0.0),
            (2, 2),
        )


def test_allocators_fail_closed_on_aggregate_weight_overflow() -> None:
    maximum = np.finfo(np.float64).max
    with pytest.raises(ValueError, match="weights must have a finite aggregate"):
        select_weighted_binary_carriers(
            (False, True),
            (0.0, 1.0),
            (maximum, maximum),
            (1, 2),
            target_share=0.5,
        )


def test_binary_allocation_receipt_is_stable_for_awkward_weight_order() -> None:
    weights = np.asarray((1e16, 1.0, 1.0, 2.0))
    stable_ids = np.asarray((40, 10, 20, 30))
    initial = np.asarray((False, False, True, True))
    scores = np.asarray((0.0, 3.0, 2.0, 1.0))
    original = select_weighted_binary_carriers(
        initial,
        scores,
        weights,
        stable_ids,
        target_share=0.5,
    )

    order = np.asarray((2, 0, 3, 1))
    shuffled = select_weighted_binary_carriers(
        initial[order],
        scores[order],
        weights[order],
        stable_ids[order],
        target_share=0.5,
    )

    assert dict(zip(stable_ids, original.carriers, strict=True)) == dict(
        zip(stable_ids[order], shuffled.carriers, strict=True)
    )
    assert shuffled.receipt == original.receipt
