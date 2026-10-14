"""NST-style noise stress records: clean ECG + em (electrode motion) / ma (muscle) noise in alternating 2-min blocks
at a given SNR (dB), after the first 5 min clean (Moody 1984 protocol). Writes data/nst_<rec>_<noise><snr>.bin/.json
with the clean annotations plus the noisy intervals."""
import json, os
import numpy as np, wfdb
from scipy.signal import resample_poly
D = os.path.expanduser("~/telomy-lab/validate"); P = os.path.expanduser("~/telomy-lab/physionet")
def load100(path):
    r = wfdb.rdrecord(path); x = r.p_signal[:, 0] * 1000
    return resample_poly(x, 5, 18) if r.fs == 360 else x
for rec in ("100", "103", "119"):
    meta = json.load(open(f"{D}/data/mitdb_{rec}.json"))
    clean = np.fromfile(f"{D}/data/mitdb_{rec}.bin", "<i2").astype(float)
    beats = np.array([b[0] for b in meta["beats"]], int)
    # signal power from QRS peak-to-peak amplitude, as in the NSTDB protocol
    amp = np.median([np.ptp(clean[max(0, b - 5): b + 5]) for b in beats if 5 < b < len(clean) - 5])
    for kind in ("em", "ma"):
        nz = load100(f"{P}/nstdb/{kind}")
        nz = np.resize(nz, len(clean)); nz -= nz.mean()
        for snr in (12, 6, 0):
            # scale so that SNR = 20·log10(S / N) with S = peak-to-peak QRS / 8 (approx RMS) as in nst.c
            scale = (amp / 8) / (np.std(nz) * 10 ** (snr / 20))
            y = clean.copy(); noisy = []
            t = 300 * 100
            while t < len(y):
                y[t:t + 12000] += scale * nz[t:t + 12000]; noisy.append([t / 100, min(len(y), t + 12000) / 100]); t += 24000
            out = f"nst_{rec}_{kind}{snr}"
            np.clip(np.round(y), -32767, 32767).astype("<i2").tofile(f"{D}/data/{out}.bin")
            json.dump({**meta, "db": "nst", "rec": out, "noisy": noisy, "snr": snr, "noise": kind}, open(f"{D}/data/{out}.json", "w"))
            print(out, "ok")
