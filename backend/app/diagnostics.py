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
             "Anaemia, infection and blood-cell health; RDW and lymphocytes feed biological age.", "A", 350, "Blood", "Same day", "None", "Yearly"),
    "cmp": T("Metabolic panel (kidney, liver, electrolytes)", "Blood", "blood", ["creatinine", "egfr", "alt", "ast", "ggt", "albumin", "alp", "sodium", "potassium", "calcium"],
             "Kidney and liver function, electrolytes.", "A", 799, "Blood", "Same day", "Fast 8 h", "Yearly"),
    "lipid": T("Lipid profile", "Blood", "blood", ["chol_total", "ldl", "hdl", "tg", "nonhdl", "vldl"], "Core cardiovascular risk input (PREVENT, PCE); non-HDL is the secondary target when triglycerides are high.", "A", 450, "Blood", "Same day", "Fast 10–12 h", "Every 1–5 years"),
    "apob": T("Apolipoprotein B", "Blood", "blood", ["apob"], "Counts every atherogenic particle — better than LDL when triglycerides are high (ESC/EAS).", "A", 750, "Blood", "1 day", "None", "Yearly if raised"),
    "lpa": T("Lipoprotein(a)", "Blood", "blood", ["lpa"], "Inherited risk factor; measure once in a lifetime (ESC/EAS 2022 consensus).", "A", 1100, "Blood", "2 days", "None", "Once"),
    "glycaemia": T("HbA1c + fasting glucose + insulin (HOMA-IR)", "Blood", "blood", ["hba1c", "glucose", "insulin", "homa_ir", "cpeptide", "fructosamine"],
                   "Diabetes screening (ADA) and early insulin resistance; C-peptide separates insulin resistance from low insulin output, fructosamine tracks the past 2–3 weeks.", "A", 1199, "Blood", "Same day", "Fast 8–12 h", "Yearly from 35 (ADA)"),
    "ogtt": T("Oral glucose tolerance test (2-h)", "Blood", "blood", ["glucose"], "Catches impaired glucose tolerance that HbA1c misses, especially in South Asians.", "A", 600, "Blood ×2", "Same day", "Fast; 75 g glucose; sit 2 h", "If HbA1c 5.7–6.4"),
    "inflam": T("hs-CRP + homocysteine", "Blood", "blood", ["hscrp", "homocysteine"], "Vascular inflammation and methylation.", "B", 1399, "Blood", "1 day", "No infection/hard training for 2 weeks", "Yearly"),
    "thyroid": T("Thyroid panel (TSH, FT4, FT3, anti-TPO)", "Hormones", "hormones", ["tsh", "ft4", "ft3", "tpo_ab", "tg_ab", "t3_uptake", "fti"], "Under-active thyroid and autoimmune thyroiditis; T3 uptake and FTI correct total T4 for binding proteins.", "A", 1399, "Blood", "1 day", "Hold biotin 2 days", "Every 1–3 years; 6–12 months if TPO+"),
    "male_hormones": T("Male hormones (testosterone, SHBG, LH, FSH, estradiol, PSA)", "Hormones", "hormones", ["testosterone", "free_t", "shbg", "dht", "lh", "fsh", "estradiol", "psa"],
                       "Low testosterone symptoms, fertility, prostate (shared decision 55–69).", "B", 2999, "Blood", "1 day", "7–10 am draw", "If symptoms"),
    "female_hormones": T("Female hormones (AMH, FSH, LH, estradiol, progesterone, prolactin)", "Hormones", "hormones", ["amh", "fsh", "lh", "estradiol", "progesterone", "prolactin", "ohp17"],
                         "Ovarian reserve, cycle and perimenopause.", "B", 3499, "Blood", "1–2 days", "Day 2–5 of cycle", "If planning or symptoms"),
    "iron": T("Iron studies (ferritin, iron, TIBC, transferrin saturation)", "Nutrients", "micronutrients", ["ferritin", "iron", "tibc", "tsat"], "Iron deficiency (common in India) and iron overload.", "A", 799, "Blood", "1 day", "Morning, fasted", "Yearly"),
    "vitamins": T("Vitamin D, B12, folate", "Nutrients", "micronutrients", ["vitd", "b12", "folate", "mma", "vitb6", "rbc_folate"], "Deficiencies affecting bone, nerves, energy and homocysteine; B6 and red-cell folate show longer-term status.", "A", 2199, "Blood", "1 day", "None", "Yearly"),
    "minerals": T("Minerals (RBC magnesium, zinc, copper, selenium)", "Nutrients", "micronutrients", ["rbc_mg", "zinc", "copper", "selenium"], "Micronutrient status before supplementing.", "B", 2999, "Blood", "3 days", "None", "If supplementing"),
    "omega3": T("Omega-3 index", "Nutrients", "advanced", ["omega3_index"], "Red-cell EPA+DHA; ≥8 % is associated with lower cardiac risk (Harris).", "B", 3999, "Dried blood spot", "7 days", "None", "Yearly"),
    "kidney_plus": T("Cystatin C + urine albumin (UACR)", "Blood", "advanced", ["cystatin_c", "uacr"], "Earlier kidney damage than creatinine alone (KDIGO).", "A", 1699, "Blood + urine", "1 day", "First-morning urine", "Yearly if BP/diabetes"),
    "cardiac_bio": T("NT-proBNP + hs-troponin", "Blood", "advanced", ["nt_probnp", "hs_troponin"], "Silent heart strain; prognostic in people at risk.", "B", 2800, "Blood", "1 day", "None", "If risk factors"),
    "advanced_lipid": T("NMR lipoproteins (LDL-P, GlycA)", "Blood", "advanced", ["ldl_p", "glyca", "apoa1"], "Particle number and inflammation glycoprotein.", "C", 5999, "Blood", "5 days", "Fast 12 h", "Optional"),
    "neuro_bio": T("Brain blood markers (p-tau217, NfL)", "Brain", "advanced", ["ptau217", "nfl", "abeta_ratio", "abeta42", "abeta40"], "Amyloid likelihood and neuro-axonal injury — research use in people without symptoms.", "C", 14999, "Blood", "10 days", "Genetic counselling first", "Only with clinician"),
    "g6pd": T("G6PD activity", "Blood", "immune", ["g6pd"], "Required before high-dose IV vitamin C and some medicines (haemolysis risk).", "A", 550, "Blood", "1 day", "None", "Once"),
    "autoimmune": T("Autoimmune & coeliac screen (ANA, tTG-IgA, ESR)", "Immunity", "immune", ["ana", "ttg_iga", "esr", "ccp_ab", "rf", "dsdna_ab", "iga_serum"], "Joint pain, rash, unexplained fatigue or GI symptoms.", "B", 2399, "Blood", "2 days", "Eat gluten for 6 weeks before tTG", "If symptoms"),
    "allergy": T("Allergy IgE panel", "Immunity", "immune", ["total_ige", "ige_mite", "ige_pollen", *ALLERGEN_IDS], "Rhinitis, asthma, eczema triggers.", "B", 5499, "Blood", "3 days", "No antihistamine needed", "If symptoms"),
    "food_igg": T("Food IgG 'intolerance' panel", "Immunity", None, [], "Not recommended — IgG reflects exposure, not intolerance (EAACI, AAAAI).", "D", 9000, "Blood", "7 days", "—", "Not advised"),
    "infection": T("Infection screen (HBsAg, HCV, HIV)", "Blood", None, [], "Once-in-adulthood screening (USPSTF HCV 18–79; HIV 15–65). Separate consent.", "A", 1199, "Blood", "1 day", "Consent", "Once"),
    "urine": T("Urine routine", "Urine", "urine", ["u_ph", "u_sg", "u_protein", "u_glucose", "u_blood", "u_pus", *_URINE_X], "Kidney, sugar, liver and infection screen, including dipstick and microscopy.", "A", 250, "Urine", "Same day", "Mid-stream sample", "Yearly"),
    "longevity_panel": T("Telomy longevity panel (100+ markers)", "Bundles", None, ["apob", "lpa", "hba1c", "insulin", "hscrp", "homocysteine", "vitd", "b12", "ferritin", "tsh", "cystatin_c", "omega3_index"],
                         "One draw covering heart, metabolism, inflammation, nutrients, thyroid, kidney and liver.", "B", 9999, "Blood + urine", "5 days", "Fast 10–12 h", "Twice a year"),
    "vitamins_adv": T("Extended vitamins (vitamin C, vitamin K1)", "Nutrients", "micronutrients", ["vitc", "vitk1"], "Status of vitamins that are rarely measured; vitamin C needs a protected, chilled sample.", "C", 2999, "Blood (protect from light)", "5 days", "Fast 8 h; deliver chilled", "If deficiency suspected"),
    "psa_free": T("Free PSA and % free PSA", "Cancer screening", "hormones", ["psa_free", "psa_pct_free"], "When total PSA is 4–10 ng/mL, a low free fraction raises suspicion and a high one is reassuring — helps avoid unnecessary biopsies.", "A", 799, "Blood", "1 day", "No cycling/ejaculation 48 h", "When total PSA is 4–10"),
    "thyroid_binding": T("T3 uptake + free thyroxine index", "Hormones", "hormones", ["t3_uptake", "fti"], "Separates binding-protein effects (pregnancy, oestrogen, steroids) from true thyroid disease when TSH or total T4 is off.", "B", 599, "Blood", "1 day", "Hold biotin 2 days", "When TSH is abnormal"),
    "ena_panel": T("ENA antibody panel (SS-A, SS-B, Sm, RNP)", "Immunity", "immune", [*_ENA, "ana", "dsdna_ab"], "Follow-up when ANA is positive: Sjögren's, lupus and mixed connective-tissue disease.", "B", 3799, "Blood", "3 days", "None", "Once when ANA positive"),
    "alzheimers_pkg": T("Alzheimer's & brain-health package", "Bundles", None, ["abeta_ratio", "abeta42", "abeta40", "ptau217", "nfl", "apoe", "homocysteine", "b12"],
                        "Plasma amyloid and tau with neuro-axonal injury, APOE genotype and reversible contributors (homocysteine, B12). Research-grade in people without symptoms.", "C", 23999, "Blood + saliva", "14 days", "Genetic counselling first", "Only with clinician"),
    "adv_cardiometabolic": T("Advanced cardiometabolic package", "Bundles", None, ["apob", "lpa", "nonhdl", "vldl", "ox_ldl", "ldl_p", "hscrp", "cpeptide", "fructosamine", "adiponectin", "leptin", "adma", "sdma"],
                             "Atherogenic particles, insulin output, adipokines and endothelial/kidney dimethylarginines beyond the standard lipid and glucose panel.", "B", 12999, "Blood", "5 days", "Fast 10–12 h", "If ApoB >100 or TG/HDL >3, or yearly"),
    "toxin_exposure": T("Toxin-exposure package (metals, environmental toxins, mycotoxins)", "Bundles", None,
                        ["lead", "mercury", "arsenic", "cadmium", *_METALS_X, "bpa", "mep", "glyphosate", *_ENV_X, "ochratoxin", "aflatoxin", *_MYCO_X],
                        "Broad exposure screen. Metals are clinical toxicology; environmental and mycotoxin assays are research / functional-medicine grade.", "C", 29999, "Blood + urine", "14 days", "No seafood 3 days; first-morning urine", "If exposure, optional"),
    # ---------------- gut
    "gut_shotgun": T("Gut microbiome (shotgun metagenomics)", "Gut", "gut", ["shannon", "akkermansia", "faecali", "butyrate", "fb_ratio"], "Diversity and butyrate producers.", "C", 9999, "Stool", "21 days", "No antibiotics 4 weeks", "Yearly"),
    "gut_comprehensive": T("Comprehensive stool (PCR pathogens, calprotectin, zonulin, sIgA)", "Gut", "gut", ["calprotectin", "zonulin", "siga", "hpylori", "candida", "blasto"],
                           "GI symptoms; inflammation (calprotectin is guideline-grade, zonulin is not).", "B", 12999, "Stool", "14 days", "Stop PPIs 2 weeks if possible", "If symptoms"),
    "hpylori": T("H. pylori stool antigen", "Gut", "gut", ["hpylori"], "Dyspepsia, ulcer risk.", "A", 1299, "Stool", "2 days", "No PPI 2 weeks", "If symptoms"),
    "sibo": T("SIBO breath test", "Gut", None, [], "Bloating after meals.", "C", 3999, "Breath", "Same day", "Low-fibre diet 24 h", "If symptoms"),
    # ---------------- genetics & ageing
    "genome": T("Whole-genome / longevity SNP panel", "Genetics", "genetic", ["apoe", "mthfr_c677t", "tcf7l2", "prs_cad", "prs_t2d"], "Inherited risk and polygenic scores (with counselling).", "B", 14999, "Saliva", "6 weeks", "Genetic counselling", "Once"),
    "pgx": T("Pharmacogenomics (CYP2C19, CYP2D6, SLCO1B1, VKORC1)", "Genetics", None, [], "Predicts response to clopidogrel, statins, antidepressants, warfarin (CPIC).", "A", 9999, "Saliva", "3 weeks", "None", "Once"),
    "epigenetic": T("Epigenetic age (DunedinPACE, GrimAge)", "Ageing", "bioage", ["dunedinpace", "grimage", "phenoage_lab", "horvath"], "Pace of ageing — research-grade but responsive to change.", "C", 17999, "Blood", "6 weeks", "None", "Yearly"),
    "telomere": T("Telomere length", "Ageing", "bioage", ["telomere"], "Weak individual predictor; not recommended alone.", "D", 11999, "Blood", "6 weeks", "None", "Not advised alone"),
    "proteomic": T("Proteomic organ age", "Ageing", "proteomic", ["org_heart", "org_liver", "org_brain", "org_global"], "Organ-specific ageing (Oh 2023) — research-grade.", "C", 27999, "Blood", "4 weeks", "Fast 8 h", "Yearly (optional)"),
    # ---------------- toxins & functional
    "metals": T("Heavy metals (blood/urine)", "Toxins", "metals", ["lead", "mercury", "arsenic", "cadmium", *_METALS_X], "High fish intake, ayurvedic/bhasma products, occupational exposure.", "B", 5499, "Blood or urine", "7 days", "No seafood 3 days", "If exposure"),
    "env_toxins": T("Environmental toxins (BPA, phthalates, glyphosate)", "Toxins", "toxins", ["bpa", "mep", "glyphosate", *_ENV_X], "Exposure profile (research-grade biomonitoring); actionable via containers and cosmetics.", "C", 21999, "Urine", "14 days", "First-morning urine", "Optional"),
    "mycotoxins": T("Mycotoxin panel", "Toxins", "toxins", ["ochratoxin", "aflatoxin", *_MYCO_X], "Mould exposure — limited clinical validation.", "D", 19999, "Urine", "14 days", "—", "Not routinely advised"),
    "cortisol_rhythm": T("Cortisol rhythm (4-point saliva)", "Functional", "functional", ["car", "cortisol_night"], "Flattened rhythm in stress, shift work and sleep apnoea.", "B", 3999, "Saliva ×4", "7 days", "Collect at waking, +30, afternoon, bedtime", "If fatigue/sleep issues"),
    "organic_acids": T("Organic acids (urine)", "Functional", "functional", ["ohdg", "pyroglutamate", "kynurenate", "hiaa", *OAT_IDS], "Functional-medicine metabolic snapshot (Krebs, fatty-acid, neurotransmitter, microbial and B-vitamin organic acids) — functional-medicine grade, research use.", "C", 14999, "Urine", "14 days", "First-morning urine", "Optional"),
    "dutch": T("Dried urine hormones (DUTCH)", "Functional", None, [], "Sex and adrenal hormone metabolites — limited validation vs serum.", "C", 19999, "Urine ×4", "14 days", "—", "Optional"),
    # ---------------- body & fitness
    "dexa": T("DEXA body composition + bone density", "Body", "bodycomp", ["body_fat_pct", "vat_area", "almi", "bmd_spine_t", "bmd_hip_t"], "Visceral fat, muscle and osteoporosis (USPSTF women ≥65).", "A", 2799, "Scan (low dose)", "Same day", "Morning, fasted, no metal", "Yearly"),
    "bca": T("Body composition analysis (bioimpedance)", "Body", "bodycomp", ["bca_body_fat", "smm", "visceral_level", "phase_angle"], "Quick, cheap tracking between DEXA scans.", "C", 599, "Device", "Immediate", "Fasted, hydrated", "Monthly"),
    "cpet": T("VO2 max (cardiopulmonary exercise test)", "Fitness", "fitness", ["vo2max_lab", "vt1_hr", "vt2_hr", "hrr_1min"], "The strongest modifiable predictor of all-cause mortality (Mandsager 2018).", "B", 5499, "Treadmill/cycle", "Same day", "No hard training 48 h", "Yearly"),
    "rmr": T("Resting metabolic rate (indirect calorimetry)", "Fitness", None, [], "Personal calorie baseline.", "C", 2799, "Breath", "Same day", "Fasted, rested", "Optional"),
    "function": T("Strength & function (grip, gait, sit-to-stand, balance)", "Fitness", "fitness", ["grip", "gait_speed", "sts_30s", "balance"], "Sarcopenia and frailty (EWGSOP2).", "A", 0, "In clinic", "Immediate", "None", "Yearly"),
    # ---------------- heart & vessels
    "ecg": T("12-lead ECG", "Heart", "cardio", ["qtc", "ecg_hr"], "Rhythm, conduction, QT.", "A", 350, "ECG", "Immediate", "None", "Baseline, then if symptoms"),
    "holter": T("24–48 h Holter / patch ECG", "Heart", "cardio", ["afib_burden", "pvc_burden"], "Palpitations; silent atrial fibrillation.", "A", 2499, "Wearable ECG", "2 days", "Normal day", "If symptoms"),
    "abpm": T("24-h ambulatory blood pressure", "Heart", "cardio", ["abpm_day_sbp", "abpm_day_dbp", "abpm_dip"], "Confirms hypertension; finds masked hypertension and non-dipping (ESC/ESH 2023).", "A", 2199, "Cuff, 24 h", "1 day", "Log sleep/wake", "If clinic/home BP borderline"),
    "echo": T("Echocardiogram", "Heart", "cardio", ["lvef", "e_e_ratio", "lavi"], "Heart structure, pump and relaxation.", "A", 2199, "Ultrasound", "Same day", "None", "If symptoms or murmur"),
    "abi_pwv": T("Arterial stiffness (PWV) + ankle-brachial index", "Heart", "cardio", ["pwv", "abi"], "Vascular ageing and leg-artery disease.", "B", 2799, "Cuffs", "Same day", "No caffeine 3 h", "Every 2–3 years"),
    "cimt": T("Carotid ultrasound (IMT + plaque)", "Heart", "screening", ["cimt", "carotid_plaque"], "Subclinical atherosclerosis.", "B", 2499, "Ultrasound", "Same day", "None", "Every 3–5 years"),
    "cac": T("Coronary calcium score (CT)", "Heart", "ct", ["cac", "cac_pct"], "Reclassifies intermediate risk; zero is powerfully reassuring (ACC/AHA).", "A", 2999, "CT (low dose)", "Same day", "None", "Once; repeat in 3–5 y"),
    "ccta": T("CT coronary angiography (CCTA)", "Heart", "ct", ["cad_rads", "plaque_vol"], "Soft plaque and stenosis; for symptoms or high risk.", "A", 10999, "CT + contrast", "Same day", "Kidney test first", "If indicated"),
    # ---------------- imaging & organ scans
    "fibroscan": T("FibroScan (liver fat + stiffness)", "Liver", "screening", ["lsm", "cap"], "Fatty liver and fibrosis without biopsy (EASL).", "A", 2799, "Ultrasound", "Immediate", "Fast 3 h", "If FIB-4 ≥1.3 or fatty liver"),
    "liver_mri": T("Liver MRI-PDFF", "Liver", "mri", ["liver_pdff"], "Most accurate liver-fat measure.", "B", 8999, "MRI", "1 day", "Fast 4 h", "Optional"),
    "brain_mri": T("Brain MRI with volumetrics", "Brain", "mri", ["wmh_fazekas", "brain_age_gap", "hippocampal_pct"], "Small-vessel disease and brain volume.", "C", 6499, "MRI", "2 days", "No metal", "Only if indicated"),
    "wbmri": T("Whole-body MRI", "Imaging", "mri", ["wbmri_findings"], "Broad screen; high rate of incidental findings — counselling first.", "C", 31999, "MRI", "3 days", "No metal", "Optional"),
    "usg_abd": T("Ultrasound abdomen", "Imaging", None, [], "Liver, gall-bladder, kidneys.", "B", 1099, "Ultrasound", "Same day", "Fast 6 h", "If symptoms"),
    "thyroid_usg": T("Thyroid ultrasound", "Imaging", None, [], "Only for a palpable nodule — not for screening (USPSTF D).", "D", 1099, "Ultrasound", "Same day", "None", "Not for screening"),
    # ---------------- lungs, sleep, brain function, senses
    "spirometry": T("Spirometry + FeNO", "Lungs", "lung", ["fev1_pct", "fvc_pct", "fev1_fvc", "feno"], "COPD/asthma; smokers and breathless people.", "A", 1299, "Breath", "Same day", "No bronchodilator 4–6 h", "If symptoms or smoker"),
    "ldct": T("Low-dose CT lung", "Lungs", None, [], "Lung-cancer screening, 50–80 y with ≥20 pack-years (USPSTF B).", "A", 4499, "CT (low dose)", "1 day", "None", "Yearly if eligible"),
    "hsat": T("Home sleep apnoea test", "Sleep", "screening", ["ahi", "odi", "min_spo2"], "Snoring, unrefreshing sleep, resistant BP.", "A", 5499, "Home device, 1 night", "3 days", "Normal night", "If symptoms"),
    "psg": T("Polysomnography (in-lab)", "Sleep", "screening", ["ahi"], "Gold standard; when home test is negative but suspicion is high.", "A", 12999, "Lab, 1 night", "5 days", "—", "If indicated"),
    "cognition": T("Cognitive screen (MoCA + digital battery)", "Brain", None, [], "Baseline cognition; repeat if concerns.", "B", 0, "In clinic", "Immediate", "Rested", "Baseline at 50+"),
    "audiometry": T("Hearing test (audiometry)", "Senses", None, [], "Hearing loss is the largest modifiable dementia risk (Lancet Commission 2024).", "A", 799, "Booth", "Same day", "None", "Every 3 y from 50"),
    "eye": T("Eye exam + retinal imaging", "Senses", None, [], "Glaucoma, diabetic retinopathy; retinal age research.", "A", 1199, "Imaging", "Same day", "No contacts", "Every 2 y; yearly if diabetic"),
    "dental": T("Dental & periodontal check", "Senses", None, [], "Periodontitis links with cardiovascular and metabolic disease.", "B", 599, "Clinic", "Same day", "None", "Every 6 months"),
    # ---------------- cancer screening
    "fit": T("FIT (faecal immunochemical test)", "Cancer screening", "screening", ["fit"], "Colorectal cancer, 45–75 (USPSTF A/B).", "A", 799, "Stool", "2 days", "None", "Yearly"),
    "colonoscopy": T("Colonoscopy", "Cancer screening", None, [], "Colorectal cancer, 45–75; every 10 y if normal.", "A", 10999, "Procedure", "Same day", "Bowel prep", "Every 10 years"),
    "psa": T("PSA", "Cancer screening", "hormones", ["psa"], "Prostate cancer, 55–69 — shared decision (USPSTF C).", "B", 600, "Blood", "1 day", "No cycling/ejaculation 48 h", "Every 2 y if chosen"),
    "mammogram": T("Mammogram", "Cancer screening", None, [], "Breast cancer, women 40–74 every 2 y (USPSTF 2024 B).", "A", 2199, "X-ray", "Same day", "No deodorant", "Every 2 years"),
    "cervical": T("HPV test / Pap smear", "Cancer screening", None, [], "Cervical cancer, 21–65 (USPSTF A).", "A", 2500, "Swab", "5 days", "Not during period", "Every 3–5 years"),
    "oral": T("Oral cancer visual exam", "Cancer screening", None, [], "High oral-cancer burden in India; tobacco/areca users.", "B", 0, "Clinic", "Immediate", "None", "Yearly if tobacco"),
    "mced": T("Multi-cancer early detection (cfDNA)", "Cancer screening", "screening", ["mced"], "Not a replacement for guideline screening; limited availability and evidence pending (NHS-Galleri).", "C", 65000, "Blood", "3 weeks", "Counselling first", "Optional"),
    # ---------------- infectious disease (2026-10-29). Symptom-driven, so none are in recommend(); prices are PLACEHOLDER India list prices.
    "hepatitis_panel": T("Hepatitis panel (A, B, C, E)", "Infectious disease", "infectious", ["hav_igm", "hbsag", "anti_hbs", "anti_hbc_total", "hcv_ab", "hev_igm"],
                         "Jaundice, raised liver enzymes, or screening before vaccination, surgery or immunosuppression. Splits acute from past infection and shows hepatitis B immunity.", "A", 1899, "Blood", "1-2 days", "None", "When indicated"),
    "hiv_test": T("HIV 1 & 2 (4th-generation antigen/antibody)", "Infectious disease", "infectious", ["hiv_combo"],
                  "One-time screening for everyone 15-65 (USPSTF A) and after any exposure. A reactive result needs a confirmatory test.", "A", 500, "Blood", "1 day", "None", "Once, then if exposed"),
    "hbv_full": T("Hepatitis B - full work-up", "Infectious disease", "infectious", ["hbsag", "anti_hbs", "hbeag", "anti_hbe", "anti_hbc_total", "anti_hbc_igm", "hbv_dna"],
                  "For a positive HBsAg: phase of infection, infectivity and viral load to decide on treatment.", "A", 5499, "Blood", "3 days", "None", "Every 6-12 months if positive"),
    "hcv_full": T("Hepatitis C - confirm & genotype", "Infectious disease", "infectious", ["hcv_ab", "hcv_rna", "hcv_genotype"],
                  "For a positive anti-HCV: confirms active infection by RNA and sets the genotype for treatment (cure rates above 95% with antivirals).", "A", 7999, "Blood", "5 days", "None", "Once if antibody positive"),
    "fever_panel": T("Tropical fever panel (dengue, chikungunya, malaria, typhoid, CBC, CRP)", "Infectious disease", "infectious",
                     ["dengue_ns1", "dengue_igm", "chik_igm", "malaria_rdt", "malaria_smear", "typhidot", "widal", "hscrp", "hemoglobin", "wbc", "platelets"],
                     "The standard India work-up for fever beyond 2-3 days, especially in monsoon season. NS1 is best in the first 5 days, IgM from day 5; platelets track dengue severity.", "A", 1999, "Blood", "Same day", "None", "When febrile"),
    "tb_panel": T("Tuberculosis panel (IGRA, AFB smear, GeneXpert)", "Infectious disease", "infectious", ["tb_igra", "tb_afb_smear", "tb_genexpert"],
                  "Cough over 2 weeks, night sweats, weight loss or a TB contact. IGRA finds latent infection; sputum GeneXpert finds active disease and rifampicin resistance.", "A", 3799, "Blood + sputum", "2 days", "Early-morning sputum", "When indicated"),
    "tb_culture_dst": T("TB culture & drug susceptibility (MGIT)", "Infectious disease", "infectious", ["tb_culture"],
                        "Gold standard for active TB and drug resistance; takes weeks.", "A", 1999, "Sputum", "2-6 weeks", "Early-morning sputum", "When indicated"),
    "tb_skin": T("Mantoux (tuberculin skin test)", "Infectious disease", "infectious", ["mantoux"],
                 "Screening for latent TB; BCG vaccination can cause false positives, so IGRA is preferred in adults.", "B", 349, "Clinic", "48-72 h", "Return for reading at 48-72 h", "When indicated"),
    "hpylori_test": T("H. pylori test", "Infectious disease", "infectious", ["hpylori_stool_ag", "hpylori_ubt"],
                      "Persistent dyspepsia, ulcer history or before long-term acid suppression. Stool antigen and breath test show active infection; blood antibodies do not.", "A", 1199, "Stool or breath", "1 day", "Stop PPIs 2 weeks, antibiotics 4 weeks", "Once; repeat after treatment"),
    "sti_panel": T("Comprehensive STI panel", "Infectious disease", "infectious", ["hiv_combo", "hbsag", "hcv_ab", "vdrl", "tpha", "hsv_igg", "ct_naat", "ng_naat", "hpv_hr"],
                   "HIV, hepatitis B/C, syphilis, herpes, chlamydia, gonorrhoea and high-risk HPV in one visit; for a new partner or after exposure.", "A", 6499, "Blood + urine/swab", "3 days", "Hold urine 1-2 h", "With new partners"),
    "syphilis_test": T("Syphilis (VDRL + TPHA)", "Infectious disease", "infectious", ["vdrl", "tpha"],
                       "Screen with VDRL, confirm with TPHA; required in pregnancy.", "A", 699, "Blood", "1 day", "None", "When indicated"),
    "hpv_test": T("HPV DNA (high-risk genotyping)", "Infectious disease", "infectious", ["hpv_hr"],
                  "Cervical-cancer screening and follow-up of abnormal Pap smears; types 16/18 carry the highest risk.", "A", 2499, "Swab", "5 days", "Not during period; no intercourse 48 h", "Every 5 years"),
    "respiratory_viral_panel": T("Respiratory viral panel (multiplex PCR)", "Infectious disease", "infectious", ["resp_viral_pcr", "influenza_ab", "covid_pcr"],
                                 "Names the virus behind cough, fever and breathlessness (influenza, COVID-19, RSV and others) so antibiotics are not used needlessly.", "B", 3999, "Nasopharyngeal swab", "1 day", "None", "When symptomatic"),
    "covid_test": T("SARS-CoV-2 RT-PCR", "Infectious disease", "infectious", ["covid_pcr"],
                    "Confirms COVID-19 in symptomatic people and before high-risk travel or procedures.", "A", 699, "Nasopharyngeal swab", "Same day", "None", "When symptomatic"),
    "dengue_test": T("Dengue NS1 + IgM/IgG", "Infectious disease", "infectious", ["dengue_ns1", "dengue_igm", "dengue_igg"],
                     "Fever with body pain or low platelets; NS1 early, IgM after day 5.", "A", 1099, "Blood", "Same day", "None", "When febrile"),
    "malaria_test": T("Malaria (smear + rapid antigen)", "Infectious disease", "infectious", ["malaria_smear", "malaria_rdt"],
                      "Any fever with chills in or after travel to an endemic area. Repeat if negative and fever persists.", "A", 599, "Blood", "Same day", "Best at a fever spike", "When febrile"),
    "typhoid_test": T("Typhoid (Typhidot + Widal)", "Infectious disease", "infectious", ["typhidot", "widal"],
                      "Fever over 3 days with abdominal symptoms. Blood culture is more reliable in the first week.", "B", 549, "Blood", "Same day", "None", "When febrile"),
    "zoonoses_panel": T("Leptospira & brucella", "Infectious disease", "infectious", ["lepto_igm", "brucella"],
                        "Fever after flood, animal or unpasteurised-milk exposure.", "B", 1999, "Blood", "2 days", "None", "When indicated"),
    "torch_screen": T("TORCH screen (toxoplasma, rubella, CMV, HSV)", "Infectious disease", "infectious",
                      ["toxo_igm", "toxo_igg", "mmr_igm", "mmr_igg", "cmv_igm", "cmv_igg", "hsv_igm", "hsv_igg"],
                      "Pre-conception or early-pregnancy immunity and infection check.", "B", 3499, "Blood", "2 days", "None", "Pre-conception"),
    "herpesvirus_panel": T("Herpesviruses (EBV, CMV, VZV, HSV)", "Infectious disease", "infectious",
                           ["ebv_vca_igm", "ebv_vca_igg", "ebv_ebna", "cmv_igm", "cmv_igg", "vzv_igm", "vzv_igg", "hsv_igm", "hsv_igg"],
                           "Glandular-fever-type illness, prolonged fatigue with fever, or an immunity check before immunosuppression.", "B", 4999, "Blood", "3 days", "None", "When indicated"),
    "hiv_monitoring": T("HIV viral load + CD4", "Infectious disease", "infectious", ["hiv_rna", "cd4"],
                        "Treatment monitoring in people living with HIV.", "A", 4999, "Blood", "3 days", "None", "Every 3-6 months on treatment"),
    "culture_blood": T("Blood culture & sensitivity", "Infectious disease", "infectious", ["blood_culture"],
                       "Fever with chills or suspected sepsis; take before antibiotics.", "A", 899, "Blood", "3-5 days", "Before first antibiotic", "When indicated"),
    "culture_urine": T("Urine culture & sensitivity", "Infectious disease", "infectious", ["urine_culture"],
                       "Urinary symptoms or recurrent UTI; identifies the bug and the antibiotics it responds to.", "A", 499, "Urine", "2-3 days", "Clean-catch mid-stream", "When symptomatic"),
    "culture_stool": T("Stool culture & sensitivity", "Infectious disease", "infectious", ["stool_culture", "vibrio_culture"],
                       "Diarrhoea beyond 3 days, blood in stool or travel-associated illness.", "A", 599, "Stool", "2-3 days", "Fresh sample", "When symptomatic"),
    "culture_sputum": T("Sputum culture & sensitivity", "Infectious disease", "infectious", ["sputum_culture"],
                        "Productive cough with fever or non-resolving pneumonia.", "A", 599, "Sputum", "2-3 days", "Early-morning deep-cough sample", "When symptomatic"),
    "culture_swab": T("Swab / pus culture & sensitivity", "Infectious disease", "infectious", ["throat_nasal_culture", "wound_pus_culture", "hvs_urethral_culture"],
                      "Throat, wound, pus, vaginal or urethral swab; the sample site is chosen at the centre.", "A", 599, "Swab", "2-3 days", "Before antibiotics", "When symptomatic"),
    "culture_sensitivity": T("Culture & sensitivity (blood, urine, stool, sputum)", "Infectious disease", "infectious",
                             ["blood_culture", "urine_culture", "stool_culture", "sputum_culture"],
                             "Combined work-up for an unexplained infection; the lab runs the cultures that match your symptoms.", "A", 2199, "Blood + urine + stool + sputum", "3-5 days", "Before antibiotics", "When indicated"),
    "stool_op_test": T("Stool ova & parasite + giardia / entamoeba / cryptosporidium", "Infectious disease", "infectious",
                       ["stool_op", "giardia_ag", "entamoeba", "crypto_stool"],
                       "Chronic loose stools, bloating or travel diarrhoea; worms and protozoa.", "A", 799, "Stool", "1 day", "Fresh sample", "When symptomatic"),
    "fungal_test": T("Fungal work-up (KOH, culture)", "Infectious disease", "infectious", ["koh_mount", "fungal_culture", "candida_culture"],
                     "Skin, nail or hair lesions that do not clear with usual creams.", "B", 799, "Scraping", "2-14 days", "No antifungal cream for 3 days", "When indicated"),
    "invasive_fungal": T("Invasive fungal markers (Aspergillus, Cryptococcus)", "Infectious disease", "infectious", ["aspergillus_gm", "crag"],
                         "Immunosuppressed people with persistent fever; done on specialist advice.", "B", 3999, "Blood", "2 days", "None", "Only with clinician"),
    "sepsis_markers": T("Sepsis markers (procalcitonin, CRP, ESR)", "Infectious disease", "infectious", ["procalcitonin", "hscrp", "esr"],
                        "Separates bacterial from viral illness and tracks response to antibiotics.", "A", 1999, "Blood", "Same day", "None", "When acutely unwell"),
    "pcr_gi_panel": T("Gastrointestinal pathogen panel (multiplex PCR)", "Infectious disease", "infectious", ["gi_pcr_panel", "rota_noro_ag"],
                      "Names bacteria, viruses and parasites behind severe or persistent diarrhoea in one run.", "B", 5999, "Stool", "1-2 days", "Fresh sample", "When symptomatic"),
    "meningitis_panel": T("Meningitis / encephalitis panel (CSF PCR + culture)", "Infectious disease", "infectious", ["meningitis_pcr", "csf_culture"],
                          "Hospital test on CSF from a lumbar puncture; ordered by the treating doctor.", "A", 8999, "CSF", "1 day", "Hospital procedure", "Only with clinician"),
    "sepsis_pcr_test": T("Bloodstream pathogen PCR", "Infectious disease", "infectious", ["sepsis_pcr", "blood_culture"],
                         "Rapid organism identification in suspected sepsis; faster than culture alone.", "B", 7999, "Blood", "1 day", "Before antibiotics", "Only with clinician"),
    # ---------------- continuous
    "cgm": T("Continuous glucose monitor (14 days)", "Metabolic", "cgm", ["cgm_mean", "cgm_tir", "cgm_cv", "gmi", "cgm_peak"], "Your own glucose response to foods, sleep and stress.", "B", 4499, "Sensor", "14 days", "Log meals in Telomy", "Every 6 months if prediabetic"),
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
