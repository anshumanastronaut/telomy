"""Add a medically-coherent, LABELLED SYNTHETIC overlay to a Telomy DB so every engine feature can be exercised with
rich, multi-timepoint, multi-modal data — without touching the person's real record.

Everything written here has is_test_data = 1 and "(synthetic test data)" in its title/source. The real report stays and
the engine prefers it (is_test_data ASC). Three blood panels carry a coherent *improving* trend for an overweight
(BMI ~29) 28-year-old male — borderline lipids/metabolic markers that get better across visits — so trends and
lifestyle correlations are visible; the real CBC abnormality (low platelets/neutrophils) is carried forward unchanged.
Also: a genetic panel, a gut-microbiome report, and CT/MRI/DEXA/CIMT imaging, all coherent for the same person.

Usage: TELOMY_DB=<copy.db> backend/.venv/bin/python tools/make_test_overlay.py [--purge]
`--purge` removes everything this script added (every is_test_data row) and nothing else.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import db, engine, seed  # noqa: E402
from app.catalog import MARKERS  # noqa: E402

TAG = "(synthetic test data)"
UNIT = lambda m: MARKERS[m][2]  # noqa: E731
REF = lambda m: MARKERS[m][3], MARKERS  # noqa: E731


def ref_text(m):
    lo, hi, better = MARKERS[m][3], MARKERS[m][4], MARKERS[m][5]
    if better == "low":
        return f"< {hi:g}"
    if better == "high":
        return f"> {lo:g}"
    return f"{lo:g} - {hi:g}"


def status_for(m, v):
    if not isinstance(v, (int, float)):
        return "in_range"
    lo, hi, better = MARKERS[m][3], MARKERS[m][4], MARKERS[m][5]
    if better == "low":
        return "in_range" if v <= hi else "out_of_range"
    if better == "high":
        return "in_range" if v >= lo else "out_of_range"
    return "in_range" if lo <= v <= hi else "out_of_range"


# Three blood panels: an improving trajectory for an overweight 28 y/o male. Real CBC (platelets/MPV/ALP/MCV/ANC) is
# carried forward unchanged so his genuine finding stays visible. Values chosen to be medically consistent across markers.
PANELS = [
    ("2026-02-15", {
        "chol_total": 221, "ldl": 155, "hdl": 36, "tg": 190, "apob": 118, "lpa": 34,
        "glucose": 102, "hba1c": 5.8, "insulin": 15.0, "homa_ir": 3.77, "uric_acid": 6.9,
        "hscrp": 3.2, "il6": 2.9, "homocysteine": 15.0,
        "alt": 48, "ast": 40, "ggt": 60, "albumin": 4.5, "creatinine": 1.0, "egfr": 108,
        "vitd": 18, "b12": 300, "folate": 6.5, "ferritin": 180, "tsh": 2.6,
        "hemoglobin": 14.6, "mcv": 82, "rdw": 13.9, "alp": 37, "wbc_total": 4600, "lymph_pct": 52, "platelets": 110, "mpv": 14.8,
    }),
    ("2026-05-15", {
        "chol_total": 205, "ldl": 138, "hdl": 39, "tg": 165, "apob": 105, "lpa": 34,
        "glucose": 97, "hba1c": 5.6, "insulin": 12.0, "homa_ir": 2.87, "uric_acid": 6.4,
        "hscrp": 2.1, "il6": 2.2, "homocysteine": 13.2,
        "alt": 40, "ast": 36, "ggt": 50, "albumin": 4.6, "creatinine": 1.0, "egfr": 110,
        "vitd": 24, "b12": 340, "folate": 7.4, "ferritin": 150, "tsh": 2.3,
        "hemoglobin": 14.6, "mcv": 82, "rdw": 13.9, "alp": 37, "wbc_total": 4400, "lymph_pct": 55, "platelets": 101, "mpv": 15.0,
    }),
    ("2026-09-25", {
        "chol_total": 190, "ldl": 125, "hdl": 42, "tg": 140, "apob": 96, "lpa": 33,
        "glucose": 92, "hba1c": 5.4, "insulin": 9.8, "homa_ir": 2.23, "uric_acid": 6.0,
        "hscrp": 1.4, "il6": 1.7, "homocysteine": 12.0,
        "alt": 34, "ast": 30, "ggt": 41, "albumin": 4.6, "creatinine": 1.0, "egfr": 112,
        "vitd": 30, "b12": 380, "folate": 8.2, "ferritin": 130, "tsh": 2.1,
        "hemoglobin": 14.6, "mcv": 82, "rdw": 13.8, "alp": 38, "wbc_total": 4300, "lymph_pct": 56, "platelets": 98, "mpv": 15.1,
    }),
]

GENETICS = {"apoe": "ε3/ε4", "mthfr_c677t": "C/T", "fto": "A/T", "tcf7l2": "C/T", "fut2": "A/A (non-secretor)", "cad9p21": "A/G"}

IMAGING = [
    {"title": f"Coronary calcium CT (CAC) {TAG}", "modality": "CT", "day": "2026-09-10", "series": 1, "images": 60,
     "findings": [{"text": "Agatston score 0 (no detectable coronary calcium)", "status": "optimal"},
                  {"text": "0th percentile for age", "status": "optimal"}], "radiologist": f"Test Radiologist {TAG}", "is_test_data": True},
    {"title": f"CT coronary angiography (CCTA) {TAG}", "modality": "CT", "day": "2026-09-10", "series": 3, "images": 220,
     "findings": [{"text": "No obstructive coronary artery disease; no soft or calcified plaque", "status": "optimal"},
                  {"text": "CAD-RADS 0", "status": "optimal"}], "radiologist": f"Test Radiologist {TAG}", "is_test_data": True},
    {"title": f"MRI brain {TAG}", "modality": "MRI", "day": "2026-09-12", "series": 6, "images": 320,
     "findings": [{"text": "No white-matter hyperintensities (Fazekas 0)", "status": "optimal"},
                  {"text": "Brain-age gap +0.3 years", "status": "in_range"}], "radiologist": f"Test Radiologist {TAG}", "is_test_data": True},
    {"title": f"MRI liver (PDFF) {TAG}", "modality": "MRI", "day": "2026-09-12", "series": 2, "images": 40,
     "findings": [{"text": "Liver fat (MRI-PDFF) 8.1% — mild steatosis (normal < 5%)", "status": "out_of_range"},
                  {"text": "No iron overload; LIC normal", "status": "optimal"}], "radiologist": f"Test Radiologist {TAG}", "is_test_data": True},
    {"title": f"DEXA body composition {TAG}", "modality": "DXA", "day": "2026-09-05", "series": 1, "images": 3,
     "findings": [{"text": "Body fat 26.2%", "status": "out_of_range"},
                  {"text": "Visceral fat area 115 cm² (target < 100)", "status": "out_of_range"},
                  {"text": "Appendicular lean mass index 8.4 kg/m² (normal)", "status": "in_range"},
                  {"text": "Bone density T-score +0.3", "status": "optimal"}], "radiologist": f"Test Radiologist {TAG}", "is_test_data": True},
    {"title": f"Carotid ultrasound (CIMT) {TAG}", "modality": "US", "day": "2026-09-05", "series": 2, "images": 48,
     "findings": [{"text": "Mean CIMT 0.58 mm (normal for age)", "status": "in_range"},
                  {"text": "No carotid plaque", "status": "optimal"}], "radiologist": f"Test Radiologist {TAG}", "is_test_data": True},
]

GUT = {"title": f"Gut microbiome (metagenomic) {TAG}", "panel": "microbiome", "day": "2026-09-01", "findings": [
    "Shannon diversity 3.4 (median range)", "Firmicutes/Bacteroidetes ratio 1.9 (slightly high — tracks with refined-carb intake)",
    "Akkermansia muciniphila 0.4% (low — associated with gut-barrier and metabolic health)",
    "Faecalibacterium prausnitzii 4.1% (adequate butyrate producer)", "No pathogenic overgrowth; non-secretor (FUT2) — lower Bifidobacterium expected"]}


def purge():
    with db.tx() as c:
        n1 = c.execute("DELETE FROM results WHERE report_id IN (SELECT id FROM reports WHERE is_test_data = 1)").rowcount
        n2 = c.execute("DELETE FROM reports WHERE is_test_data = 1").rowcount
        n3 = c.execute("DELETE FROM imaging WHERE data LIKE '%synthetic test data%'").rowcount
        n4 = c.execute("DELETE FROM signals WHERE source LIKE '%synthetic test data%'").rowcount
    engine.regenerate_insights()
    print(f"purged {n2} test reports, {n1} results, {n3} imaging rows, {n4} signal readings")


def build():
    for day, vals in PANELS:
        markers = [{"marker_id": m, "value": v, "unit": UNIT(m), "ref_low": MARKERS[m][3], "ref_high": MARKERS[m][4],
                    "ref_text": ref_text(m), "flag": None, "status": status_for(m, v)} for m, v in vals.items()]
        seed.save_report({"title": f"Comprehensive panel {TAG}", "panel": "blood", "collected_on": day,
                          "is_test_data": True, "markers": markers}, f"Synthetic Diagnostics {TAG}", "synthetic_panel.pdf")
    gmarkers = [{"marker_id": m, "value": gt, "unit": "genotype", "ref_low": None, "ref_high": None,
                 "ref_text": "", "flag": None, "status": "variant"} for m, gt in GENETICS.items()]
    seed.save_report({"title": f"Genetic risk panel {TAG}", "panel": "genetics", "collected_on": "2026-01-10",
                      "is_test_data": True, "markers": gmarkers}, f"Synthetic Genomics {TAG}", "synthetic_genetics.pdf")
    for im in IMAGING:
        db.exec_("INSERT INTO imaging (data) VALUES (?)", (db.j(im),))
    db.exec_("INSERT INTO imaging (data) VALUES (?)", (db.j({**GUT, "modality": "LAB", "series": 1, "images": 0,
             "findings": [{"text": f, "status": "in_range"} for f in GUT["findings"]], "radiologist": f"Synthetic lab {TAG}", "is_test_data": True}),))
    # home BP cuff: a short improving series so PREVENT/PCE compute and correlate (source tag lets --purge remove them)
    from datetime import date, timedelta
    import random
    rnd = random.Random(7)
    d0 = date(2026, 9, 1)
    for i in range(0, 24, 2):
        d = (d0 + timedelta(days=i)).isoformat()
        db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)", (d, "sbp", round(126 - i * 0.3 + rnd.gauss(0, 3)), f"BP cuff {TAG}"))
        db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)", (d, "dbp", round(82 - i * 0.2 + rnd.gauss(0, 2)), f"BP cuff {TAG}"))
    engine.regenerate_insights()
    print("added 3 blood panels, 1 genetic panel, 6 imaging studies, 1 gut report, 12 BP readings (all labelled test)")


if __name__ == "__main__":
    if "--purge" in sys.argv:
        purge()
    else:
        build()
