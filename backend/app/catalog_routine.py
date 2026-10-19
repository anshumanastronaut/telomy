"""Routine-panel markers as printed on Indian lab reports (Orange Health, Thyrocare, Dr Lal PathLabs, SRL, Metropolis):
LFT, KFT with electrolytes, CBC with indices and absolute counts, total thyroid hormones, urine chemistry. Added
2026-10-19 after the first real report parsed only 9 of ~50 values. Optimal bands are adult reference intervals
(Dacie & Lewis 12th ed. for CBC; Tietz for chemistry) unless noted; the report's own reference range always wins
when present. Format: id: (name, panel, unit, optimal_low, optimal_high, better, aliases, loinc).
"""

ROUTINE_MARKERS: dict[str, tuple] = {
    "bilirubin_total": ("Bilirubin, total", "blood", "mg/dL", 0.2, 1.2, "mid", ["bilirubin, total", "total bilirubin", "bilirubin total"], "1975-2"),
    "bilirubin_direct": ("Bilirubin, direct", "blood", "mg/dL", 0.0, 0.3, "low", ["bilirubin, direct", "direct bilirubin", "bilirubin direct", "conjugated bilirubin"], "1968-7"),
    "bilirubin_indirect": ("Bilirubin, indirect", "blood", "mg/dL", 0.1, 1.0, "mid", ["bilirubin, indirect", "indirect bilirubin", "bilirubin indirect"], "1971-1"),
    "ast_alt_ratio": ("AST/ALT ratio", "blood", "", 0.7, 1.4, "mid", ["aspartate aminotransferase/alanine", "ast/alt ratio", "sgot/sgpt ratio", "de ritis ratio"], "16325-3"),
    "total_protein": ("Total protein", "blood", "g/dL", 6.4, 8.3, "mid", ["protein, total", "total protein", "protein"], "2885-2"),
    "globulin": ("Globulin", "blood", "g/dL", 2.3, 3.5, "mid", ["globulin"], "10834-0"),
    "ag_ratio": ("Albumin/globulin ratio", "blood", "", 1.1, 2.0, "mid", ["albumin/globulin", "a/g ratio", "albumin globulin ratio"], "1759-0"),
    "urea": ("Urea", "blood", "mg/dL", 17, 43, "mid", ["urea", "blood urea", "serum urea"], "3091-6"),
    "bun": ("Blood urea nitrogen", "blood", "mg/dL", 7, 20, "mid", ["blood urea nitrogen", "bun"], "3094-0"),
    "bun_creat_ratio": ("BUN/creatinine ratio", "blood", "", 10, 20, "mid", ["blood urea nitrogen (bun)/creatinine", "blood urea nitrogen bun /creatinine", "blood urea nitrogen bun/creatinine", "blood urea nitrogen  bun /creatinine", "bun/creatinine ratio", "bun creatinine ratio"], "3097-3"),
    "phosphorus": ("Phosphorus", "blood", "mg/dL", 2.5, 4.5, "mid", ["phosphorus", "inorganic phosphorus", "phosphate"], "2777-1"),
    "chloride": ("Chloride", "blood", "mmol/L", 98, 107, "mid", ["chloride"], "2075-0"),
    "rbc": ("Red blood cells", "blood", "mill/mm³", 4.5, 5.5, "mid", ["red blood cells", "rbc count", "red blood cell count", "total rbc"], "789-8"),
    "hct": ("Haematocrit (PCV)", "blood", "%", 40, 50, "mid", ["hematocrit", "haematocrit", "packed cell volume", "pcv"], "4544-3"),
    "mch": ("MCH", "blood", "pg", 27, 32, "mid", ["mean corpuscular hemoglobin", "mean corpuscular haemoglobin", "mch"], "785-6"),
    "mchc": ("MCHC", "blood", "g/dL", 31.5, 34.5, "mid", ["mean corpuscular hemoglobin concentration", "mean corpuscular haemoglobin concentration", "mchc"], "786-4"),
    "mentzer": ("Mentzer index", "blood", "", 13, 99, "info", ["mentzer index"], ""),
    "sehgal": ("Sehgal index", "blood", "", 972, 9999, "info", ["sehgal index"], ""),
    "wbc_total": ("White blood cells", "blood", "cells/mm³", 4000, 10000, "mid", ["total white blood cell count", "total leucocyte count", "total leukocyte count", "tlc"], "6690-2"),
    "monocyte_pct": ("Monocytes", "blood", "%", 2, 10, "mid", ["monocytes"], "5905-5"),
    "eos_pct": ("Eosinophils", "blood", "%", 1, 6, "mid", ["eosinophils"], "713-8"),
    "baso_pct": ("Basophils", "blood", "%", 0, 2, "mid", ["basophils"], "706-2"),
    "anc": ("Absolute neutrophil count", "blood", "/mm³", 2000, 7000, "mid", ["absolute neutrophil count", "anc"], "751-8"),
    "alc": ("Absolute lymphocyte count", "blood", "/mm³", 1000, 3000, "mid", ["absolute lymphocyte count", "alc"], "731-0"),
    "amc": ("Absolute monocyte count", "blood", "/mm³", 200, 1000, "mid", ["absolute monocyte count", "amc"], "742-7"),
    "aec": ("Absolute eosinophil count", "blood", "/mm³", 20, 500, "mid", ["absolute eosinophil count", "aec"], "711-2"),
    "abc": ("Absolute basophil count", "blood", "/mm³", 0, 100, "mid", ["absolute basophil count", "abc"], "704-7"),
    "nlr": ("Neutrophil-lymphocyte ratio", "blood", "", 1, 3, "mid", ["neutrophil lymphocyte ratio", "neutrophil-lymphocyte ratio", "nlr"], ""),
    "plateletcrit": ("Plateletcrit", "blood", "%", 0.2, 0.5, "mid", ["platelet hematocrit", "plateletcrit", "pct"], "51637-7"),
    "mpv": ("Mean platelet volume", "blood", "fL", 7, 13, "mid", ["mean platelet volume", "mpv"], "32623-1"),
    "t3_total": ("T3, total", "hormones", "ng/mL", 0.97, 1.69, "mid", ["triiodothyronine (t3), total", "triiodothyronine  t3 , total", "triiodothyronine", "total t3", "t3, total", "t3 total"], "3053-6"),
    "t4_total": ("T4, total", "hormones", "µg/dL", 5.53, 11.0, "mid", ["thyroxine (t4), total", "thyroxine  t4 , total", "thyroxine", "total t4", "t4, total", "t4 total"], "3026-2"),
}

# Names on reports that map onto markers the catalog already has (merged into their alias lists).
EXTRA_ALIASES: dict[str, list[str]] = {
    "chol_total": ["cholesterol, total", "cholesterol total", "serum cholesterol"],
    "ast": ["aspartate aminotransferase", "aspartate transaminase"],
    "alt": ["alanine transaminase", "alanine aminotransferase"],
    "ggt": ["gamma-glutamyl transferase", "gamma glutamyl transferase", "gamma gt"],
    "alp": ["alkaline phosphatase (alp)"],
    "hemoglobin": ["hemoglobin (hb)", "hemoglobin", "haemoglobin (hb)"],
    "egfr": ["estimated glomerular filtration rate"],
    "glucose": ["glucose, random", "glucose random", "random blood sugar", "glucose, fasting", "fasting blood sugar"],
    "rdw": ["red cell distribution width"],
    "platelets": ["platelet count"],
    "mcv": ["mean corpuscular volume"],
    "tsh": ["thyroid stimulating hormone"],
    "calcium": ["calcium"],
    "u_ph": ["ph"],
    "u_sg": ["specific gravity"],
}
