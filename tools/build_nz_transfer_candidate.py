#!/usr/bin/env python3
"""Build a local development fixture through the real NZ transfer graph."""

import argparse
import json
from pathlib import Path

from microcosm.build.nz_transfer import run_candidate
from microcosm.build.nz_transfer_fixture import synthetic_us_donor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--copies", type=int, default=2)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    targets = json.loads(
        (
            root
            / "packages/microcosm-build/tests/fixtures/nz_transfer/observed_targets.json"
        ).read_text()
    )
    result = run_candidate(synthetic_us_donor(copies=args.copies), targets, args.out)
    report = json.loads((args.out / "report.json").read_text())
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "status",
                    "rows",
                    "fit_pass",
                    "holdout_max_abs_relative_error",
                    "manifest_key",
                )
            },
            indent=2,
        )
    )
    return result


if __name__ == "__main__":
    main()
