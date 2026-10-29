#!/usr/bin/env python3
"""PHASE 2 — LUNG aging clock (NHANES spirometry, SPX cycles E/F/G = 2007-2012).

Pipeline:
  * Keep only acceptable/reproducible tests (SPXNSTAT==1), adults 18-80, with height.
  * FEV1 %predicted and FVC %predicted are computed from a GLI-2012-form reference
    ln(y) = b0 + b1*ln(height_cm) + b2*ln(age) + sex, fit on this cohort. (GLI-2012 proper —
    Quanjer 2012, incl. the ethnicity term for Indian users — is the production normalization;
    documented in the report. Here we use the cohort-internal GLI-form reference so %predicted is
    fully reproducible without the external GLI spline lookup tables.)
  * fev1_fvc = raw FEV1/FVC ratio (NOT age-normalized -> carries genuine age signal).
  * HistGradientBoosting predicts chronological age from [sex, fev1_pct, fvc_pct, fev1_fvc]
    (our catalog ids). Residual = lung-age acceleration.
  * Validate: held-out MAE + 5-fold CV, and Cox HR per +1 SD acceleration for all-cause mortality
    (SPX cycles F/G merge to the NHANES Linked Mortality Files; cycle E predates the 2019 linkage).

Writes backend/app/assets/organ_lung.joblib and merges lung params/metrics into organ_phenoage.json
+ organ_results.json. Serving inputs: fev1_pct, fvc_pct, fev1_fvc.

Run: backend/.venv/bin/python research/ageclock/build_lung_clock.py
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
LUNG = os.path.join(HERE, "lung", "raw")
MORT_DIR = os.path.abspath(os.path.join(HERE, "..", "diseasemodel", "mort"))
SPANS = {"SEQN": (0, 6), "ELIGSTAT": (14, 15), "MORTSTAT": (15, 16), "PERMTH_EXM": (45, 48)}
FEATS = ["sex", "fev1_pct", "fvc_pct", "fev1_fvc"]


def load_mortality():
    rows = []
    for f in glob.glob(os.path.join(MORT_DIR, "*.dat")):
        for line in open(f):
            line = line.rstrip("\n")
            if len(line) < 47:
                continue
            g = lambda k: line[SPANS[k][0]:SPANS[k][1]].strip()
            seqn, elig, mort = g("SEQN"), g("ELIGSTAT"), g("MORTSTAT")
            if not seqn or elig != "1" or mort not in ("0", "1"):
                continue
            rows.append({"SEQN": int(seqn), "mortstat": int(mort),
                         "permth": int(g("PERMTH_EXM")) if g("PERMTH_EXM").isdigit() else None})
    return pd.DataFrame(rows).dropna(subset=["permth"])


def gli_form_reference(d, col):
    """Fit ln(col) = b0 + b1*ln(ht) + b2*male  (body-size normalization, NO age term).

    Deliberately age-free: the Morris & Temple (1985) lung-age principle is that spirometry normalized
    for body size DECLINES with age, and that decline is the clock signal. Putting age into the
    reference (as clinical GLI %predicted does) normalizes the age trend out, which both destroys the
    signal and — with two %predicted inputs — lets a model algebraically recover chronological age
    (a leak). So %predicted here = FEV1/FVC as a fraction of the height+sex expectation, age-free."""
    y = np.log(d[col].values)
    X = np.column_stack([np.ones(len(d)), np.log(d.ht.values), d.male.values])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return np.exp(X @ beta), beta.tolist()


def main():
    rows = []
    for s in ["E", "F", "G"]:
        spx = pd.read_sas(os.path.join(LUNG, f"SPX_{s}.xpt"))[["SEQN", "SPXNSTAT", "SPXNFEV1", "SPXNFVC"]]
        demo = pd.read_sas(os.path.join(LUNG, f"DEMO_{s}.xpt"))[["SEQN", "RIDAGEYR", "RIAGENDR"]]
        bmx = pd.read_sas(os.path.join(LUNG, f"BMX_{s}.xpt"))[["SEQN", "BMXHT"]]
        d = spx.merge(demo, on="SEQN").merge(bmx, on="SEQN"); d["cycle"] = s
        rows.append(d)
    d = pd.concat(rows, ignore_index=True)
    d = d[(d.SPXNSTAT == 1) & (d.SPXNFEV1 > 0) & (d.SPXNFVC > 0) &
          (d.RIDAGEYR >= 18) & (d.RIDAGEYR <= 80) & (d.BMXHT > 0)].copy()
    d["age"] = d.RIDAGEYR.astype(float)
    d["sex"] = d.RIAGENDR.astype(float)          # 1 male, 2 female (same convention as blood clocks)
    d["male"] = (d.RIAGENDR == 1).astype(float)
    d["ht"] = d.BMXHT.astype(float)
    d["fev1"] = d.SPXNFEV1.astype(float); d["fvc"] = d.SPXNFVC.astype(float)
    pred_fev1, b1 = gli_form_reference(d, "fev1")
    pred_fvc, b2 = gli_form_reference(d, "fvc")
    d["fev1_pct"] = 100.0 * d.fev1 / pred_fev1
    d["fvc_pct"] = 100.0 * d.fvc / pred_fvc
    d["fev1_fvc"] = d.fev1 / d.fvc
    print(f"lung usable n={len(d):,}  fev1_pct median={d.fev1_pct.median():.0f}  "
          f"fvc_pct median={d.fvc_pct.median():.0f}  ratio median={d.fev1_fvc.median():.3f}")

    X, y = d[FEATS], d.age.values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG)
    mk = lambda: HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05, l2_regularization=1.0,
                                               max_leaf_nodes=31, random_state=RNG)
    model = mk().fit(Xtr, ytr)
    pred = model.predict(Xte)
    mae, r2 = mean_absolute_error(yte, pred), r2_score(yte, pred)
    cv = -cross_val_score(mk(), X, y, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1)
    print(f"LUNG chrono-age clock: test MAE={mae:.2f}y  R2={r2:.3f}  r={pearsonr(yte,pred)[0]:.3f}  cv5={cv.mean():.2f}y")

    # out-of-fold acceleration -> Cox HR on cycles with mortality linkage (F/G)
    oof = np.full(len(d), np.nan)
    for tr, te in KFold(5, shuffle=True, random_state=RNG).split(X):
        oof[te] = mk().fit(X.iloc[tr], y[tr]).predict(X.iloc[te])
    # age-residualize the acceleration (remove regression-to-mean age confound), then adjust Cox for age+sex
    bb, aa = np.polyfit(d.age.values, oof, 1)
    d["accel"] = oof - (aa + bb * d.age.values)
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
    print(f"LUNG Cox HR per +1SD accel (all-cause, cycles F/G): {hr['HR_per_SD']} CI{hr['HR_CI95']} "
          f"(n={hr['n']:,}, deaths={hr['n_deaths']})")

    joblib.dump(model, os.path.join(ASSETS, "organ_lung.joblib"))

    # merge serving params (GLI-form reference coefs) + metrics
    pj = os.path.join(ASSETS, "organ_phenoage.json")
    serving = json.load(open(pj)) if os.path.exists(pj) else {}
    # age-bias calibration (same linear form as the blood clocks): corrected = pred - (a + b*age)
    cb, ca = np.polyfit(d.age.values, oof - d.age.values, 1)
    serving["lung"] = {"features": FEATS, "ref_fev1": b1, "ref_fvc": b2,
                       "cal_a": round(float(ca), 4), "cal_b": round(float(cb), 5),
                       "ref_form": "ln(y)=b0+b1*ln(ht_cm)+b2*male  (body-size norm, age-free)",
                       "note": "fev1_pct/fvc_pct here = FEV1/FVC as % of height+sex expectation (age-free, Morris "
                               "1985), NOT clinical GLI age-adjusted %predicted. Production: GLI-2012 (Quanjer "
                               "2012) with the ethnicity term for Indian users, fed as an age-free body-size %."}
    json.dump(serving, open(pj, "w"), indent=1)

    rj = os.path.join(HERE, "organ_results.json")
    results = json.load(open(rj))
    results["organ_lung"] = {"n": int(len(d)), "features": FEATS,
        "test_MAE_years": round(float(mae), 2), "test_R2": round(float(r2), 3),
        "cv5_MAE_mean": round(float(cv.mean()), 2), "accel_std_years": round(float(np.nanstd(d.accel)), 2),
        "cox_hr_accel": hr,
        "norm": "FEV1/FVC %predicted via cohort-internal GLI-form reference; fev1_fvc = raw ratio",
        "caveat": "spirometry-grade age clock; %predicted is body-size-normalized so most age signal rides on "
                  "the FEV1/FVC ratio and the %predicted deficit. GLI-2012 normalization recommended for serving."}
    json.dump(results, open(rj, "w"), indent=2)
    print("saved organ_lung.joblib + merged lung params/metrics")


if __name__ == "__main__":
    main()
