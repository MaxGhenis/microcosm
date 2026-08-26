#!/usr/bin/env python3
"""Seal the A16 regress-rule defaults used by the P2 marginal audit.

The D0 artifact orders gate features but does not bind category levels.  This
small, deterministic pre-reading artifact records that absence and freezes the
NON_GATED category presentation rules before P2 computes any marginal rows.
It does not read microdata or evaluate a scientific statistic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import qrf_drift_phase0_c4 as c4

WORKTREE = Path(__file__).resolve().parents[1]
DESIGN_MD = WORKTREE / "experiments/qrf_drift_validation_design.md"
D0_JSON = WORKTREE / "experiments/qrf_drift_validation_d0.json"
A16_BINDING = WORKTREE / "experiments/qrf_drift_validation_a16_binding_texts.md"
DEFAULT_OUT = Path("/private/tmp/qrf_phase0_a18_p2_defaults.json")

DESIGN_SHA256 = "5c8e55293215a7d1350c93825b1a4daf04e212bb84d17408b8750ed5d9d4e754"
D0_SHA256 = "fb57f6a0695a7a7137fb7270d4fa7bce7e6a6aa079cdc82e35bdf5bb7cf737c8"
A16_BINDING_SHA256 = "7e288bce7496e1e7f41e33f078be2043673ca54ff31182caf2ce92eab68a81c1"
A18_COMMIT = "8d553796e846012e7dc2663d7ffe108b6f965cca"

BOOLEAN_EXACT = (
    "is_female",
    "is_incapable_of_self_care",
    "previous_year_income_available",
)
BOOLEAN_SUFFIXES = ("_is_household_head",)
TENURE_SUFFIXES = ("_tenure_code",)
STATE_SUFFIXES = ("_state_fips",)
CATEGORY_KEY_MARKERS = (
    "categor",
    "category_order",
    "category_levels",
    "level_order",
    "feature_types",
    "semantic_types",
)
CATEGORY_TEXT_MARKERS = (
    "category order",
    "category levels",
    "categorical levels",
    "semantic boolean order",
    "state fips order",
    "tenure code order",
)


def require(condition: bool, message: str) -> None:
    """Raise a uniform fail-closed error."""
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    """Return a lowercase streaming SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    """Hash a JSON-safe value with the sealed Phase-0 encoder."""
    return hashlib.sha256(c4.canonical_bytes(value)).hexdigest()


def category_rules() -> dict[str, Any]:
    """Return the exact NON_GATED category rules embedded in the seal."""
    return {
        "scope": "P2 full-row marginal audit category-level detail only",
        "gated": False,
        "precedence": ["semantic_boolean", "tenure", "state_fips", "numeric"],
        "semantic_boolean": {
            "exact_names": list(BOOLEAN_EXACT),
            "suffixes": list(BOOLEAN_SUFFIXES),
            "levels_binary64": [0.0, 1.0],
            "unexpected_observed_level": "FAIL_CLOSED",
        },
        "tenure": {
            "suffixes": list(TENURE_SUFFIXES),
            "base_levels_binary64": [0.0, 1.0, 2.0, 3.0],
            "observed_extras": "append unique extras in ascending binary64 order",
        },
        "state_fips": {
            "suffixes": list(STATE_SUFFIXES),
            "levels": "unique donor+recipient observations in ascending binary64 order",
        },
        "numeric": {
            "levels": None,
            "rule": "all unmatched finite gate columns remain numeric",
        },
    }


def feature_semantics(name: str) -> str:
    """Classify one effective gate column under the sealed precedence."""
    if name in BOOLEAN_EXACT or name.endswith(BOOLEAN_SUFFIXES):
        return "semantic_boolean"
    if name.endswith(TENURE_SUFFIXES):
        return "tenure"
    if name.endswith(STATE_SUFFIXES):
        return "state_fips"
    return "numeric"


def _observed_binary64(*arrays: np.ndarray) -> list[float]:
    values = np.concatenate(
        [np.asarray(array, dtype=np.float64).reshape(-1) for array in arrays]
    )
    require(values.size > 0, "category ordering requires observed values")
    require(np.isfinite(values).all(), "category ordering received nonfinite values")
    return sorted(float(value) for value in np.unique(values))


def registered_categories(
    name: str,
    donor: np.ndarray,
    recipient: np.ndarray,
) -> tuple[list[float] | None, str]:
    """Apply the sealed category rules to observed binary64 values."""
    semantics = feature_semantics(name)
    observed = _observed_binary64(donor, recipient)
    if semantics == "semantic_boolean":
        extras = [value for value in observed if value not in {0.0, 1.0}]
        require(not extras, f"semantic boolean {name} has extra levels {extras}")
        return [0.0, 1.0], "sealed P2 default: semantic boolean order 0,1"
    if semantics == "tenure":
        base = [0.0, 1.0, 2.0, 3.0]
        extras = [value for value in observed if value not in base]
        return [*base, *extras], (
            "sealed P2 default: tenure 0,1,2,3 then ascending observed extras"
        )
    if semantics == "state_fips":
        return observed, "sealed P2 default: ascending observed binary64 FIPS"
    return None, "sealed P2 default: unmatched column is numeric"


def _scan_for_category_order(value: Any) -> dict[str, list[dict[str, str]]]:
    key_matches: list[dict[str, str]] = []
    text_matches: list[dict[str, str]] = []

    def walk(item: Any, pointer: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                child_pointer = f"{pointer}/{key}"
                lowered = str(key).lower()
                markers = [
                    marker for marker in CATEGORY_KEY_MARKERS if marker in lowered
                ]
                if markers:
                    key_matches.append(
                        {
                            "pointer": child_pointer,
                            "key": str(key),
                            "marker": markers[0],
                        }
                    )
                walk(child, child_pointer)
        elif isinstance(item, list):
            for position, child in enumerate(item):
                walk(child, f"{pointer}/{position}")
        elif isinstance(item, str):
            lowered = item.lower()
            markers = [marker for marker in CATEGORY_TEXT_MARKERS if marker in lowered]
            if markers:
                text_matches.append(
                    {"pointer": pointer, "text": item, "marker": markers[0]}
                )

    walk(value, "")
    return {"key_matches": key_matches, "text_matches": text_matches}


def d0_absence_evidence(d0: dict[str, Any]) -> dict[str, Any]:
    """Prove that the pinned D0 has feature order but no category-level order."""
    scan = _scan_for_category_order(d0)
    pattern_rows: list[dict[str, Any]] = []
    for target, target_payload in d0["D0-7"]["targets"].items():
        for pattern in target_payload["patterns"]:
            pattern_rows.append(
                {
                    "target": target,
                    "pattern": pattern["name"],
                    "keys": sorted(pattern),
                    "effective_gate_columns": pattern["effective_gate_columns"],
                }
            )
    require(len(pattern_rows) == 36, "D0-7 no longer contains 36 target-patterns")
    category_keys = [
        row
        for row in pattern_rows
        if any(
            any(marker in key.lower() for marker in CATEGORY_KEY_MARKERS)
            for key in row["keys"]
        )
    ]
    absent = not scan["key_matches"] and not scan["text_matches"] and not category_keys
    require(absent, "D0 now contains category-level ordering; default needs review")
    return {
        "checked_scope": "entire D0 JSON plus every /D0-7 target-pattern object",
        "D0_7_pattern_count": len(pattern_rows),
        "D0_7_pattern_records_sha256": canonical_sha256(pattern_rows),
        "searched_key_markers": list(CATEGORY_KEY_MARKERS),
        "searched_text_markers": list(CATEGORY_TEXT_MARKERS),
        "matching_key_pointers": scan["key_matches"],
        "matching_text_pointers": scan["text_matches"],
        "pattern_objects_with_category_keys": category_keys,
        "feature_order_present": all(
            row["effective_gate_columns"] for row in pattern_rows
        ),
        "categorical_level_order_present": False,
        "pass": True,
        "conclusion": (
            "D0 orders effective gate features but binds no category-level order"
        ),
    }


def _verify_authority_files() -> None:
    expected = {
        DESIGN_MD: DESIGN_SHA256,
        D0_JSON: D0_SHA256,
        A16_BINDING: A16_BINDING_SHA256,
    }
    for path, digest in expected.items():
        require(sha256_file(path) == digest, f"authority digest changed: {path}")


def build_payload() -> dict[str, Any]:
    """Build the deterministic pre-P2 defaults payload without writing it."""
    _verify_authority_files()
    d0 = json.loads(D0_JSON.read_text())
    helper_path = Path(__file__).resolve()
    c4_path = Path(c4.__file__).resolve()
    payload: dict[str, Any] = {
        "artifact_kind": "qrf_drift_phase0_a18_p2_descriptive_defaults",
        "schema_version": 1,
        "status": "SEALED_BEFORE_P2",
        "authority": {
            "design": {
                "path": str(DESIGN_MD),
                "sha256": DESIGN_SHA256,
                "commit": A18_COMMIT,
                "amendment": "v2.7/A18",
            },
            "d0": {"path": str(D0_JSON), "sha256": D0_SHA256},
            "a16_binding": {
                "path": str(A16_BINDING),
                "sha256": A16_BINDING_SHA256,
                "pointer": "/Finding 31 and A16 bounded regress rule",
            },
        },
        "scope": {
            "probe": "P2_marginal_audit",
            "statistic_class": "NON_GATED descriptive category-level detail",
            "sealed_phase_order": "before P2 recomputation",
            "scientific_estimator_changed": False,
        },
        "d0_absence_evidence": d0_absence_evidence(d0),
        "category_rules": category_rules(),
        "implementation": {
            "path": str(helper_path),
            "sha256": sha256_file(helper_path),
        },
        "source_files": [
            {"path": str(helper_path), "sha256": sha256_file(helper_path)},
            {"path": str(c4_path), "sha256": sha256_file(c4_path)},
        ],
    }
    payload["canonical_sha256"] = canonical_sha256(payload)
    return payload


def verify_artifact(payload: dict[str, Any]) -> str:
    """Fail closed unless a payload is the current sealed pre-P2 default."""
    recorded = payload.get("canonical_sha256")
    scope = dict(payload)
    scope.pop("canonical_sha256", None)
    actual = canonical_sha256(scope)
    require(recorded == actual, "P2 descriptive-default canonical seal mismatch")
    expected = build_payload()
    require(payload == expected, "P2 descriptive-default payload is not current/exact")
    return actual


def write_payload(path: Path) -> tuple[str, str]:
    """Write deterministic canonical bytes and return file/canonical digests."""
    payload = build_payload()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(c4.canonical_bytes(payload) + b"\n")
    return sha256_file(path), payload["canonical_sha256"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    file_sha, canonical_sha = write_payload(args.out)
    payload = json.loads(args.out.read_text())
    verify_artifact(payload)
    print(
        f"SEALED {args.out} sha256={file_sha} canonical_sha256={canonical_sha}",
        flush=True,
    )


if __name__ == "__main__":
    main()
