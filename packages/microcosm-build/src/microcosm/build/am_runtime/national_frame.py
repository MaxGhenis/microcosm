"""Armenia's two-entity national Frame carrier and staging-H5 boundary."""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from microcosm.frame import (
    EntitySchema,
    Frame,
    MassChangeRecord,
    WeightKind,
    Weights,
    engine_tables,
    put_frame_table,
    read_frame_table,
)

__all__ = [
    "AM_EXPORTED_WEIGHT_COLUMNS",
    "AM_HOUSEHOLD_WEIGHT_KIND_ATTR",
    "AM_MASS_LOG_ATTR",
    "AM_NATIONAL_H5_TABLES",
    "AM_NATIONAL_SCHEMA",
    "AM_TIME_PERIOD_METADATA_KEY",
    "AMStagingProvenance",
    "am_household_weight_kind",
    "am_national_frame",
    "am_time_period",
    "load_am_national_frame",
    "validate_am_national_frame",
    "write_am_national_frame",
]

AM_NATIONAL_SCHEMA = EntitySchema(group_entities=("household",))
AM_TIME_PERIOD_METADATA_KEY = "time_period"
AM_NATIONAL_H5_TABLES = ("person", "household", "time_period")
AM_HOUSEHOLD_WEIGHT_KIND_ATTR = "microcosm_am_household_weight_kind"
AM_MASS_LOG_ATTR = "microcosm_am_mass_log_json"
AM_EXPORTED_WEIGHT_COLUMNS = frozenset({"household_weight"})


@dataclass(frozen=True)
class _AMSourceFileFingerprint:
    device: int
    inode: int
    size_bytes: int
    modified_ns: int
    changed_ns: int


@dataclass(frozen=True)
class AMStagingProvenance:
    """Local file identity kept beside a loaded Armenian Frame."""

    source_h5: Path
    fingerprint: _AMSourceFileFingerprint


def _source_file_fingerprint(path: Path) -> _AMSourceFileFingerprint:
    stat = path.stat()
    return _AMSourceFileFingerprint(
        device=stat.st_dev,
        inode=stat.st_ino,
        size_bytes=stat.st_size,
        modified_ns=stat.st_mtime_ns,
        changed_ns=stat.st_ctime_ns,
    )


def _mass_record_payload(record: MassChangeRecord) -> dict[str, object]:
    return {
        "entity": record.entity,
        "old_total": record.old_total,
        "new_total": record.new_total,
        "declared_factor": record.declared_factor,
        "reason": record.reason,
    }


def _mass_log_from_stored(value: object) -> tuple[MassChangeRecord, ...]:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise ValueError("Stored Armenian mass log is not valid JSON.") from exc
    if not isinstance(payload, list):
        raise ValueError("Stored Armenian mass log must be a JSON list.")
    records: list[MassChangeRecord] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("Stored Armenian mass-log entries must be objects.")
        try:
            records.append(
                MassChangeRecord(
                    entity=str(entry["entity"]),
                    old_total=float(entry["old_total"]),
                    new_total=float(entry["new_total"]),
                    declared_factor=(
                        None
                        if entry.get("declared_factor") is None
                        else float(entry["declared_factor"])
                    ),
                    reason=str(entry["reason"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Stored Armenian mass-log entry is malformed.") from exc
    return tuple(records)


def _weight_kind_from_stored(value: object) -> WeightKind:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    try:
        return WeightKind(str(value))
    except ValueError as exc:
        raise ValueError(
            f"Unknown stored Armenian household weight kind {value!r}."
        ) from exc


def _read_h5_metadata(path: Path) -> tuple[WeightKind, tuple[MassChangeRecord, ...]]:
    try:
        import h5py
    except ImportError as exc:  # pragma: no cover - optional AM runtime extra
        raise RuntimeError(
            "h5py is required to read Armenian staging metadata."
        ) from exc
    with h5py.File(path, mode="r") as file:
        missing = sorted(
            name
            for name in (AM_HOUSEHOLD_WEIGHT_KIND_ATTR, AM_MASS_LOG_ATTR)
            if name not in file.attrs
        )
        if missing:
            raise ValueError(
                f"Armenian staging H5 is missing metadata attribute(s): {missing}."
            )
        kind = _weight_kind_from_stored(file.attrs[AM_HOUSEHOLD_WEIGHT_KIND_ATTR])
        mass_log = _mass_log_from_stored(file.attrs[AM_MASS_LOG_ATTR])
    return kind, mass_log


def _write_h5_metadata(
    path: Path,
    *,
    weight_kind: WeightKind,
    mass_log: tuple[MassChangeRecord, ...],
) -> None:
    try:
        import h5py
    except ImportError as exc:  # pragma: no cover - optional AM runtime extra
        raise RuntimeError(
            "h5py is required to write Armenian staging metadata."
        ) from exc
    with h5py.File(path, mode="r+") as file:
        file.attrs[AM_HOUSEHOLD_WEIGHT_KIND_ATTR] = weight_kind.value
        file.attrs[AM_MASS_LOG_ATTR] = json.dumps(
            [_mass_record_payload(record) for record in mass_log],
            sort_keys=True,
            separators=(",", ":"),
        )


def am_national_frame(
    *,
    person: pd.DataFrame,
    household: pd.DataFrame,
    time_period: int | str,
    weight_kind: WeightKind = WeightKind.DESIGN,
    household_weights: Sequence[float] | np.ndarray | pd.Series | None = None,
    mass_log: tuple[MassChangeRecord, ...] = (),
) -> Frame:
    """Assemble Armenian person/household tables with typed household weights."""

    period = "" if time_period is None else str(time_period)
    if not period.strip():
        raise ValueError("Armenian national frame time_period must be non-empty.")
    if household_weights is None and "household_weight" not in household.columns:
        raise ValueError(
            "am_national_frame requires household_weights or a household_weight "
            "input column."
        )
    weight_values = (
        household_weights
        if household_weights is not None
        else household["household_weight"].to_numpy(dtype="float64")
    )
    weights = Weights(np.asarray(weight_values, dtype="float64"), weight_kind)
    carrier_household = household.drop(columns=["household_weight"], errors="ignore")
    return Frame(
        tables={"person": person, "household": carrier_household},
        schema=AM_NATIONAL_SCHEMA,
        weights={"household": weights},
        mass_log=mass_log,
        metadata={AM_TIME_PERIOD_METADATA_KEY: period},
    )


def am_time_period(frame: Frame) -> str:
    period = frame.metadata.get(AM_TIME_PERIOD_METADATA_KEY)
    if not isinstance(period, str) or not period.strip():
        raise ValueError("Armenian national frame time_period must be non-empty.")
    return period


def am_household_weight_kind(frame: Frame) -> WeightKind:
    return frame.weights_for("household").kind


def validate_am_national_frame(frame: Frame) -> None:
    """Revalidate kernel invariants plus the Armenian carrier contract."""

    if not isinstance(frame, Frame):
        raise TypeError("Armenian national stages must operate on Frame instances.")
    frame.revalidate()
    if tuple(frame.entities) != AM_NATIONAL_SCHEMA.entities:
        raise ValueError(
            f"Armenian national frame entities must be {AM_NATIONAL_SCHEMA.entities}; "
            f"got {tuple(frame.entities)}."
        )
    if tuple(frame.weighted_entities) != ("household",):
        raise ValueError("Armenian national frames carry household typed weights only.")
    if frame.schema.links:
        raise ValueError("Armenian national frames declare no link tables.")
    am_time_period(frame)
    reserved = sorted(
        AM_EXPORTED_WEIGHT_COLUMNS & set(frame.table("household").columns)
    )
    if reserved:
        raise ValueError(
            "Armenian national Frame carrier must not persist exported weight "
            f"column(s): {reserved}; use typed weights instead."
        )
    weights = frame.weights_for("household")
    household_records = [
        record for record in frame.mass_log if record.entity == "household"
    ]
    if household_records and not np.isclose(
        household_records[-1].new_total,
        weights.total,
        rtol=1e-9,
        atol=0.0,
    ):
        raise ValueError(
            "Armenian household weight total disagrees with the latest "
            "household MassChangeRecord."
        )


def write_am_national_frame(frame: Frame, path: str | Path) -> Path:
    """Atomically write a validated Armenian Frame as a local staging H5."""

    validate_am_national_frame(frame)
    output_path = Path(path)
    if output_path.suffix != ".h5":
        raise ValueError("Armenian national staging path must end with '.h5'.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(
        f".{output_path.name}.{uuid.uuid4().hex}.tmp.h5"
    )
    tables = engine_tables(frame, weighted_entities=("household",))
    try:
        with pd.HDFStore(temporary_path) as store:
            put_frame_table(
                store,
                "person",
                tables["person"],
                preferred_format="table",
                data_columns=True,
            )
            put_frame_table(
                store,
                "household",
                tables["household"],
                preferred_format="table",
                data_columns=True,
            )
            store.put(
                "time_period",
                pd.Series([am_time_period(frame)]),
                format="table",
                data_columns=True,
            )
        _write_h5_metadata(
            temporary_path,
            weight_kind=am_household_weight_kind(frame),
            mass_log=frame.mass_log,
        )
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return output_path


def load_am_national_frame(
    path: str | Path,
) -> tuple[Frame, AMStagingProvenance]:
    """Load a local Armenian staging H5 with a mid-read file-race guard."""

    requested = Path(path).expanduser()
    if requested.suffix != ".h5":
        raise ValueError("Armenian national dataset path must end with '.h5'.")
    input_path = requested.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Armenian national dataset not found: {input_path}.")
    before = _source_file_fingerprint(input_path)
    weight_kind, mass_log = _read_h5_metadata(input_path)
    with pd.HDFStore(input_path, mode="r") as store:
        keys = {key.lstrip("/") for key in store.keys()}
        missing = sorted(set(AM_NATIONAL_H5_TABLES) - keys)
        if missing:
            raise ValueError(
                f"Armenian national dataset is missing table(s): {missing}."
            )
        raw_period = store["time_period"]
        if len(raw_period) != 1:
            raise ValueError(
                "Armenian national dataset time_period must contain one value."
            )
        person = read_frame_table(store, "person")
        household = read_frame_table(store, "household")
        time_period = str(raw_period.iloc[0])
    after = _source_file_fingerprint(input_path)
    if after != before:
        raise RuntimeError(
            "Armenian national source H5 changed while being loaded; refusing "
            "mixed bytes."
        )
    frame = am_national_frame(
        person=person,
        household=household,
        time_period=time_period,
        weight_kind=weight_kind,
        mass_log=mass_log,
    )
    validate_am_national_frame(frame)
    return frame, AMStagingProvenance(input_path, after)
