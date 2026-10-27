"""Consult scribe — a patient-visit transcript → a clinician SOAP note, a plain-language patient recap, and
structured action drafts (medications, tests, follow-up, tasks) the clinician reviews and signs.

Design: actions are extracted DETERMINISTICALLY by matching the live catalogs + a few verb/time patterns, so the
'apply' flow (prescribe / order test / book follow-up / add task) works with or without an LLM. The SOAP and recap
NARRATIVE use the grounded LLM when a provider key is set (telomy_llm), else a composed template from the same
structure. Nothing is applied until the clinician taps apply — mirrors the rest of the staff app.
"""
import re
from datetime import datetime, timedelta

from . import db, diagnostics, engine, rx, telomy_llm

SCHEMA = """CREATE TABLE IF NOT EXISTS consult_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, doctor TEXT,
  transcript TEXT, soap TEXT, recap TEXT, actions TEXT, applied TEXT);"""


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


# ---- extraction patterns -----------------------------------------------------
_FOLLOWUP = re.compile(r"\b(?:follow[-\s]?up|review|come back|see (?:you|me)|recheck|re-?check|revisit|next visit)\b[^.?!]*?\bin\s+(\d+)\s*(day|days|week|weeks|month|months)", re.I)
_MEAS = re.compile(r"\b\d{1,3}(?:[./]\d{1,3})?\s?(mmhg|bpm|kg|cm|mg/dl|mmol|%|°c|/min|ml|beats)\b", re.I)
_SYMPTOM = re.compile(r"\b(pain|ache|tired|fatigue|dizz|nausea|breath|cough|fever|headache|sleep|stress|anxious|palpitation|swelling|numb|weak|cramp|bloat|reflux|constipat|diarr)\w*", re.I)
_IMPRESS = re.compile(r"\b(diagnos|assessment|impression|likely|consistent with|suggestive of|rule out|differential|appears to be|looks like)\b", re.I)
# common generic drug stems not in the formulary, so a mention still becomes a (free-text) medication draft
_GENERIC_DRUGS = ["atorvastatin", "rosuvastatin", "statin", "metformin", "telmisartan", "amlodipine", "losartan",
                  "ramipril", "aspirin", "clopidogrel", "pantoprazole", "omeprazole", "levothyroxine", "thyroxine",
                  "vitamin d", "vitamin b12", "b12", "folate", "iron", "calcium", "magnesium", "semaglutide",
                  "ozempic", "insulin", "glimepiride", "sitagliptin", "ezetimibe", "paracetamol", "ibuprofen"]


def _med_index():
    idx = []  # (matchtoken, product_key, name)
    for key, p in rx.PRODUCTS.items():
        tok = p["name"].lower().replace("telomy formulas · ", "").split("(")[0].split("·")[0].strip()
        first = tok.split()[0] if tok else ""
        if len(first) >= 4:
            idx.append((first, key, p["name"]))
    return idx


def extract_actions(transcript: str) -> list[dict]:
    low = " " + transcript.lower() + " "
    acts: list[dict] = []
    seen: set[str] = set()

    # tests — match the catalog
    for t in diagnostics.catalogue():
        core = t["name"].lower().split("(")[0].strip()
        if len(core) >= 4 and core in low and t["id"] not in seen:
            seen.add(t["id"])
            acts.append({"type": "test", "ref": t["id"], "label": t["name"], "detail": t.get("category", ""), "selected": True})

    # medications — formulary first (gives an apply-able id), then generic stems (free-text draft)
    for first, key, name in _med_index():
        if first in low and key not in seen:
            seen.add(key)
            acts.append({"type": "medication", "ref": key, "label": name, "detail": rx.PRODUCTS[key].get("dose", ""), "selected": True})
    for g in _GENERIC_DRUGS:
        if g in low and f"drug:{g}" not in seen and not any(g.split()[0] in a["label"].lower() for a in acts if a["type"] == "medication"):
            seen.add(f"drug:{g}")
            acts.append({"type": "medication", "ref": None, "label": g.title(), "detail": "mentioned in the consult — confirm drug, dose & route", "selected": False})

    # follow-up
    m = _FOLLOWUP.search(transcript)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        days = n * (1 if unit.startswith("day") else 7 if unit.startswith("week") else 30)
        acts.append({"type": "followup", "ref": str(days), "label": f"Follow-up in {n} {unit}", "detail": f"≈ {days} days", "selected": True})

    # tasks — explicit instructions to the team/patient
    for s in _sentences(transcript):
        if re.search(r"\b(remind|make sure|ensure|schedule|arrange|refer|send|share|call|advise the patient to|patient should)\b", s, re.I) and len(s) < 160:
            acts.append({"type": "task", "ref": None, "label": s.strip().rstrip("."), "detail": "", "selected": False})
    return acts[:20]


def _sentences(text: str):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _soap_template(transcript: str, actions: list[dict]) -> dict:
    sents = _sentences(transcript)
    subj = [s for s in sents if _SYMPTOM.search(s)][:6]
    obj = [s for s in sents if _MEAS.search(s)][:6]
    assess = [s for s in sents if _IMPRESS.search(s)][:4]
    plan = []
    for a in actions:
        if a["type"] == "medication": plan.append(f"Prescribe {a['label']}" + (f" — {a['detail']}" if a['detail'] else ""))
        elif a["type"] == "test": plan.append(f"Order {a['label']}")
        elif a["type"] == "followup": plan.append(a["label"])
        elif a["type"] == "task": plan.append(a["label"])
    return {"subjective": subj or ["(see transcript)"], "objective": obj or ["No measurements captured in the transcript."],
            "assessment": assess or ["(clinician to complete)"], "plan": plan or ["(clinician to complete)"]}


def _recap_template(actions: list[dict]) -> str:
    rxs = [a["label"] for a in actions if a["type"] == "medication" and a["selected"]]
    tests = [a["label"] for a in actions if a["type"] == "test" and a["selected"]]
    fu = next((a["label"] for a in actions if a["type"] == "followup"), None)
    parts = ["Here's a summary of your visit."]
    if rxs: parts.append("Your doctor prescribed: " + ", ".join(rxs) + ".")
    if tests: parts.append("Tests to get done: " + ", ".join(tests) + ".")
    if fu: parts.append(fu + ".")
    if not rxs and not tests and not fu:
        parts.append("No new prescriptions or tests — your doctor's notes are in your record.")
    parts.append("Everything your doctor orders appears in your app so you can act on it.")
    return " ".join(parts)


def _llm_narrative(transcript: str, patient: dict | None) -> dict | None:
    ctx = (f"PATIENT: {patient.get('name','')}, {patient.get('age','?')}y {patient.get('sex','')}. "
           f"Conditions: {', '.join(patient.get('conditions') or []) or 'none recorded'}.\n\n" if patient else "")
    ctx += "CONSULT TRANSCRIPT:\n" + transcript[:6000]
    sys = ("You are a medical scribe. From the consult transcript, write a concise SOAP note for the clinician. "
           "Use only facts stated in the transcript; do not invent values, drugs, doses or diagnoses. "
           "Sections: Subjective, Objective, Assessment, Plan. Keep it tight and clinical.")
    soap = telomy_llm.ask(sys, ctx, "Write the SOAP note.", [], {"type": "object"}, max_tokens=1200, timeout=25)
    if not soap or soap.get("_error") or not soap.get("answer"):
        return None
    sys2 = ("You are explaining a medical visit to the patient in warm, plain language (8th-grade reading level). "
            "Use only what the transcript supports. 4-6 short sentences: what was discussed, what the doctor decided, "
            "and what the patient should do next. No medical jargon, no invented facts.")
    recap = telomy_llm.ask(sys2, ctx, "Write the patient recap.", [], {"type": "object"}, max_tokens=500, timeout=20)
    return {"soap_text": soap["answer"].strip(),
            "recap": (recap["answer"].strip() if recap and recap.get("answer") else None),
            "engine": soap.get("engine")}


def scribe(transcript: str, doctor: str, patient: dict | None = None) -> dict:
    """Turn a transcript into a stored consult with SOAP, patient recap and action drafts."""
    init()
    transcript = (transcript or "").strip()
    actions = extract_actions(transcript)
    llm = _llm_narrative(transcript, patient) if transcript else None
    if llm and llm.get("soap_text"):
        soap = {"narrative": llm["soap_text"], "engine": llm.get("engine")}
    else:
        soap = _soap_template(transcript, actions)
    recap = (llm["recap"] if llm and llm.get("recap") else None) or _recap_template(actions)
    cid = db.exec_("INSERT INTO consult_notes (ts, doctor, transcript, soap, recap, actions, applied) VALUES (?,?,?,?,?,?,?)",
                   (engine.now_iso(), doctor, transcript, db.j(soap), recap, db.j(actions), db.j([])))
    return get(cid)


def get(cid: int) -> dict | None:
    r = db.one("SELECT * FROM consult_notes WHERE id = ?", (cid,))
    if not r:
        return None
    r["soap"] = db.unj(r["soap"], {}); r["actions"] = db.unj(r["actions"], []); r["applied"] = db.unj(r["applied"], [])
    return r


def recent(limit: int = 20) -> list[dict]:
    out = []
    for r in db.rows("SELECT id, ts, doctor, recap, actions, applied FROM consult_notes ORDER BY id DESC LIMIT ?", (limit,)):
        r["actions"] = db.unj(r["actions"], []); r["applied"] = db.unj(r["applied"], [])
        r["n_actions"] = len(r["actions"]); r["n_applied"] = len(r["applied"])
        out.append(r)
    return out
