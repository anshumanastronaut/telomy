#!/usr/bin/env python
"""Per-organ age-bias correction for the chronological organ clocks (MONOTONE-SPLINE version).

The chrono clocks (gradient boosting -> chronological age) regress toward the population mean: they
over-age the young and under-age the old, so `age_acceleration = pred - chrono` carries a residual
age trend. We remove that trend.

Previous version fit a single straight line  resid = a + b*chrono  (np.polyfit). But aging is
nonlinear — Shen 2024 (Nat Aging) shows crests near ~44 and ~60 — so a linear residual fit leaves
age-structured error around those crests. This version fits a MONOTONE smoother instead: median
residual per 1-year age bin, then isotonic (non-increasing) regression -> a smooth monotone
correction curve c(age), evaluated on an age grid the serving layer interpolates with numpy.

This is strictly BIAS REMOVAL (flattening mean residual vs age); it is NOT a claim that aging is
linear or monotone. A residual-by-age-decade table (before vs after) is written to prove flatness.
The linear a/b are kept as a fallback for any serving code that predates the grid.

Writes backend/app/assets/organ_calibration.json.
Run: backend/.venv/bin/python research/ageclock/calibrate_organ_clocks.py
"""
import os, sys, json
import numpy as np, pandas as pd, joblib
from sklearn.isotonic import IsotonicRegression

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "..", "backend", "app", "assets")
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
from app.llx import organ_tools as O  # feature lists  # noqa: E402

GRID = list(range(18, 81))                 # ages the serving layer interpolates over
DECADES = [(18, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 81)]


def decade_table(chrono, resid):
    out = {}
    for lo, hi in DECADES:
        m = (chrono >= lo) & (chrono < hi)
        out[f"{lo}-{hi - 1}"] = round(float(resid[m].mean()), 2) if m.sum() else None
    return out


df = pd.read_csv(os.path.join(HERE, "nhanes_bloodpanel.csv"))
out = {}
for organ, feats_all in O.ORGANS.items():
    model = joblib.load(os.path.join(ASSETS, f"organ_{organ}.joblib"))
    feats = list(getattr(model, "feature_names_in_", ["sex"] + [m for m in feats_all if m in df.columns]))
    sub = df.dropna(subset=["age"]).copy()
    present = [f for f in feats if f in sub.columns]
    need = max(3, (len(feats) - 1) // 2)
    sub = sub[sub[present].notna().sum(axis=1) >= need]
    pred = model.predict(sub.reindex(columns=feats))
    chrono = sub["age"].values.astype(float)
    resid = pred - chrono

    # linear fit (kept as fallback)
    b, a = np.polyfit(chrono, resid, 1)

    # monotone smoother: median residual per 1-year bin -> isotonic (non-increasing)
    ages = np.arange(18, 81)
    med, wts = [], []
    for ag in ages:
        m = np.abs(chrono - ag) < 0.5
        if m.sum() >= 5:
            med.append(float(np.median(resid[m]))); wts.append(int(m.sum()))
        else:
            med.append(np.nan); wts.append(0)
    med = np.array(med); wts = np.array(wts, float)
    ok = wts > 0
    iso = IsotonicRegression(increasing=False, out_of_bounds="clip")
    iso.fit(ages[ok], med[ok], sample_weight=wts[ok])
    grid_corr = iso.predict(np.array(GRID, float))

    corr_spline = np.interp(chrono, GRID, grid_corr)
    corr_linear = a + b * chrono
    out[organ] = {
        "method": "monotone_spline",
        "grid_age": GRID, "grid_corr": [round(float(c), 3) for c in grid_corr],
        "a": round(float(a), 4), "b": round(float(b), 5),       # linear fallback
        "n": int(len(sub)),
        "resid_by_decade_raw": decade_table(chrono, resid),
        "resid_by_decade_after_linear": decade_table(chrono, resid - corr_linear),
        "resid_by_decade_after_spline": decade_table(chrono, resid - corr_spline),
    }
    rd, rl, rs = (out[organ]["resid_by_decade_raw"], out[organ]["resid_by_decade_after_linear"],
                  out[organ]["resid_by_decade_after_spline"])
    worst_raw = max(abs(v) for v in rd.values() if v is not None)
    worst_lin = max(abs(v) for v in rl.values() if v is not None)
    worst_spl = max(abs(v) for v in rs.values() if v is not None)
    print(f"{organ:16} worst |decade bias|  raw {worst_raw:4.1f}y -> linear {worst_lin:4.1f}y -> spline {worst_spl:4.1f}y")

path = os.path.join(ASSETS, "organ_calibration.json")
json.dump(out, open(path, "w"), indent=1)
print(f"\nwrote {path}")
