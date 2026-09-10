"""Executable, development-only NZ transfer through shared Frame/fit/calibrate.

The donor is synthetic. Published NZ population margins are real observations;
their calibration does not turn invented support into observed NZ microdata.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from microcosm.build.nz_policy import accommodation_supplement_input_coverage
from microcosm.build.stochastic_assignment import (
    sample_categorical_from_counts,
    stable_identity_uniforms,
)
from microcosm.build.transfer import (
    ScaleMeasurementsKernel,
    TransferSourceKernel,
    json_bytes,
)
from microcosm.calibrate.kernels import CALIBRATE_ADAM
from microcosm.fit.kernels import QRF_KERNEL
from microcosm.frame import EntitySchema, Frame, wsum
from microcosm.graph import (
    Capabilities,
    ContentStore,
    Determinism,
    Graph,
    KernelBase,
    KernelContext,
    KernelRegistry,
    KernelResult,
    KernelRole,
    Node,
    Owned,
    Slice,
    SourceRef,
    StructuralDelta,
    WeightTransition,
    compile_graph,
    graph_to_json,
    run_graph,
    source_hash,
)

NZ_SCHEMA = EntitySchema(group_entities=("household", "family"))
PERSON_MAPPINGS = (
    ("fixture_age", "age"),
    ("fixture_annual_earnings_usd", "donor_annual_earnings_usd"),
    *(
        (f"person_{s}", f"donor_person_{s}")
        for s in (
            "spine_source_id",
            "source_id",
            "support_channel",
            "support_clone_index",
        )
    ),
)
HOUSEHOLD_MAPPINGS = (
    ("survey_geography_origin_key", "survey_geography_origin_key"),
    ("donor_state_code", "donor_state_code"),
    ("fixture_weekly_rent_usd", "donor_weekly_rent_usd"),
    ("fixture_asset_stock_usd", "donor_asset_stock_usd"),
    ("is_donor", "is_donor"),
    ("is_recipient", "is_recipient"),
    *(
        (f"household_{s}", f"donor_household_{s}")
        for s in (
            "spine_source_id",
            "source_id",
            "support_channel",
            "support_clone_index",
        )
    ),
)


def _frame(context: KernelContext) -> Frame:
    person = context.tables["person"]
    tables = {"person": person}
    for entity in NZ_SCHEMA.group_entities:
        tables[entity] = context.tables.get(
            entity,
            pd.DataFrame({f"{entity}_id": np.unique(person[f"person_{entity}_id"])}),
        )
    # Only household weights are explicit; family/person inherit via links.
    return Frame(
        tables, NZ_SCHEMA, {"household": context.weights["household"]}, context.strata
    )


class GeographyKernel(KernelBase):
    ref = "transfer.recipient_geography_fixture@1"
    capabilities = Capabilities(
        determinism=Determinism.DETERMINISTIC, dependencies=("numpy", "pandas", "scipy")
    )

    def implementation_hash(self):
        from microcosm.graph import source_hash

        return source_hash(
            type(self),
            stable_identity_uniforms,
            dependencies=self.capabilities.dependencies,
        )

    def run(self, context):
        table = context.tables["household"]
        keys = [
            json.dumps(["NZ", origin, int(clone)], separators=(",", ":"))
            for origin, clone in zip(
                table.survey_geography_origin_key,
                table.donor_household_support_clone_index,
                strict=True,
            )
        ]
        draws = stable_identity_uniforms(keys, seed=910, salt="nz-fixture-region-2025")
        regions = sample_categorical_from_counts(
            draws, counts={r: 1 for r in context.params["regions"]}
        )
        # These are named synthetic support atoms, NOT an SAU2017/AS crosswalk.
        atoms = [f"fixture-regc2025-{r}" for r in regions]
        ids = pd.Index(table.household_id)
        return KernelResult(
            columns={
                ("household", "nz_region"): pd.Series(
                    regions, index=ids, dtype="string"
                ),
                ("household", "nz_atom"): pd.Series(atoms, index=ids, dtype="string"),
            },
            receipt={
                "atomic_system": "synthetic_region_support_atoms",
                "geography_vintage": "REGC2025",
                "method": "uniform support proposal, stable origin key + clone; calibration sets representation",
                "as_area_computable": False,
                "us_geography": "provenance only",
            },
        )


class HouseholdMeasuresKernel(KernelBase):
    ref = "transfer.household_measures@1"
    capabilities = Capabilities(
        determinism=Determinism.DETERMINISTIC, dependencies=("numpy", "pandas")
    )

    def implementation_hash(self):
        return source_hash(
            type(self), Frame, EntitySchema, dependencies=self.capabilities.dependencies
        )

    def run(self, context):
        frame = _frame(context)
        person = frame.table("person")
        region = frame.broadcast("nz_region")
        output = {}
        for target in json.loads(context.params["targets_json"])["targets"]:
            mask = np.ones(len(person), dtype=bool)
            if target["geography"]["level"] == "region":
                mask &= region.to_numpy() == target["geography"]["code"]
            if "age" in target:
                mask &= person.age.to_numpy() >= target["age"]["lower_inclusive"]
                upper = target["age"].get("upper_exclusive")
                if upper is not None:
                    mask &= person.age.to_numpy() < upper
            name = target["id"]
            table = person.copy()
            table[name] = mask.astype(float)
            local = Frame(
                {
                    "person": table,
                    **{e: frame.table(e) for e in NZ_SCHEMA.group_entities},
                },
                NZ_SCHEMA,
                {"household": frame.weights_for("household")},
                frame.strata,
            )
            placed = local.place(name, "household")
            output["household", name] = pd.Series(
                placed.table("household")[name].to_numpy(),
                index=pd.Index(placed.table("household").household_id),
                dtype="float64",
            )
        return KernelResult(
            columns=output,
            receipt={
                "aggregation": "Frame.place(person indicator, household, sum)",
                "weight_source": "household",
            },
        )


class DiagnosticsKernel(KernelBase):
    ref = "transfer.fit_holdout_coverage@1"
    capabilities = Capabilities(
        determinism=Determinism.DETERMINISTIC,
        role=KernelRole.GATE,
        dependencies=("numpy", "pandas"),
    )

    def implementation_hash(self):
        return source_hash(
            type(self),
            accommodation_supplement_input_coverage,
            Frame,
            wsum,
            json_bytes,
            dependencies=self.capabilities.dependencies,
        )

    def run(self, context):
        frame = _frame(context)
        targets = json.loads(context.params["targets_json"])
        rows = []
        for target in targets["targets"]:
            estimate = wsum(frame, target["id"])
            residual = estimate - target["value"]
            rows.append(
                {
                    **target,
                    "estimate": estimate,
                    "residual": residual,
                    "relative_error": residual / target["value"],
                }
            )
        coverage = accommodation_supplement_input_coverage(frame)
        report = {
            "status": "development_fixture_only",
            "calibration": rows,
            "source": targets["source"],
            "period": targets["period"],
            "coverage": coverage,
            "fit_tolerance_relative": 0.05,
            "fit_pass": all(
                abs(r["relative_error"]) <= 0.05 for r in rows if r["role"] == "fit"
            ),
            "holdout_max_abs_relative_error": max(
                abs(r["relative_error"]) for r in rows if r["role"] == "holdout"
            ),
            "limitations": [
                "No approved US donor artifact",
                "Family, joint income, assets and rent are synthetic assumptions",
                "No AS atomic-geography crosswalk or complete AS inputs",
                "No final AS entitlement composition bound",
                "No take-up estimate",
                "Population observations are June 2025, not an uprated 2026/27 forecast",
            ],
            "rounding_and_outside_regions": targets["measurement"],
        }
        return KernelResult(
            artifacts={"report.json": json_bytes(report)},
            receipt={
                "outcome": "evidence_absent",
                "evidence": report,
                "reason": "Synthetic support and incomplete AS inputs prevent certification regardless of demographic fit",
            },
        )


def build_graph(
    donor: Frame,
    targets: dict,
    *,
    epochs: int = 50,
    donor_namespace: str = "fixture-declaration-only",
) -> Graph:
    # Compile-time root ownership comes from the exact projection kernel result.
    # This dry projection is also validated during graph execution from the
    # content-verified source; no donor data are supplied out-of-band to kernels.
    total = next(
        t["value"] for t in targets["targets"] if t["role"] == "accounting_check"
    )
    source_person_mass = float(donor.resolve_weights("person").values.sum())
    params = {
        "donor_namespace": donor_namespace,
        "recipient_country": "NZ",
        "recipient_group": "family",
        "membership_column": "recipient_family_id",
        "family_definition": "explicit_synthetic_nuclear_family_and_unrelated_adult_split",
        "person_mappings": PERSON_MAPPINGS,
        "household_mappings": HOUSEHOLD_MAPPINGS,
        "design_scale": total / source_person_mass,
    }
    from microcosm.graph.population import token_for_dtype

    root_outputs = [
        Owned(
            "person", destination, token_for_dtype(donor.table("person")[source].dtype)
        )
        for source, destination in PERSON_MAPPINGS
    ]
    root_outputs += [
        Owned(
            "household",
            destination,
            token_for_dtype(donor.table("household")[source].dtype),
        )
        for source, destination in HOUSEHOLD_MAPPINGS
    ]
    root_outputs += [
        Owned("person", f"donor_person_{e}_id", "string")
        for e in donor.schema.group_entities
    ]
    root_outputs += [
        Owned("person", "donor_person_key", "string"),
        Owned("household", "donor_household_key", "string"),
        Owned("household", "donor_household_weight", "float64"),
        Owned("family", "family_definition", "string"),
    ]
    target_json = json.dumps(targets, sort_keys=True, separators=(",", ":"))
    names = tuple(t["id"] for t in targets["targets"])
    nodes = [
        Node(
            "nz_entities",
            TransferSourceKernel.ref,
            sources=("donor",),
            structural=StructuralDelta.CREATE,
            outputs=tuple(root_outputs),
            params=params,
            description="Explicit NZ fixture families from full synthetic US Frame; complete donor retained; policy output allowlist is empty",
        ),
        Node(
            "nz_geography",
            GeographyKernel.ref,
            population="nz_entities",
            inputs=(
                Slice(
                    "household",
                    (
                        "survey_geography_origin_key",
                        "donor_household_support_clone_index",
                    ),
                ),
            ),
            outputs=(
                Owned("household", "nz_region", "string"),
                Owned("household", "nz_atom", "string"),
            ),
            params={
                "regions": tuple(
                    t["geography"]["code"]
                    for t in targets["targets"]
                    if t["id"].startswith("nz_region_")
                )
            },
            description="Recipient REGC2025 support atoms; not valid AS areas",
        ),
        Node(
            "measurement_bridge",
            ScaleMeasurementsKernel.ref,
            population="nz_entities",
            inputs=(
                Slice("person", ("donor_annual_earnings_usd",)),
                Slice("household", ("donor_weekly_rent_usd", "donor_asset_stock_usd")),
            ),
            outputs=(
                Owned("person", "annual_earnings_nzd", "float64"),
                Owned("household", "weekly_rent_nzd", "float64"),
                Owned("household", "asset_training_nzd", "float64"),
            ),
            params={
                "mappings": (
                    (
                        "person",
                        "donor_annual_earnings_usd",
                        "annual_earnings_nzd",
                        1.6,
                        "USD annual CY2024",
                        "NZD annual CY2025",
                        "CY2025",
                        "illustrative fixture scale; no verified FX/uprating",
                    ),
                    (
                        "household",
                        "donor_weekly_rent_usd",
                        "weekly_rent_nzd",
                        1.6,
                        "USD weekly hypothetical",
                        "NZD weekly hypothetical",
                        "snapshot",
                        "illustrative fixture scale; no NZ rent observations",
                    ),
                    (
                        "household",
                        "donor_asset_stock_usd",
                        "asset_training_nzd",
                        1.6,
                        "USD hypothetical stock",
                        "NZD hypothetical stock",
                        "snapshot",
                        "fixture asset concept; not AS assessable cash assets",
                    ),
                )
            },
            description="Separate currency/period assumptions for earnings, rent and asset stock; never an AS-input equivalence claim",
        ),
        Node(
            "asset_imputation",
            QRF_KERNEL.ref,
            population="nz_entities",
            inputs=(
                Slice(
                    "household",
                    (
                        "weekly_rent_nzd",
                        "asset_training_nzd",
                        "is_donor",
                        "is_recipient",
                    ),
                ),
            ),
            outputs=(
                Owned(
                    "household",
                    "imputed_asset_stock_nzd",
                    "float64",
                    rows="is_recipient",
                ),
            ),
            params={"donor_target": "asset_training_nzd", "n_estimators": 12},
            description="Real weight-aware microcosm.fit QRF; synthetic USD donor asset structure, not observed NZ wealth or AS cash assets",
        ),
        Node(
            "target_measures",
            HouseholdMeasuresKernel.ref,
            population="nz_entities",
            inputs=(Slice("person", ("age",)), Slice("household", ("nz_region",))),
            outputs=tuple(Owned("household", name, "float64") for name in names),
            params={"targets_json": target_json},
            description="Household contributions to person-level targets through shared Frame.place",
        ),
        Node(
            "nz_calibration",
            CALIBRATE_ADAM.ref,
            base="nz_entities",
            structural=StructuralDelta.REWEIGHT,
            weights=WeightTransition("household", "calibrated", "free"),
            mass="free",
            inputs=(
                Slice(
                    "household",
                    tuple(t["id"] for t in targets["targets"] if t["role"] == "fit"),
                ),
            ),
            params={
                "targets": tuple(
                    (t["id"], t["id"], None, t["value"], None)
                    for t in targets["targets"]
                    if t["role"] == "fit"
                ),
                "epochs": epochs,
                "learning_rate": 0.025,
                "max_weight_ratio": 20.0,
                "weight_anchor": "design",
                "mass": "free",
            },
            description="Shared calibrate.adam: 20 fit targets only, 12 holdouts excluded; no receipt/spending target; no pruning",
        ),
        Node(
            "nz_diagnostics",
            DiagnosticsKernel.ref,
            population="nz_calibration",
            inputs=(
                Slice("household", names),
                Slice("person", ("age",)),
                Slice("family", ("family_definition",)),
            ),
            params={"targets_json": target_json},
            description="Fit and independent regional age holdouts, complete AS root coverage, development-only gate",
        ),
    ]
    return Graph(
        country="NZ",
        sources=(
            SourceRef(
                "donor",
                "frame-store",
                "Entire six-entity synthetic donor, all support clones",
            ),
        ),
        nodes=tuple(nodes),
    )


def run_candidate(
    donor: Frame, targets: dict, output: Path, *, epochs: int = 50
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    store = ContentStore(output / "store")
    # Hash all Frame bytes using the store's authenticated representation. Each
    # output directory holds a single immutable source fixture identity.
    import tempfile

    with tempfile.TemporaryDirectory() as temporary:
        scratch = ContentStore(Path(temporary)).put_frame("0" * 64, donor)
        digest = hashlib.sha256()
        for path in sorted(scratch.rglob("*")):
            if path.is_file():
                digest.update(str(path.relative_to(scratch)).encode())
                digest.update(path.read_bytes())
    source_key = digest.hexdigest()
    source_path = store.put_frame(source_key, donor)
    graph = build_graph(donor, targets, epochs=epochs, donor_namespace=source_key)
    registry = KernelRegistry()
    for kernel in (
        TransferSourceKernel(),
        ScaleMeasurementsKernel(),
        GeographyKernel(),
        HouseholdMeasuresKernel(),
        DiagnosticsKernel(),
        CALIBRATE_ADAM,
        QRF_KERNEL,
    ):
        registry.register(kernel)
    compiled = compile_graph(graph)
    manifest = run_graph(
        compiled, sources={"donor": source_path}, store=store, kernels=registry
    )
    manifest.save(output / "manifest.json")
    (output / "graph.json").write_text(graph_to_json(graph))
    report = dict(manifest.nodes["nz_diagnostics"].receipt["evidence"])
    report.update(
        {
            "manifest_key": manifest.key,
            "source_frame_key": source_key,
            "rows": {
                e: manifest.populations["nz_calibration"].n(e)
                for e in NZ_SCHEMA.entities
            },
        }
    )
    # Frozen receipt mappings become ordinary JSON via the canonical graph
    # manifest representation, preserving full-precision numeric values.
    from microcosm.graph.canonical import canonical_json

    (output / "report.json").write_bytes(canonical_json(report) + b"\n")
    final = manifest.populations["nz_calibration"]
    final_key = hashlib.sha256((manifest.key + ":candidate-frame").encode()).hexdigest()
    store.put_frame(final_key, final)
    (output / "candidate.json").write_bytes(
        json_bytes(
            {
                "status": "development_fixture_only",
                "frame_key": final_key,
                "manifest_key": manifest.key,
                "release_certified": False,
            }
        )
    )
    return {
        "graph": graph,
        "compiled": compiled,
        "manifest": manifest,
        "report": report,
        "store": store,
    }
