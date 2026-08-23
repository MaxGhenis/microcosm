from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from microcosm.build.us_runtime.us_firms.staging import (
    MAX_RAW_AND_STAGED_BYTES,
    SOURCE_PINS_SHA256,
    FirmSourcePin,
    USFirmSourcePins,
    load_us_firm_source_pins,
    stage_us_firm_microdata,
    us_firm_data_dir,
    verify_staged_us_firm_microdata,
)

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "tools" / "stage_us_firm_microdata.py"
FIXED_TIME = datetime(2026, 8, 23, 10, 30, tzinfo=UTC)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _archive(member: str, payload: bytes, *, actual_member: str | None = None) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(actual_member or member, payload)
    return output.getvalue()


def _pins(
    sources: list[tuple[str, str, bytes, bytes | None]],
) -> tuple[USFirmSourcePins, dict[str, bytes]]:
    """Build synthetic pins from key, staged name, raw bytes, ZIP payload."""

    pins: list[FirmSourcePin] = []
    downloads: dict[str, bytes] = {}
    for key, staged_name, raw, member_payload in sources:
        url = f"https://example.test/{key}.source"
        zip_member = staged_name if member_payload is not None else None
        pins.append(
            FirmSourcePin(
                key=key,
                url=url,
                raw_filename=f"{key}.source",
                sha256=_sha(raw),
                size_bytes=len(raw),
                staged_filename=staged_name,
                zip_member=zip_member,
            )
        )
        downloads[url] = raw
    return (
        USFirmSourcePins(
            schema_version=1,
            collection="us_firm_microdata",
            pin_recorded_on="2026-08-11",
            sources=tuple(pins),
            manifest_sha256="ab" * 32,
        ),
        downloads,
    )


class BytesOpener:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads
        self.requests: list[str] = []

    def __call__(self, request):
        self.requests.append(request.full_url)
        return io.BytesIO(self.payloads[request.full_url])


def test_packaged_pins_are_exact_and_below_raw_ceiling() -> None:
    pins = load_us_firm_source_pins()

    assert pins.manifest_sha256 == SOURCE_PINS_SHA256
    assert [source.key for source in pins.sources] == [
        "form5500_2023",
        "form5500_sf_2023",
        "osha_ita_2025",
    ]
    assert [source.size_bytes for source in pins.sources] == [
        29_317_144,
        131_009_006,
        84_600_899,
    ]
    assert sum(source.size_bytes for source in pins.sources) == 244_927_049
    assert sum(source.size_bytes for source in pins.sources) < (
        MAX_RAW_AND_STAGED_BYTES
    )
    assert pins.source("form5500_2023").sha256 == (
        "cc89e54c57cb6549ab23842bccc6f4ad20e531ebc42a394732359f6a42b7f595"
    )
    assert pins.source("form5500_sf_2023").sha256 == (
        "fa9ff9b15f0eef01dba7533121f33dfa5cc8befca9ce885db9b97063b32fb828"
    )
    assert pins.source("osha_ita_2025").sha256 == (
        "986f7025c54599c5d022fc472181a013e231b2df0c6e6b8ef5f4f9192d1ff50a"
    )


def test_data_dir_uses_explicit_then_environment_then_external_default(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("MICROCOSM_US_FIRM_DATA_DIR", str(tmp_path / "configured"))
    assert us_firm_data_dir(tmp_path / "explicit") == tmp_path / "explicit"
    assert us_firm_data_dir() == tmp_path / "configured"

    monkeypatch.delenv("MICROCOSM_US_FIRM_DATA_DIR")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    assert us_firm_data_dir() == tmp_path / "home" / "PolicyEngine" / "firm-data"


def test_stage_and_builder_verifier_bind_raw_and_derived_bytes(tmp_path) -> None:
    main_csv = b"ein,employment\n1,12\n"
    sf_csv = b"ein,employment\n2,4\n"
    osha_csv = b"establishment_ID,annual_average_employees\nA,20\n"
    main_zip = _archive("main.csv", main_csv)
    sf_zip = _archive("sf.csv", sf_csv)
    pins, payloads = _pins(
        [
            ("main", "main.csv", main_zip, main_csv),
            ("sf", "sf.csv", sf_zip, sf_csv),
            ("osha", "osha.csv", osha_csv, None),
        ]
    )
    opener = BytesOpener(payloads)

    verified = stage_us_firm_microdata(
        tmp_path,
        pins=pins,
        opener=opener,
        clock=lambda: FIXED_TIME,
        chunk_bytes=3,
        max_total_bytes=10_000,
    )

    assert opener.requests == [source.url for source in pins.sources]
    assert verified.staged_path("main").read_bytes() == main_csv
    assert verified.staged_path("sf").read_bytes() == sf_csv
    assert verified.staged_path("osha").read_bytes() == osha_csv
    assert verified.aggregate_raw_plus_staged_size_bytes == (
        len(main_zip)
        + len(sf_zip)
        + len(osha_csv)
        + len(main_csv)
        + len(sf_csv)
        + len(osha_csv)
    )
    manifest_bytes = verified.manifest_path.read_bytes()
    assert manifest_bytes.endswith(b"\n")
    assert _sha(manifest_bytes) == verified.manifest_sha256
    manifest = json.loads(manifest_bytes)
    assert manifest["source_pins_sha256"] == pins.manifest_sha256
    assert manifest["verified_at_utc"] == "2026-08-23T10:30:00+00:00"
    assert all(
        row["raw"]["retrieved_at_utc"] == "2026-08-23T10:30:00+00:00"
        for row in manifest["sources"]
    )

    reverified = verify_staged_us_firm_microdata(
        tmp_path,
        pins=pins,
        chunk_bytes=2,
        max_total_bytes=10_000,
    )
    assert reverified.manifest_sha256 == verified.manifest_sha256


def test_existing_raw_bytes_reuse_only_matching_retrieval_provenance(tmp_path) -> None:
    csv_bytes = b"header\nvalue\n"
    pins, payloads = _pins([("plain", "plain.csv", csv_bytes, None)])
    first = stage_us_firm_microdata(
        tmp_path,
        pins=pins,
        opener=BytesOpener(payloads),
        clock=lambda: FIXED_TIME,
        max_total_bytes=1_000,
    )
    assert first.source("plain").retrieved_at_utc == "2026-08-23T10:30:00+00:00"

    def no_network(_request):  # pragma: no cover - called only on regression
        raise AssertionError("verified existing raw bytes must not be downloaded")

    second = stage_us_firm_microdata(
        tmp_path,
        pins=pins,
        opener=no_network,
        clock=lambda: datetime(2026, 8, 24, 9, 0, tzinfo=UTC),
        max_total_bytes=1_000,
    )
    assert second.source("plain").retrieved_at_utc == "2026-08-23T10:30:00+00:00"
    receipt = json.loads(second.manifest_path.read_text())
    assert "same raw SHA-256" in receipt["sources"][0]["raw"]["retrieval_note"]


def test_mismatched_download_is_never_adopted(tmp_path) -> None:
    expected = b"expected bytes"
    pins, _ = _pins([("plain", "plain.csv", expected, None)])
    opener = BytesOpener({pins.sources[0].url: b"changed bytes!"})

    with pytest.raises(ValueError, match="identity mismatch"):
        stage_us_firm_microdata(
            tmp_path,
            pins=pins,
            opener=opener,
            clock=lambda: FIXED_TIME,
            max_total_bytes=1_000,
        )

    assert not (tmp_path / "raw" / "plain.source").exists()
    assert not (tmp_path / "raw" / "plain.source.part").exists()
    assert not (tmp_path / "plain.csv").exists()
    assert not (tmp_path / "source_manifest.json").exists()


def test_zip_member_name_is_exact_and_missing_member_refuses_staging(tmp_path) -> None:
    csv_bytes = b"one,two\n1,2\n"
    archive_bytes = _archive("expected.csv", csv_bytes, actual_member="other.csv")
    pins, payloads = _pins([("zip", "expected.csv", archive_bytes, csv_bytes)])

    with pytest.raises(ValueError, match="exactly one file named 'expected.csv'"):
        stage_us_firm_microdata(
            tmp_path,
            pins=pins,
            opener=BytesOpener(payloads),
            clock=lambda: FIXED_TIME,
            max_total_bytes=1_000,
        )

    assert (tmp_path / "raw" / "zip.source").read_bytes() == archive_bytes
    assert not (tmp_path / "expected.csv").exists()
    assert not (tmp_path / "source_manifest.json").exists()


def test_expanded_size_guard_runs_before_any_staged_output(tmp_path) -> None:
    csv_bytes = b"x" * 400
    archive_bytes = _archive("large.csv", csv_bytes)
    pins, payloads = _pins([("zip", "large.csv", archive_bytes, csv_bytes)])
    ceiling = len(archive_bytes) + len(csv_bytes) - 1

    with pytest.raises(ValueError, match="raw and expanded files exceed"):
        stage_us_firm_microdata(
            tmp_path,
            pins=pins,
            opener=BytesOpener(payloads),
            clock=lambda: FIXED_TIME,
            max_total_bytes=ceiling,
        )

    assert (tmp_path / "raw" / "zip.source").exists()
    assert not (tmp_path / "large.csv").exists()
    assert not (tmp_path / "source_manifest.json").exists()


def test_verifier_refuses_staged_bytes_even_if_manifest_is_rehashed(tmp_path) -> None:
    csv_bytes = b"a,b\n1,2\n"
    archive_bytes = _archive("frame.csv", csv_bytes)
    pins, payloads = _pins([("zip", "frame.csv", archive_bytes, csv_bytes)])
    verified = stage_us_firm_microdata(
        tmp_path,
        pins=pins,
        opener=BytesOpener(payloads),
        clock=lambda: FIXED_TIME,
        max_total_bytes=1_000,
    )
    changed = b"a,b\n9,9\n"
    verified.staged_path("zip").write_bytes(changed)
    manifest = json.loads(verified.manifest_path.read_text())
    manifest["sources"][0]["staged"]["sha256"] = _sha(changed)
    verified.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )

    with pytest.raises(ValueError, match="differs from its exact pinned ZIP member"):
        verify_staged_us_firm_microdata(
            tmp_path,
            pins=pins,
            max_total_bytes=1_000,
        )


def test_verifier_refuses_manifest_from_different_raw_pins(tmp_path) -> None:
    csv_bytes = b"a\n1\n"
    pins, payloads = _pins([("plain", "plain.csv", csv_bytes, None)])
    verified = stage_us_firm_microdata(
        tmp_path,
        pins=pins,
        opener=BytesOpener(payloads),
        clock=lambda: FIXED_TIME,
        max_total_bytes=1_000,
    )
    manifest = json.loads(verified.manifest_path.read_text())
    manifest["source_pins_sha256"] = "cd" * 32
    verified.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )

    with pytest.raises(ValueError, match="different source pins"):
        verify_staged_us_firm_microdata(
            tmp_path,
            pins=pins,
            max_total_bytes=1_000,
        )


def test_cli_list_is_offline_and_does_not_create_staging_directory(tmp_path) -> None:
    data_dir = tmp_path / "must-not-exist"
    environment = os.environ.copy()
    environment["MICROCOSM_US_FIRM_DATA_DIR"] = str(data_dir)
    result = subprocess.run(
        [sys.executable, str(CLI), "--list"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["source_pins_sha256"] == SOURCE_PINS_SHA256
    assert len(payload["sources"]) == 3
    assert not data_dir.exists()
