#!/usr/bin/env python3
"""Train the Telomy aging-clock family on NHANES (adults 18-85).

Models (each gets its own train/test split + 5-fold CV, each >1000 samples):
  1. telomy_full      - flagship chronological-age clock, full routine blood panel
  2. telomy_clinic9   - compact clock using only PhenoAge's 9 markers (cheap panel USP)
  3. telomy_cbc       - haematology-only sub-clock (CBC)
  4. telomy_metabolic - metabolic sub-clock (glucose, hba1c, insulin, lipids)
  5. telomy_liverkidney - hepatic/renal sub-clock
We also compute the published Levine-2018 PhenoAge (biological age) as a reference
and report how our learned clock compares.
"""
import json, os, warnings
import numpy as np, pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNetCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import pearsonr
import joblib
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__)
df = pd.read_csv(os.path.join(HERE, "nhanes_bloodpanel.csv"))
df = df[(df["age"] >= 18) & (df["age"] <= 80)].copy()   # NHANES tops out at 80 (top-coded)
RNG = 42

PANELS = {
    "telomy_full": ["sex","albumin","creatinine","glucose","crp_mgL","lymph_pct","neut_pct",
        "mono_pct","eos_pct","baso_pct","rbc","hgb","hct","mcv","rdw","platelets","mpv","wbc",
        "alt","ast","alp","ggt","bun","uric_acid","calcium","phosphorus","sodium","potassium",
        "bicarb","bilirubin","total_protein","globulin","iron","hba1c","total_chol","hdl","trig"],
    "telomy_clinic9": ["albumin","creatinine","glucose","crp_mgL","lymph_pct","mcv","rdw","alp","wbc"],
    "telomy_cbc": ["wbc","lymph_pct","neut_pct","mono_pct","eos_pct","baso_pct","rbc","hgb","hct","mcv","rdw","platelets","mpv"],
    "telomy_metabolic": ["glucose","hba1c","insulin","total_chol","hdl","trig","uric_acid","bun"],
    "telomy_liverkidney": ["alt","ast","alp","ggt","bilirubin","albumin","total_protein","globulin","creatinine","bun","uric_acid"],
}

def phenoage(d):
    """Levine 2018 phenotypic age (years) from 9 markers + chronological age."""
    alb = d["albumin"]*10          # g/dL -> g/L
    creat = d["creatinine"]*88.4   # mg/dL -> umol/L
    glu = d["glucose"]*0.0555      # mg/dL -> mmol/L
    crp = np.log(np.clip(d["crp_mgL"]/10.0, 0.01, None))  # mg/L -> mg/dL -> ln
    xb = (-19.907 - 0.0336*alb + 0.0095*creat + 0.1953*glu + 0.0954*crp
          - 0.0120*d["lymph_pct"] + 0.0268*d["mcv"] + 0.3306*d["rdw"]
          + 0.00188*d["alp"] + 0.0554*d["wbc"] + 0.0804*d["age"])
    g = 0.0076927
    mort = 1 - np.exp(-np.exp(xb) * (np.exp(g*120) - 1) / g)
    mort = np.clip(mort, 1e-6, 1-1e-6)
    return 141.50225 + np.log(-0.00553*np.log(1-mort)) / 0.090165

def make_model():
    return HistGradientBoostingRegressor(max_iter=600, learning_rate=0.05,
        max_depth=None, l2_regularization=1.0, random_state=RNG)

results = {}
models_dir = os.path.join(HERE, "models"); os.makedirs(models_dir, exist_ok=True)

for name, feats in PANELS.items():
    feats = [f for f in feats if f in df.columns]
    # keep every adult with age + at least half the panel measured; HGB uses NaN natively (no row drop)
    need = max(1, len(feats)//2)
    sub = df[df[feats].notna().sum(axis=1) >= need].dropna(subset=["age"])
    if len(sub) < 1000:
        print(f"skip {name}: only {len(sub)} rows"); continue
    X, y = sub[feats].values, sub["age"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG)
    pipe = make_model()                       # HistGradientBoosting: native NaN support, no imputer
    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    mae = mean_absolute_error(yte, pred); r2 = r2_score(yte, pred); r = pearsonr(yte, pred)[0]
    cv = -cross_val_score(pipe, X, y, cv=5, scoring="neg_mean_absolute_error")
    # ElasticNet linear baseline (interpretable)
    lin = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()),
                    ("en", ElasticNetCV(cv=4, random_state=RNG))]).fit(Xtr, ytr)
    lin_mae = mean_absolute_error(yte, lin.predict(Xte))
    joblib.dump(pipe, os.path.join(models_dir, f"{name}.joblib"))
    results[name] = {"n": int(len(sub)), "n_features": len(feats),
        "test_MAE_years": round(float(mae),3), "test_R2": round(float(r2),3),
        "test_pearson_r": round(float(r),3), "cv5_MAE_mean": round(float(cv.mean()),3),
        "cv5_MAE_std": round(float(cv.std()),3), "elasticnet_MAE": round(float(lin_mae),3)}
    print(f"{name:<20} n={len(sub):>6} feats={len(feats):>2}  MAE={mae:5.2f}y  R2={r2:.3f}  r={r:.3f}  (EN {lin_mae:.2f}y)")

# ---- PhenoAge biological-age reference (needs the 9 clinic markers) ----
pa_feats = ["albumin","creatinine","glucose","crp_mgL","lymph_pct","mcv","rdw","alp","wbc","age"]
pa = df.dropna(subset=pa_feats).copy()
pa["phenoage"] = phenoage(pa)
pa = pa[(pa["phenoage"] > 0) & (pa["phenoage"] < 150)]
acc = pearsonr(pa["age"], pa["phenoage"])
accel = pa["phenoage"] - pa["age"]   # "age acceleration" = the actual clinical signal
results["phenoage_reference"] = {"n": int(len(pa)),
    "pearson_r_vs_chronological": round(float(acc[0]),3),
    "mean_age_accel_years": round(float(accel.mean()),3),
    "std_age_accel_years": round(float(accel.std()),3)}
print(f"\nPhenoAge (Levine 2018 biological age): n={len(pa)}  r(vs chrono)={acc[0]:.3f}  "
      f"age-accel {accel.mean():+.2f}±{accel.std():.2f}y")

# ---- flagship feature importance (permutation-free: HGB has none, use correlation proxy) ----
flag = df.dropna(subset=[f for f in PANELS['telomy_clinic9']]+["age"])
corrs = {f: round(float(np.corrcoef(flag[f], flag["age"])[0,1]),3) for f in PANELS['telomy_clinic9']}
results["clinic9_marker_corr_with_age"] = dict(sorted(corrs.items(), key=lambda kv:-abs(kv[1])))

json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=2)
print("\nsaved -> results.json, models/*.joblib")
