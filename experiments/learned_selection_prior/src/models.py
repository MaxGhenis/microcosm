"""populace#346 — STEP 03: models + three-way prior ablation.

Trains logistic + histogram gradient-boosted trees to predict frozen-selection
membership, with stratified 5-fold OOF CV. Reports ROC-AUC / PR-AUC and
precision@57240 (== recall, since #positives==57240). The key ablation:

    (1) trained MODEL   vs
    (2) plain max-contribution-share formula  maxₜ wᵢ|vᵢₜ|/|targetₜ|  vs
    (3) dense-weight-proportional              wᵢ

Saves OOF model probabilities (the learned prior score) for the harness stage.

Usage: models.py --tag {base|dense}
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.inspection import permutation_importance

CORE = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/core")
FEAT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/features")
OUT = Path("/Users/maxghenis/PolicyEngine/_buildg-runtime/out/learned-prior/models")
OUT.mkdir(parents=True, exist_ok=True)
K = 57240
SEED = 0


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def precision_at_k(score, y, k=K):
    idx = np.argpartition(-score, k)[:k]
    return float(y[idx].sum() / k)


def load_frame(tag):
    f = np.load(FEAT / f"features_{tag}.npz", allow_pickle=True)
    names = [str(n) for n in f["feature_names"] if str(n) != "label"]
    df = pd.DataFrame({str(n): f[str(n)] for n in names})
    y = f["label"].astype(int)
    meta = np.load(CORE / "core_meta.npz", allow_pickle=True)
    # demographics (label-independent inputs)
    df["hh_size"] = meta["hh_size"]
    df["n_child"] = meta["n_child"]
    df["n_young_adult"] = meta["n_young_adult"]
    df["n_mid"] = meta["n_mid"]
    df["n_elderly"] = meta["n_elderly"]
    agi = meta["agi"].astype(float)
    df["signed_log_agi"] = np.sign(agi) * np.log1p(np.abs(agi))
    df["source_year"] = meta["source_year"].astype(int)
    df["state_fips"] = meta["state_fips"].astype(int)
    df["channel_puf"] = (meta["channel"].astype(str) == "puf_tax_detail").astype(int)
    df.columns = df.columns.astype(str)
    return df, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    t0 = time.time()
    df, y = load_frame(args.tag)
    n = len(df)
    log(f"tag={args.tag} rows={n} features={df.shape[1]} positives={int(y.sum())} "
        f"rate={y.mean():.4f}")

    # baseline scores for the ablation
    base_formula = df["max_share_tgt"].to_numpy()      # (2) Max's formula
    base_weight = df["weight_used"].to_numpy()          # (3) weight-proportional

    cat_cols = ["source_year", "state_fips"]
    num_cols = [c for c in df.columns if c not in cat_cols]

    # HGB frame: integer-coded categoricals
    Xhgb = df.copy()
    for c in cat_cols:
        Xhgb[c] = Xhgb[c].astype("category")
    # logistic frame: one-hot cats + standardized numerics
    Xoh = pd.get_dummies(df, columns=cat_cols, drop_first=True)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    oof_hgb = np.zeros(n); oof_logit = np.zeros(n)
    aucs = {"hgb": [], "logit": []}
    for i, (tr, te) in enumerate(skf.split(df, y)):
        hgb = HistGradientBoostingClassifier(
            max_iter=400, learning_rate=0.06, max_leaf_nodes=63,
            l2_regularization=1.0, categorical_features=cat_cols,
            random_state=SEED, early_stopping=True, validation_fraction=0.1)
        hgb.fit(Xhgb.iloc[tr], y[tr])
        oof_hgb[te] = hgb.predict_proba(Xhgb.iloc[te])[:, 1]

        sc = StandardScaler()
        Xtr = sc.fit_transform(Xoh.iloc[tr]); Xte = sc.transform(Xoh.iloc[te])
        lr = LogisticRegression(max_iter=2000, C=1.0, class_weight=None)
        lr.fit(Xtr, y[tr])
        oof_logit[te] = lr.predict_proba(Xte)[:, 1]
        aucs["hgb"].append(roc_auc_score(y[te], oof_hgb[te]))
        aucs["logit"].append(roc_auc_score(y[te], oof_logit[te]))
        log(f"  fold {i}: HGB AUC={aucs['hgb'][-1]:.4f}  LOGIT AUC={aucs['logit'][-1]:.4f}")

    # ablation table
    rows = []
    for name, score in [("HGB model (OOF)", oof_hgb),
                        ("Logistic (OOF)", oof_logit),
                        ("Formula: max contribution share", base_formula),
                        ("Prior: dense weight", base_weight)]:
        rows.append({
            "prior": name,
            "roc_auc": roc_auc_score(y, score),
            "pr_auc": average_precision_score(y, score),
            "precision_at_57240": precision_at_k(score, y),
        })
    abl = pd.DataFrame(rows)
    log("\n=== THREE-WAY ABLATION (+ models) ===\n" + abl.to_string(index=False))

    # SAVE scores + ablation FIRST (never lose them to a later failure)
    np.savez(OUT / f"model_scores_{args.tag}.npz",
             oof_hgb=oof_hgb, oof_logit=oof_logit,
             formula_max_share=base_formula, dense_weight=base_weight, label=y)
    abl.to_csv(OUT / f"ablation_{args.tag}.csv", index=False)
    json.dump({"auc_hgb_folds": aucs["hgb"], "auc_logit_folds": aucs["logit"]},
              open(OUT / f"cv_{args.tag}.json", "w"), indent=2)
    log(f"saved scores/ablation to {OUT}")

    # feature importance (lighter: 40k train / 40k eval; robust to OOM) + logistic coefs
    try:
        rng = np.random.default_rng(SEED)
        perm = rng.permutation(n)
        tr_i, ev_i = perm[:40000], perm[40000:80000]
        hgb_imp = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.06, max_leaf_nodes=63, l2_regularization=1.0,
            categorical_features=cat_cols, random_state=SEED, early_stopping=True)
        hgb_imp.fit(Xhgb.iloc[tr_i], y[tr_i])
        pi = permutation_importance(hgb_imp, Xhgb.iloc[ev_i], y[ev_i],
                                    scoring="roc_auc", n_repeats=3, random_state=SEED)
        imp = (pd.DataFrame({"feature": Xhgb.columns, "importance": pi.importances_mean})
               .sort_values("importance", ascending=False))
        imp.to_csv(OUT / f"importance_{args.tag}.csv", index=False)
        log("\n=== HGB permutation importance (top 20, drop in ROC-AUC) ===\n"
            + imp.head(20).to_string(index=False))
    except Exception as e:  # pragma: no cover
        log(f"permutation importance skipped: {e!r}")
    log(f"\nsaved model artifacts to {OUT}  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
