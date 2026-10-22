"""Layer-1 session-signature extractor — what happens DURING a therapy session.

Takes the continuous vital stream (HR, HRV, SpO₂, skin-temp from the ring/patch) captured across a
cryo / HBOT / sauna / cold-plunge session and produces the per-session signature (baseline, peak/nadir,
time-to-extreme, response magnitude, recovery, AUC) + safety flags + a check against the modality's
expected acute response. Signal processing, not statistics — this feeds the case study and the safety
agent.

Known acute signatures (literature): HBOT → HR falls across phases, BP rises on decompression, **SpO₂
unreliable in-chamber (hyperoxia/ceiling)**; sauna → HR rises like moderate exercise, BP falls after;
cold/cryo → HR response unsettled (capture to learn).
"""
from __future__ import annotations
import numpy as np

EXPECT = {
    "far_infrared_sauna": {"hr": "up", "note": "HR rises like moderate exercise; BP falls after"},
    "whole_body_cryo": {"hr": "unsettled", "note": "direction unsettled in literature — we capture to learn"},
    "cold_plunge": {"hr": "spike_then_down", "note": "cold-shock HR spike, then bradycardic drift"},
    "hbot": {"hr": "down", "spo2": "unreliable", "note": "HR falls across phases; SpO₂ invalid in-chamber (hyperoxia)"},
}

def _series(x):
    a = np.asarray([v for v in x if v is not None], float)
    return a

def session_signature(vitals: dict, sample_hz: float = 1.0, baseline_frac: float = 0.15,
                      modality: str | None = None) -> dict:
    """vitals: {'hr':[...], 'spo2':[...], 'skin_temp':[...], 'hrv':[...]} sampled through the session."""
    out = {"modality": modality, "signals": {}, "safety_flags": []}
    hr = _series(vitals.get("hr", []))
    for name, arr in [("hr", hr), ("spo2", _series(vitals.get("spo2", []))),
                      ("skin_temp", _series(vitals.get("skin_temp", []))), ("hrv", _series(vitals.get("hrv", [])))]:
        if arr.size < max(5, int(sample_hz * 10)):
            continue
        nb = max(3, int(len(arr) * baseline_frac))
        baseline = float(arr[:nb].mean())
        peak_i, nadir_i = int(arr.argmax()), int(arr.argmin())
        recovery = float(arr[-nb:].mean()) - baseline     # end vs baseline
        out["signals"][name] = {
            "baseline": round(baseline, 2), "peak": round(float(arr.max()), 2), "nadir": round(float(arr.min()), 2),
            "time_to_peak_s": round(peak_i / sample_hz, 1), "time_to_nadir_s": round(nadir_i / sample_hz, 1),
            "response_up": round(float(arr.max()) - baseline, 2), "response_down": round(float(arr.min()) - baseline, 2),
            "end_vs_baseline": round(recovery, 2),
            "auc_vs_baseline": round(float(np.trapezoid(arr - baseline) / sample_hz), 1)}
    # safety flags (deterministic)
    spo2 = _series(vitals.get("spo2", []))
    if modality != "hbot" and spo2.size and (spo2 < 88).sum() >= max(3, int(sample_hz * 10)):
        out["safety_flags"].append("sustained SpO₂ < 88% — stop session, assess")
    if hr.size and (hr.max() > 180 or (hr.min() < 35 and modality not in ("cold_plunge",))):
        out["safety_flags"].append(f"HR out of safe range (min {hr.min():.0f}, max {hr.max():.0f})")
    # expected-response check
    exp = EXPECT.get(modality or "", {})
    if exp:
        out["expected"] = exp
        if "hr" in exp and "hr" in out["signals"]:
            sig = out["signals"]["hr"]
            up, dn, end = sig["response_up"], sig["response_down"], sig["end_vs_baseline"]
            # direction = the dominant in-session deviation (sauna rises during; HBOT drifts down & stays)
            got = "up" if (abs(up) >= abs(dn) and up > 2) else ("down" if end < -2 or dn < -2 else "flat")
            out["matches_expected"] = exp["hr"] in (got, "unsettled", "spike_then_down")
        if exp.get("spo2") == "unreliable":
            out["safety_flags"] = [f for f in out["safety_flags"] if "SpO₂" not in f]  # don't trust in-chamber SpO2
            out.setdefault("notes", []).append("SpO₂ ignored for safety in HBOT (hyperoxia/oximeter ceiling)")
    return out

if __name__ == "__main__":
    import json
    hz = 1.0; n = 600  # 10-min session at 1 Hz
    t = np.arange(n)
    # sauna: HR rises from 70 to ~120 then eases
    sauna_hr = 70 + 50 * np.sin(np.pi * t / n) + np.random.default_rng(1).normal(0, 2, n)
    print("SAUNA:", json.dumps(session_signature({"hr": list(sauna_hr)}, hz, modality="far_infrared_sauna")["signals"]["hr"], indent=2))
    print("  matches expected:", session_signature({"hr": list(sauna_hr)}, hz, modality="far_infrared_sauna").get("matches_expected"))
    # HBOT: HR drifts down 72 -> 60
    hbot_hr = np.linspace(72, 60, n) + np.random.default_rng(2).normal(0, 1.5, n)
    r = session_signature({"hr": list(hbot_hr), "spo2": list(np.full(n, 99.0))}, hz, modality="hbot")
    print("\nHBOT hr end_vs_baseline:", r["signals"]["hr"]["end_vs_baseline"], "| matches:", r.get("matches_expected"), "| notes:", r.get("notes"))
