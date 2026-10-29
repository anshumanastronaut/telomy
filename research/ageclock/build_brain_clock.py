#!/usr/bin/env python3
"""PHASE 2 — BRAIN (cognitive-performance) aging clock (NHANES CFQ, cycles G/H = 2011-2014).

HONEST SCOPE: NHANES administered the cognitive battery only to adults aged 60+, so this is a
COGNITIVE-PERFORMANCE age calibrated on 60-80y (age SD ~6.8y). It is NOT a structural brain-age
(no MRI) and must NOT be extrapolated below 60 without external younger-adult norms. We label this
limitation everywhere and clamp serving to the trained support.

Inputs (CFQ): CERAD word-learning immediate total (3 trials), CERAD delayed recall, Animal Fluency,
Digit-Symbol Substitution Test (DSST). Model: HistGradientBoosting -> chronological age; residual =
cognitive-age acceleration. Validation: held-out MAE + 5-fold CV + age-residualized, age/sex-adjusted
Cox HR per +1 SD acceleration for all-cause mortality (CFQ G/H merge to the Linked Mortality Files).

The plasma-NfL route (catalog id `nfl`) is a SEPARATE path kept in backend/app/organs.py; the
recommendation (see report) is to map NfL via the Benkert 2022 age-adjusted sNfL reference percentiles
rather than the current hand-tuned exponential. We do not fabricate those reference coefficients here.

Writes backend/app/assets/organ_brain.joblib and merges brain params/metrics into organ_phenoage.json
+ organ_results.json.

Run: backend/.venv/bin/python research/ageclock/build_brain_clock.py
"""
import os, sys, json, glob
import numpy as np, pandas as pd, joblib
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import pearsonr
from lifelines import CoxPHFitter
warnings = __import__("warnings"); warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__)); RNG = 42
ASSETS = os.path.abspath(os.path.join(HERE, "..", "..", "backend", "app", "assets"))
BRAIN = os.path.join(HERE, "brain", "raw")
MORT_DIR = os.path.abspath(os.path.join(HERE, "..", "diseasemodel", "mort"))
SPANS = {"SEQN": (0, 6), "ELIGSTAT": (14, 15), "MORTSTAT": (15, 16), "PERMTH_EXM": (45, 48)}
FEATS = ["sex", "cerad_total", "cerad_delayed", "animal_fluency", "dsst"]


def load_mortality():
    rows = []
    for f in glob.glob(os.path.join(MORT_DIR, "*.dat")):
        for line in open(f):
            line = line.rstrip("\n")
            if len(line) < 47:
                continue
            g = lambda k: line[SPANS[k][0]:SPANS[k][1]].strip()
            if g("ELIGSTAT") != "1" or g("MORTSTAT") not in ("0", "1"):
                continue
            rows.append({"SEQN": int(g("SEQN")), "mortstat": int(g("MORTSTAT")),
                         "permth": int(g("PERMTH_EXM")) if g("PERMTH_EXM").isdigit() else None})
    return pd.DataFrame(rows).dropna(subset=["permth"])


def main():
    rows = []
    for s in ["G", "H"]:
        cfq = pd.read_sas(os.path.join(BRAIN, f"CFQ_{s}.xpt"))
        demo = pd.read_sas(os.path.join(BRAIN, f"DEMO_{s}.xpt"))[["SEQN", "RIDAGEYR", "RIAGENDR"]]
        rows.append(cfq.merge(demo, on="SEQN"))
    d = pd.concat(rows, ignore_index=True)
    d["cerad_total"] = d[["CFDCST1", "CFDCST2", "CFDCST3"]].sum(axis=1, min_count=3)
    d["cerad_delayed"] = d["CFDCSR"]; d["animal_fluency"] = d["CFDAST"]; d["dsst"] = d["CFDDS"]
    d["age"] = d.RIDAGEYR.astype(float); d["sex"] = d.RIAGENDR.astype(float)
    d = d.dropna(subset=["cerad_total", "cerad_delayed", "animal_fluency", "dsst", "age"])
    d = d[(d.age >= 60) & (d.age <= 80)].copy()
    print(f"brain cognitive usable n={len(d):,}  age {d.age.min():.0f}-{d.age.max():.0f} (SD {d.age.std():.1f}y)")

    X, y = d[FEATS], d.age.values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG)
    mk = lambda: HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, l2_regularization=1.0,
                                               max_leaf_nodes=15, random_state=RNG)
    model = mk().fit(Xtr, ytr)
    pred = model.predict(Xte)
    mae, r2 = mean_absolute_error(yte, pred), r2_score(yte, pred)
    cv = -cross_val_score(mk(), X, y, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1)
    baseline = mean_absolute_error(yte, np.full_like(yte, ytr.mean()))
    print(f"BRAIN cognitive-age clock: test MAE={mae:.2f}y  R2={r2:.3f}  r={pearsonr(yte,pred)[0]:.3f}  "
          f"cv5={cv.mean():.2f}y  (predict-the-mean baseline MAE={baseline:.2f}y within 60-80)")

    oof = np.full(len(d), np.nan)
    for tr, te in KFold(5, shuffle=True, random_state=RNG).split(X):
        oof[te] = mk().fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
    bb, aa = np.polyfit(d.age.values, oof, 1)
    d["accel"] = oof - (aa + bb * d.age.values)       # age-residualized
    mort = load_mortality()
    dm = d.merge(mort, on="SEQN", how="inner").copy()
    dm["accel_z"] = (dm.accel - dm.accel.mean()) / dm.accel.std()
    cd = pd.DataFrame({"T": dm.permth.astype(float), "E": dm.mortstat.astype(int),
                       "accel_z": dm.accel_z, "age": dm.age.values, "sex": dm.sex.values}).dropna()
    cph = CoxPHFitter().fit(cd, "T", "E")
    lo, up = cph.confidence_intervals_.loc["accel_z"].values
    hr = {"HR_per_SD": round(float(np.exp(cph.params_["accel_z"])), 3),
          "HR_CI95": [round(float(np.exp(lo)), 3), round(float(np.exp(up)), 3)],
          "p": float(cph.summary.loc["accel_z", "p"]), "n": int(len(cd)), "n_deaths": int(cd.E.sum()),
          "adjusted_for": ["chronological_age", "sex"], "accel": "age-residualized"}
    print(f"BRAIN Cox HR per +1SD worse-cognition accel (all-cause): {hr['HR_per_SD']} CI{hr['HR_CI95']} "
          f"(n={hr['n']:,}, deaths={hr['n_deaths']})")

    joblib.dump(model, os.path.join(ASSETS, "organ_brain.joblib"))
    pj = os.path.join(ASSETS, "organ_phenoage.json")
    serving = json.load(open(pj)) if os.path.exists(pj) else {}
    cb, ca = np.polyfit(d.age.values, oof - d.age.values, 1)
    serving["brain"] = {"features": FEATS, "age_support": [60, 80],
                        "higher_is_younger": True, "low_confidence": True,
                        "cal_a": round(float(ca), 4), "cal_b": round(float(cb), 5),
                        "note": "cognitive-performance age (ages 60+ only); do NOT extrapolate <60. NfL route "
                                "(catalog id nfl) is separate: map via Benkert 2022 age-adjusted sNfL percentiles."}
    json.dump(serving, open(pj, "w"), indent=1)

    rj = os.path.join(HERE, "organ_results.json")
    results = json.load(open(rj))
    results["organ_brain"] = {"n": int(len(d)), "features": FEATS,
        "test_MAE_years": round(float(mae), 2), "test_R2": round(float(r2), 3),
        "cv5_MAE_mean": round(float(cv.mean()), 2), "within_range_baseline_MAE": round(float(baseline), 2),
        "age_support": [60, 80], "cox_hr_accel": hr,
        "caveat": "COGNITIVE-PERFORMANCE age, not structural brain age (no MRI). Trained on ages 60-80 only "
                  "(narrow range -> low MAE is partly range compression; see within_range_baseline_MAE). Do not "
                  "extrapolate <60. NfL plasma route should use Benkert 2022 reference percentiles (not trained here)."}
    json.dump(results, open(rj, "w"), indent=2)
    print("saved organ_brain.joblib + merged brain params/metrics")


if __name__ == "__main__":
    main()
