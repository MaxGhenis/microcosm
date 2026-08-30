"""Opt-in integrity checks for source-receipted monetary constraint rows.

This module authenticates alignment, not accounting concepts or source truth.
It deliberately has no dependency on a country package or ``microcosm.build``.
"""

from __future__ import annotations

import hashlib
import json
import math
import re

import numpy as np
from numpy.typing import ArrayLike

from microcosm.calibrate.target import Target
from microcosm.frame import Frame


class MonetaryBindingIntegrityError(RuntimeError):
    """A monetary receipt cannot safely describe the compiled constraint."""


def monetary_digest(value: object) -> str:
    """Hash a canonical JSON value, refusing nonfinite numbers."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def canonical_record_ids(values: ArrayLike) -> np.ndarray:
    """Return unique integer row IDs in little-endian int64 without truncation."""
    ids = np.asarray(values)
    if ids.ndim != 1 or not ids.size or ids.dtype.kind not in "iu":
        raise ValueError(
            "record_ids must be a nonempty one-dimensional integer vector."
        )
    if ids.dtype.kind == "u" and ids.max() > np.iinfo(np.int64).max:
        raise ValueError("record_ids must fit signed int64 without overflow.")
    ids = ids.astype("<i8", copy=False)
    if np.unique(ids).size != ids.size:
        raise ValueError("record_ids must uniquely identify entity rows.")
    return ids


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_monetary_binding(target: Target, frame: Frame) -> None:
    """Fail the whole compilation on incomplete, stale, or misaligned receipts.

    Ordinary targets, with neither monetary metadata key, remain unchanged.
    Value bytes are canonical float64; IDs are canonical int64 in row order.
    """
    keys = {"monetary_binding", "monetary_binding_sha256"}
    if not keys.intersection(target.metadata):
        return
    try:
        _require(
            target.filter is None,
            "monetary filters are unsupported; prepare the masked amount vector instead",
        )
        binding = json.loads(target.metadata["monetary_binding"])
        _require(
            monetary_digest(binding) == target.metadata["monetary_binding_sha256"],
            "binding hash differs",
        )
        reference, prepared = binding["reference"], binding["prepared"]
        _require(
            isinstance(reference, dict) and isinstance(prepared, dict),
            "invalid receipt objects",
        )
        required = (
            "schema_version basis n_records source_identity_sha256 source_values_sha256 "
            "values_sha256 record_ids_sha256 bridge bridge_sha256 readiness "
            "measure_kind receipt_sha256"
        ).split()
        _require(set(required) <= prepared.keys(), "incomplete prepared receipt")
        _require(
            type(prepared["schema_version"]) is int and prepared["schema_version"] == 2,
            "unsupported prepared receipt version",
        )
        receipt = {
            key: value for key, value in prepared.items() if key != "receipt_sha256"
        }
        _require(
            monetary_digest(receipt) == prepared["receipt_sha256"],
            "prepared receipt hash differs",
        )
        _require(
            prepared["readiness"] == "ready" and prepared["measure_kind"] == "direct",
            "measure is not ready/direct",
        )
        _require(
            binding["source_assertion"]
            in {"observation", "observed", "derived_observation"},
            "source is not an observation",
        )
        hashes = "source_identity_sha256 source_values_sha256 values_sha256 record_ids_sha256".split()
        identities = [
            binding["source_identity_sha256"],
            *(prepared[key] for key in hashes),
        ]
        for identity in identities:
            _require(
                isinstance(identity, str)
                and re.fullmatch(r"[0-9a-f]{64}", identity) is not None,
                "invalid source/array identity",
            )
        basis = prepared["basis"]
        fields = (
            "currency unit period temporal_basis sector perimeter valuation".split()
        )
        _require(
            isinstance(basis, dict)
            and all(
                isinstance(basis[key], str) and basis[key].strip() for key in fields
            ),
            "incomplete monetary basis",
        )
        _require(
            basis["unit"] == "base_currency"
            and basis["temporal_basis"] in {"annual_flow", "closing_stock"},
            "invalid monetary basis",
        )
        bridge = prepared["bridge"]
        _require(
            monetary_digest(bridge) == prepared["bridge_sha256"], "bridge hash differs"
        )
        _require(
            not isinstance(bridge["factor"], bool)
            and math.isfinite(bridge["factor"])
            and bridge["factor"] > 0,
            "invalid transport factor",
        )
        _require(
            isinstance(bridge["description"], str)
            and bool(bridge["description"].strip())
            and isinstance(bridge["source_sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", bridge["source_sha256"]) is not None,
            "incomplete transport source",
        )
        for field in ("name", "entity", "measure", "period", "filter"):
            expected = reference[field]
            if field == "period" and expected is None:
                expected = basis["period"]
            _require(expected == getattr(target, field), f"reference {field} differs")
        _require(
            isinstance(target.measure, str),
            "monetary rows require named columns",
        )
        _require(
            binding["value"] == target.value and binding["source"] == target.source,
            "target value/source differs",
        )
        _require(
            {key: value for key, value in target.metadata.items() if key not in keys}
            == reference["metadata"],
            "reference metadata differs",
        )
        metadata = reference["metadata"]
        _require(
            metadata.get("activation_status", "ready")
            in {"ready", "active", "requires_prepared_measure"}
            and metadata.get("target_role", "calibration") == "calibration"
            and metadata.get("measure_kind", "direct")
            in {"direct", "direct_column", "prepared_column"},
            "reference is not ready/direct calibration",
        )
        table = frame.table(target.entity)
        values = table[target.measure].to_numpy(dtype="<f8")
        ids = canonical_record_ids(
            table[frame.schema.entity_id_column(target.entity)].to_numpy()
        )
        _require(
            type(prepared["n_records"]) is int
            and prepared["n_records"] > 0
            and values.ndim == 1
            and len(values) == prepared["n_records"],
            "record length differs",
        )
        _require(
            np.isfinite(values).all()
            and hashlib.sha256(values.tobytes()).hexdigest()
            == prepared["values_sha256"],
            "prepared values differ from frame column",
        )
        _require(
            hashlib.sha256(ids.tobytes()).hexdigest() == prepared["record_ids_sha256"],
            "prepared record IDs/order differ from frame",
        )
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise MonetaryBindingIntegrityError(
            f"{target.row_name}: monetary binding integrity failed ({exc})."
        ) from exc
