"""Contract tests for the Phase-P predictor-set OOS acceptance gate."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from microcosm.build.frame_checkpoint import write_frame_checkpoint
from microcosm.frame import Frame

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
