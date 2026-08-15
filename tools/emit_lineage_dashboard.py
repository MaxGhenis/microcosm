"""Emit the dashboard's lineage JSON from the imputation lineage spec.

The spec (``specs/us_imputation_lineage.yaml``) is the source of truth; this
tool flattens it to one row per imputed variable — its stage, family,
predictor set (resolved to columns), model, and donor path — plus the model
attributes and computed producers, for ``microcosm.institute`` to render.
Nothing on the dashboard page is hand-typed.

    uv run python tools/emit_lineage_dashboard.py --out /path/to/lineage.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

from microcosm.build.us_runtime.acs_transfer import (
    AcsPredictorSet,
    assert_acs_predictor_set_has_no_target_leakage,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "us_imputation_lineage.yaml"

_BOOLEAN_PREFIXES = ("has_", "is_", "receives_")
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


def _draw_kind(target: str, family: str) -> str:
    if target.startswith(_BOOLEAN_PREFIXES) or family.endswith("boolean"):
        return "boolean"
    return "amount"


def _nonempty_name(value: object, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _resolve_predictor_sets(spec: dict) -> dict[str, dict[str, object]]:
    """Resolve composed predictors while refusing malformed declarations."""

    if spec.get("schema_version") != 2:
        raise ValueError("lineage dashboard requires schema_version 2")
    blocks = spec.get("predictor_blocks")
    sets = spec.get("predictor_sets")
    families = spec.get("imputed_families")
    if not isinstance(blocks, dict) or not blocks:
        raise ValueError("predictor_blocks must be a non-empty mapping")
    if not isinstance(sets, dict) or not sets:
        raise ValueError("predictor_sets must be a non-empty mapping")
    if not isinstance(families, list) or not families:
        raise ValueError("imputed_families must be a non-empty list")

    normalized_blocks: dict[str, dict[str, object]] = {}
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
        normalized_columns: list[dict[str, str]] = []
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
            normalized_columns.append(
                {"column": column, **({"pending": pending} if pending else {})}
            )

        blocked = block.get("blocked_on_checkpoint_schema", [])
        if not isinstance(blocked, list):
            raise ValueError(
                f"predictor block {block_name!r} blocked entries must be a list"
            )
        normalized_blocked: list[dict[str, str]] = []
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
            if column in seen:
                raise ValueError(
                    f"predictor block {block_name!r} repeats active/blocked column "
                    f"{column!r}"
                )
            seen.add(column)
            normalized_blocked.append({"column": column, "reason": reason})
        normalized_blocks[block_name] = {
            "eligibility_linked": eligibility,
            "columns": tuple(normalized_columns),
            "blocked": tuple(normalized_blocked),
        }

    if normalized_blocks.get("geography", {}).get("columns") != (
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
            not isinstance(block, str) or block not in normalized_blocks
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
        blocked: list[dict[str, str]] = []
        seen_columns: set[str] = set()
        for requirement, names, active in (
            ("required", required_blocks, required),
            ("optional", optional_blocks, optional),
        ):
            for block_name in names:
                block = normalized_blocks[block_name]
                for row in block["columns"]:
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
                blocked.extend(
                    {
                        **row,
                        "block": block_name,
                        "requirement": requirement,
                    }
                    for row in block["blocked"]
                )
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
            normalized_blocks[block]["eligibility_linked"] for block in composed_blocks
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
            "blocked": tuple(blocked),
        }
    return resolved


def emit(spec_path: Path = SPEC) -> dict:
    text = spec_path.read_text(encoding="utf-8")
    spec = yaml.load(text, Loader=_UniqueKeyLoader)
    resolved_sets = _resolve_predictor_sets(spec)
    variables = []
    for family in spec["imputed_families"]:
        pset = resolved_sets[family["predictor_set"]]
        for target in family["targets"]:
            variables.append(
                {
                    "variable": target,
                    "entity": family["entity"],
                    "family": family["family"],
                    "family_id": family["id"],
                    "stage": family["stage"],
                    "draw": _draw_kind(target, family["family"]),
                    "model": family["model"],
                    "predictor_set": family["predictor_set"],
                    "predictor_blocks_required": list(pset["required_blocks"]),
                    "predictor_blocks_optional": list(pset["optional_blocks"]),
                    "predictors_required": list(pset["required"]),
                    "predictors_optional": list(pset["optional"]),
                    "predictors_pending": list(pset["pending"]),
                    "predictors_blocked_on_checkpoint_schema": list(pset["blocked"]),
                    "donor": family.get("donor")
                    or f"{family.get('donor_channel')} → {family.get('recipient_channel')}",
                }
            )
    return {
        "schema_version": spec["schema_version"],
        "spec_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "provenance": spec["provenance"],
        "models": spec["models"],
        "predictor_blocks": spec["predictor_blocks"],
        "predictor_sets": spec["predictor_sets"],
        "variables": variables,
        "computed_producers": spec["computed_producers"],
        "known_gaps": spec.get("known_gaps", []),
        "counts": {
            "imputed_variables": len(variables),
            "families": len(spec["imputed_families"]),
            "computed_producers": len(spec["computed_producers"]),
            "boolean": sum(v["draw"] == "boolean" for v in variables),
            "amount": sum(v["draw"] == "amount" for v in variables),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=SPEC)
    args = parser.parse_args(argv)
    payload = emit(args.spec)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out}: {payload['counts']['imputed_variables']} variables, "
        f"{payload['counts']['families']} families, spec {payload['spec_sha256'][:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
