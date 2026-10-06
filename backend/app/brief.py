"""Specialist pack / pre-clinic brief: a print-ready PDF and a FHIR-shaped JSON bundle.

Only real Vault data goes in. Missing values are written as "not available"; test data is labelled as such.
"""
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import db, engine
from .catalog import MARKERS

SPECIALTIES = {
    "neurology": {"title": "Neurology / memory clinic", "markers": ["ptau217", "nfl", "wmh_fazekas", "brain_age_gap", "hippocampal_pct",
                  "homocysteine", "b12", "mma", "org_brain"], "genes": ["apoe"], "signals": ["sleep_hours", "hrv"]},
    "cardiology": {"title": "Cardiology", "markers": ["apob", "ldl", "ldl_p", "apoa1", "hdl", "tg", "lpa", "hscrp", "homocysteine", "nt_probnp", "hs_troponin",
                               "cac", "cac_pct", "cad_rads", "plaque_vol", "epicardial_fat", "cimt", "lvef", "vo2max_lab", "org_heart", "org_artery"],
                   "genes": ["apoe", "cad9p21"], "signals": ["rhr", "hrv", "vo2max"]},
    "endocrinology": {"title": "Endocrinology", "markers": ["hba1c", "glucose", "insulin", "homa_ir", "tsh", "ft3",
                      "cortisol", "testosterone", "free_t", "shbg", "igf1", "vitd", "vat_area", "body_fat_pct", "almi", "bmd_spine_t", "liver_pdff"], "genes": ["tcf7l2", "fto"], "signals": ["glucose_mean", "weight"]},
    "gastroenterology": {"title": "Gastroenterology", "markers": ["calprotectin", "zonulin", "shannon", "butyrate",
                         "akkermansia", "faecali", "alt", "ast", "ggt", "platelets", "liver_pdff", "liver_hu", "org_liver", "candida", "fit"], "genes": ["fut2"], "signals": []},
    "sleep": {"title": "Sleep medicine", "markers": ["ahi", "odi", "min_spo2", "cortisol", "ferritin", "vat_area"], "genes": [],
              "signals": ["sleep_hours", "deep_sleep", "rem_sleep", "sleep_score", "hrv", "spo2", "resp_rate"]},
    "general": {"title": "General practice", "markers": ["hemoglobin", "hba1c", "ldl", "apob", "hscrp", "vitd", "b12",
                "alt", "creatinine", "egfr", "cystatin_c", "uacr", "tsh", "cac", "liver_pdff", "ahi", "vo2max_lab", "mced"], "genes": [], "signals": ["rhr", "sleep_hours", "steps"]},
}


def collect(specialty: str) -> dict:
    spec = SPECIALTIES[specialty]
    p = engine.profile()
    rows = []
    for m in spec["markers"] + spec["genes"]:
        h = engine.marker_history(m)
        if not h:
            rows.append({"id": m, "name": MARKERS[m][0], "value": "not available"})
            continue
        last = h[-1]
        rows.append({"id": m, "name": MARKERS[m][0],
                     "value": last["value_num"] if last["value_num"] is not None else last["value_text"],
                     "unit": last["unit"], "range": last["ref_text"], "status": last["status"], "date": last["collected_on"],
                     "previous": [(x["collected_on"], x["value_num"] if x["value_num"] is not None else x["value_text"]) for x in h[:-1]],
                     "source": last["source"], "test_data": bool(last["is_test_data"])})
    sigs = []
    for s in spec["signals"]:
        b = engine.signal_baseline(s, days=30)
        sigs.append({"id": s, "name": engine.SIGNALS[s][0], "unit": engine.SIGNALS[s][1],
                     "mean_30d": b["mean"] if b else "not available", "n": b["n"] if b else 0})
    related = [i for i in engine.list_insights() if any(e.get("marker_id") in spec["markers"] + spec["genes"]
               or e.get("metric") in spec["signals"] for e in i["evidence"])][:6]
    meds = [e["label"] for e in db.rows("SELECT label FROM events WHERE kind IN ('supplement','medication') ORDER BY ts")]
    return {"specialty": spec["title"], "generated": date.today().isoformat(), "patient": {
        "name": p.get("name"), "dob": p.get("dob"), "sex": p.get("sex"), "allergies": p.get("emergency", {}).get("allergies")},
        "labs": rows, "signals": sigs, "insights": related, "medications": meds,
        "longevity": engine.longevity_age(), "contains_test_data": any(r.get("test_data") for r in rows)}


def fhir_bundle(specialty: str) -> dict:
    d = collect(specialty)
    entries = [{"resource": {"resourceType": "Patient", "id": "self", "name": [{"text": d["patient"]["name"]}],
                             "gender": d["patient"]["sex"], "birthDate": d["patient"]["dob"]}}]
    for r in d["labs"]:
        if r["value"] == "not available":
            continue
        obs = {"resourceType": "Observation", "status": "final", "subject": {"reference": "Patient/self"},
               "code": {"text": r["name"], "coding": [{"system": "http://loinc.org", "code": MARKERS[r["id"]][7]}]
                        if MARKERS[r["id"]][7] else []},
               "effectiveDateTime": r["date"], "meta": {"source": r.get("source")}}
        if isinstance(r["value"], (int, float)):
            obs["valueQuantity"] = {"value": r["value"], "unit": r.get("unit")}
        else:
            obs["valueString"] = str(r["value"])
        if r.get("range"):
            obs["referenceRange"] = [{"text": r["range"]}]
        entries.append({"resource": obs})
    return {"resourceType": "Bundle", "type": "collection", "meta": {"tag": [{"code": "test-data"}]}
            if d["contains_test_data"] else {}, "entry": entries}


def pdf(specialty: str) -> bytes:
    d = collect(specialty)
    buf = io.BytesIO()
    st = getSampleStyleSheet()
    teal = colors.HexColor("#1F5C4E")
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"Telomy pre-clinic brief — {d['specialty']}")
    story = [Paragraph(f"<font color='#1F5C4E'><b>TELOMY</b></font> · Pre-clinic brief for {d['specialty']}", st["Title"])]
    if d["contains_test_data"]:
        story.append(Paragraph("<font color='#9B2C2C'><b>Contains TEST DATA — not for clinical use.</b></font>", st["Normal"]))
    pt = d["patient"]
    story += [Paragraph(f"{pt['name']} · DOB {pt['dob']} · {pt['sex']} · Allergies: {pt['allergies'] or 'none recorded'} "
                        f"· Generated {d['generated']}", st["Normal"]), Spacer(1, 6)]
    la = d["longevity"]
    if la.get("value"):
        story.append(Paragraph(f"PhenoAge {la['value']} vs chronological {la['chronological']} "
                               f"(as of {la['as_of']}, confidence {int(la['confidence'] * 100)}%). "
                               f"DunedinPACE {la.get('pace') or 'not available'}.", st["Normal"]))
    story += [Spacer(1, 8), Paragraph("Laboratory results", st["Heading3"])]
    data = [["Test", "Latest", "Lab range", "Date", "Previous"]]
    for r in d["labs"]:
        prev = ", ".join(f"{v} ({day})" for day, v in r.get("previous", [])) or "—"
        val = r["value"] if r["value"] == "not available" else f"{r['value']} {r.get('unit') or ''}"
        data.append([r["name"], val, r.get("range") or "—", r.get("date") or "—", prev])
    t = Table(data, colWidths=[46 * mm, 32 * mm, 30 * mm, 24 * mm, 46 * mm], repeatRows=1)
    sty = [("BACKGROUND", (0, 0), (-1, 0), teal), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
           ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1CFC5"))]
    for i, r in enumerate(d["labs"], start=1):
        if r.get("status") in ("out_of_range", "variant", "detected"):
            sty.append(("TEXTCOLOR", (1, i), (1, i), colors.HexColor("#9B2C2C")))
    t.setStyle(TableStyle(sty))
    story += [t, Spacer(1, 8)]
    if d["signals"]:
        story.append(Paragraph("Wearable signals (30-day mean)", st["Heading3"]))
        story.append(Table([["Signal", "Mean", "Days"]] + [[s["name"], f"{s['mean_30d']} {s['unit']}" if s["n"] else
                            "not available", s["n"]] for s in d["signals"]], colWidths=[70 * mm, 50 * mm, 30 * mm],
                           style=[("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey)]))
    if d["insights"]:
        story += [Spacer(1, 8), Paragraph("Patterns Sinc noticed (for your review)", st["Heading3"])]
        for i in d["insights"]:
            state = {"signed": "signed off", "awaiting": "awaiting clinician review"}.get(i["review_state"], "unreviewed")
            story.append(Paragraph(f"<b>{i['title']}</b> — {i['body']} <i>(confidence {int(i['confidence'] * 100)}%, {state})</i>",
                                   st["Normal"]))
            story.append(Spacer(1, 3))
    story += [Spacer(1, 6), Paragraph("Current supplements / medications: " + ("; ".join(d["medications"]) or "none recorded"),
                                      st["Normal"]),
              Spacer(1, 10), Paragraph("Every value above comes from the patient's Telomy Vault with its source and date. "
                                       "Sinc patterns are correlations, not diagnoses.", st["Italic"])]
    doc.build(story)
    return buf.getvalue()
