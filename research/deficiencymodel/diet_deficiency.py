#!/usr/bin/env python3
"""NHANES diet -> deficiency models: predict a measured biomarker deficiency from dietary intake +
demographics. Grounds the supplement engine in population data (who tends to be deficient), and —
honestly — shows WHY we still MEASURE: diet only partly predicts status (absorption, sun, genetics),
so modest AUC is the expected, useful finding, not a failure.
"""
import glob, os, json, warnings
import numpy as np, pandas as pd, pyreadstat, joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__); RNG = 42
INTAKE = {"DR1TKCAL":"energy","DR1TPROT":"protein","DR1TFIBE":"fiber","DR1TFOLA":"folate_intake",
          "DR1TVB12":"b12_intake","DR1TVC":"vitc","DR1TVD":"vitd_intake","DR1TCALC":"calcium",
          "DR1TMAGN":"magnesium_intake","DR1TIRON":"iron_intake"}

def rx(stem, cols):
    hits=[h for h in glob.glob(os.path.join(HERE,"raw",stem+".*")) if h.lower().endswith(".xpt")]
    if not hits: return None
    df=pyreadstat.read_xport(hits[0])[0]
    keep=["SEQN"]+[c for c in cols if c in df.columns]
    return df[keep]

def cycle(suf):
    demo=rx(f"DEMO_{suf}",["RIDAGEYR","RIAGENDR","RIDRETH1"])
    if demo is None: return None
    df=demo.rename(columns={"RIDAGEYR":"age","RIAGENDR":"sex","RIDRETH1":"race"})
    diet=rx(f"DR1TOT_{suf}",list(INTAKE))
    if diet is not None: df=df.merge(diet.rename(columns=INTAKE),on="SEQN",how="left")
    for stem,c,new in [(f"VID_{suf}","LBXVIDMS","vitd_25oh_nmol"),(f"FERTIN_{suf}","LBXFER","ferritin"),
                       (f"FOLATE_{suf}","LBDRFOSI","rbc_folate_nmol")]:
        b=rx(stem,[c])
        if b is not None: df=df.merge(b.rename(columns={c:new}),on="SEQN",how="left")
    return df

df=pd.concat([c for c in (cycle(s) for s in ["I","J"]) if c is not None],ignore_index=True)
df=df[(df.age>=18)&(df.age<=80)]
# deficiency labels (standard thresholds)
df["def_vitamin_d"]=(df["vitd_25oh_nmol"]<50).where(df["vitd_25oh_nmol"].notna())
df["def_iron"]=(df["ferritin"]<30).where(df["ferritin"].notna())
df["def_folate"]=(df["rbc_folate_nmol"]<305).where(df["rbc_folate_nmol"].notna())
FEATS=["age","sex","race"]+list(INTAKE.values())
print(f"assembled {len(df):,} adults (I+J); features {len(FEATS)}")

results={}; os.makedirs(os.path.join(HERE,"models"),exist_ok=True)
for tgt,label in [("def_vitamin_d","vitamin D (<50 nmol/L)"),("def_iron","iron/ferritin (<30 ng/mL)"),
                  ("def_folate","RBC folate (<305 nmol/L)")]:
    sub=df[df[tgt].notna()]
    y=sub[tgt].astype(int).values
    if y.sum()<50 or len(sub)<800: print(f"skip {tgt}: n={len(sub)} pos={int(y.sum())}"); continue
    X=sub[FEATS].values
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=0.2,random_state=RNG,stratify=y)
    m=HistGradientBoostingClassifier(max_iter=500,learning_rate=0.05,l2_regularization=1.0,
                                     class_weight="balanced",random_state=RNG).fit(Xtr,ytr)
    p=m.predict_proba(Xte)[:,1]
    joblib.dump(m,os.path.join(HERE,"models",f"{tgt}.joblib"))
    results[tgt]={"label":label,"n":int(len(sub)),"prevalence":round(float(y.mean()),3),
                  "test_AUC":round(float(roc_auc_score(yte,p)),3),"test_AP":round(float(average_precision_score(yte,p)),3)}
    print(f"{tgt:<16} {label:<28} n={len(sub):>5} prev={y.mean():.2f}  AUC={results[tgt]['test_AUC']}")

results["_meta"]={"features":FEATS,"cycles":"NHANES 2015-2018 (I,J)","intake_vars":INTAKE,
  "note":"diet partially predicts deficiency; modest AUC is the honest rationale to MEASURE, not just estimate from diet"}
json.dump(results,open(os.path.join(HERE,"results.json"),"w"),indent=2)
print("saved -> models/, results.json")
