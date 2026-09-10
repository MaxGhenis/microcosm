"""Attach explicit run evidence to the shared Orrery presentation contract.

The caller owns execution and must validate saved manifests with
``RunManifest.load`` before exporting them. Report values are supplied evidence,
not new graph computations. No population values are read by this adapter.
"""

from __future__ import annotations

import json

from .decl import CompiledGraph
from .explorer import (
    _MAX_OUTPUT_BYTES,
    _bounded_json,
    _copy_json,
    _id,
    _require,
    _revision,
    graph_explorer_document,
)
from .manifest import RunManifest
from .schema import graph_schema

__all__ = ["graph_run_explorer_document"]


def graph_run_explorer_document(
    compiled: CompiledGraph,
    manifest: RunManifest,
    *,
    reports: dict[str, object] | None = None,
    title: str | None = None,
) -> dict:
    """Present declared fields, recorded node receipts and supplied diagnostics.

    Roster and kernel checks prevent attaching an obviously unrelated run.
    They do not authenticate that the supplied declaration produced the run;
    the producer must retain their real execution association. Report nodes are
    separately identified, with no inferred dependencies or pass/fail verdicts.
    """
    _require(type(manifest) is RunManifest, "actual RunManifest required")
    document = graph_explorer_document(graph_schema(compiled), title=title)
    _require(manifest.country == compiled.graph.country, "run country mismatch")
    _require(set(manifest.nodes) == set(compiled.order), "run node roster mismatch")
    payload = json.loads(manifest.to_json())
    for node in document["nodes"]:
        if node["kind"] != "operation":
            continue
        declaration = node["data"]["declaration"]
        receipt = payload["nodes"][declaration["id"]]
        _require(receipt["kernel_ref"] == declaration["kernel"], "run kernel mismatch")
        node["data"]["run_receipt"] = receipt
        node["statuses"] = [
            {"label": "Receipt recorded", "tone": "neutral"},
            {"label": "Cache hit" if receipt["hit"] else "Cache miss", "tone": "neutral"},
        ]
        outcome = receipt["receipt"].get("outcome")
        if outcome is not None:
            node["statuses"].append(
                {"label": f"Recorded outcome: {outcome}", "tone": "neutral"}
            )
        node["revision"] = _revision(_copy_json(node, transport=True))

    report_values = {} if reports is None else _copy_json(reports)
    _require(type(report_values) is dict, "reports must be a JSON object")
    for name, value in report_values.items():
        _require(bool(name.strip()), "nonempty report name required")
        report = {
            "id": _id("run_report", name),
            "label": name.replace("_", " ").capitalize(),
            "kind": "diagnostics",
            "description": "Supplied development-run evidence; inspect data for values and limitations.",
            "statuses": [{"label": "Development evidence", "tone": "warning"}],
            "data": {
                "report_name": name,
                "report": value,
                "manifest_key": manifest.key,
            },
        }
        report["revision"] = _revision(_copy_json(report, transport=True))
        document["nodes"].append(report)

    document["description"] = (
        "Declared graph with recorded execution receipts and supplied diagnostics. "
        "Development evidence; no release certification or take-up estimate."
    )
    document["metadata"]["run_evidence"] = {
        "manifest_key": manifest.key,
        "manifest_tier": manifest.tier,
        "scope": "Recorded node receipts; supplied reports remain separately identified.",
        "binding_checks": ["country", "node roster", "kernel references"],
        "authority": "Graph execution and saved-manifest validation remain the caller's responsibility.",
    }
    document = _copy_json(document, transport=True)
    document.pop("revision", None)
    document["revision"] = _revision(document)
    _bounded_json(document, _MAX_OUTPUT_BYTES)
    return document
