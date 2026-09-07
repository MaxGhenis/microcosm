"""Invented shared/exclusive populations and one weight per household axis."""

from fractions import Fraction

import numpy as np
import pytest

from microcosm.build.survey_allocation import (
    SurveyAllocationError,
    SurveyDomain,
    allocate_domain_weights,
)
from microcosm.frame import WeightKind, Weights


def _domain(key="hu", unit="occupied_housing_unit", shares=None):
    return SurveyDomain(
        key,
        unit,
        "invented-period",
        "stipulated common coverage",
        {"a": Fraction(1, 2), "b": Fraction(1, 2)} if shares is None else shares,
    )


def _run(values=(100, 100, 10), **kwargs):
    inputs = dict(
        row_ids=[1, 2, 3],
        source_channels=["a", "b", "b"],
        domain_keys=["hu", "hu", "gq"],
        unit_counts=[1, 1, 1],
        domains=[_domain(), _domain("gq", "group_quarters_person", {"b": Fraction(1)})],
    )
    inputs.update(kwargs)
    return allocate_domain_weights(
        Weights(np.array(values), WeightKind.DESIGN), **inputs
    )


def test_shared_and_exclusive_estimates_preserve_distinct_units():
    result = _run()
    np.testing.assert_array_equal(result.weights.values, [50, 50, 10])
    assert result.weights.kind is WeightKind.IMPORTANCE
    assert result.row_ids == (1, 2, 3)
    totals = {}
    for cell in result.estimates:
        totals[cell.domain] = totals.get(cell.domain, 0) + cell.allocated_estimate
    assert totals == {"hu": 100, "gq": 10}


def test_source_estimates_need_not_agree_or_match_an_anchor():
    result = _run(values=(90, 100, 10))
    assert sum(c.allocated_estimate for c in result.estimates if c.domain == "hu") == 95


def test_person_clusters_use_counts_without_splitting_household_weights():
    result = _run(
        values=(20, 10, 10),
        domain_keys=["gq"] * 3,
        unit_counts=[1, 1, 3],
        domains=[_domain("gq", "group_quarters_person")],
    )
    # a estimates 20 people; b estimates 10*1 + 10*3 = 40 people.
    # The combination estimates 30, with just one output weight per cluster.
    np.testing.assert_array_equal(result.weights.values, [10, 5, 5])
    assert [c.design_estimate for c in result.estimates] == [20, 40]
    assert sum(c.allocated_estimate for c in result.estimates) == 30


def test_order_is_preserved_and_changes_neither_mapping_nor_estimates():
    original = _run()
    moved = _run(
        values=(10, 100, 100),
        row_ids=[3, 1, 2],
        source_channels=["b", "a", "b"],
        domain_keys=["gq", "hu", "hu"],
    )
    assert dict(zip(original.row_ids, original.weights.values, strict=True)) == dict(
        zip(moved.row_ids, moved.weights.values, strict=True)
    )
    assert moved.estimates == original.estimates


@pytest.mark.parametrize(
    "change,match",
    [
        ({"row_ids": [1, 1, 3]}, "unique"),
        ({"domain_keys": ["hu", None, "gq"]}, "unknown"),
        ({"source_channels": ["a", "missing", "b"]}, "source is not declared"),
        ({"unit_counts": [1, 0, 1]}, "unit_counts"),
        ({"unit_counts": [1, 1.5, 1]}, "unit_counts"),
        ({"unit_counts": [1, True, 1]}, "unit_counts"),
        ({"unit_counts": [1, 2**53 + 1, 1]}, "unit_counts"),
        ({"row_ids": [True, 2, 3]}, "int64"),
        ({"row_ids": [1, 2]}, "match"),
        ({"domains": [_domain(), _domain()]}, "unique"),
    ],
)
def test_invalid_axis_or_coverage_refuses(change, match):
    with pytest.raises(SurveyAllocationError, match=match):
        _run(**change)


def test_absent_positive_share_source_is_not_inferred_to_be_excluded():
    with pytest.raises(SurveyAllocationError, match="lacks sampled support"):
        _run(source_channels=["a", "a", "b"])
    with pytest.raises(SurveyAllocationError, match="lacks sampled support"):
        _run(values=(0, 100, 10))


def test_explicit_zero_share_is_reported_without_requiring_sample_support():
    result = _run(
        domains=[
            _domain(
                shares={"a": Fraction(1, 2), "b": Fraction(1, 2), "c": Fraction(0)}
            ),
            _domain("gq", "group_quarters_person", {"b": Fraction(1)}),
        ]
    )
    cell = next(c for c in result.estimates if c.source == "c")
    assert cell.rows == 0 and cell.allocated_estimate == 0
    assert {c.source for c in result.estimates} == {"a", "b", "c"}


def test_domain_declaration_is_owned_and_does_not_accept_float_shares():
    shares = {"a": Fraction(1)}
    domain = _domain(shares=shares)
    shares["a"] = Fraction(0)
    assert domain.source_shares["a"] == 1
    with pytest.raises(TypeError):
        domain.source_shares["a"] = Fraction(0)
    for bad in (
        {"a": 0.5, "b": 0.5},
        {"a": Fraction(1, 2)},
        {"a": Fraction(-1), "b": Fraction(2)},
    ):
        with pytest.raises(SurveyAllocationError):
            _domain(shares=bad)


def test_periods_and_units_stay_on_separate_estimates():
    result = _run()
    assert {(c.statistical_unit, c.period, c.basis) for c in result.estimates} == {
        ("occupied_housing_unit", "invented-period", "stipulated common coverage"),
        ("group_quarters_person", "invented-period", "stipulated common coverage"),
    }


def test_kind_and_numeric_overflow_underflow_refuse():
    with pytest.raises(SurveyAllocationError, match="DESIGN"):
        allocate_domain_weights(
            Weights([1.0], WeightKind.CALIBRATED),
            row_ids=[1],
            source_channels=["a"],
            domain_keys=["hu"],
            unit_counts=[1],
            domains=[_domain()],
        )
    with pytest.raises(SurveyAllocationError, match="overflow"):
        _run(values=(1e308, 100, 10), unit_counts=[10, 1, 1])
    with pytest.raises(SurveyAllocationError, match="underflow"):
        _run(values=(np.nextafter(0.0, 1.0), 100, 10))
