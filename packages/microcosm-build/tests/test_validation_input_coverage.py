"""US validation-input coverage gate: no validation row scores a structural zero.

Replays the invisible-gap class the gate exists to catch (microcosm#252/#253):
a validation config scores a provision whose effect is driven by a pure-input
leaf that no source stage produces, so the row validates as a silent zero. The
plant-a-missing-leaf test proves the gate fails loudly in exactly that case; the
registry-consistency test proves the seed entries are real provision input
leaves against the live PolicyEngine-US graph (so the registry cannot rot).
"""

from __future__ import annotations

import importlib.util

import pytest

from microcosm.build.us_runtime import (
    US_QBI_OUTPUT_COLUMNS,
    US_VALIDATION_PROVISION_INPUT_LEAVES,
    US_VALIDATION_PROVISION_PERIOD,
    ValidationInputLeaf,
    assert_validation_leaf_registry_current,
    registered_leaf_ownership,
    us_source_stage_outputs,
    us_validation_input_coverage_gate,
)
from microcosm.build.us_runtime.validation_input_coverage import (
    us_validation_input_leaf_requirements,
    us_validation_input_leaf_reviewed_exclusions,
)

policyengine_us_installed = importlib.util.find_spec("policyengine_us") is not None
requires_us = pytest.mark.skipif(
    not policyengine_us_installed,
    reason="requires the policyengine-us [us] extra (build environment)",
)


class TestUsSourceStageOutputs:
    def test_reads_shipped_manifest_outputs(self) -> None:
        outputs = us_source_stage_outputs()
        # A representative PUF income leaf declared by the tax-detail stage.
        assert "employment_income_before_lsr" in outputs
        assert "student_loan_interest" in outputs
        assert "fsla_overtime_premium" in outputs
        # Tuition and qualifying auto-loan interest are declared source-stage
        # outputs and may no longer hide behind exclusions.
        assert "qualified_tuition_expenses" in outputs
        assert "qualified_passenger_vehicle_loan_interest" in outputs
        assert "household_vehicles_owned" in outputs
        assert "household_vehicles_value" in outputs
        assert "traditional_401k_contributions_desired" in outputs
        assert "roth_401k_contributions_desired" in outputs
        assert "traditional_ira_contributions_desired" in outputs
        assert "roth_ira_contributions_desired" in outputs
        assert "self_employed_pension_contributions_desired" in outputs
        assert "takes_up_ssi_if_eligible" in outputs
        assert "takes_up_head_start_if_eligible" in outputs
        assert "weeks_unemployed" in outputs
        assert "casualty_loss" in outputs
        assert "domestic_production_ald" in outputs
        assert "unreimbursed_business_employee_expenses" in outputs
        assert "spm_unit_pre_subsidy_childcare_expenses" in outputs
        assert "spm_unit_energy_subsidy" in outputs
        assert "child_support_received" in outputs
        assert "child_support_expense" in outputs
        assert "disability_benefits" in outputs
        assert "educator_expense" in outputs
        assert "other_health_insurance_premiums" in outputs
        assert "farm_operations_income" in outputs
        assert "farm_rent_income" in outputs
        assert set(US_QBI_OUTPUT_COLUMNS) <= outputs


class TestUsValidationInputCoverageGate:
    def test_shipped_config_passes_without_reviewed_exclusions(self) -> None:
        result = us_validation_input_coverage_gate()
        assert result.passed, result.failures
        assert result.details["reviewed_exclusions"] == {}
        assert result.details["missing"] == []
        requirements = us_validation_input_leaf_requirements()
        assert requirements["tip_income"] == ["obbba_no_tax_on_tips"]
        assert requirements["treasury_tipped_occupation_code"] == [
            "obbba_no_tax_on_tips"
        ]
        assert requirements["fsla_overtime_premium"] == ["obbba_no_tax_on_overtime"]
        assert requirements["qualified_passenger_vehicle_loan_interest"] == [
            "obbba_auto_loan_interest"
        ]
        for leaf in (
            "traditional_401k_contributions_desired",
            "roth_401k_contributions_desired",
            "traditional_ira_contributions_desired",
            "roth_ira_contributions_desired",
            "self_employed_pension_contributions_desired",
        ):
            assert requirements[leaf] == ["soi_savers_credit"]
        assert requirements["casualty_loss"] == ["obbba_casualty_loss_limit"]
        assert requirements["unreimbursed_business_employee_expenses"] == [
            "obbba_misc_itemized_deductions"
        ]
        assert requirements["spm_unit_pre_subsidy_childcare_expenses"] == [
            "obbba_cdcc",
            "soi_cdcc",
            "te_cdcc",
        ]

    def test_planted_missing_leaf_fails_loudly(self) -> None:
        # Plant a NEW validation row whose provision keys on an un-imputed,
        # un-allowlisted input leaf. This is the #252/#253 pattern: the gate
        # must fail and name the variable and the affected row.
        planted = us_validation_input_leaf_requirements()
        planted["some_new_unimputed_input"] = ["obbba_new_untested_provision"]

        from microcosm.build.gates import source_stage_input_coverage_gate

        result = source_stage_input_coverage_gate(
            planted,
            declared_outputs=us_source_stage_outputs(),
            reviewed_exclusions=us_validation_input_leaf_reviewed_exclusions(),
            name="us_validation_input_coverage",
        )
        assert not result.passed
        assert any("some_new_unimputed_input" in line for line in result.failures)
        assert any("obbba_new_untested_provision" in line for line in result.failures)
        assert result.details["missing"] == ["some_new_unimputed_input"]

    def test_shipped_gate_fails_when_registry_gains_an_unimputed_leaf(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Same plant, but through the public gate entry point: appending a
        # registry entry with no reason for a leaf no stage produces must make
        # us_validation_input_coverage_gate() itself fail. This is the guard a
        # future validation row (a new provision keying on an un-imputed leaf)
        # trips in CI instead of shipping a silent zero.
        from microcosm.build.us_runtime import validation_input_coverage as module

        planted = (
            *module.US_VALIDATION_PROVISION_INPUT_LEAVES,
            ValidationInputLeaf(
                leaf="some_new_unimputed_input",
                provision_variables=("some_new_provision",),
                validation_rows=("obbba_new_untested_provision",),
                # No reason: this leaf is expected to be present, not a tracked gap.
            ),
        )
        monkeypatch.setattr(module, "US_VALIDATION_PROVISION_INPUT_LEAVES", planted)

        result = us_validation_input_coverage_gate()
        assert not result.passed
        assert result.details["missing"] == ["some_new_unimputed_input"]
        assert any("obbba_new_untested_provision" in line for line in result.failures)

    def test_removing_tuition_from_outputs_makes_the_row_fail(self) -> None:
        requirements = us_validation_input_leaf_requirements()

        from microcosm.build.gates import source_stage_input_coverage_gate

        result = source_stage_input_coverage_gate(
            requirements,
            declared_outputs=us_source_stage_outputs() - {"qualified_tuition_expenses"},
            reviewed_exclusions={},
            name="us_validation_input_coverage",
        )
        assert not result.passed
        assert set(result.details["missing"]) == {"qualified_tuition_expenses"}

    def test_removing_casualty_loss_makes_the_obbba_row_fail(self) -> None:
        requirements = us_validation_input_leaf_requirements()

        from microcosm.build.gates import source_stage_input_coverage_gate

        result = source_stage_input_coverage_gate(
            requirements,
            declared_outputs=us_source_stage_outputs() - {"casualty_loss"},
            reviewed_exclusions={},
            name="us_validation_input_coverage",
        )
        assert not result.passed
        assert set(result.details["missing"]) == {"casualty_loss"}

    def test_removing_misc_expense_makes_the_obbba_row_fail(self) -> None:
        requirements = us_validation_input_leaf_requirements()
        leaf = "unreimbursed_business_employee_expenses"

        from microcosm.build.gates import source_stage_input_coverage_gate

        result = source_stage_input_coverage_gate(
            requirements,
            declared_outputs=us_source_stage_outputs() - {leaf},
            reviewed_exclusions={},
            name="us_validation_input_coverage",
        )
        assert not result.passed
        assert set(result.details["missing"]) == {leaf}

    def test_removing_childcare_makes_cdcc_rows_fail(self) -> None:
        requirements = us_validation_input_leaf_requirements()
        leaf = "spm_unit_pre_subsidy_childcare_expenses"

        from microcosm.build.gates import source_stage_input_coverage_gate

        result = source_stage_input_coverage_gate(
            requirements,
            declared_outputs=us_source_stage_outputs() - {leaf},
            reviewed_exclusions={},
            name="us_validation_input_coverage",
        )
        assert not result.passed
        assert set(result.details["missing"]) == {leaf}


class TestValidationInputLeafRegistry:
    def test_every_entry_names_rows_and_provisions(self) -> None:
        assert US_VALIDATION_PROVISION_INPUT_LEAVES
        for entry in US_VALIDATION_PROVISION_INPUT_LEAVES:
            assert entry.leaf
            assert entry.provision_variables
            assert entry.validation_rows

    def test_entry_requires_provision_variables(self) -> None:
        with pytest.raises(ValueError, match="provision_variables is required"):
            ValidationInputLeaf(
                leaf="x", provision_variables=(), validation_rows=("r",)
            )

    def test_entry_requires_validation_rows(self) -> None:
        with pytest.raises(ValueError, match="validation_rows is required"):
            ValidationInputLeaf(
                leaf="x", provision_variables=("v",), validation_rows=()
            )

    def test_registry_leaves_are_provision_inputs_when_configs_are_present(
        self,
    ) -> None:
        # Every registered leaf must be a validation-config row id that actually
        # exists in the shipped configs, so a failure names a real row.
        import json
        from importlib.resources import files

        row_ids: set[str] = set()
        for filename, key in (
            ("obbba_reforms.json", "reforms"),
            ("tax_expenditure_reforms.json", "reforms"),
            ("soi_baseline_levels.json", "levels"),
        ):
            payload = json.loads((files("microcosm.build.us") / filename).read_text())
            row_ids.update(row["id"] for row in payload.get(key, ()))
        for entry in US_VALIDATION_PROVISION_INPUT_LEAVES:
            for row in entry.validation_rows:
                assert row in row_ids, (
                    f"{entry.leaf} registered under unknown validation row {row!r}"
                )

    @requires_us
    def test_registry_is_current_against_live_engine_graph(self) -> None:
        # The anti-rot check: each registered leaf is a pure input leaf and a
        # dependency of its provision variable per the live PolicyEngine-US
        # graph. Runs only where the [us] extra is installed.
        assert_validation_leaf_registry_current(period=US_VALIDATION_PROVISION_PERIOD)

    def test_registry_check_requires_an_explicit_period(self) -> None:
        # The provision evaluation period is not the dataset build period, so
        # no caller may inherit a default (microcosm issue #301).
        with pytest.raises(TypeError):
            assert_validation_leaf_registry_current()


class _OwnershipStub:
    """Minimal dated-ownership engine mirroring the adapter's contract."""

    def __init__(self, ownership: dict[str, dict[int, object]]) -> None:
        self._ownership = ownership

    def variable_ownership(self, name: str, *, period: int) -> object:
        by_period = self._ownership.get(name)
        if by_period is None:
            raise ValueError(f"Unknown PolicyEngine-US source variable {name!r}.")
        return by_period[period]


class _Ownership:
    def __init__(self, kind: str) -> None:
        self.kind = kind

    @property
    def computed(self) -> bool:
        return self.kind != "INPUT"


class TestRegisteredLeafOwnership:
    """The dated ownership view the registry check classifies leaves with."""

    def test_future_formula_leaf_is_an_input_before_it_commences(self) -> None:
        engine = _OwnershipStub(
            {
                "later_formula_leaf": {
                    2026: _Ownership("INPUT"),
                    2030: _Ownership("FORMULA"),
                }
            }
        )

        assert (
            registered_leaf_ownership(engine, ["later_formula_leaf"], period=2026) == {}
        )
        assert registered_leaf_ownership(
            engine, ["later_formula_leaf"], period=2030
        ) == {"later_formula_leaf": "FORMULA"}

    def test_carry_forward_delegation_is_reported_as_owned(self) -> None:
        engine = _OwnershipStub(
            {
                "weeks_worked": {
                    2024: _Ownership("INPUT"),
                    2025: _Ownership("DELEGATION"),
                }
            }
        )

        assert registered_leaf_ownership(engine, ["weeks_worked"], period=2024) == {}
        assert registered_leaf_ownership(engine, ["weeks_worked"], period=2025) == {
            "weeks_worked": "DELEGATION"
        }

    def test_name_absent_from_the_source_index_is_reported_not_assumed(self) -> None:
        engine = _OwnershipStub({})

        assert registered_leaf_ownership(engine, ["mystery"], period=2026) == {
            "mystery": "UNKNOWN"
        }
