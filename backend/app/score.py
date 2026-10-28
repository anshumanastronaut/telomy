"""Telomy Score — the headline longevity number (Track B2).

A composite 0–100 wellness score built from the member's own labs, with named domain sub-scores (cardiovascular,
metabolic, inflammation, kidney, liver, nutrition, hormones) and a biological-age readout from the best available
aging clock. Each marker is scored by how well it sits inside its optimal band (catalog ranges); domains average
their markers; the composite weights the longevity-driving domains higher. Wellness information, not a diagnosis;
bio-age is an estimate — we state the clock used and never over-claim precision.
"""
from __future__ import annotations

from . import catalog, engine

# health domain → the catalog markers that define it (longevity-weighted in COMPOSITE_W)
DOMAINS: dict[str, tuple[str, list[str]]] = {
    "cardiovascular": ("Cardiovascular", ["apob", "ldl", "hdl", "tg", "lpa", "chol_total"]),
    "metabolic": ("Metabolic", ["glucose", "hba1c", "insulin", "uric_acid"]),
    "inflammation": ("Inflammation", ["hscrp", "homocysteine", "wbc"]),
    "kidney": ("Kidney", ["egfr", "creatinine"]),
    "liver": ("Liver", ["alt", "ggt", "alp"]),
    "nutrition": ("Nutrition", ["vitd", "b12", "ferritin", "hemoglobin"]),
    "hormones": ("Hormones", ["tsh", "testosterone", "cortisol"]),
}
COMPOSITE_W = {"cardiovascular": 1.5, "metabolic": 1.5, "inflammation": 1.3,
               "kidney": 1.0, "liver": 1.0, "nutrition": 1.0, "hormones": 0.8}
# aging clocks to read a biological age from, best first
CLOCKS = ["phenoage_lab", "grimage", "horvath", "bioage"]


def _marker_score(value: float, low, high, better: str) -> float | None:
    """0–100: 100 inside the optimal band, linear decay of 100 points per band-width of deviation."""
    if better == "info" or low is None or high is None:
        return None
    band = max(high - low, 1e-6)
    if better == "mid":
        if low <= value <= high:
            return 100.0
        d = (low - value) if value < low else (value - high)
    elif better == "low":
        d = max(0.0, value - high)
    elif better == "high":
        d = max(0.0, low - value)
    else:
        return None
    return max(0.0, 100.0 - (d / band) * 100.0)


def _status(s: float) -> str:
    return "good" if s >= 80 else "borderline" if s >= 50 else "low"


def _band(s: float) -> str:
    return "excellent" if s >= 85 else "good" if s >= 70 else "fair" if s >= 55 else "needs work"


def compute(as_of: str | None = None) -> dict:
    L = engine.latest_values(as_of)
    def val(k):
        r = L.get(k)
        v = r.get("value_num") if r else None
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    domains = []
    for key, (name, ids) in DOMAINS.items():
        marks = []
        for mid in ids:
            v = val(mid)
            meta = catalog.MARKERS.get(mid)
            if v is None or not meta:
                continue
            _, _, unit, low, high, better = meta[0], meta[1], meta[2], meta[3], meta[4], meta[5]
            s = _marker_score(v, low, high, better)
            if s is None:
                continue
            marks.append({"id": mid, "name": meta[0], "value": v, "unit": unit, "score": round(s), "status": _status(s)})
        if marks:
            dscore = sum(m["score"] for m in marks) / len(marks)
            domains.append({"key": key, "name": name, "score": round(dscore), "status": _status(dscore),
                            "band": _band(dscore), "n": len(marks), "markers": marks})

    composite = None
    if domains:
        num = sum(d["score"] * COMPOSITE_W.get(d["key"], 1.0) for d in domains)
        den = sum(COMPOSITE_W.get(d["key"], 1.0) for d in domains)
        composite = round(num / den)

    # biological age from the best available clock vs chronological age
    chrono = val("chrono_age")
    if chrono is None:
        p = engine.profile() or {}
        try:
            chrono = float(p.get("age")) if p.get("age") else None
        except (TypeError, ValueError):
            chrono = None
    bio_age, clock_used = None, None
    for ck in CLOCKS:
        v = val(ck)
        if v is not None:
            bio_age, clock_used = v, catalog.MARKERS.get(ck, (ck,))[0]
            break
    age_delta = round(bio_age - chrono, 1) if (bio_age is not None and chrono is not None) else None

    return {
        "score": composite,
        "band": _band(composite) if composite is not None else None,
        "bio_age": round(bio_age, 1) if bio_age is not None else None,
        "chrono_age": round(chrono, 1) if chrono is not None else None,
        "age_delta": age_delta,
        "clock": clock_used,
        "domains": sorted(domains, key=lambda d: d["score"]),  # weakest first — what to work on
        "coverage": len(domains),
        "note": ("Your Telomy Score summarises how your labs sit against optimal ranges — wellness information, not a "
                 "diagnosis. Bio-age is an estimate from the clock shown. Track it across retests as you make changes."),
    }
