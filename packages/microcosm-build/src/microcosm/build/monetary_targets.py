"""Exact-basis, source-receipted bindings for prepared monetary measures.

This guard neither discovers facts nor calculates tax/benefit rules. A caller
must resolve the source fact and declare any level transport explicitly before
binding it. A currency conversion alone never establishes concept equivalence.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

from microcosm.build.ledger_targets import LedgerTargetReference
from microcosm.calibrate import TargetSpec
from microcosm.calibrate.monetary_binding import (
    canonical_record_ids,
)
from microcosm.calibrate.monetary_binding import (
    monetary_digest as _digest,
)


def _sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{label} must be a lowercase SHA-256 identity.")


def _vector(values: ArrayLike, label: str) -> np.ndarray:
    result = np.asarray(values, dtype="<f8")
    if result.ndim != 1 or not result.size or not np.isfinite(result).all():
        raise ValueError(f"{label} must be a nonempty, finite one-dimensional vector.")
    return result


@dataclass(frozen=True)
class MonetaryBasis:
    """An amount's exact units, measurement period, and accounting perimeter.

    ``annual_flow`` uses a calendar year (YYYY); ``closing_stock`` uses a
    specific closing date (YYYY-MM-DD). Monthly, fiscal-year, and million-unit
    inputs must be resolved explicitly upstream, not relabeled by this guard.
    """

    currency: str
    unit: str
    period: str
    temporal_basis: Literal["annual_flow", "closing_stock"]
    sector: str
    perimeter: str
    valuation: str

    def __post_init__(self) -> None:
        if not isinstance(self.currency, str) or not re.fullmatch(
            r"[A-Z]{3}", self.currency
        ):
            raise ValueError(
                "currency must be an explicit uppercase three-letter code."
            )
        if self.unit != "base_currency":
            raise ValueError("unit must be base_currency; no implicit unit scaling.")
        for name in ("sector", "perimeter", "valuation"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be explicit and nonempty.")
        if not isinstance(self.period, str):
            raise ValueError("period must be an explicit YYYY or YYYY-MM-DD string.")
        if self.temporal_basis == "annual_flow":
            if not re.fullmatch(r"[0-9]{4}", self.period):
                raise ValueError(
                    "annual_flow period must be YYYY, not a month or date."
                )
            date(int(self.period), 1, 1)
        elif self.temporal_basis == "closing_stock":
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", self.period):
                raise ValueError(
                    "closing_stock period must be an exact YYYY-MM-DD date."
                )
            date.fromisoformat(self.period)
        else:
            raise ValueError("temporal_basis must be annual_flow or closing_stock.")


@dataclass(frozen=True, eq=False)
class PreparedMonetaryMeasure:
    """Copied, immutable amount vector with an explicit sourced level bridge.

    Construction multiplies the input values by ``factor`` exactly once. The
    resulting array is backed by immutable bytes, so even ``setflags`` cannot
    make it writable. ``policy_derived`` and unbound measures may be receipted
    but cannot bind: this module has no authenticated rules-engine bridge.
    """

    values: np.ndarray = field(repr=False)
    record_ids: np.ndarray = field(repr=False)
    basis: MonetaryBasis
    factor: float
    source_identity_sha256: str
    bridge_description: str
    bridge_source_sha256: str
    readiness: str = "ready"
    measure_kind: str = "direct"
    source_values_sha256: str = field(init=False)
    values_sha256: str = field(init=False)
    record_ids_sha256: str = field(init=False)
    bridge_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.basis, MonetaryBasis):
            raise TypeError("basis must be MonetaryBasis.")
        factor = float(self.factor)
        if (
            isinstance(self.factor, (bool, np.bool_))
            or not math.isfinite(factor)
            or factor <= 0
        ):
            raise ValueError("factor must be explicitly positive and finite.")
        _sha256(self.source_identity_sha256, "source_identity_sha256")
        _sha256(self.bridge_source_sha256, "bridge_source_sha256")
        if (
            not isinstance(self.bridge_description, str)
            or not self.bridge_description.strip()
        ):
            raise ValueError("bridge_description must explain the explicit transport.")
        if self.readiness not in {"ready", "unbound"}:
            raise ValueError("readiness must be ready or unbound.")
        if self.measure_kind not in {"direct", "policy_derived"}:
            raise ValueError("measure_kind must be direct or policy_derived.")
        raw = _vector(self.values, "amounts")
        with np.errstate(over="ignore", invalid="ignore"):
            scaled = _vector(raw * factor, "transported amounts")
        ids = canonical_record_ids(self.record_ids)
        if ids.shape != raw.shape:
            raise ValueError("record_ids must align one-to-one with amounts.")
        immutable = np.frombuffer(scaled.tobytes(), dtype="<f8")
        object.__setattr__(self, "values", immutable)
        object.__setattr__(
            self, "record_ids", np.frombuffer(ids.tobytes(), dtype="<i8")
        )
        object.__setattr__(self, "factor", factor)
        object.__setattr__(
            self, "source_values_sha256", hashlib.sha256(raw.tobytes()).hexdigest()
        )
        object.__setattr__(
            self, "values_sha256", hashlib.sha256(immutable.tobytes()).hexdigest()
        )
        object.__setattr__(
            self, "record_ids_sha256", hashlib.sha256(ids.tobytes()).hexdigest()
        )
        object.__setattr__(self, "bridge_sha256", _digest(self._bridge()))

    def _bridge(self) -> dict[str, object]:
        return {
            "factor": self.factor,
            "description": self.bridge_description,
            "source_sha256": self.bridge_source_sha256,
        }

    def receipt(self) -> dict[str, object]:
        """Return fresh JSON-safe provenance; mutating it cannot alter the measure."""
        self._check_vector_metadata()
        result = {
            "schema_version": 2,
            "basis": asdict(self.basis),
            "n_records": len(self.values),
            "source_identity_sha256": self.source_identity_sha256,
            "source_values_sha256": self.source_values_sha256,
            "values_sha256": self.values_sha256,
            "record_ids_sha256": self.record_ids_sha256,
            "bridge": self._bridge(),
            "bridge_sha256": self.bridge_sha256,
            "readiness": self.readiness,
            "measure_kind": self.measure_kind,
        }
        return {**result, "receipt_sha256": _digest(result)}

    def _check_vector_metadata(self) -> None:
        # NumPy permits dtype/shape edits even on a bytes-backed read-only array.
        if (
            self.values.dtype != np.dtype("<f8")
            or self.values.ndim != 1
            or self.record_ids.dtype != np.dtype("<i8")
            or self.record_ids.shape != self.values.shape
        ):
            raise ValueError("Prepared array dtype/shape metadata was mutated.")

    def total(self, weights: ArrayLike) -> float:
        """Measure already entity-aligned weights, refusing invalid accounting."""
        self._check_vector_metadata()
        weights = _vector(weights, "weights")
        if weights.shape != self.values.shape or (weights < 0).any():
            raise ValueError("weights must be aligned with amounts and nonnegative.")
        with np.errstate(over="ignore", invalid="ignore"):
            total = float(np.dot(self.values, weights))
        if not math.isfinite(total):
            raise ValueError("weighted monetary total must be finite.")
        return total


def prepare_monetary_measure(
    values: ArrayLike,
    *,
    record_ids: ArrayLike,
    basis: MonetaryBasis,
    factor: float,
    source_identity_sha256: str,
    bridge_description: str,
    bridge_source_sha256: str,
    readiness: str = "ready",
    measure_kind: str = "direct",
) -> PreparedMonetaryMeasure:
    """Freeze explicit transport and the exact entity-row IDs of the input vector."""
    return PreparedMonetaryMeasure(
        values=values,
        record_ids=record_ids,
        basis=basis,
        factor=factor,
        source_identity_sha256=source_identity_sha256,
        bridge_description=bridge_description,
        bridge_source_sha256=bridge_source_sha256,
        readiness=readiness,
        measure_kind=measure_kind,
    )


def bind_monetary_target(
    reference: LedgerTargetReference,
    *,
    value: float,
    source_basis: MonetaryBasis,
    source_assertion: str,
    source_identity_sha256: str,
    prepared: PreparedMonetaryMeasure,
    source: str | None = None,
) -> TargetSpec:
    """Bind one resolved observation only after exact monetary-basis agreement.

    ``source_identity_sha256`` identifies the resolved fact artifact, distinct
    from the prepared measure's donor identity. A reference may use the exact
    measurement period, or a matching model year for a closing stock; its full
    closing date remains bound in the receipt. Resolution and any unit/time
    normalization are the caller's separate, source-audited responsibility.
    Filters are unsupported: prepare the intended masked amount vector instead,
    so its complete contribution is frozen in the value receipt.
    """
    if not isinstance(reference, LedgerTargetReference):
        raise TypeError("reference must be LedgerTargetReference.")
    if reference.filter is not None:
        raise ValueError(
            "Monetary filters are unsupported; prepare the masked amount vector instead."
        )
    if not isinstance(prepared, PreparedMonetaryMeasure) or not isinstance(
        source_basis, MonetaryBasis
    ):
        raise TypeError("prepared measure and source basis must be typed.")
    prepared._check_vector_metadata()
    if not isinstance(reference.signed, bool):
        raise ValueError("Reference signed must be an explicit boolean.")
    if source_assertion not in {"observation", "observed", "derived_observation"}:
        raise ValueError(
            "Only observation facts may bind; projections/forecasts are unbound."
        )
    if prepared.readiness != "ready" or prepared.measure_kind != "direct":
        raise ValueError(
            "Only ready direct measures may bind; policy-derived measures need an engine bridge."
        )
    if reference.metadata.get("activation_status", "ready") not in {
        "ready",
        "active",
        "requires_prepared_measure",
    }:
        raise ValueError("Reference activation_status is not ready.")
    if reference.metadata.get("target_role", "calibration") != "calibration":
        raise ValueError(
            "Only calibration references may bind; validation is held out."
        )
    if reference.metadata.get("measure_kind", "direct") not in {
        "direct",
        "direct_column",
        "prepared_column",
    }:
        raise ValueError("Reference measure_kind needs an unsupported policy bridge.")
    if source_basis != prepared.basis:
        mismatches = [
            key
            for key, val in asdict(source_basis).items()
            if val != getattr(prepared.basis, key)
        ]
        raise ValueError(f"Monetary basis mismatch: {', '.join(mismatches)}.")
    if reference.value_operation not in {"identity", "sum", "count_x_mean"} or any(
        item is not None
        for item in (
            reference.uprating_index,
            reference.uprating_from_period,
            reference.uprating_to_period,
        )
    ):
        raise ValueError(
            "Implicit temporal/value conversion or uprating is not permitted."
        )
    if (
        reference.value_operation == "count_x_mean"
        and source_assertion != "derived_observation"
    ):
        raise ValueError(
            "count_x_mean requires a resolved derived_observation with source lineage."
        )
    allowed_periods = {source_basis.period}
    if source_basis.temporal_basis == "closing_stock":
        allowed_periods.add(source_basis.period[:4])
    if reference.period is not None and str(reference.period) not in allowed_periods:
        raise ValueError("Reference period does not match the monetary basis.")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Target amount must be finite.")
    if not reference.signed and (prepared.values < 0).any():
        raise ValueError("Negative prepared amounts require reference signed=True.")
    for name in ("se", "tolerance"):
        number = getattr(reference, name)
        if number is not None and (
            not math.isfinite(float(number)) or float(number) < 0
        ):
            raise ValueError(f"Target {name} must be finite and nonnegative.")
    if (value > 0 and not (prepared.values > 0).any()) or (
        value < 0 and not (prepared.values < 0).any()
    ):
        raise ValueError("Target has no same-sign prepared monetary support.")
    _sha256(source_identity_sha256, "source_identity_sha256")
    source = (
        source
        or reference.source
        or reference.ledger_source_record_id
        or reference.ledger_fact_key
    )
    if not isinstance(source, str) or not source.strip():
        raise ValueError("Resolved target source citation is required.")
    binding = {
        "reference": asdict(reference),
        "value": value,
        "source": source,
        "source_assertion": source_assertion,
        "source_identity_sha256": source_identity_sha256,
        "prepared": prepared.receipt(),
    }
    return TargetSpec(
        name=reference.name,
        entity=reference.entity,
        measure=reference.measure,
        value=value,
        filter=reference.filter,
        period=reference.period
        if reference.period is not None
        else source_basis.period,
        source=source,
        family=reference.family,
        signed=reference.signed,
        se=reference.se,
        tolerance=reference.tolerance,
        notes=reference.notes,
        metadata={
            **reference.metadata,
            "monetary_binding_sha256": _digest(binding),
            "monetary_binding": json.dumps(binding, sort_keys=True, allow_nan=False),
        },
    )
