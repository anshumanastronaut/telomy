"""Per-30-s-epoch cardiorespiratory features from beats (our detector) for sleep staging.
Mirrors what the phone can compute (single-lead ECG, no motion). Everything is per-night robust-normalised.
Literature: HR/HRV time + frequency domain (Task Force 1996), DFA α1 (Penzel 2003), respiration rate/regularity
from ECG-derived respiration (Charlton 2016), position in the night (deep sleep early, REM late)."""
import numpy as np

EP = 30.0

def _interp(t, v, grid):
    return np.interp(grid, t, v) if len(t) > 1 else np.full(len(grid), np.nan)

def _band_powers(rr_t, rr, t0, t1):
    """Welch-like spectrum of RR resampled at 4 Hz over [t0, t1): VLF, LF, HF power and HF peak freq."""
    sel = (rr_t >= t0) & (rr_t < t1)
    if sel.sum() < 60: return [np.nan] * 5
    g = np.arange(t0, t1, 0.25)
    x = _interp(rr_t[sel], rr[sel], g); x = x - x.mean()
    x = x * np.hanning(len(x))
    f = np.fft.rfftfreq(len(x), 0.25); p = np.abs(np.fft.rfft(x)) ** 2
    def bp(a, b): m = (f >= a) & (f < b); return p[m].sum()
    vlf, lf, hf = bp(0.003, 0.04), bp(0.04, 0.15), bp(0.15, 0.4)
    m = (f >= 0.15) & (f < 0.4)
    hff = f[m][np.argmax(p[m])] if m.any() and p[m].max() > 0 else np.nan
    tot = vlf + lf + hf + 1e-9
    return [np.log(vlf + 1), np.log(lf + 1), np.log(hf + 1), lf / (hf + 1e-9), hff * 60]

def _dfa_a1(rr):
    if len(rr) < 64: return np.nan
    y = np.cumsum(rr - rr.mean()); F = []; ns = [4, 6, 8, 10, 12, 16]
    for n in ns:
        k = len(y) // n
        if k < 2: return np.nan
        seg = y[: k * n].reshape(k, n); xs = np.arange(n)
        res = [s - np.polyval(np.polyfit(xs, s, 1), xs) for s in seg]
        F.append(np.sqrt(np.mean(np.square(res))))
    return np.polyfit(np.log(ns), np.log(F), 1)[0]

def _edr_rate(t, amp, t0, t1):
    sel = (t >= t0) & (t < t1)
    if sel.sum() < 30: return np.nan
    g = np.arange(t0, t1, 0.25); x = _interp(t[sel], amp[sel], g)
    k = 32; x = x - np.convolve(np.pad(x, k // 2, mode="edge"), np.ones(k) / k, mode="same")[k // 2:k // 2 + len(x)]
    x = x * np.hanning(len(x)); f = np.fft.rfftfreq(len(x), 0.25); p = np.abs(np.fft.rfft(x)) ** 2
    m = (f >= 0.16) & (f <= 0.5)
    return f[m][np.argmax(p[m])] * 60 if m.any() else np.nan

NAMES = ["hr", "hr_5m", "hr_slope", "rmssd_ln", "rmssd5_ln", "sdnn5_ln", "pnn50", "vlf", "lf", "hf", "lfhf_ln", "hf_peak",
         "dfa_a1", "resp_amp", "resp_rate", "resp_rate_sd", "rr_cv", "art_frac", "night_pos"]

def epoch_features(beats_s, amps, n_epochs, t_offset=0.0):
    """beats_s: beat times (s), amps: R amplitudes; epoch i spans [t_offset + 30 i, +30)."""
    b = np.asarray(beats_s); a = np.asarray(amps)
    rr = np.diff(b) * 1000; t = b[1:]; am = a[1:]
    ok = (rr > 300) & (rr < 2000); ok[1:] &= np.abs(np.diff(rr)) < 0.2 * rr[1:]
    tc, rrc, amc = t[ok], rr[ok], am[ok]
    F = np.full((n_epochs, len(NAMES)), np.nan)
    resp = np.full(n_epochs, np.nan)
    for i in range(n_epochs):
        s0 = t_offset + i * EP; mid = s0 + EP / 2
        e = (tc >= s0) & (tc < s0 + EP); w5 = (tc >= mid - 150) & (tc < mid + 150)
        allb = (t >= s0) & (t < s0 + EP)
        if e.sum() < 8: continue
        r, r5 = rrc[e], rrc[w5]
        d, d5 = np.diff(r), np.diff(r5)
        hr = 60000 / r.mean()
        hr5 = 60000 / r5.mean() if len(r5) > 20 else hr
        slope = np.polyfit(tc[w5] - mid, 60000 / r5, 1)[0] * 60 if len(r5) > 20 else 0
        bp = _band_powers(tc, rrc, mid - 150, mid + 150)
        resp[i] = _edr_rate(tc, amc, mid - 32, mid + 32)
        F[i] = [hr, hr5, slope,
                np.log(np.sqrt(np.mean(d ** 2)) + 1) if len(d) else np.nan,
                np.log(np.sqrt(np.mean(d5 ** 2)) + 1) if len(d5) > 5 else np.nan,
                np.log(r5.std() + 1) if len(r5) > 5 else np.nan,
                np.mean(np.abs(d5) > 50) if len(d5) > 5 else np.nan,
                *bp[:3], np.log(bp[3] + 1e-3) if not np.isnan(bp[3]) else np.nan, bp[4],
                _dfa_a1(r5) if len(r5) >= 64 else np.nan,
                np.log(np.std(amc[w5]) + 1) if w5.sum() > 20 else np.nan,
                resp[i], np.nan, r5.std() / r5.mean() if len(r5) > 5 else np.nan,
                1 - e.sum() / max(1, allb.sum()), i / max(1, n_epochs - 1)]
    # breathing regularity: SD of breath rate over ±5 epochs (deep sleep breathes very regularly)
    for i in range(n_epochs):
        w = resp[max(0, i - 5): i + 6]; w = w[~np.isnan(w)]
        F[i, NAMES.index("resp_rate_sd")] = w.std() if len(w) >= 4 else np.nan
    return F

def normalise_night(F):
    """Per-night robust z-score (median / IQR) for every feature except position in the night."""
    G = F.copy()
    for j, n in enumerate(NAMES):
        if n == "night_pos": continue
        col = G[:, j]; v = col[~np.isnan(col)]
        if len(v) < 10: G[:, j] = 0; continue
        med = np.median(v); iqr = np.subtract(*np.percentile(v, [75, 25])) or 1.0
        G[:, j] = np.clip((col - med) / iqr, -5, 5)
    return np.nan_to_num(G)

def with_context(G, offsets=(-6, -2, 2, 6), smooth=(5, 15)):
    """Add neighbouring epochs and centred rolling means (sleep stages persist for minutes)."""
    n = len(G); cols = [G]
    for o in offsets:
        idx = np.clip(np.arange(n) + o, 0, n - 1); cols.append(G[idx])
    for k in smooth:
        ker = np.ones(k) / k
        cols.append(np.stack([np.convolve(np.pad(G[:, j], k // 2, mode="edge"), ker, mode="valid")[:n] for j in range(G.shape[1])], 1))
    return np.concatenate(cols, 1)
