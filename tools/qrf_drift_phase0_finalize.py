"""Finalize the v2.6/A17 QRF-drift Phase-0 report.

The finalizer is deliberately a pure assembly/validation lane.  It consumes
the sealed Step-0 report plus the independently produced A17 setup, C4, and
C2/C3 artifacts.  It never recomputes a control.  If a gated control fails,
all later manifest cells are made explicit as ``NOT_RUN_CONTROLS_FAILED``.
Optional reading results can be merged only when every control passes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments"
DEFAULT_BASE = EXP / "qrf_drift_validation_phase0.json"
DEFAULT_JSON = EXP / "qrf_drift_validation_phase0.json"
DEFAULT_MARKDOWN = EXP / "qrf_drift_validation_phase0.md"
DEFAULT_SETUP = Path("/private/tmp/qrf_phase0_a17_setup.json")
DEFAULT_C4 = Path("/private/tmp/qrf_phase0_a17_c4.json")
DEFAULT_C2C3 = Path("/private/tmp/qrf_phase0_a17_c2c3.json")

DESIGN = EXP / "qrf_drift_validation_design.md"
D0_JSON = EXP / "qrf_drift_validation_d0.json"
D0_MARKDOWN = EXP / "qrf_drift_validation_d0.md"
BINDING = EXP / "qrf_drift_validation_a16_binding_texts.md"
C0A = Path("/private/tmp/qrf_phase0_c0a.json")
C0B = Path("/private/tmp/qrf_phase0_v22_c0b.json")
C5 = Path("/private/tmp/qrf_phase0_v22_c5.json")

EXECUTION_VERSION = "v2.6/A17"
DESIGN_COMMIT = "1c315579ea1702991172fe3eb37dc084ece0ae98"
EXPECTED_AUTHORITY = {
    DESIGN: "a91d19cc6a3c7e55db28159189ce0ccc76ddbf972247a20cc6eabbb59d5719bc",
    D0_JSON: "fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8",
    D0_MARKDOWN: "c4f3a9c56426025426e56428e9bce697a6cc6112f175be86ef9ef139bf79b601",
    BINDING: "7e288bce7496e1e7f41e33f078be2043673ca54ff31182caf2ce92eab68a81c1",
}
EXPECTED_ADOPTED = {
    C0A: "d22c2acab499adb9f0fa5e2a55412a904f68757680ca2d362518d35160daf962",
    C0B: "1c7bfd65660b14068c4bc96fae4b8d270cb447ea8fbbe42c8ef982c5f1dbf542",
    C5: "7f00827190276615806e26d5c76eda7c413c49640fb843988770f58056dc584c",
}
EXPECTED_STEP0_SEALS = {
    "operator_table_sha256": "447f7c9f00220440b7ad3825223f01fec8bed28e16e6eda2a851afdda64a6e23",
    "json_schema_sha256": "1a951262e9f9420fa8bc4462d2b53f697ab428ddcdb8e820021be80983fe54d7",
    "required_id_manifest_sha256": "c2ba7add0445a91715c491d78b83677844f90767414bdd32a7511fff1d676ec9",
    "adjudication_table_sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "default_appendix_sha256": "4b58de099a1edcc11bdfbfef21ec8c06d835bca67ca9c80d55a4346beae32332",
    "composite_sha256": "2cabf69c9d91801e16686a46cf904bc346c0e009162ad2bb91eda996da73e9b8",
}
EXPECTED_MANIFEST_COUNT = 6155
EXPECTED_K = 122
EXPECTED_K_DIGEST = "348386d9675172b65550ef7cb157fb1387e1d45331f61253aefe40dbe8f2bbc9"
EXPECTED_Z = 3.526967430023352

DIMENSION_ORDER = (
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
)
NA = "_"
LEGS = ("positive", "negative")
LEDGER_ROWS = ("L0", "B1", "B2", "T1", "T2", "T3", "T4", "T5", "residual")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-json", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--setup", type=Path, default=DEFAULT_SETUP)
    parser.add_argument("--c4", type=Path, default=DEFAULT_C4)
    parser.add_argument("--c2c3", type=Path, default=DEFAULT_C2C3)
    parser.add_argument(
        "--readings",
        type=Path,
        help="optional post-control reading artifact using sealed statistic IDs",
    )
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value: float) -> str:
    """Return the finite binary64 spelling used by sealed Step 0."""

    if not math.isfinite(value):
        raise ValueError("nonfinite numbers must be encoded as strings")
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
                sign = "-"
                coefficient = coefficient[1:]
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
        if raw.endswith(".0"):
            raw = raw[:-2]
        return raw
    if "e" not in raw:
        return raw[:-2] if raw.endswith(".0") else raw
    coefficient, exponent_text = raw.split("e")
    exponent = int(exponent_text)
    if coefficient.endswith(".0"):
        coefficient = coefficient[:-2]
    return f"{coefficient}e{'+' if exponent >= 0 else ''}{exponent}"


def canonical_bytes(value: Any) -> bytes:
    """Serialize using the canonical encoder sealed in the Phase-0 schema."""

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
            return "{" + ",".join(
                encode(key) + ":" + encode(item[key]) for key in sorted(item)
            ) + "}"
        raise TypeError(f"unsupported canonical JSON type: {type(item)!r}")

    return encode(value).encode("utf-8")


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def source_ref(path: Path | str, digest: str, pointer: str | None = None, **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "sha256": digest}
    if pointer is not None:
        result["pointer"] = pointer
    result.update(extra)
    return result


def verify_file(path: Path, expected: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"digest mismatch for {path}: expected {expected}, got {actual}")
    return actual


def verify_canonical_artifact(
    path: Path, value: dict[str, Any], expected_kind: str
) -> str:
    if value.get("artifact_kind") != expected_kind:
        raise ValueError(
            f"artifact kind mismatch for {path}: {value.get('artifact_kind')!r}"
        )
    recorded = value.get("canonical_sha256")
    if not isinstance(recorded, str) or len(recorded) != 64:
        raise ValueError(f"missing canonical_sha256 in {path}")
    scope = dict(value)
    scope.pop("canonical_sha256")
    actual = digest_object(scope)
    if actual != recorded:
        raise ValueError(
            f"canonical digest mismatch for {path}: recorded {recorded}, got {actual}"
        )
    return sha256_file(path)


def verify_step0(base: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    step0 = base.get("step0")
    if not isinstance(step0, dict):
        raise ValueError("base report has no Step-0 object")
    seals = step0.get("seals")
    if seals != EXPECTED_STEP0_SEALS:
        raise ValueError("recorded Step-0 seals do not equal the ratified sealed bundle")
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
    if actual != EXPECTED_STEP0_SEALS:
        raise ValueError(f"Step-0 object digest mismatch: {actual}")
    if step0.get("sealed_before_fresh_statistics") is not True:
        raise ValueError("Step 0 was not recorded as sealed before fresh statistics")
    manifest = step0["required_id_manifest"]
    if len(manifest) != EXPECTED_MANIFEST_COUNT:
        raise ValueError(f"required-ID manifest length is {len(manifest)}, not 6155")
    manifest_by_id = {item["id"]: item for item in manifest}
    if len(manifest_by_id) != len(manifest):
        raise ValueError("duplicate IDs in sealed manifest")

    current = base.get("statistics")
    if not isinstance(current, list):
        raise ValueError("base report has no statistics array")
    current_by_id = {item["id"]: item for item in current}
    if len(current_by_id) != len(current) or set(current_by_id) != set(manifest_by_id):
        raise ValueError("base statistic IDs are not exactly the sealed manifest IDs")
    for identifier, spec in manifest_by_id.items():
        row = current_by_id[identifier]
        for field in ("id", "dimensions", "record_type", "family", "gated"):
            if row.get(field) != spec.get(field):
                raise ValueError(f"static field {field} changed for {identifier}")
    return manifest, step0


def roster(manifest: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for entry in manifest:
        dims = entry["dimensions"]
        if dims["row"] == "C0b_E2" and dims["variant"] == "repeated_draw":
            ids.append(entry["id"])
        elif dims["row"] == "C4_null_total":
            ids.append(entry["id"])
        elif dims["row"] in {"C2_oracle_error", "C3_oracle_error"}:
            ids.append(entry["id"])
    if len(ids) != EXPECTED_K or digest_object(ids) != EXPECTED_K_DIGEST:
        raise ValueError("ratified K=122 roster does not match the sealed manifest")
    return ids


def fresh_statistics(
    manifest: list[dict[str, Any]], fallback_status: str, fallback_source: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for item in manifest:
        rows.append(
            {
                "id": item["id"],
                "dimensions": copy.deepcopy(item["dimensions"]),
                "record_type": item["record_type"],
                "value": "NA",
                "se": "NA",
                "mcse": "NA",
                "family": item["family"],
                "gated": item["gated"],
                "status": fallback_status,
                "default_resolved": False,
                "sources": [copy.deepcopy(fallback_source)],
            }
        )
    return rows, {item["id"]: item for item in rows}


def dimension_index(rows: list[dict[str, Any]]) -> dict[tuple[str, ...], dict[str, Any]]:
    result: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(row["dimensions"][name] for name in DIMENSION_ORDER)
        if key in result:
            raise ValueError(f"duplicate dimension key {key}")
        result[key] = row
    return result


def get_stat(index: dict[tuple[str, ...], dict[str, Any]], **values: str) -> dict[str, Any]:
    dimensions = {name: NA for name in DIMENSION_ORDER}
    dimensions.update(values)
    key = tuple(dimensions[name] for name in DIMENSION_ORDER)
    try:
        return index[key]
    except KeyError as error:
        raise ValueError(f"sealed statistic dimension not found: {dimensions}") from error


def set_stat(
    row: dict[str, Any],
    value: Any,
    status: str,
    sources: list[dict[str, Any]],
    *,
    se: Any = "NA",
    mcse: Any = "NA",
    default_resolved: bool = False,
) -> None:
    row.update(
        {
            "value": value,
            "se": se,
            "mcse": mcse,
            "status": status,
            "default_resolved": default_resolved,
            "sources": copy.deepcopy(sources),
        }
    )


def power_pass(control: dict[str, Any]) -> bool:
    power = control.get("power")
    if isinstance(power, bool):
        return power
    if isinstance(power, dict):
        if isinstance(power.get("pass"), bool):
            return power["pass"]
        return power.get("status") == "PASS"
    if isinstance(control.get("power_pass"), bool):
        return control["power_pass"]
    raise ValueError(f"control {control.get('control')} has no power pass boolean")


def compact_control(control: dict[str, Any]) -> dict[str, Any]:
    omitted = {"replicate_arrays", "paired_same_i_j_semantic_audit"}
    return {key: copy.deepcopy(value) for key, value in control.items() if key not in omitted}


def support_by_target(d0: dict[str, Any], targets: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    d0_digest = EXPECTED_AUTHORITY[D0_JSON]
    for target in targets:
        result[target] = {}
        for leg in LEGS:
            rung = d0["D0-1"]["rungs"]["candidate-25"][target]
            asec = rung["asec"]["legs"][leg][
                "unique_clone_deduplicated_source_rows_all_clones"
            ]
            acs = rung["acs"]["legs"][leg][
                "unique_clone_deduplicated_source_rows_all_clones"
            ]
            fit_count: int | None = None
            if target == "self_employment_income_last_year" and leg == "negative":
                fit_count = 48
                status = "INSUFFICIENT_SUPPORT_NO_VERDICT"
                reason = "A7 binds 48 donor-fit carriers, below the 50-unique floor"
            elif min(asec, acs) < 50:
                status = "INSUFFICIENT_SUPPORT_NO_VERDICT"
                reason = "D0-1 clone-deduplicated source count is below 50"
            else:
                status = "SUPPORTED"
                reason = "both D0-1 clone-deduplicated source counts meet 50"
            result[target][leg] = {
                "status": status,
                "asec_unique_sources": asec,
                "acs_unique_sources": acs,
                "bound_donor_fit_count": fit_count,
                "reason": reason,
                "source": source_ref(
                    D0_JSON,
                    d0_digest,
                    f"/D0-1/rungs/candidate-25/{target}",
                ),
            }
    return result


def deep_merge(base: dict[str, Any], addition: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in addition.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def exact(value: Any) -> str:
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return repr(value)
    if value is None:
        return "NA"
    return str(value)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(payload)
    temporary.replace(path)


def build_default_sections(
    targets: list[str],
    support: dict[str, Any],
    setup_lookups: dict[str, dict[str, dict[str, Any]]],
    fallback_status: str,
    fallback_source: dict[str, Any],
    setup_source: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    target_sections: dict[str, Any] = {}
    cross: list[dict[str, Any]] = []
    for target in targets:
        p0 = {
            "A17-15(i)": {
                **copy.deepcopy(setup_lookups["A17-15(i)"][target]),
                "source": setup_source,
            },
            "A16-15(ii)": {
                **copy.deepcopy(setup_lookups["A16-15(ii)"][target]),
                "source": setup_source,
            },
            "A17-15(iii)": {
                **copy.deepcopy(setup_lookups["A17-15(iii)"][target]),
                "source": setup_source,
            },
        }
        legs: dict[str, Any] = {}
        for leg in LEGS:
            ledger = [
                {
                    "row": row,
                    "value": "NA",
                    "se": "NA",
                    "status": fallback_status,
                    "source": fallback_source,
                }
                for row in LEDGER_ROWS
            ]
            verdict = {
                "dominant_row": "NA",
                "share": "NA",
                "cancellation_index": "NA",
                "verdict": fallback_status,
                "defect_class": "NA",
                "arm_C_flag": fallback_status,
                "arm_D_flag": fallback_status,
                "arm_B_validation_flag": fallback_status,
                "support": support[target][leg]["status"],
                "source": fallback_source,
            }
            legs[leg] = {
                "support": support[target][leg],
                "ledger": ledger,
                "attribution": [
                    {
                        "row": "P2 Shapley / per-prior / marginal audit",
                        "value": "NA",
                        "se": "NA",
                        "status": fallback_status,
                        "source": fallback_source,
                    }
                ],
                "probes": {
                    probe: {"status": fallback_status, "source": fallback_source}
                    for probe in ("P0_report", "P1", "P2", "P5", "P6", "P7", "C1")
                },
                "verdict": verdict,
            }
            cross.append({"target": target, "leg": leg, **copy.deepcopy(verdict)})
        target_sections[target] = {"P0_setup": p0, "legs": legs}
    return target_sections, cross


def render_markdown(result: dict[str, Any], evidence: dict[str, Any]) -> str:
    setup = evidence["setup"]
    c0a = evidence["c0a"]
    c0b = evidence["c0b"]
    c5 = evidence["c5"]
    c4 = evidence["c4"]
    c2c3 = evidence["c2c3"]
    digests = evidence["digests"]
    readings_note = ""
    if evidence["paths"].get("readings") is not None:
        readings_note = (
            f" Later reading values cite `{evidence['paths']['readings']}`, "
            f"SHA-256 `{digests['readings']}` and exact JSON pointers."
        )
    manifest = result["step0"]["required_id_manifest"]
    seals = result["step0"]["seals"]

    c0a_lines = []
    for item in c0a["rows"]:
        c0a_lines.append(
            f"| {item['rung']} | {item['target']} | {item['leg']} | "
            f"{exact(item['asec']['incidence'])} | {exact(item['acs']['incidence'])} | "
            f"{'PASS' if item['pass'] else 'FAIL'} |"
        )
    e4_lines = [
        f"| {item['target']} | {item['pattern']} | {'PASS' if item['e4_pattern_pass'] else 'FAIL'} |"
        for item in c0b["patterns"]
    ]
    e2_lines = []
    for item in c0b["per_class_controls"]:
        repeated = abs(item["mc_mean_z"]) <= EXPECTED_Z
        production = abs(item["production_single_draw_z"]) <= EXPECTED_Z
        e2_lines.append(
            f"| {item['target']} | {item['pattern']} | {item['class']} | "
            f"{exact(item['mc_mean_z'])} | {exact(item['mc_mean_exact_se'])} | "
            f"{exact(item['production_single_draw_z'])} | "
            f"{exact(item['production_exact_conditional_draw_se'])} | "
            f"{'PASS' if repeated and production else 'FAIL'} |"
        )
    p0_i = {item["target"]: item for item in setup["setup_gates"]["A17-15(i)"]["targets"]}
    p0_ii = {item["target"]: item for item in setup["setup_gates"]["A16-15(ii)"]["targets"]}
    p0_iii = {item["target"]: item for item in setup["setup_gates"]["A17-15(iii)"]["targets"]}
    p0_lines = []
    for target in result["targets"]:
        first, second, third = p0_i[target], p0_ii[target], p0_iii[target]
        p0_lines.append(
            f"| {target} | {first['full_bank_drawn_count']} | "
            f"{first['receipt_authorized_null_rows']} | {first['S_q_count']} | "
            f"`{first['S_q_mask_sha256_uint8_full_entity_axis']}` | "
            f"{'PASS' if first['pass'] else 'FAIL'} | "
            f"{'PASS' if second['pass'] else 'FAIL'} | "
            f"{'PASS' if third['pass'] else 'FAIL'} |"
        )
    c4_lines = [
        f"| {item['target']} | {item['pattern']} | {item['leg']} | "
        f"{exact(item['value'])} | {exact(item['mcse'])} | {item['status']} |"
        for item in c4["statistics"]
    ]
    c5_lines = [
        f"| {item['pattern']} | {item['quantity']} | {'PASS' if item['exact_match'] else 'FAIL'} |"
        for item in c5["exact_match_booleans"]
    ]
    c23_lines = [
        f"| {item['control']} | {item['group']} | {exact(item['estimate'])} | "
        f"{exact(item['oracle'])} | {exact(item['value'])} | {exact(item['mcse'])} | "
        f"{item['status']} |"
        for item in c2c3["statistics"]
    ]
    for control in ("C2", "C3"):
        power = c2c3["controls"][control]["power"]
        c23_lines.append(
            f"| {control} power | {power['target_group']} | NA | "
            f"{exact(power['absolute_oracle'])} | NA | {exact(power['target_group_mcse'])} | "
            f"{'PASS' if power['pass'] else 'FAIL'} |"
        )

    operator_lines = [
        f"| {row['target']} | {row['order']} | {row['stage']} | "
        f"{row['entity']} / {row['entity_key']} | {row['dataset']} | "
        f"{row['input_column']} → {row['output_column']} | {row['weight']} | "
        f"{row['transformation']} | {row['surface_status']} | "
        f"{row['source_code']['path']} `{row['source_code']['sha256']}`; {row['source_anchor']} |"
        for row in result["step0"]["operator_table"]
    ]
    default_lines = [
        f"- `{item['id']}` — {item['scope']}: {item['rule']} ({item['reason']})."
        for item in result["step0"]["default_appendix"]
    ]

    target_blocks: list[str] = []
    for target, section in result["targets"].items():
        leg_blocks: list[str] = []
        for leg in LEGS:
            data = section["legs"][leg]
            support = data["support"]
            ledger_lines = [
                f"| {item['row']} | {exact(item.get('value', 'NA'))} | "
                f"{exact(item.get('se', 'NA'))} | {item.get('status', 'NA')} |"
                for item in data["ledger"]
            ]
            attribution_lines = [
                f"| {item.get('row', 'NA')} | {exact(item.get('value', 'NA'))} | "
                f"{exact(item.get('se', 'NA'))} | {item.get('status', 'NA')} |"
                for item in data["attribution"]
            ]
            probes = ", ".join(
                f"{name}={value.get('status', value) if isinstance(value, dict) else value}"
                for name, value in data["probes"].items()
            )
            verdict = data["verdict"]
            leg_blocks.append(
                f"""#### {leg}

Support: {support['status']} (ASEC {support['asec_unique_sources']}, ACS {support['acs_unique_sources']}). Source: `{D0_JSON}`, SHA-256 `{digests['d0']}`, `/D0-1/rungs/candidate-25/{target}`.

| Ledger row | Value | SE | Status |
| --- | ---: | ---: | --- |
{chr(10).join(ledger_lines)}

| Attribution row | Value | SE | Status |
| --- | ---: | ---: | --- |
{chr(10).join(attribution_lines)}

Probes: {probes}.

Verdict: dominant row {exact(verdict.get('dominant_row'))}; share {exact(verdict.get('share'))}; cancellation index {exact(verdict.get('cancellation_index'))}; {verdict.get('verdict')}; defect class {exact(verdict.get('defect_class'))}; C/D flags {verdict.get('arm_C_flag')} / {verdict.get('arm_D_flag')}.
"""
            )
        special = ""
        if target == "pre_subsidy_care_expenses":
            special = "The A17 setup confirms the exact registered 183-row adult-care clearing set; the T5 ledger row above records whether later readings extended that finding.\n\n"
        elif target == "weeks_unemployed":
            special = "The T5, B1, and T2 rows above are the registered UC-clearing, producer-path, and transfer-stage split.\n\n"
        target_blocks.append(
            f"""### {target}

A17 P0 setup status: {'PASS' if p0_i[target]['pass'] and p0_ii[target]['pass'] and p0_iii[target]['pass'] else 'FAIL'}. Candidate full-bank drawn count {p0_i[target]['full_bank_drawn_count']}; S_q count {p0_i[target]['S_q_count']}; S_q mask `{p0_i[target]['S_q_mask_sha256_uint8_full_entity_axis']}`. Source: `{evidence['paths']['setup']}`, SHA-256 `{digests['setup']}`, `/setup_gates`.{readings_note}

{special}{chr(10).join(leg_blocks)}"""
        )

    cross_lines = [
        f"| {item['target']} | {item['leg']} | {exact(item.get('dominant_row'))} | "
        f"{exact(item.get('share'))} | {exact(item.get('cancellation_index'))} | "
        f"{item.get('verdict')} | {exact(item.get('defect_class'))} | "
        f"{item.get('arm_C_flag')} / {item.get('arm_D_flag')} |"
        for item in result["cross_target_summary"]
    ]
    binding_text = result["a16_binding_appendix"]["text"]
    return f"""{result['status_line']}

# QRF drift validation Phase 0 — v2.6/A17

## Control results

### Ratified family

K = {EXPECTED_K}; Šidák z* = {exact(EXPECTED_Z)}; ordered roster SHA-256 `{EXPECTED_K_DIGEST}`. Source: `{evidence['paths']['setup']}`, SHA-256 `{digests['setup']}`, `/control_roster`; sealed manifest SHA-256 `{seals['required_id_manifest_sha256']}`.

### C0a — {result['controls']['C0a']['status']}

All battery-incidence values below come from `{C0A}`, SHA-256 `{digests['c0a']}`, `/rows`; the A17 setup reverified the full input bundle at `{evidence['paths']['setup']}`, SHA-256 `{digests['setup']}`, `/adopted_control_reverification`.

| Rung | Target | Leg | ASEC incidence | ACS incidence | Status |
| --- | --- | --- | ---: | ---: | --- |
{chr(10).join(c0a_lines)}

### C0b — {result['controls']['C0b']['status']}

E4 and E2 values come from `{C0B}`, SHA-256 `{digests['c0b']}`, `/patterns` and `/per_class_controls`; z* is sourced as above.

| Target | Pattern | E4 bit identity |
| --- | --- | --- |
{chr(10).join(e4_lines)}

| Target | Pattern | Class | Repeated z | Repeated MCSE | Production z | Conditional draw SE | Status |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
{chr(10).join(e2_lines)}

### A17 P0 setup — {result['controls']['P0_A17_setup']['status']}

The three columns are A17-15(i), unchanged A16-15(ii), and A17-15(iii). Source: `{evidence['paths']['setup']}`, SHA-256 `{digests['setup']}`, `/setup_gates`; each bank digest is retained in the JSON mirror.

| Target | Full-bank drawn | Receipt rows | S_q | S_q mask SHA-256 | A17-15(i) | A16-15(ii) | A17-15(iii) |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
{chr(10).join(p0_lines)}

### C4 — {result['controls']['C4']['status']}

All 40 no-change Shapley-null totals come from `{evidence['paths']['c4']}`, SHA-256 `{digests['c4']}`, `/statistics`; canonical payload SHA-256 `{c4['canonical_sha256']}`.

| Target | Pattern | Leg | Contribution | MCSE | Status |
| --- | --- | --- | ---: | ---: | --- |
{chr(10).join(c4_lines)}

### C5 — {result['controls']['C5']['status']}

All exact fixture booleans come from `{C5}`, SHA-256 `{digests['c5']}`, `/exact_match_booleans`.

| Pattern | Quantity | Exact match |
| --- | --- | --- |
{chr(10).join(c5_lines)}

### C2/C3 — {c2c3['status']}

The six rostered oracle errors and two power decisions come from `{evidence['paths']['c2c3']}`, SHA-256 `{digests['c2c3']}`, `/statistics` and `/controls`; canonical payload SHA-256 `{c2c3['canonical_sha256']}`.

| Control | Group | Estimate | Oracle | Error | MCSE | Status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
{chr(10).join(c23_lines)}

### C1 — {result['controls']['C1']['status']}

C1 is gate-scoped and post-reading under A8. Its disposition and every manifest cell are explicit in the JSON mirror.

## Sealed Step-0 deliverables

The five objects and their composite are preserved byte-for-canonical-byte. Composite SHA-256 `{seals['composite_sha256']}`; manifest {len(manifest)} IDs; statistics {len(result['statistics'])} IDs; duplicates, missing IDs, and extras are all zero. Output canonical SHA-256 (excluding its own field) `{result['canonical_sha256']}`.

| Deliverable | SHA-256 |
| --- | --- |
| Operator table | `{seals['operator_table_sha256']}` |
| JSON Schema | `{seals['json_schema_sha256']}` |
| Required-ID manifest | `{seals['required_id_manifest_sha256']}` |
| Empty adjudication table | `{seals['adjudication_table_sha256']}` |
| Default appendix | `{seals['default_appendix_sha256']}` |

### Normative operator-stage table

| Target | Order | Stage | Entity / key | Dataset | Input → output | Weight | Transformation | Surface | Code source and anchor |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(operator_lines)}

### Sealed non-gated defaults

{chr(10).join(default_lines)}

## Per-target results

{chr(10).join(target_blocks)}

## Cross-target summary

| Target | Leg | Dominant row | Share | Cancellation index | Verdict | Defect class | C/D gating |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
{chr(10).join(cross_lines)}

## P8 — SSI dependency note

{result['P8_ssi']['note']} Status: {result['P8_ssi']['status']}.

## Execution discrepancies

The historical D0 K=214 roster is void. A14.6/A16-14 and A17 ratify K=122, z*={exact(EXPECTED_Z)}, and roster digest `{EXPECTED_K_DIGEST}`. The sealed Step-0 artifact kind remains A16 because changing it would break the ratified schema seal; `execution_version` is the authoritative A17 run marker.

## Appendix A — incorporated binding texts (verbatim)

Source: `{BINDING}`, SHA-256 `{digests['binding']}`.

```text
{binding_text}
```
"""


def main() -> None:
    args = parse_args()
    authority_digests = {path: verify_file(path, expected) for path, expected in EXPECTED_AUTHORITY.items()}
    adopted_digests = {path: verify_file(path, expected) for path, expected in EXPECTED_ADOPTED.items()}

    base = load_json(args.base_json)
    manifest, sealed_step0 = verify_step0(base)
    sealed_snapshot = canonical_bytes(sealed_step0)
    k_ids = roster(manifest)

    setup = load_json(args.setup)
    c4 = load_json(args.c4)
    c2c3 = load_json(args.c2c3)
    c0a = load_json(C0A)
    c0b = load_json(C0B)
    c5 = load_json(C5)
    setup_sha = sha256_file(args.setup)
    c4_sha = verify_canonical_artifact(args.c4, c4, "qrf_drift_phase0_a17_c4")
    c2c3_sha = verify_canonical_artifact(args.c2c3, c2c3, "qrf_drift_phase0_a17_c2c3")

    if setup.get("artifact_kind") != "qrf_drift_phase0_a17_setup_verification":
        raise ValueError("not an A17 setup-verification artifact")
    setup_roster = setup.get("control_roster", {})
    if (
        setup_roster.get("K") != EXPECTED_K
        or setup_roster.get("ordered_ids_sha256") != EXPECTED_K_DIGEST
        or setup_roster.get("sidak_z") != EXPECTED_Z
    ):
        raise ValueError("setup artifact does not carry the ratified roster")
    setup_evidence = setup.get("adopted_control_reverification", {})
    if not setup_evidence.get("all_file_digests_match"):
        raise ValueError("setup did not reverify every adopted-control input")
    for item in setup_evidence.get("adopted_evidence", []):
        if Path(item["path"]).name in {path.name for path in EXPECTED_ADOPTED} and not item.get("match"):
            raise ValueError(f"setup rejected adopted evidence {item['path']}")

    gate_summary = setup.get("gate_summary", {})
    required_setup_gates = (
        "adopted_C0a_C0b_C5",
        "ratified_K_roster",
        "A17-15(i)",
        "A16-15(ii)",
        "A17-15(iii)",
    )
    c0a_payload_pass = (
        c0a.get("status") == "PASS"
        and c0a.get("mismatched_comparisons") == 0
        and len(c0a.get("rows", [])) == 36
        and all(item.get("pass") is True for item in c0a.get("rows", []))
    )
    c0b_payload_pass = (
        c0b.get("status") == "PASS"
        and len(c0b.get("patterns", [])) == 36
        and len(c0b.get("per_class_controls", [])) == 76
        and all(item.get("e4_pattern_pass") is True for item in c0b.get("patterns", []))
        and all(
            abs(item["mc_mean_z"]) <= EXPECTED_Z
            and abs(item["production_single_draw_z"]) <= EXPECTED_Z
            for item in c0b.get("per_class_controls", [])
        )
    )
    c5_payload_pass = (
        c5.get("execution_status") == "PASS"
        and c5.get("checks_total") == c5.get("checks_passed") == 8
        and len(c5.get("exact_match_booleans", [])) == 8
        and all(
            item.get("exact_match") is True
            for item in c5.get("exact_match_booleans", [])
        )
    )
    setup_pass = (
        setup.get("status") == "PASS"
        and setup_evidence.get("pass") is True
        and c0a_payload_pass
        and c0b_payload_pass
        and c5_payload_pass
        and all(gate_summary.get(name) is True for name in required_setup_gates)
    )

    c4_manifest_ids = {
        item["id"] for item in manifest if item["dimensions"]["row"] == "C4_null_total"
    }
    c4_rows = c4.get("statistics", [])
    if len(c4_rows) != 40 or {item["id"] for item in c4_rows} != c4_manifest_ids:
        raise ValueError("C4 artifact is not the sealed 40-cell roster")
    if c4.get("authority", {}).get("design", {}).get("sha256") != authority_digests[DESIGN]:
        raise ValueError("C4 artifact does not cite the current A17 authority")
    if any(
        item.get("status") != ("PASS" if item.get("pass") else "FAIL")
        for item in c4_rows
    ):
        raise ValueError("C4 row status/pass contradiction")
    c4_pass = (
        setup_pass
        and c4.get("status") == "PASS"
        and c4.get("summary", {}).get("all_run_cells_pass") is True
        and all(item.get("pass") is True for item in c4_rows)
    )

    c23_manifest_ids = {
        item["id"]
        for item in manifest
        if item["dimensions"]["row"] in {"C2_oracle_error", "C3_oracle_error"}
    }
    c23_rows = c2c3.get("statistics", [])
    if len(c23_rows) != 6 or {item["id"] for item in c23_rows} != c23_manifest_ids:
        raise ValueError("C2/C3 artifact is not the sealed six-error roster")
    if c2c3.get("authority", {}).get("design", {}).get("sha256") != authority_digests[DESIGN]:
        raise ValueError("C2/C3 artifact does not cite the current A17 authority")
    if c2c3.get("status") not in {"PASS", "FAIL", "UNDERPOWERED"}:
        raise ValueError("C2/C3 artifact is not an authoritative terminal run")
    estimator = c2c3.get("estimator", {})
    aggregation = estimator.get("coalition_aggregation", {})
    if (
        estimator.get("official_recovery_array") != "paired_delta"
        or estimator.get("official_pairing") != "same_i_j"
        or aggregation.get("method")
        != "exact_stratum_weight_share_weighted_unit_means"
        or aggregation.get("formula") != "sum_h((W_h/W)*mean_h)"
        or aggregation.get("paths") != ["real", "paired_base"]
        or aggregation.get("includes_aligned_all_endpoints") is not True
        or aggregation.get("independent_r0_null_path", {}).get("method")
        != "flat_unit_mean"
    ):
        raise ValueError(
            "C2/C3 artifact uses the rejected recovery pairing or GQ aggregation"
        )
    if any(
        item.get("estimator_array") != "paired_delta"
        or item.get("pairing") != "same_i_j"
        or item.get("source", {}).get("official_recovery_array")
        != "paired_delta"
        for item in c23_rows
    ):
        raise ValueError("C2/C3 statistic does not bind the corrected official estimator")
    if any(
        item.get("status") != ("PASS" if item.get("pass") else "FAIL")
        for item in c23_rows
    ):
        raise ValueError("C2/C3 row status/pass contradiction")
    c23_controls = c2c3.get("controls", {})
    if set(c23_controls) != {"C2", "C3"}:
        raise ValueError("C2/C3 artifact must contain exactly C2 and C3 controls")
    strata = c2c3.get("scope", {}).get("pattern_stratum_aggregation", [])
    if (
        not strata
        or not math.isclose(
            math.fsum(float(item["exact_weight_share"]) for item in strata),
            1.0,
            rel_tol=0.0,
            abs_tol=2e-15,
        )
        or any(
            int(item["stop"]) - int(item["start"]) != int(item["allocation"])
            for item in strata
        )
    ):
        raise ValueError("C2/C3 exact GQ stratum aggregation proof is invalid")
    if any(
        control.get("official_recovery")
        != {"array": "paired_delta", "pairing": "same_i_j", "rostered": True}
        for control in c23_controls.values()
    ):
        raise ValueError("C2/C3 control payload does not bind same-i,j pairing")
    c2_pass = c4_pass and c23_controls["C2"].get("pass") is True and power_pass(c23_controls["C2"])
    c3_pass = c4_pass and c23_controls["C3"].get("pass") is True and power_pass(c23_controls["C3"])
    expected_c23_status = "PASS" if c2_pass and c3_pass else None
    if expected_c23_status == "PASS" and c2c3.get("status") != "PASS":
        raise ValueError("C2/C3 top status contradicts two passing controls")
    if expected_c23_status is None and c2c3.get("status") == "PASS":
        raise ValueError("C2/C3 top status PASS contradicts a failed control")

    failures: list[str] = []
    if not setup_pass:
        failures.extend(name for name in required_setup_gates if gate_summary.get(name) is not True)
        if not c0a_payload_pass:
            failures.append("adopted_C0a")
        if not c0b_payload_pass:
            failures.append("adopted_C0b")
        if not c5_payload_pass:
            failures.append("adopted_C5")
        if not failures:
            failures.append("A17_setup_status")
    elif not c4_pass:
        failures.append("C4")
    else:
        if not c2_pass:
            failures.append("C2")
        if not c3_pass:
            failures.append("C3")
    controls_failed = bool(failures)

    if controls_failed:
        fallback_status = "NOT_RUN_CONTROLS_FAILED"
        failure_stage = failures[0]
        failure_path = args.setup if failure_stage.startswith("A") or failure_stage.startswith("adopted") or failure_stage.startswith("ratified") else args.c4 if failure_stage == "C4" else args.c2c3
        failure_sha = setup_sha if failure_path == args.setup else c4_sha if failure_path == args.c4 else c2c3_sha
        failure_pointer = (
            "/gate_summary"
            if failure_path == args.setup
            else "/summary"
            if failure_path == args.c4
            else "/controls"
        )
        fallback_source = source_ref(
            failure_path,
            failure_sha,
            failure_pointer,
            reason=f"gated {failure_stage} failure; fail closed before readings",
        )
    else:
        fallback_status = "NOT_RUN_PRIORITY"
        fallback_source = source_ref(
            DESIGN,
            authority_digests[DESIGN],
            "/Amendment-v2.4/A8",
            reason="A8 bounded-priority work not supplied to this finalization",
        )

    statistics, by_id = fresh_statistics(manifest, fallback_status, fallback_source)
    index = dimension_index(statistics)
    locked: set[str] = set()

    def assign(row: dict[str, Any], *args_: Any, **kwargs: Any) -> None:
        if row["id"] in locked:
            raise ValueError(f"attempted to populate sealed ID twice: {row['id']}")
        set_stat(row, *args_, **kwargs)
        locked.add(row["id"])

    setup_source = source_ref(args.setup, setup_sha)
    c4_source = source_ref(args.c4, c4_sha, canonical_sha256=c4["canonical_sha256"])
    c23_source = source_ref(args.c2c3, c2c3_sha, canonical_sha256=c2c3["canonical_sha256"])
    assign(get_stat(index, rung="control", row="K"), EXPECTED_K, "OK", [setup_source])
    assign(get_stat(index, rung="control", row="sidak_z"), EXPECTED_Z, "OK", [setup_source])
    assign(
        get_stat(index, rung="control", row="K_enumeration_sha256"),
        EXPECTED_K_DIGEST,
        "OK",
        [
            source_ref(
                setup_roster["source"]["path"],
                setup_roster["source"]["sha256_actual"],
                "/step0/required_id_manifest",
                object_sha256=EXPECTED_STEP0_SEALS["required_id_manifest_sha256"],
            )
        ],
    )

    c0a_source = source_ref(C0A, adopted_digests[C0A])
    for position, item in enumerate(c0a["rows"]):
        for origin in ("asec", "acs"):
            passed = bool(item["pass"] and item[origin]["incidence_exact_binary64_match"])
            assign(
                get_stat(index, rung=item["rung"], target=item["target"], leg=item["leg"], row="C0a_incidence", variant=origin),
                item[origin]["incidence"],
                "PASS" if passed else "FAIL",
                [source_ref(C0A, adopted_digests[C0A], f"/rows/{position}/{origin}/incidence", target_column_sha256_float64=item["target_column_sha256_float64"])],
            )

    c0b_source = source_ref(C0B, adopted_digests[C0B])
    for position, item in enumerate(c0b["patterns"]):
        passed = bool(item["e4_pattern_pass"])
        assign(
            get_stat(index, rung="control", target=item["target"], pattern=item["pattern"], row="C0b_E4_bit_identity"),
            passed,
            "PASS" if passed else "FAIL",
            [source_ref(C0B, adopted_digests[C0B], f"/patterns/{position}/e4_pattern_pass", state_before_sha256=item["state_before_sha256_actual"], recorded_sign_sha256=item["recorded_sign_sha256"], reproduced_sign_sha256=item["reproduced_sign_sha256"])],
        )
    for position, item in enumerate(c0b["per_class_controls"]):
        repeated_pass = abs(item["mc_mean_z"]) <= EXPECTED_Z
        production_pass = abs(item["production_single_draw_z"]) <= EXPECTED_Z
        assign(
            get_stat(index, rung="control", target=item["target"], pattern=item["pattern"], leg=item["class"], row="C0b_E2", variant="repeated_draw"),
            item["mc_mean_z"],
            "PASS" if repeated_pass else "FAIL",
            [source_ref(C0B, adopted_digests[C0B], f"/per_class_controls/{position}/mc_mean_z")],
            mcse=item["mc_mean_exact_se"],
        )
        assign(
            get_stat(index, rung="control", target=item["target"], pattern=item["pattern"], leg=item["class"], row="C0b_E2", variant="production_draw"),
            item["production_single_draw_z"],
            "PASS" if production_pass else "FAIL",
            [source_ref(C0B, adopted_digests[C0B], f"/per_class_controls/{position}/production_single_draw_z")],
            se=item["production_exact_conditional_draw_se"],
        )

    c5_source = source_ref(C5, adopted_digests[C5])
    for position, item in enumerate(c5["exact_match_booleans"]):
        passed = bool(item["exact_match"])
        assign(
            get_stat(index, rung="control", pattern=item["pattern"], row="C5_exact_match", variant=item["quantity"]),
            passed,
            "PASS" if passed else "FAIL",
            [source_ref(C5, adopted_digests[C5], f"/exact_match_booleans/{position}/exact_match")],
        )

    d0 = load_json(D0_JSON)
    targets = list(d0["scope"]["targets"])
    support = support_by_target(d0, targets)
    for target in targets:
        for leg in LEGS:
            support_item = support[target][leg]
            assign(
                get_stat(
                    index,
                    rung="candidate-25",
                    target=target,
                    leg=leg,
                    row="verdict",
                    variant="support",
                ),
                support_item["status"],
                support_item["status"],
                [support_item["source"]],
            )
    setup_lookups = {
        name: {item["target"]: item for item in setup["setup_gates"][name]["targets"]}
        for name in ("A17-15(i)", "A16-15(ii)", "A17-15(iii)")
    }
    for target in targets:
        first = setup_lookups["A17-15(i)"][target]
        second = setup_lookups["A16-15(ii)"][target]
        third = setup_lookups["A17-15(iii)"][target]
        target_positions = {
            name: next(i for i, item in enumerate(setup["setup_gates"][name]["targets"]) if item["target"] == target)
            for name in setup_lookups
        }
        for variant, gate_name, item in (
            ("receipt_count", "A17-15(i)", first),
            ("lineage_alignment", "A16-15(ii)", second),
            ("baseline_terminal_raw", "A17-15(iii)", third),
        ):
            passed = bool(item["pass"])
            assign(
                get_stat(index, rung="candidate-25", target=target, row="P0_A16_15", variant=variant),
                passed,
                "PASS" if passed else "FAIL",
                [source_ref(args.setup, setup_sha, f"/setup_gates/{gate_name}/targets/{target_positions[gate_name]}/pass")],
            )
        bank = source_ref(first["bank_path"], first["bank_file_sha256"]["sha256_actual"])
        for row_name, value, pointer in (
            ("P0_bank_drawn_count", first["full_bank_drawn_count"], "full_bank_drawn_count"),
            ("P0_S_q_count", first["S_q_count"], "S_q_count"),
            ("P0_S_q_mask_sha256", first["S_q_mask_sha256_uint8_full_entity_axis"], "S_q_mask_sha256_uint8_full_entity_axis"),
        ):
            assign(
                get_stat(index, rung="candidate-25", target=target, row=row_name),
                value,
                "OK",
                [source_ref(args.setup, setup_sha, f"/setup_gates/A17-15(i)/targets/{target_positions['A17-15(i)']}/{pointer}"), bank],
            )

    if setup_pass:
        for position, item in enumerate(c4_rows):
            assign(
                by_id[item["id"]],
                item["value"],
                "PASS" if item.get("pass") else "FAIL",
                [source_ref(args.c4, c4_sha, f"/statistics/{position}", canonical_sha256=c4["canonical_sha256"], replicate_values_sha256=item["replicate_values_identity"]["sha256"])],
                mcse=item["mcse"],
            )
    if c4_pass:
        for position, item in enumerate(c23_rows):
            assign(
                by_id[item["id"]],
                item["value"],
                "PASS" if item.get("pass") else "FAIL",
                [source_ref(args.c2c3, c2c3_sha, f"/statistics/{position}", canonical_sha256=c2c3["canonical_sha256"], replicate_values_sha256=item["replicate_values_identity"]["sha256"])],
                mcse=item["mcse"],
            )
        for control in ("C2", "C3"):
            passed = power_pass(c23_controls[control])
            assign(
                get_stat(index, rung="control", target="child_support_received", row=f"{control}_power"),
                passed,
                "PASS" if passed else "FAIL",
                [source_ref(args.c2c3, c2c3_sha, f"/controls/{control}/power", canonical_sha256=c2c3["canonical_sha256"])],
            )

    readings: dict[str, Any] | None = None
    readings_sha: str | None = None
    if args.readings is not None:
        if controls_failed:
            raise ValueError("readings input is forbidden after a gated control failure")
        readings = load_json(args.readings)
        readings_sha = sha256_file(args.readings)
        seen: set[str] = set()
        for position, item in enumerate(readings.get("statistics", [])):
            identifier = item.get("id")
            if identifier not in by_id:
                raise ValueError(f"reading uses non-manifest ID {identifier!r}")
            if identifier in seen or identifier in locked:
                raise ValueError(f"reading duplicates or overwrites locked ID {identifier}")
            seen.add(identifier)
            spec = next(entry for entry in manifest if entry["id"] == identifier)
            status = item.get("status")
            if status not in spec["allowed_statuses"]:
                raise ValueError(f"reading status {status!r} is not allowed for {identifier}")
            sources = copy.deepcopy(item.get("sources", []))
            sources.append(source_ref(args.readings, readings_sha, f"/statistics/{position}"))
            set_stat(
                by_id[identifier],
                item.get("value", "NA"),
                status,
                sources,
                se=item.get("se", "NA"),
                mcse=item.get("mcse", "NA"),
                default_resolved=bool(item.get("default_resolved", False)),
            )

    target_sections, cross_summary = build_default_sections(
        targets, support, setup_lookups, fallback_status, fallback_source, setup_source
    )
    if readings is not None:
        supplied_targets = readings.get("targets", {})
        unknown_targets = set(supplied_targets) - set(target_sections)
        if unknown_targets:
            raise ValueError(f"reading artifact has unknown targets: {sorted(unknown_targets)}")
        for target, value in supplied_targets.items():
            target_sections[target] = deep_merge(target_sections[target], value)
        if "cross_target_summary" in readings:
            cross_summary = copy.deepcopy(readings["cross_target_summary"])
            expected_pairs = {(target, leg) for target in targets for leg in LEGS}
            actual_pairs = {
                (item.get("target"), item.get("leg")) for item in cross_summary
            }
            if len(cross_summary) != 18 or actual_pairs != expected_pairs:
                raise ValueError("cross-target summary is not the exact 9x2 roster")

    if controls_failed:
        final_status = "CONTROLS_FAILED"
    elif readings is None:
        final_status = "PARTIAL"
    else:
        requested_status = readings.get("status", "PARTIAL")
        if requested_status not in {"COMPLETE", "PARTIAL"}:
            raise ValueError("readings status must be COMPLETE or PARTIAL")
        if requested_status == "COMPLETE" and any(row["status"] == "NOT_RUN_PRIORITY" for row in statistics):
            raise ValueError("readings claims COMPLETE while sealed IDs remain NOT_RUN_PRIORITY")
        if requested_status == "COMPLETE" and (
            set(readings.get("targets", {})) != set(targets)
            or "cross_target_summary" not in readings
            or "P8_ssi" not in readings
        ):
            raise ValueError(
                "COMPLETE readings must supply nine target sections, 9x2 summary, and P8"
            )
        final_status = requested_status

    failed_text = ", ".join(failures)
    if final_status == "CONTROLS_FAILED":
        status_line = f"STATUS: CONTROLS_FAILED — {failed_text}; readings and C1 NOT_RUN_CONTROLS_FAILED"
    elif final_status == "PARTIAL":
        status_line = "STATUS: PARTIAL — all controls passed; unreached readings are NOT_RUN_PRIORITY under A8"
    else:
        status_line = "STATUS: COMPLETE — all controls and required readings completed"

    result = copy.deepcopy(base)
    result.update(
        {
            "execution_version": EXECUTION_VERSION,
            "status": final_status,
            "status_line": status_line,
            "authority": {
                "design": source_ref(DESIGN, authority_digests[DESIGN], commit=DESIGN_COMMIT),
                "d0_json": source_ref(D0_JSON, authority_digests[D0_JSON]),
                "d0_markdown": source_ref(D0_MARKDOWN, authority_digests[D0_MARKDOWN]),
                "a16_binding_texts": source_ref(BINDING, authority_digests[BINDING]),
            },
            "source_catalog": {
                "A17_setup": setup_source,
                "C0a": c0a_source,
                "C0b": c0b_source,
                "C4": c4_source,
                "C5": c5_source,
                "C2_C3": c23_source,
                "readings": source_ref(args.readings, readings_sha) if readings_sha is not None else None,
            },
            "controls": {
                "K": {**copy.deepcopy(setup_roster), "ordered_ids": k_ids, "status": "BOUND_RATIFIED_A17"},
                "C0a": {"status": "PASS_ADOPTED_A14_7" if c0a_payload_pass else "FAIL", "comparisons": c0a.get("comparisons"), "cells": c0a.get("cells"), "mismatches": c0a.get("mismatched_comparisons"), "source": c0a_source},
                "C0b": {"status": "PASS_ADOPTED_A14_7_AT_A17_THRESHOLD" if c0b_payload_pass else "FAIL", "summary": copy.deepcopy(c0b.get("summary")), "A17_sidak_z": EXPECTED_Z, "source": c0b_source},
                "P0_A17_setup": {"status": "PASS" if setup_pass else "FAIL", "gates": copy.deepcopy(setup["setup_gates"]), "gate_summary": copy.deepcopy(gate_summary), "source": setup_source},
                "C4": {"status": "PASS" if c4_pass else "FAIL" if setup_pass else "NOT_RUN_CONTROLS_FAILED", "summary": copy.deepcopy(c4.get("summary")), "source": c4_source},
                "C5": {"status": "PASS_ADOPTED_A14_7" if c5_payload_pass else "FAIL", "checks": c5.get("checks_total"), "checks_passed": c5.get("checks_passed"), "source": c5_source},
                "C2": {**compact_control(c23_controls["C2"]), "source": c23_source} if c4_pass else {"status": "NOT_RUN_CONTROLS_FAILED", "source": fallback_source},
                "C3": {**compact_control(c23_controls["C3"]), "source": c23_source} if c4_pass else {"status": "NOT_RUN_CONTROLS_FAILED", "source": fallback_source},
                "C1": {"status": fallback_status, "source": fallback_source},
            },
            "statistics": statistics,
            "targets": target_sections,
            "cross_target_summary": cross_summary,
            "P8_ssi": copy.deepcopy(readings.get("P8_ssi")) if readings and "P8_ssi" in readings else {
                "status": fallback_status,
                "note": "SSI is not a QRF target; P8 is only the registered short dependency note.",
                "source": fallback_source,
            },
            "stop": {
                "stage": failures[0] if controls_failed else "A8_PRIORITY" if final_status == "PARTIAL" else "NONE",
                "reason": f"gated numerical control failure: {failed_text}" if controls_failed else "unreached work follows the A8 priority rule" if final_status == "PARTIAL" else "none",
                "readings_opened": not controls_failed and readings is not None,
                "source": fallback_source,
            },
            "execution_discrepancies": [
                {
                    "prompt": "historical D0 K=214 and z*=3.673063850314496",
                    "authority": "A14.6/A16-14 and A17 ratify K=122 and z*=3.526967430023352",
                    "disposition": "used the sealed 122-cell roster",
                    "source": setup_source,
                },
                {
                    "prompt": "A16 artifact labels in sealed Step-0 schema",
                    "authority": "A17 changes execution authority but does not authorize mutating sealed Step-0 objects",
                    "disposition": "preserved artifact_kind/schema and added execution_version v2.6/A17",
                    "source": source_ref(DESIGN, authority_digests[DESIGN], "/Amendment-v2.6/A17"),
                },
            ],
            "a16_binding_appendix": {
                "path": str(BINDING),
                "sha256": authority_digests[BINDING],
                "text": BINDING.read_text(),
            },
        }
    )

    if canonical_bytes(result["step0"]) != sealed_snapshot:
        raise ValueError("Step-0 object changed during finalization")
    statistics.sort(key=lambda item: item["id"])
    manifest_ids = [item["id"] for item in manifest]
    statistic_ids = [item["id"] for item in statistics]
    duplicate_manifest = len(manifest_ids) - len(set(manifest_ids))
    duplicate_statistics = len(statistic_ids) - len(set(statistic_ids))
    missing = sorted(set(manifest_ids) - set(statistic_ids))
    extras = sorted(set(statistic_ids) - set(manifest_ids))
    if duplicate_manifest or duplicate_statistics or missing or extras:
        raise ValueError("final statistic completeness check failed")
    manifest_by_id = {item["id"]: item for item in manifest}
    for row in statistics:
        if row["status"] not in manifest_by_id[row["id"]]["allowed_statuses"]:
            raise ValueError(f"status {row['status']} not allowed for {row['id']}")
    result["validation"] = {
        "manifest_count": len(manifest_ids),
        "statistics_count": len(statistic_ids),
        "duplicate_manifest_ids": duplicate_manifest,
        "duplicate_statistic_ids": duplicate_statistics,
        "missing_ids": len(missing),
        "extra_ids": len(extras),
        "step0_seals_unchanged": True,
        "schema_status": "PENDING_CANONICAL_HASH",
    }
    result["canonical_sha256"] = "0" * 64
    Draft202012Validator(result["step0"]["json_schema"]).validate(result)
    result["validation"]["schema_status"] = "PASS"
    canonical_scope = dict(result)
    canonical_scope.pop("canonical_sha256")
    result["canonical_sha256"] = digest_object(canonical_scope)
    Draft202012Validator(result["step0"]["json_schema"]).validate(result)

    evidence = {
        "setup": setup,
        "c0a": c0a,
        "c0b": c0b,
        "c4": c4,
        "c5": c5,
        "c2c3": c2c3,
        "paths": {
            "setup": args.setup,
            "c4": args.c4,
            "c2c3": args.c2c3,
            "readings": args.readings,
        },
        "digests": {
            "setup": setup_sha,
            "c0a": adopted_digests[C0A],
            "c0b": adopted_digests[C0B],
            "c4": c4_sha,
            "c5": adopted_digests[C5],
            "c2c3": c2c3_sha,
            "d0": authority_digests[D0_JSON],
            "binding": authority_digests[BINDING],
            "readings": readings_sha,
        },
    }
    markdown = render_markdown(result, evidence)
    atomic_write(args.json_output, canonical_bytes(result) + b"\n")
    atomic_write(args.markdown_output, markdown.encode("utf-8"))
    print(
        json.dumps(
            {
                "status": result["status"],
                "failed_controls": failures,
                "canonical_sha256": result["canonical_sha256"],
                "manifest_count": len(manifest_ids),
                "statistics_count": len(statistic_ids),
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
