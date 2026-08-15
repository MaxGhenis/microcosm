"""CPS ASEC variables carried into PolicyEngine leaves and model predictors.

This stage translates raw CPS ASEC value columns already present on the
source spine into PolicyEngine input leaves and canonical model predictors
needed by downstream donor stages. It intentionally does not emit PolicyEngine
formula-owned totals such as ``dividend_income`` or ``social_security``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

import numpy as np
import pandas as pd

from microcosm.build.us_runtime.alimony import (
    US_ASEC_OTHER_INCOME_OUTPUT_COLUMNS,
    derive_us_alimony_from_asec,
)
from microcosm.build.us_runtime.public_assistance_type_source import (
    PAW_TYPE_TANF_CODES,
    fill_asec_public_assistance_type_source,
)
from microcosm.frame import US_SCHEMA, Frame

__all__ = [
    "CPS_RELATIONSHIP_PREDICTOR_CODES",
    "CPS_CARRIED_FORMULA_OWNED_COLUMNS",
    "CPS_CARRIED_PERSON_INPUTS",
    "CPS_CARRIED_PERSON_PREDICTORS",
    "CPS_CARRIED_SPM_UNIT_INPUTS",
    "CPS_REPORTED_SNAP_RAW_COLUMN",
    "CPS_REPORTED_TANF_AMOUNT_RAW_COLUMN",
    "CPS_REPORTED_TANF_TYPE_RAW_COLUMN",
    "CPS_REPORTED_WIC_RAW_COLUMN",
    "WIC_CARRIER_ADJUDICATION_URL",
    "cps_carried_predictor_mapping_identity",
    "derive_us_cps_carried_inputs",
    "reported_snap_receipt_by_spm_unit",
    "reported_tanf_enrollment_by_spm_unit",
    "reported_wic_receipt_carrier",
    "validate_cps_carried_person_predictors",
]

TAXABLE_INTEREST_FRACTION = 0.680
QUALIFIED_DIVIDEND_FRACTION = 0.448
TAXABLE_PENSION_FRACTION = 0.590
LONG_TERM_CAPITAL_GAIN_FRACTION = 0.880
CPS_REPORTED_SNAP_RAW_COLUMN = "SPM_SNAPSUB"
CPS_REPORTED_TANF_AMOUNT_RAW_COLUMN = "PAW_VAL"
CPS_REPORTED_TANF_TYPE_RAW_COLUMN = "PAW_TYP"
CPS_REPORTED_WIC_RAW_COLUMN = "WICYN"
WIC_CARRIER_ADJUDICATION_URL = (
    "https://github.com/PolicyEngine/microcosm/issues/591#issuecomment-5160668979"
)

CPS_CARRIED_FORMULA_OWNED_COLUMNS = frozenset(
    {
        "capital_gains",
        "dividend_income",
        "employment_income",
        "interest_income",
        "long_term_capital_gains",
        "ordinary_dividend_income",
        "self_employment_income",
        "social_security",
        "taxable_pension_income",
    }
)

CPS_CARRIED_PERSON_INPUTS = frozenset(
    {
        "age",
        "employment_income_before_lsr",
        "self_employment_income_before_lsr",
        "taxable_interest_income",
        "qualified_dividend_income",
        "non_qualified_dividend_income",
        "short_term_capital_gains",
        "long_term_capital_gains_before_response",
        "social_security_retirement",
        "social_security_disability",
        "social_security_survivors",
        "social_security_dependents",
        "taxable_private_pension_income",
        "tax_exempt_private_pension_income",
        "taxable_ira_distributions",
        "health_insurance_premiums_without_medicare_part_b",
        "other_medical_expenses",
        "over_the_counter_health_expenses",
        "receives_wic",
        "rental_income",
        "farm_operations_income",
        "has_champva_health_coverage_at_interview",
        "has_esi",
        "has_indian_health_service_coverage_at_interview",
        "has_marketplace_health_coverage_at_interview",
        "has_medicaid_health_coverage_at_interview",
        "has_non_marketplace_direct_purchase_health_coverage_at_interview",
        "has_other_means_tested_health_coverage_at_interview",
        "has_tricare_health_coverage_at_interview",
        "has_va_health_coverage_at_interview",
        "is_female",
        "unemployment_compensation",
        *US_ASEC_OTHER_INCOME_OUTPUT_COLUMNS,
    }
)

# Canonical donor-side predictor columns are deliberately separate from the
# PolicyEngine input-leaf surface above. They exist only to give ACS transfer
# families survey-comparable measured predictors without widening the raw ASEC
# checkpoint schema.
CPS_CARRIED_PERSON_PREDICTORS = frozenset(
    {
        "difficulty_doing_errands",
        "difficulty_dressing_or_bathing",
        "difficulty_hearing",
        "difficulty_remembering_or_making_decisions",
        "difficulty_seeing",
        "difficulty_walking_or_climbing_stairs",
        "has_medicare_coverage",
        "household_person_count",
        "is_foreign_born",
        "is_self_employed_worker",
        "is_veteran_or_active_military",
        "marital_status_code",
        "relationship_code",
        "usual_hours_worked",
        # ``weeks_worked`` is a formula-owned transient on the pool path.
        # Keep the model-only carry distinct so it survives to early gap-fill.
        "weeks_worked_predictor",
    }
)

CPS_RELATIONSHIP_PREDICTOR_CODES = frozenset(
    {1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0}
)
_CPS_BINARY_PERSON_PREDICTORS = frozenset(
    {
        "difficulty_doing_errands",
        "difficulty_dressing_or_bathing",
        "difficulty_hearing",
        "difficulty_remembering_or_making_decisions",
        "difficulty_seeing",
        "difficulty_walking_or_climbing_stairs",
        "has_medicare_coverage",
        "is_foreign_born",
        "is_self_employed_worker",
        "is_veteran_or_active_military",
    }
)

CPS_CARRIED_SPM_UNIT_INPUTS = frozenset(
    {
        "is_tanf_enrolled",
        "receives_snap",
        "spm_unit_pre_subsidy_childcare_expenses",
    }
)

_CPS_MARITAL_STATUS_SOURCE = "A_MARITL"
_CPS_MARITAL_STATUS_RECODE: Mapping[float, float] = {
    1.0: 1.0,
    2.0: 1.0,
    3.0: 1.0,
    4.0: 2.0,
    5.0: 3.0,
    6.0: 4.0,
    7.0: 5.0,
}
_CPS_DIRECT_PERSON_PREDICTOR_SOURCES: Mapping[str, str] = {
    "relationship_code": "A_EXPRRP",
}
_CPS_USUAL_HOURS_SOURCE = "HRSWK"
_CPS_WEEKS_WORKED_SOURCE = "WKSWORK"
_CPS_VETERAN_PERSON_PREDICTOR_SOURCES: Mapping[
    str,
    tuple[frozenset[float], frozenset[float], frozenset[float]],
] = {
    "PEAFEVER": (
        frozenset({1.0}),
        frozenset({2.0}),
        frozenset({-1.0}),
    ),
    "A_MJOCC": (
        frozenset({11.0}),
        frozenset(range(11)),
        frozenset(),
    ),
}
_CPS_CODED_PERSON_PREDICTOR_SOURCES: Mapping[
    str,
    tuple[str, frozenset[float], frozenset[float], frozenset[float]],
] = {
    "difficulty_dressing_or_bathing": (
        "PEDISDRS",
        frozenset({1.0}),
        frozenset({2.0}),
        frozenset({-1.0}),
    ),
    "difficulty_hearing": (
        "PEDISEAR",
        frozenset({1.0}),
        frozenset({2.0}),
        frozenset({-1.0}),
    ),
    "difficulty_seeing": (
        "PEDISEYE",
        frozenset({1.0}),
        frozenset({2.0}),
        frozenset({-1.0}),
    ),
    "difficulty_doing_errands": (
        "PEDISOUT",
        frozenset({1.0}),
        frozenset({2.0}),
        frozenset({-1.0}),
    ),
    "difficulty_walking_or_climbing_stairs": (
        "PEDISPHY",
        frozenset({1.0}),
        frozenset({2.0}),
        frozenset({-1.0}),
    ),
    "difficulty_remembering_or_making_decisions": (
        "PEDISREM",
        frozenset({1.0}),
        frozenset({2.0}),
        frozenset({-1.0}),
    ),
    "is_self_employed_worker": (
        "PEIO1COW",
        frozenset({6.0, 7.0}),
        frozenset({1.0, 2.0, 3.0, 4.0, 5.0, 8.0}),
        frozenset({0.0}),
    ),
    "has_medicare_coverage": (
        "MCARE",
        frozenset({1.0}),
        frozenset({0.0, 2.0}),
        frozenset(),
    ),
    "is_foreign_born": (
        "PRCITSHP",
        frozenset({4.0, 5.0}),
        frozenset({1.0, 2.0, 3.0}),
        frozenset(),
    ),
}


def cps_carried_predictor_mapping_identity() -> dict[str, object]:
    """Bind every physical ASEC source, codec, and canonical-domain guard."""

    predictors: dict[str, object] = {
        "marital_status_code": {
            "source": _CPS_MARITAL_STATUS_SOURCE,
            "codec": "reviewed_code_recode_preserve_blank",
            "recode": {
                str(int(source)): target
                for source, target in sorted(_CPS_MARITAL_STATUS_RECODE.items())
            },
        },
        **{
            output: {
                "source": source,
                "codec": "reviewed_code_identity_preserve_blank",
                "valid_codes": sorted(CPS_RELATIONSHIP_PREDICTOR_CODES),
            }
            for output, source in sorted(_CPS_DIRECT_PERSON_PREDICTOR_SOURCES.items())
        },
        "usual_hours_worked": {
            "source": _CPS_USUAL_HOURS_SOURCE,
            "codec": "finite_numeric_clamp_min_0_preserve_blank",
        },
        "weeks_worked_predictor": {
            "source": _CPS_WEEKS_WORKED_SOURCE,
            "codec": "finite_numeric_clip_0_52_preserve_blank",
        },
        "household_person_count": {
            "source": "person_household_id",
            "codec": "household_group_size_sort_false",
        },
        "is_veteran_or_active_military": {
            "sources": {
                source: {
                    "true_codes": sorted(true_codes),
                    "false_codes": sorted(false_codes),
                    "missing_codes": sorted(missing_codes),
                }
                for source, (
                    true_codes,
                    false_codes,
                    missing_codes,
                ) in sorted(_CPS_VETERAN_PERSON_PREDICTOR_SOURCES.items())
            },
            "codec": "three_valued_any_true_else_all_known_false_else_missing",
        },
        **{
            output: {
                "source": source,
                "codec": "reviewed_binary_codes_preserve_blank",
                "true_codes": sorted(true_codes),
                "false_codes": sorted(false_codes),
                "missing_codes": sorted(missing_codes),
            }
            for output, (
                source,
                true_codes,
                false_codes,
                missing_codes,
            ) in sorted(_CPS_CODED_PERSON_PREDICTOR_SOURCES.items())
        },
    }
    if set(predictors) != set(CPS_CARRIED_PERSON_PREDICTORS):
        raise RuntimeError(
            "CPS carried predictor mapping identity drifted from its output "
            f"surface: missing={sorted(CPS_CARRIED_PERSON_PREDICTORS - set(predictors))}, "
            f"extra={sorted(set(predictors) - CPS_CARRIED_PERSON_PREDICTORS)}."
        )
    canonical_validation: dict[str, object] = {
        **{
            column: {
                "domain": "binary_0_1",
                "missing": "allowed",
            }
            for column in sorted(_CPS_BINARY_PERSON_PREDICTORS)
        },
        "marital_status_code": {
            "domain": "reviewed_codes",
            "valid_codes": [1.0, 2.0, 3.0, 4.0, 5.0],
            "missing": "allowed",
        },
        "relationship_code": {
            "domain": "reviewed_codes",
            "valid_codes": sorted(CPS_RELATIONSHIP_PREDICTOR_CODES),
            "missing": "allowed",
        },
        "household_person_count": {
            "domain": "positive_integer",
            "missing": "allowed",
        },
        "usual_hours_worked": {
            "domain": "finite_nonnegative",
            "missing": "allowed",
        },
        "weeks_worked_predictor": {
            "domain": "integer_0_52",
            "missing": "allowed",
        },
    }
    if set(canonical_validation) != set(CPS_CARRIED_PERSON_PREDICTORS):
        raise RuntimeError(
            "CPS carried canonical validation identity drifted from its output surface."
        )
    payload: dict[str, object] = {
        "version": 2,
        "predictors": predictors,
        "preexisting_value_policy": "preserve_after_canonical_domain_validation",
        "canonical_validation": canonical_validation,
    }
    payload["sha256"] = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return payload


def derive_us_cps_carried_inputs(
    frame: Frame,
    *,
    public_assistance_type_source: pd.DataFrame | None = None,
) -> Frame:
    """Carry raw CPS ASEC values onto PE input leaves.

    Existing leaf and canonical predictor columns are preserved, making the
    transform idempotent. The transform refuses to run on a non-US frame and
    never creates formula-owned aggregate variables.

    ``PAW_VAL``, ``SPM_SNAPSUB``, and ``WICYN`` are annual reported facts,
    while the engine's ``is_tanf_enrolled``, ``receives_snap``, and
    ``receives_wic`` leaves are monthly booleans. An annual receipt report is
    therefore broadcast to all 12 modeled months. The annual source cannot
    reveal entry or exit timing, and ``PAW_VAL > 0`` misses enrolled TANF
    units receiving zero dollars, including sanctioned cases.

    ``is_tanf_enrolled`` is additionally gated on ``PAW_TYP`` because
    ``PAW_VAL`` alone conflates TANF with other cash welfare; see
    :func:`reported_tanf_enrollment_by_spm_unit`. When the frame does not
    already carry ``PAW_TYP`` (the frozen census_cps inputs never did),
    callers with positive ``PAW_VAL`` rows must pass
    ``public_assistance_type_source`` — the pinned sidecar loaded by
    :func:`~microcosm.build.us_runtime.public_assistance_type_source.load_asec_public_assistance_type_sources`
    — which is joined transiently and never lands on the output frame.
    """

    if frame.schema != US_SCHEMA:
        raise ValueError("CPS-carried derivations require the US schema.")
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    person = tables["person"]

    _fill_person_predictors(person)
    _fill_missing(person, "age", _source(person, "A_AGE"))
    _fill_bool_missing(person, "is_female", _integer_source(person, "A_SEX") == 2)
    _fill_bool_missing(person, "receives_wic", reported_wic_receipt_carrier(person))
    _fill_missing(person, "employment_income_before_lsr", _source(person, "WSAL_VAL"))
    _fill_missing(
        person,
        "self_employment_income_before_lsr",
        _source(person, "SEMP_VAL"),
    )

    interest = _source(person, "INT_VAL")
    _fill_missing(
        person,
        "taxable_interest_income",
        interest * TAXABLE_INTEREST_FRACTION,
    )

    dividends = _source(person, "DIV_VAL")
    _fill_missing(
        person,
        "qualified_dividend_income",
        dividends * QUALIFIED_DIVIDEND_FRACTION,
    )
    _fill_missing(
        person,
        "non_qualified_dividend_income",
        dividends * (1 - QUALIFIED_DIVIDEND_FRACTION),
    )

    capital_gains = _source(person, "CAP_VAL")
    _fill_missing(
        person,
        "long_term_capital_gains_before_response",
        capital_gains * LONG_TERM_CAPITAL_GAIN_FRACTION,
    )
    _fill_missing(
        person,
        "short_term_capital_gains",
        capital_gains * (1 - LONG_TERM_CAPITAL_GAIN_FRACTION),
    )

    _fill_social_security_leaves(person)
    pensions = _source(person, "PNSN_VAL") + _source(person, "ANN_VAL")
    _fill_missing(
        person,
        "taxable_private_pension_income",
        pensions * TAXABLE_PENSION_FRACTION,
    )
    _fill_missing(
        person,
        "tax_exempt_private_pension_income",
        pensions * (1 - TAXABLE_PENSION_FRACTION),
    )
    _fill_missing(person, "taxable_ira_distributions", _ira_distributions(person))

    person = derive_us_alimony_from_asec(person)
    tables["person"] = person

    direct_sources: Mapping[str, str] = {
        "rental_income": "RNT_VAL",
        "farm_operations_income": "FRSE_VAL",
        "unemployment_compensation": "UC_VAL",
        "health_insurance_premiums_without_medicare_part_b": "PHIP_VAL",
        "other_medical_expenses": "PMED_VAL",
        "over_the_counter_health_expenses": "POTC_VAL",
    }
    # PEMCPREM remains on the source frame as evidence only. The corresponding
    # reported Part B leaf has no engine-formula consumers, so the pool must not
    # promote or transfer it onto ACS rows.
    for output, source in direct_sources.items():
        _fill_missing(person, output, _source(person, source))

    _fill_health_coverage_inputs(person)
    _fill_spm_unit_reported_enrollment_inputs(
        person,
        tables["spm_unit"],
        public_assistance_type_source=public_assistance_type_source,
    )
    _fill_spm_unit_childcare_inputs(person, tables["spm_unit"])

    formula_owned = sorted(CPS_CARRIED_FORMULA_OWNED_COLUMNS.intersection(person))
    if formula_owned:
        raise ValueError(
            "CPS-carried derivations must not carry formula-owned aggregate "
            f"columns: {formula_owned}."
        )

    return Frame(
        tables,
        frame.schema,
        {entity: frame.weights_for(entity) for entity in frame.weighted_entities},
        frame.strata,
        mass_log=frame.mass_log,
        metadata=frame.metadata,
    )


def reported_tanf_enrollment_by_spm_unit(
    person: pd.DataFrame,
    public_assistance_type_source: pd.DataFrame | None = None,
) -> pd.Series:
    """Return reported TANF enrollment per SPM unit, gated on ``PAW_TYP``.

    A unit is TANF-enrolled when any member reports a positive annual
    public-assistance amount (``PAW_VAL > 0``) whose reported type is
    TANF/AFDC (``PAW_TYP`` 1) or both TANF/AFDC and other assistance
    (``PAW_TYP`` 3). ``PAW_TYP`` 2 (other cash welfare, e.g. general
    assistance) and unreported-type PAW recipients are NOT marked
    TANF-enrolled: the engine's ``is_tanf_enrolled`` variable is
    TANF-specific, and conflating other cash welfare with TANF would poison
    its 13 cycle-safe TANF helper consumers (microcosm#591). The conflation
    is material — in the 2023 ASEC (income year 2022), 271 of 682
    PAW-positive SPM units (39.7% unweighted, 42.6% SPM-weighted) have no
    member reporting a TANF type.

    ``PAW_TYP`` is read from ``person`` when present (the pool's raw-stage
    checkpoint carries it). Otherwise, when any ``PAW_VAL`` is positive, the
    pinned public-assistance-type sidecar is required and joined transiently
    without mutating ``person``; refusing to fall back to ``PAW_VAL > 0``
    keeps the gate impossible to silently drop.
    """

    if "person_spm_unit_id" not in person.columns:
        raise ValueError(
            "Reported TANF enrollment requires person column(s): "
            "['person_spm_unit_id']."
        )
    amounts = _source(person, CPS_REPORTED_TANF_AMOUNT_RAW_COLUMN)
    if CPS_REPORTED_TANF_TYPE_RAW_COLUMN in person.columns:
        types = _integer_source(person, CPS_REPORTED_TANF_TYPE_RAW_COLUMN)
    elif not (amounts > 0.0).any():
        types = np.zeros(len(person), dtype=np.int64)
    elif public_assistance_type_source is not None:
        joined = fill_asec_public_assistance_type_source(
            person,
            public_assistance_type_source,
        )
        types = _integer_source(joined, CPS_REPORTED_TANF_TYPE_RAW_COLUMN)
    else:
        raise ValueError(
            "Reported TANF enrollment requires PAW_TYP for the positive "
            f"{CPS_REPORTED_TANF_AMOUNT_RAW_COLUMN} rows: carry the column on "
            "the frame or pass public_assistance_type_source; PAW_VAL alone "
            "conflates TANF with other cash welfare (microcosm#591)."
        )
    member_enrolled = (amounts > 0.0) & np.isin(types, sorted(PAW_TYPE_TANF_CODES))
    return (
        pd.DataFrame(
            {
                "person_spm_unit_id": person["person_spm_unit_id"],
                "_reported_tanf_enrollment": member_enrolled,
            }
        )
        .groupby("person_spm_unit_id", sort=True)["_reported_tanf_enrollment"]
        .any()
        .rename("reported_tanf_enrollment")
    )


def reported_snap_receipt_by_spm_unit(person: pd.DataFrame) -> pd.Series:
    """Return the shared max-positive annual SNAP receipt interpretation.

    ``SPM_SNAPSUB`` is an annual SPM-unit amount replicated on person rows.
    A unit reports SNAP receipt when the maximum member value is positive;
    non-numeric and missing values are treated as zero.
    """

    required = [CPS_REPORTED_SNAP_RAW_COLUMN, "person_spm_unit_id"]
    missing = [column for column in required if column not in person.columns]
    if missing:
        raise ValueError(f"Reported SNAP receipt requires person column(s): {missing}.")
    subsidy = pd.to_numeric(
        person[CPS_REPORTED_SNAP_RAW_COLUMN], errors="coerce"
    ).fillna(0.0)
    return (
        person.assign(_reported_snap_subsidy=subsidy)
        .groupby("person_spm_unit_id", sort=True)["_reported_snap_subsidy"]
        .max()
        .gt(0.0)
        .rename("reported_snap_receipt")
    )


def reported_wic_receipt_carrier(person: pd.DataFrame) -> np.ndarray:
    """Carry the SPM unit's reported WIC receipt fact on its reporting adult.

    Census asks ``WICYN`` only of adult women, and a woman may report receipt
    for herself or for a child beneficiary. ``receives_wic`` therefore remains
    stored on that reporting adult solely as the carrier for her SPM unit's
    receipt fact; it does not identify the person who received WIC. Unit-level
    aggregation is the ONLY supported consumption grain. Any person-grain use
    requires re-adjudication under microcosm#591:
    https://github.com/PolicyEngine/microcosm/issues/591#issuecomment-5160668979
    """

    return _integer_source(person, CPS_REPORTED_WIC_RAW_COLUMN) == 1


def _fill_missing(table: pd.DataFrame, column: str, values: np.ndarray) -> None:
    if column not in table.columns:
        table[column] = values.astype("float64")


def _fill_bool_missing(table: pd.DataFrame, column: str, values: np.ndarray) -> None:
    if column not in table.columns:
        table[column] = values.astype(bool)


def _fill_person_predictors(person: pd.DataFrame) -> None:
    """Carry measured ASEC analogues without converting blanks to zero."""

    validate_cps_carried_person_predictors(person)

    marital_status = _nullable_source(person, _CPS_MARITAL_STATUS_SOURCE)
    if marital_status is not None and "marital_status_code" not in person:
        observed = np.isfinite(marital_status)
        invalid = observed & ~np.isin(
            marital_status,
            list(_CPS_MARITAL_STATUS_RECODE),
        )
        if invalid.any():
            bad = sorted(set(marital_status[invalid].tolist()))
            raise ValueError(f"ASEC A_MARITL contains unsupported code(s): {bad}.")
        person["marital_status_code"] = np.asarray(
            [_CPS_MARITAL_STATUS_RECODE.get(value, np.nan) for value in marital_status],
            dtype=np.float64,
        )

    for output, source in _CPS_DIRECT_PERSON_PREDICTOR_SOURCES.items():
        values = _nullable_source(person, source)
        if values is None or output in person:
            continue
        observed = np.isfinite(values)
        invalid = observed & ~np.isin(
            values,
            list(CPS_RELATIONSHIP_PREDICTOR_CODES),
        )
        if invalid.any():
            bad = sorted(set(values[invalid].tolist()))
            raise ValueError(f"ASEC {source} contains unsupported code(s): {bad}.")
        person[output] = values

    usual_hours = _nullable_source(person, _CPS_USUAL_HOURS_SOURCE)
    if usual_hours is not None and "usual_hours_worked" not in person:
        person["usual_hours_worked"] = np.maximum(usual_hours, 0.0)
    weeks_worked = _nullable_source(person, _CPS_WEEKS_WORKED_SOURCE)
    if weeks_worked is not None and "weeks_worked_predictor" not in person:
        person["weeks_worked_predictor"] = np.minimum(
            np.maximum(weeks_worked, 0.0),
            52.0,
        )

    if "household_person_count" not in person and "person_household_id" in person:
        person["household_person_count"] = (
            person.groupby("person_household_id", sort=False)["person_household_id"]
            .transform("size")
            .astype("float64")
        )

    veteran_source, military_source = _CPS_VETERAN_PERSON_PREDICTOR_SOURCES
    veteran = _nullable_source(person, veteran_source)
    military = _nullable_source(person, military_source)
    if (
        veteran is not None
        and military is not None
        and "is_veteran_or_active_military" not in person
    ):
        veteran_codes = _CPS_VETERAN_PERSON_PREDICTOR_SOURCES[veteran_source]
        military_codes = _CPS_VETERAN_PERSON_PREDICTOR_SOURCES[military_source]
        veteran_indicator = _coded_indicator(
            veteran,
            source=veteran_source,
            true_codes=veteran_codes[0],
            false_codes=veteran_codes[1],
            missing_codes=veteran_codes[2],
        )
        military_indicator = _coded_indicator(
            military,
            source=military_source,
            true_codes=military_codes[0],
            false_codes=military_codes[1],
            missing_codes=military_codes[2],
        )
        positive = (veteran_indicator == 1.0) | (military_indicator == 1.0)
        complete = np.isfinite(veteran_indicator) & np.isfinite(military_indicator)
        person["is_veteran_or_active_military"] = np.where(
            positive,
            1.0,
            np.where(complete, 0.0, np.nan),
        )

    for output, (
        source,
        true_codes,
        false_codes,
        missing_codes,
    ) in _CPS_CODED_PERSON_PREDICTOR_SOURCES.items():
        values = _nullable_source(person, source)
        if values is None or output in person:
            continue
        person[output] = _coded_indicator(
            values,
            source=source,
            true_codes=true_codes,
            false_codes=false_codes,
            missing_codes=missing_codes,
        )

    validate_cps_carried_person_predictors(person)


def validate_cps_carried_person_predictors(
    person: pd.DataFrame,
    *,
    columns: tuple[str, ...] | None = None,
    context: str = "CPS carried",
) -> None:
    """Refuse out-of-domain canonical predictor values while allowing blanks."""

    selected = CPS_CARRIED_PERSON_PREDICTORS if columns is None else frozenset(columns)
    unknown = sorted(selected - CPS_CARRIED_PERSON_PREDICTORS)
    if unknown:
        raise ValueError(f"{context} requested unknown predictor column(s): {unknown}.")

    for column in sorted(selected.intersection(person.columns)):
        values = _nullable_source(person, column)
        if values is None:  # pragma: no cover - guarded by the intersection
            continue
        observed = np.isfinite(values)
        if column in _CPS_BINARY_PERSON_PREDICTORS:
            valid = np.isin(values, [0.0, 1.0])
        elif column == "marital_status_code":
            valid = np.isin(values, [1.0, 2.0, 3.0, 4.0, 5.0])
        elif column == "relationship_code":
            valid = np.isin(values, list(CPS_RELATIONSHIP_PREDICTOR_CODES))
        elif column == "household_person_count":
            valid = (values > 0.0) & np.equal(values, np.floor(values))
        elif column == "usual_hours_worked":
            valid = values >= 0.0
        elif column == "weeks_worked_predictor":
            valid = (
                (values >= 0.0) & (values <= 52.0) & np.equal(values, np.floor(values))
            )
        else:  # pragma: no cover - closed registry above
            raise AssertionError(f"Unhandled CPS carried predictor {column!r}.")
        invalid = observed & ~valid
        if invalid.any():
            bad = sorted(set(values[invalid].tolist()))
            raise ValueError(
                f"{context} canonical predictor {column!r} contains unsupported "
                f"value(s): {bad}."
            )


def _coded_indicator(
    values: np.ndarray,
    *,
    source: str,
    true_codes: frozenset[float],
    false_codes: frozenset[float],
    missing_codes: frozenset[float] = frozenset(),
) -> np.ndarray:
    """Decode one reviewed CPS code domain while retaining NIU sentinels."""

    observed = np.isfinite(values)
    valid_codes = [*true_codes, *false_codes, *missing_codes]
    invalid = observed & ~np.isin(values, valid_codes)
    if invalid.any():
        bad = sorted(set(values[invalid].tolist()))
        raise ValueError(f"ASEC {source} contains unsupported code(s): {bad}.")
    result = np.full(len(values), np.nan, dtype=np.float64)
    result[np.isin(values, list(false_codes))] = 0.0
    result[np.isin(values, list(true_codes))] = 1.0
    return result


def _nullable_source(person: pd.DataFrame, column: str) -> np.ndarray | None:
    """Read one optional predictor source while preserving native blanks."""

    if column not in person.columns:
        return None
    source = person[column]
    numeric = pd.to_numeric(source, errors="coerce")
    blank = source.isna()
    if pd.api.types.is_object_dtype(source.dtype) or isinstance(
        source.dtype, pd.StringDtype
    ):
        blank |= source.astype("string").str.strip().eq("").fillna(False)
    invalid = numeric.isna() & ~blank
    if invalid.any():
        bad = source.loc[invalid].astype(str).head().tolist()
        raise ValueError(
            f"ASEC predictor source {column!r} contains non-numeric value(s): {bad}."
        )
    values = numeric.to_numpy(dtype=np.float64)
    if np.isinf(values).any():
        raise ValueError(
            f"ASEC predictor source {column!r} contains infinite value(s)."
        )
    return values


def _source(person: pd.DataFrame, column: str) -> np.ndarray:
    if column not in person.columns:
        return np.zeros(len(person), dtype=np.float64)
    return (
        pd.to_numeric(person[column], errors="coerce")
        .fillna(0.0)
        .to_numpy(dtype=np.float64)
    )


def _fill_social_security_leaves(person: pd.DataFrame) -> None:
    social_security = _source(person, "SS_VAL")
    reason_1 = _integer_source(person, "RESNSS1")
    reason_2 = _integer_source(person, "RESNSS2")
    age = _integer_source(person, "A_AGE")

    is_retirement = (reason_1 == 1) | (reason_2 == 1)
    is_disability = (reason_1 == 2) | (reason_2 == 2)
    is_survivor = np.isin(reason_1, [3, 5]) | np.isin(reason_2, [3, 5])
    is_dependent = np.isin(reason_1, [4, 6, 7]) | np.isin(reason_2, [4, 6, 7])
    unclassified = (
        (social_security > 0)
        & ~is_retirement
        & ~is_disability
        & ~is_survivor
        & ~is_dependent
    )

    _fill_missing(
        person,
        "social_security_retirement",
        np.where(is_retirement | (unclassified & (age >= 62)), social_security, 0.0),
    )
    _fill_missing(
        person,
        "social_security_disability",
        np.where(
            (is_disability & ~is_retirement) | (unclassified & (age < 62)),
            social_security,
            0.0,
        ),
    )
    _fill_missing(
        person,
        "social_security_survivors",
        np.where(is_survivor & ~is_retirement & ~is_disability, social_security, 0.0),
    )
    _fill_missing(
        person,
        "social_security_dependents",
        np.where(
            is_dependent & ~is_retirement & ~is_disability & ~is_survivor,
            social_security,
            0.0,
        ),
    )


def _fill_health_coverage_inputs(person: pd.DataFrame) -> None:
    marketplace = _yes_code(person, "NOW_MRK")
    _fill_bool_missing(
        person,
        "has_marketplace_health_coverage_at_interview",
        marketplace,
    )
    source_columns: Mapping[str, str] = {
        "has_non_marketplace_direct_purchase_health_coverage_at_interview": "NOW_NONM",
        "has_medicaid_health_coverage_at_interview": "NOW_MCAID",
        "has_esi": "NOW_GRP",
        "has_champva_health_coverage_at_interview": "NOW_CHAMPVA",
        "has_tricare_health_coverage_at_interview": "NOW_MIL",
        "has_va_health_coverage_at_interview": "NOW_VACARE",
        "has_other_means_tested_health_coverage_at_interview": "NOW_OTHMT",
        "has_indian_health_service_coverage_at_interview": "NOW_IHSFLG",
    }
    for output, source in source_columns.items():
        _fill_bool_missing(person, output, _yes_code(person, source))


def _fill_spm_unit_childcare_inputs(
    person: pd.DataFrame,
    spm_unit: pd.DataFrame,
) -> None:
    """Carry ASEC SPM childcare expenses onto the SPM-unit input leaf.

    ``SPM_CHILDCAREXPNS`` is an SPM-unit value replicated on every member's
    person record, so the unit's value is its members' maximum. The engine
    derives person, tax-unit, and CDCC childcare expenses from this leaf;
    a base without it zeroes every CDCC baseline (microcosm issue #278).
    """

    column = "spm_unit_pre_subsidy_childcare_expenses"
    if column in spm_unit.columns:
        return
    member_values = pd.DataFrame(
        {
            "person_spm_unit_id": person["person_spm_unit_id"],
            column: _source(person, "SPM_CHILDCAREXPNS"),
        }
    )
    unit_values = member_values.groupby("person_spm_unit_id", sort=False)[column].max()
    spm_unit[column] = (
        unit_values.reindex(spm_unit["spm_unit_id"])
        .fillna(0.0)
        .to_numpy(dtype=np.float64)
    )


def _fill_spm_unit_reported_enrollment_inputs(
    person: pd.DataFrame,
    spm_unit: pd.DataFrame,
    *,
    public_assistance_type_source: pd.DataFrame | None = None,
) -> None:
    """Carry annual reported TANF and SNAP receipt onto monthly leaves."""

    if "is_tanf_enrolled" not in spm_unit.columns:
        tanf = reported_tanf_enrollment_by_spm_unit(
            person,
            public_assistance_type_source,
        )
        spm_unit["is_tanf_enrolled"] = (
            tanf.reindex(spm_unit["spm_unit_id"]).fillna(False).to_numpy(dtype=bool)
        )

    if "receives_snap" not in spm_unit.columns:
        snap_person = person
        if CPS_REPORTED_SNAP_RAW_COLUMN not in snap_person.columns:
            snap_person = person.assign(**{CPS_REPORTED_SNAP_RAW_COLUMN: 0.0})
        reported = reported_snap_receipt_by_spm_unit(snap_person)
        spm_unit["receives_snap"] = (
            reported.reindex(spm_unit["spm_unit_id"]).fillna(False).to_numpy(dtype=bool)
        )


def _ira_distributions(person: pd.DataFrame) -> np.ndarray:
    values = np.zeros(len(person), dtype=np.float64)
    for suffix in ("1", "2", "1_YNG", "2_YNG"):
        code = _integer_source(person, f"DST_SC{suffix}")
        amount = _source(person, f"DST_VAL{suffix}")
        values += np.where(code == 4, amount, 0.0)
    return values


def _integer_source(person: pd.DataFrame, column: str) -> np.ndarray:
    return _source(person, column).astype("int64")


def _yes_code(person: pd.DataFrame, column: str) -> np.ndarray:
    return _integer_source(person, column) == 1
