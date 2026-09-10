"""NZ AS inputs stay fail-closed; optional tests execute the real Axiom adapter."""

import importlib.util
import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from microcosm.build.nz_policy import (
    AS_MODULE,
    AS_OUTPUTS,
    AS_REQUIRED_INPUTS,
    AS_SNAPSHOT_PERIOD,
    AccommodationSupplementEngine,
    accommodation_supplement_input_coverage,
    calculate_accommodation_supplement,
    make_accommodation_supplement_kernel,
    make_as_fixture_inputs,
)
from microcosm.frame import EntitySchema, Frame, WeightKind, Weights
from microcosm.graph import (
    Capabilities,
    ContentStore,
    Determinism,
    Graph,
    KernelBase,
    KernelContext,
    KernelRegistry,
    KernelResult,
    Node,
    Owned,
    Slice,
    SourceRef,
    StructuralDelta,
    compile_graph,
    load_source,
    run_graph,
)

_SCHEMA = EntitySchema(group_entities=("family", "household"))
_ROOT = os.environ.get("MICROCOSM_RULESPEC_NZ")
_ENGINE_AVAILABLE = importlib.util.find_spec("axiom_rules_engine") is not None
if _ENGINE_AVAILABLE:
    from axiom_rules_engine.dense import NativeCompiledDenseProgram

    _ENGINE_AVAILABLE = NativeCompiledDenseProgram is not None
_NEEDS_AXIOM = pytest.mark.skipif(
    not _ROOT or not _ENGINE_AVAILABLE,
    reason="requires real Axiom dense runtime and MICROCOSM_RULESPEC_NZ checkout",
)


def _frame(family=None):
    if family is None:
        family, _ = make_as_fixture_inputs([11, 21])
    return Frame(
        tables={
            "person": pd.DataFrame(
                {
                    "person_id": [101, 102, 103, 201, 202, 203],
                    "age": [35, 7, 10, 35, 7, 10],
                    "person_family_id": [11, 11, 11, 21, 21, 21],
                    "person_household_id": [1, 1, 1, 2, 2, 2],
                }
            ),
            "family": family,
            "household": pd.DataFrame({"household_id": [1, 2]}),
        },
        schema=_SCHEMA,
        weights={"household": Weights(np.ones(2), WeightKind.DESIGN)},
    )


def _provenance():
    return {name: "fixture" for name in AS_REQUIRED_INPUTS}


def test_unmapped_donor_has_no_implicit_zero_or_computable_as():
    report = accommodation_supplement_input_coverage(
        _frame(pd.DataFrame({"family_id": [11, 21]}))
    )
    assert report["required_inputs"] == 39
    assert report["complete_rows"] == 0
    assert report["incomplete_rows"] == 2
    assert all(field["absent"] for field in report["fields"].values())
    assert not report["ready_for_core_calculation"]
    assert not report["full_entitlement_computable"]


def test_absence_null_nonfinite_and_assumption_remain_distinct():
    table, provenance = make_as_fixture_inputs([11, 21])
    rent = "accommodation_supplement_weekly_rent_paid"
    assets = "accommodation_supplement_cash_assets"
    area = "accommodation_supplement_resides_in_area_1"
    table.loc[0, rent] = np.nan
    table.loc[1, assets] = np.inf
    table.drop(columns=[area], inplace=True)
    provenance[assets] = "assumed"
    report = accommodation_supplement_input_coverage(
        _frame(table), provenance=provenance
    )
    assert report["fields"][area]["absent"]
    assert report["fields"][rent]["null_rows"] == 1
    assert report["fields"][assets]["nonfinite_rows"] == 1
    assert report["assumed_fields"] == [assets]
    assert report["complete_rows"] == 0


def test_numeric_booleans_and_boolean_money_are_invalid():
    table, provenance = make_as_fixture_inputs([11, 21])
    field = "accommodation_supplement_resides_in_area_1"
    assets = "accommodation_supplement_cash_assets"
    table[field] = table[field].astype(int)
    table[assets] = True
    report = accommodation_supplement_input_coverage(
        _frame(table), provenance=provenance
    )
    assert report["fields"][field]["invalid_dtype"]
    assert report["fields"][assets]["invalid_dtype"]
    assert report["complete_rows"] == 0


def test_complete_values_do_not_substitute_for_input_provenance():
    report = accommodation_supplement_input_coverage(_frame())
    assert report["complete_rows"] == 2
    assert len(report["unclassified_fields"]) == 39
    assert not report["ready_for_core_calculation"]
    with pytest.raises(ValueError, match="Unsupported AS provenance"):
        accommodation_supplement_input_coverage(
            _frame(), provenance={AS_REQUIRED_INPUTS[0]: "observed_us_as_nz"}
        )


def test_fixture_is_named_and_explicit_but_never_full_entitlement():
    report = accommodation_supplement_input_coverage(_frame(), provenance=_provenance())
    assert report["ready_for_core_calculation"]
    assert not report["full_entitlement_computable"]
    assert {field["provenance"] for field in report["fields"].values()} == {"fixture"}
    with pytest.raises(ValueError, match="unique"):
        make_as_fixture_inputs([1, 1])


def test_changed_rulespec_content_is_refused_before_engine_loading(tmp_path):
    module = tmp_path / AS_MODULE
    module.parent.mkdir(parents=True)
    module.write_text("unexpected replacement")
    with pytest.raises(ValueError, match="differs from the reviewed"):
        AccommodationSupplementEngine(tmp_path, _SCHEMA, provenance=_provenance())


@_NEEDS_AXIOM
def test_real_axiom_separates_non_rate_gate_and_rate_and_matches_companion():
    table, provenance = make_as_fixture_inputs([11, 21])
    table.loc[1, "accommodation_supplement_cash_assets"] = 20_000.0
    output = calculate_accommodation_supplement(
        _frame(table), rulespec_root=Path(_ROOT), provenance=provenance
    )
    # The official companion's renter gets 305; increasing assets changes only
    # the independent non-rate judgment. Calling 305 entitlement is incorrect.
    np.testing.assert_array_equal(output[AS_OUTPUTS[0]], [1, -1])
    np.testing.assert_array_equal(output[AS_OUTPUTS[1]], [305, 305])


@_NEEDS_AXIOM
def test_real_adapter_refuses_annualization_partial_outputs_and_assumptions():
    provenance = _provenance()
    engine = AccommodationSupplementEngine(Path(_ROOT), _SCHEMA, provenance=provenance)
    with pytest.raises(ValueError, match="annualization"):
        engine.materialize(_frame(), AS_OUTPUTS, 2026)
    with pytest.raises(ValueError, match="both AS core"):
        engine.materialize(_frame(), [AS_OUTPUTS[1]], AS_SNAPSHOT_PERIOD)
    provenance["accommodation_supplement_cash_assets"] = "assumed"
    engine = AccommodationSupplementEngine(Path(_ROOT), _SCHEMA, provenance=provenance)
    with pytest.raises(ValueError, match="unapproved assumptions"):
        engine.materialize(_frame(), AS_OUTPUTS, AS_SNAPSHOT_PERIOD)
    output = calculate_accommodation_supplement(
        _frame(),
        rulespec_root=Path(_ROOT),
        provenance=provenance,
        allow_assumptions=True,
    )
    np.testing.assert_array_equal(output[AS_OUTPUTS[1]], [305, 305])


@_NEEDS_AXIOM
def test_actual_axiom_runs_through_shared_simulate_rules_kernel(tmp_path):
    frame = _frame()
    kernel = make_accommodation_supplement_kernel(
        Path(_ROOT), _SCHEMA, provenance=_provenance()
    )
    node = Node(
        id="nz_as_core",
        kernel=kernel.ref,
        inputs=(Slice("person", ("age",)), Slice("family", AS_REQUIRED_INPUTS)),
        outputs=(
            Owned("family", AS_OUTPUTS[0], "int64"),
            Owned("family", AS_OUTPUTS[1], "float64"),
        ),
        params={
            "engine_ref": kernel.engine_ref,
            "variables": AS_OUTPUTS,
            "period": AS_SNAPSHOT_PERIOD,
        },
    )
    result = kernel.run(
        KernelContext(
            node=node,
            tables={"person": frame.table("person"), "family": frame.table("family")},
            weights={"household": frame.weights_for("household")},
            strata=None,
            params=node.params,
            rng=np.random.default_rng(1),
        )
    )
    assert result.columns[("family", AS_OUTPUTS[0])].tolist() == [1, 1]
    assert result.columns[("family", AS_OUTPUTS[1])].tolist() == [305, 305]
    assert result.columns[("family", AS_OUTPUTS[1])].index.tolist() == [11, 21]
    assert result.receipt["period"] == "2026-04"

    # Exercise the full shared executor as well: output dtype validation would
    # reject the Axiom native int8 judgment without the explicit int64 widening.
    class FixtureSource(KernelBase):
        ref = "test.nz.as.fixture@1"
        capabilities = Capabilities(
            determinism=Determinism.DETERMINISTIC, structural=StructuralDelta.CREATE
        )

        def run(self, context):
            return KernelResult(
                frame=load_source("frame-store", context.sources["fixture"])
            )

    source_store = ContentStore(tmp_path / "source-store")
    source_file = source_store.put_frame("a" * 64, frame)
    source = FixtureSource()
    creator = Node(
        id="fixture",
        kernel=source.ref,
        structural=StructuralDelta.CREATE,
        sources=("fixture",),
        outputs=tuple(
            Owned(entity, name, str(table[name].dtype))
            for entity in frame.schema.entities
            for table in (frame.table(entity),)
            for name in table
            if not name.endswith("_id")
        ),
    )
    registry = KernelRegistry()
    registry.register(source)
    registry.register(kernel)
    manifest = run_graph(
        compile_graph(
            Graph(
                "nz-fixture",
                (SourceRef("fixture", "frame-store"),),
                (
                    creator,
                    replace(node, population="fixture"),
                ),
            )
        ),
        sources={"fixture": source_file},
        store=ContentStore(tmp_path / "store"),
        kernels=registry,
    )
    family = manifest.populations["fixture"].table("family")
    assert family[AS_OUTPUTS[0]].dtype == np.dtype("int64")
    assert family[AS_OUTPUTS[1]].tolist() == [305, 305]
