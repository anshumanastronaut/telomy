"""ECG-derived respiration (EDR) prototype vs the slpdb respiration channel.
Per 64-s window (32-s hop): RR series and R-amplitude series → 4 Hz → detrend → Welch PSD 0.1–0.5 Hz peak.
Fusion (Karlen 2013 'smart fusion'): accept when the two estimates agree within 4 br/min, report their mean."""
import json, glob, os, numpy as np, wfdb
from scipy.signal import welch, butter, filtfilt
import sys
LO = float(sys.argv[1]) if len(sys.argv) > 1 else 0.13
V = os.path.expanduser("~/telomy-lab/validate"); P = os.path.expanduser("~/telomy-lab/physionet/slpdb")
def peak(x, fs=4.0):
    k = int(8 * fs); x = x - np.convolve(np.pad(x, k // 2, mode="edge"), np.ones(k) / k, mode="same")[k // 2:k // 2 + len(x)]
    f, p = welch(x, fs=fs, nperseg=min(len(x), 128), nfft=1024)
    m = (f >= LO) & (f <= 0.5)
    if p[m].max() <= 0: return np.nan, 0
    k = np.argmax(p[m]); fk = f[m][k]
    near = m & (np.abs(f - fk) <= 0.03)
    return fk * 60, p[near].sum() / p[m].sum()     # spectral concentration around the peak
def edr_windows(bt, rr, amp, t0, t1):
    out = []
    for s in np.arange(t0, t1 - 64, 32):
        sel = (bt >= s) & (bt < s + 64)
        if sel.sum() < 40: out.append((s, np.nan, np.nan, np.nan)); continue
        g = np.arange(s, s + 64, 0.25)
        a = peak(np.interp(g, bt[sel], rr[sel]))[0]; b = peak(np.interp(g, bt[sel], amp[sel]))[0]
        fused = (a + b) / 2 if abs(a - b) <= 4 else np.nan
        out.append((s, a, b, fused))
    return out
allerr = {"rr": [], "amp": [], "fused": []}; cover = []; night = []
for f in sorted(glob.glob(f"{V}/data/slpdb_*.json")):
    name = os.path.basename(f)[:-5]; rec = name.split("_", 1)[1]
    try: o = json.load(open(f"{V}/out3/{name}.json")); r = wfdb.rdrecord(f"{P}/{rec}")
    except Exception as e: print(name, "skip", e); continue
    rch = [i for i, nm in enumerate(r.sig_name) if nm.startswith("Resp")]
    if not rch: print(name, "no resp", r.sig_name); continue
    resp = r.p_signal[:, rch[0]]; fsr = r.fs
    x = np.fromfile(f"{V}/data/{name}.bin", "<i2").astype(float)
    b = np.array(o["beats"]); bi = b.round().astype(int); bi = bi[(bi > 30) & (bi < len(x) - 30)]
    amp = np.array([x[i] - np.median(x[i - 30:i + 30]) for i in bi]); bt = bi / 100.0
    rr = np.diff(bt) * 1000; bt2 = bt[1:]; amp2 = amp[1:]
    ok = (rr > 300) & (rr < 2000); ok[1:] &= np.abs(np.diff(rr)) < 0.2 * rr[1:]
    bt2, rr, amp2 = bt2[ok], rr[ok], amp2[ok]
    bb, aa = butter(2, [0.08 / (fsr / 2), 0.7 / (fsr / 2)], "band"); rf = filtfilt(bb, aa, np.nan_to_num(resp))
    n = 0; good = 0
    for s, a, c, fu in edr_windows(bt2, rr, amp2, 0, len(x) / 100):
        seg = rf[int(s * fsr):int((s + 64) * fsr)]
        ref, conf = peak(seg[::int(fsr / 4)])           # reference: same spectral method on the respiration belt
        if np.isnan(ref) or conf < 0.5: continue
        n += 1
        for k, v in (("rr", a), ("amp", c), ("fused", fu)):
            if not np.isnan(v): allerr[k].append(v - ref)
        good += not np.isnan(fu)
    cover.append(good / max(1, n))
    fz = [fu for *_, fu in edr_windows(bt2, rr, amp2, 0, len(x) / 100) if not np.isnan(fu)]
    refs = []
    for s0 in np.arange(0, len(x) / 100 - 64, 32):
        rv, cf = peak(rf[int(s0 * fsr):int((s0 + 64) * fsr)][::int(fsr / 4)])
        if cf >= 0.5: refs.append(rv)
    if fz and refs: night.append(np.median(fz) - np.median(refs))
    print(f"{name}: windows {n}, fused coverage {good / max(1, n):.0%}, fused MAE {np.mean(np.abs(allerr['fused'][-good:])) if good else float('nan'):.2f}")
for k, e in allerr.items():
    e = np.array(e); print(f"{k:6s} n={len(e)} MAE {np.mean(np.abs(e)):.2f} br/min  bias {np.mean(e):+.2f}  within 2 br/min {np.mean(np.abs(e) <= 2):.0%}")
print("mean fused coverage", f"{np.mean(cover):.0%}")

print("per-night median error:", np.round(night, 1).tolist(), " MAE", round(float(np.mean(np.abs(night))), 2))
