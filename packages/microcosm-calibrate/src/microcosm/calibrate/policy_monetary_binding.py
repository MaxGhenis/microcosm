"""Integrity checks for Axiom policy-derived monetary calibration rows."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np

from microcosm.calibrate.monetary_binding import (
    MonetaryBindingIntegrityError,
    canonical_record_ids,
    monetary_digest,
)
from microcosm.calibrate.target import Target
from microcosm.frame import Frame

_RECEIPT_KEYS = frozenset({"policy_monetary_binding", "policy_monetary_binding_sha256"})
_BINDING_KEYS = frozenset(
    {
        "reference",
        "source_reference",
        "observed_value",
        "observed_source",
        "observed_source_assertion",
        "observed_source_identity_sha256",
        "observed_basis",
        "prepared",
    }
)
_REFERENCE_KEYS = frozenset(
    {
        "name",
        "ledger_fact_key",
        "ledger_source_record_id",
        "ledger_selector",
        "value_operation",
        "entity",
        "measure",
        "filter",
        "period",
        "source",
        "family",
        "signed",
        "se",
        "tolerance",
        "notes",
        "metadata",
        "assertion_policy",
        "period_match_policy",
        "uprating_index",
        "uprating_from_period",
        "uprating_to_period",
    }
)
_PREPARED_KEYS = frozenset(
    {
        "schema_version",
        "identity",
        "basis",
        "output",
        "aggregation",
        "materialization",
        "perimeter_bridge",
        "readiness",
        "measure_kind",
        "receipt_sha256",
    }
)
_IDENTITY_KEYS = frozenset(
    {
        "producer_manifest_sha256",
        "rulespec_artifact_sha256",
        "axiom_runtime_sha256",
        "input_frame_sha256",
        "parameter_world_sha256",
        "materialization_receipt_sha256",
        "period",
        "output_variable",
        "output_entity",
        "target_entity",
        "target_measure",
    }
)
_BASIS_KEYS = frozenset(
    {
        "currency",
        "unit",
        "period",
        "temporal_basis",
        "sector",
        "perimeter",
        "valuation",
    }
)
_OUTPUT_KEYS = frozenset({"n_records", "values", "record_ids"})
_AGGREGATION_KEYS = frozenset(
    {
        "kind",
        "membership_column",
        "output_target_ids",
        "target_n_records",
        "target_values",
        "target_record_ids",
    }
)
_BRIDGE_KEYS = frozenset({"description", "source_sha256"})
_ARRAY_IDENTITY_KEYS = frozenset({"dtype", "shape", "sha256"})


@dataclass(frozen=True)
class AxiomPolicyAcceptance:
    """Independent expected identities required to admit one policy target.

    The receipt carried by a target is a drift detector, not an authority. A
    caller must obtain these pins from the separately authenticated producer
    manifest and observed-source artifact, then pass them explicitly to matrix
    compilation. This prevents a self-consistent fabricated target from
    authenticating itself.
    """

    binding_sha256: str
    prepared_receipt_sha256: str
    producer_manifest_sha256: str
    rulespec_artifact_sha256: str
    axiom_runtime_sha256: str
    input_frame_sha256: str
    parameter_world_sha256: str
    materialization_receipt_sha256: str
    observed_source_identity_sha256: str

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or re.fullmatch(r"[0-9a-f]{64}", value) is None
            ):
                raise ValueError(
                    f"AxiomPolicyAcceptance.{name} must be a lowercase SHA-256."
                )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _hash(value: object, label: str) -> None:
    _require(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
        f"invalid {label}",
    )


def _exact_mapping(value: object, keys: frozenset[str], label: str) -> dict:
    _require(isinstance(value, dict), f"{label} must be an object")
    actual = set(value)
    _require(
        actual == keys,
        f"{label} keys differ: expected {sorted(keys)}, got {sorted(actual)}",
    )
    return value


def _validate_basis(value: object, label: str) -> dict:
    basis = _exact_mapping(value, _BASIS_KEYS, label)
    _require(
        isinstance(basis["currency"], str)
        and re.fullmatch(r"[A-Z]{3}", basis["currency"]) is not None,
        f"invalid {label} currency",
    )
    _require(basis["unit"] == "base_currency", f"invalid {label} unit")
    _require(basis["temporal_basis"] == "annual_flow", f"invalid {label} time basis")
    period = basis["period"]
    _require(
        isinstance(period, str) and re.fullmatch(r"[0-9]{4}", period) is not None,
        f"invalid {label} period",
    )
    date(int(period), 1, 1)
    for key in ("sector", "perimeter", "valuation"):
        _require(
            isinstance(basis[key], str) and basis[key].strip(),
            f"invalid {label} {key}",
        )
    return basis


def _array_identity(values: np.ndarray) -> dict[str, object]:
    array = np.ascontiguousarray(np.asarray(values))
    header = json.dumps(
        {"dtype": array.dtype.str, "shape": list(array.shape)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": hashlib.sha256(header + b"\n" + array.tobytes()).hexdigest(),
    }


def _validate_array_identity(
    value: object,
    *,
    label: str,
    dtype: str,
    length: int,
) -> dict:
    identity = _exact_mapping(value, _ARRAY_IDENTITY_KEYS, label)
    _require(identity["dtype"] == dtype, f"invalid {label} dtype")
    _require(identity["shape"] == [length], f"invalid {label} shape")
    _hash(identity["sha256"], label)
    return identity


def _aligned_ids(values: object, label: str) -> np.ndarray:
    ids = np.asarray(values)
    _require(
        ids.ndim == 1 and ids.size > 0 and ids.dtype.kind in "iu",
        f"{label} must be a nonempty integer vector",
    )
    if ids.dtype.kind == "u":
        _require(
            ids.max() <= np.iinfo(np.int64).max,
            f"{label} exceeds signed int64",
        )
    return ids.astype("<i8", copy=False)


def validate_policy_monetary_binding_payload(
    binding_value: object,
) -> dict[str, object]:
    """Validate every serialized invariant shared by bind and replay."""
    binding = _exact_mapping(binding_value, _BINDING_KEYS, "policy binding")
    reference = _exact_mapping(
        binding["reference"], _REFERENCE_KEYS, "activated reference receipt"
    )
    source_reference = _exact_mapping(
        binding["source_reference"], _REFERENCE_KEYS, "source reference receipt"
    )
    _require(
        {key: value for key, value in reference.items() if key != "metadata"}
        == {key: value for key, value in source_reference.items() if key != "metadata"},
        "activated reference differs from its source reference",
    )
    source_metadata = source_reference["metadata"]
    _require(isinstance(source_metadata, dict), "invalid source reference metadata")
    _require(
        source_metadata.get("monetary_target_role") == "calibration"
        and source_metadata.get("measure_kind") == "policy_derived"
        and source_metadata.get("activation_status")
        in {"requires_policy_output", "ready", "active"},
        "source reference is not an eligible policy-derived calibration target",
    )
    expected_metadata = {
        **source_metadata,
        "activation_status": "active",
        "monetary_source_activation_status": source_metadata.get(
            "activation_status", "requires_policy_output"
        ),
        "monetary_target_role": "calibration",
    }
    _require(
        reference["metadata"] == expected_metadata,
        "activated reference metadata differs from its source reference",
    )
    _require(reference["filter"] is None, "policy monetary filters are unsupported")
    _require(
        reference["value_operation"] == "identity"
        and reference["assertion_policy"] == "observed_only"
        and reference["period_match_policy"] == "exact"
        and all(
            reference[key] is None
            for key in (
                "uprating_index",
                "uprating_from_period",
                "uprating_to_period",
            )
        ),
        "policy reference permits an implicit transformation",
    )
    _require(type(reference["signed"]) is bool, "policy reference signed is invalid")

    prepared = _exact_mapping(
        binding["prepared"], _PREPARED_KEYS, "policy prepared receipt"
    )
    _require(prepared["schema_version"] == 2, "unsupported policy receipt version")
    raw_prepared = {
        key: value for key, value in prepared.items() if key != "receipt_sha256"
    }
    _require(
        monetary_digest(raw_prepared) == prepared["receipt_sha256"],
        "policy prepared receipt hash differs",
    )
    _require(
        prepared["readiness"] == "ready"
        and prepared["measure_kind"] == "policy_derived",
        "policy measure is not ready/policy_derived",
    )

    identity = _exact_mapping(prepared["identity"], _IDENTITY_KEYS, "policy identity")
    for key in (
        "producer_manifest_sha256",
        "rulespec_artifact_sha256",
        "axiom_runtime_sha256",
        "input_frame_sha256",
        "parameter_world_sha256",
        "materialization_receipt_sha256",
    ):
        _hash(identity[key], key)
    for key in (
        "period",
        "output_variable",
        "output_entity",
        "target_entity",
        "target_measure",
    ):
        _require(
            isinstance(identity[key], str) and identity[key].strip(),
            f"invalid policy identity {key}",
        )

    basis = _validate_basis(prepared["basis"], "policy basis")
    observed_basis = _validate_basis(binding["observed_basis"], "observed basis")
    _require(observed_basis == basis, "observed and policy bases differ")
    _require(identity["period"] == basis["period"], "policy period differs")
    _require(str(reference["period"]) == basis["period"], "reference period differs")
    _require(reference["entity"] == identity["target_entity"], "target entity differs")
    _require(
        reference["measure"] == identity["target_measure"],
        "prepared target measure differs from reference",
    )

    output = _exact_mapping(prepared["output"], _OUTPUT_KEYS, "policy output")
    _require(
        type(output["n_records"]) is int and output["n_records"] > 0,
        "invalid policy output record count",
    )
    output_values = _validate_array_identity(
        output["values"],
        label="policy output values",
        dtype="<f8",
        length=output["n_records"],
    )
    output_ids = _validate_array_identity(
        output["record_ids"],
        label="policy output record ids",
        dtype="<i8",
        length=output["n_records"],
    )

    aggregation = _exact_mapping(
        prepared["aggregation"], _AGGREGATION_KEYS, "policy aggregation"
    )
    _require(
        type(aggregation["target_n_records"]) is int
        and aggregation["target_n_records"] > 0,
        "invalid target record count",
    )
    output_target_ids = _validate_array_identity(
        aggregation["output_target_ids"],
        label="policy output target ids",
        dtype="<i8",
        length=output["n_records"],
    )
    target_values = _validate_array_identity(
        aggregation["target_values"],
        label="policy target values",
        dtype="<f8",
        length=aggregation["target_n_records"],
    )
    target_ids = _validate_array_identity(
        aggregation["target_record_ids"],
        label="policy target record ids",
        dtype="<i8",
        length=aggregation["target_n_records"],
    )
    if identity["output_entity"] == identity["target_entity"]:
        _require(
            aggregation["kind"] == "identity"
            and aggregation["membership_column"] is None,
            "same-entity output was remapped",
        )
        _require(
            aggregation["target_n_records"] == output["n_records"]
            and target_values == output_values
            and target_ids == output_ids
            and output_target_ids == output_ids,
            "same-entity output and target receipts differ",
        )
    else:
        _require(
            aggregation["kind"] == "sum_by_membership"
            and isinstance(aggregation["membership_column"], str)
            and aggregation["membership_column"].strip(),
            "cross-entity output lacks explicit membership aggregation",
        )

    materialization = prepared["materialization"]
    _require(isinstance(materialization, dict), "materialization receipt is invalid")
    raw_materialization = {
        key: value for key, value in materialization.items() if key != "receipt_sha256"
    }
    _require(
        monetary_digest(raw_materialization) == materialization.get("receipt_sha256"),
        "materialization receipt hash differs",
    )
    _require(
        materialization.get("receipt_sha256")
        == identity["materialization_receipt_sha256"],
        "materialization receipt differs from policy identity",
    )
    _require(
        materialization.get("input_frame_sha256") == identity["input_frame_sha256"],
        "materialization input frame differs from policy identity",
    )

    bridge = _exact_mapping(
        prepared["perimeter_bridge"], _BRIDGE_KEYS, "perimeter bridge"
    )
    _require(
        isinstance(bridge["description"], str) and bridge["description"].strip(),
        "missing perimeter bridge description",
    )
    _hash(bridge["source_sha256"], "perimeter bridge source")
    _hash(binding["observed_source_identity_sha256"], "observed source identity")
    _require(
        binding["observed_source_assertion"]
        in {"observation", "observed", "derived_observation"},
        "policy target source is not an observation",
    )
    _require(
        isinstance(binding["observed_source"], str)
        and binding["observed_source"].strip(),
        "observed source is missing",
    )
    _require(
        not isinstance(binding["observed_value"], bool)
        and isinstance(binding["observed_value"], (int, float))
        and math.isfinite(binding["observed_value"]),
        "observed target value is invalid",
    )
    return {
        "aggregation": aggregation,
        "binding": binding,
        "identity": identity,
        "materialization": materialization,
        "output": output,
        "prepared": prepared,
        "reference": reference,
    }


def verify_policy_monetary_target_spec(spec: Any) -> None:
    """Authenticate TargetSpec-only fields before registry selection."""
    metadata = spec.metadata
    present = _RECEIPT_KEYS.intersection(metadata)
    active_policy = (
        metadata.get("measure_kind") == "policy_derived"
        and metadata.get("activation_status") == "active"
    )
    if not present and not active_policy:
        return
    _require(present == _RECEIPT_KEYS, "policy monetary receipt is incomplete")
    binding = json.loads(metadata["policy_monetary_binding"])
    _require(
        monetary_digest(binding) == metadata["policy_monetary_binding_sha256"],
        "policy binding hash differs",
    )
    payload = validate_policy_monetary_binding_payload(binding)
    reference = payload["reference"]
    for field in (
        "name",
        "entity",
        "measure",
        "period",
        "filter",
        "family",
        "signed",
        "se",
        "tolerance",
        "notes",
    ):
        _require(getattr(spec, field) == reference[field], f"reference {field} differs")
    _require(
        spec.value == binding["observed_value"]
        and spec.source == binding["observed_source"],
        "observed target value/source differs",
    )
    _require(
        {key: value for key, value in metadata.items() if key not in _RECEIPT_KEYS}
        == reference["metadata"],
        "policy reference metadata differs",
    )


def verify_policy_monetary_binding(
    target: Target,
    frame: Frame,
    *,
    acceptance: AxiomPolicyAcceptance | None,
) -> None:
    """Require independent pins and replay the receipt against the live frame."""
    try:
        _require(
            isinstance(acceptance, AxiomPolicyAcceptance),
            "an independent Axiom policy acceptance is required",
        )
        present = _RECEIPT_KEYS.intersection(target.metadata)
        _require(present == _RECEIPT_KEYS, "policy monetary receipt is incomplete")
        _require(target.filter is None, "policy monetary filters are unsupported")
        binding = json.loads(target.metadata["policy_monetary_binding"])
        _require(
            monetary_digest(binding)
            == target.metadata["policy_monetary_binding_sha256"],
            "policy binding hash differs",
        )
        _require(
            target.metadata["policy_monetary_binding_sha256"]
            == acceptance.binding_sha256,
            "policy binding differs from the independent acceptance",
        )
        payload = validate_policy_monetary_binding_payload(binding)
        aggregation = payload["aggregation"]
        identity = payload["identity"]
        output = payload["output"]
        prepared = payload["prepared"]
        reference = payload["reference"]
        _require(
            prepared["receipt_sha256"] == acceptance.prepared_receipt_sha256,
            "policy prepared receipt differs from the independent acceptance",
        )
        for key in (
            "producer_manifest_sha256",
            "rulespec_artifact_sha256",
            "axiom_runtime_sha256",
            "input_frame_sha256",
            "parameter_world_sha256",
            "materialization_receipt_sha256",
        ):
            _require(
                identity[key] == getattr(acceptance, key),
                f"{key} differs from the independent acceptance",
            )
        _require(
            binding["observed_source_identity_sha256"]
            == acceptance.observed_source_identity_sha256,
            "observed source differs from the independent acceptance",
        )

        for field in ("name", "entity", "measure", "period", "tolerance", "filter"):
            _require(
                getattr(target, field) == reference[field], f"reference {field} differs"
            )
        _require(
            binding["observed_value"] == target.value
            and binding["observed_source"] == target.source,
            "observed target value/source differs",
        )
        _require(
            {
                key: value
                for key, value in target.metadata.items()
                if key not in _RECEIPT_KEYS
            }
            == reference["metadata"],
            "policy reference metadata differs",
        )

        from microcosm.frame.adapters.axiom import (
            verify_axiom_materialization_receipt,
        )

        verify_axiom_materialization_receipt(frame, payload["materialization"])

        output_table = frame.table(identity["output_entity"])
        raw_outputs = output_table[identity["output_variable"]].to_numpy()
        _require(
            raw_outputs.dtype == np.dtype("<f8")
            and raw_outputs.ndim == 1
            and np.isfinite(raw_outputs).all(),
            "live Axiom outputs are not native finite float64",
        )
        output_ids = canonical_record_ids(
            output_table[
                frame.schema.entity_id_column(identity["output_entity"])
            ].to_numpy()
        )
        _require(
            _array_identity(raw_outputs) == output["values"],
            "live Axiom output values differ",
        )
        _require(
            _array_identity(output_ids) == output["record_ids"],
            "live Axiom output record IDs/order differ",
        )

        target_table = frame.table(identity["target_entity"])
        target_values = target_table[identity["target_measure"]].to_numpy()
        _require(
            target_values.dtype == np.dtype("<f8")
            and target_values.ndim == 1
            and np.isfinite(target_values).all(),
            "live policy target values are not native finite float64",
        )
        target_ids = canonical_record_ids(
            target_table[
                frame.schema.entity_id_column(identity["target_entity"])
            ].to_numpy()
        )
        if aggregation["kind"] == "identity":
            mapped_ids = output_ids
            recomputed = raw_outputs
        else:
            membership_column = aggregation["membership_column"]
            mapped_ids = _aligned_ids(
                output_table[membership_column].to_numpy(),
                "live output membership",
            )
            _require(
                mapped_ids.shape == output_ids.shape,
                "live output membership length differs",
            )
            positions = {int(value): index for index, value in enumerate(target_ids)}
            _require(
                set(int(value) for value in mapped_ids) == set(positions),
                "live output membership does not cover exact target IDs",
            )
            recomputed = np.zeros(len(target_ids), dtype="<f8")
            with np.errstate(over="raise", invalid="raise"):
                np.add.at(
                    recomputed,
                    np.fromiter(
                        (positions[int(value)] for value in mapped_ids),
                        dtype=np.int64,
                        count=len(mapped_ids),
                    ),
                    raw_outputs,
                )
        _require(
            _array_identity(mapped_ids) == aggregation["output_target_ids"],
            "live output-to-target mapping differs",
        )
        _require(
            _array_identity(target_ids) == aggregation["target_record_ids"],
            "live target record IDs/order differ",
        )
        _require(
            _array_identity(target_values) == aggregation["target_values"],
            "live policy target values differ",
        )
        _require(
            np.array_equal(recomputed, target_values),
            "live target column is not the exact output aggregation",
        )
        observed_value = binding["observed_value"]
        _require(
            reference["signed"]
            or (observed_value >= 0 and not (target_values < 0).any()),
            "negative policy amounts require signed=True",
        )
        _require(
            (observed_value == 0)
            or (observed_value > 0 and (target_values > 0).any())
            or (observed_value < 0 and (target_values < 0).any()),
            "observed target has no same-sign policy-derived support",
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
        json.JSONDecodeError,
    ) as exc:
        raise MonetaryBindingIntegrityError(
            f"{target.row_name}: policy monetary binding integrity failed ({exc})."
        ) from exc
