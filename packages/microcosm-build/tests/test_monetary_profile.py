"""Contracts for the generic, value-free monetary inventory profile."""

from __future__ import annotations

import copy
import json
import shutil
from dataclasses import replace
from importlib import resources
from typing import get_type_hints

import numpy as np
import pandas as pd
import pytest

from microcosm.build.country_spec import ResolvedCountrySpec, load_country_spec
from microcosm.build.ledger_targets import compile_ledger_target_references
from microcosm.build.monetary_profile import MonetaryTargetProfile
from microcosm.build.monetary_targets import (
    MonetaryBasis,
    bind_monetary_target,
    prepare_monetary_measure,
)
from microcosm.calibrate import TargetRegistry, build_constraint_matrix
from microcosm.frame import EntitySchema, Frame, WeightKind, Weights


def _payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "country": "xx",
        "profile_id": "financial_accounts_2024",
        "activation": "explicit_only",
        "description": "Synthetic inventory without observed values.",
        "targets": [
            {
                "reference": {
                    "name": "synthetic/payroll",
                    "ledger_source_record_id": "synthetic.payroll",
                    "entity": "person",
                    "measure": "employment_income",
                    "period": 2024,
                    "family": "income",
                    "period_match_policy": "exact",
                    "metadata": {
                        "monetary_target_role": "calibration",
                        "activation_status": "requires_prepared_measure",
                        "measure_kind": "prepared_column",
                    },
                },
                "basis": {
                    "currency": "XXX",
                    "unit": "base_currency",
                    "period": "2024",
                    "temporal_basis": "annual_flow",
                    "sector": "S14",
                    "perimeter": "resident employee compensation",
                    "valuation": "nominal",
                },
                "readiness": "requires_prepared_measure",
                "source_urls": ["https://example.test/payroll"],
                "notes": "Requires a prepared entity-aligned amount column.",
            }
        ],
    }


def test_profile_is_value_free_and_explicitly_inactive():
    profile = MonetaryTargetProfile.from_mapping(_payload(), country="xx")
    assert profile.country == "xx"
    assert profile.targets[0].basis.temporal_basis == "annual_flow"
    assert profile.targets[0].reference.measure == "employment_income"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("activation",), "automatic"),
        (("targets", 0, "reference", "value"), 100),
        (("targets", 0, "reference", "value_operation"), "sum"),
        (("targets", 0, "reference", "filter"), "included"),
        (("targets", 0, "source_urls", 0), "http://example.test"),
        (("targets", 0, "readiness"), "ready"),
    ],
)
def test_profile_refuses_activation_values_or_implicit_transforms(path, value):
    payload = copy.deepcopy(_payload())
    location = payload
    for key in path[:-1]:
        location = location[key]
    location[path[-1]] = value
    with pytest.raises(ValueError):
        MonetaryTargetProfile.from_mapping(payload, country="xx")


@pytest.fixture
def am_payload():
    return json.loads(
        resources.files("microcosm.build")
        .joinpath("am/financial_wealth_targets.json")
        .read_text(encoding="utf-8")
    )


def test_armenia_loads_inventory_without_activating_it():
    country = load_country_spec("am")
    profile = country.monetary_profile

    assert profile is not None
    assert profile.country == "am"
    assert profile.profile_id == "financial_wealth_2024"
    assert len(profile.targets) == 16
    assert len(country.target_references) == 8
    assert {target.reference.name for target in profile.targets}.isdisjoint(
        reference.name for reference in country.target_references
    )
    assert "financial_wealth_targets.json" in country.resource_hashes


def test_armenia_basis_and_readiness_are_explicit(am_payload):
    profile = MonetaryTargetProfile.from_mapping(am_payload, country="am")
    candidates = {
        target.reference.name
        for target in profile.targets
        if target.readiness == "requires_prepared_measure"
    }
    assert candidates == {
        "armstat_src_gross_payroll_annual",
        "cba_resident_household_deposits",
    }
    historical = [
        target
        for target in profile.targets
        if target.readiness == "historical_validation_only"
    ]
    assert len(historical) == 7
    assert {target.basis.period for target in historical} == {"2023-12-31"}
    assert {target.reference.period for target in historical} == {"2023-12-31"}
    assert {target.reference.period_match_policy for target in profile.targets} == {
        "exact"
    }
    assert {target.basis.sector for target in historical} == {"S14+S15"}
    assert {
        target.reference.metadata["monetary_target_role"] for target in historical
    } == {"validation"}
    net = next(t for t in historical if "net_financial_worth" in t.reference.name)
    assert net.reference.signed
    assert net.reference.measure != "net_worth"


@pytest.mark.parametrize(
    ("key", "value"),
    [("country", "be"), ("schema_version", True), ("activation", "automatic")],
)
def test_armenia_rejects_wrong_profile_identity(am_payload, key, value):
    am_payload[key] = value
    with pytest.raises(ValueError):
        MonetaryTargetProfile.from_mapping(am_payload, country="am")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("monetary_target_role", "validation"),
        ("activation_status", "requires_policy_output"),
        ("measure_kind", "policy_output"),
    ],
)
def test_armenia_reference_metadata_matches_inventory(am_payload, key, value):
    am_payload["targets"][0]["reference"]["metadata"][key] = value
    with pytest.raises(ValueError):
        MonetaryTargetProfile.from_mapping(am_payload, country="am")


def test_armenia_rejects_duplicate_targets_and_prepared_columns(am_payload):
    duplicate = copy.deepcopy(am_payload["targets"][0])
    am_payload["targets"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate target"):
        MonetaryTargetProfile.from_mapping(am_payload, country="am")
    duplicate["reference"]["name"] = "another_target"
    with pytest.raises(ValueError, match="duplicate prepared"):
        MonetaryTargetProfile.from_mapping(am_payload, country="am")


def test_existing_country_has_no_implicitly_invented_financial_profile():
    assert load_country_spec("be").monetary_profile is None


def test_country_loader_validates_optional_profile(tmp_path, am_payload):
    source = resources.files("microcosm.build").joinpath("am")
    destination = tmp_path / "am"
    shutil.copytree(str(source), destination)
    am_payload["targets"][0]["basis"]["temporal_basis"] = "monthly_flow"
    (destination / "financial_wealth_targets.json").write_text(
        json.dumps(am_payload), encoding="utf-8"
    )

    with pytest.raises(ValueError):
        load_country_spec(destination)


@pytest.mark.parametrize(
    "path",
    [
        ("targets", 0, "reference", "ledger_selector", "value"),
        ("targets", 0, "reference", "ledger_selector", "observed_value"),
        ("targets", 0, "reference", "metadata", "observed_value"),
    ],
)
def test_profile_rejects_nested_observed_value_keys(am_payload, path):
    location = am_payload
    for key in path[:-1]:
        location = location[key]
    location[path[-1]] = "smuggled"
    with pytest.raises(ValueError, match="value-free"):
        MonetaryTargetProfile.from_mapping(am_payload, country="am")


def test_loaded_profile_references_are_deeply_immutable():
    country = load_country_spec("am")
    fingerprint = country.fingerprint
    reference = country.monetary_profile.targets[0].reference

    with pytest.raises(TypeError, match="immutable"):
        reference.ledger_selector["source_name"] = "mutated"
    with pytest.raises(TypeError, match="immutable"):
        reference.metadata["activation_status"] = "active"

    assert country.fingerprint == fingerprint
    assert load_country_spec("am").fingerprint == fingerprint

    payload = _payload()
    payload["targets"][0]["reference"]["ledger_selector"] = {
        "dimension_values": {"band": ["A", "B"]}
    }
    synthetic = MonetaryTargetProfile.from_mapping(payload, country="xx")
    nested = synthetic.targets[0].reference.ledger_selector["dimension_values"]
    with pytest.raises(TypeError, match="immutable"):
        nested["band"] = ["C"]
    with pytest.raises(TypeError, match="immutable"):
        nested["band"].append("C")


def test_country_loader_rejects_name_collision_with_default_targets(
    tmp_path, am_payload
):
    source = resources.files("microcosm.build").joinpath("am")
    destination = tmp_path / "am"
    shutil.copytree(str(source), destination)
    active_name = json.loads(
        (destination / "target_references.json").read_text(encoding="utf-8")
    )["target_references"][0]["name"]
    am_payload["targets"][0]["reference"]["name"] = active_name
    (destination / "financial_wealth_targets.json").write_text(
        json.dumps(am_payload), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="must be disjoint"):
        load_country_spec(destination)


def test_resolved_country_spec_runtime_type_hints_include_monetary_profile():
    hints = get_type_hints(ResolvedCountrySpec)
    assert "monetary_profile" in hints


def test_armenia_profile_contract_is_required_and_carried_on_binding():
    profile = load_country_spec("am").monetary_profile
    contract = next(
        target
        for target in profile.targets
        if target.reference.name == "cba_resident_household_deposits"
    )
    prepared = prepare_monetary_measure(
        np.array([1.0, 2.0]),
        record_ids=np.array([1, 2]),
        basis=contract.basis,
        factor=1.0,
        source_identity_sha256="a" * 64,
        bridge_description="Synthetic Armenia deposit allocation probe.",
        bridge_source_sha256="b" * 64,
    )

    with pytest.raises(ValueError, match="complete monetary contract"):
        bind_monetary_target(
            contract.reference,
            value=3,
            source_basis=contract.basis,
            source_assertion="observation",
            source_identity_sha256="c" * 64,
            prepared=prepared,
        )

    target = bind_monetary_target(
        contract,
        value=3,
        source_basis=contract.basis,
        source_assertion="observation",
        source_identity_sha256="c" * 64,
        prepared=prepared,
    )
    receipt = json.loads(target.metadata["monetary_contract"])
    assert receipt["basis"] == {
        "currency": "AMD",
        "unit": "base_currency",
        "period": "2024-12-31",
        "temporal_basis": "closing_stock",
        "sector": "resident_households",
        "perimeter": (
            "resident_household_deposits_domestic_banks_excluding_accrued_interest"
        ),
        "valuation": "nominal_balance_amd_equivalent",
    }
    assert target.source == contract.source_urls[0]
    assert target.notes == contract.notes
    assert len(target.metadata["monetary_contract_sha256"]) == 64
    frame = Frame(
        {
            "person": pd.DataFrame(
                {"person_id": [1, 2], "person_household_id": [1, 2]}
            ),
            "household": pd.DataFrame(
                {"household_id": [1, 2], "deposit_assets_amd": [1.0, 2.0]}
            ),
        },
        EntitySchema(group_entities=("household",)),
        {"household": Weights(np.ones(2), WeightKind.DESIGN)},
    )
    problem = build_constraint_matrix(
        frame, TargetRegistry([target], country="am").to_target_set()
    )
    np.testing.assert_array_equal(problem.estimates(np.ones(2)), [3.0])


def test_armenia_profile_contract_rejects_caller_supplied_wrong_basis():
    profile = load_country_spec("am").monetary_profile
    contract = next(
        target
        for target in profile.targets
        if target.reference.name == "cba_resident_household_deposits"
    )
    wrong_basis = MonetaryBasis(
        currency="USD",
        unit="base_currency",
        period="2024",
        temporal_basis="annual_flow",
        sector="nonresident_corporations",
        perimeter="worldwide_assets",
        valuation="market_value",
    )
    prepared = prepare_monetary_measure(
        np.array([1.0, 2.0]),
        record_ids=np.array([1, 2]),
        basis=wrong_basis,
        factor=1.0,
        source_identity_sha256="a" * 64,
        bridge_description="Deliberately incompatible basis probe.",
        bridge_source_sha256="b" * 64,
    )

    with pytest.raises(ValueError, match="contract basis mismatch"):
        bind_monetary_target(
            contract,
            value=3,
            source_basis=wrong_basis,
            source_assertion="observation",
            source_identity_sha256="c" * 64,
            prepared=prepared,
        )


def test_armenia_exact_period_contract_refuses_stale_observation():
    profile = load_country_spec("am").monetary_profile
    payroll = next(
        target
        for target in profile.targets
        if target.reference.name == "armstat_src_gross_payroll_annual"
    )
    active = replace(
        payroll.reference,
        metadata={**payroll.reference.metadata, "activation_status": "active"},
    )
    stale_fact = {
        "aggregate_fact_key": "ledger.aggregate_fact.v2:stale-payroll",
        "lineage": {"source_record_id": "armstat.payroll.2023"},
        "value": 1.0,
        "period": {"type": "year", "value": 2023},
        "geography": {"level": "country", "id": "AM"},
        "observed_measure": {
            "source_name": "armstat_src_payroll_register",
            "source_measure_id": "annual_gross_payroll",
        },
    }

    with pytest.raises(ValueError, match="exact target period"):
        compile_ledger_target_references([stale_fact], [active], country="am")
