"""Synthetic-only contracts for exact monetary target bindings."""

import json
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest

from microcosm.build.ledger_targets import LedgerTargetReference
from microcosm.build.monetary_targets import (
    MonetaryBasis,
    bind_monetary_target,
    prepare_monetary_measure,
)
from microcosm.calibrate import TargetRegistry, build_constraint_matrix
from microcosm.calibrate.monetary_binding import MonetaryBindingIntegrityError
from microcosm.frame import EntitySchema, Frame, WeightKind, Weights


def _basis(**changes):
    return MonetaryBasis(
        **{
            "currency": "AMD",
            "unit": "base_currency",
            "period": "2024-12-31",
            "temporal_basis": "closing_stock",
            "sector": "S14",
            "perimeter": "resident household deposits",
            "valuation": "nominal",
            **changes,
        }
    )


def _prepared(values=(1.0, 2.0), **changes):
    return prepare_monetary_measure(
        values,
        **{
            "record_ids": np.arange(1, len(values) + 1),
            "basis": _basis(),
            "factor": 2.0,
            "source_identity_sha256": "a" * 64,
            "bridge_description": "Synthetic fixed common currency bridge, not target-derived.",
            "bridge_source_sha256": "b" * 64,
            **changes,
        },
    )


def _reference(**changes):
    return LedgerTargetReference(
        **{
            "name": "synthetic/deposits",
            "ledger_source_record_id": "synthetic.fact",
            "entity": "household",
            "measure": "deposits",
            "period": 2024,
            "family": "financial_assets",
            "source": "Synthetic source table",
            **changes,
        }
    )


def _bind(reference=None, **changes):
    return bind_monetary_target(
        reference or _reference(),
        **{
            "value": 6.0,
            "source_basis": _basis(),
            "source_assertion": "observation",
            "source_identity_sha256": "c" * 64,
            "prepared": _prepared(),
            **changes,
        },
    )


def test_binding_preserves_reference_and_receipts_without_fitting_values():
    reference = _reference(se=1, tolerance=0.1, notes="A proxy")
    result = _bind(reference, value=123)
    assert result.value == 123
    assert result.measure == "deposits"
    assert result.filter is None
    assert result.family == "financial_assets"
    assert result.period == 2024
    assert result.se == 1 and result.tolerance == 0.1
    binding = json.loads(result.metadata["monetary_binding"])
    assert binding["prepared"]["basis"]["period"] == "2024-12-31"
    assert binding["prepared"]["bridge"]["factor"] == 2
    assert binding["reference"]["ledger_source_record_id"] == "synthetic.fact"
    assert len(result.metadata["monetary_binding_sha256"]) == 64


def test_monetary_filter_is_rejected_instead_of_leaving_mask_unreceipted():
    with pytest.raises(ValueError, match="prepare the masked amount vector"):
        _bind(_reference(filter="included"))
    prepared = _prepared([1.0, 0.0])
    target = _bind(prepared=prepared, value=2)
    assert target.filter is None
    assert (
        json.loads(target.metadata["monetary_binding"])["prepared"]["values_sha256"]
        == prepared.values_sha256
    )


def test_prepare_copies_and_cannot_be_made_writable():
    values = np.array([1.0, -2.0])
    record_ids = np.array([11, 22])
    prepared = _prepared(values, record_ids=record_ids)
    values[:] = 100
    record_ids[:] = 0
    np.testing.assert_array_equal(prepared.values, [2, -4])
    np.testing.assert_array_equal(prepared.record_ids, [11, 22])
    with pytest.raises(ValueError):
        prepared.values[0] = 8
    with pytest.raises(ValueError):
        prepared.values.setflags(write=True)
    with pytest.raises(ValueError):
        prepared.record_ids[0] = 999
    with pytest.raises(ValueError):
        prepared.record_ids.setflags(write=True)
    with pytest.raises(FrozenInstanceError):
        prepared.factor = 3
    receipt = prepared.receipt()
    receipt["bridge"]["factor"] = 999
    assert prepared.receipt()["bridge"]["factor"] == 2


@pytest.mark.parametrize("array_name", ["values", "record_ids"])
@pytest.mark.parametrize("mutation", ["shape", "dtype"])
def test_numpy_metadata_mutation_fails_closed(array_name, mutation):
    prepared = _prepared()
    array = getattr(prepared, array_name)
    if mutation == "shape":
        array.shape = (2, 1)
    else:
        array.dtype = np.uint64
    for operation in (
        prepared.receipt,
        lambda: prepared.total([1, 1]),
        lambda: _bind(prepared=prepared),
    ):
        with pytest.raises(ValueError, match="metadata was mutated"):
            operation()


def test_signed_opt_in_cannot_be_a_truthy_string():
    with pytest.raises(ValueError, match="explicit boolean"):
        _bind(_reference(signed="false"), prepared=_prepared([-1, 2]))


@pytest.mark.parametrize(
    "change",
    [
        {"currency": "USD"},
        {"period": "2023-12-31"},
        {"sector": "S14+S15"},
        {"perimeter": "all financial assets"},
        {"valuation": "market"},
        {"temporal_basis": "annual_flow", "period": "2024"},
    ],
)
def test_each_valid_but_different_basis_is_rejected(change):
    with pytest.raises(ValueError, match="basis mismatch"):
        _bind(source_basis=_basis(**change))


@pytest.mark.parametrize(
    "change",
    [
        {"currency": "amd"},
        {"unit": "million_currency"},
        {"temporal_basis": "monthly_flow"},
        {"period": "2024"},
        {"period": "2024-12"},
        {"period": "2024-02-30"},
        {"temporal_basis": "annual_flow", "period": "2024-12"},
        {"temporal_basis": "annual_flow", "period": "2024-12-31"},
        {"temporal_basis": "annual_flow", "period": "0000"},
        {"period": 2024},
        {"sector": ""},
        {"perimeter": " "},
        {"valuation": ""},
    ],
)
def test_invalid_or_ambiguous_basis_is_rejected(change):
    with pytest.raises(ValueError):
        _basis(**change)


@pytest.mark.parametrize("values", [[np.nan], [np.inf], [-np.inf], [], [[1, 2]]])
def test_nonfinite_empty_or_multidimensional_amounts_are_rejected(values):
    with pytest.raises(ValueError, match="amounts"):
        _prepared(values)


@pytest.mark.parametrize("factor", [np.nan, np.inf, -np.inf, 0, -1, True])
def test_bad_factors_are_rejected(factor):
    with pytest.raises(ValueError, match="factor"):
        _prepared(factor=factor)


def test_factor_is_required_and_overflow_is_rejected():
    with pytest.raises(TypeError, match="factor"):
        prepare_monetary_measure(
            [1],
            record_ids=[1],
            basis=_basis(),
            source_identity_sha256="a" * 64,
            bridge_description="identity",
            bridge_source_sha256="b" * 64,
        )
    with pytest.raises(ValueError, match="transported amounts"):
        _prepared([np.finfo(float).max], factor=2)


def test_record_ids_are_required():
    with pytest.raises(TypeError, match="record_ids"):
        prepare_monetary_measure(
            [1],
            basis=_basis(),
            factor=1,
            source_identity_sha256="a" * 64,
            bridge_description="identity",
            bridge_source_sha256="b" * 64,
        )


@pytest.mark.parametrize(
    "record_ids",
    [
        None,
        [],
        [1],
        [[1, 2]],
        [1, 1],
        [1.0, 2.0],
        [1.5, 2],
        [True, False],
        ["1", "2"],
        [np.nan, 2],
        np.array([1, 2**63], dtype=np.uint64),
    ],
)
def test_invalid_or_misaligned_record_ids_are_rejected(record_ids):
    with pytest.raises(ValueError, match="record_ids"):
        _prepared(record_ids=record_ids)


@pytest.mark.parametrize(
    "weights", [[np.nan, 1], [np.inf, 1], [-1, 1], [1], [[1, 1]], []]
)
def test_bad_or_misaligned_weights_are_rejected(weights):
    with pytest.raises(ValueError, match="weights"):
        _prepared().total(weights)


def test_weighted_total_is_checked_and_finite():
    assert _prepared().total([3, 4]) == 22
    with pytest.raises(ValueError, match="total"):
        _prepared().total([np.finfo(float).max] * 2)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_targets_are_rejected(value):
    with pytest.raises(ValueError, match="Target amount"):
        _bind(value=value)


@pytest.mark.parametrize("field", ["se", "tolerance"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -1])
def test_bad_uncertainties_and_tolerances_are_rejected(field, value):
    with pytest.raises(ValueError):
        _bind(_reference(**{field: value}))


@pytest.mark.parametrize(
    "assertion", ["source_projection", "forecast", "model_output", ""]
)
def test_forecasts_never_bind_even_with_permissive_reference(assertion):
    with pytest.raises(ValueError, match="observation"):
        _bind(
            _reference(assertion_policy="allow_source_projection"),
            source_assertion=assertion,
        )


@pytest.mark.parametrize(
    "change", [{"readiness": "unbound"}, {"measure_kind": "policy_derived"}]
)
def test_unbound_or_policy_derived_measures_cannot_bind(change):
    with pytest.raises(ValueError, match="ready direct"):
        _bind(prepared=_prepared(**change))


@pytest.mark.parametrize(
    "status",
    [
        "requires_policy_output",
        "requires_coverage_bridge",
        "historical_validation_only",
        "requires_rules_engine",
    ],
)
def test_unready_reference_cannot_bind_ready_array(status):
    with pytest.raises(ValueError, match="activation_status"):
        _bind(_reference(metadata={"activation_status": status}))


@pytest.mark.parametrize(
    "assertion", ["observation", "observed", "derived_observation"]
)
def test_ready_measure_can_activate_prepared_measure_reference(assertion):
    reference = _reference(
        metadata={
            "activation_status": "requires_prepared_measure",
            "measure_kind": "prepared_column",
            "target_role": "calibration",
        }
    )
    assert _bind(reference, source_assertion=assertion).value == 6


def test_policy_kind_and_validation_role_cannot_be_spoofed_with_direct_array():
    with pytest.raises(ValueError, match="policy bridge"):
        _bind(_reference(metadata={"measure_kind": "policy_derived"}))
    with pytest.raises(ValueError, match="held out"):
        _bind(_reference(metadata={"target_role": "validation"}))


def test_count_times_mean_requires_separately_resolved_observation():
    reference = _reference(value_operation="count_x_mean")
    with pytest.raises(ValueError, match="derived_observation"):
        _bind(reference)
    assert _bind(reference, source_assertion="derived_observation", value=7).value == 7


@pytest.mark.parametrize(
    "change",
    [
        {"value_operation": "calendar_year_average"},
        {"uprating_index": "cpi"},
        {"uprating_from_period": 2023},
        {"uprating_to_period": 2024},
    ],
)
def test_no_implicit_time_or_value_transforms(change):
    with pytest.raises(ValueError, match="Implicit"):
        _bind(_reference(**change))


def test_reference_period_is_checked_without_discarding_stock_date():
    assert _bind(_reference(period="2024-12-31")).period == "2024-12-31"
    with pytest.raises(ValueError, match="Reference period"):
        _bind(_reference(period=2023))
    with pytest.raises(ValueError, match="Reference period"):
        _bind(_reference(period="2024-06-30"))


def test_annual_flow_binds_only_an_annual_flow_basis():
    basis = _basis(period="2024", temporal_basis="annual_flow")
    assert _bind(source_basis=basis, prepared=_prepared(basis=basis)).period == 2024


def test_zero_support_and_unsigned_negative_target_fail_closed():
    with pytest.raises(ValueError, match="same-sign"):
        _bind(prepared=_prepared([0, 0]))
    with pytest.raises(ValueError, match="same-sign"):
        _bind(_reference(signed=True), value=-1)
    with pytest.raises(ValueError, match="signed=True"):
        _bind(value=-1, prepared=_prepared([-1, 0]))
    with pytest.raises(ValueError, match="signed=True"):
        _bind(value=1, prepared=_prepared([-1, 3]))
    assert _bind(_reference(signed=True), value=-1, prepared=_prepared([-1, 0])).signed


@pytest.mark.parametrize("field", ["source_identity_sha256", "bridge_source_sha256"])
def test_missing_source_identity_is_rejected(field):
    with pytest.raises(ValueError, match="SHA-256"):
        _prepared(**{field: ""})
    with pytest.raises(ValueError, match="SHA-256"):
        _bind(source_identity_sha256="")


def test_receipts_bind_values_factor_source_and_measurement_mapping():
    baseline = _prepared().receipt()["receipt_sha256"]
    assert _prepared().receipt()["receipt_sha256"] == baseline
    for change in (
        {"factor": 3},
        {"source_identity_sha256": "d" * 64},
        {"bridge_source_sha256": "d" * 64},
        {"bridge_description": "Other bridge"},
    ):
        assert _prepared(**change).receipt()["receipt_sha256"] != baseline
    assert _prepared([2, 1]).receipt()["receipt_sha256"] != baseline
    assert _prepared(record_ids=[2, 1]).receipt()["receipt_sha256"] != baseline
    spec = _bind()
    assert (
        _bind(_reference(measure="different_column")).metadata[
            "monetary_binding_sha256"
        ]
        != spec.metadata["monetary_binding_sha256"]
    )
    assert (
        _bind(source_identity_sha256="d" * 64).metadata["monetary_binding_sha256"]
        != spec.metadata["monetary_binding_sha256"]
    )


def test_bound_target_compiles_through_existing_sparse_matrix_api():
    prepared = _prepared()
    schema = EntitySchema(group_entities=("household",))
    frame = Frame(
        {
            "person": pd.DataFrame(
                {"person_id": [1, 2], "person_household_id": [1, 2]}
            ),
            "household": pd.DataFrame(
                {"household_id": [1, 2], "deposits": prepared.values}
            ),
        },
        schema,
        {"household": Weights(np.array([3.0, 4.0]), WeightKind.DESIGN)},
    )
    registry = TargetRegistry([_bind(prepared=prepared)], country="synthetic")
    problem = build_constraint_matrix(frame, registry.to_target_set())
    assert not problem.skipped
    np.testing.assert_array_equal(problem.estimates(np.array([3.0, 4.0])), [22])
    np.testing.assert_array_equal(prepared.values, [2, 4])


def test_valid_prepared_person_amounts_fail_on_household_reduction_overflow():
    prepared = _prepared([1e308, 1e308], factor=1, record_ids=[11, 12])
    target = _bind(_reference(entity="person"), prepared=prepared)
    frame = Frame(
        {
            "person": pd.DataFrame(
                {
                    "person_id": [11, 12],
                    "person_household_id": [1, 1],
                    "deposits": prepared.values,
                }
            ),
            "household": pd.DataFrame({"household_id": [1]}),
        },
        EntitySchema(group_entities=("household",)),
        {"household": Weights(np.ones(1), WeightKind.DESIGN)},
    )
    registry = TargetRegistry([target], country="synthetic")
    with pytest.raises(MonetaryBindingIntegrityError, match="overflow"):
        build_constraint_matrix(frame, registry.to_target_set())


@pytest.mark.parametrize("period", [None, 2024, "2024-12-31"])
def test_reference_period_variants_compile_with_receipt(period):
    prepared = _prepared()
    frame = Frame(
        {
            "person": pd.DataFrame(
                {"person_id": [1, 2], "person_household_id": [1, 2]}
            ),
            "household": pd.DataFrame(
                {"household_id": [1, 2], "deposits": prepared.values}
            ),
        },
        EntitySchema(group_entities=("household",)),
        {"household": Weights(np.ones(2), WeightKind.DESIGN)},
    )
    registry = TargetRegistry([_bind(_reference(period=period))], country="synthetic")
    assert build_constraint_matrix(frame, registry.to_target_set()).n_targets == 1
