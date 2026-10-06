"""Census of what the 19-node native financial run holds, on invented inputs.

This is a measurement harness, not a contract test. It is not collected by the
default suite (``testpaths = ["packages"]``). Run it explicitly:

    uv run pytest -p conftest -s \
        experiments/native-memory-model-20260923/test_retention_census.py

It reuses the invented, source-issued fixture of
``test_us_graph_atomic_survey_financial.known_financial_run`` (same call:
demographic conditioning, two estimators, no property/status/roles) and runs
the real ``run_atomic_survey_financial`` once cold, with both retention
profiles. Five hooks record *structure*, never values:

1. every observer snapshot's per-entity row count, column count, dtype tokens
   and physical bytes (the per-node shape table);
2. at the call of ``atomic._states`` -- after the independent expected loop,
   when the detached observations, expected/current replay pools, base
   expectations, geography reconstruction, prefix, manifest and loaded
   artifacts are all simultaneously live -- a census of the runner's locals:
   unique physical buffers reachable from each local, deduplicated across
   locals in a fixed attribution order;
3. the same census over the returned run object;
4. inside the nine-node prefix runner, at the return of its second ("fresh")
   geography reconstruction, when its expected pool, its detached
   observations and both reconstructions are live together;
5. in the financial runner just after its 19-node ``run_graph`` returns.

At each of the three runner points (2, 4, 5) two attributions are recorded
(see ``census.py``). The first-owner partition charges a shared buffer to the
first local in a fixed order; it sums to the live set but says nothing about
what releasing one local would free. The exclusive attribution splits the
replay pools (``expected``, ``current``, ``observed``, ...) into one atom per
node and each geography reconstruction into one atom per stage, walks every
atom separately, and charges to a group only the bytes no atom outside the
group reaches. Savings for proposed code changes (C2, C3, C5) are read from
the exclusive attribution. The harness also records, by object identity,
which replay-pool entries *are* reconstruction stage populations, and
asserts the aliasing it found (``graph_atomic_survey_financial.py:2228-2232``
copies every ``base_expected`` geography stage into ``expected``;
``graph_atomic_survey_population.py:266-272`` builds the prefix's
``expected`` from its reconstruction's stages).

Buffers are deduplicated by physical identity (NumPy root buffer address and
size, Arrow buffer address and size, Python object identity for ``str``/object
cells and ``bytes``). Every DataFrame buffer is also classified by the entity
table it belongs to and whether that table sits at the stacked-source grain,
the cloned grain, or neither, so the bytes can be scaled per row to other
fractions. Invented row counts are tiny; only per-row bytes, column counts,
dtype mixes and object multiplicities are meant to transfer to real scale.
"""

from __future__ import annotations

import dataclasses
import gc
import hashlib
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from test_us_current_asec_demographics import _demographic_arguments
from test_us_graph_atomic_survey_population import _support_payload

from microcosm.build.us_runtime import graph_atomic_survey_financial as runner

OUT = Path(
    os.environ.get(
        "MEMORY_CENSUS_OUT", Path(__file__).with_name("retention-census.json")
    )
)


def _load_census_module():
    # The suite runs with --import-mode=importlib, which does not put this
    # directory on sys.path; load the sibling module under a unique name.
    spec = importlib.util.spec_from_file_location(
        "native_memory_census", Path(__file__).with_name("census.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_census = _load_census_module()
Census = _census.Census
exclusive_rows = _census.exclusive_rows
_SKIP = _census._SKIP
_array_buffers = _census._array_buffers
_dtype_token = _census._dtype_token
_frame_tables = _census._frame_tables


# --------------------------------------------------------------------------
# Snapshot shapes
# --------------------------------------------------------------------------


def _snapshot_shape(node_id, population):
    frame = population.frame
    tables = {}
    for kind, name, table in _frame_tables(frame):
        seen, physical = set(), 0
        by_dtype = defaultdict(lambda: [0, 0])
        for column in table.columns:
            series = table[column]
            token = _dtype_token(series)
            size = 0
            for key, nbytes in _array_buffers(series.array):
                if key not in seen:
                    seen.add(key)
                    size += nbytes
            physical += size
            by_dtype[token][0] += 1
            by_dtype[token][1] += size
        tables[name] = {
            "kind": kind,
            "rows": len(table),
            "columns": len(table.columns),
            "physical_bytes": physical,
            "dtypes": {
                k: {"columns": v[0], "bytes": v[1]} for k, v in by_dtype.items()
            },
        }
    return {"node": node_id, "version": population.version, "tables": tables}


# --------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------

_LOCAL_ORDER = (
    "prefix",
    "entry",
    "retained",
    "qualified",
    "geography",
    "base_expected",
    "donor",
    "donor_columns",
    "manifest",
    "observed",
    "witnessed",
    "expected",
    "current",
    "tax_populations",
    "loaded",
    "prefix_artifacts",
    "projection_bytes",
    "matrix_bytes",
    "raw",
    "applications",
    "drawn",
    "receipts",
    "store",
    "kernels",
    "compiled",
    "sources",
)

# Inside the nine-node prefix runner (graph_atomic_survey_population), at the
# return of its second, "fresh" geography reconstruction: its expected pool,
# its detached observations, both reconstructions and its manifest are live.
_PREFIX_ORDER = (
    "prefix",
    "preparation_entry",
    "expected",
    "observed",
    "geography",
    "fresh",
    "manifest",
    "result",
    "states",
    "prefix_artifacts",
    "view",
    "store",
    "kernels",
    "compiled",
    "sources",
)


# Replay pools split into one atom per entry for the exclusive attribution.
_FINANCIAL_SPLIT = frozenset(
    {
        "base_expected",
        "expected",
        "current",
        "observed",
        "witnessed",
        "retained",
        "tax_populations",
    }
)
_PREFIX_SPLIT = frozenset({"expected", "observed"})
# Geography reconstructions split into one atom per stage, the terminal copy
# (``population``, a separate ``_copy_population`` of the last stage) and the
# remaining small fields.
_RECONSTRUCTIONS = frozenset({"geography", "fresh"})

C3 = "C3: stream the geography expectations (runner-local)"
C3R = "C3R: C3, and drop geography stages from the replay pool (contract change)"
POOL = "replay pool, every node (expected and current)"
C5 = "C5: manifest-attached frames"
C2A = "C2a: detached copies of the six unreturned observations"
C2B_ONLY = "C2b as first written: release the expected pool only"
C2B = "C2b: release the expected pool and the first reconstruction's stages"
C2C = "C2c: build only the three fresh populations the final checks compare"
C2 = "C2: C2a, C2b and C2c together"


def _atoms(local, order, split, module_state, unreached):
    """(name, owning local, object) covering everything the census walks."""
    atoms = []
    for name in order:
        if name not in local:
            continue
        value = local[name]
        if name in split and isinstance(value, dict):
            for key, item in value.items():
                atoms.append((f"{name}[{key}]", name, item))
        elif name in _RECONSTRUCTIONS and hasattr(value, "stages"):
            for stage in value.stages:
                atoms.append((f"{name}.stages[{stage.node.id}]", name, stage))
            atoms.append((f"{name}.population", name, value.population))
            rest = [
                getattr(value, field.name)
                for field in dataclasses.fields(value)
                if field.name not in ("stages", "population")
            ]
            atoms.append((f"{name}.rest", name, rest))
        else:
            atoms.append((name, name, value))
    other = [v for k, v in local.items() if k not in order]
    atoms.append(("other_locals", "other_locals", other))
    atoms.append(("module_state", "module_state", module_state))
    atoms.append(("gc_unreached", "gc_unreached", unreached))
    return atoms


def _root_groups(atoms):
    groups = defaultdict(set)
    for name, owner, _ in atoms:
        groups[f"root:{owner}"].add(name)
    return dict(groups)


def _financial_groups(local, atoms):
    names = {name for name, _, _ in atoms}
    groups = _root_groups(atoms)
    geography = local["geography"]
    stage_ids = [stage.node.id for stage in geography.stages]
    stage_populations = [stage.population for stage in geography.stages]
    c3 = set(groups["root:geography"]) | {
        f"base_expected[{s}]" for s in stage_ids if f"base_expected[{s}]" in names
    }
    pool_stages = {f"expected[{s}]" for s in stage_ids if f"expected[{s}]" in names}
    pool_stages |= {
        f"current[{version}]"
        for version, population in local.get("current", {}).items()
        if any(population is stage for stage in stage_populations)
    }
    pool = {n for n in names if n.startswith(("expected[", "current["))}
    groups[C3] = c3
    groups[C3R] = c3 | pool_stages
    groups[POOL] = pool
    groups[C5] = set(groups["root:manifest"])
    return groups


def _prefix_groups(local, atoms):
    groups = _root_groups(atoms)
    result = local["result"]
    returned = (
        result.observed_population,
        result.expanded_population,
        result.geography_population,
    )
    c2a = {
        f"observed[{node}]"
        for node, population in local["observed"].items()
        if not any(population is kept for kept in returned)
    }
    geography, fresh = local["geography"], local["fresh"]
    c2b = set(groups["root:expected"]) | {
        f"geography.stages[{stage.node.id}]" for stage in geography.stages
    }
    c2b.add("geography.population")
    compared = (fresh.observed_population, fresh.expanded_population)
    c2c = {
        f"fresh.stages[{stage.node.id}]"
        for stage in fresh.stages
        if not any(stage.population is kept for kept in compared)
    }
    groups[C2A] = c2a
    groups[C2B_ONLY] = set(groups["root:expected"])
    groups[C2B] = c2b
    groups[C2C] = c2c
    groups[C2] = c2a | c2b | c2c
    return groups


def _aliases(local):
    """Which pool entries are, by identity, reconstruction stage populations."""
    geography = local.get("geography")
    if geography is None or not hasattr(geography, "stages"):
        return {}
    stages = {stage.node.id: stage.population for stage in geography.stages}
    aliases = {"geography_stage_ids": list(stages)}
    for pool in ("base_expected", "expected"):
        if isinstance(local.get(pool), dict):
            aliases[f"{pool}_is_geography_stage"] = [
                node for node, stage in stages.items() if local[pool].get(node) is stage
            ]
    if isinstance(local.get("current"), dict):
        aliases["current_is_geography_stage"] = sorted(
            version
            for version, population in local["current"].items()
            if any(population is stage for stage in stages.values())
        )
    return aliases


def _census_point(record, key, local, grains, order, split, groups_for):
    gc.collect()
    census = Census(grains)
    for name in order:
        if name in local:
            census.walk(name, local[name])
    census.walk("other_locals", [v for k, v in local.items() if k not in order])
    module_state = _module_state()
    census.walk("module_state", module_state)
    unreached = _gc_frames(census)
    census.walk("gc_unreached", unreached)
    atoms = _atoms(local, order, split, module_state, unreached)
    groups = groups_for(local, atoms)
    exclusive = exclusive_rows(
        [(name, value) for name, _, value in atoms], groups, grains
    )
    record[key] = {
        "locals": sorted(local),
        "summary": census.summary(),
        "rows": census.rows,
        "atoms": [[name, owner] for name, owner, _ in atoms],
        "groups": {group: sorted(members) for group, members in groups.items()},
        "exclusive": exclusive,
        "aliases": _aliases(local),
    }


def _run(root, patch, retention):
    arguments = _demographic_arguments(root, patch, unknown=False, zero=False)
    payload, source_ids = _support_payload()
    support_path = root / "invented-block-support.npz"
    support_path.write_bytes(payload)
    config = runner.reconstruction.AtomicSurveyReconstruction(
        support_path=str(support_path),
        support_sha256=hashlib.sha256(payload).hexdigest(),
        source_ids=tuple(sorted(source_ids.items())),
        seed=17,
    )
    call = {
        **arguments,
        "store_root": root / "store",
        "geography_config": config,
        "demographic_conditioning": True,
        "n_estimators": 2,
        "return_values": True,
        "_population_retention": retention,
    }
    # Closures hold only a SimpleNamespace: the runner's live-implementation
    # fence seals closure contents, and a growing dict would move that seal.
    holder = SimpleNamespace(record={"retention": retention, "snapshots": []})
    original_run_graph = runner.run_graph
    original_states = runner.atomic._states
    original_reconstruct = runner.reconstruction.reconstruct_atomic_survey_geography

    def run_graph(compiled, **kwargs):
        observer = kwargs.get("_population_observer")
        if observer is None:
            return original_run_graph(compiled, **kwargs)
        graph_order = tuple(compiled.order)

        def observe(node_id, population):
            shape = _snapshot_shape(node_id, population)
            shape["graph_nodes"] = len(graph_order)
            holder.record["snapshots"].append(shape)
            observer(node_id, population)

        manifest = original_run_graph(
            compiled, **{**kwargs, "_population_observer": observe}
        )
        caller = sys._getframe(1)
        if (
            caller.f_code.co_name == "run_atomic_survey_financial"
            and "post_graph_census" not in holder.record
        ):
            # Just after the 19-node run_graph returns: every detached
            # observation, the base expectations, the financial geography
            # reconstruction, the prefix and the manifest are live together.
            local = dict(caller.f_locals)
            local["manifest"] = manifest
            prefix = local["prefix"]
            grains, _ = _grains_from(
                prefix.manifest.population(runner.survey.CREATE_NODE),
                prefix.clone_population.frame,
            )
            _census_point(
                holder.record,
                "post_graph_census",
                local,
                grains,
                _LOCAL_ORDER,
                _FINANCIAL_SPLIT,
                _financial_groups,
            )
            del local, prefix
        return manifest

    def reconstruct(*args, **kwargs):
        result = original_reconstruct(*args, **kwargs)
        caller = sys._getframe(1)
        if (
            caller.f_code.co_name == "run_atomic_survey_population"
            and "geography" in caller.f_locals
            and "prefix_peak_census" not in holder.record
        ):
            local = dict(caller.f_locals)
            local["fresh"] = result
            terminal = local["geography"].nodes[-1].id
            grains, _ = _grains_from(
                local["expected"][runner.survey.CREATE_NODE].frame,
                local["observed"][terminal].frame,
            )
            _census_point(
                holder.record,
                "prefix_peak_census",
                local,
                grains,
                _PREFIX_ORDER,
                _PREFIX_SPLIT,
                _prefix_groups,
            )
            del local
        return result

    def states(*args, **kwargs):
        caller = sys._getframe(1)
        if (
            caller.f_code.co_name == "run_atomic_survey_financial"
            and "states_census" not in holder.record
        ):
            local = dict(caller.f_locals)
            holder.record["states_locals"] = sorted(local)
            prefix = local["prefix"]
            grains, counts = _grains_from(
                prefix.manifest.population(runner.survey.CREATE_NODE),
                prefix.clone_population.frame,
            )
            holder.record["fixture_counts"] = counts
            _census_point(
                holder.record,
                "states_census",
                local,
                grains,
                _LOCAL_ORDER,
                _FINANCIAL_SPLIT,
                _financial_groups,
            )
            del local, prefix
        return original_states(*args, **kwargs)

    patch.setattr(runner, "run_graph", run_graph)
    patch.setattr(runner.atomic, "_states", states)
    patch.setattr(
        runner.reconstruction, "reconstruct_atomic_survey_geography", reconstruct
    )
    result = runner.run_atomic_survey_financial(**call, resume="auto")
    return holder.record, result


def _module_state():
    """Every module-level container of the loaded microcosm modules."""
    state = []
    for name, module in list(sys.modules.items()):
        if not name.startswith("microcosm") or module is None:
            continue
        for value in vars(module).values():
            if isinstance(value, _SKIP):
                continue
            state.append(value)
    return state


def _gc_frames(census):
    """Live tables and frames the named roots did not reach."""
    found = []
    for item in gc.get_objects():
        if id(item) in census.visited:
            continue
        if isinstance(item, pd.DataFrame) or (
            type(item).__name__ == "Frame" and hasattr(item, "_tables")
        ):
            found.append(item)
    return found


def _grains_from(create, clone):
    grains = {}
    for entity in create.entities:
        grains[(entity, create.n(entity))] = "stacked"
    for entity in clone.entities:
        grains.setdefault((entity, clone.n(entity)), "cloned")
    return grains, {
        "stacked": {e: create.n(e) for e in create.entities},
        "cloned": {e: clone.n(e) for e in clone.entities},
    }


@pytest.mark.parametrize("retention", ["all", "compact"])
def test_retention_census(tmp_path, retention):
    with pytest.MonkeyPatch.context() as patch:
        record, result = _run(tmp_path, patch, retention)
    grains, _ = _grains_from(
        result.prefix.manifest.population(runner.survey.CREATE_NODE),
        result.prefix.clone_population.frame,
    )
    gc.collect()
    returned = Census(grains)
    returned.walk("returned_run", result)
    returned.walk("module_state", _module_state())
    record["returned_census"] = {"summary": returned.summary(), "rows": returned.rows}
    record["python"] = sys.version.split()[0]
    record["numpy"] = np.__version__
    record["pandas"] = pd.__version__
    existing = json.loads(OUT.read_text()) if OUT.exists() else {}
    existing[retention] = record
    OUT.write_text(json.dumps(existing, indent=1, sort_keys=True, default=str))
    assert record["snapshots"], "observer recorded nothing"
    assert "prefix_peak_census" in record, "prefix fresh reconstruction not reached"
    assert "post_graph_census" in record, "financial run_graph return not reached"
    # The replay pool holds every geography stage population, by identity, after
    # the replay (graph_atomic_survey_financial.py:2228-2232); so does the
    # prefix's expected pool (graph_atomic_survey_population.py:266-272). A
    # first-owner share charged to ``geography`` is therefore not what releasing
    # the reconstruction frees; the exclusive attribution below is.
    states = record["states_census"]["aliases"]
    assert states["expected_is_geography_stage"] == states["geography_stage_ids"]
    assert states["base_expected_is_geography_stage"] == states["geography_stage_ids"]
    prefix = record["prefix_peak_census"]["aliases"]
    assert prefix["expected_is_geography_stage"] == prefix["geography_stage_ids"]
    for key in ("prefix_peak_census", "post_graph_census", "states_census"):
        point = record[key]
        first_owner = defaultdict(int)
        for row in point["rows"]:
            first_owner[row["root"]] += row["new_bytes"]
        total = sum(first_owner.values())
        for group, rows in point["exclusive"].items():
            freed = sum(row["new_bytes"] for row in rows)
            assert freed <= total, (key, group)
            if group.startswith("root:"):
                # Bytes only one local reaches are charged to it in any order.
                assert freed <= first_owner[group[len("root:") :]], (key, group)
