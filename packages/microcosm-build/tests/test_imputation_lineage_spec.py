"""The imputation lineage spec is the source of truth; the code must conform.

``specs/us_imputation_lineage.yaml`` declares, per target family, which
predictor set and which model draw every imputed variable, plus the model's
attributes. These tests hold the running code to that declaration so a
predictor set, target list, or model default can never change without the
spec (and therefore the dashboard) changing with it.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from microcosm.build.us_runtime.acs_transfer import (
    DEFAULT_ACS_TRANSFER_MAX_TARGETS_PER_FIT,
    AcsPredictorSet,
    assert_acs_predictor_set_has_no_target_leakage,
)
from microcosm.build.us_runtime.stacked_spine import (
    declared_stacked_post_puf_predictor_sets,
    stacked_gap_fill_plan,
)
from microcosm.build.us_runtime.us_late_producer_registry import (
    CANONICAL_US_LATE_PRODUCER_REGISTRY,
    CANONICAL_US_LATE_TRANSFER_GROUPS,
)
from microcosm.fit.qrf import DEFAULT_N_ESTIMATORS, DEFAULT_ZERO_ATOL

SPEC_PATH = Path(__file__).resolve().parents[3] / "specs" / "us_imputation_lineage.yaml"
_PARTICIPATION_BOOLEAN_FAMILY = (
    "gap_fill/asec_survey_to_acs/person/model_required_boolean"
)


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that refuses last-key-wins declaration loss."""

    def construct_mapping(self, node, deep: bool = False):
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"duplicate YAML mapping key {key!r}")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def _load_spec(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)


@pytest.fixture(scope="module")
def spec() -> dict:
    return _load_spec(SPEC_PATH)


def _clean(name: str) -> str:
    return name.replace("__acs_transfer_", "")


def _nonempty_name(value: object, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _resolved_predictor_sets(spec: dict) -> dict[str, dict[str, object]]:
    """Validate and resolve the schema-v2 block composition fail closed."""

    if spec.get("schema_version") != 2:
        raise ValueError("lineage predictor composition requires schema_version 2")
    blocks = spec.get("predictor_blocks")
    sets = spec.get("predictor_sets")
    families = spec.get("imputed_families")
    if not isinstance(blocks, dict) or not blocks:
        raise ValueError("predictor_blocks must be a non-empty mapping")
    if not isinstance(sets, dict) or not sets:
        raise ValueError("predictor_sets must be a non-empty mapping")
    if not isinstance(families, list) or not families:
        raise ValueError("imputed_families must be a non-empty list")

    block_rows: dict[str, tuple[dict[str, str], ...]] = {}
    block_eligibility: dict[str, bool] = {}
    for block_name, block in blocks.items():
        _nonempty_name(block_name, context="predictor block name")
        if not isinstance(block, dict):
            raise ValueError(f"predictor block {block_name!r} must be a mapping")
        allowed_fields = {
            "eligibility_linked",
            "columns",
            "blocked_on_checkpoint_schema",
            "cross_grain_projection",
        }
        unknown_fields = sorted(set(block) - allowed_fields)
        if unknown_fields:
            raise ValueError(
                f"predictor block {block_name!r} has unsupported field(s): "
                f"{unknown_fields}"
            )
        projection = block.get("cross_grain_projection")
        if block_name == "puf_tax_detail":
            _nonempty_name(
                projection,
                context="puf_tax_detail cross_grain_projection",
            )
        elif projection is not None:
            raise ValueError(
                f"predictor block {block_name!r} cannot declare a cross-grain "
                "projection"
            )
        eligibility = block.get("eligibility_linked")
        if not isinstance(eligibility, bool):
            raise ValueError(
                f"predictor block {block_name!r} eligibility_linked must be boolean"
            )
        columns = block.get("columns")
        if not isinstance(columns, list) or not columns:
            raise ValueError(
                f"predictor block {block_name!r} columns must be a non-empty list"
            )
        normalized: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in columns:
            if not isinstance(row, dict) or not set(row) <= {"column", "pending"}:
                raise ValueError(
                    f"predictor block {block_name!r} has an invalid column row"
                )
            column = _nonempty_name(
                row.get("column"), context=f"predictor block {block_name!r} column"
            )
            if column in seen:
                raise ValueError(
                    f"predictor block {block_name!r} repeats column {column!r}"
                )
            seen.add(column)
            pending = row.get("pending")
            if pending is not None and pending != "microcosm#696":
                raise ValueError(
                    f"predictor block {block_name!r} column {column!r} has "
                    f"unsupported pending marker {pending!r}"
                )
            if pending is not None and (
                block_name != "geography" or column not in {"puma", "county_fips"}
            ):
                raise ValueError(
                    "pending microcosm#696 is reserved for geography.puma and "
                    "geography.county_fips"
                )
            normalized.append(
                {"column": column, **({"pending": pending} if pending else {})}
            )

        blocked = block.get("blocked_on_checkpoint_schema", [])
        if not isinstance(blocked, list):
            raise ValueError(
                f"predictor block {block_name!r} blocked entries must be a list"
            )
        blocked_names: set[str] = set()
        for row in blocked:
            if not isinstance(row, dict) or set(row) != {"column", "reason"}:
                raise ValueError(
                    f"predictor block {block_name!r} has an invalid blocked entry"
                )
            column = _nonempty_name(
                row["column"], context=f"predictor block {block_name!r} blocked column"
            )
            reason = _nonempty_name(
                row["reason"], context=f"predictor block {block_name!r} blocked reason"
            )
            if not reason.startswith("blocked-on-checkpoint-schema;"):
                raise ValueError(
                    f"predictor block {block_name!r} blocked reason must name "
                    "blocked-on-checkpoint-schema"
                )
            if column in seen or column in blocked_names:
                raise ValueError(
                    f"predictor block {block_name!r} repeats active/blocked column "
                    f"{column!r}"
                )
            blocked_names.add(column)
        block_rows[block_name] = tuple(normalized)
        block_eligibility[block_name] = eligibility

    if block_rows.get("geography") != (
        {"column": "puma", "pending": "microcosm#696"},
        {"column": "county_fips", "pending": "microcosm#696"},
    ):
        raise ValueError(
            "geography must declare exactly pending puma and county_fips rows"
        )

    family_ids = [
        _nonempty_name(family.get("id"), context="imputed family id")
        for family in families
    ]
    if len(family_ids) != len(set(family_ids)):
        raise ValueError("imputed_families repeats a family id")
    if set(sets) != set(family_ids):
        raise ValueError("predictor_sets must have exact one-to-one family-id coverage")

    resolved: dict[str, dict[str, object]] = {}
    for family in families:
        family_id = family["id"]
        if family.get("predictor_set") != family_id:
            raise ValueError(
                f"imputed family {family_id!r} must name its own predictor set"
            )
        if family.get("model") not in spec.get("models", {}):
            raise ValueError(f"imputed family {family_id!r} names an unknown model")
        declaration = sets[family_id]
        if not isinstance(declaration, dict) or set(declaration) != {
            "required_blocks",
            "optional_blocks",
        }:
            raise ValueError(
                f"predictor set {family_id!r} must declare required_blocks and "
                "optional_blocks only"
            )
        required_blocks = declaration["required_blocks"]
        optional_blocks = declaration["optional_blocks"]
        if not isinstance(required_blocks, list) or not isinstance(
            optional_blocks, list
        ):
            raise ValueError(f"predictor set {family_id!r} block fields must be lists")
        composed_blocks = [*required_blocks, *optional_blocks]
        if any(
            not isinstance(block, str) or block not in block_rows
            for block in composed_blocks
        ):
            raise ValueError(f"predictor set {family_id!r} names an unknown block")
        if len(composed_blocks) != len(set(composed_blocks)):
            raise ValueError(f"predictor set {family_id!r} repeats a block")
        stage = family.get("stage")
        if stage == "early_gap_fill":
            expected_family_id = "gap_fill/{}/{}/{}".format(
                _nonempty_name(
                    family.get("direction"),
                    context=f"imputed family {family_id!r} direction",
                ),
                _nonempty_name(
                    family.get("entity"),
                    context=f"imputed family {family_id!r} entity",
                ),
                _nonempty_name(
                    family.get("family"),
                    context=f"imputed family {family_id!r} family",
                ),
            )
            if "geography" in required_blocks or "geography" not in optional_blocks:
                raise ValueError(
                    f"early predictor set {family_id!r} must declare geography "
                    "exactly as an optional pending block"
                )
        elif stage == "late_transfer":
            expected_family_id = "late_transfer/transfer:{}/{}".format(
                _nonempty_name(
                    family.get("entity"),
                    context=f"imputed family {family_id!r} entity",
                ),
                _nonempty_name(
                    family.get("family"),
                    context=f"imputed family {family_id!r} family",
                ),
            )
            if "geography" in composed_blocks:
                raise ValueError(
                    f"late predictor set {family_id!r} cannot declare the pending "
                    "ACS geography block"
                )
        else:
            raise ValueError(
                f"imputed family {family_id!r} has unsupported stage {stage!r}"
            )
        if family_id != expected_family_id:
            raise ValueError(
                f"imputed family metadata resolves to {expected_family_id!r}, "
                f"not its declared id {family_id!r}"
            )

        required: list[str] = []
        optional: list[str] = []
        pending: list[dict[str, str]] = []
        seen_columns: set[str] = set()
        for requirement, names, active in (
            ("required", required_blocks, required),
            ("optional", optional_blocks, optional),
        ):
            for block_name in names:
                for row in block_rows[block_name]:
                    column = row["column"]
                    if column in seen_columns:
                        raise ValueError(
                            f"predictor set {family_id!r} repeats column {column!r}"
                        )
                    seen_columns.add(column)
                    if "pending" in row:
                        pending.append(
                            {
                                "column": column,
                                "block": block_name,
                                "requirement": requirement,
                                "pending": row["pending"],
                            }
                        )
                    else:
                        active.append(column)
        if not required and not optional:
            raise ValueError(
                f"predictor set {family_id!r} has no active predictor columns"
            )
        targets = family.get("targets")
        if not isinstance(targets, list) or not targets:
            raise ValueError(f"imputed family {family_id!r} has no targets")
        overlap = sorted(set(targets).intersection(seen_columns))
        if overlap:
            raise ValueError(
                f"predictor set {family_id!r} includes its own target(s): {overlap}"
            )
        assert_acs_predictor_set_has_no_target_leakage(
            AcsPredictorSet(required=tuple(required), optional=tuple(optional)),
            targets,
            context=f"predictor set {family_id!r}",
        )
        if family_id == _PARTICIPATION_BOOLEAN_FAMILY and not any(
            block_eligibility[block] for block in composed_blocks
        ):
            raise ValueError(
                "participation-boolean predictor set lacks an eligibility-linked block"
            )
        resolved[family_id] = {
            "required_blocks": tuple(required_blocks),
            "optional_blocks": tuple(optional_blocks),
            "required": tuple(required),
            "optional": tuple(optional),
            "pending": tuple(pending),
        }
    return resolved


def test_spec_declares_every_stage_family_and_target(spec: dict) -> None:
    declared = {f["id"]: f for f in spec["imputed_families"]}

    live: dict[str, list[str]] = {}
    for direction in stacked_gap_fill_plan():
        for entity, families in dict(direction.target_families).items():
            for family, targets in families.items():
                live[f"gap_fill/{direction.name}/{entity}/{family}"] = list(targets)
    for group in CANONICAL_US_LATE_TRANSFER_GROUPS:
        live[f"late_transfer/{group.name}"] = list(group.targets)

    assert set(declared) == set(live), (
        "spec families != live families; regenerate or amend the spec: "
        f"missing={sorted(set(live) - set(declared))} "
        f"stale={sorted(set(declared) - set(live))}"
    )
    for family_id, targets in live.items():
        assert declared[family_id]["targets"] == targets, family_id


def test_predictor_set_schema_is_fail_closed(spec: dict) -> None:
    resolved = _resolved_predictor_sets(spec)

    assert len(resolved) == len(spec["imputed_families"]) == 32
    participation = resolved[_PARTICIPATION_BOOLEAN_FAMILY]
    assert "disability" not in participation["optional_blocks"]
    assert {
        "veteran_va",
        "education_work",
        "own_coverage",
    } <= set(participation["optional_blocks"])
    assert participation["pending"] == (
        {
            "column": "puma",
            "block": "geography",
            "requirement": "optional",
            "pending": "microcosm#696",
        },
        {
            "column": "county_fips",
            "block": "geography",
            "requirement": "optional",
            "pending": "microcosm#696",
        },
    )
    puf = resolved["gap_fill/asec_survey_to_acs/person/puf_tax_itemization"]
    assert "earned_income_components" in puf["optional_blocks"]
    assert {
        "social_security_income",
        "retirement_income",
        "investment_income",
    }.isdisjoint(puf["optional_blocks"])
    numeric = resolved["gap_fill/asec_survey_to_acs/person/model_required_numeric"]
    assert "retirement_income" not in numeric["optional_blocks"]


def test_lineage_yaml_loader_refuses_duplicate_mapping_keys(tmp_path: Path) -> None:
    malformed = tmp_path / "lineage.yaml"
    malformed.write_text(
        "schema_version: 2\nschema_version: 2\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate YAML mapping key"):
        _load_spec(malformed)


def test_predictor_set_schema_refuses_invalid_family_declarations(spec: dict) -> None:
    missing = deepcopy(spec)
    del missing["predictor_sets"][_PARTICIPATION_BOOLEAN_FAMILY]
    with pytest.raises(ValueError, match="one-to-one family-id coverage"):
        _resolved_predictor_sets(missing)

    empty = deepcopy(spec)
    empty["predictor_sets"][_PARTICIPATION_BOOLEAN_FAMILY] = {
        "required_blocks": [],
        "optional_blocks": ["geography"],
    }
    with pytest.raises(ValueError, match="no active predictor columns"):
        _resolved_predictor_sets(empty)

    ineligible = deepcopy(spec)
    ineligible["predictor_sets"][_PARTICIPATION_BOOLEAN_FAMILY] = {
        "required_blocks": ["core_demographics"],
        "optional_blocks": [
            "earned_income_components",
            "social_security_income",
            "retirement_income",
            "investment_income",
            "household_structure",
            "housing_context",
            "nativity_english",
            "geography",
        ],
    }
    with pytest.raises(ValueError, match="lacks an eligibility-linked block"):
        _resolved_predictor_sets(ineligible)


@pytest.mark.parametrize(
    ("family_id", "leaking_block"),
    (
        (
            "gap_fill/asec_survey_to_acs/person/puf_tax_itemization",
            "social_security_income",
        ),
        (
            "gap_fill/asec_survey_to_acs/person/model_required_numeric",
            "retirement_income",
        ),
    ),
)
def test_predictor_set_schema_refuses_target_bearing_income_aggregates(
    spec: dict,
    family_id: str,
    leaking_block: str,
) -> None:
    leaked = deepcopy(spec)
    leaked["predictor_sets"][family_id]["optional_blocks"].append(leaking_block)

    with pytest.raises(ValueError, match="target-bearing predictor source"):
        _resolved_predictor_sets(leaked)


def test_predictor_set_schema_refuses_unknown_duplicate_and_target_columns(
    spec: dict,
) -> None:
    unknown = deepcopy(spec)
    unknown["predictor_sets"][_PARTICIPATION_BOOLEAN_FAMILY]["optional_blocks"].append(
        "not_a_block"
    )
    with pytest.raises(ValueError, match="names an unknown block"):
        _resolved_predictor_sets(unknown)

    duplicate = deepcopy(spec)
    duplicate["predictor_sets"][_PARTICIPATION_BOOLEAN_FAMILY][
        "optional_blocks"
    ].append("core_demographics")
    with pytest.raises(ValueError, match="repeats a block"):
        _resolved_predictor_sets(duplicate)

    self_target = deepcopy(spec)
    self_target["predictor_blocks"]["self_target"] = {
        "eligibility_linked": False,
        "columns": [{"column": "has_esi"}],
    }
    self_target["predictor_sets"][_PARTICIPATION_BOOLEAN_FAMILY][
        "optional_blocks"
    ].append("self_target")
    with pytest.raises(ValueError, match="includes its own target"):
        _resolved_predictor_sets(self_target)

    unknown_block_field = deepcopy(spec)
    unknown_block_field["predictor_blocks"]["core_demographics"][
        "eligiblity_linked"
    ] = False
    with pytest.raises(ValueError, match="unsupported field"):
        _resolved_predictor_sets(unknown_block_field)

    pending_bypass = deepcopy(spec)
    pending_bypass["predictor_blocks"]["core_demographics"]["columns"].append(
        {"column": "unmapped_future_column", "pending": "microcosm#696"}
    )
    with pytest.raises(ValueError, match="reserved for geography"):
        _resolved_predictor_sets(pending_bypass)

    late_geography = deepcopy(spec)
    late_family = "late_transfer/transfer:person/adult_care"
    late_geography["predictor_sets"][late_family]["optional_blocks"].append("geography")
    with pytest.raises(ValueError, match="late predictor set.*cannot declare"):
        _resolved_predictor_sets(late_geography)

    required_geography = deepcopy(spec)
    early_set = required_geography["predictor_sets"][_PARTICIPATION_BOOLEAN_FAMILY]
    early_set["optional_blocks"].remove("geography")
    early_set["required_blocks"].append("geography")
    with pytest.raises(ValueError, match="exactly as an optional pending block"):
        _resolved_predictor_sets(required_geography)

    mismatched_metadata = deepcopy(spec)
    participation = next(
        family
        for family in mismatched_metadata["imputed_families"]
        if family["id"] == _PARTICIPATION_BOOLEAN_FAMILY
    )
    participation["entity"] = "household"
    with pytest.raises(ValueError, match="metadata resolves to"):
        _resolved_predictor_sets(mismatched_metadata)


def test_predictor_sets_match_the_code(spec: dict) -> None:
    resolved = _resolved_predictor_sets(spec)
    early_ids = {
        family["id"]
        for family in spec["imputed_families"]
        if family["stage"] == "early_gap_fill"
    }
    observed_early: set[str] = set()
    for direction in stacked_gap_fill_plan():
        assert set(direction.predictor_sets) == set(direction.target_families)
        for entity, target_families in direction.target_families.items():
            live_sets = direction.predictor_sets[entity]
            assert set(live_sets) == set(target_families)
            for family, live in live_sets.items():
                family_id = f"gap_fill/{direction.name}/{entity}/{family}"
                observed_early.add(family_id)
                assert list(resolved[family_id]["required"]) == [
                    _clean(column) for column in live.required
                ], family_id
                assert list(resolved[family_id]["optional"]) == [
                    _clean(column) for column in live.optional
                ], family_id
    assert observed_early == early_ids

    observed_late: set[str] = set()
    for group in CANONICAL_US_LATE_TRANSFER_GROUPS:
        live_sets = declared_stacked_post_puf_predictor_sets(group.target_families)
        live = live_sets[group.entity][group.family]
        family_id = f"late_transfer/{group.name}"
        observed_late.add(family_id)
        assert resolved[family_id]["required"] == live.required, family_id
        assert resolved[family_id]["optional"] == live.optional, family_id
    assert observed_late == set(resolved) - early_ids


def test_model_attributes_match_the_code(spec: dict) -> None:
    model = spec["models"]["regime_gated_qrf"]
    assert model["n_estimators"] == DEFAULT_N_ESTIMATORS
    assert model["zero_atol"] == DEFAULT_ZERO_ATOL
    assert model["implementation"] == "microcosm.fit.qrf.RegimeGatedQRF"
    assert model["post_draw_calibration"] is None
    for family in spec["imputed_families"]:
        if family["stage"] == "early_gap_fill":
            assert (
                family["max_targets_per_fit"]
                == DEFAULT_ACS_TRANSFER_MAX_TARGETS_PER_FIT
            ), family["id"]


def test_computed_producers_match_the_registry(spec: dict) -> None:
    declared = {p["producer"]: p for p in spec["computed_producers"]}
    live = {
        name: producer
        for name, producer in CANONICAL_US_LATE_PRODUCER_REGISTRY.items()
        if str(producer.kind) != "late_transfer"
    }
    assert set(declared) == set(live)
    for name, producer in live.items():
        assert declared[name]["outputs"] == [
            getattr(o, "column", None) or getattr(o, "name", None) or str(o)
            for o in producer.outputs
        ], name


def test_every_target_appears_exactly_once(spec: dict) -> None:
    seen: dict[str, str] = {}
    for family in spec["imputed_families"]:
        for target in family["targets"]:
            key = f"{family['entity']}/{target}"
            assert key not in seen, (
                f"{key} declared by both {seen[key]} and {family['id']}"
            )
            seen[key] = family["id"]
    assert len(seen) == 118
