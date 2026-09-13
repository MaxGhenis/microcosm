"""Eager/deferred invented fixture parity through actual maintained owners.

No financial model, PUF donor or engine runs in these controls. Profiling only
counts calls to the unchanged producer during fixture construction.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
import test_us_asec_2024_native_population as native_fixture
import test_us_survey_population_preparation as survey_fixture
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


def _qualified_fixture_snapshot(
    root, *, complete_adults, deferred, original_fixture=None
):
    root.mkdir()
    calls = []
    producer_code = restoration.restore_asec_person_income_source.__code__

    def profile(frame, event, _arg):
        if event == "call" and frame.f_code is producer_code:
            calls.append(Path(frame.f_locals["output_dir"]).name)

    with pytest.MonkeyPatch.context() as patch:
        if original_fixture is not None:
            patch.setattr(survey_fixture, "asec_fixture", original_fixture)
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


def _different_field_names(left, right):
    """Bound field names only; never include a scalar value or list index."""
    names = []
    truncated = False
    visited = 0

    def add(parts):
        nonlocal truncated
        # Metadata values are never formatted, even on an unexpected schema.
        name = ".".join(parts) or "<root>"
        if len(name) > 64:
            name = name[:64]
            truncated = True
        if name not in names:
            if len(names) < 6:
                names.append(name)
            else:
                truncated = True

    def visit(first, second, parts, depth):
        nonlocal truncated, visited
        visited += 1
        if visited > 256:
            truncated = True
            return
        if first == second:
            return
        if depth == 6:
            add(parts)
            truncated = True
        elif type(first) is type(second) is dict:
            for key in sorted(set(first) | set(second)):
                label = (
                    key
                    if type(key) is str and key.isascii() and key.isidentifier()
                    else "<field>"
                )
                if key not in first or key not in second:
                    add((*parts, label))
                else:
                    visit(first[key], second[key], (*parts, label), depth + 1)
        elif type(first) is type(second) is list and len(first) == len(second):
            for a, b in zip(first, second, strict=True):
                visit(a, b, (*parts, "items"), depth + 1)
        else:
            add(parts)

    visit(left, right, (), 0)
    return {"names": names, "truncated": truncated}


def _parity_diagnostics(eager, deferred):
    """Expose equality booleans and bounded metadata field names, not payloads."""
    top = (
        "source_bytes",
        "restoration_receipt",
        "checkpoint_metadata",
        "checkpoint_frame",
        "qualified_frames",
        "qualified_tables",
        "recipient_matrix",
        "origin_document",
    )
    logical_files = (
        "request",
        "acs_households",
        "acs_persons",
        "asec_parent",
        "asec_households",
        "asec_persons",
        "asec_2022",
        "asec_2023",
        "asec_2024",
        "asec_household_csv",
    )
    assert set(eager) == set(deferred) == set(top)
    assert len(logical_files) == len(preparation._SOURCE_ROSTER) == 10
    assert (
        set(eager["source_bytes"])
        == set(deferred["source_bytes"])
        == set(preparation._SOURCE_ROSTER)
    )
    assert len(eager["qualified_frames"]) == len(deferred["qualified_frames"]) == 3
    assert len(eager["qualified_tables"]) == len(deferred["qualified_tables"]) == 8
    files = {}
    for label, source in zip(logical_files, preparation._SOURCE_ROSTER, strict=True):
        first, second = eager["source_bytes"][source], deferred["source_bytes"][source]
        # Only equality booleans leave this helper, never source bytes or hashes.
        files[label] = [
            first == second,
            hashlib.sha256(first).digest() == hashlib.sha256(second).digest(),
        ]
    diagnostic = {
        "top": {key: eager[key] == deferred[key] for key in top},
        "files_byte_hash_equal": files,
        "frames_equal": [
            first == second
            for first, second in zip(
                eager["qualified_frames"], deferred["qualified_frames"], strict=True
            )
        ],
        "tables_equal": [
            first == second
            for first, second in zip(
                eager["qualified_tables"], deferred["qualified_tables"], strict=True
            )
        ],
        "receipt_fields": _different_field_names(
            json.loads(eager["restoration_receipt"]),
            json.loads(deferred["restoration_receipt"]),
        ),
        "checkpoint_fields": _different_field_names(
            eager["checkpoint_metadata"], deferred["checkpoint_metadata"]
        ),
    }
    message = json.dumps(diagnostic, sort_keys=True, separators=(",", ":"))
    # Bound below the existing guard's 2048-character exception message limit.
    # On unforeseen schema growth, retain a static refusal without payloads.
    assert len(message) <= 1900, "PARITY_DIAGNOSTIC_SIZE"
    return message


@pytest.mark.parametrize("complete_adults", [False, True])
def test_deferred_restoration_preserves_actual_source_qualification(
    tmp_path, complete_adults
):
    shared = None
    initial_options = None
    copy_roots = []

    def original_fixture(path, patch, **options):
        nonlocal shared, initial_options
        if shared is None:
            initial_options = options
            # This stops after the real extra-household P/H reconstruction;
            # neither this construction nor sharing it produces or copies T.
            shared = native_fixture._shared_original_inputs(
                tmp_path / "shared-originals", patch, **options
            )
            parent = load_frame_checkpoint(shared.root / "invented-original-v4.h5")
            assert {107, 108} <= set(parent.frame.person.person_id)
            assert parent.metadata["source_receipt"]["sources"] == [
                {
                    "year": year,
                    "path": str(shared.root / f"invented-cohort-{year}.h5"),
                    "sha256": digest,
                }
                for year, digest in shared.source_pins[2]
            ]
        result = native_fixture._fixture(
            path, patch, shared_originals=shared, **options
        )
        assert path not in copy_roots
        copy_roots.append(path)
        native_fixture._check_shared_originals(shared)
        return result

    eager = _qualified_fixture_snapshot(
        tmp_path / "eager",
        complete_adults=complete_adults,
        deferred=False,
        original_fixture=original_fixture,
    )
    native_fixture._check_shared_originals(shared)
    deferred = _qualified_fixture_snapshot(
        tmp_path / "deferred",
        complete_adults=complete_adults,
        deferred=True,
        original_fixture=original_fixture,
    )
    assert len(copy_roots) == 2
    native_fixture._check_shared_originals(shared)
    parity_equal = eager == deferred
    # A scalar assertion preserves the complete original equality predicate
    # without pytest embedding either snapshot's private payload in its message.
    assert parity_equal, _parity_diagnostics(eager, deferred)

    # Refuse a different initial experiment before writing any variant input
    # or reaching the real producer. The positive five-versus-two call counts
    # above still observe the unchanged producer, including each base T.
    mismatch = tmp_path / "option-mismatch"
    mismatch.mkdir()
    with pytest.MonkeyPatch.context() as patch:
        with pytest.raises(AssertionError, match="^SHARED_ORIGINAL_OPTIONS$"):
            native_fixture._fixture(
                mismatch,
                patch,
                shared_originals=shared,
                **{**initial_options, "extra_household": False},
            )
    assert not tuple(mismatch.iterdir())
    native_fixture._check_shared_originals(shared)

    # Deliberate terminal revocation only after all positive parity and source
    # lifetime checks. One parameter checks bytes, the other physical metadata;
    # neither restores a revoked seed or uses an issued owner afterward.
    target = shared.root / "invented-cohort-2024.h5"
    if complete_adults:
        data = target.read_bytes()
        target.write_bytes(bytes([data[0] ^ 1]) + data[1:])
    else:
        info = target.stat()
        os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns + 1))
    revoked = tmp_path / "revoked-originals"
    revoked.mkdir()
    with pytest.MonkeyPatch.context() as patch:
        with pytest.raises(AssertionError, match="^SHARED_ORIGINAL_CHANGED$"):
            native_fixture._fixture(
                revoked, patch, shared_originals=shared, **initial_options
            )
    assert not tuple(revoked.iterdir())
