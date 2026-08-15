"""Emit a deterministic entity/column inventory from a built pool H5.

Built pool artifacts are pandas HDF5 stores with one root group per entity.
Each entity group's ``axis0`` dataset contains its column labels. Private root
groups (names beginning with ``_``) carry staging metadata and are not entity
tables.

    uv run python tools/emit_artifact_column_inventory.py /path/to/pool.h5 \
        --manifest /path/to/pool.manifest.json \
        --out /path/to/inventory.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import h5py

_HASH_CHUNK_BYTES = 8 * 1024 * 1024


def _column_name(value: Any, *, entity: str) -> str:
    if isinstance(value, bytes):
        name = value.decode("utf-8")
    elif isinstance(value, str):
        name = value
    else:
        raise TypeError(
            f"H5 entity {entity!r} has a non-string axis0 label: {value!r}"
        )
    if not name:
        raise ValueError(f"H5 entity {entity!r} has an empty axis0 label.")
    if "/" in name:
        raise ValueError(
            f"H5 entity {entity!r} column {name!r} contains '/', which makes "
            "the entity/column inventory key ambiguous."
        )
    return name


def inventory_columns(h5_path: Path) -> list[str]:
    """Return globally sorted ``entity/column`` names from a built pool H5."""

    h5_path = Path(h5_path)
    columns: list[str] = []
    entity_count = 0
    with h5py.File(h5_path, mode="r") as h5:
        for entity in sorted(h5.keys()):
            if entity.startswith("_"):
                continue
            table = h5[entity]
            if not isinstance(table, h5py.Group):
                raise ValueError(
                    f"Public H5 root member {entity!r} is not an entity group."
                )
            axis0 = table.get("axis0")
            if not isinstance(axis0, h5py.Dataset) or axis0.ndim != 1:
                raise ValueError(
                    f"H5 entity group {entity!r} has no one-dimensional "
                    "axis0 column-label dataset."
                )
            if "/" in entity:
                raise ValueError(
                    f"H5 entity {entity!r} contains '/', which makes inventory "
                    "keys ambiguous."
                )
            entity_count += 1
            columns.extend(
                f"{entity}/{_column_name(value, entity=entity)}" for value in axis0[:]
            )

    if entity_count == 0:
        raise ValueError(f"No entity tables found in built pool H5 {h5_path}.")

    columns.sort()
    duplicates = [
        name
        for previous, name in zip(columns, columns[1:], strict=False)
        if name == previous
    ]
    if duplicates:
        raise ValueError(
            "Built pool H5 contains duplicate entity/column names: "
            f"{sorted(set(duplicates))}"
        )
    return columns


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_source(
    h5_path: Path,
    manifest_path: Path,
    *,
    run_label: str | None,
) -> dict[str, str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"Pool manifest {manifest_path} must be a JSON object.")

    pool_h5 = manifest.get("pool_h5")
    if not isinstance(pool_h5, dict):
        raise ValueError(f"Pool manifest {manifest_path} has no pool_h5 object.")

    manifest_artifact_path = pool_h5.get("path")
    if not isinstance(manifest_artifact_path, str) or not manifest_artifact_path:
        raise ValueError(f"Pool manifest {manifest_path} has no pool_h5.path.")
    if Path(manifest_artifact_path).name != h5_path.name:
        raise ValueError(
            f"Pool manifest names {Path(manifest_artifact_path).name!r}, not "
            f"the supplied artifact {h5_path.name!r}."
        )

    artifact_sha256 = pool_h5.get("sha256")
    publication_run_id = manifest.get("publication_run_id")
    release_id = manifest.get("release_id")
    required_strings = {
        "pool_h5.sha256": artifact_sha256,
        "publication_run_id": publication_run_id,
        "release_id": release_id,
    }
    for field, value in required_strings.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"Pool manifest {manifest_path} has no valid {field}.")

    expected_size = pool_h5.get("size_bytes")
    if isinstance(expected_size, int) and h5_path.stat().st_size != expected_size:
        raise ValueError(
            f"Pool manifest records {expected_size} bytes for {h5_path.name}, "
            f"but the supplied artifact has {h5_path.stat().st_size} bytes."
        )
    actual_sha256 = _file_sha256(h5_path)
    if actual_sha256 != artifact_sha256:
        raise ValueError(
            f"Pool manifest records SHA-256 {artifact_sha256} for {h5_path.name}, "
            f"but the supplied artifact hashes to {actual_sha256}."
        )

    return {
        "artifact_filename": h5_path.name,
        "artifact_sha256": artifact_sha256,
        "manifest_filename": manifest_path.name,
        "publication_run_id": publication_run_id,
        "release_id": release_id,
        "run_label": run_label or manifest_path.parent.name,
    }


def emit_inventory(
    h5_path: Path,
    *,
    manifest_path: Path | None = None,
    run_label: str | None = None,
) -> dict[str, object]:
    """Build the versioned inventory payload for ``h5_path``."""

    h5_path = Path(h5_path)
    source: dict[str, str] = {"artifact_filename": h5_path.name}
    if manifest_path is not None:
        source = _manifest_source(
            h5_path,
            Path(manifest_path),
            run_label=run_label,
        )
    elif run_label is not None:
        source["run_label"] = run_label

    return {
        "schema_version": 1,
        "source": source,
        "columns": inventory_columns(h5_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("h5", type=Path, help="Built pool H5 artifact to inventory.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional pool manifest supplying authenticated artifact provenance.",
    )
    parser.add_argument(
        "--run-label",
        help="Run label for the fixture header (defaults to the manifest directory).",
    )
    args = parser.parse_args(argv)

    payload = emit_inventory(
        args.h5,
        manifest_path=args.manifest,
        run_label=args.run_label,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(payload['columns'])} entity/column names")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
