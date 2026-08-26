"""Focused tests for the fail-closed A18 branch-2 adoption verifier."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module():
    path = TOOLS / "qrf_drift_phase0_a18_adopt.py"
    spec = importlib.util.spec_from_file_location(
        "qrf_drift_phase0_a18_adopt",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOLS))
    return module


ADOPT = _load_module()


def test_canonical_evidence_digest_is_recomputed() -> None:
    value = {"artifact_kind": "fixture", "status": "SEALED"}
    digest = ADOPT.canonical_sha256(value)
    value["canonical_sha256"] = digest

    assert (
        ADOPT.verify_canonical_payload(
            value,
            expected_kind="fixture",
            expected_digest=digest,
        )
        == digest
    )

    value["status"] = "MUTATED"
    with pytest.raises(ValueError, match="payload has changed"):
        ADOPT.verify_canonical_payload(
            value,
            expected_kind="fixture",
            expected_digest=digest,
        )


def _branch2_fixture():
    rows = [
        {
            "stable_order": {"triple": 0},
            "target": "zero",
            "pattern": "p0",
            "G3_column": "unused",
            "split_count": 0,
            "total_split_gain": 0.0,
            "total_split_gain_hex": 0.0.hex(),
        },
        {
            "stable_order": {"triple": 1},
            "target": "selected",
            "pattern": "p1",
            "G3_column": "prior",
            "split_count": 2,
            "total_split_gain": 9.0,
            "total_split_gain_hex": 9.0.hex(),
        },
    ]
    table_rows = [{"table_order": 0, **rows[1]}]
    definition = {"row_predicate": "split_count >= 1"}
    all_sha = ADOPT.canonical_sha256(rows)
    table_sha = ADOPT.canonical_sha256(
        {"definition": definition, "rows": table_rows}
    )
    selected = {
        "table_order": 0,
        "target": "selected",
        "pattern": "p1",
        "G3_column": "prior",
        "split_count": 2,
        "total_split_gain": 9.0,
        "total_split_gain_hex": 9.0.hex(),
        "row_sha256": ADOPT.canonical_sha256(table_rows[0]),
    }
    value = {
        "scope": {"readings_computed": False, "target_count": 9, "gate_count": 36},
        "all_G3_triples": {"rows": rows, "row_count": 2, "sha256": all_sha},
        "sealed_split_table": {
            "definition": definition,
            "rows": table_rows,
            "row_count": 1,
            "sha256": table_sha,
        },
        "mechanical_disposition": {
            "branch": 2,
            "action": "RETARGET_C3_TO_LARGEST_GAIN_TRIPLE",
            "selected": selected,
        },
    }
    return value, all_sha, table_sha, selected


def test_branch2_recomputes_table_and_selected_row_seals() -> None:
    value, all_sha, table_sha, selected = _branch2_fixture()

    result = ADOPT.verify_branch2(
        value,
        expected_table_count=1,
        expected_table_sha=table_sha,
        expected_all_count=2,
        expected_all_sha=all_sha,
        expected_selected=selected,
    )

    assert result["branch"] == 2
    assert result["selected"] == selected

    value["mechanical_disposition"]["selected"] = {
        **selected,
        "target": "wrong",
    }
    with pytest.raises(ValueError, match="recorded selection"):
        ADOPT.verify_branch2(
            value,
            expected_table_count=1,
            expected_table_sha=table_sha,
            expected_all_count=2,
            expected_all_sha=all_sha,
            expected_selected=selected,
        )


def test_step0_recomputes_all_six_seals_and_exact_manifest() -> None:
    manifest = [
        {
            "id": "one",
            "dimensions": {"row": "fixture"},
            "record_type": "scalar",
            "family": None,
            "gated": False,
        }
    ]
    step0 = {
        "operator_table": [{"name": "operator"}],
        "json_schema": {"type": "object"},
        "required_id_manifest": manifest,
        "adjudication_table": [],
        "default_appendix": [],
        "sealed_before_fresh_statistics": True,
    }
    seals = {
        "operator_table_sha256": ADOPT.canonical_sha256(step0["operator_table"]),
        "json_schema_sha256": ADOPT.canonical_sha256(step0["json_schema"]),
        "required_id_manifest_sha256": ADOPT.canonical_sha256(manifest),
        "adjudication_table_sha256": ADOPT.canonical_sha256([]),
        "default_appendix_sha256": ADOPT.canonical_sha256([]),
    }
    seals["composite_sha256"] = ADOPT.canonical_sha256(
        {
            "operator_table": step0["operator_table"],
            "json_schema": step0["json_schema"],
            "required_id_manifest": manifest,
            "adjudication_table": [],
            "default_appendix": [],
        }
    )
    step0["seals"] = seals
    phase0 = {
        "step0": step0,
        "statistics": [
            {
                **manifest[0],
                "value": "NA",
                "status": "SEALED_NOT_COMPUTED",
            }
        ],
    }
    step0_sha = ADOPT.canonical_sha256(step0)

    verified, summary = ADOPT.verify_step0(
        phase0,
        expected_seals=seals,
        expected_count=1,
        expected_step0_sha=step0_sha,
    )

    assert verified == manifest
    assert summary["manifest_count"] == 1
    phase0["statistics"] = []
    with pytest.raises(ValueError, match="statistic count"):
        ADOPT.verify_step0(
            phase0,
            expected_seals=seals,
            expected_count=1,
            expected_step0_sha=step0_sha,
        )


def test_branch2_preserves_three_c3_ids_but_excludes_old_c3() -> None:
    manifest = []
    for group in ("G1", "G2", "G3"):
        manifest.append(
            {
                "id": f"stable-{group}",
                "dimensions": {"row": "C3_oracle_error", "group": group},
            }
        )
    selected = {
        "target": "new-target",
        "pattern": "new-pattern",
        "G3_column": "new-prior",
        "row_sha256": "a" * 64,
    }
    slots = ADOPT.retarget_c3_slots(
        manifest,
        selected,
        expected_ids=["stable-G1", "stable-G2", "stable-G3"],
    )
    assert slots["stable_ids_preserved"] == ["stable-G1", "stable-G2", "stable-G3"]
    assert slots["id_mutations"] == 0
    assert all(
        slot["retargeted_context"]["target"] == "new-target"
        for slot in slots["slots"]
    )

    disposition = ADOPT.branch2_control_disposition(
        {
            "controls": {
                "C2": {
                    "status": "PASS",
                    "pass": True,
                    "power": {"pass": True},
                },
                "C3": {
                    "status": "UNDERPOWERED",
                    "pass": False,
                    "power": {"pass": False, "absolute_oracle": 0},
                },
            }
        }
    )
    assert set(disposition["adopted"]) == {"C2"}
    assert disposition["excluded"]["C3"]["old_C3_adopted"] is False


def test_recorded_non_design_input_is_rehashed(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"sealed")
    digest = ADOPT.sha256_file(source)
    artifact = {
        "input_verification": {
            "files": [
                {
                    "path": str(source),
                    "bytes": source.stat().st_size,
                    "sha256_expected": digest,
                    "sha256_actual": digest,
                    "match": True,
                }
            ]
        }
    }

    result = ADOPT.verify_recorded_live_inputs(
        {"fixture": artifact},
        design_path=tmp_path / "not-the-source",
    )

    assert result["all_match"] is True
    assert result["unique_file_count"] == 1
    source.write_bytes(b"mutated")
    with pytest.raises(ValueError, match="input changed"):
        ADOPT.verify_recorded_live_inputs(
            {"fixture": artifact},
            design_path=tmp_path / "not-the-source",
        )
