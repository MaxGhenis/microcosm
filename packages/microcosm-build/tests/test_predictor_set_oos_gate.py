"""Contract tests for the Phase-P predictor-set OOS acceptance gate."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from microcosm.build.frame_checkpoint import write_frame_checkpoint
from microcosm.fit import RegimeGatedQRF
from microcosm.frame import EntitySchema, Frame, WeightKind, Weights

ROOT = Path(__file__).resolve().parents[3]


def _gate_module():
    path = ROOT / "tools" / "predictor_set_oos_gate.py"
    spec = importlib.util.spec_from_file_location("predictor_set_oos_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GATE = _gate_module()


def _incidence_leg(
    ratio: float | None,
    *,
    asec: float = 0.1,
    status: str = "tested",
) -> dict[str, object]:
    return {
        "status": status,
        "asec_incidence": asec,
        "acs_incidence": None if ratio is None else asec * ratio,
        "incidence_ratio_acs_over_asec": ratio,
        "nonzero_rows": {"asec": 8, "acs": 9},
    }


def _gates_receipt(
    comparisons: dict[str, object],
    *,
    failures: list[str] | None = None,
) -> dict[str, object]:
    return {
        "terminal_gates": {
            "gates": {
                "us_by_origin_battery": {
                    "details": {"comparisons": comparisons},
                    "failures": failures or [],
                }
            }
        }
    }


def _write_artifact(
    root: Path,
    frame: Frame,
    *,
    identity: str,
    comparisons: dict[str, object],
    failures: list[str] | None = None,
):
    root.mkdir()
    gates_path = root / "fixture.gates.json"
    gates_path.write_text(json.dumps(_gates_receipt(comparisons, failures=failures)))
    checkpoint_path = (
        root / "fixture.checkpoints" / "stacked" / identity / "simulated.checkpoint.h5"
    )
    write_frame_checkpoint(
        checkpoint_path,
        frame,
        metadata={
            "identity_sha256": f"sha256:{identity}",
            "identity": {"fixture_arm": identity},
        },
    )
    return GATE.resolve_artifact(root)


PERSON_INVESTMENT = "__acs_transfer_interest_dividend_rental_income"
GROUP_INVESTMENT = "__acs_transfer_group_investment_income_sum"


def _investment_frame() -> Frame:
    person = pd.DataFrame(
        {
            "person_id": np.asarray([1, 2, 3, 4], dtype=np.int64),
            "person_spm_unit_id": np.asarray([10, 10, 20, 20], dtype=np.int64),
            "age": [40.0, 38.0, 50.0, 48.0],
            "is_female": [False, True, False, True],
            "state_fips": [6.0, 6.0, 36.0, 36.0],
            "INT_VAL": [1.0, 4.0, 7.0, 10.0],
            "DIV_VAL": [2.0, 5.0, np.nan, 11.0],
            "RNT_VAL": [3.0, 6.0, 9.0, 12.0],
            # The final checkpoint has the preferred post-PUF leaves. Their
            # deliberately different values must never leak into early OOS.
            "taxable_interest_income": [100.0, 110.0, 120.0, 130.0],
            "tax_exempt_interest_income": [10.0, 11.0, 12.0, 13.0],
            "qualified_dividend_income": [20.0, 21.0, 22.0, 23.0],
            "non_qualified_dividend_income": [30.0, 31.0, 32.0, 33.0],
            "rental_income": [40.0, 41.0, 42.0, 43.0],
            "estate_income": [50.0, 51.0, 52.0, 53.0],
        }
    )
    spm_unit = pd.DataFrame({"spm_unit_id": np.asarray([10, 20], dtype=np.int64)})
    return Frame(
        {"person": person, "spm_unit": spm_unit},
        EntitySchema(group_entities=("spm_unit",)),
        {
            "spm_unit": Weights(
                values=np.ones(2, dtype=np.float64),
                kind=WeightKind.DESIGN,
            )
        },
    )


def _early_fixture_spec(entity: str, target: str) -> object:
    if entity == "person":
        required = ("age", "is_female", "__acs_transfer_state_fips")
        optional = (PERSON_INVESTMENT,)
        family = "fixture_person"
    else:
        required = (
            "__acs_transfer_person_count",
            "__acs_transfer_age_sum",
            "__acs_transfer_female_count",
            "__acs_transfer_state_fips",
        )
        optional = (GROUP_INVESTMENT,)
        family = "fixture_group"
    predictors = GATE.AcsPredictorSet(required=required, optional=optional)
    return GATE.FamilySpec(
        family_id=f"gap_fill/asec_survey_to_acs/{entity}/{family}",
        stage="early_gap_fill",
        entity=entity,
        family=family,
        baseline_targets=(target,),
        candidate_targets=(target,),
        max_targets_per_fit=1,
        baseline_predictor_set=predictors,
        candidate_predictor_set=predictors,
    )


def _surface_evidence(
    specs: tuple[object, ...],
    *,
    include_features: bool,
) -> object:
    targets = {}
    for spec in specs:
        feature = PERSON_INVESTMENT if spec.entity == "person" else GROUP_INVESTMENT
        target = spec.baseline_targets[0]
        predictors = (
            *spec.baseline_predictor_set.required,
            *((feature,) if include_features else ()),
        )
        targets[(spec.family_id, target)] = GATE.EarlyTargetExecution(
            family_id=spec.family_id,
            direction="asec_survey_to_acs",
            entity=spec.entity,
            family=spec.family,
            target=target,
            bank_identity_sha256="1" * 64,
            checkpoint_path=Path(f"/{target}.h5"),
            checkpoint_sha256="2" * 64,
            pattern_predictors=(predictors,),
            resolved_predictors=predictors,
        )
    return GATE.EarlyExecutionEvidence(
        receipts_path=Path("/fixture/simulated.checkpoint.receipts.json"),
        receipts_sha256="3" * 64,
        simulated_checkpoint_sha256="4" * 64,
        targets=targets,
    )


def _completed_qrf_state(
    *,
    entity: str,
    predictors: tuple[str, ...],
    target: str,
) -> dict:
    data = {
        **{predictor: np.asarray([1.0, 2.0]) for predictor in predictors},
        target: np.asarray([0.0, 1.0]),
    }
    state = RegimeGatedQRF(n_estimators=1, seed=17).start_chain(
        pd.DataFrame(data),
        list(predictors),
        [target],
        weights=np.ones(2, dtype=np.float64),
    )
    payload = state.to_dict()
    payload["entity"] = entity
    payload["completed_targets"] = [target]
    payload["recipient_index"] = payload["donor_index"]
    return GATE.QRFChainState.from_dict(payload).to_dict()


def _write_target_checkpoint(
    path: Path,
    *,
    bank_identity: dict[str, object],
    bank_identity_sha256: str,
    target_index: int,
    total_targets: int,
    entity: str,
    family: str,
    target: str,
    predictors: tuple[str, ...],
) -> dict[str, object]:
    descriptor = {
        "target_index": target_index,
        "total_targets": total_targets,
        "entity": entity,
        "family": family,
        "family_targets": [target],
        "model_targets": [target],
        "model_target": target,
        "exported_targets": [target],
    }
    state_after = _completed_qrf_state(
        entity=entity,
        predictors=predictors,
        target=target,
    )
    raw_bits = np.asarray([0, 1], dtype="<u8")
    raw_sha256 = hashlib.sha256(raw_bits.tobytes()).hexdigest()
    metadata = {
        "artifact_kind": GATE.ACS_TRANSFER_TARGET_BANK_ARTIFACT_KIND,
        "schema_version": GATE.ACS_TRANSFER_TARGET_BANK_SCHEMA_VERSION,
        "materializer_version": GATE.ACS_TRANSFER_TARGET_BANK_MATERIALIZER_VERSION,
        "identity": bank_identity,
        "identity_sha256": bank_identity_sha256,
        "target": descriptor,
        "recipient_rows": len(raw_bits),
        "raw_draw_sha256": raw_sha256,
        "pattern_steps": [
            {
                "pattern": "pattern_00_fixture",
                "state_before_sha256": "5" * 64,
                "state_after": state_after,
            }
        ],
    }
    metadata["content_metadata_sha256"] = GATE._bank_mapping_sha256(metadata)
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, mode="w") as h5:
        h5.create_dataset(
            "metadata_json",
            data=np.frombuffer(
                json.dumps(
                    metadata,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode(),
                dtype=np.uint8,
            ),
            dtype=np.uint8,
        )
        h5.create_dataset("raw_draw_bits", data=raw_bits, dtype="<u8")
    return {
        "source": "rebuilt",
        "descriptor": descriptor,
        "load_status": "missing",
        "path": str(path.resolve()),
        "checkpoint_sha256": GATE._sha256_file(path),
        "size_bytes": path.stat().st_size,
        "raw_draw_sha256": raw_sha256,
        "content_metadata_sha256": metadata["content_metadata_sha256"],
        "write_status": "rebuilt",
        "write_seconds": 0.01,
    }


def _write_execution_artifact(
    root: Path,
    *,
    arm: str,
    person_feature_present: bool,
    group_feature_present: bool,
) -> tuple[object, tuple[object, ...], dict[str, object]]:
    root.mkdir()
    (root / "fixture.gates.json").write_text(json.dumps(_gates_receipt({})))
    checkpoint_path = (
        root
        / "fixture.checkpoints"
        / "stacked"
        / f"{arm}-fixture"
        / "simulated.checkpoint.h5"
    )
    authority_sha256 = ("a" if arm == "baseline" else "b") * 64
    gap_sha256 = ("c" if arm == "baseline" else "d") * 64
    stage_identity_sha256 = ("e" if arm == "baseline" else "f") * 64
    write_frame_checkpoint(
        checkpoint_path,
        _investment_frame(),
        metadata={
            "artifact_kind": "populace_us_multispine_pool_stage_checkpoint",
            "schema_version": 1,
            "materializer_version": 7,
            "stage": "simulated",
            "identity_sha256": stage_identity_sha256,
            "identity": {
                "stacked_authority": {
                    "version": 10 if arm == "baseline" else 11,
                    "authority_id": "us_stacked_spine_authority",
                    "authority_form": "CANONICAL",
                    "declared_authority_form": "CANONICAL",
                    "sha256": authority_sha256,
                    "declared_sha256": authority_sha256,
                    "canonical": True,
                    "canonical_content": True,
                    "canonical_identity": True,
                    "digest_matches_declared": True,
                    "integrity_valid": True,
                    "production_manifest_permitted": True,
                    "components": {
                        "gap_fill_plan": {
                            "sha256": gap_sha256,
                            "declared_sha256": gap_sha256,
                            "digest_matches_declared": True,
                            "target_count": 48,
                            "direction_count": 2,
                        }
                    },
                }
            },
        },
    )
    artifact = GATE.resolve_artifact(root)
    person_spec = _early_fixture_spec("person", "person_target")
    group_spec = _early_fixture_spec("spm_unit", "group_target")
    specs = (person_spec, group_spec)
    bank_identity = {"artifact_kind": "fixture_bank", "note": "café"}
    bank_identity_sha256 = GATE._bank_mapping_sha256(bank_identity)
    bank_root = checkpoint_path.parent / "acs-transfer" / "asec_survey_to_acs"
    records = {}
    for index, (spec, present) in enumerate(
        (
            (person_spec, person_feature_present),
            (group_spec, group_feature_present),
        )
    ):
        feature = PERSON_INVESTMENT if spec.entity == "person" else GROUP_INVESTMENT
        predictors = (
            *spec.baseline_predictor_set.required,
            *((feature,) if present else ()),
        )
        target = spec.baseline_targets[0]
        records[str(index)] = _write_target_checkpoint(
            bank_root / "targets" / f"{index:03d}__{target}.h5",
            bank_identity=bank_identity,
            bank_identity_sha256=bank_identity_sha256,
            target_index=index,
            total_targets=2,
            entity=spec.entity,
            family=spec.family,
            target=target,
            predictors=predictors,
        )
    sidecar = {
        "artifact_kind": (
            "populace_us_multispine_pool_stage_checkpoint_operational_receipts"
        ),
        "schema_version": 1,
        "materializer_version": 7,
        "stage": "simulated",
        "identity_sha256": stage_identity_sha256,
        "checkpoint": {
            "filename": checkpoint_path.name,
            "sha256": GATE._sha256_file(checkpoint_path),
            "size_bytes": checkpoint_path.stat().st_size,
        },
        "operational_stage_receipts": {
            "impute": {
                "acs_qrf_transfer": {
                    "target_bank": {
                        "directions": {
                            "asec_survey_to_acs": {
                                "artifact_kind": (
                                    GATE.ACS_TRANSFER_TARGET_BANK_RECEIPT_ARTIFACT_KIND
                                ),
                                "schema_version": (
                                    GATE.ACS_TRANSFER_TARGET_BANK_SCHEMA_VERSION
                                ),
                                "materializer_version": (
                                    GATE.ACS_TRANSFER_TARGET_BANK_MATERIALIZER_VERSION
                                ),
                                "root": str(bank_root.resolve()),
                                "identity": bank_identity,
                                "identity_sha256": bank_identity_sha256,
                                "targets": records,
                            }
                        },
                        "identity_routing": {},
                        "late_producer_groups": {},
                    }
                }
            }
        },
    }
    artifact.operational_receipts_path.write_text(
        json.dumps(sidecar, ensure_ascii=False)
    )
    role_binding = {
        "stacked_authority_version": 10 if arm == "baseline" else 11,
        "stacked_authority_sha256": authority_sha256,
        "gap_fill_plan_sha256": gap_sha256,
        "early_target_bank_identity_sha256": {
            "asec_survey_to_acs": bank_identity_sha256
        },
    }
    return artifact, specs, role_binding


def _battery_comparisons(
    *,
    champva_ratio: float | None,
    other_boolean_ratio: float | None,
    positive_money_ratio: float | None,
    negative_money_ratio: float | None,
) -> dict[str, object]:
    champva = GATE.PHASE_P_CONFIG["verdict"]["champva_leg"]
    return {
        champva: {
            "metric": "boolean_incidence",
            **_incidence_leg(champva_ratio, asec=0.02),
        },
        "person/model_required_boolean/receives_wic[clone_0]": {
            "metric": "boolean_incidence",
            **_incidence_leg(other_boolean_ratio, asec=0.04),
        },
        "person/earnings/wages[clone_0]": {
            "metric": "monetary_sign_separated",
            "status": "tested",
            "legs": {
                "positive": _incidence_leg(positive_money_ratio),
                "negative": _incidence_leg(negative_money_ratio),
            },
        },
        "person/demographics/category[clone_0]": {
            "metric": "categorical_tvd",
            "status": "tested",
            "total_variation_distance": 0.02,
        },
    }


def _oos_measurement(
    losses: list[float],
    *,
    ids: list[str],
    clusters: list[int],
):
    size = len(ids)
    return GATE.OOSTargetMeasurement(
        key="early_gap_fill/person/earnings/wages",
        family_id="early_gap_fill/person/earnings",
        stage="early_gap_fill",
        entity="person",
        family="earnings",
        target="wages",
        target_position=0,
        chain_predecessors=(),
        predictor_set={"required": ["age"], "optional": []},
        resolved_predictors=("age",),
        unavailable_optional_predictors=(),
        training_rows=100,
        holdout_rows=size,
        ids=np.asarray(ids, dtype=object),
        weights=np.ones(size, dtype=np.float64),
        truth=np.zeros(size, dtype=np.float64),
        losses=np.asarray(losses, dtype=np.float64),
        clusters=np.asarray(clusters, dtype=np.int16),
    )


def test_resolve_artifact_discovers_real_frame_checkpoint(
    tmp_path: Path,
    small_frame: Frame,
) -> None:
    comparisons = _battery_comparisons(
        champva_ratio=3.72,
        other_boolean_ratio=1.0,
        positive_money_ratio=1.0,
        negative_money_ratio=2.0,
    )

    artifact = _write_artifact(
        tmp_path / "baseline",
        small_frame,
        identity="baseline-fixture",
        comparisons=comparisons,
    )

    assert artifact.gates_path.name == "fixture.gates.json"
    assert artifact.checkpoint_path == (
        artifact.root
        / "fixture.checkpoints"
        / "stacked"
        / "baseline-fixture"
        / "simulated.checkpoint.h5"
    )
    external = artifact.checkpoint_metadata["external_metadata"]
    assert external["identity"] == {"fixture_arm": "baseline-fixture"}
    assert external["identity_sha256"] == "sha256:baseline-fixture"


def test_battery_transitions_and_participation_rows_come_from_receipts(
    tmp_path: Path,
    small_frame: Frame,
) -> None:
    baseline = _write_artifact(
        tmp_path / "baseline",
        small_frame,
        identity="baseline",
        comparisons=_battery_comparisons(
            champva_ratio=3.72,
            other_boolean_ratio=1.0,
            positive_money_ratio=1.0,
            negative_money_ratio=2.0,
        ),
        failures=[
            "person/earnings/wages[clone_0]/positive: "
            "conditional-quantile envelope distance 0.30 exceeds 0.25."
        ],
    )
    candidate = _write_artifact(
        tmp_path / "candidate",
        small_frame,
        identity="candidate",
        comparisons=_battery_comparisons(
            champva_ratio=1.20,
            other_boolean_ratio=1.10,
            positive_money_ratio=1.40,
            negative_money_ratio=2.20,
        ),
    )

    rows, counts = GATE.battery_delta(baseline, candidate)

    assert counts == {
        "total_legs": 5,
        "ratio_comparable_legs": 4,
        "entered_band": 1,
        "left_band": 1,
        "unchanged": 3,
        "unchanged_in_band": 1,
        "unchanged_out_of_band": 1,
        "unchanged_not_ratio_comparable": 1,
    }
    transitions = {row["leg_id"]: row["transition"] for row in rows}
    champva = GATE.PHASE_P_CONFIG["verdict"]["champva_leg"]
    assert transitions[champva] == "entered_band"
    assert transitions["person/earnings/wages[clone_0]/positive"] == "left_band"
    positive = next(
        row
        for row in rows
        if row["leg_id"] == "person/earnings/wages[clone_0]/positive"
    )
    assert positive["baseline"]["gate_status"] == "FAIL"
    assert positive["candidate"]["gate_status"] == "PASS"
    assert positive["gate_status_transition"] == "FAIL->PASS"

    participation = GATE.participation_incidence(baseline, candidate)

    assert [row["leg_id"] for row in participation] == [
        champva,
        "person/model_required_boolean/receives_wic[clone_0]",
    ]
    champva_row = participation[0]
    assert champva_row["baseline"]["asec_incidence"] == pytest.approx(0.02)
    assert champva_row["baseline"]["incidence_ratio_acs_over_asec"] == pytest.approx(
        3.72
    )
    assert champva_row["candidate"]["incidence_ratio_acs_over_asec"] == pytest.approx(
        1.20
    )
    assert champva_row["candidate"]["nonzero_rows"] == {"asec": 8, "acs": 9}

    noncomparable = _write_artifact(
        tmp_path / "candidate_noncomparable",
        small_frame,
        identity="candidate-noncomparable",
        comparisons=_battery_comparisons(
            champva_ratio=1.20,
            other_boolean_ratio=None,
            positive_money_ratio=1.0,
            negative_money_ratio=2.0,
        ),
    )
    noncomparable_rows, noncomparable_counts = GATE.battery_delta(
        baseline,
        noncomparable,
    )
    noncomparable_transitions = {
        row["leg_id"]: row["transition"] for row in noncomparable_rows
    }
    assert (
        noncomparable_transitions["person/model_required_boolean/receives_wic[clone_0]"]
        == "left_band"
    )
    assert noncomparable_counts["left_band"] == 1
    assert GATE._band_status("inf", lower=0.8, upper=1.25) == "out_of_band"


def test_significant_money_oos_worsening_fails_clause_b_and_verdict(
    tmp_path: Path,
    small_frame: Frame,
) -> None:
    comparisons = _battery_comparisons(
        champva_ratio=1.20,
        other_boolean_ratio=1.0,
        positive_money_ratio=1.0,
        negative_money_ratio=1.0,
    )
    baseline = _write_artifact(
        tmp_path / "baseline",
        small_frame,
        identity="baseline",
        comparisons=comparisons,
    )
    candidate = _write_artifact(
        tmp_path / "candidate",
        small_frame,
        identity="candidate",
        comparisons=comparisons,
    )
    baseline_measurement = _oos_measurement(
        [1.0, 1.0, 1.0, 1.0],
        ids=["a", "b", "c", "d"],
        clusters=[0, 1, 2, 3],
    )
    # Reverse row order to prove pairing is by stable donor id, not position.
    candidate_measurement = _oos_measurement(
        [2.0, 2.0, 2.0, 2.0],
        ids=["d", "c", "b", "a"],
        clusters=[3, 2, 1, 0],
    )

    paired = GATE._paired_loss_comparison(
        baseline_measurement,
        candidate_measurement,
    )

    assert paired["baseline_mean_pinball_loss"] == pytest.approx(1.0)
    assert paired["candidate_mean_pinball_loss"] == pytest.approx(2.0)
    assert paired["candidate_minus_baseline"] == pytest.approx(1.0)
    assert paired["candidate_minus_baseline_ci"] == pytest.approx([1.0, 1.0])
    assert paired["statistically_significant_worsening"] is True

    verdict = GATE.build_verdict(
        baseline=baseline,
        candidate=candidate,
        oos_rows=[
            {
                "key": baseline_measurement.key,
                "is_money_amount": True,
                "paired": paired,
            }
        ],
        battery_rows=[],
        battery_counts={"left_band": 0},
        participation_rows=[],
        champva_ci={
            "baseline_ratio": 3.72,
            "candidate_ratio": 1.20,
            "baseline_minus_candidate_ci": [2.0, 3.0],
        },
        family_specs=(),
    )

    assert verdict["clauses"]["a_champva"]["passed"] is True
    assert verdict["clauses"]["b_money_oos"] == {
        "passed": False,
        "money_target_count": 1,
        "significantly_worsened_targets": [baseline_measurement.key],
        "worsening_definition": (
            "candidate_minus_baseline paired OOS loss CI lower bound > 0"
        ),
    }
    assert verdict["clauses"]["c_no_battery_leg_leaves_band"]["passed"] is True
    assert verdict["verdict"] == "FAIL"
    assert verdict["passed"] is False
    assert verdict["failing_clauses"] == ["b_money_oos"]


def test_measurement_error_writes_named_fail_closed_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = GATE.GateMeasurementError(
        arm="candidate",
        family_id="early_gap_fill/person/model_required_boolean",
        stage="early_gap_fill",
        entity="person",
        family="model_required_boolean",
        cause=ValueError("OOS target has insufficient donors: train=90, holdout=10."),
    )

    def _fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(GATE, "run_gate", _fail)
    output = tmp_path / "verdict.json"
    report = tmp_path / "report.md"

    return_code = GATE.main(
        [
            "--baseline",
            str(tmp_path / "baseline"),
            "--candidate",
            str(tmp_path / "candidate"),
            "--output",
            str(output),
            "--markdown-output",
            str(report),
        ]
    )

    assert return_code == 1
    payload = json.loads(output.read_text())
    assert payload["verdict"] == "FAIL"
    assert payload["measurement_complete"] is False
    assert payload["failing_clauses"] == ["measurement_integrity"]
    assert payload["clauses"]["measurement_integrity"]["context"] == {
        "arm": "candidate",
        "family_id": "early_gap_fill/person/model_required_boolean",
        "stage": "early_gap_fill",
        "entity": "person",
        "family": "model_required_boolean",
        "cause_type": "ValueError",
        "cause": "OOS target has insufficient donors: train=90, holdout=10.",
    }
    assert "Failing clause: `measurement_integrity`" in report.read_text()


def test_battery_schema_drift_fails_closed(
    tmp_path: Path,
    small_frame: Frame,
) -> None:
    comparisons = _battery_comparisons(
        champva_ratio=3.72,
        other_boolean_ratio=1.0,
        positive_money_ratio=1.0,
        negative_money_ratio=2.0,
    )
    unmatched = _write_artifact(
        tmp_path / "unmatched",
        small_frame,
        identity="unmatched",
        comparisons=comparisons,
        failures=["unknown/leg: synthetic schema drift."],
    )
    with pytest.raises(ValueError, match="did not map exactly once"):
        GATE._battery_legs(unmatched)

    comparisons_with_future_status = _battery_comparisons(
        champva_ratio=3.72,
        other_boolean_ratio=1.0,
        positive_money_ratio=1.0,
        negative_money_ratio=2.0,
    )
    champva = GATE.PHASE_P_CONFIG["verdict"]["champva_leg"]
    comparisons_with_future_status[champva]["status"] = "future_status"
    future_status = _write_artifact(
        tmp_path / "future_status",
        small_frame,
        identity="future-status",
        comparisons=comparisons_with_future_status,
    )
    with pytest.raises(ValueError, match="Unknown battery operational status"):
        GATE._battery_legs(future_status)

    future_status_with_failure = _write_artifact(
        tmp_path / "future_status_with_failure",
        small_frame,
        identity="future-status-with-failure",
        comparisons=comparisons_with_future_status,
        failures=[f"{champva}: synthetic failure."],
    )
    with pytest.raises(ValueError, match="Unknown battery operational status"):
        GATE._battery_legs(future_status_with_failure)

    falsy_leg_status_comparisons = _battery_comparisons(
        champva_ratio=3.72,
        other_boolean_ratio=1.0,
        positive_money_ratio=1.0,
        negative_money_ratio=2.0,
    )
    falsy_leg_status_comparisons["person/earnings/wages[clone_0]"]["legs"]["positive"][
        "status"
    ] = ""
    falsy_leg_status = _write_artifact(
        tmp_path / "falsy_leg_status",
        small_frame,
        identity="falsy-leg-status",
        comparisons=falsy_leg_status_comparisons,
    )
    with pytest.raises(ValueError, match="Unknown battery operational status"):
        GATE._battery_legs(falsy_leg_status)

    for index, malformed_legs in enumerate(([], {})):
        malformed_comparisons = _battery_comparisons(
            champva_ratio=3.72,
            other_boolean_ratio=1.0,
            positive_money_ratio=1.0,
            negative_money_ratio=2.0,
        )
        malformed_comparisons["person/earnings/wages[clone_0]"]["legs"] = malformed_legs
        malformed = _write_artifact(
            tmp_path / f"malformed_legs_{index}",
            small_frame,
            identity=f"malformed-legs-{index}",
            comparisons=malformed_comparisons,
        )
        with pytest.raises(ValueError, match="legs must be a nonempty object"):
            GATE._battery_legs(malformed)


def test_early_oos_surface_replays_raw_person_and_group_investment() -> None:
    frame = _investment_frame()
    person_spec = _early_fixture_spec("person", "person_target")
    group_spec = _early_fixture_spec("spm_unit", "group_target")
    specs = (person_spec, group_spec)
    baseline_evidence = _surface_evidence(specs, include_features=False)
    candidate_evidence = _surface_evidence(specs, include_features=True)

    baseline_person = GATE._phase_p_oos_feature_surface(
        frame,
        spec=person_spec,
        arm="baseline",
        predictor_set=person_spec.baseline_predictor_set,
        execution_evidence=baseline_evidence,
    )
    candidate_person = GATE._phase_p_oos_feature_surface(
        frame,
        spec=person_spec,
        arm="candidate",
        predictor_set=person_spec.candidate_predictor_set,
        execution_evidence=candidate_evidence,
    )
    baseline_group = GATE._phase_p_oos_feature_surface(
        frame,
        spec=group_spec,
        arm="baseline",
        predictor_set=group_spec.baseline_predictor_set,
        execution_evidence=baseline_evidence,
    )
    candidate_group = GATE._phase_p_oos_feature_surface(
        frame,
        spec=group_spec,
        arm="candidate",
        predictor_set=group_spec.candidate_predictor_set,
        execution_evidence=candidate_evidence,
    )

    assert PERSON_INVESTMENT not in baseline_person.features
    assert PERSON_INVESTMENT not in baseline_person.optional
    assert GROUP_INVESTMENT not in baseline_group.features
    assert GROUP_INVESTMENT not in baseline_group.optional
    np.testing.assert_allclose(
        candidate_person.features[PERSON_INVESTMENT],
        np.asarray([6.0, 15.0, np.nan, 33.0]),
        equal_nan=True,
    )
    np.testing.assert_allclose(
        candidate_group.features[GROUP_INVESTMENT],
        np.asarray([21.0, np.nan]),
        equal_nan=True,
    )
    assert candidate_person.features[PERSON_INVESTMENT].iloc[0] != pytest.approx(250.0)
    assert candidate_person.source_bindings["investment_income"] == {
        "feature": PERSON_INVESTMENT,
        "declared_optional": True,
        "oos_donor_source": "complete_numeric_component_sum",
        "raw_components": ["INT_VAL", "DIV_VAL", "RNT_VAL"],
        "group_projection": None,
    }
    assert (
        candidate_group.source_bindings["investment_income"]["oos_donor_source"]
        == "complete_numeric_component_sum_then_group_projection"
    )
    assert candidate_group.source_bindings["investment_income"][
        "group_projection"
    ].endswith("_aggregate_optional_to_group")


def test_early_predictor_evidence_binds_required_and_optional_surface() -> None:
    spec = _early_fixture_spec("person", "person_target")
    evidence = _surface_evidence((spec,), include_features=True)
    key = (spec.family_id, "person_target")
    execution = evidence.targets[key]

    without_age = tuple(
        predictor for predictor in execution.resolved_predictors if predictor != "age"
    )
    missing_required = replace(
        execution,
        pattern_predictors=(without_age,),
        resolved_predictors=without_age,
    )
    with pytest.raises(ValueError, match=r"missing_required=\['age'\]"):
        GATE._validate_early_predictor_evidence(
            arm="candidate",
            family_specs=(spec,),
            executions={key: missing_required},
        )

    with_future = (*execution.resolved_predictors, "__future_predictor")
    undeclared = replace(
        execution,
        pattern_predictors=(with_future,),
        resolved_predictors=with_future,
    )
    with pytest.raises(ValueError, match=r"undeclared=\['__future_predictor'\]"):
        GATE._validate_early_predictor_evidence(
            arm="candidate",
            family_specs=(spec,),
            executions={key: undeclared},
        )

    expanded_predictors = GATE.AcsPredictorSet(
        required=spec.candidate_predictor_set.required,
        optional=(*spec.candidate_predictor_set.optional, "__acs_transfer_tenure_code"),
    )
    expanded_spec = replace(
        spec,
        baseline_predictor_set=expanded_predictors,
        candidate_predictor_set=expanded_predictors,
    )
    with pytest.raises(ValueError, match="resolved predictor union changed"):
        GATE._validate_early_predictor_evidence(
            arm="candidate",
            family_specs=(expanded_spec,),
            executions=evidence.targets,
        )


def test_operational_execution_evidence_validates_person_and_group(
    tmp_path: Path,
) -> None:
    baseline, specs, baseline_role = _write_execution_artifact(
        tmp_path / "baseline",
        arm="baseline",
        person_feature_present=False,
        group_feature_present=False,
    )
    candidate, candidate_specs, candidate_role = _write_execution_artifact(
        tmp_path / "candidate",
        arm="candidate",
        person_feature_present=True,
        group_feature_present=True,
    )

    baseline_evidence = GATE._load_early_execution_evidence(
        baseline,
        arm="baseline",
        family_specs=specs,
        role_binding=baseline_role,
    )
    candidate_evidence = GATE._load_early_execution_evidence(
        candidate,
        arm="candidate",
        family_specs=candidate_specs,
        role_binding=candidate_role,
    )

    assert len(baseline_evidence.targets) == 2
    assert len(candidate_evidence.targets) == 2
    assert all(
        PERSON_INVESTMENT not in execution.resolved_predictors
        and GROUP_INVESTMENT not in execution.resolved_predictors
        for execution in baseline_evidence.targets.values()
    )
    assert {
        predictor
        for execution in candidate_evidence.targets.values()
        for predictor in execution.resolved_predictors
    } >= {PERSON_INVESTMENT, GROUP_INVESTMENT}

    identity = {"artifact_kind": "fixture_bank", "note": "café"}
    unescaped = hashlib.sha256(
        json.dumps(
            identity,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    escaped = hashlib.sha256(
        json.dumps(
            identity,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert (
        candidate_role["early_target_bank_identity_sha256"]["asec_survey_to_acs"]
        == unescaped
    )
    assert unescaped != escaped


@pytest.mark.parametrize(
    ("arm", "person_present", "group_present"),
    [
        ("baseline", True, False),
        ("candidate", True, False),
    ],
)
def test_operational_evidence_fails_closed_on_predictor_drift(
    tmp_path: Path,
    arm: str,
    person_present: bool,
    group_present: bool,
) -> None:
    artifact, specs, role = _write_execution_artifact(
        tmp_path / arm,
        arm=arm,
        person_feature_present=person_present,
        group_feature_present=group_present,
    )

    with pytest.raises(ValueError, match="investment evidence changed"):
        GATE._load_early_execution_evidence(
            artifact,
            arm=arm,
            family_specs=specs,
            role_binding=role,
        )


def test_operational_evidence_rejects_checkpoint_receipt_tampering(
    tmp_path: Path,
) -> None:
    artifact, specs, role = _write_execution_artifact(
        tmp_path / "candidate",
        arm="candidate",
        person_feature_present=True,
        group_feature_present=True,
    )
    sidecar = json.loads(artifact.operational_receipts_path.read_text())
    records = sidecar["operational_stage_receipts"]["impute"]["acs_qrf_transfer"][
        "target_bank"
    ]["directions"]["asec_survey_to_acs"]["targets"]
    records["0"]["checkpoint_sha256"] = "0" * 64
    artifact.operational_receipts_path.write_text(json.dumps(sidecar))

    with pytest.raises(ValueError, match="target checkpoint SHA-256 changed"):
        GATE._load_early_execution_evidence(
            artifact,
            arm="candidate",
            family_specs=specs,
            role_binding=role,
        )


def test_operational_evidence_rejects_bank_root_outside_checkpoint_identity(
    tmp_path: Path,
) -> None:
    artifact, specs, role = _write_execution_artifact(
        tmp_path / "candidate",
        arm="candidate",
        person_feature_present=True,
        group_feature_present=True,
    )
    sidecar = json.loads(artifact.operational_receipts_path.read_text())
    bank = sidecar["operational_stage_receipts"]["impute"]["acs_qrf_transfer"][
        "target_bank"
    ]["directions"]["asec_survey_to_acs"]
    bank["root"] = str((tmp_path / "outside-bank").resolve())
    artifact.operational_receipts_path.write_text(json.dumps(sidecar))

    with pytest.raises(ValueError, match="root escapes the selected checkpoint"):
        GATE._load_early_execution_evidence(
            artifact,
            arm="candidate",
            family_specs=specs,
            role_binding=role,
        )


def test_artifact_role_rejects_incomplete_authority_integrity(
    tmp_path: Path,
) -> None:
    artifact, _specs, role = _write_execution_artifact(
        tmp_path / "baseline",
        arm="baseline",
        person_feature_present=False,
        group_feature_present=False,
    )
    authority = artifact.checkpoint_metadata["external_metadata"]["identity"][
        "stacked_authority"
    ]
    authority["canonical_identity"] = False

    with pytest.raises(ValueError, match="audited stacked authority"):
        GATE._validate_artifact_role(
            artifact,
            arm="baseline",
            role_binding=role,
        )


def test_paired_alignment_requires_identical_unique_stable_id_sets() -> None:
    baseline_positions, candidate_positions = GATE._align_measurements(
        np.asarray(["b", "a"], dtype=object),
        np.asarray(["a", "b"], dtype=object),
    )
    np.testing.assert_array_equal(baseline_positions, [1, 0])
    np.testing.assert_array_equal(candidate_positions, [0, 1])

    with pytest.raises(ValueError, match="stable donor id sets differ"):
        GATE._align_measurements(
            np.asarray(["a", "b"], dtype=object),
            np.asarray(["a", "c"], dtype=object),
        )
    with pytest.raises(ValueError, match="stable donor ids must be unique"):
        GATE._align_measurements(
            np.asarray(["a", "a"], dtype=object),
            np.asarray(["a", "b"], dtype=object),
        )


@pytest.mark.parametrize("bad_metric", [None, "future_metric"])
def test_target_metric_index_rejects_missing_or_unknown_metric(
    tmp_path: Path,
    small_frame: Frame,
    bad_metric: object,
) -> None:
    comparisons = _battery_comparisons(
        champva_ratio=1.0,
        other_boolean_ratio=1.0,
        positive_money_ratio=1.0,
        negative_money_ratio=1.0,
    )
    comparisons["person/earnings/wages[clone_0]"]["metric"] = bad_metric
    artifact = _write_artifact(
        tmp_path / "artifact",
        small_frame,
        identity="metric-fixture",
        comparisons=comparisons,
    )

    with pytest.raises(ValueError, match="has unknown metric"):
        GATE._target_metric_index(artifact)


def test_money_amount_authority_excludes_hours_and_weeks() -> None:
    config = GATE.PHASE_P_CONFIG["money_amount_classification"]
    money = set(config["money_amount_target_keys"])
    numeric_non_money = set(config["generic_numeric_non_money_target_keys"])
    target_metrics = {
        key: "monetary_sign_separated" for key in money | numeric_non_money
    }
    non_numeric_count = config["changed_target_count"] - len(target_metrics)
    target_metrics.update(
        {
            f"fixture/non_numeric/{index}": "boolean_incidence"
            for index in range(non_numeric_count)
        }
    )

    classified = GATE._validated_money_amount_keys(target_metrics)

    assert len(classified) == 74
    assert "gap_fill/asec_housing_to_acs/person/housing/pre_subsidy_rent" in classified
    assert (
        "gap_fill/asec_survey_to_acs/person/model_required_numeric/"
        "unemployment_compensation" in classified
    )
    assert (
        "gap_fill/asec_survey_to_acs/person/model_required_numeric/"
        "hours_worked_last_week" not in classified
    )
    assert (
        "gap_fill/asec_survey_to_acs/person/source_operator_hours_worked/"
        "weekly_hours_worked_before_lsr" not in classified
    )
    assert (
        "late_transfer/transfer:person/source_operator_weeks_unemployed/"
        "weeks_unemployed" not in classified
    )


def test_markdown_reports_clause_a_receipt_and_deduplicates_status(
    tmp_path: Path,
    small_frame: Frame,
) -> None:
    baseline = _write_artifact(
        tmp_path / "baseline",
        small_frame,
        identity="baseline",
        comparisons=_battery_comparisons(
            champva_ratio=3.72,
            other_boolean_ratio=1.0,
            positive_money_ratio=1.0,
            negative_money_ratio=2.0,
        ),
    )
    candidate = _write_artifact(
        tmp_path / "candidate",
        small_frame,
        identity="candidate",
        comparisons=_battery_comparisons(
            champva_ratio=2.0,
            other_boolean_ratio=1.0,
            positive_money_ratio=1.0,
            negative_money_ratio=2.0,
        ),
    )
    battery_rows, battery_counts = GATE.battery_delta(baseline, candidate)
    payload = GATE.build_verdict(
        baseline=baseline,
        candidate=candidate,
        oos_rows=[],
        battery_rows=battery_rows,
        battery_counts=battery_counts,
        participation_rows=GATE.participation_incidence(baseline, candidate),
        champva_ci={
            "baseline_ratio": 3.72,
            "candidate_ratio": 2.0,
            "baseline_minus_candidate_ci": [1.5, 1.9],
        },
        family_specs=(),
    )
    assert payload["clauses"]["a_champva"]["passed"] is True

    ci_includes_zero = GATE.build_verdict(
        baseline=baseline,
        candidate=candidate,
        oos_rows=[],
        battery_rows=battery_rows,
        battery_counts=battery_counts,
        participation_rows=[],
        champva_ci={
            "baseline_ratio": 3.72,
            "candidate_ratio": 2.0,
            "baseline_minus_candidate_ci": [-0.1, 1.9],
        },
        family_specs=(),
    )
    assert ci_includes_zero["clauses"]["a_champva"]["passed"] is False

    below_half_progress = GATE.build_verdict(
        baseline=baseline,
        candidate=candidate,
        oos_rows=[],
        battery_rows=battery_rows,
        battery_counts=battery_counts,
        participation_rows=[],
        champva_ci={
            "baseline_ratio": 3.72,
            "candidate_ratio": 2.6,
            "baseline_minus_candidate_ci": [0.5, 1.5],
        },
        family_specs=(),
    )
    assert below_half_progress["clauses"]["a_champva"]["passed"] is False

    already_in_band = GATE.build_verdict(
        baseline=baseline,
        candidate=candidate,
        oos_rows=[],
        battery_rows=battery_rows,
        battery_counts=battery_counts,
        participation_rows=[],
        champva_ci={
            "baseline_ratio": 1.0,
            "candidate_ratio": 1.0,
            "baseline_minus_candidate_ci": [-0.1, 0.1],
        },
        family_specs=(),
    )
    assert (
        already_in_band["clauses"]["a_champva"][
            "progress_from_baseline_to_band_ceiling"
        ]
        is None
    )
    json.dumps(already_in_band, allow_nan=False)
    assert "toward the band ceiling —" in GATE.render_markdown(already_in_band)

    report = GATE.render_markdown(payload)

    assert "Clause A CHAMPVA receipt: baseline ratio 3.72" in report
    assert "baseline-minus-candidate ratio 95% CI [1.5, 1.9]" in report
    assert "Baseline gate/band" in report
    assert "Baseline gate/receipt/band" not in report
    assert "PASS / tested /" not in report
