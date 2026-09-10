"""Fail-closed NZ Accommodation Supplement core inputs and actual Axiom execution.

This boundary never implements policy. The core supplies a non-rate judgment and
an independently calculated weekly rate, not a combined entitlement. Inputs and
outputs are NZD weekly snapshots; no annualization or receipt inference occurs.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import pandas as pd

from microcosm.frame import EntitySchema, Frame
from microcosm.frame.adapters.axiom import AxiomEngine
from microcosm.frame.kernels import SimulateRulesKernel

AS_MODULE = "nz/statutes/social_security/accommodation_supplement/core.yaml"
AS_MODULE_SHA256 = "f2feca3c2f1de71623ccd577cd2aed20e8822614aac0ccfc767b5faf4eaa83cc"
AS_RULESPEC_COMMIT = "635801507e988a049f0bb4b6cfc9a660a3c587cf"
AS_SNAPSHOT_PERIOD = "2026-04"
AS_OUTPUTS = (
    "accommodation_supplement_non_rate_entitlement_requirements",
    "accommodation_supplement_rounded_weekly_payment",
)
AS_BOUNDARIES = (
    "The core's rounded weekly rate is not gated by its non-rate judgment.",
    "The delegated base rate and non-beneficiary income cutout are required inputs.",
    "No encoded cross-module final entitlement or general residence check is bound.",
    "This is an April 2026 snapshot, not an NZ tax-year or receipt estimate.",
)

# Exact first official RuleSpec companion case: sole parent, two children,
# renter in AS Area 1. Every value is an authored test fixture, not NZ evidence.
_AS_RENTER_FIXTURE = {
    "accommodation_supplement_additional_resident_in_social_housing": False,
    "accommodation_supplement_area_let_to_nonresidents": 0,
    "accommodation_supplement_base_rate_weekly_amount": 600,
    "accommodation_supplement_boarder": False,
    "accommodation_supplement_business_use_area": 0,
    "accommodation_supplement_cash_assets": 1000,
    "accommodation_supplement_concessionary_mortgage_payments_to_kainga_ora_or_crown": False,
    "accommodation_supplement_costs_are_homeownership": False,
    "accommodation_supplement_disability_accommodation_or_care_funded_under_pae_ora_act": False,
    "accommodation_supplement_has_accommodation_costs": True,
    "accommodation_supplement_has_dependent_children": True,
    "accommodation_supplement_has_two_or_more_dependent_children": True,
    "accommodation_supplement_in_relationship": False,
    "accommodation_supplement_joint_owner_with_resident": False,
    "accommodation_supplement_non_beneficiary": False,
    "accommodation_supplement_non_beneficiary_income_cutout_weekly_amount": 0,
    "accommodation_supplement_owner_weekly_payment_share": 0,
    "accommodation_supplement_owner_weekly_required_payments": 0,
    "accommodation_supplement_owns_premises_and_not_joint_owner_with_resident": False,
    "accommodation_supplement_partner_receiving_accommodation_supplement": False,
    "accommodation_supplement_receiving_or_eligible_for_student_allowance_grant": False,
    "accommodation_supplement_relevant_weekly_income": 0,
    "accommodation_supplement_rent_paid_to_kainga_ora": False,
    "accommodation_supplement_rent_paid_to_registered_community_housing_provider_social_housing": False,
    "accommodation_supplement_residential_care_funded_under_residential_care_act": False,
    "accommodation_supplement_resides_in_area_1": True,
    "accommodation_supplement_resides_in_area_2": False,
    "accommodation_supplement_resides_in_area_3": False,
    "accommodation_supplement_section_68_joint_tenant_exception_applies": False,
    "accommodation_supplement_self_contained_area_let_to_residents": 0,
    "accommodation_supplement_social_housing_weekly_contributions_paid": 0,
    "accommodation_supplement_sole_parent": True,
    "accommodation_supplement_super_or_veterans_pension_income_above_schedule_5_limit": False,
    "accommodation_supplement_total_premises_area": 100,
    "accommodation_supplement_weekly_board_and_lodgings_paid": 0,
    "accommodation_supplement_weekly_boarder_payments_received": 0,
    "accommodation_supplement_weekly_contributions_received_from_additional_residents": 0,
    "accommodation_supplement_weekly_rent_paid": 700,
    "accommodation_supplement_weekly_rent_received_from_other_residents": 0,
}
AS_REQUIRED_INPUTS = tuple(sorted(_AS_RENTER_FIXTURE))
AS_BOOLEAN_INPUTS = frozenset(
    name for name, value in _AS_RENTER_FIXTURE.items() if isinstance(value, bool)
)
_PROVENANCE_KINDS = frozenset(
    {"observed_nz", "donor_inherited", "derived", "assumed", "fixture"}
)


def make_as_fixture_inputs(
    family_ids: Sequence[int],
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Replicate one named companion scenario solely to test transport/runtime.

    Returns all 39 explicitly enumerated values and their fixture provenance.
    This does not infer policy inputs from a donor or represent a population.
    """
    ids = list(family_ids)
    if len(set(ids)) != len(ids):
        raise ValueError("Fixture family IDs must be unique.")
    table = pd.DataFrame({"family_id": ids})
    for name, value in _AS_RENTER_FIXTURE.items():
        table[name] = pd.Series(
            [value] * len(ids), dtype=bool if isinstance(value, bool) else float
        )
    return table, {name: "fixture" for name in AS_REQUIRED_INPUTS}


def accommodation_supplement_input_coverage(
    frame: Frame,
    *,
    provenance: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Report unweighted coverage without filling or treating absence as zero.

    Presence is separate from evidential provenance. Unknown provenance and bad
    types fail computation. An assumed zero remains an assumption; NaN/None and
    infinity are distinct failures. These are conservative eager-root coverage
    requirements for this exact module, not a legal minimum-input claim.
    """
    table = frame.table("family")
    provenance = dict(provenance or {})
    unknown_keys = sorted(set(provenance) - set(AS_REQUIRED_INPUTS))
    if unknown_keys:
        raise ValueError(f"Unknown AS provenance field(s): {unknown_keys}.")
    invalid = sorted(
        name for name, kind in provenance.items() if kind not in _PROVENANCE_KINDS
    )
    if invalid:
        raise ValueError(f"Unsupported AS provenance kind(s) for {invalid}.")
    rows = len(table)
    complete = np.ones(rows, dtype=bool)
    fields = {}
    for name in AS_REQUIRED_INPUTS:
        absent = name not in table
        null = np.zeros(rows, dtype=bool)
        nonfinite = np.zeros(rows, dtype=bool)
        invalid_dtype = False
        if absent:
            valid = np.zeros(rows, dtype=bool)
        else:
            column = table[name]
            null = column.isna().to_numpy()
            kind = column.dtype.kind
            invalid_dtype = (
                kind != "b" if name in AS_BOOLEAN_INPUTS else kind not in "iuf"
            )
            if not invalid_dtype:
                values = column.to_numpy(dtype=float, na_value=np.nan)
                nonfinite = ~np.isfinite(values) & ~null
            valid = ~null & ~nonfinite & ~np.full(rows, invalid_dtype)
        complete &= valid
        fields[name] = {
            "absent": absent,
            "null_rows": int(null.sum()),
            "nonfinite_rows": int(nonfinite.sum()),
            "invalid_dtype": invalid_dtype,
            "complete_rows": int(valid.sum()),
            "provenance": provenance.get(name, "unclassified"),
            "measurement": (
                "boolean"
                if name in AS_BOOLEAN_INPUTS
                else "NZD per week"
                if "weekly" in name
                else "NZD stock"
                if name.endswith("cash_assets")
                else "premises area in a common unit"
            ),
        }
    unclassified = sorted(set(AS_REQUIRED_INPUTS) - set(provenance))
    assumed = sorted(name for name, kind in provenance.items() if kind == "assumed")
    return {
        "program": "accommodation_supplement_core",
        "entity": "family",
        "rows": rows,
        "required_inputs": len(AS_REQUIRED_INPUTS),
        "complete_rows": int(complete.sum()),
        "incomplete_rows": int((~complete).sum()),
        "unclassified_fields": unclassified,
        "assumed_fields": assumed,
        "fields": fields,
        "ready_for_core_calculation": (
            rows > 0 and bool(complete.all()) and not unclassified and not assumed
        ),
        "full_entitlement_computable": False,
        "boundaries": list(AS_BOUNDARIES),
    }


class AccommodationSupplementEngine(AxiomEngine):
    """Axiom adapter with explicit coverage and a narrow snapshot contract."""

    def __init__(
        self,
        rulespec_root: str | Path,
        schema: EntitySchema,
        *,
        provenance: Mapping[str, str],
        allow_assumptions: bool = False,
    ) -> None:
        root = Path(rulespec_root)
        if not root.is_absolute() or root.resolve() != root:
            raise ValueError("Pass an explicit absolute canonical RuleSpec root.")
        module = root / AS_MODULE
        if hashlib.sha256(module.read_bytes()).hexdigest() != AS_MODULE_SHA256:
            raise ValueError("AS core module differs from the reviewed input contract.")
        if "family" not in schema.group_entities:
            raise ValueError("AS requires a separately constructed family entity.")
        super().__init__(
            module,
            schema,
            rulespec_roots=(root,),
            entity_names={entity: entity.capitalize() for entity in schema.entities},
        )
        self._provenance = dict(provenance)
        self._allow_assumptions = allow_assumptions

    def materialize(self, bundle, variables, period):
        if period != AS_SNAPSHOT_PERIOD:
            raise ValueError(
                "AS core binding supports only the April 2026 monthly snapshot; "
                "NZ tax-year aggregation and annualization are not implemented."
            )
        if set(variables) != set(AS_OUTPUTS) or len(variables) != len(AS_OUTPUTS):
            raise ValueError(
                "Request both AS core rate and non-rate judgment together."
            )
        report = accommodation_supplement_input_coverage(
            bundle, provenance=self._provenance
        )
        if (
            not report["rows"]
            or report["incomplete_rows"]
            or report["unclassified_fields"]
            or (report["assumed_fields"] and not self._allow_assumptions)
        ):
            raise ValueError(
                "AS core input coverage is incomplete, unclassified, or relies on "
                "unapproved assumptions: " + json.dumps(report, sort_keys=True)
            )
        if set(self.variables()) != set(AS_REQUIRED_INPUTS):
            raise ValueError(
                "Compiled Axiom roots differ from the reviewed AS contract."
            )
        results = dict(super().materialize(bundle, variables, period))
        # The shared graph accepts int64, not Axiom's int8 judgment arrays.
        # Widen only the storage dtype; preserve holds/not-holds/unknown codes.
        results[AS_OUTPUTS[0]] = results[AS_OUTPUTS[0]].astype(np.int64)
        return results


def calculate_accommodation_supplement(
    frame: Frame,
    *,
    rulespec_root: str | Path,
    provenance: Mapping[str, str],
    period: str = AS_SNAPSHOT_PERIOD,
    allow_assumptions: bool = False,
) -> Mapping[str, np.ndarray]:
    """Execute both raw core outputs with real Axiom, preserving their boundary."""
    return AccommodationSupplementEngine(
        rulespec_root,
        frame.schema,
        provenance=provenance,
        allow_assumptions=allow_assumptions,
    ).materialize(frame, AS_OUTPUTS, period)


def make_accommodation_supplement_kernel(
    rulespec_root: str | Path,
    schema: EntitySchema,
    *,
    provenance: Mapping[str, str],
    allow_assumptions: bool = False,
) -> SimulateRulesKernel:
    """Bind the existing shared graph kernel to the actual NZ Axiom adapter.

    The graph reference attests RuleSpec, runtime binary/wrapper bytes, helper,
    base adapter, schema, and every provenance/assumption setting. It is local
    development provenance, not an Axiom source-validation certificate.
    """
    engine = AccommodationSupplementEngine(
        rulespec_root,
        schema,
        provenance=provenance,
        allow_assumptions=allow_assumptions,
    )
    import axiom_rules_engine
    from axiom_rules_engine.dense import NativeCompiledDenseProgram

    if NativeCompiledDenseProgram is None:
        raise ImportError("AS requires the real Axiom native dense extension.")
    native = importlib.import_module(NativeCompiledDenseProgram.__module__)
    adapter = importlib.import_module(AxiomEngine.__module__)
    dense = importlib.import_module("axiom_rules_engine.dense")
    files = (
        Path(__file__),
        Path(adapter.__file__),
        Path(axiom_rules_engine.__file__),
        Path(dense.__file__),
        Path(native.__file__),
    )
    identity = {
        "module_sha256": AS_MODULE_SHA256,
        "implementation_sha256": [
            hashlib.sha256(p.read_bytes()).hexdigest() for p in files
        ],
        "schema": {"person": schema.person_entity, "groups": schema.group_entities},
        "period": AS_SNAPSHOT_PERIOD,
        "arithmetic": "decimal",
        "provenance": dict(provenance),
        "allow_assumptions": allow_assumptions,
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return SimulateRulesKernel(f"axiom.nz.as.core@sha256:{digest}", engine)
