#!/usr/bin/env python3
"""Train Telomy's nutrition models on Open Food Facts (world's largest open food DB, ~3M products).

Two models from the nutrition panel (per 100 g) alone:
  • NOVA ultra-processing group (1–4) — genuinely LEARNED: processing level is defined by ingredients/
    processing, not a nutrient formula, so predicting it from the label is a real, useful signal
    ("how ultra-processed is this product?").
  • Nutri-Score grade (A–E) — a food-quality scorer. Nutri-Score is itself computed from nutrients, so
    the model largely reproduces that formula — a pipeline/sanity check + a ready scorer, framed honestly.

These let Telomy score ANY logged food/product (quality + processing) from its nutrition label,
complementing the USDA/IFCT composition engine and feeding the "nudge toward better choices" loop.
"""
import os, json, warnings
import numpy as np, pandas as pd, joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report
warnings.filterwarnings("ignore")

HERE = os.path.dirname(__file__); RNG = 42
RAW = os.path.join(HERE, "raw", "off_nutrition.tsv")
NUTRIENTS = ["energy-kcal_100g", "fat_100g", "saturated-fat_100g", "carbohydrates_100g",
             "sugars_100g", "fiber_100g", "proteins_100g", "salt_100g", "sodium_100g"]

print("loading Open Food Facts sample...")
df = pd.read_csv(RAW, sep="\t", usecols=lambda c: c in NUTRIENTS + ["nutriscore_grade", "nova_group"],
                 dtype=str, on_bad_lines="skip", engine="python", quoting=3)
print(f"  raw rows: {len(df):,}")
for c in NUTRIENTS:
    df[c] = pd.to_numeric(df[c], errors="coerce")
# NaN-tolerant plausibility: null out impossible values (HGB handles NaN natively) rather than dropping
# the whole row — keeps every product that has at least a few usable nutrients.
MACROS = ["fat_100g","saturated-fat_100g","carbohydrates_100g","sugars_100g","fiber_100g","proteins_100g"]
for c in MACROS:
    df.loc[~df[c].between(0, 100), c] = np.nan
df.loc[~df["energy-kcal_100g"].between(0, 900), "energy-kcal_100g"] = np.nan
for c in ["salt_100g", "sodium_100g"]:
    df.loc[~df[c].between(0, 100), c] = np.nan
df = df[df[NUTRIENTS].notna().sum(axis=1) >= 3]            # at least a few real nutrients
print(f"  usable rows (>=3 plausible nutrients): {len(df):,}")

results = {}
os.makedirs(os.path.join(HERE, "models"), exist_ok=True)

def train(target, name, valid):
    sub = df[df[target].isin(valid)]
    X, y = sub[NUTRIENTS].values, sub[target].astype(str).values
    if len(sub) < 1000:
        print(f"  skip {name}: {len(sub)}"); return
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=RNG, stratify=y)
    m = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.08, l2_regularization=1.0,
                                       random_state=RNG).fit(Xtr, ytr)
    pred = m.predict(Xte)
    joblib.dump(m, os.path.join(HERE, "models", f"{name}.joblib"))
    results[name] = {"n_trained": int(len(sub)), "n_test": int(len(yte)),
                     "accuracy": round(float(accuracy_score(yte, pred)), 3),
                     "macro_f1": round(float(f1_score(yte, pred, average="macro")), 3),
                     "classes": sorted(set(y))}
    print(f"\n{name}: n={len(sub):,}  accuracy={results[name]['accuracy']}  macro-F1={results[name]['macro_f1']}")
    print(classification_report(yte, pred, digits=2, zero_division=0))

train("nova_group", "nova_processing", {"1", "2", "3", "4"})
train("nutriscore_grade", "nutriscore", {"a", "b", "c", "d", "e"})

results["_meta"] = {"source": "Open Food Facts (openfoodfacts.org, ODbL)", "features": NUTRIENTS,
                    "total_usable_rows": int(len(df)),
                    "note": "NOVA = learned processing signal; Nutri-Score largely reproduces its own formula"}
json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=2)
print(f"\ntotal usable products: {len(df):,}  -> models/, results.json")
