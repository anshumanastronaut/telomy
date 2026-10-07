"""Therapies at the longevity centre: catalogue, machines, safety screening, in-session physiology, what is working for
each person, a protocol builder with clinician sign-off, the live therapy floor and the Health-Span Adaptability Index.

Evidence grades: A guideline/strong RCT · B moderate RCTs/meta-analyses · C small trials or mechanistic · D insufficient.
Language follows the Telomy claims firewall (DPR §12.1): "supports", "tracks how your body responds" — never "treats".
"""
import math
import random
from datetime import date, datetime, timedelta

from . import db, engine, physio

SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (id TEXT PRIMARY KEY, modality TEXT, name TEXT, room TEXT, capacity INTEGER, status TEXT,
  last_service TEXT, next_service TEXT, telemetry TEXT);
CREATE TABLE IF NOT EXISTS therapy_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, modality TEXT, device_id TEXT,
  booking_id INTEGER, ts TEXT, minutes REAL, params TEXT, features TEXT, trace TEXT, subjective TEXT, adverse TEXT, status TEXT,
  source TEXT);
CREATE TABLE IF NOT EXISTS therapy_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, goal TEXT, created_at TEXT,
  state TEXT, plan TEXT, doctor TEXT, note TEXT, decided_at TEXT);
CREATE INDEX IF NOT EXISTS ix_ts_patient ON therapy_sessions(patient_id, modality);
"""

CENTRE = {"name": "Halo Longevity Centre (test)", "address": "100 Feet Road, Indiranagar, Bengaluru 560038 (fictitious)",
          "hours": "06:00 – 21:00, all week", "phone": "+91 90000 00020", "medical_director": "Dr. Meera Rao",
          "note": "TEST centre — every member, machine and session here is dummy data."}

R = lambda a, y, j: f"{a} ({y}). {j}."  # noqa: E731

# id: name, category, evidence, minutes, price ₹, default params, params schema, goals {goal: weight}, mechanism,
#     inside (what happens to the body, phase by phase), contraindications (no), cautions, refs
MODALITIES = {
    "cryo": dict(
        name="Whole-body cryotherapy", category="Cold", evidence="C", minutes=3, price=2500, capacity=1,
        params={"chamber_c": -140, "seconds": 180},
        schema=[("chamber_c", "Chamber temperature", "°C", -180, -90), ("seconds", "Exposure", "s", 60, 240)],
        goals={"recovery": 2, "stress": 1, "pain": 2, "sleep": 1},
        mechanism="2–3 min of −110 to −180 °C dry air triggers a sympathetic surge, peripheral vasoconstriction and noradrenaline "
                  "release, followed by a strong parasympathetic rebound as you rewarm.",
        inside=[("0–30 s", "Cold receptors fire; heart rate jumps 8–20 bpm; breathing quickens; skin conductance spikes."),
                ("30–120 s", "Skin falls 8–15 °C while core stays ~37 °C — blood is pulled to the core; blood pressure rises."),
                ("120–180 s", "Noradrenaline peaks (2–3× in studies). HRV is suppressed by ~35%."),
                ("Exit → 20 min", "Parasympathetic rebound: HRV rises 50–100% above baseline (Louis 2020), heart rate settles below "
                                  "baseline, skin rewarms — how fast is your Thermoregulatory Recovery Index.")],
        no=["pregnancy", "uncontrolled_htn", "recent_cardiac", "raynaud", "cold_urticaria", "dvt", "fever", "pacemaker"],
        caution=["cad", "diabetes_neuropathy", "claustrophobia", "alcohol_today", "epilepsy"],
        refs=[R("Louis J et al.", 2020, "Eur J Appl Physiol — HRV after WBC at −10, −60 and −110 °C"),
              R("Costello JT et al.", 2015, "Cochrane Database Syst Rev — WBC for muscle soreness: insufficient evidence")]),
    "cryo_local": dict(
        name="Localised cryotherapy", category="Cold", evidence="C", minutes=8, price=1500, capacity=1,
        params={"chamber_c": -30, "seconds": 480, "area": "Knee"},
        schema=[("chamber_c", "Nozzle temperature", "°C", -160, -20), ("seconds", "Duration", "s", 120, 600)],
        goals={"pain": 2, "recovery": 1},
        mechanism="Targeted cold air or CO₂ to a joint or muscle; local analgesia and reduced swelling.",
        inside=[("During", "Local skin falls to ~5–10 °C; nerve conduction slows, so pain eases for 1–3 h.")],
        no=["raynaud", "cold_urticaria"], caution=["diabetes_neuropathy"],
        refs=[R("Bleakley C et al.", 2004, "Am J Sports Med — cryotherapy in acute soft-tissue injury")]),
    "cold": dict(
        name="Cold plunge", category="Cold", evidence="B", minutes=3, price=800, capacity=2,
        params={"water_c": 8, "minutes": 3}, schema=[("water_c", "Water temperature", "°C", 2, 15), ("minutes", "Immersion", "min", 1, 10)],
        goals={"recovery": 2, "stress": 1, "metabolic": 1},
        mechanism="Cold-water immersion conducts heat ~25× faster than air: a cold-shock response then strong vagal rebound.",
        inside=[("0–30 s", "Cold shock: involuntary gasp, breathing ×2–3, heart rate +15–40 bpm. Control the exhale."),
                ("30 s–3 min", "Shock fades; heart rate settles; skin drops toward water temperature; noradrenaline rises 2–5×."),
                ("After", "Vagal rebound and alertness; muscle soreness is reduced (Machado 2016).")],
        no=["recent_cardiac", "uncontrolled_htn", "raynaud", "cold_urticaria"],
        caution=["cad", "epilepsy", "alcohol_today", "pregnancy", "strength_today"],
        refs=[R("Machado AF et al.", 2016, "Sports Med — CWI temperature and duration for muscle soreness, meta-analysis"),
              R("Søberg S et al.", 2021, "Cell Rep Med — cold and heat exposure, brown fat in winter swimmers"),
              R("Roberts LA et al.", 2015, "J Physiol — post-exercise cold water blunts strength-training adaptations")]),
    "sauna": dict(
        name="Finnish sauna", category="Heat", evidence="B", minutes=20, price=900, capacity=4,
        params={"temp_c": 80, "minutes": 20}, schema=[("temp_c", "Temperature", "°C", 60, 100), ("minutes", "Duration", "min", 5, 30)],
        goals={"cardio": 3, "sleep": 2, "longevity": 2, "recovery": 1, "stress": 1},
        mechanism="Heat stress at 70–100 °C raises cardiac output 60–70 % — cardiovascular load similar to moderate exercise — "
                  "followed by vasodilation and a parasympathetic cool-down.",
        inside=[("0–5 min", "Skin heats to ~39 °C, vessels dilate, sweating starts; heart rate climbs."),
                ("5–20 min", "Heart rate 100–150 bpm, core +0.5–1 °C, HRV suppressed; heat-shock proteins are induced."),
                ("Cool-down 20–30 min", "Heart rate falls 5–12 bpm below where you started; blood pressure ~7 mmHg lower.")],
        no=["recent_cardiac", "fever", "alcohol_today"], caution=["pregnancy", "low_bp", "chf", "diabetes_neuropathy", "cad"],
        refs=[R("Laukkanen T et al.", 2015, "JAMA Intern Med — sauna frequency and fatal CVD / all-cause mortality (KIHD)"),
              R("Laukkanen T et al.", 2019, "Complement Ther Med — cardiovascular and autonomic response to a 30-min sauna")]),
    "sauna_ir": dict(
        name="Infrared sauna", category="Heat", evidence="C", minutes=40, price=1000, capacity=2,
        params={"temp_c": 55, "minutes": 40}, schema=[("temp_c", "Cabin temperature", "°C", 40, 70), ("minutes", "Duration", "min", 15, 60)],
        goals={"recovery": 1, "sleep": 1, "stress": 1, "cardio": 1},
        mechanism="Far-infrared heats tissue directly at lower air temperature; gentler cardiac load, so longer sessions are needed.",
        inside=[("During", "Core +0.3–0.5 °C over 45 min, peak heart rate 80–110 bpm; heavy sweating at a cooler air temperature.")],
        no=["recent_cardiac", "fever", "alcohol_today"], caution=["pregnancy", "low_bp"],
        refs=[R("AJP-RICU comparison", 2025, "FIR sauna vs hot-water immersion thermoregulatory response")]),
    "contrast": dict(
        name="Contrast therapy (sauna ↔ plunge)", category="Heat + cold", evidence="C", minutes=40, price=1500, capacity=2,
        params={"rounds": 3, "temp_c": 85, "water_c": 8}, schema=[("rounds", "Rounds", "", 1, 5)],
        goals={"recovery": 2, "stress": 1},
        mechanism="Alternating vasodilation and vasoconstriction ('vascular pumping'); repeated sympathetic-parasympathetic swings.",
        inside=[("Each round", "10 min heat lifts heart rate toward 120; 2 min cold drops skin temperature and spikes heart rate briefly.")],
        no=["recent_cardiac", "uncontrolled_htn", "raynaud", "fever"], caution=["cad", "alcohol_today"],
        refs=[R("Bieuzen F et al.", 2013, "PLoS One — contrast water therapy and exercise-induced muscle damage, meta-analysis")]),
    "hbot": dict(
        name="Hyperbaric oxygen (medical, 2.0–2.4 ATA)", category="Pressure", evidence="A", minutes=90, price=6000, capacity=1,
        params={"ata": 2.0, "o2_pct": 100, "minutes": 90}, schema=[("ata", "Pressure", "ATA", 1.5, 2.4), ("o2_pct", "Oxygen", "%", 90, 100)],
        goals={"recovery": 1, "longevity": 1, "cognition": 1},
        mechanism="Breathing 100 % oxygen at 2–2.4 atmospheres dissolves 10–15× more oxygen in plasma. Strong evidence for specific "
                  "indications (non-healing diabetic ulcers, CO poisoning, radiation injury); for healthy ageing, evidence is early.",
        inside=[("Compression 10 min", "Ears feel pressure — equalise; heart rate rises 5–15 bpm briefly."),
                ("At pressure", "SpO₂ 99–100 %, plasma oxygen ×10–15; vagal tone rises: heart rate −5 to −15 bpm, HF-HRV +40–60 %."),
                ("Decompression", "Pressure returns to normal over ~10 min; HRV stays elevated for 4–8 h.")],
        no=["pneumothorax", "copd_bullae", "ear_sinus_infection", "fever"], caution=["claustrophobia", "epilepsy", "pacemaker", "chf", "pregnancy"],
        refs=[R("Kranke P et al.", 2015, "Cochrane — HBOT for chronic wounds (diabetic foot ulcers)"),
              R("Lund V et al.", 2003, "Undersea Hyperb Med — vagal tone during hyperbaric hyperoxia"),
              R("Hachmo Y et al.", 2020, "Aging (Albany NY) — telomere length and senescent cells after 60 HBOT sessions (n=35, uncontrolled)")]),
    "hbot_mild": dict(
        name="Mild hyperbaric (1.3 ATA soft chamber)", category="Pressure", evidence="D", minutes=60, price=3500, capacity=1,
        params={"ata": 1.3, "o2_pct": 40, "minutes": 60}, schema=[("ata", "Pressure", "ATA", 1.2, 1.5), ("o2_pct", "Oxygen (concentrator)", "%", 21, 95)],
        goals={"recovery": 1, "stress": 1},
        mechanism="Soft-shell chambers at 1.3 ATA with an oxygen concentrator. Plasma oxygen rises modestly; acute heart rate falls ~7 %.",
        inside=[("At pressure", "SpO₂ ~99 %, heart rate −7 % over 60 min (PMC 2025), mild vagal shift.")],
        no=["pneumothorax", "ear_sinus_infection", "fever"], caution=["claustrophobia", "pregnancy"],
        refs=[R("PMC study", 2025, "Single 1.3 ATA session: HR 63.6 → 58.8 bpm")]),
    "redlight": dict(
        name="Red / near-infrared light (photobiomodulation)", category="Light", evidence="C", minutes=20, price=1200, capacity=2,
        params={"wavelength_nm": "660/850", "irradiance_mw_cm2": 50, "minutes": 20},
        schema=[("irradiance_mw_cm2", "Irradiance", "mW/cm²", 10, 100), ("minutes", "Duration", "min", 5, 30)],
        goals={"skin": 3, "recovery": 2, "pain": 2},
        mechanism="660 nm and 850 nm light is absorbed by cytochrome-c oxidase in mitochondria; nitric oxide release improves local "
                  "blood flow. Effects follow a biphasic dose curve — more is not better.",
        inside=[("During", "Skin warms ~1 °C, perfusion index rises ~25 %, heart rate drifts down slightly."),
                ("Dose", "Delivered fluence = irradiance × time; 10–60 J/cm² is the studied window for skin and muscle.")],
        no=[], caution=["photosensitising_meds", "active_cancer", "pregnancy", "epilepsy"],
        refs=[R("Wunsch A, Matuschka K", 2014, "Photomed Laser Surg — RCT of red/NIR light on skin collagen and wrinkles"),
              R("Ferraresi C, Huang YY, Hamblin MR", 2016, "J Biophotonics — PBM in human muscle performance")]),
    "pemf": dict(
        name="PEMF (pulsed electromagnetic field)", category="Electromagnetic", evidence="C", minutes=25, price=1500, capacity=2,
        params={"intensity_gauss": 20, "frequency_hz": 10, "minutes": 25},
        schema=[("intensity_gauss", "Intensity", "G", 5, 60), ("frequency_hz", "Frequency", "Hz", 1, 50), ("minutes", "Duration", "min", 10, 45)],
        goals={"sleep": 2, "pain": 2, "recovery": 1, "stress": 1},
        mechanism="Time-varying magnetic fields induce small currents in tissue. Proven for delayed fracture healing; sleep and "
                  "recovery effects are less established — which is exactly why Telomy measures them per person.",
        inside=[("During", "Breathing slows, heart rate −2 to −4 bpm, HRV rises ~10 % in responders; skin conductance falls.")],
        no=["pacemaker", "pregnancy"], caution=["epilepsy", "active_cancer"],
        refs=[R("Griffin XL et al.", 2011, "Cochrane — electromagnetic stimulation for delayed union / non-union of long-bone fractures")]),
    "compression": dict(
        name="Pneumatic compression", category="Pressure", evidence="B", minutes=30, price=1000, capacity=3,
        params={"pressure_mmhg": 80, "minutes": 30}, schema=[("pressure_mmhg", "Pressure", "mmHg", 30, 120), ("minutes", "Duration", "min", 15, 60)],
        goals={"recovery": 2, "pain": 1},
        mechanism="Sequential cuffs push fluid proximally; reduces perceived soreness after exercise and helps lymphoedema.",
        inside=[("During", "Venous return rises, so stroke volume rises and heart rate falls 2–4 bpm; legs feel lighter afterwards.")],
        no=["dvt", "pad_severe", "chf"], caution=["anticoagulants", "diabetes_neuropathy"],
        refs=[R("Dupuy O et al.", 2018, "Front Physiol — recovery techniques meta-analysis (massage and compression effective for soreness)")]),
    "vibroacoustic": dict(
        name="Vibroacoustic therapy", category="Sound & vibration", evidence="C", minutes=30, price=1500, capacity=1,
        params={"frequency_hz": 40, "minutes": 30}, schema=[("frequency_hz", "Frequency", "Hz", 30, 120), ("minutes", "Duration", "min", 15, 45)],
        goals={"stress": 2, "sleep": 2, "pain": 1},
        mechanism="Low-frequency sound (30–120 Hz) delivered through a bed; relaxation and pain modulation via mechanoreceptors.",
        inside=[("During", "Breathing slows by ~3/min, heart rate −4 bpm, HRV +15–20 % in responders; skin conductance falls.")],
        no=[], caution=["pacemaker", "pregnancy", "epilepsy", "dvt"],
        refs=[R("Naghdi L et al.", 2015, "Pain Res Manag — low-frequency sound stimulation in fibromyalgia")]),
    "h2_inhal": dict(
        name="Molecular hydrogen inhalation", category="Gas", evidence="D", minutes=60, price=1200, capacity=2,
        params={"h2_pct": 2.0, "flow_ml_min": 600, "minutes": 60},
        schema=[("h2_pct", "H₂ concentration", "%", 1, 4), ("flow_ml_min", "Flow", "mL/min", 150, 1500)],
        goals={"recovery": 1, "longevity": 1},
        mechanism="H₂ is a selective antioxidant in animal models (Ohsawa 2007). Human evidence is small and mixed; acute "
                  "physiology changes very little — Telomy will show you whether anything moves for you.",
        inside=[("During", "No measurable change in heart rate, HRV or SpO₂ is expected. Effects, if any, would be slow.")],
        no=[], caution=[],
        refs=[R("Ohsawa I et al.", 2007, "Nat Med — hydrogen acts as a therapeutic antioxidant (rodent)"),
              R("Ichihara M et al.", 2015, "Med Gas Res — review of 321 hydrogen studies")]),
    "h2_water": dict(
        name="Hydrogen-rich water", category="Gas", evidence="D", minutes=1, price=150, capacity=10,
        params={"ppm": 1.6, "ml": 500}, schema=[("ppm", "H₂", "ppm", 0.5, 3), ("ml", "Volume", "mL", 250, 1000)],
        goals={"recovery": 1}, mechanism="Dissolved H₂; part of the Telomy Halo v1 modality list.",
        inside=[("After drinking", "No acute physiological change expected.")], no=[], caution=[],
        refs=[R("Ichihara M et al.", 2015, "Med Gas Res — review")]),
    "float": dict(
        name="Flotation (REST)", category="Sensory", evidence="B", minutes=60, price=2500, capacity=1,
        params={"minutes": 60}, schema=[("minutes", "Duration", "min", 45, 90)],
        goals={"stress": 3, "sleep": 1, "pain": 1},
        mechanism="Floating in skin-temperature Epsom-salt water with minimal light and sound reduces sensory input.",
        inside=[("During", "Blood pressure −6 mmHg, heart rate −6 bpm, breathing slows; anxiety falls (Feinstein 2018).")],
        no=["epilepsy"], caution=["claustrophobia", "skin_lesions", "low_bp"],
        refs=[R("Feinstein JS et al.", 2018, "PLoS One — flotation-REST reduces anxiety"),
              R("Kjellgren A, Westman J", 2014, "BMC Complement Altern Med — flotation RCT, stress and pain")]),
    "breathwork": dict(
        name="Resonance breathing / HRV biofeedback", category="Breath", evidence="B", minutes=10, price=0, capacity=6,
        params={"breaths_per_min": 6, "minutes": 10}, schema=[("breaths_per_min", "Pace", "/min", 4.5, 7), ("minutes", "Duration", "min", 5, 20)],
        goals={"stress": 3, "sleep": 1, "cardio": 1},
        mechanism="Breathing near 6/min aligns heart-rate oscillations with breathing (resonance), maximising RSA and baroreflex gain.",
        inside=[("During", "HRV rises 50–100 % while you breathe slowly; heart rate swings widen with each breath."),
                ("After", "A small carry-over in resting HRV; regular practice lowers anxiety (Goessl 2017).")],
        no=[], caution=[], refs=[R("Goessl VC et al.", 2017, "Psychol Med — HRV biofeedback for stress and anxiety, meta-analysis")]),
    "ihht": dict(
        name="Intermittent hypoxic-hyperoxic training", category="Gas", evidence="C", minutes=40, price=2500, capacity=1,
        params={"cycles": 6, "spo2_target": 86}, schema=[("cycles", "Cycles", "", 3, 8), ("spo2_target", "Hypoxic SpO₂ target", "%", 82, 90)],
        goals={"cognition": 1, "metabolic": 1, "cardio": 1},
        mechanism="Alternating 10–12 % and 30–40 % oxygen: brief hypoxia triggers HIF-1α adaptations; hyperoxia speeds recovery.",
        inside=[("Hypoxic 5 min", "SpO₂ falls to the target (≈85–88 %), heart rate +8–10 bpm."),
                ("Hyperoxic 3 min", "SpO₂ back to 98–99 % within a minute; heart rate settles.")],
        no=["pregnancy", "recent_cardiac", "uncontrolled_htn", "severe_anaemia"], caution=["osa", "cad"],
        refs=[R("Serebrovska TV et al.", 2019, "Int J Mol Sci — IHHT in mild cognitive impairment (pilot)")]),
    "ewot": dict(
        name="Exercise with oxygen (EWOT)", category="Gas", evidence="D", minutes=15, price=1500, capacity=1,
        params={"o2_lpm": 8, "minutes": 15}, schema=[("o2_lpm", "Oxygen flow", "L/min", 4, 15)],
        goals={"cardio": 1}, mechanism="Cycling while breathing enriched oxygen from a reservoir bag. Little controlled evidence.",
        inside=[("During", "Exercise heart rate 120–140 bpm with SpO₂ held near 99 %.")],
        no=["recent_cardiac", "uncontrolled_htn"], caution=["cad"], refs=[]),
    "iv": dict(
        name="IV infusion", category="Infusion", evidence="C", minutes=45, price=5000, capacity=4,
        params={"formula": "Hydration + electrolytes", "volume_ml": 500},
        schema=[("volume_ml", "Volume", "mL", 100, 1000)], goals={"recovery": 1},
        mechanism="Clinician-prescribed infusions. Strong evidence only where a deficiency is proven (e.g. IV iron for iron-deficiency "
                  "anaemia). Formulas and safety checks live in Telomy Rx.",
        inside=[("During", "Heart rate +1–3 bpm from fluid load; little else changes.")],
        no=[], caution=["chf", "ckd"],
        refs=[R("Ali A et al.", 2009, "J Altern Complement Med — Myers' cocktail vs placebo in fibromyalgia: no significant difference")]),
    "wbv": dict(
        name="Whole-body vibration", category="Mechanical", evidence="C", minutes=10, price=600, capacity=2,
        params={"frequency_hz": 30, "amplitude_mm": 2, "minutes": 10}, schema=[("frequency_hz", "Frequency", "Hz", 15, 45)],
        goals={"metabolic": 1, "longevity": 1}, mechanism="Platform vibration loads bone and muscle; modest BMD effects in older women.",
        inside=[("During", "Heart rate +10–15 bpm; muscle activation similar to light exercise.")],
        no=["pregnancy", "dvt", "retinal_detachment"], caution=["pacemaker", "epilepsy"],
        refs=[R("Slatkovska L et al.", 2010, "Osteoporos Int — WBV and BMD, meta-analysis")]),
    "eswt": dict(
        name="Shockwave therapy (ESWT)", category="Mechanical", evidence="B", minutes=15, price=2500, capacity=1,
        params={"pulses": 2000, "energy_mj_mm2": 0.12, "area": "Heel"}, schema=[("pulses", "Pulses", "", 1000, 3000)],
        goals={"pain": 2}, mechanism="Acoustic pressure waves for plantar fasciitis and calcific tendinopathy.",
        inside=[("During", "Local discomfort; no systemic physiological change.")],
        no=["pregnancy"], caution=["anticoagulants", "active_cancer"],
        refs=[R("Schmitz C et al.", 2015, "Br Med Bull — ESWT for orthopaedic conditions, systematic review")]),
    "acupuncture": dict(
        name="Acupuncture", category="Manual", evidence="B", minutes=30, price=1500, capacity=2,
        params={"points": 12, "minutes": 30}, schema=[("minutes", "Duration", "min", 20, 45)], goals={"pain": 2, "stress": 1},
        mechanism="Needling; modest benefit over sham for chronic pain in IPD meta-analysis.",
        inside=[("During", "Heart rate −3 bpm, HRV +10 % in many people; relaxation.")], no=[], caution=["anticoagulants"],
        refs=[R("Vickers AJ et al.", 2018, "J Pain — acupuncture for chronic pain, IPD meta-analysis")]),
    "halo": dict(
        name="Telomy Halo (adaptive chamber, prototype)", category="Multi-modal", evidence="D", minutes=45, price=4000, capacity=1,
        params={"program": "Sleep loop", "minutes": 45}, schema=[("minutes", "Duration", "min", 30, 60)],
        goals={"sleep": 2, "stress": 2, "recovery": 1},
        mechanism="Phase 2 device: 3-zone PEMF, whole-body PBM, vibroacoustic + rocking, FIR warming, guided breathing and closed-loop "
                  "acoustic stimulation in slow-wave sleep (CLAS; Ngo 2013). Investigational — data model ready, device not yet deployed.",
        inside=[("Induction", "Warming, rocking and paced breathing lower heart rate ~5 bpm and lift HRV ~20 %."),
                ("Sleep loop", "CLAS clicks phase-locked to slow oscillations (+~44 % delta in studies).")],
        no=["pacemaker", "pregnancy"], caution=["epilepsy", "active_cancer", "photosensitising_meds"],
        refs=[R("Ngo HV et al.", 2013, "Neuron — auditory closed-loop stimulation of the sleep slow oscillation")]),
}

NOT_OFFERED = {"ozone": "Ozone therapy — the US FDA classifies ozone as a toxic gas with no proven medical use (21 CFR 801.415); "
                        "Telomy does not list it."}

GOALS = {"sleep": "Deeper sleep", "recovery": "Recovery & soreness", "stress": "Stress & nervous system", "cardio": "Heart & blood pressure",
         "metabolic": "Metabolic health", "longevity": "Healthy ageing", "pain": "Pain & joints", "skin": "Skin & collagen",
         "cognition": "Focus & cognition"}
GRADE_W = {"A": 3, "B": 2.5, "C": 1.5, "D": 0.7}

DEVICES = [
    ("CRY-1", "cryo", "Electric cryo chamber (−90 to −180 °C, nitrogen-free)", "Cold room", 1),
    ("CLD-1", "cold", "Cold plunge 1 (2–15 °C chiller)", "Cold room", 1), ("CLD-2", "cold", "Cold plunge 2", "Cold room", 1),
    ("LCR-1", "cryo_local", "Localised cryo (CO₂ nozzle)", "Treatment 2", 1),
    ("SAU-1", "sauna", "Finnish sauna (4 seats, 60–100 °C)", "Heat room", 4),
    ("SIR-1", "sauna_ir", "Infrared cabin 1", "Heat room", 1), ("SIR-2", "sauna_ir", "Infrared cabin 2", "Heat room", 1),
    ("HBO-1", "hbot", "Hard-shell HBOT 2.4 ATA (supervised, medical)", "Pressure suite", 1),
    ("HBM-1", "hbot_mild", "Soft chamber 1.3 ATA + O₂ concentrator", "Pressure suite", 1),
    ("PBM-1", "redlight", "Full-body red/NIR bed 660/850 nm", "Light room", 1), ("PBM-2", "redlight", "Red/NIR panel", "Light room", 1),
    ("PMF-1", "pemf", "Bonphul PEMF bed (3-zone)", "Recovery lounge", 1), ("PMF-2", "pemf", "PEMF mat", "Recovery lounge", 1),
    ("CMP-1", "compression", "Compression boots 1", "Recovery lounge", 1), ("CMP-2", "compression", "Compression boots 2", "Recovery lounge", 1),
    ("CMP-3", "compression", "Compression boots 3", "Recovery lounge", 1),
    ("VBA-1", "vibroacoustic", "Vibroacoustic bed", "Recovery lounge", 1),
    ("H2I-1", "h2_inhal", "Hydrogen inhaler 1 (600 mL/min)", "Recovery lounge", 1), ("H2I-2", "h2_inhal", "Hydrogen inhaler 2", "Recovery lounge", 1),
    ("FLT-1", "float", "Float pod", "Float room", 1), ("IHT-1", "ihht", "IHHT system", "Treatment 1", 1),
    ("EWT-1", "ewot", "EWOT bike", "Treatment 1", 1), ("IVC-1", "iv", "IV chair 1", "Infusion bay", 1), ("IVC-2", "iv", "IV chair 2", "Infusion bay", 1),
    ("IVC-3", "iv", "IV chair 3", "Infusion bay", 1), ("IVC-4", "iv", "IV chair 4", "Infusion bay", 1),
    ("CNT-1", "contrast", "Contrast circuit (sauna + plunge)", "Heat room", 2),
    ("HAL-0", "halo", "Telomy Halo prototype (not in service)", "R&D", 1),
]

# ----------------------------------------------------------------------------- setup


def init():
    with db.tx() as c:
        c.executescript(SCHEMA)


def _theta_for(pid: int) -> dict:
    if pid == 1:
        L = engine.latest_values()
        g = lambda m: (L.get(m) or {}).get("value_num")  # noqa: E731
        b = lambda m, d=60: (engine.signal_baseline(m, days=d) or {}).get("mean")  # noqa: E731
        return physio.theta_from({"age": engine.age_on() or 34, "rhr": b("rhr") or 58, "hrv": b("hrv") or 54, "vo2max": g("vo2max_lab"),
                                  "hba1c": g("hba1c"), "bmi": 25.5, "pwv": g("pwv"), "sbp": b("sbp") or 128, "spo2": b("spo2") or 97})
    r = db.one("SELECT * FROM patients WHERE id = ?", (pid,))
    s = db.unj(r["data"], {}) if r else {}
    return physio.theta_from({"age": r["age"] if r else 45, "rhr": 74 - 0.5 * ((s.get("vo2max") or 38) - 35), "hrv": s.get("hrv", 45),
                              "vo2max": s.get("vo2max"), "hba1c": s.get("hba1c"), "bmi": s.get("bmi"), "sbp": s.get("sbp")})


def schedule_p1(start: date, days: int, sauna_days: set, hard_days: set, away: set = frozenset()) -> dict[str, list]:
    """The full-Vault member's therapy history over the last 70 days (separate RNG keeps the wearable seed stable)."""
    rnd = random.Random(7)
    out: dict[str, list] = {}
    first = start + timedelta(days=days - 70)
    hbot_block = {first + timedelta(days=d) for d in (24, 25, 26, 27, 28, 31, 32, 33, 34, 35)}
    temps = [-110, -140, -175]
    hbot_block = {d for d in hbot_block if d not in away}
    for i in range(70):
        d = first + timedelta(days=i)
        if d in away:  # travelling — no centre visits
            continue
        if d in sauna_days:
            out.setdefault("sauna", []).append((d, 18, {"temp_c": rnd.choice([75, 80, 85]), "minutes": rnd.choice([15, 20, 20])}))
        if d in hbot_block:
            out.setdefault("hbot_mild", []).append((d, 11, {"ata": 1.3, "o2_pct": 40, "minutes": 60}))
        if rnd.random() < 0.22 and d not in sauna_days:
            out.setdefault("cryo", []).append((d, 8, {"chamber_c": temps[len(out.get("cryo", [])) % 3], "seconds": 180}))
        if rnd.random() < 0.16 and d not in hard_days:
            out.setdefault("cold", []).append((d, 7, {"water_c": rnd.choice([6, 8, 10]), "minutes": 3}))
        if rnd.random() < 0.2:
            out.setdefault("redlight", []).append((d, 9, {"wavelength_nm": "660/850", "irradiance_mw_cm2": rnd.choice([40, 50, 60]), "minutes": 20}))
        if rnd.random() < 0.2:
            out.setdefault("pemf", []).append((d, 20, {"intensity_gauss": rnd.choice([15, 20, 25]), "frequency_hz": 10, "minutes": 25}))
        if d in hard_days and rnd.random() < 0.45:
            out.setdefault("compression", []).append((d, 17, {"pressure_mmhg": 80, "minutes": 30}))
        if rnd.random() < 0.1:
            out.setdefault("vibroacoustic", []).append((d, 19, {"frequency_hz": 40, "minutes": 30}))
        if rnd.random() < 0.12:
            out.setdefault("h2_inhal", []).append((d, 10, {"h2_pct": 2.0, "flow_ml_min": 600, "minutes": 60}))
    for k in (9, 30, 51):
        out.setdefault("iv", []).append((first + timedelta(days=k), 12, {"formula": "Myers' cocktail", "volume_ml": 250}))
    return out


EFFECTS_P1 = {  # embedded next-night effects (ground truth for the engine; documented in tests)
    "cryo": {"hrv": 3.5}, "cold": {"hrv": 3.0}, "pemf": {"deep_sleep": 0.15}, "vibroacoustic": {"deep_sleep": 0.1},
}


def _subjective(mod: str, rnd) -> dict:
    d = {"cryo": (2, -1.5, 0.5), "cold": (2, -1, 0.5), "sauna": (0.5, -0.5, 1.5), "contrast": (1.5, -1, 1), "hbot": (0.5, 0, 0.5),
         "hbot_mild": (0.4, 0, 0.6), "redlight": (0.3, -0.8, 0.5), "pemf": (0.3, -1.2, 1.2), "compression": (0.5, -2, 0.8),
         "vibroacoustic": (0.2, -0.6, 2), "h2_inhal": (0.3, 0, 0.3), "float": (0.4, -0.8, 2.5), "iv": (1, 0, 0.3),
         "breathwork": (0.5, 0, 2), "ihht": (0.5, 0, 0.2)}.get(mod, (0.3, -0.3, 0.5))
    pre = {"energy": rnd.randint(4, 7), "pain": rnd.randint(1, 4), "calm": rnd.randint(4, 7)}
    post = {k: max(0, min(10, round(pre[k] + d[i] + rnd.gauss(0, 0.9)))) for i, k in enumerate(("energy", "pain", "calm"))}
    return {"pre": pre, "post": post}


ADVERSE = {"hbot": (0.03, "Ear discomfort during compression"), "hbot_mild": (0.02, "Ear discomfort"), "cryo": (0.01, "Skin redness on calves"),
           "sauna": (0.02, "Light-headed on standing"), "iv": (0.03, "Bruise at cannula site"), "cold": (0.01, "Shivering > 20 min"),
           "ihht": (0.02, "Headache after session")}


def seed(rnd: random.Random, today: date, p1: dict[str, list]):
    init()
    now = engine.now_iso()
    for did, mod, name, room, cap in DEVICES:
        status = "maintenance" if did == "PMF-2" else "not_in_service" if did == "HAL-0" else "available"
        last = (today - timedelta(days=rnd.randint(5, 80))).isoformat()
        db.exec_("INSERT INTO devices (id, modality, name, room, capacity, status, last_service, next_service, telemetry) VALUES (?,?,?,?,?,?,?,?,?)",
                 (did, mod, name, room, cap, status, last, (date.fromisoformat(last) + timedelta(days=90)).isoformat(), "{}"))
    have = {r["id"] for r in db.rows("SELECT id FROM services")}
    for mid, m in MODALITIES.items():
        if mid not in have and mid not in ("h2_water", "halo", "breathwork"):
            db.exec_("INSERT INTO services (id, name, minutes, price, capacity, category, evidence, targets) VALUES (?,?,?,?,?,?,?,?)",
                     (mid, m["name"], max(15, m["minutes"]), m["price"], m["capacity"], "Therapy", m["evidence"], db.j(list(m["goals"]))))
        elif mid in have:
            db.exec_("UPDATE services SET name = ?, evidence = ? WHERE id = ?", (m["name"], m["evidence"], mid))
    # members: extra bookings for the new modalities over the same 62 days
    members = [r["id"] for r in db.rows("SELECT id FROM patients WHERE member = 1 AND id != 1")]
    extra = ["cryo", "pemf", "compression", "redlight", "vibroacoustic", "h2_inhal", "float", "sauna_ir", "contrast", "hbot_mild", "cryo_local", "ihht"]
    for d in range(-62, 8):
        day = today + timedelta(days=d)
        for _ in range(rnd.randint(14, 22)):
            mod = rnd.choice(extra)
            hour = rnd.choice([7, 8, 9, 10, 11, 12, 15, 16, 17, 18, 19, 20])
            status = "completed" if d < 0 else "booked" if d > 0 else "checked_in"
            db.exec_("INSERT INTO bookings (patient_id, service_id, ts, status, price) VALUES (?,?,?,?,?)",
                     (rnd.choice(members), mod, f"{day.isoformat()}T{hour:02d}:{rnd.choice(['00', '30'])}:00", status, MODALITIES[mod]["price"]))
    # the full-Vault member: bookings mirror the logged schedule
    db.exec_(f"DELETE FROM bookings WHERE patient_id = 1 AND service_id IN ({','.join('?' * len(MODALITIES))})", tuple(MODALITIES))
    th1 = _theta_for(1)
    hrv = dict(engine.series("hrv"))
    base = engine.signal_baseline("hrv", days=90)
    for mod, items in p1.items():
        days_done: list[date] = []
        for d, hour, params in items:
            status = "completed" if d < today else "booked"
            bid = db.exec_("INSERT INTO bookings (patient_id, service_id, ts, status, price) VALUES (1,?,?,?,?)",
                           (mod, f"{d.isoformat()}T{hour:02d}:00:00", status, MODALITIES[mod]["price"]))
            if status != "completed":
                continue
            prior = sum(1 for x in days_done if 0 < (d - x).days <= 5)
            day_state = (hrv.get(d.isoformat(), base["mean"]) / base["mean"]) if base else 1.0
            _record(1, mod, params, f"{d.isoformat()}T{hour:02d}:00:00", th1, bid, rnd, prior, max(0.7, min(1.2, day_state)), keep_trace=True)
            days_done.append(d)
    # members' completed therapy bookings → sessions with features (traces not stored, to keep the DB small)
    cache: dict[int, dict] = {}
    rows = db.rows(f"""SELECT * FROM bookings WHERE patient_id != 1 AND status = 'completed' AND service_id IN ({','.join('?' * len(MODALITIES))})""",
                   tuple(MODALITIES))
    for b in rows:
        th = cache.setdefault(b["patient_id"], _theta_for(b["patient_id"]))
        mod = b["service_id"]
        _record(b["patient_id"], mod, dict(MODALITIES[mod]["params"]), b["ts"], th, b["id"], rnd, 0, rnd.uniform(0.85, 1.1), keep_trace=False, dt=5)
    db.exec_("INSERT INTO therapy_plans (patient_id, goal, created_at, state, plan, doctor, note, decided_at) VALUES (?,?,?,?,?,?,?,?)",
             (1, "sleep", now, "active", db.j({"items": [], "seeded": True}), "Dr. Meera Rao", "Seeded example — rebuild below.", now))


def _record(pid, mod, params, ts, th, booking_id, rnd, prior, day_state, keep_trace=True, dt=1):
    p = dict(MODALITIES[mod]["params"], **params)
    if mod in ("cryo", "cryo_local"):
        p.setdefault("seconds", 180)
    tr = physio.simulate(mod, p, th, seed=rnd.randint(0, 10 ** 6), prior_sessions=prior, day_state=day_state, step=5 if keep_trace else 15, dt=dt)
    f = physio.analyse(mod, tr, p, th["age"])
    adv = None
    if mod in ADVERSE and rnd.random() < ADVERSE[mod][0]:
        adv = ADVERSE[mod][1]
    dev = db.one("SELECT id FROM devices WHERE modality = ? ORDER BY id LIMIT 1", (mod,))
    return db.exec_("""INSERT INTO therapy_sessions (patient_id, modality, device_id, booking_id, ts, minutes, params, features, trace, subjective,
                       adverse, status, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (pid, mod, dev["id"] if dev else None, booking_id, ts, p.get("minutes", MODALITIES[mod]["minutes"]), db.j(p), db.j(f),
                     db.j(tr) if keep_trace else None, db.j(_subjective(mod, rnd)), adv, "completed", tr["source"]))


# ----------------------------------------------------------------------------- safety screening

def conditions_for(pid: int) -> dict[str, str]:
    """Condition keys → human reason, derived from the Vault (labs, meds, profile) — never asked twice."""
    c: dict[str, str] = {}
    if pid == 1:
        L = engine.latest_values()
        v = lambda m: (L.get(m) or {}).get("value_num")  # noqa: E731
        prof = engine.profile()
        if (v("cac") or 0) > 0:
            c["cad"] = f"Coronary plaque on CT (CAC {int(v('cac'))})"
        if (v("abpm_day_sbp") or 0) >= 160 or ((engine.signal_baseline("sbp", days=30) or {}).get("mean") or 0) >= 160:
            c["uncontrolled_htn"] = "Blood pressure ≥ 160 systolic"
        if (v("g6pd") or 99) < 7:
            c["g6pd_def"] = "G6PD deficiency"
        if (v("ahi") or 0) >= 5:
            c["osa"] = f"Sleep apnoea (AHI {v('ahi')})"
        if (v("egfr") or 99) < 30:
            c["ckd"] = "eGFR < 30"
        if (v("abi") or 1.1) < 0.5:
            c["pad_severe"] = "Severe peripheral artery disease (ABI < 0.5)"
        meds = [m["name"].lower() for m in db.rows("SELECT name FROM medications WHERE active = 1")]
        if any(k in " ".join(meds) for k in ("doxycycline", "isotretinoin", "amiodarone", "hydrochlorothiazide")):
            c["photosensitising_meds"] = "Photosensitising medicine"
        if any(k in " ".join(meds) for k in ("warfarin", "apixaban", "rivaroxaban", "dabigatran")):
            c["anticoagulants"] = "Anticoagulant"
        day = engine.last_signal_day()
        if day and db.one("SELECT 1 AS x FROM events WHERE kind = 'alcohol' AND substr(ts,1,10) = ?", (day,)):
            c["alcohol_today"] = "Alcohol logged today"
        if day and db.one("SELECT 1 AS x FROM events WHERE kind = 'workout_hard' AND substr(ts,1,10) = ?", (day,)):
            c["strength_today"] = "Hard/strength session today"
        for k in prof.get("conditions_keys", []):
            c[k] = k.replace("_", " ").capitalize()
        return c
    r = db.one("SELECT * FROM patients WHERE id = ?", (pid,))
    s = db.unj(r["data"], {}) if r else {}
    if "Hypertension" in s.get("conditions", []) and s.get("sbp", 0) >= 160:
        c["uncontrolled_htn"] = f"SBP {s['sbp']}"
    if s.get("egfr", 99) < 30:
        c["ckd"] = "eGFR < 30"
    x = random.Random(1000 + pid)
    for key, p, why in (("pacemaker", 0.02 if r and r["age"] > 60 else 0.003, "Pacemaker / implanted device"), ("raynaud", 0.03, "Raynaud's"),
                        ("claustrophobia", 0.05, "Claustrophobia"), ("pregnancy", 0.04 if r and r["sex"] == "female" and r["age"] < 42 else 0, "Pregnant"),
                        ("epilepsy", 0.01, "Epilepsy"), ("g6pd_def", 0.03 if r and r["sex"] == "male" else 0.01, "G6PD deficiency")):
        if x.random() < p:
            c[key] = why
    return c


def screen(pid: int, modality: str | None = None) -> list[dict]:
    cond = conditions_for(pid)
    out = []
    for mid, m in MODALITIES.items():
        if modality and mid != modality:
            continue
        no = [cond[k] for k in m["no"] if k in cond]
        cau = [cond[k] for k in m["caution"] if k in cond]
        status = "not_suitable" if no else "caution" if cau else "ok"
        why = ("Not suitable: " + "; ".join(no)) if no else ("Check with your clinician: " + "; ".join(cau)) if cau else "No contraindication found in your Vault."
        out.append({"modality": mid, "name": m["name"], "status": status, "reasons": no + cau, "summary": why})
    return out


# ----------------------------------------------------------------------------- what is working for me

def _sessions(pid, mod=None, with_trace=False):
    cols = "id, patient_id, modality, device_id, ts, minutes, params, features, subjective, adverse, status, source" + (", trace" if with_trace else "")
    q = f"SELECT {cols} FROM therapy_sessions WHERE patient_id = ?" + (" AND modality = ?" if mod else "") + " ORDER BY ts"
    rows = db.rows(q, (pid, mod) if mod else (pid,))
    for r in rows:
        for k in ("params", "features", "subjective") + (("trace",) if with_trace else ()):
            r[k] = db.unj(r[k], {})
    return rows


def _slope(ys):
    pts = [(i, y) for i, y in enumerate(ys) if y is not None]
    if len(pts) < 4:
        return None
    mx, my = sum(i for i, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)
    sxx = sum((i - mx) ** 2 for i, _ in pts)
    return sum((i - mx) * (y - my) for i, y in pts) / sxx if sxx else None


KEY_METRICS = {  # metric, label, unit, better
    "cryo": [("hr_peak_delta", "Heart-rate surge", "bpm", None), ("rebound_pct", "HRV rebound at 20 min", "%", "high"),
             ("rewarm_half_min", "Rewarming half-time", "min", "low"), ("k_recovery", "Recovery constant k", "/min", "high"),
             ("skin_drop", "Skin temperature drop", "°C", None)],
    "cold": [("hr_peak_delta", "Cold-shock heart-rate spike", "bpm", "low"), ("rebound_pct", "HRV rebound", "%", "high"),
             ("rewarm_half_min", "Rewarming half-time", "min", "low")],
    "sauna": [("hr_peak", "Peak heart rate", "bpm", None), ("cardio_load_min", "Minutes above 100 bpm", "min", None),
              ("core_rise", "Core temperature rise", "°C", None), ("hr_post_delta", "Heart rate after cool-down vs before", "bpm", "low")],
    "sauna_ir": [("hr_peak", "Peak heart rate", "bpm", None), ("core_rise", "Core temperature rise", "°C", None)],
    "hbot": [("spo2_peak", "SpO₂ at pressure", "%", None), ("hr_stable_delta", "Heart rate at pressure vs before", "bpm", None),
             ("rmssd_stable_pct", "HRV at pressure", "%", "high")],
    "hbot_mild": [("spo2_peak", "SpO₂ at pressure", "%", None), ("hr_stable_delta", "Heart rate at pressure vs before", "bpm", None),
                  ("rmssd_stable_pct", "HRV at pressure", "%", "high")],
    "redlight": [("perf_change_pct", "Skin perfusion change", "%", "high"), ("dose_j_cm2", "Delivered dose", "J/cm²", None)],
}
DEFAULT_METRICS = [("hr_peak_delta", "Heart-rate change", "bpm", None), ("rebound_pct", "HRV after vs before", "%", "high")]


def response(pid: int = 1) -> list[dict]:
    """Per modality: in-session fingerprint, trend, next-day effects, subjective change, cost — and an honest verdict."""
    table = engine.effect_table() if pid == 1 else []
    out = []
    for mod in sorted({r["modality"] for r in db.rows("SELECT DISTINCT modality FROM therapy_sessions WHERE patient_id = ?", (pid,))}):
        ss = _sessions(pid, mod)
        m = MODALITIES[mod]
        feats = [s["features"] for s in ss]
        metrics = []
        for key, label, unit, better in KEY_METRICS.get(mod, DEFAULT_METRICS):
            vals = [f.get(key) for f in feats if f.get(key) is not None]
            if not vals:
                continue
            sl = _slope(vals)
            lit = next((c for c in (feats[-1].get("vs_literature") or []) if c["metric"] == key), None)
            metrics.append({"key": key, "label": label, "unit": unit, "mean": round(sum(vals) / len(vals), 3 if key == "k_recovery" else 1), "last": vals[-1],
                            "first": vals[0], "trend_per_session": round(sl, 3) if sl is not None else None,
                            "improving": (sl > 0) == (better == "high") if sl and better else None,
                            "literature": {"range": lit["range"], "source": lit["source"], "verdict": lit["verdict"]} if lit else None})
        nxt = [r for r in table if r["event"] == mod]
        subj = {}
        for k in ("energy", "pain", "calm"):
            d = [s["subjective"]["post"][k] - s["subjective"]["pre"][k] for s in ss
                 if k in (s["subjective"].get("post") or {}) and k in (s["subjective"].get("pre") or {})]
            if d:
                subj[k] = round(sum(d) / len(d), 1)
        n = len(ss)
        for r in nxt:
            r["nominal"] = r["p"] < 0.01 and abs(r["d"]) >= 0.3 and (r["ci95"][0] > 0 or r["ci95"][1] < 0)
            r["replicated"] = _split_half(pid, mod, r["metric"], r["effect"]) if (r["significant"] or r["nominal"]) else None
        helpful = [r for r in nxt if r["significant"] and r["helpful"] and r["replicated"]]
        harmful = [r for r in nxt if r["significant"] and r["helpful"] is False and r["replicated"]]
        promising = [r for r in nxt if r["nominal"] and not r["significant"] and r["replicated"] and r["helpful"]]
        unreplicated = [r for r in nxt if (r["significant"] or r["nominal"]) and not r["replicated"]]
        adverse = [s["adverse"] for s in ss if s["adverse"]]
        if pid != 1 and n >= 5:
            verdict, why = "in_session_only", (f"{n} sessions. No wearable is connected, so Telomy can show what happens inside each session "
                                                f"but not whether it carries into the next night.")
        elif n < 5:
            verdict, why = "too_early", f"{n} session{'s' if n != 1 else ''} so far — Telomy needs at least 5 with wearable nights to judge."
        elif harmful:
            verdict, why = "possible_negative", "; ".join(f"{r['label']} {r['effect']:+} {r['unit']} the next night" for r in harmful)
        elif helpful:
            verdict, why = "helped", "; ".join(f"{r['label']} {r['effect']:+} {r['unit']} the next night (95% CI {r['ci95'][0]} to {r['ci95'][1]})" for r in helpful)
        elif promising:
            verdict, why = "promising", "; ".join(f"{r['label']} {r['effect']:+} {r['unit']} the next night (95% CI {r['ci95'][0]} to {r['ci95'][1]}, {r['p_text']})"
                                                  for r in promising) + f" — consistent across your sessions but not yet past the false-discovery check across {promising[0]['tests']} tests."
        else:
            verdict, why = "no_signal", f"After {n} sessions, nothing moved reliably the next day (all {len(nxt)} outcomes checked)." + (
                f" {unreplicated[0]['label']} looked different ({unreplicated[0]['effect']:+} {unreplicated[0]['unit']}) but the pattern did not "
                f"hold in both halves of your sessions, so Telomy treats it as chance." if unreplicated else "")
        rec = _recommend(mod, verdict, ss, metrics, n)
        out.append({"modality": mod, "name": m["name"], "category": m["category"], "evidence": m["evidence"], "sessions": n,
                    "last": ss[-1]["ts"], "spend": n * m["price"], "verdict": verdict, "why": why, "metrics": metrics,
                    "next_day": [{k: r.get(k) for k in ("metric", "label", "unit", "effect", "ci95", "p_text", "significant", "nominal", "helpful", "n", "replicated")} for r in nxt],
                    "subjective": subj, "adverse": adverse, "recommendation": rec,
                    "dose_response": dose_response(pid, mod)})
    order = {"helped": 0, "promising": 1, "possible_negative": 2, "no_signal": 3, "in_session_only": 4, "too_early": 5}
    return sorted(out, key=lambda x: (order[x["verdict"]], -x["sessions"]))


def _split_half(pid: int, mod: str, metric: str, effect: float) -> bool:
    """Replication check: the next-day difference must point the same way in the first and second half of the sessions."""
    days = sorted({s["ts"][:10] for s in _sessions(pid, mod)})
    ser = dict(engine.series(metric))
    if len(days) < 6 or not ser:
        return False
    mid = days[len(days) // 2]
    ok = []
    for part in (days[: len(days) // 2], days[len(days) // 2:]):
        lo, hi = part[0], part[-1]
        nxt = {(date.fromisoformat(d) + timedelta(days=1)).isoformat() for d in part}
        a = [ser[d] for d in nxt if d in ser]
        b = [v for d, v in ser.items() if lo <= d <= hi and d not in nxt]
        if not a or not b:
            return False
        ok.append((sum(a) / len(a) - sum(b) / len(b)) * effect > 0)
    return all(ok)


def _recommend(mod, verdict, ss, metrics, n) -> str:
    m = MODALITIES[mod]
    if verdict == "helped":
        return f"Keep it. It is measurably working for you; {m['name'].lower()} stays in your plan."
    if verdict == "promising":
        return f"Keep going — about {max(5, n // 2)} more sessions should confirm or rule it out. Same time of day and settings, ring on."
    if verdict == "possible_negative":
        return "Pause it and talk to your clinician — your data moved the wrong way after these sessions."
    if verdict == "in_session_only":
        return "Connect a ring or watch so the next-night effect can be measured."
    if verdict == "too_early":
        return f"Do {5 - n} more session{'s' if 5 - n != 1 else ''} with your ring on, then Telomy will give a verdict."
    reb = next((x for x in metrics if x["key"] in ("rebound_pct", "rmssd_stable_pct")), None)
    spend = n * m["price"]
    if m["evidence"] in ("C", "D"):
        return (f"No reliable signal after {n} sessions (₹{spend:,} so far) and the evidence base is grade {m['evidence']}. "
                f"Consider stopping, or run it as a structured N-of-1 study so the answer is clear.")
    return (f"Your body does respond in-session" + (f" (HRV {reb['mean']:+.0f}%)" if reb else "") +
            ", but it isn't carrying into the next day yet. Try a different time of day or dose before deciding.")


def dose_response(pid: int, mod: str) -> dict | None:
    """Does the setting matter for you? (cryo temperature → rebound; sauna minutes → HR after; PBM dose → perfusion)"""
    key = {"cryo": ("chamber_c", "rebound_pct", "HRV rebound", "%"), "sauna": ("temp_c", "hr_post_delta", "Heart rate after", "bpm"),
           "redlight": ("irradiance_mw_cm2", "perf_change_pct", "Perfusion change", "%"),
           "cold": ("water_c", "hr_peak_delta", "Cold-shock HR spike", "bpm"), "pemf": ("intensity_gauss", "rebound_pct", "HRV after", "%")}.get(mod)
    if not key:
        return None
    groups: dict = {}
    for s in _sessions(pid, mod):
        v = s["features"].get(key[1])
        if v is not None and key[0] in s["params"]:
            groups.setdefault(s["params"][key[0]], []).append(v)
    if len(groups) < 2:
        return None
    rows = [{"setting": k, "n": len(v), "mean": round(sum(v) / len(v), 1)} for k, v in sorted(groups.items())]
    best = max(rows, key=lambda r: r["mean"] if key[1] not in ("hr_peak_delta", "hr_post_delta") else -r["mean"]) if rows else None
    unit = {"chamber_c": "°C", "temp_c": "°C", "irradiance_mw_cm2": "mW/cm²", "water_c": "°C", "intensity_gauss": "G"}[key[0]]
    return {"param": key[0], "unit": unit, "outcome": key[2], "outcome_unit": key[3], "rows": rows,
            "best": best, "note": f"Best {key[2].lower()} at {best['setting']} {unit} (n={best['n']}). Small groups — treat as a hint."}


def session(sid: int) -> dict | None:
    r = db.one("SELECT * FROM therapy_sessions WHERE id = ?", (sid,))
    if not r:
        return None
    for k in ("params", "features", "subjective", "trace"):
        r[k] = db.unj(r[k], {})
    m = MODALITIES[r["modality"]]
    r["name"], r["inside"], r["refs"], r["evidence"] = m["name"], m["inside"], m["refs"], m["evidence"]
    r["labels"] = physio.LABELS
    dev = db.one("SELECT * FROM devices WHERE id = ?", (r["device_id"],)) if r["device_id"] else None
    r["device"] = dev
    from . import devices
    r["machine"] = devices.for_session(r)
    if r["machine"] and r["source"].startswith("simulated"):
        # the machine told us what it actually did → drive the person's physiology prior with measured inputs
        mp = devices.measured_params(r, r["machine"])
        if mp != r["params"]:
            th = _theta_for(r["patient_id"])
            tr = physio.simulate(r["modality"], mp, th, seed=sid, step=5)
            r["trace"], r["features"] = tr, physio.analyse(r["modality"], tr, mp, th["age"])
            r["source"] = r["trace"]["source"] = "simulated (ODE prior driven by machine telemetry)"
            r["measured_params"] = mp
    return r


def therapy_home(pid: int = 1) -> dict:
    resp = response(pid)
    upcoming = db.rows("""SELECT b.*, s.name AS service FROM bookings b JOIN services s ON s.id = b.service_id
                          WHERE patient_id = ? AND ts >= ? ORDER BY ts LIMIT 6""", (pid, engine.now_iso()[:10]))
    plan = db.one("SELECT * FROM therapy_plans WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (pid,))
    if plan:
        plan["plan"] = db.unj(plan["plan"], {})
    pr = db.one("SELECT * FROM patients WHERE id = ?", (pid,))
    month = engine.now_iso()[:7]
    used = db.one("SELECT COUNT(*) AS n FROM therapy_sessions WHERE patient_id = ? AND substr(ts,1,7) = ?", (pid, month))["n"]
    return {"centre": CENTRE, "membership": {"plan": pr["plan"] if pr else None, "since": pr["joined"] if pr else None,
                                             "sessions_this_month": used, "credits": 20},
            "working": resp, "upcoming": upcoming, "plan": plan, "hsai": hsai(pid) if pid == 1 else None,
            "recent": [{k: s[k] for k in ("id", "modality", "ts", "minutes")} | {"name": MODALITIES[s["modality"]]["name"],
                        "safety": s["features"].get("safety", {}).get("label")} for s in _sessions(pid)[-8:][::-1]]}


def catalogue(pid: int = 1) -> list[dict]:
    scr = {s["modality"]: s for s in screen(pid)}
    resp = {r["modality"]: r for r in response(pid)}
    out = []
    for mid, m in MODALITIES.items():
        out.append({"id": mid, "name": m["name"], "category": m["category"], "evidence": m["evidence"], "minutes": m["minutes"],
                    "price": m["price"], "goals": [GOALS[g] for g in m["goals"]], "mechanism": m["mechanism"], "inside": m["inside"],
                    "refs": m["refs"], "params": m["params"], "schema": m["schema"], "safety": scr[mid],
                    "my_verdict": resp.get(mid, {}).get("verdict"), "devices": db.rows("SELECT id, name, status FROM devices WHERE modality = ?", (mid,))})
    return out


# ----------------------------------------------------------------------------- protocol builder

RULES = [
    ("cold", "strength", "Not within 4 h after strength training — cold water blunts muscle and strength gains (Roberts 2015)."),
    ("sauna", "evening", "Evening sessions (≥ 2 h before bed) — post-sauna cooling helps sleep onset."),
    ("contrast", "order", "Finish on cold only on recovery days; finish on heat before bed."),
    ("hbot", "block", "HBOT works as a block (10–20 sessions over 2–4 weeks) — then re-measure."),
    ("cryo", "spacing", "At least a day between cryo sessions — the response habituates ~20% per consecutive day (Louis 2020)."),
]


def build_plan(pid: int, goal: str, per_week: int = 4, budget: int | None = None) -> dict:
    if goal not in GOALS:
        raise ValueError("Unknown goal")
    scr = {s["modality"]: s for s in screen(pid)}
    resp = {r["modality"]: r for r in response(pid)}
    cands = []
    for mid, m in MODALITIES.items():
        gw = m["goals"].get(goal)
        if not gw or mid in ("halo", "h2_water") or scr[mid]["status"] == "not_suitable":
            continue
        v = resp.get(mid, {}).get("verdict")
        score = gw * GRADE_W[m["evidence"]] + {"helped": 6, "promising": 3.5, "no_signal": -3, "possible_negative": -10, "too_early": 0.5}.get(v, 0)
        cands.append((score, mid, v))
    cands.sort(reverse=True)
    week = {d: [] for d in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")}
    items, used = [], 0
    days = list(week)
    for score, mid, v in cands:
        if used >= per_week:
            break
        m = MODALITIES[mid]
        freq = min(per_week - used, 3 if v == "helped" or m["evidence"] in ("A", "B") else 2)
        if freq <= 0:
            continue
        params = dict(m["params"])
        dr = resp.get(mid, {}).get("dose_response")
        if dr and dr.get("best"):
            params[dr["param"]] = dr["best"]["setting"]
        hour = 19 if mid in ("sauna", "pemf", "vibroacoustic", "float") and goal == "sleep" else 8 if mid in ("cold", "cryo") else 17
        slots = [d for d in (("Tue", "Thu", "Sat") if mid in ("cold", "cryo") else ("Mon", "Wed", "Fri", "Sun")) if len(week[d]) < 2][:freq]
        for d in slots:
            week[d].append({"modality": mid, "hour": hour})
        reason = (f"Measurably helped you: {resp[mid]['why']}" if v == "helped" else
                  f"Promising in your data: {resp[mid]['why'].split(' — ')[0]}" if v == "promising" else
                  f"Evidence grade {m['evidence']} for {GOALS[goal].lower()}; Telomy will measure your own response" +
                  (" — no signal yet in your data, so it is on probation" if v == "no_signal" else ""))
        items.append({"modality": mid, "name": m["name"], "per_week": len(slots), "params": params, "hour": hour,
                      "evidence": m["evidence"], "price": m["price"], "reason": reason, "safety": scr[mid],
                      "rules": [r[2] for r in RULES if r[0] == mid]})
        used += len(slots)
    monthly = sum(i["price"] * i["per_week"] * 4 for i in items)
    if budget and monthly > budget:
        while items and monthly > budget:
            items.pop()
            monthly = sum(i["price"] * i["per_week"] * 4 for i in items)
    pairing = {"sleep": "Telomy Formulas Wind-Down (Mg glycinate 200 mg + L-theanine 200 mg + glycine 3 g)",
               "stress": "Telomy Formulas Calm (L-theanine + KSM-66 ashwagandha + saffron)",
               "recovery": "Telomy Formulas Recover (creatine + tart cherry + omega-3 + curcumin)"}.get(goal)
    return {"goal": goal, "goal_label": GOALS[goal], "per_week": per_week, "items": items, "week": week, "monthly_price": monthly,
            "checkpoints": ["Week 2: in-session fingerprint review (rebound, rewarming, k)",
                            "Week 4: next-night effects on HRV and deep sleep — keep, adjust or drop each item",
                            "Week 12: labs and HSAI re-check"],
            "formula_pairing": pairing, "excluded": [{"modality": s["modality"], "name": s["name"], "why": s["summary"]}
                                                     for s in scr.values() if s["status"] == "not_suitable" and goal in MODALITIES[s["modality"]]["goals"]],
            "note": "Drafted by Sinc; your clinician reviews and signs before any session is booked."}


def save_plan(pid: int, goal: str, per_week: int = 4) -> dict:
    plan = build_plan(pid, goal, per_week)
    pid_ = db.exec_("INSERT INTO therapy_plans (patient_id, goal, created_at, state, plan) VALUES (?,?,?,?,?)",
                    (pid, goal, engine.now_iso(), "awaiting_doctor", db.j(plan)))
    return get_plan(pid_)


def get_plan(plan_id: int) -> dict | None:
    r = db.one("SELECT * FROM therapy_plans WHERE id = ?", (plan_id,))
    if r:
        r["plan"] = db.unj(r["plan"], {})
    return r


def plans(state: str | None = None) -> list[dict]:
    rs = db.rows("SELECT * FROM therapy_plans" + (" WHERE state = ?" if state else "") + " ORDER BY id DESC", (state,) if state else ())
    for r in rs:
        r["plan"] = db.unj(r["plan"], {})
        p = db.one("SELECT name FROM patients WHERE id = ?", (r["patient_id"],))
        r["patient"] = p["name"] if p else None
    return rs


def decide_plan(plan_id: int, approve: bool, note: str, doctor: str = "Dr. Meera Rao") -> dict:
    if not note.strip():
        raise ValueError("A note is required.")
    r = get_plan(plan_id)
    if not r:
        raise LookupError("Plan not found")
    if r["state"] != "awaiting_doctor":
        raise ValueError(f"Plan is already {r['state']}.")
    booked = 0
    if approve:
        start = date.fromisoformat(engine.now_iso()[:10]) + timedelta(days=1)
        idx = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
        for wk in range(4):
            for dname, slots in r["plan"]["week"].items():
                d = start + timedelta(days=(idx[dname] - start.weekday()) % 7 + 7 * wk)
                for s in slots:
                    db.exec_("INSERT INTO bookings (patient_id, service_id, ts, status, price) VALUES (?,?,?,?,?)",
                             (r["patient_id"], s["modality"], f"{d.isoformat()}T{s['hour']:02d}:00:00", "booked", MODALITIES[s["modality"]]["price"]))
                    booked += 1
        db.exec_("UPDATE therapy_plans SET state = 'superseded' WHERE patient_id = ? AND state = 'active'", (r["patient_id"],))
    db.exec_("UPDATE therapy_plans SET state = ?, doctor = ?, note = ?, decided_at = ? WHERE id = ?",
             ("active" if approve else "rejected", doctor, note.strip(), engine.now_iso(), plan_id))
    out = get_plan(plan_id)
    out["booked"] = booked
    return out


# ----------------------------------------------------------------------------- live session (declared context) + device ingest

def start_session(pid: int, modality: str, params: dict | None = None) -> dict:
    if modality not in MODALITIES:
        raise ValueError("Unknown therapy")
    scr = screen(pid, modality)[0]
    if scr["status"] == "not_suitable":
        raise PermissionError(scr["summary"])
    p = dict(MODALITIES[modality]["params"], **(params or {}))
    th = _theta_for(pid)
    expected = physio.simulate(modality, p, th, seed=11, step=10)
    sid = db.exec_("""INSERT INTO therapy_sessions (patient_id, modality, ts, minutes, params, features, trace, subjective, status, source)
                      VALUES (?,?,?,?,?,?,?,?,?,?)""",
                   (pid, modality, engine.now_iso(), p.get("minutes", MODALITIES[modality]["minutes"]), db.j(p), "{}", db.j(expected),
                    "{}", "in_progress", "simulated (ODE prior)"))
    return {"id": sid, "expected": expected, "safety": scr, "message": "Context declared: Telomy loaded your expected response curve."}


def ingest(sid: int, samples: list[dict], source: str = "device") -> dict:
    """Real samples [{t, hr, rmssd, spo2, skin, ...}] (1–5 s) + optional phase marks replace the prior and are re-analysed."""
    r = session(sid)
    if not r:
        raise LookupError("Session not found")
    if len(samples) < 20:
        raise ValueError("Need at least 20 samples")
    for s_ in samples:  # Telomy patch / chest strap may send raw RR intervals; HRV is computed server-side
        rr = s_.get("rr_ms")
        if isinstance(rr, list) and len(rr) >= 3 and "rmssd" not in s_:
            d = [b - a for a, b in zip(rr, rr[1:])]
            s_["rmssd"] = round((sum(x * x for x in d) / len(d)) ** 0.5, 1)
            s_.setdefault("hr", round(60000 / (sum(rr) / len(rr)), 1))
    ts = [int(s["t"]) for s in samples]
    sig = {k: [s.get(k) for s in samples] for k in physio.SIGNALS if any(k in s for s in samples)}
    phases = r["trace"].get("phases") if r["trace"] else None
    if not phases or phases[-1]["end"] < ts[-1]:
        phases = [{"phase": "baseline", "start": 0, "end": 300}, {"phase": "active", "start": 300, "end": ts[-1] - 900},
                  {"phase": "recovery", "start": ts[-1] - 900, "end": ts[-1] + 1}]
    trace = {"t": ts, "signals": sig, "phases": phases, "step": ts[1] - ts[0], "source": source, "sqi": 0.9}
    age = engine.age_on() or 40 if r["patient_id"] == 1 else 45
    f = physio.analyse(r["modality"], trace, r["params"], age)
    db.exec_("UPDATE therapy_sessions SET trace = ?, features = ?, source = ? WHERE id = ?", (db.j(trace), db.j(f), source, sid))
    return {"id": sid, "features": f}


def finish_session(sid: int, subjective: dict | None = None, adverse: str | None = None) -> dict:
    r = session(sid)
    if not r:
        raise LookupError("Session not found")
    f = r["features"] or physio.analyse(r["modality"], r["trace"], r["params"], engine.age_on() or 40)
    db.exec_("UPDATE therapy_sessions SET features = ?, subjective = ?, adverse = ?, status = 'completed' WHERE id = ?",
             (db.j(f), db.j(subjective or {}), adverse, sid))
    db.exec_("INSERT INTO events (ts, kind, label, severity, data) VALUES (?,?,?,?,?)",
             (r["ts"], r["modality"], f"{MODALITIES[r['modality']]['name']} (Telomy session)", None, db.j({"session_id": sid})))
    return session(sid)


def live_floor() -> dict:
    """Who is in which machine right now, with in-session vitals (the centre's therapy floor)."""
    now = datetime.fromisoformat(engine.now_iso())
    rows = db.rows(f"""SELECT b.*, p.name, p.age FROM bookings b JOIN patients p ON p.id = b.patient_id
                       WHERE substr(b.ts,1,10) = ? AND b.service_id IN ({','.join('?' * len(MODALITIES))}) AND b.status != 'no_show' ORDER BY b.ts""",
                   (now.date().isoformat(), *MODALITIES))
    live, next_up = [], []
    for b in rows:
        m = MODALITIES[b["service_id"]]
        start = datetime.fromisoformat(b["ts"])
        p = dict(m["params"])
        total = sum(d for _, d in physio._phases(b["service_id"], p))
        el = (now - start).total_seconds() + 300  # baseline begins 5 min before the booked slot
        if 0 <= el < total:
            tr = physio.simulate(b["service_id"], p, _theta_for(b["patient_id"]), seed=b["id"], step=10, dt=5)
            k = int(el // 10)
            cur = {s: tr["signals"][s][min(k, len(tr["signals"][s]) - 1)] for s in physio.SIGNALS}
            phase = next((ph["phase"] for ph in tr["phases"] if ph["start"] <= el < ph["end"]), "recovery")
            part = {"t": tr["t"][:k + 1], "signals": {s: v[:k + 1] for s, v in tr["signals"].items()}, "phases": tr["phases"], "step": 10}
            alert = physio.safety(b["service_id"], part, {}, b["age"] or 40)
            dev = db.one("SELECT id, name FROM devices WHERE modality = ? ORDER BY id LIMIT 1", (b["service_id"],))
            live.append({"booking_id": b["id"], "patient_id": b["patient_id"], "name": b["name"], "modality": b["service_id"], "therapy": m["name"],
                         "device": dev, "phase": phase, "elapsed_s": int(el), "total_s": total, "now": cur, "params": p,
                         "spark": {s: tr["signals"][s][max(0, k - 30):k + 1] for s in ("hr", "rmssd", "skin", "spo2")}, "safety": alert,
                         "source": "simulated (ODE prior) — pair a chest strap or patch for live data"})
        elif el < 0 and len(next_up) < 8:
            next_up.append({"booking_id": b["id"], "name": b["name"], "therapy": m["name"], "ts": b["ts"]})
    devs = db.rows("SELECT * FROM devices ORDER BY room, id")
    busy = {x["modality"] for x in live}
    for d in devs:
        d["in_use"] = d["modality"] in busy and d["status"] == "available"
    return {"now": now.isoformat(timespec="minutes"), "live": live, "next": next_up, "devices": devs,
            "alerts": [x for x in live if x["safety"]["tier"] >= 1]}


# ----------------------------------------------------------------------------- centre analytics + research

def modality_outcomes() -> list[dict]:
    out = []
    for mid, m in MODALITIES.items():
        rs = db.rows("SELECT patient_id, features, subjective, adverse FROM therapy_sessions WHERE modality = ? AND status = 'completed'", (mid,))
        if not rs:
            continue
        F = [db.unj(r["features"], {}) for r in rs]
        S = [db.unj(r["subjective"], {}) for r in rs]
        mean = lambda k: (lambda v: round(sum(v) / len(v), 1) if v else None)([f[k] for f in F if f.get(k) is not None])  # noqa: E731
        dl = lambda k: [s["post"][k] - s["pre"][k] for s in S if k in (s.get("post") or {}) and k in (s.get("pre") or {})]  # noqa: E731
        pain, calm = dl("pain"), dl("calm")
        out.append({"modality": mid, "name": m["name"], "evidence": m["evidence"], "sessions": len(rs),
                    "members": len({r["patient_id"] for r in rs}), "hr_peak_delta": mean("hr_peak_delta"), "rebound_pct": mean("rebound_pct"),
                    "pain_change": round(sum(pain) / len(pain), 1) if pain else None, "calm_change": round(sum(calm) / len(calm), 1) if calm else None,
                    "pain_responders_pct": round(100 * sum(1 for x in pain if x <= -2) / len(pain)) if pain else None,
                    "adverse": sum(1 for r in rs if r["adverse"]), "safety_flags": sum(1 for f in F if (f.get("safety") or {}).get("tier", 0) >= 2)})
    return sorted(out, key=lambda x: -x["sessions"])


def phenotypes() -> dict:
    """Therapy Response Phenotype study (Echo OS research thesis 1): cluster members by their cryo fingerprint
    (rebound, rewarming half-time, k) and test whether phenotype tracks metabolic and vascular markers."""
    import numpy as np
    rows = db.rows("SELECT patient_id, features FROM therapy_sessions WHERE modality IN ('cryo','cold') AND status = 'completed'")
    per: dict[int, list] = {}
    for r in rows:
        f = db.unj(r["features"], {})
        if f.get("rebound_pct") is not None and f.get("rewarm_half_min") is not None and f.get("k_recovery") is not None:
            per.setdefault(r["patient_id"], []).append((f["rebound_pct"], f["rewarm_half_min"], f["k_recovery"]))
    ids = [p for p, v in per.items() if len(v) >= 2]
    if len(ids) < 8:
        return {"n": len(ids), "message": "Need at least 8 members with 2+ cold sessions."}
    X = np.array([np.mean(per[p], axis=0) for p in ids])
    Z = (X - X.mean(0)) / (X.std(0) + 1e-9)
    rng = np.random.default_rng(3)
    C = Z[rng.choice(len(Z), 3, replace=False)]
    for _ in range(50):  # k-means, k = 3
        lab = np.argmin(((Z[:, None, :] - C[None]) ** 2).sum(-1), axis=1)
        C = np.array([Z[lab == k].mean(0) if (lab == k).any() else C[k] for k in range(3)])
    names = {}
    for k in range(3):
        c = X[lab == k].mean(0) if (lab == k).any() else X.mean(0)
        names[k] = ("Fast rebounder" if c[0] >= np.percentile(X[:, 0], 60) and c[1] <= np.median(X[:, 1]) else
                    "Slow rewarmer" if c[1] >= np.percentile(X[:, 1], 60) else "Blunted responder" if c[0] <= np.percentile(X[:, 0], 40) else "Typical")
    snap = {p: (db.unj(db.one("SELECT data FROM patients WHERE id = ?", (p,))["data"], {}) if p != 1 else
                {"hba1c": (engine.latest_values().get("hba1c") or {}).get("value_num"), "hrv": (engine.signal_baseline("hrv", days=60) or {}).get("mean"),
                 "bmi": 25.5}) for p in ids}
    groups = []
    for k in range(3):
        mem = [ids[i] for i in range(len(ids)) if lab[i] == k]
        if not mem:
            continue
        g = lambda key: round(float(np.mean([snap[p].get(key) for p in mem if snap[p].get(key) is not None])), 1)  # noqa: E731
        groups.append({"phenotype": names[k], "members": len(mem), "rebound_pct": round(float(X[lab == k, 0].mean()), 1),
                       "rewarm_half_min": round(float(X[lab == k, 1].mean()), 1), "k": round(float(X[lab == k, 2].mean()), 3),
                       "hba1c": g("hba1c"), "bmi": g("bmi"), "hrv_night": g("hrv"), "includes_you": 1 in mem})
    hb = [(X[i, 1], snap[p].get("hba1c")) for i, p in enumerate(ids) if snap[p].get("hba1c") is not None]
    r_val, p_val = engine.pearson([a for a, _ in hb], [b for _, b in hb])
    return {"n": len(ids), "groups": sorted(groups, key=lambda g: -g["rebound_pct"]),
            "finding": {"x": "Rewarming half-time after cold", "y": "HbA1c", "r": round(r_val, 2), "p": engine.fmt_p(p_val), "n": len(hb)},
            "caveat": "Simulated cohort (ODE prior with each member's own θ). With patch data from real sessions this becomes the "
                      "Therapy Response Phenotype study — IRB protocol and research consent required."}


# ----------------------------------------------------------------------------- HSAI (Health-Span Adaptability Index)

HSAI_ZONES = [(85, "Peak adaptability"), (70, "High resilience"), (55, "Normal adaptive"), (40, "Compensating"), (25, "Instability emerging"),
              (0, "Critical threshold")]


def _sig(x):
    return 1 / (1 + math.exp(-x))


def hsai(pid: int = 1) -> dict:
    """HSAI = Σ w_i · D_i over autonomic, recovery, cognitive load, oxygen, thermoregulation, voice, metabolic (Echo OS spec v2).
    Domains without data are excluded and the rest re-weighted; σ from the trailing 30-day variance; never a diagnosis."""
    day = engine.last_signal_day()
    if not day:
        return {"available": False}
    end = date.fromisoformat(day)
    s = lambda m, a, b: [v for _, v in engine.series(m, (end - timedelta(days=a)).isoformat(), (end - timedelta(days=b)).isoformat())]  # noqa: E731
    hrv30, hrv_prev = s("hrv", 29, 0), s("hrv", 59, 30)
    if len(hrv30) < 7:
        return {"available": False, "message": "Keep wearing your ring for 7 days before HSAI is shown."}
    mean = lambda v: sum(v) / len(v) if v else None  # noqa: E731
    sd = lambda v: (sum((x - mean(v)) ** 2 for x in v) / max(1, len(v) - 1)) ** 0.5 if len(v) > 1 else 0  # noqa: E731
    sess = _sessions(pid)
    cold = [x["features"] for x in sess if x["modality"] in ("cryo", "cold")][-6:]
    dom = {}
    # Autonomic stability (25 %): RMSSD slope vs previous month + post-stress rebound efficiency
    slope_z = (mean(hrv30) - mean(hrv_prev)) / (sd(hrv_prev) or 5) if hrv_prev else 0
    reb = mean([f["rebound_pct"] for f in cold if f.get("rebound_pct") is not None])
    reb_z = ((reb - 75) / 25) if reb is not None else 0
    dom["auto"] = (0.25, 100 * _sig(1.5 * slope_z + 0.7 * reb_z + 0.3), sd(hrv30) / (mean(hrv30) or 1) * 40,
                   f"30-day HRV {mean(hrv30):.0f} ms vs {mean(hrv_prev):.0f} before" + (f"; post-cold rebound {reb:.0f}% (expected 50–100%)" if reb else ""))
    # Recovery kinetics (20 %): k vs cohort p75
    ks = [f["k_recovery"] for f in cold if f.get("k_recovery")]
    allk = sorted(db.unj(r["features"], {}).get("k_recovery") or 0 for r in db.rows("SELECT features FROM therapy_sessions WHERE modality IN ('cryo','cold')"))
    allk = [k for k in allk if k]
    if ks and allk:
        p75 = allk[int(0.75 * (len(allk) - 1))]
        dom["rec"] = (0.20, 100 * min(1.0, mean(ks) / p75), 100 * sd(ks) / (p75 or 1) / 2, f"Recovery constant k {mean(ks):.3f}/min vs cohort 75th percentile {p75:.3f}")
    # Cognitive load (15 %): resting HRV vs baseline × (1 − sleep debt); voice not measured
    sl7, hrv7 = s("sleep_hours", 6, 0), s("hrv", 6, 0)
    debt = max(0.0, 7.5 - (mean(sl7) or 7.5)) / 2
    dom["cog"] = (0.15, 100 * min(1.0, (mean(hrv7) / (mean(hrv_prev) or mean(hrv30)))) * (1 - min(0.6, debt)), 8,
                  f"7-day HRV {mean(hrv7):.0f} ms; sleep {mean(sl7):.1f} h (debt {debt * 2:.1f} h)")
    # Oxygen utilisation (13 %)
    sp = s("spo2", 29, 0)
    if sp:
        dom["oxy"] = (0.13, 100 * _sig(2 * (mean(sp) - 95) - 1.0), sd(sp) * 10, f"Night SpO₂ {mean(sp):.1f}%")
    # Thermoregulation (12 %)
    rw = [f["rewarm_half_min"] for f in cold if f.get("rewarm_half_min")]
    st = s("skin_temp", 29, 0)
    if rw:
        pen = min(0.4, max(0.0, (sd(st) - 0.4) / 1.0)) if st else 0
        dom["therm"] = (0.12, 100 * math.exp(-0.08 * max(0.0, mean(rw) - 10)) * (1 - pen), 6, f"Rewarming half-time {mean(rw):.1f} min after cold (healthy ≈ 9–11)")
    # Metabolic proxy (5 % → 15 % with CGM)
    L = engine.latest_values()
    tir = (L.get("cgm_tir") or {}).get("value_num")
    if tir is not None:
        dom["meta"] = (0.15, max(0.0, min(100.0, (tir - 50) / 45 * 100)), 6, f"CGM time in tight range {tir:.0f}%")
    wsum = sum(w for w, *_ in dom.values())
    score = sum(w * d for w, d, *_ in dom.values()) / wsum
    sigma = (sum((w / wsum) ** 2 * (u ** 2) for w, _, u, _ in dom.values())) ** 0.5
    zone = next(z for lo, z in HSAI_ZONES if score >= lo)
    names = {"auto": "Autonomic stability", "rec": "Recovery kinetics", "cog": "Cognitive load", "oxy": "Oxygen utilisation",
             "therm": "Thermoregulation", "meta": "Metabolic proxy"}
    low = min(dom, key=lambda k: dom[k][1])
    return {"available": True, "score": round(score), "range": [round(score - 2 * sigma), round(score + 2 * sigma)], "zone": zone,
            "domains": [{"key": k, "name": names[k], "weight": round(w / wsum, 2), "score": round(d), "basis": basis}
                        for k, (w, d, _, basis) in dom.items()],
            "not_measured": ["Voice biomarkers (needs the Telomy Band microphone and explicit consent)"],
            "weakest": names[low],
            "message": f"Your physiological adaptability is in the '{zone.lower()}' zone; {names[low].lower()} is the domain with most room. "
                       f"This is a wellness index, not a diagnosis.",
            "method": "HSAI v1 (Echo OS spec): weights auto .25 · rec .20 · cog .15 · oxy .13 · therm .12 · voice .10 · meta .05→.15 with CGM; "
                      "missing domains re-weighted; ±2σ shown."}
