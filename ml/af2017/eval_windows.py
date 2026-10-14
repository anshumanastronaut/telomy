"""Deployment test: 30-s windows every 15 s over long afdb (AF episodes annotated) and nsrdb (normal) recordings,
trained-on-CinC2017 GBDT vs the current rule. Windows fully inside one rhythm only."""
import json, glob, os, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from train_af import NAMES, features
V = os.path.expanduser("~/telomy-lab/validate")
X = np.load('X.npy'); y = np.load('y.npy'); keep = [i for i, n in enumerate(NAMES) if n != 'n_beats']
m = HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=15, learning_rate=0.08, class_weight='balanced', random_state=0).fit(X[:, keep], y)
TH = (0.15, 0.80, 0.40, 1.40, -1.4); ix = {k: NAMES.index(k) for k in NAMES}
res = {"afdb_AF": [], "afdb_nonAF": [], "nsrdb": []}
for f in sorted(glob.glob(f"{V}/out6/*.json")):
    name = os.path.basename(f)[:-5]; db = name.split("_")[0]
    meta = json.load(open(f"{V}/data/{name}.json")); o = json.load(open(f))
    x = np.fromfile(f"{V}/data/{name}.bin", "<i2"); b = np.array(o["beats"]); a = np.array(o["amps"])
    segs = meta.get("rhythm", [])
    step = 1500 if db == "afdb" else 3000   # 15 s (afdb) / 30 s (nsrdb) hop
    for s0 in range(0, len(x) - 3000, step):
        t0, t1 = s0 / 100, s0 / 100 + 30
        if db == "afdb":
            lab = None
            for r0, r1, r in segs:
                if r0 <= t0 and t1 <= r1: lab = r; break
            if lab is None: continue
            key = "afdb_AF" if lab == "AFIB" else "afdb_nonAF"
        else: key = "nsrdb"
        sel = (b >= s0) & (b < s0 + 3000)
        if sel.sum() < 6: continue
        fv = np.nan_to_num(np.array(features(x[s0:s0 + 3000], b[sel] - s0, a[sel])))
        p = m.predict_proba(fv[keep][None])[0]
        r = fv[ix['nrmssd']] > TH[0] and fv[ix['shannon']] > TH[1] and TH[2] < fv[ix['tpr']] < TH[3] and fv[ix['cosen']] > TH[4]
        res[key].append((p[1] > 0.5, r, p[3] > 0.5))
for k, v in res.items():
    v = np.array(v); print(f"{k:11s} windows {len(v):6d}  model AF-flag {v[:,0].mean()*100:5.1f}%  rule AF-flag {v[:,1].mean()*100:5.1f}%  model noisy {v[:,2].mean()*100:4.1f}%")
