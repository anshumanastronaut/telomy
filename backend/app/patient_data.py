"""Patient intake & the 360 summary — pull a patient's REAL stored data and compose a grounded clinical summary.

The care graph (tenancy) links a clinical `patients` row to an app user by `user_ref`; that user's live data
(labs, vitals, sleep/recovery, habits, reports) lives in their own per-user SQLite DB. This module resolves that
link, *temporarily binds* to the patient's DB (authorised because the doctor is assigned to the patient), reads
every domain, restores the binding, and returns:

  • biomarkers(pid)  — a flat, engine-keyed dict of the patient's latest labs → feeds the intake auto-fill so the
                        console never retypes values, plus /me/longevity, /me/macros and clinic assess.
  • overview(pid)    — the one-screen 360: identity + risk models + labs (grouped/flagged) + vitals (latest +
                        7-day trend) + recovery/sleep + habits + reports + a GROUNDED AI narrative.

Design is research-grounded: longitudinal trajectories not snapshots; nocturnal SpO₂/HRV are first-class; and the
AI summary is a DETERMINISTIC grounded composer (every statement traces to a value) — because in clinical AI the
dominant error is omission/fabrication, so facts never come from a model, and a clinician reviews and signs.
"""
from __future__ import annotations
import contextlib
import time

from . import db

# engine marker id -> the key the longevity/macros/assess engines expect
_MARKER_MAP = {
    "ldl": "ldl", "apob": "apob", "hba1c": "hba1c", "hdl": "hdl", "chol_total": "total_chol",
    "trig": "trig", "triglycerides": "trig", "hscrp": "crp_mgL", "hs_crp": "crp_mgL", "crp": "crp_mgL",
    "vitamin_d": "vitamin_d_25oh", "vit_d_25oh": "vitamin_d_25oh", "egfr": "egfr", "albumin": "albumin",
    "creatinine": "creatinine", "ferritin": "ferritin", "b12": "b12", "magnesium": "magnesium",
    "testosterone": "total_testosterone", "total_testosterone": "total_testosterone",
    "homocysteine": "homocysteine", "uric_acid": "uric_acid", "alt": "alt", "ast": "ast",
    "lpa": "lp_a", "vo2max": "vo2max", "almi": "almi", "omega3_index": "omega3_index", "glucose": "glucose",
}
# seed-panel field (patients.data json) -> engine key, for patients without a linked live DB
_SEED_MAP = {"ldl": "ldl", "apob": "apob", "hba1c": "hba1c", "hscrp": "crp_mgL", "egfr": "egfr",
             "trig": "trig", "hdl": "hdl", "sbp": "sbp", "vo2max": "vo2max", "testosterone": "total_testosterone"}


def _resolve_user_id(pid: int):
    """The app-user id behind a clinical patient, or None if it's a seed-only patient. pid==1 is the primary Vault."""
    if pid == 1:
        return 1
    try:
        from . import accounts as acctmod
        r = db.one("SELECT data FROM patients WHERE id = ?", (pid,))
        if not r:
            return None
        ref = (db.unj(r["data"], {}) or {}).get("user_ref")
        if ref is None:
            return None
        if str(ref).isdigit():
            return int(ref)
        # user_ref may be an email — resolve via the (separate) accounts DB, NOT the currently-bound one
        if acctmod.enabled():
            return acctmod.user_for_email(str(ref))
    except Exception:  # noqa: BLE001
        return None
    return None


@contextlib.contextmanager
def _patient_db(pid: int):
    """Bind to the patient's per-user DB for the duration, then restore. Yields True if a live DB was bound."""
    prev = db.db_path()
    live = False
    try:
        from . import accounts as acctmod
        uid = _resolve_user_id(pid)
        if uid is not None and acctmod.enabled():
            db.set_db(acctmod.user_db_path(uid))
            live = True
        elif pid == 1:
            live = True                        # primary Vault lives in the current/main DB
        yield live
    finally:
        db.set_db(prev if prev else None)


# ───────────────────────────── biomarkers (intake auto-fill) ─────────────────────────────
def _biomarkers_current() -> tuple[dict, list]:
    """Engine-keyed latest labs from the CURRENTLY BOUND DB (no re-binding)."""
    out: dict = {}
    raw: list[dict] = []
    from . import engine
    L = engine.latest_values() or {}
    try:
        from .catalog import MARKERS
    except Exception:  # noqa: BLE001
        MARKERS = {}
    for mid, rec in L.items():
        v = (rec or {}).get("value_num")
        if v is None:
            continue
        key = _MARKER_MAP.get(mid)
        if key and key not in out:
            out[key] = v
        name = MARKERS.get(mid, [mid])[0] if isinstance(MARKERS.get(mid), (list, tuple)) else mid
        raw.append({"marker": name, "id": mid, "value": v, "day": (rec or {}).get("collected_on")})
    p = engine.profile() or {}
    if p.get("sex"):
        out["sex"] = p["sex"]
    if p.get("height_cm"):
        out["height_cm"] = p["height_cm"]
    try:
        w = (engine.series("weight") or [(None, None)])[-1][1]
        if w:
            out["weight_kg"] = w
    except Exception:  # noqa: BLE001
        pass
    try:
        out["age"] = engine.age_on()
    except Exception:  # noqa: BLE001
        pass
    return out, raw


def biomarkers(pid: int) -> dict:
    """Flat, engine-keyed latest labs for a patient — the intake auto-fill. Falls back to the seed panel."""
    out, raw, source, as_of = {}, [], "seed", None
    with _patient_db(pid) as live:
        if live:
            try:
                out, raw = _biomarkers_current()
                if out:
                    source = "live_vault"
                    as_of = max((r["day"] for r in raw if r.get("day")), default=None)
            except Exception:  # noqa: BLE001
                pass
    if not out or source == "seed":
        s = db.unj((db.one("SELECT data FROM patients WHERE id = ?", (pid,)) or {"data": "{}"})["data"], {})
        for sk, key in _SEED_MAP.items():
            if s.get(sk) is not None and key not in out:
                out[key] = s[sk]
        r = db.one("SELECT age, sex FROM patients WHERE id = ?", (pid,))
        if r:
            out.setdefault("age", r["age"]); out.setdefault("sex", r["sex"])
        as_of = as_of or s.get("last_report")
    return {"markers": out, "raw": raw[:60], "source": source, "as_of": as_of,
            "note": "Latest value per marker. 'live_vault' = pulled from the patient's own record; 'seed' = the clinical panel on file."}


# ───────────────────────────── vitals / recovery / sleep / habits ─────────────────────────────
def _avg(points):
    vals = [p[1] if isinstance(p, (list, tuple)) else p.get("value") for p in points]
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else None


def _pct(points, p):
    vals = sorted(x[1] for x in points if (x[1] if isinstance(x, (list, tuple)) else None) is not None)
    return vals[max(0, min(len(vals) - 1, int(p * len(vals))))] if vals else None


def _vitals_current() -> dict:
    """Latest 7-day vitals trend + nocturnal SpO₂ min + resting HR, from the CURRENTLY BOUND DB."""
    try:
        from . import vitals
    except Exception:  # noqa: BLE001
        return {"available": False, "note": "vitals unavailable"}
    now, wk = int(time.time()), int(time.time()) - 7 * 86400
    metrics = {}
    for m in ("hr", "hrv", "spo2", "resp", "steps", "skin_temp"):
        try:
            s = vitals.series(m, wk, now, 2000)
        except Exception:  # noqa: BLE001
            s = {"points": [], "n": 0}
        if s.get("n"):
            metrics[m] = {"avg_7d": _avg(s["points"]), "n": s["n"]}
    spo2_min = rhr = None
    try:
        spo2_min = _pct(vitals.series("spo2", wk, now, 5000).get("points", []), 0.02)   # ~nocturnal dip
        spo2_min = round(spo2_min, 1) if spo2_min is not None else None
        rhr = _pct(vitals.series("hr", wk, now, 5000).get("points", []), 0.05)          # ~resting HR
        rhr = round(rhr) if rhr is not None else None
    except Exception:  # noqa: BLE001
        pass
    return {"available": bool(metrics), "window_days": 7, "metrics": metrics,
            "resting_hr": rhr, "nocturnal_spo2_min": spo2_min,
            "note": "7-day wearable trend on the shared clock; nocturnal SpO₂ min & resting HR are key sleep/recovery signals."}


def _recovery_current() -> dict:
    """Recovery = today's HRV vs this person's own 7-day HRV baseline (current DB)."""
    try:
        from . import vitals
        now = int(time.time())
        today = _avg(vitals.series("hrv", now - 86400, now, 2000).get("points", []))
        base = _avg(vitals.series("hrv", now - 7 * 86400, now, 5000).get("points", []))
        rec = min(100, max(0, round(100 * today / base))) if (today and base) else None
        return {"available": today is not None, "hrv_today": today, "hrv_baseline_7d": base, "recovery_pct": rec,
                "interpretation": ("above baseline — recovered" if rec and rec >= 100 else
                                   "below baseline — under-recovered" if rec and rec < 85 else
                                   "near baseline" if rec else "insufficient data"),
                "note": "vs the person's own 7-day HRV baseline, not a population norm."}
    except Exception:  # noqa: BLE001
        return {"available": False}


def _habits_current() -> dict:
    """Lifestyle signals the person controls (current DB)."""
    h = {}
    try:
        from . import engine
        p = engine.profile() or {}
        for k in ("smoker", "alcohol", "bp_treated", "statin"):
            h[k] = p.get(k)
        try:
            ex = engine.signal_baseline("exercise_min", days=30)
            h["exercise_min_per_day"] = round(ex["mean"], 1) if ex else None
        except Exception:  # noqa: BLE001
            pass
        try:
            from . import vitals
            now = int(time.time())
            st = vitals.series("steps", now - 7 * 86400, now, 5000)
            if st.get("n"):
                h["steps_per_day_7d"] = _avg(st["points"])
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass
    return {"available": any(v is not None for v in h.values()), **h}


def _organs_current() -> dict | None:
    """Per-organ ages from the bound DB's blood panel (organ clocks), or None if not enough data."""
    try:
        from .llx import organ_tools
        if not organ_tools.available():
            return None
        from . import telomy_ml
        panel = telomy_ml._panel()
        if len([k for k in panel if k not in ("age", "sex")]) < 4:
            return None
        return organ_tools.organ_ages(panel)
    except Exception:  # noqa: BLE001
        return None


def _environment_current() -> dict | None:
    """The exposome for the bound person's city (air/social/noise/UV/water/food)."""
    try:
        from . import exposome, engine
        city = (engine.profile() or {}).get("city")
        return exposome.exposome_profile(name=city) if city else None
    except Exception:  # noqa: BLE001
        return None


def vitals_summary(pid: int) -> dict:
    with _patient_db(pid) as live:
        return _vitals_current() if live else {"available": False, "note": "No wearable data linked for this patient."}


def recovery_sleep(pid: int) -> dict:
    with _patient_db(pid) as live:
        return _recovery_current() if live else {"available": False}


def habits(pid: int) -> dict:
    with _patient_db(pid) as live:
        return _habits_current() if live else {"available": False}


# ───────────────────────────── the 360 overview + grounded AI narrative ─────────────────────────────
def _risk(pid: int, bm: dict) -> dict:
    """Run the risk models from the patient's real labs when available, else their seed snapshot."""
    try:
        from . import predict, roles
        with _patient_db(pid) as live:
            if live and pid != 1:
                try:
                    snap = predict.inputs_from_vault()
                    return predict.run(snap)["models"] if snap.get("age") else roles.predictions(pid)["models"]
                except Exception:  # noqa: BLE001
                    pass
        return roles.predictions(pid)["models"]
    except Exception:  # noqa: BLE001
        return {}


def _narrative(ident, bm, vit, rec, hab, rep, models) -> str:
    """Deterministic grounded composer — every clause traces to a value above. Draft for clinician review."""
    L = []
    L.append(f"{ident['name']}, {ident['age']} {ident.get('sex') or ''}".strip() +
             (f", {ident['city']}" if ident.get("city") else "") + ". " +
             (f"Conditions: {', '.join(ident['conditions'])}." if ident.get("conditions") else "No conditions recorded."))
    m = bm.get("markers", {})
    key_labs = [(k, m[k]) for k in ("apob", "ldl", "hba1c", "crp_mgL", "trig", "egfr", "vitamin_d_25oh") if k in m]
    if key_labs:
        L.append("Latest labs — " + ", ".join(f"{k.replace('_',' ')} {v}" for k, v in key_labs) +
                 (f" (as of {bm['as_of']})" if bm.get("as_of") else "") + ".")
    if models:
        cvd = (models.get("cvd") or {}).get("risk")
        dm = (models.get("diabetes") or {})
        liver = (models.get("liver") or {}).get("score")
        parts = []
        if cvd is not None:
            parts.append(f"10-yr CVD {cvd}%")
        if dm.get("already"):
            parts.append("HbA1c in diabetes range")
        elif dm.get("risk") is not None:
            parts.append(f"5-yr diabetes {dm['risk']}%")
        if liver is not None:
            parts.append(f"FIB-4 {liver}")
        if parts:
            L.append("Risk models: " + "; ".join(parts) + ".")
    if rec.get("available") and rec.get("recovery_pct") is not None:
        L.append(f"Recovery {rec['recovery_pct']}% ({rec['interpretation']}); HRV {rec.get('hrv_today')} vs 7-day {rec.get('hrv_baseline_7d')}" +
                 (f"; resting HR {vit.get('resting_hr')}" if vit.get("resting_hr") else "") +
                 (f"; nocturnal SpO₂ min {vit.get('nocturnal_spo2_min')}%" if vit.get("nocturnal_spo2_min") else "") + ".")
    if hab.get("available"):
        hb = []
        if hab.get("steps_per_day_7d"):
            hb.append(f"{int(hab['steps_per_day_7d'])} steps/day")
        if hab.get("exercise_min_per_day") is not None:
            hb.append(f"{hab['exercise_min_per_day']} min activity/day")
        if hab.get("smoker"):
            hb.append("smoker")
        if hb:
            L.append("Habits: " + ", ".join(hb) + ".")
    if rep:
        flagged = sum(1 for r in rep if r.get("flagged"))
        L.append(f"{len(rep)} report(s) on file" + (f", {flagged} with results outside range" if flagged else "") + ".")
    L.append("Evidence-graded interventions and the protein/fibre/fat fix follow in Longevity Rx; everything is a "
             "draft for your review and sign-off.")
    return " ".join(L)


def overview(pid: int) -> dict:
    """The one-screen 360 for the clinic (and the member's own screen): all domains + a grounded AI summary."""
    r = db.one("SELECT * FROM patients WHERE id = ?", (pid,))
    if not r:
        return {"error": "patient not found"}
    s = db.unj(r["data"], {})
    ident = {"id": pid, "name": r["name"], "age": round(r["age"]) if r["age"] else None, "sex": r["sex"],
             "city": r["city"], "conditions": s.get("conditions") or [], "linked": _resolve_user_id(pid) is not None}
    bm = biomarkers(pid)
    vit = vitals_summary(pid)
    rec = recovery_sleep(pid)
    hab = habits(pid)
    try:
        from . import summaries
        with _patient_db(pid):
            rep = summaries.patient_reports(pid) if pid == 1 else []
    except Exception:  # noqa: BLE001
        rep = []
    with _patient_db(pid) as live:
        organs = _organs_current() if live else None
        environment = _environment_current() if live else None
    models = _risk(pid, bm)
    narrative = _narrative(ident, bm, vit, rec, hab, rep, models)
    return {
        "patient": ident,
        "organs": organs,
        "environment": environment,
        "ai_summary": {"text": narrative,
                       "drafted_by": "Telomy grounded composer — every statement traces to a value in the patient's record",
                       "disclaimer": "Draft for clinician review and sign-off. Not a diagnosis. Review for omissions before acting."},
        "biomarkers": bm,
        "vitals": vit,
        "recovery_sleep": rec,
        "habits": hab,
        "risk_models": models,
        "reports": [{"id": x["id"], "title": x["title"], "panel_title": x.get("panel_title"), "collected_on": x["collected_on"],
                     "flagged": x.get("flagged"), "headline": x.get("headline")} for x in rep][:10],
        "as_of": bm.get("as_of"),
        "data_sources": {"biomarkers": bm["source"], "vitals": vit.get("available", False),
                         "recovery": rec.get("available", False), "habits": hab.get("available", False),
                         "reports": len(rep)},
    }


def overview_me() -> dict:
    """The same 360 for the signed-in MEMBER, read from their already-bound DB (no re-binding) — so the patient's
    own app screen shows exactly what the clinic sees. 'as before' + the combined summary + AI narrative."""
    try:
        from . import engine
        p = engine.profile() or {}
        ident = {"id": "me", "name": p.get("name") or "You",
                 "age": (round(engine.age_on()) if hasattr(engine, "age_on") else p.get("age")),
                 "sex": p.get("sex"), "city": p.get("city"), "conditions": p.get("conditions") or [], "linked": True}
        out, raw = _biomarkers_current()
        as_of = max((r["day"] for r in raw if r.get("day")), default=None)
        bm = {"markers": out, "raw": raw[:60], "source": "live_vault", "as_of": as_of}
    except Exception:  # noqa: BLE001
        return {"error": "no profile for this member"}
    vit, rec, hab = _vitals_current(), _recovery_current(), _habits_current()
    try:
        from . import summaries
        rep = summaries.patient_reports(1)
    except Exception:  # noqa: BLE001
        rep = []
    try:
        from . import predict
        snap = predict.inputs_from_vault()
        models = predict.run(snap)["models"] if snap.get("age") else {}
    except Exception:  # noqa: BLE001
        models = {}
    narrative = _narrative(ident, bm, vit, rec, hab, rep, models)
    return {
        "patient": ident,
        "organs": _organs_current(),
        "environment": _environment_current(),
        "ai_summary": {"text": narrative,
                       "drafted_by": "Telomy grounded composer — every statement traces to a value in your record",
                       "disclaimer": "An at-a-glance summary of your own data. Not a diagnosis; your clinician reviews it."},
        "biomarkers": bm, "vitals": vit, "recovery_sleep": rec, "habits": hab, "risk_models": models,
        "reports": [{"id": x["id"], "title": x["title"], "panel_title": x.get("panel_title"), "collected_on": x["collected_on"],
                     "flagged": x.get("flagged"), "headline": x.get("headline")} for x in rep][:10],
        "as_of": bm.get("as_of"),
        "data_sources": {"biomarkers": bm["source"], "vitals": vit.get("available", False),
                         "recovery": rec.get("available", False), "habits": hab.get("available", False), "reports": len(rep)},
    }
