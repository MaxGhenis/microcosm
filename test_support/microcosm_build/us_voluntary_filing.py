"""Measured SIPP voluntary-filing source-stage tests."""

# ruff: noqa: F401

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import urllib.request
from collections.abc import Callable, Collection
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import microcosm.build.us_runtime.voluntary_filing as module
from microcosm.build.us_runtime.block_location import clone_frame_for_location
from microcosm.build.us_runtime.puf_support import clone_us_frame_for_puf_support
from microcosm.build.us_runtime.release_input_coverage import (
    us_release_reform_coverage_probes,
)
from microcosm.build.us_runtime.support_provenance import (
    location_clone_index_column,
)
from microcosm.build.us_runtime.voluntary_filing import (
    SIPP_2023_VOLUNTARY_FILING_DONOR_REVISION,
    SIPP_2023_VOLUNTARY_FILING_DONOR_SHA256,
    SIPP_2023_VOLUNTARY_FILING_DONOR_SIZE_BYTES,
    SIPP_2023_VOLUNTARY_FILING_DONOR_URL,
    SIPP_VOLUNTARY_FILING_MODEL_PREDICTORS,
    SIPP_VOLUNTARY_FILING_SOURCE_COLUMNS,
    US_VOLUNTARY_FILING_NONCONSTANT_TAX_UNIT_COLUMNS,
    US_VOLUNTARY_FILING_OUTPUT_COLUMNS,
    US_VOLUNTARY_FILING_STAGE_NAME,
    VOLUNTARY_FILING_ARCHIVED_DERIVATION_URL,
    VOLUNTARY_FILING_ARCHIVED_PARAMETERS_URL,
    VOLUNTARY_FILING_SIPP_DICTIONARY_URL,
    fetch_sipp_2023_voluntary_filing_donor,
    impute_us_voluntary_filing,
    load_sipp_2023_voluntary_filing_donor,
    us_voluntary_filing_signal_gate,
    us_voluntary_filing_stage_spec,
    us_voluntary_filing_summary,
    with_us_voluntary_filing_input,
)
from microcosm.frame import US_SCHEMA, Frame, WeightKind, Weights

_OUTPUT = US_VOLUNTARY_FILING_OUTPUT_COLUMNS[0]


def _load_tail_fixtures():
    path = Path(__file__).with_name("us_tail_clone_fixtures.py")
    spec = importlib.util.spec_from_file_location("us_tail_clone_fixtures", path)
    fixtures = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(fixtures)
    return fixtures


_TAIL = _load_tail_fixtures()


def _source_row(
    ssuid: int,
    pnum: int,
    *,
    month: int = 12,
    weight: float = 10.0,
    age: float = 40.0,
    sex: int = 1,
    spouse: float = np.nan,
    filing: float = 1.0,
    filing_status: int = 1,
    will_file: float = np.nan,
    will_file_status: int = 0,
    dependent: float = np.nan,
    monthly_wages: float = 1_000.0,
) -> dict[str, object]:
    row: dict[str, object] = {
        "SSUID": ssuid,
        "PNUM": pnum,
        "MONTHCODE": month,
        "WPFINWGT": weight,
        "TAGE": age,
        "ESEX": sex,
        "EPNSPOUSE": spouse,
        "AFILING": filing_status,
        "EFILING": filing,
        "AWILLFILE": will_file_status,
        "EWILLFILE": will_file,
        "EDEPCLM": dependent,
    }
    for job in range(1, 8):
        row[f"TJB{job}_MSUM"] = monthly_wages if job == 1 else 0.0
    return row


def _write_source(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    path = tmp_path / "pu2023.csv"
    pd.DataFrame(rows, columns=SIPP_VOLUNTARY_FILING_SOURCE_COLUMNS).to_csv(
        path, sep="|", index=False
    )
    return path


def _synthetic_source_rows() -> list[dict[str, object]]:
    return [
        # A non-December duplicate must not enter either target or predictors.
        _source_row(1, 101, month=11, monthly_wages=999_999.0),
        # Reciprocal spouses report the same filing target and collapse once.
        _source_row(1, 101, spouse=102, age=40, monthly_wages=1_000.0),
        _source_row(
            1,
            102,
            spouse=101,
            age=38,
            sex=2,
            monthly_wages=500.0,
        ),
        # Household context is counted before the filing-response filter.
        _source_row(
            1,
            103,
            age=10,
            filing=np.nan,
            filing_status=0,
            monthly_wages=0.0,
        ),
        # A directly reported no/not-planning response supplies the false class.
        _source_row(
            2,
            101,
            age=70,
            sex=2,
            filing=2,
            will_file=2,
            will_file_status=1,
            monthly_wages=200.0,
        ),
        # Claimed dependents are not standalone receiver tax units.
        _source_row(3, 101, age=21, dependent=1, monthly_wages=300.0),
        # Imputed filing and will-file answers are not measured targets.
        _source_row(4, 101, filing_status=2),
        _source_row(
            5,
            101,
            filing=2,
            will_file=1,
            will_file_status=2,
        ),
        # Invalid survey weights are excluded after source-unit construction.
        _source_row(6, 101, weight=0.0),
    ]


def _donor(n: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(918)
    income = rng.gamma(2.0, 18_000.0, n)
    target = (np.arange(n) % 4) != 0
    return pd.DataFrame(
        {
            "source_tax_unit_key": [f"unit:{i}" for i in range(n)],
            "employment_income": income,
            "reference_age": rng.integers(18, 90, n).astype(np.float64),
            "reference_is_female": rng.integers(0, 2, n).astype(np.float64),
            "reference_is_married": rng.integers(0, 2, n).astype(np.float64),
            "count_under_18": rng.integers(0, 5, n).astype(np.float64),
            _OUTPUT: target,
            "tax_unit_weight": rng.uniform(100.0, 2_000.0, n),
        }
    )


def _frame(n_households: int = 12) -> Frame:
    people: list[dict[str, object]] = []
    person_id = 1
    for household_id in range(1, n_households + 1):
        tax_unit_id = household_id + 100
        people.append(
            {
                "person_id": person_id,
                "person_household_id": household_id,
                "person_tax_unit_id": tax_unit_id,
                "person_spm_unit_id": household_id + 200,
                "person_family_id": household_id + 300,
                "person_marital_unit_id": household_id + 400,
                "age": float(25 + household_id % 50),
                "is_female": bool(household_id % 2),
                "tax_unit_role_input": "HEAD",
                "employment_income_before_lsr": float(household_id * 3_000),
                "A_LINENO": 1,
            }
        )
        person_id += 1
        if household_id % 3 == 0:
            people.append(
                {
                    "person_id": person_id,
                    "person_household_id": household_id,
                    "person_tax_unit_id": tax_unit_id,
                    "person_spm_unit_id": household_id + 200,
                    "person_family_id": household_id + 300,
                    "person_marital_unit_id": household_id + 400,
                    "age": float(22 + household_id % 40),
                    "is_female": not bool(household_id % 2),
                    "tax_unit_role_input": "SPOUSE",
                    "employment_income_before_lsr": 2_000.0,
                    "A_LINENO": 2,
                }
            )
            person_id += 1
        if household_id % 2 == 0:
            people.append(
                {
                    "person_id": person_id,
                    "person_household_id": household_id,
                    "person_tax_unit_id": tax_unit_id,
                    "person_spm_unit_id": household_id + 200,
                    "person_family_id": household_id + 300,
                    "person_marital_unit_id": household_id + 400,
                    "age": 8.0,
                    "is_female": False,
                    "tax_unit_role_input": "DEPENDENT",
                    "employment_income_before_lsr": 0.0,
                    "A_LINENO": 3,
                }
            )
            person_id += 1
    person = pd.DataFrame(people)
    household_ids = np.arange(1, n_households + 1, dtype=np.int64)
    tables = {
        "person": person,
        "household": pd.DataFrame({"household_id": household_ids}),
        "tax_unit": pd.DataFrame(
            {
                "tax_unit_id": household_ids + 100,
                "filing_status_input": np.where(
                    household_ids % 3 == 0, "JOINT", "SINGLE"
                ),
            }
        ),
        "spm_unit": pd.DataFrame({"spm_unit_id": household_ids + 200}),
        "family": pd.DataFrame({"family_id": household_ids + 300}),
        "marital_unit": pd.DataFrame({"marital_unit_id": household_ids + 400}),
    }
    return Frame(
        tables,
        US_SCHEMA,
        {"household": Weights(np.linspace(1.0, 2.0, n_households), WeightKind.DESIGN)},
    )


def _replace_tax_unit(frame: Frame, **columns: np.ndarray) -> Frame:
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    for column, values in columns.items():
        tables["tax_unit"][column] = values
    return Frame(
        tables,
        frame.schema,
        {entity: frame.weights_for(entity) for entity in frame.weighted_entities},
        frame.strata,
        mass_log=frame.mass_log,
    )
















class _ChunkedResponse(io.BytesIO):
    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return super().read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()












class _IncomeThresholdQRF:
    """Predict filing iff tax-unit wages reach 10,000; records the receiver."""

    receivers: list[pd.DataFrame] = []

    def __init__(self, **_kwargs: object) -> None:
        pass

    def fit(self, *_args: object, **_kwargs: object) -> _IncomeThresholdQRF:
        return self

    def predict(self, receiver: pd.DataFrame) -> pd.DataFrame:
        self.receivers.append(receiver.copy())
        return pd.DataFrame(
            {_OUTPUT: receiver["employment_income"].ge(10_000.0).to_numpy()},
            index=receiver.index,
        )


def _historical_tail_frame() -> Frame:
    """A non-assembled PUF-support frame with tail copies of units 3 and 6."""

    return _TAIL.with_capital_gains_tail_copies(
        clone_us_frame_for_puf_support(_frame(6)), [3, 6]
    )


def _divergent_tail_wages(frame: Frame) -> Frame:
    """Zero the tail copies' wages so a tail-row prediction would flip."""

    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    person = tables["person"]
    tail = person["person_support_clone_index"].eq(2)
    person.loc[tail, "employment_income_before_lsr"] = 0.0
    return Frame(
        tables,
        frame.schema,
        {entity: frame.weights_for(entity) for entity in frame.weighted_entities},
        frame.strata,
        mass_log=frame.mass_log,
    )












def _assembled_gate_frame(
    output: list[bool],
    *,
    channels: list[str] | None,
    clone_indices: list[int] | None = None,
) -> Frame:
    """Four tax units over source IDs [10, 10, 20, 20] with raw spine IDs."""

    columns: dict[str, np.ndarray] = {
        _OUTPUT: np.asarray(output),
        "tax_unit_source_id": np.asarray([10, 10, 20, 20]),
        "tax_unit_spine_source_id": np.asarray([10, 10, 20, 20]),
    }
    if channels is not None:
        columns["tax_unit_support_channel"] = np.asarray(channels, dtype=object)
    if clone_indices is not None:
        columns["tax_unit_support_clone_index"] = np.asarray(clone_indices)
    return _replace_tax_unit(_frame(4), **columns)


# --- Location clones -------------------------------------------------------
#
# ``block_location.clone_frame_for_location`` repeats every entity row K times
# (clones adjacent), remaps entity ids to ``id * K + k``, splits weights K ways
# and writes ``{entity}_location_clone_index``; source IDs and support clone
# indices are carried unchanged. These helpers pin that one decision per
# source unit fans out to every support and location copy.

_LOCATION_CLONE_COLUMN = location_clone_index_column("tax_unit")
_PERSON_LOCATION_CLONE_COLUMN = location_clone_index_column("person")


class _PositionalQRF:
    """Deterministic fake QRF whose draw depends on receiver row position.

    Filing is ``wages >= 10,000`` flipped on every third receiver row, so any
    change to the receiver's rows, order or predictor values moves the
    fanned-out output. It records each receiver it predicts.
    """

    receivers: list[pd.DataFrame] = []

    def __init__(self, **_kwargs: object) -> None:
        pass

    def fit(self, *_args: object, **_kwargs: object) -> _PositionalQRF:
        return self

    def predict(self, receiver: pd.DataFrame) -> pd.DataFrame:
        self.receivers.append(receiver.copy())
        wages = receiver["employment_income"].ge(10_000.0).to_numpy()
        flip = (np.arange(len(receiver)) % 3) == 1
        return pd.DataFrame({_OUTPUT: wages ^ flip}, index=receiver.index)


def _impute_with_fake_qrf(frame: Frame, qrf: type = _PositionalQRF) -> pd.Series:
    """Run the real imputer with ``qrf`` standing in for the fitted model."""

    qrf.receivers.clear()
    previous = module.QRF
    module.QRF = qrf
    try:
        return impute_us_voluntary_filing(frame, _donor(), seed=17, n_estimators=3)
    finally:
        module.QRF = previous


def _replace_person(
    frame: Frame,
    mask: np.ndarray | pd.Series,
    **columns: object,
) -> Frame:
    """Overwrite person ``columns`` on the ``mask`` rows."""

    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    rows = np.asarray(mask, dtype=bool)
    for column, value in columns.items():
        tables["person"].loc[rows, column] = value
    return Frame(
        tables,
        frame.schema,
        {entity: frame.weights_for(entity) for entity in frame.weighted_entities},
        frame.strata,
        mass_log=frame.mass_log,
    )


def _without_tax_units(frame: Frame, tax_unit_ids: Collection[int]) -> Frame:
    """Drop the persons (and so the groups) of ``tax_unit_ids``."""

    person = frame.table("person")
    return frame.select(~person["person_tax_unit_id"].isin(tax_unit_ids).to_numpy())


def _tax_unit_ids(frame: Frame, mask: pd.Series) -> list[int]:
    return frame.table("tax_unit").loc[mask, "tax_unit_id"].astype(int).tolist()


#: Existing fixtures covering every receiver and summary branch at K = 1:
#: historical support with tail copies (and with divergent tail wages), a
#: two-copy PUF-support frame, an unexpanded frame with and without source
#: IDs (IDs chosen so string order differs from numeric order), a
#: channel-only legacy table and an assembled table without native copies.
_K1_GOLDEN_FIXTURES: dict[str, Callable[[], Frame]] = {
    "historical_tail": lambda: _historical_tail_frame(),
    "historical_tail_divergent": lambda: _divergent_tail_wages(
        _historical_tail_frame()
    ),
    "puf_support": lambda: clone_us_frame_for_puf_support(_frame(10)),
    "unexpanded": lambda: _frame(12),
    "unexpanded_with_source": lambda: _replace_tax_unit(
        _frame(12), tax_unit_source_id=np.arange(12, dtype=np.int64) * 7 + 3
    ),
    "channel_only": lambda: _replace_tax_unit(
        _frame(4),
        tax_unit_source_id=np.asarray([10, 10, 20, 20]),
        tax_unit_support_channel=np.asarray(
            ["asec", "puf_tax_detail"] * 2, dtype=object
        ),
    ),
    "assembled": lambda: _replace_tax_unit(
        _frame(5),
        tax_unit_source_id=np.asarray([10, 10, 10, 20, 20]),
        tax_unit_spine_source_id=np.asarray([1, 1, 1, 2, 2]),
        tax_unit_support_channel=np.asarray(["acs"] * 5, dtype=object),
        tax_unit_support_clone_index=np.asarray([0, 1, 2, 1, 2]),
    ),
}

#: Fixtures with a ``tax_unit_source_id``: every one of them may be
#: location-cloned. ``unexpanded`` has none and is refused once cloned.
_SOURCE_KEYED_FIXTURES = tuple(
    name for name in _K1_GOLDEN_FIXTURES if name != "unexpanded"
)


def _k1_refusal_messages() -> dict[str, str]:
    """Today's K = 1 refusal texts, which location support must not move."""

    messages: dict[str, str] = {}
    tail = _historical_tail_frame()
    clone_index = tail.table("tax_unit")["tax_unit_support_clone_index"].to_numpy()
    duplicated_copy = _replace_tax_unit(
        tail,
        tax_unit_support_clone_index=np.where(clone_index == 2, 1, clone_index),
    )
    duplicated_source = _replace_tax_unit(
        _frame(4), tax_unit_source_id=np.asarray([10, 10, 20, 20])
    )
    duplicated_role = _replace_tax_unit(
        _frame(5),
        tax_unit_source_id=np.asarray([10, 10, 10, 20, 20]),
        tax_unit_support_channel=np.asarray(
            ["asec", "puf_tax_detail", "puf_tax_detail", "asec", "puf_tax_detail"],
            dtype=object,
        ),
        **{_OUTPUT: np.asarray([False, False, True, True, True])},
    )
    cases = {
        "duplicated_support_copy": lambda: _impute_with_fake_qrf(duplicated_copy),
        "duplicated_unexpanded_source": lambda: _impute_with_fake_qrf(
            duplicated_source
        ),
        "duplicated_same_role_rows": lambda: us_voluntary_filing_summary(
            duplicated_role
        ),
    }
    for name, call in cases.items():
        with pytest.raises(ValueError) as caught:
            call()
        messages[name] = str(caught.value)
    return messages


def _k1_golden_payload() -> dict[str, object]:
    """Receiver rows, fan-out keys, draws, summary and gate for every fixture."""

    payload: dict[str, object] = {}
    for name, build in _K1_GOLDEN_FIXTURES.items():
        frame = build()
        receiver = module._recipient_tax_unit_predictor_table(frame)
        rows, keys = module._source_receiver_rows(frame, receiver)
        predicted = _impute_with_fake_qrf(frame)
        materialized = _replace_tax_unit(frame, **{_OUTPUT: predicted.to_numpy()})
        gate = us_voluntary_filing_signal_gate(materialized)
        payload[name] = {
            "receiver_index": [str(value) for value in rows.index],
            "receiver_columns": [str(value) for value in rows.columns],
            "receiver_values": rows.to_numpy(dtype=np.float64).tolist(),
            "fanout_keys": [str(value) for value in keys.tolist()],
            "fanout_index": [str(value) for value in keys.index],
            "predicted": [bool(value) for value in predicted.tolist()],
            "predicted_index": [int(value) for value in predicted.index],
            "summary": us_voluntary_filing_summary(materialized),
            "gate_passed": bool(gate.passed),
            "gate_failures": list(gate.failures),
        }
    payload["refusals"] = _k1_refusal_messages()
    return payload


def _k1_golden_digest() -> str:
    encoded = json.dumps(_k1_golden_payload(), sort_keys=True, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _source_decisions(frame: Frame, predicted: pd.Series) -> pd.Series:
    """One decision per source unit, asserting every copy agrees."""

    source = frame.table("tax_unit")["tax_unit_source_id"].astype(str).to_numpy()
    grouped = pd.Series(predicted.to_numpy(), index=source).groupby(level=0)
    assert (grouped.nunique() == 1).all(), "copies of one source unit disagree"
    return grouped.first()


def _source_weights(frame: Frame) -> pd.Series:
    source = frame.table("tax_unit")["tax_unit_source_id"].astype(str).to_numpy()
    weights = np.asarray(frame.resolve_weights("tax_unit").values, dtype=np.float64)
    return pd.Series(weights, index=source).groupby(level=0).sum()


def _assert_location_summary_matches_k1(
    frame: Frame,
    predicted: pd.Series,
    clones: int,
) -> dict[str, object]:
    """Location-clone a materialized frame; its summary must equal K = 1's.

    Counts, flags and keys are exact; weighted totals and shares agree up to
    the float summation order of the ``w / K`` split.
    """

    materialized = _replace_tax_unit(frame, **{_OUTPUT: predicted.to_numpy()})
    cloned = clone_frame_for_location(materialized, clones)
    expected = us_voluntary_filing_summary(materialized)
    observed = us_voluntary_filing_summary(cloned)
    assert set(observed) == set(expected)
    approximate = {
        "weighted_true_share",
        "weighted_true_total",
        "weighted_false_total",
        "channel_diagnostics",
    }
    for key in set(expected) - approximate:
        assert observed[key] == expected[key], key
    for key in ("weighted_true_share", "weighted_true_total", "weighted_false_total"):
        assert observed[key] == pytest.approx(expected[key], rel=1e-12, abs=1e-12)
    assert set(observed["channel_diagnostics"]) == set(expected["channel_diagnostics"])
    for channel, diagnostics in expected["channel_diagnostics"].items():
        location = observed["channel_diagnostics"][channel]
        assert location["unique_count"] == diagnostics["unique_count"]
        assert location["weighted_true_share"] == pytest.approx(
            diagnostics["weighted_true_share"], rel=1e-12, abs=1e-12
        )
    expected_gate = us_voluntary_filing_signal_gate(materialized)
    observed_gate = us_voluntary_filing_signal_gate(cloned)
    assert observed_gate.passed == expected_gate.passed
    assert observed_gate.failures == expected_gate.failures
    pd.testing.assert_series_equal(
        _source_weights(cloned), _source_weights(materialized), rtol=1e-12
    )
    return observed


def _location_scenario_frame(
    n_households: int,
    *,
    wages: Collection[int],
    tail_households: Collection[int],
    drop_native: Collection[int],
    drop_primary: Collection[int],
) -> Frame:
    """A historical support frame with tail copies and frozen-support survivors.

    ``wages`` (thousands, cycled over person rows) replace every person's wage
    before PUF-support cloning, so all support copies share them. Tail copies
    are added for ``tail_households``; then the native (clone 0) copy of each
    ``drop_native`` source household and the primary PUF-detail (clone 1) copy
    of each ``drop_primary`` source household are dropped, except that source
    household 1 always keeps its native copy so the frame is never empty.
    """

    base = _frame(n_households)
    person = base.table("person")
    cycle = np.resize(np.asarray(list(wages), dtype=np.float64), len(person))
    base = _replace_person(
        base,
        np.ones(len(person), dtype=bool),
        employment_income_before_lsr=cycle * 1_000.0,
    )
    frame = clone_us_frame_for_puf_support(base)
    if tail_households:
        frame = _TAIL.with_capital_gains_tail_copies(frame, sorted(tail_households))
    tax_unit = frame.table("tax_unit")
    source_household = tax_unit["tax_unit_source_id"].astype(int) - 100
    clone_index = tax_unit["tax_unit_support_clone_index"].astype(int)
    dropped = (
        clone_index.eq(0)
        & source_household.isin(drop_native)
        & source_household.ne(1)
    ) | (clone_index.eq(1) & source_household.isin(drop_primary))
    return _without_tax_units(frame, _tax_unit_ids(frame, dropped))


__all__ = [name for name in globals() if not name.startswith("__")]
