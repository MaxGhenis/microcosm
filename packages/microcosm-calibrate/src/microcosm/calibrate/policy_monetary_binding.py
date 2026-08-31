"""Integrity checks for Axiom policy-derived monetary calibration rows.

A policy-derived row carries a receipt, and a receipt is a drift detector, not
an authority: anything a target carries is attacker-controlled input. Three
separate authorities therefore have to agree before such a row compiles.

* **The trust root.** :class:`AxiomPolicyTrustRoot` holds operator-supplied
  verification keys that never come from a target, a receipt, or a registry.
  :func:`build_axiom_policy_acceptances` authenticates one *signed producer*
  artifact and one *signed observed-source* artifact per row under those keys
  and mints :class:`AxiomPolicyAcceptance` values. Acceptances cannot be
  constructed by callers — each carries a seal under a process-private key held
  only by this module — so a fabricated target can never mint its own
  admission, and the accepted set is pinned by typed
  :attr:`~microcosm.calibrate.target.Target.key`, so it can be neither trimmed
  nor extended.
* **The materialization receipt.** The Axiom receipt is bound to the exact
  target period, output entity, requested output variable, row identities, and
  canonical typed output identity — at preparation, on the serialized payload,
  and again against the live frame. An unrelated output, a different period, or
  an absent entity/variable cannot satisfy a policy target.
* **The live frame.** Every recorded identity is recomputed from the frame the
  compiler is about to use.

Types fail closed before coercion throughout: a serialized ``[3.0]`` shape, an
``int`` standing in for a ``bool``, a ``float`` period standing in for an
``int`` period, and a numeric string standing in for a number are all rejected
rather than silently normalized.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import secrets
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Any

import numpy as np

from microcosm.calibrate.monetary_binding import (
    MonetaryBindingIntegrityError,
    monetary_digest,
)
from microcosm.calibrate.target import Target
from microcosm.frame import Frame

__all__ = [
    "AxiomPolicyAcceptance",
    "AxiomPolicyAcceptanceSet",
    "AxiomPolicyTarget",
    "AxiomPolicyTrustRoot",
    "axiom_array_identity",
    "axiom_policy_target_rows",
    "bind_materialization_output",
    "canonical_policy_record_ids",
    "has_policy_semantics",
    "build_axiom_policy_acceptances",
    "normalize_policy_acceptances",
    "policy_array_identity",
    "sign_axiom_policy_attestation",
    "validate_policy_monetary_binding_payload",
    "verify_policy_monetary_binding",
    "verify_policy_monetary_target_spec",
]

#: Receipt keys a policy-derived target carries in its metadata.
POLICY_RECEIPT_KEYS = frozenset(
    {"policy_monetary_binding", "policy_monetary_binding_sha256"}
)
_RECEIPT_KEYS = POLICY_RECEIPT_KEYS
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
#: Identity hashes an acceptance pins against the signed producer artifact.
IDENTITY_HASH_KEYS = (
    "producer_manifest_sha256",
    "rulespec_artifact_sha256",
    "axiom_runtime_sha256",
    "input_frame_sha256",
    "parameter_world_sha256",
    "materialization_receipt_sha256",
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
_OUTPUT_KEYS = frozenset(
    {
        "n_records",
        "values",
        "record_ids",
        "materialized_values",
        "materialized_record_ids",
    }
)
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

#: Schema-v2 Axiom receipt structures this module pins a policy target to. The
#: frame adapter owns them; they are restated here so the calibrate shard never
#: depends on that module's private helpers to authenticate a receipt.
_MATERIALIZATION_KEYS = frozenset(
    {
        "schema_version",
        "receipt_kind",
        "period",
        "arithmetic",
        "entities",
        "input_frame_sha256",
        "receipt_sha256",
    }
)
_MATERIALIZATION_ENTITY_KEYS = frozenset(
    {
        "frame_entity",
        "engine_entity",
        "current_id_column",
        "current_ids",
        "declared_root_inputs",
        "provided_root_inputs",
        "relations",
        "requested_outputs",
    }
)
_MATERIALIZATION_OUTPUT_KEYS = frozenset(
    {
        "declared_engine_dtype",
        "declared_kernel_dtype",
        "declared_period",
        "values",
    }
)
_PERIOD_KEYS = frozenset({"kind", "start", "end"})
_AXIOM_ARRAY_IDENTITY_KEYS = frozenset(
    {"dtype", "storage_dtype", "encoding", "shape", "sha256"}
)
_AXIOM_ARRAY_ENCODING = "little_endian_raw_v1"
_AXIOM_TEXT_ENCODING = "canonical_json_utf8_v1"

#: Signed artifact envelopes the trust root authenticates.
_ATTESTATION_KEYS = frozenset({"document", "signature"})
_PRODUCER_ATTESTATION_KEYS = frozenset(
    {
        "schema_version",
        "artifact_kind",
        "trust_root_id",
        "period",
        "targets",
        *IDENTITY_HASH_KEYS,
    }
)
_PRODUCER_TARGET_KEYS = frozenset(
    {"name", "period", "binding_sha256", "prepared_receipt_sha256"}
)
_OBSERVATION_ATTESTATION_KEYS = frozenset(
    {
        "schema_version",
        "artifact_kind",
        "trust_root_id",
        "name",
        "period",
        "observed_source_identity_sha256",
        "observed_value",
        "observed_source",
    }
)
PRODUCER_ARTIFACT_KIND = "axiom_policy_producer_attestation"
OBSERVATION_ARTIFACT_KIND = "axiom_policy_observation_attestation"

#: Process-private seal key. It exists only in this module's namespace, so an
#: acceptance can be minted only by :func:`build_axiom_policy_acceptances`.
_SEAL_KEY = secrets.token_bytes(32)


class AxiomPolicyTarget(Target):
    """Nominal target type preserving policy provenance outside metadata.

    Policy binding receipts remain serialized in :attr:`Target.metadata`, but
    metadata is deliberately an ordinary mapping and therefore cannot be the
    only signal that a row originated at the authenticated policy boundary.
    :class:`~microcosm.calibrate.registry.TargetSpec` emits this subtype after
    validating a policy receipt.  ``dataclasses.replace(target, metadata={})``
    preserves the concrete type, so stripping every receipt and marker cannot
    demote an accepted policy row into an ordinary calibration target.

    The subtype adds no fields and does not change the public ``Target``
    constructor or matrix API.  It is an integrity classification, not an
    acceptance: a complete receipt and a separately trust-root-minted
    :class:`AxiomPolicyAcceptance` are still required at compilation.
    """


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _hash(value: object, label: str) -> None:
    _require(
        type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
        f"invalid {label}",
    )


def _same(actual: object, expected: object) -> bool:
    """Exact equality that refuses cross-type coercion.

    ``True``/``1``, ``2024``/``2024.0``, and ``1``/``"1"`` are distinct values
    here: a receipt field must match the runtime field in type as well as
    value, so a serialized shape of ``[3.0]`` or a ``float`` period tag cannot
    impersonate the typed identity it is compared against.
    """
    if actual is None or expected is None:
        return actual is None and expected is None
    if type(actual) is not type(expected):
        return False
    return bool(actual == expected)


def _typed_period(value: object, label: str) -> int | str:
    """Require the ``int``/``str`` period tag a target identity is keyed by."""
    if type(value) is int or type(value) is str:
        return value
    raise ValueError(f"{label} must be an int or str period tag")


def _typed_target_key(value: object, label: str) -> tuple[str, int | str]:
    """Require a typed ``(name, period)`` target identity."""
    if isinstance(value, (tuple, list)) and len(value) == 2:
        name, period = value
        if type(name) is str and name:
            return (name, _typed_period(period, f"{label} period"))
    raise ValueError(f"{label} must be a typed (name, period) target key")


def _exact_mapping(value: object, keys: frozenset[str], label: str) -> dict:
    _require(isinstance(value, dict), f"{label} must be an object")
    actual = set(value)
    _require(
        actual == keys,
        f"{label} keys differ: expected {sorted(keys)}, got {sorted(actual)}",
    )
    return value


def _require_shape(value: object, length: int, label: str) -> None:
    _require(
        type(value) is list
        and len(value) == 1
        and type(value[0]) is int
        and value[0] == length,
        f"invalid {label} shape",
    )


def _validate_basis(value: object, label: str) -> dict:
    basis = _exact_mapping(value, _BASIS_KEYS, label)
    _require(
        type(basis["currency"]) is str
        and re.fullmatch(r"[A-Z]{3}", basis["currency"]) is not None,
        f"invalid {label} currency",
    )
    _require(_same(basis["unit"], "base_currency"), f"invalid {label} unit")
    _require(
        _same(basis["temporal_basis"], "annual_flow"), f"invalid {label} time basis"
    )
    period = basis["period"]
    _require(
        type(period) is str and re.fullmatch(r"[0-9]{4}", period) is not None,
        f"invalid {label} period",
    )
    date(int(period), 1, 1)
    for key in ("sector", "perimeter", "valuation"):
        _require(
            type(basis[key]) is str and basis[key].strip(),
            f"invalid {label} {key}",
        )
    return basis


def _id_key(value: object) -> object:
    """Return the stable Python key for one canonical NumPy entity ID."""
    return value.item() if isinstance(value, np.generic) else value


def canonical_policy_record_ids(
    values: object,
    label: str = "record_ids",
    *,
    unique: bool = True,
) -> np.ndarray:
    """Return immutable canonical integer or string entity IDs.

    This mirrors the Axiom relation adapter's two supported ID families:
    integers become signed little-endian int64 and text becomes a native NumPy
    Unicode vector. Object arrays are admitted only when every element belongs
    to one of those families. Booleans, floats, bytes mixed with text, and
    integer/string mixtures fail closed rather than being stringified.
    """
    array = np.asarray(values)
    _require(
        array.ndim == 1 and array.size > 0,
        f"{label} must be a nonempty one-dimensional ID vector",
    )
    kind = array.dtype.kind
    if kind in ("i", "u"):
        if kind == "u":
            _require(
                array.max() <= np.iinfo(np.int64).max,
                f"{label} contains an ID outside signed int64 range",
            )
        canonical = np.frombuffer(
            array.astype("<i8", copy=False).tobytes(), dtype="<i8"
        )
    elif kind in ("U", "S"):
        canonical = np.array([str(item) for item in array.tolist()], dtype=str)
        canonical.setflags(write=False)
    elif kind == "O":
        items = array.tolist()
        if all(isinstance(item, str) for item in items):
            canonical = np.array(items, dtype=str)
            canonical.setflags(write=False)
        elif all(
            isinstance(item, (int, np.integer))
            and not isinstance(item, (bool, np.bool_))
            for item in items
        ):
            _require(
                all(
                    np.iinfo(np.int64).min <= int(item) <= np.iinfo(np.int64).max
                    for item in items
                ),
                f"{label} contains an ID outside signed int64 range",
            )
            canonical = np.frombuffer(
                np.asarray([int(item) for item in items], dtype="<i8").tobytes(),
                dtype="<i8",
            )
        else:
            raise ValueError(
                f"{label} must contain only integer IDs or only string IDs"
            )
    else:
        raise ValueError(f"{label} must contain only integer IDs or only string IDs")
    if unique:
        keys = [_id_key(value) for value in canonical]
        _require(len(set(keys)) == len(keys), f"{label} must contain unique IDs")
    return canonical


def _id_family(values: np.ndarray) -> str:
    kind = np.asarray(values).dtype.kind
    if kind == "i":
        return "integer"
    if kind == "U":
        return "string"
    raise ValueError("policy record IDs are not in a canonical ID family")


def policy_array_identity(values: np.ndarray) -> dict[str, object]:
    """Policy-local typed identity for one exact numeric or text vector."""
    array = np.asarray(values)
    _require(array.ndim == 1, "policy receipt vectors must be one-dimensional")
    if array.dtype.kind == "U":
        dtype = "string"
        payload = json.dumps(
            array.tolist(), ensure_ascii=True, separators=(",", ":")
        ).encode("utf-8")
    elif array.dtype.kind in "biuf":
        array = np.ascontiguousarray(array)
        dtype = array.dtype.str
        payload = array.tobytes()
    else:
        raise ValueError("policy receipt vectors must be numeric or canonical strings")
    header = json.dumps(
        {"dtype": dtype, "shape": list(array.shape)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return {
        "dtype": dtype,
        "shape": [int(size) for size in array.shape],
        "sha256": hashlib.sha256(header + b"\n" + payload).hexdigest(),
    }


_array_identity = policy_array_identity


def axiom_array_identity(values: np.ndarray) -> dict[str, object]:
    """Recompute the schema-v2 Axiom receipt identity for a value vector.

    Mirrors the frame adapter's canonical numeric encoding — semantic dtype
    name, little-endian storage dtype, ``little_endian_raw_v1`` payload — so a
    policy receipt can be pinned to the exact requested output the
    materialization receipt recorded, without depending on that module's
    private helpers. Monetary outputs remain float64; entity rows may use
    either canonical int64 or canonical string IDs.
    """
    array = np.ascontiguousarray(np.asarray(values))
    if array.ndim != 1:
        raise ValueError("Axiom policy receipt vectors must be one-dimensional arrays.")
    if array.dtype.kind in "biuf":
        storage = np.ascontiguousarray(
            array.astype(array.dtype.newbyteorder("<"), copy=False)
        )
        semantic_dtype = array.dtype.name
        storage_dtype = storage.dtype.str
        encoding = _AXIOM_ARRAY_ENCODING
        payload_bytes = storage.tobytes()
    elif array.dtype.kind in ("U", "S", "O"):
        items = array.tolist()
        if any(not isinstance(item, str) for item in items):
            raise ValueError("Axiom policy text ID vectors must contain only strings.")
        semantic_dtype = "string"
        storage_dtype = "utf8"
        encoding = _AXIOM_TEXT_ENCODING
        payload_bytes = json.dumps(
            items,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
    else:
        raise ValueError(
            f"Axiom policy receipt cannot canonicalize dtype {array.dtype!s}."
        )
    header = {
        "dtype": semantic_dtype,
        "storage_dtype": storage_dtype,
        "encoding": encoding,
        "shape": [int(size) for size in array.shape],
    }
    payload = json.dumps(
        header,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return {
        **header,
        "sha256": hashlib.sha256(payload + b"\n" + payload_bytes).hexdigest(),
    }


def _validate_array_identity(
    value: object,
    *,
    label: str,
    dtype: str,
    length: int,
) -> dict:
    identity = _exact_mapping(value, _ARRAY_IDENTITY_KEYS, label)
    _require(_same(identity["dtype"], dtype), f"invalid {label} dtype")
    _require_shape(identity["shape"], length, label)
    _hash(identity["sha256"], label)
    return identity


def _validate_record_id_identity(
    value: object,
    *,
    label: str,
    length: int,
) -> dict:
    """Validate the policy receipt's canonical integer/string ID identity."""
    identity = _exact_mapping(value, _ARRAY_IDENTITY_KEYS, label)
    _require(
        _same(identity["dtype"], "<i8") or _same(identity["dtype"], "string"),
        f"invalid {label} ID dtype",
    )
    _require_shape(identity["shape"], length, label)
    _hash(identity["sha256"], label)
    return identity


def _validate_axiom_array_identity(
    value: object,
    *,
    label: str,
    dtype: str,
    storage_dtype: str,
    length: int,
) -> dict:
    identity = _exact_mapping(value, _AXIOM_ARRAY_IDENTITY_KEYS, label)
    _require(_same(identity["dtype"], dtype), f"invalid {label} dtype")
    _require(
        _same(identity["storage_dtype"], storage_dtype),
        f"invalid {label} storage dtype",
    )
    _require(
        _same(identity["encoding"], _AXIOM_ARRAY_ENCODING),
        f"invalid {label} encoding",
    )
    _require_shape(identity["shape"], length, label)
    _hash(identity["sha256"], label)
    return identity


def _validate_axiom_record_id_identity(
    value: object,
    *,
    label: str,
    length: int,
) -> dict:
    """Validate one canonical Axiom integer or string entity-ID identity."""
    identity = _exact_mapping(value, _AXIOM_ARRAY_IDENTITY_KEYS, label)
    numeric = (
        _same(identity["dtype"], "int64")
        and _same(identity["storage_dtype"], "<i8")
        and _same(identity["encoding"], _AXIOM_ARRAY_ENCODING)
    )
    text = (
        _same(identity["dtype"], "string")
        and _same(identity["storage_dtype"], "utf8")
        and _same(identity["encoding"], _AXIOM_TEXT_ENCODING)
    )
    _require(numeric or text, f"invalid {label} ID encoding")
    _require_shape(identity["shape"], length, label)
    _hash(identity["sha256"], label)
    return identity


def _identity_id_family(identity: Mapping[str, object]) -> str:
    dtype = identity["dtype"]
    if _same(dtype, "<i8") or _same(dtype, "int64"):
        return "integer"
    if _same(dtype, "string"):
        return "string"
    raise ValueError("record ID identity is not in a supported family")


def bind_materialization_output(
    materialization: object,
    *,
    period: str,
    output_entity: str,
    output_variable: str,
    materialization_receipt_sha256: str,
    input_frame_sha256: str,
    n_records: int,
) -> dict[str, object]:
    """Bind one Axiom materialization receipt to one exact requested output.

    Authenticates the receipt's closed structure and digest, then requires it to
    describe *this* target period, *this* output entity, and *this* requested
    output variable over exactly ``n_records`` rows. Returns the canonical typed
    identities the receipt recorded for that variable's values and that entity's
    row IDs, so callers can compare them against the arrays they hold — prepared
    vectors, a serialized receipt, or a live frame column. A receipt for an
    unrelated output, a different period, or an entity/variable it never ran
    cannot pass.

    Args:
        materialization: The schema-v2 Axiom materialization receipt.
        period: The four-digit target period the policy row calibrates.
        output_entity: Frame entity the requested output was computed on.
        output_variable: The requested output variable name.
        materialization_receipt_sha256: Identity hash the policy row claims.
        input_frame_sha256: Input-frame projection hash the policy row claims.
        n_records: Number of output rows the policy row claims.

    Returns:
        ``{"values": ..., "record_ids": ..., "id_column": ...}``.

    Raises:
        ValueError: If any of the above does not hold exactly.
    """
    receipt = _exact_mapping(
        materialization, _MATERIALIZATION_KEYS, "materialization receipt"
    )
    _require(
        _same(receipt["schema_version"], 2),
        "unsupported materialization receipt version",
    )
    _require(
        _same(receipt["receipt_kind"], "axiom_dense_materialization"),
        "invalid materialization receipt kind",
    )
    _require(
        receipt["arithmetic"] in ("decimal", "f64"),
        "invalid materialization arithmetic mode",
    )
    _hash(receipt["receipt_sha256"], "materialization receipt_sha256")
    _hash(receipt["input_frame_sha256"], "materialization input_frame_sha256")
    raw = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    _require(
        monetary_digest(raw) == receipt["receipt_sha256"],
        "materialization receipt hash differs",
    )
    _require(
        _same(receipt["receipt_sha256"], materialization_receipt_sha256),
        "materialization receipt differs from policy identity",
    )
    _require(
        _same(receipt["input_frame_sha256"], input_frame_sha256),
        "materialization input frame differs from policy identity",
    )
    period_receipt = _exact_mapping(
        receipt["period"], _PERIOD_KEYS, "materialization period"
    )
    _require(
        _same(period_receipt["kind"], "calendar_year"),
        "an annual policy measure requires a calendar-year materialization",
    )
    _require(
        _same(period_receipt["start"], f"{period}-01-01")
        and _same(period_receipt["end"], f"{period}-12-31"),
        "materialization period differs from the policy target period",
    )
    entities = receipt["entities"]
    _require(
        isinstance(entities, dict) and bool(entities),
        "materialization receipt needs executed entities",
    )
    _require(
        output_entity in entities,
        "materialization receipt omits the policy output entity",
    )
    entity = _exact_mapping(
        entities[output_entity],
        _MATERIALIZATION_ENTITY_KEYS,
        "materialization output entity",
    )
    _require(
        _same(entity["frame_entity"], output_entity),
        "materialization entity identity differs from the policy identity",
    )
    _require(
        type(entity["current_id_column"]) is str
        and entity["current_id_column"].strip(),
        "invalid materialization entity id column",
    )
    outputs = entity["requested_outputs"]
    _require(
        isinstance(outputs, dict) and bool(outputs),
        "materialization receipt needs requested outputs",
    )
    _require(
        output_variable in outputs,
        "materialization receipt omits the requested policy output variable",
    )
    output = _exact_mapping(
        outputs[output_variable],
        _MATERIALIZATION_OUTPUT_KEYS,
        "materialization requested output",
    )
    _require(
        _same(output["declared_period"], "year"),
        "an annual policy measure requires an annual requested output",
    )
    values = _validate_axiom_array_identity(
        output["values"],
        label="materialized policy output values",
        dtype="float64",
        storage_dtype="<f8",
        length=n_records,
    )
    record_ids = _validate_axiom_record_id_identity(
        entity["current_ids"],
        label="materialized policy output record ids",
        length=n_records,
    )
    return {
        "values": values,
        "record_ids": record_ids,
        "id_column": entity["current_id_column"],
    }


@dataclass(frozen=True)
class AxiomPolicyTrustRoot:
    """Operator-held verification keys for Axiom policy artifacts.

    The keys never come from a target, a receipt, or a registry: an operator
    supplies them from the release environment, which is exactly what makes the
    acceptance a trust-root judgment rather than a target's self-attestation.
    Producer and observed-source artifacts are authenticated under *separate*
    keys, so a compromised producer lane cannot also mint the observation that
    justifies a target's value.

    Attributes:
        trust_root_id: Stable label for the operator trust root, recorded on
            every acceptance it mints.
        producer_verification_key: Key for producer attestations (>= 32 bytes).
        observation_verification_key: Key for observed-source attestations
            (>= 32 bytes, and never equal to the producer key).
    """

    trust_root_id: str
    producer_verification_key: bytes
    observation_verification_key: bytes

    def __post_init__(self) -> None:
        _require(
            type(self.trust_root_id) is str and bool(self.trust_root_id.strip()),
            "AxiomPolicyTrustRoot.trust_root_id must be a nonempty string.",
        )
        for name in ("producer_verification_key", "observation_verification_key"):
            key = getattr(self, name)
            _require(
                isinstance(key, (bytes, bytearray)) and len(key) >= 32,
                f"AxiomPolicyTrustRoot.{name} must be at least 32 bytes.",
            )
            object.__setattr__(self, name, bytes(key))
        _require(
            not hmac.compare_digest(
                self.producer_verification_key,
                self.observation_verification_key,
            ),
            "AxiomPolicyTrustRoot producer and observation keys must differ.",
        )


def sign_axiom_policy_attestation(
    document: Mapping[str, object],
    key: bytes,
) -> str:
    """Return the detached HMAC-SHA256 signature of an attestation document.

    Producers and observed-source ingest lanes call this with the operator key
    they hold; :func:`build_axiom_policy_acceptances` recomputes it with the
    trust root's key. Holding the key is the whole authority — the signature is
    over the document's canonical JSON, so no field can move afterwards.
    """
    _require(isinstance(document, Mapping), "attestation document must be an object.")
    _require(
        isinstance(key, (bytes, bytearray)) and len(key) >= 32,
        "attestation signing key must be at least 32 bytes.",
    )
    payload = json.dumps(
        dict(document),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hmac.new(bytes(key), payload, hashlib.sha256).hexdigest()


def _seal(fields: Mapping[str, object]) -> str:
    payload = json.dumps(
        dict(fields),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hmac.new(_SEAL_KEY, payload, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class AxiomPolicyAcceptance:
    """One trust-root admission of one policy-derived calibration target.

    Callers cannot construct this: ``seal`` is an HMAC under a process-private
    key held only by this module, so the only way to obtain an acceptance is
    :func:`build_axiom_policy_acceptances` verifying signed producer and
    observed-source artifacts. Every pin therefore originates outside the
    target it admits, and :attr:`accepted_target_keys` fixes the exact set of
    typed target keys the same verification admitted, so an acceptance cannot
    be moved to another target, silently dropped, or joined by an extra row.

    Acceptances are in-process values: they intentionally do not survive
    pickling or a process boundary, because the seal key does not either.
    """

    target_key: tuple[str, int | str]
    accepted_target_keys: tuple[tuple[str, int | str], ...]
    trust_root_id: str
    binding_sha256: str
    prepared_receipt_sha256: str
    producer_manifest_sha256: str
    rulespec_artifact_sha256: str
    axiom_runtime_sha256: str
    input_frame_sha256: str
    parameter_world_sha256: str
    materialization_receipt_sha256: str
    observed_source_identity_sha256: str
    observed_value: float
    observed_source: str
    seal: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_key",
            _typed_target_key(self.target_key, "AxiomPolicyAcceptance.target_key"),
        )
        keys = self.accepted_target_keys
        _require(
            isinstance(keys, (tuple, list)) and bool(keys),
            "AxiomPolicyAcceptance.accepted_target_keys must be a nonempty tuple.",
        )
        accepted = tuple(
            _typed_target_key(key, "AxiomPolicyAcceptance.accepted_target_keys")
            for key in keys
        )
        _require(
            len(set(accepted)) == len(accepted),
            "AxiomPolicyAcceptance.accepted_target_keys must be unique.",
        )
        _require(
            accepted == tuple(sorted(accepted, key=repr)),
            "AxiomPolicyAcceptance.accepted_target_keys must be canonically ordered.",
        )
        _require(
            self.target_key in accepted,
            "AxiomPolicyAcceptance.target_key must belong to the accepted set.",
        )
        object.__setattr__(self, "accepted_target_keys", accepted)
        _require(
            type(self.trust_root_id) is str and bool(self.trust_root_id.strip()),
            "AxiomPolicyAcceptance.trust_root_id must be a nonempty string.",
        )
        for name in (
            "binding_sha256",
            "prepared_receipt_sha256",
            "observed_source_identity_sha256",
            *IDENTITY_HASH_KEYS,
        ):
            _hash(getattr(self, name), f"AxiomPolicyAcceptance.{name}")
        _require(
            type(self.observed_value) is float and math.isfinite(self.observed_value),
            "AxiomPolicyAcceptance.observed_value must be a finite float.",
        )
        _require(
            type(self.observed_source) is str and bool(self.observed_source.strip()),
            "AxiomPolicyAcceptance.observed_source must be a nonempty string.",
        )
        _require(
            type(self.seal) is str
            and re.fullmatch(r"[0-9a-f]{64}", self.seal) is not None,
            "AxiomPolicyAcceptance.seal must be a lowercase SHA-256 identity.",
        )
        _require(
            hmac.compare_digest(self.seal, _seal(self._sealed_fields())),
            "AxiomPolicyAcceptance must be minted by a trust-root verification of "
            "signed producer and observed-source artifacts "
            "(build_axiom_policy_acceptances); it cannot be constructed directly.",
        )

    def _sealed_fields(self) -> dict[str, object]:
        return {
            "target_key": list(self.target_key),
            "accepted_target_keys": [list(key) for key in self.accepted_target_keys],
            "trust_root_id": self.trust_root_id,
            "binding_sha256": self.binding_sha256,
            "prepared_receipt_sha256": self.prepared_receipt_sha256,
            **{name: getattr(self, name) for name in IDENTITY_HASH_KEYS},
            "observed_source_identity_sha256": self.observed_source_identity_sha256,
            "observed_value": self.observed_value,
            "observed_source": self.observed_source,
        }


def _require_sealed(acceptance: AxiomPolicyAcceptance) -> None:
    """Re-check the seal at use time, after any post-construction tampering."""
    unsealed = "the supplied Axiom policy acceptance is not trust-root sealed"
    if (
        not isinstance(acceptance, AxiomPolicyAcceptance)
        or type(acceptance.seal) is not str
    ):
        raise ValueError(unsealed)
    try:
        expected = _seal(acceptance._sealed_fields())
    except (AttributeError, TypeError, ValueError):
        raise ValueError(unsealed) from None
    _require(hmac.compare_digest(acceptance.seal, expected), unsealed)


@dataclass(frozen=True)
class AxiomPolicyAcceptanceSet:
    """The exact set of policy targets one trust-root verification admitted.

    The set is keyed by the typed
    :attr:`~microcosm.calibrate.target.Target.key` — never the lossy
    ``name@period`` display label, under which the distinct targets
    ``("t", 2024)`` and ``("t", "2024")`` collide.
    """

    trust_root_id: str
    acceptances: Mapping[tuple[str, int | str], AxiomPolicyAcceptance]

    def __post_init__(self) -> None:
        _require(
            type(self.trust_root_id) is str and bool(self.trust_root_id.strip()),
            "AxiomPolicyAcceptanceSet.trust_root_id must be a nonempty string.",
        )
        _require(
            isinstance(self.acceptances, Mapping) and bool(self.acceptances),
            "AxiomPolicyAcceptanceSet needs at least one acceptance.",
        )
        resolved: dict[tuple[str, int | str], AxiomPolicyAcceptance] = {}
        for key, acceptance in self.acceptances.items():
            _require(
                isinstance(acceptance, AxiomPolicyAcceptance),
                "policy acceptances must be AxiomPolicyAcceptance values.",
            )
            _require_sealed(acceptance)
            typed = _typed_target_key(key, "policy acceptance key")
            _require(
                typed == acceptance.target_key
                and type(typed[1]) is type(acceptance.target_key[1]),
                f"policy acceptance for {acceptance.target_key!r} is filed under "
                f"the wrong target key {typed!r}.",
            )
            _require(
                _same(acceptance.trust_root_id, self.trust_root_id),
                "policy acceptances mix trust roots.",
            )
            resolved[typed] = acceptance
        expected = tuple(sorted(resolved, key=repr))
        for acceptance in resolved.values():
            _require(
                acceptance.accepted_target_keys == expected,
                "the supplied policy acceptances are not the exact accepted set: "
                f"expected {list(acceptance.accepted_target_keys)}, got "
                f"{list(expected)}.",
            )
        object.__setattr__(self, "acceptances", MappingProxyType(resolved))

    @classmethod
    def from_mapping(cls, value: object) -> AxiomPolicyAcceptanceSet:
        """Rebuild and revalidate a set from a plain ``Target.key`` mapping."""
        _require(
            isinstance(value, Mapping) and bool(value),
            "policy acceptances must be a nonempty mapping keyed by Target.key.",
        )
        roots = set()
        for acceptance in value.values():
            _require(
                isinstance(acceptance, AxiomPolicyAcceptance),
                "policy acceptances must be AxiomPolicyAcceptance values.",
            )
            roots.add(acceptance.trust_root_id)
        _require(len(roots) == 1, "policy acceptances mix trust roots.")
        return cls(trust_root_id=roots.pop(), acceptances=dict(value))

    def get(self, key: object) -> AxiomPolicyAcceptance | None:
        try:
            return self.acceptances.get(key)  # type: ignore[arg-type]
        except TypeError:
            return None

    def keys(self) -> tuple[tuple[str, int | str], ...]:
        return tuple(self.acceptances)

    def __contains__(self, key: object) -> bool:
        return key in self.acceptances

    def __len__(self) -> int:
        return len(self.acceptances)


def normalize_policy_acceptances(value: object) -> AxiomPolicyAcceptanceSet | None:
    """Coerce a compiler argument into a revalidated acceptance set."""
    if value is None:
        return None
    if isinstance(value, (AxiomPolicyAcceptanceSet, Mapping)):
        if isinstance(value, Mapping) and any(isinstance(key, str) for key in value):
            raise TypeError(
                "policy_acceptances is keyed by the typed Target.key "
                "(name, period) pair, not the lossy 'name@period' row label: "
                "periods 2024 and '2024' are distinct targets that share a row "
                "label."
            )
        # Rebuild from the raw pairs either way: a set handed across a call
        # boundary is revalidated, seals included, before it can admit a row.
        pairs = (
            dict(value.acceptances)
            if isinstance(value, AxiomPolicyAcceptanceSet)
            else dict(value)
        )
        try:
            return AxiomPolicyAcceptanceSet.from_mapping(pairs)
        except (TypeError, ValueError) as exc:
            raise MonetaryBindingIntegrityError(
                f"Axiom policy acceptances are invalid ({exc})."
            ) from exc
    raise TypeError(
        "policy_acceptances must be an AxiomPolicyAcceptanceSet or a mapping "
        "from Target.key to AxiomPolicyAcceptance."
    )


def _verify_attestation(
    attestation: object,
    *,
    key: bytes,
    keys: frozenset[str],
    artifact_kind: str,
    trust_root_id: str,
    label: str,
) -> dict[str, object]:
    envelope = _exact_mapping(attestation, _ATTESTATION_KEYS, f"{label} attestation")
    signature = envelope["signature"]
    _require(
        type(signature) is str and re.fullmatch(r"[0-9a-f]{64}", signature) is not None,
        f"invalid {label} attestation signature",
    )
    document = _exact_mapping(envelope["document"], keys, f"{label} attestation body")
    _require(
        hmac.compare_digest(signature, sign_axiom_policy_attestation(document, key)),
        f"{label} attestation signature does not verify under the trust root key",
    )
    _require(
        _same(document["schema_version"], 1),
        f"unsupported {label} attestation version",
    )
    _require(
        _same(document["artifact_kind"], artifact_kind),
        f"invalid {label} attestation kind",
    )
    _require(
        _same(document["trust_root_id"], trust_root_id),
        f"{label} attestation names a different trust root",
    )
    return document


def build_axiom_policy_acceptances(
    *,
    trust_root: AxiomPolicyTrustRoot,
    producer_attestation: Mapping[str, object],
    observation_attestations: Iterable[Mapping[str, object]],
) -> AxiomPolicyAcceptanceSet:
    """Verify signed artifacts and mint the acceptances they justify.

    This is the only way to obtain an :class:`AxiomPolicyAcceptance`. The
    producer attestation carries the Axiom run's identity hashes and the exact
    set of targets it produced; one observed-source attestation per target
    carries that target's observed aggregate and source identity. Both are
    authenticated under the trust root's separate keys, so every pin an
    acceptance holds comes from an artifact the operator signed rather than
    from the target being admitted.

    Args:
        trust_root: The operator trust root holding both verification keys.
        producer_attestation: ``{"document": ..., "signature": ...}`` for the
            Axiom producer run.
        observation_attestations: One signed observed-source attestation per
            declared target — no more, no fewer.

    Returns:
        The exact :class:`AxiomPolicyAcceptanceSet` the artifacts justify.

    Raises:
        TypeError: If ``trust_root`` is not an :class:`AxiomPolicyTrustRoot`.
        ValueError: If a signature does not verify, an artifact is malformed,
            or the observations do not cover exactly the declared target set.
    """
    if not isinstance(trust_root, AxiomPolicyTrustRoot):
        raise TypeError("trust_root must be an AxiomPolicyTrustRoot.")
    producer = _verify_attestation(
        producer_attestation,
        key=trust_root.producer_verification_key,
        keys=_PRODUCER_ATTESTATION_KEYS,
        artifact_kind=PRODUCER_ARTIFACT_KIND,
        trust_root_id=trust_root.trust_root_id,
        label="producer",
    )
    for name in IDENTITY_HASH_KEYS:
        _hash(producer[name], f"producer attestation {name}")
    period = producer["period"]
    _require(
        type(period) is str and re.fullmatch(r"[0-9]{4}", period) is not None,
        "invalid producer attestation period",
    )
    rows = producer["targets"]
    _require(
        type(rows) is list and bool(rows),
        "producer attestation must declare its target set",
    )
    declared: dict[tuple[str, int | str], dict[str, object]] = {}
    for row in rows:
        target = _exact_mapping(row, _PRODUCER_TARGET_KEYS, "producer attestation row")
        key = _typed_target_key(
            (target["name"], target["period"]), "producer attestation row"
        )
        _require(
            str(key[1]) == period,
            f"producer attestation row {key!r} is outside the attested period",
        )
        _hash(target["binding_sha256"], "producer attestation row binding_sha256")
        _hash(
            target["prepared_receipt_sha256"],
            "producer attestation row prepared_receipt_sha256",
        )
        _require(
            key not in declared,
            f"producer attestation declares {key!r} twice",
        )
        declared[key] = target

    observed: dict[tuple[str, int | str], dict[str, object]] = {}
    for attestation in observation_attestations:
        document = _verify_attestation(
            attestation,
            key=trust_root.observation_verification_key,
            keys=_OBSERVATION_ATTESTATION_KEYS,
            artifact_kind=OBSERVATION_ARTIFACT_KIND,
            trust_root_id=trust_root.trust_root_id,
            label="observation",
        )
        key = _typed_target_key(
            (document["name"], document["period"]), "observation attestation"
        )
        _require(
            key not in observed,
            f"observation attestations declare {key!r} twice",
        )
        _hash(
            document["observed_source_identity_sha256"],
            "observation attestation observed_source_identity_sha256",
        )
        value = document["observed_value"]
        _require(
            type(value) in (int, float) and math.isfinite(value),
            "observation attestation observed_value must be a finite number",
        )
        _require(
            type(document["observed_source"]) is str
            and bool(document["observed_source"].strip()),
            "observation attestation observed_source must be a nonempty string",
        )
        observed[key] = document

    missing = sorted(set(declared) - set(observed), key=repr)
    extra = sorted(set(observed) - set(declared), key=repr)
    _require(
        not missing and not extra,
        "observed-source attestations must cover exactly the produced target "
        f"set: missing {missing}, unexpected {extra}",
    )

    accepted = tuple(sorted(declared, key=repr))
    acceptances: dict[tuple[str, int | str], AxiomPolicyAcceptance] = {}
    for key in accepted:
        target = declared[key]
        document = observed[key]
        fields: dict[str, object] = {
            "target_key": list(key),
            "accepted_target_keys": [list(item) for item in accepted],
            "trust_root_id": trust_root.trust_root_id,
            "binding_sha256": target["binding_sha256"],
            "prepared_receipt_sha256": target["prepared_receipt_sha256"],
            **{name: producer[name] for name in IDENTITY_HASH_KEYS},
            "observed_source_identity_sha256": document[
                "observed_source_identity_sha256"
            ],
            "observed_value": float(document["observed_value"]),
            "observed_source": document["observed_source"],
        }
        acceptances[key] = AxiomPolicyAcceptance(
            target_key=key,
            accepted_target_keys=accepted,
            trust_root_id=trust_root.trust_root_id,
            binding_sha256=target["binding_sha256"],
            prepared_receipt_sha256=target["prepared_receipt_sha256"],
            **{name: producer[name] for name in IDENTITY_HASH_KEYS},
            observed_source_identity_sha256=document["observed_source_identity_sha256"],
            observed_value=float(document["observed_value"]),
            observed_source=document["observed_source"],
            seal=_seal(fields),
        )
    return AxiomPolicyAcceptanceSet(
        trust_root_id=trust_root.trust_root_id,
        acceptances=acceptances,
    )


def has_policy_semantics(metadata: Mapping[str, str]) -> bool:
    """Whether a target's own metadata declares Axiom policy semantics."""
    return bool(
        POLICY_RECEIPT_KEYS.intersection(metadata)
        or metadata.get("measure_kind") == "policy_derived"
        or metadata.get("activation_status") == "requires_policy_output"
    )


def axiom_policy_target_rows(targets: Iterable[Target]) -> tuple[str, ...]:
    """Row labels of targets declaring Axiom policy-derived semantics."""
    return tuple(
        target.row_name for target in targets if has_policy_semantics(target.metadata)
    )


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
    _typed_period(reference["period"], "policy reference period")

    prepared = _exact_mapping(
        binding["prepared"], _PREPARED_KEYS, "policy prepared receipt"
    )
    _require(_same(prepared["schema_version"], 3), "unsupported policy receipt version")
    raw_prepared = {
        key: value for key, value in prepared.items() if key != "receipt_sha256"
    }
    _hash(prepared["receipt_sha256"], "policy prepared receipt_sha256")
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
    for key in IDENTITY_HASH_KEYS:
        _hash(identity[key], key)
    for key in (
        "period",
        "output_variable",
        "output_entity",
        "target_entity",
        "target_measure",
    ):
        _require(
            type(identity[key]) is str and identity[key].strip(),
            f"invalid policy identity {key}",
        )

    basis = _validate_basis(prepared["basis"], "policy basis")
    observed_basis = _validate_basis(binding["observed_basis"], "observed basis")
    _require(observed_basis == basis, "observed and policy bases differ")
    _require(_same(identity["period"], basis["period"]), "policy period differs")
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
    output_ids = _validate_record_id_identity(
        output["record_ids"],
        label="policy output record ids",
        length=output["n_records"],
    )
    materialized_values = _validate_axiom_array_identity(
        output["materialized_values"],
        label="policy materialized output values",
        dtype="float64",
        storage_dtype="<f8",
        length=output["n_records"],
    )
    materialized_ids = _validate_axiom_record_id_identity(
        output["materialized_record_ids"],
        label="policy materialized output record ids",
        length=output["n_records"],
    )
    _require(
        _identity_id_family(output_ids) == _identity_id_family(materialized_ids),
        "policy output and materialized record ID families differ",
    )

    aggregation = _exact_mapping(
        prepared["aggregation"], _AGGREGATION_KEYS, "policy aggregation"
    )
    _require(
        type(aggregation["target_n_records"]) is int
        and aggregation["target_n_records"] > 0,
        "invalid target record count",
    )
    output_target_ids = _validate_record_id_identity(
        aggregation["output_target_ids"],
        label="policy output target ids",
        length=output["n_records"],
    )
    target_values = _validate_array_identity(
        aggregation["target_values"],
        label="policy target values",
        dtype="<f8",
        length=aggregation["target_n_records"],
    )
    target_ids = _validate_record_id_identity(
        aggregation["target_record_ids"],
        label="policy target record ids",
        length=aggregation["target_n_records"],
    )
    _require(
        _identity_id_family(output_target_ids) == _identity_id_family(target_ids),
        "policy membership and target record ID families differ",
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

    materialized = bind_materialization_output(
        prepared["materialization"],
        period=basis["period"],
        output_entity=identity["output_entity"],
        output_variable=identity["output_variable"],
        materialization_receipt_sha256=identity["materialization_receipt_sha256"],
        input_frame_sha256=identity["input_frame_sha256"],
        n_records=output["n_records"],
    )
    _require(
        materialized["values"] == materialized_values,
        "policy output identity differs from the materialization receipt",
    )
    _require(
        materialized["record_ids"] == materialized_ids,
        "policy output rows differ from the materialization receipt",
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
        type(binding["observed_value"]) is float
        and math.isfinite(binding["observed_value"]),
        "observed target value is invalid",
    )
    return {
        "aggregation": aggregation,
        "binding": binding,
        "identity": identity,
        "materialization": prepared["materialization"],
        "materialized": {
            "values": materialized_values,
            "record_ids": materialized_ids,
            "id_column": materialized["id_column"],
        },
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
        _require(
            _same(getattr(spec, field), reference[field]), f"reference {field} differs"
        )
    _require(
        _same(spec.value, binding["observed_value"])
        and _same(spec.source, binding["observed_source"]),
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
    """Require a trust-root acceptance and replay the receipt on the frame."""
    try:
        _require(
            isinstance(acceptance, AxiomPolicyAcceptance),
            "an independent Axiom policy acceptance is required",
        )
        _require_sealed(acceptance)
        _require(
            acceptance.target_key == target.key
            and _same(acceptance.target_key[0], target.name)
            and _same(acceptance.target_key[1], target.period),
            "the Axiom policy acceptance names a different target identity "
            f"{acceptance.target_key!r}",
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
        materialized = payload["materialized"]
        output = payload["output"]
        prepared = payload["prepared"]
        reference = payload["reference"]
        _require(
            prepared["receipt_sha256"] == acceptance.prepared_receipt_sha256,
            "policy prepared receipt differs from the independent acceptance",
        )
        for key in IDENTITY_HASH_KEYS:
            _require(
                identity[key] == getattr(acceptance, key),
                f"{key} differs from the independent acceptance",
            )
        _require(
            binding["observed_source_identity_sha256"]
            == acceptance.observed_source_identity_sha256,
            "observed source differs from the independent acceptance",
        )
        _require(
            _same(binding["observed_value"], acceptance.observed_value)
            and _same(binding["observed_source"], acceptance.observed_source),
            "observed aggregate differs from the independent acceptance",
        )

        for field in ("name", "entity", "measure", "period", "tolerance", "filter"):
            _require(
                _same(getattr(target, field), reference[field]),
                f"reference {field} differs",
            )
        _require(
            _same(binding["observed_value"], target.value)
            and _same(binding["observed_source"], target.source),
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
        _require(
            _same(
                materialized["id_column"],
                frame.schema.entity_id_column(identity["output_entity"]),
            ),
            "live Axiom output entity id column differs from the receipt",
        )
        raw_outputs = output_table[identity["output_variable"]].to_numpy()
        _require(
            raw_outputs.dtype == np.dtype("<f8")
            and raw_outputs.ndim == 1
            and np.isfinite(raw_outputs).all(),
            "live Axiom outputs are not native finite float64",
        )
        output_ids = canonical_policy_record_ids(
            output_table[
                frame.schema.entity_id_column(identity["output_entity"])
            ].to_numpy(),
            "live policy output record IDs",
        )
        _require(
            _array_identity(raw_outputs) == output["values"],
            "live Axiom output values differ",
        )
        _require(
            _array_identity(output_ids) == output["record_ids"],
            "live Axiom output record IDs/order differ",
        )
        _require(
            axiom_array_identity(raw_outputs) == materialized["values"],
            "live Axiom outputs differ from the materialized requested output",
        )
        _require(
            axiom_array_identity(output_ids) == materialized["record_ids"],
            "live Axiom output rows differ from the materialized entity rows",
        )

        target_table = frame.table(identity["target_entity"])
        target_values = target_table[identity["target_measure"]].to_numpy()
        _require(
            target_values.dtype == np.dtype("<f8")
            and target_values.ndim == 1
            and np.isfinite(target_values).all(),
            "live policy target values are not native finite float64",
        )
        target_ids = canonical_policy_record_ids(
            target_table[
                frame.schema.entity_id_column(identity["target_entity"])
            ].to_numpy(),
            "live policy target record IDs",
        )
        if aggregation["kind"] == "identity":
            mapped_ids = output_ids
            recomputed = raw_outputs
        else:
            membership_column = aggregation["membership_column"]
            mapped_ids = canonical_policy_record_ids(
                output_table[membership_column].to_numpy(),
                "live output membership",
                unique=False,
            )
            _require(
                mapped_ids.shape == output_ids.shape,
                "live output membership length differs",
            )
            _require(
                _id_family(mapped_ids) == _id_family(target_ids),
                "live output membership and target ID families differ",
            )
            positions = {
                _id_key(value): index for index, value in enumerate(target_ids)
            }
            _require(
                set(_id_key(value) for value in mapped_ids) == set(positions),
                "live output membership does not cover exact target IDs",
            )
            recomputed = np.zeros(len(target_ids), dtype="<f8")
            with np.errstate(over="raise", invalid="raise"):
                np.add.at(
                    recomputed,
                    np.fromiter(
                        (positions[_id_key(value)] for value in mapped_ids),
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
