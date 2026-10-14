"""CinC 2017 (PhysioNet, single-lead AliveCor, 300 Hz) → 100 Hz int16 µV like the KY-E-B1 band, then our phone beat
detector (kyval) on every record. Output: data/<rec>.bin and out/<rec>.json."""
import os, subprocess, numpy as np, scipy.io
from concurrent.futures import ThreadPoolExecutor
from scipy.signal import resample_poly

D = os.path.expanduser("~/telomy-lab/af2017"); KYVAL = os.path.expanduser("~/telomy-lab/ky-e-b1/KYECG/.build/release/kyval")
os.makedirs(f"{D}/data", exist_ok=True); os.makedirs(f"{D}/out", exist_ok=True)

def one(rec):
    b, o = f"{D}/data/{rec}.bin", f"{D}/out/{rec}.json"
    if not os.path.exists(b):
        x = scipy.io.loadmat(f"{D}/training2017/{rec}.mat")["val"][0].astype(float)  # 1000 adu/mV → adu = µV
        np.clip(resample_poly(x, 1, 3), -32000, 32000).astype("<i2").tofile(b)
    if not os.path.exists(o):
        subprocess.run([KYVAL, b, o, "65"], capture_output=True)
    return rec

recs = [l.split(",")[0] for l in open(f"{D}/REFERENCE-v3.csv").read().split()]
with ThreadPoolExecutor(8) as ex:
    for i, _ in enumerate(ex.map(one, recs)):
        if i % 1000 == 0: print(i, flush=True)
print("done", len(recs))
