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
    "psa": ("PSA (total)", "hormones", "ng/mL", 0, 1.5, "low", ["psa (total)", "prostate-specific antigen", "prostate specific antigen", "psa, total", "psa total", "total psa"], "2857-1"),
    "dht": ("Dihydrotestosterone (DHT)", "hormones", "ng/dL", 30, 85, "mid", ["dihydrotestosterone", "dht"], "13932-9"),
    "ohp17": ("17-Hydroxyprogesterone", "hormones", "ng/dL", 0, 220, "mid", ["17-hydroxyprogesterone", "17-ohp", "17 ohp", "17-oh progesterone"], "1668-3"),
    "psa_free": ("Free PSA", "hormones", "ng/mL", None, None, "info", ["psa free", "free psa", "psa, free", "prostate-specific antigen, free", "prostate specific antigen, free"], "10886-0"),
    "psa_pct_free": ("% Free PSA", "hormones", "%", 25, 100, "high", ["psa % free", "% free psa", "percent free psa", "free psa %", "psa free %", "psa free percent", "free psa ratio", "free/total psa ratio"], "12841-3"),
    "t3_uptake": ("T3 uptake", "hormones", "%", 24, 39, "mid", ["t3 uptake", "t3 resin uptake", "thyroid uptake"], "3050-2"),
    "fti": ("Free thyroxine index", "hormones", "", 1.2, 4.9, "mid", ["free thyroxine index", "fti", "ft4 index"], "3027-0"),
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
    "vitc": ("Vitamin C (ascorbic acid)", "micronutrients", "mg/dL", 0.4, 2.0, "mid", ["vitamin c", "ascorbic acid"], "1897-8"),
    # LOINC left blank: the spec's 2888-6 is urine protein (already used by u_protein), not vitamin K.
    "vitk1": ("Vitamin K1 (phylloquinone)", "micronutrients", "ng/mL", 0.1, 2.2, "mid", ["vitamin k", "vitamin k1", "phylloquinone"], ""),
    "vitb6": ("Vitamin B6 (PLP)", "micronutrients", "µg/L", 5, 50, "high", ["vitamin b6", "pyridoxal-5-phosphate", "plp"], "2064-7"),
    "rbc_folate": ("RBC folate", "micronutrients", "ng/mL", 280, 900, "high", ["rbc folate", "red cell folate", "erythrocyte folate"], "2285-5"),
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
    "esr": ("ESR", "immune", "mm/h", 0, 15, "low", ["esr (erythrocyte sedimentation rate)", "erythrocyte sedimentation rate", "esr"], "4537-7"),
    "ana": ("Antinuclear antibodies (ANA, IFA)", "immune", "", None, None, "absent", ["antinuclear antibodies"], "8061-4"),
    "ttg_iga": ("tTG-IgA (coeliac screen)", "immune", "U/mL", 0, 4, "low", ["ttg-iga"], "31017-7"),
    "total_ige": ("Total IgE", "immune", "IU/mL", 0, 100, "low", ["total ige"], "19113-0"),
    "ige_mite": ("Specific IgE: house dust mite", "immune", "kUA/L", 0, 0.35, "low", ["specific ige: house dust mite"], ""),
    "ige_pollen": ("Specific IgE: grass pollen", "immune", "kUA/L", 0, 0.35, "low", ["specific ige: grass pollen"], ""),
    "g6pd": ("G6PD activity", "immune", "U/g Hb", 7.0, 20.5, "high", ["g6pd activity", "g6pd"], "32546-4"),
    "ccp_ab": ("Anti-CCP antibody", "immune", "U/mL", 0, 20, "low", ["cyclic citrullinated peptide", "anti-ccp", "ccp antibody"], "33935-8"),
    "dsdna_ab": ("Anti-dsDNA antibody", "immune", "IU/mL", 0, 30, "low", ["double-stranded dna antibodies", "anti-dsdna", "dsdna"], "5131-8"),
    "rf": ("Rheumatoid factor", "immune", "IU/mL", 0, 14, "low", ["rheumatoid factor", "rf"], "11572-5"),
    "iga_serum": ("Immunoglobulin A (serum)", "immune", "mg/dL", 70, 400, "mid", ["immunoglobulin a", "serum iga"], "2458-8"),
    "ena_ssa_ro": ("Anti-SS-A (Ro)", "immune", "", None, None, "absent", ["anti-ro (ss-a)", "anti-ro", "anti-ss-a", "ss-a"], ""),
    "ena_ssb_la": ("Anti-SS-B (La)", "immune", "", None, None, "absent", ["anti-ss-b", "anti-la", "ss-b", "la antibody"], ""),
    "ena_sm": ("Anti-Smith (Sm)", "immune", "", None, None, "absent", ["smith antibody", "anti-smith", "anti-sm"], ""),
    "ena_rnp": ("Anti-RNP", "immune", "", None, None, "absent", ["rnp antibody", "anti-rnp"], ""),
    # urine routine
    "u_ph": ("Urine pH", "urine", "", 5.0, 7.0, "mid", ["urine ph"], "2756-5"),
    "u_sg": ("Urine specific gravity", "urine", "", 1.005, 1.025, "mid", ["urine specific gravity"], "2965-2"),
    "u_protein": ("Urine protein", "urine", "", None, None, "absent", ["urine protein"], "2888-6"),
    "u_glucose": ("Urine glucose", "urine", "", None, None, "absent", ["urine glucose"], "2350-7"),
    "u_blood": ("Urine blood", "urine", "", None, None, "absent", ["urine blood"], "5794-3"),
    "u_pus": ("Urine pus cells", "urine", "/hpf", 0, 5, "low", ["urine pus cells"], "5821-4"),
    "u_ketones": ("Urine ketones", "urine", "", None, None, "absent", ["urine ketones"], "2514-8"),
    "u_nitrite": ("Urine nitrite", "urine", "", None, None, "absent", ["urine nitrite"], "5802-4"),
    "u_leuk_est": ("Urine leukocyte esterase", "urine", "", None, None, "absent", ["urine leukocyte esterase", "leukocyte esterase"], "5799-2"),
    "u_bilirubin": ("Urine bilirubin", "urine", "", None, None, "absent", ["urine bilirubin"], "5770-3"),
    "u_urobilinogen": ("Urobilinogen", "urine", "mg/dL", 0, 1.0, "low", ["urobilinogen"], "19161-9"),
    "u_rbc": ("Urine RBCs", "urine", "/hpf", 0, 2, "low", ["urine rbcs", "urine red blood cells"], "13945-1"),
    "u_epithelial": ("Urine epithelial cells", "urine", "/hpf", 0, 5, "low", ["urine epithelial cells", "urine squamous epithelial cells"], "20453-7"),
    "u_casts": ("Urine casts", "urine", "", None, None, "absent", ["urine granular casts", "urine hyaline casts", "urine casts"], ""),
    "u_bacteria": ("Urine bacteria", "urine", "", None, None, "absent", ["urine bacteria"], "5769-5"),
    "u_crystals": ("Urine crystals", "urine", "", None, None, "absent", ["urine crystals"], ""),
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

# ---- Tier 2 bulk panels (uniform unit/direction; built from compact tables, tuple shape identical to the rows above)
# Specific-IgE allergens (immune): sensitisation >=0.35 kUA/L. id suffix, display name, extra aliases.
_ALLERGENS = [
    ("alternaria", "Alternaria alternata", ["alternaria"]), ("aspergillus", "Aspergillus fumigatus", ["aspergillus"]),
    ("dfarinae", "D. farinae (house dust mite)", ["d. farinae", "dermatophagoides farinae"]),
    ("dpter", "D. pteronyssinus (house dust mite)", ["d. pteronyssinus", "dermatophagoides pteronyssinus"]),
    ("bermuda", "Bermuda grass", ["bermuda grass"]), ("timothy", "Timothy grass", ["timothy grass"]),
    ("cat", "Cat dander", ["cat dander"]), ("dog", "Dog dander", ["dog dander"]), ("cockroach", "Cockroach", ["cockroach"]),
    ("pigweed", "Pigweed", ["pigweed"]), ("ragweed", "Ragweed", ["ragweed"]), ("cedar", "Mountain cedar", ["mountain cedar", "cedar tree"]),
    ("mugwort", "Mugwort", ["mugwort"]), ("penicillium", "Penicillium notatum", ["penicillium"]), ("birch", "Birch", ["birch tree"]),
    ("sycamore", "Sycamore", ["sycamore"]), ("ash", "Ash tree", ["ash tree", "white ash"]), ("elm", "Elm tree", ["elm tree"]),
    ("mulberry", "Mulberry", ["mulberry"]), ("oak", "Oak tree", ["oak tree", "white oak"]),
]
ALLERGEN_IDS = [f"ige_{k}" for k, _, _ in _ALLERGENS]
MORE_MARKERS.update({
    f"ige_{k}": (f"Specific IgE: {n}", "immune", "kUA/L", 0, 0.35, "low", list(dict.fromkeys([f"specific ige: {k_al}" for k_al in [n.lower()] + a] + a)), "")
    for k, n, a in _ALLERGENS
})

# Organic acids (OAT, urine, mmol/mol creat) - functional-medicine grade; reported for context, never scored (better="info").
_OAT = [  # (id suffix, name, aliases, family, evidence)
    ("citric", "Citric acid", ["citric acid"], "Krebs", "C"), ("aconitic", "cis-Aconitic acid", ["cis-aconitic acid", "aconitic acid"], "Krebs", "C"),
    ("isocitric", "Isocitric acid", ["isocitric acid"], "Krebs", "C"), ("akg", "α-Ketoglutaric acid", ["alpha-ketoglutaric acid", "α-ketoglutaric acid", "2-oxoglutaric acid"], "Krebs", "C"),
    ("succinic", "Succinic acid", ["succinic acid"], "Krebs", "C"), ("fumaric", "Fumaric acid", ["fumaric acid"], "Krebs", "C"),
    ("malic", "Malic acid", ["malic acid"], "Krebs", "C"), ("hmg", "3-Hydroxy-3-methylglutaric acid (HMG)", ["3-hydroxy-3-methylglutaric acid", "hmg"], "Krebs", "C"),
    ("adipic", "Adipic acid", ["adipic acid"], "Fatty-acid oxidation", "C"), ("suberic", "Suberic acid", ["suberic acid"], "Fatty-acid oxidation", "C"),
    ("sebacic", "Sebacic acid", ["sebacic acid"], "Fatty-acid oxidation", "C"), ("ethylmalonic", "Ethylmalonic acid", ["ethylmalonic acid"], "Fatty-acid oxidation", "C"),
    ("hva", "Homovanillic acid (HVA)", ["homovanillic acid", "hva"], "Neurotransmitter", "C"), ("vma", "Vanillylmandelic acid (VMA)", ["vanillylmandelic acid", "vma"], "Neurotransmitter", "C"),
    ("dopac", "DOPAC", ["dopac", "3,4-dihydroxyphenylacetic acid"], "Neurotransmitter", "D"), ("quinolinic", "Quinolinic acid", ["quinolinic acid"], "Neurotransmitter", "D"),
    ("hippuric", "Hippuric acid", ["hippuric acid"], "Microbial", "D"), ("cresol4", "4-Cresol", ["4-cresol", "p-cresol"], "Microbial", "D"),
    ("hphpa", "HPHPA (Clostridia marker)", ["3-(3-hydroxyphenyl)-3-hydroxypropionic acid", "hphpa"], "Microbial", "D"),
    ("dhppa", "DHPPA (Clostridia marker)", ["3,4-dihydroxyphenylpropionic acid", "dhppa"], "Microbial", "D"),
    ("arabinose", "Arabinose (yeast marker)", ["arabinose"], "Microbial", "D"), ("tartaric", "Tartaric acid (yeast marker)", ["tartaric acid"], "Microbial", "D"),
    ("pyridoxic", "Pyridoxic acid (B6)", ["pyridoxic acid", "4-pyridoxic acid"], "B-vitamin", "D"), ("pantothenic", "Pantothenic acid (B5)", ["pantothenic acid"], "B-vitamin", "D"),
    ("glutaric", "Glutaric acid (B2)", ["glutaric acid"], "B-vitamin", "D"),
]
OAT_IDS = [f"oat_{k}" for k, *_ in _OAT]
MORE_MARKERS.update({
    f"oat_{k}": (f"{n} (OAT, {fam.lower()})", "functional", "mmol/mol creat", None, None, "info", a, "") for k, n, a, fam, _ in _OAT
})

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

# ---- 2026-10-29 biomarker gap expansion: evidence grades, zones, concerns, prep (Tier 1 + Tier 2)
MORE_EVIDENCE.update({
    **{m: "A" for m in ["ohp17", "psa_free", "psa_pct_free", "ccp_ab", "dsdna_ab", "rf", "iga_serum", "u_ketones", "u_nitrite",
                        "u_leuk_est", "u_bilirubin", "u_urobilinogen", "u_rbc", "u_epithelial", "u_bacteria"]},
    **{m: "B" for m in ["vitc", "vitb6", "rbc_folate", "dht", "t3_uptake", "fti", "ena_ssa_ro", "ena_ssb_la", "ena_sm", "ena_rnp",
                        "u_casts", "u_crystals", *ALLERGEN_IDS]},
    "vitk1": "C",  # assay variability; functional (PIVKA-II) status markers are better but not in the catalogue
    # functional-medicine grade: Krebs / fatty-acid / neurotransmitter OAT are C, microbial & B-vitamin OAT are D
    **{f"oat_{k}": ev for k, _, _, _, ev in _OAT},
})

_IGE_BANDS = [(0.35, "Not sensitised", "optimal"), (3.5, "Sensitised (class 1–2)", "out_of_range"), (None, "Strongly sensitised", "out_of_range")]
MORE_ZONES.update({
    **{m: _IGE_BANDS for m in ALLERGEN_IDS},
    "ccp_ab": [(20, "Negative", "optimal"), (60, "Weak to moderate positive", "out_of_range"), (None, "Strong positive (>3× ULN)", "out_of_range")],
    "rf": [(14, "Negative", "optimal"), (42, "Low positive", "out_of_range"), (None, "High positive (>3× ULN)", "out_of_range")],
    "dsdna_ab": [(30, "Negative", "optimal"), (75, "Borderline", "in_range"), (None, "Positive", "out_of_range")],
    # %free PSA is only informative when total PSA is 4–10 ng/mL (prostate cancer likelihood falls as the free fraction rises).
    # Stored under "male" (PSA is a male test); zone_for() falls back to it for any other profile sex.
    "psa_pct_free": {"male": [(10, "Very low — high suspicion if total PSA 4–10", "out_of_range"), (15, "Low — raised suspicion", "out_of_range"),
                              (25, "Borderline", "in_range"), (None, "Reassuring", "optimal")]},
})

MORE_CONCERNS_EXTRA = {
    "Hormones & thyroid": ["dht", "ohp17", "psa_free", "psa_pct_free", "t3_uptake", "fti"],
    "Nutrients": ["vitc", "vitk1", "vitb6", "rbc_folate"],
    "Inflammation & immunity": ["ccp_ab", "dsdna_ab", "rf", "iga_serum", "ena_ssa_ro", "ena_ssb_la", "ena_sm", "ena_rnp"],
    "Kidney": ["u_leuk_est", "u_nitrite", "u_rbc", "u_casts", "u_bacteria", "u_crystals"],
    "Liver": ["u_bilirubin", "u_urobilinogen"],
    "Blood sugar & metabolism": ["u_ketones"],
    "Cancer screening": ["psa_free", "psa_pct_free"],
    "Lungs & breathing": ALLERGEN_IDS,
    "Stress & nervous system": ["oat_hva", "oat_vma", "oat_dopac", "oat_quinolinic"],
    "Gut": ["oat_hippuric", "oat_cresol4", "oat_hphpa", "oat_dhppa", "oat_arabinose", "oat_tartaric"],
}
for _k, _v in MORE_CONCERNS_EXTRA.items():
    MORE_CONCERNS.setdefault(_k, [])
    MORE_CONCERNS[_k] += [m for m in _v if m not in MORE_CONCERNS[_k]]

MORE_PREP.update({
    "vitc": "Fasted draw; protect the sample from light and deliver on ice, as vitamin C degrades quickly.",
    "vitb6": "Fasted; skip B6 or multivitamin supplements for 24 h before the draw.",
    "dht": "Draw between 7 and 10 am.",
    "ohp17": "Women: follicular phase (day 2–5); draw in the morning.",
    "psa_pct_free": "Only informative when total PSA is 4–10 ng/mL; same prep as PSA.",
    "ccp_ab": "No preparation; interpret together with rheumatoid factor.",
    "u_nitrite": "First-morning mid-stream urine, processed within 2 hours.",
    "u_ketones": "First-morning mid-stream urine; note if fasting or on a low-carbohydrate diet.",
    "oat_citric": "First-morning urine; functional-medicine grade, so interpret with a clinician.",
})


# ---- 2026-10-29 infectious-disease menu (viral / bacterial / parasitic / fungal / STI / cultures / molecular)
# Mostly QUALITATIVE (serology, antigen, PCR, culture). better="absent": a negative result is the good one, so "Reactive" /
# "Positive" / "Growth of ..." surface as `detected` (see catalog.status_for). better="info": quantitative loads/titres, and
# IgG / anti-HBs results where positive means past exposure or immunity and must NOT be flagged. Reference intervals are the
# performing lab's. Aliases are specific on purpose (match_marker is longest-prefix): no bare "hiv", "tb", "pcr", "culture".
MORE_PANELS["infectious"] = "Infectious disease (viral, bacterial, parasitic, STI)"

_A, _I = "absent", "info"
_INF = [  # (id, name, unit, better, aliases, loinc, evidence)
    # viral hepatitis
    ("hav_igm", "Hepatitis A IgM", "", _A, ["hepatitis a igm", "hepatitis a virus igm", "hav igm", "anti-hav igm", "hepatitis a - igm"], "22314-9", "A"),
    ("hav_igg", "Hepatitis A IgG (immunity)", "", _I, ["hepatitis a igg", "hepatitis a total antibody", "hav igg", "anti-hav igg", "anti-hav total", "hepatitis a - igg"], "", "A"),
    ("hbsag", "Hepatitis B surface antigen (HBsAg)", "", _A, ["hepatitis b surface antigen", "hbsag", "hbs ag", "hepatitis b virus surface antigen", "australia antigen"], "5196-1", "A"),
    ("anti_hbs", "Anti-HBs (surface antibody)", "mIU/mL", _I, ["anti-hbs", "anti hbs", "hbsab", "hepatitis b surface antibody", "hepatitis b surface antibodies"], "22322-2", "A"),
    ("hbeag", "HBeAg", "", _A, ["hbeag", "hepatitis b e antigen", "hepatitis be antigen"], "13954-3", "A"),
    ("anti_hbe", "Anti-HBe", "", _I, ["anti-hbe", "anti hbe", "hepatitis b e antibody"], "", "A"),
    ("anti_hbc_total", "Anti-HBc (total)", "", _A, ["anti-hbc total", "anti hbc total", "hbc total", "anti-hbc", "anti hbc", "hepatitis b core antibody total", "hepatitis b core antibody"], "13952-7", "A"),
    ("anti_hbc_igm", "Anti-HBc IgM", "", _A, ["anti-hbc igm", "anti hbc igm", "hbc igm", "hepatitis b core antibody igm", "hepatitis b core igm"], "", "A"),
    ("hbv_dna", "Hepatitis B viral load (HBV DNA, quantitative PCR)", "IU/mL", _I, ["hbv dna", "hbv viral load", "hepatitis b viral load", "hepatitis b virus dna", "hepatitis b virus hbv dna", "hbv-dna"], "42595-9", "A"),
    ("hcv_ab", "Anti-HCV (hepatitis C antibody)", "", _A, ["anti-hcv", "anti hcv", "hcv antibody", "hcv ab", "hepatitis c antibody", "hepatitis c virus antibody", "hepatitis c virus hcv antibody", "hepatitis c antibodies"], "16128-1", "A"),
    ("hcv_rna", "Hepatitis C viral load (HCV RNA, PCR)", "IU/mL", _I, ["hcv rna", "hcv viral load", "hepatitis c viral load", "hepatitis c virus rna", "hepatitis c virus hcv rna", "hcv-rna"], "11011-4", "A"),
    ("hcv_genotype", "HCV genotype", "", _I, ["hcv genotype", "hcv genotyping", "hepatitis c genotype"], "", "A"),
    ("hev_igm", "Hepatitis E IgM", "", _A, ["hepatitis e igm", "hev igm", "anti-hev igm", "hepatitis e virus igm"], "", "B"),
    # viral systemic & respiratory
    ("hiv_combo", "HIV 1 & 2 (4th-gen antigen/antibody)", "", _A, ["hiv 1 & 2", "hiv 1 and 2", "hiv 1/2", "hiv-1/2", "hiv i & ii", "hiv i and ii", "hiv combo", "hiv duo", "hiv ag/ab", "hiv antibody", "anti-hiv", "hiv screening", "hiv elisa", "hiv 4th generation"], "56888-1", "A"),
    ("hiv_rna", "HIV viral load (RNA PCR)", "copies/mL", _I, ["hiv viral load", "hiv rna", "hiv-1 rna", "hiv 1 rna", "hiv-1 viral load", "hiv 1 viral load", "hiv-1 rna quantitative"], "20447-9", "A"),
    ("cd4", "CD4 count", "cells/µL", _I, ["cd4 count", "cd4 absolute", "absolute cd4", "cd4 t cell", "cd4 t-cell", "cd4 cell count"], "24467-3", "A"),
    ("dengue_ns1", "Dengue NS1 antigen", "", _A, ["dengue ns1", "dengue ns-1", "dengue antigen", "dengue virus ns1"], "", "A"),
    ("dengue_igm", "Dengue IgM", "", _A, ["dengue igm", "dengue virus igm", "dengue antibody igm", "dengue - igm", "dengue fever igm", "dengue fever antibody igm"], "", "A"),
    ("dengue_igg", "Dengue IgG", "", _I, ["dengue igg", "dengue virus igg", "dengue antibody igg", "dengue - igg", "dengue fever igg", "dengue fever antibody igg"], "", "A"),
    ("chik_igm", "Chikungunya IgM", "", _A, ["chikungunya igm", "chikungunya virus igm", "chikungunya antibody igm"], "", "B"),
    ("chik_igg", "Chikungunya IgG", "", _I, ["chikungunya igg", "chikungunya virus igg", "chikungunya antibody igg"], "", "B"),
    ("chik_pcr", "Chikungunya RT-PCR", "", _A, ["chikungunya rt-pcr", "chikungunya rt pcr", "chikungunya pcr", "chikungunya rna"], "", "B"),
    ("zika_pcr", "Zika virus RT-PCR", "", _A, ["zika virus rt-pcr", "zika virus rt pcr", "zika rt-pcr", "zika pcr", "zika virus rna", "zika virus pcr"], "", "B"),
    ("covid_pcr", "SARS-CoV-2 RT-PCR", "", _A, ["sars-cov-2 rt-pcr", "sars-cov-2 rt pcr", "sars cov 2 rt pcr", "sars-cov-2 rna", "sars-cov-2 pcr", "covid-19 rt-pcr", "covid-19 rt pcr", "covid 19 rt pcr", "covid rt-pcr", "covid-19 pcr", "covid-19 rna"], "", "A"),
    ("covid_ag", "SARS-CoV-2 rapid antigen", "", _A, ["sars-cov-2 antigen", "sars-cov-2 rapid antigen", "sars cov 2 antigen", "covid-19 antigen", "covid-19 rapid antigen", "covid antigen", "rapid antigen test"], "", "A"),
    ("covid_igg", "SARS-CoV-2 antibody (IgG / IgM serology)", "", _I, ["sars-cov-2 igg", "sars-cov-2 igm", "sars-cov-2 antibody", "sars-cov-2 antibodies", "covid-19 igg", "covid-19 igm", "covid-19 antibody", "covid igg"], "", "B"),
    ("influenza_ab", "Influenza A & B (antigen / RT-PCR)", "", _A, ["influenza a & b", "influenza a and b", "influenza a/b", "influenza a h1n1", "influenza antigen", "influenza rt-pcr", "influenza pcr", "h1n1 rt-pcr", "h1n1 pcr", "swine flu"], "", "A"),
    ("resp_viral_pcr", "Respiratory viral panel (multiplex PCR)", "", _A, ["respiratory viral panel", "respiratory pathogen panel", "respiratory virus panel", "respiratory multiplex pcr", "respiratory pcr panel", "multiplex respiratory"], "", "B"),
    ("cmv_igm", "CMV IgM", "", _A, ["cmv igm", "cytomegalovirus igm", "cytomegalovirus antibody igm", "cmv - igm"], "", "A"),
    ("cmv_igg", "CMV IgG", "", _I, ["cmv igg", "cytomegalovirus igg", "cytomegalovirus antibody igg", "cmv - igg"], "", "A"),
    ("cmv_pcr", "CMV DNA (quantitative PCR)", "copies/mL", _I, ["cmv dna", "cmv pcr", "cmv viral load", "cytomegalovirus dna", "cytomegalovirus pcr", "cytomegalovirus viral load"], "", "A"),
    ("ebv_vca_igm", "EBV VCA IgM", "", _A, ["ebv vca igm", "ebv igm", "epstein barr virus vca igm", "epstein-barr virus vca igm", "epstein barr virus igm", "epstein-barr virus igm", "vca igm"], "", "B"),
    ("ebv_vca_igg", "EBV VCA IgG", "", _I, ["ebv vca igg", "ebv igg", "epstein barr virus vca igg", "epstein-barr virus vca igg", "epstein barr virus igg", "epstein-barr virus igg", "vca igg"], "", "B"),
    ("ebv_ebna", "EBV EBNA IgG", "", _I, ["ebv ebna", "ebna igg", "epstein barr nuclear antigen", "epstein-barr virus ebna", "epstein barr virus ebna"], "", "B"),
    ("hsv_igm", "HSV-1 & HSV-2 IgM", "", _A, ["hsv igm", "hsv 1 & 2 igm", "hsv-1 igm", "hsv-2 igm", "hsv 1/2 igm", "herpes simplex igm", "herpes simplex virus igm", "herpes simplex virus 1 & 2 igm", "herpes simplex virus 1 and 2 igm"], "", "B"),
    ("hsv_igg", "HSV-1 & HSV-2 IgG", "", _I, ["hsv igg", "hsv 1 & 2 igg", "hsv-1 igg", "hsv-2 igg", "hsv 1/2 igg", "herpes simplex igg", "herpes simplex virus igg", "herpes simplex virus 1 & 2 igg", "herpes simplex virus 1 and 2 igg"], "", "B"),
    ("hsv_pcr", "HSV-1 & HSV-2 PCR", "", _A, ["hsv pcr", "hsv dna", "hsv-1 pcr", "hsv 1 & 2 pcr", "hsv 1/2 pcr", "herpes simplex pcr", "herpes simplex virus pcr", "herpes simplex virus dna"], "", "B"),
    ("vzv_igm", "Varicella-zoster (VZV) IgM", "", _A, ["vzv igm", "varicella zoster igm", "varicella-zoster igm", "varicella zoster virus igm", "varicella igm"], "", "B"),
    ("vzv_igg", "Varicella-zoster (VZV) IgG", "", _I, ["vzv igg", "varicella zoster igg", "varicella-zoster igg", "varicella zoster virus igg", "varicella igg"], "", "B"),
    ("mmr_igm", "Measles / Mumps / Rubella IgM", "", _A, ["measles igm", "mumps igm", "rubella igm", "measles virus igm", "mumps virus igm", "rubella virus igm", "rubella antibody igm"], "", "A"),
    ("mmr_igg", "Measles / Mumps / Rubella IgG (immunity)", "", _I, ["measles igg", "mumps igg", "rubella igg", "measles virus igg", "mumps virus igg", "rubella virus igg", "rubella antibody igg"], "", "A"),
    ("rota_noro_ag", "Rotavirus & Norovirus antigen (stool)", "", _A, ["rotavirus antigen", "rotavirus ag", "norovirus antigen", "norovirus ag", "rotavirus & norovirus", "rotavirus and norovirus"], "", "B"),
    # bacterial
    ("widal", "Widal test (typhoid agglutination)", "", _I, ["widal test", "widal slide agglutination", "widal tube agglutination", "widal", "salmonella typhi o", "salmonella typhi h"], "", "B"),
    ("typhidot", "Typhoid IgM / IgG (Typhidot)", "", _A, ["typhidot igm", "typhidot igg", "typhidot", "typhoid igm", "typhoid igg", "salmonella typhi igm", "salmonella typhi igg"], "", "B"),
    ("salmonella_culture", "Salmonella (typhoid) blood culture", "", _A, ["salmonella blood culture", "typhoid blood culture", "blood culture for salmonella", "blood culture for typhoid", "salmonella culture", "salmonella typhi culture", "enteric fever culture"], "", "A"),
    ("mantoux", "Mantoux / tuberculin skin test", "mm", _I, ["mantoux test", "mantoux", "tuberculin skin test", "tuberculin test"], "", "A"),
    ("tb_igra", "TB IGRA (QuantiFERON-TB Gold)", "", _A, ["quantiferon-tb gold", "quantiferon tb gold", "quantiferon-tb", "quantiferon tb", "quantiferon", "tb gold", "tb igra", "interferon gamma release assay", "interferon-gamma release assay", "t-spot.tb", "t-spot tb"], "", "A"),
    ("tb_afb_smear", "TB AFB smear (Ziehl-Neelsen)", "", _A, ["afb smear", "afb stain", "afb (ziehl neelsen)", "afb (ziehl-neelsen)", "ziehl neelsen", "ziehl-neelsen", "acid fast bacilli", "acid-fast bacilli", "sputum for afb", "sputum afb"], "", "A"),
    ("tb_genexpert", "TB GeneXpert MTB/RIF (PCR + rifampicin resistance)", "", _A, ["genexpert mtb/rif", "genexpert mtb rif", "genexpert", "gene xpert", "cbnaat", "xpert mtb/rif", "mtb/rif", "mycobacterium tuberculosis pcr", "mycobacterium tuberculosis dna", "tb pcr", "tb-pcr", "truenat"], "", "A"),
    ("tb_culture", "TB MGIT liquid culture & drug susceptibility", "", _A, ["mgit culture", "mgit 960", "tb culture", "tb mgit", "mycobacterial culture", "mycobacterium culture", "tb drug susceptibility", "afb culture", "mycobacterium tuberculosis culture"], "", "A"),
    ("hpylori_stool_ag", "Helicobacter pylori stool antigen", "", _A, ["h. pylori stool antigen", "h pylori stool antigen", "helicobacter pylori stool antigen", "h.pylori stool antigen", "helicobacter pylori antigen", "h. pylori faecal antigen", "h. pylori fecal antigen", "stool h. pylori antigen"], "", "A"),
    ("hpylori_ubt", "H. pylori urea breath test", "", _A, ["h. pylori urea breath test", "h pylori urea breath test", "helicobacter pylori urea breath test", "urea breath test", "c13 urea breath test", "13c urea breath test", "h. pylori breath test"], "", "A"),
    ("hpylori_igg", "H. pylori IgG (serology)", "", _A, ["h. pylori igg", "h pylori igg", "helicobacter pylori igg", "h.pylori igg", "h. pylori antibody", "helicobacter pylori antibody", "h. pylori antibodies", "h. pylori serology"], "", "B"),
    ("aso", "ASO (anti-streptolysin O)", "IU/mL", "low", ["anti-streptolysin o", "anti streptolysin o", "antistreptolysin o", "aso titre", "aso titer", "aso quantitative", "aslo", "aso"], "", "A"),
    ("lepto_igm", "Leptospira IgM", "", _A, ["leptospira igm", "leptospira antibody igm", "leptospira antibodies igm", "leptospira elisa", "leptospirosis igm"], "", "B"),
    ("brucella", "Brucella (agglutination / antibody)", "", _A, ["brucella agglutination", "brucella antibody", "brucella antibodies", "brucella igm", "brucella igg", "brucella serology", "brucella abortus"], "", "B"),
    ("mycoplasma_igm", "Mycoplasma pneumoniae IgM", "", _A, ["mycoplasma pneumoniae igm", "mycoplasma igm", "m. pneumoniae igm", "mycoplasma pneumoniae antibody igm"], "", "B"),
    ("mycoplasma_igg", "Mycoplasma pneumoniae IgG", "", _I, ["mycoplasma pneumoniae igg", "mycoplasma igg", "m. pneumoniae igg", "mycoplasma pneumoniae antibody igg"], "", "B"),
    ("chlamydia_pneumo", "Chlamydia pneumoniae (antibody / PCR)", "", _A, ["chlamydia pneumoniae", "chlamydophila pneumoniae", "c. pneumoniae"], "", "B"),
    ("legionella_ag", "Legionella urinary antigen", "", _A, ["legionella urinary antigen", "legionella urine antigen", "legionella pneumophila antigen", "legionella antigen"], "", "A"),
    ("vibrio_culture", "Vibrio cholerae (stool culture)", "", _A, ["vibrio cholerae", "vibrio cholera", "stool culture for vibrio", "stool culture for cholera", "cholera culture"], "", "A"),
    # parasitic & protozoal
    ("malaria_smear", "Malaria parasite - peripheral smear", "", _A, ["malaria parasite", "malarial parasite", "mp smear", "peripheral smear for malaria", "peripheral smear for mp", "malaria smear", "malaria thick and thin", "malaria thick & thin", "thick and thin smear", "malaria microscopy", "malaria - peripheral smear"], "", "A"),
    ("malaria_rdt", "Malaria rapid antigen (Pf/Pv)", "", _A, ["malaria rapid antigen", "malaria antigen", "malaria rapid test", "malaria rapid card", "malaria card", "malaria pf/pv", "malaria pf pv", "malaria pf/pan", "malaria rdt"], "", "A"),
    ("malaria_pcr", "Malaria PCR", "", _A, ["malaria pcr", "malaria rt-pcr", "malaria dna", "plasmodium pcr", "plasmodium dna"], "", "B"),
    ("filaria", "Filaria (antigen / night smear)", "", _A, ["filaria antigen", "filarial antigen", "filaria night smear", "microfilaria", "filaria smear", "night blood smear for filaria", "wuchereria bancrofti"], "", "B"),
    ("kalaazar_rk39", "Leishmania (Kala-azar) rK39 / serology", "", _A, ["rk39", "r-k39", "kala azar", "kala-azar", "leishmania rk39", "leishmania antibody", "leishmania serology", "leishmania donovani", "visceral leishmaniasis"], "", "B"),
    ("entamoeba", "Entamoeba histolytica (stool antigen / serology)", "", _A, ["entamoeba histolytica", "e. histolytica", "entamoeba antigen", "amoebic serology", "amoebiasis serology"], "", "B"),
    ("giardia_ag", "Giardia lamblia stool antigen", "", _A, ["giardia lamblia", "giardia antigen", "giardia stool antigen", "giardia ag", "giardia intestinalis", "giardia duodenalis"], "", "A"),
    ("crypto_stool", "Cryptosporidium (stool)", "", _A, ["cryptosporidium", "cryptosporidium antigen", "cryptosporidium stool", "cryptosporidium parvum"], "", "B"),
    ("toxo_igm", "Toxoplasma gondii IgM", "", _A, ["toxoplasma igm", "toxoplasma gondii igm", "toxoplasma antibody igm", "toxoplasma antibodies igm", "toxoplasmosis igm"], "", "A"),
    ("toxo_igg", "Toxoplasma gondii IgG", "", _I, ["toxoplasma igg", "toxoplasma gondii igg", "toxoplasma antibody igg", "toxoplasma antibodies igg", "toxoplasmosis igg"], "", "A"),
    ("stool_op", "Stool ova & parasite (O&P) microscopy", "", _A, ["stool ova and parasite", "stool ova & parasite", "stool for ova and parasite", "stool for ova & parasite", "ova and parasite", "ova & parasite", "ova, cyst and parasite", "ova cyst parasite", "stool o&p", "stool parasite", "stool for parasites", "stool ova"], "", "A"),
    # fungal
    ("candida_culture", "Candida (culture / antigen)", "", _A, ["candida culture", "candida antigen", "candida albicans culture", "candida albicans antigen", "candida mannan", "candida species", "candida spp"], "", "B"),
    ("aspergillus_gm", "Aspergillus galactomannan", "", _A, ["aspergillus galactomannan", "galactomannan", "aspergillus antigen", "aspergillus ag"], "", "B"),
    ("crag", "Cryptococcal antigen (CrAg)", "", _A, ["cryptococcal antigen", "crag", "cryptococcus antigen", "cryptococcal ag", "cryptococcus neoformans antigen", "india ink"], "", "A"),
    ("fungal_culture", "Fungal culture & sensitivity", "", _A, ["fungal culture", "fungus culture", "fungal culture & sensitivity", "fungal culture and sensitivity", "mycology culture", "fungal smear & culture"], "", "B"),
    ("koh_mount", "KOH mount (skin / nail / hair)", "", _A, ["koh mount", "koh preparation", "koh prep", "koh smear", "koh wet mount", "koh examination", "koh for fungus", "koh test"], "", "A"),
    # STI
    ("vdrl", "VDRL / RPR (syphilis screen)", "", _A, ["vdrl", "rpr", "rapid plasma reagin", "venereal disease research laboratory", "syphilis screening", "syphilis screen", "syphilis rpr", "syphilis vdrl"], "20507-0", "A"),
    ("tpha", "TPHA / FTA-ABS (syphilis confirmatory)", "", _A, ["tpha", "treponema pallidum haemagglutination", "treponema pallidum hemagglutination", "treponema pallidum particle agglutination", "tppa", "fta-abs", "fta abs", "fluorescent treponemal antibody", "treponema pallidum antibody", "treponema pallidum antibodies", "treponema pallidum total antibody", "syphilis total antibody", "syphilis antibody", "syphilis confirmatory", "syphilis igg"], "", "A"),
    ("hpv_hr", "HPV DNA - high-risk genotyping (16/18 + others)", "", _A, ["hpv dna", "hpv high risk", "hpv high-risk", "hpv genotyping", "hpv 16/18", "hpv 16 & 18", "hpv pcr", "hpv typing", "hpv test", "human papillomavirus dna", "human papilloma virus dna", "human papillomavirus high risk", "human papillomavirus", "human papilloma virus"], "", "A"),
    ("ct_naat", "Chlamydia trachomatis (NAAT / PCR)", "", _A, ["chlamydia trachomatis", "c. trachomatis", "chlamydia pcr", "chlamydia naat", "chlamydia dna"], "", "A"),
    ("ng_naat", "Neisseria gonorrhoeae (NAAT / PCR)", "", _A, ["neisseria gonorrhoeae", "n. gonorrhoeae", "gonorrhoea pcr", "gonorrhea pcr", "gonorrhoeae pcr", "gonorrhoea naat", "gonorrhea naat", "gonorrhoeae naat"], "", "A"),
    ("trichomonas", "Trichomonas vaginalis", "", _A, ["trichomonas vaginalis", "t. vaginalis", "trichomonas pcr", "trichomonas naat", "trichomonas antigen", "trichomonas culture", "trichomonas wet mount"], "", "A"),
    ("hsv2_pcr", "HSV-2 PCR", "", _A, ["hsv-2 pcr", "hsv 2 pcr", "hsv2 pcr", "herpes simplex virus 2 pcr", "herpes simplex virus-2 pcr", "hsv-2 dna", "hsv 2 dna", "genital herpes pcr"], "", "A"),
    # cultures & sensitivity
    ("blood_culture", "Blood culture & sensitivity (aerobic / anaerobic)", "", _A, ["blood culture & sensitivity", "blood culture and sensitivity", "blood culture", "blood c/s", "blood c&s", "blood culture, aerobic", "blood culture aerobic", "blood culture anaerobic", "aerobic blood culture", "anaerobic blood culture", "blood culture & susceptibility"], "", "A"),
    ("urine_culture", "Urine culture & sensitivity", "", _A, ["urine culture & sensitivity", "urine culture and sensitivity", "urine culture", "urine c/s", "urine c&s", "urine culture, routine", "urine culture & susceptibility", "urine for culture", "mid stream urine culture", "midstream urine culture", "msu culture"], "", "A"),
    ("stool_culture", "Stool culture & sensitivity", "", _A, ["stool culture & sensitivity", "stool culture and sensitivity", "stool culture", "stool c/s", "stool c&s", "stool culture, routine", "stool for culture", "faeces culture", "feces culture"], "", "A"),
    ("sputum_culture", "Sputum culture & sensitivity", "", _A, ["sputum culture & sensitivity", "sputum culture and sensitivity", "sputum culture", "sputum c/s", "sputum c&s", "sputum for culture", "sputum gram stain & culture"], "", "A"),
    ("throat_nasal_culture", "Throat / nasal swab culture", "", _A, ["throat swab culture", "throat culture", "nasal swab culture", "nasal culture", "throat swab for culture", "throat/nasal swab culture", "throat / nasal swab culture", "throat swab c/s", "nasal swab c/s", "nasopharyngeal swab culture"], "", "A"),
    ("wound_pus_culture", "Wound / pus culture", "", _A, ["wound culture", "pus culture", "wound swab culture", "pus swab culture", "wound/pus culture", "wound / pus culture", "wound c/s", "pus c/s", "wound swab c/s", "pus for culture", "abscess culture"], "", "A"),
    ("csf_culture", "CSF culture & analysis", "", _A, ["csf culture", "csf culture & sensitivity", "csf analysis", "csf routine", "csf examination", "csf gram stain", "csf c/s", "cerebrospinal fluid culture", "cerebrospinal fluid analysis"], "", "A"),
    ("hvs_urethral_culture", "High vaginal / urethral swab culture", "", _A, ["high vaginal swab culture", "high vaginal swab", "hvs culture", "hvs c/s", "urethral swab culture", "urethral culture", "urethral swab c/s", "vaginal swab culture", "vaginal swab c/s"], "", "A"),
    # molecular / multiplex PCR & sepsis
    ("gi_pcr_panel", "Gastrointestinal pathogen panel (multiplex PCR)", "", _A, ["gastrointestinal pathogen panel", "gastrointestinal panel", "gi pathogen panel", "gi pcr panel", "gi multiplex pcr", "stool pathogen panel", "stool multiplex pcr", "stool pcr panel", "diarrhoea panel", "diarrhea panel", "enteric pathogen panel"], "", "B"),
    ("meningitis_pcr", "Meningitis / encephalitis panel (PCR)", "", _A, ["meningitis/encephalitis panel", "meningitis / encephalitis panel", "meningitis encephalitis panel", "meningitis panel", "encephalitis panel", "meningitis pcr", "encephalitis pcr", "meningitis/encephalitis pcr", "csf pcr panel", "csf multiplex pcr"], "", "B"),
    ("sepsis_pcr", "Sepsis / bloodstream pathogen PCR", "", _A, ["sepsis pcr", "sepsis panel", "sepsis pathogen pcr", "sepsis pathogen panel", "sepsis multiplex pcr", "bloodstream pathogen pcr", "bloodstream pathogen panel", "bloodstream infection panel", "blood pathogen panel", "blood pathogen pcr", "septifast"], "", "B"),
    ("procalcitonin", "Procalcitonin (bacterial sepsis marker)", "ng/mL", "low", ["procalcitonin", "pro-calcitonin", "pro calcitonin"], "33959-8", "A"),
]
# Quantitative non-zero optima only where a clean cut-off exists (ASO <200 IU/mL, PCT <0.1 ng/mL); everything else is None.
_INF_OPT = {"aso": (0, 200), "procalcitonin": (0, 0.1)}
MORE_MARKERS.update({i: (n, "infectious", u, *_INF_OPT.get(i, (None, None)), b, a, l) for i, n, u, b, a, l, _ in _INF})
MORE_EVIDENCE.update({i: ev for i, *_, ev in _INF})
INFECTIOUS_IDS = [i for i, *_ in _INF]
MORE_CONCERNS["Infections"] = INFECTIOUS_IDS + ["hscrp", "esr"]
MORE_RETEST["infectious"] = 365
MORE_PREP.update({
    "blood_culture": "Collect before the first antibiotic dose, from two separate sites, with strict skin antisepsis.",
    "urine_culture": "Clean-catch mid-stream sample, ideally first-morning; deliver within 2 hours or refrigerate.",
    "stool_culture": "Fresh sample in a sterile container; deliver within 2 hours.",
    "stool_op": "Fresh sample in a clean container; up to three samples on alternate days improve yield.",
    "sputum_culture": "Early-morning deep-cough sample after rinsing the mouth with water; not saliva.",
    "tb_genexpert": "Early-morning sputum, deep cough, before starting anti-TB treatment.",
    "hpylori_stool_ag": "Stop PPIs for 2 weeks and antibiotics/bismuth for 4 weeks before the test.",
    "hpylori_ubt": "Fast 6 h; stop PPIs for 2 weeks and antibiotics/bismuth for 4 weeks before the test.",
    "hpv_hr": "Not during your period; no intercourse, douching or vaginal creams for 48 h.",
    "ct_naat": "Hold urine for 1-2 h before a first-void sample; no antibiotics in the last 2 weeks.",
    "ng_naat": "Hold urine for 1-2 h before a first-void sample; no antibiotics in the last 2 weeks.",
    "malaria_smear": "Best drawn during a fever spike; repeat every 12-24 h for 3 samples if negative but symptoms persist.",
    "dengue_ns1": "Most sensitive in the first 5 days of fever; IgM becomes positive after day 5.",
})
