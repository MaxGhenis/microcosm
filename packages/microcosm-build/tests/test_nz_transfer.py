"""Tiny transfer contracts; synthetic support never becomes certified NZ data."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from microcosm.build.nz_transfer import build_graph, run_candidate
from microcosm.build.nz_transfer_fixture import synthetic_us_donor
from microcosm.frame import Frame
from microcosm.graph import ContentStore, NodeRejectedError, RunManifest


@pytest.fixture(scope="module")
def targets():
    return json.loads(
        (
            Path(__file__).parent / "fixtures/nz_transfer/observed_targets.json"
        ).read_text()
    )


def test_tiny_transfer_lineage_holdouts_replay_and_missing_inputs(tmp_path, targets):
    donor = synthetic_us_donor(copies=2)
    result = run_candidate(donor, targets, tmp_path, epochs=8)
    manifest = result["manifest"]
    frame = manifest.populations["nz_calibration"]
    assert frame.n("person") == donor.n("person") == 72
    assert frame.n("household") == 32
    assert frame.n("family") == 36  # unrelated adults split from US units
    person = frame.table("person")
    assert [
        int(json.loads(value)[-1]) for value in person.donor_person_key
    ] == donor.table("person").person_id.tolist()
    assert min(person.person_id) > 2**53
    assert all(
        json.loads(key)[1] == result["report"]["source_frame_key"]
        for key in person.donor_person_key
    )
    assert person.donor_person_tax_unit_id.dtype.name == "string"
    assert set(person.donor_person_support_clone_index) == {0, 1}
    assert not any(
        "us_income_tax" in frame.table(e) or "us_snap" in frame.table(e)
        for e in frame.entities
    )
    np.testing.assert_allclose(
        person.annual_earnings_nzd,
        donor.table("person").fixture_annual_earnings_usd * 1.6,
    )
    assert frame.weights_for("household").kind.value == "calibrated"
    assert frame.table("household").donor_household_weight.eq(0.5).all()
    original = result["store"].load_frame(result["report"]["source_frame_key"])
    assert original.entities == donor.entities
    assert "us_income_tax" in original.table("person")  # retained source only
    graph = result["graph"]
    fit = {t[0] for t in graph.node("nz_calibration").params["targets"]}
    holdout = {t["id"] for t in targets["targets"] if t["role"] == "holdout"}
    assert len(fit) == 20 and len(holdout) == 12 and not fit & holdout
    coverage = result["report"]["coverage"]
    assert coverage["complete_rows"] == 0
    assert coverage["full_entitlement_computable"] is False
    assert result["report"]["fit_pass"] is False  # insufficient tiny support
    assert manifest.tier is None  # no release node or certified release exists
    assert manifest.nodes["nz_diagnostics"].receipt["outcome"] == "evidence_absent"
    RunManifest.load(tmp_path / "manifest.json", store=result["store"])
    first_report = (tmp_path / "report.json").read_bytes()
    replay = run_candidate(donor, targets, tmp_path, epochs=8)
    assert (tmp_path / "report.json").read_bytes() == first_report
    assert replay["manifest"].key == manifest.key
    assert all(r.hit for r in replay["manifest"].nodes.values())


def _changed(donor, entity, update):
    tables = {e: donor.table(e).copy() for e in donor.entities}
    update(tables[entity])
    return Frame(
        tables,
        donor.schema,
        {"household": donor.weights_for("household")},
        donor.strata,
    )


def test_refuses_nonfixture_and_cross_household_family(tmp_path, targets):
    donor = synthetic_us_donor(copies=1)
    real = _changed(
        donor,
        "household",
        lambda t: t.__setitem__("donor_fixture_status", "not_approved"),
    )
    with pytest.raises(NodeRejectedError, match="No real donor is approved"):
        run_candidate(real, targets, tmp_path / "real", epochs=1)
    bad = _changed(
        donor,
        "person",
        lambda t: t.__setitem__(
            "recipient_family_id", np.full(len(t), 1, dtype=np.int64)
        ),
    )
    with pytest.raises(NodeRejectedError, match="nest within households"):
        run_candidate(bad, targets, tmp_path / "families", epochs=1)


def test_clone_mass_and_fixture_markers_survive_shared_store(tmp_path, targets):
    donor = synthetic_us_donor(copies=1)
    assert donor.weights_for("household").values.sum() == 8
    store = ContentStore(tmp_path)
    store.put_frame("a" * 64, donor)
    loaded = store.load_frame("a" * 64)
    assert loaded.table("household").donor_fixture_status.eq("synthetic_fixture").all()
    assert len(build_graph(loaded, targets).nodes) == 7


@pytest.mark.parametrize(
    "entity,column",
    [
        ("household", "donor_fixture_status"),
        ("household", "donor_scope"),
        ("family", "family_source_id"),
    ],
)
def test_nullable_provenance_cannot_pass_admission(tmp_path, targets, entity, column):
    donor = synthetic_us_donor(copies=1)
    broken = _changed(
        donor,
        entity,
        lambda t: t.__setitem__(
            column,
            pd.Series(
                [pd.NA] * len(t),
                dtype="Int64" if column.endswith("source_id") else "string",
            ),
        ),
    )
    with pytest.raises(
        NodeRejectedError, match="(No real donor|full common Frame|Null donor lineage)"
    ):
        run_candidate(broken, targets, tmp_path, epochs=1)


def test_missing_support_clone_is_rejected(tmp_path, targets):
    donor = synthetic_us_donor(copies=1)
    pruned = donor.select(donor.table("person").person_support_clone_index.eq(0))
    with pytest.raises(NodeRejectedError, match="both support clones"):
        run_candidate(pruned, targets, tmp_path, epochs=1)
