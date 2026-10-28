"""Telomy clinical & operations copilot — grounded, propose-don't-act.

It covers the full span of what a doctor and a centre admin actually ask (researched taxonomy):

  DOCTOR (per patient, or panel-wide):
    summary · labs · trends · risk/prognosis · therapeutics(Rx) · interactions · orders/retest · findings-to-review
    · care-plan(the patient's app) · medications · evidence/guideline lookup · panel triage ("who needs me")
  CENTRE (operations):
    status/today · revenue & outstanding · bookings/schedule/no-shows · floor/equipment/utilisation · members/retention
    · staff/team performance · doctors on shift

Design invariants:
  * READ + DRAFT only. Every side-effect (prescribe, sign, order, edit, book, charge) happens in the existing approve
    flows; the copilot only answers and drafts next steps that route there.
  * GROUNDED. An answer is built from a structured context assembled out of the engines. With an LLM configured
    (telomy_llm) it answers conversationally over that context under the number-grounding guard; otherwise a per-intent
    deterministic composer answers from the same structured data. Evidence answers are clearly general, cited, and
    flagged "review for this patient".
  * AUDITABLE. Every call → copilot_log on the mgmt DB.
"""
from __future__ import annotations

from datetime import datetime

from . import db, telomy_llm

# --------------------------------------------------------------------------- prompts & schema

DOCTOR_SYSTEM = (
    "You are Telomy's clinical copilot, assisting a licensed doctor. Answer ONLY from the CONTEXT, which is this "
    "patient's own record (or your panel). Never invent numbers, labs or doses — if it isn't in the CONTEXT, say so. "
    "You DRAFT; the doctor decides and signs. If asked to change, order or prescribe, describe the proposed change — "
    "never claim it's done. Be concise and clinical, cite the specific values you use, and flag what needs judgement. "
    "Decision support, not a diagnosis."
)
CENTRE_SYSTEM = (
    "You are Telomy's operations copilot for a wellness-centre admin. Answer ONLY from the CONTEXT (this centre's own "
    "members, schedule, floor, revenue, staff). Never invent numbers. You DRAFT and inform; any booking, charge or "
    "change is made by the admin in the console. Be concise and practical."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
        "medical": {"type": "boolean"},
    },
    "required": ["answer", "confidence", "medical"],
    "additionalProperties": True,
}

DISCLAIMER = "Draft decision support from the patient's own record. Not a diagnosis — review and sign off."


# --------------------------------------------------------------------------- audit log

def _ensure_log():
    db.exec_("""CREATE TABLE IF NOT EXISTS copilot_log (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, who TEXT,
                org TEXT, scope TEXT, intent TEXT, patient_id INTEGER, query TEXT, engine TEXT, grounded INTEGER)""")


def _log(me: dict, scope: str, intent: str, patient_id, query: str, engine: str, grounded: bool):
    try:
        _ensure_log()
        db.exec_("INSERT INTO copilot_log (at, who, org, scope, intent, patient_id, query, engine, grounded) VALUES (?,?,?,?,?,?,?,?,?)",
                 (datetime.now().isoformat(), me.get("name"), me.get("org"), scope, intent, patient_id,
                  (query or "")[:400], engine, 1 if grounded else 0))
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- intent classification

def _has(s: str, *ws: str) -> bool:
    return any(w in s for w in ws)


def classify_doctor(q: str, has_patient: bool) -> str:
    s = (q or "").lower()
    if _has(s, "what can you", "who are you", "what do you do", "how do you work", "what can i ask", "help me use"):
        return "capabilities"
    if _has(s, "evidence", "guideline", "study", "studies", "research", "literature", "trial", "what does the", "recommended for"):
        return "evidence"
    if _has(s, "interact", "contraindic", "safe with", "safe to take", "safe to start", "safe to add", "together with"):
        return "interaction"
    if _has(s, "prescrib", " rx", "supplement", "statin", "start them on", "put them on", "what should i give", "treatment", "medicate", "berberine", "metformin for", "what should i start"):
        return "therapeutics"
    # orders — note: do NOT use bare "test" (matches "la-test-") ; use explicit order/retest phrasing
    if _has(s, "retest", "re-test", "recheck", "monitor", "follow up", "follow-up", "order", "scan", "imaging", "when should", "come back", "bloodwork", "blood work", "blood test", "which bloods"):
        return "orders"
    if _has(s, "care plan", "care-config", "careplan", "their app", "focus on", "target", "track", "set their", "set up their", "customis", "customiz", "prioriti", "what should i do"):
        return "careplan"
    if _has(s, "risk", "cvd", "cardiovascular", "diabetes risk", "prognos", "fib-4", "fib4", "kidney", "egfr score", "likelihood", "chance", "how likely"):
        return "risk"
    if _has(s, "awaiting", "to review", "sign off", "sign-off", "queue", "findings", "flagged for review", "waiting for my", "open finding"):
        return "findings"
    if _has(s, "medication", "meds", "taking", "on any", "drug list", "pills", "adheren"):
        return "medication"
    if _has(s, "lab", "apob", "ldl", "hba1c", "glucose", "crp", "marker", "value", "trend", "latest", "result", "cholesterol", "egfr", "vitamin", "level", "bloods", "in range", "flagged", "panel"):
        return "labs"
    if not has_patient and _has(s, "who needs", "high risk", "high-risk", "triage", "worst", "most", "which patient", "across", "red flag", "see first"):
        return "panel"
    if _has(s, "weather", "joke", "football", "cricket", "movie", "song", "sport", "politics", "stock"):
        return "offtopic"
    return "summary"


def classify_centre(q: str) -> str:
    s = (q or "").lower()
    if _has(s, "revenue", "outstanding", "paid", "invoice", "collect", "money", "earn", "income", "pending payment", "dues", "due"):
        return "revenue"
    if _has(s, "no-show", "no show", "noshow", "gap", "availab", "slot", "book", "schedule", "appointment", "this week", "today's"):
        return "bookings"
    if _has(s, "floor", "machine", "equipment", "room", "servic", "utilis", "utiliz", "busy", "free", "hbot", "sauna", "device", "down", "offline"):
        return "floor"
    if _has(s, "member", "churn", "renew", "sign up", "sign-up", "active", "freeze", "retention", "new "):
        return "members"
    if _has(s, "staff", "team", "performance", "therapist", "by staff", "trainer"):
        return "staff"
    if _has(s, "doctor", "clinician", "physician"):
        return "doctors"
    return "status"


# --------------------------------------------------------------------------- evidence mini-KB (general, cited)

_EVIDENCE = [
    (("apob", "ldl", "cholesterol", "statin", "lipid", "dyslip"),
     "ApoB/LDL are causal for atherosclerotic CVD and lowering them lowers events; ApoB captures residual risk better than LDL-C. For raised ApoB with elevated risk, statin ± ezetimibe to target is first-line.",
     "AHA/ACC & ESC/EAS dyslipidaemia guidance"),
    (("hba1c", "a1c", "glucose", "prediabet", "diabetes", "metformin", "insulin resist"),
     "HbA1c 5.7–6.4% is prediabetes. Intensive lifestyle (5–7% weight loss, ~150 min/wk activity) cut progression by ~58% and metformin by ~31% in the DPP. HbA1c ≥6.5% on two tests defines diabetes.",
     "ADA Standards of Care; Diabetes Prevention Program"),
    (("crp", "inflammation", "hs-crp", "hscrp"),
     "hs-CRP marks residual inflammatory risk; >3 mg/L is high. It complements ApoB — address lifestyle and, where indicated, anti-inflammatory risk reduction.",
     "ACC/AHA; CANTOS"),
    (("vo2", "cardiorespiratory", "fitness", "vo2max", "zone 2", "zone-2", "zone2"),
     "VO₂max is among the strongest predictors of all-cause mortality; even moving from low to below-average fitness markedly lowers risk. Build it with a Zone-2 base plus weekly VO₂max intervals.",
     "JAMA 2018 — cardiorespiratory fitness & mortality"),
    (("sleep apnea", "apnoea", "osa", "ahi", "snore"),
     "Untreated OSA worsens blood pressure, glucose, HRV and cardiovascular risk. A high STOP-BANG or low overnight SpO₂ warrants a sleep study; CPAP improves daytime function and BP.",
     "AASM"),
    (("vitamin d", "25-oh", "25oh"),
     "Correct deficiency (<20 ng/mL). Routine high-dose supplementation in replete adults did not reduce CV or cancer events (VITAL) — target sufficiency, don't megadose.",
     "VITAL trial"),
    (("omega", "epa", "dha", "fish oil"),
     "Prescription EPA lowered CV events in high-risk patients with high triglycerides (REDUCE-IT); evidence for low-dose OTC fish oil is mixed.",
     "REDUCE-IT"),
    (("lp(a)", "lipoprotein a", "lpa"),
     "Lp(a) is largely genetic and an independent CVD risk factor — measure once. No approved lowering drug yet, so manage total ApoB-driven risk aggressively.",
     "EAS Lp(a) consensus"),
    (("resistance", "sarcopenia", "muscle", "strength", "almi", "protein"),
     "Resistance training (≥2 sessions/wk) preserves muscle and ALMI, slows age-related sarcopenia and improves insulin sensitivity; pair with adequate protein.",
     "Physical Activity Guidelines"),
    (("fib-4", "fib4", "liver", "fatty liver", "nafld", "mash", "masld", "steatosis"),
     "FIB-4 stratifies fibrosis risk in fatty liver: <1.3 low, 1.3–2.67 indeterminate (consider elastography), >2.67 high. First-line is weight loss and metabolic control.",
     "AASLD MASLD guidance"),
    (("egfr", "kidney", "ckd", "kfre", "creatinine", "uacr"),
     "Confirm CKD with eGFR plus uACR; KFRE estimates 2- and 5-year kidney-failure risk. Manage BP and glucose, and consider an SGLT2 inhibitor where indicated.",
     "KDIGO"),
    (("sleep", "hrv", "recovery"),
     "Consistent sleep timing and duration (7–9 h) improve HRV, glucose and recovery; screen for apnoea when HRV and SpO₂ trend down together.",
     "AASM; sleep & cardiometabolic literature"),
    (("blood pressure", "hypertension", "sbp", "dbp", "bp"),
     "For most adults target <130/80 mmHg; lifestyle (sodium, weight, activity, alcohol) plus first-line agents (ACEi/ARB, CCB, thiazide) as needed.",
     "ACC/AHA hypertension guideline"),
]


def _evidence_answer(query: str, pdata: dict | None) -> tuple[str, list[str]]:
    s = (query or "").lower()
    hit = next((e for e in _EVIDENCE if _has(s, *e[0])), None)
    if not hit:
        return ("I don't have a curated summary for that specific question — treat it as needing a literature check "
                "rather than a grounded answer. I can summarise what this patient's own data shows instead.", [])
    _, text, src = hit
    out = f"{text}\n\n_Source: {src}. General guidance — review for this patient."
    # tie to the patient's own value where we have it
    if pdata:
        mk = pdata.get("mk") or {}
        rel = [k for k in ("apob", "ldl", "hba1c", "glucose", "crp", "hs-crp", "egfr", "vo2", "vo2max") if k in mk and _has(s, k, *( ("cholesterol","statin","lipid") if k in ("apob","ldl") else ()))]
        touched = [k for k in mk if _has(s, k)]
        show = touched or rel
        if show:
            out += " For **" + (pdata.get("name") or "this patient") + "**: " + ", ".join(f"{k} {mk[k]}" for k in show[:4]) + "."
    return out, []


# --------------------------------------------------------------------------- patient data assembly

_THRESH = {"apob": 90, "ldl": 100, "ldl-c": 100, "non-hdl": 130, "triglycerides": 150, "tg": 150,
           "crp": 3, "hs-crp": 3, "hba1c": 5.7, "a1c": 5.7, "glucose": 100, "fasting_glucose": 100,
           "sbp": 130, "ldl_c": 100}


def _flags(mk: dict) -> list[tuple]:
    out = []
    for k, t in _THRESH.items():
        v = mk.get(k)
        if isinstance(v, (int, float)) and v > t:
            out.append((k, v, t))
    return out


def _patient_data(pid: int) -> dict | None:
    from . import patient_data
    ov = patient_data.overview(pid)
    if ov.get("error"):
        return None
    pt = ov.get("patient", {})
    bm = ov.get("biomarkers") or {}
    raw = bm.get("markers") or {}
    mk = {str(k).lower(): v for k, v in raw.items() if k not in ("age", "sex") and isinstance(v, (int, float))} if isinstance(raw, dict) else {}
    rm = ov.get("risk_models") or {}
    risks = {k: v for k, v in rm.items() if isinstance(v, dict) and v.get("risk") is not None} if isinstance(rm, dict) else {}
    awaiting, cc = [], {}
    try:
        with patient_data._patient_db(pid):
            awaiting = db.rows("""SELECT id, title, body, confidence, medical FROM insights
                                  WHERE review_state = 'awaiting' AND dismissed = 0
                                  ORDER BY medical DESC, confidence DESC LIMIT 15""")
            db.exec_("CREATE TABLE IF NOT EXISTS care_config (id INTEGER PRIMARY KEY CHECK(id = 1), data TEXT)")
            row = db.one("SELECT data FROM care_config WHERE id = 1")
            cc = db.unj(row["data"], {}) if row else {}
    except Exception:  # noqa: BLE001
        pass
    return {
        "pid": pid, "name": pt.get("name"), "age": pt.get("age"), "sex": pt.get("sex"), "city": pt.get("city"),
        "conditions": pt.get("conditions") or [], "linked": pt.get("linked"),
        "mk": mk, "as_of": bm.get("as_of"), "flagged": _flags(mk), "risks": risks,
        "vitals": (ov.get("vitals") or {}), "meds": ov.get("medications") or [],
        "therapies": ov.get("therapies") or {}, "devices": ov.get("devices") or {},
        "reports": ov.get("reports") or [], "awaiting": awaiting, "care_config": cc,
        "summary": (ov.get("ai_summary") or {}).get("text") or "",
    }


def _patient_context_text(d: dict) -> str:
    L = [f"PATIENT: {d['name']}, {d.get('age')} {d.get('sex')}, {d.get('city')}. "
         f"Conditions: {', '.join(d['conditions']) or 'none recorded'}. Linked Vault: {'yes' if d['linked'] else 'no'}."]
    if d["mk"]:
        L.append(f"LATEST LABS ({d.get('as_of') or '—'}): " + "; ".join(f"{k} {v}" for k, v in list(d["mk"].items())[:26]))
    if d["flagged"]:
        L.append("ABOVE COMMON TARGETS: " + "; ".join(f"{k} {v} (>{t})" for k, v, t in d["flagged"]))
    if d["risks"]:
        L.append("RISK MODELS: " + "; ".join(f"{k} {v.get('risk')}% ({v.get('band','')})" for k, v in d["risks"].items()))
    vit = d["vitals"]
    if vit.get("available") and vit.get("metrics"):
        L.append("VITALS (7d): " + "; ".join(f"{k} {v}" for k, v in list(vit["metrics"].items())[:8]))
    if d["meds"]:
        L.append("MEDICATIONS: " + "; ".join(str(m.get("name", m)) if isinstance(m, dict) else str(m) for m in d["meds"][:12]))
    th = d["therapies"]
    if isinstance(th, dict) and (th.get("recent") or th.get("protocols")):
        L.append("THERAPIES: " + str(th.get("protocols") or th.get("recent"))[:200])
    if d["reports"]:
        L.append("RECENT REPORTS: " + "; ".join(f"{r.get('title')} ({r.get('collected_on')})" for r in d["reports"][:6]))
    if d["awaiting"]:
        L.append("FINDINGS AWAITING REVIEW: " + "; ".join(f"[{a['id']}] {a['title']}" for a in d["awaiting"]))
    cc = d["care_config"]
    if cc.get("focus") or cc.get("targets"):
        L.append(f"DOCTOR CARE PLAN: focus={cc.get('focus')}, targets={cc.get('targets')}, track={cc.get('track')}, note={cc.get('note','')}")
    if d["summary"]:
        L.append("GROUNDED SUMMARY: " + d["summary"])
    return "\n".join(L)


# --------------------------------------------------------------------------- per-intent composers (no-LLM fallback)

def _labs_line(d: dict, keys=None) -> str:
    mk = d["mk"]
    items = [(k, v) for k, v in mk.items() if (keys is None or k in keys)]
    return ", ".join(f"{k} {v}" for k, v in items[:12]) if items else "no labs on file"


def _compose_doctor(intent: str, d: dict, query: str) -> str:
    name = d.get("name") or "This patient"
    flg = d["flagged"]
    flg_s = ", ".join(f"{k} {v} (>{t})" for k, v, t in flg) if flg else "nothing above the common targets"

    if intent == "summary":
        parts = [f"**{name}** — {d.get('age')} {d.get('sex')}, {d.get('city')}. "
                 f"{'Conditions: ' + ', '.join(d['conditions']) + '.' if d['conditions'] else 'No conditions recorded.'}"]
        if d["summary"]:
            parts.append(d["summary"])
        parts.append(f"**Above target:** {flg_s}.")
        if d["risks"]:
            parts.append("**Risk:** " + "; ".join(f"{k} {v.get('risk')}% ({v.get('band','')})" for k, v in d["risks"].items()) + ".")
        if d["awaiting"]:
            parts.append(f"**{len(d['awaiting'])} finding(s) awaiting your review.**")
        return "\n".join(parts)

    if intent == "labs":
        s = query.lower()
        asked = [k for k in d["mk"] if k in s]
        if asked:
            return "**Latest:** " + ", ".join(f"{k} {d['mk'][k]}" for k in asked) + f". As of {d.get('as_of') or '—'}."
        return (f"**Latest labs ({d.get('as_of') or '—'}):** " + _labs_line(d) + ".\n"
                f"**Above target:** {flg_s}.")

    if intent == "risk":
        if not d["risks"]:
            return f"No model risk scores are on file for {name} yet. Flagged markers: {flg_s}. Order a lipid/metabolic panel to populate the models."
        lines = [f"- **{k}:** {v.get('risk')}% — {v.get('band','')}" for k, v in d["risks"].items()]
        drivers = flg_s
        return f"**Risk for {name}:**\n" + "\n".join(lines) + f"\n\nLikely drivers from the record: {drivers}. These are model estimates — review inputs before acting."

    if intent == "findings":
        if not d["awaiting"]:
            return f"Nothing is awaiting your review for {name} right now."
        lines = [f"- {a['title']}" + (f" ({round((a.get('confidence') or 0)*100)}%)" if a.get("confidence") else "") for a in d["awaiting"][:8]]
        return f"**{len(d['awaiting'])} finding(s) awaiting review for {name}:**\n" + "\n".join(lines) + "\n\nOpen the chart to read the evidence and sign each one."

    if intent == "medication":
        if not d["meds"]:
            return f"No medications are recorded for {name}. Add them in the chart so interaction checks run on any new Rx."
        meds = ", ".join(str(m.get("name", m)) if isinstance(m, dict) else str(m) for m in d["meds"])
        return f"**{name}'s medications:** {meds}.\nI check new supplement/Rx drafts against these for interactions — review in the chart before signing."

    if intent in ("therapeutics", "interaction"):
        goal = "heart" if any(k in ("apob", "ldl", "ldl-c") for k, *_ in flg) else "metabolic" if any(k in ("hba1c", "glucose") for k, *_ in flg) else "longevity"
        base = (f"I can draft an evidence-graded Longevity Rx for {name} (goal: {goal}) from their record — "
                f"supplements and, where indicated, medicines, each screened for interactions against their current meds.")
        if intent == "interaction":
            meds = ", ".join(str(m.get("name", m)) if isinstance(m, dict) else str(m) for m in d["meds"]) or "none recorded"
            base = f"Current medications: {meds}. Any Rx I draft is screened against these; open the draft to see flagged interactions before you sign."
        return base + f"\n\nAbove target now: {flg_s}. Nothing is prescribed until you review and sign."

    if intent == "orders":
        recs = []
        if any(k in ("apob", "ldl", "ldl-c", "crp", "hs-crp") for k, *_ in flg):
            recs.append("lipid panel + ApoB + hs-CRP (recheck in ~12 weeks after any change)")
        if any(k in ("hba1c", "a1c", "glucose") for k, *_ in flg):
            recs.append("HbA1c + fasting insulin (recheck in ~12 weeks)")
        if not recs:
            recs.append("a baseline longevity panel if none is recent")
        return f"**Suggested to order/retest for {name}:**\n" + "\n".join(f"- {r}" for r in recs) + "\n\nOrder from the chart — the patient sees and books them."

    if intent == "careplan":
        cc = d["care_config"]
        cur = f"Current plan: focus {cc.get('focus')}, targets {cc.get('targets')}." if cc.get("focus") else "No care plan set yet."
        suggest = "heart (ApoB/LDL targets)" if any(k in ("apob", "ldl", "ldl-c") for k, *_ in flg) else "metabolic (HbA1c/glucose targets)" if any(k in ("hba1c", "glucose") for k, *_ in flg) else "longevity"
        return (f"{cur}\nBased on what's above target ({flg_s}), I'd draft a **{suggest}** plan — set the focus, targets and "
                f"trackers in the chart under 'Customise this patient's app', then save. The patient's app updates once you apply it.")

    # fallback
    return _compose_doctor("summary", d, query)


# --------------------------------------------------------------------------- suggestions

def _doctor_suggestions(pid: int, d: dict, intent: str) -> list[dict]:
    chart = f"/doctor/patient/{pid}"
    s: list[dict] = []
    labels = {f[0] for f in d["flagged"]}
    if d["awaiting"]:
        s.append({"kind": "review", "label": f"Review & sign {len(d['awaiting'])} finding(s)", "route": chart})
    if intent in ("careplan", "summary", "risk", "labs") and (labels & {"apob", "ldl", "ldl-c", "non-hdl", "triglycerides", "tg", "crp", "hs-crp"}):
        s.append({"kind": "care_config", "label": "Draft a cardiac care plan", "route": chart})
    if intent in ("careplan", "summary", "risk", "labs") and (labels & {"hba1c", "a1c", "glucose"}):
        s.append({"kind": "care_config", "label": "Draft a metabolic care plan", "route": chart})
    if intent in ("therapeutics", "interaction", "summary"):
        s.append({"kind": "rx", "label": "Review the Longevity Rx draft", "route": chart})
    if intent in ("orders", "summary", "risk"):
        s.append({"kind": "order", "label": "Order tests & scans", "route": chart})
    if not s:
        s.append({"kind": "open", "label": "Open the full chart", "route": chart})
    seen, out = set(), []
    for x in s:
        if x["label"] in seen:
            continue
        seen.add(x["label"]); out.append(x)
    return out[:4]


# --------------------------------------------------------------------------- doctor entry

def doctor_copilot(me: dict, query: str, patient_id, history: list[dict] | None = None,
                   docs: list[dict] | None = None, images: list[dict] | None = None) -> dict:
    history = history or []
    has_patient = bool(patient_id)
    intent = classify_doctor(query, has_patient)
    d = _patient_data(int(patient_id)) if has_patient else None
    if has_patient and d is None:
        return {"answer": "I couldn't find that patient's record.", "confidence": 0, "medical": False,
                "grounded": False, "engine": "copilot", "intent": intent, "suggestions": []}

    # a file the clinician attached (lab PDF, scan, prescription, photo) → read it, grounded in the patient's record
    docs = docs or []; images = images or []
    if docs or images:
        context = _patient_context_text(d) if d else ""
        for dd in docs:
            context += f'\n\nFILE THE CLINICIAN ATTACHED — "{dd["name"]}":\n{dd["text"]}'
        sys = DOCTOR_SYSTEM + ("\nThe clinician attached a file (document and/or image) with this message — a lab "
                               "report, scan, prescription or photo. Read it, summarise what matters, and answer their "
                               "question about it, grounded in the patient's record where relevant. Draft only; they sign.")
        q = query or "Read the attached file and summarise what matters for this patient."
        out = telomy_llm.ask(sys, context or "(no patient record loaded)", q, history, _SCHEMA,
                             max_tokens=1800, images=images, skip_guard=True)
        if out and "_error" not in out and str(out.get("answer") or "").strip():
            _log(me, "doctor", "attachment", patient_id, query, out.get("engine", "copilot"), True)
            return {"answer": out["answer"], "confidence": out.get("confidence", 0.7), "medical": True,
                    "grounded": True, "engine": out.get("engine", telomy_llm.model_name()), "intent": "attachment",
                    "disclaimer": DISCLAIMER, "suggestions": _doctor_suggestions(int(patient_id), d, "summary") if d else []}
        reason = out.get("_error") if out else "no model configured"
        return {"answer": f"I couldn't read that attachment just now ({reason}). Reading files needs the cloud model — "
                          "try again when connected, or paste the key values.", "confidence": 0, "medical": False,
                "grounded": False, "engine": "copilot", "intent": "attachment", "suggestions": []}

    if intent == "capabilities":
        ans = ("I'm **Sinc** — grounded in your patients' records. Ask me to **summarise a patient**, read their "
               "**labs or risk**, list what's **awaiting your sign-off**, draft a **Longevity Rx** or **care plan**, "
               "check **interactions**, suggest what to **retest**, or look up the **evidence** on a topic. "
               "I draft; you review and sign — nothing happens until you approve it.")
        _log(me, "doctor", intent, patient_id, query, "telomy-copilot", True)
        return {"answer": ans, "confidence": 1, "medical": False, "grounded": True, "engine": "telomy-copilot",
                "intent": intent, "suggestions": _doctor_suggestions(int(patient_id), d, "summary") if d else _panel_suggestions()}
    if intent == "offtopic":
        ans = ("I focus on clinical questions about your patients — their data, risk, findings, Rx, and the evidence. "
               "Ask me one of those and I'll pull it from the record.")
        _log(me, "doctor", intent, patient_id, query, "telomy-copilot", True)
        return {"answer": ans, "confidence": 1, "medical": False, "grounded": True, "engine": "telomy-copilot",
                "intent": intent, "suggestions": _doctor_suggestions(int(patient_id), d, "summary") if d else _panel_suggestions()}

    # evidence questions are answered from the KB (general + tied to the patient's value), no LLM needed
    if intent == "evidence":
        ans, ev = _evidence_answer(query, d)
        _log(me, "doctor", intent, patient_id, query, "telomy-evidence", True)
        return {"answer": ans, "confidence": 0.75, "medical": True, "grounded": True, "engine": "telomy-evidence",
                "intent": intent, "evidence_ids": ev, "disclaimer": DISCLAIMER,
                "suggestions": _doctor_suggestions(int(patient_id), d, intent) if d else []}

    context = _patient_context_text(d) if d else _panel_context(me)
    sys = DOCTOR_SYSTEM + f"\nThe user's intent looks like: {intent}. Focus your answer there."
    out = telomy_llm.ask(sys, context, query, history, _SCHEMA, max_tokens=1500)
    if out and out.get("answer") and not out.get("_error"):
        ans, conf, med, eng = out["answer"], out.get("confidence", 0.7), out.get("medical", True), out.get("engine", telomy_llm.model_name())
        ev = out.get("evidence_ids", [])
    else:
        ans = _compose_doctor(intent, d, query) if d else context
        conf, med, eng, ev = 0.6, has_patient, "telomy-composer", [f"finding:{a['id']}" for a in (d["awaiting"][:6] if d else [])]
    _log(me, "doctor", intent, patient_id, query, eng, True)
    return {"answer": ans, "confidence": conf, "medical": med, "grounded": True, "engine": eng, "intent": intent,
            "evidence_ids": ev, "suggestions": _doctor_suggestions(int(patient_id), d, intent) if d else _panel_suggestions(),
            "disclaimer": DISCLAIMER}


def _panel_context(me: dict) -> str:
    from . import patient_data
    lines = ["DOCTOR PANEL — findings awaiting review across your patients:"]
    try:
        patients = db.rows("SELECT id, name FROM patients ORDER BY id LIMIT 40")
        seen, n = set(), 0
        for pt in patients:
            uid = patient_data._resolve_user_id(pt["id"])
            if uid is None or uid in seen:
                continue
            seen.add(uid)
            with patient_data._patient_db(pt["id"]):
                rows = db.rows("SELECT title FROM insights WHERE review_state='awaiting' AND dismissed=0 ORDER BY medical DESC, confidence DESC LIMIT 3")
            if rows:
                lines.append(f"- {pt['name']}: " + "; ".join(r["title"] for r in rows))
                n += 1
            if n >= 15:
                break
        if n == 0:
            lines.append("- Nothing awaiting review right now.")
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(lines)


def _panel_suggestions() -> list[dict]:
    return [{"kind": "queue", "label": "Open the work queue", "route": "/doctor/work"},
            {"kind": "patients", "label": "See all patients", "route": "/doctor/patients"}]


# --------------------------------------------------------------------------- centre data + composers

def _centre_data(org: str) -> dict:
    from . import centre as centremod
    d: dict = {"org": org}
    try:
        d["dash"] = centremod.dashboard(org)
    except Exception:  # noqa: BLE001
        d["dash"] = {}
    try:
        d["schedule"] = centremod.schedule(org) or []
    except Exception:  # noqa: BLE001
        d["schedule"] = []
    try:
        d["floor"] = centremod.floor(org) or []
    except Exception:  # noqa: BLE001
        d["floor"] = []
    try:
        d["members"] = centremod.list_members(org) or []
    except Exception:  # noqa: BLE001
        d["members"] = []
    return d


def _inr(v) -> str:
    try:
        return "₹" + f"{int(round(float(v or 0))):,}"
    except Exception:  # noqa: BLE001
        return "₹0"


def _centre_context_text(d: dict) -> str:
    dash = d.get("dash", {})
    L = [f"CENTRE: {d['org']}. Members {dash.get('active_members')}, booked today {dash.get('today_bookings')}, "
         f"checked in {dash.get('checked_in')}, revenue today {_inr(dash.get('revenue_today'))}, outstanding {_inr(dash.get('outstanding'))}."]
    sch = d.get("schedule", [])
    L.append("TODAY'S SCHEDULE: " + ("; ".join(f"{b.get('time','')} {b.get('member_name','')} {b.get('service_name','')}".strip() for b in sch[:12]) if sch else "no bookings today."))
    fl = d.get("floor", [])
    if fl:
        by = {}
        for f in fl:
            by[f.get("status", "?")] = by.get(f.get("status", "?"), 0) + 1
        L.append("FLOOR: " + ", ".join(f"{k} {v}" for k, v in by.items()) + ". "
                 + "Attention: " + ("; ".join(f"{f.get('name')} [{f.get('status')}]" for f in fl if f.get("status") in ("servicing", "offline")) or "none"))
    L.append(f"MEMBERS ON ROSTER: {len(d.get('members', []))}.")
    return "\n".join(L)


def _compose_centre(intent: str, d: dict, query: str) -> str:
    dash = d.get("dash", {})
    org = d["org"].replace("-", " ").title()
    if intent == "revenue":
        return (f"**{org} — money:**\n"
                f"- Revenue today: {_inr(dash.get('revenue_today'))}\n"
                f"- Outstanding: {_inr(dash.get('outstanding'))}\n"
                f"- Total to date: {_inr(dash.get('total_revenue'))}\n\n"
                "Open Revenue & payments to see invoices, gateways and who owes what.")
    if intent == "bookings":
        sch = d.get("schedule", [])
        if not sch:
            return f"No bookings today at {org}. Booked today: {dash.get('today_bookings', 0)}. Open Bookings to add one or see the week."
        lines = [f"- {b.get('time','')} · {b.get('member_name','?')} · {b.get('service_name','')}".rstrip(" ·") for b in sch[:10]]
        return f"**Today at {org} ({len(sch)}):**\n" + "\n".join(lines)
    if intent == "floor":
        fl = d.get("floor", [])
        if not fl:
            return f"No floor/equipment data for {org} yet."
        att = [f for f in fl if f.get("status") in ("servicing", "offline")]
        inuse = [f for f in fl if f.get("status") == "in_use"]
        free = [f for f in fl if f.get("status") == "available"]
        out = [f"**Floor at {org}:** {len(free)} available, {len(inuse)} in use, {len(att)} needs attention."]
        if att:
            out.append("Attention: " + ", ".join(f"{f.get('name')} ({f.get('status')})" for f in att[:8]) + ".")
        return "\n".join(out)
    if intent == "members":
        ms = d.get("members", [])
        return (f"**{org} members:** {len(ms)} on the roster (active today: {dash.get('active_members', '—')}). "
                "Open Members for plans, renewals and records.")
    if intent == "staff":
        return (f"Team performance for {org} — utilisation and revenue by staff — is on the Team performance screen. "
                "I can pull specific numbers once you open it.")
    if intent == "doctors":
        return f"Clinicians at {org} are listed under Doctors. Open it to see who's available."
    # status
    return (f"**{org} right now:**\n"
            f"- Members {dash.get('active_members')} · booked today {dash.get('today_bookings')} · checked in {dash.get('checked_in')}\n"
            f"- Revenue today {_inr(dash.get('revenue_today'))} · outstanding {_inr(dash.get('outstanding'))}\n"
            + (f"- Floor needs attention: " + "; ".join(f"{f.get('name')} [{f.get('status')}]" for f in d.get('floor', []) if f.get('status') in ('servicing', 'offline')) if any(f.get('status') in ('servicing', 'offline') for f in d.get('floor', [])) else "- Floor all clear"))


def _centre_suggestions(intent: str) -> list[dict]:
    m = {
        "revenue": [{"kind": "revenue", "label": "Revenue & payments", "route": "/centre/revenue"}],
        "bookings": [{"kind": "bookings", "label": "Open bookings", "route": "/centre/bookings"}],
        "floor": [{"kind": "floor", "label": "Open the floor", "route": "/centre/floor"}],
        "members": [{"kind": "members", "label": "Open members", "route": "/centre/members"}],
        "staff": [{"kind": "staff", "label": "Team performance", "route": "/centre/performance"}],
        "doctors": [{"kind": "doctors", "label": "Doctors", "route": "/centre/doctors"}],
    }
    base = m.get(intent, [])
    base += [{"kind": "bookings", "label": "Bookings", "route": "/centre/bookings"},
             {"kind": "revenue", "label": "Revenue", "route": "/centre/revenue"},
             {"kind": "floor", "label": "Floor", "route": "/centre/floor"}]
    seen, out = set(), []
    for x in base:
        if x["label"] in seen:
            continue
        seen.add(x["label"]); out.append(x)
    return out[:4]


def centre_copilot(me: dict, query: str, history: list[dict] | None = None) -> dict:
    org = me.get("org", "default")
    intent = classify_centre(query)
    d = _centre_data(org)
    context = _centre_context_text(d)
    out = telomy_llm.ask(CENTRE_SYSTEM + f"\nIntent: {intent}.", context, query, history or [], _SCHEMA, max_tokens=1200)
    if out and out.get("answer") and not out.get("_error"):
        ans, conf, eng = out["answer"], out.get("confidence", 0.7), out.get("engine", telomy_llm.model_name())
    else:
        ans, conf, eng = _compose_centre(intent, d, query), 0.6, "telomy-composer"
    _log(me, "centre", intent, None, query, eng, True)
    return {"answer": ans, "confidence": conf, "medical": False, "grounded": True, "engine": eng,
            "intent": intent, "suggestions": _centre_suggestions(intent)}
