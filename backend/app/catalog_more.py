"""Second wave of report types: thyroid & hormones, iron/vitamins/minerals, cardiac & vascular function, lung function,
continuous glucose (CGM), immunity/autoimmunity/allergy, urine and functional-medicine tests, plus FibroScan.

Zones follow guideline categories where they exist: ADA/International Consensus on Time in Range (Battelino 2019),
ESC/ESH 2023 hypertension (ABPM daytime ≥135/85), AHA 2016 ABI (≤0.90 PAD), ESC 2018 cf-PWV (>10 m/s organ damage),
GOLD 2024 spirometry (FEV1/FVC <0.70), EASL 2021 / Baveno VII FibroScan (LSM <8 kPa rules out advanced fibrosis),
ATA thyroid antibodies, WHO G6PD classes. Functional-medicine tests are graded C/D and labelled as such in the UI.
"""

MORE_PANELS = {
    "hormones": "Thyroid & hormones",
    "micronutrients": "Iron, vitamins & minerals",
    "cardio": "Heart & vascular function (ECG, echo, ABI, PWV, ABPM)",
    "lung": "Lung function (spirometry)",
    "cgm": "Continuous glucose monitoring (CGM)",
    "immune": "Immunity, autoimmunity & allergy",
    "urine": "Urine routine",
    "functional": "Functional medicine (cortisol rhythm, organic acids)",
}

# id: (name, panel, unit, optimal_low, optimal_high, better, aliases, loinc)
MORE_MARKERS = {
    # thyroid & hormones
    "ft4": ("Free T4", "hormones", "ng/dL", 1.0, 1.6, "mid", ["free t4", "ft4"], "3024-7"),
    "rt3": ("Reverse T3", "hormones", "ng/dL", 10, 24, "low", ["reverse t3"], "3052-8"),
    "tpo_ab": ("Anti-TPO antibodies", "hormones", "IU/mL", 0, 34, "low", ["anti-tpo antibodies", "anti-tpo"], "8099-4"),
    "tg_ab": ("Anti-thyroglobulin antibodies", "hormones", "IU/mL", 0, 115, "low", ["anti-thyroglobulin antibodies", "anti-thyroglobulin"], "8098-6"),
    "lh": ("LH", "hormones", "mIU/mL", 1.7, 8.6, "mid", ["lh (luteinising hormone)", "luteinising hormone"], "10501-5"),
    "fsh": ("FSH", "hormones", "mIU/mL", 1.5, 12.4, "mid", ["fsh (follicle-stimulating hormone)", "follicle-stimulating hormone"], "15067-2"),
    "estradiol": ("Estradiol", "hormones", "pg/mL", 20, 40, "mid", ["estradiol", "oestradiol"], "2243-4"),
    "prolactin": ("Prolactin", "hormones", "ng/mL", 4, 15, "mid", ["prolactin"], "2842-3"),
    "progesterone": ("Progesterone", "hormones", "ng/mL", 0.2, 1.4, "mid", ["progesterone"], "2839-9"),
    "amh": ("Anti-Müllerian hormone (AMH)", "hormones", "ng/mL", 1.0, 4.0, "mid", ["anti-müllerian hormone", "anti-mullerian hormone", "amh"], "38476-3"),
    "psa": ("PSA (total)", "hormones", "ng/mL", 0, 1.5, "low", ["psa (total)", "prostate-specific antigen"], "2857-1"),
    # iron, vitamins, minerals, electrolytes
    "iron": ("Serum iron", "micronutrients", "µg/dL", 60, 170, "mid", ["serum iron"], "2498-4"),
    "tibc": ("Total iron-binding capacity", "micronutrients", "µg/dL", 250, 400, "mid", ["total iron-binding capacity", "tibc"], "2500-7"),
    "tsat": ("Transferrin saturation", "micronutrients", "%", 25, 45, "mid", ["transferrin saturation"], "2502-3"),
    "folate": ("Folate (serum)", "micronutrients", "ng/mL", 10, 25, "high", ["folate (serum)", "folate", "folic acid"], "2284-8"),
    "rbc_mg": ("RBC magnesium", "micronutrients", "mg/dL", 5.0, 6.5, "high", ["rbc magnesium"], "6834-6"),
    "zinc": ("Zinc", "micronutrients", "µg/dL", 80, 120, "mid", ["zinc"], "5763-8"),
    "copper": ("Copper", "micronutrients", "µg/dL", 70, 140, "mid", ["copper"], "5631-7"),
    "selenium": ("Selenium", "micronutrients", "µg/L", 110, 150, "mid", ["selenium"], "5724-1"),
    "calcium": ("Calcium (total)", "micronutrients", "mg/dL", 8.8, 10.2, "mid", ["calcium (total)", "serum calcium"], "17861-6"),
    "sodium": ("Sodium", "micronutrients", "mmol/L", 136, 144, "mid", ["sodium"], "2951-2"),
    "potassium": ("Potassium", "micronutrients", "mmol/L", 3.8, 5.0, "mid", ["potassium"], "2823-3"),
    # heart & vascular function
    "qtc": ("QTc (ECG)", "cardio", "ms", 350, 440, "mid", ["qtc (ecg)", "qtc"], "8636-3"),
    "ecg_hr": ("Resting heart rate (ECG)", "cardio", "bpm", 50, 70, "mid", ["resting heart rate (ecg)"], "8867-4"),
    "afib_burden": ("Atrial fibrillation burden (Holter)", "cardio", "%", 0, 0, "low", ["atrial fibrillation burden"], ""),
    "pvc_burden": ("PVC burden (Holter)", "cardio", "%", 0, 1, "low", ["pvc burden"], ""),
    "e_e_ratio": ("E/e′ ratio (echo)", "cardio", "", 0, 8, "low", ["e/e' ratio", "e/e′ ratio"], ""),
    "lavi": ("Left atrial volume index (echo)", "cardio", "mL/m²", 16, 34, "mid", ["left atrial volume index"], ""),
    "abi": ("Ankle-brachial index", "cardio", "ratio", 1.0, 1.3, "mid", ["ankle-brachial index"], "76497-2"),
    "pwv": ("Pulse wave velocity (carotid-femoral)", "cardio", "m/s", 0, 8, "low", ["pulse wave velocity"], ""),
    "abpm_day_sbp": ("Daytime ambulatory SBP (ABPM)", "cardio", "mmHg", 0, 130, "low", ["daytime ambulatory sbp"], ""),
    "abpm_day_dbp": ("Daytime ambulatory DBP (ABPM)", "cardio", "mmHg", 0, 80, "low", ["daytime ambulatory dbp"], ""),
    "abpm_dip": ("Nocturnal BP dip (ABPM)", "cardio", "%", 10, 20, "mid", ["nocturnal bp dip"], ""),
    # lung
    "fev1_pct": ("FEV1 (% predicted)", "lung", "%", 80, 130, "high", ["fev1 (% predicted)"], "20150-9"),
    "fvc_pct": ("FVC (% predicted)", "lung", "%", 80, 130, "high", ["fvc (% predicted)"], "19870-5"),
    "fev1_fvc": ("FEV1/FVC ratio", "lung", "ratio", 0.75, 0.95, "high", ["fev1/fvc ratio"], "19926-5"),
    "feno": ("FeNO (exhaled nitric oxide)", "lung", "ppb", 0, 25, "low", ["feno"], ""),
    # CGM (14-day)
    "cgm_mean": ("Mean glucose (CGM)", "cgm", "mg/dL", 80, 105, "low", ["mean glucose (cgm)"], "97507-8"),
    "cgm_tir": ("Time in tight range 70–140 (CGM)", "cgm", "%", 85, 100, "high", ["time in tight range 70–140", "time in tight range 70-140", "time in tight range"], ""),
    "cgm_cv": ("Glucose variability CV (CGM)", "cgm", "%", 0, 20, "low", ["glucose variability cv"], ""),
    "gmi": ("Glucose management indicator (GMI)", "cgm", "%", 0, 5.6, "low", ["glucose management indicator"], "97506-0"),
    "cgm_peak": ("Mean post-meal peak (CGM)", "cgm", "mg/dL", 0, 140, "low", ["mean post-meal peak"], ""),
    "cgm_tbr": ("Time below 70 (CGM)", "cgm", "%", 0, 1, "low", ["time below 70"], ""),
    # immune / autoimmune / allergy / special
    "esr": ("ESR", "immune", "mm/h", 0, 15, "low", ["esr (erythrocyte sedimentation rate)", "erythrocyte sedimentation rate"], "4537-7"),
    "ana": ("Antinuclear antibodies (ANA, IFA)", "immune", "", None, None, "absent", ["antinuclear antibodies"], "8061-4"),
    "ttg_iga": ("tTG-IgA (coeliac screen)", "immune", "U/mL", 0, 4, "low", ["ttg-iga"], "31017-7"),
    "total_ige": ("Total IgE", "immune", "IU/mL", 0, 100, "low", ["total ige"], "19113-0"),
    "ige_mite": ("Specific IgE: house dust mite", "immune", "kUA/L", 0, 0.35, "low", ["specific ige: house dust mite"], ""),
    "ige_pollen": ("Specific IgE: grass pollen", "immune", "kUA/L", 0, 0.35, "low", ["specific ige: grass pollen"], ""),
    "g6pd": ("G6PD activity", "immune", "U/g Hb", 7.0, 20.5, "high", ["g6pd activity", "g6pd"], "32546-4"),
    # urine routine
    "u_ph": ("Urine pH", "urine", "", 5.0, 7.0, "mid", ["urine ph"], "2756-5"),
    "u_sg": ("Urine specific gravity", "urine", "", 1.005, 1.025, "mid", ["urine specific gravity"], "2965-2"),
    "u_protein": ("Urine protein", "urine", "", None, None, "absent", ["urine protein"], "2888-6"),
    "u_glucose": ("Urine glucose", "urine", "", None, None, "absent", ["urine glucose"], "2350-7"),
    "u_blood": ("Urine blood", "urine", "", None, None, "absent", ["urine blood"], "5794-3"),
    "u_pus": ("Urine pus cells", "urine", "/hpf", 0, 5, "low", ["urine pus cells"], "5821-4"),
    # FibroScan (screening panel)
    "lsm": ("Liver stiffness (FibroScan)", "screening", "kPa", 2, 7, "low", ["liver stiffness (fibroscan)", "liver stiffness"], ""),
    "cap": ("Controlled attenuation parameter (FibroScan)", "screening", "dB/m", 0, 248, "low", ["controlled attenuation parameter"], ""),
    # functional medicine (graded C/D)
    "car": ("Cortisol awakening response", "functional", "%", 38, 75, "mid", ["cortisol awakening response"], ""),
    "cortisol_night": ("Late-night salivary cortisol", "functional", "nmol/L", 0, 4, "low", ["late-night salivary cortisol"], ""),
    "ohdg": ("8-OHdG (oxidative DNA damage)", "functional", "ng/mg creat", 0, 4.5, "low", ["8-ohdg"], ""),
    "pyroglutamate": ("Pyroglutamic acid (glutathione status)", "functional", "mmol/mol creat", 0, 40, "low", ["pyroglutamic acid"], ""),
    "kynurenate": ("Kynurenic acid", "functional", "mmol/mol creat", 0, 6, "low", ["kynurenic acid"], ""),
    "hiaa": ("5-HIAA (serotonin metabolite)", "functional", "mmol/mol creat", 3.8, 12, "mid", ["5-hiaa"], ""),
}

MORE_EVIDENCE = {
    **{m: "A" for m in ["ft4", "tpo_ab", "psa", "tsat", "iron", "tibc", "folate", "sodium", "potassium", "calcium", "qtc", "afib_burden",
                        "abi", "abpm_day_sbp", "abpm_day_dbp", "fev1_pct", "fvc_pct", "fev1_fvc", "ttg_iga", "g6pd", "esr",
                        "u_protein", "u_glucose", "u_blood", "lsm", "gmi"]},
    **{m: "B" for m in ["pwv", "abpm_dip", "e_e_ratio", "lavi", "pvc_burden", "cgm_tir", "cgm_cv", "cgm_mean", "cgm_tbr", "cap",
                        "amh", "lh", "fsh", "estradiol", "prolactin", "progesterone", "zinc", "copper", "selenium", "feno", "total_ige",
                        "ige_mite", "ige_pollen", "ana", "cortisol_night", "ecg_hr"]},
    **{m: "C" for m in ["rt3", "tg_ab", "rbc_mg", "cgm_peak", "car", "ohdg"]},
    **{m: "D" for m in ["pyroglutamate", "kynurenate", "hiaa"]},
}

MORE_ZONES = {
    "tsat": [(16, "Low (iron deficiency)", "out_of_range"), (20, "Low-normal", "in_range"), (45, "Normal", "optimal"),
             (None, "High (check for iron overload)", "out_of_range")],
    "tpo_ab": [(35, "Negative", "optimal"), (None, "Positive (autoimmune thyroid)", "out_of_range")],
    "psa": [(2.5, "Low", "optimal"), (4.0, "Borderline — repeat", "in_range"), (None, "Raised — urology review", "out_of_range")],
    "g6pd": [(4.0, "Deficient (WHO class II/III)", "out_of_range"), (7.0, "Intermediate", "in_range"), (None, "Normal", "optimal")],
    "abi": [(0.91, "Peripheral artery disease (≤0.90)", "out_of_range"), (1.0, "Borderline (0.91–0.99)", "in_range"),
            (1.41, "Normal", "optimal"), (None, "Non-compressible arteries", "out_of_range")],
    "pwv": [(8, "Normal arterial stiffness", "optimal"), (10, "Raised", "in_range"), (None, "High — organ damage (ESC/ESH)", "out_of_range")],
    "abpm_day_sbp": [(130, "Normal", "optimal"), (135, "High-normal", "in_range"), (None, "Hypertension (ABPM ≥135)", "out_of_range")],
    "abpm_dip": [(0, "Reverse dipper", "out_of_range"), (10, "Non-dipper", "out_of_range"), (20, "Dipper (normal)", "optimal"),
                 (None, "Extreme dipper", "in_range")],
    "qtc": [(350, "Short", "out_of_range"), (450, "Normal", "optimal"), (470, "Borderline", "in_range"), (None, "Prolonged", "out_of_range")],
    "fev1_fvc": [(0.70, "Obstruction (GOLD)", "out_of_range"), (0.75, "Low-normal", "in_range"), (None, "Normal", "optimal")],
    "fev1_pct": [(50, "Severe reduction", "out_of_range"), (80, "Reduced", "out_of_range"), (None, "Normal", "optimal")],
    "cgm_tir": [(70, "Below target", "out_of_range"), (85, "Good", "in_range"), (None, "Excellent (tight range)", "optimal")],
    "cgm_cv": [(20, "Stable", "optimal"), (36, "Variable", "in_range"), (None, "Unstable (CV >36%)", "out_of_range")],
    "gmi": [(5.7, "Normal", "optimal"), (6.5, "Prediabetes range", "out_of_range"), (None, "Diabetes range", "out_of_range")],
    "lsm": [(8, "No advanced fibrosis (<8 kPa)", "optimal"), (12, "Indeterminate — specialist review", "in_range"),
            (None, "Advanced fibrosis likely", "out_of_range")],
    "cap": [(248, "No steatosis (S0)", "optimal"), (268, "Mild steatosis (S1)", "out_of_range"), (280, "Moderate (S2)", "out_of_range"),
            (None, "Severe (S3)", "out_of_range")],
    "ttg_iga": [(4, "Negative", "optimal"), (10, "Weak positive", "out_of_range"), (None, "Positive — coeliac work-up", "out_of_range")],
    "ige_mite": [(0.35, "Not sensitised", "optimal"), (3.5, "Sensitised (class 1–2)", "out_of_range"), (None, "Strongly sensitised", "out_of_range")],
}

MORE_CONCERNS = {
    "Heart & arteries": ["pwv", "abi", "abpm_day_sbp", "abpm_dip", "qtc", "afib_burden", "e_e_ratio", "lavi"],
    "Blood sugar & metabolism": ["cgm_tir", "cgm_cv", "gmi", "cgm_peak", "cgm_mean", "cap"],
    "Liver": ["lsm", "cap"],
    "Hormones & thyroid": ["ft4", "rt3", "tpo_ab", "tg_ab", "lh", "fsh", "estradiol", "prolactin", "amh", "psa"],
    "Nutrients": ["iron", "tsat", "tibc", "folate", "rbc_mg", "zinc", "copper", "selenium"],
    "Inflammation & immunity": ["esr", "ana", "total_ige", "ttg_iga"],
    "Lungs & breathing": ["fev1_pct", "fvc_pct", "fev1_fvc", "feno", "ige_mite", "ige_pollen"],
    "Kidney": ["u_protein", "u_blood", "sodium", "potassium"],
    "Stress & nervous system": ["car", "cortisol_night", "cortisol", "hiaa", "kynurenate"],
    "Cancer screening": ["psa"],
}

MORE_RETEST = {"hormones": 180, "micronutrients": 120, "cardio": 365, "lung": 730, "cgm": 180, "immune": 365, "urine": 365,
               "functional": 365}

MORE_PREP = {
    "psa": "No ejaculation or cycling for 48 h, and no prostate exam beforehand.",
    "iron": "Morning, fasted; skip iron supplements for 24 h.",
    "tsat": "Morning, fasted; skip iron supplements for 24 h.",
    "estradiol": "Women: day 2–5 of the cycle unless your clinician asks otherwise.",
    "fev1_pct": "No bronchodilator for 4–6 h, no smoking for 1 h, no heavy meal for 2 h.",
    "abpm_day_sbp": "Normal working day; keep the arm still during readings; log sleep and wake times.",
    "pwv": "Rest 10 min supine; no caffeine or nicotine for 3 h.",
    "lsm": "Fast for 3 h — a meal raises liver stiffness readings.",
    "cgm_tir": "Wear for 14 days; log meals and exercise in Telomy so peaks can be explained.",
    "car": "Collect at waking, +30 and +45 min before eating, brushing or caffeine.",
    "g6pd": "Not during or within 3 months of a haemolytic episode or transfusion.",
}
