"""Authenticated boundary from Axiom policy outputs to monetary calibration."""

from __future__ import annotations

import json
from dataclasses import replace
from hashlib import sha256

import numpy as np
import pandas as pd
import pytest

from microcosm.build.ledger_targets import LedgerTargetReference
from microcosm.build.monetary_targets import MonetaryBasis
from microcosm.build.policy_monetary_targets import (
    AxiomPolicyIdentity,
    PolicyDerivedMonetaryMeasure,
    bind_policy_derived_monetary_target,
    prepare_policy_derived_monetary_measure,
)
from microcosm.calibrate import TargetRegistry, TargetSet, build_constraint_matrix
from microcosm.calibrate.monetary_binding import (
    MonetaryBindingIntegrityError,
    monetary_digest,
)
from microcosm.calibrate.policy_monetary_binding import AxiomPolicyAcceptance
from microcosm.frame import EntitySchema, Frame, WeightKind, Weights


def _basis(**changes) -> MonetaryBasis:
    fields = {
        "currency": "AMD",
        "unit": "base_currency",
        "period": "2024",
        "temporal_basis": "annual_flow",
        "sector": "S14",
        "perimeter": "resident households within the PIT filing perimeter",
        "valuation": "cash liability",
    }
    return MonetaryBasis(**(fields | changes))


def _axiom_array_identity(values) -> dict[str, object]:
    """Mirror the public schema-v2 numeric-vector receipt contract."""
    array = np.asarray(values)
    dtype = array.dtype.newbyteorder("<")
    canonical = np.ascontiguousarray(array.astype(dtype, copy=False))
    header = {
        "dtype": array.dtype.name,
        "storage_dtype": canonical.dtype.str,
        "encoding": "little_endian_raw_v1",
        "shape": list(array.shape),
    }
    payload = json.dumps(
        header,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return {
        **header,
        "sha256": sha256(payload + b"\n" + canonical.tobytes()).hexdigest(),
    }


def _materialization_receipt(**changes) -> dict[str, object]:
    frame = _frame()
    period = {
        "kind": "calendar_year",
        "start": "2024-01-01",
        "end": "2024-12-31",
    }
    person = frame.table("person")
    entity = {
        "frame_entity": "person",
        "engine_entity": "Person",
        "current_id_column": "person_id",
        "current_ids": _axiom_array_identity(person["person_id"].to_numpy()),
        "declared_root_inputs": [],
        "provided_root_inputs": {},
        "relations": {},
        "requested_outputs": {
            "armenia_personal_income_tax": {
                "declared_engine_dtype": "Decimal",
                "declared_kernel_dtype": "float",
                "declared_period": "year",
                "values": _axiom_array_identity(
                    person["armenia_personal_income_tax"].to_numpy()
                ),
            }
        },
    }
    input_projection = {
        "schema_version": 2,
        "receipt_kind": "axiom_dense_input_projection",
        "period": period,
        "arithmetic": "decimal",
        "entities": {
            "person": {
                key: value
                for key, value in entity.items()
                if key != "requested_outputs"
            }
        },
    }
    raw = {
        "schema_version": 2,
        "receipt_kind": "axiom_dense_materialization",
        "period": period,
        "arithmetic": "decimal",
        "entities": {"person": entity},
        "input_frame_sha256": monetary_digest(input_projection),
    } | changes
    return {**raw, "receipt_sha256": monetary_digest(raw)}


def _identity(**changes) -> AxiomPolicyIdentity:
    materialization = _materialization_receipt()
    fields = {
        "producer_manifest_sha256": "9" * 64,
        "rulespec_artifact_sha256": "a" * 64,
        "axiom_runtime_sha256": "b" * 64,
        "input_frame_sha256": materialization["input_frame_sha256"],
        "parameter_world_sha256": "d" * 64,
        "materialization_receipt_sha256": materialization["receipt_sha256"],
        "period": "2024",
        "output_variable": "armenia_personal_income_tax",
        "output_entity": "person",
        "target_entity": "household",
        "target_measure": "household_armenia_personal_income_tax",
    }
    return AxiomPolicyIdentity(**(fields | changes))


def _prepared(**changes):
    materialization = _materialization_receipt()
    fields = {
        "output_values": np.array([100.0, 200.0, 300.0]),
        "output_record_ids": np.array([11, 12, 13]),
        "target_record_ids": np.array([1, 2]),
        "output_target_ids": np.array([1, 1, 2]),
        "aggregation_membership_column": "person_household_id",
        "basis": _basis(),
        "identity": _identity(),
        "materialization_receipt": materialization,
        "perimeter_bridge_description": (
            "Axiom person PIT is summed to household rows; the observed State "
            "Revenue Committee aggregate uses the same resident PIT perimeter."
        ),
        "perimeter_bridge_source_sha256": "e" * 64,
    }
    return prepare_policy_derived_monetary_measure(**(fields | changes))


def _reference(**changes) -> LedgerTargetReference:
    fields = {
        "name": "src/personal_income_tax",
        "ledger_source_record_id": "am.src.pit.2024",
        "entity": "household",
        "measure": "household_armenia_personal_income_tax",
        "period": 2024,
        "family": "tax",
        "source": "Armenia SRC 2024 PIT aggregate",
        "period_match_policy": "exact",
        "metadata": {
            "monetary_target_role": "calibration",
            "measure_kind": "policy_derived",
            "activation_status": "requires_policy_output",
        },
    }
    return LedgerTargetReference(**(fields | changes))


def _bind(**changes):
    fields = {
        "value": 650_077_932_447,
        "observed_basis": _basis(),
        "observed_source_assertion": "observation",
        "observed_source_identity_sha256": "f" * 64,
        "prepared": _prepared(),
    }
    return bind_policy_derived_monetary_target(_reference(), **(fields | changes))


def _acceptance(spec) -> AxiomPolicyAcceptance:
    binding = json.loads(spec.metadata["policy_monetary_binding"])
    identity = binding["prepared"]["identity"]
    return AxiomPolicyAcceptance(
        binding_sha256=spec.metadata["policy_monetary_binding_sha256"],
        prepared_receipt_sha256=binding["prepared"]["receipt_sha256"],
        producer_manifest_sha256=identity["producer_manifest_sha256"],
        rulespec_artifact_sha256=identity["rulespec_artifact_sha256"],
        axiom_runtime_sha256=identity["axiom_runtime_sha256"],
        input_frame_sha256=identity["input_frame_sha256"],
        parameter_world_sha256=identity["parameter_world_sha256"],
        materialization_receipt_sha256=identity["materialization_receipt_sha256"],
        observed_source_identity_sha256=binding["observed_source_identity_sha256"],
    )


def _compile(frame=None, spec=None):
    spec = spec or _bind()
    target_set = TargetRegistry([spec], country="am").to_target_set()
    target = target_set.targets[0]
    return build_constraint_matrix(
        frame or _frame(),
        target_set,
        policy_acceptances={target.row_name: _acceptance(spec)},
    )


def _frame(values=(300.0, 300.0)) -> Frame:
    return Frame(
        {
            "person": pd.DataFrame(
                {
                    "person_id": [11, 12, 13],
                    "person_household_id": [1, 1, 2],
                    "armenia_personal_income_tax": [100.0, 200.0, 300.0],
                }
            ),
            "household": pd.DataFrame(
                {
                    "household_id": [1, 2],
                    "household_armenia_personal_income_tax": list(values),
                }
            ),
        },
        EntitySchema(group_entities=("household",)),
        {"household": Weights(np.array([2.0, 1.0]), WeightKind.DESIGN)},
    )


def test_person_outputs_sum_to_exact_household_order_with_full_identity_receipt():
    prepared = _prepared()
    np.testing.assert_array_equal(prepared.values, [300.0, 300.0])
    receipt = prepared.receipt()
    assert receipt["identity"]["rulespec_artifact_sha256"] == "a" * 64
    assert receipt["identity"]["axiom_runtime_sha256"] == "b" * 64
    assert receipt["identity"]["input_frame_sha256"] == receipt["materialization"][
        "input_frame_sha256"
    ]
    assert receipt["identity"]["parameter_world_sha256"] == "d" * 64
    assert receipt["output"]["n_records"] == 3
    assert receipt["output"]["values"]["dtype"] == "<f8"
    assert receipt["aggregation"]["kind"] == "sum_by_membership"
    assert receipt["aggregation"]["target_n_records"] == 2
    assert receipt["measure_kind"] == "policy_derived"
    assert len(receipt["receipt_sha256"]) == 64


def test_same_entity_output_requires_identical_rows_and_no_mapping():
    identity = _identity(output_entity="household")
    prepared = _prepared(
        output_values=np.array([10.0, 20.0]),
        output_record_ids=[1, 2],
        output_target_ids=None,
        aggregation_membership_column=None,
        identity=identity,
    )
    assert prepared.receipt()["aggregation"]["kind"] == "identity"
    with pytest.raises(ValueError, match="must not supply"):
        _prepared(
            output_values=np.array([10.0, 20.0]),
            output_record_ids=[1, 2],
            output_target_ids=[1, 2],
            identity=identity,
        )


def test_cross_entity_mapping_rejects_unknown_target_ids():
    with pytest.raises(ValueError, match="absent from the target table"):
        _prepared(output_target_ids=[1, 1, 99])


@pytest.mark.parametrize(
    "values",
    (
        [100.0, 200.0, 300.0],
        np.array([True, False, True]),
        np.array([100, 200, 300], dtype=np.int64),
        np.array(["100", "200", "300"]),
    ),
)
def test_policy_outputs_require_native_float64_without_lossy_coercion(values):
    with pytest.raises(TypeError, match="native numpy float64"):
        _prepared(output_values=values)


def test_direct_measure_construction_derives_and_checks_aggregation_proof():
    fields = {
        "output_values": np.array([100.0, 200.0, 300.0]),
        "output_record_ids": np.array([11, 12, 13]),
        "target_record_ids": np.array([1, 2]),
        "output_target_ids": np.array([1, 1, 99]),
        "basis": _basis(),
        "identity": _identity(),
        "aggregation_membership_column": "person_household_id",
        "materialization_receipt": _materialization_receipt(),
        "perimeter_bridge_description": "Explicit person-to-household bridge.",
        "perimeter_bridge_source_sha256": "e" * 64,
    }
    with pytest.raises(ValueError, match="absent from the target table"):
        PolicyDerivedMonetaryMeasure(**fields)


def test_policy_binding_carries_observation_and_derivation_separately():
    target = _bind()
    binding = json.loads(target.metadata["policy_monetary_binding"])
    assert binding["observed_value"] == 650_077_932_447
    assert binding["observed_source_identity_sha256"] == "f" * 64
    assert binding["prepared"]["identity"]["rulespec_artifact_sha256"] == "a" * 64
    assert binding["prepared"]["output"]["n_records"] == 3
    assert target.metadata["activation_status"] == "active"
    assert (
        target.metadata["monetary_source_activation_status"] == "requires_policy_output"
    )


def test_policy_bound_target_compiles_only_against_exact_receipted_column():
    problem = _compile()
    np.testing.assert_array_equal(problem.estimates(np.array([2.0, 1.0])), [900.0])
    with pytest.raises(MonetaryBindingIntegrityError, match="values differ"):
        _compile(frame=_frame(values=(301.0, 299.0)))


def test_policy_target_requires_independent_acceptance():
    target_set = TargetRegistry([_bind()], country="am").to_target_set()
    with pytest.raises(MonetaryBindingIntegrityError, match="independent"):
        build_constraint_matrix(_frame(), target_set)


def test_policy_receipt_stripping_and_mixed_receipts_fail_closed():
    target = _bind().to_target()
    stripped = replace(
        target,
        metadata={
            key: value
            for key, value in target.metadata.items()
            if key not in {"policy_monetary_binding", "policy_monetary_binding_sha256"}
        },
    )
    with pytest.raises(MonetaryBindingIntegrityError, match="markers remain"):
        build_constraint_matrix(_frame(), TargetSet([stripped]))

    stripped_generic_markers = replace(
        target,
        metadata={
            key: value
            for key, value in target.metadata.items()
            if key
            not in {
                "policy_monetary_binding",
                "policy_monetary_binding_sha256",
                "monetary_source_activation_status",
                "monetary_target_role",
            }
        },
    )
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="policy_derived_semantics",
    ):
        build_constraint_matrix(_frame(), TargetSet([stripped_generic_markers]))

    mixed = replace(
        target,
        metadata={
            **target.metadata,
            "monetary_binding": "{}",
            "monetary_binding_sha256": "0" * 64,
        },
    )
    with pytest.raises(MonetaryBindingIntegrityError, match="cannot coexist"):
        build_constraint_matrix(_frame(), TargetSet([mixed]))


def test_tampered_rulespec_identity_fails_without_a_matching_receipt_rehash():
    spec = _bind()
    binding = json.loads(spec.metadata["policy_monetary_binding"])
    binding["prepared"]["identity"]["rulespec_artifact_sha256"] = "9" * 64
    prepared = binding["prepared"]
    prepared["receipt_sha256"] = monetary_digest(
        {key: value for key, value in prepared.items() if key != "receipt_sha256"}
    )
    tampered_binding_sha256 = monetary_digest(binding)
    tampered = replace(
        spec.to_target(),
        metadata={
            **spec.metadata,
            "policy_monetary_binding": json.dumps(binding, sort_keys=True),
            "policy_monetary_binding_sha256": tampered_binding_sha256,
        },
    )
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="independent acceptance",
    ):
        build_constraint_matrix(
            _frame(),
            TargetSet([tampered]),
            policy_acceptances={tampered.row_name: _acceptance(spec)},
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (("family", "benefit"), ("signed", True), ("se", 10.0), ("notes", "drift")),
)
def test_registry_selection_fields_cannot_drift_from_policy_receipt(field, value):
    with pytest.raises(ValueError, match=f"reference {field} differs"):
        replace(_bind(), **{field: value})
