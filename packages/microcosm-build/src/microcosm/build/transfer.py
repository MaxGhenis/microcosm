"""Small, explicit country-transfer primitives over the shared Frame graph.

This boundary retains the complete authenticated donor as a source artifact.
It projects measurements by allowlist and constructs recipient groups from an
explicit membership declaration. It never transports policy outputs or infers
recipient family membership from a donor tax unit.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from microcosm.frame import EntitySchema, Frame, WeightKind, Weights
from microcosm.graph import (
    Capabilities,
    Determinism,
    KernelBase,
    KernelContext,
    KernelResult,
    StructuralDelta,
    load_source,
    source_hash,
)


class TransferSourceKernel(KernelBase):
    """Create recipient entities from a pinned donor and declared relationships.

    The initial executable contract is deliberately fixture-only. An actual
    donor needs an approved immutable handoff and a reviewed recipient-family
    construction operator; passing a production Frame fails closed.
    """

    ref = "transfer.explicit_membership@1"
    capabilities = Capabilities(
        determinism=Determinism.DETERMINISTIC,
        structural=StructuralDelta.CREATE,
        dependencies=("numpy", "pandas"),
    )

    def implementation_hash(self) -> str:
        return source_hash(
            type(self),
            load_source,
            Frame,
            EntitySchema,
            Weights,
            dependencies=self.capabilities.dependencies,
        )

    def run(self, context: KernelContext) -> KernelResult:
        donor = load_source("frame-store", context.sources["donor"])
        household = donor.table("household")
        if (
            household.empty
            or "donor_fixture_status" not in household
            or not household.donor_fixture_status.eq("synthetic_fixture")
            .fillna(False)
            .all()
        ):
            raise ValueError(
                "No real donor is approved for this fixture transfer boundary"
            )
        if (
            "donor_scope" not in household
            or not household.donor_scope.eq("full_common_frame_all_support_clones")
            .fillna(False)
            .all()
        ):
            raise ValueError("Transfer requires the full common Frame and all clones")
        person = donor.table("person")
        household = donor.table("household")
        group = str(context.params["recipient_group"])
        membership = str(context.params["membership_column"])
        family_ids = person[membership]
        if family_ids.isna().any() or family_ids.dtype != np.dtype("int64"):
            raise ValueError("Recipient family membership must be complete exact int64")
        if person.groupby(membership).person_household_id.nunique().max() != 1:
            raise ValueError("Recipient families must nest within households")
        required = {
            "person",
            "household",
            "tax_unit",
            "spm_unit",
            "family",
            "marital_unit",
        }
        if set(donor.entities) != required:
            raise ValueError("Full donor entity inventory is incomplete")
        for entity in donor.entities:
            table = donor.table(entity)
            for suffix in (
                "spine_source_id",
                "source_id",
                "support_channel",
                "support_clone_index",
            ):
                if f"{entity}_{suffix}" not in table:
                    raise ValueError(f"Missing donor lineage {entity}_{suffix}")
                values = table[f"{entity}_{suffix}"]
                if values.isna().any():
                    raise ValueError(f"Null donor lineage {entity}_{suffix}")
                if suffix == "support_channel":
                    if (
                        not pd.api.types.is_string_dtype(values.dtype)
                        or values.str.len().eq(0).any()
                    ):
                        raise ValueError(f"Invalid support channel on {entity}")
                elif not pd.api.types.is_integer_dtype(values.dtype):
                    raise ValueError(
                        f"Donor lineage must use exact integer storage: {entity}_{suffix}"
                    )
            clones = table[f"{entity}_support_clone_index"]
            pairs = table.groupby([f"{entity}_support_channel", f"{entity}_source_id"])[
                f"{entity}_support_clone_index"
            ]
            if not clones.isin([0, 1]).all() or not pairs.nunique().eq(2).all():
                raise ValueError(f"Fixture requires both support clones on {entity}")
        recipient_person = person[["person_id", "person_household_id"]].copy()
        recipient_person[f"person_{group}_id"] = family_ids
        for entity in donor.schema.group_entities:
            recipient_person[f"donor_person_{entity}_id"] = person[
                f"person_{entity}_id"
            ].astype("string")
        for source, destination in context.params["person_mappings"]:
            recipient_person[destination] = person[source].copy()
        recipient_household = household[["household_id"]].copy()
        for source, destination in context.params["household_mappings"]:
            recipient_household[destination] = household[source].copy()
        # Absolute cohort IDs stay int64 in the Frame; portable lineage keys use
        # decimal strings/JSON origin tuples, never floating-point JS numbers.
        namespace = str(context.params["donor_namespace"])
        recipient_person["donor_person_key"] = pd.Series(
            [
                json.dumps(
                    ["US", namespace, "person", str(value)], separators=(",", ":")
                )
                for value in person.person_id
            ],
            dtype="string",
        )
        recipient_household["donor_household_key"] = pd.Series(
            [
                json.dumps(
                    ["US", namespace, "household", str(value)], separators=(",", ":")
                )
                for value in household.household_id
            ],
            dtype="string",
        )
        recipient_group = pd.DataFrame({f"{group}_id": np.sort(family_ids.unique())})
        recipient_group["family_definition"] = pd.Series(
            [str(context.params["family_definition"])] * len(recipient_group),
            dtype="string",
        )
        source_weights = donor.weights_for("household")
        # Keep the incoming weight kind and values in provenance; recipient
        # design weights are an explicitly declared proposal at NZ scale.
        recipient_household["donor_household_weight"] = source_weights.values
        scale = float(context.params["design_scale"])
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError("design_scale must be finite and positive")
        frame = Frame(
            {
                "person": recipient_person,
                "household": recipient_household,
                group: recipient_group,
            },
            EntitySchema(group_entities=("household", group)),
            {"household": Weights(source_weights.values * scale, WeightKind.DESIGN)},
            donor.strata,
            metadata={
                "status": "development_fixture_transfer",
                "donor_status": "synthetic_fixture",
                "donor_weight_kind": source_weights.kind.value,
                "source_country": "US",
                "recipient_country": context.params["recipient_country"],
                "family_definition": context.params["family_definition"],
                "full_donor_preserved_in_graph_source": True,
            },
        )
        return KernelResult(
            frame=frame,
            receipt={
                "donor_entities": {e: donor.n(e) for e in donor.entities},
                "recipient_entities": {e: frame.n(e) for e in frame.entities},
                "donor_weight_kind": source_weights.kind.value,
                "recipient_weight_kind": "design",
                "design_scale": scale,
                "family_definition": context.params["family_definition"],
                "excluded_policy_outputs": ("us_income_tax", "us_snap"),
                "status": "synthetic_fixture_only",
            },
        )


class ScaleMeasurementsKernel(KernelBase):
    """Apply explicit per-field numeric scales; no implicit FX or uprating."""

    ref = "transfer.scale_measurements@1"
    capabilities = Capabilities(
        determinism=Determinism.DETERMINISTIC, dependencies=("numpy", "pandas")
    )

    def run(self, context: KernelContext) -> KernelResult:
        columns = {}
        for (
            entity,
            source,
            target,
            factor,
            _source_unit,
            _target_unit,
            _period,
            _basis,
        ) in context.params["mappings"]:
            if not np.isfinite(factor) or factor <= 0:
                raise ValueError("Measurement factors must be finite and positive")
            table = context.tables[entity]
            columns[entity, target] = pd.Series(
                table[source].to_numpy(dtype=float) * factor,
                index=pd.Index(table[f"{entity}_id"]),
                dtype="float64",
            )
        return KernelResult(
            columns=columns,
            receipt={
                "measurement_mappings": context.params["mappings"],
                "missing_values": "preserved; never replaced with zero",
            },
        )


def json_bytes(value: object) -> bytes:
    """Canonical readable diagnostic bytes, refusing NaN/Infinity."""
    return (
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()
