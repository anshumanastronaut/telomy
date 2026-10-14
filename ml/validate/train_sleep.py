"""Sleep/wake from ECG-only epoch features (phone code), leave-one-subject-out on PhysioNet slpdb."""
import json, glob, os, sys
import numpy as np
D = os.path.expanduser("~/telomy-lab/validate")
OUTDIR = sys.argv[1] if len(sys.argv) > 1 else "out"
X, Y, G = [], [], []
for f in sorted(glob.glob(f"{D}/data/slpdb_*.json")):
    name = os.path.basename(f)[:-5]
    m = json.load(open(f)); o = json.load(open(f"{D}/{OUTDIR}/{name}.json"))
    st = m["stages"]; ts = np.array([s[0] for s in st])
    for e in o["epochs"]:
        if not e["f"]: continue
        k = np.searchsorted(ts, e["t"] - 15) - 1   # stage covering the epoch centre
        if k < 0: continue
        lab = st[k][1]
        if lab in ("MT", "?", "M"): continue
        X.append(e["f"][:4]); Y.append(0 if lab == "W" else 1); G.append(name)
X, Y, G = np.array(X), np.array(Y), np.array(G)
print(f"epochs {len(Y)}  sleep {Y.mean()*100:.1f}%  subjects {len(set(G))}")

def fit(X, Y, l2=0.1, it=3000, lr=0.3):
    Xb = np.c_[np.ones(len(X)), X]; w = np.zeros(Xb.shape[1])
    pos = Y.mean(); sw = np.where(Y == 1, 0.5 / pos, 0.5 / (1 - pos))   # balance wake vs sleep
    for _ in range(it):
        p = 1 / (1 + np.exp(-Xb @ w))
        g = Xb.T @ ((p - Y) * sw) / len(Y) + l2 * np.r_[0, w[1:]]
        w -= lr * g
    return w

def kappa(y, p):
    po = (y == p).mean(); pe = y.mean() * p.mean() + (1 - y.mean()) * (1 - p.mean())
    return (po - pe) / (1 - pe)

pred = np.zeros(len(Y))
for g in sorted(set(G)):
    tr, te = G != g, G == g
    w = fit(X[tr], Y[tr])
    pred[te] = 1 / (1 + np.exp(-np.c_[np.ones(te.sum()), X[te]] @ w))
yh = (pred > 0.5).astype(int)
# hysteresis like the app: 5-epoch median smoothing within each subject
sm = yh.copy()
for g in set(G):
    idx = np.where(G == g)[0]
    v = yh[idx]
    sm[idx] = [int(np.median(v[max(0, i - 2): i + 3]) > 0.5) for i in range(len(v))]
for lab, p in (("raw", yh), ("smoothed", sm)):
    acc = (p == Y).mean(); se = p[Y == 1].mean(); sp = 1 - p[Y == 0].mean()
    print(f"LOSO {lab:9s}: accuracy {acc*100:.1f}%  sleep-sensitivity {se*100:.1f}%  wake-specificity {sp*100:.1f}%  kappa {kappa(Y, p):.2f}")
w = fit(X, Y)
print("final coefficients [bias, hrRel, lnRMSSD, motion, hrSD]:", np.round(w, 3).tolist())
