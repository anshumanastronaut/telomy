"""Telomy Rx — personalised supplements (Telomy Formulas), prescription medicines and clinic IVs, doctor-certified.

Model (Telomy DPR §10): the trigger is Vault evidence — a lab value, an N-of-1 result, genetics or a clinician's judgement —
never a quiz. Sinc drafts; a registered doctor (NMC; Telemedicine Practice Guidelines 2020) reviews, edits and signs; only then
can the person order. Formulas are FSSAI nutraceuticals ("NOT FOR MEDICINAL USE", no disease claims). Prescription items are
dispensed only by a licensed pharmacy partner against the e-prescription; IVs are administered at the centre.
Payments are test mode. Interactions: curated supplement–drug rules (NIH ODS / NCCIH / product monographs) plus DDInter
drug–drug pairs when the open dataset is present in data/ddinter.
"""
import csv
import glob
import os
from datetime import date, timedelta

from . import db, engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS rx_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, goal TEXT, created_at TEXT, state TEXT,
  plan TEXT, doctor TEXT, reg_no TEXT, note TEXT, decided_at TEXT);
CREATE TABLE IF NOT EXISTS rx_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id INTEGER, created_at TEXT, items TEXT, total INTEGER,
  status TEXT, channel TEXT);
"""

# id: name, kind, rx?, evidence, dose, price ₹/month (or per session), goals, targets (markers it should move),
#     expected, retest_days, contains, notes
P = lambda *a: dict(zip(("name", "kind", "rx", "evidence", "dose", "price", "goals", "targets", "expected", "retest_days", "contains", "notes"), a))  # noqa: E731
PRODUCTS = {
    # ---- Telomy Formulas (launch set + roadmap), white-label FSSAI GMP partner
    "wind_down": P("Telomy Formulas · Wind-Down", "formula", False, "B", "1 sachet 60 min before bed", 1800, ["sleep", "stress"], ["deep_sleep", "sleep_score"],
                   "Sleep-onset and deep sleep; best judged by an N-of-1 study", 30, "Magnesium glycinate 200 mg · L-theanine 200 mg · glycine 3 g",
                   "Three honestly-dosed actives (DPR §10)."),
    "calm": P("Telomy Formulas · Calm", "formula", False, "B", "1 capsule after breakfast", 2200, ["stress", "sleep"], ["hrv", "cortisol_night"],
              "Perceived stress ↓ in RCTs of KSM-66 and saffron", 56, "L-theanine 200 mg · KSM-66 ashwagandha 600 mg · saffron 30 mg",
              "Ashwagandha: avoid in pregnancy, hyperthyroidism, liver disease."),
    "recover": P("Telomy Formulas · Recover", "formula", False, "B", "1 scoop post-training", 2600, ["recovery", "muscle"], ["almi", "grip", "hscrp"],
                 "Strength and lean mass with training (creatine); soreness ↓ (tart cherry)", 90,
                 "Creatine monohydrate 3–5 g · tart cherry 480 mg · omega-3 1 g · bioavailable curcumin 500 mg", "Creatine raises serum creatinine slightly — not kidney damage."),
    "focus": P("Telomy Formulas · Focus (roadmap)", "formula", False, "C", "1 capsule morning", 2400, ["cognition"], [], "Attention in small trials", 56,
               "Citicoline 250 mg · L-theanine 100 mg · rhodiola 200 mg · bacopa 300 mg", "Roadmap formula — not yet manufactured."),
    "longevity": P("Telomy Formulas · Longevity (roadmap)", "formula", False, "C", "2 capsules with breakfast", 3200, ["longevity", "heart"], ["omega3_index", "vitd"],
                   "Omega-3 index and vitamin D toward target; GlyNAC is early-stage", 90, "Glycine 3 g + NAC 1.2 g (GlyNAC) · omega-3 1 g · D3 2000 IU + K2 100 µg",
                   "Roadmap formula."),
    # ---- single supplements (clinician-recommended)
    "vitd": P("Vitamin D3", "supplement", False, "A", "Personalised (see dose)", 250, ["bone", "immunity", "longevity"], ["vitd"],
              "≈ +10 ng/mL per 1,000 IU/day (wide individual variation)", 90, "Cholecalciferol", "Take with the largest meal."),
    "omega3": P("Omega-3 (EPA+DHA)", "supplement", False, "B", "2 g EPA+DHA daily with food", 900, ["heart", "longevity"], ["omega3_index", "tg"],
                "Omega-3 index +3–4 points in 12 weeks; TG ↓ 15–30 %", 90, "Fish or algal oil", "Small bleeding-risk increase with anticoagulants."),
    "mg": P("Magnesium glycinate", "supplement", False, "B", "200–400 mg elemental at night", 450, ["sleep", "stress"], ["rbc_mg", "deep_sleep"],
            "RBC magnesium toward 5–6.5 mg/dL", 90, "Magnesium bisglycinate", "Separate from thyroid and antibiotic tablets by 4 h."),
    "methyl_b": P("Methylfolate + methylcobalamin", "supplement", False, "B", "Methylfolate 400–800 µg + B12 1,000 µg", 600, ["heart", "brain"], ["homocysteine", "b12", "folate"],
                  "Homocysteine ↓ ~25 % (B-vitamin trials)", 90, "L-5-MTHF, methylcobalamin", "Check B12 first — folate alone can mask B12 deficiency."),
    "creatine": P("Creatine monohydrate", "supplement", False, "A", "3–5 g daily", 700, ["muscle", "cognition"], ["almi", "grip"], "Strength and lean mass with resistance training", 180,
                  "Creatine monohydrate", "Avoid if eGFR < 60."),
    "psyllium": P("Psyllium husk", "supplement", False, "A", "5–10 g daily in water", 300, ["heart", "metabolic", "gut"], ["ldl", "apob", "glucose"],
                  "LDL ↓ 5–10 %; post-meal glucose ↓", 90, "Isabgol", "Separate other tablets by 2 h."),
    "zinc": P("Zinc (picolinate)", "supplement", False, "B", "15–25 mg daily for 8–12 weeks", 300, ["immunity"], ["zinc"], "Serum zinc into range", 84, "Zinc picolinate",
              "> 40 mg/day long-term lowers copper."),
    "selenium": P("Selenium (selenomethionine)", "supplement", False, "C", "100–200 µg daily", 400, ["thyroid"], ["tpo_ab"], "Anti-TPO ↓ in some trials; TSH unchanged", 180,
                  "Selenomethionine", "Do not exceed 400 µg/day."),
    "iron": P("Iron bisglycinate", "supplement", False, "A", "25–50 mg elemental on alternate days", 350, ["energy"], ["ferritin", "hemoglobin"], "Ferritin ↑ when deficient", 90,
              "Iron bisglycinate", "Only with proven deficiency (ferritin < 30)."),
    "probiotic": P("Probiotic (L. rhamnosus GG + B. lactis)", "supplement", False, "C", "1 capsule daily", 900, ["gut"], ["shannon"], "Strain-specific; modest", 90,
                   "LGG, BB-12", "Avoid if immunosuppressed."),
    "coq10": P("CoQ10 (ubiquinol)", "supplement", False, "C", "100–200 mg with food", 1200, ["heart"], [], "May ease statin muscle symptoms (mixed trials)", 90, "Ubiquinol", "Can lower INR on warfarin."),
    "theanine": P("L-theanine", "supplement", False, "B", "200 mg as needed", 600, ["stress", "sleep"], ["hrv"], "Acute calm without sedation", 30, "L-theanine", ""),
    "electrolytes": P("Electrolyte sachets", "supplement", False, "B", "1 sachet in sauna/plunge days", 500, ["recovery"], [], "Hydration in heat sessions", 0, "Na, K, Mg", ""),
    # ---- prescription medicines (doctor prescribes; licensed pharmacy partner dispenses)
    "rosuva": P("Rosuvastatin", "medicine", True, "A", "5–10 mg nightly (doctor to set)", 250, ["heart"], ["apob", "ldl"], "LDL/ApoB ↓ 40–50 %", 84, "Statin",
                "Check SLCO1B1 (PGx) and ALT; myopathy risk with gemfibrozil."),
    "ezetimibe": P("Ezetimibe", "medicine", True, "A", "10 mg daily", 200, ["heart"], ["apob", "ldl"], "LDL ↓ ~20 % (added to a statin)", 84, "Cholesterol absorption inhibitor", ""),
    "metformin": P("Metformin XR", "medicine", True, "A", "500–1,000 mg with dinner", 150, ["metabolic"], ["hba1c", "glucose"], "HbA1c ↓ 0.5–1 %; DPP: diabetes ↓ 31 %", 90,
                   "Biguanide", "Lowers B12 over time — monitor."),
    "telmisartan": P("Telmisartan", "medicine", True, "A", "20–40 mg daily", 180, ["heart", "kidney"], ["sbp", "uacr"], "SBP ↓ 8–12 mmHg; albuminuria ↓", 30, "ARB",
                     "Hyperkalaemia with potassium supplements or spironolactone."),
    "semaglutide": P("Semaglutide", "medicine", True, "A", "Weekly, titrated by doctor", 9000, ["metabolic"], ["hba1c", "vat_area", "liver_pdff"], "Weight ↓ ~15 %; liver fat ↓", 90,
                     "GLP-1 receptor agonist", "Hypoglycaemia with sulfonylureas/insulin; pancreatitis history is a contraindication."),
    "d3_60k": P("Cholecalciferol 60,000 IU", "medicine", True, "A", "Weekly × 8 then monthly", 150, ["bone"], ["vitd"], "Rapid repletion when < 20 ng/mL", 56, "Vitamin D3 sachet", ""),
    # ---- IV (administered at the centre, doctor order)
    "iv_hydration": P("IV hydration + electrolytes", "iv", True, "C", "500 mL over 30 min", 3500, ["recovery"], [], "Rehydration", 0, "Ringer's lactate, Mg", "Fluid load caution in heart/kidney failure."),
    "iv_myers": P("IV Myers' cocktail", "iv", True, "C", "250 mL over 20 min", 5000, ["energy"], [], "No difference vs placebo in fibromyalgia RCT (Ali 2009)", 0,
                  "Mg, Ca, B-complex, B12, vitamin C", "Evidence is weak; offered only with informed consent."),
    "iv_vitc": P("IV high-dose vitamin C (25 g)", "iv", True, "D", "Over 60–90 min", 7000, ["immunity"], [], "No proven benefit for healthy adults", 0, "Ascorbic acid",
                 "G6PD test mandatory first (haemolysis). Avoid with kidney stones/CKD."),
    "iv_nad": P("IV NAD+", "iv", True, "D", "250–500 mg over 2–4 h", 15000, ["longevity"], [], "Human outcome data lacking", 0, "NAD+", "Flushing and chest tightness if infused fast."),
    "iv_iron": P("IV iron (ferric carboxymaltose)", "iv", True, "A", "Single 500–1,000 mg dose", 4500, ["energy"], ["ferritin", "hemoglobin"], "Corrects iron-deficiency anaemia", 42,
                 "Ferric carboxymaltose", "Only for confirmed iron deficiency."),
    "b12_im": P("Vitamin B12 injection", "iv", True, "A", "1,000 µg IM weekly × 4", 600, ["energy", "brain"], ["b12", "mma"], "Repletes B12", 56, "Methylcobalamin", "Only if deficient (B12 < 200 or MMA raised)."),
}

EXCLUDED = [("Melatonin", "Prescription-only in India — your doctor can prescribe if appropriate."),
            ("NMN", "Not listed under FSSAI nutraceutical regulations."),
            ("8–9-active 'stacks'", "Under-dosed by design — each active below its studied dose."),
            ("High-dose antioxidants (vit C ≥1 g, vit E ≥400 IU daily)", "Blunt training adaptations (Ristow 2009; Paulsen 2014)."),
            ("Food-IgG elimination products", "IgG testing is not a valid basis (EAACI).")]

GOALS = {"sleep": "Sleep", "stress": "Stress & calm", "heart": "Heart & cholesterol", "metabolic": "Blood sugar & weight", "energy": "Energy",
         "muscle": "Muscle & strength", "longevity": "Healthy ageing", "gut": "Gut", "brain": "Brain & focus", "recovery": "Recovery"}

# (a, b, severity, note) — a/b are product ids or medicine keywords/classes
CURATED = [
    ("omega3", "anticoagulant", "moderate", "Slightly higher bleeding risk — monitor, usually fine."),
    ("longevity", "warfarin", "major", "Vitamin K2 counteracts warfarin."),
    ("mg", "levothyroxine", "moderate", "Separate by 4 hours (absorption)."),
    ("mg", "antibiotic_quinolone", "moderate", "Separate by 4 hours."),
    ("wind_down", "levothyroxine", "moderate", "Contains magnesium — separate by 4 hours."),
    ("iron", "levothyroxine", "moderate", "Separate by 4 hours."), ("iron", "ppi", "moderate", "PPIs reduce iron absorption."),
    ("zinc", "antibiotic_quinolone", "moderate", "Separate by 2–4 hours."),
    ("calm", "levothyroxine", "moderate", "Ashwagandha may raise thyroid hormone levels — check TSH."),
    ("calm", "sedative", "moderate", "Additive sedation."), ("calm", "pregnancy", "major", "Ashwagandha is not advised in pregnancy."),
    ("recover", "anticoagulant", "moderate", "Curcumin and omega-3 add mild bleeding risk."),
    ("coq10", "warfarin", "moderate", "May lower INR."), ("creatine", "ckd", "major", "Avoid with eGFR < 60."),
    ("methyl_b", "b12_unknown", "moderate", "Check B12/MMA before folate."),
    ("telmisartan", "potassium", "major", "Hyperkalaemia risk."), ("rosuva", "gemfibrozil", "major", "Myopathy risk."),
    ("rosuva", "red_yeast_rice", "major", "Duplicate statin."), ("semaglutide", "sulfonylurea", "moderate", "Hypoglycaemia risk — dose review."),
    ("metformin", "b12_low", "moderate", "Metformin lowers B12 — your B12 is already low-normal; monitor and consider B12."),
    ("iv_vitc", "g6pd_def", "major", "Contraindicated in G6PD deficiency."), ("iv_vitc", "g6pd_unknown", "major", "G6PD must be tested first."),
    ("iv_hydration", "chf", "major", "Fluid overload risk."), ("psyllium", "any_oral", "minor", "Separate other medicines by 2 hours."),
    ("vitd", "thiazide", "moderate", "High-dose D with thiazides can raise calcium."),
    ("selenium", "high_selenium", "major", "Selenium already ≥ 150 µg/L."),
]
MED_CLASSES = {"warfarin": ["warfarin", "acenocoumarol"], "anticoagulant": ["warfarin", "apixaban", "rivaroxaban", "dabigatran", "clopidogrel", "aspirin"],
               "levothyroxine": ["levothyroxine", "thyroxine", "eltroxin", "thyronorm"], "ppi": ["pantoprazole", "omeprazole", "rabeprazole", "esomeprazole"],
               "antibiotic_quinolone": ["ciprofloxacin", "levofloxacin", "doxycycline"], "sedative": ["zolpidem", "clonazepam", "alprazolam"],
               "gemfibrozil": ["gemfibrozil"], "sulfonylurea": ["glimepiride", "gliclazide"], "thiazide": ["hydrochlorothiazide", "chlorthalidone"],
               "potassium": ["potassium chloride", "spironolactone"], "red_yeast_rice": ["red yeast rice"]}


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


_DDI = None


def ddinter() -> dict[frozenset, str]:
    """DDInter drug–drug pairs (open data; CC BY-NC-SA) if downloaded into backend/data/ddinter."""
    global _DDI
    if _DDI is not None:
        return _DDI
    _DDI = {}
    for path in glob.glob(os.path.join(os.path.dirname(__file__), "..", "data", "ddinter", "*.csv")):
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    a, b, lvl = (row.get("Drug_A") or "").lower(), (row.get("Drug_B") or "").lower(), row.get("Level") or ""
                    if a and b and lvl in ("Major", "Moderate", "Minor"):
                        _DDI[frozenset((a, b))] = lvl.lower()
        except (OSError, csv.Error, UnicodeDecodeError):
            continue
    return _DDI


def _context(pid: int = 1) -> dict:
    L = engine.latest_values()
    v = lambda m: (L.get(m) or {}).get("value_num")  # noqa: E731
    meds = [m["name"].lower() for m in db.rows("SELECT name FROM medications WHERE active = 1")]
    flags = set()
    for cls, names in MED_CLASSES.items():
        if any(n in " ".join(meds) for n in names):
            flags.add(cls)
    if (v("egfr") or 99) < 60:
        flags.add("ckd")
    g6 = v("g6pd")
    flags.add("g6pd_unknown" if g6 is None else "g6pd_def" if g6 < 7 else "g6pd_ok")
    if v("b12") is None and v("mma") is None:
        flags.add("b12_unknown")
    if (v("b12") or 999) < 300 or (v("mma") or 0) > 260:
        flags.add("b12_low")
    if (v("selenium") or 0) >= 150:
        flags.add("high_selenium")
    if meds:
        flags.add("any_oral")
    return {"v": v, "L": L, "meds": meds, "flags": flags, "study": _nof1()}


def _nof1() -> dict | None:
    st = db.one("SELECT * FROM studies WHERE status = 'complete' ORDER BY id DESC")
    if not st:
        return None
    r = engine.analyse_study({**st, "data": db.unj(st["data"], {})})
    v = (r.get("verdict") or "").lower()
    summ = (f"{r.get('verdict')}: deep sleep {r.get('mean_on')} vs {r.get('mean_off')} {r.get('unit')} on vs off "
            f"({'+' if (r.get('diff') or 0) > 0 else ''}{r.get('diff')} {r.get('unit')}, {engine.fmt_p(r['p'])})") if r.get("p") is not None else r.get("verdict")
    return {"title": st["title"], "intervention": st["intervention"], "verdict": "helped" if v == "helped" else v, "effect": r.get("diff"),
            "unit": r.get("unit"), "summary": summ}


def _indication(pid_ctx: dict, pid: str) -> tuple[float, str, str | None]:
    """(strength 0–3, reason with the numbers, personalised dose) — the evidence trigger for each product."""
    v, f = pid_ctx["v"], pid_ctx["flags"]
    meds = " ".join(pid_ctx["meds"])
    st = pid_ctx["study"]
    if pid == "vitd":
        d = v("vitd")
        if d is not None and d < 40:
            current = 2000 if "vitamin d" in meds else 0
            add = round(max(1000, (40 - d) * 100) / 1000) * 1000
            dose = f"{current + add:,} IU/day" + (f" (up from your current {current:,} IU)" if current else "")
            return 3, f"25-OH vitamin D is {d} ng/mL (target 40–80) despite {current:,} IU/day" if current else f"25-OH vitamin D is {d} ng/mL", dose
    if pid == "d3_60k" and (v("vitd") or 99) < 20:
        return 3, f"Vitamin D {v('vitd')} ng/mL — deficient; loading dose", None
    if pid == "omega3" and (v("omega3_index") or 99) < 8:
        return 2.5 if "omega" not in meds else 1, f"Omega-3 index {v('omega3_index')}% (target ≥ 8)" + (" — already on 2 g; consider 3 g or check adherence" if "omega" in meds else ""), None
    if pid == "methyl_b" and (v("homocysteine") or 0) > 12:
        return 3, f"Homocysteine {v('homocysteine')} µmol/L, folate {v('folate')}, B12 {v('b12')}, MTHFR {(pid_ctx['L'].get('mthfr_c677t') or {}).get('value_text')}", None
    if pid == "wind_down":
        if st and "magnesium" in (st["intervention"] or "").lower() and st.get("verdict") in ("helped", "Helped"):
            return 3, f"Your N-of-1 showed magnesium helped: {st['summary']}", None
        if st and "magnesium" in (st["intervention"] or "").lower():
            return 0.5, (f"Your magnesium-only N-of-1 gave no reliable signal ({st['summary'].split(': ', 1)[-1]}). Wind-Down adds theanine "
                         f"and glycine — worth testing as a new N-of-1, replacing your current magnesium"), None
    if pid == "mg" and (v("rbc_mg") or 99) < 5:
        return 2, f"RBC magnesium {v('rbc_mg')} mg/dL (optimal 5–6.5)", None
    if pid == "zinc" and (v("zinc") or 999) < 80:
        return 2, f"Zinc {v('zinc')} µg/dL (range 80–120)", None
    if pid == "selenium" and (v("tpo_ab") or 0) > 34 and (v("selenium") or 0) < 150:
        return 1.5, f"Anti-TPO {v('tpo_ab')} with selenium {v('selenium')} µg/L", None
    if pid == "psyllium" and ((v("apob") or 0) > 90 or (v("ldl") or 0) > 100):
        return 2.5, f"ApoB {v('apob')} mg/dL, LDL {v('ldl')} mg/dL", None
    if pid == "iron" and (v("ferritin") or 999) < 30:
        return 3, f"Ferritin {v('ferritin')} ng/mL", None
    if pid == "iv_iron" and (v("ferritin") or 999) < 15 and (v("hemoglobin") or 99) < 12:
        return 3, "Iron-deficiency anaemia", None
    if pid == "b12_im" and ((v("b12") or 999) < 200 or (v("mma") or 0) > 400):
        return 3, f"B12 {v('b12')} pg/mL, MMA {v('mma')}", None
    if pid == "creatine" and (v("almi") or 99) < 8.5:
        return 1.5, f"ALMI {v('almi')} kg/m² (below the longevity target 8.5)", None
    if pid == "rosuva":
        cac, apob = v("cac") or 0, v("apob") or 0
        if cac > 0 and apob > 90:
            return 3, f"Coronary calcium {int(cac)} with ApoB {apob}: ACC/AHA advises statin therapy is reasonable when CAC > 0 (discuss)", None
    if pid == "ezetimibe" and (v("apob") or 0) > 110 and (v("cac") or 0) > 0:
        return 1, "Add-on if ApoB stays above target on a statin", None
    if pid == "metformin" and (v("hba1c") or 0) >= 5.7 and (v("homa_ir") or 0) > 2.5:
        return 1.5, f"HbA1c {v('hba1c')}%, HOMA-IR {v('homa_ir')} (DPP: lifestyle first; metformin if BMI ≥ 35, prior GDM or progression)", None
    if pid == "telmisartan" and (v("abpm_day_sbp") or 0) >= 135:
        return 2.5, f"ABPM daytime {int(v('abpm_day_sbp'))}/{int(v('abpm_day_dbp') or 0)} mmHg with CAC {int(v('cac') or 0)}", None
    if pid == "recover" and (v("almi") or 99) < 8.5:
        return 1.5, f"Lean mass below target (ALMI {v('almi')}); you train hard twice a week", None
    if pid == "calm" and (v("cortisol_night") or 0) > 4:
        return 1.5, f"Late-night cortisol {v('cortisol_night')} nmol/L (flattened rhythm)", None
    return 0, "", None


def screen(item: str, ctx: dict) -> list[dict]:
    out = []
    flags = ctx["flags"] | {"pregnancy"} if engine.profile().get("pregnant") else ctx["flags"]
    for a, b, sev, note in CURATED:
        if a == item and (b in flags or b in ctx["meds"]):
            out.append({"with": b.replace("_", " "), "severity": sev, "note": note, "source": "Telomy curated (NIH ODS / monographs)"})
    if PRODUCTS[item]["kind"] == "medicine":
        name = PRODUCTS[item]["name"].lower().split()[0]
        for m in ctx["meds"]:
            lvl = ddinter().get(frozenset((name, m.split()[0])))
            if lvl:
                out.append({"with": m, "severity": lvl, "note": "Drug–drug interaction", "source": "DDInter"})
    return out


def recommend(goal: str, pid: int = 1) -> dict:
    if goal not in GOALS:
        raise ValueError("Unknown goal")
    ctx = _context(pid)
    items = []
    for key, p in PRODUCTS.items():
        strength, why, dose = _indication(ctx, key)
        goal_fit = goal in p["goals"]
        if strength <= 0 and not (goal_fit and p["kind"] == "formula" and "roadmap" not in p["name"]):
            continue
        if p["kind"] in ("iv",) and strength <= 0:
            continue
        inter = screen(key, ctx)
        blocked = any(i["severity"] == "major" for i in inter)
        base = p["name"].lower().replace("telomy formulas · ", "").split(" (")[0]
        on_already = any(base.split()[0] in m for m in ctx["meds"]) and p["kind"] != "formula"
        overlap = [m for m in ctx["meds"] if any(w in p["contains"].lower() for w in m.split()[:1]) and p["kind"] == "formula"]
        score = strength * 2 + (2 if goal_fit else 0) + {"A": 1.5, "B": 1, "C": 0.3, "D": -1}[p["evidence"]]
        retest = (date.fromisoformat(engine.last_signal_day() or date.today().isoformat()) + timedelta(days=p["retest_days"])).isoformat() if p["retest_days"] else None
        items.append({"id": key, "name": p["name"], "kind": p["kind"], "rx": p["rx"], "evidence": p["evidence"],
                      "dose": dose or p["dose"], "price": p["price"], "why": why or f"Fits your goal ({GOALS[goal].lower()}); evidence grade {p['evidence']}.",
                      "triggered_by_data": strength > 0, "expected": p["expected"], "targets": p["targets"], "retest_on": retest, "contains": p["contains"],
                      "interactions": inter, "blocked": blocked, "already_taking": on_already, "notes": p["notes"], "score": round(score, 1),
                      "overlaps": [f"Contains {m.split()[0]} — replaces your current {m}" for m in overlap],
                      "status": "blocked" if blocked else "discuss" if p["rx"] else
                                ("adjust_dose" if dose else "already_taking") if on_already else
                                "recommended" if strength >= 1 or (goal_fit and strength > 0) else "optional"})
    items.sort(key=lambda x: (x["blocked"], -x["score"]))
    sup = [i for i in items if i["kind"] in ("formula", "supplement") and not i["blocked"] and i["status"] != "already_taking"][:6]
    med = [i for i in items if i["kind"] == "medicine" and i["triggered_by_data"]][:3]
    ivs = [i for i in items if i["kind"] == "iv"]
    return {"goal": goal, "goal_label": GOALS[goal], "supplements": sup, "medicines": med, "ivs": ivs,
            "blocked": [i for i in items if i["blocked"]], "excluded": [{"name": a, "why": b} for a, b in EXCLUDED],
            "already_taking": [i for i in items if i["status"] == "already_taking"],
            "monthly": sum(i["price"] for i in sup if i["status"] != "adjust_dose"), "nof1": ctx["study"],
            "note": "Drafted by Sinc from your Vault. A registered doctor reviews, edits and signs before anything can be ordered. "
                    "Telomy Formulas are FSSAI nutraceuticals — not for medicinal use."}


def submit(goal: str, pid: int = 1, chosen: list[str] | None = None) -> dict:
    r = recommend(goal, pid)
    pool = {i["id"]: i for i in r["supplements"] + r["medicines"] + r["ivs"]}
    items = [pool[c] for c in (chosen or [i["id"] for i in r["supplements"]] + [i["id"] for i in r["medicines"]]) if c in pool]
    if not items:
        raise ValueError("Choose at least one item.")
    plan = {"goal": goal, "goal_label": r["goal_label"], "items": items, "nof1": r["nof1"]}
    pid_ = db.exec_("INSERT INTO rx_plans (patient_id, goal, created_at, state, plan) VALUES (?,?,?,?,?)",
                    (pid, goal, engine.now_iso(), "awaiting_doctor", db.j(plan)))
    return get(pid_)


def get(plan_id: int) -> dict | None:
    r = db.one("SELECT * FROM rx_plans WHERE id = ?", (plan_id,))
    if r:
        r["plan"] = db.unj(r["plan"], {})
        p = db.one("SELECT name FROM patients WHERE id = ?", (r["patient_id"],))
        r["patient"] = p["name"] if p else None
        r["orders"] = db.rows("SELECT * FROM rx_orders WHERE plan_id = ? ORDER BY id DESC", (plan_id,))
    return r


def list_plans(state: str | None = None) -> list[dict]:
    ids = [r["id"] for r in db.rows("SELECT id FROM rx_plans" + (" WHERE state = ?" if state else "") + " ORDER BY id DESC", (state,) if state else ())]
    return [get(i) for i in ids]


def decide(plan_id: int, approve: bool, note: str, keep: list[str] | None = None, doses: dict | None = None,
           doctor: str = "Dr. Meera Rao", reg_no: str = "KMC-TEST-12345") -> dict:
    r = get(plan_id)
    if not r:
        raise LookupError("Plan not found")
    if r["state"] != "awaiting_doctor":
        raise ValueError(f"Plan is already {r['state']}.")
    if not note.strip():
        raise ValueError("A clinical note is required to sign.")
    plan = r["plan"]
    if approve:
        if keep is not None:
            plan["items"] = [i for i in plan["items"] if i["id"] in keep]
            if not plan["items"]:
                raise ValueError("Keep at least one item, or reject the plan.")
        for i in plan["items"]:
            if doses and i["id"] in doses:
                i["dose"], i["dose_edited_by_doctor"] = doses[i["id"]], True
        plan["signed"] = {"doctor": doctor, "reg_no": reg_no, "at": engine.now_iso()}
    db.exec_("UPDATE rx_plans SET state = ?, plan = ?, doctor = ?, reg_no = ?, note = ?, decided_at = ? WHERE id = ?",
             ("approved" if approve else "rejected", db.j(plan), doctor, reg_no, note.strip(), engine.now_iso(), plan_id))
    return get(plan_id)


def order(plan_id: int) -> dict:
    r = get(plan_id)
    if not r or r["state"] != "approved":
        raise PermissionError("Only doctor-approved plans can be ordered.")
    items = r["plan"]["items"]
    channels = sorted({"Licensed pharmacy partner (e-prescription)" if i["kind"] == "medicine" else
                       "Centre infusion bay (booked)" if i["kind"] == "iv" else "Telomy Formulas (FSSAI GMP partner)" for i in items})
    total = sum(i["price"] for i in items)
    oid = db.exec_("INSERT INTO rx_orders (plan_id, created_at, items, total, status, channel) VALUES (?,?,?,?,?,?)",
                   (plan_id, engine.now_iso(), db.j([{"id": i["id"], "name": i["name"], "price": i["price"]} for i in items]), total,
                    "confirmed (test mode — not charged)", " · ".join(channels)))
    for i in items:
        if i["kind"] in ("formula", "supplement", "medicine") and not db.one("SELECT id FROM medications WHERE active = 1 AND name = ?", (i["name"],)):
            db.exec_("INSERT INTO medications (name, dose, frequency, times, reason, prescriber, start_day, active, source) VALUES (?,?,?,?,?,?,?,1,'telomy-rx')",
                     (i["name"], i["dose"], "daily", db.j(["21:00" if "night" in i["dose"] or "bed" in i["dose"] else "09:00"]), i["why"][:120],
                      r["doctor"], engine.now_iso()[:10]))
    return {"id": oid, "total": total, "channels": channels, "message": f"Order placed — ₹{total:,} (test mode, not charged)."}


def prescription_pdf(plan_id: int) -> bytes:
    from io import BytesIO

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    r = get(plan_id)
    if not r or r["state"] != "approved":
        raise PermissionError("Only signed plans have a prescription.")
    st = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Telomy e-prescription (TEST)")
    s = r["plan"]["signed"]
    story = [Paragraph("<b>Telomy Care · e-Prescription</b>", st["Title"]),
             Paragraph("<font color='#9B2C2C'><b>TEST DOCUMENT — NOT A VALID PRESCRIPTION</b></font>", st["Normal"]), Spacer(1, 8),
             Paragraph(f"Patient: {r['patient']} · Date: {s['at'][:10]}", st["Normal"]),
             Paragraph(f"Prescriber: {s['doctor']} · Reg. no. {s['reg_no']} (test)", st["Normal"]), Spacer(1, 10)]
    for k, i in enumerate(r["plan"]["items"], 1):
        tag = "Rx" if i["rx"] else "Nutraceutical — not for medicinal use"
        story.append(Paragraph(f"<b>{k}. {i['name']}</b> — {i['dose']} <i>({tag})</i>", st["Normal"]))
        story.append(Paragraph(f"Reason: {i['why']}. Re-test: {i.get('retest_on') or '—'}", st["Italic"]))
    story += [Spacer(1, 10), Paragraph(f"Clinical note: {r['note']}", st["Normal"]),
              Paragraph("Issued under the Telemedicine Practice Guidelines 2020 (test).", st["Italic"])]
    doc.build(story)
    return buf.getvalue()


def tracking(pid: int = 1) -> list[dict]:
    """For everything taken: did the target marker move since the start date?"""
    out = []
    for m in db.rows("SELECT * FROM medications WHERE active = 1"):
        key = next((k for k, p in PRODUCTS.items() if p["name"].lower().split(" ·")[0].split(" (")[0] in m["name"].lower()
                    or m["name"].lower().split()[0] in p["name"].lower()), None)
        if not key:
            continue
        rows = []
        for t in PRODUCTS[key]["targets"]:
            h = [x for x in engine.marker_history(t) if x["value_num"] is not None]
            before = [x for x in h if x["collected_on"] <= (m["start_day"] or "")]
            after = [x for x in h if x["collected_on"] > (m["start_day"] or "")]
            if before and after:
                rows.append({"marker": t, "before": before[-1]["value_num"], "before_day": before[-1]["collected_on"],
                             "after": after[-1]["value_num"], "after_day": after[-1]["collected_on"]})
        out.append({"name": m["name"], "since": m["start_day"], "product": key, "changes": rows,
                    "message": ("; ".join(f"{c['marker']} {c['before']} → {c['after']}" for c in rows)) or "No retest yet since starting."})
    return out
