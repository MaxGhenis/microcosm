"""Fail-closed package boundary for Armenian survey artifacts."""

from __future__ import annotations

import shutil
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src"
AM_SOURCE_ROOT = SOURCE_ROOT / "microcosm" / "build" / "am"
AM_RUNTIME_ROOT = SOURCE_ROOT / "microcosm" / "build" / "am_runtime"
BUILD_ARCHIVE_PREFIXES = ("microcosm/build/", "src/microcosm/build/")
REVIEWED_AM_PACKAGE_PATHS = frozenset(
    {
        *(
            f"am/{path.relative_to(AM_SOURCE_ROOT).as_posix()}"
            for path in AM_SOURCE_ROOT.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ),
        *(
            f"am_runtime/{path.relative_to(AM_RUNTIME_ROOT).as_posix()}"
            for path in AM_RUNTIME_ROOT.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ),
    }
)
SENTINEL_NAMES = (
    "private_rows.h5",
    "private_rows.parquet",
    "private_rows.csv",
    "private_rows.dta",
    "private_rows.feather",
    "private_rows.arrow",
    "private_rows.zip",
    "private_rows.tar",
    "private_rows.json",
    "private_rows.bin",
    "private_rows",
)
NON_ARMENIAN_REVIEWED_RESOURCE = (
    "microcosm/build/us_runtime/data/congressional_district_vintage_crosswalk.csv"
)


def _am_members(names: list[str]) -> set[str]:
    members: set[str] = set()
    for name in names:
        for prefix in BUILD_ARCHIVE_PREFIXES:
            marker = f"/{prefix}"
            if name.startswith(prefix):
                candidate = name.removeprefix(prefix)
                if candidate.startswith(("am/", "am_runtime/")):
                    members.add(candidate)
                break
            if marker in name:
                candidate = name.split(marker, maxsplit=1)[1]
                if candidate.startswith(("am/", "am_runtime/")):
                    members.add(candidate)
                break
    return members


def test_source_tree_contains_only_reviewed_armenian_resources() -> None:
    assert REVIEWED_AM_PACKAGE_PATHS == {
        "am/country_package.json",
        "am/gates.json",
        "am/geography_spine.json",
        "am/release_contract.json",
        "am/source_stages.json",
        "am/target_references.json",
        "am/spec/bundle.yaml",
        "am/spec/catalogs.yaml",
        "am/spec/geography.yaml",
        "am/spec/sources.yaml",
        "am/spec/spine.yaml",
        "am/spec/vintages.yaml",
        "am_runtime/__init__.py",
        "am_runtime/ilcs_spine.py",
        "am_runtime/national_frame.py",
    }


def test_hatch_uses_positive_armenian_resource_inventory() -> None:
    config = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text())
    hatch_build = config["tool"]["hatch"]["build"]
    forced = hatch_build["force-include"]

    assert hatch_build["ignore-vcs"] is True
    assert "src/microcosm/build/am/**" in hatch_build["exclude"]
    assert "src/microcosm/build/am_runtime/**" in hatch_build["exclude"]
    assert {
        Path(source).relative_to("src/microcosm/build").as_posix() for source in forced
    } == REVIEWED_AM_PACKAGE_PATHS
    assert set(forced) == set(forced.values())


def test_wheel_and_sdist_exclude_unreviewed_armenian_sentinels(
    tmp_path: Path,
) -> None:
    """Inspect real archives, including formats a suffix mirror can miss."""

    uv = shutil.which("uv")
    assert uv is not None, "the repository test environment must provide uv"
    package_copy = tmp_path / "microcosm-build"
    package_copy.mkdir()
    shutil.copy2(PACKAGE_ROOT / "pyproject.toml", package_copy / "pyproject.toml")
    shutil.copy2(PACKAGE_ROOT / "README.md", package_copy / "README.md")
    shutil.copytree(PACKAGE_ROOT / "src", package_copy / "src")
    for relative_dir in ("am", "am_runtime"):
        sentinel_dir = package_copy / "src" / "microcosm" / "build" / relative_dir
        for name in SENTINEL_NAMES:
            (sentinel_dir / name).write_bytes(b"sentinel Armenian row payload")

    dist = tmp_path / "dist"
    subprocess.run(
        [uv, "build", "--wheel", "--sdist", str(package_copy), "--out-dir", str(dist)],
        check=True,
        capture_output=True,
        text=True,
    )

    wheel = next(dist.glob("*.whl"))
    sdist = next(dist.glob("*.tar.gz"))
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
        wheel_members = _am_members(wheel_names)
    with tarfile.open(sdist) as archive:
        sdist_names = archive.getnames()
        sdist_members = _am_members(sdist_names)

    assert wheel_members == REVIEWED_AM_PACKAGE_PATHS
    assert sdist_members == REVIEWED_AM_PACKAGE_PATHS
    assert not any(path.endswith(SENTINEL_NAMES) for path in wheel_members)
    assert not any(path.endswith(SENTINEL_NAMES) for path in sdist_members)
    assert any(name.endswith(NON_ARMENIAN_REVIEWED_RESOURCE) for name in wheel_names)
    assert any(name.endswith(NON_ARMENIAN_REVIEWED_RESOURCE) for name in sdist_names)
