#!/usr/bin/env python3
"""Telomy muscular-age clock — train chronological age from DXA body composition, grip strength and
anthropometry (NHANES 2011-2018). The prediction residual (predicted - actual) is "muscular age
acceleration" — the sarcopenia / muscle-aging signal.

Models:
  muscle_full   DXA + grip + anthropometry  (grip only 2011-14; HGB uses NaN natively elsewhere)
  muscle_dxa    DXA + anthropometry         (no dynamometer needed; all 4 cycles)
  muscle_anthro anthropometry only          (cheapest: scale + tape, no DXA)
"""
import glob, json, os
import numpy as np, pandas as pd, pyreadstat, joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from scipy.stats import pearsonr
import warnings; warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__); RAW = os.path.join(HERE, "raw"); RNG = 42
SUF = ["G", "H", "I", "J"]

def rx(stem):
    hits = [h for h in glob.glob(os.path.join(RAW, stem + ".*")) if h.lower().endswith(".xpt")]
    return pyreadstat.read_xport(hits[0])[0] if hits else None

def cycle(s):
    demo = rx(f"DEMO_{s}")
    if demo is None: return None
    df = demo[["SEQN", "RIDAGEYR", "RIAGENDR"]].rename(columns={"RIDAGEYR": "age", "RIAGENDR": "sex"})
    dxx = rx(f"DXX_{s}")
    if dxx is not None:
        keep = {"DXDLALE":"la","DXDRALE":"ra","DXDLLLE":"ll","DXDRLLE":"rl","DXDTOLE":"total_lean_g",
                "DXDTRLE":"trunk_lean_g","DXDTOFAT":"total_fat_g","DXDTOPF":"total_fat_pct",
                "DXDTOBMD":"bmd_total","DXXLSBMD":"bmd_lumbar","DXDTOBMC":"bmc_total_g"}
        cols=["SEQN"]+[c for c in keep if c in dxx.columns]
        df = df.merge(dxx[cols].rename(columns=keep), on="SEQN", how="left")
    bmx = rx(f"BMX_{s}")
    if bmx is not None:
        keep={"BMXWT":"weight","BMXHT":"height","BMXBMI":"bmi","BMXWAIST":"waist",
              "BMXARMC":"arm_circ","BMXLEG":"leg_len","BMXARML":"arm_len"}
        cols=["SEQN"]+[c for c in keep if c in bmx.columns]
        df = df.merge(bmx[cols].rename(columns=keep), on="SEQN", how="left")
    mgx = rx(f"MGX_{s}")
    if mgx is not None and "MGDCGSZ" in mgx.columns:
        df = df.merge(mgx[["SEQN","MGDCGSZ"]].rename(columns={"MGDCGSZ":"grip_kg"}), on="SEQN", how="left")
    df["cycle"] = s
    return df

frames=[c for c in (cycle(s) for s in SUF) if c is not None]
df = pd.concat(frames, ignore_index=True)
# derived clinical features
for c in ["la","ra","ll","rl"]:
    if c not in df: df[c]=np.nan
df["alm_kg"] = (df[["la","ra","ll","rl"]].sum(axis=1))/1000.0           # appendicular lean mass (kg)
df["almi"] = df["alm_kg"] / (df["height"]/100.0)**2                      # ALM index (kg/m^2) — sarcopenia marker
df["total_lean_kg"] = df["total_lean_g"]/1000.0
df["trunk_lean_kg"] = df["trunk_lean_g"]/1000.0
df["total_fat_kg"] = df["total_fat_g"]/1000.0
df["lean_fat_ratio"] = df["total_lean_kg"]/df["total_fat_kg"]
df = df[(df.age>=18)&(df.age<=80)]
print(f"assembled {len(df):,} adults; grip present on {df['grip_kg'].notna().sum():,}; DXA on {df['almi'].notna().sum():,}")

PANELS = {
  "muscle_full":   ["sex","almi","alm_kg","total_lean_kg","trunk_lean_kg","total_fat_pct","total_fat_kg",
                    "lean_fat_ratio","bmd_total","bmd_lumbar","bmc_total_g","grip_kg","bmi","waist",
                    "arm_circ","leg_len","arm_len","weight","height"],
  "muscle_dxa":    ["sex","almi","alm_kg","total_lean_kg","trunk_lean_kg","total_fat_pct","total_fat_kg",
                    "lean_fat_ratio","bmd_total","bmd_lumbar","bmi","waist","arm_circ","weight","height"],
  "muscle_anthro": ["sex","bmi","waist","arm_circ","leg_len","arm_len","weight","height"],
}
results={}; os.makedirs(os.path.join(HERE,"models"),exist_ok=True)
for name,feats in PANELS.items():
    feats=[f for f in feats if f in df.columns]
    need=max(1,len(feats)//2)
    sub=df[df[feats].notna().sum(axis=1)>=need].dropna(subset=["age"])
    if len(sub)<1000: print(f"skip {name}: {len(sub)}"); continue
    X,y=sub[feats].values, sub["age"].values
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.2,random_state=RNG)
    m=HistGradientBoostingRegressor(max_iter=600,learning_rate=0.05,l2_regularization=1.0,random_state=RNG).fit(Xtr,ytr)
    pred=m.predict(Xte); mae=mean_absolute_error(yte,pred); r2=r2_score(yte,pred); r=pearsonr(yte,pred)[0]
    cv=-cross_val_score(m,X,y,cv=5,scoring="neg_mean_absolute_error")
    joblib.dump(m,os.path.join(HERE,"models",f"{name}.joblib"))
    results[name]={"n":int(len(sub)),"n_features":len(feats),"test_MAE_years":round(float(mae),3),
        "test_R2":round(float(r2),3),"test_pearson_r":round(float(r),3),"cv5_MAE":round(float(cv.mean()),3)}
    print(f"{name:<14} n={len(sub):>6} feats={len(feats):>2}  MAE={mae:5.2f}y  R2={r2:.3f}  r={r:.3f}")

# muscle marker correlations with age (adults with DXA)
d=df.dropna(subset=["almi","grip_kg"]) if df["grip_kg"].notna().sum()>500 else df.dropna(subset=["almi"])
for k in ["almi","alm_kg","grip_kg","total_fat_pct","lean_fat_ratio","bmd_total","waist","arm_circ"]:
    if k in df and d[k].notna().sum()>100:
        results.setdefault("marker_corr_with_age",{})[k]=round(float(np.corrcoef(d[k],d["age"])[0,1]),3)
df.to_csv(os.path.join(HERE,"nhanes_muscle.csv"),index=False)
json.dump(results,open(os.path.join(HERE,"results.json"),"w"),indent=2)
print("\nmarker corr with age:",results.get("marker_corr_with_age"))
print("saved -> models/, results.json, nhanes_muscle.csv")
