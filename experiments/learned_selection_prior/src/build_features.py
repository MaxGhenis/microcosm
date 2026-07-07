"""populace#346 — STEP 02b: contribution-share + leverage features.

Given the core (A, b, base_weight, demographics, label) and a weight vector w,
compute the hypothesis features (Max's #346 correction):

  contribution_it = w_i * v_it   (v_it = A[t,i])
  share_it (vs target)   = |contribution_it| / |b_t|
  share_it (vs estimate) = |contribution_it| / sum_j|w_j v_jt|

Per-record aggregations: max / sum / top-k / per-family (income tax, SS, SNAP,
state cells, population, tax-expenditure). Plus leverage/substitutability:
  carrier_it = |v_it| / sum_j|v_jt|   (unweighted "dominant carrier" signal —
  the record-level analogue of the protect-list Max describes).

Usage:  build_features.py --weight {base|dense} [--wpath W.npy] --tag TAG
Saves a parquet feature table to OUT/features_{TAG}.parquet.
"""
from __future__ import annotations
import argparse, json, re, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse

CORE = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/core")
OUT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/features")
OUT.mkdir(parents=True, exist_ok=True)


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def family_ids(names):
    """Non-exclusive family membership masks (a target can be in several)."""
    fam = {k: np.zeros(len(names), bool) for k in
           ["income_tax", "social_security", "snap", "state_cell",
            "population", "tax_expenditure", "health", "agi_income"]}
    state_re = re.compile(r"\.[a-z]{2}\.")
    for i, n in enumerate(names):
        s = n.lower()
        if "income_tax" in s: fam["income_tax"][i] = True
        if "social_security" in s or s.startswith("ssa"): fam["social_security"][i] = True
        if "snap" in s or "supplemental_nutrition" in s: fam["snap"][i] = True
        if ("state_broad" in s or "state_agi" in s or "state_resident" in s
                or state_re.search(s)): fam["state_cell"][i] = True
        if "resident_population" in s: fam["population"][i] = True
        if s.startswith("jct") or "tax_expenditure" in s: fam["tax_expenditure"][i] = True
        if s.startswith("cms_"): fam["health"][i] = True
        if "adjusted_gross_income" in s or "income_by_source" in s: fam["agi_income"][i] = True
    return fam


def per_record_max_sum_count(row, col, val, n):
    mx = np.zeros(n); np.maximum.at(mx, col, val)
    sm = np.zeros(n); np.add.at(sm, col, val)
    cnt = np.zeros(n); np.add.at(cnt, col, 1.0)
    return mx, sm, cnt


def topk_sum(col, val, n, k):
    """Per-record sum of the k largest `val` among its nnz. One groupby."""
    df = pd.DataFrame({"c": col, "v": val})
    df = df.sort_values(["c", "v"], ascending=[True, False])
    df["rank"] = df.groupby("c").cumcount()
    top = df[df["rank"] < k].groupby("c")["v"].sum()
    out = np.zeros(n); out[top.index.to_numpy()] = top.to_numpy()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weight", choices=["base", "dense"], required=True)
    ap.add_argument("--wpath", default=None, help="npy weight vector when --weight dense")
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    t0 = time.time()
    A = sparse.load_npz(CORE / "A_value_matrix.npz").tocsr()
    b = np.load(CORE / "b_target_vector.npy")
    names = json.load(open(CORE / "target_names.json"))
    meta = np.load(CORE / "core_meta.npz", allow_pickle=True)
    base_weight = meta["base_weight"]; y = meta["label"]
    n_targets, n = A.shape
    log(f"A {A.shape} nnz={A.nnz}  positives={int(y.sum())}")

    if args.weight == "base":
        w = base_weight
    else:
        w = np.load(args.wpath).astype(np.float64)
        assert w.size == n, (w.size, n)
    log(f"weight={args.weight} sum={w.sum():.6g} min={w.min():.4g} max={w.max():.4g}")

    # COO view (row=target, col=record). CSR: indices are column (record) ids.
    A_coo = A.tocoo()
    row, col, v = A_coo.row, A_coo.col, A_coo.data.astype(np.float64)
    absv = np.abs(v)
    contrib = w[col] * v
    abscontrib = np.abs(contrib)

    # denominators
    absb = np.abs(b)
    est = np.zeros(n_targets); np.add.at(est, row, contrib)         # signed estimate
    abs_est = np.zeros(n_targets); np.add.at(abs_est, row, abscontrib)   # weighted L1 row total
    abs_unw = np.zeros(n_targets); np.add.at(abs_unw, row, absv)         # unweighted L1 row total

    # share vs target |b| (skip b==0); share vs weighted-estimate; carrier (unweighted)
    denom_b = np.where(absb > 0, absb, np.inf)
    share_tgt = abscontrib / denom_b[row]
    denom_est = np.where(abs_est > 0, abs_est, np.inf)
    share_est = abscontrib / denom_est[row]
    denom_unw = np.where(abs_unw > 0, abs_unw, np.inf)
    carrier = absv / denom_unw[row]           # fraction of target's TOTAL |value| carried by i

    log("aggregating per-record ...")
    feats = {}
    # headline: Max's max-contribution-share (vs target)
    mx, sm, cnt = per_record_max_sum_count(row, col, share_tgt, n)
    feats["max_share_tgt"] = mx; feats["sum_share_tgt"] = sm; feats["n_targets_touched"] = cnt
    feats["top5_share_tgt"] = topk_sum(col, share_tgt, n, 5)
    feats["top20_share_tgt"] = topk_sum(col, share_tgt, n, 20)
    # vs estimate
    mxe, sme, _ = per_record_max_sum_count(row, col, share_est, n)
    feats["max_share_est"] = mxe; feats["sum_share_est"] = sme
    # carrier / leverage proxy (unweighted dominant-carrier signal)
    mxc, smc, _ = per_record_max_sum_count(row, col, carrier, n)
    feats["max_carrier"] = mxc; feats["sum_carrier"] = smc
    feats["top5_carrier"] = topk_sum(col, carrier, n, 5)
    for thr in (0.01, 0.05, 0.25):
        c = np.zeros(n); np.add.at(c, col, (carrier > thr).astype(float))
        feats[f"n_carrier_gt_{thr}"] = c
    # per-family share sums (vs target)
    fam = family_ids(names)
    for fname, fmask in fam.items():
        keep = fmask[row]
        fc = np.zeros(n)
        np.add.at(fc, col[keep], share_tgt[keep])
        feats[f"famshare_{fname}"] = fc
        fm = np.zeros(n)
        np.maximum.at(fm, col[keep], share_tgt[keep])
        feats[f"fammax_{fname}"] = fm

    feats["weight_used"] = w
    feats["log_weight_used"] = np.log1p(w)
    feats["label"] = y.astype(np.float64)
    # headline EDA (before save): is each feature higher among selected?
    log("EDA (selected vs unselected medians):")
    for c in ["max_share_tgt", "max_carrier", "weight_used", "log_weight_used",
              "famshare_income_tax", "fammax_income_tax", "famshare_social_security",
              "n_targets_touched", "sum_share_tgt"]:
        v = feats[c]; s1 = np.median(v[y == 1]); s0 = np.median(v[y == 0])
        log(f"  {c:24s} sel median={s1:.4g}  unsel median={s0:.4g}  "
            f"ratio={(s1/s0) if s0 else float('nan'):.2f}")
    out = OUT / f"features_{args.tag}.npz"
    np.savez(out, **feats, feature_names=np.array(list(feats.keys())))
    log(f"saved {out}  (n_features={len(feats)-1})  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
