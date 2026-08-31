"""Authenticated ingest of the public Armenia ILCS 2024 household/member spine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from microcosm.build.am_runtime.national_frame import (
    am_national_frame,
    validate_am_national_frame,
)
from microcosm.build.source_manifest import SourceStageSpec
from microcosm.build.trace import sha256_file
from microcosm.frame import Frame, WeightKind

__all__ = [
    "AM_ILCS_HOUSEHOLD_ROWS",
    "AM_ILCS_MEMBER_ROWS",
    "AM_ILCS_OUTPUT_COLUMNS",
    "AM_ILCS_TIME_PERIOD",
    "AMILCSSpineBuildResult",
    "AMILCSSpineReceipt",
    "AMILCSSpineStageTransform",
    "am_ilcs_spine_seed_frame",
    "build_am_ilcs_spine",
    "build_am_ilcs_spine_frame",
]

AM_ILCS_TIME_PERIOD = "2024"
AM_ILCS_HOUSEHOLD_ROWS = 5_184
AM_ILCS_MEMBER_ROWS = 17_744
_SENTINEL = -999_999_999
_PERSON_ID_MULTIPLIER = 1_000

_HOUSEHOLD_REQUIRED_COLUMNS = frozenset(
    {
        "interview__key",
        "date_q",
        "hh_02",
        "settlement",
        "members",
        "memnal",
        "Weight",
        "pweight",
        "expend",
        "monincome",
        "totincome",
        "nonmoninc",
        "y1_3amd.1.00",
        "y1_3amd.2.00",
        "y1_3amd.4.00",
        "y1_3amd.6.00",
        "y1_3amd.8.00",
        "y1_3amd.9.00",
        "y1_3amd.10.00",
        "y1_3amd.12.00",
        "y1_3amd.17.00",
        "y1_3amd.18.00",
        "y1_3amd.19.00",
        "aec_r",
        "poverty",
    }
)
_MEMBER_REQUIRED_COLUMNS = frozenset(
    {
        "interview__key",
        "mem_001__id",
        "weight",
        "date",
        "mem_02",
        "mem_03",
        "mem_05",
        "ed_03",
        "emp_04",
        "emp_05",
        "emp_10",
        "emplj",
        "unemployed",
        "activ",
    }
)

_MARZ = {
    1: "YEREVAN",
    2: "ARAGATSOTN",
    3: "ARARAT",
    4: "ARMAVIR",
    5: "GEGHARKUNIK",
    6: "LORI",
    7: "KOTAYK",
    8: "SHIRAK",
    9: "SYUNIK",
    10: "VAYOTS_DZOR",
    11: "TAVUSH",
}
_SETTLEMENT = {1: "URBAN", 2: "RURAL"}
_SEX = {1: "MALE", 2: "FEMALE"}
_RELATIONSHIP = {
    1: "HEAD",
    2: "SPOUSE",
    3: "CHILD",
    4: "CHILD_IN_LAW",
    5: "GRANDCHILD",
    6: "PARENT",
    7: "OTHER_RELATIVE",
    8: "NON_RELATIVE",
}
_EDUCATION = {
    0: "NONE",
    1: "PRIMARY",
    2: "GENERAL",
    3: "SECONDARY",
    4: "PRELIMINARY_VOCATIONAL",
    5: "MIDDLE_VOCATIONAL",
    6: "HIGHER",
    7: "POST_GRADUATE",
    8: "OTHER",
}
_EMPLOYMENT_STATUS = {
    1: "EMPLOYER",
    2: "EMPLOYEE_WRITTEN_CONTRACT",
    3: "EMPLOYEE_VERBAL_AGREEMENT",
    4: "OWN_ACCOUNT_FARM",
    5: "OWN_ACCOUNT_OTHER",
    6: "UNPAID_FAMILY_WORKER",
    7: "COOPERATIVE_MEMBER",
    8: "OTHER",
}
_POVERTY = {1: "NON_POOR", 2: "POOR", 3: "VERY_POOR"}

_MONTHLY_AMOUNTS = {
    "expend": "household_expenditure_monthly",
    "monincome": "monetary_income_monthly",
    "totincome": "total_income_monthly",
    "nonmoninc": "non_monetary_income_monthly",
    "y1_3amd.1.00": "employment_income_monthly",
    "y1_3amd.2.00": "self_employment_income_monthly",
    "y1_3amd.4.00": "pension_income_reported_monthly",
    "y1_3amd.6.00": "family_benefit_reported_monthly",
    "y1_3amd.8.00": "childbirth_grant_reported_monthly",
    "y1_3amd.9.00": "child_under_two_benefit_reported_monthly",
    "y1_3amd.10.00": "other_child_benefit_reported_monthly",
    "y1_3amd.12.00": "other_benefit_reported_monthly",
    "y1_3amd.17.00": "property_and_investment_income_monthly",
    "y1_3amd.18.00": "private_transfer_income_domestic_monthly",
    "y1_3amd.19.00": "private_transfer_income_abroad_monthly",
    "aec_r": "adult_equivalent_consumption_monthly",
}

AM_ILCS_OUTPUT_COLUMNS = (
    "person_id",
    "person_household_id",
    "age",
    "sex",
    "relationship_to_household_head",
    "education_level",
    "is_employed",
    "is_employee",
    "is_unemployed",
    "is_economically_active",
    "employment_status",
    "industry_code",
    "usual_weekly_hours",
    "household_id",
    "ilcs_interview_key",
    "survey_month",
    "marz_code_observed",
    "settlement_type",
    "household_members_reported",
    "present_household_size",
    *_MONTHLY_AMOUNTS.values(),
    "poverty_status_survey",
)


@dataclass(frozen=True)
class AMILCSSpineReceipt:
    """Auditable linkage and weight checks produced by one ILCS ingest."""

    artifact_pins: Mapping[str, Mapping[str, object]]
    household_rows: int
    member_rows: int
    household_weight_total: float
    person_weight_total: float
    pweight_total: float
    member_weight_household_max_abs_error: float
    pweight_identity_max_abs_error: float
    roster_member_discrepant_households: int
    observed_monthly_amd_totals: Mapping[str, float]

    def as_dict(self) -> dict[str, object]:
        return {
            "artifact_pins": {
                table: dict(pin) for table, pin in sorted(self.artifact_pins.items())
            },
            "join": {
                "validation": "many_to_one_total_on_both_sides",
                "household_rows": self.household_rows,
                "member_rows": self.member_rows,
                "present_member_count_field": "memnal",
                "roster_member_count_field": "members",
                "roster_member_discrepant_households": (
                    self.roster_member_discrepant_households
                ),
            },
            "weights": {
                "kind": WeightKind.DESIGN.value,
                "household_weight_total": self.household_weight_total,
                "person_weight_total": self.person_weight_total,
                "pweight_total": self.pweight_total,
                "member_weight_relation": "member.weight == household.Weight",
                "member_weight_household_max_abs_error": (
                    self.member_weight_household_max_abs_error
                ),
                "pweight_relation": "pweight ~= Weight * memnal",
                "pweight_identity_max_abs_error": self.pweight_identity_max_abs_error,
                "pweight_rounding_tolerance": {"rtol": 1e-6, "atol": 1e-4},
            },
            "amount_basis": {
                "currency": "AMD",
                "definition_period": "month",
                "annualization_factor": 1.0,
                "annualization_applied": False,
                "survey_period": AM_ILCS_TIME_PERIOD,
            },
            "validation_only_observed_monthly_amd": {
                "classification": "validation_only",
                "weight": "household design Weight",
                "perimeter": (
                    "weighted sums of additive observed ILCS household columns; "
                    "not administrative, national-accounts, tax, or simulated "
                    "totals; equivalized consumption is excluded as nonadditive"
                ),
                "annualization_applied": False,
                "totals": dict(sorted(self.observed_monthly_amd_totals.items())),
            },
        }


@dataclass(frozen=True)
class AMILCSSpineBuildResult:
    frame: Frame
    receipt: AMILCSSpineReceipt


class AMILCSSpineStageTransform:
    """Whole-stage callable for the additive native ILCS source channel."""

    def __init__(self, raw_dir: str | Path, *, stage: SourceStageSpec) -> None:
        self.raw_dir = Path(raw_dir)
        self.stage = stage
        self.last_receipt: AMILCSSpineReceipt | None = None

    def __call__(self, frame: Frame) -> Frame:
        result = build_am_ilcs_spine(self.raw_dir, stage=self.stage)
        self.last_receipt = result.receipt
        return result.frame

    @staticmethod
    def output_columns() -> tuple[str, ...]:
        return AM_ILCS_OUTPUT_COLUMNS


def am_ilcs_spine_seed_frame() -> Frame:
    """Minimal valid input for the root stage, whose source replaces all rows."""

    person = pd.DataFrame({"person_id": [1], "person_household_id": [1]})
    household = pd.DataFrame({"household_id": [1], "household_weight": [1.0]})
    return am_national_frame(
        person=person,
        household=household,
        time_period=AM_ILCS_TIME_PERIOD,
        weight_kind=WeightKind.DESIGN,
    )


def build_am_ilcs_spine_frame(raw_dir: str | Path, *, stage: SourceStageSpec) -> Frame:
    return build_am_ilcs_spine(raw_dir, stage=stage).frame


def build_am_ilcs_spine(
    raw_dir: str | Path, *, stage: SourceStageSpec
) -> AMILCSSpineBuildResult:
    """Read two pinned XLSX files and build the native 2024 ILCS Frame."""

    artifacts = _artifact_by_table(stage)
    raw_root = Path(raw_dir)
    household, household_pin = _read_pinned_xlsx(
        raw_root / str(artifacts["household"]["locator"]),
        artifacts["household"],
        required_columns=_HOUSEHOLD_REQUIRED_COLUMNS,
    )
    member, member_pin = _read_pinned_xlsx(
        raw_root / str(artifacts["member"]["locator"]),
        artifacts["member"],
        required_columns=_MEMBER_REQUIRED_COLUMNS,
    )
    return _assemble_frame(
        household,
        member,
        artifact_pins={"household": household_pin, "member": member_pin},
    )


def _artifact_by_table(stage: SourceStageSpec) -> dict[str, Mapping[str, Any]]:
    by_table: dict[str, Mapping[str, Any]] = {}
    for artifact in stage.artifacts:
        table = artifact.get("table")
        if isinstance(table, str):
            if table in by_table:
                raise ValueError(f"Duplicate AM ILCS artifact for table {table!r}.")
            by_table[table] = artifact
    expected = {"household", "member"}
    missing = sorted(expected - set(by_table))
    unknown = sorted(set(by_table) - expected)
    if missing:
        raise ValueError(f"AM ILCS manifest is missing artifact(s): {missing}.")
    if unknown:
        raise ValueError(f"AM ILCS manifest declares unknown artifact(s): {unknown}.")
    return by_table


def _read_pinned_xlsx(
    path: Path,
    artifact: Mapping[str, Any],
    *,
    required_columns: frozenset[str],
) -> tuple[pd.DataFrame, dict[str, object]]:
    if not path.is_file():
        raise FileNotFoundError(f"AM ILCS workbook is missing: {path}.")
    if str(artifact.get("format", "")).lower() != "xlsx":
        raise ValueError("AM ILCS artifacts must declare format 'xlsx'.")
    if artifact.get("runtime_sha256_required") is not True:
        raise ValueError("AM ILCS artifacts must require runtime SHA-256 verification.")
    stat_before = path.stat()
    expected_size = int(artifact["size_bytes"])
    if stat_before.st_size != expected_size:
        raise ValueError(
            f"AM ILCS workbook {path.name} is {stat_before.st_size} bytes, "
            f"not the pinned {expected_size}."
        )
    expected_sha = str(artifact["sha256"])
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha:
        raise ValueError(
            f"AM ILCS workbook {path.name} hashes to {actual_sha}, "
            f"not the pinned {expected_sha}."
        )
    try:
        frame = pd.read_excel(
            path,
            sheet_name=str(artifact["sheet"]),
            engine="openpyxl",
        )
    except ImportError as exc:  # pragma: no cover - optional AM runtime extra
        raise RuntimeError(
            "openpyxl is required for the Armenia ILCS XLSX runtime."
        ) from exc
    stat_after = path.stat()
    before_identity = (
        stat_before.st_dev,
        stat_before.st_ino,
        stat_before.st_size,
        stat_before.st_mtime_ns,
        stat_before.st_ctime_ns,
    )
    after_identity = (
        stat_after.st_dev,
        stat_after.st_ino,
        stat_after.st_size,
        stat_after.st_mtime_ns,
        stat_after.st_ctime_ns,
    )
    if after_identity != before_identity:
        raise RuntimeError(
            f"AM ILCS workbook {path.name} changed while being read; refusing "
            "to bind mixed bytes."
        )
    if frame.columns.isna().any() or frame.columns.duplicated().any():
        raise ValueError(f"AM ILCS workbook {path.name} has invalid column headers.")
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(
            f"AM ILCS workbook {path.name} is missing column(s): {missing_columns}."
        )
    expected_rows = int(artifact["expected_rows"])
    if len(frame) != expected_rows:
        raise ValueError(
            f"AM ILCS workbook {path.name} has {len(frame)} rows, "
            f"not the pinned {expected_rows}."
        )
    pin = {
        "locator": str(artifact["locator"]),
        "sheet": str(artifact["sheet"]),
        "sha256": actual_sha,
        "size_bytes": stat_after.st_size,
        "rows": len(frame),
    }
    return frame.replace(_SENTINEL, np.nan), pin


def _assemble_frame(
    household_raw: pd.DataFrame,
    member_raw: pd.DataFrame,
    *,
    artifact_pins: Mapping[str, Mapping[str, object]],
) -> AMILCSSpineBuildResult:
    household = household_raw.copy()
    member = member_raw.copy()
    household_keys = _required_keys(household, table="household")
    member_keys = _required_keys(member, table="member")
    if household_keys.duplicated().any():
        duplicates = household_keys[household_keys.duplicated()].head(5).tolist()
        raise ValueError(
            f"AM ILCS household keys must be unique; duplicated: {duplicates}."
        )
    household_key_set = set(household_keys)
    member_key_set = set(member_keys)
    dangling = sorted(member_key_set - household_key_set)
    orphaned = sorted(household_key_set - member_key_set)
    if dangling:
        raise ValueError(f"AM ILCS member keys absent from households: {dangling[:5]}.")
    if orphaned:
        raise ValueError(f"AM ILCS households with no present members: {orphaned[:5]}.")

    source_person_id = _strict_integer(member["mem_001__id"], "mem_001__id")
    normalized_people = pd.DataFrame(
        {"interview__key": member_keys, "mem_001__id": source_person_id}
    )
    duplicate_people = normalized_people.duplicated(["interview__key", "mem_001__id"])
    if duplicate_people.any():
        rows = normalized_people.loc[
            duplicate_people, ["interview__key", "mem_001__id"]
        ].head(5)
        raise ValueError(
            "AM ILCS member key pairs must be unique after normalization; "
            f"duplicated: {rows.to_dict('records')}."
        )
    if (source_person_id < 1).any() or (
        source_person_id >= _PERSON_ID_MULTIPLIER
    ).any():
        raise ValueError("AM ILCS mem_001__id must be in [1, 999] for stable ids.")

    sorted_keys = sorted(household_key_set)
    id_by_key = {key: ordinal for ordinal, key in enumerate(sorted_keys, start=1)}
    household["_household_id"] = household_keys.map(id_by_key).astype("int64")
    member["_household_id"] = member_keys.map(id_by_key).astype("int64")
    member["_person_id"] = (
        member["_household_id"] * _PERSON_ID_MULTIPLIER + source_person_id
    ).astype("int64")

    member_counts = member_keys.value_counts(sort=False)
    present_members = _strict_integer(household["memnal"], "memnal")
    observed_counts = household_keys.map(member_counts).astype("int64")
    mismatch = present_members != observed_counts
    if mismatch.any():
        keys = household_keys[mismatch].head(5).tolist()
        raise ValueError(
            "AM ILCS memnal must equal joined present-member rows; mismatch for "
            f"household key(s): {keys}."
        )

    household_weight = _positive_finite(household["Weight"], "Weight")
    member_weight = _positive_finite(member["weight"], "member.weight")
    expected_member_weight = member_keys.map(
        pd.Series(household_weight.to_numpy(), index=household_keys)
    ).astype("float64")
    member_error = np.abs(member_weight.to_numpy() - expected_member_weight.to_numpy())
    if not np.allclose(member_weight, expected_member_weight, rtol=1e-12, atol=0.0):
        bad_key = member_keys.iloc[int(np.argmax(member_error))]
        raise ValueError(
            "AM ILCS member.weight must equal household.Weight within each "
            f"household; largest disagreement is for {bad_key!r}."
        )
    pweight = _positive_finite(household["pweight"], "pweight")
    expected_pweight = household_weight * present_members
    pweight_error = np.abs(pweight.to_numpy() - expected_pweight.to_numpy())
    if not np.allclose(pweight, expected_pweight, rtol=1e-6, atol=1e-4):
        bad_key = household_keys.iloc[int(np.argmax(pweight_error))]
        raise ValueError(
            "AM ILCS pweight must equal Weight * memnal within published "
            f"rounding tolerance; largest disagreement is for {bad_key!r}."
        )

    survey_month = _survey_month(household["date_q"], "date_q")
    member_month = _survey_month(member["date"], "member.date")
    expected_member_month = member_keys.map(
        pd.Series(survey_month.to_numpy(), index=household_keys)
    ).astype("int64")
    if not member_month.equals(expected_member_month.reset_index(drop=True)):
        mismatch_index = np.flatnonzero(
            member_month.to_numpy() != expected_member_month.to_numpy()
        )
        bad_key = member_keys.iloc[int(mismatch_index[0])]
        raise ValueError(
            "AM ILCS member survey month must match its household; mismatch for "
            f"{bad_key!r}."
        )

    person = pd.DataFrame(
        {
            "person_id": member["_person_id"].astype("int64"),
            "person_household_id": member["_household_id"].astype("int64"),
            "age": _nonnegative_integer(member["mem_05"], "mem_05"),
            "sex": _map_required_codes(member["mem_02"], _SEX, "mem_02"),
            "relationship_to_household_head": _map_required_codes(
                member["mem_03"], _RELATIONSHIP, "mem_03"
            ),
            "education_level": _map_optional_codes(
                member["ed_03"], _EDUCATION, "ed_03"
            ),
            "is_employed": _optional_indicator(member["emplj"], "emplj"),
            "is_employee": member["emp_05"].isin([2, 3]).astype(bool),
            "is_unemployed": _optional_indicator(member["unemployed"], "unemployed"),
            "is_economically_active": _optional_indicator(member["activ"], "activ"),
            "employment_status": _map_optional_codes(
                member["emp_05"],
                _EMPLOYMENT_STATUS,
                "emp_05",
                missing="NOT_EMPLOYED",
            ),
            "industry_code": _optional_code_strings(member["emp_04"], "emp_04"),
            "usual_weekly_hours": _nonnegative(
                member["emp_10"], "emp_10", fill_missing=0.0
            ),
        }
    ).sort_values("person_id", ignore_index=True)

    roster_members = _strict_integer(household["members"], "members")
    roster_shortfall = roster_members < present_members
    if roster_shortfall.any():
        keys = household_keys[roster_shortfall].head(5).tolist()
        raise ValueError(
            "AM ILCS members must be greater than or equal to memnal; "
            f"shortfall for household key(s): {keys}."
        )
    carrier_household = pd.DataFrame(
        {
            "household_id": household["_household_id"].astype("int64"),
            "ilcs_interview_key": household_keys,
            "survey_month": survey_month,
            "marz_code_observed": _map_required_codes(
                household["hh_02"], _MARZ, "hh_02"
            ),
            "settlement_type": _map_required_codes(
                household["settlement"], _SETTLEMENT, "settlement"
            ),
            "household_members_reported": roster_members,
            "present_household_size": present_members,
        }
    )
    for source, destination in _MONTHLY_AMOUNTS.items():
        carrier_household[destination] = _nonnegative(
            household[source], source, fill_missing=0.0
        )
    carrier_household["poverty_status_survey"] = _map_required_codes(
        household["poverty"], _POVERTY, "poverty"
    )
    carrier_household["household_weight"] = household_weight
    carrier_household = carrier_household.sort_values("household_id", ignore_index=True)

    frame = am_national_frame(
        person=person,
        household=carrier_household,
        time_period=AM_ILCS_TIME_PERIOD,
        weight_kind=WeightKind.DESIGN,
    )
    validate_am_national_frame(frame)
    receipt = AMILCSSpineReceipt(
        artifact_pins=artifact_pins,
        household_rows=len(carrier_household),
        member_rows=len(person),
        household_weight_total=float(household_weight.sum()),
        person_weight_total=float(member_weight.sum()),
        pweight_total=float(pweight.sum()),
        member_weight_household_max_abs_error=float(member_error.max(initial=0.0)),
        pweight_identity_max_abs_error=float(pweight_error.max(initial=0.0)),
        roster_member_discrepant_households=int(
            (roster_members != present_members).sum()
        ),
        observed_monthly_amd_totals={
            destination: float(
                np.dot(
                    carrier_household["household_weight"].to_numpy(dtype="float64"),
                    carrier_household[destination].to_numpy(dtype="float64"),
                )
            )
            for source, destination in _MONTHLY_AMOUNTS.items()
            # ``aec_r`` is an equivalized per-person welfare statistic, not an
            # additive household flow. Keep it on the frame, never total it.
            if source != "aec_r"
        },
    )
    return AMILCSSpineBuildResult(frame=frame, receipt=receipt)


def _required_keys(frame: pd.DataFrame, *, table: str) -> pd.Series:
    keys = frame["interview__key"]
    if keys.isna().any() or keys.astype(str).str.strip().eq("").any():
        raise ValueError(f"AM ILCS {table} interview__key must be non-empty.")
    return keys.astype(str)


def _strict_integer(values: pd.Series, name: str) -> pd.Series:
    numeric = _numeric_when_present(values, name)
    if (
        numeric.isna().any()
        or not np.isfinite(numeric).all()
        or not np.equal(numeric, np.floor(numeric)).all()
    ):
        raise ValueError(f"AM ILCS {name} must contain only integers.")
    return numeric.astype("int64")


def _nonnegative_integer(values: pd.Series, name: str) -> pd.Series:
    numeric = _strict_integer(values, name)
    if (numeric < 0).any():
        raise ValueError(f"AM ILCS {name} must be a non-negative integer.")
    return numeric


def _positive_finite(values: pd.Series, name: str) -> pd.Series:
    numeric = _numeric_when_present(values, name).astype("float64")
    if numeric.isna().any() or not np.isfinite(numeric).all() or (numeric <= 0).any():
        raise ValueError(f"AM ILCS {name} must be positive and finite.")
    return numeric


def _nonnegative(
    values: pd.Series, name: str, *, fill_missing: float | None = None
) -> pd.Series:
    numeric = _numeric_when_present(values, name).astype("float64")
    if fill_missing is not None:
        numeric = numeric.fillna(fill_missing)
    if numeric.isna().any() or not np.isfinite(numeric).all() or (numeric < 0).any():
        raise ValueError(f"AM ILCS {name} must be non-negative and finite.")
    return numeric


def _map_required_codes(
    values: pd.Series, mapping: Mapping[int, str], name: str
) -> pd.Series:
    codes = _strict_integer(values, name)
    unknown = sorted(set(codes) - set(mapping))
    if unknown:
        raise ValueError(f"AM ILCS {name} has unknown code(s): {unknown}.")
    return codes.map(mapping).astype("str")


def _map_optional_codes(
    values: pd.Series,
    mapping: Mapping[int, str],
    name: str,
    *,
    missing: str = "UNKNOWN",
) -> pd.Series:
    numeric = _numeric_when_present(values, name)
    present = numeric.dropna()
    if not np.isfinite(present).all() or not np.equal(present, np.floor(present)).all():
        raise ValueError(f"AM ILCS {name} codes must be integers when present.")
    unknown = sorted(set(present.astype(int)) - set(mapping))
    if unknown:
        raise ValueError(f"AM ILCS {name} has unknown code(s): {unknown}.")
    return numeric.map(mapping).fillna(missing).astype("str")


def _optional_code_strings(values: pd.Series, name: str) -> pd.Series:
    numeric = _numeric_when_present(values, name)
    present = numeric.dropna()
    if (
        not np.isfinite(present).all()
        or not np.equal(present, np.floor(present)).all()
        or (present < 0).any()
    ):
        raise ValueError(f"AM ILCS {name} codes must be non-negative integers.")
    return numeric.map(
        lambda value: "NOT_EMPLOYED" if pd.isna(value) else f"{int(value):02d}"
    )


def _optional_indicator(values: pd.Series, name: str) -> pd.Series:
    numeric = _numeric_when_present(values, name)
    present = numeric.dropna()
    if not present.isin([0, 1]).all():
        raise ValueError(f"AM ILCS {name} must contain only 0, 1, or missing.")
    return numeric.fillna(0).eq(1).astype(bool)


def _survey_month(values: pd.Series, name: str) -> pd.Series:
    numeric = _numeric_when_present(values, name).astype("float64")
    if numeric.isna().any() or not np.isfinite(numeric).all():
        raise ValueError(f"AM ILCS {name} must contain a 2024 survey month.")
    years = np.floor(numeric).astype(int)
    months = np.rint((numeric - years) * 100).astype(int)
    # Excel reads ArmStat's September value ``2024.9`` as a float while the
    # other months retain two decimal digits (for example, ``2024.08`` and
    # ``2024.10``). After scaling, September is therefore 90 rather than 9.
    compact_september = months == 90
    months = np.where(compact_september, 9, months)
    if (
        not (years == int(AM_ILCS_TIME_PERIOD)).all()
        or not ((months >= 1) & (months <= 12)).all()
    ):
        raise ValueError(f"AM ILCS {name} must contain months within 2024.")
    return pd.Series(months, index=values.index, dtype="int64")


def _numeric_when_present(values: pd.Series, name: str) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    invalid = values.notna() & numeric.isna()
    if invalid.any():
        raise ValueError(f"AM ILCS {name} must be numeric when present.")
    return numeric
