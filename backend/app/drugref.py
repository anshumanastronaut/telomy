"""Drug reference for the doctor platform — authoritative, free, no-key sources:
 · RxNorm/RxNav (NLM) to normalise the drug name → ingredient.
 · openFDA drug label (FDA Structured Product Labeling) for indications, dosing, contraindications, warnings,
   boxed warning and label-listed interactions.
 · openFDA FAERS counts for the most-reported adverse events (real-world signal, not causation).

Everything about doses and interactions comes from the label/FAERS — never free-text from an LLM. Short timeouts,
small cache, graceful partials (any one source can fail and the rest still return).
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

_CACHE: dict[str, tuple[float, object]] = {}
_TTL = 6 * 3600.0


def _get(url: str, timeout: float = 10.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "telomy/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _first(d: dict, key: str, limit: int = 1200) -> str:
    v = d.get(key)
    if isinstance(v, list) and v:
        return str(v[0])[:limit]
    if isinstance(v, str):
        return v[:limit]
    return ""


def _rxnorm(name: str) -> dict:
    """Normalise a free-text drug name to its RxNorm ingredient (best-effort)."""
    try:
        q = urllib.parse.quote(name)
        data = _get(f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={q}&search=2")
        ids = (data.get("idGroup") or {}).get("rxnormId") or []
        rxcui = ids[0] if ids else None
        label = name
        if rxcui:
            props = _get(f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/property.json?propName=RxNorm%20Name")
            vals = (props.get("propConceptGroup") or {}).get("propConcept") or []
            if vals:
                label = vals[0].get("propValue", name)
        return {"rxcui": rxcui, "name": label}
    except Exception:
        return {"rxcui": None, "name": name}


def _label(name: str) -> dict:
    """Pull the FDA label (SPL) for a drug by generic or brand name."""
    q = urllib.parse.quote(f'openfda.generic_name:"{name}" openfda.brand_name:"{name}"')
    try:
        data = _get(f"https://api.fda.gov/drug/label.json?search={q}&limit=1")
    except Exception:
        return {}
    results = data.get("results") or []
    if not results:
        return {}
    r = results[0]
    of = r.get("openfda", {})
    return {
        "brand": (of.get("brand_name") or [""])[0],
        "generic": (of.get("generic_name") or [""])[0],
        "route": ", ".join(of.get("route", [])[:3]),
        "indications": _first(r, "indications_and_usage", 1400),
        "dosing": _first(r, "dosage_and_administration", 1400),
        "contraindications": _first(r, "contraindications", 1000),
        "boxed_warning": _first(r, "boxed_warning", 1000),
        "warnings": _first(r, "warnings_and_cautions") or _first(r, "warnings"),
        "interactions": _first(r, "drug_interactions", 1400),
        "pregnancy": _first(r, "pregnancy", 600),
    }


def _faers_top(name: str, k: int = 8) -> list[dict]:
    """Most-reported adverse events in FAERS for this drug (disproportionate reporting ≠ causation)."""
    q = urllib.parse.quote(f'patient.drug.medicinalproduct:"{name}"')
    try:
        data = _get(f"https://api.fda.gov/drug/event.json?search={q}&count=patient.reaction.reactionmeddrapt.exact&limit={k}")
    except Exception:
        return []
    return [{"term": str(x.get("term", "")).title(), "count": x.get("count", 0)} for x in (data.get("results") or [])][:k]


DISCLAIMER = ("From the FDA label and FAERS reports — reference only, not a prescribing directive. Confirm the dose, "
              "contraindications and interactions against the current label and the patient's full medication list.")


def lookup(name: str) -> dict:
    name = (name or "").strip()
    if not name:
        return {"error": "Enter a drug name."}
    key = f"d|{name.lower()}"
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return dict(hit[1])  # type: ignore[arg-type]
    rx = _rxnorm(name)
    lab = _label(rx.get("name") or name) or _label(name)
    faers = _faers_top(rx.get("name") or name)
    sources = [{"label": "FDA label (openFDA / DailyMed)", "url": "https://dailymed.nlm.nih.gov/dailymed/"}]
    if rx.get("rxcui"):
        sources.append({"label": f"RxNorm {rx['rxcui']}", "url": f"https://mor.nlm.nih.gov/RxNav/search?searchBy=RXCUI&searchTerm={rx['rxcui']}"})
    out = {
        "query": name,
        "name": lab.get("generic") or rx.get("name") or name,
        "brand": lab.get("brand", ""),
        "rxcui": rx.get("rxcui"),
        "route": lab.get("route", ""),
        "label": {k: lab.get(k, "") for k in ("indications", "dosing", "contraindications", "boxed_warning", "warnings", "interactions", "pregnancy")},
        "faers_top": faers,
        "have_label": bool(lab),
        "sources": sources,
        "disclaimer": DISCLAIMER,
    }
    if not lab and not faers:
        out["notice"] = "No FDA label found for that spelling — try the generic name (e.g. 'atorvastatin' not a brand)."
    if len(_CACHE) > 200:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = (time.time(), out)
    return out
