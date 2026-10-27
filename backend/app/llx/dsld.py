"""Runtime access to the NIH DSLD-derived supplement reference (catalog + market dose-norms).

Grounds the rule-based supplement engine: dose_check() sanity-checks our suggested dose against what
the market actually sells (DSLD, 215k labels, CC0); match() maps a user's product query to real
products + structured ingredients. Degrades gracefully if the assets haven't been built yet.
"""
from __future__ import annotations
import os, json, re, functools

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets", "dsld")
# supplement-rule id -> DSLD ingredient key
RULE_TO_DSLD = {"vit_d": "vitamin_d", "b12": "b12", "iron": "iron", "magnesium": "magnesium",
                "folate_b": "folate", "omega3": "omega3"}

@functools.lru_cache(maxsize=1)
def _load(name):
    try:
        return json.load(open(os.path.join(ASSETS, f"{name}.json")))
    except Exception:
        return {}

def dose_norm(ingredient: str) -> dict | None:
    """Market dose distribution for an ingredient (median / p10 / p90 per unit), from DSLD."""
    return (_load("dose_norms") or {}).get(ingredient)

def dose_check(ingredient: str, dose_text: str) -> dict | None:
    """Compare our recommended dose to the market p10–p90 for the dominant unit. Returns a note."""
    norm = dose_norm(ingredient)
    if not norm or not norm.get("by_unit"):
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(iu|mcg|µg|mg|g)", dose_text, re.I)
    if not m:
        return {"market": norm["by_unit"], "note": "market dose range available (no numeric dose parsed)"}
    val, unit = float(m.group(1)), m.group(2).lower().replace("µg", "mcg")
    # match the unit band (case-insensitive)
    band = next((v for u, v in norm["by_unit"].items() if u.lower().replace("µg", "mcg") == unit), None)
    if not band:
        return {"market": norm["by_unit"], "note": f"our dose in {unit}; market data in other units"}
    within = band["p10"] <= val <= band["p90"]
    where = "within" if within else ("below" if val < band["p10"] else "above")
    return {"our_dose": f"{val} {unit}", "market_p10_p90": [band["p10"], band["p90"], unit],
            "market_median": band["median"], "n_products": band["n"],
            "note": f"our dose is {where} the typical market range (p10–p90 {band['p10']}–{band['p90']} {unit})"}

def match(query: str, k: int = 5) -> list:
    """Find real DSLD products whose brand/name matches the query (for catalog / label matching)."""
    cat = _load("catalog") or {}
    q = query.lower()
    hits = []
    for ing, products in cat.items():
        for p in products:
            name = f"{p.get('brand','')} {p.get('name','')}".lower()
            if any(w in name for w in q.split()):
                hits.append({**p, "ingredient": ing})
    return hits[:k]

def available() -> bool:
    return bool(_load("dose_norms"))

if __name__ == "__main__":
    print("DSLD assets built:", available())
    if available():
        print("vitamin D 2000 IU check:", json.dumps(dose_check("vitamin_d", "2000 IU/day"), indent=2))
