"""Lab report PDF → structured markers.

Text-layer parser for tabular lab reports: each result line is "<test> <value> <unit> <range> <flag>".
Every parsed marker keeps the report's own reference range and flag (never replaced by app defaults).
Unknown test names are returned as `unmatched` so the verify screen can show them instead of dropping them.
"""
import io
import re
from datetime import datetime

from pypdf import PdfReader

from .catalog import MARKERS, match_marker, status_for

PANEL_KEYWORDS = [
    ("urine", ["urine routine", "urinalysis"]),
    ("cgm", ["continuous glucose", "cgm"]),
    ("lung", ["spirometry", "lung function"]),
    ("cardio", ["ecg", "echocardiograph", "ankle-brachial", "pulse wave", "ambulatory blood pressure", "vascular function"]),
    ("functional", ["organic acids", "cortisol rhythm", "functional medicine"]),
    ("immune", ["autoimmun", "allergy", "immunity"]),
    ("micronutrients", ["iron studies", "micronutrient", "vitamins and minerals"]),
    ("hormones", ["thyroid", "hormone"]),
    ("gut", ["microbiome", "16s", "stool"]),
    ("proteomic", ["proteomic", "organ age"]),
    ("fitness", ["cardiopulmonary", "cpet", "vo2"]),
    ("bodycomp", ["dexa", "dxa", "body composition", "bioimpedance"]),
    ("ct", ["computed tomography", "calcium score", "ct coronary"]),
    ("mri", ["magnetic resonance", "mri"]),
    ("screening", ["sleep study", "polysomnography", "screening test"]),
    ("advanced", ["advanced cardio", "advanced panel", "nmr lipoprotein"]),
    ("bioage", ["biological age", "epigenetic", "pace of ageing", "pace of aging"]),
    ("genetic", ["genetic", "snp", "methylation snp", "genotype"]),
    ("metals", ["heavy metal", "provoked urine", "icp-ms"]),
    ("toxins", ["mycotoxin", "pesticide", "plasticis", "environmental toxin"]),
    ("blood", ["metabolic", "lipid", "haemoglobin", "hemoglobin", "cbc", "blood"]),
]

NUM = r"[-+]?\d+(?:\.\d+)?"
DATE_PATTERNS = ["%d-%b-%Y %H:%M", "%d-%b-%Y", "%Y-%m-%d"]


def _text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def vote_panel(markers: list[dict]) -> str | None:
    """Panel = where most recognised markers live (robust to words like 'thyroid' or 'ECG gating' in headers)."""
    from collections import Counter
    c = Counter(MARKERS[m["marker_id"]][1] for m in markers if m.get("marker_id") in MARKERS)
    if not c:
        return None
    top, n = c.most_common(1)[0]
    return top if n * 2 >= sum(c.values()) else None


def classify_panel(text: str) -> str:
    head = text[:600].lower()
    for panel, words in PANEL_KEYWORDS:
        if any(w in head for w in words):
            return panel
    return "blood"


def _date(text: str) -> str | None:
    m = re.search(r"Collected\s+(\d{2}-[A-Za-z]{3}-\d{4}(?:\s+\d{2}:\d{2})?)", text)
    raw = m.group(1) if m else None
    if not raw:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        raw = m.group(1) if m else None
    if not raw:
        return None
    for fmt in DATE_PATTERNS:
        try:
            return datetime.strptime(raw.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _range(s: str):
    s = s.replace("–", "-").replace("—", "-").strip()
    m = re.match(rf"^({NUM})\s*-\s*({NUM})$", s)
    if m:
        return float(m.group(1)), float(m.group(2)), s
    m = re.match(rf"^[<≤]\s*({NUM})$", s)
    if m:
        return None, float(m.group(1)), s
    m = re.match(rf"^[>≥]\s*({NUM})$", s)
    if m:
        return float(m.group(1)), None, s
    return None, None, s


FLAGS = {"H", "L", "HIGH", "LOW", "DETECTED", "RISK"}


def parse_line(line: str):
    mid = match_marker(line)
    if not mid:
        return None
    spec = MARKERS[mid]
    alias = max((a for a in spec[6] if line.lower().startswith(a)), key=len)
    # Skip the alias plus any parenthetical/rsID suffix that belongs to the test name.
    rest = line[len(alias):]
    rest = re.sub(r"^\s*(\([^)]*\))?", "", rest).strip()
    tokens = rest.split()
    flag = ""
    if tokens and tokens[-1].upper() in FLAGS:
        flag = tokens.pop().upper()
    rest = " ".join(tokens)

    m = re.match(rf"^({NUM})\s*(.*)$", rest)
    if m and spec[5] not in ("variant", "absent"):
        value = float(m.group(1))
        tail = m.group(2)
        unit = spec[2]
        if unit and tail.startswith(unit):
            tail = tail[len(unit):].strip()
        else:
            parts = tail.split(" ", 1)
            if parts and not re.match(rf"^[<>≤≥]|^{NUM}", parts[0]):
                unit = parts[0]
                tail = parts[1] if len(parts) > 1 else ""
        lo, hi, ref_text = _range(tail)
    else:
        # categorical: genotype / detection result, value runs until the unit/range words
        cut = re.split(r"\s+(genotype|percentile|Not detected$)", rest)
        value = cut[0].strip()
        if spec[5] == "absent":
            value = "Detected (low)" if rest.lower().startswith("detected") else "Not detected"
        if spec[5] == "variant" and value.endswith(" genotype"):
            value = value[: -len(" genotype")]
        value = re.sub(r"\s+genotype.*$", "", value)
        lo = hi = None
        ref_text = rest[len(cut[0]):].replace("genotype", "").strip()
        unit = spec[2]
        if mid.startswith("prs_"):
            num = re.match(r"(\d+)", value)
            value = float(num.group(1)) if num else value
    return {
        "marker_id": mid,
        "name": spec[0],
        "value": value,
        "unit": unit,
        "ref_low": lo,
        "ref_high": hi,
        "ref_text": ref_text,
        "flag": flag,
        "status": status_for(mid, value, lo, hi, flag),
    }


def _is_name_line(line: str) -> str | None:
    """A cell holding only a test name (optionally with a parenthetical / rsID)."""
    mid = match_marker(line)
    if not mid:
        return None
    alias = max((a for a in MARKERS[mid][6] if line.lower().startswith(a)), key=len)
    rest = re.sub(r"^\s*(\([^)]*\))?\s*", "", line[len(alias):])
    return mid if rest == "" else None


def _rangey(s: str) -> bool:
    s = s.replace("–", "-")
    return bool(re.match(rf"^([<>≤≥]\s*{NUM}|{NUM}\s*-\s*{NUM})$", s)) or "typical" in s or s in ("—", "Not detected") \
        or "chronological" in s or "/" in s and len(s) < 12 and not re.match(r"^[µa-zA-Z%³²]", s)


def parse_cells(lines: list[str], panel: str) -> list[dict]:
    """Table extracted as one cell per line: name, value, [unit], [range], [flag]."""
    out, seen, i = [], set(), 0
    while i < len(lines):
        mid = _is_name_line(lines[i])
        if not mid or i + 1 >= len(lines):
            i += 1
            continue
        if mid == "creatinine" and panel == "metals":
            mid = "urine_creat"
        spec = MARKERS[mid]
        raw_value = lines[i + 1]
        j = i + 2
        unit, ref_text, flag = "", "", ""
        if j < len(lines) and (lines[j] == spec[2] or not _is_name_line(lines[j]) and lines[j].upper() not in FLAGS
                               and not _rangey(lines[j]) and spec[2] != ""):
            unit, j = lines[j], j + 1
        if j < len(lines) and not _is_name_line(lines[j]) and lines[j].upper() not in FLAGS:
            ref_text, j = lines[j], j + 1
        if j < len(lines) and lines[j].upper() in FLAGS:
            flag, j = lines[j].upper(), j + 1
        num = re.match(rf"^({NUM})", raw_value.replace("+", ""))
        if spec[5] in ("variant", "absent") or not num:
            value = raw_value
            if mid.startswith("prs_") and num:
                value = float(num.group(1))
        else:
            value = float(raw_value) if re.match(rf"^{NUM}$", raw_value) else float(num.group(1))
        lo, hi, _ = _range(ref_text) if ref_text else (None, None, "")
        if mid not in seen:
            seen.add(mid)
            out.append({"marker_id": mid, "name": spec[0], "value": value, "unit": unit or spec[2],
                        "ref_low": lo, "ref_high": hi, "ref_text": ref_text, "flag": flag,
                        "status": status_for(mid, value, lo, hi, flag)})
        i = j
    return out


def parse_pdf(pdf_bytes: bytes, filename: str = "") -> dict:
    text = _text(pdf_bytes)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # Title = the first heading-like line after the lab name / disclaimer, not a demographics row ("Age / Sex").
    skip = ("patient", "age / sex", "age/sex", "test data", "referred", "collected", "sample diagnostics")
    title = next((l for l in lines[:10] if len(l) > 12 and not l.lower().startswith(skip) and any(k in l.lower() for k in
                  ["panel", "microbiome", "age", "metals", "toxins", "genetic", "test", "composition", "ct", "mri",
                   "imaging", "study", "proteom", "dexa", "thyroid", "hormone", "iron", "vitamin", "ecg", "spirometry", "lung",
                   "glucose", "allergy", "urine", "function", "assessment"])), filename)
    panel = classify_panel(text)
    markers, unmatched = parse_cells(lines, panel), []
    if not markers:  # fall back to one-row-per-line layouts
        seen = set()
        for line in lines:
            parsed = parse_line(line)
            if parsed and parsed["marker_id"] not in seen:
                markers.append(parsed)
                seen.add(parsed["marker_id"])
    panel = vote_panel(markers) or panel
    return {
        "title": title,
        "panel": panel,
        "collected_on": _date(text),
        "markers": markers,
        "unmatched": unmatched[:20],
        "is_test_data": "TEST DATA" in text.upper(),
    }
