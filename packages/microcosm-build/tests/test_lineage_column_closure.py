"""Every built-pool column has one, and only one, lineage class."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import pytest
import yaml

from microcosm.build.us_runtime.cps_carried import (
    CPS_CARRIED_PERSON_INPUTS,
    CPS_CARRIED_SPM_UNIT_INPUTS,
)

ROOT = Path(__file__).resolve().parents[3]
SPEC_PATH = ROOT / "specs" / "us_imputation_lineage.yaml"
INVENTORY_PATH = ROOT / "specs" / "us_pool_column_inventory.json"
TAKE_UP_CONTRACT_PATH = (
    ROOT
    / "packages/microcosm-build/src/microcosm/build/us/take_up_contract.json"
)
ARTIFACT_ENV = "MICROCOSM_LINEAGE_POOL_H5"


def _load_tool(name: str):
    path = ROOT / "tools" / f"{name}.py"
    module_spec = importlib.util.spec_from_file_location(name, path)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


INVENTORY_TOOL = _load_tool("emit_artifact_column_inventory")
DASHBOARD_TOOL = _load_tool("emit_lineage_dashboard")


@pytest.fixture(scope="module")
def spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def test_inventory_fixture_is_sorted_unique_entity_column_names(
    inventory: dict,
) -> None:
    columns = inventory["columns"]
    assert inventory["schema_version"] == 1
    assert inventory["source"] == {
        "artifact_filename": "populace_us_2024_stacked_pool_probe.h5",
        "artifact_sha256": (
            "c2789a2edcdc57a7317de6a65a4d4ed0cce842ade8483c420f2a7d1d21d6bbb5"
        ),
        "manifest_filename": "populace_us_2024_stacked_pool_probe.manifest.json",
        "publication_run_id": "d8198a9e4ab94e8083a26a0f63d8511a",
        "release_id": (
            "populace-us-2024-stacked-f025-s578-asec42213-acs382903-"
            "20260815T144715Z-f6094a6b"
        ),
        "run_label": "probe-f025-r1",
    }
    assert len(columns) == 392
    assert columns
    assert columns == sorted(set(columns))
    assert all(
        len(parts := column.split("/")) == 2 and all(parts)
        for column in columns
    )


def test_every_inventory_column_has_exactly_one_lineage_class(
    spec: dict,
    inventory: dict,
) -> None:
    """Modeled layers union; collisions between exclusive classes stay fatal."""

    columns = inventory["columns"]
    claims = DASHBOARD_TOOL.column_lineage_claims(spec, columns)
    owners: dict[str, list[str]] = defaultdict(list)
    for class_name, class_claims in claims.items():
        for column in class_claims:
            owners[column].append(class_name)

    unclaimed = sorted(set(columns) - set(owners))
    multiply_claimed = {
        column: sorted(class_names)
        for column, class_names in sorted(owners.items())
        if len(class_names) != 1
    }
    assert not unclaimed and not multiply_claimed, (
        "lineage column closure failed\n"
        f"unclaimed ({len(unclaimed)}): {unclaimed}\n"
        f"multiply claimed ({len(multiply_claimed)}): {multiply_claimed}"
    )

    take_up_columns = {
        column
        for column in columns
        if column.rsplit("/", maxsplit=1)[1].startswith("takes_up_")
    }
    assert claims["take_up_draws"] == take_up_columns


def test_dashboard_coverage_meter_matches_column_closure(
    spec: dict,
    inventory: dict,
) -> None:
    claims = DASHBOARD_TOOL.column_lineage_claims(spec, inventory["columns"])
    coverage = DASHBOARD_TOOL.emit(SPEC_PATH, INVENTORY_PATH)["counts"]["coverage"]

    assert coverage["claimed"] == coverage["total"] == len(inventory["columns"])
    assert coverage["per_class"] == {
        class_name: len(class_claims)
        for class_name, class_claims in claims.items()
    }
    assert sum(coverage["per_class"].values()) == coverage["total"]
    assert coverage["unclaimed"] == 0
    assert coverage["multiply_claimed"] == 0
    assert coverage["debt"] == {
        "count": len(claims["unclassified"]),
        "columns": sorted(claims["unclassified"]),
    }


def test_take_up_mechanism_trace_is_complete_and_unique(spec: dict) -> None:
    required = {
        "artifact_assignment",
        "f025_observation",
        "producer_stage",
        "probability_source",
        "conditioning",
        "determinism",
        "calibration_status",
        "source",
    }
    seen: set[str] = set()
    for record in spec["take_up_draws"]:
        key = f"{record['entity']}/{record['column']}"
        assert key not in seen, f"duplicate take-up mechanism declaration: {key}"
        seen.add(key)
        missing = sorted(
            field
            for field in required
            if not str(record.get(field, "")).strip()
        )
        assert not missing, f"{key} lacks mechanism field(s): {missing}"
        assert ".py:" in record["source"], (
            f"{key} source must cite a code module and line(s): {record['source']}"
        )

    contract_programs = {
        program["variable"]: program
        for program in json.loads(TAKE_UP_CONTRACT_PATH.read_text())["programs"]
    }
    traces = {record["column"]: record for record in spec["take_up_draws"]}
    assert set(traces) == set(contract_programs)
    for variable, program in contract_programs.items():
        trace = traces[variable]
        contract = trace["contract"]
        assert trace["entity"] == program["entity"], variable
        assert contract["treatment"] == program["populace_treatment"], variable
        assert contract["engine_default"] == program["default"], variable
        assert contract["rate_status"] == program["rate"]["status"], variable
        if "value" in program["rate"]:
            assert contract["rate_value"] == program["rate"]["value"], variable
        else:
            assert "rate_value" not in contract, variable
        if "values_by_num_children" in program["rate"]:
            assert (
                contract["values_by_num_children"]
                == program["rate"]["values_by_num_children"]
            ), variable
        else:
            assert "values_by_num_children" not in contract, variable


def test_new_grouped_classes_cite_their_owners(
    spec: dict,
    inventory: dict,
) -> None:
    measured_groups = [
        group
        for channel in spec["measured_native"].values()
        for group in channel["groups"]
    ]
    grouped = [
        *measured_groups,
        *spec["receipts"]["groups"],
        *spec["structural"]["groups"],
    ]
    for group in grouped:
        assert str(group.get("source", "")).strip(), group["id"]
        assert ".py:" in group["source"], group["id"]

    for assignment in spec["geography"]["assigned_by_ladder"]:
        assert assignment["mechanics"] == "pending microcosm#696 lane"
        assert ".py:" in assignment["source"]

    claims = DASHBOARD_TOOL.column_lineage_claims(spec, inventory["columns"])
    carried_groups = spec["measured_native"]["asec_raw"][
        "lowercase_carried_surface"
    ]["groups"]
    expected_carried = {
        "person": set(CPS_CARRIED_PERSON_INPUTS),
        "spm_unit": set(CPS_CARRIED_SPM_UNIT_INPUTS),
    }
    artifact_names = {
        entity: {
            key.split("/", maxsplit=1)[1]
            for key in inventory["columns"]
            if key.startswith(f"{entity}/")
        }
        for entity in expected_carried
    }
    assert {group["entity"] for group in carried_groups} == set(expected_carried)
    for group in carried_groups:
        measured = set(group["measured_native_columns"])
        modeled = set(group["modeled_columns"])
        assert measured.isdisjoint(modeled), group["id"]
        assert measured | modeled == (
            expected_carried[group["entity"]] & artifact_names[group["entity"]]
        ), group["id"]
        assert ".py:" in group["source"], group["id"]
        for column in measured:
            assert f"{group['entity']}/{column}" in claims["measured_native"]
        for column in modeled:
            assert f"{group['entity']}/{column}" in claims["modeled"]


def test_inventory_generator_rejects_manifest_sha_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "pool.h5"
    with INVENTORY_TOOL.h5py.File(artifact, mode="w") as h5:
        entity = h5.create_group("person")
        entity.create_dataset("axis0", data=[b"person_id"])

    manifest = tmp_path / "pool.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "publication_run_id": "test-run",
                "release_id": "test-release",
                "pool_h5": {
                    "path": str(artifact),
                    "sha256": "0" * 64,
                    "size_bytes": artifact.stat().st_size,
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="supplied artifact hashes to"):
        INVENTORY_TOOL.emit_inventory(artifact, manifest_path=manifest)


def test_inventory_fixture_matches_opt_in_built_pool(inventory: dict) -> None:
    artifact = os.environ.get(ARTIFACT_ENV)
    if not artifact:
        pytest.skip(f"set {ARTIFACT_ENV} to regenerate the inventory from a pool H5")

    artifact_path = Path(artifact)
    assert artifact_path.is_file(), f"{ARTIFACT_ENV} is not a file: {artifact_path}"
    assert INVENTORY_TOOL.inventory_columns(artifact_path) == inventory["columns"]
