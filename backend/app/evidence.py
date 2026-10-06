"""Curated evidence library: the landmark papers / guidelines behind each rule, marker and method.

Used by Sinc's Deep Research mode and the Open Methods sheet. Each entry: short cite + finding in one line.
"""

REFS = {
    "levine2018": ("Levine ME et al. An epigenetic biomarker of aging for lifespan and healthspan. Aging 2018;10:573-591.",
                   "PhenoAge from 9 blood markers predicts mortality beyond chronological age."),
    "belsky2022": ("Belsky DW et al. DunedinPACE, a DNA methylation biomarker of the pace of aging. eLife 2022;11:e73420.",
                   "Pace of ageing from one blood test; faster pace predicts morbidity and mortality."),
    "lu2019": ("Lu AT et al. DNA methylation GrimAge strongly predicts lifespan and healthspan. Aging 2019;11:303-327.",
               "GrimAge outperforms earlier clocks for time-to-death."),
    "oh2023": ("Oh HS-H et al. Organ aging signatures in the plasma proteome track health and disease. Nature 2023;624:164-172.",
               "Plasma-protein organ age gaps predict organ-specific disease."),
    "greenland2018": ("Greenland P et al. Coronary calcium score and cardiovascular risk. J Am Coll Cardiol 2018;72:434-447.",
                      "CAC is the strongest single predictor of coronary events in asymptomatic adults; CAC 0 confers low short-term risk."),
    "sniderman2019": ("Sniderman AD et al. Apolipoprotein B particles and cardiovascular disease. JAMA Cardiol 2019;4:1287-1295.",
                      "ApoB counts atherogenic particles and is a better risk marker than LDL-C."),
    "kronenberg2022": ("Kronenberg F et al. Lipoprotein(a) in atherosclerotic cardiovascular disease and aortic stenosis: EAS consensus. "
                       "Eur Heart J 2022;43:3925-3946.", "Lp(a) is a largely genetic, causal risk factor; measure once in adulthood."),
    "ridker2003": ("Ridker PM. Clinical application of C-reactive protein for cardiovascular disease detection and prevention. "
                   "Circulation 2003;107:363-369.", "hs-CRP < 1, 1–3, > 3 mg/L define low, average and high vascular risk."),
    "khan2024": ("Khan SS et al. Development and validation of the AHA PREVENT equations. Circulation 2024;149:430-449.",
                 "10- and 30-year CVD risk adding eGFR and BMI, without race."),
    "mandsager2018": ("Mandsager K et al. Association of cardiorespiratory fitness with long-term mortality. JAMA Netw Open "
                      "2018;1:e183605.", "Low fitness carried mortality risk comparable to or greater than smoking or diabetes."),
    "wisloff2007": ("Wisløff U et al. Superior cardiovascular effect of aerobic interval training. Circulation 2007;115:3086-3094.",
                    "4×4 interval training raised VO2 max more than moderate continuous exercise."),
    "leong2015": ("Leong DP et al. Prognostic value of grip strength: PURE study. Lancet 2015;386:266-273.",
                  "Each 5 kg lower grip strength was associated with higher all-cause and cardiovascular mortality."),
    "ewgsop2": ("Cruz-Jentoft AJ et al. Sarcopenia: revised European consensus (EWGSOP2). Age Ageing 2019;48:16-31.",
                "Defines low muscle strength and mass thresholds, including ALMI cut-offs."),
    "neeland2019": ("Neeland IJ et al. Visceral and ectopic fat, atherosclerosis, and cardiometabolic disease. Lancet Diabetes "
                    "Endocrinol 2019;7:715-725.", "Visceral and liver fat drive insulin resistance and cardiometabolic risk."),
    "sterling2006": ("Sterling RK et al. Development of a simple noninvasive index to predict significant fibrosis (FIB-4). "
                     "Hepatology 2006;43:1317-1325.", "FIB-4 < 1.3 makes advanced fibrosis unlikely."),
    "rinella2023": ("Rinella ME et al. A multisociety Delphi consensus statement on new fatty liver disease nomenclature. "
                    "J Hepatol 2023;79:1542-1556.", "Defines MASLD: hepatic steatosis plus a cardiometabolic risk factor."),
    "tang2013": ("Tang A et al. Accuracy of MR imaging-estimated proton density fat fraction for classification of hepatic steatosis. "
                 "Radiology 2013;267:422-431.", "MRI-PDFF ≥ 5–6.4% identifies steatosis; grade thresholds near 17% and 22%."),
    "benjafield2019": ("Benjafield AV et al. Estimation of the global prevalence and burden of obstructive sleep apnoea. Lancet Respir "
                       "Med 2019;7:687-698.", "Nearly 1 billion adults have OSA; most are undiagnosed."),
    "debette2010": ("Debette S, Markus HS. The clinical importance of white matter hyperintensities on brain MRI. BMJ "
                    "2010;341:c3666.", "WMH are associated with stroke, dementia and death."),
    "palmqvist2020": ("Palmqvist S et al. Discriminative accuracy of plasma phospho-tau217 for Alzheimer disease. JAMA "
                      "2020;324:772-781.", "Plasma p-tau217 distinguished Alzheimer's from other neurodegenerative disease."),
    "frosst1995": ("Frosst P et al. A candidate genetic risk factor for vascular disease: a common mutation in MTHFR. Nat Genet "
                   "1995;10:111-113.", "MTHFR C677T reduces enzyme activity and raises homocysteine."),
    "harris2004": ("Harris WS, von Schacky C. The Omega-3 Index: a new risk factor for death from coronary heart disease? Prev Med "
                   "2004;39:212-220.", "An omega-3 index ≥ 8% was associated with the lowest coronary risk."),
    "inker2021": ("Inker LA et al. New creatinine- and cystatin C-based equations to estimate GFR without race. N Engl J Med "
                  "2021;385:1737-1749.", "CKD-EPI 2021; combining creatinine with cystatin C is most accurate."),
    "kdigo2024": ("KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of CKD. Kidney Int 2024;105(4S):S117-S314.",
                  "CKD staging by eGFR (G1–G5) and albuminuria (A1–A3)."),
    "ada2024": ("American Diabetes Association. Standards of Care in Diabetes—2024. Diabetes Care 2024;47(Suppl 1).",
                "HbA1c 5.7–6.4% defines prediabetes; ≥ 6.5% diabetes."),
    "pietila2018": ("Pietilä J et al. Acute effect of alcohol intake on cardiovascular autonomic regulation during the first hours of "
                    "sleep. JMIR Ment Health 2018;5:e23.", "Alcohol dose-dependently lowered overnight HRV in a large wearable cohort."),
    "schrag2023": ("Schrag D et al. Blood-based tests for multicancer early detection (PATHFINDER). Lancet 2023;402:1251-1260.",
                   "MCED found cancers missed by standard screening; a negative result does not rule out cancer."),
}

RULE_REFS = {
    "cac_apob": ["greenland2018", "sniderman2019", "kronenberg2022"],
    "cac_zero": ["greenland2018", "sniderman2019"],
    "apoe_lipids": ["sniderman2019", "kronenberg2022"],
    "masld": ["rinella2023", "tang2013", "sterling2006"],
    "liver": ["rinella2023", "sterling2006"],
    "vat_metabolic": ["neeland2019"],
    "glycaemia_genetics": ["ada2024"],
    "gut_inflammation": ["ridker2003"],
    "osa": ["benjafield2019"],
    "brain_vascular": ["debette2010", "palmqvist2020"],
    "hcy_mthfr": ["frosst1995"],
    "omega3": ["harris2004"],
    "fitness_reserve": ["mandsager2018", "wisloff2007", "leong2015"],
    "organ_age": ["oh2023"],
    "pace": ["belsky2022", "lu2019", "levine2018"],
    "egfr_discord": ["inker2021", "kdigo2024"],
    "kidney_ok": ["inker2021", "kdigo2024"],
}

MARKER_REFS = {
    "apob": ["sniderman2019"], "lpa": ["kronenberg2022"], "hscrp": ["ridker2003"], "cac": ["greenland2018"],
    "vo2max_lab": ["mandsager2018"], "grip": ["leong2015"], "almi": ["ewgsop2"], "vat_area": ["neeland2019"],
    "liver_pdff": ["tang2013"], "ahi": ["benjafield2019"], "wmh_fazekas": ["debette2010"], "ptau217": ["palmqvist2020"],
    "homocysteine": ["frosst1995"], "omega3_index": ["harris2004"], "cystatin_c": ["inker2021"], "egfr": ["inker2021", "kdigo2024"],
    "uacr": ["kdigo2024"], "hba1c": ["ada2024"], "dunedinpace": ["belsky2022"], "grimage": ["lu2019"], "mced": ["schrag2023"],
}

EVENT_REFS = {"alcohol": ["pietila2018"]}


def cite(keys: list[str]) -> list[dict]:
    seen, out = set(), []
    for k in keys:
        if k in REFS and k not in seen:
            seen.add(k)
            out.append({"key": k, "citation": REFS[k][0], "finding": REFS[k][1]})
    return out
