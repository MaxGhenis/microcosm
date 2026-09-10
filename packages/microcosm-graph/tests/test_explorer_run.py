"""Evidence is attached explicitly without inventing execution or release status."""

import json
from dataclasses import replace

import pytest

from microcosm.graph import (
    Capabilities,
    Determinism,
    Graph,
    Node,
    Owned,
    SourceRef,
    StructuralDelta,
    compile_graph,
)
from microcosm.graph.explorer_run import graph_run_explorer_document
from microcosm.graph.manifest import NodeReceipt, RunManifest


def example():
    compiled = compile_graph(
        Graph(
            "nz",
            sources=(SourceRef("fixture", "csv-tables"),),
            nodes=(
                Node(
                    "source",
                    "example.source@1",
                    sources=("fixture",),
                    structural=StructuralDelta.CREATE,
                    outputs=(Owned("person", "age", "int64"),),
                ),
            ),
        )
    )
    manifest = RunManifest(
        "nz",
        {
            "source": NodeReceipt(
                key="a" * 64,
                hit=False,
                seed=2**60 + 1,
                kernel_ref="example.source@1",
                kernel_impl_hash="b" * 64,
                capabilities=Capabilities(
                    determinism=Determinism.DETERMINISTIC,
                    structural=StructuralDelta.CREATE,
                ),
                receipt={"source_status": "invented fixture"},
            )
        },
    )
    return compiled, manifest


def test_run_receipts_and_diagnostics_remain_distinct_exact_evidence():
    compiled, manifest = example()
    reports = {
        "as_coverage": {"computable_rows": 0},
        "holdout": {"relative_error": 0.1},
    }
    document = graph_run_explorer_document(compiled, manifest, reports=reports)
    operation = next(node for node in document["nodes"] if node["kind"] == "operation")
    assert operation["data"]["run_receipt"]["seed"] == {
        "integer_literal": str(2**60 + 1)
    }
    assert operation["data"]["run_receipt"]["receipt"] == {
        "source_status": "invented fixture"
    }
    diagnostics = {
        node["data"]["report_name"]: node
        for node in document["nodes"]
        if node["kind"] == "diagnostics"
    }
    assert diagnostics["as_coverage"]["data"]["report"] == reports["as_coverage"]
    assert diagnostics["holdout"]["data"]["report"] == reports["holdout"]
    assert document["metadata"]["run_evidence"]["manifest_tier"] is None
    assert "no release certification" in document["description"]
    assert not any(
        badge.get("tone") == "positive"
        for node in document["nodes"]
        for badge in node.get("statuses", [])
    )
    reports["holdout"]["relative_error"] = 999
    assert diagnostics["holdout"]["data"]["report"]["relative_error"] == 0.1
    json.dumps(document, allow_nan=False)


@pytest.mark.parametrize("alteration", ["country", "roster", "kernel"])
def test_unrelated_run_is_rejected(alteration):
    compiled, manifest = example()
    if alteration == "country":
        manifest = replace(manifest, country="us")
    elif alteration == "roster":
        manifest = replace(manifest, nodes={})
    else:
        manifest = replace(
            manifest,
            nodes={"source": replace(manifest.nodes["source"], kernel_ref="other@1")},
        )
    with pytest.raises(ValueError, match="mismatch"):
        graph_run_explorer_document(compiled, manifest)


def test_changing_report_changes_revision_without_changing_execution_identity():
    compiled, manifest = example()
    first = graph_run_explorer_document(compiled, manifest, reports={"holdout": 0.1})
    second = graph_run_explorer_document(compiled, manifest, reports={"holdout": 0.2})
    assert first["revision"] != second["revision"]
    assert (
        first["metadata"]["run_evidence"]["manifest_key"]
        == second["metadata"]["run_evidence"]["manifest_key"]
    )
