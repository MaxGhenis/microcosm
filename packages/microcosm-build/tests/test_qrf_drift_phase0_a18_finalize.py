"""Focused tests for the A18 Phase-0 report assembler."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module():
    path = TOOLS / "qrf_drift_phase0_a18_finalize.py"
    spec = importlib.util.spec_from_file_location("qrf_drift_phase0_a18_finalize", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOLS))
    return module


FINAL = _load_module()


def _dimensions(
    *,
    rung: str = "candidate-25",
    target: str = "example",
    leg: str = "positive",
    row: str,
) -> dict[str, str]:
    return {
        "rung": rung,
        "target": target,
        "pattern": "_",
        "leg": leg,
        "row": row,
        "group": "_",
        "prior": "_",
        "gq": "_",
        "decile": "_",
        "repeat": "_",
        "fold": "_",
        "variant": "_",
    }


def _statistic(
    row: str,
    value: float,
    *,
    se: float | str = 0.01,
    family: str | None = "F1",
    rung: str = "candidate-25",
    target: str = "example",
    leg: str = "positive",
    identifier: str | None = None,
) -> dict[str, Any]:
    return {
        "id": identifier or f"{rung}|{target}|{leg}|{row}",
        "dimensions": _dimensions(
            rung=rung,
            target=target,
            leg=leg,
            row=row,
        ),
        "record_type": "scalar",
        "value": value,
        "se": se,
        "mcse": "NA",
        "family": family,
        "gated": family is not None,
        "status": "PASS",
    }


def _verdict_inputs(
    values: dict[str, float],
    *,
    d_value: float = 1.0,
    endpoint_se: float = 0.01,
) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    rows = {
        name: _statistic(name, values.get(name, 0.0)) for name in FINAL.TOP_LEVEL_ROWS
    }
    rows["D"] = _statistic("D", d_value, family=None)
    rows["J0"] = _statistic("J0", 0.5, se=endpoint_se, family=None)
    rows["I_acs"] = _statistic("I_acs", 0.5 - d_value, se=endpoint_se, family=None)
    return {
        ("candidate-25", "example", "positive", name): row for name, row in rows.items()
    }


def test_step0_manifest_and_historical_c3_ids_remain_sealed() -> None:
    base = json.loads(
        (ROOT / "experiments/qrf_drift_validation_phase0.json").read_text()
    )

    manifest, step0 = FINAL.verify_step0(base)
    ids = {item["id"] for item in manifest}

    assert len(manifest) == FINAL.EXPECTED_MANIFEST_COUNT == 6155
    assert FINAL.digest_object(step0) == FINAL.EXPECTED_STEP0_SHA
    assert set(FINAL.c3_stable_ids()) <= ids
    assert all("t=child_support_received" in item for item in FINAL.c3_stable_ids())


def test_reading_static_override_is_only_for_explicitly_unavailable_rows() -> None:
    spec = {
        "id": "registered",
        "dimensions": _dimensions(row="P2_group_aggregate"),
        "record_type": "scalar",
        "family": "F2",
        "gated": True,
    }
    item = {
        "id": "registered",
        **_dimensions(row="P2_group_aggregate"),
        "record_type": "scalar",
        "family": None,
        "gated": False,
        "status": "NOT_APPLICABLE_CLASS_ABSENT",
    }

    assert FINAL.reading_fields_match(item, spec)
    item["status"] = "PASS"
    assert not FINAL.reading_fields_match(item, spec)


@pytest.mark.parametrize(
    ("producer", "registered"),
    [
        ("VALIDATED", "PASS"),
        ("NOT_VALIDATED_CLOSURE_FAILURE", "NOT_VALIDATED"),
        ("DESCRIPTIVE_VALIDATED_PATTERN", "OK"),
        ("NOT_RUN_NO_TARGET_TRIGGER", "NOT_RUN_NOT_ESCALATED"),
        ("KEEP_R250", "OK"),
        ("UNSUPPORTED_CLASS_LOST", "UNSUPPORTED"),
    ],
)
def test_p2_statuses_map_to_registered_schema(producer: str, registered: str) -> None:
    assert FINAL.normalize_status(producer) == registered


def test_p2_missing_joint_domain_preserves_values_but_not_validation(
    tmp_path: Path,
) -> None:
    base = json.loads(
        (ROOT / "experiments/qrf_drift_validation_phase0.json").read_text()
    )
    manifest = base["step0"]["required_id_manifest"]
    manifest_by_id = {item["id"]: item for item in manifest}
    group_spec = next(
        item
        for item in manifest
        if item["dimensions"]["target"] == "child_support_expense"
        and item["dimensions"]["row"] == "P2_group_pattern"
        and item["dimensions"]["leg"] == "positive"
        and item["dimensions"]["group"] == "G1"
    )
    absent_spec = next(
        item
        for item in manifest
        if item["dimensions"]["target"] == "child_support_expense"
        and item["dimensions"]["row"] == "P2_group_pattern"
        and item["dimensions"]["leg"] == "positive"
        and item["dimensions"]["group"] == "G2"
    )
    insufficient_spec = next(
        item
        for item in manifest
        if item["dimensions"]["target"] == "child_support_expense"
        and item["dimensions"]["row"] == "P2_group_pattern"
        and item["dimensions"]["leg"] == "positive"
        and item["dimensions"]["group"] == "G3"
    )
    domain_spec = next(
        item
        for item in manifest
        if item["dimensions"]["target"] == "child_support_expense"
        and item["dimensions"]["row"] == "P2_marginal_audit"
        and item["dimensions"]["variant"] == "domain_violation_share"
    )
    payload = {
        "artifact_kind": "qrf_drift_phase0_a18_p2",
        "status": "COMPLETE",
        "authority": {"design": {"sha256": FINAL.EXPECTED_AUTHORITY[FINAL.DESIGN]}},
        "targets": [
            {
                "target": "child_support_expense",
                "joint_hybrid_domain": {
                    "status": "UNAVAILABLE_D0_NOT_ENUMERATED",
                    "pattern_invalidation_decision": "NOT_EVALUABLE",
                    "no_predicates_invented": True,
                    "predicates": [],
                },
            }
        ],
        "statistics": [
            {
                "id": group_spec["id"],
                "family": group_spec["family"],
                "gated": group_spec["gated"],
                "value": 0.25,
                "se": "NA",
                "mcse": 0.01,
                "status": "VALIDATED",
            },
            {
                "id": domain_spec["id"],
                "family": domain_spec["family"],
                "gated": domain_spec["gated"],
                "value": 0.0,
                "se": "NA",
                "mcse": "NA",
                "status": "DESCRIPTIVE_NOT_A16_JOINT_GATE",
            },
            {
                "id": absent_spec["id"],
                "family": None,
                "gated": False,
                "value": "NA",
                "se": "NA",
                "mcse": "NA",
                "status": "NOT_APPLICABLE_CLASS_ABSENT",
            },
            {
                "id": insufficient_spec["id"],
                "family": insufficient_spec["family"],
                "gated": insufficient_spec["gated"],
                "value": "NA",
                "se": "NA",
                "mcse": "NA",
                "status": "INSUFFICIENT_SUPPORT_NO_VERDICT",
            },
        ],
    }
    payload["canonical_sha256"] = FINAL.digest_object(payload)
    path = tmp_path / "p2.json"
    path.write_text(json.dumps(payload, sort_keys=True))
    statistics, by_id = FINAL.fresh_statistics(
        manifest,
        "NOT_RUN_PRIORITY",
        {"path": "fallback", "sha256": "0" * 64},
    )

    FINAL.merge_statistics_artifact(path, manifest_by_id, by_id, set())

    group = by_id[group_spec["id"]]
    domain = by_id[domain_spec["id"]]
    absent = by_id[absent_spec["id"]]
    insufficient = by_id[insufficient_spec["id"]]
    assert group["value"] == 0.25
    assert group["status"] == "NOT_VALIDATED"
    assert domain["value"] == "NA"
    assert domain["status"] == "UNAVAILABLE"
    assert domain["sources"][-1]["producer_value"] == 0.0
    assert absent["status"] == "NOT_APPLICABLE"
    assert insufficient["status"] == "INSUFFICIENT_SUPPORT_NO_VERDICT"
    assert len(statistics) == FINAL.EXPECTED_MANIFEST_COUNT


def test_holm_zero_uncertainty_rules_are_exact() -> None:
    rows = [
        _statistic("zero", 0.0, se=0.0),
        _statistic("nonzero", -0.25, se=0.0),
    ]

    loading = FINAL.holm_loaded(rows)

    assert loading["candidate-25|example|positive|zero"] == {
        "p": 1.0,
        "z_abs": 0.0,
        "holm_significant": False,
        "three_se": True,
        "loaded": False,
        "uncertainty": 0.0,
    }
    assert loading["candidate-25|example|positive|nonzero"]["p"] == 0.0
    assert loading["candidate-25|example|positive|nonzero"]["z_abs"] == "inf"
    assert loading["candidate-25|example|positive|nonzero"]["loaded"] is True


def test_holm_excludes_not_validated_and_unsupported_rows() -> None:
    valid = _statistic("valid", 0.31, se=0.01, identifier="valid")
    not_validated = _statistic("invalid", 100.0, se=0.01, identifier="not-validated")
    not_validated["status"] = "NOT_VALIDATED"
    unsupported = _statistic("unsupported", 100.0, se=0.01, identifier="unsupported")
    unsupported["status"] = "UNSUPPORTED"

    loading = FINAL.holm_loaded([valid, not_validated, unsupported])

    assert set(loading) == {"valid"}
    assert loading["valid"]["loaded"] is True


def test_family_loading_excludes_other_rungs_and_diagnostic_rows() -> None:
    candidate = _statistic("T3", 3.01, se=1.0, identifier="candidate")
    other_rung = [
        _statistic(
            f"noise-{index}",
            0.0,
            se=1.0,
            rung="baseline1pct",
            identifier=f"baseline-{index}",
        )
        for index in range(30)
    ]
    residual = _statistic("residual", 100.0, se=0.01, identifier="residual")
    fold = _statistic("C1_fold_gap", 100.0, se=0.01, family="F5", identifier="fold")

    loading = FINAL.family_loading([candidate, residual, fold, *other_rung])

    assert loading["candidate"]["loaded"] is True
    assert "residual" not in loading
    assert "fold" not in loading


def test_family_loading_uses_one_global_f4_gq_adjustment_family() -> None:
    rows = []
    for index, (target, leg, gq, value) in enumerate(
        (
            ("one", "positive", "2", 4.0),
            ("one", "positive", "3", 0.0),
            ("two", "negative", "2", 0.0),
            ("two", "negative", "3", 0.0),
        )
    ):
        row = _statistic(
            "P7_GQ",
            value,
            se=1.0,
            family="F4",
            target=target,
            leg=leg,
            identifier=f"f4-{index}",
        )
        row["dimensions"]["gq"] = gq
        row["dimensions"]["variant"] = "adjustment"
        rows.append(row)
    nonadjustment = _statistic(
        "P7_GQ", 100.0, se=0.01, family="F4", identifier="not-adjustment"
    )
    nonadjustment["dimensions"]["gq"] = "H"
    nonadjustment["dimensions"]["variant"] = "incidence"

    loading = FINAL.family_loading([*rows, nonadjustment])

    assert set(loading) == {f"f4-{index}" for index in range(4)}
    assert loading["f4-0"]["holm_significant"] is True
    assert loading["f4-0"]["loaded"] is True
    assert "not-adjustment" not in loading


def test_verdict_no_material_rule_is_terminal_but_reports_shares() -> None:
    rows = _verdict_inputs(
        {"T3": 0.8, "B1": 0.2},
        d_value=0.01,
        endpoint_se=0.01,
    )
    t3 = rows[("candidate-25", "example", "positive", "T3")]

    verdict = FINAL.verdict_for_leg(
        "example",
        "positive",
        rows,
        {t3["id"]: {"loaded": True}},
        "SUPPORTED",
    )

    assert verdict["verdict"] == "no material gap"
    assert verdict["dominant_row"] == "NA"
    assert verdict["shares"]["T3"] == pytest.approx(0.8)
    assert verdict["arm_D_flag"] == "NO_D_NO_MATERIAL_GAP"


def test_a16_cumulative_defect_and_unresolved_gating() -> None:
    rows = _verdict_inputs(
        {
            "B1": 0.30,
            "T3": 0.30,
            "L0": 0.10,
            "B2": 0.10,
            "T1": 0.05,
            "T2": 0.05,
            "T4": 0.05,
            "T5": 0.05,
        }
    )
    loading = {
        rows[("candidate-25", "example", "positive", name)]["id"]: {
            "loaded": name in {"B1", "T3"}
        }
        for name in FINAL.TOP_LEVEL_ROWS
    }

    verdict = FINAL.verdict_for_leg("example", "positive", rows, loading, "SUPPORTED")

    assert verdict["verdict"] == "mixture / no dominant cause"
    assert verdict["qualifying_parents"] == ["B1", "T3"]
    assert verdict["primary_parent"] == "B1"
    assert verdict["defect_class"] == "DEFECT+UNRESOLVED"
    assert verdict["arm_C_flag"] == "BLOCK_C_DEFECT"
    assert verdict["arm_D_flag"] == "CREATE_D"
    assert verdict["arm_B_validation_flag"] == "BLOCK_B_VALIDATION_DEFECT"


def test_named_bridge_pair_requires_both_rows_loaded() -> None:
    rows = _verdict_inputs({"B1": 0.31, "B2": 0.31, "T1": 0.19, "T2": 0.19})
    b1 = rows[("candidate-25", "example", "positive", "B1")]
    b2 = rows[("candidate-25", "example", "positive", "B2")]

    both = FINAL.verdict_for_leg(
        "example",
        "positive",
        rows,
        {b1["id"]: {"loaded": True}, b2["id"]: {"loaded": True}},
        "SUPPORTED",
    )
    one = FINAL.verdict_for_leg(
        "example",
        "positive",
        rows,
        {b1["id"]: {"loaded": True}, b2["id"]: {"loaded": False}},
        "SUPPORTED",
    )

    assert both["dominant_row"] == "B1+B2"
    assert both["dominant_share"] == pytest.approx(0.62)
    assert one["dominant_row"] == "mixture"


def test_readings_barrier_accepts_declared_p5_priority_disposition() -> None:
    payload = {
        "artifact_kind": "qrf_drift_phase0_readings_prerequisite",
        "authority": {
            "commit_design_blob_sha256": FINAL.EXPECTED_AUTHORITY[FINAL.DESIGN]
        },
        "status": "COMPLETE_WITH_DECLARED_PRIORITY_OMISSIONS",
        "readings_complete": True,
        "completed_readings": {
            "P0": "COMPLETE",
            "P1": "COMPLETE",
            "P2": "COMPLETE",
            "P5": "NOT_RUN_PRIORITY_RULE",
            "P6": "DISPOSITION_RECORDED",
            "P7": "COMPLETE",
        },
        "next_phase": "C1",
    }

    dispositions = FINAL.verify_readings_barrier(payload)

    assert dispositions["P5"] == "NOT_RUN_PRIORITY_RULE"


def test_support_counts_use_clone0_roster() -> None:
    d0 = json.loads(FINAL.D0_JSON.read_text())
    source = {"path": str(FINAL.D0_JSON), "sha256": "0" * 64}

    support = FINAL.support_by_target(
        d0,
        ["self_employment_income_last_year", "pre_subsidy_care_expenses"],
        source,
    )

    seily_negative = support["self_employment_income_last_year"]["negative"]
    care_positive = support["pre_subsidy_care_expenses"]["positive"]
    assert seily_negative == {
        "asec": 48,
        "acs": 2398,
        "status": "INSUFFICIENT_SUPPORT_NO_VERDICT",
        "sources": [source],
    }
    assert care_positive["asec"] == 80
    assert care_positive["acs"] == 735
    assert care_positive["status"] == "SUPPORTED"


def test_p6_special_bridges_preserve_nested_leg_incidence() -> None:
    base = json.loads(
        (ROOT / "experiments/qrf_drift_validation_phase0.json").read_text()
    )
    manifest = base["step0"]["required_id_manifest"]
    manifest_by_id = {item["id"]: item for item in manifest}
    statistics, by_id = FINAL.fresh_statistics(
        manifest,
        "NOT_RUN_PRIORITY",
        {"path": "fallback", "sha256": "0" * 64},
    )
    locked: set[str] = set()
    p6 = {
        "boundary_bridge": {
            "status": "AVAILABLE",
            "boundary_mask": {"sha256": "a" * 64},
            "legs": {
                "positive": {"value": 0.125},
                "negative": {"value": -0.25},
            },
        },
        "clone_value_and_weight_bridge": {
            "status": "AVAILABLE",
            "source_id_identity": {"sha256": "b" * 64},
            "legs": {
                "positive": {"clone_weight_bridge": 0.375},
                "negative": {"clone_weight_bridge": -0.5},
            },
        },
    }

    FINAL.merge_p6_nested(
        p6,
        "child_support_expense",
        "/candidate-25/targets/child_support_expense",
        Path("p1.json"),
        {"sha256": "c" * 64},
        manifest,
        manifest_by_id,
        by_id,
        locked,
    )

    def row(stage: str, leg: str, variant: str) -> dict[str, Any]:
        identifier = FINAL.dimension_id(
            manifest,
            rung="candidate-25",
            target="child_support_expense",
            leg=leg,
            row=f"P6_{stage}",
            variant=variant,
        )
        return by_id[identifier]

    assert row("boundary_bridge", "positive", "incidence")["value"] == 0.125
    assert row("boundary_bridge", "negative", "incidence")["value"] == -0.25
    assert row("clone_weight_bridge", "positive", "incidence")["value"] == 0.375
    assert row("clone_weight_bridge", "negative", "incidence")["value"] == -0.5
    assert row("boundary_bridge", "positive", "mask_sha256")["value"] == "a" * 64
    assert row("clone_weight_bridge", "positive", "mask_sha256")["value"] == "b" * 64
    assert all(
        row(stage, leg, "incidence")["status"] == "OK"
        for stage in ("boundary_bridge", "clone_weight_bridge")
        for leg in FINAL.LEGS
    )
    assert len(statistics) == FINAL.EXPECTED_MANIFEST_COUNT


def test_readings_barrier_binds_exact_supplied_artifacts() -> None:
    targets = list(json.loads(FINAL.D0_JSON.read_text())["scope"]["targets"])

    def source(name: str) -> dict[str, Any]:
        character = name[0]
        return {
            "path": f"/tmp/{name}.json",
            "sha256": character * 64,
            "self_excluding_sha256": character.upper() * 64,
        }

    p1 = {
        "artifact_kind": "qrf_drift_phase0_p0_p1_p6_p7",
        "status": "COMPLETE",
        "candidate-25": {"targets": dict.fromkeys(targets, {})},
    }
    p2 = {
        "artifact_kind": "qrf_drift_phase0_a18_p2",
        "status": "COMPLETE",
        "targets": [{"target": target} for target in targets],
    }
    baseline = {
        "artifact_kind": "qrf_drift_phase0_baseline_crossrung_p0_p1",
        "status": "COMPLETE",
        "baseline1pct": {
            "targets": dict.fromkeys(
                (
                    "self_employment_income_last_year",
                    "spm_unit_energy_subsidy",
                ),
                {},
            )
        },
    }
    scopes = [targets[:4], *([target] for target in targets[4:])]
    p5 = [
        {
            "artifact_kind": "qrf_drift_phase0_a18_p5",
            "status": "COMPLETE_TARGET_SUBSET",
            "scope": {"targets": scope},
        }
        for scope in scopes
    ]
    payloads = [
        (p1, source("p1")),
        (p2, source("p2")),
        (baseline, source("baseline")),
        *((payload, source(f"s{index}")) for index, payload in enumerate(p5)),
    ]
    barrier = {
        "completed_readings": {
            "P0": "COMPLETE",
            "P1": "COMPLETE",
            "P2": "NOT_VALIDATED",
            "P5": "COMPLETE",
            "P6": "COMPLETE_WITH_NO_SURFACE",
            "P7": "COMPLETE",
        },
        "artifacts": {
            "P1": FINAL.artifact_binding_record(*payloads[0]),
            "P2": FINAL.artifact_binding_record(*payloads[1]),
            "baseline_crossrung": FINAL.artifact_binding_record(*payloads[2]),
            "P5": [
                FINAL.artifact_binding_record(payload, artifact_source)
                for payload, artifact_source in payloads[3:]
            ],
        },
    }

    FINAL.verify_barrier_artifact_bindings(barrier, payloads)

    changed = json.loads(json.dumps(barrier))
    changed["artifacts"]["P2"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="P2 binding differs"):
        FINAL.verify_barrier_artifact_bindings(changed, payloads)


def test_c1_must_bind_the_exact_live_readings_barrier(tmp_path: Path) -> None:
    path = tmp_path / "readings-barrier.json"
    path.write_text("sealed readings barrier")
    barrier_source = {
        "path": str(path.resolve()),
        "sha256": FINAL.sha256_file(path),
        "self_excluding_sha256": "a" * 64,
    }
    payload = {
        "scope": {"runs_after_readings": True},
        "prerequisites": {
            "readings": {
                **barrier_source,
                "completed_readings": ["P0", "P1", "P2", "P5", "P6", "P7"],
            }
        },
    }

    FINAL.verify_c1_phase_order(payload, barrier_source)

    payload["prerequisites"]["readings"]["self_excluding_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="supplied sealed readings barrier"):
        FINAL.verify_c1_phase_order(payload, barrier_source)


def test_required_highlights_report_care_extension_and_weeks_components() -> None:
    p1_payload = {
        "candidate-25": {
            "targets": {
                "pre_subsidy_care_expenses": {
                    "status": "COMPLETE",
                    "P1": {
                        "structural": {
                            "cleared_positive_rows": 3788,
                            "cleared_mask": {"sha256": "a" * 64},
                        },
                        "ledger": {
                            "positive": {"rows": {"T5": {"value": 0.4, "se": 0.04}}}
                        },
                    },
                },
                "weeks_unemployed": {
                    "status": "COMPLETE",
                    "P1": {
                        "levels": {"positive": {"D": {"value": 2.0, "se": 0.2}}},
                        "ledger": {
                            "positive": {
                                "rows": {
                                    "B1": {"value": 0.5, "se": 0.05},
                                    "T5": {"value": 0.4, "se": 0.04},
                                    "T2": {"value": -0.1, "se": 0.01},
                                }
                            }
                        },
                    },
                },
            }
        }
    }
    highlights = FINAL.build_required_highlights(
        (
            p1_payload,
            {
                "path": "/tmp/p1.json",
                "sha256": "b" * 64,
                "self_excluding_sha256": "c" * 64,
            },
        ),
        {"path": "/tmp/d0.json", "sha256": "d" * 64},
    )

    care = highlights["pre_subsidy_care_expenses"]
    weeks = highlights["weeks_unemployed"]
    assert care["baseline1pct_D0_4_cleared_positive_draws"] == 183
    assert care["candidate_25_cleared_positive_draws"] == 3788
    assert care["additional_cleared_draws"] == 3605
    assert care["T5"]["value"] == 0.4
    assert care["T5"]["se"] == 0.04
    assert any(
        source.get("pointer") == "/build_required_highlights"
        for source in care["T5"]["sources"]
    )
    assert weeks["B1"]["share_of_signed_D"] == 0.25
    assert weeks["T5"]["share_of_signed_D"] == 0.2
    assert weeks["T2"]["share_of_signed_D"] == -0.05
    assert all(
        item["sources"] for item in (care, weeks, weeks["B1"], weeks["T5"], weeks["T2"])
    )
    assert any(
        source.get("pointer") == "/build_required_highlights"
        for source in weeks["B1"]["sources"]
    )


def test_authoritative_baseline_crossrung_fills_exact_registered_roster(
    tmp_path: Path,
) -> None:
    def reading(target: str) -> dict[str, Any]:
        levels = {name: {"value": 0.0, "se": 0.01} for name in FINAL.LEVEL_ROWS}
        levels["I_o"] = {
            "value": "NA",
            "se": "NA",
            "empty_set": True,
        }
        ledger = {name: {"value": 0.0, "se": 0.01} for name in FINAL.TOP_LEVEL_ROWS}
        ledger["residual"] = {
            "value": 0.0,
            "se": "NA",
            "passes": True,
        }
        return {
            "status": "COMPLETE",
            "target": target,
            "leg": "positive",
            "support": {"status": "SUPPORTED"},
            "P0": {"phi": 1.0, "bindings": {"all": True}},
            "levels": levels,
            "ledger": ledger,
            "D0_incidence_binding": {
                "J0_bit_exact": True,
                "I_acs_bit_exact": True,
            },
        }

    payload = {
        "artifact_kind": "qrf_drift_phase0_baseline_crossrung_p0_p1",
        "schema_version": 1,
        "status": "COMPLETE",
        "rung": "baseline1pct",
        "authority": {
            "design": {"sha256": FINAL.EXPECTED_AUTHORITY[FINAL.DESIGN]},
            "D0": {"sha256": FINAL.EXPECTED_AUTHORITY[FINAL.D0_JSON]},
            "A16_binding": {"sha256": FINAL.EXPECTED_AUTHORITY[FINAL.BINDING]},
            "input_verification": {
                "status": "PASS",
                "all_inputs_live_hashed": True,
                "files": [],
            },
            "sealed_step0_operator_source": {
                "status": "PASS",
                "operator_table_sha256": FINAL.EXPECTED_STEP0_SEALS[
                    "operator_table_sha256"
                ],
            },
        },
        "baseline1pct": {
            "targets": {
                target: reading(target)
                for target in (
                    "self_employment_income_last_year",
                    "spm_unit_energy_subsidy",
                )
            }
        },
        "unavailable_targets": {},
        "execution": {"authoritative": True, "elapsed_seconds": 1.0},
    }
    payload["content_sha256"] = FINAL.compact_digest(
        {
            key: value
            for key, value in payload.items()
            if key not in {"execution", "content_sha256"}
        }
    )
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload, sort_keys=True))
    base = json.loads(
        (ROOT / "experiments/qrf_drift_validation_phase0.json").read_text()
    )
    manifest = base["step0"]["required_id_manifest"]
    manifest_by_id = {item["id"]: item for item in manifest}
    statistics, by_id = FINAL.fresh_statistics(
        manifest,
        "NOT_RUN_PRIORITY",
        {"path": "fallback", "sha256": "0" * 64},
    )
    locked: set[str] = set()

    merged, source = FINAL.merge_baseline_crossrung_artifact(
        path, manifest, manifest_by_id, by_id, locked
    )

    assert merged["content_sha256"] == payload["content_sha256"]
    assert source["scientific_content_sha256"] == payload["content_sha256"]
    baseline_ids = {
        row["id"]
        for row in statistics
        if row["dimensions"]["rung"] == "baseline1pct"
        and row["dimensions"]["target"] in merged["baseline1pct"]["targets"]
        and row["dimensions"]["row"] != "C0a_incidence"
    }
    assert len(baseline_ids) == 42
    assert baseline_ids <= locked
    assert {
        row["status"]
        for row in statistics
        if row["id"] in baseline_ids and row["dimensions"]["row"] == "I_o"
    } == {"NOT_APPLICABLE"}


def test_repeated_p5_shards_must_union_to_all_558_cells(tmp_path: Path) -> None:
    base = json.loads(
        (ROOT / "experiments/qrf_drift_validation_phase0.json").read_text()
    )
    manifest = base["step0"]["required_id_manifest"]
    manifest_by_id = {item["id"]: item for item in manifest}
    p5_specs = [
        item for item in manifest if item["dimensions"]["row"].startswith("P5_")
    ]
    targets = list(dict.fromkeys(item["dimensions"]["target"] for item in p5_specs))
    assert len(p5_specs) == 558

    paths: list[Path] = []
    for index, shard_targets in enumerate((targets[:4], targets[4:])):
        statistics = [
            {
                "id": spec["id"],
                "record_type": spec["record_type"],
                "family": spec["family"],
                "gated": spec["gated"],
                "value": "NA",
                "se": "NA",
                "mcse": "NA",
                "status": "NOT_APPLICABLE",
            }
            for spec in p5_specs
            if spec["dimensions"]["target"] in shard_targets
        ]
        payload = {
            "artifact_kind": "qrf_drift_phase0_a18_p5",
            "schema_version": 1,
            "status": "COMPLETE_TARGET_SUBSET",
            "authority": {"design": {"sha256": FINAL.EXPECTED_AUTHORITY[FINAL.DESIGN]}},
            "scope": {"targets": shard_targets},
            "statistics": statistics,
        }
        payload["canonical_sha256"] = FINAL.digest_object(payload)
        path = tmp_path / f"p5-{index}.json"
        path.write_text(json.dumps(payload, sort_keys=True))
        paths.append(path)

    statistics, by_id = FINAL.fresh_statistics(
        manifest,
        "NOT_RUN_PRIORITY",
        {"path": "fallback", "sha256": "0" * 64},
    )
    locked: set[str] = set()

    artifacts = FINAL.merge_p5_artifacts(paths, manifest_by_id, by_id, locked)

    assert len(artifacts) == 2
    assert (
        len(
            {
                row["id"]
                for row in statistics
                if row["dimensions"]["row"].startswith("P5_") and row["id"] in locked
            }
        )
        == 558
    )


def test_target_sections_provenance_shares_and_empty_c1_disposition() -> None:
    producer_source = {"path": "/tmp/producer.json", "sha256": "a" * 64}
    verdict_source = {
        "path": str(Path(FINAL.__file__).resolve()),
        "sha256": FINAL.sha256_file(Path(FINAL.__file__)),
        "pointer": "/verdict_for_leg",
    }
    statistics: list[dict[str, Any]] = []
    for leg in FINAL.LEGS:
        for name in (*FINAL.LEVEL_ROWS, *FINAL.TOP_LEVEL_ROWS, "residual"):
            row = _statistic(
                name,
                0.0,
                family="F1" if name in FINAL.TOP_LEVEL_ROWS else None,
                leg=leg,
            )
            row["sources"] = [producer_source]
            statistics.append(row)
    positive_c1 = _statistic(
        "C1_target_gap",
        0.0,
        family="F5",
        leg="positive",
        identifier="positive-c1",
    )
    positive_c1["sources"] = [producer_source]
    statistics.append(positive_c1)
    verdicts = [
        {
            "target": "example",
            "leg": leg,
            "shares": {name: 0.125 for name in FINAL.TOP_LEVEL_ROWS},
            "sources": [verdict_source],
        }
        for leg in FINAL.LEGS
    ]

    sections = FINAL.build_target_sections(statistics, ["example"], verdicts)

    positive = sections["example"]["legs"]["positive"]
    negative = sections["example"]["legs"]["negative"]
    assert positive["probes"]["C1"]["status"] == "COMPLETE"
    assert negative["probes"]["C1"]["status"] == "NOT_APPLICABLE"
    assert "class is absent" in negative["probes"]["C1"]["reason"]
    assert negative["probes"]["C1"]["status_counts"] == {}
    assert any(
        source.get("pointer") == "/build_target_sections"
        for source in negative["probes"]["C1"]["sources"]
    )
    t1 = next(row for row in positive["ledger"] if row["dimensions"]["row"] == "T1")
    assert t1["additive_share"]["value"] == 0.125
    assert t1["additive_share"]["sources"] == [verdict_source]
    assert any(
        source.get("pointer") == "/build_target_sections"
        for source in t1["holm_loading"]["sources"]
    )


def test_renderers_show_all_row_shares_phi_legs_and_full_p0_census() -> None:
    source = {"path": "/tmp/p1.json", "sha256": "b" * 64}
    lookup = {(source["path"], source["sha256"]): "S1"}
    ledger = []
    for name in FINAL.TOP_LEVEL_ROWS:
        row = _statistic(name, 1.0)
        row["mcse"] = "NA"
        row["sources"] = [source]
        row["additive_share"] = {"value": 0.125, "sources": [source]}
        row["holm_loading"] = {"loaded": True, "sources": [source]}
        ledger.append(row)
    rendered_ledger = FINAL.render_ledger_rows(ledger, lookup)
    assert rendered_ledger.count("| 0.125 |") == len(FINAL.TOP_LEVEL_ROWS)

    phi_rows = []
    for leg in FINAL.LEGS:
        row = _statistic("phi", 1.0, family=None, leg=leg)
        row["mcse"] = "NA"
        row["sources"] = [source]
        phi_rows.append(row)
    rendered_phi = FINAL.render_stat_rows(
        phi_rows,
        lookup,
        include_dimensions=True,
        include_leg=True,
    )
    assert "phi/leg=positive" in rendered_phi
    assert "phi/leg=negative" in rendered_phi

    path_row = _statistic("P0_path_census", 10.0, family=None, leg="_")
    path_row["mcse"] = "NA"
    path_row["sources"] = [
        {
            **source,
            "path_census": {
                "stage_pass_rows": {
                    "authorized": 10,
                    "null_before": 9,
                    "drawn": 8,
                    "finite_decode": 7,
                },
                "first_failure_rows": {
                    "authorized": 1,
                    "null_before": 1,
                    "drawn": 1,
                    "finite_decode": 1,
                },
                "first_failure_masks": {
                    name: {"sha256": character * 64}
                    for name, character in zip(
                        ("authorized", "null_before", "drawn", "finite_decode"),
                        "cdef",
                        strict=True,
                    )
                },
                "passed_rows": 6,
                "passed_mask": {"sha256": "9" * 64},
            },
        }
    ]
    census = FINAL.render_p0_path_census([path_row], lookup)
    assert "| authorized | 10 | 1 |" in census
    assert "| finite_decode | 7 | 1 |" in census
    assert f"| passed_all | 6 | NA | {'9' * 64} | S1 |" in census


def test_markdown_orders_controls_targets_summary_and_p8() -> None:
    result = {
        "status": "PARTIAL",
        "status_line": "STATUS: PARTIAL (test)",
        "source_catalog": [
            {
                "label": "S-D0",
                "path": str(FINAL.D0_MARKDOWN),
                "sha256": FINAL.EXPECTED_AUTHORITY[FINAL.D0_MARKDOWN],
            }
        ],
        "controls": {
            "adopted": {"C0a": {"status": "PASS"}},
            "sources": {
                "C0a": "S1",
                "base": "S0",
                "adoption": "S1",
                "enumeration": "S2",
                "C3": "S3",
            },
            "A18_branch2": {
                "selected": {
                    "target": "pre_subsidy_care_expenses",
                    "pattern": "pattern_03_76a0101a",
                    "G3_column": "is_incapable_of_self_care",
                    "split_count": 1,
                    "total_split_gain": 1.0,
                }
            },
            "G3_split_enumeration": {"rows": []},
            "C3": {"status": "PASS", "power": {}},
        },
        "statistics": [],
        "step0": {"seals": FINAL.EXPECTED_STEP0_SEALS},
        "targets": {},
        "cross_target_summary": [],
        "cross_rung_summary": [],
        "P8_ssi": {
            "note": "SSI direct-input note.",
            "status": "OK",
            "source": {"path": "d0.json", "sha256": "0" * 64},
        },
        "partial_reasons": ["test priority disposition"],
        "reading_dispositions": {},
        "required_highlights": {},
        "a16_binding_appendix": {"text": "binding"},
    }

    markdown = FINAL.render_markdown(result)

    assert markdown.startswith("STATUS: PARTIAL")
    assert markdown.index("## Control results") < markdown.index(
        "## Per-target results"
    )
    assert markdown.index("## Per-target results") < markdown.index(
        "## Cross-target summary"
    )
    assert markdown.index("## Cross-target summary") < markdown.index(
        "## P8 — SSI dependency note"
    )
    assert set(FINAL.SSI_DIRECT_INPUTS).isdisjoint(FINAL.SSI_NOT_DIRECT_INPUTS)
