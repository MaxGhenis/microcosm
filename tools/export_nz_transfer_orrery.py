#!/usr/bin/env python3
"""Bundle a saved development graph and its evidence with the existing Orrery CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from microcosm.graph import ContentStore, RunManifest, compile_graph, graph_from_json
from microcosm.graph.explorer_run import graph_run_explorer_document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--store", type=Path)
    parser.add_argument("--viewer-cli", type=Path, required=True)
    parser.add_argument("--node", default="node")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    compiled = compile_graph(graph_from_json(args.graph.read_text(encoding="utf-8")))
    store_path = args.store or args.manifest.parent / "store"
    if not store_path.is_dir():
        parser.error(f"Content store does not exist: {store_path}")
    manifest = RunManifest.load(args.manifest, store=ContentStore(store_path))
    report = json.loads(args.report.read_text(encoding="utf-8"))
    document = graph_run_explorer_document(
        compiled,
        manifest,
        reports=report,
        title="Microcosm NZ transfer development candidate",
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    graph_path = args.out.with_suffix(".graph-explorer.json")
    graph_path.write_text(
        json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            args.node,
            str(args.viewer_cli.resolve()),
            "--input",
            str(graph_path.resolve()),
            "--output",
            str(args.out.resolve()),
        ],
        check=True,
        timeout=60,
    )
    evidence = {
        "manifest_key": manifest.key,
        "viewer_cli": str(args.viewer_cli.resolve()),
        "viewer_cli_sha256": hashlib.sha256(args.viewer_cli.read_bytes()).hexdigest(),
        "graph_document_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        "html_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
        "scope": "Validated saved-manifest artifacts and exported development evidence; browser QA is separate.",
    }
    args.out.with_suffix(".export.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
