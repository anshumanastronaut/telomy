"""Whole-night sleep/wake from beat times only (after sync): per-night normalisation + centred context windows."""
import json, glob, os
import numpy as np
D = os.path.expanduser("~/telomy-lab/validate")

def epoch_feats(beats_s, n_ep):
    rr_t = beats_s[1:]; rr = np.diff(beats_s) * 1000
    ok = (rr > 300) & (rr < 2000); rr_t, rr = rr_t[ok], rr[ok]
    F = np.full((n_ep, 5), np.nan)
    for e in range(n_ep):
        w = rr[(rr_t >= e * 30) & (rr_t < (e + 1) * 30)]
        if len(w) < 10: continue
        d = np.diff(w)
        F[e] = [60000 / w.mean(), np.log(max(1, np.sqrt(np.mean(d * d)))), w.std(), np.mean(np.abs(d) > 50), (60000 / w).std()]
    return F

def night_features(F):
    # fill gaps, per-night robust z-score, then centred context means/SDs over 3, 11, 21 epochs
    G = F.copy()
    for j in range(G.shape[1]):
        col = G[:, j]; m = np.nanmedian(col); col[np.isnan(col)] = m
        iqr = np.nanpercentile(col, 75) - np.nanpercentile(col, 25) or 1
        G[:, j] = (col - m) / iqr
    out = [G]
    for k in (3, 11, 21):
        pad = np.pad(G, ((k // 2, k // 2), (0, 0)), mode="edge")
        out.append(np.array([pad[i:i + k].mean(0) for i in range(len(G))]))
        out.append(np.array([pad[i:i + k, :1].std(0) for i in range(len(G))]))  # HR instability in context
    # hours since recording start (sleep pressure prior)
    out.append(np.arange(len(G))[:, None] / 120.0)
    return np.hstack(out)

X, Y, G = [], [], []
for f in sorted(glob.glob(f"{D}/data/slpdb_*.json")):
    name = os.path.basename(f)[:-5]
    m = json.load(open(f)); o = json.load(open(f"{D}/out/{name}.json"))
    beats = np.array(o["beats"]) / 100
    st = m["stages"]; n_ep = int(m["seconds"] // 30)
    Fn = night_features(epoch_feats(beats, n_ep))
    ts = np.array([s[0] for s in st])
    for e in range(n_ep):
        k = np.searchsorted(ts, e * 30 + 15) - 1
        if k < 0 or st[k][1] in ("MT", "M", "?"): continue
        X.append(Fn[e]); Y.append(0 if st[k][1] == "W" else 1); G.append(name)
X, Y, G = np.array(X), np.array(Y), np.array(G)

def fit(X, Y, l2=0.05, it=4000, lr=0.2):
    Xb = np.c_[np.ones(len(X)), X]; w = np.zeros(Xb.shape[1]); pos = Y.mean()
    sw = np.where(Y == 1, 0.5 / pos, 0.5 / (1 - pos))
    for _ in range(it):
        p = 1 / (1 + np.exp(-Xb @ w)); w -= lr * (Xb.T @ ((p - Y) * sw) / len(Y) + l2 * np.r_[0, w[1:]])
    return w
def kappa(y, p):
    po = (y == p).mean(); pe = y.mean() * p.mean() + (1 - y.mean()) * (1 - p.mean()); return (po - pe) / (1 - pe)
pred = np.zeros(len(Y))
for g in sorted(set(G)):
    tr, te = G != g, G == g
    w = fit(X[tr], Y[tr]); pred[te] = 1 / (1 + np.exp(-np.c_[np.ones(te.sum()), X[te]] @ w))
for thr in (0.4, 0.5, 0.6):
    p = (pred > thr).astype(int)
    print(f"LOSO thr {thr}: accuracy {100*(p==Y).mean():.1f}%  sleep-sens {100*p[Y==1].mean():.1f}%  wake-spec {100*(1-p[Y==0].mean()):.1f}%  kappa {kappa(Y,p):.2f}")
per = {g: (( (pred[G==g]>0.5).astype(int) == Y[G==g]).mean(), kappa(Y[G==g], (pred[G==g]>0.5).astype(int))) for g in sorted(set(G))}
print("per subject accuracy/kappa:", {k: (round(100*v[0]), round(v[1], 2)) for k, v in per.items()})
w = fit(X, Y); np.save(f"{D}/sleep_w.npy", w); print("features", X.shape[1], "weights saved")
