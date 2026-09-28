"""Synthetic block -> congressional-district plan registries for US tests.

The real registry (``microcosm.build.us_runtime.cd_plan_registry``) refuses a
state whose district roster differs from its apportionment, so a registry
built for a synthetic ladder needs two things:

- :func:`registry_ready_blocks` rewrites a :func:`~test_support.microcosm_build.
  us_block_location.synthetic_blocks` ladder's own (119th) districts to codes
  its 2020 apportionment admits, leaving every other array unchanged;
- :func:`write_cd_plan_registry` then assembles the four plans the real
  registry carries. Each plan gives the ladder's blocks a district derived
  deterministically from the 119th, and extra "filler" blocks outside the
  ladder complete every state's roster. The 119th agrees with the ladder
  block for block, as the real registry does.

The pinned loader refuses every file but the packaged one, so tests that run
it on a synthetic registry pin that file's digest with
:func:`pin_cd_plan_registry`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from microcosm.build.us_runtime import cd_plan_registry
from microcosm.build.us_runtime.cd_plan_registry import (
    PRIMARY_CD_PLAN,
    US_HOUSE_APPORTIONMENT,
    assemble_us_cd_plan_registry,
    cd_block_assignment,
)

#: Plans of the real registry and the apportionment each is drawn under.
REGISTRY_PLAN_APPORTIONMENT = {
    "117th_congress": "2010_census",
    "118th_congress": "2020_census",
    "119th_congress": "2020_census",
    "120th_congress": "2020_census",
}
#: Known deviations shaped like the real registry's (117th North Carolina,
#: 120th Missouri): per plan, state FIPS -> provenance carried verbatim.
KNOWN_DEVIATIONS = {
    "117th_congress": {
        "37": {"note": "test: 2019 HB 1029 plan via the 2010->2020 relationship file"}
    },
    "120th_congress": {
        "29": {
            "note": "test: keeps the 2022 map (26A388)",
            "from_plan": "119th_congress",
        }
    },
}
_FILLER_COUNTY = 999
_SHA = "0" * 64
_BLOCK_STATE_DIVISOR = 10**13


def seats(apportionment: str, state: int) -> int:
    """District count of ``state`` (DC and at-large states have one)."""

    return max(US_HOUSE_APPORTIONMENT[apportionment][f"{state:02d}"], 1)


def _code(district: int, count: int) -> int:
    """A district code the roster ``count`` admits: ``00`` at large, else 1..count."""

    if count == 1:
        return 0
    return (max(district, 1) - 1) % count + 1


def registry_ready_blocks(arrays: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    """``arrays`` with each block's district made valid under 2020 apportionment.

    Only ``congressional_district_geoid`` changes; the block, its population,
    PUMA and every other layer are untouched, so households drawn against the
    ladder keep their states and candidate sets.
    """

    out = {key: np.asarray(value).copy() for key, value in arrays.items()}
    cd = np.asarray(out["congressional_district_geoid"], dtype=np.int64)
    state = np.asarray(out["block_geoid"], dtype=np.int64) // _BLOCK_STATE_DIVISOR
    out["congressional_district_geoid"] = np.asarray(
        [
            s * 100 + _code(int(d % 100), seats("2020_census", int(s)))
            for s, d in zip(state.tolist(), cd.tolist(), strict=True)
        ],
        dtype=np.int64,
    )
    return out


def plan_districts(
    block_geoid: np.ndarray, primary: np.ndarray
) -> dict[str, np.ndarray]:
    """Each plan's district for the ladder's blocks, derived from the 119th.

    The 119th is ``primary`` itself. The 118th and 120th rotate every second
    block of multi-seat states to the next district (at different phases, so
    the two differ from each other and from the 119th); the 117th maps the
    119th code onto the 2010 roster.
    """

    blocks = np.asarray(block_geoid, dtype=np.int64)
    cd = np.asarray(primary, dtype=np.int64)
    state = blocks // _BLOCK_STATE_DIVISOR
    code = cd % 100
    out: dict[str, np.ndarray] = {PRIMARY_CD_PLAN: cd.copy()}
    for plan, phase in (("118th_congress", 0), ("120th_congress", 1)):
        rotated = []
        for index, (s, c) in enumerate(zip(state.tolist(), code.tolist(), strict=True)):
            count = seats(REGISTRY_PLAN_APPORTIONMENT[plan], s)
            moved = count > 1 and index % 2 == phase
            rotated.append(s * 100 + (_code(c % count + 1, count) if moved else c))
        out[plan] = np.asarray(rotated, dtype=np.int64)
    out["117th_congress"] = np.asarray(
        [
            s * 100 + _code(c, seats("2010_census", s))
            for s, c in zip(state.tolist(), code.tolist(), strict=True)
        ],
        dtype=np.int64,
    )
    return out


def plan_spec(plan: str, *, known_deviations: bool = True) -> dict[str, Any]:
    """Registry plan metadata (the keys the loader requires, plus deviations)."""

    spec: dict[str, Any] = {
        "vintage": plan,
        "source": f"test source for {plan}",
        "url": f"https://example.test/{plan}.zip",
        "apportionment": REGISTRY_PLAN_APPORTIONMENT[plan],
        "source_files": {
            plan: {"url": f"https://example.test/{plan}.zip", "sha256": _SHA}
        },
    }
    if known_deviations and plan in KNOWN_DEVIATIONS:
        spec["known_deviations"] = KNOWN_DEVIATIONS[plan]
    return spec


def cd_plan_registry_payload(
    arrays: Mapping[str, np.ndarray],
    *,
    plans: Sequence[str] = tuple(REGISTRY_PLAN_APPORTIONMENT),
    overrides: Mapping[str, Mapping[int, int]] | None = None,
    known_deviations: bool = True,
) -> dict[str, np.ndarray]:
    """The NPZ payload of a registry covering every block of ``arrays``.

    ``arrays`` must already be :func:`registry_ready_blocks`. ``overrides``
    replaces single ``{block: district}`` assignments of one plan (for
    disagreement tests); the result must still pass the registry's checks.
    """

    blocks = np.asarray(arrays["block_geoid"], dtype=np.int64)
    ladder_population = np.asarray(arrays["population"], dtype=np.int64)
    by_plan = plan_districts(blocks, arrays["congressional_district_geoid"])
    states = sorted({int(s) for s in (blocks // _BLOCK_STATE_DIVISOR).tolist()})
    filler: list[int] = []
    filler_districts: dict[str, list[int]] = {plan: [] for plan in plans}
    for state in states:
        needed = max(seats(REGISTRY_PLAN_APPORTIONMENT[plan], state) for plan in plans)
        for index in range(needed):
            filler.append(
                int(f"{state:02d}{_FILLER_COUNTY:03d}{999_000 + index:06d}9000")
            )
            for plan in plans:
                count = seats(REGISTRY_PLAN_APPORTIONMENT[plan], state)
                filler_districts[plan].append(
                    state * 100 + _code(index % count + 1, count)
                )
    universe = np.concatenate([blocks, np.asarray(filler, dtype=np.int64)])
    population = np.concatenate(
        [ladder_population, np.ones(len(filler), dtype=np.int64)]
    )
    assignments = {}
    for plan in plans:
        pairs = dict(
            zip(
                universe.tolist(),
                [*by_plan[plan].tolist(), *filler_districts[plan]],
                strict=True,
            )
        )
        pairs.update((overrides or {}).get(plan, {}))
        assignments[plan] = cd_block_assignment(pairs, label=plan)
    return assemble_us_cd_plan_registry(
        block_geoid=universe,
        population=population,
        plan_assignments=assignments,
        plan_sources={
            plan: plan_spec(plan, known_deviations=known_deviations) for plan in plans
        },
    )


def write_cd_plan_registry(
    path: Path, arrays: Mapping[str, np.ndarray], **kwargs: Any
) -> Path:
    """Write :func:`cd_plan_registry_payload` to ``path`` (NPZ)."""

    np.savez_compressed(path, **cd_plan_registry_payload(arrays, **kwargs))
    return path


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin_cd_plan_registry(monkeypatch: Any, path: Path) -> str:
    """Make ``path`` the registry the pinned loader accepts; return its digest.

    Patches :func:`cd_plan_registry.packaged_us_cd_plan_registry_provenance`,
    which :func:`cd_plan_registry.load_pinned_us_cd_plan_registry` reads at
    call time, so every caller of the pinned loader sees the pin.
    """

    digest = file_sha256(path)
    monkeypatch.setattr(
        cd_plan_registry,
        "packaged_us_cd_plan_registry_provenance",
        lambda: {"output_sha256": digest},
    )
    return digest


__all__ = [name for name in globals() if not name.startswith("__")]
