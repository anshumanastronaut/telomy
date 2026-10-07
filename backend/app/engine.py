"""Telomy intelligence engine.

Everything here is deterministic and auditable: each output carries the inputs it used, the inputs that
were missing, a confidence in [0, 1] and a method/version string ("receipts").
"""
import hashlib
import math
import re
from datetime import date, datetime, timedelta
from statistics import mean, pstdev

from . import db
from .catalog import MARKERS, PANELS, RISK_GENOTYPES

ENGINE_VERSION = "telomy-engine 0.2.0"

SIGNALS = {
    # id: (label, unit, better, decimals)
    "hrv": ("HRV (RMSSD)", "ms", "high", 0),
    "rhr": ("Resting heart rate", "bpm", "low", 0),
    "sleep_hours": ("Sleep duration", "h", "mid", 1),
    "deep_sleep": ("Deep sleep", "h", "high", 1),
    "rem_sleep": ("REM sleep", "h", "high", 1),
    "sleep_score": ("Sleep score", "", "high", 0),
    "steps": ("Steps", "steps", "high", 0),
    "active_kcal": ("Active energy", "kcal", "high", 0),
    "exercise_min": ("Exercise", "min", "high", 0),
    "spo2": ("Blood oxygen (night)", "%", "high", 0),
    "resp_rate": ("Respiratory rate", "rpm", "mid", 1),
    "skin_temp": ("Skin temperature deviation", "°C", "mid", 2),
    "vo2max": ("VO2 max", "mL/kg/min", "high", 1),
    "weight": ("Weight", "kg", "mid", 1),
    "sbp": ("Systolic blood pressure", "mmHg", "low", 0),
    "dbp": ("Diastolic blood pressure", "mmHg", "low", 0),
    "glucose_mean": ("Glucose (CGM mean)", "mg/dL", "low", 0),
    "daylight_min": ("Time in daylight", "min", "high", 0),
    "mindful_min": ("Mindful minutes", "min", "high", 0),
}

EVENT_KINDS = {
    "alcohol": "Alcohol", "late_meal": "Late meal (<2h before bed)", "sauna": "Sauna", "hbot": "Halo session",
    "travel": "Travel", "supplement": "Supplement", "medication": "Medication", "symptom": "Symptom",
    "mood": "Mood", "workout_hard": "Hard workout", "stress": "Stressful day", "caffeine_late": "Caffeine after 2 pm",
    "life": "Life event", "meal": "Meal", "note": "Note",
}

# ---------------------------------------------------------------- data access

def profile() -> dict:
    p = db.one("SELECT data FROM profile WHERE id = 1")
    return db.unj(p["data"], {}) if p else {}


def age_on(day: str | None = None) -> float | None:
    dob = profile().get("dob")
    if not dob:
        return None
    d = date.fromisoformat(day) if day else date.today()
    return (d - date.fromisoformat(dob)).days / 365.25


def marker_history(marker_id: str) -> list[dict]:
    return db.rows("""SELECT r.*, rep.collected_on, rep.title AS report_title, rep.id AS report_id, rep.source,
                      rep.is_test_data FROM results r JOIN reports rep ON rep.id = r.report_id
                      WHERE r.marker_id = ? ORDER BY rep.collected_on""", (marker_id,))


def latest_values(as_of: str | None = None) -> dict[str, dict]:
    out = {}
    for r in db.rows("""SELECT r.*, rep.collected_on, rep.panel, rep.title AS report_title FROM results r
                        JOIN reports rep ON rep.id = r.report_id WHERE (? IS NULL OR rep.collected_on <= ?)
                        ORDER BY rep.collected_on""", (as_of, as_of)):
        out[r["marker_id"]] = r
    return out


def series(metric: str, start: str | None = None, end: str | None = None) -> list[tuple[str, float]]:
    sql, args = "SELECT day, value FROM signals WHERE metric = ?", [metric]
    if start:
        sql += " AND day >= ?"
        args.append(start)
    if end:
        sql += " AND day <= ?"
        args.append(end)
    return [(r["day"], r["value"]) for r in db.rows(sql + " ORDER BY day", args)]


def last_signal_day() -> str | None:
    r = db.one("SELECT MAX(day) AS d FROM signals")
    return r["d"] if r else None


def now_iso() -> str:
    """App clock: the Vault's current day with the wall-clock time, so timestamps never run ahead of the data."""
    day = last_signal_day() or date.today().isoformat()
    return f"{day}T{datetime.now().strftime('%H:%M:%S')}"

# ---------------------------------------------------------------- confidence

def confidence(n: int, days_old: float | None = None, quality: float = 1.0, n_full: int = 30) -> float:
    """Evidence-count saturation × freshness decay × source quality."""
    c = 1 - math.exp(-3 * n / max(n_full, 1))
    if days_old is not None:
        c *= math.exp(-max(days_old, 0) / 365)
    return round(max(0.0, min(1.0, c * quality)), 2)


def conf_label(c: float) -> str:
    return "strong" if c >= 0.75 else "moderate" if c >= 0.5 else "emerging" if c >= 0.25 else "weak"

# ---------------------------------------------------------------- marker scoring

def marker_score(marker_id: str, value) -> float | None:
    """0–100: 100 inside the optimal band, decaying with distance outside it."""
    spec = MARKERS.get(marker_id)
    if not spec or not isinstance(value, (int, float)):
        return None
    lo, hi, better = spec[3], spec[4], spec[5]
    if lo is None or hi is None:
        return None
    if lo <= value <= hi:
        return 100.0
    width = max(hi - lo, abs(hi) * 0.1, 1e-6)
    dist = (lo - value) if value < lo else (value - hi)
    if better == "low" and value < lo:
        return 95.0
    if better == "high" and value > hi:
        return 100.0
    return round(max(0.0, 100 - 60 * dist / width), 1)

# ---------------------------------------------------------------- PhenoAge

def phenoage(values: dict[str, float], chrono_age: float) -> dict:
    """Levine et al. 2018 phenotypic age from 9 blood markers + age."""
    need = ["albumin", "creatinine", "glucose", "hscrp", "lymph_pct", "mcv", "rdw", "alp", "wbc"]
    missing = [m for m in need if m not in values]
    if missing:
        return {"value": None, "missing": missing, "inputs": {k: values.get(k) for k in need}}
    crp_mgdl = max(values["hscrp"], 0.01) / 10
    xb = (-19.907 - 0.0336 * values["albumin"] * 10 + 0.0095 * values["creatinine"] * 88.4
          + 0.1953 * values["glucose"] / 18.016 + 0.0954 * math.log(crp_mgdl) - 0.0120 * values["lymph_pct"]
          + 0.0268 * values["mcv"] + 0.3306 * values["rdw"] + 0.00188 * values["alp"] + 0.0554 * values["wbc"]
          + 0.0804 * chrono_age)
    gamma = 0.0076927
    m = 1 - math.exp(-math.exp(xb) * (math.exp(120 * gamma) - 1) / gamma)
    pheno = 141.50225 + math.log(-0.00553 * math.log(1 - m)) / 0.090165
    return {"value": round(pheno, 1), "missing": [], "inputs": {k: values[k] for k in need},
            "mortality_10y": round(m, 4)}


def longevity_age(as_of: str | None = None) -> dict:
    """Dial value. Default PhenoAge from the most recent blood panel; lab epigenetic clocks shown alongside."""
    reports = db.rows("SELECT * FROM reports WHERE panel = 'blood' AND (? IS NULL OR collected_on <= ?) "
                      "ORDER BY collected_on", (as_of, as_of))
    history = []
    for rep in reports:
        vals = {r["marker_id"]: r["value_num"] for r in db.rows("SELECT * FROM results WHERE report_id = ?", (rep["id"],))
                if r["value_num"] is not None}
        age = age_on(rep["collected_on"])
        if age is None:
            continue
        pa = phenoage(vals, age)
        if pa["value"] is not None:
            history.append({"day": rep["collected_on"], "phenoage": pa["value"], "chrono": round(age, 1),
                            "report_id": rep["id"], "inputs": pa["inputs"]})
    clocks = {}
    for mid in ("phenoage_lab", "grimage", "horvath", "dunedinpace", "telomere"):
        h = [r for r in marker_history(mid) if not as_of or r["collected_on"] <= as_of]
        if h:
            clocks[mid] = {"name": MARKERS[mid][0], "value": h[-1]["value_num"], "unit": MARKERS[mid][2],
                           "day": h[-1]["collected_on"]}
    chrono = age_on(as_of)
    if not history:
        return {"value": None, "chronological": round(chrono, 1) if chrono else None, "clocks": clocks,
                "confidence": 0, "reason": "Needs a blood panel with albumin, creatinine, glucose, hs-CRP, "
                "lymphocytes, MCV, RDW, ALP and WBC.", "history": []}
    last = history[-1]
    days_old = (date.fromisoformat(as_of or date.today().isoformat()) - date.fromisoformat(last["day"])).days
    corroborating = sum(1 for k in ("phenoage_lab", "grimage") if k in clocks)
    conf = confidence(len(history) * 10 + corroborating * 10, days_old, 0.9)
    contributions = _pheno_contributions(last["inputs"])
    return {
        "value": last["phenoage"], "chronological": round(chrono, 1), "delta": round(last["phenoage"] - last["chrono"], 1),
        "as_of": last["day"], "method": "PhenoAge (Levine 2018) from 9 blood markers", "confidence": conf,
        "pace": clocks.get("dunedinpace", {}).get("value"), "clocks": clocks, "history": history,
        "contributors": contributions, "version": ENGINE_VERSION,
    }


def _pheno_contributions(inputs: dict) -> list[dict]:
    """Which markers push PhenoAge up/down vs an optimal reference person."""
    ref = {"albumin": 4.6, "creatinine": 0.9, "glucose": 82, "hscrp": 0.5, "lymph_pct": 32, "mcv": 88,
           "rdw": 12.3, "alp": 60, "wbc": 5.5}
    coef = {"albumin": -0.0336 * 10, "creatinine": 0.0095 * 88.4, "glucose": 0.1953 / 18.016, "lymph_pct": -0.0120,
            "mcv": 0.0268, "rdw": 0.3306, "alp": 0.00188, "wbc": 0.0554}
    out = []
    for k, v in inputs.items():
        if k == "hscrp":
            d = 0.0954 * (math.log(max(v, .01) / 10) - math.log(ref[k] / 10))
        else:
            d = coef[k] * (v - ref[k])
        out.append({"marker_id": k, "name": MARKERS[k][0], "value": v, "years": round(d / 0.0804, 1)})
    return sorted(out, key=lambda x: -abs(x["years"]))

# ---------------------------------------------------------------- trends

def marker_trend(marker_id: str) -> dict | None:
    h = [r for r in marker_history(marker_id) if r["value_num"] is not None]
    if len(h) < 2:
        return None
    a, b = h[-2], h[-1]
    delta = b["value_num"] - a["value_num"]
    pct = delta / a["value_num"] * 100 if a["value_num"] else None
    better = MARKERS[marker_id][5]
    lo, hi = MARKERS[marker_id][3], MARKERS[marker_id][4]
    if better == "low":
        direction = "better" if delta < 0 else "worse" if delta > 0 else "same"
    elif better == "high":
        direction = "better" if delta > 0 else "worse" if delta < 0 else "same"
    else:
        mid = (lo + hi) / 2 if lo is not None and hi is not None else None
        direction = "same" if mid is None else ("better" if abs(b["value_num"] - mid) < abs(a["value_num"] - mid) else "worse")
    return {"from": a["value_num"], "to": b["value_num"], "from_day": a["collected_on"], "to_day": b["collected_on"],
            "delta": round(delta, 2), "pct": round(pct, 1) if pct is not None else None, "direction": direction}


def signal_baseline(metric: str, end: str | None = None, days: int = 30) -> dict | None:
    end = end or last_signal_day()
    if not end:
        return None
    start = (date.fromisoformat(end) - timedelta(days=days)).isoformat()
    vals = [v for _, v in series(metric, start, end)]
    if len(vals) < 5:
        return None
    return {"mean": round(mean(vals), 2), "sd": round(pstdev(vals), 2), "n": len(vals), "start": start, "end": end}

# ---------------------------------------------------------------- domain scores

DOMAINS = {
    "cardiovascular": {
        "title": "Cardiovascular",
        "pillars": [
            ("Autonomic balance", 0.30, {"signals": ["hrv", "rhr"]}),
            ("Atherogenic lipids", 0.30, {"markers": ["apob", "ldl", "lpa", "hdl", "tg"]}),
            ("Vascular inflammation", 0.20, {"markers": ["hscrp", "homocysteine"]}),
            ("Cardiorespiratory fitness", 0.20, {"signals": ["vo2max"]}),
        ]},
    "metabolic": {
        "title": "Metabolic",
        "pillars": [
            ("Glycaemic control", 0.40, {"markers": ["hba1c", "glucose", "homa_ir", "insulin"]}),
            ("Liver & lipids", 0.25, {"markers": ["alt", "ggt", "tg"]}),
            ("Movement", 0.20, {"signals": ["steps", "exercise_min"]}),
            ("Uric acid", 0.15, {"markers": ["uric_acid"]}),
        ]},
    "recovery": {
        "title": "Recovery",
        "pillars": [
            ("Sleep", 0.40, {"signals": ["sleep_hours", "deep_sleep", "sleep_score"]}),
            ("HRV vs baseline", 0.35, {"signals": ["hrv"]}),
            ("Resting heart rate", 0.25, {"signals": ["rhr"]}),
        ]},
    "inflammation": {
        "title": "Inflammation & gut",
        "pillars": [
            ("Systemic", 0.45, {"markers": ["hscrp", "homocysteine", "inflam_clock"]}),
            ("Gut barrier", 0.30, {"markers": ["calprotectin", "zonulin", "butyrate", "shannon"]}),
            ("Toxic load", 0.25, {"markers": ["mercury", "lead", "bpa", "mep", "aflatoxin"]}),
        ]},
}

SIGNAL_TARGET = {"hrv": (55, 90), "rhr": (48, 60), "sleep_hours": (7, 8.5), "deep_sleep": (1.2, 2.2),
                 "sleep_score": (80, 100), "steps": (8000, 15000), "exercise_min": (30, 90), "vo2max": (45, 60)}


def _signal_score(metric: str, value: float) -> float:
    lo, hi = SIGNAL_TARGET[metric]
    better = SIGNALS[metric][2]
    if lo <= value <= hi or (better == "high" and value > hi) or (better == "low" and value < lo):
        return 100.0
    width = hi - lo
    dist = lo - value if value < lo else value - hi
    return round(max(0.0, 100 - 70 * dist / width), 1)


def domain_score(key: str, as_of: str | None = None) -> dict:
    spec = DOMAINS[key]
    latest = {}
    for r in db.rows("""SELECT r.marker_id, r.value_num, rep.collected_on FROM results r JOIN reports rep
                        ON rep.id = r.report_id WHERE (? IS NULL OR rep.collected_on <= ?) ORDER BY rep.collected_on""",
                     (as_of, as_of)):
        latest[r["marker_id"]] = r
    end = as_of or last_signal_day()
    pillars, total_w, acc, inputs_used, missing = [], 0.0, 0.0, 0, []
    for name, weight, src in spec["pillars"]:
        parts = []
        for m in src.get("markers", []):
            r = latest.get(m)
            s = marker_score(m, r["value_num"]) if r else None
            if s is None:
                missing.append(MARKERS[m][0])
            else:
                parts.append({"id": m, "name": MARKERS[m][0], "value": r["value_num"], "unit": MARKERS[m][2],
                              "score": s, "source": f"lab · {r['collected_on']}"})
        for m in src.get("signals", []):
            b = signal_baseline(m, end, 14) if end else None
            if not b:
                missing.append(SIGNALS[m][0])
            else:
                parts.append({"id": m, "name": SIGNALS[m][0], "value": round(b["mean"], 1), "unit": SIGNALS[m][1],
                              "score": _signal_score(m, b["mean"]), "source": f"wearable · 14-day mean to {end}"})
        if parts:
            ps = round(mean(p["score"] for p in parts), 0)
            acc += ps * weight
            total_w += weight
            inputs_used += len(parts)
        pillars.append({"name": name, "weight": weight, "score": round(mean(p["score"] for p in parts)) if parts else None,
                        "inputs": parts})
    score = round(acc / total_w) if total_w else None
    coverage = total_w
    conf = round(confidence(inputs_used * 3) * coverage, 2)
    status = None if score is None else "strong" if score >= 80 else "fair" if score >= 60 else "needs attention"
    return {"key": key, "title": spec["title"], "score": score, "status": status, "coverage": round(coverage, 2),
            "confidence": conf, "pillars": pillars, "missing": missing, "as_of": end,
            "method": "Weighted pillars; missing pillars excluded and weights renormalised; confidence × coverage.",
            "version": ENGINE_VERSION}

# ---------------------------------------------------------------- statistics helpers

def fmt_p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p ≈ {p:.3f}"


def lc(label: str) -> str:
    """Lower-case a label for mid-sentence use, keeping acronyms (HRV, VO2, REM)."""
    first = label.split(" ")[0]
    return label if first.isupper() or any(ch.isdigit() for ch in first) else label[0].lower() + label[1:]


def welch(a: list[float], b: list[float]) -> dict:
    na, nb = len(a), len(b)
    if na < 3 or nb < 3:
        return {"t": 0, "p": 1, "d": 0}
    ma, mb = mean(a), mean(b)
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    se = math.sqrt(va / na + vb / nb) or 1e-9
    t = (ma - mb) / se
    p = 2 * (1 - _phi(abs(t))) if (na + nb) > 30 else 2 * (1 - _t_cdf(abs(t), _welch_df(va, vb, na, nb)))
    sp = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)) or 1e-9
    return {"t": round(t, 2), "p": round(p, 4), "d": round((ma - mb) / sp, 2), "mean_a": ma, "mean_b": mb}


def _welch_df(va, vb, na, nb):
    num = (va / na + vb / nb) ** 2
    den = (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    return num / den if den else na + nb - 2


def _phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _t_cdf(t, df):
    # Hill's approximation via normal transform, adequate for df >= 3
    x = t * (1 - 1 / (4 * df)) / math.sqrt(1 + t * t / (2 * df))
    return _phi(x)


def pearson(xs, ys) -> tuple[float, float]:
    n = len(xs)
    if n < 8:
        return 0.0, 1.0
    mx, my = mean(xs), mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if not sx or not sy:
        return 0.0, 1.0
    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)
    z = 0.5 * math.log((1 + r) / (1 - r)) * math.sqrt(n - 3) if abs(r) < 1 else 10
    return round(r, 2), round(2 * (1 - _phi(abs(z))), 4)

# ---------------------------------------------------------------- correlation engine

def _iid(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:12]


def event_effects(min_events: int = 5) -> list[dict]:
    """Adjusted next-day effect of each logged event on each outcome.

    One ordinary-least-squares model per outcome: outcome(t) ~ every event kind on day t-1 + weekday + linear trend.
    Adjusting for the other events and the weekday separates, e.g., sauna (Tue/Sun) from hard workouts (Mon/Thu) and
    alcohol from weekends. Raw (unadjusted) difference is kept in the receipts for transparency.
    """
    import numpy as np

    out = []
    events = db.rows("SELECT ts, kind FROM events")
    by_kind: dict[str, set] = {}
    for e in events:
        if e["kind"] in ("mood", "meal", "note", "symptom", "supplement", "medication", "life"):
            continue
        by_kind.setdefault(e["kind"], set()).add(e["ts"][:10])
    kinds = sorted(k for k, d in by_kind.items() if len(d) >= min_events)
    if not kinds:
        return []
    outcomes = ["hrv", "rhr", "deep_sleep", "sleep_score", "sleep_hours"]
    tests: list[float] = []
    for metric in outcomes:
        s = series(metric)
        if len(s) < 40:
            continue
        days = [date.fromisoformat(d) for d, _ in s]
        y = np.array([v for _, v in s], dtype=float)
        prev = [(d - timedelta(days=1)).isoformat() for d in days]
        X_ev = np.array([[1.0 if pd in by_kind[k] else 0.0 for k in kinds] for pd in prev])
        # A single weekend term: six weekday dummies would absorb events that habitually fall on fixed weekdays.
        wd = np.array([[1.0 if d.weekday() >= 5 else 0.0] for d in days])
        trend = np.array([[(d - days[0]).days / 30.0] for d in days])
        X = np.hstack([np.ones((len(y), 1)), X_ev, wd, trend])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        dof = len(y) - X.shape[1]
        sigma2 = float(resid @ resid) / max(dof, 1)
        cov = sigma2 * np.linalg.pinv(X.T @ X)
        sd_y = float(np.std(y)) or 1e-9
        label, unit, better, dec = SIGNALS[metric]
        for j, kind in enumerate(kinds, start=1):
            b, se = float(beta[j]), float(np.sqrt(max(cov[j, j], 1e-12)))
            t = b / se
            pval = 2 * (1 - _phi(abs(t)))
            tests.append(pval)
            n_ev = int(X_ev[:, j - 1].sum())
            d_eff = b / sd_y
            if abs(d_eff) < 0.3 or n_ev < min_events:
                continue
            raw_a = y[X_ev[:, j - 1] == 1].mean()
            raw_b = y[X_ev[:, j - 1] == 0].mean()
            good = (b > 0) == (better == "high") if better != "mid" else None
            ci = (b - 1.96 * se, b + 1.96 * se)
            conf = round(min(0.9, (1 - pval) * confidence(n_ev, n_full=12)), 2)
            r = lambda v: round(v, dec or 1)
            out.append({
                "id": _iid("effect", kind, metric), "kind": "event_effect", "event": kind, "metric": metric,
                "title": f"{EVENT_KINDS.get(kind, kind)} → {lc(label)} {'rises' if b > 0 else 'drops'} {abs(r(b))} {unit}".strip(),
                "body": (f"After adjusting for your other logged events, weekends and the overall trend, "
                         f"{EVENT_KINDS.get(kind, kind).lower()} is followed by a {lc(label)} change of {'+' if b > 0 else ''}{r(b)} {unit} "
                         f"(95% CI {r(ci[0])} to {r(ci[1])}; {n_ev} occurrences, {fmt_p(pval)}). Unadjusted, the difference was "
                         f"{'+' if raw_a - raw_b > 0 else ''}{r(raw_a - raw_b)} {unit}. This is a pattern in your own data, not proof of cause."),
                "direction": "harmful" if good is False else "helpful" if good else "neutral",
                "confidence": conf, "n": n_ev,
                "evidence": [{"type": "signal", "metric": metric, "days": sorted(by_kind[kind])[-12:]}],
                "receipts": {"method": "OLS: outcome ~ prior-day events + weekend + trend", "window": f"{s[0][0]} → {s[-1][0]}",
                             "n_event": n_ev, "n_days": len(y), "adjusted_effect": r(b), "ci95": [r(ci[0]), r(ci[1])],
                             "unadjusted_effect": r(raw_a - raw_b), "effect_d": round(d_eff, 2), "p": round(pval, 6),
                             "covariates": [EVENT_KINDS.get(k, k) for k in kinds if k != kind] + ["weekend", "trend"],
                             "version": ENGINE_VERSION},
            })
    cut = bh_threshold(tests)
    out = [o for o in out if o["receipts"]["p"] <= cut]
    for o in out:
        o["receipts"]["fdr"] = f"Benjamini–Hochberg q = 0.05 across {len(tests)} tests (p ≤ {cut:.4f})"
    return sorted(out, key=lambda x: -x["confidence"])


def bh_threshold(ps: list[float], q: float = 0.05) -> float:
    """Largest p that passes Benjamini–Hochberg at false-discovery rate q (0 if none)."""
    m = len(ps)
    best = 0.0
    for i, p in enumerate(sorted(ps), start=1):
        if p <= q * i / m:
            best = p
    return best


def signal_correlations() -> list[dict]:
    pairs = [("steps", "deep_sleep", 0), ("sleep_hours", "hrv", 0), ("daylight_min", "sleep_score", 0),
             ("hrv", "rhr", 0), ("exercise_min", "hrv", 1), ("glucose_mean", "sleep_score", 0),
             ("mindful_min", "hrv", 0)]
    out, tests = [], []
    for a, b, lag in pairs:
        sa, sb = dict(series(a)), dict(series(b))
        xs, ys = [], []
        for d, v in sa.items():
            d2 = (date.fromisoformat(d) + timedelta(days=lag)).isoformat()
            if d2 in sb:
                xs.append(v)
                ys.append(sb[d2])
        r, p = pearson(xs, ys)
        tests.append(p)
        if abs(r) < 0.3:
            continue
        conf = round(min(0.9, abs(r) * 1.4) * confidence(len(xs), n_full=40), 2)
        out.append({
            "id": _iid("corr", a, b, lag), "kind": "signal_correlation", "title":
                f"{SIGNALS[a][0]} {'tracks with' if r > 0 else 'moves against'} {lc(SIGNALS[b][0])}",
            "body": (f"Across {len(xs)} days, higher {lc(SIGNALS[a][0])} "
                     f"{'went with higher' if r > 0 else 'went with lower'} {lc(SIGNALS[b][0])}"
                     f"{' the next day' if lag else ''} (r = {r}, {fmt_p(p)})."),
            "confidence": conf, "n": len(xs), "direction": "neutral",
            "evidence": [{"type": "signal", "metric": a}, {"type": "signal", "metric": b}],
            "receipts": {"method": f"Pearson correlation, lag {lag} d, Fisher z", "n": len(xs), "r": r, "p": p,
                         "version": ENGINE_VERSION},
        })
    cut = bh_threshold(tests)
    return [o for o in out if o["receipts"]["p"] <= cut]


def _v(latest, m):
    r = latest.get(m)
    if not r:
        return None
    return r["value_num"] if r["value_num"] is not None else r["value_text"]


def cross_panel_patterns() -> list[dict]:
    """Knowledge rules connecting panels. Each fires only when its inputs exist and lists them as evidence."""
    L = latest_values()
    out = []

    def add(key, title, body, markers, medical=True, direction="harmful"):
        ev = [{"type": "marker", "marker_id": m, "name": MARKERS[m][0], "value": _v(L, m), "unit": MARKERS[m][2],
               "day": L[m]["collected_on"], "status": L[m]["status"]} for m in markers if m in L]
        panels = {MARKERS[m][1] for m in markers if m in L}
        from .catalog_ext import EVIDENCE
        grade = {"A": 1.0, "B": 0.85, "C": 0.6}
        g = [grade.get(EVIDENCE.get(m, "B"), 0.85) for m in markers if m in L]
        flagged = sum(1 for m in markers if m in L and L[m]["status"] in ("out_of_range", "variant", "detected"))
        support = (flagged + 0.3 * (len(ev) - flagged)) / max(len(markers), 1)
        conf = round(min(0.95, (0.25 + 0.45 * support + 0.06 * len(panels)) * (sum(g) / len(g) if g else 0.8)), 2)
        body = re.sub(r"(\d)\.0\b", r"\1", body)
        out.append({"id": _iid("pattern", key), "kind": "cross_panel", "title": title, "body": body, "confidence": conf,
                    "n": len(ev), "direction": direction, "medical": medical, "evidence": ev,
                    "receipts": {"method": "Cross-modality rule set (labs ↔ imaging ↔ fitness ↔ genetics ↔ wearables)", "rule": key,
                                 "panels": sorted(panels), "version": ENGINE_VERSION}})

    hcy, mthfr, b12 = _v(L, "homocysteine"), _v(L, "mthfr_c677t"), _v(L, "b12")
    if isinstance(hcy, float) and hcy > 12 and mthfr in RISK_GENOTYPES["mthfr_c677t"]:
        add("hcy_mthfr", "Homocysteine is high, and your MTHFR variant may be part of why",
            f"Homocysteine is {hcy} µmol/L (lab range 5–12). You carry MTHFR C677T {mthfr}, which lowers folate-cycle "
            f"efficiency. B12 is {b12} pg/mL, near the bottom of range. Methylated folate and B12 are commonly "
            f"discussed for this pattern; worth reviewing with your clinician before starting anything.",
            ["homocysteine", "mthfr_c677t", "b12"])
    apoe, apob, ldl, lpa = _v(L, "apoe"), _v(L, "apob"), _v(L, "ldl"), _v(L, "lpa")
    if apoe and "ε4" in str(apoe) and isinstance(apob, float) and apob > 90:
        add("apoe_lipids", "ApoB is elevated on an APOE ε4 background",
            f"ApoB {apob} mg/dL and LDL {ldl} mg/dL are above range, Lp(a) is {lpa} mg/dL, and you carry APOE {apoe}. "
            f"ε4 carriers tend to absorb more dietary cholesterol, so lipid lowering is often prioritised earlier. "
            f"This combination is worth a cardiology conversation.", ["apob", "ldl", "lpa", "apoe", "cad9p21"])
    a1c, homa, tcf, prs = _v(L, "hba1c"), _v(L, "homa_ir"), _v(L, "tcf7l2"), _v(L, "prs_t2d")
    if isinstance(a1c, float) and a1c >= 5.7:
        add("glycaemia_genetics", "Blood sugar is in the prediabetic range, with genetic risk alongside",
            f"HbA1c {a1c}% and HOMA-IR {homa} suggest insulin resistance. TCF7L2 {tcf} and a type 2 diabetes "
            f"polygenic score in the {int(prs) if isinstance(prs, float) else '?'}th percentile add risk context. "
            f"Insulin resistance responds well to protein-forward meals, post-meal walks and sleep regularity.",
            ["hba1c", "homa_ir", "glucose", "tcf7l2", "fto", "prs_t2d"])
    crp, calp, zon, but, shan = (_v(L, m) for m in ("hscrp", "calprotectin", "zonulin", "butyrate", "shannon"))
    if isinstance(crp, float) and crp > 1 and isinstance(zon, float) and zon > 107:
        add("gut_inflammation", "Inflammation shows up in both your blood and your gut",
            f"hs-CRP is {crp} mg/L. In the gut report, zonulin ({zon}) and calprotectin ({calp}) are raised while "
            f"butyrate producers ({but}%) and diversity (Shannon {shan}) are low. A leaky, low-diversity gut is one "
            f"plausible driver of systemic inflammation. Fibre diversity is usually the first lever.",
            ["hscrp", "zonulin", "calprotectin", "butyrate", "shannon", "akkermansia", "inflam_clock"])
    vd, vdr = _v(L, "vitd"), _v(L, "vdr")
    if isinstance(vd, float) and vd < 30:
        add("vitd", "Vitamin D is still insufficient",
            f"25-OH vitamin D is {vd} ng/mL (lab range 30–100). Your VDR Taq1 genotype is {vdr}. Re-test after any "
            f"change in supplementation or sun exposure, since the response varies between people.", ["vitd", "vdr"])
    hg, pb = _v(L, "mercury"), _v(L, "lead")
    if isinstance(hg, float) and hg > 3:
        add("metals", "Mercury and lead are above reference",
            f"Provoked urine mercury {hg} and lead {pb} µg/g creatinine. Large predatory fish is the most common "
            f"mercury source. Provoked testing needs clinician interpretation before any chelation is considered.",
            ["mercury", "lead"])
    bpa, mep = _v(L, "bpa"), _v(L, "mep")
    if isinstance(bpa, float) and bpa > 2.1:
        add("plastics", "Plasticiser exposure is above reference",
            f"BPA {bpa} and the phthalate MEP {mep} µg/g creatinine are raised. Heated plastic food containers, "
            f"till receipts and fragranced products are common sources.", ["bpa", "mep", "mehp"], medical=False)
    alt, ggt, tg = _v(L, "alt"), _v(L, "ggt"), _v(L, "tg")
    if isinstance(ggt, float) and ggt > 55:
        n_alc = len(db.rows("SELECT id FROM events WHERE kind='alcohol' AND ts >= date('now','-90 day')"))
        add("liver", "Liver enzymes have risen alongside triglycerides",
            f"ALT {alt} U/L, GGT {ggt} U/L and triglycerides {tg} mg/dL are above range in your latest panel. "
            f"You logged alcohol on {n_alc} days in the last 90. GGT is particularly sensitive to alcohol and to "
            f"fat in the liver.", ["alt", "ggt", "tg", "uric_acid"])
    pace, pheno = _v(L, "dunedinpace"), _v(L, "phenoage_lab")
    if isinstance(pace, float) and pace > 1.0:
        add("pace", "Your pace of ageing is above average",
            f"DunedinPACE is {pace} (1.00 = one biological year per calendar year). The lab's PhenoAge is {pheno} "
            f"years. Pace tends to track the same levers as inflammation and insulin resistance above.",
            ["dunedinpace", "phenoage_lab", "grimage", "inflam_clock", "telomere"], medical=False)
    # ---------------- cross-modality rules (imaging · fitness · body composition · proteomics · advanced blood)
    cac, cpct, crads, pvol = (_v(L, m) for m in ("cac", "cac_pct", "cad_rads", "plaque_vol"))
    if isinstance(cac, float) and cac > 0 and isinstance(apob, float):
        add("cac_apob", "Plaque is already present, and ApoB is the lever that slows it",
            f"Your CT shows a calcium score of {int(cac)} ({int(cpct) if isinstance(cpct, float) else '?'}th percentile for age) "
            f"and CCTA plaque volume {pvol} mm³. ApoB is {apob} mg/dL, LDL particles {_v(L, 'ldl_p')} nmol/L and Lp(a) {lpa} mg/dL. "
            f"Once plaque is visible, guidelines move to treating ApoB/LDL to lower targets. This is worth a cardiology review.",
            ["cac", "cac_pct", "plaque_vol", "cad_rads", "apob", "ldl_p", "lpa", "org_artery", "cimt"])
    elif isinstance(cac, float) and cac == 0 and isinstance(apob, float) and apob > 100:
        add("cac_zero", "No calcified plaque yet, but ApoB is high",
            f"A calcium score of 0 means low short-term risk, but ApoB {apob} mg/dL keeps driving plaque over decades. "
            f"Soft plaque doesn't show on a calcium score; CCTA would.", ["cac", "apob"])
    pdff, lhu, fib = _v(L, "liver_pdff"), _v(L, "liver_hu"), None
    ast_v, plt = _v(L, "ast"), _v(L, "platelets")
    age = age_on()
    if isinstance(ast_v, float) and isinstance(plt, float) and isinstance(alt, float) and age:
        fib = round(age * ast_v / (plt * math.sqrt(alt)), 2)
    if (isinstance(pdff, float) and pdff >= 5) or (isinstance(lhu, float) and lhu < 50):
        add("masld", "Imaging and blood both point to fat in the liver",
            f"MRI-PDFF liver fat is {pdff}% (normal < 5%) and CT liver attenuation {lhu} HU. In blood, ALT {alt}, AST {ast_v}, "
            f"GGT {ggt} U/L and triglycerides {tg}; HOMA-IR {homa}. Proteomic liver age gap is {_v(L, 'org_liver')} years. "
            f"FIB-4 is {fib if fib else 'not computable'}" + (" — low likelihood of advanced fibrosis." if fib and fib < 1.3 else
            ", indeterminate; elastography would clarify." if fib else ".") + " Liver fat is very responsive to weight, alcohol and fructose changes.",
            ["liver_pdff", "liver_hu", "alt", "ast", "ggt", "tg", "homa_ir", "vat_area", "org_liver"])
    vat = _v(L, "vat_area")
    if isinstance(vat, float) and vat > 100:
        add("vat_metabolic", "Visceral fat is likely feeding the insulin resistance and inflammation",
            f"DEXA visceral fat area is {int(vat)} cm² (target < 100; BCA visceral level {_v(L, 'visceral_level')}). "
            f"Visceral fat releases fatty acids and IL-6 into the liver: HOMA-IR {homa}, triglycerides {tg}, IL-6 {_v(L, 'il6')} pg/mL, "
            f"epicardial fat {_v(L, 'epicardial_fat')} cm³. Losing visceral fat usually moves all of these together.",
            ["vat_area", "visceral_level", "homa_ir", "tg", "il6", "hscrp", "epicardial_fat", "liver_pdff"])
    vo2, almi, grip = _v(L, "vo2max_lab"), _v(L, "almi"), _v(L, "grip")
    if isinstance(vo2, float):
        b = signal_baseline("vo2max", days=60)
        watch = f" Your watch estimates {round(b['mean'], 1)}, so the wearable {'agrees' if abs(b['mean'] - vo2) < 3 else 'is off by ' + str(round(abs(b['mean'] - vo2), 1))}." if b else ""
        add("fitness_reserve", "Cardiorespiratory fitness is the biggest modifiable longevity lever here",
            f"Lab VO2 max is {vo2} mL/kg/min, just below the 50th percentile for your age and sex.{watch} Moving from below-average to "
            f"above-average fitness is associated with a large drop in all-cause mortality. Your Zone 2 ceiling from the CPET is "
            f"{_v(L, 'vt1_hr')} bpm. ALMI is {almi} kg/m² and grip {grip} kg — muscle is adequate, so aerobic capacity is the gap.",
            ["vo2max_lab", "vt1_hr", "hrr_1min", "almi", "grip", "org_muscle"], medical=False, direction="harmful")
    ahi = _v(L, "ahi")
    if isinstance(ahi, float) and ahi >= 5:
        sp = signal_baseline("spo2", days=60)
        add("osa", "Sleep apnoea may be behind part of your sleep and HRV pattern",
            f"Your home sleep test shows AHI {ahi} events/hour (mild ≥ 5), ODI {_v(L, 'odi')} and a lowest SpO2 of {_v(L, 'min_spo2')}%. "
            f"Your ring's nightly SpO2 averages {round(sp['mean'], 1) if sp else 'n/a'}%. Untreated apnoea raises blood pressure, "
            f"glucose and inflammation; visceral fat ({vat} cm²) is a common driver. A sleep-medicine review is worth it.",
            ["ahi", "odi", "min_spo2", "vat_area", "hscrp", "glucose"])
    wmh, ptau = _v(L, "wmh_fazekas"), _v(L, "ptau217")
    if isinstance(wmh, float) and wmh >= 1:
        add("brain_vascular", "Small white-matter changes are worth protecting against",
            f"MRI shows Fazekas {int(wmh)} white-matter hyperintensities and a brain-age gap of {_v(L, 'brain_age_gap')} years. "
            f"These track with vascular risk: homocysteine {hcy}, ApoB {apob}, and sleep apnoea (AHI {ahi}). p-tau217 is "
            f"{ptau} pg/mL (low likelihood of amyloid) and you carry APOE {apoe}. Blood pressure, homocysteine and sleep are the levers.",
            ["wmh_fazekas", "brain_age_gap", "ptau217", "nfl", "homocysteine", "apoe", "apob", "ahi"])
    o3 = _v(L, "omega3_index")
    if isinstance(o3, float) and o3 < 8:
        add("omega3", "Low omega-3 index alongside high triglycerides and inflammation",
            f"Omega-3 index is {o3}% (target ≥ 8%), with triglycerides {tg} mg/dL, IL-6 {_v(L, 'il6')} and hs-CRP {crp}. "
            f"Mercury is {hg}, so small oily fish or an algae/fish-oil supplement is safer than large predatory fish.",
            ["omega3_index", "tg", "il6", "hscrp", "mercury"], medical=False)
    org = {k: _v(L, k) for k in ("org_heart", "org_liver", "org_artery", "org_immune", "org_kidney", "org_brain", "org_muscle")}
    old = sorted([(v, k) for k, v in org.items() if isinstance(v, float) and v > 1.5], reverse=True)
    if old:
        names = {"org_heart": "heart", "org_liver": "liver", "org_artery": "arteries", "org_immune": "immune system",
                 "org_kidney": "kidneys", "org_brain": "brain", "org_muscle": "muscle"}
        support = {"org_liver": "liver fat on MRI and raised GGT", "org_heart": "calcium score and epicardial fat",
                   "org_artery": "plaque on CCTA and ApoB", "org_immune": "IL-6, GlycA and hs-CRP"}
        lines = "; ".join(f"{names[k]} +{v} y ({support.get(k, 'no corroborating test yet')})" for v, k in old)
        add("organ_age", "Your fastest-ageing organs line up with your imaging and blood",
            f"Proteomic organ ages: {lines}. The organs that read older are the same ones your other tests flag, which makes the "
            f"signal more credible. Proteomic organ clocks are research-grade (evidence C).",
            [k for _, k in old] + ["liver_pdff", "cac", "il6"], medical=False)
    dexa_bf, bca_bf = _v(L, "body_fat_pct"), _v(L, "bca_body_fat")
    if isinstance(dexa_bf, float) and isinstance(bca_bf, float) and abs(dexa_bf - bca_bf) >= 2:
        add("bf_methods", "DEXA and bioimpedance disagree on your body fat",
            f"DEXA says {dexa_bf}% and BCA says {bca_bf}%. BCA tends to read lower and shifts with hydration; DEXA is the reference. "
            f"Track each method against itself rather than mixing them.", ["body_fat_pct", "bca_body_fat"], medical=False, direction="neutral")
    cys, cr = _v(L, "cystatin_c"), _v(L, "creatinine")
    if isinstance(cys, float) and isinstance(cr, float) and age:
        from .derived import ckd_epi_2021, ckd_epi_cys_2012
        e_cr, e_cy = ckd_epi_2021(cr, age, profile().get("sex", "male")), ckd_epi_cys_2012(cys, age, profile().get("sex", "male"))
        if abs(e_cr - e_cy) > 15:
            add("egfr_discord", "Your two kidney-function estimates disagree",
                f"eGFR from creatinine is {round(e_cr)} and from cystatin C {round(e_cy)} mL/min/1.73m². Creatinine depends on muscle "
                f"mass (ALMI {almi}); cystatin C does not. The combined value is usually the most accurate.",
                ["creatinine", "cystatin_c", "almi", "uacr"], direction="neutral")
        else:
            add("kidney_ok", "Kidney function is consistent across two methods",
                f"eGFR {round(e_cr)} (creatinine) and {round(e_cy)} (cystatin C), UACR {_v(L, 'uacr')} mg/g. No action needed.",
                ["creatinine", "cystatin_c", "uacr"], medical=False, direction="helpful")
    return out


def lab_wearable_links() -> list[dict]:
    """Change in a lab marker between reports vs change in a wearable signal over the 30 days before each."""
    out = []
    pairs = [("hscrp", "hrv"), ("hscrp", "sleep_hours"), ("hba1c", "steps"), ("ggt", "sleep_score")]
    for marker, metric in pairs:
        h = [r for r in marker_history(marker) if r["value_num"] is not None]
        if len(h) < 2:
            continue
        a, b = h[-2], h[-1]
        def win(day):
            end = date.fromisoformat(day)
            vals = [v for _, v in series(metric, (end - timedelta(days=30)).isoformat(), day)]
            return mean(vals) if len(vals) >= 10 else None
        wa, wb = win(a["collected_on"]), win(b["collected_on"])
        if wa is None or wb is None:
            continue
        dm = b["value_num"] - a["value_num"]
        ds = wb - wa
        if abs(ds) / max(abs(wa), 1e-6) < 0.05:
            continue
        label, unit, better, dec = SIGNALS[metric]
        out.append({
            "id": _iid("labwear", marker, metric), "kind": "lab_wearable",
            "title": f"{MARKERS[marker][0]} {'rose' if dm > 0 else 'fell'} as {lc(label)} {'rose' if ds > 0 else 'fell'}",
            "body": (f"Between {a['collected_on']} and {b['collected_on']}, {MARKERS[marker][0]} went from {a['value_num']} "
                     f"to {b['value_num']} {MARKERS[marker][2]}. Over the 30 days before each test your {lc(label)} "
                     f"averaged {round(wa, dec or 1)} then {round(wb, dec or 1)} {unit}. Two lab points can't establish "
                     f"a trend on their own; another test in 8–12 weeks would."),
            "confidence": 0.35, "n": 2, "direction": "neutral",
            "evidence": [{"type": "marker", "marker_id": marker, "values": [a["value_num"], b["value_num"]]},
                         {"type": "signal", "metric": metric, "means": [round(wa, 2), round(wb, 2)]}],
            "receipts": {"method": "Paired change: lab delta vs 30-day wearable window before each draw",
                         "version": ENGINE_VERSION}})
    return out


def trend_insights() -> list[dict]:
    out = []
    for mid in MARKERS:
        t = marker_trend(mid)
        if not t or t["direction"] == "same" or t["pct"] is None:
            continue
        last = marker_history(mid)[-1]
        crossed = last["status"] == "out_of_range" or abs(t["pct"]) >= 15
        if not crossed or abs(t["pct"]) < 5:
            continue
        out.append({
            "id": _iid("trend", mid, t["to_day"]), "kind": "lab_trend",
            "title": f"{MARKERS[mid][0]} {'improved' if t['direction'] == 'better' else 'worsened'} "
                     f"{abs(t['pct'])}% since {t['from_day']}",
            "body": f"{MARKERS[mid][0]} went from {t['from']} to {t['to']} {MARKERS[mid][2]} "
                    f"({t['from_day']} → {t['to_day']}).",
            "confidence": 0.5, "n": 2, "direction": "helpful" if t["direction"] == "better" else "harmful",
            "evidence": [{"type": "marker", "marker_id": mid, "values": [t["from"], t["to"]]}],
            "receipts": {"method": "Difference between two most recent lab results", "version": ENGINE_VERSION},
            "marker_id": mid})
    return sorted(out, key=lambda x: (x["direction"] != "harmful", -abs(float(x["title"].split("%")[0].split()[-1]))))


def regenerate_insights() -> list[dict]:
    """Recompute all engine insights; review state and dismissals persist by stable id."""
    now = now_iso()
    produced = cross_panel_patterns() + event_effects() + lab_wearable_links() + signal_correlations() + trend_insights()
    for ins in produced:
        existing = db.one("SELECT review_state, dismissed FROM insights WHERE id = ?", (ins["id"],))
        medical = 1 if ins.get("medical") else 0
        state = existing["review_state"] if existing else ("awaiting" if medical else "none")
        db.exec_("""INSERT OR REPLACE INTO insights (id, created_at, kind, title, body, confidence, evidence, receipts,
                    review_state, medical, dismissed) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                 (ins["id"], now, ins["kind"], ins["title"], ins["body"], ins["confidence"], db.j(ins["evidence"]),
                  db.j({**ins["receipts"], "n": ins.get("n"), "direction": ins.get("direction")}), state, medical,
                  existing["dismissed"] if existing else 0))
        if not existing and medical:
            db.exec_("INSERT INTO review_thread (insight_id, ts, author, action, note) VALUES (?,?,?,?,?)",
                     (ins["id"], now, "Sinc", "drafted", "Drafted from your Vault and queued for clinician review."))
    return produced


def list_insights(include_dismissed=False) -> list[dict]:
    rs = db.rows("SELECT * FROM insights" + ("" if include_dismissed else " WHERE dismissed = 0") +
                 " ORDER BY medical DESC, confidence DESC")
    for r in rs:
        r["evidence"] = db.unj(r["evidence"], [])
        r["receipts"] = db.unj(r["receipts"], {})
        r["thread"] = db.rows("SELECT * FROM review_thread WHERE insight_id = ? ORDER BY ts, id", (r["id"],))
    return rs

# ---------------------------------------------------------------- N-of-1

def analyse_study(study: dict) -> dict:
    """ABAB design: periods alternate off (A) / on (B) from start_day, each period_days long."""
    start = date.fromisoformat(study["start_day"])
    n = study["period_days"]
    s = dict(series(study["outcome"]))
    a, b = [], []
    for i in range(4):
        arm = b if i % 2 else a
        for k in range(n):
            d = (start + timedelta(days=i * n + k)).isoformat()
            if d in s:
                arm.append(s[d])
    end = start + timedelta(days=4 * n)
    if len(a) < n or len(b) < n:
        done = sum(1 for d in s if start.isoformat() <= d < end.isoformat())
        return {"verdict": "in progress", "days_logged": done, "days_total": 4 * n, "a": len(a), "b": len(b)}
    w = welch(b, a)
    better = SIGNALS[study["outcome"]][2]
    diff = w["mean_a"] - w["mean_b"]
    good = diff > 0 if better == "high" else diff < 0
    if w["p"] < 0.05 and abs(w["d"]) >= 0.5:
        verdict = "Helped" if good else "Possible negative"
    else:
        verdict = "No reliable signal"
    lab, unit, _, dec = SIGNALS[study["outcome"]]
    return {"verdict": verdict, "mean_on": round(w["mean_a"], dec or 1), "mean_off": round(w["mean_b"], dec or 1),
            "diff": round(diff, dec or 1), "unit": unit, "d": w["d"], "p": w["p"], "n_on": len(b), "n_off": len(a),
            "method": "ABAB alternating periods, Welch t-test on-vs-off", "version": ENGINE_VERSION}

# ---------------------------------------------------------------- completeness

def completeness() -> dict:
    today = date.today()
    def report_within(panel, days):
        r = db.one("SELECT MAX(collected_on) AS d FROM reports WHERE panel = ?", (panel,))
        return bool(r and r["d"] and (today - date.fromisoformat(r["d"])).days <= days)
    last = last_signal_day()
    p = profile()
    items = [
        ("Blood panel in the last 6 months", report_within("blood", 183), "Upload a recent blood panel"),
        ("Gut microbiome report", report_within("gut", 730), "Add a gut microbiome test"),
        ("Genetics on file", report_within("genetic", 3650), "Upload a genetics / SNP report"),
        ("Biological-age test", report_within("bioage", 730), "Add an epigenetic age test"),
        ("Toxin & metals screen", report_within("metals", 730) or report_within("toxins", 730), "Add a toxins screen"),
        ("Wearable synced in the last 2 days", bool(last and (today - date.fromisoformat(last)).days <= 2),
         "Connect or sync a wearable"),
        ("Sleep data", bool(series("sleep_hours")), "Wear a sleep tracker"),
        ("Emergency card", bool(p.get("emergency", {}).get("blood_type")), "Fill in your emergency card"),
        ("Consents reviewed", bool(db.one("SELECT 1 AS x FROM consent_history")), "Review your consents"),
        ("A clinician linked", bool(db.one("SELECT 1 AS x FROM appointments")), "Link a clinician"),
        ("Imaging on file", bool(db.one("SELECT 1 AS x FROM imaging")), "Add an imaging study"),
        ("A daily reflection this week", bool(db.one("SELECT 1 AS x FROM events WHERE kind='mood' AND ts >= date('now','-7 day')")),
         "Log how you feel today"),
    ]
    done = sum(1 for _, ok, _ in items if ok)
    return {"score": round(done / len(items) * 100), "items": [{"label": l, "done": ok, "action": a} for l, ok, a in items]}


def panel_summary(panel: str) -> dict:
    latest = {}
    for r in db.rows("""SELECT r.*, rep.collected_on, rep.title FROM results r JOIN reports rep ON rep.id = r.report_id
                        WHERE rep.panel = ? ORDER BY rep.collected_on""", (panel,)):
        latest[r["marker_id"]] = r
    counts = {"optimal": 0, "in_range": 0, "out_of_range": 0, "other": 0}
    for r in latest.values():
        counts[r["status"] if r["status"] in counts else "other"] += 1
    reports = db.rows("SELECT id, title, collected_on, source, is_test_data FROM reports WHERE panel = ? "
                      "ORDER BY collected_on DESC", (panel,))
    return {"panel": panel, "title": PANELS[panel], "counts": counts, "markers": len(latest), "reports": reports,
            "latest_day": reports[0]["collected_on"] if reports else None}
