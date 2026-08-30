"""Opt-in monetary inventories cannot silently alter a country's active solve."""

from __future__ import annotations

import copy
import json
from importlib import resources

import pytest

from microcosm.build.country_spec import load_country_spec
from microcosm.build.monetary_profile import MonetaryTargetProfile


@pytest.fixture
def payload():
    return json.loads(
        resources.files("microcosm.build")
        .joinpath("am/financial_wealth_targets.json")
        .read_text(encoding="utf-8")
    )


def test_country_loads_inventory_without_activating_it():
    country = load_country_spec("am")
    profile = country.monetary_profile
    assert profile.country == "am"
    assert profile.profile_id == "financial_wealth_2024"
    assert len(profile.targets) == 16
    assert len(country.target_references) == 8
    assert {target.reference.name for target in profile.targets}.isdisjoint(
        reference.name for reference in country.target_references
    )
    assert "financial_wealth_targets.json" in country.resource_hashes


def test_basis_and_readiness_are_explicit(payload):
    profile = MonetaryTargetProfile.from_mapping(payload, country="am")
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
    assert {target.reference.metadata["target_role"] for target in historical} == {
        "validation"
    }
    net = next(t for t in historical if "net_financial_worth" in t.reference.name)
    assert net.reference.signed
    assert net.reference.measure != "net_worth"


@pytest.mark.parametrize(
    ("key", "value"),
    [("country", "be"), ("schema_version", True), ("activation", "automatic")],
)
def test_rejects_wrong_profile_identity(payload, key, value):
    payload[key] = value
    with pytest.raises(ValueError):
        MonetaryTargetProfile.from_mapping(payload, country="am")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("value", 123),
        ("target", 123),
        ("assertion_policy", "allow_source_projection"),
        ("value_operation", "sum"),
        ("period", 2023),
        ("period", True),
        ("measure", None),
        ("filter", "arbitrary_filter"),
        ("se", 0.1),
        ("tolerance", 0.05),
        ("uprating_index", "gdp"),
    ],
)
def test_rejects_values_forecasts_implicit_aging_and_unbound_filters(
    payload, key, value
):
    payload["targets"][0]["reference"][key] = value
    with pytest.raises(ValueError):
        MonetaryTargetProfile.from_mapping(payload, country="am")


@pytest.mark.parametrize(
    ("key", "value"),
    [("readiness", "ready"), ("source_url", "http://example.com"), ("notes", "")],
)
def test_inventory_cannot_self_assert_activation(payload, key, value):
    payload["targets"][0][key] = value
    with pytest.raises(ValueError):
        MonetaryTargetProfile.from_mapping(payload, country="am")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("target_role", "validation"),
        ("activation_status", "requires_policy_output"),
        ("measure_kind", "policy_output"),
    ],
)
def test_reference_metadata_must_match_inventory(payload, key, value):
    payload["targets"][0]["reference"]["metadata"][key] = value
    with pytest.raises(ValueError):
        MonetaryTargetProfile.from_mapping(payload, country="am")


def test_rejects_duplicate_target_names_and_prepared_columns(payload):
    duplicate = copy.deepcopy(payload["targets"][0])
    payload["targets"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate target"):
        MonetaryTargetProfile.from_mapping(payload, country="am")
    duplicate["reference"]["name"] = "another_target"
    with pytest.raises(ValueError, match="duplicate prepared"):
        MonetaryTargetProfile.from_mapping(payload, country="am")


def test_existing_countries_have_no_implicitly_invented_financial_profile():
    assert load_country_spec("be").monetary_profile is None


def test_country_loader_validates_optional_profile(tmp_path, payload):
    import shutil

    source = resources.files("microcosm.build").joinpath("am")
    destination = tmp_path / "am"
    shutil.copytree(str(source), destination)
    payload["targets"][0]["basis"]["temporal_basis"] = "monthly_flow"
    (destination / "financial_wealth_targets.json").write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        load_country_spec(destination)
