"""Bind an installed US build model to an operator-authenticated wheel receipt.

This is local artifact verification. Authentication of the supplied receipt
belongs to the operator; this module makes no independent GitHub trust claim.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from email.parser import BytesParser
from importlib import metadata, util
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

BUILD_MODEL_RECEIPT_FILENAME = "build_model_receipt.json"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: object, length: int, owner: str) -> str:
    if (
        not isinstance(value, str)
        or re.fullmatch(f"[0-9a-f]{{{length}}}", value) is None
    ):
        raise ValueError(f"{owner} must be a {length}-character lowercase hex digest")
    return value


def add_build_model_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--build-model-wheel", type=Path)
    parser.add_argument("--build-model-receipt", type=Path)
    parser.add_argument(
        "--build-model-receipt-sha256",
        help="Operator-authenticated SHA-256 of the exact model build receipt.",
    )


def check_build_model_arguments(args: argparse.Namespace) -> None:
    values = tuple(
        getattr(args, name, None)
        for name in (
            "build_model_wheel",
            "build_model_receipt",
            "build_model_receipt_sha256",
        )
    )
    if any(value is not None for value in values) and not all(
        value is not None for value in values
    ):
        raise ValueError(
            "--build-model-wheel, --build-model-receipt, and "
            "--build-model-receipt-sha256 are required together"
        )


@dataclass(frozen=True)
class VerifiedBuildModel:
    identity: dict[str, object]
    receipt_bytes: bytes

    def copy_receipt(self, directory: Path) -> None:
        """Retain the verified original bytes without replacing other evidence."""
        destination = Path(directory) / BUILD_MODEL_RECEIPT_FILENAME
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != self.receipt_bytes:
                raise ValueError("Refusing to replace a different build-model receipt")
            return
        destination.write_bytes(self.receipt_bytes)


def build_model_from_args(args: argparse.Namespace) -> VerifiedBuildModel | None:
    check_build_model_arguments(args)
    if getattr(args, "build_model_wheel", None) is None:
        return None
    return verify_build_model(
        args.build_model_wheel,
        args.build_model_receipt,
        args.build_model_receipt_sha256,
    )


def _wheel_members(
    path: Path, *, snapshot: bytes | None = None
) -> tuple[dict[str, bytes], str]:
    with ZipFile(
        io.BytesIO(path.read_bytes() if snapshot is None else snapshot)
    ) as wheel:
        names = wheel.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Build-model wheel has duplicate members")
        for name in names:
            parts = PurePosixPath(name).parts
            if (
                name.startswith("/")
                or "\\" in name
                or ".." in parts
                or str(PurePosixPath(name)) != name.rstrip("/")
            ):
                raise ValueError("Build-model wheel has a non-canonical member path")
        members = {
            item.filename: wheel.read(item.filename)
            for item in wheel.infolist()
            if not item.is_dir()
        }
    metadata_paths = [name for name in members if name.endswith(".dist-info/METADATA")]
    if len(metadata_paths) != 1:
        raise ValueError("Build-model wheel must have exactly one METADATA")
    prefix = metadata_paths[0].removesuffix("METADATA")
    record_path = prefix + "RECORD"
    if prefix + "WHEEL" not in members or record_path not in members:
        raise ValueError("Build-model wheel is missing WHEEL or RECORD")
    rows = list(csv.reader(io.StringIO(members[record_path].decode("utf-8"))))
    if any(len(row) != 3 for row in rows):
        raise ValueError("Build-model wheel RECORD has malformed rows")
    if len(rows) != len({row[0] for row in rows}):
        raise ValueError("Build-model wheel RECORD has duplicate rows")
    if {row[0] for row in rows} != set(members):
        raise ValueError("Build-model wheel RECORD inventory differs from its members")
    for name, digest, size in rows:
        if name == record_path:
            if digest or size:
                raise ValueError(
                    "Build-model wheel RECORD must leave its own hash empty"
                )
            continue
        actual = (
            base64.urlsafe_b64encode(hashlib.sha256(members[name]).digest())
            .decode()
            .rstrip("=")
        )
        if digest != f"sha256={actual}" or size != str(len(members[name])):
            raise ValueError(f"Build-model wheel RECORD does not match {name}")
    return members, prefix


def verify_build_model(
    wheel_path: Path,
    receipt_path: Path,
    receipt_sha256: str,
) -> VerifiedBuildModel:
    """Verify every wheel member against RECORD and the actual installed model."""
    wheel_path, receipt_path = Path(wheel_path), Path(receipt_path)
    expected_receipt_sha = _digest(receipt_sha256, 64, "Build-model receipt SHA-256")
    receipt_bytes = receipt_path.read_bytes()
    if _sha256(receipt_bytes) != expected_receipt_sha:
        raise ValueError("Build-model receipt SHA-256 mismatch")
    receipt = json.loads(receipt_bytes)
    if (
        not isinstance(receipt, dict)
        or receipt.get("policy_source_matches_head") is not True
    ):
        raise ValueError("Build-model receipt must attest unchanged policy source")
    source_head = _digest(receipt.get("source_head"), 40, "Build-model source commit")
    policy_tree = _digest(receipt.get("policy_tree"), 40, "Build-model policy tree")
    project_sha = _digest(
        receipt.get("pyproject_sha256"), 64, "Prepared project SHA-256"
    )
    lock_sha = _digest(receipt.get("uv_lock_sha256"), 64, "Prepared lock SHA-256")
    wheel_receipt = receipt.get("wheel")
    if not isinstance(wheel_receipt, dict):
        raise ValueError("Build-model receipt must identify its wheel")
    wheel_bytes = wheel_path.read_bytes()
    wheel_sha = _sha256(wheel_bytes)
    if (
        wheel_receipt.get("sha256") != wheel_sha
        or wheel_receipt.get("filename") != wheel_path.name
        or wheel_receipt.get("size_bytes") != len(wheel_bytes)
    ):
        raise ValueError("Build-model wheel differs from the pinned receipt")
    members, prefix = _wheel_members(wheel_path, snapshot=wheel_bytes)
    package_metadata = BytesParser().parsebytes(members[prefix + "METADATA"])
    name = package_metadata.get_all("Name", [])
    versions = package_metadata.get_all("Version", [])
    if len(name) != 1 or name[0].lower().replace("_", "-") != "policyengine-us":
        raise ValueError("Build-model wheel must identify policyengine-us")
    if len(versions) != 1 or versions[0] != receipt.get("prepared_version"):
        raise ValueError("Build-model wheel version differs from its pinned receipt")
    wheel_metadata = BytesParser().parsebytes(members[prefix + "WHEEL"])
    requirements = receipt.get("isolated_build_requirements", {})
    hatchling = (
        requirements.get("hatchling") if isinstance(requirements, dict) else None
    )
    if (
        not isinstance(hatchling, str)
        or wheel_metadata.get_all("Generator", []) != [f"hatchling {hatchling}"]
        or wheel_metadata.get_all("Wheel-Version", []) != ["1.0"]
    ):
        raise ValueError("Build-model WHEEL metadata differs from its pinned receipt")
    distribution = metadata.distribution("policyengine-us")
    if distribution.version != versions[0]:
        raise ValueError("Installed build-model version differs from the wheel")
    direct_url = distribution.read_text("direct_url.json")
    if direct_url and json.loads(direct_url).get("dir_info", {}).get("editable"):
        raise ValueError(
            "Build-model wheel verification requires a non-editable install"
        )
    for relative, expected in members.items():
        if relative == prefix + "RECORD":
            # Installers mechanically rewrite RECORD and add their own metadata.
            continue
        installed = Path(distribution.locate_file(relative))
        if not installed.is_file() or installed.read_bytes() != expected:
            raise ValueError(
                f"Installed build-model member differs from wheel: {relative}"
            )
    package_root = Path(distribution.locate_file("policyengine_us"))
    installed_members = {
        "policyengine_us/" + path.relative_to(package_root).as_posix()
        for path in package_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    if installed_members != {
        name for name in members if name.startswith("policyengine_us/")
    }:
        raise ValueError(
            "Installed build-model package inventory differs from the wheel"
        )
    imported = util.find_spec("policyengine_us")
    if (
        imported is None
        or imported.origin is None
        or Path(imported.origin).resolve() != (package_root / "__init__.py").resolve()
    ):
        raise ValueError(
            "Importable build-model source differs from the installed wheel"
        )
    member_identity = {
        name: {"sha256": _sha256(contents), "size_bytes": len(contents)}
        for name, contents in sorted(members.items())
    }
    return VerifiedBuildModel(
        identity={
            "schema_version": 1,
            "name": "policyengine-us",
            "version": versions[0],
            "wheel": {
                "filename": wheel_path.name,
                "sha256": wheel_sha,
                "size_bytes": len(wheel_bytes),
                "members_sha256": _sha256(
                    json.dumps(
                        member_identity, sort_keys=True, separators=(",", ":")
                    ).encode()
                ),
                "member_count": len(members),
            },
            "source": {"git_commit": source_head, "policy_tree": policy_tree},
            "prepared_pyproject_sha256": project_sha,
            "prepared_uv_lock_sha256": lock_sha,
            "receipt": {
                "path": BUILD_MODEL_RECEIPT_FILENAME,
                "sha256": expected_receipt_sha,
            },
            "verification": "operator_pinned_receipt_and_installed_wheel_members",
        },
        receipt_bytes=receipt_bytes,
    )
