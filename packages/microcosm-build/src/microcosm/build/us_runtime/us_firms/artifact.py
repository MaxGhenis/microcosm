"""Atomic, hash-bound artifact IO for the observed US firm population."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Protocol

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

__all__ = [
    "USFirmArtifactPaths",
    "sha256_file",
    "verify_us_firm_artifact",
    "write_us_firm_artifact",
]

ARTIFACT_SCHEMA_VERSION = "microcosm.us_firms.artifact.v1"
DIAGNOSTICS_FILENAME = "diagnostics.json"
FIRMS_FILENAME = "firms.parquet"
MANIFEST_FILENAME = "manifest.json"
_EXPECTED_FILES = frozenset(
    {DIAGNOSTICS_FILENAME, FIRMS_FILENAME, MANIFEST_FILENAME}
)


class _BuildResult(Protocol):
    """Structural interface accepted by :func:`write_us_firm_artifact`."""

    firms: pd.DataFrame
    diagnostics: Mapping[str, object]
    config: object


@dataclass(frozen=True)
class USFirmArtifactPaths:
    """Paths and manifest receipt for a completed atomic artifact."""

    directory: Path
    firms: Path
    diagnostics: Path
    manifest: Path
    manifest_sha256: str


def sha256_file(path: str | Path) -> str:
    """Return a streaming SHA-256 digest for ``path``."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(payload: Mapping[str, object]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _config_payload(config: object) -> Mapping[str, object]:
    if is_dataclass(config):
        payload = asdict(config)
    elif isinstance(config, Mapping):
        payload = dict(config)
    else:
        raise TypeError("result.config must be a dataclass or mapping")
    return payload


def _write_parquet(firms: pd.DataFrame, path: Path) -> None:
    table = pa.Table.from_pandas(firms, preserve_index=False)
    metadata = {
        **(table.schema.metadata or {}),
        b"microcosm.artifact": b"populace-us-firms",
        b"microcosm.schema_version": ARTIFACT_SCHEMA_VERSION.encode(),
        b"microcosm.observation_unit": b"form-5500-plan-sponsor-ein",
        b"microcosm.employment_measure": b"active-plan-participants-end-of-year",
    }
    table = table.replace_schema_metadata(metadata)
    pq.write_table(
        table,
        path,
        compression="zstd",
        use_dictionary=False,
        write_statistics=True,
        data_page_version="2.0",
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_us_firm_artifact(
    result: _BuildResult,
    output_dir: str | Path,
) -> USFirmArtifactPaths:
    """Write a complete artifact through one same-filesystem directory rename.

    The destination must not exist.  This refusal prevents a failed rerun from
    mixing new files with an older publication and avoids an implicit
    destructive overwrite policy.
    """
    from microcosm.build.us_runtime.us_firms.frame import (
        USFirmBuildConfig,
        validate_us_firm_table,
    )

    if not isinstance(result.config, USFirmBuildConfig):
        raise TypeError("result.config must be USFirmBuildConfig")
    validate_us_firm_table(result.firms, result.config)
    destination = Path(output_dir).resolve()
    if destination.exists():
        raise FileExistsError(
            f"US firm artifact destination already exists: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.staging-",
            dir=destination.parent,
        )
    )
    try:
        firms_path = staging / FIRMS_FILENAME
        diagnostics_path = staging / DIAGNOSTICS_FILENAME
        manifest_path = staging / MANIFEST_FILENAME
        _write_parquet(result.firms, firms_path)
        diagnostics_path.write_bytes(_json_bytes(dict(result.diagnostics)))

        manifest: dict[str, object] = {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "artifact": "populace-us-firms",
            "producer": "microcosm.build.us_runtime.us_firms",
            "config": dict(_config_payload(result.config)),
            "files": {
                FIRMS_FILENAME: {
                    "sha256": sha256_file(firms_path),
                    "bytes": firms_path.stat().st_size,
                    "rows": int(len(result.firms)),
                },
                DIAGNOSTICS_FILENAME: {
                    "sha256": sha256_file(diagnostics_path),
                    "bytes": diagnostics_path.stat().st_size,
                },
            },
        }
        manifest_path.write_bytes(_json_bytes(manifest))
        for path in (firms_path, diagnostics_path, manifest_path):
            with path.open("rb") as stream:
                os.fsync(stream.fileno())
        _fsync_directory(staging)
        os.replace(staging, destination)
        _fsync_directory(destination.parent)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    manifest_path = destination / MANIFEST_FILENAME
    return USFirmArtifactPaths(
        directory=destination,
        firms=destination / FIRMS_FILENAME,
        diagnostics=destination / DIAGNOSTICS_FILENAME,
        manifest=manifest_path,
        manifest_sha256=sha256_file(manifest_path),
    )


def verify_us_firm_artifact(path: str | Path) -> dict[str, object]:
    """Rehash and validate a completed US firm artifact directory."""
    directory = Path(path).resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"US firm artifact directory is missing: {directory}")
    present = {entry.name for entry in directory.iterdir()}
    if present != _EXPECTED_FILES:
        raise ValueError(
            "US firm artifact file set changed: "
            f"expected {sorted(_EXPECTED_FILES)}, got {sorted(present)}"
        )
    manifest_path = directory / MANIFEST_FILENAME
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ValueError(
            "US firm artifact schema version changed: "
            f"{manifest.get('schema_version')!r}"
        )
    if manifest.get("artifact") != "populace-us-firms":
        raise ValueError("US firm artifact manifest has the wrong artifact name")
    if manifest.get("producer") != "microcosm.build.us_runtime.us_firms":
        raise ValueError("US firm artifact manifest has the wrong producer")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("US firm artifact manifest has no files mapping")
    for filename in (FIRMS_FILENAME, DIAGNOSTICS_FILENAME):
        receipt = files.get(filename)
        if not isinstance(receipt, dict):
            raise ValueError(f"US firm artifact manifest lacks {filename!r}")
        file_path = directory / filename
        actual_sha = sha256_file(file_path)
        if actual_sha != receipt.get("sha256"):
            raise ValueError(
                f"US firm artifact {filename} SHA-256 {actual_sha} does not "
                f"match manifest {receipt.get('sha256')}"
            )
        if file_path.stat().st_size != receipt.get("bytes"):
            raise ValueError(f"US firm artifact {filename} byte size changed")
    table = pq.read_table(directory / FIRMS_FILENAME)
    firms_receipt = files[FIRMS_FILENAME]
    if table.num_rows != firms_receipt.get("rows"):
        raise ValueError("US firm artifact parquet row count changed")
    expected_metadata = {
        b"microcosm.artifact": b"populace-us-firms",
        b"microcosm.schema_version": ARTIFACT_SCHEMA_VERSION.encode(),
        b"microcosm.observation_unit": b"form-5500-plan-sponsor-ein",
        b"microcosm.employment_measure": (
            b"active-plan-participants-end-of-year"
        ),
    }
    metadata = table.schema.metadata or {}
    if any(metadata.get(key) != value for key, value in expected_metadata.items()):
        raise ValueError("US firm artifact parquet metadata is missing or changed")
    diagnostics = json.loads((directory / DIAGNOSTICS_FILENAME).read_text())
    if (
        not isinstance(diagnostics, dict)
        or diagnostics.get("schema_version")
        != "microcosm.us_firms.diagnostics.v1"
        or diagnostics.get("artifact") != "populace-us-firms"
        or not isinstance(diagnostics.get("build_identity_sha256"), str)
    ):
        raise ValueError("US firm artifact diagnostics contract is invalid")
    config_payload = manifest.get("config")
    if not isinstance(config_payload, dict):
        raise ValueError("US firm artifact manifest config is invalid")
    from microcosm.build.us_runtime.us_firms.frame import (
        USFirmBuildConfig,
        validate_us_firm_table,
    )

    normalized_config = dict(config_payload)
    for field in ("weight_bounds", "employment_out_of_scope_sectors"):
        if field in normalized_config:
            normalized_config[field] = tuple(normalized_config[field])
    try:
        config = USFirmBuildConfig(**normalized_config)
    except (TypeError, ValueError) as error:
        raise ValueError("US firm artifact manifest config is invalid") from error
    validate_us_firm_table(table.to_pandas(), config)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_file(manifest_path),
        "rows": table.num_rows,
    }
