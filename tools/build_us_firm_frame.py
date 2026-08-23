#!/usr/bin/env python3
"""Build the observed US plan-sponsor firm artifact.

The command verifies every staged raw and derived source against the packaged
byte pins before reading it.  It does not download data and it has no pin or
target override.  Production targets must ultimately come from Ledger
consumer facts; until a Chronicle SUSB package exists, command-line builds
must explicitly acknowledge the committed SUSB migration harness.

OSHA ITA is optional and remains an independent measurement reference.  It is
read only when ``--osha-max-employees`` supplies the consequential quality cap
that the OSHA reader deliberately refuses to choose on a caller's behalf.

Example::

    uv run python tools/build_us_firm_frame.py \
        --data-dir ~/PolicyEngine/firm-data \
        --use-susb-migration-harness \
        --out-dir ~/runtime/out/populace-us-firms
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "packages" / "microcosm-build" / "src")
)

FORM_5500_YEAR = 2023
OSHA_ITA_YEAR = 2025


@dataclass(frozen=True)
class _Dependencies:
    """Lazy imports keep argument and staging refusals cheap and isolated."""

    verify_staging: Callable[..., Any]
    read_sponsors: Callable[..., Any]
    load_susb_targets: Callable[..., Any]
    load_bds_validation: Callable[..., Any]
    read_ita: Callable[..., Any]
    apply_osha_quality_rule: Callable[..., Any]
    make_osha_reference: Callable[..., Any]
    build_config: Callable[..., Any]
    build_frame: Callable[..., Any]
    write_artifact: Callable[..., Any]
    verify_artifact: Callable[..., Any]


def _load_dependencies() -> _Dependencies:
    """Import builder dependencies only after CLI arguments are valid."""

    from microcosm.build.us_runtime.us_firms.artifact import (
        verify_us_firm_artifact,
        write_us_firm_artifact,
    )
    from microcosm.build.us_runtime.us_firms.form5500 import read_sponsors
    from microcosm.build.us_runtime.us_firms.frame import (
        USFirmBuildConfig,
        build_us_firm_frame,
        osha_measurement_reference,
    )
    from microcosm.build.us_runtime.us_firms.osha_ita import (
        apply_quality_rule,
        read_ita,
    )
    from microcosm.build.us_runtime.us_firms.staging import (
        verify_staged_us_firm_microdata,
    )
    from microcosm.build.us_runtime.us_firms.targets import (
        load_bds_validation_harness,
        load_susb_migration_harness,
    )

    return _Dependencies(
        verify_staging=verify_staged_us_firm_microdata,
        read_sponsors=read_sponsors,
        load_susb_targets=load_susb_migration_harness,
        load_bds_validation=load_bds_validation_harness,
        read_ita=read_ita,
        apply_osha_quality_rule=apply_quality_rule,
        make_osha_reference=osha_measurement_reference,
        build_config=USFirmBuildConfig,
        build_frame=build_us_firm_frame,
        write_artifact=write_us_firm_artifact,
        verify_artifact=verify_us_firm_artifact,
    )


def _verify_staging_only(data_dir: Path | None) -> Any:
    """Verify staged bytes before importing calibration's heavier runtime."""

    from microcosm.build.us_runtime.us_firms.staging import (
        verify_staged_us_firm_microdata,
    )

    return verify_staged_us_firm_microdata(data_dir)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help=(
            "External pinned-source staging directory. Defaults to "
            "$MICROCOSM_US_FIRM_DATA_DIR, then ~/PolicyEngine/firm-data."
        ),
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        type=Path,
        help=(
            "New artifact directory. The command refuses an existing path and "
            "adopts all output files through one atomic directory rename."
        ),
    )
    parser.add_argument(
        "--use-susb-migration-harness",
        action="store_true",
        required=True,
        help=(
            "Explicitly acknowledge that the committed, hash-pinned SUSB "
            "extract is a migration harness, not a production Ledger target."
        ),
    )
    parser.add_argument(
        "--osha-max-employees",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Include the independent OSHA ITA reference after applying this "
            "explicit employee cap. Without this option OSHA is not read."
        ),
    )
    return parser


def _build(
    args: argparse.Namespace,
    *,
    dependencies: _Dependencies | None = None,
) -> dict[str, object]:
    if args.use_susb_migration_harness is not True:
        raise ValueError(
            "The SUSB migration harness requires explicit operator acknowledgement."
        )
    if dependencies is None:
        staging = _verify_staging_only(args.data_dir)
        deps = _load_dependencies()
    else:
        deps = dependencies
        staging = deps.verify_staging(args.data_dir)
    sponsors = deps.read_sponsors(FORM_5500_YEAR, data_dir=staging.root)

    # This choice is never implicit: argparse refuses to reach this point
    # unless the operator supplied --use-susb-migration-harness.
    targets = deps.load_susb_targets()
    bds = deps.load_bds_validation(year=2022)

    osha_reference = None
    if args.osha_max_employees is not None:
        establishments = deps.read_ita(OSHA_ITA_YEAR, data_dir=staging.root)
        retained = deps.apply_osha_quality_rule(
            establishments,
            max_employees=args.osha_max_employees,
        )
        osha_reference = deps.make_osha_reference(sponsors, retained)

    result = deps.build_frame(
        sponsors,
        targets,
        # The builder re-verifies staging.root before accepting this receipt;
        # an arbitrary mapping cannot stand in for production provenance.
        source_provenance=staging,
        config=deps.build_config(source_year=FORM_5500_YEAR),
        bds_validation=bds,
        osha_reference=osha_reference,
    )
    paths = deps.write_artifact(result, args.out_dir)
    verified_artifact = deps.verify_artifact(paths.directory)
    return {
        "artifact": "populace-us-firms",
        "artifact_directory": str(paths.directory),
        "artifact_manifest_sha256": verified_artifact["manifest_sha256"],
        "build_identity_sha256": result.diagnostics["build_identity_sha256"],
        "diagnostics": str(paths.diagnostics),
        "firms": str(paths.firms),
        "manifest": str(paths.manifest),
        "osha_reference": {
            "enabled": args.osha_max_employees is not None,
            "max_employees": args.osha_max_employees,
        },
        "rows": verified_artifact["rows"],
        "source_manifest_sha256": staging.manifest_sha256,
        "source_pins_sha256": staging.source_pins_sha256,
        "target_source_mode": targets.source_mode,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = _build(args)
    except (OSError, TypeError, ValueError) as error:
        print(f"FATAL: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
