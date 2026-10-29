#!/usr/bin/env python3
"""PHASE 1 — mortality-anchored organ aging clocks (NHANES 2009-2018 + Linked Mortality Files).

For each of the 5 blood organ systems we KEEP the chronological-age model (displayed organ age,
build_organ_clocks.py) and ADD two mortality-anchored biological-age estimators fit on the NHANES
all-cause mortality linkage:

  * PhenoAge  — Levine 2018 / Liu 2018 clinical-PhenoAge method: a Gompertz proportional-hazards
                mortality model on the organ's markers + chronological age, mapped to an age scale
                through an age-only Gompertz (our own cohort constants).
  * KDM       — Klemera & Doubal 2006 biological age (second estimator).

Validation (the point of mortality-anchoring, per Oh 2023 / Argentieri 2025): out-of-fold
age-acceleration (biological − chronological) must carry hazard. We report the Cox HR per +1 SD
of acceleration for all-cause mortality, with 95% CI, held out of model fitting via 5-fold OOF.

The 9-marker clinical PhenoAge (albumin/creatinine/glucose/CRP/lymph%/MCV/RDW/ALP/WBC + age) is
refit here too as the canonical reference anchor.

Writes: backend/app/assets/organ_phenoage.json (serving params, pure-numpy scorable) and updates
research/ageclock/organ_results.json with per-clock MAE / CV / Cox-HR.

Run: backend/.venv/bin/python research/ageclock/build_organ_phenoage.py
"""
import os, sys, json, glob, warnings
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import KFold, train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import pearsonr
from lifelines import CoxPHFitter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phenoage_lib as PA  # noqa: E402
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__)); RNG = 42
ASSETS = os.path.abspath(os.path.join(HERE, "..", "..", "backend", "app", "assets"))
MORT_DIR = os.path.abspath(os.path.join(HERE, "..", "diseasemodel", "mort"))

# organ panels — MUST match backend/app/llx/organ_tools.py ORGANS (sex-first for the chrono model)
ORGANS = {
    "metabolic": ["glucose_fasting", "hba1c", "insulin", "trig", "trig_serum", "hdl", "total_chol", "ldl", "uric_acid", "glucose_serum"],
    "hepatic":   ["albumin", "alt", "ast", "alp", "ggt", "bilirubin", "total_protein", "globulin"],
    "renal":     ["creatinine", "bun", "uric_acid", "phosphorus", "potassium", "sodium", "chloride", "bicarb", "calcium"],
    "immune":    ["wbc", "lymph_pct", "neut_pct", "mono_pct", "eos_pct", "baso_pct", "rdw", "platelets", "crp_mgL"],
    "cardiometabolic": ["total_chol", "hdl", "ldl", "trig", "glucose", "hba1c", "uric_acid"],
}
# canonical clinical PhenoAge markers (Levine 2018). ln-transform CRP as in the paper.
CLINIC9 = ["albumin", "creatinine", "glucose_serum", "crp_mgL", "lymph_pct", "mcv", "rdw", "alp", "wbc"]
LOG_MARKERS = {"crp_mgL"}

SPANS = {"SEQN": (0, 6), "ELIGSTAT": (14, 15), "MORTSTAT": (15, 16), "PERMTH_EXM": (45, 48)}


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


def prep_markers(sub, markers):
    """Median-impute + ln-transform selected; return X(n,p raw-ish), medians, log flags."""
    med = {}
    cols = []
    for m in markers:
        x = sub[m].astype(float).copy()
        if m in LOG_MARKERS:
            x = np.log(np.clip(x, 1e-3, None))
        mv = float(np.nanmedian(x))
        med[m] = mv
        cols.append(x.fillna(mv).values)
    return np.column_stack(cols), med


def cox_hr(bioage, age, sex, permth, event):
    """Cox HR for all-cause mortality per +1 SD of AGE-RESIDUALIZED acceleration, adjusted for
    chronological age + sex (Oh 2023 / Argentieri 2025 convention — removes the regression-to-mean
    age confound so the HR reflects biological acceleration, not just being old)."""
    b, a = np.polyfit(age, bioage, 1)
    accel = bioage - (a + b * age)                       # age-orthogonal acceleration
    z = (accel - np.nanmean(accel)) / np.nanstd(accel)
    d = pd.DataFrame({"T": permth, "E": event, "accel_z": z, "age": age, "sex": sex}).dropna()
    cph = CoxPHFitter().fit(d, duration_col="T", event_col="E")
    lo, up = cph.confidence_intervals_.loc["accel_z"].values
    return {"HR_per_SD": round(float(np.exp(cph.params_["accel_z"])), 3),
            "HR_CI95": [round(float(np.exp(lo)), 3), round(float(np.exp(up)), 3)],
            "p": float(cph.summary.loc["accel_z", "p"]), "n": int(len(d)), "n_deaths": int(d.E.sum()),
            "adjusted_for": ["chronological_age", "sex"], "accel": "age-residualized"}


def oof_phenoage(X, age, permth, event, k=5):
    """5-fold out-of-fold PhenoAge + KDM acceleration (no leakage into the HR)."""
    n = len(age)
    oof_pa = np.full(n, np.nan); oof_kdm = np.full(n, np.nan)
    kf = KFold(n_splits=k, shuffle=True, random_state=RNG)
    for tr, te in kf.split(X):
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        amu, asd = age[tr].mean(), age[tr].std() + 1e-9
        Xtr = np.column_stack([(X[tr] - mu) / sd, (age[tr] - amu) / asd])
        Xte = np.column_stack([(X[te] - mu) / sd, (age[te] - amu) / asd])
        fit = PA.fit_gompertz(Xtr, permth[tr], event[tr])
        amap = PA.fit_age_mapping(age[tr], permth[tr], event[tr])
        M = PA.gompertz_risk(fit["a"], fit["beta"], fit["gamma"], Xte)
        oof_pa[te] = PA.risk_to_phenoage(M, amap)
        kp = PA.fit_kdm(X[tr], age[tr])
        oof_kdm[te] = PA.kdm_bioage(X[te], age[te], kp)
    return oof_pa, oof_kdm


def chrono_metrics(df, markers):
    """Re-report the chronological-age clock (held-out MAE + 5-fold CV) for this organ."""
    feats = ["sex"] + [m for m in markers if m in df.columns]
    need = max(3, (len(feats) - 1) // 2)
    sub = df[df[feats].notna().sum(axis=1) >= need].dropna(subset=["age"])
    X, y = sub[feats], sub["age"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG)
    mdl = HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05, l2_regularization=1.0,
                                        max_leaf_nodes=31, random_state=RNG).fit(Xtr, ytr)
    pred = mdl.predict(Xte)
    cv = -cross_val_score(HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05,
                          l2_regularization=1.0, max_leaf_nodes=31, random_state=RNG),
                          X, y, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1)
    return {"n": int(len(sub)), "test_MAE_years": round(float(mean_absolute_error(yte, pred)), 2),
            "test_R2": round(float(r2_score(yte, pred)), 3),
            "cv5_MAE_mean": round(float(cv.mean()), 2)}


def main():
    df = pd.read_csv(os.path.join(HERE, "nhanes_bloodpanel.csv"))
    df = df[(df.age >= 18) & (df.age <= 80)].copy()
    mort = load_mortality()
    dm = df.merge(mort, on="SEQN", how="inner")
    print(f"merged blood x mortality: n={len(dm):,}  deaths={int(dm.mortstat.sum()):,}  "
          f"median follow-up={dm.permth.median():.0f} mo")

    results = json.load(open(os.path.join(HERE, "organ_results.json")))
    results["_meta"] = {
        "source": "NHANES 2009-2018 (49.7k adults) + NHANES Linked Mortality Files (follow-up to 2019)",
        "chrono_method": "HistGradientBoosting predicts chronological age per organ panel; residual = age acceleration",
        "pheno_method": "Levine 2018/Liu 2018 clinical-PhenoAge: Gompertz PH all-cause mortality model on organ "
                        "markers + chronological age, mapped to an age scale via an age-only Gompertz (our cohort)",
        "kdm_method": "Klemera & Doubal 2006 biological age (second estimator)",
        "validation": "Cox HR per +1 SD out-of-fold acceleration, all-cause mortality (Oh 2023, Argentieri 2025)",
        "references": ["Oh 2023 Nature (organ-specific proteomic aging)",
                       "Tian 2023 Nat Med (multi-organ clinical biological age)",
                       "Nie 2022 Cell Reports (multi-omics organ ages)",
                       "Levine 2018 Aging / Liu 2018 PLoS Med (PhenoAge)",
                       "Klemera & Doubal 2006 Mech Ageing Dev (KDM)"],
        "honesty": "PhenoAge takes chronological age as a model input, so its correlation with chronological age "
                   "is inflated and is NOT reported as standalone clock accuracy; the accuracy claim is the "
                   "blood-grade chronological-clock MAE (11-14y). PhenoAge's value is mortality discrimination (Cox HR).",
    }

    # preserve any Phase-2 keys (lung/brain) already written to the serving file
    pj = os.path.join(ASSETS, "organ_phenoage.json")
    serving = json.load(open(pj)) if os.path.exists(pj) else {}
    serving["_meta"] = {"method": "Levine PhenoAge Gompertz + KDM; pure-numpy scorable", "T10_months": PA.T10}
    panels = dict(ORGANS); panels["clinic9"] = CLINIC9

    hdr = f"{'clock':<16} {'n':>6} {'deaths':>6}  {'chronoMAE':>9}  {'PA r':>5}  {'HR/SD(pheno)':>12}  {'HR/SD(kdm)':>10}"
    print(hdr)
    for organ, markers in panels.items():
        markers = [m for m in markers if m in dm.columns]
        need = max(3, len(markers) // 2)
        sub = dm[dm[markers].notna().sum(axis=1) >= need].dropna(subset=["age"]).copy()
        age = sub["age"].values.astype(float)
        sex = sub["sex"].values.astype(float)
        permth = sub["permth"].values.astype(float)
        event = sub["mortstat"].values.astype(int)
        X, med = prep_markers(sub, markers)

        # out-of-fold biological age -> honest, age-adjusted HR
        oof_pa, oof_kdm = oof_phenoage(X, age, permth, event)
        accel_pa = oof_pa - age
        hr_pa = cox_hr(oof_pa, age, sex, permth, event)
        hr_kdm = cox_hr(oof_kdm, age, sex, permth, event)
        r_pa = float(pearsonr(age, oof_pa)[0])

        # final model on ALL rows -> serving params
        mu, sd = X.mean(0), X.std(0) + 1e-9
        amu, asd = age.mean(), age.std() + 1e-9
        Xs = np.column_stack([(X - mu) / sd, (age - amu) / asd])
        fit = PA.fit_gompertz(Xs, permth, event)
        amap = PA.fit_age_mapping(age, permth, event)
        kp = PA.fit_kdm(X, age)
        serving[organ] = {
            "markers": markers, "log_markers": [m for m in markers if m in LOG_MARKERS],
            "median": med, "marker_mean": mu.tolist(), "marker_sd": sd.tolist(),
            "age_mean": float(amu), "age_sd": float(asd), "need": int(need),
            "gompertz": {"a": fit["a"], "beta": fit["beta"], "gamma": fit["gamma"]},
            "age_map": amap,
            "kdm": kp,
        }

        rk = f"organ_{organ}" if organ in ORGANS else organ
        node = results.get(rk, {})
        if organ in ORGANS:
            node.update(chrono_metrics(df, ORGANS[organ]))
        node["pheno"] = {
            "n": int(len(sub)), "n_deaths": int(event.sum()),
            "phenoage_vs_chrono_r_INFLATED": round(r_pa, 3),
            "accel_std_years": round(float(np.nanstd(accel_pa)), 2),
            "cox_hr_phenoage_accel": hr_pa,
            "cox_hr_kdm_accel": hr_kdm,
        }
        results[rk] = node
        print(f"{organ:<16} {len(sub):>6} {int(event.sum()):>6}  "
              f"{node.get('test_MAE_years', float('nan')):>8}y  {r_pa:>5.2f}  "
              f"{hr_pa['HR_per_SD']:>6} [{hr_pa['HR_CI95'][0]},{hr_pa['HR_CI95'][1]}]  "
              f"{hr_kdm['HR_per_SD']:>8}")

    json.dump(serving, open(os.path.join(ASSETS, "organ_phenoage.json"), "w"), indent=1)
    json.dump(results, open(os.path.join(HERE, "organ_results.json"), "w"), indent=2)
    print(f"\nwrote {os.path.join(ASSETS, 'organ_phenoage.json')}")
    print(f"updated {os.path.join(HERE, 'organ_results.json')}")


if __name__ == "__main__":
    main()
