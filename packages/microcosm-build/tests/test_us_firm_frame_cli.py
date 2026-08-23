"""Focused tests for the fail-closed US firm artifact build command."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

CLI = Path(__file__).resolve().parents[3] / "tools" / "build_us_firm_frame.py"
REAL_DATA_DIR = Path(
    os.environ.get(
        "MICROCOSM_US_FIRM_DATA_DIR",
        Path.home() / "PolicyEngine" / "firm-data",
    )
).expanduser()


def _run(*arguments: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _load_cli_module():
    spec = importlib.util.spec_from_file_location("build_us_firm_frame_probe", CLI)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {CLI}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _install_build_stubs(module, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    source = SimpleNamespace(
        key="form5500_2023",
        raw_sha256="01" * 32,
        raw_size_bytes=101,
        retrieved_at_utc=None,
        staged_sha256="02" * 32,
        staged_size_bytes=202,
    )
    staging = SimpleNamespace(
        root=tmp_path / "external-source-data",
        manifest_sha256="03" * 32,
        source_pins_sha256="04" * 32,
        aggregate_raw_plus_staged_size_bytes=303,
        sources=(source,),
    )
    sponsors = object()
    targets = SimpleNamespace(source_mode="migration_harness")
    bds = object()
    result = SimpleNamespace(diagnostics={"build_identity_sha256": "05" * 32})
    artifact_dir = (tmp_path / "artifact").resolve()
    paths = SimpleNamespace(
        directory=artifact_dir,
        firms=artifact_dir / "firms.parquet",
        diagnostics=artifact_dir / "diagnostics.json",
        manifest=artifact_dir / "manifest.json",
    )
    calls: dict[str, object] = {}

    def fake_read_sponsors(year, *, data_dir):
        calls["form_reader"] = (year, data_dir)
        return sponsors

    def fake_build(donors, target_receipt, **kwargs):
        calls["build"] = (donors, target_receipt, kwargs)
        return result

    def fake_write(build_result, output_dir):
        calls["write"] = (build_result, output_dir)
        return paths

    deps = module._Dependencies(
        verify_staging=lambda data_dir: staging,
        read_sponsors=fake_read_sponsors,
        load_susb_targets=lambda: targets,
        load_bds_validation=lambda *, year: calls.setdefault("bds_year", year)
        and bds,
        read_ita=lambda *args, **kwargs: calls.setdefault("osha_reader", args),
        apply_osha_quality_rule=lambda *args, **kwargs: calls.setdefault(
            "osha_quality", (args, kwargs)
        ),
        make_osha_reference=lambda *args: calls.setdefault("osha_reference", args),
        build_config=lambda *, source_year: SimpleNamespace(source_year=source_year),
        build_frame=fake_build,
        write_artifact=fake_write,
        verify_artifact=lambda directory: {
            "manifest_sha256": "06" * 32,
            "rows": 7,
        },
    )
    monkeypatch.setattr(module, "_verify_staging_only", lambda data_dir: staging)
    monkeypatch.setattr(module, "_load_dependencies", lambda: deps)
    return deps, calls, staging, sponsors, targets, bds, result, paths


def test_cli_requires_explicit_susb_migration_harness(tmp_path: Path):
    out_dir = tmp_path / "artifact"
    result = _run("--data-dir", str(tmp_path / "sources"), "--out-dir", str(out_dir))

    assert result.returncode == 2
    assert "--use-susb-migration-harness" in result.stderr
    assert not out_dir.exists()


def test_cli_fails_cleanly_when_pinned_staging_is_missing(tmp_path: Path):
    out_dir = tmp_path / "artifact"
    result = _run(
        "--data-dir",
        str(tmp_path / "missing-sources"),
        "--out-dir",
        str(out_dir),
        "--use-susb-migration-harness",
    )

    assert result.returncode == 1
    assert "source manifest is missing" in result.stderr
    assert "stage_us_firm_microdata.py" in result.stderr
    assert not out_dir.exists()


def test_cli_does_not_read_osha_without_an_explicit_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    module = _load_cli_module()
    _, calls, staging, sponsors, targets, bds, result, paths = _install_build_stubs(
        module, monkeypatch, tmp_path
    )
    exit_code = module.main(
        [
            "--data-dir",
            str(tmp_path / "external-source-data"),
            "--out-dir",
            str(tmp_path / "artifact"),
            "--use-susb-migration-harness",
        ]
    )

    assert exit_code == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["target_source_mode"] == "migration_harness"
    assert receipt["osha_reference"] == {
        "enabled": False,
        "max_employees": None,
    }
    assert calls["form_reader"] == (module.FORM_5500_YEAR, staging.root)
    assert calls["bds_year"] == 2022
    assert calls["write"] == (result, tmp_path / "artifact")
    _, _, build_options = calls["build"]
    assert build_options["osha_reference"] is None
    assert build_options["bds_validation"] is bds
    assert build_options["config"].source_year == module.FORM_5500_YEAR
    assert build_options["source_provenance"] is staging
    assert receipt["artifact_directory"] == str(paths.directory)
    assert receipt["rows"] == 7
    assert calls["build"][0:2] == (sponsors, targets)
    assert "osha_reader" not in calls


def test_cli_reads_osha_only_after_receiving_the_explicit_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    module = _load_cli_module()
    deps, calls, staging, sponsors, _, _, _, _ = _install_build_stubs(
        module, monkeypatch, tmp_path
    )
    raw_osha = object()
    retained_osha = object()
    reference = {"status": "computed", "matched_eins": 3}

    def fake_read_ita(year, *, data_dir):
        calls["osha_reader"] = (year, data_dir)
        return raw_osha

    def fake_quality_rule(frame, *, max_employees):
        calls["osha_quality"] = (frame, max_employees)
        return retained_osha

    def fake_reference(form_sponsors, establishments):
        calls["osha_reference"] = (form_sponsors, establishments)
        return reference

    deps = replace(
        deps,
        read_ita=fake_read_ita,
        apply_osha_quality_rule=fake_quality_rule,
        make_osha_reference=fake_reference,
    )

    receipt = module._build(
        SimpleNamespace(
            data_dir=staging.root,
            out_dir=tmp_path / "artifact",
            use_susb_migration_harness=True,
            osha_max_employees=12_345,
        ),
        dependencies=deps,
    )

    assert calls["osha_reader"] == (module.OSHA_ITA_YEAR, staging.root)
    assert calls["osha_quality"] == (raw_osha, 12_345)
    assert calls["osha_reference"] == (sponsors, retained_osha)
    assert calls["build"][2]["osha_reference"] == reference
    assert receipt["osha_reference"] == {
        "enabled": True,
        "max_employees": 12_345,
    }


@pytest.mark.skipif(
    not (REAL_DATA_DIR / "source_manifest.json").is_file(),
    reason="Pinned US firm source staging is not available",
)
def test_cli_builds_and_verifies_real_staged_artifact(tmp_path: Path):
    out_dir = tmp_path / "populace-us-firms"
    result = _run(
        "--data-dir",
        str(REAL_DATA_DIR),
        "--out-dir",
        str(out_dir),
        "--use-susb-migration-harness",
        timeout=1_800,
    )

    assert result.returncode == 0, result.stderr
    assert {path.name for path in out_dir.iterdir()} == {
        "diagnostics.json",
        "firms.parquet",
        "manifest.json",
    }
    receipt = json.loads(result.stdout)
    manifest = json.loads((out_dir / "manifest.json").read_text())
    diagnostics = json.loads((out_dir / "diagnostics.json").read_text())
    assert receipt["target_source_mode"] == "migration_harness"
    assert receipt["rows"] == manifest["files"]["firms.parquet"]["rows"]
    assert receipt["build_identity_sha256"] == diagnostics["build_identity_sha256"]
    assert receipt["osha_reference"] == {
        "enabled": False,
        "max_employees": None,
    }
