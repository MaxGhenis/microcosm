#!/usr/bin/env python3
"""Reverify the adopted Phase-0 inputs and A17 P0 setup gates.

The verifier is intentionally read-only with respect to the repository.  Its
deterministic evidence artifact is written to
``/private/tmp/qrf_phase0_a17_setup.json``.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from scipy.stats import norm

from microcosm.build import frame_checkpoint

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments"
D0_PATH = EXP / "qrf_drift_validation_d0.json"
PHASE0_PATH = EXP / "qrf_drift_validation_phase0.json"
OUT = Path("/private/tmp/qrf_phase0_a17_setup.json")

EXPECTED_AUTHORITY = {
    EXP / "qrf_drift_validation_design.md": (
        "a91d19cc6a3c7e55db28159189ce0ccc76ddbf972247a20cc6eabbb59d5719bc"
    ),
    EXP / "qrf_drift_validation_a16_binding_texts.md": (
        "7e288bce7496e1e7f41e33f078be2043673ca54ff31182caf2ce92eab68a81c1"
    ),
    D0_PATH: "fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8",
    EXP / "qrf_drift_validation_d0.md": (
        "c4f3a9c56426025426e56428e9bce697a6cc6112f175be86ef9ef139bf79b601"
    ),
}

EXPECTED_ADOPTED_EVIDENCE = {
    Path("/private/tmp/qrf_phase0_c0a.json"): (
        "d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962"
    ),
    Path("/private/tmp/qrf_phase0_v22_c0a_reuse_verification.json"): (
        "60562a7524a91af4eb1f554acb26e71c208ae6892cc7a273b79b465251783569"
    ),
    Path("/private/tmp/qrf_phase0_v22_c0b.json"): (
        "1c7bfd65660b14068c4bc96fae4b8d270cb447ea8fbbe42c8ef982c5f1dbf542"
    ),
    Path("/private/tmp/qrf_phase0_c0b_replay.py"): (
        "6a6b9e7ac7042d15726ac3ff895f10a613d49af5265e26a174f2151f66ad8058"
    ),
    Path("/private/tmp/qrf_phase0_c0b_replay.json"): (
        "537cedfd35ee02bbcb74ea90814f274a21e6087c449b75294f798146442e66eb"
    ),
    Path("/private/tmp/qrf_phase0_v22_c0b_input_verification.json"): (
        "a7376bd7557863c16b9b6f1dfee41d7f0c5b02c2be27ed899e9cafceb56d3e16"
    ),
    Path("/private/tmp/qrf_phase0_v22_c5.json"): (
        "7f00827190276615806e26d5c76eda7c413c49640fb843988770f58056dc584c"
    ),
    Path("/private/tmp/qrf_phase0_v22_c5_writer.py"): (
        "0a40ef954c6155c275c2640f1dcb5cae072a8d25501dca256e51e9299da34f12"
    ),
    Path("/private/tmp/qrf_phase0_v22_c5_reader.py"): (
        "8492f0bf8f9b7709d8b02586220836239815bec04adabd185a4746ace537be8e"
    ),
    Path("/private/tmp/qrf_phase0_a16_setup_checks.py"): (
        "d8e55672d141d23dcb0840f5274bc5a9d358a439464bca68189e3c2c716b7948"
    ),
    Path("/private/tmp/qrf_phase0_a16_setup_checks.json"): (
        "8382c169bec5ab9d2779f57d52926e76c71ec7d550792b62c29e126ea95a0512"
    ),
}

HISTORICAL_V22_DESIGN = {
    "commit": "51866036",
    "path": "experiments/qrf_drift_validation_design.md",
    "sha256": "91472a8e0042d819430c533ec1aa0cb112b73e98f94f380964aa33f4e22e8292",
}

SEALED_PHASE0_SOURCE = {
    "commit": "90070561b9d54a0ae103c27537df10a48969b999",
    "path": "experiments/qrf_drift_validation_phase0.json",
    "blob_sha256": (
        "e6c2105b84fda5940317aa7984159c383e6dd104b4457592e76e8a05961e86d1"
    ),
}

EXPECTED_STEP0_SEALS = {
    "operator_table_sha256": (
        "447f7c9f00220440b7ad3825223f01fec8bed28e16e6eda2a851afdda64a6e23"
    ),
    "json_schema_sha256": (
        "1a951262e9f9420fa8bc4462d2b53f697ab428ddcdb8e820021be80983fe54d7"
    ),
    "required_id_manifest_sha256": (
        "c2ba7add0445a91715c491d78b83677844f90767414bdd32a7511fff1d676ec9"
    ),
    "adjudication_table_sha256": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    ),
    "default_appendix_sha256": (
        "4b58de099a1edcc11bdfbfef21ec8c06d835bca67ca9c80d55a4346beae32332"
    ),
    "composite_sha256": (
        "2cabf69c9d91801e16686a46cf904bc346c0e009162ad2bb91eda996da73e9b8"
    ),
}

EXPECTED_K = 122
EXPECTED_K_DIGEST = (
    "348386d9675172b65550ef7cb157fb1387e1d45331f61253aefe40dbe8f2bbc9"
)
EXPECTED_SIDAK_Z = 3.526967430023352

# A17 calls the D0-4 adult-care clearing an exact row set.  D0 pins both
# extensional inputs but did not spell out a serialization.  This committed
# binding hashes the sorted /person/axis1 labels selected by finite raw draw
# and raw/terminal bit inequality, encoded as a headerless contiguous array
# of little-endian signed int64 values.  On the D0-pinned pair, axis1 labels
# are exactly the zero-based person-axis positions.
ADULT_CARE_ROW_SET_ENCODING = (
    "sort ascending /person/axis1 labels for finite raw-draw rows whose "
    "raw and terminal float64 bits differ; encode as contiguous headerless "
    "little-endian signed int64 bytes; SHA-256"
)
EXPECTED_ADULT_CARE_ROW_SET_SHA256 = (
    "7fe71e4ff4795ee968daf0acbd3f24db0db105b538508f099bd83a6e7d44dda3"
)


def canonical_json(value: Any) -> bytes:
    """Return the sealed Step-0 canonical form for the values used here."""

    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class Rehasher:
    """Stream files once even when several adopted manifests name them."""

    def __init__(self) -> None:
        self.cache: dict[Path, str] = {}

    def sha256_file(self, path: Path) -> str:
        key = path.resolve()
        if key not in self.cache:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    digest.update(chunk)
            self.cache[key] = digest.hexdigest()
        return self.cache[key]

    def check(self, path: Path, expected: str, role: str) -> dict[str, Any]:
        exists = path.is_file()
        actual = self.sha256_file(path) if exists else None
        return {
            "role": role,
            "path": str(path),
            "bytes": path.stat().st_size if exists else None,
            "sha256_expected": expected,
            "sha256_actual": actual,
            "match": actual == expected,
        }


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
    )


def git_blob_check(
    commit: str, path: str, expected: str, role: str
) -> dict[str, Any]:
    content = git_blob(commit, path)
    actual = sha256_bytes(content)
    return {
        "role": role,
        "path": f"git:{commit}:{path}",
        "bytes": len(content),
        "sha256_expected": expected,
        "sha256_actual": actual,
        "match": actual == expected,
    }


def expected_digest(item: dict[str, Any]) -> str:
    for key in ("sha256_expected", "expected_sha256", "sha256"):
        if key in item:
            return str(item[key])
    raise KeyError(f"no expected digest in {item!r}")


class SelectedCheckpoint:
    """Read selected columns from a populace frame checkpoint."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.h5 = h5py.File(path, "r")
        self.root = self.h5["_populace_frame_checkpoint"]
        self.metadata = json.loads(bytes(self.root["metadata_json"][:]).decode())
        self.table_index = {
            table["name"]: position
            for position, table in enumerate(self.metadata["tables"])
        }

    def column(self, table_name: str, column_name: str) -> np.ndarray:
        table_position = self.table_index[table_name]
        table = self.metadata["tables"][table_position]
        column_position = next(
            position
            for position, spec in enumerate(table["columns"])
            if spec["name"] == column_name
        )
        spec = table["columns"][column_position]
        group = self.root[
            f"tables/t{table_position:05d}/columns/c{column_position:05d}"
        ]
        series = frame_checkpoint._read_series(
            group,
            spec,
            self.path,
            label=f"{table_name}.{column_name}",
        )
        return series.to_numpy(copy=False)

    def close(self) -> None:
        self.h5.close()


def load_bank(
    path: Path, cache: dict[Path, dict[str, Any]]
) -> dict[str, Any]:
    if path in cache:
        return cache[path]
    with h5py.File(path, "r") as h5:
        metadata = json.loads(bytes(h5["metadata_json"][:]).decode())
        bits = np.asarray(h5["raw_draw_bits"][:], dtype="<u8")
    raw_sha256 = sha256_bytes(bits.tobytes(order="C"))
    value = {
        "metadata": metadata,
        "bits": bits,
        "raw": bits.view("<f8"),
        "raw_draw_sha256": raw_sha256,
        "metadata_raw_draw_sha256": metadata.get("raw_draw_sha256"),
        "metadata_raw_draw_sha256_match": (
            raw_sha256 == metadata.get("raw_draw_sha256")
        ),
    }
    cache[path] = value
    return value


def pool_column(h5: h5py.File, entity: str, column_name: str) -> np.ndarray:
    group = h5[entity]
    for items_name in sorted(name for name in group if name.endswith("_items")):
        names = [
            value.decode() if isinstance(value, bytes) else str(value)
            for value in group[items_name][:]
        ]
        if column_name not in names:
            continue
        position = names.index(column_name)
        values = group[items_name.replace("_items", "_values")]
        if values.ndim != 2:
            raise ValueError(
                f"unsupported non-tabular pool column {entity}.{column_name}"
            )
        return np.asarray(values[:, position])
    raise KeyError(f"pool column not found: {entity}.{column_name}")


def terminal_column(h5: h5py.File, expression: str) -> np.ndarray:
    match = re.fullmatch(r"(/[^\[]+)\[:,(\d+)\]", expression)
    if not match:
        raise ValueError(f"unsupported terminal expression {expression!r}")
    dataset, column = match.groups()
    return np.asarray(h5[dataset][:, int(column)], dtype="<f8")


def mask_sha256(mask: np.ndarray) -> str:
    encoded = np.asarray(mask, dtype=np.uint8)
    return sha256_bytes(np.ascontiguousarray(encoded).tobytes(order="C"))


def int64_set_sha256(values: np.ndarray) -> str:
    encoded = np.asarray(np.sort(values), dtype="<i8")
    return sha256_bytes(np.ascontiguousarray(encoded).tobytes(order="C"))


def adopted_control_reverification(
    rehasher: Rehasher, sidak_z: float
) -> dict[str, Any]:
    authority = [
        rehasher.check(path, expected, "current_A17_authority")
        for path, expected in EXPECTED_AUTHORITY.items()
    ]
    evidence = [
        rehasher.check(path, expected, "adopted_control_evidence")
        for path, expected in EXPECTED_ADOPTED_EVIDENCE.items()
    ]

    c0a_manifest = json.loads(
        Path("/private/tmp/qrf_phase0_v22_c0a_reuse_verification.json").read_text()
    )
    c0a_inputs = [
        rehasher.check(
            Path(item["path"]),
            expected_digest(item),
            f"C0a:{item['role']}",
        )
        for item in c0a_manifest["files"]
    ]

    c0b_manifest = json.loads(
        Path("/private/tmp/qrf_phase0_v22_c0b_input_verification.json").read_text()
    )
    c0b_inputs: list[dict[str, Any]] = []
    for item in c0b_manifest["files"]:
        if item["role"] == "operative_design_v2.2":
            c0b_inputs.append(
                git_blob_check(
                    HISTORICAL_V22_DESIGN["commit"],
                    HISTORICAL_V22_DESIGN["path"],
                    HISTORICAL_V22_DESIGN["sha256"],
                    "C0b:historical_v2.2_design_input",
                )
            )
        else:
            c0b_inputs.append(
                rehasher.check(
                    Path(item["path"]),
                    expected_digest(item),
                    f"C0b:{item['role']}",
                )
            )

    c5 = json.loads(Path("/private/tmp/qrf_phase0_v22_c5.json").read_text())
    c5_inputs: list[dict[str, Any]] = []
    for role, item in sorted(c5["artifact_digests"].items()):
        if role == "design":
            c5_inputs.append(
                git_blob_check(
                    HISTORICAL_V22_DESIGN["commit"],
                    HISTORICAL_V22_DESIGN["path"],
                    item["sha256"],
                    "C5:historical_v2.2_design_input",
                )
            )
        else:
            c5_inputs.append(
                rehasher.check(
                    Path(item["path"]),
                    item["sha256"],
                    f"C5:{role}",
                )
            )
    c5_bundle_actual = digest_object(
        {
            role: item["sha256"]
            for role, item in sorted(c5["artifact_digests"].items())
        }
    )

    c0a = json.loads(Path("/private/tmp/qrf_phase0_c0a.json").read_text())
    c0b = json.loads(Path("/private/tmp/qrf_phase0_v22_c0b.json").read_text())
    c0b_cells = c0b["per_class_controls"]
    c0b_cells_at_a17 = [
        bool(
            abs(float(cell["mc_mean_z"])) <= sidak_z
            and abs(float(cell["production_single_draw_z"])) <= sidak_z
        )
        for cell in c0b_cells
    ]
    c5_exact = [bool(item["exact_match"]) for item in c5["exact_match_booleans"]]

    groups = authority + evidence + c0a_inputs + c0b_inputs + c5_inputs
    statuses = {
        "C0a": {
            "status": c0a["status"],
            "mismatched_comparisons": c0a["mismatched_comparisons"],
            "pass": (
                c0a["status"] == "PASS"
                and int(c0a["mismatched_comparisons"]) == 0
            ),
        },
        "C0b": {
            "adopted_status": c0b["status"],
            "cells": len(c0b_cells),
            "cells_passing_at_A17_z": sum(c0b_cells_at_a17),
            "max_abs_mc_mean_z": max(
                abs(float(cell["mc_mean_z"])) for cell in c0b_cells
            ),
            "max_abs_production_single_draw_z": max(
                abs(float(cell["production_single_draw_z"]))
                for cell in c0b_cells
            ),
            "A17_sidak_z": sidak_z,
            "pass": (
                c0b["status"] == "PASS"
                and len(c0b_cells) == 76
                and all(c0b_cells_at_a17)
                and c0b["summary"]["e4_patterns_passed"] == 36
            ),
        },
        "C5": {
            "execution_status": c5["execution_status"],
            "checks_total": c5["checks_total"],
            "checks_passed": c5["checks_passed"],
            "all_exact_match": all(c5_exact),
            "artifact_digest_bundle_sha256_expected": c5[
                "artifact_digest_bundle_sha256"
            ],
            "artifact_digest_bundle_sha256_actual": c5_bundle_actual,
            "pass": (
                c5["execution_status"] == "PASS"
                and c5["checks_total"] == 8
                and c5["checks_passed"] == 8
                and len(c5_exact) == 8
                and all(c5_exact)
                and c5_bundle_actual == c5["artifact_digest_bundle_sha256"]
            ),
        },
    }
    return {
        "all_file_digests_match": all(item["match"] for item in groups),
        "authority": authority,
        "adopted_evidence": evidence,
        "C0a_inputs": c0a_inputs,
        "C0b_inputs": c0b_inputs,
        "C5_inputs": c5_inputs,
        "control_statuses": statuses,
        "pass": (
            all(item["match"] for item in groups)
            and all(item["pass"] for item in statuses.values())
        ),
    }


def verify_roster() -> dict[str, Any]:
    source_bytes = git_blob(
        SEALED_PHASE0_SOURCE["commit"], SEALED_PHASE0_SOURCE["path"]
    )
    source_sha = sha256_bytes(source_bytes)
    phase0 = json.loads(source_bytes)
    step0 = phase0["step0"]

    seal_objects = {
        "operator_table_sha256": step0["operator_table"],
        "json_schema_sha256": step0["json_schema"],
        "required_id_manifest_sha256": step0["required_id_manifest"],
        "adjudication_table_sha256": step0["adjudication_table"],
        "default_appendix_sha256": step0["default_appendix"],
    }
    actual_seals = {
        name: digest_object(value) for name, value in seal_objects.items()
    }
    actual_seals["composite_sha256"] = digest_object(
        {
            "operator_table": step0["operator_table"],
            "json_schema": step0["json_schema"],
            "required_id_manifest": step0["required_id_manifest"],
            "adjudication_table": step0["adjudication_table"],
            "default_appendix": step0["default_appendix"],
        }
    )
    seal_checks = {
        name: {
            "expected": EXPECTED_STEP0_SEALS[name],
            "recorded": step0["seals"][name],
            "actual": actual_seals[name],
            "match": (
                actual_seals[name]
                == step0["seals"][name]
                == EXPECTED_STEP0_SEALS[name]
            ),
        }
        for name in EXPECTED_STEP0_SEALS
    }

    ids: list[str] = []
    components = {"C0b": 0, "C4_null_total": 0, "C2_C3_group_errors": 0}
    for entry in step0["required_id_manifest"]:
        dimensions = entry["dimensions"]
        if (
            dimensions["row"] == "C0b_E2"
            and dimensions["variant"] == "repeated_draw"
        ):
            ids.append(entry["id"])
            components["C0b"] += 1
        elif dimensions["row"] == "C4_null_total":
            ids.append(entry["id"])
            components["C4_null_total"] += 1
        elif dimensions["row"] in {"C2_oracle_error", "C3_oracle_error"}:
            ids.append(entry["id"])
            components["C2_C3_group_errors"] += 1

    ids_sha = digest_object(ids)
    sidak_z = float(norm.ppf((1.0 + 0.95 ** (1.0 / len(ids))) / 2.0))
    recorded = phase0["controls"]["K"]
    checks = {
        "source_blob": source_sha == SEALED_PHASE0_SOURCE["blob_sha256"],
        "sealed_before_fresh_statistics": bool(
            step0["sealed_before_fresh_statistics"]
        ),
        "all_step0_seals": all(item["match"] for item in seal_checks.values()),
        "K": len(ids) == recorded["K"] == EXPECTED_K,
        "components": components == recorded["components"],
        "ordered_ids": ids == recorded["ordered_ids"],
        "ordered_ids_sha256": (
            ids_sha == recorded["ordered_ids_sha256"] == EXPECTED_K_DIGEST
        ),
        "sidak_z": sidak_z == recorded["sidak_z"] == EXPECTED_SIDAK_Z,
    }
    return {
        "source": {
            "path": (
                f"git:{SEALED_PHASE0_SOURCE['commit']}:"
                f"{SEALED_PHASE0_SOURCE['path']}"
            ),
            "sha256_expected": SEALED_PHASE0_SOURCE["blob_sha256"],
            "sha256_actual": source_sha,
        },
        "step0_seals": seal_checks,
        "selection_rule": (
            "sealed manifest order; C0b_E2/repeated_draw, C4_null_total, "
            "then C2_oracle_error or C3_oracle_error wherever encountered"
        ),
        "components": components,
        "K": len(ids),
        "ordered_ids_sha256": ids_sha,
        "sidak_formula": "Phi^-1((1+0.95^(1/K))/2)",
        "sidak_z": sidak_z,
        "checks": checks,
        "pass": all(checks.values()),
    }


def artifact_pin_lookup(
    d0: dict[str, Any], rung: str
) -> dict[str, dict[str, Any]]:
    return {
        row["target"]: row
        for row in d0["D0-0"]["artifacts"][rung]["bank_target_checkpoints"]
    }


def checkpoint_file_pin(
    d0: dict[str, Any], rung: str, filename: str
) -> dict[str, Any]:
    return next(
        row
        for row in d0["D0-11"]["builds"][rung]["files"]
        if row["filename"] == filename
    )


def verify_a17_15_i(
    d0: dict[str, Any], rehasher: Rehasher
) -> dict[str, Any]:
    root = Path(d0["D0-11"]["builds"]["candidate-25"]["root"])
    assembled_path = root / "assembled.checkpoint.h5"
    transferred_path = root / "transferred.checkpoint.h5"
    checkpoint_pins = [
        rehasher.check(
            assembled_path,
            checkpoint_file_pin(d0, "candidate-25", assembled_path.name)["sha256"],
            "A17-15(i):candidate_assembled_checkpoint",
        ),
        rehasher.check(
            transferred_path,
            checkpoint_file_pin(d0, "candidate-25", transferred_path.name)[
                "sha256"
            ],
            "A17-15(i):candidate_transferred_checkpoint",
        ),
    ]

    assembled = SelectedCheckpoint(assembled_path)
    transferred = SelectedCheckpoint(transferred_path)
    arrays = {
        ("early_gap_fill", "person"): (
            assembled.column("person", "person_support_channel"),
            assembled.column("person", "person_support_clone_index"),
        ),
        ("late_transfer", "person"): (
            transferred.column("person", "person_support_channel"),
            transferred.column("person", "person_support_clone_index"),
        ),
        ("late_transfer", "spm_unit"): (
            transferred.column("spm_unit", "spm_unit_support_channel"),
            transferred.column("spm_unit", "spm_unit_support_clone_index"),
        ),
    }
    assembled.close()
    transferred.close()

    receipts = {
        row["target"]: row
        for row in d0["D0-3"]["candidate"]["target_receipts"]
    }
    file_pins = artifact_pin_lookup(d0, "candidate-25")
    bank_cache: dict[Path, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for target in d0["scope"]["targets"]:
        spec = d0["D0-2"]["targets"][target]
        path = Path(spec["target_bank_file"])
        bank = load_bank(path, bank_cache)
        raw = bank["raw"]
        channel, clone = arrays[(spec["stage"], spec["entity"])]
        length_match = len(raw) == len(channel) == len(clone)
        if not length_match:
            raise ValueError(f"candidate bank/checkpoint length mismatch: {target}")

        full_drawn = np.isfinite(raw)
        recipient = np.asarray(channel) == "acs"
        clone0 = np.asarray(clone) == 0
        battery_scope = recipient & clone0
        s_q = full_drawn & battery_scope
        drawn_positions = np.flatnonzero(full_drawn)
        projection_count = int(
            np.count_nonzero(
                (np.asarray(channel)[drawn_positions] == "acs")
                & (np.asarray(clone)[drawn_positions] == 0)
            )
        )
        full_count = int(np.count_nonzero(full_drawn))
        receipt_count = int(receipts[target]["authorized_null_rows"])
        s_q_count = int(np.count_nonzero(s_q))
        bank_pin = file_pins[target]
        bank_file_check = rehasher.check(
            path, bank_pin["sha256"], f"A17-15(i):candidate_bank:{target}"
        )
        checks = {
            "bank_file_pin": bank_file_check["match"],
            "raw_draw_metadata_digest": bank[
                "metadata_raw_draw_sha256_match"
            ],
            "checkpoint_alignment_length": length_match,
            "full_bank_drawn_equals_receipt": full_count == receipt_count,
            "drawn_positions_are_recipient_rows": int(
                np.count_nonzero(full_drawn & ~recipient)
            )
            == 0,
            "S_q_equals_same_mask_clone0_projection": (
                s_q_count == projection_count
            ),
            "S_q_equals_D0_clone0_recipient_count": (
                s_q_count == int(spec["clone0_recipient_rows"])
            ),
        }
        rows.append(
            {
                "target": target,
                "stage": spec["stage"],
                "entity": spec["entity"],
                "bank_path": str(path),
                "bank_file_sha256": bank_file_check,
                "full_bank_rows": len(raw),
                "full_bank_drawn_count": full_count,
                "full_bank_drawn_mask_sha256_uint8": mask_sha256(full_drawn),
                "receipt_authorized_null_rows": receipt_count,
                "battery_scope_count": int(np.count_nonzero(battery_scope)),
                "S_q_count": s_q_count,
                "S_q_mask_sha256_uint8_full_entity_axis": mask_sha256(s_q),
                "S_q_sorted_axis_positions_sha256_le_i8": int64_set_sha256(
                    np.flatnonzero(s_q)
                ),
                "same_mask_clone0_projection_count": projection_count,
                "raw_draw_sha256": bank["raw_draw_sha256"],
                "checks": checks,
                "pass": all(checks.values()),
            }
        )
    return {
        "definition": (
            "full-bank finite raw-draw positions equal the whole-frame receipt; "
            "S_q is that mask intersected with ACS clone-0 battery scope"
        ),
        "mask_encoding": (
            "boolean masks are contiguous uint8 bytes in ascending entity-axis order"
        ),
        "checkpoint_pins": checkpoint_pins,
        "targets": rows,
        "targets_passed": sum(row["pass"] for row in rows),
        "targets_total": len(rows),
        "pass": (
            all(item["match"] for item in checkpoint_pins)
            and all(row["pass"] for row in rows)
        ),
    }


def lineage_matrix(
    checkpoint: SelectedCheckpoint, entity: str, names: list[str]
) -> np.ndarray:
    return np.asarray(
        np.column_stack(
            [
                np.asarray(checkpoint.column(entity, name), dtype="<i8")
                for name in names
            ]
        ),
        dtype="<i8",
        order="C",
    )


def matrix_sha256(values: np.ndarray) -> str:
    encoded = np.asarray(values, dtype="<i8", order="C")
    return sha256_bytes(np.ascontiguousarray(encoded).tobytes(order="C"))


def verify_lineage_digests(
    d0: dict[str, Any], pool: h5py.File, rehasher: Rehasher
) -> dict[str, Any]:
    root = Path(d0["D0-11"]["builds"]["baseline1pct"]["root"])
    path = root / "assembled.checkpoint.h5"
    pin = checkpoint_file_pin(d0, "baseline1pct", path.name)
    file_check = rehasher.check(
        path, pin["sha256"], "A16-15(ii):baseline_assembled_checkpoint"
    )
    checkpoint = SelectedCheckpoint(path)
    records: dict[str, Any] = {}
    specs = {
        "early_person_bank": ("person", "early_person_bank"),
        "spm_prefix_cross_check": ("spm_unit", "spm_prefix_cross_check"),
    }
    alignment = d0["D0-4"]["alignment_evidence"]
    for output_name, (entity, d0_name) in specs.items():
        expected = alignment[d0_name]
        names = list(expected["lineage_columns"])
        assembled = lineage_matrix(checkpoint, entity, names)
        terminal = np.asarray(
            np.column_stack(
                [
                    np.asarray(pool_column(pool, entity, name), dtype="<i8")
                    for name in names
                ]
            )[: len(assembled)],
            dtype="<i8",
            order="C",
        )
        assembled_sha = matrix_sha256(assembled)
        terminal_sha = matrix_sha256(terminal)
        checks = {
            "assembled_row_count": len(assembled) == expected["assembled_rows"],
            "terminal_row_count": len(pool[f"{entity}/axis1"])
            == expected[
                "terminal_person_rows"
                if entity == "person"
                else "terminal_spm_rows"
            ],
            "assembled_digest": (
                assembled_sha == expected["assembled_lineage_sha256"]
            ),
            "terminal_prefix_digest": (
                terminal_sha == expected["terminal_prefix_lineage_sha256"]
            ),
            "matrices_bitwise_equal": np.array_equal(assembled, terminal),
        }
        records[output_name] = {
            "entity": entity,
            "columns": names,
            "rows": len(assembled),
            "encoding": (
                "columns in displayed order, row-major contiguous little-endian "
                "signed int64 bytes"
            ),
            "assembled_sha256": assembled_sha,
            "terminal_prefix_sha256": terminal_sha,
            "checks": checks,
            "pass": all(checks.values()),
        }
    checkpoint.close()
    return {
        "assembled_checkpoint_file": file_check,
        "checks": records,
        "pass": file_check["match"] and all(
            record["pass"] for record in records.values()
        ),
    }


def verify_a16_ii_and_a17_iii(
    d0: dict[str, Any], rehasher: Rehasher
) -> tuple[dict[str, Any], dict[str, Any]]:
    pool_path = Path(d0["D0-4"]["pool"])
    pool_pin = d0["D0-0"]["artifacts"]["baseline1pct"]["files"]["pool_h5"]
    pool_file_check = rehasher.check(
        pool_path, pool_pin["sha256"], "A16-15(ii):baseline_pool"
    )
    bank_pins = artifact_pin_lookup(d0, "baseline1pct")
    d04 = {row["target"]: row for row in d0["D0-4"]["targets"]}
    checkpoint_root = Path(d0["D0-4"]["checkpoint_root"])
    bank_cache: dict[Path, dict[str, Any]] = {}
    alignment_rows: list[dict[str, Any]] = []
    equality_rows: list[dict[str, Any]] = []

    with h5py.File(pool_path, "r") as pool:
        lineage = verify_lineage_digests(d0, pool, rehasher)
        person_axis = np.asarray(pool["person/axis1"][:], dtype="<i8")
        person_clone = np.asarray(
            pool_column(pool, "person", "person_support_clone_index"),
            dtype="<i8",
        )
        for target in d0["scope"]["targets"]:
            item = d04[target]
            spec = d0["D0-2"]["targets"][target]
            path = checkpoint_root / item["checkpoint_relative_path"]
            bank = load_bank(path, bank_cache)
            raw = bank["raw"]
            bits = bank["bits"]
            terminal_full = terminal_column(pool, item["terminal_dataset"])
            if spec["stage"] == "early_gap_fill":
                terminal = terminal_full[: len(raw)]
                alignment_mode = "D0 early-person lineage-equal terminal prefix"
                positional_alignment = (
                    len(raw)
                    == d0["D0-4"]["alignment_evidence"]["early_person_bank"][
                        "assembled_rows"
                    ]
                    and lineage["checks"]["early_person_bank"]["pass"]
                )
            else:
                terminal = terminal_full
                alignment_mode = "D0 direct full entity-axis position alignment"
                positional_alignment = len(raw) == len(terminal_full)

            bank_file_check = rehasher.check(
                path,
                bank_pins[target]["sha256"],
                f"A16-15(ii):baseline_bank:{target}",
            )
            drawn = np.isfinite(raw)
            drawn_positions = np.flatnonzero(drawn)
            terminal_bits = np.ascontiguousarray(
                terminal[drawn_positions], dtype="<f8"
            ).view("<u8")
            bit_equal = bits[drawn_positions] == terminal_bits
            numeric_equal = np.equal(
                raw[drawn_positions], terminal[drawn_positions]
            )
            unequal_positions = drawn_positions[~bit_equal]

            integrity_checks = {
                "bank_file_pin": bank_file_check["match"],
                "metadata_raw_draw_digest": bank[
                    "metadata_raw_draw_sha256_match"
                ],
                "D0_raw_draw_digest": (
                    bank["raw_draw_sha256"] == item["raw_draw_sha256"]
                ),
                "raw_row_count": len(raw) == item["raw_rows"],
                "raw_nan_count": int(np.count_nonzero(~drawn))
                == item["raw_nan_rows"],
                "drawn_count": int(np.count_nonzero(drawn))
                == item["drawn_rows"],
                "positional_alignment": bool(positional_alignment),
            }
            alignment_rows.append(
                {
                    "target": target,
                    "stage": spec["stage"],
                    "entity": spec["entity"],
                    "alignment_mode": alignment_mode,
                    "bank_path": str(path),
                    "bank_file_sha256": bank_file_check,
                    "raw_draw_sha256_expected": item["raw_draw_sha256"],
                    "raw_draw_sha256_actual": bank["raw_draw_sha256"],
                    "checks": integrity_checks,
                    "pass": all(integrity_checks.values()),
                }
            )

            common = {
                "target": target,
                "drawn_rows": len(drawn_positions),
                "bitwise_equal_rows": int(np.count_nonzero(bit_equal)),
                "bitwise_unequal_rows": len(unequal_positions),
                "numeric_equal_rows": int(np.count_nonzero(numeric_equal)),
                "numeric_unequal_rows": int(np.count_nonzero(~numeric_equal)),
                "D0_equal_rows": item["equal_rows"],
                "D0_unequal_rows": item["unequal_rows"],
                "raw_draw_sha256": bank["raw_draw_sha256"],
                "terminal_dataset": item["terminal_dataset"],
                "source_pool_sha256": pool_file_check["sha256_actual"],
                "source_bank_sha256": bank_file_check["sha256_actual"],
            }
            if target != "pre_subsidy_care_expenses":
                checks = {
                    "all_drawn_rows_bitwise_equal": bool(bit_equal.all()),
                    "D0_bitwise_equality_reproduced": bool(
                        item["all_bitwise_equal"]
                    )
                    and len(unequal_positions) == 0,
                    "D0_counts_reproduced": (
                        int(np.count_nonzero(numeric_equal)) == item["equal_rows"]
                        and int(np.count_nonzero(~numeric_equal))
                        == item["unequal_rows"]
                    ),
                }
                equality_rows.append(
                    {
                        **common,
                        "rule": "raw and terminal float64 bits equal on every drawn row",
                        "checks": checks,
                        "pass": all(checks.values()),
                    }
                )
                continue

            axis_is_positional = np.array_equal(
                person_axis, np.arange(len(person_axis), dtype="<i8")
            )
            row_ids = np.asarray(
                np.sort(person_axis[unequal_positions]), dtype="<i8"
            )
            row_set_sha = int64_set_sha256(row_ids)
            mismatch_raw = raw[unequal_positions]
            mismatch_terminal = terminal[unequal_positions]
            mismatch_terminal_bits = np.ascontiguousarray(
                mismatch_terminal, dtype="<f8"
            ).view("<u8")
            clone_values, clone_counts = np.unique(
                person_clone[unequal_positions], return_counts=True
            )
            clone_split = {
                str(int(value)): int(count)
                for value, count in zip(clone_values, clone_counts, strict=True)
            }
            expected_clone_split = {
                clone: int(values["unequal"])
                for clone, values in item["clone_counts"].items()
            }
            values, counts = np.unique(mismatch_raw, return_counts=True)
            frequencies = [
                {"raw_value": float(value), "rows": int(count)}
                for value, count in zip(values, counts, strict=True)
            ]
            expected_frequencies = item["mismatch"]["raw_value_frequencies"]
            adult_checks = {
                "person_axis_is_zero_based_positional": axis_is_positional,
                "row_set_count_is_183": len(row_ids) == 183,
                "row_set_digest": (
                    row_set_sha == EXPECTED_ADULT_CARE_ROW_SET_SHA256
                ),
                "D0_counts_reproduced": (
                    int(np.count_nonzero(numeric_equal)) == item["equal_rows"]
                    and len(unequal_positions) == item["unequal_rows"] == 183
                ),
                "clone_split": clone_split == expected_clone_split,
                "every_mismatch_raw_positive": bool((mismatch_raw > 0.0).all()),
                "every_mismatch_terminal_positive_zero_bits": bool(
                    (mismatch_terminal_bits == 0).all()
                ),
                "raw_value_frequencies": frequencies == expected_frequencies,
                "no_other_bitwise_difference": (
                    len(unequal_positions) == 183
                    and row_set_sha == EXPECTED_ADULT_CARE_ROW_SET_SHA256
                ),
            }
            equality_rows.append(
                {
                    **common,
                    "rule": (
                        "the bitwise-unequal drawn-row set equals the committed "
                        "extensional D0 registration; every row has positive raw "
                        "and positive-zero terminal bits"
                    ),
                    "row_set": {
                        "axis": "/person/axis1",
                        "encoding": ADULT_CARE_ROW_SET_ENCODING,
                        "dtype": "<i8",
                        "byte_count": int(row_ids.nbytes),
                        "count": len(row_ids),
                        "sha256_expected": EXPECTED_ADULT_CARE_ROW_SET_SHA256,
                        "sha256_actual": row_set_sha,
                        "row_ids": row_ids.tolist(),
                        "uint8_full_axis_mask_sha256": mask_sha256(
                            np.isin(person_axis, row_ids)
                        ),
                    },
                    "clone_split_expected": expected_clone_split,
                    "clone_split_actual": clone_split,
                    "raw_value_frequencies_expected": expected_frequencies,
                    "raw_value_frequencies_actual": frequencies,
                    "checks": adult_checks,
                    "pass": all(adult_checks.values()),
                }
            )

    a16_ii = {
        "definition": (
            "rehash D0-pinned pool/banks/raw arrays and reproduce D0-4 "
            "lineage or direct-position alignment"
        ),
        "pool_file": pool_file_check,
        "lineage_digests": lineage,
        "targets": alignment_rows,
        "targets_passed": sum(row["pass"] for row in alignment_rows),
        "targets_total": len(alignment_rows),
        "pass": (
            pool_file_check["match"]
            and lineage["pass"]
            and all(row["pass"] for row in alignment_rows)
        ),
    }
    a17_iii = {
        "definition": (
            "bitwise raw/terminal equality on drawn rows for eight targets; "
            "exact committed 183-row extensional registration for adult care"
        ),
        "targets": equality_rows,
        "targets_passed": sum(row["pass"] for row in equality_rows),
        "targets_total": len(equality_rows),
        "pass": all(row["pass"] for row in equality_rows),
    }
    return a16_ii, a17_iii


def main() -> None:
    d0 = json.loads(D0_PATH.read_text())
    rehasher = Rehasher()

    roster = verify_roster()
    adopted = adopted_control_reverification(rehasher, roster["sidak_z"])
    a17_i = verify_a17_15_i(d0, rehasher)
    a16_ii, a17_iii = verify_a16_ii_and_a17_iii(d0, rehasher)

    gates = {
        "adopted_C0a_C0b_C5": adopted["pass"],
        "ratified_K_roster": roster["pass"],
        "A17-15(i)": a17_i["pass"],
        "A16-15(ii)": a16_ii["pass"],
        "A17-15(iii)": a17_iii["pass"],
    }
    result = {
        "artifact_kind": "qrf_drift_phase0_a17_setup_verification",
        "schema_version": 1,
        "status": "PASS" if all(gates.values()) else "FAIL",
        "output_path": str(OUT),
        "authority_note": (
            "The operative design is A17 SHA-256 a91d19cc...; historical "
            "v2.2 blobs are rehashed only as adopted C0b/C5 inputs. The old "
            "A16 design digest is not an expected authority."
        ),
        "adopted_control_reverification": adopted,
        "control_roster": roster,
        "setup_gates": {
            "A17-15(i)": a17_i,
            "A16-15(ii)": a16_ii,
            "A17-15(iii)": a17_iii,
        },
        "gate_summary": gates,
        "failed_gates": [name for name, passed in gates.items() if not passed],
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = {
        "status": result["status"],
        "gate_summary": gates,
        "adult_care_row_set_sha256": next(
            row["row_set"]["sha256_actual"]
            for row in a17_iii["targets"]
            if row["target"] == "pre_subsidy_care_expenses"
        ),
        "output": str(OUT),
        "output_sha256": rehasher.sha256_file(OUT),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
