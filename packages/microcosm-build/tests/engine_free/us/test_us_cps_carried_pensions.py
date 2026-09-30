"""CPS ASEC pensions split into PolicyEngine-US public and private leaves.

``PNSN_VAL = PEN_VAL1 + PEN_VAL2``, each source typed by ``PEN_SC1``/``PEN_SC2``
(Census cpsmar24.pdf: 1 company, 2 union, 3 federal, 4 state, 5 local, 6 US
military, 7 US Railroad Retirement, 8 other).  Invariants pinned here:

* conservation: the four leaves sum to ``PNSN_VAL + ANN_VAL`` per person, and
  the taxable and tax-exempt pairs each sum to what the all-private carry wrote
  before the split (the taxable fraction is unchanged);
* classification: an amount is public exactly when its source code, or for an
  uncoded amount the other source's code, is in 3-7;
* bounds: every leaf is nonnegative and public dollars never exceed
  ``PNSN_VAL``; annuities are always private;
* determinism and row-permutation equivariance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from microcosm.build.us_runtime.cps_carried import (
    CPS_CARRIED_PERSON_INPUTS,
    PENSION_LEAVES,
    PENSION_SOURCE_PRIVATE_CODES,
    PENSION_SOURCE_PUBLIC_CODES,
    TAXABLE_PENSION_FRACTION,
    _pension_public_private_amounts,
    derive_us_cps_carried_inputs,
)
from microcosm.frame import US_SCHEMA, Frame, WeightKind, Weights

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

_PUBLIC = (
    "taxable_public_pension_income",
    "tax_exempt_public_pension_income",
)
_PRIVATE = (
    "taxable_private_pension_income",
    "tax_exempt_private_pension_income",
)


def _person(**columns) -> pd.DataFrame:
    count = len(next(iter(columns.values())))
    base = {
        "PNSN_VAL": np.zeros(count),
        "ANN_VAL": np.zeros(count),
        "PEN_SC1": np.zeros(count, dtype=np.int64),
        "PEN_SC2": np.zeros(count, dtype=np.int64),
        "PEN_VAL1": np.zeros(count),
        "PEN_VAL2": np.zeros(count),
    }
    base.update(columns)
    if "PNSN_VAL" not in columns:
        base["PNSN_VAL"] = np.asarray(base["PEN_VAL1"]) + np.asarray(base["PEN_VAL2"])
    return pd.DataFrame(base)


def _frame(person: pd.DataFrame) -> Frame:
    count = len(person)
    ids = np.arange(1, count + 1, dtype=np.int64)
    person = person.assign(
        person_id=ids,
        person_household_id=ids + 100,
        person_tax_unit_id=ids + 200,
        person_spm_unit_id=ids + 300,
        person_family_id=ids + 400,
        person_marital_unit_id=ids + 500,
        A_AGE=np.full(count, 70),
        A_SEX=np.tile([1, 2], count)[:count],
    )
    tables = {
        "person": person,
        "household": pd.DataFrame(
            {"household_id": ids + 100, "state_fips": np.full(count, 36)}
        ),
        "tax_unit": pd.DataFrame(
            {"tax_unit_id": ids + 200, "filing_status_input": ["SINGLE"] * count}
        ),
        "spm_unit": pd.DataFrame({"spm_unit_id": ids + 300}),
        "family": pd.DataFrame({"family_id": ids + 400}),
        "marital_unit": pd.DataFrame({"marital_unit_id": ids + 500}),
    }
    return Frame(
        tables,
        US_SCHEMA,
        {"household": Weights(np.ones(count), WeightKind.DESIGN)},
    )


def _reference_split(row: pd.Series) -> tuple[float, float]:
    """Row-by-row restatement of the split, independent of the vectorized code."""

    public = 0.0
    private = float(row["ANN_VAL"])
    sources = [
        (int(row["PEN_SC1"]), float(row["PEN_VAL1"])),
        (int(row["PEN_SC2"]), float(row["PEN_VAL2"])),
    ]
    for index, (code, amount) in enumerate(sources):
        if code == 0:
            code = sources[1 - index][0]
        if code in {3, 4, 5, 6, 7}:
            public += amount
        else:
            private += amount
    return public, private


def test_the_code_classes_partition_the_census_codebook() -> None:
    assert PENSION_SOURCE_PUBLIC_CODES == {3, 4, 5, 6, 7}
    assert PENSION_SOURCE_PRIVATE_CODES == {1, 2, 8}
    assert PENSION_SOURCE_PUBLIC_CODES.isdisjoint(PENSION_SOURCE_PRIVATE_CODES)
    assert PENSION_SOURCE_PUBLIC_CODES | PENSION_SOURCE_PRIVATE_CODES == set(
        range(1, 9)
    )


@pytest.mark.parametrize(
    ("code", "public"),
    [
        (1, False),  # company pension
        (2, False),  # union pension
        (3, True),  # federal government pension
        (4, True),  # state government pension
        (5, True),  # local government pension
        (6, True),  # US military pension
        (7, True),  # US Railroad Retirement
        (8, False),  # other
    ],
)
@pytest.mark.parametrize("slot", ["1", "2"])
def test_each_source_code_lands_on_its_class(code: int, public: bool, slot: str):
    person = _person(
        **{f"PEN_SC{slot}": np.array([code]), f"PEN_VAL{slot}": np.array([1_000.0])}
    )

    public_amount, private_amount = _pension_public_private_amounts(person)

    assert public_amount.tolist() == ([1_000.0] if public else [0.0])
    assert private_amount.tolist() == ([0.0] if public else [1_000.0])


def test_a_person_with_one_public_and_one_private_source_is_split_by_amount():
    person = _person(
        PEN_SC1=np.array([1, 3]),
        PEN_VAL1=np.array([700.0, 2_500.0]),
        PEN_SC2=np.array([4, 2]),
        PEN_VAL2=np.array([300.0, 500.0]),
    )

    public, private = _pension_public_private_amounts(person)

    assert public.tolist() == [300.0, 2_500.0]
    assert private.tolist() == [700.0, 500.0]


def test_an_uncoded_second_amount_takes_the_first_sources_class():
    """The two 2023-ASEC rows: PEN_SC1 = 4, PEN_SC2 = 0, PEN_VAL2 = 1,271."""

    person = _person(
        PEN_SC1=np.array([4, 1]),
        PEN_VAL1=np.array([15_252.0, 15_252.0]),
        PEN_SC2=np.array([0, 0]),
        PEN_VAL2=np.array([1_271.0, 1_271.0]),
    )

    public, private = _pension_public_private_amounts(person)

    assert public.tolist() == [16_523.0, 0.0]
    assert private.tolist() == [0.0, 16_523.0]


def test_annuities_are_private_and_need_no_source_columns():
    person = pd.DataFrame({"PNSN_VAL": [0.0, 0.0], "ANN_VAL": [0.0, 1_200.0]})

    public, private = _pension_public_private_amounts(person)

    assert public.tolist() == [0.0, 0.0]
    assert private.tolist() == [0.0, 1_200.0]


def test_derive_writes_all_four_leaves_with_the_unchanged_taxable_fraction():
    person = _person(
        PEN_SC1=np.array([3, 1, 0, 6]),
        PEN_VAL1=np.array([10_000.0, 4_000.0, 0.0, 8_000.0]),
        PEN_SC2=np.array([0, 5, 0, 8]),
        PEN_VAL2=np.array([0.0, 6_000.0, 0.0, 2_000.0]),
        ANN_VAL=np.array([0.0, 1_000.0, 500.0, 0.0]),
    )

    result = derive_us_cps_carried_inputs(_frame(person)).table("person")

    public = np.array([10_000.0, 6_000.0, 0.0, 8_000.0])
    private = np.array([0.0, 5_000.0, 500.0, 2_000.0])
    np.testing.assert_allclose(
        result["taxable_public_pension_income"], public * TAXABLE_PENSION_FRACTION
    )
    np.testing.assert_allclose(
        result["tax_exempt_public_pension_income"],
        public * (1 - TAXABLE_PENSION_FRACTION),
    )
    np.testing.assert_allclose(
        result["taxable_private_pension_income"], private * TAXABLE_PENSION_FRACTION
    )
    np.testing.assert_allclose(
        result["tax_exempt_private_pension_income"],
        private * (1 - TAXABLE_PENSION_FRACTION),
    )
    assert set(PENSION_LEAVES) <= CPS_CARRIED_PERSON_INPUTS
    for leaf in PENSION_LEAVES:
        assert result[leaf].dtype == np.float64


def test_derive_preserves_all_four_leaves_when_all_already_exist():
    person = _person(PEN_SC1=np.array([3]), PEN_VAL1=np.array([1_000.0]))
    for index, leaf in enumerate(PENSION_LEAVES):
        person[leaf] = [float(index)]

    result = derive_us_cps_carried_inputs(_frame(person)).table("person")

    assert [result[leaf].item() for leaf in PENSION_LEAVES] == [0.0, 1.0, 2.0, 3.0]


@pytest.mark.parametrize("carried", [_PRIVATE, _PUBLIC, PENSION_LEAVES[:1]])
def test_derive_refuses_a_partially_carried_pension_surface(carried):
    """A frame from before the split keeps only the private pair: adding the
    public pair on top would count government pensions twice."""

    person = _person(PEN_SC1=np.array([3]), PEN_VAL1=np.array([1_000.0]))
    for leaf in carried:
        person[leaf] = [1.0]

    with pytest.raises(ValueError, match="partially present"):
        derive_us_cps_carried_inputs(_frame(person))


@pytest.mark.parametrize("dropped", ["PEN_SC1", "PEN_SC2", "PEN_VAL1", "PEN_VAL2"])
def test_positive_pensions_without_source_columns_are_refused(dropped):
    person = _person(PEN_SC1=np.array([1]), PEN_VAL1=np.array([1_000.0])).drop(
        columns=[dropped]
    )

    with pytest.raises(ValueError, match=rf"lacks \['{dropped}'\]"):
        _pension_public_private_amounts(person)


@pytest.mark.parametrize(
    ("columns", "match"),
    [
        (
            {"PEN_SC1": [3], "PEN_VAL1": [1_000.0], "PNSN_VAL": [999.0]},
            "PNSN_VAL must equal PEN_VAL1 \\+ PEN_VAL2",
        ),
        ({"PEN_SC1": [9], "PEN_VAL1": [1_000.0]}, "PEN_SC1 must be one of"),
        ({"PEN_SC2": [-1], "PEN_VAL1": [1_000.0]}, "PEN_SC2 must be one of"),
        (
            {"PEN_SC1": [3], "PEN_VAL1": [1_500.0], "PEN_VAL2": [-500.0]},
            "PEN_VAL2 must be nonnegative",
        ),
        ({"PEN_VAL1": [1_000.0]}, "both 0"),
        ({"PNSN_VAL": [-5.0]}, "PNSN_VAL must be nonnegative"),
    ],
)
def test_malformed_pension_sources_are_refused(columns, match):
    person = _person(**{key: np.asarray(value) for key, value in columns.items()})

    with pytest.raises(ValueError, match=match):
        _pension_public_private_amounts(person)


_CODES = st.integers(min_value=0, max_value=8)
_DOLLARS = st.integers(min_value=0, max_value=999_999).map(float)


@st.composite
def _pension_rows(draw) -> pd.DataFrame:
    rows = draw(st.integers(min_value=1, max_value=25))
    records = []
    for _ in range(rows):
        code_1, code_2 = draw(_CODES), draw(_CODES)
        amount_1 = draw(_DOLLARS) if code_1 or draw(st.booleans()) else 0.0
        amount_2 = draw(_DOLLARS) if code_2 or draw(st.booleans()) else 0.0
        if amount_1 + amount_2 > 0 and code_1 == 0 and code_2 == 0:
            code_1 = draw(st.integers(min_value=1, max_value=8))
        records.append(
            {
                "PEN_SC1": code_1,
                "PEN_SC2": code_2,
                "PEN_VAL1": amount_1,
                "PEN_VAL2": amount_2,
                "PNSN_VAL": amount_1 + amount_2,
                "ANN_VAL": draw(_DOLLARS),
            }
        )
    return pd.DataFrame(records)


@settings(max_examples=200, deadline=None)
@given(person=_pension_rows())
def test_split_conserves_totals_and_matches_the_row_reference(person):
    public, private = _pension_public_private_amounts(person)

    total = person["PNSN_VAL"].to_numpy() + person["ANN_VAL"].to_numpy()
    np.testing.assert_allclose(public + private, total, rtol=0, atol=1e-6)
    assert (public >= 0).all() and (private >= 0).all()
    assert (public <= person["PNSN_VAL"].to_numpy() + 1e-9).all()
    assert (private >= person["ANN_VAL"].to_numpy() - 1e-9).all()
    reference = person.apply(_reference_split, axis=1, result_type="expand")
    np.testing.assert_allclose(public, reference[0].to_numpy(), rtol=0, atol=1e-9)
    np.testing.assert_allclose(private, reference[1].to_numpy(), rtol=0, atol=1e-9)


@settings(max_examples=100, deadline=None)
@given(person=_pension_rows())
def test_derived_leaves_conserve_the_pre_split_all_private_carry(person):
    """Differential against the carry this split replaced: every pension and
    annuity dollar at 59.0% taxable on the private pair."""

    result = derive_us_cps_carried_inputs(_frame(person)).table("person")

    old = person["PNSN_VAL"].to_numpy() + person["ANN_VAL"].to_numpy()
    np.testing.assert_allclose(
        result["taxable_public_pension_income"]
        + result["taxable_private_pension_income"],
        old * TAXABLE_PENSION_FRACTION,
        rtol=1e-12,
        atol=1e-6,
    )
    np.testing.assert_allclose(
        result["tax_exempt_public_pension_income"]
        + result["tax_exempt_private_pension_income"],
        old * (1 - TAXABLE_PENSION_FRACTION),
        rtol=1e-12,
        atol=1e-6,
    )
    np.testing.assert_allclose(
        result[list(PENSION_LEAVES)].sum(axis=1), old, rtol=1e-12, atol=1e-6
    )
    for leaf in PENSION_LEAVES:
        assert (result[leaf] >= 0).all()


@settings(max_examples=50, deadline=None)
@given(person=_pension_rows(), seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_split_is_deterministic_and_row_permutation_equivariant(person, seed):
    first = _pension_public_private_amounts(person)
    second = _pension_public_private_amounts(person.copy(deep=True))
    order = np.random.default_rng(seed).permutation(len(person))
    permuted = _pension_public_private_amounts(
        person.iloc[order].reset_index(drop=True)
    )

    for one, two, shuffled in zip(first, second, permuted, strict=True):
        np.testing.assert_array_equal(one, two)
        np.testing.assert_array_equal(one[order], shuffled)
