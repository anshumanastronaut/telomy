"""Meal nutrition engine — map a recognised food (+ portion in grams) to its nutrition.

Pipeline for a meal photo:  image -> food_recognition.label()  ->  nutrition.lookup(label, grams)
This module is the deterministic back half (grounded in USDA SR Legacy), mirroring the Telomy
principle: the vision model proposes a food + portion, this table supplies the real numbers.

Run `python -m telomy_vision.nutrition "grilled chicken breast" 180` for a demo.
"""
from __future__ import annotations
import os, sys, functools
import pandas as pd

HERE = os.path.dirname(__file__)
DB = os.path.join(HERE, "..", "assets", "nutrition_db.csv")
MACROS = ["kcal", "protein_g", "fat_g", "satfat_g", "carb_g", "fiber_g", "sugar_g",
          "sodium_mg", "potassium_mg", "calcium_mg", "iron_mg", "cholesterol_mg"]

@functools.lru_cache(maxsize=1)
def _db():
    return pd.read_csv(DB)

# tokens that signal a processed/unwanted match when the query didn't ask for them
_NOISE = {"breaded", "uncooked", "dough", "mix", "frozen", "canned", "dry", "coating", "batter",
          "refrigerated", "flavored", "artificial", "substitute", "imitation"}

def _overlap(query, name):
    return len(set(query.lower().split()) & set(str(name).lower().replace(",", " ").split()))

def search(query: str, k: int = 5):
    """Rank foods by how fully they cover the query, preferring plain, concise, whole-food matches."""
    db = _db(); q = set(query.lower().split())
    def score(name):
        toks = set(str(name).replace(",", " ").split())
        overlap = len(q & toks)
        coverage = overlap / max(1, len(q))              # fraction of the query matched
        noise = len(_NOISE & toks - q)                   # processed words the user didn't ask for
        return 2.0 * coverage + 0.5 * overlap - 0.02 * len(toks) - 0.6 * noise
    sc = db["name_lc"].map(score)
    top = db.assign(_s=sc).sort_values("_s", ascending=False).head(k)
    cols = ["fdc_id", "description", "kcal", "protein_g", "fat_g", "carb_g"]
    if "source" in top: cols.append("source")
    return top[cols].to_dict("records")

def lookup(food: str, grams: float = 100.0) -> dict:
    """Return nutrition for `grams` of the best-matching food (per-100g scaled). Flags low confidence
    when the match shares no words with the query (e.g. a prepared dish not in the ingredient tables)."""
    hits = search(food, k=1)
    if not hits:
        return {"error": "no_match", "query": food}
    row = _db().set_index("fdc_id").loc[hits[0]["fdc_id"]]
    f = grams / 100.0
    out = {m: (round(float(row[m]) * f, 1) if pd.notna(row.get(m)) else None) for m in MACROS}
    overlap = _overlap(food, row["description"])
    return {"query": food, "matched_food": row["description"], "grams": grams, "per_serving": out,
            "source": row.get("source", "USDA SR Legacy"),
            "match_confidence": "low" if overlap == 0 else ("medium" if overlap == 1 else "high"),
            **({"warning": "no close match — prepared dishes may need a recipe breakdown"} if overlap == 0 else {})}

@functools.lru_cache(maxsize=1)
def _recipes():
    import json
    path = os.path.join(HERE, "..", "assets", "indian_recipes.json")
    try:
        return {k: v for k, v in json.load(open(path)).items() if not k.startswith("_")}
    except Exception:
        return {}

def _recipe_match(query: str):
    """Find a dish whose name shares the most words with the query (needs >=1 shared word)."""
    q = set(query.lower().split()); best, bs = None, 0
    for name, r in _recipes().items():
        ov = len(q & set(name.replace("-", " ").split()))
        if ov > bs:
            best, bs = (name, r), ov
    return best

def lookup_dish(query: str) -> dict | None:
    """Resolve a prepared Indian dish to real nutrition by summing its ingredients (per serving)."""
    m = _recipe_match(query)
    if not m:
        return None
    name, r = m
    total = {k: 0.0 for k in MACROS}; parts = []
    for ing, grams in r["ingredients"]:
        got = lookup(ing, grams)
        parts.append({"ingredient": ing, "grams": grams, "matched": got.get("matched_food")})
        for k in MACROS:
            v = got.get("per_serving", {}).get(k)
            if v:
                total[k] += v
    return {"query": query, "matched_dish": name, "serving": r["serving"],
            "per_serving": {k: round(total[k], 1) for k in MACROS}, "ingredients": parts,
            "source": "Telomy recipe (IFCT/USDA ingredients)", "match_confidence": "recipe"}

# distinctive prepared-dish words that should route to the recipe resolver, not the ingredient table
_DISH_WORDS = {"idli", "dosa", "uttapam", "vada", "poha", "upma", "pongal", "rajma", "chole", "chana",
               "sambar", "khichdi", "biryani", "pulao", "paratha", "roti", "chapati", "poori", "chilla",
               "omelette", "tadka", "masala", "palak", "kadhi", "makhani", "gobi", "bhindi", "baingan",
               "bharta", "sabzi", "matar", "tikka", "pav", "bhaji", "kheer", "halwa", "lassi", "chai",
               "gulab", "jamun", "jeera", "curd", "yogurt"}

def nutrition_of(query: str, grams: float | None = None) -> dict:
    """Smart entry point: a prepared dish (by distinctive name) resolves via its recipe; otherwise the
    query is treated as a food/ingredient and looked up directly."""
    if set(query.lower().split()) & _DISH_WORDS:
        dish = lookup_dish(query)
        if dish:
            return dish
    return lookup(query, grams if grams is not None else 150.0)

def meal_total(items: list[tuple[str, float]]) -> dict:
    """Sum a meal: [(food, grams), ...] -> total macros + per-item breakdown."""
    breakdown, total = [], {m: 0.0 for m in MACROS}
    for food, grams in items:
        r = lookup(food, grams)
        breakdown.append(r)
        for m in MACROS:
            v = r.get("per_serving", {}).get(m)
            if v: total[m] += v
    return {"meal_total": {m: round(total[m], 1) for m in MACROS}, "items": breakdown}

if __name__ == "__main__":
    import json
    food = sys.argv[1] if len(sys.argv) > 1 else "grilled chicken breast"
    grams = float(sys.argv[2]) if len(sys.argv) > 2 else 180
    print(json.dumps(lookup(food, grams), indent=2))
    print("\n--- example meal ---")
    print(json.dumps(meal_total([("chicken breast", 180), ("white rice cooked", 150),
                                 ("broccoli raw", 90)])["meal_total"], indent=2))
