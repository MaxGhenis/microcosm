"""A failed typed gate remains evidence without inventing downstream data."""

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from microcosm.graph import (
    ArtifactInput,
    ArtifactOutput,
    ArtifactType,
    Capabilities,
    ContentStore,
    Determinism,
    Graph,
    KernelBase,
    Node,
    NodeRejectedError,
    Owned,
    RunManifest,
    StoreCorruptError,
    StoreMissError,
    compile_graph,
    describe,
    run_graph,
)
from microcosm.graph.availability import EXECUTION_SCHEMA
from microcosm.graph.kernel import KernelRole

spec = importlib.util.spec_from_file_location(
    "_gate_artifact_toy", Path(__file__).with_name("_toy.py")
)
toy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = toy
spec.loader.exec_module(toy)
EVIDENCE = ArtifactType("test.gate-evidence", 1)


class Gate(KernelBase):
    ref = "test.typed-gate@1"
    capabilities = Capabilities(Determinism.DETERMINISTIC, role=KernelRole.GATE)
    calls = 0

    def run(self, context):
        self.calls += 1
        raise RuntimeError("evidence could not be computed")


class Consume(KernelBase):
    ref = "test.consume-evidence@1"
    capabilities = Capabilities(Determinism.DETERMINISTIC)
    calls = 0

    def run(self, context):
        self.calls += 1
        raise AssertionError("An unavailable typed value must never reach a kernel.")


def fixture(tmp_path, *, release="structural"):
    gate = Node(
        "gate",
        Gate.ref,
        population="survey",
        outputs=(Owned("release", "gate_verdict", "string"),),
        artifact_outputs=(ArtifactOutput("evidence", EVIDENCE),),
    )
    byte_input = ArtifactInput("evidence", "gate", "evidence", EVIDENCE)
    nodes = [toy.CREATE, gate, toy.derive("independent", ("age",), "age_copy")]
    if release == "structural":
        nodes.extend(
            [
                Node(
                    "consumer",
                    Consume.ref,
                    population="survey",
                    outputs=(Owned("person", "unavailable", "float64"),),
                    artifact_inputs=(byte_input,),
                    artifact_outputs=(ArtifactOutput("transformed", EVIDENCE),),
                ),
                Node(
                    "byte_child",
                    Consume.ref,
                    population="survey",
                    artifact_inputs=(
                        ArtifactInput("model", "consumer", "transformed", EVIDENCE),
                    ),
                ),
                toy.derive("column_child", ("unavailable",), "unavailable_copy"),
                toy.select_node(),
                toy.derive("structural_child", ("age",), "later", population="adults"),
                toy.release_node(population="adults"),
            ]
        )
    else:
        final = toy.release_node(population="survey")
        nodes.append(
            replace(final, artifact_inputs=(byte_input,))
            if release == "byte"
            else final
        )
    compiled = compile_graph(Graph("toy", (toy.SOURCE,), tuple(nodes)))
    registry = toy.toy_registry()
    gate_kernel, consumer = Gate(), Consume()
    registry.register(gate_kernel)
    registry.register(consumer)
    return (
        compiled,
        toy.toy_sources(tmp_path),
        ContentStore(tmp_path / "store"),
        registry,
        gate_kernel,
        consumer,
    )


@pytest.mark.parametrize("release", ["structural", "byte", "verdict"])
def test_exception_evidence_and_unreached_dependents_replay(tmp_path, release):
    compiled, sources, store, registry, gate, consumer = fixture(
        tmp_path, release=release
    )
    cold = run_graph(compiled, sources=sources, store=store, kernels=registry)
    assert cold.tier == "evidence"
    assert cold.nodes["gate"].receipt["outcome"] == "fail"
    assert cold.nodes["gate"].receipt["evidence"]["exception_type"] == "RuntimeError"
    assert cold.nodes["gate"].receipt["execution"]["unavailable_artifacts"] == (
        "evidence",
    )
    assert not cold.nodes["gate"].opaque_artifacts
    assert "age_copy" in cold.population("survey").table("person")
    assert consumer.calls == 0
    if release != "verdict":
        assert cold.nodes["release"].receipt["outcome"] == "unreached"
        assert not cold.nodes["release"].artifacts
    if release == "structural":
        for node_id in (
            "consumer",
            "byte_child",
            "column_child",
            "adults",
            "structural_child",
            "release",
        ):
            receipt = cold.nodes[node_id]
            assert receipt.receipt["execution"]["state"] == "unreached"
            assert not receipt.artifacts and not receipt.opaque_artifacts
            assert receipt.frame_key is receipt.weight_key is None
        assert "adults" not in cold.populations
        assert "unavailable" not in cold.population("survey").table("person")
        assert "unreached" in describe(compiled, "consumer", cold)
    calls = toy.total_calls(registry)
    for policy in ("auto", "require"):
        replay = run_graph(
            compiled, sources=sources, store=store, kernels=registry, resume=policy
        )
        assert replay.key == cold.key and all(
            node.hit for node in replay.nodes.values()
        )
        assert gate.calls == 1 and consumer.calls == 0
        assert toy.total_calls(registry) == calls
    path = tmp_path / "manifest.json"
    cold.save(path)
    assert json.loads(path.read_text())["schema_version"] == 4
    assert RunManifest.load(path, store).key == cold.key
    with pytest.raises(NodeRejectedError, match="unreached|evidence"):
        RunManifest.load_certified(path, store)


def test_require_refuses_missing_unreached_receipt_before_any_execution(tmp_path):
    import shutil

    from microcosm.graph.executor import _cache_record_key

    compiled, sources, store, registry, gate, consumer = fixture(tmp_path)
    cold = run_graph(compiled, sources=sources, store=store, kernels=registry)
    shutil.rmtree(store.object_path(_cache_record_key(cold.nodes["consumer"].key)))
    before = toy.total_calls(registry)
    with pytest.raises(StoreMissError, match="consumer"):
        run_graph(
            compiled, sources=sources, store=store, kernels=registry, resume="require"
        )
    assert (
        toy.total_calls(registry) == before and gate.calls == 1 and consumer.calls == 0
    )


@pytest.mark.parametrize("parent", ["missing", "survey", "consumer"])
def test_forged_dangling_or_cyclic_blocker_refused(tmp_path, parent):
    compiled, sources, store, registry, _, _ = fixture(tmp_path)
    cold = run_graph(compiled, sources=sources, store=store, kernels=registry)
    nodes = dict(cold.nodes)
    receipt = dict(nodes["consumer"].receipt)
    receipt["execution"] = {
        "schema": EXECUTION_SCHEMA,
        "state": "unreached",
        "blocked_by": {
            parent: cold.nodes[parent].key if parent in cold.nodes else "a" * 64,
        },
    }
    nodes["consumer"] = replace(nodes["consumer"], receipt=receipt)
    with pytest.raises(ValueError, match="block|unavailable|cycle"):
        replace(cold, nodes=nodes)


def test_exception_manifest_cannot_downgrade_or_claim_available_bytes(tmp_path):
    compiled, sources, store, registry, _, _ = fixture(tmp_path)
    cold = run_graph(compiled, sources=sources, store=store, kernels=registry)
    raw = json.loads(cold.to_json())
    raw["schema_version"] = 3
    with pytest.raises(ValueError, match="schema 4"):
        RunManifest.from_json(json.dumps(raw))
    nodes = dict(cold.nodes)
    with pytest.raises(ValueError, match="unavailable|artifact"):
        nodes["gate"] = replace(nodes["gate"], opaque_artifacts={"evidence": "a" * 64})
        replace(cold, nodes=nodes)


def test_forbid_reexecutes_gate_but_never_unavailable_consumers(tmp_path):
    compiled, sources, store, registry, gate, consumer = fixture(tmp_path)
    first = run_graph(compiled, sources=sources, store=store, kernels=registry)
    again = run_graph(
        compiled, sources=sources, store=store, kernels=registry, resume="forbid"
    )
    assert again.key == first.key
    assert not any(node.hit for node in again.nodes.values())
    assert gate.calls == 2 and consumer.calls == 0


def test_artifact_only_gate_exception_returns_evidence_receipt(tmp_path):
    compiled, sources, store, registry, gate, _ = fixture(tmp_path)
    original = compiled.graph
    compiled = compile_graph(
        replace(
            original,
            nodes=(
                original.node("survey"),
                replace(original.node("gate"), outputs=()),
            ),
        )
    )
    first = run_graph(compiled, sources=sources, store=store, kernels=registry)
    assert first.nodes["gate"].receipt["outcome"] == "fail"
    assert (
        not first.nodes["gate"].artifacts and not first.nodes["gate"].opaque_artifacts
    )
    again = run_graph(
        compiled, sources=sources, store=store, kernels=registry, resume="require"
    )
    assert again.key == first.key and gate.calls == 1


@pytest.mark.parametrize("resume", ["auto", "require"])
def test_cached_blockers_are_rederived_from_actual_dependencies(tmp_path, resume):
    from microcosm.graph.executor import _cache_record_key

    compiled, sources, store, registry, gate, consumer = fixture(tmp_path)
    cold = run_graph(compiled, sources=sources, store=store, kernels=registry)
    key = cold.nodes["consumer"].key
    record_key = _cache_record_key(key)
    record = store.load_json(record_key)
    record["receipt"]["execution"]["blocked_by"] = {"survey": cold.nodes["survey"].key}
    store.put_json(record_key, record, node_key=key, verify_existing=False)
    with pytest.raises(StoreCorruptError, match="blocked provenance"):
        run_graph(
            compiled, sources=sources, store=store, kernels=registry, resume=resume
        )
    assert gate.calls == 1 and consumer.calls == 0


@pytest.mark.parametrize(
    "diagnostic", ["legacy", {"state": "unreached", "detail": "legacy diagnostic"}]
)
def test_legacy_free_form_execution_metadata_remains_portable(tmp_path, diagnostic):
    from microcosm.graph import NodeReceipt

    node = NodeReceipt(
        key="a" * 64,
        hit=False,
        seed=1,
        kernel_ref="legacy@1",
        kernel_impl_hash="b" * 64,
        capabilities=Capabilities(Determinism.DETERMINISTIC),
        receipt={"execution": diagnostic},
    )
    manifest = RunManifest(country="toy", nodes={"legacy": node})
    raw = manifest.to_json()
    assert json.loads(raw)["schema_version"] == 2
    assert RunManifest.from_json(raw).key == manifest.key


@pytest.mark.parametrize("field", ["frame_key", "weight_key"])
def test_unreached_cannot_claim_an_empty_product_key(tmp_path, field):
    compiled, sources, store, registry, _, _ = fixture(tmp_path)
    cold = run_graph(compiled, sources=sources, store=store, kernels=registry)
    with pytest.raises(ValueError, match="products"):
        replace(cold.nodes["consumer"], **{field: ""})
