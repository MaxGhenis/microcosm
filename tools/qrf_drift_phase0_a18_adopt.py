#!/usr/bin/env python3
"""Fail-closed verifier for A18 branch-2 control adoption.

This program does not recompute a control.  It verifies the sealed A18 G3
enumeration and the evidence from run 20260826-163955, then records exactly
which results A18 permits a later executor to adopt.  In branch 2, old C2 is
adopted and old C3 is explicitly excluded pending a fresh retargeted run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import qrf_drift_phase0_c4 as c4
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments"
DESIGN = EXP / "qrf_drift_validation_design.md"
D0_JSON = EXP / "qrf_drift_validation_d0.json"
D0_MARKDOWN = EXP / "qrf_drift_validation_d0.md"
BINDING = EXP / "qrf_drift_validation_a16_binding_texts.md"

DEFAULT_ENUMERATION = Path(
    "/private/tmp/qrf_phase0_a18_g3_split_enumeration.json"
)
DEFAULT_PHASE0 = Path("/private/tmp/qrf_phase0_a17_terminal_report.json")
DEFAULT_C0A = Path("/private/tmp/qrf_phase0_c0a.json")
DEFAULT_C0B = Path("/private/tmp/qrf_phase0_v22_c0b.json")
DEFAULT_C5 = Path("/private/tmp/qrf_phase0_v22_c5.json")
DEFAULT_SETUP = Path("/private/tmp/qrf_phase0_a17_setup.json")
DEFAULT_C4 = Path("/private/tmp/qrf_phase0_a17_c4.json")
DEFAULT_C2C3 = Path("/private/tmp/qrf_phase0_a17_c2c3.json")
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_a18_adoption.json")

A18_COMMIT = "8d553796e846012e7dc2663d7ffe108b6f965cca"
EXPECTED_AUTHORITY = {
    DESIGN: "5c8e55293215a7d1350c93825b1a4daf04e212bb84d17408b8750ed5d9d4e754",
    D0_JSON: "fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8",
    D0_MARKDOWN: "c4f3a9c56426025426e56428e9bce697a6cc6112f175be86ef9ef139bf79b601",
    BINDING: "7e288bce7496e1e7f41e33f078be2043673ca54ff31182caf2ce92eab68a81c1",
}

EXPECTED_EVIDENCE = {
    "enumeration": {
        "sha256": "e853cc8e41c1c2d98dde605a8ca951dfb283246062cf04e280e688291b5d1314",
        "kind": "qrf_drift_phase0_a18_g3_split_enumeration",
        "canonical_sha256": (
            "6f45c63094d5b5d5e48a0f60088ab43a58debbfb708c1e9fd0fa4d2dfb2c2dd3"
        ),
        "status_key": "status",
        "status": "SEALED",
    },
    "phase0": {
        "sha256": "e65378071bf9e9519b51eba30c63fd89ca08d982e35610bb5017fcf599e29142",
        "kind": "qrf_drift_validation_phase0_a16",
        "canonical_sha256": (
            "e1e3e22fee3c2b64d4bf7a9bf4911b37b82bbb0c5cf38d84fb4959de70f7e407"
        ),
        "status_key": "status",
        "status": "CONTROLS_FAILED",
    },
    "C0a": {
        "sha256": "d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962",
        "status_key": "status",
        "status": "PASS",
    },
    "C0b": {
        "sha256": "1c7bfd65660b14068c4bc96fae4b8d270cb447ea8fbbe42c8ef982c5f1dbf542",
        "kind": "qrf_phase0_v22_c0b_e4_and_a9_e2_control",
        "status_key": "status",
        "status": "PASS",
    },
    "C5": {
        "sha256": "7f00827190276615806e26d5c76eda7c413c49640fb843988770f58056dc584c",
        "status_key": "execution_status",
        "status": "PASS",
    },
    "setup": {
        "sha256": "eed8e569e19a5be0e3de67d6f11cb2cb2b7d583d7e3bc2a1602c2492206c81bd",
        "kind": "qrf_drift_phase0_a17_setup_verification",
        "status_key": "status",
        "status": "PASS",
    },
    "C4": {
        "sha256": "8cd95aafcdb896b8f6bedc86dcb030c912b277a6b28ba87d69bac0d79a5c06c5",
        "kind": "qrf_drift_phase0_a17_c4",
        "canonical_sha256": (
            "ac3622032553c9aded22b4e182bc5db764c12232fe71c343b18a71aec31dae98"
        ),
        "status_key": "status",
        "status": "PASS",
    },
    "C2C3": {
        "sha256": "78a20b894457395add4253fd1772c3fa66194bda8b4aba69a40f10e1bfc2fa2a",
        "kind": "qrf_drift_phase0_a17_c2c3",
        "canonical_sha256": (
            "65eb83dbdd77e79548b78abc34b4898ae3c972347e5eb35a8d40f481c82756d7"
        ),
        "status_key": "status",
        "status": "UNDERPOWERED",
    },
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
EXPECTED_STEP0_CANONICAL = (
    "988aa191a1eb83c35ce009cbc889f44dcf706884095d76f588a72124d05c0283"
)
EXPECTED_MANIFEST_COUNT = 6155
EXPECTED_K = 122
EXPECTED_COMPONENTS = {
    "C0b": 76,
    "C4_null_total": 40,
    "C2_C3_group_errors": 6,
}
EXPECTED_K_DIGEST = (
    "348386d9675172b65550ef7cb157fb1387e1d45331f61253aefe40dbe8f2bbc9"
)
EXPECTED_Z = 3.526967430023352

EXPECTED_TABLE_COUNT = 31
EXPECTED_TABLE_SHA = (
    "cfbc1dc7ddece6b9895306eb2e34865da79f0f882f52724a06dfc9bf412c264d"
)
EXPECTED_ALL_TRIPLES_COUNT = 32
EXPECTED_ALL_TRIPLES_SHA = (
    "514c561bd9803fd6e7176540d43cfe4a688cf7c82386eefa69d102268be5b3be"
)
EXPECTED_SELECTED = {
    "G3_column": "is_incapable_of_self_care",
    "pattern": "pattern_03_76a0101a",
    "row_sha256": (
        "0cc8cd8f220e9c2f3ae48fdef141546356d2d780fdd72607f25c0957cf08b91b"
    ),
    "split_count": 16,
    "table_order": 6,
    "target": "pre_subsidy_care_expenses",
    "total_split_gain": 190276014528.88873,
    "total_split_gain_hex": "0x1.626aac8e071c2p+37",
}

EXPECTED_C3_IDS = [
    (
        "r=control|t=child_support_received|p=_|l=_|row=C3_oracle_error|"
        "g=G1|prior=_|gq=_|d=_|rep=_|fold=_|v=final"
    ),
    (
        "r=control|t=child_support_received|p=_|l=_|row=C3_oracle_error|"
        "g=G2|prior=_|gq=_|d=_|rep=_|fold=_|v=final"
    ),
    (
        "r=control|t=child_support_received|p=_|l=_|row=C3_oracle_error|"
        "g=G3|prior=_|gq=_|d=_|rep=_|fold=_|v=final"
    ),
]


def require(condition: bool, message: str) -> None:
    """Raise a uniform fail-closed error when an evidence invariant fails."""
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(c4.canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing evidence file: {path}")
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"evidence is not a JSON object: {path}")
    return value


def verify_canonical_payload(
    value: dict[str, Any],
    *,
    expected_kind: str,
    expected_digest: str,
) -> str:
    """Recompute an evidence artifact's self-excluding canonical digest."""
    require(
        value.get("artifact_kind") == expected_kind,
        f"artifact kind mismatch: {value.get('artifact_kind')!r}",
    )
    recorded = value.get("canonical_sha256")
    require(recorded == expected_digest, "unexpected recorded canonical digest")
    scope = dict(value)
    scope.pop("canonical_sha256", None)
    actual = canonical_sha256(scope)
    require(actual == recorded, "canonical evidence payload has changed")
    return actual


def verify_evidence(
    paths: dict[str, Path],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load and pin every evidence file before inspecting its content."""
    payloads: dict[str, dict[str, Any]] = {}
    references: dict[str, dict[str, Any]] = {}
    require(set(paths) == set(EXPECTED_EVIDENCE), "evidence path roster changed")
    for name, path in paths.items():
        spec = EXPECTED_EVIDENCE[name]
        actual = sha256_file(path)
        require(actual == spec["sha256"], f"{name} evidence file digest changed")
        value = load_json(path)
        require(
            value.get(spec["status_key"]) == spec["status"],
            f"{name} evidence has unexpected status",
        )
        canonical = None
        if "canonical_sha256" in spec:
            canonical = verify_canonical_payload(
                value,
                expected_kind=spec["kind"],
                expected_digest=spec["canonical_sha256"],
            )
        elif "kind" in spec:
            require(
                value.get("artifact_kind") == spec["kind"],
                f"{name} artifact kind changed",
            )
        payloads[name] = value
        references[name] = {
            "path": str(path.resolve()),
            "sha256": actual,
            "canonical_sha256": canonical,
            "status": spec["status"],
        }
    return payloads, references


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
    )


def verify_authority(enumeration: dict[str, Any]) -> dict[str, Any]:
    """Verify the live A18 authority and its originating commit blob."""
    files = []
    for path, expected in EXPECTED_AUTHORITY.items():
        actual = sha256_file(path)
        require(actual == expected, f"current authority changed: {path}")
        files.append(
            {"path": str(path.resolve()), "sha256": actual, "match": True}
        )

    design_relative = str(DESIGN.relative_to(ROOT))
    design_blob = git_blob(A18_COMMIT, design_relative)
    design_blob_sha = hashlib.sha256(design_blob).hexdigest()
    require(
        design_blob_sha == EXPECTED_AUTHORITY[DESIGN],
        "A18 authority commit does not contain the pinned design",
    )
    require(design_blob == DESIGN.read_bytes(), "live design differs from A18 commit")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", A18_COMMIT, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    require(ancestry.returncode == 0, "A18 authority commit is not in HEAD history")

    authority = enumeration.get("authority", {})
    expected_records = {
        "design": (DESIGN, EXPECTED_AUTHORITY[DESIGN]),
        "d0_json": (D0_JSON, EXPECTED_AUTHORITY[D0_JSON]),
        "d0_markdown": (D0_MARKDOWN, EXPECTED_AUTHORITY[D0_MARKDOWN]),
        "a16_binding": (BINDING, EXPECTED_AUTHORITY[BINDING]),
    }
    for name, (path, digest) in expected_records.items():
        record = authority.get(name, {})
        require(Path(record.get("path", "")).resolve() == path.resolve(), f"bad {name} path")
        require(record.get("sha256") == digest, f"bad {name} authority digest")
    design_record = authority["design"]
    require(design_record.get("commit") == A18_COMMIT, "bad A18 commit binding")
    require(design_record.get("amendment") == "v2.7/A18", "bad amendment binding")
    return {
        "amendment": "v2.7/A18",
        "commit": A18_COMMIT,
        "commit_design_blob_sha256": design_blob_sha,
        "head_contains_commit": True,
        "files": files,
    }


def _hash_record(value: dict[str, Any]) -> str | None:
    candidates = []
    for key in (
        "sha256_expected",
        "expected_sha256",
        "sha256",
        "sha256_actual",
        "actual_sha256",
    ):
        digest = value.get(key)
        if isinstance(digest, str) and len(digest) == 64:
            candidates.append(digest)
    if not candidates:
        return None
    require(len(set(candidates)) == 1, f"recorded file hashes disagree: {value}")
    return candidates[0]


def iter_file_records(
    value: Any,
    pointer: str = "",
) -> Iterator[tuple[str, dict[str, Any], str]]:
    """Yield recursively recorded file hashes, retaining JSON pointers."""
    if isinstance(value, dict):
        path = value.get("path")
        digest = _hash_record(value) if isinstance(path, str) else None
        if isinstance(path, str) and digest is not None:
            yield pointer or "/", value, digest
        for key, child in value.items():
            escaped = key.replace("~", "~0").replace("/", "~1")
            yield from iter_file_records(child, f"{pointer}/{escaped}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_file_records(child, f"{pointer}/{index}")


def _read_recorded_path(path: str) -> tuple[str, int, str]:
    if path.startswith("git:"):
        commit, relative = path[4:].split(":", 1)
        content = git_blob(commit, relative)
        return path, len(content), hashlib.sha256(content).hexdigest()
    resolved = Path(path).resolve()
    require(resolved.is_file(), f"recorded input is missing: {path}")
    return str(resolved), resolved.stat().st_size, sha256_file(resolved)


def verify_recorded_live_inputs(
    artifacts: dict[str, dict[str, Any]],
    *,
    design_path: Path = DESIGN,
) -> dict[str, Any]:
    """Rehash every recorded non-design file, once per unique path."""
    gathered: dict[str, dict[str, Any]] = {}
    skipped_design_records = 0
    for artifact_name, value in artifacts.items():
        for pointer, record, expected in iter_file_records(value):
            path = record["path"]
            if not path.startswith("git:") and Path(path).resolve() == design_path.resolve():
                # Old artifacts correctly cite the A17 design.  A18 supersedes
                # that local pathname, which is verified independently above.
                skipped_design_records += 1
                continue
            require(record.get("match", True) is True, f"record was not a match: {path}")
            identity, size, actual = _read_recorded_path(path)
            require(actual == expected, f"recorded live input changed: {path}")
            if "bytes" in record:
                require(record["bytes"] == size, f"recorded size changed: {path}")
            current = gathered.setdefault(
                identity,
                {
                    "path": identity,
                    "bytes": size,
                    "sha256": actual,
                    "sources": [],
                },
            )
            require(current["sha256"] == actual, f"conflicting hash for {identity}")
            current["sources"].append(
                {"artifact": artifact_name, "pointer": pointer}
            )
    files = sorted(gathered.values(), key=lambda item: item["path"])
    return {
        "status": "PASS",
        "all_match": True,
        "unique_file_count": len(files),
        "skipped_superseded_local_design_records": skipped_design_records,
        "files": files,
    }


def verify_branch2(
    enumeration: dict[str, Any],
    *,
    expected_table_count: int = EXPECTED_TABLE_COUNT,
    expected_table_sha: str = EXPECTED_TABLE_SHA,
    expected_all_count: int = EXPECTED_ALL_TRIPLES_COUNT,
    expected_all_sha: str = EXPECTED_ALL_TRIPLES_SHA,
    expected_selected: dict[str, Any] = EXPECTED_SELECTED,
) -> dict[str, Any]:
    """Recompute the A18 branch-2 table, selection, and every named seal."""
    scope = enumeration.get("scope", {})
    require(scope.get("readings_computed") is False, "enumeration computed readings")
    require(scope.get("target_count") == 9, "enumeration target count changed")
    require(scope.get("gate_count") == 36, "enumeration gate count changed")

    all_triples = enumeration.get("all_G3_triples", {})
    all_rows = all_triples.get("rows", [])
    require(len(all_rows) == expected_all_count, "all-G3 row count changed")
    require(all_triples.get("row_count") == len(all_rows), "bad all-G3 count seal")
    require(canonical_sha256(all_rows) == expected_all_sha, "bad all-G3 table seal")
    require(all_triples.get("sha256") == expected_all_sha, "recorded all-G3 seal changed")
    require(
        [row["stable_order"]["triple"] for row in all_rows]
        == list(range(len(all_rows))),
        "all-G3 rows are not in stable D0 order",
    )

    table = enumeration.get("sealed_split_table", {})
    table_rows = table.get("rows", [])
    filtered = []
    for row in all_rows:
        if int(row["split_count"]) >= 1:
            filtered.append({"table_order": len(filtered), **row})
    require(table_rows == filtered, "sealed split table is not the filtered G3 table")
    require(len(table_rows) == expected_table_count, "split-table count changed")
    require(table.get("row_count") == len(table_rows), "bad split-table count seal")
    sealed_payload = {"definition": table.get("definition"), "rows": table_rows}
    require(canonical_sha256(sealed_payload) == expected_table_sha, "bad table seal")
    require(table.get("sha256") == expected_table_sha, "recorded table seal changed")

    disposition = enumeration.get("mechanical_disposition", {})
    require(disposition.get("branch") == 2, "A18 enumeration did not select branch 2")
    require(
        disposition.get("action") == "RETARGET_C3_TO_LARGEST_GAIN_TRIPLE",
        "A18 branch-2 action changed",
    )
    selected_row = min(
        table_rows,
        key=lambda row: (-float(row["total_split_gain"]), int(row["table_order"])),
    )
    recomputed = {
        "table_order": int(selected_row["table_order"]),
        "target": selected_row["target"],
        "pattern": selected_row["pattern"],
        "G3_column": selected_row["G3_column"],
        "split_count": int(selected_row["split_count"]),
        "total_split_gain": float(selected_row["total_split_gain"]),
        "total_split_gain_hex": selected_row["total_split_gain_hex"],
        "row_sha256": canonical_sha256(selected_row),
    }
    require(recomputed == expected_selected, "largest-gain selected row changed")
    require(disposition.get("selected") == recomputed, "recorded selection is wrong")
    return {
        "branch": 2,
        "action": disposition["action"],
        "all_G3_triples": {"row_count": len(all_rows), "sha256": expected_all_sha},
        "sealed_split_table": {
            "row_count": len(table_rows),
            "sha256": expected_table_sha,
        },
        "selected": recomputed,
    }


def verify_step0(
    phase0: dict[str, Any],
    *,
    expected_seals: dict[str, str] = EXPECTED_STEP0_SEALS,
    expected_count: int = EXPECTED_MANIFEST_COUNT,
    expected_step0_sha: str = EXPECTED_STEP0_CANONICAL,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Verify all six Step-0 seals and exact manifest/statistic coverage."""
    step0 = phase0.get("step0")
    require(isinstance(step0, dict), "Phase-0 evidence lacks Step 0")
    require(step0.get("seals") == expected_seals, "recorded Step-0 seals changed")
    objects = {
        "operator_table_sha256": step0["operator_table"],
        "json_schema_sha256": step0["json_schema"],
        "required_id_manifest_sha256": step0["required_id_manifest"],
        "adjudication_table_sha256": step0["adjudication_table"],
        "default_appendix_sha256": step0["default_appendix"],
    }
    actual = {name: canonical_sha256(value) for name, value in objects.items()}
    actual["composite_sha256"] = canonical_sha256(
        {
            "operator_table": step0["operator_table"],
            "json_schema": step0["json_schema"],
            "required_id_manifest": step0["required_id_manifest"],
            "adjudication_table": step0["adjudication_table"],
            "default_appendix": step0["default_appendix"],
        }
    )
    require(actual == expected_seals, "Step-0 object seals do not reproduce")
    require(
        canonical_sha256(step0) == expected_step0_sha,
        "complete Step-0 object changed",
    )
    require(
        step0.get("sealed_before_fresh_statistics") is True,
        "Step 0 was not sealed before fresh statistics",
    )

    manifest = step0["required_id_manifest"]
    require(len(manifest) == expected_count, "Step-0 manifest count changed")
    manifest_by_id = {item["id"]: item for item in manifest}
    require(len(manifest_by_id) == len(manifest), "duplicate Step-0 manifest ID")
    statistics = phase0.get("statistics", [])
    statistics_by_id = {item["id"]: item for item in statistics}
    require(len(statistics) == expected_count, "Phase-0 statistic count changed")
    require(len(statistics_by_id) == len(statistics), "duplicate statistic ID")
    require(
        set(statistics_by_id) == set(manifest_by_id),
        "statistics do not cover the exact Step-0 manifest",
    )
    for identifier, spec in manifest_by_id.items():
        row = statistics_by_id[identifier]
        for field in ("id", "dimensions", "record_type", "family", "gated"):
            require(row.get(field) == spec.get(field), f"static field changed: {identifier}")
    return manifest, {
        "status": "PASS",
        "manifest_count": len(manifest),
        "manifest_unique_ids": len(manifest_by_id),
        "statistics_count": len(statistics),
        "complete_step0_sha256": expected_step0_sha,
        "seals": actual,
    }


def roster_ids(manifest: list[dict[str, Any]]) -> tuple[list[str], dict[str, int]]:
    ids = []
    components = {name: 0 for name in EXPECTED_COMPONENTS}
    for entry in manifest:
        dimensions = entry["dimensions"]
        if dimensions["row"] == "C0b_E2" and dimensions["variant"] == "repeated_draw":
            ids.append(entry["id"])
            components["C0b"] += 1
        elif dimensions["row"] == "C4_null_total":
            ids.append(entry["id"])
            components["C4_null_total"] += 1
        elif dimensions["row"] in {"C2_oracle_error", "C3_oracle_error"}:
            ids.append(entry["id"])
            components["C2_C3_group_errors"] += 1
    return ids, components


def retarget_c3_slots(
    manifest: list[dict[str, Any]],
    selected: dict[str, Any],
    *,
    expected_ids: list[str] = EXPECTED_C3_IDS,
) -> dict[str, Any]:
    """Bind the new C3 context without mutating any sealed statistic ID."""
    entries = [
        item for item in manifest if item["dimensions"]["row"] == "C3_oracle_error"
    ]
    ids = [item["id"] for item in entries]
    require(ids == expected_ids, "the three stable C3 roster slots changed")
    slots = []
    for entry in entries:
        slots.append(
            {
                "id": entry["id"],
                "sealed_dimensions_unchanged": entry["dimensions"],
                "retargeted_context": {
                    "target": selected["target"],
                    "pattern": selected["pattern"],
                    "G3_column": selected["G3_column"],
                    "reported_group": entry["dimensions"]["group"],
                    "selected_row_sha256": selected["row_sha256"],
                },
                "status": "PENDING_FRESH_RETARGETED_C3",
            }
        )
    return {
        "slot_count": len(slots),
        "stable_ids_preserved": ids,
        "id_mutations": 0,
        "intervention": (
            "zero the selected column on observed fit-row carriers when any "
            "exist; otherwise apply the declared 1.25x transform"
        ),
        "slots": slots,
    }


def verify_roster(
    manifest: list[dict[str, Any]],
    phase0: dict[str, Any],
    setup: dict[str, Any],
    selected: dict[str, Any],
) -> dict[str, Any]:
    ids, components = roster_ids(manifest)
    digest = canonical_sha256(ids)
    sidak_z = float(norm.ppf((1.0 + 0.95 ** (1.0 / len(ids))) / 2.0))
    require(len(ids) == EXPECTED_K, "ratified K changed")
    require(components == EXPECTED_COMPONENTS, "roster components changed")
    require(digest == EXPECTED_K_DIGEST, "ordered roster digest changed")
    require(sidak_z == EXPECTED_Z, "ratified Sidak z* changed")

    for name, record in (
        ("Phase-0", phase0.get("controls", {}).get("K", {})),
        ("setup", setup.get("control_roster", {})),
    ):
        require(record.get("K") == EXPECTED_K, f"{name} K changed")
        require(record.get("components") == EXPECTED_COMPONENTS, f"{name} components changed")
        require(record.get("ordered_ids_sha256") == EXPECTED_K_DIGEST, f"{name} roster digest changed")
        require(record.get("sidak_z") == EXPECTED_Z, f"{name} z* changed")
        require(record.get("pass") is True, f"{name} roster is not a PASS")

    return {
        "status": "PASS",
        "K": len(ids),
        "components": components,
        "ordered_ids_sha256": digest,
        "sidak_formula": "Phi^-1((1+0.95^(1/K))/2)",
        "sidak_z": sidak_z,
        "C3_retargeted_context_slots": retarget_c3_slots(
            manifest, selected
        ),
    }


def branch2_control_disposition(c2c3: dict[str, Any]) -> dict[str, Any]:
    """Adopt C2 alone; turn the old C3 result into excluded evidence."""
    controls = c2c3.get("controls", {})
    require(set(controls) == {"C2", "C3"}, "C2/C3 control roster changed")
    c2_control = controls["C2"]
    c3_control = controls["C3"]
    require(c2_control.get("status") == "PASS", "old C2 is not PASS")
    require(c2_control.get("pass") is True, "old C2 recovery failed")
    require(c2_control.get("power", {}).get("pass") is True, "old C2 power failed")
    require(c3_control.get("status") == "UNDERPOWERED", "old C3 status changed")
    require(c3_control.get("pass") is False, "old C3 unexpectedly passed")
    require(c3_control.get("power", {}).get("pass") is False, "old C3 power unexpectedly passed")
    require(c3_control.get("power", {}).get("absolute_oracle") == 0, "old C3 oracle is not zero")
    return {
        "adopted": {
            "C2": {
                "status": "PASS_ADOPTED_A18",
                "prior_status": c2_control["status"],
                "recovery_pass": True,
                "power_pass": True,
            }
        },
        "excluded": {
            "C3": {
                "status": "EXCLUDED_PENDING_FRESH_RETARGETED_C3",
                "prior_status": c3_control["status"],
                "prior_oracle": c3_control["power"]["absolute_oracle"],
                "reason": "A18 branch 2 requires C3 alone to be rerun on the sealed largest-gain triple",
                "old_C3_adopted": False,
            }
        },
    }


def verify_control_statuses(
    payloads: dict[str, dict[str, Any]],
    manifest: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify adopted PASS components and the exact C2-only disposition."""
    c0a = payloads["C0a"]
    require(c0a.get("control") == "C0a", "C0a label changed")
    require(c0a.get("comparisons") == 36, "C0a comparison count changed")
    require(c0a.get("cells") == 72, "C0a cell count changed")
    require(c0a.get("mismatched_comparisons") == 0, "C0a has mismatches")
    require(len(c0a.get("rows", [])) == 36, "C0a row count changed")
    require(all(row.get("pass") is True for row in c0a["rows"]), "C0a row failed")

    c0b = payloads["C0b"]
    summary = c0b.get("summary", {})
    require(len(c0b.get("patterns", [])) == 36, "C0b pattern count changed")
    require(len(c0b.get("per_class_controls", [])) == 76, "C0b class count changed")
    require(summary.get("e4_bit_identical_pass") is True, "C0b E4 failed")
    require(summary.get("e2_repeated_draw_control_pass") is True, "C0b E2 failed")
    require(all(row.get("e4_pattern_pass") is True for row in c0b["patterns"]), "C0b pattern failed")
    require(
        all(
            abs(float(row["mc_mean_z"])) <= EXPECTED_Z
            and abs(float(row["production_single_draw_z"])) <= EXPECTED_Z
            for row in c0b["per_class_controls"]
        ),
        "C0b fails the ratified A17 threshold",
    )

    c5 = payloads["C5"]
    require(c5.get("control") == "C5", "C5 label changed")
    require(c5.get("gate_disposition") == "PASS", "C5 gate failed")
    require(c5.get("checks_total") == c5.get("checks_passed") == 8, "C5 count changed")
    booleans = c5.get("exact_match_booleans", [])
    require(len(booleans) == 8, "C5 boolean count changed")
    require(all(row.get("exact_match") is True for row in booleans), "C5 mismatch")
    require(
        c5.get("artifact_digest_bundle_sha256")
        == "b43d7443fca595d30d01c86cea3cb0f8648ca23c0f8939a0299d195e2cac50ae",
        "C5 bundle seal changed",
    )

    setup = payloads["setup"]
    expected_gates = {
        "adopted_C0a_C0b_C5": True,
        "ratified_K_roster": True,
        "A17-15(i)": True,
        "A16-15(ii)": True,
        "A17-15(iii)": True,
    }
    require(setup.get("gate_summary") == expected_gates, "setup gates changed")
    require(setup.get("failed_gates") == [], "setup has failed gates")
    adopted_setup = setup.get("adopted_control_reverification", {})
    require(adopted_setup.get("pass") is True, "setup adoption failed")
    require(adopted_setup.get("all_file_digests_match") is True, "setup input failed")
    require(
        all(gate.get("pass") is True for gate in setup.get("setup_gates", {}).values()),
        "a setup component failed",
    )

    c4_payload = payloads["C4"]
    c4_ids = {
        item["id"]
        for item in manifest
        if item["dimensions"]["row"] == "C4_null_total"
    }
    c4_rows = c4_payload.get("statistics", [])
    require(len(c4_rows) == 40, "C4 roster count changed")
    require({row["id"] for row in c4_rows} == c4_ids, "C4 roster IDs changed")
    require(all(row.get("pass") is True for row in c4_rows), "C4 statistic failed")
    require(c4_payload.get("summary", {}).get("all_run_cells_pass") is True, "C4 summary failed")
    exact_zeros = c4_payload.get("deterministic_empty_G3_checks", [])
    require(len(exact_zeros) == 20, "C4 exact-zero count changed")
    require(all(row.get("pass") is True and row.get("value") == 0 for row in exact_zeros), "C4 exact-zero check failed")

    c2c3 = payloads["C2C3"]
    rows = c2c3.get("statistics", [])
    expected_ids = {
        item["id"]
        for item in manifest
        if item["dimensions"]["row"] in {"C2_oracle_error", "C3_oracle_error"}
    }
    require(len(rows) == 6, "C2/C3 recovery roster count changed")
    require({row["id"] for row in rows} == expected_ids, "C2/C3 recovery IDs changed")
    require(all(row.get("pass") is True for row in rows), "a C2/C3 recovery row failed")
    require(c2c3.get("summary", {}).get("rostered_cells_passed") == 6, "six-row recovery summary changed")
    disposition = branch2_control_disposition(c2c3)
    return {
        "adopted_controls": {
            "C0a": {"status": "PASS_ADOPTED_A18", "comparisons": 36, "cells": 72},
            "C0b": {"status": "PASS_ADOPTED_A18", "patterns": 36, "E2_cells": 76},
            "C5": {"status": "PASS_ADOPTED_A18", "exact_matches": 8},
            "A17_setup": {"status": "PASS_ADOPTED_A18", "gates": 5},
            "C4": {"status": "PASS_ADOPTED_A18", "stochastic_cells": 40, "exact_zero_checks": 20},
            **disposition["adopted"],
        },
        "excluded_controls": disposition["excluded"],
        "adopted_control_order": ["C0a", "C0b", "C5", "A17_setup", "C4", "C2"],
        "old_C3_present_in_adopted_controls": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enumeration", type=Path, default=DEFAULT_ENUMERATION)
    parser.add_argument("--phase0-json", type=Path, default=DEFAULT_PHASE0)
    parser.add_argument("--c0a", type=Path, default=DEFAULT_C0A)
    parser.add_argument("--c0b", type=Path, default=DEFAULT_C0B)
    parser.add_argument("--c5", type=Path, default=DEFAULT_C5)
    parser.add_argument("--setup", type=Path, default=DEFAULT_SETUP)
    parser.add_argument("--c4", type=Path, default=DEFAULT_C4)
    parser.add_argument("--c2c3", type=Path, default=DEFAULT_C2C3)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = {
        "enumeration": args.enumeration,
        "phase0": args.phase0_json,
        "C0a": args.c0a,
        "C0b": args.c0b,
        "C5": args.c5,
        "setup": args.setup,
        "C4": args.c4,
        "C2C3": args.c2c3,
    }
    payloads, evidence = verify_evidence(paths)
    authority = verify_authority(payloads["enumeration"])
    branch2 = verify_branch2(payloads["enumeration"])
    manifest, step0 = verify_step0(payloads["phase0"])
    roster = verify_roster(
        manifest,
        payloads["phase0"],
        payloads["setup"],
        branch2["selected"],
    )
    controls = verify_control_statuses(payloads, manifest)
    live_inputs = verify_recorded_live_inputs(
        {
            name: payloads[name]
            for name in ("enumeration", "setup", "C4", "C2C3", "C0b", "C5")
        }
    )

    result = {
        "artifact_kind": "qrf_drift_phase0_a18_branch2_adoption",
        "schema_version": 1,
        "status": "SEALED_ADOPTION",
        "authority": authority,
        "evidence": evidence,
        "recorded_live_input_verification": live_inputs,
        "step0": step0,
        "control_roster": roster,
        "branch2": branch2,
        "controls": controls,
        "next_required_action": (
            "rerun C3 alone on pre_subsidy_care_expenses / "
            "pattern_03_76a0101a / is_incapable_of_self_care; do not "
            "proceed to readings until that fresh C3 passes recovery and power"
        ),
        "readings_authorized": False,
        "statistics": [],
    }
    output_sha = c4.write_canonical_result(args.out, result)
    print(
        f"RESULT {args.out} sha256={output_sha} "
        f"canonical_sha256={result['canonical_sha256']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
