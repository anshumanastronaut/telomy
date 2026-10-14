"""Final rhythm model for the phone: HistGradientBoosting on CinC 2017 features (train_af.NAMES), exported as plain
trees (JSON) for Swift. Picks the AF alert threshold from 5-fold CV (target AF specificity ≥ 0.985 on CinC), then tests
it the way the phone runs it: rolling 60-s windows (step 30 s) on PhysioNet afdb (AF labels) and nsrdb (false alarms)."""
import json, os, subprocess, numpy as np
from concurrent.futures import ThreadPoolExecutor
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from train_af import NAMES, features

D = os.path.expanduser("~/telomy-lab/af2017"); V = os.path.expanduser("~/telomy-lab/validate")
KYVAL = os.path.expanduser("~/telomy-lab/ky-e-b1/KYECG/.build/release/kyval")
X = np.load(f"{D}/X.npy"); y = np.load(f"{D}/y.npy")
mk = lambda: HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, class_weight="balanced", random_state=0)
P = cross_val_predict(mk(), X, y, cv=StratifiedKFold(5, shuffle=True, random_state=0), method="predict_proba")
pa = P[:, 1]
for th in (0.3, 0.4, 0.5, 0.6, 0.7):
    print(f"th {th}: AF Se {np.mean(pa[y == 1] > th):.3f}  Sp {np.mean(pa[y != 1] <= th):.3f}")
cands = [t for t in np.arange(0.2, 0.95, 0.01) if np.mean(pa[y != 1] <= t) >= 0.985]
TH = float(round(cands[0], 2)) if cands else 0.7
print("chosen AF threshold", TH, f"Se {np.mean(pa[y == 1] > TH):.3f} Sp {np.mean(pa[y != 1] <= TH):.3f}")

m = mk().fit(X, y)
trees = []
for it in m._predictors:
    cls = []
    for t in it:
        nd = t.nodes
        cls.append([[int(n["feature_idx"]), float(n["num_threshold"]), int(n["left"]), int(n["right"]), int(n["is_leaf"]), float(n["value"]),
                     int(n["missing_go_to_left"])] for n in nd])
    trees.append(cls)
base = np.asarray(m._baseline_prediction).ravel().tolist()
model = {"features": NAMES, "classes": ["Normal", "AF", "Other", "Noisy"], "baseline": base, "trees": trees, "af_threshold": TH,
         "trained_on": "PhysioNet CinC 2017 (8528 single-lead ECGs) at 100 Hz, Telomy beat detector"}
json.dump(model, open(f"{D}/rhythm_model.json", "w"))

def raw_predict(Xr):
    """Same arithmetic as the Swift port: baseline + Σ tree leaf values per class, softmax."""
    out = []
    for x in Xr:
        s = np.array(base, float)
        for it in trees:
            for c, t in enumerate(it):
                i = 0
                while not t[i][4]:
                    f, thr, l, r = t[i][0], t[i][1], t[i][2], t[i][3]
                    i = l if x[f] <= thr else r
                s[c] += t[i][5]
        e = np.exp(s - s.max()); out.append(e / e.sum())
    return np.array(out)
print("export check: max |p - sklearn| =", np.abs(raw_predict(X[:200]) - m.predict_proba(X[:200])).max())

# ---- window test on long recordings (the phone screens rolling 60-s windows)
def kyv(rec):
    o = f"{D}/long_{rec}.json"
    if not os.path.exists(o): subprocess.run([KYVAL, f"{V}/data/{rec}.bin", o, "65"], capture_output=True)
    return rec
recs = sorted(os.path.basename(f)[:-4] for f in os.listdir(V + "/data") if f.endswith(".bin") and (f.startswith("afdb_") or f.startswith("nsrdb_")))
with ThreadPoolExecutor(8) as ex: list(ex.map(kyv, recs))
tp = fn = fp = tn = 0; nsr_fp = nsr_n = 0
for rec in recs:
    o = json.load(open(f"{D}/long_{rec}.json")); x = np.fromfile(f"{V}/data/{rec}.bin", "<i2")
    b = np.array(o["beats"]); a = np.array(o.get("amps", [])); meta = json.load(open(f"{V}/data/{rec}.json"))
    segs = meta.get("rhythm", [])
    W = []; L = []
    for s0 in range(0, len(x) // 100 - 60, 30):
        sel = (b >= s0 * 100) & (b < (s0 + 60) * 100)
        if sel.sum() < 20: continue
        lab = None
        if rec.startswith("afdb"):
            for r0, r1, r in segs:
                if r0 <= s0 and s0 + 60 <= r1: lab = (r == "AFIB"); break
            if lab is None: continue
        W.append(features(x[s0 * 100:(s0 + 60) * 100], b[sel] - s0 * 100, a[sel] if len(a) == len(b) else [])); L.append(lab)
    if not W: continue
    pr = m.predict_proba(np.nan_to_num(np.array(W)))[:, 1] > TH
    if rec.startswith("afdb"):
        L = np.array(L, bool); tp += (pr & L).sum(); fn += (~pr & L).sum(); fp += (pr & ~L).sum(); tn += (~pr & ~L).sum()
    else:
        nsr_fp += pr.sum(); nsr_n += len(pr)
print(f"afdb 60-s windows: AF Se {tp / max(1, tp + fn):.3f}  Sp {tn / max(1, tn + fp):.3f}   nsrdb false-alarm windows {nsr_fp / max(1, nsr_n):.4f} of {nsr_n}")
print("→ rhythm_model.json")
