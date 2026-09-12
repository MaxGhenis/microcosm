"""Archived CPS/ACS housing-input restoration."""

from __future__ import annotations

from itertools import product
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

import microcosm.build.us_runtime.housing_inputs as module
from microcosm.build.us_runtime.housing_constants import US_HOUSING_RECEIPT_COLUMN
from microcosm.build.us_runtime.housing_inputs import (
    ACS_2022_RENT_ARTIFACT_SHA256,
    HOUSING_INPUTS_ARCHIVED_ACS_DERIVATION_URL,
    HOUSING_INPUTS_ARCHIVED_CPS_RENT_URL,
    HOUSING_INPUTS_ARCHIVED_CPS_SPM_URL,
    HOUSING_INPUTS_ARCHIVED_PUF_IMPUTATION_URL,
    HOUSING_TAKE_UP_ARCHIVED_DERIVATION_URL,
    HOUSING_TAKE_UP_ARCHIVED_HUD_ETL_URL,
    HOUSING_TAKE_UP_ARCHIVED_PARAMETER_URL,
    US_HOUSING_INPUTS_OUTPUT_COLUMNS,
    US_HOUSING_MODEL_INPUT_COLUMNS,
    US_HOUSING_NONCONSTANT_HOUSEHOLD_COLUMNS,
    US_HOUSING_NONCONSTANT_PERSON_COLUMNS,
    US_HOUSING_NONCONSTANT_SPM_UNIT_COLUMNS,
    derive_us_housing_inputs,
    impute_us_housing_assistance_to_puf_support,
    load_acs_2022_rent_donor,
    us_housing_inputs_signal_gate,
    us_housing_inputs_stage_spec,
    with_us_housing_inputs,
)
from microcosm.build.us_runtime.l0_refit_export import (
    US_RELEASE_REQUIRED_HOUSEHOLD_NONCONSTANT_SOURCE_COLUMNS,
    US_RELEASE_REQUIRED_PERSON_SOURCE_COLUMNS,
    US_RELEASE_REQUIRED_SPM_UNIT_SOURCE_COLUMNS,
)
from microcosm.build.us_runtime.puf_support import (
    BASE_ASEC_SUPPORT_CHANNEL,
    PUF_TAX_DETAIL_SUPPORT_CHANNEL,
    clone_us_frame_for_puf_support,
    support_channel_column,
)
from microcosm.build.us_runtime.release_input_coverage import (
    RESTORED_REFERENCE_ECPS_REQUIRED_INPUTS,
    load_release_input_coverage_manifest,
    us_release_reform_coverage_probes,
)
from microcosm.build.us_runtime.support_provenance import (
    spine_assembly_manifest,
    spine_source_id_column,
    support_clone_index_column,
    support_source_id_column,
)
from microcosm.build.us_runtime.take_up_contract import load_take_up_contract
from microcosm.frame import US_SCHEMA, Frame, WeightKind, Weights


def _frame() -> Frame:
    n = 20
    household_ids = np.arange(1, n + 1, dtype=np.int64)
    person = pd.DataFrame(
        {
            "person_id": household_ids,
            "person_household_id": household_ids,
            "person_tax_unit_id": household_ids + 100,
            "person_spm_unit_id": household_ids + 200,
            "person_family_id": household_ids + 300,
            "person_marital_unit_id": household_ids + 400,
            "is_household_head": np.ones(n, dtype=bool),
            "tax_unit_role_input": ["HEAD"] * n,
            "age": np.linspace(25, 75, n),
            "is_female": household_ids % 2 == 0,
            "has_esi": household_ids % 3 == 0,
            "employment_income_before_lsr": household_ids * 2_000.0,
            "self_employment_income_before_lsr": household_ids * 100.0,
            "social_security_retirement": np.where(household_ids > 15, 12_000.0, 0.0),
            "social_security_disability": np.zeros(n),
            "social_security_survivors": np.zeros(n),
            "social_security_dependents": np.zeros(n),
            "taxable_private_pension_income": np.where(
                household_ids > 15, 4_000.0, 0.0
            ),
            "tax_exempt_private_pension_income": np.zeros(n),
            "SPM_CAPHOUSESUB": np.where(household_ids == 1, 5_000.0, 0.0),
            "SPM_TENMORTSTATUS": np.resize(np.array([3, 1, 2]), n),
        }
    )
    h_tenure = np.where(household_ids <= 4, 2, np.where(household_ids == 5, 3, 1))
    tables = {
        "person": person,
        "household": pd.DataFrame(
            {
                "household_id": household_ids,
                "state_fips": np.where(household_ids <= 10, 6, 36),
                "H_TENURE": h_tenure,
                "HPUBLIC": np.where(
                    household_ids == 1, 1, np.where(h_tenure == 1, 0, 2)
                ),
                "HLORENT": np.where((h_tenure == 1) | (household_ids == 1), 0, 2),
                "I_HPUBLI": np.zeros(n, dtype=int),
                "I_HLOREN": np.zeros(n, dtype=int),
            }
        ),
        "tax_unit": pd.DataFrame(
            {
                "tax_unit_id": household_ids + 100,
                "filing_status_input": ["SINGLE"] * n,
            }
        ),
        "spm_unit": pd.DataFrame({"spm_unit_id": household_ids + 200}),
        "family": pd.DataFrame({"family_id": household_ids + 300}),
        "marital_unit": pd.DataFrame({"marital_unit_id": household_ids + 400}),
    }
    return Frame(
        tables,
        US_SCHEMA,
        {
            "household": Weights(
                np.full(n, 1_000_000.0),
                WeightKind.DESIGN,
            )
        },
    )


def _donor(n: int = 60) -> pd.DataFrame:
    rows = np.arange(n, dtype=np.float64)
    donor = pd.DataFrame(
        {
            predictor: rows + position
            for position, predictor in enumerate(module.ACS_RENT_PREDICTORS)
        }
    )
    donor["is_household_head"] = 1.0
    donor["tenure_type"] = np.resize(
        np.array(["NONE", "OWNED_WITH_MORTGAGE", "RENTED"]), n
    )
    donor["state_code_str"] = np.resize(np.array(["06", "36", "48"]), n)
    donor["rent"] = np.where(donor["tenure_type"] == "RENTED", 12_000.0, 0.0)
    donor["rent_is_allocated"] = False
    donor["real_estate_taxes"] = np.where(
        donor["tenure_type"] == "RENTED", 0.0, 4_000.0
    )
    donor["real_estate_taxes_is_allocated"] = False
    donor["household_weight"] = np.linspace(1.0, 2.0, n)
    return donor


class _RentFitted:
    def predict(self, test: pd.DataFrame, **kwargs) -> pd.DataFrame:
        rented = test["tenure_type__RENTED"] > 0
        return pd.DataFrame(
            {"rent": np.where(rented, 12_000.0, 0.0)},
            index=test.index,
        )


class _RentQRF:
    def __init__(self, **_kwargs: object) -> None:
        pass

    def fit(self, *_args: object, **_kwargs: object) -> _RentFitted:
        return _RentFitted()


def test_stage_manifest_pins_exact_archived_sources_and_two_qrfs() -> None:
    spec = us_housing_inputs_stage_spec()

    assert spec.stage == "acs_rent"
    assert spec.outputs == US_HOUSING_INPUTS_OUTPUT_COLUMNS
    assert [operation.kind for operation in spec.operations] == [
        "derive_housing_tenure_inputs",
        "read_acs_rent_donor",
        "fit_weighted_acs_rent_qrf",
        "impute_housing_assistance_to_puf_support",
    ]
    rent_fit = spec.operations[2]
    assert tuple(rent_fit.parameters["predictors"]) == module.ACS_RENT_PREDICTORS
    assert rent_fit.parameters["max_train_samples"] == 10_000
    assert rent_fit.parameters["shared_sample_targets"] == [
        "rent",
        "real_estate_taxes",
    ]
    assert rent_fit.parameters["per_target_initial_cap"] == 5_000
    assert rent_fit.parameters["weight"] == "household_weight"
    puf_fit = spec.operations[3]
    assert puf_fit.parameters["max_train_samples"] == 5_000
    assert puf_fit.parameters["reduction"] == "household_head_spm_unit"
    assert puf_fit.parameters["target"] == US_HOUSING_RECEIPT_COLUMN
    assert puf_fit.parameters["training_grain"] == "household_head"
    assert puf_fit.parameters["take_up_output"] == (
        "takes_up_housing_assistance_if_eligible"
    )
    direct = spec.operations[0]
    assert direct.parameters["housing_take_up_assignment"] == (
        "equal_to_reported_receipt"
    )
    assert all(
        url.startswith(
            "https://github.com/PolicyEngine/" + "policyengine-" + "us-data/blob/"
            "42ed5d45c56df80d754fbe24cce21cfeb8d05cbe/"
        )
        for url in (
            HOUSING_INPUTS_ARCHIVED_CPS_RENT_URL,
            HOUSING_INPUTS_ARCHIVED_CPS_SPM_URL,
            HOUSING_INPUTS_ARCHIVED_ACS_DERIVATION_URL,
            HOUSING_INPUTS_ARCHIVED_PUF_IMPUTATION_URL,
            HOUSING_TAKE_UP_ARCHIVED_DERIVATION_URL,
            HOUSING_TAKE_UP_ARCHIVED_PARAMETER_URL,
            HOUSING_TAKE_UP_ARCHIVED_HUD_ETL_URL,
        )
    )
    artifact = next(artifact for artifact in spec.artifacts if artifact.get("sha256"))
    assert artifact["sha256"] == ACS_2022_RENT_ARTIFACT_SHA256
    assert HOUSING_TAKE_UP_ARCHIVED_DERIVATION_URL.endswith(
        "/datasets/cps/cps.py#L664-L682"
    )
    assert HOUSING_TAKE_UP_ARCHIVED_PARAMETER_URL.endswith(
        "/parameters/take_up/housing_assistance.yaml#L1-L15"
    )
    assert HOUSING_TAKE_UP_ARCHIVED_HUD_ETL_URL.endswith(
        "/db/etl_housing_assistance.py#L35-L169"
    )


def test_direct_asec_mappings_are_exact() -> None:
    result = derive_us_housing_inputs(_frame())

    household = result.table("household")
    assert household["tenure_type"].tolist()[:6] == [
        "RENTED",
        "RENTED",
        "RENTED",
        "RENTED",
        "NONE",
        "OWNED_WITH_MORTGAGE",
    ]
    spm = result.table("spm_unit")
    assert household[US_HOUSING_RECEIPT_COLUMN].sum() == 1
    assert spm["receives_housing_assistance"].tolist().count(True) == 1
    pd.testing.assert_series_equal(
        spm["takes_up_housing_assistance_if_eligible"],
        spm["receives_housing_assistance"],
        check_names=False,
    )
    assert spm["spm_unit_tenure_type"].tolist()[:3] == [
        "RENTER",
        "OWNER_WITH_MORTGAGE",
        "OWNER_WITHOUT_MORTGAGE",
    ]


def test_direct_mapping_rejects_inconsistent_spm_replicas() -> None:
    frame = _frame()
    extra = frame.table("person").iloc[[0]].copy()
    extra["person_id"] = 999
    extra["SPM_TENMORTSTATUS"] = 2
    extra["is_household_head"] = False
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    tables["person"] = pd.concat([tables["person"], extra], ignore_index=True)
    broken = Frame(tables, frame.schema, {"household": frame.weights_for("household")})

    with pytest.raises(ValueError, match="constant within its SPM unit"):
        derive_us_housing_inputs(broken)


def test_materialization_places_rent_only_on_renter_heads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _RentQRF)

    result = with_us_housing_inputs(
        _frame(),
        seed=0,
        time_period=2024,
        acs_rent_donor=_donor(),
    )

    rent = result.table("person")["pre_subsidy_rent"]
    assert rent.tolist()[:6] == [12_000.0] * 4 + [0.0, 0.0]
    gate = us_housing_inputs_signal_gate(result)
    assert gate.passed, gate.failures


@pytest.mark.parametrize(
    "tenure,public,reduced", product((1, 2, 3), (0, 1, 2), (0, 1, 2))
)
def test_receipt_decodes_exact_census_tenure_and_skip_universe(tenure, public, reduced):
    frame = _frame()
    frame.table("household").loc[0, ["H_TENURE", "HPUBLIC", "HLORENT"]] = [
        tenure,
        public,
        reduced,
    ]
    valid = (tenure == 1 and (public, reduced) == (0, 0)) or (
        tenure in (2, 3) and (public, reduced) in ((1, 0), (2, 1), (2, 2))
    )
    if not valid:
        with pytest.raises(ValueError, match="tenure/skip universe"):
            derive_us_housing_inputs(frame)
        return
    result = derive_us_housing_inputs(frame)
    expected = public == 1 or reduced == 1
    assert bool(result.table("household").loc[0, US_HOUSING_RECEIPT_COLUMN]) == expected
    assert (
        bool(result.table("spm_unit").loc[0, "receives_housing_assistance"]) == expected
    )


@pytest.mark.parametrize(
    "column", ("H_TENURE", "HPUBLIC", "HLORENT", "I_HPUBLI", "I_HLOREN")
)
@pytest.mark.parametrize("value", (None, np.nan, -1, 0.5, 4))
def test_receipt_rejects_missing_and_invalid_source_codes(column, value):
    frame = _frame()
    frame.table("household")[column] = frame.table("household")[column].astype(object)
    frame.table("household").loc[0, column] = value
    with pytest.raises(ValueError, match=column):
        derive_us_housing_inputs(frame)


def _multiple_unit_household() -> Frame:
    frame = _frame()
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    extra = tables["person"].iloc[[0]].copy()
    extra["person_id"] = 999
    extra["is_household_head"] = False
    for entity in ("spm_unit", "tax_unit", "family", "marital_unit"):
        extra[f"person_{entity}_id"] = 999
        row = tables[entity].iloc[[0]].copy()
        row[f"{entity}_id"] = 999
        tables[entity] = pd.concat([tables[entity], row], ignore_index=True)
    # The nonhead comes first, so a first-person reduction is not an award rule.
    tables["person"] = pd.concat([extra, tables["person"]], ignore_index=True)
    return Frame(tables, frame.schema, {"household": frame.weights_for("household")})


def test_single_award_belongs_to_household_head_unit_and_is_cap_independent():
    reference = None
    for capped_value in (None, 0, 1_000_000):
        frame = _multiple_unit_household()
        if capped_value is None:
            frame.table("person").drop(columns=["SPM_CAPHOUSESUB"], inplace=True)
        else:
            frame.table("person")["SPM_CAPHOUSESUB"] = capped_value
        result = derive_us_housing_inputs(frame)
        spm = result.table("spm_unit").set_index("spm_unit_id")
        assert spm["receives_housing_assistance"].sum() == 1
        assert bool(spm.loc[201, "receives_housing_assistance"])
        assert not bool(spm.loc[999, "receives_housing_assistance"])
        pd.testing.assert_series_equal(
            spm["receives_housing_assistance"],
            spm["takes_up_housing_assistance_if_eligible"],
            check_names=False,
        )
        if reference is not None:
            for entity in ("household", "spm_unit"):
                pd.testing.assert_frame_equal(
                    result.table(entity), reference.table(entity)
                )
        reference = result


def test_signal_gate_rejects_broadcast_receipt_even_when_flags_agree():
    result = derive_us_housing_inputs(_multiple_unit_household())
    result.table("person")["pre_subsidy_rent"] = 0.0
    result.table("spm_unit").loc[
        result.table("spm_unit")["spm_unit_id"].eq(999),
        ["receives_housing_assistance", "takes_up_housing_assistance_if_eligible"],
    ] = True
    gate = us_housing_inputs_signal_gate(result)
    assert not gate.passed
    assert gate.details["housing_assistance_head_unit_mismatch_count"] == 1
    assert gate.details["housing_assistance_take_up_source_mismatch_count"] == 0


def _mixed_spine_housing_frame() -> Frame:
    source = derive_us_housing_inputs(_multiple_unit_household())
    person = source.table("person")
    person["pre_subsidy_rent"] = np.where(
        person["is_household_head"] & person["person_household_id"].le(4),
        12_000.0,
        0.0,
    )
    tables = {}
    for entity in source.entities:
        native = source.table(entity).copy()
        acs = native.copy()
        primary = source.schema.entity_id_column(entity)
        acs[primary] += 10_000
        if entity == "person":
            for group in source.schema.group_entities:
                acs[source.schema.membership_column(group)] += 10_000
        for channel, table in (("asec", native), ("acs", acs)):
            table[support_channel_column(entity)] = channel
            table[support_clone_index_column(entity)] = 0
            table[support_source_id_column(entity)] = table[primary]
            table[spine_source_id_column(entity)] = native[primary].to_numpy()
        if entity == "household":
            acs[US_HOUSING_RECEIPT_COLUMN] = None
        if entity == "spm_unit":
            # ACS model inputs can be transferred to a nonhead SPM unit;
            # no CPS observed-receipt/head-unit assertion applies to it.
            for column in (
                "receives_housing_assistance",
                "takes_up_housing_assistance_if_eligible",
            ):
                acs[column] = acs[primary].eq(10_999)
        tables[entity] = pd.concat([native, acs], ignore_index=True)
    assembled = Frame(
        tables,
        source.schema,
        {
            "household": Weights(
                np.tile(source.weights_for("household").values, 2),
                WeightKind.DESIGN,
            )
        },
        metadata=spine_assembly_manifest(tables, channels=("asec", "acs")),
    )
    return clone_us_frame_for_puf_support(assembled)


def test_signal_gate_accepts_nullable_acs_evidence_and_preserves_all_rows():
    frame = _mixed_spine_housing_frame()
    before = {entity: frame.table(entity).copy(deep=True) for entity in frame.entities}

    gate = us_housing_inputs_signal_gate(frame)

    assert gate.passed, gate.failures
    assert gate.details["housing_assistance_reported_receipt_missing_count"] == 0
    assert gate.details["housing_assistance_head_unit_mismatch_count"] == 0
    assert gate.details["housing_assistance_evidence_household_count"] == 40
    assert gate.details["housing_assistance_evidence_spm_unit_count"] == 42
    for entity in frame.entities:
        pd.testing.assert_frame_equal(frame.table(entity), before[entity])


def test_signal_gate_accepts_selected_support_with_ancestor_assembly_counts():
    frame = _mixed_spine_housing_frame()
    selected = frame.select(frame.table("person")["person_household_id"].ne(20))
    before_metadata = selected.metadata

    gate = us_housing_inputs_signal_gate(selected)

    assert gate.passed, gate.failures
    assert gate.details["housing_assistance_evidence_household_count"] == 39
    assert gate.details["housing_assistance_evidence_spm_unit_count"] == 41
    assert selected.metadata == before_metadata == frame.metadata


def test_signal_gate_accepts_authenticated_empty_cps_evidence_scope():
    frame = _mixed_spine_housing_frame()
    acs_only = frame.select(
        frame.table("person")[support_channel_column("person")].eq("acs")
    )

    gate = us_housing_inputs_signal_gate(acs_only)

    assert gate.passed, gate.failures
    assert gate.details["housing_assistance_evidence_household_count"] == 0
    assert gate.details["housing_assistance_evidence_spm_unit_count"] == 0
    assert acs_only.table("household")[US_HOUSING_RECEIPT_COLUMN].isna().all()
    assert acs_only.metadata == frame.metadata
    acs_only.table("spm_unit")["takes_up_housing_assistance_if_eligible"] = True
    assert not us_housing_inputs_signal_gate(acs_only).passed


@pytest.mark.parametrize("tamper", ("unknown_channel", "cross_grain"))
def test_signal_gate_rejects_tampered_empty_cps_scope(tamper):
    frame = _mixed_spine_housing_frame()
    acs_only = frame.select(
        frame.table("person")[support_channel_column("person")].eq("acs")
    )
    person = acs_only.table("person")
    person.iloc[0, person.columns.get_loc(support_channel_column("person"))] = (
        "unknown_source" if tamper == "unknown_channel" else "asec"
    )

    with pytest.raises(ValueError, match="assembly manifest"):
        us_housing_inputs_signal_gate(acs_only)


@pytest.mark.parametrize("orphan_entity", ("household", "spm_unit"))
def test_signal_gate_rejects_orphan_cps_entities_in_empty_person_scope(orphan_entity):
    frame = _mixed_spine_housing_frame()
    acs_only = frame.select(
        frame.table("person")[support_channel_column("person")].eq("acs")
    )
    # Frame construction already forbids orphans. Exercise the defensive gate
    # projection against live-table tampering before unrelated weight checks.
    table = acs_only.table(orphan_entity)
    table.loc[len(table)] = frame.table(orphan_entity).iloc[0]
    with pytest.raises(ValueError, match="orphan CPS source entities"):
        module._housing_receipt_evidence_projection(acs_only)


@pytest.mark.parametrize("clone_index", (0, 1))
@pytest.mark.parametrize("bad_value", (None, "invalid"))
def test_signal_gate_requires_reported_receipt_on_cps_and_puf(clone_index, bad_value):
    frame = _mixed_spine_housing_frame()
    household = frame.table("household")
    selected = household[support_channel_column("household")].eq("asec") & household[
        support_clone_index_column("household")
    ].eq(clone_index)
    household.loc[selected, US_HOUSING_RECEIPT_COLUMN] = bad_value

    gate = us_housing_inputs_signal_gate(frame)

    assert not gate.passed
    assert any("reported household housing receipt" in item for item in gate.failures)


@pytest.mark.parametrize("clone_index", (0, 1))
def test_signal_gate_still_requires_head_unit_receipt_on_cps_and_puf(clone_index):
    frame = _mixed_spine_housing_frame()
    spm = frame.table("spm_unit")
    selected = (
        spm[support_channel_column("spm_unit")].eq("asec")
        & spm[support_clone_index_column("spm_unit")].eq(clone_index)
        & spm[spine_source_id_column("spm_unit")].eq(999)
    )
    spm.loc[
        selected,
        ["receives_housing_assistance", "takes_up_housing_assistance_if_eligible"],
    ] = True

    gate = us_housing_inputs_signal_gate(frame)

    assert not gate.passed
    assert gate.details["housing_assistance_head_unit_mismatch_count"] == 1
    assert gate.details["housing_assistance_take_up_source_mismatch_count"] == 0


@pytest.mark.parametrize("clone_index", (0, 1))
@pytest.mark.parametrize(
    "column,bad_value",
    (
        ("receives_housing_assistance", None),
        ("receives_housing_assistance", "invalid"),
        ("takes_up_housing_assistance_if_eligible", None),
        ("takes_up_housing_assistance_if_eligible", "invalid"),
        ("takes_up_housing_assistance_if_eligible", True),
    ),
)
def test_signal_gate_still_checks_acs_model_receipt_and_take_up(
    clone_index, column, bad_value
):
    frame = _mixed_spine_housing_frame()
    spm = frame.table("spm_unit")
    spm[column] = spm[column].astype(object)
    selected = spm[support_channel_column("spm_unit")].eq("acs") & spm[
        support_clone_index_column("spm_unit")
    ].eq(clone_index)
    spm.loc[selected, column] = bad_value

    gate = us_housing_inputs_signal_gate(frame)

    assert not gate.passed
    assert any(column in item for item in gate.failures)


@pytest.mark.parametrize(
    "tamper", ("missing_manifest", "household_channel", "missing_raw_spine")
)
def test_signal_gate_authenticates_assembled_receipt_scope(tamper):
    frame = _mixed_spine_housing_frame()
    if tamper == "missing_manifest":
        frame = Frame(
            {entity: frame.table(entity) for entity in frame.entities},
            frame.schema,
            {"household": frame.weights_for("household")},
            frame.strata,
        )
    elif tamper == "household_channel":
        frame.table("household").loc[0, support_channel_column("household")] = "acs"
    else:
        frame.table("household").drop(
            columns=[spine_source_id_column("household")], inplace=True
        )

    with pytest.raises(ValueError, match="assembly manifest"):
        us_housing_inputs_signal_gate(frame)


def test_receipt_evidence_is_owned_but_not_a_country_input_or_acs_transfer_target():
    from microcosm.build.us_runtime.multispine_pool import pool_input_surface
    from microcosm.build.us_runtime.operator_boundary import (
        PRE_ASSEMBLY_OPERATOR_OUTPUT_FAMILIES,
    )
    from microcosm.build.us_runtime.us_late_producer_registry import (
        US_LATE_SOURCE_INPUT_INVENTORIES,
    )

    assert US_HOUSING_RECEIPT_COLUMN not in {
        entry.variable for entry in pool_input_surface()
    }
    assert (
        US_HOUSING_RECEIPT_COLUMN
        in PRE_ASSEMBLY_OPERATOR_OUTPUT_FAMILIES["housing_assistance"]["household"]
    )
    inventory = US_LATE_SOURCE_INPUT_INVENTORIES[
        "impute_us_housing_assistance_to_puf_support"
    ]
    columns = {
        column.column
        for requirement in inventory.requirements
        for alternative in requirement.alternatives
        for column in alternative
    }
    assert US_HOUSING_RECEIPT_COLUMN in columns
    assert (
        not {
            "SPM_CAPHOUSESUB",
            "receives_housing_assistance",
            "takes_up_housing_assistance_if_eligible",
        }
        & columns
    )


@pytest.mark.parametrize("duplicate", (False, True))
def test_receipt_requires_exactly_one_head(duplicate):
    frame = _multiple_unit_household()
    frame.table("person").loc[0 if duplicate else 1, "is_household_head"] = duplicate
    with pytest.raises(
        ValueError, match="heads per household|household-head alignment"
    ):
        derive_us_housing_inputs(frame)


def test_puf_fit_uses_one_head_per_household_and_reassigns_only_head_unit(monkeypatch):
    direct = derive_us_housing_inputs(_multiple_unit_household())
    expanded = clone_us_frame_for_puf_support(direct)
    # Old model flags are outputs, not training evidence or prerequisites.
    expanded.table("spm_unit")["receives_housing_assistance"] = True
    expanded.table("spm_unit")["takes_up_housing_assistance_if_eligible"] = False
    captured = {}

    class QRF:
        def __init__(self, **kwargs):
            captured["init"] = kwargs

        def fit(self, training, *, predictors, targets, weights):
            captured.update(
                training=training.copy(),
                predictors=predictors,
                targets=targets,
                weights=weights.copy(),
            )
            return self

        def predict(self, test):
            captured["test"] = test.copy()
            return pd.DataFrame(
                {US_HOUSING_RECEIPT_COLUMN: np.ones(len(test))}, index=test.index
            )

    monkeypatch.setattr(module, "QRF", QRF)
    result = impute_us_housing_assistance_to_puf_support(expanded, seed=17)
    assert len(captured["training"]) == len(captured["test"]) == 20
    assert captured["training"][US_HOUSING_RECEIPT_COLUMN].sum() == 1
    assert len(captured["predictors"]) == 8
    assert captured["targets"] == [US_HOUSING_RECEIPT_COLUMN]
    assert captured["init"] == {"n_estimators": 100, "seed": 17}
    person = expanded.table("person")
    head_mask = person["is_household_head"].to_numpy(dtype=bool)
    expected_weights = pd.Series(
        expanded.resolve_weights("person").values[head_mask],
        index=person.loc[head_mask, "person_household_id"],
    ).loc[captured["training"].index]
    np.testing.assert_array_equal(captured["weights"], expected_weights)
    household = result.table("household")
    puf = (
        household[support_channel_column("household")] == PUF_TAX_DETAIL_SUPPORT_CHANNEL
    )
    assert household.loc[puf, US_HOUSING_RECEIPT_COLUMN].sum() == 20
    assert household.loc[~puf, US_HOUSING_RECEIPT_COLUMN].sum() == 1
    spm = result.table("spm_unit")
    puf_spm = spm[support_channel_column("spm_unit")] == PUF_TAX_DETAIL_SUPPORT_CHANNEL
    assert puf_spm.sum() == 21
    assert spm.loc[puf_spm, "receives_housing_assistance"].sum() == 20
    assert spm.loc[~puf_spm, "receives_housing_assistance"].sum() == 1
    pd.testing.assert_series_equal(
        spm["receives_housing_assistance"],
        spm["takes_up_housing_assistance_if_eligible"],
        check_names=False,
    )


def test_real_puf_receipt_fit_is_reproducible_and_preserves_source_households(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("quantile_forest")
    from microcosm.fit import QRF

    monkeypatch.setattr(module, "QRF", QRF)
    expanded = clone_us_frame_for_puf_support(
        derive_us_housing_inputs(_multiple_unit_household())
    )
    first = impute_us_housing_assistance_to_puf_support(
        expanded, seed=17, n_estimators=3
    )
    second = impute_us_housing_assistance_to_puf_support(
        expanded, seed=17, n_estimators=3
    )
    for entity in first.entities:
        pd.testing.assert_frame_equal(first.table(entity), second.table(entity))
    for entity, columns in (
        ("household", (US_HOUSING_RECEIPT_COLUMN,)),
        (
            "spm_unit",
            ("receives_housing_assistance", "takes_up_housing_assistance_if_eligible"),
        ),
    ):
        source = expanded.table(entity)
        asec = source[support_channel_column(entity)].eq(BASE_ASEC_SUPPORT_CHANNEL)
        pd.testing.assert_frame_equal(
            first.table(entity).loc[asec, list(columns)],
            source.loc[asec, list(columns)],
        )
    # Even a real fit can only assign awards to declared household heads.
    heads = first.table("person").query("is_household_head")
    spm = first.table("spm_unit")
    assert not spm.loc[
        ~spm["spm_unit_id"].isin(heads["person_spm_unit_id"]),
        "receives_housing_assistance",
    ].any()


def _duplicate_row_labels(frame: Frame, *, reverse_people: bool = False) -> Frame:
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    strata = frame.strata.copy()
    if reverse_people:
        tables["person"] = tables["person"].iloc[::-1].copy()
        strata = strata.iloc[::-1].copy()
    for table in tables.values():
        table.index = ["same"] * len(table)
    strata.index = tables["person"].index
    # Reconstruct a valid Frame, including its index-aligned stratum labels.
    return Frame(
        tables,
        frame.schema,
        {entity: frame.weights_for(entity) for entity in frame.weighted_entities},
        strata,
        mass_log=frame.mass_log,
        metadata=frame.metadata,
    )


def test_rent_head_mapping_preserves_duplicate_row_labels_and_person_order(monkeypatch):
    direct = _duplicate_row_labels(
        derive_us_housing_inputs(_multiple_unit_household()), reverse_people=True
    )
    person = direct.table("person")

    class Fitted:
        def predict(self, test):
            # The feature table is indexed by household identity.
            return pd.DataFrame(
                {"rent": test.index.to_numpy() * 100.0}, index=test.index
            )

    class QRF:
        def __init__(self, **kwargs):
            pass

        def fit(self, *args, **kwargs):
            return Fitted()

    monkeypatch.setattr(module, "QRF", QRF)
    rent = module.impute_us_pre_subsidy_rent(direct, _donor(), seed=0)
    expected = np.where(
        person["is_household_head"].to_numpy(),
        person["person_household_id"].to_numpy() * 100.0,
        0.0,
    )
    np.testing.assert_array_equal(rent, expected)
    assert person.index.tolist() == ["same"] * len(person)


@pytest.mark.parametrize("missing_prediction", (False, True))
def test_puf_head_fit_preserves_duplicate_entity_row_labels(
    monkeypatch, missing_prediction
):
    expanded = clone_us_frame_for_puf_support(
        derive_us_housing_inputs(_multiple_unit_household())
    )
    expanded = _duplicate_row_labels(expanded)
    captured = {}

    class QRF:
        def __init__(self, **kwargs):
            pass

        def fit(self, training, *, predictors, targets, weights):
            captured.update(training=training.copy(), weights=weights.copy())
            return self

        def predict(self, test):
            captured["test"] = test.copy()
            values = np.zeros(len(test))
            if missing_prediction:
                values[0] = np.nan
            return pd.DataFrame({US_HOUSING_RECEIPT_COLUMN: values}, index=test.index)

    monkeypatch.setattr(module, "QRF", QRF)
    if missing_prediction:
        with pytest.raises(ValueError, match="nonfinite predictions"):
            impute_us_housing_assistance_to_puf_support(expanded, seed=0)
        return
    result = impute_us_housing_assistance_to_puf_support(expanded, seed=0)
    assert len(captured["training"]) == len(captured["test"]) == 20
    assert len(captured["weights"]) == 20
    assert captured["training"].index.is_unique
    assert captured["test"].index.is_unique
    household = result.table("household")
    puf = household[support_channel_column("household")].eq(
        PUF_TAX_DETAIL_SUPPORT_CHANNEL
    )
    assert not household.loc[puf, US_HOUSING_RECEIPT_COLUMN].any()
    for entity in expanded.entities:
        assert result.table(entity).index.equals(expanded.table(entity).index)


def test_rent_fit_replays_archived_joint_target_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    donor = _donor(12_000)
    positions = np.arange(len(donor))
    donor["rent_is_allocated"] = positions >= 6_000
    donor["real_estate_taxes_is_allocated"] = positions < 6_000
    captured: dict[str, object] = {}

    class Fitted:
        def predict(self, test: pd.DataFrame, **kwargs) -> pd.DataFrame:
            return pd.DataFrame({"rent": np.zeros(len(test))}, index=test.index)

    class QRF:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def fit(
            self,
            training: pd.DataFrame,
            *,
            predictors: list[str],
            targets: list[str],
            weights: str,
        ) -> Fitted:
            captured["training"] = training.copy()
            captured["predictors"] = predictors
            captured["targets"] = targets
            captured["weights"] = weights
            return Fitted()

    monkeypatch.setattr(module, "QRF", QRF)
    module.impute_us_pre_subsidy_rent(derive_us_housing_inputs(_frame()), donor, seed=0)

    # The retired shared cap first draws 5,000 rent rows and 5,000 disjoint
    # real-estate-tax rows.  Only the rent-filtered half trains this first
    # chained target; sampling 10,000 rent rows directly would violate parity.
    assert len(captured["training"]) == 5_000
    assert captured["targets"] == ["rent"]
    assert captured["weights"] == "household_weight"


def test_signal_gate_preserves_archived_qrf_rent_outside_renter_household(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _RentQRF)
    result = with_us_housing_inputs(
        _frame(), seed=0, time_period=2024, acs_rent_donor=_donor()
    )
    result.table("person").loc[5, "pre_subsidy_rent"] = 1.0

    gate = us_housing_inputs_signal_gate(result)

    assert gate.passed, gate.failures
    assert gate.details["positive_rent_nonrenter"] == 1


def test_puf_half_reimputes_only_housing_assistance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _RentQRF)
    direct = with_us_housing_inputs(
        _frame(), seed=0, time_period=2024, acs_rent_donor=_donor()
    )
    expanded = clone_us_frame_for_puf_support(direct)
    calls: dict[str, object] = {}

    class Fitted:
        def predict(self, test: pd.DataFrame, **kwargs) -> pd.DataFrame:
            values = np.zeros(len(test), dtype=np.float64)
            values[1] = 1.0
            return pd.DataFrame({US_HOUSING_RECEIPT_COLUMN: values}, index=test.index)

    class QRF:
        def __init__(self, **kwargs: object) -> None:
            calls["init"] = kwargs

        def fit(
            self,
            training: pd.DataFrame,
            predictors: list[str],
            targets: list[str],
            **kwargs: object,
        ) -> Fitted:
            calls["training"] = training.copy()
            calls["predictors"] = predictors
            calls["targets"] = targets
            calls["fit_kwargs"] = kwargs
            return Fitted()

    monkeypatch.setattr(module, "QRF", QRF)
    result = impute_us_housing_assistance_to_puf_support(expanded, seed=7)

    spm = result.table("spm_unit")
    channel = spm[support_channel_column("spm_unit")]
    asec = channel == BASE_ASEC_SUPPORT_CHANNEL
    puf = channel == PUF_TAX_DETAIL_SUPPORT_CHANNEL
    assert spm.loc[asec, "receives_housing_assistance"].sum() == 1
    assert spm.loc[puf, "receives_housing_assistance"].sum() == 1
    assert not np.array_equal(
        spm.loc[asec, "receives_housing_assistance"].to_numpy(),
        spm.loc[puf, "receives_housing_assistance"].to_numpy(),
    )
    pd.testing.assert_series_equal(
        spm["takes_up_housing_assistance_if_eligible"],
        spm["receives_housing_assistance"],
        check_names=False,
    )
    assert calls["targets"] == [US_HOUSING_RECEIPT_COLUMN]
    assert len(calls["predictors"]) == 8
    assert "pre_subsidy_rent" not in calls["targets"]
    for entity, column in (
        ("person", "pre_subsidy_rent"),
        ("spm_unit", "spm_unit_tenure_type"),
        ("household", "tenure_type"),
    ):
        source = expanded.table(entity)[column]
        actual = result.table(entity)[column]
        pd.testing.assert_series_equal(actual, source)

    result.table("spm_unit").loc[puf, "receives_housing_assistance"] = False
    collapsed_gate = us_housing_inputs_signal_gate(result)
    assert not collapsed_gate.passed
    assert any("PUF-tax-detail" in failure for failure in collapsed_gate.failures)


@pytest.mark.parametrize("bad_value", [None, np.nan, 2, -1, "true"])
def test_signal_gate_rejects_missing_or_invalid_take_up(bad_value: object) -> None:
    result = derive_us_housing_inputs(_frame())
    result.table("spm_unit")["takes_up_housing_assistance_if_eligible"] = result.table(
        "spm_unit"
    )["takes_up_housing_assistance_if_eligible"].astype(object)
    result.table("spm_unit").loc[0, "takes_up_housing_assistance_if_eligible"] = (
        bad_value
    )
    result.table("person")["pre_subsidy_rent"] = np.where(
        result.table("person")["is_household_head"],
        1.0,
        0.0,
    )

    gate = us_housing_inputs_signal_gate(result)

    assert not gate.passed
    assert any("takes_up_housing_assistance" in failure for failure in gate.failures)


def _write_tiny_acs(path: Path) -> None:
    arrays = {
        "person_id": np.array([1, 2, 3, 4]),
        "person_household_id": np.array([10, 10, 20, 30]),
        "is_household_head": np.array([True, False, True, True]),
        "age": np.array([40, 38, 50, 60]),
        "is_male": np.array([True, False, True, False]),
        "employment_income": np.array([50_000, 20_000, 0, 10_000]),
        "self_employment_income": np.array([0, 0, 5_000, 0]),
        "social_security": np.array([0, 0, 10_000, 12_000]),
        "taxable_private_pension_income": np.array([0, 0, 3_000, 4_000]),
        "rent": np.array([12_000, 0, 0, 18_000]),
        "rent_is_allocated": np.array([False, False, True, False]),
        "real_estate_taxes": np.array([0, 0, 8_000, 4_000]),
        "real_estate_taxes_is_allocated": np.array([False, False, False, True]),
        "household_id": np.array([10, 20, 30]),
        "household_weight": np.array([100.0, 200.0, 300.0]),
        "state_fips": np.array([6, 36, 48]),
        "tenure_type": np.array([b"RENTED", b"OWNED_OUTRIGHT", b"OWNED_WITH_MORTGAGE"]),
    }
    with h5py.File(path, "w") as h5:
        for name, values in arrays.items():
            h5[name] = values


def test_acs_loader_aligns_entities_collapses_tenure_and_marks_allocations(
    tmp_path: Path,
) -> None:
    path = tmp_path / "acs_2022.h5"
    _write_tiny_acs(path)

    donor = load_acs_2022_rent_donor(path, expected_sha256=None)

    assert len(donor) == 3
    assert donor["household_size"].tolist() == [2.0, 1.0, 1.0]
    assert donor["tenure_type"].tolist() == [
        "RENTED",
        "OWNED_WITH_MORTGAGE",
        "OWNED_WITH_MORTGAGE",
    ]
    assert donor["state_code_str"].tolist() == ["06", "36", "48"]
    assert donor["rent"].tolist() == [12_000.0, 0.0, 18_000.0]
    assert donor["rent_is_allocated"].tolist() == [False, True, False]
    assert donor["real_estate_taxes"].tolist() == [0.0, 8_000.0, 4_000.0]
    assert donor["real_estate_taxes_is_allocated"].tolist() == [False, False, True]
    assert donor["household_weight"].tolist() == [100.0, 200.0, 300.0]


def test_acs_loader_rejects_wrong_artifact_hash(tmp_path: Path) -> None:
    path = tmp_path / "acs_2022.h5"
    _write_tiny_acs(path)

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_acs_2022_rent_donor(path, expected_sha256="0" * 64)


def test_acs_loader_retains_zero_weight_heads_for_archived_sampling(
    tmp_path: Path,
) -> None:
    path = tmp_path / "acs_2022.h5"
    _write_tiny_acs(path)
    with h5py.File(path, "a") as h5:
        h5["household_weight"][1] = 0.0

    donor = load_acs_2022_rent_donor(path, expected_sha256=None)

    assert len(donor) == 3
    assert donor["household_weight"].tolist() == [100.0, 0.0, 300.0]


def test_release_wiring_promotes_all_five_inputs_and_probes() -> None:
    manifest = load_release_input_coverage_manifest()
    for column in US_HOUSING_MODEL_INPUT_COLUMNS:
        assert column in RESTORED_REFERENCE_ECPS_REQUIRED_INPUTS
        assert column in manifest.required_columns
        assert column not in manifest.reviewed_exclusions
    assert US_HOUSING_RECEIPT_COLUMN not in manifest.required_columns
    assert US_HOUSING_RECEIPT_COLUMN not in RESTORED_REFERENCE_ECPS_REQUIRED_INPUTS
    assert set(US_HOUSING_NONCONSTANT_PERSON_COLUMNS) <= set(
        US_RELEASE_REQUIRED_PERSON_SOURCE_COLUMNS
    )
    assert set(US_HOUSING_NONCONSTANT_SPM_UNIT_COLUMNS) <= set(
        US_RELEASE_REQUIRED_SPM_UNIT_SOURCE_COLUMNS
    )
    assert set(US_HOUSING_NONCONSTANT_HOUSEHOLD_COLUMNS) <= set(
        US_RELEASE_REQUIRED_HOUSEHOLD_NONCONSTANT_SOURCE_COLUMNS
    )
    probe = next(
        probe
        for probe in us_release_reform_coverage_probes()
        if probe.id == "pre_subsidy_rent_neutralization"
    )
    assert probe.neutralized_variable == "pre_subsidy_rent"
    assert probe.binding_inputs == ("pre_subsidy_rent",)
    assert probe.budget_measure == "snap"
    assert probe.effect_direction == "baseline_minus_reform"
    assert probe.expected_sign == "positive"
    take_up_probe = next(
        probe
        for probe in us_release_reform_coverage_probes()
        if probe.id == "housing_assistance_take_up_neutralization"
    )
    assert take_up_probe.neutralized_variable == (
        "takes_up_housing_assistance_if_eligible"
    )
    assert take_up_probe.binding_inputs == ("takes_up_housing_assistance_if_eligible",)
    assert take_up_probe.budget_measure == "housing_assistance"
    assert take_up_probe.min_abs_effect == 100_000_000.0
    contract = load_take_up_contract().program_map()[
        "takes_up_housing_assistance_if_eligible"
    ]
    assert contract.populace_treatment == "out_of_scope"
    assert contract.rate == {"status": "not_used_measured_source"}


@pytest.mark.requires_us
def test_policyengine_us_input_contracts_and_rent_consumer() -> None:
    from policyengine_us import CountryTaxBenefitSystem

    system = CountryTaxBenefitSystem()
    expected_entities = {
        "pre_subsidy_rent": "person",
        "receives_housing_assistance": "spm_unit",
        "takes_up_housing_assistance_if_eligible": "spm_unit",
        "spm_unit_tenure_type": "spm_unit",
        "tenure_type": "household",
    }
    for name, entity in expected_entities.items():
        variable = system.variables[name]
        assert variable.is_input_variable()
        assert variable.entity.key == entity
    assert "pre_subsidy_rent" in system.variables["hud_gross_rent"].adds


@pytest.mark.requires_us
def test_policyengine_us_live_housing_take_up_neutralization() -> None:
    from importlib.metadata import version

    from policyengine_us import Simulation

    from microcosm.build.us_runtime.reform_coverage_smoke import _build_reform

    assert version("policyengine-us") == "1.819.0"
    situation = {
        "people": {
            "adult": {
                "age": {"2024": 40},
                "employment_income": {"2024": 0},
                "pre_subsidy_rent": {"2024": 12_000},
            }
        },
        "tax_units": {"tu": {"members": ["adult"]}},
        "families": {"fam": {"members": ["adult"]}},
        "spm_units": {
            "spm": {
                "members": ["adult"],
                "receives_housing_assistance": {"2024": True},
                "takes_up_housing_assistance_if_eligible": {"2024": True},
                "spm_unit_tenure_type": {"2024": "RENTER"},
            }
        },
        "households": {
            "hh": {
                "members": ["adult"],
                "state_code": {"2024": "CA"},
                "county_fips": {"2024": "06037"},
                "bedrooms": {"2024": 1},
            }
        },
        "marital_units": {"mu": {"members": ["adult"]}},
    }
    probe = next(
        probe
        for probe in us_release_reform_coverage_probes()
        if probe.id == "housing_assistance_take_up_neutralization"
    )

    baseline = Simulation(situation=situation)
    neutralized = Simulation(situation=situation, reform=_build_reform(probe))

    assert baseline.calculate("is_eligible_for_housing_assistance", 2024)[0]
    assert baseline.calculate("housing_assistance", 2024)[0] == pytest.approx(11_975)
    assert neutralized.calculate("housing_assistance", 2024)[0] == 0
