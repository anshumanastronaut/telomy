import json, glob, os
import numpy as np
D = os.path.expanduser("~/telomy-lab/validate")
def match(ref, det, tol=15):  # 150 ms at 100 Hz
    ref = np.array(sorted(ref)); det = np.array(sorted(det))
    if not len(ref) or not len(det): return 0, len(ref), len(det)
    i = j = tp = 0
    while i < len(ref) and j < len(det):
        if abs(ref[i] - det[j]) <= tol: tp += 1; i += 1; j += 1
        elif det[j] < ref[i]: j += 1
        else: i += 1
    return tp, len(ref) - tp, len(det) - tp
rows = []
for f in sorted(glob.glob(f"{D}/data/*.json")):
    m = json.load(open(f)); name = os.path.basename(f)[:-5]
    if "beats" not in m: continue
    o = json.load(open(f"{D}/out/{name}.json"))
    ref = [b[0] for b in m["beats"] if b[0] > 300]   # skip 3 s warm-up
    det = [b for b in o["beats"] if b > 300]
    tp, fn, fp = match(ref, det)
    # HR: reference 10-s mean from annotated beats vs Kalman HR at each second
    rb = np.array([b[0] for b in m["beats"]]) / 100
    hr = np.array(o["hr"]); ok = hr[:, 1] > 0
    errs = []
    for sec, h in hr[ok][:, :2][::5]:
        w = rb[(rb > sec - 10) & (rb <= sec)]
        if len(w) >= 4:
            rr = np.diff(w); rr = rr[(rr > 0.25) & (rr < 2.5)]
            if len(rr) >= 3: errs.append(abs(h - 60 / rr.mean()))
    rows.append((m["db"], name, tp, fn, fp, np.mean(errs) if errs else np.nan, np.percentile(errs, 95) if errs else np.nan, ok.mean()))
for db in ["mitdb", "nsrdb", "afdb", "slpdb"]:
    r = [x for x in rows if x[0] == db]
    if not r: continue
    tp, fn, fp = sum(x[2] for x in r), sum(x[3] for x in r), sum(x[4] for x in r)
    print(f"{db:6s} records {len(r):2d}  beats {tp+fn:8d}  Se {100*tp/(tp+fn):6.2f}%  +P {100*tp/(tp+fp):6.2f}%  HR MAE {np.nanmean([x[5] for x in r]):4.1f} bpm (p95 {np.nanmean([x[6] for x in r]):4.1f})  HR available {100*np.mean([x[7] for x in r]):4.1f}% of time")
print("worst records (Se or +P):")
for x in sorted(rows, key=lambda x: min(x[2]/(x[2]+x[3]+1e-9), x[2]/(x[2]+x[4]+1e-9)))[:8]:
    print(f"  {x[1]:14s} Se {100*x[2]/(x[2]+x[3]):6.2f}  +P {100*x[2]/(x[2]+x[4]):6.2f}  HR MAE {x[5]:5.1f}")
