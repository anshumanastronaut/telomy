"""Run the complete Telomy backend on every synthetic person (one process each, isolated DB) and score it.

Checks per person: every parameterless GET endpoint → status, latency, impossible values (NaN/inf, negative
durations, probabilities outside 0–1); planted-effect recovery from /insights (sensitivity) and invented effects for
habits planted with NO effect (false discovery); outputs saved for cohort-level checks (risk ranking vs conditions,
longevity vs fitness). Writes <out>/eval/pXXX.json and <out>/REPORT.md.
"""
import json
import math
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect", "/static/telomy_anatomy.glb", "/whoop/push", "/physio/validation"}
KEYS = {"alcohol": ["alcohol", "drink", "wine", "beer"], "late_meal": ["late meal", "late dinner", "dinner after", "eating late", "late_meal"],
        "caffeine_late": ["caffeine", "coffee"], "sauna": ["sauna"], "cold_plunge": ["cold plunge", "cold water", "cold_plunge", "cold"],
        "workout_hard": ["hard workout", "hard training", "workout_hard", "intense", "training"]}


def total_effects(person: dict) -> dict:
    """Total next-day effect of each habit on each outcome through the generator's structural equations
    (sim/cohort.build_one): sleep → deep (+0.08/h), sleep → HRV (+4 ms/h), HRV → RHR (−0.1 bpm/ms),
    sleep → score (+9/h), deep → score (+14/h). A direct effect of 0 can still have a real indirect effect."""
    out = {}
    for habit, e in person["effects"].items():
        ds = e.get("sleep_hours", 0.0)
        dd = e.get("deep_sleep", 0.0) + 0.08 * ds
        dh = e.get("hrv", 0.0) + 4 * ds
        out[habit] = {"sleep_hours": ds, "deep_sleep": dd, "hrv": dh, "rhr": e.get("rhr", 0.0) - 0.1 * dh,
                      "sleep_score": e.get("sleep_score", 0.0) + 9 * ds + 14 * dd}
    return {h: {m: (v if abs(v) > 1e-9 else 0.0) for m, v in d.items()} for h, d in out.items()}


def _bad_numbers(o, path="", out=None):
    out = [] if out is None else out
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        out.append(path)
    elif isinstance(o, dict):
        for k, v in o.items():
            kl = str(k).lower()
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if any(x in kl for x in ("prob", "risk_pct", "percentile")) and "pct" not in kl and not (0 <= v <= 1 or 0 <= v <= 100):
                    out.append(f"{path}.{k}={v}")
                if any(x in kl for x in ("minutes", "duration", "_min", "hours")) and v < 0:
                    out.append(f"{path}.{k}={v}")
            _bad_numbers(v, f"{path}.{k}", out)
    elif isinstance(o, list):
        for i, v in enumerate(o[:200]):
            _bad_numbers(v, f"{path}[{i}]", out)
    return out


def one(out: str, pid: int):
    db_path = f"{out}/p{pid:03d}.db"
    os.environ["TELOMY_DB"] = db_path
    os.environ.pop("TELOMY_ACCESS_PASSWORD", None)
    sys.path.insert(0, ROOT)
    from fastapi.testclient import TestClient
    from app.main import app
    paths = sorted(r.path for r in app.routes if "GET" in getattr(r, "methods", set()) and "{" not in r.path and r.path not in SKIP)
    res = {"id": pid, "endpoints": {}, "errors": [], "slow": [], "bad_values": []}
    keep = {}
    with TestClient(app) as c:
        from app import engine
        engine.regenerate_insights()          # what a real ingest triggers
        table = engine.effect_table()
        for p in paths:
            t = time.time()
            try:
                r = c.get(p); dt = time.time() - t
                res["endpoints"][p] = {"status": r.status_code, "s": round(dt, 3)}
                if r.status_code >= 500: res["errors"].append(f"{p} → {r.status_code}")
                if dt > 2: res["slow"].append(f"{p} {dt:.1f}s")
                if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
                    j = r.json()
                    res["bad_values"] += [f"{p}{b}" for b in _bad_numbers(j)][:10]
                    if p in ("/insights", "/predict", "/risks", "/longevity", "/twin", "/today", "/signals"):
                        keep[p] = j
            except Exception as e:  # noqa: BLE001
                res["errors"].append(f"{p} raised {type(e).__name__}: {str(e)[:120]}")
    # planted-effect recovery
    person = next(x for x in json.load(open(f"{out}/people.json")) if x["id"] == pid)
    truth = json.load(open(db_path + ".truth.json"))["planted"]
    text = json.dumps(keep.get("/insights", [])).lower()
    rec = {}
    for habit, effs in person["effects"].items():
        n = len(truth.get(habit, []))
        real = any(v != 0 for v in effs.values())
        found = any(k in text for k in KEYS[habit])
        rec[habit] = {"occurrences": n, "planted": real, "found": found,
                      "verdict": ("TP" if found else "FN") if real and n >= 8 else ("FP" if found else "TN") if not real and n >= 8 else "n<8"}
    res["recovery"] = rec
    # exact effect-level scoring against the planted truth (event × metric)
    eff_rows = []
    total = total_effects(person)
    for row in table:
        planted = total.get(row["event"], {}).get(row["metric"], 0.0)   # TOTAL effect incl. knock-on (mediated) paths
        lo, hi = row["ci95"]
        eff_rows.append({"event": row["event"], "metric": row["metric"], "planted": planted, "est": row["effect"], "lo": lo, "hi": hi,
                         "covered": lo <= planted <= hi, "sig": bool(row["significant"]), "n": row["n"],
                         "sign_ok": (planted == 0) or (row["effect"] * planted > 0)})
    res["effects"] = eff_rows
    res["keep"] = {k: keep[k] for k in ("/predict", "/risks", "/longevity") if k in keep}
    os.makedirs(f"{out}/eval", exist_ok=True)
    json.dump(res, open(f"{out}/eval/p{pid:03d}.json", "w"), default=str)


def run(out: str):
    people = json.load(open(f"{out}/people.json"))
    t0 = time.time()
    for p in people:
        r = subprocess.run([sys.executable, "-c", f"from sim.evaluate import one; one({out!r}, {p['id']})"], cwd=ROOT,
                           capture_output=True, text=True, timeout=600)
        if r.returncode:
            os.makedirs(f"{out}/eval", exist_ok=True)
            json.dump({"id": p["id"], "crash": r.stderr[-2000:]}, open(f"{out}/eval/p{p['id']:03d}.json", "w"))
    report(out, people, time.time() - t0)


def report(out: str, people: list, secs: float):
    E = {p["id"]: json.load(open(f"{out}/eval/p{p['id']:03d}.json")) for p in people}
    crashes = [i for i, e in E.items() if "crash" in e]
    err = {}
    for e in E.values():
        for x in e.get("errors", []): err[x.split(" ")[0]] = err.get(x.split(" ")[0], 0) + 1
    slow = {}
    for e in E.values():
        for x in e.get("slow", []): slow[x.split(" ")[0]] = slow.get(x.split(" ")[0], 0) + 1
    bad = {}
    for e in E.values():
        for x in e.get("bad_values", []): bad[x.split(".")[0].split("[")[0]] = bad.get(x.split(".")[0].split("[")[0], 0) + 1
    rows = [r for e in E.values() for r in e.get("effects", [])]
    real = [r for r in rows if r["planted"] != 0]; null = [r for r in rows if r["planted"] == 0]
    power = sum(r["sig"] for r in real) / max(1, len(real)); fpr = sum(r["sig"] for r in null) / max(1, len(null))
    cover = sum(r["covered"] for r in rows) / max(1, len(rows)); signok = sum(r["sign_ok"] and r["sig"] for r in real) / max(1, sum(r["sig"] for r in real))
    big = [r for r in real if r["n"] >= 15]
    power_big = sum(r["sig"] for r in big) / max(1, len(big))
    conf = {"TP": 0, "FN": 0, "FP": 0, "TN": 0}
    by_habit = {}
    for e in E.values():
        for h, v in e.get("recovery", {}).items():
            if v["verdict"] in conf:
                conf[v["verdict"]] += 1; by_habit.setdefault(h, {"TP": 0, "FN": 0, "FP": 0, "TN": 0})[v["verdict"]] += 1
    sens = conf["TP"] / max(1, conf["TP"] + conf["FN"]); fdr = conf["FP"] / max(1, conf["FP"] + conf["TP"])
    L = [f"# Telomy synthetic cohort — engine report", "",
         f"{len(people)} synthetic people (not real; isolated DBs) · {secs / 60:.1f} min · generated by backend/sim", "",
         f"- Crashed runs: **{len(crashes)}** {crashes[:10]}",
         f"- Endpoints returning 5xx (endpoint: people affected): {json.dumps(dict(sorted(err.items(), key=lambda x: -x[1])[:15]))}",
         f"- Slow endpoints > 2 s (endpoint: people): {json.dumps(dict(sorted(slow.items(), key=lambda x: -x[1])[:15]))}",
         f"- Impossible values (endpoint: people): {json.dumps(dict(sorted(bad.items(), key=lambda x: -x[1])[:15]))}", "",
         "## Effect engine vs planted truth (engine.effect_table, event × outcome)", "",
         f"- {len(rows)} estimates: {len(real)} planted non-zero, {len(null)} true nulls",
         f"- 95 % CI covers the planted value: **{cover:.0%}** (target ≈ 95 %)",
         f"- Power (planted effect significant): **{power:.0%}** overall, **{power_big:.0%}** when the habit happened ≥ 15 times",
         f"- False-positive rate on true nulls: **{fpr:.1%}** (target ≤ 5 %)",
         f"- Sign correct among significant planted effects: **{signok:.0%}**", "",
         "## Planted cause→effect recovery (/insights text)", "",
         f"Sensitivity (planted effect found) **{sens:.0%}** · False-discovery rate (effect claimed where none planted) **{fdr:.0%}** · counts {conf}", "",
         "| habit | TP | FN | FP | TN |", "|---|---|---|---|---|"]
    L += [f"| {h} | {v['TP']} | {v['FN']} | {v['FP']} | {v['TN']} |" for h, v in sorted(by_habit.items())]
    open(f"{out}/REPORT.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))
