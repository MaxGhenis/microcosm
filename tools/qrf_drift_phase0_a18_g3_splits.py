#!/usr/bin/env python3
"""Seal the A18 frozen-gate G3 split enumeration.

This executor is deliberately narrower than the Phase-0 reading executors. It
restores all 36 production gates through the already validated C0b/C4 replay
path, inspects only their fitted ``HistGradientBoostingClassifier`` tree
nodes, and writes the mechanical A18 branch decision. It does not evaluate a
reading, intervention, Shapley quantity, or magnitude forest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np
import qrf_drift_phase0_c4 as c4
import qrf_drift_phase0_replay as replay
import sklearn

WORKTREE = Path(__file__).resolve().parents[1]
DESIGN_MD = WORKTREE / "experiments/qrf_drift_validation_design.md"
D0_MD = WORKTREE / "experiments/qrf_drift_validation_d0.md"
D0_JSON = WORKTREE / "experiments/qrf_drift_validation_d0.json"
A16_BINDING = WORKTREE / "experiments/qrf_drift_validation_a16_binding_texts.md"
DEFAULT_C0B = Path("/private/tmp/qrf_phase0_v22_c0b.json")
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_a18_g3_split_enumeration.json")

EXPECTED_AUTHORITY_DIGESTS = {
    str(DESIGN_MD): (
        "5c8e55293215a7d1350c93825b1a4daf04e212bb84d17408b8750ed5d9d4e754"
    ),
    str(D0_MD): (
        "c4f3a9c56426025426e56428e9bce697a6cc6112f175be86ef9ef139bf79b601"
    ),
    str(D0_JSON): (
        "fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8"
    ),
    str(A16_BINDING): (
        "7e288bce7496e1e7f41e33f078be2043673ca54ff31182caf2ce92eab68a81c1"
    ),
}
EXPECTED_C0B_SHA256 = (
    "1c7bfd65660b14068c4bc96fae4b8d270cb447ea8fbbe42c8ef982c5f1dbf542"
)
EXPECTED_TARGET_COUNT = 9
EXPECTED_GATE_COUNT = 36


def canonical_sha256(value: Any) -> str:
    """Hash a JSON-safe value with the Phase-0 canonical JSON encoder."""
    return hashlib.sha256(c4.canonical_bytes(value)).hexdigest()


def split_feature_statistics(gate: Any) -> dict[int, dict[str, Any]]:
    """Aggregate nonleaf split counts and gains by gate feature index.

    ``gain`` is scikit-learn's stored split gain on each nonleaf HGB node.
    Iterations, class trees, and nodes are traversed in their persisted order;
    ``math.fsum`` then gives a stable binary64 total for each feature.
    """
    gains: dict[int, list[float]] = {}
    for iteration in gate._predictors:
        for predictor in iteration:
            nodes = predictor.nodes
            required_fields = {"feature_idx", "gain", "is_leaf"}
            fields = set(nodes.dtype.names or ())
            if not required_fields <= fields:
                raise ValueError(
                    "HGB node layout lacks required split fields: "
                    f"{sorted(required_fields - fields)}"
                )
            for node in nodes[nodes["is_leaf"] == 0]:
                feature_index = int(node["feature_idx"])
                gain = float(node["gain"])
                if feature_index < 0:
                    raise ValueError(f"negative nonleaf feature index {feature_index}")
                if not math.isfinite(gain) or gain < 0.0:
                    raise ValueError(
                        f"invalid split gain {gain!r} for feature {feature_index}"
                    )
                gains.setdefault(feature_index, []).append(gain)

    result: dict[int, dict[str, Any]] = {}
    for feature_index in sorted(gains):
        values = gains[feature_index]
        gain_array = np.asarray(values, dtype="<f8")
        total = float(math.fsum(values))
        result[feature_index] = {
            "split_count": len(values),
            "total_split_gain": total,
            "total_split_gain_hex": total.hex(),
            "split_gain_sequence_identity": c4.array_identity(gain_array),
        }
    return result


def gate_nodes_identity(gate: Any) -> dict[str, Any]:
    """Digest every fitted HGB node array without relying on object pickles."""
    arrays: list[dict[str, Any]] = []
    for iteration_index, iteration in enumerate(gate._predictors):
        for tree_index, predictor in enumerate(iteration):
            nodes = predictor.nodes
            arrays.append(
                {
                    "iteration": iteration_index,
                    "tree": tree_index,
                    "dtype_descr": repr(nodes.dtype.descr),
                    "nodes": c4.array_identity(nodes),
                }
            )
    return {
        "tree_count": len(arrays),
        "arrays_sha256": canonical_sha256(arrays),
    }


def enumerate_g3_columns(
    gate: Any,
    *,
    target: str,
    pattern: str,
    columns: tuple[str, ...],
    g3_columns: tuple[str, ...],
    target_order: int,
    pattern_order: int,
    first_triple_order: int,
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return all G3 triples for one gate, including exact zero-split rows."""
    if len(g3_columns) != len(set(g3_columns)):
        raise ValueError(f"duplicate G3 column for {target}/{pattern}")
    missing = [name for name in g3_columns if name not in columns]
    if missing:
        raise ValueError(f"G3 columns absent from gate for {target}/{pattern}: {missing}")

    statistics = split_feature_statistics(gate)
    invalid_indexes = [index for index in statistics if index >= len(columns)]
    if invalid_indexes:
        raise ValueError(
            f"split feature indexes exceed column roster for {target}/{pattern}: "
            f"{invalid_indexes}"
        )

    rows: list[dict[str, Any]] = []
    for g3_order, column in enumerate(g3_columns):
        feature_index = columns.index(column)
        statistic = statistics.get(
            feature_index,
            {
                "split_count": 0,
                "total_split_gain": 0.0,
                "total_split_gain_hex": 0.0.hex(),
                "split_gain_sequence_identity": c4.array_identity(
                    np.asarray([], dtype="<f8")
                ),
            },
        )
        rows.append(
            {
                "stable_order": {
                    "triple": first_triple_order + g3_order,
                    "target": target_order,
                    "pattern": pattern_order,
                    "G3_column": g3_order,
                },
                "target": target,
                "pattern": pattern,
                "G3_column": column,
                "gate_feature_index": feature_index,
                **statistic,
                "source": source,
            }
        )
    return rows


def seal_split_table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Filter the A18 table and seal its definition, ordering, and rows."""
    table: list[dict[str, Any]] = []
    previous_order = -1
    for row in rows:
        order = int(row["stable_order"]["triple"])
        if order <= previous_order:
            raise ValueError("G3 triples are not in strictly increasing D0 order")
        previous_order = order
        if int(row["split_count"]) >= 1:
            table.append({"table_order": len(table), **row})

    definition = {
        "row_predicate": "split_count >= 1",
        "split_count": (
            "count of nonleaf HistGradientBoostingClassifier nodes whose "
            "feature_idx is the G3 column, over iterations and class trees"
        ),
        "total_split_gain": (
            "math.fsum of the scikit-learn node gain field for those nodes "
            "in iteration, class-tree, node order"
        ),
        "stable_order": (
            "D0-2 target insertion order, then D0-2 pattern list order, then "
            "D0-7 G3 list order"
        ),
        "canonicalization": "Phase-0 binary64 shortest-roundtrip canonical JSON",
    }
    sealed_payload = {"definition": definition, "rows": table}
    return {
        "definition": definition,
        "rows": table,
        "row_count": len(table),
        "sha256": canonical_sha256(sealed_payload),
    }


def select_largest_gain(table: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Apply A18's largest-gain rule with the table order as the tie-break."""
    if not table:
        return None
    selected = min(
        table,
        key=lambda row: (-float(row["total_split_gain"]), int(row["table_order"])),
    )
    return {
        "table_order": int(selected["table_order"]),
        "target": selected["target"],
        "pattern": selected["pattern"],
        "G3_column": selected["G3_column"],
        "split_count": int(selected["split_count"]),
        "total_split_gain": float(selected["total_split_gain"]),
        "total_split_gain_hex": selected["total_split_gain_hex"],
        "row_sha256": canonical_sha256(selected),
    }


def _expected_input_rows(
    d0: dict[str, Any],
    c0b_path: Path,
) -> list[dict[str, str]]:
    rows = [
        {"kind": "authority", "path": path, "sha256_expected": digest}
        for path, digest in EXPECTED_AUTHORITY_DIGESTS.items()
    ]
    stage_root = Path(
        d0["D0-0"]["artifacts"]["candidate-25"]["checkpoint_directories"]
        ["stage_root"]["path"]
    )
    rows.extend(
        {
            "kind": "stage_checkpoint",
            "path": str(stage_root / filename),
            "sha256_expected": digest,
        }
        for filename, digest in c4.EXPECTED_CHECKPOINT_DIGESTS.items()
    )
    rows.extend(
        {
            "kind": "target_bank",
            "path": item["path"],
            "sha256_expected": item["sha256"],
        }
        for item in d0["D0-0"]["artifacts"]["candidate-25"]
        ["bank_target_checkpoints"]
    )

    found_predecessors = {
        path.name: path
        for path in stage_root.rglob("*.h5")
        if path.name in c4.EXPECTED_PREDECESSOR_DIGESTS
    }
    missing = set(c4.EXPECTED_PREDECESSOR_DIGESTS) - set(found_predecessors)
    if missing:
        raise ValueError(f"missing predecessor bank(s): {sorted(missing)}")
    rows.extend(
        {
            "kind": "predecessor_bank",
            "path": str(found_predecessors[filename]),
            "sha256_expected": digest,
        }
        for filename, digest in c4.EXPECTED_PREDECESSOR_DIGESTS.items()
    )
    rows.append(
        {
            "kind": "adopted_C0b",
            "path": str(c0b_path),
            "sha256_expected": EXPECTED_C0B_SHA256,
        }
    )
    return rows


def verify_inputs(d0: dict[str, Any], c0b_path: Path) -> dict[str, Any]:
    """Verify every authority, checkpoint, bank, and adopted replay artifact."""
    rows = _expected_input_rows(d0, c0b_path)
    verified: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for item in rows:
        path = Path(item["path"])
        resolved = path.resolve()
        if resolved in seen:
            raise ValueError(f"duplicate resolved input path {resolved}")
        seen.add(resolved)
        actual = c4.sha256_file(path)
        match = actual == item["sha256_expected"]
        verified.append(
            {
                **item,
                "path": str(resolved),
                "bytes": resolved.stat().st_size,
                "sha256_actual": actual,
                "match": match,
            }
        )
    failed = [item["path"] for item in verified if not item["match"]]
    if failed:
        raise ValueError(f"pinned input digest mismatch: {failed}")
    return {
        "all_match": True,
        "file_count": len(verified),
        "files": verified,
    }


def _digest_lookup(input_verification: dict[str, Any]) -> dict[Path, str]:
    return {
        Path(item["path"]).resolve(): item["sha256_actual"]
        for item in input_verification["files"]
    }


def _source_for_context(
    context: dict[str, Any],
    adopted: dict[str, Any],
    digest_lookup: dict[Path, str],
) -> dict[str, Any]:
    bank_path = Path(context["bank"]["path"]).resolve()
    if bank_path not in digest_lookup:
        raise ValueError(f"target bank absent from verified inputs: {bank_path}")
    state_source = context["state_before_source"]
    state_source_payload: dict[str, Any]
    if state_source == "reconstructed_start_chain":
        state_source_payload = {"kind": state_source}
    else:
        state_path = Path(state_source).resolve()
        if state_path not in digest_lookup:
            raise ValueError(
                f"state-before source absent from verified inputs: {state_path}"
            )
        state_source_payload = {
            "kind": "bank",
            "path": str(state_path),
            "sha256": digest_lookup[state_path],
        }
    return {
        "target_bank": {
            "path": str(bank_path),
            "sha256": digest_lookup[bank_path],
        },
        "state_before": {
            **state_source_payload,
            "state_sha256": context["state_before_sha256"],
        },
        "gate_seed": context["gate_seed"],
        "gate_classes": [int(value) for value in context["gate_classes"]],
        "fit_gate_probability_matrix_sha256": adopted[
            "fit_gate_probability_matrix_sha256"
        ],
        "adopted_C0b_pattern_sha256": canonical_sha256(adopted),
        "gate_nodes": gate_nodes_identity(context["gate"]),
    }


def _source_file_digests() -> list[dict[str, Any]]:
    paths = [Path(__file__), Path(c4.__file__), Path(replay.__file__)]
    return [
        {
            "path": str(path.resolve()),
            "sha256": c4.sha256_file(path),
        }
        for path in paths
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seal the A18 frozen-gate G3 split enumeration",
    )
    parser.add_argument("--c0b-json", type=Path, default=DEFAULT_C0B)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for path, expected in EXPECTED_AUTHORITY_DIGESTS.items():
        actual = c4.sha256_file(Path(path))
        if actual != expected:
            raise ValueError(f"authority digest mismatch for {path}: {actual}")

    d0 = json.loads(D0_JSON.read_text())
    input_verification = verify_inputs(d0, args.c0b_json)
    digest_lookup = _digest_lookup(input_verification)
    c0b = json.loads(args.c0b_json.read_text())
    if not (
        c0b.get("status") == "PASS"
        and c0b.get("summary", {}).get("e4_bit_identical_pass") is True
        and c0b.get("summary", {}).get("e2_repeated_draw_control_pass") is True
    ):
        raise ValueError("adopted C0b artifact is not a clean PASS")

    target_specs = d0["D0-2"]["targets"]
    if len(target_specs) != EXPECTED_TARGET_COUNT:
        raise ValueError(f"D0 target count changed: {len(target_specs)}")
    expected_keys = [
        (target, pattern["name"])
        for target, target_spec in target_specs.items()
        for pattern in target_spec["patterns"]
    ]
    actual_keys = [(item["target"], item["pattern"]) for item in c0b["patterns"]]
    if expected_keys != actual_keys or len(expected_keys) != EXPECTED_GATE_COUNT:
        raise ValueError("adopted C0b gate order/coverage differs from D0")
    c0b_lookup = {
        (item["target"], item["pattern"]): item for item in c0b["patterns"]
    }

    data = c4.load_analysis_data(d0)
    all_triples: list[dict[str, Any]] = []
    gates: list[dict[str, Any]] = []
    for target_order, (target, target_spec) in enumerate(target_specs.items()):
        for pattern_order, pattern_spec in enumerate(target_spec["patterns"]):
            pattern = pattern_spec["name"]
            adopted = c0b_lookup[(target, pattern)]
            context = c4.fit_gate_context(data, target, pattern, c0b_lookup)
            if not all(context["c0b_bindings"].values()):
                raise ValueError(f"C0b binding failed for {target}/{pattern}")
            source = _source_for_context(
                context,
                adopted,
                digest_lookup,
            )
            statistics = split_feature_statistics(context["gate"])
            triple_rows = enumerate_g3_columns(
                context["gate"],
                target=target,
                pattern=pattern,
                columns=context["columns"],
                g3_columns=context["groups"]["G3"],
                target_order=target_order,
                pattern_order=pattern_order,
                first_triple_order=len(all_triples),
                source=source,
            )
            all_triples.extend(triple_rows)
            gates.append(
                {
                    "stable_order": {
                        "gate": len(gates),
                        "target": target_order,
                        "pattern": pattern_order,
                    },
                    "target": target,
                    "pattern": pattern,
                    "columns": list(context["columns"]),
                    "G3_columns": list(context["groups"]["G3"]),
                    "all_split_count": sum(
                        int(item["split_count"]) for item in statistics.values()
                    ),
                    "G3_split_count": sum(
                        int(item["split_count"]) for item in triple_rows
                    ),
                    "c0b_bindings": context["c0b_bindings"],
                    "source": source,
                }
            )

    if len(gates) != EXPECTED_GATE_COUNT:
        raise ValueError(f"reconstructed gate count changed: {len(gates)}")
    table = seal_split_table(all_triples)
    selected = select_largest_gain(table["rows"])
    disposition = (
        {
            "branch": 2,
            "action": "RETARGET_C3_TO_LARGEST_GAIN_TRIPLE",
            "selected": selected,
        }
        if selected is not None
        else {
            "branch": 3,
            "action": "WAIVE_C3_AND_ASSERT_GATE_STAGE_G3_ZERO_BY_MECHANISM",
            "selected": None,
        }
    )

    result: dict[str, Any] = {
        "artifact_kind": "qrf_drift_phase0_a18_g3_split_enumeration",
        "schema_version": 1,
        "status": "SEALED",
        "authority": {
            "design": {
                "path": str(DESIGN_MD),
                "sha256": EXPECTED_AUTHORITY_DIGESTS[str(DESIGN_MD)],
                "commit": "8d553796e846012e7dc2663d7ffe108b6f965cca",
                "amendment": "v2.7/A18",
            },
            "d0_json": {
                "path": str(D0_JSON),
                "sha256": EXPECTED_AUTHORITY_DIGESTS[str(D0_JSON)],
            },
            "d0_markdown": {
                "path": str(D0_MD),
                "sha256": EXPECTED_AUTHORITY_DIGESTS[str(D0_MD)],
            },
            "a16_binding": {
                "path": str(A16_BINDING),
                "sha256": EXPECTED_AUTHORITY_DIGESTS[str(A16_BINDING)],
            },
            "adopted_C0b": {
                "path": str(args.c0b_json.resolve()),
                "sha256": EXPECTED_C0B_SHA256,
            },
        },
        "scope": {
            "rung": "candidate-25 pre-calibration",
            "target_count": len(target_specs),
            "gate_count": len(gates),
            "G3_triples_considered": len(all_triples),
            "G3_triples_with_splits": table["row_count"],
            "G3_triples_without_splits": len(all_triples) - table["row_count"],
            "forest_scope": "gate trees only; magnitude forests not loaded",
            "readings_computed": False,
        },
        "input_verification": input_verification,
        "source_files": _source_file_digests(),
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "platform": platform.platform(),
        },
        "gates": gates,
        "all_G3_triples": {
            "rows": all_triples,
            "row_count": len(all_triples),
            "sha256": canonical_sha256(all_triples),
        },
        "sealed_split_table": table,
        "mechanical_disposition": disposition,
        "statistics": [],
    }
    output_sha = c4.write_canonical_result(args.out, result)
    print(
        f"RESULT {args.out} sha256={output_sha} "
        f"table_sha256={table['sha256']} branch={disposition['branch']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
