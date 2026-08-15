"""US block-anchored geography-ladder tests."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from microcosm.build.us_runtime import (
    US_BLOCK_FIRST_GEOGRAPHY_COLUMNS,
    US_BLOCK_FIRST_GEOGRAPHY_RECEIPT_KEY,
    US_GEOGRAPHY_LADDER_COLUMNS,
    US_NYC_COUNTY_FIPS,
    assign_us_block_first_geography,
    assign_us_geography_ladder,
    load_us_block_ladder,
    us_geography_ladder_assignment_summary,
    us_geography_ladder_gate,
    validate_us_block_first_geography,
    with_household_us_block_first_geography,
    with_household_us_geography_ladder,
)
from microcosm.frame import US_SCHEMA, Frame, WeightKind, Weights


def _ladder_metadata(**overrides: object) -> dict:
    layers = {
        "puma": {
            "vintage": "2020_puma",
            "source": "Census 2020 Census Tract to 2020 PUMA relationship",
        },
        "congressional_district": {
            "vintage": "119th_congress",
            "source": "Census 119th Congressional District BEF (cd119.zip)",
        },
        "sldu": {
            "vintage": "2020_baf",
            "source": "Census 2020 Block Assignment Files (SLDU)",
        },
        "sldl": {
            "vintage": "2020_baf",
            "source": "Census 2020 Block Assignment Files (SLDL)",
        },
        "place": {
            "vintage": "2020_census",
            "source": "Census 2020 Block Assignment Files (INCPLACE_CDP)",
        },
        "cbsa": {
            "vintage": "omb_2023_delineations",
            "source": "OMB Bulletin 23-01 delineation file (list1_2023.xlsx)",
        },
    }
    metadata = {
        "schema_version": 2,
        "kind": "us_block_ladder",
        "block_vintage": "2020_tabulation_blocks",
        "sampling_basis": "population",
        "layers": layers,
    }
    metadata.update(overrides)
    return metadata


def _write_ladder(path: Path, **overrides: object) -> Path:
    arrays: dict[str, np.ndarray] = {
        # Two CDs in state 01 (one with a dominant-population block) and the
        # at-large CD in state 02.
        "block_geoid": np.asarray(
            [
                10010001001000,
                10010001001001,
                10030002002000,
                20130001001000,
            ],
            dtype=np.int64,
        ),
        "population": np.asarray([980.0, 20.0, 500.0, 400.0]),
        "puma": np.asarray([100100, 100100, 100200, 200100], dtype=np.int64),
        "congressional_district_geoid": np.asarray(
            [101, 101, 102, 200], dtype=np.int64
        ),
        "sldu": np.asarray(["001", "001", "002", "00A"], dtype="U3"),
        "sldl": np.asarray(["010", "010", "", "001"], dtype="U3"),
        "place_fips": np.asarray([12345, 0, 67890, 0], dtype=np.int32),
        "cbsa_code": np.asarray([10100, 10100, 0, 21820], dtype=np.int32),
        "metadata_json": np.asarray(json.dumps(_ladder_metadata())),
    }
    arrays.update({k: np.asarray(v) for k, v in overrides.items()})
    np.savez_compressed(path, **arrays)
    return path


def _household() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "household_id": [10, 20, 30, 40],
            "state_fips": [1, 1, 1, 2],
            "congressional_district_geoid": [101, 101, 102, 200],
        },
        index=[100, 200, 300, 400],
    )


def test_load_us_block_ladder_round_trips_arrays_and_vintages(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))

    assert len(ladder) == 4
    assert ladder.layer_vintages == {
        "block": "2020_tabulation_blocks",
        "puma": "2020_puma",
        "congressional_district": "119th_congress",
        "sldu": "2020_baf",
        "sldl": "2020_baf",
        "place": "2020_census",
        "cbsa": "omb_2023_delineations",
    }
    assert ladder.population.dtype == np.float64
    assert ladder.place_fips.dtype == np.int32


def test_load_refuses_missing_array_key(tmp_path) -> None:
    path = tmp_path / "ladder.npz"
    _write_ladder(path)
    with np.load(path) as payload:
        arrays = {k: payload[k] for k in payload.files if k != "cbsa_code"}
    np.savez_compressed(path, **arrays)

    with pytest.raises(ValueError, match="missing required key"):
        load_us_block_ladder(path)


def test_load_refuses_schema_v1_without_aligned_puma(tmp_path) -> None:
    path = tmp_path / "ladder.npz"
    _write_ladder(path)
    with np.load(path) as payload:
        arrays = {key: payload[key] for key in payload.files if key != "puma"}
    metadata = _ladder_metadata(schema_version=1)
    arrays["metadata_json"] = np.asarray(json.dumps(metadata))
    np.savez_compressed(path, **arrays)

    with pytest.raises(ValueError, match="missing required key.*puma"):
        load_us_block_ladder(path)


def test_load_refuses_missing_layer_vintage(tmp_path) -> None:
    metadata = _ladder_metadata()
    del metadata["layers"]["cbsa"]
    path = _write_ladder(
        tmp_path / "ladder.npz",
        metadata_json=np.asarray(json.dumps(metadata)),
    )

    with pytest.raises(ValueError, match="vintage_policy: error"):
        load_us_block_ladder(path)


def test_load_refuses_noncanonical_puma_vintage(tmp_path) -> None:
    metadata = _ladder_metadata()
    metadata["layers"]["puma"]["vintage"] = "2010_puma"
    path = _write_ladder(
        tmp_path / "ladder.npz",
        metadata_json=np.asarray(json.dumps(metadata)),
    )

    with pytest.raises(ValueError, match="puma.*canonical '2020_puma'"):
        load_us_block_ladder(path)


def test_load_refuses_census_unassigned_sld_markers(tmp_path) -> None:
    path = _write_ladder(
        tmp_path / "ladder.npz",
        sldu=np.asarray(["001", "ZZZ", "002", "003"], dtype="U3"),
    )

    with pytest.raises(ValueError, match="unassigned marker"):
        load_us_block_ladder(path)


def test_load_refuses_nonpositive_population(tmp_path) -> None:
    path = _write_ladder(
        tmp_path / "ladder.npz",
        population=np.asarray([980.0, 0.0, 500.0, 400.0]),
    )

    with pytest.raises(ValueError, match="positive"):
        load_us_block_ladder(path)


def test_load_refuses_duplicate_blocks(tmp_path) -> None:
    path = _write_ladder(
        tmp_path / "ladder.npz",
        block_geoid=np.asarray(
            [10010001001000, 10010001001000, 10030002002000, 20130001001000],
            dtype=np.int64,
        ),
    )

    with pytest.raises(ValueError, match="unique"):
        load_us_block_ladder(path)


def test_load_refuses_block_cd_state_mismatch(tmp_path) -> None:
    path = _write_ladder(
        tmp_path / "ladder.npz",
        congressional_district_geoid=np.asarray([101, 101, 102, 600], dtype=np.int64),
    )

    with pytest.raises(ValueError, match="state prefix must match"):
        load_us_block_ladder(path)


def test_block_first_closes_cd_draw_escape_from_observed_puma(tmp_path) -> None:
    ladder = load_us_block_ladder(
        _write_ladder(
            tmp_path / "ladder.npz",
            population=np.asarray([1.0, 1.0, 10_000.0, 400.0]),
            congressional_district_geoid=np.asarray(
                [101, 101, 101, 200], dtype=np.int64
            ),
        )
    )
    household = pd.DataFrame(
        {
            "household_id": range(100),
            "state_fips": [1] * 100,
            "puma": [100100] * 100,
            "congressional_district_geoid": [101] * 100,
        }
    )

    legacy = assign_us_geography_ladder(household, ladder, seed=0)
    block_first = assign_us_block_first_geography(household, ladder, seed=0)

    # The old CD-first draw overwhelmingly picks the CD-101 block in PUMA
    # 0100200, proving the historical escape is represented by this fixture.
    assert "010030002002000" in set(legacy["block_geoid"])
    # Block-first is strictly confined to the observed PUMA 0100100.
    assert set(block_first["block_geoid"]).issubset(
        {"010010001001000", "010010001001001"}
    )
    assert set(block_first["puma"]) == {"0100100"}


def test_block_first_derives_all_nine_geographies_from_selected_block(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))
    household = pd.DataFrame(
        {
            "household_id": [1, 2],
            "state_fips": [1, 2],
            "puma": [100200, np.nan],
        },
        index=[11, 22],
    )

    assigned = assign_us_block_first_geography(household, ladder, seed=4)

    assert assigned.index.tolist() == [11, 22]
    assert set(US_BLOCK_FIRST_GEOGRAPHY_COLUMNS).issubset(assigned.columns)
    assert assigned.loc[11, list(US_BLOCK_FIRST_GEOGRAPHY_COLUMNS)].to_dict() == {
        "block_geoid": "010030002002000",
        "tract_geoid": "01003000200",
        "county_fips": "01003",
        "puma": "0100200",
        "congressional_district_geoid": 102,
        "place_fips": "67890",
        "sldu": "002",
        "sldl": "",
        "cbsa_code": "",
    }
    assert assigned.loc[22, list(US_BLOCK_FIRST_GEOGRAPHY_COLUMNS)].to_dict() == {
        "block_geoid": "020130001001000",
        "tract_geoid": "02013000100",
        "county_fips": "02013",
        "puma": "0200100",
        "congressional_district_geoid": 200,
        "place_fips": "",
        "sldu": "00A",
        "sldl": "001",
        "cbsa_code": "21820",
    }


def test_block_first_asec_falls_back_to_state_not_input_puma(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))
    household = pd.DataFrame(
        {"household_id": range(800), "state_fips": [1] * 800}
    )

    assigned = assign_us_block_first_geography(household, ladder, seed=19)

    assert assigned["block_geoid"].str.startswith("01").all()
    assert set(assigned["puma"]).issubset({"0100100", "0100200"})
    assert {"0100100", "0100200"}.issubset(set(assigned["puma"]))


def test_block_first_is_deterministic_and_population_weighted_within_puma(
    tmp_path,
) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))
    household = pd.DataFrame(
        {
            "household_id": range(4_000),
            "state_fips": [1] * 4_000,
            "puma": [100100] * 4_000,
        }
    )

    first = assign_us_block_first_geography(household, ladder, seed=7)
    second = assign_us_block_first_geography(household, ladder, seed=7)

    assert first["block_geoid"].tolist() == second["block_geoid"].tolist()
    dominant_share = (first["block_geoid"] == "010010001001000").mean()
    assert abs(dominant_share - 0.98) < 0.02
    assert (first["puma"] == "0100100").all()


def test_block_first_refuses_missing_puma_and_state_coverage(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))

    with pytest.raises(ValueError, match="no blocks for observed household puma"):
        assign_us_block_first_geography(
            pd.DataFrame(
                {"household_id": [1], "state_fips": [1], "puma": [1099900]}
            ),
            ladder,
        )
    with pytest.raises(ValueError, match="no populated blocks for ASEC state_fips"):
        assign_us_block_first_geography(
            pd.DataFrame({"household_id": [1], "state_fips": [5]}),
            ladder,
        )


def test_block_first_validates_canonical_vintages_before_rng(
    tmp_path, monkeypatch
) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))
    metadata = dict(ladder.metadata)
    metadata["layers"] = dict(metadata["layers"])
    metadata["layers"]["puma"] = dict(metadata["layers"]["puma"])
    metadata["layers"]["puma"]["vintage"] = "2010_puma"
    invalid = type(ladder)(
        block_geoid=ladder.block_geoid,
        population=ladder.population,
        puma=ladder.puma,
        congressional_district_geoid=ladder.congressional_district_geoid,
        sldu=ladder.sldu,
        sldl=ladder.sldl,
        place_fips=ladder.place_fips,
        cbsa_code=ladder.cbsa_code,
        metadata=metadata,
    )
    called = False

    def forbidden_rng(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("RNG must not be created")

    monkeypatch.setattr(np.random, "default_rng", forbidden_rng)
    with pytest.raises(ValueError, match="puma.*canonical '2020_puma'"):
        assign_us_block_first_geography(
            pd.DataFrame(
                {"household_id": [1], "state_fips": [1], "puma": [100100]}
            ),
            invalid,
        )
    assert called is False


def test_block_first_frame_receipt_and_live_validator(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))
    frame = _minimal_us_frame()
    source_household = frame.table("household").copy()
    artifact_sha256 = "a" * 64

    assigned = with_household_us_block_first_geography(
        frame,
        ladder,
        seed=17,
        ladder_artifact_sha256=artifact_sha256,
    )

    receipt = assigned.metadata[US_BLOCK_FIRST_GEOGRAPHY_RECEIPT_KEY]
    assert receipt["seed"] == 17
    assert receipt["ladder_artifact_sha256"] == artifact_sha256
    assert receipt["draw_universes"]["acs"] == "observed_puma"
    assert receipt["draw_universes"]["asec"] == "state"
    assert validate_us_block_first_geography(
        assigned.table("household"),
        ladder,
        receipt,
        expected_seed=17,
        expected_ladder_artifact_sha256=artifact_sha256,
        source_household=source_household,
    ) is receipt
    assert assigned.weights_for("household").values.tolist() == [100.0, 300.0]

    tampered = assigned.table("household").copy()
    tampered.loc[tampered.index[0], "county_fips"] = "01999"
    with pytest.raises(ValueError, match="county_fips.*not the deterministic"):
        validate_us_block_first_geography(tampered, ladder, receipt)


def test_assignment_writes_the_full_ladder_from_the_block_anchor(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))

    assigned = assign_us_geography_ladder(_household(), ladder, seed=0)

    assert assigned.index.tolist() == [100, 200, 300, 400]
    for column in US_GEOGRAPHY_LADDER_COLUMNS:
        assert column in assigned.columns
    # CD 102 and 200 each have exactly one block: every derived value is
    # checkable end to end.
    row = assigned.loc[300]
    assert row["block_geoid"] == "010030002002000"
    assert row["tract_geoid"] == "01003000200"
    assert row["county_fips"] == "01003"
    assert row["place_fips"] == "67890"
    assert row["sldu"] == "002"
    assert row["sldl"] == ""
    assert row["cbsa_code"] == ""
    at_large = assigned.loc[400]
    assert at_large["block_geoid"] == "020130001001000"
    assert at_large["county_fips"] == "02013"
    assert at_large["place_fips"] == ""
    assert at_large["sldu"] == "00A"
    assert at_large["cbsa_code"] == "21820"
    # CD 101 households draw from CD 101 blocks only.
    assert set(assigned.loc[[100, 200], "block_geoid"]).issubset(
        {"010010001001000", "010010001001001"}
    )


def test_assignment_is_deterministic_and_population_weighted(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))
    household = pd.DataFrame(
        {
            "household_id": range(400),
            "state_fips": [1] * 400,
            "congressional_district_geoid": [101] * 400,
        }
    )

    first = assign_us_geography_ladder(household, ladder, seed=7)
    second = assign_us_geography_ladder(household, ladder, seed=7)

    assert first["block_geoid"].tolist() == second["block_geoid"].tolist()
    # The 98%-population block should absorb the overwhelming majority.
    dominant_share = (first["block_geoid"] == "010010001001000").mean()
    assert dominant_share > 0.9


def test_assignment_consumes_normalized_cd_rng_groups_in_sorted_order(tmp_path) -> None:
    ladder = load_us_block_ladder(
        _write_ladder(
            tmp_path / "ladder.npz",
            block_geoid=np.asarray(
                [
                    10010001001000,
                    10010001001001,
                    10030002002000,
                    10030002002001,
                ],
                dtype=np.int64,
            ),
            population=np.ones(4, dtype=np.float64),
            congressional_district_geoid=np.asarray(
                [101, 101, 102, 102], dtype=np.int64
            ),
            puma=np.asarray([100100, 100100, 100200, 100200], dtype=np.int64),
        )
    )
    household = pd.DataFrame(
        {
            "household_id": range(4),
            "state_fips": [1, 1, 1, 1],
            "congressional_district_geoid": ["0102", 101, 102, "0101"],
        }
    )

    assigned = assign_us_geography_ladder(household, ladder, seed=0)

    rng = np.random.default_rng(0)
    expected_index = np.empty(len(household), dtype=np.int64)
    expected_index[[1, 3]] = rng.choice([0, 1], size=2, replace=True, p=[0.5, 0.5])
    expected_index[[0, 2]] = rng.choice([2, 3], size=2, replace=True, p=[0.5, 0.5])
    expected_blocks = [
        f"{value:015d}" for value in ladder.block_geoid[expected_index].tolist()
    ]
    assert assigned["block_geoid"].tolist() == expected_blocks


def test_assignment_requires_congressional_districts(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))
    household = pd.DataFrame({"household_id": [1], "state_fips": [1]})

    with pytest.raises(ValueError, match="assign congressional districts first"):
        assign_us_geography_ladder(household, ladder)


def test_assignment_refuses_cd_missing_from_ladder(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))
    household = pd.DataFrame(
        {
            "household_id": [1],
            "state_fips": [6],
            "congressional_district_geoid": [653],
        }
    )

    with pytest.raises(ValueError, match="share a CD vintage"):
        assign_us_geography_ladder(household, ladder)


def test_assignment_refuses_mismatched_cd_vintage(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))

    with pytest.raises(ValueError, match="does not match the vintage"):
        assign_us_geography_ladder(
            _household(),
            ladder,
            expected_congressional_district_vintage="120th_congress",
        )


def test_with_household_us_geography_ladder_preserves_frame_mass(tmp_path) -> None:
    ladder = load_us_block_ladder(_write_ladder(tmp_path / "ladder.npz"))
    frame = _minimal_us_frame()

    assigned = with_household_us_geography_ladder(
        frame,
        ladder,
        seed=0,
        expected_congressional_district_vintage="119th_congress",
    )

    household = assigned.table("household")
    assert household["county_fips"].tolist() == ["01003", "02013"]
    assert assigned.weights_for("household").values.tolist() == [100.0, 300.0]
    assert assigned.strata.tolist() == frame.strata.tolist()

    summary = us_geography_ladder_assignment_summary(
        household,
        ladder,
        weight_values=assigned.weights_for("household").values,
    )
    assert summary["applied"] is True
    assert summary["assigned_county_fips_values"] == 2
    assert summary["sldl_nonempty_weighted_share"] == 0.75
    assert summary["nyc_weighted_household_share"] == 0.0
    assert summary["layer_vintages"]["congressional_district"] == "119th_congress"


def test_gate_passes_on_a_consistent_ladder() -> None:
    household, weights = _gated_household()

    result = us_geography_ladder_gate(household, weights)

    assert result.passed, result.failures
    assert 0.005 <= result.details["nyc_weighted_household_share"] <= 0.06
    assert result.details["sldu_nonempty_weighted_share"] == 1.0


def test_gate_fails_when_nyc_collapses_to_zero() -> None:
    household, weights = _gated_household()
    household.loc[
        household["county_fips"].isin(US_NYC_COUNTY_FIPS),
        ["county_fips", "block_geoid", "tract_geoid"],
    ] = ["36001", "360010001001000", "36001000100"]

    result = us_geography_ladder_gate(household, weights)

    assert not result.passed
    assert any("in_nyc collapse" in failure for failure in result.failures)


def test_gate_fails_on_prefix_inconsistency() -> None:
    household, weights = _gated_household()
    household.loc[household.index[0], "county_fips"] = "06037"

    result = us_geography_ladder_gate(household, weights)

    assert not result.passed
    assert any("disagree with the block_geoid prefix" in f for f in result.failures)


def test_gate_fails_when_columns_are_missing() -> None:
    household, weights = _gated_household()
    household = household.drop(columns=["cbsa_code"])

    result = us_geography_ladder_gate(household, weights)

    assert not result.passed
    assert any("missing geography column" in f for f in result.failures)


def _gated_household() -> tuple[pd.DataFrame, np.ndarray]:
    """A weighted household table whose shares sit inside the gate bounds.

    Weighted shares: NYC 2.6% of the nation and 42% of New York State;
    place 76.4% (NYC + CA); CBSA 80% (all but rural TX); SLD codes
    everywhere.
    """

    household = pd.DataFrame(
        {
            "household_id": [1, 2, 3, 4],
            "state_fips": [36, 36, 6, 48],
            "congressional_district_geoid": [3612, 3620, 653, 4802],
            "block_geoid": [
                "360610001001000",
                "360010001001000",
                "060370001001000",
                "480010001001000",
            ],
            "tract_geoid": [
                "36061000100",
                "36001000100",
                "06037000100",
                "48001000100",
            ],
            "county_fips": ["36061", "36001", "06037", "48001"],
            "place_fips": ["51000", "", "44000", ""],
            "sldu": ["027", "046", "024", "001"],
            "sldl": ["075", "109", "051", "001"],
            "cbsa_code": ["35620", "10580", "31080", ""],
        }
    )
    weights = np.asarray([2.6, 3.6, 73.8, 20.0])
    return household, weights


def _minimal_us_frame() -> Frame:
    tables = {
        "person": pd.DataFrame(
            {
                "person_id": np.asarray([1, 2], dtype="int64"),
                "person_household_id": np.asarray([1, 2], dtype="int64"),
                "person_tax_unit_id": np.asarray([10, 20], dtype="int64"),
                "person_spm_unit_id": np.asarray([100, 200], dtype="int64"),
                "person_family_id": np.asarray([1000, 2000], dtype="int64"),
                "person_marital_unit_id": np.asarray([10000, 20000], dtype="int64"),
            }
        ),
        "household": pd.DataFrame(
            {
                "household_id": np.asarray([1, 2], dtype="int64"),
                "state_fips": np.asarray([1, 2], dtype="int64"),
                "puma": np.asarray([100200.0, np.nan], dtype="float64"),
                "congressional_district_geoid": np.asarray([102, 200], dtype="int64"),
            }
        ),
        "tax_unit": pd.DataFrame({"tax_unit_id": np.asarray([10, 20])}),
        "spm_unit": pd.DataFrame({"spm_unit_id": np.asarray([100, 200])}),
        "family": pd.DataFrame({"family_id": np.asarray([1000, 2000])}),
        "marital_unit": pd.DataFrame({"marital_unit_id": np.asarray([10000, 20000])}),
    }
    weights = {
        "household": Weights(
            values=np.asarray([100.0, 300.0]),
            kind=WeightKind.DESIGN,
        )
    }
    strata = pd.Series(["asec_2024", "asec_2024"], name="stratum")
    return Frame(tables, US_SCHEMA, weights, strata)
