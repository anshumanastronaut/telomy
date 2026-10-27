"""Sleep fusion & filter — the 'what to show' layer of the Telomy fusion engine.

Takes raw per-device sleep sessions (WHOOP via NOOP today; Telomy ring / Apple Health as they sync) and returns one
clean, reconciled view instead of a pile of raw sessions:

  • NIGHT vs NAP: the long overnight block is the night; a session that starts in daylight is a nap. A nap must never
    masquerade as "last night" (that was the bug the user hit).
  • CONFIDENCE it was real sleep, not lying-still-awake. We learned the hard way (2026-10-18) that stillness alone is
    not sleep — WHOOP and motion methods over-call it, HR is the discriminator. So a daytime session is only kept as a
    real nap when it has sleep-like efficiency AND a genuine sleeping-HR drop; otherwise it is flagged, not shown.
  • The USER is the ground truth. Low-confidence naps are surfaced to confirm ("did you nap 16:43–18:44?"), never
    asserted. Confirmations feed back as labels.

Pure functions, no DB — callable from the endpoint and tested directly.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))   # TODO: per-user timezone from profile

# tunables (deliberately conservative; a nap is only kept when it really looks like sleep)
NAP_START, NAP_END = 8, 20          # a session starting in [08:00, 20:00) local is a daytime nap, else a night
MIN_NIGHT_H = 3.0                   # an overnight block under 3 h asleep is a fragment of lying-still, not a scored night
MIN_NAP_H = 0.25                    # < 15 min daytime stillness is not a nap
MIN_NAP_EFF = 0.5                   # sleep efficiency below this = mostly awake = quiet wakefulness, not sleep
MIN_HR_DROP = 3.0                   # sleeping HR must sit at least this far below the day's resting read


def classify(n: dict, tz: timezone = IST) -> dict:
    """Tag one session night|nap, add confidence + duration, and flag a non-credible nap (never flag a night)."""
    start_h = datetime.fromtimestamp(n["start"], tz).hour
    dur_h = (n["end"] - n["start"]) / 3600
    eff = n.get("efficiency") or 0.0
    kind = "nap" if NAP_START <= start_h < NAP_END else "night"
    # a real sleeping-HR drop: sleepHr below restingHr is the WHOOP read; keep it simple and robust to missing fields
    sleep_hr, rest = n.get("sleepHr"), n.get("restingHr")
    hr_drop = (sleep_hr - rest) if (sleep_hr is not None and rest is not None) else None
    out = dict(n, kind=kind, duration_h=round(dur_h, 2),
               confidence=round(min(1.0, eff), 2) if eff else None)
    if kind == "nap":
        credible = dur_h >= MIN_NAP_H and eff >= MIN_NAP_EFF
        if not credible:
            out["rejected"] = "too short or low sleep efficiency — likely quiet wakefulness, not sleep"
        elif eff < 0.75 or (hr_drop is not None and hr_drop > -MIN_HR_DROP):
            out["needs_confirm"] = True   # looks like a nap but not certain — ask the user, don't assert
    else:  # night — a short overnight block is a lying-still fragment, not the night (user hit this: 1 h "night" while awake)
        if dur_h < MIN_NIGHT_H:
            out["rejected"] = "overnight block under 3 h — likely lying still but awake, not a scored night"
    return out


def fuse(nights: list[dict], tz: timezone = IST) -> dict:
    """Split a raw session list into clean nights, kept naps, and flagged/rejected sessions with provenance."""
    classed = [classify(n, tz) for n in nights]
    return {
        "nights": [n for n in classed if n["kind"] == "night" and not n.get("rejected")],
        "naps": [n for n in classed if n["kind"] == "nap" and not n.get("rejected")],
        "rejected": [n for n in classed if n.get("rejected")],
    }


if __name__ == "__main__":
    import json
    demo = [
        {"start": 1792266782, "end": 1792266782 + 471 * 60, "efficiency": 0.905, "sleepHr": 63.8, "restingHr": 56.5},  # night
        {"start": 1792322036, "end": 1792322036 + 121 * 60, "efficiency": 0.888, "sleepHr": 74.2, "restingHr": 58.9},  # real nap
        {"start": 1792322036, "end": 1792322036 + 10 * 60, "efficiency": 0.3},                                         # false nap
    ]
    print(json.dumps({k: len(v) for k, v in fuse(demo).items()}))
    for n in fuse(demo)["nights"] + fuse(demo)["naps"] + fuse(demo)["rejected"]:
        print(" ", n["kind"], round(n["duration_h"], 1), "h", "conf", n.get("confidence"),
              "| rejected" if n.get("rejected") else ("| confirm?" if n.get("needs_confirm") else ""))
