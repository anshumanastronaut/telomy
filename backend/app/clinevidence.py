"""Clinical-evidence Q&A for the doctor platform — the "accurate like Vera" engine.

Vera Health's accuracy comes from a retrieve → grade → answer pipeline: it pulls real medical literature and
guidelines, grades the sources, and only THEN writes a short, cited answer. This module does the same, grounded on
PubMed (NCBI E-utilities — free, no API key), graded by publication type, with the answer composed by the grounded
LLM (telomy_llm → Claude when a key is set) and every claim tied to a numbered source.

Design rules (keep this non-device clinical decision support):
- The answer is generated ONLY from the retrieved abstracts; citations are always shown so the clinician can verify.
- Source strength is graded and surfaced (A strong … D weak), including a note when evidence is thin.
- No autonomous directives: bottom-line + exceptions + the evidence behind it, then "verify against the source".
- Everything is cached briefly; PubMed is called politely (≤3 req/s, short timeouts).
"""
from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from . import telomy_llm

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_TOOL = "telomy"
_EMAIL = "support@telomy.me"          # NCBI asks callers to identify themselves
_CACHE: dict[str, tuple[float, object]] = {}
_TTL = 3600.0

# Publication type → (grade letter, human label). Higher in this list wins when an article has several types.
_GRADE_RULES: list[tuple[str, str, str]] = [
    ("meta-analysis", "A", "Meta-analysis"),
    ("systematic review", "A", "Systematic review"),
    ("practice guideline", "A", "Practice guideline"),
    ("guideline", "A", "Guideline"),
    ("randomized controlled trial", "B", "Randomized controlled trial"),
    ("controlled clinical trial", "B", "Controlled trial"),
    ("clinical trial, phase iii", "B", "Phase III trial"),
    ("clinical trial", "C", "Clinical trial"),
    ("comparative study", "C", "Comparative study"),
    ("observational study", "C", "Observational study"),
    ("multicenter study", "C", "Multicenter study"),
    ("case reports", "D", "Case report"),
    ("review", "D", "Narrative review"),
    ("editorial", "D", "Editorial"),
    ("letter", "D", "Letter"),
    ("comment", "D", "Comment"),
]
_GRADE_LABEL = {"A": "Strong", "B": "Moderate", "C": "Limited", "D": "Weak"}


_RANK = {"A": 3, "B": 2, "C": 1, "D": 0}

# PubMed often tags major trials/reviews only as "Journal Article", so fall back to title/abstract signals.
_TEXT_RULES: list[tuple[str, str, str]] = [
    ("systematic review", "A", "Systematic review"),
    ("meta-analysis", "A", "Meta-analysis"),
    ("meta analysis", "A", "Meta-analysis"),
    ("randomized controlled trial", "B", "Randomized controlled trial"),
    ("randomised controlled trial", "B", "Randomized controlled trial"),
    ("double-blind", "B", "Randomized trial"),
    ("placebo-controlled", "B", "Randomized trial"),
    ("randomly assigned", "B", "Randomized trial"),
    ("randomized", "B", "Randomized trial"),
    ("randomised", "B", "Randomized trial"),
    ("prospective cohort", "C", "Cohort study"),
    ("retrospective", "C", "Observational study"),
    ("cohort", "C", "Cohort study"),
    ("case-control", "C", "Case-control study"),
]


def _grade(pub_types: list[str], title: str = "", abstract: str = "") -> tuple[str, str]:
    """Strongest grade from the publication types, with a title/abstract fallback for papers PubMed tags only as
    'Journal Article'. Returns the stronger of the two signals; defaults to D."""
    letter, label = "D", "Other"
    low = [p.lower() for p in pub_types]
    for needle, lt, lb in _GRADE_RULES:
        if any(needle in p for p in low):
            letter, label = lt, lb
            break
    text = f"{title} {abstract[:600]}".lower()
    for needle, lt, lb in _TEXT_RULES:
        if needle in text and _RANK[lt] > _RANK[letter]:
            letter, label = lt, lb
            break
    return letter, label


def _get(path: str, params: dict) -> bytes:
    params = {**params, "tool": _TOOL, "email": _EMAIL}
    url = f"{EUTILS}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": f"{_TOOL}/1.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.read()


def _esearch(query: str, k: int) -> list[str]:
    data = _get("esearch.fcgi", {"db": "pubmed", "term": query, "retmax": k, "retmode": "json", "sort": "relevance"})
    import json as _json
    ids = _json.loads(data).get("esearchresult", {}).get("idlist", [])
    return list(ids)[:k]


def _text(el: ET.Element | None) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def _efetch(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    data = _get("efetch.fcgi", {"db": "pubmed", "id": ",".join(pmids), "rettype": "abstract", "retmode": "xml"})
    root = ET.fromstring(data)
    out: list[dict] = []
    for art in root.findall(".//PubmedArticle"):
        pmid = _text(art.find(".//PMID"))
        title = _text(art.find(".//ArticleTitle"))
        journal = _text(art.find(".//Journal/ISOAbbreviation")) or _text(art.find(".//Journal/Title"))
        year = _text(art.find(".//JournalIssue/PubDate/Year")) or _text(art.find(".//JournalIssue/PubDate/MedlineDate"))[:4]
        # abstract may be several labelled sections
        parts = []
        for ab in art.findall(".//Abstract/AbstractText"):
            label = ab.get("Label")
            txt = _text(ab)
            parts.append(f"{label}: {txt}" if label else txt)
        abstract = " ".join(p for p in parts if p)
        pub_types = [_text(pt) for pt in art.findall(".//PublicationTypeList/PublicationType")]
        grade, grade_label = _grade(pub_types, title, abstract)
        out.append({
            "pmid": pmid, "title": title, "journal": journal, "year": year,
            "abstract": abstract, "pub_types": pub_types, "grade": grade, "grade_label": grade_label,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    # keep the esearch (relevance) order
    order = {p: i for i, p in enumerate(pmids)}
    out.sort(key=lambda a: order.get(a["pmid"], 999))
    return out


def search(query: str, k: int = 6) -> list[dict]:
    """Retrieve the top-k PubMed articles for a clinical query, each graded by publication type."""
    key = f"s|{k}|{query.lower().strip()}"
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return list(hit[1])  # type: ignore[arg-type]
    try:
        arts = _efetch(_esearch(query, k))
    except Exception as exc:  # noqa: BLE001 — network/parse issues degrade to "no sources"
        return [{"_error": f"{type(exc).__name__}: {str(exc)[:120]}"}]
    if len(_CACHE) > 300:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = (time.time(), arts)
    return arts


SYSTEM = """You are Telomy's clinical evidence assistant for licensed clinicians. You answer a clinical question using
ONLY the numbered SOURCES provided (PubMed abstracts and guidelines). Write for a doctor, not a patient.

Format every answer as:
1. Bottom line — the direct answer in 1–3 sentences.
2. Key points — the specifics (doses, thresholds, magnitudes, populations) with an inline citation [n] after each claim.
3. Caveats / when it differs — exceptions, contraindications, conflicting evidence, and the strength of the evidence.

Rules: cite the source number [n] for every factual claim; never state a fact that is not supported by a source;
if the sources do not answer the question, say so plainly and say what evidence would be needed; do not give an
autonomous directive — support the clinician's judgement; note when evidence is weak or a guideline may be dated.
Be concise. Reply with ONLY a JSON object: {"answer": string, "used": [int], "confidence": number 0-1}."""

_SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}, "used": {"type": "array"},
           "confidence": {"type": "number"}}}

DISCLAIMER = ("Decision support for licensed clinicians — not a diagnosis or a directive. "
              "Verify every point against the cited source and the patient's full context.")


def ask(question: str, k: int = 6) -> dict:
    """Retrieve → grade → cited answer. Returns {answer, citations, overall_grade, engine, disclaimer, ...}."""
    q = (question or "").strip()
    if not q:
        return {"error": "Ask a clinical question."}
    arts = search(q, k)
    if arts and arts[0].get("_error"):
        return {"answer": "", "citations": [], "error": "Couldn't reach PubMed just now — try again.",
                "disclaimer": DISCLAIMER}
    arts = [a for a in arts if a.get("abstract")]  # need text to ground on
    if not arts:
        return {"answer": "No usable published evidence was found for that question. Try rephrasing with the "
                          "condition, population and intervention.", "citations": [], "overall_grade": None,
                "engine": "pubmed", "disclaimer": DISCLAIMER}

    # grounding context: numbered sources with their grade and abstract
    blocks = []
    for i, a in enumerate(arts, 1):
        blocks.append(f"[{i}] {a['title']} — {a['journal']} {a['year']} "
                      f"(evidence: {a['grade']} {a['grade_label']}; PMID {a['pmid']}).\n{a['abstract']}")
    context = "SOURCES:\n\n" + "\n\n".join(blocks)

    out = telomy_llm.ask(SYSTEM, context, q, [], _SCHEMA, max_tokens=1400, skip_guard=True)
    citations = [{"n": i, "pmid": a["pmid"], "title": a["title"], "journal": a["journal"], "year": a["year"],
                  "grade": a["grade"], "grade_label": a["grade_label"], "url": a["url"]} for i, a in enumerate(arts, 1)]
    best = min((a["grade"] for a in arts), default="D")  # 'A' < 'B' ... so min = strongest
    overall = {"grade": best, "label": _GRADE_LABEL.get(best, "")}

    if not out or "_error" in out or not str(out.get("answer") or "").strip():
        # retrieval worked but no LLM provider (or it failed): still return the graded evidence list
        reason = out.get("_error") if out else "no model configured"
        return {"answer": "", "citations": citations, "overall_grade": overall, "engine": "pubmed",
                "notice": f"Showing the graded evidence; connect the cloud model for a written synthesis ({reason}).",
                "disclaimer": DISCLAIMER}

    used = [n for n in (out.get("used") or []) if isinstance(n, int) and 1 <= n <= len(citations)]
    return {"answer": str(out["answer"]).strip(), "citations": citations, "used": used or [c["n"] for c in citations],
            "overall_grade": overall, "confidence": out.get("confidence", 0.7),
            "engine": out.get("engine", telomy_llm.model_name()), "disclaimer": DISCLAIMER}
