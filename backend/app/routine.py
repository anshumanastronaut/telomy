"""Routines by talking, typing or tapping. A free-text routine becomes a structured weekly schedule; Telomy quantifies it
(cigarettes/day, alcohol g/week, caffeine timing, water, sleep window, protein), explains the evidence in plain words,
feeds the numbers into prediction models (e.g. smoking → PREVENT/PCE) and turns each day into expected logs the person
confirms or corrects — so deviations become events the correlation engine can learn from.
"""
import re
from datetime import date, timedelta

from . import db, engine, food

SCHEMA = """CREATE TABLE IF NOT EXISTS routines (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, text TEXT, items TEXT, metrics TEXT,
  active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS routine_log (day TEXT, item_key TEXT, status TEXT, PRIMARY KEY (day, item_key));"""

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
KINDS = [  # (kind, regex) — order matters
    ("wake", r"\b(wake|waking|woke|get up|uth)\w*"), ("sleep", r"\b(sleep|bed|soja|sona)\b"),
    ("smoke", r"\b(cigar+ett?e?s?|cigrat+es?|cigarette|smoke|sutta|bidi)\b"), ("alcohol", r"\b(vodka|whisk(e)?y|rum|gin|beer|wine|drink(s)? (3|three|\d) time|drinks?\b(?! water))"),
    ("caffeine", r"\b(coffee|tea|chai|espresso)\b"), ("water", r"\b(water|paani)\b"),
    ("supplement", r"\b(glutathione|chia|psyllium|physellium|isabgol|vitamin|omega|magnesium|creatine|supplement)\b"),
    ("commute", r"\b(drive|commute|cab|metro|bus)\b"), ("work", r"\b(office|work)\b"), ("walk", r"\b(walk|walking|steps)\b"),
    ("meal", r"\b(lunch|dinner|breakfast|snack|snacks|eat|eggs?|rice|chicken|pulses|dal|veggies|sweet|chips)\b"),
    ("screen", r"\b(phone|screen|scroll|netflix|tv)\b"),
    ("exercise", r"\b(gym|workout|work out|strength|weights|yoga|run|running|cycling|swim|swimming|sport|cricket|badminton|tennis)\b"),
]


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def _rng(s: str):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to|–)\s*(\d+(?:\.\d+)?)", s)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return (float(m.group(1)), float(m.group(1))) if m else None


def _clock(h: float, ampm: str | None, kind: str, wake: float | None = None) -> str:
    hh = int(h) % 24
    if ampm == "pm" and hh < 12:
        hh += 12
    elif not ampm:
        if kind == "sleep" and hh <= 4:
            pass  # 1–2 means after midnight
        elif kind == "sleep" and hh == 12:
            hh = 0  # "sleep around 12" = midnight
        elif kind == "sleep" and 7 <= hh <= 11:
            hh += 12  # "sleep at 11" = 23:00
        elif kind == "wake":
            pass
        elif kind == "evening" and hh < 12:
            hh += 12  # "dinner at 8" = 20:00
        elif wake is not None and wake <= hh < 12:
            pass  # after an early wake-up, "coffee at 7" is 07:00
        elif 1 <= hh <= 7:
            hh += 12  # "coffee at 4" in a day routine = 16:00
    return f"{hh:02d}:{int(round((h % 1) * 60)):02d}"


def _days(s: str) -> list[str]:
    m = re.search(r"(mon|tue|wed|thu|fri|sat|sun)\w*\s*(?:to|-|till|through)\s*(mon|tue|wed|thu|fri|sat|sun)\w*", s)
    if m:
        a, b = DAYS.index(m.group(1)), DAYS.index(m.group(2))
        return DAYS[a:b + 1] if a <= b else DAYS[a:] + DAYS[:b + 1]
    return DAYS


VOCAB = ["wake", "sleep", "cigarette", "cigarettes", "drink", "drinks", "drinking", "times", "soaked", "psyllium", "otherwise", "routine",
         "around", "glutathione", "coffee", "water", "liters", "litres", "office", "lunch", "dinner", "breakfast", "vodka", "whisky", "snacks",
         "evening", "morning", "between", "walking", "waking", "minutes", "everyday", "monday", "saturday", "sunday", "alternate", "usually", "chicken"]
COMMON = {"after", "takes", "taking", "while", "where", "there", "their", "other", "about", "drive", "total", "black", "every", "usually", "mostly",
          "major", "majorly", "boiled", "some", "night", "overnight", "seeds", "office", "phone", "between", "alternate", "sweet", "chips", "times",
          "start", "later", "early", "late", "dinner", "walk", "light", "white", "green", "plain", "water", "lunch", "drink", "drinks", "wakes"}
FIX = [(r"\bdink\b|\bdring\b", "drink"), (r"\bdinks\b", "drinks"), (r"\bothers?\s*w?\s*ise\b|\bother\s+wise\b", "otherwise"),
       (r"(\d+)\s*times?\s*as?\s*a\s*week", r"\1 times a week"), (r"\b(?!psyllium)\w+ husk\b", "psyllium husk"), (r"\bduring water\b", "drink water"),
       (r"\btimes?\s+as\s+(?=a week)", "times "), (r"\bwave up\b", "wake up"), (r"otherw\s*ise", "otherwise"), (r"(\d+)\s+in\s+drive", r"\1 min drive"), (r"\bl[ -]glutathione", "glutathione"),
       (r"\bphysellium|physillium|psylium\b", "psyllium"), (r"\bpulses\b", "dal"), (r"\bveggies\b", "sabzi"), (r"\bgms?\b", "g"),
       (r"\bi\b", "I")]


def _fix(text: str) -> str:
    import difflib
    t = text.lower().replace("’", "'")
    for a, b in FIX[:-1]:
        t = re.sub(a, b, t)
    out = []
    for w in re.findall(r"[a-z]+|\d+(?:\.\d+)?|[^\sa-z\d]|\s+", t):
        if w.isalpha() and len(w) >= 5 and w not in VOCAB and w not in COMMON:
            m = difflib.get_close_matches(w, VOCAB, n=1, cutoff=0.8)
            out.append(m[0] if m else w)
        else:
            out.append(w)
    return "".join(out)


def _clauses(t: str) -> list[str]:
    raw = [c.strip() for c in re.split(r"[.;\n]|,|\bthen\b|\band (?=(?:i )?(?:sleep|wake|go to bed|get up))", t) if c and c.strip()]
    out = []
    for c in raw:
        if out and re.match(r"(otherwise|or |and \d|a sweet|\d+\s*(g|ml))", c):
            out[-1] += ", " + c  # continuation of the previous clause
        else:
            out.append(c)
    return out


def parse(text: str) -> dict:
    t = _fix(text)
    items, office_days, last = [], None, None
    for c in _clauses(t):
        cond = "when_drinking" if re.search(r"\b(when|while) (i )?(drink|drinking|drinks)", c) else "not_drinking" if re.search(r"while not drinking|other days", c) else None
        days = _days(c)
        if "office" in c and days != DAYS:
            office_days = days
        freq = None
        m = re.search(r"(\d+|once|twice|three|two|four|five)\s*(?:times?|x)?\s*(?:a|per)\s*week", c)
        if m:
            freq = {"once": 1, "twice": 2, "two": 2, "three": 3, "four": 4, "five": 5}.get(m.group(1)) or int(m.group(1))
        tm, win = None, None
        wk = next((x for x in items if x["kind"] == "wake" and x.get("time")), None)
        wake_h = int(wk["time"][:2]) if wk else None
        r = re.search(r"(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s*(am|pm)?", c) if re.search(r"(around|at|by|from)\s+\d", c) or re.search(r"\d\s*(am|pm)", c) else None
        r1 = re.search(r"(?:at|around|by)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", c) or re.search(r"(\d{1,2})\s*(am|pm)\b", c)
        kind_hint = "sleep" if re.search(r"\bsleep\b", c) and not re.search(r"\bwake\b", c) else "wake" if re.search(r"\bwake\b", c) \
            else "evening" if re.search(r"\b(dinner|evening|night)\b", c) else ""
        if r and not re.search(r"\d\s*(?:-|to)\s*\d\s*(eggs|cig|l\b|lit)", c):
            win = [_clock(float(r.group(1)), r.group(3), kind_hint, wake_h), _clock(float(r.group(2)), r.group(3), kind_hint, wake_h)]
            tm = win[0]
        elif r1:
            g = r1.groups()
            tm = _clock(float(g[0]) + (int(g[1]) / 60 if g[1] else 0), g[-1] if g[-1] in ("am", "pm") else None, kind_hint, wake_h)
        anchor = "after waking" if "after wak" in c else "after lunch" if "after lunch" in c else None
        if not tm and "evening" in c:
            tm = "19:00"
        found = []
        for kind, rx in KINDS:
            if kind == "alcohol" and not re.search(r"(vodka|whisk(e)?y|rum|gin|beer|wine|\d+\s*ml|peg)", c):
                continue
            if kind == "alcohol" and re.search(r"\b(water|paani|juice|milk|coconut|lassi|buttermilk|chaas|shake|smoothie)\b", c) \
                    and not re.search(r"(vodka|whisk(e)?y|rum|gin|beer|wine|peg)", c):
                continue  # "drink 500 ml of water" is not alcohol
            if kind == "meal" and found and found[0] in ("alcohol", "smoke"):
                continue
            if re.search(rx, c) and kind not in found:
                found.append(kind)
        if "walk" in found and "meal" in found and re.search(r"\b(at|during|after) (lunch|dinner)", c):
            found.remove("meal")  # "walk 30 minutes at lunch" is a walk, not a meal
        if anchor == "after waking" and "wake" in found and len(found) > 1:
            found.remove("wake")  # "after waking I …" is an anchor, not a wake-up item
        # wake & sleep in one clause ("wake up 8-9, sleep 1-2") are handled by the comma split; one primary kind per clause
        prim = [k for k in found if k in ("wake", "sleep", "smoke", "alcohol", "caffeine", "water", "commute", "supplement", "exercise")]
        kinds = prim[:1] + [k for k in found if k in ("meal", "work", "walk", "screen") and not prim] if prim else found
        if prim and "supplement" in found and prim[0] == "smoke":
            kinds = ["smoke", "supplement"]
        for kind in kinds:
            it = {"kind": kind, "text": c, "days": days, "per_week": freq, "condition": cond}
            if tm:
                it["time"] = tm
            if win:
                it["window"] = win
            if anchor:
                it["anchor"] = anchor
            if not tm and not anchor and last and kind in ("supplement", "smoke", "caffeine") and (last.get("time") or last.get("anchor")):
                it["anchor"] = last.get("anchor") or None
                if not it["anchor"]:
                    it["time"] = last.get("time")
            if kind == "smoke":
                rg = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\s*cig", c)
                one = re.search(r"(\d+)\s*cig", c)
                it["count"] = (int(rg.group(1)) + int(rg.group(2))) / 2 if rg else int(one.group(1)) if one else 1
                o = re.search(r"otherwise\s*(?:only\s*)?(\d+)", c)
                if o:
                    it["condition"] = "when_drinking"
                    items.append({"kind": "smoke", "text": c, "days": DAYS, "per_week": None, "condition": "not_drinking", "count": int(o.group(1)), "time": "21:00"})
                if it["condition"] == "when_drinking":
                    it.setdefault("time", "21:00")
            if kind == "alcohol":
                ml = re.search(r"(\d+)\s*ml", c)
                drink = re.search(r"(vodka|whisk(?:e)?y|rum|gin|beer|wine)", c)
                glass = re.search(r"(\d+|one|two|a)?\s*(glass|glasses|pint|pints|peg|pegs|can|cans)\b", c)
                drink_name = drink.group(1) if drink else "spirits"
                if ml:
                    vol = float(ml.group(1))
                elif glass:
                    n = {"one": 1, "a": 1, "two": 2, None: 1}.get(glass.group(1)) or int(glass.group(1))
                    vol = n * {"wine": 150, "beer": 330}.get(drink_name, 60)
                else:
                    vol = 60.0
                it.update({"ml": vol, "drink": drink_name})
                abv = 0.05 if it["drink"] == "beer" else 0.13 if it["drink"] == "wine" else 0.40
                it["grams_alcohol"] = round(it["ml"] * abv * 0.789, 1)
            if kind == "water":
                w = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)?\s*(\d+(?:\.\d+)?)?\s*(?:l\b|lit|liter|litre)", c)
                prev_w = next((x for x in items if x["kind"] == "water"), None)
                if w and prev_w:
                    prev_w["litres"] = [float(w.group(1)), float(w.group(2) or w.group(1))]
                    continue
                if w:
                    it["litres"] = [float(w.group(1)), float(w.group(2) or w.group(1))]
                elif prev_w:
                    continue
            if kind == "commute":
                m2 = re.search(r"(\d+)\s*(?:min|minute)", c)
                it["minutes"] = int(m2.group(1)) if m2 else None
            if kind == "meal" and not tm and last and last["kind"] == "meal" and last.get("meal") in ("breakfast", "lunch", "dinner", "snack") \
                    and not re.search(r"(while|when|breakfast|dinner|lunch)", c):
                last["text"] += ", " + c  # more foods for the same meal
                if "alternate day" in c:
                    last["note"] = "sweet on alternate days"
                desc = re.sub(r"(lunch|dinner|at \d+|majorly|i take|some|while not drinking|when drinks?|while drinking|an? alternate day)", " ", last["text"])
                last["analysis"] = {k: v for k, v in food.analyze(desc).items() if k in ("kcal", "protein", "carbs", "fat", "fibre", "items")}
                continue
            if kind == "meal":
                it["meal"] = "lunch" if "lunch" in c else "dinner" if "dinner" in c else "breakfast" if "breakfast" in c else "snack" if "snack" in c else "dinner" if cond else "meal"
                if cond and it["meal"] == "dinner":
                    it.setdefault("time", "21:30")
                if "alternate day" in c:
                    it["note"] = "sweet on alternate days"
                desc = re.sub(r"(lunch|dinner|at \d+|majorly|i take|some|while not drinking|when drinks?|while drinking)", " ", c)
                it["analysis"] = {k: v for k, v in food.analyze(desc).items() if k in ("kcal", "protein", "carbs", "fat", "fibre", "items")}
            if kind == "caffeine":
                it["label"] = "Black coffee" if "black" in c else "Green tea" if "green tea" in c else "Chai" if "chai" in c \
                    else "Tea" if re.search(r"\btea\b", c) else "Coffee"
            if kind in ("wake", "sleep") and any(x["kind"] == kind for x in items):
                continue
            items.append(it)
            last = it
            if kind == "caffeine":  # "coffee at 10am and at 5" → two items
                for g in re.findall(r"\band (?:at|around)\s+(\d{1,2})\s*(am|pm)?", c):
                    items.append({**it, "time": _clock(float(g[0]), g[1] or None, "caffeine", wake_h)})
    for it in items:
        if it["kind"] in ("work", "commute") and office_days:
            it["days"] = office_days
        it["label"] = it.get("label") or _label(it)
        it["key"] = re.sub(r"[^a-z0-9]+", "-", f"{it['kind']}-{it.get('time') or it.get('anchor') or ''}-{it.get('condition') or ''}-{it['label']}".lower()).strip("-")
    items = _dedupe(items)
    return {"items": items, "metrics": metrics(items), "text": text, "understood_as": t}


def _label(it):
    k = it["kind"]
    if k == "smoke":
        return f"Cigarette ×{it.get('count', 1):g}" + (" (drinking days)" if it.get("condition") == "when_drinking" else " (other days)" if it.get("condition") == "not_drinking" else "")
    if k == "alcohol":
        return f"{int(it['ml'])} ml {it['drink']}" + (f", {it['per_week']:g}×/week" if it.get("per_week") else "")
    if k == "water":
        return f"Water {it['litres'][0]:g}–{it['litres'][1]:g} L/day" if it.get("litres") else "Water"
    if k == "supplement":
        names = re.findall(r"(glutathione|chia|psyllium|physellium|isabgol|vitamin \w|omega|magnesium|creatine)", it["text"])
        return ", ".join(sorted({n.replace('physellium', 'psyllium').title() for n in names})) or "Supplement"
    if k == "meal":
        return it["meal"].title()
    return {"wake": "Wake up", "sleep": "Sleep", "caffeine": "Coffee", "commute": f"Commute {it.get('minutes') or ''} min".strip(),
            "work": "Office", "walk": "Walking", "exercise": "Workout", "screen": "Phone / screen before bed"}.get(k, k.title())


def _dedupe(items):
    seen, out = set(), []
    for it in items:
        sig = (it["kind"], it.get("time"), it.get("anchor"), it.get("condition"), it.get("meal"))
        if sig in seen:
            continue
        seen.add(sig)
        out.append(it)
    return out


def _hours(a: str, b: str) -> float:
    ha, ma = map(int, a.split(":"))
    hb, mb = map(int, b.split(":"))
    return ((hb * 60 + mb) - (ha * 60 + ma)) % (24 * 60) / 60


def metrics(items: list[dict]) -> dict:
    alc = [i for i in items if i["kind"] == "alcohol"]
    drink_days = sum(i.get("per_week") or 1 for i in alc) if alc else 0
    g_week = round(sum(i["grams_alcohol"] * (i.get("per_week") or 1) for i in alc), 1)
    smoke_reg = sum(i.get("count", 1) for i in items if i["kind"] == "smoke" and i.get("condition") is None)
    smoke_drink = next((i.get("count", 0) for i in items if i["kind"] == "smoke" and i.get("condition") == "when_drinking"), 0)
    smoke_other = next((i.get("count", 0) for i in items if i["kind"] == "smoke" and i.get("condition") == "not_drinking"), 0)
    if smoke_drink or smoke_other:
        evening = (smoke_drink * drink_days + smoke_other * (7 - drink_days)) / 7
    else:
        evening = 0
    cig_day = round(smoke_reg + evening, 1)
    wake = next((i for i in items if i["kind"] == "wake"), {})
    sleep = next((i for i in items if i["kind"] == "sleep"), {})
    mid = lambda w: w.get("window") or [w.get("time"), w.get("time")]  # noqa: E731
    sleep_h = None
    if wake and sleep and mid(sleep)[0] and mid(wake)[0]:
        sleep_h = round((_hours(mid(sleep)[0], mid(wake)[0]) + _hours(mid(sleep)[1], mid(wake)[1])) / 2, 1)
    caff = sorted(i.get("time") for i in items if i["kind"] == "caffeine" and i.get("time"))
    water = next((i["litres"] for i in items if i["kind"] == "water" and i.get("litres")), None)
    protein = sum((i.get("analysis") or {}).get("protein", 0) for i in items if i["kind"] == "meal" and i.get("meal") == "lunch")
    flags = []
    if cig_day:
        flags.append({"topic": "Smoking", "severity": "high",
                      "text": f"≈ {cig_day} cigarettes a day. Smoking is the single largest modifiable risk in your Vault — it roughly doubles cardiovascular risk "
                              f"and Telomy's PREVENT/PCE models now include it. Quitting before 40 avoids ~90 % of the excess mortality (Jha 2013, NEJM).",
                      "evidence": "A"})
    if g_week:
        units = round(g_week / 8, 1)
        flags.append({"topic": "Alcohol", "severity": "high" if g_week > 140 else "moderate",
                      "text": f"{g_week} g alcohol a week (≈ {units} UK units, {round(g_week / 10, 1)} Indian standard drinks) over {drink_days:g} evenings. "
                              f"WHO: no safe level; above ~100 g/week all-cause mortality rises (Wood 2018, Lancet). Telomy measures what drinking nights do to your own HRV.",
                      "evidence": "A"})
    bed = mid(sleep)[0] if sleep else None
    if caff and caff[-1] >= "15:00":
        left = f"about {round(100 * 0.5 ** (_hours(caff[-1], bed) / 5))} % is still active at your {bed} bedtime" if bed else "a good share is still active at bedtime"
        flags.append({"topic": "Caffeine timing", "severity": "low", "text": f"Last caffeine at {caff[-1]}. With a ~5-h half-life {left}; fine for most, worth testing as an N-of-1.",
                      "evidence": "B"})
    if sleep_h:
        flags.append({"topic": "Sleep window", "severity": "low" if sleep_h >= 7 else "moderate",
                      "text": f"≈ {sleep_h} h in bed ({mid(sleep)[0]}–{mid(wake)[1]}). "
                              + ("Late but consistent is OK; " if bed and bed < "05:00" else "Consistency matters as much as duration; ")
                              + ("phone use before bed delays melatonin — cutting screens 30 min before bed is the cheapest lever." if any(i["kind"] == "screen" for i in items)
                                 else "aim for 7–9 h on the same schedule every day, weekends included."), "evidence": "B"})
    if any(i["kind"] == "screen" for i in items):
        pass
    return {"cigarettes_per_day": cig_day, "alcohol_g_week": g_week, "drink_days_per_week": drink_days, "caffeine_times": caff, "water_litres": water,
            "sleep_hours": sleep_h, "lunch_protein_g": round(protein), "flags": flags}


def save(text: str, apply_to_profile: bool = True) -> dict:
    r = parse(text)
    db.exec_("UPDATE routines SET active = 0")
    rid = db.exec_("INSERT INTO routines (created_at, text, items, metrics, active) VALUES (?,?,?,?,1)",
                   (engine.now_iso(), text, db.j(r["items"]), db.j(r["metrics"])))
    changed = []
    if apply_to_profile:
        prof = engine.profile()
        if r["metrics"]["cigarettes_per_day"] and not prof.get("smoker"):
            prof["smoker"] = True
            prof["cigarettes_per_day"] = r["metrics"]["cigarettes_per_day"]
            changed.append("smoker = yes (used by PREVENT and PCE)")
        if r["metrics"]["alcohol_g_week"]:
            prof["alcohol_g_week"] = r["metrics"]["alcohol_g_week"]
            changed.append(f"alcohol {r['metrics']['alcohol_g_week']} g/week")
        db.exec_("UPDATE profile SET data = ? WHERE id = 1", (db.j(prof),))
    return {"id": rid, **r, "profile_changes": changed}


def active() -> dict | None:
    r = db.one("SELECT * FROM routines WHERE active = 1 ORDER BY id DESC")
    if not r:
        return None
    return {"id": r["id"], "text": r["text"], "items": db.unj(r["items"], []), "metrics": db.unj(r["metrics"], {})}


def today(day: str | None = None, drinking: bool | None = None) -> dict:
    r = active()
    d = date.fromisoformat(day or engine.now_iso()[:10])
    if not r:
        return {"day": d.isoformat(), "weekday": DAYS[d.weekday()], "items": [], "metrics": {},
                "message": "No routine yet. Describe your day to Sinc or type it."}
    dow = DAYS[d.weekday()]
    logged = {x["item_key"]: x["status"] for x in db.rows("SELECT * FROM routine_log WHERE day = ?", (d.isoformat(),))}
    out = []
    for it in r["items"]:
        if dow not in it.get("days", DAYS):
            continue
        if it.get("condition") == "when_drinking" and drinking is False:
            continue
        if it.get("condition") == "not_drinking" and drinking is True:
            continue
        out.append({**it, "status": logged.get(it["key"], "expected")})
    return {"day": d.isoformat(), "weekday": dow, "items": sorted(out, key=lambda x: x.get("time") or {"after waking": "07:59", "after lunch": "13:30"}.get(x.get("anchor"), "23:59")),
            "metrics": r["metrics"]}


def confirm(day: str, key: str, status: str) -> dict:
    if status not in ("done", "skipped", "different"):
        raise ValueError("status must be done, skipped or different")
    r = active()
    it = next((x for x in (r or {}).get("items", []) if x["key"] == key), None)
    if not it:
        raise LookupError("Routine item not found")
    db.exec_("INSERT OR REPLACE INTO routine_log (day, item_key, status) VALUES (?,?,?)", (day, key, status))
    if status == "done":
        ts = f"{day}T{it.get('time') or '12:00'}:00"
        kind = {"smoke": "smoke", "alcohol": "alcohol", "caffeine": "caffeine_late" if (it.get("time") or "00") >= "14:00" else "caffeine",
                "supplement": "supplement", "walk": "walk"}.get(it["kind"])
        if kind:
            n = int(round(it.get("count", 1))) if it["kind"] == "smoke" else 1
            for _ in range(n):
                db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)", (ts, kind, it["label"], None, db.j({"via": "routine"})))
    return today(day)
