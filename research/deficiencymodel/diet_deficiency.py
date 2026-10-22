#!/usr/bin/env python3
"""NHANES diet -> deficiency models: predict a measured biomarker deficiency from dietary intake +
demographics. Grounds the supplement engine in population data (who tends to be deficient), and —
honestly — shows WHY we still MEASURE: diet only partly predicts status (absorption, sun, genetics),
so modest AUC is the expected, useful finding, not a failure. Uses pandas (no pyreadstat dep).
"""
import glob, os, json, warnings
import numpy as np, pandas as pd, joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__); RNG = 42
MODELS = os.path.join(HERE, "models"); os.makedirs(MODELS, exist_ok=True)
INTAKE = {"DR1TKCAL": "energy", "DR1TPROT": "protein", "DR1TFIBE": "fiber", "DR1TFOLA": "folate_intake",
          "DR1TVB12": "b12_intake", "DR1TVC": "vitc", "DR1TVD": "vitd_intake", "DR1TCALC": "calcium",
          "DR1TMAGN": "magnesium_intake", "DR1TIRON": "iron_intake", "DR1TZINC": "zinc_intake"}


def rx(stem, cols):
    hits = [h for h in glob.glob(os.path.join(HERE, "raw", stem + ".*")) if h.lower().endswith(".xpt")]
    if not hits:
        return None
    try:
        df = pd.read_sas(hits[0], format="xport")
    except Exception:
        return None
    df.columns = [c.strip() for c in df.columns]
    keep = ["SEQN"] + [c for c in cols if c in df.columns]
    return df[keep] if len(keep) > 1 else None


def cycle(suf):
    demo = rx(f"DEMO_{suf}", ["RIDAGEYR", "RIAGENDR", "RIDRETH1"])
    if demo is None:
        return None
    df = demo.rename(columns={"RIDAGEYR": "age", "RIAGENDR": "sex", "RIDRETH1": "race"})
    diet = rx(f"DR1TOT_{suf}", list(INTAKE))
    if diet is not None:
        df = df.merge(diet.rename(columns=INTAKE), on="SEQN", how="left")
    for stem, c, new in [(f"VID_{suf}", "LBXVIDMS", "vitd_25oh_nmol"), (f"FERTIN_{suf}", "LBXFER", "ferritin"),
                         (f"FOLATE_{suf}", "LBDRFOSI", "rbc_folate_nmol"), (f"FOLATE_{suf}", "LBDFOTSI", "serum_folate_nmol"),
                         (f"VITB12_{suf}", "LBDB12SI", "b12_pmol"), (f"VITB12_{suf}", "LBXB12", "b12_pgml")]:
        b = rx(stem, [c])
        if b is not None:
            df = df.merge(b.rename(columns={c: new}), on="SEQN", how="left")
    df["cycle"] = suf
    return df


df = pd.concat([c for c in (cycle(s) for s in ["H", "I", "J"]) if c is not None], ignore_index=True)
df = df[(df.age >= 18) & (df.age <= 80)]
# deficiency labels (standard clinical thresholds)
df["def_vitamin_d"] = (df["vitd_25oh_nmol"] < 50).where(df["vitd_25oh_nmol"].notna())
df["def_iron"] = (df["ferritin"] < 30).where(df["ferritin"].notna())
if "rbc_folate_nmol" in df: df["def_folate"] = (df["rbc_folate_nmol"] < 305).where(df["rbc_folate_nmol"].notna())
if "serum_folate_nmol" in df: df["def_folate_serum"] = (df["serum_folate_nmol"] < 7).where(df["serum_folate_nmol"].notna())
if "b12_pmol" in df: df["def_b12"] = (df["b12_pmol"] < 148).where(df["b12_pmol"].notna())
elif "b12_pgml" in df: df["def_b12"] = (df["b12_pgml"] < 200).where(df["b12_pgml"].notna())

FEATS = ["age", "sex", "race"] + [v for v in INTAKE.values() if v in df.columns]
print(f"assembled {len(df):,} adults (cycles H+I+J); features {len(FEATS)}")

results = {"_meta": {"source": "NHANES 2013-2018 (H,I,J); diet intake + demographics -> measured biomarker deficiency",
                     "features": FEATS, "note": "diet partly predicts status; we still MEASURE (absorption/sun/genetics)"}}
TARGETS = [("def_vitamin_d", "vitamin D (<50 nmol/L)"), ("def_iron", "iron/ferritin (<30 ng/mL)"),
           ("def_folate", "RBC folate (<305 nmol/L)"), ("def_folate_serum", "serum folate (<7 nmol/L)"),
           ("def_b12", "vitamin B12 (<148 pmol/L)")]
for tgt, label in TARGETS:
    if tgt not in df.columns:
        continue
    sub = df[df[tgt].notna()]
    y = sub[tgt].astype(int)
    if y.sum() < 50 or len(sub) < 800:
        print(f"skip {tgt}: n={len(sub)} pos={int(y.sum())}"); continue
    X = sub[FEATS]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG, stratify=y)
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, l2_regularization=1.0,
                                         random_state=RNG, class_weight="balanced", early_stopping=True)
    clf.fit(Xtr, ytr)
    p = clf.predict_proba(Xte)[:, 1]
    auc, ap = roc_auc_score(yte, p), average_precision_score(yte, p)
    joblib.dump(clf, os.path.join(MODELS, f"{tgt}.joblib"))
    results[tgt] = {"label": label, "n": int(len(sub)), "prevalence": round(float(y.mean()), 3),
                    "test_AUC": round(float(auc), 3), "test_AP": round(float(ap), 3)}
    print(f"{tgt:<18} {label:<28} n={len(sub):>6} prev={y.mean():.2f}  AUC={auc:.3f} AP={ap:.3f}")

json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=2)
print(f"\nSaved {len([k for k in results if k != '_meta'])} deficiency models + results.json")
