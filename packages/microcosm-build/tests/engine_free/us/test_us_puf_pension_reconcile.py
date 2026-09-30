"""PUF clones split the imputed taxable pension total into public and private.

The PUF reports one taxable pension total (E01700), imputed onto
``taxable_private_pension_income``; every clone also carries its native twin's
CPS public and private pensions.  Invariants (PolicyEngine/microcosm#1068):

* conservation: per clone tax unit, public plus private taxable pension equals
  the imputed PUF total, so the twin's public pension is never added on top;
* shares: a unit whose twin reports pension keeps the twin's public share; a
  unit whose twin reports none takes the clone arm's weighted public share;
* bounds: both pieces are nonnegative and public never exceeds the total;
* native rows are untouched.
"""

# ruff: noqa: F403, F405
from microcosm.build.us_runtime.puf_support import (
    PUF_TAX_DETAIL_CLONE_INDEX,
    PUF_TAX_DETAIL_PENSION_TOTAL_OUTPUT,
    PUF_TAX_DETAIL_PUBLIC_PENSION_COMPONENT,
    _reconcile_puf_pension_components,
)
from test_support.microcosm_build.us_puf_support import *

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

_PRIVATE = PUF_TAX_DETAIL_PENSION_TOTAL_OUTPUT
_PUBLIC = PUF_TAX_DETAIL_PUBLIC_PENSION_COMPONENT
_CLONE = support_clone_index_column("person")


def _clone_people(units: list[list[tuple[float, float]]]) -> pd.DataFrame:
    """Clone-arm people: one list of (public, private) CPS basis per unit."""

    rows = [
        {
            "person_tax_unit_id": unit_index + 1,
            _CLONE: PUF_TAX_DETAIL_CLONE_INDEX,
            _PUBLIC: public,
            _PRIVATE: private,
        }
        for unit_index, people in enumerate(units)
        for public, private in people
    ]
    return pd.DataFrame(rows)


def _reconcile(people, totals, weights):
    predictions = pd.DataFrame({_PRIVATE: np.asarray(totals, dtype=np.float64)})
    public = _reconcile_puf_pension_components(
        predictions,
        people,
        person_clone_index=_CLONE,
        tax_unit_ids=np.arange(1, len(totals) + 1),
        tax_unit_weights=np.asarray(weights, dtype=np.float64),
        requested_outputs=(_PRIVATE,),
    )
    return public, predictions[_PRIVATE].to_numpy()


def test_units_keep_their_twins_public_share_and_the_rest_take_the_arm_share():
    people = _clone_people(
        [
            [(300.0, 100.0), (0.0, 0.0)],  # twin share 0.75
            [(0.0, 0.0)],  # no twin pension: arm share
            [(0.0, 500.0)],  # twin share 0
        ]
    )
    # Arm share: (1 * 300 + 3 * 0) / (1 * 400 + 3 * 500) = 300 / 1,900.
    public, private = _reconcile(people, [1_000.0, 2_000.0, 800.0], [1.0, 2.0, 3.0])

    arm_share = 300.0 / 1_900.0
    np.testing.assert_allclose(public, [750.0, 2_000.0 * arm_share, 0.0])
    np.testing.assert_allclose(private, [250.0, 2_000.0 * (1 - arm_share), 800.0])


def test_no_basis_anywhere_leaves_everything_private():
    people = _clone_people([[(0.0, 0.0)], [(0.0, 0.0)]])

    public, private = _reconcile(people, [1_000.0, 0.0], [1.0, 1.0])

    np.testing.assert_array_equal(public, [0.0, 0.0])
    np.testing.assert_array_equal(private, [1_000.0, 0.0])


def test_native_rows_do_not_enter_the_basis():
    people = _clone_people([[(0.0, 100.0)]])
    native = people.assign(**{_CLONE: 0, _PUBLIC: 1_000.0, _PRIVATE: 0.0})

    public, private = _reconcile(pd.concat([people, native]), [400.0], [1.0])

    np.testing.assert_array_equal(public, [0.0])
    np.testing.assert_array_equal(private, [400.0])


def test_frames_without_a_public_leaf_or_pension_target_are_left_alone():
    people = _clone_people([[(0.0, 100.0)]]).drop(columns=[_PUBLIC])
    predictions = pd.DataFrame({_PRIVATE: [400.0]})

    assert (
        _reconcile_puf_pension_components(
            predictions,
            people,
            person_clone_index=_CLONE,
            tax_unit_ids=np.asarray([1]),
            tax_unit_weights=np.asarray([1.0]),
            requested_outputs=(_PRIVATE,),
        )
        is None
    )
    assert (
        _reconcile_puf_pension_components(
            predictions,
            _clone_people([[(1.0, 1.0)]]),
            person_clone_index=_CLONE,
            tax_unit_ids=np.asarray([1]),
            tax_unit_weights=np.asarray([1.0]),
            requested_outputs=("social_security_retirement",),
        )
        is None
    )
    assert predictions[_PRIVATE].tolist() == [400.0]


# Subnormal totals underflow share * total to zero, a float artifact, not a split.
_AMOUNT = st.floats(
    min_value=0.0, max_value=1e6, allow_nan=False, allow_subnormal=False
)


@st.composite
def _arms(draw):
    units = draw(
        st.lists(
            st.lists(st.tuples(_AMOUNT, _AMOUNT), min_size=1, max_size=3),
            min_size=1,
            max_size=12,
        )
    )
    totals = draw(st.lists(_AMOUNT, min_size=len(units), max_size=len(units)))
    weights = draw(
        st.lists(
            st.floats(min_value=0.01, max_value=1e4),
            min_size=len(units),
            max_size=len(units),
        )
    )
    return units, totals, weights


@settings(max_examples=200, deadline=None)
@given(arm=_arms())
def test_split_conserves_each_units_puf_total_within_bounds(arm):
    units, totals, weights = arm
    public, private = _reconcile(_clone_people(units), totals, weights)

    totals = np.asarray(totals)
    np.testing.assert_allclose(public + private, totals, rtol=1e-12, atol=1e-6)
    assert (public >= 0).all() and (private >= -1e-6).all()
    assert (public <= totals + 1e-6).all()
    for index, people in enumerate(units):
        basis_public = sum(person[0] for person in people)
        basis_total = basis_public + sum(person[1] for person in people)
        if basis_total > 0 and totals[index] > 0:
            np.testing.assert_allclose(
                public[index] / totals[index],
                basis_public / basis_total,
                rtol=1e-9,
                atol=1e-12,
            )


def test_imputation_writes_split_pensions_onto_clone_people_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TotalPensionQRF:
        def __init__(self, **_: object) -> None:
            pass

        def fit(self, *_: object, **__: object) -> "TotalPensionQRF":
            return self

        def predict(
            self,
            features: pd.DataFrame,
            *,
            release_models: bool = False,
        ) -> pd.DataFrame:
            return pd.DataFrame({_PRIVATE: [1_000.0, 2_000.0]}, index=features.index)

    monkeypatch.setattr(puf_support_module, "QRF", TotalPensionQRF)

    base = _minimal_us_frame()
    person = base.table("person")
    # Tax unit 10: the first twin has a $300 public and the second a $100
    # private taxable pension; tax unit 20's twin has none.
    person[_PUBLIC] = [300.0, 0.0, 0.0]
    person[_PRIVATE] = [0.0, 100.0, 0.0]
    expanded = clone_us_frame_for_puf_support(base)
    donor = pd.DataFrame(
        {
            "filing_status_code": [1.0, 2.0],
            "tax_unit_person_count": [1.0, 2.0],
            _PRIVATE: [1_000.0, 2_000.0],
            "weight": [1.0, 1.0],
        }
    )

    imputed = impute_us_puf_tax_detail_support(
        expanded,
        donor,
        predictors=(
            "puf_predictor_filing_status_code",
            "puf_predictor_tax_unit_person_count",
        ),
        person_outputs=(_PRIVATE,),
        tax_unit_outputs=(),
        n_estimators=4,
        seed=0,
    )

    person = imputed.table("person")
    is_puf = person[support_channel_column("person")] == PUF_TAX_DETAIL_SUPPORT_CHANNEL
    clones = person[is_puf].sort_values("person_id")
    natives = person[~is_puf].sort_values("person_id")
    # Unit 10 keeps its twin's 75% public share; unit 20 has no twin pension
    # and takes the arm's weighted share, which is unit 10's 75%.
    np.testing.assert_allclose(clones[_PUBLIC], [750.0, 0.0, 1_500.0])
    np.testing.assert_allclose(clones[_PRIVATE], [0.0, 250.0, 500.0])
    totals = clones.groupby("person_tax_unit_id")[[_PUBLIC, _PRIVATE]].sum()
    np.testing.assert_allclose(totals.sum(axis=1), [1_000.0, 2_000.0])
    np.testing.assert_array_equal(natives[_PUBLIC], [300.0, 0.0, 0.0])
    np.testing.assert_array_equal(natives[_PRIVATE], [0.0, 100.0, 0.0])
