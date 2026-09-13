"""Complete age-15+ invented-source property38 -> PUF55 wiring, not release proof.

No authority, observation, unknownness or production source loader is patched.
One financial construction and one PUF cold/required pair serve all controls.
"""

import json
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from test_us_graph_atomic_property_financial import _property_host_source_arguments
from test_us_graph_puf55_canonical_donor import _original_sources

from microcosm.build.us_runtime import graph_current_survey_property as property_graph
from microcosm.build.us_runtime import graph_property_tax_leaves as tax
from microcosm.build.us_runtime import graph_survey_puf55 as graph
from microcosm.graph import StructuralDelta


@pytest.fixture(scope="module")
def complete_property_puf_bridge(tmp_path_factory):
    root = tmp_path_factory.mktemp("property38-puf-complete-adults")
    with pytest.MonkeyPatch.context() as patch:
        source = _property_host_source_arguments(
            root,
            patch,
            complete_adults=True,
            defer_intermediate_restoration=True,
        )
        financial = graph.financial.run_atomic_survey_financial(
            **source.call,
            property_income=replace(source.options, completion_routing=True),
            rebase_property_taxes=True,
            resume="auto",
        )
        # Test the actual existing gate before introducing donor input paths.
        assert len(financial.compiled.order) == 38
        assert (
            graph.codec.decode_json(financial.checked_view().payload)[
                "tax_leaf_complete"
            ]
            is True
        )
        graph.financial.require_complete_property_taxes(financial)
        definition, paths, _ = _original_sources(
            root / "original_puf", full_finalization_support=True
        )
        arguments = {
            "donor_sources": paths,
            "fixture_definition": definition,
            "seed": 578,
            "n_estimators": 2,
            "zero_atol": 0,
        }
        cold = graph.run_survey_puf55(financial, **arguments)
        warm = graph.run_survey_puf55(financial, **arguments, resume="require")
        yield SimpleNamespace(
            root=root, financial=financial, cold=cold, warm=warm, arguments=arguments
        )
        # The last control revokes only warm. Cold and its original parent must
        # still pass their real retained-source/store checks before teardown.
        cold.checked_view()
        financial.checked_view()


def test_complete_observations_reach_existing_property_gate(
    complete_property_puf_bridge,
):
    case = complete_property_puf_bridge
    run = case.financial
    frame = run.financial_population.frame
    original = run.prefix.preparation._checked()[2].frame.person
    assert len(original) == 9 and original.A_AGE.ge(15).all()
    assert len(frame.person) == 18
    assert (
        np.isfinite(
            frame.person[[tax.PROPERTY_COMPONENTS[0], tax.PROPERTY_COMPONENTS[2]]]
        )
        .all()
        .all()
    )
    verification = graph.codec.decode_json(
        graph.financial._run_entry(run)[2].tax_verification
    )
    assert verification["numeric_verified"] is True
    assert verification["complete"] is True
    assert graph.financial.financial_output_node(run) == tax.GATE_NODE

    provenance = graph.financial.values.provenance
    source_id = provenance.support_source_id_column("person")
    native_id = provenance.spine_source_id_column("person")
    channel = provenance.support_channel_column("person")
    clone_id = provenance.support_clone_index_column("person")
    assert set(frame.person[channel]) == {"acs", "asec"}
    columns = [o.column for o in property_graph.owned_columns()]
    for _, pair in frame.person.groupby(source_id, sort=False):
        assert len(pair) == 2 and set(pair[clone_id]) == {0, 1}
        pd.testing.assert_series_equal(
            pair.iloc[0][columns], pair.iloc[1][columns], check_names=False
        )
    # Independent ASEC O/D survive exclusion from the joint donor fit.
    survivor_overlap = frame.person[channel].eq("asec") & frame.person[native_id].eq(
        107
    )
    assert survivor_overlap.sum() == 2
    assert (
        frame.person.loc[survivor_overlap, "property_ordinary_interest"].eq(500).all()
    )
    assert frame.person.loc[survivor_overlap, "property_dividends"].eq(500).all()
    assert frame.person.loc[survivor_overlap, tax.PROPERTY_COMPONENTS[3]].isna().all()
    assert (
        frame.person.loc[
            frame.person[channel].eq("acs"), property_graph.PROPERTY_REPORTED_TOTAL
        ]
        .lt(0)
        .any()
    )


def test_complete_154_node_extension_and_required_replay(complete_property_puf_bridge):
    case = complete_property_puf_bridge
    before, cold, warm = case.financial, case.cold, case.warm
    boundary = graph._run_entry(cold)[2].boundary
    assert tuple(route.profile for route in boundary.routes) == (
        graph.attach.PROFILES[0],
    )
    assert len(cold.compiled.order) == len(warm.compiled.order) == 38 + 6 + 110 == 154
    assert cold.financial_run is warm.financial_run is before
    assert cold.manifest.key == warm.manifest.key
    assert all(cold.manifest.node(node).hit for node in before.compiled.order)
    assert all(record.hit for record in warm.manifest.nodes.values())
    for node, key in graph.financial._run_entry(before)[2].keys:
        assert cold.manifest.node(node).key == warm.manifest.node(node).key == key
    assert cold.store.root == before.store.root
    assert cold.store is not before.store and cold.kernels is not before.kernels
    graph.physical.replay.same_replayed_population(cold.population, warm.population)
    cold_view, warm_view = cold.checked_view(), warm.checked_view()
    assert cold_view.population is cold.population
    assert warm_view.population is warm.population
    assert cold_view.payload == warm_view.payload

    order = cold.compiled.order
    clone = graph.financial.atomic.clone
    expand, claim = clone.COMBINED_CLONE_NODE, clone.COMBINED_CLONE_CLAIM_NODE
    assert cold.compiled.graph.node(expand).structural is StructuralDelta.EXPAND
    assert cold.compiled.graph.node("geography.assign").population == expand
    chain = (
        expand,
        claim,
        "geography.assign",
        "geography.derive",
        graph.financial.financial.ATTACH_NODE,
        property_graph.ATTACH_NODE,
        tax.GATE_NODE,
        graph.recipient.PROJECTION_NODE,
        graph.recipient.MATRIX_NODE,
        graph.attach.FILTER_NODE,
        graph.attach.MASK_NODE,
        graph.attach.ATTACH_NODE,
    )
    assert [order.index(node) for node in chain] == sorted(
        order.index(node) for node in chain
    )
    edges = cold.compiled.graph.node(graph.recipient.PROJECTION_NODE).artifact_inputs
    gate_edge = next(edge for edge in edges if edge.name == "property_tax_verification")
    assert (
        gate_edge.producer == tax.GATE_NODE and gate_edge.type == tax.VERIFICATION_TYPE
    )

    # Compare every original cell; only actual declared clone1 outputs may change.
    left, right = before.financial_population.frame, cold.population.frame
    masks = graph.physical._masks(left)
    owned = {(o.entity, o.column) for o in boundary.nodes[2].outputs}
    for entity in left.entities:
        a, b = left.table(entity), right.table(entity)
        assert a.index.identical(b.index)
        for name in a:
            unchanged = (
                ~masks[entity]
                if (entity, name) in owned
                else np.ones(len(a), dtype=bool)
            )
            assert graph.population_ops.storage_equal(a[name], b[name], unchanged)
        np.testing.assert_array_equal(
            left.resolve_weights(entity).values, right.resolve_weights(entity).values
        )
    # Structural metadata belongs to the actual retained receiving version,
    # after the explicit keep-all FILTER transition.
    expected = boundary.expected.frame
    assert expected.schema == right.schema and expected.links == right.links
    assert expected.metadata == right.metadata and expected.mass_log == right.mass_log
    pd.testing.assert_series_equal(left.strata, right.strata)
    for entity in before.financial_population.design_weights:
        np.testing.assert_array_equal(
            before.financial_population.design_weights[entity],
            cold.population.design_weights[entity],
        )
    assert cold.population.mass_ledger == boundary.masked.mass_ledger
    assert "census_block_geoid" in right.table("household")

    receipt = graph.codec.decode_json(cold.receipt)
    assert receipt["complete_population_compared"] is True
    assert receipt["release_eligible"] is False
    (case.root / "bridge-acceptance.json").write_text(
        json.dumps(
            {
                "scope": "invented age15+ source wiring; no native completion or release",
                "financial_nodes": 38,
                "puf_nodes": len(cold.compiled.order),
                "profiles": receipt["profiles"],
                "prefix_hits": sum(
                    cold.manifest.node(n).hit for n in before.compiled.order
                ),
                "cold_hits": sum(record.hit for record in cold.manifest.nodes.values()),
                "required_hits": sum(
                    record.hit for record in warm.manifest.nodes.values()
                ),
                "tax_leaf_complete": True,
                "persons": len(right.person),
                "complete_population_equal": True,
                "checked_payload_equal": True,
                "release_eligible": False,
            },
            indent=2,
        )
        + "\n"
    )
    graph._pure_run(cold, graph._run_entry(cold))
    graph._pure_run(warm, graph._run_entry(warm))


@pytest.mark.parametrize("target", ["financial", "puf"])
def test_copied_handles_do_not_issue_bridge_authority(
    complete_property_puf_bridge, target
):
    case = complete_property_puf_bridge
    if target == "financial":
        with pytest.raises(ValueError, match="UNISSUED_FINANCIAL_RUN"):
            graph.run_survey_puf55(replace(case.financial), **case.arguments)
    else:
        with pytest.raises(ValueError, match="UNISSUED_PUF55_RUN"):
            replace(case.cold).checked_view()


def test_corrupted_required_output_permanently_revokes_only_that_handle(
    complete_property_puf_bridge,
):
    """Destructive final control: restoring test bytes cannot mint authority."""
    run = complete_property_puf_bridge.warm
    people = run.population.frame.person
    column = "taxable_interest_income"
    row = people.index[0]
    old = people.loc[row, column]
    assert np.isfinite(old)
    try:
        people.loc[row, column] = old + 17.0
        with pytest.raises(ValueError, match="PUF55_RUN_POPULATION_CHANGED"):
            run.checked_view()
    finally:
        people.loc[row, column] = old
    with pytest.raises(ValueError, match="UNISSUED_PUF55_RUN"):
        run.checked_view()
