"""Large permutation study of Telomy's blood-age engine (PhenoAge, Levine 2018).

Goal: find, for THIS person's real anchors, the cheapest levers to lower biological age — which marker, moved how far
within a clinically plausible and achievable range, buys the most years, and what a realistic combined protocol gives.
All on our own engine; no third-party service. Writes a JSON + a readable summary.
"""
import json
import os
import sys

os.environ.setdefault("TELOMY_DB", sys.argv[1] if len(sys.argv) > 1 else "/tmp/study.db")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import numpy as np  # noqa: E402

sys.path.insert(0, "/Users/anshuman/telomy-app/backend")
from app import engine  # noqa: E402

AGE = 28.5
# Real anchors where we have them; population-typical where the real report lacks the marker (flagged ASSUMED).
REAL = {"albumin": 4.6, "creatinine": 1.0, "lymph_pct": 56.6, "mcv": 82.0, "rdw": 13.9, "alp": 37.0, "wbc": 4.29}
ASSUMED = {"glucose": 92.0, "hscrp": 1.5}
BASE = {**REAL, **ASSUMED}
# Clinically plausible adult range, and the realistically-achievable healthy target (direction that lowers PhenoAge).
RANGE = {"albumin": (3.8, 5.0, 4.8), "creatinine": (0.6, 1.3, 0.9), "glucose": (70, 130, 83), "hscrp": (0.2, 8.0, 0.4),
         "lymph_pct": (18, 48, 40), "mcv": (80, 100, 90), "rdw": (11.5, 15.5, 12.4), "alp": (30, 130, 65), "wbc": (3.5, 11.0, 5.0)}
UNIT = {"albumin": "g/dL", "creatinine": "mg/dL", "glucose": "mg/dL", "hscrp": "mg/L", "lymph_pct": "%", "mcv": "fL",
        "rdw": "%", "alp": "U/L", "wbc": "10³/µL"}
# How a person actually moves each marker (plain words); markers that are not lifestyle-movable are marked fixed.
LEVER = {"glucose": "diet, weight loss, exercise, sleep", "hscrp": "lose visceral fat, treat infection/inflammation, omega-3, exercise",
         "albumin": "adequate protein, treat inflammation", "alp": "correct zinc/magnesium, liver/bone health",
         "rdw": "correct iron/B12/folate deficiency", "mcv": "correct B12/folate or iron", "wbc": "resolve infection/inflammation, stop smoking",
         "lymph_pct": "(follows WBC differential — not a direct lifestyle lever)", "creatinine": "hydration; rises with muscle mass (not a de-aging target)"}
FIXED = {"creatinine", "lymph_pct"}


def pa(v):
    return engine.phenoage(v, AGE)["value"]


def main():
    out = {"age": AGE, "base_inputs": BASE, "assumed": list(ASSUMED), "base_phenoage": pa(BASE)}
    base = out["base_phenoage"]
    lines = [f"Baseline PhenoAge {base} at chronological age {AGE} (Δ {base - AGE:+.1f} y)",
             f"  assumed where the real report lacks them: {ASSUMED}", ""]

    # 1) one-at-a-time sweep across the full plausible range
    lines.append("1) Each marker swept across its full plausible range (others at your values):")
    sweep = {}
    for k, (lo, hi, _) in RANGE.items():
        a, z = pa({**BASE, k: lo}), pa({**BASE, k: hi})
        sweep[k] = {"low": lo, "high": hi, "pa_low": a, "pa_high": z, "span_y": round(abs(z - a), 1)}
        lines.append(f"   {k:11s} {lo:>5}→{hi:<5} {UNIT[k]:7s}  PhenoAge {a:5.1f}→{z:5.1f}   span {abs(z - a):4.1f} y")
    out["sweep"] = sweep

    # 2) Monte-Carlo variance decomposition: how much of the spread each marker owns
    rnd = np.random.default_rng(11)
    N = 50000
    keys = list(RANGE)
    X = np.zeros((N, len(keys)))
    for j, k in enumerate(keys):
        lo, hi, _ = RANGE[k]
        X[:, j] = np.exp(rnd.uniform(np.log(max(lo, .2)), np.log(hi), N)) if k == "hscrp" else rnd.uniform(lo, hi, N)
    y = np.array([pa({k: X[i, j] for j, k in enumerate(keys)}) for i in range(N)]) - AGE
    Z = (X - X.mean(0)) / X.std(0)
    beta, *_ = np.linalg.lstsq(np.c_[np.ones(N), Z], y, rcond=None)
    share = beta[1:] ** 2 / (beta[1:] ** 2).sum()
    r2 = 1 - ((y - np.c_[np.ones(N), Z] @ beta) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    imp = sorted(zip(keys, share, beta[1:]), key=lambda t: -t[1])
    out["variance_share"] = [{"marker": k, "share_pct": round(s * 100, 1), "dir": "raises" if b > 0 else "lowers"} for k, s, b in imp]
    lines += ["", f"2) {N} random combinations — share of the blood-age spread each marker owns (R² {r2:.2f}):"]
    lines += [f"   {k:11s} {s*100:5.1f} %   {'raises' if b>0 else 'lowers'} age as it rises" for k, s, b in imp]

    # 3) achievable single-lever gains (move ONE marker from your value to its healthy target)
    lines += ["", "3) Achievable gain from moving ONE marker to a healthy target (others held at your values):"]
    gains = []
    for k, (lo, hi, tgt) in RANGE.items():
        if k in FIXED:
            continue
        g = base - pa({**BASE, k: tgt})
        gains.append({"marker": k, "from": BASE[k], "to": tgt, "unit": UNIT[k], "years_saved": round(g, 1), "how": LEVER.get(k, "")})
    for gg in sorted(gains, key=lambda x: -x["years_saved"]):
        tag = " [ASSUMED baseline]" if gg["marker"] in ASSUMED else ""
        lines.append(f"   {gg['marker']:11s} {gg['from']:>5}→{gg['to']:<5} {gg['unit']:7s}  saves {gg['years_saved']:+4.1f} y   via {gg['how']}{tag}")
    out["single_lever_gains"] = gains

    # 4) realistic combined protocol: move all lifestyle-movable markers to target together
    combo = {**BASE, **{k: RANGE[k][2] for k in RANGE if k not in FIXED}}
    out["combined_protocol"] = {"inputs": combo, "phenoage": pa(combo), "years_saved": round(base - pa(combo), 1)}
    lines += ["", f"4) Realistic combined protocol (all movable markers at target): PhenoAge {pa(combo)} "
              f"(from {base}) — saves {base - pa(combo):.1f} y"]

    # 5) biggest caveat for THIS person
    lines += ["", "Caveat for your real data: your low PhenoAge is driven partly by lymphocytes 56.6 % and low ALP/WBC,",
              "which track with the LOW NEUTROPHIL count your doctor should review — not proof of slow ageing. Confirm the",
              "blood count is stable before reading the blood age as good news. Fasting glucose and hs-CRP were assumed;",
              "add them to the next test for a real number."]
    report = "\n".join(lines)
    json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else "/tmp/study.json", "w"), indent=2, default=str)
    print(report)
    open((sys.argv[2] if len(sys.argv) > 2 else "/tmp/study.json").replace(".json", ".txt"), "w").write(report)


if __name__ == "__main__":
    main()
