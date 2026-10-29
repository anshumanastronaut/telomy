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

    # ---- extended ratios (2026-10-29): each is emitted only when every input is present and non-zero
    chol = _n(L, "chol_total")
    ldl = _n(L, "ldl")
    nonhdl = _n(L, "nonhdl")
    nonhdl_src = ["nonhdl"] if nonhdl else ["chol_total", "hdl"]
    if not nonhdl and chol and hdl:
        nonhdl = chol - hdl
    if chol and hdl:
        add("castelli_i", "Castelli risk index I (TC / HDL)", chol / hdl, "", "total cholesterol ÷ HDL", ["chol_total", "hdl"],
            interp="Under 3.5 is favourable; above 5 signals higher cardiovascular risk.")
        add("atherogenic_coeff", "Atherogenic coefficient", (chol - hdl) / hdl, "", "(total cholesterol − HDL) ÷ HDL", ["chol_total", "hdl"],
            interp="Under 3 is favourable; above 4 signals higher atherogenic burden.")
    if ldl and hdl:
        add("castelli_ii", "Castelli risk index II (LDL / HDL)", ldl / hdl, "", "LDL ÷ HDL", ["ldl", "hdl"],
            interp="Under 2.5 is favourable; above 3.5 signals higher cardiovascular risk.")
    if nonhdl and apob:
        add("nonhdl_apob", "Non-HDL cholesterol / ApoB", nonhdl / apob, "", "non-HDL ÷ ApoB (mg/dL)", nonhdl_src + ["apob"],
            interp="Cholesterol carried per atherogenic particle. A low ratio means many cholesterol-poor (small, dense) particles, "
                   "so LDL-C understates risk; read alongside ApoB rather than alone.")
    tt, shbg_v, e2 = _n(L, "testosterone"), _n(L, "shbg"), _n(L, "estradiol")
    if tt and shbg_v:
        add("fai", "Free androgen index", (tt * 0.0347) / shbg_v * 100, "", "total testosterone (nmol/L) ÷ SHBG (nmol/L) × 100",
            ["testosterone", "shbg"],
            interp="Estimates bioavailable androgen. Used mainly in women (raised in PCOS, roughly > 5); less reliable when SHBG is very high or in men.")
    if tt and e2:
        add("t_e2", "Testosterone / estradiol ratio", tt / e2, "", "total testosterone (ng/dL) ÷ estradiol (pg/mL)", ["testosterone", "estradiol"],
            interp="A balance marker; both low-ratio and high-ratio readings need clinical context and the same-time-of-day draw.")
    ca, alb = _n(L, "calcium"), _n(L, "albumin")
    if ca and alb:
        add("ca_corrected", "Albumin-corrected calcium", ca + 0.8 * (4.0 - alb), "mg/dL", "calcium + 0.8 × (4.0 − albumin g/dL)", ["calcium", "albumin"],
            interp="Corrects total calcium for low or high albumin; about 8.6–10.3 mg/dL is the usual adult range.")
    t4, t3u = _n(L, "t4_total"), _n(L, "t3_uptake")
    if t4 and t3u and "fti" not in L:
        add("fti_calc", "Free thyroxine index (calculated)", t4 * t3u / 100, "", "total T4 (µg/dL) × T3 uptake (%) ÷ 100", ["t4_total", "t3_uptake"],
            interp="Roughly 1.2–4.9 is typical; corrects total T4 for binding-protein changes (pregnancy, oestrogen).")
    ua = _n(L, "uric_acid")
    if ua and hdl:
        add("uhr", "Uric acid / HDL ratio (UHR)", ua / hdl * 100, "%", "uric acid (mg/dL) ÷ HDL (mg/dL) × 100", ["uric_acid", "hdl"],
            interp="Lower is better; higher values track metabolic syndrome and insulin resistance.")
    weight = ((engine.series("weight") or [(None, None)])[-1][1]) or p.get("weight_kg") or p.get("weight")
    if tg and glu and hdl and h and weight and hdl > 1:
        bmi = weight / (h * h)
        add("mets_ir", "METS-IR (metabolic score for insulin resistance)", math.log(2 * glu + tg) * bmi / math.log(hdl), "",
            "ln(2 × glucose + TG) × BMI ÷ ln(HDL)", ["glucose", "tg", "hdl"],
            interp=f"Uses BMI {bmi:.1f}. Lower is better; values above about 40–50 suggest insulin resistance.")
    # blood-count indices from absolute counts in 10³/µL (counts reported in cells/mm³ are divided by 1000)
    plt_k = _n(L, "platelets")
    wbc_k = wbc if wbc else ((_n(L, "wbc_total") or 0) / 1000 or None)
    wbc_src = "wbc" if wbc else "wbc_total"

    def _abs(abs_id, pct_id):
        a = _n(L, abs_id)
        if a:
            return a / 1000, [abs_id]
        pct = _n(L, pct_id)
        return (wbc_k * pct / 100, [wbc_src, pct_id]) if wbc_k and pct else (None, [])

    lym_a, lym_in = _abs("alc", "lymph_pct")
    neu_a, neu_in = _abs("anc", "neutrophil_pct")
    mon_a, mon_in = _abs("amc", "monocyte_pct")
    if plt_k and lym_a:
        add("plr", "Platelet / lymphocyte ratio (PLR)", plt_k / lym_a, "", "platelets ÷ absolute lymphocytes", ["platelets"] + lym_in,
            interp="Roughly 100–150 is typical; persistently higher values accompany systemic inflammation.")
    if lym_a and mon_a:
        add("lmr", "Lymphocyte / monocyte ratio (LMR)", lym_a / mon_a, "", "absolute lymphocytes ÷ absolute monocytes", lym_in + mon_in,
            interp="Higher is better; a low ratio (< about 3–4) reflects inflammation or immune stress.")
    if plt_k and neu_a and lym_a:
        add("sii", "Systemic immune-inflammation index (SII)", plt_k * neu_a / lym_a, "", "platelets × neutrophils ÷ lymphocytes",
            ["platelets"] + neu_in + lym_in, interp="Lower is better; values above about 600–800 (×10³/µL basis) point to higher inflammatory load.")
    if neu_a and mon_a and lym_a:
        add("siri", "Systemic inflammation response index (SIRI)", neu_a * mon_a / lym_a, "", "neutrophils × monocytes ÷ lymphocytes",
            neu_in + mon_in + lym_in, interp="Lower is better; roughly < 1.0 is typical, and higher values track inflammatory and cardiometabolic risk.")
    bil = _n(L, "bilirubin_total")
    if bil and alb:
        add("bili_alb", "Bilirubin / albumin ratio", bil / alb, "", "total bilirubin (mg/dL) ÷ albumin (g/dL)", ["bilirubin_total", "albumin"],
            interp="Research-grade liver and haemolysis indicator; interpret with bilirubin and albumin themselves.")
    fer = _n(L, "ferritin")
    if fer and alb:
        add("ferritin_alb", "Ferritin / albumin ratio", fer / alb, "", "ferritin (ng/mL) ÷ albumin (g/dL)", ["ferritin", "albumin"],
            interp="Research-grade inflammation-adjusted iron-stores marker; higher values accompany inflammation and metabolic disease.")
    ggt = _n(L, "ggt")
    if ggt and hdl:
        add("ggt_hdl", "GGT / HDL ratio", ggt / hdl, "", "GGT (U/L) ÷ HDL (mg/dL)", ["ggt", "hdl"],
            interp="Research-grade liver-cardiometabolic marker; lower is better.")
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
