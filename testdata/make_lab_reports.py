"""Generate dummy lab report PDFs (clearly marked as test data) for every diagnostic panel type.

Values are deliberately internally consistent so correlation engines have something to find:
inflammation (hs-CRP, homocysteine) + dyslipidaemia + borderline glycaemia + low vitamin D / B12,
low gut diversity, MTHFR / APOE e4 variants, accelerated pace of ageing, elevated mercury, BPA.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).parent / "lab_reports"
OUT.mkdir(exist_ok=True)

PATIENT = [
    ["Patient", "Test User (SAMPLE)", "Age / Sex", "34 Y / Male"],
    ["Patient ID", "TST-000123", "Referred by", "Self"],
]
LAB = "Sample Diagnostics (fictitious test laboratory)"
styles = getSampleStyleSheet()


def report(filename, title, collected, rows, notes, method):
    doc = SimpleDocTemplate(str(OUT / filename), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm, title=title)
    story = [
        Paragraph(f"<b>{LAB}</b>", styles["Title"]),
        Paragraph("<font color='#9B2C2C'><b>TEST DATA — NOT A REAL MEDICAL REPORT. FOR SOFTWARE TESTING ONLY.</b></font>",
                  styles["Normal"]),
        Spacer(1, 6),
        Paragraph(f"<b>{title}</b>", styles["Heading2"]),
    ]
    meta = PATIENT + [["Collected", collected, "Reported", collected], ["Method", method, "Sample", "See test"]]
    t = Table(meta, colWidths=[28 * mm, 60 * mm, 28 * mm, 60 * mm])
    t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8.5), ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                           ("TEXTCOLOR", (2, 0), (2, -1), colors.grey)]))
    story += [t, Spacer(1, 8)]

    data = [["Test", "Result", "Unit", "Reference range", "Flag"]] + rows
    tbl = Table(data, colWidths=[62 * mm, 22 * mm, 24 * mm, 46 * mm, 18 * mm], repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F5C4E")),
             ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("FONTSIZE", (0, 0), (-1, -1), 8.5),
             ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1CFC5")),
             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0EDE6")])]
    for i, r in enumerate(rows, start=1):
        if r[4] in ("H", "L", "HIGH", "LOW", "DETECTED", "RISK"):
            style.append(("TEXTCOLOR", (1, i), (1, i), colors.HexColor("#9B2C2C")))
            style.append(("TEXTCOLOR", (4, i), (4, i), colors.HexColor("#9B2C2C")))
    tbl.setStyle(TableStyle(style))
    story += [tbl, Spacer(1, 10), Paragraph("<b>Interpretation / notes</b>", styles["Heading4"])]
    story += [Paragraph(n, styles["Normal"]) for n in notes]
    story += [Spacer(1, 14), Paragraph("Electronically generated sample report. Fictitious laboratory and patient.",
                                       styles["Italic"])]
    doc.build(story)


BLOOD = lambda d: [  # noqa: E731  (d = later report)
    ["Haemoglobin", "14.6" if d else "14.9", "g/dL", "13.0 – 17.0", ""],
    ["Ferritin", "48" if d else "52", "ng/mL", "30 – 400", ""],
    ["Fasting glucose", "104" if d else "98", "mg/dL", "70 – 99", "H" if d else ""],
    ["HbA1c", "5.9" if d else "5.7", "%", "4.0 – 5.6", "H"],
    ["Fasting insulin", "14.2" if d else "11.8", "µIU/mL", "2.6 – 24.9", ""],
    ["HOMA-IR", "3.65" if d else "2.85", "", "< 2.5", "H"],
    ["Total cholesterol", "228" if d else "214", "mg/dL", "< 200", "H"],
    ["LDL cholesterol", "148" if d else "136", "mg/dL", "< 100", "H"],
    ["HDL cholesterol", "38" if d else "41", "mg/dL", "> 40", "L" if d else ""],
    ["Triglycerides", "182" if d else "164", "mg/dL", "< 150", "H"],
    ["Apolipoprotein B", "121" if d else "112", "mg/dL", "< 90", "H"],
    ["Lipoprotein(a)", "38", "mg/dL", "< 30", "H"],
    ["hs-CRP", "3.4" if d else "2.1", "mg/L", "< 1.0", "H"],
    ["Homocysteine", "16.8" if d else "15.2", "µmol/L", "5 – 12", "H"],
    ["Vitamin D (25-OH)", "22" if d else "18", "ng/mL", "30 – 100", "L"],
    ["Vitamin B12", "212" if d else "236", "pg/mL", "211 – 911", ""],
    ["TSH", "3.1" if d else "2.8", "µIU/mL", "0.4 – 4.0", ""],
    ["Free T3", "2.9", "pg/mL", "2.3 – 4.2", ""],
    ["Testosterone, total", "412" if d else "438", "ng/dL", "264 – 916", ""],
    ["Cortisol (AM)", "19.8" if d else "17.4", "µg/dL", "6.2 – 19.4", "H" if d else ""],
    ["ALT (SGPT)", "46" if d else "39", "U/L", "< 41", "H" if d else ""],
    ["AST (SGOT)", "41" if d else "33", "U/L", "< 40", "H" if d else ""],
    ["GGT", "58" if d else "44", "U/L", "< 55", "H" if d else ""],
    ["Creatinine", "0.98", "mg/dL", "0.7 – 1.3", ""],
    ["eGFR", "102", "mL/min/1.73m²", "> 90", ""],
    ["Uric acid", "7.4" if d else "6.9", "mg/dL", "3.5 – 7.2", "H" if d else ""],
    ["WBC", "7.8", "10³/µL", "4.0 – 11.0", ""],
    ["Lymphocytes", "29", "%", "20 – 40", ""],
    ["Neutrophils", "62", "%", "40 – 75", ""],
    ["Platelet count", "232" if d else "248", "10³/µL", "150 – 410", ""],
    ["Albumin", "4.5", "g/dL", "3.5 – 5.2", ""],
    ["Alkaline phosphatase", "74", "U/L", "40 – 129", ""],
    ["MCV", "92", "fL", "80 – 100", ""],
    ["RDW", "13.1", "%", "11.5 – 14.5", ""],
]

report("01_Standard_Blood_Panel_2026-07-02.pdf", "Comprehensive Metabolic, Lipid & Hormone Panel",
       "02-Jul-2026 08:10", BLOOD(False),
       ["Borderline glycaemic markers with elevated HOMA-IR.", "Atherogenic lipid pattern (LDL, ApoB, Lp(a)).",
        "Low-grade inflammation (hs-CRP, homocysteine). Vitamin D insufficient."],
       "Chemiluminescence / photometry")
report("02_Standard_Blood_Panel_2026-10-01.pdf", "Comprehensive Metabolic, Lipid & Hormone Panel",
       "01-Oct-2026 07:55", BLOOD(True),
       ["Compared with July: HbA1c 5.7 → 5.9 %, hs-CRP 2.1 → 3.4 mg/L, ALT and GGT newly above range.",
        "Vitamin D improved 18 → 22 ng/mL but remains insufficient.", "Recommend clinical correlation."],
       "Chemiluminescence / photometry")

report("03_Gut_Microbiome_2026-09-18.pdf", "Gut Microbiome — 16S rRNA + Functional Markers",
       "18-Sep-2026", [
           ["Shannon diversity index", "2.9", "", "3.5 – 5.0", "L"],
           ["Bacteroidetes", "38", "%", "30 – 60", ""],
           ["Firmicutes", "54", "%", "30 – 55", ""],
           ["Firmicutes/Bacteroidetes ratio", "1.42", "", "0.5 – 1.2", "H"],
           ["Actinobacteria", "4", "%", "2 – 10", ""],
           ["Proteobacteria", "8.5", "%", "< 6", "H"],
           ["Akkermansia muciniphila", "0.3", "%", "1 – 5", "L"],
           ["Faecalibacterium prausnitzii", "2.1", "%", "5 – 15", "L"],
           ["Bifidobacterium spp.", "1.8", "%", "1 – 6", ""],
           ["Lactobacillus spp.", "0.4", "%", "0.1 – 2", ""],
           ["Butyrate producers (total)", "9", "%", "15 – 30", "L"],
           ["Calprotectin", "68", "µg/g", "< 50", "H"],
           ["Zonulin (stool)", "142", "ng/mL", "< 107", "H"],
           ["Secretory IgA", "720", "µg/mL", "510 – 2010", ""],
           ["H. pylori antigen", "Not detected", "", "Not detected", ""],
           ["Candida spp.", "Detected (low)", "", "Not detected", "DETECTED"],
           ["Blastocystis hominis", "Not detected", "", "Not detected", ""],
       ], ["Reduced diversity with low butyrate producers and Akkermansia.",
           "Markers of mucosal inflammation and permeability mildly raised."], "16S rRNA sequencing / ELISA")

report("04_Genetic_Methylation_2026-03-11.pdf", "Genetic & Methylation SNP Panel (one-time)",
       "11-Mar-2026", [
           ["MTHFR C677T (rs1801133)", "C/T", "genotype", "C/C typical", "RISK"],
           ["MTHFR A1298C (rs1801131)", "A/A", "genotype", "A/A typical", ""],
           ["APOE (rs429358 / rs7412)", "ε3/ε4", "genotype", "ε3/ε3 typical", "RISK"],
           ["FTO (rs9939609)", "A/T", "genotype", "T/T typical", "RISK"],
           ["TCF7L2 (rs7903146)", "C/T", "genotype", "C/C typical", "RISK"],
           ["VDR Taq1 (rs731236)", "T/C", "genotype", "T/T typical", ""],
           ["COMT V158M (rs4680)", "A/A (slow)", "genotype", "G/G fast", ""],
           ["CYP1A2 (rs762551)", "A/C (slow)", "genotype", "A/A fast", ""],
           ["ACTN3 R577X (rs1815739)", "R/X", "genotype", "—", ""],
           ["SOD2 (rs4880)", "C/T", "genotype", "—", ""],
           ["FUT2 (rs601338)", "A/A (non-secretor)", "genotype", "G/G / G/A", "RISK"],
           ["9p21 CAD locus (rs10757274)", "A/G", "genotype", "A/A lower risk", "RISK"],
           ["Polygenic risk — CAD", "72nd", "percentile", "—", ""],
           ["Polygenic risk — Type 2 diabetes", "81st", "percentile", "—", "H"],
       ], ["Reduced folate cycle efficiency (MTHFR heterozygous) consistent with elevated homocysteine.",
           "APOE ε4 carrier: lipid and cognitive risk context. Genetic counselling advised."],
       "SNP microarray")

report("05_Biological_Age_2026-09-25.pdf", "Biological Age — Epigenetic Clocks & Pace of Ageing",
       "25-Sep-2026", [
           ["Chronological age", "34.2", "years", "—", ""],
           ["PhenoAge (Levine 2018)", "37.9", "years", "≤ chronological", "H"],
           ["GrimAge v2", "38.6", "years", "≤ chronological", "H"],
           ["Horvath clock (2013)", "35.1", "years", "≤ chronological", ""],
           ["DunedinPACE", "1.12", "years/year", "< 1.00", "H"],
           ["Telomere length (qPCR, T/S ratio)", "0.92", "T/S", "0.95 – 1.40", "L"],
           ["Immune age (IEAA)", "+2.1", "years", "≤ 0", "H"],
           ["Inflammation clock (CRP-methylation)", "+1.8", "SD", "< 0", "H"],
       ], ["Biological age estimates exceed chronological age by 1–4 years; pace of ageing 12 % above average.",
           "Pattern is commonly associated with inflammation, insulin resistance and poor sleep."],
       "Illumina EPIC methylation array / qPCR")

report("06_Heavy_Metals_2026-08-14.pdf", "Heavy Metals — Provoked Urine (6 h, DMSA)",
       "14-Aug-2026", [
           ["Lead (Pb)", "3.8", "µg/g creat", "< 2.0", "H"],
           ["Mercury (Hg)", "6.4", "µg/g creat", "< 3.0", "H"],
           ["Arsenic (As, total)", "42", "µg/g creat", "< 50", ""],
           ["Cadmium (Cd)", "0.9", "µg/g creat", "< 1.0", ""],
           ["Aluminium (Al)", "21", "µg/g creat", "< 35", ""],
           ["Thallium (Tl)", "0.3", "µg/g creat", "< 0.5", ""],
           ["Nickel (Ni)", "5.1", "µg/g creat", "< 8", ""],
           ["Creatinine", "1.1", "g/L", "0.3 – 3.0", ""],
       ], ["Mercury above reference — common with frequent large-predatory-fish intake.",
           "Lead mildly elevated. Provoked testing interpretation requires clinician review."],
       "ICP-MS")

report("07_Environmental_Toxins_2026-08-14.pdf", "Environmental Toxins — Mycotoxins, Pesticides, Plasticisers",
       "14-Aug-2026", [
           ["Bisphenol A (BPA)", "4.6", "µg/g creat", "< 2.1", "H"],
           ["Mono-ethyl phthalate (MEP)", "118", "µg/g creat", "< 85", "H"],
           ["MEHP (phthalate)", "6.2", "µg/g creat", "< 7.5", ""],
           ["Glyphosate", "1.9", "µg/g creat", "< 1.0", "H"],
           ["2,4-D (herbicide)", "0.4", "µg/g creat", "< 0.9", ""],
           ["Organophosphate (DMP)", "9.8", "µg/g creat", "< 12", ""],
           ["Ochratoxin A", "4.1", "ng/g creat", "< 7.5", ""],
           ["Aflatoxin M1", "0.6", "ng/g creat", "< 0.5", "H"],
           ["Zearalenone", "0.3", "ng/g creat", "< 0.5", ""],
           ["Perchlorate", "3.9", "µg/g creat", "< 8.2", ""],
           ["Benzene metabolite (PGO)", "260", "µg/g creat", "< 400", ""],
       ], ["Plasticiser exposure (BPA, MEP) above reference; consider food/water container sources.",
           "Low-level glyphosate and aflatoxin M1 detected."], "LC-MS/MS")

report("08_Advanced_Panel_2026-09-30.pdf", "Advanced Cardio-Renal, Neuro & Hormone Panel", "30-Sep-2026", [
    ["Apolipoprotein A1", "128", "mg/dL", "> 120", ""],
    ["LDL particle number", "1680", "nmol/L", "< 1000", "H"],
    ["Interleukin-6", "3.1", "pg/mL", "< 2.0", "H"],
    ["GlycA", "455", "µmol/L", "< 400", "H"],
    ["NT-proBNP", "48", "pg/mL", "< 125", ""],
    ["hs-Troponin T", "5", "ng/L", "< 14", ""],
    ["Cystatin C", "0.82", "mg/L", "0.6 – 1.0", ""],
    ["Urine albumin/creatinine ratio", "14", "mg/g", "< 30", ""],
    ["Omega-3 index", "4.6", "%", "> 8", "L"],
    ["p-tau217", "0.21", "pg/mL", "< 0.40", ""],
    ["Neurofilament light (NfL)", "7.8", "pg/mL", "< 10", ""],
    ["IGF-1", "168", "ng/mL", "88 – 246", ""],
    ["SHBG", "28", "nmol/L", "17 – 56", ""],
    ["Free testosterone", "96", "pg/mL", "90 – 300", ""],
    ["DHEA-S", "310", "µg/dL", "160 – 450", ""],
    ["Methylmalonic acid", "290", "nmol/L", "< 270", "H"],
], ["Atherogenic particle burden (LDL-P) and inflammatory markers (IL-6, GlycA) are raised.",
    "Omega-3 index is low. MMA is mildly raised, consistent with low-normal B12."], "NMR spectroscopy / immunoassay / Simoa")

report("09_CPET_VO2max_2026-09-12.pdf", "Cardiopulmonary Exercise Test (CPET) and Functional Assessment", "12-Sep-2026", [
    ["VO2 max (CPET)", "41.2", "mL/kg/min", "> 42 (age/sex 50th pct)", "L"],
    ["VT1 heart rate", "138", "bpm", "—", ""],
    ["VT2 heart rate", "166", "bpm", "—", ""],
    ["Peak heart rate", "188", "bpm", "—", ""],
    ["Heart-rate recovery (1 min)", "21", "bpm", "> 18", ""],
    ["Peak RER", "1.16", "", "> 1.10 (maximal effort)", ""],
    ["Grip strength (best hand)", "46", "kg", "> 27", ""],
    ["Gait speed", "1.35", "m/s", "> 1.0", ""],
    ["30-s sit-to-stand", "22", "reps", "> 15", ""],
    ["Single-leg stance (eyes closed)", "8", "s", "> 10", "L"],
], ["Maximal test (RER 1.16). VO2 max is just below the 50th percentile for age and sex.",
    "Zone 2 training ceiling ≈ 138 bpm (VT1). Balance is below target."], "Breath-by-breath gas analysis, treadmill ramp")

report("10_DEXA_2026-07-20.pdf", "DEXA Body Composition and Bone Density (DXA)", "20-Jul-2026", [
    ["Total body fat (DEXA)", "24.1", "%", "10 – 20", "H"],
    ["Visceral fat area (DEXA)", "118", "cm²", "< 100", "H"],
    ["Appendicular lean mass index", "8.1", "kg/m²", "> 7.0", ""],
    ["Fat mass index", "6.4", "kg/m²", "3 – 6", "H"],
    ["BMD T-score (lumbar spine)", "0.4", "SD", "> -1.0", ""],
    ["BMD T-score (total hip)", "0.2", "SD", "> -1.0", ""],
], ["Visceral fat above target. Lean mass adequate; ALMI below the 75th-percentile longevity target.",
    "Bone density normal."], "Hologic Horizon DXA")

report("11_BCA_2026-09-28.pdf", "Body Composition Analysis (BCA, bioimpedance)", "28-Sep-2026", [
    ["Body fat (BCA)", "21.5", "%", "10 – 20", "H"],
    ["Skeletal muscle mass (BCA)", "34.2", "kg", "30 – 40", ""],
    ["Visceral fat level (BCA)", "11", "level", "1 – 9", "H"],
    ["Phase angle (BCA)", "6.3", "°", "> 5.5", ""],
    ["ECW/TBW ratio (BCA)", "0.385", "", "0.36 – 0.39", ""],
    ["Basal metabolic rate (BCA)", "1720", "kcal", "—", ""],
], ["Segmental multi-frequency BIA. Hydration within range."], "InBody 770 (multi-frequency BIA)")

report("12_Cardiac_CT_2026-08-02.pdf", "Cardiac CT: Coronary Calcium Score and CT Coronary Angiography (computed tomography)", "02-Aug-2026", [
    ["Coronary artery calcium (Agatston)", "38", "AU", "0", "H"],
    ["CAC percentile (MESA)", "78", "percentile", "< 50", "H"],
    ["CAD-RADS (CCTA)", "1", "grade", "0", "H"],
    ["Total plaque volume (CCTA)", "46", "mm³", "< 20", "H"],
    ["Liver attenuation (CT)", "44", "HU", "> 50", "L"],
    ["Epicardial fat volume", "112", "cm³", "< 100", "H"],
], ["IMPRESSION: Mild calcified plaque in the proximal LAD (CAC 38, 78th percentile for age/sex/ethnicity).",
    "CCTA: CAD-RADS 1, minimal non-obstructive mixed plaque. Hepatic attenuation suggests steatosis."], "Dual-source CT, prospective ECG gating")

report("13_MRI_2026-08-30.pdf", "Magnetic Resonance Imaging (MRI): Whole-body, Brain and Liver", "30-Aug-2026", [
    ["Liver fat (MRI-PDFF)", "9.4", "%", "< 5", "H"],
    ["White-matter hyperintensities (Fazekas)", "1", "grade", "0", "H"],
    ["Brain-age gap (MRI)", "1.6", "years", "≤ 0", "H"],
    ["Hippocampal volume percentile", "58", "percentile", "> 25", ""],
    ["LV ejection fraction", "61", "%", "55 – 70", ""],
    ["Whole-body MRI incidental findings", "1", "count", "0", "H"],
], ["IMPRESSION: Mild hepatic steatosis (PDFF 9.4 %). Few punctate white-matter hyperintensities (Fazekas 1).",
    "Incidental: 8 mm simple left renal cyst (Bosniak I), no follow-up needed."], "3T MRI; MRI-PDFF; FreeSurfer volumetrics")

report("14_Sleep_Study_Screening_2026-09-05.pdf", "Home Sleep Study and Screening Tests", "05-Sep-2026", [
    ["Apnoea-hypopnoea index", "13.2", "events/h", "< 5", "H"],
    ["Oxygen desaturation index", "11.0", "events/h", "< 5", "H"],
    ["Lowest SpO2 (sleep)", "86", "%", "> 90", "L"],
    ["Carotid IMT (mean)", "0.66", "mm", "< 0.70", ""],
    ["Carotid plaque", "Not detected", "", "Not detected", ""],
    ["Multi-cancer early detection (MCED)", "Not detected", "", "Not detected", ""],
    ["Faecal immunochemical test (FIT)", "Not detected", "", "Not detected", ""],
], ["Mild obstructive sleep apnoea, worse supine. No cancer signal detected on MCED (screening test, not diagnostic)."],
   "Type III home sleep test; carotid ultrasound; cfDNA methylation MCED; FIT")

report("15_Proteomic_Organ_Age_2026-09-25.pdf", "Proteomic Organ Age (plasma proteomics, 3,000 proteins)", "25-Sep-2026", [
    ["Heart age gap", "3.1", "years", "≤ 0", "H"],
    ["Brain age gap", "-1.2", "years", "≤ 0", ""],
    ["Liver age gap", "4.4", "years", "≤ 0", "H"],
    ["Kidney age gap", "0.8", "years", "≤ 0", "H"],
    ["Immune age gap", "2.5", "years", "≤ 0", "H"],
    ["Artery age gap", "2.9", "years", "≤ 0", "H"],
    ["Muscle age gap", "-0.6", "years", "≤ 0", ""],
    ["Global proteomic age gap", "1.9", "years", "≤ 0", "H"],
], ["Organ-specific ageing is fastest in liver, heart and artery. Research-grade test; interpret with clinical data."],
   "Olink Explore 3072 / organ-specific aging models")

print("\n".join(sorted(p.name for p in OUT.iterdir())))
