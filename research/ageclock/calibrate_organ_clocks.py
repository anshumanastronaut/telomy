#!/usr/bin/env python
"""Compute per-organ age-bias correction for the organ clocks.

The clocks (gradient boosting predicting chronological age) regress toward the population mean (~50): they
over-age the young and under-age the old, so `age_acceleration = pred - chrono` is systematically biased by
age. Standard fix (Horvath/Cole calibration): fit the residual r = pred - chrono on chrono (r = a + b*chrono)
over the training population, then correct  pred* = pred - (a + b*chrono).  After this, mean residual ≈ 0 at
every age, and within-age relative differences (the disease signal) are preserved.

Writes backend/app/assets/organ_calibration.json : {organ: {a, b, before_mae_bias, after_mae_bias}}.
Run: backend/.venv/bin/python research/ageclock/calibrate_organ_clocks.py
"""
import os, sys, json
import numpy as np, pandas as pd, joblib

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "..", "backend", "app", "assets")
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
from app.llx import organ_tools as O  # feature lists  # noqa: E402

df = pd.read_csv(os.path.join(HERE, "nhanes_bloodpanel.csv"))
out = {}
for organ, feats_all in O.ORGANS.items():
    model = joblib.load(os.path.join(ASSETS, f"organ_{organ}.joblib"))
    feats = list(getattr(model, "feature_names_in_", ["sex"] + [m for m in feats_all if m in df.columns]))
    sub = df.dropna(subset=["age"]).copy()
    # need enough of this organ's markers (same rule as inference)
    present = [f for f in feats if f in sub.columns]
    need = max(3, (len(feats) - 1) // 2)
    sub = sub[sub[present].notna().sum(axis=1) >= need]
    X = sub.reindex(columns=feats)
    pred = model.predict(X)
    chrono = sub["age"].values.astype(float)
    resid = pred - chrono
    # linear fit resid ~ chrono
    b, a = np.polyfit(chrono, resid, 1)   # resid ≈ a + b*chrono
    corrected = pred - (a + b * chrono)
    out[organ] = {"a": round(float(a), 4), "b": round(float(b), 5),
                  "before_bias_young": round(float(resid[chrono < 40].mean()), 1),
                  "before_bias_old": round(float(resid[chrono >= 60].mean()), 1),
                  "after_bias_young": round(float((corrected - chrono)[chrono < 40].mean()), 1),
                  "after_bias_old": round(float((corrected - chrono)[chrono >= 60].mean()), 1),
                  "n": int(len(sub))}
    print(f"{organ:16} resid=a+b*chrono  a={a:+.2f} b={b:+.3f} | "
          f"bias young {out[organ]['before_bias_young']:+.1f}→{out[organ]['after_bias_young']:+.1f}  "
          f"old {out[organ]['before_bias_old']:+.1f}→{out[organ]['after_bias_old']:+.1f}")

path = os.path.join(ASSETS, "organ_calibration.json")
json.dump(out, open(path, "w"), indent=1)
print(f"\nwrote {path}")
