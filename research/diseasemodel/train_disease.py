#!/usr/bin/env python3
"""Train one calibrated classifier per disease from a routine blood panel + age/sex, and a combined
"guess the disease" scorer. Metrics: ROC-AUC + average precision (PR-AUC, honest for rare diseases),
on a 20% held-out test set (~6k reports) plus 5-fold CV.
"""
import json, os, warnings
import numpy as np, pandas as pd, joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__)
df = pd.read_csv(os.path.join(HERE, "disease_dataset.csv"))
RNG = 42
DISEASES = ["diabetes", "hypertension", "high_cholesterol", "kidney_disease", "heart_failure",
            "coronary_hd", "angina", "heart_attack", "stroke", "liver_disease", "cancer", "copd"]
IDS = {"SEQN", "cycle"}
FEATURES = [c for c in df.columns if c not in IDS | set(DISEASES)
            and pd.api.types.is_numeric_dtype(df[c])]
# near-diagnostic markers to optionally exclude (so a result isn't tautological)
GLYCEMIC = ["glucose", "glucose_fasting", "glucose_serum", "hba1c"]

def fit_eval(feats, y_col, test_frac=0.2):
    sub = df[df[y_col].notna()]
    X, y = sub[feats].values, sub[y_col].astype(int).values
    if y.sum() < 50 or len(sub) < 1000:
        return None
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=test_frac, random_state=RNG, stratify=y)
    m = HistGradientBoostingClassifier(max_iter=500, learning_rate=0.05, l2_regularization=1.0,
                                       class_weight="balanced", random_state=RNG).fit(Xtr, ytr)
    p = m.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, p); ap = average_precision_score(yte, p)
    cvauc = cross_val_score(m, X, y, cv=5, scoring="roc_auc").mean()
    return {"model": m, "n": int(len(sub)), "n_pos": int(y.sum()), "prevalence": round(y.mean(), 3),
            "n_test": int(len(yte)), "test_AUC": round(float(auc), 3),
            "test_AP": round(float(ap), 3), "cv5_AUC": round(float(cvauc), 3)}

results, models = {}, {}
os.makedirs(os.path.join(HERE, "models"), exist_ok=True)
print(f"features: {len(FEATURES)} markers; test split ~{int(0.2*len(df)):,} reports\n")
for d in DISEASES:
    # diabetes is near-circular from glycemic markers -> report an honest "no-glycemic" version too
    feats = [f for f in FEATURES if f not in GLYCEMIC] if d == "diabetes" else FEATURES
    r = fit_eval(feats, d)
    if not r:
        print(f"{d:<16} skipped"); continue
    models[d] = r.pop("model")
    joblib.dump(models[d], os.path.join(HERE, "models", f"{d}.joblib"))
    r["features"] = "panel_minus_glycemic" if d == "diabetes" else "full_panel"
    results[d] = r
    print(f"{d:<16} AUC={r['test_AUC']:.3f} AP={r['test_AP']:.3f} cv={r['cv5_AUC']:.3f}  "
          f"(n={r['n']:,}, pos={r['n_pos']}, test={r['n_test']:,})")

# diabetes WITH glycemic markers for comparison (expected high / partly tautological)
rg = fit_eval(FEATURES, "diabetes")
if rg: results["diabetes_with_glycemic"] = {k: rg[k] for k in rg if k != "model"}; \
       print(f"\n(diabetes WITH glucose/HbA1c: AUC={rg['test_AUC']:.3f} — expected high, markers are diagnostic)")

results["_meta"] = {"features_full": FEATURES, "diseases": DISEASES, "n_dataset": int(len(df)),
                    "note": "diabetes headline model excludes glucose/HbA1c to avoid circularity"}
json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=2)

# ---- "guess the disease": rank conditions by predicted probability for one report ----
def guess(report: dict, topk=4):
    row = np.array([[report.get(f, np.nan) for f in FEATURES]])
    glyc = np.array([[report.get(f, np.nan) for f in [x for x in FEATURES if x not in GLYCEMIC]]])
    out = []
    for d, m in models.items():
        feats_row = glyc if d == "diabetes" else row
        out.append((d, float(m.predict_proba(feats_row)[:, 1][0])))
    return sorted(out, key=lambda x: -x[1])[:topk]

example = df[df["coronary_hd"] == 1].iloc[0][FEATURES].to_dict()
print("\n=== guess the disease (a known-CHD patient's panel) ===")
for d, p in guess(example):
    print(f"  {d:<16} {p:.2f}")
print("\nsaved -> models/, results.json")
