"""Actual Axiom execution through the graph, export, and shared quality (BE).

A bounded engineering seam on nine invented persons in four invented
households. Nothing here is a Belgian tax-benefit model, a SILC population, or
a release candidate.

What is real:

- The measure node executes the canonical ``rulespec-be`` CIR 1992 article 130
  rate-scale module through :class:`~microcosm.frame.adapters.axiom.AxiomEngine`
  and the native Axiom dense extension. No formula is restated here.
- The source node decodes through the production ``csv-tables`` codec, and the
  reweight node is the shared, country-neutral ``calibrate.adam@1`` kernel run
  unmodified on explicit invented count margins.
- Export and reload go through the real
  :class:`~microcosm.frame.adapters.axiom.AxiomEntityTableDataset`, and the
  quality artifacts come from the shared ``quality_aggregates`` producer.

What is not claimed: Belgian tax-benefit coverage, SILC semantics, any mapping
from a wage concept to taxable income (the module's single input is supplied
directly as an invented figure), commune assignment (the declared
``clone_assign_communes`` spine kernel is unimplemented and this slice does not
stand in for it), demographic representativeness, or release eligibility. The
posture is fixed at ``synthetic_engineering_not_release`` and
``release_eligible`` is ``False`` everywhere it appears.
"""

from __future__ import annotations

import importlib.util
import json
import os
from collections.abc import Mapping
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from microcosm.build.country_spec import load_country_spec
from microcosm.build.quality_aggregates import (
    DistributionBin,
    DistributionSpec,
    GeographySpec,
    population_distributions,
    population_support,
)
from microcosm.calibrate.kernels import CalibrateAdamKernel
from microcosm.frame import ExportContract, Frame, WeightKind, Weights
from microcosm.frame.adapters.axiom import (
    BE_SCHEMA,
    AxiomEngine,
    AxiomEntityTableDataset,
)
from microcosm.graph import (
    Capabilities,
    ContentStore,
    Determinism,
    Graph,
    KernelBase,
    KernelRegistry,
    KernelResult,
    Node,
    Numeric,
    Owned,
    SeedSource,
    Slice,
    SourceRef,
    StructuralDelta,
    WeightTransition,
    compile_graph,
    load_source,
    run_graph,
    source_hash,
)

# --------------------------------------------------------------------------
# Guards. The Axiom engine is not on PyPI and CI installs neither it nor a
# rulespec-be checkout, so this file collects and skips there.
# --------------------------------------------------------------------------

_ENGINE_INSTALLED = importlib.util.find_spec("axiom_rules_engine") is not None
if _ENGINE_INSTALLED:
    from axiom_rules_engine.dense import NativeCompiledDenseProgram

    _DENSE_AVAILABLE = NativeCompiledDenseProgram is not None
else:
    _DENSE_AVAILABLE = False

RULESPEC_BE = os.environ.get("POPULACE_RULESPEC_BE")
MODULE_RELATIVE = "be/statutes/income_tax/individual/rate_scale.yaml"

pytestmark = [
    pytest.mark.skipif(
        not _DENSE_AVAILABLE,
        reason="axiom_rules_engine (with the dense native extension) is not installed",
    ),
    pytest.mark.skipif(
        importlib.util.find_spec("tables") is None,
        reason="pytables (microcosm-frame[axiom]) is not installed",
    ),
    pytest.mark.skipif(
        importlib.util.find_spec("torch") is None,
        reason="torch (the shared calibrate.adam@1 solver) is not installed",
    ),
    pytest.mark.skipif(
        RULESPEC_BE is None,
        reason="set POPULACE_RULESPEC_BE to a rulespec-be checkout to run",
    ),
]

# --------------------------------------------------------------------------
# Pins and invented facts. Every legal fact is read, never restated.
# --------------------------------------------------------------------------

POSTURE = "synthetic_engineering_not_release"

#: The module's own only version is ``effective_from: 2025-01-01`` (CIR 1992
#: article 130, income year 2025 / assessment year 2026). Executing it at the
#: BE bundle's declared ``dataset_run.target_period`` of 2023 is refused by the
#: engine; ``test_module_refuses_the_declared_bundle_period`` asserts that
#: rather than letting a convenient period be chosen silently.
LEGAL_PERIOD = 2025
BUNDLE_TARGET_PERIOD = 2023

TAXABLE_INCOME = "belgium_pit_taxable_income"
BASE_TAX = "belgium_pit_article_130_base_tax"

#: Values already pinned by ``TestBelgianPilotSlice`` on main, reused here as
#: an independently reviewed cross-check rather than a fresh hand computation.
REVIEWED_INCOMES = (10_000.0, 30_000.0, 60_000.0)
REVIEWED_BASE_TAX = (2_500.0, 9_612.0, 23_620.0)

#: NUTS1 ids the invented rows carry. ``UNKNOWN`` is declared but deliberately
#: unobserved: the BE catalog declares ``person.region_nuts1`` non-nullable, so
#: the fixture carries no null, and the bucket must still stay visible at zero.
NUTS1_IDS = ("BE1", "BE2", "BE3")
NUTS1_UNKNOWN = "UNKNOWN"

REGION_COLUMN = "region_nuts1"
HOUSEHOLD_REGION_COLUMN = "household_region_nuts1"
COUNT_COLUMN = "synthetic_household_unit_count"
FILTER_COLUMN = "synthetic_household_in_be2"

#: Invented margins. Neither is an official Belgian statistic.
NATIONAL_COUNT_MULTIPLIER = 1.25
BE2_COUNT_MULTIPLIER = 1.60

SOURCE_NAME = "be_synthetic_population"
CREATE_NODE = "create_be_synthetic_population"
COUNT_NODE = "declare_synthetic_household_unit_count"
MEASURE_NODE = "axiom_article_130_base_tax"
CALIBRATION_NODE = "synthetic_household_count_calibration"


def _module_path() -> Path:
    return Path(RULESPEC_BE) / MODULE_RELATIVE


def _adapter(contract: ExportContract | None = None) -> AxiomEngine:
    """The real adapter over the canonical module and its explicit root."""
    return AxiomEngine(
        _module_path(),
        BE_SCHEMA,
        rulespec_roots=(Path(RULESPEC_BE),),
        contract=contract,
        arithmetic="decimal",
    )


def _plain(value):
    """Convert executor receipts (mappingproxy/tuple) to plain JSON types."""
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_plain(item) for item in value]
    return value


def _json(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


# --------------------------------------------------------------------------
# The invented source, written as CSVs the production codec decodes.
# --------------------------------------------------------------------------

PERSON_ROWS = (
    # person_id, household, region, taxable income
    (1, 1, "BE1", 10_000.0),
    (2, 1, "BE1", 30_000.0),
    (3, 2, "BE2", 60_000.0),
    (4, 2, "BE2", 0.0),  # an observed zero, not a missing value
    (5, 2, "BE2", 16_320.0),
    (6, 3, "BE3", 28_800.0),
    (7, 3, "BE3", 49_840.0),
    (8, 4, "BE2", 100_000.0),
    (9, 4, "BE2", 5_000.0),
)
HOUSEHOLD_ROWS = (
    # household_id, region, design weight
    (1, "BE1", 1_200.0),
    (2, "BE2", 800.0),
    (3, "BE3", 950.0),
    (4, "BE2", 600.0),
)


def _write_invented_source(path: Path) -> Path:
    """Write the invented CSV tables the ``csv-tables`` codec reads.

    No survey microdata is opened, downloaded, or referenced. Every figure is
    invented for this test.
    """
    path.mkdir(parents=True)
    person = pd.DataFrame(
        {
            "person_id": [row[0] for row in PERSON_ROWS],
            "person_household_id": [row[1] for row in PERSON_ROWS],
            REGION_COLUMN: [row[2] for row in PERSON_ROWS],
            TAXABLE_INCOME: [row[3] for row in PERSON_ROWS],
        }
    )
    household = pd.DataFrame(
        {
            "household_id": [row[0] for row in HOUSEHOLD_ROWS],
            HOUSEHOLD_REGION_COLUMN: [row[1] for row in HOUSEHOLD_ROWS],
            "design_weight": [row[2] for row in HOUSEHOLD_ROWS],
        }
    )
    person.to_csv(path / "person.csv", index=False)
    household.to_csv(path / "household.csv", index=False)
    (path / "schema.json").write_text(
        json.dumps(
            {
                "schema": {"person_entity": "person", "group_entities": ["household"]},
                "tables": {"person": "person.csv", "household": "household.csv"},
                "dtypes": {
                    "person": {
                        "person_id": "int64",
                        "person_household_id": "int64",
                        REGION_COLUMN: "string",
                        TAXABLE_INCOME: "float64",
                    },
                    "household": {
                        "household_id": "int64",
                        HOUSEHOLD_REGION_COLUMN: "string",
                        "design_weight": "float64",
                    },
                },
                "weights_table": "household.csv",
                "weights": [
                    {
                        "entity": "household",
                        "kind": "design",
                        "column": "design_weight",
                    }
                ],
                "posture": POSTURE,
                "note": (
                    "Invented persons and households. Not SILC, not a Belgian "
                    "population, not representative of anything."
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return path


# --------------------------------------------------------------------------
# Kernels. Only the source and measure kernels are test-owned; the reweight
# node runs the shared production calibrator unmodified.
# --------------------------------------------------------------------------


class BeSyntheticSourceKernel(KernelBase):
    """CREATE: decode the invented tables through the production codec."""

    ref = "be.test.synthetic_population@1"
    capabilities = Capabilities(
        determinism=Determinism.DETERMINISTIC,
        numeric=Numeric.BITWISE,
        seed_source=SeedSource.NONE,
        structural=StructuralDelta.CREATE,
        dependencies=("numpy", "pandas"),
    )

    def run(self, context) -> KernelResult:
        if context.params.get("posture") != POSTURE:
            raise ValueError(
                f"The invented BE source refuses any posture other than {POSTURE!r}."
            )
        frame = load_source("csv-tables", context.sources[SOURCE_NAME])
        # The codec keeps the weight column on the table; the Frame's typed
        # weights are authoritative, so the duplicate physical column is
        # dropped rather than exported as if it were source data.
        household = frame.table("household").drop(columns=["design_weight"])
        frame = Frame(
            {"person": frame.table("person"), "household": household},
            BE_SCHEMA,
            {"household": frame.weights_for("household")},
            metadata={"time_period": str(LEGAL_PERIOD)},
        )
        return KernelResult(
            frame=frame,
            receipt={
                "posture": POSTURE,
                "release_eligible": False,
                "persons": frame.n("person"),
                "households": frame.n("household"),
                "codec": "csv-tables",
            },
        )


class SyntheticCountColumnKernel(KernelBase):
    """Own the invented all-ones count measure the margins are expressed on.

    Kept as its own declared node so the count column is visible as an
    engineering artifact rather than smuggled in as source data.
    """

    ref = "be.test.synthetic_unit_count@1"
    capabilities = Capabilities(
        determinism=Determinism.DETERMINISTIC,
        numeric=Numeric.BITWISE,
        seed_source=SeedSource.NONE,
        dependencies=("numpy", "pandas"),
    )

    def run(self, context) -> KernelResult:
        table = context.tables["household"]
        ids = pd.Index(table["household_id"])
        regions = table[HOUSEHOLD_REGION_COLUMN].to_numpy(dtype=object)
        return KernelResult(
            columns={
                ("household", COUNT_COLUMN): pd.Series(
                    np.ones(len(ids), dtype="float64"), index=ids
                ),
                ("household", FILTER_COLUMN): pd.Series(
                    regions == "BE2", index=ids, dtype="bool"
                ),
            },
            receipt={"posture": POSTURE, "release_eligible": False},
        )


class AxiomArticle130Kernel(KernelBase):
    """Execute the canonical rate-scale module through the real adapter.

    The kernel restates no rule: it hands the population's own taxable-income
    column to :meth:`AxiomEngine.materialize` and returns what the engine
    computed. The engine, its native dense extension, and the module are all
    pinned in the receipt.
    """

    ref = "be.test.axiom_article_130_base_tax@1"
    capabilities = Capabilities(
        determinism=Determinism.DETERMINISTIC,
        # The Axiom decimal path is exact, but the native extension is a
        # locally built artifact whose bytes this contract cannot pin across
        # machines; claim only what holds on this platform.
        numeric=Numeric.PLATFORM_BITWISE,
        seed_source=SeedSource.NONE,
        dependencies=("numpy", "pandas"),
    )

    def implementation_hash(self) -> str:
        """Bind the adapter's source and the exact module/extension bytes.

        A change to the encoded statute or to the built engine must move this
        hash, otherwise a cached node could serve results the current runtime
        no longer produces.
        """
        import axiom_rules_engine_dense

        from microcosm.frame.adapters import axiom as axiom_adapter

        base = source_hash(
            type(self),
            axiom_adapter,
            dependencies=self.capabilities.dependencies,
        )
        digest = sha256(base.encode())
        digest.update(_module_path().read_bytes())
        digest.update(Path(axiom_rules_engine_dense.__file__).read_bytes())
        return digest.hexdigest()

    def run(self, context) -> KernelResult:
        if context.params.get("posture") != POSTURE:
            raise ValueError(
                f"The Axiom measure node refuses any posture other than {POSTURE!r}."
            )
        period = context.params["period"]
        person = context.tables["person"].copy(deep=True)
        household = context.tables["household"].copy(deep=True)
        bundle = Frame(
            {"person": person, "household": household},
            BE_SCHEMA,
            {"household": context.weights["household"]},
        )
        adapter = _adapter()
        values = adapter.materialize(bundle, [BASE_TAX], period=period)[BASE_TAX]
        metadata = adapter.variable_metadata(BASE_TAX)
        import axiom_rules_engine_dense

        return KernelResult(
            columns={
                ("person", BASE_TAX): pd.Series(
                    np.asarray(values, dtype="float64"),
                    index=pd.Index(person["person_id"]),
                )
            },
            receipt={
                "posture": POSTURE,
                "release_eligible": False,
                "engine": "axiom_rules_engine dense",
                "module": MODULE_RELATIVE,
                "module_sha256": sha256(_module_path().read_bytes()).hexdigest(),
                "dense_extension_sha256": sha256(
                    Path(axiom_rules_engine_dense.__file__).read_bytes()
                ).hexdigest(),
                "arithmetic": "decimal",
                "legal_period": period,
                "variable_entity": metadata.entity,
                "variable_dtype": metadata.dtype,
                "variable_period": metadata.period,
            },
        )


def _registry() -> KernelRegistry:
    kernels = KernelRegistry()
    kernels.register(BeSyntheticSourceKernel())
    kernels.register(SyntheticCountColumnKernel())
    kernels.register(AxiomArticle130Kernel())
    # The shared, country-neutral production calibrator, unmodified.
    kernels.register(CalibrateAdamKernel())
    return kernels


# --------------------------------------------------------------------------
# The graph.
# --------------------------------------------------------------------------


def _graph(targets: tuple) -> Graph:
    source = Node(
        id=CREATE_NODE,
        kernel=BeSyntheticSourceKernel.ref,
        structural=StructuralDelta.CREATE,
        sources=(SOURCE_NAME,),
        outputs=(
            Owned("person", REGION_COLUMN, "string"),
            Owned("person", TAXABLE_INCOME, "float64"),
            Owned("household", HOUSEHOLD_REGION_COLUMN, "string"),
        ),
        params={"posture": POSTURE, "period": LEGAL_PERIOD},
        description="Invented BE-shaped persons and households; not SILC.",
    )
    counts = Node(
        id=COUNT_NODE,
        kernel=SyntheticCountColumnKernel.ref,
        population=CREATE_NODE,
        inputs=(Slice("household", (HOUSEHOLD_REGION_COLUMN,)),),
        outputs=(
            Owned("household", COUNT_COLUMN, "float64"),
            Owned("household", FILTER_COLUMN, "bool"),
        ),
        params={"posture": POSTURE},
        description="Invented all-ones count measure and a BE2 indicator.",
    )
    measure = Node(
        id=MEASURE_NODE,
        kernel=AxiomArticle130Kernel.ref,
        population=CREATE_NODE,
        inputs=(
            Slice("person", (TAXABLE_INCOME,)),
            # The Axiom adapter's BE_SCHEMA requires both entities, and the
            # only way the executor projects a household table is a declared
            # household slice; this reads the household's own region column.
            Slice("household", (HOUSEHOLD_REGION_COLUMN,)),
        ),
        outputs=(Owned("person", BASE_TAX, "float64"),),
        params={"posture": POSTURE, "period": LEGAL_PERIOD},
        citation="CIR 1992 article 130 as encoded in rulespec-be.",
    )
    calibration = Node(
        id=CALIBRATION_NODE,
        kernel=CalibrateAdamKernel.ref,
        structural=StructuralDelta.REWEIGHT,
        base=CREATE_NODE,
        inputs=(Slice("household", (COUNT_COLUMN, FILTER_COLUMN)),),
        weights=WeightTransition("household", "calibrated", mass="free"),
        mass="free",
        params={
            "epochs": 256,
            "learning_rate": 0.02,
            "mass": "free",
            "max_weight_ratio": 10.0,
            "targets": targets,
            "weight_anchor": "design",
        },
        description="Invented count margins solved by the shared calibrator.",
    )
    return Graph(
        country="be",
        sources=(
            SourceRef(
                SOURCE_NAME,
                "csv-tables",
                description="Invented engineering fixture; no survey microdata.",
            ),
        ),
        nodes=(source, counts, measure, calibration),
    )


# --------------------------------------------------------------------------
# Geography, quality, and export helpers.
# --------------------------------------------------------------------------


def _nuts1_vintage() -> str:
    """The NUTS1 vintage the BE country spec itself declares.

    Read from the package rather than spelled here, so a vintage change in the
    spec cannot leave a stale string in a quality artifact.
    """
    spec = load_country_spec("be")
    vintages = {
        reference.ledger_selector.get("geography_vintage")
        for reference in spec.target_references
        if reference.ledger_selector.get("geography_level") == "nuts1"
    }
    if len(vintages) != 1 or None in vintages:
        raise ValueError(
            f"The BE spec does not declare exactly one NUTS1 vintage: {vintages!r}."
        )
    return str(next(iter(vintages)))


def _geographies(column: str) -> tuple[GeographySpec, ...]:
    vintage = _nuts1_vintage()
    return (
        GeographySpec("national", None, vintage, {"BE": "Belgium"}),
        GeographySpec(
            "nuts1",
            column,
            vintage,
            {
                "BE1": "BE1",
                "BE2": "BE2",
                "BE3": "BE3",
                NUTS1_UNKNOWN: "Unknown NUTS1",
            },
            unknown_id=NUTS1_UNKNOWN,
        ),
    )


def _frame_from(view, *, weights: Weights | None = None) -> Frame:
    return Frame(
        {entity: view.table(entity).copy(deep=True) for entity in view.entities},
        BE_SCHEMA,
        {"household": weights or view.weights_for("household")},
        view.strata.copy(deep=True),
        mass_log=view.mass_log,
        metadata=dict(view.metadata),
    )


def _assert_household_region_agrees(frame: Frame) -> None:
    """Refuse a household region its own members do not unanimously carry.

    The frame's linkage permits the disagreement; the BE geography contract
    does not, and a quality partition built over a disagreeing column would
    silently misattribute mass.
    """
    broadcast = frame.broadcast(HOUSEHOLD_REGION_COLUMN, to="person")
    member = frame.person[REGION_COLUMN]
    if not (broadcast.to_numpy(dtype=object) == member.to_numpy(dtype=object)).all():
        raise ValueError(
            "Household NUTS1 region must be unanimously carried by its members."
        )


def _export_contract() -> ExportContract:
    """A closed contract naming exactly the input surface that may leave."""
    return ExportContract(
        required=(TAXABLE_INCOME, REGION_COLUMN, HOUSEHOLD_REGION_COLUMN),
        forbidden=(),
        optional=(COUNT_COLUMN, FILTER_COLUMN),
        formula_owned_excluded=(),
        closed=True,
    )


def _input_only(frame: Frame) -> Frame:
    """Drop the engine-owned legal output before export.

    The article 130 base tax is a formula the engine owns. Persisting it as a
    dataset column would make a derived legal result look like a model input
    and would mask any reform. The adapter refuses that write; this drops it.
    """
    person = frame.person.drop(columns=[BASE_TAX])
    return Frame(
        {"person": person, "household": frame.table("household").copy(deep=True)},
        BE_SCHEMA,
        {"household": frame.weights_for("household")},
        frame.strata.copy(deep=True),
        mass_log=frame.mass_log,
        metadata=dict(frame.metadata),
    )


def _reloaded_frame(path: Path, *, kind: WeightKind) -> Frame:
    """Rebuild a Frame from the real Axiom entity-table reader.

    The entity-table format carries the weight *values* in a
    ``household_weight`` column but no weight *kind*; ``kind`` is therefore
    supplied by the caller from the in-memory frame and is not a fact recovered
    from the file. ``test_export_does_not_persist_the_weight_kind`` pins that
    limitation.
    """
    dataset = AxiomEntityTableDataset(file_path=path)
    household = dataset.table("household")
    weights = Weights(
        values=household["household_weight"].to_numpy(dtype="float64"), kind=kind
    )
    return Frame(
        {
            "person": dataset.table("person"),
            "household": household.drop(columns=["household_weight"]),
        },
        BE_SCHEMA,
        {"household": weights},
        metadata={"time_period": str(dataset.time_period)},
    )


# --------------------------------------------------------------------------
# The run.
# --------------------------------------------------------------------------


def _run(path: Path, *, national_multiplier=NATIONAL_COUNT_MULTIPLIER, resume="auto"):
    # The graph and the HDF reader both use Python-backed strings, matching the
    # accepted UK seam, so column and value storage stays identical end to end.
    with pd.option_context("mode.string_storage", "python"):
        return _run_python_strings(
            path, national_multiplier=national_multiplier, resume=resume
        )


def _run_python_strings(path: Path, *, national_multiplier, resume):
    raw = path / "invented-be-source"
    if not raw.exists():
        _write_invented_source(raw)

    design_total = float(sum(row[2] for row in HOUSEHOLD_ROWS))
    be2_total = float(sum(row[2] for row in HOUSEHOLD_ROWS if row[1] == "BE2"))
    targets = (
        (
            "synthetic_national_household_count",
            COUNT_COLUMN,
            None,
            design_total * national_multiplier,
            None,
        ),
        (
            "synthetic_be2_household_count",
            COUNT_COLUMN,
            FILTER_COLUMN,
            be2_total * BE2_COUNT_MULTIPLIER,
            None,
        ),
    )

    compiled = compile_graph(_graph(targets))
    manifest = run_graph(
        compiled,
        sources={SOURCE_NAME: raw},
        store=ContentStore(path / "store"),
        kernels=_registry(),
        resume=resume,
    )
    baseline = _frame_from(manifest.population(CREATE_NODE))
    calibrated = _frame_from(manifest.population(CALIBRATION_NODE))
    _assert_household_region_agrees(calibrated)

    adapter = _adapter(_export_contract())
    output = path / f"synthetic-be-{manifest.receipt(CALIBRATION_NODE).key[:16]}.h5"
    adapter.write_dataset(_input_only(calibrated), output, period=LEGAL_PERIOD)
    population_sha = sha256(output.read_bytes()).hexdigest()
    reloaded = _reloaded_frame(output, kind=calibrated.weights_for("household").kind)

    identity = {
        "candidate_release_id": "be-synthetic-"
        + manifest.receipt(CALIBRATION_NODE).key[:16],
        "population_sha256": population_sha,
        "period": str(LEGAL_PERIOD),
    }
    support = {
        entity: population_support(
            reloaded,
            entity=entity,
            geography_specs=_geographies(
                REGION_COLUMN if entity == "person" else HOUSEHOLD_REGION_COLUMN
            ),
            **identity,
        )
        for entity in reloaded.entities
    }
    distributions = population_distributions(
        reloaded,
        distributions=(
            DistributionSpec(
                TAXABLE_INCOME,
                "Invented taxable-income input (engine input, not a statutory band)",
                "person",
                "EUR",
                "synthetic-be-income-bins-v1",
                (
                    DistributionBin("under20000", None, 20_000),
                    DistributionBin("20000to50000", 20_000, 50_000),
                    DistributionBin("50000plus", 50_000, None),
                ),
            ),
        ),
        geography_specs=_geographies(REGION_COLUMN),
        **identity,
    )
    record = {
        "schema_version": "microcosm.be.synthetic_axiom_graph_quality.v1",
        "posture": POSTURE,
        "release_eligible": False,
        "country": "be",
        "routed_to_country_release": None,
        "engine": "axiom_rules_engine dense (rulespec-be)",
        "legal_period": LEGAL_PERIOD,
        "bundle_declared_target_period": BUNDLE_TARGET_PERIOD,
        "commune_nis_layer": "absent: clone_assign_communes is unimplemented",
        "nuts1_vintage": _nuts1_vintage(),
        "reload_string_storage": "python",
        "synthetic_targets": targets,
        "graph_nodes": {
            name: {"key": receipt.key, "hit": receipt.hit}
            for name, receipt in manifest.nodes.items()
        },
        "measure": _plain(manifest.receipt(MEASURE_NODE).receipt),
        "calibration": _plain(manifest.receipt(CALIBRATION_NODE).receipt),
        "population_sha256": population_sha,
        "support": support,
        "distributions": distributions,
    }
    (path / "synthetic-be-quality.json").write_bytes(_json(record))
    return {
        "baseline": baseline,
        "calibrated": calibrated,
        "reloaded": reloaded,
        "manifest": manifest,
        "compiled": compiled,
        "record": record,
        "output": output,
        "targets": targets,
    }


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """One cold run shared by the read-only assertions.

    Module scope keeps the slice inside its resource budget: the engine, torch,
    and the solve are exercised once, and the tests that need a second run ask
    for one explicitly.
    """
    return _run(tmp_path_factory.mktemp("be-cold"))


# --------------------------------------------------------------------------
# Real execution.
# --------------------------------------------------------------------------


def test_graph_output_is_actual_axiom_execution(run) -> None:
    """The graph's column equals a direct adapter call on the same rows."""
    person = run["calibrated"].person
    direct = _adapter().materialize(
        _input_only(run["calibrated"]), [BASE_TAX], period=LEGAL_PERIOD
    )[BASE_TAX]
    np.testing.assert_array_equal(person[BASE_TAX].to_numpy(), np.asarray(direct))

    receipt = run["record"]["measure"]
    assert receipt["module"] == MODULE_RELATIVE
    assert receipt["module_sha256"] == sha256(_module_path().read_bytes()).hexdigest()
    assert receipt["variable_entity"] == "person"
    assert receipt["variable_dtype"] == "float"
    assert receipt["variable_period"] == "year"
    assert receipt["legal_period"] == LEGAL_PERIOD


def test_reviewed_values_and_structure_hold(run) -> None:
    """The three values main already pins reproduce, and zero stays zero."""
    person = run["calibrated"].person
    by_income = dict(
        zip(
            person[TAXABLE_INCOME].to_numpy(),
            person[BASE_TAX].to_numpy(),
            strict=True,
        )
    )
    for income, expected in zip(REVIEWED_INCOMES, REVIEWED_BASE_TAX, strict=True):
        assert by_income[income] == pytest.approx(expected)
    # An observed zero income produces an observed zero liability, not a null.
    assert by_income[0.0] == 0.0
    assert not person[BASE_TAX].isna().any()
    ordered = person.sort_values(TAXABLE_INCOME)
    assert (ordered[BASE_TAX].diff().dropna() >= 0).all()


def test_module_refuses_the_declared_bundle_period() -> None:
    """The module's legal period is 2025; the BE bundle declares 2023.

    The engine refuses the mismatch rather than extrapolating a rate scale, so
    this slice executes at the actual legal period and says so.
    """
    frame = Frame(
        {
            "person": pd.DataFrame(
                {
                    "person_id": [1],
                    "person_household_id": [1],
                    TAXABLE_INCOME: [30_000.0],
                }
            ),
            "household": pd.DataFrame({"household_id": [1]}),
        },
        BE_SCHEMA,
        {"household": Weights(values=np.array([1.0]), kind=WeightKind.DESIGN)},
    )
    adapter = _adapter()
    assert adapter.materialize(frame, [BASE_TAX], period=LEGAL_PERIOD)[BASE_TAX][
        0
    ] == pytest.approx(9_612.0)
    # The engine raises a plain RuntimeError; the adapter does not wrap it.
    with pytest.raises(RuntimeError, match="no formula version at 2023-01-01"):
        adapter.materialize(frame, [BASE_TAX], period=BUNDLE_TARGET_PERIOD)


# --------------------------------------------------------------------------
# Calibration on invented margins.
# --------------------------------------------------------------------------


def test_shared_calibrator_moves_weights_to_the_invented_margins(run) -> None:
    baseline = run["baseline"].weights_for("household")
    calibrated = run["calibrated"].weights_for("household")
    assert baseline.kind is WeightKind.DESIGN
    assert calibrated.kind is WeightKind.CALIBRATED
    assert not np.array_equal(baseline.values, calibrated.values)
    assert run["manifest"].receipt(CALIBRATION_NODE).kernel_ref == "calibrate.adam@1"

    design_total = float(sum(row[2] for row in HOUSEHOLD_ROWS))
    national_target = design_total * NATIONAL_COUNT_MULTIPLIER
    # A seam check on an invented margin, not a calibration quality claim.
    assert abs(calibrated.total - national_target) < abs(
        baseline.total - national_target
    )
    # The filtered margin moved too, so the filter column really gated a row
    # subset rather than being carried along inertly.
    in_be2 = run["calibrated"].table("household")[FILTER_COLUMN].to_numpy()
    be2_target = (
        float(sum(row[2] for row in HOUSEHOLD_ROWS if row[1] == "BE2"))
        * BE2_COUNT_MULTIPLIER
    )
    assert abs(float(calibrated.values[in_be2].sum()) - be2_target) < abs(
        float(baseline.values[in_be2].sum()) - be2_target
    )
    # Population rows, ids, memberships and source columns are untouched.
    for entity in run["baseline"].entities:
        pd.testing.assert_frame_equal(
            run["baseline"].table(entity), run["calibrated"].table(entity)
        )


def test_changed_margins_reuse_the_source_and_rekey_the_solve(tmp_path) -> None:
    first = _run(tmp_path)
    second = _run(tmp_path, national_multiplier=1.55)
    for node in (CREATE_NODE, COUNT_NODE, MEASURE_NODE):
        assert second["manifest"].receipt(node).hit, node
        assert (
            first["manifest"].receipt(node).key == second["manifest"].receipt(node).key
        ), node
    assert not second["manifest"].receipt(CALIBRATION_NODE).hit
    assert (
        first["manifest"].receipt(CALIBRATION_NODE).key
        != second["manifest"].receipt(CALIBRATION_NODE).key
    )
    assert not np.array_equal(
        first["calibrated"].weights_for("household").values,
        second["calibrated"].weights_for("household").values,
    )

    replay = _run(tmp_path, national_multiplier=1.55, resume="require")
    assert all(receipt.hit for receipt in replay["manifest"].nodes.values())
    assert replay["manifest"].key == second["manifest"].key
    np.testing.assert_array_equal(
        replay["calibrated"].person[BASE_TAX].to_numpy(),
        second["calibrated"].person[BASE_TAX].to_numpy(),
    )


# --------------------------------------------------------------------------
# Export: only inputs leave.
# --------------------------------------------------------------------------


def test_export_refuses_the_engine_owned_legal_output(run) -> None:
    """A derived legal result may not be persisted as if it were an input."""
    adapter = _adapter(_export_contract())
    with pytest.raises(ValueError, match="formula-owned") as error:
        adapter.write_dataset(
            run["calibrated"], run["output"].parent / "refused.h5", period=LEGAL_PERIOD
        )
    assert BASE_TAX in str(error.value)
    assert not (run["output"].parent / "refused.h5").exists()


def test_export_reload_is_identity_over_the_input_surface(run) -> None:
    before = _input_only(run["calibrated"])
    reloaded = run["reloaded"]
    assert BASE_TAX not in reloaded.person.columns
    # The exported surface is exactly the declared input surface: the frame's
    # structural columns plus the contract's required and optional columns.
    assert set(reloaded.person.columns) == {
        "person_id",
        "person_household_id",
        REGION_COLUMN,
        TAXABLE_INCOME,
    }
    assert set(reloaded.table("household").columns) == {
        "household_id",
        HOUSEHOLD_REGION_COLUMN,
        COUNT_COLUMN,
        FILTER_COLUMN,
    }
    for entity in before.entities:
        # Values, order, and dtypes all survive; nothing is coerced on reload.
        pd.testing.assert_frame_equal(
            before.table(entity).reset_index(drop=True),
            reloaded.table(entity)[before.table(entity).columns].reset_index(drop=True),
        )
    np.testing.assert_array_equal(
        reloaded.weights_for("household").values,
        run["calibrated"].weights_for("household").values,
    )
    assert reloaded.metadata["time_period"] == str(LEGAL_PERIOD)


def test_region_codes_survive_the_round_trip_as_strings(run) -> None:
    """NUTS1 ids stay text through the entity-table writer and reader.

    The BE spine's commune NIS codes travel the identical string path; this
    slice does not produce them, because ``clone_assign_communes`` is an
    unimplemented declaration and inventing an assignment would be a fake.
    """
    reloaded = run["reloaded"]
    for entity, column in (
        ("person", REGION_COLUMN),
        ("household", HOUSEHOLD_REGION_COLUMN),
    ):
        values = reloaded.table(entity)[column]
        assert all(isinstance(item, str) for item in values.tolist())
        assert set(values) <= set(NUTS1_IDS)
    spine = load_country_spec("be").geography_spine.geography_spine
    assert spine.stage == "clone_assign_communes"
    assert spine.code_column not in reloaded.person.columns
    assert spine.code_column not in reloaded.table("household").columns


def test_rewriting_the_same_frame_reloads_identically(run, tmp_path) -> None:
    """Content survives a rewrite; the file's digest is not a content digest.

    Two writes of the same frame reload to identical tables. Their *bytes* are
    identical only when both writes land in the same wall-clock second:
    measured out of band, two writes 1.3 s apart differed in 133 of 363,496
    bytes at identical length, identical reloaded values, and identical node
    keys. A ``population_sha256`` therefore identifies the artifact that was
    written, not the content that was computed. Nothing in this file asserts
    digest reproducibility, and no assertion here depends on timing.
    """
    frame = _input_only(run["calibrated"])
    adapter = _adapter(_export_contract())
    with pd.option_context("mode.string_storage", "python"):
        first = tmp_path / "rewrite-a.h5"
        second = tmp_path / "rewrite-b.h5"
        adapter.write_dataset(frame, first, period=LEGAL_PERIOD)
        adapter.write_dataset(frame, second, period=LEGAL_PERIOD)
        left = AxiomEntityTableDataset(file_path=first)
        right = AxiomEntityTableDataset(file_path=second)
    assert left.time_period == right.time_period == LEGAL_PERIOD
    for entity in ("person", "household"):
        pd.testing.assert_frame_equal(left.table(entity), right.table(entity))


def test_export_does_not_persist_the_weight_kind(run) -> None:
    """A limitation, pinned: the entity-table format carries values, not kind.

    Any reader that needs ``CALIBRATED`` must obtain it from the frame or a
    sidecar; reconstructing it from the file alone is not possible today.
    """
    dataset = AxiomEntityTableDataset(file_path=run["output"])
    household = dataset.table("household")
    assert "household_weight" in household.columns
    assert not any("kind" in str(column).lower() for column in household.columns)
    assert dataset.time_period == LEGAL_PERIOD


# --------------------------------------------------------------------------
# Shared quality artifacts.
# --------------------------------------------------------------------------


def test_national_and_nuts1_partitions_reconcile(run) -> None:
    for entity, artifact in run["record"]["support"].items():
        national = [
            row for row in artifact["rows"] if row["geography"]["level"] == "national"
        ]
        nuts1 = [
            row for row in artifact["rows"] if row["geography"]["level"] == "nuts1"
        ]
        assert len(national) == 1
        assert len(nuts1) == len(NUTS1_IDS) + 1  # the declared unknown bucket
        assert sum(row["weight_sum"] for row in nuts1) == pytest.approx(
            national[0]["weight_sum"]
        )
        assert national[0]["weight_sum"] == pytest.approx(
            run["reloaded"].resolve_weights(entity).total
        )
        assert sum(row["record_count"] for row in nuts1) == run["reloaded"].n(entity)
        assert artifact["weight_entity"] == "household"
        assert artifact["period"] == str(LEGAL_PERIOD)
        assert artifact["population_sha256"] == run["record"]["population_sha256"]


def test_declared_unknown_bucket_stays_visible_at_zero(run) -> None:
    """An unobserved declared area is reported empty, never dropped.

    This is the structural counterpart to the observed zero income: a zero
    weight because nothing was observed there, not a missing value.
    """
    for artifact in run["record"]["support"].values():
        unknown = next(
            row for row in artifact["rows"] if row["geography"]["id"] == NUTS1_UNKNOWN
        )
        assert unknown["record_count"] == 0
        assert unknown["weight_sum"] == 0.0
        assert unknown["effective_sample_size"] is None
        assert unknown["max_weight_share"] is None
        for row in artifact["rows"]:
            if row["geography"]["level"] == "nuts1":
                assert row["geography"]["vintage"] == run["record"]["nuts1_vintage"]


def test_distributions_carry_the_observed_zero_and_no_missing_mass(run) -> None:
    series = run["record"]["distributions"]["series"]
    assert series
    for row in series:
        # Every invented income is observed, so nothing falls to missing mass.
        assert row["missing_weight"] == 0.0
        assert sum(item["weight"] for item in row["bins"]) + row[
            "missing_weight"
        ] == pytest.approx(row["total_weight"])
    national = [row for row in series if row["geography"]["level"] == "national"]
    assert len(national) == 1
    lowest = next(item for item in national[0]["bins"] if item["label"] == "under20000")
    # The zero-income person is counted in the lowest bin, not as missing.
    assert lowest["weight"] > 0.0


def test_household_region_disagreement_is_refused(run) -> None:
    frame = run["calibrated"]
    person = frame.person.copy(deep=True)
    person.loc[person.index[0], REGION_COLUMN] = "BE3"
    invalid = Frame(
        {"person": person, "household": frame.table("household").copy(deep=True)},
        BE_SCHEMA,
        {"household": frame.weights_for("household")},
    )
    with pytest.raises(ValueError, match="unanimously"):
        _assert_household_region_agrees(invalid)


def test_missing_unknown_bucket_refuses_instead_of_dropping_mass(run) -> None:
    frame = run["reloaded"]
    household = frame.table("household").copy(deep=True)
    household.loc[household.index[0], HOUSEHOLD_REGION_COLUMN] = pd.NA
    holed = Frame(
        {"person": frame.person.copy(deep=True), "household": household},
        BE_SCHEMA,
        {"household": frame.weights_for("household")},
    )
    geographies = tuple(
        replace(
            spec,
            unknown_id=None,
            labels={k: v for k, v in spec.labels.items() if k != NUTS1_UNKNOWN},
        )
        if spec.level == "nuts1"
        else spec
        for spec in _geographies(HOUSEHOLD_REGION_COLUMN)
    )
    with pytest.raises(ValueError, match="unknown bucket"):
        population_support(
            holed,
            entity="household",
            geography_specs=geographies,
            candidate_release_id="be-synthetic",
            population_sha256=run["record"]["population_sha256"],
            period=str(LEGAL_PERIOD),
        )


# --------------------------------------------------------------------------
# Posture: this slice is not a release and is not routed to one.
# --------------------------------------------------------------------------


def test_posture_is_synthetic_and_not_routed_to_a_country_release(run) -> None:
    record = run["record"]
    assert record["posture"] == POSTURE
    assert record["release_eligible"] is False
    assert record["routed_to_country_release"] is None
    assert record["country"] == "be"
    assert run["compiled"].graph.country == "be"
    for node in (CREATE_NODE, COUNT_NODE, MEASURE_NODE):
        receipt = run["manifest"].receipt(node).receipt
        assert receipt["posture"] == POSTURE
        assert receipt["release_eligible"] is False
    # No gate or release kernel is registered, so no verdict or tier exists.
    kernels = _registry().as_mapping()
    assert all(
        kernel.capabilities.role.value == "compute" for kernel in kernels.values()
    )


def test_source_and_measure_kernels_refuse_a_release_posture() -> None:
    class _Context:
        params = {"posture": "release"}
        sources: dict = {}
        tables: dict = {}
        weights: dict = {}

    with pytest.raises(ValueError, match=POSTURE):
        BeSyntheticSourceKernel().run(_Context())
    with pytest.raises(ValueError, match=POSTURE):
        AxiomArticle130Kernel().run(_Context())
