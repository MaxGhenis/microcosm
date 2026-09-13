"""The sex fragment on a tiny real graph: invented values, actual executor.

The Frame, the source bytes and the qualified values here are invented and
claim no source authority. Everything they are run through — compile_graph,
run_graph, the ContentStore, population patching and the replay comparison —
is the real machinery, so cold and required execution, artifact identity and
complete receiving-state preservation are checked against it rather than
against a stub.
"""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_us_current_survey_sex import _frame, _qualified, _receiving

from microcosm.build.us_runtime import current_survey_sex as sex
from microcosm.build.us_runtime import graph_current_survey_sex as graph
from microcosm.frame import Frame
from microcosm.graph import (
    ArtifactInput,
    ArtifactOutput,
    ArtifactType,
    ArtifactValue,
    Capabilities,
    ContentStore,
    Determinism,
    Graph,
    GraphError,
    KernelBase,
    KernelRegistry,
    KernelResult,
    Node,
    NumericScope,
    Owned,
    SourceRef,
    StructuralDelta,
    compile_graph,
    run_graph,
)
from microcosm.graph import population as populations

RECEIVING = "invented.receiving"
ORDERING_TYPE = ArtifactType("invented.sex_ordering", 1)


def _ordering_edge(producer=RECEIVING):
    return ArtifactInput("ordering", producer, "ordering", ORDERING_TYPE)


def _invented_source(receiving, people):
    class InventedSource(KernelBase):
        ref = "invented.sex_receiving@1"
        capabilities = Capabilities(
            Determinism.DETERMINISTIC, structural=StructuralDelta.CREATE
        )

        def implementation_hash(self):
            return "a" * 64  # Test-only fixed producer for the invented Frame.

        def run(self, context):
            return KernelResult(
                frame=receiving, artifacts={"ordering": b"invented ordering input"}
            )

    node = Node(
        RECEIVING,
        InventedSource.ref,
        sources=(graph.SOURCE_NAME,),
        structural=StructuralDelta.CREATE,
        outputs=tuple(
            Owned("person", column, graph._dtype(people[column]))
            for column in people
            if column != "person_id"
        ),
        artifact_outputs=(ArtifactOutput("ordering", ORDERING_TYPE),),
    )
    return node, InventedSource()


def _graph_case(tmp_path, incumbent=None):
    qualified = _qualified()
    people = _receiving(qualified.rows, incumbent=incumbent).person
    receiving = _frame(people)
    create, source_kernel = _invented_source(receiving, people)
    after = _ordering_edge()
    calls = []
    expected_seal = graph.sex_projection_seal(qualified)

    def current():
        assert graph.sex_projection_seal(qualified) == expected_seal
        calls.append(True)

    nodes, kernels = graph.current_survey_sex_kernels(
        qualified,
        receiving,
        receiving_version=create.id,
        host_pins={},
        after=after,
        host_edges=(),
        require_current=current,
    )
    compiled = compile_graph(
        Graph(
            "us",
            (SourceRef(graph.SOURCE_NAME, "raw-bytes-v1"),),
            (create, *nodes),
        )
    )
    registry = KernelRegistry()
    registry.register(source_kernel)
    for kernel in kernels:
        registry.register(kernel)
    path = tmp_path / "invented-source.txt"
    path.write_bytes(b"invented sex fixture only")
    store = ContentStore(tmp_path / "store")
    arguments = {
        "sources": {graph.SOURCE_NAME: path},
        "store": store,
        "kernels": registry,
    }
    cold = run_graph(compiled, **arguments)
    observed = {}

    def capture(_node_id, population):
        observed[population.version] = population

    warm = run_graph(
        compiled, **arguments, resume="require", _population_observer=capture
    )
    return SimpleNamespace(
        qualified=qualified,
        people=people,
        receiving=receiving,
        nodes=nodes,
        compiled=compiled,
        cold=cold,
        warm=warm,
        store=store,
        calls=calls,
        observed=observed,
    )


def test_actual_graph_cold_and_required_bind_both_clones_and_keep_everything_else(
    tmp_path,
):
    import pandas as pd

    case = _graph_case(tmp_path)
    assert len(case.compiled.order) == 3
    assert case.cold.key == case.warm.key
    assert all(receipt.hit for receipt in case.warm.nodes.values())
    # Before and after each of the two cold fragment nodes; replay invokes none.
    assert len(case.calls) == 4
    output = case.warm.population(RECEIVING)
    pd.testing.assert_frame_equal(
        output.person[case.receiving.person.columns],
        case.receiving.person,
        check_exact=True,
    )
    column = output.person[sex.CANONICAL_COLUMN]
    assert str(column.dtype) == "boolean"
    original = output.person[sex.support_source_id_column("person")].to_numpy()
    values = column.to_numpy(na_value=pd.NA)
    assert set(values[original == 10]) == {True}
    assert set(values[original == 20]) == {False}
    assert all(value is pd.NA for value in values[original == 30])
    projection = case.warm.population(graph.SOURCE_NODE)
    assert set(sex.COLUMNS) <= set(projection.person.columns)
    assert sex.CANONICAL_COLUMN not in projection.person


def test_private_codes_stay_in_the_typed_artifact_and_the_public_receipt_is_closed(
    tmp_path,
):
    case = _graph_case(tmp_path)
    binding = case.warm.node(graph.BIND_NODE)
    document = json.loads(case.store.load_bytes(binding.opaque_artifacts["binding"]))
    assert set(document) == sex.PUBLIC_RECEIPT_KEYS
    assert document["acs_allocation_provenance"] == "unresolved"
    assert document["equivalent_allocation_evidence_claim"] is False
    assert document["source_admission_issued"] is False
    assert document["release_eligible"] is False
    projection = case.warm.node(graph.SOURCE_NODE)
    payload = case.store.load_bytes(projection.opaque_artifacts["projection"])
    assert payload == case.qualified.projection
    # The rowwise codes live only in the private typed artifact.
    assert sex.CODE_COLUMN in payload.decode()
    assert sex.CODE_COLUMN not in json.dumps(document)


def test_actual_graph_independent_complete_reconstruction(tmp_path):
    case = _graph_case(tmp_path)
    expected = {RECEIVING: populations.Population.from_frame(case.receiving, RECEIVING)}
    for node_id in case.compiled.order:
        if node_id == RECEIVING:
            continue
        node = case.compiled.graph.node(node_id)
        artifacts = {}
        for edge in node.artifact_inputs:
            producer = case.warm.node(edge.producer)
            key = producer.opaque_artifacts[edge.artifact]
            artifacts[edge.name] = ArtifactValue(
                case.store.load_bytes(key),
                edge.type,
                key,
                producer.key,
                NumericScope(),
            )
        version = case.compiled.versions[node_id]
        expected[version] = graph.expected_survey_sex_population(
            node_id,
            expected.get(version),
            qualified=case.qualified,
            node=node,
            artifacts=artifacts,
        )
    for version, population in expected.items():
        graph.replay.same_replayed_population(population, case.observed[version])


def test_materialized_verifier_accepts_the_run_and_refuses_a_wrong_declaration(
    tmp_path,
):
    case = _graph_case(tmp_path)
    node = case.compiled.graph.node(graph.BIND_NODE)
    incoming = populations.Population.from_frame(case.receiving, RECEIVING)
    receipt = graph.verify_materialized_survey_sex(
        case.observed[RECEIVING], incoming, qualified=case.qualified, node=node
    )
    assert set(receipt) == sex.PUBLIC_RECEIPT_KEYS
    assert receipt["declared_rewrite"] is False
    assert receipt["filled_cells"] == 4 and receipt["unresolved_cells"] == 2
    # A declaration that disagrees with the population it is applied to would
    # let a create silently overwrite an incumbent leaf; it must refuse here.
    wrong = replace(node, params={**dict(node.params), "declared_rewrite": True})
    with pytest.raises(ValueError, match="RECEIVING_DECLARATION"):
        graph.verify_materialized_survey_sex(
            case.observed[RECEIVING], incoming, qualified=case.qualified, node=wrong
        )


def test_projection_artifact_bytes_cannot_be_replaced():
    qualified = _qualified()
    receiving = _frame(_receiving(qualified.rows).person)
    bind = graph.current_survey_sex_nodes(
        qualified,
        receiving,
        receiving_version="country.receiving",
        host_pins={},
        after=_ordering_edge("country.amounts"),
        host_edges=(),
    )[1]
    artifacts = {
        graph.PROJECTION_ALIAS: ArtifactValue(
            b"{}", graph.PROJECTION_TYPE, "0" * 64, "1" * 64, NumericScope()
        ),
        "ordering": ArtifactValue(
            b"x", ORDERING_TYPE, "2" * 64, "3" * 64, NumericScope()
        ),
    }
    with pytest.raises(ValueError, match="ARTIFACT_PAYLOAD"):
        graph._check_artifacts(bind, artifacts, qualified, {})
    with pytest.raises(ValueError, match="ARTIFACT_ROSTER"):
        graph._check_artifacts(bind, {}, qualified, {})


def test_host_edge_pins_are_checked_against_the_incoming_artifact():
    qualified = _qualified()
    receiving = _frame(_receiving(qualified.rows).person)
    edge = ArtifactInput(
        "preparation", "survey_population.create", "preparation", ArtifactType("p", 2)
    )
    pins = {
        "preparation": {
            "producer_key": "a" * 64,
            "artifact_key": "b" * 64,
            "payload_sha256": "c" * 64,
        }
    }
    projection = graph.current_survey_sex_nodes(
        qualified,
        receiving,
        receiving_version="country.receiving",
        host_pins=pins,
        after=_ordering_edge("country.amounts"),
        host_edges=(edge,),
    )[0]
    assert edge in projection.artifact_inputs
    artifacts = {
        "ordering": ArtifactValue(
            b"x", ORDERING_TYPE, "2" * 64, "3" * 64, NumericScope()
        ),
        "preparation": ArtifactValue(
            b"payload", edge.type, "b" * 64, "a" * 64, NumericScope()
        ),
    }
    with pytest.raises(ValueError, match="HOST_EDGE_PIN"):
        graph._check_artifacts(projection, artifacts, qualified, pins)


def test_qualified_mutation_changes_the_seal_without_touching_a_fresh_value():
    qualified = _qualified()
    fresh = _qualified()
    seal = graph.sex_projection_seal(qualified)
    assert graph.sex_projection_seal(fresh) == seal
    qualified.rows.loc[10, sex.ALLOCATION_CODE_COLUMN] = 0
    with pytest.raises(ValueError, match="PROJECTION_BINDING"):
        graph.sex_projection_seal(qualified)
    assert graph.sex_projection_seal(fresh) == seal


def test_declared_rewrite_preserves_known_incumbents_through_the_real_patch():
    """The rewrite path goes through the executor's own patch, not a private writer."""
    import pandas as pd

    qualified = _qualified()
    people = _receiving(qualified.rows, incumbent={20: False}).person
    receiving = _frame(people)
    node = graph.current_survey_sex_nodes(
        qualified,
        receiving,
        receiving_version=RECEIVING,
        host_pins={},
        after=_ordering_edge("country.amounts"),
        host_edges=(),
    )[1]
    assert node.outputs[0].rewrite and node.outputs[0].dtype == "boolean"
    incoming = populations.Population.from_frame(receiving, RECEIVING)
    result = graph._result(qualified, node, receiving.person)
    patched = populations.patch(incoming, node, result)
    column = patched.frame.person[sex.CANONICAL_COLUMN]
    original = patched.frame.person[sex.support_source_id_column("person")].to_numpy()
    values = column.to_numpy(na_value=pd.NA)
    assert set(values[original == 20]) == {False}  # Incumbent preserved.
    assert set(values[original == 10]) == {True}  # Source-known null filled.
    assert all(value is pd.NA for value in values[original == 30])
    assert patched.owners[("person", sex.CANONICAL_COLUMN)] == graph.BIND_NODE
    for entity in receiving.entities:
        carried = patched.frame.table(entity)
        before = receiving.table(entity)
        pd.testing.assert_frame_equal(carried[before.columns], before, check_exact=True)


def test_a_rewrite_needs_a_receiving_version_with_a_base():
    """A host that adopts the rewrite must open a version below its CREATE node."""
    qualified = _qualified()
    people = _receiving(qualified.rows, incumbent={20: False}).person
    receiving = _frame(people)
    create, _kernel = _invented_source(receiving, people)
    nodes = graph.current_survey_sex_nodes(
        qualified,
        receiving,
        receiving_version=create.id,
        host_pins={},
        after=_ordering_edge(),
        host_edges=(),
    )
    assert nodes[1].outputs[0].rewrite
    with pytest.raises(GraphError, match="rewrite"):
        compile_graph(
            Graph(
                "us",
                (SourceRef(graph.SOURCE_NAME, "raw-bytes-v1"),),
                (create, *nodes),
            )
        )


def test_country_host_edges_name_the_real_typed_ancestry():
    edges = graph.country_host_edges()
    assert {edge.name for edge in edges} == {
        "preparation",
        "allocation",
        "frame_context",
    }
    assert all(type(edge) is ArtifactInput for edge in edges)
    assert {edge.producer for edge in edges} == {
        "survey_population.create",
        "survey_population.allocate",
    }


def test_projection_branch_keeps_the_original_support_and_adds_only_source_columns():
    qualified = _qualified()
    projected = graph._projection_frame(qualified)
    assert type(projected) is Frame
    person = projected.person
    assert set(sex.COLUMNS) <= set(person.columns)
    assert sex.CANONICAL_COLUMN not in person
    assert person.person_id.tolist() == qualified.rows.index.tolist()
    for entity in qualified.source_frame.entities:
        assert set(projected.table(entity).columns) <= set(
            qualified.source_frame.table(entity).columns
        ) | set(sex.COLUMNS)
