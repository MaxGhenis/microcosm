"""Contracts for the sealed pre-P2 descriptive category defaults."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "tools"


def _load_module(name: str, filename: str):
    path = TOOLS / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(TOOLS))
    return module


DEFAULTS = _load_module(
    "qrf_drift_phase0_p2_defaults",
    "qrf_drift_phase0_p2_defaults.py",
)
P2 = _load_module("qrf_drift_phase0_p2", "qrf_drift_phase0_p2.py")


def test_payload_proves_d0_has_no_category_level_order() -> None:
    payload = DEFAULTS.build_payload()
    evidence = payload["d0_absence_evidence"]

    assert payload["status"] == "SEALED_BEFORE_P2"
    assert payload["scope"]["statistic_class"].startswith("NON_GATED")
    assert evidence["pass"] is True
    assert evidence["feature_order_present"] is True
    assert evidence["categorical_level_order_present"] is False
    assert evidence["D0_7_pattern_count"] == 36
    assert evidence["matching_key_pointers"] == []
    assert evidence["matching_text_pointers"] == []
    assert evidence["pattern_objects_with_category_keys"] == []
    assert DEFAULTS.verify_artifact(payload) == payload["canonical_sha256"]


@pytest.mark.parametrize(
    "feature",
    [
        "is_female",
        "__acs_transfer_is_household_head",
        "is_incapable_of_self_care",
        "previous_year_income_available",
    ],
)
def test_semantic_boolean_order_is_exact(feature: str) -> None:
    categories, source = DEFAULTS.registered_categories(
        feature,
        np.asarray([1.0, 0.0]),
        np.asarray([0.0, 1.0]),
    )

    assert categories == [0.0, 1.0]
    assert source == "sealed P2 default: semantic boolean order 0,1"
    with pytest.raises(ValueError, match="extra levels"):
        DEFAULTS.registered_categories(
            feature,
            np.asarray([0.0, 2.0]),
            np.asarray([1.0]),
        )


def test_tenure_and_state_rules_use_observed_binary64_order() -> None:
    tenure, tenure_source = DEFAULTS.registered_categories(
        "__acs_transfer_tenure_code",
        np.asarray([4.5, 0.0, -1.0]),
        np.asarray([3.0, 2.0]),
    )
    state, state_source = DEFAULTS.registered_categories(
        "__acs_transfer_state_fips",
        np.asarray([55.0, 1.0, 6.0]),
        np.asarray([6.0, 2.0]),
    )

    assert tenure == [0.0, 1.0, 2.0, 3.0, -1.0, 4.5]
    assert "ascending observed extras" in tenure_source
    assert state == [1.0, 2.0, 6.0, 55.0]
    assert "ascending observed binary64 FIPS" in state_source
    assert DEFAULTS.feature_semantics("age") == "numeric"


def test_artifact_is_byte_identical_and_p2_fails_closed_on_tamper(
    tmp_path: Path,
) -> None:
    path = tmp_path / "defaults.json"
    first_file_sha, first_canonical = DEFAULTS.write_payload(path)
    first_bytes = path.read_bytes()
    second_file_sha, second_canonical = DEFAULTS.write_payload(path)

    assert path.read_bytes() == first_bytes
    assert second_file_sha == first_file_sha
    assert second_canonical == first_canonical
    payload, receipt = P2.verify_reading_defaults(path)
    assert receipt["sha256"] == first_file_sha
    assert receipt["canonical_sha256"] == first_canonical
    assert receipt["implementation"] == payload["implementation"]

    payload["category_rules"]["state_fips"]["levels"] = "descending"
    scope = dict(payload)
    scope.pop("canonical_sha256")
    payload["canonical_sha256"] = DEFAULTS.canonical_sha256(scope)
    path.write_bytes(DEFAULTS.c4.canonical_bytes(payload) + b"\n")
    with pytest.raises(ValueError, match="not current/exact"):
        P2.verify_reading_defaults(path)
