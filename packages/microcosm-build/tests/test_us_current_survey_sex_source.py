"""Actual preparation and sex owners over the maintained invented source fixture.

The fixture constructs private tiny source members and registry pins, then uses
the real source readers, native issuers and preparation owner. No issuer or
checked accessor is replaced. These tests require their own bounded runtime
packet; the pure/graph suite does not authorize their source I/O.
"""

import sys

import pytest
from test_us_current_asec_demographics import _demographic_arguments

from microcosm.build.us_runtime import current_survey_sex as sex


@pytest.mark.parametrize("unknown", [False, True])
def test_actual_preparation_qualifies_both_source_arms_and_preserves_unknowns(
    tmp_path, monkeypatch, unknown
):
    arguments = _demographic_arguments(tmp_path, monkeypatch, unknown=unknown)
    prepared = sex.source.prepare_authenticated_survey_population(**arguments)
    assert type(prepared) is sex.source.AuthenticatedSurveyPopulationPreparation
    before = sex.source._frame_identity(prepared.checked_view().frame)
    qualified = sex.qualify_current_survey_sex(prepared)
    rows = qualified.rows
    acs = rows.loc[rows[sex.SURVEY_COLUMN].eq("acs")]
    asec = rows.loc[rows[sex.SURVEY_COLUMN].eq("asec")]
    assert len(acs) == 5 and len(asec) == 4
    assert rows[sex.CODE_KNOWN_COLUMN].all()
    assert acs[sex.VALUE_KNOWN_COLUMN].all()
    assert not acs[sex.ALLOCATION_KNOWN_COLUMN].any()
    assert acs[sex.ORIGIN_COLUMN].eq(sex.ACS_ORIGIN).all()
    assert acs[sex.VALUE_COLUMN].tolist() == acs[sex.CODE_COLUMN].eq(2).tolist()
    assert int(asec[sex.VALUE_COLUMN].isna().sum()) == int(unknown)
    allocated = asec.loc[asec[sex.ALLOCATION_CODE_COLUMN].eq(4)]
    assert len(allocated) == 2 and allocated[sex.VALUE_COLUMN].all()
    assert allocated[sex.ALLOCATION_KNOWN_COLUMN].all()
    assert allocated[sex.ORIGIN_COLUMN].eq("census_allocated").all()
    assert sex.source._frame_identity(qualified.source_frame) == before
    assert sex.source._frame_identity(prepared.checked_view().frame) == before
    fresh = sex.qualify_current_survey_sex(prepared)
    assert sex.sex_projection_seal(fresh) == sex.sex_projection_seal(qualified)
    assert fresh.receipt == qualified.receipt


@pytest.mark.parametrize("borrow_number", [1, 2])
@pytest.mark.parametrize(
    "mutation", ["callable", "code", "defaults", "constant", "owner_code"]
)
def test_actual_first_and_final_preparation_borrows_refuse_live_source_mutation(
    tmp_path, monkeypatch, borrow_number, mutation
):
    prepared = sex.source.prepare_authenticated_survey_population(
        **_demographic_arguments(tmp_path, monkeypatch)
    )
    assert type(prepared) is sex.source.AuthenticatedSurveyPopulationPreparation
    checked = type(prepared)._checked
    checked_code = checked.__code__
    qualify_code = sex.qualify_current_survey_sex.__code__
    seen, fired = [], []

    def replacement(*args, **kwargs):
        raise AssertionError("mutated executable must not run")

    def profile(frame, event, arg):
        if (
            event == "return"
            and frame.f_code is checked_code
            and frame.f_back is not None
            and frame.f_back.f_code is qualify_code
        ):
            seen.append(True)
            if len(seen) != borrow_number:
                return
            fired.append(True)
            if mutation == "callable":
                monkeypatch.setattr(sex, "_project", replacement)
            elif mutation == "code":
                monkeypatch.setattr(sex._project, "__code__", replacement.__code__)
            elif mutation == "defaults":
                monkeypatch.setattr(sex._project, "__defaults__", (None,))
            elif mutation == "constant":
                monkeypatch.setattr(sex, "ACS_OBSERVATION_YEAR", 2099)
            else:
                monkeypatch.setattr(checked, "__code__", replacement.__code__)

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        with pytest.raises(
            ValueError, match="CURRENT_SURVEY_SEX_IMPLEMENTATION_CHANGED"
        ):
            sex.qualify_current_survey_sex(prepared)
    finally:
        sys.setprofile(previous)
    assert len(seen) == borrow_number and fired == [True]
