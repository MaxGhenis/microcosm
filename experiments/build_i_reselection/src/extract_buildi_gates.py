#!/usr/bin/env python3
"""populace#359 Build I gate-table extractor.

Reads a release dir's calibration_diagnostics.json + input_mass_parity.json +
us_source_coverage.json and prints the full per-artifact gate table vs the
Build H frozen-57k certification bar (the candidate Build I sparse must MEET/BEAT
final_loss 0.03091516 / within-10% 0.8901 / income tax +0.45% AND pass export-mass).
Usage: extract_buildi_gates.py <release_dir> [sparse]
"""
import json
import sys
from pathlib import Path

# Certification bar = Build H frozen-57k actuals (#299 comment 4914302628).
BANDS = {
    "sparse": {"final_loss": 0.03091516, "within_10pct": 0.8901, "label": "Build H frozen-57k"},
}
SPARSE_PRIOR = {
    "final_loss": 0.03091516, "within_10pct": 0.8901, "ess": 13184.1,
    "income_tax_relerr": 0.0045, "ss_relerr": -0.0018, "mortgage_taxexp_relerr": 0.3548,
    "net_capital_gain_relerr": -0.2665,
}


def load(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


def zero_support(diag):
    zs = []
    for t in diag.get("targets") or []:
        tgt = float(t.get("target", 0) or 0)
        ie = abs(float(t.get("initial_estimate", 0) or 0))
        fe = abs(float(t.get("final_estimate", 0) or 0))
        if tgt > 0 and ie <= 1e-9 and fe <= 1e-9:
            zs.append(t.get("name", ""))
    return zs


def critical_fit(diag):
    out = {}
    for t in diag.get("targets") or []:
        name = (t.get("name") or "").lower()
        tgt = float(t.get("target", 0) or 0)
        est = float(t.get("final_estimate", 0) or 0)
        if not tgt:
            continue
        relerr = (est - tgt) / abs(tgt)
        if name == "irs_soi.ty2022.historic_table_2.us.all.income_tax_liability_amount@2024":
            out["fed_income_tax_liability (SOI)"] = (tgt, est, relerr)
        if "SS_benefits" not in out and (
            ("social_security" in name or "oasdi" in name)
            and ("benefit" in name or "ssa" in name)
        ):
            out["SS_benefits"] = (tgt, est, relerr)
        if "deductible_mortgage_interest" in name and "revenue_loss" in name:
            out["mortgage_tax_exp (JCT, BINDING)"] = (tgt, est, relerr)
        if "qualified_business_income" in name and "revenue_loss" in name:
            out["QBI_tax_exp (JCT)"] = (tgt, est, relerr)
        if "salt_deduction" in name and "revenue_loss" in name:
            out["SALT_tax_exp (JCT)"] = (tgt, est, relerr)
        if name == "cbo.revenue_projection.ty2024.income_by_source.net_capital_gain.projected_amount@2024":
            out["net_capital_gain (CBO agg)"] = (tgt, est, relerr)
        if name == "irs_soi.ty2023.table_1_4.all.other_income_net_income_amount@2024":
            out["other_income_net_income (misc pos leg)"] = (tgt, est, relerr)
        if name == "irs_soi.ty2023.table_1_4.all.other_income_net_loss_amount@2024":
            out["other_income_net_loss (misc neg leg)"] = (tgt, est, relerr)
    return out


def main():
    rel = Path(sys.argv[1])
    kind = "sparse"
    diag = load(rel / "calibration_diagnostics.json")
    imp = load(rel / "input_mass_parity.json")
    cov = load(rel / "us_source_coverage.json")
    if diag is None:
        print(f"NO calibration_diagnostics.json in {rel}")
        return

    band = BANDS[kind]
    b = diag.get("build", {})
    rg = b.get("release_gates", {})
    opt = diag.get("options", {})
    zs = zero_support(diag)

    print(f"================ BUILD I {kind.upper()} — {rel.name} ================\n")
    print("--- HEADLINE CALIBRATION vs Build H frozen-57k bar ---")
    fl = diag.get("final_loss")
    w10 = diag.get("fraction_within_10pct")
    print(f"  final_loss:        {fl:.6f}   (bar {band['label']}: {band['final_loss']})"
          f"  {'BEATS' if fl is not None and fl <= band['final_loss'] else 'ABOVE'}")
    print(f"  within-10%:        {w10:.4f}   (bar: {band['within_10pct']})"
          f"  {'>=bar' if w10 is not None and w10 >= band['within_10pct'] else 'below bar'}")
    print(f"  initial_loss:      {diag.get('initial_loss'):.6f}")
    print(f"  n_records:         {diag.get('n_records')}")
    print(f"  n_nonzero:         {diag.get('n_nonzero')}")
    print(f"  ESS:               {diag.get('effective_sample_size'):.1f}  (bar {SPARSE_PRIOR['ess']})")
    print(f"  realized_max_ratio:{diag.get('realized_max_weight_ratio')}")
    print(f"  top_1pct_wt_share: {diag.get('top_1pct_weight_share')}")
    print(f"  l0_lambda:         {diag.get('l0_lambda')}")
    print(f"  method/epochs:     {opt.get('method')}/{opt.get('epochs')}  l2_lambda={opt.get('l2_lambda')} max_wt_ratio={opt.get('max_weight_ratio')}")

    print("\n--- STRUCTURAL GATES ---")
    def g(name, key):
        v = b.get(key)
        if v is None:
            print(f"  {name:36s} n/a")
            return
        passed = v.get("passed") if isinstance(v, dict) else v
        fails = v.get("failures", []) if isinstance(v, dict) else []
        print(f"  {name:36s} {'PASS' if passed else 'FAIL'}"
              + (f"  ({len(fails)} failures)" if fails else ""))
        for f in fails[:6]:
            print(f"       - {str(f)[:150]}")
    g("target_profile_coverage", "target_profile_coverage")
    g("health_input_signal", "health_input_signal")
    g("degenerate_input_signal (#286)", "degenerate_input_signal")
    g("base_population_scale (334.2M)", "base_population_scale")
    g("immigration_composition (#266)", "immigration_composition")
    g("input_mass_reference (base vs 57k)", "input_mass_reference")
    g("ecps_parity (ratchet #316)", "ecps_parity")
    g("validation_input_coverage (#278/9)", "validation_input_coverage")

    print("\n--- RELEASE GATES (aggregate) ---")
    print(f"  release_gates.passed: {rg.get('passed')}")
    for f in rg.get("failures", []):
        print(f"    FAIL: {str(f)[:180]}")

    print("\n--- KEY TARGET FITS (Build H frozen-57k in brackets) ---")
    prior = {"fed_income_tax_liability (SOI)": SPARSE_PRIOR["income_tax_relerr"],
             "SS_benefits": SPARSE_PRIOR["ss_relerr"],
             "mortgage_tax_exp (JCT, BINDING)": SPARSE_PRIOR["mortgage_taxexp_relerr"],
             "net_capital_gain (CBO agg)": SPARSE_PRIOR["net_capital_gain_relerr"]}
    for k, (tgt, est, rel) in critical_fit(diag).items():
        pj = f"  [BH frozen {prior[k]:+.2%}]" if k in prior else ""
        print(f"  {k:44s} tgt={tgt:.4e} est={est:.4e} relerr={rel:+.2%}{pj}")

    print(f"\n--- ZERO-SUPPORT TARGETS (post-exclusion): {len(zs)} ---")
    for n in zs[:25]:
        print(f"    {n}")

    print("\n--- EXPORT INPUT-MASS PARITY (ref c2065b64, +/-50%, $1B floor) ---")
    if imp:
        ev = imp.get("export_vs_base_frame", {})
        det = ev.get("details", {})
        print(f"  passed: {ev.get('passed')}   reference_name: {det.get('reference_name')}")
        print(f"  columns_checked: {det.get('columns_checked')}  tol: {det.get('relative_tolerance')}  floor: {det.get('minimum_reference_total')}")
        print(f"  reviewed_exclusions: {list((det.get('reviewed_exclusions') or {}).keys())}")
        print(f"  n failures: {len(ev.get('failures', []))}")
        for f in ev.get("failures", [])[:20]:
            print(f"    FAIL: {str(f)[:200]}")

    print("\n--- CACHE-KEY COMPONENTS ---")
    print(f"  base_dataset_sha256: {b.get('base_dataset_sha256')}")
    tc = b.get("target_compilation", {})
    print(f"  target_registry (declared/compiled): {tc.get('declared_targets')}/{tc.get('compiled_candidate_targets')}")
    print(f"  seed: {opt.get('seed')}   target_period: 2024")
    ss = b.get("selection_source")
    if ss:
        print("\n--- SELECTION SOURCE PROVENANCE ---")
        print(f"  {json.dumps(ss, indent=2)[:800]}")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
