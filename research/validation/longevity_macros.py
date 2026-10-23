#!/usr/bin/env python
"""Sim-testing harness #3 — longevity Rx (geroprotectors) + macros engines.

Checks the behaviours clinical reasoning requires:
  Longevity: foundation tier always present; a condition adds clinical interventions; the claims firewall holds
             (no "cures/treats/reverses ageing/guarantees" language anywhere in the output).
  Macros:    protein target tracks 1.2–1.6 g/kg bodyweight; renal impairment caps protein and gates to a doctor;
             higher weight → higher absolute protein.

Pure functions on dicts — no DB, nothing written anywhere. Run:
  backend/.venv/bin/python research/validation/longevity_macros.py
"""
import os, sys, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
from app.llx import geroprotectors as G, macros as M  # noqa: E402

# Overclaim patterns the evidence firewall must never produce. (Bare "treat" is allowed — e.g. "treat the apnoea"
# is legitimate clinical advice; the firewall is about claiming an intervention cures/treats a disease or ageing,
# guarantees an outcome, or extends lifespan.)
BANNED = re.compile(
    r"\b(cures?\b|reverses? ag(e)?ing|treats? (ag(e)?ing|cancer|diabetes|disease)|extends? (your )?(life|lifespan)|"
    r"guarantee[sd]?|miracle|detoxes?\b)", re.I)


def _all_text(obj):
    if isinstance(obj, dict):
        return " ".join(_all_text(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_all_text(v) for v in obj)
    return str(obj) if isinstance(obj, str) else ""


def run():
    ok = tot = 0
    def check(name, cond, detail=""):
        nonlocal ok, tot
        tot += 1; ok += bool(cond)
        print(f"[{'PASS' if cond else 'FAIL'}] {name}{('  — ' + detail) if detail else ''}")

    healthy = {"age": 40, "sex": "male", "goals": ["longevity"], "conditions": [], "weight_kg": 75}
    diabetic = {"age": 55, "sex": "male", "goals": ["longevity"], "conditions": ["type 2 diabetes"], "weight_kg": 92}

    print("── LONGEVITY Rx ──")
    rh, rd = G.recommend(healthy, {}), G.recommend(diabetic, {"hba1c": 8.5, "glucose": 165})
    th, td = rh.get("tiers", {}), rd.get("tiers", {})
    check("foundation tier present (healthy)", len(th.get("foundation", [])) >= 3)
    check("condition adds clinical interventions", len(td.get("clinical", [])) > len(th.get("clinical", [])),
          f"healthy {len(th.get('clinical', []))} → diabetic {len(td.get('clinical', []))}")
    hit_h = BANNED.search(_all_text(rh)); hit_d = BANNED.search(_all_text(rd))
    check("claims firewall holds (no cure/treat/reverse-ageing)", not hit_h and not hit_d,
          (hit_h or hit_d).group(0) if (hit_h or hit_d) else "clean")

    print("\n── MACROS ──")
    for prof in (healthy, diabetic):
        mp = M.prescribe(prof, {})
        lo, hi = mp["protein"]["target_g_per_day"]
        w = prof["weight_kg"]
        check(f"protein ≈1.2–1.6 g/kg at {w}kg", abs(lo - 1.2 * w) <= w * 0.2 and abs(hi - 1.6 * w) <= w * 0.2,
              f"{lo}–{hi} g/day (want ~{round(1.2*w)}–{round(1.6*w)})")
    # heavier person → more absolute protein
    m75, m92 = M.prescribe(healthy, {}), M.prescribe(diabetic, {})
    check("heavier patient → higher protein", m92["protein"]["target_g_per_day"][0] > m75["protein"]["target_g_per_day"][0])
    # renal impairment caps protein + gates to a doctor
    renal = {"age": 60, "sex": "male", "conditions": ["chronic kidney disease"], "weight_kg": 80}
    mr = M.prescribe(renal, {"creatinine": 2.4, "egfr": 35})
    gated = mr["protein"].get("doctor_gate") or mr["protein"].get("target_g_per_kg", [9])[1] <= 1.0
    check("renal impairment caps protein / gates to doctor", gated,
          f"gate={mr['protein'].get('doctor_gate')} g/kg={mr['protein'].get('target_g_per_kg')}")

    print(f"\nSUMMARY: {ok}/{tot} checks pass")


if __name__ == "__main__":
    run()
