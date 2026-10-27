#!/usr/bin/env python
"""Sim-testing harness #2 — the Vault risk map (app/derived.py risk_matrix) and longevity age.

Injects synthetic lab panels into an ISOLATED scratchpad DB (never telomy.db / Oracle), then checks the
risk map flags the condition each panel is built to represent. Rule-based engine, so we assert exact levels.

Run: backend/.venv/bin/python research/validation/risk_map.py
"""
import os, sys, tempfile, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
os.environ.setdefault("TELOMY_TZ", "Asia/Kolkata")

from app import db, seed, derived, engine  # noqa: E402
from app.catalog import MARKERS  # noqa: E402

TODAY = dt.date.today().isoformat()

# catalog marker-id : optimal (healthy) value
HEALTHY = {
    "glucose": 85, "hba1c": 5.0, "insulin": 4, "homa_ir": 0.9,
    "chol_total": 170, "ldl": 90, "hdl": 60, "tg": 80, "apob": 70, "lpa": 10,
    "hscrp": 0.5, "homocysteine": 8, "vitd": 50, "b12": 600, "tsh": 1.8,
    "alt": 22, "ast": 22, "ggt": 22, "creatinine": 0.9, "egfr": 100, "uric_acid": 5.0,
    "sbp": 115, "dbp": 75, "hemoglobin": 15, "ferritin": 100,
}

ARCHETYPES = {
    "healthy":      ({}, {}),  # expect no 'high' risks
    "diabetic":     (dict(glucose=175, hba1c=8.8, insulin=28, homa_ir=6.5, tg=240, hdl=33),
                     {"Type 2 diabetes": "high"}),
    "fatty_liver":  (dict(alt=90, ast=72, ggt=150, tg=230, glucose=110, hba1c=5.9),
                     {"Fatty liver (MASLD)": "high"}),
    "ascvd":        (dict(apob=145, ldl=195, chol_total=290, hdl=30, lpa=120, hscrp=4.0),
                     {"Atherosclerotic heart disease": "high"}),
    "ckd":          (dict(creatinine=2.3, egfr=35, uric_acid=8.5),
                     {"Chronic kidney disease": "high"}),
}


def inject(panel):
    db.init(reset=True)
    db.exec_("INSERT OR REPLACE INTO profile (id, data) VALUES (1, ?)",
             (db.j({"name": "Sim", "first_name": "Sim", "dob": "1980-01-01", "sex": "male", "height_cm": 175,
                    "weight_kg": 78, "onboarded": True}),))
    def status_of(m, v):
        if m not in MARKERS:
            return "unknown"
        lo, hi = MARKERS[m][3], MARKERS[m][4]
        return "out_of_range" if (isinstance(v, (int, float)) and (v < lo or v > hi)) else "in_range"
    markers = [{"marker_id": m, "value": v, "unit": MARKERS[m][2] if m in MARKERS else "",
                "ref_low": MARKERS[m][3] if m in MARKERS else None,
                "ref_high": MARKERS[m][4] if m in MARKERS else None, "status": status_of(m, v)}
               for m, v in panel.items()]
    seed.save_report({"title": "Sim panel", "panel": "blood", "collected_on": TODAY,
                      "is_test_data": True, "markers": markers}, "sim", "sim.json")


def run():
    tmp = os.path.join(tempfile.gettempdir(), "telomy_sim_validation.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    db.set_db(tmp)
    print(f"RISK-MAP VALIDATION (isolated DB {tmp})\n")
    npass = ntot = 0
    for name, (overrides, expect) in ARCHETYPES.items():
        panel = dict(HEALTHY); panel.update(overrides)
        inject(panel)
        rm = {r["condition"]: r for r in derived.risk_matrix()}
        if not expect:  # healthy: no condition should be 'high'
            highs = [c for c, r in rm.items() if r["level"] == "high"]
            ok = not highs
            ntot += 1; npass += ok
            print(f"[{'PASS' if ok else 'FAIL'}] {name:12} highs={highs or 'none'}")
        else:
            for cond, want in expect.items():
                got = rm.get(cond, {}).get("level", "MISSING")
                ok = got == want
                ntot += 1; npass += ok
                drivers = ", ".join(d["name"] for d in rm.get(cond, {}).get("drivers", [])[:3])
                print(f"[{'PASS' if ok else 'FAIL'}] {name:12} {cond:32} want={want} got={got}  ({drivers})")
    print(f"\nSUMMARY: {npass}/{ntot} checks pass")
    os.remove(tmp)


if __name__ == "__main__":
    run()
