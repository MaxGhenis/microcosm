"""Fail-closed acquisition and verification for observed US firm sources.

The publisher URLs are mutable, so names are never evidence of identity.  Raw
downloads are admitted only after their byte length and SHA-256 match the
packaged pins.  ZIP members are selected by one exact name, extracted through
a sibling ``.part`` file, and atomically adopted only after the complete stream
has been hashed.  The hashes and lengths of the derived CSVs are learned at
that point and written to the external staging directory's
``source_manifest.json``.

The local source manifest is not a replacement for the immutable raw pins.  It
is a derivation receipt that lets builders rehash both the raw and staged bytes
and prove that every staged CSV is the exact copy or archive member named by a
pinned source.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
import zipfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import BinaryIO

__all__ = [
    "LOCAL_SOURCE_MANIFEST_FILENAME",
    "MAX_RAW_AND_STAGED_BYTES",
    "SOURCE_PINS_FILENAME",
    "SOURCE_PINS_SHA256",
    "FirmSourcePin",
    "USFirmSourcePins",
    "VerifiedFirmSource",
    "VerifiedUSFirmStaging",
    "load_us_firm_source_pins",
    "stage_us_firm_microdata",
    "us_firm_data_dir",
    "verify_staged_sources",
    "verify_staged_us_firm_microdata",
]

SOURCE_PINS_FILENAME = "source_pins.json"
LOCAL_SOURCE_MANIFEST_FILENAME = "source_manifest.json"
SOURCE_PINS_SHA256 = "cbecce2aa1a9ac859d17a04da41ea8f0bb6f0ff60438e0337d0fe5adaa39f0c6"

# A decimal 3 GB ceiling.  It covers every retained raw download plus every
# expanded/staged CSV, rather than only the compressed network payloads.
MAX_RAW_AND_STAGED_BYTES = 3_000_000_000

_CHUNK_BYTES = 1024 * 1024
_TIMEOUT_SECONDS = 180.0
_USER_AGENT = "PolicyEngine-Microcosm/0.1 (US firm source staging)"
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_PIN_FIELDS = {
    "key",
    "raw_filename",
    "sha256",
    "size_bytes",
    "staged_filename",
    "url",
    "zip_member",
}
_LOCAL_MANIFEST_FIELDS = {
    "aggregate_limit_bytes",
    "aggregate_raw_plus_staged_size_bytes",
    "aggregate_raw_size_bytes",
    "aggregate_staged_size_bytes",
    "collection",
    "schema_version",
    "source_pins_sha256",
    "sources",
    "verified_at_utc",
}

_Response = AbstractContextManager[BinaryIO]
_Opener = Callable[[urllib.request.Request], _Response]
_Clock = Callable[[], datetime]


@dataclass(frozen=True)
class FirmSourcePin:
    """Immutable identity and staging transform for one raw source."""

    key: str
    url: str
    raw_filename: str
    sha256: str
    size_bytes: int
    staged_filename: str
    zip_member: str | None


@dataclass(frozen=True)
class USFirmSourcePins:
    """The complete packaged raw-source declaration."""

    schema_version: int
    collection: str
    pin_recorded_on: str
    sources: tuple[FirmSourcePin, ...]
    manifest_sha256: str

    def source(self, key: str) -> FirmSourcePin:
        """Return the unique source pin named by ``key``."""

        for source in self.sources:
            if source.key == key:
                return source
        raise KeyError(key)


@dataclass(frozen=True)
class VerifiedFirmSource:
    """Paths and identities admitted by the builder-facing verifier."""

    key: str
    raw_path: Path
    staged_path: Path
    raw_size_bytes: int
    raw_sha256: str
    staged_size_bytes: int
    staged_sha256: str
    retrieved_at_utc: str | None


@dataclass(frozen=True)
class VerifiedUSFirmStaging:
    """A fully rehashed external US firm source staging directory."""

    root: Path
    manifest_path: Path
    manifest_sha256: str
    source_pins_sha256: str
    aggregate_raw_plus_staged_size_bytes: int
    sources: tuple[VerifiedFirmSource, ...]

    def source(self, key: str) -> VerifiedFirmSource:
        """Return the verified source named by ``key``."""

        for source in self.sources:
            if source.key == key:
                return source
        raise KeyError(key)

    def staged_path(self, key: str) -> Path:
        """Return the verified staged CSV path for ``key``."""

        return self.source(key).staged_path


def us_firm_data_dir(path: str | Path | None = None) -> Path:
    """Resolve the external source directory without creating it."""

    if path is not None:
        return Path(path).expanduser()
    configured = os.environ.get("MICROCOSM_US_FIRM_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "PolicyEngine" / "firm-data"


def load_us_firm_source_pins(path: str | Path | None = None) -> USFirmSourcePins:
    """Load and strictly validate the packaged source pins.

    A caller-supplied path is supported for manifest validation tooling.  The
    packaged resource additionally has an in-code digest fence, so changing a
    pin requires an explicit reviewed change to both declarations.
    """

    manifest_path = (
        Path(path)
        if path is not None
        else Path(__file__).with_name(SOURCE_PINS_FILENAME)
    )
    raw_bytes = manifest_path.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    if path is None and digest != SOURCE_PINS_SHA256:
        raise ValueError(
            "Packaged US firm source pins hash mismatch: "
            f"expected {SOURCE_PINS_SHA256}, got {digest}. Pin changes must be "
            "reviewed and the in-code digest updated deliberately."
        )
    try:
        raw = json.loads(raw_bytes)
    except json.JSONDecodeError as error:
        raise ValueError("US firm source pins are not valid JSON.") from error
    if not isinstance(raw, dict):
        raise ValueError("US firm source pins must be a JSON object.")
    expected_fields = {
        "collection",
        "pin_recorded_on",
        "schema_version",
        "sources",
    }
    _require_exact_fields(raw, expected_fields, label="US firm source pins")
    if not isinstance(raw["sources"], list):
        raise ValueError("US firm source pins 'sources' must be a JSON list.")
    sources: list[FirmSourcePin] = []
    for index, item in enumerate(raw["sources"]):
        if not isinstance(item, dict):
            raise ValueError(f"US firm source pin {index} must be a JSON object.")
        _require_exact_fields(item, _PIN_FIELDS, label=f"US firm source pin {index}")
        sources.append(FirmSourcePin(**item))
    pins = USFirmSourcePins(
        schema_version=raw["schema_version"],
        collection=raw["collection"],
        pin_recorded_on=raw["pin_recorded_on"],
        sources=tuple(sources),
        manifest_sha256=digest,
    )
    _validate_pins(pins)
    return pins


def stage_us_firm_microdata(
    data_dir: str | Path | None = None,
    *,
    pins: USFirmSourcePins | None = None,
    opener: _Opener | None = None,
    clock: _Clock | None = None,
    chunk_bytes: int = _CHUNK_BYTES,
    max_total_bytes: int = MAX_RAW_AND_STAGED_BYTES,
) -> VerifiedUSFirmStaging:
    """Download, authenticate, derive, and manifest all pinned sources.

    The aggregate ceiling may be lowered by tests or operators, but cannot be
    raised above the lane's 3 GB safety boundary.
    """

    source_pins = pins or load_us_firm_source_pins()
    _validate_pins(source_pins)
    _validate_runtime_limits(chunk_bytes, max_total_bytes)
    raw_total = sum(source.size_bytes for source in source_pins.sources)
    if raw_total > max_total_bytes:
        raise ValueError(
            "Pinned US firm raw sources alone exceed the 3 GB staging ceiling: "
            f"{raw_total} > {max_total_bytes} bytes. Nothing was downloaded."
        )

    root = us_firm_data_dir(data_dir)
    raw_root = root / "raw"
    root.mkdir(parents=True, exist_ok=True)
    raw_root.mkdir(parents=True, exist_ok=True)
    timestamp = _utc_timestamp(clock or _now_utc)
    previous = _load_previous_retrievals(root, source_pins)

    if opener is None:

        def open_url(request: urllib.request.Request) -> _Response:
            return urllib.request.urlopen(  # noqa: S310
                request,
                timeout=_TIMEOUT_SECONDS,
            )

    else:
        open_url = opener

    raw_receipts: dict[str, dict[str, object]] = {}
    raw_paths: dict[str, Path] = {}
    for source in source_pins.sources:
        raw_path = raw_root / source.raw_filename
        downloaded = _ensure_raw_source(
            source,
            raw_path,
            opener=open_url,
            chunk_bytes=chunk_bytes,
        )
        raw_paths[source.key] = raw_path
        previous_retrieved_at = previous.get((source.key, source.sha256))
        if downloaded:
            retrieved_at: str | None = timestamp
            retrieval_note = "Downloaded and verified against the immutable raw pin."
        elif previous_retrieved_at is not None:
            retrieved_at = previous_retrieved_at
            retrieval_note = (
                "Verified existing bytes; retrieval time preserved from a previous "
                "manifest carrying the same raw SHA-256."
            )
        else:
            retrieved_at = None
            retrieval_note = (
                "Verified existing bytes; original retrieval time is unavailable."
            )
        raw_receipts[source.key] = {
            "path": f"raw/{source.raw_filename}",
            "retrieval_note": retrieval_note,
            "retrieved_at_utc": retrieved_at,
            "sha256": source.sha256,
            "size_bytes": source.size_bytes,
            "verified_at_utc": timestamp,
        }

    zip_members: dict[str, zipfile.ZipInfo] = {}
    staged_total = 0
    for source in source_pins.sources:
        if source.zip_member is None:
            staged_total += source.size_bytes
            continue
        info = _exact_zip_member(raw_paths[source.key], source.zip_member, source.key)
        zip_members[source.key] = info
        staged_total += info.file_size
    projected_total = raw_total + staged_total
    if projected_total > max_total_bytes:
        raise ValueError(
            "Pinned US firm raw and expanded files exceed the 3 GB staging "
            f"ceiling: {projected_total} > {max_total_bytes} bytes. Raw files "
            "were authenticated, but no staged CSV was written."
        )

    source_rows: list[dict[str, object]] = []
    for source in source_pins.sources:
        staged_path = root / source.staged_filename
        if source.zip_member is None:
            staged_size, staged_sha = _copy_to_staged(
                raw_paths[source.key],
                staged_path,
                chunk_bytes=chunk_bytes,
            )
            transform: dict[str, object] = {"kind": "exact_copy"}
        else:
            staged_size, staged_sha = _extract_to_staged(
                raw_paths[source.key],
                zip_members[source.key],
                staged_path,
                chunk_bytes=chunk_bytes,
            )
            transform = {
                "kind": "extract_exact_zip_member",
                "zip_member": source.zip_member,
            }
        source_rows.append(
            {
                "key": source.key,
                "raw": raw_receipts[source.key],
                "staged": {
                    "path": source.staged_filename,
                    "sha256": staged_sha,
                    "size_bytes": staged_size,
                },
                "transform": transform,
                "url": source.url,
            }
        )

    manifest = {
        "aggregate_limit_bytes": max_total_bytes,
        "aggregate_raw_plus_staged_size_bytes": projected_total,
        "aggregate_raw_size_bytes": raw_total,
        "aggregate_staged_size_bytes": staged_total,
        "collection": source_pins.collection,
        "schema_version": 1,
        "source_pins_sha256": source_pins.manifest_sha256,
        "sources": source_rows,
        "verified_at_utc": timestamp,
    }
    _atomic_write_json(root / LOCAL_SOURCE_MANIFEST_FILENAME, manifest)
    return verify_staged_us_firm_microdata(
        root,
        pins=source_pins,
        max_total_bytes=max_total_bytes,
        chunk_bytes=chunk_bytes,
    )


def verify_staged_us_firm_microdata(
    data_dir: str | Path | None = None,
    *,
    pins: USFirmSourcePins | None = None,
    max_total_bytes: int = MAX_RAW_AND_STAGED_BYTES,
    chunk_bytes: int = _CHUNK_BYTES,
) -> VerifiedUSFirmStaging:
    """Rehash the local manifest and every raw and staged source.

    This is the builder-facing trust boundary.  A filename match, a manifest
    claim, or a previously successful staging run is never sufficient on its
    own.  For ZIP inputs the verifier also rehashes the exact member directly
    from the pinned archive and compares it with the staged file.
    """

    source_pins = pins or load_us_firm_source_pins()
    _validate_pins(source_pins)
    _validate_runtime_limits(chunk_bytes, max_total_bytes)
    root = us_firm_data_dir(data_dir)
    manifest_path = root / LOCAL_SOURCE_MANIFEST_FILENAME
    try:
        manifest_bytes = manifest_path.read_bytes()
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"US firm source manifest is missing at {manifest_path}; run "
            "tools/stage_us_firm_microdata.py first."
        ) from error
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    try:
        manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as error:
        raise ValueError("US firm local source manifest is not valid JSON.") from error
    if not isinstance(manifest, dict):
        raise ValueError("US firm local source manifest must be a JSON object.")
    _require_exact_fields(
        manifest,
        _LOCAL_MANIFEST_FIELDS,
        label="US firm local source manifest",
    )
    if manifest["schema_version"] != 1:
        raise ValueError(
            "Unsupported US firm local source manifest schema version "
            f"{manifest['schema_version']!r}."
        )
    if manifest["collection"] != source_pins.collection:
        raise ValueError(
            "US firm local source manifest collection does not match pins."
        )
    if manifest["source_pins_sha256"] != source_pins.manifest_sha256:
        raise ValueError(
            "US firm local source manifest was derived from different source pins."
        )
    if manifest["aggregate_limit_bytes"] != max_total_bytes:
        raise ValueError(
            "US firm local source manifest uses an unexpected aggregate byte "
            f"ceiling: {manifest['aggregate_limit_bytes']!r} != {max_total_bytes}."
        )
    _validate_timestamp(manifest["verified_at_utc"], "verified_at_utc")
    rows = manifest["sources"]
    if not isinstance(rows, list):
        raise ValueError("US firm local source manifest 'sources' must be a list.")
    if [row.get("key") if isinstance(row, dict) else None for row in rows] != [
        source.key for source in source_pins.sources
    ]:
        raise ValueError(
            "US firm local source manifest must name every pinned source exactly "
            "once and in pin order."
        )

    verified: list[VerifiedFirmSource] = []
    raw_total = 0
    staged_total = 0
    for source, row in zip(source_pins.sources, rows, strict=True):
        verified_source = _verify_source_row(
            root,
            source,
            row,
            chunk_bytes=chunk_bytes,
        )
        verified.append(verified_source)
        raw_total += verified_source.raw_size_bytes
        staged_total += verified_source.staged_size_bytes
    aggregate_total = raw_total + staged_total
    declared_totals = {
        "aggregate_raw_size_bytes": raw_total,
        "aggregate_staged_size_bytes": staged_total,
        "aggregate_raw_plus_staged_size_bytes": aggregate_total,
    }
    for field, expected in declared_totals.items():
        if manifest[field] != expected:
            raise ValueError(
                f"US firm local source manifest {field} is {manifest[field]!r}, "
                f"but rehashing produced {expected}."
            )
    if aggregate_total > max_total_bytes:
        raise ValueError(
            "US firm staging exceeds the 3 GB raw-plus-expanded ceiling: "
            f"{aggregate_total} > {max_total_bytes} bytes."
        )
    return VerifiedUSFirmStaging(
        root=root,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha,
        source_pins_sha256=source_pins.manifest_sha256,
        aggregate_raw_plus_staged_size_bytes=aggregate_total,
        sources=tuple(verified),
    )


def verify_staged_sources(
    data_dir: str | Path | None = None,
) -> VerifiedUSFirmStaging:
    """Verify the canonical pinned staging receipt for a frame build."""

    return verify_staged_us_firm_microdata(data_dir)


def _validate_pins(pins: USFirmSourcePins) -> None:
    if type(pins.schema_version) is not int or pins.schema_version != 1:
        raise ValueError(
            f"Unsupported US firm source pin schema version {pins.schema_version!r}."
        )
    if pins.collection != "us_firm_microdata":
        raise ValueError("US firm source pin collection must be 'us_firm_microdata'.")
    try:
        parsed_date = date.fromisoformat(pins.pin_recorded_on)
    except (TypeError, ValueError) as error:
        raise ValueError("US firm pin_recorded_on must be an ISO date.") from error
    if parsed_date.isoformat() != pins.pin_recorded_on:
        raise ValueError("US firm pin_recorded_on must be an ISO date.")
    if not _is_sha256(pins.manifest_sha256):
        raise ValueError("US firm source pins manifest SHA-256 is invalid.")
    if not pins.sources:
        raise ValueError("US firm source pins must declare at least one source.")
    keys = [source.key for source in pins.sources]
    if len(keys) != len(set(keys)):
        raise ValueError("US firm source pins contain duplicate keys.")
    raw_names = [source.raw_filename for source in pins.sources]
    staged_names = [source.staged_filename for source in pins.sources]
    if len(raw_names) != len(set(raw_names)):
        raise ValueError("US firm source pins contain duplicate raw filenames.")
    if len(staged_names) != len(set(staged_names)):
        raise ValueError("US firm source pins contain duplicate staged filenames.")
    for source in pins.sources:
        if not isinstance(source.key, str) or not source.key:
            raise ValueError("US firm source keys must be non-empty strings.")
        if not source.url.startswith("https://"):
            raise ValueError(f"US firm source {source.key} URL must use HTTPS.")
        _require_basename(source.raw_filename, f"{source.key} raw filename")
        _require_basename(source.staged_filename, f"{source.key} staged filename")
        if not _is_sha256(source.sha256):
            raise ValueError(f"US firm source {source.key} SHA-256 is invalid.")
        if type(source.size_bytes) is not int or source.size_bytes <= 0:
            raise ValueError(
                f"US firm source {source.key} size_bytes must be a positive integer."
            )
        if source.zip_member is not None:
            _require_basename(source.zip_member, f"{source.key} ZIP member")


def _validate_runtime_limits(chunk_bytes: int, max_total_bytes: int) -> None:
    if type(chunk_bytes) is not int or chunk_bytes <= 0:
        raise ValueError("chunk_bytes must be a positive integer.")
    if (
        type(max_total_bytes) is not int
        or max_total_bytes <= 0
        or max_total_bytes > MAX_RAW_AND_STAGED_BYTES
    ):
        raise ValueError(
            "max_total_bytes must be a positive integer no greater than "
            f"{MAX_RAW_AND_STAGED_BYTES}."
        )


def _ensure_raw_source(
    source: FirmSourcePin,
    destination: Path,
    *,
    opener: _Opener,
    chunk_bytes: int,
) -> bool:
    if destination.is_file():
        actual_size, actual_sha = _file_identity(destination, chunk_bytes=chunk_bytes)
        if actual_size == source.size_bytes and actual_sha == source.sha256:
            return False

    request = urllib.request.Request(source.url, headers={"User-Agent": _USER_AGENT})
    partial = destination.with_name(f"{destination.name}.part")
    partial.unlink(missing_ok=True)
    try:
        digest = hashlib.sha256()
        size = 0
        with opener(request) as response, partial.open("wb") as output:
            for chunk in _iter_chunks(response, chunk_bytes):
                size += len(chunk)
                if size > source.size_bytes:
                    raise ValueError(
                        f"US firm raw source {source.key} exceeded its pinned size "
                        f"of {source.size_bytes} bytes."
                    )
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        actual_sha = digest.hexdigest()
        _require_identity(
            label=f"US firm raw source {source.key}",
            actual_size=size,
            actual_sha256=actual_sha,
            expected_size=source.size_bytes,
            expected_sha256=source.sha256,
        )
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)
    return True


def _exact_zip_member(
    archive_path: Path, member_name: str, key: str
) -> zipfile.ZipInfo:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            matches = [
                info for info in archive.infolist() if info.filename == member_name
            ]
    except zipfile.BadZipFile as error:
        raise ValueError(
            f"Pinned US firm source {key} is not a readable ZIP archive."
        ) from error
    if len(matches) != 1 or matches[0].is_dir():
        found = [info.filename for info in matches]
        raise ValueError(
            f"Pinned US firm source {key} must contain exactly one file named "
            f"{member_name!r}; found {found!r}."
        )
    info = matches[0]
    if info.flag_bits & 0x1:
        raise ValueError(f"Pinned US firm source {key} ZIP member is encrypted.")
    if info.file_size < 0:
        raise ValueError(f"Pinned US firm source {key} ZIP member size is invalid.")
    return info


def _copy_to_staged(
    source_path: Path,
    staged_path: Path,
    *,
    chunk_bytes: int,
) -> tuple[int, str]:
    with source_path.open("rb") as source:
        return _write_staged_stream(
            source,
            staged_path,
            expected_size=source_path.stat().st_size,
            chunk_bytes=chunk_bytes,
        )


def _extract_to_staged(
    archive_path: Path,
    info: zipfile.ZipInfo,
    staged_path: Path,
    *,
    chunk_bytes: int,
) -> tuple[int, str]:
    try:
        with zipfile.ZipFile(archive_path) as archive, archive.open(info) as source:
            return _write_staged_stream(
                source,
                staged_path,
                expected_size=info.file_size,
                chunk_bytes=chunk_bytes,
            )
    except zipfile.BadZipFile as error:
        raise ValueError(
            f"ZIP integrity check failed while extracting {info.filename!r}."
        ) from error


def _write_staged_stream(
    source: BinaryIO,
    destination: Path,
    *,
    expected_size: int,
    chunk_bytes: int,
) -> tuple[int, str]:
    partial = destination.with_name(f"{destination.name}.part")
    partial.unlink(missing_ok=True)
    digest = hashlib.sha256()
    size = 0
    try:
        with partial.open("wb") as output:
            for chunk in _iter_chunks(source, chunk_bytes):
                size += len(chunk)
                if size > expected_size:
                    raise ValueError(
                        f"Staged source {destination.name} exceeded the declared "
                        f"expanded size of {expected_size} bytes."
                    )
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if size != expected_size:
            raise ValueError(
                f"Staged source {destination.name} size mismatch: expected "
                f"{expected_size}, got {size}."
            )
        os.replace(partial, destination)
    finally:
        partial.unlink(missing_ok=True)
    return size, digest.hexdigest()


def _verify_source_row(
    root: Path,
    source: FirmSourcePin,
    row: object,
    *,
    chunk_bytes: int,
) -> VerifiedFirmSource:
    if not isinstance(row, dict):
        raise ValueError(
            f"Local source manifest row for {source.key} must be an object."
        )
    _require_exact_fields(
        row,
        {"key", "raw", "staged", "transform", "url"},
        label=f"local source manifest row {source.key}",
    )
    if row["key"] != source.key or row["url"] != source.url:
        raise ValueError(f"Local source manifest identity differs for {source.key}.")
    raw = row["raw"]
    staged = row["staged"]
    transform = row["transform"]
    if not isinstance(raw, dict) or not isinstance(staged, dict):
        raise ValueError(f"Local source manifest paths for {source.key} are invalid.")
    _require_exact_fields(
        raw,
        {
            "path",
            "retrieval_note",
            "retrieved_at_utc",
            "sha256",
            "size_bytes",
            "verified_at_utc",
        },
        label=f"local raw receipt {source.key}",
    )
    _require_exact_fields(
        staged,
        {"path", "sha256", "size_bytes"},
        label=f"local staged receipt {source.key}",
    )
    expected_transform = (
        {"kind": "exact_copy"}
        if source.zip_member is None
        else {
            "kind": "extract_exact_zip_member",
            "zip_member": source.zip_member,
        }
    )
    if transform != expected_transform:
        raise ValueError(f"Local source manifest transform differs for {source.key}.")
    if raw["path"] != f"raw/{source.raw_filename}":
        raise ValueError(f"Local raw path differs for {source.key}.")
    if staged["path"] != source.staged_filename:
        raise ValueError(f"Local staged path differs for {source.key}.")
    if raw["sha256"] != source.sha256 or raw["size_bytes"] != source.size_bytes:
        raise ValueError(f"Local raw identity differs from the pin for {source.key}.")
    if not isinstance(raw["retrieval_note"], str) or not raw["retrieval_note"]:
        raise ValueError(f"Local retrieval note is missing for {source.key}.")
    retrieved_at = raw["retrieved_at_utc"]
    if retrieved_at is not None:
        _validate_timestamp(retrieved_at, f"{source.key}.retrieved_at_utc")
    _validate_timestamp(raw["verified_at_utc"], f"{source.key}.verified_at_utc")
    if type(staged["size_bytes"]) is not int or staged["size_bytes"] < 0:
        raise ValueError(f"Local staged size is invalid for {source.key}.")
    if not _is_sha256(staged["sha256"]):
        raise ValueError(f"Local staged SHA-256 is invalid for {source.key}.")

    raw_path = root / "raw" / source.raw_filename
    staged_path = root / source.staged_filename
    raw_size, raw_sha = _file_identity(raw_path, chunk_bytes=chunk_bytes)
    _require_identity(
        label=f"US firm raw source {source.key}",
        actual_size=raw_size,
        actual_sha256=raw_sha,
        expected_size=source.size_bytes,
        expected_sha256=source.sha256,
    )
    staged_size, staged_sha = _file_identity(staged_path, chunk_bytes=chunk_bytes)
    _require_identity(
        label=f"US firm staged source {source.key}",
        actual_size=staged_size,
        actual_sha256=staged_sha,
        expected_size=staged["size_bytes"],
        expected_sha256=staged["sha256"],
    )
    if source.zip_member is None:
        if staged_size != raw_size or staged_sha != raw_sha:
            raise ValueError(
                f"US firm staged source {source.key} is not an exact raw-byte copy."
            )
    else:
        info = _exact_zip_member(raw_path, source.zip_member, source.key)
        with zipfile.ZipFile(raw_path) as archive, archive.open(info) as member:
            member_size, member_sha = _stream_identity(member, chunk_bytes=chunk_bytes)
        if member_size != staged_size or member_sha != staged_sha:
            raise ValueError(
                f"US firm staged source {source.key} differs from its exact pinned "
                "ZIP member."
            )
    return VerifiedFirmSource(
        key=source.key,
        raw_path=raw_path,
        staged_path=staged_path,
        raw_size_bytes=raw_size,
        raw_sha256=raw_sha,
        staged_size_bytes=staged_size,
        staged_sha256=staged_sha,
        retrieved_at_utc=retrieved_at,
    )


def _load_previous_retrievals(
    root: Path,
    pins: USFirmSourcePins,
) -> dict[tuple[str, str], str]:
    manifest_path = root / LOCAL_SOURCE_MANIFEST_FILENAME
    if not manifest_path.exists():
        return {}
    try:
        manifest = json.loads(manifest_path.read_bytes())
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Existing US firm source manifest at {manifest_path} is invalid; "
            "refusing to overwrite provenance silently."
        ) from error
    if not isinstance(manifest, dict):
        raise ValueError("Existing US firm source manifest must be a JSON object.")
    if manifest.get("source_pins_sha256") != pins.manifest_sha256:
        return {}
    rows = manifest.get("sources")
    if not isinstance(rows, list):
        raise ValueError("Existing US firm source manifest sources must be a list.")
    retrieved: dict[tuple[str, str], str] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("raw"), dict):
            raise ValueError("Existing US firm source manifest has an invalid row.")
        raw = row["raw"]
        key = row.get("key")
        sha = raw.get("sha256")
        timestamp = raw.get("retrieved_at_utc")
        if not isinstance(key, str) or not isinstance(sha, str):
            raise ValueError("Existing US firm source manifest has invalid identity.")
        if timestamp is not None:
            _validate_timestamp(timestamp, f"{key}.retrieved_at_utc")
            retrieved[(key, sha)] = timestamp
    return retrieved


def _atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    content = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    partial = path.with_name(f"{path.name}.part")
    partial.unlink(missing_ok=True)
    try:
        with partial.open("wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def _file_identity(path: Path, *, chunk_bytes: int) -> tuple[int, str]:
    try:
        with path.open("rb") as source:
            return _stream_identity(source, chunk_bytes=chunk_bytes)
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Required US firm source file is missing: {path}"
        ) from error


def _stream_identity(source: BinaryIO, *, chunk_bytes: int) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    for chunk in _iter_chunks(source, chunk_bytes):
        size += len(chunk)
        digest.update(chunk)
    return size, digest.hexdigest()


def _iter_chunks(source: BinaryIO, chunk_bytes: int) -> Iterator[bytes]:
    while chunk := source.read(chunk_bytes):
        yield chunk


def _require_identity(
    *,
    label: str,
    actual_size: int,
    actual_sha256: str,
    expected_size: object,
    expected_sha256: object,
) -> None:
    if actual_size != expected_size or actual_sha256 != expected_sha256:
        raise ValueError(
            f"{label} identity mismatch: expected {expected_sha256} "
            f"({expected_size} bytes), got {actual_sha256} ({actual_size} bytes)."
        )


def _require_exact_fields(
    raw: Mapping[str, object],
    expected: set[str],
    *,
    label: str,
) -> None:
    missing = sorted(expected - raw.keys())
    extra = sorted(raw.keys() - expected)
    if missing or extra:
        raise ValueError(f"{label} fields differ: missing={missing}, extra={extra}.")


def _require_basename(value: object, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).name != value
        or value in {".", ".."}
    ):
        raise ValueError(f"{label} must be a non-empty basename.")


def _validate_timestamp(value: object, label: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a timezone-aware ISO timestamp.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} must be a timezone-aware ISO timestamp.") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must be a timezone-aware ISO timestamp.")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _utc_timestamp(clock: _Clock) -> str:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("US firm staging clock must return a timezone-aware datetime.")
    return value.astimezone(UTC).isoformat(timespec="seconds")


def _now_utc() -> datetime:
    return datetime.now(UTC)
