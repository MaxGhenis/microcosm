"""Contracts for the generic, value-free monetary inventory profile."""

from __future__ import annotations

import copy
import json
import shutil
from importlib import resources

import pytest

from microcosm.build.country_spec import load_country_spec
from microcosm.build.monetary_profile import MonetaryTargetProfile


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
                "source_url": "https://example.test/payroll",
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
        (("targets", 0, "source_url"), "http://example.test"),
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
