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
}

CLASSES = sorted({p["pclass"] for p in PEPTIDES.values()})
GRADE_RANK = {"A": 0, "B": 1, "C": 2, "D": 3}


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
        if pclass and p["pclass"] != pclass:
            continue
        items.append({"id": pid, **{k: p[k] for k in _F}})
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
        items.append({"id": pid, "name": p["name"], "pclass": p["pclass"], "grade": p["grade"],
                      "regulatory": f"FDA: {p['fda']} · India: {p['cdsco']}",
                      "claim": p["summary"], "doctor_gate": True,
                      "flag": None if approved else "Not an approved therapy — research-grade / not advised outside a trial."})
    items.sort(key=lambda x: (GRADE_RANK.get(x["grade"], 9), x["name"]))
    return {"peptides": items, "count": len(items),
            "note": ("Information only. Peptides — including any you have read about — are shown by name so you can "
                     "discuss them with a doctor on your care team. Telomy never recommends, doses, prescribes or "
                     "sources peptides, and many are unapproved or illegal to sell in India."),
            "disclaimer": "Not medical advice. Discuss any peptide with your clinician."}
