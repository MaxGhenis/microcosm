# Retirement factorial: static f001 wiring proof

## Claim boundary

This receipt proves only that the two committed factorial revisions configure
different, canonical early-PUF predictor plans under the requested
`sample_fraction = 0.01` (`f001`) and `sample_seed = 578` controls. It is a
read-only plan/configuration receipt.

**It is not a materialized 1% artifact, terminal-gate receipt, or measurement
of any of the 16 assigned checks.** No survey source was loaded, no sampled
stack was assembled, no QRF was fit, no imputation draw was made, no simulation
frame was constructed, and no H5 or gate output was written. The removal and
broad f001 cells in `ASSIGNED_CHECKS.md` therefore remain
`NOT_RUN_RSS_CAP / not measured`, and this receipt supports no improvement
claim.

The distinction is enforced by the build flow. The configured identity is
available before input verification and binds the expected input-pin digest,
sample fraction/token, sample seed, clone controls, and live stacked authority
([`build_us_multispine_pool.py:1150-1166`](../../tools/build_us_multispine_pool.py#L1150-L1166)).
The 16 comparisons, however, require the simulated frame: the build first
materializes model outputs and only afterward calls `by_origin_battery`
([`build_us_multispine_pool.py:3221-3250`](../../tools/build_us_multispine_pool.py#L3221-L3250),
[`build_us_multispine_pool.py:3263-3271`](../../tools/build_us_multispine_pool.py#L3263-L3271)).

## Exact arm receipts

Both arms have the same required early person predictors, in this order:

1. `age`
2. `is_female`
3. `__acs_transfer_state_fips`

Their optional `person/puf_tax_itemization` predictors and identities are:

| Field | Removal-only | Broad-addition-only, direct retained |
|---|---|---|
| Commit | `1a8ad451c6eff17d405ef75cbdd014de72447153` | `539e415defb27bf103a40081239f123ce9d76c6d` |
| Sample configuration | `0.01`, token `f001`, seed `578` | `0.01`, token `f001`, seed `578` |
| Expected six-pin digest | `9506a2097a34731cf14314154a382f99de0c2fde3c8276ea794a18d6dfb196ba` | same |
| Configured namespace digest | `490866d5bfdc5981e6ff376375f0d414ed3800bb7c81abb98d27d41128f26549` | `adce8ee394cc2315422c00f3cc2838a866215e3a6ff90cb79a55b68c7a6c4c95` |
| Stacked authority | v11, `16892c623844c21955ddcd4b39b829613db749b195922cbe2b5337aeb8c4cbdd` | v11, `7f6eab189fa51627c4e78c3cfcd2517f723a909d9197e538fbfec888261d564a` |
| Gap-fill plan | `6ad7b75b193950cfb273daa1660df7e94440cc24e0806963bff5c333a94b0fdd` | `642646981e96fe67cc29e687a8a8362691bcc571c5c491426243e836f16202d6` |
| Authority checks | `canonical = true`; `digest_matches_declared = true` | `canonical = true`; `digest_matches_declared = true` |

The removal-only optional tuple is exactly:

```text
__acs_transfer_employment_income
__acs_transfer_self_employment_income
__acs_transfer_is_household_head
__acs_transfer_tenure_code
```

The broad-addition-only optional tuple is exactly:

```text
__acs_transfer_employment_income
__acs_transfer_self_employment_income
__acs_transfer_social_security_income
__acs_transfer_retirement_income
__acs_transfer_marital_status_code
__acs_transfer_relationship_code
__acs_transfer_household_person_count
__acs_transfer_is_household_head
__acs_transfer_tenure_code
__acs_transfer_difficulty_dressing_or_bathing
__acs_transfer_difficulty_hearing
__acs_transfer_difficulty_seeing
__acs_transfer_difficulty_doing_errands
__acs_transfer_difficulty_walking_or_climbing_stairs
__acs_transfer_difficulty_remembering_or_making_decisions
__acs_transfer_usual_hours_worked
__acs_transfer_weeks_worked
__acs_transfer_is_self_employed_worker
__acs_transfer_has_medicare_coverage
__acs_transfer_is_foreign_born
```

At the removal commit, the declaration subtracts only the Social Security and
retirement analogues from early person/`puf_tax_itemization` and omits the
already unavailable investment analogue (`1a8ad451:packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py:374-403`).
At the broad commit, the declaration instead selects the fixed 20-column tuple
only for that same early family
([`acs_transfer.py:191-212`](../../packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py#L191-L212),
[`acs_transfer.py:438-467`](../../packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py#L438-L467)).

The plan payload serializes required and optional predictors in their declared
order, so the plan SHA above covers the exact tuples rather than merely their
membership
([`stacked_spine.py:2211-2227`](../../packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py#L2211-L2227)).
The production authority recomputes the live component and bundle digests and
rejects noncanonical content before returning its receipt
([`stacked_spine.py:3394-3403`](../../packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py#L3394-L3403),
[`stacked_spine.py:3426-3462`](../../packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py#L3426-L3462)).
The configured namespace then hashes that authority together with the f001
controls and six expected pins, making the two arm namespaces necessarily
distinct
([`build_us_multispine_pool.py:1150-1178`](../../tools/build_us_multispine_pool.py#L1150-L1178)).

## Read-only reproduction command

The following is the exact probe shape used from the broad-arm checkout. It
does not switch commits or write a worktree. For each arm it loads the two
commit-specific modules directly from Git object bytes in memory, then calls
the production plan and configured-identity functions. `PYTHONDONTWRITEBYTECODE`
also prevents import-cache writes.

```bash
for ARM_SHA in \
  1a8ad451c6eff17d405ef75cbdd014de72447153 \
  539e415defb27bf103a40081239f123ce9d76c6d
do
  env \
    ARM_SHA="$ARM_SHA" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=packages/microcosm-frame/src:packages/microcosm-fit/src:packages/microcosm-calibrate/src:packages/microcosm-build/src:packages/microcosm-data/src \
    /Users/maxghenis/PolicyEngine/_worktrees/microcosm-arm-split/.venv/bin/python - <<'PY'
import hashlib
import importlib.abc
import importlib.util
import json
import os
import runpy
import subprocess
import sys
from types import SimpleNamespace

commit = os.environ["ARM_SHA"]
sources = {
    "microcosm.build.us_runtime.acs_transfer": (
        "packages/microcosm-build/src/microcosm/build/us_runtime/acs_transfer.py"
    ),
    "microcosm.build.us_runtime.stacked_spine": (
        "packages/microcosm-build/src/microcosm/build/us_runtime/stacked_spine.py"
    ),
}


class GitObjectLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        if fullname not in sources:
            return None
        return importlib.util.spec_from_loader(fullname, self)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        raw = subprocess.check_output(
            ["git", "show", f"{commit}:{sources[module.__name__]}"]
        )
        exec(
            compile(raw, f"{commit}:{sources[module.__name__]}", "exec"),
            module.__dict__,
        )


sys.meta_path.insert(0, GitObjectLoader())
tool = runpy.run_path("tools/build_us_multispine_pool.py")
from microcosm.build.us_runtime.stacked_spine import (  # noqa: E402
    stacked_gap_fill_plan,
)

args = SimpleNamespace(
    sample_fraction=0.01,
    sample_seed=578,
    clone_attachment_fraction=1.0,
    clone_attachment_seed=578,
    asec_raw_stage_h5_sha256=(
        "51e9fafcd6f16140018fa90c7afbeb6d79008bfc8c122e437d23a399b30553fe"
    ),
    acs_household_zip_sha256=(
        "8281008e53de98f0ef81e7a2ee5a8725991dda1ecfd2713ead73246425e515d0"
    ),
    acs_person_zip_sha256=(
        "afdc6d90c6e2f0bab365ed32d95ba4c4d8ac651162f46ac7861295b2dc469894"
    ),
    acs_rent_h5_sha256=(
        "0b319b496f19a6913066f9c5ea572edfda3d78a187be6f375846617d0b441bd4"
    ),
    puf_h5_sha256=(
        "7669f5b5281f20080e77204f9bd4aabfad0aa101fa283e22caf9ba8d61d4d6df"
    ),
    puf_source_year_csv_sha256=(
        "0a7fd643edb1acc55c507db795914b41d232922be78c149b58d111f4672499df"
    ),
)
configured = tool["_configured_stacked_identity"](args)
configured_sha256 = hashlib.sha256(
    tool["_canonical_json_bytes"](configured)
).hexdigest()
direction = next(
    item for item in stacked_gap_fill_plan() if item.name == "asec_survey_to_acs"
)
predictors = direction.predictor_sets["person"]["puf_tax_itemization"]
authority = configured["stacked_authority"]
print(
    json.dumps(
        {
            "commit": commit,
            "sample_fraction": configured["sample_fraction"],
            "fraction_token": configured["fraction_token"],
            "sample_seed": configured["sample_seed"],
            "expected_input_pins_digest": configured[
                "expected_input_pins_digest"
            ],
            "configured_namespace_sha256": configured_sha256,
            "required": list(predictors.required),
            "optional": list(predictors.optional),
            "authority_version": authority["version"],
            "authority_sha256": authority["sha256"],
            "gap_fill_plan_sha256": authority["components"]["gap_fill_plan"][
                "sha256"
            ],
            "canonical": authority["canonical"],
            "digest_matches_declared": authority["digest_matches_declared"],
        },
        indent=2,
        sort_keys=True,
    )
)
PY
done
```

The build driver and `stacked_spine.py` are byte-identical between the two arm
commits. The probe runs that unchanged driver from the working tree and loads
the commit-specific `stacked_spine.py` and `acs_transfer.py` from Git; the
latter supplies the different canonical per-family declaration. The probe
embeds the six frozen expected hashes but deliberately does not open or hash
the input files. Full input verification is a separate streaming preflight in
`_verify_inputs`
([`build_us_multispine_pool.py:650-746`](../../tools/build_us_multispine_pool.py#L650-L746)).

## Why the old f001 checkpoint cannot prove either arm

The only complete historical 1% checkpoint found is:

```text
/Users/maxghenis/PolicyEngine/_buildo-runtime/out/smoke-f001-r10/
  populace_us_2024_stacked_pool_verify.checkpoints/stacked/
  2e45c4d60f66b4321bc00ffa22816470bf162c59fd91956514832f97e066ed3c/
  simulated.checkpoint.manifest.json
```

A read-only `jq` inspection gives:

```json
{
  "configured_namespace": "2e45c4d60f66b4321bc00ffa22816470bf162c59fd91956514832f97e066ed3c",
  "sample_fraction": 0.01,
  "sample_seed": 578,
  "authority_version": 10,
  "authority_sha256": "f0b676f6508dbf6bb2b787c42e6b85331bacc57c6649ac7ad15fdaa5884a1b2d",
  "gap_fill_plan_sha256": "f70bc89cd887504645bd299501e9a63ea23726fb8d9f3fe523092639e251fe0f"
}
```

That v10 baseline identity is different from both v11 treatment identities
and lives under a third configured namespace. Discovery recomputes the full
current identity from a candidate manifest and accepts it only on exact
equality, including current authority and sampling
([`build_us_multispine_pool.py:1181-1244`](../../tools/build_us_multispine_pool.py#L1181-L1244)).
Consequently the old simulated checkpoint is stale for both arms; copying,
renaming, or relabeling it would defeat the authentication contract and is not
an admissible resume.

There is also no metadata-only full resume authenticator. After manifest
identity and file-hash checks, `_PoolStageCheckpointStore._load` reconstructs
the complete `Frame` with `load_frame_checkpoint`
([`build_us_multispine_pool.py:1715-1808`](../../tools/build_us_multispine_pool.py#L1715-L1808)).
The CLI exposes no `--dry-run`, `--plan-only`, or `--verify-only` option
([`build_us_multispine_pool.py:406-532`](../../tools/build_us_multispine_pool.py#L406-L532));
without an exact same-arm checkpoint, it proceeds to source loading and cold
assembly
([`build_us_multispine_pool.py:4227-4268`](../../tools/build_us_multispine_pool.py#L4227-L4268)).

Therefore the strongest safe proof available below the standing RSS ceiling is
the static, commit-bound configured receipt above. An actual f001 result still
requires either a newly materialized below-cap arm artifact or a previously
materialized, exact-same-identity arm checkpoint. Neither exists.
