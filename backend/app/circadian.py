"""Circadian engine — diagnose, track and help fix the body clock from the continuous vitals timeline.

Method (grounded, not a black box): the body clock leaves a signature in the 24-h rhythm of heart rate, HRV,
skin/▸core temperature and activity. We fit a **cosinor** model (the standard in chronobiology) to those signals
to recover the rhythm's MESOR, amplitude, acrophase (peak time) and robustness (R²), estimate the **circadian
phase** from the heart-rate / temperature **nadir** (a validated proxy for the core-body-temperature minimum,
which tracks dim-light melatonin onset ~2–3 h earlier), measure **regularity** (day-to-day phase scatter) and
**social jetlag** (weekday vs free-day mid-sleep), then flag faults and give evidence-based fixes.

Honesty: wearable-derived phase is a PROXY for DLMO (the lab gold standard), accurate to roughly ±1–2 h in
people with regular schedules and worse in shift workers; this is decision-support, not a sleep-clinic diagnosis.
There is no large free DLMO-labelled dataset to "train" a learned phase model on (UK Biobank / MESA / MrOS all
need applications; BioDare2 is the open circadian repo) — so the engine uses the validated cosinor + nadir method
with published norms, and calibrates the phase→DLMO offset per person as their own data accrues (n-of-1).
"""
from __future__ import annotations
import math
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

# Which signal to use for the rhythm, best first. Each is (metric, "good phase = trough" direction).
# Resting HR and core temperature both fall to a nocturnal minimum ~4–5 a.m.; activity peaks mid-day.
_RHYTHM_PRIORITY = ["hr", "skin_temp", "hrv", "steps", "motion", "resp"]


def _hour_of(ts: float, tz=IST) -> float:
    d = datetime.fromtimestamp(ts, tz)
    return d.hour + d.minute / 60 + d.second / 3600


def cosinor(points: list, period_h: float = 24.0) -> dict | None:
    """Least-squares cosine fit at a fixed period. points = [[epoch_s, value], ...] (any span).
    Returns MESOR (rhythm-adjusted mean), amplitude, acrophase (clock hour of the peak), nadir hour, and R²
    (how much of the variance the 24-h rhythm explains — the rhythm's robustness)."""
    xs, ys = [], []
    for p in points:
        v = p[1] if isinstance(p, (list, tuple)) else p.get("value")
        t = p[0] if isinstance(p, (list, tuple)) else p.get("ts")
        if v is None or t is None:
            continue
        xs.append(_hour_of(float(t))); ys.append(float(v))
    n = len(ys)
    if n < 24:
        return None
    w = 2 * math.pi / period_h
    # fit y = M + A·cos(w t) + B·sin(w t)  via normal equations (3×3)
    Sc = sum(math.cos(w * x) for x in xs); Ss = sum(math.sin(w * x) for x in xs)
    Scc = sum(math.cos(w * x) ** 2 for x in xs); Sss = sum(math.sin(w * x) ** 2 for x in xs)
    Scs = sum(math.cos(w * x) * math.sin(w * x) for x in xs)
    Sy = sum(ys); Syc = sum(y * math.cos(w * x) for x, y in zip(xs, ys)); Sys = sum(y * math.sin(w * x) for x, y in zip(xs, ys))
    # solve [[n,Sc,Ss],[Sc,Scc,Scs],[Ss,Scs,Sss]] · [M,A,B] = [Sy,Syc,Sys]
    a = [[n, Sc, Ss], [Sc, Scc, Scs], [Ss, Scs, Sss]]
    b = [Sy, Syc, Sys]
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
           - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    if abs(det) < 1e-9:
        return None

    def solve(col):
        m = [row[:] for row in a]
        for i in range(3):
            m[i][col] = b[i]
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])) / det
    M, A, B = solve(0), solve(1), solve(2)
    amp = math.hypot(A, B)
    acro = (math.atan2(B, A) / w) % period_h             # clock hour of the peak (time of maximum)
    nadir = (acro + period_h / 2) % period_h
    ybar = Sy / n
    ss_tot = sum((y - ybar) ** 2 for y in ys) or 1e-9
    ss_res = sum((y - (M + A * math.cos(w * x) + B * math.sin(w * x))) ** 2 for x, y in zip(xs, ys))
    r2 = max(0.0, 1 - ss_res / ss_tot)
    return {"mesor": round(M, 1), "amplitude": round(amp, 2), "acrophase_h": round(acro, 2),
            "nadir_h": round(nadir, 2), "r2": round(r2, 3), "n": n}


def _fmt_h(h: float) -> str:
    h = h % 24
    return f"{int(h):02d}:{int(round((h - int(h)) * 60)) % 60:02d}"


def _per_day_nadir(points: list) -> list:
    """Nadir clock-hour per calendar day (IST) — for day-to-day regularity."""
    from collections import defaultdict
    by_day = defaultdict(list)
    for p in points:
        t = p[0] if isinstance(p, (list, tuple)) else p.get("ts")
        if t is None:
            continue
        by_day[datetime.fromtimestamp(float(t), IST).date().isoformat()].append(p)
    out = []
    for day, pts in sorted(by_day.items()):
        c = cosinor(pts)
        if c and c["r2"] >= 0.1:
            out.append((day, c["nadir_h"]))
    return out


def _circ_sd(hours: list) -> float:
    """Circular SD of clock hours (handles the midnight wrap)."""
    if len(hours) < 2:
        return 0.0
    ang = [h / 24 * 2 * math.pi for h in hours]
    C = sum(math.cos(a) for a in ang) / len(ang); S = sum(math.sin(a) for a in ang) / len(ang)
    R = math.hypot(C, S)
    return round(math.sqrt(max(0.0, -2 * math.log(max(R, 1e-9)))) * 24 / (2 * math.pi), 2)


def social_jetlag(sleep_windows: list) -> dict | None:
    """|mid-sleep on free days − mid-sleep on work days| (Roenneberg). sleep_windows = [{start,end,workday}]."""
    def mid(w):
        return ((_hour_of(w["start"]) + _hour_of(w["end"]) + (24 if _hour_of(w["end"]) < _hour_of(w["start"]) else 0)) / 2) % 24
    work = [mid(w) for w in sleep_windows if w.get("workday")]
    free = [mid(w) for w in sleep_windows if not w.get("workday")]
    if not work or not free:
        return None
    sjl = abs((sum(free) / len(free)) - (sum(work) / len(work)))
    sjl = min(sjl, 24 - sjl)
    return {"hours": round(sjl, 2), "msf_free": round(sum(free) / len(free), 2), "msf_work": round(sum(work) / len(work), 2),
            "severity": "high" if sjl >= 2 else "moderate" if sjl >= 1 else "low"}


def assess(series: dict | None = None, sleep_windows: list | None = None, chronotype: str | None = None,
           target_wake_h: float = 6.5) -> dict:
    """Diagnose the body clock from the continuous timeline.

    series: {metric: [[epoch_s, value], ...]} — HR/skin_temp/HRV/steps/motion/resp from vitals_ts (≥2–3 days
            of data gives a usable estimate; more is better).
    sleep_windows: optional [{start, end, workday}] for social jetlag.
    target_wake_h: the person's desired wake time (local hours) — the phase goal to align to.
    """
    series = series or {}
    metric = next((m for m in _RHYTHM_PRIORITY if series.get(m) and len(series[m]) >= 24), None)
    if not metric:
        return {"status": "insufficient_data",
                "note": "Need ≥1 day of continuous HR/temperature/activity (wear the patch, ring or WHOOP) to read the body clock."}
    pts = series[metric]
    fit = cosinor(pts)
    if not fit:
        return {"status": "insufficient_data", "note": "Rhythm fit failed — more continuous data needed."}

    # phase proxy: for HR/temp the NADIR ≈ core-body-temperature minimum (~2–3 h after DLMO, ~2 h before wake).
    trough_metric = metric in ("hr", "skin_temp", "resp")
    phase_h = fit["nadir_h"] if trough_metric else (fit["acrophase_h"] + 12) % 24  # activity acrophase→CBT nadir ~12h opposite
    cbt_min = phase_h
    dlmo_est = (cbt_min - 7) % 24          # DLMO ≈ CBTmin − 7 h (population mean)
    est_wake = (cbt_min + 2) % 24          # natural wake ≈ CBTmin + 2 h

    # regularity (day-to-day phase scatter) + days of data
    nad = _per_day_nadir(pts)
    reg_sd = _circ_sd([h for _, h in nad]) if len(nad) >= 2 else None
    days = len({datetime.fromtimestamp(float(p[0]), IST).date() for p in pts if (p[0] if isinstance(p, (list, tuple)) else None)})

    # robustness: a real circadian rhythm needs BOTH a coherent 24-h fit (R²) AND a meaningful day-night swing
    # (fractional amplitude). A tiny-but-clean rhythm has high R² but a flat clock, so check amplitude too.
    frac_amp = fit["amplitude"] / max(abs(fit["mesor"]), 1.0)
    weak = (fit["r2"] < 0.3) or (trough_metric and frac_amp < 0.06)
    rhythmic = not weak

    # degenerate fit: when samples don't span enough of the 24-h cycle the cosinor extrapolates wildly — an
    # impossible baseline (e.g. negative HR) or a swing bigger than the mean. Phase/amplitude are then unreliable,
    # so we don't emit delayed/advanced/flat verdicts off it; we ask for more continuous wear instead.
    hours_covered = len({datetime.fromtimestamp(float(p[0]), IST).hour for p in pts if isinstance(p, (list, tuple))})
    sane_mesor = {"hr": (35, 120), "resp": (6, 30), "skin_temp": (25, 40), "hrv": (5, 300)}
    lo, hi = sane_mesor.get(metric, (float("-inf"), float("inf")))
    degenerate = (not (lo <= fit["mesor"] <= hi)) or (trough_metric and frac_amp > 0.6) or hours_covered < 12
    if degenerate:
        return {
            "status": "ok", "signal": metric, "days_of_data": days, "confidence": "low",
            "rhythm": {**fit, "acrophase": _fmt_h(fit["acrophase_h"]), "nadir": _fmt_h(fit["nadir_h"]), "robust": False},
            "phase": None, "regularity": {"day_to_day_sd_h": reg_sd, "days_fit": len(nad)},
            "social_jetlag": social_jetlag(sleep_windows) if sleep_windows else None,
            "faults": [], "fixes": [],
            "alignment": {"target_wake": _fmt_h(target_wake_h), "estimated_vs_target_h": None, "verdict": "building_baseline"},
            "note": f"Only {hours_covered} h of the day are covered so far — not enough continuous around-the-clock wear "
                    "to read the body clock reliably. Wear the patch, ring or WHOOP across full days (ideally 3+) and this sharpens.",
            "disclaimer": "Decision-support from your wearable rhythm — a proxy for the clinical dim-light melatonin onset, not a diagnosis.",
            "method": "cosinor 24-h fit + heart-rate/temperature nadir phase proxy (CBTmin→DLMO offset); chronobiology-standard.",
        }

    # ---- diagnose faults ----
    faults = []
    # delayed / advanced phase vs target (CBTmin should sit ~2 h before target wake)
    want_cbt = (target_wake_h - 2) % 24
    delta = ((cbt_min - want_cbt + 12) % 24) - 12       # signed hours (late +, early −)
    if delta >= 1.5:
        faults.append({"fault": "delayed_phase", "severity": "high" if delta >= 3 else "moderate",
                       "detail": f"Your clock runs ~{abs(round(delta,1))} h late (body-temperature low ≈ {_fmt_h(cbt_min)}, natural wake ≈ {_fmt_h(est_wake)}).",
                       "grade": "C"})
    elif delta <= -1.5:
        faults.append({"fault": "advanced_phase", "severity": "high" if delta <= -3 else "moderate",
                       "detail": f"Your clock runs ~{abs(round(delta,1))} h early (natural wake ≈ {_fmt_h(est_wake)}).", "grade": "C"})
    if not rhythmic:
        why = (f"only {int(fit['r2']*100)}% of the {metric} variation follows a 24-h clock" if fit["r2"] < 0.3
               else f"the day–night swing is only {round(frac_amp*100,1)}% of the mean")
        faults.append({"fault": "low_amplitude", "severity": "high" if (fit["r2"] < 0.15 or frac_amp < 0.03) else "moderate",
                       "detail": f"Flat rhythm ({why}) — weak day/night contrast, common with irregular light, shift work, low daytime activity, or poor sleep.",
                       "grade": "C"})
    if reg_sd is not None and reg_sd >= 1.5:
        faults.append({"fault": "irregular_timing", "severity": "high" if reg_sd >= 2.5 else "moderate",
                       "detail": f"Your clock drifts ~{reg_sd} h day to day — an irregular schedule the body can't anchor to.", "grade": "C"})
    sjl = social_jetlag(sleep_windows) if sleep_windows else None
    if sjl and sjl["hours"] >= 1:
        faults.append({"fault": "social_jetlag", "severity": sjl["severity"],
                       "detail": f"Social jetlag {sjl['hours']} h (weekend mid-sleep {_fmt_h(sjl['msf_free'])} vs weekday {_fmt_h(sjl['msf_work'])}) — like flying across time zones every week.", "grade": "B"})

    # ---- fixes (evidence-based circadian hygiene, targeted to the fault) ----
    fixes = _fixes(faults, cbt_min, est_wake, target_wake_h)

    confidence = "high" if (days >= 3 and hours_covered >= 20) else "moderate" if days >= 2 else "low"
    return {
        "status": "ok",
        "signal": metric, "days_of_data": days, "confidence": confidence,
        "rhythm": {**fit, "acrophase": _fmt_h(fit["acrophase_h"]), "nadir": _fmt_h(fit["nadir_h"]), "robust": rhythmic},
        "phase": {"cbt_min_est": _fmt_h(cbt_min), "dlmo_est": _fmt_h(dlmo_est), "natural_wake_est": _fmt_h(est_wake),
                  "note": "Body-temperature minimum and DLMO are estimated from the rhythm (±1–2 h); not a lab measurement."},
        "regularity": {"day_to_day_sd_h": reg_sd, "days_fit": len(nad)},
        "social_jetlag": sjl,
        "faults": faults,
        "fixes": fixes,
        "alignment": {"target_wake": _fmt_h(target_wake_h), "estimated_vs_target_h": round(delta, 1),
                      "verdict": "aligned" if abs(delta) < 1.5 and rhythmic else "misaligned"},
        "disclaimer": "Decision-support from your wearable rhythm — a proxy for the clinical dim-light melatonin "
                      "onset, not a diagnosis. Persistent disruption, or suspected a circadian sleep disorder or "
                      "shift-work disorder, warrants a sleep clinician.",
        "method": "cosinor 24-h fit + heart-rate/temperature nadir phase proxy (CBTmin→DLMO offset); chronobiology-standard.",
    }


def _fixes(faults: list, cbt_min: float, est_wake: float, target_wake_h: float) -> list:
    kinds = {f["fault"] for f in faults}
    out = []
    if "delayed_phase" in kinds:
        out += [
            {"grade": "A", "lever": "Morning bright light", "do": f"Get 20–30 min of bright light (outdoors best, or 10,000-lux lamp) within ~30 min of your target wake ({_fmt_h(target_wake_h)}). Light just after the body-temperature low advances the clock earlier."},
            {"grade": "A", "lever": "Dim the evening", "do": "From ~2–3 h before target sleep, cut bright/blue light (dim lamps, screens to night mode or off). Evening light is what pushes a night-owl clock later."},
            {"grade": "B", "lever": "Low-dose melatonin (clinician)", "do": f"0.5 mg ~5–6 h before target sleep (≈ {_fmt_h((target_wake_h-2-6)%24)}) can advance the phase — a prescriber's call, not a sleep aid dose."},
            {"grade": "B", "lever": "Anchor meals & caffeine", "do": "Eat breakfast soon after waking; last caffeine ≥8 h before bed; last meal ≥3 h before bed. Food is a clock cue."},
        ]
    if "advanced_phase" in kinds:
        out += [{"grade": "B", "lever": "Evening light", "do": "Bright light in the early evening and avoid very early-morning light to hold the clock later."}]
    if "low_amplitude" in kinds:
        out += [
            {"grade": "A", "lever": "Sharpen day vs night", "do": "Strong light + movement in the morning/daytime; darkness and cool, quiet at night. A bigger light/dark and activity contrast rebuilds rhythm amplitude."},
            {"grade": "B", "lever": "Daytime time-restricted eating", "do": "Keep eating within a consistent daytime window (e.g. 9–10 h, not late at night) to reinforce the peripheral clocks."},
        ]
    if "irregular_timing" in kinds or "social_jetlag" in kinds:
        out += [
            {"grade": "A", "lever": "Fixed wake time", "do": f"Wake within ±30 min of {_fmt_h(target_wake_h)} every day — including weekends. A constant wake + morning light is the single strongest anchor."},
            {"grade": "B", "lever": "Shrink the weekend shift", "do": "Keep weekend sleep timing within ~1 h of weekdays to cut social jetlag."},
        ]
    if not out:
        out = [{"grade": "A", "lever": "Keep it steady", "do": f"Your clock looks aligned — hold a consistent wake time (~{_fmt_h(target_wake_h)}) with morning light and a dim evening to keep it that way."}]
    return out
