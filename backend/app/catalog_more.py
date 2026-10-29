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
    "esr": ("ESR", "immune", "mm/h", 0, 15, "low", ["esr (erythrocyte sedimentation rate)", "erythrocyte sedimentation rate"], "4537-7"),
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
