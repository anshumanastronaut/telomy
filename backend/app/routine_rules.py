"""Rules for the routine panels most people actually have (CBC with absolute counts, LFT, KFT, thyroid, lipids).

Added 2026-10-19: the cross-panel rule set only knew advanced panels (ApoB, MTHFR, imaging), so a person with a normal
Indian health-check report got zero insights. These rules read the report's OWN reference range, say what the pattern
commonly means in plain words, list what a doctor usually checks next, and never diagnose. Sources: Dacie & Lewis
Practical Haematology 12th ed.; BCSH/BSH guidance on thrombocytopenia and neutropenia; Tietz clinical chemistry.
"""
from . import engine
from .catalog import MARKERS


def _get(L, m):
    r = L.get(m)
    if not r or r["value_num"] is None:
        return None
    return {"v": r["value_num"], "lo": r["ref_low"], "hi": r["ref_high"], "d": r["collected_on"], "unit": MARKERS.get(m, ("", "", ""))[2]}


def _low(x):
    return x and x["lo"] is not None and x["v"] < x["lo"]


def _high(x):
    return x and x["hi"] is not None and x["v"] > x["hi"]


def _fmt(name, x):
    lo, hi = x["lo"], x["hi"]
    rng = f"{lo:g}–{hi:g}" if lo is not None and hi is not None else f"> {lo:g}" if lo is not None else f"< {hi:g}" if hi is not None else None
    return (f"{name} {x['v']:g} {x['unit']}" + (f" (lab range {rng})" if rng else "")).replace("  ", " ")


def routine_patterns() -> list[dict]:
    L = engine.latest_values()
    out, covered = [], set()

    def add(key, title, body, markers, medical=True, conf=0.7, direction="harmful"):
        ev = [{"type": "marker", "marker_id": m, "name": MARKERS[m][0], "value": L[m]["value_num"], "unit": MARKERS[m][2],
               "day": L[m]["collected_on"], "status": L[m]["status"]} for m in markers if m in L]
        covered.update(markers)
        out.append({"id": engine._iid("routine", key), "kind": "cross_panel", "title": title, "body": body, "confidence": conf,
                    "n": len(ev), "direction": direction, "medical": medical, "evidence": ev,
                    "receipts": {"method": "Routine-panel rule set (report's own reference ranges)", "rule": key,
                                 "panels": sorted({MARKERS[m][1] for m in markers if m in L}), "version": engine.ENGINE_VERSION}})

    plt, mpv, anc, wbc, hb, mcv, rdw = (_get(L, m) for m in ("platelets", "mpv", "anc", "wbc_total", "hemoglobin", "mcv", "rdw"))
    lymph, ment, alp, ferr = _get(L, "lymph_pct"), _get(L, "mentzer"), _get(L, "alp"), _get(L, "ferritin")
    low_lines = [n for n, x in (("platelets", plt), ("neutrophils", anc), ("haemoglobin", hb)) if _low(x)]
    if len(low_lines) >= 2:
        parts = [_fmt("Platelets", plt) if _low(plt) else None, _fmt("absolute neutrophils", anc) if _low(anc) else None,
                 _fmt("haemoglobin", hb) if _low(hb) else None]
        add("bicytopenia", f"Two blood cell lines are below range ({' and '.join(low_lines)})",
            f"On {plt['d'] if plt else anc['d']}: {'; '.join(p for p in parts if p)}. When more than one cell line is low together, doctors "
            "usually repeat the full blood count with a peripheral smear before reading anything into it. Common, often temporary "
            "reasons are a recent viral infection, low B12 or folate, some medicines, alcohol, or the spleen holding on to cells; "
            "less often it points to the bone marrow. Please show this to a doctor (a physician or haematologist); a repeat count, "
            "smear, B12, folate and a liver check are the usual next steps. I won't guess the cause.",
            ["platelets", "anc", "hemoglobin", "wbc_total"], conf=0.82)
    if _low(plt) and _high(mpv):
        add("big_platelets", "Platelets are fewer but larger than usual",
            f"{_fmt('Platelets', plt)} with {_fmt('mean platelet volume', mpv)}. Large platelets with a low count usually mean the body "
            "is making new platelets quickly to replace ones being used up, or that platelets are naturally large (an inherited trait). "
            "Clumping in the sample tube can also make the machine under-count them — a repeat in a citrate tube with a smear checks that. "
            "Avoid starting blood-thinning supplements (fish oil, high-dose vitamin E, ginkgo, curcumin) until a doctor has seen this.",
            ["platelets", "mpv", "plateletcrit"], conf=0.78)
    elif _low(plt) and "platelets" not in covered:
        add("low_platelets", "Platelets are below range", f"{_fmt('Platelets', plt)}. A repeat count with a smear is the usual first step; "
            "see a doctor promptly if you notice easy bruising, gum or nose bleeds.", ["platelets", "mpv"], conf=0.75)
    if _low(anc) and "anc" not in covered:
        lv = f" Lymphocytes are relatively high ({lymph['v']:g} %), a pattern often seen for a few weeks after a viral illness." if _high(lymph) else ""
        add("neutropenia", "Neutrophils (infection-fighting white cells) are a little low",
            f"{_fmt('Absolute neutrophil count', anc)}.{lv} Mild, isolated low neutrophils are common and often harmless, but a doctor "
            "will usually repeat the count in 4–6 weeks and may check B12, folate and copper.", ["anc", "neutrophil_pct", "lymph_pct", "nlr"], conf=0.72)
    elif _low(anc) and _high(lymph):
        covered.update(["lymph_pct", "neutrophil_pct", "nlr"])
    if _low(mcv) and not _low(hb):
        mz = f" The Mentzer index is {ment['v']:g} (below 13 leans towards a thalassaemia trait, above 13 towards iron deficiency)." if ment else ""
        fer = f" Ferritin was {ferr['v']:g} ng/mL." if ferr else " Ferritin (iron stores) wasn't measured — that is the test that tells these apart."
        add("small_cells", "Red cells are slightly small, without anaemia",
            f"{_fmt('MCV', mcv)} with normal haemoglobin.{mz}{fer} The two usual reasons are early iron deficiency and a "
            "thalassaemia trait (common in India and harmless on its own, but worth knowing before having children). "
            "Don't take iron until ferritin confirms you need it.", ["mcv", "rdw", "mentzer", "ferritin", "hemoglobin"], medical=True, conf=0.7)
    if _low(alp):
        add("low_alp", "Alkaline phosphatase is slightly low",
            f"{_fmt('ALP', alp)}. Mildly low ALP on its own is usually not significant; low zinc or magnesium, low thyroid "
            "function, or rarely an inherited bone condition (hypophosphatasia) can cause it. Recheck with the next test; "
            "nuts, seeds, legumes and whole grains cover zinc and magnesium.", ["alp"], medical=False, conf=0.55, direction="neutral")
    rest = [m for m, r in L.items() if r["status"] == "out_of_range" and m not in covered and m in MARKERS and r["value_num"] is not None]
    if rest:
        add("other_flags", f"{len(rest)} other value{'s' if len(rest) != 1 else ''} just outside the lab range",
            "; ".join(_fmt(MARKERS[m][0], _get(L, m)) for m in rest[:8]) + ". On their own these are usually minor; "
            "they are worth rechecking with your next routine test.", rest[:8], medical=False, conf=0.45, direction="neutral")
    return out
