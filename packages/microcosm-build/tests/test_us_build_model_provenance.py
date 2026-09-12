"""Small artifact fixtures; these tests never load or simulate a population."""

import argparse
import base64
import csv
import hashlib
import io
import json
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from microcosm.build import model_artifact


@pytest.fixture
def artifacts(tmp_path, monkeypatch):
    version = "8.4.2rc1"
    prefix = f"policyengine_us-{version}.dist-info/"
    members = {
        "policyengine_us/__init__.py": b"# fixture model\n",
        "policyengine_us/parameters/example.yaml": b"value: 1\n",
        prefix + "METADATA": f"Name: policyengine-us\nVersion: {version}\n".encode(),
        prefix + "WHEEL": b"Wheel-Version: 1.0\nGenerator: hatchling 1.32.0\n",
    }
    wheel = tmp_path / f"policyengine_us-{version}-py3-none-any.whl"
    record_path = prefix + "RECORD"

    def write_wheel(*, record=True):
        if record:
            output = io.StringIO()
            writer = csv.writer(output)
            for name, value in members.items():
                if name == record_path:
                    continue
                digest = (
                    base64.urlsafe_b64encode(hashlib.sha256(value).digest())
                    .decode()
                    .rstrip("=")
                )
                writer.writerow((name, f"sha256={digest}", str(len(value))))
            writer.writerow((record_path, "", ""))
            members[record_path] = output.getvalue().encode()
        with ZipFile(wheel, "w") as archive:
            for name, value in members.items():
                archive.writestr(name, value)

    write_wheel()
    install = tmp_path / "installed"
    for name, value in members.items():
        path = install / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    # Normal installer changes must not invalidate an otherwise exact install.
    (install / record_path).write_text("installer-rewritten RECORD\n")
    (install / prefix / "INSTALLER").write_text("uv\n")
    pycache = install / "policyengine_us/__pycache__/__init__.cpython-314.pyc"
    pycache.parent.mkdir()
    pycache.write_bytes(b"compiled fixture")
    dist = SimpleNamespace(
        version=version,
        locate_file=lambda path: install / path,
        read_text=lambda _name: None,
    )
    monkeypatch.setattr(model_artifact.metadata, "distribution", lambda _name: dist)
    monkeypatch.setattr(
        model_artifact.util,
        "find_spec",
        lambda _name: SimpleNamespace(
            origin=str(install / "policyengine_us/__init__.py")
        ),
    )
    receipt = {
        "source_head": "a" * 40,
        "policy_tree": "b" * 40,
        "policy_source_matches_head": True,
        "prepared_version": version,
        "pyproject_sha256": "c" * 64,
        "uv_lock_sha256": "d" * 64,
        "isolated_build_requirements": {"hatchling": "1.32.0"},
        "wheel": {},
    }
    receipt_path = tmp_path / "receipt.json"

    def pin_receipt():
        receipt["wheel"] = {
            "filename": wheel.name,
            "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "size_bytes": wheel.stat().st_size,
        }
        receipt_path.write_text(json.dumps(receipt, sort_keys=True))
        return hashlib.sha256(receipt_path.read_bytes()).hexdigest()

    return SimpleNamespace(
        wheel=wheel,
        receipt_path=receipt_path,
        receipt=receipt,
        digest=pin_receipt(),
        pin_receipt=pin_receipt,
        write_wheel=write_wheel,
        members=members,
        install=install,
        dist=dist,
        prefix=prefix,
    )


def verify(artifacts):
    return model_artifact.verify_build_model(
        artifacts.wheel, artifacts.receipt_path, artifacts.digest
    )


def test_verifies_all_members_and_retains_original_receipt(artifacts, tmp_path):
    verified = verify(artifacts)
    assert verified.identity["version"] == "8.4.2rc1"
    assert verified.identity["source"]["git_commit"] == "a" * 40
    assert verified.identity["wheel"]["member_count"] == len(artifacts.members)
    assert verified.identity["wheel"]["sha256"] == artifacts.receipt["wheel"]["sha256"]
    destination = tmp_path / "evidence"
    verified.copy_receipt(destination)
    copied = destination / model_artifact.BUILD_MODEL_RECEIPT_FILENAME
    assert copied.read_bytes() == artifacts.receipt_path.read_bytes()
    copied.write_text("different evidence")
    with pytest.raises(ValueError, match="replace a different"):
        verified.copy_receipt(destination)


def test_wheel_identity_and_record_use_the_same_byte_snapshot(artifacts, monkeypatch):
    original_reader = model_artifact._wheel_members

    def replace_path_after_capture(path, *, snapshot=None):
        assert snapshot is not None
        path.write_bytes(b"replacement after the authenticated snapshot")
        return original_reader(path, snapshot=snapshot)

    monkeypatch.setattr(model_artifact, "_wheel_members", replace_path_after_capture)
    verified = verify(artifacts)
    assert verified.identity["wheel"]["sha256"] == artifacts.receipt["wheel"]["sha256"]
    assert (
        verified.identity["wheel"]["sha256"]
        != hashlib.sha256(artifacts.wheel.read_bytes()).hexdigest()
    )


def test_verified_wheel_identity_does_not_copy_unverified_receipt_fields(artifacts):
    artifacts.receipt["wheel"]["unverified_claim"] = "unverified"
    artifacts.receipt_path.write_text(json.dumps(artifacts.receipt, sort_keys=True))
    artifacts.digest = hashlib.sha256(artifacts.receipt_path.read_bytes()).hexdigest()
    assert "unverified_claim" not in verify(artifacts).identity["wheel"]


@pytest.mark.parametrize("part", ["receipt", "wheel"])
def test_rejects_changed_pinned_artifact_bytes(artifacts, part):
    path = artifacts.receipt_path if part == "receipt" else artifacts.wheel
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="mismatch|differs"):
        verify(artifacts)


@pytest.mark.parametrize(
    "mutation", ["payload", "missing_row", "bad_size", "duplicate_row"]
)
def test_rejects_invalid_wheel_record_even_with_new_receipt_pin(artifacts, mutation):
    record = artifacts.prefix + "RECORD"
    if mutation == "payload":
        artifacts.members["policyengine_us/parameters/example.yaml"] = b"value: 2\n"
    elif mutation == "missing_row":
        artifacts.members[record] = b"\n".join(
            artifacts.members[record].splitlines()[1:]
        )
    elif mutation == "bad_size":
        rows = list(csv.reader(io.StringIO(artifacts.members[record].decode())))
        rows[0][2] = "999"
        output = io.StringIO()
        csv.writer(output).writerows(rows)
        artifacts.members[record] = output.getvalue().encode()
    else:
        artifacts.members[record] += artifacts.members[record].splitlines(
            keepends=True
        )[0]
    artifacts.write_wheel(record=False)
    artifacts.digest = artifacts.pin_receipt()
    with pytest.raises(ValueError, match="RECORD"):
        verify(artifacts)


@pytest.mark.parametrize(
    "relative",
    [
        "policyengine_us/__init__.py",
        "policyengine_us/parameters/example.yaml",
        "metadata",
    ],
)
def test_rejects_changed_installed_source_parameter_or_metadata(artifacts, relative):
    if relative == "metadata":
        relative = artifacts.prefix + "METADATA"
    (artifacts.install / relative).write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="Installed build-model member"):
        verify(artifacts)


def test_rejects_extra_installed_source_and_import_shadow(artifacts, monkeypatch):
    extra = artifacts.install / "policyengine_us/extra.py"
    extra.write_text("# extra source")
    with pytest.raises(ValueError, match="inventory differs"):
        verify(artifacts)
    extra.unlink()
    monkeypatch.setattr(
        model_artifact.util,
        "find_spec",
        lambda _name: SimpleNamespace(origin="/other/policyengine_us/__init__.py"),
    )
    with pytest.raises(ValueError, match="Importable build-model"):
        verify(artifacts)


@pytest.mark.parametrize(
    "part", ["installed_version", "receipt_version", "generator", "source_commit"]
)
def test_rejects_version_generator_or_source_identity_drift(artifacts, part):
    if part == "installed_version":
        artifacts.dist.version = "8.4.2"
    elif part == "receipt_version":
        artifacts.receipt["prepared_version"] = "8.4.2"
    elif part == "generator":
        artifacts.receipt["isolated_build_requirements"]["hatchling"] = "1.31.0"
    else:
        artifacts.receipt["source_head"] = "unknown"
    artifacts.digest = artifacts.pin_receipt()
    with pytest.raises(ValueError):
        verify(artifacts)


def test_argument_trio_is_all_or_none(artifacts):
    parser = argparse.ArgumentParser()
    model_artifact.add_build_model_arguments(parser)
    assert model_artifact.build_model_from_args(parser.parse_args([])) is None
    options = [
        ["--build-model-wheel", str(artifacts.wheel)],
        ["--build-model-receipt", str(artifacts.receipt_path)],
        ["--build-model-receipt-sha256", artifacts.digest],
    ]
    for mask in range(1, 7):
        argv = [
            value
            for index, option in enumerate(options)
            if mask & (1 << index)
            for value in option
        ]
        with pytest.raises(ValueError, match="required together"):
            model_artifact.build_model_from_args(parser.parse_args(argv))
    args = parser.parse_args([value for option in options for value in option])
    assert model_artifact.build_model_from_args(args).identity["version"] == "8.4.2rc1"
