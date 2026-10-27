"""Reference fall-detection algorithm (accelerometer), designed for low false alarms.

A real fall has a recognisable 3-phase signature, and using all three is what separates it from
"sat down hard" (the #1 false trigger):
  1. free-fall  — acceleration magnitude dips well below 1 g (the body is unsupported),
  2. impact     — a sharp peak (typically > 2.5–3 g),
  3. immobility — stillness afterwards (a person who fell and is hurt stops moving).

We require impact + post-impact immobility, and treat free-fall as a confidence booster (not all
falls have a clean free-fall phase). Confidence combines the three; the emergency workflow only
auto-escalates on high confidence AND sustained immobility — never on a lone impact spike.

This is the portable reference (Python, testable). The iOS build mirrors it in Swift/CoreMotion at
~50 Hz; thresholds are the tunables. Validate on real-fall data (FARSEEING), report false-alarms/day.
"""
from __future__ import annotations
import math
from dataclasses import dataclass

@dataclass
class FallConfig:
    sample_hz: float = 50.0
    freefall_g: float = 0.6         # magnitude below this = unsupported
    impact_g: float = 2.5           # peak above this = impact
    immobile_band: float = 0.18     # |mag-1g| below this counts as "still"
    immobile_secs: float = 2.0      # stillness required after impact
    freefall_window_s: float = 0.6  # free-fall must occur within this before impact

def _mag(sample):
    if isinstance(sample, (int, float)):
        return float(sample)
    x, y, z = sample
    return math.sqrt(x * x + y * y + z * z)

def detect_fall(samples, cfg: FallConfig = FallConfig()) -> dict:
    """samples: sequence of 3-axis tuples OR precomputed magnitudes (in g). Returns a fall verdict."""
    mags = [_mag(s) for s in samples]
    n = len(mags)
    if n < int(cfg.sample_hz):            # need ~1s of data
        return {"fall": False, "reason": "insufficient_data"}
    # impact = global peak if it clears the threshold
    peak_i = max(range(n), key=lambda i: mags[i])
    peak_g = mags[peak_i]
    if peak_g < cfg.impact_g:
        return {"fall": False, "confidence": 0.0, "impact_g": round(peak_g, 2), "reason": "no_impact"}
    # free-fall just before impact?
    ff_lo = max(0, peak_i - int(cfg.freefall_window_s * cfg.sample_hz))
    had_freefall = any(mags[i] < cfg.freefall_g for i in range(ff_lo, peak_i))
    # immobility after impact?
    im_lo = peak_i + int(0.3 * cfg.sample_hz)
    im_hi = im_lo + int(cfg.immobile_secs * cfg.sample_hz)
    window = mags[im_lo:im_hi]
    immobile = len(window) >= int(cfg.immobile_secs * cfg.sample_hz * 0.8) and \
        all(abs(m - 1.0) < cfg.immobile_band for m in window)
    # confidence: impact (0.4) + immobility (0.4) + free-fall (0.2)
    conf = 0.4 * min(1.0, (peak_g - cfg.impact_g) / 2.0 + 0.5) + 0.4 * immobile + 0.2 * had_freefall
    conf = round(min(1.0, conf), 2)
    fall = bool(immobile and peak_g >= cfg.impact_g)   # require impact AND immobility (low false alarms)
    return {"fall": fall, "confidence": conf, "impact_g": round(peak_g, 2),
            "had_freefall": had_freefall, "post_impact_immobile": immobile,
            "reason": "impact+immobility" if fall else "impact_without_immobility(likely_not_a_fall)"}

if __name__ == "__main__":
    import json, random
    hz = 50; N = hz * 6
    def walking():
        return [1.0 + 0.3 * math.sin(i / 3.0) + random.uniform(-0.1, 0.1) for i in range(N)]
    def sit_hard():   # impact spike but person keeps moving (NOT a fall)
        s = walking(); s[hz * 2] = 2.8
        for i in range(hz * 2 + 15, hz * 2 + 115): s[i] = 1.0 + random.uniform(-0.4, 0.4)
        return s
    def real_fall():  # free-fall -> impact -> stillness
        s = [1.0 + random.uniform(-0.05, 0.05) for _ in range(N)]
        for i in range(hz * 2 - 15, hz * 2): s[i] = 0.4       # free-fall
        s[hz * 2] = 3.4                                        # impact
        for i in range(hz * 2 + 15, hz * 2 + 150): s[i] = 1.0 + random.uniform(-0.05, 0.05)  # immobile
        return s
    for name, sig in [("walking", walking()), ("sat_down_hard", sit_hard()), ("real_fall", real_fall())]:
        print(f"{name:<14} -> {json.dumps(detect_fall(sig))}")
