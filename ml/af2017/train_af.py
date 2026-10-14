"""Rhythm classifier for the phone (Normal / AF / Other rhythm / Noisy) on CinC 2017 single-lead ECG at 100 Hz,
using OUR beat detector. Features are computable on the phone from the last ≤ 64 beats + the raw ECG window.
Reports 5-fold CV (challenge F1 = mean F1 of N, A, O; AF sensitivity/specificity) for LR, MLP and GBDT."""
import json, os, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, confusion_matrix

D = os.path.expanduser("~/telomy-lab/af2017"); FS = 100
LAB = {"N": 0, "A": 1, "O": 2, "~": 3}

def shannon(rr):  # identical to KYRhythmStats.shannonEntropy (Swift): trim ≤ 8 outliers, 16 bins, / log 16
    rr = list(rr)
    if len(rr) < 16: return 0.0
    m = sum(rr) / len(rr)
    srt = sorted(rr, key=lambda v: abs(v - m)); k = min(8, len(rr) // 8)
    tr = srt[:len(srt) - k] if k else srt
    lo, hi = min(tr), max(tr)
    if hi <= lo: return 0.0
    bins = [0] * 16
    for v in tr: bins[min(15, int((v - lo) / (hi - lo) * 16))] += 1
    n = len(tr); return float(-sum((c / n) * np.log(c / n) for c in bins if c > 0) / np.log(16))

def tpr(rr):  # identical to KYRhythmStats.turningPointRatio: turning points / (2(n−2)/3)
    rr = np.asarray(rr)
    if len(rr) < 3: return 0.0
    t = ((rr[1:-1] > rr[:-2]) & (rr[1:-1] > rr[2:])) | ((rr[1:-1] < rr[:-2]) & (rr[1:-1] < rr[2:]))
    return float(t.sum() / (2 * (len(rr) - 2) / 3))

def cosen(rr_ms, r=0.03):
    rr = rr_ms / 1000
    if len(rr) < 12: return -9.0
    r2 = r
    for _ in range(5):
        a = b = 0
        for i in range(len(rr) - 1):
            for j in range(i + 1, len(rr) - 1):
                if abs(rr[i] - rr[j]) <= r2:
                    b += 1
                    if abs(rr[i + 1] - rr[j + 1]) <= r2: a += 1
        if a >= 5 and b > 0: return float(-np.log(a / b) + np.log(2 * r2) - np.log(rr.mean()))
        r2 += 0.01
    return -9.0

def pwave(x, beats):
    """P-wave consistency (as KYInsight.pWaveScore): median corr of detrended 300–100 ms pre-R segments with their mean."""
    segs = []
    for s in beats:
        s = int(round(s))
        if s - 30 < 0 or s - 10 > len(x): continue
        y = x[s - 30:s - 9].astype(float); k = np.arange(len(y))
        if len(y) != 21: continue
        y = y - np.polyval(np.polyfit(k, y, 1), k); segs.append(y)
    if len(segs) < 8: return -1.0, 0.0
    S = np.array(segs); t = S.mean(0); tsd = np.sqrt((t ** 2).mean())
    if tsd < 8: return 0.0, tsd
    c = [(y @ t) / len(t) / (np.sqrt((y ** 2).mean()) * tsd + 1e-9) for y in S]
    return float(np.median(c)), float(tsd)

NAMES = ["n_beats", "hr", "rr_cv", "nrmssd", "pnn50", "pnn20", "shannon", "tpr", "cosen", "sd1_sd2", "irr_frac",
         "mad_ratio", "range_ratio", "min_ratio", "max_ratio", "pwave", "pwave_amp", "amp_cv", "beat_cov", "hf_noise", "flat_frac"]

def features(x, beats, amps):
    dur = len(x) / FS
    b = np.asarray(beats); rr = np.diff(b) / FS * 1000; am = np.asarray(amps)
    ok = (rr > 250) & (rr < 2500); r = rr[ok][-64:]
    f = dict.fromkeys(NAMES, 0.0)
    f["n_beats"] = len(b); f["beat_cov"] = (rr.sum() / 1000) / dur if len(rr) else 0
    d = np.diff(x.astype(float)); f["hf_noise"] = float(np.log(np.mean(np.abs(d)) + 1) - np.log(np.std(x) + 1))
    f["flat_frac"] = float(np.mean(np.abs(d) < 2))
    if len(r) >= 6:
        m = r.mean(); dd = np.diff(r)
        f.update(hr=60000 / m, rr_cv=r.std() / m, nrmssd=np.sqrt(np.mean(dd ** 2)) / m, pnn50=np.mean(np.abs(dd) > 50),
                 pnn20=np.mean(np.abs(dd) > 20), shannon=shannon(r), tpr=tpr(r), cosen=cosen(r),
                 irr_frac=np.mean(np.abs(dd) / r[1:] > 0.1), mad_ratio=np.median(np.abs(dd)) / np.median(r),
                 range_ratio=(r.max() - r.min()) / np.median(r), min_ratio=r.min() / np.median(r), max_ratio=r.max() / np.median(r))
        sd1 = np.std(dd) / np.sqrt(2); sd2 = np.sqrt(max(1e-9, 2 * np.var(r) - sd1 ** 2)); f["sd1_sd2"] = sd1 / sd2
    if len(am) > 4: f["amp_cv"] = float(np.std(am) / (np.mean(np.abs(am)) + 1))
    f["pwave"], f["pwave_amp"] = pwave(x, b)
    return [f[k] for k in NAMES]

if __name__ == "__main__":
    refs = [l.split(",") for l in open(f"{D}/REFERENCE-v3.csv").read().split()]
    X, y = [], []
    for rec, lab in refs:
        o = json.load(open(f"{D}/out/{rec}.json")); x = np.fromfile(f"{D}/data/{rec}.bin", "<i2")
        X.append(features(x, o["beats"], o.get("amps", []))); y.append(LAB[lab])
    X = np.nan_to_num(np.array(X)); y = np.array(y)
    np.save(f"{D}/X.npy", X); np.save(f"{D}/y.npy", y)
    print("records", len(y), "classes", np.bincount(y))
    skf = StratifiedKFold(5, shuffle=True, random_state=0)
    models = {
        "logreg": lambda: LogisticRegression(max_iter=3000, class_weight="balanced"),
        "mlp32": lambda: MLPClassifier((32,), max_iter=800, alpha=1e-3, random_state=0),
        "gbdt": lambda: HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, class_weight="balanced", random_state=0),
    }
    for name, mk in models.items():
        P = np.zeros(len(y), int)
        for tr, te in skf.split(X, y):
            sc = StandardScaler().fit(X[tr]); m = mk().fit(sc.transform(X[tr]), y[tr]); P[te] = m.predict(sc.transform(X[te]))
        f1 = f1_score(y, P, average=None)
        af_se = np.mean(P[y == 1] == 1); af_sp = np.mean(P[y != 1] != 1)
        print(f"{name:7s} challenge F1 {np.mean(f1[:3]):.3f}  F1 N/A/O/~ {' '.join(f'{v:.2f}' for v in f1)}  AF Se {af_se:.3f} Sp {af_sp:.3f}")
    # current rule (thresholds in KYInsight) as a baseline, AF vs rest
    th = (0.15, 0.80, 0.40, 1.40, -1.4); i = {k: NAMES.index(k) for k in NAMES}
    rule = (X[:, i["nrmssd"]] > th[0]) & (X[:, i["shannon"]] > th[1]) & (X[:, i["tpr"]] > th[2]) & (X[:, i["tpr"]] < th[3]) & (X[:, i["cosen"]] > th[4])
    print(f"current rule  AF Se {np.mean(rule[y == 1]):.3f} Sp {np.mean(~rule[y != 1]):.3f}")
