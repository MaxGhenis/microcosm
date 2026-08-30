"""Opt-in, value-free monetary target inventories for country packages.

Inventory membership is not solver activation. A caller must resolve a source
observation and supply an exactly compatible prepared measure through
``bind_monetary_target``. This leaves the incumbent demographic registry intact.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from microcosm.build.ledger_targets import LedgerTargetReference
from microcosm.build.monetary_targets import MonetaryBasis

READINESS_STATES = frozenset(
    {
        "requires_prepared_measure",
        "requires_policy_output",
        "requires_coverage_bridge",
        "historical_validation_only",
    }
)


@dataclass(frozen=True)
class MonetaryTargetContract:
    """A source selector, accounting basis and explicit activation prerequisite."""

    reference: LedgerTargetReference
    basis: MonetaryBasis
    readiness: str
    source_url: str
    notes: str


@dataclass(frozen=True)
class MonetaryTargetProfile:
    """A checked inventory, deliberately separate from active target references."""

    country: str
    profile_id: str
    description: str
    targets: tuple[MonetaryTargetContract, ...]

    @classmethod
    def from_mapping(
        cls, raw: Mapping[str, Any], *, country: str
    ) -> MonetaryTargetProfile:
        context = "financial_wealth_targets.json"
        _closed_keys(
            raw,
            {
                "schema_version",
                "country",
                "profile_id",
                "activation",
                "description",
                "targets",
            },
            context,
        )
        if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
            raise ValueError(f"{context}: schema_version must be 1")
        if raw["country"] != country:
            raise ValueError(f"{context}: country must match {country!r}")
        if raw["activation"] != "explicit_only":
            raise ValueError(f"{context}: activation must be explicit_only")
        for key in ("country", "profile_id", "description"):
            _text(raw[key], f"{context}.{key}")
        rows = raw["targets"]
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{context}: targets must be a nonempty list")
        targets = tuple(_contract(row, context) for row in rows)
        names = [target.reference.name for target in targets]
        measures = [target.reference.measure for target in targets]
        if len(set(names)) != len(names):
            raise ValueError(f"{context}: duplicate target names")
        if len(set(measures)) != len(measures):
            raise ValueError(f"{context}: duplicate prepared measure names")
        return cls(country, raw["profile_id"], raw["description"], targets)


def _text(value: Any, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: expected a nonempty string")


def _closed_keys(raw: Any, keys: set[str], context: str) -> None:
    if not isinstance(raw, Mapping) or set(raw) != keys:
        raise ValueError(f"{context}: expected exactly {sorted(keys)}")


def _contract(raw: Any, context: str) -> MonetaryTargetContract:
    _closed_keys(
        raw, {"reference", "basis", "readiness", "source_url", "notes"}, context
    )
    readiness = raw["readiness"]
    if not isinstance(readiness, str) or readiness not in READINESS_STATES:
        raise ValueError(f"{context}: unknown readiness state {readiness!r}")
    _text(raw["notes"], f"{context}.notes")
    _text(raw["source_url"], f"{context}.source_url")
    url = urlparse(raw["source_url"])
    if url.scheme != "https" or not url.netloc:
        raise ValueError(f"{context}: source_url must be an absolute HTTPS URL")
    reference_raw = raw["reference"]
    if not isinstance(reference_raw, Mapping):
        raise ValueError(f"{context}: reference must be a mapping")
    # The dataclass rejects observed values and arbitrary executable fields.
    try:
        reference = LedgerTargetReference(**reference_raw)
        basis = MonetaryBasis(**raw["basis"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context}: invalid monetary contract: {exc}") from exc
    if not reference.measure or not reference.name or reference.filter is not None:
        raise ValueError(f"{context}: require a scalar direct prepared measure")
    if reference.value_operation != "identity":
        raise ValueError(f"{context}: resolve derived source facts before binding")
    if reference.assertion_policy != "observed_only":
        raise ValueError(f"{context}: monetary inventory accepts observations only")
    if reference.se is not None or reference.tolerance is not None:
        raise ValueError(f"{context}: source uncertainty and gates are separate inputs")
    if any(
        value is not None
        for value in (
            reference.uprating_index,
            reference.uprating_from_period,
            reference.uprating_to_period,
        )
    ):
        raise ValueError(f"{context}: no implicit monetary period uprating")
    if isinstance(reference.period, bool) or str(reference.period) != basis.period[:4]:
        raise ValueError(f"{context}: model year must match the accounting basis")
    role = "validation" if readiness == "historical_validation_only" else "calibration"
    if reference.metadata.get("target_role") != role:
        raise ValueError(f"{context}: target_role must be {role!r} for {readiness}")
    if reference.metadata.get("activation_status") != readiness:
        raise ValueError(
            f"{context}: reference activation_status disagrees with readiness"
        )
    if reference.metadata.get("measure_kind") != "prepared_column":
        raise ValueError(f"{context}: monetary references require prepared_column")
    return MonetaryTargetContract(
        reference, basis, readiness, raw["source_url"], raw["notes"]
    )
