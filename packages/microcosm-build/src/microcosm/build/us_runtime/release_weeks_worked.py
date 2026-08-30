"""Authenticated 2024 stacked-release ownership for measured weeks worked.

The multispine pool deliberately excludes ``weeks_worked`` because the pinned
PolicyEngine-US engine owns it with a carry-forward formula from 2025 onward.
In 2024, however, it is an input leaf.  This release-only provenance boundary
materializes that leaf before support selection:

* physical ASEC lineages carry validated integral ``WKSWORK`` in ``[0, 52]``;
* physical ACS lineages join the pinned 2024 one-year PUMS person archive on
  ``SERIALNO + SPORDER`` and carry validated ``WKWN`` in ``[1, 52]``; and
* validated ACS blanks are recoded to zero by Microcosm, then fanned to every
  support clone through assembly-unique ``person_source_id``.

Origin routing belongs here, beside the pinned ACS release-predictor join.  It
does not belong in the source-blind hours-worked population operator.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import numpy as np
import pandas as pd

from microcosm.build.gates import GateResult
from microcosm.build.source_manifest import (
    SourceOperationSpec,
    SourceStageSpec,
    load_source_manifest,
)
from microcosm.build.source_runtime import (
    SourceRuntimeConfig,
    SourceRuntimeContext,
    SourceRuntimeError,
    run_source_stage,
)
from microcosm.build.us_runtime.acs_release_predictors import (
    ACS_2024_PERSON_ZIP_SHA256 as _PREDICTOR_ACS_2024_PERSON_ZIP_SHA256,
)
from microcosm.build.us_runtime.acs_release_predictors import (
    _verify_archive,
)
from microcosm.build.us_runtime.support_provenance import (
    spine_provenance_counts,
    support_channel_column,
    support_clone_index_column,
    support_source_id_column,
    validate_assembly_provenance,
)
from microcosm.frame import US_SCHEMA, Frame

__all__ = [
    "ACS_2024_PERSON_ROW_COUNT",
    "ACS_2024_PERSON_ZIP_SHA256",
    "ACS_2024_WKWN_ALLOCATION_CROSSTAB",
    "ReleaseWeeksWorkedResult",
    "US_RELEASE_WEEKS_WORKED_OPERATION",
    "US_RELEASE_WEEKS_WORKED_STAGE_NAME",
    "derive_us_release_weeks_worked_from_manifest",
    "us_release_weeks_worked_gate",
    "us_release_weeks_worked_stage_spec",
    "with_us_release_weeks_worked",
]

US_RELEASE_WEEKS_WORKED_STAGE_NAME = "stacked_release_weeks_worked"
US_RELEASE_WEEKS_WORKED_OPERATION = "derive_stacked_release_weeks_worked"
US_RELEASE_WEEKS_WORKED_PERIOD = 2024

ACS_2024_PERSON_ZIP_SHA256 = _PREDICTOR_ACS_2024_PERSON_ZIP_SHA256
ACS_2024_PERSON_ROW_COUNT = 3_422_888
ACS_2024_WKWN_ALLOCATION_CROSSTAB: Mapping[str, Mapping[str, int]] = {
    "blank": {"allocated": 2, "not_allocated": 1_655_754},
    "nonblank": {"allocated": 305_604, "not_allocated": 1_461_528},
}

_ASEC_CHANNEL = "asec"
_ACS_CHANNEL = "acs"
_ALLOWED_CLONE_INDICES = (0, 1, 2)
_PERSON_MEMBERS = ("psam_pusa.csv", "psam_pusb.csv")
_RAW_COLUMNS = ("SERIALNO", "SPORDER", "WKWN", "FWKWNP")
_ASEC_SOURCE = "WKSWORK"
_ACS_SOURCE = "WKWN"
_ACS_ALLOCATION_FLAG = "FWKWNP"
_OUTPUT = "weeks_worked"
_STAGE_ACS_WEEKS = "__microcosm_release_acs_WKWN"
_STAGE_ACS_ALLOCATION = "__microcosm_release_acs_FWKWNP"
_DEFAULT_CHUNKSIZE = 250_000
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

_OPERATION_PARAMETERS: Mapping[str, object] = {
    "release_period": US_RELEASE_WEEKS_WORKED_PERIOD,
    "asec_source": _ASEC_SOURCE,
    "asec_integral_domain": [0, 52],
    "acs_source": _ACS_SOURCE,
    "acs_blank_or_integral_domain": [1, 52],
    "acs_allocation_flag": _ACS_ALLOCATION_FLAG,
    "acs_allocation_flag_domain": [0, 1],
    "acs_blank_recode": 0,
    "acs_blank_recode_owner": "Microcosm",
    "semantic_join_key": ["SERIALNO", "SPORDER"],
    "clone_fanout_key": "person_source_id",
}


@dataclass(frozen=True)
class ReleaseWeeksWorkedResult:
    """A weeks-enriched frame and its JSON-ready measured-source receipt."""

    frame: Frame
    receipt: Mapping[str, Any]


def us_release_weeks_worked_stage_spec() -> SourceStageSpec:
    """Load the packaged release-only weeks source-stage declaration."""

    manifest = load_source_manifest(
        files("microcosm.build.us").joinpath("source_stages.json")
    )
    stage_map = manifest.stage_map()
    try:
        return stage_map[US_RELEASE_WEEKS_WORKED_STAGE_NAME]
    except KeyError as exc:
        raise ValueError(
            "US source manifest declares no release-only weeks-worked stage."
        ) from exc


def derive_us_release_weeks_worked_from_manifest(
    frame: pd.DataFrame | None,
    operation: SourceOperationSpec,
    context: SourceRuntimeContext,
) -> pd.DataFrame:
    """Apply the declared ASEC/ACS measured mapping to an authenticated table."""

    if operation.kind != US_RELEASE_WEEKS_WORKED_OPERATION:
        raise SourceRuntimeError(
            "US release weeks derivation received unexpected operation "
            f"{operation.kind!r}."
        )
    if dict(operation.parameters) != dict(_OPERATION_PARAMETERS):
        raise SourceRuntimeError(
            "US release weeks derivation parameters differ from the reviewed "
            "2024 measured mapping."
        )
    if context.config.target_year != US_RELEASE_WEEKS_WORKED_PERIOD:
        raise SourceRuntimeError(
            "US release weeks derivation is authorized only for period 2024."
        )
    if frame is None:
        raise SourceRuntimeError(
            "US release weeks derivation requires the person table to be read first."
        )
    required = {
        support_channel_column("person"),
        _ASEC_SOURCE,
        _STAGE_ACS_WEEKS,
        _STAGE_ACS_ALLOCATION,
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise SourceRuntimeError(
            f"US release weeks derivation is missing person column(s): {missing}."
        )

    channel = frame[support_channel_column("person")].astype(str)
    observed_channels = set(channel.unique())
    if observed_channels != {_ASEC_CHANNEL, _ACS_CHANNEL}:
        raise SourceRuntimeError(
            "US release weeks derivation requires exact ASEC/ACS origins; got "
            f"{sorted(observed_channels)}."
        )

    asec = channel.eq(_ASEC_CHANNEL)
    acs = channel.eq(_ACS_CHANNEL)
    asec_values = _required_integral_domain(
        frame.loc[asec, _ASEC_SOURCE],
        label="ASEC WKSWORK",
        minimum=0,
        maximum=52,
    )
    acs_values, acs_blank = _required_blank_or_integral_domain(
        frame.loc[acs, _STAGE_ACS_WEEKS],
        label="ACS WKWN",
        minimum=1,
        maximum=52,
    )
    _required_integral_domain(
        frame.loc[acs, _STAGE_ACS_ALLOCATION],
        label="ACS FWKWNP",
        minimum=0,
        maximum=1,
    )

    mapped = np.zeros(len(frame), dtype=np.float64)
    mapped[np.flatnonzero(asec.to_numpy())] = asec_values.to_numpy(dtype=np.float64)
    mapped[np.flatnonzero(acs.to_numpy())] = acs_values.fillna(0).to_numpy(
        dtype=np.float64
    )
    if int(acs_blank.sum()) != int(
        np.count_nonzero(acs.to_numpy() & np.equal(mapped, 0.0))
    ):
        raise AssertionError("ACS zero-week rows differ from validated WKWN blanks.")

    if _OUTPUT in frame:
        current = pd.to_numeric(frame[_OUTPUT], errors="coerce")
        conflict = current.isna() | ~np.isclose(
            current.to_numpy(dtype=np.float64),
            mapped,
            rtol=0.0,
            atol=0.0,
        )
        if conflict.any():
            raise ValueError(
                "US release weeks derivation refuses conflicting pre-existing "
                f"weeks_worked values; conflicts={int(conflict.sum())}."
            )

    result = frame.copy(deep=True)
    result[_OUTPUT] = mapped
    return result


def with_us_release_weeks_worked(
    frame: Frame,
    *,
    time_period: int,
    acs_person_zip: str | Path,
    acs_person_sha256: str,
    pool_identity: Mapping[str, object],
    chunksize: int = _DEFAULT_CHUNKSIZE,
) -> ReleaseWeeksWorkedResult:
    """Materialize the authorized 2024 stacked-release weeks input leaf."""

    if time_period != US_RELEASE_WEEKS_WORKED_PERIOD:
        raise ValueError(
            "Direct release weeks_worked materialization is authorized only for "
            f"period 2024, not {time_period!r}."
        )
    if frame.schema != US_SCHEMA:
        raise ValueError("US release weeks-worked inputs require the US schema.")
    if chunksize <= 0:
        raise ValueError("US release weeks-worked chunksize must be positive.")

    validated_pool_identity = _validated_pool_identity(pool_identity)
    canonical, acs_rows, clone_counts = _canonical_acs_source_people(frame)
    selected_serials = frozenset(canonical["SERIALNO"].astype(str))
    archive_identity = _verify_archive(
        acs_person_zip,
        expected_sha256=acs_person_sha256,
        canonical_sha256=ACS_2024_PERSON_ZIP_SHA256,
        label="ACS 2024 person zip for release weeks_worked",
    )
    raw_person, raw_domain = _read_and_validate_acs_weeks_archive(
        Path(acs_person_zip),
        selected_serials=selected_serials,
        chunksize=chunksize,
    )
    raw_person["SPORDER"] = _required_integral_domain(
        raw_person["SPORDER"],
        label="raw ACS SPORDER",
        minimum=1,
        maximum=10_000,
    )
    duplicate_raw = raw_person.duplicated(["SERIALNO", "SPORDER"], keep=False)
    if duplicate_raw.any():
        examples = (
            raw_person.loc[duplicate_raw, ["SERIALNO", "SPORDER"]]
            .head()
            .to_dict("records")
        )
        raise ValueError(f"ACS raw weeks person key collision(s): {examples}.")
    if len(raw_person) != len(canonical):
        raise ValueError(
            "ACS release weeks join requires an exact raw/pool semantic-key set; "
            f"pool source people={len(canonical)}, selected raw people="
            f"{len(raw_person)}."
        )

    joined = canonical.merge(
        raw_person,
        on=["SERIALNO", "SPORDER"],
        how="left",
        validate="one_to_one",
        indicator=True,
        sort=False,
    )
    unmatched = joined["_merge"].ne("both")
    if unmatched.any():
        examples = (
            joined.loc[
                unmatched, ["person_source_id", "SERIALNO", "SPORDER"]
            ]
            .head()
            .to_dict("records")
        )
        raise ValueError(
            "ACS release weeks join is not total over pool source people; "
            f"unmatched={int(unmatched.sum())}, examples={examples}."
        )
    joined = joined.drop(columns="_merge")

    person = frame.table("person")
    channel_column = support_channel_column("person")
    source_column = support_source_id_column("person")
    acs_mask = person[channel_column].eq(_ACS_CHANNEL)
    source_ids = _required_integral_domain(
        person.loc[acs_mask, source_column],
        label="ACS person_source_id",
        minimum=0,
        maximum=np.iinfo(np.int64).max,
    )
    by_source = joined.set_index("person_source_id")
    weeks = source_ids.map(by_source[_ACS_SOURCE])
    allocation = source_ids.map(by_source[_ACS_ALLOCATION_FLAG])
    if allocation.isna().any():
        raise AssertionError("ACS weeks fan-out lost FWKWNP value(s).")
    expected_blank = source_ids.map(by_source[_ACS_SOURCE].isna())
    if not weeks.isna().equals(expected_blank.astype(bool)):
        raise AssertionError("ACS weeks fan-out changed the validated WKWN blank set.")

    stage_person = person.copy(deep=True)
    stage_person[_STAGE_ACS_WEEKS] = np.nan
    stage_person[_STAGE_ACS_ALLOCATION] = np.nan
    stage_person.loc[acs_mask, _STAGE_ACS_WEEKS] = weeks.to_numpy()
    stage_person.loc[acs_mask, _STAGE_ACS_ALLOCATION] = allocation.to_numpy()
    output = run_source_stage(
        us_release_weeks_worked_stage_spec(),
        tables={"person": stage_person},
        operation_handlers={
            US_RELEASE_WEEKS_WORKED_OPERATION: (
                derive_us_release_weeks_worked_from_manifest
            )
        },
        config=SourceRuntimeConfig(target_year=time_period),
    )

    tables = {entity: frame.table(entity).copy() for entity in frame.entities}
    for link in frame.links:
        tables[link] = frame.link(link).copy()
    tables["person"][_OUTPUT] = output[_OUTPUT].to_numpy(dtype=np.float64)
    enriched = Frame(
        tables,
        frame.schema,
        {entity: frame.weights_for(entity) for entity in frame.weighted_entities},
        frame.strata,
        mass_log=frame.mass_log,
        metadata=frame.metadata,
    )

    semantic_keys = canonical.loc[:, ["SERIALNO", "SPORDER"]].sort_values(
        ["SERIALNO", "SPORDER"], kind="stable"
    )
    semantic_key_sha256 = hashlib.sha256(
        "".join(
            f"{serial}:{int(sporder)}\n"
            for serial, sporder in semantic_keys.itertuples(index=False, name=None)
        ).encode()
    ).hexdigest()
    asec_mask = person[channel_column].eq(_ASEC_CHANNEL)
    asec_values = _required_integral_domain(
        person.loc[asec_mask, _ASEC_SOURCE],
        label="ASEC WKSWORK",
        minimum=0,
        maximum=52,
    )
    asec_years = _source_year_counts(person.loc[asec_mask])
    blank_support_rows = int(output.loc[acs_mask, _OUTPUT].eq(0).sum())
    receipt: dict[str, Any] = {
        "version": 1,
        "stage": US_RELEASE_WEEKS_WORKED_STAGE_NAME,
        "operation": US_RELEASE_WEEKS_WORKED_OPERATION,
        "period_identity": {
            "release_period": time_period,
            "acs_archive_vintage": 2024,
            "asec_source_year_rows": asec_years,
            "asec_reference_window": "calendar year before each ASEC interview",
            "acs_reference_window": "rolling 12 months before ACS interview",
            "reference_window_mismatch_accepted": True,
        },
        "artifacts": {
            "authenticated_pool": validated_pool_identity,
            "acs_person_archive": dict(archive_identity),
        },
        "raw_domains": {
            "asec_WKSWORK": {
                "rows": int(len(asec_values)),
                "minimum": int(asec_values.min()),
                "maximum": int(asec_values.max()),
                "null": 0,
                "nonintegral": 0,
                "outside_0_52": 0,
                "policy": "validated_integral_0_52_no_clipping",
            },
            "acs_archive": raw_domain,
        },
        "join": {
            "semantic_key": ["household.SERIALNO", "person.SPORDER"],
            "clone_fanout_key": "person_source_id",
            "acs_source_people": int(len(canonical)),
            "acs_support_rows": acs_rows,
            "acs_support_rows_by_clone_index": clone_counts,
            "selected_raw_person_rows": int(len(raw_person)),
            "matched_pool_source_people": int(len(canonical)),
            "unmatched_pool_source_people": 0,
            "source_identity_collisions": 0,
            "raw_semantic_key_collisions": 0,
            "semantic_key_sha256": semantic_key_sha256,
        },
        "mapping": {
            "asec": "weeks_worked <- WKSWORK",
            "acs": "weeks_worked <- WKWN",
            "source_character": "source-direct reported-or-allocated",
            "acs_blank_recode": {
                "input": "validated Census WKWN blank",
                "output": 0,
                "owner": "Microcosm",
                "semantic": "structural not-in-universe recode",
                "archive_blank_source_people": int(
                    raw_domain["WKWN_blank_nonblank_by_allocation"]["blank"][
                        "allocated"
                    ]
                    + raw_domain["WKWN_blank_nonblank_by_allocation"]["blank"][
                        "not_allocated"
                    ]
                ),
                "recoded_support_rows": blank_support_rows,
            },
            "conflicting_preexisting_values": 0,
            "canonical_source_value_sha256": _source_value_sha256(output),
        },
    }
    receipt["sha256"] = _canonical_sha256(receipt)
    return ReleaseWeeksWorkedResult(frame=enriched, receipt=receipt)


def us_release_weeks_worked_gate(
    before: Frame,
    result: ReleaseWeeksWorkedResult,
) -> GateResult:
    """Fail closed on the complete release-only weeks source receipt."""

    failures: list[str] = []
    details: dict[str, object] = {"source_receipt": _json_ready(result.receipt)}
    try:
        _validate_source_receipt(result.receipt)
        after = result.frame
        person = after.table("person")
        values = _required_integral_domain(
            person[_OUTPUT],
            label="materialized weeks_worked",
            minimum=0,
            maximum=52,
        )
        details["materialized_domain"] = {
            "rows": int(len(values)),
            "minimum": int(values.min()),
            "maximum": int(values.max()),
            "null": 0,
            "nonintegral": 0,
            "outside_0_52": 0,
        }
        mapping_receipt = _mapping(result.receipt["mapping"], label="mapping")
        expected_source_value_sha256 = mapping_receipt.get(
            "canonical_source_value_sha256"
        )
        live_source_value_sha256 = _source_value_sha256(person)
        details["canonical_source_value_sha256"] = live_source_value_sha256
        if live_source_value_sha256 != expected_source_value_sha256:
            raise ValueError(
                "US release weeks-worked live values differ from the canonical "
                "source-value receipt."
            )

        channel_column = support_channel_column("person")
        asec_mask = person[channel_column].eq(_ASEC_CHANNEL)
        asec_source = _required_integral_domain(
            person.loc[asec_mask, _ASEC_SOURCE],
            label="live ASEC WKSWORK",
            minimum=0,
            maximum=52,
        )
        if not np.array_equal(
            values.loc[asec_mask].to_numpy(),
            asec_source.to_numpy(),
        ):
            raise ValueError(
                "US release weeks-worked live ASEC values differ from WKSWORK."
            )
        recode_receipt = _mapping(
            mapping_receipt.get("acs_blank_recode"),
            label="ACS blank recode",
        )
        live_acs_zero_rows = int(
            values.loc[person[channel_column].eq(_ACS_CHANNEL)].eq(0).sum()
        )
        details["acs_blank_recode_support_rows"] = live_acs_zero_rows
        if live_acs_zero_rows != recode_receipt.get("recoded_support_rows"):
            raise ValueError(
                "US release weeks-worked live ACS zero rows differ from the "
                "structural blank-recode receipt."
            )

        provenance = spine_provenance_counts(
            after,
            boundary="US release weeks-worked gate",
        )
        person_provenance = provenance["person"]
        observed_roles = set(person_provenance["by_clone_index"])
        allowed_roles = {str(index) for index in _ALLOWED_CLONE_INDICES}
        if not observed_roles <= allowed_roles:
            raise ValueError(
                "US release weeks-worked gate found unsupported clone role(s): "
                f"{sorted(observed_roles - allowed_roles)}."
            )
        joint = {
            channel: {
                str(index): int(
                    person_provenance["by_source_channel_and_clone_index"]
                    .get(channel, {})
                    .get(str(index), 0)
                )
                for index in _ALLOWED_CLONE_INDICES
            }
            for channel in (_ASEC_CHANNEL, _ACS_CHANNEL)
        }
        details["by_source_channel_and_clone_index"] = joint

        source_column = support_source_id_column("person")
        source_ids = _required_integral_domain(
            person[source_column],
            label="person_source_id",
            minimum=0,
            maximum=np.iinfo(np.int64).max,
        )
        disagreement_frame = pd.DataFrame(
            {
                "source_channel": person[channel_column].astype(str),
                "person_source_id": source_ids,
                "weeks_worked": values,
            }
        )
        disagreement_counts = {
            channel: int(
                disagreement_frame.loc[
                    disagreement_frame["source_channel"].eq(channel)
                ]
                .groupby("person_source_id", sort=False)["weeks_worked"]
                .nunique(dropna=False)
                .gt(1)
                .sum()
            )
            for channel in (_ASEC_CHANNEL, _ACS_CHANNEL)
        }
        details["per_source_clone_disagreements"] = disagreement_counts
        if any(disagreement_counts.values()):
            raise ValueError(
                "US release weeks-worked gate found per-source clone "
                f"disagreement(s): {disagreement_counts}."
            )

        column_diff = _column_diff_receipt(before, after)
        details["column_diff"] = column_diff
        if column_diff["changed_columns"] not in ([], ["person.weeks_worked"]):
            raise ValueError(
                "US release weeks-worked stage changed columns outside "
                f"person.weeks_worked: {column_diff['changed_columns']}."
            )
    except (AssertionError, KeyError, TypeError, ValueError) as exc:
        failures.append(str(exc))

    return GateResult(
        name="stacked_release_weeks_worked",
        passed=not failures,
        failures=tuple(failures),
        details=details,
    )


def _canonical_acs_source_people(
    frame: Frame,
) -> tuple[pd.DataFrame, int, dict[str, int]]:
    validate_assembly_provenance(
        frame,
        boundary="US release weeks-worked source join",
    )
    person = frame.table("person")
    household = frame.table("household")
    channel_column = support_channel_column("person")
    clone_column = support_clone_index_column("person")
    source_column = support_source_id_column("person")
    household_channel = support_channel_column("household")
    required_person = {
        "person_household_id",
        "source_year",
        "source_person_id",
        "SPORDER",
        _ASEC_SOURCE,
        channel_column,
        clone_column,
        source_column,
    }
    required_household = {"household_id", "SERIALNO", household_channel}
    missing_person = sorted(required_person - set(person.columns))
    missing_household = sorted(required_household - set(household.columns))
    if missing_person or missing_household:
        raise ValueError(
            "US release weeks-worked join requires complete pool lineage; "
            f"missing person={missing_person}, household={missing_household}."
        )
    observed_channels = set(person[channel_column].astype(str).unique())
    if observed_channels != {_ASEC_CHANNEL, _ACS_CHANNEL}:
        raise ValueError(
            "US release weeks-worked receipts require exact ASEC/ACS physical "
            f"channels; got {sorted(observed_channels)}."
        )
    clone_index = _required_integral_domain(
        person[clone_column],
        label="person support clone index",
        minimum=0,
        maximum=2,
    )
    source_id = _required_integral_domain(
        person[source_column],
        label="person_source_id",
        minimum=0,
        maximum=np.iinfo(np.int64).max,
    )
    duplicate_clone = pd.DataFrame(
        {"person_source_id": source_id, "clone_index": clone_index}
    ).duplicated(keep=False)
    if duplicate_clone.any():
        raise ValueError(
            "US release weeks-worked pool has duplicate "
            "(person_source_id, clone_index) collision(s)."
        )

    acs_mask = person[channel_column].eq(_ACS_CHANNEL)
    selected = person.loc[
        acs_mask,
        [
            "person_household_id",
            "source_year",
            "source_person_id",
            "SPORDER",
            source_column,
            clone_column,
        ],
    ].copy()
    selected[source_column] = source_id.loc[acs_mask].to_numpy()
    selected[clone_column] = clone_index.loc[acs_mask].to_numpy()
    selected = selected.merge(
        household.loc[:, ["household_id", "SERIALNO", household_channel]],
        left_on="person_household_id",
        right_on="household_id",
        how="left",
        validate="many_to_one",
        indicator=True,
        sort=False,
    )
    if selected["_merge"].ne("both").any():
        raise ValueError("US release weeks-worked ACS people have orphan households.")
    selected = selected.drop(columns="_merge")
    if not selected[household_channel].eq(_ACS_CHANNEL).all():
        raise ValueError(
            "US release weeks-worked person/household physical channels disagree."
        )
    if selected["SERIALNO"].isna().any():
        raise ValueError("US release weeks-worked ACS SERIALNO values must be complete.")
    selected["SERIALNO"] = selected["SERIALNO"].astype(str)
    source_year = _required_integral_domain(
        selected["source_year"],
        label="ACS source_year",
        minimum=2024,
        maximum=2024,
    )
    if not source_year.eq(2024).all():  # pragma: no cover - domain guard
        raise AssertionError("ACS release weeks source period changed.")
    source_person = _required_integral_domain(
        selected["source_person_id"],
        label="ACS source_person_id",
        minimum=1,
        maximum=10_000,
    )
    sporder = _required_integral_domain(
        selected["SPORDER"],
        label="ACS pool SPORDER",
        minimum=1,
        maximum=10_000,
    )
    if not np.array_equal(source_person.to_numpy(), sporder.to_numpy()):
        raise ValueError(
            "US release weeks-worked ACS source_person_id does not equal SPORDER."
        )
    selected["SPORDER"] = sporder.to_numpy(dtype=np.int64)

    invariant_columns = ("SERIALNO", "SPORDER", "source_year", "source_person_id")
    for column in invariant_columns:
        counts = selected.groupby(source_column, sort=False)[column].nunique(
            dropna=False
        )
        if counts.gt(1).any():
            raise ValueError(
                "US release weeks-worked person_source_id maps to conflicting "
                f"raw {column} identities."
            )
    native_counts = selected.loc[selected[clone_column].eq(0), source_column].value_counts()
    all_sources = pd.Index(selected[source_column].unique())
    if native_counts.reindex(all_sources, fill_value=0).ne(1).any():
        raise ValueError(
            "Every ACS person_source_id must have exactly one clone-index-zero row."
        )
    canonical = selected.loc[selected[clone_column].eq(0)].copy()
    canonical["person_source_id"] = canonical[source_column].astype("int64")
    duplicate_semantic = canonical.duplicated(["SERIALNO", "SPORDER"], keep=False)
    if duplicate_semantic.any():
        raise ValueError("ACS pool weeks semantic person key collision(s).")
    acs_clone_index = clone_index.loc[acs_mask]
    clone_counts = {
        str(index): int(acs_clone_index.eq(index).sum())
        for index in _ALLOWED_CLONE_INDICES
    }
    return canonical, int(acs_mask.sum()), clone_counts


def _read_and_validate_acs_weeks_archive(
    path: Path,
    *,
    selected_serials: frozenset[str],
    chunksize: int,
) -> tuple[pd.DataFrame, dict[str, object]]:
    pieces: list[pd.DataFrame] = []
    cross = {
        "blank": {"allocated": 0, "not_allocated": 0},
        "nonblank": {"allocated": 0, "not_allocated": 0},
    }
    total_rows = 0
    with ZipFile(path) as archive:
        csv_members = {
            Path(name).name.lower(): name
            for name in archive.namelist()
            if name.lower().endswith(".csv")
            and Path(name).name.lower().startswith("psam_pus")
        }
        expected = tuple(name.lower() for name in _PERSON_MEMBERS)
        if tuple(sorted(csv_members)) != tuple(sorted(expected)):
            raise ValueError(
                "ACS weeks person archive members differ: expected "
                f"{list(expected)}, got {sorted(csv_members)}."
            )
        for basename in expected:
            member_name = csv_members[basename]
            with archive.open(member_name) as member:
                header = pd.read_csv(member, nrows=0).columns.tolist()
            missing = sorted(set(_RAW_COLUMNS) - set(header))
            if missing:
                raise ValueError(
                    f"ACS weeks archive member {member_name!r} missing "
                    f"column(s): {missing}."
                )
            with archive.open(member_name) as member:
                for chunk in pd.read_csv(
                    member,
                    usecols=list(_RAW_COLUMNS),
                    dtype={"SERIALNO": "string"},
                    chunksize=chunksize,
                    low_memory=False,
                ):
                    if chunk["SERIALNO"].isna().any():
                        raise ValueError("ACS weeks archive SERIALNO must not be blank.")
                    chunk["SERIALNO"] = chunk["SERIALNO"].astype(str)
                    _required_integral_domain(
                        chunk["SPORDER"],
                        label="raw ACS SPORDER",
                        minimum=1,
                        maximum=10_000,
                    )
                    _values, blank = _required_blank_or_integral_domain(
                        chunk[_ACS_SOURCE],
                        label="ACS WKWN",
                        minimum=1,
                        maximum=52,
                    )
                    allocation = _required_integral_domain(
                        chunk[_ACS_ALLOCATION_FLAG],
                        label="ACS FWKWNP",
                        minimum=0,
                        maximum=1,
                    ).eq(1)
                    cross["blank"]["allocated"] += int((blank & allocation).sum())
                    cross["blank"]["not_allocated"] += int(
                        (blank & ~allocation).sum()
                    )
                    cross["nonblank"]["allocated"] += int(
                        (~blank & allocation).sum()
                    )
                    cross["nonblank"]["not_allocated"] += int(
                        (~blank & ~allocation).sum()
                    )
                    total_rows += len(chunk)
                    retained = chunk.loc[chunk["SERIALNO"].isin(selected_serials)]
                    if not retained.empty:
                        pieces.append(retained.copy())

    expected_cross = _json_ready(ACS_2024_WKWN_ALLOCATION_CROSSTAB)
    if total_rows != ACS_2024_PERSON_ROW_COUNT:
        raise ValueError(
            "ACS weeks archive row count changed: expected "
            f"{ACS_2024_PERSON_ROW_COUNT}, got {total_rows}."
        )
    if cross != expected_cross:
        raise ValueError(
            "ACS WKWN blank/nonblank x FWKWNP allocation cross-tab changed: "
            f"expected {expected_cross}, got {cross}."
        )
    if not pieces:
        raise ValueError("ACS weeks archive contains no selected pool records.")
    selected = pd.concat(pieces, ignore_index=True)
    nonblank = cross["nonblank"]["allocated"] + cross["nonblank"]["not_allocated"]
    allocated = cross["blank"]["allocated"] + cross["nonblank"]["allocated"]
    return selected, {
        "person_rows": total_rows,
        "WKWN": {
            "blank": total_rows - nonblank,
            "nonblank": nonblank,
            "minimum_nonblank": 1,
            "maximum_nonblank": 52,
            "invalid": 0,
            "policy": "blank_or_integral_1_52",
        },
        "FWKWNP": {
            "domain": [0, 1],
            "allocated": allocated,
            "invalid": 0,
        },
        "WKWN_blank_nonblank_by_allocation": cross,
    }


def _validate_source_receipt(receipt: Mapping[str, object]) -> None:
    required = {
        "version",
        "stage",
        "operation",
        "period_identity",
        "artifacts",
        "raw_domains",
        "join",
        "mapping",
        "sha256",
    }
    if set(receipt) != required:
        raise ValueError("US release weeks-worked source receipt schema changed.")
    if receipt["version"] != 1:
        raise ValueError("US release weeks-worked source receipt version changed.")
    if receipt["stage"] != US_RELEASE_WEEKS_WORKED_STAGE_NAME or receipt[
        "operation"
    ] != US_RELEASE_WEEKS_WORKED_OPERATION:
        raise ValueError("US release weeks-worked source stage identity changed.")
    expected_sha = receipt["sha256"]
    if not isinstance(expected_sha, str) or not _SHA256_PATTERN.fullmatch(expected_sha):
        raise ValueError("US release weeks-worked receipt SHA-256 is malformed.")
    unhashed = {key: value for key, value in receipt.items() if key != "sha256"}
    if _canonical_sha256(unhashed) != expected_sha:
        raise ValueError("US release weeks-worked source receipt digest changed.")
    period = _mapping(receipt["period_identity"], label="period identity")
    if (
        period.get("release_period") != 2024
        or period.get("acs_archive_vintage") != 2024
        or period.get("reference_window_mismatch_accepted") is not True
    ):
        raise ValueError("US release weeks-worked period identity changed.")
    artifacts = _mapping(receipt["artifacts"], label="artifacts")
    acs_archive = _mapping(
        artifacts.get("acs_person_archive"), label="ACS person archive"
    )
    if acs_archive.get("sha256") != ACS_2024_PERSON_ZIP_SHA256:
        raise ValueError("US release weeks-worked ACS archive hash changed.")
    _validated_pool_identity(
        _mapping(artifacts.get("authenticated_pool"), label="authenticated pool")
    )
    raw_domains = _mapping(receipt["raw_domains"], label="raw domains")
    asec_domain = _mapping(raw_domains.get("asec_WKSWORK"), label="ASEC raw domain")
    if set(asec_domain) != {
        "rows",
        "minimum",
        "maximum",
        "null",
        "nonintegral",
        "outside_0_52",
        "policy",
    }:
        raise ValueError("US release weeks-worked ASEC raw-domain schema changed.")
    asec_rows = _required_nonnegative_receipt_integer(
        asec_domain.get("rows"), label="ASEC rows", positive=True
    )
    asec_minimum = _required_nonnegative_receipt_integer(
        asec_domain.get("minimum"), label="ASEC minimum"
    )
    asec_maximum = _required_nonnegative_receipt_integer(
        asec_domain.get("maximum"), label="ASEC maximum"
    )
    if (
        asec_minimum > asec_maximum
        or asec_maximum > 52
        or asec_domain.get("null") != 0
        or asec_domain.get("nonintegral") != 0
        or asec_domain.get("outside_0_52") != 0
        or asec_domain.get("policy")
        != "validated_integral_0_52_no_clipping"
    ):
        raise ValueError("US release weeks-worked ASEC raw-domain receipt changed.")
    source_year_rows = period.get("asec_source_year_rows")
    if not isinstance(source_year_rows, Mapping) or not source_year_rows:
        raise ValueError("US release weeks-worked ASEC source-year receipt changed.")
    if sum(
        _required_nonnegative_receipt_integer(count, label="ASEC source-year rows")
        for count in source_year_rows.values()
    ) != asec_rows:
        raise ValueError(
            "US release weeks-worked ASEC source-year rows differ from raw rows."
        )
    acs_domain = _mapping(raw_domains.get("acs_archive"), label="ACS raw domain")
    if acs_domain.get("person_rows") != ACS_2024_PERSON_ROW_COUNT:
        raise ValueError("US release weeks-worked ACS row-count receipt changed.")
    if acs_domain.get("WKWN_blank_nonblank_by_allocation") != _json_ready(
        ACS_2024_WKWN_ALLOCATION_CROSSTAB
    ):
        raise ValueError(
            "US release weeks-worked WKWN/allocation joint receipt changed."
        )
    expected_cross = _json_ready(ACS_2024_WKWN_ALLOCATION_CROSSTAB)
    blank_rows = sum(expected_cross["blank"].values())
    nonblank_rows = sum(expected_cross["nonblank"].values())
    allocated_rows = (
        expected_cross["blank"]["allocated"]
        + expected_cross["nonblank"]["allocated"]
    )
    wkw_n = _mapping(acs_domain.get("WKWN"), label="ACS WKWN domain")
    if dict(wkw_n) != {
        "blank": blank_rows,
        "nonblank": nonblank_rows,
        "minimum_nonblank": 1,
        "maximum_nonblank": 52,
        "invalid": 0,
        "policy": "blank_or_integral_1_52",
    }:
        raise ValueError("US release weeks-worked ACS WKWN domain receipt changed.")
    fwkw_np = _mapping(acs_domain.get("FWKWNP"), label="ACS FWKWNP domain")
    if dict(fwkw_np) != {
        "domain": [0, 1],
        "allocated": allocated_rows,
        "invalid": 0,
    }:
        raise ValueError("US release weeks-worked ACS FWKWNP domain receipt changed.")
    if blank_rows + nonblank_rows != ACS_2024_PERSON_ROW_COUNT:
        raise ValueError(
            "US release weeks-worked joint ACS domain does not cover the archive."
        )
    join = _mapping(receipt["join"], label="join")
    for field in (
        "unmatched_pool_source_people",
        "source_identity_collisions",
        "raw_semantic_key_collisions",
    ):
        if join.get(field) != 0:
            raise ValueError(f"US release weeks-worked join receipt {field} is nonzero.")
    if join.get("semantic_key") != ["household.SERIALNO", "person.SPORDER"]:
        raise ValueError("US release weeks-worked semantic join key changed.")
    if join.get("clone_fanout_key") != "person_source_id":
        raise ValueError("US release weeks-worked clone fan-out key changed.")
    source_people = _required_nonnegative_receipt_integer(
        join.get("acs_source_people"), label="ACS source people", positive=True
    )
    matched_people = _required_nonnegative_receipt_integer(
        join.get("matched_pool_source_people"),
        label="matched ACS source people",
        positive=True,
    )
    selected_people = _required_nonnegative_receipt_integer(
        join.get("selected_raw_person_rows"),
        label="selected raw ACS people",
        positive=True,
    )
    if source_people != matched_people or source_people != selected_people:
        raise ValueError("US release weeks-worked exact join counts changed.")
    support_rows = _required_nonnegative_receipt_integer(
        join.get("acs_support_rows"), label="ACS support rows", positive=True
    )
    clone_counts = _mapping(
        join.get("acs_support_rows_by_clone_index"),
        label="ACS support rows by clone index",
    )
    if set(clone_counts) != {"0", "1", "2"} or sum(
        _required_nonnegative_receipt_integer(
            count, label="ACS support clone rows"
        )
        for count in clone_counts.values()
    ) != support_rows:
        raise ValueError("US release weeks-worked ACS clone-count receipt changed.")
    semantic_key_sha256 = join.get("semantic_key_sha256")
    if not isinstance(semantic_key_sha256, str) or not _SHA256_PATTERN.fullmatch(
        semantic_key_sha256
    ):
        raise ValueError("US release weeks-worked semantic-key digest changed.")
    mapping = _mapping(receipt["mapping"], label="mapping")
    recode = _mapping(mapping.get("acs_blank_recode"), label="ACS blank recode")
    if recode.get("owner") != "Microcosm" or recode.get("output") != 0:
        raise ValueError("US release weeks-worked ACS structural recode changed.")
    if mapping.get("conflicting_preexisting_values") != 0:
        raise ValueError("US release weeks-worked conflict receipt is nonzero.")
    source_value_sha256 = mapping.get("canonical_source_value_sha256")
    if not isinstance(source_value_sha256, str) or not _SHA256_PATTERN.fullmatch(
        source_value_sha256
    ):
        raise ValueError("US release weeks-worked source-value digest changed.")


def _required_nonnegative_receipt_integer(
    value: object,
    *,
    label: str,
    positive: bool = False,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"US release weeks-worked receipt {label} must be integral.")
    if value < int(positive):
        qualifier = "positive" if positive else "nonnegative"
        raise ValueError(
            f"US release weeks-worked receipt {label} must be {qualifier}."
        )
    return value


def _source_value_sha256(person: pd.DataFrame) -> str:
    required = {
        support_channel_column("person"),
        support_source_id_column("person"),
        _OUTPUT,
    }
    missing = sorted(required - set(person.columns))
    if missing:
        raise ValueError(
            "US release weeks-worked source-value digest lacks column(s): "
            f"{missing}."
        )
    channel_column = support_channel_column("person")
    source_column = support_source_id_column("person")
    channels = person[channel_column].astype(str)
    if set(channels.unique()) != {_ASEC_CHANNEL, _ACS_CHANNEL}:
        raise ValueError(
            "US release weeks-worked source-value digest requires exact "
            "ASEC/ACS channels."
        )
    source_ids = _required_integral_domain(
        person[source_column],
        label="source-value person_source_id",
        minimum=0,
        maximum=np.iinfo(np.int64).max,
    )
    weeks = _required_integral_domain(
        person[_OUTPUT],
        label="source-value weeks_worked",
        minimum=0,
        maximum=52,
    )
    values = pd.DataFrame(
        {
            "source_channel": channels,
            "person_source_id": source_ids,
            "weeks_worked": weeks,
        }
    )
    disagreement = (
        values.groupby(["source_channel", "person_source_id"], sort=False)[
            "weeks_worked"
        ]
        .nunique(dropna=False)
        .gt(1)
    )
    if disagreement.any():
        raise ValueError(
            "US release weeks-worked source-value digest found clone disagreement."
        )
    canonical = (
        values.drop_duplicates(["source_channel", "person_source_id"])
        .sort_values(["source_channel", "person_source_id"], kind="stable")
        .reset_index(drop=True)
    )
    return hashlib.sha256(
        "".join(
            f"{channel}:{int(source_id)}:{int(value)}\n"
            for channel, source_id, value in canonical.itertuples(
                index=False, name=None
            )
        ).encode()
    ).hexdigest()


def _column_diff_receipt(before: Frame, after: Frame) -> dict[str, object]:
    if before.schema != after.schema:
        raise ValueError("US release weeks-worked stage changed the frame schema.")
    if before.entities != after.entities or before.links != after.links:
        raise ValueError("US release weeks-worked stage changed table inventory.")
    if before.weighted_entities != after.weighted_entities:
        raise ValueError("US release weeks-worked stage changed weight inventory.")

    changed: list[str] = []
    for entity in before.entities:
        before_table = before.table(entity)
        after_table = after.table(entity)
        before_columns = list(before_table.columns)
        after_columns = list(after_table.columns)
        extra = [column for column in after_columns if column not in before_columns]
        missing = [column for column in before_columns if column not in after_columns]
        if missing or extra not in ([], [_OUTPUT] if entity == "person" else []):
            raise ValueError(
                "US release weeks-worked stage changed column inventory for "
                f"{entity}: missing={missing}, extra={extra}."
            )
        for column in before_columns:
            if not before_table[column].equals(after_table[column]):
                changed.append(f"{entity}.{column}")
        if entity == "person" and _OUTPUT in extra:
            changed.append("person.weeks_worked")
    for link in before.links:
        if not before.link(link).equals(after.link(link)):
            raise ValueError(f"US release weeks-worked stage changed link {link!r}.")
    for entity in before.weighted_entities:
        left = before.weights_for(entity)
        right = after.weights_for(entity)
        if (
            left.kind != right.kind
            or left.values.dtype != right.values.dtype
            or left.values.shape != right.values.shape
            or left.values.tobytes() != right.values.tobytes()
        ):
            raise ValueError(
                f"US release weeks-worked stage changed {entity!r} weights."
            )
    if not before.strata.equals(after.strata):
        raise ValueError("US release weeks-worked stage changed strata.")
    if before.mass_log != after.mass_log:
        raise ValueError("US release weeks-worked stage changed mass log.")
    if before.metadata != after.metadata:
        raise ValueError("US release weeks-worked stage changed frame metadata.")

    before_person = before.table("person")
    after_person = after.table("person")
    common_nonweeks = [column for column in before_person if column != _OUTPUT]
    before_digest = _table_sha256(before_person.loc[:, common_nonweeks])
    after_digest = _table_sha256(after_person.loc[:, common_nonweeks])
    if before_digest != after_digest:
        raise ValueError("US release weeks-worked non-output digest changed.")
    return {
        "allowed_changed_column": "person.weeks_worked",
        "changed_columns": changed,
        "non_weeks_person_sha256_before": before_digest,
        "non_weeks_person_sha256_after": after_digest,
        "non_person_entity_tables_verified": len(before.entities) - 1,
        "link_tables_verified": len(before.links),
        "weight_vectors_verified": len(before.weighted_entities),
        "strata_verified": True,
        "mass_log_verified": True,
        "metadata_verified": True,
    }


def _validated_pool_identity(value: Mapping[str, object]) -> dict[str, object]:
    required = {"period", "pool_h5_sha256", "pool_manifest_sha256"}
    if set(value) != required:
        raise ValueError(
            "US release weeks-worked authenticated pool identity must contain "
            f"exactly {sorted(required)}."
        )
    if value.get("period") != 2024:
        raise ValueError("US release weeks-worked pool period must be 2024.")
    result = {"period": 2024}
    for field in ("pool_h5_sha256", "pool_manifest_sha256"):
        raw = value.get(field)
        if not isinstance(raw, str) or not _SHA256_PATTERN.fullmatch(raw):
            raise ValueError(
                f"US release weeks-worked pool identity {field} is malformed."
            )
        result[field] = raw
    return result


def _source_year_counts(person: pd.DataFrame) -> dict[str, int]:
    if "source_year" not in person:
        raise ValueError("ASEC release weeks rows lack source_year provenance.")
    years = _required_integral_domain(
        person["source_year"],
        label="ASEC source_year",
        minimum=1900,
        maximum=2024,
    )
    return {
        str(int(year)): int(count)
        for year, count in years.value_counts().sort_index().items()
    }


def _required_integral_domain(
    values: pd.Series,
    *,
    label: str,
    minimum: int,
    maximum: int,
) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    array = numeric.to_numpy(dtype=np.float64)
    if (
        numeric.isna().any()
        or not np.isfinite(array).all()
        or not np.equal(array, np.floor(array)).all()
        or (array < minimum).any()
        or (array > maximum).any()
    ):
        raise ValueError(
            f"{label} must contain finite integral values in [{minimum}, {maximum}]."
        )
    return pd.Series(array.astype(np.int64), index=values.index)


def _required_blank_or_integral_domain(
    values: pd.Series,
    *,
    label: str,
    minimum: int,
    maximum: int,
) -> tuple[pd.Series, pd.Series]:
    blank = values.isna()
    numeric = pd.to_numeric(values, errors="coerce")
    nonblank = ~blank
    array = numeric.loc[nonblank].to_numpy(dtype=np.float64)
    invalid = numeric.isna() & nonblank
    if (
        invalid.any()
        or not np.isfinite(array).all()
        or not np.equal(array, np.floor(array)).all()
        or (array < minimum).any()
        or (array > maximum).any()
    ):
        raise ValueError(
            f"{label} must be blank or contain finite integral values in "
            f"[{minimum}, {maximum}]."
        )
    return numeric, blank


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"US release weeks-worked receipt {label} is malformed.")
    return value


def _table_sha256(table: pd.DataFrame) -> str:
    header = {
        "columns": [str(column) for column in table.columns],
        "dtypes": [str(table[column].dtype) for column in table.columns],
        "index_type": type(table.index).__name__,
    }
    digest = hashlib.sha256(
        json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
    )
    digest.update(
        pd.util.hash_pandas_object(table, index=True).to_numpy(dtype="<u8").tobytes()
    )
    return digest.hexdigest()


def _canonical_sha256(value: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            _json_ready(value),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _json_ready(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(nested) for key, nested in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_ready(nested) for nested in value]
    if isinstance(value, np.generic):
        return value.item()
    return value
