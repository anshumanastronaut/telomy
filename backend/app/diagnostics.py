"""Tests & scans catalogue — what to test, why, how often, how to prepare, what it costs in India — plus a personalised
"what should I test next" list that combines guideline screening (USPSTF / ADA / ESC / KDIGO / ICMR), risk-based tests
from the Vault, and gaps in the person's data. Prices are indicative Indian list prices (Oct 2026), test mode only.

Evidence: A guideline-endorsed screening · B strong prognostic value · C emerging / research-grade · D not recommended.
"""
from datetime import date

from . import db, engine
from .catalog import MARKERS
from .catalog_more import ALLERGEN_IDS, OAT_IDS

# Marker-id groups added 2026-10-29 (biomarker gap vs Superpower); kept here so the TESTS rows below stay readable.
_METALS_X = ["antimony", "barium", "beryllium", "bismuth", "cesium", "gadolinium", "palladium", "platinum", "tellurium", "thorium",
             "tin", "tungsten", "uranium", "cobalt", "mercury_blood"]
_ENV_X = ["bps", "methylparaben", "ethylparaben", "propylparaben", "butylparaben", "pba3", "atrazine", "dpp", "oxybenzone", "mbp", "mibp",
          "meohp", "hema", "methylhippuric", "phenylglyoxylic"]
_MYCO_X = ["chaetoglobosin_a", "citrinin", "enniatin_b", "gliotoxin", "mycophenolic_acid", "roridin_e", "sterigmatocystin", "verrucarin_a"]
_ENA = ["ena_ssa_ro", "ena_ssb_la", "ena_sm", "ena_rnp"]
_URINE_X = ["u_ketones", "u_nitrite", "u_leuk_est", "u_bilirubin", "u_urobilinogen", "u_rbc", "u_epithelial", "u_casts", "u_bacteria", "u_crystals"]

# id: name, category, panel (parser), markers, why, evidence, price ₹, sample, turnaround, prep, frequency text
T = lambda *a: dict(zip(("name", "category", "panel", "markers", "why", "evidence", "price", "sample", "tat", "prep", "freq"), a))  # noqa: E731
TESTS = {
    # ---------------- blood
    "cbc": T("Complete blood count", "Blood", "blood", ["hemoglobin", "wbc", "platelets", "mcv", "rdw", "lymph_pct", "neutrophil_pct"],
             "Anaemia, infection and blood-cell health; RDW and lymphocytes feed biological age.", "A", 400, "Blood", "Same day", "None", "Yearly"),
    "cmp": T("Metabolic panel (kidney, liver, electrolytes)", "Blood", "blood", ["creatinine", "egfr", "alt", "ast", "ggt", "albumin", "alp", "sodium", "potassium", "calcium"],
             "Kidney and liver function, electrolytes.", "A", 900, "Blood", "Same day", "Fast 8 h", "Yearly"),
    "lipid": T("Lipid profile", "Blood", "blood", ["chol_total", "ldl", "hdl", "tg", "nonhdl", "vldl"], "Core cardiovascular risk input (PREVENT, PCE); non-HDL is the secondary target when triglycerides are high.", "A", 600, "Blood", "Same day", "Fast 10–12 h", "Every 1–5 years"),
    "apob": T("Apolipoprotein B", "Blood", "blood", ["apob"], "Counts every atherogenic particle — better than LDL when triglycerides are high (ESC/EAS).", "A", 1200, "Blood", "1 day", "None", "Yearly if raised"),
    "lpa": T("Lipoprotein(a)", "Blood", "blood", ["lpa"], "Inherited risk factor; measure once in a lifetime (ESC/EAS 2022 consensus).", "A", 1500, "Blood", "2 days", "None", "Once"),
    "glycaemia": T("HbA1c + fasting glucose + insulin (HOMA-IR)", "Blood", "blood", ["hba1c", "glucose", "insulin", "homa_ir", "cpeptide", "fructosamine"],
                   "Diabetes screening (ADA) and early insulin resistance; C-peptide separates insulin resistance from low insulin output, fructosamine tracks the past 2–3 weeks.", "A", 1100, "Blood", "Same day", "Fast 8–12 h", "Yearly from 35 (ADA)"),
    "ogtt": T("Oral glucose tolerance test (2-h)", "Blood", "blood", ["glucose"], "Catches impaired glucose tolerance that HbA1c misses, especially in South Asians.", "A", 700, "Blood ×2", "Same day", "Fast; 75 g glucose; sit 2 h", "If HbA1c 5.7–6.4"),
    "inflam": T("hs-CRP + homocysteine", "Blood", "blood", ["hscrp", "homocysteine"], "Vascular inflammation and methylation.", "B", 1500, "Blood", "1 day", "No infection/hard training for 2 weeks", "Yearly"),
    "thyroid": T("Thyroid panel (TSH, FT4, FT3, anti-TPO)", "Hormones", "hormones", ["tsh", "ft4", "ft3", "tpo_ab", "tg_ab", "t3_uptake", "fti"], "Under-active thyroid and autoimmune thyroiditis; T3 uptake and FTI correct total T4 for binding proteins.", "A", 1800, "Blood", "1 day", "Hold biotin 2 days", "Every 1–3 years; 6–12 months if TPO+"),
    "male_hormones": T("Male hormones (testosterone, SHBG, LH, FSH, estradiol, PSA)", "Hormones", "hormones", ["testosterone", "free_t", "shbg", "dht", "lh", "fsh", "estradiol", "psa"],
                       "Low testosterone symptoms, fertility, prostate (shared decision 55–69).", "B", 3500, "Blood", "1 day", "7–10 am draw", "If symptoms"),
    "female_hormones": T("Female hormones (AMH, FSH, LH, estradiol, progesterone, prolactin)", "Hormones", "hormones", ["amh", "fsh", "lh", "estradiol", "progesterone", "prolactin", "ohp17"],
                         "Ovarian reserve, cycle and perimenopause.", "B", 4000, "Blood", "1–2 days", "Day 2–5 of cycle", "If planning or symptoms"),
    "iron": T("Iron studies (ferritin, iron, TIBC, transferrin saturation)", "Nutrients", "micronutrients", ["ferritin", "iron", "tibc", "tsat"], "Iron deficiency (common in India) and iron overload.", "A", 1200, "Blood", "1 day", "Morning, fasted", "Yearly"),
    "vitamins": T("Vitamin D, B12, folate", "Nutrients", "micronutrients", ["vitd", "b12", "folate", "mma", "vitb6", "rbc_folate"], "Deficiencies affecting bone, nerves, energy and homocysteine; B6 and red-cell folate show longer-term status.", "A", 2500, "Blood", "1 day", "None", "Yearly"),
    "minerals": T("Minerals (RBC magnesium, zinc, copper, selenium)", "Nutrients", "micronutrients", ["rbc_mg", "zinc", "copper", "selenium"], "Micronutrient status before supplementing.", "B", 3500, "Blood", "3 days", "None", "If supplementing"),
    "omega3": T("Omega-3 index", "Nutrients", "advanced", ["omega3_index"], "Red-cell EPA+DHA; ≥8 % is associated with lower cardiac risk (Harris).", "B", 4500, "Dried blood spot", "7 days", "None", "Yearly"),
    "kidney_plus": T("Cystatin C + urine albumin (UACR)", "Blood", "advanced", ["cystatin_c", "uacr"], "Earlier kidney damage than creatinine alone (KDIGO).", "A", 2100, "Blood + urine", "1 day", "First-morning urine", "Yearly if BP/diabetes"),
    "cardiac_bio": T("NT-proBNP + hs-troponin", "Blood", "advanced", ["nt_probnp", "hs_troponin"], "Silent heart strain; prognostic in people at risk.", "B", 3500, "Blood", "1 day", "None", "If risk factors"),
    "advanced_lipid": T("NMR lipoproteins (LDL-P, GlycA)", "Blood", "advanced", ["ldl_p", "glyca", "apoa1"], "Particle number and inflammation glycoprotein.", "C", 6500, "Blood", "5 days", "Fast 12 h", "Optional"),
    "neuro_bio": T("Brain blood markers (p-tau217, NfL)", "Brain", "advanced", ["ptau217", "nfl", "abeta_ratio", "abeta42", "abeta40"], "Amyloid likelihood and neuro-axonal injury — research use in people without symptoms.", "C", 15000, "Blood", "10 days", "Genetic counselling first", "Only with clinician"),
    "g6pd": T("G6PD activity", "Blood", "immune", ["g6pd"], "Required before high-dose IV vitamin C and some medicines (haemolysis risk).", "A", 600, "Blood", "1 day", "None", "Once"),
    "autoimmune": T("Autoimmune & coeliac screen (ANA, tTG-IgA, ESR)", "Immunity", "immune", ["ana", "ttg_iga", "esr", "ccp_ab", "rf", "dsdna_ab", "iga_serum"], "Joint pain, rash, unexplained fatigue or GI symptoms.", "B", 2700, "Blood", "2 days", "Eat gluten for 6 weeks before tTG", "If symptoms"),
    "allergy": T("Allergy IgE panel", "Immunity", "immune", ["total_ige", "ige_mite", "ige_pollen", *ALLERGEN_IDS], "Rhinitis, asthma, eczema triggers.", "B", 6000, "Blood", "3 days", "No antihistamine needed", "If symptoms"),
    "food_igg": T("Food IgG 'intolerance' panel", "Immunity", None, [], "Not recommended — IgG reflects exposure, not intolerance (EAACI, AAAAI).", "D", 9000, "Blood", "7 days", "—", "Not advised"),
    "infection": T("Infection screen (HBsAg, HCV, HIV)", "Blood", None, [], "Once-in-adulthood screening (USPSTF HCV 18–79; HIV 15–65). Separate consent.", "A", 2000, "Blood", "1 day", "Consent", "Once"),
    "urine": T("Urine routine", "Urine", "urine", ["u_ph", "u_sg", "u_protein", "u_glucose", "u_blood", "u_pus", *_URINE_X], "Kidney, sugar, liver and infection screen, including dipstick and microscopy.", "A", 300, "Urine", "Same day", "Mid-stream sample", "Yearly"),
    "longevity_panel": T("Telomy longevity panel (100+ markers)", "Bundles", None, ["apob", "lpa", "hba1c", "insulin", "hscrp", "homocysteine", "vitd", "b12", "ferritin", "tsh", "cystatin_c", "omega3_index"],
                         "One draw covering heart, metabolism, inflammation, nutrients, thyroid, kidney and liver.", "B", 14999, "Blood + urine", "5 days", "Fast 10–12 h", "Twice a year"),
    "vitamins_adv": T("Extended vitamins (vitamin C, vitamin K1)", "Nutrients", "micronutrients", ["vitc", "vitk1"], "Status of vitamins that are rarely measured; vitamin C needs a protected, chilled sample.", "C", 3500, "Blood (protect from light)", "5 days", "Fast 8 h; deliver chilled", "If deficiency suspected"),
    "psa_free": T("Free PSA and % free PSA", "Cancer screening", "hormones", ["psa_free", "psa_pct_free"], "When total PSA is 4–10 ng/mL, a low free fraction raises suspicion and a high one is reassuring — helps avoid unnecessary biopsies.", "A", 900, "Blood", "1 day", "No cycling/ejaculation 48 h", "When total PSA is 4–10"),
    "thyroid_binding": T("T3 uptake + free thyroxine index", "Hormones", "hormones", ["t3_uptake", "fti"], "Separates binding-protein effects (pregnancy, oestrogen, steroids) from true thyroid disease when TSH or total T4 is off.", "B", 700, "Blood", "1 day", "Hold biotin 2 days", "When TSH is abnormal"),
    "ena_panel": T("ENA antibody panel (SS-A, SS-B, Sm, RNP)", "Immunity", "immune", [*_ENA, "ana", "dsdna_ab"], "Follow-up when ANA is positive: Sjögren's, lupus and mixed connective-tissue disease.", "B", 4500, "Blood", "3 days", "None", "Once when ANA positive"),
    "alzheimers_pkg": T("Alzheimer's & brain-health package", "Bundles", None, ["abeta_ratio", "abeta42", "abeta40", "ptau217", "nfl", "apoe", "homocysteine", "b12"],
                        "Plasma amyloid and tau with neuro-axonal injury, APOE genotype and reversible contributors (homocysteine, B12). Research-grade in people without symptoms.", "C", 28000, "Blood + saliva", "14 days", "Genetic counselling first", "Only with clinician"),
    "adv_cardiometabolic": T("Advanced cardiometabolic package", "Bundles", None, ["apob", "lpa", "nonhdl", "vldl", "ox_ldl", "ldl_p", "hscrp", "cpeptide", "fructosamine", "adiponectin", "leptin", "adma", "sdma"],
                             "Atherogenic particles, insulin output, adipokines and endothelial/kidney dimethylarginines beyond the standard lipid and glucose panel.", "B", 16000, "Blood", "5 days", "Fast 10–12 h", "If ApoB >100 or TG/HDL >3, or yearly"),
    "toxin_exposure": T("Toxin-exposure package (metals, environmental toxins, mycotoxins)", "Bundles", None,
                        ["lead", "mercury", "arsenic", "cadmium", *_METALS_X, "bpa", "mep", "glyphosate", *_ENV_X, "ochratoxin", "aflatoxin", *_MYCO_X],
                        "Broad exposure screen. Metals are clinical toxicology; environmental and mycotoxin assays are research / functional-medicine grade.", "C", 38000, "Blood + urine", "14 days", "No seafood 3 days; first-morning urine", "If exposure, optional"),
    # ---------------- gut
    "gut_shotgun": T("Gut microbiome (shotgun metagenomics)", "Gut", "gut", ["shannon", "akkermansia", "faecali", "butyrate", "fb_ratio"], "Diversity and butyrate producers.", "C", 15000, "Stool", "21 days", "No antibiotics 4 weeks", "Yearly"),
    "gut_comprehensive": T("Comprehensive stool (PCR pathogens, calprotectin, zonulin, sIgA)", "Gut", "gut", ["calprotectin", "zonulin", "siga", "hpylori", "candida", "blasto"],
                           "GI symptoms; inflammation (calprotectin is guideline-grade, zonulin is not).", "B", 18000, "Stool", "14 days", "Stop PPIs 2 weeks if possible", "If symptoms"),
    "hpylori": T("H. pylori stool antigen", "Gut", "gut", ["hpylori"], "Dyspepsia, ulcer risk.", "A", 1500, "Stool", "2 days", "No PPI 2 weeks", "If symptoms"),
    "sibo": T("SIBO breath test", "Gut", None, [], "Bloating after meals.", "C", 4500, "Breath", "Same day", "Low-fibre diet 24 h", "If symptoms"),
    # ---------------- genetics & ageing
    "genome": T("Whole-genome / longevity SNP panel", "Genetics", "genetic", ["apoe", "mthfr_c677t", "tcf7l2", "prs_cad", "prs_t2d"], "Inherited risk and polygenic scores (with counselling).", "B", 25000, "Saliva", "6 weeks", "Genetic counselling", "Once"),
    "pgx": T("Pharmacogenomics (CYP2C19, CYP2D6, SLCO1B1, VKORC1)", "Genetics", None, [], "Predicts response to clopidogrel, statins, antidepressants, warfarin (CPIC).", "A", 12000, "Saliva", "3 weeks", "None", "Once"),
    "epigenetic": T("Epigenetic age (DunedinPACE, GrimAge)", "Ageing", "bioage", ["dunedinpace", "grimage", "phenoage_lab", "horvath"], "Pace of ageing — research-grade but responsive to change.", "C", 25000, "Blood", "6 weeks", "None", "Yearly"),
    "telomere": T("Telomere length", "Ageing", "bioage", ["telomere"], "Weak individual predictor; not recommended alone.", "D", 18000, "Blood", "6 weeks", "None", "Not advised alone"),
    "proteomic": T("Proteomic organ age", "Ageing", "proteomic", ["org_heart", "org_liver", "org_brain", "org_global"], "Organ-specific ageing (Oh 2023) — research-grade.", "C", 30000, "Blood", "4 weeks", "Fast 8 h", "Yearly (optional)"),
    # ---------------- toxins & functional
    "metals": T("Heavy metals (blood/urine)", "Toxins", "metals", ["lead", "mercury", "arsenic", "cadmium", *_METALS_X], "High fish intake, ayurvedic/bhasma products, occupational exposure.", "B", 6500, "Blood or urine", "7 days", "No seafood 3 days", "If exposure"),
    "env_toxins": T("Environmental toxins (BPA, phthalates, glyphosate)", "Toxins", "toxins", ["bpa", "mep", "glyphosate", *_ENV_X], "Exposure profile (research-grade biomonitoring); actionable via containers and cosmetics.", "C", 25000, "Urine", "14 days", "First-morning urine", "Optional"),
    "mycotoxins": T("Mycotoxin panel", "Toxins", "toxins", ["ochratoxin", "aflatoxin", *_MYCO_X], "Mould exposure — limited clinical validation.", "D", 22000, "Urine", "14 days", "—", "Not routinely advised"),
    "cortisol_rhythm": T("Cortisol rhythm (4-point saliva)", "Functional", "functional", ["car", "cortisol_night"], "Flattened rhythm in stress, shift work and sleep apnoea.", "B", 4500, "Saliva ×4", "7 days", "Collect at waking, +30, afternoon, bedtime", "If fatigue/sleep issues"),
    "organic_acids": T("Organic acids (urine)", "Functional", "functional", ["ohdg", "pyroglutamate", "kynurenate", "hiaa", *OAT_IDS], "Functional-medicine metabolic snapshot (Krebs, fatty-acid, neurotransmitter, microbial and B-vitamin organic acids) — functional-medicine grade, research use.", "C", 18000, "Urine", "14 days", "First-morning urine", "Optional"),
    "dutch": T("Dried urine hormones (DUTCH)", "Functional", None, [], "Sex and adrenal hormone metabolites — limited validation vs serum.", "C", 22000, "Urine ×4", "14 days", "—", "Optional"),
    # ---------------- body & fitness
    "dexa": T("DEXA body composition + bone density", "Body", "bodycomp", ["body_fat_pct", "vat_area", "almi", "bmd_spine_t", "bmd_hip_t"], "Visceral fat, muscle and osteoporosis (USPSTF women ≥65).", "A", 3500, "Scan (low dose)", "Same day", "Morning, fasted, no metal", "Yearly"),
    "bca": T("Body composition analysis (bioimpedance)", "Body", "bodycomp", ["bca_body_fat", "smm", "visceral_level", "phase_angle"], "Quick, cheap tracking between DEXA scans.", "C", 800, "Device", "Immediate", "Fasted, hydrated", "Monthly"),
    "cpet": T("VO2 max (cardiopulmonary exercise test)", "Fitness", "fitness", ["vo2max_lab", "vt1_hr", "vt2_hr", "hrr_1min"], "The strongest modifiable predictor of all-cause mortality (Mandsager 2018).", "B", 6000, "Treadmill/cycle", "Same day", "No hard training 48 h", "Yearly"),
    "rmr": T("Resting metabolic rate (indirect calorimetry)", "Fitness", None, [], "Personal calorie baseline.", "C", 3000, "Breath", "Same day", "Fasted, rested", "Optional"),
    "function": T("Strength & function (grip, gait, sit-to-stand, balance)", "Fitness", "fitness", ["grip", "gait_speed", "sts_30s", "balance"], "Sarcopenia and frailty (EWGSOP2).", "A", 0, "In clinic", "Immediate", "None", "Yearly"),
    # ---------------- heart & vessels
    "ecg": T("12-lead ECG", "Heart", "cardio", ["qtc", "ecg_hr"], "Rhythm, conduction, QT.", "A", 400, "ECG", "Immediate", "None", "Baseline, then if symptoms"),
    "holter": T("24–48 h Holter / patch ECG", "Heart", "cardio", ["afib_burden", "pvc_burden"], "Palpitations; silent atrial fibrillation.", "A", 2500, "Wearable ECG", "2 days", "Normal day", "If symptoms"),
    "abpm": T("24-h ambulatory blood pressure", "Heart", "cardio", ["abpm_day_sbp", "abpm_day_dbp", "abpm_dip"], "Confirms hypertension; finds masked hypertension and non-dipping (ESC/ESH 2023).", "A", 2500, "Cuff, 24 h", "1 day", "Log sleep/wake", "If clinic/home BP borderline"),
    "echo": T("Echocardiogram", "Heart", "cardio", ["lvef", "e_e_ratio", "lavi"], "Heart structure, pump and relaxation.", "A", 2500, "Ultrasound", "Same day", "None", "If symptoms or murmur"),
    "abi_pwv": T("Arterial stiffness (PWV) + ankle-brachial index", "Heart", "cardio", ["pwv", "abi"], "Vascular ageing and leg-artery disease.", "B", 3000, "Cuffs", "Same day", "No caffeine 3 h", "Every 2–3 years"),
    "cimt": T("Carotid ultrasound (IMT + plaque)", "Heart", "screening", ["cimt", "carotid_plaque"], "Subclinical atherosclerosis.", "B", 3000, "Ultrasound", "Same day", "None", "Every 3–5 years"),
    "cac": T("Coronary calcium score (CT)", "Heart", "ct", ["cac", "cac_pct"], "Reclassifies intermediate risk; zero is powerfully reassuring (ACC/AHA).", "A", 4000, "CT (low dose)", "Same day", "None", "Once; repeat in 3–5 y"),
    "ccta": T("CT coronary angiography (CCTA)", "Heart", "ct", ["cad_rads", "plaque_vol"], "Soft plaque and stenosis; for symptoms or high risk.", "A", 12000, "CT + contrast", "Same day", "Kidney test first", "If indicated"),
    # ---------------- imaging & organ scans
    "fibroscan": T("FibroScan (liver fat + stiffness)", "Liver", "screening", ["lsm", "cap"], "Fatty liver and fibrosis without biopsy (EASL).", "A", 3000, "Ultrasound", "Immediate", "Fast 3 h", "If FIB-4 ≥1.3 or fatty liver"),
    "liver_mri": T("Liver MRI-PDFF", "Liver", "mri", ["liver_pdff"], "Most accurate liver-fat measure.", "B", 9000, "MRI", "1 day", "Fast 4 h", "Optional"),
    "brain_mri": T("Brain MRI with volumetrics", "Brain", "mri", ["wmh_fazekas", "brain_age_gap", "hippocampal_pct"], "Small-vessel disease and brain volume.", "C", 7000, "MRI", "2 days", "No metal", "Only if indicated"),
    "wbmri": T("Whole-body MRI", "Imaging", "mri", ["wbmri_findings"], "Broad screen; high rate of incidental findings — counselling first.", "C", 35000, "MRI", "3 days", "No metal", "Optional"),
    "usg_abd": T("Ultrasound abdomen", "Imaging", None, [], "Liver, gall-bladder, kidneys.", "B", 1500, "Ultrasound", "Same day", "Fast 6 h", "If symptoms"),
    "thyroid_usg": T("Thyroid ultrasound", "Imaging", None, [], "Only for a palpable nodule — not for screening (USPSTF D).", "D", 1500, "Ultrasound", "Same day", "None", "Not for screening"),
    # ---------------- lungs, sleep, brain function, senses
    "spirometry": T("Spirometry + FeNO", "Lungs", "lung", ["fev1_pct", "fvc_pct", "fev1_fvc", "feno"], "COPD/asthma; smokers and breathless people.", "A", 1700, "Breath", "Same day", "No bronchodilator 4–6 h", "If symptoms or smoker"),
    "ldct": T("Low-dose CT lung", "Lungs", None, [], "Lung-cancer screening, 50–80 y with ≥20 pack-years (USPSTF B).", "A", 6000, "CT (low dose)", "1 day", "None", "Yearly if eligible"),
    "hsat": T("Home sleep apnoea test", "Sleep", "screening", ["ahi", "odi", "min_spo2"], "Snoring, unrefreshing sleep, resistant BP.", "A", 6000, "Home device, 1 night", "3 days", "Normal night", "If symptoms"),
    "psg": T("Polysomnography (in-lab)", "Sleep", "screening", ["ahi"], "Gold standard; when home test is negative but suspicion is high.", "A", 15000, "Lab, 1 night", "5 days", "—", "If indicated"),
    "cognition": T("Cognitive screen (MoCA + digital battery)", "Brain", None, [], "Baseline cognition; repeat if concerns.", "B", 0, "In clinic", "Immediate", "Rested", "Baseline at 50+"),
    "audiometry": T("Hearing test (audiometry)", "Senses", None, [], "Hearing loss is the largest modifiable dementia risk (Lancet Commission 2024).", "A", 1000, "Booth", "Same day", "None", "Every 3 y from 50"),
    "eye": T("Eye exam + retinal imaging", "Senses", None, [], "Glaucoma, diabetic retinopathy; retinal age research.", "A", 1500, "Imaging", "Same day", "No contacts", "Every 2 y; yearly if diabetic"),
    "dental": T("Dental & periodontal check", "Senses", None, [], "Periodontitis links with cardiovascular and metabolic disease.", "B", 800, "Clinic", "Same day", "None", "Every 6 months"),
    # ---------------- cancer screening
    "fit": T("FIT (faecal immunochemical test)", "Cancer screening", "screening", ["fit"], "Colorectal cancer, 45–75 (USPSTF A/B).", "A", 900, "Stool", "2 days", "None", "Yearly"),
    "colonoscopy": T("Colonoscopy", "Cancer screening", None, [], "Colorectal cancer, 45–75; every 10 y if normal.", "A", 12000, "Procedure", "Same day", "Bowel prep", "Every 10 years"),
    "psa": T("PSA", "Cancer screening", "hormones", ["psa"], "Prostate cancer, 55–69 — shared decision (USPSTF C).", "B", 800, "Blood", "1 day", "No cycling/ejaculation 48 h", "Every 2 y if chosen"),
    "mammogram": T("Mammogram", "Cancer screening", None, [], "Breast cancer, women 40–74 every 2 y (USPSTF 2024 B).", "A", 2500, "X-ray", "Same day", "No deodorant", "Every 2 years"),
    "cervical": T("HPV test / Pap smear", "Cancer screening", None, [], "Cervical cancer, 21–65 (USPSTF A).", "A", 2500, "Swab", "5 days", "Not during period", "Every 3–5 years"),
    "oral": T("Oral cancer visual exam", "Cancer screening", None, [], "High oral-cancer burden in India; tobacco/areca users.", "B", 0, "Clinic", "Immediate", "None", "Yearly if tobacco"),
    "mced": T("Multi-cancer early detection (cfDNA)", "Cancer screening", "screening", ["mced"], "Not a replacement for guideline screening; limited availability and evidence pending (NHS-Galleri).", "C", 75000, "Blood", "3 weeks", "Counselling first", "Optional"),
    # ---------------- continuous
    "cgm": T("Continuous glucose monitor (14 days)", "Metabolic", "cgm", ["cgm_mean", "cgm_tir", "cgm_cv", "gmi", "cgm_peak"], "Your own glucose response to foods, sleep and stress.", "B", 5000, "Sensor", "14 days", "Log meals in Telomy", "Every 6 months if prediabetic"),
}


def _have() -> dict[str, str]:
    """marker_id → last collected date in the Vault."""
    return {mid: r["collected_on"] for mid, r in engine.latest_values().items()}


# Bundles overlap with standard tests (ApoB, ANA, APOE, lead...), so "have I done this?" is judged on the markers that only
# the bundle adds - otherwise one old ApoB would mark the whole package "current" and hide it from recommend().
_STATUS_MARKERS = {
    "alzheimers_pkg": ["abeta_ratio", "abeta42", "abeta40", "ptau217", "nfl"],
    "adv_cardiometabolic": ["ox_ldl", "cpeptide", "fructosamine", "adiponectin", "leptin", "adma", "sdma"],
    "ena_panel": _ENA,
    "toxin_exposure": [*_METALS_X, *_ENV_X, *_MYCO_X],
}


def status(tid: str, have: dict, today: date) -> dict:
    t = TESTS[tid]
    mk = _STATUS_MARKERS.get(tid, t["markers"])
    got = [m for m in mk if m in have]
    if not mk:
        return {"state": "unknown", "last": None}
    if not got:
        return {"state": "never", "last": None}
    last = max(have[m] for m in got)
    age = (today - date.fromisoformat(last)).days
    return {"state": "current" if age < 365 else "due", "last": last, "coverage": round(len(got) / len(mk), 2)}


def recommend(pid: int = 1) -> list[dict]:
    """Personalised next tests: guideline screening by age/sex, risk-based follow-ups, and gaps — each with a reason."""
    today = date.fromisoformat(engine.last_signal_day() or date.today().isoformat())
    prof = engine.profile()
    age, sex = engine.age_on() or 40, prof.get("sex", "male")
    have = _have()
    L = engine.latest_values()
    v = lambda m: (L.get(m) or {}).get("value_num")  # noqa: E731
    recs: list[tuple[str, str, str]] = []  # (test, priority, reason)
    # guideline screening
    if age >= 35:
        recs.append(("glycaemia", "routine", "ADA: screen for diabetes from 35 (South Asians at lower BMI)."))
    if "lpa" not in have:
        recs.append(("lpa", "high", "Lp(a) should be measured once in every adult (ESC/EAS 2022)."))
    if age >= 45:
        recs.append(("fit", "high", "Colorectal screening from 45 (USPSTF)."))
    if sex == "female" and age >= 40:
        recs.append(("mammogram", "high", "Breast screening every 2 years from 40 (USPSTF 2024)."))
    if sex == "female" and 21 <= age <= 65:
        recs.append(("cervical", "routine", "Cervical screening 21–65 (USPSTF)."))
    if sex == "male" and 55 <= age <= 69:
        recs.append(("psa", "discuss", "PSA screening is a shared decision at 55–69."))
    if prof.get("smoker"):
        recs.append(("spirometry", "high", "Smoker: spirometry; low-dose CT lung from 50 with ≥20 pack-years."))
    recs.append(("infection", "routine", "Once-in-adulthood HCV/HIV/HBV screening (USPSTF; separate consent)."))
    recs.append(("dental", "routine", "Dental review every 6 months."))
    # risk-based from the Vault
    if (v("hba1c") or 0) >= 5.7:
        recs.append(("cgm", "high", f"HbA1c {v('hba1c')}% — a 14-day CGM shows which meals and habits drive it."))
        recs.append(("ogtt", "routine", "Prediabetic HbA1c: an OGTT catches post-load glucose that HbA1c can miss in South Asians."))
    if (v("apob") or 0) > 100 or (v("cac") or 0) > 0:
        recs.append(("apob", "high", f"ApoB {v('apob')} / CAC {v('cac')}: recheck ApoB 12 weeks after any change."))
        recs.append(("pgx", "discuss", "Before starting a statin, SLCO1B1 tells you your myopathy risk (CPIC guideline)."))
    if (v("abpm_day_sbp") or 0) >= 135:
        recs.append(("kidney_plus", "high", "Hypertension on ABPM: KDIGO advises UACR + cystatin C for kidney damage."))
    if (v("liver_pdff") or 0) >= 5 or (v("cap") or 0) >= 248:
        recs.append(("fibroscan", "routine", "Fatty liver: FibroScan every 1–2 years to watch stiffness."))
    if (v("ahi") or 0) >= 5:
        recs.append(("abpm", "routine", "Sleep apnoea and BP are linked; repeat ABPM after apnoea treatment."))
    if (v("tpo_ab") or 0) > 34:
        recs.append(("thyroid", "routine", "Anti-TPO positive: TSH every 6–12 months."))
    if (v("vitd") or 99) < 30:
        recs.append(("vitamins", "routine", f"Vitamin D {v('vitd')} ng/mL: recheck 3 months after supplementing."))
    if (v("homocysteine") or 0) > 12:
        recs.append(("vitamins", "routine", "Raised homocysteine: recheck folate, B12 and MMA after methylated B vitamins."))
    # 2026-10-29 additions: amyloid, advanced cardiometabolic, ENA, thyroid-binding, prostate
    apoe_row = L.get("apoe")
    apoe_e4 = bool(apoe_row and "ε4" in str(apoe_row.get("value_text") or ""))
    if apoe_e4 or age >= 65:
        recs.append(("alzheimers_pkg", "discuss", ("APOE ε4 carrier" if apoe_e4 else f"Age {int(age)}") +
                     ": plasma amyloid-β 42/40 with p-tau217 can show amyloid pathology years early (research-grade; clinician and counselling first)."))
    tg_hdl = (v("tg") / v("hdl")) if v("tg") and v("hdl") else None
    if (v("apob") or 0) > 100 or (tg_hdl or 0) > 3:
        recs.append(("adv_cardiometabolic", "routine", f"ApoB {v('apob')} / TG:HDL {round(tg_hdl, 1) if tg_hdl else '—'}: particle number, insulin output and endothelial markers refine the risk."))
    if (L.get("ana") or {}).get("status") == "detected":
        recs.append(("ena_panel", "high", "ANA positive: an ENA panel (SS-A, SS-B, Sm, RNP) with anti-dsDNA identifies the specific autoimmune pattern."))
    if 4.0 <= (v("psa") or 0) <= 10.0 and sex == "male":
        recs.append(("psa_free", "high", f"Total PSA {v('psa')} ng/mL is in the 4–10 range: % free PSA helps decide whether a biopsy is needed."))
    if (v("tsh") or 0) > 4.0 and "t3_uptake" not in have:
        recs.append(("thyroid_binding", "routine", "Abnormal TSH: T3 uptake / free thyroxine index separates binding-protein effects from true thyroid disease."))
    if any((L.get(m) or {}).get("status") == "out_of_range" for m in ("lead", "mercury", "arsenic", "cadmium")):
        recs.append(("toxin_exposure", "routine", "A heavy metal is out of range: the wider metals and exposure screen helps find the source."))
    if "g6pd" not in have:
        recs.append(("g6pd", "routine", "Needed before high-dose IV vitamin C at the centre."))
    # gaps in the Vault for the six streams
    for tid, why in (("cpet", "VO2 max is the strongest modifiable longevity predictor."), ("dexa", "Visceral fat, muscle and bone in one scan."),
                     ("abi_pwv", "Vascular age in 10 minutes.")):
        if status(tid, have, today)["state"] in ("never", "due"):
            recs.append((tid, "routine", why))
    seen, out = set(), []
    order = {"high": 0, "routine": 1, "discuss": 2}
    for tid, pr, why in sorted(recs, key=lambda x: order[x[1]]):
        if tid in seen:
            continue
        seen.add(tid)
        st = status(tid, have, today)
        if st["state"] == "current" and (pr != "high" or (today - date.fromisoformat(st["last"])).days < 60):
            continue
        t = TESTS[tid]
        out.append({"id": tid, "name": t["name"], "category": t["category"], "priority": pr, "reason": why, "evidence": t["evidence"],
                    "price": t["price"], "prep": t["prep"], "status": st})
    return out


def catalogue() -> list[dict]:
    today = date.fromisoformat(engine.last_signal_day() or date.today().isoformat())
    have = _have()
    return [{"id": k, **{x: t[x] for x in ("name", "category", "why", "evidence", "price", "sample", "tat", "prep", "freq")},
             "markers": [{"id": m, "name": MARKERS[m][0]} for m in t["markers"] if m in MARKERS], "status": status(k, have, today)}
            for k, t in TESTS.items()]


def book(test_id: str, day: str, pid: int = 1) -> dict:
    if test_id not in TESTS:
        raise ValueError("Unknown test")
    t = TESTS[test_id]
    if t["evidence"] == "D":
        raise PermissionError(f"{t['name']}: not recommended — {t['why']}")
    db.exec_("INSERT OR IGNORE INTO services (id, name, minutes, price, capacity, category, evidence, targets) VALUES (?,?,?,?,?,?,?,?)",
             (f"test:{test_id}", t["name"], 20, t["price"], 6, "Diagnostics", t["evidence"], db.j(t["markers"])))
    bid = db.exec_("INSERT INTO bookings (patient_id, service_id, ts, status, price) VALUES (?,?,?,?,?)",
                   (pid, f"test:{test_id}", f"{day}T08:00:00", "booked", t["price"]))
    return {"id": bid, "message": f"{t['name']} booked for {day} 08:00 at the centre (test mode, ₹{t['price']:,} not charged). Prep: {t['prep']}."}
