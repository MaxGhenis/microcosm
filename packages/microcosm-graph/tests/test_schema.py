"""Invented declaration-only schema inspection; no kernels, Frames or sources."""

import hashlib
import json
from dataclasses import replace

import pytest

from microcosm.graph import (
    Graph,
    GraphError,
    Node,
    Owned,
    Ownership,
    Slice,
    SourceRef,
    StructuralDelta,
    compile_graph,
    graph_to_json,
    schema,
)


def declaration():
    return Graph(
        "invented",
        sources=(SourceRef("first", "unused@1"), SourceRef("other", "unused@1")),
        nodes=(
            Node(
                "base",
                "unused.create@1",
                structural=StructuralDelta.CREATE,
                sources=("first",),
                outputs=(
                    Owned("person", "age", "int64"),
                    Owned("person", "mask", "boolean"),
                    Owned(
                        "person", "unavailable", "float64", ownership=Ownership.ABSENT
                    ),
                ),
            ),
            Node(
                "derived",
                "unused.derive@1",
                population="base",
                inputs=(Slice("person", ("age", "mask")),),
                outputs=(Owned("person", "double_age", "float64", rows="mask"),),
                params={"factor": 2, "nested": ("literal", (True, None))},
                description="An invented masked derivation",
                citation="invented:rule",
            ),
            Node(
                "filtered",
                "unused.filter@1",
                structural=StructuralDelta.FILTER,
                base="base",
                inputs=(Slice("person", ("age",)),),
            ),
            Node(
                "rewrite",
                "unused.rewrite@1",
                population="filtered",
                inputs=(Slice("person", ("age", "mask"), rows="mask"),),
                outputs=(Owned("person", "age", "int64", rows="mask", rewrite=True),),
            ),
            Node(
                "expanded",
                "unused.expand@1",
                structural=StructuralDelta.EXPAND,
                base="filtered",
            ),
            Node(
                "other",
                "unused.create@1",
                structural=StructuralDelta.CREATE,
                sources=("other",),
                outputs=(Owned("person", "other_value", "int32"),),
            ),
            Node(
                "consumer",
                "unused.consume@1",
                population="expanded",
                inputs=(Slice("person", ("age", "double_age")),),
            ),
        ),
    )


def fields_by_key(result):
    return {
        (row["population"], row["entity"], row["column"]): row
        for row in result["schema"]
    }


def test_all_visible_fields_and_nearest_declarations():
    result = schema.graph_schema(compile_graph(declaration()))
    rows = fields_by_key(result)
    assert len(rows) == 13
    for version in ("base", "filtered", "expanded"):
        assert {
            (entity, column)
            for population, entity, column in rows
            if population == version
        } == {
            ("person", "age"),
            ("person", "mask"),
            ("person", "unavailable"),
            ("person", "double_age"),
        }
    assert rows["base", "person", "double_age"] == {
        "population": "base",
        "entity": "person",
        "column": "double_age",
        "dtype": "float64",
        "producer": "derived",
        "declared_in": "derived",
        "rows": "mask",
        "ownership": "produced",
        "rewrite": False,
    }
    assert rows["filtered", "person", "age"]["producer"] == "rewrite"
    assert rows["expanded", "person", "age"] == {
        "population": "expanded",
        "entity": "person",
        "column": "age",
        "dtype": "int64",
        "producer": "expanded",
        "declared_in": "rewrite",
        "rows": "mask",
        "ownership": "produced",
        "rewrite": True,
    }
    assert rows["expanded", "person", "unavailable"]["ownership"] == "absent"
    assert rows["expanded", "person", "unavailable"]["declared_in"] == "base"


def test_rewrite_incumbent_and_named_mask_bindings():
    result = schema.graph_schema(compile_graph(declaration()))
    bindings = result["input_bindings"]
    incumbent = next(
        row
        for row in bindings
        if row["node"] == "rewrite" and row["kind"] == "rewrite_incumbent"
    )
    assert incumbent == {
        "node": "rewrite",
        "population": "filtered",
        "entity": "person",
        "column": "age",
        "rows": "mask",
        "producer": "filtered",
        "declared_in": "base",
        "kind": "rewrite_incumbent",
    }
    explicit = next(
        row
        for row in bindings
        if row["node"] == "rewrite"
        and row["kind"] == "slice"
        and row["column"] == "age"
    )
    assert explicit["producer"] == "filtered" and explicit["declared_in"] == "base"
    for kind in ("slice_mask", "output_mask"):
        mask = next(
            row for row in bindings if row["node"] == "rewrite" and row["kind"] == kind
        )
        assert mask["column"] == "mask"
        assert mask["producer"] == "filtered" and mask["declared_in"] == "base"
    derived_mask = next(
        row
        for row in bindings
        if row["node"] == "derived" and row["kind"] == "output_mask"
    )
    assert derived_mask["producer"] == "base"


def test_actual_serialization_hash_and_descriptions():
    graph = declaration()
    compiled = compile_graph(graph)
    result = schema.graph_schema(compiled)
    raw = graph_to_json(graph).encode("utf-8")
    assert result["graph"] == json.loads(raw)
    assert result["graph_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["protocol"] == "microcosm.graph.schema.v1"
    assert result["country"] == "invented"
    assert result["compiled"]["order"] == list(compiled.order)
    assert result["compiled"]["owners"] == [
        list(key) + [value] for key, value in sorted(compiled.owners.items())
    ]
    assert not any(
        row["population"] == "expanded" and row["column"] == "other_value"
        for row in result["schema"]
    )
    derived = next(node for node in result["graph"]["nodes"] if node["id"] == "derived")
    assert derived["description"] == "An invented masked derivation"
    assert derived["citation"] == "invented:rule"
    assert derived["params"] == {"factor": 2, "nested": ["literal", [True, None]]}
    assert not {"units", "period", "formula", "nullability"} & set(result["schema"][0])


def test_declaration_reordering_preserves_compilation_and_schema_not_serialized_byte_hash():
    graph = declaration()
    left = schema.graph_schema(compile_graph(graph))
    right = schema.graph_schema(
        compile_graph(replace(graph, nodes=tuple(reversed(graph.nodes))))
    )
    assert left["compiled"] == right["compiled"]
    assert left["schema"] == right["schema"]
    assert left["input_bindings"] == right["input_bindings"]
    # The requested digest is of the actual serializer bytes, whose node list
    # retains authored order. It is not a claim of a computation/node key.
    assert left["graph_sha256"] != right["graph_sha256"]


def test_returned_objects_are_detached():
    compiled = compile_graph(declaration())
    first = schema.graph_schema(compiled)
    expected = schema.graph_schema(compiled)
    first["schema"][0]["producer"] = "forged"
    first["compiled"]["predecessors"]["consumer"].clear()
    first["graph"]["nodes"][1]["params"].clear()
    assert schema.graph_schema(compiled) == expected


@pytest.mark.parametrize("value", [None, {}, "compiled", declaration()])
def test_noncompiled_input_refuses(value):
    with pytest.raises(GraphError, match="actual CompiledGraph"):
        schema.graph_schema(value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("order", ("fake",)),
        ("versions", {}),
        ("predecessors", {}),
        ("owners", {}),
    ],
)
def test_stale_or_forged_compilation_refuses(field, value):
    compiled = replace(compile_graph(declaration()), **{field: value})
    with pytest.raises(GraphError, match="compiled structure mismatch"):
        schema.graph_schema(compiled)


@pytest.mark.parametrize(
    "name,limit",
    [
        ("MAX_NODES", 1),
        ("MAX_SOURCES", 1),
        ("MAX_DECLARED_FIELDS", 1),
        ("MAX_ROWS", 1),
        ("MAX_DECLARATION_BYTES", 64),
        ("MAX_EXPORT_BYTES", 64),
        ("MAX_ITEMS", 1),
        ("MAX_STRING_CHARS", 2),
        ("MAX_DEPTH", 1),
    ],
)
def test_small_limits_refuse_without_truncation(monkeypatch, name, limit):
    compiled = compile_graph(declaration())
    monkeypatch.setattr(schema, name, limit)
    with pytest.raises(GraphError):
        schema.graph_schema(compiled)


def test_invalid_graph_does_not_become_valid_by_wrapping_compilation():
    compiled = compile_graph(declaration())
    bad = replace(declaration().nodes[-1], inputs=(Slice("person", ("missing",)),))
    graph = replace(declaration(), nodes=(*declaration().nodes[:-1], bad))
    with pytest.raises(GraphError, match="no node owns"):
        schema.graph_schema(replace(compiled, graph=graph))
