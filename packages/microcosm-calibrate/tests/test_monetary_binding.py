"""Synthetic compiler receipt contracts, without a build/country dependency."""

import hashlib
import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from microcosm.calibrate import Target, TargetSet, build_constraint_matrix
from microcosm.calibrate.monetary_binding import (
    MonetaryBindingIntegrityError,
    monetary_digest,
)
from microcosm.frame import EntitySchema, Frame, WeightKind, Weights


def _frame(values=(2.0, 4.0), ids=(1, 2), *, measure="deposits", entity="household"):
    person_ids = np.arange(11, 11 + len(ids))
    return Frame(
        {
            "person": pd.DataFrame(
                {
                    "person_id": person_ids,
                    "person_household_id": ids,
                    **({measure: values} if entity == "person" else {}),
                }
            ),
            "household": pd.DataFrame(
                {
                    "household_id": ids,
                    **({measure: values} if entity == "household" else {}),
                }
            ),
        },
        EntitySchema(group_entities=("household",)),
        {"household": Weights(np.ones(len(ids)), WeightKind.DESIGN)},
    )


def _reseal(target, binding, *, nested=True):
    if nested:
        prepared = binding["prepared"]
        prepared["bridge_sha256"] = monetary_digest(prepared["bridge"])
        prepared["receipt_sha256"] = monetary_digest(
            {key: value for key, value in prepared.items() if key != "receipt_sha256"}
        )
    return replace(
        target,
        metadata={
            **target.metadata,
            "monetary_binding": json.dumps(binding),
            "monetary_binding_sha256": monetary_digest(binding),
        },
    )


def _target(values=(2.0, 4.0), ids=(1, 2), **changes):
    target = Target(
        **{
            "name": "synthetic/deposits",
            "entity": "household",
            "measure": "deposits",
            "value": 6.0,
            "period": 2024,
            "source": "Synthetic observation",
            **changes,
        }
    )
    binding = {
        "reference": {
            key: getattr(target, key)
            for key in ("name", "entity", "measure", "period", "filter", "metadata")
        },
        "value": target.value,
        "source": target.source,
        "source_assertion": "observed",
        "source_identity_sha256": "a" * 64,
        "prepared": {
            "schema_version": 2,
            "basis": {
                "currency": "AMD",
                "unit": "base_currency",
                "period": "2024-12-31",
                "temporal_basis": "closing_stock",
                "sector": "S14",
                "perimeter": "resident deposits",
                "valuation": "nominal",
            },
            "n_records": len(values),
            "source_identity_sha256": "b" * 64,
            "source_values_sha256": "c" * 64,
            "values_sha256": hashlib.sha256(
                np.asarray(values, dtype="<f8").tobytes()
            ).hexdigest(),
            "record_ids_sha256": hashlib.sha256(
                np.asarray(ids, dtype="<i8").tobytes()
            ).hexdigest(),
            "bridge": {
                "factor": 2.0,
                "description": "Synthetic bridge",
                "source_sha256": "d" * 64,
            },
            "readiness": "ready",
            "measure_kind": "direct",
        },
    }
    return _reseal(target, binding)


def _compile(frame=None, target=None):
    return build_constraint_matrix(
        frame if frame is not None else _frame(),
        TargetSet((target if target is not None else _target(),)),
    )


def test_matching_receipt_compiles_without_build_dependency():
    problem = _compile()
    assert problem.n_targets == 1 and not problem.skipped
    np.testing.assert_array_equal(problem.matrix.toarray(), [[2, 4]])


def test_receipted_filter_is_rejected_even_when_reference_and_hashes_match():
    with pytest.raises(
        MonetaryBindingIntegrityError, match="prepare the masked amount vector"
    ):
        _compile(target=_target(filter="included"))
    # A pre-masked amount vector has its actual contribution frozen in the receipt.
    problem = _compile(_frame(values=(2, 0)), _target(values=(2, 0), value=2))
    np.testing.assert_array_equal(problem.matrix.toarray(), [[2, 0]])


def test_receipt_is_checked_on_source_entity_before_household_collapse():
    problem = _compile(
        frame=_frame(entity="person"), target=_target(entity="person", ids=(11, 12))
    )
    np.testing.assert_array_equal(problem.matrix.toarray(), [[2, 4]])


@pytest.mark.parametrize(
    "frame",
    [
        _frame(values=(200, 400)),
        _frame(values=(4, 2)),
        _frame(values=(np.nan, 4)),
        _frame(values=(np.inf, 4)),
        _frame(values=(2,), ids=(1,)),
        _frame(ids=(101, 102)),
        _frame(measure="different_column"),
    ],
)
def test_changed_frame_refuses_whole_compilation(frame):
    with pytest.raises(MonetaryBindingIntegrityError):
        _compile(frame=frame)


def test_equal_values_do_not_hide_reordered_entity_ids():
    with pytest.raises(MonetaryBindingIntegrityError, match="IDs/order"):
        _compile(_frame(values=(2, 2)), _target(values=(2, 2), ids=(2, 1)))


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "other"},
        {"entity": "person"},
        {"entity": "absent_entity"},
        {"measure": "other"},
        {"measure": lambda frame: np.ones(2)},
        {"period": 2025},
        {"period": "2024"},
        {"value": 123},
        {"filter": "other"},
        {"source": "other"},
    ],
)
def test_changed_target_fields_refuse_compilation(changes):
    with pytest.raises(MonetaryBindingIntegrityError):
        _compile(target=replace(_target(), **changes))


@pytest.mark.parametrize("missing", ["monetary_binding", "monetary_binding_sha256"])
def test_partial_opt_in_is_not_treated_as_an_ordinary_target(missing):
    target = _target()
    metadata = dict(target.metadata)
    del metadata[missing]
    with pytest.raises(MonetaryBindingIntegrityError):
        _compile(target=replace(target, metadata=metadata))


@pytest.mark.parametrize(
    "json_value", ["not JSON", "null", "[]", "{}", '{"value": NaN}']
)
def test_malformed_binding_refuses_compilation(json_value):
    target = _target()
    with pytest.raises(MonetaryBindingIntegrityError):
        _compile(
            target=replace(
                target, metadata={**target.metadata, "monetary_binding": json_value}
            )
        )


@pytest.mark.parametrize(
    "missing",
    [
        "schema_version",
        "basis",
        "n_records",
        "source_identity_sha256",
        "source_values_sha256",
        "values_sha256",
        "record_ids_sha256",
        "bridge",
        "bridge_sha256",
        "readiness",
        "measure_kind",
        "receipt_sha256",
    ],
)
def test_incomplete_receipt_fails_even_when_outer_hash_is_updated(missing):
    target = _target()
    binding = json.loads(target.metadata["monetary_binding"])
    del binding["prepared"][missing]
    with pytest.raises(MonetaryBindingIntegrityError):
        _compile(target=_reseal(target, binding, nested=False))


@pytest.mark.parametrize(
    "field", ["value", "source_assertion", "source_identity_sha256"]
)
def test_modified_binding_fails_without_resealing(field):
    target = _target()
    binding = json.loads(target.metadata["monetary_binding"])
    binding[field] = "altered"
    metadata = {**target.metadata, "monetary_binding": json.dumps(binding)}
    with pytest.raises(MonetaryBindingIntegrityError, match="binding hash"):
        _compile(target=replace(target, metadata=metadata))


def test_inner_receipt_hash_is_checked_independently():
    target = _target()
    binding = json.loads(target.metadata["monetary_binding"])
    binding["prepared"]["n_records"] = 99
    with pytest.raises(MonetaryBindingIntegrityError, match="receipt hash"):
        _compile(target=_reseal(target, binding, nested=False))


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": 1},
        {"readiness": "unbound"},
        {"measure_kind": "policy_derived"},
        {"n_records": 99},
        {"n_records": True},
        {"values_sha256": "e" * 64},
        {"record_ids_sha256": "e" * 64},
        {"source_values_sha256": "not a hash"},
    ],
)
def test_invalid_or_mismatched_prepared_receipt_fails_even_when_resealed(changes):
    target = _target()
    binding = json.loads(target.metadata["monetary_binding"])
    binding["prepared"].update(changes)
    with pytest.raises(MonetaryBindingIntegrityError):
        _compile(target=_reseal(target, binding))


def test_forecast_and_unready_metadata_cannot_activate_receipt():
    target = _target()
    binding = json.loads(target.metadata["monetary_binding"])
    binding["source_assertion"] = "forecast"
    with pytest.raises(MonetaryBindingIntegrityError, match="observation"):
        _compile(target=_reseal(target, binding))
    with pytest.raises(MonetaryBindingIntegrityError, match="ready/direct"):
        _compile(
            target=_target(metadata={"activation_status": "requires_policy_output"})
        )


def test_metadata_cannot_diverge_from_receipted_reference():
    target = _target()
    with pytest.raises(MonetaryBindingIntegrityError, match="metadata differs"):
        _compile(
            target=replace(
                target,
                metadata={
                    **target.metadata,
                    "activation_status": "requires_policy_output",
                },
            )
        )


def test_integrity_failure_precedes_the_skippable_entity_row_path(monkeypatch):
    import microcosm.calibrate.matrix as matrix_module

    def must_not_run(*args, **kwargs):
        pytest.fail("stale monetary receipt reached the skippable compiler path")

    monkeypatch.setattr(matrix_module, "_entity_row", must_not_run)
    with pytest.raises(MonetaryBindingIntegrityError):
        _compile(frame=_frame(values=(200, 400)))


@pytest.mark.parametrize(
    "error_type", [KeyError, ValueError, TypeError, FloatingPointError, RuntimeError]
)
def test_receipted_entity_row_exceptions_are_fatal(monkeypatch, error_type):
    import microcosm.calibrate.matrix as matrix_module

    original = matrix_module._entity_row

    def broken_row(target, frame, weight_entity):
        if target.name == "synthetic/deposits":
            raise error_type("synthetic row failure")
        return original(target, frame, weight_entity)

    monkeypatch.setattr(matrix_module, "_entity_row", broken_row)
    ordinary = replace(_target(), name="ordinary", metadata={})
    with pytest.raises(
        MonetaryBindingIntegrityError, match="compilation failed"
    ) as caught:
        build_constraint_matrix(_frame(), TargetSet((ordinary, _target())))
    assert isinstance(caught.value.__cause__, error_type)


@pytest.mark.parametrize(
    "row",
    [
        None,
        [2, 4],
        np.array([2.0]),
        np.ones((2, 1)),
        np.array([np.nan, 4]),
        np.array([np.inf, 4]),
        np.array(["bad", "row"]),
    ],
)
def test_receipted_malformed_length_or_nonfinite_rows_are_fatal(monkeypatch, row):
    import microcosm.calibrate.matrix as matrix_module

    original = matrix_module._entity_row

    def broken_row(target, frame, weight_entity):
        return (
            row
            if target.name == "synthetic/deposits"
            else original(target, frame, weight_entity)
        )

    monkeypatch.setattr(matrix_module, "_entity_row", broken_row)
    ordinary = replace(_target(), name="ordinary", metadata={})
    with pytest.raises(MonetaryBindingIntegrityError, match="compilation failed"):
        build_constraint_matrix(_frame(), TargetSet((ordinary, _target())))


def test_receipted_person_reduction_overflow_is_fatal_but_ordinary_row_is_skipped():
    frame = Frame(
        {
            "person": pd.DataFrame(
                {
                    "person_id": [11, 12],
                    "person_household_id": [1, 1],
                    "deposits": [1e308, 1e308],
                }
            ),
            "household": pd.DataFrame({"household_id": [1], "count": [1.0]}),
        },
        EntitySchema(group_entities=("household",)),
        {"household": Weights(np.ones(1), WeightKind.DESIGN)},
    )
    monetary = _target(values=(1e308, 1e308), ids=(11, 12), entity="person")
    count = Target(name="count", entity="household", measure="count", value=1)
    with pytest.raises(MonetaryBindingIntegrityError, match="overflow"):
        build_constraint_matrix(frame, TargetSet((count, monetary)))
    ordinary = replace(monetary, name="ordinary", metadata={})
    with np.errstate(over="ignore"):
        problem = build_constraint_matrix(frame, TargetSet((count, ordinary)))
    assert problem.n_targets == 1
    assert [item.target.name for item in problem.skipped] == ["ordinary"]
    assert "non-finite" in problem.skipped[0].reason


def test_non_nested_receipted_entity_cannot_be_skipped():
    frame = Frame(
        {
            "person": pd.DataFrame(
                {
                    "person_id": [11, 12],
                    "person_household_id": [1, 2],
                    "person_tax_unit_id": [10, 10],
                }
            ),
            "household": pd.DataFrame({"household_id": [1, 2], "count": [1.0, 1.0]}),
            "tax_unit": pd.DataFrame({"tax_unit_id": [10], "deposits": [2.0]}),
        },
        EntitySchema(group_entities=("household", "tax_unit")),
        {"household": Weights(np.ones(2), WeightKind.DESIGN)},
    )
    monetary = _target(values=(2,), ids=(10,), entity="tax_unit")
    count = Target(name="count", entity="household", measure="count", value=2)
    with pytest.raises(MonetaryBindingIntegrityError, match="span multiple"):
        build_constraint_matrix(frame, TargetSet((count, monetary)))
    ordinary = replace(monetary, name="ordinary", metadata={})
    problem = build_constraint_matrix(frame, TargetSet((count, ordinary)))
    assert problem.n_targets == 1
    assert [item.target.name for item in problem.skipped] == ["ordinary"]


@pytest.mark.parametrize(
    "row",
    [np.array([2.0]), np.ones((2, 1)), np.array([np.nan, 4]), np.array([np.inf, 4])],
)
def test_ordinary_wrong_length_and_nonfinite_rows_still_skip(monkeypatch, row):
    import microcosm.calibrate.matrix as matrix_module

    original = matrix_module._entity_row

    def broken_row(target, frame, weight_entity):
        return (
            row if target.name == "invalid" else original(target, frame, weight_entity)
        )

    monkeypatch.setattr(matrix_module, "_entity_row", broken_row)
    ordinary = replace(_target(), name="ordinary", metadata={})
    problem = build_constraint_matrix(
        _frame(), TargetSet((ordinary, replace(ordinary, name="invalid")))
    )
    assert problem.n_targets == 1
    assert [item.target.name for item in problem.skipped] == ["invalid"]


def test_ordinary_targets_keep_existing_compile_and_skip_behavior():
    valid = Target(
        name="ordinary",
        entity="household",
        measure="deposits",
        value=6,
        metadata={"note": "ordinary"},
    )
    missing = replace(valid, name="missing", measure="absent")
    problem = build_constraint_matrix(_frame(), TargetSet((valid, missing)))
    assert problem.n_targets == 1
    assert [item.target.name for item in problem.skipped] == ["missing"]
    with pytest.raises(MonetaryBindingIntegrityError):
        build_constraint_matrix(
            _frame(values=(200, 400)), TargetSet((valid, _target()))
        )
