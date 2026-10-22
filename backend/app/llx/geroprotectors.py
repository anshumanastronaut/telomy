"""Telomy-LLX longevity therapeutics corpus — the geroprotector / biohacking / wellness layer.

The disease side lives in clinic_engine (TREATMENTS/THERAPIES), the centre-hardware side in modalities, and
the deficiency side in supplements. This module adds the missing layer every longevity clinic actually sells
and every biohacker actually asks about: the geroprotector DRUGS, HORMONES, PEPTIDES, longevity SUPPLEMENTS and
lifestyle PROTOCOLS — each as an evidence-graded, safety-screened, machine-readable record, so the doctor /
centre / member is steered to the *right* intervention with the *real* evidence, and onto a *proper* n-of-1
trial rather than a guess.

Design matches the existing engines exactly:
  • evidence grade  A strong human RCT/guideline · B moderate human · C small/mechanistic/mixed · D weak/contested
  • each record carries scope (what the grade is FOR — a biomarker move is not a lifespan claim)
  • status            lifestyle · consumer_supplement · otc · approved_drug · off_label · investigational · unapproved
  • hard-coded safety  contraindications + drug interactions (never a model output)
  • claims firewall   "supports / consider / discuss / tracks response" — never "treats / cures / prescribes /
                       extends lifespan". Human lifespan extension is UNPROVEN for every entry here; say so.
  • doctor gate        anything that is a drug/hormone/peptide/off-label is a clinician decision, flagged as such.

The evidence baked in is current to the 2023–2026 literature, INCLUDING the reversals that the hype missed:
taurine (2025 NIA rebuttal — not a reliable aging biomarker), metformin (TAME still unfunded; MASTERS shows it
blunts resistance-training gains), senolytics (mostly null / subgroup-only in humans), NMN (FDA relisted it as a
lawful supplement in Sept 2025; raises NAD+ but no clinical-outcome benefit shown), rapamycin (PEARL: low-dose
weekly relatively safe, benefits modest/mixed, primary visceral-fat endpoint missed). Honesty is the product.
"""
from __future__ import annotations

# ── hallmarks of aging (López-Otín 2023) used to tag mechanism ───────────────────────────────────────────
HALLMARKS = {
    "nutrient_sensing": "deregulated nutrient sensing (mTOR/AMPK/IGF-1)",
    "mito": "mitochondrial dysfunction",
    "senescence": "cellular senescence",
    "inflammation": "chronic inflammation (inflammaging)",
    "proteostasis": "loss of proteostasis / disabled autophagy",
    "epigenetic": "epigenetic alterations",
    "stem": "stem-cell exhaustion",
    "telomere": "telomere attrition",
    "intercellular": "altered intercellular communication",
    "genomic": "genomic instability",
}

GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}

# ── the corpus ───────────────────────────────────────────────────────────────────────────────────────────
# each record:
#   id, name, category (drug|hormone|peptide|senolytic|supplement|protocol), status, grade, scope,
#   hallmarks[], mechanism, effect, evidence (named trials/programs), dose, monitor[] (markers to track),
#   contra[] (conditions), interactions[] (drug substrings), triggers{goals[],biomarkers[],min_age,sex},
#   caution (one honest line). Everything is a CONSIDERATION a clinician reviews — never an order.
INTERVENTIONS: list[dict] = [

    # ========================= PROTOCOLS — the strongest, best-evidenced levers ========================
    {"id": "aerobic_vo2max", "name": "Aerobic / Zone-2 + VO₂max training", "category": "protocol",
     "status": "lifestyle", "grade": "A", "scope": "all-cause & CV mortality (large cohorts/meta-analysis)",
     "hallmarks": ["mito", "intercellular", "inflammation"],
     "mechanism": "raises cardiorespiratory fitness; mitochondrial biogenesis, insulin sensitivity, vascular function",
     "effect": "each +1 MET (~3.5 ml/kg/min VO₂max) ≈ 13% lower all-cause mortality (Kodama JAMA 2009); least-fit ≈ 5× death risk vs elite-fit (Cleveland Clinic cohort). The single highest-yield longevity intervention.",
     "evidence": "Kodama 2009 JAMA meta-analysis; Mandsager 2018 JAMA Netw Open (122,007 adults)",
     "dose": "150–300 min/wk Zone-2 (conversational) + 1–2 VO₂max intervals/wk (e.g. 4×4 min); build gradually",
     "monitor": ["vo2max", "resting_hr", "hrv", "blood_pressure"],
     "contra": ["unstable angina", "decompensated heart failure", "acute illness"],
     "interactions": [], "triggers": {"goals": ["longevity", "cardiovascular", "metabolic", "cognitive"], "biomarkers": {"vo2max": ("<", 40)}, "min_age": 18},
     "caution": "Clear high-intensity work with a clinician if known cardiac disease; progress load gradually."},

    {"id": "resistance_training", "name": "Resistance / strength training", "category": "protocol",
     "status": "lifestyle", "grade": "A", "scope": "sarcopenia, function, all-cause mortality (cohorts)",
     "hallmarks": ["stem", "intercellular", "nutrient_sensing"],
     "mechanism": "preserves muscle mass & strength, bone density, insulin sensitivity; counters sarcopenia",
     "effect": "muscle strength/mass track survival; each ~5 kg lower grip strength ≈ 16% higher mortality (PURE). Protects independence in later life.",
     "evidence": "PURE grip-strength cohort; ACSM resistance-training guidance",
     "dose": "2–3 sessions/wk, major movement patterns, progressive overload, 1.2–1.6 g/kg/day protein alongside",
     "monitor": ["grip_strength", "almi", "lean_mass", "hba1c"],
     "contra": ["acute injury", "uncontrolled hypertension (for maximal lifts)"],
     "interactions": [], "triggers": {"goals": ["longevity", "muscle", "metabolic"], "biomarkers": {"almi": ("<", 7.0)}, "min_age": 18},
     "caution": "Technique first; supervise if frail or new to training."},

    {"id": "sleep_optimization", "name": "Sleep regularity & duration", "category": "protocol",
     "status": "lifestyle", "grade": "A", "scope": "mortality, cardiometabolic, cognition (cohorts)",
     "hallmarks": ["inflammation", "proteostasis", "intercellular"],
     "mechanism": "glymphatic clearance, glucose regulation, autonomic & hormonal recovery",
     "effect": "both short (<6 h) and irregular sleep raise all-cause & CV mortality; 7–9 h with a regular schedule is protective.",
     "evidence": "UK Biobank sleep-regularity cohorts; AASM guidance",
     "dose": "7–9 h, consistent sleep/wake times, morning light, cool dark room, limit late alcohol/caffeine",
     "monitor": ["sleep_duration", "sleep_regularity", "hrv", "resting_hr"],
     "contra": [], "interactions": [], "triggers": {"goals": ["longevity", "cognitive", "metabolic", "recovery", "stress"], "biomarkers": {"sleep_duration": ("<", 6.5)}},
     "caution": "Screen for sleep apnoea if snoring/daytime sleepiness/nocturnal desaturation — treat the apnoea, not just the hours."},

    {"id": "diet_mediterranean", "name": "Mediterranean / whole-food dietary pattern", "category": "protocol",
     "status": "lifestyle", "grade": "A", "scope": "CV events & mortality (RCT: PREDIMED)",
     "hallmarks": ["inflammation", "nutrient_sensing", "intercellular"],
     "mechanism": "polyphenols, fibre, unsaturated fats, low ultra-processed load; lowers inflammation & improves lipids",
     "effect": "PREDIMED RCT: ~30% fewer major CV events vs control diet.",
     "evidence": "PREDIMED 2018 (re-analysed); large cohort consistency",
     "dose": "vegetables, legumes, whole grains, olive oil, nuts, fish; minimise ultra-processed (NOVA 4) foods",
     "monitor": ["apob", "ldl", "crp_mgL", "hba1c", "trig"],
     "contra": [], "interactions": [], "triggers": {"goals": ["longevity", "cardiovascular", "metabolic", "inflammation"]},
     "caution": "Pattern over single foods; individualise for renal/allergy needs."},

    {"id": "protein_adequacy", "name": "Adequate protein (1.2–1.6 g/kg/day)", "category": "protocol",
     "status": "lifestyle", "grade": "B", "scope": "lean mass & function in mid/older age",
     "hallmarks": ["stem", "proteostasis"],
     "mechanism": "sustains muscle protein synthesis; counters age-related anabolic resistance",
     "effect": "higher protein + resistance training preserves lean mass; benefit is on function, not a lifespan claim.",
     "evidence": "PROT-AGE / ESPEN expert guidance; RCTs on lean-mass retention",
     "dose": "1.2–1.6 g/kg/day, ~0.4 g/kg per meal, leucine-rich sources; higher end if training/older",
     "monitor": ["albumin", "almi", "creatinine"],
     "contra": [], "interactions": [], "triggers": {"goals": ["muscle", "longevity"], "biomarkers": {"albumin": ("<", 4.0)}, "min_age": 40},
     "caution": "Reduce target and supervise in significant CKD (nephrology-guided)."},

    {"id": "time_restricted_eating", "name": "Time-restricted eating / intermittent fasting", "category": "protocol",
     "status": "lifestyle", "grade": "B", "scope": "weight & glycemic markers (mixed RCTs)",
     "hallmarks": ["nutrient_sensing", "proteostasis"],
     "mechanism": "fasting lowers insulin/mTOR, may raise autophagy; most human benefit tracks the calorie deficit",
     "effect": "modest weight/glucose improvement in RCTs; eating window alone often no better than calorie matching.",
     "evidence": "TREAT RCT; multiple TRE meta-analyses (mixed)",
     "dose": "e.g. 8–10 h eating window; protect protein & total intake; not late-night eating",
     "monitor": ["hba1c", "trig", "weight", "fasting_glucose"],
     "contra": ["history of eating disorder", "pregnancy", "type 1 diabetes", "underweight", "frailty"],
     "interactions": ["insulin", "sulfonylurea"], "triggers": {"goals": ["metabolic", "longevity"], "biomarkers": {"hba1c": (">", 5.6)}},
     "caution": "Can cause hypoglycaemia on insulin/sulfonylureas — clinician must adjust meds first. Not for sarcopenia risk without protein safeguards."},

    {"id": "caloric_restriction", "name": "Mild caloric restriction / fasting-mimicking", "category": "protocol",
     "status": "lifestyle", "grade": "B", "scope": "biological-aging pace & cardiometabolic markers (RCT: CALERIE)",
     "hallmarks": ["nutrient_sensing", "inflammation", "epigenetic"],
     "mechanism": "sustained nutrient-sensing downshift; the most robust lifespan lever across species",
     "effect": "CALERIE: ~2 yr of ~12% CR slowed the DunedinPACE pace-of-aging and improved cardiometabolic risk in healthy adults.",
     "evidence": "CALERIE-2 RCT (2023 pace-of-aging analysis)",
     "dose": "modest, sustainable deficit with full micronutrient & protein adequacy; or periodic fasting-mimicking cycles",
     "monitor": ["crp_mgL", "hba1c", "ldl", "blood_pressure", "almi"],
     "contra": ["underweight", "frailty", "eating disorder history", "pregnancy"],
     "interactions": ["insulin", "sulfonylurea"], "triggers": {"goals": ["longevity", "metabolic"], "min_age": 25},
     "caution": "Guard against muscle loss and under-nutrition; not for lean/older/frail members without supervision."},

    {"id": "stress_hrv", "name": "Stress regulation (breathwork / HRV / meditation)", "category": "protocol",
     "status": "lifestyle", "grade": "B", "scope": "BP, perceived stress, autonomic balance",
     "hallmarks": ["inflammation", "intercellular"],
     "mechanism": "parasympathetic activation; lowers sympathetic drive, BP and inflammatory tone",
     "effect": "slow-breathing & meditation lower BP and improve HRV in RCTs; downstream aging effect inferred.",
     "evidence": "RCTs of device-guided slow breathing & MBSR",
     "dose": "5–10 min slow breathing (≈6 breaths/min) daily; or regular meditation practice",
     "monitor": ["hrv", "resting_hr", "blood_pressure"],
     "contra": [], "interactions": [], "triggers": {"goals": ["stress", "cardiovascular", "sleep"], "biomarkers": {"hrv": ("<", 40)}},
     "caution": "Adjunct, not a substitute for treating hypertension or an anxiety disorder."},

    {"id": "smoking_alcohol", "name": "Smoking cessation & alcohol moderation", "category": "protocol",
     "status": "lifestyle", "grade": "A", "scope": "mortality, cancer, CV (overwhelming evidence)",
     "hallmarks": ["genomic", "inflammation", "intercellular"],
     "mechanism": "removes the two largest modifiable toxic exposures",
     "effect": "cessation is the single highest-yield act for a smoker; lower alcohol lowers cancer & CV risk.",
     "evidence": "Surgeon-General / IARC consensus",
     "dose": "cessation support (NRT/varenicline via clinician); alcohol as low as feasible (no safe cancer threshold)",
     "monitor": ["blood_pressure", "ggt", "crp_mgL"],
     "contra": [], "interactions": [], "triggers": {"goals": ["longevity", "cardiovascular", "cancer_risk"]},
     "caution": "Pharmacotherapy for cessation is a clinician decision."},

    # ========================= DRUGS — geroprotectors (clinician-gated) ================================
    {"id": "rapamycin", "name": "Rapamycin (sirolimus), low-dose intermittent", "category": "drug",
     "status": "off_label", "grade": "C", "scope": "healthspan markers in humans — modest/mixed; lifespan UNPROVEN",
     "hallmarks": ["nutrient_sensing", "proteostasis", "senescence"],
     "mechanism": "mTOR inhibition → autophagy, lower senescence; most consistent lifespan drug in mice (ITP, both sexes)",
     "effect": "PEARL RCT (48 wk, weekly 5–10 mg): relatively safe; gains in lean mass & pain in women on 10 mg; primary visceral-fat endpoint NOT met. Mouse ITP strong; human longevity unproven. Industry-affiliated authors (COI).",
     "evidence": "PEARL 2024/25 (Aging-US); NIA ITP (rapamycin both sexes)",
     "dose": "investigational, e.g. ~5–6 mg once weekly; strictly clinician-supervised, off-label",
     "monitor": ["lipids", "fasting_glucose", "cbc", "crp_mgL", "mouth_ulcers"],
     "contra": ["active infection", "poor wound healing / upcoming surgery", "immunosuppression", "pregnancy", "uncontrolled hyperlipidemia"],
     "interactions": ["cyp3a4 inhibitor", "cyp3a4 inducer", "grapefruit", "live vaccine", "statin"],
     "triggers": {"goals": ["longevity"], "min_age": 45},
     "caution": "Off-label with no approved longevity indication; immunosuppressant — infection, impaired healing, lipid/glucose effects. Clinician-only, informed-consent, monitored."},

    {"id": "metformin", "name": "Metformin", "category": "drug",
     "status": "approved_drug", "grade": "A", "scope": "A for dysglycemia/diabetes prevention; C/D as a geroprotector in metabolically healthy people",
     "hallmarks": ["nutrient_sensing", "inflammation"],
     "mechanism": "AMPK activation, hepatic gluconeogenesis ↓, insulin sensitivity ↑",
     "effect": "first-line for type 2 diabetes & strong for prevention (DPP). As a longevity drug in healthy people it is unproven — TAME is still unfunded/not enrolled (2026), and MASTERS showed metformin BLUNTS resistance-training muscle/strength gains.",
     "evidence": "DPP/DPPOS; TAME (unfunded); MASTERS 2019 (exercise blunting)",
     "dose": "clinician-set (e.g. 500 mg titrated) FOR a glycemic indication; not endorsed as a healthy-person geroprotector here",
     "monitor": ["hba1c", "b12", "egfr", "fasting_glucose"],
     "contra": ["egfr <30", "acute kidney injury", "decompensated heart failure", "significant hepatic impairment", "alcohol excess"],
     "interactions": ["iodinated contrast", "insulin", "sulfonylurea"],
     "triggers": {"goals": ["metabolic"], "biomarkers": {"hba1c": (">", 5.6)}, "min_age": 25},
     "caution": "If training for strength/muscle, metformin may work against you. Depletes B12. Hold around iodinated contrast; stop if eGFR <30."},

    {"id": "acarbose", "name": "Acarbose", "category": "drug",
     "status": "off_label", "grade": "C", "scope": "mouse lifespan (male-biased); human = glucose-AUC control",
     "hallmarks": ["nutrient_sensing"],
     "mechanism": "α-glucosidase inhibition → blunts post-prandial glucose spikes",
     "effect": "NIA ITP: extended male mouse lifespan ~17%; combination with rapamycin additive. Human geroprotection unproven; used clinically for post-prandial glycemia.",
     "evidence": "NIA ITP; diabetes RCTs for glycemia",
     "dose": "clinician-set with meals (GI tolerance limits dose)",
     "monitor": ["hba1c", "fasting_glucose", "post_prandial_glucose"],
     "contra": ["inflammatory bowel disease", "cirrhosis", "significant GI disorder"],
     "interactions": ["insulin", "sulfonylurea"],
     "triggers": {"goals": ["metabolic", "longevity"], "biomarkers": {"post_prandial_glucose": (">", 140)}},
     "caution": "Flatulence/GI side-effects limit adherence; off-label for longevity."},

    {"id": "sglt2i", "name": "SGLT2 inhibitor (empagliflozin / canagliflozin / dapagliflozin)", "category": "drug",
     "status": "approved_drug", "grade": "A", "scope": "A for cardiorenal/HF outcomes; C as a geroprotector",
     "hallmarks": ["nutrient_sensing", "mito", "inflammation"],
     "mechanism": "urinary glucose loss, mild ketosis, cardiorenal protection",
     "effect": "strong RCT cardiorenal & heart-failure mortality benefit; canagliflozin extended male mouse lifespan (ITP). Healthy-person geroprotection unproven.",
     "evidence": "EMPA-REG/CREDENCE/DAPA-HF; NIA ITP (canagliflozin, males)",
     "dose": "clinician-set FOR a cardiorenal/metabolic indication",
     "monitor": ["egfr", "hba1c", "ketones", "volume_status"],
     "contra": ["type 1 diabetes", "recurrent genital infection", "volume depletion", "DKA history"],
     "interactions": ["diuretic", "insulin"],
     "triggers": {"goals": ["metabolic", "cardiovascular"], "biomarkers": {"hba1c": (">", 6.0)}},
     "caution": "Euglycemic DKA risk, genital mycotic infections; prescribe for an indication, not vanity."},

    {"id": "glp1_ra", "name": "GLP-1 / GIP receptor agonist (semaglutide / tirzepatide)", "category": "drug",
     "status": "approved_drug", "grade": "A", "scope": "A for obesity, cardiometabolic & mortality in obesity+CVD; aging = inference",
     "hallmarks": ["inflammation", "nutrient_sensing", "intercellular"],
     "mechanism": "appetite/satiety & glycemic control; weight loss, anti-inflammatory, cardiovascular benefit",
     "effect": "SELECT RCT (obese, CVD, no diabetes): all-cause death HR 0.81, MACE −20%. A genuine mortality signal — but it is a cardiometabolic drug, not a proven anti-aging agent.",
     "evidence": "SELECT 2023; STEP/SURMOUNT; SURPASS",
     "dose": "clinician-set, titrated FOR obesity/metabolic indication",
     "monitor": ["weight", "hba1c", "almi", "heart_rate", "gi_tolerance"],
     "contra": ["personal/family medullary thyroid cancer", "MEN2", "pancreatitis history", "pregnancy", "severe gastroparesis"],
     "interactions": ["insulin", "sulfonylurea"],
     "triggers": {"goals": ["metabolic", "cardiovascular", "longevity"], "biomarkers": {"bmi": (">", 30)}},
     "caution": "Protect muscle (protein + resistance training) during rapid weight loss; GI effects; prescribe for an indication."},

    {"id": "low_dose_lithium", "name": "Low-dose lithium (microdose)", "category": "drug",
     "status": "investigational", "grade": "C", "scope": "neuroprotection/mood signals; longevity contested",
     "hallmarks": ["proteostasis", "intercellular"],
     "mechanism": "GSK-3β inhibition, autophagy induction (preclinical)",
     "effect": "ecological & small-trial signals for lower suicide/dementia risk; longevity data thin and contested.",
     "evidence": "trace-lithium ecological studies; small cognition trials",
     "dose": "investigational microdoses; clinician-only",
     "monitor": ["lithium_level", "tsh", "egfr"],
     "contra": ["significant renal impairment", "thyroid disease (uncontrolled)", "pregnancy"],
     "interactions": ["nsaid", "ace inhibitor", "arb", "thiazide", "diuretic"],
     "triggers": {"goals": ["cognitive", "longevity"], "min_age": 50},
     "caution": "Even low-dose lithium has a narrow therapeutic index and renal/thyroid effects; evidence is weak. Clinician-only."},

    # ========================= HORMONES =================================================================
    {"id": "trt", "name": "Testosterone replacement (TRT)", "category": "hormone",
     "status": "approved_drug", "grade": "A", "scope": "A for diagnosed hypogonadism; NOT a longevity therapy",
     "hallmarks": ["stem", "intercellular"],
     "mechanism": "restores physiologic testosterone in true deficiency",
     "effect": "corrects symptoms of confirmed hypogonadism (libido, mood, lean mass). TRAVERSE showed CV safety in that population — but it is treatment of a deficiency, not anti-aging for normal levels.",
     "evidence": "TRAVERSE 2023 (CV safety); Endocrine Society guideline",
     "dose": "clinician-set, only after two low morning totals + symptoms",
     "monitor": ["total_testosterone", "free_testosterone", "hematocrit", "psa", "estradiol"],
     "contra": ["prostate/breast cancer", "polycythemia", "untreated severe OSA", "desire for fertility", "uncontrolled heart failure"],
     "interactions": ["anticoagulant"],
     "triggers": {"goals": ["muscle", "energy"], "biomarkers": {"total_testosterone": ("<", 300)}, "sex": "M", "min_age": 30},
     "caution": "Raises hematocrit, suppresses fertility. Only for biochemically & symptomatically confirmed hypogonadism — not for 'optimisation' of normal levels."},

    {"id": "dhea", "name": "DHEA", "category": "hormone",
     "status": "otc", "grade": "C", "scope": "modest effects; benefit mainly if measured low",
     "hallmarks": ["intercellular"],
     "mechanism": "adrenal precursor to sex steroids; declines with age",
     "effect": "small/inconsistent effects on bone, skin, well-being; clearest when DHEA-S is low. Not a proven longevity agent.",
     "evidence": "small RCTs; largely null for hard outcomes",
     "dose": "clinician-guided if DHEA-S low (e.g. 25–50 mg); banned in sport",
     "monitor": ["dhea_s", "estradiol", "total_testosterone"],
     "contra": ["hormone-sensitive cancer", "pregnancy"],
     "interactions": ["hormone therapy"],
     "triggers": {"goals": ["energy", "longevity"], "biomarkers": {"dhea_s": ("<", 100)}, "min_age": 50},
     "caution": "Converts to sex steroids — avoid in hormone-sensitive cancer; measure before using."},

    {"id": "melatonin", "name": "Melatonin", "category": "hormone",
     "status": "otc", "grade": "B", "scope": "B for sleep-onset & circadian; longevity C",
     "hallmarks": ["intercellular", "inflammation"],
     "mechanism": "circadian signalling; antioxidant at higher doses (preclinical)",
     "effect": "helps sleep onset & circadian realignment (jet lag/shift work) at low doses; direct aging benefit unproven.",
     "evidence": "sleep & circadian RCTs/meta-analyses",
     "dose": "0.5–3 mg, 30–60 min before target sleep; low dose often better",
     "monitor": ["sleep_onset", "sleep_quality"],
     "contra": ["pregnancy", "autoimmune disease (caution)"],
     "interactions": ["anticoagulant", "sedative", "immunosuppressant"],
     "triggers": {"goals": ["sleep", "longevity"], "biomarkers": {"sleep_onset": (">", 30)}},
     "caution": "Product-dose accuracy varies; it is a chronobiotic, not a sedative — timing matters more than dose."},

    {"id": "growth_hormone", "name": "Growth hormone / GH secretagogues", "category": "hormone",
     "status": "approved_drug", "grade": "D", "scope": "NOT recommended for longevity — risk outweighs",
     "hallmarks": ["nutrient_sensing"],
     "mechanism": "GH/IGF-1 axis — but the longevity literature links LOWER IGF-1 to longer life",
     "effect": "raises lean mass/reduces fat cosmetically but increases insulin resistance, edema, carpal tunnel, and cancer-risk concerns; low-IGF-1 states (Laron) are long-lived. Against longevity logic.",
     "evidence": "Laron-syndrome longevity; GH adult-deficiency trials (indication-specific)",
     "dose": "only for diagnosed GH deficiency, endocrinologist-managed; not for anti-aging",
     "monitor": ["igf_1", "fasting_glucose", "hba1c"],
     "contra": ["active malignancy", "diabetes/insulin resistance", "proliferative retinopathy"],
     "interactions": ["insulin", "corticosteroid"],
     "triggers": {"goals": [], "min_age": 99},
     "caution": "Explicitly NOT advised as a longevity therapy — flag and steer away unless true, diagnosed GH deficiency."},

    # ========================= PEPTIDES (investigational / regulatory caveats) =========================
    {"id": "bpc157", "name": "BPC-157", "category": "peptide",
     "status": "unapproved", "grade": "D", "scope": "animal healing data; human evidence very thin",
     "hallmarks": ["intercellular"],
     "mechanism": "putative angiogenesis / tissue-repair peptide (mostly rodent)",
     "effect": "strong anecdote & rodent data for soft-tissue healing; almost no controlled human evidence.",
     "evidence": "rodent studies; one small UC trial; 2026 FDA compounding advisory (non-binding)",
     "dose": "not established; not an approved drug",
     "monitor": [], "contra": ["active cancer", "pregnancy"], "interactions": [],
     "triggers": {"goals": [], "min_age": 99},
     "caution": "Not FDA-approved; US compounding status unsettled (2026). Purity/sourcing & legal risk. Do not recommend — discuss only as experimental with full informed consent."},

    {"id": "thymosin_a1", "name": "Thymosin alpha-1", "category": "peptide",
     "status": "unapproved", "grade": "B", "scope": "B for immune modulation (approved ex-US); not US-approved",
     "hallmarks": ["inflammation", "intercellular"],
     "mechanism": "T-cell maturation / immune modulation",
     "effect": "the best-evidenced longevity-adjacent peptide — randomized human immune data; approved in 30+ countries (e.g. sepsis/hepatitis adjunct), not the US.",
     "evidence": "RCTs in infection/immune contexts; ex-US approvals",
     "dose": "indication-specific, clinician-managed where approved",
     "monitor": ["cbc", "lymphocyte_subsets"],
     "contra": ["organ transplant/immunosuppression", "pregnancy"], "interactions": ["immunosuppressant"],
     "triggers": {"goals": ["immune"], "min_age": 50},
     "caution": "Not US-approved (regulatory, not purely scientific, gap). Jurisdiction & sourcing matter; clinician-only."},

    {"id": "epitalon", "name": "Epitalon (epithalon)", "category": "peptide",
     "status": "unapproved", "grade": "D", "scope": "small single-group claims (telomerase); unreplicated",
     "hallmarks": ["telomere"],
     "mechanism": "putative telomerase induction (mostly one research lineage)",
     "effect": "claimed telomere/telomerase effects from small, mostly Russian studies; not independently replicated.",
     "evidence": "Khavinson-group studies (small, unreplicated)",
     "dose": "not established; not an approved drug",
     "monitor": [], "contra": ["active cancer", "pregnancy"], "interactions": [],
     "triggers": {"goals": [], "min_age": 99},
     "caution": "Unapproved, unreplicated, telomerase activation carries theoretical cancer concern. Do not recommend."},

    # ========================= SENOLYTICS ===============================================================
    {"id": "dq_senolytic", "name": "Dasatinib + Quercetin (senolytic)", "category": "senolytic",
     "status": "investigational", "grade": "C", "scope": "clears senescent cells; clinical benefit mostly null/subgroup",
     "hallmarks": ["senescence", "inflammation"],
     "mechanism": "intermittent 'hit-and-run' clearance of senescent cells",
     "effect": "pilot data: reduces senescent-cell burden in days. But the randomized post-menopausal bone trial MISSED its primary endpoint (benefit only in a high-senescent-burden subgroup); no adequately-powered RCT shows clinical benefit yet.",
     "evidence": "Mayo DKD pilot; Mayo bone RCT 2024 (subgroup-only)",
     "dose": "investigational intermittent dosing; trial/clinician context only",
     "monitor": ["crp_mgL", "senescence_markers", "cbc"],
     "contra": ["active infection", "cytopenias", "QT-prolonging context (dasatinib)", "pregnancy"],
     "interactions": ["cyp3a4 inhibitor", "anticoagulant", "qt-prolonging drug"],
     "triggers": {"goals": ["longevity", "inflammation"], "min_age": 60},
     "caution": "Dasatinib is a chemotherapeutic with real toxicity. Investigational only — best inside a trial, never casual."},

    {"id": "fisetin", "name": "Fisetin", "category": "senolytic",
     "status": "consumer_supplement", "grade": "C", "scope": "senolytic flavonoid; human outcomes largely null so far",
     "hallmarks": ["senescence", "inflammation"],
     "mechanism": "flavonoid with senolytic activity in mice",
     "effect": "robust mouse data; human trials to date (incl. OA) have not shown clear benefit. Well-tolerated as a supplement.",
     "evidence": "mouse senolytic studies; human trials mixed/null (Mayo fisetin data unpublished)",
     "dose": "studied intermittently (e.g. 20 mg/kg × 2 days/month) — unvalidated in humans; low-dose otherwise",
     "monitor": ["crp_mgL"],
     "contra": ["pregnancy"], "interactions": ["anticoagulant", "cyp substrate"],
     "triggers": {"goals": ["longevity", "inflammation"], "min_age": 50},
     "caution": "Human senolytic benefit unproven; cheap and safe but don't over-claim."},

    # ========================= SUPPLEMENTS (consumer) ===================================================
    {"id": "omega3", "name": "Omega-3 (EPA/DHA)", "category": "supplement",
     "status": "consumer_supplement", "grade": "B", "scope": "B for TG & biological-aging markers; CV-outcome evidence mixed",
     "hallmarks": ["inflammation", "intercellular"],
     "mechanism": "anti-inflammatory eicosanoids; membrane & lipid effects",
     "effect": "DO-HEALTH RCT: 1 g/day slowed several DNAm aging clocks (small, ~3–4 months over 3 yr), additive with vitamin D + exercise; lowers triglycerides. Hard CV-outcome trials are mixed.",
     "evidence": "DO-HEALTH 2025 (Nature Aging); VITAL; REDUCE-IT (EPA, high-TG)",
     "dose": "1–2 g/day combined EPA+DHA (higher for high triglycerides, clinician-guided)",
     "monitor": ["trig", "omega3_index", "crp_mgL"],
     "contra": [], "interactions": ["warfarin", "apixaban", "clopidogrel"],
     "triggers": {"goals": ["longevity", "cardiovascular", "inflammation", "cognitive"], "biomarkers": {"trig": (">", 150)}},
     "caution": "Mild bleeding-risk additivity with anticoagulants; choose oxidation-tested products."},

    {"id": "vitamin_d", "name": "Vitamin D3 (+K2 where appropriate)", "category": "supplement",
     "status": "consumer_supplement", "grade": "A", "scope": "A for correcting deficiency & falls; aging B",
     "hallmarks": ["inflammation", "intercellular"],
     "mechanism": "endocrine/immune signalling; musculoskeletal",
     "effect": "corrects measured deficiency; falls/fracture benefit when deficient; DO-HEALTH additive aging-clock effect. Routine mega-dosing without deficiency adds little.",
     "evidence": "DO-HEALTH; VITAL; deficiency-correction RCTs",
     "dose": "1000–2000 IU/day (4000 IU if <20 ng/mL, recheck 8–12 wk); test first",
     "monitor": ["vitamin_d_25oh", "calcium"],
     "contra": ["hypercalcemia", "sarcoidosis", "primary hyperparathyroidism"],
     "interactions": ["thiazide (calcium)"],
     "triggers": {"goals": ["longevity", "immune", "muscle"], "biomarkers": {"vitamin_d_25oh": ("<", 30)}},
     "caution": "Dose to the level, not the fashion; avoid in hypercalcemia."},

    {"id": "creatine", "name": "Creatine monohydrate", "category": "supplement",
     "status": "consumer_supplement", "grade": "A", "scope": "A for strength/lean mass; B cognition/fatigue",
     "hallmarks": ["mito", "stem"],
     "mechanism": "phosphocreatine energy buffering in muscle & brain",
     "effect": "one of the most robust supplements — improves strength, power & lean mass with resistance training; emerging cognition/fatigue benefit. Safe long-term.",
     "evidence": "large RCT/meta-analysis base (strength); cognition emerging",
     "dose": "3–5 g/day (no load needed); consistent daily",
     "monitor": ["almi", "grip_strength"],
     "contra": ["significant renal impairment (caution)"],
     "interactions": [], "triggers": {"goals": ["muscle", "cognitive", "longevity"], "min_age": 18},
     "caution": "Harmless creatinine rise can mimic renal change on labs — tell the lab. Caution in real CKD."},

    {"id": "nmn", "name": "NMN (nicotinamide mononucleotide)", "category": "supplement",
     "status": "consumer_supplement", "grade": "D", "scope": "A for raising NAD+; D for any clinical outcome",
     "hallmarks": ["mito", "nutrient_sensing"],
     "mechanism": "NAD+ precursor",
     "effect": "reliably ~doubles circulating NAD+ (head-to-head RCT) but a 2024 meta-analysis of 12 trials found no clinically meaningful outcome vs control. FDA relisted NMN as a lawful supplement (Sept 2025).",
     "evidence": "NAD+ head-to-head RCT (Nature Metab); 2024 NMN meta-analysis (null outcomes)",
     "dose": "commonly 250–500 mg/day; short-term safe",
     "monitor": ["nad_level"],
     "contra": ["active cancer (precautionary, NAD+/proliferation debate)"], "interactions": [],
     "triggers": {"goals": ["longevity", "energy"], "min_age": 40},
     "caution": "Raises a number (NAD+), not yet a proven outcome. Precautionary pause in active malignancy."},

    {"id": "nr", "name": "NR (nicotinamide riboside)", "category": "supplement",
     "status": "consumer_supplement", "grade": "D", "scope": "A for raising NAD+; D for clinical outcomes",
     "hallmarks": ["mito", "nutrient_sensing"],
     "mechanism": "NAD+ precursor (longer regulatory record than NMN; GRAS since 2016)",
     "effect": "raises NAD+ and is well-tolerated, but like NMN no human outcome benefit demonstrated.",
     "evidence": "multiple NR RCTs (NAD+ up, outcomes neutral)",
     "dose": "commonly 300–1000 mg/day",
     "monitor": ["nad_level"],
     "contra": ["active cancer (precautionary)"], "interactions": [],
     "triggers": {"goals": ["longevity", "energy"], "min_age": 40},
     "caution": "Same as NMN — a biomarker mover without proven endpoints."},

    {"id": "urolithin_a", "name": "Urolithin A (Mitopure)", "category": "supplement",
     "status": "consumer_supplement", "grade": "C", "scope": "C for muscle/mitochondrial endurance; low-certainty",
     "hallmarks": ["mito"],
     "mechanism": "induces mitophagy (clears damaged mitochondria)",
     "effect": "several RCTs show modest muscle strength/endurance & mitochondrial-marker gains, but some missed primary endpoints; a 2026 review rated certainty LOW.",
     "evidence": "ATLAS & related RCTs (mixed primaries); 2026 systematic review (low certainty)",
     "dose": "500–1000 mg/day",
     "monitor": ["grip_strength", "vo2max"],
     "contra": [], "interactions": [],
     "triggers": {"goals": ["muscle", "longevity"], "min_age": 40},
     "caution": "Promising mechanism, modest & low-certainty human effect; not a lifespan claim."},

    {"id": "glynac", "name": "GlyNAC (glycine + N-acetylcysteine)", "category": "supplement",
     "status": "consumer_supplement", "grade": "C", "scope": "C for glutathione/oxidative stress, strength; small single-group trials",
     "hallmarks": ["mito", "inflammation", "proteostasis"],
     "mechanism": "restores glutathione synthesis; lowers oxidative stress",
     "effect": "Baylor trials: improves glutathione, oxidative stress, mitochondrial markers, strength & (secondary) cognition in older adults — but small, mostly one group, benefit recedes on stopping.",
     "evidence": "Baylor pilot + small RCT (Kumar et al.)",
     "dose": "glycine ~100 mg/kg/day + NAC ~100 mg/kg/day (studied doses; large) — clinician-guided",
     "monitor": ["glutathione", "crp_mgL", "grip_strength"],
     "contra": ["asthma (NAC caution)"], "interactions": ["nitroglycerin"],
     "triggers": {"goals": ["longevity", "muscle", "energy"], "min_age": 60},
     "caution": "Evidence from one group; study doses are high. Glycine alone also aids sleep/metabolic markers."},

    {"id": "spermidine", "name": "Spermidine", "category": "supplement",
     "status": "consumer_supplement", "grade": "C", "scope": "autophagy inducer; human cognition mostly null",
     "hallmarks": ["proteostasis", "nutrient_sensing"],
     "mechanism": "induces autophagy (strong preclinical)",
     "effect": "epidemiology links dietary spermidine to lower mortality; the SmartAge memory RCT was largely null. Food sources (wheat germ, legumes, aged cheese) are reasonable.",
     "evidence": "cohort associations; SmartAge RCT (null on memory)",
     "dose": "~1 mg/day (supplement) or spermidine-rich foods",
     "monitor": [], "contra": [], "interactions": [],
     "triggers": {"goals": ["longevity", "cognitive"], "min_age": 50},
     "caution": "Food-first; supplement cognition benefit not shown."},

    {"id": "ca_akg", "name": "Calcium alpha-ketoglutarate (Ca-AKG)", "category": "supplement",
     "status": "consumer_supplement", "grade": "D", "scope": "one uncontrolled human methylation-age study",
     "hallmarks": ["epigenetic", "nutrient_sensing"],
     "mechanism": "TCA-cycle metabolite; epigenetic cofactor (preclinical)",
     "effect": "mouse healthspan data; the human 'Rejuvant' study (n≈42) reported a large methylation-age drop but had NO control group. Hypothesis-generating only.",
     "evidence": "mouse (Buck Institute); uncontrolled human cohort (Rejuvant)",
     "dose": "~1 g/day in studies",
     "monitor": ["epigenetic_age"], "contra": [], "interactions": [],
     "triggers": {"goals": ["longevity"], "min_age": 50},
     "caution": "Uncontrolled human data — a striking number that may be regression/selection. Weak."},

    {"id": "coq10", "name": "CoQ10 / ubiquinol", "category": "supplement",
     "status": "consumer_supplement", "grade": "B", "scope": "B for statin myalgia & heart failure adjunct",
     "hallmarks": ["mito"],
     "mechanism": "mitochondrial electron transport, antioxidant",
     "effect": "helps some statin-associated muscle symptoms; HF adjunct signal (Q-SYMBIO). General anti-aging benefit weak.",
     "evidence": "Q-SYMBIO (HF); statin-myalgia trials (mixed)",
     "dose": "100–200 mg/day (ubiquinol better absorbed)",
     "monitor": ["statin_myalgia", "ef"],
     "contra": [], "interactions": ["warfarin"],
     "triggers": {"goals": ["cardiovascular", "energy"], "biomarkers": {}},
     "caution": "Clearest value is statin myalgia & HF adjunct, not general longevity."},

    {"id": "magnesium", "name": "Magnesium (glycinate/threonate)", "category": "supplement",
     "status": "consumer_supplement", "grade": "B", "scope": "B for repletion, BP, sleep, glycemia",
     "hallmarks": ["intercellular", "nutrient_sensing"],
     "mechanism": "cofactor in 300+ reactions; vascular & neuromuscular",
     "effect": "corrects common insufficiency; modest BP, sleep & insulin-sensitivity benefits.",
     "evidence": "BP & glycemic meta-analyses",
     "dose": "200–400 mg elemental/day (glycinate for sleep, threonate marketed for brain)",
     "monitor": ["magnesium", "blood_pressure"],
     "contra": ["significant renal impairment"], "interactions": ["levothyroxine", "quinolone", "tetracycline", "bisphosphonate"],
     "triggers": {"goals": ["sleep", "cardiovascular", "metabolic"], "biomarkers": {"magnesium": ("<", 1.9)}},
     "caution": "Separate from thyroid meds/antibiotics; caution in CKD."},

    {"id": "glycine", "name": "Glycine", "category": "supplement",
     "status": "consumer_supplement", "grade": "C", "scope": "C for sleep quality & metabolic markers",
     "hallmarks": ["proteostasis", "inflammation"],
     "mechanism": "glutathione substrate; thermoregulatory sleep effect",
     "effect": "~3 g before bed improves subjective sleep in small trials; component of GlyNAC's benefit.",
     "evidence": "small sleep RCTs; GlyNAC program",
     "dose": "3 g before bed",
     "monitor": ["sleep_quality"], "contra": [], "interactions": ["clozapine"],
     "triggers": {"goals": ["sleep", "longevity"], "biomarkers": {}},
     "caution": "Cheap and safe; benefit modest."},

    {"id": "taurine", "name": "Taurine", "category": "supplement",
     "status": "consumer_supplement", "grade": "D", "scope": "D for longevity (2025 rebuttal); C for BP",
     "hallmarks": ["mito", "inflammation"],
     "mechanism": "osmolyte; mitochondrial & calcium-handling roles",
     "effect": "the 2023 Science mouse paper drove hype, but a 2025 NIA rebuttal (humans, monkeys, mice) found taurine does NOT reliably fall with age — it is not a good aging biomarker. Modest BP-lowering has some human support.",
     "evidence": "Singh 2023 Science (mice); de Cabo 2025 Science rebuttal",
     "dose": "1–3 g/day (studied for BP/exercise)",
     "monitor": ["blood_pressure"], "contra": [], "interactions": [],
     "triggers": {"goals": ["cardiovascular"], "biomarkers": {}},
     "caution": "Longevity case was overstated and partly reversed in 2025; keep expectations to BP/exercise, if anything."},

    {"id": "sulforaphane", "name": "Sulforaphane (broccoli sprout extract)", "category": "supplement",
     "status": "consumer_supplement", "grade": "C", "scope": "C for Nrf2/antioxidant & detox markers",
     "hallmarks": ["inflammation", "genomic"],
     "mechanism": "Nrf2 activation → endogenous antioxidant/detox enzymes",
     "effect": "biomarker-level antioxidant & detoxification effects; clinical outcomes preliminary.",
     "evidence": "small human biomarker trials",
     "dose": "standardised sprout extract with active myrosinase; food (broccoli sprouts) first",
     "monitor": ["crp_mgL"], "contra": [], "interactions": [],
     "triggers": {"goals": ["longevity", "inflammation"], "biomarkers": {}},
     "caution": "Bioavailability varies hugely by product; food source is reliable."},

    {"id": "collagen", "name": "Collagen peptides (+ vitamin C)", "category": "supplement",
     "status": "consumer_supplement", "grade": "C", "scope": "C for skin elasticity/hydration & joint comfort",
     "hallmarks": ["intercellular"],
     "mechanism": "provides glycine/proline; may signal dermal/tendon matrix synthesis",
     "effect": "meta-analyses show modest skin elasticity/hydration gains; some tendon/joint benefit. Counts toward protein.",
     "evidence": "skin-elasticity meta-analyses; tendon trials",
     "dose": "10–15 g/day with vitamin C",
     "monitor": ["skin_assessment"], "contra": [], "interactions": [],
     "triggers": {"goals": ["skin", "muscle"], "biomarkers": {}},
     "caution": "Modest cosmetic/joint effect; not a systemic anti-aging agent."},
]

_BY_ID = {x["id"]: x for x in INTERVENTIONS}

# tier by how ready the evidence is to act on — how the UI/doctor should frame it
TIER = {"lifestyle": "foundation", "consumer_supplement": "optional", "otc": "optional",
        "approved_drug": "clinical", "off_label": "experimental", "investigational": "experimental",
        "unapproved": "experimental", "hormone": "clinical"}


def _cmp(op: str, v: float, thr: float) -> bool:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return False
    return (v < thr) if op == "<" else (v > thr) if op == ">" else False


def _matches(iv: dict, profile: dict, biomarkers: dict) -> tuple[bool, list[str]]:
    """Does this intervention fit the person's goals / biomarkers / age / sex? Returns (fit, reasons)."""
    t = iv.get("triggers", {})
    reasons: list[str] = []
    # age / sex gates first (a min_age of 99 is our "do not surface proactively" sentinel)
    age = profile.get("age")
    if t.get("min_age") and (age is None or age < t["min_age"]):
        if t["min_age"] >= 99:
            return False, []
        return False, []
    if t.get("sex") and profile.get("sex") and str(profile["sex"]).upper()[:1] != t["sex"]:
        return False, []
    goals = {g.lower() for g in profile.get("goals", [])}
    gmatch = goals & set(t.get("goals", []))
    for g in gmatch:
        reasons.append(f"goal:{g}")
    # biomarker triggers
    for mk, (op, thr) in (t.get("biomarkers") or {}).items():
        val = biomarkers.get(mk)
        if val is not None and _cmp(op, val, thr):
            reasons.append(f"{mk}{op}{thr} (={val})")
    return (len(reasons) > 0), reasons


def _safety(iv: dict, profile: dict) -> tuple[bool, list[str]]:
    """Hard-coded contraindication + interaction screen. Returns (blocked, flags)."""
    conditions = {c.lower() for c in profile.get("conditions", [])}
    meds = {m.lower() for m in profile.get("medications", [])}
    devices = {d.lower() for d in profile.get("devices", [])}
    flags, blocked = [], False
    haystack = conditions | devices
    for c in iv.get("contra", []):
        head = c.lower().split("(")[0].strip()
        # "prostate/breast cancer" -> match on "prostate" OR "breast cancer" (err toward blocking)
        tokens = [t.strip() for t in head.split("/") if t.strip()]
        if any(tok and tok in cond for cond in haystack for tok in tokens):
            flags.append(f"contraindicated: {c}")
            blocked = True
    hits = [m for m in iv.get("interactions", []) if any(m in med for med in meds)]
    if hits:
        flags.append("interaction: " + ", ".join(hits) + " — clinician review / separate timing")
    return blocked, flags


def recommend(profile: dict | None = None, biomarkers: dict | None = None,
              include_experimental: bool = True, max_per_tier: int = 8) -> dict:
    """Steer a person to the right longevity interventions.

    profile: {age, sex, goals[], conditions[], medications[], devices[]}
    biomarkers: {vo2max, hba1c, vitamin_d_25oh, crp_mgL, trig, almi, total_testosterone, ...}

    Returns evidence-graded, safety-screened candidates grouped into tiers:
      foundation  (lifestyle — do these first, strongest evidence)
      clinical    (approved drugs/hormones — for an indication, prescriber-led)
      optional    (consumer supplements — biomarker-driven, mostly biomarker-level benefit)
      experimental(off-label/investigational/unapproved — informed-consent, trial-grade, clinician-only)
    """
    profile = profile or {}
    biomarkers = biomarkers or {}
    tiers: dict[str, list] = {"foundation": [], "clinical": [], "optional": [], "experimental": []}
    blocked_out = []

    for iv in INTERVENTIONS:
        fit, reasons = _matches(iv, profile, biomarkers)
        if not fit:
            continue
        tier = TIER.get(iv["status"], "optional")
        if iv["category"] == "hormone":
            tier = "clinical"
        if tier == "experimental" and not include_experimental:
            continue
        blocked, flags = _safety(iv, profile)
        item = {"id": iv["id"], "name": iv["name"], "category": iv["category"], "status": iv["status"],
                "grade": iv["grade"], "scope": iv["scope"], "why": reasons,
                "mechanism": iv["mechanism"], "hallmarks": [HALLMARKS[h] for h in iv["hallmarks"]],
                "effect": iv["effect"], "dose": iv["dose"], "monitor": iv["monitor"],
                "caution": iv["caution"], "safety_flags": flags,
                "doctor_gate": iv["status"] in ("approved_drug", "off_label", "investigational", "unapproved") or iv["category"] == "hormone"}
        if blocked:
            blocked_out.append({"id": iv["id"], "name": iv["name"], "blocked_by": flags})
            continue
        tiers[tier].append(item)

    # rank within each tier by evidence grade, then trim
    for k in tiers:
        tiers[k].sort(key=lambda r: GRADE_ORDER[r["grade"]])
        tiers[k] = tiers[k][:max_per_tier]

    return {
        "tiers": tiers,
        "blocked_by_contraindication": blocked_out,
        "ordering": ["foundation", "clinical", "optional", "experimental"],
        "doctor_gate": {"status": "pending_validation",
                        "message": "Every clinical/experimental item needs a prescriber. Nothing ships to the member until a clinician validates it.",
                        "n_clinical": len(tiers["clinical"]) + len(tiers["experimental"])},
        "disclaimer": "Decision-support, not prescription. No item here has proven HUMAN lifespan extension; grades "
                      "describe the evidence for the stated SCOPE (often a biomarker, not an outcome). "
                      "Foundation (lifestyle) has the strongest evidence and the lowest risk — do it first.",
    }


def design_trial(intervention_id: str, profile: dict | None = None, goal_markers: list | None = None) -> dict:
    """Build a proper n-of-1 / self-experiment protocol for one intervention on one person — so a doctor or
    centre runs a real, interpretable trial instead of a vibe. Baseline → defined course → retest, with the
    tracked markers, duration from the intervention's own retest cadence, stopping rules and a response rule."""
    iv = _BY_ID.get(intervention_id)
    if not iv:
        return {"error": f"unknown intervention '{intervention_id}'"}
    profile = profile or {}
    markers = goal_markers or iv["monitor"] or ["subjective_wellbeing"]
    # duration heuristic by category — biology needs time; drugs/hormones monitored sooner for safety
    weeks = {"protocol": 12, "supplement": 12, "senolytic": 16, "drug": 12, "hormone": 12, "peptide": 8}.get(iv["category"], 12)
    blocked, flags = _safety(iv, profile)
    return {
        "intervention": {"id": iv["id"], "name": iv["name"], "status": iv["status"], "grade": iv["grade"], "scope": iv["scope"]},
        "eligible": not blocked,
        "safety_flags": flags,
        "design": "single-subject (n-of-1), own-baseline controlled; where feasible add a washout + re-challenge to confirm",
        "primary_markers": markers,
        "baseline": {"capture": markers + ["symptoms", "side_effects"],
                     "repeats": "2 baseline measurements 1–2 weeks apart to pin variability before starting"},
        "intervention_arm": {"dose": iv["dose"], "duration_weeks": weeks,
                             "adherence": "log daily; a result is only interpretable with ≥80% adherence"},
        "washout_rechallenge": ("recommended — stop for 4 weeks then re-start to confirm the signal is real"
                                if iv["category"] in ("supplement", "protocol") else
                                "only under clinician direction (do not self-stop a prescribed drug/hormone)"),
        "retest_at_weeks": weeks,
        "response_rule": f"call it a RESPONSE if ≥half of {markers} move in the beneficial direction beyond their "
                         f"baseline variability AND no stopping rule triggered; otherwise NO-SIGNAL and deprescribe",
        "stopping_rules": ["any serious adverse event", "clinically significant lab shift",
                           *([f"safety flag: {f}" for f in flags] if flags else [])],
        "doctor_gate": iv["status"] in ("approved_drug", "off_label", "investigational", "unapproved") or iv["category"] == "hormone",
        "feeds": "results recalibrate this member's plan and roll up (de-identified) into centre priors — the same n-of-1 loop as modalities/supplements",
        "disclaimer": "An n-of-1 trial shows what happens in THIS person, not population efficacy. Clinician-"
                      "supervised for anything beyond lifestyle/consumer supplements.",
    }


def lookup(intervention_id: str) -> dict:
    return _BY_ID.get(intervention_id) or {"error": f"unknown intervention '{intervention_id}'"}


def corpus_summary() -> dict:
    """Counts by category and grade — a quick audit of the knowledge base."""
    from collections import Counter
    cat = Counter(x["category"] for x in INTERVENTIONS)
    grade = Counter(x["grade"] for x in INTERVENTIONS)
    status = Counter(x["status"] for x in INTERVENTIONS)
    return {"total": len(INTERVENTIONS), "by_category": dict(cat), "by_grade": dict(grade), "by_status": dict(status)}


if __name__ == "__main__":
    import json
    print("== corpus ==")
    print(json.dumps(corpus_summary(), indent=2))
    print("\n== recommend: 46M, goals longevity+muscle+metabolic, low VO2max + prediabetic + low vit D, on warfarin ==")
    prof = {"age": 46, "sex": "M", "goals": ["longevity", "muscle", "metabolic"],
            "conditions": [], "medications": ["warfarin"], "devices": []}
    bm = {"vo2max": 34, "hba1c": 5.9, "vitamin_d_25oh": 22, "trig": 180, "almi": 6.8, "total_testosterone": 280}
    out = recommend(prof, bm)
    for tier in out["ordering"]:
        print(f"\n[{tier}]")
        for r in out["tiers"][tier]:
            print(f"  {r['grade']}  {r['name']:42s} why={r['why']}  flags={r['safety_flags']}")
    print("\nblocked:", [b["name"] for b in out["blocked_by_contraindication"]])
    print("\n== n-of-1 trial: rapamycin for this person ==")
    print(json.dumps(design_trial("rapamycin", prof), indent=2))
