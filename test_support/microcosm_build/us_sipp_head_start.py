"""Strict measured-SIPP Head Start take-up tests."""

# ruff: noqa: F401

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import microcosm.build.us_runtime.sipp_head_start as module
from microcosm.build.us_runtime.block_location import clone_frame_for_location
from microcosm.build.us_runtime.puf_support import clone_us_frame_for_puf_support
from microcosm.build.us_runtime.sipp_head_start import (
    HEAD_START_SIPP_DICTIONARY_URL,
    SIPP_2023_HEAD_START_DONOR_REVISION,
    SIPP_2023_HEAD_START_DONOR_SHA256,
    SIPP_2023_HEAD_START_DONOR_SIZE_BYTES,
    SIPP_2023_HEAD_START_DONOR_URL,
    SIPP_HEAD_START_FIT_PARAMETERS,
    SIPP_HEAD_START_MODEL_PREDICTORS,
    SIPP_HEAD_START_READ_PARAMETERS,
    SIPP_HEAD_START_SOURCE_COLUMNS,
    US_SIPP_HEAD_START_NONCONSTANT_PERSON_COLUMNS,
    US_SIPP_HEAD_START_OUTPUT_COLUMNS,
    US_SIPP_HEAD_START_REQUIRED_SOURCE_COLUMNS,
    US_SIPP_HEAD_START_STAGE_NAME,
    impute_us_sipp_head_start,
    load_sipp_2023_head_start_donor,
    us_sipp_head_start_signal_gate,
    us_sipp_head_start_summary,
    with_us_sipp_head_start_input,
)
from microcosm.build.us_runtime.support_provenance import location_clone_index_column
from microcosm.frame import US_SCHEMA, Frame, WeightKind, Weights

_OUTPUT = US_SIPP_HEAD_START_OUTPUT_COLUMNS[0]


def _load_tail_fixtures():
    path = Path(__file__).with_name("us_tail_clone_fixtures.py")
    spec = importlib.util.spec_from_file_location("us_tail_clone_fixtures", path)
    fixtures = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(fixtures)
    return fixtures


_TAIL = _load_tail_fixtures()


def _source_row(
    ssuid: str,
    pnum: int,
    *,
    month: int = 12,
    age: int = 4,
    head_start_status: int = 1,
    head_start_answer: float = 2.0,
    screen_status: int = 1,
    screen: float = 1.0,
    grade_status: int = 1,
    grade: float = 21.0,
    end_month_status: int = 1,
    end_month: float = 12.0,
    weight: float = 100.0,
) -> dict[str, object]:
    row: dict[str, object] = {column: 0.0 for column in SIPP_HEAD_START_SOURCE_COLUMNS}
    row.update(
        {
            "SSUID": ssuid,
            "PNUM": pnum,
            "MONTHCODE": month,
            "WPFINWGT": weight,
            "TAGE": age,
            "ESEX": 2 if pnum % 2 else 1,
            "EED_SCRNR": screen,
            "AED_SCRNR": screen_status,
            "EEDGRADE": grade,
            "AEDGRADE": grade_status,
            "EEDEMONTH": end_month,
            "AEDMONTH": end_month_status,
            "EEDHEADST": head_start_answer,
            "AEDHEADST": head_start_status,
        }
    )
    return row


def _write_source(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    path = tmp_path / "pu2023.csv"
    pd.DataFrame(rows, columns=SIPP_HEAD_START_SOURCE_COLUMNS).to_csv(
        path, sep="|", index=False
    )
    return path


def _donor() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "age": [3.0, 4.0, 5.0, 4.0],
            "is_female": [0.0, 1.0, 0.0, 1.0],
            "household_size": [2.0, 3.0, 4.0, 5.0],
            "count_under_18": [1.0, 2.0, 3.0, 4.0],
            "count_under_6": [1.0, 1.0, 2.0, 2.0],
            "household_employment_income": [0.0, 10_000.0, 20_000.0, 30_000.0],
            _OUTPUT: [False, True, False, True],
            "sipp_weight": [1.0, 2.0, 3.0, 4.0],
        }
    )


def _frame(
    source_ids: list[int],
    *,
    ages: list[int] | None = None,
    female: list[bool] | None = None,
    channels: list[str] | None = None,
    output: list[object] | None = None,
) -> Frame:
    n = len(source_ids)
    ids = np.arange(1, n + 1, dtype=np.int64)
    if ages is None:
        ages = [4] * n
    if female is None:
        female = [i % 2 == 0 for i in range(n)]
    person = pd.DataFrame(
        {
            "person_id": ids,
            "person_household_id": ids,
            "person_tax_unit_id": ids + 100,
            "person_spm_unit_id": ids + 200,
            "person_family_id": ids + 300,
            "person_marital_unit_id": ids + 400,
            "person_source_id": source_ids,
            "age": ages,
            "is_female": female,
            "employment_income_before_lsr": np.arange(n, dtype=np.float64) * 100.0,
        }
    )
    if channels is not None:
        person["person_support_channel"] = channels
    if output is not None:
        person[_OUTPUT] = output
    tables = {
        "person": person,
        "household": pd.DataFrame({"household_id": ids}),
        "tax_unit": pd.DataFrame({"tax_unit_id": ids + 100}),
        "spm_unit": pd.DataFrame({"spm_unit_id": ids + 200}),
        "family": pd.DataFrame({"family_id": ids + 300}),
        "marital_unit": pd.DataFrame({"marital_unit_id": ids + 400}),
    }
    return Frame(
        tables,
        US_SCHEMA,
        {"household": Weights(np.ones(n), WeightKind.DESIGN)},
    )


def _replace_person(frame: Frame, person: pd.DataFrame) -> Frame:
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    tables["person"] = person
    return Frame(
        tables,
        frame.schema,
        {entity: frame.weights_for(entity) for entity in frame.weighted_entities},
        frame.strata,
        mass_log=frame.mass_log,
    )


class _FakeQRF:
    instances: list[_FakeQRF] = []

    def __init__(self, *, n_estimators: int, seed: int) -> None:
        self.n_estimators = n_estimators
        self.seed = seed
        self.weights: object = None
        self.training: pd.DataFrame | None = None
        self.receiver: pd.DataFrame | None = None
        self.__class__.instances.append(self)

    def fit(
        self,
        training: pd.DataFrame,
        *,
        predictors: list[str],
        targets: list[str],
        weights: object,
    ) -> _FakeQRF:
        assert predictors == list(SIPP_HEAD_START_MODEL_PREDICTORS)
        assert targets == [_OUTPUT]
        self.training = training.copy()
        self.weights = weights
        return self

    def predict(self, receiver: pd.DataFrame) -> pd.DataFrame:
        self.receiver = receiver.copy()
        return pd.DataFrame(
            {_OUTPUT: receiver["is_female"].to_numpy(dtype=bool)},
            index=receiver.index,
        )


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    _FakeQRF.instances.clear()




















def _historical_tail_frame() -> Frame:
    """A non-assembled PUF-support frame whose source 10 has a tail copy."""

    native = _frame(
        [10, 20, 30],
        ages=[4, 5, 40],
        female=[True, False, True],
    )
    native = _replace_person(
        native, native.table("person").drop(columns=["person_source_id"])
    )
    cloned = clone_us_frame_for_puf_support(native)
    tailed = _TAIL.with_capital_gains_tail_copies(cloned, [1])
    person = tailed.table("person").copy()
    # Source IDs are the pre-clone person IDs; restate them as the test's
    # source labels so assertions read in source-person terms.
    person["person_source_id"] = person["person_source_id"].map({1: 10, 2: 20, 3: 30})
    return _replace_person(tailed, person)


# Location clones (``block_location.clone_frame_for_location``). A location
# clone is a distinct copy of its source unit that differs only in location:
# it keeps the source ID and support clone index and gains this column.
_LOCATION_COLUMN = location_clone_index_column("person")


def _located(frame: Frame, clones: int) -> Frame:
    """Clone every household ``clones`` times; ``1`` returns ``frame`` itself."""

    return clone_frame_for_location(frame, clones)


def _with_location_column(frame: Frame, values: object) -> Frame:
    """``frame`` with ``person_location_clone_index`` set to ``values``."""

    person = frame.table("person").copy()
    person[_LOCATION_COLUMN] = values
    return _replace_person(frame, person)


def _real_qrf() -> type:
    from importlib import import_module

    return import_module("microcosm.fit").QRF


class _DrawOrderQRF(_FakeQRF):
    """A fake QRF whose decisions depend on every predictor and on draw order.

    Like the real QRF it draws one seeded uniform per receiver row in row
    order, so a changed canonical row set, row order or predictor value moves
    the output, while it stays cheap enough for property tests.
    """

    _LOADINGS = np.array([0.13, 0.29, 0.07, 0.11, 0.17, 1e-5])

    def predict(self, receiver: pd.DataFrame) -> pd.DataFrame:
        self.receiver = receiver.copy()
        values = receiver.loc[:, list(SIPP_HEAD_START_MODEL_PREDICTORS)].to_numpy(
            dtype=np.float64
        )
        score = values @ self._LOADINGS
        probability = score - np.floor(score)
        draws = np.random.default_rng(self.seed).random(len(receiver))
        return pd.DataFrame({_OUTPUT: draws < probability}, index=receiver.index)


def _support_population_frame(
    households: Sequence[Sequence[tuple[int, bool, float]]],
    *,
    tails: Sequence[int] = (),
    household_weights: Sequence[float] | None = None,
) -> Frame:
    """A historical PUF-support frame over multi-person households.

    Each household lists its members' ``(age, is_female, earnings)``. The
    production operator clones it into ASEC (clone index 0) and PUF-detail
    (1) support copies, and each 1-based source household in ``tails``
    gains a capital-gains own-tail copy (2), as a base built without a
    selection source carries them. ``person_source_id`` is the native
    person ID. Tax, SPM and family units are one per household; marital
    units one per person.
    """

    person_rows: list[dict[str, object]] = []
    for household_id, members in enumerate(households, start=1):
        for age, is_female, earnings in members:
            person_id = len(person_rows) + 1
            person_rows.append(
                {
                    "person_id": person_id,
                    "person_household_id": household_id,
                    "person_tax_unit_id": 1_000 + household_id,
                    "person_spm_unit_id": 2_000 + household_id,
                    "person_family_id": 3_000 + household_id,
                    "person_marital_unit_id": 4_000 + person_id,
                    "age": int(age),
                    "is_female": bool(is_female),
                    "employment_income_before_lsr": float(earnings),
                }
            )
    person = pd.DataFrame(person_rows)
    household_ids = np.arange(1, len(households) + 1, dtype=np.int64)
    if household_weights is None:
        household_weights = [1.0] * len(households)
    native = Frame(
        {
            "person": person,
            "household": pd.DataFrame({"household_id": household_ids}),
            "tax_unit": pd.DataFrame({"tax_unit_id": household_ids + 1_000}),
            "spm_unit": pd.DataFrame({"spm_unit_id": household_ids + 2_000}),
            "family": pd.DataFrame({"family_id": household_ids + 3_000}),
            "marital_unit": pd.DataFrame(
                {"marital_unit_id": person["person_id"].to_numpy() + 4_000}
            ),
        },
        US_SCHEMA,
        {
            "household": Weights(
                np.asarray(household_weights, dtype=np.float64), WeightKind.DESIGN
            )
        },
    )
    cloned = clone_us_frame_for_puf_support(native)
    return _TAIL.with_capital_gains_tail_copies(cloned, list(tails)) if tails else cloned


#: A fixed population for the K = 1 golden: seven age-3--5 source persons in
#: multi-person households of varied size and earnings, two with tail copies.
_GOLDEN_HOUSEHOLDS: tuple[tuple[tuple[int, bool, float], ...], ...] = (
    ((34, True, 42_000.0), (36, False, 18_000.0), (4, True, 0.0), (1, False, 0.0)),
    ((29, True, 0.0), (3, False, 0.0), (5, True, 0.0)),
    ((61, False, 55_000.0),),
    (
        (41, False, 9_500.0),
        (39, True, 12_000.0),
        (4, False, 0.0),
        (8, True, 0.0),
        (15, False, 0.0),
    ),
    ((22, True, 26_000.0), (5, False, 0.0)),
    ((45, True, 70_000.0), (3, True, 0.0), (3, False, 0.0)),
)
_GOLDEN_TAILS = (1, 4)
_GOLDEN_HOUSEHOLD_WEIGHTS = (120.0, 80.0, 200.0, 60.0, 150.0, 90.0)
_GOLDEN_QRF_SEED = 17
_GOLDEN_QRF_TREES = 8


def _golden_population_frame() -> Frame:
    return _support_population_frame(
        _GOLDEN_HOUSEHOLDS,
        tails=_GOLDEN_TAILS,
        household_weights=_GOLDEN_HOUSEHOLD_WEIGHTS,
    )


def _real_qrf_donor(rows: int = 48, *, seed: int = 20_260_930) -> pd.DataFrame:
    """A deterministic two-class donor for the real ``microcosm.fit.QRF``."""

    rng = np.random.default_rng(seed)
    household_size = rng.integers(2, 8, size=rows).astype(np.float64)
    count_under_18 = np.minimum(
        household_size - 1.0, rng.integers(1, 5, size=rows).astype(np.float64)
    )
    count_under_6 = np.minimum(
        count_under_18, rng.integers(1, 4, size=rows).astype(np.float64)
    )
    income = np.round(rng.uniform(0.0, 80_000.0, size=rows), -2)
    take_up = rng.random(rows) < np.where(income < 25_000.0, 0.6, 0.15)
    take_up[:2] = [True, False]
    return pd.DataFrame(
        {
            "age": rng.integers(3, 6, size=rows).astype(np.float64),
            "is_female": rng.integers(0, 2, size=rows).astype(np.float64),
            "household_size": household_size,
            "count_under_18": count_under_18,
            "count_under_6": count_under_6,
            "household_employment_income": income,
            _OUTPUT: take_up,
            "sipp_weight": np.round(rng.uniform(50.0, 500.0, size=rows), 3),
        }
    )


def _head_start_receipt_digest(frame: Frame, predicted: pd.Series) -> str:
    """SHA-256 of the canonical predictors, the output and the summary."""

    canonical, source_key, eligible = module._recipient_predictors(frame)
    person = frame.table("person").copy()
    person[_OUTPUT] = predicted.to_numpy(dtype=bool)
    summary = us_sipp_head_start_summary(_replace_person(frame, person))
    payload = {
        "canonical": {
            str(column): canonical[column].tolist() for column in canonical.columns
        },
        "source_key": [str(value) for value in source_key.tolist()],
        "eligible": [bool(value) for value in eligible.tolist()],
        "predicted": [bool(value) for value in predicted.tolist()],
        "summary": summary,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()

__all__ = [name for name in globals() if not name.startswith("__")]
