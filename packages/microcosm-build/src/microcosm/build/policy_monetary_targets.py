"""Receipted policy-derived monetary measures produced by Axiom.

This lane is intentionally separate from :mod:`microcosm.build.monetary_targets`.
The direct-measure binder must never admit a policy output merely because both
are numeric columns.  A policy-derived receipt binds the legal artifact,
runtime, input frame, parameter world, the exact requested output the Axiom
materialization receipt recorded (its period, entity, variable, rows, and
canonical typed identity), any entity aggregation, and the observed aggregate
used as the calibration target.

The hashes here detect drift; they are not an authority.  Compiling one of
these targets additionally requires a trust-root acceptance minted by
:func:`microcosm.calibrate.policy_monetary_binding.build_axiom_policy_acceptances`
from separately signed producer and observed-source artifacts, so a receipt
can never authenticate itself.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field

import numpy as np
from numpy.typing import ArrayLike

from microcosm.build.ledger_targets import LedgerTargetReference
from microcosm.build.monetary_targets import MonetaryBasis
from microcosm.calibrate import TargetSpec
from microcosm.calibrate.monetary_binding import (
    canonical_record_ids,
    monetary_digest,
)
from microcosm.calibrate.policy_monetary_binding import (
    axiom_array_identity,
    bind_materialization_output,
    validate_policy_monetary_binding_payload,
)


def _sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 identity.")


def _text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string.")


def _vector(values: ArrayLike, label: str) -> np.ndarray:
    result = np.asarray(values, dtype="<f8")
    if result.ndim != 1 or not result.size or not np.isfinite(result).all():
        raise ValueError(f"{label} must be a nonempty, finite one-dimensional vector.")
    return result


def _axiom_output_vector(values: object, label: str) -> np.ndarray:
    """Require the native dense output contract without lossy coercion."""
    if not isinstance(values, np.ndarray):
        raise TypeError(f"{label} must be a native numpy float64 array.")
    if values.dtype != np.dtype("<f8"):
        raise TypeError(
            f"{label} must be a native numpy float64 array, got dtype {values.dtype}."
        )
    if values.ndim != 1 or not values.size or not np.isfinite(values).all():
        raise ValueError(f"{label} must be a nonempty, finite one-dimensional vector.")
    return values


def _immutable_f64(values: np.ndarray) -> np.ndarray:
    return np.frombuffer(values.astype("<f8", copy=False).tobytes(), dtype="<f8")


def _immutable_i64(values: np.ndarray) -> np.ndarray:
    return np.frombuffer(values.astype("<i8", copy=False).tobytes(), dtype="<i8")


def _aligned_ids(values: ArrayLike, label: str) -> np.ndarray:
    ids = np.asarray(values)
    if ids.ndim != 1 or not ids.size or ids.dtype.kind not in "iu":
        raise ValueError(f"{label} must be a nonempty one-dimensional integer vector.")
    if ids.dtype.kind == "u" and ids.max() > np.iinfo(np.int64).max:
        raise ValueError(f"{label} must fit signed int64 without overflow.")
    return ids.astype("<i8", copy=False)


def _array_identity(values: np.ndarray) -> dict[str, object]:
    """Typed identity for one exact dense vector."""
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


@dataclass(frozen=True)
class AxiomPolicyIdentity:
    """Immutable identities for one Axiom policy-output parameter world."""

    producer_manifest_sha256: str
    rulespec_artifact_sha256: str
    axiom_runtime_sha256: str
    input_frame_sha256: str
    parameter_world_sha256: str
    materialization_receipt_sha256: str
    period: str
    output_variable: str
    output_entity: str
    target_entity: str
    target_measure: str

    def __post_init__(self) -> None:
        for name in (
            "producer_manifest_sha256",
            "rulespec_artifact_sha256",
            "axiom_runtime_sha256",
            "input_frame_sha256",
            "parameter_world_sha256",
            "materialization_receipt_sha256",
        ):
            _sha256(getattr(self, name), name)
        for name in (
            "period",
            "output_variable",
            "output_entity",
            "target_entity",
            "target_measure",
        ):
            _text(getattr(self, name), name)


@dataclass(frozen=True, eq=False)
class PolicyDerivedMonetaryMeasure:
    """Raw Axiom rows plus their factory-derived calibration projection."""

    output_values: np.ndarray = field(repr=False)
    output_record_ids: np.ndarray = field(repr=False)
    target_record_ids: np.ndarray = field(repr=False)
    output_target_ids: np.ndarray | None = field(repr=False)
    basis: MonetaryBasis
    identity: AxiomPolicyIdentity
    aggregation_membership_column: str | None
    materialization_receipt: Mapping[str, object] = field(repr=False)
    perimeter_bridge_description: str
    perimeter_bridge_source_sha256: str
    values: np.ndarray = field(init=False, repr=False)
    record_ids: np.ndarray = field(init=False, repr=False)
    aggregation_kind: str = field(init=False)
    output_identity: Mapping[str, object] = field(init=False)
    output_record_ids_identity: Mapping[str, object] = field(init=False)
    materialized_output_identity: Mapping[str, object] = field(init=False)
    materialized_record_ids_identity: Mapping[str, object] = field(init=False)
    output_target_ids_identity: Mapping[str, object] = field(init=False)
    values_identity: Mapping[str, object] = field(init=False)
    record_ids_identity: Mapping[str, object] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.basis, MonetaryBasis):
            raise TypeError("basis must be MonetaryBasis.")
        if not isinstance(self.identity, AxiomPolicyIdentity):
            raise TypeError("identity must be AxiomPolicyIdentity.")
        if self.basis.temporal_basis != "annual_flow":
            raise ValueError(
                "Policy-derived tax-benefit measures must be annual flows."
            )
        if self.identity.period != self.basis.period:
            raise ValueError(
                "Policy identity period must equal the monetary basis period."
            )
        _sha256(
            self.perimeter_bridge_source_sha256,
            "perimeter_bridge_source_sha256",
        )
        _text(self.perimeter_bridge_description, "perimeter_bridge_description")
        if not isinstance(self.materialization_receipt, Mapping):
            raise TypeError("materialization_receipt must be a mapping.")
        materialization = dict(self.materialization_receipt)

        outputs = _immutable_f64(
            _axiom_output_vector(self.output_values, "Axiom output values")
        )
        output_ids = _immutable_i64(canonical_record_ids(self.output_record_ids))
        target_ids = _immutable_i64(canonical_record_ids(self.target_record_ids))
        if outputs.shape != output_ids.shape:
            raise ValueError(
                "output_record_ids must align one-to-one with Axiom outputs."
            )
        materialized = self._bind_materialization(materialization, outputs, output_ids)

        if self.identity.output_entity == self.identity.target_entity:
            if self.output_target_ids is not None:
                raise ValueError(
                    "Same-entity policy outputs must not supply a mapping vector."
                )
            if self.aggregation_membership_column is not None:
                raise ValueError(
                    "Same-entity policy outputs must not name a membership column."
                )
            if not np.array_equal(output_ids, target_ids):
                raise ValueError(
                    "Same-entity policy output and target row identities differ."
                )
            mapped_ids = output_ids
            target_values = outputs
            aggregation_kind = "identity"
        else:
            if self.output_target_ids is None:
                raise ValueError(
                    "Cross-entity policy outputs require explicit target ids."
                )
            _text(
                self.aggregation_membership_column,
                "aggregation_membership_column",
            )
            mapped_ids = _immutable_i64(
                _aligned_ids(self.output_target_ids, "output_target_ids")
            )
            if mapped_ids.shape != output_ids.shape:
                raise ValueError(
                    "output_target_ids must align one-to-one with Axiom outputs."
                )
            target_positions = {
                int(value): index for index, value in enumerate(target_ids)
            }
            unknown = sorted(
                {int(value) for value in mapped_ids} - set(target_positions)
            )
            if unknown:
                raise ValueError(
                    "Policy output mapping names target ids absent from the target "
                    f"table: {unknown[:5]}."
                )
            unmapped = sorted(
                set(target_positions) - {int(value) for value in mapped_ids}
            )
            if unmapped:
                raise ValueError(
                    "Policy output mapping leaves target ids without output rows: "
                    f"{unmapped[:5]}."
                )
            target_values = np.zeros(len(target_ids), dtype="<f8")
            positions = np.fromiter(
                (target_positions[int(value)] for value in mapped_ids),
                dtype=np.int64,
                count=len(mapped_ids),
            )
            with np.errstate(over="raise", invalid="raise"):
                np.add.at(target_values, positions, outputs)
            if not np.isfinite(target_values).all():
                raise ValueError("Aggregated policy output contains non-finite values.")
            aggregation_kind = "sum_by_membership"

        immutable_values = _immutable_f64(target_values)
        object.__setattr__(self, "output_values", outputs)
        object.__setattr__(self, "output_record_ids", output_ids)
        object.__setattr__(self, "target_record_ids", target_ids)
        object.__setattr__(self, "output_target_ids", mapped_ids)
        object.__setattr__(self, "materialization_receipt", materialization)
        object.__setattr__(self, "values", immutable_values)
        object.__setattr__(self, "record_ids", target_ids)
        object.__setattr__(self, "aggregation_kind", aggregation_kind)
        object.__setattr__(self, "output_identity", _array_identity(outputs))
        object.__setattr__(
            self,
            "output_record_ids_identity",
            _array_identity(output_ids),
        )
        object.__setattr__(
            self,
            "output_target_ids_identity",
            _array_identity(mapped_ids),
        )
        object.__setattr__(self, "values_identity", _array_identity(immutable_values))
        object.__setattr__(self, "record_ids_identity", _array_identity(target_ids))
        object.__setattr__(
            self,
            "materialized_output_identity",
            materialized["values"],
        )
        object.__setattr__(
            self,
            "materialized_record_ids_identity",
            materialized["record_ids"],
        )

    def _bind_materialization(
        self,
        materialization: Mapping[str, object],
        outputs: np.ndarray,
        output_ids: np.ndarray,
    ) -> dict[str, object]:
        """Pin this measure to the exact output the Axiom receipt materialized.

        Requires the receipt to describe this identity's period, output entity,
        and requested output variable, then requires the values and entity rows
        it recorded to be byte-identical to the vectors being frozen here. An
        unrelated output, a different period, or an entity/variable the run
        never produced cannot reach a calibration target.
        """
        materialized = bind_materialization_output(
            materialization,
            period=self.basis.period,
            output_entity=self.identity.output_entity,
            output_variable=self.identity.output_variable,
            materialization_receipt_sha256=(
                self.identity.materialization_receipt_sha256
            ),
            input_frame_sha256=self.identity.input_frame_sha256,
            n_records=len(outputs),
        )
        if materialized["values"] != axiom_array_identity(outputs):
            raise ValueError(
                "Axiom output values differ from the materialized requested output."
            )
        if materialized["record_ids"] != axiom_array_identity(output_ids):
            raise ValueError(
                "Axiom output rows differ from the materialized entity rows."
            )
        return materialized

    def _check_vector_metadata(self) -> None:
        if (
            self.output_values.dtype != np.dtype("<f8")
            or self.output_values.ndim != 1
            or self.output_record_ids.dtype != np.dtype("<i8")
            or self.output_record_ids.shape != self.output_values.shape
            or self.output_target_ids is None
            or self.output_target_ids.dtype != np.dtype("<i8")
            or self.output_target_ids.shape != self.output_values.shape
            or self.values.dtype != np.dtype("<f8")
            or self.values.ndim != 1
            or self.record_ids.dtype != np.dtype("<i8")
            or self.record_ids.shape != self.values.shape
        ):
            raise ValueError("Policy-derived array dtype/shape metadata was mutated.")
        expected_identities = (
            (self.output_identity, _array_identity(self.output_values)),
            (
                self.output_record_ids_identity,
                _array_identity(self.output_record_ids),
            ),
            (
                self.output_target_ids_identity,
                _array_identity(self.output_target_ids),
            ),
            (self.values_identity, _array_identity(self.values)),
            (self.record_ids_identity, _array_identity(self.record_ids)),
        )
        if any(actual != expected for actual, expected in expected_identities):
            raise ValueError("Policy-derived array identity metadata was mutated.")
        materialized = self._bind_materialization(
            self.materialization_receipt,
            self.output_values,
            self.output_record_ids,
        )
        if (
            materialized["values"] != self.materialized_output_identity
            or materialized["record_ids"] != self.materialized_record_ids_identity
        ):
            raise ValueError("Axiom materialization receipt was mutated.")

    def receipt(self) -> dict[str, object]:
        """Return the self-contained policy-output derivation receipt."""
        self._check_vector_metadata()
        receipt = {
            "schema_version": 3,
            "identity": asdict(self.identity),
            "basis": asdict(self.basis),
            "output": {
                "n_records": len(self.output_values),
                "values": self.output_identity,
                "record_ids": self.output_record_ids_identity,
                "materialized_values": self.materialized_output_identity,
                "materialized_record_ids": self.materialized_record_ids_identity,
            },
            "aggregation": {
                "kind": self.aggregation_kind,
                "membership_column": self.aggregation_membership_column,
                "output_target_ids": self.output_target_ids_identity,
                "target_n_records": len(self.values),
                "target_values": self.values_identity,
                "target_record_ids": self.record_ids_identity,
            },
            "materialization": self.materialization_receipt,
            "perimeter_bridge": {
                "description": self.perimeter_bridge_description,
                "source_sha256": self.perimeter_bridge_source_sha256,
            },
            "readiness": "ready",
            "measure_kind": "policy_derived",
        }
        return {**receipt, "receipt_sha256": monetary_digest(receipt)}


def prepare_policy_derived_monetary_measure(
    output_values: np.ndarray,
    *,
    output_record_ids: ArrayLike,
    target_record_ids: ArrayLike,
    output_target_ids: ArrayLike | None,
    aggregation_membership_column: str | None,
    basis: MonetaryBasis,
    identity: AxiomPolicyIdentity,
    materialization_receipt: Mapping[str, object],
    perimeter_bridge_description: str,
    perimeter_bridge_source_sha256: str,
) -> PolicyDerivedMonetaryMeasure:
    """Freeze Axiom output rows and their explicit target-entity aggregation.

    Same-entity outputs require exact row identity and no mapping vector.
    Cross-entity outputs require one target id per output row and are summed in
    the exact order of ``target_record_ids``.  No relation direction is inferred
    from a variable or relation name.
    """
    return PolicyDerivedMonetaryMeasure(
        output_values=output_values,
        output_record_ids=np.asarray(output_record_ids),
        target_record_ids=np.asarray(target_record_ids),
        output_target_ids=(
            None if output_target_ids is None else np.asarray(output_target_ids)
        ),
        basis=basis,
        identity=identity,
        aggregation_membership_column=aggregation_membership_column,
        materialization_receipt=materialization_receipt,
        perimeter_bridge_description=perimeter_bridge_description,
        perimeter_bridge_source_sha256=perimeter_bridge_source_sha256,
    )


def bind_policy_derived_monetary_target(
    reference: LedgerTargetReference,
    *,
    value: float,
    observed_basis: MonetaryBasis,
    observed_source_assertion: str,
    observed_source_identity_sha256: str,
    prepared: PolicyDerivedMonetaryMeasure,
    source: str | None = None,
) -> TargetSpec:
    """Bind an observed aggregate to one exact Axiom-derived distribution.

    Binding is not admission: the resulting :class:`~microcosm.calibrate.TargetSpec`
    still compiles only under a trust-root
    :class:`~microcosm.calibrate.policy_monetary_binding.AxiomPolicyAcceptance`
    for its typed target key.  Scalar fields fail closed before coercion here —
    a bool or numeric string amount, a float or bool period tag, and a non-float
    ``se``/``tolerance`` are refused rather than normalized, because the
    compiled spec is later compared against this receipt by exact type.
    """
    if not isinstance(reference, LedgerTargetReference):
        raise TypeError("reference must be LedgerTargetReference.")
    if not isinstance(observed_basis, MonetaryBasis) or not isinstance(
        prepared, PolicyDerivedMonetaryMeasure
    ):
        raise TypeError("observed_basis and prepared must be typed monetary values.")
    prepared._check_vector_metadata()
    if observed_source_assertion not in {
        "observation",
        "observed",
        "derived_observation",
    }:
        raise ValueError("Policy-derived monetary targets require observed aggregates.")
    if observed_basis != prepared.basis:
        raise ValueError("Observed and policy-derived monetary bases differ.")
    if reference.entity != prepared.identity.target_entity:
        raise ValueError("Reference entity differs from the policy target entity.")
    if reference.measure != prepared.identity.target_measure:
        raise ValueError("Reference measure differs from the prepared target measure.")
    if reference.filter is not None:
        raise ValueError(
            "Policy-derived monetary filters must be materialized upstream."
        )
    if (
        reference.value_operation != "identity"
        or reference.assertion_policy != "observed_only"
        or reference.period_match_policy != "exact"
        or any(
            item is not None
            for item in (
                reference.uprating_index,
                reference.uprating_from_period,
                reference.uprating_to_period,
            )
        )
    ):
        raise ValueError(
            "Policy-derived targets do not permit implicit transformations."
        )
    if type(reference.period) is not int and type(reference.period) is not str:
        raise ValueError(
            "Reference period must be an explicit int or str period tag; a bool "
            "or float tag is refused rather than coerced."
        )
    if str(reference.period) != observed_basis.period:
        raise ValueError("Reference period differs from the policy-output period.")
    if type(reference.signed) is not bool:
        raise ValueError("Reference signed must be an explicit boolean.")
    for name in ("se", "tolerance"):
        declared = getattr(reference, name)
        if declared is not None and type(declared) is not float:
            raise ValueError(
                f"Reference {name} must be an explicit float or None: the compiled "
                "TargetSpec stores floats, so any other numeric type would drift "
                "from the receipt it is checked against."
            )
    if type(value) is not int and type(value) is not float:
        raise ValueError(
            "Observed target amount must be an int or float, got "
            f"{type(value).__name__}; booleans and numeric strings are refused "
            "rather than coerced."
        )
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Observed target amount must be finite.")
    if not reference.signed and (value < 0 or (prepared.values < 0).any()):
        raise ValueError("Negative policy amounts require reference signed=True.")
    if (value > 0 and not (prepared.values > 0).any()) or (
        value < 0 and not (prepared.values < 0).any()
    ):
        raise ValueError("Observed target has no same-sign policy-derived support.")
    _sha256(observed_source_identity_sha256, "observed_source_identity_sha256")

    metadata = reference.metadata
    reserved = {
        "policy_monetary_binding",
        "policy_monetary_binding_sha256",
        "monetary_source_activation_status",
    }
    conflicts = reserved.intersection(metadata)
    if conflicts:
        raise ValueError(
            "Reference metadata may not predeclare generated policy binding fields: "
            f"{sorted(conflicts)}."
        )
    if metadata.get("monetary_target_role", "calibration") != "calibration":
        raise ValueError("Only calibration references may bind to policy outputs.")
    if metadata.get("measure_kind") != "policy_derived":
        raise ValueError("Reference measure_kind must be policy_derived.")
    if metadata.get("activation_status") not in {
        "requires_policy_output",
        "ready",
        "active",
    }:
        raise ValueError("Reference is not ready for an authenticated policy output.")

    source = (
        source
        or reference.source
        or reference.ledger_source_record_id
        or reference.ledger_fact_key
    )
    if not isinstance(source, str) or not source.strip():
        raise ValueError("Resolved observed-target source citation is required.")
    bound_metadata = {
        **metadata,
        "activation_status": "active",
        "monetary_source_activation_status": metadata.get(
            "activation_status", "requires_policy_output"
        ),
        "monetary_target_role": "calibration",
    }
    source_reference = asdict(reference)
    binding = {
        "reference": {**source_reference, "metadata": bound_metadata},
        "source_reference": source_reference,
        "observed_value": value,
        "observed_source": source,
        "observed_source_assertion": observed_source_assertion,
        "observed_source_identity_sha256": observed_source_identity_sha256,
        "observed_basis": asdict(observed_basis),
        "prepared": prepared.receipt(),
    }
    validate_policy_monetary_binding_payload(binding)
    return TargetSpec(
        name=reference.name,
        entity=reference.entity,
        measure=reference.measure or "",
        value=value,
        filter=None,
        period=reference.period,
        source=source,
        family=reference.family,
        signed=reference.signed,
        se=reference.se,
        tolerance=reference.tolerance,
        notes=reference.notes,
        metadata={
            **bound_metadata,
            "policy_monetary_binding": json.dumps(
                binding, sort_keys=True, allow_nan=False
            ),
            "policy_monetary_binding_sha256": monetary_digest(binding),
        },
    )
