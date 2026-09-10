"""Honest synthetic US support for exercising the NZ transfer, without data access."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from microcosm.frame import US_SCHEMA, Frame, WeightKind, Weights


def synthetic_us_donor(*, copies: int = 34) -> Frame:
    """Six US entity spines, two support clones, and explicit recipient families.

    The two clone roles each receive half the base design weight. Role 1 is
    PUF-detail support on the survey population, not a second PUF population.
    IDs exceed the JS safe-integer range intentionally; origin keys preserve
    zero-padded raw identifiers. All values and relationships are invented.
    """
    shapes = (
        (30,),
        (45, 42),
        (32, 7, 10),
        (35, 33, 5, 8),
        (70,),
        (72, 68),
        (25, 60),
        (40, 39, 16),
    )
    people, households = [], []
    groups = {e: [] for e in US_SCHEMA.group_entities if e != "household"}
    pid = 2**53 + 101
    for copy in range(copies):
        for shape_index, ages in enumerate(shapes):
            origin = copy * len(shapes) + shape_index
            channel = "acs" if origin % 2 == 0 else "asec"
            raw_id = f"{origin:08d}"
            for clone in (0, 1):
                hid = 2**53 + 10000 + origin * 2 + clone
                hh = {
                    "household_id": hid,
                    "donor_fixture_status": "synthetic_fixture",
                    "donor_scope": "full_common_frame_all_support_clones",
                    "survey_geography_origin_key": json.dumps(
                        [channel, 2024, 2024 if channel == "acs" else 2025, raw_id],
                        separators=(",", ":"),
                    ),
                    "donor_state_code": "06" if origin % 3 else "36",
                    "fixture_weekly_rent_usd": float(180 + (origin % 7) * 40),
                    "fixture_asset_stock_usd": float((origin % 9) * 1500),
                    "is_donor": bool(origin % 3 == 0),
                    "is_recipient": bool(origin % 3 != 0),
                }
                households.append(hh)
                for entity in groups:
                    groups[entity].append({f"{entity}_id": hid})
                for age_index, age in enumerate(ages):
                    # One deliberately multifamily household: two unrelated
                    # adults have distinct recipient families, even though the
                    # donor tax/SPM/family IDs are identical in this fixture.
                    family_offset = age_index if shape_index == 6 else 0
                    row = {
                        "person_id": pid,
                        **{f"person_{e}_id": hid for e in US_SCHEMA.group_entities},
                        "recipient_family_id": hid * 2 + family_offset,
                        "fixture_age": float(age),
                        "fixture_annual_earnings_usd": float(
                            0
                            if age < 18 or age >= 65
                            else (15000 + origin % 6 * 9000) * (0.7 if age_index else 1)
                        ),
                        "us_income_tax": 99999.0,
                        "us_snap": 8888.0,
                        "person_spine_source_id": origin * 10 + age_index,
                        "person_source_id": origin * 10 + age_index,
                        "person_support_channel": channel,
                        "person_support_clone_index": clone,
                    }
                    people.append(row)
                    pid += 1
                for entity, row in [
                    ("household", hh),
                    *[(e, groups[e][-1]) for e in groups],
                ]:
                    row.update(
                        {
                            f"{entity}_spine_source_id": origin,
                            f"{entity}_source_id": origin,
                            f"{entity}_support_channel": channel,
                            f"{entity}_support_clone_index": clone,
                        }
                    )
    tables = {
        "person": pd.DataFrame(people),
        "household": pd.DataFrame(households),
        **{e: pd.DataFrame(rows) for e, rows in groups.items()},
    }
    for table in tables.values():
        for name in table.select_dtypes(include=["object", "str"]).columns:
            table[name] = table[name].astype("string")
    return Frame(
        tables,
        US_SCHEMA,
        {"household": Weights(np.full(len(households), 0.5), WeightKind.DESIGN)},
        pd.Series(
            [f"synthetic_{r['person_support_channel']}_support" for r in people],
            dtype="string",
        ),
        metadata={
            "status": "synthetic_fixture",
            "scope": "full_common_frame_all_support_clones",
            "source_access": "invented records; no restricted data",
            "measurement": "Age at 2025-06-30; annual earnings calendar 2024; rent weekly and assets stock, all hypothetical USD",
            "recipient_membership": "Explicit fixture nuclear families; unrelated adults split. No reviewed general NZ legal-unit construction yet.",
        },
    )
