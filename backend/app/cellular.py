"""Cellular-level effects — what a supplement, medicine, food or stressor actually does inside the cell, and which
measurable marker it shows up in. The goal: when Telomy says "your ApoB is high" or "you started omega-3", it can also
say what is happening at the cellular level and how we'd see it change.

No single public database maps interventions → cells → biomarkers, so this is a curated, evidence-graded knowledge base
built from: Reactome (reactome.org) and WikiPathways for pathways, MitoCarta 3.0 for mitochondria, DrugBank/openFDA for
drug targets, and the NIH ODS fact sheets for nutrients. Each entry is one mechanism, graded A (RCT/mechanistic
consensus) to D (preliminary), with the cell type, the site inside the cell, the pathway, the plain-language mechanism,
and the catalog markers it moves. Nothing here is advice; it explains biology and points to what we can measure.
"""
import re

# trigger kinds that match an event/tracker/intervention name
E = lambda kind, name, terms, cells, site, pathway, mech, markers, direction, grade, cite: {  # noqa: E731
    "kind": kind, "name": name, "terms": terms, "cells": cells, "site": site, "pathway": pathway,
    "mechanism": mech, "markers": markers, "direction": direction, "evidence": grade, "citation": cite}

EFFECTS = [
    E("supplement", "Omega-3 (EPA/DHA)", ["omega-3", "omega 3", "fish oil", "epa", "dha"],
      "every cell (plasma-membrane phospholipids); hepatocytes; endothelium; immune cells",
      "cell membrane + nucleus (PPARα)", "Reactome: Synthesis of specialized pro-resolving mediators; PPARα signalling",
      "EPA/DHA are incorporated into membrane phospholipids, making membranes more fluid and serving as substrate for "
      "resolvins/protectins that actively switch off inflammation; in the liver they activate PPARα, which lowers "
      "VLDL-triglyceride output.",
      ["tg", "hscrp", "il6", "hrv"], "triglycerides ↓, hs-CRP/IL-6 ↓, HRV ↑", "A",
      "Mozaffarian & Wu 2011, JACC; Calder 2017, Biochem Soc Trans"),
    E("supplement", "Vitamin D3", ["vitamin d", "vitamin d3", "cholecalciferol", "vitd"],
      "most cells carry the vitamin-D receptor; osteoblasts; enterocytes; immune cells",
      "nucleus (VDR nuclear receptor)", "Reactome: Vitamin D (calciferol) metabolism; VDR-RXR transcription",
      "Calcitriol binds the vitamin-D receptor, which pairs with RXR and sits on DNA to switch genes on/off — raising "
      "calcium absorption in the gut and modulating immune-cell behaviour. Measured as 25-OH vitamin D in blood.",
      ["vitd", "calcium"], "25-OH vitamin D ↑", "A", "Holick 2007, NEJM; NIH ODS Vitamin D fact sheet"),
    E("supplement", "Magnesium", ["magnesium", "magnesium glycinate", "magnesium citrate"],
      "all cells (ATP is used as Mg-ATP); neurons; cardiomyocytes",
      "mitochondria + cytosol (enzyme cofactor)", "Reactome: Mg2+ is a cofactor across the TCA cycle and oxidative phosphorylation",
      "Magnesium is the counter-ion for ATP — most enzymes that use ATP actually use Mg-ATP — and it gates NMDA receptors "
      "in neurons, which is part of why it steadies sleep and calms the stress response.",
      ["deep_sleep", "sleep_score", "hrv"], "deep sleep ↑, HRV ↑ (individual)", "B",
      "de Baaij 2015, Physiol Rev; Abbasi 2012 (sleep RCT)"),
    E("supplement", "Creatine monohydrate", ["creatine"],
      "skeletal muscle; neurons", "cytosol + mitochondria (phosphocreatine shuttle)",
      "Reactome: Creatine metabolism", "Creatine loads the phosphocreatine system that rapidly regenerates ATP during "
      "short, hard efforts, and buffers brain energy; the extra intramuscular water shows up as a small weight gain.",
      ["weight"], "body weight ↑ ~1 kg (water), strength ↑", "A", "Kreider 2017, JISSN"),
    E("supplement", "L-theanine", ["l-theanine", "theanine"],
      "cortical neurons", "synapse (glutamate/GABA modulation)", "WikiPathways: GABAergic synapse",
      "Theanine raises alpha-wave activity and nudges GABA/glutamate balance toward calm without sedation; pairs well "
      "with caffeine to blunt its jitter.", ["sleep_score", "hrv"], "calm, HRV ↑ (individual)", "C",
      "Nobre 2008, Asia Pac J Clin Nutr"),
    E("medicine", "Statin (e.g. rosuvastatin)", ["statin", "rosuvastatin", "atorvastatin", "simvastatin"],
      "hepatocytes (liver cells)", "endoplasmic reticulum (HMG-CoA reductase)", "Reactome: Cholesterol biosynthesis",
      "Statins block HMG-CoA reductase, the rate-limiting enzyme of cholesterol synthesis in the liver. The hepatocyte "
      "senses less internal cholesterol and puts more LDL receptors on its surface, pulling LDL/ApoB out of the blood.",
      ["ldl", "apob", "chol_total", "hscrp"], "LDL/ApoB ↓↓, hs-CRP ↓", "A",
      "Ference 2017, Eur Heart J; CTT Collaboration 2010, Lancet"),
    E("medicine", "Metformin", ["metformin"],
      "hepatocytes; gut enterocytes", "mitochondria (Complex I) → AMPK",
      "Reactome: Energy dependent regulation of mTOR by AMPK", "Metformin mildly inhibits mitochondrial Complex I, which "
      "raises the AMP:ATP ratio and switches on AMPK — the cell's low-fuel sensor — cutting the liver's glucose output "
      "and improving insulin sensitivity.", ["glucose", "hba1c", "homa_ir", "insulin"],
      "fasting glucose/HbA1c ↓, HOMA-IR ↓", "A", "Rena 2017, Diabetologia"),
    E("food", "Saturated fat / refined carbohydrate", ["saturated fat", "fried", "refined carb", "sugar", "processed"],
      "hepatocytes; adipocytes; arterial endothelium", "ER + nucleus (SREBP-2); lipoproteins",
      "Reactome: Regulation of cholesterol biosynthesis by SREBP", "A surplus of saturated fat and refined carbs pushes "
      "the liver to make more ApoB-containing particles and down-regulates LDL receptors, raising circulating ApoB/LDL; "
      "excess energy is stored as liver and visceral fat.", ["apob", "ldl", "tg", "alt"],
      "ApoB/LDL ↑, triglycerides ↑, ALT ↑", "A", "Mensink 2016, WHO meta-analysis"),
    E("food", "Dietary fibre (soluble)", ["fibre", "fiber", "psyllium", "isabgol", "oats", "beta-glucan"],
      "gut enterocytes; gut microbiota; hepatocytes", "gut lumen + colonocyte mitochondria (butyrate)",
      "WikiPathways: Bile acid and bile salt metabolism", "Soluble fibre binds bile acids so the liver must pull "
      "cholesterol from blood to make more; fermentation by gut bacteria yields butyrate that feeds colonocytes and "
      "improves the gut barrier and insulin sensitivity.", ["ldl", "glucose", "hscrp"],
      "LDL ↓, post-meal glucose ↓", "A", "Brown 1999 meta-analysis; ICMR-NIN 2020"),
    E("activity", "Zone-2 / aerobic exercise", ["zone 2", "zone2", "running", "cycling", "cardio", "aerobic", "walk"],
      "skeletal muscle; cardiomyocytes; endothelium", "mitochondria (biogenesis via PGC-1α)",
      "Reactome: PGC-1α promotes mitochondrial biogenesis", "Repeated aerobic work switches on PGC-1α, the master "
      "regulator that tells muscle cells to build more mitochondria and capillaries — raising fat-burning capacity, "
      "VO₂max and insulin sensitivity, and lowering resting heart rate.", ["vo2max", "rhr", "hrv", "glucose", "tg"],
      "VO₂max ↑, resting HR ↓, HRV ↑, glucose/triglycerides ↓", "A", "Holloszy 1967; San-Millán 2018"),
    E("activity", "Resistance training", ["strength", "lifting", "resistance", "gym", "weights"],
      "skeletal muscle fibres", "ribosomes (mTOR → protein synthesis)", "Reactome: mTOR signalling",
      "Mechanical load plus amino acids activate mTORC1, which drives muscle protein synthesis and, over time, bigger, "
      "more insulin-sensitive muscle — a glucose sink that improves metabolic health.", ["glucose", "homa_ir", "weight"],
      "muscle ↑, insulin sensitivity ↑", "A", "Morton 2018, Br J Sports Med"),
    E("stress", "Chronic psychological stress", ["stress", "stressed", "anxiety", "overwhelmed", "burnout"],
      "immune cells; neurons (hippocampus); every cell (telomeres)",
      "HPA axis → cortisol → glucocorticoid receptor; telomeres", "WikiPathways: Glucocorticoid receptor signalling",
      "Sustained cortisol keeps the glucocorticoid receptor active, which over time blunts immune regulation, raises "
      "blood glucose and inflammation, suppresses overnight HRV, and is linked to faster telomere shortening.",
      ["hrv", "rhr", "sleep_score", "hscrp", "glucose"], "HRV ↓, resting HR ↑, hs-CRP ↑, sleep ↓", "A",
      "Epel 2004, PNAS (telomeres); McEwen 2007, Physiol Rev"),
    E("stress", "Alcohol", ["alcohol", "beer", "wine", "whisky", "vodka", "drinks"],
      "hepatocytes; cardiomyocytes; neurons", "mitochondria + ER (acetaldehyde, oxidative stress)",
      "Reactome: Ethanol oxidation", "Ethanol is processed to acetaldehyde in liver mitochondria, generating oxidative "
      "stress and fat accumulation (raising GGT/ALT and triglycerides), and it disrupts autonomic balance overnight — "
      "the clearest single hit to next-day HRV and deep sleep.", ["ggt", "alt", "tg", "hrv", "deep_sleep"],
      "GGT/ALT ↑, triglycerides ↑, HRV ↓, deep sleep ↓", "A", "Rehm 2017; Pietraszek 2010"),
    E("supplement", "Berberine", ["berberine"],
      "hepatocytes; gut microbiota", "mitochondria (Complex I) → AMPK (metformin-like)",
      "WikiPathways: AMPK signalling", "Berberine activates AMPK much like metformin, lowering liver glucose output and "
      "improving lipids; it also shifts the gut microbiome.", ["glucose", "hba1c", "ldl", "tg"],
      "glucose/HbA1c ↓, LDL ↓", "B", "Yin 2008, Metabolism"),
    E("supplement", "B-vitamins (folate/B12/B6)", ["folate", "folic acid", "b12", "vitamin b12", "b6", "methylfolate"],
      "all cells (one-carbon metabolism); red-cell precursors; neurons",
      "cytosol + mitochondria (methylation cycle)", "Reactome: Folate metabolism; Metabolism of folate and pterines",
      "Folate, B12 and B6 run the one-carbon/methylation cycle that converts homocysteine back to methionine; a gap "
      "(common with an MTHFR variant) lets homocysteine build up, which is toxic to the vessel lining.",
      ["homocysteine", "b12", "folate", "mcv"], "homocysteine ↓", "A", "Clarke 2010; NIH ODS folate fact sheet"),
    E("supplement", "Iron", ["iron", "ferrous", "ferritin"],
      "red-cell precursors (erythroblasts)", "mitochondria (haem synthesis)", "Reactome: Heme biosynthesis",
      "Iron is built into haem inside developing red cells; a shortage makes small, pale cells (low MCV, high RDW) and "
      "low ferritin. Only correct it when ferritin confirms a true deficiency — iron is pro-oxidant in excess.",
      ["ferritin", "mcv", "rdw", "hemoglobin"], "ferritin ↑, MCV normalises, RDW ↓", "A", "WHO 2020 iron guidance"),
    E("activity", "Sauna / heat", ["sauna", "heat"],
      "most cells (heat-shock response); endothelium", "cytosol (heat-shock proteins); nitric-oxide pathway",
      "WikiPathways: Heat shock response", "Heat stress triggers heat-shock proteins that refold damaged proteins "
      "(cellular housekeeping) and improves endothelial nitric-oxide function — part of why regular sauna tracks with "
      "lower cardiovascular risk and better HRV.", ["hrv", "rhr", "sbp"], "HRV ↑, blood pressure ↓ (individual)", "B",
      "Laukkanen 2018, Mayo Clin Proc"),
    E("activity", "Daylight / morning light", ["daylight", "sunlight", "morning light"],
      "retinal ganglion cells → SCN neurons", "nucleus (clock genes BMAL1/CLOCK)", "WikiPathways: Circadian rhythm genes",
      "Bright morning light sets the suprachiasmatic clock via melanopsin cells, which synchronises the body's clock "
      "genes — advancing melatonin timing at night and improving sleep timing and metabolism.", ["sleep_score", "daylight_min"],
      "sleep timing ↑, melatonin onset earlier", "B", "Blume 2019, Somnologie"),
]


def _all_effects() -> list:
    base = list(EFFECTS)
    try:
        from . import science
        base += science.extra_cellular_effects()
    except Exception:  # noqa: BLE001
        pass
    return base


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower())


def explain(name: str) -> list[dict]:
    """Every cellular mechanism that matches an intervention/food/stressor name."""
    q = _norm(name)
    out = []
    for e in _all_effects():
        if any(t in q for t in e["terms"]) or _norm(e["name"]) in q:
            out.append(_public(e))
    return out


def for_marker(marker_id: str) -> list[dict]:
    """What acts on the cell biology behind a given blood/signal marker."""
    return [_public(e) for e in _all_effects() if marker_id in e["markers"]]


def _public(e: dict) -> dict:
    return {k: e[k] for k in ("kind", "name", "cells", "site", "pathway", "mechanism", "markers", "direction", "evidence", "citation")}


def cards() -> list[dict]:
    """For the RAG index: one card per mechanism, so Sinc can ground a cellular-level answer."""
    return [{"id": f"cell:{i}", "kind": "cellular", "title": f"Cellular effect — {e['name']}",
             "text": f"{e['name']} ({e['kind']}): acts on {e['cells']} at the {e['site']}. {e['mechanism']} "
                     f"Seen in: {', '.join(e['markers'])} ({e['direction']}). Evidence {e['evidence']}. {e['citation']}"}
            for i, e in enumerate(_all_effects())]
