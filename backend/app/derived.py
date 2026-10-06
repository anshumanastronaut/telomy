"""Derived markers, personalised zones, disease-risk matrix, retest nudges and action plans.

Derived values are computed only when every input exists; each carries its formula and inputs.
"""
import math
from datetime import date

from . import db, engine
from .catalog import MARKERS
from .catalog_ext import ACTIONS, CONCERNS, EVIDENCE, RETEST_DAYS, RETEST_PREP, ZONES


def _latest_nums() -> dict[str, dict]:
    out = {}
    for mid, r in engine.latest_values().items():
        out[mid] = r
    return out


def _n(L, m):
    r = L.get(m)
    return r["value_num"] if r and r["value_num"] is not None else None


def ckd_epi_2021(creat: float, age: float, sex: str) -> float:
    k, a = (0.7, -0.241) if sex == "female" else (0.9, -0.302)
    v = 142 * min(creat / k, 1) ** a * max(creat / k, 1) ** -1.200 * 0.9938 ** age
    return v * 1.012 if sex == "female" else v


def ckd_epi_cys_2012(cys: float, age: float, sex: str) -> float:
    v = 133 * min(cys / 0.8, 1) ** -0.499 * max(cys / 0.8, 1) ** -1.328 * 0.996 ** age
    return v * 0.932 if sex == "female" else v


def derived() -> list[dict]:
    L = _latest_nums()
    p = engine.profile()
    age = engine.age_on() or 0
    sex = p.get("sex", "male")
    h = (p.get("height_cm") or 0) / 100
    out = []

    def add(key, name, value, unit, formula, inputs, zones=None, interp=None):
        out.append({"id": key, "name": name, "value": round(value, 2), "unit": unit, "formula": formula,
                    "inputs": {k: _n(L, k) for k in inputs}, "as_of": max(L[k]["collected_on"] for k in inputs if k in L),
                    "interpretation": interp})

    tg, hdl, glu = _n(L, "tg"), _n(L, "hdl"), _n(L, "glucose")
    if tg and hdl:
        r = tg / hdl
        add("tg_hdl", "Triglyceride / HDL ratio", r, "", "TG ÷ HDL (mg/dL)", ["tg", "hdl"],
            interp="Under 2 is favourable; over 3 suggests insulin resistance and small dense LDL." if r else None)
        aip = math.log10((tg / 88.57) / (hdl / 38.67))
        add("aip", "Atherogenic index of plasma", aip, "", "log10(TG ÷ HDL) in mmol/L", ["tg", "hdl"],
            interp="< 0.11 low risk · 0.11–0.21 intermediate · > 0.21 high.")
    if tg and glu:
        tyg = math.log(tg * glu / 2)
        add("tyg", "TyG index", tyg, "", "ln(TG × glucose ÷ 2)", ["tg", "glucose"],
            interp="Above ~8.5 is associated with insulin resistance.")
    apob, apoa1 = _n(L, "apob"), _n(L, "apoa1")
    if apob and apoa1:
        add("apob_apoa1", "ApoB / ApoA1 ratio", apob / apoa1, "", "ApoB ÷ ApoA1", ["apob", "apoa1"],
            interp="Lower is better; > 0.9 (men) / > 0.8 (women) signals higher risk (INTERHEART).")
    ast, alt, plt = _n(L, "ast"), _n(L, "alt"), _n(L, "platelets")
    if ast and alt and plt and age:
        fib4 = age * ast / (plt * math.sqrt(alt))
        add("fib4", "FIB-4 liver fibrosis index", fib4, "", "age × AST ÷ (platelets × √ALT)", ["ast", "alt", "platelets"],
            interp="< 1.3 low likelihood of advanced fibrosis · 1.3–2.67 indeterminate (consider elastography) · > 2.67 high.")
    neu, lym = _n(L, "neutrophil_pct"), _n(L, "lymph_pct")
    if neu and lym:
        add("nlr", "Neutrophil / lymphocyte ratio", neu / lym, "", "neutrophil % ÷ lymphocyte %", ["neutrophil_pct", "lymph_pct"],
            interp="1–3 typical; persistently > 3 suggests systemic inflammation, < 0.7 can reflect viral response or stress.")
    wbc = _n(L, "wbc")
    if wbc and neu:
        add("anc", "Absolute neutrophil count", wbc * neu / 100, "10³/µL", "WBC × neutrophil %", ["wbc", "neutrophil_pct"],
            interp="< 1.5 is neutropenia.")
    cr = _n(L, "creatinine")
    if cr and age:
        add("egfr_cr", "eGFR (CKD-EPI 2021, creatinine)", ckd_epi_2021(cr, age, sex), "mL/min/1.73m²",
            "CKD-EPI 2021 race-free equation", ["creatinine"])
    cys = _n(L, "cystatin_c")
    if cys and age:
        e = ckd_epi_cys_2012(cys, age, sex)
        add("egfr_cys", "eGFR (cystatin C)", e, "mL/min/1.73m²", "CKD-EPI 2012 cystatin C", ["cystatin_c"],
            interp="Unaffected by muscle mass — compare with the creatinine eGFR.")
    ins = _n(L, "insulin")
    if ins and glu and "homa_ir" not in L:
        add("homa_ir_calc", "HOMA-IR (calculated)", ins * glu / 405, "", "insulin × glucose ÷ 405", ["insulin", "glucose"])
    if h and _n(L, "almi") is None:
        pass
    return out


def zone_for(mid: str, value, sex: str | None = None):
    z = ZONES.get(mid)
    if z is None or not isinstance(value, (int, float)):
        return None
    if isinstance(z, dict):
        z = z.get(sex or engine.profile().get("sex", "male")) or next(iter(z.values()))
    for upper, label, status in z:
        if upper is None or value < upper:
            return {"label": label, "status": status, "bands": [{"upper": u, "label": l, "status": s} for u, l, s in z]}
    return None


def concerns_for(mid: str) -> list[str]:
    return [c for c, ms in CONCERNS.items() if mid in ms]


def concern_groups() -> list[dict]:
    L = engine.latest_values()
    out = []
    for c, ms in CONCERNS.items():
        present = [m for m in ms if m in L]
        if not present:
            continue
        flagged = [m for m in present if L[m]["status"] in ("out_of_range", "variant", "detected")]
        out.append({"concern": c, "markers": [{"id": m, "name": MARKERS[m][0], "status": L[m]["status"],
                                                "value": L[m]["value_num"] if L[m]["value_num"] is not None else L[m]["value_text"],
                                                "unit": L[m]["unit"]} for m in present],
                    "flagged": len(flagged), "total": len(present)})
    return sorted(out, key=lambda x: -x["flagged"])


def retest_nudges(today: str) -> list[dict]:
    L = engine.latest_values()
    groups: dict[str, list] = {}
    for mid, r in L.items():
        if r["status"] not in ("out_of_range", "detected"):
            continue
        panel = MARKERS[mid][1]
        days = RETEST_DAYS.get(panel)
        if not days:
            continue
        since = (date.fromisoformat(today) - date.fromisoformat(r["collected_on"])).days
        if since >= days * 0.6:
            groups.setdefault(panel, []).append((mid, since, days))
    out = []
    for panel, items in groups.items():
        since = max(i[1] for i in items)
        out.append({"panel": panel, "days_since": since, "due_in": max(0, items[0][2] - since),
                    "markers": [{"id": m, "name": MARKERS[m][0]} for m, _, _ in items],
                    "prep": [RETEST_PREP[m] for m, _, _ in items if m in RETEST_PREP][:3],
                    "text": f"It's been {since} days since these were out of range. A retest tells you whether the change is holding."})
    return sorted(out, key=lambda x: -x["days_since"])


def _blocked(action, L) -> str | None:
    a = action.get("avoid_if", {})
    for k, thr in a.items():
        if k.endswith("_above"):
            m = k[:-6]
            v = _n(L, m)
            if v is not None and v > thr:
                return f"Avoid: your {MARKERS[m][0]} is {v}, already above {thr}."
        elif k.endswith("_below"):
            m = k[:-6]
            v = _n(L, m)
            if v is not None and v < thr:
                return f"Avoid: your {MARKERS[m][0]} is {v}, below {thr}."
        else:
            v = _n(L, k)
            if v is not None and v > thr:
                return f"Avoid: your {MARKERS[k][0]} is {v}."
    return None


def action_plan() -> dict:
    L = engine.latest_values()
    flagged = {m for m, r in L.items() if r["status"] in ("out_of_range", "in_range", "variant")}
    out = {"food": [], "supplement": [], "lifestyle": []}
    for a in ACTIONS:
        hits = [t for t in a["targets"] if t in flagged]
        if not hits:
            continue
        if a.get("requires") and L.get(a["requires"], {}).get("status") != "variant":
            continue
        gate = a.get("only_if_below", {})
        if gate and not all(_n(L, m) is not None and _n(L, m) < thr for m, thr in gate.items()):
            continue
        caution = None
        for m, thr in a.get("caution_if", {}).items():
            v = _n(L, m)
            if v is not None and v > thr:
                caution = a["caution"]
        out[a["kind"]].append({**{k: v for k, v in a.items() if k not in ("avoid_if", "requires", "caution_if", "only_if_below")},
                               "targets": [{"id": t, "name": MARKERS[t][0], "status": L[t]["status"]} for t in hits],
                               "avoid": _blocked(a, L), "caution": caution})
    for k in out:
        out[k].sort(key=lambda x: (x["avoid"] is not None, {"high": 0, "moderate": 1, "low": 2}[x["impact"]], -len(x["targets"])))
    return out


# ------------------------------------------------------------------ disease-risk matrix (Fittr-style, transparent)

RISKS = {
    "Atherosclerotic heart disease": {"apob": 2, "ldl": 1, "lpa": 2, "hscrp": 1, "cac": 3, "cad_rads": 3, "cimt": 1, "apoe": 1, "cad9p21": 1, "homocysteine": 1},
    "Type 2 diabetes": {"hba1c": 3, "glucose": 2, "homa_ir": 2, "insulin": 1, "tg": 1, "vat_area": 2, "tcf7l2": 1, "prs_t2d": 1, "liver_pdff": 1},
    "Fatty liver (MASLD)": {"liver_pdff": 3, "liver_hu": 3, "alt": 2, "ggt": 2, "tg": 1, "homa_ir": 1, "vat_area": 1},
    "Chronic kidney disease": {"egfr": 3, "cystatin_c": 2, "uacr": 3, "creatinine": 1, "uric_acid": 1},
    "Hypertension & heart strain": {"nt_probnp": 2, "vat_area": 1, "uric_acid": 1, "ahi": 1},
    "Neurodegeneration": {"ptau217": 3, "nfl": 2, "wmh_fazekas": 2, "apoe": 2, "homocysteine": 1, "b12": 1},
    "Osteoporosis & fracture": {"bmd_spine_t": 3, "bmd_hip_t": 3, "vitd": 1, "testosterone": 1},
    "Sarcopenia & frailty": {"almi": 3, "grip": 3, "gait_speed": 2, "sts_30s": 1, "vo2max_lab": 1},
    "Chronic inflammation": {"hscrp": 2, "il6": 2, "glyca": 1, "calprotectin": 1, "zonulin": 1, "inflam_clock": 1},
    "Thyroid dysfunction": {"tsh": 3, "ft3": 1},
    "Sleep apnoea": {"ahi": 3, "odi": 2, "min_spo2": 2, "vat_area": 1},
    "Cancer (screened)": {"mced": 3, "fit": 2},
}


def risk_matrix() -> list[dict]:
    L = engine.latest_values()
    out = []
    for name, weights in RISKS.items():
        drivers, total_w, bad_w = [], 0, 0.0
        for m, w in weights.items():
            r = L.get(m)
            if not r:
                continue
            total_w += w
            st = r["status"]
            z = zone_for(m, r["value_num"])
            if z:
                st = z["status"]
            badness = {"out_of_range": 1.0, "variant": 0.6, "detected": 1.0, "in_range": 0.15}.get(st, 0.0)
            bad_w += w * badness
            if badness:
                drivers.append({"id": m, "name": MARKERS[m][0], "status": st, "weight": w,
                                "value": r["value_num"] if r["value_num"] is not None else r["value_text"]})
        possible = sum(weights.values())
        if not total_w:
            out.append({"condition": name, "level": "unknown", "coverage": 0, "drivers": [],
                        "missing": [MARKERS[m][0] for m in weights]})
            continue
        score = bad_w / total_w
        level = "high" if score >= 0.5 else "moderate" if score >= 0.2 else "low"
        out.append({"condition": name, "level": level, "score": round(score, 2), "coverage": round(total_w / possible, 2),
                    "drivers": sorted(drivers, key=lambda d: -d["weight"]),
                    "missing": [MARKERS[m][0] for m in weights if m not in L and m in MARKERS],
                    "method": "Weighted share of available risk markers outside range; coverage = evidence present / possible."})
    order = {"high": 0, "moderate": 1, "low": 2, "unknown": 3}
    return sorted(out, key=lambda x: (order[x["level"]], -x.get("score", 0)))


def evidence_grade(mid: str) -> str | None:
    return EVIDENCE.get(mid)
