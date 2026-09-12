import ast
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from microcosm.frame.adapters import policyengine_us as module

_EXPECTED_IN_STATE = frozenset(
    "AL AK AZ AR CA CO CT DC DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN "
    "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA "
    "WV WI WY PR VI".split()
)
_EXPECTED_PUF = frozenset(
    "e02000 e26270 e19200 e18500 e19800 e20400 e20100 e00700 e03270 e24515 "
    "e03300 e07300 e62900 e32800 e87530 e03240 e01100 e01200 e24518 e09900 "
    "e27200 e03290 e58990 e03230 e11200 e07260 e07240 e03220 p08000 e03400 "
    "e09800 e09700 e03500 e87521".split()
)
_EXPECTED_STATE_MFS = frozenset(
    "ar_standard_deduction ar_itemized_deductions ar_taxable_income ar_agi "
    "dc_taxable_income de_standard_deduction de_itemized_deductions "
    "de_taxable_income de_agi ia_standard_deduction ia_itemized_deductions "
    "ia_taxable_income ia_agi ky_standard_deduction ky_itemized_deductions "
    "ky_taxable_income ms_standard_deduction ms_itemized_deductions "
    "ms_taxable_income mt_standard_deduction mt_itemized_deductions "
    "mt_taxable_income".split()
)
_EXPECTED_SPM_AMOUNTS = frozenset(
    {
        "spm_unit_reference_spm_threshold",
        "spm_unit_unadjusted_spm_threshold",
        "spm_unit_geographic_adjustment",
        "spm_unit_spm_threshold",
        "spm_unit_spm_threshold_housing_portion",
    }
)
_EXPECTED_SPM_FORMULAS = _EXPECTED_SPM_AMOUNTS | {
    "is_spm_independent_minor_role",
    "spm_measurement_adults",
    "spm_measurement_children",
}


def _write_variable_source(
    root: Path, source: str, *, name: str = "variables.py"
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(source)


def _installed_package() -> tuple[object, Path]:
    try:
        package = module.distribution("policyengine-us")
    except module.PackageNotFoundError:
        pytest.skip("requires the policyengine-us [us] extra")
    return package, Path(package.locate_file("policyengine_us"))


def _copy_generated_sources(root: Path) -> tuple[object, Path]:
    package, installed_root = _installed_package()
    for relative_path in module._GENERATED_SOURCE_SHA256:
        source = installed_root / relative_path
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    return package, root


def test_source_index_classifies_leaf_and_formula_mutations(tmp_path: Path) -> None:
    _write_variable_source(
        tmp_path,
        """
class source_leaf(Variable):
    value_type = float
    entity = Person
    definition_period = YEAR

class future_formula(Variable):
    value_type = int
    entity = Person
    definition_period = YEAR

    def formula_2025(person, period, parameters):
        return 0

class aggregate_formula(Variable):
    value_type = bool
    entity = TaxUnit
    definition_period = MONTH
    adds = ["source_leaf"]
""",
    )

    indexed = module._index_policyengine_us_variable_sources(tmp_path)

    assert not indexed["source_leaf"].formula_owned
    assert indexed["future_formula"].formula_owned
    assert not indexed["future_formula"].computed_at(2024)
    assert indexed["future_formula"].computed_at(2025)
    assert indexed["aggregate_formula"].always_computed
    assert indexed["aggregate_formula"].metadata.entity == "tax_unit"
    assert indexed["aggregate_formula"].metadata.dtype == "bool"
    assert indexed["aggregate_formula"].metadata.period == "month"


def test_source_index_rejects_duplicate_variable_classes(tmp_path: Path) -> None:
    source = """
class duplicate(Variable):
    value_type = float
    entity = Person
    definition_period = YEAR
"""
    _write_variable_source(tmp_path, source, name="first.py")
    _write_variable_source(tmp_path, source, name="second.py")

    with pytest.raises(RuntimeError, match="Duplicate.*duplicate"):
        module._index_policyengine_us_variable_sources(tmp_path)


def test_source_index_rejects_dynamic_required_metadata(tmp_path: Path) -> None:
    _write_variable_source(
        tmp_path,
        """
class dynamic_metadata(Variable):
    value_type = choose_value_type()
    entity = Person
    definition_period = YEAR
""",
    )

    with pytest.raises(RuntimeError, match="dynamic.*value_type"):
        module._index_policyengine_us_variable_sources(tmp_path)


def test_generated_snapshot_covers_the_pinned_default_system() -> None:
    package, package_root = _installed_package()
    generated = module._index_policyengine_us_generated_variable_sources(
        package_root,
        version=package.version,
    )
    formula_owned = (
        _EXPECTED_IN_STATE
        | _EXPECTED_STATE_MFS
        | {"mi_surtax"}
        | _EXPECTED_SPM_FORMULAS
    )

    assert set(generated) == formula_owned | _EXPECTED_PUF | {"is_household_spouse"}
    assert len(generated) == 119
    assert {name for name, item in generated.items() if item.formula_owned} == (
        formula_owned
    )
    assert {name for name, item in generated.items() if not item.formula_owned} == (
        _EXPECTED_PUF | {"is_household_spouse"}
    )

    expected_metadata = {
        "AK": ("household", "bool", "year"),
        "e00700": ("person", "float", "year"),
        "ar_agi": ("tax_unit", "float", "year"),
        "mi_surtax": ("tax_unit", "float", "year"),
        "is_household_spouse": ("person", "bool", "point"),
        "is_spm_independent_minor_role": ("person", "bool", "point"),
        "spm_measurement_adults": ("spm_unit", "int", "year"),
        "spm_unit_spm_threshold": ("spm_unit", "float", "year"),
    }
    for name, expected in expected_metadata.items():
        metadata = generated[name].metadata
        assert (metadata.entity, metadata.dtype, metadata.period) == expected


@pytest.mark.requires_us
def test_complete_metadata_and_ownership_match_actual_default_system() -> None:
    from policyengine_us.spm import DATASET_FORMULA_OWNED_INPUTS, DATASET_SOURCE_INPUTS
    from policyengine_us.system import system

    module._installed_policyengine_us_variable_sources.cache_clear()
    index = module.PolicyEngineUSVariableMetadataIndex()
    live = module.PolicyEngineUSEngine()
    live._system = system
    assert len(index._definitions) == len(system.variables) == 6_159
    assert set(index._definitions) == set(system.variables)
    for name, variable in system.variables.items():
        assert index.variable_metadata(name) == live.variable_metadata(name), name
        assert index._definitions[name].formula_owned == module._is_engine_computed(
            variable
        ), name
    assert index.variables() == live.variables()
    assert index.formula_owned_outputs(
        index._definitions
    ) == live.formula_owned_outputs(index._definitions)
    assert DATASET_SOURCE_INPUTS.isdisjoint(DATASET_FORMULA_OWNED_INPUTS)
    assert DATASET_SOURCE_INPUTS <= set(index.variables())
    assert not (
        DATASET_SOURCE_INPUTS & index.formula_owned_outputs(DATASET_SOURCE_INPUTS)
    )
    assert live.default_values(tuple(DATASET_SOURCE_INPUTS)) == {}
    for name in DATASET_SOURCE_INPUTS:
        closure = index.variable_dependency_closure(name)
        assert closure.input_leaves == (name,)
        assert closure.formula_nodes == closure.edges == ()
        assert index.consumer_receipts("is_household_head")
    import pandas as pd

    native = {
        "person": pd.DataFrame({name: [True, False] for name in DATASET_SOURCE_INPUTS})
    }
    assert index._engine_computed_columns(native, period=2024) == set()
    assert live._engine_computed_columns(native, period=2024) == set()


def test_generated_metadata_index_does_not_import_country_or_calculator() -> None:
    _installed_package()
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json, sys
from microcosm.frame.adapters.policyengine_us import _installed_policyengine_us_variable_sources
index = _installed_policyengine_us_variable_sources()
assert not any(name == "policyengine_us" or name.startswith("policyengine_us.") or name == "spm_calculator" or name.startswith("spm_calculator.") for name in sys.modules)
print(json.dumps({"definitions": len(index.definitions)}))
""",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {"definitions": 6159}


@pytest.mark.parametrize("tamper", ("source", "missing", "version"))
def test_generated_snapshot_authenticates_external_calculator(tmp_path, tamper):
    package, package_root = _installed_package()
    source = module._authenticated_calculator_source()
    copied = tmp_path / source.name
    copied.write_bytes(source.read_bytes())
    version = module._GENERATED_CALCULATOR_VERSION
    if tamper == "source":
        copied.write_bytes(copied.read_bytes() + b"\n# altered factory\n")
    elif tamper == "missing":
        copied.unlink()
    else:
        version = "1.0.1"
    with pytest.raises(RuntimeError, match="SPM calculator"):
        module._index_policyengine_us_generated_variable_sources(
            package_root,
            version=package.version,
            calculator_root=tmp_path,
            calculator_version=version,
        )


def test_generated_factory_dependency_receipts_are_complete_and_real():
    receipts = module._generated_calculator_consumer_receipts()
    expected = {
        "is_spm_independent_minor_role": {"is_household_head", "is_household_spouse"},
        "spm_measurement_adults": {"age", "is_spm_independent_minor_role"},
        "spm_measurement_children": {"spm_measurement_adults"},
        **{
            name: {
                "spm_measurement_adults",
                "spm_measurement_children",
                "spm_unit_tenure_type",
                "county_fips",
            }
            for name in _EXPECTED_SPM_AMOUNTS
        },
    }
    observed = {}
    source = module._authenticated_calculator_source()
    tree = ast.parse(source.read_text())
    string_sites = {
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    for target, rows in receipts.items():
        for row in rows:
            observed.setdefault(row.consumer, set()).add(target)
            assert row.path == "spm_calculator/policyengine_adapter.py"
            assert (row.line, target) in string_sites
            assert row.kind == "entity_call"
            assert row.receiver_entity == (
                "household"
                if target == "county_fips"
                else "person"
                if row.consumer
                in {"is_spm_independent_minor_role", "spm_measurement_adults"}
                else "spm_unit"
            )
    assert observed == expected
    combined = module._installed_policyengine_us_variable_sources()
    for target, rows in receipts.items():
        assert set(rows) <= set(combined.consumers[target])


def test_dependency_closure_stops_at_native_input_but_traverses_ordinary_formulas(
    tmp_path,
):
    _write_variable_source(
        tmp_path,
        """
class household_role(Variable):
    value_type = bool
    entity = Person
    definition_period = ETERNITY

class source_income(Variable):
    value_type = float
    entity = Person
    definition_period = YEAR

class native_role(Variable):
    value_type = bool
    entity = Person
    definition_period = ETERNITY
    def formula(person, period, parameters):
        return person("household_role", period)

class ordinary_formula(Variable):
    value_type = float
    entity = Person
    definition_period = YEAR
    def formula(person, period, parameters):
        return person("source_income", period)

class outer_formula(Variable):
    value_type = float
    entity = Person
    definition_period = YEAR
    def formula(person, period, parameters):
        return person("ordinary_formula", period) * person("native_role", period)
""",
    )
    source = module._index_policyengine_us_sources(tmp_path)
    # Isolate the graph behavior from the separately authenticated country
    # contract; these are explicit fixture variables, never installed metadata.
    index = object.__new__(module.PolicyEngineUSVariableMetadataIndex)
    index._definitions = source.definitions
    index._consumers = source.consumers
    index._engine_version = "fixture"
    index._source_inputs = frozenset({"native_role"})
    index._country_formula_owned = frozenset()
    closure = index.variable_dependency_closure("outer_formula")
    assert closure.input_leaves == ("native_role", "source_income")
    assert closure.formula_nodes == ("ordinary_formula", "outer_formula")
    assert ("ordinary_formula", "source_income") in closure.edges
    assert ("native_role", "household_role") not in closure.edges
    assert index.consumer_receipts("household_role")[0].consumer == "native_role"

    index._source_inputs = frozenset()
    fallback = index.variable_dependency_closure("outer_formula")
    assert fallback.input_leaves == ("household_role", "source_income")
    assert "native_role" in fallback.formula_nodes
    assert ("native_role", "household_role") in fallback.edges


@pytest.mark.parametrize("invalid", ("overlap", "unknown", "entity", "dtype", "period"))
def test_country_source_input_contract_fails_closed(invalid):
    name = "declared_native_role"
    source = frozenset({name})
    owned = source if invalid == "overlap" else frozenset()
    metadata = (
        {}
        if invalid == "unknown"
        else {
            name: module.VariableMetadata(
                name=name,
                entity="household" if invalid == "entity" else "person",
                dtype="int" if invalid == "dtype" else "bool",
                period="year" if invalid == "period" else "point",
            )
        }
    )
    with pytest.raises(RuntimeError, match="Country dataset"):
        module._validate_dataset_source_inputs(source, owned, metadata)


def test_live_source_contract_cannot_be_missing_or_synthesized(monkeypatch):
    variable = SimpleNamespace(
        entity=SimpleNamespace(key="person"),
        value_type=bool,
        definition_period="eternity",
        formulas={"0001-01-01": lambda *_: False},
        adds=None,
        subtracts=None,
        default_value=False,
    )
    engine = module.PolicyEngineUSEngine()
    engine._system = SimpleNamespace(variables={"declared_native_role": variable})
    contract = SimpleNamespace(DATASET_FORMULA_OWNED_INPUTS=frozenset())
    monkeypatch.setattr(module, "import_module", lambda _: contract)
    with pytest.raises(RuntimeError, match="DATASET_SOURCE_INPUTS"):
        engine.variables()
    contract.DATASET_SOURCE_INPUTS = frozenset({"declared_native_role"})
    assert engine.variables() == ["declared_native_role"]
    assert engine.formula_owned_outputs(["declared_native_role"]) == set()
    assert engine.default_values(["declared_native_role"]) == {}
    variable.definition_period = "day"
    with pytest.raises(RuntimeError, match="ETERNITY"):
        engine.variables()


@pytest.mark.parametrize(
    "variant", ("valid", "missing", "dynamic", "overlap", "tampered")
)
def test_static_country_source_contract_is_literal_and_authenticated(
    tmp_path, monkeypatch, variant
):
    package, package_root = _installed_package()
    definitions = module._index_policyengine_us_generated_variable_sources(
        package_root, version=package.version
    )
    role = "is_spm_independent_minor_role"
    source = tmp_path / "spm.py"
    source.write_text(
        (
            f"DATASET_FORMULA_OWNED_INPUTS = FORMULA_OWNED_INPUTS | frozenset({{{role!r}}})\n"
            if variant == "overlap"
            else "DATASET_FORMULA_OWNED_INPUTS = FORMULA_OWNED_INPUTS | frozenset(())\n"
        )
        + (
            ""
            if variant == "missing"
            else "DATASET_SOURCE_INPUTS = frozenset(get_roles())\n"
            if variant == "dynamic"
            else f"DATASET_SOURCE_INPUTS = frozenset({{{role!r}}})\n"
        )
    )
    # This is an explicit unit-test contract fixture, not installed wheel evidence.
    monkeypatch.setitem(
        module._GENERATED_SOURCE_SHA256,
        "spm.py",
        module.sha256(source.read_bytes()).hexdigest(),
    )
    if variant == "tampered":
        source.write_text(source.read_text() + "\n# changed after authentication\n")
    if variant != "valid":
        with pytest.raises(RuntimeError, match="Country dataset"):
            module._country_dataset_contract_from_sources(tmp_path, definitions)
    else:
        native, computed = module._country_dataset_contract_from_sources(
            tmp_path, definitions
        )
        assert native == frozenset({role})
        assert not native & computed


@pytest.mark.parametrize("relative_path", module._GENERATED_SOURCE_SHA256)
def test_generated_snapshot_fails_closed_on_source_mutation(
    tmp_path: Path,
    relative_path: str,
) -> None:
    package, package_root = _copy_generated_sources(tmp_path)
    source = package_root / relative_path
    source.write_bytes(source.read_bytes() + b"\n# metadata audit mutation\n")

    with pytest.raises(RuntimeError, match="source changed without a metadata audit"):
        module._index_policyengine_us_generated_variable_sources(
            package_root,
            version=package.version,
        )


def test_generated_snapshot_fails_closed_on_missing_source(tmp_path: Path) -> None:
    package, package_root = _copy_generated_sources(tmp_path)
    (package_root / "system.py").unlink()

    with pytest.raises(RuntimeError, match="source is unavailable"):
        module._index_policyengine_us_generated_variable_sources(
            package_root,
            version=package.version,
        )


def test_generated_snapshot_fails_closed_on_unreviewed_version(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="has not been audited"):
        module._index_policyengine_us_generated_variable_sources(
            tmp_path,
            version="1.764.7",
        )


def test_installed_index_distinguishes_absent_extra_from_broken_layout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class _BrokenDistribution:
        version = module._GENERATED_SOURCE_VERSION

        @staticmethod
        def locate_file(path: str) -> Path:
            return tmp_path / path

    module._installed_policyengine_us_variable_sources.cache_clear()
    monkeypatch.setattr(module, "distribution", lambda _name: _BrokenDistribution())
    with pytest.raises(RuntimeError, match="source tree is unavailable"):
        module._installed_policyengine_us_variable_sources()
    module._installed_policyengine_us_variable_sources.cache_clear()

    def _missing_distribution(_name: str) -> None:
        raise module.PackageNotFoundError("policyengine-us")

    monkeypatch.setattr(module, "distribution", _missing_distribution)
    with pytest.raises(ImportError, match="requires the 'policyengine-us' package"):
        module._installed_policyengine_us_variable_sources()
    module._installed_policyengine_us_variable_sources.cache_clear()
