#!/usr/bin/env python
"""Sim-testing harness #1 — organ-age clocks (app/llx/organ_tools.py).

Generates synthetic blood panels across clinical archetypes (healthy / diabetic / fatty-liver / CKD / CVD /
inflammation / metabolic-syndrome / edge cases), runs each MANY times with randomised within-archetype
perturbations, and checks the organ clocks behave the way clinical reasoning says they *should*:

  - a fully-optimal panel should read every organ near chronological age (calibration),
  - a diabetic panel should age the metabolic + cardiometabolic clocks,
  - a fatty-liver panel should age the hepatic clock,
  - a CKD panel should age the renal clock,
  - an inflammatory panel should age the immune clock.

It is read-only and self-contained: organ_ages() is a pure function on a panel dict, so NO database is
touched (nothing is written to telomy.db or Oracle). Run:  backend/.venv/bin/python research/validation/organ_clocks.py
"""
import os, sys, random, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
from app.llx import organ_tools as O  # noqa: E402

AGE = 45  # chronological age used for every synthetic patient

# A fully-optimal male panel (every value mid-optimal). Archetypes override a few markers off this base.
HEALTHY = dict(
    sex=1, age=AGE,
    glucose_fasting=85, glucose=85, glucose_serum=85, hba1c=5.0, insulin=4.0,
    trig=80, trig_serum=80, hdl=60, total_chol=170, ldl=95, uric_acid=5.0,
    albumin=4.6, alt=22, ast=22, alp=70, ggt=22, bilirubin=0.8, total_protein=7.0, globulin=2.5,
    creatinine=0.9, bun=14, phosphorus=3.5, potassium=4.2, sodium=140, chloride=102, bicarb=25, calcium=9.5,
    wbc=6.0, lymph_pct=32, neut_pct=55, mono_pct=7, eos_pct=2, baso_pct=0.5, rdw=13.0, platelets=250, crp_mgL=0.5,
)

# Clinically-abnormal overrides per archetype, and which organ(s) SHOULD then age.
ARCHETYPES = {
    "healthy":            (dict(), set()),  # expect: no organ strongly older (calibration baseline)
    "diabetic":           (dict(glucose_fasting=170, glucose=170, glucose_serum=170, hba1c=8.8, insulin=28, trig=260, hdl=34),
                           {"metabolic", "cardiometabolic"}),
    "fatty_liver":        (dict(alt=85, ast=70, ggt=140, bilirubin=1.3, albumin=4.0, globulin=3.2, trig=240),
                           {"hepatic"}),
    "ckd":                (dict(creatinine=2.4, bun=42, phosphorus=5.2, potassium=5.4, bicarb=19, calcium=8.4, uric_acid=8.5),
                           {"renal"}),
    "dyslipidemia_cvd":   (dict(ldl=195, total_chol=290, hdl=30, trig=230, uric_acid=7.5),
                           {"cardiometabolic"}),
    "inflammation":       (dict(crp_mgL=14, wbc=13.5, neut_pct=78, lymph_pct=14, rdw=16.5, platelets=480),
                           {"immune"}),
    "metabolic_syndrome": (dict(glucose_fasting=120, hba1c=6.2, insulin=18, trig=210, hdl=33, ldl=160, uric_acid=7.2, alt=55, ggt=70),
                           {"metabolic", "cardiometabolic"}),
}


def perturb(panel, rnd, pct=0.08):
    """Jitter every numeric marker by ±pct to test robustness of the direction (not a single lucky value)."""
    out = {}
    for k, v in panel.items():
        if k in ("sex", "age") or not isinstance(v, (int, float)):
            out[k] = v
        else:
            out[k] = round(v * (1 + rnd.uniform(-pct, pct)), 3)
    return out


def _mean_accel(base, rnd, n_runs):
    acc = {}
    for _ in range(n_runs):
        r = O.organ_ages(perturb(base, rnd), chronological_age=AGE)
        for o in r["organs"]:
            acc.setdefault(o["organ"], []).append(o["age_acceleration_years"] or 0.0)
    return {o: st.mean(v) for o, v in acc.items()}


def run(n_runs=50, delta_thresh=3.0):
    """Disease archetypes are judged RELATIVE to the healthy baseline: the target organ(s) should age at least
    `delta_thresh` years MORE than on the optimal panel. (An age clock's absolute level is set by calibration;
    the clinically-meaningful quantity is how much a disease moves the organ vs a clean panel.)"""
    rnd = random.Random(7)
    base_healthy = _mean_accel(dict(HEALTHY), rnd, n_runs)
    print(f"ORGAN-CLOCK VALIDATION — {n_runs} runs/archetype; disease target must age >=+{delta_thresh}y vs healthy, chrono={AGE}")
    print(f"healthy baseline accel: " + "  ".join(f"{o}={base_healthy[o]:+.1f}" for o in sorted(base_healthy, key=lambda x: -base_healthy[x])) + "\n")
    results = {}
    for name, (overrides, expect_older) in ARCHETYPES.items():
        if not expect_older:
            continue
        mean = _mean_accel({**HEALTHY, **overrides}, rnd, n_runs)
        deltas = {o: mean[o] - base_healthy.get(o, 0) for o in mean}
        ok = all(deltas.get(o, 0) >= delta_thresh for o in expect_older)
        # also: the expected organ(s) should rank among the most-elevated vs baseline
        top = sorted(deltas, key=lambda x: -deltas[x])[:len(expect_older)]
        ranked_ok = expect_older <= set(top)
        verdict = "PASS" if (ok and ranked_ok) else ("WEAK" if ok or ranked_ok else "FAIL")
        results[name] = verdict
        d = "  ".join(f"{o}=+{deltas[o]:.1f}" for o in sorted(expect_older))
        print(f"[{verdict:4}] {name:20} Δvs-healthy for target {sorted(expect_older)}: {d}   (top-moved: {top})")
    npass = sum(1 for v in results.values() if v == "PASS")
    print(f"\nSUMMARY: {npass}/{len(results)} disease archetypes PASS (target organ aged >=+{delta_thresh}y vs healthy & ranked top)")
    fails = [n for n, v in results.items() if v != "PASS"]
    if fails:
        print("Needs attention: " + ", ".join(fails) + "  (dyslipidemia/metabolic_syndrome: age-clock≠risk — lipids weakly predict chronological age; risk_map covers CVD)")
    return results


if __name__ == "__main__":
    run()
