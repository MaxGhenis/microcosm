"""Focused contract tests for the schema-v2 lineage dashboard payload."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "specs" / "us_imputation_lineage.yaml"
EMITTER = ROOT / "tools" / "emit_lineage_dashboard.py"
_PARTICIPATION_FAMILY = "gap_fill/asec_survey_to_acs/person/model_required_boolean"


@pytest.fixture(scope="module")
def emit():
    return runpy.run_path(str(EMITTER))["emit"]


def test_dashboard_shows_composed_family_predictors(emit) -> None:
    payload = emit(SPEC)

    assert payload["schema_version"] == 2
    assert payload["counts"] == {
        "imputed_variables": 118,
        "families": 32,
        "computed_producers": 19,
        "boolean": 24,
        "amount": 94,
    }
    assert payload["models"]["regime_gated_qrf"]["post_draw_calibration"] is None
    assert "predictor_blocks" in payload

    participation = next(
        row
        for row in payload["variables"]
        if row["family_id"] == _PARTICIPATION_FAMILY
        and row["variable"] == "has_champva_health_coverage_at_interview"
    )
    assert participation["predictor_blocks_required"] == ["core_demographics"]
    assert "disability" not in participation["predictor_blocks_optional"]
    assert {
        "veteran_va",
        "education_work",
        "own_coverage",
    } <= set(participation["predictor_blocks_optional"])
    assert participation["predictors_required"] == [
        "age",
        "is_female",
        "state_fips",
    ]
    assert participation["predictors_pending"] == [
        {
            "column": "puma",
            "block": "geography",
            "requirement": "optional",
            "pending": "microcosm#696",
        },
        {
            "column": "county_fips",
            "block": "geography",
            "requirement": "optional",
            "pending": "microcosm#696",
        },
    ]
    assert {
        row["column"]
        for row in participation["predictors_blocked_on_checkpoint_schema"]
    } == {
        "education_attainment_code",
        "english_ability_code",
        "va_service_connected_disability_rating",
    }

    late = next(
        row
        for row in payload["variables"]
        if row["family_id"] == "late_transfer/transfer:person/adult_care"
    )
    assert late["predictor_blocks_required"] == ["puf_tax_detail"]
    assert late["predictor_blocks_optional"] == []
    assert late["predictors_optional"] == []
    assert late["predictors_pending"] == []


def test_dashboard_refuses_a_missing_family_predictor_set(emit, tmp_path: Path) -> None:
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    del spec["predictor_sets"][_PARTICIPATION_FAMILY]
    malformed = tmp_path / "lineage.yaml"
    malformed.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="one-to-one family-id coverage"):
        emit(malformed)


def test_dashboard_refuses_a_target_bearing_income_aggregate(
    emit,
    tmp_path: Path,
) -> None:
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    family = "gap_fill/asec_survey_to_acs/person/puf_tax_itemization"
    spec["predictor_sets"][family]["optional_blocks"].append("social_security_income")
    malformed = tmp_path / "lineage.yaml"
    malformed.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="target-bearing predictor source"):
        emit(malformed)


def test_dashboard_refuses_pending_outside_the_geography_hook(
    emit,
    tmp_path: Path,
) -> None:
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    spec["predictor_blocks"]["core_demographics"]["columns"].append(
        {"column": "unmapped_future_column", "pending": "microcosm#696"}
    )
    malformed = tmp_path / "lineage.yaml"
    malformed.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="reserved for geography"):
        emit(malformed)


def test_dashboard_refuses_duplicate_yaml_keys(emit, tmp_path: Path) -> None:
    text = SPEC.read_text(encoding="utf-8")
    malformed = tmp_path / "lineage.yaml"
    malformed.write_text(
        text.replace(
            "schema_version: 2\n",
            "schema_version: 2\nschema_version: 2\n",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate YAML mapping key"):
        emit(malformed)


def test_dashboard_refuses_pending_geography_on_a_late_family(
    emit,
    tmp_path: Path,
) -> None:
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    family = "late_transfer/transfer:person/adult_care"
    spec["predictor_sets"][family]["optional_blocks"].append("geography")
    malformed = tmp_path / "lineage.yaml"
    malformed.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="late predictor set.*cannot declare"):
        emit(malformed)
