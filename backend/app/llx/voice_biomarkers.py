"""Voice biomarkers — stress / arousal from speech acoustics (the Omi-style signal).

Extracts acoustic features from a short speech segment and returns a RELATIVE arousal/stress index vs
the person's own baseline. Honest framing (per the 2024-25 literature): speech acoustics track
*physiological arousal* more than labelled emotion; absolute thresholds are unreliable and sex/individual-
dependent (F0 effect weakens after publication-bias correction; jitter/shimmer inconsistent). So we use
a personal baseline + trend, never an absolute "you are stressed" claim. Features: F0 (pitch), energy,
voiced fraction / pause ratio, speaking-rate proxy, spectral tilt (alpha-ratio), jitter & shimmer proxies.

Privacy: operates on an already-captured waveform array (the app captures on-device with consent). We
return derived features only — raw audio is never stored or sent by this module.

Deps: numpy, scipy (both in the project venv). No raw-audio I/O here (that's the native/ASR layer).
"""
from __future__ import annotations
import numpy as np
from scipy.signal import stft

def _frames(x, sr, win=0.025, hop=0.010):
    n, h = int(win * sr), int(hop * sr)
    if len(x) < n:
        return np.empty((0, n))
    idx = range(0, len(x) - n + 1, h)
    return np.stack([x[i:i + n] for i in idx])

def _f0_autocorr(frame, sr, fmin=75, fmax=400):
    f = frame - frame.mean()
    if np.sqrt((f * f).mean()) < 1e-4:
        return None
    ac = np.correlate(f, f, "full")[len(f) - 1:]
    lo, hi = int(sr / fmax), int(sr / fmin)
    if hi >= len(ac):
        return None
    peak = lo + int(np.argmax(ac[lo:hi]))
    if ac[peak] <= 0 or ac[0] <= 0 or ac[peak] / ac[0] < 0.3:   # weak periodicity = unvoiced
        return None
    return sr / peak

def features(waveform, sr: int) -> dict:
    """Acoustic feature set from a mono waveform (float, any scale)."""
    x = np.asarray(waveform, float)
    x = x / (np.max(np.abs(x)) + 1e-9)
    fr = _frames(x, sr)
    if len(fr) == 0:
        return {"error": "segment too short"}
    rms = np.sqrt((fr ** 2).mean(axis=1))
    voiced = rms > max(0.02, np.percentile(rms, 40))
    f0s = [v for v in (_f0_autocorr(fr[i], sr) for i in np.where(voiced)[0]) if v]
    f0 = np.array(f0s) if f0s else np.array([np.nan])
    # spectral tilt (alpha ratio: energy >1kHz vs <1kHz) — rises with vocal effort/arousal
    f, _, Z = stft(x, fs=sr, nperseg=min(1024, len(x)))
    P = (np.abs(Z) ** 2).mean(axis=1)
    lo_e, hi_e = P[f < 1000].sum(), P[f >= 1000].sum()
    alpha_ratio = float(10 * np.log10((hi_e + 1e-9) / (lo_e + 1e-9)))
    # jitter (F0 period variability) & shimmer (amplitude variability) proxies
    jitter = float(np.nanstd(np.diff(f0)) / (np.nanmean(f0) + 1e-9)) if len(f0) > 2 else np.nan
    voiced_rms = rms[voiced]
    shimmer = float(np.std(np.diff(voiced_rms)) / (np.mean(voiced_rms) + 1e-9)) if voiced_rms.size > 2 else np.nan
    return {"f0_mean": _r(np.nanmean(f0)), "f0_cv": _r(np.nanstd(f0) / (np.nanmean(f0) + 1e-9)),
            "energy_mean": _r(rms.mean()), "energy_cv": _r(rms.std() / (rms.mean() + 1e-9)),
            "voiced_fraction": _r(voiced.mean()), "pause_ratio": _r(1 - voiced.mean()),
            "speaking_rate_proxy": _r(_onsets(voiced) / (len(x) / sr)), "alpha_ratio_db": _r(alpha_ratio),
            "jitter": _r(jitter), "shimmer": _r(shimmer), "duration_s": _r(len(x) / sr)}

def _onsets(voiced):
    return int(np.sum((voiced[1:].astype(int) - voiced[:-1].astype(int)) == 1))

def _r(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 4)

# features that rise with physiological arousal (personal-baseline z-score combine)
_AROUSAL = {"f0_mean": +1, "energy_mean": +1, "speaking_rate_proxy": +1, "alpha_ratio_db": +1, "f0_cv": +1}

def build_baseline(feature_dicts: list[dict]) -> dict:
    """Per-feature mean + SD from several CALM segments — the only valid basis for the arousal index."""
    out = {}
    for k in _AROUSAL:
        vals = [fd[k] for fd in feature_dicts if fd.get(k) is not None]
        if len(vals) >= 3:
            out[k] = {"mean": float(np.mean(vals)), "sd": float(np.std(vals, ddof=1))}
    return {"per_feature": out, "n_segments": len(feature_dicts)}

def arousal_index(feat: dict, baseline: dict | None) -> dict:
    """Relative arousal/stress vs the person's calm baseline (from build_baseline). Skips any feature that
    lacks a real baseline SD — we never fabricate a spread, so one feature can't dominate."""
    bf = (baseline or {}).get("per_feature") if baseline else None
    if not bf:
        return {"index": None, "note": "needs a personal voice baseline from >=3 calm segments "
                                        "(build_baseline) — absolute voice-stress thresholds are unreliable"}
    zs, used = [], []
    for k, sign in _AROUSAL.items():
        v = feat.get(k); b = bf.get(k)
        if v is None or not b or b["sd"] <= 1e-6:
            continue
        zs.append(sign * (v - b["mean"]) / b["sd"]); used.append(k)
    if not zs:
        return {"index": None, "note": "insufficient overlapping features vs baseline"}
    z = float(np.mean(zs))
    tier = "elevated" if z >= 1.0 else "mildly elevated" if z >= 0.4 else "baseline" if z > -0.4 else "calm"
    return {"index": round(z, 2), "arousal_tier": tier, "features_used": used,
            "note": "physiological arousal relative to YOUR calm baseline — a trend signal, not an emotion "
                    "diagnosis (speech tracks arousal more than labelled affect; validate per-person over time)"}

if __name__ == "__main__":
    import json
    sr = 16000; t = np.arange(int(2.5 * sr)) / sr
    calm = 0.3 * np.sin(2 * np.pi * 120 * t) * (np.random.default_rng(1).random(len(t)) > 0.3)
    tense = 0.6 * np.sin(2 * np.pi * 180 * t) * (np.random.default_rng(2).random(len(t)) > 0.15)
    fc, ft = features(calm, sr), features(tense, sr)
    print("calm  :", json.dumps({k: fc[k] for k in ("f0_mean", "energy_mean", "speaking_rate_proxy", "alpha_ratio_db")}))
    print("tense :", json.dumps({k: ft[k] for k in ("f0_mean", "energy_mean", "speaking_rate_proxy", "alpha_ratio_db")}))
    print("arousal vs calm-baseline:", json.dumps(arousal_index(ft, fc), indent=2))
