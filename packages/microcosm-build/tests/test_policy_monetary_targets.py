"""Authenticated boundary from Axiom policy outputs to monetary calibration.

Three authorities have to agree before a policy-derived row compiles: an
operator trust root that authenticates signed producer and observed-source
artifacts, the Axiom materialization receipt bound to one exact requested
output, and the live frame. Each of the adversarial cases below is a bypass
that a probe compiled before this suite existed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace
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
from microcosm.calibrate import (
    AXIOM_POLICY_ACCEPTANCE_SEAL_TRUST_MODEL,
    AxiomPolicyTargetSpec,
    TargetRegistry,
    TargetSet,
    TargetSpec,
    build_constraint_matrix,
    calibrate,
    calibrate_l0_refit,
    refit_l0_selection,
    score_targets,
)
from microcosm.calibrate.monetary_binding import (
    MonetaryBindingIntegrityError,
    monetary_digest,
)
from microcosm.calibrate.policy_monetary_binding import (
    AxiomPolicyAcceptance,
    AxiomPolicyAcceptanceSet,
    AxiomPolicyTarget,
    AxiomPolicyTrustRoot,
    axiom_array_identity,
    build_axiom_policy_acceptances,
    sign_axiom_policy_attestation,
    verify_policy_monetary_binding,
)
from microcosm.calibrate.target import Target
from microcosm.frame import EntitySchema, Frame, WeightKind, Weights

PRODUCER_KEY = b"axiom-producer-verification-key-0" * 2
OBSERVATION_KEY = b"armstat-observation-verification0" * 2
TRUST_ROOT_ID = "am-release-trust-root"


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
    """Mirror the public schema-v2 numeric/text-vector receipt contract."""
    array = np.asarray(values)
    if array.dtype.kind in "biuf":
        dtype = array.dtype.newbyteorder("<")
        canonical = np.ascontiguousarray(array.astype(dtype, copy=False))
        semantic_dtype = array.dtype.name
        storage_dtype = canonical.dtype.str
        encoding = "little_endian_raw_v1"
        payload_bytes = canonical.tobytes()
    elif array.dtype.kind in ("U", "S", "O"):
        items = array.tolist()
        if any(not isinstance(item, str) for item in items):
            raise ValueError("test receipt text vectors must contain only strings")
        semantic_dtype = "string"
        storage_dtype = "utf8"
        encoding = "canonical_json_utf8_v1"
        payload_bytes = json.dumps(
            items, ensure_ascii=True, separators=(",", ":")
        ).encode()
    else:
        raise ValueError("unsupported test receipt vector dtype")
    header = {
        "dtype": semantic_dtype,
        "storage_dtype": storage_dtype,
        "encoding": encoding,
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
        "sha256": sha256(payload + b"\n" + payload_bytes).hexdigest(),
    }


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


def _string_frame(values=(300.0, 300.0)) -> Frame:
    return Frame(
        {
            "person": pd.DataFrame(
                {
                    "person_id": ["p11", "p12", "p13"],
                    "person_household_id": ["h1", "h1", "h2"],
                    "armenia_personal_income_tax": [100.0, 200.0, 300.0],
                }
            ),
            "household": pd.DataFrame(
                {
                    "household_id": ["h1", "h2"],
                    "household_armenia_personal_income_tax": list(values),
                }
            ),
        },
        EntitySchema(group_entities=("household",)),
        {"household": Weights(np.array([2.0, 1.0]), WeightKind.DESIGN)},
    )


def _materialization_receipt(
    *,
    frame: Frame | None = None,
    year: str = "2024",
    entity: str = "person",
    id_column: str = "person_id",
    output_name: str = "armenia_personal_income_tax",
    output_values=None,
    declared_period: str = "year",
    **changes,
) -> dict[str, object]:
    frame = _frame() if frame is None else frame
    table = frame.table(entity)
    if output_values is None:
        output_values = table[
            "armenia_personal_income_tax"
            if entity == "person"
            else "household_armenia_personal_income_tax"
        ].to_numpy()
    period = {
        "kind": "calendar_year",
        "start": f"{year}-01-01",
        "end": f"{year}-12-31",
    }
    entity_receipt = {
        "frame_entity": entity,
        "engine_entity": entity.capitalize(),
        "current_id_column": id_column,
        "current_ids": _axiom_array_identity(table[id_column].to_numpy()),
        "declared_root_inputs": [],
        "provided_root_inputs": {},
        "relations": {},
        "requested_outputs": {
            output_name: {
                "declared_engine_dtype": "decimal",
                "declared_kernel_dtype": "float",
                "declared_period": declared_period,
                "values": _axiom_array_identity(np.asarray(output_values)),
            }
        },
    }
    input_projection = {
        "schema_version": 2,
        "receipt_kind": "axiom_dense_input_projection",
        "period": period,
        "arithmetic": "decimal",
        "entities": {
            entity: {
                key: value
                for key, value in entity_receipt.items()
                if key != "requested_outputs"
            }
        },
    }
    raw = {
        "schema_version": 2,
        "receipt_kind": "axiom_dense_materialization",
        "period": period,
        "arithmetic": "decimal",
        "entities": {entity: entity_receipt},
        "input_frame_sha256": monetary_digest(input_projection),
    } | changes
    return {**raw, "receipt_sha256": monetary_digest(raw)}


def _identity(materialization=None, **changes) -> AxiomPolicyIdentity:
    materialization = (
        _materialization_receipt() if materialization is None else materialization
    )
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
    materialization = changes.pop("materialization_receipt", None)
    if materialization is None:
        materialization = _materialization_receipt()
    fields = {
        "output_values": np.array([100.0, 200.0, 300.0]),
        "output_record_ids": np.array([11, 12, 13]),
        "target_record_ids": np.array([1, 2]),
        "output_target_ids": np.array([1, 1, 2]),
        "aggregation_membership_column": "person_household_id",
        "basis": _basis(),
        "identity": _identity(materialization),
        "materialization_receipt": materialization,
        "perimeter_bridge_description": (
            "Axiom person PIT is summed to household rows; the observed State "
            "Revenue Committee aggregate uses the same resident PIT perimeter."
        ),
        "perimeter_bridge_source_sha256": "e" * 64,
    }
    return prepare_policy_derived_monetary_measure(**(fields | changes))


def _string_prepared(**changes):
    frame = _string_frame()
    materialization = changes.pop("materialization_receipt", None)
    if materialization is None:
        materialization = _materialization_receipt(frame=frame)
    fields = {
        "output_values": np.array([100.0, 200.0, 300.0]),
        "output_record_ids": np.array(["p11", "p12", "p13"]),
        "target_record_ids": np.array(["h1", "h2"]),
        "output_target_ids": np.array(["h1", "h1", "h2"]),
        "aggregation_membership_column": "person_household_id",
        "basis": _basis(),
        "identity": _identity(materialization),
        "materialization_receipt": materialization,
        "perimeter_bridge_description": (
            "Axiom person PIT is summed to string-keyed household rows within "
            "the observed State Revenue Committee perimeter."
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


def _bind(reference=None, **changes):
    fields = {
        "value": 650_077_932_447,
        "observed_basis": _basis(),
        "observed_source_assertion": "observation",
        "observed_source_identity_sha256": "f" * 64,
        "prepared": _prepared(),
    }
    return bind_policy_derived_monetary_target(
        _reference() if reference is None else reference,
        **(fields | changes),
    )


# --- trust-root artifacts -------------------------------------------------


def _trust_root(**changes) -> AxiomPolicyTrustRoot:
    fields = {
        "trust_root_id": TRUST_ROOT_ID,
        "producer_verification_key": PRODUCER_KEY,
        "observation_verification_key": OBSERVATION_KEY,
    }
    return AxiomPolicyTrustRoot(**(fields | changes))


def _binding_of(spec) -> dict:
    return json.loads(spec.metadata["policy_monetary_binding"])


def _producer_document(*specs, **changes) -> dict[str, object]:
    """The signed producer artifact an operator holds for one Axiom run."""
    identity = _binding_of(specs[0])["prepared"]["identity"]
    document = {
        "schema_version": 1,
        "artifact_kind": "axiom_policy_producer_attestation",
        "trust_root_id": TRUST_ROOT_ID,
        "period": "2024",
        "producer_manifest_sha256": identity["producer_manifest_sha256"],
        "rulespec_artifact_sha256": identity["rulespec_artifact_sha256"],
        "axiom_runtime_sha256": identity["axiom_runtime_sha256"],
        "input_frame_sha256": identity["input_frame_sha256"],
        "parameter_world_sha256": identity["parameter_world_sha256"],
        "materialization_receipt_sha256": identity["materialization_receipt_sha256"],
        "targets": [
            {
                "name": spec.name,
                "period": spec.period,
                "binding_sha256": spec.metadata["policy_monetary_binding_sha256"],
                "prepared_receipt_sha256": _binding_of(spec)["prepared"][
                    "receipt_sha256"
                ],
            }
            for spec in specs
        ],
    }
    return document | changes


def _observation_document(spec, **changes) -> dict[str, object]:
    """The signed observed-source artifact for one administrative aggregate."""
    binding = _binding_of(spec)
    document = {
        "schema_version": 1,
        "artifact_kind": "axiom_policy_observation_attestation",
        "trust_root_id": TRUST_ROOT_ID,
        "name": spec.name,
        "period": spec.period,
        "observed_source_identity_sha256": binding["observed_source_identity_sha256"],
        "observed_value": binding["observed_value"],
        "observed_source": binding["observed_source"],
    }
    return document | changes


def _signed(document, key) -> dict[str, object]:
    return {
        "document": document,
        "signature": sign_axiom_policy_attestation(document, key),
    }


def _acceptances(*specs, trust_root=None, producer=None, observations=None):
    trust_root = _trust_root() if trust_root is None else trust_root
    producer = _producer_document(*specs) if producer is None else producer
    observations = (
        [_observation_document(spec) for spec in specs]
        if observations is None
        else observations
    )
    return build_axiom_policy_acceptances(
        trust_root=trust_root,
        producer_attestation=_signed(producer, PRODUCER_KEY),
        observation_attestations=[
            _signed(document, OBSERVATION_KEY) for document in observations
        ],
    )


def _targets(*specs) -> TargetSet:
    return TargetRegistry(list(specs), country="am").to_target_set()


def _compile(frame=None, spec=None, **kwargs):
    spec = _bind() if spec is None else spec
    return build_constraint_matrix(
        _frame() if frame is None else frame,
        _targets(spec),
        policy_acceptances=_acceptances(spec),
        **kwargs,
    )


def _tampered_target(spec, binding):
    """Re-hash a mutated binding onto a target the way a forger would."""
    prepared = binding["prepared"]
    prepared["receipt_sha256"] = monetary_digest(
        {key: value for key, value in prepared.items() if key != "receipt_sha256"}
    )
    return replace(
        spec.to_target(),
        metadata={
            **spec.metadata,
            "policy_monetary_binding": json.dumps(binding, sort_keys=True),
            "policy_monetary_binding_sha256": monetary_digest(binding),
        },
    )


def _acceptance_for_target(target, **identity_overrides):
    """Mint an acceptance an operator would sign for exactly this row.

    ``identity_overrides`` states what the operator's own signed producer
    artifact says, independently of what the row's receipt claims.
    """
    binding = json.loads(target.metadata["policy_monetary_binding"])
    identity = binding["prepared"]["identity"]
    producer = {
        "schema_version": 1,
        "artifact_kind": "axiom_policy_producer_attestation",
        "trust_root_id": TRUST_ROOT_ID,
        "period": "2024",
        **{
            key: identity[key]
            for key in (
                "producer_manifest_sha256",
                "rulespec_artifact_sha256",
                "axiom_runtime_sha256",
                "input_frame_sha256",
                "parameter_world_sha256",
                "materialization_receipt_sha256",
            )
        },
        "targets": [
            {
                "name": target.name,
                "period": target.period,
                "binding_sha256": target.metadata["policy_monetary_binding_sha256"],
                "prepared_receipt_sha256": binding["prepared"]["receipt_sha256"],
            }
        ],
    } | identity_overrides
    observation = {
        "schema_version": 1,
        "artifact_kind": "axiom_policy_observation_attestation",
        "trust_root_id": TRUST_ROOT_ID,
        "name": target.name,
        "period": target.period,
        "observed_source_identity_sha256": binding["observed_source_identity_sha256"],
        "observed_value": binding["observed_value"],
        "observed_source": binding["observed_source"],
    }
    return build_axiom_policy_acceptances(
        trust_root=_trust_root(),
        producer_attestation=_signed(producer, PRODUCER_KEY),
        observation_attestations=[_signed(observation, OBSERVATION_KEY)],
    )


# --- preparation and receipts --------------------------------------------


def test_person_outputs_sum_to_exact_household_order_with_full_identity_receipt():
    prepared = _prepared()
    np.testing.assert_array_equal(prepared.values, [300.0, 300.0])
    receipt = prepared.receipt()
    assert receipt["schema_version"] == 3
    assert receipt["identity"]["rulespec_artifact_sha256"] == "a" * 64
    assert receipt["identity"]["axiom_runtime_sha256"] == "b" * 64
    assert (
        receipt["identity"]["input_frame_sha256"]
        == receipt["materialization"]["input_frame_sha256"]
    )
    assert receipt["identity"]["parameter_world_sha256"] == "d" * 64
    assert receipt["output"]["n_records"] == 3
    assert receipt["output"]["values"]["dtype"] == "<f8"
    assert receipt["aggregation"]["kind"] == "sum_by_membership"
    assert receipt["aggregation"]["target_n_records"] == 2
    assert receipt["measure_kind"] == "policy_derived"
    assert len(receipt["receipt_sha256"]) == 64


def test_prepared_receipt_carries_the_materialized_output_identity():
    receipt = _prepared().receipt()
    materialization = receipt["materialization"]["entities"]["person"]
    assert (
        receipt["output"]["materialized_values"]
        == materialization["requested_outputs"]["armenia_personal_income_tax"]["values"]
    )
    assert (
        receipt["output"]["materialized_record_ids"] == materialization["current_ids"]
    )


def test_public_axiom_identity_helper_matches_the_receipt_schema():
    values = np.array([100.0, 200.0, 300.0])
    ids = np.array([11, 12, 13], dtype="<i8")
    text_ids = np.array(["p11", "p12", "p13"])
    assert axiom_array_identity(values) == _axiom_array_identity(values)
    assert axiom_array_identity(ids) == _axiom_array_identity(ids)
    assert axiom_array_identity(text_ids) == _axiom_array_identity(text_ids)


def test_string_keyed_policy_rows_preserve_canonical_id_receipts():
    prepared = _string_prepared()
    np.testing.assert_array_equal(prepared.values, [300.0, 300.0])
    receipt = prepared.receipt()
    assert receipt["output"]["record_ids"]["dtype"] == "string"
    assert (
        receipt["output"]["materialized_record_ids"]
        == (receipt["materialization"]["entities"]["person"]["current_ids"])
    )
    assert receipt["aggregation"]["output_target_ids"]["dtype"] == "string"
    assert receipt["aggregation"]["target_record_ids"]["dtype"] == "string"

    # TargetSpec construction validates the complete serialized payload before
    # the live relation-layer verifier is involved.
    spec = _bind(prepared=prepared)
    assert _binding_of(spec)["prepared"]["output"]["record_ids"]["dtype"] == "string"


def test_string_keyed_policy_target_replays_against_live_rows():
    """Exercise the real relation verifier and policy replay with string IDs."""
    spec = _bind(prepared=_string_prepared())
    problem = build_constraint_matrix(
        _string_frame(),
        _targets(spec),
        policy_acceptances=_acceptances(spec),
    )
    np.testing.assert_array_equal(problem.estimates(np.array([2.0, 1.0])), [900.0])


@pytest.mark.parametrize(
    "record_ids",
    (
        np.array(["p11", 12, "p13"], dtype=object),
        np.array([True, False, True]),
        np.array([11.0, 12.0, 13.0]),
    ),
)
def test_policy_record_ids_reject_mixed_bool_and_float_families(record_ids):
    with pytest.raises(ValueError, match="only integer IDs or only string IDs"):
        _prepared(output_record_ids=record_ids)


@pytest.mark.parametrize(
    "record_ids",
    (
        ["p11", 12, "p13"],
        [b"p11", b"p12", b"p13"],
        np.array([b"p11", b"p12", b"p13"]),
    ),
)
def test_policy_record_ids_classify_raw_values_before_numpy_coercion(record_ids):
    with pytest.raises(ValueError, match="only integer IDs or only string IDs"):
        _prepared(output_record_ids=record_ids)


def test_membership_and_target_ids_must_use_one_id_family():
    with pytest.raises(ValueError, match="same integer or string ID family"):
        _string_prepared(output_target_ids=np.array([1, 1, 2]))


@pytest.mark.parametrize(
    "identity_changes",
    (
        {"storage_dtype": "<i8"},
        {"encoding": "little_endian_raw_v1"},
        {"dtype": "int64"},
        {"dtype": []},
    ),
)
def test_string_id_receipt_rejects_malformed_or_mixed_identity(identity_changes):
    materialization = _materialization_receipt(frame=_string_frame())
    materialization["entities"]["person"]["current_ids"].update(identity_changes)
    raw = {
        key: value for key, value in materialization.items() if key != "receipt_sha256"
    }
    materialization["receipt_sha256"] = monetary_digest(raw)
    with pytest.raises(ValueError, match="record ids ID encoding"):
        _string_prepared(materialization_receipt=materialization)


def test_same_entity_output_requires_identical_rows_and_no_mapping():
    materialization = _materialization_receipt(
        entity="household",
        id_column="household_id",
        output_name="household_armenia_personal_income_tax",
        output_values=np.array([10.0, 20.0]),
    )
    identity = _identity(
        materialization,
        output_entity="household",
        output_variable="household_armenia_personal_income_tax",
    )
    prepared = _prepared(
        output_values=np.array([10.0, 20.0]),
        output_record_ids=[1, 2],
        output_target_ids=None,
        aggregation_membership_column=None,
        identity=identity,
        materialization_receipt=materialization,
    )
    assert prepared.receipt()["aggregation"]["kind"] == "identity"
    with pytest.raises(ValueError, match="must not supply"):
        _prepared(
            output_values=np.array([10.0, 20.0]),
            output_record_ids=[1, 2],
            output_target_ids=[1, 2],
            identity=identity,
            materialization_receipt=materialization,
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
    binding = _binding_of(target)
    assert binding["observed_value"] == 650_077_932_447
    assert binding["observed_source_identity_sha256"] == "f" * 64
    assert binding["prepared"]["identity"]["rulespec_artifact_sha256"] == "a" * 64
    assert binding["prepared"]["output"]["n_records"] == 3
    assert target.metadata["activation_status"] == "active"
    assert (
        target.metadata["monetary_source_activation_status"] == "requires_policy_output"
    )


# --- finding 1: the materialization receipt is bound to one exact output ---


def test_receipt_for_an_unrelated_output_cannot_back_a_policy_measure():
    materialization = _materialization_receipt(
        output_name="unrelated_variable",
        output_values=np.array([-1.0, -2.0, -3.0]),
    )
    with pytest.raises(ValueError, match="omits the requested policy output variable"):
        _prepared(materialization_receipt=materialization)


def test_a_prior_period_materialization_cannot_back_this_period_target():
    materialization = _materialization_receipt(year="2023")
    with pytest.raises(ValueError, match="period differs from the policy target"):
        _prepared(materialization_receipt=materialization)


def test_a_receipt_without_the_output_entity_cannot_back_a_policy_measure():
    materialization = _materialization_receipt(
        entity="household",
        id_column="household_id",
        output_name="household_armenia_personal_income_tax",
    )
    with pytest.raises(ValueError, match="omits the policy output entity"):
        _prepared(materialization_receipt=materialization)


def test_materialized_values_must_be_the_exact_prepared_output_vector():
    materialization = _materialization_receipt(
        output_values=np.array([100.0, 200.0, 301.0])
    )
    with pytest.raises(ValueError, match="differ from the materialized requested"):
        _prepared(materialization_receipt=materialization)


def test_multi_output_materialization_is_rejected_during_preparation():
    materialization = _materialization_receipt()
    outputs = materialization["entities"]["person"]["requested_outputs"]
    outputs["unreplayed_policy_output"] = {
        **outputs["armenia_personal_income_tax"],
        "values": _axiom_array_identity(np.array([1.0, 2.0, 3.0])),
    }
    raw = {
        key: value for key, value in materialization.items() if key != "receipt_sha256"
    }
    materialization["receipt_sha256"] = monetary_digest(raw)

    with pytest.raises(ValueError, match="exactly one requested output"):
        _prepared(materialization_receipt=materialization)


def test_materialized_rows_must_be_the_exact_prepared_output_rows():
    materialization = _materialization_receipt()
    entity = materialization["entities"]["person"]
    entity["current_ids"] = _axiom_array_identity(np.array([11, 12, 99], dtype="<i8"))
    raw = {
        key: value for key, value in materialization.items() if key != "receipt_sha256"
    }
    materialization = {**raw, "receipt_sha256": monetary_digest(raw)}
    with pytest.raises(ValueError, match="materialized entity rows"):
        _prepared(
            materialization_receipt=materialization,
            identity=_identity(materialization),
        )


def test_a_non_annual_requested_output_cannot_back_an_annual_flow_target():
    materialization = _materialization_receipt(declared_period="month")
    with pytest.raises(ValueError, match="annual requested output"):
        _prepared(materialization_receipt=materialization)


def test_replayed_binding_rejects_a_swapped_materialized_output_identity():
    spec = _bind()
    binding = _binding_of(spec)
    binding["prepared"]["output"]["materialized_values"] = _axiom_array_identity(
        np.array([1.0, 2.0, 3.0])
    )
    target = _tampered_target(spec, binding)
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="differs from the materialization receipt",
    ):
        build_constraint_matrix(
            _frame(),
            TargetSet([target]),
            policy_acceptances=_acceptance_for_target(target),
        )


# --- finding 2: acceptance is a trust-root judgment, not self-attestation --


def test_acceptances_cannot_be_constructed_outside_the_trust_root():
    minted = _acceptances(_bind()).acceptances[("src/personal_income_tax", 2024)]
    with pytest.raises(ValueError, match="minted by a trust-root verification"):
        AxiomPolicyAcceptance(
            target_key=minted.target_key,
            accepted_target_keys=minted.accepted_target_keys,
            trust_root_id=minted.trust_root_id,
            binding_sha256=minted.binding_sha256,
            prepared_receipt_sha256=minted.prepared_receipt_sha256,
            producer_manifest_sha256="0" * 64,
            rulespec_artifact_sha256=minted.rulespec_artifact_sha256,
            axiom_runtime_sha256=minted.axiom_runtime_sha256,
            input_frame_sha256=minted.input_frame_sha256,
            parameter_world_sha256=minted.parameter_world_sha256,
            materialization_receipt_sha256=minted.materialization_receipt_sha256,
            observed_source_identity_sha256=minted.observed_source_identity_sha256,
            observed_value=minted.observed_value,
            observed_source=minted.observed_source,
            seal=minted.seal,
        )


def test_a_tampered_acceptance_is_refused_at_use_time():
    spec = _bind()
    acceptances = _acceptances(spec)
    acceptance = acceptances.acceptances[("src/personal_income_tax", 2024)]
    object.__setattr__(acceptance, "rulespec_artifact_sha256", "9" * 64)
    with pytest.raises(MonetaryBindingIntegrityError, match="not trust-root sealed"):
        build_constraint_matrix(
            _frame(),
            _targets(spec),
            policy_acceptances={("src/personal_income_tax", 2024): acceptance},
        )


@pytest.mark.parametrize(
    ("producer_key", "observation_key", "message"),
    (
        (OBSERVATION_KEY, OBSERVATION_KEY, "producer attestation signature"),
        (PRODUCER_KEY, PRODUCER_KEY, "observation attestation signature"),
    ),
)
def test_attestations_must_verify_under_their_own_trust_root_key(
    producer_key, observation_key, message
):
    spec = _bind()
    with pytest.raises(ValueError, match=message):
        build_axiom_policy_acceptances(
            trust_root=_trust_root(),
            producer_attestation=_signed(_producer_document(spec), producer_key),
            observation_attestations=[
                _signed(_observation_document(spec), observation_key)
            ],
        )


def test_a_document_edited_after_signing_no_longer_verifies():
    spec = _bind()
    attestation = _signed(_producer_document(spec), PRODUCER_KEY)
    attestation["document"]["rulespec_artifact_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="producer attestation signature"):
        build_axiom_policy_acceptances(
            trust_root=_trust_root(),
            producer_attestation=attestation,
            observation_attestations=[
                _signed(_observation_document(spec), OBSERVATION_KEY)
            ],
        )


def test_observations_must_cover_exactly_the_produced_target_set():
    spec = _bind()
    with pytest.raises(ValueError, match="cover exactly the produced target set"):
        build_axiom_policy_acceptances(
            trust_root=_trust_root(),
            producer_attestation=_signed(_producer_document(spec), PRODUCER_KEY),
            observation_attestations=[],
        )
    other = _observation_document(spec, name="src/other_tax")
    with pytest.raises(ValueError, match="cover exactly the produced target set"):
        build_axiom_policy_acceptances(
            trust_root=_trust_root(),
            producer_attestation=_signed(_producer_document(spec), PRODUCER_KEY),
            observation_attestations=[
                _signed(_observation_document(spec), OBSERVATION_KEY),
                _signed(other, OBSERVATION_KEY),
            ],
        )


def test_a_forged_receipt_cannot_restate_the_signed_producer_identity():
    """The operator's signed artifact, not the receipt, states the run identity.

    Even where an operator countersigns the digest of a rehashed binding, the
    producer artifact still carries the true RuleSpec hash, so the substituted
    identity is caught on its own pin.
    """
    spec = _bind()
    binding = _binding_of(spec)
    binding["prepared"]["identity"]["rulespec_artifact_sha256"] = "9" * 64
    target = _tampered_target(spec, binding)
    acceptances = _acceptance_for_target(target, rulespec_artifact_sha256="a" * 64)
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="rulespec_artifact_sha256 differs from the independent acceptance",
    ):
        build_constraint_matrix(
            _frame(),
            TargetSet([target]),
            policy_acceptances=acceptances,
        )


def test_the_signed_observation_pins_the_observed_aggregate():
    spec = _bind()
    acceptances = _acceptances(
        spec,
        observations=[_observation_document(spec, observed_value=1.0)],
    )
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="observed aggregate differs from the independent acceptance",
    ):
        build_constraint_matrix(
            _frame(), _targets(spec), policy_acceptances=acceptances
        )


def test_an_accepted_target_key_cannot_be_stripped_into_an_ordinary_row():
    spec = _bind()
    target = spec.to_target()
    stripped = replace(target, metadata={})
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="carries no policy monetary receipt",
    ):
        build_constraint_matrix(
            _frame(),
            TargetSet([stripped]),
            policy_acceptances=_acceptances(spec),
        )


def test_policy_target_cannot_strip_all_metadata_and_omit_acceptance():
    """Policy provenance survives the combined receipt/acceptance stripping bypass."""
    spec = _bind()
    stripped = replace(spec.to_target(), metadata={})

    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="authenticated_policy_target",
    ):
        build_constraint_matrix(_frame(), TargetSet([stripped]))


def test_policy_spec_provenance_survives_metadata_replacement_through_matrix():
    spec = _bind()
    stripped_spec = replace(spec, metadata={})
    stripped_target = stripped_spec.to_target()

    assert isinstance(spec, AxiomPolicyTargetSpec)
    assert isinstance(stripped_spec, AxiomPolicyTargetSpec)
    assert isinstance(stripped_target, AxiomPolicyTarget)
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="authenticated_policy_target",
    ):
        build_constraint_matrix(_frame(), TargetSet([stripped_target]))


def test_policy_metadata_cannot_be_rewrapped_in_a_plain_target_spec():
    with pytest.raises(TypeError, match="must be constructed as AxiomPolicyTargetSpec"):
        TargetSpec(**asdict(_bind()))


def test_policy_registry_round_trip_restores_the_nominal_spec_type(tmp_path):
    path = TargetRegistry([_bind()], country="am").to_json(tmp_path / "targets.json")
    restored = TargetRegistry.from_json(path).specs[0]

    assert isinstance(restored, AxiomPolicyTargetSpec)
    assert isinstance(restored.to_target(), AxiomPolicyTarget)


def test_nominal_policy_target_never_enters_direct_monetary_verification():
    target = replace(
        _bind().to_target(),
        metadata={
            "monetary_binding": "{}",
            "monetary_binding_sha256": "0" * 64,
        },
    )

    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="nominal Axiom policy target cannot use a direct monetary receipt",
    ):
        build_constraint_matrix(_frame(), TargetSet([target]))


def test_an_accepted_target_dropped_from_the_surface_fails_the_compilation():
    spec = _bind()
    ordinary = Target(
        name="households",
        entity="household",
        measure="household_armenia_personal_income_tax",
        value=900.0,
        period=2024,
        source="ordinary",
    )
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="did not match compiled policy targets",
    ):
        build_constraint_matrix(
            _frame(),
            TargetSet([ordinary]),
            policy_acceptances=_acceptances(spec),
        )


def test_the_accepted_set_can_be_neither_trimmed_nor_refiled():
    int_spec = _bind()
    str_spec = _bind(_reference(period="2024"))
    acceptances = _acceptances(int_spec, str_spec)
    trimmed = {
        ("src/personal_income_tax", 2024): acceptances.acceptances[
            ("src/personal_income_tax", 2024)
        ]
    }
    with pytest.raises(
        MonetaryBindingIntegrityError, match="not the exact accepted set"
    ):
        build_constraint_matrix(
            _frame(), _targets(int_spec), policy_acceptances=trimmed
        )
    refiled = {
        ("src/personal_income_tax", "2024"): acceptances.acceptances[
            ("src/personal_income_tax", 2024)
        ],
        ("src/personal_income_tax", 2024): acceptances.acceptances[
            ("src/personal_income_tax", "2024")
        ],
    }
    with pytest.raises(
        MonetaryBindingIntegrityError, match="filed under the wrong target key"
    ):
        build_constraint_matrix(
            _frame(),
            _targets(int_spec, str_spec),
            policy_acceptances=refiled,
        )


def test_acceptances_from_two_trust_roots_cannot_be_merged():
    spec = _bind()
    other_root = _trust_root(trust_root_id="rogue-root")
    other = build_axiom_policy_acceptances(
        trust_root=other_root,
        producer_attestation=_signed(
            _producer_document(spec, trust_root_id="rogue-root"), PRODUCER_KEY
        ),
        observation_attestations=[
            _signed(
                _observation_document(spec, trust_root_id="rogue-root"),
                OBSERVATION_KEY,
            )
        ],
    )
    merged = {
        ("src/personal_income_tax", 2024): _acceptances(spec).acceptances[
            ("src/personal_income_tax", 2024)
        ],
        ("src/other_tax", 2024): other.acceptances[("src/personal_income_tax", 2024)],
    }
    with pytest.raises(MonetaryBindingIntegrityError, match="mix trust roots"):
        build_constraint_matrix(_frame(), _targets(spec), policy_acceptances=merged)


def test_trust_root_requires_separate_strong_producer_and_observation_keys():
    with pytest.raises(ValueError, match="at least 32 bytes"):
        _trust_root(producer_verification_key=b"short")
    with pytest.raises(ValueError, match="keys must differ"):
        _trust_root(observation_verification_key=PRODUCER_KEY)


def test_acceptance_seal_declares_its_trusted_python_process_boundary():
    spec = _bind()
    acceptance = next(iter(_acceptances(spec).acceptances.values()))

    assert AXIOM_POLICY_ACCEPTANCE_SEAL_TRUST_MODEL == "trusted_in_process_python_v1"
    assert (
        acceptance._sealed_fields()["seal_trust_model"]
        == AXIOM_POLICY_ACCEPTANCE_SEAL_TRUST_MODEL
    )
    assert "trusted in-process Python" in AxiomPolicyAcceptance.__doc__


# --- compilation, replay, and stripping ------------------------------------


def test_policy_bound_target_compiles_only_against_exact_receipted_column():
    problem = _compile()
    np.testing.assert_array_equal(problem.estimates(np.array([2.0, 1.0])), [900.0])
    with pytest.raises(MonetaryBindingIntegrityError, match="values differ"):
        _compile(frame=_frame(values=(301.0, 299.0)))


def test_matrix_uses_verified_live_policy_vector_without_constraint_redispatch(
    monkeypatch,
):
    spec = _bind()
    verified = verify_policy_monetary_binding(
        spec.to_target(),
        _frame(),
        acceptance=_acceptances(spec).get(spec.key),
    )
    assert verified.flags.owndata
    assert not verified.flags.writeable

    def reject_redispatch(self, frame):
        raise AssertionError("policy constraint_row must not be redispatched")

    monkeypatch.setattr(AxiomPolicyTarget, "constraint_row", reject_redispatch)
    problem = _compile()
    np.testing.assert_array_equal(problem.estimates(np.array([2.0, 1.0])), [900.0])


def test_policy_target_requires_independent_acceptance():
    with pytest.raises(MonetaryBindingIntegrityError, match="independent"):
        build_constraint_matrix(_frame(), _targets(_bind()))


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
    binding = _binding_of(spec)
    binding["prepared"]["identity"]["rulespec_artifact_sha256"] = "9" * 64
    tampered = _tampered_target(spec, binding)
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="independent acceptance",
    ):
        build_constraint_matrix(
            _frame(),
            TargetSet([tampered]),
            policy_acceptances=_acceptances(spec),
        )


# --- finding 5: acceptances are keyed by the typed target identity ---------


def test_row_name_keyed_acceptances_are_refused_by_name():
    spec = _bind()
    with pytest.raises(TypeError, match="not the lossy 'name@period' row label"):
        build_constraint_matrix(
            _frame(),
            _targets(spec),
            policy_acceptances={"src/personal_income_tax@2024": object()},
        )


def test_int_and_string_period_targets_receive_their_own_acceptances():
    int_spec = _bind()
    str_spec = _bind(_reference(period="2024"))
    targets = _targets(int_spec, str_spec)
    assert [target.key for target in targets] == [
        ("src/personal_income_tax", 2024),
        ("src/personal_income_tax", "2024"),
    ]
    assert len({target.row_name for target in targets}) == 1
    problem = build_constraint_matrix(
        _frame(),
        targets,
        policy_acceptances=_acceptances(int_spec, str_spec),
    )
    np.testing.assert_array_equal(
        problem.estimates(np.array([2.0, 1.0])), [900.0, 900.0]
    )


def test_a_float_period_target_cannot_borrow_an_int_period_acceptance():
    """``2024.0`` hashes and compares equal to ``2024``; the identity must not."""
    spec = _bind()
    drifted = replace(spec.to_target(), period=2024.0)
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="names a different target identity",
    ):
        build_constraint_matrix(
            _frame(),
            TargetSet([drifted]),
            policy_acceptances=_acceptances(spec),
        )


def test_policy_acceptances_reject_a_non_mapping_argument():
    with pytest.raises(TypeError, match="must be an AxiomPolicyAcceptanceSet"):
        build_constraint_matrix(
            _frame(), _targets(_bind()), policy_acceptances=["not-a-mapping"]
        )


def test_an_acceptance_set_round_trips_through_a_plain_typed_mapping():
    spec = _bind()
    acceptances = _acceptances(spec)
    assert acceptances.keys() == (("src/personal_income_tax", 2024),)
    rebuilt = AxiomPolicyAcceptanceSet.from_mapping(dict(acceptances.acceptances))
    problem = build_constraint_matrix(
        _frame(), _targets(spec), policy_acceptances=rebuilt
    )
    assert problem.names == ("src/personal_income_tax@2024",)


# --- finding 6: schema and numeric types fail closed before coercion -------


def test_a_float_shape_cannot_impersonate_a_typed_vector_identity():
    spec = _bind()
    binding = _binding_of(spec)
    binding["prepared"]["output"]["values"]["shape"] = [3.0]
    target = _tampered_target(spec, binding)
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="invalid policy output values shape",
    ):
        build_constraint_matrix(
            _frame(),
            TargetSet([target]),
            policy_acceptances=_acceptance_for_target(target),
        )


def test_an_integer_observed_value_cannot_impersonate_the_float_receipt():
    spec = _bind()
    binding = _binding_of(spec)
    binding["observed_value"] = 650_077_932_447
    target = _tampered_target(spec, binding)
    with pytest.raises(
        MonetaryBindingIntegrityError,
        match="observed target value is invalid",
    ):
        build_constraint_matrix(
            _frame(),
            TargetSet([target]),
            policy_acceptances=_acceptance_for_target(target),
        )


@pytest.mark.parametrize("value", (True, "1", "650077932447"))
def test_observed_amounts_refuse_bool_and_string_coercion(value):
    with pytest.raises(ValueError, match="must be an int or float"):
        _bind(value=value)


def test_observed_amounts_accept_int_and_float_alike():
    assert _bind(value=650_077_932_447).value == 650_077_932_447.0
    assert _bind(value=650_077_932_447.0).value == 650_077_932_447.0


@pytest.mark.parametrize("value", (2**53 + 1, -(2**53 + 1)))
def test_observed_integer_amount_must_be_exactly_representable_as_float(value):
    reference = _reference(signed=value < 0)
    with pytest.raises(ValueError, match="exactly representable as float64"):
        _bind(reference, value=value)


@pytest.mark.parametrize("period", (2024.0, True))
def test_reference_period_tags_refuse_float_and_bool(period):
    with pytest.raises(ValueError, match="explicit int or str period tag"):
        _bind(_reference(period=period))


def test_reference_uncertainty_must_be_float_or_none():
    with pytest.raises(ValueError, match="must be an explicit float or None"):
        _bind(_reference(se=10))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("family", "benefit"),
        ("signed", True),
        ("signed", 0),
        ("se", 10.0),
        ("notes", "drift"),
        ("period", 2024.0),
    ),
)
def test_registry_selection_fields_cannot_drift_from_policy_receipt(field, value):
    with pytest.raises(ValueError, match=f"reference {field} differs"):
        replace(_bind(), **{field: value})


# --- public calibration and scoring paths ---------------------------------


def test_score_targets_accepts_authenticated_policy_rows():
    spec = _bind()
    result = score_targets(
        _frame(),
        _targets(spec),
        policy_acceptances=_acceptances(spec),
    )
    diagnostic = result.diagnostics[0]
    assert diagnostic.name == "src/personal_income_tax@2024"
    assert diagnostic.initial_estimate == pytest.approx(900.0)


def test_score_targets_without_acceptance_fails_closed():
    with pytest.raises(MonetaryBindingIntegrityError, match="independent"):
        score_targets(_frame(), _targets(_bind()))


def test_calibrate_accepts_authenticated_policy_rows():
    spec = _bind()
    result = calibrate(
        _frame(),
        _targets(spec),
        epochs=4,
        policy_acceptances=_acceptances(spec),
    )
    assert result.weights.shape == (2,)
    assert result.diagnostics[0].name == "src/personal_income_tax@2024"


def test_calibrate_without_acceptance_fails_closed():
    with pytest.raises(MonetaryBindingIntegrityError, match="independent"):
        calibrate(_frame(), _targets(_bind()), epochs=1)


def test_frozen_support_refits_reject_policy_targets_by_name():
    spec = _bind()
    targets = _targets(spec)
    with pytest.raises(
        ValueError,
        match="calibrate_l0_refit does not support authenticated Axiom",
    ):
        calibrate_l0_refit(_frame(), targets, l0_lambda=0.5, epochs=1)

    ordinary = TargetSet(
        [
            Target(
                name="households",
                entity="household",
                measure="household_armenia_personal_income_tax",
                value=900.0,
                period=2024,
                source="ordinary",
            )
        ]
    )
    selection = calibrate(_frame(), ordinary, epochs=2, l0_lambda=0.001)
    assert selection.l0_lambda > 0.0
    with pytest.raises(
        ValueError,
        match="refit_l0_selection does not support authenticated Axiom",
    ):
        refit_l0_selection(_frame(), targets, selection)


def test_ordinary_targets_are_unaffected_by_the_policy_lane():
    ordinary = TargetSet(
        [
            Target(
                name="households",
                entity="household",
                measure="household_armenia_personal_income_tax",
                value=900.0,
                period=2024,
                source="ordinary",
            )
        ]
    )
    problem = build_constraint_matrix(_frame(), ordinary)
    np.testing.assert_array_equal(problem.estimates(np.array([2.0, 1.0])), [900.0])
    assert score_targets(_frame(), ordinary).diagnostics[0].name == "households@2024"
