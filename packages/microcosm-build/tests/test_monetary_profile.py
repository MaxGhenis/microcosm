"""Contracts for the generic, value-free monetary inventory profile."""

from __future__ import annotations

import copy

import pytest

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


def _policy_payload() -> dict[str, object]:
    """A policy-output inventory row the policy binder can actually bind."""
    payload = copy.deepcopy(_payload())
    row = payload["targets"][0]
    row["readiness"] = "requires_policy_output"
    row["reference"]["period_match_policy"] = "exact"
    row["reference"]["metadata"].update(
        {
            "activation_status": "requires_policy_output",
            "measure_kind": "policy_derived",
        }
    )
    return payload


def test_policy_output_profile_accepts_only_policy_derived_measure_kind():
    payload = _policy_payload()
    profile = MonetaryTargetProfile.from_mapping(payload, country="xx")
    assert profile.targets[0].readiness == "requires_policy_output"
    assert profile.targets[0].reference.period_match_policy == "exact"

    payload["targets"][0]["reference"]["metadata"]["measure_kind"] = "prepared_column"
    with pytest.raises(ValueError, match="policy_derived"):
        MonetaryTargetProfile.from_mapping(payload, country="xx")


def test_policy_output_profile_requires_an_exact_period_match():
    """The binder requires exact matching, so the inventory must too."""
    payload = _policy_payload()
    payload["targets"][0]["reference"]["period_match_policy"] = "latest_not_after"
    with pytest.raises(ValueError, match="requires period_match_policy 'exact'"):
        MonetaryTargetProfile.from_mapping(payload, country="xx")


def test_policy_output_profile_requires_an_annual_flow_basis():
    """Closing-stock policy contracts are unbindable, so they are refused."""
    payload = _policy_payload()
    payload["targets"][0]["basis"] |= {
        "temporal_basis": "closing_stock",
        "period": "2024-12-31",
    }
    with pytest.raises(ValueError, match="requires an annual_flow"):
        MonetaryTargetProfile.from_mapping(payload, country="xx")


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
