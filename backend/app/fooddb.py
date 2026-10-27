"""Food composition lookup: USDA FoodData Central SR Legacy (2018-04, public domain / CC0), 7 793 foods per 100 g
with one typical portion each, plus micronutrients (iron, folate, B12, vitamin D, magnesium, zinc, potassium, sodium …).

Used for foods the curated Indian dish table in food.py doesn't know. Matching is deliberately strict — every word of
the query must appear in the food's name — so "chapati" never silently becomes "chapati flour, dry"; unmatched stays
unmatched and lowers the analysis confidence. Built by ~/telomy-lab/tools/build_usda.py.
"""
import gzip
import json
import os
import re
from functools import lru_cache

PATH = os.path.join(os.path.dirname(__file__), "..", "data", "foods", "usda_sr_legacy.json.gz")
STOP = {"a", "an", "the", "of", "with", "and", "some", "bowl", "plate", "cup", "glass", "piece", "pieces", "small", "large",
        "big", "medium", "serving", "g", "gm", "grams", "ml", "my", "had", "ate"}
# Raw/plain forms first: a bare query ("spinach") should hit "Spinach, raw", not a branded soup.
PLAIN = ("raw", "cooked", "boiled", "plain", "whole", "fresh")
AVOID = ("babyfood", "baby food", "infant formula", "restaurant", "fast foods", "brand")
# A product form the person didn't name: "almond" is the nut, not almond oil; "pumpkin seeds" is not sunfish.
FORMS = {"oil", "flour", "sauce", "soup", "juice", "spread", "candie", "beverage", "dressing", "mix", "nugget", "smoked",
         "roll", "glazed", "fried", "sweetened", "breaded", "frozen", "canned", "dehydrated", "powder", "dried", "salad", "sandwich", "pie", "cake", "cookie", "cracker"}


# Common words → the plain USDA entry (fdc id). Checked by hand against the SR Legacy names.
ALIAS = {"chicken breast": 171477, "chicken": 171477, "brown rice": 169704, "pumpkin seeds": 170188, "oats": 173905, "oatmeal": 173905,
         "egg": 171287, "eggs": 171287, "salmon": 175168, "chickpeas": 173757, "lentils": 172421, "tofu": None, "walnuts": None}


def _words(s: str) -> list[str]:
    return [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in re.findall(r"[a-z]+", s.lower())]


@lru_cache(maxsize=1)
def _load() -> list[dict]:
    if not os.path.exists(PATH):
        return []
    with gzip.open(PATH, "rt") as fh:
        foods = json.load(fh)["foods"]
    for f in foods:
        f["_w"] = set(_words(f["name"]))
    return foods


def search(q: str, limit: int = 8) -> list[dict]:
    want = [w for w in _words(q) if w not in STOP and not w.isdigit()]
    if not want:
        return []
    hits = []
    for f in _load():
        if not all(w in f["_w"] for w in want):
            continue
        name = f["name"].lower()
        head = set(_words(",".join(name.split(",")[:2])))
        score = 10 - 0.6 * name.count(",") - 0.02 * len(name) - 1.0 * len(head - set(want))
        score -= 3 * len((f["_w"] & FORMS) - set(want))
        score += 2 if name.split(",")[0].strip() in (q.lower().strip(), " ".join(want)) else 0
        score += 1.5 if any(p in name for p in PLAIN) else 0
        score -= 5 if any(a in name for a in AVOID) else 0
        score -= 4 if re.search(r"\b[A-Z]{3,}\b", f["name"]) else 0       # brand names are written in capitals
        hits.append((score, f))
    hits.sort(key=lambda x: -x[0])
    return [{"id": f["id"], "name": f["name"], "category": f["cat"], "per_100g": f["n"],
             "portion": {"label": f["portion"][0], "grams": f["portion"][1]} if f.get("portion") else None}
            for _, f in hits[:limit]]


def by_id(fid: int) -> dict | None:
    f = next((x for x in _load() if x["id"] == fid), None)
    return f and {"id": f["id"], "name": f["name"], "category": f["cat"], "per_100g": f["n"],
                  "portion": {"label": f["portion"][0], "grams": f["portion"][1]} if f.get("portion") else None}


def best(chunk: str) -> dict | None:
    key = " ".join(w for w in re.findall(r"[a-z]+", chunk.lower()) if w not in STOP)
    for a, fid in ALIAS.items():
        if fid and re.search(rf"\b{a}\b", key):
            return by_id(fid)
    r = search(chunk, 1)
    return r[0] if r else None


def nutrients_for(food: dict, grams: float) -> dict:
    return {k: round(v * grams / 100, 2) for k, v in food["per_100g"].items()}


def source() -> str:
    return "USDA FoodData Central SR Legacy 2018-04 (public domain)" if _load() else "not installed"
