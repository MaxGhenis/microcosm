"""UK graph imports do not activate unrelated country resource contracts."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pandas as pd
import pytest

from microcosm.build import country_spec
from microcosm.build.cross_grain import CrossGrainBridge
from microcosm.build.uk_runtime import (
    battery_bindings,
    calibration_run,
    ledger_targets,
    source_runtime,
)


@pytest.fixture(autouse=True)
def _clear_requested_contracts():
    caches = (
        source_runtime._uk_nonnegative_declarations,
        calibration_run.uk_calibration_gate_scope_exclusions,
        ledger_targets._uk_contract_targets,
    )
    for cache in caches:
        cache.cache_clear()
    yield
    for cache in caches:
        cache.cache_clear()


def test_nonnegative_contract_loads_once_and_preserves_compatibility_identity(
    monkeypatch,
):
    requests = []

    def load(country):
        requests.append(country)
        return SimpleNamespace(
            sources=SimpleNamespace(
                stages=(
                    SimpleNamespace(stage="first", nonnegative_outputs=("x", "y")),
                    SimpleNamespace(stage="second", nonnegative_outputs=("y", "z")),
                )
            )
        )

    monkeypatch.setattr(country_spec, "load_country_spec", load)
    assert requests == []
    by_stage = source_runtime.uk_nonnegative_outputs_by_stage()
    assert by_stage == {"first": ("x", "y"), "second": ("y", "z")}
    assert source_runtime.UK_NONNEGATIVE_OUTPUTS_BY_STAGE is by_stage
    assert source_runtime.uk_nonnegative_outputs_by_stage() is by_stage
    outputs = source_runtime.uk_nonnegative_source_outputs()
    assert outputs == ("x", "y", "z")
    assert source_runtime.UK_NONNEGATIVE_SOURCE_OUTPUTS is outputs
    assert requests == ["uk"]

    # These compatibility views were formerly initialized together. Mutating
    # the returned legacy dict must not retroactively rebuild its union.
    by_stage["third"] = ("later",)
    assert source_runtime.uk_nonnegative_source_outputs() is outputs
    assert "later" not in outputs


def test_missing_source_manifest_still_has_no_nonnegative_outputs(monkeypatch):
    monkeypatch.setattr(
        country_spec, "load_country_spec", lambda country: SimpleNamespace(sources=None)
    )
    assert source_runtime.uk_nonnegative_outputs_by_stage() == {}
    assert source_runtime.uk_nonnegative_source_outputs() == ()


def test_nonnegative_gate_loads_constraints_and_refuses_missing_scheduled_column(
    monkeypatch,
):
    requests = []

    def load(country):
        requests.append(country)
        return SimpleNamespace(
            sources=SimpleNamespace(
                stages=(
                    SimpleNamespace(
                        stage="scheduled", nonnegative_outputs=("required",)
                    ),
                    SimpleNamespace(
                        stage="other", nonnegative_outputs=("not_required",)
                    ),
                )
            )
        )

    monkeypatch.setattr(country_spec, "load_country_spec", load)
    context = SimpleNamespace(
        frame=SimpleNamespace(
            entities=("person",), table=lambda entity: pd.DataFrame({"incumbent": [1]})
        ),
        artifacts={"build_stage_names": ("scheduled",)},
    )
    result = battery_bindings._evaluate_nonnegative_columns(context, {})
    assert not result.passed
    assert "required" in str(result.failures)
    assert "not_required" not in str(result.failures)
    assert requests == ["uk"]


def _invented_gate_scopes(monkeypatch):
    for attr, ids in (
        ("UK_CALIBRATION_GATE_SCOPE", ("calibration",)),
        ("UK_SPINE_GATE_SCOPE", ("spine",)),
        ("UK_NATIONAL_GATE_SCOPE", ("national",)),
        ("UK_LOCAL_GATE_SCOPE", ("local",)),
        ("UK_SHARED_GATE_IDS", frozenset()),
    ):
        monkeypatch.setattr(calibration_run, attr, ids)


def test_gate_scope_loads_on_request_and_preserves_compatibility_identity(monkeypatch):
    _invented_gate_scopes(monkeypatch)
    requests = []

    def load(country):
        requests.append(country)
        return SimpleNamespace(
            gates=SimpleNamespace(
                gates=tuple(
                    SimpleNamespace(id=name)
                    for name in ("calibration", "spine", "national", "local")
                )
            )
        )

    monkeypatch.setattr(calibration_run, "load_country_spec", load)
    assert requests == []
    exclusions = calibration_run.uk_calibration_gate_scope_exclusions()
    assert set(exclusions) == {"spine", "national", "local"}
    assert all(exclusions.values())
    assert calibration_run.UK_CALIBRATION_GATE_SCOPE_EXCLUSIONS is exclusions
    assert calibration_run.uk_calibration_gate_scope_exclusions() is exclusions
    assert requests == ["uk"]


@pytest.mark.parametrize("violation", ("overlap", "absent_declared_gate"))
def test_gate_scope_validation_still_refuses_invalid_declarations(
    monkeypatch, violation
):
    _invented_gate_scopes(monkeypatch)
    names = ("calibration", "spine", "national", "local")
    if violation == "overlap":
        monkeypatch.setattr(calibration_run, "UK_SPINE_GATE_SCOPE", ("calibration",))
        match = "both claim"
    else:
        names = ("calibration", "spine", "national")
        match = "does not classify"
    monkeypatch.setattr(
        calibration_run,
        "load_country_spec",
        lambda country: SimpleNamespace(
            gates=SimpleNamespace(
                gates=tuple(SimpleNamespace(id=name) for name in names)
            )
        ),
    )
    with pytest.raises(RuntimeError, match=match):
        calibration_run.uk_calibration_gate_scope_exclusions()


def _invented_contract(monkeypatch, targets, bridges):
    reads = []

    class Resource:
        def joinpath(self, name):
            assert name == "uk_population_targets.json"
            return self

        def read_text(self):
            reads.append("invented contract")
            return json.dumps({"targets": targets})

    def files(package):
        assert package == "microcosm.build.uk"
        return Resource()

    monkeypatch.setattr(ledger_targets.importlib_resources, "files", files)
    monkeypatch.setattr(ledger_targets, "UK_CROSS_GRAIN_BRIDGES", bridges)
    return reads


def _bridge(name="invented", higher=("higher",), lower="contract:lower"):
    return CrossGrainBridge(name, "invented.concept", higher, lower)


def _contract_rows():
    return [
        {"target_id": "higher", "geography_levels": ["country"]},
        {"target_id": "lower", "geography_levels": ["constituency"]},
    ]


def test_contract_validates_complete_mapping_before_national_projection(monkeypatch):
    reads = _invented_contract(monkeypatch, _contract_rows(), (_bridge(),))
    assert reads == []
    national = ledger_targets._uk_contract_targets()
    assert set(national) == {"higher"}
    assert ledger_targets._uk_contract_targets() is national
    assert reads == ["invented contract"]
    assert set(ledger_targets._uk_contract_targets(national_only=False)) == {
        "higher",
        "lower",
    }
    # The no-argument compatibility call uses the cached complete contract;
    # loading now validates with the supplied mapping and cannot recurse.
    ledger_targets._validate_uk_cross_grain_declarations()
    assert reads == ["invented contract", "invented contract"]


@pytest.mark.parametrize("missing", ("higher", "lower"))
def test_contract_getter_refuses_missing_bridge_side_before_filtering(
    monkeypatch, missing
):
    rows = [row for row in _contract_rows() if row["target_id"] != missing]
    reads = _invented_contract(monkeypatch, rows, (_bridge(),))
    with pytest.raises(ValueError, match="absent from the committed contract"):
        ledger_targets._uk_contract_targets()
    assert reads == ["invented contract"]


def test_contract_getter_refuses_duplicate_bridge_coverage(monkeypatch):
    _invented_contract(
        monkeypatch,
        _contract_rows(),
        (_bridge("first"), _bridge("second")),
    )
    with pytest.raises(ValueError, match="covered by both"):
        ledger_targets._uk_contract_targets()


def test_contract_missing_geography_warning_and_national_default_survive(monkeypatch):
    _invented_contract(monkeypatch, [{"target_id": "unspecified"}], ())
    with pytest.warns(UserWarning, match="geography"):
        result = ledger_targets._uk_contract_targets()
    assert set(result) == {"unspecified"}


@pytest.mark.parametrize("module", (source_runtime, calibration_run))
def test_lazy_contract_compatibility_rejects_unknown_attributes(module):
    with pytest.raises(AttributeError, match="no attribute"):
        _ = module.not_a_contract
