"""Eager/deferred invented fixture parity through actual maintained owners.

No financial model, PUF donor or engine runs in these controls. Profiling only
counts calls to the unchanged producer during fixture construction.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest
from test_us_graph_atomic_property_financial import _property_host_source_arguments

from microcosm.build.frame_checkpoint import load_frame_checkpoint
from microcosm.build.us_runtime import asec_person_income_source as restoration
from microcosm.build.us_runtime import current_property_income_sources as owner
from microcosm.build.us_runtime import graph_survey_population as graph
from microcosm.build.us_runtime import survey_population_preparation as preparation


def _source_snapshot(source_root):
    # Ten explicitly admitted invented files; do not traverse fixture stores.
    result = {}
    for name in preparation._SOURCE_ROSTER:
        path = source_root / name
        data = path.read_bytes()
        stat = path.stat()
        result[name] = (
            data,
            (
                stat.st_dev,
                stat.st_ino,
                stat.st_mode,
                stat.st_size,
                stat.st_mtime_ns,
                stat.st_ctime_ns,
            ),
        )
    assert len(result) == 10
    return result


def _qualified_fixture_snapshot(root, *, complete_adults, deferred):
    root.mkdir()
    calls = []
    producer_code = restoration.restore_asec_person_income_source.__code__

    def profile(frame, event, _arg):
        if event == "call" and frame.f_code is producer_code:
            calls.append(Path(frame.f_locals["output_dir"]).name)

    with pytest.MonkeyPatch.context() as patch:
        previous_profile = sys.getprofile()
        try:
            sys.setprofile(profile)
            # Omitting the new flag explicitly exercises the eager default.
            kwargs = {"defer_intermediate_restoration": True} if deferred else {}
            case = _property_host_source_arguments(
                root, patch, complete_adults=complete_adults, **kwargs
            )
        finally:
            sys.setprofile(previous_profile)
        assert sys.getprofile() is previous_profile
        assert calls == (
            ["restored", "property-restored-money"]
            if deferred
            else [
                "restored",
                "ss-restored-money",
                "demographic-restored-money",
                "routing-restored-money",
                "property-restored-money",
            ]
        )

        source_root = case.call["source_dir"]
        before = _source_snapshot(source_root)
        output = root / "property-restored-money"
        restored = output / restoration.CHECKPOINT_FILENAME
        attached_bytes = before["asec/person-income-attachment.h5"][0]
        assert restored.read_bytes() == attached_bytes
        receipt_bytes = (output / "restoration.receipt.json").read_bytes()
        receipt = json.loads(receipt_bytes)
        assert receipt["output_sha256"] == hashlib.sha256(attached_bytes).hexdigest()
        assert receipt["output_file"] == restoration.CHECKPOINT_FILENAME
        checkpoint = load_frame_checkpoint(restored)
        assert checkpoint.metadata["person_income_observations"] == {
            key: value
            for key, value in receipt.items()
            if key not in {"output_sha256", "output_file"}
        }

        arguments = {
            key: case.call[key]
            for key in ("source_dir", "snapshot_root", "store_root", "fraction", "seed")
        }
        live = graph.run_authenticated_survey_population(
            **arguments, clones=True, return_values=True
        )
        qualified = owner.qualify_current_property_income_sources(
            live.preparation, live.allocated_population, live.clone_population
        )
        seal = owner.property_income_sources_seal(qualified)
        # Compare complete literal/checkpoint bytes and original physical file
        # identities before/after actual source qualification. No T is patched
        # after issuance; both variants consume their own original live owner.
        assert _source_snapshot(source_root) == before
        entry = live.preparation._checked()
        assert owner.property_income_sources_seal(qualified) == seal
        preparation._pure_final(entry[2])
        assert len(qualified.origins) == 9
        assert live.clone_population.frame.n("person") == 18
        assert qualified.evidence["model_fitted"] is False
        return {
            "source_bytes": {name: data for name, (data, _stat) in before.items()},
            "restoration_receipt": receipt_bytes,
            "checkpoint_metadata": checkpoint.metadata,
            "checkpoint_frame": owner._frame_seal(checkpoint.frame),
            "qualified_frames": tuple(
                owner._frame_seal(frame)
                for frame in (
                    qualified.source_frame,
                    qualified.donor_frame,
                    qualified.recipient_frame,
                )
            ),
            "qualified_tables": tuple(
                owner.physical._table_stamp(table)
                for table in (
                    qualified.donor_basis.person,
                    qualified.donor_basis.provenance,
                    qualified.donor_basis.exclusions,
                    qualified.donor_basis.summary,
                    qualified.donor_columns,
                    qualified.recipient_columns,
                    qualified.origins,
                    qualified.recipient_diagnostics,
                )
            ),
            "recipient_matrix": qualified.recipient_matrix,
            "origin_document": qualified.origin_document,
        }


@pytest.mark.parametrize("complete_adults", [False, True])
def test_deferred_restoration_preserves_actual_source_qualification(
    tmp_path, complete_adults
):
    eager = _qualified_fixture_snapshot(
        tmp_path / "eager", complete_adults=complete_adults, deferred=False
    )
    deferred = _qualified_fixture_snapshot(
        tmp_path / "deferred", complete_adults=complete_adults, deferred=True
    )
    assert eager == deferred
