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

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "us_imputation_lineage.yaml"
INVENTORY = ROOT / "specs" / "us_pool_column_inventory.json"

_BOOLEAN_PREFIXES = ("has_", "is_", "receives_")


def _draw_kind(target: str, family: str) -> str:
    if target.startswith(_BOOLEAN_PREFIXES) or family.endswith("boolean"):
        return "boolean"
    return "amount"


# BEGIN additive column-closure dashboard data (microcosm#697)
# ``imputed_families`` and ``computed_producers`` are two layers of the same
# modeled lineage class: 90 artifact columns intentionally occur in both.  A
# duplicate across any of the exclusive classes below remains a collision.
_EXPLICIT_COLUMN_CLASSES = (
    "measured_native",
    "receipts",
    "structural",
    "assigned_by_ladder",
    "unclassified",
)
_COLUMN_CLASSES = ("modeled", "take_up_draws", *_EXPLICIT_COLUMN_CLASSES)


def _inventory_names(inventory_path: Path) -> list[str]:
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    columns = payload.get("columns")
    if not isinstance(columns, list) or not all(
        isinstance(column, str) for column in columns
    ):
        raise ValueError(f"{inventory_path}: columns must be a list of strings")
    if columns != sorted(set(columns)):
        raise ValueError(f"{inventory_path}: columns must be sorted and unique")
    return columns


def _column_key(*, entity: object, column: object, context: str) -> str:
    if not isinstance(entity, str) or not entity or "/" in entity:
        raise ValueError(f"{context}: entity must be a non-empty name without '/'")
    if not isinstance(column, str) or not column or "/" in column:
        raise ValueError(f"{context}: column must be a non-empty name without '/'")
    return f"{entity}/{column}"


def _add_group_claims(
    claims: dict[str, set[str]],
    *,
    class_name: str,
    groups: object,
    context: str,
    raw_modeled: set[str],
    group_label: str = "groups",
) -> None:
    if not isinstance(groups, list):
        raise ValueError(f"{context}.{group_label} must be a list")
    for group_index, group in enumerate(groups):
        group_context = f"{context}.{group_label}[{group_index}]"
        if not isinstance(group, dict):
            raise ValueError(f"{group_context}: entry must be an object")
        columns = group.get("columns")
        if not isinstance(columns, list) or not columns:
            raise ValueError(f"{group_context}: columns must be a non-empty list")
        group_claims = {
            _column_key(
                entity=group.get("entity"),
                column=column,
                context=group_context,
            )
            for column in columns
        }
        modeled_overlaps = group_claims & raw_modeled
        has_supersession = "supersedes_modeled" in group
        if bool(modeled_overlaps) != has_supersession:
            raise ValueError(
                f"{group_context}: supersedes_modeled must be present if and only "
                "if the group's columns intersect the raw modeled union; "
                f"overlaps={sorted(modeled_overlaps)}"
            )
        if has_supersession and group["supersedes_modeled"] is not True:
            raise ValueError(f"{group_context}: supersedes_modeled must be true")
        claims["modeled"].difference_update(modeled_overlaps)
        claims[class_name].update(group_claims)


def column_lineage_claims(
    spec: dict,
    inventory_columns: list[str],
) -> dict[str, set[str]]:
    """Resolve the spec to exclusive lineage-class claims over an inventory."""

    inventory = set(inventory_columns)
    by_name: dict[str, list[str]] = {}
    for key in inventory_columns:
        try:
            entity, column = key.split("/", maxsplit=1)
        except ValueError as error:
            raise ValueError(f"invalid inventory key {key!r}; expected entity/column") from error
        by_name.setdefault(column, []).append(entity)

    claims = {class_name: set() for class_name in _COLUMN_CLASSES}
    for family_index, family in enumerate(spec.get("imputed_families", [])):
        context = f"imputed_families[{family_index}]"
        if not isinstance(family, dict):
            raise ValueError(f"{context}: entry must be an object")
        targets = family.get("targets")
        if not isinstance(targets, list) or not targets:
            raise ValueError(f"{context}: targets must be a non-empty list")
        for target in targets:
            claims["modeled"].add(
                _column_key(
                    entity=family.get("entity"),
                    column=target,
                    context=context,
                )
            )

    unresolved_outputs: list[str] = []
    for producer_index, producer in enumerate(spec.get("computed_producers", [])):
        context = f"computed_producers[{producer_index}]"
        if not isinstance(producer, dict):
            raise ValueError(f"{context}: entry must be an object")
        outputs = producer.get("outputs")
        if not isinstance(outputs, list):
            raise ValueError(f"{context}: outputs must be a list")
        for output in outputs:
            if not isinstance(output, str) or not output:
                raise ValueError(f"{context}: every output must be a non-empty string")
            if output.startswith("@"):
                continue
            entities = by_name.get(output, [])
            if len(entities) != 1:
                unresolved_outputs.append(f"{context}:{output} -> {sorted(entities)}")
                continue
            claims["modeled"].add(f"{entities[0]}/{output}")
    if unresolved_outputs:
        raise ValueError(
            "computed producer outputs must resolve to exactly one artifact column: "
            f"{sorted(unresolved_outputs)}"
        )
    raw_modeled = set(claims["modeled"])

    take_up_records = spec.get("take_up_draws", [])
    if not isinstance(take_up_records, list):
        raise ValueError("take_up_draws must be a list")
    for record_index, record in enumerate(take_up_records):
        context = f"take_up_draws[{record_index}]"
        if not isinstance(record, dict):
            raise ValueError(f"{context}: entry must be an object")
        key = _column_key(
            entity=record.get("entity"),
            column=record.get("column"),
            context=context,
        )
        overlaps_modeled = key in raw_modeled
        has_supersession = "supersedes_modeled" in record
        if overlaps_modeled != has_supersession:
            raise ValueError(
                f"{context}: supersedes_modeled must be present if and only if "
                "the take-up column occurs in the raw modeled union"
            )
        if has_supersession and record["supersedes_modeled"] is not True:
            raise ValueError(f"{context}: supersedes_modeled must be true")
        if overlaps_modeled:
            claims["modeled"].remove(key)
        claims["take_up_draws"].add(key)

    measured_native = spec.get("measured_native", {})
    if not isinstance(measured_native, dict):
        raise ValueError("measured_native must be an object keyed by channel")
    if measured_native and set(measured_native) != {"asec_raw", "acs_native"}:
        raise ValueError(
            "measured_native must declare exactly the asec_raw and acs_native channels"
        )
    for channel, channel_spec in measured_native.items():
        context = f"measured_native.{channel}"
        if not isinstance(channel_spec, dict):
            raise ValueError(f"{context}: channel must be an object")
        _add_group_claims(
            claims,
            class_name="measured_native",
            groups=channel_spec.get("groups"),
            context=context,
            raw_modeled=raw_modeled,
        )

    for class_name in ("receipts", "structural"):
        section = spec.get(class_name, {})
        if not isinstance(section, dict):
            raise ValueError(f"{class_name} must be an object")
        if section:
            _add_group_claims(
                claims,
                class_name=class_name,
                groups=section.get("groups"),
                context=class_name,
                raw_modeled=raw_modeled,
            )

    geography = spec.get("geography", {})
    if not isinstance(geography, dict):
        raise ValueError("geography must be an object")
    assigned_by_ladder = geography.get("assigned_by_ladder", [])
    if not isinstance(assigned_by_ladder, list):
        raise ValueError("geography.assigned_by_ladder must be a list")
    _add_group_claims(
        claims,
        class_name="assigned_by_ladder",
        groups=assigned_by_ladder,
        context="geography",
        raw_modeled=raw_modeled,
        group_label="assigned_by_ladder",
    )

    unclassified = spec.get("unclassified", [])
    if not isinstance(unclassified, list):
        raise ValueError("unclassified must be a list")
    for record_index, record in enumerate(unclassified):
        context = f"unclassified[{record_index}]"
        if not isinstance(record, dict):
            raise ValueError(f"{context}: entry must be an object")
        if not str(record.get("reason", "")).strip():
            raise ValueError(f"{context}: unclassified claims require a reason")
        claims["unclassified"].add(
            _column_key(
                entity=record.get("entity"),
                column=record.get("column"),
                context=context,
            )
        )

    unknown = {
        class_name: sorted(class_claims - inventory)
        for class_name, class_claims in claims.items()
        if class_claims - inventory
    }
    if unknown:
        raise ValueError(f"lineage spec claims columns absent from inventory: {unknown}")

    return claims


def lineage_coverage(spec: dict, inventory_columns: list[str]) -> dict:
    """Return additive dashboard coverage data for the column-closure spec."""

    claims = column_lineage_claims(spec, inventory_columns)
    owners: dict[str, list[str]] = {column: [] for column in inventory_columns}
    for class_name, class_claims in claims.items():
        for column in class_claims:
            owners[column].append(class_name)
    unclassified = sorted(claims["unclassified"])
    return {
        "claimed": sum(bool(class_names) for class_names in owners.values()),
        "total": len(inventory_columns),
        "per_class": {
            class_name: len(claims[class_name]) for class_name in _COLUMN_CLASSES
        },
        "unclaimed": sum(not class_names for class_names in owners.values()),
        "multiply_claimed": sum(
            len(class_names) > 1 for class_names in owners.values()
        ),
        "debt": {"count": len(unclassified), "columns": unclassified},
    }


# END additive column-closure dashboard data (microcosm#697)


def emit(spec_path: Path = SPEC, inventory_path: Path = INVENTORY) -> dict:
    text = spec_path.read_text(encoding="utf-8")
    spec = yaml.safe_load(text)
    inventory_columns = _inventory_names(inventory_path)
    sets = spec["predictor_sets"]
    variables = []
    for family in spec["imputed_families"]:
        pset = sets[family["predictor_set"]]
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
                    "predictors_required": list(pset.get("required", [])),
                    "predictors_optional": list(pset.get("optional", [])),
                    "donor": family.get("donor")
                    or f"{family.get('donor_channel')} → {family.get('recipient_channel')}",
                }
            )
    return {
        "schema_version": spec["schema_version"],
        "spec_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "provenance": spec["provenance"],
        "models": spec["models"],
        "predictor_sets": sets,
        "variables": variables,
        "computed_producers": spec["computed_producers"],
        "known_gaps": spec.get("known_gaps", []),
        # BEGIN additive column-closure dashboard fields (microcosm#697)
        "measured_native": spec.get("measured_native", {}),
        "take_up_draws": spec.get("take_up_draws", []),
        "receipts": spec.get("receipts", {}),
        "structural": spec.get("structural", {}),
        "geography": spec.get("geography", {}),
        "unclassified": spec.get("unclassified", []),
        # END additive column-closure dashboard fields (microcosm#697)
        "counts": {
            "imputed_variables": len(variables),
            "families": len(spec["imputed_families"]),
            "computed_producers": len(spec["computed_producers"]),
            "boolean": sum(v["draw"] == "boolean" for v in variables),
            "amount": sum(v["draw"] == "amount" for v in variables),
            # Additive: existing count consumers need not change.
            "coverage": lineage_coverage(spec, inventory_columns),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=SPEC)
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    args = parser.parse_args(argv)
    payload = emit(args.spec, args.inventory)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out}: {payload['counts']['imputed_variables']} variables, "
        f"{payload['counts']['families']} families, spec {payload['spec_sha256'][:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
