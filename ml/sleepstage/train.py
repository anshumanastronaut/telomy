"""4-class sleep staging (Wake / Light / Deep / REM) from single-lead ECG beats (our phone detector).
Data: HMC (PhysioNet, CC BY 4.0, 151 nights) for training with subject-wise 5-fold CV; slpdb as an external test.
Models (numpy, portable to Swift): softmax regression and a 1-hidden-layer MLP, each + HMM (Viterbi) smoothing.
usage: train.py  → prints CV metrics, writes model.json (weights, normalisation, transition matrix)."""
import glob, json, os, subprocess, sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from features import NAMES, epoch_features, normalise_night, with_context

D = os.path.expanduser("~/telomy-lab/sleepstage"); V = os.path.expanduser("~/telomy-lab/validate")
KYVAL = os.path.expanduser("~/telomy-lab/ky-e-b1/KYECG/.build/release/kyval")
CLS = ["Wake", "Light", "Deep", "REM"]
MAP = {"W": 0, "N1": 1, "N2": 1, "N3": 2, "R": 3, "1": 1, "2": 1, "3": 2, "4": 2}

def beats_for(binpath, out):
    if not os.path.exists(out):
        subprocess.run([KYVAL, binpath, out, "65"], check=True, capture_output=True)
    o = json.load(open(out))
    return np.array(o["beats"]) / 100.0, np.array(o["amps"])

def load_night(kind, name):
    if kind == "hmc":
        meta = json.load(open(f"{D}/data/hmc_{name}.json"))
        y = np.array([MAP.get(s, -1) for s in meta["stages"]]); t0 = meta["onsets"][0] if meta["onsets"] else 0.0
        b, a = beats_for(f"{D}/data/hmc_{name}.bin", f"{D}/out/hmc_{name}.json")
    else:
        meta = json.load(open(f"{V}/data/slpdb_{name}.json"))
        st = meta["stages"]; t0 = st[0][0]
        y = np.array([MAP.get(s[1], -1) for s in st])
        b, a = beats_for(f"{V}/data/slpdb_{name}.bin", f"{D}/out/slpdb_{name}.json")
    F = epoch_features(b, a, len(y), t0)
    return F, y

def build(kind, names):
    os.makedirs(f"{D}/out", exist_ok=True)
    with ThreadPoolExecutor(8) as ex: nights = list(ex.map(lambda n: load_night(kind, n), names))
    X, Y, G = [], [], []
    for gi, (F, y) in enumerate(nights):
        Z = with_context(normalise_night(F))
        ok = (y >= 0) & ~np.isnan(F[:, 0])
        X.append(Z[ok]); Y.append(y[ok]); G.append(np.full(ok.sum(), gi))
    return X, Y, G

# ---------------------------------------------------------------- models
def softmax(z): z = z - z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)

def fit_mlp(X, y, hidden=32, epochs=60, lr=3e-3, l2=1e-4, w_cls=None, seed=0):
    rng = np.random.default_rng(seed); n, d = X.shape; k = 4
    if hidden:
        W1 = rng.normal(0, np.sqrt(2 / d), (d, hidden)); b1 = np.zeros(hidden); W2 = rng.normal(0, np.sqrt(2 / hidden), (hidden, k))
    else:
        W1 = None; b1 = None; W2 = np.zeros((d, k))
    b2 = np.zeros(k); params = [p for p in (W1, b1, W2, b2) if p is not None]
    m = [np.zeros_like(p) for p in params]; v = [np.zeros_like(p) for p in params]; step = 0
    Yoh = np.eye(k)[y]; sw = (w_cls[y] if w_cls is not None else np.ones(n))[:, None]
    for ep in range(epochs):
        idx = rng.permutation(n)
        for s in range(0, n, 256):
            bi = idx[s:s + 256]; xb = X[bi]
            if hidden:
                h = np.maximum(0, xb @ W1 + b1); pr = softmax(h @ W2 + b2)
            else:
                pr = softmax(xb @ W2 + b2)
            g = (pr - Yoh[bi]) * sw[bi] / len(bi)
            if hidden:
                gW2 = h.T @ g + l2 * W2; gb2 = g.sum(0); gh = (g @ W2.T) * (h > 0)
                grads = [xb.T @ gh + l2 * W1, gh.sum(0), gW2, gb2]
            else:
                grads = [xb.T @ g + l2 * W2, g.sum(0)]
            step += 1
            for i, (p, gr) in enumerate(zip(params, grads)):
                m[i] = 0.9 * m[i] + 0.1 * gr; v[i] = 0.999 * v[i] + 0.001 * gr * gr
                p -= lr * (m[i] / (1 - 0.9 ** step)) / (np.sqrt(v[i] / (1 - 0.999 ** step)) + 1e-8)
    return (W1, b1, W2, b2)

def predict(model, X):
    W1, b1, W2, b2 = model
    h = np.maximum(0, X @ W1 + b1) if W1 is not None else X
    return softmax(h @ W2 + b2)

def viterbi(P, prior, T):
    """HMM smoothing: emissions ∝ p(y|x)/p(y), transitions T (from training hypnograms)."""
    E = np.log(np.clip(P, 1e-9, None)); LT = np.log(T + 1e-9)  # P from class-balanced training already ~ likelihood
    n, k = E.shape; dp = np.zeros((n, k)); bp = np.zeros((n, k), int); dp[0] = E[0] + np.log(prior)
    for i in range(1, n):
        s = dp[i - 1][:, None] + LT; bp[i] = s.argmax(0); dp[i] = s.max(0) + E[i]
    path = np.zeros(n, int); path[-1] = dp[-1].argmax()
    for i in range(n - 1, 0, -1): path[i - 1] = bp[i, path[i]]
    return path

def kappa(y, p, k=4):
    C = np.zeros((k, k));
    for a, b in zip(y, p): C[a, b] += 1
    po = np.trace(C) / C.sum(); pe = (C.sum(0) * C.sum(1)).sum() / C.sum() ** 2
    return (po - pe) / (1 - pe), C

def report(name, ys, ps):
    y = np.concatenate(ys); p = np.concatenate(ps); k, C = kappa(y, p)
    f1 = [2 * C[i, i] / max(1, C[i].sum() + C[:, i].sum()) for i in range(4)]
    # per-night minutes of deep and REM: what the user sees
    dm = [abs((a == 2).sum() - (b == 2).sum()) / 2 for a, b in zip(ys, ps)]
    rm = [abs((a == 3).sum() - (b == 3).sum()) / 2 for a, b in zip(ys, ps)]
    print(f"{name:26s} acc {np.mean(y == p):.3f}  κ {k:.3f}  F1 W/L/D/R {' '.join(f'{x:.2f}' for x in f1)}"
          f"  | deep min MAE {np.mean(dm):.0f}  REM min MAE {np.mean(rm):.0f}")
    return k, C

def transitions(Ys):
    T = np.ones((4, 4))
    for y in Ys:
        for a, b in zip(y[:-1], y[1:]): T[a, b] += 1
    return T / T.sum(1, keepdims=True)

if __name__ == "__main__":
    hmc = sorted(os.path.basename(f)[4:-4] for f in glob.glob(f"{D}/data/hmc_*.bin"))
    slp = sorted(os.path.basename(f)[6:-4] for f in glob.glob(f"{V}/data/slpdb_*.bin"))
    X, Y, _ = build("hmc", hmc)
    print(f"HMC nights {len(X)}  epochs {sum(len(y) for y in Y)}  class mix", np.bincount(np.concatenate(Y), minlength=4) / sum(len(y) for y in Y))
    folds = np.arange(len(X)) % 5
    res = {}
    for label, hidden in (("softmax", 0), ("mlp32", 32)):
        ys, pr, pv = [], [], []
        for f in range(5):
            tr = [i for i in range(len(X)) if folds[i] != f]; te = [i for i in range(len(X)) if folds[i] == f]
            Xt = np.concatenate([X[i] for i in tr]); yt = np.concatenate([Y[i] for i in tr])
            prior = np.bincount(yt, minlength=4) / len(yt); wc = (1 / prior) / (1 / prior).mean() * 0.5 + 0.5
            mdl = fit_mlp(Xt, yt, hidden=hidden, w_cls=wc, epochs=40 if hidden else 30)
            T = transitions([Y[i] for i in tr])
            for i in te:
                P = predict(mdl, X[i]); ys.append(Y[i]); pr.append(P.argmax(1)); pv.append(viterbi(P, prior, T))
        report(f"{label}", ys, pr); res[label] = report(f"{label} + HMM", ys, pv)
    # final model on all HMC; external test on slpdb
    best = max(res, key=lambda k: res[k][0]); hidden = 32 if best == "mlp32" else 0
    Xa = np.concatenate(X); ya = np.concatenate(Y); prior = np.bincount(ya, minlength=4) / len(ya)
    wc = (1 / prior) / (1 / prior).mean() * 0.5 + 0.5
    mdl = fit_mlp(Xa, ya, hidden=hidden, w_cls=wc, epochs=40 if hidden else 30); T = transitions(Y)
    if slp:
        Xs, Ys, _ = build("slpdb", slp)
        report(f"slpdb external ({best}+HMM)", Ys, [viterbi(predict(mdl, x), prior, T) for x in Xs])
    W1, b1, W2, b2 = mdl
    json.dump({"classes": CLS, "features": NAMES, "context": {"offsets": [-6, -2, 2, 6], "smooth": [5, 15]},
               "hidden": hidden, "W1": None if W1 is None else W1.tolist(), "b1": None if b1 is None else b1.tolist(),
               "W2": W2.tolist(), "b2": b2.tolist(), "prior": prior.tolist(), "T": T.tolist(),
               "trained_on": f"HMC {len(X)} nights", "cv_kappa": res[best][0]}, open(f"{D}/model.json", "w"))
    print("model:", best, "→ model.json")
