#!/usr/bin/env python3
"""Organ-specific aging clocks (NHANES 2009-2018, 49.7k adults).

One age-regressor per organ system, trained only on that system's biomarkers. The predicted value is the
"organ age"; the residual (predicted − chronological) is the **age acceleration** — the actual signal (is this
person's liver/kidney/metabolism/immune system older or younger than their birthday). Mirrors the 2026 Cell
"Digital Aging Twin" approach (organs age unevenly), grounded in routine blood chemistry we already parse.
"""
import os, json, warnings
import numpy as np, pandas as pd, joblib
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import pearsonr
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__); RNG = 42
MODELS = os.path.join(HERE, "models"); os.makedirs(MODELS, exist_ok=True)
df = pd.read_csv(os.path.join(HERE, "nhanes_bloodpanel.csv"))
df = df[(df.age >= 18) & (df.age <= 80)].copy()

ORGANS = {
    "metabolic": ["glucose_fasting", "hba1c", "insulin", "trig", "trig_serum", "hdl", "total_chol", "ldl", "uric_acid", "glucose_serum"],
    "hepatic":   ["albumin", "alt", "ast", "alp", "ggt", "bilirubin", "total_protein", "globulin"],
    "renal":     ["creatinine", "bun", "uric_acid", "phosphorus", "potassium", "sodium", "chloride", "bicarb", "calcium"],
    "immune":    ["wbc", "lymph_pct", "neut_pct", "mono_pct", "eos_pct", "baso_pct", "rdw", "platelets", "crp_mgL"],
    "cardiometabolic": ["total_chol", "hdl", "ldl", "trig", "glucose", "hba1c", "uric_acid"],
}


def model():
    return HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05, l2_regularization=1.0,
                                         max_leaf_nodes=31, random_state=RNG)


results = {"_meta": {"source": "NHANES 2009-2018 (49.7k adults); organ-specific age clocks from routine chemistry",
                     "method": "predict chronological age per organ panel; residual = age acceleration",
                     "reference": "mirrors Cell 2026 Digital Aging Twin (organ-specific clocks)"}}
print(f"{'organ':<16} {'n':>6} {'feats':>5}  {'MAE':>6}  {'R2':>6}  {'r':>6}  accel σ")
for organ, markers in ORGANS.items():
    feats = ["sex"] + [m for m in markers if m in df.columns]
    need = max(3, (len(feats) - 1) // 2)
    sub = df[df[feats].notna().sum(axis=1) >= need].dropna(subset=["age"])
    if len(sub) < 2000:
        print(f"{organ:<16} skip (n={len(sub)})"); continue
    X, y = sub[feats], sub["age"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG)
    m = model(); m.fit(Xtr, ytr)
    pred = m.predict(Xte)
    mae, r2 = mean_absolute_error(yte, pred), r2_score(yte, pred)
    r = pearsonr(yte, pred)[0]
    cv = -cross_val_score(model(), X, y, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1)
    accel = pred - yte                      # organ age acceleration on held-out
    joblib.dump(m, os.path.join(MODELS, f"organ_{organ}.joblib"))
    results[f"organ_{organ}"] = {"n": int(len(sub)), "n_features": len(feats), "markers": feats,
                                 "test_MAE_years": round(float(mae), 2), "test_R2": round(float(r2), 3),
                                 "test_pearson_r": round(float(r), 3), "cv5_MAE_mean": round(float(cv.mean()), 2),
                                 "accel_std_years": round(float(accel.std()), 2)}
    print(f"{organ:<16} {len(sub):>6} {len(feats):>5}  {mae:5.2f}y  {r2:.3f}  {r:.3f}  ±{accel.std():.1f}y")

json.dump(results, open(os.path.join(HERE, "organ_results.json"), "w"), indent=2)
print(f"\nSaved {len([k for k in results if k != '_meta'])} organ clocks -> organ_results.json")
