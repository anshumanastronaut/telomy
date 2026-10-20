#!/usr/bin/env python3
"""Calibrate the disease classifiers so they output honest probabilities, not just rankings.

The rigor pass showed strong ranking but miscalibrated probabilities for rare conditions (balanced
class weights trade calibration for ranking). We wrap each model in CalibratedClassifierCV (isotonic,
5-fold) and report Brier + calibration error before vs after. Calibrated models -> models/calibrated/.
"""
import json, os, warnings
import numpy as np, pandas as pd, joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import brier_score_loss, roc_auc_score
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__); RNG = 42
df = pd.read_csv(os.path.join(HERE, "disease_dataset.csv"))
meta = json.load(open(os.path.join(HERE, "results.json")))["_meta"]
FEATURES, DISEASES = meta["features_full"], meta["diseases"]
GLY = ["glucose", "glucose_fasting", "glucose_serum", "hba1c"]
os.makedirs(os.path.join(HERE, "models", "calibrated"), exist_ok=True)

def cal_err(y, p):
    f, m = calibration_curve(y, p, n_bins=10, strategy="quantile")
    return float(np.mean(np.abs(f - m)))

out = {}
for d in DISEASES:
    feats = [f for f in FEATURES if f not in GLY] if d == "diabetes" else FEATURES
    sub = df[df[d].notna()]
    X, y = sub[feats].values, sub[d].astype(int).values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG, stratify=y)
    base = HistGradientBoostingClassifier(max_iter=500, learning_rate=0.05, l2_regularization=1.0,
                                          class_weight="balanced", random_state=RNG).fit(Xtr, ytr)
    p0 = base.predict_proba(Xte)[:, 1]
    cal = CalibratedClassifierCV(HistGradientBoostingClassifier(max_iter=500, learning_rate=0.05,
            l2_regularization=1.0, class_weight="balanced", random_state=RNG),
            method="isotonic", cv=5).fit(Xtr, ytr)
    p1 = cal.predict_proba(Xte)[:, 1]
    joblib.dump(cal, os.path.join(HERE, "models", "calibrated", f"{d}.joblib"))
    out[d] = {"brier_before": round(brier_score_loss(yte, p0), 4), "brier_after": round(brier_score_loss(yte, p1), 4),
              "calib_err_before": round(cal_err(yte, p0), 3), "calib_err_after": round(cal_err(yte, p1), 3),
              "auc_before": round(roc_auc_score(yte, p0), 3), "auc_after": round(roc_auc_score(yte, p1), 3)}
    print(f"{d:<16} Brier {out[d]['brier_before']:.4f}->{out[d]['brier_after']:.4f}  "
          f"calib {out[d]['calib_err_before']:.3f}->{out[d]['calib_err_after']:.3f}  "
          f"AUC {out[d]['auc_before']:.3f}->{out[d]['auc_after']:.3f}")

json.dump(out, open(os.path.join(HERE, "results_calibration.json"), "w"), indent=2)
imp = np.mean([out[d]["calib_err_before"] - out[d]["calib_err_after"] for d in out])
print(f"\nmean calibration-error improvement: {imp:+.3f}  (positive = better)")
print("saved -> models/calibrated/, results_calibration.json")
