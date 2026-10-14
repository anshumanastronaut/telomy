"""Download HMC sleep staging DB (PhysioNet, CC BY 4.0): keep the ECG channel only, resampled to 100 Hz int16 µV
(same as the KY-E-B1 band), plus 30-s stages. The 100 MB EDFs are deleted after extraction.
usage: dl_hmc.py [N]   → data/hmc_SNxxx.bin + data/hmc_SNxxx.json {stages: [...], fs: 100}"""
import json, os, socket, sys, urllib.request, numpy as np
socket.setdefaulttimeout(60)
from concurrent.futures import ThreadPoolExecutor
from scipy.signal import resample_poly

BASE = "https://physionet-open.s3.amazonaws.com/hmc-sleep-staging/1.1/"
OUT = os.path.expanduser("~/telomy-lab/sleepstage/data")
STAGE = {"Sleep stage W": "W", "Sleep stage N1": "N1", "Sleep stage N2": "N2", "Sleep stage N3": "N3", "Sleep stage R": "R"}

def read_edf_channel(path, want="ECG"):
    with open(path, "rb") as f:
        h = f.read(256)
        ns = int(h[252:256]); nrec = int(h[236:244]); dur = float(h[244:252])
        hh = f.read(ns * 256)
        def field(off, width): return [hh[off + i * width: off + (i + 1) * width].decode("latin1").strip() for i in range(ns)]
        labels = field(0, 16); o = ns * 16
        o += ns * 80; o += ns * 8
        pmin = [float(x) for x in field(o, 8)]; o += ns * 8
        pmax = [float(x) for x in field(o, 8)]; o += ns * 8
        dmin = [float(x) for x in field(o, 8)]; o += ns * 8
        dmax = [float(x) for x in field(o, 8)]; o += ns * 8
        o += ns * 80
        nsamp = [int(x) for x in field(o, 8)]
        ci = next(i for i, l in enumerate(labels) if want.lower() in l.lower())
        rec = np.fromfile(f, dtype="<i2")
    per = sum(nsamp); rec = rec[: nrec * per].reshape(nrec, per)
    start = sum(nsamp[:ci]); x = rec[:, start:start + nsamp[ci]].reshape(-1).astype(np.float64)
    gain = (pmax[ci] - pmin[ci]) / (dmax[ci] - dmin[ci]); x = (x - dmin[ci]) * gain + pmin[ci]
    return x, nsamp[ci] / dur, labels[ci]

def stages(txt):
    out = []
    for line in txt.splitlines()[1:]:
        p = [s.strip() for s in line.split(",")]
        if len(p) >= 5 and p[4] in STAGE: out.append((float(p[2]), STAGE[p[4]]))
    return out

def one(rec, tries=3):
    for k in range(tries):
        r = _one(rec)
        if "ERR" not in r[1]: return r
    return r

def _one(rec):
    name = rec.split("/")[-1].replace(".edf", "")
    tgt = f"{OUT}/hmc_{name}.bin"
    if os.path.exists(tgt): return name, "cached"
    edf = f"{OUT}/{name}.edf"
    try:
        urllib.request.urlretrieve(BASE + f"recordings/{name}.edf", edf)
        txt = urllib.request.urlopen(BASE + f"recordings/{name}_sleepscoring.txt", timeout=60).read().decode()
        x, fs, lab = read_edf_channel(edf)
        unit = 1000.0 if np.nanmax(np.abs(x)) < 50 else 1.0  # mV → µV
        y = resample_poly(x * unit, 100, int(round(fs)))
        np.clip(y, -32000, 32000).astype("<i2").tofile(tgt)
        st = stages(txt)
        json.dump({"fs": 100, "src_fs": fs, "channel": lab, "stages": [s for _, s in st], "onsets": [o for o, _ in st]}, open(f"{OUT}/hmc_{name}.json", "w"))
        return name, f"ok {len(y)/360000:.1f} h, {len(st)} epochs"
    except Exception as e:
        return name, f"ERR {e}"
    finally:
        if os.path.exists(edf): os.remove(edf)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    recs = [r for r in urllib.request.urlopen(BASE + "RECORDS").read().decode().split() if r]
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(recs)
    with ThreadPoolExecutor(4) as ex:
        for name, msg in ex.map(one, recs[:n]): print(name, msg, flush=True)
