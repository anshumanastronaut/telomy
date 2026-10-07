"""Biomarker catalogue: canonical ids, aliases (for lab-PDF matching), panels, optimal ranges.

`better` says which direction is desirable ("low", "high", "mid") so trends can be judged.
Optimal ranges are longevity-oriented targets, distinct from the lab's own reference range,
which is always stored from the report itself.
"""

PANELS = {
    "blood": "Standard blood panel",
    "gut": "Gut microbiome",
    "genetic": "Genetic & methylation",
    "bioage": "Biological age",
    "metals": "Heavy metals",
    "toxins": "Environmental toxins",
}

# id: (display name, panel, unit, optimal_low, optimal_high, better, aliases, loinc)
MARKERS: dict[str, tuple] = {
    "hemoglobin": ("Haemoglobin", "blood", "g/dL", 13.5, 16.5, "mid", ["haemoglobin", "hemoglobin", "hb"], "718-7"),
    "ferritin": ("Ferritin", "blood", "ng/mL", 50, 150, "mid", ["ferritin"], "2276-4"),
    "glucose": ("Fasting glucose", "blood", "mg/dL", 72, 90, "low", ["fasting glucose", "glucose"], "1558-6"),
    "hba1c": ("HbA1c", "blood", "%", 4.6, 5.3, "low", ["hba1c", "glycated haemoglobin"], "4548-4"),
    "insulin": ("Fasting insulin", "blood", "µIU/mL", 2, 6, "low", ["fasting insulin", "insulin"], "20448-7"),
    "homa_ir": ("HOMA-IR", "blood", "", 0.5, 1.5, "low", ["homa-ir", "homa ir"], ""),
    "chol_total": ("Total cholesterol", "blood", "mg/dL", 150, 200, "low", ["total cholesterol"], "2093-3"),
    "ldl": ("LDL cholesterol", "blood", "mg/dL", 50, 100, "low", ["ldl cholesterol", "ldl"], "13457-7"),
    "hdl": ("HDL cholesterol", "blood", "mg/dL", 50, 90, "high", ["hdl cholesterol", "hdl"], "2085-9"),
    "tg": ("Triglycerides", "blood", "mg/dL", 40, 100, "low", ["triglycerides"], "2571-8"),
    "apob": ("Apolipoprotein B", "blood", "mg/dL", 40, 80, "low", ["apolipoprotein b", "apob"], "1884-6"),
    "lpa": ("Lipoprotein(a)", "blood", "mg/dL", 0, 30, "low", ["lipoprotein(a)", "lp(a)"], "10835-7"),
    "hscrp": ("hs-CRP", "blood", "mg/L", 0, 1.0, "low", ["hs-crp", "hscrp", "c-reactive protein"], "30522-7"),
    "homocysteine": ("Homocysteine", "blood", "µmol/L", 5, 9, "low", ["homocysteine"], "13965-9"),
    "vitd": ("Vitamin D (25-OH)", "blood", "ng/mL", 40, 60, "mid", ["vitamin d (25-oh)", "vitamin d", "25-oh"], "1989-3"),
    "b12": ("Vitamin B12", "blood", "pg/mL", 500, 900, "mid", ["vitamin b12", "b12"], "2132-9"),
    "tsh": ("TSH", "blood", "µIU/mL", 0.5, 2.5, "mid", ["tsh"], "3016-3"),
    "ft3": ("Free T3", "blood", "pg/mL", 3.0, 4.0, "mid", ["free t3"], "3051-0"),
    "testosterone": ("Testosterone, total", "blood", "ng/dL", 500, 900, "mid", ["testosterone, total", "testosterone"], "2986-8"),
    "cortisol": ("Cortisol (AM)", "blood", "µg/dL", 10, 18, "mid", ["cortisol (am)", "cortisol"], "2143-6"),
    "alt": ("ALT (SGPT)", "blood", "U/L", 10, 25, "low", ["alt (sgpt)", "alt", "sgpt"], "1742-6"),
    "ggt": ("GGT", "blood", "U/L", 10, 25, "low", ["ggt"], "2324-2"),
    "creatinine": ("Creatinine", "blood", "mg/dL", 0.7, 1.1, "mid", ["creatinine"], "2160-0"),
    "egfr": ("eGFR", "blood", "mL/min/1.73m²", 90, 130, "high", ["egfr"], "33914-3"),
    "uric_acid": ("Uric acid", "blood", "mg/dL", 3.5, 5.5, "low", ["uric acid"], "3084-1"),
    "wbc": ("WBC", "blood", "10³/µL", 4.0, 6.5, "mid", ["wbc", "white blood cells"], "6690-2"),
    "lymph_pct": ("Lymphocytes", "blood", "%", 25, 40, "mid", ["lymphocytes"], "736-9"),
    "albumin": ("Albumin", "blood", "g/dL", 4.3, 5.0, "high", ["albumin"], "1751-7"),
    "alp": ("Alkaline phosphatase", "blood", "U/L", 40, 90, "mid", ["alkaline phosphatase", "alp"], "6768-6"),
    "mcv": ("MCV", "blood", "fL", 82, 92, "mid", ["mcv"], "787-2"),
    "rdw": ("RDW", "blood", "%", 11.5, 13.0, "low", ["rdw"], "788-0"),
    # gut
    "shannon": ("Shannon diversity", "gut", "", 3.5, 5.0, "high", ["shannon diversity index", "shannon"], ""),
    "bacteroidetes": ("Bacteroidetes", "gut", "%", 30, 60, "mid", ["bacteroidetes"], ""),
    "firmicutes": ("Firmicutes", "gut", "%", 30, 50, "mid", ["firmicutes"], ""),
    "fb_ratio": ("Firmicutes/Bacteroidetes ratio", "gut", "", 0.5, 1.2, "mid", ["firmicutes/bacteroidetes ratio"], ""),
    "actinobacteria": ("Actinobacteria", "gut", "%", 2, 10, "mid", ["actinobacteria"], ""),
    "proteobacteria": ("Proteobacteria", "gut", "%", 0, 6, "low", ["proteobacteria"], ""),
    "akkermansia": ("Akkermansia muciniphila", "gut", "%", 1, 5, "high", ["akkermansia muciniphila", "akkermansia"], ""),
    "faecali": ("Faecalibacterium prausnitzii", "gut", "%", 5, 15, "high", ["faecalibacterium prausnitzii"], ""),
    "bifido": ("Bifidobacterium spp.", "gut", "%", 1, 6, "high", ["bifidobacterium spp.", "bifidobacterium"], ""),
    "lacto": ("Lactobacillus spp.", "gut", "%", 0.1, 2, "mid", ["lactobacillus spp.", "lactobacillus"], ""),
    "butyrate": ("Butyrate producers", "gut", "%", 15, 30, "high", ["butyrate producers (total)", "butyrate producers"], ""),
    "calprotectin": ("Calprotectin", "gut", "µg/g", 0, 50, "low", ["calprotectin"], ""),
    "zonulin": ("Zonulin (stool)", "gut", "ng/mL", 0, 107, "low", ["zonulin (stool)", "zonulin"], ""),
    "siga": ("Secretory IgA", "gut", "µg/mL", 510, 2010, "mid", ["secretory iga"], ""),
    "hpylori": ("H. pylori antigen", "gut", "", None, None, "absent", ["h. pylori antigen"], ""),
    "candida": ("Candida spp.", "gut", "", None, None, "absent", ["candida spp."], ""),
    "blasto": ("Blastocystis hominis", "gut", "", None, None, "absent", ["blastocystis hominis"], ""),
    # genetics (categorical)
    "mthfr_c677t": ("MTHFR C677T", "genetic", "genotype", None, None, "variant", ["mthfr c677t"], ""),
    "mthfr_a1298c": ("MTHFR A1298C", "genetic", "genotype", None, None, "variant", ["mthfr a1298c"], ""),
    "apoe": ("APOE", "genetic", "genotype", None, None, "variant", ["apoe"], ""),
    "fto": ("FTO rs9939609", "genetic", "genotype", None, None, "variant", ["fto"], ""),
    "tcf7l2": ("TCF7L2 rs7903146", "genetic", "genotype", None, None, "variant", ["tcf7l2"], ""),
    "vdr": ("VDR Taq1", "genetic", "genotype", None, None, "variant", ["vdr taq1"], ""),
    "comt": ("COMT V158M", "genetic", "genotype", None, None, "variant", ["comt v158m"], ""),
    "cyp1a2": ("CYP1A2", "genetic", "genotype", None, None, "variant", ["cyp1a2"], ""),
    "actn3": ("ACTN3 R577X", "genetic", "genotype", None, None, "variant", ["actn3 r577x"], ""),
    "sod2": ("SOD2", "genetic", "genotype", None, None, "variant", ["sod2"], ""),
    "fut2": ("FUT2", "genetic", "genotype", None, None, "variant", ["fut2"], ""),
    "cad9p21": ("9p21 CAD locus", "genetic", "genotype", None, None, "variant", ["9p21 cad locus"], ""),
    "prs_cad": ("Polygenic risk — CAD", "genetic", "percentile", 0, 50, "low", ["polygenic risk — cad"], ""),
    "prs_t2d": ("Polygenic risk — Type 2 diabetes", "genetic", "percentile", 0, 50, "low", ["polygenic risk — type 2 diabetes"], ""),
    # bio age
    "chrono_age": ("Chronological age", "bioage", "years", None, None, "info", ["chronological age"], ""),
    "phenoage_lab": ("PhenoAge (lab)", "bioage", "years", None, None, "low", ["phenoage (levine 2018)", "phenoage"], ""),
    "grimage": ("GrimAge v2", "bioage", "years", None, None, "low", ["grimage v2", "grimage"], ""),
    "horvath": ("Horvath clock", "bioage", "years", None, None, "low", ["horvath clock (2013)", "horvath clock"], ""),
    "dunedinpace": ("DunedinPACE", "bioage", "years/year", 0.6, 1.0, "low", ["dunedinpace"], ""),
    "telomere": ("Telomere length (T/S)", "bioage", "T/S", 0.95, 1.40, "high", ["telomere length (qpcr, t/s ratio)", "telomere length"], ""),
    "immune_age": ("Immune age (IEAA)", "bioage", "years", -5, 0, "low", ["immune age (ieaa)"], ""),
    "inflam_clock": ("Inflammation clock", "bioage", "SD", -2, 0, "low", ["inflammation clock (crp-methylation)", "inflammation clock"], ""),
    # metals
    "lead": ("Lead (Pb)", "metals", "µg/g creat", 0, 2.0, "low", ["lead (pb)", "lead"], ""),
    "mercury": ("Mercury (Hg)", "metals", "µg/g creat", 0, 3.0, "low", ["mercury (hg)", "mercury"], ""),
    "arsenic": ("Arsenic (total)", "metals", "µg/g creat", 0, 50, "low", ["arsenic (as, total)", "arsenic"], ""),
    "cadmium": ("Cadmium (Cd)", "metals", "µg/g creat", 0, 1.0, "low", ["cadmium (cd)", "cadmium"], ""),
    "aluminium": ("Aluminium (Al)", "metals", "µg/g creat", 0, 35, "low", ["aluminium (al)", "aluminium"], ""),
    "thallium": ("Thallium (Tl)", "metals", "µg/g creat", 0, 0.5, "low", ["thallium (tl)"], ""),
    "nickel": ("Nickel (Ni)", "metals", "µg/g creat", 0, 8, "low", ["nickel (ni)"], ""),
    "urine_creat": ("Urine creatinine", "metals", "g/L", 0.3, 3.0, "mid", [], ""),
    # toxins
    "bpa": ("Bisphenol A (BPA)", "toxins", "µg/g creat", 0, 2.1, "low", ["bisphenol a (bpa)"], ""),
    "mep": ("Mono-ethyl phthalate", "toxins", "µg/g creat", 0, 85, "low", ["mono-ethyl phthalate (mep)"], ""),
    "mehp": ("MEHP (phthalate)", "toxins", "µg/g creat", 0, 7.5, "low", ["mehp (phthalate)"], ""),
    "glyphosate": ("Glyphosate", "toxins", "µg/g creat", 0, 1.0, "low", ["glyphosate"], ""),
    "d24": ("2,4-D herbicide", "toxins", "µg/g creat", 0, 0.9, "low", ["2,4-d (herbicide)"], ""),
    "dmp": ("Organophosphate (DMP)", "toxins", "µg/g creat", 0, 12, "low", ["organophosphate (dmp)"], ""),
    "ochratoxin": ("Ochratoxin A", "toxins", "ng/g creat", 0, 7.5, "low", ["ochratoxin a"], ""),
    "aflatoxin": ("Aflatoxin M1", "toxins", "ng/g creat", 0, 0.5, "low", ["aflatoxin m1"], ""),
    "zearalenone": ("Zearalenone", "toxins", "ng/g creat", 0, 0.5, "low", ["zearalenone"], ""),
    "perchlorate": ("Perchlorate", "toxins", "µg/g creat", 0, 8.2, "low", ["perchlorate"], ""),
    "pgo": ("Benzene metabolite (PGO)", "toxins", "µg/g creat", 0, 400, "low", ["benzene metabolite (pgo)"], ""),
}

# Variants considered risk alleles, for genetics interpretation.
RISK_GENOTYPES = {
    "mthfr_c677t": {"C/T": "heterozygous — ~35% lower enzyme activity", "T/T": "homozygous — ~70% lower enzyme activity"},
    "apoe": {"ε3/ε4": "one ε4 allele", "ε4/ε4": "two ε4 alleles", "ε2/ε4": "one ε4 allele"},
    "fto": {"A/T": "one risk allele", "A/A": "two risk alleles"},
    "tcf7l2": {"C/T": "one risk allele", "T/T": "two risk alleles"},
    "fut2": {"A/A (non-secretor)": "non-secretor"},
    "cad9p21": {"A/G": "one risk allele", "G/G": "two risk alleles"},
}


from .catalog_ext import EXT_MARKERS, EXT_PANELS  # noqa: E402

PANELS.update(EXT_PANELS)
MARKERS.update(EXT_MARKERS)


def match_marker(test_name: str) -> str | None:
    """Return canonical id for a lab line's test name, longest alias first."""
    n = test_name.strip().lower()
    best, best_len = None, 0
    for mid, spec in MARKERS.items():
        for alias in spec[6]:
            if n.startswith(alias) and len(alias) > best_len:
                best, best_len = mid, len(alias)
    return best


def status_for(mid: str, value, ref_low=None, ref_high=None, flag: str = "") -> str:
    """optimal | in_range | out_of_range | variant | absent | detected | info"""
    spec = MARKERS[mid]
    better = spec[5]
    if better == "variant":
        return "variant" if value in RISK_GENOTYPES.get(mid, {}) else "typical"
    if better == "absent":
        return "detected" if isinstance(value, str) and value.lower().startswith(("detected", "positive", "present", "trace", "+")) else "absent"
    if better == "info" or not isinstance(value, (int, float)):
        return "info"
    lo, hi = spec[3], spec[4]
    out = flag.upper() in ("H", "L", "HIGH", "LOW")
    if ref_low is not None and value < ref_low:
        out = True
    if ref_high is not None and value > ref_high:
        out = True
    if out:
        return "out_of_range"
    if lo is not None and hi is not None and lo <= value <= hi:
        return "optimal"
    return "in_range"
