#!/usr/bin/env python3
"""Stage the byte-pinned Form 5500 and OSHA ITA source files.

Raw downloads and expanded CSVs remain outside Git.  The command has no
digest-override mode: a publisher refresh must be reviewed by changing the
packaged pins and rebuilding every dependent artifact.

Examples::

    uv run python tools/stage_us_firm_microdata.py --list
    uv run python tools/stage_us_firm_microdata.py
    uv run python tools/stage_us_firm_microdata.py --data-dir /secure/firm-data
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def _load_staging_module() -> ModuleType:
    """Load the standalone staging module without the heavy US runtime init."""

    path = (
        Path(__file__).resolve().parents[1]
        / "packages"
        / "microcosm-build"
        / "src"
        / "microcosm"
        / "build"
        / "us_runtime"
        / "us_firms"
        / "staging.py"
    )
    module_name = "_microcosm_us_firm_staging_cli"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load US firm staging module at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_STAGING = _load_staging_module()
MAX_RAW_AND_STAGED_BYTES = _STAGING.MAX_RAW_AND_STAGED_BYTES
load_us_firm_source_pins = _STAGING.load_us_firm_source_pins
stage_us_firm_microdata = _STAGING.stage_us_firm_microdata
us_firm_data_dir = _STAGING.us_firm_data_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help=(
            "External staging directory. Defaults to "
            "$MICROCOSM_US_FIRM_DATA_DIR, then ~/PolicyEngine/firm-data."
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print immutable raw pins without downloading anything.",
    )
    args = parser.parse_args(argv)
    pins = load_us_firm_source_pins()
    if args.list:
        payload = {
            "aggregate_raw_size_bytes": sum(
                source.size_bytes for source in pins.sources
            ),
            "maximum_raw_plus_staged_size_bytes": MAX_RAW_AND_STAGED_BYTES,
            "source_pins_sha256": pins.manifest_sha256,
            "sources": [
                {
                    "key": source.key,
                    "sha256": source.sha256,
                    "size_bytes": source.size_bytes,
                    "staged_filename": source.staged_filename,
                    "url": source.url,
                    "zip_member": source.zip_member,
                }
                for source in pins.sources
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    destination = us_firm_data_dir(args.data_dir)
    print(f"Staging US firm sources into {destination}")
    try:
        verified = stage_us_firm_microdata(destination, pins=pins)
    except (OSError, ValueError) as error:
        print(f"FATAL: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "aggregate_raw_plus_staged_size_bytes": (
                    verified.aggregate_raw_plus_staged_size_bytes
                ),
                "source_manifest": str(verified.manifest_path),
                "source_manifest_sha256": verified.manifest_sha256,
                "staged_files": {
                    source.key: {
                        "path": str(source.staged_path),
                        "sha256": source.staged_sha256,
                        "size_bytes": source.staged_size_bytes,
                    }
                    for source in verified.sources
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
