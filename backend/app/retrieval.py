"""Telomy RAG — one searchable index over everything Telomy knows about the person, plus a synthesis that connects
domains into insight rather than answering one marker at a time.

Why not just dump a context pack: a fixed dump either misses what the question is about or drowns the model in facts it
doesn't need. Here every data source becomes a small "card" (one lab marker, one 30-day signal, one engine finding, one
tracker, the nutrition targets, a twin projection, the WHOOP day, a CGM summary, a memory). A question retrieves the
cards that matter for it (BM25 over the cards + always-keep the flagged/critical ones); Sinc then grounds on those.

The synthesis (`connect`) is the "insights not answers" part: it links a lab finding to the live wearable trend, the
tracker, the nutrition lever and the genetics that bear on it, so the person sees one connected story with its evidence —
e.g. ApoB ↔ LDL particles ↔ saturated-fat target ↔ APOE ε4 ↔ CT plaque. Dependency-free and deterministic.
"""
import math
import re
from collections import Counter
from datetime import date, datetime

from . import db, engine
from .catalog import MARKERS

_STOP = set("""the a an and or of to in on for with is are was were be been being this that these those my your you it its
as at by from into than then there their them they not but can could should would will more most less low high very
over under about above below within without i me we our value values level result results test tests""".split())


def _tok(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in _STOP and len(w) > 1]


# ---- cards: every data source → one small searchable unit --------------------------------------------------------

def cards() -> list[dict]:
    out: list[dict] = []

    def add(cid, kind, title, text, when=None, critical=False, terms=""):
        out.append({"id": cid, "kind": kind, "title": title, "text": text, "when": when, "critical": critical,
                    "_t": _tok(f"{title} {text} {terms}")})

    latest = engine.latest_values()
    for k, r in latest.items():
        spec = MARKERS.get(k)
        if not spec:
            continue
        val = r["value_num"] if r["value_num"] is not None else r["value_text"]
        flag = r.get("status") in ("out_of_range", "variant", "detected")
        trend = engine.marker_trend(k)
        tx = f"{spec[0]}: {val} {r['unit'] or ''} on {r['collected_on']}".rstrip()
        if r.get("ref_text"):
            tx += f" (lab range {r['ref_text']})"
        if flag:
            tx += " — outside the optimal range" if r["status"] == "out_of_range" else f" — {r['status']}"
        if trend and trend.get("direction") and trend["direction"] != "flat":
            tx += f"; trend {trend['direction']}"
        add(f"lab:{k}", "lab", spec[0], tx, when=r["collected_on"], critical=flag, terms=" ".join(spec[6] if isinstance(spec[6], list) else []))

    for m, spec in engine.SIGNALS.items():
        b = engine.signal_baseline(m, days=30)
        if b:
            add(f"sig:{m}", "signal", spec[0], f"{spec[0]}: 30-day mean {round(b['mean'], spec[3]) if spec[3] else round(b['mean'])} {spec[1]} over {b['n']} days".replace("  ", " "),
                when=engine.last_signal_day())

    for i in engine.list_insights():
        add(f"ins:{i['id']}", "insight", i["title"], f"{i['title']}: {re.sub(r'\\s+', ' ', i['body'] or '')[:400]} (confidence {int(i['confidence'] * 100)}%)",
            critical=bool(i.get("medical")), terms=i.get("kind", ""))

    try:
        from . import trackers
        for t in trackers.all_trackers(active_only=True):
            b = t.get("baseline", {})
            add(f"trk:{t['id']}", "tracker", t["name"], f"Tracker {t['name']} ({t['kind']}): {t['entries']} entries. {b.get('text', '')}", when=None)
    except Exception:  # noqa: BLE001
        pass

    try:
        from . import nutrition
        p = engine.profile()
        nt = nutrition.targets(p.get("goal") if p.get("goal") in ("maintain", "lose") else "maintain")
        if nt.get("ok"):
            add("nut:targets", "nutrition", "Daily nutrition targets",
                f"Targets: {nt['kcal']} kcal, protein {nt['protein_g']} g, fibre {nt['fibre_g']} g, carbs {nt['carbs_g']} g, fat {nt['fat_g']} g (goal {nt['goal']})")
            for n in nt.get("labs", [])[:6]:
                add(f"nut:{n['marker']}", "nutrition", f"Food note — {n['marker']}", n["text"], terms=n["marker"])
    except Exception:  # noqa: BLE001
        pass

    try:
        from . import whoop_day
        d = whoop_day.day()
        if d.get("ok"):
            add("whoop:day", "wearable", "Today's WHOOP day",
                f"WHOOP today: strain {d['strain']}, resting heart rate {d['restingHr']} bpm, {len(d['workouts'])} workouts")
    except Exception:  # noqa: BLE001
        pass

    try:
        from . import cgm
        c = cgm.summary(14)
        if c.get("ok"):
            add("cgm:summary", "wearable", "Glucose (CGM) 14-day",
                f"CGM 14 days: mean {c['mean']} mg/dL, GMI {c['gmi']}%, time in range {c['tir']}%, variability {c['cv']}%")
    except Exception:  # noqa: BLE001
        pass

    for m in db.rows("SELECT fact FROM memories ORDER BY ts DESC LIMIT 10"):
        add(f"mem:{hash(m['fact']) & 0xffff}", "memory", "You told me", m["fact"], terms="preference remember")

    try:
        from . import cellular
        for c in cellular.cards():
            add(c["id"], "cellular", c["title"], c["text"], terms="cell cellular mechanism pathway mitochondria")
    except Exception:  # noqa: BLE001
        pass

    la = engine.longevity_age()
    if la.get("value") is not None:
        add("age:bio", "biomarker", "Biological age",
            f"Blood age (PhenoAge) {la['value']} vs chronological {la['chronological']} ({la['delta']:+} years), as of {la.get('as_of')}", critical=False)
    return out


# ---- retrieval: BM25 over the cards, always keeping the flagged ones ----------------------------------------------

def retrieve(query: str, k: int = 18) -> list[dict]:
    cs = cards()
    q = _tok(query)
    if not q:
        return sorted(cs, key=lambda c: (not c["critical"], c["id"]))[:k]
    N = len(cs)
    df = Counter()
    for c in cs:
        for w in set(c["_t"]):
            df[w] += 1
    scored = []
    for c in cs:
        tf = Counter(c["_t"])
        dl = max(1, len(c["_t"]))
        s = 0.0
        for w in q:
            if w not in tf:
                continue
            idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * (tf[w] * 2.5) / (tf[w] + 1.5 * (0.25 + 0.75 * dl / 20))
        scored.append((s, c))
    hits = [c for s, c in sorted(scored, key=lambda x: -x[0]) if s > 0][:k]
    # always keep flagged/critical cards so a safety-relevant value is never retrieved out
    for c in cs:
        if c["critical"] and c not in hits:
            hits.append(c)
    return hits[: k + 6]


def context(query: str = "", k: int = 18) -> str:
    today = engine.last_signal_day() or datetime.now().date().isoformat()
    p = engine.profile()
    age = engine.age_on()
    head = [f"Today: {today}", "Person: " + ", ".join(x for x in [p.get("sex"), f"{age:.0f} years" if age else None,
            f"{p['height_cm']:.0f} cm" if p.get("height_cm") else None, f"goal: {p['goal']}" if p.get("goal") else None] if x)]
    return "\n".join(head + [c["text"] for c in retrieve(query, k)])


# ---- synthesis: connect domains into one story (insights, not answers) -------------------------------------------

# Which live signals / food levers / genes bear on each engine finding, by the words in its title/body.
_LINKS = {
    r"apob|ldl|cholesterol|plaque|lipid|statin": {"signals": [], "labs": ["apob", "ldl", "lpa", "hdl", "chol_total"],
        "food": "saturated fat and refined carbs", "genes": ["apoe"], "why": "cardiovascular"},
    r"glucose|insulin|hba1c|homa|metabolic|diabet": {"signals": ["glucose_mean", "steps", "exercise_min"], "labs": ["hba1c", "glucose", "homa_ir", "insulin", "triglycerides"],
        "food": "refined carbohydrate load and meal timing", "genes": ["tcf7l2", "fto"], "why": "metabolic"},
    r"liver|alt|ggt|fatty|steato|fib": {"signals": ["weight", "exercise_min"], "labs": ["alt", "ast", "ggt", "triglycerides"],
        "food": "alcohol, fructose and energy surplus", "genes": [], "why": "liver"},
    r"sleep|apnoea|apnea|ahi|hrv|recovery": {"signals": ["sleep_score", "deep_sleep", "rem_sleep", "hrv", "rhr", "spo2"], "labs": [],
        "food": "late meals, alcohol and caffeine", "genes": [], "why": "sleep & recovery"},
    r"inflamm|crp|il-6|il6": {"signals": ["hrv", "skin_temp"], "labs": ["hscrp", "crp"], "food": "omega-3 vs processed foods", "genes": [], "why": "inflammation"},
    r"vitamin d|homocyst|b12|folate|mthfr": {"signals": ["daylight_min"], "labs": ["vitd", "homocysteine", "b12", "folate"],
        "food": "sunlight, B-vitamin and omega-3 intake", "genes": ["mthfr_c677t", "fut2"], "why": "nutrient status"},
}


def connect(max_threads: int = 4) -> dict:
    """The connected story: each engine finding, enriched with the person's live signals, trackers and food levers that
    bear on it, so related things are shown together with their evidence — not one answer at a time."""
    L = engine.latest_values()
    insights = engine.list_insights()
    threads = []
    seen = set()
    for i in insights:
        title = (i["title"] or "").lower()
        link = next((v for pat, v in _LINKS.items() if re.search(rf"\b({pat})\b", title)), None)
        if not link or link["why"] in seen:
            continue
        # only theme a finding when the theme's own markers are actually in this person's data — no forcing a label
        present = [m for m in link["labs"] if m in L and L[m]["value_num"] is not None]
        if not present and not any(engine.signal_baseline(m, days=30) for m in link["signals"]):
            continue
        seen.add(link["why"])
        bits = []
        for m in link["signals"]:
            b = engine.signal_baseline(m, days=30)
            if b and m in engine.SIGNALS:
                sp = engine.SIGNALS[m]
                bits.append(f"{sp[0].lower()} {round(b['mean'], sp[3]) if sp[3] else round(b['mean'])} {sp[1]}".strip())
        labs = [f"{MARKERS[m][0]} {L[m]['value_num']}" for m in link["labs"] if m in L and L[m]["value_num"] is not None][:4]
        genes = [f"{MARKERS[g][0]} {L[g]['value_text']}" for g in link["genes"] if g in L and L[g].get("value_text")]
        threads.append({
            "theme": link["why"], "headline": i["title"], "confidence": i["confidence"], "insight_id": i["id"],
            "labs": labs, "live_signals": bits, "genetics": genes, "food_lever": link["food"],
            "story": (f"{i['title']}. " + (f"Bloods: {', '.join(labs)}. " if labs else "")
                      + (f"Your last 30 days: {', '.join(bits)}. " if bits else "")
                      + (f"Background: {', '.join(genes)}. " if genes else "")
                      + f"The lever you control most here is {link['food']}. This connects your labs, wearables"
                      + (" and genetics" if genes else "") + " — a pattern in your data, reviewed with your clinician for anything medical."),
        })
        if len(threads) >= max_threads:
            break
    return {"threads": threads, "as_of": engine.last_signal_day(),
            "note": "Sinc connects your labs, wearables, trackers and genetics. Patterns in your own data, not medical advice."}
