#!/usr/bin/env python3
"""Phase-P acceptance gate for the per-family predictor-set change.

The command compares a held baseline stacked-f025 artifact with a candidate
stacked-f025 artifact.  It intentionally does not consume library defaults for
the statistical design: the fold, quantiles, forest, and bootstrap are pinned
in :data:`PHASE_P_CONFIG` below and are copied into every verdict receipt.

The OOS comparison refits one quantile forest per modeled target.  Family
target order comes from each artifact's own execution receipt; preceding
targets in the same bounded chain are supplied as observed (teacher-forced)
predictors.  This makes the baseline CHAMPVA-first order and the candidate
disability-first order part of the measured treatment.  Optional predictor
missingness is handled deterministically with a training-fold median plus an
observed-value indicator, while required-predictor null rows remain ineligible.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import yaml
from quantile_forest import RandomForestQuantileRegressor

from microcosm.build.frame_checkpoint import load_frame_checkpoint
from microcosm.build.us_runtime.acs_transfer import (
    AcsPredictorSet,
    _complete_case_target_encodings,
    _complete_target_mask,
    _legacy_predictor_set,
    _transfer_feature_surface,
    declared_acs_transfer_predictor_sets,
)
from microcosm.build.us_runtime.stacked_spine import (
    declared_stacked_post_puf_predictor_sets,
)
from microcosm.frame import Frame

# ---------------------------------------------------------------------------
# Phase-P statistical configuration.  These are gate authority, not tunables.
# ---------------------------------------------------------------------------

PHASE_P_CONFIG: dict[str, object] = {
    "schema_version": 1,
    "fold": {
        "algorithm": "sha256(namespace + NUL + stable_source_id)",
        "seed": 20260816,
        "fold_count": 5,
        "held_out_fold": 0,
        "unit": "entity_source_id",
    },
    "quantiles": [0.10, 0.25, 0.50, 0.75, 0.90],
    "optional_missingness": {
        "value": "unweighted_training_fold_median",
        "indicator": "one_observed_value_indicator_per_optional_predictor",
        "all_missing_training_predictor": "drop_and_report",
        "required_missing": "row_ineligible",
    },
    "forest": {
        "weighted_training": "seeded_n_of_n_probability_weighted_bootstrap",
        "seed": 260816,
        "n_estimators": 32,
        "default_quantiles": 0.5,
        "criterion": "squared_error",
        "max_depth": 16,
        "min_samples_split": 40,
        "min_samples_leaf": 20,
        "max_samples_leaf": 256,
        "min_weight_fraction_leaf": 0.0,
        "max_features": 1.0,
        "max_leaf_nodes": None,
        "min_impurity_decrease": 0.0,
        "bootstrap": True,
        "oob_score": False,
        "n_jobs": 4,
        "verbose": 0,
        "warm_start": False,
        "ccp_alpha": 0.0,
        "max_samples": 0.8,
        "monotonic_cst": None,
        "predict_interpolation": "linear",
        "predict_weighted_quantile": True,
        "predict_weighted_leaves": False,
        "predict_aggregate_leaves_first": True,
        "minimum_training_rows": 100,
        "minimum_holdout_rows": 20,
    },
    "bootstrap": {
        "method": "paired_cluster_nonparametric_percentile",
        "cluster_assignment": "sha256(seed + NUL + stable_source_id)",
        "seed": 8162026,
        "clusters": 256,
        "replicates": 2000,
        "confidence_level": 0.95,
        "percentile_method": "linear",
    },
    "verdict": {
        "ratio_band": [0.8, 1.25],
        "champva_leg": (
            "person/model_required_boolean/"
            "has_champva_health_coverage_at_interview[clone_0]"
        ),
        "champva_minimum_progress_to_band_ceiling": 0.50,
        "champva_progress_anchor": "baseline artifact ratio",
        "money_worsening": (
            "candidate_minus_baseline paired OOS loss CI lower bound > 0"
        ),
        "pass_iff": [
            "a_champva",
            "b_money_oos",
            "c_no_battery_leg_leaves_band",
        ],
    },
}

_CHECKPOINT_ROOT = "_populace_frame_checkpoint"
_CHECKPOINT_METADATA = "metadata_json"
_ASEC_CHANNEL = "asec"
_ACS_CHANNEL = "acs"
_CLONE_ZERO = 0
_PUF_CLONE = 1


@dataclass(frozen=True)
class Artifact:
    """Resolved paths and small receipts for one stacked artifact."""

    root: Path
    gates_path: Path
    checkpoint_path: Path
    gates: dict[str, object]
    checkpoint_metadata: dict[str, object]


@dataclass(frozen=True)
class FamilySpec:
    """One changed family and the exact A/B model declarations."""

    family_id: str
    stage: str
    entity: str
    family: str
    baseline_targets: tuple[str, ...]
    candidate_targets: tuple[str, ...]
    max_targets_per_fit: int
    baseline_predictor_set: AcsPredictorSet
    candidate_predictor_set: AcsPredictorSet

    @property
    def donor_clone_index(self) -> int:
        return _CLONE_ZERO if self.stage == "early_gap_fill" else _PUF_CLONE


@dataclass(frozen=True)
class OOSTargetMeasurement:
    """Internal per-row OOS losses retained until the paired comparison."""

    key: str
    family_id: str
    stage: str
    entity: str
    family: str
    target: str
    target_position: int
    chain_predecessors: tuple[str, ...]
    predictor_set: dict[str, list[str]]
    resolved_predictors: tuple[str, ...]
    unavailable_optional_predictors: tuple[str, ...]
    training_rows: int
    holdout_rows: int
    ids: np.ndarray
    weights: np.ndarray
    truth: np.ndarray
    losses: np.ndarray
    clusters: np.ndarray


@dataclass(frozen=True)
class IncidenceMeasurement:
    """Per-row inputs needed for the paired CHAMPVA ratio bootstrap."""

    origin: str
    ids: np.ndarray
    weights: np.ndarray
    values: np.ndarray
    clusters: np.ndarray


@dataclass(frozen=True)
class ArmMeasurement:
    """All retained measurements for one artifact after its Frame is freed."""

    targets: dict[str, OOSTargetMeasurement]
    champva_by_origin: dict[str, IncidenceMeasurement]


class GateMeasurementError(RuntimeError):
    """A contextualized Phase-P measurement failure that must fail closed."""

    def __init__(
        self,
        *,
        arm: str,
        family_id: str,
        stage: str,
        entity: str,
        family: str,
        cause: Exception,
    ) -> None:
        self.context = {
            "arm": arm,
            "family_id": family_id,
            "stage": stage,
            "entity": entity,
            "family": family,
            "cause_type": type(cause).__name__,
            "cause": str(cause),
        }
        super().__init__(
            f"Phase-P {arm} measurement failed for {family_id}: "
            f"{type(cause).__name__}: {cause}"
        )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_bucket(value: object, *, namespace: str, buckets: int) -> int:
    if buckets <= 0:
        raise ValueError("Stable bucket count must be positive.")
    payload = f"{namespace}\0{value!s}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % buckets


def _seed(namespace: str, *parts: object) -> int:
    payload = "\0".join([namespace, *(str(part) for part in parts)]).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def _read_checkpoint_metadata(path: Path) -> dict[str, object]:
    with h5py.File(path, mode="r") as h5:
        dataset = h5[f"{_CHECKPOINT_ROOT}/{_CHECKPOINT_METADATA}"]
        payload = bytes(dataset[...])
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError(f"Checkpoint metadata in {path} is not an object.")
    return value


def resolve_artifact(path: str | Path) -> Artifact:
    """Resolve one directory containing a stacked pool and its checkpoint."""

    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Stacked artifact directory not found: {root}.")
    gate_paths = sorted(root.glob("*.gates.json"))
    if len(gate_paths) != 1:
        raise ValueError(
            f"Stacked artifact {root} must contain exactly one *.gates.json; "
            f"found {[item.name for item in gate_paths]}."
        )
    gates_path = gate_paths[0]
    stem = gates_path.name.removesuffix(".gates.json")
    checkpoint_paths = sorted(
        (root / f"{stem}.checkpoints" / "stacked").glob("*/simulated.checkpoint.h5")
    )
    if len(checkpoint_paths) != 1:
        raise ValueError(
            f"Stacked artifact {root} must contain exactly one "
            f"{stem}.checkpoints/stacked/<identity>/simulated.checkpoint.h5; "
            f"found {checkpoint_paths}."
        )
    gates = json.loads(gates_path.read_text())
    if not isinstance(gates, dict):
        raise ValueError(f"Gate receipt {gates_path} is not a JSON object.")
    checkpoint_path = checkpoint_paths[0]
    return Artifact(
        root=root,
        gates_path=gates_path,
        checkpoint_path=checkpoint_path,
        gates=gates,
        checkpoint_metadata=_read_checkpoint_metadata(checkpoint_path),
    )


def _external_metadata(artifact: Artifact) -> dict[str, object]:
    value = artifact.checkpoint_metadata.get("external_metadata")
    if not isinstance(value, dict):
        raise ValueError(
            f"Checkpoint {artifact.checkpoint_path} lacks object external_metadata."
        )
    return value


def _nested(mapping: Mapping[str, object], *keys: str) -> object:
    current: object = mapping
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            raise ValueError(f"Artifact receipt lacks {'.'.join(keys)}.")
        current = current[key]
    return current


def _artifact_target_orders(artifact: Artifact) -> dict[str, tuple[str, ...]]:
    external = _external_metadata(artifact)
    impute = _nested(external, "stage_receipts", "impute")
    if not isinstance(impute, Mapping):
        raise ValueError("Artifact impute stage receipt is not an object.")
    families = _nested(impute, "acs_qrf_transfer", "target_families")
    if not isinstance(families, Mapping):
        raise ValueError("Artifact target_families receipt is not an object.")

    result: dict[str, tuple[str, ...]] = {}
    early = families.get("early_gap_fill")
    if not isinstance(early, Mapping):
        raise ValueError("Artifact target_families lacks early_gap_fill.")
    for entity, entity_families in early.items():
        if not isinstance(entity_families, Mapping):
            raise ValueError(f"Early target families for {entity!r} are malformed.")
        for family, targets in entity_families.items():
            if not isinstance(targets, list) or not all(
                isinstance(target, str) for target in targets
            ):
                raise ValueError(
                    f"Early target order for {entity}/{family} is malformed."
                )
            result[f"early_gap_fill/{entity}/{family}"] = tuple(targets)

    late = _nested(impute, "stacked_post_puf_transfer", "groups")
    if not isinstance(late, Mapping):
        raise ValueError("Artifact late-transfer groups receipt is not an object.")
    for group_name, receipt in late.items():
        if not isinstance(receipt, Mapping):
            raise ValueError(f"Late group receipt {group_name!r} is malformed.")
        targets = receipt.get("ordered_targets")
        if not isinstance(targets, list) or not all(
            isinstance(target, str) for target in targets
        ):
            raise ValueError(f"Late target order for {group_name!r} is malformed.")
        result[f"late_transfer/{group_name}"] = tuple(targets)
    return result


def _load_lineage_spec() -> dict[str, object]:
    path = Path(__file__).resolve().parents[1] / "specs" / "us_imputation_lineage.yaml"
    value = yaml.safe_load(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"Lineage spec {path} is not a mapping.")
    return value


def production_family_specs(
    baseline: Artifact,
    candidate: Artifact,
) -> tuple[FamilySpec, ...]:
    """Bind the 32 changed families to both artifacts' executed target order."""

    spec = _load_lineage_spec()
    declared = spec.get("imputed_families")
    if not isinstance(declared, list) or not declared:
        raise ValueError("Lineage spec imputed_families must be a nonempty list.")
    baseline_orders = _artifact_target_orders(baseline)
    candidate_orders = _artifact_target_orders(candidate)

    result: list[FamilySpec] = []
    observed_ids: set[str] = set()
    for raw in declared:
        if not isinstance(raw, Mapping):
            raise ValueError("Lineage imputed family entry is not an object.")
        family_id = str(raw["id"])
        stage = str(raw["stage"])
        entity = str(raw["entity"])
        family = str(raw["family"])
        targets = tuple(str(item) for item in raw["targets"])
        # Early families declare their runtime bound explicitly.  Each late
        # family is already one registry-bounded transfer group, so its full
        # declared target tuple is the chain.
        max_targets = int(raw.get("max_targets_per_fit", len(targets)))
        if family_id in observed_ids:
            raise ValueError(f"Lineage spec repeats family id {family_id!r}.")
        observed_ids.add(family_id)

        if stage == "early_gap_fill":
            order_key = f"early_gap_fill/{entity}/{family}"
        elif stage == "late_transfer":
            order_key = family_id
        else:
            raise ValueError(f"Unsupported Phase-P family stage {stage!r}.")
        try:
            baseline_targets = baseline_orders[order_key]
            candidate_targets = candidate_orders[order_key]
        except KeyError as exc:
            raise ValueError(
                f"Artifact target receipts do not bind family {family_id!r}."
            ) from exc
        if set(baseline_targets) != set(targets):
            raise ValueError(
                f"Baseline targets for {family_id!r} differ from the Phase-P "
                f"declaration: receipt={baseline_targets}, declared={targets}."
            )
        if candidate_targets != targets:
            raise ValueError(
                f"Candidate target order for {family_id!r} differs from the "
                f"Phase-P declaration: receipt={candidate_targets}, "
                f"declared={targets}."
            )

        baseline_predictors = _legacy_predictor_set(
            entity=entity,
            targets=baseline_targets,
        )
        surface = {entity: {family: candidate_targets}}
        if stage == "early_gap_fill":
            candidate_predictors = declared_acs_transfer_predictor_sets(surface)[
                entity
            ][family]
        else:
            candidate_predictors = declared_stacked_post_puf_predictor_sets(surface)[
                entity
            ][family]
        result.append(
            FamilySpec(
                family_id=family_id,
                stage=stage,
                entity=entity,
                family=family,
                baseline_targets=baseline_targets,
                candidate_targets=candidate_targets,
                max_targets_per_fit=max_targets,
                baseline_predictor_set=baseline_predictors,
                candidate_predictor_set=candidate_predictors,
            )
        )
    if len(result) != 32:
        raise ValueError(
            f"Phase-P lineage must bind exactly 32 changed families; got {len(result)}."
        )
    return tuple(result)


def _donor_projection(frame: Frame, *, clone_index: int) -> Frame:
    person = frame.table(frame.schema.person_entity)
    required = {"person_support_channel", "person_support_clone_index"}
    missing = sorted(required - set(person.columns))
    if missing:
        raise ValueError(f"OOS donor projection lacks person columns {missing}.")
    mask = (
        person["person_support_channel"].astype(str).eq(_ASEC_CHANNEL)
        & pd.to_numeric(person["person_support_clone_index"], errors="raise").eq(
            clone_index
        )
    ).to_numpy()
    if not mask.any():
        raise ValueError(
            f"OOS donor projection found no ASEC clone-{clone_index} person rows."
        )
    return frame.select(mask)


def _source_ids(frame: Frame, *, entity: str) -> np.ndarray:
    table = frame.table(entity)
    column = f"{entity}_source_id"
    if column not in table:
        raise ValueError(f"OOS donor entity {entity!r} lacks stable id {column!r}.")
    values = table[column].astype(str).to_numpy(dtype=object)
    if pd.isna(table[column]).any():
        raise ValueError(f"OOS donor stable id {column!r} contains nulls.")
    if len(set(values.tolist())) != len(values):
        raise ValueError(f"OOS donor stable id {column!r} is not unique.")
    return values


def _folds_and_clusters(
    ids: np.ndarray, *, entity: str
) -> tuple[np.ndarray, np.ndarray]:
    fold = PHASE_P_CONFIG["fold"]
    bootstrap = PHASE_P_CONFIG["bootstrap"]
    assert isinstance(fold, Mapping) and isinstance(bootstrap, Mapping)
    fold_namespace = f"phase-p-fold-v1:{int(fold['seed'])}:{entity}"
    cluster_namespace = f"phase-p-bootstrap-v1:{int(bootstrap['seed'])}:{entity}"
    folds = np.fromiter(
        (
            _stable_bucket(
                item,
                namespace=fold_namespace,
                buckets=int(fold["fold_count"]),
            )
            for item in ids
        ),
        dtype=np.int16,
        count=len(ids),
    )
    clusters = np.fromiter(
        (
            _stable_bucket(
                item,
                namespace=cluster_namespace,
                buckets=int(bootstrap["clusters"]),
            )
            for item in ids
        ),
        dtype=np.int16,
        count=len(ids),
    )
    return folds, clusters


def _as_float_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            column: frame[column].to_numpy(dtype=np.float64, na_value=np.nan)
            for column in frame.columns
        },
        index=frame.index,
    )


def _prepare_design(
    features: pd.DataFrame,
    *,
    required: Sequence[str],
    optional: Sequence[str],
    predecessors: pd.DataFrame,
    y: np.ndarray,
    weights: np.ndarray,
    folds: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple[str, ...]]:
    """Return explicit train/test matrices and masks for one target."""

    fold = PHASE_P_CONFIG["fold"]
    assert isinstance(fold, Mapping)
    held_out = int(fold["held_out_fold"])
    base = _as_float_frame(features.loc[:, [*required, *optional]])
    chain = _as_float_frame(predecessors)
    required_matrix = pd.concat([base.loc[:, list(required)], chain], axis=1)
    required_complete = np.isfinite(required_matrix.to_numpy(copy=False)).all(axis=1)
    valid = required_complete & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    train_mask = valid & (folds != held_out)
    test_mask = valid & (folds == held_out)

    train_parts = [required_matrix.loc[train_mask].to_numpy(dtype=np.float64)]
    test_parts = [required_matrix.loc[test_mask].to_numpy(dtype=np.float64)]
    unavailable: list[str] = []
    for predictor in optional:
        train_values = base.loc[train_mask, predictor].to_numpy(dtype=np.float64)
        test_values = base.loc[test_mask, predictor].to_numpy(dtype=np.float64)
        finite = np.isfinite(train_values)
        if not finite.any():
            unavailable.append(predictor)
            continue
        median = float(np.median(train_values[finite]))
        train_parts.extend(
            [
                np.where(finite, train_values, median)[:, None],
                finite.astype(np.float64)[:, None],
            ]
        )
        test_finite = np.isfinite(test_values)
        test_parts.extend(
            [
                np.where(test_finite, test_values, median)[:, None],
                test_finite.astype(np.float64)[:, None],
            ]
        )
    return (
        np.concatenate(train_parts, axis=1),
        np.concatenate(test_parts, axis=1),
        y[train_mask],
        y[test_mask],
        weights[train_mask],
        tuple(unavailable),
    )


def _fit_target_loss(
    *,
    key: str,
    train_x: np.ndarray,
    test_x: np.ndarray,
    train_y: np.ndarray,
    test_y: np.ndarray,
    train_weights: np.ndarray,
) -> np.ndarray:
    forest = PHASE_P_CONFIG["forest"]
    quantiles = np.asarray(PHASE_P_CONFIG["quantiles"], dtype=np.float64)
    assert isinstance(forest, Mapping)
    minimum_train = int(forest["minimum_training_rows"])
    minimum_test = int(forest["minimum_holdout_rows"])
    if len(train_y) < minimum_train or len(test_y) < minimum_test:
        raise ValueError(
            f"OOS target {key} has insufficient donors: train={len(train_y)} "
            f"(minimum {minimum_train}), holdout={len(test_y)} "
            f"(minimum {minimum_test})."
        )
    probability = train_weights / train_weights.sum()
    rng = np.random.default_rng(_seed("phase-p-oos-fit", forest["seed"], key))
    sampled = rng.choice(len(train_y), size=len(train_y), replace=True, p=probability)
    model = RandomForestQuantileRegressor(
        n_estimators=int(forest["n_estimators"]),
        default_quantiles=float(forest["default_quantiles"]),
        criterion=str(forest["criterion"]),
        max_depth=int(forest["max_depth"]),
        min_samples_split=int(forest["min_samples_split"]),
        min_samples_leaf=int(forest["min_samples_leaf"]),
        max_samples_leaf=int(forest["max_samples_leaf"]),
        min_weight_fraction_leaf=float(forest["min_weight_fraction_leaf"]),
        max_features=float(forest["max_features"]),
        max_leaf_nodes=forest["max_leaf_nodes"],
        min_impurity_decrease=float(forest["min_impurity_decrease"]),
        bootstrap=bool(forest["bootstrap"]),
        oob_score=bool(forest["oob_score"]),
        n_jobs=int(forest["n_jobs"]),
        random_state=_seed("phase-p-oos-forest", forest["seed"], key),
        verbose=int(forest["verbose"]),
        warm_start=bool(forest["warm_start"]),
        ccp_alpha=float(forest["ccp_alpha"]),
        max_samples=float(forest["max_samples"]),
        monotonic_cst=forest["monotonic_cst"],
    )
    model.fit(train_x[sampled], train_y[sampled])
    predicted = model.predict(
        test_x,
        quantiles=quantiles.tolist(),
        interpolation=str(forest["predict_interpolation"]),
        weighted_quantile=bool(forest["predict_weighted_quantile"]),
        weighted_leaves=bool(forest["predict_weighted_leaves"]),
        aggregate_leaves_first=bool(forest["predict_aggregate_leaves_first"]),
        oob_score=False,
        indices=None,
        duplicates=None,
    )
    predicted = np.asarray(predicted, dtype=np.float64)
    if predicted.shape != (len(test_y), len(quantiles)):
        raise RuntimeError(
            f"OOS target {key} produced quantile matrix {predicted.shape}; "
            f"expected {(len(test_y), len(quantiles))}."
        )
    residual = test_y[:, None] - predicted
    losses = np.maximum(quantiles * residual, (quantiles - 1.0) * residual)
    return losses.mean(axis=1)


def _bounded_chunks(targets: Sequence[str], width: int) -> list[tuple[str, ...]]:
    return [
        tuple(targets[start : start + width]) for start in range(0, len(targets), width)
    ]


def _measure_family(
    donor: Frame,
    *,
    spec: FamilySpec,
    arm: str,
) -> dict[str, OOSTargetMeasurement]:
    targets = spec.baseline_targets if arm == "baseline" else spec.candidate_targets
    predictor_set = (
        spec.baseline_predictor_set
        if arm == "baseline"
        else spec.candidate_predictor_set
    )
    surface = _transfer_feature_surface(
        donor,
        donor,
        entity=spec.entity,
        targets=targets,
        predictor_set=predictor_set,
        require_all_predictors=False,
    )
    resolved_optional = tuple(surface.optional)
    missing_optional = tuple(
        predictor
        for predictor in predictor_set.optional
        if predictor not in resolved_optional
    )
    table = donor.table(spec.entity)
    ids = _source_ids(donor, entity=spec.entity)
    weights = donor.resolve_weights(spec.entity).values
    folds, clusters = _folds_and_clusters(ids, entity=spec.entity)
    holdout_mask = folds == int(PHASE_P_CONFIG["fold"]["held_out_fold"])
    results: dict[str, OOSTargetMeasurement] = {}

    for chunk in _bounded_chunks(targets, spec.max_targets_per_fit):
        complete = _complete_target_mask(table, targets=chunk)
        encodings = _complete_case_target_encodings(
            table,
            targets=chunk,
            complete=complete,
        )
        model_order: list[str] = []
        model_values: dict[str, pd.Series] = {}
        targets_by_model: dict[str, list[str]] = {}
        for target in chunk:
            encoding = encodings[target]
            targets_by_model.setdefault(encoding.model_target, []).append(target)
            if encoding.model_target not in model_values:
                model_order.append(encoding.model_target)
                model_values[encoding.model_target] = encoding.model_values

        for model_position, model_target in enumerate(model_order):
            exported_targets = targets_by_model[model_target]
            predecessors = tuple(model_order[:model_position])
            predecessor_frame = pd.DataFrame(
                {
                    f"__phase_p_chain_{position:02d}": model_values[name]
                    for position, name in enumerate(predecessors)
                },
                index=table.index,
            )
            y = model_values[model_target].to_numpy(dtype=np.float64)
            (
                train_x,
                test_x,
                train_y,
                test_y,
                train_weights,
                all_missing_optional,
            ) = _prepare_design(
                surface.donor,
                required=surface.required,
                optional=resolved_optional,
                predecessors=predecessor_frame,
                y=y,
                weights=weights,
                folds=folds,
            )
            # Excluding the arm from the seed key is deliberate: paired arms
            # consume the same bootstrap/forest randomness for a target, so
            # the loss delta is not polluted by independent Monte Carlo noise.
            model_key = f"{spec.family_id}/{model_target}"
            losses = _fit_target_loss(
                key=model_key,
                train_x=train_x,
                test_x=test_x,
                train_y=train_y,
                test_y=test_y,
                train_weights=train_weights,
            )

            valid = (
                np.isfinite(y)
                & np.isfinite(weights)
                & (weights > 0)
                & np.isfinite(
                    _as_float_frame(
                        pd.concat(
                            [
                                surface.donor.loc[:, list(surface.required)],
                                predecessor_frame,
                            ],
                            axis=1,
                        )
                    ).to_numpy(copy=False)
                ).all(axis=1)
            )
            test_positions = np.flatnonzero(valid & holdout_mask)
            if len(test_positions) != len(losses):
                raise RuntimeError(
                    f"OOS target {model_key} lost holdout row alignment."
                )
            unavailable = tuple(
                dict.fromkeys([*missing_optional, *all_missing_optional])
            )
            resolved = tuple(
                [
                    *surface.required,
                    *(
                        predictor
                        for predictor in resolved_optional
                        if predictor not in all_missing_optional
                    ),
                    *predecessors,
                ]
            )
            for target in exported_targets:
                key = f"{spec.family_id}/{target}"
                results[key] = OOSTargetMeasurement(
                    key=key,
                    family_id=spec.family_id,
                    stage=spec.stage,
                    entity=spec.entity,
                    family=spec.family,
                    target=target,
                    target_position=targets.index(target),
                    chain_predecessors=predecessors,
                    predictor_set={
                        "required": list(predictor_set.required),
                        "optional": list(predictor_set.optional),
                    },
                    resolved_predictors=resolved,
                    unavailable_optional_predictors=unavailable,
                    training_rows=len(train_y),
                    holdout_rows=len(test_y),
                    ids=ids[test_positions].copy(),
                    weights=weights[test_positions].copy(),
                    truth=test_y.copy(),
                    losses=losses.copy(),
                    clusters=clusters[test_positions].copy(),
                )
    expected = {f"{spec.family_id}/{target}" for target in targets}
    if set(results) != expected:
        raise RuntimeError(
            f"OOS family {spec.family_id!r} did not measure every target: "
            f"missing={sorted(expected - set(results))}, "
            f"extra={sorted(set(results) - expected)}."
        )
    return results


def _champva_incidence(frame: Frame) -> dict[str, IncidenceMeasurement]:
    person = frame.table("person")
    target = "has_champva_health_coverage_at_interview"
    required = {
        target,
        "person_source_id",
        "person_support_channel",
        "person_support_clone_index",
    }
    missing = sorted(required - set(person.columns))
    if missing:
        raise ValueError(f"CHAMPVA bootstrap lacks person columns {missing}.")
    weights = frame.resolve_weights("person").values
    channel = person["person_support_channel"].astype(str)
    clone = pd.to_numeric(person["person_support_clone_index"], errors="raise")
    values = person[target].to_numpy(dtype=np.float64, na_value=np.nan)
    results: dict[str, IncidenceMeasurement] = {}
    for origin in (_ASEC_CHANNEL, _ACS_CHANNEL):
        mask = (
            channel.eq(origin).to_numpy()
            & clone.eq(_CLONE_ZERO).to_numpy()
            & np.isfinite(values)
            & np.isfinite(weights)
            & (weights > 0)
        )
        ids = person.loc[mask, "person_source_id"].astype(str).to_numpy(dtype=object)
        if len(set(ids.tolist())) != len(ids):
            raise ValueError(f"CHAMPVA {origin} source ids are not unique.")
        _, clusters = _folds_and_clusters(ids, entity=f"person:{origin}")
        results[origin] = IncidenceMeasurement(
            origin=origin,
            ids=ids,
            weights=weights[mask].copy(),
            values=values[mask].copy(),
            clusters=clusters,
        )
    return results


def measure_arm(
    artifact: Artifact,
    *,
    arm: str,
    family_specs: Sequence[FamilySpec],
) -> ArmMeasurement:
    """Load one large checkpoint once, retain only compact OOS measurements."""

    loaded = load_frame_checkpoint(artifact.checkpoint_path)
    frame = loaded.frame
    incidence = _champva_incidence(frame)
    targets: dict[str, OOSTargetMeasurement] = {}
    completed = 0
    for clone_index in (_CLONE_ZERO, _PUF_CLONE):
        matching_specs = [
            spec for spec in family_specs if spec.donor_clone_index == clone_index
        ]
        if not matching_specs:
            continue
        donor = _donor_projection(frame, clone_index=clone_index)
        for spec in matching_specs:
            completed += 1
            print(
                f"phase-p-oos: {arm} family {completed}/{len(family_specs)} "
                f"{spec.family_id}",
                flush=True,
            )
            try:
                measured = _measure_family(donor, spec=spec, arm=arm)
            except Exception as error:
                raise GateMeasurementError(
                    arm=arm,
                    family_id=spec.family_id,
                    stage=spec.stage,
                    entity=spec.entity,
                    family=spec.family,
                    cause=error,
                ) from error
            overlap = sorted(set(targets).intersection(measured))
            if overlap:
                raise RuntimeError(
                    f"OOS target keys repeat across families: {overlap}."
                )
            targets.update(measured)
        del donor
        gc.collect()
    del frame, loaded
    gc.collect()
    return ArmMeasurement(targets=targets, champva_by_origin=incidence)


def _battery_gate(artifact: Artifact) -> dict[str, object]:
    value = _nested(
        artifact.gates,
        "terminal_gates",
        "gates",
        "us_by_origin_battery",
    )
    if not isinstance(value, dict):
        raise ValueError(f"Battery gate in {artifact.gates_path} is malformed.")
    return value


def _battery(artifact: Artifact) -> dict[str, object]:
    value = _battery_gate(artifact).get("details")
    if not isinstance(value, dict):
        raise ValueError(f"Battery details in {artifact.gates_path} are malformed.")
    return value


def _battery_legs(artifact: Artifact) -> dict[str, dict[str, object]]:
    battery = _battery(artifact)
    comparisons = battery.get("comparisons")
    if not isinstance(comparisons, Mapping):
        raise ValueError(f"Battery comparisons in {artifact.gates_path} are malformed.")
    failures = _battery_gate(artifact).get("failures")
    if not isinstance(failures, list) or not all(
        isinstance(failure, str) for failure in failures
    ):
        raise ValueError(f"Battery failures in {artifact.gates_path} are malformed.")
    result: dict[str, dict[str, object]] = {}
    for comparison_id, raw in comparisons.items():
        if not isinstance(raw, Mapping):
            raise ValueError(f"Battery comparison {comparison_id!r} is malformed.")
        metric = raw.get("metric")
        legs = raw.get("legs")
        if isinstance(legs, Mapping):
            for leg_name, leg in legs.items():
                if not isinstance(leg, Mapping):
                    raise ValueError(
                        f"Battery leg {comparison_id}/{leg_name} is malformed."
                    )
                leg_id = f"{comparison_id}/{leg_name}"
                leg_failures = [
                    failure for failure in failures if failure.startswith(f"{leg_id}:")
                ]
                operational_status = leg.get("status") or raw.get("status")
                result[leg_id] = {
                    "comparison_id": comparison_id,
                    "leg": leg_name,
                    "metric": metric,
                    "raw_status": operational_status,
                    "gate_status": _gate_leg_status(
                        operational_status,
                        leg_failures,
                    ),
                    "failure_messages": leg_failures,
                    "ratio": leg.get("incidence_ratio_acs_over_asec"),
                    "asec_incidence": leg.get("asec_incidence"),
                    "acs_incidence": leg.get("acs_incidence"),
                    "nonzero_rows": leg.get("nonzero_rows"),
                    "quantile_envelope_distance": leg.get("quantile_envelope_distance"),
                    "total_variation_distance": None,
                }
        else:
            leg_id = str(comparison_id)
            leg_failures = [
                failure for failure in failures if failure.startswith(f"{leg_id}:")
            ]
            operational_status = raw.get("status")
            result[leg_id] = {
                "comparison_id": comparison_id,
                "leg": None,
                "metric": metric,
                "raw_status": operational_status,
                "gate_status": _gate_leg_status(
                    operational_status,
                    leg_failures,
                ),
                "failure_messages": leg_failures,
                "ratio": raw.get("incidence_ratio_acs_over_asec"),
                "asec_incidence": raw.get("asec_incidence"),
                "acs_incidence": raw.get("acs_incidence"),
                "nonzero_rows": raw.get("nonzero_rows"),
                "quantile_envelope_distance": raw.get("quantile_envelope_distance"),
                "total_variation_distance": raw.get("total_variation_distance"),
            }
    mapped_failures = [
        failure for leg in result.values() for failure in leg["failure_messages"]
    ]
    if Counter(mapped_failures) != Counter(failures):
        missing = list((Counter(failures) - Counter(mapped_failures)).elements())
        repeated = list((Counter(mapped_failures) - Counter(failures)).elements())
        raise ValueError(
            f"Battery failures in {artifact.gates_path} did not map exactly once "
            f"to physical legs; unmatched={missing}, multiply_mapped={repeated}."
        )
    return result


def _gate_leg_status(
    operational_status: object,
    failure_messages: Sequence[str],
) -> str:
    if failure_messages or operational_status == "dead_comparison":
        return "FAIL"
    if operational_status in {"absent_on_both_origins", "insufficient_support"}:
        return "NOT_TESTED"
    if operational_status == "tested":
        return "PASS"
    raise ValueError(
        f"Unknown battery operational status {operational_status!r}; refusing "
        "to infer a gate status."
    )


def _band_status(ratio: object, *, lower: float, upper: float) -> str:
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float, str)):
        return "not_ratio_comparable"
    try:
        numeric = float(ratio)
    except ValueError:
        return "not_ratio_comparable"
    if math.isnan(numeric):
        return "not_ratio_comparable"
    return "in_band" if lower <= numeric <= upper else "out_of_band"


def battery_delta(
    baseline: Artifact,
    candidate: Artifact,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    baseline_legs = _battery_legs(baseline)
    candidate_legs = _battery_legs(candidate)
    if set(baseline_legs) != set(candidate_legs):
        raise ValueError(
            "Baseline/candidate battery leg sets differ: "
            f"missing_candidate={sorted(set(baseline_legs) - set(candidate_legs))}, "
            f"extra_candidate={sorted(set(candidate_legs) - set(baseline_legs))}."
        )
    lower, upper = map(float, PHASE_P_CONFIG["verdict"]["ratio_band"])
    counts = {
        "total_legs": 0,
        "ratio_comparable_legs": 0,
        "entered_band": 0,
        "left_band": 0,
        "unchanged": 0,
        "unchanged_in_band": 0,
        "unchanged_out_of_band": 0,
        "unchanged_not_ratio_comparable": 0,
    }
    rows: list[dict[str, object]] = []
    for leg_id in sorted(baseline_legs):
        base = baseline_legs[leg_id]
        cand = candidate_legs[leg_id]
        if base["metric"] != cand["metric"]:
            raise ValueError(f"Battery metric changed for {leg_id!r}.")
        base_status = _band_status(base["ratio"], lower=lower, upper=upper)
        candidate_status = _band_status(cand["ratio"], lower=lower, upper=upper)
        counts["total_legs"] += 1
        transition: str
        if base_status != "in_band" and candidate_status == "in_band":
            transition = "entered_band"
        elif base_status == "in_band" and candidate_status != "in_band":
            transition = "left_band"
        elif base_status == candidate_status == "in_band":
            transition = "unchanged_in_band"
        elif base_status == candidate_status == "out_of_band":
            transition = "unchanged_out_of_band"
        else:
            transition = "unchanged_not_ratio_comparable"
        counts[transition] += 1
        if transition.startswith("unchanged_"):
            counts["unchanged"] += 1
        if base_status != "not_ratio_comparable" and candidate_status != (
            "not_ratio_comparable"
        ):
            counts["ratio_comparable_legs"] += 1
        rows.append(
            {
                "leg_id": leg_id,
                "metric": base["metric"],
                "baseline": {
                    **base,
                    "band_status": base_status,
                },
                "candidate": {
                    **cand,
                    "band_status": candidate_status,
                },
                "gate_status_transition": (
                    f"{base['gate_status']}->{cand['gate_status']}"
                ),
                "transition": transition,
            }
        )
    return rows, counts


def participation_incidence(
    baseline: Artifact,
    candidate: Artifact,
) -> list[dict[str, object]]:
    base = _battery_legs(baseline)
    cand = _battery_legs(candidate)
    rows: list[dict[str, object]] = []
    for leg_id in sorted(base):
        if "/model_required_boolean/" not in leg_id:
            continue
        if leg_id not in cand:
            raise ValueError(f"Candidate battery lacks participation leg {leg_id!r}.")
        rows.append(
            {
                "leg_id": leg_id,
                "baseline": {
                    "asec_incidence": base[leg_id]["asec_incidence"],
                    "acs_incidence": base[leg_id]["acs_incidence"],
                    "incidence_ratio_acs_over_asec": base[leg_id]["ratio"],
                    "nonzero_rows": base[leg_id]["nonzero_rows"],
                },
                "candidate": {
                    "asec_incidence": cand[leg_id]["asec_incidence"],
                    "acs_incidence": cand[leg_id]["acs_incidence"],
                    "incidence_ratio_acs_over_asec": cand[leg_id]["ratio"],
                    "nonzero_rows": cand[leg_id]["nonzero_rows"],
                },
            }
        )
    if not rows:
        raise ValueError("Battery contains no model_required_boolean targets.")
    return rows


def _align_measurements(
    baseline_ids: np.ndarray,
    candidate_ids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    base_index = pd.Index(baseline_ids)
    candidate_index = pd.Index(candidate_ids)
    common = base_index.intersection(candidate_index, sort=True)
    if common.empty:
        raise ValueError("Paired measurement has no common stable donor ids.")
    base_positions = base_index.get_indexer(common)
    candidate_positions = candidate_index.get_indexer(common)
    if (base_positions < 0).any() or (candidate_positions < 0).any():
        raise RuntimeError("Paired donor alignment produced missing positions.")
    return base_positions, candidate_positions


def _cluster_sums(
    clusters: np.ndarray,
    weights: np.ndarray,
    values: np.ndarray,
    *,
    cluster_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    denominator = np.bincount(clusters, weights=weights, minlength=cluster_count)
    numerator = np.bincount(
        clusters,
        weights=weights * values,
        minlength=cluster_count,
    )
    return numerator, denominator


def _bootstrap_ci(values: np.ndarray) -> list[float]:
    bootstrap = PHASE_P_CONFIG["bootstrap"]
    assert isinstance(bootstrap, Mapping)
    alpha = (1.0 - float(bootstrap["confidence_level"])) / 2.0
    return [
        float(
            np.quantile(
                values,
                alpha,
                method=str(bootstrap["percentile_method"]),
            )
        ),
        float(
            np.quantile(
                values,
                1.0 - alpha,
                method=str(bootstrap["percentile_method"]),
            )
        ),
    ]


def _paired_loss_comparison(
    baseline: OOSTargetMeasurement,
    candidate: OOSTargetMeasurement,
) -> dict[str, object]:
    base_pos, cand_pos = _align_measurements(baseline.ids, candidate.ids)
    base_weights = baseline.weights[base_pos]
    candidate_weights = candidate.weights[cand_pos]
    if not np.allclose(base_weights, candidate_weights, rtol=0.0, atol=1e-10):
        raise ValueError(f"Paired OOS weights changed for {baseline.key!r}.")
    if not np.allclose(
        baseline.truth[base_pos],
        candidate.truth[cand_pos],
        rtol=0.0,
        atol=1e-10,
        equal_nan=False,
    ):
        raise ValueError(f"Paired OOS donor truth changed for {baseline.key!r}.")
    base_loss = baseline.losses[base_pos]
    candidate_loss = candidate.losses[cand_pos]
    weight_total = float(base_weights.sum())
    base_mean = float(np.dot(base_weights, base_loss) / weight_total)
    candidate_mean = float(np.dot(base_weights, candidate_loss) / weight_total)
    delta = candidate_mean - base_mean

    bootstrap = PHASE_P_CONFIG["bootstrap"]
    assert isinstance(bootstrap, Mapping)
    cluster_count = int(bootstrap["clusters"])
    base_clusters = baseline.clusters[base_pos]
    candidate_clusters = candidate.clusters[cand_pos]
    if not np.array_equal(base_clusters, candidate_clusters):
        raise ValueError(f"Paired OOS bootstrap clusters changed for {baseline.key!r}.")
    base_num, denominator = _cluster_sums(
        base_clusters,
        base_weights,
        base_loss,
        cluster_count=cluster_count,
    )
    cand_num, cand_denominator = _cluster_sums(
        base_clusters,
        base_weights,
        candidate_loss,
        cluster_count=cluster_count,
    )
    if not np.array_equal(denominator, cand_denominator):
        raise RuntimeError("Paired OOS cluster denominators changed unexpectedly.")
    active = np.flatnonzero(denominator > 0)
    if len(active) < 2:
        raise ValueError(f"OOS target {baseline.key!r} has fewer than two clusters.")
    rng = np.random.default_rng(
        _seed("phase-p-oos-bootstrap", bootstrap["seed"], baseline.key)
    )
    replicate_count = int(bootstrap["replicates"])
    replicate_delta = np.empty(replicate_count, dtype=np.float64)
    for start in range(0, replicate_count, 256):
        size = min(256, replicate_count - start)
        sampled = rng.integers(0, len(active), size=(size, len(active)))
        selected = active[sampled]
        denom = denominator[selected].sum(axis=1)
        replicate_delta[start : start + size] = (
            cand_num[selected].sum(axis=1) / denom
            - base_num[selected].sum(axis=1) / denom
        )
    ci = _bootstrap_ci(replicate_delta)
    return {
        "paired_rows": len(base_pos),
        "bootstrap_nonempty_clusters": len(active),
        "baseline_mean_pinball_loss": base_mean,
        "candidate_mean_pinball_loss": candidate_mean,
        "candidate_minus_baseline": delta,
        "candidate_minus_baseline_ci": ci,
        "statistically_significant_worsening": ci[0] > 0.0,
    }


def _target_metric_index(artifact: Artifact) -> dict[tuple[str, str, str], str]:
    result: dict[tuple[str, str, str], str] = {}
    for leg in _battery_legs(artifact).values():
        comparison_id = str(leg["comparison_id"])
        base = comparison_id.split("[", 1)[0]
        pieces = base.split("/", 2)
        if len(pieces) == 3:
            result[(pieces[0], pieces[1], pieces[2])] = str(leg["metric"])
    return result


def compare_oos(
    baseline: ArmMeasurement,
    candidate: ArmMeasurement,
    *,
    metric_index: Mapping[tuple[str, str, str], str],
) -> list[dict[str, object]]:
    if set(baseline.targets) != set(candidate.targets):
        raise ValueError(
            "Baseline/candidate OOS target sets differ: "
            f"missing_candidate={sorted(set(baseline.targets) - set(candidate.targets))}, "
            f"extra_candidate={sorted(set(candidate.targets) - set(baseline.targets))}."
        )
    rows: list[dict[str, object]] = []
    for key in sorted(baseline.targets):
        base = baseline.targets[key]
        cand = candidate.targets[key]
        battery_family = base.family.split("__batch_", 1)[0]
        metric = metric_index.get((base.entity, battery_family, base.target))
        if metric is None:
            raise ValueError(
                f"Battery does not classify OOS target {base.entity}/{base.family}/"
                f"{base.target}."
            )
        paired = _paired_loss_comparison(base, cand)
        rows.append(
            {
                "key": key,
                "family_id": base.family_id,
                "stage": base.stage,
                "entity": base.entity,
                "family": base.family,
                "target": base.target,
                "metric": metric,
                "is_money_amount": metric == "monetary_sign_separated",
                "baseline": {
                    "target_position": base.target_position,
                    "chain_predecessors": list(base.chain_predecessors),
                    "predictor_set": base.predictor_set,
                    "resolved_predictors": list(base.resolved_predictors),
                    "unavailable_optional_predictors": list(
                        base.unavailable_optional_predictors
                    ),
                    "training_rows": base.training_rows,
                    "holdout_rows": base.holdout_rows,
                },
                "candidate": {
                    "target_position": cand.target_position,
                    "chain_predecessors": list(cand.chain_predecessors),
                    "predictor_set": cand.predictor_set,
                    "resolved_predictors": list(cand.resolved_predictors),
                    "unavailable_optional_predictors": list(
                        cand.unavailable_optional_predictors
                    ),
                    "training_rows": cand.training_rows,
                    "holdout_rows": cand.holdout_rows,
                },
                "paired": paired,
            }
        )
    return rows


def _paired_incidence_origin(
    baseline: IncidenceMeasurement,
    candidate: IncidenceMeasurement,
) -> dict[str, object]:
    base_pos, cand_pos = _align_measurements(baseline.ids, candidate.ids)
    weights = baseline.weights[base_pos]
    if not np.allclose(weights, candidate.weights[cand_pos], rtol=0.0, atol=1e-10):
        raise ValueError(f"CHAMPVA {baseline.origin} weights changed between arms.")
    base_values = baseline.values[base_pos]
    candidate_values = candidate.values[cand_pos]
    if (
        not np.isin(base_values, [0.0, 1.0]).all()
        or not np.isin(candidate_values, [0.0, 1.0]).all()
    ):
        raise ValueError("CHAMPVA incidence inputs must be physical booleans.")
    base_clusters = baseline.clusters[base_pos]
    if not np.array_equal(base_clusters, candidate.clusters[cand_pos]):
        raise ValueError(f"CHAMPVA {baseline.origin} clusters changed between arms.")
    bootstrap = PHASE_P_CONFIG["bootstrap"]
    assert isinstance(bootstrap, Mapping)
    cluster_count = int(bootstrap["clusters"])
    base_num, denominator = _cluster_sums(
        base_clusters,
        weights,
        base_values,
        cluster_count=cluster_count,
    )
    candidate_num, candidate_denominator = _cluster_sums(
        base_clusters,
        weights,
        candidate_values,
        cluster_count=cluster_count,
    )
    if not np.array_equal(denominator, candidate_denominator):
        raise RuntimeError("CHAMPVA paired cluster denominator changed.")
    active = np.flatnonzero(denominator > 0)
    return {
        "rows": len(base_pos),
        "active_clusters": active,
        "baseline_numerator": base_num,
        "candidate_numerator": candidate_num,
        "denominator": denominator,
        "baseline_incidence": float(np.dot(weights, base_values) / weights.sum()),
        "candidate_incidence": float(np.dot(weights, candidate_values) / weights.sum()),
    }


def champva_ratio_bootstrap(
    baseline: ArmMeasurement,
    candidate: ArmMeasurement,
    *,
    baseline_ratio_receipt: float,
    candidate_ratio_receipt: float,
) -> dict[str, object]:
    origins = {
        origin: _paired_incidence_origin(
            baseline.champva_by_origin[origin],
            candidate.champva_by_origin[origin],
        )
        for origin in (_ASEC_CHANNEL, _ACS_CHANNEL)
    }
    base_ratio = (
        origins[_ACS_CHANNEL]["baseline_incidence"]
        / origins[_ASEC_CHANNEL]["baseline_incidence"]
    )
    candidate_ratio = (
        origins[_ACS_CHANNEL]["candidate_incidence"]
        / origins[_ASEC_CHANNEL]["candidate_incidence"]
    )
    if not math.isclose(base_ratio, baseline_ratio_receipt, rel_tol=1e-10, abs_tol=0.0):
        raise ValueError(
            "Baseline CHAMPVA checkpoint ratio does not reproduce its gates receipt: "
            f"checkpoint={base_ratio}, receipt={baseline_ratio_receipt}."
        )
    if not math.isclose(
        candidate_ratio,
        candidate_ratio_receipt,
        rel_tol=1e-10,
        abs_tol=0.0,
    ):
        raise ValueError(
            "Candidate CHAMPVA checkpoint ratio does not reproduce its gates receipt: "
            f"checkpoint={candidate_ratio}, receipt={candidate_ratio_receipt}."
        )

    bootstrap = PHASE_P_CONFIG["bootstrap"]
    assert isinstance(bootstrap, Mapping)
    replicate_count = int(bootstrap["replicates"])
    rng = np.random.default_rng(_seed("phase-p-champva-bootstrap", bootstrap["seed"]))
    replicate: dict[str, dict[str, np.ndarray]] = {}
    for origin, measured in origins.items():
        active = measured["active_clusters"]
        if len(active) < 2:
            raise ValueError(f"CHAMPVA {origin} has fewer than two clusters.")
        base_incidence = np.empty(replicate_count, dtype=np.float64)
        candidate_incidence = np.empty(replicate_count, dtype=np.float64)
        for start in range(0, replicate_count, 256):
            size = min(256, replicate_count - start)
            sampled = rng.integers(0, len(active), size=(size, len(active)))
            selected = active[sampled]
            denominator = measured["denominator"][selected].sum(axis=1)
            base_incidence[start : start + size] = (
                measured["baseline_numerator"][selected].sum(axis=1) / denominator
            )
            candidate_incidence[start : start + size] = (
                measured["candidate_numerator"][selected].sum(axis=1) / denominator
            )
        replicate[origin] = {
            "baseline": base_incidence,
            "candidate": candidate_incidence,
        }
    finite = (replicate[_ASEC_CHANNEL]["baseline"] > 0) & (
        replicate[_ASEC_CHANNEL]["candidate"] > 0
    )
    if int(finite.sum()) < math.ceil(0.95 * replicate_count):
        raise ValueError(
            "Too many CHAMPVA bootstrap replicates have zero ASEC incidence."
        )
    base_rep_ratio = (
        replicate[_ACS_CHANNEL]["baseline"][finite]
        / replicate[_ASEC_CHANNEL]["baseline"][finite]
    )
    candidate_rep_ratio = (
        replicate[_ACS_CHANNEL]["candidate"][finite]
        / replicate[_ASEC_CHANNEL]["candidate"][finite]
    )
    improvement = base_rep_ratio - candidate_rep_ratio
    return {
        "baseline_ratio": base_ratio,
        "candidate_ratio": candidate_ratio,
        "baseline_minus_candidate": base_ratio - candidate_ratio,
        "baseline_minus_candidate_ci": _bootstrap_ci(improvement),
        "finite_bootstrap_replicates": int(finite.sum()),
        "origin_rows": {
            origin: int(measured["rows"]) for origin, measured in origins.items()
        },
    }


def _artifact_receipt(artifact: Artifact) -> dict[str, object]:
    external = _external_metadata(artifact)
    identity = external.get("identity")
    return {
        "artifact_dir": str(artifact.root),
        "gates_json": str(artifact.gates_path),
        "gates_json_sha256": _sha256_file(artifact.gates_path),
        "simulated_checkpoint_h5": str(artifact.checkpoint_path),
        "simulated_checkpoint_size_bytes": artifact.checkpoint_path.stat().st_size,
        "stacked_identity": artifact.checkpoint_path.parent.name,
        "checkpoint_identity_sha256": external.get("identity_sha256"),
        "run_identity": identity if isinstance(identity, Mapping) else None,
    }


def _gate_implementation_receipt() -> dict[str, str]:
    path = Path(__file__).resolve()
    return {"path": str(path), "sha256": _sha256_file(path)}


def measurement_failure_verdict(
    *,
    baseline_path: str | Path,
    candidate_path: str | Path,
    error: Exception,
) -> dict[str, object]:
    """Return a machine-decidable FAIL when the required sweep cannot finish."""

    context = error.context if isinstance(error, GateMeasurementError) else None
    return {
        "schema_version": 1,
        "artifact_kind": "phase_p_predictor_set_oos_acceptance_verdict",
        "verdict": "FAIL",
        "passed": False,
        "measurement_complete": False,
        "failing_clauses": ["measurement_integrity"],
        "rule": {
            "pass_iff": PHASE_P_CONFIG["verdict"]["pass_iff"],
            "measurement_precondition": (
                "All declared family/target OOS measurements, battery legs, and "
                "paired bootstrap inputs must be available before clauses a-c "
                "can be evaluated; otherwise the verdict is FAIL."
            ),
        },
        "clauses": {
            "measurement_integrity": {
                "passed": False,
                "error_type": type(error).__name__,
                "error": str(error),
                "context": context,
            },
            "a_champva": {"passed": None, "evaluated": False},
            "b_money_oos": {"passed": None, "evaluated": False},
            "c_no_battery_leg_leaves_band": {
                "passed": None,
                "evaluated": False,
            },
        },
        "config": PHASE_P_CONFIG,
        "gate_implementation": _gate_implementation_receipt(),
        "artifacts": {
            "baseline": {"artifact_dir": str(Path(baseline_path).resolve())},
            "candidate": {"artifact_dir": str(Path(candidate_path).resolve())},
        },
    }


def build_verdict(
    *,
    baseline: Artifact,
    candidate: Artifact,
    oos_rows: list[dict[str, object]],
    battery_rows: list[dict[str, object]],
    battery_counts: dict[str, int],
    participation_rows: list[dict[str, object]],
    champva_ci: dict[str, object],
    family_specs: Sequence[FamilySpec],
) -> dict[str, object]:
    rule = PHASE_P_CONFIG["verdict"]
    assert isinstance(rule, Mapping)
    lower, upper = map(float, rule["ratio_band"])
    baseline_ratio = float(champva_ci["baseline_ratio"])
    candidate_ratio = float(champva_ci["candidate_ratio"])
    improvement_ci = list(champva_ci["baseline_minus_candidate_ci"])
    enters_band = lower <= candidate_ratio <= upper
    denominator = baseline_ratio - upper
    progress = (
        (baseline_ratio - candidate_ratio) / denominator
        if denominator > 0
        else float("nan")
    )
    progress_pass = (
        math.isfinite(progress)
        and progress >= float(rule["champva_minimum_progress_to_band_ceiling"])
        and float(improvement_ci[0]) > 0.0
    )
    clause_a = enters_band or progress_pass

    money_rows = [row for row in oos_rows if row["is_money_amount"]]
    money_worsened = [
        str(row["key"])
        for row in money_rows
        if row["paired"]["statistically_significant_worsening"]
    ]
    clause_b = bool(money_rows) and not money_worsened
    clause_c = battery_counts["left_band"] == 0
    clauses = {
        "a_champva": {
            "passed": clause_a,
            "candidate_enters_band": enters_band,
            "progress_from_baseline_to_band_ceiling": progress,
            "minimum_progress": rule["champva_minimum_progress_to_band_ceiling"],
            "improvement_ci_excludes_zero": float(improvement_ci[0]) > 0.0,
            "baseline_minus_candidate_ratio_ci": improvement_ci,
        },
        "b_money_oos": {
            "passed": clause_b,
            "money_target_count": len(money_rows),
            "significantly_worsened_targets": money_worsened,
            "worsening_definition": rule["money_worsening"],
        },
        "c_no_battery_leg_leaves_band": {
            "passed": clause_c,
            "leaving_band_count": battery_counts["left_band"],
        },
    }
    passed = all(bool(clause["passed"]) for clause in clauses.values())
    failing = [name for name, clause in clauses.items() if not clause["passed"]]
    return {
        "schema_version": 1,
        "artifact_kind": "phase_p_predictor_set_oos_acceptance_verdict",
        "verdict": "PASS" if passed else "FAIL",
        "passed": passed,
        "measurement_complete": True,
        "failing_clauses": failing,
        "rule": {
            "pass_iff": rule["pass_iff"],
            "a": (
                "CHAMPVA ratio enters [0.8, 1.25], or reaches at least 50% "
                "of the baseline-to-1.25 distance with the paired bootstrap "
                "improvement CI strictly above zero."
            ),
            "b": (
                "No monetary target has a candidate-minus-baseline OOS "
                "pinball-loss bootstrap CI strictly above zero."
            ),
            "c": "No ratio-bearing battery leg leaves [0.8, 1.25].",
        },
        "clauses": clauses,
        "config": PHASE_P_CONFIG,
        "gate_implementation": _gate_implementation_receipt(),
        "artifacts": {
            "baseline": _artifact_receipt(baseline),
            "candidate": _artifact_receipt(candidate),
        },
        "family_count": len(family_specs),
        "target_count": len(oos_rows),
        "families": [
            {
                **{
                    key: value
                    for key, value in asdict(spec).items()
                    if key not in {"baseline_predictor_set", "candidate_predictor_set"}
                },
                "baseline_predictor_set": {
                    "required": list(spec.baseline_predictor_set.required),
                    "optional": list(spec.baseline_predictor_set.optional),
                },
                "candidate_predictor_set": {
                    "required": list(spec.candidate_predictor_set.required),
                    "optional": list(spec.candidate_predictor_set.optional),
                },
            }
            for spec in family_specs
        ],
        "oos_pinball_loss": oos_rows,
        "by_origin_battery": {
            "counts": battery_counts,
            "legs": battery_rows,
        },
        "participation_incidence": participation_rows,
        "champva_ratio_bootstrap": champva_ci,
    }


def run_gate(
    baseline_path: str | Path,
    candidate_path: str | Path,
    *,
    family_specs: Sequence[FamilySpec] | None = None,
) -> dict[str, object]:
    baseline = resolve_artifact(baseline_path)
    candidate = resolve_artifact(candidate_path)
    specs = (
        tuple(family_specs)
        if family_specs is not None
        else production_family_specs(baseline, candidate)
    )
    battery_rows, battery_counts = battery_delta(baseline, candidate)
    participation_rows = participation_incidence(baseline, candidate)
    baseline_measurement = measure_arm(
        baseline,
        arm="baseline",
        family_specs=specs,
    )
    candidate_measurement = measure_arm(
        candidate,
        arm="candidate",
        family_specs=specs,
    )
    metric_index = _target_metric_index(baseline)
    oos_rows = compare_oos(
        baseline_measurement,
        candidate_measurement,
        metric_index=metric_index,
    )
    champva_leg = str(PHASE_P_CONFIG["verdict"]["champva_leg"])
    base_champva = next(row for row in battery_rows if row["leg_id"] == champva_leg)
    champva_ci = champva_ratio_bootstrap(
        baseline_measurement,
        candidate_measurement,
        baseline_ratio_receipt=float(base_champva["baseline"]["ratio"]),
        candidate_ratio_receipt=float(base_champva["candidate"]["ratio"]),
    )
    return build_verdict(
        baseline=baseline,
        candidate=candidate,
        oos_rows=oos_rows,
        battery_rows=battery_rows,
        battery_counts=battery_counts,
        participation_rows=participation_rows,
        champva_ci=champva_ci,
        family_specs=specs,
    )


def _number(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value)


def render_markdown(payload: Mapping[str, object]) -> str:
    """Render the committed short report from the machine verdict."""

    if not payload.get("measurement_complete", True):
        failure = payload["clauses"]["measurement_integrity"]
        baseline = payload["artifacts"]["baseline"]
        candidate = payload["artifacts"]["candidate"]
        implementation = payload["gate_implementation"]
        return "\n".join(
            [
                "# Phase P predictor-sets acceptance gate",
                "",
                "## Verdict",
                "",
                "**FAIL**",
                "",
                "Failing clause: `measurement_integrity`.",
                "",
                f"Error: `{failure['error_type']}: {failure['error']}`.",
                "",
                f"Context: `{json.dumps(failure['context'], sort_keys=True)}`.",
                "",
                f"Baseline artifact: `{baseline['artifact_dir']}`.",
                "",
                f"Candidate artifact: `{candidate['artifact_dir']}`.",
                "",
                f"Gate implementation: `{implementation['path']}` "
                f"(SHA-256 `{implementation['sha256']}`).",
                "",
                "Clauses a-c were not evaluated because the declared OOS sweep "
                "did not complete. This gate fails closed; no tuning was attempted.",
                "",
            ]
        )

    artifacts = payload["artifacts"]
    baseline = artifacts["baseline"]
    candidate = artifacts["candidate"]
    clauses = payload["clauses"]
    lines = [
        "# Phase P predictor-sets acceptance gate",
        "",
        "## Verdict",
        "",
        f"**{payload['verdict']}**",
        "",
        f"Failing clauses: `{', '.join(payload['failing_clauses']) or 'none'}`.",
        "",
        "| Clause | Status | Receipt |",
        "|---|---:|---|",
    ]
    for name, clause in clauses.items():
        lines.append(
            f"| `{name}` | {'PASS' if clause['passed'] else 'FAIL'} | "
            f"`{baseline['gates_json']}`; `{candidate['gates_json']}`; "
            f"`{baseline['simulated_checkpoint_h5']}`; "
            f"`{candidate['simulated_checkpoint_h5']}` |"
        )
    lines.extend(
        [
            "",
            "The rule is machine-decidable in the adjacent verdict JSON: PASS "
            "iff clauses a, b, and c all pass.",
            "",
            "## Artifact receipts",
            "",
            "| Arm | Gates JSON | Simulated checkpoint | Stacked identity |",
            "|---|---|---|---|",
            f"| baseline | `{baseline['gates_json']}` | "
            f"`{baseline['simulated_checkpoint_h5']}` | "
            f"`{baseline['stacked_identity']}` |",
            f"| candidate | `{candidate['gates_json']}` | "
            f"`{candidate['simulated_checkpoint_h5']}` | "
            f"`{candidate['stacked_identity']}` |",
            "",
            "## Per-target OOS pinball loss",
            "",
            "| Family | Target | Money | Baseline | Candidate | Delta | 95% CI | "
            "Train B/C | Holdout B/C | Sources |",
            "|---|---|---:|---:|---:|---:|---|---:|---:|---|",
        ]
    )
    for row in payload["oos_pinball_loss"]:
        paired = row["paired"]
        ci = paired["candidate_minus_baseline_ci"]
        lines.append(
            f"| `{row['family_id']}` | `{row['target']}` | "
            f"{'yes' if row['is_money_amount'] else 'no'} | "
            f"{_number(paired['baseline_mean_pinball_loss'])} | "
            f"{_number(paired['candidate_mean_pinball_loss'])} | "
            f"{_number(paired['candidate_minus_baseline'])} | "
            f"[{_number(ci[0])}, {_number(ci[1])}] | "
            f"{row['baseline']['training_rows']}/{row['candidate']['training_rows']} | "
            f"{row['baseline']['holdout_rows']}/{row['candidate']['holdout_rows']} | "
            f"`{baseline['simulated_checkpoint_h5']}`; "
            f"`{candidate['simulated_checkpoint_h5']}` |"
        )
    battery = payload["by_origin_battery"]
    counts = battery["counts"]
    lines.extend(
        [
            "",
            "## By-origin battery leg delta",
            "",
            f"Entered band: {counts['entered_band']}; left band: "
            f"{counts['left_band']}; unchanged: {counts['unchanged']} "
            f"(in band: "
            f"{counts['unchanged_in_band']}; unchanged out of band: "
            f"{counts['unchanged_out_of_band']}; not ratio-comparable: "
            f"{counts['unchanged_not_ratio_comparable']}). Sources: "
            f"`{baseline['gates_json']}`; `{candidate['gates_json']}`.",
            "",
            "| Leg | Metric | Baseline gate/receipt/band | Baseline ratio | "
            "Baseline distance | Candidate gate/receipt/band | Candidate ratio | "
            "Candidate distance | Band transition | Sources |",
            "|---|---|---|---:|---:|---|---:|---:|---|---|",
        ]
    )
    for row in battery["legs"]:
        baseline_distance = (
            row["baseline"]["quantile_envelope_distance"]
            if row["baseline"]["quantile_envelope_distance"] is not None
            else row["baseline"]["total_variation_distance"]
        )
        candidate_distance = (
            row["candidate"]["quantile_envelope_distance"]
            if row["candidate"]["quantile_envelope_distance"] is not None
            else row["candidate"]["total_variation_distance"]
        )
        lines.append(
            f"| `{row['leg_id']}` | {row['metric']} | "
            f"{row['baseline']['gate_status']} / "
            f"{row['baseline']['raw_status']} / "
            f"{row['baseline']['band_status']} | "
            f"{_number(row['baseline']['ratio'])} | "
            f"{_number(baseline_distance)} | "
            f"{row['candidate']['gate_status']} / "
            f"{row['candidate']['raw_status']} / "
            f"{row['candidate']['band_status']} | "
            f"{_number(row['candidate']['ratio'])} | "
            f"{_number(candidate_distance)} | {row['transition']} | "
            f"`{baseline['gates_json']}`; `{candidate['gates_json']}` |"
        )
    lines.extend(
        [
            "",
            "## Participation incidence",
            "",
            "| Target leg | Baseline ASEC | Baseline ACS | Baseline ratio | "
            "Candidate ASEC | Candidate ACS | Candidate ratio | Sources |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in payload["participation_incidence"]:
        base = row["baseline"]
        cand = row["candidate"]
        lines.append(
            f"| `{row['leg_id']}` | {_number(base['asec_incidence'])} | "
            f"{_number(base['acs_incidence'])} | "
            f"{_number(base['incidence_ratio_acs_over_asec'])} | "
            f"{_number(cand['asec_incidence'])} | "
            f"{_number(cand['acs_incidence'])} | "
            f"{_number(cand['incidence_ratio_acs_over_asec'])} | "
            f"`{baseline['gates_json']}`; `{candidate['gates_json']}` |"
        )
    lines.extend(
        [
            "",
            "## Configuration",
            "",
            f"Source: `{payload['gate_implementation']['path']}` "
            f"(SHA-256 `{payload['gate_implementation']['sha256']}`).",
            "",
            "```json",
            json.dumps(payload["config"], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--markdown-output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = run_gate(args.baseline, args.candidate)
    except Exception as error:
        payload = measurement_failure_verdict(
            baseline_path=args.baseline,
            candidate_path=args.candidate,
            error=error,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    if args.markdown_output is not None:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(payload))
    print(
        _canonical_json(
            {
                "verdict": payload["verdict"],
                "failing_clauses": payload["failing_clauses"],
                "output": str(args.output.resolve()),
                "markdown_output": (
                    None
                    if args.markdown_output is None
                    else str(args.markdown_output.resolve())
                ),
            }
        ),
        flush=True,
    )
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
