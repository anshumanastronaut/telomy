"""Derived biomarker ratios & indices — Longevity super-app, Track B1.

Pure computation on the member's own imported labs (mg/dL, per catalog): many high-signal "insights" at ~zero cost,
the way Superpower/Function surface atherogenic and insulin-resistance indices. Each result carries value + optimal
band + a status (good / borderline / high) + a plain-language line + the primary reference. We only emit a ratio when
all of its inputs are present. Nothing here is a diagnosis — it's a signal to discuss, framed as wellness information.
"""
from __future__ import annotations

import math

from . import engine


def _val(L: dict, key: str) -> float | None:
    r = L.get(key)
    try:
        return float(r["value"]) if r and r.get("value") is not None else None
    except (TypeError, ValueError, KeyError):
        return None


def _bmi() -> float | None:
    p = engine.profile() or {}
    h = p.get("height_cm") or p.get("height")
    w = p.get("weight_kg") or p.get("weight")
    try:
        h, w = float(h), float(w)
        return w / (h / 100) ** 2 if h and w else None
    except (TypeError, ValueError):
        return None


def _status(v: float, good_below: float, high_above: float) -> str:
    return "good" if v < good_below else "high" if v > high_above else "borderline"


def ratios(as_of: str | None = None) -> dict:
    L = engine.latest_values(as_of)
    g = lambda k: _val(L, k)  # noqa: E731
    out: list[dict] = []

    def emit(key, name, value, unit, status, optimal, interp, inputs, ref):
        out.append({"key": key, "name": name, "value": round(value, 2), "unit": unit, "status": status,
                    "optimal": optimal, "interpretation": interp, "inputs": inputs, "ref": ref})

    tc, hdl, ldl, tg, glu, ins, apob, lpa = (g(k) for k in ("chol_total", "hdl", "ldl", "tg", "glucose", "insulin", "apob", "lpa"))

    # ---- lipid / atherogenic
    if tc and hdl:
        r = tc / hdl
        emit("tc_hdl", "Total cholesterol : HDL", r, "ratio", _status(r, 3.5, 5.0), "< 3.5",
             "A lower ratio means a more favourable cholesterol balance and lower cardiovascular risk.",
             ["chol_total", "hdl"], "Framingham")
    if ldl and hdl:
        r = ldl / hdl
        emit("ldl_hdl", "LDL : HDL", r, "ratio", _status(r, 2.0, 3.5), "< 2.0",
             "The balance of 'bad' to 'good' cholesterol; lower is better for artery health.", ["ldl", "hdl"], "ESC/EAS")
    if tg and hdl:
        r = tg / hdl
        emit("tg_hdl", "Triglyceride : HDL", r, "ratio", _status(r, 2.0, 3.0), "< 2.0",
             "A surrogate for insulin resistance and small dense LDL; higher values flag metabolic risk.", ["tg", "hdl"], "Gaziano 1997")
        aip = math.log10(tg / hdl)
        emit("aip", "Atherogenic index of plasma", aip, "log", _status(aip, 0.11, 0.21), "< 0.11",
             "AIP = log(TG/HDL); higher values associate with more atherogenic, small dense LDL particles.", ["tg", "hdl"], "Dobiášová 2001")
    if tc and hdl:
        nonhdl = tc - hdl
        emit("non_hdl", "Non-HDL cholesterol", nonhdl, "mg/dL", _status(nonhdl, 130, 160), "< 130 mg/dL",
             "All the cholesterol in artery-clogging particles — a better risk marker than LDL alone.", ["chol_total", "hdl"], "ACC/AHA")
    if tc and hdl and ldl:
        remnant = max(0.0, tc - hdl - ldl)
        emit("remnant_chol", "Remnant cholesterol", remnant, "mg/dL", _status(remnant, 24, 30), "< 24 mg/dL",
             "Cholesterol in triglyceride-rich remnant particles; an emerging independent cardiovascular risk marker.",
             ["chol_total", "hdl", "ldl"], "Varbo 2013")

    # ---- insulin resistance / metabolic
    if tg and glu:
        tyg = math.log(tg * glu / 2.0)  # mg/dL inputs; IR cutoff ≈ 8.5
        emit("tyg", "TyG index", tyg, "index", _status(tyg, 8.5, 8.75), "< 8.5",
             "Triglyceride–glucose index, a validated marker of insulin resistance.", ["tg", "glucose"], "Simental-Mendía 2008")
        bmi = _bmi()
        if bmi and hdl:
            # Bello-Chavolla 2018: BMI multiplies OUTSIDE the first log. IR cutoff ≈ 50.
            mets = math.log(2 * glu + tg) * bmi / math.log(hdl)
            emit("mets_ir", "METS-IR", mets, "index", _status(mets, 50, 50.01), "< 50",
                 "Metabolic score for insulin resistance; above ~50 suggests reduced insulin sensitivity.",
                 ["glucose", "tg", "hdl", "BMI"], "Bello-Chavolla 2018")
    if glu and ins:
        homa = glu * ins / 405.0
        emit("homa_ir", "HOMA-IR", homa, "index", _status(homa, 2.0, 2.9), "< 2.0",
             "Fasting insulin resistance estimate; higher means the body needs more insulin for the same glucose.",
             ["glucose", "insulin"], "Matthews 1985")

    # ---- glycaemia translation
    a1c = g("hba1c")
    if a1c:
        eag = 28.7 * a1c - 46.7
        st = "good" if a1c < 5.7 else "high" if a1c >= 6.5 else "borderline"
        emit("eag", "Estimated average glucose", eag, "mg/dL", st, "< 117 mg/dL (A1c < 5.7%)",
             f"Your HbA1c of {a1c}% corresponds to an average glucose of about {eag:.0f} mg/dL over ~3 months.",
             ["hba1c"], "Nathan 2008")

    return {"ratios": out,
            "note": "Derived from your most recent labs — wellness information, not a diagnosis. Discuss anything flagged with your clinician.",
            "available": len(out)}
