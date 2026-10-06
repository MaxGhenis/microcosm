"""The US release tool's stored-input gate and its register (microcosm#1026).

``microcosm.data.stored_inputs`` owns the rule and the reviewed register of
stored columns that are deliberately not policyengine-us variables. The data
shard depends on no other Microcosm shard, so it spells the register's names
itself; this file binds every entry to the producer definition it names. It
also pins the release tool's use of the rule: the batched pre-export gate over
the export frame's modeled stored tables, that model against the real writer
(``requires_us``), and the post-write check that the written H5 earns the
gate's verdict. Location-cloned exports (``block_location.
clone_frame_for_location`` with K > 1) are pinned as well: the gate passes
their six location-clone index columns and refuses nothing it would not
refuse at K = 1, and at K = 1 its reading matches a golden computed on the
tree before those register entries existed.
"""

from __future__ import annotations

# ruff: noqa: F401
import ast
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from microcosm.build.outer_stage_runtime import _POOLED_SOURCE_PROVENANCE_COLUMNS
from microcosm.build.us_runtime import acs_pums, acs_transfer
from microcosm.build.us_runtime import puf_capital_gains_tail as puf_tail
from microcosm.build.us_runtime.base_pool import spine_column
from microcosm.build.us_runtime.block_location import clone_frame_for_location
from microcosm.build.us_runtime.eligibility_inputs import (
    US_ELIGIBILITY_INPUTS_PARENT_ID_COLUMNS,
)
from microcosm.build.us_runtime.operator_boundary import _ACS_NATIVE_INPUT_CONTRACTS
from microcosm.build.us_runtime.support_provenance import (
    location_clone_index_column,
    spine_source_id_column,
    support_channel_column,
    support_clone_index_column,
    support_source_id_column,
)
from microcosm.data.stored_inputs import (
    _US_ENTITIES,
    US_STORED_NON_VARIABLE_COLUMNS,
    CertifiedEngine,
    h5_stored_tables,
    stored_input_failures,
)
from microcosm.frame import Frame, WeightKind, Weights
from microcosm.frame.units import (
    _TAX_UNIT_ROLE_COLUMN,
    TAX_UNIT_FILING_STATUS_COLUMN,
    US_SCHEMA,
)
from test_support.paths import paths_for

_TEST_PATHS = paths_for("microcosm-build")


def _load_builder_module():
    path = _TEST_PATHS.repository / "tools" / "build_us_fiscal_refresh_release.py"
    spec = importlib.util.spec_from_file_location(
        "build_us_fiscal_refresh_release", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder():
    return _load_builder_module()


def _engine(*variables: str) -> CertifiedEngine:
    return CertifiedEngine(
        label="policyengine-us 2.2.1", variables=frozenset(variables)
    )


_STRUCTURAL = (
    "person_id",
    "person_household_id",
    "person_tax_unit_id",
    "person_spm_unit_id",
    "person_family_id",
    "person_marital_unit_id",
    "household_id",
    "tax_unit_id",
    "spm_unit_id",
    "family_id",
    "marital_unit_id",
    "household_weight",
    "age",
    "takes_up_wic_if_eligible",
)


def _frame(**person_columns) -> Frame:
    """Two households, one person each, every US entity populated."""

    ids = np.asarray([1, 2], dtype=np.int64)
    person = pd.DataFrame(
        {
            "person_id": ids,
            "person_household_id": ids,
            "person_tax_unit_id": ids * 10,
            "person_spm_unit_id": ids * 100,
            "person_family_id": ids * 1_000,
            "person_marital_unit_id": ids * 10_000,
            "age": np.asarray([40, 70], dtype=np.int64),
            **person_columns,
        }
    )
    return Frame(
        {
            "person": person,
            "household": pd.DataFrame({"household_id": ids}),
            "tax_unit": pd.DataFrame({"tax_unit_id": ids * 10}),
            "spm_unit": pd.DataFrame({"spm_unit_id": ids * 100}),
            "family": pd.DataFrame({"family_id": ids * 1_000}),
            "marital_unit": pd.DataFrame({"marital_unit_id": ids * 10_000}),
        },
        US_SCHEMA,
        {"household": Weights(np.asarray([1_500.0, 2_500.0]), WeightKind.CALIBRATED)},
    )


# ---------------------------------------------------------------------------
# The register is bound to the producers it names
# ---------------------------------------------------------------------------


#: The ACS-native amounts microcosm.build.us_runtime.acs_inputs maps under an
#: acs_ name: the acs_ keys of its contract. None is a variable of the
#: installed engine (test_the_inputs_the_acs_native_reasons_name_are_engine_inputs).
_ACS_NATIVE_AMOUNTS = frozenset(
    column for column in _ACS_NATIVE_INPUT_CONTRACTS if column.startswith("acs_")
)


# ---------------------------------------------------------------------------
# The release tool's gate
# ---------------------------------------------------------------------------


def _post_write_check(builder, monkeypatch, tmp_path, written, pre_export):
    """The post-write check on an H5 whose stored tables are ``written``."""

    monkeypatch.setattr(builder, "installed_us_engine", lambda: _engine(*_STRUCTURAL))
    monkeypatch.setattr(builder, "h5_stored_tables", lambda path: written)
    return builder._written_stored_input_verdict_mismatch(
        tmp_path / "populace_us_2024.h5", pre_export
    )


_STALE = {"person": ("person_id", "would_claim_wic")}
_CLEAN = {"person": ("person_id", "takes_up_wic_if_eligible")}


# ---------------------------------------------------------------------------
# Location clones (block_location.clone_frame_for_location, K > 1)
# ---------------------------------------------------------------------------


#: The column location cloning writes on every US entity table, by the
#: build's own helper: the register must list exactly these.
_LOCATION_CLONE_COLUMNS = frozenset(
    location_clone_index_column(entity) for entity in US_SCHEMA.entities
)


def _canonical_sha256(payload) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _k1_gate_frames() -> dict[str, Frame]:
    """The K = 1 frames the gate golden reads: this file's ``_frame`` fixture
    bare, with a stale input, with the live input, and with support
    provenance plus a column outside the naming convention."""

    return {
        "plain": _frame(),
        "stale": _frame(would_claim_wic=[True, False], person_source_id=[7, 8]),
        "live": _frame(takes_up_wic_if_eligible=[True, False]),
        "provenance": _frame(
            person_source_id=[7, 8],
            person_support_channel=["asec", "puf_tax_detail"],
            person_support_clone_index=[0, 1],
            A_AGE=[40, 70],
        ),
    }


def _gate_readings(builder, frames) -> dict[str, dict]:
    """The Route A gate's reading of each frame: the modeled stored tables,
    the failure lines and the details, less the register digest (which a
    register change moves by design)."""

    readings = {}
    for name, frame in frames.items():
        failures, details = builder._stored_input_gate_failures(
            frame, stage="export frame"
        )
        readings[name] = {
            "stored": {
                entity: list(columns)
                for entity, columns in builder._export_stored_tables(frame).items()
            },
            "failures": failures,
            "details": {
                key: value
                for key, value in details.items()
                if key != "register_sha256"
            },
        }
    return readings


#: K = 1 golden: :func:`_canonical_sha256` of :func:`_gate_readings` over
#: :func:`_k1_gate_frames`, with ``installed_us_engine`` returning
#: ``_engine(*_STRUCTURAL)``. Computed by running these same helper bodies
#: against the tree before the location-clone register entries existed
#: (commit 4324432e5, "Location v1: address review round 2", with that
#: tree's release tool and fixtures). A K = 1 export stores no location
#: column, so the gate's reading must not move.
_K1_GATE_READINGS_SHA256 = (
    "89edf0ec75ee0492193dbcc30ec3ded73d9373f41d05b267205890fc03a991ab"
)


def _cloned_stored_tables(stored, clones: int) -> dict[str, tuple[str, ...]]:
    """The stored tables location cloning should yield from ``stored``: each
    entity's columns, then its location column when ``clones > 1``, then the
    household weight the writer materializes (which is not a frame column)."""

    expected = {}
    for entity, columns in stored.items():
        frame_columns = [column for column in columns if column != "household_weight"]
        if clones > 1:
            frame_columns.append(location_clone_index_column(entity))
        if "household_weight" in columns:
            frame_columns.append("household_weight")
        expected[entity] = tuple(frame_columns)
    return expected


def _households_frame(
    sizes, weights, person_columns: dict[str, list] | None = None
) -> Frame:
    """Households of the given sizes, one of each group entity per household.

    Household ``h`` (1-based) holds ``sizes[h - 1]`` people and one tax unit,
    SPM unit, family and marital unit, with ids ``h * 10`` to ``h * 10_000``
    as in :func:`_frame`. ``person_columns`` align with the person rows.
    """

    household = np.arange(1, len(sizes) + 1, dtype=np.int64)
    member = np.repeat(household, sizes)
    person = pd.DataFrame(
        {
            "person_id": np.arange(1, len(member) + 1, dtype=np.int64),
            "person_household_id": member,
            "person_tax_unit_id": member * 10,
            "person_spm_unit_id": member * 100,
            "person_family_id": member * 1_000,
            "person_marital_unit_id": member * 10_000,
            "age": np.full(len(member), 40, dtype=np.int64),
            **(person_columns or {}),
        }
    )
    return Frame(
        {
            "person": person,
            "household": pd.DataFrame({"household_id": household}),
            "tax_unit": pd.DataFrame({"tax_unit_id": household * 10}),
            "spm_unit": pd.DataFrame({"spm_unit_id": household * 100}),
            "family": pd.DataFrame({"family_id": household * 1_000}),
            "marital_unit": pd.DataFrame({"marital_unit_id": household * 10_000}),
        },
        US_SCHEMA,
        {
            "household": Weights(
                np.asarray(weights, dtype=np.float64), WeightKind.CALIBRATED
            )
        },
    )


#: Person columns the property draws from: a stale input, the live one,
#: registered support provenance, a column outside the naming convention and
#: an unregistered non-variable.
_PROPERTY_PERSON_COLUMNS = (
    "would_claim_wic",
    "takes_up_wic_if_eligible",
    "person_source_id",
    "person_support_clone_index",
    "A_AGE",
    "stale_input",
)


# ---------------------------------------------------------------------------
# Against the installed engine and the real writer
# ---------------------------------------------------------------------------


__all__ = [name for name in globals() if not name.startswith("__")]
