"""Daytime engine on the WHOOP 1 Hz stream (heart rate + gravity vector, pushed by NOOP): day strain, workouts,
calories and heart-rate stress — what WHOOP shows that NOOP leaves thin, computed with published methods.

Calibrated on the wearer's own data (2026-10-18): 10-s mean gravity change is ≤ 0.012 g asleep/at rest and ≈ 0.19 g
when moving, so motion ≥ 0.15 = moving.
- Day strain: Banister (1991) TRIMP on per-minute %HR reserve (HRmax = Tanaka 208 − 0.7·age, resting = day's 10th
  percentile; minutes below 20 % HRR ignored), strain = 4·ln(1 + TRIMP/6). Not yet calibrated against WHOOP's own
  Day Strain (needs WHOOP's official numbers for the same days).
- Workouts: HR ≥ resting + 15 bpm AND moving, ≥ 5 min, gaps < 150 s merged, ≥ 50 % of the bout at ≥ 60 % HRmax
  (Edwards zone 2+). Resting HR = 10th percentile of the day's HR.
- Calories: Keytel et al. 2005 (J Sports Sci) HR-based energy expenditure during workouts (needs age, sex, weight).
- Stress (HR-based): per still, awake minute, (HR − resting) / (HRmax − resting) → 0–3 scale like WHOOP's Stress
  Monitor, but from heart rate only: WHOOP 4.0 history R-R is re-delivered, so HRV can't be trusted here. Labelled so.
"""
import json
import math
from datetime import date, datetime, timedelta, timezone

from . import db, engine

IST = timezone(timedelta(hours=5, minutes=30))
MOVE = 0.15


def _rows(stream: str, a: int, b: int):
    return [(json.loads(r["key"])["ts"], json.loads(r["data"])) for r in
            db.rows("SELECT key, data FROM whoop_rows WHERE stream=? AND ts>=? AND ts<? ORDER BY ts", (stream, a, b))]


_CACHE: dict[tuple, tuple[float, dict]] = {}


def day(day_iso: str | None = None) -> dict:
    """Cached: a past day is final once computed; today is recomputed at most every 10 min (≈ 10 s on the 1-core
    server for a full day of 1 Hz rows)."""
    import time
    d = date.fromisoformat(day_iso) if day_iso else datetime.now(IST).date()
    key = (db.db_path(), d.isoformat())
    today = d == datetime.now(IST).date()
    hit = _CACHE.get(key)
    if hit and (not today or time.time() - hit[0] < 600) and hit[1].get("ok"):
        return hit[1]
    out = _compute(d)
    _CACHE[key] = (time.time(), out)
    if len(_CACHE) > 64:
        _CACHE.pop(next(iter(_CACHE)))
    return out


def _compute(d: date) -> dict:
    a = int(datetime(d.year, d.month, d.day, tzinfo=IST).timestamp()); b = a + 86400
    hr = {t: v["bpm"] for t, v in _rows("hrSample", a, b) if 30 <= (v.get("bpm") or 0) <= 220}
    if len(hr) < 600:
        return {"day": d.isoformat(), "ok": False, "reason": f"only {len(hr)} s of WHOOP heart rate this day"}
    grav = _rows("gravitySample", a, b)
    mv: dict[int, float] = {}
    prev, win = None, []
    for t, v in grav:
        x = (v["x"], v["y"], v["z"])
        dlt = math.dist(x, prev) if prev else 0.0
        prev = x; win.append(dlt); win = win[-10:]
        mv[t] = sum(win) / len(win)
    p = engine.profile()
    age = engine.age_on() or 35
    hrmax = 208 - 0.7 * age
    vals = sorted(hr.values()); rest = vals[len(vals) // 10]
    # per-minute
    mins: dict[int, list[int]] = {}
    for t, v in hr.items():
        mins.setdefault((t - a) // 60, []).append(v)
    mhr = {m: sum(v) / len(v) for m, v in mins.items() if len(v) >= 20}
    mmv = {}
    for t, v in mv.items():
        mmv.setdefault((t - a) // 60, []).append(v)
    mmv = {m: sum(v) / len(v) for m, v in mmv.items()}
    # Zones (display) on heart-rate RESERVE; load = Banister (1991) TRIMP, which counts every minute in proportion to
    # effort (x = %HRR, weight 0.64·e^(1.92x) men / 0.86·e^(1.67x) women), ignoring x < 0.2 (sitting/fidgeting).
    # Why: with all-day wear, Edwards' %HRmax zone 1 (≥ 50 % HRmax ≈ 93 bpm) counted 3.8 h of ordinary walking as
    # training (strain 15.8 on a day without exercise, 2026-10-18); Edwards on %HRR counted almost nothing (1.2).
    male = str(p.get("sex", "")).lower().startswith("m")
    bk, bb = (0.64, 1.92) if male else (0.86, 1.67)
    zones = [0] * 5
    trimp = 0.0
    for m, h in mhr.items():
        f = (h - rest) / max(1, hrmax - rest)
        if f >= 0.5:
            zones[min(4, int((f - 0.5) * 10))] += 1
        if f >= 0.2:
            trimp += f * bk * math.exp(bb * f)
    trimp = round(trimp, 1)
    strain = min(21.0, 4 * math.log(1 + trimp / 6))
    # workouts (per second)
    act = sorted(t for t, h in hr.items() if h >= rest + 15 and mv.get(t, 0) >= MOVE)
    bouts, s0, last = [], None, None
    for t in act:
        if s0 is None or t - last > 150:
            if s0 is not None: bouts.append((s0, last))
            s0 = t
        last = t
    if s0 is not None: bouts.append((s0, last))
    weight = p.get("weight_kg") or (engine.series("weight")[-1][1] if engine.series("weight") else None)
    workouts = []
    for s, e in bouts:
        if e - s < 300:
            continue
        hs = [hr[t] for t in range(s, e + 1) if t in hr]
        z2 = sum(1 for h in hs if h >= 0.6 * hrmax) / max(1, len(hs))
        if z2 < 0.5:
            continue
        avg = sum(hs) / len(hs)
        kcal = None
        if weight and age:
            per_min = ((-55.0969 + 0.6309 * avg + 0.1988 * weight + 0.2017 * age) if male else
                       (-20.4022 + 0.4472 * avg - 0.1263 * weight + 0.074 * age)) / 4.184
            kcal = round(max(0, per_min) * (e - s) / 60)
        workouts.append({"start": s, "end": e, "min": round((e - s) / 60), "avgHr": round(avg), "maxHr": max(hs),
                         "zone2plusPct": round(100 * z2), "kcal": kcal, "source": "WHOOP motion + heart rate"})
    # stress: still, awake minutes (exclude workouts and the night's sleep sessions)
    asleep = [(n["start"], n["end"]) for n in _sleep_sessions(a - 43200, b)]
    in_bout = lambda t: any(s <= t <= e for s, e in bouts)          # noqa: E731
    lvl = []
    for m, h in mhr.items():
        t = a + m * 60
        if mmv.get(m, 0) >= MOVE or in_bout(t) or any(s <= t < e for s, e in asleep):
            continue
        lvl.append(max(0.0, min(3.0, 3 * (h - rest) / max(1, (hrmax - rest) * 0.4))))
    stress = {"avg": round(sum(lvl) / len(lvl), 2) if lvl else None, "minutes": len(lvl),
              "highMin": sum(1 for x in lvl if x >= 2), "method": "heart rate vs your resting level, still minutes only (WHOOP 4.0 HRV not reliable)"}
    return {"day": d.isoformat(), "ok": True, "wornMin": len(mhr), "restingHr": round(rest), "hrMax": round(hrmax),
            "strain": round(strain, 1), "trimp": trimp, "zonesMin": zones, "workouts": workouts, "stress": stress,
            "method": "Banister TRIMP on %HR reserve → 4·ln(1+T/6), not yet calibrated to WHOOP; workouts HR ≥ rest+15 & motion ≥ 0.15 g ≥ 5 min; Keytel 2005 kcal"}


def _sleep_sessions(a: int, b: int):
    out = []
    for r in db.rows("SELECT key, data FROM whoop_rows WHERE stream='sleepSession' AND ts>=? AND ts<?", (a, b)):
        k, v = json.loads(r["key"]), json.loads(r["data"])
        out.append({"start": k["startTs"], "end": v.get("endTs") or k["startTs"]})
    return out



def store_signals(days: int = 3) -> int:
    """Finished WHOOP days → daily signals (strain, exercise minutes, active kcal when the phone has none) so the load
    models (dynamics.banister), the effect engine and trackers can use them. Today is skipped until it is over."""
    n = 0
    today = datetime.now(IST).date()
    for i in range(1, days + 1):
        d = today - timedelta(days=i)
        r = day(d.isoformat())
        if not r.get("ok") or r.get("wornMin", 0) < 600:          # < 10 h worn: not a full day
            continue
        ex = sum(w.get("min", 0) for w in r.get("workouts", []))
        rows = [("strain", r["strain"]), ("exercise_min", round(ex))]
        for m, v in rows:
            if m == "exercise_min" and db.one("SELECT 1 AS x FROM signals WHERE day = ? AND metric = ? AND source != 'WHOOP'", (d.isoformat(), m)):
                continue                                             # Apple Health/phone value wins for exercise minutes
            db.exec_("INSERT OR REPLACE INTO signals (day, metric, value, source) VALUES (?,?,?,?)", (d.isoformat(), m, v, "WHOOP"))
            n += 1
    return n
