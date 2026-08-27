#!/usr/bin/env python3
"""Assemble the v2.7/A18 QRF-drift Phase-0 report.

This is a pure assembly lane.  It verifies the immutable 6,155-ID Step-0
bundle, the A18 G3 enumeration/adoption evidence, and the fresh retargeted C3
artifact.  It then merges independently sealed P0/P1/P2/P5/P6/P7/C1 reading
artifacts, computes the A16 verdict rules, validates the original JSON Schema,
and derives Markdown from the authoritative JSON.

The sealed C3 statistic IDs deliberately keep their historical
``target=child_support_received`` dimensions.  A18's evaluated
``pre_subsidy_care_expenses / pattern_03_76a0101a /
is_incapable_of_self_care`` context is carried as source metadata and in the
control section; changing the IDs would invalidate Step 0.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from statistics import NormalDist
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments"
DESIGN = EXP / "qrf_drift_validation_design.md"
D0_JSON = EXP / "qrf_drift_validation_d0.json"
D0_MARKDOWN = EXP / "qrf_drift_validation_d0.md"
BINDING = EXP / "qrf_drift_validation_a16_binding_texts.md"
P1_EXECUTOR = ROOT / "tools/qrf_drift_phase0_p1.py"

DEFAULT_BASE = Path("/private/tmp/qrf_phase0_a17_terminal_report.json")
DEFAULT_ENUMERATION = Path("/private/tmp/qrf_phase0_a18_g3_split_enumeration.json")
DEFAULT_ADOPTION = Path("/private/tmp/qrf_phase0_a18_adoption.json")
DEFAULT_C3 = Path("/private/tmp/qrf_phase0_a18_c3.json")
DEFAULT_JSON = EXP / "qrf_drift_validation_phase0.json"
DEFAULT_MARKDOWN = EXP / "qrf_drift_validation_phase0.md"

EXECUTION_VERSION = "v2.7/A18"
A18_COMMIT = "8d553796e846012e7dc2663d7ffe108b6f965cca"
EXPECTED_AUTHORITY = {
    DESIGN: "5c8e55293215a7d1350c93825b1a4daf04e212bb84d17408b8750ed5d9d4e754",
    D0_JSON: "fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8",
    D0_MARKDOWN: "c4f3a9c56426025426e56428e9bce697a6cc6112f175be86ef9ef139bf79b601",
    BINDING: "7e288bce7496e1e7f41e33f078be2043673ca54ff31182caf2ce92eab68a81c1",
}
EXPECTED_STEP0_SEALS = {
    "operator_table_sha256": "447f7c9f00220440b7ad3825223f01fec8bed28e16e6eda2a851afdda64a6e23",
    "json_schema_sha256": "1a951262e9f9420fa8bc4462d2b53f697ab428ddcdb8e820021be80983fe54d7",
    "required_id_manifest_sha256": "c2ba7add0445a91715c491d78b83677844f90767414bdd32a7511fff1d676ec9",
    "adjudication_table_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "default_appendix_sha256": "4b58de099a1edcc11bdfbfef21ec8c06d835bca67ca9c80d55a4346beae32332",
    "composite_sha256": "2cabf69c9d91801e16686a46cf904bc346c0e009162ad2bb91eda996da73e9b8",
}
EXPECTED_STEP0_SHA = "988aa191a1eb83c35ce009cbc889f44dcf706884095d76f588a72124d05c0283"
EXPECTED_MANIFEST_COUNT = 6155
EXPECTED_K = 122
EXPECTED_K_DIGEST = "348386d9675172b65550ef7cb157fb1387e1d45331f61253aefe40dbe8f2bbc9"
EXPECTED_Z = 3.526967430023352
EXPECTED_SPLIT_TABLE_SHA = (
    "cfbc1dc7ddece6b9895306eb2e34865da79f0f882f52724a06dfc9bf412c264d"
)
EXPECTED_SELECTED_SHA = (
    "0cc8cd8f220e9c2f3ae48fdef141546356d2d780fdd72607f25c0957cf08b91b"
)
EXPECTED_P1_EXECUTOR_SHA = (
    "3230692e61f8fb5c98a5a7fbcde563a57c69fd9d8833ec6aba853031014b3e72"
)
P1_EXECUTION_COMMIT = "7ef29548844b60be4c8cd6c85b0a66339542290f"
EXPECTED_P2_EVIDENCED_UNAVAILABLE = 312
EXPECTED_P6_EVIDENCED_UNAVAILABLE = 504

NA = "_"
LEGS = ("positive", "negative")
TOP_LEVEL_ROWS = ("L0", "B1", "B2", "T1", "T2", "T3", "T4", "T5")
LEVEL_ROWS = (
    "J0",
    "J1",
    "J2",
    "P_D",
    "P_R",
    "I_raw",
    "I_dec",
    "I_q",
    "I_o",
    "I_acs",
    "D",
)
P0_SETUP_ROWS = {
    "P0_A16_15",
    "P0_bank_drawn_count",
    "P0_S_q_count",
    "P0_S_q_mask_sha256",
}
INCOMPLETE_STATUSES = {"NOT_RUN_CONTROLS_FAILED", "NOT_RUN_PRIORITY", "UNAVAILABLE"}
INCOMPLETE_STATUS_PRIORITY = (
    "NOT_RUN_CONTROLS_FAILED",
    "NOT_RUN_PRIORITY",
    "UNAVAILABLE",
)
P6_COMPLETE_NO_SURFACE = "COMPLETE_WITH_NO_SURFACE"
P6_SEALED_DISPOSITION = "COMPLETE_WITH_NO_SURFACE_ROWS"
P2_NOT_VALIDATED_DISPOSITION = "NOT_VALIDATED"
P2_JOINT_DOMAIN_DISPOSITION = "A16-31 joint hybrid predicates not enumerated at D0"
P6_STAGE_ORDER = (
    "full_asec_source",
    "fit_sample_5000",
    "first_hop_draw",
    "producer_codec",
    "producer_constraints",
    "J1_donor_projection",
    "clone2_tail_exclusion",
    "clone_weight_bridge",
    "bridge_producer_value_bridge",
    "bridge_clone_weight_bridge",
    "bridge_sum_equals_B1",
    "boundary_bridge",
    "transfer_fit_rows",
    "recipient_raw_draw",
    "recipient_codec",
    "recipient_structural",
)
P6_VARIANT_ORDER = (
    "mask_sha256",
    "sign_count",
    "weighted_sign_mass",
    "incidence",
    "seed",
    "diagnostic_only",
)
P0_PATH_OPERATOR_STAGE = {
    "authorized": "recipient_raw_draw",
    "null_before": "recipient_raw_draw",
    "drawn": "recipient_raw_draw",
    "finite_decode": "recipient_codec",
    "passed_all": "recipient_codec",
}
P0_PATH_EXECUTOR_ANCHOR = {
    "authorized": "_run_candidate_target:1512-1514; _path_census:203-247",
    "null_before": "_run_candidate_target:1512-1514; _path_census:203-247",
    "drawn": "_run_candidate_target:1512-1515; _path_census:203-247",
    "finite_decode": (
        "_run_candidate_target:1512-1516; _production_codec:604-672; "
        "_path_census:203-247"
    ),
    "passed_all": "_run_candidate_target:1512-1519; _path_census:203-247",
}

SSI_DIRECT_INPUTS = (
    "child_support_received",
    "workers_compensation",
    "unemployment_compensation",
    "disability_benefits",
)
SSI_NOT_DIRECT_INPUTS = (
    "child_support_expense",
    "weeks_unemployed",
    "spm_unit_energy_subsidy",
    "pre_subsidy_care_expenses",
    "self_employment_income_last_year",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-json", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--enumeration", type=Path, default=DEFAULT_ENUMERATION)
    parser.add_argument("--adoption", type=Path, default=DEFAULT_ADOPTION)
    parser.add_argument("--c3", type=Path, default=DEFAULT_C3)
    parser.add_argument(
        "--baseline-crossrung",
        type=Path,
        required=True,
        help="authoritative sealed two-target A15.53 baseline1pct replay",
    )
    parser.add_argument("--p1", type=Path)
    parser.add_argument("--p2", type=Path, action="append", default=[])
    parser.add_argument("--p5", type=Path, action="append", default=[])
    parser.add_argument("--c1", type=Path, action="append", default=[])
    parser.add_argument(
        "--readings-barrier",
        type=Path,
        help=(
            "self-sealed P0/P1/P2/P5/P6/P7 completion/disposition barrier; "
            "NOT_RUN_PRIORITY probe dispositions are propagated to manifest cells"
        ),
    )
    parser.add_argument(
        "--reading-artifact",
        type=Path,
        action="append",
        default=[],
        help="additional self-sealed artifact carrying a statistics array",
    )
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value: float) -> str:
    """RFC-8785-compatible binary64 spelling used by sealed Step 0."""
    require(math.isfinite(value), "nonfinite JSON numbers must be strings")
    if value == 0.0:
        return "0"
    raw = repr(float(value)).lower()
    absolute = abs(value)
    if 1e-6 <= absolute < 1e21:
        if "e" in raw:
            coefficient, exponent_text = raw.split("e")
            exponent = int(exponent_text)
            sign = ""
            if coefficient.startswith("-"):
                sign, coefficient = "-", coefficient[1:]
            digits = coefficient.replace(".", "")
            decimal_position = (
                coefficient.index(".") if "." in coefficient else len(coefficient)
            ) + exponent
            if decimal_position <= 0:
                raw = sign + "0." + "0" * (-decimal_position) + digits
            elif decimal_position >= len(digits):
                raw = sign + digits + "0" * (decimal_position - len(digits))
            else:
                raw = sign + digits[:decimal_position] + "." + digits[decimal_position:]
        return raw[:-2] if raw.endswith(".0") else raw
    if "e" not in raw:
        return raw[:-2] if raw.endswith(".0") else raw
    coefficient, exponent_text = raw.split("e")
    exponent = int(exponent_text)
    if coefficient.endswith(".0"):
        coefficient = coefficient[:-2]
    return f"{coefficient}e{'+' if exponent >= 0 else ''}{exponent}"


def canonical_bytes(value: Any) -> bytes:
    def encode(item: Any) -> str:
        if item is None:
            return "null"
        if item is True:
            return "true"
        if item is False:
            return "false"
        if isinstance(item, str):
            return json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        if isinstance(item, int) and not isinstance(item, bool):
            return str(item)
        if isinstance(item, float):
            return _number(item)
        if isinstance(item, list):
            return "[" + ",".join(encode(child) for child in item) + "]"
        if isinstance(item, dict):
            return (
                "{"
                + ",".join(
                    encode(key) + ":" + encode(item[key]) for key in sorted(item)
                )
                + "}"
            )
        raise TypeError(f"unsupported canonical JSON type: {type(item)!r}")

    return encode(value).encode("utf-8")


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def compact_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing input artifact: {path}")
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"input artifact is not an object: {path}")
    return value


def source_ref(
    path: Path | str, sha256: str, pointer: str = "", **extra: Any
) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "sha256": sha256}
    if pointer:
        result["pointer"] = pointer
    result.update(extra)
    return result


def executor_source(pointer: str = "") -> dict[str, Any]:
    path = Path(__file__).resolve()
    return source_ref(
        path,
        sha256_file(path),
        pointer,
        role="Phase-0 A18 assembly and verdict executor",
    )


def verify_self_seal(payload: dict[str, Any], label: str) -> str:
    if "canonical_sha256" in payload:
        recorded = payload["canonical_sha256"]
        scope = dict(payload)
        scope.pop("canonical_sha256")
        actual = digest_object(scope)
    elif "content_sha256" in payload:
        recorded = payload["content_sha256"]
        scope = dict(payload)
        scope.pop("content_sha256")
        actual = compact_digest(scope)
    else:
        raise ValueError(f"{label} has no supported self-excluding digest")
    require(recorded == actual, f"{label} self-excluding digest mismatch")
    return str(recorded)


def load_sealed(path: Path, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = load_json(path)
    self_digest = verify_self_seal(payload, label)
    return payload, source_ref(
        path.resolve(),
        sha256_file(path),
        self_excluding_sha256=self_digest,
        artifact_kind=payload.get("artifact_kind"),
    )


def authority_design_sha(payload: dict[str, Any]) -> str | None:
    authority = payload.get("authority", {})
    if isinstance(authority.get("commit_design_blob_sha256"), str):
        return authority["commit_design_blob_sha256"]
    for name in ("design", "Design"):
        item = authority.get(name)
        if isinstance(item, dict) and isinstance(item.get("sha256"), str):
            return item["sha256"]
    for item in authority.get("files", []):
        if isinstance(item, dict) and str(item.get("path", "")).endswith(
            "qrf_drift_validation_design.md"
        ):
            return item.get("sha256")
    return None


def verify_authorities() -> dict[str, str]:
    result: dict[str, str] = {}
    for path, expected in EXPECTED_AUTHORITY.items():
        actual = sha256_file(path)
        require(actual == expected, f"authority digest mismatch for {path}")
        result[str(path)] = actual
    return result


def verify_step0(base: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    step0 = base.get("step0")
    require(isinstance(step0, dict), "base report has no Step-0 object")
    require(step0.get("seals") == EXPECTED_STEP0_SEALS, "Step-0 seals changed")
    objects = {
        "operator_table_sha256": step0["operator_table"],
        "json_schema_sha256": step0["json_schema"],
        "required_id_manifest_sha256": step0["required_id_manifest"],
        "adjudication_table_sha256": step0["adjudication_table"],
        "default_appendix_sha256": step0["default_appendix"],
    }
    actual = {name: digest_object(value) for name, value in objects.items()}
    actual["composite_sha256"] = digest_object(
        {
            "operator_table": step0["operator_table"],
            "json_schema": step0["json_schema"],
            "required_id_manifest": step0["required_id_manifest"],
            "adjudication_table": step0["adjudication_table"],
            "default_appendix": step0["default_appendix"],
        }
    )
    require(actual == EXPECTED_STEP0_SEALS, "Step-0 object digests changed")
    require(
        digest_object(step0) == EXPECTED_STEP0_SHA, "complete Step-0 digest changed"
    )
    require(
        step0.get("sealed_before_fresh_statistics") is True,
        "Step 0 was not sealed first",
    )
    manifest = step0["required_id_manifest"]
    require(
        len(manifest) == EXPECTED_MANIFEST_COUNT, "Step-0 manifest is not 6,155 IDs"
    )
    ids = [item["id"] for item in manifest]
    require(len(set(ids)) == len(ids), "Step-0 manifest has duplicate IDs")
    base_rows = base.get("statistics", [])
    require(len(base_rows) == len(manifest), "base statistics are incomplete")
    require(
        {item["id"] for item in base_rows} == set(ids), "base IDs differ from Step 0"
    )
    return manifest, step0


def verify_a18_inputs(
    base_path: Path,
    enumeration_path: Path,
    adoption_path: Path,
    c3_path: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    base, base_source = load_sealed(base_path, "A17 terminal base")
    manifest, step0 = verify_step0(base)
    adoption, adoption_source = load_sealed(adoption_path, "A18 adoption")
    enumeration, enumeration_source = load_sealed(enumeration_path, "A18 enumeration")
    c3, c3_source = load_sealed(c3_path, "A18 retargeted C3")

    require(
        adoption.get("artifact_kind") == "qrf_drift_phase0_a18_branch2_adoption"
        and adoption.get("status") == "SEALED_ADOPTION",
        "A18 adoption is not sealed branch-2 evidence",
    )
    require(
        authority_design_sha(adoption) == EXPECTED_AUTHORITY[DESIGN],
        "adoption authority changed",
    )
    evidence_base = adoption.get("evidence", {}).get("phase0", {})
    require(
        evidence_base.get("sha256") == base_source["sha256"],
        "adoption did not pin the supplied base",
    )
    adopted_step0 = adoption.get("step0", {})
    require(
        adopted_step0.get("status") == "PASS"
        and adopted_step0.get("manifest_count") == EXPECTED_MANIFEST_COUNT
        and adopted_step0.get("complete_step0_sha256") == EXPECTED_STEP0_SHA
        and adopted_step0.get("seals") == EXPECTED_STEP0_SEALS,
        "A18 adoption did not verify the sealed Step-0 bundle",
    )
    roster = adoption.get("control_roster", {})
    require(
        roster.get("K") == EXPECTED_K
        and roster.get("ordered_ids_sha256") == EXPECTED_K_DIGEST
        and roster.get("sidak_z") == EXPECTED_Z,
        "A18 adoption roster changed",
    )
    adopted = adoption.get("controls", {}).get("adopted_controls", {})
    for name in ("C0a", "C0b", "C5", "A17_setup", "C4", "C2"):
        require(
            str(adopted.get(name, {}).get("status", "")).startswith("PASS"),
            f"{name} was not adopted PASS",
        )
    require(
        adoption.get("controls", {}).get("old_C3_present_in_adopted_controls") is False,
        "old C3 was incorrectly adopted",
    )

    require(
        enumeration.get("artifact_kind") == "qrf_drift_phase0_a18_g3_split_enumeration"
        and enumeration.get("status") == "SEALED",
        "A18 G3 enumeration is not sealed",
    )
    require(
        authority_design_sha(enumeration) == EXPECTED_AUTHORITY[DESIGN],
        "enumeration authority changed",
    )
    table = enumeration.get("sealed_split_table", {})
    require(
        table.get("row_count") == len(table.get("rows", [])) == 31
        and table.get("sha256") == EXPECTED_SPLIT_TABLE_SHA
        and digest_object(
            {"definition": table.get("definition"), "rows": table["rows"]}
        )
        == EXPECTED_SPLIT_TABLE_SHA,
        "A18 G3 split-table seal changed",
    )
    disposition = enumeration.get("mechanical_disposition", {})
    selection = disposition.get("selected", {})
    require(
        disposition.get("branch") == 2
        and selection == adoption.get("branch2", {}).get("selected")
        and selection.get("row_sha256") == EXPECTED_SELECTED_SHA,
        "A18 branch or selected split row changed",
    )
    adopted_enumeration = adoption.get("evidence", {}).get("enumeration", {})
    require(
        adopted_enumeration.get("status") == "SEALED"
        and adopted_enumeration.get("sha256") == enumeration_source["sha256"]
        and adopted_enumeration.get("canonical_sha256")
        == enumeration.get("canonical_sha256"),
        "A18 adoption does not bind the supplied sealed enumeration",
    )

    require(
        c3.get("artifact_kind") == "qrf_drift_phase0_a18_c3",
        "wrong A18 C3 artifact kind",
    )
    require(
        authority_design_sha(c3) == EXPECTED_AUTHORITY[DESIGN], "C3 authority changed"
    )
    require(
        c3.get("scope", {}).get("selection") == selection,
        "C3 evaluated a different A18 row",
    )
    c3_enumeration = c3.get("authority", {}).get("enumeration", {})
    require(
        c3_enumeration.get("sha256") == enumeration_source["sha256"]
        and c3_enumeration.get("canonical_sha256")
        == enumeration.get("canonical_sha256")
        and c3_enumeration.get("table_sha256") == EXPECTED_SPLIT_TABLE_SHA
        and c3_enumeration.get("selected_row_sha256") == EXPECTED_SELECTED_SHA,
        "C3 does not bind the supplied sealed A18 enumeration",
    )
    c3_roster = c3.get("control_roster", {})
    require(
        c3_roster.get("overall_K") == EXPECTED_K
        and c3_roster.get("overall_ordered_ids_sha256") == EXPECTED_K_DIGEST
        and c3_roster.get("sidak_z") == EXPECTED_Z,
        "C3 did not use the ratified A18 control roster",
    )
    input_verification = c3.get("input_verification", {})
    input_files = input_verification.get("files")
    require(
        input_verification.get("all_match") is True
        and isinstance(input_files, list)
        and bool(input_files)
        and input_verification.get("file_count") == len(input_files)
        and all(item.get("match") is True for item in input_files),
        "C3 input verification is not a complete digest PASS",
    )
    c3_rows = c3.get("statistics", [])
    expected_ids = c3_stable_ids()
    require(
        [item.get("id") for item in c3_rows] == expected_ids,
        "fresh C3 did not preserve stable IDs",
    )
    require(
        c3_roster.get("ids") == expected_ids,
        "C3 roster IDs differ from the sealed slots",
    )
    for item, group in zip(c3_rows, ("G1", "G2", "G3"), strict=True):
        require(f"|g={group}|" in item["id"], "fresh C3 group order changed")
    return (
        base,
        step0,
        enumeration,
        adoption,
        c3,
        {
            "base": base_source,
            "enumeration": enumeration_source,
            "adoption": adoption_source,
            "C3": c3_source,
        },
    )


def c3_stable_ids() -> list[str]:
    return [
        "r=control|t=child_support_received|p=_|l=_|row=C3_oracle_error|"
        f"g={group}|prior=_|gq=_|d=_|rep=_|fold=_|v=final"
        for group in ("G1", "G2", "G3")
    ]


def fresh_statistics(
    manifest: list[dict[str, Any]],
    fallback_status: str,
    fallback_source: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = [
        {
            "id": spec["id"],
            "dimensions": copy.deepcopy(spec["dimensions"]),
            "record_type": spec["record_type"],
            "value": "NA",
            "se": "NA",
            "mcse": "NA",
            "family": spec["family"],
            "gated": spec["gated"],
            "status": fallback_status,
            "default_resolved": False,
            "sources": [copy.deepcopy(fallback_source)],
        }
        for spec in manifest
    ]
    return rows, {item["id"]: item for item in rows}


def normalize_status(status: Any) -> str:
    text = str(status)
    if text.startswith(("INAPPLICABLE", "NOT_APPLICABLE")):
        return "NOT_APPLICABLE"
    if text.startswith("AVAILABLE") or text.startswith("COMPLETE"):
        return "OK"
    if text.startswith("NO_SURFACE") or text.startswith("FAIL_CLOSED_SURFACE"):
        return "UNAVAILABLE"
    if text.startswith("UNSUPPORTED"):
        return "UNSUPPORTED"
    if text.startswith("NOT_RUN_PRIORITY"):
        return "NOT_RUN_PRIORITY"
    aliases = {
        "NOT_RUN_PRIORITY_RULE": "NOT_RUN_PRIORITY",
        "NOT_RUN_COMMAND_OPTION": "NOT_RUN_PRIORITY",
        "FAIL_CLOSED_SURFACE_UNAVAILABLE": "UNAVAILABLE",
        "AVAILABLE": "OK",
        "AVAILABLE_DESCRIPTIVE": "OK",
        "AVAILABLE_F4": "OK",
        "COMPLETE": "OK",
        # Reading executors retain these more specific producer dispositions.
        # The sealed report schema has only the generic OK status for these
        # descriptive/escalation cells; the original spelling is retained in
        # the appended source record by ``merge_statistics_artifact``.
        "DESCRIPTIVE": "OK",
        "DESCRIPTIVE_NOT_A16_JOINT_GATE": "OK",
        "DESCRIPTIVE_VALIDATED_PATTERN": "OK",
        "DESCRIPTIVE_NOT_VALIDATED_CLOSURE_FAILURE": "NOT_VALIDATED",
        "VALIDATED": "PASS",
        "NOT_VALIDATED_CLOSURE_FAILURE": "NOT_VALIDATED",
        "NOT_VALIDATED_PATTERN_CLOSURE_FAILURE": "NOT_VALIDATED",
        "ESCALATE_TARGET": "OK",
        "KEEP_R250": "OK",
        "NO_TRIGGER": "OK",
        "RUN": "OK",
        "TRIGGER": "OK",
        "NOT_RUN_NO_TARGET_TRIGGER": "NOT_RUN_NOT_ESCALATED",
    }
    return aliases.get(text, text)


def set_row(
    row: dict[str, Any],
    spec: dict[str, Any],
    *,
    value: Any,
    status: str,
    sources: list[dict[str, Any]],
    se: Any = "NA",
    mcse: Any = "NA",
    default_resolved: bool = False,
) -> None:
    status = normalize_status(status)
    require(
        status in spec["allowed_statuses"],
        f"status {status!r} not allowed for {row['id']}",
    )
    row.update(
        value="NA" if value is None else value,
        se="NA" if se is None else se,
        mcse="NA" if mcse is None else mcse,
        status=status,
        default_resolved=bool(default_resolved),
        sources=copy.deepcopy(sources),
    )


def static_fields_match(item: dict[str, Any], spec: dict[str, Any]) -> bool:
    return all(
        field not in item or item[field] == spec[field]
        for field in ("id", "dimensions", "record_type", "family", "gated")
    )


def reading_fields_match(item: dict[str, Any], spec: dict[str, Any]) -> bool:
    """Validate a producer fragment while preserving sealed static fields.

    P2/C1 executors flatten dimensions and may label an absent class
    ``family=null, gated=false``.  Step 0 remains authoritative: such a row is
    still the registered F2/F5 cell with an inapplicable status.  A mismatch
    is accepted only for an explicitly unavailable/inapplicable cell.
    """
    if item.get("id") != spec["id"]:
        return False
    dims = spec["dimensions"]
    for name in (
        "rung",
        "target",
        "pattern",
        "leg",
        "row",
        "group",
        "prior",
        "gq",
        "decile",
        "repeat",
        "fold",
        "variant",
    ):
        if name in item and str(item[name]) != dims[name]:
            return False
    if "dimensions" in item and item["dimensions"] != dims:
        return False
    if "record_type" in item and item["record_type"] != spec["record_type"]:
        return False
    static_changed = any(
        name in item and item[name] != spec[name] for name in ("family", "gated")
    )
    unavailable = normalize_status(item.get("status")) in {
        "NOT_APPLICABLE",
        "INSUFFICIENT_SUPPORT_NO_VERDICT",
        "NOT_RUN_CONTROLS_FAILED",
        "NOT_RUN_PRIORITY",
        "NOT_RUN_NOT_ESCALATED",
        "UNAVAILABLE",
        "UNSUPPORTED",
        "NOT_VALIDATED",
        "SEALED_NOT_COMPUTED",
    }
    return not static_changed or unavailable


def adopt_base_statistics(
    base: dict[str, Any],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> set[str]:
    """Copy only A18-adopted control/setup/support rows from the A17 report."""
    locked: set[str] = set()
    for item in base["statistics"]:
        dims = item["dimensions"]
        row_name = dims["row"]
        adopted = (
            dims["rung"] == "control"
            or row_name == "C0a_incidence"
            or row_name in P0_SETUP_ROWS
            or (row_name == "verdict" and dims["variant"] == "support")
        )
        old_c3 = row_name in {"C3_oracle_error", "C3_power"}
        if not adopted or old_c3:
            continue
        spec = manifest_by_id[item["id"]]
        require(
            static_fields_match(item, spec),
            f"base static fields changed for {item['id']}",
        )
        set_row(
            by_id[item["id"]],
            spec,
            value=item["value"],
            se=item["se"],
            mcse=item["mcse"],
            status=item["status"],
            sources=item["sources"],
            default_resolved=item.get("default_resolved", False),
        )
        locked.add(item["id"])
    return locked


def merge_c3(
    c3: dict[str, Any],
    c3_source: dict[str, Any],
    selection: dict[str, Any],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
) -> bool:
    control = c3.get("control", {})
    power = control.get("power", {})
    passed = (
        c3.get("status") == "PASS"
        and control.get("pass") is True
        and control.get("group_recoveries_pass") is True
        and power.get("pass") is True
    )
    for position, item in enumerate(c3["statistics"]):
        identifier = item["id"]
        require(identifier not in locked, f"fresh C3 overwrites locked ID {identifier}")
        context = {
            "target": selection["target"],
            "pattern": selection["pattern"],
            "G3_column": selection["G3_column"],
            "selected_row_sha256": selection["row_sha256"],
            "sealed_id_dimensions_unchanged": True,
        }
        source = source_ref(
            c3_source["path"],
            c3_source["sha256"],
            f"/statistics/{position}",
            canonical_sha256=c3.get("canonical_sha256"),
            retargeted_context=context,
        )
        set_row(
            by_id[identifier],
            manifest_by_id[identifier],
            value=item.get("value", "NA"),
            se=item.get("se", "NA"),
            mcse=item.get("mcse", "NA"),
            status=item.get("status", "FAIL"),
            sources=[source],
        )
        locked.add(identifier)
    power_id = (
        "r=control|t=child_support_received|p=_|l=_|row=C3_power|"
        "g=_|prior=_|gq=_|d=_|rep=_|fold=_|v=_"
    )
    set_row(
        by_id[power_id],
        manifest_by_id[power_id],
        value=bool(power.get("pass")),
        status="PASS" if power.get("pass") else "FAIL",
        sources=[
            source_ref(
                c3_source["path"],
                c3_source["sha256"],
                "/control/power",
                retargeted_context=selection,
            )
        ],
    )
    locked.add(power_id)
    return passed


P2_DOMAIN_INVALIDATED_ROWS = {
    "P2_group_pattern",
    "P2_group_aggregate",
    "P2_prior_pattern",
}


def p2_domain_gap_targets(payload: dict[str, Any]) -> set[str]:
    """Return targets whose A16-31 joint-domain gate was not enumerated.

    A one-feature marginal support check is not the D0-enumerated joint hybrid
    predicate required by A16-31.  The current sealed P2 artifact records that
    absence uniformly.  Preserve its numerical estimates, but do not present
    them as validated attributions.
    """
    if payload.get("artifact_kind") != "qrf_drift_phase0_a18_p2":
        return set()
    target_rows = payload.get("targets")
    require(isinstance(target_rows, list) and target_rows, "P2 has no target results")
    targets: list[str] = []
    matched: set[str] = set()
    for target_row in target_rows:
        require(isinstance(target_row, dict), "P2 target result is not an object")
        target = target_row.get("target")
        require(isinstance(target, str), "P2 target result has no target name")
        targets.append(target)
        domain = target_row.get("joint_hybrid_domain", {})
        if (
            domain.get("status") == "UNAVAILABLE_D0_NOT_ENUMERATED"
            and domain.get("pattern_invalidation_decision") == "NOT_EVALUABLE"
            and domain.get("no_predicates_invented") is True
            and domain.get("predicates") == []
        ):
            matched.add(target)
    require(
        not matched or matched == set(targets),
        "P2 joint-domain disposition is not uniform across its target scope",
    )
    return matched


def merge_statistics_artifact(
    path: Path,
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
    readings_barrier_source: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, artifact_source = load_sealed(path, f"reading artifact {path.name}")
    require(
        authority_design_sha(payload) == EXPECTED_AUTHORITY[DESIGN],
        f"{path} design authority changed",
    )
    if payload.get("artifact_kind") == "qrf_drift_phase0_a18_c1":
        verify_c1_phase_order(payload, readings_barrier_source)
    p2_domain_targets = p2_domain_gap_targets(payload)
    statistics = payload.get("statistics")
    require(isinstance(statistics, list), f"{path} has no statistics array")
    seen: set[str] = set()
    for position, item in enumerate(statistics):
        identifier = item.get("id")
        require(
            identifier in manifest_by_id, f"{path} uses nonmanifest ID {identifier!r}"
        )
        require(identifier not in seen, f"{path} duplicates {identifier}")
        require(identifier not in locked, f"{path} overwrites populated {identifier}")
        seen.add(identifier)
        spec = manifest_by_id[identifier]
        require(
            reading_fields_match(item, spec),
            f"{path} changes static fields for {identifier}",
        )
        sources = copy.deepcopy(item.get("sources", []))
        if isinstance(item.get("source"), dict):
            sources.append(copy.deepcopy(item["source"]))
        sources.append(
            source_ref(
                path.resolve(),
                artifact_source["sha256"],
                f"/statistics/{position}",
                producer_family=item.get("family"),
                producer_gated=item.get("gated"),
                producer_status=item.get("status"),
                producer_value=item.get("value", "NA"),
                producer_se=item.get("se", "NA"),
                producer_mcse=item.get("mcse", "NA"),
                sealed_family=spec["family"],
                sealed_gated=spec["gated"],
            )
        )
        row_name = spec["dimensions"]["row"]
        target = spec["dimensions"]["target"]
        status = item.get("status", "UNAVAILABLE")
        value = item.get("value", "NA")
        se = item.get("se", "NA")
        mcse = item.get("mcse", "NA")
        normalized_status = normalize_status(status)
        if target in p2_domain_targets and row_name in P2_DOMAIN_INVALIDATED_ROWS:
            if normalized_status not in {
                "NOT_APPLICABLE",
                "INSUFFICIENT_SUPPORT_NO_VERDICT",
                "NOT_RUN_CONTROLS_FAILED",
                "NOT_RUN_PRIORITY",
                "NOT_RUN_NOT_ESCALATED",
                "SEALED_NOT_COMPUTED",
                "UNAVAILABLE",
                "UNSUPPORTED",
            }:
                status = "NOT_VALIDATED"
        elif (
            target in p2_domain_targets
            and row_name == "P2_marginal_audit"
            and spec["dimensions"]["variant"] == "domain_violation_share"
        ):
            value = se = mcse = "NA"
            status = "UNAVAILABLE"
        if target in p2_domain_targets and status != item.get("status"):
            sources[-1]["assembly_disposition"] = P2_JOINT_DOMAIN_DISPOSITION
        set_row(
            by_id[identifier],
            spec,
            value=value,
            se=se,
            mcse=mcse,
            status=status,
            sources=sources,
            default_resolved=item.get("default_resolved", False),
        )
        locked.add(identifier)
    return payload, artifact_source


def merge_p5_artifacts(
    paths: list[Path],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Merge one all-target P5 artifact or a disjoint complete shard set."""
    if not paths:
        return []
    expected_all = {
        identifier
        for identifier, spec in manifest_by_id.items()
        if spec["dimensions"]["row"].startswith("P5_")
    }
    require(len(expected_all) == 558, "sealed P5 roster is not 558 cells")
    merged: list[tuple[dict[str, Any], dict[str, Any]]] = []
    supplied: set[str] = set()
    scoped_targets: set[str] = set()
    for path in paths:
        payload, source = merge_statistics_artifact(path, manifest_by_id, by_id, locked)
        require(
            payload.get("artifact_kind") == "qrf_drift_phase0_a18_p5",
            f"wrong P5 artifact kind in {path}",
        )
        require(
            payload.get("status") in {"COMPLETE", "COMPLETE_TARGET_SUBSET"},
            f"nonterminal P5 artifact {path}",
        )
        targets = payload.get("scope", {}).get("targets")
        require(
            isinstance(targets, list)
            and targets
            and all(isinstance(target, str) for target in targets),
            f"P5 artifact {path} has no target scope",
        )
        require(
            scoped_targets.isdisjoint(targets),
            f"P5 target scope overlaps an earlier shard: {path}",
        )
        scoped_targets.update(targets)
        expected = {
            identifier
            for identifier in expected_all
            if manifest_by_id[identifier]["dimensions"]["target"] in targets
        }
        actual = {item["id"] for item in payload["statistics"]}
        require(
            len(expected) == 62 * len(targets) and actual == expected,
            f"P5 shard roster mismatch in {path}",
        )
        supplied.update(actual)
        merged.append((payload, source))
    require(
        supplied == expected_all,
        f"P5 shard union is not the full 558-cell roster; missing={len(expected_all - supplied)}",
    )
    return merged


def completed_probe_dispositions(payload: dict[str, Any]) -> dict[str, str]:
    """Normalize either registered readings-barrier spelling."""
    candidates = (
        payload.get("completed_readings"),
        payload.get("completed_probes"),
        payload.get("phase_order", {}).get("completed")
        if isinstance(payload.get("phase_order"), dict)
        else None,
        payload.get("readings", {}).get("completed")
        if isinstance(payload.get("readings"), dict)
        else None,
    )
    for value in candidates:
        if isinstance(value, dict):
            return {str(name): str(status) for name, status in value.items()}
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return {item: "COMPLETE" for item in value}
    return {}


def verify_readings_barrier(payload: dict[str, Any]) -> dict[str, str]:
    allowed_kinds = {
        "qrf_drift_phase0_readings_prerequisite",
        "qrf_drift_phase0_readings",
        "qrf_drift_phase0_p0_p1_p2_p5_p6_p7",
    }
    require(
        payload.get("artifact_kind") in allowed_kinds,
        "unsupported readings-barrier kind",
    )
    require(
        payload.get("status")
        in {
            "READINGS_COMPLETE",
            "COMPLETE",
            "COMPLETE_WITH_DECLARED_PRIORITY_OMISSIONS",
        },
        "readings barrier does not have a C1-compatible terminal status",
    )
    require(
        authority_design_sha(payload) == EXPECTED_AUTHORITY[DESIGN],
        "readings barrier design authority changed",
    )
    phase = payload.get("phase_order", {})
    require(
        payload.get("readings_complete") is True
        or (isinstance(phase, dict) and phase.get("readings_complete") is True),
        "readings barrier does not assert completion/disposition",
    )
    dispositions = completed_probe_dispositions(payload)
    required = {"P0", "P1", "P2", "P5", "P6", "P7"}
    require(
        required <= set(dispositions),
        f"readings barrier lacks {sorted(required - set(dispositions))}",
    )
    next_phase = payload.get("next_phase") or (
        phase.get("next") if isinstance(phase, dict) else None
    )
    require(next_phase == "C1", "readings barrier does not place C1 next")
    return dispositions


def barrier_completes_evidenced_p6(
    artifact: tuple[dict[str, Any], dict[str, Any]] | None,
) -> bool:
    """Return true only for a valid barrier's exact P6 disposition."""
    if artifact is None:
        return False
    return verify_readings_barrier(artifact[0]).get("P6") == P6_COMPLETE_NO_SURFACE


def barrier_disposes_unvalidated_p2(
    artifact: tuple[dict[str, Any], dict[str, Any]] | None,
) -> bool:
    """Return true only for a valid barrier's exact P2 disposition."""
    if artifact is None:
        return False
    return (
        verify_readings_barrier(artifact[0]).get("P2") == P2_NOT_VALIDATED_DISPOSITION
    )


def artifact_binding_record(
    payload: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    kind = payload.get("artifact_kind")
    if kind == "qrf_drift_phase0_p0_p1_p6_p7":
        targets = list(payload.get("candidate-25", {}).get("targets", {}))
    elif kind == "qrf_drift_phase0_a18_p2":
        targets = [item.get("target") for item in payload.get("targets", [])]
    elif kind == "qrf_drift_phase0_baseline_crossrung_p0_p1":
        targets = list(payload.get("baseline1pct", {}).get("targets", {}))
    else:
        targets = list(payload.get("scope", {}).get("targets", []))
    return {
        "path": str(Path(source["path"]).resolve()),
        "sha256": source["sha256"],
        # The barrier's historical field name covers either supported
        # self-excluding seal (canonical_sha256 or content_sha256).
        "canonical_sha256": source.get("self_excluding_sha256")
        or source.get("scientific_content_sha256")
        or payload.get("canonical_sha256")
        or payload.get("content_sha256"),
        "artifact_kind": kind,
        "status": payload.get("status"),
        "targets": sorted(str(target) for target in targets),
    }


def verify_barrier_artifact_bindings(
    barrier: dict[str, Any],
    reading_payloads: list[tuple[dict[str, Any], dict[str, Any]]],
) -> None:
    """Bind the pre-C1 barrier to the exact reading artifacts in this report."""
    expected = barrier.get("artifacts")
    require(isinstance(expected, dict), "readings barrier has no artifact bindings")
    dispositions = completed_probe_dispositions(barrier)
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payload, source in reading_payloads:
        kind = payload.get("artifact_kind")
        if kind in {
            "qrf_drift_phase0_p0_p1_p6_p7",
            "qrf_drift_phase0_a18_p2",
            "qrf_drift_phase0_baseline_crossrung_p0_p1",
            "qrf_drift_phase0_a18_p5",
        }:
            by_kind[str(kind)].append(artifact_binding_record(payload, source))

    mapping = {
        "P1": "qrf_drift_phase0_p0_p1_p6_p7",
        "P2": "qrf_drift_phase0_a18_p2",
        "baseline_crossrung": "qrf_drift_phase0_baseline_crossrung_p0_p1",
    }
    for barrier_name, kind in mapping.items():
        records = by_kind.get(kind, [])
        require(len(records) == 1, f"report needs exactly one {barrier_name} artifact")
        expected_record = copy.deepcopy(expected.get(barrier_name))
        require(
            isinstance(expected_record, dict), f"barrier lacks {barrier_name} binding"
        )
        expected_record["path"] = str(Path(expected_record["path"]).resolve())
        if isinstance(expected_record.get("targets"), list):
            expected_record["targets"] = sorted(
                str(target) for target in expected_record["targets"]
            )
        require(
            records[0] == expected_record,
            f"barrier {barrier_name} binding differs from the supplied artifact",
        )

    p5_records = by_kind.get("qrf_drift_phase0_a18_p5", [])
    expected_p5 = copy.deepcopy(expected.get("P5"))
    require(isinstance(expected_p5, list), "barrier P5 binding is not a list")
    require(
        len(p5_records) == len(expected_p5) == 6,
        "barrier does not bind the required six P5 shards",
    )
    for record in expected_p5:
        require(isinstance(record, dict), "barrier P5 record is not an object")
        record["path"] = str(Path(record["path"]).resolve())
        if isinstance(record.get("targets"), list):
            record["targets"] = sorted(str(target) for target in record["targets"])

    def record_key(item: dict[str, Any]) -> tuple[str, str]:
        return item["path"], item["sha256"]

    require(
        sorted(p5_records, key=record_key) == sorted(expected_p5, key=record_key),
        "barrier P5 shard bindings differ from the supplied complete shard set",
    )
    p5_targets = [target for record in p5_records for target in record["targets"]]
    require(
        len(p5_targets) == len(set(p5_targets)) == 9,
        "barrier-bound P5 shards do not cover nine disjoint targets",
    )
    require(
        dispositions.get("P2") == P2_NOT_VALIDATED_DISPOSITION
        and dispositions.get("P6") == P6_COMPLETE_NO_SURFACE,
        "barrier does not preserve the sealed P2/P6 reading dispositions",
    )


def verify_c1_phase_order(
    payload: dict[str, Any], readings_barrier_source: dict[str, Any] | None
) -> None:
    require(
        payload.get("scope", {}).get("runs_after_readings") is True,
        "C1 does not assert post-reading order",
    )
    require(
        readings_barrier_source is not None, "C1 requires the supplied readings barrier"
    )
    readings = payload.get("prerequisites", {}).get("readings", {})
    require(isinstance(readings, dict), "C1 has no readings prerequisite receipt")
    completed = set(readings.get("completed_readings", []))
    require(
        {"P0", "P1", "P2", "P5", "P6", "P7"} <= completed,
        "C1 prerequisite lacks a disposition for every pre-C1 probe",
    )
    recorded_path = readings.get("path")
    recorded_sha = readings.get("sha256")
    require(
        isinstance(recorded_path, str) and isinstance(recorded_sha, str),
        "C1 readings prerequisite lacks path/file SHA-256",
    )
    live = Path(recorded_path)
    require(live.is_file(), "C1 readings prerequisite is no longer readable")
    require(
        sha256_file(live) == recorded_sha,
        "C1 readings prerequisite file digest changed",
    )
    require(
        live.resolve() == Path(readings_barrier_source["path"]).resolve()
        and recorded_sha == readings_barrier_source["sha256"]
        and readings.get("self_excluding_sha256")
        == readings_barrier_source.get("self_excluding_sha256"),
        "C1 was not run from the supplied sealed readings barrier",
    )


def merge_readings_barrier(
    path: Path,
    manifest: list[dict[str, Any]],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, artifact_source = load_sealed(path, "readings completion barrier")
    dispositions = verify_readings_barrier(payload)
    prefixes = {
        "P0": ("P0_", "phi"),
        "P1": (*LEVEL_ROWS, *TOP_LEVEL_ROWS, "residual", "B2_"),
        "P2": ("P2_", "e_D", "e_R", "e_T"),
        "P5": ("P5_",),
        "P6": ("P6_",),
        "P7": ("P7_",),
    }
    for probe, disposition in dispositions.items():
        normalized = normalize_status(disposition)
        if normalized not in {
            "NOT_RUN_PRIORITY",
            "UNAVAILABLE",
            "NOT_VALIDATED",
            "UNSUPPORTED",
        }:
            continue
        for spec in manifest:
            if spec["id"] in locked or spec["dimensions"]["rung"] != "candidate-25":
                continue
            row_name = spec["dimensions"]["row"]
            matches = any(
                row_name == prefix or row_name.startswith(prefix)
                for prefix in prefixes.get(probe, ())
            )
            if not matches:
                continue
            set_row(
                by_id[spec["id"]],
                manifest_by_id[spec["id"]],
                value="NA",
                status=normalized,
                sources=[
                    source_ref(
                        path.resolve(),
                        artifact_source["sha256"],
                        "/completed_readings",
                        probe=probe,
                        declared_disposition=disposition,
                    )
                ],
            )
            locked.add(spec["id"])
    return payload, artifact_source


def dimension_id(
    manifest: list[dict[str, Any]],
    **wanted: str,
) -> str:
    matches = [
        item["id"]
        for item in manifest
        if all(item["dimensions"].get(key) == value for key, value in wanted.items())
    ]
    require(
        len(matches) == 1,
        f"expected one manifest cell for {wanted}, got {len(matches)}",
    )
    return matches[0]


def is_p1_row(row_name: str) -> bool:
    return (
        row_name in LEVEL_ROWS
        or row_name in TOP_LEVEL_ROWS
        or row_name == "residual"
        or row_name in {"P0_S_o_count", "P0_phi", "P0_path_census", "phi"}
        or row_name.startswith("B2_")
        or row_name.startswith("P6_")
        or row_name.startswith("P7_")
    )


def is_p2_row(row_name: str) -> bool:
    return row_name.startswith("P2_") or row_name in {"e_D", "e_R", "e_T"}


def _nested_value(item: Any) -> tuple[Any, Any, str]:
    if not isinstance(item, dict):
        return item, "NA", "OK"
    value = item.get("value", "NA")
    se = item.get("se", "NA")
    default_status = (
        "NOT_APPLICABLE"
        if item.get("empty_set") is True and value == "NA"
        else "OK"
        if value != "NA"
        else "UNAVAILABLE"
    )
    status = item.get("status", default_status)
    return value, se, normalize_status(status)


def p0_path_code_anchors(
    payload: dict[str, Any],
    target: str,
    operator_table: list[dict[str, Any]],
    step0_source: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Bind each P0 predicate to the sealed target implementation source."""
    require(
        P1_EXECUTOR.is_file() and sha256_file(P1_EXECUTOR) == EXPECTED_P1_EXECUTOR_SHA,
        "P1 executor differs from the execution-commit code binding",
    )
    sealed = payload.get("authority", {}).get("sealed_step0_operator_source", {})
    require(
        sealed.get("status") == "PASS"
        and sealed.get("operator_table_sha256")
        == EXPECTED_STEP0_SEALS["operator_table_sha256"],
        "P1 does not bind the sealed Step-0 operator table",
    )
    require(
        isinstance(sealed.get("path"), str)
        and Path(sealed["path"]).resolve() == Path(step0_source["path"]).resolve()
        and sealed.get("sha256") == step0_source.get("sha256"),
        "P1 Step-0 operator source differs from the supplied A17 base",
    )
    checked_sources = sealed.get("source_code")
    require(
        isinstance(checked_sources, list) and checked_sources,
        "P1 sealed operator binding has no source-code checks",
    )
    checked_by_path = {
        str(Path(item["path"]).resolve()): item
        for item in checked_sources
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    anchors: dict[str, dict[str, Any]] = {}
    target_reading = payload.get("candidate-25", {}).get("targets", {}).get(target, {})
    sealed_codec = target_reading.get("P1", {}).get("codec", {})
    for path_stage, operator_stage in P0_PATH_OPERATOR_STAGE.items():
        matches = [
            (index, item)
            for index, item in enumerate(operator_table)
            if item.get("target") == target and item.get("stage") == operator_stage
        ]
        require(
            len(matches) == 1,
            f"sealed operator table has no unique {target}/{operator_stage} P0 anchor",
        )
        index, operator = matches[0]
        code = operator.get("source_code")
        require(
            isinstance(code, dict)
            and isinstance(code.get("path"), str)
            and valid_sha256(code.get("sha256"))
            and isinstance(operator.get("source_anchor"), str)
            and bool(operator["source_anchor"]),
            f"sealed operator row lacks a code anchor for {target}/{operator_stage}",
        )
        code_path = (ROOT / code["path"]).resolve()
        checked = checked_by_path.get(str(code_path), {})
        require(
            checked.get("match") is True
            and checked.get("sha256_actual") == code["sha256"]
            and checked.get("sha256_expected") == code["sha256"]
            and code_path.is_file()
            and sha256_file(code_path) == code["sha256"],
            f"P1 source-code check does not bind {target}/{operator_stage}",
        )
        production_source = source_ref(
            code_path,
            code["sha256"],
            role="sealed production implementation code anchor",
            p0_path_stage=path_stage,
            operator_stage=operator_stage,
            source_anchor=operator["source_anchor"],
        )
        if operator_stage == "recipient_codec":
            require(
                sealed_codec.get("status") == "AVAILABLE_REPLAYED"
                and sealed_codec.get("source_code") == code
                and sealed_codec.get("source_anchor") == operator["source_anchor"]
                and sealed_codec.get("transformation")
                == operator.get("transformation"),
                f"sealed P1 codec binding differs for {target}",
            )
        executor = source_ref(
            P1_EXECUTOR.resolve(),
            EXPECTED_P1_EXECUTOR_SHA,
            role="sealed P0 path-census executor code anchor",
            execution_commit=P1_EXECUTION_COMMIT,
            p0_path_stage=path_stage,
            source_anchor=P0_PATH_EXECUTOR_ANCHOR[path_stage],
        )
        anchors[path_stage] = {
            "operator_stage": operator_stage,
            "predicate_anchor": P0_PATH_EXECUTOR_ANCHOR[path_stage],
            "production_anchor": operator["source_anchor"],
            "sources": [executor, production_source],
            "operator_table_source": source_ref(
                step0_source["path"],
                step0_source["sha256"],
                f"/step0/operator_table/{index}",
            ),
        }
    return anchors


def merge_p1_artifact(
    path: Path,
    manifest: list[dict[str, Any]],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
    operator_table: list[dict[str, Any]] | None = None,
    step0_source: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, artifact_source = load_sealed(path, "P0/P1/P6/P7")
    require(
        payload.get("artifact_kind") == "qrf_drift_phase0_p0_p1_p6_p7",
        "wrong P1 artifact kind",
    )
    require(
        authority_design_sha(payload) == EXPECTED_AUTHORITY[DESIGN],
        "P1 design authority changed",
    )

    require(
        (operator_table is None) == (step0_source is None),
        "P0 code-anchor inputs must be supplied together",
    )

    def assign(
        identifier: str,
        value: Any,
        se: Any,
        status: str,
        pointer: str,
        *,
        additional_sources: list[dict[str, Any]] | None = None,
        **extra: Any,
    ) -> None:
        if identifier in locked:
            return
        sources = [
            source_ref(path.resolve(), artifact_source["sha256"], pointer, **extra)
        ]
        sources.extend(copy.deepcopy(additional_sources or []))
        set_row(
            by_id[identifier],
            manifest_by_id[identifier],
            value=value,
            se=se,
            status=status,
            sources=sources,
        )
        locked.add(identifier)

    candidate = payload.get("candidate-25", {}).get("targets", {})
    for target, reading in candidate.items():
        prefix = f"/candidate-25/targets/{target}"
        if reading.get("status") != "COMPLETE":
            evidence = copy.deepcopy(reading.get("evidence", {}))
            for spec in manifest:
                dims = spec["dimensions"]
                if (
                    dims["rung"] == "candidate-25"
                    and dims["target"] == target
                    and is_p1_row(dims["row"])
                    and spec["id"] not in locked
                ):
                    assign(
                        spec["id"],
                        "NA",
                        "NA",
                        "UNAVAILABLE",
                        prefix,
                        unavailable_evidence=evidence,
                    )
            continue

        p0 = reading["P0"]
        path_code_anchors = (
            p0_path_code_anchors(
                payload,
                target,
                operator_table,
                step0_source,
            )
            if operator_table is not None and step0_source is not None
            else None
        )
        p0_map = {
            "P0_S_o_count": (p0["S_o_rows"], "NA"),
            "P0_phi": (p0["phi"], "NA"),
            # The scalar cell records the reconciled scope size; the complete
            # first-failure census is retained in the row source metadata.
            "P0_path_census": (p0["scope_rows"], "NA"),
        }
        for row_name, (value, se) in p0_map.items():
            identifier = dimension_id(
                manifest, rung="candidate-25", target=target, row=row_name
            )
            assign(
                identifier,
                value,
                se,
                "OK",
                f"{prefix}/P0",
                path_census=p0.get("path_census")
                if row_name == "P0_path_census"
                else None,
                path_code_anchors=path_code_anchors
                if row_name == "P0_path_census"
                else None,
                additional_sources=[
                    source
                    for anchor in (path_code_anchors or {}).values()
                    for source in anchor["sources"]
                ]
                if row_name == "P0_path_census"
                else None,
            )
        for leg in LEGS:
            identifier = dimension_id(
                manifest,
                rung="candidate-25",
                target=target,
                leg=leg,
                row="phi",
            )
            assign(
                identifier,
                p0["phi"],
                "NA",
                "OK",
                f"{prefix}/P0/phi",
            )

        for leg in LEGS:
            levels = reading["P1"]["levels"][leg]
            for row_name in LEVEL_ROWS:
                value, se, status = _nested_value(levels[row_name])
                identifier = dimension_id(
                    manifest,
                    rung="candidate-25",
                    target=target,
                    leg=leg,
                    row=row_name,
                )
                assign(
                    identifier,
                    value,
                    se,
                    status,
                    f"{prefix}/P1/levels/{leg}/{row_name}",
                )
            ledger = reading["P1"]["ledger"][leg]["rows"]
            for row_name in (*TOP_LEVEL_ROWS, "residual"):
                value, se, status = _nested_value(ledger[row_name])
                identifier = dimension_id(
                    manifest,
                    rung="candidate-25",
                    target=target,
                    leg=leg,
                    row=row_name,
                )
                assign(
                    identifier,
                    value,
                    se,
                    status,
                    f"{prefix}/P1/ledger/{leg}/rows/{row_name}",
                )
            b2_rows = (
                reading["P1"]
                .get("B2_diagnostics", {})
                .get("legs", {})
                .get(leg, {})
                .get("rows", {})
            )
            for subrow, item in b2_rows.items():
                row_name = f"B2_{subrow}"
                value, se, status = _nested_value(
                    {
                        "value": item.get("ledger_value", item.get("value", "NA")),
                        "se": item.get("ledger_se", item.get("se", "NA")),
                    }
                )
                identifier = dimension_id(
                    manifest,
                    rung="candidate-25",
                    target=target,
                    leg=leg,
                    row=row_name,
                )
                assign(
                    identifier,
                    value,
                    se,
                    status,
                    f"{prefix}/P1/B2_diagnostics/legs/{leg}/rows/{subrow}",
                )

        merge_p6_nested(
            reading.get("P6", {}),
            target,
            prefix,
            path,
            artifact_source,
            manifest,
            manifest_by_id,
            by_id,
            locked,
        )
        merge_p7_nested(
            reading.get("P7", {}),
            target,
            prefix,
            path,
            artifact_source,
            manifest,
            manifest_by_id,
            by_id,
            locked,
        )

    return payload, artifact_source


def load_baseline_crossrung(
    path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify the helper's execution-excluded scientific content seal."""
    payload = load_json(path)
    require(
        payload.get("artifact_kind") == "qrf_drift_phase0_baseline_crossrung_p0_p1",
        "wrong baseline cross-rung artifact kind",
    )
    require(payload.get("status") == "COMPLETE", "baseline cross-rung is not COMPLETE")
    require(payload.get("rung") == "baseline1pct", "baseline cross-rung rung changed")
    require(
        payload.get("execution", {}).get("authoritative") is True,
        "baseline cross-rung execution is not authoritative",
    )
    recorded = payload.get("content_sha256")
    require(isinstance(recorded, str), "baseline cross-rung has no content seal")
    scientific_scope = {
        key: value
        for key, value in payload.items()
        if key not in {"execution", "content_sha256"}
    }
    require(
        compact_digest(scientific_scope) == recorded,
        "baseline cross-rung scientific content seal mismatch",
    )
    authority = payload.get("authority", {})
    require(
        authority.get("design", {}).get("sha256") == EXPECTED_AUTHORITY[DESIGN]
        and authority.get("D0", {}).get("sha256") == EXPECTED_AUTHORITY[D0_JSON]
        and authority.get("A16_binding", {}).get("sha256")
        == EXPECTED_AUTHORITY[BINDING],
        "baseline cross-rung authority changed",
    )
    inputs = authority.get("input_verification", {})
    require(
        inputs.get("status") == "PASS"
        and inputs.get("all_inputs_live_hashed") is True
        and all(item.get("match") is True for item in inputs.get("files", [])),
        "baseline cross-rung input verification is not a clean PASS",
    )
    operator = authority.get("sealed_step0_operator_source", {})
    require(
        operator.get("status") == "PASS"
        and operator.get("operator_table_sha256")
        == EXPECTED_STEP0_SEALS["operator_table_sha256"],
        "baseline cross-rung operator binding changed",
    )
    targets = payload.get("baseline1pct", {}).get("targets", {})
    require(
        set(targets)
        == {
            "self_employment_income_last_year",
            "spm_unit_energy_subsidy",
        },
        "baseline cross-rung target roster changed",
    )
    require(
        not payload.get("unavailable_targets"),
        "baseline cross-rung has unavailable targets",
    )
    for target, reading in targets.items():
        require(
            reading.get("status") == "COMPLETE"
            and reading.get("target") == target
            and reading.get("leg") == "positive",
            f"baseline cross-rung reading is incomplete for {target}",
        )
        require(
            reading.get("support", {}).get("status") == "SUPPORTED",
            f"baseline cross-rung support failed for {target}",
        )
        require(
            reading.get("ledger", {}).get("residual", {}).get("passes") is True,
            f"baseline cross-rung ledger does not close for {target}",
        )
        require(
            reading.get("D0_incidence_binding", {}).get("J0_bit_exact") is True
            and reading.get("D0_incidence_binding", {}).get("I_acs_bit_exact") is True,
            f"baseline cross-rung incidence binding failed for {target}",
        )
        require(
            all(reading.get("P0", {}).get("bindings", {}).values()),
            f"baseline cross-rung P0 binding failed for {target}",
        )
    artifact_source = source_ref(
        path.resolve(),
        sha256_file(path),
        scientific_content_sha256=recorded,
        digest_scope="all fields except execution and content_sha256",
        artifact_kind=payload["artifact_kind"],
    )
    return payload, artifact_source


def merge_baseline_crossrung_artifact(
    path: Path,
    manifest: list[dict[str, Any]],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, artifact_source = load_baseline_crossrung(path)
    targets = payload["baseline1pct"]["targets"]
    expected = {
        spec["id"]
        for spec in manifest
        if spec["dimensions"]["rung"] == "baseline1pct"
        and spec["dimensions"]["target"] in targets
        and spec["dimensions"]["row"] != "C0a_incidence"
    }
    require(
        len(expected) == 42, "baseline cross-rung registered roster is not 42 cells"
    )
    populated: set[str] = set()
    for target, reading in targets.items():
        prefix = f"/baseline1pct/targets/{target}"
        objects: dict[str, Any] = {
            "phi": {
                "value": reading["P0"]["phi"],
                "se": "NA",
            },
            **reading["levels"],
            **reading["ledger"],
        }
        for row_name, item in objects.items():
            identifier = dimension_id(
                manifest,
                rung="baseline1pct",
                target=target,
                leg="positive",
                row=row_name,
            )
            require(identifier in expected, f"unregistered baseline row {identifier}")
            require(
                identifier not in locked,
                f"baseline row was already populated: {identifier}",
            )
            value, se, status = _nested_value(item)
            set_row(
                by_id[identifier],
                manifest_by_id[identifier],
                value=value,
                se=se,
                status=status,
                sources=[
                    source_ref(
                        path.resolve(),
                        artifact_source["sha256"],
                        f"{prefix}/{'P0' if row_name == 'phi' else 'levels' if row_name in reading['levels'] else 'ledger'}/{row_name}",
                        scientific_content_sha256=payload["content_sha256"],
                    )
                ],
            )
            locked.add(identifier)
            populated.add(identifier)
    require(populated == expected, "baseline cross-rung merge missed registered cells")
    return payload, artifact_source


def p6_scalar_representation(value: Any) -> Any:
    """Keep scalar seeds exact and reversibly encode structured P6 cells."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def p6_surface_value(surface: dict[str, Any], leg: str, variant: str) -> Any:
    if variant == "mask_sha256":
        identity = (
            surface.get("native_row_identity")
            or surface.get("boundary_mask")
            or surface.get("source_id_identity")
        )
        return identity.get("sha256", "NA") if isinstance(identity, dict) else "NA"
    if variant == "sign_count":
        return surface.get("unweighted_sign_counts", {}).get(leg, "NA")
    if variant == "weighted_sign_mass":
        return surface.get("weighted_sign_mass", {}).get(leg, "NA")
    if variant == "incidence":
        return surface.get("incidence", {}).get(leg, "NA")
    if variant == "seed":
        return surface.get("seed", "NA")
    return "NA"


def p6_pattern_value(stage: dict[str, Any], leg: str, variant: str) -> Any:
    patterns = stage.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        return "NA"
    values = {
        str(surface["pattern"]): p6_surface_value(surface, leg, variant)
        for surface in patterns
        if isinstance(surface, dict) and isinstance(surface.get("pattern"), str)
    }
    if not values or any(value == "NA" for value in values.values()):
        return "NA"
    return values


def p6_clone_bridge_value(stage: dict[str, Any], leg: str, variant: str) -> Any:
    if variant == "incidence":
        return stage.get("legs", {}).get(leg, {}).get("clone_weight_bridge", "NA")
    populations = {
        name: stage[name]
        for name in ("J0_native", "J1_native", "J1_on_J0_rows_and_weights")
        if isinstance(stage.get(name), dict)
    }
    if populations:
        values = {
            name: p6_surface_value(surface, leg, variant)
            for name, surface in populations.items()
        }
        if variant == "seed" and "seed" in stage:
            values["bridge"] = copy.deepcopy(stage["seed"])
        if all(value != "NA" for value in values.values()):
            return values
    return p6_surface_value(stage, leg, variant)


def p6_unavailable_evidence(stage: dict[str, Any], variant: str) -> Any:
    evidence: dict[str, Any] = {
        "reason": f"sealed P1 surface does not expose {variant}",
        "stage_status": stage.get("status", "UNAVAILABLE"),
    }
    for key in (
        "evidence",
        "declared_surface_status",
        "transformation",
        "source_code",
        "seed",
    ):
        if key in stage:
            evidence[key] = copy.deepcopy(stage[key])
    return evidence


def p6_intentional_unavailable_kind(
    *,
    p6_status: Any,
    stage_name: str,
    stage: dict[str, Any],
    stage_present: bool,
    variant: str,
) -> str | None:
    """Whitelist only unavailable fields declared by the sealed P1 contract."""
    if p6_status != P6_SEALED_DISPOSITION:
        return None
    if stage.get("status") == "NO_SURFACE" and isinstance(stage.get("evidence"), str):
        return "SEALED_NO_SURFACE"
    if not stage_present and stage_name == "fit_sample_5000":
        return "OPERATOR_STAGE_OMITTED"
    if (
        stage_name == "boundary_bridge"
        and stage.get("status") == "AVAILABLE"
        and variant in {"seed", "sign_count", "weighted_sign_mass"}
    ):
        return "SEALED_DIAGNOSTIC_FIELD_NOT_DEFINED"
    return None


def intentional_p2_unavailable(row: dict[str, Any]) -> bool:
    """Recognize only the sealed A16-31 joint-domain placeholder cells."""
    dims = row.get("dimensions", {})
    if not (
        row.get("status") == "UNAVAILABLE"
        and dims.get("rung") == "candidate-25"
        and dims.get("row") == "P2_marginal_audit"
        and dims.get("variant") == "domain_violation_share"
    ):
        return False
    return any(
        source.get("producer_status") == "DESCRIPTIVE_NOT_A16_JOINT_GATE"
        and source.get("assembly_disposition") == P2_JOINT_DOMAIN_DISPOSITION
        and source.get("producer_value") != "NA"
        and source.get("producer_se") == "NA"
        and source.get("producer_mcse") == "NA"
        for source in row.get("sources", [])
    )


def intentional_p6_unavailable(row: dict[str, Any]) -> bool:
    if not (
        row.get("status") == "UNAVAILABLE"
        and row.get("dimensions", {}).get("row", "").startswith("P6_")
    ):
        return False
    stage_name = row["dimensions"]["row"][3:]
    variant = row["dimensions"].get("variant")
    for source in row.get("sources", []):
        if source.get("p6_disposition") != P6_SEALED_DISPOSITION:
            continue
        evidence = source.get("unavailable_evidence")
        if not isinstance(evidence, dict):
            continue
        kind = source.get("intentional_unavailable_kind")
        if (
            kind == "SEALED_NO_SURFACE"
            and source.get("stage_status") == "NO_SURFACE"
            and source.get("stage_present_in_sealed_p1") is True
            and isinstance(evidence.get("evidence"), str)
        ):
            return True
        if (
            kind == "OPERATOR_STAGE_OMITTED"
            and stage_name == "fit_sample_5000"
            and source.get("stage_status") == "UNAVAILABLE"
            and source.get("stage_present_in_sealed_p1") is False
        ):
            return True
        if (
            kind == "SEALED_DIAGNOSTIC_FIELD_NOT_DEFINED"
            and stage_name == "boundary_bridge"
            and variant in {"seed", "sign_count", "weighted_sign_mass"}
            and source.get("stage_status") == "AVAILABLE"
            and source.get("stage_present_in_sealed_p1") is True
        ):
            return True
    return False


def merge_p6_nested(
    p6: dict[str, Any],
    target: str,
    prefix: str,
    path: Path,
    artifact_source: dict[str, Any],
    manifest: list[dict[str, Any]],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
) -> None:
    p6_status = p6.get("status")
    stages = {
        item.get("stage"): (index, item)
        for index, item in enumerate(p6.get("stages", []))
        if isinstance(item, dict)
    }
    specials = {
        "boundary_bridge": (
            "/boundary_bridge",
            p6.get("boundary_bridge", {}),
        ),
        "clone2_tail_exclusion": (
            "/clone_2_tail_exclusion",
            p6.get("clone_2_tail_exclusion", {}),
        ),
        "clone_weight_bridge": (
            "/clone_value_and_weight_bridge",
            p6.get("clone_value_and_weight_bridge", {}),
        ),
    }
    for spec in manifest:
        dims = spec["dimensions"]
        if not (
            dims["rung"] == "candidate-25"
            and dims["target"] == target
            and dims["row"].startswith("P6_")
            and spec["id"] not in locked
        ):
            continue
        stage_name = dims["row"][3:]
        stage_record = stages.get(stage_name)
        special_record = specials.get(stage_name)
        if stage_record is not None:
            stage_index, stage = stage_record
            pointer = f"{prefix}/P6/stages/{stage_index}"
            stage_present = True
        elif special_record is not None:
            special_pointer, stage = special_record
            pointer = f"{prefix}/P6{special_pointer}"
            stage_present = True
        else:
            stage = {}
            pointer = f"{prefix}/P6"
            stage_present = False
        leg = dims["leg"]
        variant = dims["variant"]
        value: Any = "NA"
        status = "UNAVAILABLE"
        if stage.get("status") not in {"NO_SURFACE", "UNAVAILABLE", None}:
            if stage_name == "boundary_bridge" and variant == "incidence":
                value = stage.get("legs", {}).get(leg, {}).get("value", "NA")
            elif stage_name == "clone_weight_bridge":
                value = p6_clone_bridge_value(stage, leg, variant)
            elif variant == "seed" and "seed" in stage:
                value = copy.deepcopy(stage["seed"])
            else:
                value = p6_pattern_value(stage, leg, variant)
                if value == "NA":
                    value = p6_surface_value(stage, leg, variant)
            value = p6_scalar_representation(value)
            status = "OK" if value != "NA" else "UNAVAILABLE"
        source_extra: dict[str, Any] = {
            "stage": stage_name,
            "stage_status": stage.get("status", "UNAVAILABLE"),
            "p6_disposition": p6_status,
            "stage_present_in_sealed_p1": stage_present,
        }
        for key in (
            "declared_surface_status",
            "transformation",
            "source_code",
        ):
            if key in stage:
                source_extra[key] = copy.deepcopy(stage[key])
        if "seed" in stage:
            source_extra["seed_representation"] = copy.deepcopy(stage["seed"])
        if isinstance(stage.get("patterns"), list):
            source_extra["per_pattern_values"] = copy.deepcopy(
                p6_pattern_value(stage, leg, variant)
            )
        if stage_name == "clone_weight_bridge":
            source_extra["clone_bridge_variant_value"] = copy.deepcopy(
                p6_clone_bridge_value(stage, leg, variant)
            )
        if status == "UNAVAILABLE":
            source_extra["unavailable_evidence"] = p6_unavailable_evidence(
                stage, variant
            )
            intentional_kind = p6_intentional_unavailable_kind(
                p6_status=p6_status,
                stage_name=stage_name,
                stage=stage,
                stage_present=stage_present,
                variant=variant,
            )
            if intentional_kind is not None:
                source_extra["intentional_unavailable_kind"] = intentional_kind
        set_row(
            by_id[spec["id"]],
            spec,
            value=value,
            status=status,
            sources=[
                source_ref(
                    path.resolve(),
                    artifact_source["sha256"],
                    pointer,
                    **source_extra,
                ),
                executor_source("/merge_p6_nested"),
            ],
        )
        locked.add(spec["id"])


def merge_p7_nested(
    p7: dict[str, Any],
    target: str,
    prefix: str,
    path: Path,
    artifact_source: dict[str, Any],
    manifest: list[dict[str, Any]],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
) -> None:
    for spec in manifest:
        dims = spec["dimensions"]
        if not (
            dims["rung"] == "candidate-25"
            and dims["target"] == target
            and dims["row"] == "P7_GQ"
            and spec["id"] not in locked
        ):
            continue
        gq, leg, variant = dims["gq"], dims["leg"], dims["variant"]
        stratum = p7.get("strata", {}).get(gq, {})
        item: Any = None
        if variant == "omega":
            item = {"value": stratum.get("omega", "NA"), "se": "NA"}
        elif variant == "incidence":
            item = stratum.get("legs", {}).get(leg)
        elif variant == "adjustment":
            label = {
                "H": "J0_minus_I_H",
                "2": "adjustment_TYPEHUGQ_2",
                "3": "adjustment_TYPEHUGQ_3",
                "U": "adjustment_unprojectable",
            }[gq]
            item = p7.get("legs", {}).get(leg, {}).get(label)
        value, se, status = _nested_value(
            item or {"value": "NA", "status": "UNAVAILABLE"}
        )
        set_row(
            by_id[spec["id"]],
            spec,
            value=value,
            se=se,
            status=status,
            sources=[
                source_ref(path.resolve(), artifact_source["sha256"], f"{prefix}/P7")
            ],
        )
        locked.add(spec["id"])


def normal_p(value: float, uncertainty: float) -> tuple[float, float]:
    if uncertainty == 0.0:
        return (1.0, 0.0) if value == 0.0 else (0.0, math.copysign(math.inf, value))
    z = value / uncertainty
    return 2.0 * NormalDist().cdf(-abs(z)), z


def holm_loaded(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Apply A16-47, including zero-SE rules and the exact tie order."""
    eligible: list[tuple[float, float, str, float, float]] = []
    for row in rows:
        if normalize_status(row.get("status")) not in {
            "PASS",
            "FAIL",
            "OK",
            "SUPPORTED",
        }:
            continue
        value = row.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        se = row.get("se")
        mcse = row.get("mcse")
        uncertainty = (
            se
            if isinstance(se, (int, float))
            else mcse
            if isinstance(mcse, (int, float))
            else None
        )
        if (
            uncertainty is None
            or uncertainty < 0
            or not math.isfinite(float(value))
            or not math.isfinite(float(uncertainty))
        ):
            continue
        p, z = normal_p(float(value), float(uncertainty))
        eligible.append((p, -abs(z), row["id"], float(value), float(uncertainty)))
    eligible.sort(key=lambda item: (item[0], item[1], item[2]))
    rejected: set[str] = set()
    continuing = True
    m = len(eligible)
    for position, (p, _negative_abs_z, identifier, _value, _uncertainty) in enumerate(
        eligible
    ):
        threshold = 0.05 / (m - position)
        if continuing and p <= threshold:
            rejected.add(identifier)
        else:
            continuing = False
    result: dict[str, dict[str, Any]] = {}
    for p, negative_abs_z, identifier, value, uncertainty in eligible:
        z_abs: float | str = -negative_abs_z
        if isinstance(z_abs, float) and not math.isfinite(z_abs):
            z_abs = "inf"
        result[identifier] = {
            "p": p,
            "z_abs": z_abs,
            "holm_significant": identifier in rejected,
            "three_se": abs(value) >= 3.0 * uncertainty,
            "loaded": identifier in rejected and abs(value) >= 3.0 * uncertainty,
            "uncertainty": uncertainty,
        }
    return result


def family_loading(statistics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in statistics:
        family = row.get("family")
        if family not in {"F1", "F2", "F4", "F5"}:
            continue
        dims = row["dimensions"]
        # A16-25 supersedes A15.25: F1 contains only the eight top-level
        # additive rows.  A16-30 similarly limits F2 to the three aggregate
        # group rows plus the per-pattern closure rows.  Fold diagnostics are
        # outside A16-44's F5 family of target-leg statistics.
        if family == "F1" and dims["row"] not in TOP_LEVEL_ROWS:
            continue
        if family == "F2" and dims["row"] not in {
            "P2_group_aggregate",
            "e_D",
            "e_R",
            "e_T",
        }:
            continue
        if family == "F5" and dims["row"] != "C1_target_gap":
            continue
        if family == "F4" and not (
            dims["row"] == "P7_GQ"
            and dims["variant"] == "adjustment"
            and dims["gq"] in {"2", "3"}
        ):
            continue
        if family in {"F1", "F2"}:
            # A2's target x leg family is defined within a rung.  In
            # particular, the two baseline1pct F1 families must not change
            # candidate-25 Holm denominators or loading decisions.
            key = (family, dims["rung"], dims["target"], dims["leg"])
        else:
            # A2/A16-39 bind all 36 TYPEHUGQ 2/3 adjustment terms into
            # one F4 family.  F5 is likewise one global C1 target-leg family.
            key = (family, "_global", "_global")
        grouped[key].append(row)
    result: dict[str, dict[str, Any]] = {}
    for rows in grouped.values():
        result.update(holm_loaded(rows))
    return result


def finite_row(row: dict[str, Any]) -> bool:
    return (
        isinstance(row.get("value"), (int, float))
        and not isinstance(row.get("value"), bool)
        and math.isfinite(float(row["value"]))
    )


def dominant_label(
    shares: dict[str, float | str], loaded: dict[str, bool]
) -> tuple[str, float | str, str]:
    """Apply the frozen individual and named-row-set 60% rule."""
    candidates: list[tuple[float, str]] = []
    for name, share in shares.items():
        if isinstance(share, float) and share >= 0.60 and loaded[name]:
            candidates.append((share, name))
    for label, names in (("B1+B2", ("B1", "B2")), ("T4+T5", ("T4", "T5"))):
        share = math.fsum(float(shares[name]) for name in names)
        if share >= 0.60 and all(loaded[name] for name in names):
            candidates.append((share, label))
    if candidates:
        dominant_share, dominant_row = sorted(
            candidates, key=lambda item: (-item[0], item[1])
        )[0]
        return dominant_row, dominant_share, f"dominant — {dominant_row}"
    numeric = [float(value) for value in shares.values() if isinstance(value, float)]
    return "mixture", max(numeric) if numeric else "NA", "mixture / no dominant cause"


def verdict_for_leg(
    target: str,
    leg: str,
    rows_by_key: dict[tuple[str, str, str, str], dict[str, Any]],
    loading: dict[str, dict[str, Any]],
    support: str,
    classifications: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compute A16-45--52 at unrounded binary64 precision."""
    classifications = classifications or {}
    ledger = {
        name: rows_by_key.get(("candidate-25", target, leg, name))
        for name in TOP_LEVEL_ROWS
    }
    d_row = rows_by_key.get(("candidate-25", target, leg, "D"))
    j0 = rows_by_key.get(("candidate-25", target, leg, "J0"))
    i_acs = rows_by_key.get(("candidate-25", target, leg, "I_acs"))
    input_ids = [row["id"] for row in ledger.values() if row] + [
        row["id"] for row in (d_row, j0, i_acs) if row
    ]
    base = {
        "target": target,
        "leg": leg,
        "support": support,
        "input_statistic_ids": input_ids,
        "shares": {name: "NA" for name in TOP_LEVEL_ROWS},
        "loaded": {name: False for name in TOP_LEVEL_ROWS},
        "holm": {},
        "qualifying_parents": [],
        "mechanism_tags": {},
    }
    if support != "SUPPORTED":
        return {
            **base,
            "dominant_row": "NA",
            "dominant_share": "NA",
            "cancellation_index": "NA",
            "verdict": "insufficient support — no verdict",
            "defect_class": "NA",
            "arm_C_flag": "NO_GATING_INSUFFICIENT_SUPPORT",
            "arm_D_flag": "NO_D_INSUFFICIENT_SUPPORT",
            "arm_B_validation_flag": "DEFERRED_INSUFFICIENT_SUPPORT",
            "status": "INSUFFICIENT_SUPPORT_NO_VERDICT",
        }
    if not all(
        finite_row(row)
        for row in (*ledger.values(), d_row, j0, i_acs)
        if row is not None
    ) or any(row is None for row in (*ledger.values(), d_row, j0, i_acs)):
        return {
            **base,
            "dominant_row": "NA",
            "dominant_share": "NA",
            "cancellation_index": "NA",
            "verdict": "UNAVAILABLE — additive ledger or D uncertainty is incomplete",
            "defect_class": "UNAVAILABLE",
            "arm_C_flag": "UNAVAILABLE",
            "arm_D_flag": "UNAVAILABLE",
            "arm_B_validation_flag": "UNAVAILABLE",
            "status": "UNAVAILABLE",
        }
    if not isinstance(j0["se"], (int, float)) or not isinstance(
        i_acs["se"], (int, float)
    ):
        return {
            **base,
            "dominant_row": "NA",
            "dominant_share": "NA",
            "cancellation_index": "NA",
            "verdict": "UNAVAILABLE — SE(D) inputs are incomplete",
            "defect_class": "UNAVAILABLE",
            "arm_C_flag": "UNAVAILABLE",
            "arm_D_flag": "UNAVAILABLE",
            "arm_B_validation_flag": "UNAVAILABLE",
            "status": "UNAVAILABLE",
        }
    values = {name: float(row["value"]) for name, row in ledger.items()}
    d_value = float(d_row["value"])
    d_se = math.sqrt(float(j0["se"]) ** 2 + float(i_acs["se"]) ** 2)
    total_abs = math.fsum(abs(value) for value in values.values())
    shares = (
        {name: abs(value) / total_abs for name, value in values.items()}
        if total_abs > 0.0
        else {name: "NA" for name in TOP_LEVEL_ROWS}
    )
    cancellation: Any
    if total_abs == 0.0:
        cancellation = "NA"
    elif d_value == 0.0:
        cancellation = "inf"
    else:
        cancellation = total_abs / abs(d_value)
    loaded = {
        name: bool(loading.get(row["id"], {}).get("loaded", False))
        for name, row in ledger.items()
    }
    holm = {
        name: copy.deepcopy(loading.get(row["id"], {})) for name, row in ledger.items()
    }
    base.update(
        D=d_value,
        SE_D=d_se,
        sum_abs=total_abs,
        shares=shares,
        cancellation_index=cancellation,
        loaded=loaded,
        holm=holm,
    )

    if abs(d_value) <= 2.0 * d_se:
        return {
            **base,
            "dominant_row": "NA",
            "dominant_share": "NA",
            "verdict": "no material gap",
            "defect_class": "NO_MATERIAL_GAP",
            "arm_C_flag": "NO_GATING_NO_MATERIAL_GAP",
            "arm_D_flag": "NO_D_NO_MATERIAL_GAP",
            "arm_B_validation_flag": "NO_GATING_NO_MATERIAL_GAP",
            "status": "OK",
        }

    dominant_row, dominant_share, label = dominant_label(shares, loaded)

    intrinsic = {
        "L0": "UNRESOLVED",
        "B1": "UNRESOLVED",
        "B2": "UNRESOLVED",
        "T1": "ESTIMATOR_PROPERTY",
        "T2": "UNRESOLVED",
        "T3": "DEFECT",
        "T4": "UNRESOLVED",
        "T5": "UNRESOLVED",
    }
    # An empty Step-0 adjudication table prevents overrides of the rows whose
    # bug-vs-design status requires owner authority (H0/H6b/H7).
    for name, classification in classifications.items():
        if name == "T2" and classification in {"DEFECT", "NOT_DEFECT", "UNRESOLVED"}:
            intrinsic[name] = classification
    qualifying = [
        {
            "row": name,
            "share": shares[name],
            "classification": intrinsic[name],
        }
        for name in TOP_LEVEL_ROWS
        if loaded[name]
        and isinstance(shares[name], float)
        and float(shares[name]) >= 0.25
    ]
    qualifying.sort(key=lambda item: (-float(item["share"]), item["row"]))
    defects = [item for item in qualifying if item["classification"] == "DEFECT"]
    unresolved = [item for item in qualifying if item["classification"] == "UNRESOLVED"]
    arm_d = "CREATE_D" if defects else "NO_D"
    arm_c = (
        "BLOCK_C_DEFECT"
        if defects
        else "BLOCK_C_UNRESOLVED"
        if unresolved
        else "C_ELIGIBLE"
    )
    arm_b = "BLOCK_B_VALIDATION_DEFECT" if defects else "B_VALIDATION_ELIGIBLE"
    defect_class = (
        "DEFECT+UNRESOLVED"
        if defects and unresolved
        else "DEFECT"
        if defects
        else "UNRESOLVED"
        if unresolved
        else "NO_QUALIFYING_DEFECT"
    )
    mechanisms = {
        "L0": ["H0"],
        "B1": ["H7"],
        "B2": ["H7"],
        "T1": ["H1"],
        "T2": [],
        "T3": ["H6a"],
        "T4": ["H6b"],
        "T5": ["H6b"],
    }
    c1_gap = rows_by_key.get(("candidate-25", target, leg, "C1_target_gap"))
    if c1_gap and loading.get(c1_gap["id"], {}).get("loaded"):
        mechanisms["T1"].append("H2")
    p5_concentration = rows_by_key.get(
        ("candidate-25", target, leg, "P5_concentration")
    )
    if (
        loaded["T2"]
        and p5_concentration
        and finite_row(p5_concentration)
        and float(p5_concentration["value"]) >= 0.5
    ):
        mechanisms["T2"].append("H5")
    qualifying_parents = [item["row"] for item in qualifying]
    return {
        **base,
        "dominant_row": dominant_row,
        "dominant_share": dominant_share,
        "verdict": label,
        "defect_class": defect_class,
        "arm_C_flag": arm_c,
        "arm_D_flag": arm_d,
        "arm_B_validation_flag": arm_b,
        "qualifying_parents": qualifying_parents,
        "qualifying_parent_details": qualifying,
        "primary_parent": qualifying_parents[0] if qualifying_parents else "NA",
        "mechanism_tags": {name: mechanisms[name] for name in qualifying_parents},
        "status": "OK",
    }


def statistic_key_index(
    statistics: list[dict[str, Any]],
) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    result: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in statistics:
        dims = row["dimensions"]
        key = (dims["rung"], dims["target"], dims["leg"], dims["row"])
        if (
            dims["pattern"]
            == dims["group"]
            == dims["prior"]
            == dims["gq"]
            == dims["decile"]
            == dims["repeat"]
            == dims["fold"]
            == dims["variant"]
            == NA
        ):
            result[key] = row
    return result


def apply_verdicts(
    statistics: list[dict[str, Any]],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
    targets: list[str],
    verdict_source: dict[str, Any],
    classifications: dict[str, Any],
) -> list[dict[str, Any]]:
    loading = family_loading(statistics)
    key_index = statistic_key_index(statistics)
    summaries: list[dict[str, Any]] = []
    for target in targets:
        for leg in LEGS:
            support_id = dimension_id(
                list(manifest_by_id.values()),
                rung="candidate-25",
                target=target,
                leg=leg,
                row="verdict",
                variant="support",
            )
            support = str(by_id[support_id]["value"])
            classification = (
                classifications.get(target, {}).get(leg, {})
                if isinstance(classifications, dict)
                else {}
            )
            verdict = verdict_for_leg(
                target, leg, key_index, loading, support, classification
            )
            source = copy.deepcopy(verdict_source)
            source["input_statistic_ids"] = verdict["input_statistic_ids"]
            verdict["sources"] = [copy.deepcopy(source)]
            summaries.append(verdict)
            values = {
                "dominant_row": verdict["dominant_row"],
                "dominant_share": verdict["dominant_share"],
                "cancellation_index": verdict["cancellation_index"],
                "verdict": verdict["verdict"],
                "defect_class": verdict["defect_class"],
                "arm_C_flag": verdict["arm_C_flag"],
                "arm_D_flag": verdict["arm_D_flag"],
                "arm_B_validation_flag": verdict["arm_B_validation_flag"],
            }
            for variant, value in values.items():
                identifier = dimension_id(
                    list(manifest_by_id.values()),
                    rung="candidate-25",
                    target=target,
                    leg=leg,
                    row="verdict",
                    variant=variant,
                )
                require(
                    identifier not in locked,
                    f"verdict cell was prepopulated: {identifier}",
                )
                set_row(
                    by_id[identifier],
                    manifest_by_id[identifier],
                    value=value,
                    status=verdict["status"],
                    sources=[source],
                )
                locked.add(identifier)
    return summaries


def apply_p8(
    manifest: list[dict[str, Any]],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
    authority: dict[str, str],
    controls_pass: bool,
) -> dict[str, Any]:
    note = (
        "SSI is a simulated output, not a QRF target. Its installed unearned-income "
        f"source directly names {', '.join(SSI_DIRECT_INPUTS)}. It does not directly "
        f"name {', '.join(SSI_NOT_DIRECT_INPUTS)}. This is a dependency note only: "
        "it has no gate, root-cause attribution, controls, or arm-C eligibility."
    )
    identifier = dimension_id(
        manifest, rung="candidate-25", target="ssi", row="P8_ssi_dependency_note"
    )
    status = "OK" if controls_pass else "NOT_RUN_CONTROLS_FAILED"
    value = note if controls_pass else "NA"
    source = source_ref(
        D0_MARKDOWN,
        authority[str(D0_MARKDOWN)],
        "/D0-7",
        installed_policyengine_us="1.819.0",
    )
    set_row(
        by_id[identifier],
        manifest_by_id[identifier],
        value=value,
        status=status,
        sources=[source],
    )
    locked.add(identifier)
    return {"status": status, "note": note, "source": source}


def cross_rung_snapshot(
    available: dict[str, dict[str, Any]], rung: str
) -> dict[str, Any]:
    def cell(name: str) -> dict[str, Any]:
        row = available[f"{rung}:{name}"]
        return {
            "id": row["id"],
            "value": row["value"],
            "se": row["se"],
            "status": row["status"],
        }

    return {
        "D": cell("D"),
        "top_level_rows": {name: cell(name) for name in TOP_LEVEL_ROWS},
    }


def apply_cross_rung(
    manifest: list[dict[str, Any]],
    manifest_by_id: dict[str, dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    locked: set[str],
    verdicts: list[dict[str, Any]],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    verdict_lookup = {(item["target"], item["leg"]): item for item in verdicts}
    loading = family_loading(list(by_id.values()))
    output: list[dict[str, Any]] = []
    populated: set[str] = set()
    for target in ("self_employment_income_last_year", "spm_unit_energy_subsidy"):
        available: dict[str, dict[str, Any]] = {}
        for rung in ("candidate-25", "baseline1pct"):
            for row_name in ("D", "J0", "I_acs", *TOP_LEVEL_ROWS):
                try:
                    identifier = dimension_id(
                        manifest, rung=rung, target=target, leg="positive", row=row_name
                    )
                except ValueError:
                    continue
                available[f"{rung}:{row_name}"] = by_id[identifier]
        d25, d1 = available.get("candidate-25:D"), available.get("baseline1pct:D")
        d_tension: Any = "NA"
        if (
            d25
            and d1
            and finite_row(d25)
            and finite_row(d1)
            and isinstance(d25["se"], (int, float))
            and isinstance(d1["se"], (int, float))
        ):
            d_tension = abs(float(d25["value"]) - float(d1["value"])) > 3.0 * math.sqrt(
                float(d25["se"]) ** 2 + float(d1["se"]) ** 2
            )
        row_tensions: list[bool] = []
        for row_name in TOP_LEVEL_ROWS:
            left, right = (
                available.get(f"candidate-25:{row_name}"),
                available.get(f"baseline1pct:{row_name}"),
            )
            if (
                left
                and right
                and finite_row(left)
                and finite_row(right)
                and isinstance(left["se"], (int, float))
                and isinstance(right["se"], (int, float))
            ):
                row_tensions.append(
                    abs(float(left["value"]) - float(right["value"]))
                    > 3.0 * math.sqrt(float(left["se"]) ** 2 + float(right["se"]) ** 2)
                )
        top_tension: Any = (
            any(row_tensions) if len(row_tensions) == len(TOP_LEVEL_ROWS) else "NA"
        )
        candidate_label = verdict_lookup[(target, "positive")]["dominant_row"]
        baseline_rows = {
            name: available.get(f"baseline1pct:{name}") for name in TOP_LEVEL_ROWS
        }
        baseline_label: Any = "NA"
        baseline_d = available.get("baseline1pct:D")
        baseline_j0 = available.get("baseline1pct:J0")
        baseline_i_acs = available.get("baseline1pct:I_acs")
        if (
            all(row is not None and finite_row(row) for row in baseline_rows.values())
            and baseline_d
            and baseline_j0
            and baseline_i_acs
            and finite_row(baseline_d)
            and isinstance(baseline_j0.get("se"), (int, float))
            and isinstance(baseline_i_acs.get("se"), (int, float))
        ):
            baseline_se_d = math.sqrt(
                float(baseline_j0["se"]) ** 2 + float(baseline_i_acs["se"]) ** 2
            )
            if abs(float(baseline_d["value"])) > 2.0 * baseline_se_d:
                absolute = {
                    name: abs(float(row["value"]))
                    for name, row in baseline_rows.items()
                    if row is not None
                }
                total = math.fsum(absolute.values())
                shares = (
                    {name: absolute[name] / total for name in TOP_LEVEL_ROWS}
                    if total > 0.0
                    else {name: "NA" for name in TOP_LEVEL_ROWS}
                )
                loaded = {
                    name: bool(loading.get(row["id"], {}).get("loaded"))
                    for name, row in baseline_rows.items()
                    if row is not None
                }
                baseline_label = dominant_label(shares, loaded)[0]
        label_tension: Any = (
            candidate_label != baseline_label
            if candidate_label != "NA" and baseline_label != "NA"
            else "NA"
        )
        values = {
            "D": d_tension,
            "top_level_rows": top_tension,
            "dominant_label": label_tension,
        }
        for variant, value in values.items():
            identifier = dimension_id(
                manifest,
                rung="cross-rung",
                target=target,
                leg="positive",
                row="cross_rung_tension",
                variant=variant,
            )
            status = "OK" if isinstance(value, bool) else "UNAVAILABLE"
            set_row(
                by_id[identifier],
                manifest_by_id[identifier],
                value=value,
                status=status,
                sources=[source],
            )
            locked.add(identifier)
            populated.add(identifier)
        summary_source = copy.deepcopy(source)
        summary_source["input_statistic_ids"] = sorted(
            row["id"] for row in available.values()
        )
        output.append(
            {
                "target": target,
                **values,
                "candidate_label": candidate_label,
                "baseline_label": baseline_label,
                "candidate": cross_rung_snapshot(available, "candidate-25"),
                "baseline": cross_rung_snapshot(available, "baseline1pct"),
                "sources": [summary_source],
            }
        )
    expected = {
        spec["id"]
        for spec in manifest
        if spec["dimensions"]["rung"] == "cross-rung"
        and spec["dimensions"]["row"] == "cross_rung_tension"
    }
    require(populated == expected, "cross-rung tension roster was not filled exactly")
    return output


def p6_target_detail(
    target: str,
    p1_artifact: tuple[dict[str, Any], dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if p1_artifact is None:
        return None
    payload, artifact_source = p1_artifact
    p6 = payload.get("candidate-25", {}).get("targets", {}).get(target, {}).get("P6")
    if not isinstance(p6, dict):
        return None
    return {
        "sealed_payload": copy.deepcopy(p6),
        "sources": [
            source_ref(
                artifact_source["path"],
                artifact_source["sha256"],
                f"/candidate-25/targets/{target}/P6",
                self_excluding_sha256=artifact_source.get("self_excluding_sha256"),
            )
        ],
    }


def p6_bridge_closure_rows(
    target: str,
    leg: str,
    detail: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if detail is None:
        return []
    bridge = detail["sealed_payload"].get("clone_value_and_weight_bridge", {})
    leg_values = bridge.get("legs", {}).get(leg, {})
    if not isinstance(leg_values, dict):
        return []
    source = copy.deepcopy(detail["sources"][0])
    source["pointer"] += f"/clone_value_and_weight_bridge/legs/{leg}"
    derived_source = executor_source("/p6_bridge_closure_rows")
    rows: list[dict[str, Any]] = []
    for name in ("producer_value_bridge", "clone_weight_bridge", "sum_equals_B1"):
        value = leg_values.get(name, "NA")
        rows.append(
            {
                "id": f"diagnostic|{target}|{leg}|P6_bridge_{name}",
                "dimensions": {
                    "rung": "candidate-25",
                    "target": target,
                    "pattern": NA,
                    "leg": leg,
                    "row": f"P6_bridge_{name}",
                    "group": NA,
                    "prior": NA,
                    "gq": NA,
                    "decile": NA,
                    "repeat": NA,
                    "fold": NA,
                    "variant": "diagnostic_only",
                },
                "record_type": "scalar",
                "value": value,
                "se": "NA",
                "mcse": "NA",
                "family": None,
                "gated": False,
                "status": "OK" if value != "NA" else "UNAVAILABLE",
                "default_resolved": False,
                "diagnostic_only": True,
                "sources": [copy.deepcopy(source), copy.deepcopy(derived_source)],
            }
        )
    return rows


def p6_report_sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    dims = row["dimensions"]
    stage = dims["row"][3:] if dims["row"].startswith("P6_") else dims["row"]
    stage_order = {name: index for index, name in enumerate(P6_STAGE_ORDER)}
    variant_order = {name: index for index, name in enumerate(P6_VARIANT_ORDER)}
    return (
        stage_order.get(stage, len(stage_order)),
        variant_order.get(dims.get("variant"), len(variant_order)),
        row["id"],
    )


def build_target_sections(
    statistics: list[dict[str, Any]],
    targets: list[str],
    verdicts: list[dict[str, Any]],
    p1_artifact: tuple[dict[str, Any], dict[str, Any]] | None = None,
    *,
    p2_not_validated_complete: bool = False,
    p6_no_surface_complete: bool = False,
    completion_barrier_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verdict_lookup = {(item["target"], item["leg"]): item for item in verdicts}
    loading = family_loading(statistics)
    assembly_source = executor_source("/build_target_sections")

    def report_row(row: dict[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(row)
        if row["id"] in loading:
            result["holm_loading"] = {
                **copy.deepcopy(loading[row["id"]]),
                "sources": [copy.deepcopy(assembly_source)],
            }
            result.setdefault("sources", []).append(copy.deepcopy(assembly_source))
        return result

    sections: dict[str, Any] = {}
    for target in targets:
        p6_detail = p6_target_detail(target, p1_artifact)
        target_rows = [
            row for row in statistics if row["dimensions"]["target"] == target
        ]
        p0 = [
            row
            for row in target_rows
            if row["dimensions"]["rung"] == "candidate-25"
            and (
                row["dimensions"]["row"].startswith("P0_")
                or row["dimensions"]["row"] == "phi"
            )
        ]
        legs: dict[str, Any] = {}
        for leg in LEGS:
            verdict = verdict_lookup[(target, leg)]
            leg_rows = [
                row for row in target_rows if row["dimensions"]["leg"] in {leg, NA}
            ]
            ledger = [
                report_row(
                    next(
                        row
                        for row in target_rows
                        if row["dimensions"]["rung"] == "candidate-25"
                        and row["dimensions"]["leg"] == leg
                        and row["dimensions"]["row"] == name
                        and row["dimensions"]["variant"] == NA
                    )
                )
                for name in (*LEVEL_ROWS, *TOP_LEVEL_ROWS, "residual")
            ]
            for row in ledger:
                row_name = row["dimensions"]["row"]
                if row_name not in TOP_LEVEL_ROWS:
                    continue
                row["additive_share"] = {
                    "value": verdict["shares"][row_name],
                    "sources": copy.deepcopy(verdict.get("sources", [])),
                }
                row.setdefault("sources", []).extend(
                    copy.deepcopy(verdict.get("sources", []))
                )
            attribution = [
                report_row(row)
                for row in leg_rows
                if is_p2_row(row["dimensions"]["row"])
            ]
            p6_rows = [
                report_row(row)
                for row in leg_rows
                if row["dimensions"]["row"].startswith("P6_")
            ] + p6_bridge_closure_rows(target, leg, p6_detail)
            p6_rows.sort(key=p6_report_sort_key)
            diagnostic_rows = {
                "B2 selection telescope": [
                    report_row(row)
                    for row in leg_rows
                    if row["dimensions"]["row"].startswith("B2_")
                ],
                "P6 producer ledger": p6_rows,
                "P5 Gower support": [
                    report_row(row)
                    for row in leg_rows
                    if row["dimensions"]["row"].startswith("P5_")
                ],
                "P7 GQ identity": [
                    report_row(row)
                    for row in leg_rows
                    if row["dimensions"]["row"].startswith("P7_")
                ],
                # Fold cells remain in the authoritative flat statistics
                # array; the target-leg estimator is the official C1 reading.
                "C1 cross-fitted target gap": [
                    report_row(row)
                    for row in leg_rows
                    if row["dimensions"]["row"] == "C1_target_gap"
                ],
            }
            probes: dict[str, Any] = {}
            for probe, predicate in {
                "P0": lambda name: name.startswith("P0_"),
                "P1": lambda name: (
                    name in LEVEL_ROWS
                    or name in TOP_LEVEL_ROWS
                    or name == "residual"
                    or name.startswith("B2_")
                ),
                "P2": is_p2_row,
                "P5": lambda name: name.startswith("P5_"),
                "P6": lambda name: name.startswith("P6_"),
                "P7": lambda name: name.startswith("P7_"),
                "C1": lambda name: name.startswith("C1_"),
            }.items():
                rows = [row for row in leg_rows if predicate(row["dimensions"]["row"])]
                statuses = Counter(row["status"] for row in rows)
                completion_neutral = [
                    row
                    for row in rows
                    if (
                        probe == "P2"
                        and p2_not_validated_complete
                        and intentional_p2_unavailable(row)
                    )
                    or (
                        probe == "P6"
                        and p6_no_surface_complete
                        and intentional_p6_unavailable(row)
                    )
                ]
                incomplete_rows = [
                    row
                    for row in rows
                    if row["status"] in INCOMPLETE_STATUSES
                    and row not in completion_neutral
                ]
                reason = ""
                if not rows:
                    status = "NOT_APPLICABLE"
                    reason = (
                        "no registered cells for this target-leg; the class is absent "
                        "from the frozen probe roster"
                    )
                elif incomplete_rows:
                    status = next(
                        candidate
                        for candidate in INCOMPLETE_STATUS_PRIORITY
                        if any(row["status"] == candidate for row in incomplete_rows)
                    )
                elif probe == "P2" and completion_neutral:
                    status = P2_NOT_VALIDATED_DISPOSITION
                    reason = (
                        "the exact A16-31 joint-domain placeholders retain their "
                        "unavailable cells under the bound NOT_VALIDATED barrier disposition"
                    )
                elif probe == "P6" and completion_neutral:
                    status = P6_COMPLETE_NO_SURFACE
                    reason = (
                        "the exact sealed P1 no-surface disposition is complete under "
                        "the bound readings barrier; unavailable cells retain evidence"
                    )
                elif "NOT_VALIDATED" in statuses:
                    status = "NOT_VALIDATED"
                elif "UNSUPPORTED" in statuses:
                    status = "COMPLETE_WITH_UNSUPPORTED"
                else:
                    status = "COMPLETE"
                probe_source_map: dict[tuple[str, str], dict[str, str]] = {}
                for row in rows:
                    for source in row.get("sources", []):
                        path, digest = source.get("path"), source.get("sha256")
                        if isinstance(path, str) and isinstance(digest, str):
                            probe_source_map[(path, digest)] = {
                                "path": path,
                                "sha256": digest,
                            }
                probe_source_map[
                    (assembly_source["path"], assembly_source["sha256"])
                ] = copy.deepcopy(assembly_source)
                if (
                    probe in {"P2", "P6"}
                    and completion_neutral
                    and completion_barrier_source is not None
                ):
                    probe_source_map[
                        (
                            completion_barrier_source["path"],
                            completion_barrier_source["sha256"],
                        )
                    ] = copy.deepcopy(completion_barrier_source)
                probes[probe] = {
                    "status": status,
                    "reason": reason,
                    "status_counts": dict(statuses),
                    "completion_neutral_status_counts": dict(
                        Counter(row["status"] for row in completion_neutral)
                    ),
                    "statistic_ids": [row["id"] for row in rows],
                    "sources": list(probe_source_map.values()),
                }
            legs[leg] = {
                "ledger": ledger,
                "attribution": attribution,
                "diagnostic_rows": diagnostic_rows,
                "probes": probes,
                "verdict": verdict,
            }
        sections[target] = {
            "P0": p0,
            "P6_sealed_detail": p6_detail,
            "legs": legs,
        }
    return sections


def probe_bucket(row_name: str) -> str:
    if row_name.startswith("P0_") or row_name == "phi":
        return "P0"
    if is_p2_row(row_name):
        return "P2"
    for name in ("P5", "P6", "P7", "C1"):
        if row_name.startswith(f"{name}_"):
            return name
    if (
        row_name in LEVEL_ROWS
        or row_name in TOP_LEVEL_ROWS
        or row_name == "residual"
        or row_name.startswith("B2_")
    ):
        return "P1"
    if row_name == "verdict":
        return "VERDICTS"
    if row_name == "cross_rung_tension":
        return "CROSS_RUNG"
    if row_name.startswith("P8_"):
        return "P8"
    return "CONTROL_OR_SETUP"


def incomplete_statistics(
    statistics: Iterable[dict[str, Any]],
    *,
    p2_not_validated_complete: bool = False,
    p6_no_surface_complete: bool = False,
) -> Counter[tuple[str, str]]:
    """Count incomplete cells, narrowly exempting barrier-authorized P6 evidence."""
    return Counter(
        (row["status"], probe_bucket(row["dimensions"]["row"]))
        for row in statistics
        if row["status"] in INCOMPLETE_STATUSES
        and not (
            (p2_not_validated_complete and intentional_p2_unavailable(row))
            or (p6_no_surface_complete and intentional_p6_unavailable(row))
        )
    )


def phase0_run_status(c3_pass: bool, incomplete: Counter[tuple[str, str]]) -> str:
    if not c3_pass:
        return "CONTROLS_FAILED"
    return "PARTIAL" if incomplete else "COMPLETE"


def support_by_target(
    d0: dict[str, Any], targets: list[str], source: dict[str, Any]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for target in targets:
        result[target] = {}
        for leg in LEGS:
            rung = d0["D0-1"]["rungs"]["candidate-25"][target]
            # Section 3.7 binds support to the clone-0 battery estimand, not
            # the larger all-clones diagnostic census.  The distinction is
            # material for the sparse SEILY negative leg (48 rather than 69)
            # and must also be reflected in the printed counts.
            asec = rung["asec"]["legs"][leg][
                "unique_clone_deduplicated_source_rows_clone0"
            ]
            acs = rung["acs"]["legs"][leg][
                "unique_clone_deduplicated_source_rows_clone0"
            ]
            status = (
                "INSUFFICIENT_SUPPORT_NO_VERDICT"
                if min(asec, acs) < 50
                else "SUPPORTED"
            )
            if target == "self_employment_income_last_year" and leg == "negative":
                status = "INSUFFICIENT_SUPPORT_NO_VERDICT"
            result[target][leg] = {
                "asec": asec,
                "acs": acs,
                "status": status,
                "sources": [copy.deepcopy(source)],
            }
    return result


def build_required_highlights(
    p1_artifact: tuple[dict[str, Any], dict[str, Any]] | None,
    d0_source: dict[str, Any],
) -> dict[str, Any]:
    """Preserve the two user-required structural/bridge readings in JSON."""
    if p1_artifact is None:
        return {
            "status": "UNAVAILABLE",
            "reason": "P0/P1 artifact was not supplied",
            "sources": [copy.deepcopy(d0_source)],
        }
    payload, artifact_source = p1_artifact
    assembly_source = executor_source("/build_required_highlights")
    targets = payload.get("candidate-25", {}).get("targets", {})
    care = targets.get("pre_subsidy_care_expenses", {})
    weeks = targets.get("weeks_unemployed", {})
    require(
        care.get("status") == "COMPLETE" and weeks.get("status") == "COMPLETE",
        "required care/weeks highlights need complete P1 target readings",
    )
    care_structural = care["P1"]["structural"]
    care_t5 = care["P1"]["ledger"]["positive"]["rows"]["T5"]
    weeks_rows = weeks["P1"]["ledger"]["positive"]["rows"]
    weeks_d = weeks["P1"]["levels"]["positive"]["D"]
    baseline_cleared = 183
    candidate_cleared = int(care_structural["cleared_positive_rows"])
    p1_source = source_ref(
        artifact_source["path"],
        artifact_source["sha256"],
        "/candidate-25/targets",
        self_excluding_sha256=artifact_source.get("self_excluding_sha256"),
    )
    care_sources = [
        copy.deepcopy(p1_source),
        source_ref(
            d0_source["path"],
            d0_source["sha256"],
            "/D0-4/targets/5",
        ),
        copy.deepcopy(assembly_source),
    ]
    weeks_source = source_ref(
        artifact_source["path"],
        artifact_source["sha256"],
        "/candidate-25/targets/weeks_unemployed/P1",
        self_excluding_sha256=artifact_source.get("self_excluding_sha256"),
    )

    def weeks_component(name: str) -> dict[str, Any]:
        item = weeks_rows[name]
        return {
            "value": item["value"],
            "se": item["se"],
            "share_of_signed_D": item["value"] / weeks_d["value"],
            "sources": [
                copy.deepcopy(weeks_source),
                copy.deepcopy(assembly_source),
            ],
        }

    return {
        "status": "COMPLETE",
        "pre_subsidy_care_expenses": {
            "baseline1pct_D0_4_cleared_positive_draws": baseline_cleared,
            "candidate_25_cleared_positive_draws": candidate_cleared,
            "additional_cleared_draws": candidate_cleared - baseline_cleared,
            "T5": {
                "value": care_t5["value"],
                "se": care_t5["se"],
                "sources": [
                    copy.deepcopy(p1_source),
                    copy.deepcopy(assembly_source),
                ],
            },
            "relationship": "CONFIRMS_AND_EXTENDS_D0_4",
            "cleared_mask_sha256": care_structural["cleared_mask"]["sha256"],
            "sources": care_sources,
        },
        "weeks_unemployed": {
            "D": {
                "value": weeks_d["value"],
                "se": weeks_d["se"],
                "sources": [
                    copy.deepcopy(weeks_source),
                    copy.deepcopy(assembly_source),
                ],
            },
            "B1": weeks_component("B1"),
            "T5": weeks_component("T5"),
            "T2": weeks_component("T2"),
            "sources": [
                copy.deepcopy(weeks_source),
                copy.deepcopy(assembly_source),
            ],
        },
    }


def global_reading_dispositions(
    reading_payloads: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    p2_targets: set[str] = set()
    p2_sources: list[dict[str, Any]] = []
    for payload, source in reading_payloads:
        targets = p2_domain_gap_targets(payload)
        if not targets:
            continue
        p2_targets.update(targets)
        p2_sources.append(
            source_ref(
                source["path"],
                source["sha256"],
                "/targets/*/joint_hybrid_domain",
                self_excluding_sha256=source.get("self_excluding_sha256"),
            )
        )
    if not p2_targets:
        return {}
    return {
        "P2": {
            "status": "NOT_VALIDATED",
            "reason": (
                "D0 did not enumerate A16-31 joint hybrid-domain predicates; "
                "group and prior estimates remain numerical diagnostics only"
            ),
            "targets": sorted(p2_targets),
            "affected_rows": sorted(P2_DOMAIN_INVALIDATED_ROWS),
            "marginal_domain_violation_share": "UNAVAILABLE_NOT_A_JOINT_GATE",
            "sources": p2_sources,
        }
    }


def fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "inf" if value > 0 else "-inf"
        return "0" if value == 0.0 else format(value, ".6g")
    if value is None:
        return "NA"
    return str(value)


def render_p6_structured_value(value: Any) -> str:
    """Render structured P6 evidence with six-significant-digit numeric leaves."""

    def structured(item: Any) -> str:
        if item is None:
            return "null"
        if isinstance(item, bool):
            return "true" if item else "false"
        if isinstance(item, int):
            return format(item, ".6g")
        if isinstance(item, float):
            return fmt(item)
        if isinstance(item, str):
            return json.dumps(item, ensure_ascii=False)
        if isinstance(item, list):
            return "[" + ",".join(structured(child) for child in item) + "]"
        if isinstance(item, dict):
            return (
                "{"
                + ",".join(
                    json.dumps(str(key), ensure_ascii=False)
                    + ":"
                    + structured(item[key])
                    for key in sorted(item)
                )
                + "}"
            )
        return json.dumps(str(item), ensure_ascii=False)

    if isinstance(value, str) and value[:1] in {"{", "["}:
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        if isinstance(decoded, (dict, list)):
            return structured(decoded)
    if isinstance(value, (dict, list)):
        return structured(value)
    return fmt(value)


def source_catalog(
    statistics: list[dict[str, Any]], fixed: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], str]]:
    catalog: list[dict[str, Any]] = []
    lookup: dict[tuple[str, str], str] = {}
    for source in [
        *fixed,
        *(item for row in statistics for item in row.get("sources", [])),
    ]:
        path, digest = source.get("path"), source.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            continue
        key = (path, digest)
        if key not in lookup:
            label = f"S{len(catalog) + 1}"
            lookup[key] = label
            catalog.append({"label": label, "path": path, "sha256": digest})
    return catalog, lookup


def source_labels(row: dict[str, Any], lookup: dict[tuple[str, str], str]) -> str:
    labels: list[str] = []
    seen: set[str] = set()
    for source in row.get("sources", []):
        label = lookup.get((source.get("path"), source.get("sha256")))
        rendered = label + str(source.get("pointer", "")) if label else None
        if rendered and rendered not in seen:
            seen.add(rendered)
            labels.append(rendered)
    return ", ".join(labels) or "NA"


def valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def valid_producer_metadata_source(source: dict[str, Any]) -> bool:
    """Recognize the sealed P2 lineage object, which is not an artifact ref."""
    return (
        set(source) == {"design_sha256", "d0_sha256", "pointer"}
        and source.get("design_sha256") == EXPECTED_AUTHORITY[DESIGN]
        and source.get("d0_sha256") == EXPECTED_AUTHORITY[D0_JSON]
        and isinstance(source.get("pointer"), str)
        and source["pointer"].startswith("/")
        and len(source["pointer"]) > 1
    )


def validate_nested_source_lists(
    value: Any,
    catalog_keys: set[tuple[str, str]],
    context: str,
) -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_nested_source_lists(item, catalog_keys, f"{context}/{index}")
        return
    if not isinstance(value, dict):
        return
    sources = value.get("sources")
    if isinstance(sources, list):
        require(sources, f"empty source list at {context}")
        cataloged = 0
        for index, source in enumerate(sources):
            require(isinstance(source, dict), f"non-object source at {context}/{index}")
            has_path = "path" in source
            has_digest = "sha256" in source
            if not has_path and not has_digest:
                require(
                    valid_producer_metadata_source(source),
                    f"untyped source metadata at {context}/{index}",
                )
                continue
            require(
                has_path and has_digest,
                f"source path/SHA-256 pair is incomplete at {context}/{index}",
            )
            path, digest = source["path"], source["sha256"]
            require(
                isinstance(path, str) and path,
                f"source path is absent at {context}/{index}",
            )
            require(
                valid_sha256(digest),
                f"source SHA-256 is invalid at {context}/{index}",
            )
            require(
                (path, digest) in catalog_keys,
                f"source is absent from the catalog at {context}/{index}",
            )
            cataloged += 1
        require(
            cataloged >= 1,
            f"source list has no cataloged artifact/code reference at {context}",
        )
    for key, item in value.items():
        if key != "sources":
            validate_nested_source_lists(item, catalog_keys, f"{context}/{key}")


def validate_report_contract(
    result: dict[str, Any],
    targets: list[str],
    p1_artifact: tuple[dict[str, Any], dict[str, Any]] | None,
) -> None:
    """Supplement the immutable permissive Step-0 schema with report checks."""
    catalog = result["source_catalog"]
    catalog_keys = {(item["path"], item["sha256"]) for item in catalog}
    executor_binding = executor_source()
    require(len(catalog_keys) == len(catalog), "source catalog has duplicate keys")
    require(
        all(valid_sha256(item.get("sha256")) for item in catalog),
        "source catalog contains an invalid SHA-256",
    )
    for row in result["statistics"]:
        validate_nested_source_lists(row, catalog_keys, f"statistics/{row['id']}")
    authorizations = result["reading_completion_authorizations"]
    p2_authorization = authorizations["P2_evidenced_unavailable"]
    p6_authorization = authorizations["P6_evidenced_unavailable"]
    actual_p2_evidence = sum(
        intentional_p2_unavailable(row) for row in result["statistics"]
    )
    actual_p6_evidence = sum(
        intentional_p6_unavailable(row) for row in result["statistics"]
    )
    require(
        p2_authorization["evidenced_cell_count"] == actual_p2_evidence
        and p6_authorization["evidenced_cell_count"] == actual_p6_evidence,
        "completion-authorization evidence counts differ from flat statistics",
    )
    if p2_authorization["authorized"]:
        require(
            p2_authorization["required_barrier_disposition"]
            == P2_NOT_VALIDATED_DISPOSITION
            and actual_p2_evidence == EXPECTED_P2_EVIDENCED_UNAVAILABLE,
            "P2 completion authorization lacks the exact 312-cell disposition",
        )
    if p6_authorization["authorized"]:
        require(
            p6_authorization["required_barrier_disposition"] == P6_COMPLETE_NO_SURFACE
            and p6_authorization["required_sealed_p1_disposition"]
            == P6_SEALED_DISPOSITION
            and actual_p6_evidence == EXPECTED_P6_EVIDENCED_UNAVAILABLE,
            "P6 completion authorization lacks the exact 504-cell disposition",
        )
    validate_nested_source_lists(
        authorizations,
        catalog_keys,
        "reading_completion_authorizations",
    )
    if result["status"] == "CONTROLS_FAILED":
        require(result["targets"] == {}, "control failure opened target sections")
        require(
            result["cross_target_summary"] == [],
            "control failure opened cross-target verdicts",
        )
        return

    require(
        list(result["targets"]) == targets,
        "target sections differ from the D0 stable roster",
    )
    require(
        len(result["cross_target_summary"]) == len(targets) * len(LEGS),
        "cross-target summary is not target by leg complete",
    )
    summary_lookup = {
        (item["target"], item["leg"]): item for item in result["cross_target_summary"]
    }
    eligible_f4 = 0
    loaded_f4 = 0
    for target in targets:
        section = result["targets"][target]
        require(set(section["legs"]) == set(LEGS), f"leg roster changed for {target}")
        if p1_artifact is not None:
            expected_p6 = p1_artifact[0]["candidate-25"]["targets"][target].get("P6")
            require(
                section["P6_sealed_detail"]["sealed_payload"] == expected_p6,
                f"sealed P6 detail changed for {target}",
            )
            p0_path_row = next(
                row
                for row in section["P0"]
                if row["dimensions"]["row"] == "P0_path_census"
            )
            anchors = next(
                (
                    source.get("path_code_anchors")
                    for source in p0_path_row.get("sources", [])
                    if isinstance(source.get("path_code_anchors"), dict)
                ),
                None,
            )
            require(
                isinstance(anchors, dict)
                and set(anchors) == set(P0_PATH_EXECUTOR_ANCHOR),
                f"P0 path census lacks exact code anchors for {target}",
            )
            for path_stage, anchor in anchors.items():
                require(
                    anchor.get("predicate_anchor")
                    == P0_PATH_EXECUTOR_ANCHOR[path_stage]
                    and isinstance(anchor.get("production_anchor"), str)
                    and len(anchor.get("sources", [])) == 2
                    and any(
                        source.get("path") == str(P1_EXECUTOR.resolve())
                        and source.get("sha256") == EXPECTED_P1_EXECUTOR_SHA
                        for source in anchor["sources"]
                    ),
                    f"P0 path code anchor changed for {target}/{path_stage}",
                )
        for leg in LEGS:
            data = section["legs"][leg]
            expected_ledger = [*LEVEL_ROWS, *TOP_LEVEL_ROWS, "residual"]
            actual_ledger = [row["dimensions"]["row"] for row in data["ledger"]]
            require(
                actual_ledger == expected_ledger,
                f"ledger roster changed for {target}/{leg}",
            )
            verdict = data["verdict"]
            require(
                verdict == summary_lookup[(target, leg)],
                f"verdict object is not mirrored for {target}/{leg}",
            )
            for row in data["ledger"]:
                name = row["dimensions"]["row"]
                if name in TOP_LEVEL_ROWS:
                    require(
                        row["additive_share"]["value"] == verdict["shares"][name],
                        f"additive share differs for {target}/{leg}/{name}",
                    )
            require(
                set(data["probes"]) == {"P0", "P1", "P2", "P5", "P6", "P7", "C1"},
                f"probe roster changed for {target}/{leg}",
            )
            c1_probe = data["probes"]["C1"]
            if not c1_probe["statistic_ids"]:
                require(
                    c1_probe["status"] == "NOT_APPLICABLE",
                    f"empty C1 probe is not inapplicable for {target}/{leg}",
                )
            p2_probe = data["probes"]["P2"]
            if p2_probe["completion_neutral_status_counts"]:
                require(
                    p2_authorization["authorized"]
                    and p2_probe["status"] == P2_NOT_VALIDATED_DISPOSITION,
                    f"P2 completion-neutral cells lack exact disposition for {target}/{leg}",
                )
            p6_probe = data["probes"]["P6"]
            if p6_probe["completion_neutral_status_counts"]:
                require(
                    p6_authorization["authorized"]
                    and p6_probe["status"] == P6_COMPLETE_NO_SURFACE,
                    f"P6 completion-neutral cells lack exact disposition for {target}/{leg}",
                )
            p6_rows = data["diagnostic_rows"]["P6 producer ledger"]
            require(
                p6_rows == sorted(p6_rows, key=p6_report_sort_key),
                f"P6 transition order changed for {target}/{leg}",
            )
            for row in p6_rows:
                expected_pointer = (
                    "/p6_bridge_closure_rows"
                    if row.get("diagnostic_only")
                    else "/merge_p6_nested"
                )
                require(
                    any(
                        source.get("path") == executor_binding["path"]
                        and source.get("sha256") == executor_binding["sha256"]
                        and source.get("pointer") == expected_pointer
                        for source in row.get("sources", [])
                    ),
                    f"P6 assembler provenance is absent: {row['id']}",
                )
                if row.get("diagnostic_only"):
                    continue
                if row["status"] == "UNAVAILABLE":
                    require(
                        any(
                            "unavailable_evidence" in source
                            for source in row.get("sources", [])
                        ),
                        f"P6 unavailable cell has no evidence: {row['id']}",
                    )
            for row in data["diagnostic_rows"]["P7 GQ identity"]:
                if row["family"] != "F4":
                    continue
                if finite_row(row) and isinstance(row.get("se"), (int, float)):
                    eligible_f4 += 1
                    require(
                        "holm_loading" in row,
                        f"eligible F4 row has no Holm result: {row['id']}",
                    )
                    loaded_f4 += 1
    require(eligible_f4 == loaded_f4, "F4 Holm mirror is incomplete")
    for name in (
        "targets",
        "cross_target_summary",
        "cross_rung_summary",
        "required_highlights",
        "reading_dispositions",
    ):
        validate_nested_source_lists(result[name], catalog_keys, name)
    p8_source = result["P8_ssi"]["source"]
    require(
        (p8_source.get("path"), p8_source.get("sha256")) in catalog_keys,
        "P8 source is absent from the catalog",
    )


def validate_markdown_mirror(
    markdown: str,
    result: dict[str, Any],
    targets: list[str],
) -> None:
    if result["status"] == "CONTROLS_FAILED":
        require(
            "## Per-target results" not in markdown, "failed controls rendered readings"
        )
        return
    require(
        markdown.count("Additive shares over Σ|c|:") == len(targets) * len(LEGS),
        "Markdown does not report every target-leg share vector",
    )
    require(
        markdown.count("##### P0 first-failure path census") == len(targets),
        "Markdown P0 census count differs from the target roster",
    )
    anchored_targets = sum(
        any(
            isinstance(source.get("path_code_anchors"), dict)
            for row in result["targets"][target]["P0"]
            for source in row.get("sources", [])
        )
        for target in targets
    )
    require(
        markdown.count("; predicate `_run_candidate_target:")
        == anchored_targets * len(P0_PATH_EXECUTOR_ANCHOR),
        "Markdown does not render one sealed code anchor per available P0 path",
    )
    for target in targets:
        require(
            markdown.count(f"\n### {target}\n") == 1,
            f"Markdown target section count changed for {target}",
        )
        for leg in LEGS:
            verdict = next(
                item
                for item in result["cross_target_summary"]
                if item["target"] == target and item["leg"] == leg
            )
            summary_prefix = (
                f"| {target} | {leg} | {verdict['dominant_row']} | "
                f"{fmt(verdict['dominant_share'])} |"
            )
            require(
                summary_prefix in markdown,
                f"Markdown cross-target row is absent for {target}/{leg}",
            )
    for item in result["source_catalog"]:
        require(
            f"`{item['sha256']}`" in markdown,
            f"Markdown source catalog omits {item['label']}",
        )


def render_stat_rows(
    rows: list[dict[str, Any]],
    lookup: dict[tuple[str, str], str],
    *,
    include_dimensions: bool = False,
    include_leg: bool = False,
) -> str:
    output: list[str] = []
    for row in rows:
        dims = row["dimensions"]
        label = dims["row"]
        if include_dimensions:
            suffix_parts = [
                value
                for value in (
                    dims["pattern"],
                    dims["group"],
                    dims["prior"],
                    dims["gq"],
                    dims["decile"],
                    dims["repeat"],
                    dims["fold"],
                    dims["variant"],
                )
                if value != NA
            ]
            if include_leg and dims["leg"] != NA:
                suffix_parts.insert(0, f"leg={dims['leg']}")
            suffix = "/".join(suffix_parts)
            if suffix:
                label += "/" + suffix
        loaded = row.get("holm_loading", {}).get("loaded", "NA")
        output.append(
            f"| {label} | {fmt(row['value'])} | {fmt(row['se'])} | {fmt(row['mcse'])} | {row['status']} | {fmt(loaded)} | {source_labels(row, lookup)} |"
        )
    return "\n".join(output)


def render_ledger_rows(
    rows: list[dict[str, Any]], lookup: dict[tuple[str, str], str]
) -> str:
    output: list[str] = []
    for row in rows:
        share = row.get("additive_share", {}).get("value", "NA")
        loaded = row.get("holm_loading", {}).get("loaded", "NA")
        output.append(
            f"| {row['dimensions']['row']} | {fmt(row['value'])} | {fmt(row['se'])} | "
            f"{fmt(row['mcse'])} | {fmt(share)} | {row['status']} | {fmt(loaded)} | "
            f"{source_labels(row, lookup)} |"
        )
    return "\n".join(output)


def render_p6_rows(
    rows: list[dict[str, Any]], lookup: dict[tuple[str, str], str]
) -> str:
    output: list[str] = []
    for row in rows:
        dims = row["dimensions"]
        suffix = "/".join(
            value
            for value in (
                dims["pattern"],
                dims["group"],
                dims["prior"],
                dims["gq"],
                dims["decile"],
                dims["repeat"],
                dims["fold"],
                dims["variant"],
            )
            if value != NA
        )
        label = dims["row"] + (f"/{suffix}" if suffix else "")
        evidence = next(
            (
                source["unavailable_evidence"]
                for source in row.get("sources", [])
                if "unavailable_evidence" in source
            ),
            "NA",
        )
        rendered_evidence = render_p6_structured_value(evidence)
        output.append(
            f"| {label} | {render_p6_structured_value(row['value'])} | "
            f"{render_p6_structured_value(row['se'])} | "
            f"{render_p6_structured_value(row['mcse'])} | {row['status']} | "
            f"{rendered_evidence} | "
            f"{source_labels(row, lookup)} |"
        )
    return "\n".join(output)


def render_p0_path_census(
    rows: list[dict[str, Any]], lookup: dict[tuple[str, str], str]
) -> str:
    path_row = next(
        (row for row in rows if row["dimensions"]["row"] == "P0_path_census"),
        None,
    )
    if path_row is None:
        return "Path census: `NOT_RUN_PRIORITY`."
    census = next(
        (
            source.get("path_census")
            for source in path_row.get("sources", [])
            if isinstance(source.get("path_census"), dict)
        ),
        None,
    )
    anchors = next(
        (
            source.get("path_code_anchors")
            for source in path_row.get("sources", [])
            if isinstance(source.get("path_code_anchors"), dict)
        ),
        None,
    )
    if not isinstance(census, dict):
        return f"Path census: `UNAVAILABLE`. Source: {source_labels(path_row, lookup)}."

    def render_anchor(stage: str) -> str:
        if not isinstance(anchors, dict) or not isinstance(anchors.get(stage), dict):
            return "UNAVAILABLE"
        anchor = anchors[stage]
        anchor_sources = copy.deepcopy(anchor.get("sources", []))
        if isinstance(anchor.get("operator_table_source"), dict):
            anchor_sources.append(copy.deepcopy(anchor["operator_table_source"]))
        labels = source_labels({"sources": anchor_sources}, lookup)
        return (
            f"{labels}; predicate `{anchor.get('predicate_anchor', 'NA')}`; "
            f"production `{anchor.get('production_anchor', 'NA')}`"
        )

    lines: list[str] = []
    stage_pass = census.get("stage_pass_rows", {})
    failure_rows = census.get("first_failure_rows", {})
    failure_masks = census.get("first_failure_masks", {})
    for stage in ("authorized", "null_before", "drawn", "finite_decode"):
        mask = failure_masks.get(stage, {})
        lines.append(
            f"| {stage} | {fmt(stage_pass.get(stage, 'NA'))} | "
            f"{fmt(failure_rows.get(stage, 'NA'))} | "
            f"{fmt(mask.get('sha256', 'NA'))} | {render_anchor(stage)} | "
            f"{source_labels(path_row, lookup)} |"
        )
    passed_mask = census.get("passed_mask", {})
    lines.append(
        f"| passed_all | {fmt(census.get('passed_rows', 'NA'))} | NA | "
        f"{fmt(passed_mask.get('sha256', 'NA'))} | {render_anchor('passed_all')} | "
        f"{source_labels(path_row, lookup)} |"
    )
    return "\n".join(lines)


def render_markdown(result: dict[str, Any]) -> str:
    catalog = result["source_catalog"]
    lookup = {(item["path"], item["sha256"]): item["label"] for item in catalog}
    adopted = result["controls"]["adopted"]
    control_lines = [
        f"| {name} | {item['status']} | "
        f"{json.dumps({key: value for key, value in item.items() if key != 'status'}, sort_keys=True)} | "
        f"{result['controls']['sources'][name]} |"
        for name, item in adopted.items()
    ]
    enumeration_lines = [
        f"| {item['target']} | {item['pattern']} | {item['G3_column']} | {item['split_count']} | {fmt(item['total_split_gain'])} | {result['controls']['sources']['enumeration']} |"
        for item in result["controls"]["G3_split_enumeration"]["rows"]
    ]
    c3_rows = [row for row in result["statistics"] if row["id"] in set(c3_stable_ids())]
    source_lines = [
        f"| {item['label']} | `{item['path']}` | `{item['sha256']}` |"
        for item in catalog
    ]
    seals = result["step0"]["seals"]
    selected = result["controls"]["A18_branch2"]["selected"]

    if result["status"] == "CONTROLS_FAILED":
        return f"""{result["status_line"]}

# QRF drift validation Phase 0 — v2.7/A18

## Control results

The previously adopted controls retain their PASS dispositions, but the fresh retargeted C3 failed. Readings were not opened and no target verdict is reported.

| Control | Status | Result details | Source |
| --- | --- | --- | --- |
{chr(10).join(control_lines)}
| C3 | {result["controls"]["C3"]["status"]} | {json.dumps(result["controls"]["C3"]["power"], sort_keys=True)} | {result["controls"]["sources"]["C3"]} |

### A18 G3 split enumeration — SEALED

The frozen enumeration selected `{selected["target"]} / {selected["pattern"]} / {selected["G3_column"]}` from 31 nonzero-split triples. Table SHA-256: `{EXPECTED_SPLIT_TABLE_SHA}`. Source: {result["controls"]["sources"]["enumeration"]}.

| Target | Pattern | G3 column | Splits | Total gain | Source |
| --- | --- | --- | ---: | ---: | --- |
{chr(10).join(enumeration_lines)}

### Retargeted C3 diagnostics

| Stable C3 row | Oracle error | SE | MCSE | Status | Loaded | Source |
| --- | ---: | ---: | ---: | --- | --- | --- |
{render_stat_rows(c3_rows, lookup, include_dimensions=True)}

## Source catalog

| Label | Path | SHA-256 |
| --- | --- | --- |
{chr(10).join(source_lines)}

Execution stopped at C3 under A18's numerical-control rule. All reading cells remain `NOT_RUN_CONTROLS_FAILED` in the authoritative 6,155-row JSON manifest mirror.
"""

    target_blocks: list[str] = []
    d0_markdown_label = lookup[(str(D0_MARKDOWN), EXPECTED_AUTHORITY[D0_MARKDOWN])]
    for target, section in result["targets"].items():
        leg_blocks: list[str] = []
        for leg in LEGS:
            data = section["legs"][leg]
            verdict = data["verdict"]
            attribution = data["attribution"]
            support = data["support_counts"]
            probe_lines = [
                f"| {name} | {item['status']}"
                f"{' — ' + item['reason'] if item.get('reason') else ''} | "
                f"{json.dumps(item['status_counts'], sort_keys=True)} | "
                f"{source_labels(item, lookup)} |"
                for name, item in data["probes"].items()
            ]
            attribution_text = (
                render_stat_rows(attribution, lookup, include_dimensions=True)
                if attribution
                else "| P2 | NA | NA | NA | NOT_RUN_PRIORITY | NA | NA |"
            )
            diagnostic_blocks: list[str] = []
            for title, rows in data["diagnostic_rows"].items():
                if title == "P6 producer ledger":
                    body = (
                        render_p6_rows(rows, lookup)
                        if rows
                        else f"| {title} | NA | NA | NA | NOT_RUN_PRIORITY | "
                        "no P6 artifact was supplied | NA |"
                    )
                    diagnostic_blocks.append(
                        f"""##### {title}

The exact sealed nested P6 payload, including per-pattern fit surfaces and clone/value/weight bridge diagnostics, is mirrored once under this target's JSON `P6_sealed_detail`.

| Row/dimensions | Value | SE | MCSE | Status | Unavailable evidence | Source |
| --- | ---: | ---: | ---: | --- | --- | --- |
{body}
"""
                    )
                    continue
                body = (
                    render_stat_rows(rows, lookup, include_dimensions=True)
                    if rows
                    else f"| {title} | NA | NA | NA | "
                    f"{data['probes']['C1']['status'] if title.startswith('C1 ') else 'NOT_RUN_PRIORITY'} | "
                    "NA | NA |"
                )
                diagnostic_blocks.append(
                    f"""##### {title}

| Row/dimensions | Value | SE | MCSE | Status | Loaded | Source |
| --- | ---: | ---: | ---: | --- | --- | --- |
{body}
"""
                )
            leg_blocks.append(
                f"""#### {leg}

Support is ASEC {support["asec"]} and ACS {support["acs"]} unique rows: `{support["status"]}`. Source: {source_labels(support, lookup)}.

| Ledger row | Value | SE | MCSE | Share | Status | Loaded | Source |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
{render_ledger_rows(data["ledger"], lookup)}

| Attribution row/dimensions | Value | SE | MCSE | Status | Loaded | Source |
| --- | ---: | ---: | ---: | --- | --- | --- |
{attribution_text}

{chr(10).join(diagnostic_blocks)}

| Probe | Disposition | Registered-cell status counts | Source |
| --- | --- | --- | --- |
{chr(10).join(probe_lines)}

Verdict: {verdict["verdict"]}. Additive shares over Σ|c|: {", ".join(f"`{name}` {fmt(verdict['shares'][name])}" for name in TOP_LEVEL_ROWS)}. Dominant row `{verdict["dominant_row"]}`, share {fmt(verdict["dominant_share"])}, cancellation index {fmt(verdict["cancellation_index"])}, defect class `{verdict["defect_class"]}`. Arm C / D / B-validation flags: `{verdict["arm_C_flag"]}` / `{verdict["arm_D_flag"]}` / `{verdict["arm_B_validation_flag"]}`. Source: {source_labels(verdict, lookup)}; exact inputs are enumerated in JSON `input_statistic_ids`.
"""
            )
        special = ""
        if (
            target == "pre_subsidy_care_expenses"
            and target in result["required_highlights"]
        ):
            highlight = result["required_highlights"][target]
            special = (
                f"The candidate replay cleared {highlight['candidate_25_cleared_positive_draws']} "
                f"positive adult-care draws, confirming and extending D0-4's "
                f"{highlight['baseline1pct_D0_4_cleared_positive_draws']} by "
                f"{highlight['additional_cleared_draws']} rows. Its positive-leg T5 is "
                f"{fmt(highlight['T5']['value'])} (SE {fmt(highlight['T5']['se'])}). "
                f"Sources: {source_labels(highlight, lookup)}; D0 catalog anchor "
                f"{d0_markdown_label}/D0-4.\n\n"
            )
        elif target == "weeks_unemployed" and target in result["required_highlights"]:
            highlight = result["required_highlights"][target]
            special = (
                f"The positive-leg gap D is {fmt(highlight['D']['value'])} "
                f"(SE {fmt(highlight['D']['se'])}). Of its signed decomposition, "
                f"B1 (producer path) is {fmt(highlight['B1']['value'])} "
                f"(SE {fmt(highlight['B1']['se'])}; "
                f"{fmt(highlight['B1']['share_of_signed_D'])} of D), T5 "
                f"(UC clearing) is {fmt(highlight['T5']['value'])} "
                f"(SE {fmt(highlight['T5']['se'])}; "
                f"{fmt(highlight['T5']['share_of_signed_D'])} of D), and T2 "
                f"(covariate shift) is {fmt(highlight['T2']['value'])} "
                f"(SE {fmt(highlight['T2']['se'])}; "
                f"{fmt(highlight['T2']['share_of_signed_D'])} of D). Source: "
                f"{source_labels(highlight, lookup)}.\n\n"
            )
        p0_rows = section["P0"]
        p0_text = (
            render_stat_rows(
                p0_rows,
                lookup,
                include_dimensions=True,
                include_leg=True,
            )
            if p0_rows
            else "| P0 | NA | NA | NA | NOT_RUN_PRIORITY | NA | NA |"
        )
        p0_path_census = render_p0_path_census(p0_rows, lookup)
        p0_block = f"""#### P0 provenance

| Row/dimensions | Value | SE | MCSE | Status | Loaded | Source |
| --- | ---: | ---: | ---: | --- | --- | --- |
{p0_text}

##### P0 first-failure path census

| Stage | Stage-pass rows | First-failure rows | First-failure mask SHA-256 | Code anchor | Source |
| --- | ---: | ---: | ---: | --- | --- |
{p0_path_census}

"""
        target_blocks.append(
            f"### {target}\n\n{special}{p0_block}" + "\n".join(leg_blocks)
        )

    cross_lines = [
        f"| {item['target']} | {item['leg']} | {item['dominant_row']} | {fmt(item['dominant_share'])} | {fmt(item['cancellation_index'])} | {item['verdict']} | {item['defect_class']} | {item['arm_C_flag']} / {item['arm_D_flag']} | {source_labels(item, lookup)} |"
        for item in result["cross_target_summary"]
    ]
    cross_rung_lines = [
        f"| {item['target']} | {fmt(item['candidate']['D']['value'])} ({fmt(item['candidate']['D']['se'])}) | {fmt(item['baseline']['D']['value'])} ({fmt(item['baseline']['D']['se'])}) | {fmt(item['D'])} | {fmt(item['top_level_rows'])} | {fmt(item['dominant_label'])} | {item['candidate_label']} | {item['baseline_label']} | {source_labels(item, lookup)} |"
        for item in result["cross_rung_summary"]
    ]
    cross_rung_row_lines = [
        f"| {item['target']} | {name} | {fmt(item['candidate']['top_level_rows'][name]['value'])} | {fmt(item['candidate']['top_level_rows'][name]['se'])} | {fmt(item['baseline']['top_level_rows'][name]['value'])} | {fmt(item['baseline']['top_level_rows'][name]['se'])} | {source_labels(item, lookup)} |"
        for item in result["cross_rung_summary"]
        for name in TOP_LEVEL_ROWS
    ]
    binding_text = result["a16_binding_appendix"]["text"]
    disposition_lines = [
        f"{name}: `{item['status']}` — {item['reason']} Source: {source_labels(item, lookup)}."
        for name, item in result["reading_dispositions"].items()
    ]
    return f"""{result["status_line"]}

# QRF drift validation Phase 0 — v2.7/A18

## Control results

All adopted controls and the fresh C3 pass. K is {EXPECTED_K}, Šidák z* is {fmt(EXPECTED_Z)}, and the ordered roster SHA-256 is `{EXPECTED_K_DIGEST}`. The historical D0 K=214 is void. Roster source: {result["controls"]["sources"]["adoption"]}.

| Control | Status | Result details | Source |
| --- | --- | --- | --- |
{chr(10).join(control_lines)}

### A18 G3 split enumeration — SEALED

The frozen-gate enumeration has 31 nonzero-split triples; its canonical table SHA-256 is `{EXPECTED_SPLIT_TABLE_SHA}`. Every numeric table cell below comes from source `{result["controls"]["sources"]["enumeration"]}`.

| Target | Pattern | G3 column | Splits | Total gain | Source |
| --- | --- | --- | ---: | ---: | --- |
{chr(10).join(enumeration_lines)}

### Retargeted C3 — {result["controls"]["C3"]["status"]}

A18 mechanically selected `{selected["target"]} / {selected["pattern"]} / {selected["G3_column"]}`: {selected["split_count"]} splits and total gain {fmt(selected["total_split_gain"])}. The old manifest target in all three IDs remains `child_support_received`; the evaluated context is attached to every row source.

| Stable C3 row | Oracle error | SE | MCSE | Status | Loaded | Source |
| --- | ---: | ---: | ---: | --- | --- | --- |
{render_stat_rows(c3_rows, lookup, include_dimensions=True)}

The exact target-group oracle is {fmt(result["controls"]["C3"]["power"].get("effect"))}; the strict power threshold is {fmt(result["controls"]["C3"]["power"].get("threshold_5_z_mcse"))}. Source: {result["controls"]["sources"]["C3"]} `/control/power`.

## Sealed Step-0 deliverables

The operator table, JSON Schema, ordered manifest, empty adjudication table, and default appendix remain unchanged. The manifest and final statistics arrays each contain {EXPECTED_MANIFEST_COUNT} unique IDs with zero missing and zero extras.

| Object | SHA-256 | Source |
| --- | --- | --- |
| Operator table | `{seals["operator_table_sha256"]}` | {result["controls"]["sources"]["base"]} |
| JSON Schema | `{seals["json_schema_sha256"]}` | {result["controls"]["sources"]["base"]} |
| Required-ID manifest | `{seals["required_id_manifest_sha256"]}` | {result["controls"]["sources"]["base"]} |
| Empty adjudication table | `{seals["adjudication_table_sha256"]}` | {result["controls"]["sources"]["base"]} |
| Default appendix | `{seals["default_appendix_sha256"]}` | {result["controls"]["sources"]["base"]} |
| Composite | `{seals["composite_sha256"]}` | {result["controls"]["sources"]["base"]} |

## Source catalog

Every numeric cell above and below carries a Source label. Each label resolves here to a full path and SHA-256; JSON sources also retain exact pointers and secondary digests.

| Label | Path | SHA-256 |
| --- | --- | --- |
{chr(10).join(source_lines)}

## Reading dispositions

{chr(10).join(disposition_lines) if disposition_lines else "No global reading qualification was required."}

## Per-target results

{chr(10).join(target_blocks)}

## Cross-target summary

| Target | Leg | Dominant row | Share | Cancellation | Verdict | Defect class | C/D gating | Source |
| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |
{chr(10).join(cross_lines)}

## Cross-rung consistency

| Target | Candidate D (SE) | Baseline D (SE) | D tension | Top-level-row tension | Label tension | Candidate label | Baseline label | Source |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- |
{chr(10).join(cross_rung_lines)}

| Target | Top-level row | Candidate value | Candidate SE | Baseline value | Baseline SE | Source |
| --- | --- | ---: | ---: | ---: | ---: | --- |
{chr(10).join(cross_rung_row_lines)}

Tension is diagnostic only and never gates.

## P8 — SSI dependency note

{result["P8_ssi"]["note"]} Status: `{result["P8_ssi"]["status"]}`. Source: `{result["P8_ssi"]["source"]["path"]}`, SHA-256 `{result["P8_ssi"]["source"]["sha256"]}`, D0-7.

## Explicitly unreached or unavailable work

{"; ".join(result["partial_reasons"]) if result["partial_reasons"] else "None."}

## Appendix A — A16 binding texts incorporated verbatim

Source: `{BINDING}`, SHA-256 `{EXPECTED_AUTHORITY[BINDING]}`.

```text
{binding_text}
```
"""


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(payload)
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    authority = verify_authorities()
    base, sealed_step0, enumeration, adoption, c3, core_sources = verify_a18_inputs(
        args.base_json, args.enumeration, args.adoption, args.c3
    )
    manifest = sealed_step0["required_id_manifest"]
    manifest_by_id = {item["id"]: item for item in manifest}
    selection = adoption["branch2"]["selected"]
    c3_control = c3.get("control", {})
    c3_pass = (
        c3.get("status") == "PASS"
        and c3_control.get("pass") is True
        and c3_control.get("power", {}).get("pass") is True
    )
    fallback_status = "NOT_RUN_PRIORITY" if c3_pass else "NOT_RUN_CONTROLS_FAILED"
    fallback_source = source_ref(
        DESIGN,
        authority[str(DESIGN)],
        "/Amendment-v2.4/A8" if c3_pass else "/Amendment-v2.7/A18",
        reason="A8 bounded priority" if c3_pass else "retargeted C3 numerical failure",
    )
    statistics, by_id = fresh_statistics(manifest, fallback_status, fallback_source)
    locked = adopt_base_statistics(base, manifest_by_id, by_id)
    c3_pass = merge_c3(c3, core_sources["C3"], selection, manifest_by_id, by_id, locked)

    reading_payloads: list[tuple[dict[str, Any], dict[str, Any]]] = []
    p1_artifact: tuple[dict[str, Any], dict[str, Any]] | None = None
    readings_barrier_artifact: tuple[dict[str, Any], dict[str, Any]] | None = None
    classifications: dict[str, Any] = {}
    if c3_pass:
        if args.p1:
            p1_artifact = merge_p1_artifact(
                args.p1,
                manifest,
                manifest_by_id,
                by_id,
                locked,
                sealed_step0["operator_table"],
                core_sources["base"],
            )
            reading_payloads.append(p1_artifact)
        baseline_artifact = merge_baseline_crossrung_artifact(
            args.baseline_crossrung,
            manifest,
            manifest_by_id,
            by_id,
            locked,
        )
        reading_payloads.append(baseline_artifact)
        for path in [*args.p2, *args.reading_artifact]:
            reading_payloads.append(
                merge_statistics_artifact(path, manifest_by_id, by_id, locked)
            )
        reading_payloads.extend(
            merge_p5_artifacts(args.p5, manifest_by_id, by_id, locked)
        )
        if args.readings_barrier:
            readings_barrier_artifact = merge_readings_barrier(
                args.readings_barrier,
                manifest,
                manifest_by_id,
                by_id,
                locked,
            )
            verify_barrier_artifact_bindings(
                readings_barrier_artifact[0], reading_payloads
            )
            reading_payloads.append(readings_barrier_artifact)
        require(
            not args.c1 or readings_barrier_artifact is not None,
            "C1 artifacts cannot be assembled without --readings-barrier",
        )
        for path in args.c1:
            reading_payloads.append(
                merge_statistics_artifact(
                    path,
                    manifest_by_id,
                    by_id,
                    locked,
                    readings_barrier_artifact[1]
                    if readings_barrier_artifact is not None
                    else None,
                )
            )
        for payload, _source in reading_payloads:
            parent_classifications = payload.get("parent_classifications")
            require(
                parent_classifications is None or parent_classifications == {},
                "reading artifact attempts to override sealed empty owner adjudication",
            )

    d0 = load_json(D0_JSON)
    targets = list(d0["scope"]["targets"])
    p8 = apply_p8(manifest, manifest_by_id, by_id, locked, authority, c3_pass)
    assembly_source = executor_source("/verdict_for_leg")
    assembly_source["design_authority"] = source_ref(
        DESIGN, authority[str(DESIGN)], "/Amendment-v2.5/A16-findings-45-52"
    )
    assembly_source["empty_adjudication_table_sha256"] = EXPECTED_STEP0_SEALS[
        "adjudication_table_sha256"
    ]
    verdict_source = copy.deepcopy(assembly_source)
    verdicts = apply_verdicts(
        statistics,
        manifest_by_id,
        by_id,
        locked,
        targets,
        verdict_source,
        classifications,
    )
    cross_rung = apply_cross_rung(
        manifest,
        manifest_by_id,
        by_id,
        locked,
        verdicts,
        {
            **executor_source("/apply_cross_rung"),
            "design_authority": source_ref(
                DESIGN,
                authority[str(DESIGN)],
                "/Amendment-v2.5/A16-finding-54",
            ),
        },
    )

    statistics.sort(key=lambda item: item["id"])
    manifest_ids = {item["id"] for item in manifest}
    statistic_ids = [item["id"] for item in statistics]
    require(
        len(statistic_ids) == len(set(statistic_ids)) == EXPECTED_MANIFEST_COUNT,
        "final statistics have duplicate IDs",
    )
    require(
        set(statistic_ids) == manifest_ids, "final statistics have missing or extra IDs"
    )
    for row in statistics:
        require(
            static_fields_match(row, manifest_by_id[row["id"]]),
            f"static field changed for {row['id']}",
        )
        require(
            row["status"] in manifest_by_id[row["id"]]["allowed_statuses"],
            f"invalid status for {row['id']}",
        )

    p2_not_validated_complete = barrier_disposes_unvalidated_p2(
        readings_barrier_artifact
    )
    p6_no_surface_complete = barrier_completes_evidenced_p6(readings_barrier_artifact)
    incomplete = incomplete_statistics(
        statistics,
        p2_not_validated_complete=p2_not_validated_complete,
        p6_no_surface_complete=p6_no_surface_complete,
    )
    partial_reasons = [
        f"{status}/{probe}: {count} registered cells"
        for (status, probe), count in sorted(incomplete.items())
    ]
    final_status = phase0_run_status(c3_pass, incomplete)
    if final_status == "CONTROLS_FAILED":
        status_line = "STATUS: CONTROLS_FAILED — retargeted C3 failed recovery or power; readings NOT_RUN_CONTROLS_FAILED"
    elif final_status == "PARTIAL":
        status_line = "STATUS: PARTIAL — " + "; ".join(partial_reasons)
    else:
        status_line = (
            "STATUS: COMPLETE — all controls and registered readings have a disposition"
        )

    fixed_sources = [
        *core_sources.values(),
        executor_source(),
        source_ref(DESIGN, authority[str(DESIGN)]),
        source_ref(D0_JSON, authority[str(D0_JSON)]),
        source_ref(D0_MARKDOWN, authority[str(D0_MARKDOWN)]),
        source_ref(BINDING, authority[str(BINDING)]),
        *(source for _payload, source in reading_payloads),
    ]
    catalog, source_lookup = source_catalog(statistics, fixed_sources)

    def source_label(source: dict[str, Any]) -> str:
        return source_lookup[(source["path"], source["sha256"])]

    adopted_controls = copy.deepcopy(adoption["controls"]["adopted_controls"])
    control_sources = {
        name: source_label(core_sources["adoption"]) for name in adopted_controls
    }
    control_sources.update(
        base=source_label(core_sources["base"]),
        adoption=source_label(core_sources["adoption"]),
        enumeration=source_label(core_sources["enumeration"]),
        C3=source_label(core_sources["C3"]),
    )
    target_sections = (
        build_target_sections(
            statistics,
            targets,
            verdicts,
            p1_artifact,
            p2_not_validated_complete=p2_not_validated_complete,
            p6_no_surface_complete=p6_no_surface_complete,
            completion_barrier_source=(
                readings_barrier_artifact[1]
                if readings_barrier_artifact is not None
                else None
            ),
        )
        if c3_pass
        else {}
    )
    support = support_by_target(
        d0,
        targets,
        source_ref(D0_JSON, authority[str(D0_JSON)], "/D0-1"),
    )
    if c3_pass:
        for target in targets:
            for leg in LEGS:
                target_sections[target]["legs"][leg]["support_counts"] = support[
                    target
                ][leg]
    highlights = build_required_highlights(
        p1_artifact,
        source_ref(D0_JSON, authority[str(D0_JSON)]),
    )
    reading_dispositions = global_reading_dispositions(reading_payloads)
    completion_authorization_sources = [
        *(
            [copy.deepcopy(readings_barrier_artifact[1])]
            if readings_barrier_artifact is not None
            else []
        ),
        executor_source("/incomplete_statistics"),
    ]

    result = copy.deepcopy(base)
    result.update(
        execution_version=EXECUTION_VERSION,
        status=final_status,
        status_line=status_line,
        failed_controls=[] if c3_pass else ["C3"],
        failed_control_details=[]
        if c3_pass
        else [
            {
                "control": "C3",
                "status": "FAIL",
                "producer_artifact_status": c3.get("status", "UNKNOWN"),
                "producer_control_status": c3_control.get("status", "UNKNOWN"),
                "power": copy.deepcopy(c3_control.get("power", {})),
            }
        ],
        authority={
            "design": source_ref(DESIGN, authority[str(DESIGN)], commit=A18_COMMIT),
            "d0_json": source_ref(D0_JSON, authority[str(D0_JSON)]),
            "d0_markdown": source_ref(D0_MARKDOWN, authority[str(D0_MARKDOWN)]),
            "a16_binding_texts": source_ref(BINDING, authority[str(BINDING)]),
            "phase0_finalizer": executor_source(),
        },
        controls={
            "status": "PASS" if c3_pass else "FAIL",
            "K": EXPECTED_K,
            "sidak_z": EXPECTED_Z,
            "roster_sha256": EXPECTED_K_DIGEST,
            "adopted": adopted_controls,
            "A18_branch2": copy.deepcopy(adoption["branch2"]),
            "G3_split_enumeration": {
                **copy.deepcopy(enumeration["sealed_split_table"]),
                "source": copy.deepcopy(core_sources["enumeration"]),
            },
            "C3": {
                "status": "PASS" if c3_pass else "FAIL",
                "control": {
                    key: copy.deepcopy(value)
                    for key, value in c3_control.items()
                    if key != "replicate_arrays"
                },
                "power": copy.deepcopy(c3_control.get("power", {})),
                "retargeted_context": copy.deepcopy(selection),
                "stable_manifest_ids": c3_stable_ids(),
            },
            "sources": control_sources,
        },
        source_catalog=catalog,
        reading_artifacts=[
            {
                "artifact_kind": payload.get("artifact_kind"),
                "status": payload.get("status"),
                **source,
            }
            for payload, source in reading_payloads
        ],
        statistics=statistics,
        targets=target_sections,
        cross_target_summary=verdicts if c3_pass else [],
        cross_rung_summary=cross_rung if c3_pass else [],
        P8_ssi=p8,
        required_highlights=highlights if c3_pass else {},
        reading_dispositions=reading_dispositions if c3_pass else {},
        reading_completion_authorizations={
            "P2_evidenced_unavailable": {
                "authorized": p2_not_validated_complete,
                "required_barrier_disposition": P2_NOT_VALIDATED_DISPOSITION,
                "evidenced_cell_count": sum(
                    intentional_p2_unavailable(row) for row in statistics
                ),
                "sources": copy.deepcopy(completion_authorization_sources),
            },
            "P6_evidenced_unavailable": {
                "authorized": p6_no_surface_complete,
                "required_barrier_disposition": P6_COMPLETE_NO_SURFACE,
                "required_sealed_p1_disposition": P6_SEALED_DISPOSITION,
                "evidenced_cell_count": sum(
                    intentional_p6_unavailable(row) for row in statistics
                ),
                "sources": copy.deepcopy(completion_authorization_sources),
            },
        },
        partial_reasons=partial_reasons,
        partial_breakdown={
            status: {
                probe: count
                for (cell_status, probe), count in sorted(incomplete.items())
                if cell_status == status
            }
            for status in sorted({cell_status for cell_status, _probe in incomplete})
        },
        stop={
            "stage": "C3"
            if not c3_pass
            else "A8_PRIORITY"
            if final_status == "PARTIAL"
            else "NONE",
            "readings_opened": c3_pass,
            "reason": "numerical C3 failure"
            if not c3_pass
            else "A8 bounded priority"
            if final_status == "PARTIAL"
            else "none",
        },
        execution_discrepancies=[
            {
                "sealed_ids": c3_stable_ids(),
                "retargeted_context": selection,
                "disposition": "stable C3 IDs retained; evaluated A18 context attached as metadata",
            },
            {
                "historical": "D0 K=214",
                "operative": f"K={EXPECTED_K}, z*={EXPECTED_Z}",
                "roster_sha256": EXPECTED_K_DIGEST,
            },
        ],
        a16_binding_appendix={
            "path": str(BINDING),
            "sha256": authority[str(BINDING)],
            "text": BINDING.read_text(),
        },
        validation={
            "manifest_count": EXPECTED_MANIFEST_COUNT,
            "statistics_count": EXPECTED_MANIFEST_COUNT,
            "duplicate_manifest_ids": 0,
            "duplicate_statistic_ids": 0,
            "missing_ids": 0,
            "extra_ids": 0,
            "step0_seals_unchanged": True,
            "schema_status": "PENDING_CANONICAL_HASH",
            "report_contract_status": "PENDING",
            "markdown_mirror_status": "PENDING",
            "sources": [executor_source("/validate_report_contract")],
        },
    )
    require(
        canonical_bytes(result["step0"]) == canonical_bytes(sealed_step0),
        "Step 0 mutated during assembly",
    )
    result["canonical_sha256"] = "0" * 64
    Draft202012Validator(result["step0"]["json_schema"]).validate(result)
    result["validation"]["schema_status"] = "PASS"
    validate_report_contract(result, targets, p1_artifact)
    result["validation"]["report_contract_status"] = "PASS"
    markdown = render_markdown(result)
    validate_markdown_mirror(markdown, result, targets)
    result["validation"]["markdown_mirror_status"] = "PASS"
    scope = dict(result)
    scope.pop("canonical_sha256")
    result["canonical_sha256"] = digest_object(scope)
    Draft202012Validator(result["step0"]["json_schema"]).validate(result)

    markdown = render_markdown(result)
    validate_markdown_mirror(markdown, result, targets)
    atomic_write(args.json_output, canonical_bytes(result) + b"\n")
    atomic_write(args.markdown_output, markdown.encode())
    print(
        json.dumps(
            {
                "status": final_status,
                "canonical_sha256": result["canonical_sha256"],
                "manifest_count": EXPECTED_MANIFEST_COUNT,
                "statistics_count": EXPECTED_MANIFEST_COUNT,
                "partial_reasons": partial_reasons,
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
