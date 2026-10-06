"""Tests split from packages/microcosm-build/tests/test_us_sipp_head_start.py."""

# ruff: noqa: F403, F405
from test_support.microcosm_build.us_sipp_head_start import *


def test_source_coordinates_and_operation_contract_are_exact() -> None:
    assert US_SIPP_HEAD_START_STAGE_NAME == "sipp_head_start"
    assert US_SIPP_HEAD_START_OUTPUT_COLUMNS == ("takes_up_head_start_if_eligible",)
    assert US_SIPP_HEAD_START_NONCONSTANT_PERSON_COLUMNS == (
        "takes_up_head_start_if_eligible",
    )
    assert US_SIPP_HEAD_START_REQUIRED_SOURCE_COLUMNS == (
        "person_source_id",
        "person_household_id",
        "age",
        "is_female",
        "employment_income_before_lsr",
    )
    assert SIPP_2023_HEAD_START_DONOR_REVISION == (
        "21280dca5995e978d706740a8a4b9b7860cfd7b6"
    )
    assert SIPP_2023_HEAD_START_DONOR_SHA256 == (
        "5c30439e365fc26483318ef61d1d8f4bb2f0e9d6bb47c22c06756a7698733ee2"
    )
    assert SIPP_2023_HEAD_START_DONOR_SIZE_BYTES == 3_726_010_471
    assert SIPP_2023_HEAD_START_DONOR_REVISION in SIPP_2023_HEAD_START_DONOR_URL
    assert HEAD_START_SIPP_DICTIONARY_URL.endswith("2023/2023_SIPP_Data_Dictionary.pdf")
    assert SIPP_HEAD_START_READ_PARAMETERS == {
        "table": "sipp_person",
        "delimiter": "|",
        "month_column": "MONTHCODE",
        "month": 12,
        "source_columns": list(SIPP_HEAD_START_SOURCE_COLUMNS),
    }
    assert SIPP_HEAD_START_FIT_PARAMETERS["age_domain"] == [3, 5]
    assert SIPP_HEAD_START_FIT_PARAMETERS["assignment_unit"] == "person_source_id"
    assert SIPP_HEAD_START_FIT_PARAMETERS["fan_to_support_clones"] is True
    assert SIPP_HEAD_START_FIT_PARAMETERS["seed_from_build_config"] is True
    assert "rate" not in " ".join(map(str, SIPP_HEAD_START_FIT_PARAMETERS.values()))

def test_loader_keeps_only_strict_reported_labels(tmp_path: Path) -> None:
    rows = [
        _source_row("yes", 1, head_start_answer=1),
        _source_row("no", 1, head_start_answer=2),
        _source_row(
            "not_enrolled",
            1,
            head_start_status=0,
            head_start_answer=np.nan,
            screen_status=1,
            screen=2,
            grade_status=0,
            grade=np.nan,
        ),
        _source_row(
            "other_grade",
            1,
            head_start_status=0,
            head_start_answer=np.nan,
            screen_status=1,
            screen=1,
            grade_status=1,
            grade=22,
        ),
        _source_row("hot_deck_head_start", 1, head_start_status=2, head_start_answer=1),
        _source_row(
            "unknown_screen",
            1,
            head_start_status=0,
            head_start_answer=np.nan,
            screen_status=4,
            screen=2,
        ),
        _source_row(
            "hot_deck_grade",
            1,
            head_start_status=0,
            head_start_answer=np.nan,
            screen_status=1,
            screen=1,
            grade_status=2,
            grade=22,
        ),
        _source_row("age_two", 1, age=2, head_start_answer=1),
        _source_row("month_eleven", 1, month=11, head_start_answer=1),
    ]
    donor = load_sipp_2023_head_start_donor(
        _write_source(tmp_path, rows),
        expected_sha256=None,
        expected_size_bytes=None,
        chunksize=3,
    )

    assert donor[_OUTPUT].tolist() == [True, False, False, False]
    audit = donor.attrs["source_audit"]
    assert audit["raw_rows"] == 9
    assert audit["december_rows"] == 8
    assert audit["age_domain_rows"] == 7
    assert audit["training_rows"] == 4
    assert audit["positive_rows"] == 1
    assert audit["direct_response_rows"] == 2
    assert audit["reported_no_enrollment_rows"] == 1
    assert audit["reported_other_grade_rows"] == 1
    assert audit["pinned_transform"] is False

def test_loader_refuses_missing_upstream_status(tmp_path: Path) -> None:
    path = _write_source(tmp_path, [_source_row("one", 1)])
    source = pd.read_csv(path, sep="|").drop(columns=["AED_SCRNR"])
    source.to_csv(path, sep="|", index=False)

    with pytest.raises(ValueError, match="AED_SCRNR"):
        load_sipp_2023_head_start_donor(
            path,
            expected_sha256=None,
            expected_size_bytes=None,
        )

def test_pinned_full_file_audit_constants_are_exact() -> None:
    # The 740 negatives are the strict upstream-observed set. A looser
    # status-only mask has 743, but the extra three have no reported screening
    # fact and therefore cannot be called measured structural negatives.
    assert module._PINNED_RAW_ROWS == 476_744
    assert module._PINNED_DECEMBER_ROWS == 39_513
    assert module._PINNED_AGE_DOMAIN_ROWS == 1_177
    assert module._PINNED_TRAINING_ROWS == 785
    assert module._PINNED_POSITIVE_ROWS == 45
    assert module._PINNED_NEGATIVE_ROWS == 740
    assert module._PINNED_DIRECT_RESPONSE_ROWS == 215
    assert module._PINNED_REPORTED_NO_ENROLLMENT_ROWS == 440
    assert module._PINNED_REPORTED_OTHER_GRADE_ROWS == 130
    assert module._PINNED_WEIGHT_SUM == pytest.approx(7_978_494.5412483)
    assert module._PINNED_POSITIVE_WEIGHT_SUM == pytest.approx(491_970.1041311)
    assert module._PINNED_WEIGHTED_TRUE_SHARE == pytest.approx(0.06166202177461505)

def test_imputer_weights_qrf_and_fans_one_asec_decision_to_source_clones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    frame = _frame(
        [10, 10, 20, 30, 30, 40, 40],
        ages=[4, 4, 5, 3, 3, 40, 40],
        # Source 10 deliberately disagrees: canonical ASEC must win. Source 20
        # is PUF-only and remains supported.
        female=[True, False, False, True, False, True, False],
        channels=[
            "asec",
            "puf_tax_detail",
            "puf_tax_detail",
            "asec",
            "puf_tax_detail",
            "asec",
            "puf_tax_detail",
        ],
    )

    first = impute_us_sipp_head_start(frame, _donor(), seed=91)
    second = impute_us_sipp_head_start(frame, _donor(), seed=91)

    assert _FakeQRF.instances[0].n_estimators == 100
    assert _FakeQRF.instances[0].seed == 91
    assert _FakeQRF.instances[0].weights == "sipp_weight"
    np.testing.assert_array_equal(first, second)
    values = pd.DataFrame(
        {
            "source": frame.table("person")["person_source_id"],
            "value": first,
        }
    )
    assert values.groupby("source")["value"].nunique().max() == 1
    assert values[values["source"] == 10]["value"].all()
    assert not values[values["source"] == 20]["value"].any()
    assert values[values["source"] == 30]["value"].all()
    # An off-domain adult is always false even if the QRF would draw true.
    assert not values[values["source"] == 40]["value"].any()

def test_imputer_fails_closed_on_provenance_and_clone_age(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    frame = _frame(
        [1, 1],
        ages=[4, 4],
        channels=["asec", "puf_tax_detail"],
    )
    person = frame.table("person").drop(columns=["person_source_id"])
    missing = _replace_person(frame, person)
    with pytest.raises(ValueError, match="person_source_id"):
        impute_us_sipp_head_start(missing, _donor(), seed=0)

    person = frame.table("person").copy()
    person.loc[1, "person_support_channel"] = "mystery"
    unknown = _replace_person(frame, person)
    with pytest.raises(ValueError, match="unsupported support channel"):
        impute_us_sipp_head_start(unknown, _donor(), seed=0)

    person = frame.table("person").copy()
    person.loc[1, "age"] = 5
    inconsistent = _replace_person(frame, person)
    with pytest.raises(ValueError, match="disagree on age"):
        impute_us_sipp_head_start(inconsistent, _donor(), seed=0)

def test_imputer_rejects_conflicting_duplicate_asec_source_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    duplicate = _frame(
        [7, 7],
        ages=[3, 5],
        channels=["asec", "asec"],
    )

    with pytest.raises(ValueError, match="source clones disagree on age"):
        impute_us_sipp_head_start(duplicate, _donor(), seed=0)

def test_imputer_rejects_identical_duplicate_same_role_source_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    duplicate = _frame(
        [7, 7],
        ages=[3, 3],
        channels=["asec", "asec"],
    )

    with pytest.raises(ValueError, match="duplicated support copies"):
        impute_us_sipp_head_start(duplicate, _donor(), seed=0)

def test_assembled_clone_two_uses_lowest_clone_and_fans_to_every_clone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    frame = _frame(
        [10, 10, 10, 20, 20],
        ages=[4, 4, 4, 5, 5],
        female=[True, False, False, False, True],
        channels=["acs"] * 5,
    )
    person = frame.table("person").copy()
    person["person_spine_source_id"] = [100, 100, 100, 200, 200]
    person["person_support_clone_index"] = [0, 1, 2, 1, 2]
    assembled = _replace_person(frame, person)

    predicted = impute_us_sipp_head_start(assembled, _donor(), seed=7)
    by_source = pd.DataFrame(
        {
            "source": person["person_source_id"],
            "value": predicted,
        }
    ).groupby("source")["value"]
    assert (by_source.nunique() == 1).all()
    assert by_source.first().to_dict() == {10: True, 20: False}

    materialized = person.copy()
    materialized[_OUTPUT] = predicted.to_numpy()
    summary = us_sipp_head_start_summary(_replace_person(frame, materialized))
    assert summary["clone_group_count"] == 2
    assert summary["clone_mismatch_count"] == 0

    materialized.loc[materialized["person_support_clone_index"].eq(2), _OUTPUT] ^= True
    mismatch = us_sipp_head_start_summary(_replace_person(frame, materialized))
    assert mismatch["clone_mismatch_count"] == 2

def test_historical_tail_copy_fans_the_source_decision_to_every_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    frame = _historical_tail_frame()
    person = frame.table("person")
    assert "person_spine_source_id" not in person
    assert person["person_support_clone_index"].tolist() == [0, 0, 0, 1, 1, 1, 2]
    assert person["person_support_channel"].tolist() == [
        "asec",
        "asec",
        "asec",
        "puf_tax_detail",
        "puf_tax_detail",
        "puf_tax_detail",
        "puf_tax_detail",
    ]

    # Give the tail copy a predictor that would flip the fake QRF's decision:
    # the native copy must still be the canonical predictor row.
    divergent = person.copy()
    divergent.loc[divergent["person_support_clone_index"].eq(2), "is_female"] = False
    predicted = impute_us_sipp_head_start(
        _replace_person(frame, divergent), _donor(), seed=3
    )
    receiver = _FakeQRF.instances[-1].receiver
    assert receiver is not None
    assert len(receiver) == 2  # one canonical row per eligible source person
    by_source = pd.DataFrame(
        {"source": person["person_source_id"], "value": predicted}
    ).groupby("source")["value"]
    assert (by_source.nunique() == 1).all()
    assert by_source.first().to_dict() == {10: True, 20: False, 30: False}
    tail = person["person_support_clone_index"].eq(2).to_numpy()
    twin = (
        person["person_support_clone_index"].eq(1) & person["person_source_id"].eq(10)
    ).to_numpy()
    assert predicted[tail].tolist() == predicted[twin].tolist() == [True]

    materialized = person.copy()
    materialized[_OUTPUT] = predicted.to_numpy()
    summary = us_sipp_head_start_summary(_replace_person(frame, materialized))
    assert summary["clone_group_count"] == 3
    assert summary["clone_mismatch_count"] == 0
    materialized.loc[tail, _OUTPUT] = False
    mismatch = us_sipp_head_start_summary(_replace_person(frame, materialized))
    assert mismatch["clone_mismatch_count"] == 1

def test_historical_puf_only_survivor_predicts_from_the_primary_detail_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    frame = _historical_tail_frame()
    person = frame.table("person").copy()
    # Selection kept only source 10's PUF-role copies, tail copy first.
    survivor = ~(
        person["person_source_id"].eq(10) & person["person_support_clone_index"].eq(0)
    )
    person = person.loc[survivor].iloc[::-1].reset_index(drop=True)
    person.loc[person["person_support_clone_index"].eq(2), "is_female"] = False
    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    tables["person"] = person
    kept_households = set(person["person_household_id"])
    tables["household"] = tables["household"].loc[
        tables["household"]["household_id"].isin(kept_households)
    ]
    weights = frame.weights_for("household").values[
        frame.table("household")["household_id"].isin(kept_households).to_numpy()
    ]
    for entity in ("tax_unit", "spm_unit", "family", "marital_unit"):
        membership = f"person_{entity}_id"
        tables[entity] = tables[entity].loc[
            tables[entity][f"{entity}_id"].isin(set(person[membership]))
        ]
    survivor_frame = Frame(
        tables,
        frame.schema,
        {"household": Weights(weights, WeightKind.DESIGN)},
    )

    predicted = impute_us_sipp_head_start(survivor_frame, _donor(), seed=3)
    source_ten = person["person_source_id"].eq(10).to_numpy()
    # Copy rank, not row order or role, picks the primary PUF-detail copy.
    assert predicted[source_ten].tolist() == [True, True]

def test_historical_duplicate_clone_index_still_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    frame = _historical_tail_frame()
    person = frame.table("person").copy()
    person.loc[
        person["person_support_clone_index"].eq(2), "person_support_clone_index"
    ] = 1
    duplicated = _replace_person(frame, person)

    with pytest.raises(ValueError, match=r"duplicated support copies.*\('10', 1\)"):
        impute_us_sipp_head_start(duplicated, _donor(), seed=3)

@pytest.mark.parametrize("clone_index", [3, 7, 2**62])
@pytest.mark.parametrize("dtype", [np.int64, np.float64])
def test_historical_out_of_domain_copy_refused_before_prediction(
    monkeypatch: pytest.MonkeyPatch,
    clone_index: int,
    dtype: type,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    frame = _historical_tail_frame()
    person = frame.table("person").copy()
    column = "person_support_clone_index"
    tail = person[column].eq(2)
    person[column] = person[column].astype(dtype)
    person.loc[tail, column] = clone_index
    with pytest.raises(ValueError, match="historical support clone indices.*0, 1, 2"):
        impute_us_sipp_head_start(_replace_person(frame, person), _donor(), seed=3)
    assert not _FakeQRF.instances

@pytest.mark.parametrize("assembled", [True, False], ids=["assembled", "historical"])
@pytest.mark.parametrize(
    "bad_index",
    [np.inf, -np.inf, np.nan, 1.5, -1.0, float(2**63)],
    ids=[
        "inf",
        "negative_inf",
        "nan",
        "non_integer",
        "negative_float",
        "float_past_int64",
    ],
)
def test_malformed_clone_index_fails_closed_before_canonical_selection(
    monkeypatch: pytest.MonkeyPatch,
    assembled: bool,
    bad_index: float,
) -> None:
    # Microcosm #992 gate finding: an assembled [0, inf] once ranked as
    # INT64_MAX and passed canonical selection; a historical tail copy set to
    # inf was likewise accepted as a distinct PUF-role copy. A float -1.0
    # would rank ahead of the native row and silently replace it.
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    column = "person_support_clone_index"
    if assembled:
        frame = _frame([10, 10], ages=[4, 4], channels=["acs", "acs"])
        person = frame.table("person").copy()
        person["person_spine_source_id"] = [100, 100]
        person[column] = [0.0, bad_index]
    else:
        frame = _historical_tail_frame()
        person = frame.table("person").copy()
        tail = person[column].eq(2)
        person[column] = person[column].astype(np.float64)
        person.loc[tail, column] = bad_index

    with pytest.raises(
        ValueError,
        match=(
            r"clone-role metadata: PUF support metadata column "
            r"'person_support_clone_index' must contain nonnegative integers"
        ),
    ):
        impute_us_sipp_head_start(_replace_person(frame, person), _donor(), seed=3)
    assert not _FakeQRF.instances

def test_assembled_frame_without_clone_indices_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Microcosm #992 gate finding: with the clone-index column dropped, an
    # assembled ASEC-channel frame once fell back to role ranks and passed
    # canonical selection. Assembled channels name physical sources, so they
    # cannot tell a native row from a donor copy; the base raised here.
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    frame = _frame([10, 11], ages=[4, 4], channels=["asec", "asec"])
    person = frame.table("person").copy()
    person["person_spine_source_id"] = [100, 101]
    person = person.drop(columns=["person_support_clone_index"], errors="ignore")

    with pytest.raises(
        ValueError,
        match=(
            r"assembled support metadata requires "
            r"'person_support_clone_index'"
        ),
    ):
        impute_us_sipp_head_start(_replace_person(frame, person), _donor(), seed=3)
    assert not _FakeQRF.instances

@pytest.mark.parametrize(
    ("source_ids", "clone_indices", "missing"),
    [
        pytest.param(
            [10, 20, 30, 40],
            None,
            r"'person_support_channel' and 'person_support_clone_index'",
            id="no_channel_no_clone_unique_ids",
        ),
        pytest.param(
            [10, 10, 20, 20],
            None,
            r"'person_support_channel' and 'person_support_clone_index'",
            id="no_channel_no_clone_repeated_ids",
        ),
        pytest.param(
            [10, 10, 20, 20],
            [0, 1, 0, 1],
            r"'person_support_channel'",
            id="clone_index_without_channel",
        ),
    ],
)
def test_assembled_frame_missing_support_provenance_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    source_ids: list[int],
    clone_indices: list[int] | None,
    missing: str,
) -> None:
    # Microcosm #992 gate finding (b): an assembled person table (raw spine
    # IDs present) stripped of both provenance columns reached the
    # no-metadata early return in _support_group_keys, ranked every row 0 and
    # passed canonical selection; the base raised KeyError here. Unique IDs
    # hid it best: nothing even looked duplicated.
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    frame = _frame(source_ids, ages=[4] * len(source_ids))
    person = frame.table("person").copy()
    person["person_spine_source_id"] = source_ids
    if clone_indices is not None:
        person["person_support_clone_index"] = clone_indices
    stripped = _replace_person(frame, person)

    pattern = (
        r"assembled support metadata requires "
        + missing
        + r" alongside 'person_spine_source_id'"
    )
    with pytest.raises(ValueError, match=pattern):
        module._recipient_predictors(stripped)
    with pytest.raises(ValueError, match=pattern):
        impute_us_sipp_head_start(stripped, _donor(), seed=3)
    assert not _FakeQRF.instances

@pytest.mark.parametrize("entry", ["predictors", "impute", "gate"])
def test_assembled_provenance_checked_before_other_receiver_inputs(
    monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    # Missing predictor/output inputs must not bypass the provenance check.
    # The pre-fix predictors reported missing age, imputation read the donor,
    # and the gate returned only the missing-output failure.
    frame = _frame([10, 20, 30, 40])
    person = frame.table("person").copy()
    person["person_spine_source_id"] = person["person_source_id"]
    person = person.drop(columns=["age"])
    stripped = _replace_person(frame, person)
    message = "assembled support metadata requires"
    if entry == "gate":
        gate = us_sipp_head_start_signal_gate(stripped)
        assert not gate.passed
        assert any(message in failure for failure in gate.failures)
        assert gate.details["support_channel_invalid"] is True
    else:
        monkeypatch.setattr(module, "QRF", _FakeQRF)
        with pytest.raises(ValueError, match=message):
            if entry == "predictors":
                module._recipient_predictors(stripped)
            else:
                impute_us_sipp_head_start(stripped, pd.DataFrame(), seed=3)
        assert not _FakeQRF.instances

@pytest.mark.parametrize(
    "channels",
    [None, ["asec"] * 4, ["asec", "puf_tax_detail"] * 2],
    ids=["no_channel", "all_asec", "role_labels"],
)
def test_gate_flags_assembled_frame_missing_clone_indices(
    channels: list[str] | None,
) -> None:
    # The summary groups copies by source ID and flags the incomplete
    # provenance instead of raising, so the gate reports every failure. It
    # must never read an assembled channel as a historical role.
    frame = _frame(
        [10, 10, 20, 20],
        channels=channels,
        output=[False, True, True, True],
    )
    person = frame.table("person").copy()
    person["person_spine_source_id"] = [10, 10, 20, 20]
    stripped = _replace_person(frame, person)

    summary = us_sipp_head_start_summary(stripped)
    assert summary["support_channel_invalid"] is True
    assert summary["clone_group_count"] == 2
    assert summary["clone_mismatch_count"] == 1
    assert "channel_eligible_weighted_take_up_shares" not in summary
    gate = us_sipp_head_start_signal_gate(stripped)
    assert not gate.passed
    assert f"{_OUTPUT}: support-channel provenance is invalid" in gate.failures

def test_gate_flags_clone_index_past_int64() -> None:
    # float(2**63) is the first float past int64; the base let it wrap to
    # INT64_MAX. The gate now flags it as invalid provenance.
    frame = _historical_tail_frame()
    person = frame.table("person").copy()
    column = "person_support_clone_index"
    tail = person[column].eq(2)
    person[column] = person[column].astype(np.float64)
    person.loc[tail, column] = float(2**63)
    person[_OUTPUT] = [True, False, False, True, False, False, True]

    summary = us_sipp_head_start_summary(_replace_person(frame, person))
    assert summary["support_channel_invalid"] is True
    gate = us_sipp_head_start_signal_gate(_replace_person(frame, person))
    assert f"{_OUTPUT}: support-channel provenance is invalid" in gate.failures

def test_wrapper_heals_stale_output_and_is_exactly_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    monkeypatch.setattr(module, "us_sipp_head_start_stage_spec", lambda: None)
    base = _frame(
        [1, 2, 3, 4],
        ages=[3, 4, 5, 40],
        female=[True, False, True, True],
        output=[True, True, True, True],
    )

    healed = with_us_sipp_head_start_input(
        base,
        seed=5,
        time_period=2024,
        sipp_donor=_donor(),
    )
    twice = with_us_sipp_head_start_input(
        healed,
        seed=5,
        time_period=2024,
        sipp_donor=_donor(),
    )

    assert healed.table("person")[_OUTPUT].tolist() == [True, False, True, False]
    assert twice is healed

def test_summary_and_gate_require_nonconstant_clone_consistent_domain_signal() -> None:
    sources = [source for source in range(20) for _ in range(2)]
    channels = [channel for _ in range(20) for channel in ("asec", "puf_tax_detail")]
    values = [source == 0 for source in range(20) for _ in range(2)]
    healthy = _frame(sources, channels=channels, output=values)

    summary = us_sipp_head_start_summary(healthy)
    gate = us_sipp_head_start_signal_gate(healthy)
    assert summary["eligible_weighted_take_up_share"] == pytest.approx(0.05)
    assert summary["clone_mismatch_count"] == 0
    assert gate.passed, gate.failures

    person = healthy.table("person").copy()
    person.loc[1, _OUTPUT] = False
    mismatch = _replace_person(healthy, person)
    mismatch_gate = us_sipp_head_start_signal_gate(mismatch)
    assert not mismatch_gate.passed
    assert any("clone" in failure for failure in mismatch_gate.failures)

    person = healthy.table("person").copy()
    person.loc[2, "age"] = 40
    person.loc[2, _OUTPUT] = True
    outside = _replace_person(healthy, person)
    outside_gate = us_sipp_head_start_signal_gate(outside)
    assert not outside_gate.passed
    assert any("outside" in failure for failure in outside_gate.failures)

    person = healthy.table("person").copy()
    person[_OUTPUT] = False
    constant = _replace_person(healthy, person)
    constant_gate = us_sipp_head_start_signal_gate(constant)
    assert not constant_gate.passed
    assert any("constant" in failure for failure in constant_gate.failures)

    person = healthy.table("person").drop(columns=["person_source_id"])
    no_provenance = _replace_person(healthy, person)
    provenance_gate = us_sipp_head_start_signal_gate(no_provenance)
    assert not provenance_gate.passed
    assert any("provenance" in failure for failure in provenance_gate.failures)

    person = healthy.table("person").copy()
    person.loc[0, "person_support_channel"] = "mystery"
    bad_channel = _replace_person(healthy, person)
    channel_gate = us_sipp_head_start_signal_gate(bad_channel)
    assert not channel_gate.passed
    assert any("support-channel" in failure for failure in channel_gate.failures)

# K = 1 golden digests of the canonical predictors, the output and the
# summary (``_head_start_receipt_digest``). Computed by running the original
# code (commit 4324432e5, before location-clone copy keys) on these fixtures;
# location-clone support must not move them. The real-QRF digests also pin the
# QRF draw order, so they move legitimately if microcosm.fit.qrf or its locked
# RNG libraries change.
_K1_GOLDEN_DIGESTS = {
    ("tail", "fake"): (
        "031e67291ac74d8bca75be332964a6a36618a4321e299f06c7471a2b4d459566"
    ),
    ("tail", "real"): (
        "2dd77a71f11e7056ec036edcdd48c8e9d88075a03e56324ed1ffc51e51b933a2"
    ),
    ("population", "fake"): (
        "cb78635b5798ad1c88222fb3bd18c9ee7700d2eaadf02956fc28b78bf24ad5e2"
    ),
    ("population", "real"): (
        "045e5e93f7c440e0e9d30bd0c5535be8e096067bbb00387615f5ccc117724040"
    ),
}
_K1_GOLDEN_FRAMES = {
    "tail": _historical_tail_frame,
    "population": _golden_population_frame,
}


@pytest.mark.parametrize("explicit_zero_column", [False, True], ids=["absent", "zero"])
@pytest.mark.parametrize("qrf", ["fake", "real"])
@pytest.mark.parametrize("fixture", ["tail", "population"])
def test_k1_output_matches_the_pre_location_golden_digest(
    monkeypatch: pytest.MonkeyPatch,
    fixture: str,
    qrf: str,
    explicit_zero_column: bool,
) -> None:
    # K = 1 is byte-identical to the code before location clones existed, and
    # an explicit all-zero location column reads exactly like an absent one.
    frame = _K1_GOLDEN_FRAMES[fixture]()
    assert _located(frame, 1) is frame
    assert _LOCATION_COLUMN not in frame.table("person")
    if explicit_zero_column:
        frame = _with_location_column(frame, 0)
    if qrf == "real":
        monkeypatch.setattr(module, "QRF", _real_qrf())
        predicted = impute_us_sipp_head_start(
            frame,
            _real_qrf_donor(),
            seed=_GOLDEN_QRF_SEED,
            n_estimators=_GOLDEN_QRF_TREES,
        )
    else:
        monkeypatch.setattr(module, "QRF", _FakeQRF)
        predicted = impute_us_sipp_head_start(frame, _donor(), seed=3)

    assert predicted.any() and not predicted.all()
    assert _head_start_receipt_digest(frame, predicted) == (
        _K1_GOLDEN_DIGESTS[(fixture, qrf)]
    )


def test_k1_wrapper_adds_no_location_column(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    monkeypatch.setattr(module, "us_sipp_head_start_stage_spec", lambda: None)
    frame = _historical_tail_frame()

    written = with_us_sipp_head_start_input(
        frame, seed=3, time_period=2024, sipp_donor=_donor()
    )

    assert list(written.table("person").columns) == [
        *frame.table("person").columns,
        _OUTPUT,
    ]


@pytest.mark.parametrize("clones", [2, 3])
def test_location_clones_are_distinct_copies_that_inherit_the_source_decision(
    monkeypatch: pytest.MonkeyPatch,
    clones: int,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    monkeypatch.setattr(module, "us_sipp_head_start_stage_spec", lambda: None)
    frame = _historical_tail_frame()
    base = impute_us_sipp_head_start(frame, _donor(), seed=3)
    base_receiver = _FakeQRF.instances[-1].receiver
    located = _located(frame, clones)
    person = located.table("person")
    # Every (source, support copy) row became `clones` adjacent copies that
    # keep the source ID and support clone index; only the location index
    # tells them apart.
    assert person[_LOCATION_COLUMN].tolist() == list(range(clones)) * 7
    assert person["person_support_clone_index"].tolist() == (
        np.repeat([0, 0, 0, 1, 1, 1, 2], clones).tolist()
    )
    assert person["person_source_id"].tolist() == (
        np.repeat([10, 20, 30, 10, 20, 30, 10], clones).tolist()
    )

    predicted = impute_us_sipp_head_start(located, _donor(), seed=3)

    receiver = _FakeQRF.instances[-1].receiver
    assert receiver is not None and base_receiver is not None
    assert len(receiver) == 2  # still one canonical row per eligible source
    pd.testing.assert_frame_equal(receiver, base_receiver)
    np.testing.assert_array_equal(
        predicted.to_numpy(), np.repeat(base.to_numpy(), clones)
    )
    by_source = pd.DataFrame(
        {"source": person["person_source_id"], "value": predicted}
    ).groupby("source")["value"]
    assert (by_source.nunique() == 1).all()
    assert (by_source.size() == np.array([3, 2, 2]) * clones).all()

    written = with_us_sipp_head_start_input(
        located, seed=3, time_period=2024, sipp_donor=_donor()
    )
    np.testing.assert_array_equal(
        written.table("person")[_OUTPUT].to_numpy(), predicted.to_numpy()
    )
    base_written = frame.table("person").copy()
    base_written[_OUTPUT] = base.to_numpy()
    base_summary = us_sipp_head_start_summary(_replace_person(frame, base_written))
    summary = us_sipp_head_start_summary(written)
    # Each copy carries w / K, so every source-level total is conserved.
    assert summary["clone_mismatch_count"] == 0
    assert summary["support_channel_invalid"] is False
    assert summary["eligible_weight"] == pytest.approx(
        base_summary["eligible_weight"], rel=1e-12
    )
    assert summary["eligible_weighted_take_up_share"] == pytest.approx(
        base_summary["eligible_weighted_take_up_share"], rel=1e-12
    )
    assert summary["positive_count"] == clones * base_summary["positive_count"]
    gate = us_sipp_head_start_signal_gate(written)
    assert not any("clone" in failure for failure in gate.failures)
    assert not any("provenance" in failure for failure in gate.failures)


def test_location_clone_zero_is_canonical_even_when_its_id_sorts_last(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # With K = 3, person 3's clones get ids 9, 10 and 11; as strings "10"
    # sorts first. Give clones 1 and 2 a predictor that would flip the fake
    # QRF's decision: location clone 0 must still be the canonical row.
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    located = _located(_frame([10, 20, 30], female=[True, True, True]), 3)
    person = located.table("person").copy()
    assert person["person_id"].tolist()[6:] == [9, 10, 11]
    person.loc[person[_LOCATION_COLUMN].ne(0), "is_female"] = False

    predicted = impute_us_sipp_head_start(
        _replace_person(located, person), _donor(), seed=3
    )

    receiver = _FakeQRF.instances[-1].receiver
    assert receiver is not None
    assert receiver["is_female"].tolist() == [1.0, 1.0, 1.0]
    assert predicted.all()


def test_real_qrf_decisions_commute_with_location_cloning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # impute(clone(F, K)) == repeat(impute(F), K) with the real QRF: location
    # copies inherit the source decision instead of redrawing it, and the
    # canonical rows, their order and so the draw stream are unchanged.
    monkeypatch.setattr(module, "QRF", _real_qrf())
    frame = _golden_population_frame()
    donor = _real_qrf_donor()
    base = impute_us_sipp_head_start(frame, donor, seed=29, n_estimators=6)
    assert base.any() and not base.all()
    assert _located(frame, 1) is frame

    for clones in (2, 3):
        predicted = impute_us_sipp_head_start(
            _located(frame, clones), donor, seed=29, n_estimators=6
        )
        np.testing.assert_array_equal(
            predicted.to_numpy(), np.repeat(base.to_numpy(), clones)
        )


@pytest.mark.parametrize("clones", [2, 3])
def test_location_clone_collision_still_fails_closed_naming_the_triple(
    monkeypatch: pytest.MonkeyPatch,
    clones: int,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    located = _located(_historical_tail_frame(), clones)
    person = located.table("person").copy()
    # Relabel source 10's tail-copy location clones all as location clone 0.
    person.loc[person["person_support_clone_index"].eq(2), _LOCATION_COLUMN] = 0
    collided = _replace_person(located, person)

    with pytest.raises(
        ValueError,
        match=(
            r"duplicated support copies; invalid \(source, copy rank, location "
            r"clone\) triple\(s\): \[\('10', 2, 0\)\]\."
        ),
    ):
        impute_us_sipp_head_start(collided, _donor(), seed=3)
    assert not _FakeQRF.instances


def test_duplicated_support_copy_of_a_location_clone_still_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The historical duplicate (tail copy relabelled rank 1) stays refused
    # once located: every location clone repeats the duplicated pair.
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    located = _located(_historical_tail_frame(), 2)
    person = located.table("person").copy()
    column = "person_support_clone_index"
    person.loc[person[column].eq(2), column] = 1

    with pytest.raises(
        ValueError,
        match=(
            r"duplicated support copies; invalid \(source, copy rank, location "
            r"clone\) triple\(s\): \[\('10', 1, 0\), \('10', 1, 1\)\]\."
        ),
    ):
        impute_us_sipp_head_start(_replace_person(located, person), _donor(), seed=3)
    assert not _FakeQRF.instances


@pytest.mark.parametrize(
    "bad_index",
    [-1, -1.0, np.nan, 1.5, np.inf, float(2**63), "north"],
    ids=[
        "negative_int",
        "negative_float",
        "partial_nan",
        "non_integer",
        "inf",
        "float_past_int64",
        "text",
    ],
)
def test_malformed_location_clone_index_fails_closed_before_prediction(
    monkeypatch: pytest.MonkeyPatch,
    bad_index: object,
) -> None:
    monkeypatch.setattr(module, "QRF", _FakeQRF)
    located = _located(_historical_tail_frame(), 2)
    person = located.table("person").copy()
    person[_LOCATION_COLUMN] = person[_LOCATION_COLUMN].astype(object)
    person.loc[person.index[-1], _LOCATION_COLUMN] = bad_index

    with pytest.raises(
        ValueError,
        match=(
            r"malformed location clone metadata: location clone metadata column "
            r"'person_location_clone_index' must contain nonnegative integers"
        ),
    ):
        impute_us_sipp_head_start(_replace_person(located, person), _donor(), seed=3)
    assert not _FakeQRF.instances
