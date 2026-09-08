"""The supplied UK graph owns stage order and structural kernel selection."""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from microcosm.build.uk_runtime.graph_kernels import (
    UKExpandStageKernel,
    UKStageKernel,
    build_uk_registry,
)
from microcosm.graph import (
    Graph,
    Node,
    Owned,
    Slice,
    SourceRef,
    StructuralDelta,
    WeightTransition,
    compile_graph,
)


def _graph(*stages: Node) -> Graph:
    return Graph(
        country="uk",
        sources=(SourceRef("frs", "csv-tables", "Invented source; never loaded."),),
        nodes=(
            Node(
                id="root",
                kernel="uk.create@1",
                structural=StructuralDelta.CREATE,
                sources=("frs",),
                outputs=(Owned("household", "source", "float64"),),
                params={
                    "source_mode": "split",
                    "sample_fraction": 0.1,
                    "sample_seed": 9,
                },
            ),
            Node(
                id="boundary",
                kernel="uk.identity@1",
                structural=StructuralDelta.FILTER,
                base="root",
                inputs=(Slice("household", ("source",)),),
            ),
            Node(
                id="frs_spine",
                kernel="uk.claim@1",
                population="boundary",
                outputs=(Owned("household", "source", "float64", rewrite=True),),
            ),
            *stages,
        ),
    )


def _stage(name="invented_clone", *, expand=True) -> Node:
    return Node(
        id=name,
        kernel=f"uk.stage.{'expand.' if expand else ''}{name}@1",
        structural=StructuralDelta.EXPAND if expand else StructuralDelta.NONE,
        base="boundary" if expand else None,
        population=None if expand else "boundary",
        params={"stage": name},
    )


@pytest.mark.parametrize(
    "name,expand,expected_type",
    [
        ("invented_clone", True, UKExpandStageKernel),
        ("spi_support_channel", False, UKStageKernel),
    ],
)
def test_registry_uses_declared_mode_instead_of_a_stage_name_roster(
    name, expand, expected_type
):
    node = _stage(name, expand=expand)
    transform = object()
    registry = build_uk_registry(_graph(node), {name: transform})
    kernel = registry.get(node.kernel)
    assert isinstance(kernel, expected_type)
    assert kernel.capabilities.structural is node.structural
    assert kernel.transform is transform
    assert set(registry.refs()) == {n.kernel for n in _graph(node).nodes}


def test_registry_preserves_repeated_identical_stage_bindings():
    node = _stage()
    registry = build_uk_registry(_graph(node, replace(node, id="clone_again")), {})
    assert registry.refs().count(node.kernel) == 1


def test_registry_refuses_conflicting_modes_for_one_stage():
    expanded = _stage()
    ordinary = replace(_stage(expand=False), id="ordinary_again")
    with pytest.raises(ValueError, match="conflicting kernel bindings"):
        build_uk_registry(_graph(expanded, ordinary), {})


def test_registry_refuses_different_stages_that_collide_on_one_kernel_ref():
    expanded = _stage("x")
    ordinary = _stage("expand.x", expand=False)
    assert expanded.kernel == ordinary.kernel
    with pytest.raises(ValueError, match="conflicting stage bindings"):
        build_uk_registry(_graph(expanded, ordinary), {})


def test_registry_refuses_a_kernel_ref_inconsistent_with_structural_mode():
    node = replace(_stage(), kernel="uk.stage.invented_clone@1")
    with pytest.raises(ValueError, match="structural mode requires"):
        build_uk_registry(_graph(node), {})


@pytest.mark.parametrize("mode", [StructuralDelta.FILTER, StructuralDelta.REWEIGHT])
def test_registry_refuses_unsupported_stage_structural_modes(mode):
    node = replace(
        _stage(),
        structural=mode,
        weights=(
            WeightTransition("household", "calibrated")
            if mode is StructuralDelta.REWEIGHT
            else None
        ),
    )
    with pytest.raises(ValueError, match="unsupported structural mode"):
        build_uk_registry(_graph(node), {})


@pytest.mark.parametrize(
    "implementations,message",
    [
        ({"frs_spine": object()}, "Missing UK graph stage implementations"),
        ({"unknown": object()}, "Unknown UK graph stage implementations"),
    ],
)
def test_registry_retains_complete_transform_binding_checks(implementations, message):
    with pytest.raises(ValueError, match=message):
        build_uk_registry(_graph(_stage()), implementations)


def test_registry_retains_exact_reference_coverage_check():
    undeclared_family = Node(id="other", kernel="other.kernel@1", population="boundary")
    with pytest.raises(ValueError, match="does not exactly cover its graph"):
        build_uk_registry(_graph(_stage(), undeclared_family), {})


@pytest.fixture
def driver():
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "build_uk_frs_spine_authority_test", root / "tools/build_uk_frs_spine.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _spec(*stages):
    return SimpleNamespace(
        sources=SimpleNamespace(stages=tuple(SimpleNamespace(stage=s) for s in stages))
    )


def test_stage_projection_uses_the_supplied_graph_without_recompiling(
    driver, monkeypatch
):
    producer = Node(
        id="z_producer",
        kernel="uk.stage.z_producer@1",
        population="boundary",
        inputs=(Slice("household", ("source",)),),
        outputs=(Owned("household", "intermediate", "float64"),),
    )
    consumer = Node(
        id="a_consumer",
        kernel="uk.stage.a_consumer@1",
        population="boundary",
        inputs=(Slice("household", ("intermediate",)),),
        outputs=(Owned("household", "result", "float64"),),
    )
    graph = _graph(consumer, producer)
    compiled = compile_graph(replace(graph, nodes=tuple(reversed(graph.nodes))))

    def unexpected_reconstruction(*args, **kwargs):
        raise AssertionError("The projection must use the graph being executed.")

    monkeypatch.setattr(driver, "uk_spine_graph", unexpected_reconstruction)
    monkeypatch.setattr(driver, "compile_graph", unexpected_reconstruction)
    manifest = _spec(
        "a_consumer", "frs_hmrc_retained_leaves", "frs_spine", "z_producer"
    )
    assert driver._uk_spine_stage_names(manifest, compiled) == (
        "frs_spine",
        "z_producer",
        "a_consumer",
    )
    assert compiled.graph.node("root").params == graph.node("root").params


def test_stage_projection_refuses_missing_manifest_stage(driver):
    compiled = compile_graph(_graph())
    with pytest.raises(ValueError, match="graph and manifest stage roster disagree"):
        driver._uk_spine_stage_names(_spec("frs_spine", "missing"), compiled)


def test_stage_projection_refuses_missing_source_manifest(driver):
    with pytest.raises(ValueError, match="no source stages"):
        driver._uk_spine_stage_names(
            SimpleNamespace(sources=None), compile_graph(_graph())
        )
