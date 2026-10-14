import json, os, sys, numpy as np
D = os.path.expanduser("~/telomy-lab/validate")
for name in sys.argv[1:]:
    m = json.load(open(f"{D}/data/{name}.json")); o = json.load(open(f"{D}/out/{name}.json"))
    ref = np.array([b[0] for b in m["beats"]]); det = np.array(o["beats"])
    idx = np.clip(np.searchsorted(ref, det), 1, len(ref) - 1)
    near = np.where(np.abs(ref[idx] - det) < np.abs(ref[idx - 1] - det), ref[idx], ref[idx - 1])
    off = (det - near) * 10  # ms
    off = off[np.abs(off) < 400]
    h = np.histogram(off, bins=[-400, -200, -150, -100, -50, -20, 20, 50, 100, 150, 200, 400])[0]
    print(f"{name}: median offset {np.median(off):6.1f} ms, IQR {np.percentile(off,25):.0f}..{np.percentile(off,75):.0f}  hist {h.tolist()}  ({len(det)} det / {len(ref)} ref)")
