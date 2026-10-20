"""Score any food/product's nutritional quality from its label — trained on Open Food Facts (>1M products).

score(nutrients_per_100g) -> Nutri-Score grade (A–E, food quality) + NOVA group (1–4, ultra-processing)
+ a plain-language verdict. Lets Telomy grade anything the user logs or scans, and powers the
"nudge toward better choices" loop. Models: telomy-app/research/nutritionmodel (HistGradientBoosting).
"""
from __future__ import annotations
import os, json
import numpy as np, joblib

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets", "foodscore")
FEATURES = ["energy-kcal_100g", "fat_100g", "saturated-fat_100g", "carbohydrates_100g",
            "sugars_100g", "fiber_100g", "proteins_100g", "salt_100g", "sodium_100g"]
# accept friendly keys too (map the nutrition engine's names -> model feature names)
ALIAS = {"kcal": "energy-kcal_100g", "energy": "energy-kcal_100g", "fat_g": "fat_100g",
         "satfat_g": "saturated-fat_100g", "carb_g": "carbohydrates_100g", "sugar_g": "sugars_100g",
         "fiber_g": "fiber_100g", "protein_g": "proteins_100g", "sodium_mg": "sodium_100g"}
_C = {}

def _m(name):
    if name not in _C:
        _C[name] = joblib.load(os.path.join(ASSETS, f"{name}.joblib"))
    return _C[name]

def _vec(n):
    d = dict(n)
    for k, v in list(d.items()):
        if k in ALIAS:
            d.setdefault(ALIAS[k], v)
    if "sodium_mg" in n and "sodium_100g" not in d:        # mg per serving isn't /100g; only if given as /100g
        pass
    return np.array([[float(d[f]) if d.get(f) not in (None, "") else np.nan for f in FEATURES]])

def score(nutrients_per_100g: dict) -> dict:
    x = _vec(nutrients_per_100g)
    grade = str(_m("nutriscore").predict(x)[0]).upper()
    nova = int(_m("nova_processing").predict(x)[0])
    verdicts = {"A": "excellent nutritional quality", "B": "good", "C": "moderate",
                "D": "poor — occasional", "E": "very poor — limit"}
    nova_txt = {1: "unprocessed / minimally processed", 2: "processed culinary ingredient",
                3: "processed food", 4: "ultra-processed"}
    msg = f"Nutri-Score {grade} ({verdicts.get(grade,'')}); {nova_txt.get(nova,'')}."
    if grade in ("D", "E") or nova == 4:
        msg += " Good candidate to swap for a less-processed option."
    return {"nutriscore_grade": grade, "nova_group": nova, "nova_label": nova_txt.get(nova),
            "verdict": verdicts.get(grade), "message": msg,
            "source": "trained on Open Food Facts >1M products"}

if __name__ == "__main__":
    print("oats (A-ish):", json.dumps(score({"kcal": 370, "fat_g": 7, "satfat_g": 1.2, "carb_g": 60,
          "sugar_g": 1, "fiber_g": 10, "protein_g": 13, "salt_100g": 0.0}), indent=2))
    print("\nsoda/junk (E-ish):", json.dumps(score({"kcal": 420, "fat_g": 20, "satfat_g": 10, "carb_g": 62,
          "sugar_g": 55, "fiber_g": 0.5, "protein_g": 3, "salt_100g": 1.2}), indent=2))
