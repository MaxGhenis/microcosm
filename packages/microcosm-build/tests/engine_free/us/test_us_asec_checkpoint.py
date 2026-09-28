from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from microcosm.build.frame_checkpoint import write_frame_checkpoint
from microcosm.build.outer_stage_runtime import (
    OUTER_STAGE_CONTEXT_SCHEMA_VERSION,
    frame_identity,
)
from microcosm.build.serialization_dtypes import CANONICAL_STRING_DTYPE
from microcosm.build.us_runtime import (
    ASEC_RAW_STAGE_ARTIFACT_KIND,
    ASEC_RAW_STAGE_OPERATOR_STATUS,
    ASEC_RAW_STAGE_SCHEMA_VERSION,
    ASEC_RAW_STAGE_STAGE,
    PRE_ASSEMBLY_OPERATOR_OUTPUT_FAMILIES,
    assert_operator_free_source_frame,
    load_asec_pre_clone_checkpoint,
    load_asec_raw_stage_checkpoint,
    load_take_up_contract,
)
from microcosm.build.us_runtime.asec_checkpoint import (
    _validate_lkweeks_source_provenance,
)
from microcosm.build.us_runtime.education_assistance_source import (
    ASEC_EDUCATION_ASSISTANCE_ARCHIVES,
)
from microcosm.build.us_runtime.spm_role_source import NATIVE_SPM_ROLE
from microcosm.frame import US_SCHEMA, EntitySchema, Frame, WeightKind, Weights

_OUTER_STAGE_ARTIFACT_KIND = "populace_outer_stage_frame"


def _us_frame(
    *,
    id_offset: int = 0,
    household_weights: tuple[float, float] = (2.0, 3.0),
    include_age: bool = True,
    person_weights: bool = False,
) -> Frame:
    ids = np.asarray([1, 2], dtype=np.int64) + id_offset
    person = pd.DataFrame(
        {
            "person_id": ids,
            "person_household_id": ids,
            "person_tax_unit_id": ids + 10,
            "person_spm_unit_id": ids + 20,
            "person_family_id": ids + 30,
            "person_marital_unit_id": ids + 40,
        }
    )
    if include_age:
        person["age"] = np.asarray([30, 50], dtype=np.int16)
    tables = {
        "person": person,
        "household": pd.DataFrame({"household_id": ids}),
        "tax_unit": pd.DataFrame({"tax_unit_id": ids + 10}),
        "spm_unit": pd.DataFrame({"spm_unit_id": ids + 20}),
        "family": pd.DataFrame({"family_id": ids + 30}),
        "marital_unit": pd.DataFrame({"marital_unit_id": ids + 40}),
    }
    weights = {
        "household": Weights(
            np.asarray(household_weights, dtype=np.float64),
            WeightKind.DESIGN,
        )
    }
    if person_weights:
        weights["person"] = Weights(
            np.asarray([2.0, 3.0], dtype=np.float64),
            WeightKind.DESIGN,
        )
    return Frame(
        tables,
        US_SCHEMA,
        weights,
        pd.Series(["asec_2023", "asec_2024"], dtype=object),
    )


def _non_us_frame() -> Frame:
    schema = EntitySchema(group_entities=("household",))
    return Frame(
        {
            "person": pd.DataFrame(
                {
                    "person_id": np.asarray([1], dtype=np.int64),
                    "person_household_id": np.asarray([1], dtype=np.int64),
                }
            ),
            "household": pd.DataFrame(
                {"household_id": np.asarray([1], dtype=np.int64)}
            ),
        },
        schema,
        {
            "household": Weights(
                np.asarray([1.0], dtype=np.float64),
                WeightKind.DESIGN,
            )
        },
        pd.Series(["fixture"], dtype=object),
    )


def _binding(frame: Frame) -> dict[str, object]:
    return {
        "artifact_kind": _OUTER_STAGE_ARTIFACT_KIND,
        "identity": frame_identity(frame).to_payload(),
        "pipeline_sha256": "a" * 64,
        "schema_version": OUTER_STAGE_CONTEXT_SCHEMA_VERSION,
        "stage": "pre_clone_enrichment",
        "stage_index": 1,
    }


def _raw_binding(frame: Frame) -> dict[str, object]:
    pin = {
        "income_year": 2022,
        "locator": "https://example.test/asec.zip",
        "member": "pppub.csv",
        "member_sha256": "b" * 64,
        "sha256": "a" * 64,
    }
    return {
        "artifact_kind": ASEC_RAW_STAGE_ARTIFACT_KIND,
        "identity": frame_identity(frame).to_payload(),
        "operator_status": ASEC_RAW_STAGE_OPERATOR_STATUS,
        "pipeline_sha256": "c" * 64,
        "raw_source_mappings": {
            column: {
                "audit": {"rows": 2},
                "column": column,
                "entity": "person",
                "join_keys": ["source_year", "PERIDNUM"],
                "operation": "exact_source_join",
                "source_pins": [pin],
            }
            for column in ("ED_VAL", "LKWEEKS", "PAW_TYP")
        },
        "schema_version": ASEC_RAW_STAGE_SCHEMA_VERSION,
        "source_construction_identity": frame_identity(frame).to_payload(),
        "source_receipt": {
            "kind": "pooled_asec",
            "sources": [
                {
                    "max_households": None,
                    "path": "/raw/asec_2022.h5",
                    "sha256": "d" * 64,
                    "share": 1.0,
                    "year": 2022,
                }
            ],
            "target_year": 2022,
        },
        "stage": ASEC_RAW_STAGE_STAGE,
    }


def _raw_us_frame(
    *,
    id_offset: int = 0,
    years: tuple[int, int] = (2022, 2023),
) -> Frame:
    source = _us_frame(id_offset=id_offset, include_age=False)
    tables = {entity: source.table(entity).copy() for entity in source.entities}
    tables["person"]["source_year"] = list(years)
    tables["person"]["PERIDNUM"] = [
        "0000000000000000000001",
        "0000000000000000000002",
    ]
    tables["person"]["ED_VAL"] = [0.0, 500.0]
    tables["person"]["LKWEEKS"] = [-1, 12]
    tables["person"]["PAW_TYP"] = np.asarray([0, 1], dtype=np.int64)
    return Frame(
        tables,
        source.schema,
        {entity: source.weights_for(entity) for entity in source.weighted_entities},
        source.strata,
    )


def _write_checkpoint(
    path: Path,
    frame: Frame,
    *,
    metadata: dict[str, object] | None = None,
) -> None:
    write_frame_checkpoint(path, frame, metadata=metadata or _binding(frame))


def test_loads_bound_input_complete_asec_checkpoint(tmp_path: Path) -> None:
    path = tmp_path / "001_pre_clone_enrichment.frame.h5"
    source = _us_frame()
    expected_metadata = _binding(source)
    _write_checkpoint(path, source, metadata=expected_metadata)

    frame, metadata = load_asec_pre_clone_checkpoint(path)

    assert frame_identity(frame) == frame_identity(source)
    assert frame.schema == US_SCHEMA
    assert frame.weighted_entities == ("household",)
    assert metadata == expected_metadata
    assert json.loads(json.dumps(metadata)) == metadata


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("artifact_kind", "other", "not an outer-stage Frame artifact"),
        ("schema_version", 999, "unsupported outer-stage schema version"),
        ("stage", "source_construction", "must be bound to stage"),
        ("stage_index", 0, "must be bound to stage_index 1"),
        ("pipeline_sha256", "not-a-digest", "lowercase SHA-256 digest"),
    ),
)
def test_rejects_wrong_outer_stage_binding(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    path = tmp_path / f"wrong-{field}.frame.h5"
    frame = _us_frame()
    metadata = _binding(frame)
    metadata[field] = value
    _write_checkpoint(path, frame, metadata=metadata)

    with pytest.raises(ValueError, match=message):
        load_asec_pre_clone_checkpoint(path)


def test_loads_operator_untouched_raw_stage_checkpoint(tmp_path: Path) -> None:
    path = tmp_path / "asec_raw_stage.checkpoint.h5"
    source = _raw_us_frame()
    metadata = _raw_binding(source)
    _write_checkpoint(path, source, metadata=metadata)

    frame, loaded_metadata = load_asec_raw_stage_checkpoint(path)

    assert frame_identity(frame) == frame_identity(source)
    assert loaded_metadata == metadata
    assert loaded_metadata["artifact_kind"] == ASEC_RAW_STAGE_ARTIFACT_KIND
    assert loaded_metadata["stage"] == ASEC_RAW_STAGE_STAGE
    assert loaded_metadata["operator_status"] == ASEC_RAW_STAGE_OPERATOR_STATUS
    # The load is a declared string-storage canonicalization boundary: no
    # entity may leak a non-canonical pandas string dtype downstream,
    # whatever storage the checkpoint was written under.
    for entity in frame.entities:
        for column, dtype in frame.table(entity).dtypes.items():
            if isinstance(dtype, pd.StringDtype):
                assert dtype == CANONICAL_STRING_DTYPE, (entity, column)


@pytest.mark.parametrize(
    "column",
    ("ED_VAL", "LKWEEKS", "PAW_TYP", "PERIDNUM", "source_year"),
)
def test_raw_loader_rejects_missing_input_complete_source_column(
    tmp_path: Path,
    column: str,
) -> None:
    source = _raw_us_frame()
    tables = {entity: source.table(entity).copy() for entity in source.entities}
    tables["person"] = tables["person"].drop(columns=[column])
    incomplete = Frame(
        tables,
        source.schema,
        {entity: source.weights_for(entity) for entity in source.weighted_entities},
        source.strata,
    )
    path = tmp_path / f"raw-missing-{column}.checkpoint.h5"
    _write_checkpoint(path, incomplete, metadata=_raw_binding(incomplete))

    with pytest.raises(ValueError, match=rf"input-complete.*{column}"):
        load_asec_raw_stage_checkpoint(path)


@pytest.mark.parametrize(
    ("column", "values", "message"),
    (
        ("source_year", [2022, np.nan], "source_year must be complete"),
        ("PERIDNUM", ["0000000000000000000001", ""], "PERIDNUM must be complete"),
        ("ED_VAL", [0.0, np.nan], "ED_VAL must be complete"),
        ("LKWEEKS", [-1, 53], "LKWEEKS must be complete"),
        ("PAW_TYP", [0, 4], "PAW_TYP must be complete integers"),
    ),
)
def test_raw_loader_rejects_invalid_input_complete_source_values(
    tmp_path: Path,
    column: str,
    values: list[object],
    message: str,
) -> None:
    source = _raw_us_frame()
    tables = {entity: source.table(entity).copy() for entity in source.entities}
    tables["person"][column] = values
    invalid = Frame(
        tables,
        source.schema,
        {entity: source.weights_for(entity) for entity in source.weighted_entities},
        source.strata,
    )
    path = tmp_path / f"raw-invalid-{column}.checkpoint.h5"
    _write_checkpoint(path, invalid, metadata=_raw_binding(invalid))

    with pytest.raises(ValueError, match=message):
        load_asec_raw_stage_checkpoint(path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("artifact_kind", _OUTER_STAGE_ARTIFACT_KIND, "not a dedicated raw-stage"),
        ("schema_version", 999, "unsupported raw-stage schema version"),
        ("stage", "pre_clone_enrichment", "must be bound to stage"),
        ("operator_status", "operator_enriched", "must declare operator_status"),
        ("pipeline_sha256", "not-a-digest", "lowercase SHA-256 digest"),
    ),
)
def test_raw_loader_rejects_wrong_artifact_binding(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    path = tmp_path / f"raw-wrong-{field}.checkpoint.h5"
    frame = _raw_us_frame()
    metadata = _raw_binding(frame)
    metadata[field] = value
    _write_checkpoint(path, frame, metadata=metadata)

    with pytest.raises(ValueError, match=message):
        load_asec_raw_stage_checkpoint(path)


def test_raw_loader_rejects_legacy_enriched_checkpoint(tmp_path: Path) -> None:
    path = tmp_path / "001_pre_clone_enrichment.frame.h5"
    frame = _us_frame()
    _write_checkpoint(path, frame, metadata=_binding(frame))

    with pytest.raises(ValueError, match="incomplete raw-stage artifact binding"):
        load_asec_raw_stage_checkpoint(path)


def test_raw_loader_rejects_identity_not_bound_to_frame(tmp_path: Path) -> None:
    path = tmp_path / "raw-wrong-identity.checkpoint.h5"
    frame = _raw_us_frame()
    metadata = _raw_binding(frame)
    metadata["identity"] = frame_identity(_raw_us_frame(id_offset=100)).to_payload()
    _write_checkpoint(path, frame, metadata=metadata)

    with pytest.raises(ValueError, match="Frame identity changed"):
        load_asec_raw_stage_checkpoint(path)


def test_raw_loader_rejects_wrong_source_construction_identity(
    tmp_path: Path,
) -> None:
    path = tmp_path / "raw-wrong-source-identity.checkpoint.h5"
    frame = _raw_us_frame()
    metadata = _raw_binding(frame)
    metadata["source_construction_identity"] = frame_identity(
        _raw_us_frame(id_offset=100)
    ).to_payload()
    _write_checkpoint(path, frame, metadata=metadata)

    with pytest.raises(ValueError, match="source-construction structural identity"):
        load_asec_raw_stage_checkpoint(path)


_OPERATOR_OUTPUT_CASES = tuple(
    (family, entity, column)
    for family, by_entity in PRE_ASSEMBLY_OPERATOR_OUTPUT_FAMILIES.items()
    for entity, columns in by_entity.items()
    for column in sorted(columns)
)


def test_operator_boundary_enumerates_full_take_up_contract() -> None:
    expected: dict[str, set[str]] = {}
    for program in load_take_up_contract().programs:
        expected.setdefault(program.entity, set()).add(program.variable)

    assert PRE_ASSEMBLY_OPERATOR_OUTPUT_FAMILIES["take_up"] == {
        entity: frozenset(columns) for entity, columns in expected.items()
    }


def test_raw_loader_rejects_prefilled_spm_independence_role(tmp_path: Path) -> None:
    source = _raw_us_frame()
    tables = {entity: source.table(entity).copy() for entity in source.entities}
    # A nonconstant role would otherwise bypass the source stage's derivation.
    tables["person"][NATIVE_SPM_ROLE] = [True, False]
    contaminated = Frame(
        tables,
        source.schema,
        {entity: source.weights_for(entity) for entity in source.weighted_entities},
        source.strata,
    )
    path = tmp_path / "prefilled-spm-role.checkpoint.h5"
    _write_checkpoint(path, contaminated, metadata=_raw_binding(contaminated))

    with pytest.raises(ValueError, match="spm_independence_role:person"):
        load_asec_raw_stage_checkpoint(path)


def test_operator_boundary_accepts_only_receipted_acs_native_exception() -> None:
    source = _us_frame(include_age=False)
    tables = {entity: source.table(entity).copy() for entity in source.entities}
    tables["person"]["AGEP"] = [30, 50]
    tables["person"]["age"] = [30, 50]
    acs = Frame(
        tables,
        source.schema,
        {entity: source.weights_for(entity) for entity in source.weighted_entities},
        source.strata,
    )
    receipt = {
        "age": {
            "entity": "person",
            "source_columns": ["AGEP"],
            "transformation": "identity",
            "provenance": "acs_2024_1yr_native",
            "observed_rows": 2,
            "missing_rows": 0,
        }
    }

    assert_operator_free_source_frame(
        acs,
        label="ACS fixture",
        native_inputs=receipt,
    )
    with pytest.raises(ValueError, match="canonical operator output"):
        assert_operator_free_source_frame(acs, label="unreceipted ACS fixture")

    malformed = {"age": {**receipt["age"], "provenance": "fixture_allowlist"}}
    with pytest.raises(ValueError, match="provenance"):
        assert_operator_free_source_frame(
            acs,
            label="malformed ACS fixture",
            native_inputs=malformed,
        )


def test_operator_boundary_rejects_forged_native_receipt_for_operator_output() -> None:
    source = _us_frame(include_age=False)
    tables = {entity: source.table(entity).copy() for entity in source.entities}
    tables["person"]["AGEP"] = [30, 50]
    tables["person"]["takes_up_wic_if_eligible"] = [True, False]
    forged = Frame(
        tables,
        source.schema,
        {entity: source.weights_for(entity) for entity in source.weighted_entities},
        source.strata,
    )
    forged_receipt = {
        "takes_up_wic_if_eligible": {
            "entity": "person",
            "source_columns": ["AGEP"],
            "transformation": "identity",
            "provenance": "acs_2024_1yr_native",
            "observed_rows": 2,
            "missing_rows": 0,
        }
    }

    with pytest.raises(ValueError, match="not a declared ACS native mapping"):
        assert_operator_free_source_frame(
            forged,
            label="forged ACS fixture",
            native_inputs=forged_receipt,
        )


@pytest.mark.parametrize(
    ("family", "entity", "column"),
    _OPERATOR_OUTPUT_CASES,
)
def test_raw_loader_rejects_every_registered_operator_output(
    tmp_path: Path,
    family: str,
    entity: str,
    column: str,
) -> None:
    source = _raw_us_frame()
    tables = {
        table_entity: source.table(table_entity).copy()
        for table_entity in source.entities
    }
    tables[entity][column] = 0
    contaminated = Frame(
        tables,
        source.schema,
        {
            weighted_entity: source.weights_for(weighted_entity)
            for weighted_entity in source.weighted_entities
        },
        source.strata,
    )
    path = tmp_path / f"{family}-{entity}-{column}.checkpoint.h5"
    _write_checkpoint(path, contaminated, metadata=_raw_binding(contaminated))

    with pytest.raises(ValueError, match=rf"{family}:{entity}"):
        load_asec_raw_stage_checkpoint(path)


def test_rejects_incomplete_outer_stage_binding(tmp_path: Path) -> None:
    path = tmp_path / "missing-stage.frame.h5"
    frame = _us_frame()
    metadata = _binding(frame)
    del metadata["stage"]
    _write_checkpoint(path, frame, metadata=metadata)

    with pytest.raises(ValueError, match="incomplete outer-stage artifact binding"):
        load_asec_pre_clone_checkpoint(path)


def test_rejects_identity_not_bound_to_loaded_frame(tmp_path: Path) -> None:
    path = tmp_path / "wrong-identity.frame.h5"
    frame = _us_frame()
    metadata = _binding(frame)
    metadata["identity"] = frame_identity(_us_frame(id_offset=100)).to_payload()
    _write_checkpoint(path, frame, metadata=metadata)

    with pytest.raises(ValueError, match="Frame identity changed"):
        load_asec_pre_clone_checkpoint(path)


@pytest.mark.parametrize(
    ("frame", "message"),
    (
        (_non_us_frame(), "must use the US entity schema"),
        (_us_frame(person_weights=True), "must carry household weights only"),
        (
            _us_frame(household_weights=(2.0, 0.0)),
            "household weights must be strictly positive and finite",
        ),
    ),
)
def test_rejects_invalid_asec_frame_boundary(
    tmp_path: Path,
    frame: Frame,
    message: str,
) -> None:
    path = tmp_path / f"invalid-{len(list(tmp_path.iterdir()))}.frame.h5"
    _write_checkpoint(path, frame)

    with pytest.raises(ValueError, match=message):
        load_asec_pre_clone_checkpoint(path)


# -- LKWEEKS provenance: the sidecar only when 2022 is pooled ----------------
#
# Only income year 2022's processed H5 lacks LKWEEKS. A pool with 2022 binds the
# one income-2022 sidecar; a pool without it binds each pooled year's Census
# member, the pins ED_VAL binds, with an audit tied to the frame and receipt.


def _sidecar_pin() -> dict[str, object]:
    return {
        "income_year": 2022,
        "locator": (
            "https://www2.census.gov/programs-surveys/cps/datasets/2023/march/"
            "asecpub23csv.zip"
        ),
        "member": "pppub23.csv",
        "member_sha256": (
            "19b56537e50e7663f954361ef2bb5ce9cef8d9d45f156fe1a69a99b654198ffe"
        ),
        "sha256": "d2e000250782adfbdd7f29c82b66d866591a30f0d330496698ec19f9c784ce11",
    }


def _census_pin(year: int) -> dict[str, object]:
    archive = ASEC_EDUCATION_ASSISTANCE_ARCHIVES.get(year)
    if archive is None:
        digest = hashlib.sha256(f"member-{year}".encode()).hexdigest()
        return {
            "income_year": year,
            "locator": f"https://example.test/asecpub{year + 1}.zip",
            "member": f"pppub{year + 1}.csv",
            "member_sha256": digest,
            "sha256": hashlib.sha256(f"archive-{year}".encode()).hexdigest(),
        }
    return {
        "income_year": year,
        "locator": archive.zip_url,
        "member": archive.member,
        "member_sha256": archive.member_sha256,
        "sha256": archive.zip_sha256,
    }


def _h5_sha256(year: int) -> str:
    return hashlib.sha256(f"census_cps_{year}.h5".encode()).hexdigest()


def _per_year_provenance(
    person: pd.DataFrame,
    *,
    receipt_years: tuple[int, ...] | None = None,
) -> dict[str, object]:
    """The mappings and receipt the builder writes for a pool without 2022."""

    frame_years = sorted({int(year) for year in person["source_year"]})
    years = frame_years if receipt_years is None else sorted(receipt_years)
    mappings = {
        column: {
            "audit": {"rows": len(person)},
            "column": column,
            "entity": "person",
            "join_keys": ["source_year", "PERIDNUM"],
            "operation": "exact_source_join",
            "source_pins": [_census_pin(year) for year in years],
        }
        for column in ("ED_VAL", "LKWEEKS", "PAW_TYP")
    }
    audit = {}
    for year in years:
        values = person.loc[person["source_year"] == year, "LKWEEKS"].astype(int)
        audit[str(year)] = {
            "carried_h5_sha256": _h5_sha256(year),
            "maximum": int(values.max()) if len(values) else 0,
            "member_rows": int(len(values)) + 4,
            "minimum": int(values.min()) if len(values) else 0,
            "niu_rows": int(values.eq(-1).sum()),
            "positive_rows": int(values.gt(0).sum()),
            "rows": int(len(values)),
            "verified_rows": int(len(values)),
        }
    mappings["LKWEEKS"]["audit"] = audit
    return {
        "raw_source_mappings": mappings,
        "source_receipt": {
            "kind": "pooled_asec",
            "sources": [
                {
                    "max_households": None,
                    "path": f"/raw/asec_{year}.h5",
                    "sha256": _h5_sha256(year),
                    "share": 1.0 / len(years),
                    "year": year,
                }
                for year in years
            ],
            "target_year": 2024,
        },
    }


def _per_year_binding(
    frame: Frame,
    *,
    receipt_years: tuple[int, ...] | None = None,
) -> dict[str, object]:
    """The full raw-stage binding for a pool without income year 2022."""

    return {
        **_raw_binding(frame),
        **_per_year_provenance(frame.table("person"), receipt_years=receipt_years),
    }


class _PersonTable:
    """The only part of a Frame the provenance rule reads."""

    def __init__(self, years: list[int], weeks: list[int]) -> None:
        self._person = pd.DataFrame(
            {
                "source_year": np.asarray(years, dtype=np.int64),
                "LKWEEKS": np.asarray(weeks, dtype=np.int64),
            }
        )

    def table(self, entity: str) -> pd.DataFrame:
        assert entity == "person"
        return self._person


_TWO_PERSON_POOLS = (
    (2023,),
    (2024,),
    (2025,),
    (2023, 2024),
    (2023, 2025),
    (2024, 2025),
)


@pytest.mark.parametrize(
    "pool", _TWO_PERSON_POOLS, ids=["-".join(map(str, p)) for p in _TWO_PERSON_POOLS]
)
def test_raw_loader_accepts_a_per_year_lkweeks_join_without_2022(
    tmp_path: Path, pool: tuple[int, ...]
) -> None:
    path = tmp_path / "asec_raw_stage.checkpoint.h5"
    source = _raw_us_frame(years=(pool[0], pool[-1]))
    metadata = _per_year_binding(source)
    _write_checkpoint(path, source, metadata=metadata)

    _frame, loaded_metadata = load_asec_raw_stage_checkpoint(path)

    assert loaded_metadata == metadata
    lkweeks = loaded_metadata["raw_source_mappings"]["LKWEEKS"]
    assert [pin["income_year"] for pin in lkweeks["source_pins"]] == list(pool)


def test_raw_loader_rejects_the_income_2022_sidecar_for_a_pool_without_2022(
    tmp_path: Path,
) -> None:
    """The pre-change builder's 2022-free receipt claimed a join that filled nothing."""

    path = tmp_path / "asec_raw_stage.checkpoint.h5"
    source = _raw_us_frame(years=(2023, 2024))
    metadata = _per_year_binding(source)
    metadata["raw_source_mappings"]["LKWEEKS"]["source_pins"] = [_sidecar_pin()]
    _write_checkpoint(path, source, metadata=metadata)

    with pytest.raises(
        ValueError,
        match=r"names income year\(s\) \[2022\], but the artifact pools \[2023, 2024\]",
    ):
        load_asec_raw_stage_checkpoint(path)


def test_raw_loader_keeps_the_sidecar_shape_for_every_pool_with_2022(
    tmp_path: Path,
) -> None:
    for years, receipt in (((2022, 2022), (2022,)), ((2022, 2023), (2022, 2023))):
        path = tmp_path / f"raw-{'-'.join(map(str, receipt))}.checkpoint.h5"
        source = _raw_us_frame(years=years)
        metadata = _raw_binding(source)
        metadata["raw_source_mappings"]["LKWEEKS"]["source_pins"] = [_sidecar_pin()]
        metadata["source_receipt"]["sources"] = [
            {**metadata["source_receipt"]["sources"][0], "year": year}
            for year in receipt
        ]
        _write_checkpoint(path, source, metadata=metadata)
        _frame, loaded = load_asec_raw_stage_checkpoint(path)
        assert loaded["raw_source_mappings"]["LKWEEKS"]["source_pins"] == [
            _sidecar_pin()
        ]


def _mutate(path: tuple, value):
    def apply(metadata: dict[str, object]) -> None:
        target = metadata
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return apply


_LKWEEKS = ("raw_source_mappings", "LKWEEKS")
_AUDIT_2023 = (*_LKWEEKS, "audit", "2023")


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            _mutate((*_LKWEEKS, "source_pins"), [_census_pin(2023)]),
            r"names income year\(s\) \[2023\], but the artifact pools \[2023, 2024\]",
        ),
        (
            _mutate((*_LKWEEKS, "source_pins"), [_census_pin(2024), _census_pin(2023)]),
            "in year order",
        ),
        (
            _mutate(
                (*_LKWEEKS, "source_pins"),
                [_census_pin(2023), _census_pin(2023), _census_pin(2024)],
            ),
            "names an income year more than once",
        ),
        (
            _mutate(
                (*_LKWEEKS, "source_pins"),
                [{**_census_pin(2023), "member": "pppub23.csv"}, _census_pin(2024)],
            ),
            "pin for income year 2023 is not the Census member pin",
        ),
        (
            _mutate((*_LKWEEKS, "audit"), {"2023": {}}),
            "audit must have one entry per pooled income year",
        ),
        (
            _mutate((*_AUDIT_2023, "extra"), 1),
            "audit for income year 2023 is malformed",
        ),
        (_mutate((*_AUDIT_2023, "rows"), True), "must record integer counts"),
        (_mutate((*_AUDIT_2023, "rows"), 1.0), "must record integer counts"),
        (_mutate((*_AUDIT_2023, "rows"), 2), r"differs on \['rows'\]"),
        (
            _mutate((*_AUDIT_2023, "verified_rows"), 0),
            r"differs on \['verified_rows'\]",
        ),
        (
            _mutate((*_AUDIT_2023, "carried_h5_sha256"), "0" * 64),
            r"differs on \['carried_h5_sha256'\]",
        ),
        (_mutate((*_AUDIT_2023, "maximum"), 52), r"differs on \['maximum'\]"),
        (
            _mutate((*_AUDIT_2023, "positive_rows"), 1),
            r"differs on \['positive_rows'\]",
        ),
        (_mutate((*_AUDIT_2023, "member_rows"), 0), "fewer Census member persons"),
    ],
    ids=[
        "missing-year",
        "out-of-order",
        "repeated-year",
        "relabelled-member",
        "audit-years",
        "audit-extra-key",
        "audit-boolean",
        "audit-float",
        "audit-rows",
        "audit-verified",
        "audit-h5",
        "audit-maximum",
        "audit-positive",
        "audit-member-rows",
    ],
)
def test_raw_loader_rejects_a_mislabelled_per_year_lkweeks_join(
    tmp_path: Path, mutate, message: str
) -> None:
    path = tmp_path / "asec_raw_stage.checkpoint.h5"
    source = _raw_us_frame(years=(2023, 2024))
    metadata = _per_year_binding(source)
    mutate(metadata)
    _write_checkpoint(path, source, metadata=metadata)

    with pytest.raises(ValueError, match=message):
        load_asec_raw_stage_checkpoint(path)


def test_raw_loader_rejects_per_year_pins_for_a_pool_with_2022(tmp_path: Path) -> None:
    path = tmp_path / "asec_raw_stage.checkpoint.h5"
    source = _raw_us_frame(years=(2022, 2023))
    metadata = _per_year_binding(source)
    _write_checkpoint(path, source, metadata=metadata)

    with pytest.raises(ValueError, match="must bind only the income-2022 sidecar"):
        load_asec_raw_stage_checkpoint(path)


def test_raw_loader_rejects_frame_years_the_receipt_does_not_pool(
    tmp_path: Path,
) -> None:
    path = tmp_path / "asec_raw_stage.checkpoint.h5"
    source = _raw_us_frame(years=(2023, 2024))
    metadata = _per_year_binding(source, receipt_years=(2023, 2025))
    _write_checkpoint(path, source, metadata=metadata)

    with pytest.raises(
        ValueError,
        match=r"frame holds source_year \[2023, 2024\] but its source_receipt pools",
    ):
        load_asec_raw_stage_checkpoint(path)


@st.composite
def _per_year_pools(draw):
    years = sorted(
        draw(
            st.sets(
                st.integers(min_value=2000, max_value=2100).filter(
                    lambda year: year != 2022
                ),
                min_size=1,
                max_size=5,
            )
        )
    )
    rows = []
    for year in years:
        count = draw(st.integers(min_value=1, max_value=6))
        rows += [
            (year, draw(st.integers(min_value=-1, max_value=52))) for _ in range(count)
        ]
    rows = draw(st.permutations(rows))
    return _PersonTable([year for year, _ in rows], [weeks for _, weeks in rows])


@settings(max_examples=200, deadline=None)
@given(frame=_per_year_pools(), data=st.data())
def test_per_year_lkweeks_rule_accepts_exactly_the_builder_shape(frame, data) -> None:
    """For any pool without 2022: the builder's binding passes, and any one
    corruption of an audit entry, a pin, or the pin order is refused."""

    metadata = _per_year_provenance(frame.table("person"))
    _validate_lkweeks_source_provenance(frame, metadata, path=Path("fixture"))

    audit = metadata["raw_source_mappings"]["LKWEEKS"]["audit"]
    year = data.draw(st.sampled_from(sorted(audit)))
    key = data.draw(st.sampled_from(sorted(audit[year])))
    if key == "carried_h5_sha256":
        audit[year][key] = "0" * 64
    elif key == "member_rows":
        audit[year][key] = audit[year]["rows"] - 1
    else:
        audit[year][key] += data.draw(st.sampled_from([-1, 1]))
    with pytest.raises(ValueError):
        _validate_lkweeks_source_provenance(frame, metadata, path=Path("fixture"))

    metadata = _per_year_provenance(frame.table("person"))
    pins = metadata["raw_source_mappings"]["LKWEEKS"]["source_pins"]
    corruption = data.draw(st.sampled_from(["sidecar", "field", "drop", "swap"]))
    if corruption == "swap" and len(pins) < 2:
        corruption = "field"
    if corruption == "sidecar":
        pins.append(_sidecar_pin())
    elif corruption == "field":
        index = data.draw(st.integers(min_value=0, max_value=len(pins) - 1))
        pins[index] = {**pins[index], "member_sha256": "0" * 64}
    elif corruption == "drop":
        pins.pop()
    else:
        pins[0], pins[1] = pins[1], pins[0]
    with pytest.raises(ValueError):
        _validate_lkweeks_source_provenance(frame, metadata, path=Path("fixture"))
