"""Domain-adapt the rhythm model to continuous (Holter-like) data: add 60-s windows from afdb + nsrdb TRAIN records to
CinC 2017, test on held-out afdb/nsrdb records. Compares: CinC-only, CinC+long, each with/without 2-window persistence
and AND-ed with the KYInsight rule. Writes rhythm_model.json for the best safe option."""
import json, os, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from train_af import NAMES, features

D = os.path.expanduser("~/telomy-lab/af2017"); V = os.path.expanduser("~/telomy-lab/validate")
TRAIN_AF = {"afdb_04015", "afdb_04126", "afdb_04908", "afdb_05091", "afdb_06426", "afdb_07879", "afdb_08455"}

def windows(rec):
    c = f"{D}/win_{rec}.npz"
    if os.path.exists(c): z = np.load(c); return z["X"], z["L"], z["T"]
    o = json.load(open(f"{D}/long_{rec}.json")); x = np.fromfile(f"{V}/data/{rec}.bin", "<i2")
    b = np.array(o["beats"]); a = np.array(o.get("amps", [])); segs = json.load(open(f"{V}/data/{rec}.json")).get("rhythm", [])
    Xw, Lw, Tw = [], [], []
    for s0 in range(0, len(x) // 100 - 60, 30):
        sel = (b >= s0 * 100) & (b < (s0 + 60) * 100)
        if sel.sum() < 20: continue
        lab = 0
        if rec.startswith("afdb"):
            lab = -1
            for r0, r1, r in segs:
                if r0 <= s0 and s0 + 60 <= r1: lab = 1 if r == "AFIB" else 0; break
        Xw.append(features(x[s0 * 100:(s0 + 60) * 100], b[sel] - s0 * 100, a[sel] if len(a) == len(b) else [])); Lw.append(lab); Tw.append(s0)
    Xw = np.nan_to_num(np.array(Xw)); np.savez(c, X=Xw, L=np.array(Lw), T=np.array(Tw)); return Xw, np.array(Lw), np.array(Tw)

recs = sorted(f[5:-5] for f in os.listdir(D) if f.startswith("long_") and f.endswith(".json"))
nsr = [r for r in recs if r.startswith("nsrdb")]; nsr_train = set(nsr[: len(nsr) // 2])
W = {r: windows(r) for r in recs}
istrain = lambda r: (r in TRAIN_AF) or (r in nsr_train)

Xc = np.load(f"{D}/X.npy"); yc = np.load(f"{D}/y.npy")
Xl = np.concatenate([W[r][0][W[r][1] >= 0] for r in recs if istrain(r)])
yl = np.concatenate([np.where(W[r][1][W[r][1] >= 0] == 1, 1, 0) for r in recs if istrain(r)])   # long data: AF vs normal(0)
mk = lambda: HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, class_weight="balanced", random_state=0)
models = {"cinc only": mk().fit(Xc, yc), "cinc + long": mk().fit(np.concatenate([Xc, Xl]), np.concatenate([yc, yl]))}
i = {k: NAMES.index(k) for k in NAMES}
def rule(X): return (X[:, i["nrmssd"]] > 0.15) & (X[:, i["shannon"]] > 0.8) & (X[:, i["tpr"]] > 0.4) & (X[:, i["tpr"]] < 1.4) & (X[:, i["cosen"]] > -1.4)
def persist(p): return p & np.r_[False, p[:-1]] | p & np.r_[p[1:], False]   # positive only if a neighbour window agrees

for name, m in models.items():
    for th in (0.5, 0.63, 0.75):
        for mode in ("plain", "persist", "and-rule"):
            tp = fn = fp = tn = 0; nf = nn = 0
            for r in recs:
                if istrain(r): continue
                X, L, T = W[r]
                if not len(X): continue
                pr = m.predict_proba(X)[:, 1] > th
                if mode == "persist": pr = persist(pr)
                if mode == "and-rule": pr = pr & rule(X)
                if r.startswith("afdb"):
                    k = L >= 0; p, l = pr[k], L[k] == 1
                    tp += (p & l).sum(); fn += (~p & l).sum(); fp += (p & ~l).sum(); tn += (~p & ~l).sum()
                else: nf += pr.sum(); nn += len(pr)
            print(f"{name:12s} th {th:.2f} {mode:8s} afdb(test) Se {tp/max(1,tp+fn):.3f} Sp {tn/max(1,tn+fp):.3f} | nsrdb(test) FP {nf/max(1,nn):.4f}")
# rule alone for reference
tp = fn = fp = tn = 0; nf = nn = 0
for r in recs:
    if istrain(r): continue
    X, L, T = W[r]
    if not len(X): continue
    pr = rule(X)
    if r.startswith("afdb"):
        k = L >= 0; p, l = pr[k], L[k] == 1; tp += (p & l).sum(); fn += (~p & l).sum(); fp += (p & ~l).sum(); tn += (~p & ~l).sum()
    else: nf += pr.sum(); nn += len(pr)
print(f"{'rule only':12s}                   afdb(test) Se {tp/max(1,tp+fn):.3f} Sp {tn/max(1,tn+fp):.3f} | nsrdb(test) FP {nf/max(1,nn):.4f}")
