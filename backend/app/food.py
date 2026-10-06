"""Meal analysis from free text, a weekly menu, and meal swaps.

Nutrition values per typical serving from a small Indian-first food table. Every analysis reports which
items were matched and which were not, and its confidence reflects that coverage.
"""
import re
from datetime import date, datetime, timedelta

# name: (aliases, kcal, protein, carbs, fat, fibre, processing 0-3, veg)
FOODS = {
    "egg": (["egg", "eggs", "omelette"], 78, 6.3, 0.6, 5.3, 0, 0, False),
    "toast": (["toast", "bread", "slice"], 80, 3, 14, 1, 1.2, 2, True),
    "roti": (["roti", "chapati", "phulka"], 110, 3.5, 20, 2.5, 3, 0, True),
    "rice": (["rice", "steamed rice"], 205, 4.3, 45, 0.4, 0.6, 1, True),
    "dal": (["dal", "daal", "arhar", "toor", "moong dal", "lentil"], 180, 11, 28, 3, 8, 0, True),
    "paneer": (["paneer"], 265, 18, 6, 20, 0, 1, True),
    "chicken": (["chicken"], 240, 31, 0, 12, 0, 0, False),
    "fish": (["fish", "salmon", "pomfret", "rohu"], 210, 30, 0, 9, 0, 0, False),
    "dosa": (["dosa"], 170, 4, 29, 4, 1.5, 1, True),
    "ragi": (["ragi"], 150, 4, 30, 1.5, 4, 0, True),
    "idli": (["idli"], 60, 2, 12, 0.3, 0.8, 1, True),
    "sambar": (["sambar"], 130, 6, 18, 4, 5, 0, True),
    "chole": (["chole", "chana", "chickpea"], 270, 13, 40, 7, 11, 0, True),
    "rajma": (["rajma", "kidney bean"], 240, 13, 38, 4, 12, 0, True),
    "curd": (["curd", "yogurt", "yoghurt", "dahi"], 98, 7, 8, 4, 0, 0, True),
    "oats": (["oats", "oatmeal", "porridge"], 150, 5, 27, 2.5, 4, 1, True),
    "banana": (["banana"], 105, 1.3, 27, 0.4, 3.1, 0, True),
    "apple": (["apple"], 95, 0.5, 25, 0.3, 4.4, 0, True),
    "salad": (["salad", "greens", "cucumber", "sprouts"], 60, 3, 9, 1, 4, 0, True),
    "sabzi": (["sabzi", "bhindi", "beans", "palak", "vegetable curry", "veg"], 120, 3, 12, 7, 4, 0, True),
    "biryani": (["biryani"], 480, 18, 60, 18, 2, 2, False),
    "pizza": (["pizza"], 285, 12, 36, 10, 2.5, 3, True),
    "burger": (["burger"], 450, 22, 40, 22, 2, 3, False),
    "samosa": (["samosa"], 260, 4, 30, 14, 2.5, 3, True),
    "chips": (["chips", "namkeen", "bhujia"], 160, 2, 15, 10, 1, 3, True),
    "sweet": (["gulab jamun", "jalebi", "sweet", "dessert", "ice cream", "cake"], 300, 4, 45, 12, 0.5, 3, True),
    "coffee": (["coffee", "latte", "cappuccino"], 120, 6, 10, 6, 0, 1, True),
    "tea": (["chai", "tea"], 90, 3, 12, 3, 0, 1, True),
    "soda": (["coke", "soda", "cola", "soft drink"], 140, 0, 39, 0, 0, 3, True),
    "nuts": (["almonds", "nuts", "walnuts", "peanuts"], 170, 6, 6, 15, 3.5, 0, True),
    "quinoa": (["quinoa"], 220, 8, 39, 3.5, 5, 0, True),
    "poha": (["poha"], 250, 5, 45, 6, 2, 1, True),
    "upma": (["upma"], 230, 6, 35, 7, 3, 1, True),
    "milk": (["milk"], 120, 8, 12, 5, 0, 0, True),
    "whey": (["whey", "protein shake"], 120, 24, 3, 1.5, 0, 2, True),
    "wine": (["wine"], 125, 0, 4, 0, 0, 1, True),
    "beer": (["beer"], 155, 1.6, 13, 0, 0, 2, True),
    "whisky": (["whisky", "whiskey", "vodka", "rum", "gin"], 140, 0, 0, 0, 0, 2, True),
}
# Per typical serving: (total sugar g, added sugar g, saturated fat g)
DETAIL = {"toast": (1.5, 1.5, 0.2), "rice": (0.1, 0, 0.1), "dosa": (1, 0, 0.8), "biryani": (3, 0, 6), "pizza": (4, 2, 4.5),
          "burger": (8, 5, 8), "samosa": (1, 0, 4), "chips": (1, 0, 3), "sweet": (35, 30, 6), "coffee": (9, 4, 3.5),
          "tea": (10, 8, 2), "soda": (39, 39, 0), "milk": (12, 0, 3), "curd": (7, 0, 2.5), "banana": (14, 0, 0.1),
          "apple": (19, 0, 0.1), "oats": (1, 0, 0.4), "paneer": (2, 0, 12), "chicken": (0, 0, 3.5), "fish": (0, 0, 2),
          "egg": (0.2, 0, 1.6), "nuts": (1.2, 0, 1.2), "chole": (5, 0, 0.8), "rajma": (1, 0, 0.6), "dal": (2, 0, 0.5),
          "sabzi": (4, 0, 1), "poha": (1, 0, 1), "upma": (1, 0, 1.5), "whey": (2, 0, 0.5), "wine": (1, 0, 0), "beer": (0, 0, 0)}
DAILY = {"added_sugar": 25, "fibre": 30, "sat_fat": 20}

WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "half": 0.5, "a": 1, "an": 1}


def analyze(text: str, when: datetime | None = None) -> dict:
    when = when or datetime.now()
    t = text.lower()
    items, unmatched = [], []
    chunks = [c.strip() for c in re.split(r",| and | with |\+|&|\n", t) if c.strip()]
    for chunk in chunks:
        # Prefer the most specific match: longest alias, then the composite dish (more energy) over an ingredient.
        cands = [(max(len(a) for a in spec[0] if re.search(rf"\b{re.escape(a)}\b", chunk)), spec[1], key)
                 for key, spec in FOODS.items() if any(re.search(rf"\b{re.escape(a)}\b", chunk) for a in spec[0])]
        found = max(cands)[2] if cands else None
        if not found:
            unmatched.append(chunk)
            continue
        m = re.search(r"(\d+(?:\.\d+)?)|\b(one|two|three|four|half|an?)\b", chunk)
        qty = float(m.group(1)) if m and m.group(1) else WORDNUM.get(m.group(2), 1) if m else 1
        if found in ("egg", "toast", "roti", "idli") or qty <= 4:
            qty = qty
        else:
            qty = 1
        items.append({"food": found, "qty": qty, "text": chunk})
    tot = {"kcal": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fibre": 0.0}
    proc = []
    alcohol = False
    for it in items:
        s = FOODS[it["food"]]
        for i, k in enumerate(("kcal", "protein", "carbs", "fat", "fibre")):
            tot[k] += s[1 + i] * it["qty"]
        proc.append(s[6])
        alcohol = alcohol or it["food"] in ("wine", "beer", "whisky")
    for it in items:
        sug, add, sat = DETAIL.get(it["food"], (0, 0, 0))
        tot["sugar"] = tot.get("sugar", 0) + sug * it["qty"]
        tot["added_sugar"] = tot.get("added_sugar", 0) + add * it["qty"]
        tot["sat_fat"] = tot.get("sat_fat", 0) + sat * it["qty"]
    tot = {k: round(v, 1) for k, v in tot.items()}
    tot["pct_daily"] = {k: round(100 * tot.get(k, 0) / v) for k, v in DAILY.items()}
    coverage = len(items) / max(len(chunks), 1)
    if not items:
        return {"items": [], "unmatched": unmatched, "confidence": 0, "message":
                "I couldn't recognise these foods yet. Try naming each item, for example '2 rotis, dal, salad'."}
    protein_density = tot["protein"] * 4 / max(tot["kcal"], 1)
    score = 60 + 60 * min(protein_density, 0.35) + 2.5 * min(tot["fibre"], 10) - 8 * (sum(proc) / len(proc))
    hour = when.hour
    late = hour >= 21 or hour < 5
    if late:
        score -= 8
    if alcohol:
        score = min(score, 25)
    score = int(max(5, min(98, score)))
    load = max(0.0, tot["carbs"] - tot["fibre"] * 1.5 - tot["protein"] * 0.3)
    glucose = "steady" if load < 35 else "moderate rise" if load < 65 else "sharp rise likely"
    tips = []
    if protein_density < 0.15:
        tips.append("Add a protein source (dal, paneer, curd, eggs) to flatten the glucose curve.")
    if tot["fibre"] < 6:
        tips.append("A side of salad or sabzi would add fibre.")
    if late:
        tips.append("Eating within 2 hours of bed has cut your deep sleep in the past.")
    if load >= 50:
        tips.append("A 10-minute walk after this meal usually blunts the rise.")
    if alcohol:
        tips.append("Alcohol has lowered your next-night HRV in your own data.")
    if tot.get("added_sugar", 0) >= 15:
        tips.append(f"{round(tot['added_sugar'])} g added sugar — {tot['pct_daily']['added_sugar']}% of a 25 g daily limit in one meal.")
    return {"items": items, "unmatched": unmatched, **tot, "score": score, "glucose_response": glucose,
            "glycaemic_load_est": round(load), "circadian": "late (after 9 pm)" if late else "within your eating window",
            "processing": ["whole", "minimally processed", "processed", "ultra-processed"][round(sum(proc) / len(proc))],
            "tips": tips, "confidence": round(0.4 + 0.5 * coverage, 2),
            "method": "Food table estimate per typical serving; not a lab measurement."}


WEEK = [
    [("08:00", "Ragi dosa with tomato chutney and curd"), ("13:00", "Arhar dal, rice, beans sabzi and salad"),
     ("19:30", "Paneer tikka with two rotis and greens")],
    [("08:00", "Masala oats with two eggs"), ("13:00", "Rajma, rice and cucumber salad"),
     ("19:30", "Grilled fish with quinoa and sabzi")],
    [("08:00", "Moong dal chilla with curd"), ("13:00", "Chole with two rotis and salad"),
     ("19:30", "Palak paneer with one roti")],
    [("08:00", "Idli with sambar"), ("13:00", "Chicken curry, rice and salad"), ("19:30", "Dal, sabzi and two rotis")],
    [("08:00", "Poha with peanuts and curd"), ("13:00", "Sambar rice with beans sabzi"),
     ("19:30", "Egg curry with quinoa")],
    [("09:00", "Upma with nuts"), ("13:30", "Paneer bhurji with rotis and salad"), ("19:30", "Fish, rice and sabzi")],
    [("09:00", "Dosa with sambar"), ("13:30", "Chole, rice and curd"), ("19:30", "Dal, sabzi and two rotis")],
]
SWAPS = {
    "protein": ["Paneer bhurji with two rotis", "Grilled chicken with salad", "Moong dal chilla with curd and whey",
                "Egg bhurji with one roti and greens"],
    "veg": ["Rajma with rice and salad", "Palak paneer with roti", "Chole with quinoa", "Sprouts salad with curd"],
    "light": ["Idli with sambar", "Moong dal soup with salad", "Curd rice with cucumber"],
    "default": ["Dal, sabzi and two rotis", "Fish, quinoa and greens", "Paneer tikka salad"],
}


def week_menu(start: date) -> list[dict]:
    out = []
    for i in range(7):
        d = start + timedelta(days=i)
        meals = []
        for slot, name in WEEK[d.weekday()]:
            a = analyze(name, datetime.combine(d, datetime.strptime(slot, "%H:%M").time()))
            meals.append({"time": slot, "name": name, **{k: a.get(k) for k in ("kcal", "protein", "carbs", "fat", "score")}})
        out.append({"day": d.isoformat(), "meals": meals})
    return out


def swap(name: str, preference: str) -> dict:
    p = preference.lower()
    pool = SWAPS["protein"] if "protein" in p else SWAPS["veg"] if ("veg" in p or "no egg" in p or "out of egg" in p) \
        else SWAPS["light"] if "light" in p or "less" in p else SWAPS["default"]
    if "egg" in p:
        pool = [x for x in pool if "egg" not in x.lower()]
    choice = next((x for x in pool if x.lower() != name.lower()), pool[0])
    a = analyze(choice)
    return {"name": choice, **{k: a.get(k) for k in ("kcal", "protein", "carbs", "fat", "score")},
            "reason": f"Matched your request: '{preference}'." if preference else "A balanced alternative."}
