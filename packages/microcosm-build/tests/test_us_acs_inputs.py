from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from microcosm.build.us_runtime.acs_inputs import map_acs_native_inputs
from microcosm.build.us_runtime.operator_boundary import (
    assert_operator_free_source_frame,
)
from microcosm.frame import US_SCHEMA, Frame, WeightKind, Weights


def _acs_frame() -> Frame:
    person = pd.DataFrame(
        {
            "person_id": [1, 2],
            "person_household_id": [1, 1],
            "person_tax_unit_id": [1, 1],
            "person_spm_unit_id": [1, 1],
            "person_family_id": [1, 1],
            "person_marital_unit_id": [1, 2],
            "AGEP": [40, 12],
            "SEX": [2, 1],
            "RELSHIPP": [20, 25],
            "ADJINC": [1_100_000, 1_100_000],
            "WAGP": [50_000.0, np.nan],
            "SEMP": [-500.0, np.nan],
            "SSP": [1_000.0, np.nan],
            "SSIP": [200.0, np.nan],
            "RETP": [300.0, np.nan],
            "INTP": [-100.0, np.nan],
        }
    )
    tables = {
        "person": person,
        "household": pd.DataFrame(
            {
                "household_id": [1],
                "ADJHSG": [1_250_000],
                "TEN": [3],
                "TYPEHUGQ": [1],
                "RNTP": [1_000.0],
                "GRNTP": [1_200.0],
                "TAXAMT": [np.nan],
            }
        ),
        "tax_unit": pd.DataFrame(
            {"tax_unit_id": [1], "filing_status_input": ["HEAD_OF_HOUSEHOLD"]}
        ),
        "spm_unit": pd.DataFrame({"spm_unit_id": [1]}),
        "family": pd.DataFrame({"family_id": [1]}),
        "marital_unit": pd.DataFrame({"marital_unit_id": [1, 2]}),
    }
    return Frame(
        tables,
        US_SCHEMA,
        {"household": Weights(np.array([10.0]), WeightKind.DESIGN)},
        pd.Series(["acs_2024_1yr", "acs_2024_1yr"], name="stratum"),
    )


def test_acs_demographic_and_relationship_mapping_is_native() -> None:
    result = map_acs_native_inputs(_acs_frame())
    person = result.frame.table("person")

    assert person["age"].tolist() == [40.0, 12.0]
    assert person["is_female"].tolist() == [True, False]
    assert person["is_household_head"].tolist() == [True, False]
    assert result.native_inputs["age"]["source_columns"] == ["AGEP"]
    assert result.native_inputs["is_household_head"]["source_columns"] == ["RELSHIPP"]


def test_acs_income_mapping_adjusts_native_dollars_without_splitting_aggregates() -> (
    None
):
    result = map_acs_native_inputs(_acs_frame())
    person = result.frame.table("person")

    assert person.loc[0, "employment_income_before_lsr"] == pytest.approx(55_000.0)
    assert person.loc[0, "self_employment_income_before_lsr"] == pytest.approx(-550.0)
    assert person.loc[0, "ssi_reported"] == pytest.approx(220.0)
    assert person.loc[0, "acs_social_security_income"] == pytest.approx(1_100.0)
    assert person.loc[0, "acs_retirement_income"] == pytest.approx(330.0)
    assert person.loc[0, "acs_interest_dividend_rental_income"] == pytest.approx(-110.0)
    assert pd.isna(person.loc[1, "employment_income_before_lsr"])
    assert pd.isna(person.loc[1, "acs_retirement_income"])
    assert "social_security" not in person
    assert "taxable_private_pension_income" not in person
    assert "interest_income" not in person
    assert result.native_inputs["acs_social_security_income"]["transformation"] == (
        "SSP * ADJINC / 1_000_000"
    )
    assert result.native_inputs["employment_income_before_lsr"]["observed_rows"] == 1
    assert result.native_inputs["employment_income_before_lsr"]["missing_rows"] == 1


def test_acs_housing_mapping_preserves_rent_without_synthesizing_model_rent() -> None:
    result = map_acs_native_inputs(_acs_frame())
    person = result.frame.table("person")
    household = result.frame.table("household")
    spm_unit = result.frame.table("spm_unit")

    assert household["tenure_type"].tolist() == ["RENTED"]
    assert spm_unit["spm_unit_tenure_type"].tolist() == ["RENTER"]
    assert household["acs_monthly_contract_rent"].tolist() == [1_250.0]
    assert household["acs_monthly_gross_rent"].tolist() == [1_500.0]
    assert household["acs_annual_property_tax"].tolist() == [0.0]
    assert "pre_subsidy_rent" not in person
    assert person["real_estate_taxes"].tolist() == [0.0, 0.0]
    assert result.native_inputs["real_estate_taxes"]["source_domain"] == {
        "version": 1,
        "owner_housing_rows": 0,
        "owner_observed_rows": 0,
        "renter_or_no_rent_structural_zero_rows": 1,
        "group_quarters_structural_zero_rows": 0,
        "structural_zero_rule": (
            "TAXAMT blank-or-zero outside owner-occupied housing; owner blank refused"
        ),
    }
    assert result.native_inputs["acs_monthly_contract_rent"]["source_columns"] == [
        "RNTP",
        "ADJHSG",
    ]


def test_property_tax_native_domain_receipt_crosses_operator_boundary() -> None:
    result = map_acs_native_inputs(_acs_frame())

    assert result.native_inputs["acs_annual_property_tax"]["source_columns"] == [
        "TAXAMT",
        "ADJHSG",
        "TEN",
        "TYPEHUGQ",
    ]
    assert result.native_inputs["real_estate_taxes"]["source_columns"] == [
        "TAXAMT",
        "ADJHSG",
        "TEN",
        "TYPEHUGQ",
        "RELSHIPP",
    ]
    assert_operator_free_source_frame(
        result.frame,
        label="mapped ACS property-tax fixture",
        native_inputs=result.native_inputs,
    )

    forged = {
        output: dict(receipt) for output, receipt in result.native_inputs.items()
    }
    forged["real_estate_taxes"] = {
        **forged["real_estate_taxes"],
        "source_domain": {
            **forged["real_estate_taxes"]["source_domain"],
            "group_quarters_structural_zero_rows": 1,
        },
    }
    with pytest.raises(ValueError, match="live ACS real-estate-tax domain"):
        assert_operator_free_source_frame(
            result.frame,
            label="forged ACS property-tax fixture",
            native_inputs=forged,
        )


def test_acs_owner_property_tax_mapping_places_observed_amount_on_head() -> None:
    frame = _acs_frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    household = tables["household"]
    household["TEN"] = 1
    household["RNTP"] = np.nan
    household["GRNTP"] = np.nan
    household["TAXAMT"] = 2_400.0
    owner = Frame(
        tables,
        frame.schema,
        {"household": frame.weights_for("household")},
        frame.strata,
    )

    result = map_acs_native_inputs(owner)

    assert result.frame.table("household")["tenure_type"].tolist() == [
        "OWNED_WITH_MORTGAGE"
    ]
    assert result.frame.table("person")["real_estate_taxes"].tolist() == [
        3_000.0,
        0.0,
    ]


def test_acs_owner_property_tax_mapping_refuses_blank_source() -> None:
    frame = _acs_frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    tables["household"]["TEN"] = 2
    owner = Frame(
        tables,
        frame.schema,
        {"household": frame.weights_for("household")},
        frame.strata,
    )

    with pytest.raises(ValueError, match="owner-housing TAXAMT must be observed"):
        map_acs_native_inputs(owner)


def test_acs_group_quarters_blank_tenure_is_not_synthesized() -> None:
    frame = _acs_frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    household = tables["household"]
    household["TEN"] = np.nan
    household["TYPEHUGQ"] = 3
    household[["RNTP", "GRNTP", "TAXAMT"]] = np.nan
    group_quarters = Frame(
        tables,
        frame.schema,
        {"household": frame.weights_for("household")},
        frame.strata,
    )

    result = map_acs_native_inputs(group_quarters)

    assert result.frame.table("household")["tenure_type"].isna().all()
    assert result.frame.table("spm_unit")["spm_unit_tenure_type"].isna().all()
    assert result.native_inputs["tenure_type"]["observed_rows"] == 0
    assert result.native_inputs["tenure_type"]["missing_rows"] == 1
    assert result.frame.table("household")["acs_annual_property_tax"].tolist() == [
        0.0
    ]
    assert result.frame.table("person")["real_estate_taxes"].tolist() == [0.0, 0.0]


def test_acs_property_tax_mapping_rejects_nonzero_group_quarters_value() -> None:
    frame = _acs_frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    household = tables["household"]
    household["TEN"] = np.nan
    household["TYPEHUGQ"] = 2
    household["TAXAMT"] = 1.0
    tampered = Frame(
        tables,
        frame.schema,
        {"household": frame.weights_for("household")},
        frame.strata,
    )

    with pytest.raises(ValueError, match="renter/group-quarters TAXAMT"):
        map_acs_native_inputs(tampered)


def test_acs_property_tax_structural_zero_needs_no_adjustment_factor() -> None:
    frame = _acs_frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    household = tables["household"]
    household[["RNTP", "GRNTP"]] = np.nan
    household["TAXAMT"] = 0.0
    household["ADJHSG"] = np.nan
    structural_zero = Frame(
        tables,
        frame.schema,
        {"household": frame.weights_for("household")},
        frame.strata,
    )

    result = map_acs_native_inputs(structural_zero)

    assert result.frame.table("household")["acs_annual_property_tax"].tolist() == [
        0.0
    ]
    assert result.frame.table("person")["real_estate_taxes"].tolist() == [0.0, 0.0]


def test_acs_property_tax_mapping_rejects_nonnumeric_structural_value() -> None:
    frame = _acs_frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    tables["household"]["TAXAMT"] = "not-a-number"
    invalid = Frame(
        tables,
        frame.schema,
        {"household": frame.weights_for("household")},
        frame.strata,
    )

    with pytest.raises(ValueError, match="TAXAMT must be numeric"):
        map_acs_native_inputs(invalid)


@pytest.mark.parametrize(
    ("type_hugq", "tenure"),
    [(np.nan, 3), (4, 3), (1, np.nan), (1, 9)],
)
def test_acs_property_tax_mapping_rejects_invalid_source_domain(
    type_hugq: float,
    tenure: float,
) -> None:
    frame = _acs_frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    tables["household"]["TYPEHUGQ"] = type_hugq
    tables["household"]["TEN"] = tenure
    invalid = Frame(
        tables,
        frame.schema,
        {"household": frame.weights_for("household")},
        frame.strata,
    )

    with pytest.raises(ValueError, match="real-estate-tax source-domain|ACS TEN"):
        map_acs_native_inputs(invalid)


@pytest.mark.parametrize(
    ("factor", "invalid"),
    [("ADJINC", np.nan), ("ADJINC", np.inf), ("ADJHSG", np.nan)],
)
def test_acs_observed_dollars_require_finite_positive_adjustment(
    factor: str,
    invalid: float,
) -> None:
    frame = _acs_frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    entity = "person" if factor == "ADJINC" else "household"
    tables[entity][factor] = tables[entity][factor].astype(float)
    tables[entity].loc[0, factor] = invalid
    invalid_frame = Frame(
        tables,
        frame.schema,
        {"household": frame.weights_for("household")},
        frame.strata,
    )

    with pytest.raises(ValueError, match=f"{factor} must be finite and positive"):
        map_acs_native_inputs(invalid_frame)


def test_acs_native_mapping_refuses_existing_output_collision() -> None:
    frame = _acs_frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    tables["person"]["age"] = [999.0, 999.0]
    collision = Frame(
        tables,
        frame.schema,
        {"household": frame.weights_for("household")},
        frame.strata,
    )

    with pytest.raises(ValueError, match="refuses to overwrite.*age"):
        map_acs_native_inputs(collision)


def test_acs_unmapped_missing_source_columns_stay_absent() -> None:
    frame = _acs_frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    tables["person"] = tables["person"].drop(columns=["RETP", "INTP"])
    sparse = Frame(
        tables,
        frame.schema,
        {"household": frame.weights_for("household")},
        frame.strata,
    )

    result = map_acs_native_inputs(sparse)

    assert "acs_retirement_income" not in result.frame.table("person")
    assert "acs_interest_dividend_rental_income" not in result.frame.table("person")
    assert "acs_retirement_income" not in result.native_inputs
    assert "acs_interest_dividend_rental_income" not in result.native_inputs
