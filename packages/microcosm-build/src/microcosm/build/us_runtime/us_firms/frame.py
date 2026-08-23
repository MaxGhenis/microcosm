"""Observed US plan-sponsor firm table calibrated to SUSB margins.

Form 5500 sponsor EINs define the donor table.  OSHA establishments never join
that population; :func:`osha_measurement_reference` scores their independent
measurement after an explicit OSHA quality rule.  Calibration cells are
private SUSB build support, not the dynamics IC2 wire band.  The published
table carries raw participant counts and lets dynamics band them at its seam.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from microcosm.build.us_runtime.us_firms.diagnostics import (
    margin_ratio,
    weight_diagnostics,
)
from microcosm.build.us_runtime.us_firms.staging import (
    VerifiedUSFirmStaging,
    verify_staged_sources,
)
from microcosm.build.us_runtime.us_firms.targets import (
    CALIBRATION_BANDS,
    CALIBRATION_TARGET_COLUMNS,
    USFirmTargets,
    calibration_band_for_employment,
    calibration_sector_for_naics,
)
from microcosm.calibrate import calibrate_bounded_moment

__all__ = [
    "DEFAULT_WEIGHT_BOUNDS",
    "FIRM_TABLE_COLUMNS",
    "USFirmBuildConfig",
    "USFirmBuildResult",
    "USFirmCoverageError",
    "SyntheticUSFirmSourceReceipt",
    "build_us_firm_frame",
    "osha_measurement_reference",
    "synthetic_us_firm_source_receipt",
    "validate_us_firm_table",
]

CELL_KEYS = ("calibration_sector", "calibration_band")
DEFAULT_WEIGHT_BOUNDS = (0.1, 140.0)

_SPONSOR_COLUMNS = (
    "sponsor_ein",
    "active_participants_eoy",
    "naics_code",
    "naics_sector",
    "state",
    "plan_entity_code",
    "plan_entity_code_system",
    "plan_entity_type",
    "plan_entity_strata",
    "plan_entity_types",
    "plan_entity_code_conflict",
    "plan_entity_type_conflict",
    "naics_codes",
    "naics_code_conflict",
    "source_form",
    "source_forms",
    "source_year",
    "source_filename",
    "filings",
    "observation_unit",
    "employment_measure",
    "participant_timing",
    "employment_measure_source_field",
    "employment_is_lower_bound",
    "active_participants_boy",
    "total_participants_boy",
)

FIRM_TABLE_COLUMNS = (
    "firm_id",
    "source_firm_id",
    "source_firm_key",
    "firm_weight",
    "employment",
    "employment_in_scope",
    "naics_code",
    "naics_sector",
    "calibration_sector",
    "state",
    "plan_entity_code",
    "plan_entity_code_system",
    "plan_entity_type",
    "plan_entity_strata",
    "plan_entity_types",
    "plan_entity_code_conflict",
    "plan_entity_type_conflict",
    "naics_codes",
    "naics_code_conflict",
    "source_form",
    "source_forms",
    "source_year",
    "source_filename",
    "filings",
    "observation_unit",
    "employment_measure",
    "participant_timing",
    "employment_measure_source_field",
    "employment_is_lower_bound",
    "active_participants_boy",
    "total_participants_boy",
    "calibration_status",
    "source_dataset",
    "source_manifest_sha256",
    "target_source_mode",
    "target_identity_sha256",
)


@dataclass(frozen=True)
class USFirmBuildConfig:
    """Method choices that become part of every artifact's identity."""

    source_year: int = 2023
    weight_bounds: tuple[float, float] = DEFAULT_WEIGHT_BOUNDS
    max_bound_iterations: int = 20
    require_full_coverage: bool = True
    employment_out_of_scope_sectors: tuple[str, ...] = ("55",)
    firm_only_fallback_for_infeasible_support: bool = True
    calibration_method: str = "bounded_exponential_count_and_moment_tilt"

    def __post_init__(self) -> None:
        if (
            isinstance(self.source_year, bool)
            or not isinstance(self.source_year, int)
            or self.source_year < 1900
        ):
            raise ValueError("source_year must be a valid integer year")
        lower, upper = self.weight_bounds
        if (
            not math.isfinite(lower)
            or not math.isfinite(upper)
            or lower <= 0.0
            or upper < lower
        ):
            raise ValueError("weight_bounds must be finite positive lower/upper")
        if self.max_bound_iterations < 1:
            raise ValueError("max_bound_iterations must be at least one")
        if not isinstance(self.require_full_coverage, bool):
            raise ValueError("require_full_coverage must be boolean")
        if not self.firm_only_fallback_for_infeasible_support:
            raise ValueError(
                "The observed-frame contract requires firm-only fallback for "
                "employment-infeasible support; disabling it would erase a "
                "published firm margin."
            )
        if tuple(self.employment_out_of_scope_sectors) != ("55",):
            raise ValueError(
                "The current US firm contract requires NAICS 55 as the sole "
                "whole-sector employment exclusion."
            )
        if (
            self.calibration_method
            != "bounded_exponential_count_and_moment_tilt"
        ):
            raise ValueError(
                "calibration_method is an attested implementation identity, "
                "not a caller-selected label"
            )


@dataclass(frozen=True)
class USFirmBuildResult:
    """Firm table and its hash-ready build evidence."""

    firms: pd.DataFrame
    coverage: pd.DataFrame
    diagnostics: Mapping[str, object]
    config: USFirmBuildConfig


@dataclass(frozen=True)
class SyntheticUSFirmSourceReceipt:
    """Explicit source identity admitted only for secrets-free fixtures."""

    fixture_name: str
    donor_content_sha256: str

    def __post_init__(self) -> None:
        if not self.fixture_name.strip():
            raise ValueError("fixture_name must be non-empty")
        _require_sha256(
            self.donor_content_sha256,
            label="donor_content_sha256",
        )


def synthetic_us_firm_source_receipt(
    sponsors: pd.DataFrame,
    *,
    fixture_name: str,
) -> SyntheticUSFirmSourceReceipt:
    """Hash a synthetic donor fixture without impersonating verified staging."""

    return SyntheticUSFirmSourceReceipt(
        fixture_name=fixture_name,
        donor_content_sha256=_dataframe_content_sha256(sponsors),
    )


class USFirmCoverageError(ValueError):
    """A target grid has cells that no observed donor can populate."""

    def __init__(self, coverage: pd.DataFrame) -> None:
        uncovered = coverage.loc[
            coverage["observed_records"].eq(0),
            ["calibration_sector", "calibration_band"],
        ]
        labels = [f"{row.calibration_sector}/{row.calibration_band}" for row in uncovered.itertuples()]
        super().__init__(
            f"{len(labels)} SUSB target cell(s) have no Form 5500 sponsor "
            f"support: {', '.join(labels)}"
        )
        self.coverage = coverage.copy()


def build_us_firm_frame(
    sponsors: pd.DataFrame,
    targets: USFirmTargets,
    *,
    source_provenance: VerifiedUSFirmStaging | SyntheticUSFirmSourceReceipt,
    config: USFirmBuildConfig | None = None,
    bds_validation: pd.DataFrame | None = None,
    osha_reference: Mapping[str, object] | None = None,
) -> USFirmBuildResult:
    """Build a deterministic firm-entity table from observed plan sponsors."""
    cfg = config or USFirmBuildConfig()
    _validate_sponsors(sponsors, cfg)
    target_cells = _validate_targets(targets, cfg)
    sponsor_attrs = _plain_mapping(sponsors.attrs)
    target_receipt = _plain_mapping(targets.provenance)
    osha_receipt = (
        _plain_mapping(osha_reference) if osha_reference is not None else None
    )
    bds_provenance = (
        _plain_mapping(bds_validation.attrs)
        if bds_validation is not None
        else None
    )

    donor_hash = _dataframe_content_sha256(sponsors)
    source_receipt = _source_receipt(source_provenance, donor_hash)
    manifest_sha = str(source_receipt["manifest_sha256"])
    target_hash = _dataframe_content_sha256(target_cells)
    detail_hash = (
        _dataframe_content_sha256(targets.detail_cells)
        if targets.detail_cells is not None
        else None
    )
    bds_hash = (
        _dataframe_content_sha256(bds_validation)
        if bds_validation is not None
        else None
    )
    transformations = _transformation_register(cfg)

    working = sponsors.copy()
    source_rows = len(working)
    missing_naics = working["naics_code"].isna()
    working = working.loc[~missing_naics].copy()
    working["employment"] = working["active_participants_eoy"].astype("int64")
    working["calibration_sector"] = working["naics_code"].map(
        calibration_sector_for_naics
    )
    working["calibration_band"] = working["employment"].map(
        calibration_band_for_employment
    )

    target_keys = set(
        zip(
            target_cells["calibration_sector"],
            target_cells["calibration_band"],
            strict=True,
        )
    )
    donor_keys = pd.Series(
        list(
            zip(
                working["calibration_sector"],
                working["calibration_band"],
                strict=True,
            )
        ),
        index=working.index,
        dtype="object",
    )
    unmatched = ~donor_keys.isin(target_keys)
    unmatched_count = int(unmatched.sum())
    unmatched_donor_cells = (
        working.loc[unmatched]
        .groupby(list(CELL_KEYS), as_index=False)
        .agg(
            observed_records=("sponsor_ein", "size"),
            observed_employment_sum=("employment", "sum"),
        )
        .sort_values(list(CELL_KEYS), kind="mergesort")
        .reset_index(drop=True)
    )
    working = working.loc[~unmatched].copy()
    working = working.sort_values("sponsor_ein", kind="mergesort").reset_index(
        drop=True
    )

    precoverage = _precalibration_coverage(working, target_cells)
    if cfg.require_full_coverage and precoverage["observed_records"].eq(0).any():
        raise USFirmCoverageError(precoverage)

    weights = np.zeros(len(working), dtype=np.float64)
    employment_scope = np.zeros(len(working), dtype=bool)
    statuses = np.full(len(working), "unassigned", dtype=object)
    coverage_rows: list[dict[str, object]] = []
    groups = working.groupby(list(CELL_KEYS), sort=False).groups
    for target in target_cells.itertuples(index=False):
        key = (target.calibration_sector, target.calibration_band)
        positions = np.asarray(groups.get(key, []), dtype=np.int64)
        values = working.loc[positions, "employment"].to_numpy(dtype=np.float64)
        target_firms = float(target.firms)
        target_employment = float(target.employment)
        declared_scope = bool(target.employment_in_scope)
        reason: str | None = None
        receipt_payload: dict[str, object]

        if positions.size == 0:
            cell_weights = np.asarray([], dtype=np.float64)
            status = "uncovered_target_cell"
            actual_scope = False
            reason = "No Form 5500 sponsor occupies the target cell."
            receipt_payload = {
                "status": "uncovered",
                "reason": reason,
                "iterations": 0,
                "clipped_low": 0,
                "clipped_high": 0,
            }
        elif not declared_scope:
            cell_weights = _flat_firm_margin_weights(
                positions.size,
                target_firms,
                cfg.weight_bounds,
            )
            status = "firm_only_declared_employment_exclusion"
            actual_scope = False
            reason = (
                f"NAICS {target.calibration_sector} employment is excluded "
                "before calibration; only the firm-count margin is attempted."
            )
            receipt_payload = {
                "status": "declared_employment_exclusion",
                "reason": reason,
                "iterations": 0,
                "clipped_low": int(
                    np.count_nonzero(
                        np.isclose(
                            cell_weights,
                            cfg.weight_bounds[0],
                            rtol=0.0,
                            atol=1e-12,
                        )
                    )
                ),
                "clipped_high": int(
                    np.count_nonzero(
                        np.isclose(
                            cell_weights,
                            cfg.weight_bounds[1],
                            rtol=0.0,
                            atol=1e-12,
                        )
                    )
                ),
            }
        else:
            receipt = calibrate_bounded_moment(
                values,
                target_count=target_firms,
                target_total=target_employment,
                weight_bounds=cfg.weight_bounds,
                max_bound_iterations=cfg.max_bound_iterations,
            )
            receipt_payload = {
                "status": receipt.status,
                "reason": receipt.reason,
                "iterations": receipt.iterations,
                "clipped_low": receipt.clipped_low,
                "clipped_high": receipt.clipped_high,
                "target_mean": receipt.target_mean,
                "observed_min": receipt.observed_min,
                "observed_max": receipt.observed_max,
                "count_residual": receipt.count_residual,
                "employment_residual": receipt.total_residual,
                "exact_after_bounds": receipt.exact,
            }
            if receipt.weights is None:
                cell_weights = _flat_firm_margin_weights(
                    positions.size,
                    target_firms,
                    cfg.weight_bounds,
                )
                status = "firm_only_infeasible_employment_support"
                actual_scope = False
                reason = receipt.reason
            else:
                cell_weights = receipt.weights
                actual_scope = True
                if receipt.exact:
                    status = "dual_margin_calibrated"
                else:
                    status = "dual_margin_bounded_residual"
                    reason = (
                        "The absolute weight bounds bind; the returned weights "
                        "stay within the declared interval and both resulting "
                        "margin residuals are published."
                    )

        if positions.size:
            weights[positions] = cell_weights
            employment_scope[positions] = actual_scope
            statuses[positions] = status
        estimated_firms = float(cell_weights.sum())
        estimated_employment = (
            float(cell_weights @ values) if positions.size else 0.0
        )
        cell_weight_diagnostics = weight_diagnostics(
            cell_weights,
            employment=values,
            bounds=cfg.weight_bounds,
        )
        coverage_rows.append(
            {
                "calibration_sector": target.calibration_sector,
                "calibration_band": target.calibration_band,
                "observed_records": int(positions.size),
                "observed_employment_sum": (
                    int(values.sum()) if positions.size else 0
                ),
                "observed_employment_min": (
                    int(values.min()) if positions.size else None
                ),
                "observed_employment_max": (
                    int(values.max()) if positions.size else None
                ),
                "target_firms": target_firms,
                "estimated_firms": estimated_firms,
                "firm_margin_residual": estimated_firms - target_firms,
                "firm_margin_ratio": margin_ratio(estimated_firms, target_firms),
                "target_employment": target_employment,
                "estimated_employment": estimated_employment,
                "employment_margin_residual": (
                    estimated_employment - target_employment
                ),
                "employment_margin_ratio": margin_ratio(
                    estimated_employment, target_employment
                ),
                "declared_employment_in_scope": declared_scope,
                "employment_constraint_in_scope": actual_scope,
                "calibration_status": status,
                "calibration_reason": reason,
                "solver_receipt": receipt_payload,
                "weight_diagnostics": cell_weight_diagnostics,
            }
        )

    working["firm_weight"] = weights
    working["employment_in_scope"] = employment_scope
    working["calibration_status"] = statuses
    coverage = pd.DataFrame(coverage_rows)

    fine_attempt = _fine_detail_attempt(working, targets.detail_cells)
    firm_only_attempt = _firm_only_attempt(working, target_cells)
    bds_receipt = _bds_holdout(working, coverage, bds_validation)
    scope_rows = working["employment_in_scope"]
    scoped_target_employment = float(
        coverage.loc[
            coverage["employment_constraint_in_scope"], "target_employment"
        ].sum()
    )
    scoped_estimated_employment = float(
        (
            working.loc[scope_rows, "firm_weight"]
            * working.loc[scope_rows, "employment"]
        ).sum()
    )
    total_target_firms = float(coverage["target_firms"].sum())
    total_estimated_firms = float(working["firm_weight"].sum())
    global_weights = weight_diagnostics(
        working["firm_weight"],
        employment=working["employment"],
        bounds=cfg.weight_bounds,
    )

    target_identity = target_hash
    firms = _assemble_firm_table(
        working,
        cfg,
        source_manifest_sha256=manifest_sha,
        target_source_mode=targets.source_mode,
        target_identity_sha256=target_identity,
    )
    validate_us_firm_table(firms, cfg)

    identity_payload = {
        "config": asdict(cfg),
        "donor_content_sha256": donor_hash,
        "target_content_sha256": target_hash,
        "target_detail_content_sha256": detail_hash,
        "bds_content_sha256": bds_hash,
        "source_provenance": source_receipt,
        "source_reader_receipts": sponsor_attrs,
        "target_provenance": target_receipt,
        "bds_provenance": bds_provenance,
        "osha_reference": osha_receipt,
        "transformations": transformations,
    }
    build_identity_sha256 = hashlib.sha256(
        _canonical_json(identity_payload)
    ).hexdigest()
    diagnostics: dict[str, object] = {
        "schema_version": "microcosm.us_firms.diagnostics.v1",
        "artifact": "populace-us-firms",
        "build_identity_sha256": build_identity_sha256,
        "input_content": {
            "donors_sha256": donor_hash,
            "targets_sha256": target_hash,
            "target_detail_sha256": detail_hash,
            "bds_sha256": bds_hash,
        },
        "source_provenance": source_receipt,
        "target_provenance": target_receipt,
        "source_reader_receipts": sponsor_attrs,
        "transformations": transformations,
        "filters": {
            "source_sponsors": int(source_rows),
            "missing_or_invalid_full_naics_dropped": int(missing_naics.sum()),
            "unmatched_susb_calibration_cell_dropped": unmatched_count,
            "firm_rows_out": int(len(firms)),
        },
        "unmatched_donor_cells_dropped": _records(unmatched_donor_cells),
        "target_grid": _target_grid_receipt(target_cells),
        "coverage_table": _records(coverage),
        "weight_distribution": global_weights,
        "margins": {
            "firm": {
                "target": total_target_firms,
                "estimate": total_estimated_firms,
                "ratio": margin_ratio(total_estimated_firms, total_target_firms),
            },
            "employment_in_scope": {
                "target": scoped_target_employment,
                "estimate": scoped_estimated_employment,
                "ratio": margin_ratio(
                    scoped_estimated_employment,
                    scoped_target_employment,
                ),
            },
            "by_calibration_band": _aggregate_coverage(
                coverage, "calibration_band"
            ),
            "by_calibration_sector": _aggregate_coverage(
                coverage, "calibration_sector"
            ),
        },
        "recorded_attempts": [firm_only_attempt, fine_attempt],
        "bds_national_heldout": bds_receipt,
        "osha_independent_measurement_reference": (
            osha_receipt
            if osha_receipt is not None
            else {
                "status": "not_run",
                "reason": "No explicitly capped OSHA reference was supplied.",
            }
        ),
        "legacy_claim_comparison": _legacy_claim_comparison(
            coverage,
            working,
            cfg,
            osha_reference,
        ),
        "open_contracts": {
            "observation_unit": "plan_sponsor_ein_not_reconciled_to_susb_enterprise",
            "single_employer_filter": "not_applied_plan_entity_strata_preserved",
            "participant_to_employment_relation": (
                "not_ordered_across_retained_plan_entity_strata"
            ),
            "susb_sector_firm_counts": (
                "non_additive_for_multi_industry_enterprises"
            ),
        },
    }
    return USFirmBuildResult(
        firms=firms,
        coverage=coverage,
        diagnostics=diagnostics,
        config=cfg,
    )


def osha_measurement_reference(
    sponsors: pd.DataFrame,
    establishments: pd.DataFrame,
) -> dict[str, object]:
    """Compare Form sponsor and explicitly cleaned OSHA EIN measurements."""
    quality = establishments.attrs.get("quality_rule")
    if not isinstance(quality, Mapping) or "max_employees" not in quality:
        raise ValueError(
            "OSHA reference requires apply_quality_rule() with an explicit cap."
        )
    sponsor_required = {"sponsor_ein", "active_participants_eoy"}
    establishment_required = {
        "record_id",
        "establishment_id",
        "ein",
        "annual_average_employees",
    }
    if missing := sorted(sponsor_required - set(sponsors.columns)):
        raise ValueError(f"Sponsors lack OSHA comparison columns {missing}.")
    if missing := sorted(establishment_required - set(establishments.columns)):
        raise ValueError(f"OSHA reference lacks columns {missing}.")
    if sponsors["sponsor_ein"].duplicated().any():
        raise ValueError("OSHA comparison requires unique Form sponsor EINs.")
    left = sponsors[["sponsor_ein", "active_participants_eoy"]].copy()
    left = left.dropna().drop_duplicates("sponsor_ein").set_index("sponsor_ein")
    retained = establishments.dropna(subset=["ein"])
    aggregation_receipt = {
        "rule": "sum_all_quality_retained_submissions_by_ein_without_deduplication",
        "rows_in": int(len(establishments)),
        "missing_ein_dropped": int(establishments["ein"].isna().sum()),
        "rows_aggregated": int(len(retained)),
        "distinct_eins": int(retained["ein"].nunique()),
        "distinct_establishment_ids": int(
            retained["establishment_id"].nunique()
        ),
        "duplicate_record_ids": int(retained["record_id"].duplicated().sum()),
        "repeated_establishment_ids": int(
            retained["establishment_id"].duplicated().sum()
        ),
        "deduplication_applied": False,
    }
    form_measurement = _plain_mapping(
        sponsors.attrs.get("measurement_model", {})
    )
    osha_measurement = _plain_mapping(
        establishments.attrs.get("measurement_model", {})
    )
    measurement_warning = (
        "Form values are sponsor plan participants; OSHA values are sums "
        "of retained establishment submissions. Agreement does not reconcile "
        "either unit to a SUSB legal enterprise."
    )
    right = (
        retained
        .groupby("ein", sort=True)["annual_average_employees"]
        .sum()
        .rename("osha_establishment_employment_sum")
    )
    joined = left.join(right, how="inner")
    if joined.empty:
        return {
            "status": "computed",
            "matched_eins": 0,
            "agreement_rate": None,
            "median_form_to_osha_ratio": None,
            "confusion": {},
            "osha_quality_rule": _plain_mapping(quality),
            "osha_aggregation": aggregation_receipt,
            "form_measurement_model": form_measurement,
            "osha_measurement_model": osha_measurement,
            "measurement_warning": measurement_warning,
        }
    joined["form_calibration_band"] = joined["active_participants_eoy"].map(
        calibration_band_for_employment
    )
    joined["osha_calibration_band"] = joined[
        "osha_establishment_employment_sum"
    ].map(calibration_band_for_employment)
    agreement = joined["form_calibration_band"].eq(
        joined["osha_calibration_band"]
    )
    ratios = joined["active_participants_eoy"] / joined[
        "osha_establishment_employment_sum"
    ]
    cross = pd.crosstab(
        joined["form_calibration_band"], joined["osha_calibration_band"]
    ).reindex(index=CALIBRATION_BANDS, columns=CALIBRATION_BANDS, fill_value=0)
    return {
        "status": "computed",
        "unit": "EIN_join_of_plan_sponsor_to_sum_of_retained_establishments",
        "band_vocabulary": "private_build_time_calibration_cells_not_ic2_wire",
        "matched_eins": int(len(joined)),
        "agreement_rate": float(agreement.mean()),
        "median_form_to_osha_ratio": float(ratios.median()),
        "confusion": {
            str(index): {str(column): int(cross.loc[index, column]) for column in cross.columns}
            for index in cross.index
        },
        "osha_quality_rule": _plain_mapping(quality),
        "osha_aggregation": aggregation_receipt,
        "form_measurement_model": form_measurement,
        "osha_measurement_model": osha_measurement,
        "measurement_warning": measurement_warning,
    }


def validate_us_firm_table(
    firms: pd.DataFrame,
    config: USFirmBuildConfig | None = None,
) -> None:
    """Validate the standalone table against Microcosm's firm conventions."""
    cfg = config or USFirmBuildConfig()
    if tuple(firms.columns) != FIRM_TABLE_COLUMNS:
        raise ValueError(
            "US firm table columns differ from the contract: "
            f"{list(firms.columns)}"
        )
    if firms.empty:
        raise ValueError("US firm table must contain at least one firm")
    if firms["firm_id"].tolist() != list(range(1, len(firms) + 1)):
        raise ValueError("firm_id must be stable, sorted, and contiguous from one")
    if not firms["firm_id"].is_unique or not firms["source_firm_key"].is_unique:
        raise ValueError("US firm identifiers must be unique")
    if not firms["source_firm_id"].astype(str).str.fullmatch(r"\d{9}").all():
        raise ValueError("source_firm_id must preserve a nine-digit sponsor EIN")
    weights = firms["firm_weight"].to_numpy(dtype=np.float64)
    if not np.isfinite(weights).all() or (weights <= 0.0).any():
        raise ValueError("firm_weight must be finite and positive")
    if (weights < cfg.weight_bounds[0]).any() or (
        weights > cfg.weight_bounds[1]
    ).any():
        raise ValueError("firm_weight violates the declared absolute bounds")
    employment = firms["employment"].to_numpy(dtype=np.float64)
    if (
        not np.isfinite(employment).all()
        or (employment < 1).any()
        or not np.equal(employment, np.floor(employment)).all()
    ):
        raise ValueError("employment must contain positive raw integer counts")
    if not firms["naics_code"].astype(str).str.fullmatch(r"\d{6}").all():
        raise ValueError("naics_code must preserve full six-digit codes")
    if not firms["employment_in_scope"].isin([True, False]).all():
        raise ValueError("employment_in_scope must be boolean")


def _validate_sponsors(sponsors: pd.DataFrame, config: USFirmBuildConfig) -> None:
    missing = sorted(set(_SPONSOR_COLUMNS) - set(sponsors.columns))
    if missing:
        raise ValueError(f"Form 5500 sponsors lack required columns {missing}.")
    if sponsors.empty:
        raise ValueError("US firm build requires at least one Form 5500 sponsor")
    if sponsors["sponsor_ein"].duplicated().any():
        raise ValueError("Form 5500 sponsors must be unique by sponsor_ein")
    valid_ein = sponsors["sponsor_ein"].astype("string").str.fullmatch(r"\d{9}")
    if not valid_ein.fillna(False).all():
        raise ValueError("Form 5500 sponsor_ein must be a nine-digit identifier")
    employment = pd.to_numeric(
        sponsors["active_participants_eoy"], errors="coerce"
    )
    if (
        employment.isna().any()
        or not np.isfinite(employment).all()
        or (employment < 1).any()
        or (employment != np.floor(employment)).any()
    ):
        raise ValueError(
            "Form 5500 active_participants_eoy must be positive integer counts"
        )
    years = pd.to_numeric(sponsors["source_year"], errors="coerce")
    if years.isna().any() or not years.eq(config.source_year).all():
        raise ValueError(
            f"Form 5500 source_year must equal configured {config.source_year}"
        )
    naics = sponsors["naics_code"].astype("string")
    valid_naics = naics.isna() | naics.str.fullmatch(r"\d{6}").fillna(False)
    if not valid_naics.all():
        raise ValueError("Form 5500 naics_code must be missing or six digits")
    declared_sector = sponsors["naics_sector"].astype("string")
    expected_sector = naics.str[:2]
    sector_matches = (
        (naics.isna() & declared_sector.isna())
        | (naics.notna() & declared_sector.eq(expected_sector))
    )
    if not sector_matches.fillna(False).all():
        raise ValueError("Form 5500 naics_sector must match full naics_code")
    expected_constants: dict[str, object] = {
        "observation_unit": "plan_sponsor_ein",
        "employment_measure": "active_plan_participants",
        "participant_timing": "end_of_year",
        "employment_is_lower_bound": False,
    }
    for column, expected in expected_constants.items():
        if not sponsors[column].eq(expected).all():
            raise ValueError(
                f"Form 5500 {column} must be consistently {expected!r}"
            )
    expected_fields = sponsors["source_form"].map(
        {
            "5500": "TOT_ACTIVE_PARTCP_CNT",
            "5500-SF": "SF_TOT_ACT_PARTCP_EOY_CNT",
        }
    )
    if expected_fields.isna().any() or not sponsors[
        "employment_measure_source_field"
    ].eq(expected_fields).all():
        raise ValueError(
            "Form 5500 source form and EOY participant field disagree"
        )
    expected_code_system = sponsors["source_form"].map(
        {
            "5500": "form_5500_type_plan_entity_cd",
            "5500-SF": "form_5500_sf_type_plan_entity_cd",
        }
    )
    if not sponsors["plan_entity_code_system"].eq(expected_code_system).all():
        raise ValueError(
            "Form 5500 source form and plan entity code system disagree"
        )
    measurement_model = sponsors.attrs.get("measurement_model")
    aggregation = sponsors.attrs.get("aggregation")
    if not isinstance(measurement_model, Mapping) or not isinstance(
        aggregation, Mapping
    ):
        raise ValueError(
            "Form 5500 sponsors must retain reader measurement and aggregation receipts"
        )
    if (
        measurement_model.get("observation_unit") != "plan_sponsor_ein"
        or measurement_model.get("participant_timing") != "end_of_year"
        or aggregation.get("single_employer_filter_applied") is not False
    ):
        raise ValueError("Form 5500 reader receipts contradict the frame contract")


def _validate_targets(
    targets: USFirmTargets,
    config: USFirmBuildConfig,
) -> pd.DataFrame:
    if not isinstance(targets, USFirmTargets):
        raise TypeError("targets must be a USFirmTargets receipt")
    cells = targets.calibration_cells.copy()
    if tuple(cells.columns) != CALIBRATION_TARGET_COLUMNS:
        raise ValueError("US firm target columns differ from the target contract")
    if cells.empty or cells.duplicated(list(CELL_KEYS)).any():
        raise ValueError("US firm targets must contain unique positive cells")
    if not set(cells["calibration_band"]).issubset(CALIBRATION_BANDS):
        raise ValueError("US firm targets contain unknown calibration bands")
    for column in ("firms", "employment"):
        values = pd.to_numeric(cells[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values).all():
            raise ValueError(f"US firm target {column} must be finite")
        if (values < 0).any() or (values != np.floor(values)).any():
            raise ValueError(f"US firm target {column} must be non-negative integer")
        cells[column] = values.astype("int64")
    if (cells["firms"] <= 0).any():
        raise ValueError("US firm calibration cells must have positive firm counts")
    if not cells["employment_in_scope"].isin([True, False]).all():
        raise ValueError("US firm target employment_in_scope must be boolean")
    expected_scope = ~cells["calibration_sector"].isin(
        config.employment_out_of_scope_sectors
    )
    if not cells["employment_in_scope"].eq(expected_scope).all():
        raise ValueError(
            "US firm target employment scope differs from build configuration"
        )
    cells["_sector_order"] = cells["calibration_sector"].str[:2].astype(int)
    cells["_band_order"] = cells["calibration_band"].map(
        {band: index for index, band in enumerate(CALIBRATION_BANDS)}
    )
    return (
        cells.sort_values(["_sector_order", "_band_order"], kind="mergesort")
        .drop(columns=["_sector_order", "_band_order"])
        .reset_index(drop=True)
    )


def _precalibration_coverage(
    working: pd.DataFrame,
    targets: pd.DataFrame,
) -> pd.DataFrame:
    observed = (
        working.groupby(list(CELL_KEYS), as_index=False)
        .agg(
            observed_records=("sponsor_ein", "size"),
            observed_employment_sum=("employment", "sum"),
            observed_employment_min=("employment", "min"),
            observed_employment_max=("employment", "max"),
        )
    )
    coverage = targets.rename(
        columns={"firms": "target_firms", "employment": "target_employment"}
    ).merge(observed, on=list(CELL_KEYS), how="left", validate="one_to_one")
    coverage["observed_records"] = coverage["observed_records"].fillna(0).astype(int)
    coverage["observed_employment_sum"] = (
        coverage["observed_employment_sum"].fillna(0).astype(int)
    )
    return coverage


def _flat_firm_margin_weights(
    records: int,
    target_firms: float,
    bounds: tuple[float, float],
) -> np.ndarray:
    if records < 1:
        return np.asarray([], dtype=np.float64)
    return np.clip(
        np.full(records, target_firms / records, dtype=np.float64),
        *bounds,
    )


def _assemble_firm_table(
    working: pd.DataFrame,
    config: USFirmBuildConfig,
    *,
    source_manifest_sha256: str,
    target_source_mode: str,
    target_identity_sha256: str,
) -> pd.DataFrame:
    firms = working.copy()
    firms["firm_id"] = np.arange(1, len(firms) + 1, dtype=np.int64)
    firms["source_firm_id"] = firms["sponsor_ein"].astype("string")
    firms["source_firm_key"] = firms["source_firm_id"].map(
        lambda value: f"form5500:{config.source_year}:sponsor_ein:{value}"
    )
    firms["source_dataset"] = "dol_form_5500_plan_sponsors"
    firms["source_manifest_sha256"] = source_manifest_sha256
    firms["target_source_mode"] = target_source_mode
    firms["target_identity_sha256"] = target_identity_sha256
    firms["firm_weight"] = firms["firm_weight"].astype("float64")
    firms["employment"] = firms["employment"].astype("int64")
    firms["employment_in_scope"] = firms["employment_in_scope"].astype(bool)
    return firms.loc[:, list(FIRM_TABLE_COLUMNS)].reset_index(drop=True)


def _firm_only_attempt(
    working: pd.DataFrame,
    targets: pd.DataFrame,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    groups = working.groupby(list(CELL_KEYS), sort=False).groups
    for target in targets.itertuples(index=False):
        key = (target.calibration_sector, target.calibration_band)
        positions = np.asarray(groups.get(key, []), dtype=np.int64)
        values = working.loc[positions, "employment"].to_numpy(dtype=np.float64)
        cell_weights = (
            np.full(positions.size, float(target.firms) / positions.size)
            if positions.size
            else np.asarray([], dtype=np.float64)
        )
        rows.append(
            {
                "calibration_sector": target.calibration_sector,
                "calibration_band": target.calibration_band,
                "records": int(positions.size),
                "target_firms": float(target.firms),
                "estimated_firms": float(cell_weights.sum()),
                "target_employment": float(target.employment),
                "estimated_employment": (
                    float(cell_weights @ values) if positions.size else 0.0
                ),
                "employment_in_scope": bool(target.employment_in_scope),
            }
        )
    return _attempt_receipt(
        "sector_by_calibration_band_firm_only_poststratification",
        rows,
        failure=(
            "Controls firm counts only; within-cell sponsor selection leaves "
            "the employment margin uncontrolled."
        ),
        geometry={
            "sectors": int(targets["calibration_sector"].nunique()),
            "size_cells": len(CALIBRATION_BANDS),
            "published_positive_cells": int(len(targets)),
        },
    )


def _fine_detail_attempt(
    working: pd.DataFrame,
    detail: pd.DataFrame | None,
) -> dict[str, object]:
    name = "sector_by_susb_published_detail_class_firm_only_poststratification"
    if detail is None:
        return {
            "attempt": name,
            "status": "unavailable",
            "failure": (
                "Production Ledger cells carry no SUSB detail-class facts; "
                "the builder refuses to invent them."
            ),
        }
    rows: list[dict[str, object]] = []
    for target in detail.itertuples(index=False):
        lower = int(target.employment_lower_bound)
        upper = (
            None
            if pd.isna(target.employment_upper_bound)
            else int(target.employment_upper_bound)
        )
        mask = working["calibration_sector"].eq(target.calibration_sector) & working[
            "employment"
        ].ge(lower)
        if upper is not None:
            mask &= working["employment"].le(upper)
        values = working.loc[mask, "employment"].to_numpy(dtype=np.float64)
        target_firms = float(target.firms)
        cell_weights = (
            np.full(values.size, target_firms / values.size)
            if values.size and target_firms > 0.0
            else np.asarray([], dtype=np.float64)
        )
        rows.append(
            {
                "calibration_sector": target.calibration_sector,
                "calibration_band": target.calibration_band,
                "entrsize_code": str(target.entrsize_code),
                "records": int(values.size),
                "target_firms": target_firms,
                "estimated_firms": float(cell_weights.sum()),
                "target_employment": float(target.employment),
                "estimated_employment": (
                    float(cell_weights @ values) if values.size else 0.0
                ),
                "employment_in_scope": target.calibration_sector != "55",
            }
        )
    return _attempt_receipt(
        name,
        rows,
        failure=(
            "Finer firm-count strata still do not control employment, and the "
            "open-ended top SUSB class remains heterogeneous."
        ),
        geometry={
            "published_detail_rows": int(len(detail)),
            "distinct_detail_classes": int(detail["entrsize_code"].nunique()),
            "legacy_prose_claimed_detail_classes": 22,
        },
    )


def _attempt_receipt(
    name: str,
    rows: list[dict[str, object]],
    *,
    failure: str,
    geometry: Mapping[str, object],
) -> dict[str, object]:
    frame = pd.DataFrame(rows)
    target_firms = float(frame["target_firms"].sum())
    estimated_firms = float(frame["estimated_firms"].sum())
    target_employment = float(frame["target_employment"].sum())
    estimated_employment = float(frame["estimated_employment"].sum())
    scope = frame["employment_in_scope"].astype(bool)
    scoped_target = float(frame.loc[scope, "target_employment"].sum())
    scoped_estimate = float(frame.loc[scope, "estimated_employment"].sum())
    uncovered = int(
        ((frame["target_firms"] > 0) & frame["records"].eq(0)).sum()
    )
    return {
        "attempt": name,
        "status": "computed_with_uncovered_cells" if uncovered else "computed",
        "failure": failure,
        "geometry": dict(geometry),
        "uncovered_positive_firm_cells": uncovered,
        "firm_margin": {
            "target": target_firms,
            "estimate": estimated_firms,
            "ratio": margin_ratio(estimated_firms, target_firms),
        },
        "employment_margin_all_cells": {
            "target": target_employment,
            "estimate": estimated_employment,
            "ratio": margin_ratio(estimated_employment, target_employment),
        },
        "employment_margin_declared_scope": {
            "target": scoped_target,
            "estimate": scoped_estimate,
            "ratio": margin_ratio(scoped_estimate, scoped_target),
        },
    }


def _bds_holdout(
    working: pd.DataFrame,
    coverage: pd.DataFrame,
    bds: pd.DataFrame | None,
) -> dict[str, object]:
    if bds is None:
        return {
            "status": "not_run",
            "reason": "No BDS validation harness was supplied.",
        }
    required = {"calibration_band", "firms", "employment", "year"}
    if missing := sorted(required - set(bds.columns)):
        raise ValueError(f"BDS validation harness lacks columns {missing}.")
    exact = {"LT10", "B100_499", "B500_PLUS"}
    if (
        len(bds) != len(exact)
        or bds["calibration_band"].duplicated().any()
        or set(bds["calibration_band"]) != exact
    ):
        raise ValueError(
            "BDS holdout must contain one row for each of the three exact bands"
        )
    if bds["year"].nunique(dropna=False) != 1:
        raise ValueError("BDS holdout rows must share one explicit year")
    if bds.attrs.get("held_out") is not True:
        raise ValueError("BDS validation input must retain held_out=True provenance")
    _require_sha256(
        bds.attrs.get("extract_sha256"),
        label="BDS extract_sha256",
    )
    for column in ("year", "firms", "employment"):
        numeric = pd.to_numeric(bds[column], errors="coerce")
        if (
            numeric.isna().any()
            or not np.isfinite(numeric).all()
            or (numeric < 0).any()
            or not numeric.eq(np.floor(numeric)).all()
        ):
            raise ValueError(
                f"BDS holdout {column} must contain non-negative integers"
            )
    if bds["firms"].eq(0).any():
        raise ValueError("BDS exact-band firm counts must be positive")
    rows: list[dict[str, object]] = []
    ordered = bds.copy()
    ordered["_band_order"] = ordered["calibration_band"].map(
        {band: index for index, band in enumerate(CALIBRATION_BANDS)}
    )
    for target in ordered.sort_values("_band_order").drop(
        columns="_band_order"
    ).itertuples(index=False):
        donors = working[working["calibration_band"].eq(target.calibration_band)]
        estimated_firms = float(donors["firm_weight"].sum())
        estimated_employment = float(
            (donors["firm_weight"] * donors["employment"]).sum()
        )
        susb = coverage[
            coverage["calibration_band"].eq(target.calibration_band)
        ]
        susb_firms = float(susb["target_firms"].sum())
        susb_employment = float(susb["target_employment"].sum())
        rows.append(
            {
                "calibration_band": target.calibration_band,
                "bds_firms": float(target.firms),
                "susb_firms": susb_firms,
                "frame_firms": estimated_firms,
                "frame_to_bds_firm_ratio": margin_ratio(
                    estimated_firms, float(target.firms)
                ),
                "susb_to_bds_firm_ratio": margin_ratio(
                    susb_firms, float(target.firms)
                ),
                "frame_to_susb_firm_ratio": margin_ratio(
                    estimated_firms, susb_firms
                ),
                "employment_descriptive_noncomparable": {
                    "bds_all_sector_employment": float(target.employment),
                    "susb_all_sector_employment": susb_employment,
                    "frame_all_rows_weighted_employment": estimated_employment,
                    "reason": (
                        "The frame value includes rows whose employment is "
                        "declared out of scope, while national BDS has no "
                        "sector dimension on which to apply the same exclusion."
                    ),
                },
            }
        )
    return {
        "status": "computed",
        "year": int(bds["year"].iloc[0]),
        "scope": "national_exactly_nesting_bands_only",
        "held_out": True,
        "source_provenance": _plain_mapping(bds.attrs),
        "cells": rows,
        "warning": (
            "BDS is national while calibration uses non-additive SUSB industry "
            "firm counts; these ratios are a diagnostic, not a clean independent "
            "sector-by-band validation. Employment values are descriptive and "
            "not comparable across the frame's scope exclusions."
        ),
    }


def _aggregate_coverage(
    coverage: pd.DataFrame,
    dimension: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for value, group in coverage.groupby(dimension, sort=False):
        scope = group["employment_constraint_in_scope"].astype(bool)
        target_firms = float(group["target_firms"].sum())
        estimated_firms = float(group["estimated_firms"].sum())
        target_employment = float(group.loc[scope, "target_employment"].sum())
        estimated_employment = float(
            group.loc[scope, "estimated_employment"].sum()
        )
        rows.append(
            {
                dimension: str(value),
                "target_firms": target_firms,
                "estimated_firms": estimated_firms,
                "firm_ratio": margin_ratio(estimated_firms, target_firms),
                "target_employment_in_scope": target_employment,
                "estimated_employment_in_scope": estimated_employment,
                "employment_ratio_in_scope": margin_ratio(
                    estimated_employment, target_employment
                ),
            }
        )
    return rows


def _legacy_claim_comparison(
    coverage: pd.DataFrame,
    working: pd.DataFrame,
    config: USFirmBuildConfig,
    osha_reference: Mapping[str, object] | None,
) -> dict[str, object]:
    scope = working["employment_in_scope"]
    scoped_employment = float(
        (working.loc[scope, "firm_weight"] * working.loc[scope, "employment"]).sum()
    )
    scoped_target = float(
        coverage.loc[
            coverage["employment_constraint_in_scope"], "target_employment"
        ].sum()
    )
    all_weighted_employment = float(
        (working["firm_weight"] * working["employment"]).sum()
    )
    sector_55 = working["calibration_sector"].eq("55")
    weighted_55 = float(
        (
            working.loc[sector_55, "firm_weight"]
            * working.loc[sector_55, "employment"]
        ).sum()
    )
    agreement = (
        osha_reference.get("agreement_rate")
        if isinstance(osha_reference, Mapping)
        else None
    )
    return {
        "real_records_987039": {
            "claim": 987_039,
            "observed_current_frame_rows": int(len(working)),
            "reproduced": False,
            "status": "not_reproduced_unit_changed",
            "reason": (
                "The legacy count pooled unlike Form sponsor and OSHA "
                "establishment units; this frame deliberately does not."
            ),
        },
        "positive_susb_cells_97": {
            "claim": 97,
            "observed": int(len(coverage)),
            "target_geometry_reproduced": len(coverage) == 97,
            "all_cells_have_sponsor_support": bool(
                coverage["observed_records"].gt(0).all()
            ),
            "all_cells_have_at_least_10_sponsors": bool(
                coverage["observed_records"].ge(10).all()
            ),
        },
        "all_cells_at_least_10_sponsors": {
            "claim": True,
            "observed": bool(coverage["observed_records"].ge(10).all()),
            "minimum_records": int(coverage["observed_records"].min()),
        },
        "form_osha_band_agreement_0_663": {
            "claim": 0.663,
            "observed": agreement,
            "status": "computed" if agreement is not None else "not_run",
        },
        "in_scope_employment_ratio_1_024": {
            "claim": 1.024,
            "observed": margin_ratio(scoped_employment, scoped_target),
        },
        "weight_upper_bound_140": {
            "claim": 140.0,
            "configured": float(config.weight_bounds[1]),
            "configuration_reproduced": config.weight_bounds[1] == 140.0,
            "empirical_knee_reproduced": False,
        },
        "naics_55_weighted_employment_share_0_24": {
            "claim": 0.24,
            "observed": margin_ratio(weighted_55, all_weighted_employment),
        },
    }


def _transformation_register(config: USFirmBuildConfig) -> dict[str, object]:
    return {
        "observation_unit": "one_plan_sponsor_ein",
        "deduplication": (
            "maximum_end_of_year_active_participants_with_coherent_lexical_"
            "tie_break"
        ),
        "employment_measure": "active_plan_participants_end_of_plan_year",
        "employment_measure_relation_to_enterprise_employment": (
            "not_ordered_across_retained_plan_entity_strata"
        ),
        "single_employer_filter_applied": False,
        "plan_entity_strata_preserved": True,
        "unknown_full_naics_rule": "drop_and_count_before_target_join",
        "unmatched_target_cell_rule": "drop_and_count",
        "sector_crosswalk": {
            "31|32|33": "31-33",
            "44|45": "44-45",
            "48|49": "48-49",
        },
        "private_calibration_band_edges": [10, 50, 100, 500],
        "private_calibration_bands_are_ic2_wire_type": False,
        "employment_out_of_scope_sectors": list(
            config.employment_out_of_scope_sectors
        ),
        "weight_bounds_absolute": list(config.weight_bounds),
        "max_bound_iterations": config.max_bound_iterations,
        "calibration_method": config.calibration_method,
        "bound_rule": (
            "final_absolute_clip_without_rescale; both margin residuals reported"
        ),
        "support_infeasible_rule": (
            "bounded_flat_firm_only_weight_and_employment_in_scope_false"
        ),
        "synthetic_rows_created": False,
        "osha_union_applied": False,
    }


def _source_receipt(
    source: VerifiedUSFirmStaging | SyntheticUSFirmSourceReceipt,
    donor_hash: str,
) -> dict[str, object]:
    if isinstance(source, VerifiedUSFirmStaging):
        # A previously returned dataclass is only a hint to the staging root.
        # Rehash the pinned raw and derived bytes at the build trust boundary.
        verified = verify_staged_sources(source.root)
        if (
            verified.manifest_sha256 != source.manifest_sha256
            or verified.source_pins_sha256 != source.source_pins_sha256
            or verified.aggregate_raw_plus_staged_size_bytes
            != source.aggregate_raw_plus_staged_size_bytes
        ):
            raise ValueError(
                "US firm staging changed after the supplied receipt was issued"
            )
        return {
            "status": "verified_external_staging",
            "manifest_sha256": verified.manifest_sha256,
            "source_pins_sha256": verified.source_pins_sha256,
            "aggregate_raw_plus_staged_size_bytes": (
                verified.aggregate_raw_plus_staged_size_bytes
            ),
            "sources": [
                {
                    "key": item.key,
                    "raw_size_bytes": item.raw_size_bytes,
                    "raw_sha256": item.raw_sha256,
                    "staged_size_bytes": item.staged_size_bytes,
                    "staged_sha256": item.staged_sha256,
                    "retrieved_at_utc": item.retrieved_at_utc,
                }
                for item in verified.sources
            ],
        }
    if isinstance(source, SyntheticUSFirmSourceReceipt):
        if source.donor_content_sha256 != donor_hash:
            raise ValueError(
                "Synthetic US firm source receipt does not match donor content"
            )
        fixture_payload = {
            "schema_version": "microcosm.us_firms.synthetic_source.v1",
            "status": "synthetic_fixture",
            "fixture_name": source.fixture_name,
            "donor_content_sha256": donor_hash,
        }
        return {
            **fixture_payload,
            "manifest_sha256": hashlib.sha256(
                _canonical_json(fixture_payload)
            ).hexdigest(),
        }
    raise TypeError(
        "source_provenance must be VerifiedUSFirmStaging or an explicit "
        "SyntheticUSFirmSourceReceipt"
    )


def _target_grid_receipt(targets: pd.DataFrame) -> dict[str, object]:
    sectors = sorted(
        {str(value) for value in targets["calibration_sector"]},
        key=lambda value: int(value[:2]),
    )
    positive = set(
        zip(
            targets["calibration_sector"].astype(str),
            targets["calibration_band"].astype(str),
            strict=True,
        )
    )
    rectangular = {(sector, band) for sector in sectors for band in CALIBRATION_BANDS}
    absent = sorted(
        rectangular - positive,
        key=lambda cell: (int(cell[0][:2]), CALIBRATION_BANDS.index(cell[1])),
    )
    return {
        "definition": (
            "Positive published target cells are calibrated. The additional "
            "rectangle entries below are non-positive or unpublished and are "
            "not silently represented as positive targets."
        ),
        "sectors": sectors,
        "calibration_bands": list(CALIBRATION_BANDS),
        "rectangular_cell_count": len(rectangular),
        "positive_target_cell_count": len(positive),
        "nonpositive_or_unpublished_cells": [
            {
                "calibration_sector": sector,
                "calibration_band": band,
            }
            for sector, band in absent
        ],
    }


def _require_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"{label} must be a lowercase 64-character SHA-256")
    return value


def _dataframe_content_sha256(frame: pd.DataFrame) -> str:
    if not frame.columns.is_unique or any(
        not isinstance(column, str) for column in frame.columns
    ):
        raise ValueError("Hash-bound input tables require unique string columns")
    columns = sorted(frame.columns)
    normalized = frame.loc[:, columns].copy()
    normalized = normalized.sort_values(columns, kind="mergesort", na_position="last")
    schema = {
        "columns": [
            {"name": column, "dtype": str(normalized[column].dtype)}
            for column in columns
        ],
        "rows": int(len(normalized)),
    }
    null_bitmap = np.packbits(
        normalized.isna().to_numpy(dtype=np.uint8),
        axis=None,
        bitorder="little",
    ).tobytes()
    content = normalized.to_csv(
        index=False,
        lineterminator="\n",
        na_rep="<NA>",
        float_format="%.17g",
    ).encode("utf-8")
    digest = hashlib.sha256()
    for part in (_canonical_json(schema), null_bitmap, content):
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def _canonical_json(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _plain_mapping(value: Mapping[str, object]) -> dict[str, object]:
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return json.loads(
        frame.to_json(orient="records", double_precision=15)
    )
