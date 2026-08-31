#!/usr/bin/env python3
"""Build a local, authenticated Armenia ILCS 2024 spine diagnostic."""

from __future__ import annotations

import argparse
import inspect
import json
import uuid
from importlib import metadata
from pathlib import Path

from microcosm.build.am_runtime import (
    AMILCSSpineStageTransform,
    am_household_weight_kind,
    am_ilcs_spine_seed_frame,
    write_am_national_frame,
)
from microcosm.build.country_spec import country_stage_plan, load_country_spec
from microcosm.build.trace import sha256_file

_PIPELINE = "am-ilcs-2024-native-spine"
_STAGE = "ingest_am_ilcs_2024"


def _source_sha256(value: object) -> str:
    source = inspect.getsourcefile(value)
    if source is None:
        raise RuntimeError(f"Cannot locate source for AM ILCS runtime {value!r}.")
    return sha256_file(Path(source))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the local Armenian ILCS 2024 household/member Frame from "
            "the two exact workbooks pinned by the country package. This is "
            "an ingest diagnostic, not a calibration or publication command."
        )
    )
    parser.add_argument(
        "--ilcs-raw-dir",
        type=Path,
        required=True,
        help="Directory containing the pinned household and member XLSX files.",
    )
    parser.add_argument(
        "--spine-h5",
        type=Path,
        required=True,
        help="Output path for the local Armenian staging H5.",
    )
    parser.add_argument(
        "--build-sidecar",
        type=Path,
        help="Optional receipt path; defaults to <spine-h5 stem>.build.json.",
    )
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> Path:
    if not args.ilcs_raw_dir.is_dir():
        raise ValueError(
            f"--ilcs-raw-dir must be an existing directory: {args.ilcs_raw_dir}"
        )
    if args.spine_h5.suffix != ".h5":
        raise ValueError("--spine-h5 must end with '.h5'.")
    sidecar = args.build_sidecar or args.spine_h5.with_suffix(".build.json")
    if sidecar.suffix != ".json":
        raise ValueError("--build-sidecar must end with '.json'.")
    if args.spine_h5.expanduser().resolve() == sidecar.expanduser().resolve():
        raise ValueError("--spine-h5 and --build-sidecar must not collide.")
    return sidecar


def _atomic_write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def _build_sidecar(
    *, frame, stage, stage_record, transform, output: Path
) -> dict[str, object]:
    if transform.last_receipt is None:
        raise RuntimeError("AM ILCS stage completed without a linkage receipt.")
    spec = load_country_spec("am")
    if spec.resolved_spec is None:
        raise RuntimeError("AM country package did not resolve through the typed spec.")
    receipt = transform.last_receipt.as_dict()
    return {
        "schema_version": 1,
        "pipeline": _PIPELINE,
        "disposition": "local_ingest_diagnostic_only",
        "release_eligible": False,
        "publication_authorized": False,
        "country": "am",
        "time_period": str(frame.metadata["time_period"]),
        "amount_basis": receipt["amount_basis"],
        "entity_row_counts": {
            entity: int(len(frame.table(entity))) for entity in frame.entities
        },
        "household_weight_kind": am_household_weight_kind(frame).value,
        "household_weight_total": float(frame.weights_for("household").total),
        "stage": {
            "name": stage.stage,
            "operations": [operation.kind for operation in stage.operations],
            "produced": list(stage_record.produced),
            "nonzero_share": dict(stage_record.nonzero_share),
        },
        "source_authentication": {
            "country_spec_fingerprint": spec.fingerprint,
            "typed_spec_sha256": spec.resolved_spec.spec_sha256,
            "source_stages_sha256": spec.resource_hashes["source_stages.json"],
            "artifacts": receipt["artifact_pins"],
        },
        "join_receipt": receipt["join"],
        "weight_receipt": receipt["weights"],
        "validation_only_observed_monthly_amd": receipt[
            "validation_only_observed_monthly_amd"
        ],
        "output": {
            "filename": output.name,
            "sha256": sha256_file(output),
            "size_bytes": output.stat().st_size,
        },
        "runtime": {
            "microcosm_build": metadata.version("microcosm-build"),
            "raw_loader": "pandas.read_excel(engine='openpyxl')",
            "implementation_sha256": {
                "microcosm.build.am_runtime.ilcs_spine": _source_sha256(
                    AMILCSSpineStageTransform
                ),
                "microcosm.build.am_runtime.national_frame": _source_sha256(
                    write_am_national_frame
                ),
                "tools/build_am_ilcs_spine.py": sha256_file(Path(__file__).resolve()),
            },
        },
        "licensing": {
            "raw_inputs": "caller_supplied_local_only",
            "derived_unit_record_redistribution": "not_authorized_by_this_build",
            "blocker": "capture and review exact ArmStat licence text",
        },
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    sidecar_path = _validate_args(args)
    spec = load_country_spec("am")
    stage = spec.sources.stage_map()[_STAGE]
    transform = AMILCSSpineStageTransform(args.ilcs_raw_dir, stage=stage)
    plan = country_stage_plan(
        spec,
        {_STAGE: transform},
        stage_names=(_STAGE,),
    )
    frame, records = plan.run(am_ilcs_spine_seed_frame())
    output = write_am_national_frame(frame, args.spine_h5)
    _atomic_write_json(
        sidecar_path,
        _build_sidecar(
            frame=frame,
            stage=stage,
            stage_record=records[0],
            transform=transform,
            output=output,
        ),
    )
    print(output)
    print(sidecar_path)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main
    raise SystemExit(main())
