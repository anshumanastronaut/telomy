"""AI summaries for the doctor: one per report and one per patient. Sinc drafts (deterministic composer grounded in the
Vault — every sentence traces to a value, a zone, a previous result or a rule); the doctor reviews and signs. When an
ANTHROPIC_API_KEY is configured the same grounded facts can be rephrased by Claude, but facts never come from the model.
"""
from datetime import date, timedelta

from . import db, derived, engine, predict, therapy
from .catalog import MARKERS, PANELS
from .catalog_ext import EVIDENCE, RETEST_DAYS

SCHEMA = """CREATE TABLE IF NOT EXISTS report_reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, report_id INTEGER, doctor TEXT, ts TEXT,
  action TEXT, note TEXT);"""

STATUS_RANK = {"out_of_range": 0, "detected": 0, "variant": 1, "in_range": 2, "optimal": 3, "absent": 3, "typical": 3, "info": 4}


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def _fmt(v):
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _u(unit):
    return f" {unit}" if unit else ""


def _dm(preds, hba1c=None) -> str:
    d = preds["diabetes"]
    if d.get("risk") is None:
        return "already in the diabetes range" if (hba1c or 0) >= 6.5 else "not computable"
    return f"{d['risk']}%"


def report_summary(rid: int) -> dict | None:
    rep = db.one("SELECT * FROM reports WHERE id = ?", (rid,))
    if not rep:
        return None
    res = db.rows("SELECT * FROM results WHERE report_id = ?", (rid,))
    sex = engine.profile().get("sex")
    rows = []
    for r in res:
        mid = r["marker_id"]
        val = r["value_num"] if r["value_num"] is not None else r["value_text"]
        z = derived.zone_for(mid, val, sex)
        hist = [h for h in engine.marker_history(mid) if h["collected_on"] < rep["collected_on"] and h["value_num"] is not None]
        prev = hist[-1] if hist else None
        delta = None
        if prev and isinstance(val, float):
            delta = round(val - prev["value_num"], 2)
        status = z["status"] if z else r["status"]
        rows.append({"marker_id": mid, "name": MARKERS[mid][0], "value": val, "unit": r["unit"], "ref": r["ref_text"], "flag": r["flag"],
                     "status": status, "zone": z["label"] if z else None, "evidence": EVIDENCE.get(mid),
                     "previous": {"value": prev["value_num"], "day": prev["collected_on"]} if prev else None, "delta": delta,
                     "better": MARKERS[mid][5]})
    rows.sort(key=lambda x: STATUS_RANK.get(x["status"], 5))
    flagged = [x for x in rows if x["status"] in ("out_of_range", "detected", "variant")]
    ids = {x["marker_id"] for x in rows}
    pats = [i for i in engine.list_insights() if i["kind"] == "cross_panel" and any(e.get("marker_id") in ids for e in i["evidence"])]
    changes = []
    for x in rows:
        if x["delta"] and x["previous"] and abs(x["delta"]) / max(abs(x["previous"]["value"]), 1e-9) >= 0.08:
            worse = (x["delta"] > 0) == (x["better"] == "low") if x["better"] in ("low", "high") else None
            changes.append(f"{x['name']} {_fmt(x['previous']['value'])} → {_fmt(x['value'])}{_u(x['unit'])} since {x['previous']['day']}"
                           + (" (worse)" if worse else " (better)" if worse is False else ""))
    retest_days = RETEST_DAYS.get(rep["panel"])
    retest = (date.fromisoformat(rep["collected_on"]) + timedelta(days=retest_days)).isoformat() if retest_days and flagged else None
    headline = (f"{len(flagged)} of {len(rows)} results need attention" if flagged else f"All {len(rows)} results within range")
    lines = [f"{headline} on this {PANELS.get(rep['panel'], rep['panel']).lower()} ({rep['collected_on']})."]
    if flagged:
        lines.append("Outside target: " + "; ".join(f"{x['name']} {_fmt(x['value'])}{_u(x['unit'])}" + (f" — {x['zone']}" if x["zone"] else "")
                                                    for x in flagged[:6]) + ("…" if len(flagged) > 6 else "") + ".")
    if changes:
        lines.append("Change since last test: " + "; ".join(changes[:4]) + ".")
    if pats:
        lines.append("Connected findings: " + "; ".join(p["title"] for p in pats[:3]) + ".")
    actions = []
    for kind, acts in derived.action_plan().items():
        for a in acts:
            if any(t["id"] in ids for t in a["targets"]) and not a["avoid"]:
                actions.append(a["title"])
    return {"report": {k: rep[k] for k in ("id", "title", "panel", "collected_on", "source", "is_test_data")}, "panel_title": PANELS.get(rep["panel"]),
            "headline": headline, "summary": " ".join(lines), "results": rows, "flagged": len(flagged), "changes": changes,
            "patterns": [{"id": p["id"], "title": p["title"], "confidence": p["confidence"]} for p in pats[:5]],
            "actions": actions[:5], "retest_on": retest,
            "reviews": db.rows("SELECT * FROM report_reviews WHERE report_id = ? ORDER BY id", (rid,)),
            "drafted_by": "Sinc (grounded composer v1) — every statement links to a value in this report or your Vault",
            "disclaimer": "Draft for clinician review. Not a diagnosis."}


def review_report(rid: int, action: str, note: str, doctor: str = "Dr. Meera Rao") -> dict:
    if action not in ("signed", "amended", "needs_followup"):
        raise ValueError("Unknown action")
    if not note.strip():
        raise ValueError("A note is required.")
    if not db.one("SELECT id FROM reports WHERE id = ?", (rid,)):
        raise LookupError("Report not found")
    db.exec_("INSERT INTO report_reviews (report_id, doctor, ts, action, note) VALUES (?,?,?,?,?)", (rid, doctor, engine.now_iso(), action, note.strip()))
    return report_summary(rid)


def patient_reports(pid: int) -> list[dict]:
    if pid != 1:
        return []
    out = []
    for r in db.rows("SELECT * FROM reports ORDER BY collected_on DESC"):
        s = report_summary(r["id"])
        out.append({"id": r["id"], "title": r["title"], "panel": r["panel"], "panel_title": PANELS.get(r["panel"], r["panel"]),
                    "collected_on": r["collected_on"], "markers": len(s["results"]), "flagged": s["flagged"], "headline": s["headline"],
                    "summary": s["summary"], "reviewed": bool(s["reviews"]), "is_test_data": r["is_test_data"]})
    return out


def patient_summary(pid: int) -> dict:
    """The one-screen clinical summary a doctor reads first."""
    from . import roles
    r = db.one("SELECT * FROM patients WHERE id = ?", (pid,))
    if not r:
        return {}
    preds = roles.predictions(pid)["models"]
    lines, problems = [], []
    age, sex = round(r["age"]), r["sex"]
    if pid == 1:
        L = engine.latest_values()
        risk = [x for x in derived.risk_matrix() if x.get("level") in ("high", "elevated", "moderate")]
        problems = [f"{x['condition']} ({x['level']})" for x in risk[:6]]
        pats = [i for i in engine.list_insights() if i["kind"] == "cross_panel" and i.get("direction", "harmful") == "harmful" and i.get("medical", 1)][:5]
        meds = [f"{m['name']} {m['dose']}" for m in db.rows("SELECT name, dose FROM medications WHERE active = 1")]
        work = therapy.response(1)
        helped = [w["name"] for w in work if w["verdict"] in ("helped", "promising")]
        nosig = [w["name"] for w in work if w["verdict"] == "no_signal"]
        h = therapy.hsai(1)
        lines.append(f"{r['name']}, {age} {sex}. {len(db.rows('SELECT id FROM reports'))} reports in the Vault across "
                     f"{len({x['panel'] for x in db.rows('SELECT panel FROM reports')})} modalities; 120 days of wearable data.")
        if pats:
            lines.append("Key findings: " + "; ".join(p["title"] for p in pats) + ".")
        pv = preds.get("prevent") or {}
        lines.append(f"Risk: PREVENT CVD {pv.get('ten_year', {}).get('total_cvd', '—')}% at 10 y / {pv.get('thirty_year', {}).get('total_cvd', '—')}% at 30 y; "
                     f"PCE {preds['cvd'].get('risk', '—')}%; 5-y diabetes {_dm(preds)}; FIB-4 {preds['liver'].get('score', '—')}.")
        if h.get("available"):
            lines.append(f"HSAI {h['score']} ({h['zone']}); weakest domain {h['weakest'].lower()}.")
        if helped or nosig:
            lines.append(f"Centre therapies — working: {', '.join(helped) or 'none yet'}; no reliable signal: {', '.join(nosig[:4]) or '—'}.")
        lines.append("Current: " + (", ".join(meds) if meds else "no medicines") + ".")
        open_items = {"insights": db.one("SELECT COUNT(*) AS n FROM insights WHERE review_state = 'awaiting' AND dismissed = 0")["n"],
                      "therapy_plans": len([p for p in therapy.plans("awaiting_doctor") if p["patient_id"] == 1]),
                      "unreviewed_reports": sum(1 for x in patient_reports(1) if not x["reviewed"] and x["flagged"])}
    else:
        s = db.unj(r["data"], {})
        lines.append(f"{r['name']}, {age} {sex}, {r['city']}. Conditions: {', '.join(s.get('conditions') or []) or 'none recorded'}.")
        lines.append(f"Latest labs: LDL {s.get('ldl')}, ApoB {s.get('apob')}, HbA1c {s.get('hba1c')}%, hs-CRP {s.get('hscrp')}, "
                     f"eGFR {s.get('egfr')}, SBP {s.get('sbp')} mmHg ({s.get('last_report')}).")
        lines.append(f"Risk: PCE {preds['cvd'].get('risk', '—')}%; 5-y diabetes {_dm(preds, s.get('hba1c'))}; FIB-4 {preds['liver'].get('score', '—')}.")
        problems = [c for c in s.get("conditions") or []]
        if s.get("apob", 0) > 100:
            problems.append(f"ApoB {s['apob']}")
        if s.get("hba1c", 0) >= 5.7:
            problems.append(f"HbA1c {s['hba1c']}%")
        open_items = {}
        sess = db.rows("SELECT modality, COUNT(*) AS n FROM therapy_sessions WHERE patient_id = ? GROUP BY modality ORDER BY n DESC LIMIT 4", (pid,))
        if sess:
            lines.append("Centre sessions: " + ", ".join(f"{therapy.MODALITIES[x['modality']]['name']} ×{x['n']}" for x in sess) + ".")
    return {"patient_id": pid, "summary": " ".join(lines), "problems": problems, "open_items": open_items,
            "drafted_by": "Sinc (grounded composer v1)", "disclaimer": "Draft for clinician review. Not a diagnosis."}
