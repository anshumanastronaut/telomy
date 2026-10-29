"""Peptide reference library — an evidence-graded, region-aware knowledge module (not a recommender, not a store).

Telomy's posture (see protocols.py / the dossier): drugs, hormones and peptides are CLINICIAN-GATED — shown to the
member by name only and routed to a doctor, never recommended, never with dosing or sourcing. This module is the
reference layer *behind* that gate: for each peptide, an honest evidence grade, the regulatory status PER REGION
(FDA + India/CDSCO — critical, since most are unapproved or research-chem here and selling/facilitating access carries
real legal risk), mechanism, whether there is human data, and citations. It deliberately carries NO dosing/protocol.

Honesty is the whole point: the category is full of hype-sellers, so we show the grade and the regulatory reality.
Grades: A robust human RCT / approved-drug evidence · B meaningful human data · C limited/mixed human data ·
D preclinical or anecdote only (animal/lab), not advised outside research. `advised` = has a credible approved use.
Seed set (~22) spanning A→D and the main classes; extend from primary literature (never copy a vendor's pages).
"""
from __future__ import annotations

# name, aliases, class (by where/how it acts), mechanism, grade, fda status, india/CDSCO status, human-data?, advised?,
# one-line summary (claim + honest caveat), safety, citations (honest source descriptors — not fabricated IDs)
_F = ("name", "aliases", "pclass", "mechanism", "grade", "fda", "cdsco", "human", "advised", "summary", "safety", "citations")
def P(*a): return dict(zip(_F, a))  # noqa: E731

PEPTIDES: dict[str, dict] = {
    # ---------------- Hormonal & metabolic (GLP-1 / incretin) — the approved, high-evidence end
    "semaglutide": P("Semaglutide", ["ozempic", "wegovy", "rybelsus"], "Hormonal / metabolic (GLP-1)",
        "GLP-1 receptor agonist — slows gastric emptying, increases satiety, improves insulin secretion.", "A",
        "Approved (type 2 diabetes; chronic weight management)", "Approved (Rybelsus oral; Wegovy launched 2025)",
        True, True, "Strong weight and cardiometabolic benefit in large RCTs — a prescription drug, not a wellness peptide.",
        "GI effects; pancreatitis and gallbladder signals; not with personal/family medullary thyroid cancer history.",
        ["FDA prescribing information", "SELECT cardiovascular outcomes trial (NEJM 2023)", "STEP weight-management trials"]),
    "tirzepatide": P("Tirzepatide", ["mounjaro", "zepbound"], "Hormonal / metabolic (GIP/GLP-1)",
        "Dual GIP + GLP-1 receptor agonist.", "A", "Approved (T2D; obesity)", "Approved (Mounjaro, 2025)", True, True,
        "Largest weight effect of the incretins in head-to-head data — prescription only.",
        "GI effects; same thyroid-tumour caution as GLP-1s.", ["FDA prescribing information", "SURMOUNT / SURPASS trials"]),
    "liraglutide": P("Liraglutide", ["victoza", "saxenda"], "Hormonal / metabolic (GLP-1)",
        "Daily GLP-1 receptor agonist.", "A", "Approved (T2D; obesity)", "Approved", True, True,
        "Approved, well-characterised; superseded on efficacy by semaglutide/tirzepatide.", "GI effects; pancreatitis signal.",
        ["FDA prescribing information", "LEADER cardiovascular trial"]),
    # ---------------- Growth-hormone axis
    "tesamorelin": P("Tesamorelin", ["egrifta"], "Growth-hormone axis (GHRH analogue)",
        "GHRH analogue → raises endogenous GH/IGF-1.", "A", "Approved (HIV-associated lipodystrophy)",
        "Not approved", True, True, "Approved for a narrow indication; visceral-fat reduction shown in RCTs.",
        "Raises IGF-1; glucose intolerance; contraindicated in active malignancy.", ["FDA prescribing information"]),
    "sermorelin": P("Sermorelin", [], "Growth-hormone axis (GHRH analogue)",
        "GHRH(1-29) fragment → stimulates GH release.", "C", "Not approved (approval withdrawn; compounded)",
        "Not approved", True, False, "Older GHRH peptide, now compounded only; limited modern human evidence for 'anti-ageing' use.",
        "Raises IGF-1; injection-site reactions.", ["Historical FDA approval (withdrawn, non-safety)", "Limited human data"]),
    "cjc1295": P("CJC-1295", ["cjc-1295", "cjc 1295 dac"], "Growth-hormone axis (GHRH analogue)",
        "Long-acting GHRH analogue (often stacked with a GHRP).", "D", "Not approved", "Not approved (research-chem)",
        False, False, "Popular in 'GH-peptide' stacks; essentially no controlled human evidence for longevity claims.",
        "Unregulated sourcing/purity risk; sustained IGF-1 elevation is a theoretical cancer concern.",
        ["Preclinical / early-phase only; no longevity RCTs"]),
    "ipamorelin": P("Ipamorelin", [], "Growth-hormone axis (GHRP / ghrelin-receptor)",
        "Selective GH secretagogue (ghrelin-receptor agonist).", "D", "Not approved", "Not approved (research-chem)",
        False, False, "Common in GH stacks; no controlled human longevity evidence.", "Unregulated sourcing; IGF-1 caution.",
        ["Preclinical / anecdotal only"]),
    "ghrp2": P("GHRP-2", ["ghrp-2", "pralmorelin"], "Growth-hormone axis (GHRP)",
        "GH-releasing peptide; used diagnostically as a GH-stimulation test in some regions.", "C", "Not approved",
        "Not approved", True, False, "Human data exist mainly as a GH-stimulation diagnostic, not as a therapy.",
        "Cortisol/prolactin rise; sourcing risk.", ["Diagnostic-use human studies"]),
    "mk677": P("Ibutamoren (MK-677)", ["mk-677", "mk 677"], "Growth-hormone axis (oral GH secretagogue)",
        "Non-peptide oral ghrelin-receptor agonist (grouped here by mechanism).", "C", "Investigational, not approved",
        "Not approved", True, False, "Raises GH/IGF-1 in humans; long-term benefit unproven, worsened outcomes in one Alzheimer's trial.",
        "Increased appetite, fluid retention, insulin resistance; IGF-1 elevation.", ["Phase-II trials (mixed/negative)"]),
    # ---------------- Repair / 'research' peptides — the hyped, low-evidence end
    "bpc157": P("BPC-157", ["bpc 157", "body protection compound"], "Repair / research (investigational)",
        "Synthetic gastric peptide fragment; angiogenic/cytoprotective in animals.", "D",
        "Not approved; FDA flagged; restricted compounding access (Feb 2026)", "Not approved (research-chem)", False, False,
        "The most-hyped 'healing' peptide — evidence is almost entirely rodent; no RCTs. Compounding was restricted in 2026.",
        "Unknown human safety; unregulated sourcing/purity; angiogenesis is a theoretical tumour concern.",
        ["Rodent studies only; no human RCTs", "FDA compounding-list action 2026"]),
    "tb500": P("TB-500 (thymosin β4)", ["tb-500", "thymosin beta-4", "tb4"], "Repair / research (investigational)",
        "Actin-binding peptide; promotes cell migration/angiogenesis in models.", "D", "Not approved (research/veterinary)",
        "Not approved (research-chem)", False, False, "Repair claims rest on animal/veterinary data; no human efficacy trials.",
        "Unknown human safety; angiogenesis/tumour concern; sourcing risk.", ["Preclinical / veterinary data only"]),
    "ghk_cu": P("GHK-Cu", ["copper peptide", "ghk copper"], "Repair / cosmetic (signal peptide)",
        "Copper-binding tripeptide; wound-healing and skin-remodelling signalling.", "C",
        "Cosmetic ingredient (topical); not an approved drug", "Topical cosmetic use common; not an approved drug",
        True, False, "Reasonable topical/cosmetic evidence for skin; systemic 'anti-ageing' injection use is unproven.",
        "Topical generally well tolerated; injected use unstudied.", ["Topical dermatology studies", "No systemic RCTs"]),
    "mots_c": P("MOTS-c", ["mots c"], "Mitochondrial-derived / metabolic (investigational)",
        "Mitochondrial-derived peptide; activates AMPK, improves insulin sensitivity in models.", "D",
        "Not approved", "Not approved (research-chem)", False, False,
        "Exciting mechanism (exercise-mimetic) but human evidence is essentially absent.", "Unknown human safety.",
        ["Preclinical only"]),
    "epithalon": P("Epithalon", ["epitalon", "ahk peptide"], "Longevity / research (investigational)",
        "Tetrapeptide claimed to modulate telomerase/pineal function.", "D", "Not approved",
        "Not approved (research-chem)", True, False, "Longevity claims come from small, methodologically weak Russian studies; not replicated.",
        "Unknown; unregulated sourcing.", ["Small unreplicated human studies; low quality"]),
    "aod9604": P("AOD-9604", ["aod 9604"], "Metabolic / research (investigational)",
        "Modified GH fragment (176-191) promoted for fat loss.", "D", "Not approved (failed obesity trials)",
        "Not approved", True, False, "Failed to beat placebo for fat loss in trials; marketing outran the evidence.",
        "Sourcing risk; no demonstrated benefit.", ["Phase-II obesity trials (negative)"]),
    "melanotan2": P("Melanotan II", ["melanotan 2", "mt-2"], "Neuropeptide / research (melanocortin agonist)",
        "Non-selective melanocortin agonist (tanning, libido).", "D", "Not approved (safety concerns)",
        "Not approved", True, False, "Unapproved; associated with changing moles, nausea and priapism — explicitly not advised.",
        "Melanoma/mole concern, priapism, nausea; unregulated sourcing.", ["Case reports / safety warnings"]),
    # ---------------- Immune / neuro / sexual / bone — region-approved or narrow-indication
    "thymosin_alpha1": P("Thymosin α1", ["thymalfasin", "zadaxin", "thymosin alpha-1"], "Immune (immunomodulator)",
        "Immunomodulatory peptide; enhances T-cell function.", "B", "Not FDA-approved", "Approved (Zadaxin, e.g. hepatitis B)",
        True, True, "Approved in India and several countries for specific immune/hepatitis indications; longevity use is off-label.",
        "Generally well tolerated in approved use.", ["Approved-indication human trials (hepatitis B, sepsis adjunct)"]),
    "pt141": P("PT-141 (bremelanotide)", ["bremelanotide", "vyleesi"], "Neuropeptide (melanocortin agonist)",
        "Melanocortin-4 receptor agonist for sexual desire.", "B", "Approved (HSDD in premenopausal women)",
        "Not approved", True, True, "Approved for a specific sexual-desire indication; evidence is modest but real.",
        "Nausea, transient BP rise, injection-site reactions.", ["FDA prescribing information", "RECONNECT trials"]),
    "teriparatide": P("Teriparatide", ["forteo", "pth 1-34"], "Bone (PTH analogue)",
        "Recombinant PTH(1-34) — anabolic bone-building.", "A", "Approved (osteoporosis)", "Approved",
        True, True, "Strong fracture-reduction evidence; prescription anabolic bone agent.",
        "Hypercalcaemia; 2-year lifetime limit; osteosarcoma boxed warning (rodent).", ["FDA prescribing information", "Fracture Prevention Trial"]),
    "oxytocin": P("Oxytocin", [], "Neuropeptide (hormone)",
        "Posterior-pituitary hormone; social/bonding and obstetric roles.", "A", "Approved (obstetric use)",
        "Approved but retail sale restricted (KAPL-only supply since 2018 to curb misuse)", True, True,
        "Approved as an obstetric drug; 'wellness/bonding' intranasal use is experimental.", "Obstetric use is clinician-only; misuse is tightly regulated in India.",
        ["FDA prescribing information", "Intranasal social-cognition studies (mixed)"]),
    "semax": P("Semax", [], "Neuropeptide / nootropic (region-approved)",
        "ACTH(4-10) analogue; nootropic/neuroprotective claims.", "D", "Not approved",
        "Not approved (approved only in Russia/Ukraine)", True, False, "Used clinically in Russia; no Western-standard RCTs to support nootropic claims.",
        "Unregulated sourcing outside its origin markets.", ["Russian clinical use; limited international evidence"]),
    "selank": P("Selank", [], "Neuropeptide / anxiolytic (region-approved)",
        "Tuftsin analogue; anxiolytic claims.", "D", "Not approved", "Not approved (approved only in Russia)",
        True, False, "Russian anxiolytic; essentially no international controlled evidence.", "Unregulated sourcing.",
        ["Russian clinical use; limited international evidence"]),
    # ---------------- Metabolic / incretin — next-generation (investigational)
    "retatrutide": P("Retatrutide", [], "Hormonal / metabolic (GIP/GLP-1/glucagon)",
        "Triple GIP + GLP-1 + glucagon receptor agonist.", "B", "Investigational (Phase 3)", "Not approved",
        True, False, "Largest weight loss yet seen in Phase 2; still investigational — not yet an approved drug.",
        "GI effects; long-term safety not established.", ["Phase-II trial (NEJM 2023)", "Phase-III ongoing"]),
    "cagrilintide": P("Cagrilintide", ["cagrisema (with semaglutide)"], "Hormonal / metabolic (amylin analogue)",
        "Long-acting amylin analogue; often paired with semaglutide (CagriSema).", "B", "Investigational (Phase 3)",
        "Not approved", True, False, "Promising weight data in combination; investigational.", "GI effects; under study.",
        ["Phase-II/III trials"]),
    "survodutide": P("Survodutide", [], "Hormonal / metabolic (GLP-1/glucagon)",
        "Dual GLP-1 + glucagon agonist; studied for obesity and MASH.", "B", "Investigational (Phase 3)", "Not approved",
        True, False, "Positive Phase 2 for weight and liver fat; investigational.", "GI effects; under study.",
        ["Phase-II MASH/obesity trials"]),
    "setmelanotide": P("Setmelanotide", ["imcivree"], "Neuropeptide (MC4R agonist)",
        "Melanocortin-4 receptor agonist for rare genetic obesity.", "A", "Approved (specific genetic obesity syndromes)",
        "Not approved (orphan)", True, True, "Approved for narrow monogenic obesity indications — not for general weight loss.",
        "Hyperpigmentation, nausea, priapism.", ["FDA prescribing information", "Phase-III POMC/LEPR trials"]),
    "teduglutide": P("Teduglutide", ["gattex", "revestive"], "Hormonal / GI (GLP-2 analogue)",
        "GLP-2 analogue; intestinal adaptation in short-bowel syndrome.", "A", "Approved (short-bowel syndrome)",
        "Limited / specialist use", True, True, "Approved for a specific GI indication; reduces parenteral-support needs.",
        "Intestinal polyp risk (monitoring), fluid overload.", ["FDA prescribing information", "STEPS trial"]),
    "linaclotide": P("Linaclotide", ["linzess", "constella"], "Hormonal / GI (GC-C agonist)",
        "Guanylate-cyclase-C agonist peptide for IBS-C / chronic constipation.", "A", "Approved (IBS-C, CIC)",
        "Approved", True, True, "Well-evidenced approved GI peptide.", "Diarrhoea; not in paediatric use.",
        ["FDA prescribing information", "Phase-III IBS-C trials"]),
    # ---------------- Endocrine / oncology — approved peptide drugs (grade-A anchors)
    "octreotide": P("Octreotide", ["sandostatin"], "Endocrine (somatostatin analogue)",
        "Somatostatin analogue; suppresses GH and various hormones.", "A", "Approved (acromegaly, NETs)", "Approved",
        True, True, "Mainstay approved peptide for acromegaly and neuroendocrine tumours.", "Gallstones, GI effects, glucose changes.",
        ["FDA prescribing information"]),
    "lanreotide": P("Lanreotide", ["somatuline"], "Endocrine (somatostatin analogue)",
        "Long-acting somatostatin analogue.", "A", "Approved (acromegaly, NETs)", "Approved", True, True,
        "Approved depot somatostatin analogue.", "Gallstones, GI effects.", ["FDA prescribing information", "CLARINET trial"]),
    "leuprolide": P("Leuprolide", ["lupron", "leuprorelin"], "Endocrine (GnRH agonist)",
        "GnRH agonist; downregulates sex-hormone production.", "A", "Approved (prostate cancer, endometriosis, CPP)",
        "Approved", True, True, "Widely used approved hormonal agent.", "Menopausal symptoms, bone-density loss, initial flare.",
        ["FDA prescribing information"]),
    "goserelin": P("Goserelin", ["zoladex"], "Endocrine (GnRH agonist)",
        "GnRH agonist depot.", "A", "Approved (prostate/breast cancer, endometriosis)", "Approved", True, True,
        "Approved hormonal depot.", "Hypogonadal effects; initial flare.", ["FDA prescribing information"]),
    "desmopressin": P("Desmopressin", ["ddavp", "minirin"], "Hormone (vasopressin analogue)",
        "Synthetic ADH analogue; antidiuretic.", "A", "Approved (diabetes insipidus, nocturnal enuresis, some bleeding)",
        "Approved", True, True, "Well-established approved peptide hormone.", "Hyponatraemia — fluid restriction needed.",
        ["FDA prescribing information"]),
    "glucagon": P("Glucagon", ["baqsimi", "gvoke"], "Hormone (metabolic)",
        "Counter-regulatory hormone; raises blood glucose.", "A", "Approved (severe hypoglycaemia)", "Approved",
        True, True, "Approved emergency hypoglycaemia treatment.", "Nausea; transient.", ["FDA prescribing information"]),
    "calcitonin": P("Calcitonin (salmon)", ["miacalcin", "fortical"], "Bone (hormone)",
        "Inhibits osteoclast-mediated bone resorption.", "B", "Approved (osteoporosis, hypercalcaemia, Paget's)",
        "Approved", True, True, "Approved but second-line for osteoporosis; modest efficacy, malignancy signal with long nasal use.",
        "Possible small cancer-risk signal with prolonged use.", ["FDA prescribing information"]),
    "icatibant": P("Icatibant", ["firazyr"], "Immune / vascular (bradykinin B2 antagonist)",
        "Bradykinin B2-receptor antagonist for hereditary angioedema attacks.", "A", "Approved (HAE)",
        "Limited / specialist use", True, True, "Approved acute HAE treatment.", "Injection-site reactions.",
        ["FDA prescribing information"]),
    "enfuvirtide": P("Enfuvirtide", ["fuzeon", "t-20"], "Antiviral (HIV fusion inhibitor)",
        "Blocks HIV gp41-mediated fusion.", "A", "Approved (HIV, salvage therapy)", "Limited / specialist use",
        True, True, "Approved but now rarely used (injections, newer orals preferred).", "Injection-site reactions.",
        ["FDA prescribing information"]),
    "gonadorelin": P("Gonadorelin", ["gnrh"], "Endocrine (GnRH)",
        "Native GnRH; diagnostic and fertility uses.", "B", "Approved (diagnostic/fertility, limited)", "Limited use",
        True, True, "Approved for specific endocrine/fertility uses; 'testosterone support' use is off-label.",
        "Generally mild in approved use.", ["Approved-indication human data"]),
    # ---------------- Neuro / mitochondrial / repair — investigational
    "cerebrolysin": P("Cerebrolysin", [], "Neuropeptide (neurotrophic mixture)",
        "Porcine-brain peptide mixture with neurotrophic claims.", "C", "Not approved",
        "Available / used (stroke, dementia adjunct) in some markets incl. India", True, False,
        "Used in parts of Asia/Europe for stroke and dementia; meta-analyses are mixed and often low-quality.",
        "Hypersensitivity; variable evidence.", ["Mixed-quality human trials / Cochrane reviews"]),
    "elamipretide": P("Elamipretide (SS-31)", ["ss-31", "mtp-131"], "Mitochondrial (investigational)",
        "Cardiolipin-targeting peptide; stabilises mitochondrial membranes.", "C", "Investigational (not approved)",
        "Not approved", True, False, "Human trials in mitochondrial and cardiac disease are mixed; not approved.",
        "Injection-site reactions; efficacy unproven.", ["Phase-II trials (mixed)"]),
    "humanin": P("Humanin", [], "Mitochondrial-derived (investigational)",
        "Mitochondrial-derived peptide; cytoprotective/metabolic signalling.", "D", "Not approved",
        "Not approved", False, False, "Interesting longevity-associated biology; essentially no human therapeutic data.",
        "Unknown human safety.", ["Preclinical only"]),
    "kisspeptin": P("Kisspeptin", [], "Neuropeptide (reproductive)",
        "Upstream regulator of GnRH; reproductive-axis research.", "C", "Investigational", "Not approved",
        True, False, "Active human research for fertility and sexual function; not an approved therapy.",
        "Early-stage; safety under study.", ["Phase-I/II reproductive studies"]),
    "dsip": P("DSIP (delta sleep-inducing peptide)", [], "Neuropeptide (investigational)",
        "Peptide associated with sleep modulation.", "D", "Not approved", "Not approved (research-chem)",
        True, False, "Old, weak and unreplicated human sleep data; popular online, not evidence-based.",
        "Unregulated sourcing.", ["Small unreplicated human studies"]),
    "ll37": P("LL-37 (cathelicidin)", ["cathelicidin"], "Immune / antimicrobial (investigational)",
        "Host-defence antimicrobial peptide.", "D", "Not approved", "Not approved (research-chem)", False, False,
        "Important innate-immunity biology; no human therapeutic approval or trials supporting injectable 'wellness' use.",
        "Pro-inflammatory potential; unknown human safety.", ["Preclinical"]),
    "kpv": P("KPV", [], "Immune / repair (α-MSH fragment)",
        "Tripeptide fragment of α-MSH with anti-inflammatory signalling in models.", "D", "Not approved",
        "Not approved (research-chem)", False, False, "Anti-inflammatory claims rest on animal/cell data; no human trials.",
        "Unknown human safety; sourcing risk.", ["Preclinical"]),
    "larazotide": P("Larazotide", ["at-1001"], "GI / barrier (investigational)",
        "Tight-junction regulator studied for coeliac disease.", "C", "Investigational (Phase 3 missed primary)",
        "Not approved", True, False, "Phase-3 coeliac trial did not meet its primary endpoint; not approved.",
        "Generally well tolerated in trials.", ["Phase-III coeliac trial (negative primary)"]),
    "afamelanotide": P("Afamelanotide (Melanotan I)", ["scenesse", "melanotan 1"], "Neuropeptide (melanocortin agonist)",
        "Melanocortin-1 agonist; increases eumelanin (photoprotection).", "B", "Approved (erythropoietic protoporphyria)",
        "Not approved (orphan)", True, True, "Approved for a rare photodermatosis — distinct from the unapproved Melanotan II.",
        "Implant-site reactions, nausea.", ["FDA/EMA approval (EPP)", "Phase-III EPP trials"]),
    "argireline": P("Argireline (acetyl hexapeptide-8)", ["acetyl hexapeptide-8", "ah8"], "Cosmetic (topical)",
        "SNAP-25-mimicking peptide marketed as a topical 'Botox-like' wrinkle agent.", "C",
        "Cosmetic ingredient (topical)", "Topical cosmetic use", True, False,
        "Modest topical cosmetic evidence for fine lines; not a drug, effect is small.", "Topical, generally well tolerated.",
        ["Small cosmetic studies"]),
    "matrixyl": P("Matrixyl (palmitoyl pentapeptide)", ["palmitoyl pentapeptide-4", "matrixyl 3000"], "Cosmetic (topical)",
        "Collagen-stimulating signal peptide in skincare.", "C", "Cosmetic ingredient (topical)", "Topical cosmetic use",
        True, False, "Reasonable topical cosmetic evidence for skin texture; cosmetic, not therapeutic.",
        "Topical, generally well tolerated.", ["Cosmetic dermatology studies"]),
}

GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3}


def family(pclass: str) -> str:
    """Coarse bucket for the UI filter (the full `pclass` stays for display). Keyword-mapped to ~10 families."""
    s = pclass.lower()
    if "cosmetic" in s:
        return "Cosmetic / skin"
    if "growth-hormone" in s or "ghrh" in s or "ghrp" in s or "secretagogue" in s:
        return "Growth-hormone axis"
    if any(k in s for k in ("glp", "gip", "amylin", "incretin", "glucagon", "gc-c", "mc4r")):
        return "Metabolic / weight"
    if "somatostatin" in s or "gnrh" in s or "endocrine" in s:
        return "Endocrine / hormonal"
    if "bone" in s or "pth" in s:
        return "Bone"
    if "mitochond" in s or "longevity" in s:
        return "Mitochondrial / longevity"
    if any(k in s for k in ("neuro", "melanocortin", "sleep", "reproductive", "nootropic", "anxiolytic")):
        return "Neuro / behavioural"
    if "immune" in s or "antimicrob" in s or "vascular" in s:
        return "Immune / inflammatory"
    if "antiviral" in s:
        return "Antiviral"
    if s.startswith("gi") or "barrier" in s or "/ gi" in s:
        return "Gut / GI"
    if "repair" in s or "research" in s:
        return "Repair / research"
    if "hormon" in s or "metabolic" in s:
        return "Metabolic / weight"
    return "Other"


CLASSES = sorted({family(p["pclass"]) for p in PEPTIDES.values()})


def _match(p: dict, pid: str, q: str) -> bool:
    if not q:
        return True
    q = q.lower()
    return q in pid or q in p["name"].lower() or any(q in a for a in p["aliases"]) or q in p["pclass"].lower()


def library(q: str = "", pclass: str | None = None) -> dict:
    """Full clinician reference: every field, graded, region-aware, with citations. For the doctor surface."""
    items = []
    for pid, p in PEPTIDES.items():
        if not _match(p, pid, q):
            continue
        if pclass and family(p["pclass"]) != pclass:
            continue
        items.append({"id": pid, "family": family(p["pclass"]), **{k: p[k] for k in _F}})
    items.sort(key=lambda x: (GRADE_RANK.get(x["grade"], 9), x["name"]))
    return {"peptides": items, "classes": CLASSES, "count": len(items),
            "disclaimer": ("Reference for clinicians. Evidence grades and regulatory status are point-in-time; verify "
                           "against current FDA/CDSCO status before any clinical decision. Telomy does not sell, "
                           "prescribe or facilitate access to any peptide.")}


def get(pid: str) -> dict | None:
    p = PEPTIDES.get(pid)
    return {"id": pid, **{k: p[k] for k in _F}} if p else None


def member_view(q: str = "") -> dict:
    """What a MEMBER may see: name, class, grade and the regulatory reality + a route-to-clinician gate. No mechanism-
    as-howto, no dosing, no sourcing, never a recommendation — mirrors protocols.py's clinician-gated `light` view."""
    items = []
    for pid, p in PEPTIDES.items():
        if not _match(p, pid, q):
            continue
        approved = p["advised"]
        items.append({"id": pid, "name": p["name"], "pclass": p["pclass"], "family": family(p["pclass"]), "grade": p["grade"],
                      "regulatory": f"FDA: {p['fda']} · India: {p['cdsco']}",
                      "claim": p["summary"], "doctor_gate": True,
                      "flag": None if approved else "Not an approved therapy — research-grade / not advised outside a trial."})
    items.sort(key=lambda x: (GRADE_RANK.get(x["grade"], 9), x["name"]))
    return {"peptides": items, "count": len(items),
            "note": ("Information only. Peptides — including any you have read about — are shown by name so you can "
                     "discuss them with a doctor on your care team. Telomy never recommends, doses, prescribes or "
                     "sources peptides, and many are unapproved or illegal to sell in India."),
            "disclaimer": "Not medical advice. Discuss any peptide with your clinician."}
