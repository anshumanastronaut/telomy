"""Data-backed drug-safety layer — loads the FAERS disproportionality signals mined from ~20.7M FDA adverse-
event reports (built by research/safety/build_faers_signals.py) and serves them to the geroprotector engine.

This augments the hand-coded contraindication/interaction screen with real-world reporting signals: for each
geroprotector drug/hormone, the reactions reported disproportionately often (ROR with 95% CI). It is a
monitoring/consent aid — reporting disproportionality is NOT proof of causation — so it informs what to watch
and what to tell the member, never a hard block (the hand-coded screen keeps that job).
"""
from __future__ import annotations
import json, os, functools

_ASSET = os.path.join(os.path.dirname(__file__), "..", "assets", "safety", "faers_signals.json")


@functools.lru_cache(maxsize=1)
def _load() -> dict:
    try:
        with open(os.path.abspath(_ASSET)) as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def available() -> bool:
    return bool(_load().get("drugs"))


def signals(gid: str, topk: int = 8) -> dict | None:
    """Top FAERS signals for a geroprotector id, or None if we have no FAERS data for it (e.g. a supplement)."""
    d = _load()
    rec = (d.get("drugs") or {}).get(gid)
    if not rec or not rec.get("signals"):
        return None
    meta = d.get("meta", {})
    return {
        "faers_name": rec.get("faers_name"), "n_reports": rec.get("n_reports"),
        "total_corpus": meta.get("total_reports"),
        "top_signals": [{"reaction": s["reaction"], "ror": s["ror"], "ror_95ci": [s["ror_lo"], s["ror_hi"]],
                         "reports": s["a"]} for s in rec["signals"][:topk]],
        "watch": [s["reaction"] for s in rec["signals"][:topk]],
        "note": "FAERS reporting disproportionality (ROR, 95% CI) across the full corpus — a monitoring/consent "
                "signal, not causation.",
    }


def summary() -> dict:
    d = _load()
    if not d:
        return {"available": False}
    drugs = d.get("drugs", {})
    return {"available": True, "total_reports": d.get("meta", {}).get("total_reports"),
            "drugs_covered": len(drugs), "signals": {k: len(v.get("signals", [])) for k, v in drugs.items()}}
