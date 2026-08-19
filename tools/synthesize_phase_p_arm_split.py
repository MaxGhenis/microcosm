#!/usr/bin/env python3
"""Build the exhaustive Phase-P arm-attribution synthesis from committed verdicts."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUND1_PATH = Path(
    "/Users/maxghenis/PolicyEngine/_worktrees/microcosm-predictor-sets/"
    "experiments/phase_p_predictor_sets/verdict.json"
)
OUTPUT = ROOT / "experiments/phase_p_arm_split/SYNTHESIS.md"
CONFIG_SHA256 = "10f29427d83c340973869fb735188967aff9a4eea770b066f604e7a28a0b5e5a"
BASELINE_IDENTITY = "9be8ecdf82356f38998e8b620ee36d9134f554fe89a8eafd8406f438e2b5aad6"

SOURCE_META = OrderedDict(
    [
        (
            "R1",
            {
                "label": "round-1 bundle",
                "locator": str(ROUND1_PATH),
                "commit": "predictor-sets@df6bd65b",
                "sha256": "3abc932602de54f4847c2c5ca16ea39713284e106e1f3928c538d5d01c2c3f26",
                "artifact": (
                    "/Users/maxghenis/PolicyEngine/_worktrees/"
                    "microcosm-predictor-sets/_buildo-runtime/out/"
                    "stacked-f025-predictor-sets-r1/"
                ),
            },
        ),
        (
            "O",
            {
                "label": "order arm",
                "locator": (
                    "arm-order@9d6eecb4:experiments/phase_p_arm_split/"
                    "order/verdict.json"
                ),
                "git_ref": (
                    "arm-order:experiments/phase_p_arm_split/order/verdict.json"
                ),
                "commit": "arm-order@9d6eecb4",
                "sha256": "75e74a8e7cf4615eb12b5cb9efad189cc8b0f57a82f42a3315e0914f881f9059",
                "artifact": (
                    "/Users/maxghenis/PolicyEngine/_worktrees/"
                    "microcosm-arm-split/_buildo-runtime/out/"
                    "stacked-f025-arm-order-r1/"
                ),
            },
        ),
        (
            "E",
            {
                "label": "eligibility arm",
                "locator": (
                    "arm-eligibility@1ffea7ae:experiments/phase_p_arm_split/"
                    "eligibility/verdict.json"
                ),
                "git_ref": (
                    "arm-eligibility:experiments/phase_p_arm_split/"
                    "eligibility/verdict.json"
                ),
                "commit": "arm-eligibility@1ffea7ae",
                "sha256": "bf531f48f4efa6969680c306718f2e46fb88876ccf46f5cfa1fb543429beb79d",
                "artifact": (
                    "/Users/maxghenis/PolicyEngine/_worktrees/"
                    "microcosm-arm-split/_buildo-runtime/out/"
                    "stacked-f025-arm-eligibility-r1/"
                ),
            },
        ),
        (
            "I",
            {
                "label": "investment arm",
                "locator": (
                    "arm-investment@5cf6a306:experiments/phase_p_arm_split/"
                    "investment/verdict.json"
                ),
                "git_ref": (
                    "arm-investment:experiments/phase_p_arm_split/"
                    "investment/verdict.json"
                ),
                "commit": "arm-investment@5cf6a306",
                "sha256": "c430aa4f625f9b00956a91ee3d6bb57809562aa933b6e2628b3f8675f83be22c",
                "artifact": (
                    "/Users/maxghenis/PolicyEngine/_worktrees/"
                    "microcosm-arm-split/_buildo-runtime/out/"
                    "stacked-f025-arm-investment-r1/"
                ),
            },
        ),
    ]
)


def load_sources() -> OrderedDict[str, dict]:
    sources: OrderedDict[str, dict] = OrderedDict()
    for tag, meta in SOURCE_META.items():
        if tag == "R1":
            raw = ROUND1_PATH.read_bytes()
        else:
            raw = subprocess.check_output(["git", "show", meta["git_ref"]], cwd=ROOT)
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == meta["sha256"], (tag, digest, meta["sha256"])
        sources[tag] = json.loads(raw)
    return sources


def fmt(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def tagged(value: object, tag: str) -> str:
    return f"{fmt(value)} `{tag}`"


def code(value: str) -> str:
    return f"`{value.replace('`', '&#96;')}`"


def ci_flag(row: dict, tag: str) -> str:
    low, high = row["paired"]["candidate_minus_baseline_ci"]
    if high < 0:
        return f"yes—better `{tag}`"
    if low > 0:
        return f"yes—worse `{tag}`"
    return f"no `{tag}`"


def money_rows(verdict: dict) -> dict[str, dict]:
    return {
        row["key"]: row for row in verdict["oos_pinball_loss"] if row["is_money_amount"]
    }


def battery_rows(verdict: dict) -> dict[str, dict]:
    return {row["leg_id"]: row for row in verdict["by_origin_battery"]["legs"]}


def diagnostic(side: dict, tag: str) -> str:
    if side["ratio"] is not None:
        value = f"ratio={tagged(side['ratio'], tag)}"
    elif side["total_variation_distance"] is not None:
        value = f"TVD={tagged(side['total_variation_distance'], tag)}"
    elif side["quantile_envelope_distance"] is not None:
        value = f"QED={tagged(side['quantile_envelope_distance'], tag)}"
    else:
        value = "diagnostic=—"
    return f"{side['band_status']}; {side['gate_status']}; {value}"


def stat_counts(verdict: dict) -> tuple[int, int, int]:
    rows = list(money_rows(verdict).values())
    better = sum(row["paired"]["candidate_minus_baseline_ci"][1] < 0 for row in rows)
    worse = sum(row["paired"]["candidate_minus_baseline_ci"][0] > 0 for row in rows)
    return better, worse, len(rows) - better - worse


def normalized_config(verdict: dict) -> dict:
    config = copy.deepcopy(verdict["config"])
    del config["execution_surface"]["artifact_role_bindings"]["candidate"]
    return config


def validate(sources: OrderedDict[str, dict]) -> dict:
    tags = list(sources)
    assert tags == ["R1", "O", "E", "I"]
    for tag, verdict in sources.items():
        assert verdict["measurement_complete"] is True, tag
        assert verdict["family_count"] == 32, tag
        assert verdict["target_count"] == 118, tag
        assert len(money_rows(verdict)) == 74, tag
        assert verdict["by_origin_battery"]["counts"]["total_legs"] == 211, tag
        assert len(battery_rows(verdict)) == 211, tag

    reference_config = normalized_config(sources["R1"])
    for tag in tags[1:]:
        assert normalized_config(sources[tag]) == reference_config, tag

    money = {tag: money_rows(verdict) for tag, verdict in sources.items()}
    money_keys = sorted(money["R1"])
    for tag in tags[1:]:
        assert sorted(money[tag]) == money_keys, tag
    for key in money_keys:
        baseline = money["R1"][key]["paired"]["baseline_mean_pinball_loss"]
        for tag in tags[1:]:
            assert money[tag][key]["paired"]["baseline_mean_pinball_loss"] == baseline

    battery = {tag: battery_rows(verdict) for tag, verdict in sources.items()}
    battery_keys = sorted(battery["R1"])
    for tag in tags[1:]:
        assert sorted(battery[tag]) == battery_keys, tag
    for key in battery_keys:
        baseline = battery["R1"][key]["baseline"]
        for tag in tags[1:]:
            assert battery[tag][key]["baseline"] == baseline, (tag, key)

    assert all(
        row["paired"]["candidate_minus_baseline"] == 0.0 for row in money["O"].values()
    )
    retirement = {
        tag: next(
            row
            for row in verdict["oos_pinball_loss"]
            if row["target"] == "social_security_retirement"
        )
        for tag, verdict in sources.items()
    }
    r1_base = set(retirement["R1"]["baseline"]["resolved_predictors"])
    r1_candidate = set(retirement["R1"]["candidate"]["resolved_predictors"])
    r1_removed = sorted(r1_base - r1_candidate)
    r1_added = sorted(r1_candidate - r1_base)
    assert r1_removed == [
        "__acs_transfer_retirement_income",
        "__acs_transfer_social_security_income",
    ]
    assert len(r1_added) == 14

    transitions = {
        tag: {
            key: row["transition"]
            for key, row in rows.items()
            if row["transition"] in {"entered_band", "left_band"}
        }
        for tag, rows in battery.items()
    }
    shared_e = sorted(set(transitions["R1"]) & set(transitions["E"]))
    shared_i = sorted(set(transitions["R1"]) & set(transitions["I"]))
    shared_o = sorted(set(transitions["R1"]) & set(transitions["O"]))
    assert len(shared_e) == 10
    assert len(shared_i) == 1
    assert len(shared_o) == 0
    isolated = set(transitions["E"]) | set(transitions["I"]) | set(transitions["O"])
    assert len(set(transitions["R1"]) - isolated) == 24

    r1_worse = [
        row
        for row in money["R1"].values()
        if row["paired"]["candidate_minus_baseline_ci"][0] > 0
    ]
    late_worse = [row for row in r1_worse if row["stage"] == "late_transfer"]
    assert len(r1_worse) == 21
    assert len(late_worse) == 14
    return {
        "money": money,
        "money_keys": money_keys,
        "battery": battery,
        "battery_keys": battery_keys,
        "retirement": retirement,
        "r1_added": r1_added,
        "transitions": transitions,
        "shared_e": shared_e,
        "shared_i": shared_i,
    }


def add_decision_and_sources(lines: list[str], sources: OrderedDict[str, dict]) -> None:
    lines.extend(
        [
            "# Phase P predictor-set arm attribution",
            "",
            "## Decision",
            "",
            "**No isolated arm is landable as an authored F1 predictor-set change.** "
            "Order has no money benefit; eligibility has significant money regressions "
            "and battery exits; investment has significant money improvements but also "
            "battery exits. This is an attribution verdict for the full money set and full "
            "battery, not a publication decision and not a CHAMPVA-specific project.",
            "",
            "| Configuration | Significant money better / worse / neither | Battery entered / left | Frozen clauses A / B / C | Landable |",
            "|---|---:|---:|---|---|",
        ]
    )
    for tag, verdict in sources.items():
        better, worse, neither = stat_counts(verdict)
        counts = verdict["by_origin_battery"]["counts"]
        clauses = verdict["clauses"]
        clause_text = " / ".join(
            "PASS" if clauses[name]["passed"] else "FAIL"
            for name in (
                "a_champva",
                "b_money_oos",
                "c_no_battery_leg_leaves_band",
            )
        )
        reasons = {
            "R1": "No—bundled regressions and battery exits",
            "O": "No—every money delta is exactly zero",
            "E": "No—money regressions and battery exits",
            "I": "No—battery exits",
        }
        lines.append(
            f"| {SOURCE_META[tag]['label']} `{tag}` | "
            f"{tagged(better, tag)} / {tagged(worse, tag)} / {tagged(neither, tag)} | "
            f"{tagged(counts['entered_band'], tag)} / {tagged(counts['left_band'], tag)} | "
            f"{clause_text} `{tag}` | {reasons[tag]} `{tag}` |"
        )

    lines.extend(
        [
            "",
            "## Evidence registry and source-tag rule",
            "",
            "Every measurement number below is immediately followed by a source tag. "
            "The tag expands to this immutable commit-qualified verdict path; the verdict "
            "in turn binds the artifact path and checkpoint receipts. A slash-composite "
            "tag such as `R1/O/E/I` means the value was validated identically in every "
            "listed source.",
            "",
        ]
    )
    for tag, meta in SOURCE_META.items():
        lines.append(
            f"- `{tag}` — {meta['label']}; `{meta['commit']}`; verdict "
            f"`{meta['locator']}`; verdict SHA-256 `{meta['sha256']}`; candidate artifact "
            f"`{meta['artifact']}`."
        )
    lines.extend(
        [
            "- Shared baseline artifact — "
            "`/Users/maxghenis/PolicyEngine/_buildo-runtime/out/stacked-f025-r1/`; "
            f"stacked identity `{BASELINE_IDENTITY}`; bound under `.artifacts.baseline` "
            "in `R1`, `O`, `E`, and `I`.",
            "- Spec schema — `spec-engine-schema@b027dcb0:packages/"
            "microcosm-build/src/microcosm/build/spec_engine/schema/"
            "imputation.schema.json` (`SCHEMA`).",
            "",
            "All verdicts report complete "
            f"{tagged(32, 'R1/O/E/I')}-family / "
            f"{tagged(118, 'R1/O/E/I')}-target / "
            f"{tagged(74, 'R1/O/E/I')}-money-target / "
            f"{tagged(211, 'R1/O/E/I')}-battery-leg measurement. After deleting only "
            "`.config.execution_surface.artifact_role_bindings.candidate`, every "
            f"configuration has audited hash `{CONFIG_SHA256}` (`R1/O/E/I`).",
            "",
            "## Treatment boundary",
            "",
            "- `O` changes only the declared target order in "
            "`gap_fill/asec_survey_to_acs/person/model_required_boolean`; other "
            "families retain baseline predictor sets.",
            "- `E` retains the baseline resolved predictors and adds "
            "`__acs_transfer_difficulty_hearing`, `__acs_transfer_difficulty_seeing`, "
            "and `__acs_transfer_has_medicare_coverage` to the PUF-tax and numeric "
            "families, with Medicare alone added to the boolean family. The `HINS3` "
            "object-dtype decode fix is included in the artifact.",
            "- `I` makes `__acs_transfer_interest_dividend_rental_income` observable in "
            "eight person families and `__acs_transfer_group_investment_income_sum` "
            "observable in four SPM families; it does not opt the early PUF-tax family in.",
            "- `R1` is not merely the union of those arms. It uses a broader early PUF "
            "predictor replacement and supplies an explicit eight-column PUF-detail "
            "predictor set to every late transfer. Isolated arms retain the baseline "
            "late-transfer surface, so bundle-only effects cannot be assigned to an arm.",
            "",
        ]
    )


def add_money_table(lines: list[str], data: dict) -> None:
    money = data["money"]
    lines.extend(
        [
            "## Four-way money-target table",
            "",
            "Rows are `.oos_pinball_loss[] | select(.is_money_amount)` keyed by `.key`. "
            "OOS and delta are stored under `.paired`; the CI flag is `yes—better` only "
            "when the stored CI upper endpoint is below zero, `yes—worse` only when its "
            "lower endpoint is above zero, and `no` otherwise. The shared baseline was "
            "validated exactly across `R1/O/E/I`.",
            "",
            "| Money target | Baseline OOS | Bundle candidate OOS | Bundle Δ | Bundle CI excludes zero | Order candidate OOS | Order Δ | Order CI excludes zero | Eligibility candidate OOS | Eligibility Δ | Eligibility CI excludes zero | Investment candidate OOS | Investment Δ | Investment CI excludes zero |",
            "|---|---:|---:|---:|---|---:|---:|---|---:|---:|---|---:|---:|---|",
        ]
    )
    for key in data["money_keys"]:
        r1 = money["R1"][key]
        cells = [
            code(key),
            tagged(r1["paired"]["baseline_mean_pinball_loss"], "R1/O/E/I"),
        ]
        for tag in ("R1", "O", "E", "I"):
            row = money[tag][key]
            cells.extend(
                [
                    tagged(row["paired"]["candidate_mean_pinball_loss"], tag),
                    tagged(row["paired"]["candidate_minus_baseline"], tag),
                    ci_flag(row, tag),
                ]
            )
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")


def add_battery_table(lines: list[str], data: dict) -> None:
    battery = data["battery"]
    lines.extend(
        [
            "## Four-way battery-leg table",
            "",
            "Rows are `.by_origin_battery.legs[]` keyed by `.leg_id`. Candidate cells "
            "show stored band status, gate status, the available ratio/TVD/QED diagnostic, "
            "stored `.transition`, and `.gate_status_transition`. A dash preserves a null "
            "diagnostic; it is not zero. All baseline battery objects were validated "
            "exactly across the four verdict paths. `entered_band` and `left_band` are "
            "ratio-band transitions; another battery criterion may still determine gate "
            "status.",
            "",
            "| Battery leg | Metric | Shared baseline | Bundle candidate / transition | Order candidate / transition | Eligibility candidate / transition | Investment candidate / transition |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for key in data["battery_keys"]:
        r1 = battery["R1"][key]
        cells = [
            code(key),
            code(r1["metric"]),
            diagnostic(r1["baseline"], "R1/O/E/I"),
        ]
        for tag in ("R1", "O", "E", "I"):
            row = battery[tag][key]
            cells.append(
                f"{diagnostic(row['candidate'], tag)}; {row['transition']}; "
                f"{row['gate_status_transition']} `{tag}`"
            )
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")


def add_clause_table(lines: list[str], sources: OrderedDict[str, dict]) -> None:
    lines.extend(
        [
            "## Frozen clause table",
            "",
            "Clause A is the frozen CHAMPVA ratio-band/progress clause, reported as one "
            "battery leg rather than the organizing objective. Clause B forbids a money "
            "target whose candidate-minus-baseline OOS CI lower endpoint is above zero. "
            "Clause C forbids any battery leg leaving the ratio band.",
            "",
            "| Configuration | Clause A | Clause B | Clause C | Overall |",
            "|---|---|---|---|---|",
        ]
    )
    for tag, verdict in sources.items():
        a = verdict["clauses"]["a_champva"]
        b = verdict["clauses"]["b_money_oos"]
        c = verdict["clauses"]["c_no_battery_leg_leaves_band"]
        champva = verdict["champva_ratio_bootstrap"]
        a_ci = champva["baseline_minus_candidate_ci"]
        a_text = (
            f"{'PASS' if a['passed'] else 'FAIL'}; ratio "
            f"{tagged(champva['baseline_ratio'], tag)} → "
            f"{tagged(champva['candidate_ratio'], tag)}; progress "
            f"{tagged(a['progress_from_baseline_to_band_ceiling'], tag)}; "
            f"baseline−candidate CI [{tagged(a_ci[0], tag)}, {tagged(a_ci[1], tag)}]"
        )
        b_text = (
            f"{'PASS' if b['passed'] else 'FAIL'}; significantly worsened "
            f"{tagged(len(b['significantly_worsened_targets']), tag)} / "
            f"{tagged(b['money_target_count'], tag)}"
        )
        c_text = (
            f"{'PASS' if c['passed'] else 'FAIL'}; left band "
            f"{tagged(c['leaving_band_count'], tag)} / "
            f"{tagged(verdict['by_origin_battery']['counts']['total_legs'], tag)}"
        )
        lines.append(
            f"| {SOURCE_META[tag]['label']} `{tag}` | {a_text} | {b_text} | "
            f"{c_text} | {verdict['verdict']} `{tag}` |"
        )
    lines.append("")


def add_attribution(
    lines: list[str], sources: OrderedDict[str, dict], data: dict
) -> None:
    retirement = data["retirement"]
    r1 = retirement["R1"]["paired"]
    eligibility = retirement["E"]["paired"]
    r1_ci = r1["candidate_minus_baseline_ci"]
    e_ci = eligibility["candidate_minus_baseline_ci"]
    transitions = data["transitions"]
    shared_e = [
        key
        for key in data["shared_e"]
        if transitions["R1"][key] == transitions["E"][key]
    ]
    shared_i = [
        key
        for key in data["shared_i"]
        if transitions["R1"][key] == transitions["I"][key]
    ]
    assert len(shared_e) == 10
    assert shared_i == ["spm_unit/model_required_boolean/is_tanf_enrolled[clone_0]"]
    lines.extend(
        [
            "## Attribution supported by the evidence",
            "",
            "### Retirement cluster",
            "",
            "The retirement blowup is a **bundle-only predictor-replacement effect or "
            "interaction**, not an effect reproduced by any isolated arm. "
            f"`social_security_retirement` moves from {tagged(r1['baseline_mean_pinball_loss'], 'R1')} "
            f"to {tagged(r1['candidate_mean_pinball_loss'], 'R1')} in the bundle, delta "
            f"{tagged(r1['candidate_minus_baseline'], 'R1')} with CI "
            f"[{tagged(r1_ci[0], 'R1')}, {tagged(r1_ci[1], 'R1')}]. Order and investment "
            f"are exactly unchanged at {tagged(retirement['O']['paired']['candidate_mean_pinball_loss'], 'O')} "
            f"and {tagged(retirement['I']['paired']['candidate_mean_pinball_loss'], 'I')}. "
            f"Eligibility reaches {tagged(eligibility['candidate_mean_pinball_loss'], 'E')}, "
            f"delta {tagged(eligibility['candidate_minus_baseline'], 'E')} with CI "
            f"[{tagged(e_ci[0], 'E')}, {tagged(e_ci[1], 'E')}], so the three-column "
            "eligibility arm does not reproduce the harm.",
            "",
            "For that target, the bundle's resolved predictor set removes "
            "`__acs_transfer_social_security_income` and "
            "`__acs_transfer_retirement_income` while adding "
            f"{tagged(len(data['r1_added']), 'R1')} broader predictors. Eligibility "
            "retains both direct income predictors and adds only hearing, seeing, and "
            "Medicare. Loss of the direct income predictors is the leading hypothesis "
            "suggested by this contrast, but it is not isolated from the simultaneous "
            "additions or bundle interactions.",
            "",
            "The non-additivity extends to the cluster: the bundle significantly worsens "
            "social-security disability, dependents, survivors, taxable IRA, taxable "
            "private pension, tax-exempt private pension, and taxable SEP rows shown in "
            "the money table. Isolated arms do not reproduce those magnitudes; investment "
            "makes tax-exempt private pension significantly better rather than worse.",
            "",
            "### Battery movements",
            "",
            f"- Order produces {tagged(0, 'O')} entries and {tagged(0, 'O')} exits. It "
            "does not reproduce a bundle crossing, although CHAMPVA moves farther out of "
            "band as the clause table shows.",
            f"- Eligibility produces {tagged(6, 'E')} entries and {tagged(6, 'E')} exits. "
            f"It reproduces {tagged(10, 'R1/E')} of the bundle's "
            f"{tagged(35, 'R1')} crossings in the same categorical direction: "
            + ", ".join(code(key) for key in shared_e)
            + ". Casualty loss and farm income cross opposite sides of the band in `E` "
            "and `R1`, so magnitude and signed direction remain interaction-dependent. "
            "The eligibility-only crossings are "
            "`person/source_operator_retirement_distributions/"
            "taxable_403b_distributions[clone_0]/positive` entering (`E`) and "
            "`person/source_operator_retirement_distributions/"
            "tax_exempt_ira_distributions[clone_0]/positive` leaving (`E`); neither is "
            "a crossing in `R1`.",
            f"- Investment produces {tagged(0, 'I')} entries and {tagged(3, 'I')} exits: "
            + ", ".join(code(key) for key in sorted(transitions["I"]))
            + ". Only TANF also exits in the bundle; the isolated direction is consistent "
            "with investment contributing, but does not establish a unique driver. The "
            "separation and SPM-childcare exits do not occur in the bundle, consistent "
            "with masking or interaction.",
            f"- The remaining {tagged(24, 'R1/O/E/I')} of the bundle's "
            f"{tagged(35, 'R1')} crossings are not reproduced by an isolated arm. They "
            "cannot be assigned among order, minimal eligibility, or investment; the "
            "bundle-only broad replacement, late-PUF swap, and interactions remain "
            "jointly responsible candidates.",
            "",
            "CHAMPVA is one row in the full table and remains out of band throughout. "
            "Eligibility alone moves it toward the band but not far enough for the frozen "
            "clause; order and investment move it away. The larger bundle deterioration "
            "is non-additive and has no unique isolated driver in this design.",
            "",
            "### Money accuracy and landability",
            "",
            f"- Order has {tagged(74, 'O')} exactly zero money deltas, so it supplies no "
            "accuracy improvement even though no leg crosses out of band.",
            f"- Eligibility has {tagged(5, 'E')} significant improvements, "
            f"{tagged(5, 'E')} significant regressions, and {tagged(6, 'E')} exits. It is "
            "not landable.",
            f"- Investment has {tagged(3, 'I')} significant improvements, "
            f"{tagged(0, 'I')} significant regressions, but {tagged(3, 'I')} exits and an "
            "adverse CHAMPVA movement. It has one-sided money evidence but is not landable "
            "without isolating benefit from battery damage.",
            f"- The bundle has {tagged(12, 'R1')} significant improvements and "
            f"{tagged(21, 'R1')} significant regressions. {tagged(14, 'R1')} regressions "
            "are late-transfer rows, whose explicit PUF-detail predictor swap is absent "
            "from every isolated arm.",
            "",
        ]
    )


def add_handoff_and_next(lines: list[str]) -> None:
    lines.extend(
        [
            "## Bundle handoff",
            "",
            "**NONE — do not author an arm into the F1 bundle.** There is no landable "
            "predictor-set, chain-position, or availability-policy delta from this "
            "experiment.",
            "",
            "At `SCHEMA`, predictor columns would be expressed through "
            "`predictor_blocks.<id>.columns` and selected with "
            "`families[].predictors`; target positions are the order of "
            "`families[].targets` under root `chaining.order: declared`, with "
            "`families[].max_targets_per_fit` and optional root "
            "`chaining.split_after` / `chaining.keep_together`. Predictor-block "
            "`availability` is only `observed` or `always`. It cannot encode the "
            "investment arm's exact stage-specific donor-availability policy, and both "
            "block and family objects reject undeclared fields. A future successful "
            "investment treatment would need a typed schema/compiler extension rather "
            "than an approximate availability declaration.",
            "",
            "## Next experiment implied by the evidence",
            "",
            "- Run a frozen-gate factorial for the broad early PUF replacement: "
            "removal-only for `__acs_transfer_social_security_income` and "
            "`__acs_transfer_retirement_income`; broad-addition-only while retaining "
            "those baseline predictors; then the exact replacement. This separates the "
            "leading retirement mechanism from other additions and interactions.",
            "- Run a late-PUF-only arm using the bundle's explicit eight-column PUF-detail "
            "predictor set while preserving every early baseline family. This tests the "
            "unisolated treatment present in late-transfer regressions and many "
            "bundle-only PUF battery crossings.",
            "- Split investment by family scope. Significant gains are all in "
            "`person/model_required_numeric`, while isolated exits occur in "
            "`person/source_operator_relationship_inputs`, "
            "`spm_unit/model_required_boolean`, and "
            "`spm_unit/model_required_numeric`; test the narrow numeric opt-in before "
            "reconsidering a spec handoff.",
            "",
            "The owner adjudicates; this lane stops at synthesis.",
            "",
        ]
    )


def build_report(sources: OrderedDict[str, dict], data: dict) -> str:
    lines: list[str] = []
    add_decision_and_sources(lines, sources)
    add_money_table(lines, data)
    add_battery_table(lines, data)
    add_clause_table(lines, sources)
    add_attribution(lines, sources, data)
    add_handoff_and_next(lines)
    return "\n".join(lines)


def main() -> None:
    sources = load_sources()
    data = validate(sources)
    report = build_report(sources, data)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "bytes": OUTPUT.stat().st_size,
                "lines": report.count("\n"),
                "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
