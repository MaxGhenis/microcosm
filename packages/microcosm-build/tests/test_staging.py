import json

import pytest

from microcosm.build.staging import StagingTelemetry


class FakeApi:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, str, str]] = []

    def upload_file(
        self,
        *,
        path_or_fileobj,
        path_in_repo,
        repo_id,
        repo_type,
    ):
        self.uploads.append((str(path_or_fileobj), path_in_repo, repo_id, repo_type))
        return None


def test_staging_telemetry_writes_local_progress(tmp_path) -> None:
    telemetry = StagingTelemetry(
        run_id="run-a",
        candidate_release_id="populace-us-2024-abc-20260618T000000Z",
        run_dir=tmp_path / "run-a",
    )

    telemetry.stage("calibrating", message="Calibration started.", n_targets=3)
    telemetry.calibration_progress(
        {"kind": "calibration_epoch", "epoch": 1, "epochs": 5, "loss": 12.5}
    )
    telemetry.complete()

    progress = json.loads((tmp_path / "run-a" / "progress.json").read_text())
    calibration = json.loads(
        (tmp_path / "run-a" / "calibration_progress.json").read_text()
    )
    events = (tmp_path / "run-a" / "events.ndjson").read_text().strip().splitlines()

    assert progress["status"] == "passed"
    assert progress["stage"] == "complete"
    assert calibration["events"][0]["loss"] == 12.5
    assert len(events) >= 3


def test_staging_telemetry_uploads_repo_paths(tmp_path) -> None:
    api = FakeApi()
    telemetry = StagingTelemetry(
        run_id="run-b",
        candidate_release_id="populace-us-2024-def-20260618T000000Z",
        run_dir=tmp_path / "run-b",
        repo_id="policyengine/populace-us-staging",
        api=api,
        upload_interval_seconds=0,
    )
    telemetry.stage("target_compilation", force_upload=True)

    uploaded_paths = {upload[1] for upload in api.uploads}
    assert "runs/run-b/progress.json" in uploaded_paths
    assert "runs/run-b/run_manifest.json" in uploaded_paths
    assert "latest_staging.json" in uploaded_paths
    assert "runs.json" in uploaded_paths


def test_runs_index_keeps_existing_runs(tmp_path) -> None:
    # An older run is already recorded in the repo's index.
    existing = tmp_path / "existing.json"
    existing.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-06-19T00:00:00+00:00",
                "runs": [
                    {
                        "run_id": "older",
                        "candidate_release_id": "populace-us-2024-old-20260619T000000Z",
                        "status": "running",
                        "stage": "write_calibration_npz",
                        "updated_at": "2026-06-19T00:00:00+00:00",
                    }
                ],
            }
        )
    )

    class FakeApiWithDownload(FakeApi):
        def hf_hub_download(self, *, repo_id, filename, repo_type, **kwargs):
            return str(existing)

    telemetry = StagingTelemetry(
        run_id="newer",
        candidate_release_id="populace-us-2024-new-20260620T000000Z",
        run_dir=tmp_path / "newer",
        repo_id="policyengine/populace-us-staging",
        api=FakeApiWithDownload(),
        upload_interval_seconds=0,
    )
    telemetry.complete()

    index = json.loads((tmp_path / "newer" / "runs.json").read_text())
    run_ids = [run["run_id"] for run in index["runs"]]
    # Both the pre-existing run and this run survive (no overwrite).
    assert run_ids == ["newer", "older"]


def test_upload_failures_never_raise_and_disable_after_three(tmp_path, capsys):
    class FailingApi:
        def upload_file(self, **kwargs):
            raise RuntimeError("401 Unauthorized")

        def hf_hub_download(self, **kwargs):
            raise RuntimeError("401 Unauthorized")

    telemetry = StagingTelemetry(
        run_id="run-1",
        candidate_release_id="run-1",
        run_dir=tmp_path / "run",
        repo_id="org/staging",
        api=FailingApi(),
        upload_interval_seconds=0.0,
    )
    # Staging telemetry is best-effort: failing uploads must never raise, and
    # after three consecutive failures uploads are disabled for the run.
    telemetry.stage("one", force_upload=True)
    telemetry.stage("two", force_upload=True)
    assert telemetry.repo_id is None
    err = capsys.readouterr().err
    assert "staging upload" in err
    assert "disabling staging uploads" in err
    # Nothing reached the repo, and the run says so. A configured destination
    # is not evidence of delivery.
    assert telemetry.uploads_succeeded == 0


def test_uploads_succeeded_counts_files_that_reached_the_repo(tmp_path):
    api = FakeApi()
    telemetry = StagingTelemetry(
        run_id="run-c",
        candidate_release_id="run-c",
        run_dir=tmp_path / "run-c",
        repo_id="org/staging",
        api=api,
        upload_interval_seconds=0.0,
    )

    telemetry.stage("target_compilation", force_upload=True)

    assert telemetry.uploads_succeeded == len(api.uploads)
    assert telemetry.uploads_succeeded > 0


def test_blank_path_prefix_falls_back_to_the_default(tmp_path):
    # A blank or slash-only prefix would put run files at the repo root, where
    # the dashboard's runs/<run_id> paths cannot find them.
    for blank in ("", "   ", "/", " / "):
        telemetry = StagingTelemetry(
            run_id="run-e",
            candidate_release_id="run-e",
            run_dir=tmp_path / "run-e",
            path_prefix=blank,
        )
        assert telemetry.path_prefix == "runs"
        assert telemetry.repo_run_prefix == "runs/run-e"


def test_path_prefix_is_trimmed_but_otherwise_respected(tmp_path):
    telemetry = StagingTelemetry(
        run_id="run-f",
        candidate_release_id="run-f",
        run_dir=tmp_path / "run-f",
        path_prefix="  /candidate-runs/  ",
    )
    assert telemetry.path_prefix == "candidate-runs"
    assert telemetry.repo_run_prefix == "candidate-runs/run-f"


def test_uploads_succeeded_is_zero_for_a_local_only_run(tmp_path):
    telemetry = StagingTelemetry(
        run_id="run-d",
        candidate_release_id="run-d",
        run_dir=tmp_path / "run-d",
    )

    telemetry.stage("target_compilation", force_upload=True)

    assert telemetry.uploads_succeeded == 0
    assert (tmp_path / "run-d" / "progress.json").is_file()


@pytest.mark.parametrize(
    "suffix",
    (
        ".h5",
        ".hdf5",
        ".npz",
        ".xlsx",
        ".xls",
        ".sav",
        ".7z",
        ".txt",
        ".jsonl",
        "",
    ),
)
def test_staging_attachment_rejects_non_telemetry_without_mutation(
    tmp_path, suffix
) -> None:
    class NoDownloadApi(FakeApi):
        def hf_hub_download(self, **kwargs):
            raise FileNotFoundError("no existing runs index")

    api = NoDownloadApi()
    run_dir = tmp_path / "run-guarded"
    telemetry = StagingTelemetry(
        run_id="run-guarded",
        candidate_release_id="populace-us-2024-test",
        run_dir=run_dir,
        repo_id="alternate-owner/private-staging",
        api=api,
        upload_interval_seconds=0,
    )
    source = tmp_path / f"private-rows{suffix}"
    source.write_bytes(b"row-level payload")
    copied = run_dir / source.name
    manifest_before = (run_dir / "run_manifest.json").read_bytes()
    uploads_before = list(api.uploads)
    successes_before = telemetry.uploads_succeeded

    with pytest.raises(ValueError, match="only .json and .ndjson"):
        telemetry.attach_artifact("private_rows", source, copy=True)

    assert not copied.exists()
    assert telemetry._artifacts == {}
    assert (run_dir / "run_manifest.json").read_bytes() == manifest_before
    assert api.uploads == uploads_before
    assert telemetry.uploads_succeeded == successes_before


def test_armenian_remote_staging_is_disabled_before_local_or_remote_mutation(
    tmp_path,
) -> None:
    api = FakeApi()
    run_dir = tmp_path / "am-run"

    with pytest.raises(ValueError, match="remote staging is disabled for Armenian"):
        StagingTelemetry(
            run_id="am-run",
            candidate_release_id="populace-am-2024-native-test",
            run_dir=run_dir,
            repo_id="alternate-owner/private-staging",
            api=api,
        )

    assert not run_dir.exists()
    assert api.uploads == []


@pytest.mark.parametrize(
    "filename",
    ("diagnostics.json", "diagnostics.ndjson", "diagnostics.JSON", ".ndjson"),
)
def test_staging_attachment_allows_json_telemetry(tmp_path, filename) -> None:
    telemetry = StagingTelemetry(
        run_id="run-json",
        candidate_release_id="populace-am-2024-native-test",
        run_dir=tmp_path / "run-json",
    )
    source = tmp_path / filename
    source.write_text("{}\n")

    telemetry.attach_artifact("diagnostics", source, copy=True)

    copied = telemetry.run_dir / source.name
    manifest = json.loads((telemetry.run_dir / "run_manifest.json").read_text())
    assert copied.read_text() == "{}\n"
    assert manifest["artifacts"]["diagnostics"]["path"] == source.name
