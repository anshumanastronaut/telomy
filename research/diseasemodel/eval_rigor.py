#!/usr/bin/env python3
"""Rigor pass on the disease models: calibration (Brier + reliability), PR-AUC, and a multi-label
"guess the disease" top-3 recall. Turns the headline AUCs into defensible evidence.
"""
import json, os, warnings
import numpy as np, pandas as pd, joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.calibration import calibration_curve
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__); RNG = 42
df = pd.read_csv(os.path.join(HERE, "disease_dataset.csv"))
meta = json.load(open(os.path.join(HERE, "results.json")))["_meta"]
FEATURES, DISEASES = meta["features_full"], meta["diseases"]
GLY = ["glucose", "glucose_fasting", "glucose_serum", "hba1c"]
NOGLY = [f for f in FEATURES if f not in GLY]

def model_feats(d):
    return NOGLY if d == "diabetes" else FEATURES

out = {"per_disease": {}}
# cache each model's test-set probabilities (reproducing train_disease's split) for calibration/PR
test_prob = {}
for d in DISEASES:
    m = joblib.load(os.path.join(HERE, "models", f"{d}.joblib"))
    feats = model_feats(d)
    sub = df[df[d].notna()]
    X, y = sub[feats].values, sub[d].astype(int).values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG, stratify=y)
    p = m.predict_proba(Xte)[:, 1]
    frac_pos, mean_pred = calibration_curve(yte, p, n_bins=10, strategy="quantile")
    cal_err = float(np.mean(np.abs(frac_pos - mean_pred)))     # mean |observed - predicted| across bins
    out["per_disease"][d] = {"PR_AUC": round(float(average_precision_score(yte, p)), 3),
                             "brier": round(float(brier_score_loss(yte, p)), 4),
                             "calibration_err": round(cal_err, 3),
                             "prevalence": round(float(yte.mean()), 3), "n_test": int(len(yte))}

# ---- multi-label "guess the disease": for patients with >=1 diagnosed condition, is a true one in top-k? ----
common = df.dropna(subset=DISEASES)           # patients with all labels known
if len(common) > 500:
    probs = {}
    for d in DISEASES:
        m = joblib.load(os.path.join(HERE, "models", f"{d}.joblib"))
        probs[d] = m.predict_proba(common[model_feats(d)].values)[:, 1]
    P = pd.DataFrame(probs, index=common.index)
    hits1 = hits3 = total = 0
    for idx, row in common.iterrows():
        true = [d for d in DISEASES if row[d] == 1]
        if not true:
            continue
        total += 1
        ranked = P.loc[idx].sort_values(ascending=False).index.tolist()
        if ranked[0] in true: hits1 += 1
        if set(ranked[:3]) & set(true): hits3 += 1
    out["guess_the_disease"] = {"n_patients_with_a_condition": total,
                                "top1_recall": round(hits1 / total, 3),
                                "top3_recall": round(hits3 / total, 3),
                                "note": "of patients with >=1 diagnosed condition, how often a true one is the top (or top-3) ranked"}

json.dump(out, open(os.path.join(HERE, "results_rigor.json"), "w"), indent=2)
print("=== calibration + PR-AUC (held-out) ===")
for d, r in out["per_disease"].items():
    print(f"  {d:<16} PR-AUC={r['PR_AUC']:.3f}  Brier={r['brier']:.4f}  calib_err={r['calibration_err']:.3f}  prev={r['prevalence']:.2f}")
if "guess_the_disease" in out:
    g = out["guess_the_disease"]
    print(f"\nguess-the-disease: top-1 recall {g['top1_recall']:.1%}, top-3 recall {g['top3_recall']:.1%} "
          f"(n={g['n_patients_with_a_condition']:,})")
print("saved -> results_rigor.json")
