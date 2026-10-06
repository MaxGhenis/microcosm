"""Tests split from packages/microcosm-frame/tests/test_policyengine_uk_adapter.py."""

# ruff: noqa: F403, F405
from test_support.microcosm_frame.policyengine_uk_adapter import *


def test_policyengine_uk_adapter_satisfies_rules_protocol_without_importing_engine() -> (
    None
):
    adapter = PolicyEngineUKEngine()

    assert isinstance(adapter, RulesEngine)
    assert adapter.country == "uk"
    assert adapter.entity_schema() == UK_SCHEMA


def test_policyengine_uk_adapter_export_side_is_not_implemented() -> None:
    adapter = PolicyEngineUKEngine()

    with pytest.raises(NotImplementedError, match="write_uk_national_frame"):
        adapter.write_dataset(object(), "unused.h5", period=2023)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "defect", ["missing", "not_loaded", "changed", "entity", "dtype", "period"]
)
def test_adapter_refuses_unconsumed_explicit_uc_roles(monkeypatch, defect):
    definition = SimpleNamespace(
        entity=SimpleNamespace(key="person"), value_type=bool, definition_period="year"
    )
    variables = {
        "is_uc_claimant": definition,
        "universal_credit": SimpleNamespace(
            entity=SimpleNamespace(key="benunit"), value_type=float
        ),
    }
    if defect == "missing":
        del variables["is_uc_claimant"]
    elif defect == "entity":
        definition.entity.key = "benunit"
    elif defect == "dtype":
        definition.value_type = float
    elif defect == "period":
        definition.definition_period = "month"
    calls = []

    def calculate(name, *args, **kwargs):
        calls.append(name)
        return np.array([False if defect == "changed" else True])

    simulation = SimpleNamespace(
        tax_benefit_system=SimpleNamespace(variables=variables),
        input_variables=[] if defect == "not_loaded" else ["is_uc_claimant"],
        calculate=calculate,
    )
    engine = PolicyEngineUKEngine()
    engine._system = simulation.tax_benefit_system
    monkeypatch.setattr(engine, "_build_dataset", lambda *args: object())
    monkeypatch.setattr(
        engine,
        "_import_policyengine_uk",
        lambda: SimpleNamespace(Microsimulation=lambda **kwargs: simulation),
    )
    bundle = SimpleNamespace(
        table=lambda entity: pd.DataFrame({"is_uc_claimant": [True]}),
        n=lambda entity: 1,
    )
    with pytest.raises(ValueError, match="is_uc_claimant"):
        engine.materialize(bundle, ["universal_credit"], 2025)
    assert "universal_credit" not in calls


def _role_engine(monkeypatch, variables, *, loaded, values):
    calls = []

    def calculate(name, *args, **kwargs):
        calls.append(name)
        return np.asarray(values[name]) if name in values else np.zeros(2)

    simulation = SimpleNamespace(
        tax_benefit_system=SimpleNamespace(variables=variables),
        input_variables=loaded,
        calculate=calculate,
    )
    engine = PolicyEngineUKEngine()
    engine._system = simulation.tax_benefit_system
    monkeypatch.setattr(engine, "_build_dataset", lambda *args: object())
    monkeypatch.setattr(
        engine,
        "_import_policyengine_uk",
        lambda: SimpleNamespace(Microsimulation=lambda **kwargs: simulation),
    )
    return engine, calls


def _person_role():
    return SimpleNamespace(
        entity=SimpleNamespace(key="person"), value_type=bool, definition_period="year"
    )


_ROLE_BUNDLE = SimpleNamespace(
    table=lambda entity: pd.DataFrame(
        {"is_uc_claimant": [True, False], "is_claimant_or_partner": [True, False]}
    ),
    n=lambda entity: 2,
)
_OUTPUT = SimpleNamespace(entity=SimpleNamespace(key="person"), value_type=float)


@pytest.mark.parametrize("defect", ["not_loaded", "changed", "entity", "dtype", "period"])
def test_adapter_refuses_unconsumed_claimant_or_partner_roles(monkeypatch, defect):
    # policyengine-uk 2.107.0 defines is_claimant_or_partner: a supplied role
    # must reach the model as an input, unchanged, exactly like is_uc_claimant.
    role = _person_role()
    if defect == "entity":
        role.entity.key = "benunit"
    elif defect == "dtype":
        role.value_type = float
    elif defect == "period":
        role.definition_period = "month"
    variables = {
        "is_uc_claimant": _person_role(),
        "is_claimant_or_partner": role,
        "income_tax": _OUTPUT,
    }
    loaded = ["is_uc_claimant"]
    if defect != "not_loaded":
        loaded.append("is_claimant_or_partner")
    supplied = np.array([True, False])
    engine, calls = _role_engine(
        monkeypatch,
        variables,
        loaded=loaded,
        values={
            "is_uc_claimant": supplied,
            "is_claimant_or_partner": ~supplied if defect == "changed" else supplied,
        },
    )
    with pytest.raises(ValueError, match="is_claimant_or_partner"):
        engine.materialize(_ROLE_BUNDLE, ["income_tax"], 2025)
    assert "income_tax" not in calls


def test_adapter_accepts_claimant_or_partner_roles_the_model_reads(monkeypatch):
    variables = {
        "is_uc_claimant": _person_role(),
        "is_claimant_or_partner": _person_role(),
        "income_tax": _OUTPUT,
    }
    supplied = np.array([True, False])
    engine, calls = _role_engine(
        monkeypatch,
        variables,
        loaded=["is_uc_claimant", "is_claimant_or_partner"],
        values={"is_uc_claimant": supplied, "is_claimant_or_partner": supplied},
    )
    engine.materialize(_ROLE_BUNDLE, ["income_tax"], 2025)
    assert calls == ["is_uc_claimant", "is_claimant_or_partner", "income_tax"]


def test_adapter_ignores_claimant_or_partner_roles_before_the_model_defines_them(
    monkeypatch,
):
    # Before policyengine-uk 2.107.0 no variable of that name exists, so the
    # loader's dropping the column changes nothing the model computes.
    variables = {"is_uc_claimant": _person_role(), "income_tax": _OUTPUT}
    supplied = np.array([True, False])
    engine, calls = _role_engine(
        monkeypatch,
        variables,
        loaded=["is_uc_claimant"],
        values={"is_uc_claimant": supplied},
    )
    engine.materialize(_ROLE_BUNDLE, ["income_tax"], 2025)
    assert calls == ["is_uc_claimant", "income_tax"]
